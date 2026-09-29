<!-- liquid-glass.md part 2 of 3; index: liquid-glass.md -->
## 6. Copy-ready Python (Resolve scripting API)

Status: unverified (not yet rendered). Mechanics used are live-verified: `SetActiveTool(None)`
before every `AddTool`, explicit AddTool flags, `SetExpression`, relative Bezier handles.

### 6.1 Build the rig on the current Fusion-page comp

```python
# comp = resolve.Fusion().GetCurrentComp(); bg = comp.FindTool("MediaIn1")
RES = "UHD"   # or "HD"
PX = {"UHD": dict(bezel=35, frost=12, body=25, bloom=8),
      "HD":  dict(bezel=18, frost=12, body=25, bloom=4)}[RES]   # blur sizes are width-relative (live): same at HD; bezel/bloom HD halving untested

def inp(tool, iid):
    return next(v for v in tool.GetInputList().values() if v.GetAttrs()["INPS_ID"] == iid)

def ex(tool, iid, text):
    inp(tool, iid).SetExpression(text)

def add(reg, name, x, y, **vals):
    comp.SetActiveTool(None)                          # [live] prevents auto-wiring
    t = comp.AddTool(reg, False, x, y, False, False)
    if not t:
        raise RuntimeError("AddTool failed: " + reg)
    t.SetAttrs({"TOOLS_Name": name})
    for k, v in vals.items():
        t.SetInput(k, v)
    return t

def wire(dst, port, src):
    if not dst.ConnectInput(port, src):               # [live] check every return
        raise RuntimeError("ConnectInput failed: %s.%s" % (dst.GetAttrs()["TOOLS_Name"], port))

C = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)"
W = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3"
H = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3"
R = "GlassCtrl.NumberIn6"
S = "GlassCtrl.NumberIn3"
ASP = 'comp:GetPrefs("Comp.FrameFormat.Width")/comp:GetPrefs("Comp.FrameFormat.Height")'

def geo(m):
    ex(m, "Center", C); ex(m, "Width", W); ex(m, "Height", H); ex(m, "CornerRadius", R)

comp.Lock()
try:
    ctrl = add("Custom", "GlassCtrl", 0, -6)
    for i, (v, n) in enumerate([(0.5, "Center X"), (0.5, "Center Y"), (1.0, "Scale"),
                                (0.196615, "Width (w/W)"), (0.217130, "Height (h/H)"),
                                (1.0, "Roundness"), (PX["bezel"], "Bezel px"),
                                (0.06, "Refraction")], 1):
        ctrl.SetInput("NumberIn%d" % i, v); ctrl.SetInput("NameforNumber%d" % i, n)
    look = add("Custom", "GlassLook", 1, -6)
    for i, (v, n) in enumerate([(154, "Rim Angle"), (0.0156, "Rim Arc"), (0.00156, "Rim Thickness"),
                                (0.0139, "Shadow Drop"), (0.0208, "Shadow Soft"),
                                (0.0039, "Edge Soft"), (0.00078, "Edge Choke"), (1.0, "Lens k")], 1):
        look.SetInput("NumberIn%d" % i, v); look.SetInput("NameforNumber%d" % i, n)
    for t in (ctrl, look):
        for p in range(1, 5):
            t.SetInput("ShowPoint%d" % p, 0)

    gin = add("PipeRouter", "GlassIn", 0, 0); wire(gin, "Input", bg)

    # masks
    pill = add("RectangleMask", "PillMask", 9, -3); geo(pill)
    shm = add("RectangleMask", "ShadowMask", 1, -3); geo(shm)
    ex(shm, "Center", "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2 - GlassLook.NumberIn4*" + S + ")")
    ex(shm, "SoftEdge", "GlassLook.NumberIn5*" + S)
    edo = add("RectangleMask", "EdgeDarkOuter", 11, -4, BorderWidth=0.001); geo(edo)
    ex(edo, "SoftEdge", "GlassLook.NumberIn6*" + S)
    edh = add("RectangleMask", "EdgeDarkHole", 11, -3, PaintMode="Subtract"); geo(edh)
    ex(edh, "BorderWidth", "-GlassLook.NumberIn7*" + S); wire(edh, "EffectMask", edo)
    rg = add("Background", "RimGradient", 12, -6, Type="Gradient", GradientType="Reflect")
    ex(rg, "Start", C)
    ex(rg, "End", "Point(GlassCtrl.NumberIn1 + GlassLook.NumberIn2*" + S +
       "*cos((GlassLook.NumberIn1-90)*pi/180), GlassCtrl.NumberIn2 + GlassLook.NumberIn2*" + S +
       "*sin((GlassLook.NumberIn1-90)*pi/180)*" + ASP + ")")
    arc = add("BitmapMask", "RimArc", 12, -5, Channel="Luminance", Invert=1); wire(arc, "Image", rg)
    ro = add("RectangleMask", "RimOuter", 12, -4, SoftEdge=0.0003, PaintMode="Multiply"); geo(ro)
    wire(ro, "EffectMask", arc)
    rh = add("RectangleMask", "RimHole", 12, -3, PaintMode="Subtract"); geo(rh)
    ex(rh, "BorderWidth", "-GlassLook.NumberIn3*" + S); wire(rh, "EffectMask", ro)

    # shadow + glass body
    shd = add("BrightnessContrast", "ShadowDarken", 1, 0, Gain=0.70)
    wire(shd, "Input", gin); wire(shd, "EffectMask", shm)
    mag = add("Transform", "GlassMagnify", 2, 0, Size=1.10); ex(mag, "Center", C); ex(mag, "Pivot", C)
    wire(mag, "Input", shd)
    lens = add("Dent", "GlassLens", 3, 0, Type=5, Strength=0.3); ex(lens, "Center", C)   # 5 = Sine Dent (0 pinches, live)
    ex(lens, "Size", "GlassLook.NumberIn8*" + W); wire(lens, "Input", mag)

    bh = add("Blur", "BodyHeight", 3, 2, XBlurSize=PX["body"]); wire(bh, "Input", lens)
    bn = add("CreateBumpMap", "BodyNormal", 4, 2, HeightScale=3); wire(bn, "Input", bh)
    bc = add("BrightnessContrast", "BodyCenter", 5, 2, Brightness=-0.5); wire(bc, "Input", bn)
    body = add("Displace", "BodyRefract", 4, 0, Type=1, XRefraction=0.006, LightPower=0.5, LightAngle=135)
    ex(body, "YRefraction", "XRefraction"); wire(body, "Input", lens); wire(body, "Foreground", bc)

    bs = add("Background", "BezelSrc", 3, 4, TopLeftRed=1, TopLeftGreen=1, TopLeftBlue=1, TopLeftAlpha=1)
    wire(bs, "EffectMask", pill)
    bzh = add("Blur", "BezelHeight", 4, 4); ex(bzh, "XBlurSize", "GlassCtrl.NumberIn7*" + S)
    wire(bzh, "Input", bs)
    bzn = add("CreateBumpMap", "BezelNormal", 5, 4); ex(bzn, "HeightScale", "0.85*GlassCtrl.NumberIn7*" + S)
    wire(bzn, "Input", bzh)
    bzc = add("BrightnessContrast", "BezelCenter", 6, 4, Brightness=-0.5); wire(bzc, "Input", bzn)
    rim = add("Displace", "RimRefract", 5, 0, Type=1, LightPower=0)
    ex(rim, "XRefraction", "GlassCtrl.NumberIn8"); ex(rim, "YRefraction", "GlassCtrl.NumberIn8")
    wire(rim, "Input", body); wire(rim, "Foreground", bzc)

    frost = add("Blur", "GlassFrost", 6, 0, XBlurSize=PX["frost"]); wire(frost, "Input", rim)
    sat = add("BrightnessContrast", "GlassSat", 7, 0, Saturation=1.3); wire(sat, "Input", frost)
    grain = add("FilmGrain", "GlassGrain", 8, 0, MasterStrength=0.03, MasterXSize=0.8, LogProcessing=0)
    wire(grain, "Input", sat)
    gc = add("Merge", "GlassComp", 9, 1)
    wire(gc, "Background", shd); wire(gc, "Foreground", grain); wire(gc, "EffectMask", pill)

    # finishing
    tint = add("BrightnessContrast", "GlassTint", 10, 1, Lift=0.40)
    wire(tint, "Input", gc); wire(tint, "EffectMask", pill)
    edk = add("BrightnessContrast", "EdgeDarken", 11, 1, Gain=0.92)
    wire(edk, "Input", tint); wire(edk, "EffectMask", edh)
    rl = add("BrightnessContrast", "RimLight", 12, 1, Brightness=0.6)
    wire(rl, "Input", edk); wire(rl, "EffectMask", rh)
    bloom = add("SoftGlow", "RimBloom", 13, 1, Threshold=0.6, Gain=1.0, XGlowSize=PX["bloom"])
    wire(bloom, "Input", rl); wire(bloom, "GlowMask", rh)
    fade = add("Merge", "GlassFade", 14, 1, Blend=1.0)
    wire(fade, "Background", gin); wire(fade, "Foreground", bloom)
finally:
    comp.Unlock()
# then: comp.FindTool("MediaOut1").ConnectInput("Input", fade)  and read back wiring
```

