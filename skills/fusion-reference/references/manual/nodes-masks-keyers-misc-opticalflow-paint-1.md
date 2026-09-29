<!-- nodes-masks-keyers-misc-opticalflow-paint.md part 1 of 3; index: nodes-masks-keyers-misc-opticalflow-paint.md -->
# Fusion Nodes: Mask, Matte, Metadata, Miscellaneous, Optical Flow, Paint

Scope: Fusion Reference Manual pages 1231-1414 (Chapters 49-54). Use when: building/scripting mask
shapes, pulling or refining a key/matte, reading/writing clip metadata, using utility nodes (Custom Tool,
time-remap nodes, Run Command, DoD tools), doing optical-flow retiming/repair/warp, or driving Paint
for wire removal, cloning, or hand-drawn mattes.

## Mental model

- **Bracketed abbreviation** = Select Tool dialog search string / scripting reference (full list under
  Scripting).
- **Effect Mask (blue input)**, on almost every node: connect any mask-producing node to limit where
  the effect applies; applied *after* the node processes.
- **Garbage Matte (gray)** forces areas transparent; **Solid Matte (white)** forces areas opaque (e.g.
  hold out blue eyes against a blue screen). Different garbage-matte "modes" can't mix in one tool —
  chain a Matte Control node for an opposite-effect garbage matte.
- **Mask combination = Paint Mode** (documented once under Mask common controls): whenever a
  mask feeds another mask/effect-mask input, this menu decides how they combine.
- **Level vs Blend vs Invert(checkbox) vs Invert(Paint Mode)**: Level scales the *whole* mask channel
  (dims other shapes stacked underneath too — classic gotcha). Invert checkbox inverts the whole mask;
  Invert Paint Mode only inverts the overlap area.
- **Keyer pecking order**: Delta Keyer first for blue/green screen; Primatte (Studio only) second; Ultra
  Keyer third. Chroma Keyer = general non-screen color removal. Luma Keyer = luminance/any single
  channel. Difference Keyer needs a clean BG plate, usually only yields a rough matte.
- **Clipping Mode**: `Frame` (full frame, outside-DoD=black — default) / `Domain` (respect upstream
  DoD) / `None` (no source clipping). Mask nodes expose only Frame/None; Matte/Misc/Optical Flow
  expose all three where documented.
- **Domain of Definition (DoD)**: bounding box of non-zero pixels, skips empty-region processing;
  doesn't change actual image size. Auto Domain/Set Domain manipulate it directly.
- **Filter menu** (recurs on soft-edge/blur controls): `Box` (fastest, low quality) / `Bartlett` (pyramid,
  speed/quality compromise) / `Multi-box` (Num Passes: 1-2 ≈ Box/Bartlett, 4+ ≈ Gaussian, no ringing) /
  `Gaussian` (best quality, slowest, faint ringing possible on float pixels).
- **Premultiplied-alpha discipline**: Alpha Divide -> CC -> Alpha Multiply (or a node's own Pre-Divide/
  Post-Multiply checkbox). Keyers' **Post-Multiply Image** (on by default) — disabling it needs Merge's
  **Subtractive** mode instead of Additive downstream.
- **Custom Tool** = per-pixel expression node, the escape hatch for math no built-in node covers.
- **Optical Flow** stores motion in `Vector`/`BackVector` aux channels, consumed (usually destroyed) by
  Time Speed/Stretcher (Flow mode), Repair Frame, Smooth Motion, Tween, and the Studio-only Vector
  Warp/Transform/Denoise toolset.

---

## Mask Nodes (Ch.49, p.1231-1271)

### Common mask controls (documented once)
- **Show View Controls**: show/hide onscreen handles.
- **Level**: mask-channel opacity (1.0 = opaque unless soft-edged); lowering it dims *all* pixels in the
  channel, even other shapes stacked underneath (p.1233).
- **Filter**: see Mental Model.
- **Soft Edge**: feather amount (0.0 = crisp).
- **Border Width**: outline thickness (Solid off) or edge thicken/narrow amount (Solid on).
- **Paint Mode** (shown once a mask feeds an effect-mask input): `Merge` (default) / `Add` / `Subtract` /
  `Minimum` / `Maximum` / `Average` / `Multiply` / `Replace` (new mask replaces input where they
  intersect; black areas of new mask leave input untouched) / `Invert` (overlap area inverted; gray =
  partial) / `Copy` (discard input, keep new) / `Ignore` (discard new, keep input).
