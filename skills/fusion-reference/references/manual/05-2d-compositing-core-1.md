<!-- 05-2d-compositing-core.md part 1 of 2; index: 05-2d-compositing-core.md -->
# 2D Compositing Foundations: Resolution, Bit Depth, Color Management, Channels, Merge, Masks
Scope: Fusion 21.1 manual pp. 406-512 (Ch. 16 Image Processing and Resolution, Ch. 17 Managing Color, Ch. 18 Image Channels, Ch. 19 Compositing Layers, Ch. 20 Rotoscoping with Masks), plus targeted cross-references outside the slice, each cited by page: Merge node reference (pp. 980-988), Channel Booleans (pp. 923-925), Polygon/Rectangle mask controls and mask Image tab (pp. 1249-1252, 1260-1262, 1269-1270), DoD/RoI (pp. 21, 211-213), Proxy (pp. 26-27, 84-85), tracker connections (pp. 559-560, 1797). Use when: building or debugging any 2D comp where resolution, bit depth, linear/log color, alpha premultiplication, aux channels, Merge behavior, or roto masks affect the result.

## Mental model

1. **Resolve page order is fixed.** Source Media > RAW Debayering > Clip Attributes > **Fusion** > Edit/Cut Inspector adjustments > Edit/Cut plugins (Resolve FX/OFX) > Color. Only Lens Correction (and Super Scale, sizing-wise) happens before Fusion. Edit-page Zoom, Position, Crop, Stabilization, retiming, Resolve FX and OFX are NOT visible in Fusion (pp. 408, 412).
2. **No comp resolution exists.** Resolution flows from sources down the tree. At a Merge, the orange Background input decides output resolution AND bit depth; the foreground is conformed to it (pp. 410-411, 415).
3. **The Fusion page always processes 32-bit float.** Per-node Depth (int8/int16/float16/float32) is a Fusion Studio concept (pp. 413-414).
4. **Fusion math assumes linear gamma.** Log or Rec.709 data composited as-is produces "1 + 1 = 3" errors in blurs, merges, screens, unpremultiplies. Convert to linear at the head, view through a viewer LUT, convert back at the tail, or let RCM/ACES do it (pp. 420-426).
5. **One wire carries many channels.** A connection can carry RGB, RGBA, RGBA+Z, or just Z. A branched output carries identical channels on every branch (pp. 433-434).
6. **2D nodes propagate and operate on every channel** (RGB, alpha, aux) unless the node deliberately ignores some (Color Corrector and Gamut skip alpha and aux) (pp. 438-440).
7. **Background first.** Orange = background, green = foreground, blue = effect mask, white = solid matte, gray = garbage matte. Multi-input nodes expect the background connected first; only Dissolve tolerates foreground-first (pp. 436-437, 498-499).
8. **Aux channels survive a Merge only through the Background input** (pp. 442, 464).
9. **Merge expects a premultiplied foreground.** Color-correct straight, filter and transform premultiplied, never premultiply twice (p. 445).
10. **Masks are single-channel images.** Effect masks are applied after the node's effect (copying unaffected input back) and define the node's DoD; pre-masks act before the effect (pp. 498-499).
11. **DoD vs RoI.** DoD = where the image actually has data (travels with the image). RoI = what the viewer needs rendered. A node renders the intersection. RoI never affects final output (pp. 211-213).
12. **Polygon and B-Spline masks auto-animate their points.** One keyframe stores the whole shape; center and rotation are not auto-animated (p. 511).
13. **Transforms concatenate and color adjustments concatenate** (p. 438). Merge's built-in FG transform concatenates too unless Flatten Transform is on (p. 987).

---

## 1. Resolve pipeline: what Fusion sees

| Item | Visible inside Fusion? | Page |
|---|---|---|
| RAW decode/debayer settings | Yes (happens first) | 408 |
| Clip Attributes (incl. Alpha Mode) | Yes | 408, 447 |
| Edit/Cut Lens Correction | Yes (only Inspector adjustment that carries over) | 408, 412 |
| Edit/Cut Zoom, Position, Crop, Stabilization | No (applied after Fusion) | 408, 412 |
| Edit timeline retiming | No | 408 |
| Resolve FX / OFX added on Edit/Cut | No (after Fusion) | 408 |
| Color page grades | No (after Fusion) | 409 |
| RCM input transform | Yes (Fusion viewer shows timeline color space/gamma incl. RCM) | 409 |

