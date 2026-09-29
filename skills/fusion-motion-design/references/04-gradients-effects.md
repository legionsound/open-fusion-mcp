# 04 Gradients, materials and native effects

Use this module for backgrounds, fields of color, light that travels, iridescent type, glows, ribbons and swooshes of light, bands that bend, warped surfaces, and for the case where an effect looks right on its own but wrong once it is inside the comp. Timing at 24 fps.

## Backgrounds, gradients and travelling light

Atmosphere and moving color get the same care as the objects in front of them: they are designed, not decoration. Look at several moments in time and note the palette, where each field sits, its scale and falloff, the empty or dark areas, and the route and speed of every highlight. First decide the cause of change: camera motion, moving light, changing color, or deformation (02 cause table).

Build a few semantic fields, not many color fragments:

| Layer | Fusion build |
|---|---|
| Base palette | `Background` `Type`="Gradient", `GradientType` "Linear"/"Radial", `Start`/`End` points, `Gradient` stops |
| Low-frequency depth | Large `Background` radial gradient, or solid `Background` through an `EllipseMask` with high `SoftEdge` (0.1-0.2), merged `ApplyMode` "Multiply" or "Screen" |
| Diffuse illumination | Second soft radial field, `Merge` `ApplyMode` "Screen" or "Soft Light", `BlendClone` 0.3-0.6 |
| Narrow specular | Thin `sRectangle`/`sEllipse` -> `sRender` -> `Blur` -> `Merge` "Screen", or `Glow` on that pass only |
| Texture/noise | `FastNoise` only if the grain or evolution is visible in the reference (`Seethe` keyed or `SeetheRate` self-animating) |

Use `GradientInterpolationMethod` "LAB" (or "HLS") when RGB midpoints go muddy between saturated stops; `SubPixel` "3x3" or higher for animated or repeating gradients. Scroll a gradient with `Offset` (0..1) and `Repeat` "Once"/"Repeat"/"Ping-Pong". Avoid visible ellipse edges (raise SoftEdge or use a radial gradient instead of a masked solid), banding (float is native; check the delivery bit depth), muddy overlaps, and a generic background that only shares the reference hue.

`.setting` gradient syntax (corpus): `Gradient = Input { Value = Gradient { Colors = { [0] = { r, g, b, a }, [0.37] = { r, g, b, a }, [1] = { r, g, b, a } } } }`; stop position is the table key.

## Iridescent type and moving color over a surface

Match both spatial color variation and temporal phase. A uniform fill changing hue, or a tiny point shift inside a nearly uniform gradient, does not reproduce a travelling highlight. Two Fusion routes:

1. Text+ shading: element 1 `Type1` set to gradient (index 2: the live option list reads Solid, Image, Gradient, 2026-09-26; not render-checked), `ShadingGradient1` stops, `ShadingMappingLevel1` (Full Image vs Text vs Character: one gradient across the frame, the block, or each glyph), animate `ShadingMappingAngle1`/`ShadingMappingSize1` or the stops.
2. Explicit color field matted by the text (clearer coordinates, preferred when the field must move independently of the surface): `FIELD Background (gradient, Offset keyed) -> Merge.Foreground`, `TITLE -> Merge.Background`, Merge `Operator` "In" (FIELD kept only where TITLE has alpha). Alternatives: `MatteControl` with TITLE on a matte input, or `ChannelBoolean` alpha copy. The field's `Start`/`End` or `Offset` animates relative to the surface; transforming the surface with a fixed gradient does not recreate independent color phase.

Verify start, passage and settled palette in rendered pixels. Keep glow subordinate to the legible core and check clipping margins. If Glow washes a colored fill to white, split the crisp colored core from a bloom pass under it: `Glow` `ApplyMode` 1 ("Merge Under", glow beneath the image by alpha) does this in one node; or `TITLE -> Glow (Glow 0.4, BlendClone 1) -> Merge.Background`, `TITLE -> Merge.Foreground`. Tint bloom with `RedScale`/`GreenScale`/`BlueScale`. `SoftGlow` has `Threshold` and `Gain` for highlight-only bloom. The `GlowMask` input restricts the source but lets the glow spread past the mask; an EffectMask clips the result.

## When an effect is right alone but wrong in the comp

Validate the effect on an isolated render, then in the final parent at several timestamps. Read rendered colors and alpha (Saver PNG then sample pixels, or a `Probe` modifier), not parameter values. Locate the first failing parent by viewing each Merge upstream. Common Fusion causes:

| Symptom | Cause | Fix |
|---|---|---|
| Glow/blur cut off at frame edge | `ClippingMode` "Frame" (default on Blur/Glow/SoftGlow) | "Domain" or "None" when content lives off frame |
| Element cropped or rescaled after merge | Merge `Background` sets resolution/bit depth | Full-frame plate on Background |
| Bright fringe / dark halo | straight vs double-premultiplied foreground | fix alpha at source; `SubtractiveAdditive` only for Normal mode |
| Soft/resampled edges after several moves | transforms concatenated then resampled; or `FlattenTransform` forcing early resample | one Transform chain, flatten only deliberately |
| Wrong position after grouping | expression references a renamed tool; Point inputs expect 0-1 | read back names; rebind |
| Different result in a timeline instance | template/instance holds its own values (06) | compare instance values |

