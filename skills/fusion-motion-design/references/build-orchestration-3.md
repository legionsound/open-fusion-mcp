<!-- build-orchestration.md part 3 of 6; index: build-orchestration.md -->
# Module 2: Visual Matcher (Visual Passport + Effect Atlas)

Dissect a reference image and rebuild its visual properties with built-in Fusion nodes only (no third-party Fuses/OFX unless verified present). It complements the Scene Director (direction) and fusion-realities (IDs). When the whole frame must be reconstructed, feed this passport into the Phase A Fidelity Passport and the UI Rebuilder.

## Hard rule (before any node is created)

1. Read the reference image.
2. SAMPLE colors and gradients with `measure_ref.py`; never name them by eye. Each result carries hex and rgb 0-1; keep the rgb for inputs. If you cannot measure, sample by eye from a zoomed crop and say so per field.
3. Write the Visual Passport below.
4. Map every observed element to a node chain from the Effect Atlas.
5. Convert every hex to 0-1 per channel before any SetInput or `.setting` value: `#2dff8a` -> `(0.176, 1.0, 0.541)`. A hex string in a Fusion input silently fails.
6. Only then build (Phase B). Skipping the passport = building blind; eyeballed colors = washed-out, wrong-hue output.

## Visual Passport (fill before building)

```
PALETTE:        dark anchor #______ -> (r,g,b)   dark mid #______   light mid #______
                light highlight #______          accent #______
GRADIENT:       type [none|linear|radial|reflect|square|angle|4-corner|noise-driven]
                direction [top->bottom | left->right | NW->SE | center-out]
                stops [c1 @0 -> c2 @x -> c3 @1] (from `gradient`, with the axis pixels used)
LIGHTING:       key [top|top-left|left|bottom-up|front|back-rim]  hardness [hard|soft|mixed]
                temp [cool ~6500K|neutral ~5500K|warm ~3200K]  intensity [low|mid|blow-out]
                fill [none|low ambient|rim opposite]
TYPE:           face [geometric sans|humanist sans|serif|mono|display|hand]  weight  case
                tracking [tight -50|0|+50|+200 -> Text+ CharacterSpacing ~0.95|1.0|1.05|1.2 (calibrate)]
                color #______  treatment [plain|outline|glow|drop shadow|emboss|gradient fill|knockout]
DEPTH/SHADOW:   drop shadows [none|soft contact|hard offset|long directional]
                inner glow/shadow [y/n, color, strength]   bevel [none|subtle|pronounced|glassy]
TEXTURE:        grain [none|light|medium|heavy]  noise [none|digital|film|analog]
                artifacts [clean|banding|scanlines|chromatic aberration|dust]
ATMOSPHERE:     vignette [none|subtle|strong]  haze/bloom [none|mild|atmospheric]  leaks [none|corner|streak]
GRADE:          black point [lifted|normal|crushed]  white point [normal|rolled-off]
                saturation [desat|normal|punchy]  cast [neutral|teal/orange|blue|amber|mono]
MOTION IMPLIED: direction [static|slow push|pull|orbit|parallax slide]  rhythm [loop|one-shot|pulses]
```

Then three lines: **Hero element** (where the eye lands first), **Negative space** (how much is empty/dark), **Style label** (`cinematic | brutalist | minimal | Y2K | holographic | grunge | corporate | editorial | maximalist | glass | neon`).

## Effect Atlas: Visual -> Fusion node chain -> exact inputs and starting values

Chains use `A -> B -> Merge.Foreground` notation. All IDs are in the TSV unless marked. AE coordinates in the original assume 1920x1080; here every position is normalized, so no per-resolution recompute is needed except for pixel-derived sizes (`px/W`). Every row: status unverified (not yet rendered); verify = render the frame and compare against the passport probe for that element.

