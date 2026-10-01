<!-- fusion-realities.md part 2 of 3; index: fusion-realities.md -->
## §11. Silent-failure list

0. AddTool on the Fusion-page comp without `SetActiveTool(None)`: silent auto-wiring and
   stray Merges; later `ConnectInput` returns False (§5).
1. Paste on a non-current comp: returns False, nothing created (§1).
2. Treating `comp.Execute` as synchronous: the next line sees no tools yet (§9).
3. Pixel coordinates in `Center`: the element flies off frame. Normalize and flip Y (§2).
4. Degrees in an expression's `sin`: wrong motion. Expressions are radians (§7).
5. Seconds for `time`: 24x too fast. `time` is frames (§7).
6. `noise()` in a SimpleExpression: input goes nil/0 (§7).
7. Option label passed to a numeric Combo, or index passed to a ComboID: ignored or wrong.
8. Relative handles written into a `.setting`, or absolute handles into Python: broken easing.
9. Merge with no Background: black/empty output. Merge Background also sets resolution.
10. Straight (unpremultiplied) foreground: bright fringes.
11. Mask connected before it has a shape: blanks the image.
12. Clearing an expression with `""` leaves 0 and blocks later SetInput on it; clear with `None` (§7).
13. Orphan modifiers after failed AddModifier or host deletion.
14. Text+ layout inputs named like `HorizontalJustificationNew`: use the TSV ID, not the label.
15. Renderer3D left on the Software default when the look needs OpenGL-only features
    (accumulation DOF, supersampling, Cryptomatte), or on OpenGL when it needs soft/colored
    shadows (Software only). Check the renderer before judging a 3D render.
16. **[live]** A Renderer3D created by `.setting` paste without `UseFrameFormatSettings = 1` renders
    320x240 (then sits tiny in the middle of the next Merge). Write it on every pasted Renderer3D.
17. **[live]** A Camera3D created by paste comes up `FilmGate "TV"` (AoV 24.33 at 35 mm); AddTool gives
    `"BMD_URSA_4K_16x9"` (AoV 19.26). Frustum math built on 19.26 then under-fills.
    **Corrected [from rebuild log, K2]:** this item used to say "Write `FilmGate`". That is not enough:
    a pasted `FilmGate = "BMD_URSA_4K_16x9"` read back the FuID but left `ApertureW`/`ApertureH` at the
    TV values 0.792 x 0.594, and a 1-unit card rendered 0.79x its expected size. Write
    `ApertureW = 0.8315` and `ApertureH = 0.4677` explicitly (FilmGate may stay), then read `AoV` back:
    with `FLength` 29.337 that gives AoV 22.89 vertical = 39.6 horizontal (a 400 px card rendered
    400 px, a far card centre within 1 px of the pinhole prediction); the TV apertures gave 28.84.
    `setting.validate` warns on a pasted Camera3D without ApertureW/H.
18. **[live]** `comp.RenderStart`/`RenderEnd` follow the last `Render({Start, End})` or preview range;
    guards/progress built on them break on partial renders. Use `comp.GlobalStart`/`GlobalEnd`.
19. **[live]** `comp.Render` leaves a "Render completed!" modal every time; the next calls return
    `None` until it is dismissed (§10).
20. **[live]** `SetKeyFrames(dict, True)` keeps a stray seeded key; delete it per frame (§6).
21. **[live]** `comp.SetMarker` ignores the time argument and stores the marker at frame 0 (§12).
22. **[live, skills-gap pass]** Malformed `.setting` text (a raw newline inside a quoted string):
    `bmd.readfile` returns nil and `comp:Paste(nil)` pastes the system clipboard, reporting ok (§9).
23. **[from rebuild log, K4]** ImagePlane3D `MtlStdInputs.ReceivesLighting` 0 (meant as "unlit")
    renders the card's RGB **black** in the OpenGL renderer, alpha intact. The unlit switch is
    `SurfacePlaneInputs.Lighting.IsAffectedByLights` 0 alone; leave `ReceivesLighting` at 1.