Grid coordinates above are node-grid units; multiply by your spacing if AddTool expects pixels.
After the build, read back `inp(t, port).GetConnectedOutput()` for every wired port and list
`comp.GetToolList(False)` to catch stray auto-inserted Merges.

### 6.2 Animate the controller (entrance: rise + settle)

AE rule kept: animate ONLY the controller (plus `GlassFade.Blend` for a fade). Easy ease =
cubic-bezier(0.333, 0, 0.667, 1); handle mapping is live-verified: `RH = {x1*D, y1*V}`,
`LH = {(x2-1)*D, (y2-1)*V}`.

| Beat | 24 fps | 25 fps | 30 fps | Values |
|---|---|---|---|---|
| Rise + scale | 0 -> 18 | 0 -> 19 | 0 -> 23 | Y 0.30 -> 0.50, Scale 0.92 -> 1.00 |
| Fade in | 0 -> 8 | 0 -> 8 | 0 -> 10 | Blend 0 -> 1 |
| Mid-move check frame (0.5 s) | 12 | 13 | 15 | render and read |

```python
def bez(tool, iid, keys):
    """keys: list of (frame, value); easy ease between each pair."""
    tool.AddModifier(iid, "BezierSpline")                       # seeds a stray key: replaced below
    sp = inp(tool, iid).GetConnectedOutput().GetTool()
    kf = {}
    for i, (f, v) in enumerate(keys):
        k = {1: v}
        if i + 1 < len(keys):
            D = keys[i + 1][0] - f
            k["RH"] = {1: 0.333 * D, 2: 0.0}                     # y1 = 0
        if i > 0:
            D = f - keys[i - 1][0]
            k["LH"] = {1: -0.333 * D, 2: 0.0}                    # y2 = 1 -> dv = 0
        kf[f] = k
    sp.SetKeyFrames(kf, True)                                     # True = replace all keys
    return sp

ctrl = comp.FindTool("GlassCtrl")
bez(ctrl, "NumberIn2", [(0, 0.30), (18, 0.50)])
bez(ctrl, "NumberIn3", [(0, 0.92), (18, 1.00)])
bez(comp.FindTool("GlassFade"), "Blend", [(0, 0.0), (8, 1.0)])
# verify: GetKeyFrames() has exactly the intended keys; value at frame 9 of NumberIn2 is ~0.40
```

