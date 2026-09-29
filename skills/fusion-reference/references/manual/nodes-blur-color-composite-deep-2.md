<!-- nodes-blur-color-composite-deep.md part 2 of 4; index: nodes-blur-color-composite-deep.md -->
## Color Nodes (Chapter 34, p.902-975)

### ColorFX subcategory

#### ACES Transform (`ATr`)
Color transform via ACES Input Device Transform (IDT) / Output Device Transform (ODT). (p.903)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `ACES Version`. `Input Transform` (IDT — typically pick the camera the footage was shot on). `Output Transform` (ODT — target color space for the exported timeline). `Gamut Compress Type` — prevents clipping of saturated monochromatic light sources (LEDs, neon, taillights). (p.903-904)

#### Chromatic Adaptation (`CrA`)
Precisely transforms an image lit/processed under one color temperature to appear as if under another, matching human visual adaptation. (p.905)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Method` — **CAT02 (default)**, compensates saturated-blue-going-purple, best for emissive/dim environments / Bradford Linear, also common, saturated blues go purple, works for emissive dim + reflective dark environments / Von Kries, oldest method, saturated blues go purple. All methods match neutral colors identically; they differ only on saturated-color handling. `Source/Target Illuminant` — Standard Illuminant list, Color Temperature slider, or CIE 1931 xy coordinates, for both source and target. Transform path: Timeline Color Space → XYZ → LMS (cone-response) space. Also respects the clip's `Color Space`/`Gamma` (defaults to timeline settings). (p.905-907)

#### Color Space Transform (`CST`)
LUT-like color transforms using RCM (Resolve Color Management) math instead of lookup tables — clean, no clipping. (p.907)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: Input Colorspace / Input Gamma / Output Colorspace / Output Gamma pop-ups + `Swap` button (reverses conversion direction). `Tone Mapping`: None (simple 1:1) / Clip (hard clips out-of-bounds) / Simple (maps ~5500 nits to ~100 nits — may still clip HDR highlights above 5500 nits) / Luminance Mapping (like DaVinci, more accurate for single standards-based color space like Rec.709/2020) / DaVinci (smooth luminance rolloff + controlled desaturation at extremes; good for mixed-camera wide-gamut media) / Saturation Preserving (rolloff without desaturating; exposes `Sat. Rolloff Start`/`Sat. Rolloff Limit` in nits, plus `Use Custom Max Input/Output` sliders, plus `Adaptation` — usually 0-10, higher for very bright scenes like snow at noon). `Gamut Mapping`: None / Saturation Mapping (`Saturation Knee` = level where remapping begins, `Saturation Max.` = new max, both 1.0 = max saturation in output space) / Clip. `Advanced`: `Apply Forward OOTF` (scene-referred → display-referred), `Apply Inverse OOTF` (display → scene), `Use White Point Adaptation` (chromatic-adapt for differing white points, e.g. P3-D60 clip cut into P3-D65 timeline — uncheck to preserve the source white point unaltered instead).
- Gotcha: this node's ACES settings do a colormetric transform, **not** an Academy-correct ACES transform — use the dedicated ACES Transform node for real ACES workflows. (p.907-910)

#### Gamut Limiter (`GML`)
Hard-clips (limits) the gamut to a standard, e.g. clamp a Rec.2020 delivery down to P3 for QC. (p.910)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Current Gamut`, `Current Gamma` (of the incoming image), `Limit Gamut` (target restriction).
- Gotcha: this is a limiting/clipping op — place it near the end of the tree so useful data upstream isn't prematurely destroyed. (p.910-911)

