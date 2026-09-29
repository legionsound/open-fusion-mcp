<!-- setting-format.md part 3 of 3; index: setting-format.md -->
## 4. Idiom catalog (copy-ready, trimmed from shipped files)

### 4.1 Title with Follower per-character animation, auto-stretched to clip length
Trimmed from `Edit/Titles/Random Write On.setting`.
```lua
{
	Tools = ordered() {
		RandomWriteOn = GroupOperator {
			Inputs = ordered() {
				Input1 = InstanceInput { SourceOp = "Text1", Source = "StyledText", },
				Input2 = InstanceInput { SourceOp = "Text1", Source = "Font", ControlGroup = 2, },
				Input3 = InstanceInput { SourceOp = "Text1", Source = "Style", ControlGroup = 2, },
				Input4 = InstanceInput { SourceOp = "Text1", Source = "Red1Clone", Name = "Color", ControlGroup = 3, Default = 0.81, },
				Input5 = InstanceInput { SourceOp = "Text1", Source = "Green1Clone", ControlGroup = 3, Default = 0.81, },
				Input6 = InstanceInput { SourceOp = "Text1", Source = "Blue1Clone", ControlGroup = 3, Default = 0.75, },
				Input7 = InstanceInput { SourceOp = "Text1", Source = "Alpha1Clone", ControlGroup = 3, Default = 1, },
				Input8 = InstanceInput { SourceOp = "Text1", Source = "Size", Default = 0.08, },
				Input23 = InstanceInput { SourceOp = "Text1", Source = "Center", Name = "Position", },
			},
			Outputs = { MainOutput1 = InstanceOutput { SourceOp = "KeyframeStretcher1", Source = "Result", } },
			ViewInfo = GroupInfo { Pos = { 0, 0 } },
			Tools = ordered() {
				Text1 = TextPlus {
					Inputs = {
						GlobalOut = Input { Value = 119, },
						Width = Input { Value = 1920, }, Height = Input { Value = 1080, },
						UseFrameFormatSettings = Input { Value = 1, },
						Center = Input { Value = { 0.1, 0.5 }, },
						StyledText = Input { SourceOp = "Follower1", Source = "StyledText", },
						Font = Input { Value = "Open Sans", }, Style = Input { Value = "Bold", },
						Size = Input { Value = 0.0748, },
						VerticalJustificationNew = Input { Value = 3, },
						HorizontalLeftCenterRight = Input { Value = -1, },
						HorizontalJustificationNew = Input { Value = 3, },
					},
					ViewInfo = OperatorInfo { Pos = { 0, 8.75 } },
				},
				Follower1 = StyledTextFollower {
					Inputs = {
						LastCharacter = Input { Value = 200, },
						Order = Input { Value = 4, },          -- character order mode (4 = random here)
						ThisValue = Input { Value = 5, },
						Delay = Input { SourceOp = "Follower1Delay", Source = "Value", },
						Text = Input { Value = StyledText { Value = "SAMPLE TEXT" }, },
						Opacity1 = Input { SourceOp = "Follower1Opacity", Source = "Value", },
					},
				},
				Follower1Delay = BezierSpline {
					SplineColor = { Red = 32, Green = 113, Blue = 253 },
					KeyFrames = {
						[5] = { 8, RH = { 20.6666666666667, 6 }, Flags = { Linear = true } },
						[52] = { 2, LH = { 36.3333333333333, 4 }, Flags = { Linear = true } }
					}
				},
				Follower1Opacity = BezierSpline {
					SplineColor = { Red = 179, Green = 28, Blue = 244 },
					KeyFrames = {
						[5] = { 0, RH = { 5.20625, 0 }, Flags = { Linear = true } },
						[5.625] = { 0.74, LH = { 5.625, 0.41 }, RH = { 6.67, 0.74 }, Flags = { StepIn = true } },
						[12.5] = { 1, LH = { 12.5, 0.33 }, Flags = { StepIn = true } }
					}
				},
				KeyframeStretcher1 = KeyStretcher {
					Inputs = {
						Keyframes = Input { SourceOp = "Text1", Source = "Output", },
						SourceEnd = Input { Value = 119, },     -- authored length
						StretchStart = Input { Value = 80, },   -- keys before 80 play at authored speed
						StretchEnd = Input { Value = 110, },    -- keys after 110 are pinned to the clip end
					},
					ViewInfo = OperatorInfo { Pos = { 110, 8.75 } },
				}
			},
		}
	},
	ActiveTool = "RandomWriteOn"
}
```
Follower per-character channels seen animated: `Opacity1`, `SoftnessX1`/`SoftnessY1`, `CharacterAngleX`/`Y`, `CharacterSizeX`/`Y`, `CharacterShearX`, `Offset1` (via PolyPath), `Size`, `Thickness2`; options `Delay`, `DelayType` (2), `Order` (1,2,4), `SelectElement`, `Transform1 = 1`/`TransformSize`/`CharacterRotation`/`LineRotation` (enable groups).

