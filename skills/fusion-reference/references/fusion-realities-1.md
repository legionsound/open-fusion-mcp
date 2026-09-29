<!-- fusion-realities.md part 1 of 2; index: fusion-realities.md -->
# Fusion realities: the facts that cause silent failures

The Fusion counterpart of Higgsfield's `ae-mcp-realities`. Read before the first
mutating Fusion call. Everything marked **[live]** was observed on Resolve Studio
21.1.0.14 (macOS) on 2026-09-26 in a disposable project. Re-probe on another build.
Exact IDs, types, defaults, ranges and option lists live in
[`../data/fusion-21.1-inputs.tsv`](../data/fusion-21.1-inputs.tsv); grep it, do not guess.

## §1. Which comp you are touching

- A timeline item's comp: `item.GetFusionCompByIndex(1)` (or by name). The comp shown on
  the Fusion page is `resolve.Fusion().GetCurrentComp()`. They can differ. Address work
  through the intended timeline item, never "whatever is open".
- **[live]** `comp.Paste()` and Lua `comp:Paste(...)` only work on the comp that is current
  on the Fusion page. On any other comp (or while the Edit page is showing) `Paste` returns
  `False` and creates nothing. To make a comp current:
  `project.SetCurrentTimeline(tl)`, `tl.SetCurrentTimecode(<tc inside the item>)`,
  `resolve.OpenPage("fusion")`, wait about 1.5 s, then `cc = resolve.Fusion().GetCurrentComp()`.
- **[live, gapfix pass, F11]** For an item on V2 or higher that sequence failed for most items in the
  rebuild (NOT_CURRENT): `SetCurrentTimecode` returned True but the playhead did not move. What worked:
  `resolve.OpenPage("edit")`, wait about 2 s (the settle is required), `SetCurrentTimecode` at the
  item's middle, `resolve.OpenPage("fusion")`, wait about 3 s, then confirm with
  `FindTool("<a tool you know is in that comp>")`. Never confirm by comp name: every item comp is
  "Composition1". The connector's `comp.set_current` runs this sequence and verifies identity with a
  data token (verified on a V2 item of a scratch timeline). The Fusion page shows the topmost clip under
  the playhead: a V3 clip over a V2 item made it fail, and the connector names the covering clip.
- AddTool, SetInput, ConnectInput, AddModifier, SetExpression, Render work on a non-current
  item comp **[live]**.
- `timeline.InsertFusionCompositionIntoTimeline()` creates a Fusion Composition
  item (default 12 s at the timeline rate) with only `MediaOut1`. A good disposable lab.
  **[from rebuild log, F3]** Its length is fixed: no API sets or trims a Fusion Composition item.
  **[live, gapfix pass]** For an exact length or a track above V1 use `timeline.add_fusion_clip` (a
  black carrier clip of exactly that length + `AddFusionComp`: 48- and 42-frame items on V2 at record
  frames 0 and 48 landed exactly) or `comp.create {timeline, track, onItem}` on an existing clip (§16).
  An item comp's global range is the whole source range of its clip (a 900-frame carrier under a
  42-frame item gave 0..899), so carriers are cut to the exact length.
- Never experiment in a client project. Use a scratch project/timeline and say so.

## §2. Coordinates and units

