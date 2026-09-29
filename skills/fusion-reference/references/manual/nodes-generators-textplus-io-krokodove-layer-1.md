<!-- nodes-generators-textplus-io-krokodove-layer.md part 1 of 2; index: nodes-generators-textplus-io-krokodove-layer.md -->
# Fusion 21.1 Generator, I/O, Krokodove, Layer and LUT Nodes
Scope: Fusion Page Effects manual pp. 1125-1230 (Ch. 44 Generator Nodes incl. Text+ and its modifiers, Ch. 45 I/O Nodes, Ch. 46 Krokodove, Ch. 47 Layer Nodes, Ch. 48 LUT Nodes). Use when: building or advising on titles/Text+ animation, procedural backgrounds and noise, getting media in and out of a comp (MediaIn/MediaOut/Loader/Saver), multilayer EXR/PSD layer management, Krokodove tool selection, or LUT creation/application.

## Mental model

1. **Generators make pixels from nothing.** Background, Day Sky, Fast Noise, Mandelbrot, Plasma, Text+, MultiText have no image input, only a blue Effect Mask (Fast Noise adds two map inputs). Their resolution, bit depth, pixel aspect and time range come from the shared **Image tab** (Use Frame Format Settings, Width/Height, Depth, Global In/Out) (p. 1170).
2. **Text+ is a 2D image generator, not 3D geometry.** For extruded/beveled text use Text 3D (p. 1150). Text+ does fake 3D (Angle X/Y/Z, Perspective, Z offsets) inside a 2D render.
3. **Text+ has three stacked transform levels:** Layout tab (whole text block: Center, Size, Perspective, Rotation/Angle) -> Transform tab (per Character, Word or Line: Spacing, Pivot, Rotation, Shear, Size) -> Shading tab (per shading element: Offset, Pivot, Rotation, Shear, Size) (pp. 1156-1162).
4. **Text+ look = up to 8 shading elements** layered by priority (1 = top, 8 = bottom) or by Z. Each element is a Text Fill, Text Outline, Border Fill or Border Outline, colored Solid, Gradient or Image, with its own softness and transform (pp. 1158-1162). Shadows, glows, boxes and outlines are all built from these elements.
5. **Text+ size is relative to image width**, not points (p. 1152). Tab positions run -0.5 to 0.5 with 0 at center (p. 1154). Treat Text+ positions as normalized frame coordinates.
6. **Per-character animation lives in text modifiers**, which you add by right-clicking the Styled Text box: Follower, Character Level Styling, Text Scramble, Text Timer, Time Code, Comp Name. Their controls appear in the Inspector **Modifiers** tab. With Follower, values you set take effect only when **keyframed** (pp. 1164-1167).
7. **Resolve vs Fusion Studio I/O.** In DaVinci Resolve, MediaIn/MediaOut are the real I/O. **In Resolve, Loader only imports EXR and Saver only exports EXR** (pp. 1176, 1192). Every Resolve comp needs a MediaOut. The first MediaOut returns the image to the timeline, and extra MediaOuts pass mattes to the Color page (p. 1189).
8. **Color tagging is not conversion.** Source Color Space / Color Space Type on generators, Loader and MediaIn only writes metadata when none exists. Remove Curve linearizes. On Saver, Color Space/Curve Type + Apply Curve convert only the file written to disk, not the comp (pp. 1171, 1182, 1195).
9. **Clip timing** (Loader, MediaIn, OGrafLoader): Global In/Out places the clip in comp time; shrinking auto-adjusts Trim, extending auto-adds Hold First/Last Frame (green in the range bar). Trim values are frame offsets; Loop includes holds and trims (pp. 1146-1147, 1177-1179).
10. **Layer nodes (Ch. 47) handle multilayer images** (multi-part EXR, PSD layers, multi-video-layer Fusion Clips). They merge, filter/rename by regex, strip, or build layers and Aux channels. Every multilayer stream has a **Default/[Main] layer** (pp. 1208-1221).
11. **Krokodove** is the formerly third-party toolset, now built into Resolve and Fusion. It spans image tools, color, pixel, warp, shape tools (`s` prefix), region tools (`r` prefix), 3D creators, and animation/text modifiers (pp. 1202-1207).
12. **LUT nodes:** File LUT references a LUT file by path, so the comp stores only the path. The Cube workflow runs LUT Cube Creator -> any grading nodes -> LUT Cube Analyzer (writes a 3D LUT file) or LUT Cube Apply (applies live without a file) (pp. 1222-1229).

