# Collage: motion and depth

Timing at 24 fps. Values are tuning ranges from the Higgsfield source, not required timings. Recipes
are **status: unverified (not yet rendered)**.

## Timing and dynamic openings

- Open on a clear visual event: a dominant subject assembling, a cluster entering from several
  directions, or a close camera revealing a coherent scene. Show a recognizable subject early; no
  empty background or slow move with nothing to discover unless the reference does exactly that.
- Staggered arrivals with different travel distances, converging on one event. Fast paper assembly:
  0.25-0.6 s (6-14 f) per principal entrance, stagger 0.04-0.15 s (1-4 f); a 3-6 % positional
  overshoot of the travel only when it reinforces the material, then a short settle. Tune in playback.
- Start the camera reveal while the assembly is still finishing, without every object and the camera
  reversing together. One strong pullback reveals more depth than repeated zoom punches. Keep margin
  for the moving subject before it reaches rest, not only after.
- Short letter-by-letter headline: fast Text+ Write On, then hold the full word through the action.
  Longer text keeps reading time, and the reveal never changes the final layout. Discrete character
  changes may step (`StepIn`); camera travel and color interpolation normally should not.
- Plan action, readable hold, transition. "More energy": trim needless anticipation and settle,
  overlap compatible actions, give transitions a stronger direction. Never speed all text and footage
  uniformly or put the same bounce everywhere. The camera may keep travelling through a hold if the
  subject stays legible.
- In holds separate camera drift, local secondary motion and material boil. Loose paper gets a
  restrained tilt or flutter about a plausible attachment point (`Pivot` at the tape or pin), with
  attached captions and clips inside its group. Independent deterministic phases and bounded
  amplitudes (sums of sines with per-card phase controls), never one shared random shake; keep one
  stable focal element.
- Duration is independent from movement speed. Keep the timeline for a local energy pass unless
  shortening is asked. When duration changes, update together: nested Fusion clips, camera coverage,
  textures, prompt lifetimes, footage handles, markers, render range and absolute-time expressions
  (`time > 240`, `comp.RenderEnd`). Snap hard cuts to the master frame grid.
- Time-bounded refinement: neutral outside the interval. Preserve the boundary pose **and velocity**:
  added motion returns to zero offset and zero added slope at both ends (an added term shaped by
  `sin^2` over the interval does this), later expressions and handles stay intact; compare checkpoints
  across the supposedly unchanged interval (09).

## Camera and depth construction

- One understandable `Camera3D` with an explicit controller for deliberate travel. Choose the aiming
  model: fixed orientation (`Transform3DOp.Rotate.*`) or point of interest
  (`Transform3DOp.UseTarget` 1 with `Target.X/Y/Z`); never both by accident. Inspect camera
  translation, any parent `Transform3D`/`Merge3D` transform, `FLength`/`AoV`, and target before
  changing the rig (and write `ApertureW`/`ApertureH` on pasted cameras: `FilmGate` alone is not enough, realities
  §11.17 [from rebuild log, K2]).
- Compose the arrival frame first, then derive the starting close-up or off-screen arrangement. Keep
  `FLength` fixed when a physical move gives the result: zoom and a Z dolly have different depth
  behavior. A small roll rotates the camera about its own axis (`Rotate.Z` on the camera), not a
  distant controller, which orbits.
- Stage background, rear paper, photographic object and foreground details on distinct Z planes.
  Keep tightly attached paper components (border, print, label) shallow and in one `Merge3D` so they
  never peel apart during a pan. Judge foreground from world space relative to the camera, not from
  the sign of Z.
- Moving a card in Z changes its projected size and position. Compensate with the real projection:
  frustum-fit size at distance d is `2*d*tan(AoV/2)` tall (realities §2); for rotated or off-center
  cards place `Locator3D`s on the visible corners and read their 2D screen `Position`. A card's image
  canvas includes transparent padding and overstates visible bounds.
- Shape velocity, not only positions: sparse poses, intentional rests, nonzero transit slopes through
  waypoints that should flow (02 match-cut handoff slopes). Flat handles at every waypoint make
  stop-start travel. `XYPath`/separate `Translate.X/Y/Z` splines allow signed per-axis speed design;
  keep segments monotonic unless a reversal is intended; check spatial arcs and loops.
- The camera stays subordinate to the focal object. Depth of field after blocking (OpenGL renderer
  accumulation DOF, or `DepthBlur` from the Z channel), focused on the intended plane; never blur key
  text to fake depth. Oversize every background and texture plate for the widest view, roll, jitter
  and blur margins.
- Motion blur does not fix intersecting planes. For wrong overlaps inspect Z values, parent
  transforms, mattes, duplicate cards, opaque source backgrounds, and 2D tools spliced into the 3D
  branch; check in-betweens and both endpoints before adding blur.

## Photographic assembly and object replacement

- Assembling a photographed object from pieces: split one source into meaningful regions with
  complementary masks (the same `PolylineMask` used normally for one piece and with `Invert` 1 for the
  other, or `PaintMode` Subtract). Pieces that must join share resting transform, `Pivot`, size and Z.
  Animate the major mass first, then a recognizable upper or foreground detail shortly after.
- A small mask `SoftEdge` keeps the edge looking photographic; check each join at full resolution for a
  gap or a see-through double seam. No separate shadows between adjoining pieces; one shadow for the assembled
  silhouette. A late piece must not intersect an unrelated foreground plate.
- Replacement: keep a clear relation between outgoing and incoming object. Refit `Pivot` and size to
  the new artwork's real dimensions, align the meaningful ground or resting point, stage the travel so
  the objects do not cover the interface, and keep old and new backgrounds covered throughout.
- Reusing keyed footage: keep a working key chain and test it on a scratch copy first. The AE source
  needed Keylight + Key Cleaner + Advanced Spill together; the Fusion equivalent is `DeltaKeyer` (or
  `UltraKeyer`) with its own clean-plate, matte and spill controls, sometimes plus `MatteControl`
  (keyer inputs: skill `fusion-reference`). Never swap a validated key for a rough color-removal shortcut;
  check spill, edge transparency, source duration, audio state and placement against the interface.

## Cadence and motion blur

- 12 updates/s when requested or supported by the reference; keep the delivery fps. Fusion steps a
  whole branch with one `TimeStretcher` (`SourceTime` = `floor(time/2)*2` at 24 fps,
  `InterpolateBetweenFrames` 0) placed where the stepping should start (characters/overview). An
  expression `floor(time/2)*2` inside one input steps only that input: stepping the grain alone does
  not step the camera or the cards.
- At 24 fps, 12 updates/s is an even 2-frame hold. At 25 or 30 fps the holds are uneven (at 30 fps a
  2-3 pattern); review real playback rhythm.
- Decide whether the interface steps too. Clean UI merges above the cadence and grain stage when it
  should stay smooth; put it upstream of the `TimeStretcher` only when it should share the timing.
  Keep the stepper on 2D image data (after the `Renderer3D`), never spliced inside the 3D branch.
- Motion blur on moving Transforms (`MotionBlur` 1, `ShutterAngle` 180, `CenterBias` 0 for a shutter
  centered on the frame, which is AE's 180 deg / -90 deg phase; [verified live 2026-09-26] a square
  moving 38.4 px/frame smeared +/-10 px around its frame position at `CenterBias` 0, only backward
  (trailing) at +1 and only forward at -1) and matching
  `Renderer3D`/`Camera3D` blur settings. Reduce blur when it smears cut-paper edges or defeats the
  stepped look; check posterization plus blur together in playback.