| Quantity | Fusion convention | Convert from a pixel spec (W x H frame) |
|---|---|---|
| 2D position (`Center`, `Pivot`, mask `Center`, Text+ `Center`) | normalized 0-1, origin bottom-left, **Y up**, (0.5,0.5) = frame center | `x = px/W`, `y = 1 - py/H` (py measured from top) |
| RectangleMask `Width`/`Height` | **each axis against its own frame dimension** **[live measured]**: 0.5 x 0.5 on 3840x2160 = 1920 x 1080 px | `Width = w/W`, `Height = h/H` |
| EllipseMask `Width`/`Height` | **both axes against frame width** **[live measured]**: 0.25 x 0.25 on 3840x2160 = 960 x 960 px circle | `Width = w/W`, `Height = h/W` (equal values = circle) |
| RectangleMask `CornerRadius` | fraction of half the shorter side **[live measured]**: 0.2 on a 1920x1080 px rect = ~108 px radius; 1.0 = full pill | `CornerRadius = r / (min(w,h)/2)` |
| Mask `SoftEdge`, Shadow `Softness` | fraction of frame width **[live measured]**: SoftEdge 0.01 at 3840 = 42 px 10-90% ramp, centered on the hard edge; Shadow Softness 0.01 about the same | CSS blur B px: `SoftEdge ~= 1.18*B/W` |
| Shadow `ShadowOffset` | {0.5,0.5} = none; x in width units, y in height units, Y up **[live measured]** | `(0.5 + dx/W, 0.5 - dy/H)` |
| Text+ `Size` | relative to image **width** **[live measured]**, default 0.08. Open Sans Bold at Size 0.1: cap height 161 px at W 3840, 91 px at W 2160 (portrait or square) | em px ~= 0.587 x Size x W, so `Size ~= 1.70 x font_px / W`; cap px ~= 0.42 x Size x W (Open Sans; other fonts differ, verify by render). The constant K is per font and weight: Helvetica Neue Bold K 1.478, cap/em 0.714 (`text.size_for_px`) **[live, gapfix pass, K1]**; Light 0.989 x Bold **[from rebuild log, K20]** (03 typography) |
| Text+ `Center` | positions the text block's anchor; with default justification the glyph box is centered on it **[live]** | as 2D position |
| Blur/Glow `XBlurSize`/`XGlowSize` | slider 0..100, default 1/10 **[live]**. Blur size **scales with frame width** **[live measured]**: size 10 = FWHM 30 px at 1920 wide, 58 px at 3840 (sigma about 1.25 x size x W/1920 px, Fast Gaussian) | same value at HD and UHD; `size ~= sigma_px / (1.25 x W/1920)`. Glow not measured |
| Erode/Dilate `Amount` | fraction of width (1 px on HD = 1/1920) | `px / W` |
| Angles on inputs (`Angle`, `Transform3DOp.Rotate.*`) | **degrees** (Transform Angle 0..360, 3D rotate -180..180) | direct |
| Trig inside SimpleExpressions | **radians** **[live]** (`sin(90)` = 0.894, `sin(pi/2)` = 1) | `sin(deg*pi/180)` |
| `time` in SimpleExpressions | **frame number** **[live]** (at frame 10, `time` = 10) | seconds = `time / fps` |
| 3D space | scene units; Camera3D default `FLength` 35 mm, `AoV` 19.26 (harvest), `PlaneOfFocus` 4, near clip 0.1, far 1000 **[live]**. A Camera3D pasted into a 3840x2160 Resolve comp read `AoV` 24.33 (vertical): read it, do not assume; write `ApertureW`/`ApertureH` on pasted cameras (§11 item 17) | ImagePlane3D = **1 unit wide, height = image H/W** **[live measured]** (16:9 -> 1 x 0.5625; 900x1200 -> 1 x 1.333). Visible height at distance d = `2*d*tan(AoV/2)` |
| Transform `Size` | 1 = 100 %, slider 0..5 | `pct / 100` |

The rectangle/ellipse difference is real and easy to get wrong: a "square" RectangleMask
needs `Height = Width x W/H`, while an EllipseMask circle needs `Height = Width`.
**sShapes [live measured]:** sRectangle `Width`, `Height`, `Translate.X` and `Translate.Y` are all
fractions of frame **width** (0.5 x 0.25 on 3840x2160 = 1920 x 960 px; Translate 0.1/0.1 = +384 px
right and up from center); `CornerRadius` follows the RectangleMask rule (fraction of half the shorter
side). So equal sShape Width/Height = a square/circle.

**[live, skills-gap pass]** More measured units (3840x2160):
- The SoftEdge/Softness `B` above is a CSS box-shadow / Figma blur **radius** (Gaussian sigma = B/2):
  Shadow `Softness` 1.18 x 20/W gave a 26 px 10-90 % ramp (sigma ~10 px), so a Figma radius R needs
  `Softness ~= 1.18 x R / W`, not 1.18 x (R/2)/W.