### A. Background fills and gradients

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Solid dark BG | `Background` (comp-sized) -> first Merge `Background` | `TopLeftRed/Green/Blue` = dark anchor, `TopLeftAlpha` 1, `UseFrameFormatSettings` 1 |
| Linear top -> bottom | `Background` `Type` "Vertical" | top colour in `TopLeft*`, bottom colour in `BottomLeft*` (Vertical uses top/bottom per manual; verify which corner inputs it reads) |
| Linear, N stops or any angle | `Background` `Type` "Gradient", `GradientType` "Linear" | `Start` {0.5, 1.0}, `End` {0.5, 0.0} (AE [960,0] -> [960,1080]); `Gradient` stops from the passport; `GradientInterpolationMethod` "LAB" for smoother mid-tones |
| Radial centerlight | same, `GradientType` "Radial" | `Start` {0.5, 0.5} (center), `End` {0.5, 0.0} (radius point; AE [960,1080]); radius in X vs Y may follow aspect: verify it is round |
| 4-corner gradient | `Background` `Type` "Corner" | `TopLeft*`, `TopRight*`, `BottomLeft*`, `BottomRight*` from the palette. AE `Blend` 1.0 is inherent; AE `Jitter` 0.05 (anti-banding) -> `FilmGrain` `MasterStrength` 0.005 after it (banding appears only at 8-bit delivery) |
| Subtle wash / Tint (map black/white) | `BrightnessContrast` `Saturation` 0 -> `ColorCorrector` | `MasterRedOutputLow/Green/Blue` = dark colour, `MasterRedOutputHigh/Green/Blue` = light colour; `Blend` 0.3-0.6 (AE Amount to Tint 30-60) |
| Tritone | duotone above + `ColorCorrector` `CorrectionRange` MidTones: `MidTonesRedGain/GreenGain/BlueGain` toward the mid colour | approximation; exact N-stop map = `ColorCurves` with per-channel LUTBezier curves authored in `.setting` (curves live in the tool's nested `Tools`, setting-format gotcha 14) |
| Multi-stop toner (CC Toner, 5 stops) | `ColorCurves` per channel (.setting) | 5 stops at luminance 0, 0.25, 0.5, 0.75, 1 per channel |
| Animated organic gradient | `FastNoise` (`Type` 1 = Gradient colour mode, manual order Two Color/Gradient) -> Merge `ApplyMode` "Overlay" over BG | `Contrast` 1.0 (AE 100), `Brightness` 0, `XScale` ~1 (AE Scale 300, calibrate), `SeetheRate` 0.02 (keyless) or `Seethe` keyed 0 -> 1 |

### B. Glows, luminescence, neon

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Soft text/shape glow | element branch -> `SoftGlow` | `Threshold` 0.6 (AE 60), `Gain` 1.5 (AE intensity 1.5), `XGlowSize` 30 x W/1920 (AE radius 30 px; calibrate), glow colour via `RedScale/GreenScale/BlueScale` = accent/max(accent) (0..2 range). AE "Color A/B" two-tone: two SoftGlows with different scales |
| Hard punchy neon | `Glow` (tight) -> `Glow` (wide) | first: `XGlowSize` 8 x W/1920, `Glow` 1.0 (AE intensity 2.0; slider 0..1, values > 1 blow out to white), `ApplyMode` 2 (Threshold) with `Low` 0.7; second: `XGlowSize` 60 x W/1920, `Glow` 0.5 (AE 0.8), `Low` 0.5 |
| Big atmospheric bloom | merged stream -> `SoftGlow` (LIGHT group) | `Threshold` 0.4, `XGlowSize` 120 x W/1920, `Gain` 0.5, `Blend` 0.5-1 |
| Light sweep across element | `SWEEP_Fill` `Background` `Type` "Gradient", `GradientType` "Linear", stops {0: (1,1,1,0), 0.45: (1,1,1,0), 0.5: (1,1,1,0.35), 0.55: (1,1,1,0), 1: (1,1,1,0)} -> Merge.Foreground over the element, `ApplyMode` "Screen", `Operator` "Atop" (sweep only where the element has alpha) | 45 deg: `Start` {0,0}, `End` {1,1}; motion: key `Offset` 0 -> 1 over 18-24 f (Background `Offset`, `Repeat` "Once"); AE Width 25 -> band 0.05 wide; Sweep Intensity 35 -> peak alpha 0.35; Edge Intensity 1.5 -> add a thin brighter stop at 0.5 |
| God rays from a point | source (bright element with alpha) -> `Fuse.OCLRays` | `Center` = light point normalized, `Exposure` 1-2 (AE Intensity 100), `Decay` 0.01-0.02 (ray length; AE Radius 50), `Weight` 3, `Threshold` 0.6-0.8, `MergeOver` 1 |
| Lens flare burst | `HotSpot` (flare) + `Highlight` (star glints) | HotSpot `PrimaryCenter`, `PrimaryStrength` 0.5-1 (AE Intensity 50), `HotSpotSize` 0.25; Highlight `Low` 0.9, `Length` 0.2-0.8, `NumberOfPoints` 4-6, `Angle` 0-45 |
| Volumetric beam | `Background` beam colour + `PolylineMask` trapezoid (or `TriangleMask` `Point1..3`) `SoftEdge` 0.02-0.06 -> `SoftGlow` -> Merge `ApplyMode` "Screen" (AE Add) | AE thickness 4 -> 30 px = trapezoid ends 4 and 30 px x W/1920; AE Softness 60 -> SoftEdge; inside/outside colours = a 2-stop Background gradient along the beam. 3D alternative: `LightSpot` + `Fog3D` (depth cue, not true volumetrics) |

### C. Shadows

`Shadow` needs alpha on its input; its default `OutputMode` 0 returns image-with-shadow (1 = shadow only, index semantics per manual order; verify). `ShadowOffset` default {0.5, 0.5} = no offset. AE Opacity 0-255 quirk does not exist here: shadow opacity = `Alpha` 0-1.

Offset conversion from AE Direction d (deg, 135 = down-right) and Distance D px: `dx = D*sin(d)`, `dy_down = -D*cos(d)`; `ShadowOffset = {0.5 + dx/W, 0.5 - dy_down/H}`. D 10 at 135 deg on 3840x2160 (D scaled to 20 px) -> {0.5037, 0.4935}.

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Standard drop shadow | unit -> `Shadow` | `Red/Green/Blue` 0, `Alpha` 0.5 (AE 50 % = 128/255), offset from 135 deg / 10 px (x W/1920), `Softness` 0.004-0.008 (AE 15 px; slider 0..0.05, fraction-of-width assumption unverified), `LightDistance` 1 |
| Long offset shadow | `Shadow` | offset from 135 deg / 40 px, `Softness` 0, `Alpha` 1.0. True long cast: `Fuse.Duplicate` of the shadow shape, `Copies` 40, `Center` offset 1 px diagonal per copy, `MergeUnder` 1 |
| Soft floor contact | `Shadow` | offset 3 px down, `Softness` 0.02 (AE 40), `Alpha` 0.3 (AE 30 %) |
| Stacked depth shadows | `Shadow` -> `Shadow` -> `Shadow` | (2 px, soft 0.002, 0.25), (8 px, 0.008, 0.18), (24 px, 0.02, 0.12) |
| Coloured neon shadow | `Shadow` | `Red/Green/Blue` = accent, `Softness` 0.02-0.03 (AE 50), offset small or 0 |
| Inner shadow | unit alpha -> `Blur` of its inverted alpha (`ChannelBoolean` to build the inverse) offset by `Transform` -> Merge over the unit with `Operator` "Atop" | offset opposite the light, blur 4-8 px x W/1920, Blend 0.3-0.5. Text+: an element with `ElementShape` Text Outline, `OutsideOnly` 0, soft and offset can fake it |
| Contact shadow for 3D | `LightSpot` `ShadowLightInputs3D.ShadowsEnabled` 1 + catcher geometry; soft/coloured shadows need the Software renderer | |

### D. Bevel, emboss, 3D look

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Subtle text/shape emboss | unit -> `KD_Bevel` | `BevelSize` 2 x W/1920 (AE Edge Thickness 2; units unverified), `LightPosition` {0.25, 0.75} (AE light angle -60 = upper left; Y up), `Type` 0; white highlight strength via `Blend` 0.6 (AE Light Intensity 0.6) |
| Pronounced bevel | `KD_Bevel` | `BevelSize` 4-6 (scaled), `Blend` 0.8 |
| Relief / coin | `Filter` `FilterType` 0 (Relief; manual order Relief, Emboss Over, Noise, Defocus, Sobel, Laplacian, Grain) | `Angle` 135 (45 deg steps), `Power` 1-3 |
| Emboss over itself | `Filter` `FilterType` 1 (Emboss Over) | `Angle` 135, `Power` 1-2 |
| Glossy plastic | unit -> `KD_Plastic` | `BumpChannel` 4 (default), `BlurSize` 12 (default), `Low`/`High` 0.9/1 highlight range, `Position` = light {0.4, 0.4}, colour `ColorRed/Green/Blue` 1 (AE Specular 100) |
| Glass / refraction | BG copy -> `Displace` (`Foreground` = a height map from the shape: `Blur` of its alpha) -> clip to shape | `Type` 0 (Radial) or 1 (XY), `RefractionStrength` 0.1 (AE Refraction 1.5; calibrate), `XRefraction`/`YRefraction` 0.02; softness = map blur 7 px (AE Softness 7). See the glass module for the full native rig |
| Metallic chrome | `Displace` glass + `ColorCorrector` duotone (dark steel to white) + `SoftGlow` | chain the three; brushed metal = `FastNoise` with `LockXY` 0 and `XScale` >> `YScale` as the map |
| Real 3D look | `Text3D`/`Extrude3D` (`ExtrusionDepth`, `BevelDepth`, `BevelWidth`) + `LightDirectional`/`LightSpot` + `MtlBlinn` or `MtlCookTorrance` -> `Renderer3D` | Fusion does this natively; use it when the reference shows true perspective or lit bevels |

### E. Texture, grain, noise

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Film grain | final stream -> `FilmGrain` | `MasterStrength` 0.06 (AE Intensity 0.6 feel), `MasterXSize` 1.0, `Monochrome` 0 + `ColorStrength` 0.5 (AE Saturation 0.5) or `Monochrome` 1 (AE monochromatic), `LogProcessing` 1 |
| Digital noise | `FilmGrain` | `LogProcessing` 0, `MasterRoughness` 0, `Complexity` 1, `MasterStrength` 0.10 (AE 10 %), `Monochrome` 1 (mono) / 0 (colour noise). Alternative: `Filter` `FilterType` 2 (Noise), `Power` 1-3, `Animated` 1 |
| Organic animated texture | `FastNoise` -> Merge `ApplyMode` "Overlay" | `Contrast` 1.2, `Brightness` 0, `XScale` ~1.5 (AE 200; calibrate), `Detail` 3 (AE Complexity 3), `SeetheRate` 0.02 or `Seethe` keyed 0 -> 1 over the duration (AE Evolution 0 -> 360) |
| Cracked / liquid distortion | `FastNoise` -> `Displace.Foreground`, content -> `Displace.Input` | `Type` 1 (XY), `XRefraction`/`YRefraction` 0.008 (AE Amount 15; range +/-0.1), noise `XScale` for AE Size 50, `Detail` 3, `SeetheRate` 0.03 |
| Wave displacement | content -> `Drip` | `Shape` for a horizontal wave (manual order; verify index), `Amplitude` 0.005 (AE Wave Height 5 px), `Frequency` ~ W/40/100 (AE Wave Width 40; calibrate), `Phase` keyed or `time/24*0.5` for travel |
| Stipple / halftone / mosaic | content -> `Transform` `Size` 1/16, `FilterMethod` Nearest (index 0 by manual order; verify) -> `Transform` `Size` 16, `FilterMethod` Nearest -> `BrightnessContrast` `Contrast` 0.4 to crush mids | AE 120 x 68 blocks at 1920 = block 16 px; no native mosaic node in the TSV (ResolveFX MosaicBlur is OFX: unverified here) |
| Hex / tessellated tiles | `KD_Pattern` | `Type` 0..2, `Size` 0.03 (AE Radius 30 px / 1920 x 2), `Thickness` 0.1, `Count`; hex availability unverified |
| Scanlines | `KD_Lines` (cookbook) or `TV` `ScanLines` 1 | Merge "Multiply", `Blend` 0.1-0.3 |
| VHS chromatic shift | content -> `KD_ChannelShifter` | per-channel `Center1`/`Center2`/`Center3` offsets +/-0.002 (about 4-8 px at 4K; channel order unverified), `BlurX1..3` 1-2; flicker `OverallEffect` via `PerturbNumber` |

### F. Blur, depth of field, atmosphere

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Soft background blur | BG -> `Transform` `Size` 1.06 (push blurred edge falloff outside the frame; replaces AE "Repeat Edge Pixels") -> `Blur` | `XBlurSize` 15-30 x W/1920 (calibrate), `Filter` "Gaussian", `LockXY` 1 |
| Cinema DOF / bokeh (2D) | layer -> `Defocus` | `XDefocusSize` 2-4 (AE Blur Radius 20; slider 0..10, calibrate), `LensType` 1 (Lens), `LensSides` 6 (hexagonal iris), `BloomLevel` 0.9, `BloomThreshold` 0.75 (AE Highlight Gain 2 -> raise BloomLevel) |
| Real DOF / rack focus (3D, Fusion does better) | ImagePlane3D planes at Z depths -> `Merge3D` -> `Renderer3D` `RendererType` "RendererOpenGL" with accumulation DOF enabled; `Camera3D` `PlaneOfFocus` keyed for a focus pull | OpenGL accumulation/DOF input IDs appear only after switching renderer (`RendererOpenGL.AccumQuality` seen in corpus; DOF toggle/amount IDs unverified: read `GetInputList()` after setting `RendererType`) |
| Depth-driven blur (2D with Z) | `VariBlur` (`BlurImage` = depth map, `XBlurSize`, `FocalPoint`, `DepthOfField`) or `DepthBlur` | |
| Motion blur trails | animated unit: `Transform`/`Merge`/`TextPlus` `MotionBlur` 1, `Quality` 16, `ShutterAngle` 360 (AE CC Force Motion Blur 16 samples / 360). Footage: `Dimension.OpticalFlow` -> `VectorMotionBlur` (`XScale` 1). Ghosting that shows only preceding motion: `Trails` (`GainRed` 0.6-0.9, needs pre-roll + Reset) | |
| Radial / zoom blur from center | `DirectionalBlur` | `Type` 3 (Zoom, as seen in corpus), `Center` = focus, `Length` 0.05 (AE Amount 50; range +/-0.1) |
| Directional speed blur | `DirectionalBlur` | `Type` 0 (Linear), `Angle` = motion angle (deg), `Length` 40/1920 = 0.021 (AE Blur Length 40 px; units unverified) |
| Atmospheric haze | merged content -> `SoftGlow` | `Threshold` 0, `Gain` 1, `XGlowSize` 30 x W/1920, `Blend` 0.3 (AE duplicate + blur 30 + Screen 30 %). 3D: `Fog3D` (`FogType` "Exp", `FogDensity` 0.05, `FogRed/Green/Blue` haze colour) |

### G. Colour grade, cinematic look (the GRADE group, topmost before MediaOut)

AE 0-255 levels -> Fusion 0-1: value/255. Use `ColorCorrector` Master range unless the row says otherwise.

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Crush blacks | `ColorCorrector` | `MasterRGBLow` 0.118 (AE Input Black 30) |
| Lift blacks (matte film) | `ColorCorrector` | `MasterRGBOutputLow` 0.059 (AE Output Black 15) |
| Punch contrast | `ColorCorrector` | `MasterRGBLow` 0.059 (15), `MasterRGBHigh` 0.941 (240), `MasterRGBGamma` 1.05 (verify gamma direction by render) |
| Teal-orange | `ColorGain` balance | `DarkRedCyan` -0.25, `DarkBlueYellow` +0.25, `HighRedCyan` +0.20, `HighBlueYellow` -0.20 (AE Color Balance -25/+25/+20/-20 of +/-100; slider sign conventions unverified: confirm shadows go teal, highlights orange, halve if heavy) |
| Cool blue unified | `ColorGain` | `GainRed` 0.92, `GainBlue` 1.10 (AE Photo Filter Cooling 80, Density 40; approximate). Kelvin alternative: `WhiteBalance` |
| Warm amber unified | `ColorGain` | `GainRed` 1.08, `GainBlue` 0.90 (AE Warming 85, Density 40; approximate) |
| Desaturated film | `BrightnessContrast` | `Saturation` 0.6 (AE -40) |
| Punchy modern | `BrightnessContrast` | `Saturation` 1.15 (AE +15) |
| Vignette | `BrightnessContrast` `Gain` 0.6 with inverted soft `EllipseMask` (cookbook) | AE CC Vignette -40 -> Gain 0.6 |
| Monochrome tinted | `BrightnessContrast` `Saturation` 0 -> duotone `ColorCorrector` (A. Tint row) | |
| Full film emulation | `FilmLookCreator` | `FilmLookCoreLook` "CoreLookCinematic", `ColorContrast` 1.25, `HalationAmount` 0.25, `BloomAmount` 0.25, `GrainAmount` 0.125, `VignetteAmount` 0.25 (defaults); set input/output colour space to match the pipeline; disable the modules you do not want (`FlickerIsEnable` 0, `GateWeaveIsEnable` 0) |

### H. Distortion, stylize, glitch

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Glitch slice | content -> `Transform` with `EffectMask` = 2-3 thin `RectangleMask` bands (`Height` 0.01-0.04) | `Center` expression, 4 frames at the glitch moment f0: `Point(0.5 + iif(time==f0,0.012,iif(time==f0+1,-0.008,iif(time==f0+2,0.005,0))), 0.5)` (AE Slant 0 -> 15 -> -10 -> 0 over 4 f); add `KD_ChannelShifter` on the same frames. Shear: `KD_Shear` |
| Pixel sort | content -> `KD_Sort` | `SortLength` 0.2-0.6, `Direction` 0/1, `RangeMin`/`RangeMax` luminance window, `RangeSeeds` |
| Mosaic / blocks | Transform down/up with Nearest (E. halftone row) | AE 80 x 45 blocks at 1920 = 24 px blocks |
| Liquid melt | FastNoise -> `Displace` | key `XRefraction`/`YRefraction` 0 -> 0.05 over 24 f at 24 fps (AE Amount 0 -> 50 over 1 s) |
| Cartoon outlines | `Filter` `FilterType` 4 (Sobel) -> invert (`BrightnessContrast` `Gain` -1 + `Brightness` 1, or ChannelBoolean) -> Merge "Multiply" over a posterized copy | AE Detail Threshold 1.5 -> raise contrast before Sobel |
| Find edges | `Filter` `FilterType` 4 (Sobel) or 5 (Laplacian, finer); Sobel -> `Glow` = neon edge look | inverted white-paper look as above |
| Posterize | `Custom` tool, `RedExpression` `floor(r1*5+0.5)/5` (same for Green/Blue) | 5 levels (AE Level 5); Custom expression syntax unverified |
| Roughen edges | matte -> `Displace` by FastNoise (small `XScale`) -> `ErodeDilate` `XAmount` -0.0005 | AE Border 30 -> noise amplitude; units calibrate |
| Stained glass | `KD_Fragments` or `KD_Pack` | inputs: see TSV; unverified look |
| Warp swirl / dent | `Vortex` (`Size` 0.5, `Angle` 180, `Power` 2), `Dent` (`Size`, `Strength`) | |

### I. Light leaks, atmosphere

| Observed | Fusion chain | Inputs and starting values |
|---|---|---|
| Corner light leak | `LEAK_Fill` warm `Background` + `EllipseMask` at the corner (`Width` 0.6, `SoftEdge` 0.3-0.5) -> Merge `ApplyMode` "Screen", `Blend` 0.4 | AE blur 80 = the SoftEdge; drift `Center` slowly (0.02 over 5 s) and breathe `Blend` with a slow sine |
| Volumetric beam | B. beam row + `Glow` | Merge "Screen" (AE Add; or Normal with `SubtractiveAdditive` 0 for additive) |
| Dust motes | cookbook particles (Fusion better than AE wiggled shapes) | `pEmitter` -> `pTurbulence` -> `pRender` "TwoD" |
| Smoke / fog | `FastNoise` grey, `Contrast` 0.6, `XScale` 0.7 (AE Scale 400: big features), `SeetheRate` 0.02 -> Merge "Overlay" or "Screen", `Blend` 0.4 | 3D: `Fog3D`, `FastNoiseTexture3D` on planes |
| Film burn | `FastNoise` high contrast -> `ColorCorrector` warm (orange/white) -> `EllipseMask` at `Center` -> Merge "Screen", key `Blend`/`Brightness` | AE Burn 0.5 -> Blend 0.5; unverified look |

### J. Type treatments

Text+ builds most treatments inside ONE node via shading elements 1-8 (element 1 on by default; others need `EnabledN` 1). Element inputs follow the suffix pattern `ElementShapeN`, `ThicknessN`, `RedN`..`AlphaN`, `OpacityN`, `SoftnessXN`/`SoftnessYN`, `OffsetN`, `TypeN`, `ShadingGradientN`, `LevelN`, `RoundN`, `ExtendHorizontalN`, `PriorityBackN`; the TSV lists element 1 only, higher suffixes come from the corpus (setting-format §3). Enum indices by manual order (unverified): `ElementShapeN` 0 Text Fill, 1 Text Outline, 2 Border Fill, 3 Border Outline; `TypeN` 0 Solid, 1 Image, 2 Gradient; `LevelN` Text/Line/Word/Character. `SortShadingElements` = Priority order.

| Observed | Fusion construction | Inputs and starting values |
|---|---|---|
| Stroke / outline | Text+ element 2 | `Enabled2` 1, `ElementShape2` 1, `Thickness2` 0.02-0.04 (AE Brush 2-4 px; units calibrate), colour `Red2/Green2/Blue2`, below the fill via priority |
| Hollow / knockout | outline only: `Enabled1` 0 (fill off) + outline element; or cut text out of a plate: Merge `Background` = Text+, `Foreground` = plate, `Operator` "Held Out" | plate shows everywhere except the glyphs |
| Gradient-filled text | element 1 `Type1` 2 | `ShadingGradient1` stops, `ShadingMappingAngle1` 90 (vertical), mapping level Text (one gradient across the word) or Character |
| Glowing edge text | element 2 white outline + text branch -> `SoftGlow` tinted accent (`RedScale`...) | `Threshold` 0.5, `XGlowSize` 15 x W/1920 |
| Soft drop shadow | element 2 `ElementShape2` 0, colour black, `Opacity2` 0.6, `SoftnessX2`/`SoftnessY2` 2-5, `Offset2` {0.005, -0.005} (check Y sign), priority behind element 1 | or the `Shadow` node on the Text+ output |
| Box behind text (lower third) | element 3 `ElementShape3` 2 (Border Fill), `Level3` Text or Line | `ExtendHorizontal3`/`ExtendVertical3` padding, `Round3` corner, auto-fits the copy |
| Typewriter reveal | Text+ `End` (Write On End) keyed 0 -> 1 | linear over n_chars x 1-2 f; per-character stepped look = expression `floor(time/2)/n_chars` clamp; caret/prefix: `KD_TextWrite` modifier |
| Per-character entrance (fade/scale/slide in chars) | `StyledTextFollower` modifier on `StyledText` | Follower `Delay` 1-2 f per char (0.05 s = 1.2 f at 24), keyed `Opacity1` 0 -> 1, `Offset1` {0,-0.02} -> {0,0}, character `CharacterSizeX/Y`; Follower values only take effect when keyed; spaces count as characters |
| Unstable / randomized text | `TextScramble` modifier (`Randomness`) for glyph churn; per-character jitter = Follower + `PerturbPoint` on `Offset1` (unverified) | whole-block wiggle: `PerturbPoint` on Text+ `Center` or the unit `_Xf.Center` |

## Build order after the passport (per scene)

1. Resolve the item comp; confirm W, H, fps (default for a free brief: timeline res, 5-8 s loop).
2. **BG group:** comp-sized `Background` (dark anchor), gradient variant if detected.
3. **ENV group:** grids, scanlines, noise overlays.
4. **CONTENT group:** Text+ and shape units for the hero element, exact palette values.
5. **EFFECTS group:** per-unit effects from the atlas (`SoftGlow` for luminescence, `Shadow` for depth, `KD_Bevel` if embossed).
6. **LIGHT group** on the merged stream: `SoftGlow` bloom, optional sweep.
7. **GRADE group** last: `ColorCorrector` -> `ColorGain` (or duotone) -> `FilmGrain` -> vignette, in this order, then `MediaOut1`.
8. **Loops:** continuous properties loop by expression (`time % N`), spline loop flags (`Loop`, `Pingpong`, `LoopRel` in `.setting` key `Flags`), or `SeetheRate` (keyless noise).
9. Audit frame via Saver (Phase E). Saving belongs to Phase F.

## Light in the passport

Fusion has real lights, but only in 3D (`LightSpot`, `LightDirectional`, `LightPoint`, `LightAmbient`, `LightDome`; shadows need the right renderer). For 2D content, route every lighting note through the LIGHT group: `HotSpot` centred on the hero for a directional key burst, `Fuse.OCLRays` for god rays, `SoftGlow` for bloom, a Screen/Atop gradient sweep for a moving key. Choose 3D lights only when the Scene Director picked the Camera3D mode.

## Don'ts (matcher)

- Don't add nodes you cannot justify from the passport. Node bloat = render time for no visual gain.
- Don't use `Shadow` where the reference shows an inner shadow; read the light direction.
- Don't glow every unit. Glow where there is actual luminescence, then at most one atmospheric bloom on the merged stream.
- Don't pick colours from libraries or by eye. Sample and paste the 0-1 values.
- Don't skip the tint/colour-balance step when the reference has a unified cast; that is how cinematic looks happen.

---

