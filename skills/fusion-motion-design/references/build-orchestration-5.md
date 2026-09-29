<!-- build-orchestration.md part 5 of 6; index: build-orchestration.md -->
# Module 4: Scene Director

Owns the creative DIRECTION of a whole comp. fusion-realities owns IDs and mechanics; the UI Rebuilder and design modules own layout construction.

## Routing

- **Use** when the brief describes a scene aesthetically (mood, vibe), implies camera + light + motion together, or names an aesthetic ("keynote", "cyberpunk", "Swiss", "Y2K", "brutalist").
- **Don't use** for a single low-level operation ("add a wiggle to Card01", "Blend to 0.8"); do it directly.
- **Layout** for a mockable frame (title card, lower third, dashboard, stat card, hero frame) comes from the UI Rebuilder / design modules first; layer this module's direction on top.
- **Multi-plane depth** (parallax ladders, atmosphere, push-in math) -> the depth module.
- When the brief nearly matches a recipe below, name it and swap parameters; don't re-derive structure.

## Chapterization gate (before directing)

- **Split into chapters** when the brief carries more than one idea (long text, feature list, several stats, timeline, before/after, problem/solution, walkthrough). One readable idea per chapter, each with ONE job (hook / setup / claim / proof / contrast / payoff / CTA) and a readable hold before its seam. In Fusion each chapter is a `SC<nn>_` group; chapters longer than one shot belong on the Edit timeline as separate Fusion items or clips, not one giant comp (Module 5: time-gated switching inside one comp still renders every scene [from rebuild log, B1]).
- **Keep ONE beat** for a single logo lockup, one CTA, one stat card, one micro-interaction, or a calm hero whose settle IS the payoff.
- Two structure modes: **repeated armature** (same layout + motion, content swaps; build one macro with published text/colour and reuse it) vs **evolving layout** (units carry into new positions; keep the same unit names across chapters so the audience tracks them).
- Never place a paragraph at once: rewrite long text into short authored beats.

## The 7-step process

Walk in order; each step constrains the next. On a simple scene the steps collapse into one pass, but every decision (intent, hierarchy, camera, light, easing, loop) is MADE, never defaulted.

### 1. Treatment (before any tool call)

```
SCENE:     one sentence: what the viewer sees
MOOD:      3 adjectives
PALETTE:   2-4 hex -> 0-1 triplets anchored to the mood
DURATION:  seconds + frames at the comp fps (default 5 s = 120 f @24; reels 10 s; brand 15 s)
LOOP:      yes/no (default yes for ambient scenes)
CAMERA:    one mode (step 3) and rig (2D Transform or Camera3D)
```

Default: dark background, cool palette, single hard key light. No warm tones unless the brief says warm.

### 2. Node-graph groups (4-7, never one flat chain)

Groups are Underlays (visual boxes, zero wiring risk, the default) or GroupOperators (collapsible; use for reusable units and anything that becomes a macro; verify group output wiring on first use). Each group ends in one named output node.

| Group | Purpose | Typical nodes |
|---|---|---|
| **GRP_BG** | atmosphere base | comp-sized `Background` (solid/gradient), `FastNoise`, vignette |
| **GRP_ENV** | environmental detail | `KD_Lines` grid, scanlines, dust `pEmitter`, gradient sweep |
| **GRP_CT_<Unit>** | hero content | Text+, masks/sShapes, media; unit `_Mrg` + `_Xf` |
| **GRP_FX** | secondary motion | falling characters, glitch streaks, `Trails`, particles |
| **GRP_LT** | bloom, glow, flares | `SoftGlow`/`Glow` on the merged stream, `Fuse.OCLRays`, `HotSpot`, sweep |
| **GRP_CAM** | depth + move | `CAM_Rig` Transform (2D) OR `Camera3D` + `Merge3D` + `Renderer3D` (3D) |
| **GRP_GR** | final look | `ColorCorrector`, `ColorGain`, `FilmGrain`, vignette -> `MediaOut1` |

BG, CONTENT, LIGHT, GRADE are always required.

### 3. ONE dominant camera mode (never mix vocabularies)

First choose the rig, then the motion vocabulary.

