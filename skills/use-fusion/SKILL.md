---
name: use-fusion
description: Entry point for the Use Fusion MCP connector (use-fusion), the local server that gives an agent native control of DaVinci Resolve Fusion comps (the Fusion mirror of Higgsfield's use-after-effects). Use when a task should build, edit, inspect, animate or render a Fusion comp through fu_* tools, when checking that the connector is connected or installed, or when choosing its policy switches. Hands off to fusion-motion-design for the craft and fusion-reference for API facts.
metadata:
  routing:
    domain: filmmaking-editing
    lane:
    - fusion
    output:
    - timeline
    - file
    tool_routes:
    - resolve
    authority: reference
    status: active
    triggers:
    - use fusion
    - fusion connector
    - fu_do
    - fusion mcp
    notes: Entry for the local use-fusion MCP (<repo>/connector); mirror of Higgsfield use-after-effects.
---

# Use Fusion (connector entry)

The connector is a fast path, not the only path. It sits beside the official DaVinci Resolve MCP
(`run_script` / `run_script_unsafe`: the full Resolve API) and computer use (the node graph,
Inspector, viewer, dialogs): combine all three freely in one task, choosing per step whatever takes
the fewest calls at the least risk. The craft lives in `fusion-motion-design` and the API facts in
`fusion-reference`. Do not duplicate them here.

## 1. Is it connected?

Call `fu_version_info`. Expect `resolve.studio: true` and your skills root. If the tool is missing,
the server is not registered or failed to start (see 3). If it returns `RESOLVE_UNAVAILABLE`, open
DaVinci Resolve Studio and set Preferences > System > General > External scripting using = Local.
`UI_BLOCKED` means a modal dialog in Resolve is up: look at the window, close it, retry.
`RENDERING` means a Deliver render is running: `deliver.status` / `deliver.stop` / `system.memory`
still work, everything else waits. After a Resolve restart Resolve may open "Untitled Project":
`fu_do project.load {name: "Testbed"}` (allowlisted projects only). Every call timing out after a restart:
an orphan may hold scripting port 49152 (`fusion-connector doctor` and the `TIMEOUT` hint name it); ask the
user to quit it and reopen Resolve.

## 2. Working loop

1. `fu_get_skill {name: "fusion-motion-design"}`, then only the modules it names; read
   `fusion-reference` `references/fusion-realities.md` before the first mutation. Long references
   come back in ~34k-char pages (`nextOffset`, heading TOC); `section: "R8"` returns one section,
   `toc: true` lists headings.
2. `fu_context` (project, timeline, page, current comp, rules), `fu_comp_info`, `fu_tool_info`.
3. Look up: `fu_catalog({operation: "tool.add"})` or `({query: "delete tool"})`. Act: `fu_scene_build`,
   `fu_scene_plan`, `fu_batch`, `fu_contact_sheet`, else `fu_do`. Several steps: one `fu_batch` (one call, one
   undo event). Finished steps stay when a later one fails; `atomic: true` undoes all and verifies (comp
   changes only): use it when half a batch is worse than none. `snapshot: "names"` (up to 1,500 tools) lets
   recovery list added tools. Paste-based ops (setting.paste, builder.*, mask.add_polygon, tool.duplicate)
   need the comp showing on the Fusion page: pass `comp: {timeline, item}` or call `comp.set_current`.
4. Verify by looking: `fu_render_frame` returns the preview inline; `fu_contact_sheet` shows a
   whole motion in one grid; `timeline.grab_frame` (not in the build loop: it switches to the Edit page and
   back, ~2 s) only when you need the cut's color-managed timeline output; `render.compare` (optional: a supplied reference, or version-to-version regression) scores a
   frame (MAE, PSNR, SSIM, diff panel); `audit.motion` checks timing, easing and stagger numerically. Fix what you see.
   Renders cannot show node wiring or Inspector state: for those take a computer-use screenshot of
   the Resolve window (Fusion page node editor / Inspector; `viewer.view` puts a tool in the viewer).
5. `TIMEOUT`/`TRANSPORT` = uncertain completion; never blindly retry. Read `details.receipt`, run
   `batch.recover {callId}`, then BEFORE any other change `batch.rollback {callId}` (`keep: true` keeps the
   changes; with no sign of a change it undoes nothing and says why); then re-run from the first unfinished step. `comp.undo` reverts one call. A timed-out render may
   still run and leave its temp Saver: `render.cancel`.

## 2b. Film-scale work (ops added after the benchmark ad rebuild)

| Need | Op |
|---|---|
| Timeline at its own size/rate | `timeline.create {name, width, height, fps, fusionFrames}`, `timeline.set_format` (fps only while empty; existing Fusion clips keep their size) |
| Fusion item of exact length on any track (one item for a whole-film comp, or one per beat on V2) | `timeline.add_fusion_clip {track, recordFrame, frames, compName}` (black carrier + AddFusionComp; returns compRef) |
| Media Pool clip onto a track at a record frame | `timeline.append_clip {clip, sourceIn, frames, track, recordFrame}` |
| Comp on a V2+ item | `comp.create {onItem, track}`; `comp.set_current` goes through the Edit page (settled) to the item's middle frame and names a covering upper-track clip |
| Wipe a comp before re-pasting a scene | `comp.clear {keep}` (default keeps MediaIn/MediaOut; one Lua call) |
| Big paste without a 100k echo | `setting.paste` is quiet above 50 tools; `rewireExternal: true` reconnects SourceOps to tools already in the comp; `connect: [[tool, input, source]]` |
| Many deletes | `tool.delete` takes globs inside lists; 40+ tools go in one Lua call |
| Generated op lists | `batch.run {path: "/abs/ops.json"}`; children's previews come back with the batch |
| One CTRL across per-beat comps | `controller.sync {timeline, tool: "CTRL"}` after editing one copy |
| Memory before big pastes/renders | `system.memory` (also in `fu_context` and render results); `system.purge_cache` frees Fusion's render cache (about 1 GB after 30 heavy frames; most of Resolve's footprint is not that cache); above the warning, save and ask the user before restarting Resolve |
| Deliver progress / stop | `deliver.start` refuses a timeline whose comps measured 60+ s/frame (confirm to override); `deliver.status` works during the render (percent, ETA, approx frame, s/frame, seconds without a frame); `deliver.stop` sends one stop and waits. Never stop a heavy job mid-frame: a stuck CPU-heavy frame kept rendering ~8 min after the stop and Resolve crashed |
| Whole film in one comp (faster than one comp per beat, same pixels) | one item as long as the film; each scene's output enters through a Merge trimmed to its frames (`scene.build {film: true}`, or `SetAttrs({"TOOLNT_EnabledRegion_Start": {1: a}, "TOOLNT_EnabledRegion_End": {1: b}})` via run_script; the connector has no region op yet) [live, efficiency lab] |
| Draft check renders for a hand-built comp | `render.frame` / `render.range` / `render.contact_sheet` / `render.compare` with `quality: "draft"` (HiQ and motion blur off): 3-7x faster, layout exact; `quality: "final"` to judge the look (the scene builder's `CTRL.Draft` covers its own scenes) [live, efficiency lab] |
| Check a culled comp for the black-frame trap | `comp.lint_regions`: flags a trimmed tool feeding a non-mask input that is active outside the trim, and overlapping FILM_ regions, with the fix |
| A heavy branch slowing the check loop while you work below it | `cache.to_disk` (render once, read back through a Loader: -42 % vs live, pixel-identical); `cache.status` / `cache.refresh` / `cache.restore` / `cache.clear`. See "Disk caches for the build loop" below [live] |
| A readable node graph | `comp.layout` (whole comp, `{scene}` or `{tools}`; `dryRun` returns the plan and metrics); `scene.build` / `scene.update` lay out their own graphs. See "Graph layout" below [live] |
| Text+ size for a px font size in any font | `text.size_for_px {font, style, px}` (measured and cached per font/style; `text.set_style sizePx` then uses it) |

Renders point MediaOut1 at the rendered tool for the render and restore it (`isolate: false` to
skip): `comp.Render` in Resolve also renders MediaOut1's chain. Render results name the comp
(`comp.mediaOutSource`) so a wrong-comp render is visible.

## 3. Install / register (once)

- Project: `<repo>/connector` (Python 3.12 venv in `.venv`, `mcp` SDK 1.x).
- `<repo>/connector/bin/fusion-connector doctor` checks Python, SDK, Resolve, Studio, project,
  UI, skills, TSV, manifest, System Events and who holds scripting port 49152.
- `<repo>/connector/bin/fusion-connector config` prints the registration command, e.g.
  `claude mcp add --scope user -e FUSION_MCP_PROJECT_ALLOWLIST=Testbed use-fusion -- <repo>/connector/bin/use-fusion-mcp`.
  Restart the client session after registering.
- After editing any fusion-* skill run `fusion-connector skills-manifest` (served files are hash-checked).

## 4. Policy switches (server env)

| Variable | Effect |
|---|---|
| `FUSION_MCP_READONLY=1` | only read operations; `fu_render_frame` and `fu_contact_sheet` withheld (they add a temporary Saver) |
| `FUSION_MCP_ALLOW_CATEGORIES=comp,tool,...` | category allowlist |
| `FUSION_MCP_PROJECT_ALLOWLIST=Testbed,...` | mutating ops refuse other projects (reads still work) |
| `FUSION_MCP_ENABLE_EVAL=1` | allow `eval.python` / `eval.lua` (off by default) |
| `FUSION_MCP_ALLOW_TEMPLATE_INSTALL=1` | allow `template.install` into Resolve's Templates folders (also needs confirm: true) |
| `FUSION_MCP_AUTO_DISMISS_RENDER_MODAL=0` | stop auto-clicking OK on Resolve's render dialogs (default on) |
| `FUSION_MCP_MAX_RESPONSE_CHARS=40000` | response size budget; larger responses spill to `out/responses/` with a preview |
| `FUSION_MCP_MEMORY_WARN_GB` | Resolve footprint that triggers the restart advice (default 60 % of RAM) |

Every `comp.Render` in Resolve 21.1 raises a modal dialog that blocks scripting: "Render completed!"
on success, "WARNING! Render did not complete!" when the source tool produced nothing. The connector
clicks OK on these two only, through System Events (needs Accessibility permission for the process
that runs the server, the MCP client app). A failed render returns `RENDER_FAILED` with the dialog
text; check the source tool (`fu_tool_info`, `viewer.view`) rather than retrying. With the switch
off, close the dialog yourself after each render.

## Scene builder: one description in, one native graph out

Use it for any new piece built from a brief (title sequences, UI feature cards, lower thirds, kinetic type, 3D
pushes, product cards). You describe the piece at the layer level, in pixels, in design terms (tokens, type styles,
layout, enter/exit moves), and `scene.build` writes a plain, editable native Fusion graph (Text+, sShapes,
Backgrounds, masks, Merges, Camera3D/ImagePlane3D/Renderer3D, splines with your eases) in one quiet paste. Retiming,
restyling and re-laying-out are edits of the same description (`scene.update`), not graph surgery.

### Loop
1. Write the description from the brief (section B has the method; `scene.schema` has the JSON Schema, the
   defaults and a small example). Keep it small: tokens, type styles, then layers.
2. `fu_scene_plan {description}` (offline, instant): validation with paths and spelling suggestions, node count by
   regId, cost drivers (renderers, accumulation passes, motion-blur tools, texture megapixels, holds, freezes,
   culled tools) and every efficiency decision. `outPath` writes the `.setting` it would paste.
   `preview: {frames: [0, 30, 60, 90]}` returns an offline wireframe sheet inline (shapes, real-font text,
   groups, transforms, opacity, trims, 3D cards through the camera; no blur, DOF, glow, masks or mattes): check
   layout, spacing and timing here before touching Resolve.
3. `fu_scene_build {comp: {timeline, item}, description}`: ONE call. Returns layer id -> tools, node counts,
   decisions, warnings, paste time. MediaOut1 is wired to `<scene>_Out`. The scene is built in **draft**
   (`<scene>_CTRL.Draft = 1`: motion blur and 3D accumulation off) for fast iteration renders.
4. Look: `fu_render_frame` on key frames, `fu_contact_sheet` for the whole motion. Draft is for layout,
   timing, text, colour and opacity; not for blur, DOF, glow softness or grain.
5. Iterate: `scene.update {scene, edits: [...]}` (grammar below) or `scene.update {scene, description}` (diff
   mode: the whole new JSON; only what changed is touched). `dryRun: true` shows the ops first. Static values are
   set in place, changed splines are rewritten in place, only structurally changed tools are deleted and
   re-pasted; wires and culling follow. One call = one undo event.
6. Final: `scene.update {scene, edits: [{scene: {quality: "final"}}]}` flips only `CTRL.Draft`. Check the hero
   frames and the fastest in-between at final quality, and every culling edge (first/last frame of a layer).
   Deliver with explicit jobIds.
7. `scene.export {scene}` returns the description (stored on `<scene>_Out` as CustomData, so it travels with the
   tools); `drift: true` lists hand edits made in Fusion since (tool, input, expected, live).

| op | what | Resolve |
|---|---|---|
| `scene.schema` | JSON Schema, defaults, presets, example | offline |
| `scene.plan` | validate + node count + costs + decisions (+ `.setting`, + wireframe `preview`) | offline |
| `scene.diff` | old/new (or old + edits) -> the ops scene.update would run | offline |
| `scene.read` | description(s) from `.setting` text or a file | offline |
| `scene.build` | one call build (paste, culling regions, output wire); `replace: true` rebuilds | live |
| `scene.update` | surgical edits by layer id, or diff mode; `dryRun` | live |
| `scene.export` | description back; `drift: true` | live (read) |

### Edit grammar (`scene.update`)
- `{layer: "title", set: {"text.content": "New", "position": [960, 500], "opacity": 80}}` (dotted paths)
- `{layer: "title", keys: {position: [[0, [960, 600], "out_expo"], [20, [960, 540]]]}}` (`null` removes a track)
- `{layer: "title", in: 10, out: 90}`
- `{add: {...layer...}, after: "bg"}` / `before` / `into: "group"`; `{remove: "cursor"}`
- `{scene: {quality: "final"}}`, `{scene: {"controls.accent": "#00C2A8"}}`, `{scene: {"textStyles.h1.size": 110}}`

Changing a control colour or a type style re-derives everything that references it; changing a layout gap or an
align target moves every affected layer; retiming an enter preset rewrites only those splines.

### Description cheat sheet
- Units: pixels, top-left origin, y down, +z away from the camera. Frames are comp frames. Layers are listed
  **bottom to top**. A key is `[frame, value, ease]`; the ease shapes the segment that LEAVES the key (CSS
  keyframe semantics). Eases: presets by name (`linear`, `hold`, `ease`, `in_out`, `out_expo`, `out_back`,
  `house`, `sine_io`, `cubic_out`, `quart_out`, `expo_io`, `settle` ...), `[x1, y1, x2, y2]`, AE speed/influence
  objects, or your own names in scene `eases`.
- Scene: `scene` (id = tool prefix), `size`, `fps`, `duration`, `start` (comp frame of its frame 0), `background` (colour, `$control` or
  `{gradient}`), `controls` (live tokens: colours and numbers on `<scene>_CTRL`), `textStyles`, `eases`,
  `safeArea` (fraction or px, default 5 %), `motionBlur` (`{shutter, samples}` or false), `quality`
  (`draft`|`final`), `grain`, `assets` (reusable groups), `efficiency`, `render3d`.
- Layer common: `id`, `type` (`text|rect|ellipse|path|solid|image|group|null|camera|light`), `in`/`out` (out
  exclusive), `position`, `anchor`, `scale` (% or [sx, sy]), `rotation` (degrees clockwise), `rotationX/Y`
  (3D), `opacity` (0-100, `$control` or `{expr}`), `threeD`, `parent`, `keys`, `blend`, `motionBlur`,
  `effects` (`blur`, `glow`, `shadow` (CSS-like offset/blur), `tint`, `grain`), `masks` (rect/ellipse/path in
  layer px), `matte` (`{layer, mode: alpha|alphaInverted|luma|lumaInverted}`), `glass` (`{blur, saturation, tint,
  opacity}`: frosted glass; what is below the layer in its container is blurred and merged back inside the layer's shape,
  following its transform, animation, motion blur and opacity; 2D layers, 2.5D cards and cards in a Renderer3D; `blur` px
  like `effects` blur, default 20; `tint` a colour with alpha over the frost; `opacity` the frost strength %).
- Placement (AE conventions): path `points` are offsets from the layer's position (absolute comp coordinates need
  `position: [0, 0]`); `anchor` is the layer point that lands on `position` and the scale/rotation pivot, so setting it
  MOVES the layer. Shapes, solids, images and groups anchor at their centre; text and paths at their origin. `scene.plan`
  warns when a path looks absolute or an anchor pushes a still layer off frame.
