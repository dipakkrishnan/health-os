# Health OS — Progress

## Done
- Design thesis: `design-thesis.md`
- Epic on FHIR app registered: **"Health OS"** — patient-facing, USCDI v3 auto-distribution,
  R4 everywhere, SMART v1 scopes, public client + PKCE, dynamic clients (JWT bearer grant)
  - Non-production client ID: `2da9c3f3-6f6e-45a9-8d89-84eaa7f48007`
  - Production client ID: `ae8f0930-576b-4f19-a146-a2a3745d60dc` (NOT yet marked ready for production)
  - Redirect URIs: `http://localhost:8965/callback` (dev), `https://dipakkrishnan.github.io/health-os/callback` (prod relay — page not built yet)
- Epic public sandbox validated end to end against Camila Lopez:
  - PKCE login and localhost callback succeeded
  - Epic granted `system/DynamicClient.register` and the configured patient read scopes
  - Dynamic registration returned a device client ID
  - A signed RS256 JWT minted a new bearer token without another login
  - Four complete syncs ran; every repeat, including fresh-process runs, inserted zero duplicate clinical items
- Deterministic local health core: `core/`
  - Contract and SQLite schema: `core/CONTRACT.md`, `core/schema.sql`
  - Exact content-addressed FHIR response bytes and per-run/page audit records
  - Append-only resource versions and resolvable evidence pointers
  - Parsers for labs, medication orders, conditions, allergies, and encounters
  - Dynamic registration/JWT helper: `core/epic_auth.py`
  - Sync/parse/status CLI: `core/health_core.py`
  - Unit/integration-style tests: `core/test_core.py`
- Reproducible live proof artifacts:
  - Safe result summary: `spike/dynamic_result.json`
  - Local sandbox repository: `spike/health-data/`
  - Sandbox RSA key: `spike/state/epic-sandbox.pem` (mode 0600; development only)
  - Plaintext OAuth token response was deleted after registration

- Review pass on the overnight core:
  - Verified: 4 complete syncs, zero duplicate items, schema v2, dynamic JWT auth artifacts
  - Fixed: 13/60 evidence pointers dangled (parser hardcoded field paths) → parser `fhir-r4-v2`
    emits only resolvable pointers; sandbox items regenerated; 54/54 pointers now resolve
  - Added: `health_core.py verify` — CLI grounding check, nonzero exit on any dangling pointer

## Now
- The data plane required by the user-authored timeline skill is ready.
- Current sandbox counts: 21 current resource versions and 15 normalized clinical items
  (1 lab, 1 medication order, 7 conditions, 1 allergy, 5 encounters).
- All stored raw hashes and clinical-item resource pointers were checked against the live sandbox files.

- Live-readiness infrastructure (2026-07-14):
  - GitHub Pages published: `/health-os/` docs, `/health-os/terms`, `/health-os/callback` OAuth relay
  - macOS Keychain credential storage (`keychain:<service>` refs) — roundtrip + JWT signing tested
  - `core/connect.py`: `connect` (org lookup -> PKCE -> dynamic registration -> first sync)
    and `resync` (unattended cron path — proven live against sandbox: JWT mint, sync, verify, no login)
  - Epic endpoint directory lookup works (NYU Langone -> epicfhir.nyumc.org FHIR R4 base)

## Next
1. USER ACTION: mark app ready for production on fhir.epic.com (T&C + docs pages are live); wait out
   propagation (~1 day), then: `python3 core/connect.py connect --repo <repo> --connection nyu --org "NYU Langone"`
2. First real value: visit-prep skill over live data (timeline + med list + questions, every claim cited)
3. Timeline skill scaffolded (2026-07-14) following the deep-review-skill plugin pattern:
   canonical source in `skills/timeline/` (SKILL.md + references/), `.claude/skills/timeline`
   symlinked to it, plugin manifests (`.claude-plugin/`, `.codex-plugin/`), README + PRIVACY.
   Deterministic `timeline` and `cite` subcommands in health_core.py (tested). Repo git-initialized
   (.gitignore excludes health data/keys); first commit pending. Refine against real data.
4. Parser v3: Epic negation placeholders ("Not on File"); extend DATASETS to vitals, notes,
   procedures, immunizations, diagnostic reports (spike/out/ has sandbox fixtures for all).
5. launchd job wiring `resync` per connection; exercise updates/deletions and partial-failure recovery.
6. Onboarding interview skill (coverage map, patient-reported items, boot confirmation artifact).
