# Matching an After Effects render in Fusion

Only for the rare case of rebuilding or scoring an EXISTING After Effects comp in Fusion; the default
workflow is original design-first work from a brief (the fusion-motion-design router, then
[design-first](design-first.md)).

This file holds the AE-specific mapping: AE coordinates, rotation order and signs, the AE camera to
Camera3D and DOF mapping, AE looks that Fusion does differently, AE text-animator semantics, and how
to read `render.compare` numbers. The general Fusion rules behind them live in their home modules
(linked per row). Distilled from a 25 s AE ad rebuilt from its spec with no AE assets (8 scenes,
1920x1080 @30, 750 frames): of 21 scored frames 8 matched and 13 were close (one first called
different, revised at full size); whole-film contact sheet MAE median 2.45 / 255. Every rule is
[from rebuild log] with its friction id unless tagged live.

## 1. Space and time

| AE | Fusion rule | Home module |
|---|---|---|
| px coordinates, y down, z away from the camera | `(x - W/2)/U, (H/2 - y)/U, -z/U` with U = 1080 (1 unit = comp height; y inverted, z negated so the camera looks down -Z). A layer of source width w px at Scale s % = ImagePlane3D `Transform3DOp.Scale.X` w x s/100/U (planes are 1 unit wide); a layer without an anchor point uses its source comp centre [from rebuild log, W4] | [depth-space](depth-space.md) section 2 |
| X/Y/Z Rotation | X kept, Y and Z negated, **and** `Transform3DOp.Rotate.RotOrder` "ZYX" on every card; the default "XYZ" gave a visibly different window pose, "ZYX" matched at f120 and f138 [from rebuild log, K7] | depth-space section 3 "Aimed camera and compound rotations" |
| global frame of a scene | one culled comp for the film (comp frame = global frame; each scene through a trimmed Merge) [live, efficiency lab], or one comp per scene item (comp frame = global frame - scene start); never a TimeSpeed shift of a 3D render [from rebuild log, K12] | [build-orchestration](build-orchestration.md) Module 5 |
| comp format | timeline created at the AE size and fps (`timeline.create {width, height, fps}`) [from rebuild log, F2] | fusion-realities §16 |

## 2. Camera, depth of field, motion blur

| AE | Fusion rule | Home module |
|---|---|---|
| two-node camera (Position + Point of Interest, no roll) | `Camera3D` `Transform3DOp.UseTarget` 1, Translate and Target keyed per axis with each segment's cubic-bezier; `PlaneOfFocus` = AE focus distance along the view axis / 1080. First scene matched at 9 frames, MAE 1.4-2.4 [from rebuild log, W4] | depth-space section 3 |
| zoom 2666.7 px (50 mm on a 36 mm back, HFOV 39.6°) | `FLength` 29.337 **with `ApertureW` 0.8315 and `ApertureH` 0.4677 written** (a pasted `FilmGate` alone left the TV apertures, cards 0.79x size). Read `AoV` back: 22.89 vertical [from rebuild log, K2] | depth-space section 2; fusion-realities §11 item 17 |
| camera Aperture px, Blur Level % | OpenGL accumulation DOF with `RendererOpenGL.DoFBlur` = AE Aperture px / 2 / 1080 x BlurLevel/100 (DoFBlur is the aperture radius in scene units). Assumes U = 1080 and a Camera3D whose AoV equals the AE zoom (row above). Written as a controller expression, e.g. `20.25/2/1080*CTRL.FocusBlur/100` (FocusBlur = AE Blur Level %) [from rebuild log, K3] | depth-space R8 "DoFBlur unit" |
| DOF on a layer scaled down in 3D | AE applies camera blur in each 3D layer's own pixel space, so a layer authored large and scaled down (an app window at 33 %) blurs about 3x less on screen than physical DOF predicts, and Fusion's physical DOF looks too soft. Multiply DoFBlur by a per-scene factor chosen by the dominant scaled layer (used: S3 0.5 and S5 0.45 where the scaled window dominated, S4 and S6 0.8, end card 0.9) and judge by render [from rebuild log, K8] | depth-space R8 |
| shutter 180°, phase -90 | Renderer3D `MotionBlur` 1, `ShutterAngle` 180, `CenterBias` 0; samples = `AccumQuality` when accumulation is on (12 for fast passes; `Quality` adds nothing at or below it [live, efficiency lab, T02]); without accumulation `Quality` 16 for fast passes, 32 for a fast wipe [from rebuild log, COMPARE polish pass]; AE never blurs a still layer: switch `MotionBlur` off per frame where nothing moves | depth-space section 8 |
| 2D precomp content on a 3D layer | hold each card texture per frame (`TimeStretcher` `SourceTime` `floor(time + 0.5)`, Nearest), or every blur/DOF sample re-renders it: 32 -> 1.6 s/frame [from rebuild log, K13] | depth-space section 8 |

## 3. Opacity

- **AE never motion-blurs opacity; a motion-blurred Renderer3D does.** A 0 -> 1 ramp starting at f600
  was ~8 % visible at f600.25 (a ghost of the next word). Key 3D opacity as a per-frame staircase
  (value(n) on [n - 0.5, n + 0.5)) and start in-point ramps on the key, not half a frame early:
  f600 MAE 4.08 -> 1.86 [from rebuild log, K15]. Recipe: depth-space section 8.

