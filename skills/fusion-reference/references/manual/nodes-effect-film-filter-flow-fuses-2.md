<!-- nodes-effect-film-filter-flow-fuses.md part 2 of 2; index: nodes-effect-film-filter-flow-fuses.md -->
## Film Nodes (Chapter 39)

### Cineon Log [Log]
Converts log camera formats to linear gamma and back. Despite the name, handles log gamma from many
digital-cinema sources (Blackmagic Design, Arri, Red), not just Cineon files (p. 1079).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Setup: placed directly after a MediaIn/Loader node, or before a MediaOut/Saver node to convert back
  to log-encoded output (p. 1079).
- Controls tab (p. 1080-1081): **Depth** — Auto (default; determined by file format, e.g. JPEG loads at
  8-bit, Blackmagic RAW at Float; falls back to the Frame Format preferences default if undetermined) or
  manual selection. **Mode**: Log to Lin / Lin to Log. **Log Type**: Cineon, Arri Log C, BMD Film, Canon
  Log, Nikon N Log, Panalog, Panasonic V-Log, Red Log Film, Sony S-Log, Viper Film Stream, ACESlog, Josh
  Pines (film-scan-workflow specific). **Lock RGB** (on = all channels share settings; off = independent
  R/G/B settings). **Level** (range control — left handle = black level, right handle = white level, in
  log space before conversion; values below black go out-of-range <0.0, above white go out-of-range
  >1.0; float preserves out-of-range values, 16-bit/8-bit clip them). **Soft Clip (Knee)** (smooths the
  conversion curve top/bottom to draw out-of-range values back into range; **GOTCHA**: any Soft Clip
  value other than 1 forces the node to process at 16-bit integer, eliminating out-of-range values that
  don't fit the soft clip). **Film Stock Gamma**, **Conversion Gamma**, **Conversion Table** (set the
  response curve; a custom ASCII LUT file can be loaded via the Browse button).
- Common Controls: Settings tab.
- **Black Rolloff note / custom black-ramp recipe** (p. 1081, technical aside): `log(0 or negative)` is
  mathematically invalid, so Fusion clips values below `1e-38` to 0. Some pipelines instead *scale*
  near-zero values (0.0-1e-16 scaled into 1e-18 to 1e-16) to crush most of the visual range near zero
  then re-expand it, forcing a gentle ramp in extreme blacks. To mimic this with a Custom node:
  1. Convert log → linear using a small conversion gamma (e.g. 0.6) and a wider-than-normal
     black-to-white level (e.g. black = 10, white = 1010) — this crushes most of the range into very
     small values.
  2. Feed that into a Custom node using this expression on the Red, Green, and Blue channels:
     `if (c1< 1e-16, 1e-18 + (c1/1e-16)*(1e-16 - 1e-18), c1)`
  3. Convert linear → log again, using a slightly *higher* black level than step 1 — the difference
     between the two black levels defines the falloff range.
  4. Since this lifts the blacks, convert back to linear one more time using traditional values (the
     manual gives 95-685 as an example) to reset the black point.

### Film Grain [FGr]
Adds generated film grain — typically re-applied after grain was removed for cleaner keys/composites, so
different elements read as one film stock. **NOTE (manual)**: does not replace the older Grain node
(kept only so old comps still load/render) — "in almost every case, it is better to use the Film Grain
node" (p. 1082).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Setup: commonly placed just before a MediaOut/Saver node (p. 1082).
- Controls tab (p. 1083-1085): **Complexity** (number of grain "layers" calculated and mean-combined —
  1 = single layer, 4 = four layers averaged; higher = more sophisticated look, less apparent
  regularity). **Alpha Multiply** (multiplies the grain result by the source Alpha, so grain doesn't
  affect transparent post-multiplied areas; **NOTE**: since semitransparent-pixel final values aren't
  known until after compositing, avoid log-processed grain on elements before they're composited — apply
  it after, for accurate strength). **Log Processing** (default ON — applies grain intensity
  nonlinearly to match real film response, roughly exponential from black to white; real film also
  shows more grain in the blue channel due to chemical layer response differences; disabling applies
  grain uniformly regardless of pixel brightness; enabling ≈ the old Grain node preceded by a Linear-
  to-Log and followed by a Log-to-Linear conversion). **Seed** + Reseed button (matching seeds on two
  nodes = matching random result). **Time Lock** (stops the seed from generating new grain every
  frame). **Monochrome** (default ON — grain applied equally to R/G/B; off = independent Size/
  Strength/Roughness per channel). **Lock Size X/Y** (deselect for independent X/Y grain size). **Size**
  (relative to pixel size, so it's resolution-independent; default 1.0 ≈ grain kernels covering ~2
  pixels). **Strength** (variation from the original pixel value; example: complexity=1, size=1,
  roughness=0, log off — a pixel at 0.5 with strength 0.02 can land between 0.48 and 0.52; Log
  Processing skews this so blacks vary less and whites vary more). **Roughness** (adds low-frequency
  variation for a "clumping" look; 0 = even luminance variation across the image, 1.0 = visible cellular
  differences). **Offset** (matches grain intensity in deep blacks by offsetting the value before the
  strength calculation — e.g. offset 0.1 makes a 0.1-valued pixel receive grain as if it were 0.2).
