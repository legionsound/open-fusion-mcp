# 01 Construction: text, simple geometry, UI and 3D

Load when choosing how to represent an object, simplifying a traced or fragmented build, building UI chrome, logos or a volumetric product. Target: the reference's look; method: the smallest editable semantic Fusion graph. Units below assume a 3840x2160 comp (W, H); positions normalized 0-1, Y up.

## Choose the representation

| Visible thing | Fusion representation | Not this |
|---|---|---|
| Words, numbers, captions | `TextPlus` per semantic phrase; `StyledTextFollower` for per-character motion (03) | Outlined glyph paths, `sText` (no gradient fill), `Text3D` unless real extrusion is visible |
| One flat plate, card, pill, circle | `Background` + `RectangleMask`/`EllipseMask` on its EffectMask, or into a Merge | Stacks of colored fragments |
| Several vector parts that combine, cut, outline, repeat or draw on | sShape chain: `sRectangle`/`sEllipse`/`sNGon`/`sStar`/`sPolygon` -> `sMerge`/`sBoolean` -> `sOutline`/`sTransform` -> `sRender` | One PolylineMask per color patch |
| Custom silhouette | `sPolygon` (or `PolylineMask` on a Background) with a few Bezier points on real extrema | Auto-traced contours, hundreds of vertices |
| Gradient field | `Background` `Type`="Gradient" (04) | Quantized color bands |
| Logo | Authentic clean asset via `Loader` (alpha PNG/EXR), or a compact sShape rebuild | A crop of a screenshot |
| Photo, footage, organic detail | `Loader`/`MediaIn` in a replaceable media subgraph (05) | Generated UI, text or chrome baked into media |
| Volumetric product with visible thickness/perspective | Real geometry: `Shape3D`, `SurfaceFBXMesh` (OBJ/FBX), `SurfaceAlembicMesh`; `Camera3D`; lights; `Renderer3D`; live screen UI into `ImagePlane3D.MaterialInput` | `CornerPositioner`/`PerspectivePositioner` on a flat card, or a plane tilted to fake depth |
| Button, field, prompt window, dialog | Native `TextPlus` + rounded mask/shape + gradient `Background` + `SoftGlow`/`Blur`, one named group per control | UI bitmap, material plate, screenshot |

sShapes vs masks: use sShapes when parts are vector design (booleans, uniform outline, `sDuplicate`/`sGrid`, one antialiased raster at `sRender`, per-shape Style color). Use masks when the shape is a matte for an image (photo card corners, effect limits). Both expose `WritePosition`/`WriteLength` for draw-on. sShape results are only viewable through `sRender`.

Add complexity only where it explains visible design or independent movement. No universal node or vertex cap. Grouping 300 fragments into one Group does not simplify them.

## Pixel to Fusion conversion (live-verified 2026-09-26 unless marked)

| Quantity | Formula |
|---|---|
| Any Center/point | (x/W, 1 - y/H) |
| `RectangleMask` `Width`, `Height` | w/W, h/H (each axis relative to its own frame dimension) |
| `EllipseMask` `Width`, `Height` | w/W, h/W (both relative to frame WIDTH; a circle uses equal values) |
| Mask `CornerRadius` | r / (min(w,h)/2); 1.0 = pill |
| `TextPlus` `Size` | about 1.70 * font_px / W (Open Sans; em ~= 0.587*Size*W, cap height ~= 0.42*Size*W) |
| sShape `Translate.X` | (x - W/2)/W; 0 = centered (manual: normalized to width) |
| sShape `Width`/`Height`, `Translate.Y` | **all against frame WIDTH** (live-measured 2026-09-26 on 3840x2160 through `sRender`: `Width 0.5, Height 0.25` = 1920 x 960 px; `Translate.X/Y 0.1` = +384 px right / +384 px up). `Width = w/W`, `Height = h/W`, `Translate.Y = (H/2 - y)/W`. `CornerRadius` = fraction of half the shorter side (0.2 on 1920x960 = ~96 px), as on RectangleMask |
| 3D units | unitless; FBX/OBJ keep file scale (100 mm = 100 units) |

## Build from meaningful parts

Name parts after what they are, not how they were made. Example, a treasure chest:

