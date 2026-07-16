# Health OS

A private, local-first personal health record with grounded agent skills on top.

The **health core** (`core/`) syncs your records from your health systems'
patient-access FHIR APIs into a versioned local SQLite store with full provenance —
every normalized clinical item points to the exact response bytes it came from, and
`health_core.py verify` mechanically checks that every evidence pointer resolves.

**Skills** (`skills/`) are thin, replaceable workflows that present that record.
Every stated fact carries a citation that resolves back to source bytes.

- `memory` — builds an understanding of your data first: bootstraps and maintains
  persistent, cited context across recorded evidence, clinical intent, and lived
  reality. Imported facts and explicit patient/caregiver reports retain different,
  mechanically checked citations.
- `chart` — consults that understanding to answer questions: lab trends, medication
  history, appointments, notes, open orders, conditions, encounters, and grounded
  chronological views — every fact cited.

More to come: visit prep, medication reconciliation, cross-specialty deep review.

Read the [design thesis](design-thesis.md) for the full picture, and
[PROGRESS.md](PROGRESS.md) for current status.

## Install

### Claude Code

```text
/plugin marketplace add dipakkrishnan/health-os
/plugin install health-os@health-os-marketplace
/reload-plugins
```

Or clone this repository and run Claude Code inside it — the skills load from
`.claude/skills/`.

### Codex

Install **Health OS** from Plugins in the Codex app, or clone this repository and
open it as a local project while developing. The same skills are shared by both
runtimes; only their native scheduling instructions differ.

## Setup

Connect a health system (one-time, interactive — opens your patient portal login):

```bash
pip install -r core/requirements.txt
python3 core/connect.py connect --repo ~/health-data --connection nyu --org "NYU Langone"
```

Repeat `connect` with another `--connection` name to add another health system.

Keep one connection fresh (unattended and suitable for a runtime-native local
scheduled task):

```bash
python3 core/connect.py resync --repo ~/health-data --connection nyu
```

Then ask your agent for a timeline.

## Privacy

There is no Health OS server. Records go directly from your health system to your
machine and stay there; credentials live in the OS keychain. See
[PRIVACY.md](PRIVACY.md) and the [terms](https://dipakkrishnan.github.io/health-os/terms.html).

## Status

Early and under active development. Epic (sandbox-verified) is the first supported
EHR vendor. Not a medical device; not a substitute for care from your clinicians.