24. **[from rebuild log, B1]** Time-gated switching does not stop evaluation: a `Dissolve` at `Mix` 0
    or 1 and a Merge at Blend 0 still cook every input, and the common `ProcessWhenBlendIs00` 0 did not
    stop the upstream requests. One frame of one scene took 363 s because all eight scenes'
    motion-blurred Renderer3Ds rendered. **[live, efficiency lab, T04]** The switch that works is the
    tool enabled region (trim): a Merge outside its region passes Background and does not request its
    Foreground. Enter each scene through a trimmed Merge (§17 item 7); one culled comp per film Delivered
    faster than one comp per scene (§17 item 5).
25. **[from rebuild log, F8]** A pasted `Switch` with `NumberOfInputs` 8 has untyped `Input0..7`:
    in the rebuild `input.connect`/`ConnectInput` refused every source ("loop, type mismatch, or wrong
    port") and nothing downstream could take its output; one comp per scene on separate timeline items
    worked instead. **[live, gapfix pass]** The connector's `input.connect` (with its fallback to the
    source's Output object / `Input.ConnectTo`) connected all eight inputs of a pasted 8-input Switch,
    and a Merge took the Switch output and rendered. Unverified: whether a Switch spares its
    unselected inputs from cooking; use trimmed Merges instead (§17 item 7).
26. **[from rebuild log, K11]** `comp.Render` also renders `MediaOut1`'s chain, whatever the Saver
    watches (§10; the connector isolates it, live-verified).
27. **[from rebuild log, K12]** A `TimeSpeed` after a motion-blurred Renderer3D (used as `Delay` -48 to
    shift a scene into global frames) made one frame take 189 s and another abort with
    "failed to get scene at time 100.083333". Never retime a 3D render with TimeSpeed; offset the keys
    instead (§16).
28. **[from rebuild log, K13]** Renderer3D motion blur and accumulation DOF sample sub-frame times, and
    every sample re-evaluates each animated 2D texture graph upstream of an `ImagePlane3D` (a
    1,100-tool scene: 32 s/frame). Hold each card texture at integer frames with a `TimeStretcher`
    between texture and ImagePlane3D: `SourceTime` expression `floor(time + 0.5)`,
    `InterpolateBetweenFrames` 0 (Nearest). 1.6 s/frame after, camera and card transforms keep full
    motion blur (it works because TimeStretcher never evaluates at a fractional time, §14).
    **[live, efficiency lab, T03]** A hold still re-renders a static texture every frame; if the card's
    texture never changes, use a constant `SourceTime`, and freeze static sub-branches of animated
    textures the same way (§17 item 4).
29. **[from rebuild log, K5]** A paste drops SourceOp wires to tools outside the text (§9) and renames
    pasted splines (`S1_CAM_PX` became `S1_CAMXOffset`, §14): address splines through
    `GetConnectedOutput()`, never by authored name.
30. **[from rebuild log, K15]** Renderer3D motion blur samples material opacity across the shutter, so
    an in-point opacity ramp ghosts: a ramp starting at f600 was ~8 % visible at f600.25, a one-frame
    ghost of the incoming card. When a clean cut-in matters, key opacity stepped per frame
    (depth-space §8).
31. **[live, gapfix pass]** Pasted generators come up at 320x240: a `Background`, `TextPlus`,
    `FastNoise` and `sRender` pasted without `UseFrameFormatSettings`/`Width`/`Height` read
    `UseFrameFormatSettings` 0, `Width` 320, `Height` 240 (AddTool gives 1 and the comp size). Write
    `UseFrameFormatSettings = 1` (or an explicit size) on every pasted generator, like Renderer3D (16);
    `setting.validate` warns.
32. **[live, gapfix pass]** A UserControl whose ID matches a built-in input silently becomes that
    input: a slider "Depth" added to a Background was the Background's bit-depth `Depth` (a set of 73
    read back 4). Prefix control IDs (`CtlDepth`); `input.add_control` refuses a taken ID.
33. **[live, gapfix pass]** Deleting a tool heals the chain: deleting the Merge between `MediaIn1` and
    `MediaOut1` left `MediaOut1` wired to `MediaIn1`; deleting a keyed tool removed its BezierSpline too.
    Re-read wiring after deletes instead of assuming a dangling input.

## §12. Not available or needs another route

- No Saver in a template for Edit-page delivery: use MediaOut and the Deliver page.
- Loader in Resolve is for EXR/stills per the manual; bring footage in through MediaIn from
  the Media Pool or timeline.
