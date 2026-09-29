<!-- nodes-masks-keyers-misc-opticalflow-paint.md part 3 of 3; index: nodes-masks-keyers-misc-opticalflow-paint.md -->
## Recipes / workflows

1. **Basic Delta Keyer key**: screen footage -> orange input. Key tab: Background Color eyedropper on
   the screen color. Pre Matte tab (View Mode=Pre Matte): box-select uneven-lighting regions, Soft
   Range/Erode to even the screen. Matte tab (viewer=alpha): tune Threshold/Erode-Dilate/Blur. Fringe
   tab: Spill Method (Medium=green, Well Done=blue) + Spill Suppression. Add Polygon/B-Spline
   garbage/solid mattes as needed -> Merge foreground. For a hard/soft split, key twice: one Delta Keyer
   tuned for a hard inner matte, a second for soft edges, feeding keyer #1's output into keyer #2's
   **Solid Matte** input; keep CC/spill-suppression in a separate branch from matte generation.
2. **Clean Plate -> Delta Keyer**: branch screen footage to a Clean Plate node and a Delta Keyer. On
   Clean Plate: box-select screen regions, Erode non-screen noise, Grow Edges to fill holes solid.
   Connect its output to the Delta Keyer's magenta **Clean Plate** input.
3. **Primatte 4-step key** (p.1324): Select Background Color -> Clean Background Noise (View
   Mode=Black, alpha view) -> Clean Foreground Noise (same view) -> Remove Spill (View
   Mode=Composite, RGB view; Spill Sponge then Fine Tuning sliders).
4. **Premultiplied-alpha CC**: Alpha Divide -> color correction -> Alpha Multiply (or, for one CC node,
   its own **Pre-Divide/Post-Multiply** checkbox instead of two extra nodes).
5. **Duration-adaptive title template**: build animated text/graphics, add **Keyframe Stretcher** just
   before Media Out/Saver. Source Start/End = animation's original range; Stretch Start/End protects
   fixed-speed in/out beats while stretching only the middle when comp duration changes.
6. **Custom Tool centered rotation** (copy-ready): Setup `s1=cos(n1)`, `s2=sin(n1)`; Intermediate
   `i1=(x-.5)*s1-(y-.5)*s2+.5`, `i2=(x-.5)*s2+(y-.5)*s1+.5`; Channel R/G/B/A =
   `getr1b(i1,i2)`/`getg1b(i1,i2)`/`getb1b(i1,i2)`/`geta1b(i1,i2)`; drive angle via `n1`.
7. **Optical-flow slow motion**: Optical Flow on the source (trim Loader/MediaIn to the needed range
   first) -> Time Speed/Stretcher w/ Interpolate Mode=Flow -> pick Depth Ordering to match camera-vs-
   subject motion -> enable Clamp Edges + small Edge Softness only if you see edge gaps. If flow is slow
   to iterate on, render once to OpenEXR via a Saver and reload as the new source.
8. **Bulk per-frame roto cleanup**: Multistroke/Clone Multistroke with Duration=1 frame (or 0.5 for
   single-field work), not the fully-editable Stroke type, which slows down at scale.

## Scripting and automation hooks

- **Node abbreviations**: Mask — `Bmp`, `BSp`, `Elp`, `PNM`, `MPly`, `Ply`, `RNG`, `Rec`, `Tri`, `Wnd`.
  Matte — `ADv`, `AML`, `CKy`, `Cry`, `DMp`, `DFK`, `LKy`, `MagM`, `MAT`, `Pri`, `RLT`, `UKY` (Clean
  Plate has no bracketed code in the manual). Metadata — `Meta`, `SMeta`, `TCMeta`. Miscellaneous —
  `ADoD`, `CD`, `CT`, `FLDs`, `Avg`, `KFS`, `Run`, `DOD`, `SPDw`, `Swi`, `TSpd`, `TST`, `Wire`.
  Optical Flow — `OF`, `REP`, `SM`, `Tw`, `VDn`, `VXf`, `VWp`. Paint has no separate bracketed code
  given in this slice.
- **Custom Tool expression language**: full variable/function/operator tables + worked rotation and 3x3
  box-blur examples above — the primary scripting surface for per-pixel procedural motion design.
- **Run Command wildcards**: `%a` (Number A), `%b` (Number B), `%t` (frame, unpadded), `%s` (text
  field); `%0x` zero-pads to x digits, `%x` space-pads. Frame/Start/End Command fields accept any
  executable, batch/shell script, FusionScript, VBScript, JScript, CGI, or Perl file.
- **Set Timecode [TCMeta] is itself a Fuse** (Lua) — its FPS button list is user-editable source, given
  verbatim in the manual:
  ```lua
  MBTNC_StretchToFit = true,
  { MBTNC_AddButton = "24" },
  { MBTNC_AddButton = "25" },
  { MBTNC_AddButton = "30" },
  { MBTNC_AddButton = "48" },
  { MBTNC_AddButton = "50" },
  { MBTNC_AddButton = "60" },
  })
  ```
  paired with `local rates = { 24, 25, 30, 48, 50, 60 }` — edit both together to add custom frame rates.
  **Print to Console** emits `TimeCode: 00:00:08:15` / `Frames: 207`-style lines for automation/debug logs.
- **Multistroke/Clone Multistroke Duration** must be set *before* painting — cannot change after (unlike
  Stroke/Polyline Stroke, editable anytime in Keyframes Editor).
- **Keystretcher modifier** (single-control stretch vs. Keyframe Stretcher node for a subtree) and
  **Switch modifier** (Switch-style selection on one control via its context menu) are generic modifiers,
  not just dedicated nodes.
- Cross-references this slice defers elsewhere: DaVinci Resolve manual's **Composite Nodes** (Merge
  Additive/Subtractive), **Understanding Image Channels** (Coverage/Background Color, Object/
  Material ID), **Resolve FX Refine** (full Relight detail), **Fusion scripting documentation** (Scripts field).
