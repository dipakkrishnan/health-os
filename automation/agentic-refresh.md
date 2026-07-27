# Health OS recurring refresh

This is an owner-approved local automation. Use the exact paths and interpreter
listed below. The automation is installed only after the user has approved model
access to this local record.

Before accessing the record, read `skills/refresh/SKILL.md`,
`skills/memory/SKILL.md`, and `skills/memory/references/memory_format.md` under the
installed plugin root listed below. Follow their current command and grounding rules.

1. Read `memory/manifest.json`, then run Health OS `status`. Resync every connection
   that reports unattended refresh support. Never start interactive authorization.
2. Verify the repository even if a connection fails. Keep prior data intact and
   treat failures as coverage gaps.
3. Run `delta` from the manifest's prior `synced_through_run`. Update only affected
   memory views, preserve unresolved conflicts, advance the manifest to the latest
   completed run, and verify every citation. Recorded evidence uses `[ci:...]`;
   patient and caregiver claims remain separately attributed `[report:...]`.
4. If something actionable changed, write a compact brief under `artifacts/` with
   the change, why it matters, evidence citations, and the next owner or question.
   If nothing actionable changed, do not create an artifact and reply exactly
   `Nothing actionable changed`.

Do not turn an order into confirmed use, overwrite a patient or caregiver report
with inference, contact anyone, change care, record inferred reports, or disclose
record content. If the manifest is missing or invalid, stop and request an
interactive memory rebuild instead of guessing.