Taste option: an ease-out entrance reads more "UI". cubic-bezier(0.22, 1, 0.36, 1) over D = 18,
V = 0.2: key 0 `RH = {3.96, 0.2}`, key 18 `LH = {-11.52, 0}`.

### 6.3 Verify render (three frames, PNG)

```python
sv = add("Saver", "GlassCheck", 15, 1)
sv.SetInput("Clip", "/abs/scratch/glass_check_.png")     # [live] PNG works in 21.1
wire(sv, "Input", comp.FindTool("GlassFade"))
for f in (0, 12, 36):
    ok = comp.Render({"Start": f, "End": f, "Wait": True})
# then open glass_check_0012.png etc.; a True return is not acceptance
```

## 7. `.setting` (whole rig as one macro, paste route)

status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frame 0 at UHD, 8 variants) after two fixes (GlassLens Type 5, Frost 12; see the note at the top). Pasted as one group; `LiquidGlass.ConnectInput("MainInput1", bg)` and `saver.ConnectInput("Input", LiquidGlass)` both returned True; `LiquidGlass.SetInput("Frost", 12)` drove the inner Blur. Look judged: frosted, magnified, soft lens curvature, bent band at the rims, floor shadow, bottom-right rim bright, top-left rim faint (raise `RimLight.Brightness` if the brief wants both equal). HD not rendered. Grammar follows `setting-format.md` (InstanceInput/Output,
FuID values, mask `Source = "Mask"`, expressions next to cached values, `PipeRouterInfo`); tool and
input IDs are TSV-checked. UHD defaults; for HD change the pixel values marked `-- HD:` (blur sizes stay the same: Fusion blur is width-relative, live; the bezel and glow halvings are untested).
Paste on the Fusion-page comp: write to a file, then
`cc.Execute('comp:Paste(bmd.readfile([[/abs/path/LiquidGlass.setting]]))')`, poll
`cc.FindTool("LiquidGlass")` up to ~3 s, then wire `LiquidGlass.MainInput1` and its output.

