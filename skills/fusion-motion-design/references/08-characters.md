# 08 Character families, blink, gaze and parallax

Load for mascot or agent silhouettes, a family of characters, blink and gaze rigs, smooth head turns, or subtle flat-character parallax. Built with sShapes (vector, one raster per agent at `sRender`) and one controller per agent. Timing at 24 fps (the accepted AE example was 30 fps; converted values noted).

This module is the simple avatar/face rig. For drawn or illustrated characters end to end, start at
[characters/overview](characters/overview.md); to build or repair a 2D limb/face rig, start at
[rigging/overview](rigging/overview.md); for measured performance, reference playback and lighting
passes, add [11 Character production](11-character-production.md); for glyph-built characters, add
[12 Symbol characters](12-symbol-characters.md).

## Character families and silhouette quality

When the brief names an existing avatar or mascot system, study its actual base shapes and hero examples first and only then design variants; start from the product's own vector artwork if it exists. A large cast rarely needs one unrelated shape per character: vary proportion, orientation, color and eyes inside the family you observed, and add new base geometry only where the design calls for it. If the user says the outlines repeat, a recolored, stretched or rotated copy of one base is no fix; draw genuinely different outlines with the same curve quality and compare them side by side before any animation.

Review every body shape with the eyes hidden, once at its real on-screen size and once zoomed in, hunting for sharp kinks, flattened stretches, pinched dips, lopsided corners and paths that cross themselves. Points scattered around a radius, or handles left on automatic, can make a technically valid path read as broken. Asymmetry and lobes that belong to the design stay, with tangents that flow on purpose. When the source SVG is densely sampled, rebuild it as a handful of meaningful Bezier segments and check the outline by eye against the original; a simple body should never carry hundreds of sample points.

Fusion geometry choices per silhouette:

| Shape | Build |
|---|---|
| circle, oval, egg (near) | `sEllipse` (`Width`/`Height`), egg via `sPolygon` 4 points |
| squircle, pill, rounded rectangle | `sRectangle` + `CornerRadius` |
| hexagon, pentagon, rounded triangle | `sNGon` + `sExpand` (`Border Style` Round) to soften corners |
| diamond, wedge, drop, bean, leaf, heart, fan, dome, cloud, n-lobe, soft cross | `sPolygon` with 4-10 Bezier points on real extrema; lobes via `sMerge` of `sEllipse`s unioned (`sBoolean` Union) when that is cleaner |

Polyline `.setting` points are relative to the tool's center (about -0.5..0.5) and each point's `LX/LY/RX/RY` handles are relative to that point (installed-template syntax: `{ X = -0.27, Y = -0.17, LX = ..., LY = ..., RX = 0.089, RY = 0.089 }`).

When correcting a silhouette, preserve approved gaze, blink timing, control overrides and group identity. Reposition the face optically only where the new body's center or interior changes; then check open eyes, a closed blink and extreme gaze inside the new body. Containment is a technical check, not evidence the silhouette looks good.

## Compact editable agent rig

One group per agent, transparent output:

```
AGENT07 (Group)
  CTRL07 Custom (UserControls: LookX, LookY, Blink, Tilt, Parallax, TurnLag, AutoAmount, Phase, BodyRed/Green/Blue,
                 EyeRed/Green/Blue, BodyScaleX, BodyScaleY, EyeW, EyeH, EyeSpacing, EyeTravel, BodyTravel)
  BODY07 sPolygon/sEllipse/sRectangle (few points)       -> BODY07_XF sTransform (parallax, foreshortening)
  EYE07_L sRectangle (CornerRadius 1) --\
  EYE07_R sRectangle (CornerRadius 1) ---> EYES07 sMerge -> FACE07_XF sTransform (gaze, eye travel)
  BODY07_XF -> HEAD07 sMerge.Input1 ; FACE07_XF -> HEAD07 sMerge.Input2 -> HEAD07_XF sTransform (Tilt) -> AGENT07_R sRender
LIB (one shared motion library tool, outside or packaged with the family): keyed looping curves GazeX, GazeY, BlinkCurve
```

Keep only the vertices the outline actually needs. Finish the full set of shapes before any motion; a recolored cloud is still the same cloud. With a large cast, line the shapes up at their final grid size and view them in grey (a review branch with `ColorCorrector` saturation at 0). Aim for similar visual weight, breathing room and face position across the grid, not identical outlines. One approved set ranged from circles, squircles and diamonds through clouds, drops, eggs, beans and pills to hearts, leaves, fans and lobed flowers; that shows the kind of controlled range to aim for, it is not a required list or anyone's brand artwork.

## Blink and gaze

Publish these controls: Look X and Look Y (-1 to 1), Blink (0 = open, 1 = closed), Tilt in degrees, body and eye colors, body proportions, eye size and eye spacing, and a Speed or motion-amount control when it helps. Idle motion samples shared curves, offset by a phase per character; hand animation keys the CTRL controls instead. Decide whether a hand-keyed gaze is added on top of the idle gaze or overrides it, say so in the control label, and clamp the combined value to the supported range:

