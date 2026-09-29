<!-- design-first.md part 2 of 3; index: design-first.md -->
## 4. Copy-ready template: SaaS hero frame

status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0, 6, 12, 18, 24, 32, 48 at 3840x2160). Pasted as typed; all 19 `WIRES` correct; all 7 `PROBES` within 0.01 (Card_Xf Size f8 0.9926, CTA Size f22 1.01931 peak, Subline Blend f14 0.42178, AnimMove f2 0.53424); `Card_Xf.Center` f4 = (0.5, 0.47); settled-frame pixels card 1E2640, CTA 4F5BD5 exact, bg 151B32 vs 161C33 (1 level). Visual: card rises and fades from f4, headline writes on per character with the Y settle, subline then pill CTA pop, settled by f32. **One naming surprise:** the three master splines keyed on UserControls were renamed on paste to `Ctrl_MainCurveMovekeyed`, `Ctrl_MainCurveFadekeyed`, `Ctrl_MainCurvePopkeyed` (host name + the control's `LINKS_Name` without spaces/punctuation); everything still worked because consumers read `Ctrl_Main.AnimMove`, never the spline name. Semantics still open are listed in §13.

### 4.1 Spec -> normalized values (1920x1080 reference)

| Node | Spec (px, top-left origin) | Fusion values |
|---|---|---|
| `BG_Base` | vertical gradient #161C33 (top) -> #0B0E1A | `Start` {0.5,1}, `End` {0.5,0}; stops {0.0863,0.1098,0.2} / {0.0431,0.0549,0.102} |
| `BG_Glow` | radial accent glow at (960, 410), radius ~0.45 W, Screen | `Start` {0.5,0.62}, `End` {0.95,0.62} |
| `Card_BG_Mask` | box 400,310, 1120x460, r 28 | `Center` {0.5,0.5}, `Width` 0.583333, `Height` 0.425926, `CornerRadius` 0.121739 |
| `Card_Headline` | center (960,455), 56 px Open Sans Bold, #F2F4FA | `Center` {0.5,0.578704}, `Size` 0.0496 |
| `Card_Subline` | center (960,520), 28 px Regular, #A7AFC4 | `Center` {0.5,0.518519}, `Size` 0.0248 |
| `Card_CTA_Mask` | box 800,579, 320x72, pill | `Center` {0.5,0.430556}, `Width` 0.166667, `Height` 0.066667, `CornerRadius` 1 |
| `Card_CTA_Label` | 24 px Bold, white | `Size` 0.02125, same `Center` |
| Accent #4F5BD5 | HSL S 61 %, L 57 % (muted, in range) | {0.3098, 0.3569, 0.8353} |
| Card #1E2640 / Ink #F2F4FA | | {0.1176, 0.149, 0.251} / {0.949, 0.9569, 0.9804} |

Contrast: subline on card ~6.8:1, white on accent ~5.7:1 (both above 4.5:1).

### 4.2 Graph

```
BG_Base -> BG_Glow_Mrg.Background        BG_Glow -> BG_Glow_Mrg.Foreground (Screen, drifting Center)
BG_Glow_Mrg -> Card_Mrg.Background -> [Python] MediaOut1.Input, QA_Saver.Input
Card_BG_Mask -> Card_BG.EffectMask
Card_BG -> Card_Shadow -> Card_Headline_Mrg.Background -> Card_Subline_Mrg.Background
        -> Card_CTA_Mrg.Background -> Card_Xf -> Card_Mrg.Foreground
Card_Headline_Flw -> Card_Headline.StyledText;  Card_Headline -> Card_Headline_Mrg.Foreground
Card_Subline -> Card_Subline_Mrg.Foreground
Card_CTA_Mask -> Card_CTA_BG.EffectMask
Card_CTA_BG -> Card_CTA_Label_Mrg.Background;  Card_CTA_Label -> Card_CTA_Label_Mrg.Foreground
Card_CTA_Label_Mrg -> Card_CTA_Xf -> Card_CTA_Mrg.Foreground
Ctrl_Main (unconnected): colors + AnimStart/AnimStagger/AnimRise + master curves AnimMove/AnimFade/AnimPop
```

### 4.3 Timing sheet (24 fps)

| Unit | k | Start f | Motion | Settled by |
|---|---|---|---|---|
| Card (plate, shadow, children) | 0 | 4 | rise 0.03 H + Size 0.96 -> 1 (Move 14 f), Blend (Fade 6 f) | 18 |
| Headline characters | 2 | 10 | Follower Opacity1 (fade 6 f) + CharacterOffset Y -0.02 -> 0 (decel 10 f), Delay 0.5 f/char, 27 chars | ~33 |
| Subline | 3 | 13 | rise 0.6 x Rise (Move), Blend (Fade) | 27 |
| CTA | 4 | 16 | Size 0.8 -> 1 (Pop 10 f, peak 1.019 near f 21-22), Blend (Fade) | 26 |
| BG glow | - | always | Center drift, 6 s loop (`time/24`; use `/30` at 30 fps) | - |

QA frames: 18 (mid-entrance, never 0) and 48 (settled). **30 fps variant:** `AnimStart` 5, `AnimStagger` 4, swap the three master curves for the 30 fps rows in §3.6, headline keys Opacity1 `[13]={0,RH={15.64,1}}, [21]={1,LH={18.44,1}}` and OffsetY `[13]={-0.02,RH={15.64,0}}, [25]={0,LH={17.32,0}}`, Delay 0.6, glow `time/30`.

### 4.4 `saas_hero.setting`

`__QA_OUT__` is replaced by the Python in §5. Delete `QA_Saver` before saving as a template or delivering.

```lua
{
	Tools = ordered() {
		Ctrl_Main = Background {
			NameSet = true,
			Colors = { TileColor = { R = 0.92, G = 0.56, B = 0.25 }, },
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				AnimStart = Input { Value = 4, },
				AnimStagger = Input { Value = 3, },
				AnimRise = Input { Value = 0.03, },
				AnimMove = Input { SourceOp = "Ctrl_MainAnimMove", Source = "Value", },
				AnimFade = Input { SourceOp = "Ctrl_MainAnimFade", Source = "Value", },
				AnimPop = Input { SourceOp = "Ctrl_MainAnimPop", Source = "Value", },
				AccentRed = Input { Value = 0.3098, },
				AccentGreen = Input { Value = 0.3569, },
				AccentBlue = Input { Value = 0.8353, },
				InkRed = Input { Value = 0.949, },
				InkGreen = Input { Value = 0.9569, },
				InkBlue = Input { Value = 0.9804, },
				CardRed = Input { Value = 0.1176, },
				CardGreen = Input { Value = 0.149, },
				CardBlue = Input { Value = 0.251, },
			},
			ViewInfo = OperatorInfo { Pos = { -165, -66 } },
			UserControls = ordered() {
				AnimStart = { LINKS_Name = "Entrance Start (frames)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 4, INP_MinScale = 0, INP_MaxScale = 48, ICS_ControlPage = "Controls", },
				AnimStagger = { LINKS_Name = "Unit Stagger (frames)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 3, INP_MinScale = 0, INP_MaxScale = 12, ICS_ControlPage = "Controls", },
				AnimRise = { LINKS_Name = "Rise (fraction of height)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0.03, INP_MinScale = 0, INP_MaxScale = 0.1, ICS_ControlPage = "Controls", },
				AnimMove = { LINKS_Name = "Curve Move (keyed)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 1, ICS_ControlPage = "Controls", },
				AnimFade = { LINKS_Name = "Curve Fade (keyed)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 1, ICS_ControlPage = "Controls", },
				AnimPop = { LINKS_Name = "Curve Pop (keyed)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 1.2, ICS_ControlPage = "Controls", },
				Accent = { LINKS_Name = "Accent", LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = -1, INP_Default = 0, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				AccentRed = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = 0, INP_Default = 0.3098, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				AccentGreen = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = 1, INP_Default = 0.3569, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				AccentBlue = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = 2, INP_Default = 0.8353, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				Ink = { LINKS_Name = "Ink (headline)", LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 2, IC_ControlID = -1, INP_Default = 0, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				InkRed = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 2, IC_ControlID = 0, INP_Default = 0.949, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				InkGreen = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 2, IC_ControlID = 1, INP_Default = 0.9569, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				InkBlue = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 2, IC_ControlID = 2, INP_Default = 0.9804, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				Card = { LINKS_Name = "Card Surface", LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 3, IC_ControlID = -1, INP_Default = 0, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				CardRed = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 3, IC_ControlID = 0, INP_Default = 0.1176, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				CardGreen = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 3, IC_ControlID = 1, INP_Default = 0.149, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
				CardBlue = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 3, IC_ControlID = 2, INP_Default = 0.251, CLRC_ShowWheel = false, ICS_ControlPage = "Controls", },
			},
		},
		Ctrl_MainAnimMove = BezierSpline {
			SplineColor = { Red = 240, Green = 140, Blue = 60, },
			NameSet = true,
			KeyFrames = {
				[0] = { 0, RH = { 3.08, 1, }, },
				[14] = { 1, LH = { 5.04, 1, }, },
			},
		},
		Ctrl_MainAnimFade = BezierSpline {
			SplineColor = { Red = 179, Green = 28, Blue = 244, },
			NameSet = true,
			KeyFrames = {
				[0] = { 0, RH = { 1.98, 1, }, },
				[6] = { 1, LH = { 4.08, 1, }, },
			},
		},
		Ctrl_MainAnimPop = BezierSpline {
			SplineColor = { Red = 60, Green = 200, Blue = 120, },
			NameSet = true,
			KeyFrames = {
				[0] = { 0, RH = { 3.4, 1.56, }, },
				[10] = { 1, LH = { 6.4, 1, }, },
			},
		},
		BG_Base = Background {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				Type = Input { Value = FuID { "Gradient" }, },
				Start = Input { Value = { 0.5, 1 }, },
				End = Input { Value = { 0.5, 0 }, },
				Gradient = Input {
					Value = Gradient {
						Colors = {
							[0] = { 0.0863, 0.1098, 0.2, 1 },
							[1] = { 0.0431, 0.0549, 0.102, 1 },
						},
					},
				},
			},
			ViewInfo = OperatorInfo { Pos = { 0, 0 } },
		},
		BG_Glow = Background {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				Type = Input { Value = FuID { "Gradient" }, },
				GradientType = Input { Value = FuID { "Radial" }, },
				Start = Input { Value = { 0.5, 0.62 }, },
				End = Input { Value = { 0.95, 0.62 }, },
				Gradient = Input {
					Value = Gradient {
						Colors = {
							[0] = { 0.1084, 0.1249, 0.2924, 1 },
							[0.45] = { 0.0372, 0.0428, 0.1002, 1 },
							[1] = { 0, 0, 0, 1 },
						},
					},
				},
			},
			ViewInfo = OperatorInfo { Pos = { 110, 49.5 } },
		},
		BG_Glow_Mrg = Merge {
			NameSet = true,
			Inputs = {
				Background = Input { SourceOp = "BG_Base", Source = "Output", },
				Foreground = Input { SourceOp = "BG_Glow", Source = "Output", },
				ApplyMode = Input { Value = FuID { "Screen" }, },
				Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(0.5 + 0.015*sin(time/24*2*pi/6), 0.5 + 0.01*cos(time/24*2*pi/6))", },
				PerformDepthMerge = Input { Value = 0, },
			},
			ViewInfo = OperatorInfo { Pos = { 110, 0 } },
		},
		Card_BG_Mask = RectangleMask {
			NameSet = true,
			Inputs = {
				Center = Input { Value = { 0.5, 0.5 }, },
				Width = Input { Value = 0.583333, },
				Height = Input { Value = 0.425926, },
				CornerRadius = Input { Value = 0.121739, },
			},
			ViewInfo = OperatorInfo { Pos = { 0, 115.5 } },
		},
		Card_BG = Background {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				TopLeftRed = Input { Value = 0.1176, Expression = "Ctrl_Main.CardRed", },
				TopLeftGreen = Input { Value = 0.149, Expression = "Ctrl_Main.CardGreen", },
				TopLeftBlue = Input { Value = 0.251, Expression = "Ctrl_Main.CardBlue", },
				TopLeftAlpha = Input { Value = 1, },
				EffectMask = Input { SourceOp = "Card_BG_Mask", Source = "Mask", },
			},
			ViewInfo = OperatorInfo { Pos = { 110, 115.5 } },
		},
		Card_Shadow = Shadow {
			NameSet = true,
			Inputs = {
				Input = Input { SourceOp = "Card_BG", Source = "Output", },
				ShadowOffset = Input { Value = { 0.5, 0.4926 }, },
				Softness = Input { Value = 0.02, },
				Alpha = Input { Value = 0.45, },
			},
			ViewInfo = OperatorInfo { Pos = { 220, 115.5 } },
		},
		Card_Headline_Flw = StyledTextFollower {
			NameSet = true,
			Inputs = {
				Text = Input { Value = StyledText { Value = "Ship your launch in minutes", }, },
				LastCharacter = Input { Value = 200, },
				Delay = Input { Value = 0.5, },
				Opacity1 = Input { SourceOp = "Card_Headline_FlwOpacity1", Source = "Value", },
				CharacterOffset = Input { SourceOp = "Card_Headline_FlwOffset", Source = "Value", },
			},
		},
		Card_Headline_FlwOpacity1 = BezierSpline {
			SplineColor = { Red = 179, Green = 28, Blue = 244, },
			KeyFrames = {
				[10] = { 0, RH = { 11.98, 1, }, },
				[16] = { 1, LH = { 14.08, 1, }, },
			},
		},
		Card_Headline_FlwOffset = XYPath {
			ShowKeyPoints = false,
			DrawMode = "ModifyOnly",
			Inputs = {
				X = Input { Value = 0, },
				Y = Input { SourceOp = "Card_Headline_FlwOffsetY", Source = "Value", },
			},
		},
		Card_Headline_FlwOffsetY = BezierSpline {
			SplineColor = { Red = 0, Green = 200, Blue = 255, },
			KeyFrames = {
				[10] = { -0.02, RH = { 12.2, 0, }, },
				[20] = { 0, LH = { 13.6, 0, }, },
			},
		},
		Card_Headline = TextPlus {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				StyledText = Input { SourceOp = "Card_Headline_Flw", Source = "StyledText", },
				Font = Input { Value = "Open Sans", },
				Style = Input { Value = "Bold", },
				Size = Input { Value = 0.0496, },
				CharacterSpacing = Input { Value = 0.98, },
				Center = Input { Value = { 0.5, 0.578704 }, },
				Red1 = Input { Value = 0.949, Expression = "Ctrl_Main.InkRed", },
				Green1 = Input { Value = 0.9569, Expression = "Ctrl_Main.InkGreen", },
				Blue1 = Input { Value = 0.9804, Expression = "Ctrl_Main.InkBlue", },
			},
			ViewInfo = OperatorInfo { Pos = { 330, 165 } },
		},
		Card_Headline_Mrg = Merge {
			NameSet = true,
			Inputs = {
				Background = Input { SourceOp = "Card_Shadow", Source = "Output", },
				Foreground = Input { SourceOp = "Card_Headline", Source = "Output", },
				PerformDepthMerge = Input { Value = 0, },
			},
			ViewInfo = OperatorInfo { Pos = { 330, 115.5 } },
		},
		Card_Subline = TextPlus {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				StyledText = Input { Value = "Automations, analytics and approvals in one place.", },
				Font = Input { Value = "Open Sans", },
				Style = Input { Value = "Regular", },
				Size = Input { Value = 0.0248, },
				Center = Input { Value = { 0.5, 0.518519 }, },
				Red1 = Input { Value = 0.6549, },
				Green1 = Input { Value = 0.6863, },
				Blue1 = Input { Value = 0.7686, },
			},
			ViewInfo = OperatorInfo { Pos = { 440, 165 } },
		},
		Card_Subline_Mrg = Merge {
			NameSet = true,
			Inputs = {
				Background = Input { SourceOp = "Card_Headline_Mrg", Source = "Output", },
				Foreground = Input { SourceOp = "Card_Subline", Source = "Output", },
				Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(0.5, 0.5 - 0.6*Ctrl_Main.AnimRise*(1 - Ctrl_Main:GetValue('AnimMove', time - (Ctrl_Main.AnimStart + 3*Ctrl_Main.AnimStagger))))", },
				Blend = Input { Value = 1, Expression = "Ctrl_Main:GetValue('AnimFade', time - (Ctrl_Main.AnimStart + 3*Ctrl_Main.AnimStagger))", },
				PerformDepthMerge = Input { Value = 0, },
			},
			ViewInfo = OperatorInfo { Pos = { 440, 115.5 } },
		},
		Card_CTA_Mask = RectangleMask {
			NameSet = true,
			Inputs = {
				Center = Input { Value = { 0.5, 0.430556 }, },
				Width = Input { Value = 0.166667, },
				Height = Input { Value = 0.066667, },
				CornerRadius = Input { Value = 1, },
			},
			ViewInfo = OperatorInfo { Pos = { 220, 231 } },
		},
		Card_CTA_BG = Background {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				TopLeftRed = Input { Value = 0.3098, Expression = "Ctrl_Main.AccentRed", },
				TopLeftGreen = Input { Value = 0.3569, Expression = "Ctrl_Main.AccentGreen", },
				TopLeftBlue = Input { Value = 0.8353, Expression = "Ctrl_Main.AccentBlue", },
				TopLeftAlpha = Input { Value = 1, },
				EffectMask = Input { SourceOp = "Card_CTA_Mask", Source = "Mask", },
			},
			ViewInfo = OperatorInfo { Pos = { 330, 231 } },
		},
		Card_CTA_Label = TextPlus {
			NameSet = true,
			Inputs = {
				UseFrameFormatSettings = Input { Value = 1, },
				StyledText = Input { Value = "Start free trial", },
				Font = Input { Value = "Open Sans", },
				Style = Input { Value = "Bold", },
				Size = Input { Value = 0.02125, },
				CharacterSpacing = Input { Value = 1.02, },
				Center = Input { Value = { 0.5, 0.430556 }, },
			},
			ViewInfo = OperatorInfo { Pos = { 440, 280.5 } },
		},
		Card_CTA_Label_Mrg = Merge {
			NameSet = true,
			Inputs = {
				Background = Input { SourceOp = "Card_CTA_BG", Source = "Output", },
				Foreground = Input { SourceOp = "Card_CTA_Label", Source = "Output", },
				PerformDepthMerge = Input { Value = 0, },
			},
			ViewInfo = OperatorInfo { Pos = { 440, 231 } },
		},
		Card_CTA_Xf = Transform {
			NameSet = true,
			Inputs = {
				Input = Input { SourceOp = "Card_CTA_Label_Mrg", Source = "Output", },
				Pivot = Input { Value = { 0.5, 0.430556 }, },
				Size = Input { Value = 1, Expression = "0.8 + 0.2*Ctrl_Main:GetValue('AnimPop', time - (Ctrl_Main.AnimStart + 4*Ctrl_Main.AnimStagger))", },
			},
			ViewInfo = OperatorInfo { Pos = { 550, 231 } },
		},
		Card_CTA_Mrg = Merge {
			NameSet = true,
			Inputs = {
				Background = Input { SourceOp = "Card_Subline_Mrg", Source = "Output", },
				Foreground = Input { SourceOp = "Card_CTA_Xf", Source = "Output", },
				Blend = Input { Value = 1, Expression = "Ctrl_Main:GetValue('AnimFade', time - (Ctrl_Main.AnimStart + 4*Ctrl_Main.AnimStagger))", },
				PerformDepthMerge = Input { Value = 0, },
			},
			ViewInfo = OperatorInfo { Pos = { 550, 115.5 } },
		},
		Card_Xf = Transform {
			NameSet = true,
			Inputs = {
				Input = Input { SourceOp = "Card_CTA_Mrg", Source = "Output", },
				Center = Input { Value = { 0.5, 0.5 }, Expression = "Point(0.5, 0.5 - Ctrl_Main.AnimRise*(1 - Ctrl_Main:GetValue('AnimMove', time - Ctrl_Main.AnimStart)))", },
				Size = Input { Value = 1, Expression = "0.96 + 0.04*Ctrl_Main:GetValue('AnimMove', time - Ctrl_Main.AnimStart)", },
			},
			ViewInfo = OperatorInfo { Pos = { 660, 115.5 } },
		},
		Card_Mrg = Merge {
			NameSet = true,
			Inputs = {
				Background = Input { SourceOp = "BG_Glow_Mrg", Source = "Output", },
				Foreground = Input { SourceOp = "Card_Xf", Source = "Output", },
				Blend = Input { Value = 1, Expression = "Ctrl_Main:GetValue('AnimFade', time - Ctrl_Main.AnimStart)", },
				PerformDepthMerge = Input { Value = 0, },
			},
			ViewInfo = OperatorInfo { Pos = { 770, 0 } },
		},
		QA_Saver = Saver {
			NameSet = true,
			Inputs = {
				Input = Input { SourceOp = "Card_Mrg", Source = "Output", },
				Clip = Input { Value = Clip { Filename = "__QA_OUT__", FormatID = "PNGFormat", }, },
				OutputFormat = Input { Value = FuID { "PNGFormat" }, },
			},
			ViewInfo = OperatorInfo { Pos = { 880, 0 } },
		},
	},
	ActiveTool = "Card_Mrg",
}
```

**Verify (render):** frame 48: navy vertical gradient with a soft indigo glow above center; rounded card 1120x460 px (at 1920) centered with a soft shadow below; headline, subline and pill centered on the card; pill color #4F5BD5 with white label; no fringes on the card corners. Frame 18: card nearly settled, headline letters mid-cascade from the left, subline half-risen, CTA small (~0.94) and partly transparent.

**To ship as an Edit-page Title:** remove `QA_Saver`, wrap the rest in a `GroupOperator` with `Outputs = { MainOutput1 = InstanceOutput { SourceOp = "Card_Mrg", Source = "Output", } }`, publish `Card_Headline_Flw.Text`, `Card_Subline.StyledText`, `Card_CTA_Label.StyledText` and the `Ctrl_Main` controls via `InstanceInput`, save into `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Titles/`, relaunch Resolve. Keys start at clip frame 0, so the entrance plays at the clip head; add a KeyStretcher only if an exit animation must pin to the clip end.

---

## 5. Paste and verify (Python)

### 5.1 Snippet

Status: the paste, wiring, probe and render steps were exercised live 2026-09-26 with the verifier's own helper (same calls); the snippet as a whole was not run verbatim. Every step mirrors a **[live]** mechanic (fusion-realities §1, §5, §9, §10). Runs in the Resolve MCP `run_script` environment or any Resolve Python session. Guarded to the user's scratch project.

```python
import os, re, time, subprocess

SETTING_SRC = "/abs/scratch/saas_hero.setting"        # §4.4 text, with __QA_OUT__
QA_DIR = "/abs/scratch/qa"
SCRATCH_PROJECT = "Testbed"                           # the user's scratch project (FusionSkillLab is its lab timeline); never a client project
TRACK, ITEM_INDEX = 1, 0                              # an existing Fusion Composition item
QA_FRAMES = (18, 48)                                  # mid-entrance, settled; never 0
NAMES = ["Ctrl_Main",                                 # live: its 3 splines paste as Ctrl_MainCurve*keyed, so they are not listed
         "BG_Base", "BG_Glow", "BG_Glow_Mrg", "Card_BG_Mask", "Card_BG", "Card_Shadow",
         "Card_Headline_Flw", "Card_Headline_FlwOpacity1", "Card_Headline_FlwOffset",
         "Card_Headline_FlwOffsetY", "Card_Headline", "Card_Headline_Mrg", "Card_Subline",
         "Card_Subline_Mrg", "Card_CTA_Mask", "Card_CTA_BG", "Card_CTA_Label",
         "Card_CTA_Label_Mrg", "Card_CTA_Xf", "Card_CTA_Mrg", "Card_Xf", "Card_Mrg", "QA_Saver"]
WIRES = [("BG_Glow_Mrg", "Background", "BG_Base"), ("BG_Glow_Mrg", "Foreground", "BG_Glow"),
         ("Card_BG", "EffectMask", "Card_BG_Mask"), ("Card_Shadow", "Input", "Card_BG"),
         ("Card_Headline", "StyledText", "Card_Headline_Flw"),
         ("Card_Headline_Mrg", "Background", "Card_Shadow"), ("Card_Headline_Mrg", "Foreground", "Card_Headline"),
         ("Card_Subline_Mrg", "Background", "Card_Headline_Mrg"), ("Card_Subline_Mrg", "Foreground", "Card_Subline"),
         ("Card_CTA_BG", "EffectMask", "Card_CTA_Mask"),
         ("Card_CTA_Label_Mrg", "Background", "Card_CTA_BG"), ("Card_CTA_Label_Mrg", "Foreground", "Card_CTA_Label"),
         ("Card_CTA_Xf", "Input", "Card_CTA_Label_Mrg"),
         ("Card_CTA_Mrg", "Background", "Card_Subline_Mrg"), ("Card_CTA_Mrg", "Foreground", "Card_CTA_Xf"),
         ("Card_Xf", "Input", "Card_CTA_Mrg"),
         ("Card_Mrg", "Background", "BG_Glow_Mrg"), ("Card_Mrg", "Foreground", "Card_Xf"),
         ("QA_Saver", "Input", "Card_Mrg")]
PROBES = [("Card_Mrg", "Blend", 0, 0.0), ("Card_Mrg", "Blend", 48, 1.0), ("Card_Xf", "Size", 8, 0.9926),
          ("Card_CTA_Xf", "Size", 22, 1.019), ("Card_CTA_Xf", "Size", 48, 1.0),
          ("Card_Subline_Mrg", "Blend", 14, 0.422), ("Ctrl_Main", "AnimMove", 2, 0.534)]
PIXELS = [("card", 0.25, 0.35, "1E2640"), ("cta", 0.425, 0.5694, "4F5BD5"), ("bg", 0.02, 0.03, "161C33")]

resolve = globals().get("resolve") or __import__("DaVinciResolveScript").scriptapp("Resolve")
project = resolve.GetProjectManager().GetCurrentProject()
assert project and project.GetName() == SCRATCH_PROJECT, "refusing: not the scratch project"
tl = project.GetCurrentTimeline()
item = tl.GetItemListInTrack("video", TRACK)[ITEM_INDEX]
item_comp = item.GetFusionCompByIndex(1)
assert item_comp, "not a Fusion item"

# 1. Make the item's comp CURRENT on the Fusion page (Paste works only there) [live]
fps = float(project.GetSetting("timelineFrameRate"))
def tc(frame, fps):                                  # non-drop timecode only
    r, f = int(round(fps)), int(frame)
    return "%02d:%02d:%02d:%02d" % (f // (3600 * r), (f // (60 * r)) % 60, (f // r) % 60, f % r)
tl.SetCurrentTimecode(tc(item.GetStart() + 1, fps))
resolve.OpenPage("fusion"); time.sleep(1.5)
cc = resolve.Fusion().GetCurrentComp()

# 2. Refuse name collisions: a collision renames the pasted tool (X_1) and expressions keep pointing at the OLD X
clash = [n for n in NAMES if cc.FindTool(n)]
assert not clash, "already in comp: %s (delete the old set by prefix or use a fresh item)" % clash
name_of = lambda t: t.GetAttrs()["TOOLS_Name"]
before = {name_of(t) for t in cc.GetToolList(False).values()}

# 3. Paste via Lua (no clipboard side effect). Execute is DEFERRED and swallows Lua errors [live]
os.makedirs(QA_DIR, exist_ok=True)
text = open(SETTING_SRC).read().replace("__QA_OUT__", os.path.join(QA_DIR, "saas_.png"))
path = os.path.join(QA_DIR, "paste.setting"); open(path, "w").write(text)
cc.SetData("fmd_paste", "pending")
cc.SetActiveTool(None)                               # a selected tool can capture pasted inputs
cc.Execute("comp:Lock() local ok, err = pcall(function() "
           "local s = bmd.readfile([[" + path + "]]) "
           "if s == nil then error('readfile nil: Lua table syntax error') end "
           "comp:SetData('fmd_paste', tostring(comp:Paste(s))) end) comp:Unlock() "
           "if not ok then comp:SetData('fmd_paste', 'ERR ' .. tostring(err)) end")
for _ in range(24):                                  # poll up to ~6 s
    if cc.GetData("fmd_paste") != "pending" and cc.FindTool("QA_Saver"): break
    time.sleep(0.25)

# 4. Inventory, target, wiring
report = {"paste": cc.GetData("fmd_paste")}
after = {name_of(t) for t in cc.GetToolList(False).values()}
report["missing"] = [n for n in NAMES if not cc.FindTool(n)]
report["unexpected"] = sorted(after - before - set(NAMES))      # X_1 renames, stray Merges
report["in_target_item"] = bool(item_comp.FindTool("Ctrl_Main"))
def src(tool, inp_id):                               # never GetInput on image/mask ports
    for inp in cc.FindTool(tool).GetInputList().values():
        if inp.GetAttrs()["INPS_ID"] == inp_id:
            o = inp.GetConnectedOutput()
            return name_of(o.GetTool()) if o else None
report["bad_wires"] = [(t, i, s, src(t, i)) for t, i, s in WIRES if src(t, i) != s]
mo = cc.FindTool("MediaOut1")
report["mediaout"] = bool(mo) and mo.ConnectInput("Input", cc.FindTool("Card_Mrg"))

# 5. Expression and spline probes (None = expression failed and the input evaluates to nothing)
report["probes"] = []
for t, i, f, want in PROBES:
    v = cc.FindTool(t).GetInput(i, f)
    report["probes"].append((t, i, f, v, v is not None and abs(v - want) < 0.01))
report["card_center_f4"] = cc.FindTool("Card_Xf").GetInput("Center", 4)   # expect {1: 0.5, 2: 0.47}

# 6. Render QA frames, downscale for viewing, probe pixels
def dims(p):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", p], capture_output=True, text=True).stdout
    return [int(x) for x in re.findall(r"pixel(?:Width|Height): (\d+)", out)]
def px(p, fx, fy):                                   # fractions from top-left
    w, h = dims(p)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", "crop=1:1:%d:%d" % (int(fx * w), int(fy * h)),
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return tuple(raw[:3])
report["renders"] = []
for f in QA_FRAMES:
    ok = cc.Render({"Start": f, "End": f, "Wait": True})
    p = os.path.join(QA_DIR, "saas_%04d.png" % f)
    exists = os.path.exists(p)
    if exists:
        subprocess.run(["sips", "-Z", "960", p, "--out", p.replace(".png", "_960.png")], capture_output=True)
    report["renders"].append((f, ok, exists, dims(p) if exists else None))
settled = os.path.join(QA_DIR, "saas_%04d.png" % QA_FRAMES[-1])
report["pixels"] = []
if os.path.exists(settled):
    for label, fx, fy, hx in PIXELS:
        got = px(settled, fx, fy); want = tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))
        report["pixels"].append((label, got, want, max(abs(a - b) for a, b in zip(got, want)) <= 4))
print(report)
# After review: cc.FindTool("QA_Saver").Delete()
```

Then LOOK at both `_960.png` files (one Read each). Numbers first, then eyes.

### 5.2 Healthy paste (the result envelope)

A build is healthy only if ALL hold; otherwise report the failing fields verbatim and call it a partial failure, never "built":

- `paste` == `"true"` (not `"false"`, not `"ERR ..."`, not `"pending"`).
- `missing` == [] and `unexpected` == [] (no `_1` renames, no auto-inserted Merges).
- `in_target_item` is True (the paste landed in the intended item, not whatever comp was open).
- `bad_wires` == [] and `mediaout` is True.
- every probe True; `card_center_f4` ~ {0.5, 0.47}; `Card_CTA_Xf.Size` at 22 > 1 proves the overshoot handle survived.
- both renders exist at comp resolution; settled pixels within 4/255; the two images match the "Verify" description.

---

## 6. Spec helpers (Python): conversions and spline emitter

```python
CURVES = {"settle": (0.22, 0.0, 0.25, 1.0), "decel": (0.22, 1.0, 0.36, 1.0), "snap": (0.16, 1.0, 0.30, 1.0),
          "fade": (0.33, 1.0, 0.68, 1.0), "pop": (0.34, 1.56, 0.64, 1.0), "smooth": (1/3, 0.0, 2/3, 1.0)}
TOKENS = {"fast": 0.15, "base": 0.25, "slow": 0.40, "hero": 0.60}

def frames(sec, fps): return max(1, round(sec * fps))
def g(a): return ("%.6f" % a).rstrip("0").rstrip(".")
def spline_setting(name, S, D, v0, v1, curve):          # .setting form: ABSOLUTE handles
    x1, y1, x2, y2 = CURVES[curve]; V = v1 - v0
    return ("\t\t%s = BezierSpline {\n\t\t\tSplineColor = { Red = 240, Green = 140, Blue = 60, },\n"
            "\t\t\tKeyFrames = {\n\t\t\t\t[%s] = { %s, RH = { %s, %s, }, },\n"
            "\t\t\t\t[%s] = { %s, LH = { %s, %s, }, },\n\t\t\t},\n\t\t},\n") % (
            name, g(S), g(v0), g(S + x1 * D), g(v0 + y1 * V), g(S + D), g(v1), g(S + x2 * D), g(v0 + y2 * V))
def spline_python(S, D, v0, v1, curve):                  # SetKeyFrames form: RELATIVE handles [live]
    x1, y1, x2, y2 = CURVES[curve]; V = v1 - v0
    return {S: {1: v0, "RH": {1: x1 * D, 2: y1 * V}}, S + D: {1: v1, "LH": {1: (x2 - 1) * D, 2: (y2 - 1) * V}}}

def hexf(h): h = h.lstrip("#"); return tuple(round(int(h[i:i + 2], 16) / 255, 4) for i in (0, 2, 4))
def point(px_x, px_y, W, H): return (px_x / W, 1 - px_y / H)          # CSS top-left px -> Fusion
def rect_mask(x, y, w, h, r, W, H):                                    # CSS box -> RectangleMask [live units]
    cx, cy = point(x + w / 2, y + h / 2, W, H)
    return {"Center": (cx, cy), "Width": w / W, "Height": h / H,
            "CornerRadius": 1.0 if r == "pill" else min(1.0, r / (min(w, h) / 2))}
def ellipse_mask(x, y, w, h, W, H):                                    # both axes width-relative [live]
    cx, cy = point(x + w / 2, y + h / 2, W, H)
    return {"Center": (cx, cy), "Width": w / W, "Height": h / W}
def text_size(font_px, W): return 1.70 * font_px / W                    # Open Sans [live]; calibrate others
def offset_expr(curve_ctl, k): return ("Ctrl_Main:GetValue('%s', time - (Ctrl_Main.AnimStart + %d*Ctrl_Main.AnimStagger))"
                                       % (curve_ctl, k))
```

Emit the `.setting` by string-building from the spec with these helpers, in bottom-up order (background first, trunk merges in stacking order), then run §5. Keep the generated text next to the spec; it is the artifact to diff and re-paste.

---

## 7. Batch-then-render cadence

1. **Batch by category.** All positions, then all colors, then all timing. Apply with `SetInput`/`SetKeyFrames` on the existing nodes (or edit the source and re-paste into a clean item); do not interleave categories.
2. **One contact sheet per batch.** Render a range once, then tile: `cc.Render({"Start": 0, "End": 48, "Wait": True})`, then `ffmpeg -v error -start_number 0 -i saas_%04d.png -vf "select='not(mod(n\,6))',scale=480:-2,tile=3x3" -frames:v 1 -y sheet.png` (frames 0, 6, ..., 48). Look once.
3. **Cap at 5 preview renders per rebuild.** Needing more means the spec is wrong: fix the spec, re-paste.
4. **Full resolution only for the final frame.** The Saver renders at comp resolution; downscale on disk with `sips -Z 960` before viewing. `Render` has a `proxy` parameter in the 21.1 stub (unverified effect on Saver output size).
5. **Never judge frame 0.** Entrances start at `AnimStart`; frame 0 shows only the background. Probe a mid-entrance frame and a settled frame (settled = last unit start + its longest curve + a few frames; 48 at 24 fps here).

---

