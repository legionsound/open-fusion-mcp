<!-- depth-space.md part 1 of 3; index: depth-space.md -->
# Fusion Depth & Space: true 3D stages and 2.5D rigs (port of `ae-depth-space`)

What it is: the Fusion-native craft module for depth. Parallax stacks, camera push-ins, orbit-like
arcs, rack focus, exponential atmosphere, grounding shadows, perspective floors, single-image 2.5D,
motion blur and the "why it reads flat" fixes, for DaVinci Resolve 21.1 (Fusion page). Load it when
a shot must read as space rather than as layers, or when a depth comp looks like cardboard. Reader:
an agent building through the Resolve Python API or by pasting `.setting` text.

The AE original had no 3D layers, camera or lights, so it faked everything in 2.5D. Fusion has a
real 3D compositor. The biggest decision in this port: **true 3D is the default tier**, because the
camera enforces the speed/scale law, Fog3D enforces the atmosphere law and accumulation DOF enforces
the blur law by construction. The 2.5D rigs remain for light templates and single images.

## Conventions

- Timing assumes **24 fps**; frame counts for 25/30 fps are given where timing matters.
- "px @1920" = pixels on a 1920-wide frame; double for UHD 3840. Positions are normalized 0-1,
  origin bottom-left, **Y up** (`y = 1 - py/H`).
- Blur, Glow, Defocus and VariBlur size inputs are **not pixel radii** [live note in
  fusion-realities §2]. Every blur number here is a target in px; the recipe states how to calibrate.
- ID trust: plain IDs are in `fusion-reference/data/fusion-21.1-inputs.tsv`. **[C]** = present in shipped Blackmagic
  templates (corpus) but absent from the TSV harvest (Renderer3D OpenGL sub-inputs only appear once
  `RendererType` is OpenGL). **[U]** = unverified (option index inferred from manual order, or
  semantics not observed).
- Build route: for multi-node rigs prefer **`.setting` paste** on the current Fusion-page comp
  (`cc.Execute('comp:Paste(bmd.readfile([[/abs/x.setting]]))')`, deferred: poll `FindTool`). With
  Python, call **`comp.SetActiveTool(None)` before every `AddTool`** and check every `ConnectInput`
  return (live-verified auto-connect trap).
- SimpleExpressions: trig in **radians**, `time` = **frame number**, `noise()` does not exist, cross-tool
  refs like `CAM.Transform3DOp.Translate.Z` work [live]. Python Bezier handles are relative
  `{dt, dv}`; `.setting` handles are absolute `{frame, value}`.
- Every recipe: **status: unverified (not yet rendered)**.

---

## 0. Pick the tier first

| Situation | Tier | Why |
|---|---|---|
| 3+ planes, truck/pedestal/push, rack focus, haze, any "cinematic space" shot | **T1 true 3D** (default) | ImagePlane3D cards at real Z + Camera3D. Speed, size, haze and defocus all derive from one geometry, so they cannot disagree |
| Cutouts must cast soft, alpha-shaped shadows onto a floor | T1 with **Software** renderer | Soft, alpha-aware and colored shadows exist only in the Software renderer |
| Edit-page template, 2-5 planes, gentle drift, must stay light and publishable | **T2a 2.5D Transform ladder** | One Custom controller, p written once per plane, exact per-plane motion blur, no renderer cost |
| One flat photo, subtle move, no cutouts | **T2b 2D Displace** or **T1b Displace3D relief card** | Stereo-limited budget (1.5-3% width); T1b adds real DOF/fog/motion blur for free |
| Needed spread from one photo > ~2-3% width | Cut into cards, then T1 | Displacement only pulls pixels; it cannot reveal what is behind an edge |
| Titles, UI, lower thirds over the space | 2D on top of the T1 render | They must not receive fog, DOF or lens effects |

3D is overkill when: fewer than 3 planes, total move < 1% width, the result must be a light Edit-page
effect, or the plates were painted with baked perspective that a camera would contradict.
Do not introduce a camera merely to move flat text or a single flat layer: a Transform does that
exactly. (The AE local connector now allows native 3D too; its old cloud "no camera" rule never
applied to Fusion.)