## Common controls (documented once; referenced below)

### Generator Image tab (Bg, DS, FN, MAN, PLAS, TXT+, MTxT) (pp. 1170-1171)
| Control | Behavior |
|---|---|
| Process Mode | Fields processing. Default follows the **Has Fields** checkbox in Frame Format prefs. |
| Global In / Out | Frame range (inclusive) where the node outputs an image. No image outside it. |
| Use Frame Format Settings | Locks Width/Height/Pixel Aspect to the comp Frame Format prefs, which change with it. Turn off to build at a different resolution than the final target. |
| Width / Height | Output dimensions. |
| Pixel Aspect | 1:1 square. 0.9:1 is the NTSC-like example. Right-click Width, Height or Pixel Aspect for a menu of Frame Format presets. |
| Depth | Bit depth. 32-bit uses 4x the memory of 8-bit. Float permits values <0 and >1 (HDR). |
| Source Color Space | **Auto** (pass existing metadata) or **Space** (pick a Color Space Type). Metadata only, no conversion. It is consumed downstream by Gamut (From Image) or a Saver. |
| Source Gamma Space | Curve type: **Auto**, **Space** (Gamma Space Type menu), **Log** (Log/Lin settings like the Cineon tool). |
| Remove Curve | Removes the gamma curve, or does log-to-lin, giving linear output. |

Fast Noise also has the Noise Detail Map and Noise Brightness Map connections here (p. 1172).

### Settings tab (all generator nodes; same family on most tools) (pp. 1172-1174)
- **Blend** (0.0 normally skips processing; **Process When Blend Is 0.0** forces it, e.g. for render scripts). **R/G/B/A** selectors usually copy the original channel back after processing (tools that truly skip a channel repeat RGBA buttons on their Controls tab). **Apply Mask Inverted**, **Multiply by Mask**.
- **Use Object / Use Material** (EXR ID channels as mask) + **Correct Edges** (uses Coverage/Background Color channels) + Object/Material ID sliders with Sample.
- **Motion Blur**: Quality (samples each side), **Shutter Angle** (360 = full-frame exposure; higher allowed), Center Bias (trails), Sample Spread (sample weighting). **Use GPU**: Disable / Enabled / Auto. Comments; Scripts (3 edit boxes run at render).

### I/O node Settings tab (Loader, Saver, MediaIn, MediaOut) (pp. 1199-1201)
Same Blend/RGBA/mask/Object-Material family, plus **Hide Incoming Connections**. It hides input wires unless the node is selected, and the Inspector shows input fields you can drag nodes into. Comments, Scripts.

### Layer node and LUT node Settings (pp. 1220-1221, 1229-1230)
Layer nodes: Hide Incoming Connections, Comments tab (animatable), Scripting tab (manual calls these "Deep Image" settings, a copy artifact). LUT nodes: Use GPU, Hide Incoming Connections, Comments, Scripts.


## Generator nodes (Ch. 44)

### Background (Bg)
Solid color or gradient generator (p. 1126). Use it as a color plate, a gradient matte for Vari Blur and similar tools, or a paint canvas.
- Inputs: Effect Mask (blue) only.
- Color tab > **Type**: Solid Color (default), Horizontal (2-color), Vertical (2-color), Four Corner (4-color), **Gradient**. The manual lists "four selections" but then documents Gradient, so there are five (p. 1127).
- Horizontal/Vertical/Four Corner: two or four color swatches for left/right, top/bottom or the corners.
- Gradient mode controls (pp. 1128-1129):
  - **Gradient Type**: Linear, Reflect (mirrors the linear gradient around the start), Square, Cross, Radial, Angle (counterclockwise sweep). Square, Cross, Radial and Angle assume the start point sits at image center.
  - Start and End: two red viewer points joined by a green line.
  - Gradient Colors bar: click the bar's bottom edge to add a stop. Drag to move. **Cmd/Ctrl-drag copies** a stop. **Drag a stop up off the bar to delete** it. Select the triangle under a stop to edit it.
  - **Interpolation Space**: the color space used to interpolate between stops.
  - **Offset**: shifts the gradient relative to Start/End. Animate it for scrolling gradients.
  - **Repeat**: Once / Repeat / Ping-pong (behavior when Offset scrolls past the ends).
  - **Sub-Pixel**: precision for visible repeat edges or animated gradients. Higher values are slower.
  - Right-click the gradient bar for its menu: animate, publish, connect gradients, plus a gradient modifier that **samples colors from a node's output** (p. 1129).
