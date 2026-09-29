# Rigging: volume and instance ownership

Recipes are **status: unverified (not yet rendered)**.

## Dimensional movement

- Define the supported range from the available design and reconstructed surfaces. Frontal to
  three-quarter can be a limited 2.5D rig; never promise a rear view or full rotation without the art.
- Separate horizontal (yaw) and vertical (pitch) turn controls for the face, and for the body when
  requested. Silhouette, cheek exposure, feature depth, near/far widths, shading and occlusion must each
  respond. Moving every feature by one offset, rotating in plane, or rotating the intact flat image does
  not produce a form change.

Two Fusion constructions:

**A. Feature cards in real depth (Fusion-native parallax).** Each facial part becomes an `ImagePlane3D`
at a meaningful relative Z (nose nearest, then mouth and cheeks, eyes, face rim, ears and rear hair
farthest), all under one `HEAD_3D` `Transform3D`/`Merge3D` whose `Transform3DOp.Rotate.Y` (yaw) and
`Rotate.X` (pitch) come from `CTRL_Face`. The camera projection gives near features more travel and
foreshortens the far side automatically. Limits: keep yaw within about +/-25 deg (flat cards go
edge-on), keep a fixed orthographic-like framing (long `FLength`) if perspective distortion is unwanted,
and swap in reconstructed side art (cheek, ear) past a threshold with `SwitchNumber`-driven `Blend`s.
Z spacing of about 1-4 % of face width is a starting point. [verified live 2026-09-26] Two cards at
Z +0.04 and -0.04 under one `Merge3D` (`Transform3DOp.Rotate.Y` -25 / 0 / +25, camera at Z 1.8) moved
in opposite directions by about 47 px each at UHD: depth-dependent parallax from one rotation.

**B. Pose banks sampled in time.** Key a part's polyline (or the whole part branch) at "pose frames" of
a hidden timeline: frame 0 = three-quarter left, frame 10 = front, frame 20 = three-quarter right
(non-negative frames, inside the source range). Feed the branch through a `TimeStretcher` whose
`SourceTime` = `10 + CTRL_Face.Yaw * 10` (Yaw -1..1): Fusion interpolates points and both
handles with identical weights, so topology and tangents stay matched. [corrected live 2026-09-26]
That holds only at **whole** source frames: TimeStretcher does not evaluate upstream at a fractional
time. `SourceTime` 12.5 showed pose frame 13 in Nearest and a cross-dissolve of frames 12 and 13 (two
overlapping shapes) in Blend. So space the pose frames far apart (for example 0 / 100 / 200 with
`SourceTime` = `100 + Yaw * 100` and Nearest) for 1 % steps, and never use Blend on a pose bank. Use one `TimeStretcher` per
independent control group; only static pose data may sit upstream of it (animated parts upstream would
be sampled at pose time too).

- A projection uses one sign convention, pivot and coordinate system for artwork, attachment landmarks,
  shading and limb frames. Never project twice (a turned card under another turning parent).
- Keep body thickness in the visible contour while front details slide over the surface; reveal
  reconstructed side geometry as needed. Compress the far side without negative scales or collapsing
  features. A face opening stays attached to its costume while the form inside turns.
- Body-only turns, face-only turns and counter-turns stay independently recognizable.

## Instance ownership

- Controls are local: the character is a group/macro whose published inputs feed its inner tools
  (06). Shared immutable pose data is fine (a pose-bank branch inside the group); an inner expression
  that reads a named tool **outside** the group (a global rest rig) makes every instance share one pose
  and is not acceptable. Pasting a group twice renames inner tools `_1` and retargets inner expressions
  (realities §14), which keeps instances independent only if nothing reaches outside.
- The rest rig stays manual and unkeyed; animation lives in a separate performance comp or instance.
- Repairing an existing project: find the source group, demonstration comps and every user instance
  before changing control routing. Keep working names and keys. Update the shared source or every
  relevant copy explicitly; never leave an obsolete manual rig while fixing only the demo.
- Verify two instances with opposite body/face turns and different mouth or hand states in one render,
  and confirm the source group's defaults did not change. [verified live 2026-09-26] A `GroupOperator`
  pasted twice (second copy's inner tools renamed `_1`, inner expression retargeted to
  `VG_G_Ctl_1.NumberIn1`) took published `Input1`/`Input2` independently: +20 deg with an open mouth and
  -20 deg with a closed one (`t_rig_instance_A.png`, `t_rig_instance_B.png`). Clear the active tool
  before the second paste, or Fusion adds a Merge joining the two (realities §9).
