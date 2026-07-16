#!/usr/bin/env python3
"""Connect a live Epic organization to the local health core, and resync it.

connect: one-time interactive setup for an org —
  endpoint lookup -> SMART PKCE login (browser) -> dynamic client registration
  (key in macOS Keychain) -> init connection -> first sync -> verify.

resync: unattended refresh for an existing connection (cron entry point) —
  JWT bearer token from the Keychain key -> sync -> verify.

Examples:
  python3 core/connect.py connect --repo ~/health-data --connection nyu --org "NYU Langone"
  python3 core/connect.py resync  --repo ~/health-data --connection nyu
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import epic_auth  # noqa: E402
import health_core  # noqa: E402

PROD_CLIENT_ID = "ae8f0930-576b-4f19-a146-a2a3745d60dc"
RELAY_REDIRECT = "https://dipakkrishnan.github.io/health-os/callback"
CALLBACK_PORT = 8965
ENDPOINT_DIRECTORY = "https://open.epic.com/Endpoints/R4"
SANDBOX_BASE = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"


def find_org(query: str) -> str:
    directory = epic_auth.http_json(ENDPOINT_DIRECTORY, headers={"Accept": "application/json"})
    matches = [
        (entry.get("name", ""), entry.get("address", ""))
        for item in directory.get("entry", [])
        if (entry := item.get("resource", item))
        and query.lower() in entry.get("name", "").lower()
    ]
    if not matches:
        sys.exit(f"No Epic organization matched {query!r}")
    if len(matches) > 1:
        print(f"Multiple organizations match {query!r}; rerun with --fhir-base <address>:")
        for name, address in matches[:25]:
            print(f"  {name}: {address}")
        sys.exit(1)
    print(f"Matched organization: {matches[0][0]}")
    return matches[0][1].rstrip("/")


def oauth_endpoints(fhir_base: str, client_id: str) -> dict[str, str]:
    capability = epic_auth.http_json(
        f"{fhir_base}/metadata",
        headers={"Accept": "application/fhir+json", "Epic-Client-ID": client_id},
    )
    found = {
        name: epic_auth.find_oauth_uri(capability, name)
        for name in ("authorize", "token", "register")
    }
    if not found["authorize"] or not found["token"]:
        sys.exit("FHIR metadata did not advertise OAuth authorize/token endpoints")
    return found


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def wait_for_callback(expected_state: str) -> str:
    result: dict[str, str] = {}

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

    server = HTTPServer(("localhost", CALLBACK_PORT), Handler)
    while not result:
        server.handle_request()
    server.server_close()
    if "error" in result:
        sys.exit(f"OAuth callback error: {result['error']}")
    return result["code"]


def authorize(fhir_base: str, authorize_url: str, token_url: str, client_id: str, redirect: str) -> dict:
    verifier = b64url(secrets.token_bytes(32))
    state = secrets.token_urlsafe(16)
    url = authorize_url + "?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect,
        "scope": "openid fhirUser",
        "state": state,
        "aud": fhir_base,
        "code_challenge": b64url(hashlib.sha256(verifier.encode()).digest()),
        "code_challenge_method": "S256",
    })
    print("Opening browser for patient portal login...")
    print(f"If it doesn't open: {url}\n")
    webbrowser.open(url)
    code = wait_for_callback(state)
    return epic_auth.http_json(
        token_url,
        method="POST",
        body=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
            "client_id": client_id,
            "code_verifier": verifier,
        }).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def connect(args: argparse.Namespace) -> None:
    fhir_base = args.fhir_base.rstrip("/") if args.fhir_base else find_org(args.org)
    endpoints = oauth_endpoints(fhir_base, args.client_id)

    token = authorize(fhir_base, endpoints["authorize"], endpoints["token"], args.client_id, args.redirect)
    patient_id = token.get("patient")
    if not patient_id:
        sys.exit(f"No patient id in token response (fields: {sorted(token)})")
    print(f"Authorized. Patient id: {patient_id}")

    health_core.initialize(
        args.repo, args.connection, args.provider or args.org or fhir_base,
        fhir_base, patient_id, endpoints["token"],
        str(token.get("scope") or "").split(), token.get("fhirUser"),
    )

    access_token = token["access_token"]
    if endpoints["register"]:
        credential_ref = f"keychain:health-os/{args.connection}"
        epic_auth.generate_key_in_keychain(f"health-os/{args.connection}")
        registration = epic_auth.register_dynamic_client(
            endpoints["register"], access_token, args.client_id, credential_ref
        )
        epic_auth.save_registration(args.repo, args.connection, registration["client_id"], credential_ref)
        print(f"Dynamic client registered: {registration['client_id']} (key in Keychain)")
        access_token = epic_auth.obtain_access_token(
            endpoints["token"], registration["client_id"], credential_ref
        )["access_token"]
    else:
        print("WARNING: org does not advertise dynamic registration; unattended resync unavailable.")

    summary = health_core.sync(args.repo, args.connection, access_token)
    print(json.dumps(summary, indent=2))
    report = health_core.verify(args.repo)
    print(f"Grounding: {report['pointers_resolved']} pointers resolved, {len(report['dangling'])} dangling")
    if report["dangling"]:
        sys.exit(1)


def resync(args: argparse.Namespace) -> None:
    with health_core.connect(args.repo) as db:
        row = db.execute(
            "SELECT * FROM connections WHERE connection_id=?", (args.connection,)
        ).fetchone()
    if not row:
        sys.exit(f"Unknown connection: {args.connection}")
    if not row["dynamic_client_id"] or not row["credential_ref"]:
        sys.exit(f"Connection {args.connection} has no dynamic client; rerun connect")
    access_token = epic_auth.obtain_access_token(
        row["token_endpoint"], row["dynamic_client_id"], row["credential_ref"]
    )["access_token"]
    summary = health_core.sync(args.repo, args.connection, access_token)
    print(json.dumps(summary, indent=2))
    report = health_core.verify(args.repo)
    if report["dangling"]:
        sys.exit(f"Grounding check failed: {len(report['dangling'])} dangling pointers")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    connect_parser = subparsers.add_parser("connect")
    connect_parser.add_argument("--repo", type=Path, required=True)
    connect_parser.add_argument("--connection", required=True)
    connect_parser.add_argument("--org", help="Organization name to look up in Epic's endpoint directory")
    connect_parser.add_argument("--fhir-base", help="Explicit FHIR R4 base URL (skips directory lookup)")
    connect_parser.add_argument("--provider", help="Display name for the connection")
    connect_parser.add_argument("--client-id", default=PROD_CLIENT_ID)
    connect_parser.add_argument("--redirect", default=RELAY_REDIRECT)

    resync_parser = subparsers.add_parser("resync")
    resync_parser.add_argument("--repo", type=Path, required=True)
    resync_parser.add_argument("--connection", required=True)

    args = parser.parse_args()
    if args.command == "connect":
        if not args.org and not args.fhir_base:
            sys.exit("Provide --org or --fhir-base")
        connect(args)
    else:
        resync(args)


if __name__ == "__main__":
    main()