Rules that hold in every tier (local connector revision, 2026-09-26):
- **Depth strength control with an exact zero.** Expose one `Depth` (or parallax strength)
  number on the controller; every per-plane offset, scale and haze term multiplies by it, so
  `Depth` 0 returns exactly the baseline layout (render f0 at 0 and diff against the flat
  build). [verified live 2026-09-26] Per-plane `Center`/`Size` expressions of the form
  `baseline + Depth*k` and a haze Merge `Blend` = `Depth*0.15`: at `Depth` 0 the render matched the
  flat build to 0.0 max difference (identity Transforms and a Blend-0 Merge add no resample);
  `Depth` 1 differed by up to 0.36. Test 0, the typical value and the extreme for uncovered edges, over-scale and clipping.
- Farther planes move less and lose contrast, saturation and detail consistently. Saturation
  steps of 0/15/30/50 % and haze steps of about 15 % per plane are starting points, not physics:
  match the reference and never wash out readable text (titles stay 2D on top, table above).
- Small tight contact shadows anchor touching surfaces; broader, softer shadows separate planes.
  One light direction for the whole scene; recheck shadows after regrouping or retiming.
- Pivot rigid objects before rotating them; inspect real perspective instead of compensating with
  arbitrary skew.
- Camera drift or idle wobble only when asked. Enable motion blur when motion benefits, render at
  delivery settings and check thin UI strokes and small text.

---

## 1. The consistency law, Fusion form

One depth coefficient per plane: **p = z_f / z** (z_f = camera-to-focal-plane distance, z =
camera-to-plane distance). From that one p:

| Cue | Law | T1 (3D) enforces it by | T2 (2.5D) you must write |
|---|---|---|---|
| Parallax speed | screen speed under a truck ∝ p | the camera | `Center` offset × p |
| Apparent size | like objects appear ∝ p | the camera | content authored at p scale; push `Size = 1/(1 - p·Δ)` |
| Atmosphere | haze = 1 − e^(−δ·z) (monotonic in z) | Fog3D `FogType` Exp | haze passes by plane order |
| Defocus | CoC ∝ \|p − p_focus\| | OpenGL accumulation DOF | `XBlurSize = K·abs(p − p_focus)` |

The defocus row is why the AE "blur ladder saturates 4:6:7" rule is real optics: with focus at the
focal plane, planes at 2×/4×/8× distance have p = 0.5/0.25/0.125 and CoC = 0.5/0.75/0.875 of the
infinity blur. Fusion 3D gives this automatically; the 2.5D rig reproduces it with one expression.

**How the law breaks in 3D** (new failure modes, not present in AE):
- Scaling a card down to make it "look far" instead of moving it in Z: it keeps the parallax of its
  real Z while looking small. Cardboard again. Move cards in Z; only full-bleed backdrops get the
  frustum-fit scale (section 2).
- Animating `FLength` (zoom) or a Merge3D transform instead of translating the camera: uniform
  magnification, zero parallax.
- Baking grain or blur into plates before they become cards: card scale and distance change grain
  size and blur per plane (multiple sensors, multiple lenses).

**AE equivalence.** AE's p = zoom/(zoom + z) used zoom = 1.3889 × comp width, i.e. a 50 mm lens on a
36 mm back (HFOV 39.6°). The same FOV on Fusion's default gate (ApertureW 0.8315 in = 21.12 mm) is
`FLength` **29.3** (29.337: AoV 22.89 vertical once the apertures are written, section 2). Fusion's
default `FLength` 35 gives HFOV 33.6° (slightly longer). (Rebuilding an existing AE comp: ae-matching.md.)

**Plane count:** 3 = floor, **5 = sweet spot**, > 8 adds nothing. Adjacent planes should differ
1.5-4× in p; 10% steps merge visually.

**Occlusion is cue #1.** Card silhouettes must physically overlap. In 3D the overlap changes during
a truck (dynamic occlusion), which is the strongest depth cue you have. It requires hole fill: every
card behind an occluder needs real image content under the occluder for a margin of
`(p_front − p_back) × total focal-plane screen travel` (frame widths), plus 10-15 px.

**Blur is double-edged (measured in the AE study: defocus lowered depth discrimination d′ 1.56 → 1.22).**
Keep perspective-line planes (floors, horizons) and occlusion edges sharp; spend blur on the extreme
FG occluder and the geometry-free sky. Heavy blur top and bottom = tilt-shift miniature.

