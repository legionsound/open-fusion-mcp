<!-- transition-kit.md part 2 of 3; index: transition-kit.md -->
## 4. Worked builds

4.1 push: **status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0, 1, 143, 286, 287 in the 288-frame lab comp, two Backgrounds + Text+ as A/B)** after one shell fix (guards on `GlobalStart`/`GlobalEnd`; with the original `RenderStart`/`RenderEnd` guards a single-frame render of f143 came out 100% B). Other builds: **status: unverified (not yet rendered)**. They are built from shipped idioms and TSV IDs, and each parses once assembled. Timing: 0.5-0.8 s unless the family is a deliberate chapter moment.

| Family | 24 fps | 25 fps | 30 fps | Ease In / Out |
|---|---|---|---|---|
| Whip pan | 8-10 | 8-10 | 10-12 | Expo / Expo |
| Slide push | 12-16 | 12-17 | 15-20 | Cubic / Cubic |
| Zoom-through | 10-14 | 10-15 | 12-18 | Expo / Expo |
| Smear wipe | 12-18 | 13-19 | 15-22 | Cubic / Cubic |
| Door open | 18-24 | 19-25 | 22-30 | Cubic / None (accelerates out) |
| Card flip, cube | 14-20 | 15-21 | 18-24 | Cubic / Cubic (Back out to settle) |
| Page peel | 20-28 | 21-29 | 24-34 | Sine / Cubic (shipped) |
| Luma / gradient wipe | 16-24 | 17-25 | 20-30 | Sine / Sine |

Angles on inputs are degrees; trig in expressions is radians (`deg*pi/180`); `time` is frames [live].

### 4.1 Whip / slide push

A leaves in one direction while B arrives edge to edge from the opposite side. Slide push: Cubic, 12-16 f. Whip: the same file at 8-10 f with Expo/Expo, `ShutterAngle` 360, `Quality` 16, plus the smear add-on.

Graph: `A_In -> A_Move(Center <- VecA <- EaseA) -> Push.Background`; `B_In -> B_Move(Center <- VecB <- EaseB) -> Push.Foreground`.

Decisions: `ImageAspect` 1 and `EaseA.Scale = 1/max(|cos|,|sin|)`, so at any angle B starts exactly one frame away along the push axis. B uses the same angle with `Offset = -Scale` (it runs from -1 frame to 0 in lockstep with A: one shared seam, no gap). A uses `Edges` Duplicate, so the 1 px filtered seam blends into A's edge color instead of showing a dark line.
```lua
-- NAME TK_Push  FX_OUT Push
-- INPUTS
				Input1 = InstanceInput { SourceOp = "VecA", Source = "Angle", Name = "Direction (deg)", Default = 180, },
				Input2 = InstanceInput { SourceOp = "EaseA", Source = "EaseIn", Name = "Ease In", Width = 0.5, },
				Input3 = InstanceInput { SourceOp = "EaseA", Source = "EaseOut", Name = "Ease Out", Width = 0.5, },
				Input4 = InstanceInput { SourceOp = "A_Move", Source = "MotionBlur", Name = "Motion Blur", Default = 1, },
				Input5 = InstanceInput { SourceOp = "A_Move", Source = "ShutterAngle", Name = "Shutter", Default = 180, },
-- TOOLS
				A_Move = Transform { Inputs = {
					Input = Input { SourceOp = "A_In", Source = "Output", },
					Center = Input { SourceOp = "VecA", Source = "Position", },
					Edges = Input { Value = 2, },
					MotionBlur = Input { Value = 1, }, Quality = Input { Value = 8, }, ShutterAngle = Input { Value = 180, },
				}, },
				VecA = Vector { Inputs = {
					Distance = Input { SourceOp = "EaseA", Source = "Value", },
					Angle = Input { Value = 180, },                      -- 180 = content moves left
					ImageAspect = Input { Value = 1, },
				}, },
				EaseA = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Cubic" }, }, EaseOut = Input { Value = FuID { "Cubic" }, },
					Scale = Input { Value = 1, Expression = "1/max(abs(cos(VecA.Angle*pi/180)), abs(sin(VecA.Angle*pi/180)))", },
					Offset = Input { Value = 0, },
				}, },
				B_Move = Transform { Inputs = {
					Input = Input { SourceOp = "B_In", Source = "Output", },
					Center = Input { SourceOp = "VecB", Source = "Position", },
					MotionBlur = Input { Expression = "A_Move.MotionBlur", },
					Quality = Input { Expression = "A_Move.Quality", },
					ShutterAngle = Input { Expression = "A_Move.ShutterAngle", },
				}, },
				VecB = Vector { Inputs = {
					Distance = Input { SourceOp = "EaseB", Source = "Value", },
					Angle = Input { Expression = "VecA.Angle", },
					ImageAspect = Input { Value = 1, },
				}, },
				EaseB = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, Expression = "EaseA.Curve", },
					EaseIn = Input { Value = FuID { "Cubic" }, Expression = "EaseA.EaseIn", },
					EaseOut = Input { Value = FuID { "Cubic" }, Expression = "EaseA.EaseOut", },
					Scale = Input { Expression = "EaseA.Scale", },
					Offset = Input { Expression = "-EaseA.Scale", },         -- -1 frame -> 0
				}, },
				Push = Merge { Inputs = {
					Background = Input { SourceOp = "A_Move", Source = "Output", },
					Foreground = Input { SourceOp = "B_Move", Source = "Output", },
					PerformDepthMerge = Input { Value = 0, },
				}, },
```
Whip add-on: insert `Smear = DirectionalBlur { Input <- Push, Type = 2, Angle = Expression "VecA.Angle", Length <- BellW }` and set FX_OUT to `Smear`, with `BellW = LUTLookup { Easing, Sine/Sine, Mirror = 1, Scale = 0.075, Offset = -0.015, ClipLow = 1 }` (peak Length 0.06). `Type` 2 = Centered is inferred from the manual's menu order (Linear, Radial, Centered, Zoom); the TSV shows a 0..1 slider, so verify the index. At whip speed Transform motion blur needs `Quality` 16+; the smear is cheaper.

