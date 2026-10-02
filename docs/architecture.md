# Architecture

```
MCP client (agent) --stdio--> server (policy, validation, skills, envelopes, receipts)
                                  |  one lock, one request at a time, timeouts
                                  v
                              worker process --DaVinciResolveScript--> DaVinci Resolve Studio (Fusion)
                                  |  one fsynced line per step; the server reads it after a kill
                                  v
                              out/journal/<callId>.jsonl
```

## Server (`fusion_connector/server.py`)

- Speaks MCP over stdio and exposes 15 tools. Eleven mirror the tool set of Higgsfield's After Effects connector:
  `fu_get_skill`, `fu_get_skill_asset`, `fu_project_info`, `fu_comp_info`, `fu_tool_info`, `fu_render_frame`,
  `fu_comp_export`, `fu_version_info`, `fu_context`, `fu_catalog`, `fu_do`. Four are dedicated tools for the
  most-used operations: `fu_scene_build`, `fu_scene_plan`, `fu_batch` and `fu_contact_sheet` (see below).
- `fu_do` runs one operation from the catalog (181 operations in 36 categories, `fusion_connector/ops/`), or
  many through `batch.run` (one call, one undo event; all or nothing only with `atomic: true`). `dryRun`
  validates and checks policy without touching Resolve.
- `fu_catalog` returns the categories, one category with full parameters, one operation (`operation`: its
  parameters, category, sibling operations and dedicated tool, if any), or the top ten matches of a keyword
  search over names and descriptions (`query`, optionally within a `category`). It lists only the operations
  the current policy allows, and it rejects unknown arguments with a suggestion.
- Before anything reaches Resolve, the server validates arguments against the operation's schema (types,
  enums, unknown keys with spelling suggestions) and checks registry IDs, input IDs and option strings against
  the harvested tables in `skills/fusion-reference/data/`. Every `INVALID_ARGS` reply, from these checks, from
  inside the operation or from a failed batch child, lists the operation's parameters in `details.expected`
  (type, required, allowed values, default), so the agent can fix the call without a catalog lookup.
