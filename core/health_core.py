#!/usr/bin/env python3
"""Deterministic Epic FHIR storage and first-slice clinical item parsing."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PARSER_VERSION = "fhir-r4-v2"
SCHEMA = Path(__file__).with_name("schema.sql")
DATASETS = (
    ("patient", "Patient", None),
    ("observation-labs", "Observation", {"category": "laboratory"}),
    ("observation-vitals", "Observation", {"category": "vital-signs"}),
    ("medication-requests", "MedicationRequest", {}),
    ("medication-dispenses", "MedicationDispense", {}),
    ("conditions", "Condition", {}),
    ("allergies", "AllergyIntolerance", {}),
    ("encounters", "Encounter", {}),
    # ponytail: assess-plan returns Epic's longitudinal plan too; add other
    # category variants only if a real org proves they carry distinct data
    ("care-plans", "CarePlan", {"category": "assess-plan"}),
    ("document-references", "DocumentReference", {}),
    ("service-requests", "ServiceRequest", {}),
    ("diagnostic-reports", "DiagnosticReport", {}),
    ("procedures", "Procedure", {}),
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_id(*parts: str) -> str:
    return sha256("\x1f".join(parts).encode())


def database_path(repo: Path) -> Path:
    return repo / "health.sqlite"


def connect(repo: Path) -> sqlite3.Connection:
    db = sqlite3.connect(database_path(repo))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'"
    ).fetchone():
        migrate_schema(db)
        db.commit()
    return db


def migrate_schema(db: sqlite3.Connection) -> None:
    connection_columns = {row[1] for row in db.execute("PRAGMA table_info(connections)")}
    for name, declaration in (
        ("authorization_scopes_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("fhir_user", "TEXT"),
        ("authorized_at", "TEXT"),
    ):
        if name not in connection_columns:
            db.execute(f"ALTER TABLE connections ADD COLUMN {name} {declaration}")
    columns = {row[1] for row in db.execute("PRAGMA table_info(resources)")}
    if "is_current" not in columns:
        db.execute(
            "ALTER TABLE resources ADD COLUMN is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1))"
        )
        db.execute("UPDATE resources SET is_current=0")
        db.execute(
            """
            UPDATE resources SET is_current=1
            WHERE rowid IN (
                SELECT MAX(rowid) FROM resources GROUP BY connection_id, logical_key
            )
            """
        )
    db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS resources_one_current_idx ON resources(connection_id, logical_key) WHERE is_current=1"
    )
    db.execute(
        """
        CREATE VIEW IF NOT EXISTS current_clinical_items AS
        SELECT ci.*
        FROM clinical_items ci
        JOIN resources r ON r.resource_version_key=ci.resource_version_key
        WHERE r.is_current=1
        """
    )
    db.execute("UPDATE metadata SET value='3' WHERE key='schema_version'")


def initialize(
    repo: Path,
    connection_id: str,
    provider: str,
    fhir_base: str,
    patient_id: str,
    token_endpoint: str | None = None,
    authorization_scopes: list[str] | None = None,
    fhir_user: str | None = None,
) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "raw").mkdir(exist_ok=True)
    now = utcnow()
    with connect(repo) as db:
        db.executescript(SCHEMA.read_text())
        migrate_schema(db)
        db.execute(
            """
            INSERT INTO connections (
                connection_id, provider, fhir_base, patient_id, token_endpoint,
                authorization_scopes_json, fhir_user, authorized_at,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(connection_id) DO UPDATE SET
                provider=excluded.provider,
                fhir_base=excluded.fhir_base,
                patient_id=excluded.patient_id,
                token_endpoint=COALESCE(excluded.token_endpoint, connections.token_endpoint),
                authorization_scopes_json=excluded.authorization_scopes_json,
                fhir_user=COALESCE(excluded.fhir_user, connections.fhir_user),
                authorized_at=excluded.authorized_at,
                updated_at=excluded.updated_at
            """,
            (
                connection_id,
                provider,
                fhir_base.rstrip("/"),
                patient_id,
                token_endpoint,
                canonical_json(sorted(authorization_scopes or [])),
                fhir_user,
                now,
                now,
                now,
            ),
        )


def http_get(url: str, token: str) -> tuple[int, str, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/fhir+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.headers.get_content_type(), response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get_content_type(), error.read()


def store_blob(
    db: sqlite3.Connection,
    repo: Path,
    body: bytes,
    media_type: str,
    created_at: str,
) -> str:
    digest = sha256(body)
    relative = Path("raw") / digest[:2] / f"{digest}.json"
    destination = repo / relative
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_bytes(body)
        os.replace(temporary, destination)
    db.execute(
        """
        INSERT OR IGNORE INTO raw_blobs
            (sha256, relative_path, media_type, byte_count, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (digest, str(relative), media_type, len(body), created_at),
    )
    return digest


def resource_rows(document: Any) -> Iterable[tuple[dict[str, Any], str]]:
    if isinstance(document, dict) and document.get("resourceType") == "Bundle":
        for index, entry in enumerate(document.get("entry", [])):
            resource = entry.get("resource") if isinstance(entry, dict) else None
            if isinstance(resource, dict) and resource.get("resourceType"):
                yield resource, f"/entry/{index}/resource"
    elif isinstance(document, dict) and document.get("resourceType"):
        yield document, ""


def store_resources(
    db: sqlite3.Connection,
    connection_id: str,
    sync_run_id: str,
    blob_sha: str,
    body: bytes,
    seen_at: str,
) -> list[tuple[str, dict[str, Any], str]]:
    document = json.loads(body)
    stored = []
    for resource, pointer in resource_rows(document):
        resource_type = str(resource["resourceType"])
        content = canonical_json(resource)
        content_sha = sha256(content.encode())
        resource_id = str(resource.get("id") or f"anonymous-{content_sha[:16]}")
        logical_key = f"{connection_id}/{resource_type}/{resource_id}"
        version_id = resource.get("meta", {}).get("versionId")
        version_key = stable_id(logical_key, content_sha)
        db.execute(
            "UPDATE resources SET is_current=0 WHERE connection_id=? AND logical_key=?",
            (connection_id, logical_key),
        )
        db.execute(
            """
            INSERT INTO resources (
                resource_version_key, connection_id, logical_key, resource_type,
                resource_id, version_id, content_sha256, source_blob_sha256,
                json_pointer, content_json, first_seen_run_id, last_seen_run_id,
                first_seen_at, last_seen_at, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(connection_id, logical_key, content_sha256) DO UPDATE SET
                last_seen_run_id=excluded.last_seen_run_id,
                last_seen_at=excluded.last_seen_at,
                is_current=1
            """,
            (
                version_key,
                connection_id,
                logical_key,
                resource_type,
                resource_id,
                version_id,
                content_sha,
                blob_sha,
                pointer,
                content,
                sync_run_id,
                sync_run_id,
                seen_at,
                seen_at,
            ),
        )
        stored.append((version_key, resource, pointer))
    return stored


def first_coding(concept: Any) -> tuple[str | None, str | None, str | None]:
    if not isinstance(concept, dict):
        return None, None, None
    coding = next((item for item in concept.get("coding", []) if isinstance(item, dict)), {})
    display = concept.get("text") or coding.get("display")
    return coding.get("system"), coding.get("code"), display


def period(resource: dict[str, Any], prefix: str) -> tuple[str | None, str | None]:
    date_time = resource.get(f"{prefix}DateTime") or resource.get(f"{prefix}Instant")
    if date_time:
        return str(date_time), None
    value_period = resource.get(f"{prefix}Period")
    if isinstance(value_period, dict):
        return value_period.get("start"), value_period.get("end")
    value_date = resource.get(f"{prefix}Date")
    return (str(value_date), None) if value_date else (None, None)


def pointer(base: str, suffix: str) -> str:
    return f"{base}{suffix}" if base else suffix


def resolve_pointer(document: Any, ptr: str) -> Any:
    value = document
    if not ptr:
        return value
    for part in ptr.lstrip("/").split("/"):
        if isinstance(value, list):
            value = value[int(part)]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise KeyError(ptr)
    return value


def first_present(resource: dict[str, Any], base: str, *suffixes: str) -> str | None:
    """First candidate pointer whose path actually exists in the resource.

    Evidence pointers are a grounding guarantee — a pointer that does not
    resolve must be omitted, never emitted."""
    for suffix in suffixes:
        try:
            resolve_pointer(resource, suffix)
        except (KeyError, IndexError, ValueError):
            continue
        return pointer(base, suffix)
    return None


def parse_resource(
    version_key: str,
    resource: dict[str, Any],
    base_pointer: str,
) -> dict[str, Any] | None:
    resource_type = resource.get("resourceType")
    status = resource.get("status")
    evidence = {"resource": base_pointer or ""}

    if resource_type == "Patient":
        names = resource.get("name") or []
        name = names[0] if names and isinstance(names[0], dict) else {}
        display = name.get("text") or " ".join(
            [*name.get("given", []), name.get("family", "")]
        ).strip() or "Patient"
        system, code = None, None
        start, end = resource.get("birthDate"), None
        recorded = resource.get("meta", {}).get("lastUpdated")
        value = {
            "name": names,
            "birthDate": resource.get("birthDate"),
            "gender": resource.get("gender"),
            "deceasedBoolean": resource.get("deceasedBoolean"),
            "deceasedDateTime": resource.get("deceasedDateTime"),
        }
        kind = "patient_profile"
        evidence.update(
            value=first_present(resource, base_pointer, "/name", "/birthDate", "/gender"),
            time=first_present(resource, base_pointer, "/meta/lastUpdated", "/birthDate"),
        )

    elif resource_type == "Observation":
        categories = {
            coding.get("code")
            for category in resource.get("category", [])
            for coding in category.get("coding", [])
            if isinstance(coding, dict)
        }
        if "laboratory" in categories:
            kind = "lab_result"
        elif "vital-signs" in categories:
            kind = "vital_sign"
        else:
            return None
        system, code, display = first_coding(resource.get("code"))
        start, end = period(resource, "effective")
        value = {
            key: resource[key]
            for key in resource
            if key.startswith("value") or key in ("interpretation", "referenceRange")
        }
        recorded = resource.get("issued")
        evidence.update(
            code=first_present(resource, base_pointer, "/code"),
            value=first_present(resource, base_pointer, "/valueQuantity", "/valueCodeableConcept", "/valueString", "/valueBoolean", "/valueInteger", "/valueRatio", "/component"),
            time=first_present(resource, base_pointer, "/effectiveDateTime", "/effectivePeriod", "/effectiveInstant", "/issued"),
        )

    elif resource_type == "MedicationRequest":
        medication = resource.get("medicationCodeableConcept")
        system, code, display = first_coding(medication)
        if not display and resource.get("medicationReference"):
            display = resource["medicationReference"].get("display") or resource["medicationReference"].get("reference")
        start = resource.get("authoredOn")
        end = None
        value = {
            "intent": resource.get("intent"),
            "dosageInstruction": resource.get("dosageInstruction", []),
            "dispenseRequest": resource.get("dispenseRequest"),
        }
        kind, recorded = "medication_order", resource.get("authoredOn")
        evidence.update(
            code=first_present(resource, base_pointer, "/medicationCodeableConcept", "/medicationReference"),
            value=first_present(resource, base_pointer, "/dosageInstruction"),
            time=first_present(resource, base_pointer, "/authoredOn"),
        )

    elif resource_type == "MedicationDispense":
        medication = resource.get("medicationCodeableConcept")
        system, code, display = first_coding(medication)
        if not display and resource.get("medicationReference"):
            display = resource["medicationReference"].get("display") or resource["medicationReference"].get("reference")
        start = resource.get("whenHandedOver") or resource.get("whenPrepared")
        end = None
        recorded = resource.get("whenPrepared")
        value = {
            "dosageInstruction": resource.get("dosageInstruction", []),
            "quantity": resource.get("quantity"),
            "daysSupply": resource.get("daysSupply"),
            "authorizingPrescription": resource.get("authorizingPrescription", []),
            "whenHandedOver": resource.get("whenHandedOver"),
        }
        kind = "medication_dispense"
        evidence.update(
            code=first_present(resource, base_pointer, "/medicationCodeableConcept", "/medicationReference"),
            value=first_present(resource, base_pointer, "/dosageInstruction", "/quantity", "/daysSupply"),
            time=first_present(resource, base_pointer, "/whenHandedOver", "/whenPrepared"),
        )

    elif resource_type == "Condition":
        system, code, display = first_coding(resource.get("code"))
        start, end = period(resource, "onset")
        value = {
            "clinicalStatus": resource.get("clinicalStatus"),
            "verificationStatus": resource.get("verificationStatus"),
            "category": resource.get("category", []),
            "abatementDateTime": resource.get("abatementDateTime"),
        }
        kind, recorded = "condition_assertion", resource.get("recordedDate")
        evidence.update(
            code=first_present(resource, base_pointer, "/code"),
            value=first_present(resource, base_pointer, "/verificationStatus", "/clinicalStatus"),
            time=first_present(resource, base_pointer, "/onsetDateTime", "/onsetPeriod", "/onsetAge", "/recordedDate"),
        )

    elif resource_type == "AllergyIntolerance":
        system, code, display = first_coding(resource.get("code"))
        start, end = period(resource, "onset")
        value = {
            "clinicalStatus": resource.get("clinicalStatus"),
            "verificationStatus": resource.get("verificationStatus"),
            "criticality": resource.get("criticality"),
            "reaction": resource.get("reaction", []),
        }
        kind, recorded = "allergy_assertion", resource.get("recordedDate")
        evidence.update(
            code=first_present(resource, base_pointer, "/code"),
            value=first_present(resource, base_pointer, "/reaction", "/clinicalStatus", "/criticality"),
            time=first_present(resource, base_pointer, "/onsetDateTime", "/onsetPeriod", "/recordedDate"),
        )

    elif resource_type == "Encounter":
        concept = next(iter(resource.get("type", [])), {})
        system, code, display = first_coding(concept)
        if not display:
            display = resource.get("class", {}).get("display") or "Encounter"
        encounter_period = resource.get("period", {})
        start, end = encounter_period.get("start"), encounter_period.get("end")
        value = {
            "class": resource.get("class"),
            "type": resource.get("type", []),
            "reasonCode": resource.get("reasonCode", []),
            "hospitalization": resource.get("hospitalization"),
        }
        kind, recorded = "encounter", None
        evidence.update(
            code=first_present(resource, base_pointer, "/type/0"),
            value=first_present(resource, base_pointer, "/class"),
            time=first_present(resource, base_pointer, "/period"),
        )

    elif resource_type == "CarePlan":
        system, code, display = first_coding(next(iter(resource.get("category", [])), {}))
        display = resource.get("title") or display or "Care plan"
        plan_period = resource.get("period", {})
        start, end = plan_period.get("start"), plan_period.get("end")
        recorded = resource.get("meta", {}).get("lastUpdated")
        value = {
            "intent": resource.get("intent"),
            "category": resource.get("category", []),
            "addresses": resource.get("addresses", []),
            "goal": resource.get("goal", []),
            "activity": resource.get("activity", []),
        }
        kind = "care_plan"
        evidence.update(
            code=first_present(resource, base_pointer, "/category/0"),
            value=first_present(resource, base_pointer, "/activity", "/goal", "/addresses"),
            time=first_present(resource, base_pointer, "/period", "/meta/lastUpdated"),
        )

    elif resource_type == "DocumentReference":
        system, code, display = first_coding(resource.get("type"))
        display = resource.get("description") or display or "Clinical document"
        start, end = resource.get("date"), None
        recorded = resource.get("date")
        value = {
            "docStatus": resource.get("docStatus"),
            "category": resource.get("category", []),
            "author": resource.get("author", []),
            "custodian": resource.get("custodian"),
            "content": resource.get("content", []),
            "context": resource.get("context"),
        }
        kind = "clinical_document"
        evidence.update(
            code=first_present(resource, base_pointer, "/type", "/category/0"),
            value=first_present(resource, base_pointer, "/content", "/description"),
            time=first_present(resource, base_pointer, "/date"),
        )

    elif resource_type == "ServiceRequest":
        system, code, display = first_coding(resource.get("code"))
        start, end = period(resource, "occurrence")
        recorded = resource.get("authoredOn")
        value = {
            "intent": resource.get("intent"),
            "category": resource.get("category", []),
            "requester": resource.get("requester"),
            "reasonCode": resource.get("reasonCode", []),
            "reasonReference": resource.get("reasonReference", []),
        }
        kind = "service_request"
        evidence.update(
            code=first_present(resource, base_pointer, "/code"),
            value=first_present(resource, base_pointer, "/requester", "/reasonCode", "/category"),
            time=first_present(resource, base_pointer, "/occurrenceDateTime", "/occurrencePeriod", "/authoredOn"),
        )

    elif resource_type == "DiagnosticReport":
        system, code, display = first_coding(resource.get("code"))
        start, end = period(resource, "effective")
        recorded = resource.get("issued")
        value = {
            "category": resource.get("category", []),
            "conclusion": resource.get("conclusion"),
            "conclusionCode": resource.get("conclusionCode", []),
            "result": resource.get("result", []),
            "presentedForm": resource.get("presentedForm", []),
        }
        kind = "diagnostic_report"
        evidence.update(
            code=first_present(resource, base_pointer, "/code"),
            value=first_present(resource, base_pointer, "/conclusion", "/result", "/presentedForm"),
            time=first_present(resource, base_pointer, "/effectiveDateTime", "/effectivePeriod", "/issued"),
        )

    elif resource_type == "Procedure":
        system, code, display = first_coding(resource.get("code"))
        start, end = period(resource, "performed")
        recorded = resource.get("meta", {}).get("lastUpdated")
        value = {
            "category": resource.get("category"),
            "reasonCode": resource.get("reasonCode", []),
            "reasonReference": resource.get("reasonReference", []),
            "outcome": resource.get("outcome"),
            "performer": resource.get("performer", []),
        }
        kind = "procedure"
        evidence.update(
            code=first_present(resource, base_pointer, "/code"),
            value=first_present(resource, base_pointer, "/outcome", "/performer", "/reasonCode"),
            time=first_present(resource, base_pointer, "/performedDateTime", "/performedPeriod", "/meta/lastUpdated"),
        )

    else:
        return None

    evidence = {key: value for key, value in evidence.items() if value is not None}
    return {
        "kind": kind,
        "effective_start": start,
        "effective_end": end,
        "recorded_at": recorded,
        "status": status,
        "code_system": system,
        "code": code,
        "display": display or f"{resource_type} {resource.get('id', '')}".strip(),
        "value_json": canonical_json(value),
        "evidence_json": canonical_json(evidence),
        "version_key": version_key,
    }


def store_clinical_item(
    db: sqlite3.Connection,
    connection_id: str,
    version_key: str,
    resource: dict[str, Any],
    base_pointer: str,
    source_blob_sha: str,
    created_at: str,
) -> bool:
    item = parse_resource(version_key, resource, base_pointer)
    if not item:
        return False
    resource_id = str(resource.get("id") or "anonymous")
    logical_key = f"{connection_id}/{resource['resourceType']}/{resource_id}"
    item_id = stable_id(version_key, item["kind"], PARSER_VERSION)
    before = db.total_changes
    db.execute(
        """
        INSERT OR IGNORE INTO clinical_items (
            clinical_item_id, connection_id, resource_version_key, logical_key,
            kind, effective_start, effective_end, recorded_at, status,
            code_system, code, display, value_json, assertion_origin,
            source_blob_sha256, evidence_json, parser_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            connection_id,
            version_key,
            logical_key,
            item["kind"],
            item["effective_start"],
            item["effective_end"],
            item["recorded_at"],
            item["status"],
            item["code_system"],
            item["code"],
            item["display"],
            item["value_json"],
            "clinical_record",
            source_blob_sha,
            item["evidence_json"],
            PARSER_VERSION,
            created_at,
        ),
    )
    return db.total_changes > before


def dataset_url(fhir_base: str, patient_id: str, resource_type: str, parameters: dict[str, str] | None) -> str:
    if parameters is None:
        return f"{fhir_base}/{resource_type}/{urllib.parse.quote(patient_id, safe='')}"
    query = urllib.parse.urlencode({"patient": patient_id, **parameters})
    return f"{fhir_base}/{resource_type}?{query}"


def document_binary_urls(resource: dict[str, Any], fhir_base: str) -> list[str]:
    """Return same-origin Binary links; never send a bearer token to another host."""
    base = urllib.parse.urlparse(fhir_base)
    urls = []
    for content in resource.get("content", []):
        url = (content.get("attachment") or {}).get("url") if isinstance(content, dict) else None
        if not url:
            continue
        absolute = urllib.parse.urljoin(f"{fhir_base.rstrip('/')}/", url)
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme == base.scheme and parsed.netloc == base.netloc and "/Binary/" in parsed.path:
            urls.append(absolute)
    return urls


def update_coverage(
    db: sqlite3.Connection,
    connection_id: str,
    dataset: str,
    resource_type: str,
    status: str,
    item_count: int,
    attempted_at: str,
    error: str | None,
) -> None:
    success = attempted_at if status in ("success", "empty") else None
    db.execute(
        """
        INSERT INTO coverage (
            connection_id, dataset, resource_type, status, item_count,
            last_attempt_at, last_success_at, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(connection_id, dataset) DO UPDATE SET
            status=excluded.status,
            item_count=excluded.item_count,
            last_attempt_at=excluded.last_attempt_at,
            last_success_at=COALESCE(excluded.last_success_at, coverage.last_success_at),
            error=excluded.error
        """,
        (connection_id, dataset, resource_type, status, item_count, attempted_at, success, error),
    )


def sync(repo: Path, connection_id: str, token: str) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    started = utcnow()
    failures = []
    binary_urls: set[str] = set()
    summary: dict[str, Any] = {"sync_run_id": run_id, "datasets": {}}
    with connect(repo) as db:
        connection = db.execute(
            "SELECT * FROM connections WHERE connection_id=?", (connection_id,)
        ).fetchone()
        if not connection:
            raise ValueError(f"Unknown connection: {connection_id}")
        db.execute(
            "INSERT INTO sync_runs (sync_run_id, connection_id, started_at, status) VALUES (?, ?, ?, 'running')",
            (run_id, connection_id, started),
        )

        for dataset, resource_type, parameters in DATASETS:
            url = dataset_url(connection["fhir_base"], connection["patient_id"], resource_type, parameters)
            page_number = 0
            resource_count = 0
            new_item_count = 0
            error_message = None
            while url:
                page_number += 1
                retrieved = utcnow()
                status_code, media_type, body = http_get(url, token)
                blob_sha = store_blob(db, repo, body, media_type, retrieved)
                db.execute(
                    """
                    INSERT INTO sync_pages (
                        sync_run_id, dataset, page_number, request_url,
                        retrieved_at, http_status, blob_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (run_id, dataset, page_number, url, retrieved, status_code, blob_sha),
                )
                if not 200 <= status_code < 300:
                    error_message = f"HTTP {status_code}; response blob {blob_sha}"
                    failures.append(f"{dataset}: {error_message}")
                    break
                try:
                    document = json.loads(body)
                    stored = store_resources(db, connection_id, run_id, blob_sha, body, retrieved)
                except (json.JSONDecodeError, TypeError, KeyError) as error:
                    error_message = f"Invalid FHIR JSON in blob {blob_sha}: {error}"
                    failures.append(f"{dataset}: {error_message}")
                    break
                target = [row for row in stored if row[1].get("resourceType") == resource_type]
                resource_count += len(target)
                for version_key, resource, resource_pointer in target:
                    if resource_type == "DocumentReference":
                        binary_urls.update(document_binary_urls(resource, connection["fhir_base"]))
                    if store_clinical_item(
                        db,
                        connection_id,
                        version_key,
                        resource,
                        resource_pointer,
                        blob_sha,
                        retrieved,
                    ):
                        new_item_count += 1
                url = next(
                    (
                        link.get("url")
                        for link in document.get("link", [])
                        if link.get("relation") == "next"
                    ),
                    None,
                ) if document.get("resourceType") == "Bundle" else None

            coverage_status = "error" if error_message else ("success" if resource_count else "empty")
            update_coverage(
                db,
                connection_id,
                dataset,
                resource_type,
                coverage_status,
                resource_count,
                utcnow(),
                error_message,
            )
            summary["datasets"][dataset] = {
                "status": coverage_status,
                "resources": resource_count,
                "new_clinical_items": new_item_count,
                "pages": page_number,
            }

        binary_count = 0
        binary_error = None
        for page_number, url in enumerate(sorted(binary_urls), 1):
            retrieved = utcnow()
            status_code, media_type, body = http_get(url, token)
            blob_sha = store_blob(db, repo, body, media_type, retrieved)
            db.execute(
                """
                INSERT INTO sync_pages (
                    sync_run_id, dataset, page_number, request_url,
                    retrieved_at, http_status, blob_sha256
                ) VALUES (?, 'document-binaries', ?, ?, ?, ?, ?)
                """,
                (run_id, page_number, url, retrieved, status_code, blob_sha),
            )
            if not 200 <= status_code < 300:
                binary_error = f"HTTP {status_code}; response blob {blob_sha}"
                failures.append(f"document-binaries: {binary_error}")
                continue
            binary_count += 1
            try:
                store_resources(db, connection_id, run_id, blob_sha, body, retrieved)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass  # Exact non-JSON attachment bytes are already preserved in raw_blobs.
        binary_status = "error" if binary_error else ("success" if binary_count else "empty")
        update_coverage(
            db, connection_id, "document-binaries", "Binary", binary_status,
            binary_count, utcnow(), binary_error,
        )
        summary["datasets"]["document-binaries"] = {
            "status": binary_status,
            "resources": binary_count,
            "new_clinical_items": 0,
            "pages": len(binary_urls),
        }

        completed = utcnow()
        final_status = "partial" if failures else "complete"
        db.execute(
            "UPDATE sync_runs SET completed_at=?, status=?, error=? WHERE sync_run_id=?",
            (completed, final_status, "\n".join(failures) or None, run_id),
        )
        summary["status"] = final_status
        summary["errors"] = failures
    return summary


def reparse(repo: Path, connection_id: str) -> int:
    inserted = 0
    with connect(repo) as db:
        rows = db.execute(
            "SELECT * FROM resources WHERE connection_id=? ORDER BY first_seen_at",
            (connection_id,),
        ).fetchall()
        for row in rows:
            resource = json.loads(row["content_json"])
            inserted += store_clinical_item(
                db,
                connection_id,
                row["resource_version_key"],
                resource,
                row["json_pointer"],
                row["source_blob_sha256"],
                utcnow(),
            )
    return inserted


def status(repo: Path) -> dict[str, Any]:
    with connect(repo) as db:
        latest = db.execute(
            "SELECT sync_run_id FROM sync_runs WHERE completed_at IS NOT NULL ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        stored_coverage = [dict(row) for row in db.execute(
            "SELECT * FROM coverage ORDER BY connection_id, dataset"
        )]
        connections = []
        for row in db.execute("SELECT * FROM connections ORDER BY connection_id"):
            latest_run = db.execute(
                """
                SELECT sync_run_id, started_at, completed_at, status, error
                FROM sync_runs WHERE connection_id=? ORDER BY rowid DESC LIMIT 1
                """,
                (row["connection_id"],),
            ).fetchone()
            connection_coverage = {
                item["dataset"]: item for item in stored_coverage
                if item["connection_id"] == row["connection_id"]
            }
            for dataset, resource_type, _ in (*DATASETS, ("document-binaries", "Binary", {})):
                connection_coverage.setdefault(dataset, {
                    "connection_id": row["connection_id"],
                    "dataset": dataset,
                    "resource_type": resource_type,
                    "status": "not_queried",
                    "item_count": 0,
                    "last_attempt_at": None,
                    "last_success_at": None,
                    "error": None,
                })
            connections.append({
                "connection_id": row["connection_id"],
                "provider": row["provider"],
                "fhir_base": row["fhir_base"],
                "patient_id": row["patient_id"],
                "authorization": {
                    "access": "read-only patient access",
                    "scopes": json.loads(row["authorization_scopes_json"] or "[]"),
                    "scope_status": "recorded" if row["authorized_at"] else "unknown",
                    "fhir_user": row["fhir_user"],
                    "authorized_at": row["authorized_at"],
                    "unattended_refresh": bool(row["dynamic_client_id"] and row["credential_ref"]),
                },
                "latest_refresh": dict(latest_run) if latest_run else None,
                "coverage": sorted(connection_coverage.values(), key=lambda item: item["dataset"]),
            })
        coverage = [item for connection in connections for item in connection["coverage"]]
        return {
            "schema_version": db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0],
            "latest_sync_run_id": latest["sync_run_id"] if latest else None,
            "connections": len(connections),
            "connection_details": connections,
            "sync_runs": db.execute("SELECT COUNT(*) FROM sync_runs").fetchone()[0],
            "raw_blobs": db.execute("SELECT COUNT(*) FROM raw_blobs").fetchone()[0],
            "resource_versions": db.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
            "clinical_items": db.execute("SELECT COUNT(*) FROM clinical_items").fetchone()[0],
            "current_clinical_items": db.execute("SELECT COUNT(*) FROM current_clinical_items").fetchone()[0],
            "coverage": coverage,
        }


def item_summary(kind: str, value: dict[str, Any]) -> str | None:
    if kind in ("lab_result", "vital_sign"):
        quantity = value.get("valueQuantity")
        if isinstance(quantity, dict):
            return f"{quantity.get('value')} {quantity.get('unit', '')}".strip()
        return value.get("valueString")
    if kind in ("medication_order", "medication_dispense"):
        dosages = value.get("dosageInstruction") or []
        return dosages[0].get("text") if dosages and isinstance(dosages[0], dict) else None
    if kind in ("condition_assertion", "allergy_assertion"):
        parts = []
        for field in ("clinicalStatus", "verificationStatus"):
            coding = (value.get(field) or {}).get("coding") or []
            if coding and isinstance(coding[0], dict) and coding[0].get("code"):
                parts.append(coding[0]["code"])
        if kind == "allergy_assertion" and value.get("criticality"):
            parts.append(f"criticality:{value['criticality']}")
        return ", ".join(parts) or None
    if kind == "encounter":
        klass = value.get("class") or {}
        return klass.get("display") or klass.get("code")
    if kind == "care_plan":
        parts = [
            reference.get("display")
            for key in ("addresses", "goal")
            for reference in value.get(key, []) if isinstance(reference, dict)
        ]
        return "; ".join(part.strip() for part in parts if part) or None
    if kind == "clinical_document":
        return value.get("docStatus")
    if kind == "service_request":
        return value.get("intent")
    if kind == "diagnostic_report":
        return value.get("conclusion")
    if kind == "procedure":
        outcome = value.get("outcome") or {}
        return outcome.get("text")
    if kind == "patient_profile":
        return value.get("birthDate")
    return None


def timeline(
    repo: Path,
    kinds: list[str] | None = None,
    query: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM current_clinical_items WHERE 1=1"
    parameters: list[Any] = []
    if kinds:
        sql += f" AND kind IN ({','.join('?' * len(kinds))})"
        parameters += kinds
    if query:
        sql += " AND (display LIKE ? OR code = ?)"
        parameters += [f"%{query}%", query]
    if since:
        sql += " AND COALESCE(effective_start, recorded_at) >= ?"
        parameters.append(since)
    if until:
        sql += " AND COALESCE(effective_start, recorded_at) <= ?"
        parameters.append(until)
    sql += """ ORDER BY (effective_start IS NULL AND recorded_at IS NULL),
               COALESCE(effective_start, recorded_at)"""
    with connect(repo) as db:
        rows = db.execute(sql, parameters).fetchall()
    return [entry_from_row(row) for row in rows]


def entry_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["clinical_item_id"],
        "kind": row["kind"],
        "display": row["display"],
        "summary": item_summary(row["kind"], json.loads(row["value_json"])),
        "status": row["status"],
        "code": row["code"],
        "when": {
            "start": row["effective_start"],
            "end": row["effective_end"],
            "recorded": row["recorded_at"],
            "date_unknown": row["effective_start"] is None and row["recorded_at"] is None,
        },
        "connection": row["connection_id"],
    }


def delta(repo: Path, after_run: str) -> dict[str, Any]:
    """Current clinical items first seen in sync runs after the given one —
    the diff a memory update processes."""
    with connect(repo) as db:
        anchor = db.execute(
            "SELECT rowid FROM sync_runs WHERE sync_run_id=?", (after_run,)
        ).fetchone()
        if not anchor:
            raise SystemExit(f"Unknown sync run: {after_run}")
        latest = db.execute(
            "SELECT sync_run_id FROM sync_runs WHERE completed_at IS NOT NULL ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        rows = db.execute(
            """
            SELECT ci.* FROM current_clinical_items ci
            JOIN resources r ON r.resource_version_key = ci.resource_version_key
            JOIN sync_runs sr ON sr.sync_run_id = r.first_seen_run_id
            WHERE sr.rowid > ?
            ORDER BY sr.rowid
            """,
            (anchor["rowid"],),
        ).fetchall()
    return {
        "after_run": after_run,
        "latest_run": latest["sync_run_id"] if latest else None,
        "new_items": [entry_from_row(row) for row in rows],
    }


def cite(repo: Path, item_id_prefix: str) -> dict[str, Any]:
    """Resolve a clinical item citation back to its exact source evidence."""
    with connect(repo) as db:
        rows = db.execute(
            """
            SELECT ci.*, rb.relative_path
            FROM current_clinical_items ci
            JOIN raw_blobs rb ON rb.sha256 = ci.source_blob_sha256
            WHERE ci.clinical_item_id LIKE ?
            """,
            (f"{item_id_prefix}%",),
        ).fetchall()
    if not rows:
        raise SystemExit(f"No current clinical item matches id prefix {item_id_prefix!r}")
    if len(rows) > 1:
        raise SystemExit(f"Ambiguous id prefix {item_id_prefix!r} ({len(rows)} matches)")
    row = rows[0]
    raw = json.loads((repo / row["relative_path"]).read_bytes())
    evidence = {
        field: {"pointer": ptr, "value": resolve_pointer(raw, ptr)}
        for field, ptr in json.loads(row["evidence_json"]).items()
    }
    return {
        "clinical_item_id": row["clinical_item_id"],
        "kind": row["kind"],
        "display": row["display"],
        "status": row["status"],
        "raw_blob": row["relative_path"],
        "parser_version": row["parser_version"],
        "evidence": evidence,
    }


class _HTMLText(HTMLParser):
    _BLOCKS = {"br", "p", "div", "li", "tr", "td", "h1", "h2", "h3", "h4", "table", "ul", "ol"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _collapse(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def attachment_text(content_type: str | None, data: bytes) -> str:
    """Deterministic plain-text rendering of a stored attachment.

    The raw blob remains the ground truth; this is a readable projection."""
    media = (content_type or "").split(";")[0].strip().lower()
    if media in ("text/html", "application/xhtml+xml"):
        parser = _HTMLText()
        parser.feed(data.decode("utf-8", "replace"))
        return _collapse("".join(parser.parts))
    if media in ("text/rtf", "application/rtf"):
        text = data.decode("latin-1", "replace")
        text = re.sub(r"\{\\\*[^{}]*\}", "", text)
        text = re.sub(r"\\par(?![a-z])", "\n", text)
        text = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
        text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
        return _collapse(text.replace("{", "").replace("}", ""))
    if media in ("application/xml", "text/xml"):
        # ponytail: text nodes only — CDA coded attributes stay in the raw blob;
        # extract displayName/value attributes if a workflow ever needs them
        root = ET.fromstring(data)
        parts = []
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            own = (element.text or "").strip()
            if tag == "title" and own:
                parts.append(f"\n\n# {own}\n")
            elif own:
                parts.append(own + " ")
            if tag in ("br", "paragraph", "item", "tr"):
                parts.append("\n")
            tail = (element.tail or "").strip()
            if tail:
                parts.append(tail + " ")
        return _collapse("".join(parts))
    return _collapse(data.decode("utf-8", "replace"))


def document(repo: Path, item_id_prefix: str) -> dict[str, Any]:
    """Render a clinical document's stored attachments as cited plain text."""
    with connect(repo) as db:
        rows = db.execute(
            """
            SELECT * FROM current_clinical_items
            WHERE kind='clinical_document' AND clinical_item_id LIKE ?
            """,
            (f"{item_id_prefix}%",),
        ).fetchall()
        if not rows:
            raise SystemExit(f"No current clinical document matches id prefix {item_id_prefix!r}")
        if len(rows) > 1:
            raise SystemExit(f"Ambiguous id prefix {item_id_prefix!r} ({len(rows)} matches)")
        row = rows[0]
        fhir_base = db.execute(
            "SELECT fhir_base FROM connections WHERE connection_id=?",
            (row["connection_id"],),
        ).fetchone()[0]
        value = json.loads(row["value_json"])
        attachments = []
        for content in value.get("content", []):
            attachment = (content or {}).get("attachment") or {}
            content_type = attachment.get("contentType")
            data_bytes, blob_path = None, None
            if attachment.get("url"):
                absolute = urllib.parse.urljoin(f"{fhir_base.rstrip('/')}/", attachment["url"])
                page = db.execute(
                    """
                    SELECT rb.relative_path, rb.media_type
                    FROM sync_pages sp JOIN raw_blobs rb ON rb.sha256=sp.blob_sha256
                    WHERE sp.request_url=? AND sp.http_status BETWEEN 200 AND 299
                    ORDER BY sp.retrieved_at DESC, sp.rowid DESC LIMIT 1
                    """,
                    (absolute,),
                ).fetchone()
                if page:
                    raw = (repo / page["relative_path"]).read_bytes()
                    blob_path = page["relative_path"]
                    data_bytes = raw
                    if "json" in page["media_type"]:
                        try:
                            binary = json.loads(raw)
                        except json.JSONDecodeError:
                            binary = None
                        if isinstance(binary, dict) and binary.get("resourceType") == "Binary":
                            content_type = binary.get("contentType") or content_type
                            data_bytes = base64.b64decode(binary.get("data") or "")
            elif attachment.get("data"):
                data_bytes = base64.b64decode(attachment["data"])
            attachments.append({
                "content_type": content_type,
                "url": attachment.get("url"),
                "blob": blob_path,
                "fetched": data_bytes is not None,
                "text": attachment_text(content_type, data_bytes) if data_bytes is not None else None,
            })
    return {
        "clinical_item_id": row["clinical_item_id"],
        "display": row["display"],
        "date": row["effective_start"] or row["recorded_at"],
        "status": row["status"],
        "doc_status": value.get("docStatus"),
        "connection": row["connection_id"],
        "attachments": attachments,
    }


def record_report(
    repo: Path,
    reporter_role: str,
    statement: str,
    subject: str | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    """Preserve an explicit patient/caregiver statement as a local source."""
    if not database_path(repo).is_file():
        raise SystemExit(f"No health repository at {repo}")
    if not reporter_role.strip() or not statement.strip():
        raise SystemExit("Reporter role and statement must not be empty")
    sources = repo / "memory" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    if supersedes:
        if not re.fullmatch(r"[0-9a-fA-F]{6,32}", supersedes):
            raise SystemExit("Superseded report id must be a 6-32 character hex prefix")
        matches = list(sources.glob(f"{supersedes}*.json"))
        if len(matches) != 1:
            raise SystemExit(f"Superseded report prefix must resolve once; found {len(matches)}")
        supersedes = matches[0].stem
    report = {
        "id": uuid.uuid4().hex,
        "recorded_at": utcnow(),
        "reporter_role": reporter_role.strip(),
        "subject": subject.strip() if subject else None,
        "statement": statement.strip(),
        "supersedes": supersedes,
    }
    destination = sources / f"{report['id']}.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    os.replace(temporary, destination)
    return report


def verify(repo: Path) -> dict[str, Any]:
    """Verify clinical evidence pointers and durable-memory citations."""
    resolved, dangling = 0, []
    with connect(repo) as db:
        rows = db.execute(
            """
            SELECT ci.clinical_item_id, ci.kind, ci.display, ci.evidence_json, rb.relative_path
            FROM current_clinical_items ci
            JOIN raw_blobs rb ON rb.sha256 = ci.source_blob_sha256
            """
        ).fetchall()
    for row in rows:
        raw = json.loads((repo / row["relative_path"]).read_bytes())
        for field, ptr in json.loads(row["evidence_json"]).items():
            try:
                resolve_pointer(raw, ptr)
                resolved += 1
            except (KeyError, IndexError, ValueError):
                dangling.append(
                    {"clinical_item_id": row["clinical_item_id"], "kind": row["kind"],
                     "display": row["display"], "field": field, "pointer": ptr}
                )
    memory_citations: dict[str, Any] = {"checked": 0, "reports_checked": 0, "bad": []}
    memory_dir = repo / "memory"
    if memory_dir.is_dir():
        with connect(repo) as db:
            ids = [r[0] for r in db.execute("SELECT clinical_item_id FROM current_clinical_items")]
        reports: dict[str, dict[str, Any]] = {}
        for source in sorted((memory_dir / "sources").glob("*.json")):
            try:
                payload = json.loads(source.read_text())
            except (OSError, json.JSONDecodeError) as error:
                memory_citations["bad"].append({"file": str(source.relative_to(memory_dir)), "error": str(error)})
                continue
            required = ("id", "recorded_at", "reporter_role", "statement")
            if not isinstance(payload, dict) or any(not payload.get(field) for field in required):
                memory_citations["bad"].append({
                    "file": str(source.relative_to(memory_dir)),
                    "error": f"report source requires {', '.join(required)}",
                })
                continue
            if payload["id"] != source.stem:
                memory_citations["bad"].append({
                    "file": str(source.relative_to(memory_dir)),
                    "error": "report id must match filename",
                })
                continue
            reports[payload["id"]] = payload
        for report_id, payload in reports.items():
            supersedes = payload.get("supersedes")
            if supersedes and supersedes not in reports:
                memory_citations["bad"].append({
                    "file": f"sources/{report_id}.json",
                    "error": f"superseded report does not exist: {supersedes}",
                })
        artifacts_dir = repo / "artifacts"
        cited_files = sorted(memory_dir.glob("*.md"))
        if artifacts_dir.is_dir():
            cited_files += sorted(artifacts_dir.glob("*.md"))
        for md_file in cited_files:
            for prefix in re.findall(r"\[ci:([0-9a-fA-F]{6,64})\]", md_file.read_text()):
                matches = [i for i in ids if i.startswith(prefix.lower())]
                if len(matches) == 1:
                    memory_citations["checked"] += 1
                else:
                    memory_citations["bad"].append(
                        {"file": md_file.name, "citation": prefix, "matches": len(matches)}
                    )
            for prefix in re.findall(r"\[report:([0-9a-fA-F]{6,64})\]", md_file.read_text()):
                matches = [report_id for report_id in reports if report_id.startswith(prefix.lower())]
                if len(matches) == 1:
                    memory_citations["reports_checked"] += 1
                else:
                    memory_citations["bad"].append(
                        {"file": md_file.name, "report": prefix, "matches": len(matches)}
                    )
    return {
        "items": len(rows),
        "pointers_resolved": resolved,
        "dangling": dangling,
        "memory_citations": memory_citations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--repo", type=Path, required=True)
    init_parser.add_argument("--connection", required=True)
    init_parser.add_argument("--provider", required=True)
    init_parser.add_argument("--fhir-base", required=True)
    init_parser.add_argument("--patient-id", required=True)
    init_parser.add_argument("--token-endpoint")
    init_parser.add_argument("--scope", action="append", default=[])
    init_parser.add_argument("--fhir-user")

    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--repo", type=Path, required=True)
    sync_parser.add_argument("--connection", required=True)
    sync_parser.add_argument("--token-env", default="HEALTH_OS_ACCESS_TOKEN")

    parse_parser = subparsers.add_parser("parse")
    parse_parser.add_argument("--repo", type=Path, required=True)
    parse_parser.add_argument("--connection", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--repo", type=Path, required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--repo", type=Path, required=True)

    timeline_parser = subparsers.add_parser("timeline")
    timeline_parser.add_argument("--repo", type=Path, required=True)
    timeline_parser.add_argument("--kind", action="append", help="Filter by item kind (repeatable)")
    timeline_parser.add_argument("--query", help="Substring match on display, or exact code")
    timeline_parser.add_argument("--since", help="ISO date lower bound")
    timeline_parser.add_argument("--until", help="ISO date upper bound")

    cite_parser = subparsers.add_parser("cite")
    cite_parser.add_argument("--repo", type=Path, required=True)
    cite_parser.add_argument("item_id", help="Clinical item id (prefix allowed)")

    document_parser = subparsers.add_parser("document")
    document_parser.add_argument("--repo", type=Path, required=True)
    document_parser.add_argument("item_id", help="Clinical document item id (prefix allowed)")

    delta_parser = subparsers.add_parser("delta")
    delta_parser.add_argument("--repo", type=Path, required=True)
    delta_parser.add_argument("--after", required=True, help="Sync run id the memory is current through")

    report_parser = subparsers.add_parser("record-report")
    report_parser.add_argument("--repo", type=Path, required=True)
    report_parser.add_argument("--reporter-role", required=True)
    report_parser.add_argument("--statement", required=True)
    report_parser.add_argument("--subject")
    report_parser.add_argument("--supersedes", help="Prior report id prefix corrected by this report")

    args = parser.parse_args()
    if args.command == "init":
        initialize(
            args.repo, args.connection, args.provider, args.fhir_base, args.patient_id,
            args.token_endpoint, args.scope, args.fhir_user,
        )
        print(json.dumps(status(args.repo), indent=2))
    elif args.command == "sync":
        token = os.environ.get(args.token_env)
        if not token:
            sys.exit(f"Missing access token in environment variable {args.token_env}")
        print(json.dumps(sync(args.repo, args.connection, token), indent=2))
    elif args.command == "parse":
        print(json.dumps({"new_clinical_items": reparse(args.repo, args.connection)}, indent=2))
    elif args.command == "status":
        print(json.dumps(status(args.repo), indent=2))
    elif args.command == "verify":
        report = verify(args.repo)
        print(json.dumps(report, indent=2))
        if report["dangling"] or report["memory_citations"]["bad"]:
            sys.exit(1)
    elif args.command == "delta":
        print(json.dumps(delta(args.repo, args.after), indent=2))
    elif args.command == "timeline":
        print(json.dumps(timeline(args.repo, args.kind, args.query, args.since, args.until), indent=2))
    elif args.command == "cite":
        print(json.dumps(cite(args.repo, args.item_id), indent=2))
    elif args.command == "document":
        print(json.dumps(document(args.repo, args.item_id), indent=2))
    elif args.command == "record-report":
        print(json.dumps(record_report(
            args.repo, args.reporter_role, args.statement, args.subject, args.supersedes,
        ), indent=2))


if __name__ == "__main__":
    main()
