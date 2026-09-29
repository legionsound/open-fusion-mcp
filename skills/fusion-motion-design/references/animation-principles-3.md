<!-- animation-principles.md part 3 of 3; index: animation-principles.md -->
## 12. Stagger and offset patterns

**Formula:** `start_i = startDelay + i * stagger` (frames = seconds x fps).

| Tier | Per element | @24 | @25 | @30 | Use |
|---|---|---|---|---|---|
| Micro (same group children) | 40-60 ms | 1-1.5f | 1-1.5f | 1.2-1.8f | Rows, list items, stat cells, icon clusters |
| Premium menus/cards | 50-100 ms | 1.2-2.4f | 1.25-2.5f | 1.5-3f | Menus, cards |
| House distinct panels | 150 ms (120-180) | 3.6f (3-4) | 3.75f | 4.5f | Separate beats (Heart Rate -> Step Distance) |
| Avoid | > 150 ms | > 3.6f | | > 4.5f | Cascade reads sluggish |

Keep the whole sequence under 2 s: `startDelay + (N-1)*stagger + element_window < 2 s`; shrink stagger toward 40 ms before stretching the window. 12 cards -> about 80 ms; 30 cells -> stagger by row/diagonal.

Fusion mechanisms (pick by structure):
1. **Text characters:** Follower `Delay` (DelayType 1) or total spread (DelayType 2); `Order` 2/3 for center-out / edges-in.
2. **Separate tools, one curve:** each element reads a shared controller at an offset: `CTRL:GetValue("NumberIn1", time - start_i)` (verified). Change the master curve once and every element updates. This is the Fusion answer to per-layer keyframes.
3. **Repeated copies of one animated source:** `Fuse.Duplicate` `TimeOffset` (per copy; -1 = each copy one frame earlier; chained copies compound transforms), `sDuplicate` `TimeOffset` (shapes; X/Y Size and rotation compound from the previous copy), `Duplicate3D` `TimeOffset` (3D).
4. **Branch offset (precomp slide):** `TimeSpeed.Delay` = +N frames later; UI Keyframes Editor T Offset on selected keys.
5. **Negative start (seamless loops):** read at `time + P - start_i` wrapped with `% P` so the cycle is already mid-flight at f0.
6. **From-origin cascade:** order `i` by distance from the origin: center-out `i = abs(k - (N-1)/2)`, last-first `i = N-1-k`.

**Worked 3-dot loader (24 fps):** period P = 15f (0.625 s), stagger 5f (P/3), each dot `DOT_k_XF.Size = 0.8 + 0.4*CTRL:GetValue("NumberIn1", (time - 5*k + 15) % 15)` where `CTRL.NumberIn1` is keyed 0@0 -> 1@7 -> 0@15 (SINE_IO both segments, flat extrema). Alive from frame 0, seamless forever.

---

## 13. Motion taste: orchestration, reveal grammar, review beats

**Per-property orchestration:** Locked (all start/end together: UI panels, mechanical states); Lead/follow (one property leads by 1-3f: logo, hero, organic); Primary/secondary (one carries, others support); Early-opacity / late-settle (Blend resolves in about half the move while Center/Size settle); Single-property overshoot (only Size or Angle overshoots, Center stays controlled). Hierarchy rule: only the focal element gets personality (pop, overshoot, snap); support gets quiet settles; accents never steal the read.

**Reveal grammar:** build -> settle -> hold (the hold is where the message registers). Reveal in reading/importance order. Prefer mask wipes, draw-ons (mask `WritePosition/WriteLength`, `KD_ShapeWriteOn`), marker sweeps and purposeful cuts over uniform fades for premium scenes. One main flourish per beat.

**Data and figure motion:** bars grow from the baseline (Transform `Pivot` at the bar base, animate `YSize` with `UseSizeAndAspect 0`), lines draw left to right (mask/shape `WriteLength` 0 -> 1), rings sweep (`sEllipse Solid 0` + `WriteLength`), dots populate (Duplicate TimeOffset). Count-ups near-linear with an ease-out landing (COUNT_UP). Labels arrive after the value resolves. Serious data = calm ease-out, no bounce.

**Camera:** one dominant move per scene; camera easing smoother than objects inside; never unreadable text mid-move.

**Motion economy:** motion reinforces the final frame's hierarchy. Animate fewer properties when it reads clearer; stillness gives contrast. If the scene feels busy, simplify the layout first.