- Full source clip is accessible, but render range = clip's timeline duration. Full source resolution is used even if the timeline is lower (p. 408).
- **Forcing effects/grades into Fusion:** make a compound clip or Fusion clip. Cost: the clip is resized to **timeline resolution** (p. 409, 412).
- Fusion output handoff to Color: MediaOut > Color page source; if Edit/Cut plugins exist on the clip the order is Fusion > Edit/Cut Inspector > Edit plugins > Color (p. 409).

Viewer states (p. 409): Edit source viewer = source media (at timeline color space if RCM on). Edit timeline viewer and Color page viewer = everything applied. **Fusion viewer = Media Pool source at timeline color space/gamma incl. RCM, but no Edit Inspector adjustments, no Resolve FX, no grades.**

---

## 2. Resolution: how it is set and how it propagates

### Where resolution comes from (p. 410)
- Fusion page generators (Background, Fast Noise, Text+, etc.) default to **timeline resolution**.
- Fusion Studio generators default to **Preferences > Frame Format** (dropdown or manual Width/Height).
- The comp's resolution is "initially determined by the source resolution of the input image." Example stated: UHD clip in an HD timeline opens a **UHD** comp and "All Fusion-generated images in this composition will be UHD resolution."
- Fusion output returns to the Edit timeline through Resolve's **Image Sizing** project setting, default **Scale to Fit**: a 4K comp in a 1920x1080 timeline conforms to 1920x1080.

### Nodes that change pixel resolution (p. 410, 490)
All four are in Effects Library > Transform; Resize is also on the toolbar.

| Node (abbr) | How it sets output resolution | Note |
|---|---|---|
| Crop (Crp) | X/Y size + X/Y offset | Discards pixels; a later Transform cannot recover them. Changes the "canvas" without resizing the image (p. 981) |
| Letterbox (LBX) | Adds black bars to reach a frame size/aspect | |
| Resize (Rsz) | Absolute pixels | Changes both resolution and image size (p. 981) |
| Scale (SCL) | Relative % of input size | |
| Transform (XF) | Does NOT change pixel resolution | Use to reposition/scale within the same frame |

### Merge and mixed resolutions (pp. 411, 481, 981)
- The image on the orange **Background** input determines Merge output resolution. Standard practice: feed a **Background** node (cheap) at the desired size into the first Merge's BG to lock comp resolution.
- A foreground larger than the background is cropped at the output edges, but **all its pixels remain available for repositioning** (infinite workspace, see DoD).
- Mixed bit depths: the BG input decides output bit depth and the FG is converted to match (p. 415).

### Performance: Downscale Timeline Resolution (p. 411-412)
Project Settings > Fusion > **Downscale Timeline Resolution for Timeline Clip Compositions**: sources are downscaled to timeline resolution before processing (4K media in an HD timeline processes at HD cost). **EXR files are never downscaled** by this option.

### Order of sizing operations across pages (p. 412)
Super Scale > Lens Correction > **Fusion** > Edit/Cut Page Transforms > Input Sizing > Output Sizing.

### Compound/Fusion clips and resolution (p. 412)
Both conform every member clip to timeline resolution (two stacked 4K clips in an HD timeline become HD inside Fusion and are handed to Color at that size). To keep full source resolution: bring **one** clip into Fusion from the timeline, then add the others from the **Media Pool** (drag into Node Editor = new MediaIn). HD sources in an HD timeline are unaffected.

### Mask output resolution (p. 1269)
Mask nodes' Image tab **Output Size** menu: default comp resolution, the source input's resolution (for nodes with an input), or Custom (Width, Height, Pixel Aspect, Depth). Right-click Width/Height/Pixel Aspect to pick a Frame Format preset.

### Mask vs Crop for graphics (p. 489)
A mask only hides pixels; the layer keeps its full dimensions, so centering and match-moving are computed against the wrong size. Put a **Crop** after the masked MediaIn (viewer Crop tool: drag a bounding box) to make the graphic's real resolution equal the visible area, then position it with the Merge's Center/Size.

---

## 3. Domain of Definition (DoD) and Region of Interest (RoI)
(Cross-reference: Using Viewers chapter, pp. 211-213; viewer toolbar, p. 21.)

