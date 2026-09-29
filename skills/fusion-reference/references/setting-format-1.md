<!-- setting-format.md part 1 of 3; index: setting-format.md -->
# Fusion .setting / .comp format, registry IDs and authoring idioms (Resolve 21.1.0.14)
Scope: ground truth mined from 583 installed Fusion files (417 built-in templates in `DaVinci Resolve.app/Contents/Resources/Fusion/Templates/Templates.drfx`, 54 MrAT transitions in `/Library/.../Fusion/Templates/Edit/Transitions`, 30 settings from 19 user `.drfx`, 10 user `.setting`, 72 Reactor/Kartaverse files incl. 65 `.comp`), cross-checked against the live 21.1 registry dump and the 21.1 API stub. Use when: writing or pasting `.setting`/`.comp` text, building Edit-page Title/Transition/Effect/Generator templates, or when a scripting call needs an exact registry ID, input ID, output name or value type.

Evidence conventions: `n=` is occurrence count in the corpus. "(inference)" marks anything not directly observed. Registry IDs were checked against the live registry dump (`fusion-reference/data/fusion-21.1-registry.tsv`); nothing here is invented. Mining code: `scratchpad/corpus/luatable.py` (tolerant Lua-table parser, parses 583/585 files), `mine.py` (aggregator), raw output `stats.json`, `tool_inputs.txt`.

## Mental model

1. A `.setting` is one Lua table literal: `{ Tools = ordered() { <Name> = <RegID> { ... }, ... }, ActiveTool = "<Name>" }`. It is exactly what Fusion puts on the clipboard; pasting it or `comp:Paste(table)` recreates the nodes.
2. The word before each tool's `{` is the **registry ID** (`TextPlus`, `Merge`, `Fuse.Duplicate`, `ofx.com.blackmagicdesign.resolvefx.GaussianBlur`), never the UI name (`Text+`). The key on the left is the **node name**, which is what `SourceOp` and expressions reference.
3. Every value-carrying control is an entry in `Inputs = { <InputID> = Input { ... } }`. An Input holds exactly one of: a static `Value`, a connection (`SourceOp` + `Source`), and optionally an `Expression`. Omitted inputs are at default.
4. Wires are written only on the **receiving** side: `Foreground = Input { SourceOp = "Text1", Source = "Output" }`. There is no edge list.
5. Animation and modifiers are **separate tool entries** (no `ViewInfo`) connected to the input they drive: a keyed number is `SourceOp = "<Tool><Input>"` pointing at a `BezierSpline`; a keyed point goes through a path modifier (`PolyPath`, `XYPath`), never a BezierSpline directly.
6. Macros and groups (`MacroOperator`, `GroupOperator`) wrap an inner `Tools = ordered()` and expose inner inputs via `InstanceInput` and inner outputs via `InstanceOutput`. Edit-page templates are just these macros saved into `Templates/Edit/<Category>`.
7. Edit-page templates never hard-key absolute frames for the main motion when they must fit any clip length: they use `LUTLookup` ("Anim Curves") with `Source = Duration`/`Transition`, or a `KeyStretcher` node, or `time/comp.RenderEnd` expressions.
8. Coordinates are normalized: points are `{x, y}` in 0..1 of image width/height (origin bottom-left), but polyline control points are offsets from the owning tool's `Center` (default 0.5,0.5), so they live around -0.5..0.5.

---

## 1. File format, precisely

### 1.1 Top level

`.setting` (518 non-comp files):
```lua
{
	Tools = ordered() {
		Template = TextPlus { ... },      -- one or more tool entries, order preserved
	},
	ActiveTool = "Template"                -- optional: present in 291/518; a name mismatch is tolerated
}
```
- `Tools` is `ordered() { ... }` in 517/518 `.setting` files (exception: Reactor `kvrViewer.setting`, plain `{}`). Top-level keys observed besides `Tools`/`ActiveTool`: none in settings.
- `ActiveTool` is optional and not validated: `Repeat.setting` ships with `ActiveTool = "Repeat_"` while the group is named `Repeat`.
- Modifiers/splines can sit at file top level beside the group even when the tool they drive is inside the group (16 Title files have `BezierSpline` siblings of the `GroupOperator`/`MacroOperator`; `Edit/Effects/Repeat.setting` keeps `XYPath1` outside the group). Name resolution for `SourceOp` spans the whole file.

`.comp` (65 files, all Fusion Studio 17.4 Kartaverse demos; none built into Resolve templates):
```lua
Composition {
	CurrentTime = 0, RenderRange = { 0, 10 }, GlobalRange = { 0, 10 }, CurrentID = 510,
	PlaybackUpdateMode = 0, Version = "Fusion Studio 17.4.3 build 14", SavedOutputs = 0,
	HeldTools = 0, DisabledTools = 0, LockedTools = 0, AudioOffset = 0, Resumable = true,
	OutputClips = { }, HiQ = true, StereoMode = false, AutoRenderRange = true,
	Tools = { Name = RegID { ... }, ... },  -- plain table, NOT ordered(), in every .comp seen
	Frames = { ... },                        -- window/panel layout
	Prefs = { Comp = { Views = {...}, Unsorted = { GlobalEnd = 10 }, Paths = {}, QuickTime = {} } },
}
```

