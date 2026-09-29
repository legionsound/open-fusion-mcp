<!-- animation-principles.md part 2 of 3; index: animation-principles.md -->
## 7. Recipe library (R1-R16)

Conventions: 24 fps; W x H any (normalized units); AE pixel values converted at 1920x1080. `Y` offsets are negative for "below". Every recipe: **status: unverified (not yet rendered)**.

### R1. Fade-up hero text (most common reveal)
Purpose: title lifts 30 px and fades in; opacity finishes early (early-opacity / late-settle).
Graph: `TITLE_TXT (TextPlus) -> TITLE_XF (Transform) -> TITLE_MRG.Foreground`; `BG -> TITLE_MRG.Background`; `CTRL (Custom)` unconnected.
- `TITLE_TXT`: `StyledText`, `Size` (1.70*px/W), `Center {0.5,0.5}`.
- `CTRL.NumberIn1` progress: 0@0 -> 1@10 (0.4 s), HOUSE_SETTLE.
- `TITLE_XF.Center` expression: `Point(0.5, 0.5 - 0.0278*(1 - CTRL.NumberIn1))` (replace 0.5,0.5 with the layout position).
- `TITLE_MRG.Blend`: 0@0 -> 1@5 (0.2 s), linear or Sine in-out.
- `TITLE_XF.MotionBlur 1, Quality 4, ShutterAngle 180`.
Hold to end of comp. Verify: f5 Center Y offset about -0.0059 (1-0.789 of 0.0278), Blend 1.0; f10 exact rest position; no pop at f0 (Blend 0).
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0..14) after a fix: the first build FAILED (a stray key seeded by `AddModifier` at the comp's current time survived one `SetKeyFrames(dict, True)` and the value sagged after f10); the `animate` helper above now replaces twice and asserts the key set. Measured Center Y 0.4722/0.49414/0.5 at f0/5/10, Blend 0/0.5/1.

### R2. Smash zoom entry
Purpose: arrives oversized, smashes to rest, micro-bounce.
Graph: `LOGO -> LOGO_XF -> LOGO_MRG.Foreground`.
- `LOGO_XF.Size` keys: 1.30@0 -> 1.00@6 (0.267 s) EXPO_OUT; 1.00@6 -> 1.02@10 (0.4 s) SINE_IO; 1.02@10 -> 1.00@13 (0.533 s) SINE_IO. The f6 and f10 keys are extrema: flat handles.
- `LOGO_MRG.Blend`: 0@0 -> 1@3 (0.133 s) linear.
- Motion blur on `LOGO_XF`: `ShutterAngle 270` for smear on frames 0-4.
Python: `animate(LOGO_XF, "Size", [(0,1.3),(6,1.0),(10,1.02),(13,1.0)], [EXPO_OUT, SINE_IO, SINE_IO])`.
Verify: `sample(LOGO_XF,"Size",[3,6,8,10,13])` about 1.008, 1.000, 1.010, 1.020, 1.000.
Status: unverified (not yet rendered); mechanics verified.

### R3. Slide-in from left
Purpose: element enters fully from off-frame left.
- Measure the element's right edge `xR` (normalized). Corpus-backed read in an expression: `EL_SRC.Output.DataWindow[3]/EL_SRC.Width` (DataWindow = pixel DoD `{x1,y1,x2,y2}`, unverified index order), or compute from layout.
- `CTRL.NumberIn1`: 0@0 -> 1@14 (0.6 s) QUART_OUT (AE "easeOut 80").
- `EL_XF.Center`: `Point(0.5 - (xR + 0.02)*(1 - CTRL.NumberIn1), 0.5)`.
- `EL_MRG.Blend`: 0@0 -> 1@6 (0.267 s) Cubic out (or linear).
- Motion blur on `EL_XF` (Quality 4).
Verify: f0 element fully outside frame (no pixels at x>0); f7 about 93% of travel done (Quart out y50 .934); f14 at rest.
Status: unverified (not yet rendered); mechanics verified except the DataWindow read.

### R4. Typewriter reveal
Purpose: characters appear at a constant rate, then a blinking caret.
Option A (native, simplest): `TITLE_TXT.End` (Write On End) 0@t0 -> 1@t1 **linear**; `Start` stays 0. Shipped template "Background Reveal" keys `End 0 -> 1` to write on and `Start 0 -> 1` to write off (corpus-backed; the manual's wording is reversed). Duration = chars x 20-50 ms: at 24 fps 0.5-1.2 f/char; 20 chars x 42 ms = 0.83 s = 20f.
Option B (caret built in): `TITLE_TXT.AddModifier("StyledText", "KD_TextWrite")` (attach verified). Inputs (TSV): `Text`, `Write` 0-1 (key linear 0 -> 1), `Cursor` ("_" or "|"), `ShowCursor`, `Prefix`, `ShowPrefix`. Blink after typing: `ShowCursor` expression `iif((time/F*2) % 1 < 0.5, 1, 0)` (2 Hz).
Option C (per-char styling): Follower with `Opacity1` stepped per character (kinetic suite 1).
Set `UseLigatures` to the "None" index (default for Latin keeps letters separate; TSV default reads 1, verify the index) and prefer a monospaced or `ForceMonospaced 1` face for terminal looks.
Verify: character count visible at t0 + k*rate matches k; caret blinks at 2 Hz after t1; no half-faded glyphs (Write On is per character).
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0..16), Option A only: `End` 0@0 -> 1@16 linear on a 16-character line showed exactly 4/8/12/16 characters at f4/8/12/16 (the space counts), glyphs stay at their final-layout positions and none are half-faded. Options B/C not rendered.

### R5. Logo reveal (anticipation + action + settle)
- `LOGO_XF.Size`: 0.90@0 -> 0.92@3 (0.133 s) CUBIC_OUT; 0.92@3 -> 1.05@13 (0.533 s) CUBIC_OUT; 1.05@13 -> 1.00@19 (0.8 s) SINE_IO.
- `LOGO_MRG.Blend`: 0@0 -> 1@6 (0.267 s).
- Optional glow: `LOGO -> LOGO_GLOW (Glow) -> LOGO_XF`. Key `LOGO_GLOW.Glow` 0@6 -> 0.8@13 and `XGlowSize` 10 -> 25 (TSV), SINE_IO; or `SoftGlow.Gain` 0 -> 1.5 with `Threshold` about 0.6 for a highlight-only bloom. Put the glow before the Transform so it scales with the logo.
Verify: f13 is the widest frame; f19 exact rest; glow peak lands with the scale peak, not before.
Status: unverified (not yet rendered); mechanics verified.

### R6. Parallax push (multi-layer depth)
2D (one controller, depth-weighted, AE "Null push" done better):
- `CTRL.NumberIn1`: 0@0 -> 1@L (shot length) IO_60 (camera moves are smoother than the objects inside).
- `BG_XF.Size = 1 + 0.05*CTRL.NumberIn1`, `MID_XF.Size = 1 + 0.10*CTRL.NumberIn1`, `FG_XF.Size = 1 + 0.20*CTRL.NumberIn1`; optional lateral parallax: `Center = Point(0.5 - d_i*CTRL.NumberIn1, 0.5)` with `d_i` 0.005 / 0.01 / 0.02.
3D (Fusion is better here: true perspective, DOF, fog):
`BG_IMG -> BG_PLANE (ImagePlane3D, Transform3DOp.Translate.Z -6)`, `MID_PLANE (-3)`, `FG_PLANE (-1)` -> `SCENE (Merge3D SceneInput1..3)`; `CAM (Camera3D)` into the Merge3D; `CAM.Transform3DOp.Translate.Z` keyed 2.0 -> 1.4 over L with IO_60; `SCENE -> RENDER (Renderer3D)`. Scale each plane (`Transform3DOp.Scale.X`) so it still fills frame at its depth. Optional rack focus: OpenGL renderer + accumulation DOF, animate `CAM.PlaneOfFocus` (renderer input IDs unverified).
Verify: FG moves about 4x BG over the shot; no plane edge enters frame at the last frame.
Status: unverified (not yet rendered); 2D mechanics verified, 3D unverified.

### R7. Snap rotate (90 degrees)
- `EL_XF.Angle`: 0@0 -> -90@5 (0.2 s) QUINT_OUT (AE "easeOut 95"; negative = clockwise: Fusion + is CCW, live-verified).
- Optional recoil: -90@5 -> -85@6 (0.267 s) -> -90@8 (0.333 s), SINE_IO, flat handles on extrema.
- Motion blur on (rotation smear sells the snap), Pivot at the element center.
Verify: direction matches the reference; f5 exactly -90.
Status: unverified (not yet rendered); mechanics verified.

### R8. Breathing loop (ambient)
- `EL_XF.Size` expression: `1 + 0.015*sin(2*pi*0.5*time/F)` (0.5 breaths/s, +/-1.5%). Or pulse between 0.96 and 1.08 with period 1.2 s: `0.96 + 0.12*(0.5 + 0.5*sin(2*pi*time/(1.2*F)))`.
- Seamless loop: choose the frequency so the loop length L frames holds an integer number of cycles (`Hz = n*F/L`): 8 s @24 = 192f -> 0.5 Hz gives 4 cycles.
Verify: `GetInput("Size", 0)` equals `GetInput("Size", L)`.
Status: unverified (not yet rendered); mechanics verified.

### R9. Wiggle (organic instability)
Option A (native modifier): `EL_XF.AddModifier("Center", "PerturbPoint")` (attach verified on Transform.Center). Inputs (TSV): `Value` (center point = base position), `Strength` (amplitude), `Speed` (rate), `Wobble` (roughness), `RandomSeed`, `XScale`, `YScale`. AE mapping by intent: `wiggle(2, 8px)` subtle handheld, `wiggle(4, 20px)` nervous, `wiggle(0.5, 3px)` drift. **Measured 2026-09-26 (PerturbPoint on Transform.Center, 480 frames):** peak deviation is about 0.5-0.7 x `Strength` in normalized units **on each axis** (Strength 0.05 -> +/-0.023..0.036; Strength 0.1 -> +/-0.045), so X and Y are not pixel-isotropic on 16:9 (set `YScale` = W/H for equal pixel amplitude). `Speed` scales the rate linearly: zero crossings per second about 0.35 at Speed 1, 1.05 at 5, 2.2 at 10 (roughly 0.2 x Speed above Speed 5). AE `wiggle(2, 8px)` at 1920 is about `Strength 0.007`, `Speed 10`, `YScale 1.78`. Still sample `GetInput("Center", f)` to confirm before a final. To wiggle on top of a keyed move, key the base on the Perturb's `Value` (the API equivalent of UI Insert > Perturb).
Option B (deterministic, loopable, verified mechanics): summed incommensurate sines, `A` in normalized units:
`Point(0.5 + A*(0.5*sin(2*pi*Hz*time/F) + 0.3*sin(2*pi*Hz*2.37*time/F + 1.3) + 0.2*sin(2*pi*Hz*0.61*time/F + 4.1)), 0.5 + A*1.78*(0.5*sin(2*pi*Hz*1.13*time/F + 2.2) + 0.3*sin(2*pi*Hz*2.71*time/F + 0.7) + 0.2*sin(2*pi*Hz*0.47*time/F + 5.3)))`
(1.78 = W/H so X and Y amplitudes match in pixels at 16:9). For a seamless loop use integer cycle counts over L instead of the irrational multipliers.
Option C (true Perlin via `.setting` paste): Expression modifier with `noise()` on `Center` (section 5.1). Shipped `Advanced Camera Shake.setting` combines two `Shake` modifiers through an Expression modifier for layered handheld shake.
`.setting` for Option A (shape from shipped `Hologram Glitch.setting`; values illustrative): `EL_Wig = PerturbPoint { Inputs = { Value = Input { Value = { 0.5, 0.5 } }, Strength = Input { Value = 0.05 }, Speed = Input { Value = 0.5 }, Wobble = Input { Value = 1 }, RandomSeed = Input { Value = 1234 } } }`, consumer `Center = Input { SourceOp = "EL_Wig", Source = "Value", }`.
- Rotation wobble: `PerturbNumber` on `Angle` (`Value 0`, small `Strength`), or `2*sin(...)` in degrees.
- Opacity flicker (rare): `TITLE_MRG.Blend` = `iif(((sin(time*12.9898)*43758.5453) % 1) > 0.95, 0.3, 1)` (deterministic hash, not `math.random`).
- `Shake` modifier (`XMinimum/XMaximum/YMinimum/YMaximum`, `Smoothness`, `LockXY`, `RandomSeed`): ranges are **absolute**, 0-1 throws the element anywhere; use 0.49-0.51 around the base. `CameraShake` tool (`XDeviation`, `YDeviation`, `RotationDeviation`, `OverallStrength`, `Speed`, `Randomness`) shakes a whole image branch.
Never `wiggle(20, 50)`-level violence unless the brief is glitch/distress.
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0, 24, 48 and sampled 480 frames), Option A (PerturbPoint) amplitude/rate calibrated as above; `Shake` with X/Y Min/Max 0.49-0.51, Smoothness 10 stayed inside +/-0.0081. Options B/C not rendered.