- Image and Settings tabs: see Common controls.

### Day Sky (DS)
Physically based daylight **light map**, an implementation of Preetham, Shirley and Smits, "A Practical Analytical Model for Daylight". Per the manual it is **not a sky generator**. Combine it with a cloud generator or noise to make a sky (p. 1129).
- Inputs: Effect Mask.
- Controls tab: **Latitude**, **Longitude**; **Day**, **Month**, **Time**; **Turbidity** (haze/murk); **Do Tone Mapping** (on by default per the wording; turn it off only in a float pipeline that will be graded later); **Exposure** (for tone mapping) (p. 1131).
- Advanced tab: Horizon Brightness, Luminance Gradient (width of the horizon-to-sky transition), Circumsolar Region Intensity, Circumsolar Region Width, Backscattered Light (pp. 1131-1132).
- Gotcha: it is computed in 32-bit float with values far above 1.0 and below 0.0. Keep Depth at float if tone mapping is off.

### Fast Noise (FN)
Fast Perlin noise generator (p. 1132). Use it for clouds, fog, waves, water caustics, stylized fire and smoke, heat-shimmer sources, particle bitmaps and dirt maps. Use Plasma for circular-interference patterns and Mandelbrot for fractals.
- Inputs: **Noise Detail Map** (gray), a soft mask that gives zero detail where black and full detail where white, applied before color mapping. **Noise Brightness Map** (white): controls the noise map directly, and with Detail = 0 it **replaces the Perlin noise entirely**. **Effect Mask** (blue).
- Noise tab (pp. 1133-1134):
  - **Discontinuous**: hard discontinuity lines along contours, a very different look. **Inverted**: negative pattern, most effective with Discontinuous.
  - **Center**: pan the pattern.
  - **Detail**: adds octaves of finer noise without changing the overall pattern. Higher is slower and more natural.
  - **Brightness**: overall level before color mapping. In Gradient mode it acts like Offset.
  - **Contrast**: before color mapping. It widens the range of gradient colors used.
  - **Lock X/Y** + **Scale** (or separate X/Y Scale when unlocked, which suits a brushed-metal look).
  - **Angle**: rotate the pattern.
  - **Seethe**: interpolates toward a different noise map, giving a crawling/flowing shift. Must be keyframed to animate.
  - **Seethe Rate**: per-frame evolution rate that **animates automatically with no keyframes**.
- Color tab: **Two Color** (smooth two-color ramp) or **Gradient** (Advanced Gradient control) (p. 1135).
- Gotcha: the manual documents **no "seamless/tileable" option** for Fast Noise. For a seamless tile, Krokodove **Seamless** mirrors opposite edges (inference, p. 1205).

### Mandelbrot (MAN)
Mandelbrot-set fractal pattern for sci-fi or motion-graphics backgrounds (p. 1135).
- Inputs: Effect Mask.
- Noise tab: **Position X/Y** (seed point), **Zoom** (recalculated at every magnification, so no practical limit), **Escape Limit** (iteration abort threshold; low values give blurry halos), **Iterations** (animating it "grows" the set), **Rotation** (each angle recalculates) (p. 1136).
- Color tab: **Grad Method**: Continuous Potential (edges blend to background) or Iterations (solid edges). **Gradient Curve** (width of the pattern-to-background gradation). **R/G/B/A Phase and Repetitions** (pp. 1136-1137).

### Plasma (PLAS)
Four interfering circular patterns making plasma-like images. It is "similar to Fast Noise" and is recommended as a deform source for Shadow and Deform nodes (p. 1148).
- Inputs: Effect Mask.
- Circles tab: **Scale**, **Operation** (math used where the four circles intersect), **Circle Type**, **Circle Center**, **Circle Scale** (p. 1149).
- Color tab: **Phase** (whole-image color phase; animate it for psychedelic cycling), **R/G/B/A Phases** (per-channel cycling) (p. 1149).

