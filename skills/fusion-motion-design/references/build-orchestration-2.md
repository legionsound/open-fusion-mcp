<!-- build-orchestration.md part 2 of 6; index: build-orchestration.md -->
# Module 1: Draw vs Generate (build the chrome, generate the content)

Per the Fidelity Passport, mark EACH element [DRAW] or [GEN] before writing any build text. Default detailed/illustrative -> [GEN]; default flat geometry -> [DRAW].

> **There is NO third option [CROP].** The reference is a measurement source, never an asset source. A 552 px-wide reference scaled to 3840 has under 1 px of real detail per 7 px of frame; crop + inpaint ships one dead, off-style, non-animatable block. The cheap path must be a smart cheap path: native nodes (free and editable) or [GEN] with the style lock (costs credits; spend them when quality needs it). Crop only when the user hands over a high-res asset to place verbatim.

## Decision matrix

| Element | Verdict | Fusion construction |
|---|---|---|
| Card / panel / sheet, buttons, pills, dividers, bars, toggles, progress tracks | **DRAW** | `Background` fill + `RectangleMask` (`CornerRadius`), or `sRectangle` -> `sRender` -> Background `EffectMask`; unit Merge + unit Transform |
| ALL text: titles, labels, numbers, body, captions | **DRAW** | `TextPlus` (shading elements for outline/shadow/box); image models cannot render real text |
| Simple flat icons | **DRAW** | recognize, then rebuild from sShapes (`sRectangle`, `sEllipse`, `sNGon` Sides 3 for triangles, `sStar`, `sBoolean` Subtract for rings, `sOutline` for strokes) |
| Character / mascot / person | **GEN** | Nano Banana Pro 2K still or Seedance 2.5 1080p footage, composited |
| 3D / glossy / isometric object, product render | **GEN** (or native 3D when simple) | [GEN]; if the object is primitive geometry (rounded box, sphere, extruded logo), `Shape3D`/`Extrude3D`/`Text3D` + lights is often better and stays editable |
| Detailed illustration (coffee cup with steam, books, a fox) | **GEN** | |
| Street map, ornate gauge with many ticks | **GEN** | (a clean gauge with regular ticks is DRAW: `sRectangle` + `sDuplicate` radial copies) |
| Small label plate / badge / chip / stat pill / status tag, even with gradient, glow or shadow, even with its own text | **DRAW** | Background gradient + mask + separate `TextPlus` + `Shadow`/`SoftGlow`; it is chrome, not art |
| Flat gradient / glow fill on any surface | **DRAW** | `Background` `Type` "Vertical"/"Horizontal"/"Corner"/"Gradient" (+ `GradientType` "Radial"...); never a raster |
| Repeating geometric texture (grid, scanlines, dots, noise, vignette, grain, clouds, stars) | **DRAW** | cookbook below |
| Painterly / textured / photographic artwork (a rendered scene or material) | **GEN** | |

Litmus test: if a native version would look crude next to the reference, GENERATE. When in doubt and the element has real illustrative detail, GENERATE.

## Hard rules

