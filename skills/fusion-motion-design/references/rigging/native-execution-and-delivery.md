# Rigging: native execution and delivery

Read before changes and again for delivery. General rules: [10](../10-fusion-scripting.md),
[fusion-realities](../../../fusion-reference/references/fusion-realities.md).

## Application operations

- Routes: `.setting` paste for whole part groups and controllers (polylines, shape keys, handles,
  published inputs in one call), Resolve API Python for surgical edits, `fusion_kit.py` helpers. If a
  needed capability is missing (for example scripted GridWarp point edits), report it and keep the
  preparation instead of claiming a finished rig. No privilege escalation around a failing call; keep
  code inline in the skill or the builder you deliver.
- Back up first: `item.ExportFusionComp(path, i)` plus a project save, in a versioned name.
- One mutation at a time; wait for real completion before a dependent call. A timeout after the call was
  accepted means unknown completion: inspect before replaying (realities §15). An old success report
  says nothing about the current call.
- Freeform vector parts: `PolylineMask` (`Polyline` input) or `sPolygon`, points and handles written as
  `.setting` Polyline tables (setting-format); colors as split float channels. Re-resolve tool names
  after pastes or grouping (collision renames). Tools are not "locked" in Fusion, but a tool in
  pass-through (`TOOLB_PassThrough`) renders nothing of its own: check before debugging.
- Shared apertures: one mask output fanned out (face-construction); for holdouts, Merge "Held Out" or
  the mask's `Invert`. Confirm each consumer's mask input with `GetConnectedOutput()`.
- Vector parts stay resolution independent until a Merge flattens them; zoomed rigs keep the Merge
  canvas large enough (boards/camera-and-easing resolution trap).
- Published-input enumeration: read a group's inputs with `GetInputList()` and match `INPS_Name`;
  never assume an order.

## Visual and numerical verification

- Render the source-matched neutral pose, relevant extremes and in-between transitions with boil and
  motion blur off. Dimensional work: requested head yaw and pitch with silhouette and occlusion changes;
  body turns and opposed face/body motion only when body controls are in scope. Faces: gaze at the
  boundary, half and full blinks, independent lids, each mouth pose, small to large openings. Limbs: both
  hands, sleeve sockets, planted feet, lifted feet, a crouch. Add an exploded-parts view when separation
  must be shown.
- Evaluate expressions at two frames (no nil, no NaN or inf), reachable-target drift, stable bend
  direction; compare shared aperture boundaries; confirm mask wiring. These checks add to looking,
  they do not replace it: perfectly valid paths can still produce diamond-shaped eyes, wrong thumbs,
  exposed shoulder caps or two mouths. Zoom in on trouble spots, and check the instance inside its final
  comp as well as the source group.
- After changing nested expressions, judge freshly written Saver frames, not the viewer cache. Wait for
  file writes to finish; never run mutation tests concurrently with a render.
- Verify independent instances when the rig is reusable. Restore temporary QA values and times without
  deleting user keys. Inspect the exported video at rest, extremes and transitions, check duration and
  frame count, decode the whole file (`ffmpeg -v error -i out.mov -f null -`). Judge a loop by its
  boundary poses and motion, not by the player repeating it.

## Deliverable

- The saved project with a discoverable manual rig (one group or macro, grouped meaningful published
  controls, neutral defaults), linked artwork, an animated demonstration, usable previews and short
  operating notes (defaults, tested ranges, known limits). Confirm external assets resolve from the
  handover folder (15). An Edit-page template is optional; the rig stays editable on the Fusion page
  without it. Keep earlier versions and checkpoints apart from the current package.
- Report what changed, what was rendered and inspected, and what is incomplete. A syntax check, a numeric
  test or a routing evaluation cannot certify visual rig quality; never promise an automatic rig for an
  unseen design whose separation, reconstruction or deformation is unverified.