- One controller per film: scene `controlsFrom: "<scene id>"` makes this scene's CTRL (Draft and every same-named control)
  follow `<id>_CTRL` by expression. Edit colours, numbers and quality on that scene only; an update to a follower warns.
- Design helpers (resolved at build; the authored JSON is what is stored and exported):
  - `"$name"` in `size`, `radius`, `gap`, `padding`, text `size/tracking/leading`, stroke `width`, `offset`
    reads a number control at build time; in colours and in `opacity`/`rotation` it stays a live expression.
  - `text.textStyle: "h1"` pulls a named style from `textStyles` (explicit fields override).
  - `align`: `"center" | "top" | "bottom-left" ...` (to the safe area) or `{to: "frame|safe|parent|<layer id>",
    x, y, place: inside|above|below|left|right, gap, offset}`. Works across groups (a cursor can target a button
    inside a card). Text alignment sets the text's own justification, so edges are exact.
  - group `layout`: `{type: "stack", direction, gap, align: start|center|end, padding}` or
    `{type: "grid", columns, gap, cell}`; a group without `size` hugs its content (`[600, null]` fixes the width).
  - `enter` / `exit`: a preset name (`fadeIn`, `fadeUp`, `fadeDown`, `slideLeft`, `slideRight`, `pop`, `zoomIn`,
    `fadeOut`, `fadeOutUp`, `fadeOutDown`, `shrink`) or `{preset, at, duration, ease, from|to: {x, y, z, opacity,
    scale, rotation}}`, relative to the laid-out rest state.
  - group `stagger`: `{each: frames, order: forward|reverse|center, enter, exit}` applies to the children.
  - text `animators`: `{type: "cascade", start, stagger, duration, ease, from: {y, x, opacity, scale, rotation}}`
    (per character; `stagger: 0` = the whole line rises inside a mask) or `{type: "typewriter", start, end, mode:
    step|fade}`.
