<!-- liquid-glass.md part 1 of 3; index: liquid-glass.md -->
# Fusion Liquid Glass: native node rig (port of ae-liquid-glass)

Front line: a frosted, refracting "liquid glass" panel (pill, button, card, or any alpha shape)
built from native Fusion 21.1 tools only, driven by one controller, packaged as a GroupOperator
with published controls. Load it when a brief asks for glass UI, frosted panels, Apple-style
Liquid Glass, glass buttons/navbars/cards over video, or "make this element glass".

Status of everything below: **unverified (not yet rendered)** unless a line says **[live]** (observed
on Resolve Studio 21.1.0.14) or **[builtin]** (copied from a Blackmagic-shipped template in the local
corpus). A later pass tests it live; the NEEDS-LIVE-VERIFY list at the end is the test plan.

**Live pass 2026-09-26 (Resolve 21.1.0.14, UHD):** the section 7 `.setting` pasted and rendered over a
colorful gradient + Text+ backdrop. Two defaults were wrong and are fixed below: `GlassLens` Type 0
(Dent 1) made a pinched blob at the lens center (now Type 5, Sine Dent: smooth bulge), and Frost 40
erased the backdrop completely (Fusion blur scales with frame width, sigma about 1.25 x XBlurSize px
per 1920 px of width; now 12 at every resolution). Renders: `renders/verify/glass_*.png`,
contact sheet `renders/verify/sheet_glass.png`.

Sources: the After Effects liquid-glass skill (see CREDITS.md); IDs from `fusion-reference/data/fusion-21.1-inputs.tsv`
(plus the full live input dump for inputs the TSV filter dropped); `.setting` grammar from
`skills/fusion-reference/references/setting-format.md`; measured units from
`skills/fusion-reference/references/fusion-realities.md`; builtin evidence from
`corpus/builtin/Fusion/How To/Displace 2D.setting`, `Backgrounds/Plasmic.setting`,
`Tools/Advanced Camera Shake.setting`, `Backgrounds/Spot Ground.setting`.

---

## 0. Target look (what "correct" is), unchanged from AE

- Bright thin arcs on the TOP-LEFT and BOTTOM-RIGHT rims only (both, never one).
- A whisper-subtle darker rim at the edge, about 5-8 % darker, never a dark outline.
- Background visibly BENDS in a band along the edges; interior is soft-blurred and slightly
  magnified (x1.05-1.15) with a gentle lens curvature; colors behind are a little richer (x1.3 sat).
- A soft shadow floats below the panel.
- Optional: very fine frost grain inside the panel only.

If you see a dark rim, a dark halo just inside the edge, or the interior shifting uniformly with no
edge band, a step below went wrong (checklist, section 9).

## 1. Fusion-native decisions (read this before building)

| Decision | Fusion choice | Why it differs from AE |
|---|---|---|
| "Adjustment layer with alpha matte of Main" | Process the **full-frame** background branch, then cut it with the pill **once** at a Merge `EffectMask` | Blurring after masking pulls transparent black into the edge (dark halo). Full-frame processing is exactly what the AE adjustment layer did. |
| Hidden guide layer "Main" + 5 duplicate pill layers | One `RectangleMask` per role, every geometry input an **expression** on the controller | Masks are cheap, chainable (`PaintMode`), and one mask output can feed many tools. No "identical duplicate" drift. |
| RM-hole / ED-hole choker layers | Mask chains: second mask with negative `BorderWidth` and `PaintMode = "Subtract"` wired into the first mask's `EffectMask` **[builtin]** | Same ring, no hidden layers. |
| Refraction map (gray ring + vertical ramp, blur 30, Displacement Map vertical -110) | Blurred pill -> `CreateBumpMap` -> `BrightnessContrast` Brightness -0.5 -> `Displace` Type 1 (XY) **[builtin chain in Plasmic.setting]** | One node refracts along the true surface normal on BOTH axes (the AE tool needed two orthogonal ring maps for "radial" mode). Band width = one blur value. |
| CC Glass (bump from BG lightness) | Optional second XY `Displace` fed by a bump map of the blurred backdrop, with `LightPower` for the CC Glass shading | Same job, same idiom. |
| CC Lens | `Dent` (Type 0, "Dent 1" bulge) centered on the controller | Built-in warp; KD_Spherize is an alternative. |
| Transform Scale 110 after Displacement | `Transform` Size 1.10 **before** the warps, pivot on the panel | Displace samples its map in output space; a scale after it pushes the bend band under the mask edge. Deliberate reorder. |
| Solid layers in Multiply / Normal 40 % / Add | Color tools with an `EffectMask`: `BrightnessContrast` Gain (multiply), Lift (lerp to white), Brightness (add) | Mathematically exact equivalents, one node each, always at the stream's resolution, no premultiplied-blend-mode edge darkening. |
| 2x CC Light Sweep (-64 deg, +118 deg) | ONE `Background` gradient, `GradientType = "Reflect"`, used as a `BitmapMask` and multiplied into a thin rim ring | A reflected linear gradient is symmetric, so one node lights both opposite arcs. |
| CTRL null + toComp expressions | `Custom` tool `GlassCtrl` (NumberIn1..8, renamed) referenced by SimpleExpressions **[live pattern]** | Expressions reference tool names, not layer indices or comp spaces; they survive grouping. No toComp needed. |
| "Controller" null sliders | Second `Custom` tool `GlassLook` + direct publishing of tool inputs in the GroupOperator | Two controllers, same split as AE (CTRL null for motion, Controller null for look). |
| BG precomp + index-based Bump Map / Displacement layer params | A `PipeRouter` named `GlassIn` that every consumer wires from | Wires survive grouping, duplication and nesting. AE packaging failure #1 (index drift) does not exist here. |
| `ae_build_liquid_glass` one call | Paste one `.setting` (section 7) with `comp.Execute('comp:Paste(bmd.readfile([[path]]))')` **[live route]** | The Fusion one-call build. Python per-tool build (section 6) is the fallback. |