| Rig | Use when | Mechanics |
|---|---|---|
| **2D Transform rig** (default for graphics, UI, type) | pushes, drifts, handheld breath, 2-4 plane parallax faked by fractions | `CAM_Rig` Transform on the merged content stream before LIGHT/GRADE (`Center`, `Size`, `Angle`, `Pivot`); background planes follow by expression, e.g. `BG_Xf.Size = 1 + 0.3*(CAM_Rig.Size - 1)`. Transforms concatenate: cheap and sharp |
| **Camera3D** (Fusion does this natively, AE MCP could not) | true parallax over many planes, orbit/dolly, rack focus, fog depth cue, lit bevels, Text3D/Extrude3D | planes as `ImagePlane3D` at Z depths (`Transform3DOp.Translate.Z`) -> `Merge3D` (+ lights) -> `Renderer3D`; `Camera3D` `FLength` 35 default, `Transform3DOp.Translate.Z`, `Transform3DOp.Rotate.Y`, `Transform3DOp.UseTarget` + `Target.*` for orbit; `PlaneOfFocus` for focus pulls; OpenGL renderer for accumulation DOF, Software for soft shadows |

Never animate both a `CAM_Rig` and a `Camera3D` in one scene. A low-amplitude `CameraShake` after the 3D render counts as part of the camera and must use the same mode's vocabulary.

| Mode | For | Easing (2-key move, flat values; D = span in frames) |
|---|---|---|
| Slow elegant cinematic | keynote, product reveal, premium tech | long soft landing: RH 0.30D, LH -0.70D = `cubic-bezier(0.30,0,0.30,1)` (AE "ease-out ~70") |
| Hyperkinetic | brand chaos, gaming, sports | snap start, hard settle: RH 0.10D, LH -0.90D = `(0.10,0,0.10,1)`; add an overshoot key or Anim Curves `EaseOut` "Back" (AE in 30 / out 90) |
| Motion-control roboarm | dystopian, AI product, surveillance | near-linear: RH 0.15D, LH -0.15D = `(0.15,0,0.85,1)` (AE low influence) |
| Static + element motion | terminals, dashboards, UI demos | no camera move at all |

Terminal -> static. Logo reveal -> slow elegant. Brand reel -> slow elegant unless briefed otherwise.

### 4. Beat sheet

5 s = 4-5 beats, 10 s = 6, 15 s = 9. Every key anchors to a beat; no floating animation.

| Beat | Seconds | 24 fps | 25 fps | 30 fps |
|---|---|---|---|---|
| HOOK: first element appears (cold open) | 0.0-0.5 | 0-12 | 0-12 | 0-15 |
| BUILD: units stack in, camera starts | 0.5-2.0 | 12-48 | 12-50 | 15-60 |
| HERO: key moment, full composition | 2.0-3.5 | 48-84 | 50-88 | 60-105 |
| HOLD: settle, ambient motion only | 3.5-4.5 | 84-108 | 88-112 | 105-135 |
| TAIL: silent hold for loop blend/transition | 4.5-5.0 | 108-120 | 112-125 | 135-150 |

### 5. Expressions and modifiers over keyframes

If a value is always moving subtly, it is an expression or modifier, not keys. Fusion expressions work on ANY input (effect parameters included), which removes AE MCP's transform-only limit.

