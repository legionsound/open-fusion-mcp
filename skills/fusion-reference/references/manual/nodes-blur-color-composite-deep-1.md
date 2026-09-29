<!-- nodes-blur-color-composite-deep.md part 1 of 4; index: nodes-blur-color-composite-deep.md -->
# Fusion Blur, Color, Composite, Deep Image, and Deep Pixel Nodes
Scope: Fusion 21.1 manual pages 877-1039 (Chapters 33-37). Use when: building or editing a Fusion/Resolve-Fusion node tree that needs blur/sharpen/glow effects, color correction/space/gamut work, image compositing (Merge/Dissolve/MultiMerge), or deep-image (OpenEXR multi-sample) and AOV-based (Ambient Occlusion/Depth Blur/Fog/Shader/Texture) nodes.

Node tree screenshots in the manual show `MediaIn` (DaVinci Resolve) interchangeably with `Loader` (Fusion Studio) — treat them as equivalent throughout.

## Mental model

1. **Two inputs on almost every simple node**: an orange required image input, and a blue optional Effect Mask. The mask is created from polylines/shapes/paint strokes/bitmaps and is **applied after the node processes**, i.e. it clips the *result*, not the source.
2. **Common Controls pattern**: every node category (Blur, Color, Composite, Deep Image, Deep Pixel) has a nearly-identical Settings tab at the end of its Inspector: Blend, Process When Blend Is 0.0, RGBA channel selector, Apply Mask Inverted, Multiply by Mask, Use Object/Use Material + Correct Edges, Object ID/Material ID sliders, Use GPU, Motion Blur group, Comments, Scripts. Documented once below per chapter; only chapter-specific deltas are called out.
3. **Two different RGBA selectors look the same but differ**: a node's own Controls-tab RGBA buttons (e.g. Blur's Color Channels) are applied *before* processing — deselecting a channel skips it entirely, which is faster. The Settings-tab (Common Controls) RGBA buttons are applied *after* processing — the node still computes that channel, then the original is copied back over it. Do not conflate these.
4. **Clipping Mode** (Frame default / Domain / None) governs domain-of-definition edge handling for filter nodes that sample outside their input's current DoD (Blur, Defocus, Directional Blur, Sharpen family). Frame = ignore upstream DoD, treat as full frame (missing data outside upstream DoD = black/transparent). Domain = respect upstream DoD (can cause clipping with large filters). None = no source clipping at all (data outside upstream DoD is treated as black/transparent when needed).
5. **Gain vs Lift vs Gamma** (recurring across Brightness/Contrast, Color Corrector, Color Gain, OCIO CDL): Gain multiplies around black (affects highlights more), Lift scales around white / affects shadows more, Gamma is a non-linear midtone power curve that leaves 0.0 and 1.0 untouched.
6. **Premultiplied alpha and Pre-Divide/Post-Multiply**: recurring checkbox across color nodes — divides RGB by non-zero Alpha before correcting, re-multiplies after. Prevents color math from being skewed by partial-alpha edges; important before additive Merges or with CG/premultiplied renders.
7. **Additive vs Subtractive compositing** (Merge node): Additive assumes a premultiplied foreground (transparent pixels already black); Subtractive assumes a non-premultiplied foreground and multiplies it by its own alpha first. The Merge node lets you blend between the two to fix problem edges.
8. **Ranges tab pattern** (Color Corrector, Color Gain, White Balance, dColorCorrector): a 4-point Bezier spline defines where Shadows/Highlights start and end; Midtones is whatever's left. Master applies after Shadow/Mid/Highlight corrections.
9. **Deep image compositing** is fundamentally different from 2D: pixels can carry multiple samples at different Z depths (from OpenEXR deep data or 3D renderers). Requires a linear colorspace. All `d`-prefixed tools (except Image to Deep / Deep to Image) auto-convert an ordinary 2D input into deep data.
10. **Deep Pixel nodes operate on AOVs** (Z, Normals, UV, etc.) embedded in a rendered 2D image, not on true deep (multi-sample) data — a different concept from Chapter 36's Deep Image tools despite similar-sounding use cases (fog, depth blur).
11. **Node names can collide by design**: Channel Booleans `Bol` (2D, this chapter) vs Channel Boolean `3Bol` (3D materials) are different tools — same idea, different domain.

---

## Blur Nodes (Chapter 33, p.877-901)

