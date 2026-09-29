# 11 Character production: motion first, reference playback, compositing passes

Load around a character rig that exists or is being built with [rigging/overview](rigging/overview.md).
This module is the production wrap, not joint placement or artwork separation: read the reference's
motion before designing the rig, keep manual controls free while automatic motion plays, add light and
texture as editable passes, and validate against the reference. Port of Higgsfield `ae-clean-rig`
module 11 (local connector, 2026-09-26). Timing at 24 fps. Every recipe here is
**status: unverified (not yet rendered)** unless it says otherwise.

## Establish the actual motion before designing the rig

- Inspect clean and occluded reference frames (02 frame evidence). Separate whole-scene motion,
  character or vehicle travel, limb gestures, face-shape changes, fluid/ribbon deformation and
  foreground occlusion. Elements can have different periods: in the Higgsfield flying-bottle study
  image measurement showed a 1 s bottle translation cycle while the gesture and atmosphere were
  treated over 2 s; the contact sheet alone had suggested the wrong period.
- Measure to find extrema, then fit a sparse trajectory. Sampling every source frame for analysis
  (`scripts/measure_ref.py`, a `Tracker` pass read as data) is fine; it is not a reason to key every
  frame. Preserve real contact points and phase relations. A cloud crossing a hand is not evidence
  that the hand vanished or changed shape.
- Record per element: period in frames, phase offset against the root cycle, extrema frames, holds.
  That table becomes the controller's `Phase` and per-part offsets.

## IK in one coordinate space