- Common Controls: Settings tab.

### Grain [Grn]
Older film-grain emulation, superseded by Film Grain; kept only so older compositions still load/render
— "in almost every case, it is better to use the Film Grain node" (p. 1086).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Controls tab (p. 1087): **Power** (overall strength); **RGB Difference** (separate per-channel
  strength sliders); **Grain Softness** (blur/fuzziness — smaller = sharper/coarser grain); **Grain
  Size** (particle size); **Grain Spacing** (density — higher = more spaced out); **Aspect Ratio**
  (match to anamorphic images); **Alpha-Multiply** (multiplies by Alpha, clearing black areas of grain).
- Spread tab (p. 1088): **RGB checkboxes** (enable a custom curve per channel — to mimic real film,
  blue typically needs the most grain, red less, green least); **In and Out** (direct edit of curve
  points via In/Out values). Right-click the spline area for a curve-editing contextual menu.
- Common Controls: Settings tab.

### Light Trim [LT]
Emulates film-scanner light trims. Designed for logarithmic data (Cineon, Arri, Blackmagic RAW); raises
or lowers the apparent exposure of the image (p. 1089).
- Inputs: **Input** (orange, primary Log 2D image); **Effect Mask** (blue).
- Setup: placed after a LOG clip but *before* it is converted by a Cineon Log node (p. 1090).
- Controls tab (p. 1090): **Lock RGBA** (default ON, one slider controls all channels; deselect for
  independent per-channel control). **Trim** (shifts color in film/optical-printing/lab-printing points;
  **8 points = one stop of exposure**).
- Common Controls: Settings tab.

### Remove Noise [RN]
Simple noise management: blurs each channel, compares blurred vs. original to extract the noise, then
sharpens everywhere except where noise was detected. Workflow given in the manual (p. 1091): view the
red channel, increase Red Softness until grain disappears, increase sharpness until detail reappears but
stop before grain returns, then repeat for green and blue.
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Controls tab (p. 1092): **Method** — Color (separate R/G/B blur+sharpen sliders) or Chroma (Luma/
  Chroma sliders instead). **Lock** (links Softness/Detail sliders across channels). **Softness Red/
  Green/Blue** (or Luma/Chroma in Chroma mode) — blur amount per channel. **Detail Red/Green/Blue** (or
  Luma/Chroma) — sharpness reintroduced after softening, per channel.
- Common Controls: Settings tab.

### Common Controls (Film nodes)
Same family as the Effect chapter (Blend, Process When Blend Is 0.0, RGBA selector, Apply Mask Inverted,
Multiply by Mask, Use Object/Material + Correct Edges + ID sliders, Use GPU, Comments, Scripts — see the
shared section above), with these differences noted in the manual text for this chapter (p. 1093-1095):
Clipping Mode here has **three** options — Frame (default), **Domain** (respects the upstream DoD; can
adversely clip with large filters), None (no clipping at all). This slice's Film Common Controls text
does not restate the Motion Blur family.

---

## Filter Nodes (Chapter 40)

