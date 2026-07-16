---
name: memory
description: Bootstrap and maintain the persistent, cited memory of the user's health record — a set of markdown files (timeline, medications, conditions, gaps) derived from the local health core. Use after a sync reports new items, when the user asks to update or rebuild their health memory, or when another health skill finds the memory missing or stale.
---

# Health Memory

The memory is the agent's durable, consolidated understanding of the health record:
`memory/` inside the data repo, containing a manifest and cited markdown files. It is
a derived cache — the database is always the truth, and the memory must be fully
regenerable from it. You never write to the database itself.

## Start Here

1. Resolve the core CLI: `${CLAUDE_PLUGIN_ROOT}/core/health_core.py` when running as
   an installed plugin, else `core/health_core.py` from the project root.
2. Resolve the data repo: `$HEALTH_OS_REPO` if set, else `~/health-data` if it
   exists, else `spike/health-data` (sandbox) in the project.
3. Read `references/memory_format.md` for the file layout and manifest schema, and
   the chart skill's `references/grounding_rules.md` — memory files obey the same
   rules: every factual line cites `[ci:<12-char id>]`, orders are not use, unknown
   dates stay unknown, placeholders like "Not on File" are absences.
4. Read `memory/manifest.json` if it exists, then choose the path:
   - **No manifest → bootstrap.** Query the record per domain (`timeline --kind ...`),
     consolidate, and write the memory files. Duplicate assertions (e.g. the same
     diagnosis recorded per encounter) become ONE line with multiple citations.
   - **Manifest present → incremental update.** Run
     `delta --repo <repo> --after <synced_through_run>`. If `new_items` is empty,
     report that memory is current and stop. Otherwise process only the delta.
5. For each delta item, ask what existing memory it touches — a new item may extend
   the timeline, but it may also contradict a line (a condition resolved, a corrected
   result, a med discontinued). Edit the affected line rather than appending a
   duplicate; move superseded statements to the file's `## History` section with a
   note of what replaced them.
6. Write `manifest.json` with `synced_through_run` = the `latest_run` from the delta
   (or `latest_sync_run_id` from `status` when bootstrapping) and `updated_at`.
7. Always finish with `verify --repo <repo>` — it resolves every `[ci:…]` citation in
   the memory files against current clinical items and fails on danglers. A failing
   verify means fix the memory before reporting success.

## Rebuild

On explicit request ("rebuild my health memory"), when `verify` fails irreparably, or
when the manifest's watermark run no longer exists: delete the memory files and
bootstrap from scratch. Incremental updates accumulate small drift; a rebuild is
cheap and the record loses nothing — that is the point of memory being derived.

## Principles

- Memory is cache; the database is truth. Never resolve a conflict in memory's favor.
- Consolidation is the value: many items, one cited line.
- Deltas can invalidate, not just append. Look for contradictions before adding.
- Interpretation ("likely one continuing episode") is labeled as such, in place.
- Patient-reported facts are recorded in memory only as clearly patient-reported;
  promotion into the record itself is a core concern, not a memory edit.

## Bundled Resources

- `references/memory_format.md`: file layout, manifest schema, consolidation rules.
