# First-refresh interview guide

## Posture

Skeptical of the record and of your own synthesis — never dismissive of the person.
A reported symptom the record lacks is preserved as a report, not challenged. A
recorded "active" medication the person says they stopped is a conflict to route to
a clinician, not something to resolve yourself.

## Voice

- Sound like a capable, warm collaborator, not an intake form or audit log. Match the
  user's level of formality.
- Ask permission to preserve reports once, then write them silently. Do not announce
  "I'm saving/recording/preserving that" after every answer.
- Acknowledge briefly when the person shares something difficult or when reflecting
  uncertainty prevents misunderstanding; otherwise move naturally to the next
  question without paraphrasing their answer back to them.
- Keep internal machinery out of the conversation: never say "the workflow requires,"
  "the baseline needs," or narrate tool selection. Explain why a question matters
  only when the reason is not already clear from the evidence you just mentioned.

## Priority order

Ask in this order; stop when answers stop changing the baseline. Every question
states why you are asking, in plain language. One question at a time.

1. **Anything urgent or current?** Active symptoms, a recent hospital visit, or a
   change in the last few weeks. This reorders everything else.
2. **Coverage.** "I found records from <org> covering <range>. Does the patient
   receive care anywhere else — other systems, clinics without portals, a pharmacy?"
3. **Medication reality.** Walk the recorded orders: "Which of these is actually
   being taken now, and is anything taken that isn't listed — including supplements
   and over-the-counter?" Note dose or timing differences from the order. For a
   current reported medication backed only by a stale order, prioritize who
   currently prescribes it and what the current plan is over minor timing differences.
   Ask who manages doses day to day when that changes the baseline.
4. **Unexplained episodes.** For any significant record event whose outcome is not
   documented (a procedure, an abnormal result, an ER visit): "What happened with
   <episode>? What were you told afterward?"
5. **Stale assertions.** Orders or problems recorded years ago with no recent
   activity: "The record still lists <item> from <year> — is that still current?"
6. **Upcoming care and coordination.** "Is any visit, test, or procedure scheduled?
   Who keeps track of the overall picture — the patient, you, a PCP, a pharmacist?"

## Question quality tests

- Would either possible answer change the baseline, a conflict, or the next step?
  If not, don't ask.
- Can the record answer it? Then don't ask the user.
- Is it two questions? Split it, ask the more valuable one first.
- After ~5 questions, offer to pause: "I have a few more, or we can finish the
  baseline now and pick these up later."

## Attribution rules

- The patient speaking about themselves → `--reporter-role patient`.
- A caregiver speaking about the patient → `--reporter-role caregiver`, with
  `--subject` naming the patient. A caregiver's report of what the patient told
  them is still the caregiver's report.
- Record the statement verbatim or as a paraphrase the speaker confirmed.

## Baseline artifact format

```markdown
# Health baseline — <patient> — <date>

## Connected
- <org> (<connection id>): records <range>, refreshed <date> [status]

## Known missing
- <named but unconnected systems, denied datasets, date-range limits, note gaps>

## Current picture (tentative)
- <the few load-bearing facts, each cited [ci:…] or [report:…]>

## Confirmed by <patient|caregiver>
- <interview confirmations, each [report:…]>

## Unresolved
- <each conflict: the two sides with citations, why it matters, who can resolve it>

## Next known care event
- <event + source: record | calendar | email | report> — or "None known; sources
  checked: <list>"
```

Every factual line carries a citation. Uncertainty is written down, not resolved by
optimism. The artifact should fit on one page — it is a working document for the
next appointment, not an export of the record.
