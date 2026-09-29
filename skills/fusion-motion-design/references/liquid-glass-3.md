<!-- liquid-glass.md part 3 of 3; index: liquid-glass.md -->
## 9. "Doesn't look right" checklist (symptom -> node -> fix)

| Symptom | Cause -> fix |
|---|---|
| Heavy dark outline around the panel | `EdgeDarken.Gain` far below 0.92, or `EdgeDarkHole.BorderWidth` positive (hole bigger than outer, darkening the whole inside inverted). Gain 0.92, hole BorderWidth negative. |
| Dark halo just inside the edge | Glass branch blurred after masking (a mask on `GlassFrost` or an alpha cut before the blur). Only `GlassComp.EffectMask` cuts the glass. |
| Bright or dark fringe exactly on the edge | Different geometry on two masks (a typed number instead of the expression). Re-apply C/W/H/R expressions to every mask. |
| No background bending at the rims | `RimRefract.Type` left 0 (Radial) with a normal map; `BezelHeight.XBlurSize` near 0 (1 px band); `NumberIn8` tiny; `Foreground` not connected. |
| Whole interior shifted diagonally | `BezelCenter` (Brightness -0.5) missing, so 0.5-gray reads as displacement (NEEDS-LIVE-VERIFY 1-2). |
| Band pinches content inward | Sign: negate `GlassCtrl.NumberIn8`. |
| Distortion covers the whole frame | `GlassComp.EffectMask` lost its PillMask connection. |
| Interior warps uniformly, no lens feel | `GlassLens.Strength` 0 or `Size` far smaller than the panel (Lens k). |
| Rim shine on one side only | `RimGradient.GradientType` not "Reflect", or Start and End swapped. |
| Rims sit in the wrong place / skewed on 16:9 | End expression missing the aspect factor, or angle entered in degrees into trig (expressions are radians). |
| Rims slide off the edges when scaling | A rim mask missing the `*GlassCtrl.NumberIn3` scale term. |
| Glass reads flat or plastic | Frost, Magnify, Saturation or the CC Glass stage missing; rims too thick (> 10 px UHD). |
| Glass reads milky gray on a light background | `GlassTint.Lift` too high: 0.15-0.25 on light plates; raise `Saturation`. |
| Parts lag behind during a move | An expression got cleared (SetExpression("") sets the input to 0, not the old value): re-set it. |
| Fills cover only the frame center or sit offset | A `Background` (BezelSrc, RimGradient) resolution differs from the background: keep `UseFrameFormatSettings` 1 and the comp format equal to the plate, or set Width/Height explicitly. |
| Stair-stepped bend band | HeightScale too high (saturated normals), bezel blur too small; raise `BezelHeight`, lower HeightScale factor, keep Frost after Displace. |
| Frost darkens where the panel touches the frame edge | Blur samples black outside the frame (NEEDS-LIVE-VERIFY 12). |
| Stray `Merge1`, wires spliced into masks after a Python build | `SetActiveTool(None)` not called before AddTool **[live trap]**. Delete strays, rewire, read back. |
| Grain crawls on a still | `GlassGrain.TimeLockSeed` 1 for stills; 0 for video. |
| Render very slow at UHD | Custom-tool fallback map in use, or `RimBloom` very large; prefer `CreateBumpMap`, disable the CC Glass stage for previews. |

## 10. Look levers (what to change per brief)

