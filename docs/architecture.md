# Architecture

```
MCP client (agent) --stdio--> server (policy, validation, skills, envelopes)
                                  |  one lock, one request at a time, timeouts
                                  v
                              worker process --DaVinciResolveScript--> DaVinci Resolve Studio (Fusion)
```

## Server (`fusion_connector/server.py`)

- Speaks MCP over stdio and exposes 11 tools: `fu_get_skill`, `fu_get_skill_asset`, `fu_project_info`,
  `fu_comp_info`, `fu_tool_info`, `fu_render_frame`, `fu_comp_export`, `fu_version_info`, `fu_context`,
  `fu_catalog`, `fu_do`. They mirror the tool set of Higgsfield's After Effects connector.
- `fu_do` runs one operation from the catalog (179 operations in 36 categories, `fusion_connector/ops/`), or
  many through `batch.run` (one call, one undo event, not transactional). `dryRun` validates and checks policy
  without touching Resolve.
- Before anything reaches Resolve, the server validates arguments against the operation's schema (types,
  enums, unknown keys with spelling suggestions) and checks registry IDs, input IDs and option strings against
  the harvested tables in `skills/fusion-reference/data/`.
- Policy (read-only mode, category allowlist, project allowlist, eval and template-install opt-ins) is checked
  in the server and shipped to the worker with every call ([install.md](install.md#6-policy-switches)).
- Replies are compact envelopes (`ok`, `result` or `error {code, message, hint}`). Replies over the response
  budget are written to `out/responses/` and replaced by a preview with the path. Renders come back inline as
  images, so the agent sees its own work without a second read.

## Worker (`fusion_connector/worker.py`)

- The only process that talks to Resolve. It is spawned once and receives one request at a time over a pipe;
  the server holds one lock, so parallel MCP calls never interleave inside Resolve.
- It redirects stdout to stderr, because Resolve and Fusion print to stdout and must never corrupt the MCP
  channel.
- On timeout the server kills the worker and reports `TIMEOUT` with `uncertain: true`: the call may have run,
  so the agent re-reads state instead of retrying blindly. The next call gets a fresh worker.
- Every call starts with a UI check. A modal dialog makes Resolve return `None` for basic calls; the worker
  reports `UI_BLOCKED` instead of pretending the project is empty, after dismissing Resolve's own render
  dialogs (`dismiss_render_modal.applescript`). During a Deliver render calls return `RENDERING`, while
  `deliver.status`, `deliver.stop` and `system.memory` keep working.

## Skills (`fusion_connector/skills.py`)

`fu_get_skill` serves the skills with a sha256 manifest (`connector/skills-manifest.json`, rebuilt at start):
a file edited after the manifest was built is refused until the manifest is rebuilt. Documents over about
34,000 characters come back in pages with a heading table of contents, and `section: "<heading>"` returns one
section, including across split reference files.

## Scene builder (`fusion_connector/scenegraph.py`, `ops/scene.py`)

Compiles a layer-level JSON description into native Fusion `.setting` text offline, then pastes it in one call.
See [scene-builder.md](scene-builder.md).

## Graph layout (`fusion_connector/layout.py`, `ops/layout.py`)

Plans node positions and labeled backdrops for the house graph style. See [graph-layout.md](graph-layout.md).

## Disk caches (`ops/cache.py`)

Renders a locked branch to PNG once and swaps a Loader in. See [caching.md](caching.md).

## Tests

- `tests/test_offline.py`, `tests/test_layout.py`: 172 offline unit tests (no Resolve). Tests that need the
  private benchmark fixture, the LuaJIT inside Resolve.app, or the harvested data tables skip themselves with a
  reason when those are missing.
- `tests/smoke.py`, `tests/cache_live.py`, `tests/layout_live.py`, `tests/sb3_live.py`: live checks through the real server in a
  scratch Resolve project (they run with the project allowlist set to `Testbed`, work on timelines they create
  and delete them in their cleanup stage).
- `scripts/parity.py` regenerates `PARITY.md` from the After Effects connector's operation registry (not
  shipped; see CREDITS.md) and `tests/smoke_results.json`.