Verify: frame 0 = A, last = B; the midpoint seam has no dark or transparent line; on a 9:16 timeline at 45 deg, B starts fully off-frame; blur exists mid-transition only.
**Live 2026-09-26 (UHD, 16:9, Direction 180, Cubic):** f0 and f1 = 98.7% A pixels (rest = white letter), f143 = 49.6% A / 48.6% B with the seam at x 0.504 W and 0 dark pixels, f286 and f287 = 100% B; motion blur visible mid-push. Pasted without inner `ViewInfo` fine; group `ConnectInput("MainInput1/2")` and a Saver on the group worked. 9:16, 45 deg and the whip add-on not tested.

### 4.2 Zoom-through with motion blur

Punch into A, cut on the fastest frame, land out of B. Craft: zoom in log space and match relative zoom speed across the cut. A runs `Size` 1 -> 3 and B runs 1/3 -> 1; the log-symmetric pair makes dS/S equal on both sides at the midpoint, so the cut reads as one move. The swap is a short Window (p 0.42..0.58), not a full-length dissolve. Both Transforms use `Edges` Mirror, so B below Size 1 never exposes transparency (as shipped Zoom In does).

Graph: `A_In -> A_Zoom(Size <- ZoomA) -> Cross.Background`; `B_In -> B_Zoom(Size <- ZoomB) -> Cross.Foreground`; `Cross.Mix <- Window`.
```lua
-- NAME TK_ZoomThrough  FX_OUT Cross
-- INPUTS
				Input1 = InstanceInput { SourceOp = "A_Zoom", Source = "Pivot", Name = "Zoom Center", },
				Input2 = InstanceInput { SourceOp = "ZoomA", Source = "Scale", Name = "Zoom Depth", MinScale = 0.5, MaxScale = 4, Default = 2, },
				Input3 = InstanceInput { SourceOp = "ZoomA", Source = "EaseIn", Name = "Ease In", Width = 0.5, },
				Input4 = InstanceInput { SourceOp = "ZoomA", Source = "EaseOut", Name = "Ease Out", Width = 0.5, },
				Input5 = InstanceInput { SourceOp = "A_Zoom", Source = "ShutterAngle", Name = "Shutter", Default = 270, },
-- TOOLS
				A_Zoom = Transform { Inputs = {
					Input = Input { SourceOp = "A_In", Source = "Output", },
					Size = Input { SourceOp = "ZoomA", Source = "Value", },
					Edges = Input { Value = 3, },
					MotionBlur = Input { Value = 1, }, Quality = Input { Value = 8, }, ShutterAngle = Input { Value = 270, },
				}, },
				ZoomA = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Expo" }, }, EaseOut = Input { Value = FuID { "Expo" }, },
					Scale = Input { Value = 2, }, Offset = Input { Value = 1, },          -- 1 -> 3
				}, },
				B_Zoom = Transform { Inputs = {
					Input = Input { SourceOp = "B_In", Source = "Output", },
					Size = Input { SourceOp = "ZoomB", Source = "Value", },
					Pivot = Input { Expression = "A_Zoom.Pivot", },
					Edges = Input { Value = 3, },
					MotionBlur = Input { Expression = "A_Zoom.MotionBlur", },
					Quality = Input { Expression = "A_Zoom.Quality", },
					ShutterAngle = Input { Expression = "A_Zoom.ShutterAngle", },
				}, },
				ZoomB = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, Expression = "ZoomA.Curve", },
					EaseIn = Input { Value = FuID { "Expo" }, Expression = "ZoomA.EaseIn", },
					EaseOut = Input { Value = FuID { "Expo" }, Expression = "ZoomA.EaseOut", },
					Scale = Input { Expression = "1 - 1/(1 + ZoomA.Scale)", },          -- 1/3 -> 1
					Offset = Input { Expression = "1/(1 + ZoomA.Scale)", },
				}, },
				Cross = Dissolve { Transitions = { [0] = "DFTDissolve" }, Inputs = {
					Background = Input { SourceOp = "A_Zoom", Source = "Output", },
					Foreground = Input { SourceOp = "B_Zoom", Source = "Output", },
					Mix = Input { SourceOp = "Window", Source = "Value", },
				}, },
				Window = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Custom" }, },
					Scale = Input { Value = 1, }, Offset = Input { Value = 0, },
					Lookup = Input { SourceOp = "WindowLookup", Source = "Value", },
				}, },
				WindowLookup = LUTBezier { KeyColorSplines = { [0] = {
					[0] = { 0, RH = { 0.14, 0 }, Flags = { Linear = true } },
					[0.42] = { 0, LH = { 0.28, 0 }, RH = { 0.4733, 0.3333 }, Flags = { Linear = true } },
					[0.58] = { 1, LH = { 0.5267, 0.6667 }, RH = { 0.72, 1 }, Flags = { Linear = true } },
					[1] = { 1, LH = { 0.86, 1 }, Flags = { Linear = true } },
				} }, SplineColor = { Red = 255, Green = 255, Blue = 255 }, },
```
Optional extra smear: `DirectionalBlur` `Type` 3 (Zoom, index inferred), `Center` = expression `A_Zoom.Pivot`, `Length` from a Bell. Verify: exact ends; the midpoint frame is mostly blur; no mirrored edge is visible before p 0.35 (if one is, lower Zoom Depth).