### R10. Orbit
Option A (native): `EL_MRG.AddModifier("Center", "Vector")` (attach verified on Transform.Center). Inputs (TSV): `Origin` (orbit center), `Distance` (radius, normalized width), `Angle` (degrees), `ImageAspect` (default 1.778, keeps the orbit circular). `Angle` expression: `time/F*360*0.2` (0.2 rev/s).
Option B (expression): `Point(0.5 + 0.104*cos(2*pi*0.2*time/F), 0.5 + 0.104*1.778*sin(2*pi*0.2*time/F))` (AE radius 200 px at 1920 = 0.104; the 1.778 = W/H aspect fix is mandatory or the orbit is an ellipse). With Y up this runs counterclockwise; negate the sine for clockwise (AE's same formula is clockwise because AE Y is down).
Verify: on-screen distance from origin constant in pixels at f0, f30, f60.
Status: unverified (not yet rendered); B mechanics verified.

### R11. Glitch stutter
Deterministic hash, posterized to 12 fps (2-frame blocks at 24 fps; AE used 15 fps, not integer at 24):
`EL_XF.Center` =
`Point(0.5 + iif(((sin(floor(time/2)*12.9898)*43758.5453) % 1) > 0.97, (((sin(floor(time/2)*78.233)*12543.21) % 1) - 0.5)*0.042, 0), 0.5 + iif(((sin(floor(time/2)*12.9898)*43758.5453) % 1) > 0.97, (((sin(floor(time/2)*39.425)*23421.63) % 1) - 0.5)*0.019, 0))`
(+/-20 px X = 0.021 half-range at 1920, +/-5 px Y at 1080; threshold 0.97 at 12 blocks/s = a glitch about every 2.8 s.) Optional companions on the same hash: `KD_ChannelShifter` or a stepped `Merge.Blend` dip for an RGB tear; `KD_NumberRandom` (`MinimumValue`, `MaximumValue`, `Seed`, `Frames`, `Interpolation`, `NewValueForEveryFrame`) as a seeded random source on `CTRL.NumberIn1`. Motion blur **off** for glitch (hard jumps should not smear).
Verify: identical frames on re-render (determinism); jumps only on even-frame boundaries.
Status: unverified (not yet rendered); mechanics verified (`%` corpus-backed).

### R12. Reveal with mask (wipe-on)
Graph: `WIPE (RectangleMask) -> TITLE_TXT.EffectMask` (or `TITLE_MRG.EffectMask` to mask the merge). Fusion's mask input is the AE track matte.
- `WIPE.Width 1.0`, `Height 1.0` (each relative to its own frame dimension, live-verified), `SoftEdge 0.005-0.02` for a feathered edge.
- Left-to-right: the mask's right edge travels from the text's left edge `xL` to its right edge `xR`: `WIPE.Center = Point(xL - 0.5 + (xR - xL)*CTRL.NumberIn1, 0.5)`; `CTRL.NumberIn1` 0@0 -> 1@10 (0.42 s; range 7-14f = 300-600 ms) CUBIC_OUT or QUART_OUT.
- Matte variants: inverted = `WIPE.Invert 1`; luma matte = `BitmapMask` fed by the matte image (channel set to luminance, input IDs unverified) or `MatteControl`; alpha matte from another image = Merge `Operator "In"` (Held Out = inverted).
- Straight (linear spatial) wipe reads architectural and premium; angle the mask (`WIPE.Angle`) for a diagonal sweep.
Verify: f0 no text pixels, f10 full text, edge travels in reading direction.
Status: unverified (not yet rendered); mechanics verified.

### R13. Counter (number counting up) - Fusion can do this natively
AE could not set Source Text through MCP; Fusion drives Text+ `StyledText` with a SimpleExpression (manual slate example).
- `CTRL.NumberIn1`: 0@t0 -> 1234@t1 with COUNT_UP (near-linear, soft landing), 1.5-2 s.
- `NUM_TXT.StyledText` expression: `Text(string.format("%d", floor(CTRL.NumberIn1 + 0.5)))`.
- Thousands separators (corpus pattern, statement block): `:local s=string.format("%d", math.floor(CTRL.NumberIn1+0.5)); local l,n,r=string.match(s,'^(.-%d)(%d*)(.*)'); return Text(l..(n:reverse():gsub('%d%d%d','%0,'):reverse())..r)` (unverified as typed; the shipped template returns a plain string).
- Prefix/suffix: `Text("$" .. string.format("%.1f", CTRL.NumberIn1) .. "M")`.
- **Tabular digits** or the number jitters sideways every frame: `NUM_TXT.FontFeatures "tnum"` (OpenType) or `ForceMonospaced 1`, and right-align (`HorizontalLeftCenterRight 1`, verify sign).
- Plain frame counter: `TimeCode` modifier with only `Frms` on. `Text Timer` runs on real clock time: not for renders.
- Unit label arrives after the number resolves (+4-6f), per data-motion taste.
Verify: final frame shows exactly 1234 (format and rounding), digits do not shift horizontally during the count.
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 12, 24, 36): `Text(string.format('%d', floor(CTRL.NumberIn1 + 0.5)))` rendered 664 / 1118 / 1234. The thousands-separator statement block above works as typed (read back "561,604" mid-count). **Trap (live): Custom `NumberIn*` clamps to +/-1,000,000**, so a 0 -> 1234567 key read 1,000,000 at the end: key the controller 0 -> 1 and write `floor(CTRL.NumberIn1*1234567 + 0.5)` in the text expression. Tabular-digit jitter not measured.

