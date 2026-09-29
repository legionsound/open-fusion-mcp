# 10 Fusion scripting and expression reliability

Load before scripted rig builds, when an expression misbehaves, a call times out or returns something contradictory, or you need an exact tool/input ID. Read `fusion-realities.md` (fusion-reference skill) first: it holds the live-verified API facts (comp addressing, units, auto-connect trap, Bezier handles, expression semantics, modifiers, paste route, render). This module adds the rig-reliability discipline on top and does not repeat those tables.

## Discover before you mutate

- Use supported, discovered capabilities. Do not assume yesterday's project, timeline, comp, page, app version or connector. Read `resolve.GetVersionString()`, the current project/timeline, the intended item and its comps; check the official MCP `get_whats_new` and installed stubs (`fusion_api.pyi`) when an API detail matters.
- The user opens scratch projects themselves. Mutate only the authorized project/item; never switch, save or overwrite unrelated work to diagnose.
- Get IDs from the live TSV, never from memory or UI labels:

```bash
T=.../fusion-reference/data/fusion-21.1-inputs.tsv   # cols: RegID, input ID, UI name, type, control, default, slider|allowed range, options, page
grep -P '^@' "$T" | grep -i glow                  # tool/modifier headers: @RegID, default name, category, outputs
grep -P '^SoftGlow\t' "$T" | cut -f2,4-8          # every input with type, control, default, range, options
grep -P '^[^@#][^\t]*\t[^\t]*\t[^\t]*Corner' "$T" # search by UI name
grep -P '^Fuse\.' .../fusion-reference/data/fusion-21.1-registry.tsv   # registry-only IDs (Fuses: inputs not in TSV)
```
Settings-tab common inputs (Blend, MotionBlur, Quality, ShutterAngle, EffectMask...) are stripped from each tool's rows and listed once in the header comment. Numeric Combo/MultiButton take 0-based indices; ComboID/MultiButtonID take option strings. When the TSV lacks an option list (e.g. Follower `Order`), set it once in the Inspector and read the number back. Anything not in the TSV or registry is "unverified".
- On a live tool: `{v.GetAttrs()['INPS_ID']: v.GetAttrs()['INPS_Name'] for v in tool.GetInputList().values()}`.

## Choose the build route

| Route | Use for | Must do |
|---|---|---|
| `.setting` paste (Route A) | multi-node units, groups, UserControls, instances, keyed splines with absolute handles, long expressions | current Fusion-page comp only; `comp.Execute` is deferred; capture Lua errors; poll for the first tool |
| Python `AddTool`/`SetInput`/`ConnectInput` | single tools and edits, including on non-current item comps | `comp.SetActiveTool(None)` before every `AddTool` on the current comp; explicit 6-arg `AddTool`; `Lock()`/`Unlock()` around Loader/Saver/mesh creation; check each `ConnectInput` return |
| UI | Macro Editor layout, modals, visual state | inspect before acting; clear dialogs deliberately |

Idempotent paste with error capture (status: unverified wrapper around the live-verified paste):

```python
import time, pathlib
def paste_setting(cc, text, first_tool, path, timeout=3.0):
    if cc.FindTool(first_tool):
        raise RuntimeError(first_tool + ' exists: inspect partial state before retrying')
    pathlib.Path(path).write_text(text)
    cc.SetData('paste_err', '')
    cc.Execute("local ok, r = pcall(function() return comp:Paste(bmd.readfile([[" + path + "]])) end) "
               "if not ok then comp:SetData('paste_err', tostring(r)) "
               "elseif not r then comp:SetData('paste_err', 'Paste returned false (comp not current?)') end")
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.1)
        if cc.FindTool(first_tool):
            return True
    raise RuntimeError(cc.GetData('paste_err') or 'nothing pasted within timeout')
```
`.setting` authoring rules that bite: dotted IDs need bracket keys (`["Transform3DOp.Translate.X"] = Input {...}`); spline handles are absolute; polyline points are relative to the tool center and handles relative to their point; masks output `Mask`, most tools `Output`, splines/XYPath `Value`, PolyPath `Position`; Loader media is a tool-level `Clips` table; keep every tool and modifier name unique file-wide (grammar: `setting-format.md`).

## Writing inputs and animation safely