- Text+ `CharacterSpacing` adds (CS - 1) x `Size` x W px per letter gap; `LineSpacing` scales the
  baseline-to-baseline distance (Open Sans Bold: 0.80 x `Size` x W at 1.0, i.e. 1.36 em).
- Transform `XSize`/`YSize` are ignored while `UseSizeAndAspect` is 1 (the default): set it to 0 or
  squash with `Aspect`.
- Chained Transforms act like parent and child: the downstream `Size`/`Angle` scale and rotate the
  upstream `Center` offset about the downstream `Pivot` (offsets add only at Size 1, Angle 0).
- `CornerPositioner` maps the input's whole frame (not its content bounds) onto the four corners.

## §3. Colors and pixels

- Color inputs are float 0-1 per channel, split into separate inputs (`TopLeftRed`,
  `TopLeftGreen`, `TopLeftBlue`, `TopLeftAlpha` on Background; `Red1`/`Green1`/`Blue1`/
  `Alpha1` on Text+ shading element 1; `Red`/`Green`/`Blue`/`Alpha` on sShapes). Hex must be
  converted: `r = int(hex[0:2],16)/255`.
- The Fusion page processes in 32-bit float. Values above 1 are legal and survive until a
  display or an 8/16-bit file clips them.
- Nothing is color managed by default. If Resolve Color Management is on, do not add
  CineonLog/Gamut conversions on top. A MediaIn's Color Space/Curve Type only tag metadata.
- Merge expects a premultiplied foreground. A bright fringe means a straight image
  (Subtractive/Additive toward Subtractive or premultiply first); a dark halo means double
  premultiplication. **[live, skills-gap pass]** `SubtractiveAdditive` 1 (default) = premultiplied FG,
  0 = straight FG; at an alpha-0.5 edge, premultiplied data treated as straight read 0.25 over black and
  0.75 over white, straight data treated as premultiplied read 1.0 over black.
- **[live, skills-gap pass]** A Saver PNG stores straight (unpremultiplied) RGB: premultiply by alpha
  before measuring color from it (a FastNoise, whose noise lives in alpha, reads RGB 1). A Saver whose
  `Clip` path ends in `.exr` writes float RGBA (ffmpeg decodes it as `gbrapf32le`): use it for
  numeric checks below one 8-bit code value.
- **[live, skills-gap pass]** An `EffectMask` limits a tool's effect; it does not create alpha. To cut
  an image to a shape, Merge it "In" a mask image or use `MatteControl`.
- Merge `Background` sets output resolution and bit depth. A Merge with only a Foreground
  outputs nothing.

## §4. IDs: registry, inputs, options

- UI names and registry IDs differ. Examples **[live]**: Text+ = `TextPlus`,
  Rectangle = `RectangleMask`, Polygon = `PolylineMask`, B-Spline = `BSplineMask`,
  Channel Booleans = `ChannelBoolean`, Follower = `StyledTextFollower`,
  Path = `PolyPath`, Perturb = `PerturbNumber`/`PerturbPoint`/`PerturbGradient`/
  `PerturbPolyLine`, Anim Curves = `LUTLookup`, Keyframe Stretcher (modifier) =
  `KeyStretcherMod`, Alembic Mesh 3D = `SurfaceAlembicMesh`, FBX Mesh = `SurfaceFBXMesh`,
  Ambient Light = `LightAmbient`, USD tools start with `u`, Krokodove tools with `KD_`.
- Find a tool: `grep -P '^@' fusion-21.1-inputs.tsv | grep -i glow`.
  Find its inputs: `grep -P '^Glow\t' fusion-21.1-inputs.tsv`.
- Two kinds of choice inputs:
  - `Combo`/`MultiButton` with Number type take the **0-based index** (Merge `FilterMethod`
    default 2, `Edges` 0..3).
  - `ComboID`/`MultiButtonID` with FuID type take the **option string** (Merge `ApplyMode`
    "Normal", "Screen", "Multiply", "Overlay", ...; `Operator` "Over", "In", "Held Out",
    "Atop", "XOr", ...; Blur `Filter` "Fast Gaussian"; Background `Type` "Solid",
    "Horizontal", "Vertical", "Corner", "Gradient"; Renderer3D `RendererType`
    "RendererSoftware" (default), "RendererOpenGL", "RendererOpenGLUV").