Fusion does better than AE here: 32-bit float (rim highlights above 1.0 bloom correctly), node reuse
(one pill mask feeds 4 consumers), expressions on any input, a real XY displacement in one node, a
pre-mask `GlowMask` on SoftGlow that lets the rim bloom spill past the rim, and alpha mode (glass
from any live `TextPlus` or logo alpha via `BitmapMask`).

## 2. The rig, layer by layer (AE job -> Fusion nodes)

| # | AE layer | Job | Fusion node(s) (RegID) | Key inputs |
|---|---|---|---|---|
| 11 | `BG` precomp | what the glass distorts | `GlassIn` (`PipeRouter`) | `Input` <- your background (MediaIn1, a Merge, anything) |
| 10 | `CTRL` null | moves/scales the rig | `GlassCtrl` (`Custom`) | `NumberIn1` X, `NumberIn2` Y, `NumberIn3` Scale, `NumberIn4` Width, `NumberIn5` Height, `NumberIn6` Roundness, `NumberIn7` Bezel px, `NumberIn8` Refraction |
| - | `Controller` null | look sliders used by expressions | `GlassLook` (`Custom`) | `NumberIn1` Rim Angle, `2` Rim Arc, `3` Rim Thickness, `4` Shadow Drop, `5` Shadow Soft, `6` Edge Soft, `7` Edge Choke, `8` Lens k |
| 7 | `Main` (hidden guide) | panel geometry | `PillMask` (`RectangleMask`) | `Center`, `Width`, `Height`, `CornerRadius` all expressions on `GlassCtrl` |
| 9 | `Shadow` (Drop Shadow, shadow only) | floor shadow | `ShadowMask` (`RectangleMask`) + `ShadowDarken` (`BrightnessContrast`) | Gain 0.70 = 30 % black; mask offset down, SoftEdge |
| 8 | `Effects` adjustment: Transform | magnify 110 % | `GlassMagnify` (`Transform`) | `Size` 1.10, `Center` = `Pivot` = panel center |
| 8 | `Effects`: CC Lens | lens curvature | `GlassLens` (`Dent`) | `Type` 5 (Sine Dent; Type 0 pinches, live), `Center`, `Size`, `Strength` 0.3 |
| 8 | `Effects`: CC Glass | backdrop-driven micro refraction + shading | `BodyHeight` (`Blur`) -> `BodyNormal` (`CreateBumpMap`) -> `BodyCenter` (`BrightnessContrast`) -> `BodyRefract` (`Displace`) | Type 1, X/YRefraction 0.006, LightPower 0.5 |
| 2+1 | `Refraction Map` + `RM-hole` | the refracting rim band | `BezelSrc` (`Background` white, EffectMask PillMask) -> `BezelHeight` (`Blur`) -> `BezelNormal` (`CreateBumpMap`) -> `BezelCenter` (`BrightnessContrast` Brightness -0.5) -> `RimRefract` (`Displace`) | Type 1 (XY), XChannel 0 (Red), YChannel 1 (Green), X/YRefraction = `GlassCtrl.NumberIn8` |
| 8 | `Effects`: Gaussian Blur 40 | frost | `GlassFrost` (`Blur`) | `XBlurSize` 12 at any resolution (live-calibrated) |
| - | (look lever "saturation 130 %") | richer backdrop | `GlassSat` (`BrightnessContrast`) | `Saturation` 1.3 |
| - | (new) frosted grain | frost texture | `GlassGrain` (`FilmGrain`) | `MasterStrength` 0.03 |
| 8 | alpha matte to `Main` | cut glass to the pill | `GlassComp` (`Merge`) | `Background` <- ShadowDarken, `Foreground` <- GlassGrain, `EffectMask` <- PillMask |
| 6 | `Color` white 40 % | milky tint | `GlassTint` (`BrightnessContrast`) | `Lift` 0.40, EffectMask PillMask |
| 5+4 | `Edge Darkness` (#EAEAEA multiply, blur 15) + `ED-hole` | whisper rim | `EdgeDarkOuter` + `EdgeDarkHole` (`RectangleMask`, Subtract) -> `EdgeDarken` (`BrightnessContrast`) | `Gain` 0.92 (= multiply by #EAEAEA) |
| 3 | `Edge Shine` (2x CC Light Sweep, Add) | top-left + bottom-right arcs | `RimGradient` (`Background` Gradient/Reflect) -> `RimArc` (`BitmapMask`) -> `RimOuter` (Multiply) -> `RimHole` (Subtract) -> `RimLight` (`BrightnessContrast` Brightness 0.6) -> `RimBloom` (`SoftGlow`, `GlowMask`) | one gradient lights both arcs |
| - | "Glass Opacity" knob | fade whole rig | `GlassFade` (`Merge`) | `Background` <- GlassIn (clean), `Foreground` <- RimBloom, `Blend` 0..1 |

### Node graph (ascii)

```
Controllers (not in the image flow):  GlassCtrl (Custom)   GlassLook (Custom)

Masks (all geometry = expressions on GlassCtrl/GlassLook):
  PillMask ------------------------------+--> BezelSrc.EffectMask
                                         +--> GlassComp.EffectMask
                                         +--> GlassTint.EffectMask
  ShadowMask -----------------------------> ShadowDarken.EffectMask
  EdgeDarkOuter -> EdgeDarkHole(Subtract) -> EdgeDarken.EffectMask
  RimGradient -> RimArc(BitmapMask, Invert) -> RimOuter(Multiply) -> RimHole(Subtract)
                                         +--> RimLight.EffectMask
                                         +--> RimBloom.GlowMask

Bezel normal map:
  BezelSrc -> BezelHeight(Blur) -> BezelNormal(CreateBumpMap) -> BezelCenter(BC -0.5) -> RimRefract.Foreground
Body normal map (optional):
  GlassLens.Output -> BodyHeight(Blur) -> BodyNormal(CreateBumpMap) -> BodyCenter(BC -0.5) -> BodyRefract.Foreground

Image flow:
  BG -> GlassIn -> ShadowDarken ------------------------------------------+--> GlassComp.Background
                        \-> GlassMagnify -> GlassLens -> BodyRefract -> RimRefract
                              -> GlassFrost -> GlassSat -> GlassGrain -----+--> GlassComp.Foreground
  GlassComp -> GlassTint -> EdgeDarken -> RimLight -> RimBloom -> GlassFade.Foreground
  GlassIn ------------------------------------------------------------------> GlassFade.Background
  GlassFade -> (MediaOut1 / downstream)
```

## 3. Node order and why (order matters)

1. **Shadow before the glass branch.** In AE the `Effects` adjustment sits above `Shadow`, so the
   glass refracts and frosts the shadow under it. `ShadowDarken` feeds both `GlassComp.Background`
   and the glass branch, so the shadow is seen through the panel.
2. **The glass branch is full frame; the pill cuts it once, at `GlassComp`.** The frost blur must
   sample pixels outside the pill (real backdrop blur does), and blurring an already-masked image
   averages in transparent black: a dark halo inside the edge. One mask at one Merge also means one
   antialiased edge instead of five slightly different ones.
3. **Magnify first.** `Displace` samples its map in output space. If a Transform scales after the
   rim displacement (AE order), the bent band moves 5 % outward and hides under the mask edge. With
   the Transform first, bezel map, mask and bend band stay registered.
4. **Lens, then body texture, then rim.** Interior curvature is the broadest warp; the CC Glass
   texture rides on it; the rim band is last so it dominates at the edge (AE: Glass -> Lens ->
   Displacement).
5. **Frost after every warp.** Blur hides resampling stair-steps in the bend band and blends the
   distortion (AE: blur added LAST).
6. **Saturation after frost.** Blur grays colors; boosting after the blur restores life (real glass
   materials boost ~130 %).
7. **Grain after saturation, before the cut.** Grain stays crisp over the blurred backdrop and only
   exists inside the panel.
8. **Tint after the cut.** It lifts the refracted image toward white only inside the pill (AE
   `Color` sits above `Main`).
9. **Edge darkness after tint.** Otherwise the tint lifts the rim darkening away (AE order).
10. **Rim light last, bloom after it.** Additive highlights go on top (AE `Edge Shine`, Add, top
    layer); `SoftGlow` must see the final highlight to bloom it.
11. **Fade against the clean background.** `GlassFade` blends the finished glass (shadow included)
    over the untouched `GlassIn`, so one `Blend` fades everything together.
12. Inside the map branches: **blur before `CreateBumpMap`** (the slope of the blurred edge IS the
    bezel), **recenter after it** (packed normals sit at 0.5; `Displace` XY treats 0 as no motion,
    per the Plasmic builtin).

## 4. Units and conversions (AE 4K px -> Fusion)

Fps assumption for timing: 24 fps primary, 25/30 given where timing matters.
Frame sizes: UHD 3840x2160, HD 1920x1080 (16:9). Normalized values are identical at both
resolutions; only pixel-valued inputs (blur/glow sizes, bezel px, HeightScale) change.

| Quantity | Fusion input | Convention | Formula |
|---|---|---|---|
| Panel center | `GlassCtrl.NumberIn1/2` -> mask `Center` | 0..1 per axis, Y up **[live]** | `x = px/W`, `y = 1 - py/H` |
| Panel width | `NumberIn4` -> `RectangleMask.Width` | fraction of frame WIDTH **[live]** | `w/W` |
| Panel height | `NumberIn5` -> `RectangleMask.Height` | fraction of frame HEIGHT **[live]** | `h/H` |
| Roundness | `NumberIn6` -> `CornerRadius` | fraction of half the shorter side **[live]**; 1.0 = pill | `r / (min(w,h)/2)`, clamp 1 |
| Soft edge / border | mask `SoftEdge`, `BorderWidth` | assumed fraction of frame width (VERIFY) | `px/W` |
| Shadow drop | `GlassLook.NumberIn4` (Center Y offset) | fraction of frame height | `px/H` |
| Blur / glow size | `XBlurSize`, `XGlowSize` | NOT a pixel radius; **scales with frame width [live]**: Blur (Fast Gaussian) size 10 gave FWHM 30 px at 1920 wide and 58 px at 3840, sigma about 1.25 x size x W/1920 px | same value at HD and UHD; do not halve for HD |
| Displace strength | `XRefraction`/`YRefraction` | assumed fraction of width per unit map value (VERIFY) | AE 110 px @4K -> ~0.06 |
| Angles in expressions | SimpleExpressions | radians **[live]** | `deg*pi/180` |

AE reference values converted (reference pill 755x469 @ UHD, capsule):

| AE value | Fusion value (UHD / HD) |
|---|---|
| Pill 755x469, Roundness 368 | `Width` 0.196615, `Height` 0.217130, `CornerRadius` 1.0 (both res) |
| Refraction ring 70 px centered (35 px inside), blur 30 | `GlassCtrl.NumberIn7` Bezel = 35 / 18 px; `BezelNormal.HeightScale` = 0.85 x bezel |
| Max Vertical -110 px | `GlassCtrl.NumberIn8` = 0.06 (sign VERIFY); X too for surface-normal mode |
| CC Lens k 0.025, Convergence 80 | `GlassLens.Size` = 1.0 x panel width, `Strength` 0.3 (VERIFY units) |
| Transform Scale 110 | `GlassMagnify.Size` 1.10 |
| Gaussian Blur 40 | `GlassFrost.XBlurSize` 12, HD and UHD (40 erased the backdrop, live) |
| CC Glass Softness 50, Displacement 100, Light 65 / Ambient 70 / Diffuse 60 | `BodyHeight.XBlurSize` 25 (HD too: blur is width-relative), `BodyNormal.HeightScale` 3, `BodyRefract` X/YRefraction 0.006, `LightPower` 0.5, `LightAngle` 135 |
| Edge Darkness #EAEAEA multiply, blur 15, choke 3 | `EdgeDarken.Gain` 0.92; `EdgeDarkOuter.SoftEdge` 0.0039, `BorderWidth` +0.001; `EdgeDarkHole.BorderWidth` -0.00078 |
| Light Sweep Width 120, Edge Thickness 0.8, Edge Intensity 60, Dir -64/+118 | `GlassLook.NumberIn2` Rim Arc 0.0156, `NumberIn3` Rim Thickness 0.00156 (6 px), `RimLight.Brightness` 0.6, Rim Angle 154 deg |
| Drop Shadow 30 %, 180 deg, distance 30, softness 80 | `ShadowDarken.Gain` 0.70, Drop 0.0139, `ShadowMask.SoftEdge` 0.0208 |
| Color white 40 % | `GlassTint.Lift` 0.40 |
| Saturation 130 % | `GlassSat.Saturation` 1.3 |
| Magnify knob 105-115 | `GlassMagnify.Size` 1.05-1.15 |

## 5. Recipes

Every recipe: status: unverified (not yet rendered).

### R1. Controller (`GlassCtrl`, `GlassLook`)

Purpose: the only things you type numbers into or animate. Every geometry input elsewhere is an
expression on these.

- `GlassCtrl` = `Custom`. Set `NumberIn1` 0.5, `NumberIn2` 0.5, `NumberIn3` 1.0, `NumberIn4`
  0.196615, `NumberIn5` 0.217130, `NumberIn6` 1.0, `NumberIn7` 35 (UHD) / 18 (HD), `NumberIn8` 0.06.
  Labels: `NameforNumber1..8` = "Center X", "Center Y", "Scale", "Width (w/W)", "Height (h/H)",
  "Roundness", "Bezel px", "Refraction". Hide points: `ShowPoint1..4` = 0.
- `GlassLook` = `Custom`. `NumberIn1` 154, `NumberIn2` 0.0156, `NumberIn3` 0.00156, `NumberIn4`
  0.0139, `NumberIn5` 0.0208, `NumberIn6` 0.0039, `NumberIn7` 0.00078, `NumberIn8` 1.0. Labels:
  "Rim Angle", "Rim Arc", "Rim Thickness", "Shadow Drop", "Shadow Soft", "Edge Soft", "Edge Choke",
  "Lens k". `ShowPoint1..4` = 0.
- NumberIn allowed range is +/-1e6 (live dump), so values above 1 and negative positions are legal.

Shared expression strings (C = center, W/H/R = geometry, S = scale):

```
C = Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2)
W = GlassCtrl.NumberIn4*GlassCtrl.NumberIn3
H = GlassCtrl.NumberIn5*GlassCtrl.NumberIn3
R = GlassCtrl.NumberIn6
```

Verify: change `NumberIn1` to 0.3 and every mask, the magnify pivot, the lens center and the rim
gradient move together; nothing stays behind.

### R2. Panel geometry (`PillMask`)

`RectangleMask`: `Center` = C, `Width` = W, `Height` = H, `CornerRadius` = R (all via
`SetExpression`). Leave `SoftEdge` 0 (the mask rasterizer antialiases; `ShapeRasterizer.Supersampling`
default 32).

Verify: in the viewer the mask is 755x469 px at UHD (378x235 at HD), capsule ends, centered.

### R3. Floor shadow (`ShadowMask` -> `ShadowDarken`)

- `ShadowMask` `RectangleMask`: `Center` = `Point(GlassCtrl.NumberIn1, GlassCtrl.NumberIn2 -
  GlassLook.NumberIn4*GlassCtrl.NumberIn3)`, `Width` = W, `Height` = H, `CornerRadius` = R,
  `SoftEdge` = `GlassLook.NumberIn5*GlassCtrl.NumberIn3`.
- `ShadowDarken` `BrightnessContrast`: `Input` <- `GlassIn`, `Gain` 0.70, `EffectMask` <- ShadowMask.
  Math: `x*(1-0.3*m)`, identical to 30 % black at the mask's alpha.

Alternative (unverified semantics): `Shadow` tool on a white pill with `OutputMode` 1 (shadow only,
inferred index) and `ShadowOffset`/`Softness`; its offset convention is unmeasured, so prefer the
mask version.

Verify: a soft darkening peeks out below the pill, about 30 px lower edge at UHD, gone above it.

### R4. Glass body chain (full frame)

- `GlassMagnify` `Transform`: `Input` <- ShadowDarken, `Center` = C, `Pivot` = C, `Size` 1.10.
- `GlassLens` `Dent`: `Input` <- GlassMagnify, `Type` 5 (Sine Dent, smooth bulge; live: Type 0 Dent 1 pinches to a point at the center), `Center` = C,
  `Size` = `GlassLook.NumberIn8*GlassCtrl.NumberIn4*GlassCtrl.NumberIn3`, `Strength` 0.3.
- `BodyRefract` (optional CC Glass stage, R6) then `RimRefract` (R5).
- `GlassFrost` `Blur`: `Input` <- RimRefract, `XBlurSize` 12 (UHD and HD; live-calibrated), `Filter` "Fast
  Gaussian" (default), `LockXY` 1.
- `GlassSat` `BrightnessContrast`: `Input` <- GlassFrost, `Saturation` 1.3.
- `GlassGrain` `FilmGrain`: `Input` <- GlassSat, `MasterStrength` 0.03, `MasterXSize` 0.8,
  `Monochrome` 1, `LogProcessing` 0 (display-referred comp; VERIFY), `TimeLockSeed` 0.
- `GlassComp` `Merge`: `Background` <- ShadowDarken, `Foreground` <- GlassGrain, `EffectMask` <-
  PillMask. `ApplyMode` "Normal", `Operator` "Over".

Verify: inside the pill the image is magnified, blurred and richer; outside it is untouched; the pill
edge has no dark or bright fringe.

### R5. Refraction band (bezel normal map -> `RimRefract`)

Purpose: the AE `Refraction Map` + `RM-hole` + Displacement Map, as a surface-normal refraction on
both axes.

- `BezelSrc` `Background`: `TopLeftRed/Green/Blue/Alpha` = 1, `EffectMask` <- PillMask. (Solid
  white pill on transparent; `UseFrameFormatSettings` 1.)
- `BezelHeight` `Blur`: `Input` <- BezelSrc, `XBlurSize` = `GlassCtrl.NumberIn7*GlassCtrl.NumberIn3`.
  The slope of the blurred edge is the bezel; the inside half of it is the visible bend band.
- `BezelNormal` `CreateBumpMap`: `Input` <- BezelHeight, `SourceChannel` "Luminance" (default),
  `FilterSize` "3", `WrapMode` "Clamp", `HeightScale` = `0.85*GlassCtrl.NumberIn7*GlassCtrl.NumberIn3`
  (keeps the normal profile constant as the bezel or resolution changes; VERIFY per-pixel derivative).
- `BezelCenter` `BrightnessContrast`: `Input` <- BezelNormal, `Brightness` -0.5 (packed 0.5-centered
  normals -> signed; the Plasmic builtin does exactly this before its XY Displace **[builtin]**).
- `RimRefract` `Displace`: `Input` <- BodyRefract (or GlassLens if R6 is skipped), `Foreground` <-
  BezelCenter, `Type` 1 (X/Y), `XChannel` 0 (Red), `YChannel` 1 (Green) (both defaults),
  `XRefraction` = `YRefraction` = `GlassCtrl.NumberIn8`, `LightPower` 0.

Modes (decision table):

| Want | Set | Note |
|---|---|---|
| Real glass, bends at ALL edges along the normal (AE tool "radial" default) | X and Y refraction = NumberIn8 | default |
| AE tutorial look, top/bottom bands only | `XRefraction` 0 | AE "Max Horizontal 0" |
| Cheaper lens-rim look (Blackmagic "Displace 2D" How-To style) | `Type` 0 (Radial), `Foreground` = a white ring mask image, `RefractionStrength` 0.2, `Center` = C | pushes from the center, not the normal; fine for circles |
| Bevel shading baked in | `LightPower` 0.3-2, `LightAngle` 112-135 | one-sided (bright/dim); keep R8 rims anyway |

Verify: a straight horizontal line in the background crossing the pill edge visibly curves inside a
band about 35 px deep (UHD); flat interior areas do not shift. If the whole interior shifts
diagonally, `BezelCenter` is missing or the neutral point differs (NEEDS-LIVE-VERIFY 1-2). If the
band pinches content inward instead of pulling outside content into the rim, negate NumberIn8.

Fallback bezel map (if `CreateBumpMap` encoding surprises): `Custom` tool `BezelNormalCT`, `Image1`
<- BezelHeight, `Setup1` = `1.0/w1`, `Setup2` = `1.0/h1`, `NumberIn1` = bezel px / 4,
`RedExpression` = `(getr1d(x-s1,y)-getr1d(x+s1,y))*n1`, `GreenExpression` =
`(getr1d(x,y-s2)-getr1d(x,y+s2))*n1`, `BlueExpression` = `0`, `AlphaExpression` = `1`. Output is
already signed: wire it straight to `RimRefract.Foreground` (no -0.5). Custom Tool per-pixel
functions are from the manual (J); CPU cost at UHD is higher.

### R6. CC Glass stage (optional, default on, subtle)

- `BodyHeight` `Blur`: `Input` <- GlassLens, `XBlurSize` 25 (UHD and HD: blur size is width-relative, live).
- `BodyNormal` `CreateBumpMap`: `Input` <- BodyHeight, `SourceChannel` "Luminance", `HeightScale` 3.
- `BodyCenter` `BrightnessContrast`: `Brightness` -0.5.
- `BodyRefract` `Displace`: `Input` <- GlassLens, `Foreground` <- BodyCenter, `Type` 1,
  `XRefraction` 0.006, `YRefraction` = expression `XRefraction` (same-tool link), `LightPower` 0.5,
  `LightAngle` 135.

Verify: bright/dark shapes behind the glass wobble very slightly and pick up faint top-left
shading; toggling the node (pass-through) should read as "a little less glassy", not a different look.
If it looks like water, halve `XRefraction`.

### R7. Tint and edge darkness

- `GlassTint` `BrightnessContrast`: `Input` <- GlassComp, `Lift` 0.40, `EffectMask` <- PillMask.
  Lift math is `x + lift*(1-x)` = 40 % toward white, exactly the AE white layer at 40 %.
  Colored tint: use `ColorCorrector` instead with per-channel `MasterRedGain` = 1-a,
  `MasterRedBrightness` = r*a (same for Green/Blue); a = tint opacity, (r,g,b) = tint color (VERIFY
  the correction order).
- `EdgeDarkOuter` `RectangleMask`: geometry C/W/H/R, `BorderWidth` 0.001 (grow ~4 px),
  `SoftEdge` = `GlassLook.NumberIn6*GlassCtrl.NumberIn3`.
- `EdgeDarkHole` `RectangleMask`: geometry C/W/H/R, `BorderWidth` =
  `-GlassLook.NumberIn7*GlassCtrl.NumberIn3`, `PaintMode` "Subtract", `EffectMask` <- EdgeDarkOuter.
- `EdgeDarken` `BrightnessContrast`: `Input` <- GlassTint, `Gain` 0.92, `EffectMask` <- EdgeDarkHole.
  0.92 = #EAEAEA; never go below 0.85.

Verify: zoom 400 % on the edge: a 3-4 px band just inside the edge and a soft falloff just outside
are 5-8 % darker; no line is visible at 100 %.

### R8. Rim lights (the two arcs)

- `RimGradient` `Background`: `Type` "Gradient", `GradientType` "Reflect", default gradient (black
  at 0 -> white at 1, as serialized in every builtin), `Start` = C, `End` =
  `Point(GlassCtrl.NumberIn1 + GlassLook.NumberIn2*GlassCtrl.NumberIn3*cos((GlassLook.NumberIn1-90)*pi/180), GlassCtrl.NumberIn2 + GlassLook.NumberIn2*GlassCtrl.NumberIn3*sin((GlassLook.NumberIn1-90)*pi/180)*comp:GetPrefs("Comp.FrameFormat.Width")/comp:GetPrefs("Comp.FrameFormat.Height"))`.
  Result: value 0 along a line through the center at Rim Angle, rising to 1 at Rim Arc distance on
  both sides (Reflect).
- `RimArc` `BitmapMask`: `Image` <- RimGradient, `Channel` "Luminance", `Invert` 1 (first in the
  chain, so Invert is unambiguous). Now 1 on the line, 0 beyond Rim Arc.
- `RimOuter` `RectangleMask`: geometry C/W/H/R, `SoftEdge` 0.0003, `PaintMode` "Multiply",
  `EffectMask` <- RimArc.
- `RimHole` `RectangleMask`: geometry C/W/H/R, `BorderWidth` = `-GlassLook.NumberIn3*GlassCtrl.NumberIn3`,
  `PaintMode` "Subtract", `EffectMask` <- RimOuter. Output = thin inner ring x arc weight: bright only
  where the line crosses the rim, i.e. top-left and bottom-right.
- `RimLight` `BrightnessContrast`: `Input` <- EdgeDarken, `Brightness` 0.6, `EffectMask` <- RimHole
  (`x + 0.6*m`, the AE Add of a 60 % sweep; float keeps values over 1).
- `RimBloom` `SoftGlow`: `Input` <- RimLight, `GlowMask` <- RimHole (pre-mask: restricts the glow
  source to the arcs, lets the bloom spill), `Threshold` 0.6, `Gain` 1.0, `XGlowSize` 8 (UHD) / 4 (HD).

Verify: two thin bright arcs, upper-left end cap and lower-right end cap, same brightness; rotate Rim
Angle 154 -> 135 and both arcs slide together toward the top-left corner and bottom-right corner.
One arc only = `GradientType` not "Reflect".

### R9. Fade and output

- `GlassFade` `Merge`: `Background` <- GlassIn, `Foreground` <- RimBloom, `Blend` 1.0.
- Downstream: `MediaOut1.Input` <- GlassFade (Fusion-page comp) or the group's `MainOutput1`.

Verify: `Blend` 0 returns the exact background (no shadow, no tint); 0.5 fades all parts together.

### R10. Alpha mode (glass from an existing element)

AE mode "an element already exists" (`sourceLayerName`). Replace the rectangle geometry with the
element's alpha so the glass follows ANY shape, including live `TextPlus`.

- `ShapeAlpha` `BitmapMask`: `Image` <- the element (e.g. `Label` TextPlus), `Channel` "Alpha".
  Use it wherever `PillMask` was used (BezelSrc, GlassComp, GlassTint).
- Rings: `BitmapMask` copies with `BorderWidth`/`SoftEdge` (BitmapMask has both) instead of
  RectangleMasks; `PaintMode` chains unchanged.
- `BezelHeight.Input` can take the element directly (its alpha blurred is the height).
- `GlassCtrl` X/Y still drive the magnify pivot, lens and rim line: set them to the element's
  center (for Text+: `Label.Center`).
- Show the element on top (AE `hideSource:false`): Merge it over `GlassFade`; hide it by not merging.

Verify: edit the text; bezel, tint and rims follow the new glyphs on the next frame without touching
the rig.

### R11. Auto-fit pill to a label (button variant helper)

From the builtin `Text Box.setting` idiom (expression on rendered text bounds), set on `GlassCtrl`:
`NumberIn4` = `(Label.Output[0].DataWindow[3]-Label.Output[0].DataWindow[1])/Label.Output[0].Width+0.04`,
`NumberIn5` = `(Label.Output[0].DataWindow[4]-Label.Output[0].DataWindow[2])/Label.Output[0].Height+0.05`.
Padding values are taste. Unverified in this rig; the idiom itself ships in a Blackmagic title.

Verify: type a longer label; the pill grows and the rims stay on the new end caps.

### R12. Optional true-3D variant

Only when the glass must sit in a moving 3D scene.

- Recommended: keep the 2D rig, feed it a 3D matte. Build the panel as `ImagePlane3D` (white
  material) under the same `Camera3D` as the scene, render it alone with a second `Renderer3D`
  (`SceneInput` <- its own `Merge3D`), and use that render's alpha through `BitmapMask` (R10). The
  3D renderer gives real perspective; refraction stays correct in screen space.
- Material-only alternative: `SphereMap` (`Image` <- the background) -> `MtlReflect`
  (`Reflection.Color.Material` <- SphereMap, `Refraction.RefractiveIndex.RGB` 1.1-1.5,
  `BackgroundMaterial` with opacity < 1) on a `Shape3D`/`ImagePlane3D`. This refracts an
  environment map, not the actual scene behind: good for abstract glass objects, wrong for UI glass.

Verify: orbit the camera; the matte version keeps rims on the panel's projected edge every frame.