### 4.2 PolyPath-animated Center (default when you keyframe a Point)
From `Edit/Titles/Horizontal Slide.setting` (path ends at X=0,Y=0, i.e. at `Center`).
```lua
lowerTextPath = PolyPath {
	DrawMode = "InsertAndModify",
	Inputs = {
		Center = Input { Value = { 0.5, 0.456054 }, },               -- path origin (default 0.5,0.5)
		Displacement = Input { SourceOp = "lowerTextPathDisplacement", Source = "Value", },
		PolyLine = Input {
			Value = Polyline {
				Points = {
					{ Linear = true, LockY = true, X = -0.826719576719577, Y = 0, RX = 0.275573192239859, RY = 0 },
					{ Linear = true, LockY = true, X = 0, Y = 0, LX = -0.275573192239859, LY = 0 }
				}
			},
		},
	},
},
lowerTextPathDisplacement = BezierSpline {
	SplineColor = { Red = 255, Green = 0, Blue = 255 },
	KeyFrames = {
		[0]  = { 0, RH = { 3.33333333333333, 0.166666666666666 }, Flags = { Linear = true, LockedY = true } },
		[10] = { 1, LH = { 0.499999999999996, 1 }, Flags = { LockedY = true } }       -- eased arrival
	}
},
-- consumer:  Center = Input { SourceOp = "lowerTextPath", Source = "Position", },
```

### 4.3 XYPath (independent X/Y curves)
From `Fusion/Motion Graphics/Crazy Circle.setting`.
```lua
XYPath2 = XYPath {
	ShowKeyPoints = false, DrawMode = "ModifyOnly",
	Inputs = {
		X = Input { SourceOp = "XYPath2X", Source = "Value", },
		Y = Input { SourceOp = "XYPath2Y", Source = "Value", },
	},
},
XYPath2X = BezierSpline {
	SplineColor = { Red = 255, Green = 0, Blue = 0, },
	KeyFrames = {
		[0]   = { -0.002, RH = { 40, 0.332666666666667, }, Flags = { Linear = true, Loop = true, }, },
		[120] = { 1.002,  LH = { 80, 0.667333333333333, }, Flags = { Linear = true, Loop = true, }, },
	},
},
XYPath2Y = BezierSpline { KeyFrames = { [0] = { 0.04, RH = { 40, 0.04 } }, [120] = { 0.04, LH = { 80, 0.04 } } } },
-- consumer:  Center = Input { SourceOp = "XYPath2", Source = "Value", },
```
XYPath X/Y may instead be LUTLookups (`Mosaic Edge Wipe.setting`) or expressions (`Perspective.setting`: `X = Input { Value = 0.5, Expression = "iif (DVE1.PivotX==0, 0, iif (DVE1.PivotX==1, 0.5, 1))" }`).

