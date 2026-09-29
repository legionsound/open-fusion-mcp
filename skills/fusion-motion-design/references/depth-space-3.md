<!-- depth-space.md part 3 of 3; index: depth-space.md -->
## 12. Copy-ready builds

### S1. Python helpers (live-verified patterns)
```python
# comp = resolve.Fusion().GetCurrentComp()  -- the Fusion-page comp of an authorized scratch item
def inp(tool, iid):
    for v in tool.GetInputList().values():
        if v.GetAttrs()["INPS_ID"] == iid:
            return v
    raise KeyError(iid)

def add(reg, name, x, y):
    comp.SetActiveTool(None)                      # REQUIRED: else AddTool auto-wires to the active tool
    t = comp.AddTool(reg, False, x, y, False, False)
    if not t:
        raise RuntimeError("AddTool failed: " + reg)
    t.SetAttrs({"TOOLS_Name": name})
    return t

def wire(dst, port, src):
    if not dst.ConnectInput(port, src):           # returns True/False; False = loop or bad port
        raise RuntimeError("ConnectInput failed: %s.%s" % (dst.GetAttrs()["TOOLS_Name"], port))

def ease(tool, iid, f0, v0, f1, v1, x1=0.333, x2=0.667):
    """cubic-bezier(x1,0,x2,1); Python handles are RELATIVE {dt, dv}."""
    tool.AddModifier(iid, "BezierSpline")         # seeds a stray key; replaced below
    spl = inp(tool, iid).GetConnectedOutput().GetTool()
    D = f1 - f0
    spl.SetKeyFrames({f0: {1: v0, "RH": {1: x1 * D, 2: 0.0}},
                      f1: {1: v1, "LH": {1: (x2 - 1) * D, 2: 0.0}}}, True)
    return spl
```

### S2. Python: T1 depth stage with plain truck, fog, DOF, motion blur (R1 + R2a + R4 + R5 + R8)
status: unverified (not yet rendered).
```python
ZF, F_MM, AW_MM, T = 10.0, 35.0, 0.8315 * 25.4, 1.5   # focal dist, lens, aperture mm, total truck
W = lambda z: z * AW_MM / F_MM
PLANES = [("FAR", 0.07, "PlateFar"), ("HILLS", 0.2, "PlateHills"), ("MID", 0.5, "PlateMid"),
          ("FOCAL", 1.0, "PlateFocal"), ("FG", 1.5, "PlateFG")]   # plate tools must already exist
comp.Lock()
try:
    stage = add("Merge3D", "DS_STAGE", 600, 0)
    slot = 1
    for i, (name, p, src) in enumerate(PLANES):
        z = ZF / p
        card = add("ImagePlane3D", "DS_CARD_" + name, 450, 35 * i)
        s = comp.FindTool(src)
        if s:
            wire(card, "MaterialInput", s)
        card.SetInput("Transform3DOp.Translate.Z", -z)
        card.SetInput("Transform3DOp.Scale.X", (W(z) + T) * 1.05)      # 1-unit plane assumed (verify)
        wire(stage, "SceneInput%d" % slot, card); slot += 1
    cam = add("Camera3D", "DS_CAM", 450, 220)
    cam.SetInput("FLength", F_MM); cam.SetInput("PlaneOfFocus", ZF)
    wig = add("Transform3D", "DS_CAMWIG", 520, 220); wire(wig, "SceneInput", cam)
    inp(wig, "Transform3DOp.Translate.X").SetExpression(
        "0.0045*sin(2*pi*time/24) + 0.003*sin(2*pi*time/41 + 1.3)")
    inp(wig, "Transform3DOp.Translate.Y").SetExpression(
        "0.003*sin(2*pi*time/29 + 0.7) + 0.002*sin(2*pi*time/53 + 2.1)")
    wire(stage, "SceneInput%d" % slot, wig)
    fog = add("Fog3D", "DS_HAZE3D", 720, 0); wire(fog, "SceneInput", stage)
    fog.SetInput("FogType", "Exp"); fog.SetInput("FogDensity", 0.0042); fog.SetInput("Radial", 0)
    for k, v in (("FogRed", 0.651), ("FogGreen", 0.784), ("FogBlue", 0.847)):
        fog.SetInput(k, v)
    rnd = add("Renderer3D", "DS_RENDER", 850, 0); wire(rnd, "SceneInput", fog)
    rnd.SetInput("RendererType", "RendererOpenGL")                   # sub-inputs appear after this
    for k, v in (("RendererOpenGL.AccumulationEffects", 1), ("RendererOpenGL.EnableAccumEffects", 1),
                 ("RendererOpenGL.EnableAccumDepthOfField", 1), ("RendererOpenGL.AccumQuality", 16),
                 ("RendererOpenGL.DoFBlur", 0.02), ("RendererOpenGL.TransparencySorting", 1),
                 ("MotionBlur", 1), ("Quality", 6), ("ShutterAngle", 180)):
        rnd.SetInput(k, v)
    sky = add("Background", "DS_SKY", 850, -110)
    sky.SetInput("Type", "Vertical")
    for k, v in (("TopLeftRed", 0.36), ("TopLeftGreen", 0.55), ("TopLeftBlue", 0.72),
                 ("BottomLeftRed", 0.651), ("BottomLeftGreen", 0.784), ("BottomLeftBlue", 0.847)):
        sky.SetInput(k, v)
    out = add("Merge", "DS_COMP", 1000, 0)
    wire(out, "Background", sky); wire(out, "Foreground", rnd)
finally:
    comp.Unlock()
ease(cam, "Transform3DOp.Translate.X", 0, -T / 2, 96, T / 2)          # 4 s plain truck, within budget
# read back: rnd.GetInput("RendererType"), inp(stage,"SceneInput6").GetConnectedOutput(), key values at 0/48/96
```