### 1.2 Lexical rules (verified by the parser)
- Standard Lua table syntax; trailing commas everywhere are fine (`{ 0.5, 0.5, }`); `;` never used.
- Comments allowed: `-- INPID_InputControl = "SliderControl",` appears inside `Subtitles/Animated/Slide In.setting`.
- Keys containing dots or other non-identifier chars must be bracketed strings: `["Gamut.SLogVersion"] = Input {...}`, `["Transform3DOp.Translate.X"]`, `["Layer2.Blend"]`, `["DFTLumaRamp.Softness"]`, `["ParticleStyle.SizeOverLife"]`, `["Text2.Text1Fill"]`.
- Numeric keys use brackets: `[0] = ...`, `[5.625] = ...`, `[-0.94] = ...`.
- Constructors are `Name { ... }` (e.g. `FuID { "SLog2" }`) or `ordered() { ... }`. Strings may be `"..."` with `\n`, `\r\n`, `\"` escapes, or single-quoted (`'HFill'` in HighlightStyle).
- Numbers: plain decimals and exponents (`1e-09`). Line endings may be CRLF.

### 1.3 Tool entry
```lua
Merge1 = Merge {
	CtrlWZoom = false,          -- inspector zoom state (n=417 on LUTLookup alone); safe to omit
	CtrlWShown = false,         -- inspector collapsed (inference); safe to omit
	NameSet = true,             -- the node was renamed by the user
	Inputs = {
		Background = Input { SourceOp = "BG", Source = "Output", },
		Foreground = Input { SourceOp = "Text1", Source = "Output", },
		Blend = Input { Value = 0.5, },
		PerformDepthMerge = Input { Value = 0, },
	},
	ViewInfo = OperatorInfo { Pos = { 163.7, 45.6 } },   -- flow position; modifiers have no ViewInfo
},
```
Tool-level keys observed (besides `Inputs`, `ViewInfo`):

| Key | Where | Meaning / note |
|---|---|---|
| `CtrlWZoom`, `CtrlWShown` | any | UI state only |
| `NameSet = true` | any | user-renamed |
| `ExtentSet = true` | TextPlus, MediaIn | UI state (inference); harmless |
| `PassThrough = true` | any (38) | node disabled/bypassed (inference from name; Fusion attr `TOOLB_PassThrough`) |
| `Colors = { TileColor = { R = 1, G = 0.5, B = 0 } }` | any | node tile color |
| `CustomData = { ... }` | any | persistent data; see 1.13 (Path map, HighlightStyle, MediaProps, Settings slots) |
| `CurrentSettings = n` | any | active settings slot (API: `Operator.SetCurrentSettings(index)`) |
| `UserControls = ordered() { ... }` | any | custom/overridden controls, section 1.11 |
| `SourceOp = "Orig"` | any | this node is an **instance** of `Orig` (1.10) |
| `Transitions = { [0] = "DFTDissolve" }` | Dissolve | transition method registry (`DFTDissolve`, `DFTLumaRamp` seen) |
| `Clips = { Clip { ID = "Clip1", Filename = "Setting:/Images/x.png", FormatID = "PNGFormat", StartFrame = 1, LengthSetManually = true, TrimIn = 0, TrimOut = 0, ExtendFirst = 0, ExtendLast = 0, Loop = 0, AspectMode = 0, Depth = 0, TimeCode = 0, GlobalStart = 0, GlobalEnd = 0 } }` | Loader | media reference lives here, not in Inputs |
| `KeyFrames = {...}`, `SplineColor = { Red, Green, Blue }` | BezierSpline etc. | animation curve |
| `KeyColorSplines = { [0] = {...} }` | LUTBezier | 0..1 lookup curve |
| `DrawMode = "InsertAndModify"` / `"ModifyOnly"`, `ShowKeyPoints`, `ShowHandles` | PolyPath, XYPath | viewer edit mode |
| `Faster = true` | Shake (13) | option flag |
| `PickColor = true` | ColorCurves | UI state |
| `Tools = { ... }` | ColorCurves, groups | **nested child tools**: ColorCurves stores its `LUTBezier` curves (`ColorCurves1Red` etc.) inside its own `Tools` table, not at comp level |

`ViewInfo` classes: `OperatorInfo { Pos = {x,y} }` (tools, n=6073), `GroupInfo` (groups; may add `Flags = { AllowPan, ConnectedSnap, AutoSnap, RemoveRouters }`, `Size = {w,h,..}`, `Direction = "Horizontal"`, `PipeStyle = "Direct"`, `Scale`, `Offset`), `PipeRouterInfo { Pos }`, `StickyNoteInfo { Pos, Flags = { Expanded = true }, Size }` (tool `Note`, text in `Inputs.Comments`), `UnderlayInfo { Pos, Size }` (tool `Underlay`).

