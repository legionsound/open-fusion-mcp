<!-- nodes-generators-textplus-io-krokodove-layer.md part 2 of 2; index: nodes-generators-textplus-io-krokodove-layer.md -->
## I/O nodes (Ch. 45)

### Loader (LD)
Fusion Studio's footage input. In Resolve it is **limited to EXR** (pp. 1176-1184).
- Added via Effects Library/toolbar (Studio), OS drag, or File > Import > Footage (Studio; makes a new comp). Opens a file dialog unless **Auto Clip Browse** is off (Global > General prefs).
- Inputs: Effect Mask (applied after the tool processes).
- **File tab**:
  - **Global In/Out**: placement in comp time. Shrinking auto-trims and extending auto-holds (green in the range bar). Drag the middle of the range bar, or type Global In, to slide without changing length.
  - **Filename**: browse or type, with path autocompletion (arrow keys pick matches). **Sequence detection**: if the last part of the name (before the extension) is numeric, the whole folder is scanned (`image.0001.braw`, `image151.exr` qualify; `shot.1.fg.jpg` does not). Any file in the sequence can be picked. Length runs from the first to the last number, and gaps are ignored, so `image.0001.exr` + `image.0100.exr` is a 100-frame clip. **Shift-drag** a file from the OS to load it as a single frame. The Trim In/Out context menu can force a clip length or rescan the folder.
  - **Proxy Filename**: appears once Filename is valid. It loads when comp Proxy mode is on. It must have the **same frame count and start/end numbers**, and the same format is strongly suggested (format options are inherited).
  - **Trim** (offsets: Trim In 5 starts at the 5th frame; Trim Out 95 stops after the 95th), **Hold First Frame / Hold Last Frame** (holds are included in loops), **Reverse**, **Loop** (to project end; includes holds and trims).
  - **Missing Frames**: **Fail** (no output; render aborts), **Hold Previous Output** (fails if the first frame is missing), **Output Black**, **Wait** (polls every few seconds; use it when comping while a 3D render is still writing).
