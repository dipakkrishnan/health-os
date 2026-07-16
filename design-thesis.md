# Health OS — Design Thesis

## One-line thesis

Health OS is a local-first toolkit that gives a person's general-purpose agent durable, evidence-grounded health context and repeatable workflows for staying ahead of care.

In shorter form:

> A user-owned health context that helps an agent understand what is true, notice what is next, and carry work across care.

Health OS is a tool, not a destination product. It builds on the conversational interface, reasoning quality, permissions, task continuity, automations, and notifications already supplied by agent runtimes such as ChatGPT, Codex, and Claude. As those runtimes become more capable and accessible, Health OS should become more capable without rebuilding their horizontal features.

## The job

The core job is not to collect records or answer isolated health questions. It is to keep a coherent, operational picture of care alive across daily life, clinicians, institutions, and time.

That job is currently carried by patients and caregivers. It includes remembering what actually happened, reconciling conflicting medication lists, preparing for appointments, arranging tests, tracking changes, and translating between specialists who each see only part of the case. The burden is especially high for an older adult with several conditions and a family caregiver coordinating meals, medications, glucose checks, symptoms, hygiene, appointments, and follow-up.

Health OS should reduce that cognitive load. A visit is not the product; it is a checkpoint in a continuous loop.

## Three competing truths

Health state cannot be represented by a single authoritative narrative. The agent must work interactively across three kinds of truth:

1. **Recorded evidence:** what source systems say happened. This is objective evidence of what was recorded, not a guarantee that the record is complete or correct.
2. **Clinical intent:** what a clinician believes, recommends, or is trying to accomplish. This may live in notes, orders, messages, or conversation and may conflict across clinicians or change over time.
3. **Lived reality:** what the patient or caregiver actually does and experiences, including medication use, symptoms, constraints, preferences, and missed or modified plans.

The system must preserve these perspectives separately and help the user reconcile them. It must never silently convert an order into confirmed use, a diagnosis code into current clinical belief, or an agent inference into fact.

Every material statement should remain distinguishable as:

- Imported evidence
- Patient- or caregiver-reported information
- Clinical intent or interpretation
- A confirmed correction
- An unresolved conflict
- A derived agent interpretation

Interactivity is therefore part of the evidence system, not presentation polish. The agent should explain gaps, ask discriminating questions, challenge convenient assumptions, accept correction, and show how its understanding changed. It should be skeptical of its synthesis and of record completeness without being dismissive of the patient.

## Distribution thesis: ride the agent-runtime curve

Health OS is not a hosted health-data service, standalone app, or custom agent platform. It is a portable set of skills, contracts, and deterministic local tools that helps a user create and operate a private health core through an agent they already use.

The health core belongs to the user and remains useful if a model, runtime, skill, or project disappears. The agent runtime supplies the interface and horizontal capabilities. Health OS supplies health-specific context, tools, and workflow intelligence.

```text
General-purpose agent runtime
    conversation, voice, reasoning, approvals, tasks,
    automations, notifications, and artifact presentation

        +

Health OS
    local evidence, provenance, health semantics,
    deterministic commands, and care workflows

        =

An agent that can carry health work across time
```

This is **batteries included, infrastructure omitted**. A Health OS skill may offer to configure the runtime's native scheduled task or automation. Health OS should provide reliable commands and workflow recipes for that automation, not build another scheduler, notification service, chat interface, or account system.

The distribution risk is discovery and setup, not the absence of a new consumer destination. The toolkit should be installable wherever capable general agents run and should improve with them.

## The continuity loop

```text
Connect one or more health systems
    ↓
Refresh their records into the local core
    ↓
Interview the patient or caregiver about coverage and lived reality
    ↓
Confirm a baseline while preserving conflicts and gaps
    ↓
Notice what is next, especially the next appointment or required follow-up
    ↓
Prepare proactively and ask only what the record cannot answer
    ↓
Let the user inspect, correct, interrupt, and approve
    ↓
After the event, refresh and reconcile what changed
    ↓
Update the durable context and continue
```