**Review beats (scrub, do not trust endpoints):** frame 0 · first meaningful beat · midpoint · settle start · final frame · loop seam · every semantic beat (number resolves, word lands, logo locks, CTA appears). The midpoint must communicate; the final settle must land in the strongest composition; the last 10-20% of motion must feel intentional; loop seams invisible.

Fusion QC procedure:
1. **Numeric pass (cheap):** `sample(tool, input, frames)` at the beats above; compare to the curve table (y@25/50/75) and to exact rest values; check f0 vs fL for loops; check stagger starts.
2. **Pixel pass:** render stills at the beats (Saver `PNGFormat` rendered in Resolve 21.1, live-verified; `comp.Render({"Start": f, "End": f, "Wait": True})`, then inspect the files, the return value alone is not proof).
3. **Motion pass:** a short PNG sequence or the Deliver page at final fps, with motion blur on; judge at 1x speed.

---

## 14. Motion blur in Fusion

| Case | Where | Settings |
|---|---|---|
| 2D moves (Transform/Merge/Text+/shapes) | The tool **whose own inputs animate** (usually `EL_XF`). Settings-tab common inputs: `MotionBlur`, `Quality`, `ShutterAngle`, `CenterBias`, `SampleSpread` (TSV/json) | `MotionBlur 1`; `Quality` 2 default, 4 for fast UI moves, 6-8 for smash/snap; `ShutterAngle` 180 (cinematic), 90-120 crisp UI, 270-360 smash smear; `CenterBias 0`, `SampleSpread 1` |
| Shape chains | `sRender` only (shape nodes' Settings apply only there) | same |
| 3D scenes | `Renderer3D` Settings tab (same five inputs); particles: `pRender` motion blur must match Renderer3D exactly | Quality 4-8; cost multiplies scene render |
| Footage, pre-rendered plates, or cheap 3D blur | `VectorMotionBlur` (`Vectors` input, `XScale` about 0.5 = 180 deg) fed by vector aux: `Renderer3D RendererSoftware.Channels.Vector 1`, or `Dimension.OpticalFlow` upstream | vectors must be float; TimeSpeed/TimeStretcher destroy vector channels |
| Stylized streak | `DirectionalBlur` (`Length`, `Angle`) keyed | smash cuts, whips |

Rules: a static downstream node does not blur upstream animation, enable MB on the animated tool. Enable it per revealed element, not on everything (the AE per-layer rule carries over). Disable it for glitch steps and posterized motion. The viewer shows blur only with the viewer Motion Blur toggle / HiQ; final renders include it. Rotation and scale blur need a correct `Pivot`.

---

## 15. Ported bundle helpers (Fusion equivalents)

| AE helper | Fusion equivalent | Status |
|---|---|---|
| `easeIO` (in22/out75 on every key) | `keys(points, [HOUSE]*n)` per segment | mechanics verified |
| `countUp(textLayer, t0, dur, target)` | R13: keyed `CTRL.NumberIn1` + `StyledText` expression with `Text(string.format(...))`, tabular digits | unverified |
| `drawOn(shape)` (Trim Paths 0 -> 100) | Mask tools with `Solid 0` + `BorderWidth`: key `WriteLength` 0 -> 1 (`WritePosition` = start offset); shapes: `sEllipse`/`sRectangle` `WriteLength`, or `KD_ShapeWriteOn` `RangeStart/RangeEnd/Shift`; HOUSE ease | unverified |
| `progressRing(shape, pct)` | `sEllipse` (`Solid 0`, `BorderWidth` 0.004) -> `sRender`; key `WriteLength` 0 -> pct; rotate the start to 12 o'clock with `Angle` (start point unverified) | unverified |
| `shimmer(band)` | `Background` `Type "Gradient"` with a narrow white stop, `Repeat "Repeat"`, key `Offset` 0 -> 1 linear with Loop flags; or a thin `RectangleMask` band (Angle 18) whose `Center` sweeps; merge at `Blend 0.35` | unverified |
| `pulseLoop(min 96, max 108, period 1.2)` | `Size = 0.96 + 0.12*(0.5 + 0.5*sin(2*pi*time/(1.2*F)))` | mechanics verified |
| `easeSnap` (symmetric 85) | IO_85 handles on every segment | mechanics verified |
| `addOvershoot(amp .10, freq 2.6, decay 5.5)` | Section 5.3 expression, `G` 0.10, `Hz` 2.6, `DEC` 5.5; never combine with easeSnap on the same property | mechanics verified |

When to reach for each (match the reference, do not add what is not there): countUp for a metric, drawOn for line icons/underlines/connectors, progressRing for gauges, shimmer for skeleton loaders, pulse for live dots/badges/recording indicators, overshoot for a tactile drop-in, easeSnap for smooth camera/opacity snaps.

---

## 16. The house reveal recipe (default entrance for every element)

Ground truth (user-approved AE keys, 30 fps authoring, keep the **seconds**):

| Property | Key 1 | Key 2 | Fusion input | Curve |
|---|---|---|---|---|
| Position | t0: baseY + 42 px below | t0 + 0.70 s: baseY | `EL_XF.Center` Y (or via CTRL progress) | HOUSE_SETTLE |
| Scale | t0: 95% | t0 + 0.70 s: 100% | `EL_XF.Size` 0.95 -> 1.0 | HOUSE_SETTLE |
| Opacity | t0 + 0.21 s: 0 | t0 + 0.33 s: 1 | `EL_MRG.Blend` | HOUSE_SETTLE (or SINE_IO) |

Frames: 0.70 s = 17f @24 (17.5 @25 -> 18, 21 @30); opacity 0.21-0.33 s = 5-8f @24 (5-8 @25, 6-10 @30). Stagger between distinct cards 0.15 s (3.6f @24; use 4, or fractional); same-group children 40-60 ms (1-1.5f).

Mandatory core: scale 0.95 -> 1.00 over the 0.70 s window; fast fade starting 0.21 s after t0 (never a hard pop); settle-weighted Bezier on every key, never linear, never hold.
Optional: the rise (42 px at 1080 = 0.039 H; scale it to 6-10% of element height, or drop it where a lift reads wrong); stagger 0.12-0.18 s as a feel knob.
Exit: mirror it: drop 0.039 H, scale to 0.95, Blend to 0 over about 0.4 s with IN_70.
Follow-through/overshoot: panels and modals only (spring Z >= 0.72). **Text and small chrome (icons, badges, labels, rows) get none.**
Seals/emblems: fade in, then spin forever (R16).
Motion blur: per revealed element (`EL_XF.MotionBlur 1`, Quality 4, ShutterAngle 180).
Settlement phases: primary move 0-400 ms, children overlap on a 30-60 ms stagger, visually settled by about 600 ms, whole group under 2 s. Looping reveals: negative start on the group, not per element.

### Python (one shared curve, N staggered elements; mechanics verified)

```python
def house_reveal(elements, start_sec=0.15, step_sec=0.15, rise=0.039):
    """elements: list of (xf_tool, mrg_tool, (x, y)) with sources centered; x,y = rest position."""
    ctrl = add("Custom", "REVEAL_CTRL", -300, -300)          # never wired into the image path
    animate(ctrl, "NumberIn1", [(0, 0.0), (F(0.70), 1.0)], [HOUSE])          # rise+scale progress
    animate(ctrl, "NumberIn2", [(F(0.21), 0.0), (F(0.33), 1.0)], [HOUSE])    # opacity progress
    for i, (xf, mrg, (x, y)) in enumerate(elements):
        off = (start_sec + i * step_sec) * fps               # fractional frames are fine
        p = 'REVEAL_CTRL:GetValue("NumberIn1", time - %.4f)' % off
        o = 'REVEAL_CTRL:GetValue("NumberIn2", time - %.4f)' % off
        inp(xf, "Center").SetExpression("Point(%.5f, %.5f - %.5f*(1 - %s))" % (x, y, rise, p))
        inp(xf, "Size").SetExpression("0.95 + 0.05*%s" % p)
        inp(mrg, "Blend").SetExpression(o)
        xf.SetInput("MotionBlur", 1); xf.SetInput("Quality", 4); xf.SetInput("ShutterAngle", 180)
    return ctrl
```
Verify: for element 0 at 24 fps, `Size` at f3.6 = 0.95, at f12.1 about 0.9895 (half window), at f20.6 = 1.0; `Blend` 0 until f8.6, 1 from f11.6; element i is the same curve shifted by 3.6*i frames.
Status: unverified (not yet rendered); mechanics verified (Custom controller, SetKeyFrames handles, Point/GetValue expressions).

### `.setting` (one element; unverified as typed, syntax corpus-backed)

```lua
{
  Tools = ordered() {
    REVEAL_CTRL = Custom {
      Inputs = {
        NumberIn1 = Input { SourceOp = "REVEAL_P", Source = "Value", },
        NumberIn2 = Input { SourceOp = "REVEAL_O", Source = "Value", },
      },
      ViewInfo = OperatorInfo { Pos = { -300, -300 } },
    },
    REVEAL_P = BezierSpline {
      SplineColor = { Red = 225, Green = 0, Blue = 225 }, NameSet = true,
      KeyFrames = {
        [0]  = { 0, RH = { 3.74, 0 } },          -- 0.22*17
        [17] = { 1, LH = { 4.25, 1 } },          -- 0 + 0.25*17 (absolute)
      },
    },
    REVEAL_O = BezierSpline {
      SplineColor = { Red = 179, Green = 28, Blue = 244 }, NameSet = true,
      KeyFrames = {
        [5] = { 0, RH = { 5.66, 0 } },           -- D = 3
        [8] = { 1, LH = { 5.75, 1 } },
      },
    },
    CARD1_XF = Transform {
      Inputs = {
        Center = Input { Value = { 0.3, 0.6 }, Expression = "Point(0.3, 0.6 - 0.039*(1 - REVEAL_CTRL:GetValue('NumberIn1', time - 3.6)))", },
        Size = Input { Value = 1, Expression = "0.95 + 0.05*REVEAL_CTRL:GetValue('NumberIn1', time - 3.6)", },
        MotionBlur = Input { Value = 1, },
        Quality = Input { Value = 4, },
        Input = Input { SourceOp = "CARD1_SRC", Source = "Output", },
      },
    },
    CARD1_MRG = Merge {
      Inputs = {
        Blend = Input { Value = 1, Expression = "REVEAL_CTRL:GetValue('NumberIn2', time - 3.6)", },
        Background = Input { SourceOp = "BG", Source = "Output", },
        Foreground = Input { SourceOp = "CARD1_XF", Source = "Output", },
      },
    },
  },
}
```
(`CARD1_SRC` and `BG` must exist or be defined in the same paste.)

---

## 17. The 12 principles, Fusion mechanisms

| Principle | Fusion implementation |
|---|---|
| Squash and stretch | `Transform UseSizeAndAspect 0`; key `YSize`; `XSize` expression `1 + (1 - self.YSize)*0.5` (AE formula) or `1/self.YSize` (exact volume). Pivot at the contact point. |
| Anticipation | 2-4 frames of reverse motion or a slight scale-down before the action (R5); Back-in curve for a wind-up dip in one segment. |
| Staging | 3D DOF (Camera3D `PlaneOfFocus` + OpenGL accumulation), Blur/Defocus on BG, vignette, lower `Merge.Blend` on secondary elements, light the subject. |
| Straight ahead / pose to pose | Pose to pose = keys + curves (default). Straight ahead = paint/Trails/particles; Onion skin is not a Fusion feature, scrub instead. |
| Follow-through / overlap | Child reads parent late: `PARENT_XF:GetValue("Size", time - 2)` (numbers verified; Point reads unverified), or a Calculation modifier with `FirstOperandTimeOffset` (sign convention: test). Secondary elements continue 4-8f past the primary stop. |
| Slow in / slow out | Section 3 handles; never linear on heroes. |
| Arc | XY Path with different X/Y eases, or a smooth Polyline Path with Displacement easing; `Heading` for auto-orient. |
| Secondary action | Particles (`pEmitter` -> `pRender`), shadows (`Shadow`, Text+ shading elements), parallax response, audio-driven accents; offset timing, never compete. |
| Timing | Section 1. 24 fps reads cinematic and needs motion blur; 30 smoother; 60 digital-first. |
| Exaggeration | House style: subtle, +2-8% entrance overshoot; big scale moves only for a deliberate hero beat. |
| Solid drawing | Real 3D: `ImagePlane3D`/`Shape3D`/`Text3D`, `Camera3D`, lights, `Renderer3D`; consistent light direction. |
| Appeal | Clear silhouettes, clean paths, defined curve + duration per motion, and a reduced-motion variant (instant state or opacity-only). |

---

## 18. Delivery and reel pacing (tool-agnostic, ported)

- Brand reel 45-90 s: Intro 0-3 s (0-72f @24, logo, establish the motion language), Hero 3-15 s (strongest work first), Montage 15-40 s (specific results, varied timing), CTA 40-45 s (one ask, clear the stage).
- Visuals lead, audio supports: cut muted first. Cut on the beat (Fusion: Keyframes Editor shows the MediaIn waveform and Resolve markers; `KD_NumberBeat` for BPM grids). No dead gaps over 200 ms (5f @24). Hold the intro's motion language for the whole reel.
- Edit-point cookbook: hard cut on beat (montage); smash/scale punch-in (R2/R14); whip/directional wipe on matched vectors (DirectionalBlur + Transform); speed ramp into cut (`TimeStretcher` SourceTime with an ease-in segment); cross-dissolve sparingly (`Dissolve.Mix`).
- Specs must resolve to numbers: duration (ms or frames + fps), a named curve from section 3, optional trigger/stagger, and a reduced-motion alternative.
- Preview at final fps with motion blur on; check title/action safe; judge at 1x.

---

## 19. Don'ts and failure lessons

Craft (from AE, still true):
- Don't key frame 0 and also enter from off-frame: pick one entrance style.
- Don't start Opacity and Position together unoffset: Position 0-10f, Blend 0-5f (@24) so opacity finishes mid-slide.
- Don't use linear easing on hero motion.
- Don't animate Size + Blend + Angle + Center all at once to enter: too busy.
- Don't leave ambient elements static in a "looping" scene; don't end every animation on the same frame; stagger exits too.
- Don't wiggle at violent levels (AE `wiggle(20, 50)`); default subtle and escalate only for glitch/distress.
- Don't add overshoot to text or small chrome; don't exceed 3-10 px / +2-5% scale.

From the local Higgsfield connector (2026-09-26 revision):
- Set an explicit hidden or off-frame state for every delayed reveal: Fusion holds the first
  key's value backward, so key the hidden value at the reveal's start frame and check the frame
  before it.
- No idle wobble, breathing or drift on stationary elements unless the brief or reference asks
  for it; an ambient loop is a request, not a default.
- Gate optional automatic motion (a `Demo` checkbox on `CTRL`, 06) so manual keys stay usable,
  and keep time-driven randomness bounded (sine hash or seeded Perturb with explicit Strength).
- Keep text bounds, `Pivot` and masks stable while wording changes; rigid text motion never
  stretches glyphs unless the reference does.
- Proof frames: start, anticipation, fastest motion, overshoot, settle and last visible frame,
  rendered with delivery motion-blur settings at real timing. A sampled preview proves only the
  sampled intervals.

Fusion-specific:
- **Fusion keys default to linear.** A key without handles is a linear key. Always write handles (or Anim Curves).
- **`AddModifier(inp, "BezierSpline")` seeds a stray key** at the current frame, and one `SetKeyFrames(dict, True)` did not remove it (live): set `comp.CurrentTime` to the first key frame first, or replace twice, then assert `GetKeyFrames()`. Its return value is inconsistent: verify with `GetConnectedOutput()`.
- **Python handles are relative, `.setting` handles are absolute.** Mixing them produces wild curves. Never paste Python dicts into `.setting` or vice versa.
- **`AddTool` auto-connects to the active tool** on the current Fusion-page comp even with autoconnect False: `comp.SetActiveTool(None)` before every AddTool, and check every `ConnectInput` return.
- **`noise()` is not a SimpleExpression function** (input reads None). **Radians** in SimpleExpressions, degrees on Angle inputs and in the Expression modifier.
- **Clearing an expression leaves 0.0**: re-set the value.
- **An expression replaces keys on that input**: keep keys on a controller.
- **Transform has no opacity.** `Transform.Blend` mixes the transformed and untransformed image, it is not layer opacity. Fade with the compositing `Merge.Blend` or Text+ `Opacity1`.
- **Y is up and positive Angle is counterclockwise**: negate AE Y offsets and AE rotations.
- **Orbits and circular wiggles need the W/H aspect factor** on Y (or the Vector modifier's `ImageAspect`).
- **Scale about the right pivot:** center the source and position with `Transform.Center`, or set `Pivot` to the element center.
- **Shake Min/Max are absolute** (0-1 teleports the element); Perturb adds around a Value.
- **Anim Curves `Source` defaults to `Transition`**: set `Custom` (with keyed `Input`) or `Duration` in ordinary comps. Its `Scale` default follows the host (5 on Transform.Size, 360 on Transform.Angle, live): always set Scale and Offset explicitly.
- **Custom tool `NumberIn1..8` clamp to +/-1,000,000** (live: `INPN_MaxAllowed` 1e6; keys, SetInput and expressions all clamp). Drive big counters with a 0-1 progress and multiply inside the text expression.
- **Follower ignores unkeyed changes**; spaces count; set `Order` explicitly (default 7 = Automatic, live: behaves Left to right on Latin text); `DelayType` 0 none, 1 per char, 2 total spread (live-verified). Once attached, **the text lives in the Follower's `Text`**: editing `TextPlus.StyledText` does nothing.
- **Points never take a BezierSpline**: `Center`, `Pivot`, `CharacterOffset`, `Offset1` animate through PolyPath, XYPath, Vector, Shake, PerturbPoint or a Point expression.
- **Paste collisions rename silently** (`_1` suffix): prefix every pasted graph uniquely or your expressions point at the old tools.
- **Text+ Write On:** reveal = key `End` 0 -> 1, write-off = `Start` 0 -> 1 (shipped template), despite the manual's wording.
- **Deleting a host tool does not delete its modifiers**; failed AddModifier can orphan a modifier. Clean with `comp.GetToolList(False)`.
- **Expression modifier could not be attached via AddModifier**: use SimpleExpressions, or paste it in `.setting` when you need `noise()`.
- **Spline loops run to the end of the global range**; Duplicate copies are dead; Python loop flags work (`{"Flags": {"Loop": True}}` per key, live) but `GetKeyFrames()` does not report them. A cycle loop never displays the last key's value (0@0 -> 1@10 cycle reads 0 at f10): make the last key equal the first for a seamless loop.
- **Motion blur belongs on the animated tool**; `pRender` must match `Renderer3D` motion blur exactly; TimeSpeed/TimeStretcher destroy vector channels.
- **Proportional digits jitter in counters**: use `tnum` or `ForceMonospaced`.
- **Scaling a flattened 2D comp softens it**: push upstream or in 3D.
- **Don't trust a render call's return value**: inspect the frames.
- **Don't use `math.random` for anything that must re-render identically**; use the sine hash or seeded modifiers.

---

## 20. IDs and behaviors still unverified

Resolved by the 2026-09-26 live pass (Resolve 21.1.0.14), details inline above: Follower `Order` 0-7 and `DelayType` 0-2 (section 8); Anim Curves `curve*Scale + Offset` and Penner direction (section 3); Python and `.setting` loop flags (section 9); statement-block `:` expressions, `string.format`, `%`, `ceil`, `comp:GetPrefs().Comp.FrameFormat.Rate` in expressions and `comp.GetPrefs("Comp.FrameFormat.Rate")` from Python (all work); Point `SetInput` accepts both `{1: x, 2: y}` and `[x, y]`; Transform `Angle` positive = counterclockwise; PerturbPoint Strength/Speed calibration (R9). Still open:

- Anim Curves `Input` clamping outside 0-1.
- `XYPath` / `PolyPath` attached to a Point input via AddModifier (harvest attached them to a number host); `Path` `Heading` connection from Python.
- `CameraShake` amplitude units (PerturbPoint measured, R9).
- `TextPlus.LayoutWidth` and `FitCharacters` semantics on Circle layout (options live: None, Adjust Spacing to Fit, Adjust Horizontal Size to Fit, Adjust Size to Fit; `LayoutType` Point, Text Box, Circle, Path); `UseLigatures` options live: None, Non-Latin, All Scripts (default 1 = Non-Latin keeps Latin letters separate); `HorizontalLeftCenterRight` sign (-1 = left anchor, live in ui-mastery).
- Option lists read live (live option-string lists 2026-09-26; value order confirmed by render only where noted): `TimeStretcher.InterpolateBetweenFrames` Nearest, Blend, Flow; `DirectionalBlur.Type` Linear, Radial, Centered, Zoom.
- Renderer3D OpenGL accumulation/DOF input IDs (not in the TSV because the default renderer is Software).
- `BitmapMask` input IDs for luma mattes; `Output.DataWindow` index order in expressions.
- `KD_TextWrite`, `KD_NumberBeat`, `KD_SeamlessLoop`, `FairlightAnimator.Analysis` behavior.
- `BlendClone` vs `Blend` on Merge: keying `Blend` assumed canonical.
