# Rigging: body construction

Recipes are **status: unverified (not yet rendered)**.

## Hierarchy and sockets

- Declare whether left/right means anatomical or screen side in neutral, and use it everywhere
  (tool names `L_`/`R_` plus a note).
- Rest landmarks (shoulders, elbows, wrists, hips, knees, ankles) are measured from the reference in the
  shared canvas space (artwork-preparation) and stored on the controller as points.
- Chain order builds the hierarchy: forearm+hand -> `XF_ForeL` -> merged over upper arm -> `XF_UpperL`
  -> merged over torso -> `XF_Torso` -> `XF_Root`. Head, neck, torso, hair and clothing stay separate
  tools wherever they move separately; chaining never requires merging their artwork into one image
  before its own Transform.
- Fusion has no parent compensation, so a Transform's values are never "unchanged world coordinates"
  once something upstream moves: solve in one declared space (11: pixel space, comp coordinates, targets
  on the controller). If body volume changes, move sockets and limb geometry with the same projection
  as the torso (volume-and-instances), not just the costume art.
- Shoulder roots stay complete and hidden under the real foreground costume or body surface, with filled
  geometry behind them. Never lift a whole arm above the costume in Merge order to reveal its hand;
  check sleeve exits in both turn directions. Where a gesture crosses the torso, design the
  forearm/hand occlusion explicitly (a second merge of just the forearm above the torso, gated by a
  control) while keeping the hidden root.

## Limb mechanics

- Bounded two-bone IK, FK (keyed segment `Angle`s) or a bendable soft part (native-puppet), per the
  requested motion. Joint radii and overlapping fills compatible; stroked end caps inside the limb must
  not show as rings (draw joint discs as fill only, under both segments).
- IK math: clamp reach to `[|L1-L2|+e, L1+L2-e]`, clamp the `acos` input to [-1, 1], handle unreachable
  targets without blowing up or silently stretching (11 IK1 is checked offline for this).
- Bend direction (pole sign) from anatomy and camera view; verify hip-knee-ankle sign and the silhouette.
  A frontal character's signs do not transfer to a profile. Test planted feet, each lifted foot, a crouch
  and the opposite planted leg. Foot targets meant to stay planted live in comp space on the controller
  and do not ride `XF_Root` turns. Report target error against the reachable or deliberately clamped
  endpoint.
- Body yaw with neutral hand offsets must keep the projected rest arm pose: if the turn shortens the
  projected shoulder width but bone lengths stay planar, the solver bends the elbow. Scale rest lengths
  by the same projection (`L * cos(yaw)` on the horizontal component) or solve in the turned space.

## Hands and secondary parts

- Identify palm, back or side view in the reference before authoring wrist motion. A wrist frame and a
  recognizable thumb with the right handedness. Rotating a dorsal hand flat never makes a palm gesture;
  a palm/back turn needs compatible drawn views switched near edge-on (`SwitchNumber`-driven Merge
  `Blend`s or a `Switch` tool), with a rounded side-thickness view between, finger length kept, and the
  primary outline suppressed near edge-on so it does not collapse to a line.
- The hand extends under its cuff; check the join with a flat cuff or the artwork's own opening, not a
  rounded sleeve cap over the palm. Test both hands at rest, raised and mid-turn.
- Secondary rigid parts (tassels, badges, straps) follow with delayed reads of the parent motion
  (`XF_Torso:GetValue("Angle", time - 3)` style); use native-puppet only when a part must truly bend.