| Need | Fusion (SimpleExpression or modifier) |
|---|---|
| Ambient drift (AE `wiggle(0.5, 8)`: 0.5 Hz, 8 px) | exact-unit sum of sines on `Center`: `Point(0.5 + 8/W*(0.6*sin(time/24*2*pi*0.5) + 0.4*sin(time/24*2*pi*0.83+1.7)), 0.5 + 8/H*(0.6*sin(time/24*2*pi*0.47+0.9) + 0.4*sin(time/24*2*pi*0.79)))` (replace W, H, 24 with numbers); organic alternative `PerturbPoint` (`Strength`, `Speed`, `Wobble`; calibrate) |
| Camera breath (`wiggle(0.2, 3)`) | same form at 0.2 Hz, 3 px on `CAM_Rig.Center` |
| BG parallax | fraction of the camera: `BG_Xf.Center = Point(0.5 + 0.3*(CAM_Rig.Center.X - 0.5), 0.5 + 0.3*(CAM_Rig.Center.Y - 0.5))` (`.X`/`.Y` member access unverified; fall back to a Custom controller's NumberIn values) |
| Spinning seal / ring (8-15 deg/s, never reveal-and-stop) | `Angle` = `time/24*12` (deg; Transform Angle is degrees) |
| Loop anything keyed | spline loop (`Flags = { Loop = true }` on the bounding keys in `.setting`; Inspector Set Loop), or `time % N` in the expression |
| Pulse a glow | `SoftGlow.Gain` = `1.2 + 0.3*sin(time/24*2*pi*0.5)`: legal in Fusion (AE MCP needed keys) |
| Typewriter / falling chars / counters | Text+ `End` keys, Follower, `KD_TextWrite`, `TextScramble`, counter `Text(...)` expression on `StyledText` |
| Audio-reactive (21.x) | `FairlightAnimator` modifier; beat pulses `KD_NumberBeat` |

Wiggle units in Fusion terms: position 2-10 px -> amplitude px/W and px/H; rotation 0.5-3 deg -> `Angle` +/-0.5-3; scale 1-3 % -> `Size` +/-0.01-0.03.

### 6. Easing: never accept linear

AE influence -> Fusion handle: an influence of x % becomes a handle of length x % of the segment with zero value change. The AE text gives entrance "influenceOut 80 / influenceIn 10"; its stated intent (house settle: quick departure, long soft arrival) puts the long handle on the ARRIVING key, so:

| Move | Fusion handles | cubic-bezier | Signature 25/50/75 % |
|---|---|---|---|
| Entrance | RH 0.10D, LH -0.80D | (0.10, 0, 0.20, 1) | 0.522 / 0.828 / 0.963 |
| House settle (default entrance) | RH 0.22D, LH -0.75D | (0.22, 0, 0.25, 1) | 0.394 / 0.789 / 0.957 |
| Exit (AE in 75 / out 10: slow departure, clean exit) | RH 0.75D, LH -0.10D | (0.75, 0, 0.90, 1) | 0.041 / 0.190 / 0.511 |
| Continuous move (AE ~30) | RH 0.30D, LH -0.30D | (0.30, 0, 0.70, 1) | 0.167 / 0.500 / 0.833 |
| Settle / overshoot | Anim Curves (`LUTLookup`) `Curve` "Easing", `EaseOut` "Back" (or "Elastic"/"Bounce"), `Source` "Duration" for clip-length-relative timing; or an explicit overshoot key (1.04 then 1.0 over 4-6 f) | | |

Fusion does springs natively through Anim Curves easing presets; AE had none.

### 7. Glow + grade are mandatory

**LIGHT group** (on the merged CONTENT stream): `SoftGlow` `XGlowSize` 30 x W/1920, `Threshold` 0.7, `Gain` 1.2; one subtle diagonal sweep per loop (atlas B).

**GRADE group** (last before MediaOut): `ColorCorrector` crush blacks / lift mids (`MasterRGBLow`, `MasterRGBGamma`, `MasterRGBOutputLow`), duotone tint mapping black to deep blue #0a1428 = (0.039, 0.078, 0.157) or neutral #0a0a0a = (0.039, 0.039, 0.039) via `MasterRedOutputLow/GreenOutputLow/BlueOutputLow`, then `FilmGrain` `MasterStrength` 0.02-0.03 `Monochrome` 1 (AE noise 2-3 %).

Values that bite: Fusion thresholds are 0-1 (AE Glow Threshold 0-100); colours are 0-1 per split input; `ColorCurves` points are `.setting`-only; grade with `ColorCorrector`/`ColorGain` from Python.

## Recipe library (match the brief, swap parameters)

All: status unverified (not yet rendered). Colours converted from the AE source.

**Futuristic terminal** (AE: 1920x1080, 30 fps, 5 s; use the timeline res), BG #000000.
BG `Background` black + `FilmGrain` 0.03 + vignette `BrightnessContrast` `Gain` 0.4 through an inverted soft `EllipseMask` (AE CC Vignette -60) · ENV digit grid = one multi-line mono Text+ at `Blend` 0.08 with scrolling `Center` `Point(0.5, 0.5 + ((time/30*0.02) % 0.1))`; scanlines `KD_Lines` (replaces AE's CC Light Burst scanline hack) · CONTENT mono title, typewriter via Text+ `End`, colour #5fb3d4 = (0.373, 0.702, 0.831); secondary log lines at `Blend` 0.6 · EFFECTS 8-12 Text+ of random ASCII (`TextScramble`), `Center` Y = `1.1 - ((time/30*speed - delay) % 1.2)`, flicker via `PerturbNumber` on `Blend` · LIGHT `SoftGlow` `XGlowSize` 25 x W/1920, `Threshold` 0.6, tint `RedScale` 0.45 `GreenScale` 0.84 `BlueScale` 1.0 · CAMERA locked · GRADE `MasterRGBLow` 0.051 (AE Input Black ~13), duotone black -> #0a1428, white -> #5fb3d4 (`MasterRed/Green/BlueOutputHigh` 0.373/0.702/0.831), `FilmGrain` 0.02 · LOOP via `time`-modulo expressions.

**Logo reveal (premium keynote)** (5 s, LOOP no, hold last frame), BG #000000.
BG `Background` `Type` "Gradient", `GradientType` "Radial" to #0a0e14 = (0.039, 0.055, 0.078) · LOGO clean authentic file via `Loader` (`GA_Logo`), unit `_Xf.Size` 0 -> 1 settling at 1.2 s (29 f @24) with overshoot (Anim Curves `EaseOut` "Back", or keys 0 -> 1.04 at f24 -> 1.0 at f29), slight upward float `Center.Y` +0.005 over the shot · EFFECTS diagonal sweep at 1.5 s (f36 @24); particle burst = `pEmitter` `Number` keyed 300 for one frame then 0, blob style, `Velocity` outward, -> `pRender` "TwoD" (Fusion has real particles; AE substitutes are unnecessary); or `Fuse.OCLRays` streaks from the logo · LIGHT `SoftGlow` `XGlowSize` 40 x W/1920, `Threshold` 0.6, `Gain` keyed 0 -> max at the hero beat · GRADE lift/crush, no tint, `FilmGrain` 0.01.

**Kinetic typography** (1080x1920, 3 s per phrase), BG #f5edf5 = (0.961, 0.929, 0.961) or #000000.
TEXT one phrase, large bold sans, per-character entrance via `StyledTextFollower`: `Delay` 1.2 f @24 (0.05 s), keyed `Opacity1` 0 -> 1, character size 0 -> 1, `Offset1` Y 0.026 -> 0 (50 px at 1920 tall), entrance handles RH 0.10D / LH -0.85D (AE influenceOut ~85 intent) · HIGHLIGHT `RectangleMask` behind one keyword, `Width` 0 -> full at the hero beat, `Center.X` = left + Width/2 · LIGHT `SoftGlow` on the keyword only (separate Text+ for the keyword, or a Glow with `EffectMask` = the highlight mask) · GRADE slight tint, `FilmGrain` 0.01 · LOOP cycles a word stack (Switch or time-gated `Blend`).

**Neural / network map** (8 s loop = 192 f @24 / 240 @30), BG #000000.
NODES ~20 points: `sEllipse` -> `sDuplicate` + `sJitter` (random offsets) -> `sRender`, or `pEmitter` burst with `Velocity` 0; drift `PerturbPoint` 0.3 Hz / 5 px on the node layer `_Xf.Center` · EDGES thin `PolylineMask` lines (`Solid` 0) between node positions, `Blend` pulsing `0.5 + 0.5*sin(2*time/24)` (AE `sin(time*2)`, seconds -> frames) · DATA small Text+ labels, staggered fade 3 f · LIGHT `SoftGlow` with `Threshold` expression-animated · CAMERA 2D rig: `CAM_Rig.Angle` = `time/192*360` (exact loop: value at f192 equals f0 mod 360), breath 0.2 Hz / 2 px on `CAM_Rig.Center` · GRADE duotone white -> #5fb3d4, heavy crush `MasterRGBLow` 0.1, `FilmGrain` 0.03.

**HUD dashboard** (10 s loop), BG #000814 = (0, 0.031, 0.078), primary #00d4ff = (0, 0.831, 1), alert #ff4d4d = (1, 0.302, 0.302), panels #1a2332 = (0.102, 0.137, 0.196).
PANELS `Background` panel colour + `RectangleMask` `CornerRadius` (measured), real stroke = second mask `Solid` 0 with `BorderWidth` in primary at `Blend` 0.4 (Fusion has native strokes) · GRID `KD_Lines` two sets · BARS mask `Height` = `h0*(0.5 + 0.5*sin(time/24*2*pi*f + phase))` with the base-anchored Center expression · RADAR sweep `Angle` = `time/24*60` (60 deg/s) on a wedge (`sEllipse` `WriteLength` 0.1) · COUNTERS Text+ `StyledText` expression (never keyed strings) · LIGHT `SoftGlow` `XGlowSize` 20 x W/1920 · GRADE crush, cyan duotone, `FilmGrain` 0.02.

## Data-visualization motion

Governing rule: every motion must ENCODE or CLARIFY the data; if it does not make a value, trend or comparison easier to read, cut it. A bar is a mask whose `Height` (or `Width`) encodes value; a dot is a positioned mask or sShape. Compute every value -> fraction mapping before building (value/max x plot_px x S / H).

| Pattern | Encodes | Mechanics | Easing |
|---|---|---|---|
| Tweening (morph) | same data, new view | re-key the SAME units between layouts (bar -> line -> pie); identity 1:1 | RH 0.30D / LH -0.70D on position + size |
| Animated sorting (bar race) | rank change | fixed bar COUNT; animate row `Center.Y` and value `Width` with OVERLAPPING windows so bars pass each other | near-linear, 0.25D handles both sides; never snap |
| Spatial motion | geography | marker `Center` along a `PolyPath` route on a static map, `Size` pulse on arrival | RH 0.30D |
| Uncertainty | forecast confidence | `PerturbPoint` on band-edge `Center`, amplitude proportional to band width, 2-6 px (reads "unsure", not "broken") | modifier-driven; the oscillation is the encoding |
| Temporal scatter | trend over time | each dot keyed from its t0 to t1 position; reveal in time order by staggered `Blend` | RH 0.60D / LH -0.15D intent: AE out 60 / in 15 |

- Anchor horizontal bars at their LEFT edge: `Center.X = left + self.Width/2` so `Width` grows rightward; vertical bars at the base: `Center.Y = base + self.Height/2`.
- House stagger 0.05-0.08 s (1-2 f @24), entrance 0.3-0.4 s (7-10 f @24), house settle ease.
- Stagger by DATA order, not layout order; the reveal sequence carries meaning.
- Keep the same unit names across morphs and sorts so the audience tracks each datum.
- Labels ride with their bar by expression on `Center` (the Fusion parent link), e.g. `Point(Bar03_Mask.Center.X, Bar03_Mask.Center.Y + Bar03_Mask.Height/2 + 0.01)` (member access unverified; controller fallback).

## Generated assets (only if the Higgsfield connector is reachable)

Gated on the connection. Not reachable -> build from Backgrounds, masks, sShapes, Text+, particles and procedural nodes, or ask for assets; never block. When reachable: the user's defaults (Seedance 2.5 1080p footage, Nano Banana Pro 2K stills), generate -> Loader/MediaIn -> continue with ENV/FX/LIGHT/GRADE on top.

## Never

- One flat Merge chain with no groups (minimum 4 groups).
- Linear easing on spatial motion without a reference that demands it.
- Floating animation not tied to a beat.
- Default colours: everything flows from the step-1 palette.
- Skipping GRADE.
- Continuing after a failed call or a contradictory readback.
- Mixing camera rigs or vocabularies.
- Music inside the comp: score belongs on the Edit/Fairlight timeline (audio-driven animation may READ it via `FairlightAnimator`).

## Response shape before building

```
**Scene Treatment**      description, mood, palette (hex + 0-1), camera rig + mode, duration (s + frames), loop
**Composition Blueprint** groups and their units
**Beat Sheet**           beats in frames at the comp fps
```

Then execute the Phase B call sequence. Report failures and ask before improvising.

---

# Module 5: Multi-scene films (one culled comp per film) [from rebuild log; live, efficiency lab]

The architecture for any piece with more than one scene, more than one camera setup or more than a
few hundred tools, designed from a brief or otherwise. Proven on a 25 s, 8-scene, 1920x1080 @30 piece
(about 3,250 tools, 750 frames). Mechanics, numbers and memory rules: fusion-realities §16-§17.

## Default: one comp per film, scenes culled by trimmed Merges [live, efficiency lab, one-comp]
The same eight scenes Delivered in **14.6 min as one comp on one timeline item** and 21.9 min as eight
items with a comp each (quiet machine, restart before each; same peak memory ~24 GB; frames
bit-identical; the eight-item version also rendered the first frames after each item boundary further
from the reference). One comp is one paste, one comp to make current, one controller for the film, and
expressions can reach across scenes.
1. **Timeline at the target format** with one Fusion item as long as the film: `timeline.create {name,
   width, height, fps, fusionFrames}` [from rebuild log, F2, F3].
2. **Each scene is a self-contained subgraph** ending in its own output tool (grain included), named
   with a scene prefix so scenes never collide (a per-scene prefix on paste does it).
3. **The film ladder:** `BG -> FILM_1 -> ... -> FILM_n -> MediaOut1`, where `FILM_k` is a Merge whose
   Foreground is scene k's output and whose **enabled region is scene k's frames**. Outside its region a
   Merge passes its Background and does not request its Foreground, so only the active scene cooks
   (realities §17 item 7). Set the region with `SetAttrs({"TOOLNT_EnabledRegion_Start": {1: a},
   "TOOLNT_EnabledRegion_End": {1: b}})` (the Keyframes-editor trim; saved with the comp).
   `scene.build {film: true}` emits this ladder.
4. **Author in film frames** (comp frame = timeline frame). When importing scenes authored in local
   frames, shift every spline key time and handle by the scene start, `GlobalIn/GlobalOut` values, and
   `(time + start)` conversions in expressions; also shift the VALUES of splines that hold times
   (a TimeStretcher `SourceTime` warp): missing that re-timed a title cascade by the scene start
   [live, efficiency lab, one-comp]. Never shift with TimeSpeed [from rebuild log, K12].
5. **Cull inside scenes too:** a layer that is invisible for a run of frames enters through a Merge
   trimmed to its visible frames +-1 (shutter margin). Never trim the renderer or generator that feeds
   an active Merge's Foreground: Deliver then writes black frames without an error (realities §17 item 7).
6. **One controller for the film** (a single `CTRL` all scenes' expressions read), or per-scene
   controllers when scenes must stay independently re-pastable.
7. **3D per scene:** one Camera3D per scene (apertures written, depth-space section 2); OpenGL renderer
   with `TransparencySorting` 0 (Z buffer); every animated card texture held per frame, static textures
   and static sub-branches frozen with a constant-time TimeStretcher; `MotionBlur` switched off on frames
   where nothing moves (depth-space section 8; realities §17).
8. **Inspect with draft renders** while building (`HiQ False, MotionBlur False`: 3-7x faster, layout
   exact), final quality on hero frames, the fastest in-between and every culled layer's first and last
   frame; scan the whole Deliver before calling it done (realities §17 item 13).
9. **Deliver the whole timeline once**, after `system.memory` and, following heavy work, a Resolve
   restart (with the user's approval, after `project.save`); watch with `deliver.status`; `deliver.stop`
   waits for the in-flight frame [from rebuild log, B3, F13].

## Alternative: one Fusion item + comp per beat [from rebuild log]
Use it when scenes must be edited, re-timed or replaced independently on the Edit page, or handed to
different people. Per beat `timeline.add_fusion_clip {timeline, track: 2, recordFrame: start, frames:
end - start + 1, compName}` [from rebuild log, F3, F10], `comp.set_current` to open each (confirm by a
known tool name: every item comp is "Composition1") [from rebuild log, F11], comp frame 0 = item start
[from rebuild log, K12], an identical `CTRL` per comp kept in step with `controller.sync` [from rebuild
log, F14, T1], `comp.clear {keep}` + re-paste to fix one beat [from rebuild log, W5, F5, F6, F12].
Expect ~50 % more Deliver time than one culled comp and different first frames after each item boundary.

## What not to do
- **Time-gated scene switching with Dissolves or Blend-0 Merges** [from rebuild log, B1, B2]. A Dissolve
  at `Mix` 0/1 and a Merge at Blend 0 still cook every input: one frame of one beat took 363 s. The
  2,081-tool all-in-one comp built that way pinned Resolve at 28 GB. Switch scenes with trimmed Merges
  (the ladder above), never with blend values.
- **Trimming the renderer instead of the consuming Merge** [live, efficiency lab, T04]: black frames.
- **Sorted transparency with accumulation** [live, efficiency lab, B5]: cards drop out of passes (flicker,
  dim cards, job-to-job differences).
- **TimeSpeed to retime a 3D beat** [from rebuild log, K12]: 189 s frames and "failed to get scene".
- **Parallel navigation and render calls** [from rebuild log, F15]: a render then inspected the wrong
  comp.
- **Starting Deliver without job IDs** [live, efficiency lab]: every queued job in the project renders,
  stale ones included (one overwrote a delivered file).
- **Unbudgeted re-pastes and stacked full-film renders in one session**: 8 re-pastes and ~60 renders
  took Resolve to 26 GB and stalled a Deliver [from rebuild log, B3]; one full-film Deliver alone grows
  Resolve by ~17 GB [live, efficiency lab]. Restart between heavy phases.

---