- **DoD**: axis-aligned bounding box (shown as two XY pixel coordinates) of where an image actually contains data. Nodes skip pixels outside it, and effects can apply to pixels **outside the visible frame** (infinite workspace).
- Generators set DoD automatically: Fast Noise, Mandelbrot, Background = full frame; **Text+ and most masks = much smaller (or larger) than frame**.
- OpenEXR data window is read as DoD by Loader and written by Saver. In the Fusion page, timeline/Media Pool clips get a full-frame DoD **except OpenEXR**.
- DoD is set at creation/load, then each node may shrink, expand, or move it.
- **See it**: hover a node (tooltip shows DoD if it differs from frame size) or viewer right-click **Region > Show DoD**.
- **Set it manually**: **Auto Domain (ADoD)** node (Effects Library > Tools > Miscellaneous), e.g. animate a DoD around a CG character that only occupies part of frame.
- **Effect masks define the DoD for that effect**, making it more efficient (p. 498).
- **Clipping Mode** (mask Image tab and many nodes, p. 1270): **Frame** (default) forces DoD to full frame; if upstream DoD is smaller, the rest of the frame is treated as black/transparent. **None** does no source clipping; any data needed from outside the upstream DoD is treated as black/transparent. Matters most with blur/softness.
- **Merge Edges** (p. 987) decide what fills areas outside a smaller FG's DoD: Canvas, Wrap, Duplicate, Mirror. **Set Canvas Color (SCv)** sets the color/opacity outside a DoD.
- **RoI**: rectangle of pixels the viewer actually needs. Viewer toolbar RoI button, or right-click **Region > Show Region**. Menu options: **Auto** (default, fits visible zoom/pan area), **Set** (draw rectangle; also Region > Set Region), **Lock**, **Reset** (also disabling RoI resets it). Drag edges/corners; drag the small circle at the top-left to move.
- RoI is **preview only**: Flipbook previews respect it; **MediaOut and Saver always write full frame**. Loaders/MediaIn only read pixels inside RoI when the format supports direct pixel access (Cineon, DPX, many uncompressed formats; OpenEXR and TIFF in limited cases).
- Changing viewed image size or color depth, or switching Proxy/Auto Proxy, resets pixels outside the RoI to canvas color.

## 4. Proxy and viewer quality
(Cross-reference: pp. 26-27, 84-85, Preferences.)
- **Proxy**: renders only 1 of every x pixels to the viewer. Fusion page: right-click the empty transport area to enable; ratio set in **Fusion > Fusion Settings > General > Proxy** slider. Fusion Studio: **Prx** button, right-click for ratio (e.g. 5 = 5:1).
- **Auto Proxy**: degrades only while dragging a control, snaps back on release. Ratio slider in the same panel (Studio: right-click **APrx**).
- **High Quality** off skips area sampling, anti-aliasing, interpolation in the viewer; on = identical to final render. Global **Motion Blur** toggle disables all node motion blur in the viewer (nodes must have MB enabled first).
- **Selective Update**: Update All / Selective (default; only nodes contributing to the viewed image) / No Update.
- Final renders always use full quality regardless of these settings. Viewer scales still refer to original resolution; proxy processing "may differ slightly" from full-res.
- Fusion Studio Loader: **Proxy Filename** field loads a lower-res clip in Proxy mode; it must have the same frame count and same start/end sequence numbers.
- Toggling quality/proxy preserves the previous cache until you play through frames at the new setting (p. 33).

---

## 5. Bit depth and float

| Depth | Range handling | Use |
|---|---|---|
| 8-bit integer | 0-255, rounds every op, clips | Consumer/phone/camcorder video; bands under heavy grading |
| 16-bit integer | 2x precision, **truncates <0.0 and >1.0** | Reduces new banding, cannot fix existing banding |
| 16-bit float (half) | Stores <0 and >1, slightly less precision than int16 | OpenEXR norm; enough for film/HDR at far less RAM than float32 |
| 32-bit float | Full over/under-range, max precision | Most memory/processing; Fusion page always uses it |