- Types: `text {content, textStyle, font, style|weight, size, tracking (1/1000 em), leading (px), color, align}`;
  `rect|ellipse {size, radius, fill (colour or {gradient}), stroke {color, width, cap, join, opacity, dash: [on, off, ...]
  px, dashOffset, taper: {startLength, endLength, startWidth, endWidth, startEase, endEase} (AE, %)}, repeat {count,
  offset}}` (dashes default to butt caps; a taper makes the stroke a filled polygon; trim works on rect, ellipse and path
  strokes, a trimmed rect/ellipse starting at the top-left corner / 12 o'clock clockwise; `trimStart`/`trimEnd` both key;
  a trim draws strokes only, never a fill); `path {points [[x, y] or {p, in, out}], closed, trim {start, end}}` (keys `trimStart/trimEnd` draw
  it on); `solid {size, color}`; `image {src, size}` [unverified live]; `group {size, layers | use: asset,
  background, radius, layout, stagger}`; `null`; `camera {zoom | lens (mm on 36 mm), poi | null, dof: {focus: px
  or layer id, aperture px}}`; `light {light: ambient|point|directional|spot, color, intensity}` with `lit: true`
  on cards.

### What the builder decides for you (efficiency defaults, tunable under `efficiency` / `render3d`)
- **In/out and culling are separate**: a layer's in/out is cut frame-exact on its Merge Blend, so hard cuts land
  on the right frame; each layer's in/out and fully transparent ranges also become the enabled region of that
  Merge, which only culls (its motion-blur margin can no longer show a layer early). Never trim the renderer or
  generator that feeds it (a trimmed Renderer3D feeding an active Merge writes black Deliver frames); check a comp
  with `comp.lint_regions`. Scenes built before 2026-09-27 15:30 keep region-only gating until rebuilt with
  `replace: true`. Applied after the paste (`TOOLNT_EnabledRegion_*`, table form).