### R14. Smash cut (instant change with motion blur and flash)
At cut frame `C`:
- Hard switch without keys: `OUT_MRG.Blend = iif(time < C, 1, 0)`, `IN_MRG.Blend = iif(time >= C, 1, 0)` (or `Flags = { StepIn = true }` keys in `.setting`, corpus-backed).
- `IN_XF.Size`: 1.05@C -> 1.00@C+3 (0.133 s) EXPO_OUT; `IN_XF.MotionBlur 1`, `ShutterAngle 270-360`, `Quality 6`.
- Flash: `FLASH (Background, TopLeftRed/Green/Blue 1)` -> `FLASH_MRG.Foreground` (`ApplyMode "Screen"` or Normal) with `Blend` 0@C-1 -> 1@C -> 0@C+1 (2 frames).
- Directional streak alternative: `DirectionalBlur` (`Type` linear index, `Length` 0.03 -> 0 over 3f, `Angle` = motion direction).
Verify: frame C is the first frame of the new state; flash peaks exactly on C; no dissolve frames.
Status: unverified (not yet rendered); mechanics verified.

### R15. Camera push-in (cinematic)
2D (the AE Null): `PUSH_XF (Transform)` after the final composite: `Size` 1.00@0 -> 1.20@L IO_85 (or HOUSE_SETTLE for a push that lands). Scaling a finished 2D frame resamples: keep it under about 1.15 on text-heavy frames, or push per layer upstream, or go 3D.
3D (preferred when layers exist): `Camera3D.Transform3DOp.Translate.Z` dolly with IO_85; real parallax and optional DOF.
Handheld feel: `PerturbPoint` on `PUSH_XF.Center` (small Strength, slow Speed, calibrate to about 4 px at 0.5 Hz), or the `CameraShake` tool with `OverallStrength` about 0.1, `Speed` about 0.2.
Rule: one dominant camera move per scene; camera easing smoother than the objects; never a push that makes text unreadable mid-move.
Verify: text stays inside title safe at L; midpoint frame still legible.
Status: unverified (not yet rendered); 2D mechanics verified.