| Lever | Control | Subtle / recipe / heavy |
|---|---|---|
| Frost | `GlassFrost.XBlurSize` (any res) | 6 / 12 / 18 |
| Backdrop saturation | `GlassSat.Saturation` | 1.0 (off) / 1.3 / 1.5 |
| Refraction strength | `GlassCtrl.NumberIn8` | 0.03 / 0.06 / 0.09 |
| Bend band depth | `GlassCtrl.NumberIn7` bezel px (UHD) | 20 / 35 / 50 |
| Refraction style | `RimRefract.XRefraction` 0 vs linked | vertical only / all edges |
| Glass thickness | `GlassLens.Strength` + `GlassMagnify.Size` | 0.15 + 1.05 / 0.3 + 1.10 / 0.45 + 1.15 |
| Glass texture (CC Glass) | `BodyRefract.XRefraction`, `LightPower` | 0.003 / 0.006 / 0.012 |
| Rim light | `RimLight.Brightness`, Rim Arc | 0.4 / 0.6 / 0.8; arc 0.010 / 0.0156 / 0.024 |
| Key light direction | Rim Angle (deg) | 130-165; both arcs always move together (keep BOTH: single-rim glass reads as plastic) |
| Rim bloom | `RimBloom.XGlowSize`, `Gain` | off / 8 & 1.0 / 14 & 1.5 |
| Edge whisper | `EdgeDarken.Gain` | 0.96 / 0.92 / 0.88 |
| Tint | `GlassTint.Lift` (or ColorCorrector for color) | 0.2 / 0.4 / 0.6 |
| Shadow | `ShadowDarken.Gain`, Drop, Soft | 0.85 / 0.70 / 0.55 |
| Frost texture | `GlassGrain.MasterStrength` | 0 / 0.03 / 0.06 |
| Dark UI | on light plates: EdgeDarken toward 0.96, Tint 0.2; on dark plates: Tint 0.45-0.55 | |

## 11. Finish the build: package, reconnect, verify (mandatory)

A rig that renders once at its build position is not the deliverable. The component must survive
moving, duplicating, nesting and new content.

1. **Package** as one `GroupOperator` named for the component (section 7). Publish the controller
   and look controls; keep `GlassIn` as `MainInput1`; keep the background OUTSIDE the group (a glass
   group carrying its own background is a picture of glass). For the Edit page: save the group as an
   Effect template into `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Effects/`
   with `MainInput1` = the clip and `MainOutput1` (builtin Effects have no MediaOut), then relaunch
   Resolve. Use Anim Curves (`LUTLookup`, `Source` "Duration") instead of absolute keys if the
   entrance must stretch with clip length.
2. **What packaging can break in Fusion** (the analog of AE index drift and `thisComp`):
   - Expressions reference tool **names**. A second paste of the group renames inner tools
     (`GlassCtrl_1`). Confirm the second instance's expressions point at its own controller, not the
     first one (NEEDS-LIVE-VERIFY 15). Never rename `GlassCtrl`/`GlassLook` after building.
   - Published inputs that also carry expressions (e.g. publishing `PillMask.Width` directly) are
     overridden by the expression: publish the controller NumberIns, not the expression-driven inputs.
   - Wires survive grouping; no reconnection of map/source references is needed (unlike AE's
     index-based Bump Map and Displacement Map layer params).
3. **Connect a new background** by re-wiring `MainInput1` (or `GlassIn.Input`). Nothing else. If you
   need to rebuild to change what is behind the glass, the packaging is wrong.
4. **Verify on the actual comp, after each change**, by rendering PNGs (6.3) and looking:
   - one frame over the NEW background: the band bends that background;
   - one frame with `GlassCtrl` moved and scaled: rims, lens, magnify and shadow travel together,
     nothing clips at the pill edge;
   - one frame after a real content edit (alpha mode: longer word or new icon): bezel and rims
     follow the new shape;
   - the mid-move frame (12 @ 24 fps): in-betweens, not only hero poses.
   A True from `Render` or `ConnectInput` is not evidence.
5. **Stress the look** (local Higgsfield connector revision, 2026-09-26): render over a bright
   plate, a dark plate and a detailed high-frequency plate, in motion, and at the smallest size the
   brief uses; inspect edge crops at 1:1 as well as the full frame. Glass is a coordinated response
   to the background (slight bend, edge light, transmission, restrained tint, contact shadow); a
   translucent white panel alone does not read as refraction.
6. **Numbers are per resolution and per background.** AE's blur 40 / scale 110 %, and the second
   light sweep at +118 deg, are recipe examples. Calibrate `GlassFrost` size and the expansion
   margin to the comp width and the background's detail (blur sizes scale with width, realities §2),
   and pair opposing rim directions rather than adding an even white wash.
7. **Helpers never render.** Fusion's hole/choker helpers are masks, which cannot leak into the
   output the way AE helper layers can; still confirm the hole mask cuts the intended region
   (`PaintMode` "Subtract") and that color tools with an `EffectMask` touch only the glass.
8. **Report, do not substitute.** If a node the look needs is missing (a Fuse, `CreateBumpMap`,
   an OFX), say so and name the fallback; never swap in an unrelated look silently.