### 1.4 The `Input { }` entry
Keys observed inside `Input { }`: `Value` (35,399), `SourceOp` + `Source` (10,013), `Expression` (1,484), `Disabled = true` (358, hides/locks a control, e.g. pRender `OutputMode`), `UserString1` (8). `Input { }` empty is legal (deinstanced input on an instance, or UI-only nest toggles).

An `Expression` may stand alone or next to a cached `Value`:
```lua
Width  = Input { Value = 0.408854, Expression = "(Text1.Output[0].DataWindow[3]-Text1.Output[0].DataWindow[1])/Text1.Output[0].Width+.1", },
SourceStart = Input { Expression = "InFrames * (1-StartSwitch)", },
```

### 1.5 Value types as stored

| Type | Syntax (verbatim from corpus) | n | Notes |
|---|---|---|---|
| Number | `Value = 0.5` | 26,137 | checkboxes, menus and integer enums are Numbers too (`Invert = 1`, `ElementShape2 = 3`) |
| Number (boxed) | `Value = Number { Value = 1 }` | 48 | seen in titles; equivalent (inference) |
| Point | `Value = { 0.5, 0.596154 }` | 2,126 | normalized x,y |
| Point (ctor) | `Value = Point { X = 0, Y = -0.04 }` | 4 | alternate form |
| Text | `Value = "Open Sans"` | 1,604 | Font, Style, Name1, Comments, FuID-less strings |
| Text (ctor) | `Value = Text { }` | 40 | MediaIn `Layer`, OFX serialized params |
| FuID | `Value = FuID { "Fast Gaussian" }` | 4,285 | enumerations by string ID |
| StyledText | `Value = StyledText { Value = "SAMPLE TEXT" }` or `StyledText { Array = { }, Value = "" }` | 143 | TextPlus/Follower text; `Array` holds char-level styling codes (`{ 100, 0, 0, String = "Open Sans" }`) |
| Gradient | `Value = Gradient { Colors = { [0] = { 0, 0, 0, 1 }, [1] = { 1, 1, 1, 1 } } }` | 346 | keys are 0..1 positions, values RGBA |
| Polyline | `Value = Polyline { Closed = true, Points = { { Linear = true, X = 0.0031, Y = 0.0389, LX = -0.001, LY = 0, RX = -4.6e-05, RY = 0 }, ... } }` | 294 | point keys: `X,Y,LX,LY,RX,RY,Linear,LockY,LockP,LockPF,PublishID` |
| BSplinePolyline | `BSplinePolyline { Closed = true, Points = { { X = -0.52, Y = 0.58, W = 2 }, ... } }`; empty 2nd: `BSplinePolyline { Order = 4, Type = "Tensioned", Knots = { } }` | 4 | BSplineMask |
| ColorCurves | `ColorCurves { Curves = { { Points = { { 0, 1 }, { 0.4, 0.2 }, { 0.6, 0 }, { 1, 0 } } }, ... } }` | 61 | ColorCorrector/ColorGain `ColorRanges` |
| ScriptVal | `ScriptVal { { [0] = 2, 1 } }` | 50 | MultiMerge `LayerOrder`, MultiText `TextOrder`, MultiPoly `PolyOrder` |
| Clip | `Clip { Filename = "...", ... }` | 22 | Saver `Clip`, Renderer3D `RendererOpenGL.Clip` |
| Matrix | `Matrix { RefTime = 58, ToRef = { [0] = 1.009, -0, 0, ... 16 values } }` | 6 | MultiText global transform |
| MagicMaskStrokes | `MagicMaskStrokes { }` | 1 | MagicMask `Strokes` |

Polyline geometry: point `X,Y` are relative to the owning tool's `Center` (default `{0.5,0.5}`), handles `LX,LY,RX,RY` are relative to their point. Proof: `Callout Modern Lines.setting` point `{ X = -0.1596, Y = -0.1478, PublishID = "Point0" }` corresponds to published input `Point0 = {0.3404, 0.3522}` (= 0.5 + X, 0.5 + Y). `PublishID = "PointN"` on a polyline point creates a tool input `PointN` (absolute coords) that can be wired (`Point0 = Input { SourceOp = "Publish2", Source = "Value" }`).

### 1.6 Connections and output names
`Source` is the **output ID** on the source tool. Observed output IDs:

