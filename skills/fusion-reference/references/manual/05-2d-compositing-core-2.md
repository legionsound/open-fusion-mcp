<!-- 05-2d-compositing-core.md part 2 of 2; index: 05-2d-compositing-core.md -->
## 10. Merge node (Mrg), complete
(Behavior from pp. 442, 445, 472-481; full control reference pp. 980-988.)

Combines FG over BG using the FG alpha. Operation modes are Porter-Duff; Apply modes are blend modes. Supports additive (premultiplied) and subtractive (straight) compositing and Z-depth compositing.

- **Inputs** (all optional, p. 980):
  - **Background** (orange): connect first. BG alone = Merge outputs BG. Sets output **resolution**, **bit depth**, and is the only source of **aux** channels.
  - **Foreground** (green): FG alone without BG = **no output**.
  - **Effect Mask** (blue): merge happens where mask is white; BG shows alone where black.
- **Output channels**: RGB, or RGBA if both FG and BG have alpha (p. 442).
- **Layer order** = input wiring (FG on top) unless Perform Depth Merge is on (then per-pixel Z decides) (pp. 442, 980). **Swap FG/BG: Command-T / Ctrl-T** (p. 984).
- **Chaining**: timeline track 1 = BG of Merge1, track 2 = FG of Merge1; Merge1 output = BG of Merge2; track 3 = FG of Merge2. "No loss of quality or precomposing when you chain Merges together" (p. 483).
- **Auto-creation**: drag a Media Pool clip onto a connection line (Fusion page) or add a Loader with a Loader selected (Studio): new node becomes the FG of a new Merge. Drag a disconnected node's output onto another node's **output**: Merge created with the dragged node as FG (pp. 471-472). Text+ toolbar button with a node selected creates Text+ as FG of a new Merge (p. 475). Mask toolbar buttons (e.g. Rectangle) with a MediaIn selected attach the mask (p. 488).

### Merge tab: Foreground sizing (p. 982)
- **Center X/Y**: default 0.5, 0.5 (FG centered on BG). Displayed value = normalized position x Reference Size.
- **Size**: slider 0.0-5.0, any value > 0 can be typed. 1.0 = pixel-for-pixel with BG.
- **Angle**: rotates FG before combining.
- **Flip** controls also exist (p. 474 tip). All of these avoid a separate Transform node.

### Apply Mode (pp. 982-984)
Normal (default; FG alpha as mask; exposes Operator), Screen (alpha ignored, order irrelevant, always lighter; exposes Operator; good for reflections with lowered Blend, p. 474), Dissolve (average), Darken, Multiply (use for AO/shadow passes), Color Burn, Linear Burn, Darker Color (compares composite RGB), Lighten, Color Dodge, Linear Dodge (Add), Lighter Color, Overlay, Soft Light, Hard Light, Vivid Light, Linear Light, Pin Light, Difference, Exclusion, Hue, Saturation, Color, Luminosity, **Hypotenuse** `Out = sqrt(Fc*Fc + Bc*Bc)` and **Geometric** `Out = 2*Fc*Bc / (Fc+Bc)` (both recommended for HDR/over-1.0 values).

### Operator (Normal or Screen only) (pp. 984-985)
Formula is always `(fg * x) + (bg * y)`:

| Operator | x | y | Result |
|---|---|---|---|
| **Over** | 1 | 1 - FG alpha | Standard FG over BG |
| **In** | BG alpha | 0 | FG clipped to BG's matte; FG color only |
| **Held Out** | 1 - BG alpha | 0 | FG punched out by BG matte (same as In + inverted BG matte) |
| **Atop** | BG alpha | 1 - FG alpha | FG over BG only where BG has matte |
| **XOr** | 1 - BG alpha | 1 - FG alpha | Where either has matte, never both |
| Conjoint | manual: `X= 1, Y= X+Y(1-af)/ab, if af>ab` | | Decision-based alpha combine; for soft/motion-blurred non-solid alpha |
| Disjoint | manual: `X= X+Y(1-af)/ab, Y= X+Y if af+ab<1` | | Avoids out-of-range alpha; correct premult edge alpha |
| Mask | manual: `X = X * af, Y = 0` | | Outputs BG multiplied by FG alpha |
| Stencil | manual: `X = X * (1-af), Y = 0` | | Outputs BG multiplied by inverse FG alpha |
| Under | manual: `X = Y, Y = X *(1-af)` | | Over with FG/BG swapped |

