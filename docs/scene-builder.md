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

## Tool names

Layer ids become tool names (`<scene>_<id>`, plus suffixes such as `_Fill`), and Fusion tool names are
case-insensitive: a paste treats `S1_tl_mt` and `S1_tl_Mt` as one name and renames one of them with a `_1`
suffix. The builder therefore rejects a description whose tool names collide when case is ignored, and names
both tools, so `scene.plan` catches the problem offline. Two cases to know:

- ids that differ only by case, such as `tl_mt` and `tl_Mt`;
- the ids `bg`, `ctrl`, `out` and `r3d`, which collide with the builder's own `<scene>_BG`, `<scene>_CTRL`,
  `<scene>_Out` and `<scene>_R3D` tools.

The ids `BG`, `Out`, `CTRL` and `Camera`, and ids that start with `R3D` or `A_`, are reserved outright.

## Frame size

A comp on a carrier clip (the kind `timeline.add_fusion_clip` makes) keeps the carrier's frame size, and
changing the timeline's format (`timeline.set_format`) does not resize Fusion clips already on the timeline.
After a timeline was switched from 1920x1080 to 1080x1920, its existing comp stayed 1920x1080 and the film
ladder cropped the vertical scene. `scene.build` warns when the comp's size differs from the scene's: make a new
clip with `timeline.add_fusion_clip` on a timeline of the scene's size (its carrier is made at the timeline's
size) and build there.

## Limits today

`image` layers, 2.5D mode, light rigs and 3D parent rigs are not yet verified live, and image layers can come in
empty or at the wrong size until each Loader is re-read and its Merge rescaled
([#10](https://github.com/legionsound/open-fusion-mcp/issues/10)). The film ladder (`film: true`) is verified
live. No video media layer yet, and one text animator per text layer. Backdrop blur (`glass`), dashed and
tapered strokes (`stroke.dash`, `stroke.taper`) and size-animation motion blur are built in.
