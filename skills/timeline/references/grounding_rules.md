# Grounding rules

These follow from the health core contract (`core/CONTRACT.md`). They are not
stylistic preferences; violating them turns derived interpretation into fake fact.

## Orders are not use

A `medication_order` proves a prescription was authored, not that the medication was
taken. Say "ordered" or "prescribed", never "was taking", unless a patient-reported
item states actual use.

## Assertions keep their status

Conditions and allergies carry `clinicalStatus` and `verificationStatus`. A
`resolved`, `inactive`, or `unconfirmed` assertion must be presented with that
status. Epic placeholder entries such as "Not on File" mean *nothing documented* —
never present them as findings.

## Unknown time is unknown

Items with `date_unknown: true` go in a separate "Undated" section. Never guess,
interpolate, or silently order them among dated entries.

## Interpretation is labeled

Trends, connections, and hypotheses you infer go under a heading that marks them as
derived ("Interpretation (not in record)"), visually separate from grounded entries.
Never state numeric claims the record does not contain.

## Gaps are findings

A period with no items may mean nothing happened OR nothing was captured. Check the
coverage table: datasets never synced (today: vitals, notes, procedures,
immunizations, imaging) and date ranges before a connection's history are gaps, not
evidence of absence.

## Citations resolve

Every factual line ends with `[ci:<first 12 chars of clinical_item_id>]`. A citation
you cannot resolve with `cite` must not appear. Multiple items may back one line.