#### Gamut Mapping (`GMp`)
Standalone node exposing the same Gamut Mapping controls found inside Color Space Transform (and the Color Management panel of Project Settings) — for gamut-only remapping without a full CST. (p.912)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Gamma` (of the clip). `Tone Mapping Method`: None/Clip/Simple/Luminance Mapping/DaVinci/Saturation Preserving (identical semantics to CST above, plus separate `Max Input/Output Luminance` sliders and `Average Input Luminance`). `Gamut Mapping Method`: Saturation Mapping (Saturation Knee/Max, same as CST). `Advanced`: Apply Forward/Inverse OOTF. (p.912-914)

### Revival subcategory

#### Chromatic Aberration Removal (`CAR`)
Manually corrects lens color fringing. (p.915)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Advanced Options` — `Lens Center X/Y` (offset for reframed/re-rendered shots), `Stronger Correction`. `Estimation Options` (only active once a Show Estimated Fringes box is checked) — R/C, G/P, B/Y Balance sliders + `Brightness` (magnifies fringe indicators). `Aberration Correction` — R/C, G/P, B/Y `Scale` (removes fringing) and `Edge` (compensates for lens-edge-curvature fringing variance); `Show Estimated Fringes` checkbox displays fringes isolated against gray and unlocks Estimation Options. (p.915-917)

### Color subcategory