### 4.4 BezierSpline eased move (absolute handles)
From `Edit/Titles/Rise Fade.setting` (fade in 0-10, hold, fade out 133-141, smooth ease handles).
```lua
Follower15Opacity = BezierSpline {
	SplineColor = { Red = 179, Green = 28, Blue = 244 },
	NameSet = true,
	KeyFrames = {
		[0]   = { 0, RH = { 3.33333333333333, 0.166666666666666 }, Flags = { Linear = true } },
		[10]  = { 1, LH = { 1.4, 1 }, RH = { 51.0000000000001, 1 } },     -- flat handle = ease-in to hold
		[133] = { 1, LH = { 92, 1 }, RH = { 137.8, 1 } },
		[141] = { 0, LH = { 138.333333333333, 0 } }
	}
},
```
Ease recipe: put the handle at 1/3 of the segment's time and at the **same value** as its key for ease; put it on the straight line to the neighbor for linear (`Flags = { Linear = true }`). API equivalent (stub): `spline:SetKeyFrames(keyframes, replace)`; the table shape matches `KeyFrames` (inference).

### 4.5 Duration-relative easing with Anim Curves (the Edit-page workhorse)
From `Edit/Transitions/Fall and Bounce.setting`: Vector distance driven 0..1 over the transition, bounce ease.
```lua
Merge1 = Merge {
	Inputs = {
		Quality = Input { Value = 7, },
		Center = Input { SourceOp = "Vector1", Source = "Position", },
		PerformDepthMerge = Input { Value = 0, },
	},
	ViewInfo = OperatorInfo { Pos = { 654.8, 148.2 } },
},
Vector1 = Vector {
	Inputs = {
		Distance = Input { SourceOp = "AnimCurves2", Source = "Value", },
		Angle = Input { Value = 90, },
		ImageAspect = Input { Value = 1.777778, },
	},
},
AnimCurves2 = LUTLookup {
	Inputs = {
		Curve = Input { Value = FuID { "Easing" }, },
		EaseOut = Input { Value = FuID { "Bounce" }, },
		Lookup = Input { SourceOp = "AnimCurves2Lookup", Source = "Value", },
		Invert = Input { Value = 1, },
	},
},
AnimCurves2Lookup = LUTBezier {
	KeyColorSplines = { [0] = {
		[0] = { 0, RH = { 0.333333333333333, 0.333333333333333 }, Flags = { Linear = true } },
		[1] = { 1, LH = { 0.666666666666667, 0.666666666666667 }, Flags = { Linear = true } }
	} },
	SplineColor = { Red = 255, Green = 255, Blue = 255 },
}
```
Title/generator form adds `Source = Input { Value = FuID { "Duration" }, }` plus `Scale`, `Offset`, `TimeScale`, `TimeOffset`, `Mirror` (e.g. `Polka Dots.setting`: `Offset = 0.05, TimeScale = 4, Scale = 0.399`).

### 4.6 Expression-linked controls
```lua
-- auto-fit box to rendered text bounds (Edit/Titles/Text Box.setting)
Width  = Input { Value = 0.4089, Expression = "(Text1.Output[0].DataWindow[3]-Text1.Output[0].DataWindow[1])/Text1.Output[0].Width+.1", },
Height = Input { Value = 0.1861, Expression = "(Text1.Output[0].DataWindow[4]-Text1.Output[0].DataWindow[2])/Text1.Output[0].Height+.1", },
-- continuous rotation from a published speed (Fusion/Backgrounds/Optics.setting)
Angle = Input { Expression = "time*MainBG.Speed", },
-- Center from numbers (Edit/Transitions/Slice Push.setting)
Center = Input { Expression = "Point(XSize*0.5, 0.5)", },
-- transition progress with elastic easing (Templates/Edit/Transitions/MrAT-ZoomShake.setting, abbreviated)
Angle = Input { Expression = "iif((time/comp.RenderEnd < 0.5), -((2 ^ (20 * (time/comp.RenderEnd) - 10)) * sin((20 * (time/comp.RenderEnd) - 11.125) * ((2 * pi) / 4.5))) /2, ...) * 360", },
-- 3D sub-input link (Edit/Transitions/Page Curl.setting)
["Transform3DOp.Rotate.Z"] = Input { Expression = "Transform3D2.Transform3DOp.Rotate.Z*-1", },
```

