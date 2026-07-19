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
- Current ingestion: patient demographics, labs, vitals, medication orders and dispenses, conditions, allergies, encounters, longitudinal care plans, clinical documents and same-origin Binary content, service requests, diagnostic reports, and procedures.
- The `document` command renders stored note/report/summary attachments (HTML, RTF, C-CDA XML) as plain text for reading and citation; `verify` checks citations in `memory/` and `artifacts/`.
- `status` exposes each system, represented patient, recorded OAuth scopes or `unknown`, unattended-refresh capability, latest refresh result, and every expected dataset including `not_queried` ones.
- Deterministic sync, parse, status, delta, timeline, citation, patient/caregiver report capture, and verification commands.
- `verify` checks normalized evidence pointers plus citations to both imported clinical items and immutable local patient/caregiver reports.
- Memory v2 preserves recorded evidence, clinical intent, and lived reality separately while maintaining compact views of medications, appointments, the care plan, conflicts, and source coverage.
- Sandbox proof: four complete syncs with zero duplicate clinical items on repeat runs.

## Important gaps

These are workflow gaps, not reasons to build a larger platform first.

1. **No real-patient baseline yet.** Production propagation and a first live connection still need to be exercised.
2. **First-refresh skill is a draft.** `skills/refresh` guides setup, coverage explanation, the skeptical interview, and the cited baseline artifact; it has been exercised against sandbox persona runs but not a real patient or a real first-time user.
3. **No next-appointment discovery.** Epic's Appointment API is non-USCDI and denied to the auto-distributed client, so the record cannot supply upcoming visits directly. Discovery must combine care-plan activity, the host runtime's calendar and email connectors, and user reports; no skill implements that yet.
4. **No interactive reconciliation workflow.** Memory can represent and cite the three truths, but no skill yet conducts the skeptical interview or confirms an operational baseline with the user.
5. **No proactive continuity loop.** There is no visit-preparation skill, post-visit refresh, or change reconciliation.
6. **Multiple connections are low-level.** Named connections and honest per-system coverage exist, but users cannot yet refresh several systems as one coherent operation.
7. **Native automations are not packaged.** `resync` is schedulable, but no skill offers to configure or manage the host runtime's automation and notification facilities.
8. **Some feeds remain absent.** Immunizations, portal messages, device/wearable data, and structured symptoms remain workflow-driven additions. Actual medication use and patient observations must still come from explicit reports rather than being inferred from FHIR.
9. **Operational hardening is incomplete.** Resource disappearance, partial failures, authorization expiry, institution-specific API differences, and refresh-all recovery need live exercise.

## Next vertical slice

The next milestone is not “more FHIR.” It is one complete continuity loop around a real appointment.

1. **Ship the interactive first refresh.** Inventory providers and portals; connect one or more systems; show permissions and coverage; interview the patient or caregiver; and save a confirmed baseline with conflicts intact. Setup is explicit and never falls back to demo data.
2. **Make refresh a multi-system user operation.** Add a clear `refresh` surface (keeping compatibility with `resync`), refresh all selected connections, summarize changes and failures per source, and verify the repository afterward.
3. **Add next-appointment discovery.** Resolve the next visit from care-plan activity, the runtime's calendar and email connectors, and user reports; document source-specific omissions rather than implying completeness.
4. **Build visit preparation.** Detect the next visit; identify the relevant clinician and prior encounter; compare interval changes; surface medication and plan conflicts, missing follow-up, and incomplete data; ask focused questions about lived reality; then emit a compact cited artifact in the active agent task.
5. **Close the loop after the visit.** Refresh relevant systems, detect new notes, orders, results, referrals, and appointments, and ask the user to reconcile clinical intent with the plan that will actually be followed.
6. **Offer runtime-native automation.** Let the skill offer recurring refresh and appointment-triggered preparation using the host agent's scheduler, permissions, task continuity, and notifications. Health OS owns the command and workflow recipe, not the scheduler.
7. **Add only the feeds the loop exposes as necessary.** The initial first-refresh feeds are present; validate each against a real decision before adding more.
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