- Dotted input IDs are real IDs: `Transform3DOp.Translate.Z`, `Transform3DOp.Rotate.Y`.
- Manual-derived reference files name ports as the manual prints them. When a reference
  file and the TSV disagree, the TSV wins (known cases: Fog3D density port is
  `FogDensityTex`; Alembic registry ID is `SurfaceAlembicMesh`).
- **[live, skills-gap pass]** Inputs the TSV harvest misses or mislabels: `Polyline` on `sPolygon` and
  `PolylineMask` (data type Polyline); `Pattern.Polygon` and the hidden `Track` (Matrix) on
  `Dimension.PlanarTracker`; `SrcGridChange`/`DstGridChange` (Mesh) on `GridWarp`. `Displace`'s image
  input is **`Input`** (its `Background` input accepts a wire and is ignored: Render True, no file);
  setting-format's "Displace uses Background/Foreground" is wrong. Paint's UI "Clone" mode is
  `ApplyMode` "PaintApplyRubThrough" on a `PolylineStroke`, whose `PaintApplyRubThrough.Offset` is a
  point with (0.5, 0.5) = no offset. OFX image input is `Source`; `Fuse.Duplicate`'s is `Background`.
- **[live, skills-gap pass]** Option strings of a `MultiButton` input are in
  `INPST_MultiButtonControl_String` (a `Combo` uses `INPST_ComboControl_String`). DepthBlur
  `BlurChannel` 0 Z, 1 Red, 2 Green, 3 Blue, 4 Alpha, 5 Luma; Text+ `Direction` 0 Automatic,
  1 Horizontal, 2 Reversed Horizontal, 3 Vertical, 4 Reversed Vertical; `LineDirection` 0 Automatic,
  1 Top Down, 2 Bottom Up (both render-confirmed).
- Tracker published outputs **[live]**: `Output`, `SteadyPosition`, `UnsteadyPosition`,
  `SteadyAxis`, `SteadySize`, `UnsteadySize`, `SteadyAngle`, `UnsteadyAngle`, `Position1`
  (offset position of pattern 1), `PerspectivePosition1`, `PositionX1`, `PositionY1`,
  `SteadyPosition1`, `UnsteadyPosition1`.

## §5. Creating, naming, connecting

**[live] The auto-connect trap.** On the comp that is current on the Fusion page, `AddTool`
auto-connects the new tool to the *active* tool even with `autoconnect=False,
automerge=False`: a new Saver spliced itself into a Background's EffectMask pipe, stray
`Merge1..3` tools appeared, and the next `ConnectInput` returned `False` because it would
have made a loop. Fix, verified: call `comp.SetActiveTool(None)` immediately before every
`AddTool`, check every `ConnectInput` return value, and read back wiring with
`GetConnectedOutput()` before rendering. The `.setting` paste route (§9) avoids the problem.

```python
comp.SetActiveTool(None)          # REQUIRED on the Fusion-page comp, harmless elsewhere
comp.Lock()                       # suppresses file-picker dialogs for Loader/Saver/mesh tools
try:
    t = comp.AddTool("TextPlus", False, x, y, False, False)
    # id, defsettings, xpos, ypos, autoconnect, automerge  (explicit flags: the short form auto-merged)
finally:
    comp.Unlock()
t.SetAttrs({"TOOLS_Name": "Title_Main"})   # alnum/underscore, no spaces, no leading digit
t.SetInput("StyledText", "Hello")
t.SetInput("Center", {1: 0.5, 2: 0.62})
merge.ConnectInput("Foreground", t)          # or ("Background", bg)
```

- **[live]** `AddTool(id, False, -32768, -32768, False, False)` inside Lock/Unlock created all
  379 native tools with no dialogs.