### OGrafLoader (OGL)
Loader for **OGraf** (EBU open HTML5 broadcast-graphics spec) and **Lottie** files (pp. 1145-1147). Chapter-level info says OGraf is `.json` and Lottie is `.lottie`, alpha is preserved, and both can also be dragged in from the Media Pool (Ch. "OGraf HTML Graphics and Lottie Animations", p. 84 area).
- Inputs: Effect Mask only. The file path is the only requirement, and a file browser opens when the node is added.
- OGraf tab: **Global In/Out** (same auto-trim/auto-hold behavior as Loader), **Template Path** (browse or type; OGraf and Lottie only), **Trim** (offsets), **Time Scale** (speeds up or slows the animation and changes the Global Range to match), **Hold First/Last Frame**, **Loop**. There is **no Reverse**.
- **Scheduled Actions**: **Play** (frame where the animation starts playing) and **Stop** (frame where it stops). If the template has Ease In/Out animations, Play/Stop mark where those eases begin. For **single-step templates, Play only works if preceded by a Stop** (p. 1147).
- Image and Settings tabs: common.

### MultiText (MTxT)
Multi-layer title generator "based on the Text+ tool": several independent text layers in one node, with simpler shading (pp. 1137-1145).
- Inputs: Effect Mask.
- Viewer: double-click in the viewer to edit text. The toolbar has **Allow Typing in Viewer**, **Allow Manual Positioning** (kerning handles, same keys as Text+), and a three-way outline toggle (No Text Outline / Text Outline Outside Frame Only / Show Always Text Outline). A **Pivot Points** icon toggles Character/Word/Line pivots (pp. 1138-1139).
- Text tab (pp. 1140-1142):
  - **Text List**: master list of text layers. Enable/disable, lock, delete, rename.
  - **Add Text** buttons: **Point** (unconstrained), **Text Box** (constrained; Layout tab gains **Wrap to Text Box** and **Clip to Text Box**, where clip hides overflow without deleting it), **Circle** (text on an arc), **CSV** (imports a .csv spreadsheet as column-aligned text).
  - Font, Size, **Emphasis** (underline/strikethrough), Color, Tracking, **Align** (L/R/center + top/center/bottom), **Justify** (left, right, center, all), **Indent**, Line Spacing, then the same Direction/Line Direction/Reading Direction/Force Monospaced/kerning/ligature/Stylistic Set controls as Text+ Advanced, Manual Kerning/Positioning clear buttons, and **Merge** (Merge-node compositing settings per layer).
- Layout tab: **Type** Point / Text box / Circle (**no Path**, unlike Text+). Center X/Y/Z (X/Y on screen, Z slider), Pivot X/Y/Z, Size, Perspective, **Align Layer** (align horizontally or vertically to the frame boundary or title-safe margin; with several layers selected, a **Selection** option aligns relative to them), Rotation order + angle dials (p. 1143).
- Shading tab (fixed three blocks, not 8 elements) (pp. 1144-1145):
  - **Fill**: Enable, Color, Softness X/Y, Glow, Blend.
  - **Outline**: Enable, Color, Thickness, Adapt to Perspective, Outside Only, Join Style (Sharp/Rounded/Beveled), Line Style (solid, dashes, dots).
  - **Shadow**: Enable, Color, Position X/Y.
- **Page tab**: Layout (size/position of the page) + Background color behind the text layers. **Pure black background = transparent** (p. 1145).
- Image tab (aspect, color and gamma spaces) and Settings tab.

### Text+ (TXT+)
Fusion's main 2D title generator: multiple styles, fake-3D transforms, 8 shading layers, Point/Frame/Circle/**Path** layouts (p. 1150). Accepts any installed TrueType, OpenType or PostScript Type 1 font. Unicode/multibyte, RTL and vertical text are supported.
- Inputs: **Effect Mask** (blue) only, to crop the text.
- Output: 2D image with a transparent background by default (Layout > Background Color can fill it).

#### Text+ vs alternatives
| Need | Use |
|---|---|
| Per-character ripple animation, burn-ins, scramble, 8-layer shading, text on a path | **Text+** |
| Several independent text layers in one node, CSV tables, wrap/clip to box, layer alignment to title safe | **MultiText** |
| True extruded/beveled 3D text | **Text 3D** (Character Level Styling cannot go directly on Text 3D; copy Text+ then right-click Text 3D > Paste Settings) (p. 1164) |
| Imported broadcast graphic or Lottie animation | **OGrafLoader** |