(pp. 413-415)
- **Fusion page**: always 32-bit float. To save memory use **Performance Mode** in User > Playback Preferences (p. 414).
- **Fusion Studio auto depth by format**: JPEG = 8-bit, 16-bit TIFF = 16-bit, DPX = 32-bit float, OpenEXR = usually 16-bit float. Override in the Loader **Import** tab. Loader and generators (Text, gradients, Fast Noise...) have a **Depth** menu: 8-bit, 16-bit integer, 16-bit float, 32-bit float (p. 414).
- **Frame Format preferences** have three color depth menus: **Interactive, Final Render, Preview Render**. Interactive/Preview at 8-bit with Final at int16 speeds work, but **if final output is float, do not use integer for Interactive**: results can look significantly different (p. 414).
- Hover a node: status bar tooltip shows its color depth (p. 414).
- Tip: 10/12-bit+ sources (Blackmagic RAW, CinemaDNG): set Depth to 16- or 32-bit float to keep highlight detail (p. 415).
- **Why float**: (1) no rounding: 8-bit red 75 halved = 37.5 -> 37, doubled = 74, one point lost per round trip; (2) no clipping: 8-bit 200 x2 = 400 clips to 255, halving gives 127 not 200; in float the round trip restores 200 (pp. 415-416). Float also helps 8-bit HD that needs heavy grading (p. 416).
- **Out-of-range values display as black/white** in the viewer. Detect them with viewer right-click **Options > Normalized Color Range** (remaps brightest to 1.0, darkest to 0.0) or the **3D Histogram** SubView (pp. 416-417).
- **Clipping out-of-range values** (p. 417): add **Brightness Contrast (BC)**, enable **Clip Black** and **Clip White**, with **only the Alpha** channel checkbox on, to clamp stray alpha <0 or >1 (out-of-range alpha gives unexpected composites). Alternative: **Change Depth (CD)** to 8-bit or 16-bit integer (clips everything).

---

## 6. Color management and linear workflow

### Defaults (p. 420-421)
Images entering Fusion are **not color managed**: file values go straight to the viewer, whether from the Edit page or a Loader. Fine for simple sRGB/Rec.709 work; wrong for log media or physically based operations.

### Conversion toolset

| Node / control (abbr) | Library | Direction and settings | Page |
|---|---|---|---|
| **Cineon Log (Log)** | Film | **Log Type** menu picks camera log (BMD, ARRI, RED common); **Mode** menu sets direction (log>linear or linear>log). Place right after MediaIn/Loader | 421 |
| **Gamut (Gmt)** | Color | Input: set **Source Space** to the media's space (HD ProRes: **ITU-R BT.709 (scene)**, gamma 2.4), enable **Remove Gamma**. Output (before MediaOut/Saver): **Source Space = No Change**, **Output Space** = sRGB or ITU-R BT.709 (scene), enable **Add Gamma** | 421-423 |
| MediaIn / Loader **Source Gamma Space** | built-in | **Curve Type**: **Auto** (reads metadata, e.g. RAW), **Log**, or **Space**; then **Remove Curve** checkbox linearizes without an extra node | 423 |
| **File LUT (FLU)** | LUT | Loads ALUT3, ITX, 3DL, CUBE. Common at the tree's end; Gamut/CineonLog give more accurate linearization | 423 |
| **OCIO Color Space (OCS)** | Color | OCIO config-based source/output conversion | 428 |
| **OCIO File Transform (OCF)** | Color | Applies LUTs via OCIO | 428 |
| **OCIO CDL Transform (OCT)** | Color | Create/save/load/apply a CDL grade | 428 |

- Gamut and Color Corrector do **not** touch alpha (p. 438) or aux channels (p. 440): safe for color-matching a layer without disturbing its matte/depth.
- **CG EXRs are usually already linear**; check, but do not linearize twice (pp. 421, 452).

### Manual linear workflow (p. 420)
1. Gamut or CineonLog after every MediaIn/Loader (to linear).
2. Viewer LUT: Gamut View LUT set to sRGB or Rec.709.
3. Gamut or CineonLog before Saver/MediaOut (linear to delivery).

### Viewer LUT (pp. 424-425)
Linear images look dark with blown highlights and oversaturation; float means nothing is lost. To preview: enable the viewer **LUT** button > choose **Gamut View LUT** (or a VFX IO LUT that maps linear to Rec.709/sRGB) > menu **Edit** > set **Output Space** > enable **Add Gamma**. Match your monitor calibration if different. Persist with viewer right-click **Settings > Save Defaults**.

