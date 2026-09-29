<!-- depth-space.md part 2 of 3; index: depth-space.md -->
## 6. Depth of field

### R8. Real DOF: OpenGL accumulation (T1 default)
status: unverified (not yet rendered).

On `RENDER`: `RendererType` "RendererOpenGL", then `RendererOpenGL.AccumulationEffects` 1 [C],
`RendererOpenGL.EnableAccumEffects` 1 [C], `RendererOpenGL.EnableAccumDepthOfField` 1 [C],
`RendererOpenGL.AccumQuality` 12-16 final (it is also the motion-blur sample count, section 8) [live,
efficiency lab], `RendererOpenGL.TransparencySorting` 0 (Z buffer; section 8) (shipped templates use 2-32),
`RendererOpenGL.DoFBlur` start **0.02** [C] (templates 0.01-0.1). Focus = `CAM.PlaneOfFocus` (distance
from camera; `PlaneOfFocusVis` 1 shows the green focal plane). Values from Blackmagic's
`Backgrounds/Platform Fly-Through.setting`, which publishes exactly these four controls.

Pick K, the blur of the infinity plane (sky), by scene scale:

| Preset | K (infinity CoC) | mid / hills / far / sky / FG 1.5 / hero FG 2.5 @1920 |
|---|---|---|
| Subtle (default, vistas) | 0.35% W ≈ 7 px | 3.5 / 5.6 / 6.5 / 7 / 3.5 / 10.5 |
| Cinematic (AE example) | 0.73% W ≈ 14 px | 7 / 11 / 13 / 14 / 7 / 21 |
| Tabletop (intentional miniature only) | ≥ 1.5% W | |

Calibrate `DoFBlur` once: render one frame, measure the 10-90% edge width of a hard edge on the far
card, scale `DoFBlur` proportionally toward the target, repeat once.

**DoFBlur unit [from rebuild log, K3].** `RendererOpenGL.DoFBlur` behaves as the lens aperture
**radius in scene units**: measured 10-90 % edge widths matched a disc circle of confusion at two
camera distances. General form: CoC diameter px = `DoFBlur x H x |1/f - 1/d| / tan(AoV/2)` (H =
render height px, AoV = the camera's vertical `AoV`, f = `PlaneOfFocus`, d = the card's distance along
the view axis, f and d in scene units). So the blur can be computed instead of guessed: for an infinity
(sky) blur of K px, `DoFBlur = K x f x tan(AoV/2) / H`. Canonical stage (f 10, AoV 19.26, 1080 high):
Subtle 7 px -> 0.011, Cinematic 14 px -> 0.022 (derived from the measured relation, not rendered
here); confirm on one render as above. (Rebuilding an existing AE comp: ae-matching.md.)

- **Split focus keeps geometry sharp:** if two geometry-carrying planes p_a and p_b must both read
  sharp, focus at p_f = (p_a + p_b)/2, i.e. `PlaneOfFocus` = z_f/p_f (harmonic mean of the distances);
  both then sit at 0.25·|p_a − p_b|·K.
- **Rack focus** (a depth cue in itself): keys on `PlaneOfFocus` 10 -> 6.67 (subject to FG) over
  12-24 f @24 (13-25 @25, 15-30 @30), ease (0.33, 0, 0.67, 1). During a dolly use the R3a expression
  plus the rack offset.