- Policy (read-only mode, category allowlist, project allowlist, eval and template-install opt-ins) is checked
  in the server and shipped to the worker with every call ([install.md](install.md#6-policy-switches)).
- Replies are compact envelopes (`ok`, `result` or `error {code, message, hint}`). Replies over the response
  budget are written to `out/responses/` and replaced by a preview with the path. Renders come back inline as
  images, so the agent sees its own work without a second read.

## Dedicated tools and generated schemas

`fu_scene_build` (`scene.build`), `fu_scene_plan` (`scene.plan`), `fu_batch` (`batch.run`) and
`fu_contact_sheet` (`render.contact_sheet`) are each `fu_do` with one operation. The server passes their
arguments on as that operation's `args` (with `timeoutMs` and `dryRun` as on `fu_do`), so they go through the
same validation, policy gate and dry run.

Their input schemas are generated from the operation's parameter list (`schema.json_schema`: types, enums,
defaults, required parameters, no unknown keys). It is the same list that `fu_catalog` prints and the validator
checks, so a schema cannot drift from its operation. The MCP SDK checks each call against the schema before it
reaches the server; `fu_catalog`'s own schema is generated the same way. A dedicated tool is listed only when
the policy allows its operation: read-only mode keeps `fu_scene_plan` and `fu_batch` (whose children are
checked one by one), and a category allowlist hides the tools whose operations fall outside it.

## Worker (`fusion_connector/worker.py`)

- The only process that talks to Resolve. It is spawned once and receives one request at a time over a pipe;
  the server holds one lock, so parallel MCP calls never interleave inside Resolve.
- It redirects stdout to stderr, because Resolve and Fusion print to stdout and must never corrupt the MCP
  channel.
- On timeout the server kills the worker and reports `TIMEOUT` with `uncertain: true`: the call may have run,
  so the agent re-reads state instead of retrying blindly. The next call gets a fresh worker. The reply carries
  a receipt from the call's journal (below).
- Every call starts with a UI check. A modal dialog makes Resolve return `None` for basic calls; the worker
  reports `UI_BLOCKED` instead of pretending the project is empty, after dismissing Resolve's own render
  dialogs (`dismiss_render_modal.applescript`). During a Deliver render calls return `RENDERING`, while
  `deliver.status`, `deliver.stop` and `system.memory` keep working.

## Journal and receipts (`fusion_connector/journal.py`)

Killing the worker on a timeout also kills the results of the steps that had already run. The journal keeps
them on disk.

- The server gives every operation call it sends to the worker a call id, and the worker writes
  `<out>/journal/<callId>.jsonl` as it runs: one JSON line per event, flushed and fsynced so it survives a kill.
  The lines are a header (operation, target comp, a batch's child operations), the comp snapshot before the
  first change, the undo group opening and closing, each step's start (with the tool names its arguments point
  at) and end (`ok` with what its result reports it changed, or the error), an atomic rollback, and `done`. A
  batch's header also holds a short hash of each step's arguments, and a resumed batch logs the steps it skipped.
  The newest 200 journals are kept. A journal that cannot be written never fails the call.
- Batches take the snapshot: the tool count, plus every tool name with `snapshot: "names"` or `atomic: true`
  when the comp holds at most `FUSION_MCP_SNAPSHOT_LIMIT` tools (default 1,500; names cost one call per tool).
  A single operation's journal has no snapshot, so recovery can check the uncertain step's target tools but
  not the comp's tool count, and a rollback of it reports `verified: null` (nothing to compare).
- After a `TIMEOUT`, or a `TRANSPORT` error when the worker died, the server reads the journal (a torn last line
  is dropped) and reconciles it into `details.receipt`: completed steps and their changes, failed steps, the
  step that was running and its target tools, the steps that never started, the undo group state (`open`,
  `closed` or `none`) and the snapshot. The message gains a one-line summary, for example "Receipt: steps 0-1
  finished; step 2 (tool.add on 'Title') was running and may have partly applied; steps 3-4 never started. The
  batch's undo group was left open." The hint names the recovery calls.

## Recovery (`fusion_connector/ops/recover.py`)

- `batch.recover {callId}` is read-only; without `callId` it takes the newest call that never finished. It
  re-reads the comp the call targeted: the tool count against the snapshot, added and removed tools when the
  snapshot holds names, whether each uncertain step's target tools exist, and later changes on the same comp.
  It ends with advice: roll back or keep an open undo group, inspect the uncertain step, then re-run from the
  first unfinished step.
- `batch.rollback {callId}` closes an undo group the dead worker left open (`EndUndo`), undoes the call (one
  `Undo`) and verifies the comp against the snapshot: the tool count, the names when the snapshot has them, and
  that the tools the finished steps report they created are gone. `keep: true` only closes the group and keeps
  the changes. An undo reverts the newest event, so rollback refuses with `CONFLICT` when a later journaled
  change targeted the same comp; `force: true` overrides. It cannot see changes made outside the connector (the
  official Resolve MCP, a person working in Fusion), so recovery comes before anything else touches the comp. A
  call that never opened an undo group has nothing to undo.
- `batch.run {ops, resume: callId}` finishes an unfinished batch instead. The caller sends the same ops: the
  connector checks the operation names and the argument hashes of the finished steps against the journal, skips
  those steps, and runs the rest. A step that was running, or failed, may have partly applied: by default
  (`uncertain: "check"`) it runs again only when none of its target tools exist. A step that names no tools (a
  paste) runs again only when the comp holds no tools that the snapshot and the finished steps do not explain,
  and never without a snapshot. Otherwise the call stops with `CONFLICT` so the agent can inspect and choose
  `skip` or `rerun`. The dead worker's undo group is closed first,
  so the resumed part is its own undo event. Afterwards the comp is read back: every tool the batch meant to
  create exists, and no new tool is a renamed copy of one (Fusion names a repeated tool `Title1`, or `Title_1`
  in a paste, instead of failing, which is what a plain retry of the whole batch would cause). New tools that no step reported creating
  are listed for a look. A call is resumed once; resume and
  `atomic` do not combine.
- Rollback undoes only with evidence that the call changed something: a step that finished, or a comp that
  differs from the snapshot. An undo group that recorded no change may not be an undo event, and one `Undo`
  after it would revert an earlier, unrelated change. Without that evidence it closes the group, undoes nothing
  and says why; `force: true` undoes anyway. It records what it did in the call's journal, so a second rollback
  of the same call is refused with `CONFLICT` and `batch.recover` no longer picks the call by default.

## Atomic batches

`batch.run {atomic: true}` stops at the first failure, undoes the batch's undo event and verifies the comp
against a names snapshot. The error says whether the rollback was verified, and `details.rollback` holds the
evidence. Before the first step, an atomic batch refuses every child that one undo on the batch comp cannot
revert: operations outside the comp (timeline, project, Deliver), operations without an undo event, and steps
that target another comp. It also refuses up front when a child failed validation. Reads may ride along. The
same evidence rule as rollback applies: when the first step fails, no step finished and the tool list matches
the snapshot, nothing is undone (`rolledBack: false`), and the hint says how to check for input changes. Without `atomic`, a failed batch keeps its completed steps,
and one `comp.undo` still reverts the whole batch.

## What only real Fusion can confirm

The offline tests run these paths through the real server and a real worker process against a fake Resolve
(below). Some behaviors belong to Fusion itself: whether a killed worker leaves the comp's undo group open,
whether closing that group and one `Undo` revert exactly the batch on a real comp (rollback, `keep`, atomic),
whether `setting.paste`, which runs as a deferred Lua `Execute`, lands inside the batch's undo group, whether an
undo group that recorded no change is an undo event at all (`test.undo_probe`), how Fusion names a tool whose
name is taken (what a plain retry would do), and whether a resumed batch finishes without duplicates.
`tests/receipts_live.py` checks them in a scratch project.

All of its stages passed on 2026-10-01 in Resolve Studio 21.1.0.14. A killed worker leaves the undo group open,
and closing it then undoing once reverts exactly the batch. A deferred paste lands inside the batch's undo group.
Fusion drops an undo group that recorded no change, which is why rollback needs evidence of a change before it
undoes. Renaming a tool onto a taken name appends a digit (`RL_Dup1`) instead of failing, and a resumed batch
finished with no duplicates.

## Scripting-port check (`fusion_connector/diag.py`)

Scripting clients reach Resolve on TCP port 49152. After a Resolve restart, a process from the old session (a
Workflow Integration plugin helper, an old `fuscript -s`) can keep that port; the new Resolve then registers on
49153 and every client hangs without an error. The check reads `lsof` and `ps`, so it answers while scripting
hangs. A holder of 49152 counts as Resolve's when it descends from the running Resolve or shares its socket (a
plugin that the running Resolve started also has parent PID 1); any other holder is an orphan.
`fusion-connector doctor` lists the holders; when it finds an orphan, it names it with the fix and skips its own
Resolve call, which would hang. On every `TIMEOUT` the server runs the same check (bounded, skipped on Windows)
and adds the problem and its fix to the hint.

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