Fusion has no bone or IK system for 2D artwork. Build limbs as Transform chains (child artwork
passes through its own Transform, is merged over the parent segment, and the merged result passes
through the parent's Transform) and solve two-bone IK analytically in SimpleExpressions.

Rules that make it hold:

- **Solve in pixel space.** Normalized `Center` values are not isotropic on 16:9 (0.1 in X is 384 px
  at UHD, 0.1 in Y is 216 px). Convert start, target and pole side to pixels (`dx*W`, `dy*H`), solve,
  convert back. Transform `Angle` rotation is pixel-isotropic, positive counterclockwise (realities §14).
- Solve in one declared space. If the shoulder rides a torso Transform, feed the solver the
  shoulder's final comp-space position (the controller point that also drives the torso), never an
  unconverted local value from inside the chain. Fusion has no `toComp`/`fromComp`; keeping every
  rig point on one controller in comp space is the substitute.
- Law of cosines for the joint, the pole sign for bend side, and explicit handling of coincident or
  unreachable targets (clamp distance to `[|L1-L2|+e, L1+L2-e]`). A stretch option, if any, is a
  bounded control with stated units (percent of limb length).
- The rendered hand or foot uses the solver's **reachable** endpoint too; otherwise the limb stops
  short of a freely moving palm. The whole wrist/ankle assembly (palm, fingers, cuff, shoe, prop)
  sits upstream of the forearm/shin Transform so it rides the chain; hand twist or foot roll stays an
  independent control on its own Transform before that.
- Test a moved parent and a moved endpoint together. Neutral-root tests miss coordinate-space
  errors. When a detail is re-attached to a different chain, set its own `Pivot`, `Center`, `Size`
  and `Angle` explicitly; a small cuff or shoe detaches even when the main hand is right.

### Recipe IK1: two-bone arm from one controller [verified live 2026-09-26]

Graph (rest pose drawn straight, shoulder at `Sr`, elbow at `Er`, pointing along `rest` degrees):
```
HandArt -> XF_Hand (Pivot = wrist rest, Angle = CTRL_Arm.NumberIn7 twist) --+
ForeArt ------------------------------------------------------------------ M_Fore.Background
                                                                            M_Fore.Foreground <- XF_Hand
M_Fore -> XF_Fore (Pivot = Er, Angle = CTRL_Arm.NumberIn6) -> M_Arm.Foreground
UpperArt -------------------------------------------------------------> M_Arm.Background
M_Arm -> XF_Upper (Pivot = Sr, Angle = CTRL_Arm.NumberIn5 - rest)
      -> XF_ArmPos (Center = Point(0.5 + S.X - Sr.X, 0.5 + S.Y - Sr.Y)) -> body Merge
```
`CTRL_Arm` is a `Custom` tool (never wired into the image path): `PointIn1` shoulder S (expression
from the body controller), `PointIn2` hand target (the user keys it through `XYPath`), `NumberIn1`
L1 px, `NumberIn2` L2 px, `NumberIn3` pole (+1 or -1), `NumberIn5` upper angle (deg, expression),
`NumberIn6` forearm bend relative to the upper arm (deg, expression), `NumberIn7` hand twist,
`PointIn3` elbow and `PointIn4` reachable wrist (expressions, for QC overlays and attached props).
Keeping `XF_Upper.Center` at 0.5 and translating in a separate `XF_ArmPos` keeps rotation about a
fixed image point, whatever the Pivot/Center coupling of the Transform.

```python
PRE = (':local W = comp:GetPrefs("Comp.FrameFormat.Width") '
       'local H = comp:GetPrefs("Comp.FrameFormat.Height") '
       'local dx = (PointIn2.X - PointIn1.X)*W local dy = (PointIn2.Y - PointIn1.Y)*H '
       'local L1, L2 = NumberIn1, NumberIn2 '
       'local d = math.sqrt(dx*dx + dy*dy) '
       'd = math.max(math.abs(L1 - L2) + 0.001, math.min(L1 + L2 - 0.001, d)) '
       'local c = math.max(-1, math.min(1, (L1*L1 + d*d - L2*L2)/(2*L1*d))) '
       'local a = math.atan2(dy, dx) local t1 = a + NumberIn3*math.acos(c) ')
ctrl = comp.FindTool('CTRL_Arm')
ctrl.NumberIn5.SetExpression(PRE + 'return math.deg(t1)')
ctrl.NumberIn6.SetExpression(PRE + 'local ex, ey = L1*math.cos(t1), L1*math.sin(t1) '
                             'local wx, wy = d*math.cos(a), d*math.sin(a) '
                             'local r = math.deg(math.atan2(wy - ey, wx - ex) - t1) '
                             'return (r + 180) % 360 - 180')          # wrap to [-180, 180)
ctrl.PointIn3.SetExpression(PRE + 'return Point(PointIn1.X + L1*math.cos(t1)/W, PointIn1.Y + L1*math.sin(t1)/H)')
ctrl.PointIn4.SetExpression(PRE + 'return Point(PointIn1.X + d*math.cos(a)/W, PointIn1.Y + d*math.sin(a)/H)')
for f in (0, 12, 24):
    print(f, ctrl.GetInput('NumberIn5', f), ctrl.GetInput('NumberIn6', f), ctrl.GetInput('PointIn3', f))
```
The math was checked offline in Python (forward kinematics from these angles lands exactly on the
reachable wrist for in-reach, full-reach and coincident targets; pole -1 mirrors the elbow).
[verified live 2026-09-26] This exact block evaluates in Resolve 21.1 (`math.atan2`, `math.acos`,
`math.deg`, `%`, `comp:GetPrefs` inside `:` blocks; bare `PointIn1.X`/`NumberIn1` names resolve on the
Custom tool). Read-backs of `NumberIn5/6` and `PointIn3/4` matched the offline solver to 4 decimals at
six frames (in reach, full reach, beyond reach, pole -1, body + target moved in the same frames,
coincident target). Rendered chain: the wrist dot sits on the target in reach, the arm straightens and
stops at the reachable point beyond reach (no pop across the sweep), `NumberIn3` -1 mirrors the elbow,
and moving `CTRL_Body.PointIn1` and the target together translates the arm with unchanged angles
(shoulder stays attached). `CTRL_Arm.PointIn2` takes `XYPath` keys; `PointIn1` driven by the
expression `CTRL_Body.PointIn1` works. A pasted `Custom` tool also brings four `LUTBezier` splines
(`CTRL_ArmLUTIn1..4`): count them in audits, do not delete them as orphans.
Evidence: `renders/skillsgap/t11_ik_sheet.png`.
Verify: read-back values are numbers at two frames (a nil means an expression failed); render with the
target inside reach, at full reach and beyond reach (wrist stops at the reachable point, no pop); flip
`NumberIn3` and confirm the elbow swaps side; move the body controller and the target in the same
frame and confirm the shoulder stays attached. Upper-arm and forearm angles use `atan2` in Y-up pixel
space, which matches Transform `Angle` sign. Legs: same rig, `NumberIn3` chosen so knees bend forward.

## Manual posing and reference playback

- Automatic offsets live on helper Transforms or controller terms, leaving the advertised hand/foot
  targets (`CTRL_Arm.PointIn2` via `XYPath`) free for keys (06 ordinary transforms).
- Controls on the character controller: `RefLoop` (checkbox, reference playback on/off), `Phase`
  (frames, offsets the loop), `Amount` (0..1 per motion family) and a sparse pose library. The
  library is a Lua table inside a `:` expression block or a `SwitchNumber`/`SwitchPoint` modifier
  indexed by a `Pose` control; consumers read `CTRL.Manual*(1 - RefLoop) + ref_value*RefLoop`.
- A manual template can be a real independent copy (plain paste, new prefix) of the rig with
  `RefLoop` 0, not a hidden duplicate of the playing one.
- Document ownership in the control labels: a manual target may **add** an offset to the automatic
  pose, an instance override may **replace** a value. Never expose a slider with no visible effect.
- Exercise face controls as well as limbs. A blink contracts each eye about its own center (each
  eye's Transform `Pivot` at that eye, or sEllipse `Height` keyed per eye), never by scaling a whole
  eye group toward the head origin (08).
- Fit independent curves for the observed gesture and for shared motion; hold where the reference
  holds; snap pose events to measured source frames (02). No idle breathing, head bob, extra foot
  swings or `Perturb` noise to make the rig look sophisticated.

## Compositing as editable passes

After the rig works, add lighting, contact shadow, material variation and texture as distinct, named
passes on the character's stream, each switchable (Merge `Blend` 0 disables a pass without rewiring).

| Pass | Fusion construction |
|---|---|
| Shared flight/travel | rider, vehicle and the attached part of a trail all merge **before** one `XF_Flight` Transform, so one move carries them |
| Near and far atmosphere | separate branches: far haze under the character, near cloud over it; the foreground can cross the subject without joining its artwork |
| Contact shadow | `Shadow` tool fed by the posed character (`OutputMode` 1 = Shadow Only, `ShadowOffset`, `Softness`, `Red/Green/Blue/Alpha`) so it shares pose and timing; clip it to the receiving surface with Merge `Operator` "In" against the surface matte or an `EffectMask`. Never a second hand-animated shadow. [verified live 2026-09-26] Merge "In" with the surface on Background and the shadow on Foreground outputs only the shadow inside the surface alpha (the surface itself is not in the output: merge the surface separately below it); OutputMode 1 alpha equals the `Alpha` input (0.85 read back); the shadow follows the pose frame to frame (`t11_shadow_sheet.png`) |
| Light on material | a `Background` gradient (`Type` "Gradient", `GradientType` Radial/Linear) merged with `ApplyMode` "Soft Light" or "Overlay", masked by the character alpha; expose angle/intensity on the controller |
| Printed color vs moving light | keep flat color regions (fills) upstream and light passes downstream; the light must not repaint the print |
| Object-attached grain | `FastNoise` merged inside the object's subgraph **before** its Transform (moves with the object) |
| Screen/film grain | `FilmGrain` or `Grain` after the final Merge (stays on screen) |

- Static paper grain: `FastNoise` with `SeetheRate` 0 and fixed `Seethe`, `Center` unkeyed; no
  per-frame boiling. [verified live 2026-09-26: frames 0 and 10 identical to the bit at SeetheRate 0;
  at SeetheRate 0.5 they differ.] FastNoise's default Color 1 is transparent black, so the noise lives
  in alpha (a PNG of it reads white RGB with varying alpha). `FilmGrain` `TimeLockSeed` 1 freezes film grain for stills.
- A global blur does not fix a rough silhouette or a broken joint; fix the artwork or the chain.
- Blur edge handling: `Blur` `ClippingMode` "Frame" (default), "Domain" or "None" changes what the
  blur samples at the frame/DoD boundary. [verified live 2026-09-26, size 20 at UHD] "Frame": a
  full-frame image keeps opaque edges and a small source's blur spreads past its DoD; "Domain": the
  blur is cut at the input's DoD (hard rectangular edge, alpha jumps 0 to 0.5): the rectangular
  color-field failure; "None": outside the frame counts as transparent, so a full-frame blur fades at
  the edges (alpha 0.5 mid-edge, 0.25 at corners). In the AE study a blur's Repeat Edge Pixels created
  rectangular color-field edges; the Fusion twin is a wrong `ClippingMode` or an unexpanded DoD.
  Render and inspect the alpha and edges; do not flip the option on every blur.
- After routing a matte (Merge "In"/"Held Out", `EffectMask`), confirm the receiver still renders:
  a matte wired into the wrong input silently blanks the artwork.
- Expose the useful light and material parameters and check each one changes its own pass.

## Validate the rig, then record the lesson

1. Render a clean neutral pose, the maximum reference bend or gesture, and at least one manual pose
   with `RefLoop` 0.
2. Move a hand, a foot and the hips/torso; edit a material color and one face control; check
   connections, overlap order, contact and clipping. Test the advertised reach limit as well as
   comfortable poses. Restore intended values afterwards.
3. Review a real-time render at normal speed and at matching reference frames, including intervals
   partly hidden by foreground effects. Check the loop boundary (seam value and velocity), the parent
   motion and each independently phased gesture.
4. Count honestly: artwork tools, helpers, spline keys and expressions per group (09 complexity
   audit). A three-node top level can still hide a dense or broken construction.
5. Deliver the animated scene, the editable rig/manual entry point, dependencies and a preview. A
   reference may be a labelled guide or audio-only source, never the hidden rendered character.
   Separate "measured structural reconstruction" from "pixel-exact" (unproven), keep aesthetic
   acceptance apart from technical rig checks, and fold the user's corrections into this workflow.

## Don'ts and failure lessons

- Don't solve IK in normalized coordinates on a non-square frame: limbs change length as they rotate.
- Don't let the drawn hand follow the raw target when the solver clamped reach.
- Don't hang props or cuffs from the wrong chain level; re-set their local transform after moving them.
- Don't give the shadow its own animation; derive it from the posed character.
- Don't put automatic motion on the input the user is meant to key (06).
- Don't infer a period from a contact sheet; measure it.
