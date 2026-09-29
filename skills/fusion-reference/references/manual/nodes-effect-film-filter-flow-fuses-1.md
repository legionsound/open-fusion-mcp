<!-- nodes-effect-film-filter-flow-fuses.md part 1 of 2; index: nodes-effect-film-filter-flow-fuses.md -->
# Effect, Film, Filter, and Flow Nodes, and Fuses

Scope: manual pages 1040-1124 (Fusion 21.1 Reference, Chapters 38-43). Use when: building motion-graphics
repetition arrays (Duplicate), lens/light effects (Highlight, Hot Spot, Rays, Pseudo Color), drop shadows
and ghost trails (Shadow, Trails), analog-TV looks, film emulation (Cineon Log, Film Grain, Grain, Light
Trim, Remove Noise), convolution/morphological filters (Create Bump Map, CreateReliefMap, Custom Filter,
Erode/Dilate, Filter, Rank Filter), comp organization (Sticky Note, Underlay, Groups, Macro, Pipe Router),
or Lua-scripted Fuse plugins.

## Mental model

1. Every node in these chapters follows the same input pattern: **Input** (orange, required primary
   2D image) + **Effect Mask** (blue, optional; a mask made of polylines/primitive shapes/paint
   strokes/bitmaps). The Effect Mask is always applied **after** the tool processes — it crops the
   result, it does not pre-limit computation (exception: Highlight's separate white Highlight Mask,
   see below).
2. Nodes in the Effect, Film, and Filter categories share one "Settings tab" common-controls family
   (Blend, RGBA selector, mask handling, Clipping Mode, Use GPU, Motion Blur, Comments, Scripts). It is
   documented once below and referenced from every node entry as "Common Controls."
3. A second, easy-to-confuse RGBA control exists on some Controls tabs (Custom Filter, Erode/Dilate,
   Filter node): it skips a channel from processing entirely (faster render), vs. the Settings-tab RGBA
   selector which processes all channels then copies the untouched channel back over the result
   (slower, same visual outcome except for tools with side effects).
4. Duplicate and Trails share **identical** Apply Mode / Operator / Subtractive-Additive / Alpha Gain /
   Burn In math — document it once (under Duplicate) and reuse it for Trails.
5. "Copies" logic in Duplicate is chained, not parallel: each copy is a transform of the *previous*
   copy, not of the original — this compounds size/angle/gain effects across the array.
6. Fusion's node-name bracket abbreviation (e.g. `[Dup]`, `[SH]`, `[Fus]`) is stated by the manual to be
   usable both in the Select Tool dialog search and "in scripting references" — treat it as the
   searchable/scripting shorthand for that node type.
7. Shadow, Trails, and Film Grain/Grain all depend on an image buffer or Alpha channel from the
   upstream node — a bad or absent Alpha channel is the most common reason these "don't do anything."
8. Groups, Macro, Pipe Router, Underlay, and Sticky Note are comp-*organization* tools, not image
   operations — Groups hide, Underlay highlights without hiding or restricting connections, Macro turns
   a node cluster into a true reusable custom node, Router only reroutes wire geometry.
9. Fuses are Lua-script plugins, edited live and recompiled on the fly (no OFX build step), but that
   convenience trades away performance versus an equivalent compiled OFX node.
10. Log/Cineon-space math breaks down at or near zero (log of 0/negative is undefined) — Fusion clips
    values below 1e-38 to 0; this matters when scripting custom black-level ramps in Cineon Log.
11. Coordinates and offsets in these nodes are frequently expressed relative to image width (e.g.
    Duplicate's Center X offset of 1 = one full image width; Erode/Dilate's Amount of 1 = full image
    width) — always convert "N pixels" to a fraction of image width when scripting exact values.
12. "Common Controls" sections are **not identical** across the three categories: Effect lists Clipping
    Mode with only Frame/None; Film lists Frame/Domain/None; the Filter chapter's Common Controls text
    in this slice does not mention Clipping Mode at all. Don't assume symmetry across categories.

## Common Controls (Settings tab) — Effect / Film / Filter categories

Documented once here (first full statement, Effect chapter, p. 1075-1077); node entries below just say
"Common Controls: Settings tab" and reference this section. Variations by category are called out inline.

- **Blend**: blends the tool's original input against its final output. At 0.0 the tool is skipped
  entirely and the input is passed straight through (p. 1075).