### 4.3 Directional blur (smear) wipe

A soft linear wipe whose edge is buried in a directional smear that peaks as the edge crosses frame center. Wipe axis and smear axis share one published angle (`PublishNumber` `Dir`, fanned out by `SourceOp` and read by expression).

Graph: `Ramp(Background gradient) -> Wipe.Map`; `A_In/B_In -> Wipe(DFTLumaRamp, Mix <- WipeE) -> Smear(DirectionalBlur, Angle <- Dir, Length <- BellL)`.
```lua
-- NAME TK_SmearWipe  FX_OUT Smear
-- INPUTS
				Input1 = InstanceInput { SourceOp = "Dir", Source = "Value", Name = "Direction (deg)", MinScale = 0, MaxScale = 360, Default = 0, },
				Input2 = InstanceInput { SourceOp = "BellL", Source = "Scale", Name = "Smear", MinScale = 0, MaxScale = 0.15, Default = 0.06, },
				Input3 = InstanceInput { SourceOp = "Wipe", Source = "DFTLumaRamp.Softness", Name = "Softness", Default = 0.3, },
				Input4 = InstanceInput { SourceOp = "WipeE", Source = "EaseIn", Name = "Ease In", Width = 0.5, },
				Input5 = InstanceInput { SourceOp = "WipeE", Source = "EaseOut", Name = "Ease Out", Width = 0.5, },
-- TOOLS
				Dir = PublishNumber { Inputs = { Value = Input { Value = 0, }, }, },
				Ramp = Background { Inputs = {
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
					Type = Input { Value = FuID { "Gradient" }, }, GradientType = Input { Value = FuID { "Linear" }, },
					Start = Input { Expression = "Point(0.5 - 0.5*cos(Dir.Value*pi/180), 0.5 - 0.5*sin(Dir.Value*pi/180))", },
					End = Input { Expression = "Point(0.5 + 0.5*cos(Dir.Value*pi/180), 0.5 + 0.5*sin(Dir.Value*pi/180))", },
					Gradient = Input { Value = Gradient { Colors = { [0] = { 0, 0, 0, 1 }, [1] = { 1, 1, 1, 1 }, }, }, },
				}, },
				Wipe = Dissolve { Transitions = { [0] = "DFTLumaRamp" }, Inputs = {
					Operation = Input { Value = FuID { "DFTLumaRamp" }, },
					Background = Input { SourceOp = "A_In", Source = "Output", },
					Foreground = Input { SourceOp = "B_In", Source = "Output", },
					Map = Input { SourceOp = "Ramp", Source = "Output", },
					Mix = Input { SourceOp = "WipeE", Source = "Value", },
					["DFTLumaRamp.Softness"] = Input { Value = 0.3, },
				}, },
				WipeE = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Cubic" }, }, EaseOut = Input { Value = FuID { "Cubic" }, },
					Scale = Input { Value = 1, }, Offset = Input { Value = 0, },
				}, },
				Smear = DirectionalBlur { Inputs = {
					Input = Input { SourceOp = "Wipe", Source = "Output", },
					Type = Input { Value = 2, },                               -- Centered (index inferred)
					Angle = Input { SourceOp = "Dir", Source = "Value", },
					Length = Input { SourceOp = "BellL", Source = "Value", },
				}, },
				BellL = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Sine" }, }, EaseOut = Input { Value = FuID { "Sine" }, },
					Mirror = Input { Value = 1, }, Scale = Input { Value = 0.06, },
					Offset = Input { Expression = "-0.2*Scale", }, ClipLow = Input { Value = 1, },
				}, },
```
`DFTLumaRamp.*` sub-inputs are shipped (Luma Wipe) but not in the TSV dump, because they exist only once `Operation` = `DFTLumaRamp`. If the wipe runs backward, add 180 to Direction instead of inverting Mix. Verify: no B leaks through the softness band on frame 1 (else use the 4.7 fallback); smear is exactly 0 on the first and last ~15 % of frames.

