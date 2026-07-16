# Health OS — Design Thesis

## One-line thesis

Health OS is an installable skill system that helps anyone build a private, evidence-grounded longitudinal health context on their own machine and use coding-agent runtimes to convene on-demand specialist perspectives that augment human care.

In shorter form:

> User-owned longitudinal health context with an on-demand multidisciplinary review layer.

## Distribution thesis

Health OS is not a hosted health-data product. It is a portable set of skills, contracts, and deterministic local tools that helps each user create and operate their own health core.

The health core belongs to the user. The distributed product is the machinery and procedural intelligence required to build, maintain, and compute over it across compatible agent runtimes.

```text
Install
    install the Health OS skills and local core

Boot
    interview the user, inventory providers, authenticate,
    fetch records, assemble state, and confirm the baseline

Daemon
    deterministically synchronize new source records

Apps
    run visit preparation, reconciliation, investigation,
    and multidisciplinary review skills on demand
```

The onboarding interview is part of the evidence system, not merely setup UX. It produces:

- A provider and record-coverage ledger
- Explicitly patient-reported clinical items
- Confirmed corrections to imported records
- Unresolved conflicts and missing information
- Questions used to reconcile the initial health state

The agent may discover gaps, propose interpretations, and ask intelligent questions. It cannot manufacture grounded state. Every onboarding output must remain distinguishable as imported evidence, patient-reported information, a confirmed correction, an unresolved conflict, or a derived interpretation.

## The two gaps

### 1. The context gap

No participant has a complete, computationally useful longitudinal record.

- Records are fragmented across institutions.
- Important changes are separated by months or years.
- Medication, laboratory, symptom, and diagnosis histories conflict.
- A short appointment cannot reconstruct the entire case.
- Patient-visible records may themselves be incomplete.

The health core addresses this gap.

It imports and preserves original records, normalizes grounded clinical items, maintains their temporal and provenance relationships, and assembles question-specific context without silently turning interpretations into facts.

### 2. The expertise-coverage gap

Care is necessarily specialized. Each clinician sees a case through a particular scope, time budget, and clinical responsibility.

A nephrologist may focus on renal function. A neurologist may focus on neuropathy. A transplant specialist may focus on rejection risk and immunosuppression. A clinical pharmacologist may notice an interaction that is not central to any one visit.

The missing capability is not merely another opinion. It is an on-demand multidisciplinary review that asks:

- Which specialties are relevant to this particular case?
- What would each specialty inspect?
- Where do their interpretations interact or conflict?
- What evidence supports or contradicts each interpretation?
- What information would discriminate between competing explanations?
- Which findings are important enough to bring to a clinician?

Deep Review addresses this gap.

## Product model

```text
Installable Skill System
    bootstraps and operates the user's health core

        +

User-Owned Health Core
    preserves grounded longitudinal context

        +

Runtime Specialist Skills
    expand expertise coverage on demand

        +

Review Interface
    compresses findings for human judgment
```

The review interface is essential. Producing twenty specialist reports would increase review load. The system succeeds only if it converts broad investigation into a small number of high-leverage, evidence-backed findings.

## System boundary

```text
Health Core
    durable evidence and context

        +

Agent Skills
    repeatable workflows

        +

Runtime Agents
    question-specific reasoning

        =

Cited Health Artifact
```

### Health core

The trusted, model-independent data plane.

It:

- Imports and synchronizes health records.
- Preserves original sources.
- Normalizes grounded clinical items.
- Maintains temporal and provenance relationships.
- Exposes timelines and question-specific case packets.
- Validates citations and snapshots.
- Stores user corrections without rewriting history.

### Agent skills

Thin, replaceable workflow definitions.

They specify:

- How to request context from the core.
- Which investigation to perform.
- How specialist passes should be scoped.
- What output structure to produce.
- How claims must cite evidence.
- What uncertainty and safety language is required.

Skills do not own the health record, parse source formats, or become the source of truth.

### Runtime agents

Ephemeral compute.

They may reconstruct timelines, compare trends, investigate contradictions, search literature, or prepare clinician-facing summaries. Their conclusions remain derived artifacts and never silently become grounded health state.

## Foundational data flow

```text
Raw source
    ↓
Grounded clinical items
    ↓
Timeline and state views
    ↓
Question-specific case packet
    ↓
Cross-specialty Deep Review
    ↓
Cited review artifact
```

The repository preserves evidence. Views compress it. Case packets select it. Agents interpret it.

## Core primitives

### Source

An immutable imported object:

- FHIR resource or response
- Clinical note
- PDF
- Image
- Wearable export
- Patient journal entry

### Clinical item

A normalized, source-grounded piece of health information:

- Laboratory result
- Medication order
- Medication-use report
- Diagnosis
- Symptom report
- Procedure
- Vital sign
- Imaging finding

Every clinical item references its source and precise supporting evidence.

“Clinical item” is preferable to a universal atomic triple because it accommodates values, units, ranges, statuses, dosage structure, and multiple relevant times without discarding clinical meaning.

### Timeline

A generated chronological view over clinical items.

The timeline is not a separate source of truth. Its entries reference the underlying clinical items.

### Case packet

An immutable, question-specific context snapshot containing:

- The question
- Relevant clinical items
- Timeline entries
- Selected source excerpts
- Known conflicts
- Missing information
- Repository snapshot ID

This is the primary interface between the health core and agent skills.

### Claim

A runtime interpretation supported or contradicted by clinical items.

Claims are derived and contain:

- Supporting item IDs
- Contradicting item IDs
- Confidence
- Generation method
- Review status

### Review

A saved runtime artifact containing the case packet, claims, output, and execution metadata.

## Health Deep Review