- **Process When Blend Is 0.0**: forces the tool to still process at Blend 0.0 — useful when the node
  is scripted to trigger a side effect regardless of blend (p. 1076).
- **Red/Green/Blue/Alpha Channel Selector**: 4 buttons limiting the effect to chosen channels. This
  filtering is applied *after* the tool processes (e.g. deselecting Red on a Blur blurs everything, then
  copies the original Red channel back over the result). Exception: tools that expose an identical RGBA
  button set on their own Controls tab (Custom Filter, Erode/Dilate, Filter node) instead skip that
  channel *before* processing, for speed (p. 1076, 1094, 1102-1103).
- **Apply Mask Inverted**: inverts the combined mask channel (all masks connected to/generated in the
  node) (p. 1076).
- **Multiply by Mask**: multiplies RGB by the mask channel's values, forcing all pixels outside the mask
  to black/transparent (p. 1076).
- **Use Object / Use Material** (checkboxes): use an EXR file's Object ID / Material ID channels as a
  mask source, if present. **Correct Edges** appears only when one of these is on; it uses Coverage +
  Background Color channels to clean up overlapping-object edges (else aliasing can occur). **Object
  ID / Material ID** sliders pick which ID is used; a Sample button grabs an ID from the viewer like a
  color picker (p. 1076, 1094, 1102, 1113).
- **Clipping Mode** (governs domain-of-definition/DoD edge handling, matters most for blur/softness that
  samples outside the current DoD):
  - Effect chapter: **Frame** (default; DoD = full frame; area beyond upstream DoD = black/transparent)
    and **None** (no source clipping at all; still black/transparent beyond upstream DoD) (p. 1077).
  - Film chapter: **Frame** (default, same as above), **Domain** (respects the upstream DoD — can cause
    adverse clipping with large filters), **None** (no clipping) (p. 1095).
  - Filter chapter Common Controls text in this slice does not list a Clipping Mode control.
- **Use GPU**: Disable / Enabled / Auto (Auto uses a capable GPU if available, else falls back to
  software) (p. 1077, 1095, 1113).
- **Motion Blur family** (stated for Effect and Filter chapters, not present in this slice's Film Common
  Controls text): **Motion Blur** toggle (uses predicted motion from the virtual camera shutter);
  **Quality** (samples per side of actual motion — e.g. 2 = two samples each side; higher = smoother,
  slower); **Shutter Angle** (360 = one full frame exposure equivalent; higher = more blur/render time,
  values >360 allowed for stylized effects); **Center Bias** (shifts the blur's center position, usable
  to build motion-trail looks); **Sample Spread** (reweights samples, affects sample brightness)
  (p. 1077, 1113-1114).
- **Comments**: free-text note field; shows a red square (full tile) or a text-bubble icon (collapsed
  node); hover for tooltip (p. 1077, 1095, 1114).
- **Scripts**: 3 scripting edit-box fields per tool, on every tool's Settings tab, executed at render
  time (p. 1077, 1095, 1114).

---

## Effect Nodes (Chapter 38)

### Duplicate [Dup]
Replicates a 2D image N times with a per-copy transform, creating repeating patterns/arrays — the
primary motion-graphics repetition tool (compare to the separate Duplicate 3D node). Jitter tab adds
per-copy randomization (position, rotation, size, color/blend).
- Inputs: **Input** (orange, primary 2D image); **Effect Mask** (blue, limits where duplicated objects
  appear; applied after processing) (p. 1041).