- **[live, skills-gap pass]** `comp:Paste` has the same trap: with a tool active it adds a stray `Merge1`
  (active tool on Background, pasted tool on Foreground), and a paste leaves its own last tool active,
  so two pastes in a row chain. Run `comp:SetActiveTool(nil)` before (and after) every paste
  (fusion_kit.paste_setting and the connector now do, and delete any `Merge<n>` the text did not define).
- Lua `tool.TOOLS_Name = "x"` does not rename; use `SetAttrs`.
- Invalid characters in names are stripped silently. Keep names stable and semantic
  (`Card_Price_BG`, `Ctrl_Main`), because expressions reference tools by name.
- Inspect wiring with `inp.GetConnectedOutput()`; do not call `GetInput` on Image/Mask/3D
  ports (a material-port read preceded a UI hang in an earlier session).
- Only the first MediaOut feeds the timeline. Extra MediaOuts send mattes to the Color page.

## §6. Keyframes and Bezier splines [live]

```python
t.AddModifier("Size", "BezierSpline")          # seeds a key at the current frame
sp = next(v for v in t.GetInputList().values()
          if v.GetAttrs()["INPS_ID"] == "Size").GetConnectedOutput().GetTool()
D, V = 24, 1.0                                  # duration in frames, value change
x1, y1, x2, y2 = 0.25, 0.1, 0.25, 1.0           # any cubic-bezier / AE-style curve
sp.SetKeyFrames({
    0:  {1: 0.0, "RH": {1: x1*D, 2: y1*V}},
    24: {1: 1.0, "LH": {1: (x2-1)*D, 2: (y2-1)*V}},
}, True)                                        # True = replace all keys
```

- Python `RH`/`LH` are **relative** `{dt, dv}` offsets from their key. Verified exact:
  `RH {8,0}`, `LH {-8,0}` over 0 to 24 frames gives 0.1562 at frame 6, 0.5 at 12,
  0.8438 at 18, which is cubic-bezier(0.333, 0, 0.667, 1).
- `.setting`/`.comp` files store handles as **absolute** `{frame, value}` coordinates.
  Convert: absolute = key + relative. Never mix the two forms.
- Keys without handles become linear (Fusion fills the handles at one third along the line).
- `GetKeyFrames()` returns string frame keys ("0.0") and value index "1".
- `AddModifier` seeds a key at the comp's **current time** with the current value (after a
  `Render`, the current time can be the last rendered frame, e.g. 21). **[live, verification
  pass]** One `SetKeyFrames(dict, True)` did NOT remove that stray key and dropped the first
  key's `RH`, so the value sagged back after the move. Fix, verified: set
  `comp.CurrentTime = <first key frame>` before `AddModifier`. **[live, connector pass]** Calling
  `SetKeyFrames(dict, True)` again does not remove a stray key (tested twice); a range
  `DeleteKeyFrames(a, b)` can miss it. Single-frame `sp.DeleteKeyFrames(f)` on each stray frame
  (with comp time moved off it) removes it; then re-apply `SetKeyFrames(dict, True)` and assert `GetKeyFrames()` equals exactly the intended frames and check an
  in-between value.
- Removing a stray key can leave bad tangents: rebuild intended handles.
- **[live, skills-gap pass]** `DeleteKeyFrames` cannot remove a spline's last key (one key stays, so the
  input holds that value). Deleting or disconnecting the spline leaves the input at the value it had at
  the comp's **current time**, not the default.
- **[live, skills-gap pass]** `GetKeyFrames()` can include a non-numeric `"Value"` entry (Planar Tracker
  track splines): filter keys before `float(k)`.
- **[live, skills-gap pass]** Twice, `GetInput` read in the same script call right after
  `AddModifier`/`SetKeyFrames` returned stale values (all 0), while the next call read the correct curve.
  Re-read in a separate call before concluding keys are wrong.
- **[live, skills-gap pass]** Loop flags are confirmed only on two-key splines. On a three-key spline
  (0/12/24) Python `Flags = {Loop = true}` on every key looped only the first segment (0 -> 12 repeated
  between 12 and 24, then held); the flag on the first key alone did not loop; the connector's
  `keyframe.add loop` and `keyframe.set_loop` produced no loop. Check `GetInput` past the last key.