Test a fresh copy of the subgraph with explicitly restored transforms before changing the design or flattening. Re-verify after saving and on a completed short-range render. A successful script or isolated test does not prove the composed shot renders correctly; a stale viewer frame is not a render.

## Native animation mechanisms

Choose the mechanism that matches observed behavior before drawing geometry.

| Reference behavior | Fusion mechanism |
|---|---|
| Light ribbon/swoosh travelling along a trajectory | `sPolygon` (Solid 0, `BorderWidth`, `CapStyle` round) with `WritePosition` (start) and `WriteLength` (visible length) keyed; reveal and trailing disappearance keyed separately. Equivalent on `PolylineMask`/`sOutline`/`sEllipse`. `KD_ShapeWriteOn` (`RangeStart`, `RangeEnd`, `Shift`, `ShiftWrap`) for wrap-around offset |
| Stroke taper with draw-on | **[from rebuild log, K10]** sShapes have no variable-width stroke (this row used to offer unverified crossfade/soft-edge alternatives; the route below is the one that rendered). Compute the tapered outline from the path in code (offset each sample by ± half the local width) and fill it: `sPolygon` `Solid` 1 -> `sRender`. Reveal it with the centre path as a wide stroke: `sPolygon` `Solid` 0, `BorderWidth` wider than the ribbon, `WriteLength` 0 -> 1 keyed -> `sRender` -> `BitmapMask` (`Channel` "Alpha") on the fill Merge's `EffectMask`. The ribbon then read with a smooth convex taper; do not fake with a rotating filled ribbon |
| Dashed stroke / dashed circle | **[from rebuild log, K10, K14]** no dash option in sShapes. Dashed ring: one short `sRectangle` dash at radius r (`Translate.X` = r) -> `sDuplicate` with `ZRotation` = 360/N, `XPivot`/`YPivot` 0 and **`AxisMode` "Absolute"**, `Copies` keyed 0 -> N-1 for a trim-like draw-on -> `sRender` |
| Radial copies (spokes, ticks, petals) | **[from rebuild log, K14]** `sDuplicate` `AxisMode` "Absolute" rotates each copy about the shape-space origin. "Progressive" accumulates the transform about each copy's own centre: 84 rotated dashes stacked into one 14 px star at 9 o'clock and the ring never drew. Progressive is for cumulative offset/scale chains. Default is "OriginRelative"; options Absolute, OriginRelative, OriginAbsolute, Progressive. Centre the ring on the shape origin (the rebuild's sat at the comp centre) |
| Ribbon wraps around an object | two passes of one path (Paste Instance, deinstance `WritePosition`/masks): back pass under the object, front pass over it, separated by simple masks with shared timing |
| Typography on a bending band, glyphs deform | Text+ and one rectangle in a group, then `GridWarp` (Dst grid points, `DstSubdivisionLevel` 3) or 3D: group -> `ImagePlane3D` (raise `SurfacePlaneInputs.SubdivisionWidth`) -> `Bender3D` (`Bender` "Bend", `Amount`, `Axis`, `Angle`, `RangeMin/Max`) -> Renderer3D |
| Glyphs stay rigid on a curve | `TextPlus` `LayoutType` Path + `PositionOnPath`, band warped separately |
| Heat/glass refraction | `Displace` (`Type`, `XRefraction`/`YRefraction`, `RefractionStrength`) fed by a soft map |

Calibrate interior text deformation in a Fusion render: an external fit can match the band's boundary while stretching letters inside it wrongly. Infer the surface from its full construction and unoccluded edges; a triangular overlap fragment is not the whole card. Where the reference keeps glyphs rigid, keep their measured position, size and orientation inside the same rig instead of forcing a warp.

Glow and motion blur only where the reference shows them. Motion blur lives in each tool's common Settings inputs (`MotionBlur`, `Quality`, `ShutterAngle`, `CenterBias`, `SampleSpread`) on Transform, Text+, sRender and Renderer3D; use `VectorMotionBlur` only with vectors. Preview Quality 4-8, raise for final.

Restore reference-supported secondary motion (button hover/bounce, arrow nudge, shadows, entrances, particle births/deaths, tails) after confirming it exists. Measure phase and amplitude of repeated motion, key one cycle on a controller spline, loop it (`.setting` key `Flags = { Loop = true }`), and give each element a phase offset by reading it at shifted time: `CTRL:GetValue("Cycle", time + 6)`. An active button bouncing is no evidence that the inactive ones move too. And a tidy still icon has not rebuilt a control that animates.

## Shape canvases, glow cores and grain [from rebuild log]

- **Shape content clips to its `sRender` canvas [from rebuild log, K18].** A dot drawn at the shape origin into a comp-size sRender and then moved into place by a Transform lost three quarters of its area (it became a tilted sliver); corner brackets clipped the same way. Put the shape's final position into the shape coordinates (sShape `Translate.X`/`Translate.Y`, width units) and pivot any downstream Transform at that point. Never draw outside the canvas and translate afterwards; size the canvas to hold the shape at every animated pose.
- **A small bright core with a halo needs split, tight glows [from rebuild log, K19].** One large `Glow` over a 22 px core and a 70x46 px halo smeared both into a soft blob. Build halo and core as their own shapes in their own colours (a warm #B7843A halo, a near-white #FFFFF4 core) and give each a tight Glow (halo `XGlowSize` 10, `Glow` 0.45; core `XGlowSize` 3, `Glow` 0.2 on a 1920x1080 comp). (Matching an AE Glow: ae-matching.md.)
- **FilmGrain scales with brightness by default [from rebuild log, K17].** `LogProcessing` 1 (default) grows grain with pixel value: high-pass std 0.6 on a dark field, 3.4 on a bright one. For grain that stays even across dark and bright fields use `LogProcessing` 0 with `Monochrome` 1; strength is then linear: measured std 3.03 (0-255 levels) at `MasterStrength` 0.03, so `MasterStrength` = 0.03 x target_std / 3.03 (**0.0115** for std 1.2). Keep the default when brightness-scaled grain is the look. Judge grain on a flat field (high-pass std) at delivery resolution.

## Recipe E1: travelling highlight across a headline (status: unverified (not yet rendered))

Purpose: a soft white band sweeps left to right across `HEAD` (Text+) once, f24-f60, only inside the letters.

```
HEAD TextPlus (white fill) --------------------------------------> Merge HEAD_MRG.Background
SWEEP Background Type "Gradient", GradientType "Linear", Start {0,0.5} End {1,0.5}
   Gradient stops [0]={1,1,1,0} [0.45]={1,1,1,0} [0.5]={1,1,1,0.9} [0.55]={1,1,1,0} [1]={1,1,1,0}
   Offset keyed f24 -0.55 -> f60 0.55 (ease in-out: RH {12,0}, LH {-12,0})
SWEEP -> SWEEP_IN Merge (Operator "In": FG = SWEEP, BG = HEAD) -> HEAD_MRG.Foreground (ApplyMode "Screen", BlendClone 0.6)
```
Verify: band invisible before f24 and after f60 (Offset beyond range with `Repeat` "Once"); no light outside glyph edges; band speed constant mid-sweep; `Offset` input range allows negative values (slider 0..1, typed values may exceed; read back). If the `In` operator keeps the BG color, swap to `ChannelBoolean` alpha multiply.

## Recipe E2: swoosh draw-on with trailing tail (status: unverified (not yet rendered))

`SWOOSH sPolygon` (open path, `Solid` 0, `BorderWidth` 0.012, `CapStyle` round index per TSV) -> `sRender` -> `SoftGlow` (`Threshold` 0.6, `Gain` 1.5) -> scene Merge. Keys (24 fps): `WriteLength` 0 @f0 -> 0.35 @f8 (ease-out); `WritePosition` 0 @f6 -> 0.65 @f22 (ease in-out); `WriteLength` 0.35 @f18 -> 0 @f26 (tail collapses at the end). Verify the head reaches the path end exactly at f22-26, cap shape at both ends, and no glow clipping (`ClippingMode`).

```python
sw = comp.FindTool('SWOOSH')
def keys(tool, inp, kf):
    tool.AddModifier(inp, 'BezierSpline')
    sp = next(v for v in tool.GetInputList().values()
              if v.GetAttrs()['INPS_ID'] == inp).GetConnectedOutput().GetTool()
    sp.SetKeyFrames(kf, True); return sp
keys(sw, 'WriteLength', {0: {1: 0.0, 'RH': {1: 2.7, 2: 0.3}}, 8: {1: 0.35, 'LH': {1: -2.7, 2: 0.0}, 'RH': {1: 3.3, 2: 0.0}},
                          18: {1: 0.35, 'LH': {1: -3.3, 2: 0.0}, 'RH': {1: 2.7, 2: 0.0}}, 26: {1: 0.0, 'LH': {1: -2.7, 2: 0.2}}})
keys(sw, 'WritePosition', {6: {1: 0.0, 'RH': {1: 5.3, 2: 0.0}}, 22: {1: 0.65, 'LH': {1: -5.3, 2: 0.0}}})
```

## Don'ts and failure lessons

- No noise/evolution unless its texture and motion are visible in the reference.
- No many-small-ellipse color fields; a few soft semantic fields.
- Do not infer render correctness from parameter values or a single isolated node view.
- Do not rotate an already-visible filled ribbon to imitate a stroke travelling along a path.
- Do not let glow wash the core; do not glow the whole comp to add "polish".
- Premultiplication, Merge Background resolution and Clipping Mode explain most "works alone, breaks nested" cases in Fusion; check them before redesigning.
- Do not use `sDuplicate` "Progressive" for radial copies; use "Absolute" [from rebuild log, K14].
- Do not render shape content outside its sRender canvas and move it afterwards [from rebuild log, K18].
- Do not light a small bright core with one large Glow; split core and halo, each with a tight glow [from rebuild log, K19].
- Do not leave FilmGrain on `LogProcessing` 1 when grain must stay even across dark and bright fields [from rebuild log, K17].
