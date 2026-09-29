<!-- nodes-particles-shapes-position-stereo.md part 1 of 2; index: nodes-particles-shapes-position-stereo.md -->
# Fusion Node Reference: Particle, Position, Resolve Connect, Shape, and Stereo Nodes

Scope: Fusion Page Effects manual, Chapters 55-59 (pp. 1415-1571): Particle Nodes, Position Nodes, Resolve Connect, Shape Nodes, Stereo Nodes.
Use when: building or troubleshooting a particle simulation, a WPP-driven volumetric fog/mask, a multi-matte EXR export to Resolve Color, a procedural vector-shape motion-graphics rig (sRender chain), or a stereoscopic 3D pipeline (Fusion Studio / Resolve Studio only).

## Mental model

1. **Particle chains always end in `pRender`.** Sources are only `pEmitter`/`pImage Emitter`; every other p-node is a modifier (particle-in, particle-out on the orange input) and is not viewable — only pRender renders. (p. 1416, 1429)
2. **Shape chains always end in `sRender`.** Generators (sEllipse, sRectangle, sNGon, sStar, sPolygon, sBSpline, sText) have no inputs; every other s-node modifies a shape stream; only sRender rasterizes to a viewable bitmap. (p. 1507, 1528)
3. **Input colors are contextual, not fixed** — "the color of the input is determined by whichever is selected first in the menu." Region/Style menu choices (Bitmap vs Mesh, etc.) change which color a port gets; always check the node's own Inputs list.
4. **Particles are stateful across frames** — position depends on the prior frame's state, so scrubbing past frames without Pre-Roll gives wrong results (intervening generations/motion are never simulated). The single most consequential particle gotcha (p. 1449-1450; see Recipes).
5. **Region tab (7 modes: All, Bézier, Bitmap, Cube, Line, Mesh, Rectangle, Sphere) is shared verbatim across almost every particle node** — restricts where an effect applies, or (pEmitter) where particles are born. (p. 1467-1470)
6. **Sets (1-32) are the particle filtering mechanism** — assigned at birth/change by pEmitter, pImage Emitter, pChangeStyle, pSpawn; any other node's Conditions tab can target "Affect Specified Sets"/"Ignore Specified Sets." (p. 1433, 1466)
7. **Allow Combining governs alpha at self-overlap, set per compound node, not summed upstream** — ON preserves original alpha through downstream overlaps (e.g. sDuplicate/sGrid); OFF compounds alpha at overlaps. On sBoolean/sChangeStyle the node's own checkbox overrides upstream shapes' checkboxes. (p. 1500-1501, 1503-1504)
8. **pChangeStyle order is counter-intuitive**: to make a style change look caused by a downstream event (e.g. a bounce), place pChangeStyle *before* that event node, sharing its region. (p. 1420)
9. **WPP (World Position Pass) is the Position-node substrate** — each pixel's 3D XYZ encoded as RGB, must be 32-bit float, and must be **World Space** (not Eye/Object Space). (p. 1486-1487)
10. **Stereo Nodes need Fusion Studio or Resolve Studio** (not free Resolve); Resolve Connect (External Matte Saver) needs standalone Fusion Studio only. (p. 1491, 1539)
11. **New Eye and Stereo Align destroy the disparity aux channel** as a side effect of interpolating — re-run Disparity afterward if it's needed downstream. (p. 1556, 1560)
12. **Shape X/Y Offset is normalized to frame width** (0.0 = centered, 0.5 = shape center at the right edge) — consistent across sEllipse, sRectangle, sNGon, sStar, sPolygon, sDuplicate, sGrid.

---

## Particle Nodes

### Shared plumbing (read first)
- Every particle node's orange input accepts **only** the output of another particle node (i.e., you cannot feed a 2D image into the main particle chain — only into the secondary Style/Image/Region inputs that some nodes expose).
- A green/magenta bitmap-or-mesh **Region** input appears on a node only once you set that node's Region-tab **Region** menu to **Bitmap** or **Mesh**; the color assigned depends on which node port claimed it first.
- The four tabs **Conditions, Style, Region, Settings** are common across nearly all particle nodes; see "Particle Common Controls" below — each node entry below only lists what's unique to it.