- Accumulation DOF works with Fog3D and anti-aliasing (unlike 2D Fog). **[live, efficiency lab, P0]**
  It is nearly free in Deliver (+0.07 s/frame at 12 passes on a 1,100-tool scene): passes at one time
  reuse the uploaded textures; it does not multiply with motion blur (the old "AccumQuality x motion-blur
  samples" cost model is wrong for OpenGL with accumulation on). Supersampling: `RendererOpenGL.AntiAliasing.Channels.RGBA.HighQuality.Enable` 1,
  `RendererOpenGL.AntiAliasing.Presets.Color.Supersampling.HighQuality.RateX/RateY` 3 [C].
- Miniature guard: the DOF amount must match the implied scene size. Vistas ≤ Subtle.

Verify: sky blur ≈ K, focal card sharp at 1:1, mid ≈ K/2; bokeh on speculars is round.

### R9. 2D DOF from Z (T1 with the Software renderer, or external renders)
status: unverified (not yet rendered).

Needed when the shot also needs Software-only soft shadows (one renderer cannot do both).
- `RendererSoftware.Channels.Z` 1 on RENDER (Z is eyespace, negative into the scene, not anti-aliased).
- CoC map: `Custom` tool `COC`, `Image1` <- RENDER; `RedExpression` =
  `if(z1 > -0.0001, 1, abs(n1/(-z1) - n1/n2))`, same in Green/Blue, `AlphaExpression` `1`;
  `NumberIn1` = z_f (10), `NumberIn2` = focus distance (10, keyable for rack focus). Output = |p − p_f|
  with sky = 1. (Custom Tool channel vars `z1`, `n1..n8`, `if()` per the manual; sky Z value [U].)
- `VariBlur`: `Input` <- RENDER, `BlurImage` <- COC, `BlurChannel` Red [U index 0], `XBlurSize` = K
  (calibrated), **`BlurLimit` ≥ 2** (default 0.5 clamps the map), `Method` 2 = Defocus disc [U index].
- Known 2D-DOF flaw: a blurred FG cannot spread over a sharp BG on a flattened image. Render FG cards
  in their own Renderer3D (section 9, light wrap) and blur that layer before the merge.
- Quick alternative: `DepthBlur` (`BlurChannel` = Z [U index], `FocalPoint` = −z_focus [U sign],
  `DepthOfField` = in-focus band width, `ZScale` 1 or ~0.2 for float per the manual recipe, sample the
  focal pixel with the Inspector pick). It models a linear in-focus band, not |p − p_f|.

### R10. 2.5D DOF (T2)
status: unverified (not yet rendered).

- **Per-plane blur is exact and edge-safe:** `DOF_k.XBlurSize` = `CAM25.NumberIn7*abs(p - CAM25.NumberIn4)`.
  Static focus at the focal plane reproduces the 4:6:7 ladder; keying `NumberIn4` 1.0 -> 1.5 over
  12-24 f is a rack focus to FG with no camera.
- Calibrate `NumberIn7`: render, measure the sky edge, adjust until the sky blur = K px.
- Specular bokeh on a far plane: `Defocus` (`Filter` 1 = Lens [U index], `BloomThreshold` start 1.0 and
  lower until only true speculars bloom, `BloomLevel` 0.3-0.6, `XDefocusSize` calibrated). Anamorphic
  squeeze S: `LockXY` 0, `YDefocusSize` = S × `XDefocusSize` (tall ovals). Optional taste.

---

## 7. Grounding and the perspective floor

One soft shadow = floating object. Dark contact core + wide weak skirt = "touches the floor", and the
floor then exists as a plane.

### R11. Real floor (T1)
status: unverified (not yet rendered).

`FloorTex -> Texture2DOperator -> FLOOR (Shape3D.MaterialInput) -> STAGE`
- `FLOOR`: `Shape` "SurfacePlaneInputs", `SurfacePlaneInputs.Width` 400 (lock on),
  `SurfacePlaneInputs.SubdivisionWidth` 40 (vertex lighting quality), `Transform3DOp.Rotate.X` −90,
  `Transform3DOp.Translate.Y` = −eye height (1.6 when 1 unit ≈ 1 m at z_f 10),
  `Transform3DOp.Translate.Z` −195 (spans from just behind the camera to z ≈ 395).
- Tiling: `Texture2DOperator.UScale/VScale` 20-60, `WrapMode` "Wrap" (image input ID [U]).
- Perspective compression 1/z of texture rows is automatic: this replaces AE's CC Power Pin.
- Horizon = eye level. With a level camera it sits at frame center; to put it at y 380-540 @1080
  (normalized 0.5-0.65), tilt `CAM.Transform3DOp.Rotate.X` by −atan((y_h − 0.5)·2·tan(vFOV/2))
  (−1.9° for 0.6 at 35 mm), or use `LensShiftY` to keep verticals parallel [U units and sign].
- Standing cards: bottom edge on the floor (`Translate.Y` = −eye + card height/2, card height =
  scale/aspect). Cards at the ladder Z automatically sit at the right perspective height.

**Floor light (inverse square, "quarter per doubling").** `LightPoint` above the subject, `DecayType`
2 = Quadratic [U index; manual order No Decay/Linear/Quadratic], `Intensity` 1, plus `LightAmbient`
`Intensity` 0.3-0.5. Enable `RendererOpenGL.LightingEnabled` [C] or `RendererSoftware.LightingEnabled`.
Keep cards unlit: `SurfacePlaneInputs.Lighting.IsAffectedByLights` 0 on cards (live-tested: a display
card looked right with that at 0 and `MtlStdInputs.ReceivesLighting` 1). With lighting on and no
lights, everything renders black. Never set `MtlStdInputs.ReceivesLighting` 0 to mean "unlit": the
card renders RGB black in OpenGL, alpha intact [from rebuild log, K4].

### R12. Shadow cards (fast, works with accumulation DOF)
status: unverified (not yet rendered).

Two cards lying on the floor per grounded object:
- **Contact core:** Background black, `EffectMask` <- EllipseMask (`Width` = object footprint,
  `Height` = Width × 0.35, `SoftEdge` 0.01-0.02) -> ImagePlane3D rotated `Rotate.X` −90 at the object's
  base, `MtlStdInputs.Diffuse.Opacity` 0.35-0.5.
- **Cast skirt:** the object's cutout -> `BrightnessContrast.Gain` 0 (RGB black, alpha kept) -> Blur
  (calibrate to 24-48 px @1920) -> ImagePlane3D rotated −90 about its bottom edge
  (`Transform3DOp.Pivot.Y` = −half height), `Transform3DOp.Scale.Y` 0.3-1.0 (sun height; unlock
  `Transform3DOp.ScaleLock`), `MtlStdInputs.Diffuse.Opacity` 0.12-0.2, extending away from the light.
- Lift both **0.002 units** above the floor or they Z-fight and flicker.

Verify: object base, contact core and floor meet with no gap in any frame of the move; no flicker.

### R13. Real soft shadows (Software renderer)
status: unverified (not yet rendered).

- `LightSpot` aimed at the subject (`Transform3DOp.UseTarget` 1), `ConeAngle` 40-60,
  `ShadowLightInputs3D.SoftnessType` "Variable", `ShadowLightInputs3D.Spread` 2-5,
  `ShadowLightInputs3D.ShadowDensity` 0.5-0.7, `ShadowLightInputs3D.ShadowMapSize` 2048-4096; fix
  acne with `ShadowLightInputs3D.MultiplicativeBias` first, then `ShadowLightInputs3D.AdditiveBias`.
- Renderer: `RendererType` "RendererSoftware", `RendererSoftware.LightingEnabled` 1,
  `RendererSoftware.ShadowsEnabled` 1, `RendererSoftware.Channels.Z` 1 (for R9 DOF).
- **Unlit card + invisible caster twin:** an unlit card (`SurfacePlaneInputs.Lighting.IsAffectedByLights` 0) casts no shadow, so
  duplicate it: twin with `SurfacePlaneInputs.Visibility.IsUnseenByCameras` 1, lit, `SurfacePlaneInputs.Lighting.IsShadowCaster` 1,
  `MtlStdInputs.Transmittance.AlphaDetail` 1 (alpha shapes the shadow). Unseen objects still cast in
  the Software renderer (not OpenGL).
- The OpenGL renderer casts shadows from the whole card rectangle, always black. Never judge cutout
  shadows in OpenGL.

### R14. 2.5D grounding and floor (T2)
status: unverified (not yet rendered).

- Double drop shadow from alpha (all TSV inputs): cutout -> `BrightnessContrast.Gain` 0 -> Transform
  `Center` offset down 3 px (0.5, 0.5 − 3/1080) -> Blur (6 px target) -> Merge under the object,
  `BlendClone` 0.20 (contact); second branch offset 12 px, blur 36 px target, `BlendClone` 0.13
  (ambient). The `Shadow` tool (`ShadowOffset`, `Softness`, `Alpha`) is the one-node alternative
  [U offset/softness units].
- On a perspective floor: shadow-only branch, Transform `Pivot` = `Center` = contact point,
  `UseSizeAndAspect` 0, `YSize` 0.3, `FlipVert` 1, Blur 10-20 px target, Merge `ApplyMode` "Multiply",
  `BlendClone` 0.2-0.3.
- Floor: `CornerPositioner` `MappingType` 1 = Perspective (default; 0 = Bi-Linear reads as a tilted
  wall) [U index]. AE example horizon y 430 @1920×1080: `BottomLeft` (0, 0), `BottomRight` (1, 0),
  `TopLeft` (0.4, 0.4815), `TopRight` (0.6, 0.4815). Far edge width = near × z_near/z_far.
- Floor light before the pin: Background `Type` "Gradient", `GradientType` "Radial", stops
  [0] 1.0, [0.25] 1.0, [0.5] 0.25, [1.0] 0.0625 (quarter per doubling), Merge `ApplyMode` "Multiply".
  Linear gradient = airbrush.

---

## 8. Motion blur (mandatory)

FG planes at 1.2-1.5× speed strobe without it.

- **T1 with accumulation (the default renderer setup) [live, efficiency lab, T02]:** the sample count is
  `RendererOpenGL.AccumQuality` (12 for fast moves; 6 showed stepping at SSIM 0.93); `Quality` adds nothing
  at or below it (Quality 1 and 8 rendered identically at AccumQuality 12). Distinct time samples are the
  real cost (~0.7 s/frame on a 1,100-tool scene): switch `MotionBlur` off on frames where nothing moves
  (on-screen streak under ~0.75 px; bake a per-frame table from the camera and card splines and drive
  `MotionBlur` with `:local q={...}; return q[floor(time+0.5)+1] or 1`): -24 % on a hold-heavy range,
  pixels at noise level.
- **Transparency under accumulation [live, efficiency lab, B5]:** `RendererOpenGL.TransparencySorting` 0
  (Z buffer). Sorted (1) re-sorts near-tied cards per pass and drops them from some passes (a card
  missing on odd frames, a headline at 40 %, different pixels between two Deliver jobs); Z buffer was
  deterministic and matched the reference on a whole film of flat cards.
- **T1 without accumulation:** `RENDER.MotionBlur` 1, `Quality` 6 (4 preview, 8-10 fast FG), `ShutterAngle` 180,
  `CenterBias` 0 (centered, the AE "phase −90 at 180" ideal), `SampleSpread` 1. The camera move blurs
  every card by its own screen speed; expression-driven wiggle is sampled per subframe [U verify]
  (sub-frame evaluation of everything upstream, textures included, is confirmed: K13 below).
  Particles in the scene: `pRender` motion-blur settings must match the Renderer3D exactly.
- **T2:** `MotionBlur` 1, `Quality` 4-8, `ShutterAngle` 180 on every animated `XF_k` Transform.
  Expression rigs need no keys to blur correctly.
- Over budget (section 3 table)? `ShutterAngle` 270-360 buys ×1.5-2 speed: smear reads as speed,
  judder reads as broken playback.
- **Fast path:** `RendererOpenGL.Channels.Vector` 1 [C], Renderer MotionBlur 0, then
  `VectorMotionBlur` (`Input` <- RENDER, vectors from its aux channels, `XScale` 0.5 ≈ 180° [U]).
  Cheap, wrong at occlusion edges. Blackmagic's `How To/Vector-Blur.setting` shows the wiring.
- **Sharp-scroll trap (AE "never scroll with Offset"):** texture offsets (`Texture2DOperator.UOffset`),
  generator internals (`FastNoise.Center`, gradient `Offset`) and similar do not blur unless that tool's
  own motion blur is on [U]. A sharp BG under a blurred FG inverts the depth cue. Move pixels with
  Transform/Merge/3D transforms with MotionBlur on; for tiling scrolls use Transform `Edges` 1 (Wrap
  [U index]) with animated `Center`.
- Groups do not hide motion (unlike AE precomps). But motion applied downstream of a flattened stack
  (a Transform after the final Merge) blurs all planes equally: the depth cue dies.
- **Hold card textures at integer frames [from rebuild log, K13].** Renderer3D motion blur and
  accumulation DOF evaluate the scene at sub-frame times, and every sample re-renders each animated 2D
  texture graph upstream of an ImagePlane3D (a 1,100-tool UI scene: 32 s/frame in Deliver, about 2 h
  for one scene). Put a `TimeStretcher` between each card texture and its ImagePlane3D:
  `SourceTime` expression `floor(time + 0.5)`, `InterpolateBetweenFrames` 0 (Nearest). The texture is
  then evaluated once per frame (its content steps per frame) while camera and card transforms keep
  full motion blur: 1.6 s/frame, and a whole 750-frame, 8-scene piece Delivered in 13 min. Use it on
  every animated card texture by default; skip it only where the texture's own internal motion must
  blur (then blur that motion in 2D). **[live, efficiency lab, T03]** The hold still re-renders the
  texture once per frame: for a card whose texture never changes use a constant `SourceTime` (served
  from the cache on every later frame, also in Deliver), and inside animated textures freeze each static
  sub-branch with its own constant-time TimeStretcher where it meets an animated tool (73 freezes on a
  1,100-tool scene: bit-identical, -19 %).
  ```lua
  S5_Type_Hold = TimeStretcher { Inputs = {
      Input = Input { SourceOp = "T_TYPE_Mrg", Source = "Output", },
      SourceTime = Input { Value = 0, Expression = "floor(time + 0.5)", },
      InterpolateBetweenFrames = Input { Value = 0, }, }, },
  S5_Type = ImagePlane3D { Inputs = { MaterialInput = Input { SourceOp = "S5_Type_Hold", Source = "Output", }, }, },
  ```
  (Shape of the rebuild's pasted text, names shortened.)
- **Opacity under a motion-blurred Renderer3D ghosts at in-points [from rebuild log, K15].** The
  shutter samples material opacity (`MtlStdInputs.Diffuse.Opacity`) too: a 0 -> 1 ramp starting at
  f600 was about 8 % visible at f600.25, so the incoming word showed as a one-frame ghost before its
  cut-in. When a clean cut-in or cut-out matters, key opacity as a per-frame staircase, value(n) held
  on [n - 0.5, n + 0.5): key pairs at n + 0.499 (value n) and n + 0.5 (value n+1), e.g.
  `[52.5] = { 0 }, [53.499] = { 0 }, [53.5] = { 1 }` shows the card from f54 exactly. Start the ramp on
  the in-point key, not half a frame early. Smooth opacity blur is fine for soft dissolves.
  (Rebuilding an existing AE comp: ae-matching.md.)
- **Never retime a 3D render with TimeSpeed [from rebuild log, K12].** A `TimeSpeed` (`Delay` -48)
  after a motion-blurred Renderer3D made one frame take 189 s and another abort with "failed to get
  scene at time 100.083333". Offset the keys (and `time` in expressions) instead.
- **Sample counts [from rebuild log, COMPARE polish pass]:** a fast card passing the lens showed stepped
  copies at `Quality` 8; 16 removed them; a fast ring wipe needed 32 to stop banding. Raise the sample
  count for the fastest element in the shot, not the average. With accumulation on that count is
  `AccumQuality` (Quality 1 vs 8 identical at 12 passes [live, efficiency lab, T02]); the stepped copies
  seen then also fit the Sorted-transparency dropouts above.

---

## 9. Edges and unification (one lens, one sensor)

### R15. Light wrap (kills the sticker look)
status: unverified (not yet rendered).

T1 needs the FG as its own layer: split into `STAGE_BG` and `STAGE_FG` Merge3Ds fed by the same CAM
(one output may feed many inputs), each through its own Fog3D (same settings) and Renderer3D, then:

```
RENDER_BG -> [LumaKeyer Low 0.9: bright-only wrap, optional]
          -> WRAP_IN  (MatteControl: Background <- above, Garbage.Matte <- BitmapMask(Image <- RENDER_FG, Channel "Alpha"))
          -> WRAP_S   (Blur, rim 5-10 px target) -> WRAP_L (Blur, 60-100 px target, BlendClone 0.4)
          -> WRAP_OUT (MatteControl: Garbage.Matte <- same BitmapMask, Garbage.MaskInverted 1)
BASE = Merge(Background <- RENDER_BG, Foreground <- RENDER_FG)
LW   = Merge(Background <- BASE, Foreground <- WRAP_OUT, ApplyMode "Screen", BlendClone 0.70-0.75)
```

Structure from Blackmagic's `How To/Light-Wrap.setting` (which uses the legacy input name
`GarbageMatte` and an additive merge with `Gain` 0; the TSV ID is `Garbage.Matte`). The garbage matte
cuts a hole in the BG where the FG is, the blurs bleed BG light into the hole, the inverted matte
keeps only the bleed inside the FG edge. Screen 70-75% matches the AE value.

**Cutout hygiene (every plate with alpha, before it becomes a card):**
`AlphaDivide -> ErodeDilate (Red/Green/Blue 0, Alpha 1, XAmount −0.0005 ≈ −1 px @1920) -> Blur
(Red/Green/Blue 0, Alpha 1, ~1-2 px target) -> AlphaMultiply` (feather-then-choke 1-2 px; Controls-tab
channel buttons skip the RGB work).

### R16. Grain, vignette, lens contract
status: unverified (not yet rendered).

- **Grain: one pass over the finished frame** (`FilmGrain` after the last Merge, `Monochrome` 1,
  `MasterStrength` 0.04-0.08, default 0.1 as the ceiling). Never grain plates: in 3D the card's scale
  and distance change grain size per plane (several sensors). Degrain noisy plates before carding.
- **Vignette:** Background black with `EffectMask` <- EllipseMask (`Invert` 1, `Width` 1.3,
  `Height` 0.73 = Width × 9/16 because ellipse axes are both width-relative [live], `Center` 0.5, 0.53,
  `SoftEdge` 0.18-0.26 = 350-500 px @1920) -> Merge over the comp, `BlendClone` 0.2-0.4. Subtle depth
  element: `BlendClone` 0.1, `SoftEdge` 0.1.
- **Lens contract, one number for the whole stack:** one `LensDistort` on the final comp (`Model`
  "FusionRadial", `FusionRadial.LowOrderDistortion` ±0.02-0.05 for soft wide curvature [U sign for
  barrel], `Mode` Distort [U index]). Live plates: undistort first with the same model, re-distort
  once at the end.
- **Chromatic aberration in corners only:** two channel-limited Transforms on the final comp, `Size`
  1.005 with only red processed (common `ProcessGreen`/`ProcessBlue`/`ProcessAlpha` 0) and `Size`
  0.995 with only blue processed. Split at the corner = 2 × 0.005 × 0.574 W ≈ 0.57% W ≈ 11 px @1920
  (target 0.5-0.75%), zero at center.
- One artifact without its siblings = filter; a correlated set (distortion + CA + vignette + one bokeh
  shape + one grain) = a lens.

---

## 10. Single-image parallax

### R17. T1b: Displace3D relief card (preferred in Fusion)
status: unverified (not yet rendered).

`Photo -> CARD (ImagePlane3D, SurfacePlaneInputs.SubdivisionWidth 200-400) -> RELIEF (Displace3D, Input <- DepthMap) -> STAGE`
- Map convention: FAR = 0 (black), NEAR = 1 (white). Displacement = (map + `Bias`) × `Scale` along the
  normal (Bias first). `Scale` = relief depth R = 0.1-0.25 · z_f (1-2.5 units at z_f 10), `Bias` 0.
- `PointCamera` 1 with `CameraSelector` = CAM: vertices move toward the camera, so through CAM the
  photo looks untouched while it gains real Z; DOF, fog and motion blur then come from the scene.
- Displace3D adds no vertices: detail = card subdivision. `Channel` = luminance [U index].
- Budget: screen disparity for truck x ≈ x·R / (z_f(z_f − R)) × 1.657 frame widths; keep ≤ 0.02
  (z_f 10, R 2: x ≤ 0.48 units). Large disparity stretches rubber sheets at depth edges.

### R18. T2b: 2D Displace
status: unverified (not yet rendered).

`Photo -> DSP (Displace.Input); MapPrep -> DSP.Foreground`
- `Type` 1 = X/Y [U index; manual order Radial, X/Y], `XChannel` 4 = Luminance [U index],
  `XRefraction` animated ±D, `YRefraction` 0 or ≤ D/3.
- Budget: total spread ≤ 1.5-3% width (AE: max 15-29 px @1080, ±58 px red line). Calibrate the
  unit once: constant-1.0 map, `XRefraction` 0.01, measure the shift; then set D for 0.8-1.5% W.
- Neutral: AE needed exact 128 gray. In Fusion's float pipeline 0.5 is exact, but whether X/Y mode
  displaces around 0 or 0.5 is [U]: with a constant-0 map the frame must not move; if it does, cancel
  with `XOffset`. Author FAR = locked (zero shift) so the far plane never drifts.
- Loop, camera-less: `XRefraction` expr `0.012*sin(2*pi*time/120)` (5 s period @24).
- **Map prep (tearing and banding are the failures):** `BetterResize` the map to the plate resolution
  first (AI depth maps are low-res; upscale stairs become displacement bands), then Blur ≈ the
  displacement size, then a vertical-only Blur 1.5-2× stronger (`LockXY` 0, `YBlurSize`), plus 3-5%
  noise for 8-bit maps (`FastNoise` merged at `BlendClone` 0.04). Hard silhouette steps = tearing.
- **Threshold to cutouts:** needed spread > ~2-3% width -> cut the photo into cards (mask each plane
  +10-15 px, fill holes behind FG), then T1.
- **One map, three cues** (consistent because one source): (a) DOF: map -> Custom `RedExpression`
  `abs(r1*4 - n1)*n2` (p ≈ 4·map, `NumberIn1` focus p, keyable rack focus) -> `VariBlur.BlurImage`;
  (b) haze: Merge `Foreground` <- HAZE color, `EffectMask` <- BitmapMask (`Image` <- map, `Channel`
  "Luminance", `Invert` 1), `BlendClone` 0.4; (c) the same map drives R17 if you upgrade to 3D.

---

## 11. Vertical 9:16 (1080×1920): different budgets

- Render: timeline or `RENDER.Width` 1080 / `Height` 1920 (`UseFrameFormatSettings` 0 if the comp
  format differs; these Renderer3D inputs are in the live harvest JSON, not the TSV).
- **Portrait film back:** swap the gate, `ApertureW` 0.4677, `ApertureH` 0.8315 (`FilmGate` becomes
  "User"), keep `ResolutionGateFit` "Height", `FLength` 24-28. Without the swap, "Height" fit keeps the
  landscape vertical FOV (19.3°) and 9:16 becomes a telephoto sliver. Portrait W(z) = z × 11.88/f,
  H(z) = z × 21.12/f.
- **Lateral de-rated:** fastest plane total travel ≤ 1.5% W (16 px) for continuous moves, 3-3.3% W
  (32-36 px) for one slow reveal. At FG z 6.67, 35 mm portrait: plain truck ≤ 0.034 units.
- **Vertical is the star:** 3% H = 57.6 px. Pedestal (`Translate.Y`) ≤ 0.03·H(z_fg) (≤ 0.12 units at
  z 6.67, 35 mm portrait), tilt, and push-in (R3a, Δ 0.05-0.1 z_f). Avoid pans.
- **T2 Y-rig:** `NumberIn2` with per-plane k = 0.2 / 0.5 / 0.8 / 1.0 / 2.0 (the p column).
- **Horizon slots:** normalized Y **0.667** (y 640 from top: long receding ground, max texture
  gradient) or **0.333** (y 1280: near band plus sky scale); never dead center without intent.
  Vanishing point X 0.5 ± 0.083 (540 ± 90 px).
- **Safe depth core:** anchors that carry depth (VP, subject eyes, occlusion nodes) inside X
  0.083-0.917, Y 0.135-0.865 (900×1400 centered), and inside the 4:5 crop core Y 0.149-0.852. Outer
  bands are sacrificial garnish under platform UI.

---

