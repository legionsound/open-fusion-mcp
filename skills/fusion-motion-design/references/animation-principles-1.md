<!-- animation-principles.md part 1 of 3; index: animation-principles.md -->
# Fusion Animation Principles (port of ae-animation-principles)

**What it is:** the motion brain for DaVinci Resolve 21.1 Fusion-page builds: timing tables, easing as exact BezierSpline handle math, springs/overshoot/bounce as SimpleExpressions, the R1-R16 recipe library, kinetic type via Text+ Follower, loops, stepped motion, stagger, choreography, motion blur, review beats and failure lessons. **Load it** whenever an agent keys, eases, loops, staggers or reviews motion in a Fusion comp (Python API or `.setting` text), or ports an After Effects motion spec to Fusion.

**Evidence levels used below.** "live-verified" = tested on Resolve Studio 21.1.0.14 on 2026-09-26 (see `fusion-motion-design/references/tested-native-recipes.md`). "corpus-backed" = copied from shipped Blackmagic or third-party `.setting` templates. "TSV" = ID exists in `fusion-reference/data/fusion-21.1-inputs.tsv` (a few frame-format inputs are only in the full live dump). "unverified" = inference, must be tested. Every recipe is **status: unverified (not yet rendered)**; where all mechanics are live-verified the status line says so.

---

## 0. Value contract (Fusion units, not AE units)

| Quantity | Fusion rule | AE conversion |
|---|---|---|
| Time | `time` in expressions and keyframe keys are **frames** (live-verified). Author in seconds, convert with `f = round(sec * fps)`. Subframe keys are legal (corpus: `[5.625] = {...}`). | AE `time` is seconds. |
| Position | Normalized 0-1, (0.5,0.5) = frame center, **Y up** (live-verified). `Transform.Center` is an offset: default {0.5,0.5} = no move. | x/W, and y: `1 - y/H`. A rise of +30 px (down in AE) at 1080 = **-0.0278** in Y. |
| Scale | `Transform.Size` 1.0 = 100%. `Size` scales about `Pivot`. | AE `[130,130]` = `Size 1.3`. |
| Rotation | `Angle` in degrees. **Positive = counterclockwise** (live-verified 2026-09-26: `Angle 30` tilted a bar up-right by 29.97 deg in the Y-up frame). | AE positive Rotation is clockwise: negate. |
| Opacity | No layer opacity on Transform. Fade a layer with the **Merge that composites it**: `Merge.Blend` 0-1 (TSV; `BlendClone` is the Merge-tab mirror). For Text+, `Opacity1` (shading element 1). | AE 0-100 -> 0-1. |
| Text size | `TextPlus.Size` relative to image width: `Size ~= 1.70 * font_px / W` (Open Sans, live-verified). | |
| Masks | `RectangleMask.Width/Height`: each axis relative to its own frame dimension. `EllipseMask.Width/Height`: both relative to frame WIDTH (circle = equal values). `CornerRadius` = fraction of half the shorter side (all live-verified). | |
| Colors | Float 0-1 per channel (`TopLeftRed`, `Red1`...). | |
| Combo inputs | Numeric Combo/MultiButton = 0-based index; ComboID/MultiButtonID = option string (TSV options column). | |
| SimpleExpression trig | **Radians** (`sin(pi/2)=1`, live-verified). Angle inputs still want degrees, so convert results that feed `Angle`. | AE `Math.sin` also radians. |
| Expression modifier trig | Degrees (manual), and it could not be attached via `AddModifier` in tests. Prefer SimpleExpressions. | |