```lua
{
	Tools = ordered() {
		LiquidGlass = GroupOperator {
			Inputs = ordered() {
				MainInput1 = InstanceInput { SourceOp = "GlassIn", Source = "Input", },
				CenterX = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn1", Name = "Center X", Default = 0.5, },
				CenterY = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn2", Name = "Center Y", Default = 0.5, },
				Scale = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn3", Name = "Scale", MinScale = 0.5, MaxScale = 1.5, Default = 1, },
				PanelWidth = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn4", Name = "Width (w/W)", Default = 0.196615, },
				PanelHeight = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn5", Name = "Height (h/H)", Default = 0.21713, },
				Roundness = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn6", Name = "Roundness", MinScale = 0, MaxScale = 1, Default = 1, },
				Bezel = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn7", Name = "Bezel (px)", MinScale = 0, MaxScale = 100, Default = 35, },
				Refraction = InstanceInput { SourceOp = "GlassCtrl", Source = "NumberIn8", Name = "Refraction", MinScale = -0.1, MaxScale = 0.1, Default = 0.06, },
				Magnify = InstanceInput { SourceOp = "GlassMagnify", Source = "Size", Name = "Magnify", MinScale = 1, MaxScale = 1.2, Default = 1.1, },
				Lens = InstanceInput { SourceOp = "GlassLens", Source = "Strength", Name = "Lens", MinScale = 0, MaxScale = 1, Default = 0.3, },
				BodyTexture = InstanceInput { SourceOp = "BodyRefract", Source = "XRefraction", Name = "Body Texture", MinScale = 0, MaxScale = 0.02, Default = 0.006, },
				Frost = InstanceInput { SourceOp = "GlassFrost", Source = "XBlurSize", Name = "Frost", MinScale = 0, MaxScale = 40, Default = 12, },
				Saturation = InstanceInput { SourceOp = "GlassSat", Source = "Saturation", Name = "Backdrop Saturation", MinScale = 1, MaxScale = 2, Default = 1.3, },
				Tint = InstanceInput { SourceOp = "GlassTint", Source = "Lift", Name = "Tint (toward white)", MinScale = 0, MaxScale = 1, Default = 0.4, },
				EdgeDark = InstanceInput { SourceOp = "EdgeDarken", Source = "Gain", Name = "Edge Darkness (gain)", MinScale = 0.8, MaxScale = 1, Default = 0.92, },
				RimIntensity = InstanceInput { SourceOp = "RimLight", Source = "Brightness", Name = "Rim Intensity", MinScale = 0, MaxScale = 1.5, Default = 0.6, },
				RimAngle = InstanceInput { SourceOp = "GlassLook", Source = "NumberIn1", Name = "Rim Angle", MinScale = 90, MaxScale = 180, Default = 154, },
				RimArc = InstanceInput { SourceOp = "GlassLook", Source = "NumberIn2", Name = "Rim Arc", MinScale = 0, MaxScale = 0.05, Default = 0.0156, },
				ShadowGain = InstanceInput { SourceOp = "ShadowDarken", Source = "Gain", Name = "Shadow (gain)", MinScale = 0.5, MaxScale = 1, Default = 0.7, },
				ShadowDrop = InstanceInput { SourceOp = "GlassLook", Source = "NumberIn4", Name = "Shadow Drop", MinScale = 0, MaxScale = 0.05, Default = 0.0139, },
				Grain = InstanceInput { SourceOp = "GlassGrain", Source = "MasterStrength", Name = "Frost Grain", MinScale = 0, MaxScale = 0.1, Default = 0.03, },
				Opacity = InstanceInput { SourceOp = "GlassFade", Source = "Blend", Name = "Glass Opacity", Default = 1, },
			},
			Outputs = {
				MainOutput1 = InstanceOutput { SourceOp = "GlassFade", Source = "Output", },
			},
			ViewInfo = GroupInfo { Pos = { 0, 0 } },
			Tools = ordered() {
				GlassCtrl = Custom {
					NameSet = true,
					Inputs = {
						NumberIn1 = Input { Value = 0.5, },
						NumberIn2 = Input { Value = 0.5, },
						NumberIn3 = Input { Value = 1, },
						NumberIn4 = Input { Value = 0.196615, },
						NumberIn5 = Input { Value = 0.21713, },
						NumberIn6 = Input { Value = 1, },
						NumberIn7 = Input { Value = 35, },            -- HD: 18
						NumberIn8 = Input { Value = 0.06, },
						NameforNumber1 = Input { Value = "Center X", },
						NameforNumber2 = Input { Value = "Center Y", },
						NameforNumber3 = Input { Value = "Scale", },
						NameforNumber4 = Input { Value = "Width (w/W)", },
						NameforNumber5 = Input { Value = "Height (h/H)", },
						NameforNumber6 = Input { Value = "Roundness", },
						NameforNumber7 = Input { Value = "Bezel px", },
						NameforNumber8 = Input { Value = "Refraction", },
						ShowPoint1 = Input { Value = 0, }, ShowPoint2 = Input { Value = 0, },
						ShowPoint3 = Input { Value = 0, }, ShowPoint4 = Input { Value = 0, },
					},
					ViewInfo = OperatorInfo { Pos = { 0, -198 } },
				},
				GlassLook = Custom {
					NameSet = true,
					Inputs = {
						NumberIn1 = Input { Value = 154, },
						NumberIn2 = Input { Value = 0.0156, },
						NumberIn3 = Input { Value = 0.00156, },
						NumberIn4 = Input { Value = 0.0139, },
						NumberIn5 = Input { Value = 0.0208, },
						NumberIn6 = Input { Value = 0.0039, },
						NumberIn7 = Input { Value = 0.00078, },
						NumberIn8 = Input { Value = 1, },
						NameforNumber1 = Input { Value = "Rim Angle", },
						NameforNumber2 = Input { Value = "Rim Arc", },
						NameforNumber3 = Input { Value = "Rim Thickness", },
						NameforNumber4 = Input { Value = "Shadow Drop", },
						NameforNumber5 = Input { Value = "Shadow Soft", },
						NameforNumber6 = Input { Value = "Edge Soft", },
						NameforNumber7 = Input { Value = "Edge Choke", },
						NameforNumber8 = Input { Value = "Lens k", },
						ShowPoint1 = Input { Value = 0, }, ShowPoint2 = Input { Value = 0, },
						ShowPoint3 = Input { Value = 0, }, ShowPoint4 = Input { Value = 0, },
					},
					ViewInfo = OperatorInfo { Pos = { 110, -198 } },
				},
				GlassIn = PipeRouter {
					Inputs = { Input = Input { }, },
					ViewInfo = PipeRouterInfo { Pos = { 0, 0 } },
				},
				PillMask = RectangleMask {
					NameSet = true,
					Inputs = {
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Width = Input { Value = 0.196615, Expression = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Height = Input { Value = 0.21713, Expression = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3", },
						CornerRadius = Input { Value = 1, Expression = "GlassCtrl.NumberIn6", },
					},
					ViewInfo = OperatorInfo { Pos = { 990, -99 } },
				},
				ShadowMask = RectangleMask {
					NameSet = true,
					Inputs = {
						Center = Input { Value = { 0.5, 0.4861 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2 - GlassLook.NumberIn4*GlassCtrl.NumberIn3)", },
						Width = Input { Value = 0.196615, Expression = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Height = Input { Value = 0.21713, Expression = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3", },
						CornerRadius = Input { Value = 1, Expression = "GlassCtrl.NumberIn6", },
						SoftEdge = Input { Value = 0.0208, Expression = "GlassLook.NumberIn5*GlassCtrl.NumberIn3", },
					},
					ViewInfo = OperatorInfo { Pos = { 110, -99 } },
				},
				EdgeDarkOuter = RectangleMask {
					NameSet = true,
					Inputs = {
						BorderWidth = Input { Value = 0.001, },
						SoftEdge = Input { Value = 0.0039, Expression = "GlassLook.NumberIn6*GlassCtrl.NumberIn3", },
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Width = Input { Value = 0.196615, Expression = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Height = Input { Value = 0.21713, Expression = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3", },
						CornerRadius = Input { Value = 1, Expression = "GlassCtrl.NumberIn6", },
					},
					ViewInfo = OperatorInfo { Pos = { 1210, -132 } },
				},
				EdgeDarkHole = RectangleMask {
					NameSet = true,
					Inputs = {
						PaintMode = Input { Value = FuID { "Subtract" }, },
						BorderWidth = Input { Value = -0.00078, Expression = "-GlassLook.NumberIn7*GlassCtrl.NumberIn3", },
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Width = Input { Value = 0.196615, Expression = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Height = Input { Value = 0.21713, Expression = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3", },
						CornerRadius = Input { Value = 1, Expression = "GlassCtrl.NumberIn6", },
						EffectMask = Input { SourceOp = "EdgeDarkOuter", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1210, -99 } },
				},
				RimGradient = Background {
					NameSet = true,
					Inputs = {
						UseFrameFormatSettings = Input { Value = 1, },
						Type = Input { Value = FuID { "Gradient" }, },
						GradientType = Input { Value = FuID { "Reflect" }, },
						Start = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						End = Input { Value = { 0.5068, 0.5249 }, Expression = "Point(GlassCtrl.NumberIn1 + GlassLook.NumberIn2*GlassCtrl.NumberIn3*cos((GlassLook.NumberIn1-90)*pi/180), GlassCtrl.NumberIn2 + GlassLook.NumberIn2*GlassCtrl.NumberIn3*sin((GlassLook.NumberIn1-90)*pi/180)*comp:GetPrefs(\"Comp.FrameFormat.Width\")/comp:GetPrefs(\"Comp.FrameFormat.Height\"))", },
						Gradient = Input { Value = Gradient { Colors = { [0] = { 0, 0, 0, 1 }, [1] = { 1, 1, 1, 1 } } }, },
					},
					ViewInfo = OperatorInfo { Pos = { 1320, -231 } },
				},
				RimArc = BitmapMask {
					NameSet = true,
					Inputs = {
						Image = Input { SourceOp = "RimGradient", Source = "Output", },
						Channel = Input { Value = FuID { "Luminance" }, },
						Invert = Input { Value = 1, },
					},
					ViewInfo = OperatorInfo { Pos = { 1320, -198 } },
				},
				RimOuter = RectangleMask {
					NameSet = true,
					Inputs = {
						SoftEdge = Input { Value = 0.0003, },
						PaintMode = Input { Value = FuID { "Multiply" }, },
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Width = Input { Value = 0.196615, Expression = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Height = Input { Value = 0.21713, Expression = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3", },
						CornerRadius = Input { Value = 1, Expression = "GlassCtrl.NumberIn6", },
						EffectMask = Input { SourceOp = "RimArc", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1320, -165 } },
				},
				RimHole = RectangleMask {
					NameSet = true,
					Inputs = {
						PaintMode = Input { Value = FuID { "Subtract" }, },
						BorderWidth = Input { Value = -0.00156, Expression = "-GlassLook.NumberIn3*GlassCtrl.NumberIn3", },
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Width = Input { Value = 0.196615, Expression = "GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Height = Input { Value = 0.21713, Expression = "GlassCtrl.NumberIn5*GlassCtrl.NumberIn3", },
						CornerRadius = Input { Value = 1, Expression = "GlassCtrl.NumberIn6", },
						EffectMask = Input { SourceOp = "RimOuter", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1320, -132 } },
				},
				ShadowDarken = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Gain = Input { Value = 0.7, },
						Input = Input { SourceOp = "GlassIn", Source = "Output", },
						EffectMask = Input { SourceOp = "ShadowMask", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 110, 0 } },
				},
				GlassMagnify = Transform {
					NameSet = true,
					Inputs = {
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Pivot = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Size = Input { Value = 1.1, },
						Input = Input { SourceOp = "ShadowDarken", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 220, 0 } },
				},
				GlassLens = Dent {
					NameSet = true,
					Inputs = {
						Type = Input { Value = 5, },                      -- Sine Dent (0 pinches, live)
						Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)", },
						Size = Input { Value = 0.196615, Expression = "GlassLook.NumberIn8*GlassCtrl.NumberIn4*GlassCtrl.NumberIn3", },
						Strength = Input { Value = 0.3, },
						Input = Input { SourceOp = "GlassMagnify", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 330, 0 } },
				},
				BodyHeight = Blur {
					NameSet = true,
					Inputs = {
						XBlurSize = Input { Value = 25, },                -- same at HD (blur is width-relative)
						Input = Input { SourceOp = "GlassLens", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 330, 66 } },
				},
				BodyNormal = CreateBumpMap {
					NameSet = true,
					Inputs = {
						HeightScale = Input { Value = 3, },
						Input = Input { SourceOp = "BodyHeight", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 440, 66 } },
				},
				BodyCenter = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Brightness = Input { Value = -0.5, },
						Input = Input { SourceOp = "BodyNormal", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 550, 66 } },
				},
				BodyRefract = Displace {
					NameSet = true,
					Inputs = {
						Type = Input { Value = 1, },
						XRefraction = Input { Value = 0.006, },
						YRefraction = Input { Value = 0.006, Expression = "XRefraction", },
						LightPower = Input { Value = 0.5, },
						LightAngle = Input { Value = 135, },
						Input = Input { SourceOp = "GlassLens", Source = "Output", },
						Foreground = Input { SourceOp = "BodyCenter", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 440, 0 } },
				},
				BezelSrc = Background {
					NameSet = true,
					Inputs = {
						UseFrameFormatSettings = Input { Value = 1, },
						TopLeftRed = Input { Value = 1, },
						TopLeftGreen = Input { Value = 1, },
						TopLeftBlue = Input { Value = 1, },
						TopLeftAlpha = Input { Value = 1, },
						EffectMask = Input { SourceOp = "PillMask", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 330, 132 } },
				},
				BezelHeight = Blur {
					NameSet = true,
					Inputs = {
						XBlurSize = Input { Value = 35, Expression = "GlassCtrl.NumberIn7*GlassCtrl.NumberIn3", },
						Input = Input { SourceOp = "BezelSrc", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 440, 132 } },
				},
				BezelNormal = CreateBumpMap {
					NameSet = true,
					Inputs = {
						WrapMode = Input { Value = FuID { "Clamp" }, },
						HeightScale = Input { Value = 29.75, Expression = "0.85*GlassCtrl.NumberIn7*GlassCtrl.NumberIn3", },
						Input = Input { SourceOp = "BezelHeight", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 550, 132 } },
				},
				BezelCenter = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Brightness = Input { Value = -0.5, },
						Input = Input { SourceOp = "BezelNormal", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 660, 132 } },
				},
				RimRefract = Displace {
					NameSet = true,
					Inputs = {
						Type = Input { Value = 1, },
						XRefraction = Input { Value = 0.06, Expression = "GlassCtrl.NumberIn8", },
						YRefraction = Input { Value = 0.06, Expression = "GlassCtrl.NumberIn8", },
						Input = Input { SourceOp = "BodyRefract", Source = "Output", },
						Foreground = Input { SourceOp = "BezelCenter", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 550, 0 } },
				},
				GlassFrost = Blur {
					NameSet = true,
					Inputs = {
						Filter = Input { Value = FuID { "Fast Gaussian" }, },
						XBlurSize = Input { Value = 12, },                -- same at HD (live-calibrated)
						Input = Input { SourceOp = "RimRefract", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 660, 0 } },
				},
				GlassSat = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Saturation = Input { Value = 1.3, },
						Input = Input { SourceOp = "GlassFrost", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 770, 0 } },
				},
				GlassGrain = FilmGrain {
					NameSet = true,
					Inputs = {
						MasterStrength = Input { Value = 0.03, },
						MasterXSize = Input { Value = 0.8, },
						LogProcessing = Input { Value = 0, },
						Input = Input { SourceOp = "GlassSat", Source = "Output", },
					},
					ViewInfo = OperatorInfo { Pos = { 880, 0 } },
				},
				GlassComp = Merge {
					NameSet = true,
					Inputs = {
						Background = Input { SourceOp = "ShadowDarken", Source = "Output", },
						Foreground = Input { SourceOp = "GlassGrain", Source = "Output", },
						EffectMask = Input { SourceOp = "PillMask", Source = "Mask", },
						PerformDepthMerge = Input { Value = 0, },
					},
					ViewInfo = OperatorInfo { Pos = { 990, 33 } },
				},
				GlassTint = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Lift = Input { Value = 0.4, },
						Input = Input { SourceOp = "GlassComp", Source = "Output", },
						EffectMask = Input { SourceOp = "PillMask", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1100, 33 } },
				},
				EdgeDarken = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Gain = Input { Value = 0.92, },
						Input = Input { SourceOp = "GlassTint", Source = "Output", },
						EffectMask = Input { SourceOp = "EdgeDarkHole", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1210, 33 } },
				},
				RimLight = BrightnessContrast {
					NameSet = true,
					Inputs = {
						Brightness = Input { Value = 0.6, },
						Input = Input { SourceOp = "EdgeDarken", Source = "Output", },
						EffectMask = Input { SourceOp = "RimHole", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1320, 33 } },
				},
				RimBloom = SoftGlow {
					NameSet = true,
					Inputs = {
						Threshold = Input { Value = 0.6, },
						Gain = Input { Value = 1, },
						XGlowSize = Input { Value = 8, },                 -- HD: 4
						Input = Input { SourceOp = "RimLight", Source = "Output", },
						GlowMask = Input { SourceOp = "RimHole", Source = "Mask", },
					},
					ViewInfo = OperatorInfo { Pos = { 1430, 33 } },
				},
				GlassFade = Merge {
					NameSet = true,
					Inputs = {
						Background = Input { SourceOp = "GlassIn", Source = "Output", },
						Foreground = Input { SourceOp = "RimBloom", Source = "Output", },
						Blend = Input { Value = 1, },
						PerformDepthMerge = Input { Value = 0, },
					},
					ViewInfo = OperatorInfo { Pos = { 1540, 33 } },
				},
			},
		},
	},
	ActiveTool = "LiquidGlass",
}
```

