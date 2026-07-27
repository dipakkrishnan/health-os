# Health OS — Progress

Updated 2026-07-26

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

- Claude and Codex plugin manifests, with `refresh`, `memory`, `chart`,
  `morning-brief`, and `visit-prep` skills.
- Public repository and marketplace install: <https://github.com/dipakkrishnan/health-os>
- GitHub Pages hosts documentation, terms, and the production OAuth callback relay.

### Epic connectivity

- Epic patient-facing app registered for R4/USCDI v3, public-client PKCE, and dynamic-client JWT renewal.
- Public sandbox validated end to end: login, dynamic registration, unattended token renewal, repeated syncs, and deduplication.
- Production access validated against a real Mount Sinai patient account.
- `core/connect.py connect` performs organization lookup, PKCE authorization, dynamic registration, and first sync.
- `core/connect.py resync` refreshes an existing connection without another interactive login; credentials remain in macOS Keychain.
- The data model and CLI can hold and address multiple named connections, although setup and refresh-all orchestration are not yet a polished user workflow.

### Local health core

- SQLite contract and schema with append-only resource versions, exact content-addressed FHIR response bytes, and per-run/page audit records.
- Current ingestion: patient demographics, labs, vitals, medication orders and dispenses, conditions, allergies, encounters, longitudinal care plans, clinical documents and same-origin Binary content, service requests, diagnostic reports, and procedures.
- The `document` command renders stored note/report/summary attachments (HTML, RTF, C-CDA XML) as plain text for reading and citation; `verify` checks citations in `memory/` and `artifacts/`.
- `status` exposes each system, represented patient, recorded OAuth scopes or `unknown`, unattended-refresh capability, latest refresh result, and every expected dataset including `not_queried` ones.
- Deterministic sync, parse, status, delta, timeline, citation, patient/caregiver report capture, and verification commands.
- `verify` checks normalized evidence pointers plus citations to imported clinical
  items, immutable patient/caregiver reports, sync runs, and runtime-connector
  observations.
- Memory v2 preserves recorded evidence, clinical intent, and lived reality separately while maintaining compact views of medications, appointments, the care plan, conflicts, and source coverage.
- Sandbox proof: four complete syncs with zero duplicate clinical items on repeat runs.
- Real-patient proof: a first refresh imported 117 current clinical items, conducted
  a five-question reconciliation interview, used Google Calendar when MyChart did
  not expose appointments, and produced a baseline with 447 source pointers and no
  dangling citations.

## Important gaps

These are workflow gaps, not reasons to build a larger platform first.

1. **The magic moment is not yet validated.** `morning-brief` and `visit-prep` now
   define the workflow, but neither has carried a real appointment from preparation
   through follow-up.
2. **No post-visit reconciliation.** The system does not yet refresh after an
   encounter and reconcile new clinician intent with what will actually happen.
3. **Multiple connections are low-level.** Named connections and honest per-system
   coverage exist, but users cannot yet refresh several systems as one coherent
   operation.
4. **Automations are recipes, not validated behavior.** Skills can offer a paired
   caregiver morning brief and visit-horizon check through Codex automations or
   Claude scheduled tasks/routines, but the pair has not run longitudinally.
5. **Some feeds remain absent.** Immunizations, portal messages, device/wearable
   data, and structured symptoms remain workflow-driven additions. Actual medication
   use and patient observations must still come from explicit reports rather than
   being inferred from FHIR.
6. **Operational hardening is incomplete.** Resource disappearance, partial
   failures, authorization expiry, institution-specific API differences, and
   refresh-all recovery need more live exercise.

## Next vertical slice

The next milestone is not “more FHIR.” It is one complete continuity loop around a real appointment.

1. **Land operational provenance.** Verify sync citations and preserve bounded
   observations after the runtime's Calendar connector searches, without adding a
   Google client to Health OS.
2. **Review the paired skills.** Refine the caregiver morning brief and visit-prep
   workflow against the original caregiver interview.
3. **Exercise the automations locally.** Run a morning brief followed by a quiet
   visit-horizon check; verify that the second workflow reuses the first artifact and
   that task/session history is continuity context rather than uncited medical fact.
4. **Evaluate one real appointment.** Find it without requiring the user to restate
   it, compare interval changes and unresolved work, and produce questions the
   patient or caregiver actually uses.
5. **Close the loop after the visit.** Refresh relevant systems, detect new notes,
   orders, results, referrals, and appointments, and reconcile clinician intent with
   what will actually happen.
6. **Add only the feeds the loop exposes as necessary.** The initial first-refresh
   feeds are present; validate each addition against a real decision.

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