- Python-side `SaveSettings` serialization is empty (§9).
- The Expression modifier via `AddModifier` (§7).
- **[live, connector pass]** Comp markers: `comp.SetMarker` ignores time (marker lands at 0). Put
  timing markers on the timeline item instead (`TimelineItem.AddMarker(frameId, color, name, note, duration)`).
- Planar Tracker data does not survive save/reload: finish the track and create a
  Planar Transform in the same session.
- Bins, Fusion Connect and Composition preferences are Fusion Studio features, not Resolve.
- **[live, skills-gap pass]** No API creates a Media Pool "Fusion Composition" clip: `ImportMedia` of a
  `.comp` returns nothing, and `InsertFusionCompositionIntoTimeline` items have no Media Pool item.

## §13. Cheap, preview-friendly construction

- Prefer Transform (concatenates) over Resize/Scale/Crop for animated moves; Corner/
  Perspective Positioner do not concatenate.
- Use resolution-independent sources (Background, Text+, sShapes, masks) and keep DoD tight.
- Put blurs/glows after the Merge only when they must affect the composite; otherwise
  branch-local on the smallest image.
- Motion blur costs samples: use Transform/Text+ `MotionBlur` with `Quality` 4-8 for previews,
  raise for final. On an OpenGL Renderer3D with accumulation on, the sample count is `AccumQuality`
  (§17 items 1-3), and `MotionBlur` can be switched off per frame where nothing moves (§17 item 9).
- For build checks render with `HiQ = False, MotionBlur = False` (3-7x faster, layout exact; §17 item 13).
- Particle systems and Trails need pre-roll; set it before judging a frame.

## §14. Verification pass findings [live]

Observed 2026-09-26 on Resolve Studio 21.1.0.14 (project Testbed, 3840x2160, 24 fps). Log:
`out/verify_log.md`; renders `renders/verify/`.

- **Custom tool `NumberIn1..8` clamp to +/-1,000,000** (`INPN_MaxAllowed`). Keys, `SetInput` and
  expressions are all clamped. Keep controllers as 0-1 progress and scale in the consumer.
- **Follower (`StyledTextFollower`) `Order`** values: 0 Left to right, 1 Right to left, 2 Inside out,
  3 Outside in, 4 Random but one by one, 5 Completely random, 6 Manual curve, 7 Automatic (default,
  behaves Left to right on Latin text). The input's `INPST_ComboControl_String` table lists
  Automatic first, so a Combo's attribute string order is **not** always its value order: confirm by
  render. `DelayType` 0 None, 1 Between each character (default), 2 Between first and last.
- **Combo option strings are readable live**: `inp.GetAttrs()["INPST_ComboControl_String"]`
  (1-based dict). Useful where the TSV `options` column is empty; still check value order.
- **Spline flags from Python work**: `SetKeyFrames({0: {1: 0, "Flags": {"Loop": True}}, ...}, True)`
  loops; `GetKeyFrames()` does not echo flags. `.setting` `Flags` `Loop`, `LoopRel`, `Pingpong`,
  `StepIn` behave as cycle / offset / ping-pong / hold. A cycle shows the first key's value at the
  last key's frame.
- **Transform `Angle` positive = counterclockwise** (Y-up frame).
- **Point `SetInput`** accepts `{1: x, 2: y}` and `[x, y]` (returns None; read back to confirm).
- **SimpleExpressions** also support `:` statement blocks with `local`, `if`, `while`, `return`,
  `string.format`, `string.match`, `gsub`, `ceil`, `%`, and `comp:GetPrefs().Comp.FrameFormat.Rate`
  / `comp:GetPrefs("Comp.FrameFormat.Width")`. Inside a tool's own expressions, bare names of its
  inputs and UserControls (`Idx`, `D`) resolve without `self.`.
- `Input.GetExpression()` returns the expression string from Python.
- **Anim Curves (`LUTLookup`)**: `value = curve*Scale + Offset`; Ease names follow Penner
  (EaseOut Cubic = 0.578 at 25%); defaults `Source "Transition"`, `Scale` = host range (360 on
  Angle, 5 on Size).
- **PerturbPoint**: peak deviation about 0.5-0.7 x `Strength` per axis in normalized units (not
  pixel-isotropic on 16:9; `YScale` = W/H evens it); rate about 0.2 x `Speed` zero crossings/s.
- **`Tool.UserControls` setter + `Refresh()` work through the Python bridge**; the returned handle
  has the new inputs.