#### Auto Gain (`AG`)
Automatically stretches tonal range: darkest pixels → black, brightest → white (or user-selected values) by default. (p.918)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Do Z` — applies Auto Gain to Z/Depth channel instead (useful to match ranges between Z-channels, or view float Z as RGB). `Range` — Low/High black-point/white-point sliders. Example (p.919): gradient 0.2-0.8 gray, set Low=0.0 High=0.5 → brightest pixels pushed to 0.5, darkest to black, rest rescaled between.
- Gotcha: variations over time in the input (e.g. a bright object leaving frame) cause corresponding brightness jumps in the result, since remaining values get re-stretched — same caveat applies to Z with Do Z enabled. (p.918-919)

#### Brightness Contrast (`BC`)
Adjusts gain, brightness, contrast, gamma, saturation; controls are reversible except Pre-Divide/Post-Multiply which is applied first. (p.920)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls, in **application order** (Pre-Divide first, then top-to-bottom as listed): `Color Channels (RGBA)` pre-process selector (defaults R/G/B, not Alpha). `Gain` — `pixel * gain` (black unaffected, highlights affected more). `Lift` — `pixel + lift * (1 - pixel)` (whites unaffected, shadows affected more; e.g. lift 0.2 on pixel 0.1 → 0.28). `Gamma` — non-linear midtone power, 0.0/1.0 untouched. `Contrast` — stretches/squeezes around pivot 0.5. `Brightness` — linear, adds a fixed value uniformly. `Saturation` — 0 = grayscale via Rec.601 weighting. `Low`/`High` — remapping/normalization: `Output = (input - low) / (high - low)` (worked example p.922: Low=0.2 High=0.8 → pixel 0.2→0.0, 0.5→0.5, 0.8→1.0). `Direction` — Forward/Reverse (not all corrections are reversible, e.g. slope-to-zero can't be undone). `Clip Black`/`Clip White` — clips out-of-range float values; no effect on int8/int16 (can't go out of range). `Pre-Divide/Post-Multiply` — divides by non-zero Alpha before correction, re-multiplies after; prevents premultiplied-alpha images from being scaled incorrectly by gain/lift/gamma.
- For optimal results, run this in 32-bit float. (p.920-923)

#### Channel Booleans (`Bol`)
Applies math/logical ops between one image's channels and another's; also remaps/copies channels (color↔aux). (p.923)
- **Gotcha**: a same-named 3D node `3Bol` (Channel Boolean, no "s") handles 3D materials — this 2D tool is `Bol` (with the "s").
- Inputs: Background (orange, required — the image being adjusted); Effect Mask (blue); Foreground (green — modifies the background); Matte (white — combine external mattes into fg/bg ops). If Foreground isn't connected, operations that reference FG channels fall back to using Background's own channels.
- Key controls — `Operation` menu: Copy / Add / Subtract / And / Or / Exclusive Or / Multiply (darkens, white=1 no change, gray=0.5 half brightness) / Divide (lightens) / Maximum / Minimum / Negative (inverts FG) / Solid (channel→255, e.g. full Alpha) / Clear (channel→0, e.g. clear Alpha) / Difference / Signed Add (subtracts below mid-gray, adds above — good for embossed-gray effects). `To Red/Green/Blue/Alpha` menus — pick source channel (BG or FG suffix, e.g. "Red FG") for each output channel; also exposes auxiliary channels (Z-buffer, saturation, luminance, hue). Aux Channel tab: `Enable Extra Channels` — unlocks non-RGBA channel output.
- Recipes (p.923-926): copy FG red → BG alpha to build a matte; copy an image's own Alpha into its RGB via `Red/Green/Blue = Alpha BG`, Operation = Copy; replace an existing Alpha with another image's Alpha via `To Alpha = Alpha FG`, other outputs = Do Nothing, Operation = Copy; combine any mask into Alpha via `To Alpha = Matte`, feed the mask into Foreground; subtract one image's red channel from another's blue via `To Blue = Red FG`, Operation = Subtract. (Same "copy alpha into color" trick is also available on the Matte Control node.) (p.923-926)

#### Color Corrector (`CC`)
Comprehensive grading node: histogram matching/equalization, hue shifting, tinting, color suppression. (p.926)
- Inputs: Input (orange, required); Effect Mask (blue); **Match Reference** (green — reference image for histogram matching); **Match Mask** (white — defines the match sample area with more flexibility than the built-in match rectangle).
- 4 tabs: **Correction** (submenu Colors/Levels/Histogram/Suppress), **Ranges**, **Options**, **Settings**.
- `Range` menu (Colors/Levels/Suppress submenus share it): Shadows / Midtones / Highlights / **Master (default)**. Controls are fully independent per range; Master corrections apply *after* Shadow/Mid/Highlight corrections.
- **Colors submenu**: Color Wheel (drag or type numeric Hue/Saturation; Cmd/Ctrl-drag for fine adjustment; Shift-drag to lock to a single axis — tint or strength). `Tint Mode` — Better (default, quality) vs faster. `Hue` slider — clone of wheel control, effective range roughly -0.1 to 1.0 (clockwise angle; 0.25 = 90 degrees = red toward blue). `Saturation` slider — 0 = gray, 1.0 = unchanged chroma, >1 oversaturates. `Channel` menu — selects which channel's controls display (independent per channel). `Contrast`, `Gain` (multiplier, e.g. gain 1.2 on 0.4 → 0.48, black unaffected), `Lift` (multiplies around white, e.g. lift 0.5 on 0.0 → 0.5, white unaffected), `Gamma` (>1 raises midgray), `Brightness` (linear add). `Reset All Color Changes`.
- **Levels submenu**: histogram view with `Channel` selector; drag triangles beneath the histogram to shift/compress the input range (shift High left = push toward white; Low does the opposite). `Output Level` High/Low — clips/compresses output (Low toward High pushes darkest pixels toward white). `Reset All Levels`.
- **Histogram submenu**: input + reference histograms; `Histogram Type` — Keep (no change, ignores reference) / Equalize (flattens histogram) / Match (matches source distribution to reference — for matching lighting/exposure between shots). Equalize/Match reveal: `Match/Equalize Luminance` (0 = per-channel independent; positive = flatten/match luminance distribution first, before per-channel color correction — Luminance and RGB sliders are cumulative and rarely both set to 1.0), `Lock R/G/B` (uncheck for independent per-channel sliders), `Equalize/Match R/G/B` sliders (1.0 = full effect). `Precision` — 8/10/16-bit (higher = finer histogram fidelity). `Smooth Correction` — blends original histogram back in to reduce posterization from equalize/match. `Snapshot Match Time` — freezes the current reference histogram (prevents flicker from a changing reference); `Release Match` reverts to live reference. `Reset All Histogram Changes`.
  - Gotcha: **Equalize/Match on a float image converts color depth to 16-bit integer** — 2D histograms aren't suited to float's extreme dynamic range, so this always reverts to int16 processing. (p.932)
- **Suppress submenu**: color wheel surrounded by 6 per-hue controls; drag a control toward center to suppress that color. `Suppression Angle` rotates the wheel to target a specific hue. `Reset All Suppression` (resets to 1.0).
- **Ranges tab**: `Range` selector for viewer display (Result default, or view a grayscale mask of Shadows/Mids/Highlights — mid-gray = partial membership). `Channel` (defaults to luminance). Spline: 4 points w/ Bezier handles (top handles = range start, bottom = range end, control falloff); midtones has no direct control (whatever's left between shadow/highlight ranges). `Output the Range You See Now as Final Render` — outputs the monochrome range view as the actual render (handy for generating a range matte to reuse as an Effect Mask elsewhere). `Preset Simple/Smooth Ranges` buttons.
- **Options tab**: `Pre-Divide/Post-Multiply` (critical for additive merges / premultiplied CG). `Histogram Proxy Scale` (lower = higher precision). `Process Order` (gamma before or after levels). (p.926-936)

#### Color Curves (`CCv`)
Spline-based LUT color correction, one spline per channel; supports out-of-range (below 0/above 1) values. (p.937)
- Inputs: Input (orange, required); Effect Mask (blue); **Reference Image** (green — for match sampling); **Match Mask** (white — flexible match-area shape, vs the built-in rectangle).
- Key controls: `Mode` — **No Animation (default)** / Animated (per-channel change-spline over time) / Dissolve (obsolete, kept for compatibility). `Color Space` for the LUT view: RGB (default) / YUV / HLS / YIQ / CMY (nonlinear). `Color Channels (RGBA)` — selects which spline(s) are *editable*, doesn't restrict the effect itself; relabels per selected Color Space (e.g. Y/U/V). `Spline Window` — default linear 0-in/0-out to 1-in/1-out; add a 0.5/0.5 point and raise it to brighten mids. `In`/`Out` numeric fields for the selected point. `Eyedropper (Pick)` — click-drag from viewer sets triangular (vertically-locked unless unlocked via context menu "Locked Pick Points") points on all *enabled* channels at once — disable other channels first to target one spline; classic white-balance trick: pick a should-be-gray pixel, drag its point's Out value to 0.5. `Reference` group: `Match Reference` button (adds curve points to match the green reference image, count set by `Number of Samples`), `Sample Reference` (samples center scanline of background image instead), `Show Match Rectangle` + `Match Center`/`Width`/`Height` (repositions the match sample area — Sample Reference always uses the center scanline regardless). `Pre-Divide/Post-Multiply`.
- LUT view zoom: `+`/`-` on numeric keypad. Splines are also editable in the full Spline Editor. (p.937-940)

#### Color Gain (`Clr`)
Simpler/faster alternative to Color Corrector for gain/gamma/saturation/hue, plus unique Balance controls for tinting highlights/mids/shadows. (p.940)
- Inputs: Input (orange, required); Effect Mask (blue).
- Tabs: `Gain` — `Lock R/G/B` (locks RGB together, Alpha stays independent); `Gain RGBA` (linear multiply); `Lift RGBA` (scales around white); `Gamma RGBA` (nonlinear midtone, large changes push mids to black/white); `Pre-Divide/Post-Multiply`.
- `Saturation` tab — `RGB Saturation` per channel (0.0 strips that channel's color, >1 intensifies toward the primary).
- `Balance` tab — independent per-range (`Highs`/`Mids`/`Darks`) color-balance and brightness controls; colors paired as opposing CMY axes (Red↔Cyan, Green↔Magenta, Blue↔Yellow). `CMY Brightness Highs/Mids/Darks` sliders default -1 to +1 (typeable beyond that); 0.0 = no change.
- `Hue` tab — independent `High/Mid/Dark Hue` sliders, default range -1.0 to 1.0 (cyclical — hits original value again at the extremes); hue order in RGB space is Red→Yellow→Green→Cyan→Blue→Magenta→Red; positive values push right (red→yellow), negative push left (red→magenta).
- `Ranges` tab — same 4-point Bezier spline pattern as Color Corrector; `Preset Simple/Smooth Ranges` buttons. (p.940-944)

#### Color Matrix (`CMx`)
4x4-plus-Add matrix multiply/remap across RGBA channels — very flexible channel math tool. (p.945)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Update Lock` — pauses rendering while you set up all matrix values, then uncheck to render. `Matrix` — 4x4 grid + 5th "Add" column/row; rows = output (R,G,B,A,Add top-to-bottom), columns = input; default identity (1.0 on diagonal = 100% pass-through). Equation form: `[R out] = 1*[R in] + 0*[G in] + 0*[B in] + 0*[A in] + 0` (and similarly for G/B/A). `Invert` — inverts the whole matrix (handy for round-tripping: swap channels, do other ops, paste original matrix with Invert to restore).
- Recipes (worked examples, p.946-948): **Invert/negative**: set RGB diagonal to -1, Add column to +1 for R/G/B (push inverted negative values back into 0-1 range), leave Alpha untouched. **Per-channel brightness**: Add column values -0.2 (R), +0.314 (G), +0.75 (B), Alpha unchanged. **Channel copying**: e.g. Red output = luminance via "thirds" weighting, Green output = proper B&W luminance formula, Blue output = a red-weighted variant minus 0.1 brightness, Alpha output = original Blue channel. (p.945-948)