### Resolve Color Management (RCM) (pp. 425-426)
- Enable: Project Settings > Color Management > **Color Science = DaVinci YRGB Color Managed** > **Automatic color management** (or uncheck and set Color Processing mode and Output Color Space manually).
- With RCM on, every MediaIn is automatically converted **to linear** from its detected input color space; MediaOut is converted back to the Color Processing mode for grading/editing. **Do not add CineonLog/Gamut nodes.**
- Switching to the Fusion page enables the viewer LUT with **Managed LUT** selected (linear image displayed per RCM output color space).
- Per-clip override: Media Pool > select clips > right-click > Input Color Space.
- RCM input math preserves wide-latitude data, so highlights are retrievable without extra steps.

### ACES in Resolve (pp. 427-428)
- Color Science menu: **ACEScct** or **ACEScc** (identical except shadow response to grading; Fusion converts to linear either way). ACEScc = Cineon-style log; ACEScct adds a toe roll-off (lift feels like film/LogC).
- **ACES Version**, **ACES Input Device Transform** (IDT, for the dominant media), **ACES Output Device Transform** (ODT, deliverable).
- **Process Node LUTs In**: Color page only, no effect on Fusion.
- **Disable tone mapping for Fusion conversion**: removes ACES tone mapping from the Fusion conversion.
- Fusion Studio uses OCIO for ACES.