1. **Never generate text.** Generate the wordless object; place every word as a `TextPlus` on top. A generated asset with legible text is wrong: regenerate wordless.
2. **Never generate the whole card/frame as one image.** Generate only the content object; build the chrome as separate named units so each can pop, reveal and parallax.
3. **Hard cap ~4-6 generated assets per frame.**
4. **One clean asset per distinct object**, then place, instance (`Instance_` tools share settings) or `Fuse.Duplicate` it.
5. **Small is not generate.** Badges, chips, tooltips, lower thirds, legend swatches are chrome: surface as Background + mask, label as a separate Text+.
6. **A gradient or glow is DRAW.** 2-stop -> `Background` `Type` "Vertical"/"Horizontal" (Python-settable corner colors); 3-4 stop corner blend -> `Type` "Corner"; N-stop or radial -> `Type` "Gradient" with a `Gradient` value (set it in `.setting`: `Gradient = Input { Value = Gradient { Colors = { [0] = {r,g,b,a}, [0.5] = {...}, [1] = {...} } } }`; Python SetInput of a Gradient table is unverified). Read the colour back (`GetInput`) and render; never fall back to a baked PNG.
7. **Build, don't bake, by ANY method.** Do not render a plate, badge, button, gradient or any text into a PNG yourself with PIL/Python/ffmpeg and Load it. That is the same baking. PIL is for measurement and audits only.
8. **Never disable or delete a node because a fill "didn't apply".** Read the input back with `GetInput`, check the colour went to the right split inputs (`TopLeftRed/Green/Blue`, not a hex string), check the mask actually has a shape (an empty mask blanks the image), check `Merge.Background` exists (a Merge with only a Foreground outputs nothing), render and look. Keep the node enabled.
9. **Circular/arc text is DRAW with native Text+.** Text+ `LayoutType` Circle (index 2 by manual menu order Point/Frame/Circle/Path: unverified) or Path (index 3) with `PositionOnPath`; spin via layout `AngleZ` expression (`time/24*12` = 12 deg/s at 24 fps). Two arcs (stamp): two Text+ nodes, bottom one flipped to read upright; build both inside one `SEAL` unit. Never bake a seal, never scatter per-character Text+ nodes by hand. The emblem ring behind may be [GEN] or DRAW (`sEllipse` `Solid` 0 + `BorderWidth`).

> **Symptom self-check before declaring done:** if any text cannot be edited in the Inspector or any gradient cannot be retuned, you generated an image where you should have built. Regenerate that asset wordless/empty and rebuild the text as Text+ and the gradient as a Background gradient.

## The generate-and-composite pipeline

1. **Style anchor:** crop the element region from the reference (as a generator style reference only, never as an asset).
2. **Generate wordless** with the style lock prepended; the user's defaults (Nano Banana Pro 2K stills, Seedance 2.5 1080p footage) unless they name another model. All [GEN] jobs in one parallel batch; only [GEN] content enters the batch. Plates, pills, badges and buttons never enter it, not even as a "bake now, rebuild later" hedge.
3. **Import:** Loader (stills) or MediaIn (footage) into a `MEDIA_<Name>` node; verify dimensions.
4. **Fit and clip** into its frame (cover-fit expression + rounded mask, Phase C).
5. **Animate** it like any other unit (house reveal, own `_Xf`).

## Blend the GEN asset into the built chrome

1. **Linearize the blend** (the AE "Blend Colors Using 1.0 Gamma" move): Fusion blends whatever values arrive. With Resolve Color Management OFF, linearize gamma-encoded inputs before compositing high-contrast assets over chrome: `GamutConvert` `SourceSpace` "Rec709" (or "SimplifiedsRGB"), `RemoveGamma` 1, `OutputSpace` "NoChange"; composite; then one final `GamutConvert` `SourceSpace` "NoChange", `OutputSpace` "Rec709", `AddGamma` 1 before MediaOut. MediaIn/Loader "Remove Curve" is the alternative on the source. With RCM ON, add no conversions (fusion-realities §3). Unverified in this stack: render both ways and compare halos at glow rims and antialiased cutout edges.
2. **Grade with a node, not on the asset.** Fusion has no adjustment layers: an effect node on the stream IS the adjustment layer, and its `Blend` (0-1) is its opacity. To seat an asset: put `ColorCorrector`/`BrightnessContrast` on the asset branch before its Merge; to glow/darken/push contrast relative to the chrome, merge a graded copy over it with Merge `ApplyMode` "Screen" (brighten/glow), "Multiply" (seat into shadow) or "Overlay" (detail/contrast) and tune `Blend`. Keep it a separate node so it stays re-tunable per shot.

Order matters: a node's `EffectMask` and `Blend` apply to that node's finished output, so a grade node after the Merge sits on the finished, effected composite.

## Native texture / background cookbook (never generate a PNG for these)

Measure size and spacing FROM the reference (count cells across the frame, `scanline` for exact stripes), then build procedurally. Fractions below are of frame width unless stated.

