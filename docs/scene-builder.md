# Scene builder

Describe a piece at the layer level, in pixels and design terms; get a plain, editable native Fusion graph in one
call. The full reference, with the description grammar and every default, is the `use-fusion` skill (section
"Scene builder").

## Loop

1. Write a description: tokens (`controls`), type styles, eases, then layers listed bottom to top (`text`,
   `rect`, `ellipse`, `path`, `solid`, `image`, `group`, `null`, `camera`, `light`). `scene.schema` returns the
   JSON Schema, defaults and an example.
2. `scene.plan` (offline, instant): validation with paths and spelling suggestions, node counts, cost drivers,
   every efficiency decision, and optionally a wireframe preview sheet and the `.setting` it would paste.
3. `scene.build`: one call pastes the graph (Text+, sShapes, Backgrounds, masks, Merges, Camera3D, ImagePlane3D,
   Renderer3D, splines with your eases), wires MediaOut1 and lays out the graph. It starts in draft (motion blur
   and 3D accumulation off).
4. Look: `fu_render_frame` on key frames, `render.contact_sheet` for the whole motion.
5. Iterate with `scene.update`: edits by layer id, or the whole new description (only what changed is touched).
6. Flip to final quality with one edit, check hero frames and culling edges, Deliver.
7. `scene.export` returns the description (stored on the scene's output tool) and lists hand edits made since.

## What it decides for you

- **Frame-exact in/out, separate culling.** A layer's in/out is cut on its Merge; its enabled region only culls.
  Renderers and generators are never trimmed (a trimmed Renderer3D feeding an active Merge writes black Deliver
  frames); `comp.lint_regions` checks hand-built comps for that trap.
- **Motion blur only where it shows.** Per-layer blur switches on only on frames whose streak is at least 0.75 px.
- **Holds and freezes.** Animated textures under motion blur are held once per frame; static sources feeding
  animation are frozen (-19 % on the heaviest benchmark scene, bit-identical).
- **Textures at their largest sharp on-screen size**, shared when identical (one benchmark scene went from 8.8 to
  2.9 megapixels of 3D textures).
- **Animate the Merge, not the content**: a whole-line rise moves a frozen Text+ raster instead of re-rendering
  Text+ for every blur sample.
- **3D defaults**: explicit film back, Z-buffer transparency (sorted transparency with accumulation dropped cards
  at random), accumulation depth of field (nearly free in Deliver).
- **Text+ sizes from pixel sizes**, measured per font and style (`text.size_for_px`) or estimated from the font file.

## Whole films

Give each scene a `start` frame and build with `film: true`: each scene joins a ladder of Merges trimmed to its
frames, so only the active scene cooks. On the benchmark ad the same ladder built by hand (3,244 tools, one paste)
Delivered in 14.6 min against 21.9 min as eight per-beat clips, with identical frames.

## Limits today

`image` layers, 2.5D mode, the film ladder through `film: true`, light rigs and 3D parent rigs are not yet
verified live. No video media layer yet, one text animator per text layer, and no built-in backdrop blur,
dashed or tapered strokes (build those by hand).