### Blur (`Blur`)
Blurs the input image; the most common image-processing op. (p.878)
- Inputs: Input (orange, 2D image, required); Effect Mask (blue).
- Key controls: `Filter` — Box (fast, lower quality) / Bartlett (subtle, anti-aliased) / Multi-box (layered Box passes approximating Gaussian, ~4 passes = good quality without ringing) / Gaussian (constant-time approximation, can ring/overshoot on float images — switch to Multi-box if visible) / **Fast Gaussian (default)**. `Color Channels (RGBA)` — pre-process selector (see Mental model #3), all on by default. `Lock X/Y` — default **on**. `Blur Size` — amount of blur; splits into X/Y when Lock is off. `Clipping Mode` — Frame (default)/Domain/None (see Mental model #4). `Blend` — cloned instance of Common Controls Blend.
- Gotchas: Gaussian ringing only appears on float-depth images, usually invisible in HiQ/final render but can surface in downstream processing — use Multi-box if you see it. (p.879-880)

### Defocus (`Dfo`)
Simulates an out-of-focus lens, with blooming/flaring; more physically-styled than Blur. (p.881)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Filter` — Gaussian (fast/simple) / Lens (realistic, significantly slower). `Lock X/Y`. `Defocus Size`. `Bloom Level` — intensity/size of bloom on pixels above threshold. `Bloom Threshold`. Lens-mode-only: `Lens Type` (bokeh shape), `Lens Angle` (rotation; no effect on Circle), `Lens Sides` (NGon side count; no effect on Circle), `Lens Shape` (pointedness; best with NGon + 5-10 sides; no effect on Circle). `Clipping Mode`.
- Modes/options: Lens mode unlocks the four bokeh-shape controls; Circle lens type ignores Angle/Sides/Shape entirely. (p.882-883)

### Directional Blur (`DrBl`)
Directional/radial smear blur for simulated motion blur or light-ray effects; affects all RGBA channels. (p.883)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Type` — Linear (straight-line smear) / Radial (originates from a point, radiates outward) / Centered (like Linear but blur distributed equally both directions) / Zoom (scale-smear, simulates slow-shutter zoom). `Center X/Y` — only affects Radial and Zoom. `Length` — strength/heading; negative values reverse relative to Angle; values above slider max can be typed manually. `Angle` — direction (Linear/Centered) or spin (Radial/Zoom — combined with nonzero Length creates a whirlpool effect). `Glow` — adds glow to simulate longer shutter exposure. `Clipping Mode`.
- Gotcha: Center X/Y control is inert for Linear/Centered types — don't waste time trying to reposition those. (p.884-885)

### Glow (`Glo`)
Blurs the image, brightens the blurred result, mixes it back with the original. (p.885)
- Inputs: Input (orange, required); Effect Mask (blue); **Glow Mask (white)** — a pre-mask that filters the image *before* the glow is generated, then the glow is merged back over the full original (glow can spread beyond the mask edges, unlike an Effect Mask which clips the final result).
- Key controls: `Filter` — Box / Bartlett (softer, smoother drop-off, slower) / Multi-box / Gaussian / **Fast Gaussian (default)** / Blend (nonlinear, visible in whites and blacks) / Hilight (no halo) / Solarize. `Color Channels (RGBA)` pre-process selector. `Lock X/Y`. `Glow Size`. `Num Passes` — Multi-box only; more passes = smoother but slower. `Glow` — intensity slider (large values blow out to white). `Clipping Mode`. `Blend` (cloned). `Apply Mode` — **Normal (default)**, adds glow over original / Merge Under, glow placed beneath image per Alpha / Threshold — clips glow effect, reveals a High-Low Range control (below-low pixels pushed black, above-high pushed white). `Color Scale (RGBA)` — tints the glow per channel; Pick button samples a color from the viewer.
- Gotchas: this Glow Mask behavior (extend-beyond-mask-borders while restricting source) is identical on Soft Glow — don't confuse it with a normal Effect Mask. (p.885-888)

### Sharpen (`Shrp`)
Convolution-filter sharpening, overall or per-channel. (p.888)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Color Channels (RGBA)` pre-process selector. `Lock X/Y` — default checked. `Amount` — sharpening strength; splits X/Y when unlocked. `Clipping Mode`. `Blend` (cloned). (p.888-890)

### Soft Glow (`SGlo`)
Like Glow but with extra processing for a softer, more natural result; good for atmospheric haze, skin tones, dreamlike looks. (p.890)
- Inputs: Input (orange, required); Effect Mask (blue); Glow Mask (white, same pre-mask behavior as Glow's).
- Key controls: `Filter` — Box / Bartlett / Multi-box / **Gaussian (default)**. `Threshold` — higher = pixel must be brighter before the glow affects it. `Gain` — brightness of the glow. `Lock X/Y`. `Glow Size`. `Num Passes` (Multi-box only). `Clipping Mode`. `Blend` (cloned). `Color Scale (RGBA)` + Pick eyedropper.
- Gotcha: Soft Glow has no Apply Mode/Threshold-range control set that Glow has — its equivalent shaping controls are Threshold + Gain instead. (p.890-893)

### Unsharp Mask (`USM`)
Sharpens only edge detail; corrects blur/low-contrast in long-exposure or soft source material by extracting high-frequency detail and brightening it. (p.893)
- Inputs: Input (orange, required); Effect Mask (blue).
- Key controls: `Color Channels (RGBA)` pre-process selector. `Lock X/Y`. `Size` — size of the internal blur used to extract detail; higher = more pixels flagged as detail. `Gain` — amount of brightening applied to flagged detail. `Threshold` — raises this to exclude low-contrast areas from the effect.
- Mechanism: blurs a frequency range, diffs against original — large diffs = edges = brightened. (p.893-895)

### Vari Blur (`VBL`)
True per-pixel variable blur driven by a second image (a blur map); similar intent to Depth Blur (Ch.37) but a different, often cleaner, algorithm. (p.895)
- Inputs: Input (gold, required, primary image); **Blur Image** (green, required — spline shape, text, still, or movie; choose R/G/B/Alpha/luminance channel to drive blur amount); Effect Mask (blue, optional).
- Key controls: `Method` — Soften (Box→Bartlett→Smooth as Quality rises; best detail preservation at low blur) / Multi-box (better Gaussian approximation at high Quality) / Defocus (flat circular blur shape). `Quality` — 1 = fast simple Box for all methods; 2 usually enough for low Blur Size; 4 generally enough unless Blur Size is very high. `Blur Channel` — which channel of the Blur Image drives per-pixel amount. `Lock X/Y`. `Blur Size` — pixels where Blur Image is black/nonexistent still get blurred by this base amount. `Blur Limit` — clamps blur-map values (useful because some Z-depth images run to infinity and would otherwise skew blur size). (p.895-897)

### Vector Motion Blur (`VMB`)
Directional blur driven by a motion-vector map or AOV (Arbitrary Output Variable) exported from 3D renderers (Arnold, Renderman, VRay) or generated by Fusion's Optical Flow node. (p.897)
- Inputs: Input (orange, required, 2D image); **Vectors** (green, required — motion vector AOV or Optical Flow EXR; must be float16/float32 to carry +/- values, e.g. X=1 means moved 1px right, X=-10 means 10px left); Vector Mask (white, optional, masks image before processing); Effect Mask (blue).
- Key controls: `X Channel` / `Y Channel` — select which image channel supplies the X/Y vector. `Flip Channel` (X, Y) — inverts a vector value's sign (e.g. 5 becomes -5). `Lock Scale X/Y` — off shows a single combined Scale slider. `Scale` — multiplies vector values (scale 2 x vector 10 = 20 pixel shift). (p.897-899)

### Blur Nodes Common Controls (Settings tab, p.899-901)
Found on every Blur-category tool (including third-party plugins):
- `Blend` — 0.0 skips processing entirely, output = input.
- `Process When Blend Is 0.0` — forces the node to still process (e.g. for scripted side effects) even at Blend 0.0.
- `Red/Green/Blue/Alpha` selector buttons — **post-process** (see Mental model #3); some tools instead skip the channel entirely if their Controls-tab RGBA buttons are identical to these.
- `Apply Mask Inverted` — inverts the combined mask channel.
- `Multiply by Mask` — multiplies masked-out RGB by mask value (0 outside mask → becomes black/transparent).
- `Use Object` / `Use Material` checkboxes — use EXR Object ID / Material ID channels as a mask, if present.
- `Correct Edges` — appears only with Use Object/Material; uses Coverage + Background Color channels to clean up overlapping-object edges (else aliasing may occur).
- `Object ID` / `Material ID` sliders — pick ID via Sample button (same UX as color picker).
- `Use GPU` — Disable / Enabled / Auto (falls back to software if no capable GPU).
- `Motion Blur` group — `Motion Blur` toggle; `Quality` (samples each side of motion, e.g. 2 = 2 samples per side); `Shutter Angle` (360 = one full frame exposure; higher values are legal and create stylized effects); `Center Bias` (shifts motion-blur center, for trail effects); `Sample Spread` (weights sample brightness).
- `Comments` — free text note; shows a red square / speech-bubble icon on the node.
- `Scripts` — 3 scripting edit-box fields that run when the tool renders.

---

