# Rigging: artwork preparation

For a new flattened illustration, changed topology or repaired overlaps. Recipes are
**status: unverified (not yet rendered)**.

## Registration and one coordinate space

- Fusion coordinates are normalized **per image**: a `Pivot` of (0.5, 0.5) on a 1200x1600 part is that
  part's center, not the comp's. Mixing part-space and comp-space numbers is the Fusion version of AE's
  display-size-vs-source-pixel error.
- Establish one conversion: register every part on a transparent canvas of the master artwork's size
  (the same W x H for all parts; `Background` with alpha 0 and explicit `Width`/`Height`, part merged at
  its source offset), so every part, pivot and landmark shares one space. DoD keeps the empty pixels
  cheap. Then fit the whole character into the comp once with a single `CHAR_Fit` Transform.
- Keep alignment, bounds and overscan through import and grouping; read real image dimensions from the
  file (`ffprobe` or the MediaIn/Loader), never from a display size.

## Separation

- Split by independent movement and occlusion. A portrait usually needs body/clothing, neck, head
  base, rear hair, front hair and moving locks, plus independent facial assemblies (eyes, brows, mouth).
  A costume character may need sockets and shell layers instead of a neck. Separate background and
  decoration before deforming the character. Each part: complete alpha, useful pivot, clear owner.
- Distinctive texture and linework: reference-preserving raster cut-outs (each part its own PNG with
  alpha, or a `PolylineMask`/`BSplineMask` cut from the master inside Fusion). Simple shapes: native
  sShape reconstruction when it keeps silhouette, palette and expression; compare the rebuilt neutral
  pose against the source before accepting. Never silently redraw a detailed illustration in a new style.

## Hidden surfaces

- Remove the old pixels of every extracted moving feature from the surface beneath it. An intact
  original under moving hair, eyes or mouth leaves a stationary duplicate that only shows when the part
  moves. Keep an untouched reference outside the rendered character (a disabled branch or a QA merge
  deleted before delivery).
- Reconstruct skin under hair, neck under the jaw and collar, clothing under limbs, complete roots under
  overlaps. Carry color, texture and light on through the hidden area so no ink line crosses a joint
  that is normally covered. Make the overlap as large as this character's planned motion needs, not a
  pixel margin borrowed from a different character.
- Fusion tools for the patch: `Paint` clone strokes on the part (static patch, then keep the Paint
  output as the part's plate), a `PolylineMask`-shaped fill with sampled color plus `FastNoise` texture
  match, or an image-editing provider (Higgsfield/Nano Banana edit, Affinity) given the source, the edit
  region and preservation instructions. Respect the user's chosen provider and its real capability;
  register the result back to the source and inspect it. A newly generated full portrait is not a patch
  unless a redesign was asked for.

## Preparation gate

Render the neutral assembly and compare proportions, silhouette, facial placement, edges and color with
the reference (side-by-side or `QA_Ref` overlay at `Blend` 0.5). Temporarily push adjacent parts to
their intended extremes before building deformers; inspect newly revealed pixels, roots and canvas
bounds for holes, doubled features, visible patch edges or clipped tips. An exploded-parts sheet proves
separation, not hidden coverage. Repair, restore neutral and export a checkpoint comp.