#### Viewer controls and toolbar (pp. 1150-1151, 1162-1163)
- Enable in-viewer editing from the viewer's popup toolbar or the View right-click menu. With Text+ selected, **double-click in the viewer** to enter text-edit mode.
- **Allow Typing in Viewer**: type in the viewer. Click to place the cursor. Left/Right arrows move between characters and Up/Down between lines.
- **Allow Manual Kerning**: click the small **red handle under a character** (or drag a selection rectangle) to select it. **Option/Alt + Left/Right** nudges. **Option+Shift / Alt+Shift + arrows** moves in larger steps. To animate, right-click the **Manual Font Kerning** label (Text tab > Advanced Controls) > **Animate**. A key is added each time a character moves, and **all characters share one spline**, like polyline mask animation.
- **No Text Outline / Text Outline Outside Frame Only / Show Always Text Outline**: a three-way toggle for the on-screen (non-rendered) outline. "Outside Frame Only" helps find text that has moved off screen.
- **Pivot Points** toolbar icon: shows or hides the Character/Word/Line transform pivots.
- Depth sorting (p. 1151): **Z Position** mode sorts only on Z distance from camera (orientation ignored); **Distance** mode sorts on absolute camera distance. Use Z Position to layer overlapping text in depth.

#### Text tab: Text section (pp. 1152-1153)
| Control | Detail |
|---|---|
| **Styled Text** | Main edit box. OS clipboard shortcuts work. Emoji: **Ctrl-Cmd-Space** (macOS), **Win + .** (Windows). A multi-language spell checker marks errors red in the viewer and Inspector; right-click the word for suggestions. **Right-click menu**: Animate, Character Level Styling, Comp Name, Follower, Publish, Text Scramble, Text Timer, Time Code, Connect To. |
| **Font** | Two menus: family and typeface/style (Regular, Bold, Italic...). Font Browser icon beside them. |
| **Color** | Basic fill color. Same as the Shading tab element-1 swatch. |
| **Size** | **Relative to image width**, not point size. |
| **Tracking** | Uniform spacing between characters. |
| **Line Spacing** | Leading. |
| **V Anchor** | 3 buttons (top of text / middle / bottom **baseline**) + slider for custom values. Sets the rotation reference and where line-spacing changes pivot. Mostly used with Layout = Frame. |
| **V Justify** | Slider from the V Anchor alignment to full vertical justification (flush top and bottom). Mostly used with Frame. |
| **H Anchor** | 3 buttons (left / middle / right) + slider. Sets the rotation reference and where tracking changes pivot. Mostly used with Frame. |
| **H Justify** | Slider from the H Anchor alignment to full justification (flush left and right). Mostly used with Frame. |
| **Direction** | Write horizontally or vertically, in either direction (for Asian scripts during animation). |
| **Line Direction** | Line flow: top-to-bottom, bottom-to-top, left-to-right, right-to-left. |
| **Underline / Strikeout** | Emphasis buttons. |
| **Write On** | Range control (Start/End) for quick write-on and write-off. Manual: "Write On: animate End from 1 to 0. Write Off: animate Start from 0 to 1" (p. 1153). See Gotchas: a reveal is normally End 0 -> 1 (inference). |

#### Text tab: Tab Spacing (pp. 1153-1154)
- Eight tab stops. Tab characters typed or pasted into Styled Text snap to them.
- **Position**: -0.5 to 0.5, with **0 = frame center**. Shown in the viewer as a thin white vertical line with a draggable handle.
- **Alignment**: -1.0 (left) / 0.0 (center) / 1.0 (right). Clicking a tab handle in the viewer cycles the three states.

#### Text tab: Advanced Controls (pp. 1154-1155)
- **Reading Direction**: automatic or manual, LTR (English, German) or RTL (Arabic, Hebrew).
- **Force Monospaced**: 0 (default) uses the font's kerning. 1 gives fully even spacing.
- **Use Font Defined Kerning**: on by default.
- **Use Ligatures**: **None is the default for Latin** so animated letters stay separate. **All Scripts** enables ligatures (e.g. ff, fl). **Non-Latin** is required for Arabic and similar scripts.
- **Style Can Split Ligatures**: checkbox, if the font supports it.
- **Stylistic Set**: dropdown of the font's sets.
- **Font Features**: OpenType 4-letter tags, e.g. `smcp` (small caps), `frac` (1/2 as ½). Font support varies. The full list is in Microsoft's OpenType feature list.
- **Manual Font Kerning/Placement**: right-click the label to animate kerning (see toolbar).