- **Groups**: a pasted `GroupOperator` exposes its `InstanceInput`s as inputs on the group;
  `group.ConnectInput("MainInput1", src)` and `group.SetInput("<published>", v)` drive the inner
  tools; `saver.ConnectInput("Input", group)` takes `MainOutput1`. Pasting the same group twice
  renames every inner tool `_1` and retargets inner expressions.
- `Dent` `Type` 0 (Dent 1) pinches to a point at its center; Type 5 (Sine Dent) is a smooth bulge.
- **Pasted defaults differ from AddTool defaults**: pasted `Renderer3D` = `UseFrameFormatSettings 0`
  (320x240); pasted `Camera3D` = `FilmGate "TV"` (0.792 x 0.594 in, AoV 24.33 at 35 mm) vs AddTool
  `"BMD_URSA_4K_16x9"` (0.8315 x 0.4677 in, AoV 19.26). ImagePlane3D = 1 unit wide, height = image H/W.
  **[from rebuild log, K2]** Writing `FilmGate` in the paste does not restore the apertures; write
  `ApertureW`/`ApertureH` (§11 item 17).
- **`comp.RenderStart`/`RenderEnd`** are set by each `Render({Start, End})` call (a single-frame render
  of f143 made both 143). Anim Curves `Source "Transition"` in a plain comp follows the global range.
- **Pasted BezierSplines get renamed** to `<Host><control label>`: `Ctrl_MainAnimMove` on a UserControl
  labelled "Curve Move (keyed)" became `Ctrl_MainCurveMovekeyed`; `REVEAL_P` on `NumberIn1` became
  `REVEAL_CTRLNumberIn1`. Never address splines by name; use `inp.GetConnectedOutput().GetTool()`.
- **Text+ shading elements 2-8**: their inputs (`Red2`, `Type2`, ...) exist only after `EnabledN = 1`
  arrives through a `.setting` paste; `SetInput("EnabledN", 1)` alone did not create them through the
  bridge (a following `tool.Refresh()` did once, not reliably). Renderer3D OpenGL sub-inputs appear
  immediately after `SetInput("RendererType", "RendererOpenGL")`. Both sets are now in the TSV.
- **Blur** `XBlurSize` scales with frame width (sigma about 1.25 x size x W/1920 px); use the same value at
  HD and UHD. **sShapes** measure everything in frame-width units (§2 note under the units table).
- `GetInput(id, frame)` accepts fractional frames (curve QC between keys). `tool.Comp()` returns the comp.
- Render cost reference (this Mac): UHD OpenGL renderer with 16 accumulation samples + motion blur
  Quality 6 rendered about 1.1 s per frame; flat 2D UI/title comps 0.3-1 s per UHD frame.
- AddTool `Renderer3D` defaults `UseFrameFormatSettings 1` (3840x2160 here); only the pasted default is 320x240.
- Option lists read live from `INPST_ComboControl_String` (list order; render-confirmed only for Dent, where it
  matches, and Follower `Order`, where it does not): Dent `Type` Dent 1, Kaleidascope, Dent 2, Dent 3, Cosine
  Dent, Sine Dent; DirectionalBlur `Type` Linear, Radial, Centered, Zoom; Displace `Type` Radial, X Y and
  channels Red, Green, Blue, Alpha, Luma; Transform `Edges` Canvas, Wrap, Duplicate, Mirror; TimeStretcher
  `InterpolateBetweenFrames` Nearest, Blend, Flow; Text+ `LayoutType` Point, Text Box, Circle, Path,
  `FitCharacters` None, Adjust Spacing / Horizontal Size / Size to Fit, `UseLigatures` None, Non-Latin, All
  Scripts, `Type1` Solid, Image, Gradient; CornerPositioner `MappingType` Bi-Linear, Perspective; Shadow
  `OutputMode` Image with Shadow, Shadow Only; Renderer3D OpenGL `TransparencySorting` Z Buffer (fast),
  Sorted (accurate), Quick Sort.
- **[live, skills-gap pass]** Button inputs press through `SetInput(id, 1)`: Planar Tracker `TrackToEnd`
  tracked 24 UHD frames (~8 s) and `CreatePlanarTransform` created `PlanarTransform1`.