**fps assumption:** tables give 24 / 25 / 30 fps. Recipes are written at **24 fps** (the user's default timelines) with seconds shown so any fps can be re-derived. Never re-derive seconds from AE 30 fps frame counts at another rate: convert AE frames to seconds first (`sec = f30 / 30`).

### The three rules, Fusion edition

1. **No linear keys on spatial or hero motion.** This matters more in Fusion than in AE: **new Bezier keys are linear by default** (manual, and live-verified: keys with no handles get linear 1/3 handles). Every Position, Scale, Rotation and hero reveal key pair must be given explicit `RH`/`LH` handles or an Anim Curves easing. Exceptions: an opacity fade may stay linear; constant-speed spins and ambient wiggle are linear by nature; typewriter progress is linear.
2. **Timing is rhythm, not randomness.** Pick durations from the timing table: every move has anticipation, action and settle.
3. **Animations narrate.** Left-to-right, big-to-small, BG-to-FG. Stagger reveals; never fire everything on one frame.

---

## 1. Timing table (AE 30 fps source converted)

| Phase | AE @30 | Seconds | @24 fps | @25 fps | @30 fps | Use for |
|---|---|---|---|---|---|---|
| Snap | 2-4f | 0.07-0.13 s | 2-3f | 2-3f | 2-4f | Cut-style transition, flash, bullet hit |
| Anticipation | 4-6f | 0.13-0.20 s | 3-5f | 3-5f | 4-6f | Pre-roll before the main action |
| Quick action | 8-12f | 0.27-0.40 s | 6-10f | 7-10f | 8-12f | Hero reveals, smash zooms, slide-ins |
| Cinematic action | 18-30f | 0.60-1.00 s | 14-24f | 15-25f | 18-30f | Slow text reveals, camera moves, big transitions |
| Settle | 6-10f | 0.20-0.33 s | 5-8f | 5-8f | 6-10f | After-bounce, residual motion |
| Loop period | 60-240f | 2-8 s | 48-192f | 50-200f | 60-240f | Ambient loops (breath, orbit, drift) |
| Hold | 30-90f | 1-3 s | 24-72f | 25-75f | 30-90f | Time to read text |

**Scene duration cheat:** logo reveal 2-3 s (48-72f @24, 50-75f @25, 60-90f @30); title card with intro 4-6 s (96-144f / 100-150f / 120-180f); looping ambient scene 8 s (192f / 200f / 240f); brand reel beat 3 s per beat (72f / 75f / 90f).

**UI-system durations:** micro-interactions 100-200 ms = 2-5f @24 (3-5f @25, 3-6f @30); transitions/reveals 300-500 ms = 7-12f @24 (8-12f @25, 9-15f @30).

**Deliverable defaults (seconds):** UI microinteraction 0.2-0.5 · state/feedback icon 0.5-1.25 (+ short hold) · logo mark 0.75-2 · lower third in 0.75-1.5, out 0.5-1 · typography reveal 0.75-2.5 · one promo message 1.5-3 · loops 1-2 s seamless. Broadcast quick refs: text reveal 0.5-0.83 s, logo 1-2 s, transition 0.33-0.67 s, lower third in 0.4-0.6 s (ease-out) and out 0.27-0.4 s (ease-in).

**Rounding rule:** round each key time independently from seconds (`round(t0*fps)`, `round((t0+dur)*fps)`); do not round a duration and add it, or staggered groups drift. Fusion accepts fractional keys when a tight stagger needs them.

---

## 2. Three easing mechanisms, pick one per property

| Mechanism | What it is | Use when | Evidence |
|---|---|---|---|
| **BezierSpline keys with explicit handles** | `AddModifier(id, "BezierSpline")` then `SetKeyFrames(dict, True)` with relative `RH`/`LH` | Default for every keyed move: exact cubic-bezier curves, overshoot via handles, multi-key choreography, visible in the Spline Editor | live-verified |
| **Anim Curves modifier** (`LUTLookup`) | Normalized 0-1 ramp shaped by named Penner curves: `EaseIn`/`EaseOut` options `None|Sine|Quad|Cubic|Quart|Quint|Expo|Circ|Back|Elastic|Bounce` (TSV), then `value = curve * Scale + Offset` | Named presets, especially **Elastic and Bounce** (which no single cubic can express); duration-aware Edit-page templates (`Source` = `Duration` or `Transition`) | live-verified 2026-09-26: `value = curve*Scale + Offset` (Scale 2, Offset 3 -> 3.0..5.0); EaseOut Cubic = Penner ease-out (0.578 at 25%); defaults `Source "Transition"`, `Curve "Linear"`, `Scale` = host range (360 on `Angle`, 5 on `Size`): always set Source/Scale/Offset |
| **SimpleExpression** | One-line Lua on the input (`input.SetExpression("...")`, or `Expression = "..."` in `.setting`) | Springs, loops, wiggle, orbit, stagger by time offset, posterize, anything procedural | live-verified (see function inventory in section 5) |

UI equivalents (for human hand-off): select keys, **Shift-S** smooth, **Shift-L** linear, **T** opens the Ease In/Out length dialog, **I/O** step in/out, Cmd-drag a handle to break it.

### Easing semantics matrix (intent -> family)

| Intent | Family | Why | Typical actions | Curve |
|---|---|---|---|---|
| Responsive, affirmation, arrival | **ease-OUT** (fast start, soft end) | Arrives eager, settles confident | Entrances, reveals, confirm states | Cubic/Quart out, or Back out (tiny overshoot) |
| Reluctance, departure | **ease-IN** (slow start, fast end) | Resists, then leaves | Exits, dismissals, error states | Quart in |
| Neutral, informational | **ease-IN-OUT** | No emotional emphasis | Camera, parallax, A->B repositions | Sine or Cubic in-out |
| Mechanical (avoid) | **Linear** | Robotic | Only fades, spins, typewriter progress, wiggle | none |

Decision rule: entrance/"yes" -> ease-out; exit/"no" -> ease-in; moving information -> ease-in-out; never linear on hero motion.

**Pitfall carried over from AE:** the AE skill's influence tables mixed up which key's handle does what. In Fusion reason per **segment**: the departing key's `RH` shapes the start, the arriving key's `LH` shapes the landing. "Soft landing" = long, flat `LH` on the arriving key.

---

## 3. Cubic-bezier -> BezierSpline handles (exact)

### 3.1 The mapping (live-verified)

For a key pair `t0 -> t1` with values `v0 -> v1`, duration `D = t1 - t0` frames and change `V = v1 - v0`, the CSS curve `cubic-bezier(x1, y1, x2, y2)` is reproduced exactly by:

```
Python SetKeyFrames (RELATIVE offsets {dt, dv}):
  key t0:  RH = {1: x1*D,      2: y1*V}
  key t1:  LH = {1: (x2-1)*D,  2: (y2-1)*V}

.setting file (ABSOLUTE control-point coordinates {time, value}):
  [t0] = { v0, RH = { t0 + x1*D, v0 + y1*V } }
  [t1] = { v1, LH = { t0 + x2*D, v0 + y2*V } }     -- same point as t1+(x2-1)D, v1+(y2-1)V
```

Live test: keys 0:0 -> 24:1 with `RH {8,0}`, `LH {-8,0}` gave f3 .043, f6 .1562, f12 .5, f18 .8438, exactly `cubic-bezier(.333,0,.667,1)`. Keys without handles are linear (Fusion fills `RH {D/3, V/3}`, `LH {-D/3, -V/3}`). Python `GetKeyFrames` returns string frame keys (`"0.0"`) and value index `"1"`.

Rules:
- Keep handle times inside the segment: `0 < x1, x2 < 1`. Curves with `x = 0` or `x = 1` (Circ) become zero-length time handles: clamp to 0.01 / 0.99.
- `y` outside 0-1 is legal and produces real overshoot inside the segment. **Fusion does what AE temporal ease cannot:** a 2-key Back-out overshoots without an extra settle key.
- A middle key used by two segments carries both `LH` (from the previous segment) and `RH` (from the next). If the two tangents are not colinear you get a velocity kink; at extrema (overshoot peaks, holds) keep both flat (`dv = 0`).
- AE influence/speed -> handles: influence `I` % with speed 0 on the departing key -> `RH = {I/100*D, 0}`; on the arriving key -> `LH = {-I/100*D, 0}`. Non-zero AE speed `s` (units per second) -> `dv = s * dt / fps`.

### 3.2 Worked example (house settle on Size, 24 fps)

`Transform.Size` 0.95 -> 1.00 from f4 to f21 (0.70 s = 16.8 -> 17f), curve `(0.22, 0, 0.25, 1)`, so `D = 17`, `V = 0.05`: `RH = {3.74, 0}`, `LH = {-12.75, 0}`.

```python
xf.AddModifier("Size", "BezierSpline")          # seeds a stray key at the current frame
spl = inp(xf, "Size").GetConnectedOutput().GetTool()
spl.SetKeyFrames({
    4:  {1: 0.95, "RH": {1: 3.74,   2: 0.0}},
    21: {1: 1.00, "LH": {1: -12.75, 2: 0.0}},
}, True)                                         # True = replace, removes the stray key
```

`.setting` equivalent (absolute handles; unverified as typed, format corpus-backed):

```lua
XF_Size = BezierSpline {
    SplineColor = { Red = 225, Green = 0, Blue = 225 },
    NameSet = true,
    KeyFrames = {
        [4]  = { 0.95, RH = { 7.74, 0.95 } },
        [21] = { 1,    LH = { 8.25, 1 } },
    },
},
-- and on the tool:  Size = Input { SourceOp = "XF_Size", Source = "Value", },
```

Verify: `xf.GetInput("Size", 12.5)` about 0.9895 (curve y50 = 0.789); `GetInput("Size", 21)` = 1.0; nothing at f<4 below 0.95.

### 3.3 Curve library (handles as fractions of D and V; expected progress for QC)

| Curve | cubic-bezier | RH (dt, dv) | LH (dt, dv) | y@25% | y@50% | y@75% | AE influence analog |
|---|---|---|---|---|---|---|---|
| Sine in | .12,0,.39,0 | .12D, 0 | -.61D, -1V | .077 | .300 | .617 | |
| **Sine out** | .61,1,.88,1 | .61D, 1V | -.12D, 0 | .383 | .700 | .923 | out ~55 |
| Sine in-out | .37,0,.63,1 | .37D, 0 | -.37D, 0 | .145 | .500 | .855 | |
| Quad out | .5,1,.89,1 | .5D, 1V | -.11D, 0 | .436 | .749 | .939 | out ~65 |
| Quad in-out | .45,0,.55,1 | .45D, 0 | -.45D, 0 | .120 | .500 | .880 | |
| Cubic in | .32,0,.67,0 | .32D, 0 | -.33D, -1V | .017 | .128 | .423 | |
| **Cubic out** | .33,1,.68,1 | .33D, 1V | -.32D, 0 | .577 | .872 | .983 | out ~70 |
| Cubic in-out | .65,0,.35,1 | .65D, 0 | -.65D, 0 | .071 | .500 | .929 | |
| Quart in | .5,0,.75,0 | .5D, 0 | -.25D, -1V | .006 | .066 | .311 | exits |
| **Quart out** | .25,1,.5,1 | .25D, 1V | -.5D, 0 | .689 | .934 | .994 | out ~80 |
| Quart in-out | .76,0,.24,1 | .76D, 0 | -.76D, 0 | .053 | .500 | .947 | |
| Quint out | .22,1,.36,1 | .22D, 1V | -.64D, 0 | .765 | .961 | .997 | out ~85 |
| Quint in-out | .83,0,.17,1 | .83D, 0 | -.83D, 0 | .044 | .500 | .956 | |
| Expo out | .16,1,.3,1 | .16D, 1V | -.7D, 0 | .826 | .972 | .998 | out ~90, smash |
| Expo in-out | .87,0,.13,1 | .87D, 0 | -.87D, 0 | .040 | .500 | .960 | |
| Circ out | 0,.55,.45,1 | .01D (clamp), .55V | -.55D, 0 | .660 | .865 | .968 | out ~88 |
| Back in | .36,0,.66,-.56 | .36D, 0 | -.34D, -1.56V | -.060 | -.087 | .184 | anticipation dip |
| **Back out** | .34,1.56,.64,1 | .34D, 1.56V | -.36D, 0 | .816 | 1.087 | 1.060 | peak 1.098 at 57% |
| Back in-out | .68,-.6,.32,1.6 | .68D, -.6V | -.68D, .6V | -.098 | .500 | 1.098 | |
| Elastic / Bounce | not a cubic | use Anim Curves `EaseOut = "Elastic"/"Bounce"` or section 5 expressions | | | | | |

**Named house presets** (use these names in specs):

| Preset | cubic-bezier | RH | LH | y@25/50/75 | Use |
|---|---|---|---|---|---|
| **HOUSE_SETTLE** (AE in22/out75) | .22,0,.25,1 | .22D, 0 | -.75D, 0 | .394/.789/.957 | Default for everything that enters |
| EASY_EASE_33 | .33,0,.67,1 | .33D, 0 | -.33D, 0 | .157/.500/.843 | Reads mechanical; avoid for heroes |
| OUT_70 | 0.01,0,.3,1 | .01D, 0 | -.7D, 0 | .519/.805/.955 | Quick start, soft landing |
| OUT_85 | 0.01,0,.15,1 | .01D, 0 | -.85D, 0 | .607/.854/.968 | Premium decelerating push |
| IN_70 | .7,0,.99,1 | .7D, 0 | -.01D, 0 | .045/.195/.481 | Exits, anticipation |
| IO_60 | .6,0,.4,1 | .6D, 0 | -.6D, 0 | .081/.500/.919 | Camera, parallax |
| IO_85 (easeSnap) | .85,0,.15,1 | .85D, 0 | -.85D, 0 | .042/.500/.958 | Heavy cinematic push, keynote snap |
| COUNT_UP | .25,.25,.4,1 | .25D, .25V | -.6D, 0 | .394/.765/.950 | Near-linear count, soft landing |

**Premium default = settle-weighted, not flat.** Leave the start key with pace and arrive soft (HOUSE_SETTLE). Flat 33/33 reads mechanical.

**Anim Curves presets map 1:1 to this library's names.** `EaseIn="None", EaseOut="Cubic"` should equal Cubic out. Direction live-verified 2026-09-26: `EaseOut="Cubic"` reads 0.578/0.875/0.984 at 25/50/75% (Penner ease-out); `EaseIn="Cubic"` reads 0.016/0.125/0.422. Naming matches Penner.

---

## 4. Spatial vs temporal easing in Fusion

Fusion separates them structurally, which AE only does in the graph editor:

- **Temporal** = value over time = BezierSpline handles on each scalar, or the **Displacement** spline of a Polyline Path.
- **Spatial** = the shape of the path through the frame:
  - **Polyline Path** (`PolyPath`, the UI default for Center): a viewer polyline (spatial, with smooth or linear points) plus a `Displacement` spline 0-1 (temporal). Constant speed along a curved arc = linear Displacement keys; a soft landing on a curved path = HOUSE_SETTLE on Displacement. The last locked point must be 1.0. Option-click on the path adds a shape point without a timing key.
  - **XY Path** (`XYPath`): separate `X` and `Y` splines, no Displacement. Identical easing on X and Y gives a straight line; **different eases on X and Y bend the path** (X Cubic-out + Y Cubic-in = an arc that curves in and lands). This is the scriptable way to get spatial curvature.
  - **Expression path**: `Point(fx(t), fy(t))` on Center, e.g. an arc from a progress value `p`: `Point(x0 + (x1-x0)*p, y0 + (y1-y0)*p + h*4*p*(1-p))` (h = arc height, normalized).
- Auto-orient along a path: connect `Angle` to the Path's `Heading` output (UI: Angle > Connect To > Path > Heading; `.setting`: `Angle = Input { SourceOp = "Path1", Source = "Heading" }`, unverified as typed), trim with `HeadingOffset`.

Common bug, same as AE: a hero element with a perfect temporal ease still looks robotic through a turn. The fix is spatial (round the path, or split X/Y eases), not more temporal influence.

**Points never take a BezierSpline** (0 of 182 shipped `Transform.Center` uses): animate a Point through `PolyPath`, `XYPath`, `Vector`, `Shake`, `PerturbPoint`, a Point expression, or the Expression modifier.

`.setting` idioms (from `skills/fusion-reference/references/setting-format.md` 4.2/4.3, trimmed from shipped titles; unverified as retyped):

```lua
-- PolyPath: straight slide ending at the path Center, eased arrival on Displacement
EL_Path = PolyPath {
    DrawMode = "InsertAndModify",
    Inputs = {
        Center = Input { Value = { 0.5, 0.5 }, },                          -- rest position
        Displacement = Input { SourceOp = "EL_PathDisplacement", Source = "Value", },
        PolyLine = Input { Value = Polyline { Points = {                     -- points RELATIVE to Center
            { Linear = true, LockY = true, X = -0.35, Y = 0, RX = 0.1167, RY = 0 },
            { Linear = true, LockY = true, X = 0, Y = 0, LX = -0.1167, LY = 0 },
        } }, },
    },
},
EL_PathDisplacement = BezierSpline {
    SplineColor = { Red = 255, Green = 0, Blue = 255 },
    KeyFrames = {                                                            -- QUART_OUT over 0-14, absolute handles
        [0]  = { 0, RH = { 3.5, 1 } },
        [14] = { 1, LH = { 7, 1 } },
    },
},
-- consumer:  Center = Input { SourceOp = "EL_Path", Source = "Position", },
-- XYPath instead: EL_XY = XYPath { Inputs = { X = Input { SourceOp = "EL_XY_X", Source = "Value" }, Y = ... } }
-- consumer:  Center = Input { SourceOp = "EL_XY", Source = "Value", },   (XYPath outputs Value, PolyPath/Vector output Position)
```

From Python, prefer XYPath (`AddModifier("Center", "XYPath")`, then BezierSplines on its `X`/`Y`) or a Point expression; building polyline points through the API is not established.

---

## 5. Springs, overshoot and bounce as SimpleExpressions

### 5.1 SimpleExpression inventory (live-verified unless marked)

| Available | Notes |
|---|---|
| `time` | Current frame number (frames, not seconds). |
| `pi`, `sin`, `cos`, `sqrt`, `atan2`, `exp`, `abs`, `floor`, `min`, `max`, `iif(c,a,b)` | Trig in **radians**. `ceil` corpus-backed. |
| full Lua `math.*` | `math.max`, `math.rad`, `math.random` (per-evaluation noise, not repeatable: avoid in renders). |
| `%` (Lua modulo, float, result >= 0 for positive divisor) | corpus-backed (`(...)%1` in shipped templates). |
| `Point(x, y)` | Return type for Point inputs; `+`/`-` Point arithmetic works (manual, corpus). |
| `Text("...")`, `..` concat, `string.format` | Return type for text inputs (manual slate example; `string.format` corpus-backed, not live-tested). |
| `Tool.Input`, `self.Input`, `Tool:GetValue("Input", frame)` | Cross-tool reads and **reads at other frames** (live-verified). |
| `comp.RenderStart`, `comp.RenderEnd`, `comp:GetPrefs().Comp.FrameFormat.Rate` | RenderStart live-verified; Rate and RenderEnd corpus-backed. |
| Statement block: expression starting with `:` then `local ...; if ... then ... end; return ...` | corpus-backed (third-party templates). Enables loops. Not live-tested. |
| **`noise()` does NOT exist** | Returns nil, input reads None (live-verified). Use Perturb/Shake modifiers or summed sines. |

Clearing an expression with `SetExpression("")` leaves the input at 0.0: `SetInput` the intended value afterwards. An expression replaces keys on that input: keep keys on a controller and read them.

**Need real Perlin `noise()`?** It exists only in the **Expression modifier** (degrees, `n1..n9`, `p1..p9`, current frame only). `AddModifier` could not attach it, but shipped files contain it, so the `.setting` paste route can (corpus-backed format, `Advanced Camera Shake.setting`): `EL_Noise = Expression { Inputs = { n1 = Input { Value = 0.0074 }, n2 = Input { Value = 0.08 }, PointExpressionX = Input { Value = "0.5 + n1*noise(time*n2)" }, PointExpressionY = Input { Value = "0.5 + n1*1.78*noise2(0, time*n2 + 100)" } } }` with consumer `Center = Input { SourceOp = "EL_Noise", Source = "PointResult", }` (`NumberExpression` -> `NumberResult` for scalars). Output range of `noise()` unverified: calibrate by sampling.

**Controller pattern (Null + Expression Controls equivalent):** a `Custom` tool renamed e.g. `CTRL` owns `NumberIn1..8` and `PointIn1..4` (TSV). Key progress curves there; element inputs read them with `CTRL.NumberIn1` or `CTRL:GetValue("NumberIn1", time - k)`. Tested: `Point(UNIT_CTRL.NumberIn1, UNIT_CTRL.NumberIn2)` drove a Transform Center. The Custom tool is never connected to the render path.

In the formulas below `F` is the comp fps written as a literal at build time (`f"{fps}"`), `K` is a frame number, and `T`/`S` are target/start values.

### 5.2 Spring entrance with no keys (critically meaningful physics)

Exact underdamped step response from `S` to `T` starting at frame `K0`:

```
iif(time < K0, S, T + (S - T) * exp(-Z*W*(time-K0)/F) * (cos(Wd*(time-K0)/F) + Z*W/Wd*sin(Wd*(time-K0)/F)))
```

with `W = sqrt(k/m)` (rad/s), `Z = c / (2*sqrt(k*m))`, `Wd = W*sqrt(1 - Z*Z)`. Overshoot fraction = `exp(-pi*Z/sqrt(1-Z*Z))`, peak at `pi/Wd` s, 2% settle about `4/(Z*W)` s.

| Spring preset | m, k, c | W | Z | Wd (Hz) | Overshoot | Settle | Fusion use |
|---|---|---|---|---|---|---|---|
| Framer default | 1, 100, 10 | 10 | 0.50 | 8.66 (1.38 Hz) | 16% | 0.8 s | too bouncy for house text; OK for playful UI |
| Bouncy | 1, 300, 10 | 17.3 | 0.29 | 16.6 (2.64 Hz) | 39% | 0.8 s | toys, badges only |
| Smooth | 1, 100, 20 | 10 | 1.0 | none | 0% | | use HOUSE_SETTLE keys, no expression |
| **House panel spring** | pick Z, W | 11.1 | 0.72 | 7.71 | 4% | 0.5 s | panels/modals |

Z for a target overshoot: 2% -> 0.78, 3% -> 0.745, 4% -> 0.716, 5% -> 0.69, 8% -> 0.63, 10% -> 0.59. Pick settle time `Ts`, then `W = 4/(Z*Ts)`. Mapping rules from AE stay true: stiffness -> frequency, damping -> decay (settles sooner), mass stretches the period.

Worked (24 fps, Size 0.95 -> 1.0, K0 = 10, Z 0.72, W 11.11, Wd 7.71):
`iif(time < 10, 0.95, 1 + (0.95 - 1)*exp(-8*(time-10)/24)*(cos(7.71*(time-10)/24) + 1.0375*sin(7.71*(time-10)/24)))`
Verify: peak about 1.0019 near f19.8 (4% of V), value 1.0 +/- 0.001 from f23. **Live-verified 2026-09-26** (Resolve 21.1.0.14, sampled f8..29): peak 1.00191 at f20, 1.00131 at f22, 1.00092 at f23, 0.99993 at f29.

### 5.3 Velocity-matched overshoot after a keyed move (AE "OVERSHOOT")

Keys live on `CTRL.NumberIn1`; the element input reads them and adds a decaying oscillation after the last key `K`, seeded by the arrival velocity (units per second = per-frame delta * F). Physically consistent form (continuous velocity at K):

```
iif(time <= K, CTRL.NumberIn1,
    CTRL.NumberIn1 + G*(CTRL:GetValue("NumberIn1", K) - CTRL:GetValue("NumberIn1", K-1))*F
                     * sin(2*pi*Hz*(time-K)/F) / (2*pi*Hz*exp(DEC*(time-K)/F)))
```
(one line in practice). `Hz` 1-3, `DEC` 2-6 (higher settles faster), `G` 0-1 restraint gain. **It needs arrival velocity:** key the move with a linear or accelerating arrival (short `LH`), not a soft landing. With HOUSE_SETTLE arrival the velocity is about 0 and nothing overshoots, which is the correct result for text. Use `sin` when the element arrives moving and should swing past (default); use `cos` (and drop the velocity term, use a fixed amplitude) for a struck element that starts at max deflection.

**SUBTLE rule (unchanged): overshoot 3-10 px at 1080 = 0.3-0.9% of frame height (0.003-0.009 normalized Y); Scale overshoot +2-5% (1.00 -> 1.03 -> 1.00).** More reads cheap. Note that Back-out and Anim Curves "Back" overshoot about 10% **of the change V**: fine for 0.95 -> 1.0 (peak 1.005), far too much for 0 -> 1 (peak 1.10). For large-range pops use explicit keys (0 -> 1.04 -> 1.0) or a spring with Z >= 0.72.

### 5.4 Bounce

Preferred: **Anim Curves** on the input: `Source = "Custom"`, `Input` keyed linear 0 -> 1 over the drop window, `Curve = "Easing"`, `EaseIn = "None"`, `EaseOut = "Bounce"`, `Offset = start`, `Scale = change` (live-verified 2026-09-26: Bounce reads 0.97 at 37.5%, dips to 0.77, lands exactly on `start + change` at the window end; the corpus uses negative `Scale` with `Offset = 1` for reversed ranges). Shipped `Fall and Bounce.setting` drives a `Vector.Distance` with `EaseOut "Bounce"` exactly this way.

```lua
-- .setting (shape from setting-format.md 4.5 + corpus Custom-source pattern; unverified as typed)
EL_Drop = LUTLookup {
    Inputs = {
        Source  = Input { Value = FuID { "Custom" }, },
        Input   = Input { SourceOp = "EL_DropInput", Source = "Value", },
        Curve   = Input { Value = FuID { "Easing" }, },
        EaseIn  = Input { Value = FuID { "None" }, },
        EaseOut = Input { Value = FuID { "Bounce" }, },
        Scale   = Input { Value = 1, },          -- change
        Offset  = Input { Value = 0, },          -- start
    },
},
EL_DropInput = BezierSpline {                    -- LINEAR 0 -> 1 over the window (f10-f34), timing only
    SplineColor = { Red = 104, Green = 195, Blue = 244 },
    KeyFrames = {
        [10] = { 0, RH = { 18, 0.333333 }, Flags = { Linear = true } },
        [34] = { 1, LH = { 26, 0.666667 }, Flags = { Linear = true } },
    },
},
-- consumer (number):  Distance = Input { SourceOp = "EL_Drop", Source = "Value", },
```
Python: `xf.AddModifier("Size", "LUTLookup")`, get the modifier with `inp(xf,"Size").GetConnectedOutput().GetTool()`, `SetInput("Source","Custom")`, `SetInput("Curve","Easing")`, `SetInput("EaseOut","Bounce")`, set `Scale`/`Offset` explicitly (default read 5 on this host), then `animate(ac, "Input", [(10,0),(34,1)], [None])`.

Keyless one-line approximation (floor bounce toward T, decaying):
`iif(time < K0, S, T + (S - T) * abs(cos(Wb*(time-K0)/F)) * exp(-DEC*(time-K0)/F))` with `Wb` about 8-12 rad/s, `DEC` 3-5.

Physically exact parabolic restitution bounce (port of the AE loop) needs a statement block (corpus-backed syntax, unverified):
```
:local K=12; local F=24; local e=0.7; local g=4.6; local base=CTRL.NumberIn1; if time<=K then return base end; local v=(CTRL:GetValue("NumberIn1",K)-CTRL:GetValue("NumberIn1",K-1))*F; if v==0 then return base end; local dir=(v>0) and -1 or 1; local vl=math.abs(v)*e; local t=(time-K)/F; local tb=2*vl/g; local tn=tb; local n=1; while t>tn and n<=9 do vl=vl*e; tb=2*vl/g; tn=tn+tb; n=n+1 end; if n>9 then return base end; local t2=t-(tn-tb); return base + dir*(vl*t2 - g*t2*t2/2)
```
`g` is in property units per s^2 (AE 5000 px/s^2 at 1080 = 4.6 normalized H/s^2). For a Point input wrap the Y result in `Point(x, ...)`.

---

## 6. API cheat sheet (Python, Resolve 21.1)

```python
import math
# fps: read it, do not assume. Live-verified: returns 24.0 on a 24 fps timeline; inside expressions `comp:GetPrefs().Comp.FrameFormat.Rate` also reads 24.
fps = float(comp.GetPrefs("Comp.FrameFormat.Rate") or 24)
def F(sec):  return int(round(sec * fps))

def add(reg_id, name, x=0, y=0):
    comp.SetActiveTool(None)          # live-verified fix: otherwise AddTool auto-connects to the active tool
    t = comp.AddTool(reg_id, False, x, y, False, False)
    t.SetAttrs({"TOOLS_Name": name})  # alphanumeric/underscore only, no leading digit
    return t

def wire(dst, port, src):
    if not dst.ConnectInput(port, src):          # returns True/False; read back wiring
        raise RuntimeError("ConnectInput failed: %s.%s" % (dst.GetAttrs()["TOOLS_Name"], port))

def inp(tool, input_id):
    for v in tool.GetInputList().values():
        if v.GetAttrs()["INPS_ID"] == input_id:
            return v
    raise KeyError(input_id)

def spline(tool, input_id):
    """BezierSpline driving a scalar input (creates one if absent)."""
    i = inp(tool, input_id)
    out = i.GetConnectedOutput()
    if not out:
        tool.AddModifier(input_id, "BezierSpline")   # return value inconsistent: check the connection
        out = i.GetConnectedOutput()
    return out.GetTool()

def keys(points, curves):
    """points [(frame, value), ...]; curves: one (x1,y1,x2,y2) or None (linear) per segment."""
    kf = {t: {1: v} for t, v in points}
    for (t0, v0), (t1, v1), bez in zip(points, points[1:], curves):
        if bez is None:
            continue
        x1, y1, x2, y2 = bez
        D, V = t1 - t0, v1 - v0
        kf[t0]["RH"] = {1: x1 * D, 2: y1 * V}
        kf[t1]["LH"] = {1: (x2 - 1) * D, 2: (y2 - 1) * V}
    return kf

HOUSE = (0.22, 0, 0.25, 1); CUBIC_OUT = (0.33, 1, 0.68, 1); QUART_OUT = (0.25, 1, 0.5, 1)
EXPO_OUT = (0.16, 1, 0.3, 1); SINE_IO = (0.37, 0, 0.63, 1); IO_85 = (0.85, 0, 0.15, 1)
IN_70 = (0.7, 0, 0.99, 1); QUART_IN = (0.5, 0, 0.75, 0)

def animate(tool, input_id, points, curves):
    sp = spline(tool, input_id)
    k = keys(points, curves)
    sp.SetKeyFrames(k, True)
    sp.SetKeyFrames(k, True)   # live-verified fix: the 1st replace can keep AddModifier's stray key and drop key-0 RH
    got = sorted(float(f) for f in sp.GetKeyFrames().keys())
    assert got == sorted(float(t) for t, _ in points), got
    return sp

def sample(tool, input_id, frames):          # curve QC without rendering
    return [(f, tool.GetInput(input_id, f)) for f in frames]
```

Build hygiene (from tested mechanics): wrap multi-tool builds in `comp.Lock()` / `comp.Unlock()` with a `finally`; `comp.StartUndo("name")` / `EndUndo(True)`; a failed `AddModifier` can leave an orphan modifier and deleting a host does not delete its modifiers (clean via `comp.GetToolList(False)`). Alternative one-call route (live-verified): write `.setting` text to a file, make the comp current on the Fusion page, `comp.Execute('comp:Paste(bmd.readfile([[/abs/path.setting]]))')`, wait about 1 s, poll `FindTool`. Paste also avoids the auto-connect trap. On a name collision pasted tools get a `_1` suffix and expressions inside the pasted set are rewritten, but your script's names and any outside expressions are not: use a unique prefix per paste. In `.setting` text, dotted IDs need bracket keys (`["Transform3DOp.Translate.Z"] = Input { ... }`); in `SetInput` they are plain strings.

**Standard element rig ("layer"):** `SRC` (Text+, shape, image) generated **centered** -> `EL_XF` (`Transform`: `Center` places it, `Pivot` stays {0.5,0.5} = the element's own center, `Size`, `Angle`, motion blur) -> `EL_MRG.Foreground` (`Merge.Blend` = opacity) with the running comp on `EL_MRG.Background`. Centering the source keeps scale/rotation about the element, like an AE anchor at center. If the source is not centered, set `EL_XF.Pivot` to its center (e.g. expression `TITLE_TXT.Center`). Consecutive Transforms concatenate (one resample), so parenting = chaining Transforms, not a quality cost.

---

