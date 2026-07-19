---
name: memory
description: Build and maintain the user's durable, cited health context across recorded evidence, clinical intent, and lived reality. Use after record refreshes, when memory is missing or stale, when the patient or caregiver confirms or corrects something, or when another health workflow needs the current care plan, conflicts, coverage, or upcoming appointments.
---

# Health Memory

Maintain `memory/` inside the user's data repo as a reconciled working context. The
FHIR database is authoritative only for what source systems recorded. Explicit
patient and caregiver reports are separate local sources. Memory views bring those
sources together without pretending they agree.

## Resolve the environment

1. Resolve the plugin root without assuming a runtime: use `$PLUGIN_ROOT` when
   available (Codex), then `$CLAUDE_PLUGIN_ROOT` (Claude), otherwise locate the
   nearest parent of this skill or the working directory containing
   `.codex-plugin/plugin.json` or `.claude-plugin/plugin.json`. Confirm
   `<plugin-root>/core/health_core.py` exists; never guess a path.
2. Resolve the data repo from `$HEALTH_OS_REPO`, then `~/health-data`. If neither
   exists, stop and help the user connect a health system. Never use sandbox data.
3. Before the first record access in a task, explain that selected local context
   will be processed by the active agent runtime and follow its configured data
   policy. Stop if the user declines.
4. Read `references/memory_format.md` completely before writing memory.

## Preserve the three truths

- **Recorded evidence:** describe only what the imported source establishes and cite
  `[ci:<id>]` on every claim.
- **Clinical intent:** cite the note, order, or message expressing it. Label intent
  reconstructed from several sources as interpretation.
- **Lived reality:** use only an explicit patient or caregiver statement preserved
  with `record-report`; cite it as `[report:<id>]` and name the reporter role.

Never convert an order or dispense into confirmed use. Never infer clinical intent
from a diagnosis code alone. Never treat an empty or successful query as proof that
nothing happened.

## Update memory

1. Run `status --repo <repo>`. Read every connection's latest refresh, permissions,
   and coverage. `not_queried`, `error`, and missing systems remain visible gaps.
2. Read `memory/manifest.json` and the relevant views if present.
3. Choose the path:
   - **No manifest:** query the record by domain, create the version 2 views from
     `memory_format.md`, and set the watermark from `latest_sync_run_id`.
   - **Version 1 manifest:** preserve existing files, split `gaps.md` into coverage
     and conflicts, add the new views, and upgrade only after reviewing each line's
     truth category.
   - **Version 2 manifest:** run `delta --repo <repo> --after <synced_through_run>`
     and process only new current items.
4. For every new item, ask which existing understanding it confirms, changes, or
   contradicts. Update the affected view; do not merely append another assertion.
5. A record change may alter recorded evidence or reveal a possible conflict. It
   does not overwrite a patient report or prove that the operational plan changed.
6. Put unresolved disagreements in `conflicts.md` with evidence for each side, the
   coverage limitation, and the smallest question that could resolve the conflict.
7. Write `manifest.json` with the latest completed run and `memory_version: 2`.
8. Finish with `verify --repo <repo>`. Fix every dangling clinical-item or report
   citation before reporting success.

## Record explicit reports

When the user explicitly states what they or the patient do, experience, prefer, or
believe, ask permission to preserve it before the first write in a task. Store a
verbatim statement or a paraphrase the user has confirmed, then summarize it:

```bash
python3 <plugin-root>/core/health_core.py record-report \
  --repo <repo> --reporter-role "patient|caregiver" \
  --subject "who the statement concerns" --statement "verbatim or confirmed statement"
```

If it corrects an earlier report, add `--supersedes <prior-report-id>`. Do not edit
or delete the prior source file. Do not call `record-report` for agent inference or
for information merely copied from the clinical record.

## Skeptical pass

Before finishing, test the memory against these failure modes:

- Does the medication view distinguish ordered, dispensed, intended, and reported use?
- Do plans name whose intent they represent and whether the patient follows them?
- Are conflicting clinicians or systems still visible?
- Could a “gap” actually be missing source coverage?
- Did a newer item truly supersede the old one, or merely add another perspective?
- Is every operational next step assigned, timed, and grounded—or explicitly unknown?

Surface unresolved questions; do not manufacture resolution.

## Rebuild

On explicit request or irreparable citation drift, rebuild the Markdown views and
manifest from the clinical core plus `memory/sources/`. Never delete
`memory/sources/`; those files are user-provided evidence, not derived cache.
