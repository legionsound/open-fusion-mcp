# Characters: artwork and materials

Recipes are **status: unverified (not yet rendered)**.

## Preserve illustrated construction

- Measure the approved silhouette, facial proportions, major contour landmarks, palette, overlap and
  framing before rebuilding (`scripts/measure_ref.py`, pixel color sampling in design-first §2).
  Match them in one native still before extending the rig.
- Bold graphic anatomy (almond eyes, angular nose, expressive mouth, broad hands, flowing hair masses,
  simplified continuous limbs) stays bold; a supplied likeness is held to the same stylization.
- Build visible components as native vectors: `sPolygon` (fill, `BorderWidth` stroke) through
  `sMerge` -> `sRender`, or `PolylineMask` shapes on colored `Background`s. A continuous form gets one
  continuous contour; split a detail only where independent motion or material control needs it. No
  tool-count target.
- Cover internal rig boundaries with coherent geometry and overlap: shoulders, elbows, wrists, hips,
  knees, ankles stay connected (joint caps drawn as overlapping discs under both segments). Keep finger
  count, limb orientation, foreshortening and Merge order through deformation.
- Foreground plants, oversized flowers, companions and background shapes follow the approved
  composition. For a new canvas, reposition or extend the setting; never stretch the anatomy.

## Textured volume

- Match the accepted grain from the artwork or the approved render; keep grain strength, size, color
  response and tonal distribution separate from geometry.
- Volume on hair, skin, clothing, petals, foliage and fur: gradient `Background`s (`Type` "Gradient",
  radial or linear) masked by the part's shape and merged with `ApplyMode` "Multiply"/"Soft Light",
  plus `FastNoise` for mottling where the reference has it. Look up every input in the TSV; check the
  look in the current build.
- Texture and shading merge inside the part's group, before its Transform and after its shape, so they
  follow transforms and deformation (use the part's own alpha as `EffectMask`). Keep material
  continuous across connected parts and the illustrated light direction consistent.
- Separate controls for gradient texture and fine grain when both exist (`CTRL_Mat.GradAmt`,
  `CTRL_Mat.Grain`); values come from the accepted look, not one number for every material.
- Highlights and reflections stay on their surface. A glasses glint is its own gradient streak,
  animated independently, visible only inside the lens (lens shape as `EffectMask`).
- Verify in rendered crops at output scale: shadows and highlights, texture density, silhouette edges,
  material seams, and scale changes during motion. Fix crawling grain (object grain `SeetheRate` 0,
  `FilmGrain` `TimeLockSeed` for stills) or flicker without erasing the accepted texture.