## Fake Resolve for tests (`fusion_connector/testkit.py`)

A file-backed stand-in for Resolve and Fusion. Its comp state (tools and undo groups) lives in a JSON file, so,
like the real app, it survives a killed worker. Undo groups behave like Fusion's: the actions inside
`StartUndo`/`EndUndo` form one event, and `Undo(n)` reverts the newest closed events. Test-only operations add
tools (`test.add`), fail after a partial change (`test.partial`), stall (`test.hang`), kill the worker
mid-call (`test.crash`) or measure how undo groups that recorded nothing are treated (`test.undo_probe`). The
fake keeps such groups as events by default; a flag in its state file makes it drop them, the other behavior an
app can have, so the tests cover both.

The kit is inert unless `FUSION_MCP_FAKE_RESOLVE=<state file>` (the worker then talks to the fake) and
`FUSION_MCP_TEST_FAULTS=1` (registers the `test.*` operations) are set. The test operations refuse a real
Resolve, except for the live check in the project named `Testbed` with `FUSION_MCP_TEST_FAULTS_LIVE=1`.

## Tests

- `tests/test_offline.py`, `tests/test_layout.py`, `tests/test_catalog_tools.py`, `tests/test_receipts.py`,
  `tests/test_diagnostics.py`: 237 offline unit tests (no Resolve). `test_receipts.py` drives the real server
  and a spawned worker through the fake Resolve's faults: receipts on `TIMEOUT` and `TRANSPORT`, recover,
  rollback with and without `keep`, the refusals after later changes and after a first rollback, atomic
  batches, the evidence rule with empty undo groups kept or dropped, resume (a plain retry duplicates the
  finished steps, a resumed one does not) and the expected parameters on errors. Tests that need the
  private benchmark fixture, the LuaJIT inside Resolve.app, or the harvested data tables skip themselves with a
  reason when those are missing.
- `tests/smoke.py`, `tests/cache_live.py`, `tests/layout_live.py`, `tests/sb3_live.py`, `tests/receipts_live.py`:
  live checks through the real server in a scratch Resolve project (they run with the project allowlist set to
  `Testbed`, work on timelines they create and delete them in their cleanup stage).
- `scripts/parity.py` regenerates `PARITY.md` from the After Effects connector's operation registry (not
  shipped; see CREDITS.md) and `tests/smoke_results.json`.