### S3. Python: T2a 2.5D ladder with one controller (section 4 + R6 + R10)
status: unverified (not yet rendered).
```python
VPX, VPY, PAN = 0.5, 0.45, 0.25                    # vanishing point, total pan (focal-plane widths)
P25 = [("FAR", 0.07, "PlateFar"), ("HILLS", 0.2, "PlateHills"), ("MID", 0.5, "PlateMid"),
       ("FOCAL", 1.0, "PlateFocal"), ("FG", 1.5, "PlateFG")]
comp.Lock()
try:
    ctl = add("Custom", "CAM25", 0, -250)          # number holder only; never wire into the image flow
    ctl.SetInput("NumberIn4", 1.0); ctl.SetInput("NumberIn7", 4.0)   # focus p; K (calibrate by render)
    inp(ctl, "NumberIn5").SetExpression("0.0008*sin(2*pi*time/24) + 0.0005*sin(2*pi*time/41 + 1.3)")
    inp(ctl, "NumberIn6").SetExpression("0.0006*sin(2*pi*time/29 + 0.7) + 0.0004*sin(2*pi*time/53 + 2.1)")
    haze = add("Background", "HAZE25", -150, -150)
    for k, v in (("TopLeftRed", 0.651), ("TopLeftGreen", 0.784), ("TopLeftBlue", 0.847)):
        haze.SetInput(k, v)
    stack = comp.FindTool("SKY25")                 # existing sky Background/MediaIn = first Background
    for i, (name, p, src) in enumerate(P25):
        xf = add("Transform", "XF_" + name, 150 + 150 * i, 100)
        wire(xf, "Input", comp.FindTool(src))
        xf.SetInput("Pivot", {1: VPX, 2: VPY})
        inp(xf, "Center").SetExpression(
            "Point(%g + %g*(CAM25.NumberIn1 + CAM25.NumberIn5), %g + %g*(CAM25.NumberIn2 + CAM25.NumberIn6))"
            % (VPX, p, VPY, p))
        inp(xf, "Size").SetExpression("%g/(1 - %g*CAM25.NumberIn3)" % (1.02 + p * PAN, p))
        xf.SetInput("MotionBlur", 1); xf.SetInput("Quality", 6); xf.SetInput("ShutterAngle", 180)
        bl = add("Blur", "DOF_" + name, 150 + 150 * i, 150); wire(bl, "Input", xf)
        inp(bl, "XBlurSize").SetExpression("CAM25.NumberIn7*abs(%g - CAM25.NumberIn4)" % p)
        m = add("Merge", "M_" + name, 150 + 150 * i, 0)
        wire(m, "Background", stack); wire(m, "Foreground", bl); stack = m
        if name in ("FAR", "HILLS", "MID"):
            hz = add("Merge", "HZ_" + name, 225 + 150 * i, 0)
            wire(hz, "Background", stack); wire(hz, "Foreground", haze)
            hz.SetInput("BlendClone", 0.15); stack = hz
finally:
    comp.Unlock()
ease(ctl, "NumberIn1", 0, -PAN / 2, 96, PAN / 2)   # 4 s pan: FG moves 0.375 W total, within budget
```