### Create Bump Map [CBu]
Converts a grayscale height-map image into a bump map: bump vector data output as an RGB image, for
further 2D image processing (different from the 3D Bump Map node, which turns an image into a 3D
material) (p. 1097).
- Inputs: **Input** (orange, RGBA used to calculate the bump map); **Effect Mask** (blue).
- Controls tab (p. 1098): **Filter Size** — 3×3 or 5×5 (radius of pixels sampled; larger = slower).
  **Height Source** (channel used for grayscale extraction). **Clamp Normal.Z** (clips lower values of
  the resulting bump texture's blue channel). **Wrap Mode** (border-wrap handling, for seamless tiling
  textures). **Height Scale** (contrast of resulting values; higher = more visible bump). **Bump Map
  Texture Depth** (match/convert bit depth).
- Terminology (manual definitions, p. 1098): **Height Map** = grayscale image, one height value/pixel.
  **Bump Map** = image with normals in RGB, used to *modify* existing normals (usually tangent space).
  **Normal Map** = image with normals in RGB, used to *replace* existing normals (tangent or object
  space).
- Common Controls: Settings tab.

### CreateReliefMap [CRM]
Companion tool for the ReliefMap node: generates a relief map from a height field to modify an object's
surface normals, producing simulated texture/lighting when fed into ReliefMap (p. 1099).
- Inputs: single yellow input (2D image) — no separate mask input stated.
- Controls tab (p. 1100-1101): **Map Type** — Relief, Relaxed Cone, Cone (all combine RGB + Alpha;
  Relaxed Cone/Cone are more accurate at a higher performance cost). **Depth Source** (dropdown source
  for depth data). **Depth Scale** (higher = deeper relief). **Texture Depth** (match/change bit
  depth). **Pre Blur** (blurs the source image before generating the map). **Flip Depth** (checkbox,
  inverts the depth mapping).
- Common Controls: **both** Transform and Settings tabs apply to this node (unlike most Filter nodes,
  which reference only Settings) (p. 1101).

### Custom Filter [CFlt]
Applies custom convolution filters (emboss, relief, sharpen, blur, edge detection, etc.). Many preset
filters ship in the Filters directory, loadable via right-click on the control header > Settings > Load
(p. 1101).
- Inputs: **Input** (orange, RGBA); **Effect Mask** (blue).
- Controls tab (p. 1101-1103): **Color Channels (RGBA)** checkboxes — pre-process channel skip (speeds
  rendering; distinct from the post-process Common Controls RGBA buttons). **Matrix Size** — 3×3, 5×5,
  or 7×7 (larger = slower). **Update Lock** (pauses rendering while you set up filter values). **Filter
  Matrix** — a 7×7 grid of integer text boxes (the Inspector always shows 7×7; Matrix Size just
  determines how many of the cells are active, e.g. 3×3 only uses the center 9). Center cell = the
  pixel being processed; adjacent cells = neighboring pixels. Value 1 = full pixel weight, 0 = ignored,
  >1 multiplies the effect, negative values subtract from the average. **GOTCHA: only integer values
  are valid — 0.x entries are not accepted.** **Normalize** (0 = normalized image; positive = brighten/
  raise level; negative = darken/lower level). **Floor Level** (adds/subtracts a minimum to the
  filtered result; 0 = no change).
- Recipes — matrix examples verbatim from the manual (p. 1103-1105):
  1. **Identity / no-op**: `0 0 0 / 0 1 0 / 0 0 0` — zero effect from neighbors, image unchanged.
  2. **Softening/blur**: `1 1 1 / 1 1 1 / 1 1 1` — averages the neighboring pixels with the center.
  3. **Emboss**: `-5 0 0 / 0 1 0 / 0 0 5` — subtracts 5× the top-left value, adds 5× the bottom-right
     value; smooth areas stay similar, edges (where neighbors differ) get highlighted/embossed.
  4. **Exposure/glow (simulated overexposure)**: same all-1s matrix as softening (`1 1 1 / 1 1 1 /
     1 1 1`), with **Normalize** turned to a positive value — brightens/glows the image.
  5. **Relief**: `-1 0 0 / 0 0 0 / 0 0 1`, with **Floor Level** set to a positive value — creates a
     relief effect.
- Common Controls: Settings tab.

