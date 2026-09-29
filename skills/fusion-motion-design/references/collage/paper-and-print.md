# Collage: paper, print and typography

AE starting values were measured on ~1440 px-wide artwork; convert with the unit rules in
[fusion-realities](../../../fusion-reference/references/fusion-realities.md) §2 and calibrate by
render. Recipes are **status: unverified (not yet rendered)**.

## Paper, wear and contact

- Stable paper structure, printed image texture, edge wear, contact shadow, ambient shadow and moving
  grain are different materials, each its own tool or pass. Coarse fibers stay attached to the sheet
  (inside the card's group, before its Transform/ImagePlane3D); fine finishing grain changes in time
  (after the final Merge). One heavy noise pass over everything never reads as paper.
- Separate a sheet from its background by luminance, temperature, silhouette and a directional
  shadow; give it a slightly different stock tone rather than washing the frame into one gray or brown.
  Photo, creases and marks stay registered to the sheet in motion.
- Restrained defects: worn corner, shallow crease, broken fibers, slight edge darkening, irregular cut.
  Clip scans and abrasions to the sheet (the sheet alpha as `EffectMask`); wear that belongs to the
  backing sits under the printed image; never let a large unmasked Multiply plate dirty labels or the
  desk.
- Two shadows, one light direction (starting points, then refit to camera scale and resolution):

| Shadow | AE @ 1440 px | Fusion `Shadow` tool |
|---|---|---|
| Contact | 28 % opacity, 2 px distance, 3 px softness | `Alpha` 0.28, `ShadowOffset` = (0.5 + dx/W, 0.5 - dy/H) with dx, dy = 2 px scaled to the sheet's on-screen size, `Softness` ~ softness_px / W |
| Ambient | 12 %, 7 px, 12 px | `Alpha` 0.12, offset from 7 px, `Softness` from 12 px |

  `OutputMode` 1 (Shadow Only) lets both shadows merge under the sheet as separate passes. Doubled
  shadows make a dark outline, not depth. [verified live 2026-09-26] With the AE values scaled by
  3840/1440, the contact and ambient passes offset their alpha bbox centers by +4/+4 px and +13/+13.5 px
  (the intended 3.8 and 13.2 px diagonal components, positive dy = down) and read as a tight contact
  line plus a soft falloff (`t_collage_shadows.png`).
- Silhouette wear (AE Roughen Edges): Fusion has none; use `PerturbPolyLine` on the sheet's polyline
  (`Jaggedness`, `Strength`, `Speed` 0 for static wear, `RandomSeed`; [verified live 2026-09-26]
  `PerturbPolyLine` feeding `PolylineMask.Polyline` from its `Value` output: frames 0 and 10
  bit-identical at `Speed` 0, different at `Speed` 2) or an irregular hand-drawn cut polyline; for fibrous micro-edges, `Displace` (`Type` 1 X Y) of the sheet's alpha only, driven by a
  fine `FastNoise`. Edge irregularity of 1-2 source px; the closest camera crop decides plausibility.

## Continuous grain and material motion

- One finishing strategy, tuned against the reference before adding layers. Animated grain covers the
  whole timeline including holds and transitions; it must not depend on camera movement or on a short
  branch that ends between scenes.
- Moderate monochrome finish (AE Noise 4-8 %, no color noise): `FilmGrain` after the final Merge
  (`Monochrome` 1, `MasterStrength` starting low, `TimeLockSeed` 0 for video) or `Grain`. Judge at
  final viewing size over dark regions and small text.
- A coarse print texture or evolving field only when the reference needs it: start restrained and raise
  until it reads as print, not flicker. `ApplyMode` "Soft Light" keeps midtones, "Multiply" for dark
  flecks, "Screen" for pale abrasion; choose for the texture, never by an unexplained number.
- Stable fibers stay visible under the animated finish. Move a texture by small deterministic offsets
  (1-2 px at working scale), e.g. `Center = Point(0.5 + 1.5/W*math.sin(7.1 + floor(time/2)*2.3),
  0.5 + 1.5/H*math.sin(3.7 + floor(time/2)*1.9))`, and set that Transform's `Edges` 1 (Wrap) so the
  plate's border never shows (Fusion-better than oversizing). [verified live 2026-09-26] At `Edges` 0
  (Canvas) the drifted plate left 12016 transparent border pixels; at `Edges` 1 none. Each texture keeps its own fixed phase
  constants, which do not change when tools are reordered.
- Subtle print or edge boil (AE Turbulent Displace): `FastNoise` (`XScale` = size, `Detail` =
  complexity, `Seethe` driven by a stepped expression for evolution) into `Displace` (`Type` 1 X Y,
  `XRefraction`/`YRefraction` small). [verified live 2026-09-26, corrected] The image goes into
  Displace's **`Input`**, the noise into `Foreground`. Displace also exposes a `Background` input that
  accepts a connection and is ignored: wired there, the render returned True and wrote no file. With
  `Seethe` = `floor(time/2)*0.25` frames 0 and 1 were identical and frame 2 changed; `XRefraction`/
  `YRefraction` 0.004 gave a visible edge wobble at UHD (`t_collage_boil_f0.png`). AE's print pass ran Amount 1.1, Size 58, Complexity 1.2,
  evolution 90 deg/s at the stepped rate; ink boil Size 23, Amount 0.85, Complexity 1.15; broad paper
  Size 112, Amount 1.1. These are source values from one project, not a Fusion preset: map by look and
  reduce for small output or dense text. Evolution changes the field; moving the paper is separate.
  Keep boil off faces, rigid buildings, clean interface elements and anything optical.

## Typography, ink and annotations

- Match lettering by what you can measure (letter proportions, cap height, how strokes behave,
  spacing, where lines break) rather than by guessing the font's name. Enter installed fonts exactly as
  Text+ lists them and check the glyphs that actually render (14 glyph check). Kalam Bold for marker
  notes and Lora Bold for serif display can stand in when they fit; nobody has confirmed them as the
  originals.
- Missing fonts: authorized sources, license checked before redistribution. No silent substitution of a
  variable font or a similarly named family without comparing metrics. A wider marker face may need a
  wider tape label or new placement; never squash text horizontally to keep an old label width.
- Keep words as native Text+ with the full string underneath and type-on separate (Write On). Reset
  inherited case, fill, outline, `CharacterSpacing` and justification deliberately; a same-color
  outline that helped a thin handwritten font muddies a heavier marker face.
- Felt-tip character: uneven ink density, slightly broken edges, natural stroke ends. A restrained
  edge treatment (fine `Displace` on the text alpha, a light `ErodeDilate`) that keeps counters open
  and text legible. Underlines and arrows stay editable paths (`sOutline`/`sPolygon` with round
  `CapStyle` and `JoinStyle`), written on with `WriteLength` when the reference draws them; never a
  mechanically perfect oval by default.
- Measure text bounds with offsets, not only width and height: `DataWindow` gives left, bottom, right,
  top. Evaluate the current type-on state and the final parent scale; a Text+ can have an empty data
  window before its first character appears (guard divisions). Check long words, changing labels,
  camera extremes and overlaps at output size.

## Continuous color changes

- Keep a persistent underlying background and animate a separate oversize color plate, a color input
  (`Background` `TopLeftRed/Green/Blue` keyed with eased handles), or a registered transition matte.
  Never fake a smooth change with a one-frame switch, a tool that starts at the final color, or
  `StepIn` keys on a continuous transition.
- Wipe reveal (AE Linear Wipe completion/angle/feather): a `RectangleMask` (oversize, `Angle`) whose
  `Center` travels across frame, `SoftEdge` for feather (`SoftEdge ~= 1.18*B/W`, realities §2; AE's
  100-200 px feather at HD is `SoftEdge` 0.06-0.12), or a `Dissolve` with a map. A paper tear needs an
  authored torn polyline edge, not a soft wipe.
- Exposure and grain stay constant through the change: never double the finishing stack during a
  crossfade or reveal a differently exposed material halfway. Check start, midpoint and end on adjacent
  frames. A deliberate hard cut in the reference stays a hard cut.
- Color inputs are split float channels (realities §3); Text+ fills are `Red1/Green1/Blue1`; a Tint-like
  black/white mapping is `ColorCorrector`/`BrightnessContrast` or a `Gradient` map, each with its own
  input contract. Read the TSV rather than treating color arguments as interchangeable.