- **[live, skills-gap pass]** Polyline shape keys with different point counts do not morph: the mask
  shows the later key's shape from the first frame.

## §7. Expressions [live]

Set from Python with `tool.Input.SetExpression("...")` (Inspector: type `=` then the
expression). Read with `tool.GetInput("Input", frame)`.

| Works | Example |
|---|---|
| Frame-based time | `time`, `floor(time/4)*4` (stepped), `comp.RenderStart` |
| Radian trig, `pi` | `sin(time/24*2*pi)` (1 Hz at 24 fps) |
| Point results | `Point(0.5 + 0.1*sin(time/24*2*pi), 0.5)` |
| Other tools | `Title_Main.Size * 10`, `Title_Main.Center`, `Ctrl_Main.NumberIn1` |
| Self | `self.Size * 2` |
| Other frames | `Title_Main:GetValue('Size', time - 5)` |
| Conditionals | `iif(time > 5, 1, 0)` |
| Lua math | `math.max(0, math.min(1, x))`, `exp`, `abs`, `min`, `max`, `floor` |

Does not work / traps:
- `noise()` is **not** available in SimpleExpressions (the input evaluates to nil). For smooth
  randomness use the Perturb or Shake modifiers, or a sum of incommensurate sines.
- Clear an expression with `SetExpression(None)`. **[live, connector pass]** `SetExpression("")`
  leaves the input at **0** and silently blocks later `SetInput` on that input (the value
  does not change, no error). `SetExpression(None)` clears cleanly and un-sticks an input
  already cleared with `""`. SetInput the intended value after clearing, then read it back.
- **[live, skills-gap pass]** Also verified: multi-line `:` blocks with real newlines set through
  `SetExpression`; `math.atan2`/`acos`/`deg` and `comp:GetPrefs` in a Custom tool's own expressions
  (two-bone IK read-backs matched offline math to 4 decimals); `and` inside `iif(...)`; floored `%`
  outside blocks (`(-0.2) % 1` = 0.8; `math.fmod` keeps the sign); `Tool.Output[0].DataWindow[3]` (1-based
  left, bottom, right, top in pixels) tracks a partial Write On but returns garbage for empty text.
  A text UserControl reads as a Text object: use `CTRL.Label.Value` for the Lua string
  (`CTRL.Label .. "x"` makes the expression nil). `tool.SetData("a.b", v)` is saved in the comp as
  `CustomData = { a = { b = v } }`.
- The Expression *modifier* (separate from SimpleExpressions) uses degrees for trig and can
  only read the current frame per the manual. It could not be attached via `AddModifier` on
  Number/Point hosts in testing; prefer SimpleExpressions.

## §8. Modifiers [live]

- `AddModifier(input, "<RegID>")` return values are inconsistent (`True`, `None`, `False`).
  Judge success by `input.GetConnectedOutput()` changing to a new tool.
- A failed `AddModifier` can still leave an orphan modifier tool in the comp. Deleting a host
  tool does not delete its modifiers. Clean up via `comp.GetToolList(False)`.
- Host types that accepted modifiers: Number (`Transform.Size`), Point (`Transform.Center`),
  Text (`TextPlus.StyledText`), Gradient (`Background.Gradient`), PolyLine
  (`PolylineMask.Polyline`, which already carries a BezierSpline by default).
- Useful modifier IDs: `StyledTextFollower`, `StyledTextCLS`, `TextScramble`, `TextTimer`,
  `TimeCode`, `PerturbNumber`, `PerturbPoint`, `Shake`, `XYPath`, `PolyPath`, `Calculation`,
  `Offset`, `LUTLookup` (Anim Curves), `KeyStretcherMod`, `ResolveParameter`,
  `FairlightAnimator` (audio-driven), `MIDI`, `Probe`, `GradientColorModifier`,
  `KD_NumberBeat`, `KD_NumberRandom`, `KD_TextWrite`, `KD_TextJuggle`, `KD_TextFormula`,
  `Publish*` / `Switch*` families. Inputs of each are in the TSV (header `@<ID>`).

## §9. One-call build: paste a `.setting` graph [live]