- **Motion blur is the cost**: per-layer Merge motion blur and the Renderer3D motion blur are switched on only on
  frames whose on-screen streak is at least 0.75 px (a per-frame table expression), and always off in draft. 2D tools use
  min(`motionBlur.samples`, 8) samples (`efficiency.mb2dSamples` overrides): bench_s2 Delivered 72 frames in 42.1 s at 8 vs
  49.9 s at 12, pixels within tile 0.5 [live, efficiency lab item 7].
- **Size animation blurs through a scale**: Fusion blurs a tool's own transform, not an upstream shape's Width/Height. A
  rect/ellipse with moving `size` keys is held per frame and scaled by a Transform (`<id>_SizeMB`) whose ratio is exactly 1
  on every whole frame, with its own motion blur: still frames and draft renders are the same pixels (MAE 0.0 live), moving
  frames smear like AE. A stroke width scales with the shutter samples. `efficiency.sizeBlur: false` turns it off [live, sb3].
- **Glass cards in 3D** split the Renderer3D block: cards listed before the glass card render in one pass (the frost comes
  from it), the glass card's silhouette renders alone through the same camera for the mask, and the glass card with the
  cards after it render in a second pass. Keep depth order equal to list order around a glass card; cost: two extra
  renderers (the silhouette pass is culled to the card's frames) [live, sb3].
- **Masks are never frozen**: freezes skip `*Mask` tools and track-matte image chains; every compile checks it [live, sb3].
- **Translucent backgrounds are premultiplied**: a Background tool's colour is read as premultiplied (`#FFFFFF21` used to
  composite as solid white); group backgrounds, solids and plates now premultiply static colours [live, sb3].