- **Invert** (checkbox): inverts whole mask (vs. Invert Paint Mode = overlap only).
- **Solid**: filled shape vs. outline-only (width = Border Width).
- **Center X/Y, Size, Angle, X/Y/Z Rotation**: standard transform; Size scales without a keyframe or
  altering point-relative behavior.
- **Fill Method**: `Alternate` vs `Non Zero Winding` (switch if overlapping segments create unwanted
  holes).
- **Fit Input** (Bitmap/Ranges, when source size ≠ mask size): `Crop` / `Stretch` (non-uniform, can
  distort) / `Inside` (uniform scale until one axis fits inside) / `Width` / `Height` (uniform scale to match
  that axis) / `Outside` (uniform scale until one axis fits outside).
- **Image tab**: **Output Size** = Comp default / Source input's res / **Custom** (locks W/H/Pixel Aspect/
  Depth to Frame Format prefs; right-click for a preset list). **Depth**: 8/16/32-bit or Float (HDR beyond
  0..1). **Clipping Mode**: `Frame`/`None` only (no Domain option for masks).
- **Settings tab**: Motion Blur family (toggle, **Quality** samples/side, **Shutter Angle** [360 = one full
  frame], **Center Bias**, **Sample Spread**), **Use GPU** (Disable/Enabled/Auto), **Comments**,
  **Scripts** (3 render-time script fields).

### Polylines toolbar (shared: B-Spline, Polygon, Mask Paint, Paint node polyline strokes)
Click (Bézier append) / Draw (freehand) / Insert / Modify / Done (locks; whole spline still movable/
rotatable) / Closed / Smooth / Linear / Select All / Keys / Handles / Shape (reshape rect for group edits)
/ Delete / Reduce (Freehand precision window, cuts point count) / Publish (points or path, for tracker
attach) / Follow Points (offset-follow a published point) / Double Poly (soften part of a curve — inner
shape stays sharp, outer shape sets softness spread; Tab cycles to outer, or Controls > Outer Polygon)
/ Multiframe (`None`/`All`/`Prev`/`Next` — which keyframes a point edit touches) / Onion Skinning (mix
nearby frames' shapes for alignment) / Roto Assist (snap points to nearest edge; sub-options: Multiple
Points one-click multi-point trace, Distance search-radius dialog, Reset clears snap state).

### Bitmap Mask [Bmp] (p.1232)
Turns any image channel into a mask; not required for a plain effect-mask connection but adds channel
choice, softness, clipping unavailable on a raw connection — also needed for non-effect-mask mask
inputs (Garbage Matte, Pre-Matte, etc.).
- Inputs: `Input` (orange, source), `Effect Mask` (blue).
- Controls (+ mask common): **Channel** (R/G/B/Alpha, Hue/Luminance/Saturation, or Aux Coverage).
  **Threshold Low/High** (clip below Low to black, force above High to white). **Use Object/Use
  Material** (mask from a 3D render's Object/Material ID channel). **Center X/Y**, **Fit Input**.
- Gotcha: chain two Bitmaps and use the second's Paint Mode to combine mattes (add/subtract/
  multiply) for advanced garbage-matte builds.

### B-Spline Mask [BSp] (p.1237)
Like Polygon Mask but B-Spline math: one control point per vertex (no Bézier handles) pulls the curve
toward it — far fewer points needed for smooth shapes. Auto-animates (keyframes on creation and on
any shape edit at a new frame).
- Inputs: `Effect Mask` only.
- Controls: mask common, plus **Adjusting Tension**: select a point, hold **W**, drag left/right.