| Source tool | Output ID(s) |
|---|---|
| Image tools (Merge, Background, TextPlus, Transform, Blur, MediaIn, Loader, PipeRouter, Renderer3D, pRender, sRender...) | `Output` |
| Masks (RectangleMask, EllipseMask, PolylineMask, BSplineMask, BitmapMask, TriangleMask, MultiPoly) | `Mask` (n=556 on RectangleMask) |
| 3D scene tools (Shape3D, Merge3D, Transform3D, Camera3D, lights, Text3D, Extrude3D) | `Output` |
| Replicate3D | `Data3D` |
| Materials/textures (MtlBlinn, MtlReflect, BumpMap, SphereMap, Texture2DOperator...) | `MaterialOutput` |
| BezierSpline, LUTBezier, LUTLookup, Perturb*, Publish*, XYPath, ResolveParameter | `Value` |
| PolyPath | `Position` (and `Heading`, published as a group output) |
| Vector | `Position` |
| Shake | `X`, `Y` (numbers), `Position` (point) |
| Calculation, KeyStretcher, KeyStretcherMod | `Result` |
| StyledTextFollower | `StyledText` |
| TextScramble | `ScrambledText` |
| Expression (modifier) | `PointResult`, `NumberResult` |
| GradientColorModifier | `Color1`..`Color4` |
| AudioDisplay (Sound) | `Data` (wired into MediaIn `LeftAudio`/`RightAudio`) |
| SwitchNumber | `Output` |
| Locator3D | `Output`, `Position` |
| PolylineStroke | `Out` (into Paint `Paint`) |

Image input IDs are **not** uniform: `Input` (Transform, Blur, BrightnessContrast, most filters), `Background`/`Foreground` (Merge, Dissolve, ChannelBoolean, MatteControl, Fuse.Duplicate; **not** Displace: its image input is `Input` and the map `Foreground`, [live, skills-gap pass] a wire into Displace `Background` is ignored), `EffectMask` (all), `Image` (BitmapMask, SphereMap, Fuse.OCLRays), `Source` (**all ResolveFX OFX tools**), `SceneInput`/`SceneInput1..N` (3D), `MaterialInput` (Shape3D, ImagePlane3D), `ImageInput` (Camera3D projection), `Input1..N` (sMerge, sBoolean), `Layer1.Foreground..` (MultiMerge), `Input0..N` (Switch), `Keyframes` (KeyStretcher), `Map` (Dissolve luma map), `GlowMask`/`HighlightMask`/`GarbageMatte` (pre-masks).

Masks chain through `EffectMask`: `RectangleMask.EffectMask <- RectangleMask.Mask` (n=316) combines masks with `PaintMode` (`Add`, `Subtract`, `Multiply`, `Maximum`, `Invert`).

### 1.7 Animation: BezierSpline
```lua
Follower1_1Delay = BezierSpline {
	SplineColor = { Red = 32, Green = 113, Blue = 253 },
	KeyFrames = {
		[5]  = { 8, RH = { 20.6666666666667, 6 }, Flags = { Linear = true } },
		[52] = { 2, LH = { 36.3333333333333, 4 }, Flags = { Linear = true } }
	}
},
-- driven input:  Delay = Input { SourceOp = "Follower1_1Delay", Source = "Value" },
```
- Key = frame number (comp time). `[1]` of each entry = value. `RH`/`LH` = right/left Bezier handle in **absolute** `{frame, value}` (above: RH x = 5 + (52-5)/3 = 20.667, y = 8 + (2-8)/3 = 6). First key has only `RH`, last only `LH`.
- 1,987 of 8,419 BezierSpline keys have fractional frame times; 40 are negative. Both are legal.
- `Flags` observed: `Linear` (3,280), `LockedY` (2,467), `Loop` (86), `Pingpong` (38), `LoopRel` (18), `StepIn` (17), `PreLoop`, `PrePingpong`. Loop flags sit on the keys bounding the loop (`Burning Engine.setting`).
- `offset = 1e-09` sometimes appears in a key (3 cases) (inference: tiny time offset to disambiguate coincident keys).
- Non-number splines carry `Value = <typed>` per key: text keyframes `[0] = { 0, RH = {...}, Flags = {...}, Value = Text { ... } }` (`Radar.setting`), polyline keyframes `[48] = { 0, Flags = {...}, Value = Polyline { ... } }` (`Planet.setting`).
- Node name convention: `<ToolName><InputID>` (e.g. `Path5Displacement`, `XYPath2X`, `Follower15Opacity`). Any name works.
- Registry spline classes (cls 69): `BezierSpline`, `BSpline`, `CubicSpline`, `NaturalCubicSpline`, `NURBSpline`. Only `BezierSpline` occurs in the corpus.

`LUTBezier` (curve inside a normalized 0..1 domain, used by LUTLookup, Text3D/Extrude3D `ExtrusionProfile`, pEmitter `ParticleStyle.SizeOverLife`/`BlurOverLife`, pTurbulence `StrengthOverLifeLUT`, HotSpot channels, Custom `LUTIn1..4`, Grain, ColorCurves):
```lua
AnimCurves2Lookup = LUTBezier {
	KeyColorSplines = {
		[0] = {                                   -- channel index (always [0] outside ColorCurves)
			[0] = { 0, RH = { 0.1033, 0 }, Flags = { Linear = true } },
			[0.3098] = { 1, LH = { 0.2065, 1 }, RH = { 0.4504, 1 } },
			[1] = { 0, LH = { 0.9105, 0 } }
		}
	},
	SplineColor = { Red = 255, Green = 255, Blue = 255 },
},
```
Keys are x in 0..1, handles absolute in the same 0..1 space.