```
CHEST_BODY  sRectangle (CornerRadius 0.15) --\
CHEST_TRIM  sOutline of body (Thickness 0.006) -> sMerge CHEST_BASE -> sRender CHEST_BASE_R --\
CHEST_LID   sPolygon (6 points) -> sTransform LID_HINGE (XPivot/YPivot at hinge) -> sRender --> Merge chain -> CHEST_OUT
CHEST_CLASP sEllipse + sRectangle -> sBoolean (Union) -> sRender ------------------------------/
CHEST_SHADOW sEllipse -> sRender -> Blur -> Merge (under everything, Blend 0.5)
```

Lid opening is one rotation (`sTransform` `ZRotation`) about a hinge pivot, not redrawn points. Deformation (squash of the lid) is either a scale on a correctly placed pivot or a few consistent-topology `sPolygon` poses; never per-frame reshaping.

## This user's construction requirements

- Build buttons, inputs, prompt windows, dialogs, panels and their states natively: `TextPlus`, rounded masks or sRectangles, `Background` gradients, `Blur`/`SoftGlow`, `Displace` for glass refraction. One named group per control (`BTN_Primary`, `FIELD_Prompt`). No generated UI images, no rasterized UI plates, no embedded control screenshots. A glass look is still a controllable native construction (continuous geometry, bevel/reflection gradient passes, displacement, blur, animated highlight).
- Never mask an object out of a reference screenshot and present it as the asset. Reference crops are for analysis and A/B comparison only. A logo inside a phone screenshot is not a standalone source asset: obtain the authentic asset, rebuild it compactly, or use an explicitly authorized generated original.
- Phones and other volumetric products: real geometry with bevels, side detail, material response and changing light, a `Camera3D` and `Renderer3D`. Qualified chain (2026-09-17): rounded OBJ via `SurfaceFBXMesh`, native UI subgraph into `ImagePlane3D.MaterialInput`, `Merge3D` + `Transform3D` rig, camera and lights into a world `Merge3D`, `Renderer3D`, then 2D overlays. For that classic renderer the screen used `SurfacePlaneInputs.Lighting.IsAffectedByLights`=0 and `MtlStdInputs.ReceivesLighting`=1 (both off = black, both on = overlit UI). Re-verify in pixels. Keep screen UI editable and check its registration through the move.
- Improve animation with measured staging, continuous velocity, motivated acceleration, overlap, anticipation, overshoot and settling on a shared object/camera rig (02). No random wobble or generic bounce to hide missing reference motion. Check intermediate frames at playback speed after rebuilding materials or geometry.

## Recipes

### R1 Pill button with label (status: unverified (not yet rendered))
Purpose: native, editable primary button. Target 480x120 px, center at (1920, 1400 px from top).

```
BTN_Fill Background (TopLeftRed/Green/Blue 0.16/0.47/1.0, EffectMask <- BTN_Shape)
BTN_Shape RectangleMask Center {0.5, 0.3519} Width 0.125 Height 0.0556 CornerRadius 1.0 SoftEdge 0
BTN_Label TextPlus StyledText "Continue" Size 0.0195 (44 px) Center {0.5, 0.3519} Font "Open Sans" Style "Semibold"
BTN_Fill -> BTN_Merge.Background ; BTN_Label -> BTN_Merge.Foreground ; BTN_Merge -> scene Merge.Foreground
```
Verify: pill ends are true semicircles at 4K; label optically centered (cap height, not bbox); edit label to "Continue with email" and confirm it still fits or that a width control follows it (06).

### R2 Soft contact shadow (status: unverified (not yet rendered))
`SHADOW_Shape sEllipse (Width 0.3, Height 0.04, Translate.Y below object) -> sRender -> Blur XBlurSize 20 -> Merge (Blend 0.45)` placed under the object merge. `XBlurSize` is not a pixel radius: calibrate the softness by render at delivery resolution. Verify the shadow does not clip at the Blur's `ClippingMode` Frame boundary and stays attached through the object's motion (connect its X to the object rig by expression).

### R3 Product with live screen (status: unverified for any new mesh; chain qualified 2026-09-17)
`SCREEN_UI (native 2D group) -> PHONE_Screen ImagePlane3D.MaterialInput`; `PHONE_Body SurfaceFBXMesh` + screen -> `PHONE_Rig Merge3D` -> `PHONE_XF Transform3D` -> `WORLD Merge3D` (+ `Camera3D`, `LightDirectional`, `LightAmbient`) -> `Renderer3D` -> 2D Merge under overlays. Verify registration of UI corners to the bezel at the widest rotation and a mid-turn frame.

