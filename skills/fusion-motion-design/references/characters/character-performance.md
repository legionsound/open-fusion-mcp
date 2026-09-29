# Characters: performance

Timing at 24 fps. Recipes are **status: unverified (not yet rendered)**.

## Shared timing and rigs

- For each action set anticipation, travel, contact or arrival, reaction, hold and settle from the
  request or the motion reference. The primary action must read at normal speed; secondary motion
  supports it.
- Shared movement lives on a character or object controller and one group Transform. Facial details
  merge inside the head group (they ride the head Transform); held objects merge inside the contact
  rig (hand group); articulated details sit at their attachment `Pivot`s. Local deformation stays
  independently editable.
- Transforms for coherent travel and orientation; polyline shape keys where the silhouette must bend.
  **Vertex correspondence:** every shape key of a `PolylineMask`/`sPolygon` has the same point count
  and order (Fusion keys the whole polyline; add points before keying, never between poses), so
  in-betweens morph instead of tearing. [verified live 2026-09-26] A 4-point square keyed to a
  4-point diamond (pasted polyline spline, `Value = Polyline {...}` per key) morphed smoothly over 12
  frames; with a 5-point second key there was no morph at all: the mask showed the second key's
  shape from frame 0 (`t_chars_shapekeys.png`). One owner per deformation: a blink or squash lives in the
  shape keys or in a Transform `Size`, never both.
- Intentional keys and curves for actions; controlled phase offsets for repeated secondary motion
  (`time - k` reads of one controller curve). Keep fitted curves and the user's adjustments in local
  revisions. No motion just because a tool can move.
- One cadence for all linked parts, including masks and reflections (overview: one `TimeStretcher`).
  **Wing aliasing at a stepped cadence:** a flap of frequency f sampled at r updates/s shows at
  `|f - k*r|` for the nearest integer k. At r = 12, a 12 Hz flap looks frozen and 11 Hz looks like a
  slow 1 Hz beat. Either choose f well under r/2 (3-5 Hz reads as flapping at 12 updates/s) or author
  wings as alternating up/down poses per step (a clean 6 Hz flicker). Render the wings at the chosen
  cadence before approving.

## Braided hair and a flying visitor

- An insect entering starts with its full silhouette beyond the frame edge (check frame 0 has no wing
  tip inside). Curved approach (`PolyPath`), banking that follows direction (`Angle` from the path's
  `Heading` output), deceleration, and a readable arrival above the target flower; then a hover with
  restrained position and orientation changes.
- Each visible wing has its own attachment control (`Pivot` at the wing root, merged inside the body
  group). Offset wing phases; vary rotation and foreshortening (`YSize` squash on the wing Transform)
  while staying attached. The body group carries the flight path. [corrected live 2026-09-26]
  Transform `YSize` is ignored while `UseSizeAndAspect` is 1 (the default): a note with `YSize` 0.5
  stayed 400 px tall; with `UseSizeAndAspect` 0 it rendered 202 px. Set `UseSizeAndAspect` 0 or
  squash with `Aspect`.
- Wind wave from braid root to tip: segment Transforms chained root to tip (each segment merged over
  the next and passed through the parent's Transform), segment k angle
  `A * (k/N)^1.5 * sin(2*pi*f*((time - k*d)/fps))` with delay d frames per segment: displacement
  grows toward the tip and each section lags. Keep the silhouette connected (overlap segment ends).
  [verified live 2026-09-26] Four overlapped segments, each Transform `Pivot` at its root joint,
  A 30, f 1 Hz, d 3 frames: a connected wave travelling root to tip with the largest swing at the
  tip (`t_chars_braid.png`).
  Fringe, side lock and earrings get smaller, later responses from the same wave.
- Head and torso react to the visitor's arrival; gaze moves inside the eye boundary (pupil merged
  with the eye-white matte as `EffectMask`); blinks through the eyelid contour or one equivalent rig.
- Gripping hand and flower move together (flower inside the hand group); stem bends and petals
  respond after the main motion; fingers stay in contact.
- Verify: off-screen start, arrival, every wing attachment, braid continuity, blink closure, reflection
  containment.

## Seated group interaction

- Handling a flower or petal: forearm, wrist, fingers and object move together until release; the
  petal gets its own motion only after contact ends (switch its parent at the release frame by
  stepping `Blend` between an in-hand copy and a free copy that starts at the same screen pose).
- Stagger companion responses around the main gesture. A reading bird: gaze, head, neck and book move
  as one rig. A companion lifting a cup keeps both grips through lift, pause and lowering.
- Keep tabletop layout and occlusion (Merge order) while characters react; check prop contact and the
  timing between participants.

## Reclining character on a flexible support

- One rig drives the support's spring and the body's response; hand, torso and leg contacts stay
  pinned to the surface (drive contact points from the support's deformation, never slide).
- Continuous deformation through thigh, knee, calf and ankle (shape keys with correspondence, or a
  chain of short segment Transforms with overlapping joints); footwear follows the feet. Keep limb
  overlap and the approved pose at every extreme.
- Ponytail and ribbons follow with delayed waves and settle (braid formula above). When a bird lands
  on a petal, align the landing frame with the local petal dip and the character's reaction.
- Inspect intermediate leg poses, contacts, hair attachments and the landing frame.

## Character with a mirror

- Head tilt, hand gesture and mirror angle move together; the grip on the stem or handle holds.
- The reflection is the same performance: fan the character branch out (Fusion reuse is live) through
  a `Transform` with `FlipHoriz` and the mirror's own orientation, clipped by the mirror surface
  matte (Merge "In" or `EffectMask`). Blink and expression are synchronized by construction; never
  animate a second performance. [verified live 2026-09-26] `FlipHoriz` 1 flips about the frame center
  (Pivot 0.5) before `Center` translates; the fanned-out reflection followed every pose change and
  was clipped at the mirror edges by Merge "In" (`t_chars_mirror.png`).
- Delayed hair and earring motion; independent petal travel if asked. Check face-to-reflection
  correspondence and containment through the mirror's full move.

## Animal tracking a flying visitor

- Pupil tracking, head turn, blink and paw reach follow the visitor's actual path: pupils read the
  visitor's `Center` (`Point` expression toward it, clamped inside the eye). The reach has
  anticipation, extension, a readable hold and a controlled return.
- The paw stays connected to the foreleg (11 two-bone IK or overlapping segments). Keep head
  proportions and folded-ear construction; add local ear and tail responses.
- Visitor wings animate independently; its path stays visible enough to explain the animal's
  attention. Nearby flower and grass deflect as the paw passes and recover staggered.
- Check gaze direction, wing and paw attachments, foreground occlusion and the end of the reach.
