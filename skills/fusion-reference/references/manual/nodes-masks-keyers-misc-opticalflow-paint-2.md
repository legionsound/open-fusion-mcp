<!-- nodes-masks-keyers-misc-opticalflow-paint.md part 2 of 3; index: nodes-masks-keyers-misc-opticalflow-paint.md -->
## Miscellaneous Nodes (Ch.52, p.1348-1385)

### Auto Domain [ADoD] (p.1349)
Auto-sets DoD from background Canvas-color bounds (no physical resize). Speeds renders on non-EXR
sources lacking a pre-optimized DoD. Canvas color defaults black (works w/ premultiplied alpha); for
non-alpha flat-matte sources (e.g. a CG specular/shadow pass), precede with **Set Canvas Color**
(solid alpha + matching BG color).
- Inputs: `Input` (orange), `Effect Mask` (blue, limits detection area).
- Controls: **Left/Bottom/Right/Top** sliders (0..1 normalized border; Left/Bottom default 0, Right/Top
  default 1 — raise to exclude more margin from that side).

### Change Depth [CD] (p.1351)
Converts bits/channel (e.g. float->16-bit post-grade to save memory, or up-convert for precision).
- Inputs: `Input` (orange), `Effect Mask` (blue).
- Controls: **Depth** (`Keep` = no change, else 8/16/32-bit or Float). **Dither**: `Error Diffusion` or
  `Additive Noise` (mask banding artifacts when down-converting).

### Custom Tool [CT] (p.1352) — full expression/scripting reference
The most powerful/complex Fusion node: per-pixel expressions across up to 3 image inputs, a matte
input, 8 numeric sliders, 4 XY position controls, 4 LUT splines. **Use for motion-design math no built-in
node covers** (custom rotations, tilings, procedural per-pixel logic).
- Inputs: `Input` orange/green/magenta (image1/2/3, `c1`/`c2`/`c3` in expressions — `c` context-
  resolves so one expression can be pasted across R/G/B fields and auto-pick the right source
  channel), `Matte Input` (white, `m1`), `Effect Mask` (blue).
- **Controls tab**: `Point In 1-4` (X/Y centers, exposed as `p1x,p1y`..`p4x,p4y`; animatable/modifier-
  connectable). `Number In 1-8` (sliders, `n1`..`n8`). `LUT In 1-4` (4 spline LUTs via `getlut#(value)` —
  e.g. R/G/B/A = `getlut1(r1)`,`getlut2(g1)`,`getlut3(b1)`,`getlut4(a1)` mimics Color Curves). Renaming
  Number/Point controls in Config only changes UI labels — expressions still use `n1..n8`/`p1x..p4y`.
- **Setup tab** (`Setup 1-4`): up to 4 expressions evaluated **once per frame**, before anything else.
  Results = `s1..s4`. Only frame-level values valid (constants, `n1..n8`, `time`, `W`/`H`, `sin()` etc) — per-
  pixel vars (`x`,`y`,`r1`...) are meaningless here since Setup doesn't run per pixel.
- **Intermediate tab** (`Intermediate 1-4`): 4 expressions evaluated **once per pixel**, after Setup,
  before Channel. Per-pixel vars allowed. Results = `i1..i4`. Hoist any math constant across a pixel's
  channels here to cut redundant work.
- **Config tab**: **Random Seed** + Randomize button (seeds `rand()`/`rands()` — needed when multiple
  Custom Tool nodes must differ randomly). **Number/Point Controls**: per-control `Show` checkbox +
  rename field (hiding a Point also removes its viewer crosshair).
- **Channels tab**: one expression per output channel — RGBA, **Z**, **UV**, **XYZ Normal**, evaluated
  once per pixel using `s1-4`/`i1-4`. RGBA should return 0.0-1.0 (clipped on integer output); Vector/
  Normal ≈ -1.0..1.0; Coverage 0.0..1.0; Depth any value.

