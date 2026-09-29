<!-- 03-animation-splines-modifiers-expressions.md part 2 of 2; index: 03-animation-splines-modifiers-expressions.md -->
## 5. Modifiers (Ch. 12 pp. 315-318; details xref Ch. 65)

### 5.1 How modifiers attach
- Right-click a parameter in the Inspector (name or slider) or its onscreen control in the viewer. **Modify With** lists only modifiers valid for that type (number, text, polyline, gradient, point) (p. 315).
- Applied modifier controls appear in the **Modifiers** tab (highlighted when present; grayed if none). Modifier headers behave like tool headers; drag a modifier title bar into a viewer to view its output (p. 316). xref p. 1767: Modifiers tab shortcut **F11**.
- Modifiers chain/branch like nodes (e.g. Calculation's two operands can each take modifiers). **Insert** submenu places a modifier between an existing modifier and the parameter (p. 317), e.g. Insert > Anim Curves on Displacement, Insert > Perturb on a path.
- **Connect To** links a parameter to a modifier or published value; list is filtered by type; link is **bidirectional** (p. 317).
- Modifiers stack with keyframes: keyframe Center, then Modify With > Perturb for secondary wiggle (p. 316).

### 5.2 Catalog (pp. 317-318; details xref)

| Modifier | What it does | Apply |
|---|---|---|
| Anim Curves | Retimes/rescales/eases an animation normalized to comp or clip duration | Modify With / Insert > Anim Curves |
| Bézier Spline | Default keyframe curve | Animate / BezierSpline |
| B-Spline, Cubic Spline, Natural Cubic Spline | Alternative keyframe curves | Modify With |
| Calculation | Math on two operands, each time-offsettable | Modify With > Calculation |
| CoordTransform Position | World position of a 3D object after downstream transforms | Modify With > CoordTransform Position |
| Custom Poly (xref p. 1770) | Per-point expressions on polylines | Shape label > Insert > Custom Poly |
| Expression | Formula with 9 number + 9 point inputs | Modify With > Expression |
| Fairlight Animator | Drives a number from Fairlight audio analysis | Modify With |
| From Image | Builds a gradient by sampling an image along a line | Right-click a Gradient bar > From Image |
| Gradient Color | Gradient mapped over a time range to drive a value | Modify With > Gradient Color |
| KeyStretcher | Stretches keys when a Title template is trimmed in Edit/Cut | Modify with > KeyStretcher |
| MIDI Extractor | Drives a value from a MIDI file | Modify With > MIDI Extractor |
| Offset (Angle, Distance, Position) | Value/point from relation between two positions | Modify With > Offset ... |
| Path | Polyline motion path + Displacement (time) spline | Path |
| Perturb | Smooth Perlin random animation (wiggle) | Modify With / Insert > Perturb |
| Probe | Drives a value from pixel color/luma of an image region | Modify With > Probe |
| Publish | Exposes a static value for Connect To | Publish |
| Resolve Parameter | Auto-animates over a transition template's duration | context menu Resolve Parameter |
| Shake | Smoothed random values between Min/Max | Modify With > Shake (viewer: Shake Position) |
| Track | Single-point tracker on a parameter | viewer: Modify With > Tracker > Position/Steady/Unsteady |
| Vector Result | Offsets a position by distance and angle from an origin | Modify With > Vector (Result) |
| XY Path | Separate X and Y splines | Modify With > XY Path |

Text+ Styled Text field adds text modifiers (xref p. 1152): Animate, Character Level Styling, Comp Name, **Follower**, Publish, **Text Scramble**, **Text Timer**, **Time Code**, Connect To.

### 5.3 Animation-critical modifier details (xref)

**Anim Curves** (pp. 1761-1763)
- **Source**: Transition (auto for Edit-page transitions; follows transition duration), **Duration** (clip-based comps; follows trims), **Custom** (shows **Input** dial to drive timing manually).
- **Curve**: **Linear** (default), **Easing** (shows **In** and **Out** menus of ease types; manual names **Bounce**, others unlisted), **Custom** (mini Spline Editor).
- **Mirror** (plays forward then back to start; first half twice as fast), **Invert** (flips curve high to low).
- Scaling: **Scale** (multiplier, think "end value"; set at last frame), **Offset** (added, think "start value"; set at first frame), **Clip Low** (never below 0.0), **Clip High** (never above 1.0).
- Timing: **Time Scale** (1.0 = runs for comp duration; 2.0 = twice as fast), **Time Offset** (delay as fraction of duration: 0.5 = start midway).
- On a bare parameter it animates 0 to 1 over the duration (Size example); on Displacement it is normalized to comp duration.

**Calculation** (pp. 1765-1768)
- **First Operand**, **Second Operand**, **Operator**: Add; Subtract (First - Second); Subtract (Second - First); Multiply; Divide (First / Second); Divide (Second / First); Minimum; Maximum; Average; First only.
- Time tab: **First/Second Operand Time Scale** (multiplies frame number: 0.5 at frame 10 reads frame 5), **First/Second Operand Time Offset** (+10 reads 10 frames ahead, -10 reads 10 back).
- Easier to retime operands than with Expression.

**Expression modifier** (pp. 1772-1776): see 6.3.

**Perturb** (pp. 1789-1791): Smooth Perlin jitter, works on sliders, points, polylines, shapes, grid meshes, gradients, even if already animated. Controls: **Value** (center value; type matches the parameter), **Jaggedness** and **Phase** (polylines/meshes only), **Random Seed** + **Randomize**, **Strength** (max deviation), **Wobble** (smoothness vs unpredictability), **Speed** (rate of change). Cannot smooth existing animation.

**Shake** (pp. 1795-1796): **Random Seed**, **Smoothness** (0 = fully random; higher smoother), **Lock X/Y** (toggle to split X and Y into independent sliders), **Minimum / Maximum** (absolute output range, e.g. 0.0-1.0 anywhere in frame, 0.70-0.90 small corner shake). Keyframe Min/Max to tighten over time.

**Offset Angle / Distance / Position** (pp. 1785-1788): Position X/Y, Offset X/Y, Flip Position/Offset Horizontal/Vertical, **Mode** (Offset, Difference (Position - Offset), Difference (Offset - Position), Average, Use Position Only, Use Offset Only, Maximum, Minimum, Invert Position, Invert Offset, "Invert Sugar" (as printed; likely a typo), Random Offset), **Image Aspect** (width/height). Time tab: Position/Offset **Time Scale** and **Time Offset**. Offset Angle outputs 0-360 degrees.

**Vector Result** (pp. 1798-1799): **Origin**, **Distance**, **Angle** (thumbwheel), **Image Aspect**. Animate Angle (10 to 1000) with a path on Origin = orbit.

**Gradient Color** (pp. 1779-1780): Gradient bar, Gradient Interpolation Method (RGB default), **Repeat** (Once / Repeat / Ping Pong), **Gradient Offset**, **Start Time / End Time** (frames).

**KeyStretcher / Keyframe Stretcher [KFS] node** (pp. 1366-1368, 1780): **Source Start/Source End** (full animation range), **Stretch Start/Stretch End** (only keys between these stretch; keys outside keep their frame distance to the ends), **Stretch Edges Instead**. Spline Editor still shows original key positions. KFS node goes just before MediaOut/Saver and affects all upstream animation.

**Resolve Parameter** (p. 1794): add to a control in a transition macro; it animates over the transition duration. Save to `$TEMPLATE_MAC_OS_PATH/Transitions` or `$TEMPLATE_MAC_USER_PATH/Transitions` (Windows `$TEMPLATE_WIN_OS_PATH\Transitions`, `$TEMPLATE_WIN_USER_PATH\Transitions`); restart Resolve.

**Publish** (p. 1793): only animated controls appear in Connect To automatically; static controls must be Published first (right-click > Publish).

**Track** (pp. 1796-1798): single pattern, single output; source defaults to the node upstream of the modified node; type/drag another node into the Track Source field.

**Probe** (pp. 1791-1793): Image to Probe, Channel (Red/Green/Blue/Alpha/Luma), Position X Y, Probe Rectangle + Width/Height + Evaluation (Average/Minimum/Maximum), Value tab Scale Input, Black Value, White Value, Out of Image Value; outputs Result/Red/Green/Blue/Alpha for Connect To.

**Fairlight Animator** (p. 1778): Clip Name, Analysis, Scale, Offset, High/Low Pass Filter (Hz), Time Scale, Time Offset. **MIDI Extractor** (pp. 1781-1784): Mode Beat/Note/Control Change/Poly AfterTouch/Channel AfterTouch/Pitch Bend, Beat (Quarters), envelope (times in seconds), Result Offset/Scale/Curve, 16 channels.

**Custom Poly** (pp. 1770-1771): Poly Expression X/Y per point, variables `px`, `py`, `disp` (0-1 along polyline), `index` (0-based), `num`, `getx(disp)`, `gety(disp)`, `getx_at(disp, time)`, `gety_at(disp, time)`, `get2x/y()`, `get3x/y()` (+ `_at`), plus n1..n9 etc.; Number of Points (0 = source count).

**Text+ text modifiers** (pp. 1153, 1165-1169):
- **Follower** (Styled Text right-click > Follower): animate text params in the Modifiers tab (a change is invisible unless keyed), then Timing tab: **Range** (all or selected characters), **Order** (Left to right, Right to left, Inside out, Outside in, Random but one by one, Completely random, Manual curve; spaces count), **Delay Type** (**Between Each Character**: N frames per char; **Between First and Last Character**: total duration fixed), Clear All Character Styling.
- **Text Scramble**: Randomness 0-1, Input Text, Animate on Time, Animate on Randomness, Don't Change Spaces, Substitute Chars.
- **Text Timer**: Mode CountDown / Timer / Clock; Hrs/Mins/Secs show checkboxes and start sliders; Start/Reset.
- **Time Code**: Hrs, Mins, Secs, Frms, Flds (Frms only = plain frame counter), Start Offset, Frames per Second, Drop Frame.
- **Write On** (Text+ range control): manual says animate the End from 1 to 0 for Write On and Start 0 to 1 for Write Off (p. 1153). (inference: End 0 to 1 reveals characters; verify, the printed direction looks reversed.)

---

## 6. Expressions

### 6.1 Math in number fields (p. 319)
Typing `2.0 + 4.0` into a number field enters 6.0. This is a one-time calculation, not a live link.

### 6.2 SimpleExpressions (pp. 319-321)
- Create: type **=** in the parameter's number field and press **Return**. An expression field appears below, a **yellow indicator** at left, and the current value is filled in. Or in the Spline Editor right-click the parameter > **Set SimpleExpression** (result is plotted).
- Language: **one-line Lua** with Fusion shorthand. Unidirectional (the driven parameter follows; the source is unaffected).
- **Pick whip:** drag the **+** button at the left of the expression field onto another control; inserts a reference you can then edit (unlike Connect To) (p. 321).
- Remove: right-click the parameter name > **Remove Expression**.
- Verify: open the Spline Editor to see the evaluated curve over time.
- Long expressions: widen the Inspector or paste from a text editor/Console (p. 320).

Syntax reference (all from the manual's table, pp. 319-320, plus the DirectionalBlur example p. 323):

| Expression | Meaning |
|---|---|
| `time` | Current frame number |
| `Merge1.Blend` | Value of input Blend on node Merge1 (ToolName.InputID) |
| `Merge1:GetValue("Blend", time-5)` | Value of another input sampled at another frame (5 frames earlier) |
| `sin(time/20)/2+.5` | Sine wave between 0 and 1; divide time to slow, multiply to speed up |
| `iif(Merge1.Blend == 0, 0, 1)` | Inline if-then-else: `iif(condition, then, else)` |
| `iif(Input.Metadata.ColorSpaceID == "sRGB", 0, 1)` | Bare `Input` means this node's input; equivalent to `self.Input`. Images expose members like `Depth`, `Width`, `Metadata` |
| `Point(Text1.Center.X, Text1.Center.Y-.1)` | Returns a Point (members `.X`, `.Y`): 1/10 image height below Text1's Center |
| `Text1.Center - Point(0,.1)` | Same result with Point arithmetic |
| `Text("Colorspace: "..(Merge1.Background.Metadata.ColorSpaceID))` | Returns Text; `..` concatenates; reads metadata of Merge1's Background image |
| `Text("Rendered "..os.date("%b %d, %Y").." at "..os.date("%H:%M").."\n on the computer "..os.getenv("COMPUTERNAME").." running "..os.getenv("OS").."\n from the comp "..ToUNC(comp.Filename))` | Slate text: Lua `os.date`, `os.getenv`, `\n` newline, `comp` variable (`comp.Filename`), `ToUNC()` |
| `sqrt(((Center.X-.5)*(self.Input.XScale))^2+((Center.Y-.5)*(self.Input.YScale)*(self.Input.Height/self.Input.Width))^2)` | Length from this node's Center control; `self.Input.XScale`, `.YScale`, `.Height`, `.Width`; `^` power |
| `atan2(.5-Center.Y , .5-Center.X) * 180 / pi` | Angle in degrees from Center; `pi` available |
| `iif(TypeNew==0, 0, 2)` | Drive a combo (Type) from a custom checkbox input |

Return type must match the parameter: Number for sliders, `Point(...)` for point inputs, `Text(...)` for text inputs.

(inference) Because the manual's Angle example converts `atan2` with `* 180 / pi`, SimpleExpression trig works in **radians** and `atan2` takes (y, x), unlike the Expression modifier (degrees, `atan2(x, y)` as printed). Verify before relying on it.

For more: Fusion Studio Scripting Guide and official Lua docs (p. 321).

### 6.3 Expression modifier (xref pp. 1772-1776)
- Right-click parameter > **Modify With > Expression**. Tabs: **Controls** (Number In 1-9 = `n1`..`n9`; Point In 1-9 = `p1x`..`p9x`, `p1y`..`p9y`; each can be set, animated, or connected), **Number Out** (formula for sliders), **Point Out** (two formulas: X and Y, for point controls), **Config** (Random Seed for `rand()`, 18 Show checkboxes, 18 Name fields).
- **Cannot access values from other frames** (use Calculation or SimpleExpression GetValue instead).

Functions: `n1..n9`, `p1x..p9x`, `p1y..p9y`, `time`, `pi`, `e`, `log(x)` (base 10), `ln(x)`, `sin/cos/tan(x)` (**x in degrees**), `asin/acos/atan(x)` (degrees), `atan2(x, y)` (degrees), `abs(x)`, `int(x)`, `frac(x)`, `sqrt(x)`, `rand(x, y)` (new value each frame, seeded by Random Seed), `rands(x, y, s)`, `min(x, y)`, `max(x, y)`, `dist(x1, y1, x2, y2)`, `dist3d(x1,y1,z1,x2,y2,z2)`, `noise(x)`, `noise2(x, y)`, `noise3(x, y, z)` (smooth Perlin), `if(c, x, y)` (x if c not 0).

Operators (reconstructed; the extracted table is garbled): `x+y`, `x-y`, `x<y`, `x>y`, `!x`, `-x`, `+x`, `x^y`, `x*y`, `x/y`, `x%y` (modulo), `x<=y`, `x>=y`, `x=y` and `x==y`, `x<>y` and `x!=y`, `x&y` and `x&&y`, `x|y` and `x||y`. Comparisons/logic return 1.0 or 0.0.

Manual examples: Number Out `p1y` (connect a Path to Point In 1 to follow its Y); `max(n1, n2) * cos(n3) + p1x`; Hotspot Point Out X = `n1` (n1 Bézier 0 to 1 over frames 0-29, looped), Y = `0.5 + sin(time*50) * 4` (printed "sin(time*50) 4"; operator lost in extraction).

### 6.4 Which linking tool

| Need | Use |
|---|---|
| Same curve on two params, edit either | Connect To (bidirectional) |
| Link to a static value | Publish, then Connect To |
| One-way link with math, other frames, text/metadata | SimpleExpression (pick whip) |
| Formula with many animatable/connectable inputs, noise, rand | Expression modifier |
| Two-operand math with per-operand time scale/offset | Calculation |
| Values from distance/angle between two points | Offset / Vector Result |

---

## 7. Custom controls: Edit Controls (pp. 322-325)

- Open: right-click the **node name in the Inspector** > **Edit Controls**.
- Dialog: **ID** menu (existing parameter or **New Control**), **Name**, **Type** (text field, **Number**, **Point**), **Page** list (Inspector tab, e.g. **Controls** = first tab), default and range settings, onscreen preview control option, **Input Ctrl** box (type-specific widget, e.g. **CheckboxControl**), **View Ctrl** list (onscreen controls), **Items** list with **Del** for combo options.
- Selecting an existing ID prompts **Replace**, **Hide**, or **Change ID**.
- Edits are stored **in the tool instance** (copy/paste carries them). To reuse in other comps, save the node settings (bins in Fusion Studio) or favorites (p. 323).
- Renaming a control keeps its internal ID, so existing expressions keep working (Center renamed "Blur Vector" still referenced as `Center`) (p. 324).
- The manual does not document UserControls table syntax, numeric range fields by name, or all Input Ctrl types beyond CheckboxControl.

DirectionalBlur example (pp. 323-325): drive Length and Angle from the Center onscreen control with the two SimpleExpressions in 6.2; then:
1. Edit Controls > ID **Center** > **Replace** > Name **Blur Vector** > Type **Point** > Page **Controls** > OK.
2. Hide Length: ID **Length** > Page Controls > Input Ctrl **Node** (as printed; inference: probably "None") > OK. Same for **Angle**.
3. Trim the Type menu: ID **Type** > Page Controls > select **Radial** in Items > **Del**; **Zoom** > **Del** > OK (leaves Linear and Centered).
4. New checkbox: Name **Center Blur**, ID **New Control**, Type **Number**, Page **Controls**, Input Ctrl **CheckboxControl** > OK. Then on Type: `iif(TypeNew==0, 0, 2)`. (inference: `TypeNew` is the new control's generated ID; confirm the ID shown in the dialog. Type index 2 = Centered implies original order Linear 0, Radial 1, Centered 2, Zoom 3.)

---

## 8. FusionScript (p. 325)
- Lua plus Python 2 and 3 "for some contexts"; libraries for common tasks.
- **Utility Scripts** (Fusion app context): File > Scripts. **Comp Scripts** (composition context): Script menu or the Console. **Tool Scripts** (tool context): tool context menu > Scripts.
- Other types: Startup Scripts, Scriptlibs, Bin Scripts, Event Suites, Hotkey Scripts, Intool Scripts, SimpleExpressions. Fusion Studio adds external/command-line and render-node scripting. **Fuses** and **ViewShaders** are script-based plugins.
- Docs: Help > Documentation > Fusion Scripting Documentation.

---

## AE-to-Fusion porting map
Manual-backed unless marked (inference).

| AE practice | Fusion implementation | Notes |
|---|---|---|
| Linear keys | Shift-L / Linear | New Bézier keys are already linear |
| Easy Ease (F9), temporal ease influence | Shift-S Smooth, then **Ease In/Out** (T) fields for handle length; Lock In/Out for symmetric | No %-influence/speed units documented; tune by curve shape |
| cubic-bezier(x1,y1,x2,y2) / custom graph | Drag Bézier handles in Spline Editor; Cmd-drag or Independent Handles for asymmetric | .setting handle syntax not in manual |
| Easing presets (easeInOutCubic, Bounce, etc.) | **Anim Curves** > Curve **Easing** > In/Out menus (Bounce named) | Normalized to duration; Scale/Offset set end/start values |
| Overshoot / spring / settle | Hand-key an overshoot key (Set Key, Shape Box to scale); Anim Curves Easing Out = Bounce; or Expression modifier (inference): Number Out `if(time<n2, 0, n1*(1 - e^(-(time-n2)/n3)*cos((time-n2)*n4)))` (n1 target, n2 start frame, n3 decay frames, n4 degrees/frame) | Expression trig in degrees |
| Hold keyframe | Step Out (O) on the key; Step In (I) on the next key; Set Key Equal To | See 3.7 note |
| wiggle(freq, amp) | **Perturb** (Speed ~ freq, Strength ~ amp, Wobble, Random Seed) or **Shake** (Smoothness, Min/Max, Lock X/Y); Insert on keyed params; Expression `noise(time*n1)` (inference: scale/offset noise range) | Perturb adds on top of keys |
| Wiggle only along a path | Insert > Perturb on Displacement | Jitters along path |
| loopOut("cycle") | **Set Loop** | Live instance |
| loopOut("pingpong") | **Ping-Pong** | |
| loopOut("offset") | **Relative Loop** | Cumulative |
| loopOut("continue") | **Gradient Extrapolation** | Continues last slope |
| loopIn(...) | **Set Pre-Loop** | |
| Repeat N times, then edit copies | **Duplicate** (count dialog) | Copies, not instances |
| posterizeTime(n) | Step In/Out on keys for held poses; or SimpleExpression `Tool:GetValue("Input", time - time % n)` reading another animated param (inference, Lua `%`); or Time Stretcher Source Time keys with steps | Expression modifier has `int()`, but cannot read other frames |
| valueAtTime / time offset / delay | SimpleExpression `Tool:GetValue("Input", time-5)`; Calculation Time Offset/Scale; Offset modifier time tab | |
| Stagger layers | Keyframes Editor **T Offset** on selected keys; Cmd-drag duplicate keys; Anim Curves **Time Offset** (fraction); GetValue with per-node frame offsets | |
| Stagger text characters (text animators) | **Follower** modifier: Order + Delay Type | Values in Follower tabs must be keyed |
| Counter (number count-up) | SimpleExpression on Text+ Styled Text returning `Text(...)`, e.g. `Text(string.format("%.0f", Merge1.Blend*100).."%")` (inference: assumes Lua `string` library is exposed; the manual only shows `os`) or **Time Code** (Frms only) / **Text Timer** | |
| Typewriter | Text+ **Write On** range; **Follower** for per-character styling | See Write On note |
| Time remap | **Time Stretcher** Source Time spline (Bézier, one key at 0.0 when added) | Time Speed for constant changes |
| Auto-Orient along path | Angle > Connect To > Path > Heading (+ Heading Offset) | |
| Speed graph for position | Polyline path **Displacement** spline | |
| Separate dimensions | **XY Path** | |
| Pick whip / parenting params | SimpleExpression pick whip, Connect To, Publish | |
| Slider/checkbox controls on null | Edit Controls New Control (Number + CheckboxControl, Point) or Expression modifier Config names | |
| Audio-driven | Fairlight Animator; MIDI Extractor Beat mode | |
| Template duration-safe animation | Anim Curves (Source Duration/Transition), KeyStretcher, Keyframe Stretcher node, Resolve Parameter | |

---

## Gotchas and non-obvious behavior

1. **New Bézier keys are linear.** Smoothness needs Shift-S or Autosmooth prefs (p. 283; xref p. 387).
2. **Auto-keying**: once one key exists, every value change at another frame writes a key. To tweak without keying, remove animation or change on an existing key frame (p. 277).
3. **Remove [param] may not delete the spline** if another parameter is Connected To it; deleting all keys leaves an empty spline (pp. 275, 279).
4. **Spline types don't mix** for copy/paste (p. 281). Pick B-Spline/Cubic via Modify With **before** keying (p. 275).
5. **Step In vs Step Out** wording differs between body text and captions; test on the curve (p. 289).
6. **Loops are live, Duplicates are copies.** Loop runs to end of Global range unless a later key ends it; remove by selecting the originating keys and clicking Loop again (pp. 290-291).
7. **Keyframes Editor ruler:** dragging anywhere but the playhead scales the view; Cmd-Option-click jumps (p. 253).
8. **Trimmed effect segments act disabled** outside their range; good for render savings, surprising if a node "stops working" (p. 255).
9. **T Scale** in the Spline Editor scales relative to the **playhead**, not the first key (p. 282). Value field with multiple keys sets all to one value (p. 282).
10. **Displacement end key is fixed at 1.0**; Option-click adds a path point without a timing key; unlocked points do not affect timing (pp. 304, 309-310).
11. **XY Path has no Displacement**; speed is the key timing (p. 306). Default Center animator is Polyline Path unless Point With = XY Path.
12. **Masks auto-animate their shape.** Before using a mask as a path, Remove Polygon1Polyline, Publish, and delete Path1's automatic Displacement key (pp. 300-301).
13. **No motion paths on 1D values** (p. 298).
14. **Connect To is bidirectional; SimpleExpression is one-way** (pp. 317, 321). Static values must be Published before they appear in Connect To (xref p. 1793).
15. **Expression modifier trig is degrees and cannot read other frames**; SimpleExpressions can (GetValue) and appear to use radians (pp. 319-323; xref pp. 1772-1774).
16. **SimpleExpressions are one line**; use `\n` for line breaks inside Text output (pp. 319-320).
17. **Edit Controls changes live on that tool instance only** until saved as settings/macro (p. 323).
18. **Import Spline replaces** existing animation; export "Key Points" loses curve shape (linear) (p. 295).
19. **Reduce Points 100 = no change** (p. 284). **Perturb cannot smooth**; use Smooth Points -Y Dialog (xref pp. 1764, 1789).
20. **Anim Curves Clip Low/High clamp to 0-1**; Time Offset is a fraction of duration, not frames (xref p. 1762).
21. Edit-page **clip** markers are read-only in Fusion and absent from the Spline Editor (p. 262).

## Recipes / workflows

**R1. Smooth ease-in/out move (AE Easy Ease)** (pp. 251, 283, 294)
1. Transform > Center: Keyframe at frame A, move playhead to B, drag Center (Path auto-created).
2. Spline Editor: enable Path1 **Displacement**; select both keys; **Shift-S**.
3. Press **T**, adjust Ease In/Out fields (Lock In/Out for symmetry). For a harder ease, Cmd-drag individual handles.

**R2. Hold then jump (stepped animation)** (p. 289): key values, select keys, press **O** (Step Out) so each value holds to the next key; check curve.

**R3. Infinite spin / cycle** (p. 290): Angle key 0 at frame 0, 360 at frame 24, select both > Set Loop (repeats); for continuous accumulation use **Relative Loop**; for back-and-forth **Ping-Pong**; for pre-roll add **Set Pre-Loop**.

**R4. Constant drift beyond last key** (p. 292): select last two keys > right-click > **Gradient Extrapolation**.

**R5. Retime a block of keys** (pp. 258, 292-293): Keyframes Editor Time Stretch box, or Spline Editor Modes > Time Stretching (white bars), or T Offset/T Scale fields; Shape Box (Shift-B) to also scale values.

**R6. Organic secondary motion** (p. 316): keyframe Center into a figure-8; right-click Center X > Modify With > **Perturb**; Modifiers tab: set **Strength**, **Wobble**, **Speed** while playing.

**R7. Object follows a drawn curve with controlled speed** (pp. 300-303): see 4.3 step 3; key **Displacement** 0.0 at start, 1.0 at end; shape speed with Displacement handles; Angle > Connect To > Path > **Heading** for auto-orient.

**R8. Pause mid-path** (p. 311): on the Displacement spline Cmd-drag a locked key horizontally to create an unlocked copy (flat section = pause).

**R9. Pulsing size** (p. 319): Size field type `=` Return, enter `sin(time/20)/2+.5` (scale/offset as needed, e.g. `0.8 + 0.2*sin(time/5)`); check in Spline Editor.

**R10. Offset follower text** (p. 320): Text2 Center = `Point(Text1.Center.X, Text1.Center.Y-.1)` or `Text1.Center - Point(0,.1)`.

**R11. Delayed echo of another node** (p. 319): `Merge1:GetValue("Blend", time-5)`; chain with different offsets for staggered copies.

**R12. Burn-in slate** (p. 320): Text+ Styled Text `=Text("Rendered "..os.date("%b %d, %Y").." at "..os.date("%H:%M").."\n from the comp "..ToUNC(comp.Filename))`.

**R13. Blur that shrinks as text grows (Calculation)** (xref pp. 1766-1768): Text+ Size keyed 0.05 (f0) to 0.50 (f100); Blur > Blur Size > Modify With > Calculation; First Operand > Connect To > Text 1 > Size; Operator **Multiply**; Second Operand **100**; Time tab First Operand Time Scale **-1.0**, Time Offset **100**.

**R14. Bouncing drop, duration-safe** (xref p. 1763): key text top to bottom (Path created); Modifiers tab right-click Displacement > **Insert > Anim Curves**; Source **Duration**; Curve **Easing**, Out **Bounce**; Scale to taste; Time Scale 2.0 to double speed.

**R15. Duration-safe transition** (xref pp. 1763, 1794): Transform Size > Modify With > Anim Curves on both MediaIns, **Invert** one, Curve Easing; or Resolve Parameter on the dissolve control; save macro as a Transition template.

**R16. Character stagger** (xref pp. 1165-1166): Text+ Styled Text right-click > **Follower**; key the desired properties (e.g. offset/opacity) in the Follower's text tabs; Timing: Order **Left to right**, Delay Type **Between Each Character** = frames per char (or Between First and Last Character for fixed total).

**R17. Checkbox driving a menu** (p. 325): Edit Controls new Number control with CheckboxControl, then `iif(NewID==0, 0, 2)` on the menu input.

## Scripting and automation hooks

- SimpleExpression entry: `=` in a number field + Return. Removal: context **Remove Expression**. Spline Editor: **Set SimpleExpression**.
- SimpleExpression identifiers from the manual: `time`, `self`, `self.Input`, `Input`, `comp`, `comp.Filename`, `ToolName.InputID` (e.g. `Merge1.Blend`, `Text1.Center`, `Text1.Center.X`, `Merge1.Background`), `Tool:GetValue("InputID", frame)`, `iif(c, a, b)`, `Point(x, y)`, `Text(str)`, `..` concat, `ToUNC()`, `os.date()`, `os.getenv()`, `sqrt()`, `sin()`, `atan2()`, `pi`, `^`. Image members: `.Width`, `.Height`, `.Depth`, `.XScale`, `.YScale`, `.Metadata` (e.g. `.Metadata.ColorSpaceID`).
- Input IDs named in this slice: DirectionalBlur `Center`, `Length`, `Angle`, `Type`; Merge `Blend`, `Background`; Text `Center`; generic `Input`. Spreadsheet row naming `Blur1BlurSize` = tool name + input ID.
- Expression modifier variables: `n1`..`n9`, `p1x`..`p9x`, `p1y`..`p9y`, `time`, `pi`, `e`; Custom Poly adds `px`, `py`, `disp`, `index`, `num`, `getx()`, `gety()`, `getx_at()`, `gety_at()`, `get2x/y()`, `get3x/y()`.
- Modifier menu names: Animate, BezierSpline, Modify With > B-Spline / Cubic Spline / Natural Cubic Spline / XY Path / Perturb / Shake / Anim Curves / Calculation / Expression / Gradient Color / KeyStretcher / MIDI Extractor / Probe / Offset / Vector / CoordTransform Position / Tracker; Path; Publish; Resolve Parameter; Insert > (modifier); Connect To > (Tool) > (Input), e.g. Connect To > Path > Heading, Connect To > Polygon1Polyline.
- Files: splines `.spl` (Export Samples / Key Points / All Points; Import Spline); shapes and node settings `.setting` (Settings > Save As / Load; drag into Node Editor); polyline import FXF, SSF, Nuke shapes. Transition templates: `$TEMPLATE_MAC_OS_PATH/Transitions`, `$TEMPLATE_MAC_USER_PATH/Transitions`, `$TEMPLATE_WIN_OS_PATH\Transitions`, `$TEMPLATE_WIN_USER_PATH\Transitions`.
- Preferences: Fusion > Fusion Settings > Defaults > **Number With**, **Point With**; Splines > **Autosmooth**, **B-Spline Modifier Degree**; Spline Editor > **Independent Handles**, **Show Key Markers**, **Autosnap Points**; Timeline > **Filter to Use**, **Tools Display Mode**.
- Script locations: File > Scripts (Utility), Script menu / Console (Comp), tool context menu > Scripts (Tool).
- Keyboard shortcuts:

| Key | Action |
|---|---|
| F7 | Toggle Keyframes Editor |
| F11 | Modifiers tab (xref p. 1767) |
| Cmd-Option-click | Jump playhead (Keyframes Editor track area) |
| Shift-G | Marker List |
| Cmd-R / Cmd-F | Zoom/Scale to Rectangle / Scale to Fit (Spline Editor) |
| + / - | Zoom graph |
| Cmd-K | Set Key at playhead |
| Cmd-A | Select all points |
| Cmd-click | Toggle key selection (Spline Ed.) / discontiguous (Keyframes Ed.) |
| Option-drag | Constrain key to one axis |
| Up/Down (Shift) | Nudge value (larger) |
| , / . | Nudge key time left / right |
| Delete / Backspace | Delete keys (or selected marker) |
| Cmd-C / Cmd-V | Copy Points / Paste Points/Value |
| Cmd-drag keys | Duplicate keys |
| Cmd-drag handle | Break Bézier handles temporarily |
| Shift-S / Shift-L | Smooth / Linear |
| I / O | Step In / Step Out |
| V | Reverse |
| Shift-B | Shape Box |
| T | Ease In/Out |
| W + drag | B-Spline tension |
| Cmd-I | Insert and Modify (polyline) |
| Tab | Cycle viewer controls (select path) |
| Option-click path | Add path point without Displacement key |
| Cmd-drag segment edge | Hold first/last frame (Loader) |