```
LookXFinal (CTRL07 user control) = math.max(-1, math.min(1, LookX + AutoAmount*LIB:GetValue("GazeX", time + Phase)))
```
(additive mode; `LookYFinal` likewise from `LookY` and `GazeY`; for replace mode use `iif(AutoAmount > 0, <auto>, LookX)`). Computing the final look once on CTRL keeps every body and eye expression cheap and consistent.

Blink by reducing capsule-eye height about its center. Fusion advantage: `sRectangle` `CornerRadius` is normalized to the shorter side (1.0 = pill, live-verified on RectangleMask; sRectangle CornerRadius 0.2 on a 1920x960 px rect measured ~96 px, the same rule), so the eye stays a capsule at every height without recomputing roundness. Keep a small closed height, never 0:

```
EYE07_L.Height = CTRL07.EyeH * (1 - math.max(CTRL07.Blink, CTRL07.AutoAmount*LIB:GetValue("BlinkCurve", time + CTRL07.Phase)) * 0.88)
EYE07_L.Width  = CTRL07.EyeW
EYE07_L.Translate.X = -CTRL07.EyeSpacing/2 * (1 - math.abs(CTRL07.LookXFinal)*0.12*CTRL07.Parallax)
```
Do not squash eyes with `sTransform` `YSize` (that squashes the rounded ends into ellipses, the Fusion version of AE's "square eyes" failure). Inspect the actual closed frame and intermediate frames.

Blink curve starting point (taste, 24 fps): close over 2-3 frames, hold 1 frame at 0.12 height, open over 3-4 frames; auto interval 3-5 s with per-agent phase so agents do not blink or stare in sync unless the reference does. Keep optional breathing at 0 unless requested or visible.

Keep the idle motion in one small shared library (`LIB` holding looping `GazeX`, `GazeY` and `BlinkCurve` keys; in a `.setting` file the loop is `Flags = { Loop = true }`) instead of keying every eye separately; it is far easier to edit. Ship the library inside the family package (06) so a single exported character still finds it.

## Subtle head-turn parallax

Drive the face and the body from one look value. The eyes move a little further than the body, the body catches up after a short delay you can adjust, and a touch of foreshortening narrows the body and the gap between the eyes. A plain head turn never morphs the outline: it is a light 2D hint of depth, not a modelled 3D head.

```
FACE07_XF.XOffset  = CTRL07.LookXFinal * CTRL07.EyeTravel
FACE07_XF.YOffset  = CTRL07.LookYFinal * CTRL07.EyeTravel
BODY07_XF.XOffset  = CTRL07.Parallax * CTRL07.BodyTravel * CTRL07:GetValue("LookXFinal", time - CTRL07.TurnLag)
BODY07_XF.XSize    = 1 - CTRL07.Parallax * 0.06 * math.abs(CTRL07:GetValue("LookXFinal", time - CTRL07.TurnLag))
HEAD07_XF.ZRotation = CTRL07.Tilt
```
Expose `Parallax` (0..1, 0 restores the prior non-parallax motion exactly) and `TurnLag` in frames with the unit in its label. Accepted AE starting point: lag 2.4 frames at 30 fps (0.08 s) = about 1.9 frames at 24 fps; amount 70/100 = 0.7. These are starting points, not presets. Scale travel to the character's size and available face interior; narrow eggs and rotated diamonds need smaller gaze travel than circles. `GetValue` at `time - lag` is verified on plain inputs; on an expression-driven input and at fractional frames it is unverified: read back values at two frames before trusting it.

## Recipe A1: one agent from scratch (status: unverified (not yet rendered))

1. Paste the group skeleton as `.setting` (Route A, 10) with CTRL07 UserControls (06 syntax) and the expressions above.
2. BODY07: `sEllipse` `Width` 0.22 `Height` 0.22 (circle; sShape sizes are all relative to frame width, live-measured on sRectangle, so equal values give a circle), colors from `BodyRed/Green/Blue` by expression.
3. Eyes: `EyeW` 0.018, `EyeH` 0.05, `EyeSpacing` 0.06, `EyeTravel` 0.02, `BodyTravel` 0.008.
4. `AGENT07_R` sRender, `UseFrameFormatSettings` on, then a Transform places the agent in the grid.

Verify: open, mid-blink and closed frames at LookX/LookY = (0,0), (1,0), (-1,0), (0,1), (1,1), (-1,-1), with Tilt +-10 and Parallax 1; eyes stay capsules and inside the body; Parallax 0 renders pixel-identical to the pre-parallax baseline (difference Merge or compare PNGs); automatic cycle and manual keys both work.

## Carry-over evidence

When improving only silhouettes or parallax, compare before/after: source colors, group identity, user overrides and existing motion keys. Export the comp (`item.ExportFusionComp(path, i)`) before and after and diff the text for unintended changes (Python `SaveSettings` returns empty through the bridge). Preserve numbering and controls unless a change is required. Test a real manual edit through the published Edit-page control and directly on CTRL, and explain which value wins (06).

## Don'ts and failure lessons

- Do not add an independent idle oscillation to fake parallax.
- Do not scale eyes to blink; change `Height` with `CornerRadius` 1.
- Do not let gaze clip at the advertised extremes; clipping checks alone do not prove pleasant eye placement.
- Do not replace approved gaze/blink timing when only the body changes.
- Do not claim silhouette variety from recolors or rotations of one base.