### R16. Rotating seal / emblem / circular text badge
A seal is a live accent: slow continuous rotation for the whole shot, never reveal-and-stop.
Graph: `SEAL_TXT (TextPlus) -> SEAL_XF (Transform) -> SEAL_MRG.Foreground`; optional rings `RING (sEllipse, Solid 0, BorderWidth 0.002) -> RING_R (sRender)` merged under the text before `SEAL_XF`.
- `SEAL_TXT.LayoutType 2` (= Circle; shipped "Circle Layout" preset, and 3 = Path), `LayoutWidth` about 0.25-0.35 (ring size, verify), `FitCharacters` (verify options), `Size` 0.02-0.03, `CharacterSpacing` 1.1-1.3, text with a trailing separator ("EST 2014 • STUDIO NAME • ") so the ring closes evenly.
- Spin: `SEAL_XF.Angle` expression `-time/F*12` (12 deg/s clockwise, one rev per 30 s; premium range 8-15 deg/s; drop the minus for counterclockwise). Constant speed: **no ease** on a steady spin.
- Keyframed loop-safe alternative: `Angle` 0@0 -> -360@F*30 linear with `.setting` flags `Flags = { Linear = true, Loop = true, LoopRel = true }` on both keys (Relative Loop = AE `loopOut("offset")`, corpus-backed).
- Entrance: `SEAL_MRG.Blend` 0 -> 1 over 12f; the spin runs from frame 0.
- Text on an arbitrary curve instead: `LayoutType 3` (Path) and key `PositionOnPath` (values beyond 0-1 continue off the path).
Verify: text reads correctly at f0 (upright letters on the ring), rotation direction and rate match the reference, no seam in the ring text.
Status: unverified (not yet rendered); mechanics verified except LayoutWidth/FitCharacters semantics.