- Controls tab (p. 1042-1046):
  - **Copies** — number of copies. Chained, not parallel: copy 2 is a copy of copy 1, copy 3 of copy 2,
    etc., so per-copy transforms compound down the chain.
  - **Time Offset** — offsets any upstream animation per copy (e.g. -1.0 shows each successive copy one
    frame earlier than the last; useful for showing successive frames of a clip on duplicated planes).
  - **Center** (X/Y) — per-copy position offset; units are relative to image width (X offset of 1 = one
    full image width per copy).
  - **Pivot** — pivot point for per-copy size/position/angle changes. Does not auto-follow the original
    object or the array; must be manually adjusted to "follow" the array.
  - **Size** — per-copy scale.
  - **Angle** — per-copy Z rotation; linear, based on Pivot location (centered pivot vs. offset pivot
    give visibly different results, shown in manual figures).
  - **Apply Mode** (how overlapping copies blend; also used identically by Trails, see below):
    | Mode | Behavior |
    |---|---|
    | Normal (default) | Uses fg Alpha as mask; reveals an **Operator** submenu (Over/In/Held Out/Atop/XOr) |
    | Screen | Multiplies color values, ignores Alpha, layer order irrelevant, result always lighter (like projecting film frames together) |
    | Dissolve | Averages overlapping objects |
    | Multiply | Darkens as if scaling 0-1; white=no change, gray=half brightness |
    | Overlay | Multiplies/screens fg depending on bg color; preserves bg highlights/shadows |
    | Soft Light | Diffused-spotlight-style darken/lighten by bg color |
    | Hard Light | Harsh-spotlight-style multiply/screen by bg color |
    | Color Dodge | Fg color brightens bg (photographic dodge analogy) |
    | Color Burn | Fg color darkens bg (photographic burn analogy) |
    | Darken | Picks the darker of fg/bg per channel |
    | Lighten | Picks the lighter of fg/bg per channel |
    | Difference | Subtracts fg/bg (direction depends on which is brighter); white inverts, black = no change |
    | Exclusion | Like Difference but lower contrast |
    | Hue | Result = bg luminance+saturation, fg hue |
    | Saturation | Result = base luminance+hue, blend saturation |
    | Color | Result = bg luminance, fg hue+saturation (good for colorizing monochrome) |
    | Luminosity | Result = bg hue+saturation, fg luminance (inverse of Color mode) |
    (p. 1043-1044)
  - **Operator** (visible only when Apply Mode = Normal): formula is always
    `result = (fg * x) + (bg * y)`:
    - Over: `x=1, y=1-[fg Alpha]`
    - In: `x=[bg Alpha], y=0`
    - Held Out: `x=1-[bg Alpha], y=0`
    - Atop: `x=[bg Alpha], y=1-[fg Alpha]`
    - XOr: `x=1-[bg Alpha], y=1-[fg Alpha]` (p. 1044-1045)
  - **Subtractive/Additive** — slider blending between Additive compositing (for premultiplied fg,
    default assumption) and Subtractive compositing (for non-premultiplied fg). Additive on a
    non-premultiplied image lightens edges; Subtractive on a premultiplied image darkens edges — blend
    the slider to tune edge brightness (p. 1045).
  - **Gain**: Gain RGB linearly multiplies channel values (black unaffected); **Alpha Gain** linearly
    scales the fg Alpha, reducing how much it obscures the background (brightens result); with
    Subtractive/Additive = Additive and Alpha Gain = 0.0, fg pixels are simply added to bg. In
    Subtractive mode, Alpha Gain controls composite density like Blend. All Gain values compound with
    the number of duplications (p. 1045).
  - **Blur**: Lock Blur (default on, symmetrical X/Y), Blur (amount does NOT compound with duplication
    count), Glow, Blend (mixes more of the original as it nears 0), RGBA Scale (per-channel blur
    strength) (p. 1046).
  - **Burn In**: 0.0 = straight Alpha blend; 1.0 = fg effectively added onto bg (post Alpha-mult if
    Subtractive) — brightens objects behind, same result as decreasing Alpha Gain for Additive blends
    (p. 1046).
  - **Blend** (Controls-tab, distinct from the Common Settings Blend): fades the *last* object first,
    then the penultimate, etc.; range 0-1, 1 = all copies fully opaque, 0 = only the original shows
    (p. 1046).
  - **Merge Under**: reverses layer order — last copy becomes bottommost (p. 1046).
- Jitter tab (p. 1046-1047): **Random Seed** + Reseed button (two nodes, same settings, different seed
  = different result); **Center X/Y** (position variation); **Axis X/Y** (variation in rotational pivot
  center — affects only jitter rotation, not Controls-tab rotation); **X Size** (scale variation);
  **Angle** dial (Z-rotation variation); **Gain** RGBA (random per-channel multiply); **Blend**
  (randomizes the inter-object blend).
- Common Controls: Settings tab (see above).
- Gotchas: copies chain multiplicatively, so Gain/Size/Angle effects compound with Copies count; Blur
  amount is the one control on this node that explicitly does *not* compound.

### Highlight [HIL]
Star-shaped highlights/glints in bright regions, similar to a lens star filter.
- Inputs: **Input** (orange); **Effect Mask** (blue, post-process, standard behavior); **Highlight
  Mask** (white) — a *pre*-mask: the image is filtered before the highlight is applied, then merged
  back over the original. Unlike a normal Effect Mask, it does **not** crop off highlights that extend
  past the mask's edges (p. 1048).