---

## 2. The depth stage: numbers

Stage constants (default Camera3D: `FLength` 35, `ApertureW` 0.8315 in, `ApertureH` 0.4677 in,
`ResolutionGateFit` "Height", 16:9 render):

- Visible width at distance z: **W(z) = z × 21.12 / 35 = 0.6034·z** units; height H(z) = 0.3394·z.
  **Only with the URSA 4K 16:9 apertures** (the AddTool default). A Camera3D created by `.setting` paste
  comes up as `"TV"` (0.792 x 0.594 in, AoV 24.33 at 35 mm, live). **Corrected [from rebuild log, K2]:**
  this line used to say writing `FilmGate = Input { Value = FuID { "BMD_URSA_4K_16x9" }, }` is enough.
  In the rebuild that FuID read back but `ApertureW`/`ApertureH` stayed 0.792 x 0.594 and a 1-unit card
  rendered 0.79x its expected size. Write `ApertureW = Input { Value = 0.8315, }` and
  `ApertureH = Input { Value = 0.4677, }` explicitly (FilmGate may stay) and read `AoV` back before
  trusting W(z): 19.26 at 35 mm, 22.89 at 29.337 mm (28.84 at 29.337 mm means the TV apertures).
- Canonical stage: camera at the origin looking down −Z (Fusion eyespace), **z_f = 10**, so the focal
  plane is 6.034 units wide. A card's `Transform3DOp.Translate.Z` = −z.
- An ImagePlane3D is **1 unit wide**, height = 1/image aspect (**live-measured 2026-09-26**). Its
  uniform scale is `Transform3DOp.Scale.X` while `Transform3DOp.ScaleLock` = 1 (default).
- Frustum-fit scale for a full-bleed 16:9 plate: **S = (W(z) + T) × 1.05**, T = total camera truck in
  units (0 for push-ins). For plates of aspect a ≠ 16:9: `S = max(W(z) + T, H(z)·a) × 1.05`.
- Wide panoramas for long trucks still map to a 1-unit-wide plane, so their height shrinks (1/a): the
  `H(z)·a` term above is what keeps them covering the frame vertically.

**The ladder** (translate the AE slider ladder to Z; haze column uses Fog3D Exp δ = 0.0042, section 5):

| Plane | AE slider | p | z (units) | Card `Translate.Z` | W(z) | Scale for T = 1.5 | CoC (× K) | T1 haze | T2 haze passes |
|---|---|---|---|---|---|---|---|---|---|
| Sky | 0 | 0 | ∞ | 2D behind Renderer3D (sec. 3 rule) | - | - | 1.00 | = fog color at horizon | behind all 3 |
| Far mountains | 5-10 | 0.07 | 142.9 | −142.9 | 86.2 | 92.1 | 0.93 | 45% | 3 (39%) |
| Hills | 15-30 | 0.2 | 50 | −50 | 30.2 | 33.3 | 0.80 | 19% | 2 (28%) |
| Mid | 40-70 | 0.5 | 20 | −20 | 12.1 | 14.2 | 0.50 | 8% | 1 (15%) |
| Focal / subject | 100 | 1.0 | 10 | −10 | 6.03 | 7.91 | 0 | 4% | 0 |
| FG | 120-150 | 1.5 | 6.67 | −6.67 | 4.02 | 5.80 | 0.50 | 3% | 0 |
| Hero FG fly-by | 200-300 | 2.0-3.0 | 5.0-3.33 | −5.0 to −3.33 | 3.02-2.01 | 4.7-3.7 | 1.0-2.0 | 2% | 0 |

- In T2 the "p" column is literally the per-plane speed multiplier (AE slider / 100).
- Discrete objects (a person, a tree) are **not** frustum-fit: give them a real-world size in units
  (consistent across planes) and let the camera shrink them.
- `PerspAdaptiveClip` (default 1) fits clip planes to the scene. If a far card vanishes, set it to 0
  and `PerspFarClip` ≥ 1.2 × farthest z.