### Ellipse Mask [Elp] (p.1241)
Circle by default; independent Width/Height/Angle for any ellipse.
- Inputs: `Effect Mask` only.
- Controls: mask common plus **Width**/**Height** (drag edges in viewer; diagonal-drag scales both
  proportionally), **Angle** (drag dashed handle or type value).

### Mask Paint [PNM] (p.1244)
Freehand/pressure-sensitive mask painting (brush, primitives, or polyline strokes). Controls tab is
functionally identical to the Paint node except: no Channel Selector (single-channel mask, single-Alpha
color), and the tab is named **Mask** not Controls. Strokes can each carry their own duration
(whole project / one frame / arbitrary field range), editable per-stroke in the Keyframes Editor;
**Multistrokes** trade per-stroke editability for speed on bulk cleanup.
- Inputs: `Effect Mask` only.
- Use when: patching holes in another mask (e.g. a Bitmap matte) by hand.

### MultiPoly [MPly] (p.1247)
Holds multiple Polygon/B-Spline shapes in one node's scrolling list (like MultiMerge for layers) —
draw, animate, rename, reorder, toggle many roto shapes without stacking nodes.
- Usage: press **Polygon** or **BSpline** in Inspector to add a shape row.
- List right-click: **Duplicate**, **Split here** (moves this shape + everything below it into a new
  MultiPoly node), **Rename**, **Reset to default** (keeps entry, clears shape/controls), **Delete**.

### Polygon Mask [Ply] (p.1249)
Bézier-spline polyline mask for irregular shapes; auto-animates. Same Polylines toolbar and Fill Method
as B-Spline.
- Inputs: `Effect Mask` only. Controls: mask common (Center/Size/Angle/Rotation/Fill Method/Solid/
  Border Width).

### Ranges Mask [RNG] (p.1254)
Like Bitmap Mask but does spline-based Shadow/Midtone/Highlight range selection (akin to a Color
Corrector qualifier) instead of a single luminance cut.
- Inputs: `Input` (orange), `Effect Mask` (blue).
- Controls: **Channel** (R/G/B/Alpha/Hue/Luminance [default]/Saturation/Aux Coverage). **Shadows/
  Midtones/Highlights** buttons pick which range outputs as white (midtones = whatever's left after
  low/high masks apply). **Mini Spline Editor**: 4 Bézier points (2 handles = start of shadow/highlight
  range, 2 = end; handles control falloff), X/Y numeric fields for precise placement. **Presets**:
  `Simple` (linear) / `Smooth` (natural falloff). Plus mask common Level/Filter/Soft Edge/Paint Mode/
  Invert/Fit Input/Center X-Y.

### Rectangle Mask [Rec] (p.1259)
Square/rectangular mask, defaults to comp aspect.
- Inputs: `Effect Mask` only. Controls: mask common plus **Width/Height** (independent), **Corner
  Radius** (0.0 sharp -> 1.0 max round), **Angle**.

### Triangle Mask [Tri] (p.1262)
No Center/Size/Angle — instead each corner (**Point 1/2/3**) is independently positionable, publishable,
path-animatable, or tracker-attachable (right-click the point or Position control).
- Inputs: `Effect Mask` only.

### Wand Mask [Wnd] (p.1265)
Magic-Wand-style: click a crosshair on a source color, mask grows to contiguous same-color pixels.
- Inputs: `Input` (orange, sample source), `Effect Mask` (blue).
- Controls: **Selection Point** (X/Y crosshair; path/track/expression-drivable). **Color Space** (RGB/YUV/
  HLS/LAB). **Channel** (labels change per Color Space, e.g. R/G/B or Y/U/V). **Range** (0.0 = exact
  color only; higher = more similar colors included). **Range Soft Edge** (falloff of the range boundary).
  Plus mask common Level/Filter/Soft Edge/Paint Mode/Invert.

---

## Matte Nodes (Ch.50, p.1272-1339)

### Common matte controls (documented once)
Settings tab, every Matte tool: **Blend** (0.0 = pass-through, usually skips processing). **Process
When Blend Is 0.0** (force processing anyway, e.g. for a scripted side effect). **RGBA channel
selector** (limit effect to selected channels; deselected ones copied back post-process, except tools
with their own duplicate RGBA buttons that skip that channel entirely). **Apply Mask Inverted** (inverts
combined mask channel). **Multiply by Mask** (RGB x mask -> outside-mask pixels go black/
transparent). **Use Object/Use Material** + **Correct Edges** + **Object ID/Material ID sliders** (mask
from a 3D render's Object/Material ID aux channel; Correct Edges uses Coverage + Background Color
channels to clean multi-object edge aliasing; Sample button grabs an ID from the viewer). **Clipping
Mode**: Frame/Domain/None. **Use GPU**. **Hide Incoming Connections** (hides connector lines; drag
a node into the resulting empty Inspector field to "wire" it invisibly). **Comments**, **Scripts**.

### Common keying sub-block (recurs across Chroma/Delta/Ultra/Primatte/Magic Mask/Matte Control)
**Spill Method**: `None` / `Rare` (lightest) / `Medium` (best for green) / `Well Done` (best for blue) /
`Burnt` (blue, troublesome shots — expect to need heavy post-key CC, e.g. skin tones). **Spill
Suppression** slider (0 = none). **Fringe Gamma/Size/Shape** (brightness / expand-contract / push
toward outer vs inner edge of the halo). **Cyan/Red, Magenta/Green, Yellow/Blue**: 3-way CC the
fringe pixels. **Threshold** (low/high handles: below low -> black, above high -> white, between ->
gray). **Restore Fringe** (recover hair detail thresholding clipped, without softening the rest). **Invert
Matte**. **Solid Matte** input (white, forces opaque, e.g. blue eyes) + its own **Invert**. **Garbage
Matte** input (gray, forces transparent, e.g. mic booms) + **Invert** (inverted = removes everywhere
*except* the shape). Different garbage-matte modes can't mix in one tool. **Post-Multiply Image**
(default on; off -> use Merge Subtractive downstream). **Matte tab Filter/Blur/Contract-Expand/
Gamma**: Filter = Box/Bartlett/Multi-box/Gaussian; Blur softens edge (0 = hard cutout); Contract/
Expand grows(+)/shrinks(-) only semitransparent edge pixels (no effect on hard edge, usually paired
with Blur to fight fringing); Gamma raises/lowers only semitransparent gray values.

### Alpha Divide [ADv] (p.1273) / Alpha Multiply [AML] (p.1274)
Alpha Divide un-premultiplies color by alpha (pre color-correction); Alpha Multiply re-premultiplies
(post color-correction). No controls on either. Inputs: `Input` (orange) + `Effect Mask` (blue, applied
after processing, limits where the divide/multiply occurs).

### Chroma Keyer [CKy] (p.1275)
General color-removal keyer (any color, not blue/green-optimized — prefer Delta Keyer/Primatte for
screens).
- Inputs: `Input` (orange), `Garbage Matte` (gray), `Solid Matte` (white), `Effect Mask` (blue).
- Chroma Key tab: **Key Type** `Chroma` (RGB-based) vs `Color` (hue-based). **Color Range** (drag-
  select in viewer; sliders fine-tune). **Lock Color Picking**. **Soft Range**. **Reset Color Ranges**.
- Image tab: Spill Color/Suppression/Method (keying sub-block). Matte tab: Filter/Blur/Clipping Mode/
  Contract-Expand/Gamma/Threshold/Restore Fringe/Invert Matte/Solid+Garbage Matte/Post-Multiply
  (keying sub-block).

### Clean Plate (p.1280)
Pre-keying helper: builds a smoothed image of *just* the screen (opposite of keying — keep the screen,
discard the subject), feeding the Delta Keyer's dedicated **Clean Plate** input for finer, less-choked keys.
- Inputs: `Input` (orange, has the screen), `Garbage Matte` (white — areas NOT part of the screen, to
  exclude), `Effect Mask` (blue).
- Plate tab: **Method** `Color` (difference method, even screens) vs `Ranges` (chroma-range, better for
  shadowed/uneven screens). **Matte Threshold** (low/high). **Erode** (eats non-screen noise). **Crop**
  (trims edges). **Grow Edges** (expands screen color to fill holes). **Fill** (fills remaining holes from
  surrounding color). **Time Mode**: `Sequence` (new plate every frame) / `Hold Frame`.
- Mask tab: **Invert** (uses transparent parts of the garbage mask to clear the image, instead of solid
  parts).

### Cryptomatte [Cry] (Studio only) (p.1283)
Reads IDs embedded in an EXR's Cryptomatte layers (from a 3D renderer) — isolate objects/materials
without manual masking/keying.
- Inputs: `Input` (orange, EXR w/ embedded mattes) only.
- Controls: **View Layer** (which layer/type: Object, Material...). **View Mode**: `Colors` (flat per-ID) /
  `Edges` (source + outlines) / `Beauty` (plain source) / `Matte` (B/W selected matte). **Select Matte**:
  `Pick` (list, click/drag or Cmd/Ctrl-click multi-select) or `Mode` (eyedropper in viewer). **Selected
  Matte List** (yellow-highlighted in viewer): `Clear` / `Clear All` / `Clear Selected Layer`. **Expression**
  (regex to select layers). **Matte Layers** toggle (`Selected`/`View`/`All`).

### Delta Keyer (p.1285) — primary green/blue-screen keyer, full workflow
Tabs run in typical-use order: **Key** (master difference key) -> **Pre Matte** (built-in screen-smoothing)
-> **Tuning**/**Fringe**/**Matte** (finishing).
- Inputs: `Input` (orange), `Garbage Matte` (gray), `Solid Matte` (white), `Clean Plate` (magenta, from a
  Clean Plate node), `Effect Mask` (blue).
- **View Mode** (top of Inspector): `Pre Matte` / `Matte` (raw alpha, set viewer to alpha) / `Tuning
  Ranges` (false color: Shadows=red, Midtones=green, Highlights=blue) / `Status` (solid/transparent/
  in-between + areas affected by threshold, erode-dilate, solid mask) / `Intermediate Result` (untouched
  source color + final matte, chainable into another Delta Keyer) / `Final Result` (keyed + spill-
  suppressed).
- **Key tab**: **Background Color** (eyedropper-drag the screen color). **Pre-Blur** (blur before alpha
  generation, helps noise/edge artifacts). **Gain** (more influence for the screen color -> more
  transparency there). **Balance** (0 = min of the two non-dominant channels, 1 = max, 0.5 = half each).
  **Lock Alpha/Spill Removal Color Balance Reference** (unlock to use different references for alpha
  vs. spill-subtraction amount). **Color Balance Reference** (corrects for lighting/white-balance reducing
  screen purity, without altering the actual subtracted color).
- **Pre Matte tab** (a pre-key garbage-matte/clean-plate smoother; View Mode = Pre Matte to watch):
  **Soft Range** (extend range/rolloff). **Erode** (contract edge, protect detail). **Blur** (soften edges).
  **Pre Matte Range** (auto from viewer drags). **Lock Color Picking**. **Reset Pre Matte Ranges**.
- **Matte tab**: **Threshold**. **Restore Fringe**. **Erode/Dilate**. **Blur**. **Clean Foreground** (fills
  light-gray near-transparent holes). **Clean Background** (clips dark bottom range). **Replace Mode**:
  `None`/`Source`/`Hard Color`/`Soft Color` (weighted by how much background color was removed) +
  **Replace Color**.
- **Fringe tab**: full keying sub-block (Spill Method/Suppression, Fringe Gamma/Size/Shape, CMY) — the
  main spill-suppression location.
- **Tuning tab**: **Range Controls** (spline-adjustable Shadow/Highlight tonal maps). **Simple/Smooth**
  presets. **Lock Alpha/Spill Removal Tuning** (disable to separate alpha-gen tuning from spill-
  subtraction tuning). **Shadows/Midtones/Highlights** sliders (key strength per tonal range).
- **Mask tab**: **Solid Source Alpha**: `Ignore` / `Add` (source-alpha-solid areas become solid in solid
  mask) / `Subtract` (source-alpha-transparent areas become transparent in solid mask). **Solid
  Replace Mode/Color** + **Invert**. **Garbage Mask Invert** (normally solid areas remove image;
  inverted, transparent areas remove image instead).

### Depth Map [DMp] (p.1293)
Builds an alpha from a clip's *perceived* depth (image-based estimate, not real 3D Z) — for DoF sims,
distance-based grading, or fixing depth-correlated issues (e.g. a daylight window tinting only far
background actors blue).
- Inputs: `Input` (yellow), `Effect Mask` (blue).
- Controls: **Mode** `Faster` (scrub) vs `Better` (final quality). **Depth Map Preview** (checked by
  default; uncheck to use the alpha for grading rather than viewing it). **Invert**. **Adjust Map Levels**
  (off = full unclipped range; on = clips 0..1, previews Alpha-channel behavior, unlocks **Far Limit**
  [black level] / **Near Limit** [white level] / **Gamma**). Isolate Specific Depth: **Isolation** toggle,
  **Target Depth** (1 = full foreground, 0 = full background), **Tolerance**, **Softness**. Map Finesse:
  **Post Processing** toggle, **Post-Filter** (blend map to smooth areas/edges), **Contract/Expand**,
  **Blur**.

### Difference Keyer [DFK] (p.1296)
Keys from the difference between a background-only plate and background+subject plate; camera drift
usually leaves structure visible, so typically a *rough matte* to combine with others.
- Inputs: `Background` (orange, set only), `Foreground` (green, set+subject), `Garbage Matte` (gray),
  `Solid Matte` (white), `Effect Mask` (blue).
- Controls: **Threshold** (below low -> transparent, above high -> opaque, between -> gray based on
  the difference), then Filter/Blur/Clipping Mode/Contract-Expand/Gamma/Invert/Solid+Garbage
  Matte/Post-Multiply (keying sub-block).

### Luma Keyer [LKy] (p.1299)
Keys off luminance or any single channel (effectively a general channel keyer despite the name).
- Inputs: `Input` (orange), `Garbage Matte` (gray), `Solid Matte` (white), `Effect Mask` (blue).
- Controls: **Channel** (Red/Green/Blue/Alpha/Hue/Luminance/Saturation/**Depth [Z-buffer]**).
  **Threshold** (low/high). Then Filter/Blur/Clipping Mode/Contract-Expand/Gamma/Invert/Solid+
  Garbage Matte/Post-Multiply (keying sub-block).

### Magic Mask [MagM] (p.1303)
v2 is the current default (DaVinci Neural Engine auto-isolates a person/object or feature — face, hair,
arms, shoes — from click points). **Use Legacy Magic Mask** checkbox switches to the old algorithm for
older-project compatibility.
- Workflow: **positive clicks** (blue) include, **negative/subtractive clicks** (red, Option/Alt-click-drag)
  exclude sub-regions (e.g. a car's wheels, one book on a shelf). Usually one point per region suffices.
- Inputs: `Input` (orange), `Garbage Matte` (gray), `Solid Matte` (white), `Effect Mask` (blue).
- Tracking tab: **Mode** `Faster`/`Better`. **Point Mode**: Add/Subtract/Select(drag box, green)/Delete.
  **Tracking Controls**: Reverse / Reverse One Frame / Forward Then Reverse / Stop / Forward /
  Forward One Frame (frame-by-frame lets you catch and reposition a drifting point immediately).
  **Clear Points** Current/Range/All. **Go To Frame** First/Reference/Last Tracked. **Disk Cache**
  Regenerate All/Clear. **Reference Time** (frame points drawn — **cannot change later** without
  destroying tracking). **Processed Frames** (read-only Start/End).
- Matte tab: same Filter/Blur/Erode-Dilate/Gamma/Threshold/Restore Fringe/Invert Matte/Solid+
  Garbage Matte pattern as other keyers, plus Filter gains a **Fast Gaussian** (default) option.

### Matte Control [MAT] (p.1308)
Combines/manipulates alpha (or other channels) between two images — e.g. copy FG's alpha onto a BG
lacking one, or logic/arithmetic-combine two alphas.
- Inputs: `Background` (orange, receives channel), `Foreground` (green, source channel), `Garbage
  Matte` (gray), `Solid Matte` (white), `Effect Mask` (blue).
- Matte tab: **Combine**: `None` / `Combine Red|Green|Blue|Alpha` (that FG channel -> BG alpha) /
  `Solid` (BG alpha -> fully opaque) / `Clear` (BG alpha -> fully transparent). **Combine Operation**:
  `Copy` / `Add` / `Subtract` / `Inverse Subtract` (BG-FG) / `Maximum` / `Minimum` / `And` / `Or` /
  `Merge Over` / `Merge Under`.
- Then Filter/Blur/Clipping Mode/Contract-Expand/Gamma/Threshold/Restore Fringe/Invert Matte/
  Solid+Garbage Matte/Post-Multiply (keying sub-block), plus a **Spill tab** (Spill Color/Suppression/
  Method/Fringe Gamma/Size/Shape/CMY) — useful for adding spill suppression to an already-keyed
  image without re-keying.

### Primatte [Pri] (Fusion Studio only) (p.1313) — full keying workflow
Zone-based keyer (IMAGICA Corp.). Classifies RGB pixels into 4 zones: **Zone 1** complete background,
**Zone 2** FG w/ spill suppression + transparency, **Zone 3** FG w/ spill suppression only, **Zone 4**
complete foreground. No universal winner vs. Delta Keyer — try both, sometimes combine.
- Inputs: `Foreground` (**orange** — reversed from every other Fusion node; this is the screen plate),
  `Background` (green, optional — enables advanced edge blending; if connected without a Replacement
  Image it also serves as the spill-suppression reference), `Replacement Image` (magenta, optional, spill
  color source), `Garbage Matte` (gray), `Solid Matte` (white), `Effect Mask` (blue).
- **View Mode**: `Black` (subject on black) / `Composite` (final, over Background input) / `Defocus
  Foreground` (Pre Matte key out) / `Processed Foreground` (raw alpha, viewer=alpha) / `Hybrid Matte`
  (with Hybrid Rendering on — tune via Hybrid Blur/Erode) / `Lighting Foreground`/`Lighting
  Background` (Adjust Lighting's synthetic even backing screen).
- **Primatte tab, operational-mode buttons** (click a mode, scrub/click in viewer): **Auto Compute**
  (one-click backing-color + FG detection + Clean FG Noise — try first). **Select Background Color**
  (scrub the screen color; viewer toolbar Box/Median sample options — Median = 3x3 + median filter,
  cuts noisy picks; avoid sampling into a shadow you want kept). **Clean Background Noise** (scrub
  remaining white/light-gray screen-area noise to black). **Clean Foreground Noise** (scrub dark FG
  holes to white). **Spill Sponge** (quick spill removal by scrubbing) / **Matte Sponge** (fix accidentally-
  gray opaque areas) / **Restore Detail** (scrub BG regions to bring back translucent hair/smoke) /
  **Make Foreground Transparent** (one-time thin of an opaque FG region; for repeatable thinning use
  Matte(-)). **Spill(+)/Spill(-)**, **Matte(+)/Matte(-)**, **Detail(+)/Detail(-)**: paired increment buttons —
  scrub a sampled color/all-like-it once per click to add-back/remove spill, opaque-up/thin the matte
  density, or hide/reveal fine detail respectively; each `+` nullifies one `-` step; Detail(-) can reintroduce
  BG noise on imperfect shoots. **Algorithms**: `Primatte` (default, best quality, multifaceted polyhedron
  separation, both spill modes, slowest), `Primatte RT` (single planar surface, fastest, weak on
  desaturated screens, no Complement spill), `Primatte RT+` (six planar surfaces, middle ground, same
  desaturation/Complement limits as RT). **Hybrid Rendering** (for transparency inside the FG when a
  subject color is close to screen color — splits internal Body/Edge keys and combines; workflow: key
  main area -> enable -> Clean FG Noise over the transparent area; tune **Hybrid Blur**/**Erode**).
  **Adjust Lighting** (generates an artificial even-lit clean plate after backing-color detection; tune
  **Lighting Threshold** while viewing Lighting Background mode). **Crop** (built-in rectangular garbage
  matte, no resize). **Reset** (full) / **Soft Reset** (only params since last Select Background Color).