### First refresh

The first refresh is evidence collection, not truth acquisition. It should:

- Inventory providers, institutions, portals, and known missing sources.
- Connect multiple health systems when care is fragmented.
- Report exactly which organizations, date ranges, and resource types were queried.
- Import appointments as well as clinical history.
- Ask the patient or caregiver what is current, what is wrong, and what the record omits.
- Reconcile medications, active concerns, clinician roles, and immediate follow-up.
- Produce a confirmed baseline that preserves disagreement rather than flattening it.
- Offer useful runtime-native automations, with clear permission and an easy way to stop them.

### The first magic moment

The agent identifies the next known appointment and begins useful work before the user has to reconstruct the case.

It should compare the current record with the last relevant visit, identify interval changes, conflicting plans, medication uncertainty, missing tests, and open follow-up; ask focused questions about lived reality; and produce a cited visit-preparation artifact. After the visit, it should refresh the relevant systems, detect new notes, orders, results, and appointments, and interactively reconcile the new plan with what will actually happen.

The result appears in the agent task where the work is already happening and is saved as a local, cited artifact. The user can inspect the underlying evidence, correct the agent, decline actions, or interrupt an automation through the host runtime.

## System boundary

### Local health core

The trusted, model-independent data plane. It:

- Maintains separate connections to multiple health systems.
- Imports and refreshes records and appointments.
- Preserves exact original sources and versions.
- Normalizes source-grounded clinical items.
- Stores patient and caregiver reports without confusing them with imported evidence.
- Maintains time, provenance, conflicts, corrections, coverage, and reconciliation history.
- Exposes timelines, state views, deltas, and question-specific case packets.
- Validates citations and repository snapshots.

### Health OS skills

Thin, replaceable workflow definitions. They specify:

- How to establish and challenge a baseline.
- How to request deterministic context from the core.
- Which questions require interaction with the user.
- What actions may be proposed and what approval is required.
- What artifact to produce and how every claim must cite evidence.
- When to offer a host-runtime automation.
- How uncertainty, conflicts, and safety boundaries must be expressed.

Skills do not own the record, implement a general chat UI, or become the source of truth.

### General-purpose agent runtime

The runtime supplies natural-language and voice interaction, reasoning, permissions, task continuity, scheduling, notifications, and artifact presentation. It may investigate contradictions, search literature, prepare summaries, or act through connected systems when the user has granted access.

The agent's conclusions remain derived artifacts. The runtime may change; the user's local evidence and reconciled context remain.

## Core primitives

### Connection and coverage

A connection represents one authorized source system and the permissions granted to it. Coverage records what was actually queried: organization, resource type, date range, status, and failure. Several connections may describe the same person's care without implying that any one is complete.

### Source

An immutable imported object such as a FHIR resource or response, clinical note, PDF, image, wearable export, portal message, or patient journal entry.

### Clinical item

A normalized, source-grounded piece of health information such as a laboratory result, medication order, medication-use report, diagnosis, symptom, procedure, vital sign, appointment, or imaging finding. Every clinical item references its source and precise supporting evidence.

### Perspective and reconciliation

A perspective captures recorded evidence, clinical intent, or lived reality without forcing agreement. A reconciliation records how the user and agent resolved—or deliberately did not resolve—a conflict, what evidence was considered, who confirmed it, and when.

### Timeline and state

Generated views over clinical items, perspectives, and reconciliations. They are not independent sources of truth and always point back to underlying evidence.

### Case packet

An immutable, question-specific snapshot containing the question or event, relevant items and perspectives, selected excerpts, known conflicts, missing information, coverage limitations, and repository snapshot ID. It is the primary interface between the health core and agent workflows.

### Claim and artifact