- **Import tab** (pp. 1180-1183):
  - Process Mode: Full frames, NTSC fields, PAL/HD fields, PAL/HD fields (reversed), NTSC fields (reversed). The reversed modes swap fields spatially and in time.
  - **Depth**: **Format** (default; the file's native depth: JPEG 8-bit, **EXR Float**, fallback to prefs), **Default** (Frame Format prefs), Int 8 Bit, Int 16 Bit, Float 16, Float 32.
  - **Pixel Aspect**: From File (TIFF, JPEG, EXR headers), Default (ignore the header; use prefs), Custom (shows X/Y Pixel Aspect; right-click for presets).
  - **Import Mode**: Normal, **Pull Up** (removes 3:2 pulldown, 30 -> 24 fps), **Pull Down** (adds pulldown, 24 -> 30; Process Mode must be Full Frames). **First Frame** (cadence start). **Detect Pull-Down Sequence** (works only after Pull Up/Pull Down is chosen).
  - **Make Alpha Solid** (alpha = white/opaque). **Invert Alpha** (combine with Make Alpha Solid for fully transparent). **Post-Multiply by Alpha** (converts straight to premultiplied). **Swap Field Dominance** (temporal only, no scanline swap).
  - **Color Space Type** (Auto/Space; metadata only), **Curve Type** (Auto/Space/Log), **Remove Curve** (linearize).
- **Format tab** (per format): **OpenEXR** maps arbitrary EXR channels onto Fusion channels by typing channel names into the fields. **QuickTime** chooses a track. **CinemaDNG**. **PSD** loads one layer or the composite; transformation and adjustment layers are unsupported. File > Import > PSD brings in all layers with blend modes.
- **Comp:\ path variable** (Fusion Studio): `Comp:\` = the folder of the saved .comp. Example: comp at `X:\Project\Shot0815\Fusion\Shot0815.comp` -> `Comp:\Greenscreen\0815Green_0000.dpx`, or `Comp:\..\Footage\Greenscreen\0815Green_0000.dpx` (`..` goes up one folder). **Enable Reverse Mapping of Paths** (Path Map prefs) applies `Comp:\` automatically. It keeps comps portable for net-render (pp. 1179-1180).

### MediaIn (MI)
Resolve-only foundation of every Fusion-page comp (pp. 1184-1188). The Effects Library's MediaIn "is not used as a method to import clips".
- Created when you open the Fusion page on a timeline clip, drag from the Media Pool, drag from the OS, or use **Fusion > Import > PSD** (each PSD layer becomes a separate MediaIn).
- Inputs: Effect Mask.
- **Image tab** (the full set appears for Media Pool/OS clips; timeline clips get a subset):
  - **Global In/Out**: only for Media Pool/OS clips. Same auto-trim/hold behavior. **Clip Name** display.
  - Process Mode (same field options as Loader).
  - **Media Source**: **Timeline** (default; the edit clip), **Background** (pulls the **composited result of the lower video tracks**), **Media Pool** (bypasses the timeline edit).
  - **Layer**: picks the layer of multilayer/PSD files. For a Fusion Clip built from several video layers it is the layer index.
  - Trim, Hold First/Last Frame, Reverse, Loop (as Loader).
  - **Source Color Space**: **Auto** (timeline color space, or the RCM-assigned space when Resolve Color Management is on) or **Space** (menu + horseshoe graph).
  - **Source Gamma Space**: Auto (timeline or RCM gamma), Space, **Log** (Log Type menu + Lock RGB, Level, Soft Clip, Film Stock Gamma, Conversion Gamma, Conversion table). **Remove Curve** (linearize). **Pre-Divide/Post-Multiply** (straight alpha to premultiplied).
- **Audio tab**: **Audio Track** dropdown (solo the clip or hear all timeline tracks), **Sound Offset** wheel (sub-frame slip that affects **only the Fusion page**), **Purge Audio Cache** button.
  - **Media Pool clip audio is muted by default.** Select the node > Audio tab > choose the clip in Audio Track. With several MediaIns, the last one selected plays. Right-click the toolbar **Speaker icon** to choose which MediaIn you hear.
  - **Purge the audio cache** after changing tracks, slipping audio, or changing levels in the Edit/Cut/Fairlight pages.

### MediaOut (MO)
Resolve-only. **Every Fusion-page comp must have one.** It sends the result back to the Edit/Cut timeline (pp. 1188-1191).
- Input: **Input** (orange, **required**), any 2D image.
- **The first MediaOut renders to the timeline. Additional MediaOuts (added from the Effects Library) pass mattes to the Color page.**
- With RCM or ACES, **each MediaOut converts back to the timeline color space** for the Color page handoff.
- Handoff order when the clip also has Edit/Cut-page transforms or plugins: **Fusion effects -> Edit page effects/plugins -> Color** (p. 1189).
- Inspector **Color Grade** view, preview only (output unchanged): **None** (default; Fusion output at source/comp resolution), **Color** (+ Color-page grade), **Mix** (+ Cut/Edit effects + grade). Color and Mix display at **timeline resolution**.

### Saver (SV)
Fusion Studio render output. In Resolve it is **EXR export only**. Any number per comp, and it can be placed mid-tree to render intermediates. In Studio it can also carry a scratch audio track (pp. 1192-1199).
- Input: **Image Input** (orange).
- **File tab**:
  - **Filename**: sequence numbers are added automatically. **Default is 4-digit padding** (e.g. `image0000.exr`). Set padding explicitly in the name: `image000000.exr` = 6 digits, `image.001.exr` = 3, `image1.exr` = none.
  - **Output Format**: changing it **does not change the filename extension**. Edit the extension yourself.
  - **Save Frames**: **Full Renders Only** (normal; writes on Start Render) or **High Quality Interactive** (writes each frame as it is processed interactively, for paint/roto). Frames already written are **not** re-rendered when splines change later, so re-step or do a final render.
  - **Frame Offset**: start number for the file sequence. The manual's example says start 100 renders as 100-131, but 30 frames would be 100-129.
- **Export tab**:
  - Process Mode (field options as Loader).
  - **Export Mode**: normal, or apply SMPTE 3:2 pulldown (24 -> 30).
  - **Clipping Mode**: **Frame** (default; clips to frame dimensions, **breaks infinite workspace**, and area outside the DoD is black) or **None** (no clipping; can write huge images).
  - **Save Alpha to Color**: writes alpha as grayscale into RGB, **overwriting color**.
  - **Color Space Type** (Auto/Space) + **Curve Type** (Auto/Space/Log) + **Apply Curve**: converts **only the written file**. For example, linear EXR and Rec.709 QuickTime from one comp via two Savers.
- **Audio tab** (Fusion Studio only): **Source Filename** (WAV only), **Sound Offset**. Scratch-track use only. The entire file loads into RAM, so keep it small. Audio is embedded only for QuickTime output. Final renders should generally be done without audio.
- **Legal tab**: **Video Type** (NTSC, NHK, PAL/SECAM), **Action** (Adjust to Legal, Indicate as Black, Indicate as White, No Changes), **Adjust Based On** (75% or 100% amplitude; leave 75% for most markets), **Soft Clip**.
- **Format tab**: format-specific (EXR options differ from MOV). **DPX: with Bypass Conversion on and log data, keep Data Is Linear OFF.** Data Is Linear tags the DPX header as linear, and downstream apps then skip the log-to-lin conversion (p. 1198).


## Krokodove nodes (Ch. 46)
The formerly third-party Krokodove motion-graphics toolset, now integrated into Resolve and Fusion. **The manual gives one-line descriptions only**: no abbreviations, inputs or controls (pp. 1203-1207). Inspect a node's Inspector (or `GetInputList()`) before scripting it.

| Category | Nodes (manual description, condensed) |
|---|---|
| **3D** | **Mapped Duplicate 3D**: 3D grid of duplicated objects in X/Y/Z. Images can drive offset, rotation, scale, timing. |
| **3D Create** | **Fold Create 3D**: plane that folds its subdivisions in a set order (folding-card effect). **Heightfield Create 3D**: plane displaced in depth by image luminance, shapeable into squares or bars. **Tube Create 3D**: pipe along a path; profile Polygon or Star. |
| **Image Tools** | **Bounding Box** (rectangle from a channel; Threshold sets size). **Color Map** (map texture to flat colors, manual or auto-detected). **Connect** (continuous line through positionable way-points). **Dither** (crunchy dither shading). **Extend** (repeat edge pixels H or V). **Fragments** (chop into pieces, fade via Range). **Grow** (image grows or disappears from seed locators). **Grow Color** (stretch edge colors into transparent areas). **Microwaves** (radiating light beams from a point). **Pack** (stacked shapes within a channel). **Painterly** (stylized artwork filter). **Rasterize** (halftone dots/squares/diamonds). **Time Mapper** (mix times of a sequence via an image map). **Worm** (straight and curved lines through points). |
| **Image Color Tools** | **Invert** (color, luminance or hue). **Match Color** (pick shadows/mids/highlights and replace with a color). **Recolor** (substitute one or more source colors). **Replace Color** (source color -> correction). **Threshold** (isolate a narrow color or brightness range with tolerance). |
| **Image Create Tools** | **Blobs** (circles at points). **Generate** (grayscale pseudo-random texture). **Lines** (multi-level repeating line sets). **Pattern** (tessellated full-frame shapes). **Shapes** (concentric squares/circles). |
| **Image Pixel Tools** | **Average** (frame blending across frames). **Bevel** (internal bevel). **Channel Shifter** (offset/blur/scale RGBA separately). **Clean Edges** (replace frame-edge pixels by duplication or solid color). **Deflicker** (regional or global flicker removal). **Duplicate** (replicate image along a pattern/shape). **Extrude** (edge-distortion depth illusion). **Noise** (pixelated random or picked colors). **Plastic** (plastic sheen/bevel). **Positioner** (corner pin with source and destination). **Push** (slide transition to a second image). **Rest** (shift pixels to rest on a line/path). **Seamless** (mirror the opposite edge and blend, for tiling). **Seamless Loop** (retime a comp into a seamless loop). **Sort** (pixel sort by color). |
| **Image Position Tools** | **Contour** (edge detection). |
| **Image Vector Tools** | **Vector Visualisation** (overlay of motion-vector direction and velocity). |
| **Image Warp Tools** | **Bend** (radial bend). **Directional Scale**. **Kaleidoscope**. **Mirror** (flip along a line). **Offset** (H/V displace). **Radial** (dent with a warp-mask input). **Relative Transform** (second input drives position/rotation/scale; pivot detected from pixel data). **Segment Transform** (square segments each rotated/scaled). **Shear** (angular shear; extra input sets intensity). **Shuffle** (reposition subdivided tiles). **Spherize** (magnifier dent in a shape region). **Stretch** (pixel stretch along a line). **Warped Transform** (simple stretch/squish/turn). |
| **Shape Tools** (operate on Fusion shapes) | **sExtrude**, **sKill** (delete segments matching criteria), **sOffset** (grow/shrink outline; **Number** repeats it), **sResample**, **sRestyle** (override fill/outline look), **sRound** (rounded corners), **sSmooth** (smooth segments, keep corners), **sTriangulate**, **sWriteOn** (reveal/hide the outline), **sZigZag** (wave/jagged each segment). |
| **Shape Create Tools** | **sPrimitiveCreate** (cross, polygon, rectangle, star). **sSpiral Create**. **sTrace Create** (converts 2D text or shapes into Fusion's shape environment; thickness, opacity, line styles). |
| **Region Tools** (for tools with a Region input) | **rCube**, **rPlane**, **rSphere** (region volumes with softness, invert, transform), **rNoise** (Perlin-noise region), **rMerge**, **rModify**, **rTransform**. |
| **Modifiers** | **Beat** (drive animation in Frames per Beat or BPM; Start/End, Attack, Decay, Sustain, Release). **Color Switcher** (switch or rotate palettes; connect RGBA channels to its outputs). **Random** (Min/Max random values; smooth transitions over a frame range). |
| **Text Modifiers** | **Formula** (custom tool as a modifier). **From File** (load a .txt file or type text; show it a line at a time for fixed or custom durations). **Juggle** (random character mixing). **Write** (typewriter write-on with an optional cursor/caret, plus an always-visible **Prefix**). |

Notes (inference): **Write** is the Krokodove typewriter alternative to Text+ Write On and Follower. **Beat** is the tool for music-synced motion. **sTrace Create** is the bridge from Text+ into the shape toolset.


## Layer nodes (Ch. 47)
They operate on **multilayer images**: multi-part EXR, PSD layers, and multi-video-layer Fusion Clips (inference from MediaIn Layer, p. 1186). A layer carries RGBA plus Aux channels. One layer is the **Default/[Main]** layer, which is what normal single-layer tools see (inference). The four nodes are below.

### Layer Muxer (LMx)
Combines the layers of two multilayer sources (pp. 1209-1210).
- Inputs: **Image 1** (orange), **Image 2** (green).
- **Layer**: which Image 2 layers are added to Image 1. **Default Layer** (Image 2's default layer), **All Layers**, **Custom** (checklist). Any choice other than All Layers puts a **small layer icon on the node** as a reminder.
- **Conflicts**: Image 1 or Image 2. The chosen input becomes the output's **Default/[Main]** layer.

### Layer Regex (LRx)
Filters, keeps, removes or renames layers by regex on layer names (pp. 1210-1213).
- Inputs: Image 1 (orange), Image 2 (green).
- **Expression**: the regex (PCRE style; the manual links a PCRE cheat sheet).
- **Mode**: **Transform** (rename via Name Template), **Keep** (keep matches), **Remove** (drop matches).
- **Name Template**: replacement string with capture groups `$1`, `$2`...
- **Unmatched**: **Keep** (non-matching layers pass) or **Remove** (only matched layers survive).
- **Tester**: live preview of the results. **Conflicts**: which input becomes Default/[Main].
- Manual examples (verbatim patterns):

| Goal | Expression | Name Template / Mode | Result |
|---|---|---|---|
| Prefix all | `(.*)` | `Right.$1` | `Right.Layer1` |
| Suffix all | `(.*)` | `$1.Right` | `Layer1.Right` |
| Prefix matching layers | `(Right.*)` | `Stereo-$1` | `Stereo-Right.Layer1` |
| Find and replace | `right(.*)` | `Left$1` | `right.1` -> `Left.1` (also hits `copyright`) |
| Anchor to start | `^right(.*)` | `Left$1` | skips `copyright` |
| Remove either word | `(copy\|right)` | Mode Remove (Keep inverts) | drops layers containing copy or right |
| Case-insensitive | `(?i)(right)` | | matches Right, RIGHT... |

### Layer Remover (LRm)
One input, **Image 1** (orange). The Controls tab is a checklist of layers, and **checking a box removes that layer** (p. 1214).

### Swizzler (Swz)
Builds new layers and assigns channels from any inputs. It is "like Channel Booleans, but layer-aware": it creates layers, pushes source layers or channels into a layer, or removes channels (pp. 1214-1219).
- Inputs: **Input 1** (orange) plus **Input X** (white, additional inputs added as you connect).
- **Layer List**: view, select and rename custom layers. **Add Layer** button. **Keep Main Input Layers**: pass Input 1's existing layers through, so you add to an existing multilayer.
- **Channels** (for the selected layer): **All Channels**; **Color/Aux** (separate sources for RGBA and for Aux); **RGB/A**; **R/G/B/A** (per-channel sources).
- **Source** (input), **Source Layer** (a layer of a multilayer input), **Source Channels** (Color/Aux mode: which channels feed Aux; for RGB-only passes pick e.g. **RG for UV Texture**, **RGB for XYZ Normal**).
- A single added layer becomes the new **default layer** (p. 1217).


## LUT nodes (Ch. 48)

### File LUT (FLU)
Applies a 1D or supported 3D LUT **from a file on disk**, not a spline. Only the **path** is stored in the comp, so comps stay small and editing the file updates every File LUT that uses it (p. 1223).
- Inputs: **Input** (orange, required), Effect Mask (blue).
- **LUT File**: path/Browse. Supports Fusion **.LUT** and **.ALUT**, Resolve **.CUBE**, and several 3D LUT formats. **If the file can't load, it fails with an error in the Console.**
- **Pre-Gain** (pull highlights in before the LUT clips them), **Post-Gain**, **Color Space** (RGB default; YUV, HLS, HSV, others), **Pre-Divide/Post-Multiply** (prevents illegal additive values on keyed or CG edges) (p. 1224).
- Placement: after MediaIn/Loader to linearize camera footage, or at the end as a colorist's look.

### LUT Cube Creator (LCC)
No inputs. Generates the color-cube test image (pp. 1227-1229).
- **Type**: Horizontal strip, Vertical strip, **Rect**.
- **Size**: samples per cube side. Typical **33** (33x33x33, about 35,937 samples) or **65**. Higher is more accurate but costs more memory and compute.
- If graded outside Fusion, **keep it 32-bit float**.

### LUT Cube Analyzer (LCA)
Input: one orange input, the (graded) Creator image. Writes a 3D LUT (pp. 1225-1226).
- **Type**: **ALUT3, ITX, 3DL**. **Filename**. **Write File** button.
- Feeding the ungraded cube gives a 1:1 LUT, and **the viewer shows nothing**.

### LUT Cube Apply (LCP)
Applies a graded cube live, **with no LUT file** (pp. 1226-1227).
- Inputs: **Input** (orange; the image to transform), **Reference Image** (green; the Creator output or its graded version), Effect Mask.
- **No controls.**


## Gotchas and non-obvious behavior

1. **Resolve Loader/Saver are EXR-only** (pp. 1176, 1192). In Resolve, bring footage in as MediaIn and deliver through MediaOut + Deliver page. Use Saver only for EXR renders.
2. **Every Resolve comp needs MediaOut. Only the first MediaOut goes to the timeline**, and extra ones only feed mattes to the Color page (p. 1189).
3. **Media Pool MediaIn audio is muted by default.** Audio changes need **Purge Audio Cache**. Sound Offset affects the Fusion page only (p. 1188).
4. **Text+ Write On direction:** the manual (p. 1153, repeated in the 3D chapter) says Write On = animate **End from 1 to 0** and Write Off = animate **Start from 0 to 1**. With Start 0 / End 1 showing all text, End 1 -> 0 actually removes text from the end. For a left-to-right reveal, keyframe **End 0 -> 1** (inference; verify in the viewer).
5. **Follower does nothing until parameters are keyframed** in its Modifiers tabs, and **spaces count as characters** in the Order/delay math (pp. 1165-1167).
6. **Character Level Styling selection happens in the viewer**, not the Modifiers-tab text box. It works on Text+ only; for Text 3D, copy Text+ and Paste Settings (pp. 1164-1165).
7. **Only shading element 1 is on by default.** Other elements hide their controls until **Enabled** is checked (p. 1158). Priority Back/Front works only when Sort By = Priority (p. 1162).
8. **Ligatures default to None for Latin** so per-character animation doesn't treat "fi"/"ff" as one glyph. Arabic needs **Non-Latin** (p. 1155).
9. **Manual kerning animation uses one spline for all characters** (p. 1163), so every moved character is keyed together.
10. **Y-direction wording:** the manual says Pivot 0.1, 0.1 moves the axis "downward and to the right" and Offset Y 0.1 moves "further down". Fusion's normalized Y usually increases upward (inference), so verify the sign in the viewer before scripting offsets.
11. **Fast Noise Seethe needs keyframes and Seethe Rate does not.** Seethe Rate is the zero-keyframe way to animate noise (p. 1134). There is no built-in seamless option.
12. **Day Sky is a light map, not a sky**, and outputs HDR float. Disable Do Tone Mapping only in a float, graded pipeline (p. 1131).
13. **Saver Output Format does not rename the extension**, padding defaults to 4 digits, and **High Quality Interactive leaves stale frames** after spline edits (pp. 1193-1194).
14. **Saver Clipping Mode = Frame (default) breaks infinite workspace.** None can write enormous files (p. 1195).
15. **Color Space/Curve Type on inputs only tags metadata.** Only Remove Curve (input) or Apply Curve (Saver) change pixels. Saver conversion affects the file, not the comp (pp. 1171, 1182, 1195).
16. **Loader sequence length = first to last number found.** Gaps count as missing frames, handled by the Missing Frames setting. Shift-drag loads a single still from a numbered folder (p. 1178).
17. **DPX Saver:** log data + Bypass Conversion means **Data Is Linear OFF**, or downstream apps skip log-to-lin (p. 1198).
18. **OGrafLoader has no Reverse.** Single-step templates need a **Stop before a Play** (p. 1147).
19. **Layer Muxer/Regex Conflicts decides the Default/[Main] layer.** A node icon warns when Layer Muxer passes only some layers (p. 1210).
20. **Layer Regex unanchored patterns over-match** (`right` hits `copyright`). Anchor with `^`, and use `(?i)` for case-insensitive matching (pp. 1212-1213).
21. **File LUT stores only a path.** A missing file errors in the Console, and editing the file changes every comp that uses it (pp. 1223-1224).

## Recipes / workflows

**R1. Per-character ripple-in with Follower (Text+)** (pp. 1165-1167)
1. Text+ > type the title in Styled Text. Set Text tab > Advanced > Use Ligatures = None (default for Latin) so each letter animates separately.
2. Right-click the Styled Text box > **Follower**. Open the Inspector **Modifiers** tab.
3. At the start frame, keyframe the animated values in the Follower's Transform/Shading tabs (e.g. Shading Opacity 0, or a Transform offset/size). Move to a later frame and keyframe the end values. Without keys nothing changes.
4. **Timing tab**: Range = all characters (or drag-select a range in the viewer), Order = **Left to right**, Delay Type = **Between Each Character**, delay e.g. 2 frames (example value). For a fixed total duration regardless of text length, use **Between First and Last Character**.
5. For organic reveals, set Order = **Random but one by one** or **Inside out**.

**R2. Write-on/write-off without modifiers** (p. 1153)
1. Text tab > **Write On** range. For a reveal, key End 0 at the first frame and End 1 at the last (inference; see Gotchas, Write On direction).
2. For a write-off, key Start 0 -> 1.
3. For a typewriter with a caret or a fixed prefix, use the Krokodove **Write** text modifier instead (p. 1207).

**R3. Soft drop shadow built from shading elements** (built from documented controls, pp. 1158-1162)
1. Shading tab > Sort By **Priority**. Shading Element **2** > **Enabled**.
2. Appearance **Text Fill**, Color Types **Solid** black, **Opacity** e.g. 0.6 (example; use Opacity, not color alpha).
3. **Softness X/Y** up for blur. **Offset X/Y** small (e.g. 0.005, -0.005; check the Y sign in the viewer).
4. **Priority Back/Front** slide left so it sits behind element 1.

**R4. Lower-third box behind text** (pp. 1159-1160)
1. Enable a free element. Appearance **Border Fill**, **Level = Text** (or Line for one box per line).
2. **Extend Horizontal / Extend Vertical** for padding. **Round** for corner radius. Color and Opacity as needed.
3. Push it behind the fill with Priority Back/Front. For a keyline, add a second element with **Border Outline** + Thickness.

**R5. Image- or gradient-filled text** (pp. 1160-1161)
1. Element 1 > Color Types **Image** > Image Source **Tool** > drag the texture node into **Color Image** (or right-click > Connect To). Clip and Brush are the other sources.
2. **Mapping Level**: Text (one image across the text), or Character (per letter). Use Mapping Size/Angle/Aspect to fit.
3. For aliasing, set **Image Sampling = Area**. For gradient text use Color Types **Gradient** with the same Mapping controls.

**R6. Text on an animated path** (pp. 1156-1157)
1. Layout **Type = Path**. Shape the path on screen.
2. Keyframe **Position on Path** (0 -> 1. Values beyond run off the path end).
3. For a path shared with other nodes or morphing, use **Right-click Here for Shape Animation**.

**R7. Dailies burn-in slate** (pp. 1165, 1169)
1. Text+ #1: right-click Styled Text > **Time Code**. Enable Hrs/Mins/Secs/Frms, set **Frames per Second = comp FPS**, **Drop Frame** if NTSC DF, and Start Offset to match source TC.
2. Text+ #2: right-click > **Comp Name**. Merge both over the plate.

**R8. Animated procedural texture without keyframes** (pp. 1133-1135)
1. Fast Noise > raise Detail (higher is slower), Contrast up, Scale to taste.
2. **Seethe Rate > 0** for automatic evolution. Unlock X/Y and stretch one axis for brushed metal.
3. For hard caustic-like lines: **Discontinuous** + **Inverted**.
4. Color tab > **Gradient** for color, or feed a **Noise Detail Map** mask to localize detail.

**R9. Looping/scrolling gradient background** (pp. 1127-1129)
1. Background > Type **Gradient** > Gradient Type **Linear** or **Radial**. Place Start/End in the viewer.
2. Repeat **Repeat** or **Ping-pong**. Animate **Offset**. Raise **Sub-Pixel** if the repeat edges shimmer.

**R10. Pass a matte to the Color page (Resolve)** (p. 1189)
1. Build the matte branch. Add a second **MediaOut** from the Effects Library and connect the matte.
2. MediaOut1 still carries the main composite to the timeline. The Color page receives MediaOut2 as a matte.

**R11. Bake a Fusion grade to a 3D LUT** (pp. 1225-1229)
1. **LUT Cube Creator**: Type **Rect**, Size **33** (or 65).
2. Run it through the grading nodes (the same ones used on the plate).
3. **LUT Cube Analyzer**: Type **ALUT3 / ITX / 3DL**, Filename, **Write File**. Apply it later with **File LUT**.
4. To apply the grade without writing a file, connect the graded cube to **LUT Cube Apply**'s green Reference Image and the plate to orange Input.

**R12. Rename or split multilayer EXR layers** (pp. 1211-1213)
1. Layer Regex: Expression `^right(.*)`, Mode **Transform**, Name Template `Left$1`, Unmatched **Keep**.
2. To isolate only certain layers: Mode **Keep** with `(?i)(beauty|spec)` (inference pattern), or Unmatched **Remove**.
3. Remove stray layers with **Layer Remover** (check the boxes to drop them). Merge two sources with **Layer Muxer** and choose Conflicts for the Main layer.

**R13. Pack separate render passes into Aux channels / a multilayer clip** (pp. 1216-1219)
1. Connect each RGB pass to its own Swizzler input (Input 1, then the white Input X inputs).
2. **Add Layer**. Set Channels **Color/Aux** and assign each Aux channel's **Source** (RG for UV, RGB for normals). A single layer becomes the default layer.
3. Or add one layer per pass (rename it, e.g. "UV-Texture"), choose its Source input, and enable **Keep Main Input Layers** to append to an existing multilayer.

## Scripting and automation hooks

**Toolbar abbreviations** (manual: "can be used in the Select Tool dialog when searching for tools and in scripting references") (pp. 1125, 1175, 1208, 1222):
`Bg` Background, `DS` Day Sky, `FN` Fast Noise, `MAN` Mandelbrot, `MTxT` MultiText, `OGL` OGrafLoader, `PLAS` Plasma, `TXT+` Text+, `LD` Loader, `MI` MediaIn, `MO` MediaOut, `SV` Saver, `LMx` Layer Muxer, `LRx` Layer Regex, `LRm` Layer Remover, `Swz` Swizzler, `FLU` File LUT, `LCA` LUT Cube Analyzer, `LCP` LUT Cube Apply, `LCC` LUT Cube Creator. Krokodove nodes: no abbreviations given.

**Registry IDs for `comp.AddTool()`: NOT stated in this slice** (inference; verify with `comp:GetToolList()` / `tool:GetAttrs()` before relying on them): `Background`, `FastNoise`, `TextPlus`, `Loader`, `Saver`, `MediaIn`, `MediaOut`, `FileLUT`. Input IDs (e.g. the Styled Text input) are not given in the manual. Discover them with `tool:GetInputList()` or by copying a configured node and reading the pasted `.setting` Lua table (inference).

**Paths and variables**
- `Comp:\` = the saved comp's folder (Fusion Studio Loader/Saver), with `..` for parent folders. Path Map pref **Enable Reverse Mapping of Paths** substitutes it automatically (p. 1179).
- Global > General pref **Auto Clip Browse** controls whether Loader opens a file dialog when added (p. 1176).
- Saver padding is encoded in the filename: `name0000.exr` (default 4), `name000000.exr` (6), `name.001.exr` (3), `name1.exr` (none) (p. 1193).
- OpenEXR channel names for the Loader Format tab can be listed with the OpenEXR command-line utility (openexr.com) (p. 1183).

**Text+ hooks:** Styled Text right-click **Publish** / **Connect To** links text between nodes (p. 1152). Font Features take OpenType tags (`smcp`, `frac`) (p. 1155). Image-shading **Color Image** takes a node name as text (p. 1161).

**Shortcuts:** emoji Ctrl-Cmd-Space / Win+. (p. 1152); kerning Option/Alt+Left/Right, larger with +Shift (p. 1163); double-click viewer to edit Text+/MultiText; gradient stops click-add, Cmd/Ctrl-drag copy, drag-up delete (p. 1128); Loader Shift-drag = single frame (p. 1178); drag middle of Global In/Out bar to slide (p. 1178).

**Regex syntax accepted by Layer Regex** (p. 1212-1213): capture groups `( )`, backrefs `$1` in Name Template, alternation `(a|b)`, start anchor `^`, inline case-insensitive `(?i)`. PCRE cheat sheet referenced.

**Settings-tab scripting:** every tool has **three Scripts edit boxes** that run while the tool renders. "Process When Blend Is 0.0" keeps them firing when Blend = 0 (pp. 1172, 1174, 1201).
