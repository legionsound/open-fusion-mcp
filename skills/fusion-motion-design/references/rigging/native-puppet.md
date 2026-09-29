# Rigging: soft-part deformation (Fusion has no Puppet)

AE's Puppet pins (`ADBE FreePin3`) have no Fusion equivalent: no pin tool, no ARAP mesh. Read this for
soft parts (hair locks, tails, sleeves, ribbons, cheeks, bellies) after separation, hidden
reconstruction and overlap tests are done. Recipes are **status: unverified (not yet rendered)**.

## Choose the deformer

| Need | Fusion deformer | Notes |
|---|---|---|
| Sway or wave that grows from a pinned root to a free tip (hair lock, tail, ribbon) | **Gradient-weighted `Displace`**: the part -> `Displace` (`Type` 1 X Y, `XRefraction`/`YRefraction`) whose `Foreground` map is a `Background` gradient (0 at root, 1 at tip) multiplied (`ChannelBoolean` or Merge "Multiply") by an animated value | Root weight 0 pins the root exactly; amplitude grows along the gradient; animate the multiplier with the braid wave (characters/character-performance). Displace needs both inputs: the part into **`Input`** (its `Background` input is ignored), the map into `Foreground`. [verified live 2026-09-26] `Background` `Type` "Gradient" Linear from root (0.3, 0.5) to tip (0.6, 0.5), `YRefraction` 0.05, both channels Red: the root column moved 1 px, the tip 190 px, linearly in between (map value 0 = no displacement) |
| Bend along an arc (tail curl, bending limb, drooping ear) | **`KD_Bend`** (`Start`, `Midpoint`, `End`, `StartAngle`, `EndAngle`, `Radius`, `Warp`) | Krokodove, installed with Resolve. [calibrated live 2026-09-26] Image input `Image`; `SourceStart`/`SourceEnd` mark the straight source span, `Start`/`Midpoint`/`End` (normalized points) define the arc it is bent onto: a bar from 0.3 to 0.6 with `Midpoint` (0.45, 0.62) bent into a clean arc; with collinear points, `StartAngle` 150 / `EndAngle` 30 (or `EndAngle` 90) left it straight. Bend by moving `Midpoint` |
| Free-form reshape at a few handles (cheek puff, belly squash) | **`GridWarp`**: set `SrcXGridSize`/`SrcYGridSize` first (changing them later resets all edits), `CopySrcToDest`, then enable "Mesh Animation" and key destination points | A Polychange spline: moving one point keys all points. `DstCenter` can follow a tracker. [verified live 2026-09-26] Scripted route: `.setting` text. The meshes are inputs `SrcGridChange`/`DstGridChange` with `Value = Mesh { Count = 9, Col = 3, DeltaR = 0.5, DeltaC = 0.5, P1X = -0.5, P1Y = -0.5, Points = { { X = -0.5, Y = -0.5 }, ... } }` (read the exact form with `setting.copy`); a pasted `DstGridChange` with the center point moved warps the image, and a `BezierSpline` whose keys carry `Value = Mesh {...}` (0 at frame 0, 1 at frame 10) animates the warp (half-way at frame 5) (`t_rig_gw_static.png`, `t_rig_gw_anim.png`) |
| Vector part that changes silhouette | **Polyline shape keys** (`PolylineMask`/`sPolygon`) with vertex correspondence | Cleanest for drawn-vector characters; every key same point count and order |
| Twist, taper or bend of a card in depth | **`Bender3D`** (`Bender` Bend/Taper/Twist/Shear, `Amount`, `Axis`, `Angle`, `Center`, `RangeMin/Max`) on an `ImagePlane3D` with raised `SurfacePlaneInputs.SubdivisionWidth/Height` | Bender3D adds no vertices: subdivide first. Page-curl style bends (transition-kit). [verified live 2026-09-26] Bend `Amount` 0.6: subdivisions 1 rendered a flat card, 60 a curved one (`t_rig_bender_sub1.png`, `t_rig_bender_sub60.png`) |
| Pin-like point warp from the UI | Resolve FX **Warper** OFX (`ofx.com.blackmagicdesign.resolvefx.Warper`) | Point-and-constraint warp closest to pins; per-point scripting unverified; OFX dependency (15) |

Place a small set of meaningful controls at roots, bend regions and moving tips; their count follows the
part's geometry. Apply each deformer to its own prepared part, never to the flattened character with
hair, face and decorations glued together.

## Proof before binding controls

1. Hold the part's Transform fixed. Render rest.
2. Change one deformer control (one GridWarp point, the Displace multiplier, the KD_Bend end angle).
   Render again and confirm the intended region deformed while the root stayed put; restore.
3. Only then bind the deformer to controller inputs. Keep roots stable; flexible tips get restrained,
   delayed motion (`time - k` reads).
4. Retest in-between poses: a deformed edge can expose pixels that rigid overlap tests never showed
   (Displace samples outside the part's alpha: extend the hidden surface or set the part's DoD margin).

## Recovery and honesty

- Export the comp after each verified group of deformer edits. If Resolve crashes, reopen the latest
  checkpoint and isolate the failing operation on one part; never repeat a batch that produced the same
  crash.
- If a deformer cannot be made to work safely, keep the prepared parts and report exactly which soft
  deformation is unfinished. An alternative method is fine when the user accepts it, but it is not "pins",
  and a transform labelled as deformation is not a deformer.
- Recheck or rebuild deformers whenever the underlying alpha changes (GridWarp grids and polylines do not
  follow a repainted part).