A claim is a derived interpretation with supporting and contradicting evidence, confidence, method, and review status. An artifact saves the case packet, claims, output, and execution metadata so the user can inspect and revisit the work.

## Health Deep Review

Deep Review remains a high-value escalation workflow, not the top-level product thesis. When a case warrants it, the agent can assemble a grounded case packet, select relevant specialist perspectives, run independent and cross-specialty passes, verify evidence and literature, challenge preliminary findings, and compress the survivors into a short cited report.

It is useful for complex multisystem questions, medication-condition interactions, competing explanations, and unclear monitoring gaps. It should not turn routine continuity work into a committee of agents.

Each material finding should include:

1. What appears connected and why it matters.
2. Evidence for and evidence against.
3. Which truth category each assertion belongs to.
4. What remains unknown or unreliable.
5. The most useful next question or action for the appropriate human.

## Design principles

1. **Interaction is reconciliation.** Conversation is how the system discovers and preserves the differences between the record, clinical intent, and lived reality.
2. **Evidence before interpretation.** No factual claim exists without a resolvable source or an explicit patient, caregiver, or clinician attribution.
3. **Be constructively skeptical.** Test record completeness, agent synthesis, and user assumptions; ask questions that could change the conclusion.
4. **Preserve sources; version understanding.** Imported sources are append-only. Corrections and new interpretations never rewrite prior evidence.
5. **Time is first-class.** Preserve effective, recorded, and import time. Unknown or approximate dates remain explicit.
6. **Provenance is structural.** Citations are identifiers and evidence locators, not prose added after generation.
7. **Completeness is never assumed.** Expose queried systems, scopes, resource types, date ranges, failures, and missing sources.
8. **Local context is durable; skills and runtimes are replaceable.** The user-owned core outlives any model or interface.
9. **Ride the agent-runtime curve.** Reuse the host's conversation, approvals, automations, notifications, and connected accounts instead of rebuilding them.
10. **Autonomy follows permission.** Read, write, message, or schedule only through connected systems and scopes the user has granted; make consequential actions inspectable and interruptible.
11. **Derived knowledge cannot silently become fact.** Promotion into confirmed state requires explicit reconciliation.
12. **Local-first includes compute policy.** Any transmission to an external model or tool must be visible and governed by policy.
13. **Breadth must end in compression.** The result should reduce cognitive load, not expose raw agent work.
14. **Build data breadth through workflows.** Add notes, vitals, procedures, messages, and other feeds when a concrete workflow needs them, not to chase nominal completeness.

## What compounds

The durable asset is not a proprietary interface or a single model answer. It is the user's local, increasingly reconciled longitudinal context:

- Original evidence from multiple systems
- Coverage and permission history
- Normalized clinical items and temporal relationships
- Patient and caregiver reports
- Clinical intent and competing interpretations
- Corrections, conflicts, and reconciliation history
- Cited workflow artifacts

Once this core exists, new capabilities become relatively small skills:

```text
health core
    ├── prepare for the next visit
    ├── reconcile medications and care plans
    ├── detect missing follow-up
    ├── investigate a trend
    ├── coordinate caregiver work
    └── perform a cross-specialty Deep Review
```

## Non-goals

Health OS is not initially:

- A standalone consumer app or custom chat interface
- A hosted health-data account or record custodian
- A scheduler, notification service, or general agent orchestrator
- A replacement electronic health record
- An autonomous diagnostic or treatment system
- A substitute for clinicians or caregiver judgment
- A universal healthcare ontology
- A guarantee of complete or correct medical records
- A chatbot that answers without evidence

## The three foundational pillars

```text
Pillar 1: User-owned, evidence-grounded longitudinal context
Pillar 2: Interactive reconciliation across the three truths
Pillar 3: Agent-native workflows that anticipate and carry care forward
```

The core makes the agent trustworthy. Interaction makes the context honest. The runtime makes the system useful in the flow of life.