#### Color Space (`CS`)
Converts the working image to/from an alternate color space (viewers still label channels R/G/B even when they represent e.g. Hue/Luminance/Saturation post-conversion). (p.949)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Conversion` — None / To Color (RGB→selected type) / To RGB (selected type→RGB). `Color Type`: HSV, YUV (PAL broadcast), YIQ (NTSC broadcast, rare), CMY (nonlinear, print/CG-common), HLS (minor diffs from HSV), XYZ (CIE, weighted not nonlinear, used for gamut conversion/matching — contains the full perceivable gamut), Negative (inverts RGB, stays RGBA space), BW (grayscale via adjustable per-channel luminance-contribution sliders, stays RGBA space).
- Gotcha: the common-controls' single-channel R/G/B restrict buttons keep their R/G/B labels after a conversion but represent whatever channels the new color space actually holds (e.g. RGB→HLS: Red button=Hue, Green=Luminance, Blue=Saturation); Alpha is never touched by the conversion. (p.949-951)

#### Copy Aux (`CpA`)
Shuffles data between visible RGBA channels and auxiliary (3D-rendered) data channels — a convenience layer over Channel Booleans, operating on channel *groups* rather than individual channels. (p.951)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Mode` — Aux to Color / Color to Aux (Color to Aux hides all controls except Aux Channel). `Aux Channel` — background color, z-depth, texture coordinates, coverage, object ID, material ID, normals, vectors, back vectors, world position; single-component channels copy as `aaa1`, 2-component as `ab01`, 3 as `abc1`, 4 as `abcd` (e.g. Z→`zzz1`, UV→`uv01`, normals→`nxnynz1`). `Out Color Depth` — Match Aux Channel Depth (bumps RGBA to int16/float32 to match the aux data — most aux channels are float32 except Object/Material ID which are int16) / Match Source Color Depth (can clip — e.g. int8 output clips normals' [-1,1] to [0,1], and clips Z's [-1e30,0] to all-zero) / Force Float32. `Channel Missing` — Fail (errors to console) / Use Default Value (0, except Z which defaults -1e30). `Kill Aux Channels` — strips all non-RGBA channels after the copy, useful to extend cacheable playback frame count (e.g. long disparity sequences), or with Color to Aux>Color for longer color-only playback. `Enable Remapping` — linearly rescales the selected aux channel per-channel (settings remembered separately per channel) before conversion: `From > Min/Max` (source range; From Max < From Min flips/inverts), `Detect Range` (scan current frame), `Update Range` (scan + enlarge existing range to include new min/max), `To > Min/Max` (target range, defaults 0/1), `Invert` (flip after rescale to To range).
- Gotcha: be careful copying float aux channels into integer image formats — misconfigured Copy Aux can silently clip. (p.951-954)

