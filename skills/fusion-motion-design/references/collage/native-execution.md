# Collage: native execution

Scoped to collage builds; general rules in [10](../10-fusion-scripting.md) and
[fusion-realities](../../../fusion-reference/references/fusion-realities.md).

## Establish real control of Resolve

- Prove control with reads before any write: `get_resolve_status`/`resolve.GetVersionString()`, the
  current project and timeline, the intended item's comp, and one target tool's inputs. A connected MCP
  server or a login elsewhere is not proof that Resolve can be driven (realities §15).
- Routes: Resolve API Python via `run_script` for comp edits, `run_script_unsafe` only for file access,
  `.setting` paste for whole card groups. No privilege escalation to get around a failing call.
- When the user wants a script as the deliverable, hand over a reviewed Python builder or `.setting` with
  the exact manual route (paste in the Fusion page node editor, or Workspace > Scripts) and mark it
  unverified until it has run.
- Human-run route: first a read-only preflight script that reports Resolve version and edition, target
  timeline/item/comp, fonts (14 glyph check), assets and required tools (OFX/Fuse RegIDs, 15). Adapt the
  builder to the returned report. Planning continues meanwhile; never claim host checks that did not
  run. Write report files only where the user allows.
- Inspect downloaded Fuses, scripts and macros before installing or running them: Fuses are Lua code
  (look for `os.execute`, `io.popen`, file writes outside their scope, network calls, `loadstring`
  of remote text). A supplied script is not automatically safe or needed.
- UI automation (computer use) only from a fresh screenshot or accessibility tree; refresh after every
  change; stop a route that throws an application error instead of repeating it. Set the frame by API
  (`comp.CurrentTime = f`) rather than fighting the time ruler. Never close or relaunch an unsaved
  project to refresh a panel.

## Inspect and preserve the project

- Record project, timeline, item and comp identity; frame format (W, H, pixel aspect, fps); duration
  and render range; `Renderer3D` type (Software/OpenGL); color management; the active camera.
- For affected tools read the inputs being changed, not only names: sources (MediaIn/Loader), Transform
  chains and 3D parents, time offsets (`TimeSpeed`, `TimeStretcher`, controller `time - k` reads),
  transforms, expressions, modifiers, masks, Merge operators and apply modes.
- Back up the live state before structural changes (comp export + project save). A from-scratch
  interpretation inside an existing project goes in a new named comp or timeline; a duplicated
  timeline item or Media Pool Fusion clip may still share sources (13), so duplicate an affected source
  before changing it when the baseline must stay identical.
- Semantic names with an ownership prefix (`COL_`), so a builder can detect an existing stage before
  running again. Keep unknown user animation and unrelated comps. Never rerun a whole builder to repair
  one failed tool, never normalize every key or clear expressions as unannounced cleanup.

## Reliable editing

- Python through the Resolve bridge, Lua inside `.setting`/`Execute`: neither is a browser or Node
  environment. One stage per script. Preflight targets, assets, input types, source dependencies and
  backup paths before mutating. Find a unique tool by exact name and stop on ambiguity.
- Look up every input ID in the TSV. 3D transforms use dotted IDs (`Transform3DOp.Translate.Z`); Text+
  content is `StyledText` (or the Follower's `Text`); points take `{1: x, 2: y}`.
- Validate finite numbers, value shapes and denominators before `SetInput`: scalars need numbers,
  points need two values, colors are separate channel inputs (realities §3), polylines need complete
  point tables (setting-format), text inputs need strings.
- Easing lives in BezierSpline handles (Python relative, `.setting` absolute, realities §6). Points do
  not take BezierSplines: use `XYPath` (per-axis splines, separate easing per axis) or `PolyPath`. Keep
  `StepIn` discrete events.
- Adding a tool to a pasted group can rename it on collision: re-resolve names after any structural
  change; locate the intended instance explicitly when duplicates exist.
- Shadows: `Shadow` tool (`ShadowOffset`, `Softness`, `Alpha`, `OutputMode`) is native and needs no
  availability check; OFX alternatives do.
- Group each scoped edit with `comp.StartUndo`/`EndUndo` (closed in a `finally`); an undo group does
  not roll back partial changes by itself. Log the failed stage and error text, and inspect what applied
  before retrying.
- A copied card group: verify its wiring, masks, effects, time offsets and expression references
  before integrating. To freeze a deliberately duplicated pose, read the evaluated values
  (`GetInput(id, f)`) before removing animation; never freeze a source just because its keys are hard
  to read.