#### Layout tab (pp. 1156-1157)
| Control | Detail |
|---|---|
| **Type** | **Point** (text around a center point), **Frame** (rectangular frame; anchor/justify controls work inside it), **Circle** (around a circle or oval; alignment picks inside or outside the edge and multi-line justification), **Path** (text along a path; reveals **Position on Path**). |
| Center X, Y, Z | X/Y are on screen. Z is a slider. |
| Size | Scale of the whole layout element. |
| Perspective | Adds or removes perspective from the Angle X/Y/Z rotations. |
| Rotation | Order buttons (e.g. XYZ) + Angle X/Y/Z dials. |
| Width / Height | Width shows for Circle and Frame. **Height only for Frame**. |
| Fit Characters | Circle only: how characters are spaced to fit the circumference. |
| **Position on Path** | Path only: position along the path. **Values <0 or >1 continue off the path** along the direction of its last segment. |
| Background Color | Output is normally transparent. This color picker sets a background. |
| Right-Click Here for Shape Animation | Path only: menu to connect the path to other paths or animate its shape (see the "Animating with Motion Paths" chapter). |

#### Transform tab (pp. 1157-1158)
Transforms applied **per text unit**. Line, word and character transforms can all be active at once. The menu only chooses which set is shown.
- **Transform**: Characters (each on its own center) / Words / Lines.
- **Spacing**: space between the chosen units. **<1 usually causes overlap**.
- **Pivot X, Y, Z**: an **offset** from the unit's calculated center. The manual says 0.1, 0.1 shifts the axis "downward and to the right". +Z moves the axis away from the viewer and -Z toward it.
- **Rotation**: order buttons (XYZ = X then Y then Z). **X, Y, Z**: angles.
- **Shear X/Y**: slant. **Size X/Y**: per-unit scale.

#### Shading tab: the 8 shading elements (pp. 1158-1162)
Each element is an independent layer of the text's look, with its own transform.

| Control | Detail |
|---|---|
| **Shading Element** | Selector 1-8. The rest of the tab edits the selected element. |
| **Enabled** | Per element. **Only element 1 (fill) is enabled by default.** An element's controls are hidden until it is enabled. |
| **Sort By** | **Priority** (1 = topmost ... 8 = bottommost) or **Z depth** from the element's Z position. |
| Name | Custom label for the element. |
| **Appearance** | **Text Fill** (default; fills the glyphs), **Text Outline** (outline of the glyph edges), **Border Fill** (fills a box around the text), **Border Outline** (outline of that box). Each shows different sub-controls. |
| **Opacity** | Element transparency. **Prefer it over lowering the color's Alpha.** |
| **Blending** | How overlaps between characters render: **Composite** (over itself), **Solid** (overlap opaque), **Transparent** (overlap cut out). |
| Thickness | Outline only. |
| Adapt Thickness to Perspective | Outline only. Thinner when far and thicker when near. More realistic for 3D-rotated text, but much slower. |
| Outside Only | Outline only. By default the outline is centered on the edge and overlaps the fill. This draws it outside only. |
| Join Style | Outline only: Sharp / Rounded / Beveled. |
| Line Style | Outline only: solid plus dash/dot patterns. |
| **Level** | Border Fill: box around the whole **Text**, each **Line**, each **Word**, or each **Character**. |
| Extend Horizontal / Extend Vertical | Border modes: box dimensions (padding). |
| Round | Border Fill and Border Outline: corner rounding. |
| **Color Types** | **Solid** (color picker), **Image** (texture from a node, clip or brush), **Gradient** (gradient bar; same stop editing as Background: click to add, drag to move, Cmd/Ctrl-drag to copy, drag up to delete). |
| Image Source | Image mode: **Tool** (the Color Image field names a node), **Clip** (browse to a media file), **Brush** (the Color Brush menu picks a Fusion paint-brush bitmap). |
| Color Image / Color Brush | Type the node name, **drag the node from the Node Editor into the field**, or right-click > Connect To. |
| Image Sampling | Image mode: **Pixel** (default, "sufficient for 90%"), **Area** (less aliasing, slower), **None** (fastest, lowest quality). |
| Image Edges | Image mode: how transformed image shading wraps off the text edges. |
| Shading Mapping | Image mode: stretch the whole image to fill, or scale to fit keeping aspect with cropping. |
| Mapping Angle / Size / Aspect | Image and Gradient modes: Z rotation / scale / vertical stretch of the texture or gradient. |
| **Mapping Level** | Image and Gradient modes: **Full Image**, **Text** (fit to the whole text), **Line**, **Word**, **Character** (one texture or gradient per character). |
| Softness X / Y | Blur of the element's source outline, independent in X and Y. |
| Apply Softness to Fill Color | Blurs the fill itself. Most visible with image-textured elements. |
| Softness Glow | Glow on the softened region. |
| Softness Blend | Mixes the softened result back with the original to tone it down. |
| **Priority Back/Front** | Only when Sort By = Priority. Overrides the order: slide right to bring forward, left to tuck behind. |
| **Offset X, Y, Z** | Element offset from the text's global center (Layout tab). The manual says X0.0, Y0.1 moves it 10% of the image "further down" the screen. +Z pushes the element away from the camera (the manual repeats "positive" for toward the camera, a typo). |
| Pivot X, Y, Z | Element rotation axis, as an offset from the calculated center. |
| Rotation X, Y, Z | Element angles. |
| Shear X / Y, Size X / Y | Element slant and scale. |

