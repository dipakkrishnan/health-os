#!/usr/bin/env python3
"""Turn the one-time Epic OAuth result into a restart-safe sandbox sync proof."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

import epic_auth  # noqa: E402
import health_core  # noqa: E402


FHIR_BASE = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
TOKEN_ENDPOINT = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
SOFTWARE_ID = "2da9c3f3-6f6e-45a9-8d89-84eaa7f48007"
CONNECTION_ID = "epic-sandbox"


def run(token_file: Path, data_repo: Path, key_path: Path) -> dict:
    token_payload = json.loads(token_file.read_text())
    initial_token = token_payload["access_token"]
    patient_id = token_payload["patient"]

    # The OAuth response contains live bearer credentials. Keep it only in memory.
    token_file.unlink()

    health_core.initialize(
        data_repo,
        CONNECTION_ID,
        "Epic public sandbox",
        FHIR_BASE,
        patient_id,
        TOKEN_ENDPOINT,
    )
    if not key_path.exists():
        epic_auth.generate_key(key_path)

    registration_endpoint = epic_auth.discover_registration_endpoint(FHIR_BASE, SOFTWARE_ID)
    registration = epic_auth.register_dynamic_client(
        registration_endpoint,
        initial_token,
        SOFTWARE_ID,
        key_path,
    )
    dynamic_client_id = registration["client_id"]
    epic_auth.save_registration(data_repo, CONNECTION_ID, dynamic_client_id, key_path)

    # Mint a fresh JWT-backed access token for each process-equivalent sync.
    first_token = epic_auth.obtain_access_token(TOKEN_ENDPOINT, dynamic_client_id, key_path)["access_token"]
    first = health_core.sync(data_repo, CONNECTION_ID, first_token)
    del first_token

    second_token = epic_auth.obtain_access_token(TOKEN_ENDPOINT, dynamic_client_id, key_path)["access_token"]
    second = health_core.sync(data_repo, CONNECTION_ID, second_token)
    del second_token

    return {
        "registration_endpoint": registration_endpoint,
        "dynamic_client_id": dynamic_client_id,
        "patient_id": patient_id,
        "first_sync": first,
        "second_sync": second,
        "core_status": health_core.status(data_repo),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", type=Path, default=ROOT / "spike/out/token_response.json")
    parser.add_argument("--data-repo", type=Path, default=ROOT / "spike/health-data")
    parser.add_argument("--key", type=Path, default=ROOT / "spike/state/epic-sandbox.pem")
    parser.add_argument("--result", type=Path, default=ROOT / "spike/dynamic_result.json")
    args = parser.parse_args()

    result = run(args.token_file, args.data_repo, args.key)
    args.result.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
