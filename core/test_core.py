#!/usr/bin/env python3

import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import epic_auth
import health_core
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


PATIENT_ID = "sandbox-patient"


def bundle(resource):
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"fullUrl": f"urn:test:{resource['id']}", "resource": resource}],
    }


RESPONSES = {
    "/Patient/": {
        "resourceType": "Patient",
        "id": PATIENT_ID,
        "name": [{"text": "Sandbox Patient"}],
    },
    "category=laboratory": bundle(
        {
            "resourceType": "Observation",
            "id": "lab-1",
            "status": "final",
            "category": [{"coding": [{"code": "laboratory"}]}],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "2160-0",
                        "display": "Creatinine",
                    }
                ]
            },
            "effectiveDateTime": "2026-07-01T09:00:00Z",
            "issued": "2026-07-01T10:00:00Z",
            "valueQuantity": {"value": 1.42, "unit": "mg/dL"},
        }
    ),
    "category=vital-signs": bundle(
        {
            "resourceType": "Observation",
            "id": "vital-1",
            "status": "final",
            "category": [{"coding": [{"code": "vital-signs"}]}],
            "code": {"coding": [{"code": "8480-6", "display": "Systolic blood pressure"}]},
            "effectiveDateTime": "2026-07-01T09:05:00Z",
            "valueQuantity": {"value": 128, "unit": "mmHg"},
        }
    ),
    "/MedicationRequest?": bundle(
        {
            "resourceType": "MedicationRequest",
            "id": "med-1",
            "status": "active",
            "intent": "order",
            "authoredOn": "2026-06-20",
            "medicationCodeableConcept": {"text": "Tacrolimus 1 mg capsule"},
            "dosageInstruction": [{"text": "Take 1 mg twice daily"}],
        }
    ),
    "/MedicationDispense?": bundle(
        {
            "resourceType": "MedicationDispense",
            "id": "dispense-1",
            "status": "completed",
            "medicationCodeableConcept": {"text": "Tacrolimus 1 mg capsule"},
            "whenHandedOver": "2026-06-21",
            "quantity": {"value": 60, "unit": "capsule"},
            "daysSupply": {"value": 30, "unit": "day"},
        }
    ),
    "/Condition?": bundle(
        {
            "resourceType": "Condition",
            "id": "condition-1",
            "code": {"text": "Kidney transplant status"},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "verificationStatus": {"coding": [{"code": "confirmed"}]},
            "recordedDate": "2020-03-10",
        }
    ),
    "/AllergyIntolerance?": bundle(
        {
            "resourceType": "AllergyIntolerance",
            "id": "allergy-1",
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "verificationStatus": {"coding": [{"code": "confirmed"}]},
            "code": {"text": "Penicillin"},
            "recordedDate": "2018-02-01",
            "reaction": [{"manifestation": [{"text": "Rash"}]}],
        }
    ),
    "/Encounter?": bundle(
        {
            "resourceType": "Encounter",
            "id": "encounter-1",
            "status": "finished",
            "class": {"code": "AMB", "display": "ambulatory"},
            "type": [{"text": "Transplant follow-up"}],
            "period": {
                "start": "2026-07-01T08:30:00Z",
                "end": "2026-07-01T09:30:00Z",
            },
        }
    ),
    "/Appointment?": bundle(
        {
            "resourceType": "Appointment",
            "id": "appointment-1",
            "status": "booked",
            "description": "Transplant follow-up",
            "start": "2026-08-01T08:30:00Z",
            "end": "2026-08-01T09:00:00Z",
            "participant": [{"actor": {"display": "Transplant Clinic"}, "status": "accepted"}],
        }
    ),
    "/DocumentReference?": bundle(
        {
            "resourceType": "DocumentReference",
            "id": "note-1",
            "status": "current",
            "docStatus": "final",
            "date": "2026-07-01T10:00:00Z",
            "type": {"text": "Progress note"},
            "content": [{"attachment": {
                "contentType": "text/plain",
                "url": "https://example.test/FHIR/R4/Binary/note-1",
            }}],
        }
    ),
    "/Binary/note-1": {
        "resourceType": "Binary",
        "id": "note-1",
        "contentType": "text/plain",
        "data": "VGFjcm9saW11cyBkb3NlIHVuY2hhbmdlZC4=",
    },
    "/ServiceRequest?": bundle(
        {
            "resourceType": "ServiceRequest",
            "id": "request-1",
            "status": "active",
            "intent": "order",
            "code": {"text": "Basic metabolic panel"},
            "authoredOn": "2026-07-01",
            "occurrenceDateTime": "2026-07-20",
            "requester": {"display": "Transplant Clinic"},
        }
    ),
    "/DiagnosticReport?": bundle(
        {
            "resourceType": "DiagnosticReport",
            "id": "report-1",
            "status": "final",
            "code": {"text": "Renal function report"},
            "effectiveDateTime": "2026-07-01T09:00:00Z",
            "issued": "2026-07-01T10:00:00Z",
            "conclusion": "Stable renal function",
        }
    ),
    "/Procedure?": bundle(
        {
            "resourceType": "Procedure",
            "id": "procedure-1",
            "status": "completed",
            "code": {"text": "Kidney transplant"},
            "performedDateTime": "2020-03-10",
        }
    ),
}