#### Text+ modifiers (right-click Styled Text) (pp. 1164-1169)
Controls appear in the Inspector **Modifiers** tab.

**Character Level Styling** (Text+ only)
- After it is applied, **select characters in the viewer**. They **cannot be selected in the Modifiers-tab Styled Text box**, which only mirrors the text.
- The Text tab formatting then applies only to the selected characters. **Clear Character Styling on Selection** and **Clear All Character Styling** reset them. The modifier also has Transform and Shading tabs, identical to Text+.
- Not directly usable on Text 3D. Copy the Text+, right-click the Text 3D, and choose **Paste Settings** (p. 1164).
- Fusion 21 refinement: character-level offsets and translations are more consistent across multiple separate selections, which reduces the need for manual positioning (p. 1151).

**Comp Name**: puts the composition name into Styled Text, for slates and burn-ins. No controls (p. 1165).

**Follower**: sequences (ripples) animation across characters (pp. 1165-1167).
1. Right-click Styled Text > **Follower**.
2. In the Modifiers tab's Text Controls, Alignment, Transform and Shading tabs, **keyframe** the parameters to animate. **Changing a value without a keyframe has no visible effect.**
3. **Timing tab**:
   - **Range**: all characters, or a selected range (drag-select characters in the viewer).
   - **Order**: Left to right, Right to left, Inside out (center outward, symmetric), Outside in, Random but one by one, Completely random (several at once), Manual curve (per-character sliders). **Spaces count as characters.**
   - **Delay Type**: **Between Each Character**. The value is frames between successive character starts (1 = each character starts 1 frame after the previous), so total time grows with text length. **Between First and Last Character**: total spread is fixed regardless of character count.
   - Clear All Character Styling.

**Text Scramble**: replaces characters with random ones (pp. 1167-1168).
- **Randomness** 0-1 (0 = none, 1 = all changed). Animate 0 -> 1 for a gradual scramble, or 1 -> 0 to resolve (inference).
- **Input Text**: the original text, editable here or in Text+.
- **Animate on Time**: re-scramble every frame. **Animate on Randomness**: re-scramble every frame while Randomness is animated. Both do nothing at Randomness 0.
- **Don't Change Spaces**: keeps word lengths. **Substitute Chars**: the pool of replacement characters.

**Text Timer**: turns Text+ into a clock (p. 1168).
- **Mode**: CountDown / Timer / Clock (Clock shows system time).
- Hrs/Mins/Secs **checkboxes** (which fields show) and **sliders** (start time for CountDown/Timer).
- **Start** (toggles to Stop) and **Reset**.
- It runs on real time, which suits live displays or burning in the frame creation time. It is not tied to comp frames (inference from "real-time displays").

**Time Code** (Text+ only): a frame-based counter for dailies burn-ins (p. 1169).
- Hrs, Mins, Secs, Frms, Flds toggles. **Frames only = a plain frame counter.**
- **Start Offset** (+/- to match existing TC), **Frames per Second** (must match the comp FPS), **Drop Frame**.

Other right-click entries: **Animate** (keyframe the text itself), **Publish** (share the text with other text nodes), **Connect To** (use another node's published text) (p. 1152).