### 4.4 Door open

A splits at the vertical center line; each half swings on its outer edge, accelerating out (ease on the start only), revealing B, with a ~15 % exposure dip at the midpoint.

Graph: `A_In -> LeftLeaf(BrightnessContrast, EffectMask <- MaskR) -> DoorL(ImagePlane3D, Pivot.X -0.5)`; `A_In -> RightLeaf(EffectMask <- MaskL) -> DoorR(Pivot.X 0.5)`; `DoorL + DoorR + Cam -> Doors(Merge3D) -> Render -> Reveal.Foreground`; `B_In -> Reveal.Background`; `Reveal -> Dip(Gain <- DipE)`.

Why: each leaf is the full A with the other half cleared to RGBA 0 (`BrightnessContrast` `Alpha` 1, `Gain` 0 under a mask: shipped Slice Push "Darken" idiom). The plane stays 1 unit wide, so a pivot at x = +/-0.5 is exactly the frame edge at any aspect. `DiscardTransparentPixels` (default 1) keeps the cleared halves from occluding each other. B sits in 2D underneath, so the doors never intersect it. Signs (right-hand rule, verify by render): left +90 and right -90 swing away from camera; a negative Swing swings toward it.
```lua
-- NAME TK_Door  FX_OUT Dip
-- INPUTS
				Input1 = InstanceInput { SourceOp = "SwingE", Source = "Scale", Name = "Swing (deg)", MinScale = -120, MaxScale = 120, Default = 90, },
				Input2 = InstanceInput { SourceOp = "SwingE", Source = "EaseIn", Name = "Ease In", Width = 0.5, },
				Input3 = InstanceInput { SourceOp = "SwingE", Source = "EaseOut", Name = "Ease Out", Width = 0.5, },
				Input4 = InstanceInput { SourceOp = "DipE", Source = "Scale", Name = "Midpoint Dip", MinScale = -0.5, MaxScale = 0, Default = -0.15, },
				Input5 = InstanceInput { SourceOp = "Render", Source = "MotionBlur", Name = "Motion Blur", Default = 1, },
-- TOOLS
				MaskR = RectangleMask { Inputs = { Center = Input { Value = { 0.75, 0.5 }, }, Width = Input { Value = 0.5, }, Height = Input { Value = 1, }, }, },
				MaskL = RectangleMask { Inputs = { Center = Input { Value = { 0.25, 0.5 }, }, Width = Input { Value = 0.5, }, Height = Input { Value = 1, }, }, },
				LeftLeaf = BrightnessContrast { Inputs = {
					Input = Input { SourceOp = "A_In", Source = "Output", }, Alpha = Input { Value = 1, }, Gain = Input { Value = 0, },
					EffectMask = Input { SourceOp = "MaskR", Source = "Mask", },
				}, },
				RightLeaf = BrightnessContrast { Inputs = {
					Input = Input { SourceOp = "A_In", Source = "Output", }, Alpha = Input { Value = 1, }, Gain = Input { Value = 0, },
					EffectMask = Input { SourceOp = "MaskL", Source = "Mask", },
				}, },
				DoorL = ImagePlane3D { Inputs = {
					MaterialInput = Input { SourceOp = "LeftLeaf", Source = "Output", },
					["Transform3DOp.Pivot.X"] = Input { Value = -0.5, },
					["Transform3DOp.Rotate.Y"] = Input { SourceOp = "SwingE", Source = "Value", },
				}, },
				DoorR = ImagePlane3D { Inputs = {
					MaterialInput = Input { SourceOp = "RightLeaf", Source = "Output", },
					["Transform3DOp.Pivot.X"] = Input { Value = 0.5, },
					["Transform3DOp.Rotate.Y"] = Input { Expression = "-DoorL.Transform3DOp.Rotate.Y", },
				}, },
				SwingE = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Cubic" }, }, EaseOut = Input { Value = FuID { "None" }, },
					Scale = Input { Value = 90, }, Offset = Input { Value = 0, },
				}, },
				Cam = Camera3D { Inputs = {
					FilmGate = Input { Value = FuID { "BMD_URSA_4K_16x9" }, },   -- live: a pasted Camera3D defaults to "TV" (AoV 24.33); the 2.94614 formula needs 19.26
					ApertureW = Input { Value = 0.8315, }, ApertureH = Input { Value = 0.4677, },   -- [from rebuild log, K2] FilmGate alone can leave the TV apertures
					["Transform3DOp.Translate.Z"] = Input { Expression = "2.94614*comp:GetPrefs(\"Comp.FrameFormat.Height\")/comp:GetPrefs(\"Comp.FrameFormat.Width\")", },
				}, },
				Doors = Merge3D { Inputs = {
					SceneInput1 = Input { SourceOp = "DoorL", Source = "Output", },
					SceneInput2 = Input { SourceOp = "DoorR", Source = "Output", },
					SceneInput3 = Input { SourceOp = "Cam", Source = "Output", },
				}, },
				Render = Renderer3D { Inputs = {
					SceneInput = Input { SourceOp = "Doors", Source = "Output", },
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
					MotionBlur = Input { Value = 1, }, Quality = Input { Value = 8, }, ShutterAngle = Input { Value = 180, },
				}, },
				Reveal = Merge { Inputs = {
					Background = Input { SourceOp = "B_In", Source = "Output", },
					Foreground = Input { SourceOp = "Render", Source = "Output", },
					PerformDepthMerge = Input { Value = 0, },
				}, },
				Dip = BrightnessContrast { Inputs = {
					Input = Input { SourceOp = "Reveal", Source = "Output", },
					Gain = Input { SourceOp = "DipE", Source = "Value", },
				}, },
				DipE = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Sine" }, }, EaseOut = Input { Value = FuID { "Sine" }, },
					Mirror = Input { Value = 1, }, Scale = Input { Value = -0.15, }, Offset = Input { Value = 1, },
				}, },
```
Renderer3D stays on the default Software renderer with lighting off, so leaves render at 1:1 color. Verify: frame 1 has no seam at the center line; at 9:16 the leaves meet exactly at center; no 1 px edge-on sliver on the last pre-guard frame (if there is one, set Swing to 95).