def fake_get(url, _token):
    for marker, document in RESPONSES.items():
        if marker in url:
            return 200, "application/fhir+json", json.dumps(document, separators=(",", ":")).encode()
    raise AssertionError(f"Unexpected URL: {url}")


def resolve_pointer(document, pointer):
    value = document
    if not pointer:
        return value
    for component in pointer.lstrip("/").split("/"):
        value = value[int(component)] if isinstance(value, list) else value[component]
    return value


class CoreTest(unittest.TestCase):
    def test_sync_is_idempotent_and_provenance_resolves(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            health_core.initialize(
                repo,
                "epic-sandbox",
                "Epic sandbox",
                "https://example.test/FHIR/R4",
                PATIENT_ID,
                authorization_scopes=["patient/*.read", "openid"],
                fhir_user="Patient/sandbox-patient",
            )
            with patch.object(health_core, "http_get", fake_get):
                first = health_core.sync(repo, "epic-sandbox", "test-token")
                second = health_core.sync(repo, "epic-sandbox", "test-token")

            updated_responses = copy.deepcopy(RESPONSES)
            updated_responses["category=laboratory"]["entry"][0]["resource"]["valueQuantity"]["value"] = 1.50

            def updated_get(url, _token):
                for marker, document in updated_responses.items():
                    if marker in url:
                        return 200, "application/fhir+json", json.dumps(document, separators=(",", ":")).encode()
                raise AssertionError(f"Unexpected URL: {url}")

            with patch.object(health_core, "http_get", updated_get):
                third = health_core.sync(repo, "epic-sandbox", "test-token")

            self.assertEqual(first["status"], "complete")
            self.assertEqual(second["status"], "complete")
            self.assertEqual(sum(row["new_clinical_items"] for row in first["datasets"].values()), 13)
            self.assertEqual(sum(row["new_clinical_items"] for row in second["datasets"].values()), 0)
            self.assertEqual(sum(row["new_clinical_items"] for row in third["datasets"].values()), 1)

            current = health_core.status(repo)
            self.assertEqual(current["sync_runs"], 3)
            self.assertEqual(current["resource_versions"], 15)
            self.assertEqual(current["clinical_items"], 14)
            self.assertEqual(current["current_clinical_items"], 13)
            self.assertEqual(current["connection_details"][0]["provider"], "Epic sandbox")
            self.assertEqual(
                current["connection_details"][0]["authorization"]["scopes"],
                ["openid", "patient/*.read"],
            )
            self.assertEqual(current["connection_details"][0]["latest_refresh"]["status"], "complete")
            self.assertEqual(
                {row["dataset"] for row in current["connection_details"][0]["coverage"]},
                {dataset for dataset, _, _ in health_core.DATASETS} | {"document-binaries"},
            )

            with health_core.connect(repo) as db:
                rows = db.execute(
                    """
                    SELECT ci.*, rb.relative_path, r.resource_id
                    FROM clinical_items ci
                    JOIN raw_blobs rb ON rb.sha256=ci.source_blob_sha256
                    JOIN resources r ON r.resource_version_key=ci.resource_version_key
                    """
                ).fetchall()
                self.assertEqual({row["kind"] for row in rows}, {
                    "patient_profile", "lab_result", "vital_sign", "medication_order",
                    "medication_dispense", "condition_assertion", "allergy_assertion",
                    "encounter", "appointment", "clinical_document", "service_request",
                    "diagnostic_report", "procedure",
                })
                for row in rows:
                    raw = json.loads((repo / row["relative_path"]).read_bytes())
                    resource_pointer = json.loads(row["evidence_json"])["resource"]
                    resource = resolve_pointer(raw, resource_pointer)
                    self.assertEqual(resource["id"], row["resource_id"])
                current_lab = db.execute(
                    "SELECT value_json FROM current_clinical_items WHERE kind='lab_result'"
                ).fetchone()
                self.assertEqual(json.loads(current_lab["value_json"])["valueQuantity"]["value"], 1.50)

            entries = health_core.timeline(repo)
            self.assertEqual(len(entries), 13)
            dated = [e["when"]["start"] or e["when"]["recorded"] for e in entries if not e["when"]["date_unknown"]]
            self.assertEqual(dated, sorted(dated))
            lab = next(e for e in entries if e["kind"] == "lab_result")
            self.assertEqual(lab["summary"], "1.5 mg/dL")
            citation = health_core.cite(repo, lab["id"][:12])
            self.assertEqual(citation["evidence"]["value"]["value"]["value"], 1.5)
            self.assertEqual(citation["evidence"]["time"]["value"], "2026-07-01T09:00:00Z")

            changes = health_core.delta(repo, first["sync_run_id"])
            self.assertEqual(changes["latest_run"], third["sync_run_id"])
            self.assertEqual([e["kind"] for e in changes["new_items"]], ["lab_result"])
            self.assertEqual(changes["new_items"][0]["summary"], "1.5 mg/dL")

            memory_dir = repo / "memory"
            memory_dir.mkdir()
            (memory_dir / "timeline.md").write_text(
                f"- Creatinine 1.5 mg/dL [ci:{lab['id'][:12]}]\n- bogus [ci:deadbeef0000]\n"
            )
            report = health_core.verify(repo)
            self.assertEqual(report["memory_citations"]["checked"], 1)
            self.assertEqual(len(report["memory_citations"]["bad"]), 1)
            self.assertEqual(report["memory_citations"]["bad"][0]["citation"], "deadbeef0000")

    def test_dynamic_key_and_assertion(self):
        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "epic.pem"
            jwk = epic_auth.generate_key(key_path)
            token = epic_auth.signed_assertion(
                "dynamic-client",
                "https://example.test/oauth2/token",
                key_path,
                now=1_700_000_000,
            )
            encoded_header, encoded_claims, encoded_signature = token.split(".")
            claims = json.loads(base64.urlsafe_b64decode(encoded_claims + "=="))
            self.assertEqual(claims["iss"], "dynamic-client")
            self.assertEqual(claims["exp"] - claims["iat"], 300)
            self.assertEqual(jwk["kty"], "RSA")
            epic_auth.load_key(key_path).public_key().verify(
                base64.urlsafe_b64decode(encoded_signature + "=="),
                f"{encoded_header}.{encoded_claims}".encode(),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            self.assertEqual(key_path.stat().st_mode & 0o777, 0o600)

    def test_registration_endpoint_discovery(self):
        capability = {
            "rest": [{
                "security": {
                    "extension": [{
                        "url": "oauth-uris",
                        "extension": [
                            {"url": "token", "valueUri": "https://example.test/token"},
                            {"url": "register", "valueUri": "https://example.test/register"},
                        ],
                    }]
                }
            }]
        }
        self.assertEqual(
            epic_auth.find_oauth_uri(capability, "register"),
            "https://example.test/register",
        )


if __name__ == "__main__":
    unittest.main()