- **[live, skills-gap pass]** TimeStretcher never evaluates upstream at a fractional time: `SourceTime`
  10.5 shows frame 11 in Nearest and a 10/11 dissolve in Blend. `floor(time/2)*2` + Nearest steps a
  whole branch, masks and expressions included. `floor(time + 0.5)` + Nearest is the texture hold
  under motion blur (§11 item 28) **[from rebuild log, K13]**.
- **[live, skills-gap pass]** A MediaIn of a clip shorter than the comp reads `GlobalOut` = comp end and
  holds its last frame; a Loader shows nothing outside `GlobalIn`..`GlobalOut` (inclusive).
- **[live, skills-gap pass]** Displace `Type` X Y is neutral at map value 0 with default offsets
  (displacement grows with the value); `XOffset`/`YOffset` -0.5 make mid gray neutral.
- **[live, skills-gap pass]** DepthBlur with `BlurChannel` Z compares `FocalPoint` with Z values, which
  are negative scene-unit depths (enable `RendererSoftware.Channels.Z`, off by default); with a color
  channel map `FocalPoint` had no effect (white = more blur). Renderer3D `RendererSoftware.LightingEnabled`
  and `ShadowsEnabled` default to 0.
- **[live, skills-gap pass]** Transform `FlipHoriz` flips about the default Pivot before `Center` moves;
  `CenterBias` 0 = shutter centered on the frame, +1 trailing only, -1 leading only.
- **[live, skills-gap pass]** Resolve API: `AppendToTimeline` `endFrame` is exclusive (0..23 appends 23
  frames); `DuplicateTimeline` makes the copy current and its comps independent; subtitle items'
  `GetName()` is the caption text (`.srt` via `ImportMedia` -> "Subtitle" clip, needs
  `AddTrack("subtitle")`); `SetTrackEnable("audio", i, False)` + `GetIsTrackEnabled` work.

## §15. Transport, completion and retries

Carried over from Higgsfield's local-connector `ae-mcp-realities` (2026-09-26); the rules are
transport-level and hold for every Resolve route (official MCP `run_script`, community MCP, a
local Fusion connector).

- A connected MCP server does not prove Resolve is reachable or that the intended project is
  open. Probe with a read-only call (`get_resolve_status`, or `resolve.GetVersionString()` and the
  current project/timeline names) before the first mutation.
- A multi-step script is not a transaction. When step 7 fails, steps 1-6 already changed the comp.
  Inspect partial results (`FindTool` for each planned name, `GetConnectedOutput`, `GetKeyFrames`)
  before any retry, and repair only what is confirmed missing. `comp.StartUndo(name)` /
  `comp.EndUndo(True)` groups a batch into one undo step (in the stub; bridge behavior
  unverified); never nest undo calls inside the batch they are meant to undo.
- A timeout after the call was accepted means completion is unknown, not failed. A "retryable"
  transport error does not make a mutation safe to replay. Inspect state, then decide.
- Distinguish an error raised by your script (a Lua/Python exception, a `False` from
  `ConnectInput`) from a transport failure (no response). Keep the real error text in the report.
- Use the least-privileged route that works: sandboxed `run_script` for comp edits,
  `run_script_unsafe` only when files must be read or written. Do not escalate privilege to get
  around an operation that failed for a real reason.
- One driver at a time: no concurrent mutations or renders against the same Resolve session.
- **[from rebuild log, F15]** Issue navigation and render calls sequentially, never in the same turn:
  a navigation that silently failed (playhead stayed) followed by a render in the same turn rendered
  the wrong scene's comp (a compare scored S6 frame 72 against the S7 reference, MAE 115). Check the
  comp identity a render result echoes (comp name, MediaOut1 source) before trusting the frame.
- **[from rebuild log, F16]** `run_script` has a 60 s cap: navigation + delete + paste in one script
  timed out mid-way (the paste landed, only the final MediaOut wire was missing). Split long work and
  re-read state after any timeout.

## §16. Production scale: multi-scene films, render cost, memory [from rebuild log; live, gapfix pass where marked]

General rules for any multi-scene piece. Observed building a 25 s, 8-scene piece natively (750
frames, 1920x1080 @30, about 3,250 tools; a stress-test rebuild) on Resolve Studio 21.1.0.14, a 32 GB
Mac, 2026-09-26/27. The architecture that worked is in
`fusion-motion-design/references/build-orchestration.md` (Module 5: multi-scene films).