---

## 8. Kinetic typography suite (Text+ Follower)

Follower = AE text animator + range selector. `text.AddModifier("StyledText", "StyledTextFollower")` (attach verified). Get it with `inp(text, "StyledText").GetConnectedOutput().GetTool()`. **The text now lives in the Follower's `Text` input**; `TextPlus.StyledText` is wired from the Follower's `StyledText` output, and setting `TextPlus.StyledText` does nothing while it is connected. Set `follower.SetInput("Text", "TITLE")` and read it back.

Follower facts (TSV + corpus):
- **Nothing happens unless values are keyed** on the Follower's inputs (static changes are ignored). Key the per-character animation once; the Follower replays it per character with a delay.
- Animatable per-character inputs: `Opacity1`, `Red1/Green1/Blue1/Alpha1`, `SoftnessX1/Y1`, `Offset1` (shading element offset), `CharacterSizeX/Y`, `CharacterOffset` (Point), `CharacterAngleX/Y/Z`, `CharacterShearX/Y`, `CharacterSpacing`, `Size`, plus Word/Line variants. Shipped presets mostly key `Opacity1`, `CharacterAngleX/Y`, `CharacterSizeX/Y`, `CharacterShearX`.
- Timing tab, **live-verified 2026-09-26 by render**: `Order` 0 = Left to right, 1 = Right to left, 2 = Inside out, 3 = Outside in, 4 = Random but one by one, 5 = Completely random, 6 = Manual curve (default curve: all characters together), 7 = **Automatic** (the default; behaved Left to right on Latin text). The input's `INPST_ComboControl_String` list shows Automatic first, so do not derive indices from that list. **Always set Order explicitly.** `DelayType` 0 = None (all characters together), 1 = frames **between each character** (the default; corpus: Delay 1-3), 2 = total spread **between first and last character** (corpus: Delay 8-50). `Delay` (-25..25, fractional allowed). `Range` + `FirstCharacter`/`LastCharacter` limit the effect to a character span. Spaces count as characters.
- Keep `UseLigatures` at None for Latin so "fi"/"ff" do not animate as one glyph.