## 12. Don'ts and failure lessons

- Don't mask the glass branch before the frost blur, and don't put the pill on more than one
  EffectMask in that branch. One cut, at `GlassComp`.
- Don't type geometry into any mask. Every mask's Center/Width/Height/CornerRadius is an expression.
- Don't use Merge apply modes (Multiply, Screen, Add) with premultiplied solid pills to fake the AE
  blend-mode layers; use the masked BrightnessContrast equivalents (exact, no edge artifacts).
- Don't treat RectangleMask Height like EllipseMask Height: rectangle Height is h/H, ellipse Height
  is h/W **[live]**.
- Don't use degrees inside SimpleExpression trig, and don't use `noise()` there **[live]**.
- Don't leave `BezelCenter` out: CreateBumpMap output is 0.5-centered.
- Don't use a dark edge color: #EAEAEA (Gain 0.92) is the whole point.
- Don't drop one of the rims; don't make rims thicker than ~10 px UHD.
- Don't animate masks or effect inputs directly: animate `GlassCtrl` (and `GlassFade.Blend`).
- Don't build via AddTool on the Fusion-page comp without `SetActiveTool(None)` first.
- Don't trust `XBlurSize` as pixels; calibrate Frost by render.
- Don't use MtlReflect 3D refraction for UI glass; it refracts an env map, not the scene.

## 13. NEEDS-LIVE-VERIFY (test plan for the next pass)

1. `Displace` Type 1 neutral value: with `Foreground` = constant 0 image, nothing moves; with 0.5,
   everything shifts (confirms the -0.5 recenter).
   **Live 2026-09-26 (visual):** with Frost 0 and Lens 0 the interior shows only the x1.1 magnify about
   the panel center plus bending near the rims, no uniform diagonal shift, so the -0.5 recenter works.
   Neutral value not probed numerically.
2. `CreateBumpMap` encoding: probe `BezelNormal` on a flat area (expect ~0.5, 0.5, ~1) and at the
   top edge (G above 0.5 on the outward side); confirm float output keeps negatives after
   `BezelCenter`.
3. `Displace` XRefraction/YRefraction units: measure px offset of a BG line vs value (target 110 px
   UHD at recipe strength), and the sign convention.
4. `CreateBumpMap` derivative per pixel (HeightScale = 0.85 x bezel px keeps profile constant
   across HD/UHD).
5. `XBlurSize` / `XGlowSize` calibration vs AE Blurriness 40 / 30 / 15 at UHD and HD.
   **Live 2026-09-26:** Blur size scales with frame width (size 10: FWHM 30 px at 1920, 58 px at 3840;
   sigma about 1.25 x size x W/1920). Frost 40 erased 226 px letters; 10-12 leaves soft readable shapes.
   Default now 12 at every resolution. `XGlowSize` not measured.
6. RectangleMask `SoftEdge` and `BorderWidth` units (fraction of width?) and whether SoftEdge is
   centered on the edge; `BorderWidth` sign on a solid mask.
7. Mask chain math: `Subtract` clamps at 0; `Multiply` then `Subtract` ordering in
   RimArc -> RimOuter -> RimHole gives ring x arc.
8. `BitmapMask` `Invert` on the first mask in a chain, `Channel` "Luminance" on a gradient,
   default `FitInput` "Crop" with same-size image.
9. `Background` Gradient default colors (black -> white) when created by AddTool, and
   `GradientType` "Reflect" mirroring about `Start`.
10. `Dent` Size units and Strength vs CC Lens Convergence 80; `Type` 0 = Dent 1; compare
    `KD_Spherize` (`Center`, `Size`, `DeformX/Y`).
11. Merge `EffectMask` compositing FG only inside the mask with correct antialiased edge.
12. Frost near frame edges (navbar flush to the top): does `GlassFrost` darken; do `ClippingMode`
    "Domain"/"None" or `GlassMagnify.Edges` 2 (Duplicate) fix it.
13. `ColorCorrector` per-channel Gain/Brightness order for colored tint.
14. `FilmGrain` `LogProcessing` 0 vs 1 on a display-referred comp.
15. Group paste twice: inner tool renames and whether expressions re-target (`GlassCtrl_1`).
    **Live 2026-09-26: PASS.** Every inner tool got `_1` (`LiquidGlass_1`, `GlassCtrl_1`, `PillMask_1`...),
    `PillMask_1.Width` expression became `GlassCtrl_1.NumberIn4*GlassCtrl_1.NumberIn3` and followed
    `GlassCtrl_1` only; the first copy was untouched.
