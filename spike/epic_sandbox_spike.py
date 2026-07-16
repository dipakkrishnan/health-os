#!/usr/bin/env python3
"""Epic sandbox spike: SMART on FHIR standalone patient launch with PKCE.

Proves the auth flow end to end against Epic's public sandbox, then pulls
every resource type Health OS cares about for the test patient and dumps
raw FHIR JSON to spike/out/.

Run:  python3 spike/epic_sandbox_spike.py
Sandbox MyChart login: fhircamila / epicepic1  (test patient Camila Lopez)

Stdlib only. Exit code 0 means both spike questions are answered:
  1. localhost redirect works
  2. token response contents printed (look for refresh_token / granted scopes)
"""

import base64
import hashlib
import json
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CLIENT_ID = "2da9c3f3-6f6e-45a9-8d89-84eaa7f48007"  # non-production
REDIRECT_URI = "http://localhost:8965/callback"
AUTHORIZE_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
FHIR_BASE = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
SCOPE = "openid fhirUser"  # Epic grants per app registration; scope string stays minimal
OUT_DIR = Path(__file__).parent / "out"

# (name, resource path, extra query params). Patient is fetched by id, not searched.
# Epic requires category on some searches; failures are logged, not fatal — the
# spike's job is to discover exactly which queries the sandbox accepts.
QUERIES = [
    ("observation-labs", "Observation", {"category": "laboratory"}),
    ("observation-vitals", "Observation", {"category": "vital-signs"}),
    ("observation-social", "Observation", {"category": "social-history"}),
    ("medication-requests", "MedicationRequest", {}),
    ("conditions", "Condition", {}),
    ("allergies", "AllergyIntolerance", {}),
    ("immunizations", "Immunization", {}),
    ("procedures", "Procedure", {}),
    ("encounters", "Encounter", {}),
    ("diagnostic-reports", "DiagnosticReport", {}),
    ("document-references", "DocumentReference", {"category": "clinical-note"}),
]


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def wait_for_callback(expected_state: str) -> str:
    """Serve localhost:8965 until the OAuth callback arrives; return the auth code."""
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            params = urllib.parse.parse_qs(parsed.query)
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if "error" in params:
                result["error"] = params["error"][0]
                self.wfile.write(b"<h1>Authorization failed</h1><p>See terminal.</p>")
            elif params.get("state", [""])[0] != expected_state:
                result["error"] = "state mismatch"
                self.wfile.write(b"<h1>State mismatch</h1>")
            else:
                result["code"] = params["code"][0]
                self.wfile.write(b"<h1>Health OS: authorized.</h1><p>Close this tab.</p>")

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 8965), Handler)
    while not result:
        server.handle_request()
    server.server_close()
    if "error" in result:
        sys.exit(f"OAuth callback error: {result['error']}")
    return result["code"]


def http_json(url: str, data: bytes | None = None, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}\n{body[:2000]}") from e


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- authorize (PKCE) ---
    verifier = b64url(secrets.token_bytes(32))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)
    auth_url = AUTHORIZE_URL + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "aud": FHIR_BASE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    print("Opening browser for MyChart sandbox login (fhircamila / epicepic1)...")
    print(f"If it doesn't open: {auth_url}\n")
    webbrowser.open(auth_url)
    code = wait_for_callback(state)
    print("SPIKE Q1 ANSWERED: localhost redirect works.\n")

    # --- token exchange ---
    token = http_json(
        TOKEN_URL,
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    (OUT_DIR / "token_response.json").write_text(json.dumps(token, indent=2))
    print("SPIKE Q2 — token response fields (full copy in out/token_response.json):")
    for k, v in token.items():
        shown = v if k not in ("access_token", "refresh_token", "id_token") else str(v)[:12] + "..."
        print(f"  {k}: {shown}")
    print()

    patient_id = token.get("patient")
    if not patient_id:
        sys.exit("No patient id in token response — cannot continue.")
    bearer = {"Authorization": f"Bearer {token['access_token']}", "Accept": "application/fhir+json"}

    # --- fetch ---
    patient = http_json(f"{FHIR_BASE}/Patient/{patient_id}", headers=bearer)
    (OUT_DIR / "patient.json").write_text(json.dumps(patient, indent=2))
    name = patient.get("name", [{}])[0].get("text", "?")
    print(f"Patient: {name} ({patient_id})")

    for name_, resource, extra in QUERIES:
        params = {"patient": patient_id, **extra}
        url = f"{FHIR_BASE}/{resource}?" + urllib.parse.urlencode(params)
        entries, page = [], 0
        try:
            while url:
                bundle = http_json(url, headers=bearer)
                page += 1
                entries += bundle.get("entry", [])
                url = next((l["url"] for l in bundle.get("link", []) if l.get("relation") == "next"), None)
            (OUT_DIR / f"{name_}.json").write_text(json.dumps(entries, indent=2))
            print(f"  {name_}: {len(entries)} entries ({page} page(s))")
        except RuntimeError as e:
            print(f"  {name_}: FAILED — {str(e).splitlines()[0]}")

    print(f"\nDone. Raw FHIR in {OUT_DIR}/")


if __name__ == "__main__":
    main()