**Full expression syntax** (verbatim, p.1356-1360):
Value vars: `n1..n8` numeric inputs; `p1x..p4x`/`p1y..p4y` position; `s1..s4` Setup results; `i1..i4`
Intermediate results; `time`; `x`,`y` current pixel (0.0-1.0; no suffix = primary image); `w`/`w1..w3`,
`h`/`h1..h3` width/height; `ax`/`ax1..ax3`, `ay`/`ay1..ay3` aspect X/Y.
Channel vars (per image1-3): `c1..c3` current channel (context-sensitive — copy/paste across R/G/B
fields safely); `r1..r3`/`g1..g3`/`b1..b3`/`a1..a3`; `z1..z3` Z-buffer; `cv1..cv3` Z coverage; `u1..u3`/
`v1..v3` UV; `nx1..nx3`/`ny1..ny3`/`nz1..nz3` XYZ normal; `bgr/bgg/bgb/bga1..3` background RGBA;
`vx1..vx3`/`vy1..vy3` X/Y motion vector.
Sampling functions (`[ch]`=channel letter, `[#]`=image 1-3): **`get[ch][#]b(x,y)`** — 0 if out of bounds
(all channels), e.g. `getr1b(0,0)`. **`get[ch][#]d(x,y)`** — edge-clamped if out of bounds (RGBA only).
**`get[ch][#]w(x,y)`** — wraps if out of bounds (RGBA only). Coordinates are normalized 0.0-1.0 — use
`1.0/w1`, `1.0/h1` as a step size (typically precomputed in Setup as `s1`/`s2`).
Math fns: `pi`, `e`, `log(x)` (base-10), `ln(x)`, `sin/cos/tan(x)` (deg), `asin/acos/atan(x)` (result deg),
`atan2(x,y)`, `abs(x)`, `int(x)`, `frac(x)`, `sqrt(x)`, `rand(x,y)`, `rands(x,y,s)` (seeded), `min(x,y)`,
`max(x,y)`, `dist(x1,y1,x2,y2)`, `dist3d(x1,y1,z1,x2,y2,z2)`, `noise(x)`/`noise2(x,y)`/`noise3(x,y,z)`
(Perlin), `if(c,x,y)` (x if c!=0 else y).
Operators: `!x`, unary `-x`/`+x`, `x^y`, `x*y`, `x/y`, `x%y`, `x+y`, `x-y`, `<`,`>`,`<=`,`>=`,`=`/`==`,`<>`/`!=`,
`&`/`&&` (AND), `|`/`||` (OR) — comparisons/logic return 1.0/0.0.

**Worked examples** (verbatim): *Centered rotation* by `n1`: Setup `s1=cos(n1)`, `s2=sin(n1)`;
Intermediate `i1=(x-.5)*s1-(y-.5)*s2+.5`, `i2=(x-.5)*s2+(y-.5)*s1+.5`; Channel R/G/B/A =
`getr1b(i1,i2)`/`getg1b(i1,i2)`/`getb1b(i1,i2)`/`geta1b(i1,i2)` (ignores aspect; center-only rotation).
*3x3 box blur* (dupes a Custom Filter node): Setup `s1=1.0/w1`, `s2=1.0/h1`; Channel R =
`(getr1w(x-s1,y-s2)+getr1w(x,y-s2)+getr1w(x+s1,y-s2)+getr1w(x+s1,y)+getr1w(x-s1,y)+r1+
getr1w(x-s1,y+s2)+getr1w(x,y+s2)+getr1w(x+s1,y+s2))/9` (repeat for g/b/a substituting
`getg1w`/`getb1w`/`geta1w`, `g1`/`b1`/`a1`). Gotcha: offset by `s1`/`s2` (normalized step), never literal
`+1`, or you resample the same pixel repeatedly.

### Fields [FLDs] (p.1362)
Interlace/de-interlace utility: field<->frame interpolation, PAL/NTSC standards conversion, or interlacing
two images together (background = dominant field 1, foreground = field 2).
- Inputs: `Stream1` (orange, primary), `Stream2` (green, optional, only for merging two streams).
- **Operation**: `Do Nothing` (Process Mode only) / `Strip Field 2`|`Strip Field 1` (half-height output) /
  `Strip Field 2/1 and Interpolate` (drop + interpolate replacement, keeps full height — feed frames not
  fields) / `Interlace` (combine fields from one stream in pairs, or single frames from two streams, into
  double-height frames) / `De-Interlace` (split fields from one stream into double-count half-height
  frames). **Reverse Field Dominance** (swap field order).