Stagger math: character `i` starts at `t0 + i*Delay` (DelayType 1). Total = `(n-1)*Delay + clip`. Keep totals under 2 s (48f @24).

**(1) Typewriter, 20-50 ms per char.** Follower `Opacity1` keyed as a step: 0@0, 1@0.01 (or `Flags = { StepIn = true }`), `DelayType 1`, `Delay` = 0.5-1.2 f/char at 24 fps (fractional OK). Or R4 Write On / KD_TextWrite. 24 chars x 30 ms = 0.72 s = 17f.

**(2) Mask reveal, 300-600 ms (7-14f @24) ease-out.** R12 mechanism on the whole line, CUBIC_OUT or QUART_OUT. Straight wipe for architectural feel.

**(3) Scale pop per character (energetic).** Follower keys: `CharacterSizeX` and `CharacterSizeY` 0.70@0 -> 1.05@4 (0.167 s) CUBIC_OUT -> 1.00@6 (0.267 s) SINE_IO; `Opacity1` 0@0 -> 1@3; the "drop into place" is a small Y settle on a Point (`CharacterOffset` or `Offset1`), which needs an `XYPath` (Points never take a BezierSpline; shipped Followers drive `Offset1` through a PolyPath) with its `Y` keyed 0.006 -> 0 over 0-6f (units and sign unverified: check in the viewer). `Order 0`, `DelayType 1`, `Delay 1.5`. Without the small Y settle it reads flat.

```python
def follower_pop(text_tool, title, delay_f=1.5):
    text_tool.AddModifier("StyledText", "StyledTextFollower")
    fol = inp(text_tool, "StyledText").GetConnectedOutput().GetTool()
    fol.SetInput("Text", title)          # the text now lives here
    fol.SetInput("Order", 0)             # Left to right: set explicitly
    fol.SetInput("DelayType", 1)         # frames between each character
    fol.SetInput("Delay", delay_f)
    for ch in ("CharacterSizeX", "CharacterSizeY"):
        animate(fol, ch, [(0, 0.70), (4, 1.05), (6, 1.0)], [CUBIC_OUT, SINE_IO])
    animate(fol, "Opacity1", [(0, 0.0), (3, 1.0)], [None])
    return fol
```

```lua
-- .setting (shape from setting-format.md 4.1 / shipped Random Write On; handles absolute; unverified as typed)
POP_TXT = TextPlus {
    Inputs = {
        UseFrameFormatSettings = Input { Value = 1, },
        StyledText = Input { SourceOp = "POP_Follower", Source = "StyledText", },
        Font = Input { Value = "Open Sans", }, Style = Input { Value = "Bold", },
        Size = Input { Value = 0.08, },
    },
    ViewInfo = OperatorInfo { Pos = { 0, 0 } },
},
POP_Follower = StyledTextFollower {
    Inputs = {
        Text = Input { Value = StyledText { Value = "MAKE IT MOVE" }, },
        Order = Input { Value = 0, },
        DelayType = Input { Value = 1, },
        Delay = Input { Value = 1.5, },
        CharacterSizeX = Input { SourceOp = "POP_Size", Source = "Value", },
        CharacterSizeY = Input { SourceOp = "POP_Size", Source = "Value", },   -- one shared curve (Connect To)
        Opacity1 = Input { SourceOp = "POP_Opacity", Source = "Value", },
    },
},
POP_Size = BezierSpline {
    SplineColor = { Red = 28, Green = 132, Blue = 243 },
    KeyFrames = {
        [0] = { 0.7,  RH = { 1.32, 1.05 } },                         -- CUBIC_OUT 0->4
        [4] = { 1.05, LH = { 2.72, 1.05 }, RH = { 4.74, 1.05 } },    -- flat extremum, SINE_IO 4->6
        [6] = { 1,    LH = { 5.26, 1 } },
    },
},
POP_Opacity = BezierSpline {
    SplineColor = { Red = 179, Green = 28, Blue = 244 },
    KeyFrames = {
        [0] = { 0, RH = { 1, 0.333333 }, Flags = { Linear = true } },
        [3] = { 1, LH = { 2, 0.666667 }, Flags = { Linear = true } },
    },
},
```
Verify: character k reaches full size at f6 + 1.5k; the last character of a 12-character word lands at about f22.5 (0.94 s); no character is visible before its own start frame.
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0, 2, 4, 8, 14, 23, 40): the `.setting` above pasted as typed; characters appear left to right 1.5 f apart (f8 shows "MAKE" plus a faint "I"), the line is complete and static from f23. The optional Y settle was not built.

