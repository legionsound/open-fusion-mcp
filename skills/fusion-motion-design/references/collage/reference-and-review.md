# Collage: reference analysis and review

## Analyze the reference before building

- Watch motion as motion whenever playback is available: the opening, each substantial camera move,
  transitions, readable holds, the ending. Stills measure layout and edges; they never establish smooth
  motion. Record where each piece of evidence came from: playback, selected frames (with indices, 02),
  tutorial captions, source projects, or inferred construction.
- Break the reference into observable events and dependencies: what arrives first, what the camera
  reveals, when text becomes readable, how the palette changes, which small elements keep moving in
  holds. Measure how large action relates to secondary detail instead of leaning on a style label.
- Keep a short list of the details: the outline of each paper piece and its damaged edges, the shape
  of annotations, tape angles, clips, contact shadows, lens highlights, how dense the grain is, small
  specks, which way things enter, how the depth layers separate. Every meaningful detail is built or listed as an intentional omission; random decoration
  is not a substitute.
- With a tutorial link, inspect the relevant material before adopting its technique; extract camera
  hierarchy, layer relations, effect setup and velocity design and adapt them to Fusion and the new
  artwork (AE effects map through 04, depth-space and this pack). Never transplant its coordinates,
  paid plugins or subject. Say when only captions or parts were inspected.

## Verification and review

- Honor the review mode. "Preview on the Fusion page" means viewer playback: no Saver renders, no
  Deliver jobs, no uploads, no MP4 without a new request. Use a proxy/low-res viewer for timing and full
  resolution with HiQ for edges, print and text (09 viewer vs render). Saving the project is separate
  from exporting a movie.
- Play the opening seconds at real speed before saying the opening works. Look at the main entrances,
  camera moves, type-ons, palette shifts, background activity and at least one moment where everything
  holds still. Smooth motion, steady grain and the absence of flicker only show up in playback; if you
  could not watch it play, say so and leave the comp ready for the user to review.
- Inspect adjacent frames around every hard cut and suspicious flash. Backgrounds, camera, finishing and
  textures must cover the whole master range. Compare source length, `GlobalIn`/`GlobalOut` (inclusive)
  and keyed visibility at the real frame rate, including fractional rates: a tiny mismatch can leave a
  blank last frame. Extend the source and its dependents deliberately instead of masking the gap.
- Check expression values (`GetInput` at two frames) and evaluated motion, not just script completion.
  Verify projected text bounds, visible silhouettes, attached groups, matte alignment and backdrop
  coverage at camera extremes and in-betweens (`Locator3D` screen positions or rendered alpha bboxes). A
  populated `DataWindow` does not prove the visible rim or lettering is framed.
- Test the editable surface on a duplicate: a longer prompt sentence, a replacement photo of a different
  size, a material control swept without losing coverage. Restore content afterwards. Local changes
  check their branch; broad construction needs broad review.
- Save the project and read back what was saved (comp export path, project name). Report the target comp
  and every unresolved dependency, missing asset, expression failure, framing defect or unobserved
  playback. A clean script is not the user's approval or reference-perfect motion.

## Handoff and evidence

- Leave the intended comp current on the Fusion page. When packaging is requested: editable project,
  collected authorized media, dependencies, a preserved baseline (15). No credentials; no assumption
  that fonts or third-party footage are redistributable.
- Separate native vector construction from photographic raster assets and disclose generated
  substitutes; never call the result generation-free or all-vector when it is not. No extra aspect
  ratios, public sharing or plugin installs without a current request.
- The numeric starting values in this pack come from native AE 26.3 workflows on macOS, translated to
  Fusion: construction guidance, not guaranteed compatibility or taste. Recheck inputs, media and
  playback when the environment or reference changes. With live access, done means a saved, editable,
  technically checked comp plus an honest account of what was reviewed; without access, done means a
  reviewed builder script and instructions with execution and verification pending.