### S4. `.setting`: minimal T1 stage (paste route)
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0, 48, 96) after two fixes. As first written it FAILED: `DS_Render` had no `UseFrameFormatSettings` and rendered a 320x240 image in the middle of the UHD sky, and the pasted `DS_Cam` came up with `FilmGate "TV"` (AoV 24.33) so the plates no longer filled frame. Both lines are now in the text. After the fix: plates fill frame at f0/48/96, the FG disc's right edge moves 1651 -> 935 -> 223 px (0.186 W per 48 f, prediction 0.19 W), accumulation DOF softens the FG and far edges, fog lifts the far plate; three UHD frames rendered in 3.4 s. Mid/far shifts not measured (placeholder plates have no vertical edges).
Correction [from rebuild log, K2]: that pass framed correctly with the `FilmGate` line alone, but in a
later rebuild the same line read back while `ApertureW`/`ApertureH` stayed at the TV values (cards
0.79x size). The text now also writes `ApertureW` 0.8315 and `ApertureH` 0.4677, the URSA values the
verified framing already used, so the verified result is unchanged; the added lines are not
re-rendered here.
Three placeholder plates, eased truck with absolute handles, keep-alive, Exp fog, accumulation DOF,
motion blur, 2D sky. Paste on the current Fusion-page comp, poll `FindTool("DS_Comp")`, then swap the
placeholder Backgrounds for real plates.
```lua
{
	Tools = ordered() {
		DS_PlateFar = Background {
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				TopLeftRed = Input { Value = 0.42, }, TopLeftGreen = Input { Value = 0.52, }, TopLeftBlue = Input { Value = 0.6, },
			},
			ViewInfo = OperatorInfo { Pos = { 0, 0 } },
		},
		DS_PlateMid = Background {
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				TopLeftRed = Input { Value = 0.25, }, TopLeftGreen = Input { Value = 0.32, }, TopLeftBlue = Input { Value = 0.3, },
				EffectMask = Input { SourceOp = "DS_MidMask", Source = "Mask", },
			},
			ViewInfo = OperatorInfo { Pos = { 0, 50 } },
		},
		DS_MidMask = RectangleMask {
			Inputs = { Center = Input { Value = { 0.5, 0.2 }, }, Width = Input { Value = 1.1, }, Height = Input { Value = 0.45, }, SoftEdge = Input { Value = 0.01, }, },
			ViewInfo = OperatorInfo { Pos = { -110, 50 } },
		},
		DS_PlateFG = Background {
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				TopLeftRed = Input { Value = 0.06, }, TopLeftGreen = Input { Value = 0.07, }, TopLeftBlue = Input { Value = 0.06, },
				EffectMask = Input { SourceOp = "DS_FGMask", Source = "Mask", },
			},
			ViewInfo = OperatorInfo { Pos = { 0, 100 } },
		},
		DS_FGMask = EllipseMask {
			Inputs = { Center = Input { Value = { 0.1, 0.15 }, }, Width = Input { Value = 0.45, }, Height = Input { Value = 0.45, }, SoftEdge = Input { Value = 0.005, }, },
			ViewInfo = OperatorInfo { Pos = { -110, 100 } },
		},
		DS_CardFar = ImagePlane3D {
			Inputs = {
				MaterialInput = Input { SourceOp = "DS_PlateFar", Source = "Output", },
				["Transform3DOp.Translate.Z"] = Input { Value = -142.857, },
				["Transform3DOp.Scale.X"] = Input { Value = 92.1, },
			},
			ViewInfo = OperatorInfo { Pos = { 110, 0 } },
		},
		DS_CardMid = ImagePlane3D {
			Inputs = {
				MaterialInput = Input { SourceOp = "DS_PlateMid", Source = "Output", },
				["Transform3DOp.Translate.Z"] = Input { Value = -20, },
				["Transform3DOp.Scale.X"] = Input { Value = 14.25, },
			},
			ViewInfo = OperatorInfo { Pos = { 110, 50 } },
		},
		DS_CardFG = ImagePlane3D {
			Inputs = {
				MaterialInput = Input { SourceOp = "DS_PlateFG", Source = "Output", },
				["Transform3DOp.Translate.Z"] = Input { Value = -6.667, },
				["Transform3DOp.Scale.X"] = Input { Value = 5.8, },
			},
			ViewInfo = OperatorInfo { Pos = { 110, 100 } },
		},
		DS_Cam = Camera3D {
			Inputs = {
				FilmGate = Input { Value = FuID { "BMD_URSA_4K_16x9" }, },   -- live fix: a pasted Camera3D defaults to "TV" (AoV 24.33 at 35 mm), the plate scales assume 19.26
				ApertureW = Input { Value = 0.8315, },   -- [from rebuild log, K2] FilmGate alone can leave the TV apertures (0.792 x 0.594)
				ApertureH = Input { Value = 0.4677, },
				FLength = Input { Value = 35, },
				PlaneOfFocus = Input { Value = 10, },
				["Stereo.Mode"] = Input { Value = FuID { "Mono" }, },
				["Transform3DOp.Translate.X"] = Input { SourceOp = "DS_CamTruckX", Source = "Value", },
			},
			ViewInfo = OperatorInfo { Pos = { 110, 160 } },
		},
		DS_CamTruckX = BezierSpline {
			SplineColor = { Red = 250, Green = 59, Blue = 49 },
			KeyFrames = {
				[0] = { -0.75, RH = { 32, -0.75 }, },
				[96] = { 0.75, LH = { 64, 0.75 }, },
			},
		},
		DS_CamWig = Transform3D {
			Inputs = {
				SceneInput = Input { SourceOp = "DS_Cam", Source = "Output", },
				["Transform3DOp.Translate.X"] = Input { Value = 0, Expression = "0.0045*sin(2*pi*time/24) + 0.003*sin(2*pi*time/41 + 1.3)", },
				["Transform3DOp.Translate.Y"] = Input { Value = 0, Expression = "0.003*sin(2*pi*time/29 + 0.7) + 0.002*sin(2*pi*time/53 + 2.1)", },
			},
			ViewInfo = OperatorInfo { Pos = { 220, 160 } },
		},
		DS_Stage = Merge3D {
			Inputs = {
				SceneInput1 = Input { SourceOp = "DS_CardFar", Source = "Output", },
				SceneInput2 = Input { SourceOp = "DS_CardMid", Source = "Output", },
				SceneInput3 = Input { SourceOp = "DS_CardFG", Source = "Output", },
				SceneInput4 = Input { SourceOp = "DS_CamWig", Source = "Output", },
			},
			ViewInfo = OperatorInfo { Pos = { 330, 50 } },
		},
		DS_Haze = Fog3D {
			Inputs = {
				SceneInput = Input { SourceOp = "DS_Stage", Source = "Output", },
				FogType = Input { Value = FuID { "Exp" }, },
				FogDensity = Input { Value = 0.0042, },
				FogRed = Input { Value = 0.651, }, FogGreen = Input { Value = 0.784, }, FogBlue = Input { Value = 0.847, },
			},
			ViewInfo = OperatorInfo { Pos = { 440, 50 } },
		},
		DS_Render = Renderer3D {
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },               -- live fix: without it a pasted Renderer3D renders 320x240
				SceneInput = Input { SourceOp = "DS_Haze", Source = "Output", },
				RendererType = Input { Value = FuID { "RendererOpenGL" }, },
				["RendererOpenGL.AccumulationEffects"] = Input { Value = 1, },
				["RendererOpenGL.EnableAccumEffects"] = Input { Value = 1, },
				["RendererOpenGL.EnableAccumDepthOfField"] = Input { Value = 1, },
				["RendererOpenGL.AccumQuality"] = Input { Value = 16, },
				["RendererOpenGL.DoFBlur"] = Input { Value = 0.02, },
				["RendererOpenGL.TransparencySorting"] = Input { Value = 1, },
				MotionBlur = Input { Value = 1, },
				Quality = Input { Value = 6, },
				ShutterAngle = Input { Value = 180, },
			},
			ViewInfo = OperatorInfo { Pos = { 550, 50 } },
		},
		DS_Sky = Background {
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				Type = Input { Value = FuID { "Vertical" }, },
				TopLeftRed = Input { Value = 0.36, }, TopLeftGreen = Input { Value = 0.55, }, TopLeftBlue = Input { Value = 0.72, },
				BottomLeftRed = Input { Value = 0.651, }, BottomLeftGreen = Input { Value = 0.784, }, BottomLeftBlue = Input { Value = 0.847, },
			},
			ViewInfo = OperatorInfo { Pos = { 550, -50 } },
		},
		DS_Comp = Merge {
			Inputs = {
				Background = Input { SourceOp = "DS_Sky", Source = "Output", },
				Foreground = Input { SourceOp = "DS_Render", Source = "Output", },
			},
			ViewInfo = OperatorInfo { Pos = { 660, 50 } },
		},
	},
	ActiveTool = "DS_Comp",
}
```
Notes: the truck handles are absolute (RH at 1/3 of the segment with the key's own value = ease).
On a name collision the paste renames to `_1` and rewrites internal references; `CameraSelector` is
left at "Default" because the stage holds one camera. Verify: `FindTool("DS_Comp")` exists. Between frame 0 and frame 48 the camera trucks +0.75 units, so the FG plate shifts left ~0.19 W, the focal plane ~0.12 W, the mid plate ~0.06 W, the far plate ~0.009 W, the sky 0; fog lifts the far plate's blacks, the far plate edge is soft, the FG edge moderately soft.

---

## 13. "Why it reads flat" checklist (Fusion)

| Symptom | Likely Fusion cause | Fix |
|---|---|---|
| Planes slide like cardboard | T2: p not shared by Center/Size/Blur/haze. T1: cards scaled to "look far" instead of moved in Z | One p per plane (section 4 rig); T1: z = z_f/p, frustum-fit only for full-bleed plates |
| No parallax at all in 3D | `FLength` animated, Merge3D transform animated, or all cards at one Z | Translate the Camera3D; spread cards by the ladder |
| A card is invisible | card at Z 0 (camera inside it), behind far clip, or wrong `CameraSelector` | Z = −z; `PerspAdaptiveClip` on; set the camera name |
| Everything black | lighting enabled with no lights, or cards affected by lights | lights, or `SurfacePlaneInputs.Lighting.IsAffectedByLights` 0 on cards |
| Stickers on a background | hard alpha, no light wrap, grain per plate | R15 wrap Screen 0.70-0.75, cutout hygiene, one `FilmGrain` pass after the render |
| Far plane too contrasty or black | no Fog3D, fog color ≠ sky horizon, T2 no Lift ladder | Fog3D Exp δ calibrated; sky bottom = fog color; T2 Lift 0-0.07 + haze passes |
| Fog is a milky sheet | Linear fog from Near 0, density too high, fog cards too opaque | Exp with H_far 0.45; fog cards A 0.25-0.35 behind the mid plane |
| Push-in looks like digital zoom | `FLength` or a flattened 2D `Size` animated | R3a dolly (camera Z) or T2 `S0/(1 − p·Δ)`; zoom only exponential |
| Strobing on the move | `MotionBlur` off on Renderer3D / Transforms, or over budget, or 85% AE-style eases | R8 settings; budget table; `ShutterAngle` 270-360; gentler ease |
| Sky creeps or sticks wrong | sky card at finite Z under a truck, or 2D static sky under pan/zoom/target-lock | Section 3 sky rule |
| Scene looks miniature | K too large for scene scale, blur on geometry planes | Subtle preset; split focus; blur only extreme FG and sky |
| Cards reveal flatness | yaw/orbit > 10°, camera too close to a big card | Limit yaw; Displace3D relief (R17) or real geometry |
| Card edges pop, fog cards sort wrong | OpenGL Z-buffer transparency | `RendererOpenGL.TransparencySorting` Sorted, or Software renderer |
| Cards flicker, dim on alternate frames, or two renders of a frame differ | Sorted transparency with accumulation [live, efficiency lab, B5] | `TransparencySorting` 0 (Z buffer); separate near-tied cards in depth (section 8) |
| Cutout casts a rectangle shadow | OpenGL shadows ignore alpha | Software renderer + `MtlStdInputs.Transmittance.AlphaDetail` 1 + caster twin (R13), or shadow cards (R12) |
| Objects float | single soft shadow, shadow card Z-fighting | contact core + skirt, lifted 0.002 (R12) |
| Floor reads as a tilted wall | 2D CornerPositioner Bi-Linear | `MappingType` Perspective, or a real Shape3D floor |
| Focus drifts during a push | `PlaneOfFocus` static while the camera moves | `10 + CAM.Transform3DOp.Translate.Z` |
| Parallax freezes in stills | no keep-alive | R4 sines on CAM_WIG / CAM25 |
| Depth dies in 9:16 | landscape gate in portrait, lateral moves | swap aperture, vertical moves ≤ 3% H, lateral ≤ 1.5% W, horizon 0.667/0.333 |
| Holes at occlusion edges | coverage or hole fill too small | S = (W(z) + T) × 1.05; fill (p_front − p_back) × travel behind FG |
| Cards 0.79x size, frustum under-fills | pasted Camera3D kept the TV apertures [from rebuild log, K2] | write `ApertureW`/`ApertureH`, read `AoV` (section 2) |
| Card pose wrong although the angles are right | rotation order [from rebuild log, K7] | set `Transform3DOp.Rotate.RotOrder` to the order the angles assume (section 3) |
| 3D frames take tens of seconds or minutes | textures re-cooked per blur/DOF sample [from rebuild log, K13]; hidden scenes still cooking behind Dissolves or Blend-0 Merges [from rebuild log, B1] | texture hold (section 8); scenes entering through trimmed Merges (build-orchestration Module 5) [live, efficiency lab] |
| 3D render slower than expected after holds | motion-blur time samples on still frames; static textures re-rendered every frame [live, efficiency lab, T02, T03] | `MotionBlur` off where nothing moves; constant-time freezes (section 8) |
| Incoming card ghosts a frame early | opacity sampled across the shutter [from rebuild log, K15] | stepped opacity (section 8) |
| Card renders black with correct alpha | `MtlStdInputs.ReceivesLighting` 0 [from rebuild log, K4] | leave it 1; unlit = `IsAffectedByLights` 0 (R11) |

---

## 14. Don'ts and failure lessons

- Don't animate cards, a Merge3D or `FLength` to fake a camera move. Animate the Camera3D.
- Don't scale a card to fake distance; move it in Z. Frustum-fit scale is for full-bleed plates only.
- Don't bake grain, blur, haze or lens effects into plates before carding them.
- Don't leave the Renderer3D on Software and expect DOF, or on OpenGL and expect soft cutout shadows.
- Don't add AddTool calls on the Fusion-page comp without `comp.SetActiveTool(None)`; don't ignore
  `ConnectInput` returns; prefer the `.setting` paste for rigs.
- Don't use `noise()` in SimpleExpressions, degrees in `sin()`, or seconds for `time`.
- Don't fade far planes with opacity; converge color (Fog3D, haze passes).
- Don't put a static 2D sky behind any pan, target-locked truck or zoom.
- Don't use strong AE 85% eases on camera moves; peak speed triples and strobes.
- Don't blur perspective-line planes; don't apply heavy top-and-bottom blur (tilt-shift).
- Don't trust blur-size numbers as pixels; calibrate each blur tool once by render.
- Don't leave shadow cards coplanar with the floor (Z-fight).
- Don't orbit more than 8-10° around flat cards.
- Don't judge 3D output before checking `RendererType`, lighting switches and the selected camera.
- Don't grade after the light wrap and grain; grain is the last pixel operation before delivery.
- Don't trust `FilmGate` alone on a pasted Camera3D; write `ApertureW`/`ApertureH` [from rebuild log, K2].
- Don't feed animated 2D texture graphs straight into ImagePlane3D under motion blur or accumulation
  DOF; hold them per frame [from rebuild log, K13].
- Don't retime a motion-blurred 3D render with TimeSpeed [from rebuild log, K12].
- Don't let an in-point opacity ramp straddle the shutter when the cut-in must be clean; step it per
  frame [from rebuild log, K15].

---

## 15. Unverified IDs, indices and semantics (resolve in the live pass)

- **Resolved live 2026-09-26:** every `RendererOpenGL.*` ID below exists once `RendererType` is `RendererOpenGL` (now appended to the TSV with defaults: AccumQuality 2, DoFBlur 0.2, TransparencySorting 0 with options Z Buffer (fast) | Sorted (accurate) | Quick Sort), except the supersampling rate, which is `RendererOpenGL.AntiAliasing.Presets.Color.Supersampling.HighQuality.Rate` (one input, no RateX/RateY). ImagePlane3D base width is 1 unit (height = image H/W). Background "Vertical" puts TopLeft at the top and BottomLeft at the bottom (S4 sky). Renderer3D found the camera parented under `DS_CamWig` (Transform3D).
- **[C] corpus-only (not in the TSV harvest):** `RendererOpenGL.AccumulationEffects`,
  `RendererOpenGL.EnableAccumEffects`, `RendererOpenGL.EnableAccumDepthOfField`,
  `RendererOpenGL.AccumQuality`, `RendererOpenGL.DoFBlur`, `RendererOpenGL.LightingEnabled`,
  `RendererOpenGL.TransparencySorting` (value 1 assumed Sorted), `RendererOpenGL.Channels.Z`,
  `RendererOpenGL.Channels.Vector`, `RendererOpenGL.AntiAliasing.Channels.RGBA.HighQuality.Enable`,
  `RendererOpenGL.AntiAliasing.Presets.Color.Supersampling.HighQuality.RateX/RateY`.
- **Option lists read live 2026-09-26** (value order assumed = list order; Dent and Follower checked by render, Follower did not match): Displace `Type` Radial, X Y; `XChannel`/`YChannel`/`Channel` Red, Green, Blue, Alpha, Luma; CornerPositioner `MappingType` Bi-Linear, Perspective; Transform `Edges` Canvas, Wrap, Duplicate, Mirror; DirectionalBlur `Type` Linear, Radial, Centered, Zoom.
- **[U] option indices:** Displace `Type` 1 = X/Y, `XChannel` 4 = Luminance; Displace3D `Channel`
  luminance index; CornerPositioner `MappingType` 1 = Perspective; LightPoint/LightSpot `DecayType`
  2 = Quadratic; VariBlur `Method` 2 = Defocus and `BlurChannel` 0 = Red; DepthBlur `BlurChannel` Z
  index; Defocus `Filter` 1 = Lens; Transform `Edges` 1 = Wrap; LensDistort `Mode` Distort index.
- **[U] semantics:** ImagePlane3D base width 1 unit; `Transform3DOp.Scale.X` acting as uniform scale
  with lock on; Displace neutral level and `XRefraction` unit; DepthBlur `FocalPoint` sign vs negative
  Z; Fog3D Near/Far behavior in Exp mode (standard OpenGL fog formulas assumed); Camera3D
  `LensShiftY` unit/sign; Background "Vertical" = TopLeft (top) to BottomLeft (bottom); motion blur
  sampling of SimpleExpressions at subframes; `VectorMotionBlur.XScale` 0.5 ≈ 180°; Custom tool `z1`
  value for empty (sky) pixels; Texture2DOperator image input ID; generator motion blur for animated
  internal offsets; renderer finding a camera parented under a Transform3D.
- Not used because unavailable: the Expression modifier via AddModifier (use SimpleExpressions);
  `noise()` in SimpleExpressions.