### Erode Dilate Node [ErDl]
Contracts (Erode, negative Amount) or expands (Dilate, positive Amount) the image; commonly used to
contract/expand mattes (e.g. after a Luma Keyer, before a Matte Control) (p. 1106).
- Inputs: **Input** (orange, RGBA); **Effect Mask** (blue).
- Controls tab (p. 1107): **Color Channels (RGBA)** — same pre-process skip family as Custom Filter.
  **Lock X/Y** (uncheck to separate Amount into independent X and Y). **Amount** — negative = erode
  (shrinks the image; darker areas grow, eating brighter regions — like underexposure); positive =
  dilate (expands; brighter/high-luminance regions grow, eating darker regions — like overexposure).
  Both destroy fine detail and posterize gradients. **GOTCHA / key scripting fact: the Amount scale is
  based on the input image width — Amount = 1 equals the full image width.** To erode/dilate by exactly
  1 pixel on an HD (1920-wide) image, enter `1/1920 = 0.00052083`.
- Common Controls: Settings tab.

### Filter Node [Fltr]
Selectable standard convolution filters; Sobel and Laplacian are commonly used for edge detection
(p. 1108).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Controls tab (p. 1109-1110): **Filter Type** — Relief (presses the image into metal/a coin look,
  bumped and overlaid on gray); Emboss Over (embosses the image over itself, adjustable via Angle);
  Noise (uniform noise, useful for blending CG with live action — frame number is the random seed, so
  the effect differs per frame but is repeatable); Defocus (blurs the image); Sobel (advanced edge
  detection — combine with a Glow filter for neon-light looks); Laplacian (more sensitive edge
  detection, finer edges than Sobel); Grain (film-like noise mostly in the midrange, same CG-compositing
  use case as Noise, also frame-number-seeded). **Color Channels (RGBA)** — standard channel selection.
  **Power** — range 1-10, proportionately increases the filter's effect; **does not apply to Sobel or
  Laplacian**. **Angle** — range 0-315°, in 45° increments; applies **only** to Relief and Emboss.
  **Median** — appears depending on Filter Type; 0.5 = true median (middle value), 0.0 = finds the
  minimum, 1.0 = finds the maximum. **Seed** — visible only for Grain/Noise; same seed = same random
  result. **Animated** — visible only for Grain/Noise; checked = changes frame to frame, unchecked =
  static noise.
- Common Controls: Settings tab.

### Rank Filter Node [RFlt]
Examines nearby pixels, sorts them by value, and replaces the center pixel's color with the pixel at a
chosen rank (p. 1110).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Controls tab (p. 1111): **Size** — sample-area radius in pixels; 1 = 1 pixel each direction = 9
  total pixels including center. Low Size settings are good for removing salt-and-pepper noise; larger
  Size settings produce a watercolor-painting look. **Rank** — 0 = lowest/darkest value, 1 = highest/
  brightest value chosen from the sample.
- Recipe (manual example, p. 1111): **Size = 7, Rank = 0.7** produces a watercolor-style effect.
- Common Controls: Settings tab.

### Common Controls (Filter nodes)
Same family as above (Blend, Process When Blend Is 0.0, RGBA Channel Selector [post-process], Apply
Mask Inverted, Multiply by Mask, Use Object/Material + Correct Edges + ID sliders, Use GPU, Motion Blur
family [Motion Blur/Quality/Shutter Angle/Center Bias/Sample Spread], Comments, Scripts — p. 1112-1114).
**GOTCHA: unlike the Effect and Film chapters, this slice's Filter-chapter Common Controls text does not
include a Clipping Mode control at all** — don't assume it exists here just because it does elsewhere.

---

## Flow Nodes (Chapter 41)

### Sticky Note [NTE]
Not a node — attaches notes/comments/history to an area of a comp; complements the Comments tab found
on individual tools (p. 1116).
- Usage: click an empty area of the Node Editor where the note should appear, then choose Sticky Note
  from Effects Library > Tools > Flow, or press **Shift-Spacebar** and search "Sticky Note" in the
  Select Tool window.
- Created collapsed; double-click to expand; resize from any side/corner; move by dragging the name
  header; click the top-left icon to re-collapse.
- Right-click for: rename, delete, copy, change color, lock (prevents editing).
- To edit text: expand it, click below the title bar, and type (only if unlocked).

### Underlay [UND]
Visually organizes comp areas into labeled functional blocks. Difference from Groups: Underlay
*highlights* rather than hiding, and does **not** restrict outside connections (Groups collapse
complexity into a single node and do restrict how it connects) (p. 1117).
- Usage: add from the Flow category in the Effects Library or via Select Tool search; it centers on the
  last-clicked position. Resizable from any side/corner without affecting contained nodes.
