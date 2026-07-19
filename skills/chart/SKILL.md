---
name: chart
description: Consult the user's health chart — answer questions about imported health records from the local core, oriented by persistent memory when it exists. Use for health history, lab trends, medication orders or fills, allergies, conditions, care plans, documents, procedures, changes over time, or source inspection. Cite every recorded fact to a clinical item and every mentioned patient/caregiver report to its report source.
---

# Chart

Use this skill to consult the user's local health record and answer questions from
it. The record is the source of truth; you are a presenter, not an author. You never
write to the health database.

## Start Here

1. Resolve the plugin root without assuming a runtime: use `$PLUGIN_ROOT` when
   available (Codex), then `$CLAUDE_PLUGIN_ROOT` (Claude), otherwise locate the
   nearest parent of this skill or the working directory containing
   `.codex-plugin/plugin.json` or `.claude-plugin/plugin.json`. Confirm
   `<plugin-root>/core/health_core.py` exists; never guess a path.
2. Resolve the data repo: `$HEALTH_OS_REPO` if set, else `~/health-data` if it
   exists. If neither exists, stop and help the user connect a health system.
   Never silently use bundled or sandbox data.
3. Before the first record access in a task, explain that selected local record
   context will be processed by the active agent runtime and follow its configured
   data policy. Do not read the record if the user declines.
4. Before presenting anything, read `references/grounding_rules.md`.
5. If `<repo>/memory/` exists, read `memory/manifest.json` and the relevant memory
   files first — they are the consolidated, cited working context; start from them
   without treating them as a replacement for evidence. If `synced_through_run` in the
   manifest differs from `latest_sync_run_id` in `status`, tell the user the memory
   is stale and suggest running the memory skill. Memory orients; specifics are
   still grounded through `timeline`/`cite` queries.
6. Report coverage first: run `status --repo <repo>` and state which connections and
   datasets the record covers, last sync times, and any `not_queried`, `error`, or
   `empty` datasets.
   Completeness is never assumed — name gaps relevant to the question.
7. Query with filters via `timeline --repo <repo>`; don't dump the whole record:
   - `--kind patient_profile|lab_result|vital_sign|medication_order|medication_dispense|condition_assertion|allergy_assertion|encounter|care_plan|clinical_document|service_request|diagnostic_report|procedure` (repeatable)
   - `--query <text>` — substring on display name, or exact code (e.g. LOINC `2160-0`)
   - `--since` / `--until` — ISO date bounds
8. Produce the view using `references/output_format.md`. Every factual line carries a
   `[ci:<first 12 chars of item id>]` citation.
9. When the user questions a fact, resolve the citation with
   `cite --repo <repo> <id-prefix>` — it returns the exact field pointers, values,
   and raw source bytes behind the item.
10. To read a note, imaging narrative, or encounter/patient summary, run
   `document --repo <repo> <id-prefix>` on a `clinical_document` item — it renders
   the stored attachment (HTML, RTF, or C-CDA XML) as plain text. Facts you quote
   from it cite that document's `[ci:…]`. The rendering is a projection; if wording
   is disputed, the raw blob is the ground truth.

Script examples:

```bash
python3 core/health_core.py status --repo ~/health-data
python3 core/health_core.py timeline --repo ~/health-data --kind lab_result --query 2160-0 --since 2023-01-01
python3 core/health_core.py cite --repo ~/health-data c906417c572e
```

## Principles

- Recorded facts come from clinical items. Patient/caregiver reports come from
  immutable report sources. Anything else inferred is labeled interpretation.
- Cite exact items or reports; never blur provenance. No uncited factual lines.
- Time is first-class: unknown dates stay unknown, never guessed or interpolated.
- Gaps are findings. A silent period may be an uncaptured one — say which is likely
  given known coverage.
- If the core CLI fails (missing repo, no database), stop and help the user run
  setup (`core/connect.py connect`) rather than answering from memory.

## Bundled Resources

- `references/grounding_rules.md`: contract rules for presenting clinical items.
- `references/output_format.md`: the timeline output shape.