## 4. Type

| AE | Fusion rule | Home module |
|---|---|---|
| font size px | `Size = K x px / W`, K per font and weight: Open Sans Bold 1.70 [live]; Helvetica Neue Bold 1.478 measured by `text.size_for_px` [live, gapfix pass, K1] (the rebuild's calibration against the AE render gave 1.49); Helvetica Neue Light 0.989 x Bold [from rebuild log, K20] | [03-typography](03-typography.md) "Size and metrics" |
| glyph fallback | none except emoji: symbols (✦ ✓) draw as boxes; split them into a Text+ in a font that has them (Menlo) [from rebuild log, K6] | 03 "Glyphs, line blocks, typewriters and eased cascades" |
| multi-line text (the spec flattened lines as "a / b") | one Text+ per line [from rebuild log, K9] | same |
| Opacity-0 typewriter (range selector Start 0 -> 100 % linear) | AE fades each character over its slot, so a partly covered character is partly visible: per-line Follower opacity ramp of one slot, `Delay` one slot, not Text+ `End`. AE does not count the line break (counting it was wrong). f484 and a data block at f222 then matched to the glyph [from rebuild log, K21] | same |
| range selector, Shape Ramp Up, `Offset` -100 -> 100 with an ease | the selection is linear in Offset, not in time, so a constant Follower delay landed letters 3-4 f late (f204 MAE 6.9). Warped clock (03 recipe) with AE's timing: evaluated at character centres (the f204 fit supports it), each letter ramps over S/2, `Delay` = S/(2n), first ramp at f0 + Delay/2 (11 letters over 24 f: `Delay` 1.0909, ramp 12 f, first key f0 + 0.545), warp ease = the Offset key's ease. f204 MAE 3.16 after [from rebuild log, K16] | same |

## 5. Shapes and effects

| AE | Fusion rule | Home module |
|---|---|---|
| stroke taper + trim | computed outline polygon (sPolygon fill) revealed by a wide stroke with animated `WriteLength` through a `BitmapMask` [from rebuild log, K10] | [04-gradients-effects](04-gradients-effects.md) "Native animation mechanisms" |
| dashes, radial repeaters | `sDuplicate` of a short `sRectangle`, **`AxisMode` "Absolute"** ("Progressive" stacks copies about their own centres) [from rebuild log, K10, K14] | same |
| shape layer Position and Anchor Point | AE draws shape content relative to the layer's anchor: bake Position - Anchor into the sShape coordinates and pivot there; content outside the sRender canvas is clipped (a Position [955, 602], anchor [0, 0] tittle became a sliver) [from rebuild log, K18] | 04 "Shape canvases, glow cores and grain" |
| Glow (threshold 40 %, radius 40, intensity 1.6) | a Fusion `Glow` sized from the AE radius smeared the core and halo into a blob. Sample halo and core colours from the AE render (#B7843A, #FFFFF4) and give each part a tight glow; a designed approximation, not an AE glow model [from rebuild log, K19] | same |
| Noise/grain | AE's grain measured about 1.2 high-pass std on every field; `FilmGrain` defaults (`LogProcessing` 1) ran 2-3x stronger on bright fields. `LogProcessing` 0, `Monochrome` 1, `MasterStrength` 0.0115 [from rebuild log, K17] | same |

## 6. Scoring with `render.compare` (optional)

`render.compare` is for this rare case (and version-to-version regression). It never replaces
looking at rendered frames.

- **Method:** in each scene comp, `render.compare` at comp frame = global frame - scene start against
  the extracted AE frame. The strip is [AE | Fusion | difference x4] with MAE (0-255), PSNR and
  grayscale SSIM (7x7). Batch frames in `batch.run` (9 frames in 193 s) and issue it only after the
  navigation call has returned; check the comp identity the result echoes (a failed navigation once
  scored the wrong scene at MAE 115) [from rebuild log, W7, F15].
- **Sample:** every beat hero plus in-betweens of every camera move (all sampled moves landed on the
  same framing at the same frame), and a whole-film contact sheet (every 12th frame of both MP4s).
- **Verdicts:** matches = same frame to the eye, diff is grain and sub-pixel edges; close = same
  design and timing with a named small difference; different = wrong or missing content.
- **Reading the numbers:** grain is random in both films, so grain alone costs about 1.5-4 MAE and
  pulls SSIM down most on bright flat fields; there SSIM 0.66-0.76 understated real matches. Judge by
  the diff panel, not the score. Measure grain separately (high-pass std on a flat field) and fix it
  first, or it hides everything else: the grain fix alone took f615 from MAE 3.88 / SSIM 0.72 to
  1.82 / 0.95 and f168 from 3.13 to 2.39 [from rebuild log, K17, COMPARE].
- **Look at full size before calling a miss:** a card pass read "nearly invisible" on a 640 px strip
  and was there at full size (verdict revised from different to close) [from rebuild log, COMPARE f536].
- Typical landed numbers at 1080p with grain: matches scored MAE 1.4-3.9 before the grain fix (the
  high end is grain on bright fields); after it most frames sat at MAE 1.8-2.8, SSIM 0.91-0.96.
  Residual 1-2 px text-edge lines in the diff are anti-aliasing or sub-pixel placement.
