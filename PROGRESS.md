# Health OS — Progress

Updated 2026-07-16

## Direction settled

- Health OS is a **local-first tool for general-purpose agents**, not a standalone product, hosted record, or custom interface.
- The durable asset is the user's local longitudinal context. Skills, models, and runtimes are replaceable.
- The system must preserve and interactively reconcile three competing truths: recorded evidence, clinical intent, and lived reality.
- The first refresh is a skeptical baseline interview as well as an import. It explains coverage, identifies missing systems, and asks the patient or caregiver to confirm or correct the emerging picture.
- Multiple health-system connections are foundational. No single portal is assumed complete.
- Appointments are a primary trigger. The first proactive loop is: find the next visit, prepare from interval changes and open gaps, then refresh and reconcile what changed after the visit.
- Health OS should use host-runtime conversation, approvals, tasks, automations, and notifications. It supplies deterministic commands and health workflows: **batteries included, infrastructure omitted**.
- Deep Review remains an escalation workflow for complex cases, not the headline product or the default response to routine care coordination.

## Working today

### Packaging and distribution

- Claude and Codex plugin manifests, with `memory` and `chart` skills.
- Public repository and marketplace install: <https://github.com/dipakkrishnan/health-os>
- GitHub Pages hosts documentation, terms, and the production OAuth callback relay.

### Epic connectivity

- Epic patient-facing app registered for R4/USCDI v3, public-client PKCE, and dynamic-client JWT renewal.
- Public sandbox validated end to end: login, dynamic registration, unattended token renewal, repeated syncs, and deduplication.
- Production app marked ready on 2026-07-16; propagation was still in progress at the last check.
- `core/connect.py connect` performs organization lookup, PKCE authorization, dynamic registration, and first sync.
- `core/connect.py resync` refreshes an existing connection without another interactive login; credentials remain in macOS Keychain.
- The data model and CLI can hold and address multiple named connections, although setup and refresh-all orchestration are not yet a polished user workflow.

### Local health core

- SQLite contract and schema with append-only resource versions, exact content-addressed FHIR response bytes, and per-run/page audit records.
- Current ingestion: patient demographics, labs, medication orders, conditions, allergies, and encounters.
- Deterministic sync, parse, status, delta, timeline, citation, and verification commands.
- All normalized evidence pointers are resolvable; `verify` exits nonzero for dangling source or memory citations.
- Persistent cited memory with bootstrap and incremental updates over a local data repository.
- Sandbox proof: four complete syncs with zero duplicate clinical items on repeat runs.

## Important gaps

These are workflow gaps, not reasons to build a larger platform first.

1. **No real-patient baseline yet.** Production propagation and a first live connection still need to be exercised.
2. **No setup/first-refresh skill.** The agent does not yet guide multi-system inventory, explain source coverage, interview the patient or caregiver, or confirm a skeptical baseline.
3. **Appointments are not ingested.** Epic exposes [FHIR R4 Appointment search](https://fhir.epic.com/Specifications?api=10469), but `Appointment` is not in the current dataset or normalized views.
4. **The three truths are not represented.** The core preserves imported evidence and corrections, but has no complete structure or workflow for clinical intent, lived reality, unresolved conflicts, and reconciliation history.
5. **No proactive continuity loop.** There is no next-visit detection, visit-preparation skill, post-visit refresh, or change reconciliation.
6. **Multiple connections are low-level.** Named connections exist, but users cannot yet connect, assess, and refresh several systems as one coherent record.
7. **Native automations are not packaged.** `resync` is schedulable, but the skill does not offer to configure or manage the host runtime's automation and notification facilities.
8. **Important feeds remain absent.** Notes, diagnostic reports, vitals, procedures, service requests, immunizations, portal messages, medication use, symptoms, and patient observations should be added as the appointment and reconciliation workflows demand them.
9. **Operational hardening is incomplete.** Updates, deletions, partial failures, authorization expiry, per-system coverage differences, and refresh-all recovery need live exercise.

## Next vertical slice

The next milestone is not “more FHIR.” It is one complete continuity loop around a real appointment.

1. **Ship setup and first refresh.** Guide explicit local-repository setup; inventory providers and portals; connect one or more systems; show permissions and coverage; import records; interview the patient or caregiver; and save a confirmed baseline with conflicts intact. Never silently fall back to demo data.
2. **Make refresh a multi-system user operation.** Add a clear `refresh` surface (keeping compatibility with `resync`), refresh all selected connections, summarize changes and failures per source, and verify the repository afterward.
3. **Ingest appointments.** Add FHIR `Appointment` search, preservation, normalization, coverage reporting, and a deterministic `next appointment` query. Document Epic's source-specific omissions rather than implying completeness.
4. **Build visit preparation.** Detect the next visit; identify the relevant clinician and prior encounter; compare interval changes; surface medication and plan conflicts, missing follow-up, and incomplete data; ask focused questions about lived reality; then emit a compact cited artifact in the active agent task.
5. **Close the loop after the visit.** Refresh relevant systems, detect new notes, orders, results, referrals, and appointments, and ask the user to reconcile clinical intent with the plan that will actually be followed.
6. **Offer runtime-native automation.** Let the skill offer recurring refresh and appointment-triggered preparation using the host agent's scheduler, permissions, task continuity, and notifications. Health OS owns the command and workflow recipe, not the scheduler.
7. **Add only the feeds the loop exposes as necessary.** Likely early additions are notes/DocumentReference, DiagnosticReport, Observation categories beyond labs, ServiceRequest, Procedure, and patient/caregiver reports. Validate each against a real decision in the workflow.
8. **Evaluate with a real care episode.** Measure whether the loop finds a meaningful discrepancy, reduces preparation work, preserves the three truths, and produces questions a patient or caregiver actually uses.

## Validation questions for the slice

- Did the agent know which systems and date ranges it had—and did not have?
- Did it find the next appointment without the user restating it?
- Did it distinguish orders, clinician intent, and actual behavior?
- Did its questions change or correct the baseline rather than merely collect biography?
- Could the user inspect every material claim, interrupt the work, and correct it?
- Did the post-visit refresh identify what changed and who must do what next?
- Did the result appear naturally in the existing agent task and persist locally?
- Was the cognitive burden lower than manually opening portals and reconstructing the story?

## Explicitly deferred

- A standalone UI or mobile app
- A custom scheduler, daemon, or notification service
- A hosted Health OS account or cloud record
- Broad parser expansion without a workflow need
- A universal clinical ontology or general episode engine
- Full Deep Review infrastructure before the continuity loop demands it