### pEmitter [pEm]
The primary particle source; almost every particle system's first node. Use over pImage Emitter unless you specifically want one particle per input pixel in a fixed 2D grid.
- Inputs: none by default. Style Bitmap input appears if Style tab menu = Bitmap. Region (bitmap or mesh) inputs appear per Region tab.
- Key controls (Controls tab):
  - **Number** — particles created per frame. Animate down to 0 after your desired count to cap the total (e.g., 5/frame for frames 0–4, then 0 from frame 5) (p. 1430).
  - **Number Variance** — e.g. Number=10, Variance=2 → 9–11/frame; if Variance > 2× Number, some frames may emit zero (p. 1430).
  - **Lifespan** (default 100 frames) / **Lifespan Variance** — many other controls (Size Over Life, Color Over Life, etc.) are keyed to % of Lifespan (p. 1431).
  - **Color**: Use Style Color (default, from Style tab) vs **Use Color From Region** (overrides Style, samples underlying bitmap region color; renders **white** if the region isn't a bitmap) (p. 1431).
  - **Position Variance** — 0 (default) restricts birth strictly to region edge; >0 lets particles be born outside the boundary, "softening" the edge (p. 1431).
  - **Temporal Distribution**: At The Same Time (default, frame-boundary births) / Randomly Distributed (sub-frame random) / Evenly Distributed (sub-frame regular spacing) — influenced by pRender's **Sub Frame Calculation Accuracy** (p. 1431).
  - Velocity: **Velocity/Velocity Variance** (10.0 = crosses full image width in one frame; 1.0 = crosses over 10 frames), **Inherit** (Inherit Velocity: negative = opposite direction, 1 = matches emitter region velocity, 2 = moves ahead of region), **Angle/Angle Variance**, **Angle Z/Angle Z Variance** (p. 1431-1432).
  - Rotation: **Rotation Mode** = Absolute Rotation vs Rotation Relative To Motion; **Rotation XYZ/Variance** (p. 1432).
  - Spin: **Spin XYZ/Spin Variance** — auto-animated, degrees applied per frame (p. 1432).
  - **Sets tab**: Set 1–32 checkboxes; assigns particles to sets for later selective targeting (p. 1433).
- Modes/options: Region tab sets emitter shape (7 modes, see Common Controls). If pRender is 2D, region emits along a flat Z plane; if 3D, region can be volumetric.
- Gotchas: default Region is **Sphere (3D)** for a new pEmitter (p. 1468).

### pImage Emitter [pIE]
Emits one particle per input-image pixel on a fixed 2D grid, colored from that image — versus pEmitter's random-in-region births. Use for turning footage/stills into particle fields (video-on-particles, dissolve/disintegration effects).
- Inputs: orange = the **source image** (not a particle stream — the sole exception among particle nodes) and doubles as color source if a region is defined; Style Bitmap input; teal/white Region input.
- Key controls (unique vs pEmitter): **X and Y Density** (1.0 = 1 sample/pixel; <1 = sparser/pointillistic; >1 = multiple particles per pixel) (p. 1442). **Alpha Threshold** (default 0.0 = particle for every pixel regardless of alpha, hardens soft edges as raised; 1/255 = 0.004 is recommended to eliminate fully transparent pixels) (p. 1442-1443). **Lock Particle Color to Initial Frame** (keep birth color for life vs track the changing input image → enables "video playback on a grid of particles") (p. 1442). **Create Particles Every Frame** — OFF by default, meaning only ONE set of particles is ever created (on the first frame); animating any other emitter control has **no effect** unless this is enabled (p. 1443). **X/Y/Z Pivot** (positions the grid). **Use Z Channel for Particle Z** (uses image's Z-depth channel for initial particle Z — hollow-shell effect with camera rotation in pRender) (p. 1443).
- Gotchas: fully transparent (black-alpha) pixels still generate **invisible** particles unless Alpha Threshold is raised above 0.0 — "can slow down rendering significantly" (p. 1443). The grid is fixed-size on the XY plane centered at Pivot; to resize it, add a Transform 3D **after** pRender, not before (p. 1443).

### pRender [pRn]
Converts the particle stream to an image (2D) or geometry (3D, default). The only viewable node in a particle branch; always the terminal node.
- Inputs: orange particle input; optional green **Camera** (frames the render, works even in 2D via a virtual viewpoint); optional blue **Effect Mask** (2D only — crops output to mask shape).
- Key controls:
  - **Output Mode**: 3D (default) vs 2D buttons, or switch via viewer's View > 2D Viewer if not hard-connected to a 2D/3D-only node (p. 1448).
  - **In 3D mode, only these controls have any effect at all**: Restart, Pre-Roll/Automatic Pre-Roll, Sub-Frame Calculation Accuracy, Pre-Generate Frames. Everything else on this node is 2D-render-only (p. 1449).
  - **Restart** — clears all particles and restarts the system fresh at the current frame (works in 3D too) (p. 1449).
  - **Pre-Roll** — recalculates particle *positions only* (not the rendered image) from render-range start up to the current frame; shown in viewer as point-style particles during the calculation (works in 3D too) (p. 1449).
  - **Automatic Pre-Roll** — auto pre-rolls on every frame change (no progress shown); recommended ON for simple/fast systems, OFF (manual Pre-Roll only) for slow/long-range systems (p. 1450).
  - **Only Render in Hi-Q** — overrides style to fast Point particles when the comp's Hi-Q checkbox is off; useful for large counts of slow Image/Blob particles during interactive work (p. 1450).
  - **View** menu (2D-mode camera position: Scene/Perspective default, or ortho Front/Top/Side) — ignored if a Camera 3D is connected to pRender's Camera input, or if pRender is in 3D mode. Onscreen controls of upstream particle nodes are drawn as front-ortho in 2D mode regardless of View setting (p. 1450).
  - Conditions (2D only): **Blur, Glow, Blur Blend** — same result as adding a Blur node after pRender (p. 1450).
  - **Sub-Frame Calculation Accuracy** — # sub-samples between frames; higher = more accurate + slower (p. 1450).
  - **Pre-Generate Frames** — pre-generates N frames before frame 1, e.g. so chimney smoke is already present at the start rather than just starting to emerge (p. 1450).
  - **Kill Particles That Leave the View** — speeds render; destroyed particles never return regardless of forces (p. 1451).
  - **Generate Z Buffer** — outputs a Z Buffer aux channel for downstream Depth Blur/Depth Fog/Z Merge; "likely to increase render times dramatically" (p. 1451).
  - **Depth Merge Particles** — merges via Depth Merge technique instead of layer order (p. 1451).
  - Scene tab: **Z Clip** — clipping plane in front of camera so particles crossing it don't dominate/impact the lens (p. 1451).
  - Grid tab (2D only, non-rendering guide; width/depth/#lines/color; not animatable) (p. 1452).
  - Image tab: Process Mode, Use Frame Format Settings, Width/Height, Pixel Aspect (right-click for frame-format presets), **Depth** (8-bit/32-bit/Float), Source Color Space (Auto/Space), Source Gamma Space (Auto/Space/Log), Remove Curve (p. 1452-1454).
- Gotchas: 3D-mode particle **Motion Blur also requires identical motion-blur settings on the downstream Renderer 3D node** — setting it only on pRender is not sufficient (p. 1454). See Recipes for the full Pre-Roll demonstration.

### pAvoid [pAv]
Creates a region particles try to steer away from (not a hard wall). Compare to pBounce (hard collision response) and pKill (destroys on contact) for stronger alternatives.
- Inputs: orange particle; Region (green/magenta bitmap or mesh).
- Key controls: **Distance** — how far from the region a particle must be before it starts moving away. **Strength** — how strongly it moves away; negative values attract toward the region instead (p. 1417-1418).
- Gotchas: this is a "desire," not a constraint — if particle velocity/momentum is stronger than the combined distance+strength, the particle crosses the region anyway (p. 1416).

### pBounce [pBn]
Hard-collision response: particles bounce off a defined region.
- Key controls: **Elasticity** (0.0–1.0 UI range, unbounded manually; 1.0 = same velocity after bounce, 0.1 = loses 90% velocity; >1.0 gains momentum; negative accepted but not useful). **Variance** — randomizes reflection angle (rougher-surface look). **Spin** — imparts spin on impact based on collision angle (+forward/−backward). **Roughness** — randomizes bounce direction slightly. **Surface Motion** / **Surface Motion Direction** (thumbwheel) — makes the bounce surface behave as if it were itself moving, at a set angle (p. 1419-1420).

### pChangeStyle [pCS]
Changes a particle's appearance (Set/Style) on contact with a region — mirrors the pEmitter Style tab. One of only two particle nodes that affects appearance rather than motion (the other is pCustom).
- Key controls: **Change Sets** (reassign the particle's Set), **Style** (reassign look) (p. 1421).
- Gotchas: **must be placed upstream of** the node whose event you want the style change to appear to respond to (e.g., before pBounce), using the same region reference — placing it downstream means the particle never intersects the pChangeStyle region in time and the style never changes (p. 1420).

### pCustom [pCu]
Custom per-particle expressions (position/velocity/rotation/etc.) — the particle-domain analog of the Custom node.
- Inputs: orange particle; green/magenta **Image 1 / Image 2** (2D, for per-pixel calc/compositing); teal/white Region.
- Key controls / expression surface:
  - **Numbers 1-8**: dial-animatable variables; usable in expressions as `n1..n8` (current time) or `n1_at(float t)..n4_at(float t)` (arbitrary time) (p. 1423).
  - **Position 1-8**: 3D X/Y/Z point controls, animatable/connectable, exposed to Setup/Intermediate/Channels tab expressions (p. 1424).
  - **Setup 1-8**: up to 8 expressions evaluated once per frame *before* anything else; results available as `s1..s4` (p. 1424).
  - **Inter 1-8**: up to 8 expressions evaluated once per frame *after* Setup; results available as `i1..i8` (p. 1425).
  - Full **Particle** variable list exposed to expressions: `px, py, pz` (position), `vx, vy, vz` (velocity), `rx, ry, rz` (rotation), `sx, sy, sz` (spin), `pxi1, pyi1` (2D position corrected for Image 1 aspect), `pxi2, pyi2` (for Image 2), `mass` (not currently used by anything), `size`, `id`, `r, g, b, a`, `rgnhit` (1 if particle hit the region), `rgndist` (distance from region), `condscale` (region strength at particle position), `rgnix, rgniy, rgniz` (where on region it hit), `rgnnx, rgnny, rgnnz` (region surface normal at hit), `w1, h1` / `w2, h2` (image 1/2 dimensions), `i1..i4` (Intermediate results), `s1..s4` (Setup results), `n1..n8` (Number inputs), `p1x, p1y, p1z .. p4x, p4y, p4z` (Position inputs 1–4), `time`, `age`, `lifespan` (p. 1425).
  - Pixel-read functions for the two image inputs, e.g. `getr1w(x,y)`, `getz2b(x,y)` — same operator/function/conditional set as the Custom node (p. 1423).
- Gotchas: keep small/square style-bitmap images (e.g. 256×256) since they get duplicated across potentially thousands of particles (shared guidance across style-bitmap nodes).

### pCustomForce [pCF]
Like pCustom but modifies **forces** (position XYZ and Torque/spin) via custom equations instead of style — "one of the most complex and most powerful" particle nodes, aimed at users comfortable with scripting/C++ concepts.
- Inputs/tabs are structurally identical to pCustom (three inputs: particle, Image1/2, Region; same Numbers/Position/Setup/Inter tab layout) — refer to pCustom for the full variable/expression list (p. 1426-1427).

### pDirectionalForce [pDF]
Unidirectional pull — the standard way to simulate gravity.
- Key controls: **Strength** (+/− direction), **Direction** (X/Y angle), **Direction Z**.
- Defaults: direction is -90° (down the Y axis), and the node **ignores regions and affects all particles by default** — i.e., you must explicitly set up a region if you want to restrict it (p. 1427-1428).

### pFlock [pFl]
Simulates organic/herd/flock behavior via two competing "desires": stay close to peers, and keep minimum spacing.
- Key controls: **Flock Number** (how many other particles a given particle tries to follow — higher = more visible clumping/larger groups). **Follow Strength** (higher = more committed following; lower = more likely to break away). **Attract Strength** (pull toward the pack once farther than Maximum Space). **Repel Strength** (push away once closer than Minimum Space). **Minimum/Maximum Space** (range control; smaller range = organized motion, larger range = chaotic/disorganized) (p. 1435-1436).
- Recipe hint: combine with pFollow for natural swarming that also changes direction (p. 1434, 1436).

### pFollow [pFo]
Springs particles toward a follow object that can be positioned/animated in 3D — creates a new motion path.
- Key controls: **Position XYZ** (positions/animates the follow object — animating it creates the path). **Spring** (back-and-forth spring motion; higher = more elastic). **Dampen** (attenuates spring; lower = less resistance to the oscillation) (p. 1437).

### pFriction [pFr]
Slows particles crossing a region. Produces two independent friction effects.
- Key controls: **Velocity Friction** (slows linear motion), **Spin Friction** (slows rotation/spin) — larger value = more friction in each case (p. 1439).

### pGradientForce [pGF]
Accelerates particles along an image's alpha gradient (white→black / high→low by default) — e.g. simulating flow downhill or along a shape's contour.
- Inputs: orange particle; green image (must have an **alpha channel gradient** — e.g. a Fast Noise node); Region.
- Key controls: **Strength** — single control; negative reverses direction to black→white (p. 1440).

### pKill [pKI]
Destroys particles that cross/intersect its region. No unique controls at all — only the shared Conditions and Region tabs govern who dies (age/set/probability/region) (p. 1444-1445).

### pMerge [pMg]
Combines two particle streams into one for all downstream nodes. No controls whatsoever.
- Inputs: two identical particle inputs (orange, green) — no Region/Style/Conditions tabs (p. 1445).
- Gotchas: sets assigned at particle birth are preserved through the merge, so downstream nodes can still isolate particles from either original stream by Set (p. 1445).

### pPoint Force [pPF]
Attracts or repels particles from a single 3D point.
- Key controls: **Strength** (+attract/−repel). **Power** (falloff sharpness with distance; 0 = no falloff, higher = sharper falloff). **Limit Force** — counters temporal sub-sampling overshoot: because particle position is sampled once per frame (absent extra sub-sampling in pRender), a particle can overshoot the force point and get flung in the wrong direction; raising this reduces that risk. **X, Y, Z Center Position** (p. 1447).

### pSpawn [pSp]
Makes each affected particle act as its own emitter, producing independent child particles with their own lifespan/properties while the parent continues unaffected.
- Key controls: most duplicate pEmitter's controls. Unique: **Affect Spawned Particles** — if enabled, spawned children are themselves affected by pSpawn on later frames, which can **exponentially** increase particle count and render time; "Use this checkbox cautiously" (p. 1456). **Velocity Transfer** — default 1.0 = child inherits 100% of parent's velocity/direction; lower = less inherited motion (p. 1456).
- Recipe hint: use Start/End Age in the Conditions tab to spawn new particles only as old ones near death — classic rocket-trail-into-fireworks-burst technique (p. 1455).

### pTangent Force [pTF]
Applies force perpendicular to the vector between the node's region/point and the particle — makes particles curve around/orbit rather than move directly toward/away.
- Key controls: **X, Y, Z Center Position** and independent **X, Y, Z Center Strength** per axis (p. 1457).

### pTurbulence [pTr]
Frequency-based chaotic motion — "natural" randomized jitter to otherwise-rigid particle flow.
- Key controls: **X, Y, Z Strength**. **Strength Over Life** — mini spline graph keying turbulence to particle age (e.g. fire starts calm, gets more turbulent with age). **Density** — lower = broad "waves" moving groups of particles together; higher = finer per-particle variation/spread (p. 1458-1459).

### pVortex [pVt]
Rotational pull-toward-source force — spiraling motion.
- Key controls: **Strength**, **Power** (falloff with distance), **X, Y, Z Offset** (positions the vortex relative to affected particles), **Size**, **Angle X and Y** (rotational force magnitude along those axes) (p. 1459-1461).

### Particle Common Controls (Style / Conditions / Region / Settings tabs)

**Style tab** — present only on pEmitter, pSpawn, pChangeStyle, pImage Emitter. **Style menu** (particle look type):
| Style | Notes |
|---|---|
| Point | 1 px, no size controls at all. Apply Mode (2D only): Add (sums overlapping color) / Merge (standard over). Sub Pixel Rendered checkbox: smoother motion, blurrier, slower (p. 1461, 1470). |
| Bitmap | Style Bitmap orange input (keep small/square, e.g. 256×256, for performance/quality). Animate Over Time: **Over Time** (all particles share the current global frame of the movie, changing in lockstep) / **Particle Age** (each particle's own age indexes into the movie from frame 1) / **Particle Birth Time** (particle locks to the movie frame matching its own birth frame, held for its whole life). Time Offset (slip start frame). Time Scale (multiplier, e.g. 2× → comp frame 2 shows movie frame 4). Gain (pixel multiplier, e.g. 0.5×1.2=0.6; black pixels unaffected) (p. 1462, 1470-1471). |
| Blob | Large soft spherical particles. Noise (2D only) — Perlin-style texture, 0=none, 1=max (p. 1462). |
| Brush | Images from the Brushes directory (Preferences > Path Maps; default is Fusion's own Brushes subfolder — empty folder = only "None" option, no particles render). Gain (same formula as Bitmap). Use Aspect From: Image Format / Frame Format / Custom (p. 1462-1463). |
| Line | Straight-line particles with optional falloff. Fade (default 1.0 = full fade by line end). Pairs well with **Size to Velocity** (p. 1463, 1471). |
| Point Cluster | Small clusters of 1-px particles — more efficient at scale than Point. Number of Points / Variance controls cluster density (p. 1463). |

Color Controls: **Color Variance** (per-channel range, e.g. Red −0.2/+0.2 = 40% total variance around base color). **Lock Color Variance** (locked = uniform variance across channels; unlocked = independent per-channel variance → broader color range). **Color Over Life** (gradient: left stop = birth color, right stop = death color; multi-stop supported; animate the gradient itself via right-click > Animate, controlled by a single spline that sets the speed of the shift; **From Image** modifier available to derive the gradient from an image's colors along a line between two points) (p. 1463-1464, 1471-1472).

Size Controls: Point style has **no** size controls. Bitmap style: 1.0 = same size as source bitmap, 2.0 = 200% — keep the source bitmap as large as the largest particle for quality. Point Cluster: size = cluster density/tightness. **Size to Velocity** — adds `velocity × control value` to size (e.g. control 1.0 + velocity 0.1 → +0.1 size); most useful with Line style. **Size Z Scale** — perspective exaggeration; default 1.0 = realistic (Z=0 focal plane = actual size, farther = smaller, closer = larger); 0.0 cancels perspective, 2.0 exaggerates it. **Size Over Life** — spline, vertical axis = 0–200% of the Size control, horizontal = 0–100% of lifespan (p. 1464-1465).

Fade Controls: Fade In / Fade Out as a % of lifespan (e.g. Fade In 0.1 on a 100-frame particle fades in over frames 0–10) (p. 1465).

Merge Controls (no effect on 3D particles): Subtractive/Additive slider (as in the standard Merge node); Burn-In (overexposure/blow-out at overlaps) (p. 1465).

Blur Controls (no effect on 3D particles): **Blur (2D)/Blur Variance (2D)** — applied per-particle *before* merging (unlike pRender's Blur, which is post-merge). **Blur Over Life** spline. **Z Blur (DoF) (2D)** + **DoF Focus** range — particles inside the focus range stay sharp; outside get Z Blur applied; lower Z values = closer to camera (p. 1465-1466).

**Conditions tab** (all particle nodes): **Probability** (0.0–1.0, re-rolled per particle per frame — 0.6 = 60% chance any given particle is affected that frame). **Start/End Age** (range control, % of lifespan — e.g. Start=0.8/End=1.0 limits the effect to the last 20% of life). **Set Mode Menu**: Ignore Sets (applies to all) / Affect Specified Sets / Ignore Specified Sets. **Set #** checkboxes — target particles by the Set assigned at birth (only pEmitter, pImage Emitter, pChangeStyle, pSpawn assign Sets) (p. 1466-1467).

**Region tab** (all particle nodes; on pEmitter/pImage Emitter this defines the *emitter* region). **Region Mode Menu** (7 types):
| Mode | Behavior |
|---|---|
| All | 2D: anywhere in image bounds. 3D: a 1.0×1.0×1.0 cube. |
| Bézier | User polyline; works 2D+3D, but the polyline itself can only be drawn in 2D. Animate via right-click "Shape animation" label. |
| Bitmap | Uses another node's bitmap as the birth/effect region. |
| Cube | Full 3D cube; H/W/D and XYZ position all animatable. |
| Line | Two endpoints (connectable to Paths/Trackers); XYZ start/end controls. |
| Mesh | Any 3D mesh; restrictable by Object ID slider (Limit By ObjectID checkbox). Has its own Region Type (interior volume vs surface) and Winding Rule/Winding Ray Direction controls to handle non-closed/"leaky" imported meshes (ray cast to ±infinity, tally crossings into a winding number; e.g. Winding Rule = Odd keeps only odd-winding-number interior points). |
| Rectangle | Like Cube but no Z depth; unlike other 2D regions, can be positioned/rotated in Z space. |
| Sphere | 3D, Size + Center Z controls. **Default region for a new pEmitter.** |
(p. 1467-1470)

**Settings tab** (all particle nodes) = Fusion's standard common-controls family, documented once here: **Blend** (0.0 = pass input through unchanged, tool typically skips processing) / **Process When Blend Is 0.0** (force processing anyway, e.g. for scripted side effects) / **Red/Green/Blue/Alpha channel selector** (limits the effect to specific channels, applied post-process) / **Apply Mask Inverted** / **Multiply by Mask** / **Use Object/Use Material** checkboxes + **Correct Edges** + **Object ID/Material ID** sliders (EXR Object/Material ID channel masking) / **Motion Blur** group (Motion Blur toggle, Quality, Shutter Angle, Center Bias, Sample Spread) / **Use GPU** (Disable/Enabled/Auto) / **Hide Incoming Connections** / **Comments** / **Scripts** (3 scripting fields). This exact family recurs verbatim on Position, Shape (sRender-only in that chapter), and Stereo nodes — not repeated per-node below.

---

## Position Nodes

Brief coverage — WPP (World Position Pass) volumetrics. All three nodes share a **Settings tab** identical to the Particle Common Controls Settings tab above.

### Volume Fog [VLF]
Volumetric fog from images carrying XYZ Position (WPP) channels; runs on 2D images so is much faster/more interactive than true 3D-rendered volumetrics.
- Inputs: **Image** (orange, must carry a WPP), **Fog Image** (green, 2D texture e.g. small Fast Noise at 256×256), **Effect Mask** (blue), **Scene** (magenta, 3D scene/camera).
- Shape tab: **Shape** (Sphere/Rectangle), **Pick** (drag into viewer to sample XYZ — 2D picks need 32-bit float), X/Y/Z Offset, Rotation Pick, X/Y/Z Rotation, X/Y/Z Scale, **Size**, **Soft Edge**.
- Color tab: **Adaptive Samples > Dither**, **Samples** (raytrace-like eval count), **Z Slices** (# Fog Image frames for volume depth — rule of thumb 256×256px @ 256 slices ≈ 256MB float data), **First Slice Time**, **Color**, **Gain**, **Subtractive/Additive**, **Fog Only** (black-bg output for compositing/masking).
- Noise tab: Detail, Gain, Brightness, Translation, Noise Rotation, **Seethe** (animate for crawling/drifting), Discontinuous, Inverted.
- Light tab (needs real lights+camera in Scene): **Do Lighting**, **Do In-Scattering**, **Light Samples**, **Density** (thickness via transmission vs Scattering which exits light early), **Scattering**, **Asymmetry** (0=isotropic; >0=forward scattering like water droplets in cloud; <0=back scattering), **Transmission** (color multiplier), **Reflection** (multiplies with volume texture color — red texture × blue Reflection = black), **Emission** (glow; Transmission>1 = unphysical glow trick) (p. 1474-1480).
- Gotcha ("Invisible Sphere"): an empty scene background defaults WPP to 0/0/0, so fog incorrectly fills that void — add an invisible bounding sphere for dummy WPP values (p. 1487).

### Volume Mask [VLM]
Volumetric masks from WPP images — isolates 3D objects for color correction **without tracking or rotoscoping**. Inputs: Image (orange, WPP), Mask Image (green, refines mask), Effect Mask (blue). Shape tab mirrors Volume Fog's. Color tab: Color, Subtractive/Additive, **Mask Only** (black-bg output for a Color Corrector mask). Camera tab: Camera menu, Translation Pick, X/Y/Z Offset (p. 1481-1484).

### Z to World Pos [Z2W]
Converts a Z-depth + 3D Camera ↔ a World Position Pass, either direction — builds a WPP when the 3D app can't, or when tracking software outputs per-pixel Z + camera (enables Volume Mask/Fog on real-world tracked footage). Inputs: Image (orange, WPP or Z-depth per Mode), Effect Mask (blue), Scene (magenta, needs a 3D Camera). Controls: **Mode** (Z↔WPP direction), **Camera** (select among multiple) (p. 1485-1486).

### WPP Concept (reference, no controls)
A WPP encodes each pixel's 3D XYZ position as an RGB color (0/0/0 → black; 1/0/0 → pure red); must be **32-bit float**. Renders can be World, Eye, or Object Space — **Fusion's Position nodes require World Space**. Scene input can be a bare camera or scene-with-camera; Z to World Pos requires one, Volume Mask/Fog can run without (or with camera at 0/0/0), but accuracy improves when the connected camera matches the WPP's original render camera (p. 1486-1487).

---

## Resolve Connect

Chapter contains a single node, **available only in standalone Fusion Studio** (not DaVinci Resolve). (p. 1491)

### External Matte Saver [EMS]
Renders multiple mattes into multiple channels of one EXR file for efficient multi-matte delivery into DaVinci Resolve's Color page — replaces the manual workflow of a Channel Boolean + Saver + per-channel naming.
- Inputs: starts with a single orange 2D-image input; the Inspector's **Add** button appends further inputs, each a new color, all accepting 2D RGBA.
- Key controls — Controls tab: **Filename** (must append `.exr` manually), **Browse**.
- Mattes tab: **Channels** menu (Alpha / RGB / RGBA per matte), **Channels Name** (custom name shown in Resolve's Color page), **Node Name** (auto-populated from the connected source), **Add** (adds another input + field set).
- Settings tab: same common-controls family as above (Blend, Process When Blend Is 0.0, RGBA selector, Apply Mask Inverted, Multiply by Mask, Use Object/Material + Correct Edges + ID sliders, Motion Blur group, Hide Incoming Connections, Comments, Scripts). (p. 1492-1496)

---