Deep Review is not “ask several agents for opinions.” It is procedural scaffolding that calibrates the investigation, decomposes it into specialist passes, verifies claims, independently challenges findings, and only then synthesizes a prioritized report.

```text
Patient question or review goal
    ↓
Calibrate scope and urgency
    ↓
Assemble grounded case packet
    ↓
Select relevant specialist perspectives
    ↓
Run independent specialist passes
    ↓
Run cross-specialty interaction pass
    ↓
Verify evidence and literature
    ↓
Run adversarial critique
    ↓
Produce prioritized synthesis
    ↓
Present patient and clinician review interface
```

### Calibration

Determine what the user is trying to accomplish:

- Prepare for an appointment
- Investigate a longitudinal change
- Reconcile medications
- Understand competing explanations
- Identify missing follow-up
- Review a complex multisystem case

Calibration also establishes what the system should not attempt.

### Dynamic specialist selection

Specialist perspectives are selected from the case rather than run as a fixed committee.

For example, a question involving tingling, tacrolimus, and rising creatinine might route to:

- Nephrology
- Neurology
- Transplant medicine
- Clinical pharmacology
- Electrolyte and metabolic review

Each specialist receives the same grounded case packet but a distinct review mandate.

These agents provide specialist review perspectives; they do not represent actual clinicians or replace specialist care.

### Specialist passes

A specialist pass inspects evidence through a defined clinical lens. For example:

```text
Clinical pharmacology pass:
- Reconstruct medication exposure.
- Identify dose changes and interacting drugs.
- Check whether symptoms or laboratory changes followed exposure.
- Find evidence against a medication-related explanation.
- Identify monitoring information that is absent.
```

### Cross-specialty interaction pass

This pass identifies relationships that may not be central to any individual specialty:

- One treatment improving one system while worsening another
- Symptoms crossing conventional specialty boundaries
- Medication–condition interactions
- Conflicting specialty assumptions
- Findings whose meaning changes when considered together
- Tests ordered in one lane that answer questions in another

### Adversarial critique

Critique agents attempt to defeat preliminary findings:

- Is the temporal association spurious?
- Is there a more ordinary explanation?
- Is supposedly missing information present elsewhere?
- Does the cited literature apply to this patient?
- Is a conclusion based on a medication order rather than confirmed use?
- Is the record incomplete in a way that invalidates the interpretation?

Only findings that survive critique reach the final report.

## Review output

The output should reduce review load rather than expose the user to raw agent discussion.

Each material finding should contain:

```text
1. Cross-specialty finding
   What appears connected.

2. Why it matters
   Concise clinical relevance.

3. Evidence for
   Grounded record citations.

4. Evidence against
   Contradictions and alternative explanations.

5. What remains unknown
   Missing or unreliable information.

6. Useful next question
   A question for the appropriate clinician.
```

Findings should be ranked as:

- Time-sensitive issue to raise
- Significant cross-specialty question
- Record inconsistency
- Monitoring gap
- Lower-confidence hypothesis

## Design principles

1. **Evidence before interpretation.** No factual statement exists without a resolvable source reference. Derived conclusions remain distinguishable from source-grounded information.

2. **Preserve sources; version interpretations.** Imported sources are append-only. Corrections, normalization changes, and new interpretations create new versions without rewriting prior evidence.

3. **Time is first-class.** Preserve effective time, recorded time, and import time. Unknown or approximate dates remain explicitly unknown or approximate.

4. **Provenance is structural.** Citations are identifiers and evidence locators, not prose added after generation.

5. **Completeness is never assumed.** The system records which sources, organizations, date ranges, and resource types were queried and exposes gaps to runtime consumers.

6. **Skills are replaceable; context is durable.** Codex, Claude Code, and future runtimes may use different skills over the same health-core contract.

7. **Derived knowledge cannot silently become fact.** Agent conclusions may be saved as claims or reviews. Promotion into user-reported state requires explicit confirmation.

8. **Local-first includes compute policy.** Data is stored locally by default. Any transmission to an external model or tool must be visible and governed by an explicit policy.

9. **Optimize for auditability.** A review preserves its snapshot, context, citations, model, and workflow version. Exact model reproduction is not promised.

10. **Breadth must end in compression.** Specialist passes are valuable only when synthesis reduces the findings to a tractable human review surface.

11. **Build views when demanded.** Timelines, medication histories, and lab trends are useful early. General episode detection and universal terminology mapping should be added only when real workflows require them.

## Product thesis

The primary product is not the answer to a health question. It is the ability to repeatedly ask new questions against the same trustworthy longitudinal context and convene the relevant review perspectives at runtime.

Once the health core exists, capabilities become skills:

```text
health core
    ├── prepare for a visit
    ├── reconcile medications
    ├── investigate a trend
    ├── reconstruct a timeline
    ├── identify record conflicts
    └── perform a cross-specialty Deep Review
```

Each skill is relatively inexpensive to create because ingestion, grounding, chronology, provenance, and case assembly are shared.

## Defensible asset

The durable asset is the user-controlled longitudinal context:

- Original evidence
- Normalized clinical items
- Temporal relationships
- Corrections and reconciliation history
- Provenance graph
- Review history

Models, prompts, and agent runtimes will change. The grounded context remains useful across all of them.

## Non-goals

Health OS is not initially:

- A replacement electronic health record
- A clinical decision-support device
- An autonomous diagnostic or treatment system
- A substitute for specialist care
- A universal healthcare ontology
- A guarantee of complete medical records
- A chatbot that answers without evidence

## The two foundational pillars

```text
Pillar 1: Grounded longitudinal context
Pillar 2: On-demand multidisciplinary review
```

The core makes the review trustworthy. The review makes the core worth building.
