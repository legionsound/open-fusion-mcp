# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-01

Reliability release. Issues #1 to #5, #13 and #14 came from feedback on the r/mcp launch thread; #6 to #11 were
found while building a 9:16 version of the explainer film. The recovery paths were checked live in Resolve Studio
21.1.0.14 before release (`tests/receipts_live.py`, every stage passed).

### Added

- Receipts after a lost reply (#1). The worker journals every operation call it runs, one JSON line per step,
  flushed and fsynced to `out/journal/<callId>.jsonl` (the newest 200 are kept). A `TIMEOUT` reply, or a `TRANSPORT`
  reply after the worker died, carries `details.receipt`: the steps that finished and what they report they
  changed, the step that was running and its target tools, the steps that never started, and whether the
  call's undo group was left open. The message adds a one-line summary.
- `batch.recover` (#1), read-only: re-reads the comp the call targeted, compares its tool count with the
  snapshot taken before the call (and lists added and removed tools when the snapshot holds names), checks
  whether the uncertain step's target tools exist, and ends with plain advice.
- `batch.rollback` (#1): closes an open undo group, undoes the call and verifies the comp against the
  snapshot. `keep: true` only closes the group. It undoes only when a step finished or the comp differs from
  the snapshot (an undo group that recorded no change may not be an undo event, so an undo could revert an
  earlier change), refuses when later changes ran on the same comp, and refuses a second rollback of the same
  call; `force: true` overrides. With nothing to compare against, it reports `verified: null`.
- Atomic batches (#2): `batch.run` takes `atomic: true` (stop at the first failure, undo the whole batch, verify
  the comp against a names snapshot) and `snapshot: "count" | "names"`. Steps that one comp undo cannot revert,
  such as timeline, project and Deliver operations, and steps that failed validation are refused before the
  batch starts. The undo follows the same evidence rule as `batch.rollback`.
- Resume (#14): `batch.run` takes `resume: <callId>` to finish a batch whose reply was lost. The same ops are sent
  again; the steps that finished are skipped (their arguments must match the journal's fingerprints), a step that
  may have partly applied runs again only when none of its target tools exist, or, for a step that names no
  tools (a paste), only when the comp holds no tools the finished steps do not explain (`uncertain: "check" |
  "skip" | "rerun"`). The dead worker's undo group is closed, and the comp is read back: every intended tool
  exists and none was duplicated. A plain retry of the whole batch would make Fusion rename the repeated tools (Title1, or
  Title_1 in a paste).
- Fault-injection tests (#3). `fusion_connector/testkit.py` is a file-backed fake Resolve whose state survives a
  killed worker, with test-only operations that hang, crash the worker or fail after a partial change; it is
  inert unless the test environment variables are set. `tests/test_receipts.py` drives the real server and
  worker through these faults, and `tests/receipts_live.py` repeats the cases that only real Fusion can
  confirm, in a scratch project.
- Dedicated tools for the most-used operations (#5): `fu_scene_build`, `fu_scene_plan`, `fu_batch` and
  `fu_contact_sheet`, with input schemas generated from the operation definitions (15 tools in all; `fu_do`
  stays for everything else). They pass the same validation and policy gate as `fu_do`, and a tool whose
  operation the policy blocks is not listed.
- Scripting-port check (#8): `fusion-connector doctor` reports who holds ports 49152 and 49153 and names an
  orphan that makes every scripting client hang, such as a Workflow Integration plugin helper or an old
  `fuscript -s` left by a Resolve session that exited. When the check finds one, `TIMEOUT` replies include the
  problem and its fix.

### Changed

- `fu_catalog` (#4) looks up one operation (`operation`: its parameters, category and sibling operations) and
  searches names and descriptions (`query`, optionally narrowed by `category`). Unknown arguments are rejected
  with a suggestion instead of being ignored.
- `batch.run` children accept `{op, args}` as well as `{operation, args}` (#4).
- Every `INVALID_ARGS` reply lists the operation's expected parameters, with allowed values and defaults (#13):
  schema errors did already; now errors raised inside an operation, ID checks and failed batch children do too,
  and the hint points at `details.expected` instead of a catalog lookup.
- When `StartRendering` fails, `deliver.start` names the job IDs missing from the render queue and the known cause
  seen live: a job added in the same script call that loaded the project does not start until it is added again
  in a new call.
- The Fusion realities reference gained the render-night findings: check renders do not predict Deliver time,
  how Resolve's render cache and "Use render cached images" behave, and how to keep the clean part of a stopped
  Deliver.
- 181 operations in 36 categories. The offline suite has 237 tests, and CI runs all five test modules.

### Fixed

- In a 3D block, a group whose last child was an animated group reused that child's texture hold, so its card
  showed only the child (#6).
- Fusion tool names are case-insensitive, and the scene builder now rejects descriptions whose tool names
  collide when case is ignored (#7): layer ids that differ only by case, and the ids `bg`, `ctrl`, `out` and
  `r3d`, which collide with the builder's own `<scene>_BG`, `_CTRL`, `_Out` and `_R3D` tools.
- The `scene.build` frame-format warning suggested `timeline.set_format`, which does not resize an existing
  Fusion clip (#9). It now says that a comp keeps its clip's frame size and that `timeline.add_fusion_clip`
  makes a new clip at the new size.
- The `scene.plan` preview drew every 3D block over the 2D layers and left out 3D layers inside groups; it now
  draws 3D blocks in stack order, inside groups too (#11).

## [0.1.0] - 2026-09-29

First public release.

### Added

- `use-fusion` MCP server: 11 `fu_*` tools over 179 checked operations in 36 categories, with read-back of every
  write, dry runs, batches as one undo step, and a worker process that is Resolve's only scripting caller.
- Scene builder: `scene.build` and `scene.update` turn a scene description into an editable native graph; films
  run as one culled comp on a film ladder with a single draft/final controller; 2D and true-3D layers, glass,
  dashed and tapered strokes, size-driven motion blur.
- Render-and-look tools: frame renders with inline previews, contact sheets, image comparison, motion audit,
  and Deliver jobs with explicit job IDs.
- Build-loop tools: disk caches with staleness warnings (`cache.*`), a graph tidier (`comp.layout`), and
  automatic dismissal of Resolve's render dialogs.
- Guard rails: project allowlist, read-only mode, category allowlist, default-off `eval.*`.
- Skills: `use-fusion`, `fusion-motion-design`, `fusion-reference` and `fusion-figma-transfer`.
- Example agent definitions, documentation, measured results and the explainer film.
- Offline test suite (172 tests) and CI.
