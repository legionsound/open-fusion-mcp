<!-- nodes-warp-modifiers-vr.md part 1 of 2; index: nodes-warp-modifiers-vr.md -->
# VR Nodes, Warp Nodes and Modifiers (Fusion 21.1)
Scope: manual pp. 1716-1802 (Ch. 63 VR Nodes, Ch. 64 Warp Nodes, Ch. 65 Modifiers, Menu Descriptions stub). Use when: driving any parameter procedurally (wiggle, easing, linking, audio/MIDI/pixel-driven, tracking, duration-aware templates), warping/distorting 2D images, or patching/converting/stabilizing 360/VR footage.

## Mental model

1. **Modifiers are parameter drivers, not nodes.** A modifier attaches to one input and replaces or feeds its value; its controls appear in the Inspector's **Modifiers** tab (shortcut F11, p. 1767), not on the node. They range from motion paths and links to expressions, procedural noise, external data (audio, MIDI, pixels) and Fuses (p. 1761).
2. **How you attach them matters.** Right-click a parameter (Inspector) or its on-screen control (viewer) > **Modify With > ...**. Not every modifier appears for every parameter type: some work only on points, gradients or polylines (p. 1761). A few live outside Modify With: **BezierSpline** (top-level, same as Animate), **Path** (on position controls), **Publish**, **From Image** (right-click a Gradient bar), **Custom Poly** (Insert on "Right-click here for shape animation"), **Resolve Parameter**.
3. **Modify With vs Insert.** The manual uses **Insert > Anim Curves** on a Path's Displacement and **Insert > Perturb** on an animated crosshair (pp. 1763, 1789). Insert stacks a modifier on a control that is already animated or modified, so the existing animation keeps working underneath (inference from those examples).
4. **Animation curves are modifiers too.** Keyframing a number creates a **Bézier Spline**. B-Spline, Cubic Spline and Natural Cubic Spline are alternatives with no Controls tab; you edit them in the Spline Editor (pp. 1764-1769, 1784).
5. **Point animation has two spline flavors.** A **Path** is a spatial polyline plus a temporal **Displacement** spline (0.0 = path start, 1.0 = end). An **XY Path** is separate X and Y value splines with no keyframes on the on-screen path (pp. 1788, 1799).
6. **Linking.** **Connect To** only lists animated or published parameters. Static controls must be **Published** first (p. 1793). Use **Calculation** or **Expression** when the ranges differ (a direct link is AE's pick whip).
7. **Time access.** **Expression cannot read other frames** (p. 1772). Use **Calculation** (Time tab) or **Offset** (Time tab) for time-offset or time-scaled reads (AE `valueAtTime`).
8. **Randomness: Shake vs Perturb vs Expression.** Shake sets an absolute Min/Max range with Smoothness. Perturb adds Perlin wobble (Strength/Wobble/Speed) around a center Value, works on polylines, meshes and gradients, and can sit on top of existing animation. Expression offers `rand`, `rands` and `noise`.
9. **Duration-aware templates.** **Anim Curves** (Source = Transition/Duration), **Key Stretcher** and **Resolve Parameter** make Fusion animation follow Edit/Cut page trims (pp. 1761, 1780, 1794).
10. **Warp nodes are 2D pixel remappers.** Most have orange Input + blue Effect Mask. Displace needs a green map. Vector Distortion takes an optional green Distort input. The mask is applied after processing. Corner/Perspective Positioner **do not concatenate**, so each pass adds softness (p. 1751).
11. **VR nodes are Studio-only** (Fusion Studio / DaVinci Resolve Studio). Patch workflows always go extract, fix flat, re-apply with **identical rotation / angle-of-view settings** (copy-paste the node) (pp. 1719-1721).
12. **Coordinates:** Center-type controls are normalized with 0.5, 0.5 = image center (Dent, Drip, Vortex defaults, pp. 1735, 1740, 1756). Where a modifier works in distances, **Image Aspect** = width/height compensates for non-square frames (Offset, Vector Result, pp. 1786, 1798).

---

## Modifiers (Ch. 65, pp. 1760-1800)

**Not in this slice:** the **Follower** and the other Text+/Text3D text-specific modifiers ("covered in their nodes' sections", p. 1761). Key Stretcher controls are in the Miscellaneous Nodes chapter (p. 1780). Tracker controls are in the Tracking Nodes chapter (p. 1797). The chapter has **no "Stabilizer" modifier**. For single-point stabilization use Track > **Steady Position**, and for 360 footage use the Spherical Stabilizer node.

### Quick chooser

| Need | Use | Not |
|---|---|---|
| Keyframe animation with handles | Bézier Spline (default) | - |
| Smooth auto-curve through keys, no handles | Natural Cubic / Cubic Spline | B-Spline (does not pass through key values) |
| Very soft curve, weighted | B-Spline (W + drag) | - |
| Ease presets / bounce / mirror / invert without hand-editing splines; duration-responsive | Anim Curves | manual spline edits |
| Link A to B with remapped range or math | Calculation (2 operands, time-shiftable) | direct Connect To |
| Arbitrary math of up to 9 numbers + 9 points | Expression | Calculation |
| Value from another frame | Calculation / Offset Time tab | Expression (current frame only) |
| Random jitter, absolute range | Shake | - |
| Organic wobble on an existing animation, polyline, mesh or gradient | Perturb (Insert) | Shake |
| Drive from pixel color/luma | Probe | - |
| Drive from audio | Fairlight Animator | - |
| Drive from MIDI notes/CC/beat | MIDI Extractor | - |
| Value from angle/distance between two points | Offset Angle / Offset Distance | - |
| Orbit / polar offset of a point | Vector Result | - |
| Position from 3D hierarchy (world position) | CoordTransform Position | - |
| Map a gradient over time to a color/value | Gradient Color | - |
| Gradient sampled from an image line | From Image | - |
| Per-point procedural polyline edits | Custom Poly | - |
| Track a point straight onto a parameter | Track (Tracker modifier) | Tracker node (multi-pattern, match move) |
| Make a static control linkable | Publish | - |
| Edit-page transition that follows trims | Resolve Parameter (or Anim Curves Source = Transition) | - |
| Title keyframes that stretch with clip trim | Key Stretcher / Anim Curves Source = Duration | - |

### After Effects idiom map (inference: the mapping is editorial; controls are from the manual)

| AE idiom | Fusion equivalent |
|---|---|
| `wiggle(freq, amp)` | **Perturb**: Strength ≈ amp, Speed ≈ freq, Wobble = roughness, Random Seed. Or **Shake** (Min/Max/Smoothness). Or Expression `noise(time*k)` |
| Easy Ease / easing presets / bounce | **Anim Curves**: Curve = Easing with In/Out menus (Bounce is listed, p. 1763). Or Bézier keys with Shift-S / Ease In/Out dialog |
| `loopOut("cycle")` | Loop the spline in the Spline Editor (p. 1776 Ex. 3). Or Expression with `%`/`frac(time/N)` |
| `loopOut("pingpong")` / yo-yo | **Anim Curves > Mirror** (whole-duration forward then back). **Gradient Color > Repeat = Ping Pong** for gradients |
| Pick whip | **Connect To** (Publish static controls first) |
| `linear()`/`ease()` remap, `* 100` | **Calculation** (Multiply/Add...), **Anim Curves** Scale/Offset, **Probe** Scale Input + Black/White Value |
| `valueAtTime(time - d)` / echo | **Calculation** or **Offset** Time Offset/Time Scale |
| `sampleImage()` | **Probe** (pixel or rectangle; Average/Min/Max) |
| Convert Audio to Keyframes | **Fairlight Animator** (with High/Low Pass in Hz) |
| Text Animator + Range Selector | **Follower** modifier on Text+ (not in this slice) |
| Track Motion > apply to null / effect point | **Track** modifier (Tracker Position) |
| Stabilize (single point) | **Track** modifier (Steady Position / Unsteady Position) |
| `toComp()` / world position | **CoordTransform Position** (3D) |
| Auto-Orient along path | Connect the angle to **Path Heading**, then trim with **Heading Offset** |
| Separate Dimensions | **XY Path** |
| Time-remap an animation / stretch it | **Anim Curves** Time Scale / Time Offset |
| MOGRT duration-responsive keyframes | **Anim Curves** (Source), **Key Stretcher**, **Resolve Parameter** |
| Corner Pin | **Corner Positioner** |
| Optics Compensation | **Lens Distort** |
| Displacement Map / Turbulent Displace | **Displace** (+ Fast Noise map) |
| Polar Coordinates | **Coordinate Space** |
| Twirl | **Vortex** |
| Bulge / Spherize | **Dent** |
| Wave Warp / Ripple | **Drip** |
| Mesh Warp / Reshape | **Grid Warp** |

---

### Anim Curves (pp. 1761-1763)
Dynamically retimes, reshapes and rescales an animation. It outputs a normalized 0→1 ramp across the comp (or transition/clip) duration, then shapes and scales it. Its main job is making Fusion templates stretch correctly when trimmed on the Edit/Cut page.
- Apply: right-click the param > **Modify With > Anim Curves**. On a Path: Modifiers tab, right-click **Displacement** > **Insert > Anim Curves**. The animation is then normalized to the comp duration (p. 1763).
- On a plain parameter (e.g. Transform Size) it animates the value **0 → 1 over the duration** (p. 1763).
- **Curve Shape**
  - **Source**:
    - **Transition**: auto-selected when the comp was created from an Edit page transition. Timing follows transition duration changes.
    - **Duration**: for comps made from an Edit page clip. Timing follows clip trims.
    - **Custom**: shows an **Input** dial for manual timing (p. 1762).
  - **Input**: visible only when Source = Custom. It changes the input keyframe value.
  - **Curve**:
    - **Linear** (default)
    - **Easing**: shows **In** and **Out** interpolation menus. Bounce is one Out option (p. 1763).
    - **Custom**: opens a mini Spline Editor.
  - **Mirror**: plays forward to the end, then returns to the start. The forward half runs twice as fast because the second half of the comp is used for the reverse.
  - **Invert**: flips the curve upside-down so values start high and end low.
- **Scaling**
  - **Scale**: a multiplier on the keyframe values ("ending value"). Set it while viewing the last frame.
  - **Offset**: added to the keyframe values ("starting value"). Set it while viewing the first frame.
  - **Clip Low**: output never below 0.0.
  - **Clip High**: output never above 1.0.
  - The output works as keyvalue × Scale + Offset (inference from the descriptions).
- **Timing**
  - **Time Scale**: stretches or squishes the animation. 1.0 = runs for the comp duration, 2.0 = twice as fast (p. 1763).
  - **Time Offset**: a delay as a **fraction of total duration**. 0.0 = none, 0.5 = starts midway.
- Tip: to view the resulting curve, select the parameter name in the Spline Editor header. It updates live (p. 1763).

### Bézier Spline (pp. 1764-1765)
The default animation spline for numbers. It is created automatically when you keyframe or choose **Animate**. The context menu lists **BezierSpline** separately from Modify With. Selecting it adds a key at the current frame. It has no Controls tab; edit it in the Spline Editor.
- **Shift-S** = smooth the selected points. **Shift-L** = linear. Both are also in the context menu (Smooth / Linear).
- Context menu **Smooth Points -Y Dialog**: Savitzky-Golay convolution smoothing of the selected points (useful on dense tracked/recorded data).
- Context menu **Ease In/Out...**: numeric ease in/out via number-field virtual sliders in the Spline Editor.

### B-Spline (p. 1765)
Apply with **Modify With > B-Spline**. It has no Controls tab.
- Gotcha: the curve **does not pass through key values**. In the manual's example, a key of 0 produces a spline value of 0.33 because of B-spline weighting.
- Weight/tension: select point(s), **hold W** and drag the mouse left/right. This works on multiple selected points.

### Cubic Spline (p. 1769) and Natural Cubic Spline (p. 1784)
Animation splines with no Controls tab. You edit them in the Spline Editor. Cubic splines have **no handles** and auto-fit a smooth curve through the control points (p. 1784). Both entries say to apply via **Modify With > Natural Cubic Spline**. The Cubic Spline entry repeats this wording, probably a documentation carry-over (inference).

### Calculation (pp. 1765-1768)
Makes an indirect link between parameters: two operands combined by one math operator, each readable at a shifted or scaled time. Use it when one parameter's range or scope doesn't fit the other. The manual calls Expression "a more flexible version" except that **operand timing is far easier here** (p. 1766).
- **Calc tab**
  - **First Operand**, **Second Operand**: sliders that you set manually, animate, or **Connect To** other parameters.
  - **Operator**: Add; Subtract (First - Second); Subtract (Second - First); Multiply; Divide (First / Second); Divide (Second / First); Average; First only; Minimum; Maximum.
- **Time tab**
  - **First/Second Operand Time Scale**: multiplies the frame number. 1 = same frame. Example: operand animates 1→50 over frames 0-10, and Scale 0.5 returns 25 at frame 10.
  - **First/Second Operand Time Offset**: reads the operand at an offset. **+10 = 10 frames forward, -10 = 10 frames back** (p. 1767).
- Reverse-read trick (p. 1768): Time Scale **-1.0** reads frame -t. Add Time Offset **100** (in a 0-100 comp) to read frame 100 - t.

### CoordTransform Position (pp. 1768-1769)
Calculates an object's **current world position** after downstream 3D transforms (for example, an image plane at 1,2,1 ending up at 10,20,5 after parent transforms). Add it to any XYZ coordinate control via **Modify With > CoordTransform Position**.
- **Target Object**: the 3D tool that produces the original coordinates. Drag the node in, pick it via right-click, or type its name.
- **SubID**: targets a sub-element, e.g. one character of Text 3D or one copy from Duplicate 3D.
- **Scene Input**: the 3D tool that outputs the scene containing the object at its new location.

### Custom Poly (pp. 1770-1771)
Per-point expressions on a **polygon mask or path**, like the Custom Tool / pCustom tools. It can reposition existing points or replace them with a new set. Apply by right-clicking **"Right-click here for shape animation"** > **Insert > Custom Poly**. Controls appear in the Polygon's Modifiers tab.
- **Controls tab**: point input(s) and number variables. The default is 1 point and 4 numbers, expandable to **9 each** via the Config tab.
- **Polyline tab**
  - **Connect Source Polyline here**
  - **Show View Controls**
  - **Number of Points**: output point count. **0 = use the source point count**.
  - **Poly Expression X / Y**
- Variables: the same as Expression (`n1..n9`, `p1x..p9x`, `p1y..p9y`, math functions) plus the following:
  - `px`, `py`: the current source point
  - `disp`: the point's displacement along the polyline (0.0 start, 1.0 end)
  - `index`: zero-based point index
  - `num`: output point count
  - `getx(disp)`, `gety(disp)`: sample anywhere on the polyline
  - `getx_at(disp, time)`, `gety_at(disp, time)`: sample at other times
  - `get2x/get2y()`, `get3x/get3y()`, `get2x_at()`, `get3x_at()` etc.: the 2nd and 3rd source polys
- Manual example, a blend toward a second poly by `n1`: X `px*(1-n1)+n1*get2x(disp)`, Y `py*(1-n1)+n1*get2y(disp)`.
- **Config tab**: how many Points/Numbers to show (max 9) and custom names.

### Expression (pp. 1772-1776)
The most flexible driver: 9 number inputs + 9 point inputs feeding a formula. **It can only read the current frame** (p. 1772). The return type follows the modified control. On a slider, the **Number Out** formula is used. On a point (e.g. Center), **Point Out** is used. Apply with **Modify With > Expression**. (Simple per-parameter expressions also exist; this chapter only mentions them.)
- **Controls tab**: 9 number controls (`n1`-`n9`) and 9 point controls (`p1x`-`p9x`, `p1y`-`p9y`). You can set, animate, Connect To, or chain each into other Expressions/Calculations.
- **Number Out tab**: one formula field.
- **Point Out tab**: two fields, top = X formula, bottom = Y formula.
- **Config tab**
  - **Random Seed**: seeds `rand()`. The same seed gives the same value at the same frame.
  - **Show Number/Point x**: 18 checkboxes that show or hide each input.
  - **Name for Number/Point x**: 18 fields that relabel the inputs.

Functions (p. 1774-1775). **All trig uses degrees.**

| Syntax | Meaning |
|---|---|
| `n1`..`n9` | Number inputs |
| `p1x`..`p9x`, `p1y`..`p9y` | Point inputs X / Y |
| `time` | current frame number |
| `pi`, `e` | constants |
| `log(x)` / `ln(x)` | base-10 / natural log |
| `sin cos tan (x)` | x in **degrees** |
| `asin acos atan (x)`, `atan2(x, y)` | results in **degrees** |
| `abs int frac sqrt (x)` | abs, integer part, fractional part, square root |
| `rand(x, y)` | random in [x, y], new value **every frame**, seeded by Config > Random Seed |
| `rands(x, y, s)` | random in [x, y] with explicit seed s |
| `min(x, y)`, `max(x, y)` | min / max |
| `dist(x1, y1, x2, y2)` | 2D distance |
| `dist3d(x1,y1,z1,x2,y2,z2)` | 3D distance |
| `noise(x)`, `noise2(x, y)`, `noise3(x, y, z)` | smooth Perlin noise |
| `if(c, x, y)` | x if c ≠ 0, else y |

Operators (p. 1775). They return 1.0/0.0 for comparisons and logic. In the extracted text some glyphs are lost. The `*`, `/`, `<`, `<=` forms below are reconstructed from their descriptions (inference):
`x+y`, `x-y`, `x*y`, `x/y`, `x%y` (modulo), `x^y` (power), `-x`, `+x`, `!x` (1 if x = 0), `x<y`, `x>y`, `x<=y`, `x>=y`, `x=y` / `x==y`, `x<>y` / `x!=y`, `x&y` / `x&&y`, `x|y` / `x||y`.

Manual examples (p. 1776):
1. A number equal to a path's Y: connect the Path to Point In 1, then Number Out `p1y`.
2. Number Out: `max(n1, n2) * cos(n3) + p1x`.
3. Lissajous-style hotspot:
   - Set up a black Background and a Hotspot (Size 0.08, Strength max). Put an Expression on its Center.
   - Animate `n1` 0→1 over frames 0-29 on a Bézier Spline and loop it in the Spline Editor.
   - Point Out: X `n1`, Y `0.5 + sin(time*50)/4`. (The "/" was lost in extraction, which is an inference. Try it with motion blur.)

### From Image (pp. 1776-1777)
**Gradients only** (e.g. Background gradient). It samples colors along a line in an image and builds gradient stops from them. It is not in Modify With: right-click a **Gradient bar** > **From Image**.
- **Image to Scan**: drop a node here.
- **Start X/Y**, **End X/Y**: endpoints of the sample line. You can also drag them in the viewer.
- **Number of Sample Steps**: how many color stops are created.
- **Edges** (behavior when the line runs past the frame):
  - **Black**
  - **Wrap**
  - **Duplicate**
  - **Color**: a user color
- Tip: you can remove the modifier afterward. The generated gradient stays and becomes hand-editable (p. 1777).

### Fairlight Animator (p. 1778)
Drives any numeric control from Fairlight audio analysis of timeline clips or Media Pool sources. Controls are in the Modifiers tab.
- **Parameter tab**
  - **Clip Name**: read-only display.
  - **Analysis**: which Fairlight parameter drives the value.
  - **Scale**
  - **Offset**
  - **High/Low Pass Filter**: in **Hz**. To animate on bass only, **lower the low-pass** slider.
- **Time tab**
  - **Time Scale**: a frame multiplier.
  - **Time Offset**: slips the audio start frame.

### Gradient Color (pp. 1779-1780)
Maps a custom gradient onto a frame range to drive a color or value. Apply with **Modify With > Gradient Color**.
- **Gradient**: add, move and remove stops. Stop colors and positions are animatable. From Image can be applied to it.
- **Gradient Interpolation Method**: the default is linear in **RGB**. Choose another color space if the in-between colors look wrong.
- **Repeat** (behavior at the borders when shifted by Gradient Offset):
  - **Once**: holds the end colors.
  - **Repeat**: wraps, giving a hard jump.
  - **Ping Pong**: mirrors, giving a smooth fold.
- **Gradient Offset**: pans through the gradient (animate it for manual control).
- **Start Time / End Time**: frames. **If both are 0, the modifier returns the gradient's start value.** You get the same effect with Repeat = Once plus an animated Offset.

### Key Stretcher (p. 1780)
Apply with **Modify with > KeyStretcher** on an animated parameter. Keyframes stretch when a title template is trimmed on the Edit/Cut page. The controls are documented in the Miscellaneous Nodes chapter.

### MIDI Extractor (pp. 1781-1784)
Drives a control from a MIDI file. Apply with **Modify With > MIDI Extractor**. **All MIDI Extractor times are in seconds** (p. 1783).
- **Controls tab**
  - **MIDI File**: file browser.
  - **Time Scale**: 1.0 = normal speed, 2.0 = double.
  - **Time Offset**: syncs MIDI timing to Fusion timing.
  - **Result Offset, Result Scale**: the default output is 0-1 (Pitch Bend: -1 to 1). Scale widens it (e.g. ×0.0-2.0) and Offset adds a base value.
  - **Result Curve**: a gamma-like curve on the result that keeps full scale. The linear default maps velocity 127 → 1.0 and 63 → ~0.5.
  - **Mode**:
    - **Beat**: regular pulses from the file's tempo map, including tempo changes. It uses no messages.
    - **Note**
    - **Control Change**
    - **Poly AfterTouch**
    - **Channel AfterTouch**
    - **Pitch Bend**
  - **Combine Events** (when events coincide): Most recent, Oldest still active, Highest, Lowest, Average, Sum, Median.
  - **Beat (Quarters)** (Beat mode only): beat interval in quarter notes. 1.0 = every quarter.
  - **Note Range** (Note / Poly AfterTouch modes): e.g. **35-36 isolates the kick in a GM drum track**.
  - **Pitch Scale** (Note mode only): 1.0 = the result varies 0-1 over the full pitch range.
  - **Velocity Scale** (Note mode only): 1.0 = 0-1 over the velocity range. It is added to the Pitch Scale result.
  - **Control Number** (Control Change mode only): the CC number.
  - **Envelope** (Note and Beat modes only):
    - **Pre-Attack Time/Level**: the ramp-up before the event.
    - **Attack** Time/Level
    - **Decay**, **Sustain**: Notes only.
    - **Release**: the ramp-down after the event ends.
    - Beats are instantaneous and go straight to Release. **Set Release > 0 in Beat mode or you get almost no visible beat** (p. 1783).
- **Channels tab**: 16 channel checkboxes that isolate an instrument.
- MIDI background:
  - Data is 7-bit (0-127) and is represented as 0-1 in Fusion. Middle C = 60.
  - There are 128 CCs.
  - Pitch Bend is 14-bit and maps to -1 to 1.
  - Channel AfterTouch is per channel. Poly AfterTouch is per note.

### Offset: Angle, Distance, Position (pp. 1785-1788)
Three modifiers with identical Inspectors. Apply with **Modify With > Offset** (the manual's example uses **Modify With > Offset Distance**).
- **Offset Angle**: outputs **0-360**, the angle between two positional controls.
- **Offset Distance**: outputs the distance between two positions.
- **Offset Position**: outputs an X/Y point. It is the point equivalent of Calculation.
- **Offset tab**
  - **Position X/Y** and **Offset X/Y**. On screen, the Position is a crosshair and the Offset is an X. Both are animatable and connectable.
  - **Flip Position Horizontal/Vertical**
  - **Flip Offset Horizontal/Vertical**
  - **Mode**: Offset; Difference (Position - Offset); Difference (Offset - Position); Average; Use Position Only; Use Offset Only; Maximum; Minimum; Invert Position; Invert Offset; Invert Sugar (sic); Random Offset.
  - **Image Aspect**: width/height (500×500 → 1; 500×1000 → 2). The default comes from the frame format preference. You can also use it to fake an aspect.
- **Time tab**
  - **Position Time Scale**: 0.5 = the value at half the current frame time.
  - **Position Time Offset**: the manual says "10 is 10 frames back". This is the **opposite sign convention from Calculation's text** (p. 1787 vs p. 1767), so verify by testing.
  - **Offset Time Scale**, **Offset Time Offset**
- Example (pp. 1787-1788): text Size driven by the distance from a fixed X to the text's animated path:
  1. Put **Modify With > Offset Distance** on Text Size.
  2. Place the X at bottom center.
  3. Right-click Position > **Connect To > Path1 Position**.
  4. The text shrinks near the middle of the path and grows at the ends.

### Path (pp. 1788-1789)
The default motion path for points. It has a spatial polyline in the viewer and a temporal **Displacement** spline in the Spline Editor. Right-click a Position/Center control (Inspector or viewer) > **Path**. This adds a key. Then move the playhead and drag.
- **Center**: moves the whole path. Animatable.
- **Size**: scales the path.
- **X Y Z Rotation**: rotates the path in 3D.
- **Displacement**: position along the path, **0.0 = start, 1.0 = end**. Edit it in the Spline Editor or the Inspector to slow, stop or reverse motion.
  - **Locked** path points have matching Displacement keys.
  - **Unlocked** points exist only spatially, with no Displacement key.
- **Heading Offset**: connect a control (e.g. a mask Angle) to the path's **Heading** to auto-orient along the path. Heading Offset trims that angle.
- **Right-Click Here for Shape Animation**: animate the path shape, or connect it to other polylines (masks, paint strokes).
- Default point animation type: Preferences > Global Settings > **Default > Point With** = Path (or XY Path) (pp. 1789, 1800).

### Perturb (pp. 1789-1791)
Smooth Perlin-noise jitter, shake or wobble added to any animatable parameter, **even one that is already animated**. It is similar to Shake but has more intuitive controls. **Unlike other random modifiers, it works on polylines, shapes, grid meshes and color gradients.** It **cannot smooth** existing animation, only add jitter.
- Ways to apply:
  - Camera shake on an existing path: right-click the crosshair > **Insert > Perturb**, then lower **Strength**.
  - Jitter the path shape: right-click "Right-click here for shape animation" > Perturb. This works best on dense polylines (tracked, or drawn with Draw Append).
  - **Insert** onto **Displacement**: the object jitters back and forth **along** the path without leaving it.
- **Value**: the center/default value. Its type matches the host control (a slider, or a gradient if applied to a gradient).
- **Jaggedness** (polylines/meshes only): variation along the length rather than over time, giving squigglier shapes.
- **Phase** (polylines/meshes only): animate it to travel the ripple along the shape. This is easiest to see with Speed 0.0.
- **Random Seed** + **Randomize** button: different seeds give different results.
- **Strength**: maximum deviation from Value (AE wiggle amplitude).
- **Wobble**: smoothness. Less wobble is smoother, more is less predictable.
- **Speed**: rate of change (AE wiggle frequency). It gives more predictable "frantic vs languid" control than Wobble.

### Probe (pp. 1791-1793)
Drives any numeric parameter from the color/luma of a pixel or rectangle in an image. Examples: flicker-matching a Brightness to practical lights, or measuring LUT values. Apply with **Modify With > Probe**.
- **Controls tab**
  - **Image to Probe**: drag a node here.
  - **Channel**: Red, Green, Blue, Alpha, **Luma**.
  - Other controls can **Connect To** the Probe's outputs individually: **Result, Red, Green, Blue, Alpha**.
  - **Position X Y**: the sample location.
  - **Probe Rectangle**: the default samples a single pixel. Enable this to sample an area.
  - **Width, Height**: the rectangle size.
  - **Evaluation**: Average, Minimum or Maximum over the rectangle.
- **Value tab**
  - **Scale Input**: the input range. By default, probe 0 → Black Value and probe 1 → White Value. Narrow it for more sensitivity.
  - **Black Value**: the output when the probe reads Scale Input black.
  - **White Value**: the output when the probe reads Scale Input white.
  - **Out of Image Value**: the output when the probe leaves the frame. For a rectangle, this applies only once the **entire** rectangle is outside.

### Publish (p. 1793)
Makes a static control linkable. **Only animated controls appear in Connect To.** Animated controls are auto-published; static ones need right-click > **Publish**. The Controls tab shows **Published Value**.

### Resolve Parameter (p. 1794)
Used on transition templates. It auto-animates the parameter over the transition's duration, so trims on the Edit/Cut page retime it. It is applied from the Modifier context menu. See Recipe 3 below.

### Shake (pp. 1795-1796)
Randomizes a Position or Value control, from fully random to smoothed organic motion. Apply with **Modify With > Shake** (on a viewer Center, the menu item is **Shake Position**).
- **Random Seed**: the same seed gives the same result.
- **Smoothness**: 0 = completely random. Higher is smoother.
- **Lock X/Y**: unlock to get separate X/Y sliders.
- **Minimum / Maximum**: the **absolute** output range.
  - For Center: 0.0-1.0 can land anywhere in frame.
  - 0.70-0.90 confines it to the bottom-right corner.
  - Animate Min/Max to tighten or loosen the shake (see Recipe 6).

### Track (Tracker modifier) (pp. 1796-1798)
Puts a tracker directly on a parameter. In the viewer, right-click the Center of a transform/text/mask > **Object x Center > Modify With > Tracker** (the example menu path is **Modify With > Tracker > Position**). There are three options:
- **Tracker Position**: tracks a point.
- **Steady Position**: stabilizes on a single point.
- **Unsteady Position**: adds the original motion back after stabilizing.

The controls are nearly identical to the Tracker node (see the Tracking Nodes chapter). How it differs from the node:
- **One pattern only.**
- **One output value.** It can't do complex stabilization or match moves.
- **Its default source is the node immediately upstream of the host node.** Override it by typing a node name or dragging the node into the **Track Source** field.
- Example: tracking an eye with an Ellipse mask on a Glow would track the glowed image, so drag the clean Loader into Track Source instead (p. 1798).

### Vector Result (pp. 1798-1799)
Offsets a point by **Distance** and **Angle** from an **Origin**. Use it to orbit something without rotating it, which is different from moving a pivot. Apply with **Modify With > Vector** (the viewer example uses **Modify With > Vector Result**).
- **Origin**: a point that can take its own Path.
- **Distance**: a slider.
- **Angle**: a thumbwheel.
- **Image Aspect**: width/height, defaulting from the Frame Format preference.
- See Recipe 7 for the manual's orbit example.

### XY Path (pp. 1799-1800)
Separate X and Y splines, with **no keyframes on the on-screen path**. This makes single-axis motion easy (AE Separate Dimensions). Apply with **Modify With > XY Path**.
- **X Y Z Values**
- **Center**
- **Size**
- **Angle**
- **Heading Offset**: adds to or subtracts from the heading angle when another control is connected to the heading.
- **Plot Path in View**: toggles the path display.
- Can be made the default via **Default > Point With** = XY Path.

---