### 4.7 Macro with published controls, custom sliders and buttons
Condensed from `Edit/Titles/Fade On.setting` (Calculation to publish a multiplier) and `Edit/Effects/Repeat.setting` (buttons).
```lua
FadeOn = GroupOperator {
	Inputs = ordered() {
		Input1 = InstanceInput { SourceOp = "Text1", Source = "StyledText", },
		Input19 = InstanceInput { SourceOp = "Calculation1", Source = "SecondOperand", Name = "Tracking", MinScale = 0.5, MaxScale = 1.5, Default = 1, },
		Input18 = InstanceInput { SourceOp = "Text1", Source = "Center", Name = "Position", },
	},
	Outputs = { MainOutput1 = InstanceOutput { SourceOp = "Blur1", Source = "Output", } },
	ViewInfo = GroupInfo { Pos = { 0, 0 } },
	Tools = ordered() {
		Text1 = TextPlus { Inputs = {
			CharacterSpacing = Input { SourceOp = "Calculation1", Source = "Result", },
			StyledText = Input { Value = StyledText { Value = "SAMPLE TEXT" }, },
			Size = Input { Value = 0.0709, },
		}, ViewInfo = OperatorInfo { Pos = { 275, 49.5 } }, },
		Calculation1 = Calculation { Inputs = {
			FirstOperand = Input { SourceOp = "AnimCurves1", Source = "Value", },
			Operator = Input { Value = 2, },             -- 2 used as multiply here (inference from context)
			SecondOperand = Input { Value = 1, },
		}, },
		AnimCurves1 = LUTLookup { Inputs = {
			Source = Input { Value = FuID { "Duration" }, },
			Lookup = Input { SourceOp = "AnimCurves1Lookup", Source = "Value", },
			Scale = Input { Value = 0.2, }, Offset = Input { Value = 1.2, },
		}, },
		AnimCurves1Lookup = LUTBezier { KeyColorSplines = { [0] = {
			[0] = { 0, RH = { 0.333, 0.333 }, Flags = { Linear = true } },
			[1] = { 1, LH = { 0.667, 0.667 }, Flags = { Linear = true } } } },
			SplineColor = { Red = 255, Green = 255, Blue = 255 }, },
		Blur1 = Blur { Inputs = {
			Filter = Input { Value = FuID { "Fast Gaussian" }, },
			Input = Input { SourceOp = "Text1", Source = "Output", },
		}, ViewInfo = OperatorInfo { Pos = { 0, 16.5 } }, },
	},
}
-- a button on an inner tool that drives the macro's own published inputs (Repeat.setting):
UserControls = ordered() {
	Square = { INPID_InputControl = "ButtonControl", LINKID_DataType = "Number", ICD_Width = 0.4, INP_External = false,
	           BTNCS_Execute = "tool:SetInput('Input20',0)\n tool:SetInput('Input18',0.283)\n tool:SetInput('Input19',0.5)",
	           LINKS_Name = "Square", },
}
```

### 4.8 Transition template skeleton
Verbatim `Edit/Transitions/Cross Dissolve.setting` (the whole file, 898 bytes):
```lua
{
	Tools = ordered() {
		CrossDissolve = GroupOperator {
			Inputs = ordered() {
				MainInput1 = InstanceInput { SourceOp = "Dissolve1", Source = "Background", },
				MainInput2 = InstanceInput { SourceOp = "Dissolve1", Source = "Foreground", },
			},
			Outputs = { MainOutput1 = InstanceOutput { SourceOp = "Dissolve1", Source = "Output", } },
			ViewInfo = GroupInfo { Pos = { 0, 0 } },
			Tools = ordered() {
				Dissolve1 = Dissolve {
					Transitions = { [0] = "DFTDissolve" },
					CtrlWZoom = false,
					Inputs = { Mix = Input { SourceOp = "AnimCurves1", Source = "Value", }, },
					ViewInfo = OperatorInfo { Pos = { 613.333, 166.667 } },
				},
				AnimCurves1 = LUTLookup { CtrlWZoom = false, }     -- all defaults: 0..1 over the transition
			},
		}
	},
	ActiveTool = "CrossDissolve"
}
```
Luma-wipe variant (`Luma Wipe.setting`): `Dissolve1` with `Transitions = { [0] = "DFTLumaRamp" }`, `Operation = FuID { "DFTLumaRamp" }`, `Map <- MediaIn3.Output`, and `InstanceInput { SourceOp = "MediaIn3", Source = "ClipName", Name = "Luma Clip", DefaultText = "" }`. Push/slide variant: `MainInput2 -> Instance_BG.Input` (instanced Transform) with `Vector -> Transform.Center`.