- Scalar animation: `AddModifier(id, "BezierSpline")` (seeds a key at the current frame; judge success by `GetConnectedOutput()`), then `SetKeyFrames(dict, True)`; Python handles relative, `.setting` absolute. Read back `GetKeyFrames()` (string frame keys) and `GetInput(id, t)` at an in-between frame.
- Points never take a BezierSpline: animate `Center`-type inputs through `XYPath` (edit its `X`/`Y` splines), `PolyPath` (`Displacement` spline 0..1), `PerturbPoint`, `Shake` or a `Point(...)` expression. The AE "separated dimensions" lesson maps here: edit the X/Y splines, not the Point.
- Key simplification: bounded loops only; after each operation verify the key count actually changed; rebuild intended tangents after deleting a key. Never loop "until it looks right".
- Frame-aligned ranges use comp frames (`COMPN_RenderStart/End`, `comp.RenderStart` in expressions); map timeline to comp time before keying (`C = C0 + (T - T0)`, api-routing-and-qc.md). Fractional and negative key frames are legal.
- Programmatic `TextPlus`: set `Font`, `Style`, `Size`, color and justification explicitly; render to confirm weight and case. With a Follower attached the text lives in the Follower's `Text`; writing `StyledText` does nothing.
- Check wiring and stacking in a render: a new Merge wired to the wrong input puts the new detail behind the existing fill (Merge `Background` vs `Foreground`; sMerge `Input1` is bottom).
- Inspect effect defaults before relying on them (Blur/Glow `ClippingMode` Frame, `Filter`), preserve working defaults, and validate blend/composite choices on a colored test background to catch fringes or unwanted shadows. Check point-control coordinates after grouping or moving a shape: sShape offsets are center-origin, masks and Merge Center are 0-1.

## Expression access is not scripting access

| In Python (outside) | In a SimpleExpression (inside) |
|---|---|
| `tool.GetInput("Size", t)` | `Title.Size`, bare `Size` on the same tool, `self.Size` |
| `tool.GetInput("Size", t - 5)` | `Title:GetValue("Size", time - 5)` (colon, Lua method) |
| input object via `GetInputList()` | 3D sub-inputs by dotted path `Transform3D2.Transform3DOp.Rotate.Z` (corpus) |
| image size via `GetAttrs` of output | `Background.Width`, `Title.Output[0].DataWindow[3]`, `self.Input.OriginalWidth` (corpus) |

- SimpleExpressions: `time` in frames, trig in radians (`math.rad`), `noise()` absent, `Point(x, y)` for points, `Text(...)` for text, `iif(c, a, b)` evaluates both branches (it is a function), multi-statement form starts with `:` and uses `return` (installed templates). Clearing an expression leaves 0: SetInput the intended value right after.
- A script finishing does not prove each embedded expression evaluated. For each expression input read `GetInput(id, f)` at two frames; None or an implausible constant means it failed. Then render the changing state.
- Structure-dependent references break silently: prefer stable semantic names and controller UserControls over paths into another tool's internals. The AE "square eyes" failure has a Fusion twin: squashing capsule eyes with `sTransform` `YSize` flattens their ends; change `Height` with `CornerRadius` 1 instead (08).
- Compute shared gaze/phase values once on a controller user control; consumers read that value. Keep keyframe ownership clear and a clean manual path (06).
- After a structural edit (rename, group, paste into another comp) re-read every expression that references moved tools, published inputs and instance overrides in the actual parent.

## Timeouts, modals and partial writes

- A timeout is an unknown state, not a failure. Stop new mutations, then inspect the exact target for the planned tool names (`FindTool`), connections and keys. Repair only confirmed intended work; never re-run a whole build blindly (duplicate tools, stray `Merge1..n`, compounded keys).
- Make builders idempotent: check existence first, reuse deliberately, or delete-then-create with orphan cleanup (`comp.GetToolList(False)` includes modifiers; deleting a host leaves its modifiers).
- Group each mutation batch with `comp.StartUndo("rig: cards")` / `comp.EndUndo(True)` so a partial batch can be undone as one step (API in stub; behavior through the bridge unverified).
- Save incremental progress between phases: `item.ExportFusionComp(path, i)` (Resolve API); Python `tool.SaveSettings()` returns empty through the bridge.
- Known modals: file pickers on Loader/Saver/mesh creation (avoided with `Lock()`/`Unlock()`; always unlock in `finally`), trim-reset dialog when changing an existing clip length, late render-completion notices. When returns are null or contradictory, look at the UI before continuing.
- Do not `GetInput` Image/Material/3D ports (a material-port read preceded a UI hang); use `GetConnectedOutput()`.
- If UI and calls stop responding: stop queueing, establish the last checkpoint, bounded read-only diagnosis, abort only an identified active operation, force quit only with the user's approval.
- A historical community wrapper let values read back while renders ignored them (Lock interaction). Readback is structural evidence only; render to prove.

## Failures that transfer from the Higgsfield DevDay rebuild

Targeted checks for when the symptom appears, not reasons to rebuild a project or change
unrelated settings. Each AE failure is given with its Fusion twin.

- **Retime keys cleared** (AE: deleting the last Time Remap key disabled remapping). Fusion
  [corrected live 2026-09-26]: the branch freezes, but not on frame 0. `DeleteKeyFrames` cannot
  remove a spline's last key, so deleting "every" key leaves one key and a constant `SourceTime`
  (the remaining key's value, 40 in the test); deleting the spline modifier (or disconnecting it)
  leaves the input at the value it had at the comp's **current time** (27.34 with the playhead at
  frame 30). Either way every output frame shows one source frame. When replacing retime keys,
  write the new keys before removing old ones, or `SetInput` the intended static value right after;
  confirm the shown source frame with an upstream Text+ counter (02).
