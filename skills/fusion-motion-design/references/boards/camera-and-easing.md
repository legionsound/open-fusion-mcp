# Boards: camera and easing

Recipes are **status: unverified (not yet rendered)**.

## One wrapper owns the camera

- AE "precompose all layers" = in Fusion, the board's final Merge output feeding one `CAM_Board`
  Transform (header, sidebar, hidden mattes and UI included when "all layers" was asked). No
  re-wiring of the board itself: ordering, Transform chains, keys, expressions are untouched. Reuse an
  existing wrapper on a retry instead of stacking a second one.
- Flat board: animate `CAM_Board.Center` and uniform `Size`. A `Camera3D` only when perspective or
  depth is requested (depth-space).
- Never retime the board (`TimeSpeed`, `TimeStretcher`) to implement a camera move.
- Header and sidebar move with the board when "all layers" was requested; keep them fixed (merged
  after `CAM_Board`) only when the user asks for an overlay or the project already works that way.
- Internal parallax only on request; each note's paper, text and badge stay locked within its group.

**Resolution trap (Fusion-specific).** `CAM_Board` scales a flattened raster: a 2.5x close-up of a
3840-wide board is soft. Build the board canvas at output size x max zoom (the board's Merge
`Background` at e.g. 7680x4320 for a 2x close-up in UHD, generators with explicit `Width`/`Height`),
then let `CAM_Board` scale down, and crop to output with the final Merge over an output-size
Background. [verified live 2026-09-26] A hard edge on a 3840 board zoomed 2x by the Transform
rendered a 2 px 10-90 % ramp; the same edge built on a 7680x4320 canvas (`UseFrameFormatSettings` 0)
at `Size` 1 over a 3840 Background rendered a 0 px ramp, and the Merge showed the canvas center at
native pixels (the crop). Or push the camera upstream (per-element Transforms) or into 3D. Text+ and sShapes are
resolution independent only before the Merge flattens them (realities §13).

## Framing and route

- Pick close-up targets from the request or the board; order them into a readable route with
  deliberate stops. Do not copy another project's labels or coordinates.
- Measure each target's visible bounds after its entrance settles, including rotation, scale, pivot
  offsets, paper folds and badges: render the settled note branch with alpha and take its alpha bbox
  (`scripts/audit_frame.py`), or read `Tool.Output[0].DataWindow` in an expression. A group's canvas
  is not its visible content.
- Uniform zoom from the viewport and target bounds with a margin m, in pixels:
  `S = min(W*(1-m)/w_px, H*(1-m)/h_px)`.
- Keep `CAM_Board.Pivot` fixed at (0.5, 0.5). To bring target center t (normalized, board space) to
  frame center: `Center = (0.5 - S*(t.x - 0.5), 0.5 - S*(t.y - 0.5))`. [verified live 2026-09-26] With
  Pivot (0.5, 0.5), S 2 and t (0.7, 0.3) (Center 0.1, 0.9) the target dot's alpha bbox centered at
  exactly (0.5, 0.5); still check one frame per new setup.
- Stationary close-ups repeat the pose on two keys. Coordinate arrivals and departures with note
  entrances and exits without retiming them.
- A camera loop matches end position and size to the start; compare the last rendered frame with the
  first (seam value and velocity, animation principles §9).

## Temporal and spatial interpolation

- Match a supplied speed graph. For "quick departure, long deceleration" with no other data: zero end
  speeds, out influence 33.333 %, in 77.15 % = cubic-bezier(0.3333, 0, 0.2285, 1). Python handles over
  a D-frame move of size V: first key `RH = {0.3333*D, 0}`, second key `LH = {-0.7715*D, 0}`
  (realities §6).
- Temporal and spatial are separate in Fusion by construction: `XYPath` X and Y splines with the same
  normalized curve travel a straight line; `PolyPath` holds the spatial shape (polyline) and a
  `Displacement` spline for timing. For a straight pan give both XYPath channels identical easing;
  for curved travel draw the PolyPath and inspect intermediate framing.
- "Replace linear with eased" across a comp: visit each BezierSpline once (dedupe by tool), change only
  continuous segments, keep `StepIn` holds, discrete text keys, existing custom handles, key times,
  values and expressions. Read back both handles of every affected key and list unsupported inputs
  (points without XYPath, expression-driven inputs).
- Zero-speed stops only at intentional pauses; keep velocity continuous through flowing cursor paths
  or uninterrupted travel (handoff keys with matching slopes, 02 match cuts step 4).

## Rendering and checks

- Motion blur on `CAM_Board` (`MotionBlur` 1, `ShutterAngle` ~180, `Quality` 4-8 preview, higher
  final) only where travel benefits; stationary close-ups must stay crisp. Check a dense vector grid
  only if it causes a demonstrated render problem, and keep its look.
- Verify wrapper keys, unchanged board playback, target centering, unclipped notes, intermediate
  travel and the ending. Read handles back (`GetKeyFrames`) or sample `GetInput` at fractional frames;
  key times and values alone do not prove easing.