### 4.9 Wiggle: Shake and Perturb
```lua
-- Shake (Edit/Generators/Vintage Texture.setting): position jitter, published as an extra output
Shake1 = Shake { Faster = true, Inputs = {
	Smoothness = Input { Value = 1.38, },
	XMinimum = Input { Value = -0.01, }, XMaximum = Input { Value = 0.01, },
}, },
-- consumers:  Center = Input { SourceOp = "Shake1", Source = "Position", },   Blend = Input { SourceOp = "Shake1_1", Source = "X", },
-- PerturbNumber (Edit/Effects/Hologram Glitch.setting)
Perturb1_1 = PerturbNumber { Inputs = {
	RandomSeed = Input { Value = 10676, }, Strength = Input { Value = 0.79, },
	Wobble = Input { Value = 10, }, Speed = Input { Value = 10, },
}, },
-- consumer:  Gamma = Input { SourceOp = "Perturb1_1", Source = "Value", },
-- PerturbPoint: Inputs Value (base point), XScale, YScale, Strength, Wobble, Speed, RandomSeed; consumer Center <- "Value"
```

### 4.10 Duplicate and shape grids
```lua
-- Fuse.Duplicate stepped by an XYPath (Edit/Effects/Repeat.setting)
Duplicate1_1 = Fuse.Duplicate { Inputs = {
	Copies = Input { Value = 6, },
	Center = Input { SourceOp = "XYPath1", Source = "Value", },    -- per-copy offset target
	Background = Input { SourceOp = "Merge1_2", Source = "Output", },
}, ViewInfo = OperatorInfo { Pos = { 170, 57.6 } }, },
XYPath1 = XYPath { ShowKeyPoints = false, DrawMode = "ModifyOnly",
	Inputs = { X = Input { Value = 0.5, }, Y = Input { Value = 0.4, }, }, },
-- sDuplicate radial copies of a shape, rendered as a mask (Edit/Generators/Polka Dots.setting)
sDuplicate1 = sDuplicate { Inputs = {
	Copies = Input { Value = 3, }, AxisMode = Input { Value = FuID { "Absolute" }, },
	ZRotation = Input { Value = 90, }, Polyline = Input { Value = Polyline { }, },
	Input = Input { SourceOp = "sEllipse1_1", Source = "Output", },
}, },
sRender2 = sRender { Inputs = {
	Width = Input { Value = 1080, }, Height = Input { Value = 1080, },
	Input = Input { SourceOp = "sDuplicate1", Source = "Output", },
}, },
Dot = Background { Inputs = { EffectMask = Input { SourceOp = "sRender2", Source = "Output", }, TopLeftRed = Input { Value = 0.89, }, }, },
-- sGrid of text (Edit/Titles/Barrel.setting)
sGrid1 = sGrid { Inputs = {
	CellsX = Input { Value = 10, }, CellsY = Input { Value = 20, },
	XOffset = Input { Value = 0.196, }, YOffset = Input { Value = 0.05, },
	Input = Input { SourceOp = "sText1", Source = "Output", },
}, },
```

### 4.11 Expression modifier combining two Shakes (Fusion/Tools/Advanced Camera Shake.setting)
```lua
Expression_1 = Expression { Inputs = {
	p1 = Input { SourceOp = "Shake1_1", Source = "Position", },
	n1 = Input { Value = 0.5, },
	n2 = Input { SourceOp = "Shake2_1", Source = "X", },
	PointExpressionX = Input { Value = "p1x*n1*n2+p2x", },
	PointExpressionY = Input { Value = "p1y*n1*n2*n3*n4+p2y", },
	NameforNumber1 = Input { Value = "Magnitude", },
}, },
-- consumer:  Center = Input { SourceOp = "Expression_1", Source = "PointResult", },
```