- **Merge chains, never MultiMerge**: a MultiMerge re-composites every layer when any layer changes (2x slower on a real
  animated scene, efficiency lab); tidiness comes from the layout's labeled backdrops.
- **Texture holds and freezes**: an animated texture under motion blur is held once per frame (TimeStretcher
  `floor(time + 0.5)`); a static source feeding something animated (a static card texture in 3D, the static
  prefix of a stack) is frozen with a constant-time TimeStretcher (efficiency lab T03: -19 % on S5, bit-identical).
- **Textures at their largest SHARP on-screen size**: 3D textures are rasterized at the largest on-screen scale over
  the visible frames where the card's motion-blur streak is under 12 px (`sharpTexturePx`; a card smeared across a
  whip shows no texture detail), x1.1, capped at 2x, in 1/8 steps; identical visuals share one texture (13 bokeh
  specks, three rows of one filmstrip). On S2 this cut the 3D textures from 8.8 to 2.9 MP (Deliver pixels moved by MAE 0.15 median, 0.43 max). 2D sources rasterize at their largest scale (a static 67 % layer draws at 67 %,
  so the Merge Size is exactly 1).
- **Animate the Merge, not the content**: a whole-line rise (`cascade` with `stagger: 0` that only offsets or fades)
  becomes a Merge move over a frozen Text+ raster, with the layer's masks drawn in container space at the rest pose
  (the AE LineBox reveal), instead of a Follower that re-renders Text+ for every motion-blur sample.
