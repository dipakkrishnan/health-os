# Memory format

```
<repo>/memory/
├── manifest.json      # watermark + bookkeeping
├── timeline.md        # the chronological narrative of the record
├── medications.md     # consolidated medication courses
├── conditions.md      # problem list with statuses
└── gaps.md            # known coverage limits and open questions
```

## manifest.json

```json
{
  "synced_through_run": "<sync_run_id the memory is current through>",
  "updated_at": "<ISO timestamp>",
  "memory_version": 1
}
```

`synced_through_run` is the watermark: `delta --after <it>` yields exactly the items
the next update must process. Set it from `delta.latest_run` (update) or
`status.latest_sync_run_id` (bootstrap) — never invent it.

## File conventions

- Every factual line ends with one or more `[ci:<first 12 chars>]` citations.
- `timeline.md`: entries grouped by year; one line per event; an `## Undated`
  section for items with unknown time; optional `## Interpretation (not in record)`.
- `medications.md`: one entry per medication *course* — consolidate repeated or
  renewed orders into a single entry citing each order. State explicitly that
  entries are orders, with actual use unknown unless patient-reported.
- `conditions.md`: one entry per problem, not per assertion — the same diagnosis
  recorded across five encounters is one line with five citations. Keep
  clinicalStatus/verificationStatus. Placeholder entries ("Not on File") are
  reported in prose as absences ("no allergies documented"), citing the placeholder
  item.
- `gaps.md`: datasets never synced, date ranges before each connection's history,
  known providers not yet connected, and questions the record raises but cannot
  answer. Sourced from `status` coverage plus what assembly noticed.
- Each file may keep a short `## History` section at the bottom: superseded lines
  moved there with the date and the citation of what replaced them.

## Consolidation rules

- Merge, cite everything: a consolidated line carries the citations of all items it
  summarizes.
- Never average, interpolate, or round values into new numbers the record does not
  contain.
- When two items conflict (same fact, different values/status), the memory line
  states the conflict and cites both — resolution belongs to review skills, not to
  memory.