Author the whole graph as Fusion's Lua-table text, then paste it. This is the Fusion
equivalent of Higgsfield's one-call HTML/Lottie build and it keeps everything native.

```python
open(path, "w").write(setting_text)             # { Tools = ordered() { Name = RegID { Inputs = {...} }, ... } }
cc = resolve.Fusion().GetCurrentComp()          # must be the Fusion-page comp (§1)
cc.Execute('comp:Paste(bmd.readfile([[' + path + ']]))')
# Execute is DEFERRED: poll cc.FindTool("<first tool name>") for up to ~3 s before continuing
```

- **[live, builders pass]** A paste silently DROPS any `SourceOp` wire that points at a tool
  outside the pasted text (for example `Background = Input { SourceOp = "ExistingBG" }`).
  Wire to existing tools after the paste with `ConnectInput` (fusion_build's `build()` does
  this). Inside one pasted text, a group's inner tool may reference an outer tool pasted in
  the same text.
- **[from rebuild log, K5]** So re-pasting one unit breaks every wire from a shared tool outside
  it (a global speck texture feeding all scenes broke per-scene re-paste). Keep re-pasteable units
  self-contained (own textures), or paste with `setting.paste {rewireExternal: true}` plus
  `connect: [[tool, input, source(, output)]]` for the unit's outbound wires. **[live, gapfix pass]**
  `rewireExternal` reconnected `Background <- MediaIn1` after a paste and read it back; without it the
  result lists the dropped wires (`droppedExternal`).
- **[live, gapfix pass, F5, F7]** A plain paste echoed every tool in the rebuild (773 tools ~15k
  tokens, 2,081 tools 110k chars). `setting.paste` is now quiet above 50 tools: counts by regId,
  renames and a 10-name sample (61 tools verified). Large-paste timings are in §16.
- Route B: `pbcopy` the text and call `cc.Paste()` (returns True). It overwrites the user's
  clipboard: save it with `pbpaste` first and restore it afterwards.
