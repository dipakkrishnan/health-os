---
name: visit-prep
description: Prepare a compact, cited brief for an upcoming health visit by finding the appointment through local memory or the host runtime's Google Calendar connector, reviewing interval changes and prior morning briefs, reconciling recorded evidence with clinician intent and lived reality, and surfacing the few decisions and questions that matter. Use for "prepare me for my appointment", "what should we ask the doctor?", or a local appointment-horizon automation.
---

# Visit Prep

Help the patient or caregiver arrive with the right facts, priorities, and questions.
The useful output is a one-page brief, not a comprehensive history.

## Start from current context

1. Resolve the plugin root and local data repo exactly as the memory skill does.
2. Get consent before the first record access in an interactive task. In an
   automation, stay within the access approved when it was created.
3. Run `status`; refresh and update memory when stale. Preserve a failed source as a
   coverage gap rather than blocking preparation from available evidence.
4. Read `memory/appointments.md`, `care-plan.md`, `medications.md`,
   `conflicts.md`, and `coverage.md`.

## Find the visit

Use the first reliable source:

1. A dated appointment already cited in memory.
2. Care-plan activity or another imported clinical item.
3. The host runtime's authorized Google Calendar connector.
4. An explicit patient or caregiver report.

For Calendar, search a bounded horizon, preserve only the relevant query/result with
`record-observation`, and cite `[event:<id>]`. Health OS never fetches Google data
itself. If several visits qualify, ask which one to prepare. In an unattended
automation, choose the nearest unprepared visit and state the rule.

If no visit is found, an automation should remain quiet. In an interactive task,
state the systems, calendars, and date range checked and ask once whether an
uncaptured visit exists.

## Reuse daily continuity

Read local `artifacts/morning-brief-*.md` files created since the last relevant
visit, newest first. Follow their citations to the underlying evidence; do not treat
a prior agent priority as a medical fact.

If local artifacts are absent or an action appears unfinished, inspect recent local
Health OS task/session history and prior automation runs when the runtime supports
it. Use task history to recover handoffs and user corrections, then ground each
material claim through `[ci:…]`, `[report:…]`, `[sync:…]`, or `[event:…]`. Leave
uncorroborated session context visibly provisional.

## Build the case

Identify the last relevant encounter or clinician note, then compare it with the
interval since that visit:

- New symptoms, acute care, labs, procedures, notes, diagnoses, or orders.
- What the clinician intended versus what was completed.
- Ordered/dispensed medication versus reported current use.
- Morning-brief tasks that remain blocked or repeatedly deferred.
- Missing tests, referrals, records, or source coverage.
- Caregiver observations and practical constraints, including meals, transport,
  routines, or adherence, only when explicitly reported.

Ask only questions whose answers could change the visit agenda. Ask one at a time
when interactive. In an automation, place unanswered discriminating questions in
the draft rather than guessing.

## Deliver and persist

```markdown
# Visit prep — <clinician or visit> — <date>

## Appointment
- <time, clinician, location, purpose, source> <citation>

## What changed since the last relevant visit
- <only decision-relevant interval changes> <citations>

## Current plan versus lived reality
- <aligned or conflicting medication, monitoring, food, and follow-up> <citations>

## Decisions and questions
1. <short question, with why it matters>

## Bring or arrange
- <records, medication list, measurements, transport, forms, or follow-up owner>

## Coverage limits
- <systems or periods not checked> <citations where available>
```

Omit empty sections and keep the artifact to one page. Save it as
`<repo>/artifacts/visit-prep-<YYYY-MM-DD>-<short-slug>.md`, run `verify`, and show
the user where it was saved. Never recommend changing treatment without the
appropriate clinician.
