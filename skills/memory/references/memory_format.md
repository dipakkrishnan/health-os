# Memory format

```text
<repo>/memory/
├── manifest.json       # refresh watermark and memory version
├── timeline.md         # important recorded events; not a full dump
├── medications.md      # order, dispense, intent, and reported use kept separate
├── conditions.md       # recorded problem assertions with status
├── appointments.md     # upcoming visits from care-plan, connectors, or reports
├── care-plan.md        # intent, lived reality, and operational next steps
├── conflicts.md        # unresolved disagreements and discriminating questions
├── coverage.md         # connected systems, permissions, query results, missing sources
└── sources/            # immutable patient/caregiver report JSON files
```

## Manifest

```json
{
  "synced_through_run": "<latest completed sync run id>",
  "updated_at": "<ISO timestamp>",
  "memory_version": 2
}
```

The watermark advances after all new items are incorporated and citations verify.

## Source and citation rules

- Imported record claims end in one or more `[ci:<12-char id>]` citations.
- Patient and caregiver claims end in `[report:<12-char id>]` and state the reporter
  role and report date in prose.
- Clinical intent cites the note, order, or message that expresses it. If intent is
  reconstructed, label it “Interpretation” and cite the contributing items.
- Agent interpretation never receives a source citation that implies it was stated.
- One line may include different truth categories only when each is visibly labeled.

`memory/sources/<id>.json` is append-only and has this shape:

```json
{
  "id": "<32 lowercase hex characters; matches filename>",
  "recorded_at": "<ISO timestamp>",
  "reporter_role": "patient or caregiver role",
  "subject": "<person concerned, optional>",
  "statement": "<explicit statement>",
  "supersedes": "<full prior report id, optional>"
}
```

Create sources only through `health_core.py record-report`. A correction appends a
new source with `supersedes`; it never edits the earlier statement.

## View conventions

### timeline.md

Keep a selective chronology of clinically or operationally meaningful recorded
events. Group dated entries by year and keep unknown dates under `## Undated`.
Timeline entries describe recorded evidence; perspectives belong in other views.

### medications.md

Use one section per medication concept when identity is reasonably clear:

```text
### Tacrolimus
- Recorded orders: ... [ci:...]
- Recorded dispenses: ... [ci:...]
- Clinical intent: ... [ci:...] or Unknown
- Lived use: caregiver reports ... [report:...] or Unknown
- Reconciliation: Aligned | Conflicting | Unknown
```

Do not merge medications solely because their display strings are similar. Preserve
dose, route, timing, status, and source-system disagreements.

### conditions.md

Consolidate repeated assertions only when code, meaning, and status are compatible.
Preserve clinical and verification status. A diagnosis code establishes recorded
evidence, not current clinician belief or patient experience.

### appointments.md

List upcoming appointments first, then recent appointments relevant to active care.
The record itself rarely exposes upcoming visits: they come from care-plan activity
when an organization inlines them `[ci:…]`, from the runtime's calendar or email
connectors, or from what the patient or caregiver reports `[report:…]`. State each
entry's source; include status, time, participant/location when present, and
preparation state if another workflow has established it. An empty list is a
coverage statement, not proof that no visit exists.

### care-plan.md

Use one block per active concern or goal:

```text
### <concern or goal>
- Recorded evidence: ... [ci:...]
- Clinical intent: <who intends what> [ci:...] | Unknown
- Lived reality: <what actually happens> [report:...] | Unknown
- Next step: <action, owner, due time> | Unresolved
```

Do not promote a proposed order into an agreed operational next step.

### conflicts.md

Each conflict contains:

1. The competing statements, separately attributed and cited.
2. Why the difference matters operationally.
3. Relevant missing source coverage.
4. The smallest question or evidence that could resolve it.
5. Status: `unresolved`, `confirmed`, or `superseded`, with date.

Keep confirmed conflicts as short history rather than deleting them.

### coverage.md

Summarize `status.connection_details`: system, represented patient, recorded scopes
or `unknown`, latest refresh status, and every dataset status. Also list providers or
portals the patient/caregiver says exist but that are not connected. “Success” means
the source answered the query; it does not establish historical completeness.

## Consolidation rules

- Consolidate duplicate evidence; never collapse competing perspectives.
- Never average, interpolate, or round values into facts absent from a source.
- A delta can invalidate a view without invalidating an immutable source.
- Move superseded derived summaries to short history only when doing so aids audit.
- Keep views compact enough to orient an agent before it opens underlying evidence.