**(4) Audio sync.** Options, most native first:
- `FairlightAnimator` modifier on `EL_XF.Size` (attach verified): `Analysis` (pick in UI; option strings unlisted), `Scale` (sensitivity 0.3-0.8 of the AE slider idea), `Offset` (base, e.g. 1.0), `TimeOffset` to anticipate the beat.
- `KD_NumberBeat` on `CTRL.NumberIn1` for BPM-locked pulses: `BeatsperMinute`, **`FramesperSecond` (defaults to 25: set to comp fps)**, `Attacktime`, `DecayTime`, `SustainTime`, `ReleaseTime`, `MinimumValue`, `MaximumValue`; then `EL_XF.Size = 1 + 0.05*CTRL.NumberIn1`.
- `Fuse.SuckLessAudio` (reads a WAV: `WaveFile`, `AmplitudeScale`, `SampleStartFrame`) or MIDI Extractor Beat mode (Release > 0 or the beat is invisible).

**Phrase choreography:** treat kinetic type as a phrase performance: anchor / support / **active word**. The active word gets the strongest motion; offset each word's properties so words relate. Mechanism: one `TextPlus` per word (own Transform, own timing) when roles differ; a single Text+ + Follower when a uniform ripple is the brief; Follower `Range` with `FirstCharacter/LastCharacter` to hit one word. Reject every word sharing identical entrance timing unless minimal is the brief.

**Source-text patterns (Fusion SimpleExpressions on StyledText):** `Text("SCORE: " .. floor(CTRL.NumberIn1 + 0.5))`; `Text("LVL " .. string.format("%d", CTRL.NumberIn2))`; mirroring another title: right-click Publish on the source Styled Text and Connect To on the target (manual), or a `PublishText` modifier.

**Font guidance:** geometric/grotesque sans animate clearly at speed (Futura, Montserrat, Bebas Neue, Helvetica, Inter, Open Sans); avoid decorative, script and high-contrast serif faces: hairlines shimmer and vanish in motion blur. Keep a kinetic-type reel under 3 minutes.

Status: all suite items unverified (not yet rendered); Follower attach verified, per-input behavior unverified.

---

## 9. Loop patterns

| AE | Fusion spline (UI / `.setting` flags on BOTH end keys of the segment, corpus-backed) | Expression (verified mechanics), `P` = period frames, `t0` = loop start |
|---|---|---|
| `loopOut("cycle")` | Set Loop / `Flags = { Loop = true }` | `CTRL:GetValue("NumberIn1", t0 + (time - t0) % P)` |
| `loopOut("pingpong")` | Ping-Pong / `Flags = { Loop = true, Pingpong = true }` | `CTRL:GetValue("NumberIn1", t0 + P - abs((time - t0) % (2*P) - P))` |
| `loopOut("offset")` | Relative Loop / `Flags = { Loop = true, LoopRel = true }` | `CTRL:GetValue("NumberIn1", t0 + (time-t0) % P) + floor((time-t0)/P)*(CTRL:GetValue("NumberIn1", t0+P) - CTRL:GetValue("NumberIn1", t0))` |
| `loopOut("continue")` | Gradient Extrapolation (UI) | `v(K) + (time - K)*(v(K) - v(K-1))` past the last key K |
| `loopIn(...)` | Set Pre-Loop / `PreLoop = true`, `PrePingpong = true` | mirror the formulas for `time < t0` |