#### Gamut (`Gmt`)
Transforms between color spaces and adds/removes gamma curves; paired with Cineon Log node for linearize-then-reapply-gamma workflows — typically one instance right after the Loader/MediaIn (linearize) and another right before the Saver/MediaOut (re-gamma). (p.954)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Source Space` — input color space; check `Remove Gamma` when linearizing after a Loader (leave at No Change when only adding gamma via Output Space before a Saver). `DCI-P3` — SMPTE-431-2, common with DLP projectors and HP Dreamcolor / Apple Pro Display XDR emulation. `Custom` gamut — CIE 1931 primaries + white point (xy coords) + gamma + linear limit + slope; DCI-P3 as Custom values: Red Primary 0.68/0.32, Green 0.265/0.69, Blue 0.15/0.06, White Point 0.314/0.351, Gamma 2.6, Linear Limit 0.0313. `Output Space` + `Add Gamma` (leave Output Space at No Change when only removing gamma via Source Space). `Pre-Divide/Post-Multiply`.
- Gotcha: for HD Rec.709 output, Fusion's terminology is **Scene = gamma 2.4**, **Display = gamma 2.2** — don't assume "Rec.709" alone specifies the gamma. (p.954-956)

#### Hue Curves (`HCv`)
Spline-based correction where the **horizontal axis is the image's hue** (not input/output value like Color Curves) — lets you isolate and animate a narrow color range easily. (p.957)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Mode` — **No Animation (default)** / Animated Points / Dissolve (obsolete). Color channel checkboxes gate both which splines are editable *and* which get new points from the Eyedropper. Spline window: control points sit at Red/Yellow/Green/Cyan/Blue/Magenta by default; cyclical — leftmost point is connected to rightmost. `In`/`Out` numeric fields. `Eyedropper` — left-click-drag onto viewer creates horizontally-locked points on active splines at the sampled hue (unlock via context menu's Lock Selected Points toggle). `Pre-Divide/Post-Multiply`. (p.957-960)

#### OCIO nodes — CDL, Color Space, Display, File Transform
Fusion's OpenColorIO pipeline; a shared `.ocio` config file (path via the user-set `OCIO` environment variable, or Fusion's own `DefaultConfig.ocio` in its LUTs directory if none found) shares color settings across facilities. See opencolorio.org for format internals. (p.959)

