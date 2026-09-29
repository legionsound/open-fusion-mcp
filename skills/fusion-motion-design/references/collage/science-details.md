# Collage: scientific details and magnification

Only for scientific or explanatory artwork, or when a magnifier is required. Recipes are
**status: unverified (not yet rendered)**.

## Scientific collage details

- Keep the illustration's meaning coherent; label uncertain or decorative content as such. Diagrams
  from editable paths and independent marks; animate phase, write-on (`WriteLength`) or staggered
  emphasis as the reference supports, never random motion that changes the apparent claim.
- A dish of small organisms or particles: independently phased `sEllipse` dots and rounded capsules
  (`sRectangle` with `CornerRadius` 1) inside the dish's interior matte (`EffectMask` or Merge "In").
  At a ~600 px-wide prop, small particles drift ~2 px and larger capsules ~8 px horizontally and ~6 px
  vertically with restrained rotation. In sShape units (width fractions) at W = 3840 that is ~0.0005
  and ~0.002/0.0016. Per element: `Translate.X = x0 + ax*math.sin(2*math.pi*(time/24*f + ph))`, with
  its own `f` and `ph` (generate the elements as `.setting` text so every phase differs; `sDuplicate`
  copies share one phase). Tune count and scale to the shot; no uniform noise fill.
- Everything stays inside the inner boundary and under the rim reflections (rim highlights merge above
  the particle group). Vary phases and directions so the population never pulses together. More
  activity = raise `f` (the time driver), then recheck blur and containment; never raise amplitude until
  things escape. This is illustration, not a validated simulation of biology.
- Annotations sit on clear paper away from captions and optics. Move the whole label-and-arrow group to
  fix a collision; never hide it behind a bigger shadow. Plan the camera to reveal the dish before its
  arrival finishes: a prop that fits the final frame can be cropped all through its entrance.
- A research-paper insert naming a real study uses an authentic, permitted page; keep its hierarchy,
  margins and focal text. Paper stock, page print, shadow, highlight and annotation stay separate; the
  highlighter sits behind the letters (Merge "Multiply" under the text, or text merged over the
  highlight); the title stays readable at the closest camera position. Never swap real body text for
  decorative lines while claiming authenticity.

## Registered magnification

- One controller (`CTRL_Lens`: center, radius, magnification, visibility) drives rim, handle, aperture
  content, highlight and contact shadow. A modest rim keeps the enlarged subject as the focal point.
  Start at 1.3-1.6x and tune on the real artwork.
- Fusion-native registration: the aperture content is the **same** image branch (fan-out, live) passed
  through a Transform with `Pivot` at the lens center and `Size` = magnification, then masked by the
  lens interior (`EllipseMask`, both axes width-relative, realities §2). Scaling about the lens center
  keeps the point under the lens fixed and enlarges its neighborhood, so base and magnified content
  share source time, diagram phase and marks by construction. Keep `Center` at (0.5, 0.5) on that
  Transform and verify one frame. [verified live 2026-09-26] Pivot (0.6, 0.4), Size 1.5: a dot at the
  lens center stayed at (0.6, 0.4) and grew 30 -> 46 px; a dot 0.05 to its right moved to 0.075.
- A lens over a card in 3D: magnify inside the card's own 2D subgraph (before its `ImagePlane3D`),
  with the lens center converted to the card's image coordinates; a plain screen-space offset is wrong
  once the card is tilted or nested under a camera.
- Magnify clean artwork before the final fine grain (grain merges after the lens stage) so the lens
  does not enlarge print texture into coarse fabric; do not double the noise inside the aperture.
- Animate an entrance, a purposeful inspection path (`PolyPath` on `CTRL_Lens` center), a readable
  pause and an exit; restrained lag or settle only where the reference shows it. Review the whole path
  for sampling slips, clipping, diagram discontinuity and caption overlap. Correct math does not by
  itself make the lens convincing: add rim highlight, slight edge darkening and a soft contact shadow.