**Lens vocabulary (tele vs wide contract, now physical).** To keep the subject framed with a
longer lens, move the camera back: z_f scales with FLength while the cards stay put, so every p moves
toward 1 (compressed parallax). Wide = `FLength` 18-24, camera close, large p spread, light haze
(δ × 0.5). Tele = `FLength` 85-135, camera far, small p spread, strong haze (δ × 1.5-2). Never mix: a
long lens with a large p spread is the fatal subtle inconsistency.

---

## 3. T1 camera rigs (true 3D)

### R1. Depth stage build (the workhorse)
Purpose: 5-plane parallax stage that every other T1 recipe animates. status: unverified (not yet rendered).

```
PlateFar   -> CARD_FAR   (ImagePlane3D.MaterialInput) --\
PlateHills -> CARD_HILLS                               --+
PlateMid   -> CARD_MID                                 --+-> STAGE (Merge3D) -> HAZE3D (Fog3D) -> RENDER (Renderer3D) -> COMP.Foreground
PlateFocal -> CARD_FOCAL                               --+                         SKY (Background) -> SKY_XF (Transform) -> COMP.Background
PlateFG    -> CARD_FG                                  --+
CAM (Camera3D) -> CAM_WIG (Transform3D) ---------------/
```

- Cards: `ImagePlane3D`, `MaterialInput` <- plate; `Transform3DOp.Translate.Z` = −z and
  `Transform3DOp.Scale.X` = S from the ladder table. Leave lighting off (Renderer default) so cards
  show their texture at full value.
- Plate hygiene before the card: cutouts through AlphaDivide -> edge work -> AlphaMultiply (section 9);
  **no grain, no blur, no haze baked in**.
- `CAM`: `FLength` 35 (or 29.3 to match AE FOV), `PlaneOfFocus` 10, `Stereo.Mode` "Mono".
  Animate the camera, never the cards or the Merge3D.
- `CAM_WIG` (Transform3D, `SceneInput` <- CAM): keep-alive expressions (R4). Chaining a 3D object into
  a downstream transform parents it; the camera travels with CAM_WIG.
- `STAGE` (Merge3D): `SceneInput1..N` <- cards, then CAM_WIG. Each connection creates the next
  `SceneInputN` slot; wire them in order.
- `HAZE3D` (Fog3D): section 5. `RENDER` (Renderer3D): `RendererType` "RendererOpenGL" for DOF (section
  6), `MotionBlur` 1, `Quality` 6, `ShutterAngle` 180 (section 8). One camera in the scene, so
  `CameraSelector` "Default" is safe; with more cameras set it to the camera node name.