- Spline loops are **live** (edit the source keys, repeats update) and run to the end of the global range; Duplicate (context menu) makes dead copies.
- **Live-verified 2026-09-26:** `.setting` flags behave as the table says (0@0 -> 1@10 sampled at f0/5/10/12/15/20/25/30: Relative Loop 0, .5, 1, 1.2, 1.5, 2, 2.5, 3; Loop 0, .5, 0, .2, .5, 0, .5, 0; Ping-Pong 0, .5, 1, .8, .5, 0, .5, 1; `StepIn` 0 until f10 then 1). Python `SetKeyFrames({0: {1: 0, "Flags": {"Loop": True, "Linear": True}}, 10: {...same flags}}, True)` also works (same cycle values), though `GetKeyFrames()` does not echo the flags. A cycle shows the first key's value at the last key's frame: end on the start value for a seamless loop.
- Where to loop: continuous spin = Relative Loop 0 -> 360 (or `time*rate` expression); orbit = cycle; flicker pattern = cycle; Fast Noise evolution = `SeetheRate` (self-animating, no keys); scrolling gradient = Background `Offset` with `Repeat "Repeat"` or `"Ping-Pong"`.
- Seamless-loop checklist: every procedural term has an integer number of cycles over L; Perturb/Shake do not loop (use summed sines); compare `GetInput` at f0 and fL for every animated input; for image-level loops `KD_SeamlessLoop` retimes a branch into a loop (behavior unverified).
- Seam velocity, not only seam value: compare the step across the seam with the steps beside it
  (`GetInput(id, L-1) - GetInput(id, L-2)` against `GetInput(id, 1) - GetInput(id, 0)`); a match
  in value with a mismatch in slope reads as a hitch. Deliver frames 0..L-1: a loop whose last
  rendered frame repeats frame 0 holds one duplicate frame at every wrap. [checked live 2026-09-26,
  L 24] A `sin(2*pi*time/24)` loop read steps 0.241 (22->23), 0.259 (23->24) and 0.259 (0->1): smooth.
  An eased 0 -> 1 -> 0 cycle read -0.042 (22->23) against +0.014 (0->1): the raw rule flags it, yet the
  motion is smooth because it turns around at the seam with zero velocity on both sides. At a turning
  point compare second differences instead (`f(L-1) - 2*f(0) + f(1)` against the same one frame inside
  the loop); a linear triangle loop shows its hitch there as a spike. Both loops read f(24) = f(0), so
  rendering 0..24 inclusive would duplicate frame 0.
- Negative control values (a slide index driven below 0): Lua `%` is floored, so `x % n` is
  already in [0, n) for n > 0. Do not port AE/JavaScript's `((x % n) + n) % n`; it is redundant
  here. `math.fmod` keeps the sign of x and is the wrong choice for wrapping.

---

## 10. Posterize / stepped motion (AE `posterizeTime`)

| Target look | @24 fps step n | @25 | @30 |
|---|---|---|---|
| Limited animation 12 fps | 2 | 2 (12.5) | 2.5 -> use 2 or 3 |
| Toy/cardboard 15 fps | 2 (12) or alternate 2/1 | 2 | 2 |
| Stop motion 8 fps | 3 | 3 | 4 |
| Glitch 5-8 fps | 3-5 | 3-5 | 4-6 |

Mechanisms:
- One property: read the source at stepped time: `CTRL:GetValue("NumberIn1", floor(time/n)*n)`; for a procedural term just replace `time` with `floor(time/n)*n`.
- **Whole branch (Fusion is better):** `TimeStretcher` after the animated branch, `SourceTime` expression `floor(time/2)*2`, `InterpolateBetweenFrames` = Nearest (index 0 expected: Nearest/Blend/Flow, verify). Everything upstream (Perturb, Follower, 3D) steps together. `TimeSpeed.Speed` cannot be animated; `TimeSpeed.Delay` shifts a branch.
- Hold keys: `Flags = { StepIn = true }` in `.setting` (corpus); UI keys I/O. The manual's Step In / Step Out wording is contradictory: check the curve.
- Motion blur on stepped motion should be off or low (a held pose with blur looks wrong).

---

## 11. Scene-level choreography

Sequence reveals, never simultaneously (AE 30 fps beats converted):

| Beat | AE @30 | Seconds | @24 | What |
|---|---|---|---|---|
| BG appears | 0 | 0 | 0 | Instant, no fade: establishes the canvas |
| BG ambient starts | 4 | 0.13 | 3 | Breath, drift, parallax |
| ENV elements stagger in | 8 | 0.27 | 6 | Grid, scanlines fade up over 13f (0.53 s) |
| Hero content enters | 20 | 0.67 | 16 | R1 or R2 |
| Secondary content | 36 | 1.2 | 29 | Subtitle, supporting elements |
| Effects punch in | 50 | 1.67 | 40 | Glow ramp, sweep |
| Grade settles | 60 | 2.0 | 48 | Grade nodes static, no animation needed |
| Loops live | 60+ | 2.0+ | 48+ | All loop expressions active |

Stagger between layer reveals 8-16f @30 = 0.27-0.53 s = 6-13f @24. Never reveal everything at frame 0.

In Fusion, build the beat sheet as data: one `CTRL` per scene holding progress curves, with each element's expression reading `CTRL:GetValue(..., time - beat_i)`. Retiming a beat = changing one number. For Edit-page templates, add `KeyStretcherMod` (or the `KeyStretcher` node before MediaOut; `SourceStart/SourceEnd/StretchStart/StretchEnd`) so entrance and exit keep their timing when the clip is trimmed; shipped titles use StretchStart/End about 34/99 of 119.

---