### 4.5 Card flip and cube (true 3D)

A and B are two faces of one card (or of a cube) that rotates 180 (or 90) degrees. The real camera supplies the perspective. The AE "10 % scale dip" becomes a camera pull-back on a Bell bus, which also keeps the swinging near edge inside the frame.

Depth-dip math: at rest the camera sits at d = 2.94614*H/W. At rotation theta the near edge comes 0.5*sin(theta) units closer and is cropped unless the camera is at least d + 0.5*sin(theta) away. The pull-back is therefore in absolute units: 0.25 is a ~15 % dip at 16:9 (d 1.657) but only ~5 % at 9:16 (d 5.238), where the crop barely happens. 0.5 keeps a 16:9 card fully inside at every angle.

Graph: `A_In -> CardA`; `B_In -> CardB(Rotate.Y 180)`; `-> Card(Merge3D, Rotate.Y <- FlipE)`; `Card + Cam(Z <- CamZ) -> World -> Render -> OverVoid.Foreground`; `Void -> OverVoid.Background`. `CullBackFace` 1 on both planes: Fusion does not cull back faces by default, so the departing face would otherwise show through mirrored and z-fight [manual].
```lua
-- NAME TK_CardFlip  FX_OUT OverVoid
-- INPUTS
				Input1 = InstanceInput { SourceOp = "FlipE", Source = "Scale", Name = "Rotation (deg)", MinScale = -180, MaxScale = 180, Default = 180, },
				Input2 = InstanceInput { SourceOp = "FlipE", Source = "EaseIn", Name = "Ease In", Width = 0.5, },
				Input3 = InstanceInput { SourceOp = "FlipE", Source = "EaseOut", Name = "Ease Out", Width = 0.5, },
				Input4 = InstanceInput { SourceOp = "CamZ", Source = "Scale", Name = "Depth Dip", MinScale = 0, MaxScale = 1, Default = 0.25, },
				Input5 = InstanceInput { SourceOp = "Render", Source = "MotionBlur", Name = "Motion Blur", Default = 1, },
-- TOOLS
				CardA = ImagePlane3D { Inputs = {
					MaterialInput = Input { SourceOp = "A_In", Source = "Output", },
					["SurfacePlaneInputs.Visibility.CullBackFace"] = Input { Value = 1, },
				}, },
				CardB = ImagePlane3D { Inputs = {
					MaterialInput = Input { SourceOp = "B_In", Source = "Output", },
					["Transform3DOp.Rotate.Y"] = Input { Value = 180, },
					["SurfacePlaneInputs.Visibility.CullBackFace"] = Input { Value = 1, },
				}, },
				Card = Merge3D { Inputs = {
					SceneInput1 = Input { SourceOp = "CardA", Source = "Output", },
					SceneInput2 = Input { SourceOp = "CardB", Source = "Output", },
					["Transform3DOp.Rotate.Y"] = Input { SourceOp = "FlipE", Source = "Value", },
				}, },
				FlipE = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Cubic" }, }, EaseOut = Input { Value = FuID { "Cubic" }, },
					Scale = Input { Value = 180, }, Offset = Input { Value = 0, },
				}, },
				Cam = Camera3D { Inputs = {
					FilmGate = Input { Value = FuID { "BMD_URSA_4K_16x9" }, },   -- live: pasted default is "TV" (AoV 24.33)
					ApertureW = Input { Value = 0.8315, }, ApertureH = Input { Value = 0.4677, },   -- [from rebuild log, K2] FilmGate alone can leave the TV apertures
					["Transform3DOp.Translate.Z"] = Input { SourceOp = "CamZ", Source = "Value", },
				}, },
				CamZ = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Sine" }, }, EaseOut = Input { Value = FuID { "Sine" }, },
					Mirror = Input { Value = 1, }, Scale = Input { Value = 0.25, },
					Offset = Input { Expression = "2.94614*comp:GetPrefs(\"Comp.FrameFormat.Height\")/comp:GetPrefs(\"Comp.FrameFormat.Width\")", },
				}, },
				World = Merge3D { Inputs = {
					SceneInput1 = Input { SourceOp = "Card", Source = "Output", },
					SceneInput2 = Input { SourceOp = "Cam", Source = "Output", },
				}, },
				Render = Renderer3D { Inputs = {
					SceneInput = Input { SourceOp = "World", Source = "Output", },
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
					MotionBlur = Input { Value = 1, }, Quality = Input { Value = 8, }, ShutterAngle = Input { Value = 180, },
				}, },
				Void = Background { Inputs = {
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
					TopLeftRed = Input { Value = 0, }, TopLeftGreen = Input { Value = 0, }, TopLeftBlue = Input { Value = 0, }, TopLeftAlpha = Input { Value = 1, },
				}, },
				OverVoid = Merge { Inputs = {
					Background = Input { SourceOp = "Void", Source = "Output", },
					Foreground = Input { SourceOp = "Render", Source = "Output", },
					PerformDepthMerge = Input { Value = 0, },
				}, },
```
B is not mirrored at the end: CardB's 180 plus the card's 180 = 360 = identity. Vertical flip: use `Rotate.X` on both CardB and Card.