### 4.12 Word-animated subtitle (21.x)
See 1.12. Minimum: a `GroupOperator` whose `CustomData.HighlightStyle` holds `{ { Time = 0, ... }, { Time = 1, ... } }`, containing a `TextPlus` named `Template` with UserControls `StyledText` (read-only TextEdit), `Words`, `WriteOn`, `Speaker`, `Speed` whose `INPS_ExecuteOnChange = "tool:UpdateWordAnimation()"` (`Subtitles/Animated/Slide In.setting`).

---

## 5. Gotchas

1. **Registry ID, not UI name**: `TextPlus` (Text+), `BetterResize` (Resize), `PolylineMask` (Polygon), `ChannelBoolean` (Channel Booleans), `LUTLookup` (Anim Curves), `StyledTextFollower` (Follower), `PolyPath` (Path), `Custom` (Custom Tool), `Mandel`, `Note` (Sticky Note), `Fuse.Duplicate`, `LightProjector` (Projector 3D), `CleanPLate` (odd casing is real).
2. **Points never take a BezierSpline**: Transform/Merge/TextPlus `Center` is animated through `PolyPath`, `XYPath`, `Vector`, `Shake`, `PerturbPoint`, `Expression` or `Publish*` (0 direct BezierSplines on Transform.Center across 182 uses). Numbers use BezierSpline or LUTLookup.
3. **BezierSpline handles are absolute `{frame, value}`; LUTBezier handles are absolute in 0..1**. Copying a curve to a different frame range means rewriting handles too. Frame keys can be fractional or negative.
4. **Polyline points are relative to the tool's Center** (-0.5..0.5 around 0), handles relative to their point; published `PointN` inputs are absolute 0..1. PolyPath positions = PolyPath `Center` + point.
5. **Image input names vary**: Merge uses `Background`/`Foreground`, most filters `Input`, OFX tools `Source`, BitmapMask `Image`, 3D `SceneInput`, masks output `Mask` not `Output`, materials output `MaterialOutput`, Replicate3D outputs `Data3D`, Calculation/KeyStretcher output `Result`, Shake outputs `X`/`Y`/`Position`, PolyPath/Vector output `Position` while XYPath outputs `Value`.
6. **Dotted input IDs need bracket keys** in Lua text (`["Transform3DOp.Translate.X"]`, `["Gamut.SLogVersion"]`, `["Layer1.Foreground"]`) but are plain strings in `SetInput("Transform3DOp.Translate.X", 1)`.
7. **Gradients** store RGBA per 0..1 key in `Gradient { Colors = { [pos] = { r, g, b, a } } }`; the key position is the table key, not an element.
8. **FuID vs Number enums**: some menus are FuIDs (`Merge.ApplyMode`, `Blur.Filter`, `Background.Type`, `LUTLookup.EaseIn`), others are plain numbers (`Transform.Edges`, `ChannelBoolean.Operation`, `ElementShapeN`, `FastNoise.GradientType`). Writing a string where a Number is expected, or a number where a FuID is expected, silently fails (inference).
9. **Default-omission**: an absent `ApplyMode`/`Operator`/`Type` means the default (Normal/Over/Solid); built-ins nearly always write `PerformDepthMerge = 0` and `Gamut.SLogVersion = FuID { "SLog2" }` (harmless boilerplate from the save).
10. **LUTLookup `Source`** decides timing: `Duration` = 0..1 over the clip (titles/generators/effects), `Transition` or omitted = over the transition, `Custom` = read `Input`. Keyframe-based templates instead wrap the last node in `KeyStretcher` (`Keyframes` input, `SourceEnd` = authored length).
11. **Transitions**: `MainInput1` = outgoing/A (Background), `MainInput2` = incoming/B (Foreground); both are required and must exist as InstanceInputs; the output must be `MainOutput1`. Effects need only `MainInput1`; titles and generators have no image input.
12. **Resolution**: set `UseFrameFormatSettings = 1` on generators (Background, TextPlus, FastNoise, sRender, masks) or templates render at the authored 1920x1080 in UHD timelines (inference; universal practice in built-ins).
13. **Modifiers/splines may live outside the group**; `SourceOp` resolves by name across the file. Keep names unique file-wide.
14. **ColorCurves hides its curves** in a nested `Tools = { ColorCurves1Red = LUTBezier {...} }` inside the tool; copying only `Inputs` loses them.
15. **Loader media is tool-level `Clips`**, not an Input; use `Setting:` relative paths for bundled assets; a `.drfx` must keep the relative layout.
16. **UserControls can override built-in inputs** (re-range sliders, change control type) and their values live in the same `Inputs` table; `INP_External = false` hides the node-input port.
17. **Button scripts** (`BTNCS_Execute`) run with `tool` = the owning node; inside a macro they address the macro's published IDs (`Input20`), so renumbering InstanceInputs breaks buttons.
18. **OFX ID casing**: registry keys are CamelCase (`...resolvefx.RadialBlur`), but shipped templates also use lowercase (`...resolvefx.radialblur`, `...mosaicblur`, `...dropshadow`, 29+ tools) (inference: lookup is case-insensitive). Author with the registry spelling.
19. **Missing tools load anyway**: built-in Shaders reference `Fuse.RealFastNoiseFuse`, not in the 21.1 registry. Check the registry (`fusion:GetRegList(typemask)`, `GetRegAttrs(id)`) before relying on a Fuse.
20. **`ActiveTool` is not validated** and `Tools` order is only UI order; the macro wrapper name is the Edit-page item's identity, the file name is its display name.
21. **Instance tools** list only deinstanced inputs; editing the original propagates. `Instance_` prefix is a naming habit, the `SourceOp` at tool level is what makes it an instance.
22. **Text in TextPlus when a Follower is attached** lives in the Follower's `Text` input; setting `TextPlus.StyledText` does nothing while it is connected.
23. **`GlobalOut` authored on generators** (e.g. 119) defines the valid range; built-ins that must not end use `GlobalIn = -1000`, `GlobalOut = 20000`.