## Python build pattern (current Fusion-page comp)

```python
def add(comp, reg, name, x, y):
    comp.SetActiveTool(None)            # live-verified: without this AddTool auto-connects to the active tool
    t = comp.AddTool(reg, False, x, y, False, False)
    t.SetAttrs({'TOOLS_Name': name})
    assert t.GetAttrs()['TOOLS_Name'] == name   # names with spaces/leading digits are silently stripped
    return t

comp.Lock()
try:
    fill  = add(comp, 'Background', 'BTN_Fill', 0, 0)
    shape = add(comp, 'RectangleMask', 'BTN_Shape', 0, -1)
    label = add(comp, 'TextPlus', 'BTN_Label', 1, -1)
    mrg   = add(comp, 'Merge', 'BTN_Merge', 1, 0)
    for k, v in {'Width': 0.125, 'Height': 0.0556, 'CornerRadius': 1.0}.items():
        shape.SetInput(k, v)
    shape.SetInput('Center', {1: 0.5, 2: 0.3519})   # GetInput returns {1:x,2:y,3:0} (verified); dict write: read back
    for k, v in {'TopLeftRed': 0.16, 'TopLeftGreen': 0.47, 'TopLeftBlue': 1.0}.items():
        fill.SetInput(k, v)
    label.SetInput('StyledText', 'Continue'); label.SetInput('Size', 0.0195)
    label.SetInput('Center', {1: 0.5, 2: 0.3519})
    ok = [fill.ConnectInput('EffectMask', shape),
          mrg.ConnectInput('Background', fill),
          mrg.ConnectInput('Foreground', label)]
finally:
    comp.Unlock()
assert all(ok), ok                      # ConnectInput returns True/False: check, then read back wiring
```

Equivalent `.setting` paste (Route A in 10) avoids the auto-connect trap entirely and is the preferred way to create a multi-node unit:

```lua
-- status: unverified (not yet rendered); structure mirrors the live-verified lab_title.setting
{ Tools = ordered() {
  BTN_Shape = RectangleMask { Inputs = { Center = Input { Value = { 0.5, 0.3519 }, },
      Width = Input { Value = 0.125, }, Height = Input { Value = 0.0556, }, CornerRadius = Input { Value = 1, }, },
    ViewInfo = OperatorInfo { Pos = { 0, -50 } }, },
  BTN_Fill = Background { Inputs = { TopLeftRed = Input { Value = 0.16, }, TopLeftGreen = Input { Value = 0.47, },
      TopLeftBlue = Input { Value = 1, }, EffectMask = Input { SourceOp = "BTN_Shape", Source = "Mask", }, },
    ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  BTN_Label = TextPlus { Inputs = { StyledText = Input { Value = "Continue", }, Size = Input { Value = 0.0195, },
      Center = Input { Value = { 0.5, 0.3519 }, }, }, ViewInfo = OperatorInfo { Pos = { 110, -50 } }, },
  BTN_Merge = Merge { Inputs = { Background = Input { SourceOp = "BTN_Fill", Source = "Output", },
      Foreground = Input { SourceOp = "BTN_Label", Source = "Output", }, }, ViewInfo = OperatorInfo { Pos = { 110, 0 } }, },
} }
```

## Don'ts and failure lessons

- Do not use per-frame auto-tracing, palette segmentation or disconnected contour replacement as the reconstruction. Computer vision (Tracker, Probe, external measurement) may measure timing, colors, bounds and motion; it drives a stable rig, it does not regenerate topology each frame.
- A reference `MediaIn`/`Loader` may be a guide under a Dissolve or in viewer B for split-wipe comparison. It is never hidden inside the output as the "reconstruction".
- Do not approximate continuous shading with stacked bands or tiny polygons. Blur is not a fix for fragmented construction; never soften the whole comp to hide a local defect.
- A Merge whose Background is a small graphic crops the whole result to that graphic (Merge BG sets resolution). Put the full-frame plate on Background.
- Merge expects premultiplied foregrounds: bright fringe = straight alpha, dark halo = double premultiply. Fix at the source, not with Erode.
- Keep each independently meaningful part selectable. A single `sPolygon` holding body, trim and clasp cannot animate the lid.