- **[live, skills-gap pass]** A raw newline inside a quoted string in `.setting` text makes Fusion's
  parser fail: `bmd.readfile` returns `nil`, and `comp:Paste(nil)` then pastes the **system
  clipboard** and reports success (it added a stale `Connector_BG` + `Merge1`). Escape newlines as `\n`
  in quoted values, and in the Execute string check `type(t) == 'table'` before `comp:Paste(t)`
  (fusion_kit.paste_setting and the connector's setting.paste now do both).
- **[live, skills-gap pass]** Clear the active tool before pasting (§5): otherwise Fusion auto-merges
  the pasted tool with the active one.
- **[live, 2026-09-27]** Pasting a `Loader` opens a modal "Open File" browser that blocks scripting until
  someone clicks Cancel (3 times in the layout pass, relative and absolute paths). Paste under
  `comp:Lock()` ... `comp:Unlock()` (pcall the paste so Unlock always runs); the connector's paste does.
- **[live, skills-gap pass]** A pasted `Custom` tool also creates four `LUTBezier` splines
  (`<Name>LUTIn1..4`). They are not orphans; count them in audits.
- Lua errors inside `Execute` are silent. Wrap in `pcall` and report through
  `comp:SetData("dbg", msg)`, then read `comp.GetData("dbg")` after a short wait.
- Connections inside the text (`Input { SourceOp = "Name", Source = "Output" }`) are kept.
  Tool names are kept unless they collide. **[live]** On collision the pasted tools get a
  `_1` suffix (`Ctrl_A` becomes `Ctrl_A_1`) and expressions inside the pasted set are
  rewritten to match (`Ctrl_A_1.Size * 3`); anything outside the set, including your own
  script's variables, still refers to the old names. Use unique prefixes per paste.
- Through the Python bridge, `tool.SaveSettings()` with no path returns `{"Tools": {}}` and
  **[live, 2026-09-27]** `comp.CopySettings(tool)` returns `{"Tools": None}`: neither holds the settings, so a
  hash of them never changes. `tool.SaveSettings(path)` WITH a path writes the tool's full `.setting` text
  (inputs, keyed splines, expressions) from any page, for any comp; the connector's cache fingerprint reads
  that file. Otherwise use Lua (`bmd.writestring(comp:CopySettings(list))`) or `item.ExportFusionComp(path, 1)`.
- Format details and verified snippets: `setting-format.md` in this skill.

## §10. Rendering and checking pixels [live]

```python
saver.SetInput("Clip", "/abs/dir/name_.png")    # or in .setting: Clip = Input { Value = Clip { Filename = "...", FormatID = "PNGFormat", }, }
ok = comp.Render({"Start": f, "End": f, "Wait": True})
```

- PNG Saver output works in Resolve 21.1 (`FormatID = "PNGFormat"`) even though the manual
  describes the Resolve Saver as EXR-only. Output: `name_0000.png` style, 4-digit padding.
- **[live, connector pass]** Every `comp.Render(...)` raises a modal "Render completed!" dialog.
  No variant avoids it (tested: Wait True/False, SetBatch, Lock, positional args, current and
  non-current comp). Dismiss it after each render: `fusion_kit.dismiss_render_dialogs()` clicks
  OK only on windows whose text is "Render completed!" (System Events; the calling process needs
  Accessibility permission). The use-fusion connector does this automatically. Dialogs stack across calls, and while any is open the scripting API returns `None` for basic
  calls (`GetCurrentPage`, `CreateEmptyTimeline`). Treat unexpected `None` as a blocking modal: stop calls, screenshot,
  dismiss (UI layer), re-check. Prefer a render path that does not leave the modal, and dismiss after each render batch.
- `Render` returning True is not proof. Check the file exists, its dimensions, and look at it.
- **[from rebuild log, K11]** In Resolve `comp.Render` also renders `MediaOut1`'s chain: a Saver
  render of one small tool paid for the whole scene (3 s with MediaOut1 on that tool, minutes with it
  on the scene output). **[live, gapfix pass]** The connector's `render.frame`/`render.range`/
  `render.contact_sheet`/`render.compare` point MediaOut1 at the rendered tool for the call, restore it
  (read back after each render), and echo the comp identity (name, MediaOut1 source) and Resolve
  memory. By hand, park MediaOut1 on a light tool while inspecting parts and rewire it after.
- **[live, gapfix pass, B1]** A render interrupted by a connector timeout leaves its temp Saver, render
  range and MediaOut1 wiring behind (rebuild: range [100,104]). Verified: a 42-frame `render.range`
  killed at 3 s kept rendering inside Resolve, the scripting API still answered, and `render.cancel`
  (`comp.AbortRender`) stopped it in 1.4 s, dismissed the dialog, deleted the temp Saver and restored
  the range and MediaOut1. It replaces the Escape + "Yes" UI cancel. The next render also repairs
  leftovers on its own.
- **[live, gapfix pass]** Render speed differs by path: a 12-Blur 1080p chain took 2.25 s/frame
  through a Saver PNG `comp.Render` but the Deliver page rendered 90 frames of it in 1.3 s. Budget
  long inspections as Deliver renders, not Saver renders.
- **[live, skills-gap pass]** A render of a tool with no image fails in two ways: a Merge with no
  Background makes `comp.Render` return False and raises a "WARNING! Render did not complete!" modal
  (also blocking); an input wired into an ignored port (Displace `Background`) returns True and writes
  no file. Both dialogs can appear after a first dismiss pass: poll for a few seconds.
  `fusion_kit.render_frames` returned while `GetCurrentPage()` was still None for under a second: wait
  for it to answer before the next call.
- **[live, skills-gap pass]** `Project.ExportCurrentFrameAsStill(path)` grabs the playhead frame only on
  the Edit or Color page (on the Fusion page it returns False and `GetCurrentTimecode()` is None): exact
  frame after `SetCurrentTimecode`, no modal, 0.1-0.2 s at UHD, png 8-bit RGB / tif 16-bit / jpg, and the
  image is the color-managed timeline output, not Fusion pixel values.
- Delivering the timeline is a Deliver-page job; MediaOut feeds the Edit timeline.
- Downscale previews with `sips -Z 960 in.png --out out.png` before viewing to save context.