16. `comp:GetPrefs("Comp.FrameFormat.Width")` inside a SimpleExpression on a Resolve Fusion-page
    comp (pattern from a builtin).
    **Live 2026-09-26: PASS.** `RimGradient.End` evaluated to (0.50684, 0.52493), matching the W/H-corrected formula.
17. `SoftGlow.GlowMask` pre-mask with a chained mask; bloom spills past the rim.
18. `.setting` paste of the full group: InstanceInputs appear with names/ranges; `PipeRouter` with an
    empty `Input` accepts `MainInput1`; Custom `NameforNumber*` labels show.
    **Live 2026-09-26: PASS** for the first two: the group exposes `MainInput1`, `CenterX` ... `Opacity`
    and `MainOutput1`; connecting `MainInput1` wired `GlassIn.Input` to the backdrop. Labels not inspected (UI).
19. Auto-fit expressions (R11) `Label.Output[0].DataWindow[...]` on Resolve 21.1.
20. `Shadow` tool alternative: `OutputMode` 1 = shadow only, `ShadowOffset` neutral point.
    **Live 2026-09-26:** `OutputMode` options Image with Shadow, Shadow Only; `ShadowOffset` {0.5,0.5} = no
    offset, x in width units, y in height units (measured). Dent `Type` options Dent 1, Kaleidascope, Dent 2,
    Dent 3, Cosine Dent, Sine Dent (5 = Sine Dent confirmed by render); Displace channels Red, Green, Blue,
    Alpha, Luma.
21. Edit-page Effect template: group with only `MainInput1`/`MainOutput1` loads after relaunch and
    the published controls appear in the Edit inspector.

## 14. IDs used (all TSV-checked unless noted)

Tools: `Custom`, `PipeRouter` (registry; `Input` port from builtin files), `RectangleMask`,
`BitmapMask`, `Background`, `BrightnessContrast`, `Transform`, `Dent`, `Blur`, `CreateBumpMap`,
`Displace`, `FilmGrain`, `Merge`, `SoftGlow`, `ColorCorrector`, `Saver`, `GroupOperator`
(registry); alternatives `KD_Spherize`, `Shadow`, `SphereMap`, `MtlReflect`, `ImagePlane3D`,
`Shape3D`, `Camera3D`, `Merge3D`, `Renderer3D`.
Inputs: RectangleMask `Center Width Height CornerRadius SoftEdge BorderWidth PaintMode EffectMask`
(Width/Height live-measured; present in the rebuilt TSV); BitmapMask `Image Channel Invert PaintMode
FitInput`; Background `Type GradientType Start End Gradient TopLeftRed/Green/Blue/Alpha
UseFrameFormatSettings EffectMask`; BrightnessContrast `Gain Lift Brightness Saturation Input
EffectMask`; Transform `Center Pivot Size Edges`; Dent `Type Center Size Strength`; Blur `XBlurSize
Filter LockXY ClippingMode`; CreateBumpMap `SourceChannel HeightScale FilterSize WrapMode`; Displace
`Type XChannel YChannel XRefraction YRefraction XOffset YOffset RefractionStrength LightPower
LightAngle Spread Foreground`; FilmGrain `MasterStrength MasterXSize Monochrome LogProcessing
TimeLockSeed`; Merge `Background Foreground EffectMask Blend ApplyMode Operator Gain`; SoftGlow
`Threshold Gain XGlowSize GlowMask`; Custom `NumberIn1-8 NameforNumber1-8 ShowPoint1-4 Image1 Setup1-2
RedExpression GreenExpression BlueExpression AlphaExpression`; ColorCorrector `MasterRedGain
MasterRedBrightness` (and Green/Blue); MtlReflect `Reflection.Color.Material
Refraction.RefractiveIndex.RGB BackgroundMaterial`.
Unverified expression features: `comp:GetPrefs(...)` in SimpleExpressions (builtin pattern),
`Tool.Output[0].DataWindow[...]` (builtin pattern), Custom Tool `getr1d()` (manual).