- **Fine Tuning tab**: sample a color region, then **Spill**/**Transparency**/**Detail** sliders — additive,
  finer-grained equivalents of the Spill(-)/Matte(-)/Detail(-) buttons (same directions as those buttons).
- **Replace tab — Replace Mode**: `Complement` (best quality/detail, can add noise on heavy spill) /
  `Image` (defocused Background or Replace input; good tone on high-contrast BG, can lose edge detail,
  breaks if FG/BG alignment later changes) / `Color` (solid swatch + RGB; handles severe spill, loses
  edge detail, single color may not match a high-contrast BG).
- **Degrain tab** (grainy plates whose noise removal roughens edges): **Grain Size** `None`/`Small`
  (dense grain)/`Medium`/`Large` (loose grain) — averages a region around the sample instead of
  cleaning pixel-by-pixel. **Grain Tolerance** (strengthens Clean Background Noise without touching
  edge).
- **Matte tab**: Filter/Blur/**Blur Inward** (blurs only toward subject center — avoids the halo a two-
  directional blur causes; cleans small dark screen-area noise without Clean Background Noise
  reintroducing it)/Contract-Expand/Gamma/Threshold/Restore Fringe/Invert Matte/Solid+Garbage
  Matte/Post-Multiply (keying sub-block).
- **How to Key with Primatte** (p.1324): (1) **Select Background Color** — drag over screen near
  subject; Box/Median viewer tools for area/median sampling; avoid shadows you want kept. (2) **Clean
  Background Noise** — View Mode=Black, viewer alpha view, drag through white/light-gray noise until
  clean (viewer Options > Gain/Gamma reveals hidden noise; not every pixel needs removing). (3)
  **Clean Foreground Noise** — same alpha view, drag through dark FG holes until white; disable Gain/
  Gamma after. (4) **Remove Spill** — View Mode=Composite, RGB view; Spill Sponge for a fast pass,
  then Fine Tuning tab's Spill slider (or Spill(-)) for the remainder; Detail slider recovers thin smoke/hair,
  Transparency thins opaque smoke.

### Relight [RLT] (p.1326)
Adds light sources by analyzing scene shapes into a **Surface Map** (per-pixel normal estimate) and
reflecting light off it — illusion of following surface curvature, no true 3D shadow-casting/depth output.
Useful for an extra light, matching another shot, or day-for-night grades. Full detail lives in Resolve FX
Refine (DaVinci Resolve manual); control names only here.
- Inputs: `Input` (orange), `Effect Mask` (blue), `Normals` (green, optional external normal map).
- Structure needed: MediaIn -> ColorCorrector (any effect) -> Merge FG; MediaIn -> Relight -> Merge's
  blue effect-mask input; MediaIn -> Merge BG — Relight itself supplies only the light mask, not the grade.
- Controls: **Surface Map** (`Use Internal`/`Use Normals Input`). **Output Surface Map** (emit a
  multicolor normal map for a second Relight node). **Directional/Point Source/Spotlight** type.
  **Relighting Map Preview** (checked = alpha shows light effect; unchecked = light mask baked into
  alpha). Light Properties: **Brightness** (amplifies grading, adds none itself), **Reach** (dimming w/
  distance), **Contrast**. Surface Properties: **Glossiness**, **Specularity**, **Shadow Softness**.
  Directional-only: **Azimuth/Elevation XY**. Spotlight-only: **Beam Angle**, **Edge Softness**. Point/
  Spotlight: **Light Position** (set via viewer drag). External Map: **Rescale Oversaturated**,
  **Reinterpret Left/Right**, **Reinterpret Up/Down**.

### Ultra Keyer [UKY] (p.1330)
Two built-in keying systems (pre-matte garbage-matte-style + color-difference fine key), Delta-Keyer-
like. Manual's order: Delta Keyer first, Primatte second, Ultra Keyer third.
- Inputs: `Input` (orange), `Garbage Matte` (gray), `Solid Matte` (white), `Effect Mask` (blue).
- Pre-Matte tab: **Background Color** (sample near subject). **Red/Green/Blue Level** (whichever two
  non-key channels apply, tunes difference-channel separation). **Background Correction** (re-merges
  pre-keyed image over blue/green BG for subtler edges). **Matte Separation** (pre-process to separate
  FG/BG — raise while viewing alpha until just before it cuts holes/erodes fine edges). **Pre-Matte
  Range** (R/G/B/Luminance, auto from eyedropper). **Lock Color Picking**. **Pre Matte Size** (softens
  around key, closes spill-holes; can add a halo, fixable via Matte Contract). **Reset Pre Matte Ranges**.
- Image tab: Spill Suppression/Method/Fringe Gamma/Size/Shape/CMY (keying sub-block — main spill
  location).
- Matte tab: Filter/Blur/Clipping Mode/Contract-Expand/Gamma/Threshold/Restore Fringe/Invert Matte/
  Solid+Garbage Matte/Post-Multiply (keying sub-block), plus **Subtract Background** (CC's edges when
  screen color is anti-aliased to black; on = can darken edges, off = passes screen color through).

---

## Metadata Nodes (Ch.51, p.1340-1347)

### Copy Metadata [Meta] (p.1341)
Merges/replaces/clears metadata between two images (viewable in a viewer subview).
- Inputs: `Background` (orange, primary/output), `Foreground` (green, metadata source).
- **Operation**: `Merge (Replace Duplicates)` (dup keys taken from FG) / `Merge (Preserve
  Duplicates)` (dup keys taken from BG) / `Replace` (FG wholly replaces BG's) / `Clear` (discard all).

### Set Metadata [SMeta] (p.1342)
Creates new Name=Value pairs. Input: `Background` (orange) only. Controls: **Field Name** (no
spaces), **Field Value**.

### Set Timecode [TCMeta] (p.1344)
Inserts dynamic timecode from FPS settings; implemented as an editable Fuse (Lua).
- Input: `Background` (orange) only.
- Controls: **FPS** buttons (24/25/30/48/50/60 by default, editable in the Fuse source — see Scripting).
  **Hours/Minutes/Seconds/Frames** sliders (offset from comp start). **Print to Console** (verbose
  `TimeCode: HH:MM:SS:FF` / `Frames: N`, computed per FPS setting).

### Common Metadata controls
Settings tab: Use Object/Use Material + Correct Edges + Object/Material ID sliders (Matte-common
semantics), Comments, Scripts.

---