**Timeline and items**
- A new timeline inherits the project format (3840x2160 @24 here) (F2). `timeline.create {name,
  width, height, fps, fusionComp, fusionFrames}` sets a custom format and reads it back
  (`fusionFrames` makes the V1 Fusion item exactly that long); `timeline.set_format` changes it
  later (fps only while the timeline is empty). By hand: `CreateEmptyTimeline`, then `SetSetting`
  `useCustomSettings`, `timelineResolutionWidth`, `timelineResolutionHeight`, `timelineFrameRate`.
  **[live, gapfix pass]** 1920x1080 @30 read back on a new timeline in a 3840x2160 @24 project; a later
  fps change on the same timeline (clips present) did not stick and `timeline.set_format` said so.
- Exact-duration Fusion items (F3, F10): `InsertFusionCompositionIntoTimeline` is fixed length and no
  API trims a Fusion Composition item. Recipe: a black carrier clip of the exact length on the target
  track at the record frame, then `AddFusionComp()` on it. `timeline.add_fusion_clip {timeline, track,
  recordFrame, frames, compName}` does both and returns the compRef; `timeline.append_clip {timeline,
  clip, sourceIn, frames, track, recordFrame}` places any Media Pool clip; `comp.create {timeline,
  track, onItem, name}` adds a comp to a V2+ item. `AppendToTimeline` `endFrame` is exclusive (§14).
- V2 items need the Edit-page settle before `SetCurrentTimecode` (§1, F11; live, gapfix pass).
- **[live, gapfix pass]** Resolve adds two `AudioDisplay` tools (`Left`, `Right`) to item comps;
  `comp.clear` keeps them with MediaIn/MediaOut by default.
- **Per-item comps start at comp frame 0 = item start** (K12); the comp's global range can include
  source handles (-48..701 for a scene starting at timeline frame 48, cut from a 750-frame carrier). Author keys in comp frames: comp frame = timeline frame -
  scene start. Shift keys and `time` in expressions on export, never with a TimeSpeed (§11 item 27).
