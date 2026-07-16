#!/usr/bin/env python3
"""Epic dynamic client registration and JWT bearer access for native clients."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError as error:  # pragma: no cover - exercised by CLI environment
    raise SystemExit("Install core/requirements.txt before using Epic dynamic auth") from error


JWT_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def integer_bytes(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def public_jwk(private_key: rsa.RSAPrivateKey) -> dict[str, str]:
    numbers = private_key.public_key().public_numbers()
    base = {
        "kty": "RSA",
        "n": b64url(integer_bytes(numbers.n)),
        "e": b64url(integer_bytes(numbers.e)),
        "use": "sig",
        "alg": "RS256",
    }
    base["kid"] = b64url(hashlib.sha256(json.dumps(base, sort_keys=True).encode()).digest())[:32]
    return base


def generate_key(path: Path) -> dict[str, str]:
    if path.exists():
        raise FileExistsError(f"Refusing to replace existing key: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    return public_jwk(key)


def load_key(path: Path) -> rsa.RSAPrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Epic dynamic client keys must be RSA private keys")
    return key


def keychain_store(service: str, pem: bytes) -> str:
    # ponytail: `security -w` briefly exposes the (base64) key in the process
    # list; upgrade path is the Security framework via ctypes if that matters.
    subprocess.run(
        ["security", "add-generic-password", "-a", os.environ.get("USER", "health-os"),
         "-s", service, "-w", base64.b64encode(pem).decode(), "-U"],
        check=True, capture_output=True,
    )
    return f"keychain:{service}"


def keychain_load(service: str) -> rsa.RSAPrivateKey:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        check=True, capture_output=True, text=True,
    )
    key = serialization.load_pem_private_key(base64.b64decode(result.stdout.strip()), password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Epic dynamic client keys must be RSA private keys")
    return key


def generate_key_in_keychain(service: str) -> dict[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    keychain_store(service, pem)
    return public_jwk(key)


def resolve_key(ref: Path | str) -> rsa.RSAPrivateKey:
    """Load a private key from a credential ref: a Path, 'keychain:<service>',
    or 'sandbox-file:<path>' (development only)."""
    if isinstance(ref, Path):
        return load_key(ref)
    text = str(ref)
    if text.startswith("keychain:"):
        return keychain_load(text.split(":", 1)[1])
    if text.startswith("sandbox-file:"):
        return load_key(Path(text.split(":", 1)[1]))
    return load_key(Path(text))


def http_json(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        response_body = error.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {response_body[:1000]}") from error


def find_oauth_uri(document: Any, name: str) -> str | None:
    if isinstance(document, dict):
        if document.get("url") == name and isinstance(document.get("valueUri"), str):
            return document["valueUri"]
        for value in document.values():
            found = find_oauth_uri(value, name)
            if found:
                return found
    elif isinstance(document, list):
        for value in document:
            found = find_oauth_uri(value, name)
            if found:
                return found
    return None


def discover_registration_endpoint(fhir_base: str, software_id: str) -> str:
    capability = http_json(
        f"{fhir_base.rstrip('/')}/metadata",
        headers={"Accept": "application/fhir+json", "Epic-Client-ID": software_id},
    )
    registration = find_oauth_uri(capability, "register")
    if not registration:
        raise RuntimeError("FHIR metadata did not advertise a dynamic registration endpoint")
    return registration


def register_dynamic_client(
    registration_endpoint: str,
    initial_access_token: str,
    software_id: str,
    key_ref: Path | str,
) -> dict[str, Any]:
    jwk = public_jwk(resolve_key(key_ref))
    payload = json.dumps({"software_id": software_id, "jwks": {"keys": [jwk]}}).encode()
    return http_json(
        registration_endpoint,
        method="POST",
        body=payload,
        headers={
            "Authorization": f"Bearer {initial_access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )


def signed_assertion(dynamic_client_id: str, token_endpoint: str, key_ref: Path | str, now: int | None = None) -> str:
    issued_at = now if now is not None else int(datetime.now(timezone.utc).timestamp())
    key = resolve_key(key_ref)
    jwk = public_jwk(key)
    header = {"alg": "RS256", "typ": "JWT", "kid": jwk["kid"]}
    claims = {
        "iss": dynamic_client_id,
        "sub": dynamic_client_id,
        "aud": token_endpoint,
        "jti": str(uuid.uuid4()),
        "iat": issued_at,
        "nbf": issued_at,
        "exp": issued_at + 300,
    }
    signing_input = f"{b64url(json.dumps(header, separators=(',', ':')).encode())}.{b64url(json.dumps(claims, separators=(',', ':')).encode())}"
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input}.{b64url(signature)}"


def obtain_access_token(token_endpoint: str, dynamic_client_id: str, key_ref: Path | str) -> dict[str, Any]:
    assertion = signed_assertion(dynamic_client_id, token_endpoint, key_ref)
    body = urllib.parse.urlencode(
        {
            "grant_type": JWT_GRANT,
            "assertion": assertion,
            "client_id": dynamic_client_id,
        }
    ).encode()
    return http_json(
        token_endpoint,
        method="POST",
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )


def save_registration(repo: Path, connection_id: str, dynamic_client_id: str, key_ref: Path | str) -> None:
    credential_ref = f"sandbox-file:{key_ref.resolve()}" if isinstance(key_ref, Path) else str(key_ref)
    database = repo / "health.sqlite"
    with sqlite3.connect(database) as db:
        changed = db.execute(
            """
            UPDATE connections
            SET dynamic_client_id=?, credential_ref=?, updated_at=?
            WHERE connection_id=?
            """,
            (
                dynamic_client_id,
                credential_ref,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                connection_id,
            ),
        ).rowcount
    if changed != 1:
        raise ValueError(f"Unknown connection: {connection_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    key_parser = subparsers.add_parser("generate-key")
    key_parser.add_argument("--key", type=Path, required=True)

    discover_parser = subparsers.add_parser("discover")
    discover_parser.add_argument("--fhir-base", required=True)
    discover_parser.add_argument("--software-id", required=True)

    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("--registration-endpoint", required=True)
    register_parser.add_argument("--software-id", required=True)
    register_parser.add_argument("--key", type=Path, required=True)
    register_parser.add_argument("--token-env", default="HEALTH_OS_INITIAL_ACCESS_TOKEN")
    register_parser.add_argument("--repo", type=Path)
    register_parser.add_argument("--connection")

    token_parser = subparsers.add_parser("token")
    token_parser.add_argument("--token-endpoint", required=True)
    token_parser.add_argument("--client-id", required=True)
    token_parser.add_argument("--key", type=Path, required=True)
    token_parser.add_argument("--access-token-only", action="store_true")

    args = parser.parse_args()
    if args.command == "generate-key":
        print(json.dumps({"jwks": {"keys": [generate_key(args.key)]}}, indent=2))
    elif args.command == "discover":
        print(discover_registration_endpoint(args.fhir_base, args.software_id))
    elif args.command == "register":
        initial_token = os.environ.get(args.token_env)
        if not initial_token:
            sys.exit(f"Missing one-time registration token in {args.token_env}")
        registration = register_dynamic_client(
            args.registration_endpoint, initial_token, args.software_id, args.key
        )
        dynamic_client_id = registration.get("client_id")
        if not dynamic_client_id:
            sys.exit("Epic registration response did not include client_id")
        if args.repo or args.connection:
            if not args.repo or not args.connection:
                sys.exit("--repo and --connection must be supplied together")
            save_registration(args.repo, args.connection, dynamic_client_id, args.key)
        print(json.dumps(registration, indent=2))
    elif args.command == "token":
        token = obtain_access_token(args.token_endpoint, args.client_id, args.key)
        if args.access_token_only:
            print(token["access_token"])
        else:
            safe = {key: value for key, value in token.items() if key not in ("access_token", "refresh_token", "id_token")}
            safe["access_token_present"] = "access_token" in token
            print(json.dumps(safe, indent=2))


if __name__ == "__main__":
    main()
