---
name: refresh
description: Connect health systems and keep the local record current — guided local-first setup, multi-system refresh, the skeptical first-refresh interview that reconciles the record with clinical intent and lived reality, and change review between refreshes. Use for "connect my health records", "set up health-os", "refresh my records", "what changed since last time", or when another health workflow finds no repository or stale data.
---

# Refresh

Treat every refresh as evidence collection, not truth acquisition. The record shows
what source systems recorded; only the patient or caregiver can say what is actually
happening. Your job is to fetch honestly, explain coverage plainly, and ask the few
questions whose answers change the picture.

## Resolve the environment

1. Resolve the plugin root without assuming a runtime: use `$PLUGIN_ROOT` when
   available (Codex), then `$CLAUDE_PLUGIN_ROOT` (Claude), otherwise locate the
   nearest parent of this skill or the working directory containing
   `.codex-plugin/plugin.json` or `.claude-plugin/plugin.json`. Confirm
   `<plugin-root>/core/health_core.py` exists; never guess a path.
2. Resolve the data repo from `$HEALTH_OS_REPO`, then `~/health-data`. No repo means
   first-time setup below. Never use sandbox data.
3. Connecting and refreshing need `python3` with the `cryptography` package
   (`pip install -r <plugin-root>/core/requirements.txt`, ideally in a venv). Check
   before promising a refresh. Reuse a compatible environment or create one local
   to the workspace and request the minimum installation approval. Report the
   outcome, not each probe, failed command, or implementation detail.
4. Before the first record access in a task, explain that selected local context
   will be processed by the active agent runtime and follow its configured data
   policy. Stop if the user declines.

## First-time setup

Run this as a conversation, not a checklist recital. The user should never need to
learn command names, connection IDs, or FHIR vocabulary.

1. **Who is this record about, and who is operating?** The patient may be the user,
   or the user may be a caregiver coordinating for someone else. Record both roles
   in your head now — every preserved statement is attributed to its reporter, and
   a caregiver's observation is never written as the patient's own report.
2. **Say where things live before touching anything.** Records are stored only in
   the local repository (`~/health-data` unless the user chooses otherwise);
   there is no hosted account; uninstalling never deletes the record; sharing
   anything externally will always be asked first.
3. **Inventory care before connecting.** Ask where the patient receives care —
   health systems, portals they can log into, and care that has no portal. Systems
   named but not connected go into coverage as known-missing sources, not silence.
   If the user chooses one system without answering about the rest, acknowledge the
   deferral and revisit it once before the baseline; do not ask as though their
   earlier answer was lost.
4. **Connect one system at a time:**

   ```bash
   python3 <plugin-root>/core/connect.py connect \
     --repo <repo> --connection <short-slug> --org "<organization name>"
   ```

   A browser opens for the patient portal login. For caregivers: use the portal's
   own proxy access if they have it; never ask for or encourage sharing the
   patient's credentials. Keep the connection process under observation and resume
   when its callback completes. Do not ask the user to type `done` when the runtime
   can observe completion; ask only if the page did not open, an error appeared, or
   the runtime genuinely cannot monitor the process. Repeat for each additional
   system.
5. After the first successful connection and sync, continue with the coverage
   explanation and interview below — setup and first refresh are one experience.

## Refresh existing connections

1. List connections from `status --repo <repo>` and refresh each:

   ```bash
   python3 <plugin-root>/core/connect.py resync --repo <repo> --connection <id>
   ```

2. A network or auth failure is a calm coverage fact, never a stack trace in the
   user's face: say which system could not be reached, that the prior record is
   intact, and when to retry. Partial results are usable results.
3. Finish every refresh with `verify --repo <repo>` and report if grounding fails.

## Explain coverage honestly

From `status`, per connection: provider, represented patient, granted scopes (or
`unknown`), latest refresh result, and each dataset's status. Then the rules:

- Say that all **configured queries completed**, never that the person's record is
  complete.
- `empty` or `not_queried` is not "none exist". "Not on file" is not "no allergies".
- Upcoming appointments are special: most organizations' records cannot expose them
  to this client. Look first in care-plan activity, then inventory calendar and
  email connectors already authorized in the runtime and proactively offer to check
  the relevant accounts before asking the user to reconstruct the schedule. Search
  narrowly and state the account/calendar and time range checked. A connector result
  and the user's confirmation are different evidence: never rewrite the connector
  observation as a patient report. Until connector evidence has a durable citation,
  preserve only the user's explicit confirmation and label the connector check as
  session-only. Every appointment claim states its source (record, calendar, email,
  or report).
- Name the systems the user said exist but that are not connected.

## The first-refresh interview

Before asking anything, read the evidence: `timeline` by domain, and render recent
notes and summaries with `document --repo <repo> <id-prefix>` — notes are where
clinical intent lives. Build a private list of candidate questions, then ask only
the ones whose answers would change the baseline, **one at a time**, highest value
first. Use the runtime's structured question tool when one exists; otherwise ask
plainly in chat and wait. Follow `references/interview_guide.md` for question
patterns and priority order. After five substantive questions, offer the guide's
pause before continuing. A report can clarify lived reality; do not say it resolves
a conflicting order, note, or clinical intent unless the competing sides now agree.

Preserve what you learn as you go — ask permission once per task, then:

```bash
python3 <plugin-root>/core/health_core.py record-report \
  --repo <repo> --reporter-role "patient|caregiver" \
  --subject "<who it concerns>" --statement "<verbatim or confirmed>"
```

Corrections use `--supersedes`. Never record your own inference as a report.

## Baseline and memory

1. Invoke the memory skill to build or update the cited views from the refreshed
   record plus the new reports.
2. Produce the baseline artifact (format in `references/interview_guide.md`) and
   save it to `<repo>/artifacts/baseline-<YYYY-MM-DD>.md`.
3. Ask: "Does this baseline faithfully represent what you know? We can leave
   anything unresolved rather than guess." Amend from the answers; unresolved
   items stay visible in the conflicts view.

## Change review (every later refresh)

1. `delta --repo <repo> --after <memory watermark>` for what is new.
2. For each change, say what it confirms, changes, or contradicts — including
   contradictions with reported lived reality ("the record now shows X; you told
   me Y — has something changed?").
3. Update memory; ask only what the record cannot know.

## Ongoing automation

After a successful baseline, offer — never silently install — a recurring refresh
using the host runtime's local scheduler (Codex automations; Claude Code scheduled
tasks). It must run on this machine: the repository is local, so a cloud routine
cannot do this job. Distinguish clearly and get separate consent for:

- **Deterministic maintenance:** resync + verify; no model reads record content.
- **Agentic review:** the model reads changes to summarize or flag them.

Default to quiet: an automation should speak only when something actionable changed.