- Expressions cannot reach another comp (F14). Give every scene comp an identical controller (same
  tool name, e.g. `CTRL`, same published controls) generated from one definition, and propagate
  edits with `controller.sync {timeline, tool: "CTRL", inputs}` (**[live, gapfix pass]** a slider
  set to 73 in one item comp arrived in the other item's CTRL, set through the non-current comp).

**Bulk edits and context cost**
- Tool echoes are the largest context cost (F5-F7, F12). Use `setting.paste {quiet}`, `comp.clear
  {keep}` (default keeps MediaIn/MediaOut) before a full re-paste, `tool.delete` with globs inside
  lists (before this fix only a single string globbed; the failed list call echoed 976 names,
  ~30k tokens), and `batch.run {path: ops.json}` for long op lists.
- Timings: one paste of 2,081 tools 116 s (zero renames); a Lua `comp:Paste` of 1,100 tools about
  40 s; deleting about 1,100 tools one glob per op 130 s. **[live, gapfix pass]** 800 simple
  Backgrounds pasted in 2.9 s; `comp.clear` deleted 801 tools in 7.9 s and `tool.delete` (one Lua
  chunk) 801 in 7.3 s (37 s while it still scanned every input of every target for modifiers).
- **[live, gapfix pass]** The per-input wiring walk behind a comp summary costs about 80 bridge calls
  per tool: an uncapped `fu_context` on a 1,100-tool scene comp timed out at 60 s. Summaries now
  detail the first 40 (fu_context) / 150 (comp.info) tools and count the rest by regId.
- References over the MCP output limit: `fu_get_skill {name, reference, section | offset+limit |
  toc}` pages them (F1).

**Render cost**
- Hidden scenes still cook behind Dissolves and Blend-0 Merges (§11 items 24, 25); a trimmed Merge does
  not (§17 item 7). Animated textures re-cook per motion-blur sample (§11 item 28): hold them. With
  separate comps and holds, the full 750-frame Deliver took 13 min in the rebuild (~1 s/frame; the
  heaviest scene 1.6 s/frame, 32 s before the hold). **[live, efficiency lab]** Re-measured on a quiet
  machine after a restart: 21.9 min as 8 items, 14.6 min as one culled comp (§17 item 5).
- Motion-blur `Quality` 8 on a Renderer3D showed stepped copies on a fast card pass; 16 samples
  removed them, a ring wipe needed 32 (COMPARE polish pass). **[live, efficiency lab]** With
  accumulation 12 on, Quality 1 and 8 rendered identically (§17 item 2); the stepped copies seen then
  fit the Sorted-transparency dropouts (§17 item 8) better than a sample shortage.

**Memory (B2, B3)**
- After the 2,081-tool one-comp paste, Resolve sat at 28 GB RSS (GPU "Alloc system memory" 30.7 GB,
  device utilisation 100 %, After Effects also resident at 25 GB on the 32 GB Mac). The same small
  scene went from 4-7 s to 358 s per frame (about 50x); several renders hung with `COMPB_Rendering`
  true and `AbortRender()` did not clear it. 8-bit textures did not help. After a restart: 7 s.
- It returned: 8 scene re-pastes (up to 1,105 tools each) and about 60 comp renders later Resolve
  held 26 GB (14 GB compressed, about 250 MB free) and the next Deliver stalled on frame 47 for over
  10 min. `Fusion().CacheManager.GetSize()` read 0: the Fusion image cache is not what holds it.
- **[live, gapfix pass]** Purge probe (Resolve at ~17 GB): 30 heavy 1080p Saver renders added about
  1.1 GB; `fusion.CacheManager.Purge()` or the undocumented `fusion._Memory_Purge(0)` gave it back
  (17.09 -> 16.0 GB; the second call after the first freed nothing more). `CacheManager.GetSize()`
  under-reports (3.5 KB while ~1 GB was held), so judge by the footprint. A purge frees only render
  cache (about 1 of 17 GB here): most of Resolve's footprint is not Fusion's image cache, and a purge
  is no substitute for a restart. 800-tool pastes and bulk deletes did not move the footprint.
  Read-only prefs: `Global.Memory.PercentCacheLimit` 75 (`AutoPercentCacheLimit` true),
  `Global.Tweaks.GraphicsMemory` 23000; never write them from a script.
- **[live, efficiency lab]** Memory grows with the scenes rendered, not with the number of comps: a
  whole-film Deliver went 6 -> 24 GB both as 8 comps and as one culled comp (the 1,100-tool 3D scene
  adds most). The growth is in untagged VM (Resolve/Fusion image buffers) and GPU-owned memory
  (`footprint` categories), not the malloc heap; a purge after a whole-film Deliver freed 0.1-3 GB.
  Restart between heavy phases (with the user's approval) rather than stacking full-film renders.
- Rules: watch `system.memory` (Resolve footprint, compressed, swap, free %; warns above a threshold;
  fu_context and render results carry the same block; live, gapfix pass); run `system.purge_cache`
  after heavy render sessions; budget re-pastes per session; restart Resolve before the final Deliver.
  Restart only with the user's approval, after `project.save`.
- After a relaunch Resolve may come up on "Untitled Project" (first restart) or on the last project
  (second restart) (F9, B4). Check `fu_context`, then `project.load {name}` (allowlisted projects).

**Deliver (F13, CU2-CU4)**
- **[live, gapfix pass]** While Resolve renders a Deliver job, UI-bound connector calls return code
  `RENDERING` (they used to return UI_BLOCKED; `comp.info` verified) and `fu_context` returns the job's
  progress; `deliver.status` answers throughout (status, percent, ETA, output file). Percent only moves
  when a frame completes: on a job whose first frame never finished it stayed 0 for 8 min.
- `StopRendering()` sets the job to "Cancelled" at once, but `IsRenderingInProgress()` stays true and
  the Stop button stays live until the in-flight frame finishes (about 6 min under memory pressure).
  `deliver.stop` waits for that frame; "Cancelled" is not "idle". The partial movie was finalised
  with the frames done (44).
- **[live, gapfix pass] Never stop a heavy Deliver mid-frame, and never test with CPU-only filters.**
  A 42-frame job through two `Defocus` at `UseGPU` 0, Lens filter, size 60 (1080p) had not finished its
  first frame after 17 s; `StopRendering()` set "Cancelled" at once, `IsRenderingInProgress()` stayed
  true for about 8 min, and Resolve then crashed (about 10:20, 2026-09-27; unsaved scratch work lost).
  Before a Deliver: render one frame of the heaviest part with `render.frame` and read `renderSeconds`;
  cancel only between frames, and prefer letting a short job finish.