- **Nodes**: one layer = its source + one Merge (Center/Size/Angle/Blend/motion blur on the Merge, no Transform
  node); static shape layers in a row share one sRender; transparent groups get a canvas cropped to their content
  (no oversized pad Merges); asset groups are built once.
- **3D**: explicit ApertureW/H and a FLength from the AE zoom; RotOrder ZYX with the Y/Z sign flip; unlit cards
  via `IsAffectedByLights 0`; opacity held per frame under the renderer; accumulation DOF (nearly free in
  Deliver); **`TransparencySorting` 0 (Z buffer)** by default (Sorted + accumulation dropped cards
  non-deterministically; Z buffer was bit-identical and matched AE). If two semi-transparent cards overlap and
  mis-order, separate them in depth or set `render3d.transparency: "sorted"` for that scene. Flat cards under a
  straight camera (`mode3d: auto`) become 2.5D Merges with per-frame projected Center/Size and a per-card depth
  blur (AE's own DOF method) [unverified live]; parents of 3D layers become Merge3D rigs.
- **Text+ size**: `Size = K * px / W`, K measured (`text.size_for_px`) or estimated from the font file as
  1.243 x (ascent + descent)/em (within 0.6 % of the three measured faces). Text widths for layout come from the
  real font (Fusion's FontManager list live, the installed-font index offline).
- Not decided: comp format (the clip's size wins; the build warns on a mismatch), Deliver settings, the
  grade. Resolve processes Fusion images in 32-bit float whatever `Depth` says (efficiency lab G), so texture SIZE is
  the memory lever and the Depth written on generators documents intent only.

### Measured live (2026-09-27, Testbed, 1920x1080 30p)
| scene | calls to build | tools | build call (paste) | notes |
|---|---|---|---|---|
| showcase (title + 3D card + camera push + cursor) | 1 | 58 | 2.5-5.8 s (0.9-1.0 s) | restyle+retime update 2.5 s; quality flip 52 ms (one set) |
| title sequence / feature card / 3D push | 1 each | 45 / 56 / 54 | 2.0-8.1 s (0.6-1.1 s) | contact sheets match the offline previews |
| Benchmark S2 (from its spec) | 1 | 196 (rebuild 198) | 6-9.5 s (2.3 s; the rebuild comp pasted in 6.8 s) | vs the rebuild's S2 Delivered in the same session: MAE median 1.0, max 1.35 (first build: SSIM min 0.980); vs the v002 MP4 f96/f116: MAE 2.49/1.63 |
- Deliver S2 (72 frames): draft 0.045 s/frame; final 0.67-0.74 s/frame vs the rebuild comp 0.62-0.75 in the same
  session.
- Scene builder pass 3 (28 live checks): paste and in-place updates no longer grow with comp size (50 tools 0.27 / 0.31 /
  0.36 s at 0 / 1,000 / 2,000 tools); size blur rest MAE 0.0; glass frost pixel spread 90 -> 23 (2D), 94 -> 19 (3D split).
- Live fix: multi-line Text+ with `CenterOnBaseOfFirstLine` 1 stacks extra lines UPWARD. The builder writes
  `CenterOnBaseOfFirstLine` 0 + `VerticalTopCenterBottom` 1 with Center on the LAST baseline; line pitch at
  `LineSpacing` 1 = 0.80 x Size x W (measured on Helvetica Neue Bold).

### Limits today
- `image` (still Loader hold; pastes no longer open the file browser), 2.5D, light rigs, 3D parent rigs: **[unverified live]**.
  The film ladder (`film: true`) is live-verified (the one-comp benchmark rebuild, the layout film check, sb3).
- No video `media` layer yet (use `media.add_mediain` beside the scene), no expression-driven layer links beyond
  `{expr}` scalars, one text animator per text layer, non-uniform scale in 3D uses X only. Text layout boxes use
  cap top to baseline (descenders are not part of a stack gap).
- Text masks: `box` is `[x, y, w, h]` with the origin at the first baseline; for AE-style corners use
  `corners: [x0, y0, x1, y1]` (never both). A text mask covering under 90 % of the resting text warns.
- Layer ids are one namespace across the scene and its assets, and tool names ignore case: duplicates,
  case-only differences and the ids `bg`, `ctrl`, `out`, `r3d` fail early. One asset may be used at
  several 2D scales (later rasters get `_v2` names); non-uniform scale keys respect supersampled textures.
- Quiet replies: build (default) and plan (`quiet: true`) return counts, up to 20 warnings and 8 sample decisions;
  the full layer map and decisions go to the `detail` JSON file named in the reply.
- Now built in [live, sb3]: backdrop blur (`glass`), dashed strokes (`stroke.dash`), tapered strokes (`stroke.taper`),
  trim on rect/ellipse, size-animation motion blur, one film controller (`controlsFrom`).
- Dashes cost one shape node per dash (a trimmed 2,048 px circle at [12, 8] = 103 shapes + 103 splines); over 400 dashes is
  refused. A tapered stroke with keyed trim is keyed as a polyline per frame; a later edit of those keys re-pastes the tool.
- A build, or an update that adds or removes tools, still runs the layout pass, which reads the whole comp (0.43 / 0.99 /
  1.8 s at 0 / 1,000 / 2,000 tools); for many builds into a big film comp pass `layout: false` and run `comp.layout` once
  at the end.
- A whole film in one comp: give each scene `start` (the comp frame its frame 0 lands on; keys, `time` expressions
  and culling shift with it) and build with `film: true`: each scene's `<scene>_Out` joins a ladder of Merges
  (`FILM_<scene>`) trimmed to that scene's frames, so only the active scene cooks (efficiency lab F). The same
  ladder built by hand for the whole benchmark ad (3,244 tools, one paste) Delivered in 14.6 min vs 21.9 min as eight
  per-beat items, frames bit-identical [live, efficiency lab]; prefer it unless beats must stay separate Edit-page
  clips.

## Disk caches for the build loop (`cache.*`)

Freeze while you still edit upstream; pre-render to disk once a branch is locked; refresh or restore after any edit above a cache. Measurements, dialog traps and the film workflow: fusion-motion-design `references/build-loop-caching.md`.

Cache a locked branch. Omit `start`/`end` and the range becomes the union of its consumers' enabled regions,
else the comp render range:

```json
{"operation": "cache.to_disk", "args": {"comp": {"timeline": "FILM", "track": 1, "item": 0}, "tool": "S5_Window_Shd", "start": 60, "end": 90}, "timeoutMs": 600000}
```

- **Files:** `FUSION_MCP_CACHE_DIR` (default `~/Movies/FusionCache`) + `<project>/<timeline>/<clip>/<tool>/<tool>_r1_####.png`.
- **Loader:** `<tool>_Cache` reads that sequence at comp frames `start..end`, and every consumer of the tool
  is rewired to it.
- **Live branch:** stays in the comp, intact but unconsumed, so it does not cook.
- **Manifest:** comp CustomData `fc_cache`, holding the range, revision, rewired inputs and the upstream
  fingerprint.
- **Out-of-range warning:** a consumer that can request frames outside the range is named in `warnings`,
  because the Loader has no image there.

Check what is cached and what is stale:

```json
{"operation": "cache.status", "args": {}}
```

- **Reply:** per cache: range, frames on disk, bytes, created or refreshed, `stale`, and `changed` (the
  upstream tools whose settings, keys, expressions or wiring differ). Node moves and other UI state do not
  count.
- **Also warned by:** `render.frame/range/contact_sheet/compare` (under `warnings`) and `deliver.start`, which
  refuses without `confirm: true`.

Re-render stale caches (a new file revision; the old one is deleted), or one cache or all:

```json
{"operation": "cache.refresh", "args": {}}
{"operation": "cache.refresh", "args": {"tool": "S5_Window_Shd"}}
```

Put the live branch back (consumers of the Loader rewired to the tool, Loader deleted), optionally deleting
the files:

```json
{"operation": "cache.restore", "args": {"tool": "S5_Window_Shd", "clear": true}}
```

Delete cache files, only ever inside the cache root. `tool` is a restored cache's folder (`restore: true` for
an active one); `all: true` deletes every unused cache folder of this comp:

```json
{"operation": "cache.clear", "args": {"all": true}}
```

## Graph layout (`comp.layout`)

The house graph style (spine, layer columns, labeled backdrops) is in fusion-motion-design `references/graph-style.md`, with the measured units for placing nodes yourself.

- **`scene.build` / `scene.update` lay the graph out automatically** (`layout`, default true).
  - Whole comp: when the comp holds only scene-builder tools (scenes, the FILM_ ladder, MediaIn/MediaOut, the
    connector's FC_* helpers).
  - This scene only: when the comp also holds a user's hand-made tools. A build goes below them; an update keeps
    `<scene>_Out` where it is. The user's tools never move unasked.
  - An update re-lays out only when tools or wires changed. A value, key or expression edit moves nothing.
  - A layout failure becomes a warning, never a failed build.
- **`comp.layout` tidies ANY comp.**
  - Scope: `{}` (the whole comp), `{scene: "S5"}` (tools named `S5_*`, kept in place), or
    `{tools: ["Title*", ...]}`.
  - `dryRun: true` returns the plan and its metrics (overlaps, crossings, wires over tools, spines straight,
    off-lattice) without touching the comp. `preview: true` draws the planned graph.
  - Underlays: the ones comp.layout made (CustomData `fcLayout`) are refreshed on every run. A user's own
    underlays are left alone and reported. `underlays: false` leaves all underlays untouched.
  - `fit: true` frames the graph with a zoom cap of 0.5; FrameAll alone zooms in to 1.0 on small comps when
    thumbnails are on. It is off by default, so the user's view is not moved.
  - Cost: two Lua chunks whatever the size (one read, one apply); one undo event. Measured live: 97 tools in
    about 0.3 s, 560 tools in 1.27 s.
- **`scene.plan {graph: true}`** draws the graph `scene.build` will paste, offline, with the same metrics. The .setting
  from `scene.plan outPath` carries the positions and underlays, so a manual paste is tidy too.

## 5. Beside the connector

The official DaVinci Resolve MCP covers the whole Resolve API (Edit, Color, Fairlight, Media Pool,
Deliver, anything the catalog lacks) and one `run_script` can beat many `fu_do` calls; computer
use sees and touches what no API reaches. Use them whenever they are the quicker or safer route,
not only when the catalog has no op. A `run_script` pattern that keeps recurring is a candidate
connector op: note it for the connector's next pass. The community server (`davinci-resolve`)
adds guarded Fusion helpers and offline `.comp` authoring.