### OCIO for ACES without RCM (pp. 428-430)
1. OCIO Color Space node directly after MediaIn/Loader. Built-in default transforms exist; for full ACES download the config from opencolorio.org, **Browse** to the ACES 1.0.3-or-later folder, pick **config.ocio**.
2. **Source** = recording profile (default **raw** = no management). **Output** typically **ACEScg** (scene linear) in Fusion Studio.
3. Viewer: LUT menu > **OCIO Color Space View LUT** > **Edit** > Browse same config > source **lin sRGB** (manual's wording when working ACEScg) > output **sRGB** or **Rec.709**. Save Defaults to persist.

---

## 7. Channels

### Channel types (pp. 432-433)
- **RGB**: additive color, each a grayscale image.
- **Alpha**: 4th channel; **white = opaque, black = transparent**. Every alpha-capable node can invert it (for reversed conventions).
- **Single-channel masks**: produced by Mask nodes, external to RGB; connect only to mask inputs (Effect Mask, Garbage Matte, Solid Matte) or to other masks.
- **Auxiliary**: 3D-derived data (Z, normals, vectors...). See section 9.
- View any channel via the viewer **Color** dropdown (C/A toggles color/alpha; R, G, B, A keys isolate) (p. 433, p. 21). **Color Inspector** SubView reads numeric values of all channels (p. 456).

### Node color categories (pp. 437-438)

| Color | Category | Channel behavior |
|---|---|---|
| Blue | MediaIn, Loader | Output RGBA (+ optional aux) |
| Green | Generators; Shape nodes | RGBA; Shape nodes need gray "s"-prefixed shape modifier/render nodes |
| Orange | Blur | 2D, processes RGBA, passes aux |
| Olive | Color adjustment | 2D; **concatenate with each other** |
| Pink | Paint | 2D |
| Dark orange | Tracking | 2D |
| Tan | Transform | 2D; **concatenate with each other** |
| Teal | VR | 2D |
| Dark brown | Warp | 2D |
| Gray | Compositing and many others | 2D |
| Purple | Particles | Incompatible with 2D until **pRender** |
| Dark blue | 3D | Incompatible with 2D until **Renderer 3D** (a Text3D cannot plug into a Merge) |
| Brown | Masks | Single-channel; only to other masks or mask inputs |

### Connection rules (pp. 433-437)
- One output per input; branching duplicates the same channels.
- Dropping a wire on a node body connects to the default input ("Input" or "Background"). Dropping on a specific input connects there. **Option-drag and release on a node** pops a menu of inputs by name (pp. 436, 479).
- Mask nodes dropped on a node connect to the first available mask input (p. 437). Selecting a node with an empty effect mask input and adding a Mask node auto-connects it (p. 497).
- Wrong-input connections often produce no error, just no result. Hover inputs for tooltips (Tooltip bar, then Node Editor tooltip) (pp. 435, 479).

### Channel limiting (pp. 440-441, 992)
Settings tab **Red/Green/Blue/Alpha** buttons: the node processes all channels, then copies unchecked channels from input to output (e.g. Transform with only Green on shifts only green). Nodes whose RGBA buttons also appear on the Controls tab (**Blur, Brightness/Contrast, Erode/Dilate, Filter**) truly skip processing unchecked channels; the two sets are instanced.
Example: TV effect writes scan lines into alpha; uncheck **Alpha** in Settings for a solid image (p. 469).

### Common Settings tab (documented once; applies across 2D nodes) (pp. 992-993)
**Blend** (0.0 = passthrough, node normally skips processing), **Process When Blend Is 0.0**, RGBA selectors, **Apply Mask Inverted**, **Multiply by Mask** (RGB multiplied by mask, outside becomes black/transparent), **Use Object / Use Material** + **Object ID / Material ID** sliders with Sample picker, **Correct Edges** (uses Coverage and Background Color aux to anti-alias ID masks; without them edges may alias), **Use GPU** (Disable/Enabled/Auto), Motion Blur group, Comments, Scripts.

### Recombining channels (p. 443)

| Node (abbr) | Purpose |
|---|---|
| **Channel Booleans (Bol)** | Shuffle/math RGBA and aux within one image or between two. **With a single image, connect it to the Background input** |
| Channel Boolean (3Bol) | 3D material node, not for 2D |
| **Copy Aux (CpA)** | Aux <-> RGB copying, remapping values/depths, removing aux. Convenience subset of Channel Booleans |
| **Matte Control (MAT)** | Combine mattes/masks/alpha, refine alpha, copy alpha from FG or Garbage/Solid matte into the BG image. **Image receiving alpha must be on Background** (p. 478) |

**Channel Booleans details** (pp. 923-925): inputs Background (orange, required), Foreground (green), Effect Mask (blue), **Matte** (white, external matte usable as a source). Missing FG = FG options use BG channels. Color Channels tab: **Operation** = Copy, Add, Subtract, And, Or, Exclusive Or, Multiply, Divide, Maximum, Minimum, Negative, Solid, Clear, Difference, Signed Add. **To Red/To Green/To Blue/To Alpha** menus choose sources (suffix BG or FG; also alpha, Z-buffer, saturation, luminance, hue; **Do Nothing** leaves the channel). **Aux Channel** tab: **Enable Extra Channels** must be on before aux targets (To Z Buffer, To X Vector, To Y Vector...) are written. Recipes stated: replace alpha with another image's alpha = To R/G/B Do Nothing, To Alpha **Alpha FG**, Operation Copy; mask into alpha = To Alpha **Matte**, Operation Copy.

---

## 8. Premultiplication

### Definitions (pp. 443-445)
- **Straight (unpremultiplied)**: RGB not multiplied by alpha; RGB edges look ragged, the soft edge lives only in alpha.
- **Premultiplied**: RGB x alpha. Alpha itself is unchanged. Transparent RGB = 0 (black), opaque = unchanged, edge pixels (e.g. alpha 0.3) become darker mixed colors. Most CG is premultiplied.

### The four rules (p. 445)
1. Always feed **premultiplied** images to Merge.
2. Only **color-correct straight** images.
3. **Filter and transform premultiplied** images.
4. **Never double-premultiply.**

### Symptoms and fixes

| Symptom | Cause | Fix | Page |
|---|---|---|---|
| Bright fringe around FG edges in Merge | FG not premultiplied; transparent pixels still added (Merge is additive) | Merge **Subtractive/Additive** slider fully left (Subtractive), or premultiply upstream | 445, 472-473 |
| Dark halo | Double premultiply, or Subtractive on premultiplied FG | Remove extra multiply; slider to Additive | 446, 473 |
| Grading the FG brightens/darkens the whole BG in the Merge | CC on premultiplied RGB breaks RGB/alpha relationship ("glow") | **Pre-Divide/Post-Multiply** checkbox, or Alpha Divide > CC > Alpha Multiply | 446 |
| Checkerboard only semi-transparent where it should be clear | MatteControl combined RGB with mask but did not multiply RGB | Multiply RGB by the mask (in MatteControl) | 446 |
| Artifacts at transparent edges after a bloom/defocus filter | Filter modifies color near edges | Mind premult state for color-modifying filters | 447 |

### Controls (pp. 447-448)
- **Pre-Divide/Post-Multiply** checkbox: Brightness Contrast, Color Curves, and Color Corrector (**Options** panel), among "most nodes that require you to explicitly deal with" premult. Divides, corrects, re-multiplies: output stays Merge-friendly.
- **Alpha Divide (ADv)** and **Alpha Multiply (AML)** (Matte category): bookend a run of several color nodes, or third-party OFX color tools that lack the checkbox. Tip: 3D render alphas are typically premultiplied (p. 454).
- **Loader Import tab**: checkboxes to make alpha solid (ignore transparency), Invert alpha, **Post-Multiply** RGB by alpha.
- **MediaIn**: Resolve **Clip Attributes > Alpha Mode**: ignore, premultiplied, inverted, or straight (non-premultiplied).

---

## 9. Multi-pass compositing

### Beauty passes (pp. 448-454)
- One MediaIn/Loader outputs one RGBA set, so **one node per pass**. EXR is optimized: several Loaders on the same file load it once. Rename nodes after their pass.
- **MediaIn**: **Image** tab **Layer** menu assigns a combined pass to RGBA (whole pass only). **Channels** tab has per-channel RGBA menus (e.g. Red = `AO.R`, Green = `AO.G`, Blue = `AO.B`) and lets you borrow alpha from another pass. **Loader**: **Format** tab does the same; each channel's checkbox must be on or that channel is not output (p. 452). Pass names vary by renderer (AO, AM_OCC...).
- 3D renders are typically linear: no Gamut conversion needed if you stay linear (p. 452).

### Aux mapping (pp. 455-456)
Channels/Format tab contains predefined aux slots (Z, Object ID, UV, normals, vectors...), each with a menu listing every EXR attribute. Mapped aux appear in the viewer Color menu.

### Aux channel reference (pp. 456-466)

| Channel | Meaning | Primary consumers | Notes |
|---|---|---|---|
| **Z-Depth** | Per-pixel relative depth (nearest object wins) | Merge Perform Depth Merge, **Depth Blur (DBl)**, **Fog**, Shadow (Z-Map), SSAO (needs Camera3D input), Luma Keyer (select Z in channel list) | Often negative values: use Normalized Color Range to view |
| **Z-Coverage** | % transparency of pixels where two objects overlap in Z | Merge depth merge, Correct Edges | "Somewhat extinct" |
| **Background RGBA** | Colors behind Z-coverage pixels | Merge depth merge, Correct Edges | "Somewhat extinct"; Cryptomatte has largely superseded Coverage/BG/ID mattes |
| **Object ID** | Integer ID per object | Settings tab **Use Object** + ID; Bitmap mask | Map pass to Object ID slot first |
| **Material ID** | Integer ID per material | Settings tab **Use Material**; Bitmap mask | |
| **UV Texture** | Pixel-to-texture coordinates | **Texture (Txr)** node (retexture), Shader | Separate UV pass in RGB: map red to U, green to V via Channel Booleans |
| **X/Y/Z Normals** | Surface orientation | **Shader (Shd)** relighting | 2D warps (e.g. Vortex) warp normals too |
| **XY Vector / XY BackVector** | Motion to next / previous frame | **Vector Motion Blur (VMB)**, Vector Distortion (forward only), Time Speed, Time Stretcher, Smooth Motion | Separate pass: X in R, Y in G |
| **World Position (WPP)** | XYZ position as RGB (0/0/0 = black, 1/0/0 = red) | **Volume Mask (VLM)**, Volume Fog, Z to WorldPos | **Always render in 32-bit float** |
| **XY Disparity** | Where each pixel lies in the other stereo eye | New Eye, Stereo Align, Disparity to Z | Only aux channel not produced by 3D apps |

Also: Custom Tool, Custom Vertex 3D, pCustom can sample aux per pixel/vertex/particle; Disparity to Z, Z to Disparity, Z to WorldPos convert between them (p. 464).

**Formats carrying aux** (p. 465): OpenEXR (arbitrary named channels, primary), SoftImage PIC + ZPIC (same folder, same names, auto-detected), Wavefront/3ds Max RLA and RPF (RPF can store multiple samples per pixel), Fusion RAW (all aux + metadata).
**Fusion creators** (p. 466): Renderer 3D (all aux types), Optical Flow (Vector/BackVector), Disparity (Disparity).
**Propagation** (p. 464): aux flows through gray/Blur/Filter/Effect/Transform/Warp nodes (and gets manipulated by them). At a Merge only the BG input's aux survives.

---