- `SKY`: Background, `Type` "Vertical", `TopLeftRed/Green/Blue` = zenith (e.g. 0.36, 0.55, 0.72),
  `BottomLeftRed/Green/Blue` = horizon = fog color (0.651, 0.784, 0.847 = #a6c8d8). `COMP` Merge:
  `Background` <- SKY_XF, `Foreground` <- RENDER.

Verify: view STAGE in the 3D viewer, right-click > Camera > CAM, Guides > Frame Aspect: every card
fills the frame at both ends of the move; no card sits at Z 0 (the camera would be inside it). Render
frames 0, mid and end: planes overlap, nothing reveals black.

**Sky placement rule.** Pure translation (truck, pedestal, dolly) = sky is a true infinity plane:
keep it 2D behind the render, static (AE "s = 0 strictly"). **Any rotation or focal-length change**
moves the infinity plane: pans/tilts/target-lock shift it, zooms scale it. Then either drive
`SKY_XF` by expression (R2b, R3c) or put the sky on a card at z ≥ 50·z_f inside a Merge3D placed
**after** Fog3D (so it stays unfogged).

### R2. Truck (lateral parallax)
status: unverified (not yet rendered).

**R2a Plain truck** (AE null-rig pan): keys on `CAM.Transform3DOp.Translate.X`, 96-144 f @24
(100-150 @25, 120-180 @30), ease cubic-bezier(0.33, 0, 0.67, 1). All planes move opposite to the
camera at speed ∝ p; sky static.

**R2b Target-locked truck** (AE "FG runs opposite to BG", reads as an orbit around the subject):
same keys plus `Transform3DOp.UseTarget` 1, `Transform3DOp.Target.X/Y/Z` = (0, 0, −z_f). Screen shift
of each plane = (1 − p) × x_cam / W(z_f): focal plane locked, FG against the move, BG and sky with it.
Sky must move: `SKY_XF.Center` expression
`Point(0.5 + CAM.Transform3DOp.Translate.X/6.034, 0.5)` (6.034 = W(z_f); sign [U], flip if the sky
drifts against the far card). Coverage for card k becomes W(z) + T·|1 − z/z_f|.
Keep total yaw ≤ 8-10° (atan(x_max/z_f)); beyond that cards reveal their flatness.

**Budgets (7-second rule: the fastest plane may cross the frame in no less than 7 s).**
Peak velocity = 1.5 × average for ease (0.33, 0, 0.67, 1); 2 × for (0.5, 0, 0.5, 1); strong AE-style
85% influence eases peak near 3× and strobe, so avoid them on camera moves.

| Rig | Fastest plane factor | Max total camera travel over T seconds (ease 0.33/0.67) | Example, T = 4 s |
|---|---|---|---|
| Plain truck | p_max (FG 1.5) | W(z_near) × T / 10.5 | FG z 6.67: **1.53 units**; hero FG z 5: 1.15 |
| Target-locked | max\|1 − p\| (sky = 1) | W(z_f) × T / (10.5 × max\|1 − p\|) | **2.30 units**, yaw ±6.6° |
| 2.5D pan (T2a) | p_max | T / (10.5 × p_max) frame widths | 0.254 W at the focal plane |

Per frame at 24/25/30 fps the plain-truck peak for FG 1.5 is 0.0239 / 0.0230 / 0.0191 units: the
focal plane then moves 7.6 / 7.3 / 6.1 px @1920 per frame, matching AE's 7.6 px/frame. Faster needs
`ShutterAngle` 270-360 (section 8).

Verify: step frames at peak velocity; FG edge displacement per frame ≤ 11 px @1920; no strobing.

### R3. Push-in
status: unverified (not yet rendered).

**R3a Dolly push (true push-in).** Keys on `CAM.Transform3DOp.Translate.Z` from 0 to −Δ, Δ =
**0.05-0.15 · z_f** (0.5-1.5 units), 72-120 f @24 (75-125 @25, 90-150 @30), ease (0.33, 0, 0.67, 1)
or a long settle (0.45, 0, 0.15, 1). Growth is exactly z/(z − Δ), no expression needed:

| Δ = 1.0 (0.1 z_f) | hero FG z 5 | FG z 6.67 | focal 10 | mid 20 | hills 50 | far 143 | sky |
|---|---|---|---|---|---|---|---|
| scale | ×1.25 | ×1.176 | ×1.111 | ×1.053 | ×1.020 | ×1.007 | ×1.0 |

Focus must follow the dolly: `CAM.PlaneOfFocus` expression `10 + CAM.Transform3DOp.Translate.Z`.
Never let Δ approach z_near; if the move must pass a card, add SoftClip (section 5).

**R3b Counter-scale push (AE §1 "push-in = counter-scale only", FG 110-115% / BG 90-95%, mid still).**
This is a dolly-zoom. Dolly as R3a and link focal length so the focal plane keeps its size:
`CAM.FLength` expression `35*(10 + CAM.Transform3DOp.Translate.Z)/10`. With Δ = 1: FLength 31.5,
hero FG ×1.125, FG ×1.059, focal ×1.000, mid ×0.947, hills ×0.918, far ×0.906, sky ×0.900. The sky
must shrink too: `SKY_XF.Size` expression `CAM.FLength/35`. Card coverage needs × f0/f_min extra.

**R3c Zoom (FLength only).** Uniform magnification, no parallax: it reads as a digital zoom. Only
as a deliberate style, and exponential, never linear:
`CAM.FLength` = `35*(70/35)^(min(time,96)/96)` (35 -> 70 mm over 96 f). Sky: `SKY_XF.Size` =
`CAM.FLength/35`. A 2D equivalent on a flattened comp: `Transform.Size` =
`1*(1.2/1)^(min(time,96)/96)`.

Verify: at end frame the focal card measures ×1.111 (R3a) or ×1.000 (R3b) against frame 0; the far
card changes < 1% (R3a); nothing drifts laterally.

### R4. Keep-alive micro parallax (AE `wiggle(1,2)` on the CAM null)
status: unverified (not yet rendered).

On `CAM_WIG` (Transform3D) set expressions (2 px @1920 at the focal plane = 0.0063 units; `noise()`
does not exist, so sum incommensurate sines):
- `Transform3DOp.Translate.X`: `0.0045*sin(2*pi*time/24) + 0.003*sin(2*pi*time/41 + 1.3)`
- `Transform3DOp.Translate.Y`: `0.003*sin(2*pi*time/29 + 0.7) + 0.002*sin(2*pi*time/53 + 2.1)`

Translation (not rotation) is what produces parallax. Alternative: `Shake` modifier (`XMinimum`
−0.006, `XMaximum` 0.006, `Smoothness` 10-15; outputs `X`, `Y`). Deterministic sines are time
coherent and safe under motion-blur subframes; `math.random` flickers.

Verify: a still-frame sequence of 48 frames shows FG vs far relative motion of 1-3 px, no jitter.

### Movement grammar (T1)

| Move | Fusion operation | Reads as | Rule |
|---|---|---|---|
| Truck | `CAM.Transform3DOp.Translate.X` | lateral parallax, all planes same way, speed ∝ p | sky static |
| Arc / orbit feel | truck + `Transform3DOp.UseTarget` at focal center | subject locked, FG vs BG opposite | sky moves ×1 (R2b) |
| Pedestal | `Translate.Y` | vertical parallax | the 9:16 star axis |
| Dolly push | `Translate.Z` forward 0.05-0.15 z_f | push-in, FG grows most | focus expression follows |
| Counter-scale push | dolly + `FLength` link | breathing space, subject constant | sky Size = FLength/35 |
| Zoom | `FLength` | flat magnification | exponential only, style choice |
| Pan / tilt | `Transform3DOp.Rotate.Y/X` | no parallax (nodal) | sky inside the rotation |
| Scene move | Merge3D / Transform3D on cards | nothing gained, confusing | don't |

### Aimed camera and compound rotations [from rebuild log]
- **Aimed camera** [from rebuild log, W4]: a position + point-of-interest camera is a `Camera3D` with
  `Transform3DOp.UseTarget` 1, `Transform3DOp.Translate.X/Y/Z` and `Transform3DOp.Target.X/Y/Z` keyed
  per axis, each BezierSpline carrying its segment's ease. `PlaneOfFocus` = distance from the camera
  to the focus target along the view axis (keyed or by expression); a rack focus moves that target.
  The first scene built this way matched its reference at 9 sampled frames, whip-pan streaks included.
- **Compound card rotations** [from rebuild log, K7]: a pose built from X, Y and Z angles depends on
  `Transform3DOp.Rotate.RotOrder` (default "XYZ"; options XYZ, XZY, YXZ, YZX, ZXY, ZYX). The wrong order
  gives a visibly different pose with the same angles: set it deliberately whenever angles come from a
  spec, a tracker or another app.
- **Time**: author keys in the item comp's own frames (comp frame 0 = item start); never shift a
  motion-blurred 3D render with TimeSpeed [from rebuild log, K12] (section 8).
- (Rebuilding an existing AE comp: ae-matching.md.)

---

## 4. T2a: 2.5D Transform ladder (one controller, p written once)

Use when 3D is overkill (section 0). status: unverified (not yet rendered).

```
CAM25 (Custom, never wired into the image flow; a number holder)
SKY -----------------------------------------------------------------> M_FAR.Background
PlateFar   -> XF_FAR   (Transform) -> DOF_FAR   (Blur) ---------------> M_FAR.Foreground
M_FAR   -> HZ1 (Merge: Foreground <- HAZE, BlendClone 0.15) -> M_HILLS.Background
PlateHills -> XF_HILLS -> DOF_HILLS -> M_HILLS.Foreground;  M_HILLS -> HZ2 -> M_MID ...
PlateMid   -> XF_MID   -> DOF_MID   -> M_MID;               M_MID -> HZ3 -> M_FOCAL
PlateFocal -> XF_FOCAL -> DOF_FOCAL -> M_FOCAL -> M_FG <- DOF_FG <- XF_FG <- PlateFG
HAZE (Background, one node feeding HZ1..HZ3)
```

Controller `CAM25` (`Custom` tool, inputs `NumberIn1..8` [live-tested pattern]):

| Input | Meaning | Typical |
|---|---|---|
| `NumberIn1` | pan X, focal-plane frame widths (+ = world moves right) | keyed, ≤ 0.254 over 4 s |
| `NumberIn2` | pan Y, frame heights | keyed |
| `NumberIn3` | push Δ, fraction of z_f | 0 -> 0.1 over 72-120 f |
| `NumberIn4` | focus p (1 = focal plane) | 1.0; rack to 1.5 |
| `NumberIn5` | keep-alive X | expr `0.0008*sin(2*pi*time/24) + 0.0005*sin(2*pi*time/41 + 1.3)` |
| `NumberIn6` | keep-alive Y | expr `0.0006*sin(2*pi*time/29 + 0.7) + 0.0004*sin(2*pi*time/53 + 2.1)` |
| `NumberIn7` | K: blur units at \|Δp\| = 1 | calibrate (section 6) |

Per plane k with constant p (write the number into the expression; this is the only place p lives):
- `XF_k.Pivot` = (VPX, VPY), the vanishing point or ground-contact point (e.g. 0.5, 0.45).
- `XF_k.Center` expr: `Point(0.5 + p*(CAM25.NumberIn1 + CAM25.NumberIn5), 0.45 + p*(CAM25.NumberIn2 + CAM25.NumberIn6))`
  (first constants = VPX, VPY; Center must equal Pivot at rest or the plane shifts).
- `XF_k.Size` expr: `S0/(1 - p*CAM25.NumberIn3)` (exact dolly: p = 2 gives ×1.25 at Δ 0.1; sky p = 0
  stays 1). S0 = coverage = 1 + p × total pan + 0.02 for frame-sized plates.
- `XF_k.MotionBlur` 1, `Quality` 4-8, `ShutterAngle` 180 (each plane blurs its own motion; expressions
  are sampled per subframe [U]).
- `DOF_k.XBlurSize` expr: `CAM25.NumberIn7*abs(p - CAM25.NumberIn4)` (section 6).

Rules carried from AE:
- **Infinity plane p = 0 strictly.** The sky never moves a frame under pan.
- **Apparent-size law:** an element placed on plane p is authored or sized to p × its focal-plane
  size. Full-bleed plates are exempt from shrinking but must already contain content at that scale.
- **Push = no translation**, sizes only, about the VP pivot. Lateral pan = offsets down the ladder.
- Keep slow-to-fast spread 3-5× (far 0.07 to FG 1.5 is 21×; fine because the sky/far planes carry
  almost no geometry).

Verify: at `NumberIn1` = 0.1 the FG moved 0.15 W, focal 0.1 W, mid 0.05 W, far 0.007 W, sky 0;
with `NumberIn3` = 0.1 the FG measures ×1.176 and the sky ×1.

---

## 5. Atmosphere (exponential, color convergence, never opacity)

Aerial perspective belongs to vista planes. Per plane back, value rises toward sky, contrast drops,
hue shifts toward sky color, edges soften: all four together, monotonic. FG is the inversion (darkest
shadows, full saturation, sharpest edges). Pure black in a far plane is the loudest fake tell.

### R5. Fog3D, calibrated exponential haze (T1)
status: unverified (not yet rendered).

`STAGE -> HAZE3D (Fog3D) -> [SoftClip] -> RENDER`
- `FogType` "Exp"; `FogDensity` **δ = −ln(1 − H_far) / z_far**. Standard H_far = 0.45 at z 142.9 ->
  **δ = 0.0042** (haze: FG 3%, focal 4%, mid 8%, hills 19%, far 45%). Clear day H_far 0.25 -> 0.0020;
  dense mood 0.65 -> 0.0073. Tele shots ×1.5-2, wide ×0.5.
- `FogRed/Green/Blue` = sky horizon color, e.g. 0.651, 0.784, 0.847 (#a6c8d8, the AE far-mountain
  reference). The sky Background's bottom color must equal it exactly or the horizon seams.
- `Radial` 0 for trucks and dollies with frontal cards (each card gets uniform haze, like AE's per-plane
  ladder); 1 only for pans/orbits with geometry spread across the frame (radial fogs the edges of a
  near card more than its center).
- Keep the subject perfectly clean instead: `FogType` "Linear", `NearFogDist` = z_f (10),
  `FarFogDistance` = z_f + (z_far − z_f)/H_far (305 for 45% at 142.9) [U: Near/Far semantics for Exp].
- Fog is a color mix toward the fog color, so "flash the blacks", the saturation ladder and the blue
  shift all come from this one node. It is not opacity, so overlapping cards never show through.
- `Enable` is an effect toggle, not the node's power switch. `ShowFogInView` 1 to see it in the
  3D viewer when not looking through the camera.

Verify: sample a black pixel on each card in the render: far ≈ 0.45 × fog color, mid ≈ 0.08 ×; FG
blacks stay near 0. The far card's lowest value is never pure black.

### R6. 2.5D haze and per-plane grade (T2)
status: unverified (not yet rendered).

- **Equal haze passes between planes auto-compound the exponential:** HZ_k = Merge (`Background` <-
  stack, `Foreground` <- HAZE Background of sky color, `BlendClone` **0.15**) after FAR, HILLS and MID.
  Far sits behind 3 passes (39%), hills 2 (28%), mid 1 (15%), focal and FG none. Dense 0.20-0.25 per
  pass, clear 0.05-0.08. One HAZE node feeds all passes (change once, all update).
- **Saturation ladder** 1.0 / 0.85 / 0.70 / 0.50 FG-to-far: `BrightnessContrast.Saturation` on each
  plate (`PreDividePostMultiply` 1 on cutouts).
- **Flash the blacks:** `BrightnessContrast.Lift` 0 / 0.02 / 0.04 / 0.07 FG-to-far (Lift = pixel + lift
  × (1 − pixel), the direct Output-Black raise; no ramp matte needed per plane in Fusion). For a
  vertical falloff inside one plane add an EffectMask from a vertical-gradient Background through
  `BitmapMask` (`Channel` "Luminance").
- **Tint, not opacity.** Never fade far planes with Merge Blend or material Opacity; overlaps reveal
  what is behind.

### R7. Fog banks between planes (volumetric feel)
status: unverified (not yet rendered).

`FastNoise -> FOGCARD_k (ImagePlane3D)` placed between depth planes (e.g. z 30 and z 90), two or three
per gap offset 5-10% in Z and in noise `Center`:
- FastNoise: `Detail` 3-4, `Contrast` 0.6-1.0, `LockXY` 0, `XScale` 1, `YScale` 2.5 (stretched bank,
  not cloud; if the banks read vertical swap the ratio [U axis sense]), `SeetheRate` 0.05-0.1 (self-
  animates), `Center` expr `Point(0.5 + time*0.0004, 0.5)` drift.
- Color: `Color1Red/Green/Blue/Alpha` 0,0,0,0; `Color2Red/Green/Blue` = fog color × A,
  `Color2Alpha` = A = 0.25-0.35 (premultiplied; if edges brighten, check premult).
- Mask to the lower third: FastNoise `EffectMask` <- RectangleMask (`Center` 0.5, 0.3; `Width` 1.2;
  `Height` 0.45; `SoftEdge` 0.2).
- Card: `Transform3DOp.Translate.Y` = −0.25·H(z), scale = W(z) × 1.2.
- Renderer: `RendererOpenGL.TransparencySorting` 1 (Sorted) because semi-transparent fog cards overlap.
  Software renderer always sorts. **[live, efficiency lab, B5]** With accumulation effects on, Sorted can
  drop near-tied cards from some passes (flicker, dim cards, different pixels between Deliver jobs):
  render the same fog frames in two Deliver jobs and diff them; if they differ, spread the fog cards in
  depth or render the fog in its own renderer without accumulation. Scenes of opaque-ish flat cards use
  Z buffer (0) (section 8).
- Camera passing through fog cards: `SoftClip` before RENDER, `TransparentDistance` 0.5,
  `OpaqueDistance` 1.5, `SmoothTransition` 1.

2.5D equivalent: the same FastNoise merged between plane Merges with `ApplyMode` "Screen",
`BlendClone` 0.25-0.35, masked to the lower third (AE: fractal fog, Screen 25-35%, mask feather
~440 px @1080 = `SoftEdge` 0.23).

Verify: fog reads as banks behind the mid plane, never as a milky sheet over the subject.

---