(af = FG alpha, ab = BG alpha; the last five formulas are reproduced as printed, notation is loose.)

Under, In, Held In, Below are obtainable by swapping inputs (Cmd/Ctrl-T) and picking the mirror mode.

### Compositing adjustment sliders (pp. 473, 985-986)
- **Subtractive/Additive**: Normal Apply Mode only (hidden otherwise, because the math would be invalid). Default **Additive** = assumes premultiplied FG: BG multiplied by (1 - FG alpha), FG added. **Subtractive** = FG first multiplied by its own alpha (for straight FG). Intermediate values blend both to tune edges that are too bright or too dark.
- **Alpha Gain**: linearly scales FG alpha. Subtractive: acts like density/Blend. Additive: lowers BG obscuring (brightens). **Additive + Alpha Gain 0.0 = pure add** of FG onto BG (glows, light passes).
- **Burn In**: amount of alpha used to darken BG, without changing how much FG is added. 0.0 = straight alpha blend, 1.0 = FG added onto BG. In Additive, raising Burn In = lowering Alpha Gain.
- **Blend**: clone of Settings tab Blend; blends BG with the merged result.

### Additional controls (pp. 986-988)
- **Filter Method** (for resized FG, default **Linear**): Nearest Neighbor, Box, Linear, Quadratic, Cubic, Catmull-Rom (sharpens, good for downscaling detail), Gaussian, Mitchell, Lanczos, Sinc (sharp, may ring), Bessel. **Window Method** for Sinc/Bessel: Hanning, Hamming, Blackman, Kaiser.
- **Edges** (area outside a FG smaller than the BG-defined DoD): **Canvas** (canvas color/opacity; change via Set Canvas Color between FG source and FG input), **Wrap** (tiled video wall), **Duplicate** (smear edge pixels), **Mirror** (alternating flipped tiles).
- **Invert Transform**: inverts position/rotation/scale; for driving the Merge from a tracker in match moves.
- **Flatten Transform**: stops this Merge concatenating its transform with **downstream** nodes (it may still concatenate from its input).
- **Reference Size** (display only): **Use Frame Format Settings**, or **Width/Height**. With 100x100 set, Center shows 50,50 and 55,50 moves 5 px right. **Internally and via scripting the Center stays normalized 0-1.**
- **Channels tab**: **Perform Depth Merge** (off by default; uses both images' Z to order front/back, alpha still defines transparency; ignored if either lacks Z; can also use Z-Coverage and BG RGBA), **Foreground Z-Offset** (+ **Pick** from viewer Z; higher = FG farther), **Subtractive/Additive** for BG pixels that land in front via Z.

Related: **MultiMerge (MMrg)** combines many sources in a layer-based structure (p. 988+). **Dissolve (DX)** is the only node safe to wire FG first; it dissolves or switches between inputs of unequal duration (p. 437).

---

## 11. Masks and rotoscoping

### Mask node types (pp. 492-493)
| Node (abbr) | Notes |
|---|---|
| **Polygon (Ply)** | Bezier polyline; roto workhorse; on toolbar; auto-animates |
| **B-Spline (BSp)** | Tension/weight-controlled points without handles; smoother with fewer points; auto-animates |
| **Bitmap (Bmp)** | Mask from any image channel: color, alpha, hue, saturation, luminance, coverage aux, Object/Material ID |
| **Mask Paint (PNM)** | Vector paint as mask |
| **Wand (Wnd)** | Crosshair seed, contiguous similar-color region; good for isolating color adjustments |
| **Ellipse (Elp), Rectangle (Rec), Triangle (Tri)** | Primitives. Rectangle has **Corner Radius** 0.0 (sharp) to 1.0 (max). Triangle has no Center/Size/Angle; its 3 points attach to trackers/paths |
| **Ranges (RNG)** | Spline-based low/mid/high luminance selection (like Color Corrector ranges) |

Convert shape type: viewer right-click **Convert Bezier Spline to B-Spline** / **Convert B-Spline to Bezier**. Shape preserved, point count roughly doubles, animation preserved but review it (p. 494).

### Ways to use a mask
| Method | Wiring | Notes | Page |
|---|---|---|---|
| Effect mask | Mask > blue Effect Mask input of almost any node | Applied **post-effect** (node processes the whole image, mask copies unaffected input back). Defines DoD. **Not supported**: Savers, Time nodes, Resize, Scale, Crop | 498 |
| Roto via MatteControl | Image > MatteControl **Background**; Polygon/B-Spline > **Garbage Matte** input | View MatteControl, edit Polygon. **Garbage Matte > Invert** picks which side goes transparent | 434, 496 |
| Roto on source | Polygon > MediaIn/Loader effect input | Alpha added to that node. **Draw in a disconnected mask first**: an empty mask outputs full transparency and blanks the image | 441, 496 |
| Pre-mask | Node-specific input name | Used **before** the effect (faster, more realistic). Highlight/Glow: restrict source but let glow spread beyond mask. DVE: transform only a region | 499 |
| Garbage Matte | Gray input on keyers/MatteControl | Excludes rigs, stands, booms. Opaque vs transparent chosen in the receiving node | 499 |
| Solid Matte | White input | Fills matte holes ("hold-out matte"), e.g. a harder, eroded second DeltaKeyer into DeltaKeyer1's SolidMatte | 499-500 |
| Text as matte | Text+ > MatteControl Garbage Matte, image on BG | Garbage Matte controls can fill instead of cut | 478-480 |

Right-click a keyer's header in the Inspector to add a mask to its Effect Mask, SolidMatte, or GarbageMatte via submenus (p. 499). Masks or mattes (images) can generally feed any mask input (p. 497).

### Combining masks: Paint Mode (pp. 497, 1251)
Chain masks: a mask's own effect-mask input takes the previous mask; the **Paint Mode** menu appears once connected.

| Paint Mode | Result |
|---|---|
| **Merge** (default) | New mask merged with input |
| Add | Values added |
| Subtract | New subtracts from input where they intersect (cut holes) |
| Minimum / Maximum | Lowest / highest value (intersection / union) |
| Average | Half the sum |
| Multiply | Input x new |
| Replace | New replaces input where intersecting; zero areas of the new mask leave input untouched |
| Invert | Input inverted where covered by new mask (gray = partial) |
| Copy | Discard input, use new |
| Ignore | Discard new, use input |

**Invert checkbox** inverts the **entire** mask (all pixels), unlike Invert Paint Mode (only covered areas). **Solid** off = outline only, thickness = Border Width.

### Mask controls (Polygon; shared by most masks) (pp. 1250-1252, 1260-1261)
- **Show View Controls**: hides onscreen controls.
- **Level**: mask opacity; 1.0 opaque. Lowering it lowers all mask-channel pixels covered, including those from masks underneath.
- **Filter** (for Soft Edge): Box (fastest), Bartlett (pyramid), Multi-box (**Num Passes**; 1 = Box, 2 = Bartlett, 4+ approx. Gaussian without ringing), Gaussian (best, slower, possible slight ringing on float).
- **Soft Edge**: uniform feather; 0.0 = crisp.
- **Border Width**: grows/shrinks a solid mask; outline thickness when not Solid.
- **Paint Mode**, **Invert**, **Solid**: above.
- **Center X/Y**, **Size** (scales without changing point relationships and **without setting a shape keyframe**), **X, Y, Z Rotation**.
- **Fill Method**: **Alternate** vs **Non Zero Winding** (switch to fix holes from self-overlapping segments).
- **Right-Click Here for Shape Animation**: remove/re-add animation, publish, connect.
- **Image tab**: Output Size, Width/Height, Pixel Aspect, **Depth**, **Clipping Mode** (Frame/None). Settings tab: Motion Blur group, Use GPU, Comments, Scripts.

### Polyline editing: modes and keys (pp. 500-508)

| Action | Key / control |
|---|---|
| Click Append (default for new masks) | **Shift-C**; click to add, click first point to close (auto-switches to Insert and Modify) |
| Insert and Modify (default for motion paths) | **Shift-I** |
| Draw Append (freehand, tablet) | **Shift-D** |
| Modify Only (no new points; deletion still allowed) | **Shift-M** |
| Done (no add, no modify; whole shape can still move/rotate) | **Shift-N** |
| Close/open toggle | **Shift-O**, Close button, click first point, or right-click Polygon:Polyline > Closed |
| Constrain new points to 45 degrees | Hold **Shift** while drawing |
| Cycle active polyline | **Tab / Shift-Tab**; or right-click Controls > Select |
| Select points | Click, lasso; **Shift** = continuous range; **Command**-click toggle; **Command-A** all (**Shift-A** also cited for all points, p. 510) |
| Next/previous point | **Page Down / Page Up** |
| Move points | Drag; Shift-drag single axis; Option-drag anywhere; Arrow keys nudge, Command-Arrow smaller, Shift-Arrow larger |
| Smooth / Linear | **Shift-S** / **Shift-L** |
| Twist / scale / scale X / scale Y / offset perpendicular to tangent | Hold **T / S / X / Y / O** and drag (pointer position = pivot) |
| Delete points | Delete/Backspace (deleting all points does not delete the polyline; delete the node) |
| Break Bezier handle symmetry | **Command**-drag a handle (per adjustment) |
| Change handle length only | **Shift**-drag handle |
| Point Editor (exact X/Y, offsets, math) | **E**; click axis label for X-offset/Y-offset; Individual vs all radio; Next/Previous |
| Shape Box (scale/stretch/skew groups) | **Shift-B**; Command-drag = from center, proportional; Shift-drag corner = that corner only (skew) |
| Reduce Points | Toolbar/context menu; **100 = no reduction**, drag left to remove points |
| Show Key Points / Show Handles | Toolbar or context menu |
| Stop Rendering | Render only after points stop moving |
| Roto Assist | Snaps new points to nearest high-contrast edge (cyan outline). Options: **Multiple Points** (many points along an edge per click), **Distance** (pixel search range), **Reset** (clear snap; points then unavailable for tracking) |

Polyline toolbar buttons on Polygon/B-Spline (p. 1252): Click, Draw, Insert, Modify, Done, Closed, Smooth, Linear, Select All, Keys, Handles, Shape, Delete, Reduce, Publish menu, Follow Points, Double Poly. Right-click the toolbar to resize icons/add labels.

### Double polylines: non-uniform softness (pp. 509-510)
- Soft Edge feathers uniformly; for motion-blurred edges use a **double polyline**: **Double Polyline** button or right-click **Make Outer Polyline**.
- Inner = original shape; outer (green dashed) = falloff extent. Both start identical (sharp), existing animation kept.
- Outer points are **parented one-way** to inner points (dashed lines show pairs): editing inner moves outer; editing outer does not affect inner.
- Select outer: **Tab** until dashed outline shows, or right-click **Controls > Select > Polygon: Outer Polygon**. Quick start: **Shift-A**, then hold **O** and drag to offset all outer points.
- Points need not match 1:1; add points to either. Each polyline keeps its own animation; moving a parented inner point keys **both** splines; moving an outer point keys only the outer. Disable coupling: context menu **Polygon: Outer Polygon > Follow Inner Polyline**. **Lock Point Pairs** parents selected outer/inner points (animation preserved); deselect to unlock.

### Animating masks (pp. 511-512, 1249)
- Polygon/B-Spline add a keyframe at the current frame on creation. Move the playhead and reshape = new keyframe; shapes interpolate. **One keyframe holds all control points** for that frame.
- **Center and rotation are not auto-animated**; keyframe them explicitly in the Inspector.
- Retime by moving the shape keyframe in the Spline Editor or Timeline Editor.
- Adding a point inserts it at **all** keyframes; deleting removes it from all.
- Static mask: Inspector right-click **Right Click Here For Shape Animation > Remove Bezier Spline**; re-enable with **Animate**.
- **Publish Points** (toolbar or context menu): selected points leave the shape spline and get their own coordinate controls (**Point 0, Point 1...**), drawn larger in the viewer; they can then be connected to a tracker, path, expression, or modifier via right-click. Publishing **removes existing animation** from those points and disconnects them from paths/modifiers/expressions/trackers on the main spline.
- **Publish to Path**: publishes and converts existing animation to a path (keeps motion).
- **Follow Published Points**: in-between points (drawn as diamonds) keep their offset/shape relative to moving published points, and can still be animated for morphing.

### Tracking masks
- **Mask center to a tracker**: track the feature, then connect the mask's Center to the tracker's **Offset Position** via the control's context menu, e.g. `Center > Connect To > Tracker1 > Offset Position` (pp. 559-560). Other published tracker values: Steady Position, Unsteady Position, Steady Angle (needs 2+ patterns), Steady Size.
- **Tracker modifier on a mask**: right-click the mask Center > **Modify With > Tracker > Position**; then drag the clean source node (e.g. the Loader, not the Glow being masked) into the modifier's **Track Source** field before tracking (p. 1797).
- **Per-point tracking**: Publish Points, then connect each published point to a tracker; use Follow Published Points for the points in between (p. 512). Triangle mask points attach directly to trackers/paths (p. 1262).
- **Camera-move-proof masks**: **Volume Mask** uses World Position aux to place a mask in 3D space (p. 465).
- **Merge Invert Transform** for tracker-driven match moves (p. 987).

---

## 12. Layer-to-node workflow notes (Ch. 19)
- Clicking a node in the Effects Library inserts it after the selected node; dragging a library node onto an existing node **replaces** it (pp. 468, 470). Fusion Studio: press 1 or 2 to view the selected node.
- Sliders: a dot under a dragged slider marks the default and resets on click; typing a larger value than the slider max **expands the slider range** (e.g. Highlight Number of Points maxes at 24 on the slider) (p. 470). **Command**-drag gears down any Inspector control (p. 476).
- Dragging files from the OS into the Node Editor adds them to the current Media Pool bin (p. 472).
- Text+: six tabs; viewer toolbar text entry and **Manual Kerning** (Option-drag red dots under letters; clear kerning in Advanced Controls) (pp. 475-477).
- DeltaKeyer quick key (pp. 484-487): Shift-Space > add DeltaKeyer after the green-screen MediaIn; drag the Inspector **Eyedropper** over the screen; view the keyer's alpha (viewer **Color** button or **C**); tune **Gain** (more screen transparency, can hurt FG), **Balance** (tints FG toward the other two primaries); Matte tab (3rd of 7): lower/upper **Threshold** for density, **Clean Foreground** / **Clean Background** subtly (harsher edges as they rise). Mattes should be pure black/white except glass, smoke, fog.
- Spill: Matte tab **Replace Mode = Source** disables DeltaKeyer spill suppression; handle spill with a color node after the keyer, or branch the source to a color node and combine with MatteControl (p. 487).

---

## Gotchas and non-obvious behavior
1. Edit-page Zoom/Position/Crop/Stabilization/retime/Resolve FX are invisible in Fusion; only Lens Correction precedes it (p. 408).
2. Compound and Fusion clips conform members to timeline resolution: 4K sources become HD inside Fusion (p. 412).
3. Scale to Fit sends a 4K Fusion output back at timeline resolution (p. 410).
4. Merge output resolution, bit depth and aux all come from the **BG** input. A FG-only Merge outputs nothing; a BG-only Merge outputs BG (pp. 411, 415, 442, 980).
5. Merge's Subtractive/Additive slider disappears unless Apply Mode = Normal; Operator menu appears only for Normal or Screen (pp. 474, 984).
6. Bright edge fringe = straight FG in an additive Merge; dark halo = double premultiply (pp. 445-446, 472-473).
7. 16-bit **integer** truncates super-whites and sub-blacks; use float for log/RAW/HDR (p. 413).
8. Integer Interactive depth with float Final render can look significantly different (p. 414).
9. Out-of-range values look clipped in the viewer but are still there in float; check with Normalized Color Range (p. 416).
10. Stray alpha outside 0-1 breaks composites: clamp alpha only with Brightness Contrast Clip Black/White, or Change Depth to integer (p. 417).
11. Unmanaged by default: log footage composited without linearizing gives wrong blurs/merges (pp. 420-421). With RCM on, do NOT add CineonLog/Gamut; ACES "Process Node LUTs In" does not affect Fusion (pp. 426, 428).
12. Color Corrector and Gamut ignore alpha and aux; to force processing of other channels shuffle with Channel Booleans (single image on BG) (pp. 438, 440).
13. Channel Booleans (Bol, 2D) vs Channel Boolean (3Bol, 3D): different nodes (pp. 443, 923). Aux targets need **Enable Extra Channels** (p. 462).
14. Depth Blur's Z Scale default assumes 8-bit; lower it (about 0.2) for float Z (pp. 458, 464).
15. World Position must be 32-bit float (p. 463). Z-Depth often contains negative values (p. 459).
16. EXR is never downscaled by "Downscale Timeline Resolution" (p. 412).
17. Effect masks are post-effect and unsupported on Savers, Time nodes, Resize, Scale, Crop (p. 498).
18. A mask connected with no shape yet outputs full transparency and blanks the image (p. 496).
19. Mask Invert checkbox inverts everything; Invert Paint Mode inverts only covered areas (p. 1251). Mask Level also lowers underlying masks' pixels (p. 1250).
20. Polygon center/rotation are not auto-animated; Size does not set a shape keyframe (pp. 511, 1252).
21. Publishing points wipes their animation (use Publish to Path to keep it) and detaches them from the shape's trackers/modifiers (pp. 511-512).
22. Masking a graphic does not change its dimensions; crop it for accurate centering/match moves (p. 489).
23. Merge Center via scripting is always normalized 0-1, whatever Reference Size shows (p. 987).
24. RoI never affects renders; MediaOut/Saver write full frame (p. 213).
25. A Text3D (or any 3D node) cannot feed a Merge directly; render through Renderer 3D first (p. 436). Particles need pRender (p. 438).

## Recipes / workflows

**R1. Lock comp resolution** (p. 411): Background node at target size > Merge1 Background; plates as Foregrounds. Larger plates are cropped at output but remain repositionable via Merge Center/Size.

**R2. Linear workflow without RCM** (pp. 420-425): MediaIn > Gamut (Source Space = camera space, e.g. ITU-R BT.709 (scene); Remove Gamma on) or CineonLog (Log Type = camera; Mode = to linear), or MediaIn Source Gamma Space Curve Type Auto/Log/Space + Remove Curve. Comp. Before MediaOut: Gamut (Source Space = No Change; Output Space = sRGB or ITU-R BT.709 (scene); Add Gamma on). Viewer LUT = Gamut View LUT, Output Space Rec.709, Add Gamma; Settings > Save Defaults.

**R3. RCM** (p. 426): Project Settings > Color Management > Color Science = DaVinci YRGB Color Managed; Automatic color management on (or set Color Processing mode + Output Color Space); per-clip Input Color Space from Media Pool right-click. Fusion page then works linear with Managed viewer LUT.

**R4. Color-correct a premultiplied layer** (pp. 446-448): single node: enable **Pre-Divide/Post-Multiply** (Color Corrector: Options panel). Several nodes or OFX: Alpha Divide > corrections > Alpha Multiply > Merge FG.

**R5. Fix edge fringing** (pp. 472-473): select the Merge > drag **Subtractive/Additive** fully left. Blend between ends to balance too-bright vs too-dark edges.

**R6. Beauty pass rebuild** (pp. 449-454):
1. One MediaIn/Loader per pass; map channels in Channels tab (MediaIn) / Format tab (Loader, tick each channel).
2. Color pass > Merge BG, Direct Lighting > FG; adjust Alpha Gain and Blend. Or Channel Booleans: Color pass BG, light pass FG, Operation **Add**, To Alpha **Do Nothing**.
3. AO: last Merge > BG, AO pass > FG, Apply Mode **Multiply**, adjust Gain/Blend.
4. Re-embed alpha: last node > MatteControl BG, pass with alpha > MatteControl FG, **Combine = Combine Alpha**, **Combine Op = Copy**.

**R7. Separate Z pass to Depth Blur** (pp. 457-458): beauty > Channel Booleans BG; Z pass > FG; To Red/Green/Blue/Alpha = Do Nothing; Aux tab **To Z Buffer = Lightness FG** (the p. 457 steps omit it, but the Channel Booleans reference says aux targets only write once **Enable Extra Channels** is on, p. 925, so tick it); output > Depth Blur BG. Start with **Blur Size 10**, drag the **Sample** button into the viewer to pick the focus pixel, **Z Scale about 0.2** for float, leave Depth of Field, then refine.

**R8. Separate vector pass to motion blur** (p. 462): image > Channel Booleans BG; vector pass > FG; To R/G/B/A = Do Nothing; Aux tab: **Enable Extra Channels** on, **To X Vector = Red FG**, **To Y Vector = Green FG**; output > Vector Motion Blur background input.

**R9. UV retexture** (p. 460): map U/V passes to U/V aux (or Channel Booleans red>U, green>V); MediaIn > Texture BG; new texture > Texture FG; optionally Merge original BG + Texture FG and tune Apply Mode/Alpha Gain/Blend. Limit to one object with Object/Material ID.

**R10. Normals relight** (p. 461): map X/Y/Z Normal passes; MediaIn > Shader BG; optional float EXR to Shader reflection input; adjust Shader.

**R11. Object ID matte** (p. 459): map Object ID pass to Object ID aux; on the node to limit, Settings tab > **Use Object** + ID (Sample picker); enable **Correct Edges** if Coverage/BG Color exist.

**R12. Roto with MatteControl** (p. 496): plate > MatteControl BG; Polygon > Garbage Matte; view MatteControl, select Polygon, Shift-C draw, click first point to close; Garbage Matte > Invert to choose side; MatteControl > Merge FG.

**R13. Soft motion-blurred roto edge** (pp. 509-510): Double Polyline > Shift-A > hold O and drag outward > refine outer points (Tab to select outer) per segment.

**R14. Track a mask** (pp. 559-560, 1797): Tracker on the plate > track feature > mask Center right-click **Connect To > Tracker1 > Offset Position**. Or mask Center **Modify With > Tracker > Position**, set Track Source to the clean plate, track.

**R15. Graphic cutout** (pp. 488-490): select the graphic's MediaIn, click Rectangle on the toolbar, size with handles, **Corner Radius** for rounded logos; add **Crop** (viewer Crop tool) to make true resolution match; position with Merge2 Center X/Y and Size.

**R16. Clamp alpha** (p. 417): Brightness Contrast, only Alpha channel on, **Clip Black** + **Clip White**.

## Scripting and automation hooks

Stated in the manual:
- Node abbreviations "can be used in the Select Tool dialog when searching for tools and in scripting references" (e.g. p. 1272). Relevant here: Merge `Mrg`, MultiMerge `MMrg`, Dissolve `DX`, Background `Bg`, Channel Booleans `Bol` (3D: `3Bol`), Copy Aux `CpA`, Matte Control `MAT`, Alpha Divide `ADv`, Alpha Multiply `AML`, Change Depth `CD`, Brightness Contrast `BC`, Color Curves `CCv`, Color Corrector `CC`, Gamut `Gmt`, Cineon Log `Log`, File LUT `FLU`, OCIO Color Space `OCS`, OCIO File Transform `OCF`, OCIO CDL Transform `OCT`, OCIO Display `OCD`, Crop `Crp`, Resize `Rsz`, Scale `SCL`, Letterbox `LBX`, Transform `XF`, Auto Domain `ADoD`, Set Canvas Color `SCv`, Polygon `Ply`, B-Spline `BSp`, Bitmap `Bmp`, Ellipse `Elp`, Rectangle `Rec`, Triangle `Tri`, Wand `Wnd`, Ranges `RNG`, Mask Paint `PNM`, Depth Blur `DBl`, Fog `Fog`, Shader `Shd`, Texture `Txr`, Vector Motion Blur `VMB`, Volume Mask `VLM`, Text+ `TXT+`.
- Input labels named in the manual text: MatteControl `SolidMatte`, `GarbageMatte`, `EffectsMask` (p. 434); `EffectMask` (node reference input lists); Merge option "Perform Depth Merge" written as `PerformDepthMerge` in a 3D renderer tip (p. 744, which also warns supersampled Z can make depth merges worse).
- Merge Center is stored normalized (0-1, 1 = full image width/height); scripting queries and published connections return the normalized value regardless of Reference Size (p. 987). Merge Center default `0.5, 0.5`; Size slider 0-5, 1.0 = pixel-for-pixel (p. 982).
- Formulas: Merge `(fg * x) + (bg * y)`; Hypotenuse `sqrt(Fc*Fc + Bc*Bc)`; Geometric `2*Fc*Bc / (Fc+Bc)` (pp. 984-985).
- Point Editor fields accept arithmetic (the manual's example "1.0-5" moving to 0.5 is evidently meant as 1.0-.5) (p. 506).
- Connection menus: `Center > Connect To > Tracker1 > Offset Position` (p. 559); `Modify With > Tracker > Position` + Track Source field (p. 1797); Publish Points / Publish to Path / Follow Published Points (pp. 511-512); shape animation context menu `Remove Bezier Spline` / `Animate` (p. 511).
- Shortcuts: Swap Merge inputs **Command-T / Ctrl-T**; Select Tool **Shift-Space**; viewer color/alpha **C**, **A**, **R/G/B**; polyline keys in section 11; Option-drag-drop for input menu.
- Menus/paths: Project Settings > Fusion > Downscale Timeline Resolution for Timeline Clip Compositions; Project Settings > Color Management > Color Science; Fusion > Fusion Settings > General > Proxy; Preferences > Frame Format (resolution and Interactive/Final/Preview depth); viewer right-click Options > Normalized Color Range, Region > Show DoD / Show Region / Set Region / Auto Region / Reset Region, Settings > Save Defaults.

Not in the manual (inference; verify before relying on them):
- Registry IDs commonly used with `comp:AddTool()`: Merge `Merge`, Background `Background`, Polygon `PolylineMask`, B-Spline `BSplineMask`, Rectangle `RectangleMask`, Ellipse `EllipseMask`, Matte Control `MatteControl`, Channel Booleans `ChannelBoolean`, Resize `BetterResize`, Crop `Crop`, Transform `Transform`, Alpha Divide `AlphaDivide`, Alpha Multiply `AlphaMultiply`, Change Depth `ChangeDepth`, Gamut `GamutConvert`, Cineon Log `CineonLog`, File LUT `FileLUT`, Brightness Contrast `BrightnessContrast`, Color Corrector `ColorCorrector`, Auto Domain `AutoDomain`, Delta Keyer `DeltaKeyer`, Text+ `TextPlus`. (inference)
- Merge input IDs likely `Background`, `Foreground`, `EffectMask`, `Center`, `Size`, `Angle`, `ApplyMode`, `Operator`, `SubtractiveAdditive`, `AlphaGain`, `BurnIn`, `Blend`, `PerformDepthMerge`. Mask inputs likely `Level`, `SoftEdge`, `BorderWidth`, `Invert`, `Solid`, `Center`, `PaintMode`, and the shape in `Polyline`; animated shapes live in a BezierSpline whose keyframe values are `Polyline { Closed = true, Points = {...} }`. (inference)
- Discover real IDs at runtime instead of guessing (inference):
```lua
local t = comp:AddTool("Merge")
print(t:GetAttrs().TOOLS_RegID)
for _, inp in pairs(t:GetInputList()) do
  local a = inp:GetAttrs(); print(a.INPS_ID, a.INPS_Name)
end
```
```python
t = comp.AddTool("Merge")
for inp in t.GetInputList().values():
    a = inp.GetAttrs(); print(a["INPS_ID"], a["INPS_Name"])
```
