---
name: timeline
description: Build a grounded chronological view of the user's health record from the local health core. Use when the user asks about their health history, a lab trend, medication history, "what happened when", changes over time, or wants a timeline of conditions, encounters, or results. Every statement of fact must cite a clinical item id.
---

# Health Timeline

Use this skill to present the user's local health record as a grounded chronological
view. The record is the source of truth; you are a presenter, not an author. You
never write to the health database.

## Start Here

1. Resolve the core CLI: `${CLAUDE_PLUGIN_ROOT}/core/health_core.py` when running as
   an installed plugin, else `core/health_core.py` from the project root.
2. Resolve the data repo: `$HEALTH_OS_REPO` if set, else `~/health-data` if it
   exists, else `spike/health-data` (sandbox) in the project.
3. Before presenting anything, read `references/grounding_rules.md`.
4. Report coverage first: run `status --repo <repo>` and state which connections and
   datasets the record covers, last sync times, and any `error`/`empty` datasets.
   Completeness is never assumed — name gaps relevant to the question.
5. Query with filters via `timeline --repo <repo>`; don't dump the whole record:
   - `--kind lab_result|medication_order|condition_assertion|allergy_assertion|encounter` (repeatable)
   - `--query <text>` — substring on display name, or exact code (e.g. LOINC `2160-0`)
   - `--since` / `--until` — ISO date bounds
6. Produce the view using `references/output_format.md`. Every factual line carries a
   `[ci:<first 12 chars of item id>]` citation.
7. When the user questions a fact, resolve the citation with
   `cite --repo <repo> <id-prefix>` — it returns the exact field pointers, values,
   and raw source bytes behind the item.

Script examples:

```bash
python3 core/health_core.py status --repo ~/health-data
python3 core/health_core.py timeline --repo ~/health-data --kind lab_result --query 2160-0 --since 2023-01-01
python3 core/health_core.py cite --repo ~/health-data c906417c572e
```

## Principles

- Facts come from clinical items; anything you infer is interpretation and is
  presented separately, clearly labeled.
- Cite exact items, never paraphrase provenance. No uncited factual lines.
- Time is first-class: unknown dates stay unknown, never guessed or interpolated.
- Gaps are findings. A silent period may be an uncaptured one — say which is likely
  given known coverage.
- If the core CLI fails (missing repo, no database), stop and help the user run
  setup (`core/connect.py connect`) rather than answering from memory.

## Bundled Resources

- `references/grounding_rules.md`: contract rules for presenting clinical items.
- `references/output_format.md`: the timeline output shape.