Notes on the text: cached `Value`s beside expressions are only display caches; the expression wins.
The `PipeRouter` input is left empty so the group's `MainInput1` feeds it. If a paste errors
silently, wrap the Execute call in `pcall` and report through `comp:SetData` (fusion-realities §9).

## 8. Variants (normalized, valid for 1920x1080 AND 3840x2160)

Normalized inputs are identical at both resolutions; pixel-valued inputs are listed as UHD / HD.

| Control | Reference pill (AE) | Pill / button | Card |
|---|---|---|---|
| Size UHD px (w x h, r) | 755 x 469, capsule | 560 x 168, capsule | 1440 x 880, r 88 |
| Size HD px | 378 x 235 | 280 x 84 | 720 x 440, r 44 |
| `NumberIn4` Width (w/W) | 0.196615 | 0.145833 | 0.375000 |
| `NumberIn5` Height (h/H) | 0.217130 | 0.077778 | 0.407407 |
| `NumberIn6` Roundness | 1.0 | 1.0 | 0.20 (= 88/440) |
| `NumberIn7` Bezel px (UHD / HD) | 35 / 18 | 22 / 11 | 48 / 24 |
| `NumberIn8` Refraction | 0.06 | 0.04 | 0.07 |
| `GlassFrost.XBlurSize` (any res) | 12 | 7 | 18 |
| `GlassMagnify.Size` | 1.10 | 1.06 | 1.06 |
| `GlassLens.Strength`, Lens k | 0.30, 1.0 | 0.20, 1.0 | 0.15, 0.9 |
| `GlassTint.Lift` | 0.40 | 0.30 | 0.35 |
| Rim Thickness (w-units, UHD px) | 0.00156 (6) | 0.00104 (4) | 0.00208 (8) |
| Rim Arc (w-units, UHD px) | 0.0156 (60) | 0.0104 (40) | 0.0260 (100) |
| `RimLight.Brightness` | 0.6 | 0.7 | 0.5 |
| `RimBloom.XGlowSize` (UHD / HD) | 8 / 4 | 5 / 3 | 10 / 5 |
| Shadow Drop (h-units, UHD px) | 0.0139 (30) | 0.0074 (16) | 0.0222 (48) |
| Shadow Soft (w-units, UHD px) | 0.0208 (80) | 0.0104 (40) | 0.0365 (140) |
| `ShadowDarken.Gain` | 0.70 | 0.78 | 0.72 |
| Edge Soft / Edge Choke (w-units) | 0.0039 / 0.00078 | 0.0026 / 0.00052 | 0.0052 / 0.00104 |

Sizing rules behind the table:
- Bezel px <= 0.25 x the panel's short side in px; small elements need a proportionally thicker
  bezel to read (button 13 % of height, reference 7.5 %, card 5.5 %).
- Rim Arc about 8 % of the panel's long side; thickness 4-8 px UHD. Arcs thicker than ~10 px UHD
  read as a stroke, not a reflection.
- Big cards: less lens, less magnify, more frost (a large lens bulge looks like a fishbowl).
- Buttons: less frost (the label must stay readable if text sits on the glass), lighter shadow.
- Vertical deliverables (1080x1920, 2160x3840): recompute Width = w/W and Height = h/H with the
  vertical frame; the Rim gradient's aspect factor reads the comp format automatically; Shadow Drop
  is height-relative, so halve it for the same px drop on a 9:16 frame.
- Button with text: keep the `TextPlus` label outside the group, Merge it over `MainOutput1`; use
  R11 to auto-fit, or R10 to make the label itself glass.

