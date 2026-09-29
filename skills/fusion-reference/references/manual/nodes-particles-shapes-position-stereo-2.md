<!-- nodes-particles-shapes-position-stereo.md part 2 of 2; index: nodes-particles-shapes-position-stereo.md -->
## Shape Nodes

This is Fusion's procedural vector-shape system — the direct analog of After Effects' shape layers, and central to Fusion motion graphics. Nearly every node entry below repeats: **"you can only view [this node]'s results through an sRender node"** — treat that as universal (except sRender itself).

### sBoolean
Combines/excludes overlapping areas of two shapes via boolean logic. Compare to sMerge (Union-only, layered compositing, no cutouts) — use sBoolean when you need Intersection/Subtract/Xor.
- Inputs: **Input1** [orange, required] — base shape (used as the base for Subtract). **Input2** [green, optional] — cutter shape (used to cut Input1 under Subtract). Which shape connects to which input is irrelevant **except** for Subtract.
- Key controls — **Operation** menu: **Intersection** (AND — only overlap survives), **Union** (OR — either shape; visually similar to sMerge's result), **Subtract** (NOT — Input1 minus Input2), **Xor** (AND NOT — (Input1−Input2) + (Input2−Input1)) (p. 1499).
- **Style Mode**: only one option, **Replace** — replaces incoming shapes' color/alpha with the color set in this node's own Style tab (p. 1500).
- Style tab: **Color** (RGBA). **Allow Combining** — first full explanation of this control (recurs on every shape node with a Style tab): ON preserves a shape's set alpha value even when it later overlaps a copy of itself downstream (e.g. via sDuplicate/sGrid); OFF lets alpha compound/increase at each overlap. **On sBoolean specifically, this checkbox overrides and the individual upstream shape nodes' own checkboxes are ignored** (p. 1500-1501).

### sBSpline [sBSp]
Identical to sPolygon except it uses B-Splines instead of Bézier splines: a B-Spline control point only *influences/pulls* the curve rather than lying directly on it, so far fewer points are needed for a smooth shape.
- Auto-animates: adding the node creates a keyframe at the current frame; moving to a new frame and editing the shape creates a new keyframe and interpolates between them (p. 1501-1502).

### sChangeStyle [sCS]
Overrides style (color + Allow Combining) for an entire upstream combined shape tree feeding it — a single override point rather than editing each generator.
- Inputs: single input (the shape tree to restyle).
- Key controls: **Color** (RGBA), **Allow Combining** (same semantics as sBoolean's) (p. 1502-1504).

### sDuplicate
Creates offset copies of the input shape — Fusion's core "repeater" for procedural patterns. Usually fed a compound shape from sMerge/sBoolean.
- Inputs: **Input1** [orange, required].
- Key controls — Controls tab: **Copies** (count **not including** the original — 5 = 5 copies + original = 6 total). **Copy Probability** (chance any given duplicate actually appears). **Time Offset** (offsets each copy's inherited animation by N frames per copy — e.g. −1.0 with a Y-rotating source means each successive copy shows the animation one frame earlier than the one before; useful for showing successive frames of a clip across a set of textured planes). **X and Y Offset** (distance between copies, normalized coords: 0.5 = half frame width right per copy, −1.0 = full frame width left). **X and Y Size** (scale offset relative to the **previous** copy, not the original: 1.0 = identical chain, 0.5 = each half the size of the one before it). **Axis Mode**: **Absolute** (fixed X/Y Pivot, offset+copied with each duplicate) / **Origin Relative** (each copy pivots on its own center) / **Origin Absolute** (each copy pivots on the *original* shape's center) / **Progressive** (compounds each copy's transform cumulatively from the previous copy's position/rotation/scale). **X and Y Pivot** (visible only in Absolute mode). **Rotation** (offset rotation per copy, calculated cumulatively from the previous copy — to rotate ALL copies identically instead, use the shape's own Angle parameter or an sTransform node). **Style** (color picker for the duplicates) (p. 1505-1506).
- Jitter tab: **Random Seed/Reseed**, **Center X and Y** (position variance), **Pivot X and Y** (rotational-pivot variance — affects only jitter rotation, not the Controls-tab Rotation), **Size** (scale variance, Lock Size checkbox), **Angle** (Z-rotation variance dial), **Gain RGBA** (randomizes channel values), **Blur** (randomizes blur between copies) (p. 1506-1507).

### sEllipse
Circle/ellipse generator; no inputs.
- Key controls: **Solid** (fill vs outline via Border Width + transparent center). **Border Width**. **Cap Style** (Flat/Round/Square — visible only when Length < 1.0). **Position** (start point of the outline gap, shown only when Solid is off). **Length** (1.0 = closed; <1.0 = gap/opening — keyframe for write-on animation). **X/Y Offset** (normalized to frame width: 0.0 = centered, 0.5 = shape center at the right edge). **Width/Height** (equal = perfect circle). **Angle**. Style tab: **Color** (RGBA), **Allow Combining** (p. 1508-1510).

### sExpand
Dilates or erodes shapes (vector equivalent of Erode/Dilate, but geometry-based, not pixel-based). Input is usually a compound shape but can be a single generator (sStar, sNGon).
- Inputs: **Input1** [orange, required].
- Key controls: **Amount** (positive dilates, negative erodes). **Border Style**: Bevel (squares off), Round, Miter, Miter Clip (last two hold points until a threshold). **Miter Limit** (Miter/Miter Clip only — determines when pointed edges bevel, based on shape thickness) (p. 1511).

### sGrid
Replicates the input shape on an X/Y grid with row/column offset. Input usually a single or compound shape.
- Inputs: **Input1** [orange, required].
- Key controls: **Grid Cells X and Y** (e.g. 5×5 = 5 rows, 5 columns). **X and Y Offset** (distance between rows/cols — 0.0 stacks everything on top of itself; 1.0 spreads columns the full frame width) (p. 1512-1513).

### sJitter
Randomizes position/size/rotation of a shape array (typically fed from sGrid or sDuplicate); also has an auto-animating random mode usable on single shapes for distortion/wobble.
- Inputs: **Input1** [orange, required].
- Key controls: **Jitter Mode**: **Fixed** (default — static offsets you keyframe/modify manually) vs **Random** (auto-animates within the range-slider bounds; if all range sliders sit at default, no animation occurs). **Shape X and Y Offset** (per-shape random position offset — not uniform across the array). **Shape X and Y Size** (per-shape random scale; left range value shrinks, right grows). **Shape Rotate**. **Point Jitter X and Y** — distorts the underlying **vector control points themselves** (distinct from whole-shape offset/size/rotate) — gives a distressed/wobbly look, e.g. to ellipse outlines (p. 1513-1514).

### sMerge
Combines 2+ shapes, like a standard Merge node but N-ary (unlimited inputs).
- Inputs: dynamically adds a new input each time the last one is filled — always at least one free input available. Layering order: first (orange) input is bottom-most; each subsequent input layers progressively on top.
- Key controls: **Override Axis** checkbox only — overrides the combined shape's axis (p. 1515-1516).

### sNGon
Multi-sided polygon generator (triangle, pentagon, octagon, etc.); no inputs.
- Key controls: **Solid**, **Border Width**, **Border Style** (Bevel/Round/Miter — only 3 options, no Miter Clip, unlike sExpand), **Cap Style**, **Position**, **Length**, **X/Y Offset**, **Width/Height** (equal = regular polygon), **Angle**. Style tab: **Color**, **Allow Combining** (p. 1517-1519).

### sOutline
Creates a **uniform** outline from a merged/boolean compound shape while individual shapes retain their own style/color/size/position — only thickness/border style/position/length are applied uniformly across the whole compound. Also usable on a single shape for a double-outline effect.
- Inputs: **Input1** [orange, required] — typically a compound shape from sMerge/sBoolean.
- Key controls: **Thickness**, **Border Style** (Bevel/Round/Miter), **Cap Style**, **Position** (start point, works with Length to place a gap), **Length** (1.0 = closed; <1.0 = gap; keyframe for write-on) (p. 1519-1521).

### sPolygon [sPly]
Freeform custom vector-shape drawing tool via click-based point manipulation (Bézier: point + 2 handles). "A valuable tool in motion graphics design" per the manual (p. 1521).
- Inputs: none (generator).
- Key controls: **Solid**, **Border Width**, **Border Style** (Bevel/Round/Miter), **Cap Style**, **Position**, **Length**, **X/Y Offset**, **Z Offset [3D]**, **Size** (scales the shape *without* affecting relative point behavior or setting an animation keyframe — distinct from moving points), **X/Y/Z Rotation**, **Fill Method [3D]**: Alternate vs **Non Zero Winding** — switch away from Alternate if overlapping polyline segments create undesired holes. Style tab: **Color**, **Allow Combining** (p. 1522-1524).
- Point-adding workflow: node starts in **Click Append** mode; click in the viewer to place each point; click the first point again to close the shape, which auto-switches the mode to **Insert and Modify**; switch to **Done** manually to lock the shape against accidental edits (p. 1524).
- Toolbar modes (shared with sBSpline): **Click** (default Bézier append), **Draw** (freehand; can extend an existing open spline from its last point), **Insert and Modify**, **Modify Only** (move/smooth without adding points), **Done** (locks points; whole spline can still move/rotate), **Close**, **Smooth** (linear→smooth on selected point), **Linear** (smooth→linear), **Select All**, **Show Key Points**, **Show All Handles**, **Shape Box** (reshape rectangle for group deformation), **Delete Points**, **Reduce Points** (opens a Freehand precision window to cut point count — useful after using Draw) (p. 1524-1525).

### sRectangle
Rectangle/square generator; no inputs. **Key node for rounded-corner motion graphics.**
- Key controls: **Solid**, **Border Width**, **Border Style** (Bevel/Round/Miter), **Cap Style**, **Position**, **Length**, **X/Y Offset**, **Width/Height** (equal = square), **Corner Radius** (0.0 = sharp corners; 1.0 = a circle from a starting square, or a pill shape from a rectangle), **Angle**. Style tab: **Color**, **Allow Combining** (p. 1526-1528).

### sRender
Converts the vector shape chain into a rasterized bitmap image for compositing with the rest of the comp. Always the terminal node of a shape branch; the only viewable node in the chain.
- Inputs: **Input1** [orange, required] (final shape-node output). **Effect Mask** [blue, optional].
- Key controls — Image tab: **Process Mode**, **Width/Height**, **Pixel Aspect** (right-click for frame-format presets), **Auto Resolution** (locks to comp Frame Format prefs; disable to build the comp at a resolution different from the final target), **Depth** (8-bit/32-bit/Float), **Source Color Space** (Auto/Space), **Source Gamma Space** (Auto/Space/Log), **Remove Curve** (p. 1528-1531).

### sStar
Multi-point star generator; no inputs.
- Key controls: **Points** (# arms). **Depth** (inner radius/arm width — 0.001 = hair-thin arms, 1.0 = a faceted circle). **Solid**, **Border Width**, **Border Style** (Bevel/Round/Miter), **Cap Style**, **Position**, **Length**, **X/Y Offset**, **Width/Height** (equal = symmetric arms), **Angle**. Style tab: **Color**, **Allow Combining** (p. 1531-1534).

### sText [sTxt]
"Shape" version of the 2D Text+ node — advanced character generator with multi-style, 3D transforms, multi-layer shading, controls near-identical to Text+.
- Gotcha: **does not support gradient colors**, unlike the 2D Text+ node (p. 1534-1535).

### sTransform
Adds a **second, independent** set of transform controls downstream of a shape's own built-in transform — the mechanism for hierarchical/parented shape animation (e.g., a star's own Angle control spins it in place; feeding that into sTransform's Rotation then orbits the spinning star around the frame — two independent motions stacked).
- Inputs: **Input1** [orange, required].
- Key controls: **X/Y Offset** (normalized, same convention as generators), **X and Y Size** (unequal values skew the shape), **Rotation** (dial, about the pivot), **X and Y Pivot** (visible in viewer as a draggable red X), **Transform Axis** checkbox (also apply the transform to the shape's axis) (p. 1535-1537).

### Shape Common Controls (Settings tab)
Documented once here. Most of these controls are explicitly marked **"(sRender only)"** in the manual — i.e. present in the Settings tab UI on every shape node, but only functionally meaningful on sRender: Blend, Process When Blend Is 0.0, RGBA channel selector, Apply Mask Inverted, Multiply By Mask, Motion Blur group (Motion Blur/Quality/Shutter Angle/Center Bias/Sample Spread), Use GPU (Disable/Enabled/Auto). **Hide Incoming Connections, Comments, and Scripts apply generally** across all shape nodes (p. 1537-1538).

---

## Stereo Nodes

Available **only in Fusion Studio and DaVinci Resolve Studio** (not free Resolve) (p. 1539). Brief coverage; all nine nodes share a Settings tab (Blend, Process When Blend Is 0.0, RGBA selector, Apply Mask Inverted, Multiply by Mask, Use Object/Material + Correct Edges + ID sliders, Hide Incoming Connections, Comments, Scripts — this slice's Common Controls excerpt does not list Motion Blur/Use GPU for this family, unlike Particle/Position/Shape, p. 1569-1571).

### Anaglyph [ANA]
Combines separate L/R eye images into one color-encoded stereo image (typically the terminal node). Inputs: Left (orange), Right (green), Effect Mask (blue); **Horiz Stack**/**Vert Stack** checkboxes let one pre-stacked image feed just the orange input. **Color Type**: Red/Cyan (most common), Red/Green, Red/Blue, Amber/Blue, Green/Magenta. **Method**: Monochrome (luminance per eye) / Half-Color (left=luminance, right=matching color channels) / Color (both eyes matched color channels) / **Optimized** (corrects the ~2× red/cyan brightness mismatch that causes retinal rivalry — blends left image's green+blue at 1.05×/0.45× weights into the red output channel; red itself unused from either eye) / **Dubois** (uses actual glasses+CRT-phosphor spectral data, reduces both rivalry and ghosting; red/cyan-specific). Swap Eyes (p. 1540-1544).

### Combiner [Com]
Builds one stacked image (side-by-side/top-bottom) from two eye images — e.g. to bake EXRs instead of computing disparity live. Inputs: Image 1 (orange, left), Image 2 (green, right). **Combine**: None / Horiz (doubles width, left on left) / Vert (doubles height, left on bottom) / Layers (renameable layer fields). Swap Eyes, Add Metadata (view via viewer SubView > Metadata) (p. 1544-1546).

### Disparity [Dis]
Computes L/R pixel shift into a Disparity aux channel (left stores L→R, right stores R→L); two outputs (Left/Right). Best practice, stated explicitly: color-match L/R first (matching is color/gradient-based); crop black borders (confuses tracking); pre-align large vertical offsets with a Transform node first; consider SmoothMotion on the result to reduce flicker; decide about lens distortion up front (otherwise disparity = combined disparity+distortion, and later vertical alignment strips distortion unintentionally); tune Proxy + Iteration Count first for speed; does not support RoI or DoD (p. 1546-1547). Key controls: **Proxy for Tracking** (downscale/upscale; proxy 2≈4× speedup, proxy 3≈9×; also a simple noise low-pass — very grainy footage may not benefit from 1:1). Advanced (defaults rarely need changing): **Smoothness** (higher=denoise/lower=detail), **Edges** (lower=smoother/overshoots; higher=tighter edge alignment but leaks color detail — use higher for Z/DoF derivation, lower for interpolation), **Match Weight** (typical 0.7-0.9; lower=match large structural features, higher=match small sharp variation, helps local lighting diffs e.g. mirror rig), **Mismatch Penalty** (Quadratic↔Linear; lower=strong penalty on dissimilarity→noisier; higher=more robust→smoother), **Warp Count**/**Iteration Count** (both linear compute cost; default high enough to always converge), **Filtering** (Catmull-Rom=better quality, steep cost increase), **Stack Mode** (Separate exposes Right in/out) (p. 1547-1549).

### Disparity To Z [D2Z]
3D camera + disparity image → new Z channel (DoF/fog). Math gotcha: Z accuracy degrades severely at large negative Z since disparity approaches a constant as Z→−∞ (e.g. Z=−1000/−10000/−100000 → D≈142.4563/142.4712/142.4713 — only 0.0001 of D separates 10,000 from 100,000 in Z) (p. 1549-1550). Inputs: Left (orange), Right (green, Separate only), Stereo Camera (magenta); two outputs. Controls: **Output Z to RGB** ({z,z,z,1}, promotes float32), **Refine Z** Enable (aligns depth edges to RGB edges; trade-off = RGB texture leaking into Z), **HiQ Only**, **Strength**, **Radius**, Stack Mode, Swap Eyes (p. 1551). Camera tab: **External** (real stereo camera or tracked L/R pair, physically correct) vs **Artistic** (no camera; **Foreground/Background Disparity** [pick from Left Eye; out-of-range values clip to flat Z] + **Foreground/Background Depth** + **Falloff**: **Hyperbolic** [default, depth=constant/disparity, physically accurate] vs **Linear** [depth=constant×disparity, artistic only] — use Hyperbolic unless there's a reason not to). Tip: for physically-based artistic control, connect a dummy Camera 3D to the Camera input instead (p. 1552-1553).

### Global Align [GA]
Fast non-optical-flow manual X/Y/rotation alignment, used early (before Disparity) to fix major L/R discrepancies + initial color match, improving Disparity's accuracy. Inputs: Left (orange), Right (green, Separate only); two outputs. Controls: Translation **Balance** (None/Left Only/Right Only/**Split Both** [opposite directions]), **Snap to Nearest Pixel**; Rotation **Balance** (same 4, Split Both = e.g. −5°/+5° for a 10° total, not −10°/+10°), **Angle**; **Translation Filter Method**; **Visualization** (color-codes L/R for review without a temp Anaglyph/Combiner — set None for final); Stack Mode, Swap Eyes (p. 1554-1555).

### New Eye [NE]
Interpolates a new view between an existing L/R pair using their disparity channels; can fully replace one eye with a warped version of the other. Destroys/consumes the disparity aux channel — re-run Disparity after if needed downstream; in Stack Mode L/R outputs are identical (p. 1556-1557). Inputs: Left (orange), Right (green, Separate only); two outputs. Per-eye controls (identical set L/R): **Enable** (activates reconstruction for that eye), **Lock XY** (unlocked = independent X/Y factors, e.g. X=1.0/Y=−1.0 = right eye horizontally, left-aligned vertically), **XY Interpolation Factor** (−1.0=pure Left, 1.0=pure Right, 0.0=halfway), **Depth Ordering** (Largest/Smallest Disparity On Top), **Clamp Edges** (fixes small edge gaps but causes stretch artifacts with motion), **Softness** (~0.01 with multiple Source Frame/Warp boxes checked, ~0.03 with one), **Source Frame and Warp Direction** checkboxes (up to 4 combinable: Left/Right Forward = L→R disparity, Left/Right Backward = R→L disparity; both eyes fills edge gaps, both Forward+Backward can double-image on disagreement) (p. 1557-1558).

### Splitter [Spl]
Inverse of Combiner — one stacked image → separate L/R. Input: Left (orange, stacked); two outputs. Controls: **Split** (None/Horiz [half width each]/Vert [half height each]), Swap Eyes (p. 1559-1560).

### Stereo Align [SA]
Most versatile stereo fixer — vertical alignment + convergence + eye separation in one resampling pass. Modifies RGBA only; changing eye separation can create unfillable holes; destroys the disparity aux channel like New Eye (p. 1560-1561). Inputs: Left (orange), Right (green, Separate only); two outputs. **Vertical Alignment**: Apply to (Right/Left/**Both**=50-50 split; convention: Left is the pure reference, align Right to it), Mode (**Global**=simple Y-shift vs **Per Pixel**=disparity-warped, can artifact); caution: vertical alignment removes each eye's own lens-distortion Y-component — remove lens distortion before Disparity instead; **Y-shift** (Global only; Sample picks from Left's disparity channel — can't sample while viewing this node's own output), Snap to Whole Pixels. **Convergence Point** (global X-translation): Apply to (Left/Right/**Split**=50-50), X-shift (Sample from disparity), Snap. **Eye Separation**: Separation scale factor (0.0=unchanged, 0.1=+10% shift) — its **Both** option applies **100%-100%** to each eye, unlike Vertical Alignment's 50-50 Split (an explicit UI asymmetry); enable per-pixel vertical alignment when changing this or interpolation can double up. **Left/Right Eye Options**: Depth Ordering, Clamp Edges, Edge Softness (same ~0.01/0.03 guidance as New Eye), Source Frame and Warp Direction (same 4-checkbox scheme). Stack Mode (L/R identical); nearest-neighbor sampling unless High Quality render is enabled. Swap Eyes (p. 1562-1565).

### Z To Disparity [Z2D]
Inverse of Disparity To Z: stereo camera + Z channel → disparity channels; more accurate than Disparity's optical-flow estimate for CG-rendered sources (p. 1565). Inputs: Left (orange), Right (green, Separate only), Stereo Camera (magenta); two outputs. Controls: **Output Disparity To RGB** ({x,y,0,1}, float32), **Refine Disparity** (same edge/texture trade-off as Disparity To Z), Strength, Radius, Stack Mode, Swap Eyes (p. 1566-1567). Camera tab: **External** (real/matching stereo camera, physically correct) vs **Artistic** (no camera; **Convergence Point** [Z value of the zero-disparity plane = negative of Camera 3D's Convergence Distance] + **Background Disparity** [sampled from Left Eye; right eye = same magnitude, negated]) (p. 1567-1568).

---

## Gotchas and non-obvious behavior

1. Particles are stateful across frames — scrubbing without Pre-Roll gives wrong results; nothing retroactively simulates skipped frames (p. 1449-1450).
2. `pImage Emitter` Create Particles Every Frame is OFF by default — animating emitter controls does **nothing** until it's enabled (p. 1443).
3. `pImage Emitter` Alpha Threshold defaults to 0.0 — invisible particles are still generated for transparent pixels, a hidden render-time cost; set ~0.004 (1/255) (p. 1443).
4. `pChangeStyle` must sit **upstream** of the event node (e.g. pBounce) it's meant to visually react to, sharing its region — downstream placement means the style never changes (p. 1420).
5. `pSpawn` Affect Spawned Particles can blow up particle count exponentially without tight Age/Probability/Set/Region limiters (p. 1456).
6. 3D-mode particle Motion Blur also needs matching settings on the **downstream Renderer 3D**, not just pRender (p. 1454).
7. `sBoolean`/`sChangeStyle` Allow Combining on the compound node overrides upstream shapes' own checkboxes (p. 1500, 1503).
8. `sDuplicate` X/Y Size and Rotation are relative to the *previous copy*, not the original — both compound geometrically across copies; use the source shape's own Angle (or an sTransform) to rotate every copy identically.
9. `sPolygon`/`sBSpline` Size scales without keyframing or disturbing point-relative behavior — unlike dragging points, which does keyframe.
10. `sText` does not support gradient colors, unlike the 2D Text+ node it otherwise mirrors (p. 1534-1535).
11. Stereo Nodes need Fusion Studio or Resolve Studio; External Matte Saver/Resolve Connect needs standalone Fusion Studio — neither works in free Resolve (p. 1491, 1539).
12. `New Eye` and `Stereo Align` both destroy the disparity aux channel while interpolating — re-run Disparity after either if it's needed downstream (p. 1556, 1560).
13. `Stereo Align` Eye Separation "Both" applies 100%-100% to each eye, while its Vertical Alignment/Convergence "Both"/"Split" apply a 50-50 split — not the same semantics (p. 1554-1555, 1563-1564).
14. `Disparity To Z`/`Z To Disparity` depth math degrades severely at large negative Z — not a bug, a property of the disparity-depth relationship (p. 1549-1550).
15. Volume Fog/Volume Mask require **World-Space** WPP; Eye Space or Object Space renders won't interpret correctly (p. 1487).
16. `pEmitter`'s default Region is **Sphere (3D)**, not All — common source of "why aren't there particles at the frame edges" confusion (p. 1468).
17. `Disparity`'s Y-shift/X-shift Sample buttons (used inside Stereo Align) can't be used while viewing that same node's own output (p. 1562-1563).

---

## Recipes / workflows

**1. Demonstrate why Pre-Roll matters (from the manual's own walkthrough, p. 1449-1450):**
1. Add a `pEmitter` and a `pRender`; view the pRender.
2. Set particle **Velocity** to 0.1; position the pEmitter at the left edge of frame.
3. Set Current Frame to 0; set Render Range 0-100; press Play and observe normal behavior.
4. Stop, return to frame 0. In pRender, **disable Automatic Pre-Roll**.
5. Jump the current-time field directly to frame 10, then 60, then 90 — notice the particle system only adds to particles already created; it does not simulate the frames you skipped.
6. Click **Pre-Roll** in pRender — the system recalculates from range start to current frame and the display becomes correct.
   Takeaway: leave Automatic Pre-Roll ON for small/fast systems; for slow/long-range systems, pre-roll manually as needed.

**2. Firework trail-and-burst using pSpawn (p. 1455):**
1. Build a base emitter (`pEmitter`) with upward Velocity and a short Lifespan for the initial "rocket" particle(s).
2. Add `pSpawn` downstream; in its Conditions tab, set **Start Age** near the end of the parent's life (e.g. Start=0.8) so children only spawn as the trail particle nears death.
3. Tune **Velocity Transfer** below 1.0 so burst children don't simply continue the parent's trajectory in a straight line.
4. Keep **Affect Spawned Particles** off unless you deliberately want cascading generations (fireworks-of-fireworks) — otherwise particle count/render time can explode.

**3. Rounded-rectangle motion graphic (procedural pill/rounded-rect, p. 1526-1528):**
1. Add `sRectangle`; set Width/Height for the base rect proportions.
2. Raise **Corner Radius** from 0.0 toward 1.0 — at 1.0 a square becomes a circle, a rectangle becomes a pill shape.
3. Feed into `sRender` to view.

**4. Star-cutout-from-ellipse using sBoolean (p. 1498-1500):**
1. Add `sEllipse` (or any base shape) → Input1 (orange) of `sBoolean`.
2. Add `sStar` → Input2 (green) of `sBoolean`.
3. Set **Operation = Subtract** — output is the ellipse with the star's shape cut out of it. (Which input the star/ellipse land on matters for Subtract specifically — Input1 is the base, Input2 is the cutter.)
4. Feed into `sRender`.

**5. Duplicated-grid pattern with per-copy variation (sDuplicate + Jitter, p. 1504-1507):**
1. Build a base shape (e.g. `sEllipse` → `sMerge`/`sBoolean` if compound).
2. Feed into `sDuplicate`; set **Copies** to the desired repeat count, and **X/Y Offset** for spacing (normalized to frame width).
3. For organic variation, switch to the **Jitter** tab and raise **Center X/Y** (position), **Size**, and/or **Angle** — each duplicate gets independent randomized variation seeded by **Random Seed** (use **Reseed** for a new pattern with identical settings).
4. Feed into `sRender`.

**6. Basic Volume Fog setup (p. 1474):**
1. Render/obtain a 3D scene with a **World Position Pass** (WPP) in its XYZ Position channels (e.g. via a Renderer 3D with World Position enabled in output channels).
2. Connect that WPP-carrying image to `Volume Fog`'s orange **Image** input.
3. Connect a `Fast Noise` node (small resolution, e.g. 256×256) to the green **Fog Image** input.
4. Connect the 3D scene (containing the camera) to the magenta **Scene** input.
5. Use the Shape tab's **Pick** tool to position/scale the fog volume relative to the WPP data; adjust Color-tab **Z Slices**/**Samples**/**Gain** for density and detail.

**7. Multi-matte delivery to Resolve Color page (External Matte Saver, p. 1492-1493):**
1. Place `External Matte Saver` at the end of one matte-producing branch (e.g. a Delta Keyer output) — connects to the default single orange input.
2. Click **Add** in the Inspector for each additional matte source; connect each new colored input to its own upstream node.
3. In the Mattes tab, set **Channels Name** per input to a meaningful label (this name surfaces in Resolve's Color page).
4. In the Controls tab, set **Filename** ending in `.exr` and **Browse** to a destination.

---

## Scripting and automation hooks

This slice is UI/Inspector-focused; it does not include Lua/Python `comp.AddTool` / `SetInput` examples. The concrete, verbatim scripting-relevant surface it does provide:

- **Node abbreviations** (usable in the Select Tool dialog and in scripting references), as stated in this slice's Contents pages:
  Particle: `pAv` (pAvoid), `pBn` (pBounce), `pCS` (pChangeStyle), `pCu` (pCustom), `pCF` (pCustomForce), `pDF` (pDirectionalForce), `pEm` (pEmitter), `pFl` (pFlock), `pFo` (pFollow), `pFr` (pFriction), `pGF` (pGradientForce), `pIE` (pImage Emitter), `pKI` (pKill), `pMg` (pMerge), `pPF` (pPoint Force), `pRn` (pRender), `pSp` (pSpawn), `pTF` (pTangent Force), `pTr` (pTurbulence), `pVt` (pVortex).
  Position: `VLF` (Volume Fog), `VLM` (Volume Mask), `Z2W` (Z to World Pos).
  Resolve Connect: `EMS` (External Matte Saver).
  Shape: `sBSp` (sBSpline), `sCS` (sChangeStyle), `sPly` (sPolygon), `sTxt` (sText). (sBoolean, sDuplicate, sEllipse, sExpand, sGrid, sJitter, sMerge, sNGon, sOutline, sRectangle, sRender, sStar, sTransform have no bracketed abbreviation given in this slice.)
  Stereo: `ANA` (Anaglyph), `Com` (Combiner), `Dis` (Disparity), `D2Z` (Disparity To Z), `GA` (Global Align), `NE` (New Eye), `Spl` (Splitter), `SA` (Stereo Align), `Z2D` (Z To Disparity).

- **pCustom / pCustomForce expression variables** (usable in Setup/Intermediate/Channels/Particle tab expressions):
  - Numeric inputs: `n1..n8` (current time) and `n1_at(float t)`, `n2_at(float t)`, `n3_at(float t)`, `n4_at(float t)` (arbitrary time).
  - Setup results: `s1, s2, s3, s4` (evaluated once/frame, before everything else).
  - Intermediate results: `i1, i2, i3, i4, i5, i6, i7, i8` (evaluated once/frame, after Setup).
  - Particle state: `px, py, pz`, `vx, vy, vz`, `rx, ry, rz`, `sx, sy, sz`, `pxi1, pyi1`, `pxi2, pyi2`, `mass` (unused by anything), `size`, `id`, `r, g, b, a`, `rgnhit`, `rgndist`, `condscale`, `rgnix, rgniy, rgniz`, `rgnnx, rgnny, rgnnz`, `w1, h1`, `w2, h2`, `time`, `age`, `lifespan`.
  - Position inputs: `p1x, p1y, p1z .. p4x, p4y, p4z`.
  - Pixel-read functions (per the Custom node's shared function set): `getr1w(x,y)`, `getz2b(x,y)`, and the same family for other channel/image-input combinations.

- **File-path/registry references**: Brushes directory is configured in **Preferences > Path Maps**; default is the `Brushes` subdirectory inside Fusion's install folder (p. 1462-1463, 1748 note in Style tab section). External Matte Saver output requires an explicit `.exr` extension typed into its **Filename** field (p. 1493).

- **Right-click affordances relevant to automation/pipeline work**: right-click a shape's animated points/gradient control and choose **Animate** to key the whole control as one spline (e.g. Color Over Life); right-click Width/Height/Pixel Aspect fields (pRender, sRender) to pick a Frame Format preset by name; right-click the polyline "Shape animation" label (Bézier region mode) to connect it to another polyline.