- **Process Mode**: `Full Frames` / `NTSC Fields` / `PAL Fields` / `PAL Fields (Reversed)` / `NTSC
  Fields (Reversed)` / `Auto` (match input; mixed types default to fields).

### Frame Average [Avg] (p.1365)
Averages a run of frames — long-shutter motion blur sim, or aids time warps/noise removal.
- Input: `Input` (orange) only.
- Controls: **Sample Direction** `Forward`/`Both`/`Backward`. **Missing Frames**: `Duplicate Original` or
  `Blank Frame`. **Frames** (count to average).

### Keyframe Stretcher [KFS] (p.1366)
Rescales upstream keyframe animation to fit the comp's *current* duration — key for title templates that
must adapt to whatever timeline duration Resolve's Edit/Cut page drops them into. For a single
parameter (not a subtree), use the **Keystretcher modifier** instead.
- Input: `Input` (orange — can be a Merge whose FG/BG are animated even if the Merge itself isn't).
- Keyframes tab: **Source Start/Source End** (match the animation spline's actual range). **Stretch
  Start/Stretch End** (a *middle* zone that stretches/squishes; keys outside it keep their original frame-
  offset from Start/End). **Stretch Edges Instead** (overrides Start/End — stretches the outer edges
  instead). Note: the Spline Editor still shows only original keyframe positions — only playback timing
  changes, not the spline data.
- Recipe (p.1367): 50-frame anim, keys at 0/10/40/50. Source Start=0, Source End=50. Stretch
  Start=11, Stretch End=39 keeps first/last 10 frames at original speed while stretching only the middle
  to fill a longer (e.g. 75-frame) comp.

### Run Command [Run] (p.1368)
Executes an external command/batch file at render start, render end, or once per frame — net-render
orchestration, custom post-processing, FTP transfer, print-on-render.
- Input: `Input` (orange, optional — if connected, waits for that node to finish first; typically chained
  after a Saver; non-zero return from the launched app fails the node).
- Frame tab: **Hide** (suppress launched window). **Wait** (block render until the process exits;
  unchecked = fire-and-forget). **Frame Command** (path/command + Browse). **Interactive** (allow user
  input). Wildcards: **`%a`**=Number A thumbwheel, **`%b`**=Number B thumbwheel, **`%t`**=current
  frame (unpadded), **`%s`**=large text field. Zero-pad with **`%0x`** (x=digits), e.g.
  `test%04t.tga`->`test0000.tga`...`test0010.tga`. Space-pad with `%x`.
- Start/End tabs: file browsers for render-start/render-end commands.
- Recipe (p.1368-1371): copy each rendered frame elsewhere as it completes. Batch file
  (`copyfile.bat`): `@echo off` / `set parm=%1 %2` / `copy %1 %2` / `set parm=`. Chain Run Command after
  the Saver; Frame Command = `C:\copytest.bat D:\test%04f.exr C:\` (adjust paths). Check Hide to
  suppress the console flash per frame. Also valid: FusionScript, VBScript, JScript, CGI, Perl.

### Set Domain [DOD] (p.1371)
Manually sets/adjusts an image's active/valid area (DoD), no physical resize; speeds downstream
compute-heavy nodes.
- Inputs: `Input` (orange, required), `Foreground` (green, optional — if connected, replaces
  Background's DoD wholesale with Foreground's).
- Controls: **Mode** `Set` (sliders default to full extent, 0-1) vs `Adjust` (sliders default 0 = no
  change; positive shrinks DoD, negative expands to include more data). **Left/Bottom/Right/Top**
  (same 0..1 border semantics as Auto Domain).

### SpeedWarp [SPDw] (p.1373)
AI retiming node (DaVinci neural network) synthesizing new in-between frames from analyzed motion —
stutter-free slow motion beyond traditional blend/interpolation retiming.
- Input: `Input` (orange) only.
- Controls: **Speed** wheel (1.0 = none; 0.5 = half speed; 2.0 = double). **Delay** (offset output start
  frame; + = later, - = earlier). **Mode**: `Faster` vs `Better`.

### Switch [Swi] (p.1375)
Selects one of several inputs to pass through — works with 2D, Shapes, 3D; also available as a
**Switch modifier** on any supported control (context menu's Modify With/Insert submenus).
- Inputs: up to 9 via Config slider; type a number directly into **Number of Inputs** for more.
- Controls: **Source** switcher. Config: **Number of Inputs**, **Name X** rename fields.

### Time Speed [TSpd] (p.1376)
Static speed change/reverse/delay (constant rate only — for animated ramps use Time Stretcher).
**Flow** mode consumes pre-existing Optical Flow `Vector`/`BackVector` channels (generate upstream —
**Time Speed does not generate flow itself**) and **destroys** them after computing; add a fresh Optical
Flow node *after* if downstream needs flow on the retimed footage.
- Input: `Input` (orange) only.
- Controls: **Speed** (%; 2.0=200%, 1.0=100%, 0.5=50%, 0.1=10%; negative reverses; **cannot be
  animated**). **Delay** (frame offset; - earlier, + later). **Interpolate Mode**: `Nearest` (drop/duplicate
  frames, cheapest/roughest) / `Blend` (dissolve duplicated adjacent frames, cheap+smoother) / `Flow`
  (most expensive/highest quality via Optical Flow vectors; can artifact on crossing motion or
  unpredictable camera). **Sample Spread** (Blend only; 0.5 = 50% frame-before + 50% frame-ahead +
  0% current). **Depth Ordering** (Flow only): `Fastest on Top` (e.g. a car moving through a locked-off
  shot draws over the slower background) vs `Slowest on Top` (e.g. camera panning to follow the car —
  background now faster than car). **Clamp Edges** (Flow only; removes transparent edge gaps from
  interpolation but can stretch/artifact near frame edges on moving subjects/camera — use sparingly).
  **Edge Softness** (Flow + Clamp Edges; ~0.01 if >1 Source Frame/Warp Direction box is on, ~0.03 if
  only one). **Source Frame and Warp Direction** checkboxes (Flow only, each blended in if checked):
  `Prev Forward`/`Next Forward`/`Prev Backward`/`Next Backward`. **Freeze Frame** button (auto-sets
  Speed/Delay to freeze on current frame).

### Time Stretcher [TST] (p.1379)
Like Time Speed but speed is **animatable via a spline** (nonlinear remap) — ramp to 200%, back to
normal, pause, reverse like a VCR rewind. Same Flow-mode caveats as Time Speed (needs upstream
Optical Flow, destroys Vector/BackVector after use).
- Input: `Input` (orange) only.
- Controls: **Source Time** (Bézier spline — value at each key = which source frame to sample; starts
  as one key at 0.0 on the frame the node was added; may need "Edit" from its contextual menu, or
  "Display all Splines" from the Spline Editor menu, to become visible). Shares **Interpolate Mode**/
  **Sample Spread**/**Depth Ordering**/**Clamp Edges**/**Edge Softness**/**Source Frame and Warp
  Direction** with Time Speed above (identical semantics).
- Recipe (p.1381): shrink 100 frames to 25 — Current Time=0, Source Time=0.0; advance to frame 24,
  Source Time=99; confirm spline is linear -> Fusion interpolates 100 down to 25. To then hold the last
  frame 30 frames and play backward at normal speed: advance to frame 129, right-click Source Time
  -> Set Key; advance to frame 229 (129+100); set Source Time to 0.0.

### Wireless Link [Wire] (p.1382)
De-clutters a tree by "wirelessly" mirroring one 2D node's output elsewhere, no drawn connection line.
Use sparingly. No inputs (free-standing). Controls: **Input** field — drag the source node in; changes
propagate; connect the Wireless Link's output normally downstream.

### Common Miscellaneous controls
Settings tab: Blend, Process When Blend Is 0.0, RGBA selector, Apply Mask Inverted, Multiply by Mask,
Use Object/Material+Correct Edges+ID sliders (Matte-common), Use GPU, Motion Blur family (Mask-
common), Hide Incoming Connections, Comments, Scripts. (No Clipping Mode block here.)

---

## Optical Flow Nodes (Ch.53, p.1386-1405)

### Optical Flow [OF] (p.1387)
Analyzes per-pixel motion across frames; stores results in **Vector**/**Back Vector** aux channels for
downstream use (Vector Motion Blur, Vector Distort, Time Speed/Stretcher Flow mode, Repair Frame,
Smooth Motion, Tween, Vector Denoise/Transform/Warp).
- Input: `Input` (orange) only.
- Gotcha: Time Stretcher/Time Speed expect channel order `A.FwdVec` then `B.BackVec`, but Optical
  Flow *generates* `A.BackVec` then `A.FwdVec` — flagged explicitly by the manual (p.1387).
- Tips: render once to OpenEXR via a Saver if flow is slow to iterate on (embeds vector channels for
  reload). Deflicker footage first — flicker corrupts flow matching. Add a **Smooth Motion** node after
  with forward/backward vector smoothing enabled. View vectors: viewer right-click > Channel >
  Vectors, then Options > Normalize Color Range.
- **Method** dropdown (shared w/ Repair Frame/Tween): `Advanced` (GPU-based, same algorithm used
  elsewhere in Resolve) vs `Classic` (CPU-based, back-compat; may suit Stereo3D better).
- Shared tuning concepts (both methods): **Warp Count** (lower=faster; the algorithm progressively
  warps one image to match the other — past convergence, extra warps waste time; time scales linearly
  in Classic). **Iteration Count** (lower=faster, same diminishing-returns logic; linear time in Classic).
  **Smoothness** (higher = handles noise better, lower = more detail).
- Advanced-only: **Half Resolution** (resize down before tracking, pure speed tradeoff). **Output
  Vectors as Layers** (multi-layer-pipeline-compatible export; consumers: Smooth Motion, Vector
  Denoise, Vector Transform, Vector Warp, TimeSpeed/TimeStretcher Flow mode).
- Classic-only: **Proxy (for Tracking)** (resize-down for speed; time ~proportional to pixel count —
  Proxy=2 -> ~4x speedup, Proxy=3 -> ~9x). **Edges** (second smoothness axis tied to color edges; low
  = smoother flow that overshoots edges; high = flow tracks color edges tightly, risking streaked
  interpolation — lower for Z/DoF derivation, higher for interpolation). **Match Weight** (typical
  **0.7-0.9**; low = match large structural features, high = match small sharp variations; raise for
  Stereo3D lighting-driven L/R differences — still deflicker/color-match first). **Mismatch Penalty**
  (Quadratic<->Linear; Quadratic penalizes big dissimilarities [more disparity noise], Linear more tolerant
  [smoother]). **Filtering**: Catmull-Rom (better quality, steeply higher cost) vs default.

### Repair Frame [REP] (p.1391)
Replaces a damaged/missing frame or region using its two neighbors; computes its own optical flow
internally (upstream Optical Flow node not required, but slower without pre-cached flow). Destroys any
aux channels after computing. Shares all Optical Flow Classic/Advanced controls.
- Inputs: `Input` (orange), `Effect Mask` (blue, limit repair area).
- Controls: **Depth Ordering** (`Fastest On Top`/`Slowest On Top`, same semantics as Time Speed).
  **Clamp Edges** + **Edge Softness** (same guidance as Time Speed). **Source Frame and Warp
  Direction** checkboxes (Prev/Next Forward/Backward). **Optical Flow Options** (Classic/Advanced
  tuning as above).
- Tip: if source color varies frame-to-frame, the repair can be visible (must pull color from adjacent
  frames) — deflicker, CC, or use a soft-edged mask first.

### Smooth Motion [SM] (p.1393)
Temporally smooths AOV channels (Disparity, Vectors, Normals, Z...) via optical flow across neighboring
frames — e.g. reduces stereo-3D disparity flicker. **Requires** precomputed Vector/BackVector or prints
Console errors; if a *specific* checked channel just isn't present, it silently no-ops for that channel (no
error at all).
- Input: `Input` (orange) — must carry precomputed Vector/BackVector.
- Controls: **Channel** checkboxes (any AOV channel, not just RGBA).
- Gotcha: smoothing Vector/BackVector themselves can *worsen* interpolation on erratic/jittery/
  bouncing motion.
- Tip: chain 2+ nodes for wider windows — 1 node examines 3 frames (prev/current/next), 2 -> 5, 3 -> 7.
  Alt technique: first node smooths Vector/BackVector only; second smooths the target channel (e.g.
  Disparity) using those already-smoothed vectors.

### Tween [Tw] (p.1395)
Reconstructs a missing frame by interpolating between two **non-sequential** neighboring frames (unlike
Time Speed/Stretcher). Generates its own optical flow internally (no upstream Optical Flow node
needed) and discards it — destroys input aux channels. Color-match/deflicker/denoise sources first.
- Inputs: `Input 0` (orange, previous frame), `Input 1` (green, next frame), `Effect Mask` (blue).
- Controls: **Interpolation Parameter** (0.0 = exactly frame A, 1.0 = exactly frame B, 0.5 = halfway).
  Plus Depth Ordering, Clamp Edges, Edge Softness, Source Frame and Warp Direction, and full Optical
  Flow Options — identical semantics to Repair Frame above.

### Vector Warping Toolset (Studio only) (p.1398)
3 nodes (Vector Denoise, Vector Transform, Vector Warp) for mapping/warping a single reference frame
across a sequence via optical flow — face replacement, digital makeup, sign replacement. Recipe: apply
VFX changes on one reference frame -> ensure the affected area stays visible across tracked frames ->
add Vector Warp, set reference frame, choose **Generate + Texture Map**, let flow propagate the change.

### Vector Denoise [VDn] (p.1398)
General temporal averaging across neighboring frames, but **motion-vector-compensated** (follows
moving subjects rather than static pixel positions). Requires precomputed Vector/BackVector.
- Input: `Input` (orange) only.
- Controls: **Average** (temporal window, frames). **Threshold** (upper cutoff ignoring flashes/brief
  highlights when averaging).

### Vector Transform [VXf] (p.1399)
Custom transform (resize/rotate/translate) on vector-channel tracking data — drives another image/
sequence, e.g. simulating kinetic-energy transfer or differing material response between objects.
- Inputs: `Input` (orange), `Attenuate Mask` (white).
- Controls: **Smooth UV** (average w/ neighbors to remove anomalies). **Smooth Vector** (smooth
  across neighboring frames — pre-process before a texture-mapped Vector Warp). **Attenuate UV**
  (amplify/decrease/zero the warp-map effect via magnitude). **Attenuate Vector** (reduce motion-vector
  length, dial warp strength full->none). **Center X/Y**, **Size X/Y** (reposition/rescale UVs). **Use Size
  and Aspect** (unlocks **Size** [uniform] and **Aspect**). **Angle** (UV rotation).

### Vector Warp [VWp] (p.1401)
Distorts a nominated reference frame/image per a source clip's motion vectors. **Input Layer** (source +
its Optical-Flow vectors) and **Texture Layer** (still/clip warped per that motion) — Input Layer needs
pre-existing vectors (run Optical Flow first). Good for adding/removing elements on non-rigid surfaces
(fabric, skin) since it follows deformation, not just rigid tracking.
- Inputs: `Input` (orange, sequence w/ precomputed Vector/BackVector), `Texture` (green, still texture).
- Controls: **Set Frame** (use current frame as reference). **Reference Frame** (which frame the Map/
  Texture overlay corresponds to). **Operation**: `Generate Warp` (build map into UV channels only) /
  `Generate Warp + Map` (build map AND warp the texture) / `Apply Warp Map` (warp texture from a
  previously generated map) / `UnWarp` (freeze at reference, reverse-warp current frame toward it).
  **Smooth UV**. **Grid Overlay** (viewer overlay). **Merge Warp over BG** (composite warped map over
  main image for review).

### Common Optical Flow controls
Settings tab: Blend, Process When Blend Is 0.0, RGBA selector, Apply Mask Inverted, Multiply by Mask,
Use Object/Material+Correct Edges+ID sliders (Matte-common), Hide Incoming Connections, Comments,
Scripts. (No Use GPU or Motion Blur block here.)

---

## Paint Node (Ch.54, p.1406-1414)

Stroke-based tool for wire/rig removal, cloning, hand-built masks/mattes, or original artwork. Each
stroke is an independently editable vector shape (brush/size/effect) with its own Apply Mode; most
styles are editable polylines, animatable in shape/length/size, pressure/velocity-reactive on tablet.
Unlimited undo/redo before committing.
- Inputs: `Input` (orange, required — sets the "canvas" size), `Effect Mask` (blue, limits paint area).
- Setups: paint directly on an incoming MediaIn, **or** (more flexible) paint on a fully transparent
  Background node sized to match, then Merge it as foreground over the real image (keeps the paint
  layer independently reorderable).

### Types of Paint Strokes (viewer toolbar order)
Unless noted, default duration = entire global range, editable per-stroke any time in the Keyframes
Editor.
- **Multistroke**: default selection, but not most-used — built for speed on bulk per-frame cleanup (e.g.
  100 tracking markers/frame). **Not editable after creation; default duration = 1 frame** (set Duration
  *before* painting; shaded, non-editable range shown in Keyframes Editor). Not trackable directly —
  group with **PaintGroup** modifier and animate the group instead.
- **Clone Multistroke**: Multistroke variant for cloning one area/image onto another; same speed/non-
  editability/1-frame-default caveats.
- **Stroke**: the default mental-model paint stroke — fully animatable/editable vector paint; can slow
  down with hundreds of strokes (use Multistroke for bulk work instead). Click **Select** in the toolbar
  once done to avoid accidental new strokes.
- **Polyline Stroke**: Bézier-path/polygon-style point-by-point construction (Click Append default, or
  Draw Append freehand); trackable/connectable to existing masks/paths.
- **Circle** / **Rectangle**: animatable primitive shapes.
- **Copy Polyline** / **Copy Circle/Rectangle**: closed-shape variants with animatable offset, for cloning
  a region onto another.
- **Fill**: Wand-Mask-like — fills contiguous similarly-colored pixels based on a selected channel.
- **Paint Group**: groups multiple strokes under one center/size control — the standard way to track/
  move/rotate Multistroke or Clone Multistroke sets (which can't be tracked individually).

### Editing Options Toolbar (Polyline Stroke, Copy Polyline, or any Stroke after Make Editable)
Same as the Mask nodes' Polylines toolbar: Click Append / Draw Append / Insert / Modify / Done /
Closed / Smooth / Linear / Select All / Keys / Handles / Shape / Delete / Reduce / Publish / Follow
Points / Roto Assist (Multiple Points, Distance, Reset).

### Controls tab (mode-specific controls hide themselves when not applicable)
**Brush Controls** — **Brush Shape**: `Soft Brush` (circular, soft edge) / `Circular Brush` (circular, hard
edge) / `Image Brush` (any node output or file as brush tip) / `Single Pixel Brush` (exactly 1px, no anti-
aliasing) / `Square Brush`; Cmd/Ctrl-drag in viewer resizes any shaped brush. **Vary Size**: `Constant` /
`With Pressure` / `With Velocity` (faster = thinner). **Vary Opacity**: `Constant` / `With Pressure` /
`With Velocity` (faster = more transparent). **Softness** (soft-brush edge amount). **Image Source**
(Image Brush only): `Node` (drag one into Source field) / `Clip` (any Loader/MediaIn-supported file) /
`Brush` (built-in library, Fusion > Brushes directory). **Color Space** (Fill only): sample color space.
**Channel** (Fill only): which channel's contiguity drives the fill (e.g. Alpha = contiguous alpha pixels).

**Apply Controls — Apply Mode**: `Color` (flat color strokes; tints when combined w/ an image brush) /
`Clone` (copies from elsewhere in the same or another node's image, w/ position+time offset; any node
can be the source) / `Emboss` / `Erase` (non-destructively reveals underlying image through other
strokes) / `Merge` (like Color but no color controls; best w/ image brushes) / `Smear` (uses stroke
direction/strength as a guide) / `Stamp` (ignores alpha/transparency — decals) / `Wire` (Wire Removal:
samples adjacent pixels, draws inward — purpose-built for wire/rig removal).

**Stroke Controls** — **Size** (brush diameter for Soft Brush/Circle; Cmd/Ctrl-drag to adjust
interactively). **Spacing** (distance between stroke "dabs"; low = dotted line, high = dense continuous).
**Stroke Animation** (vector strokes only): `All Frames` (default) / `Limited Duration` (uses Duration
slider) / `Write On` (adds a spline reproducing the exact draw timing — the stroke "writes itself on"; use
a Time Stretcher on the spline to retime, or thin points in the Spline Editor to smooth) / `Write Off`
(reverse — end back to start) / `Write On Then Off` / `Trail` (start+end points animate simultaneously,
offset by Duration — a moving painted segment following the path; starts on the current frame when
selected). **Duration** (frames/stroke — Multistroke/Clone Multistroke, or Limited Duration mode; can
be 0.5 for single-field duration in Fields-mode processing, common for frame-by-frame roto). **Write
On/Off range slider** (Start 0.0->1.0 erases, End 0.0->1.0 draws on; animatable, usually auto-driven by
the Write On/Off modes). **Make Editable** (Vector strokes only — converts a Stroke to an editable
polyline spline).

### Paint Node Modifiers
Every viewer-drawn stroke creates a modifier entry in the **Modifiers tab** — a reorderable/editable/
deletable stack of paint-stroke operations, each carrying the same Brush/Apply/Stroke controls as the
main Controls tab. Multistroke internally avoids bloating this stack even with many strokes.

### Paint Keyboard Shortcuts (verbatim)
Painting: Cmd/Ctrl+left-drag = brush size; Option/Alt+click = pick color from viewer. Cloning:
Option/Alt-click = set clone source; hold **O** = 50%-transparent clone overlay (pref
`Tweaks.CloneOverlayBlend`); **P** = toggle opaque overlay; with overlay showing, arrow keys move the
clone source (or drag crosshair/sliders), Option/Alt+Left/Right = angle, Option/Alt+Up/Down = size,
Shift+Cmd/Ctrl = finer/coarser steps, `[`/`]` = Time Offset (needs a Clone Source node set in Source
Node field). Copy Rect/Ellipse: Shift+drag constrains shape. Single stroke (not Multi/Polyline): X/Y flips
it. Paint Groups: Cmd/Ctrl+drag moves the group crosshair without moving the group.

---

## Gotchas and non-obvious behavior

- Lowering a mask's **Level** dims the *entire* mask channel, including other opaque shapes stacked
  beneath it via Paint Mode — not scoped to just that shape (p.1233).
- **Invert checkbox** inverts the whole mask; **Invert Paint Mode** only inverts the new/input overlap.
- Mask nodes' Clipping Mode has only **Frame**/**None** — no **Domain** (Matte/Misc/Optical Flow get
  all three). Don't assume parity across categories.
- **Primatte's orange input is the Foreground** (the screen plate) — every other node uses orange for
  background/primary; an explicit exception (p.1314). Its green **Background** input, if connected
  without a **Replacement Image**, silently doubles as the spill-suppression source (p.1314).
- Garbage mattes of different modes can't mix in one tool — chain a Matte Control node instead.
- **Post-Multiply Image** defaults on for every keyer; disabling it breaks premultiply downstream — use
  Merge **Subtractive**, not Additive, after.
- **Time Speed's Speed cannot be animated** — use Time Stretcher for ramps.
- Time Speed/Stretcher, Tween, and Repair Frame all **destroy Vector/BackVector** after Flow-mode use
  — add a fresh Optical Flow node *after* if downstream needs flow data.
- **Optical Flow's generation order is reversed** vs. what Time Speed/Stretcher expect (`A.BackVec,
  A.FwdVec` generated vs. `A.FwdVec, B.BackVec` expected) — explicit manual callout (p.1387).
- **Smooth Motion** needs precomputed Vector/BackVector or prints Console errors, but a missing
  *specific* checked channel silently no-ops — silence isn't confirmation of success.
- **Tween** generates and discards its own flow (no upstream Optical Flow node needed); its two inputs
  need not be sequential, unlike Time Speed/Stretcher.
- **Custom Tool Setup expressions run once per frame** — per-pixel vars there are meaningless; only
  Intermediate/Channel run per pixel. Sampling suffixes differ on out-of-bounds: `b`=0/black,
  `d`=edge-clamp, `w`=wrap. Coordinates are normalized 0.0-1.0 — offset by `1.0/w`/`1.0/h`, never `+1`.
- **Run Command's Wait** toggles whether render blocks until the external process exits; unchecked
  runs in parallel — risky if a later node depends on that output.
- **Keyframe Stretcher** changes only playback timing — the Spline Editor still shows original keys.
- **MultiPoly's "Split here"** moves the selected shape *and everything below it* into a new node.
- **Magic Mask's Reference Time** cannot change later without destroying existing tracking.
- Delta Keyer's **Lock Alpha/Spill Removal** checkboxes default combined; unlocking lets alpha-
  generation and spill-subtraction use separate tuning — easy to miss since the default "just works."