- Acts as a selection group: clicking its title selects all tools wholly contained within it, so the
  whole set can be moved/duplicated/etc. together.
- To rename: first make sure the contained nodes are *not* selected, then **Option-click** the Underlay
  title to select the Underlay alone, then right-click > Rename. Color is assignable from the same
  contextual menu.

---

## Flow Organizational Nodes (Chapter 42)

### Groups
Keeps complex node trees organized by collapsing any selection of nodes into a single icon.
Non-destructive and reopenable at any time (p. 1119).
- Usage: select nodes, right-click > **Group**.
- Edit: right-click the group > **Expand Group** — opens a floating node-tree window that hovers over
  the existing comp; edit the contained nodes there.
- Remove: right-click > **Ungroup** to decompose the group and retain the individual nodes.

### Macro
Not technically a node — a group of nodes that behaves as one, exposing a user-definable set of
controls. Fast way to build a custom node (p. 1120).
- Usage: select the nodes to include — **selection order becomes their display order** in the Macro
  Editor — then right-click > **Macro > Create Macro**.
- Macro Editor: rename the tool (manual example: "Light_Wrap") and enable/rename exposed controls
  (example: Matte Control 1's Blur slider renamed to "Softness" as it appears in the final Inspector).
- Close button's Save dialog: **Yes** = save, **No** = discard changes, **Cancel** = return to the
  editor.
- Add the finished macro to a tree: right-click anywhere > **Macro > [MacroName]**.
- **File path (key fact)** — to make a *title* macro appear in the DaVinci Resolve Edit page Effects
  Library (macros are otherwise Fusion-page-only), save it to:
  - macOS: `Users/UserName/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/
    Templates/Edit/Titles`
  - Windows: `C:\Users\UserName\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\
    Templates\Edit\Titles`
- Example use (manual, p. 1121): a single Channel Boolean node set to Add mode, macro'd with zero
  exposed controls, becomes the equivalent of an "Add Mix" node (as found in Nuke).

### Pipe Router
Purely organizational — creates "elbows" in the node tree's connection lines so wires don't overlap
nodes; **has no effect on render times** (p. 1121).
- Usage: **Option/Alt-click** on a connection line to insert a router; reposition it freely afterward.
- Has no real controls of its own, but can still hold a comment.

---

## Fuses (Chapter 43)

### Fuses [Fus]
Plugins written as a Lua script, as opposed to compiled Open FX (OFX) plugins (p. 1124).
- **Advantages**: edited directly inside Fusion/Resolve; changes compile **on the fly** — no need to
  close the current composition; easy for non-programmers to prototype/develop custom nodes; can also
  act as modifiers (manipulating parameters, curves, and text); ViewShader Fuses can use the GPU for
  faster performance.
- **GOTCHA (tradeoff)**: because a Fuse compiles on the fly, it can be **significantly slower** than the
  identical node built with the OFX SDK.
- Example uses given in the manual: generating a mask from an image's over-exposed areas; creating
  initial particle positions from XYZ data stored in a text file.
- SDK docs are not bundled — the manual says to contact Blackmagic Design directly for the Fuse SDK
  documentation.
- **Installation (key scripting/file-path fact)**: Fuses install to the `Fusion:\Fuses` path map. Default
  locations, and files **must** use the `.fuse` extension or Fusion ignores them:
  - macOS: `Users/User_Name/Library/Application Support/Blackmagic Design/Fusion (or DaVinci
    Resolve)/Fuses`
  - Windows: `C:\Users\User_Name\AppData\Roaming\Blackmagic Design\Fusion (or DaVinci Resolve)\Fuses`
- Working with Fuses in a comp: once installed, a Fuse can appear in any Effects Library category and is
  added to a comp exactly like any native or third-party node. Because a Fuse is a plain text document,
  click the **Edit** button at the top of the Inspector (when the Fuse node is selected) to open it in
  the default script editor set in **Global Preferences > Scripting**.
- **GOTCHA**: editing a Fuse's script does **not** immediately affect other copies of the same Fuse
  already placed in the comp. To propagate the update to all instances, either close and reopen the
  composition, or click the **Reload** button in each individual Fuse's Inspector.
- **GOTCHA**: opening a saved composition always loads the currently-saved version of any Fuse script at
  that time — the simplest way to guarantee you're running the current Fuse code is to close and reopen
  the composition.

---

## Gotchas and non-obvious behavior

- Effect Mask on every node in this slice is applied **after** the tool processes — it's a post-crop,
  not a pre-limit on computation (stated identically for every node with an Effect Mask input).
- Highlight's white **Highlight Mask** is the one exception: it pre-masks the image before the highlight
  is computed, then merges the result back — and it deliberately does *not* crop highlights that extend
  past the mask edges the way a normal Effect Mask would.
- Two different "RGBA channel" controls exist on the same node for Custom Filter, Erode/Dilate, and
  Filter node: the Controls-tab RGBA checkboxes skip a channel from processing (faster), while the
  Settings-tab (Common Controls) RGBA buttons process everything then copy the untouched channel back
  (same visual result, no speed gain, but works when the node's own math would otherwise use that
  channel).
- Duplicate's **Copies** chain — each copy transforms the *previous* copy, not the original — so Gain,
  Size, and Angle changes compound multiplicatively with the Copies count. Blur amount is explicitly
  called out as the one control that does *not* compound.
- Duplicate and Trails use **identical** Apply Mode / Operator math — memorize it once:
  `result = (fg * x) + (bg * y)`, with x/y defined per Operator mode (Over, In, Held Out, Atop, XOr).
- Cineon Log's **Soft Clip (Knee)**: any value other than 1 silently forces the node to process at
  16-bit integer internally, which eliminates out-of-range float values that don't fit inside the soft
  clip — a precision gotcha if you're relying on float-range highlight/shadow recovery.
  Custom Filter matrix values **must be integers** — decimal entries (0.x) are rejected.
- Erode/Dilate's Amount is scaled to image width, not pixels — Amount = 1 is a full image width; for
  exact single-pixel offsets, divide 1 by the image's pixel width (e.g. `1/1920` for HD).
  Clipping Mode option sets differ by node category in this slice (Effect: Frame/None; Film: Frame/
  Domain/None; Filter: not documented in this slice's Common Controls text) — don't assume all three
  categories expose the same menu.
- Film Grain vs. Grain, and Cineon Log's Log Type list: the manual explicitly recommends Film Grain over
  the legacy Grain node "in almost every case" — Grain exists purely for backward-compatible comps.
- Object Removal's Scene Analysis is not "set and forget": you must re-press **Scene Analysis** any time
  you change an Analysis-section parameter, or the result is stale.
- Groups vs. Underlay vs. Macro vs. Pipe Router are easy to conflate: Groups hide/collapse and restrict
  connections into the collapsed icon; Underlay only highlights and never restricts connections; Macro
  actually becomes a new reusable node type with its own exposed controls; Pipe Router is cosmetic wire
  routing only and never affects render time.
- A Fuse's script edits don't retroactively update sibling instances already in the comp — you must
  Reload each one or reopen the composition; and a comp always runs whatever Fuse script version was
  saved at open time.

## Recipes / workflows

1. **Basic 2D drop shadow** (Shadow node, p. 1064-1066): connect the alpha-bearing element to Shadow's
   Input; optionally feed a depth image to the Depth input and set Z Map Channel / Minimum Depth Map
   Light Distance; dial in Shadow Offset, Softness, Shadow Color, Light Position, and Light Distance;
   feed the Shadow node's output into a Merge's foreground with the real background on the Merge's
   background; place the original element above the shadow so it sits on top of its own cast shadow.
2. **Object Removal** (p. 1058, verbatim manual steps): (1) draw a polygon around the object to remove
   in a Polygon node; (2) track the polygon (manually or via tracker) so it stays on the object for the
   whole clip; (3) press **Scene Analysis** in the Object Removal Inspector. Adjust Scene Mode, Search
   Range, and Blend Mode if the result has fringing or blends poorly; re-run Scene Analysis after any
   parameter change.
3. **Custom Filter convolution recipes** (p. 1103-1105, verbatim matrices): identity `0 0 0/0 1 0/0 0 0`;
   soften `1 1 1/1 1 1/1 1 1`; emboss `-5 0 0/0 1 0/0 0 5`; simulated overexposure = soften matrix +
   positive Normalize; relief = `-1 0 0/0 0 0/0 0 1` + positive Floor Level.
4. **Repeating/array motion graphic** (Duplicate, p. 1041-1042 basic setup): feed a masked/shaped
   Background (or any 2D element) into Duplicate's Input; set Copies; set Center X/Y for per-copy
   offset, Size for per-copy scale, Angle for per-copy rotation (position the Pivot first if the array
   should rotate/scale around something other than its default pivot); open the Jitter tab and use
   Center/Axis/X Size/Angle/Gain/Blend with a Random Seed to break up uniform repetition.
5. **Watercolor / de-speckle** (Rank Filter, p. 1111): set **Size = 7** and **Rank = 0.7** for a
   watercolor-style look; use smaller Size values with Rank near the extremes to remove salt-and-pepper
   noise instead.
6. **Installing and iterating on a Fuse** (p. 1124): drop a `.fuse` text file into the platform Fuses
   folder (see Scripting section below); it appears in the Effects Library like a native node; select it
   in a comp and click **Edit** (top of Inspector) to open it in the Global Preferences > Scripting
   editor; after saving changes, click **Reload** on every existing instance (or close/reopen the comp)
   to propagate the update.

## Scripting and automation hooks

- **Node bracket abbreviations** — stated to be usable in the Select Tool dialog search and "in
  scripting references" for every node in this slice:

  | Node | Abbrev. | Node | Abbrev. |
  |---|---|---|---|
  | Duplicate | `Dup` | Grain | `Grn` |
  | Highlight | `HIL` | Light Trim | `LT` |
  | Hot Spot | `Hot` | Remove Noise | `RN` |
  | Object Removal | `ORm` | Create Bump Map | `CBu` |
  | Pseudo Color | `PSCL` | CreateReliefMap | `CRM` |
  | Rays | `CIR` | Custom Filter | `CFlt` |
  | Shadow | `SH` | Erode Dilate | `ErDl` |
  | Trails | `TRLS` | Filter | `Fltr` |
  | TV | `TV` | Rank Filter | `RFlt` |
  | Cineon Log | `Log` | Sticky Note | `NTE` |
  | Film Grain | `FGr` | Underlay | `UND` |
  | | | Fuses | `Fus` |

  (inference: the manual does not give the literal internal `AddTool`/registration ID string for these
  nodes in this slice — only the bracket abbreviation and display name are confirmed. Do not assume the
  abbreviation itself is the AddTool ID string.)
- **Custom node expression** (Cineon Log black-rolloff technique, p. 1081) — apply to Red, Green, and
  Blue channel expressions in a Custom node: `if (c1< 1e-16, 1e-18 + (c1/1e-16)*(1e-16 - 1e-18), c1)`.
- **File paths**:
  - Fuses path map: `Fusion:\Fuses`.
  - Fuses default folder, macOS: `Users/User_Name/Library/Application Support/Blackmagic Design/Fusion
    (or DaVinci Resolve)/Fuses`.
  - Fuses default folder, Windows: `C:\Users\User_Name\AppData\Roaming\Blackmagic Design\Fusion (or
    DaVinci Resolve)\Fuses`.
  - Fuse files must use the **`.fuse`** extension.
  - Title-macro folder (to surface in Resolve's Edit-page Effects Library), macOS: `Users/UserName/
    Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Titles`.
  - Title-macro folder, Windows: `C:\Users\UserName\AppData\Roaming\Blackmagic Design\DaVinci
    Resolve\Support\Fusion\Templates\Edit\Titles`.
  - Custom Filter presets live in a "Filters directory," loadable via right-click header > Settings >
    Load (exact path not stated in this slice).
- **UI location for Fuse editing**: the script editor used by the Inspector's **Edit** button on a Fuse
  is whichever editor is set in **Global Preferences > Scripting**.
- **Keyboard/mouse shortcuts stated in this slice**:
  - `Shift-Spacebar` opens the Select Tool search dialog (used e.g. to find Sticky Note).
  - `Option/Alt-click` on a connection line inserts a Pipe Router.
  - `Option-click` (Mac) on an Underlay's title bar selects the Underlay alone, without its contained
    nodes (needed before Rename).
  - Click-and-hold-drag on Highlight's Color Scale **Pick** button samples a color directly from the
    viewer.
- **Every tool in Effect/Film/Filter categories** exposes 3 **Scripts** edit-box fields on its Settings
  tab, executed when the tool renders (no further syntax given in this slice — "consult the Fusion
  scripting documentation").
- **Reload button**: present in every individual Fuse node's Inspector; forces that instance to pick up
  the currently saved script file.