| Texture | Node chain | Starting values (status: unverified) |
|---|---|---|
| Straight grid | `KD_Lines` (two line sets) -> Merge over BG, `ApplyMode` "Normal", `Blend` 0.3-0.6 | `Angle1` 0, `Angle2` 90 (default), `Spacing1`/`Spacing2` = cell_px/W, `Thickness1`/`Thickness2` = line_px/W (1-2 px), `Softness1`/`Softness2` 0; line colour: `Color1*` inputs of KD_Lines (check TSV) or tint after with ColorCorrector |
| Diagonal crosshatch | same, `Angle1` 45, `Angle2` 135 | no oversizing needed (procedural, fills the frame) |
| Grid (shape route) | `sRectangle` (thin line) -> `sGrid` (`CellsX`/`CellsY`, `XOffset`/`YOffset`) -> `sRender` -> Background `EffectMask` | sShape units unmeasured; measure once |
| Scanlines | `KD_Lines` one set, `Angle1` 0 (verify orientation), `Spacing1` 2-8 px/W, `Thickness1` half of spacing -> Merge `ApplyMode` "Multiply", `Blend` 0.1-0.3. Pixel-exact alternative: `TV` `ScanLines` 1 (drops every 2nd line; resolution-dependent) | |
| Vignette | `BrightnessContrast` `Gain` 0.6-0.85 (AE Amount 15-40 %) with `EffectMask` = `EllipseMask` `Width` 1.15, `Height` 0.65, `SoftEdge` 0.25-0.4, `Invert` 1. All-in-one alternative: `FilmLookCreator` `VignetteIsEnable` 1, `VignetteAmount` 0.15-0.4, `VignetteSize` 0.25 (disable its other looks) | |
| Film grain | `FilmGrain` last before MediaOut | `MasterStrength` 0.02-0.06 (AE 2-6 %; strength = +/- variation of a pixel value), `MasterXSize` 1.0, `Monochrome` 1, `Complexity` 8, `LogProcessing` 1, `TimeLockSeed` 0; `Blend` 0.3-0.5 for AE "opacity 30-50 %" |
| Soft ambient glow blob | `Background` in glow colour with `EllipseMask` (small, NOT full frame, `SoftEdge` 0.2-0.4) -> Merge `ApplyMode` "Screen", `Blend` 0.04-0.10, placed where the reference light is | AE 100-150 px box blur at 1080 -> SoftEdge ~0.05-0.08 of width (calibrate) |
| Dotted grid | `KD_Lines` with dots: `DotSpacing1` = `Spacing1`, `DotLength1` small (0.05-0.1), round via `DotSoftness1`; or `sEllipse` -> `sGrid` -> `sRender` | low `Blend` |
| Clouds / organic field | `FastNoise` -> Merge `ApplyMode` "Screen", `Blend` 0.05-0.15 | `Detail` 3-5, `Contrast` 1.2 (AE 120), `Brightness` -0.3 (AE -30), `XScale` 1-2 (AE Scale 150-300 = big features; FastNoise direction of Scale unverified: calibrate), `SeetheRate` 0.02-0.05 for keyless evolution (AE Evolution `time*30`) |
| Plasma / interference | `Plasma` | `Scale` 1, `Operation` 0-9, `Phase` keyed 0 -> 1 per loop for colour cycling |
| Sky gradient | `DaySky` (`Time`, `Turbidity`, `Exposure` 0.72) or `Background` "Vertical" | |
| Starfield | `pEmitter` (`Number` at frame 0 only, `Velocity` 0, `Lifespan` >= comp length) -> `pRender` (`OutputMode` "TwoD") with small blob style; or `sEllipse` (2-8 px) -> `sDuplicate` + `sJitter` (`Shape.OffsetX.Min/Max` +/-0.1, `Shape.SizeX.Min/Max` 0.3-1) -> `sRender`; sparkle = two crossed thin `sRectangle`; twinkle = `PerturbNumber` on `Blend` | 6-14 stars for UI backgrounds, hundreds with particles |
| Dust motes | `pEmitter` `Number` 0.5-2 per frame, `Lifespan` 120-200, slow `Velocity`, + `pTurbulence` -> `pRender` "TwoD"; set pre-roll before judging a frame | |
| Seamless tile | `KD_Seamless` after any procedural source (FastNoise has no tile option) | |

Decision rule (replaces AE's `data-pattern` vs `data-gen`): a repeating geometric texture is ALWAYS a procedural node; raster generation is reserved for genuinely photographic or pictorial content, never text, never glows, never a flat geometric texture.

---