## 6. Scripting hooks that map to this format (21.1 API stub)
- `comp:AddTool(id, defsettings, xpos, ypos, autoconnect, automerge)` uses the registry ID from section 2; `comp:AddSettingAction(filename, xpos, ypos)` "Adds a .settings to the comp".
- `comp:Paste(settings_table)`, `comp:CopySettings([tool|toollist])` -> table in this exact format; `fusion:GetClipboard()` returns "tables and ASCII text", `fusion:SetClipboard(table|text)`.
- `tool:SaveSettings(filename|customdata)` / `tool:LoadSettings(filename|table)`; `tool:SetCurrentSettings(index)` (the `CurrentSettings` key).
- `tool:SetInput(id, value, time)` / `GetInput(id, time)`; `tool:ConnectInput(input, target)`; `input:ConnectTo(output)`; `input:SetExpression(str)`/`GetExpression()`; `input:GetKeyFrames()`.
- `tool:AddModifier(input, modifier_regid)` e.g. `AddModifier("Center", "XYPath")`; for numbers `AddModifier("Size", "BezierSpline")` (common practice, inference) then set keys on the returned spline.
- `BezierSpline:SetKeyFrames(table, replace)`, `GetKeyFrames()`, `AdjustKeyFrames(start, end, x, y, operation, pivotx, pivoty)`, `DeleteKeyFrames(start, end)`.
- `PolylineMask:ConvertToBezier()`, `ConvertToBSpline()`, `GetBezierPolyline(time, which)`.
- `TextPlus/Text3D/sText:UpdateWordAnimation([style_table])` for HighlightStyle subtitles.
- `MediaIn:GetMarkers()`, `SetMarker(timestamp, data)`.
