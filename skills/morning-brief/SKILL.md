---
name: morning-brief
description: Build a caregiver-facing morning brief of what needs attention today and soon across medications, meals, monitoring, household coordination, refills, follow-up, and upcoming visits. Use for "what do I need to do for my loved one today?", daily care coordination, a morning health briefing, or a local recurring care automation.
---

# Caregiver Morning Brief

Reduce today's cognitive load. Produce a short action list, not a chart summary.
Include ordinary life work when it affects care, but never invent a regimen or task
because it sounds medically sensible.

## Start

1. Resolve the plugin root and local data repo exactly as the memory skill does.
2. Before the first record access in a task, explain that selected local context will
   be processed by the active agent runtime and follow its configured data policy.
   In an automation, rely only on the access the user approved when creating it.
3. Read `status`, `memory/manifest.json`, and the relevant memory views. If memory is
   stale, invoke refresh and memory before briefing; if refresh fails, use the prior
   record and name the stale source.
4. Establish who receives care and who coordinates it. Preserve patient and
   caregiver perspectives separately.

## Continue from prior mornings

Read the newest `<repo>/artifacts/morning-brief-*.md` first, then older briefs only
as needed to find unfinished or changed work.

If the host runtime exposes local task/session history, inspect recent Health OS
morning-brief tasks and automation runs when the local artifact is missing or a
handoff appears incomplete. Codex may use task history; Claude may use its scheduled
task or routine history. Treat that history as navigation and continuity context,
not clinical evidence. Before carrying a task into a cited artifact, resolve its
existing citation or confirm it with the user and preserve a report.

## Look ahead

Check the runtime's authorized Google Calendar connector for health-related events
today and within the next 14 days, unless the user chose another horizon. Health OS
does not call Google directly. Preserve the minimal bounded query and result with
`record-observation`, then cite it `[event:<id>]`.

Do not assume an event is medical from a vague title. Use surrounding record context
or ask. Do not include unrelated private calendar details in the artifact.

## Decide what earns attention

Rank only work that is due, time-sensitive, changed, blocked, or easy to miss:

- Medications actually reported as used, plus refills or reconciliation conflicts.
- Meals, hydration, glucose/vitals, mobility, hygiene, or household support only
  when established by the care plan or a patient/caregiver report.
- Visits, tests, transport, forms, records, or questions on the horizon.
- New record information that changes today's plan.
- Calls, scheduling, or follow-up with a named owner.

Distinguish recorded orders `[ci:…]`, clinical intent `[ci:…]`, lived reality
`[report:…]`, connector observations `[event:…]`, and derived prioritization.
Never convert an old order into today's instruction.

## Deliver

Lead with at most five ranked actions. Use this compact shape:

```markdown
# Morning care brief — <person> — <local date/time>

## Today
- <time or priority> — <action> — Owner: <person> <citations>

## On the horizon
- <date> — <preparation or decision needed> <citations>

## Changed or needs confirmation
- <new information, conflict, or blocked item> <citations>
```

Omit empty sections. Say "Nothing actionable changed" when true. Save the exact
brief to `<repo>/artifacts/morning-brief-<YYYY-MM-DDTHHMM>.md` and run `verify`.

## Offer paired local automations

After a successful interactive brief, offer two host-runtime automations:

1. A local morning-brief run at the user's chosen time and days.
2. A local visit-horizon check shortly afterward that invokes visit prep only when
   an appointment enters the chosen horizon or relevant preparation changed.

Use Codex automations or Claude scheduled tasks/routines in natural language. Do not
build a scheduler. Ask separately before creating either automation. The visit check
stays quiet when no preparation is needed.