##### OCIO CDL Transform (`OCT`)
Create/save/load/apply an ASC-CDL grade. (p.959)
- Inputs: Input (orange, required); Effect Mask (blue). Typically placed after a Gamut node has linearized the Loader.
- Key controls: `Operation` — File (load a standard ASC-CDL file) / Controls (manual Slope/Offset/Power/Saturation + save-to-file). `Direction` — Forward / Reverse (not all corrections are reversible — e.g. all-zero Slope can't un-black an image). `Slope` (= Gain in Brightness Contrast terms — mids-to-high contrast). `Offset` (= Brightness — color balance/exposure). `Power` (inverse of the Gamma function — shadow-contrast control via a raised pivot). `Saturation`. `Export File` — saves current settings as a CDL file. (p.959-962)

##### OCIO Color Space (`OCS`)
Sophisticated colorspace conversion driven by an OCIO config; identical functionality is also exposed as the **View LUT** node from the View LUT menu. (p.962)
- Inputs: Input (orange, required); Effect Mask (blue). Typically one instance after Loader/MediaIn, another before Saver/MediaOut.
- Key controls: `OCIO Config` — File>Open to load a custom `.ocio`. `Source Space` / `Output Space` — populated from the loaded config (or DefaultConfig.ocio). `Look` — installed OCIO Color Transform Looks (None if none installed). (p.962-964)

##### OCIO Display (`OCD`)
Applies an OCIO Display transform to an input. (p.964)
- Inputs: single input + Effect Mask (single input listed, no separate BG/FG split described).
- Key controls: `OCIO Config File` (Browse). `Source Space`. `Display` (target monitor). `View` (color space to view through). (p.964-965)

##### OCIO File Transform (`OCF`)
Loads/applies a LUT (of various formats); identical functionality also exposed as the **View LUT** node. (p.965)
- Inputs: Input (orange, required); Effect Mask (blue). Typically placed after a Gamut node has linearized the Loader.
- Key controls: `LUT File` (File>Open). `CCC ID` — identifies a specific transform within an ASC CDL correction XML. `Direction` — Forward/Reverse. `Interpolation` — Nearest (fastest) ... Best (slowest); choose per quality/speed need. (p.965-967)

#### Set Canvas Color (`SCv`)
Sets the color of the workspace **outside the domain of definition (DoD)** — e.g. the transparent margin left when a Transform shrinks an image within its raster. Default canvas is black/zero-alpha; some nodes (e.g. inverting a mask) flip the implicit canvas to white, so this node lets you take explicit control. (p.967)
- Inputs: Input (orange, required); **Foreground** (green, optional — sample the canvas color from a connected image instead of using the color picker).
- Key controls: `Color Picker` (+ Alpha) — defaults black/0 alpha; empty/no controls shown when Foreground is connected.
- Gotcha/tip: hover the mouse over a black area outside the raster in the viewer to read the current canvas RGB in the status bar (bottom-left of the Fusion window). (p.967-968)

#### White Balance (`WB`)
Automatically removes color casts from bad camera setup/lighting, via a neutral-color pick or a color-temperature spec. (p.969)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Space` — source color space, for gamma-aware correction (leave default if unknown). `Method` — Custom (pick a pixel that should be pure gray; node computes correction; with no Effect Mask and Lock Black/Mid/White on, the whole shot is white-balanced) / Temperature (specify actual shot color temperature). `Lock Black/Mid/White` — locks the three tonal ranges together (affects both methods); uncheck for independent per-range correction. Custom-only: `Black/Mid/White Reference` (pick source pixel) + `Black/Mid/White Result` (target color, usually pure mid gray). Temperature-only: `Temperature Reference` + `Temperature Result`. `Use Gamma` — factors in the selected Space's default gamma. `Ranges` tab — same 4-point Bezier spline as Color Corrector, + Preset Simple/Smooth buttons.
- **IMPORTANT gotcha** (manual's own emphasis, p.970): when picking neutral colors with the Custom method, sample from the **source image, not the White Balance node's own output** — otherwise the image shifts mid-pick and the correction is based on wrong data. Also avoid reference pixels that are clipped in any channel (e.g. light pink 255/240/240 is clipped red but not truly white; dark blue-gray 0/2/10 is clipped red but not truly black) — neither leaves enough headroom for a good correction. (p.969-972)

### Color Nodes Common Controls (Settings tab, p.973-975)
Same list as Blur's Common Controls (Blend, Process When Blend Is 0.0, RGBA post-selector, Apply Mask Inverted, Multiply by Mask, Use Object/Material + Correct Edges, Object/Material ID sliders, Use GPU, Motion Blur group, Comments, Scripts) — **plus, unlike the Blur chapter, `Clipping Mode` (Frame/Domain/None) is explicitly folded into this shared Color Settings tab** rather than living only on individual Controls tabs.

---