### 1.8 Modifiers as written
Modifiers are tool entries without `ViewInfo`, wired to the input they drive. Observed forms (source file in parentheses):

- **PolyPath** (registry name "Path"; default for animated Points):
  `Path5 = PolyPath { DrawMode = "InsertAndModify", Inputs = { Displacement = Input { SourceOp = "Path5Displacement", Source = "Value" }, PolyLine = Input { Value = Polyline { Points = {...} } }, Center = Input { Value = { 0.5, 0.456 } } } }` — `Displacement` (0..1 along path, always a BezierSpline, n=86/86), `PolyLine` points relative to the path's own `Center` (default 0.5,0.5). Drives `Transform.Center` (24), `Merge.Center` (11), `RectangleMask.Center` (10), `TextPlus.Center` (9), Follower/TextPlus `Offset1` (9), `Tracker.TrackedCenterN`. (`Rise Fade.setting`, `Horizontal Slide.setting`)
- **XYPath**: `Inputs = { X = Input {...}, Y = Input {...}, Z = ..., Displacement = ... }`, output `Value`; X/Y usually BezierSplines (`XYPath2X`, `XYPath2Y`) or LUTLookups or expressions. (`Crazy Circle.setting`, `Perspective.setting`)
- **Vector**: `Distance` (usually LUTLookup), `Angle` (deg), `ImageAspect` (1.777778 or expression `comp:GetPrefs("Comp.FrameFormat.Width")/comp:GetPrefs("Comp.FrameFormat.Height")`), `Origin` (point); output `Position`. Used 44x on `Transform.Center` in slide/push transitions. (`Fall and Bounce.setting`)
- **LUTLookup** ("Anim Curves"): see 3.x table; output `Value`. Most-used modifier in Edit templates (405 of 472 instances are in Edit templates).
- **Shake**: `XMinimum`, `XMaximum`, `YMinimum`, `YMaximum`, `LockXY`, `Smoothness`, `RandomSeed`; outputs `X`, `Y`, `Position`. (`Vintage Texture.setting`)
- **PerturbNumber / PerturbPoint / PerturbPolyLine**: `Value` (base), `Strength`, `Wobble`, `Speed`, `RandomSeed`, Point adds `XScale`/`YScale`, PolyLine adds `Jaggedness`; output `Value`. (`Hologram Glitch.setting`)
- **StyledTextFollower** ("Follower"): owns the text in its own `Text` input; TextPlus `StyledText` is wired to the Follower's `StyledText` output. (`Random Write On.setting`)
- **Calculation**: `FirstOperand`, `Operator` (number enum; 1,2,3 seen), `SecondOperand`; output `Result`. (`Fade On.setting` multiplies an Anim Curve by a published Tracking value)
- **Expression** modifier: `n1..n9` numbers, `p1..p9` points, `NumberExpression`, `PointExpressionX`, `PointExpressionY` (strings using `n1`, `p1x`, `p1y`), `NameforNumberN`, `NameforPointN`, `ShowNumberN`, `ShowPointN`, `NumberControls`, `PointControls`; outputs `NumberResult`, `PointResult`. (`Advanced Camera Shake.setting`)
- **PublishNumber / PublishPoint / PublishText / PublishFuID**: single `Value` input; output `Value`. Publishing lets several inputs share one value (e.g. PublishFuID drives three LUTLookups' `Curve`, `EaseIn`, `EaseOut`).
- **KeyStretcherMod**: `Keyframes` (<- spline/path), `SourceStart`, `SourceEnd`, `StretchStart`, `StretchEnd`; output `Result`.
- **TimeCode**: `Hrs`, `Mins`, `Secs`, `Frms`, `Flds`, `StartOffset`, `FramesPerSecond`, `PadDigits` -> TextPlus `StyledText`.
- **TextScramble**: `InputText`, `Randomness` -> `ScrambledText`.
- **GradientColorModifier**: `Gradient`, `StartTime`, `EndTime` (`floor(time)`/`ceil(time)` expressions), `Repeat`, `Offset`.
- **SwitchNumber**: `NumberOfInputs`, `Input0..N`, `Name0..N`, `Source`.
- **ResolveParameter** (1 use, no inputs saved) -> RectangleMask `BorderWidth`.
- **AudioDisplay** ("Sound"): no inputs saved; `Data` -> MediaIn audio.

Full modifier registry list is in section 2.3.

### 1.9 Expressions as stored
Plain Lua-ish strings in `Expression = "..."`. Features counted over 1,465 expressions: `time` 297, `iif(` 292, `comp.RenderStart`/`RenderEnd` 281, `comp:GetPrefs(...)` 80, `Point(` 76, multi-line `:` scripts 42, `math.*` 25, `.Output...DataWindow` 9, `Text(` 2, `self.` 1.

| Pattern | Verbatim example | Source |
|---|---|---|
| Link to other tool's input | `Rectangle5.Width`, `Transform3D2.Transform3DOp.Rotate.Z*-1` | Titles, Page Curl |
| Same-tool input (no prefix) | `Height`, `SoftnessX2`, `Offset*-1` | masks, TextPlus, LUTLookup |
| Group/macro published control | `CarPaint.BaseColorRed`, `DVE1.PivotX` | Car Paint, Perspective |
| Point from numbers | `Point(Width/2.0, 0.5)`, `Point(0.5+Folds, 0.5)` | Slice Push, Stage Curtains |
| Time-based | `time*MainBG.Speed` | Optics |
| Normalized transition progress | `time/comp.RenderEnd` inside easing math | MrAT-ZoomShake |
| Comp format | `comp:GetPrefs("Comp.FrameFormat.Height")/comp:GetPrefs("Comp.FrameFormat.Width")` | Callout Modern Lines |
| Conditional | `iif(DVE1.PivotX==0, 0, iif(DVE1.PivotX==1, 0.5, 1))`, `iif(time%12<10,0,1)*onoff` | Perspective, mHelloDV |
| Image metadata | `(Text1.Output[0].DataWindow[3]-Text1.Output[0].DataWindow[1])/Text1.Output[0].Width+.1` | Text Box (auto-fit box to text) |
| Input image size | `self.Input.OriginalWidth*1.25` | Rotate Rays |
| Text result | `Text((math.floor(M_Blue.Width*50)).." %")` | Circle Values |
| Multi-statement | `:local tD = (time - comp.RenderStart) * 1 / comp:GetPrefs().Comp.FrameFormat.Rate; ... return iif(cond, a, b)` | MagicAnimateV3 |
| Modifier output | `1.0-Mix.Value`, `Xf_Shake_1.Input.Width` | Slice Push, Advanced Camera Shake |

Leading/trailing newlines inside the string are tolerated (`"\nPoint(0.5, ...)\n"` in MrAT). Per-frame Lua also exists as a Text input: `FrameRenderScript = Input { Value = "Width = math.max(...)" }` on BetterResize and Crop.

### 1.10 Groups, macros, instances

```lua
FadeOn = GroupOperator {                  -- or MacroOperator
	Inputs = ordered() {
		Input1 = InstanceInput { SourceOp = "Text1", Source = "StyledText", },
		Input4 = InstanceInput { SourceOp = "Text1", Source = "Red1Clone", Name = "Color", ControlGroup = 3, Default = 1, },
		Input19 = InstanceInput { SourceOp = "Calculation1", Source = "SecondOperand", Name = "Tracking", MinScale = 0.5, MaxScale = 1.5, Default = 1, },
	},
	Outputs = { MainOutput1 = InstanceOutput { SourceOp = "Blur1", Source = "Output", } },
	ViewInfo = GroupInfo { Pos = { 0, 0 } },
	Tools = ordered() { Text1 = TextPlus {...}, Calculation1 = Calculation {...}, ... },
}
```
- `GroupOperator` (394, openable in the Node editor) vs `MacroOperator` (83, closed macro). Both load as Edit templates. MrAT and many third-party packs use MacroOperator; Blackmagic's own mostly GroupOperator.
- `InstanceInput` keys (n): `SourceOp`/`Source` (9,462), `Default` (6,227), `ControlGroup` (3,219; same number = one row, e.g. RGBA color or H/V anchor buttons), `Name` (2,959; label override), `Page` (1,267; e.g. `"Controls"`), `Width` (291; `0.5` = half-width), `DefaultX`/`DefaultY` (129; point defaults, sometimes strings `"0.5"`), `MaxScale`/`MinScale` (slider range), `MinAllowed`/`MaxAllowed`, `DefaultText` (text default), `Type` (`"Separator"`, `"Spacer"`, `"BeginNest"`), `Expression` (7), `Value` (22; Comments text).
- The published key (`Input1`, `MainInput1`, `StyledText`...) is the macro's own input ID; order in `ordered()` is the Inspector order (keys need not be sequential).
- `InstanceOutput` keys: `SourceOp`, `Source`, `Name`. `MainOutput1` is the image output; extra `OutputN` can publish modifier outputs (`Output1 -> Path5.Heading`, `Output1 -> Shake1.Position`).
- A group can also carry its own `UserControls` plus plain `Input { Value = ... }` entries in its `Inputs` (59 cases, e.g. `Car Paint.setting` `BaseLayer = Input { Value = ... }`); inner tools read them by expression `CarPaint.BaseColorRed`.
- Groups nest (`mHelloDV Lower3rd.setting` has a KeyStretcher inside a group inside a group).
- `TextPlus` exposes `...Clone` inputs meant for publishing: `Red1Clone`, `Green1Clone`, `Blue1Clone`, `Alpha1Clone`, `CharacterSpacingClone`, `LineSpacingClone`; Merge exposes `BlendClone` (n=28).
- **Instances**: `Instance_BG = Transform { SourceOp = "BG", Inputs = { <only deinstanced inputs> } }` or a renamed instance `LineMask = TextPlus { NameSet = true, SourceOp = "InsideText_Box", Inputs = { EffectMask = Input { }, SettingsNest = Input { }, ... } }`. Empty `Input { }` entries list deinstanced controls with no stored value (inference). Pan/Slide transitions feed `MainInput2` into `Instance_BG.Input`.
- Duplicate node names in different scopes occur in shipped files (`Expression_1` both inside and outside the group in `Advanced Camera Shake.setting`); avoid it when authoring.

### 1.11 UserControls
```lua
UserControls = ordered() {
	Speed = { LINKS_Name = "Animation Speed", LINKID_DataType = "Number", INPID_InputControl = "SliderControl",
	          INP_MaxScale = 20, INP_Default = 10, INP_External = false, ICS_ControlPage = "Controls",
	          INPS_ExecuteOnChange = "tool:UpdateWordAnimation()", },
}
```
Control types (`INPID_InputControl`, n): `LabelControl` 516, `SliderControl` 302, `CheckboxControl` 225, `ButtonControl` 176, `ScrewControl` 170, `ColorControl` 70, `TextEditControl` 31, `RangeControl` 20, `MultiButtonControl` 17, `OffsetControl` 8, `ComboControl` 6. Preview (viewer) widgets via `INPID_PreviewControl`: `RectangleControl` 14, `CrosshairControl` 9, `AngleControl` 3.
`LINKID_DataType`: `"Number"` 1,406, `"Text"` 26, `"Point"` 11, `"StyledText"` 5.

| Key | Values seen | Use |
|---|---|---|
| `LINKS_Name` | label | display name |
| `INP_Default`, `INP_DefaultX`, `INP_DefaultY` | numbers | default |
| `INP_MinScale`/`INP_MaxScale` | 0/1, -360/360 | slider range |
| `INP_MinAllowed`/`INP_MaxAllowed` | -1000000/1000000, 0/1 | hard clamp |
| `INP_Integer` | true/false | integer steps |
| `INP_External` | false (371) | false = not connectable as a node input |
| `INP_Passive` | true (153) | not animatable / no re-render (inference) |
| `INP_SplineType` | `"Default"` | animation spline type |
| `ICS_ControlPage` | `"Controls"` (893), `"Image"`, `"Color"`, `"Common"` | Inspector tab |
| `IC_ControlPage` | 1, 0, -1 | numeric page index |
| `IC_ControlGroup`, `IC_ControlID` | group n; ID -1 (header), 0,1,2,3 (R,G,B,A) | multi-part color rows |
| `IC_Visible = false`, `IC_NoLabel = true`, `IC_Steps` | | UI |
| `ICD_Width` | 0.5 (143), 0.4, 0.25 | fraction of row |
| `ICD_Center` | 1, 0, 180 | slider center/default marker |
| `CBC_TriState` | false | checkbox |
| `LBLC_DropDownButton`, `LBLC_NumInputs`, `LBLC_NestLevel` | true, N, 1 | collapsible label covering the next N inputs |
| `BTNCS_Execute` | Lua string | button script; `tool` = the node that owns the control, e.g. `"tool:SetInput('Input20',1)\n tool:SetInput('Input18',0.283)"` targets the macro's published IDs (`Repeat.setting`) |
| `INPS_ExecuteOnChange` | `"tool:UpdateWordAnimation()"` (44) | run on value change |
| `MBTNC_AddButton` (positional `{ MBTNC_AddButton = "Left" }` entries), `MBTNC_ShowBasicButton`, `MBTNC_ShowName`, `MBTNC_StretchToFit`, `MBTNC_ShowToolTip` | | MultiButtonControl |
| `CLRC_ShowWheel = false`, `CLRC_ColorSpace = 0`/`"HSV"`, `CLRC_NoSliders` | | ColorControl |
| `TEC_Lines`, `TEC_Wrap`, `TEC_ReadOnly` | 25/3/1 | TextEditControl |
| `CC_LabelPosition = "Horizontal"` | | ComboControl |
| `CHC_Style = "NormalCross"`, `PC_ControlID`, `PC_ControlGroup`, `ACID_Center = "Input21"` | | preview controls |
| `CTID_DIB_ID = "Icons.Tools.Tabs.Color"`, `CT_Visible`, `CT_Priority` | | custom Inspector tab icon/visibility |

Color control pattern (4 entries sharing `IC_ControlGroup`): header `{ INPID_InputControl = "ColorControl", IC_ControlID = -1, LINKS_Name = "Color" }`, then `...Red` (`IC_ControlID = 0`), `...Green` (1), `...Blue` (2) (`Car Paint.setting`).
A UserControls entry with the **same ID as a built-in input** overrides its UI: `Polka Dots.setting` re-ranges LUTLookup `Scale` (-2..2) and `Offset` (-5..5); subtitle templates override TextPlus `StyledText` into a read-only `TextEditControl`. Values of user controls live in the same tool's `Inputs` (`Duplicates = Input { Value = 1 }`); my aggregation excludes them from the per-tool tables below.

### 1.12 Edit-page template requirements (observed across 274 built-in + 84 third-party Edit templates)

| Category (folder) | Top node | Image inputs | Output | Timing idiom |
|---|---|---|---|---|
| `Edit/Titles` (134 built-in) | `GroupOperator`/`MacroOperator`, or a **bare `TextPlus`/`MultiText`** (51 files; node always named `Template`) | none | `MainOutput1` | LUTLookup `Source = Duration` (22 files) or `KeyStretcher` (53 titles, 1 generator) or Follower delays |
| `Edit/Generators` (44) | Group/Macro | none | `MainOutput1` | LUTLookup Duration (36), TimeStretcher in Stinger Transitions |
| `Edit/Effects` (29 + 16) | Group/Macro | `MainInput1` = the clip (42/45) | `MainOutput1` | LUTLookup Duration/Custom |
| `Edit/Transitions` (67 + 55) | Group/Macro | `MainInput1` = outgoing A (wired to `Dissolve/Merge.Background`), `MainInput2` = incoming B (`Foreground`) (122/122) | `MainOutput1` | LUTLookup (Source omitted or `Transition`), `Dissolve.Mix` via LUTLookup (43), or `time/comp.RenderEnd` expressions (MrAT) |

- Folders: system `/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/<Category>/...`, user `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/<Category>/...`; subfolders become groups (`Edit/Effects/Custom Fusion Effect/`, `Edit/Titles/Subtitles/Animated/`, `Edit/Generators/Stinger Transitions/`). Fusion-page templates use `Templates/Fusion/<Category>/` (built-in: Backgrounds, Generators, How To, Lens Flares, Looks, Motion Graphics, Particles, Shaders, Styled Text, Tools).
- `.drfx` = zip placed in `.../Fusion/Templates/`; inside: `Edit/<Category>/<Vendor>/<Pack>/<Name>.setting` + `<Name>.png` thumbnail + optional `media/` (`mHelloDV.drfx`). Built-ins ship in `Templates.drfx` inside the app bundle with thumbnails `<Name>.wide.png`, `.small.png`, `.large.png` (+ `@2x`, `.hover`, `.push`, `.active` variants).
- Bundled media paths use the `Setting:` path map (relative to the .setting): `Filename = "Setting:/Images/DRAG LOGO HERE.png"`, `"setting:media/Logo_White.png"`. Packaging writes `CustomData = { Path = { Map = { ["Setting:"] = "Templates:\\MasterSplitscreen.drfx\\Edit\\Effects\\" } } }` (185 tools carry a `Path.Map`, many pointing at the author's disk; harmless).
- Every generator/text/background inside a template sets `UseFrameFormatSettings = 1` with authored `Width = 1920, Height = 1080` (n=186 TextPlus, 307 Background), so output follows the timeline resolution.
- `GlobalIn/GlobalOut` are typically authored (`GlobalOut = 119`, or `GlobalIn = -1000 / -9999`, `GlobalOut = 20000 / 99999` to keep generators valid past the authored range).
- MediaIn inside templates: `Luma Wipe.setting` publishes `MediaIn3.ClipName` as "Luma Clip" so the user picks a Media Pool clip; `Watermark.setting` uses `MediaSource = FuID { "MediaPool" }`, `MediaID = "<uuid>"`. `MediaOut` appears only in one third-party effect (`MasterSplitscreen.setting`, no MainInput); built-in templates never contain MediaOut.
- Animated subtitles (21.x, `Edit/Titles/Subtitles/Animated/*`): group `CustomData.HighlightStyle = { { Time = 0, CharOffsetX = 0.045, CharShearX = -0.66, ElementOpacity = 0, Element8 = { ElementOpacity = 0.001 } }, { Time = 0.375, ... }, ... }` (keyed 0..1 word-animation states; keys seen: `WordScaleX`, `WordAngleY`, `CharOffsetX`, `CharShearX`, `ElementOpacity`, `ElementEnabled`, `ElementShape`, `ElementPriority`, `ElementColorR/G/B/A`, `ElementSoftnessX/Y/Glow/Blend`, `ElementOffsetX/Y`, `ElementScaleX/Y`, `ElementShearX/Y`, `OutlineThickness`, `BorderLevel`, `BorderRound`, `BorderExtendLeft/Top`, nested `ElementN = {...}`; values may be control names as strings, e.g. `ElementColorR = 'InputHCR'`). The TextPlus has UserControls `StyledText` (read-only TextEdit), `Words` ("Words per line"), `WriteOn`, `Speaker`, `Speed`, all with `INPS_ExecuteOnChange = "tool:UpdateWordAnimation()"`. API: `TextPlus:UpdateWordAnimation([style_table])` "Rebuilds animated word styling from a HighlightStyle table" (also on `Text3D`, `sText`).

---