- Controls tab (p. 1049): **Low/High** (Luminance range that generates highlights; below Low = none,
  above High = full effect); **Curve** (drop-off shape — higher = flares fall off nearer center, lower =
  farther); **Length** (flare length); **Number of Points** (flare count); **Angle** (rotates
  highlights); **Merge Over** (on = overlay on original image; off = highlights-only output, useful for
  downstream color correction of just the highlights).
- Color Scale tab (p. 1049): Pick button (click-hold-drag over viewer to sample a color); **Red/Green/
  Blue Scale** (per-channel falloff color); **Alpha Scale** (falloff transparency).
- Common Controls: Settings tab.

### Hot Spot [Hot]
Lens flare, spotlight, and burn/dodge effects (simulates bright light sources reflecting inside a
camera lens).
- Inputs: **Input** (orange, required); **Effect Mask** (blue); **Occlusion** (green) — an image whose
  channel provides an occlusion matte; white pixels fully occlude the hot spot ("wink"), gray pixels
  partially suppress it (p. 1050).
- Hot Spot tab (p. 1051-1052): **Primary Center X/Y** (position; secondary elements/reflections are
  positioned relative to this); **Primary Strength** (brightness); **Hot Spot Size** (diameter, 1.0 =
  full image width); **Aspect** (1.0 = circular; >1 elongates horizontally, <1 vertically); **Aspect
  Angle** (rotates primary); **Secondary Strength**/**Secondary Size** (the secondary hot spot is a
  reflection, always on the opposite side of the image from the primary); **Apply Mode**: Add (Burn,
  brightens), Subtract (Dodge, dims), Multiply (Spotlight — isolates a lit area, darkens the rest);
  **Occlude** (selects which channel of the Occlusion input drives the matte: Alpha/R/G/B); **Lens
  Aberration**: In/Out (elongates toward center/toward corners), Flare In/Flare Out (severity increases
  near center / near edges), Lens (ringed-lens emulation); **Aberration** (overall strength slider).
- Color tab (p. 1052-1054): **Color Mode**: None (static curve), Animated Points (keyframe the spline
  curves per-frame), Dissolve (obsolete, compatibility only). **Color Channel and Mix** checkboxes
  enable editing of R/G/B/A splines and the Mix spline. **R/G/B/A Splines**: mini spline editor;
  horizontal axis = position along the hot spot's radius (left outside edge to right inside edge),
  vertical = channel intensity; default = linear falloff. **Mix Spline**: horizontal axis = position
  around the circumference (0 = 0°, 1.0 = 360°), vertical = blend of Radial vs. Color hot spot (0 = all
  radial, 1.0 = all color). Right-click in the spline/LUT area for a curve-editing contextual menu.
- Radial tab (p. 1054-1055): **Radial On** (enables radial splines; if off, the Mix spline in Color tab
  has no effect); **Radial Mode**: No Animation (static) / Animated Points (keyframe by moving frame +
  editing spline) — Interpolated Values option is obsolete; **Radial Length** and **Radial Density**
  splines (horizontal = position around circumference 0-360°; Length = radius of light along the
  circumference, Density = brightness along it); **Radial Repeat** (repeats the spline's effect N times
  around the circle, e.g. 2.0 = spline acts over 0-180° then repeats 180-360°); **Length Angle**/
  **Density Angle** (rotate the respective spline's effect around the circumference).
- L1/L2/L3 tabs — Lens Reflect (p. 1055-1056): 3 checkboxes each enable a *pair* of lens-reflection
  elements. **Element Strength**, **Element Size**, **Element Position** (distance from the axis, where
  the axis = line between hot-spot position and image center). **Element Type**: Circular (soft-edge
  circle), Soft Circular (very soft edge), Circle (hard edge), NGon Solid (filled variable-sided
  polygon), NGon Star (soft star, variable sides), NGon Shaded Out (soft circular), NGon Shaded In
  (variable-sided polygon, very soft reversed dark-center/bright-radius look), NGon Angle (rotation),
  NGon Sides (# sides, for star/shaded types), NGon Starriness (higher = more star-like). Lens Color
  Controls pick the reflection tint from the displayed image or RGBA sliders.
- Common Controls: Settings tab.

### Object Removal [ORm]
Uses the DaVinci Neural Engine to auto-remove an object — best for a moving object over a temporally
stable background, or lens dirt with camera motion; smaller objects work better than larger ones
(p. 1057).
- Inputs: **Input** (orange, footage to remove object from); **Clean Plate** (magenta, optional, used
  if Clean Plate Source = External); **Mask** (green, a polygon/ellipse/rectangle drawn around the
  object); **Effect Mask** (blue, optional, standard post-process mask) (p. 1057).
- Setup (numbered steps from the manual, p. 1058):
  1. Draw a polygon around the object to remove, in a Polygon node.
  2. Track the polygon (manually or with a tracker) so the object stays inside its boundary for the
     whole clip.
  3. Press **Scene Analysis** in the Object Removal controls.
- Controls (p. 1059-1060): **Show Mask Overlay** (mask highlighted in red). Analysis: **Scene
  Analysis** button (must be re-pressed after any parameter change in this section); **Assume No
  Motion** (locked-off camera simplification); **Scene Mode**: Background (analyzes entire image except
  the object region), Boundary (analyzes the surrounding boundary area), Object (for an object moving
  with the background, e.g. a window sticker while the camera moves); **Analysis Boundary** (object
  boundary size for analysis); **Show Scene Mask Overlay**. Render: **Search Range** (distance in
  frames the plugin searches for replacement detail — e.g. Search Range 20 = ±20 frames = 40 total;
  fringing on some frames → adjust this; use the smallest range that gives an acceptable result);
  **Blend Mode**: Linear (default, simple cloning) or Adaptive Blend (better except when the patch
  edges differ in color/brightness from the background). Clean Plate: **Clean Plate Source**: Gray
  Image (no source), Internal ("best guess" background generation, integrates successfully filled
  frames), External (connect your own plate to the pink input); **Build Clean Plate** button; **Show
  Clean Plate**.
- Common Controls: Settings tab.

### Pseudo Color [PSCL]
Produces color variance based on generator waveforms (static or animated).
- Inputs: **Input** (orange); **Effect Mask** (blue) (p. 1060).
- Four identical R/G/B/A tabs (p. 1061-1062): **Color** checkbox (enable this channel); **Wrap**
  (wraps out-of-range waveform values to the opposite extreme); **High/Low** (range affected in this
  channel); **Soft Edge** (softness of the color transition); **Waveform**: Sine, Triangle, Sawtooth,
  Square; **Frequency** (occurrence rate); **Phase** (animate for color-cycling effects); **Mean**
  (waveform level — raises channel brightness up to the allowed max); **Amplitude** (overall waveform
  power).
- Common Controls: Settings tab.

### Rays [CIR]
A modified zoom-blur effect radiating through an object from a specified point. Works best with an
Alpha channel present to define where rays emit from (p. 1062).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Controls (p. 1063): **Center X/Y** (light-source position, plus viewer crosshair); **Blend** (% of
  original blended with the rays); **Decay** (ray length); **Weight** (ray falloff); **Exposure** (ray
  intensity); **Threshold** (luminance limit above which rays are produced).
- Common Controls: Settings tab.

### Shadow [SH]
Versatile 2D drop-shadow generator, based on the source's Alpha channel; an optional depth matte can
distort the shadow by depth. **NOTE (manual)**: this node is for simple 2D drop shadows only — for full
3D shadow casting, use a Spot Light node + Image Plane 3D node (p. 1064).
- Inputs: **Input** (orange, primary 2D image w/ Alpha — the shadow source); **Depth** (green, extracts
  a depth matte from a chosen channel; used with Light Position/Distance); **Effect Mask** (blue, limits
  the area the shadow appears) (p. 1064).
- Basic Node Setup (p. 1064): Shadow node output feeds the foreground of a Merge; the shadow shows over
  the background input to that Merge (e.g. Shadow-from-MediaIn2 shown over MediaIn1).
- Controls tab (p. 1065-1066): **Shadow Offset** (X/Y position; adjustable via viewer crosshair when
  node is selected); **Softness** (edge blur — "most realistic shadows are usually not totally black
  and razor sharp"); **Shadow Color**; **Light Position** (position of the light relative to the
  shadow-casting object; only used when Light Distance is not set to infinity/1.0); **Light Distance**
  (varies apparent light distance between infinity/1.0 and zero; produces the realistic effect of
  farther shadow parts being longer than closer parts); **Minimum Depth Map Light Distance** (active
  only with a Depth input connected — controls how much the depth map contributes to Light Distance;
  dark depth-map areas make the shadow deeper, white areas bring it closer to camera); **Z Map
  Channel** (selects which channel of the Depth input drives the depth map: RGB and A, Luminance, or
  Z-buffer); **Output** menu: image-with-shadow, or shadow-only (useful for grading/perspective work
  before re-merging).
- Common Controls: Settings tab.
- **Recipe — basic drop shadow** (structure per Basic Node Setup, p. 1064):
  1. Connect the alpha-carrying element to the Shadow node's Input.
  2. (Optional) connect a depth image to the Depth input; set Z Map Channel and Minimum Depth Map Light
     Distance to taste.
  3. Adjust Shadow Offset, Softness, Shadow Color, Light Position/Distance.
  4. Connect the Shadow node's output to a Merge's foreground; connect the actual background plate to
     the Merge's background.
  5. Connect the original alpha-carrying element to a second Merge (or the same Merge chain) above the
     shadow so the object sits on top of its own shadow.

### Trails [TRLS]
Ghost-like after-trail from a moving image; unlike directional blur, only the *preceding* motion is
shown. Based on an image buffer, so it requires pre-roll (playing/activating for some frames) before
the effect is visible (p. 1066).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Setup: the **Reset** button must be pressed in the Inspector between previews or trails accumulate
  (p. 1067).
- Controls tab (p. 1067-1069): **Restart** (clears the image buffer to a clean frame); **Preroll**
  (pre-renders N frames, slider); **Reset/Preroll on Render** (resets on preview/final-render init, then
  pre-rolls the designated frame count); **This Time Only** (pre-roll uses only the current frame, not
  previous ones); **Preroll Frames** (# frames to pre-roll); **Lock RGBA** (when on, Gain is one control;
  off = independent per-channel Gain for tinting); **Gain** (buffer intensity/brightness — lower = short
  faint trail, higher = long solid trail); **Rotate** (rotates the buffer image before merging with the
  current frame; offset compounds between trail elements; the pivot stays over the original object, not
  per-element); **Offset X/Y** (independent-axis buffer offset before merge, compounds between
  elements); **Lock Scale X/Y** (independent X/Y scaling when on); **Scale** (resizes buffer image
  before merge, compounds between elements); **Lock Blur X/Y** (independent per-axis blur); **Blur
  Size** (blurs trails in the buffer before merge, compounds between elements).
  - **Apply Mode** / **Operator** / **Subtractive-Additive** / **Alpha Gain** / **Burn In**: identical
    controls and math to Duplicate's (see Duplicate above for the full mode list and the `(fg*x)+(bg*y)`
    operator formulas) (p. 1069-1071).
  - **Merge Under**: places the current image under the generated trail (reverse of usual), and also
    reverses the trailing layer order so the last trail is topmost (p. 1071).
- Common Controls: Settings tab.
- Gotcha: expect a black/empty result on the very first frames after adding or resetting Trails — it
  needs pre-roll frames before ghosting appears.

### TV [TV]
Simulates analog-TV broadcast flaws (scan lines, roll bars, noise). Manual notes it is mostly obsolete
in DaVinci Resolve given the more advanced Analog Damage ResolveFX (p. 1072).
- Inputs: **Input** (orange); **Effect Mask** (blue).
- Controls tab (p. 1073): **Scan Lines** (0 = off; 1/default = drops every 2nd line; 2 = show 1 line,
  drop next 2, repeat); **Horizontal**/**Vertical** (simple offsets); **Skew** (diagonal offset;
  positive = skews top-left, negative = top-right; off-frame pixels wrap around); **Amplitude** (sine
  deformation intensity at image edges); **Frequency** (sine-wave repeat rate, visible once Amplitude
  > 1); **Offset** (moves the sine wave's position, sweeping the deformation across the image).
- Noise tab (p. 1073-1074): **Power** (>0 introduces noise, higher = stronger); **Size** (scales the
  noise map); **Random** (thumbwheel; 0 = static noise map, animate to change frame-to-frame).
- Roll Bar tab (p. 1074): **Bar Strength** (0 = no bar/default; higher = darker bar); **Bar Size**
  (taller bar); **Bar Offset** (animate to scroll the bar).
- Common Controls: Settings tab.

---

