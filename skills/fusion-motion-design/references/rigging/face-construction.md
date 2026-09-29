# Rigging: face construction

Recipes are **status: unverified (not yet rendered)**.

## Eyes and brows

- Keep the reference's default expression and proportions. Separate owners: eye white (aperture fill),
  whole pupil, eyelid fill, visible lid contour, brow.
- Rounded eyes need smooth curves: `PolylineMask`/`sPolygon` points with Bezier handles (`LX,LY,RX,RY`),
  or `EllipseMask`. A sparse linear polygon renders a diamond even though the geometry is valid. Under a
  pose blend or projection, move both handles with their points (pose banks sampled by `TimeStretcher`
  interpolate handles for you, volume-and-instances).
- Gaze is bounded and the entire pupil is clipped by the **current** aperture. Fusion-native: the lid
  aperture is one mask tool whose output feeds the white's fill, the pupil's `EffectMask` and the visible
  opening, so all three share exactly one boundary through gaze, independent lids and blink.
  [verified live 2026-09-26] One `EllipseMask` fanned out to the white's `EffectMask` and the pupil
  Merge's `EffectMask`: the moving pupil was clipped exactly at the aperture edge (`t_rig_eye.png`). Never hide
  an escaping pupil under a skin-colored cover.
- A fully closed eye is a single lid line with no white showing, never an upper and a lower outline
  lying on top of each other. Half-closed eyes can narrow naturally, but the fully open eye must not pick
  up new corners. A blink squeezes each eye toward its own center (08).
- Compare the upper lid's volume and its crease with the brow in both a neutral and an expressive pose,
  and derive the spacing from this drawing, not from pixel values taken off another character.
- Where a forward nose hides an eye or crease, give the nose an opaque skin volume under its shading and
  contour. Shorten occluded crease strokes with rounded ends (`CapStyle` round, `WriteLength` < 1) before
  the holdout, so clipping leaves no pointed fragment.

## Mouth and jaw

- Remove the original mouth from the head base. One current aperture and one lip contour, driven by
  opening, expression and mouth poses: interpolate compatible geometry (shape keys with equal point
  counts, or a pose bank) or switch complete poses cleanly (`StepIn` or a `Switch` tool); never crossfade
  two visible mouths. Closing restores one line with no leftover lip shape.
- Internal anatomy on request: throat cavity, palate, uvula, tongue, optional teeth, all clipped by the
  same live mouth mask (one mask tool fanned out). Palate above, tongue below, uvula attached to the
  palate; details move within that structure, never floating across the lips. Jaw extension and mouth
  placement are derived together (both from `CTRL_Face.Open`), so big openings stay under the nose and
  inside the moving face. Inspect small openings as well as wide ones.

## Local evaluation and expression

- Face controls are local to the rig instance: published inputs on the character group, read by the
  inner tools (06). The visible lip and the clipping aperture must agree in the final render of the
  instance, not only inside the source group. Because both come from one mask output in Fusion, this
  holds by construction; if they are separate shapes, compute both from the same local controls.
- Line boil on request: restrained, adjustable contour variation (`PerturbPolyLine` with low
  `Strength`, stepped `Speed`/phase) applied coherently to the fill and the matte boundaries of a part
  (perturb the one polyline both use). Do geometric QA with boil and motion blur off, then inspect the
  final effect. Keep motion, hair response and acting intentional; perpetual random movement adds no
  volume.