- **Missing still exports** (AE `saveFrameToPng` returned but skipped files). Fusion: a Saver
  render returning True proves nothing (realities §10). List every expected
  `name_0000.png`-style file, check existence and dimensions, and re-render only the missing
  indices. Never report the requested list as rendered files.
- **Premature cut of a nested element** (AE: a catalogue vanished six frames early). Fusion:
  check in order MediaIn/Loader `GlobalOut` (inclusive) and `HoldLastFrame`, keyed Merge `Blend`
  or Dissolve `Mix` steps, `TimeSpeed` `Delay`, the comp's `GlobalEnd` against the timeline
  item's real length (Edit-page trims hide comp frames), and anything merged over it. Prefer the
  smallest verified repair; when a tool must be recreated, preserve its connections, masks,
  keys, expressions and Merge order, then render the boundary again.
- **Wrong source selected** (a compact selector mapped scenes wrongly). Use explicit lookup
  tables (a Python dict, or a Lua table inside a `:` expression block) for scene/character
  mappings, or a `Switch` tool (`NumberOfInputs`, `Source`, `Input0..n`) whose `Source` index
  is documented per option. Verify each `FindTool` result and each `Switch` choice in the live
  comp before wiring dependents. [verified live 2026-09-26] `Switch` `Source` 1 output `Input1`,
  `Source` 2 output `Input2` (0-based index, `NumberOfInputs` 3 in a paste).
- **Session and UI state**: a stuck dialog does not mean the scripting bridge is dead, and a
  responsive bridge does not mean the UI is free ([UI layer](ui-layer.md)). Probe with a read-only call
  (`resolve.GetVersionString()`). A timeout leaves mutation status unknown: inspect the comp
  and output file timestamps before any retry. One driver at a time: no concurrent mutations or
  renders against the same Resolve.

Render hygiene: a frame-render helper deletes its temporary Saver, restores `comp.CurrentTime`
and any value changed for a test (also in the failure path), and returns the real file paths.
Remember that `comp.RenderStart`/`RenderEnd` now equal the last rendered range (realities §11.18).
On the Deliver page, record existing jobs (`project.GetRenderJobList()`) and delete only the job
you added (`project.DeleteRenderJob(id)`); poll `project.IsRenderingInProgress()` and
`GetRenderJobStatus(id)` for real completion (Resolve API; confirm names with
`get_scripting_api`).

## Editing text and state through the API, safely

- An inspection step names the project, timeline, item, comp, tools and the exact input states
  it read. A mutation takes the exact target and intended values, then reads them back. A save
  needs a verified destination; a reopened or collected project needs its media resolved again.
  A frame check names the comp and frame and returns a viewable file. Do not infer support for
  keyed `StyledText`, character styling, arbitrary scripts, saving or collection from an
  operation's general name.
- Read text from the tool that owns it: `StyledText` on the Text+, or the Follower's `Text` when
  a `StyledTextFollower` is attached. Preserve keyed text states and character-level styling
  (`StyledTextCLS` modifier). A whole-tool `Font`/`Style` change may not carry into those
  overrides: render and read back before and after.
- For retime edits (`TimeStretcher` `SourceTime`, MediaIn `ClipTimeStart`), confirm the path
  supports it, add the new keys before removing redundant ones, and inspect the state after any
  exception.
- `comp.Render(..., "Wait": True)` should leave the file finished, but a Deliver render or an
  external viewer can lag: confirm the file exists and decodes before viewing, and let pending
  renders finish before switching projects or timelines. Inspection or relinking can mark the
  project modified; that never authorizes discarding or overwriting the user's work. If the Mac is
  locked, ask for it to be unlocked and do only independent file checks meanwhile. Keep keys and
  license details out of every report.

## 3D and renderer checks

Verify transform conventions against rendered points, not a solver's Euler order: set one known rotation, render, compare; use `Transform3DOp.Rotate.RotOrder` explicitly and `Locator3D` (`Position` output) to project a 3D point to 2D. Check hole/compound paths and depth ordering in the actual `Renderer3D` (a correct 2D fill does not prove the 3D result). Features split by renderer: soft/colored shadows need Software; accumulation DOF, supersampling, Cryptomatte need OpenGL (`RendererType`). For motion blur on fast text-bearing surfaces, raise `Quality`, set `ShutterAngle` deliberately, and inspect for repeated outlines; particle and Renderer3D blur settings must match.

## Rig build checklist

1. Read version, project, timeline, item, comp; export a backup.
2. Grep IDs from the TSV; write the graph as `.setting` or plan explicit Python calls.
3. Create (paste or `SetActiveTool(None)` + `AddTool`); read back names.
4. Verify every connection return and `GetConnectedOutput()`.
5. Verify key sets and in-between values; verify each expression at two frames.
6. Render one representative frame, then the changed span (09).
7. Make one real content/control edit, render, restore.
8. Export the comp; report what passed at which gate.
