# Health OS Core Data Contract — v1

This directory is the deterministic data layer. Skills may read it, but should not
write its database tables directly.

## Trust boundary

```text
FHIR HTTP response (exact bytes)
    -> raw_blobs + sync_pages
    -> versioned FHIR resources
    -> regenerable clinical_items
    -> skill-owned timelines, case packets, and reviews
```

- `raw_blobs` are immutable and content-addressed.
- `sync_pages` record which exact response was observed during a sync.
- `resources` retain every distinct content version of a FHIR resource.
- `clinical_items` are deterministic, regenerable indexes over resources.
- Timelines and agent interpretations are downstream views, not source evidence.

## Identity

- A FHIR resource's `logical_key` is `{connection}/{resourceType}/{id}`.
- A `resource_version_key` adds the resource content hash. A changed resource is
  therefore appended rather than overwriting its prior version.
- Exactly one stored version of each logical resource has `is_current = 1`.
  Skills should read `current_clinical_items`; `clinical_items` is the audit history.
- A `clinical_item_id` is derived from its resource version, item kind, and parser
  version. Repeating the same sync cannot duplicate it.

## Provenance

Every clinical item carries:

- the exact raw response blob hash;
- the JSON pointer to the containing FHIR resource;
- pointers to the fields used for its code, value, and time;
- the deterministic parser version.

Grounding means that these pointers resolve. It does not mean that an upstream
clinical record is complete or correct.

## Clinical semantics

The parser supports the first-refresh evidence surface:

- `Patient` -> `patient_profile`;
- laboratory `Observation` -> `lab_result`;
- vital-sign `Observation` -> `vital_sign`;
- `MedicationRequest` -> `medication_order`;
- `MedicationDispense` -> `medication_dispense`;
- `Condition` -> `condition_assertion`;
- `AllergyIntolerance` -> `allergy_assertion`;
- `Encounter` -> `encounter`;
- `Appointment` -> `appointment`;
- `DocumentReference` -> `clinical_document`, with same-origin `Binary` content preserved;
- `ServiceRequest` -> `service_request`;
- `DiagnosticReport` -> `diagnostic_report`;
- `Procedure` -> `procedure`.

A medication order is never promoted to confirmed medication use. A condition or
allergy is an assertion with its original verification/status fields preserved.

## Secrets

OAuth tokens and private keys are not stored in `health.sqlite` or `raw/`.
Connections store only a `credential_ref` suitable for an OS keychain adapter.
The sandbox auth helper can use a chmod-0600 key file for development only.

## Skill-facing read boundary

The stable starting point for downstream skills is the read-only SQLite view
`current_clinical_items`. Join through `resource_version_key` to `resources` for
the normalized source resource, or through `source_blob_sha256` to `raw_blobs`
for the exact HTTP response bytes. Skills must not treat historical rows in
`clinical_items` as simultaneous current facts.