**Cube variant** (edit the block): CardB `Translate.X` 0.5, `Translate.Z` -0.5, `Rotate.Y` 90 (instead of 180); Card `["Transform3DOp.Pivot.Z"]` -0.5; `FlipE.Scale` -90; `CamZ.Scale` 0.35 (the cube corner reaches z = +0.21 at 45 deg). The side face is 1 unit wide, so cube depth = frame width at any aspect. For a vertical-axis cube the depth is the plane height: `Translate.Y` 0.5/AR, `Translate.Z` and `Pivot.Z` -0.5/AR, rotate on X. Verify: rest frames fill the frame with no border at 16:9 and 9:16; no z-fighting at 90 deg; the Void catches all transparency.

### 4.6 Page peel

Honest status: Fusion has no 2D page-turn node (no CC Page Turn equivalent), and GridWarp cannot fake a convincing curl. The native tool is **`Bender3D`** bending a finely subdivided image plane, and Blackmagic ships exactly that as Edit/Transitions/**Page Curl** [shipped]. Start there: apply it from Video Transitions > Fusion Transitions and inspect it with Open in Fusion Page.

How the shipped build works: the clip goes onto the **camera's own image plane** (`Camera3D.ImageInput`, `IDepth` 4.6, `SurfacePlaneInputs.SubdivisionWidth` 100), which always fills the view, so no fill formula is needed. `Transform3D` rotates the rig by the curl angle (`Rotate.Z` 23.5). `Bender3D` (`Amount` -1.25, `Axis` 0, `Angle` -90, `Center` 1, `Group` 1) rolls the plane, with `RangeMax` driven by Anim Curves. A second `Transform3D` counter-rotates (`CurlAxis.Transform3DOp.Rotate.Z*-1`). A directional light and two OpenGL renders (lit and flat, merged with `ApplyMode` Lighten) shade the curl, and `Shadow` drops a shadow beneath it.

Shipped Page Curl lays the incoming B down over A (`Invert` 1). The AE-style peel (A peels away to reveal B) needs two changes: A goes on the camera plane with B under the render, and `RangeMax` runs 0 -> 1 (`Invert` 0). Spend the craft on the ease (Sine in, Cubic out) and the shadow. Boundary care: the lit render must not darken the flat rest frame, so the Lighten mix starts at `Blend` 1 (pure flat) and eases to the shading amount over the first 20 % of the move.
```lua
-- NAME TK_Peel  FX_OUT Peel
-- INPUTS
				Input1 = InstanceInput { SourceOp = "CurlAxis", Source = "Transform3DOp.Rotate.Z", Name = "Curl Angle", Default = 23.5, },
				Input2 = InstanceInput { SourceOp = "Curl", Source = "Amount", Name = "Roll Amount", Default = -1.25, },
				Input3 = InstanceInput { SourceOp = "CurlShadow", Source = "Softness", Name = "Shadow Softness", Default = 0.05, },
				Input4 = InstanceInput { SourceOp = "CurlE", Source = "EaseIn", Name = "Ease In", Width = 0.5, },
				Input5 = InstanceInput { SourceOp = "CurlE", Source = "EaseOut", Name = "Ease Out", Width = 0.5, },
-- TOOLS
				PageCam = Camera3D { Inputs = {
					ImageInput = Input { SourceOp = "A_In", Source = "Output", },
					["Transform3DOp.Translate.Z"] = Input { Value = 5, }, IDepth = Input { Value = 4.6, },
					["SurfacePlaneInputs.SubdivisionWidth"] = Input { Value = 100, },
					["MtlStdInputs.Specular.Intensity"] = Input { Value = 0, },
				}, },
				CurlAxis = Transform3D { Inputs = {
					SceneInput = Input { SourceOp = "PageCam", Source = "Output", },
					["Transform3DOp.Rotate.Z"] = Input { Value = 23.5, },
				}, },
				Curl = Bender3D { Inputs = {
					SceneInput = Input { SourceOp = "CurlAxis", Source = "Output", },
					Amount = Input { Value = -1.25, }, Axis = Input { Value = 0, }, Angle = Input { Value = -90, },
					Center = Input { Value = 1, }, Group = Input { Value = 1, },
					RangeMax = Input { SourceOp = "CurlE", Source = "Value", },
				}, },
				CurlE = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Sine" }, }, EaseOut = Input { Value = FuID { "Cubic" }, },
					Scale = Input { Value = 1, }, Offset = Input { Value = 0, }, Invert = Input { Value = 0, },
				}, },
				Uncurl = Transform3D { Inputs = {
					SceneInput = Input { SourceOp = "Curl", Source = "Output", },
					["Transform3DOp.Rotate.Z"] = Input { Expression = "CurlAxis.Transform3DOp.Rotate.Z*-1", },
				}, },
				Sun = LightDirectional { Inputs = {
					["ShadowLightInputs3D.ShadowsEnabled"] = Input { Value = 1, },
					["ShadowLightInputs3D.ShadowMapSize"] = Input { Value = 2048, },
				}, },
				PageScene = Merge3D { Inputs = {
					SceneInput1 = Input { SourceOp = "Uncurl", Source = "Output", },
					SceneInput2 = Input { SourceOp = "Sun", Source = "Output", },
				}, },
				RenderLit = Renderer3D { Inputs = {
					SceneInput = Input { SourceOp = "PageScene", Source = "Output", },
					CameraSelector = Input { Value = FuID { "PageCam" }, },
					RendererType = Input { Value = FuID { "RendererOpenGL" }, },
					["RendererOpenGL.LightingEnabled"] = Input { Value = 1, }, ["RendererOpenGL.AccumQuality"] = Input { Value = 32, },
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
				}, },
				RenderFlat = Renderer3D { Inputs = {
					SceneInput = Input { SourceOp = "PageScene", Source = "Output", },
					CameraSelector = Input { Value = FuID { "PageCam" }, },
					RendererType = Input { Value = FuID { "RendererOpenGL" }, }, ["RendererOpenGL.AccumQuality"] = Input { Value = 32, },
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
				}, },
				Shade = Merge { Inputs = {
					Background = Input { SourceOp = "RenderLit", Source = "Output", },
					Foreground = Input { SourceOp = "RenderFlat", Source = "Output", },
					ApplyMode = Input { Value = FuID { "Lighten" }, },
					Blend = Input { Expression = "1 - 0.6*min(1, CurlE.Value*5)", },    -- 0.6 = shading strength
					PerformDepthMerge = Input { Value = 0, },
				}, },
				CurlShadow = Shadow { Inputs = {
					Input = Input { SourceOp = "Shade", Source = "Output", }, Softness = Input { Value = 0.05, },
				}, },
				Peel = Merge { Inputs = {
					Background = Input { SourceOp = "B_In", Source = "Output", },
					Foreground = Input { SourceOp = "CurlShadow", Source = "Output", },
					PerformDepthMerge = Input { Value = 0, },
				}, },
```
`RendererOpenGL.*` IDs come from the shipped file (sub-inputs that are absent from the TSV until OpenGL is selected). Settle two things by render: whether the fully rolled tube has left the frame on the last pre-guard frames (if not, increase the Roll Amount magnitude), and the default light direction (if frame 1 is darker than A, lower the 0.6). This is the most expensive build here (two OpenGL renders at `AccumQuality` 32); reserve it for one chapter moment.

### 4.7 Luma / gradient wipe

B reveals through a luminance ramp: a generated gradient (linear, radial iris, angle sweep) or an editor-chosen luma clip. `Dissolve` `Operation` = `DFTLumaRamp` does this natively and is the cheapest custom-shape wipe. Five controls (the border-color row counts as one).
```lua
-- NAME TK_LumaWipe  FX_OUT Wipe
-- INPUTS
				Input1 = InstanceInput { SourceOp = "Ramp", Source = "GradientType", Name = "Shape", },
				Input2 = InstanceInput { SourceOp = "Wipe", Source = "DFTLumaRamp.Softness", Name = "Softness", Default = 0.2, },
				Input3 = InstanceInput { SourceOp = "Wipe", Source = "DFTLumaRamp.Border", Name = "Border", Default = 0, },
				Input4 = InstanceInput { SourceOp = "Wipe", Source = "DFTLumaRamp.Red", Name = "Border Color", ControlGroup = 4, Default = 1, },
				Input5 = InstanceInput { SourceOp = "Wipe", Source = "DFTLumaRamp.Green", Name = "Border Color", ControlGroup = 4, Default = 1, },
				Input6 = InstanceInput { SourceOp = "Wipe", Source = "DFTLumaRamp.Blue", Name = "Border Color", ControlGroup = 4, Default = 1, },
				Input7 = InstanceInput { SourceOp = "WipeE", Source = "EaseIn", Name = "Ease In", },
-- TOOLS
				Ramp = Background { Inputs = {
					UseFrameFormatSettings = Input { Value = 1, }, Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
					Type = Input { Value = FuID { "Gradient" }, }, GradientType = Input { Value = FuID { "Radial" }, },
					Start = Input { Value = { 0.5, 0.5 }, }, End = Input { Value = { 1, 1 }, },
					Gradient = Input { Value = Gradient { Colors = { [0] = { 0, 0, 0, 1 }, [1] = { 1, 1, 1, 1 }, }, }, },
				}, },
				Wipe = Dissolve { Transitions = { [0] = "DFTLumaRamp" }, Inputs = {
					Operation = Input { Value = FuID { "DFTLumaRamp" }, },
					Background = Input { SourceOp = "A_In", Source = "Output", },
					Foreground = Input { SourceOp = "B_In", Source = "Output", },
					Map = Input { SourceOp = "Ramp", Source = "Output", },
					Mix = Input { SourceOp = "WipeE", Source = "Value", },
					["DFTLumaRamp.Softness"] = Input { Value = 0.2, },
				}, },
				WipeE = LUTLookup { Inputs = {
					Curve = Input { Value = FuID { "Easing" }, },
					EaseIn = Input { Value = FuID { "Sine" }, }, EaseOut = Input { Value = FuID { "Sine" }, },
					Scale = Input { Value = 1, }, Offset = Input { Value = 0, },
				}, },
```
`GradientType` options [TSV]: Linear, Reflect, Square, Cross, Radial, Angle. With a radial ramp, `End` at a corner should reach white in the corners; verify, since gradient distance may be aspect-corrected. Organic: replace `Ramp` with `FastNoise` (`Detail`, `Contrast`, `XScale`) followed by `BrightnessContrast` that spreads it to 0..1. Luma clip [shipped Luma Wipe]: put a `MediaIn` named `LumaClip` inside, wire `Map <- LumaClip`, and publish `InstanceInput { SourceOp = "LumaClip", Source = "ClipName", Name = "Luma Clip", DefaultText = "" }`; the editor then drags any Media Pool clip onto it.

Softness-leak fallback: if frame 1 shows B (the softness band extending below Mix 0), build the matte yourself with `m = clamp((p*(1+s) - L)/s, 0, 1)`. It is 0 everywhere at p 0 and 1 everywhere at p 1 for any softness s. Use a `Custom` tool (`AlphaExpression`, `NumberIn1` = p, `NumberIn2` = s; expression syntax unverified), then Merge B over A through the matte.

---

