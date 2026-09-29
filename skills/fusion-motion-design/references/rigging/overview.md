# Rigging: face, body, soft parts and delivery (Fusion)

The complete pipeline for building or repairing a 2D character rig in Fusion: artwork separation,
face and body controls, soft-part deformation, dimensional turns and the rendered rig test. Read first
for any rig request. [11 Character production](../11-character-production.md) adds the production wrap
(measured motion, two-bone IK, reference playback, passes); [characters/overview](../characters/overview.md)
owns animating the finished character. Port of Higgsfield `ae-clean-rig/references/rigging/` (local
connector, 2026-09-26). Recipes are **status: unverified (not yet rendered)**.

## What differs from After Effects

Fusion has **no Puppet pin tool** and no bone/ARAP mesh. It rigs with:

| AE mechanism | Fusion mechanism |
|---|---|
| Parenting + anchor points | Transform chains: child part -> own Transform (`Pivot` at the joint) -> merged over parent part -> parent Transform. One `Pivot` per joint, no compensation step |
| Puppet pins on a soft part | [native-puppet](native-puppet.md): gradient-weighted `Displace` (root pinned by a 0 weight), `KD_Bend` along an arc, `GridWarp` destination mesh keys, polyline/sShape shape keys with vertex correspondence, or `Bender3D` on a subdivided `ImagePlane3D`; the Resolve FX `Warper` OFX for point warps driven from the UI |
| Track mattes sharing an aperture | one mask tool fanned out to every consumer (`EffectMask`, Merge "In"/"Held Out"): the same output, so boundaries cannot disagree |
| Essential Properties forwarded through precomps | group/macro published inputs (`InstanceInput`), per instance (06) |
| Expression IK | pixel-space two-bone IK on a controller (11 recipe IK1) |
| Dimensional turn | feature cards at relative depths under one `Transform3D`/`Merge3D` head (real parallax), or pose banks sampled by a `TimeStretcher` ([volume-and-instances](volume-and-instances.md)) |

## Outcome and inputs

- Produce an editable Fusion character (a group/macro with published controls) whose separated artwork,
  controls and demonstrated motion preserve the supplied design, verified in rendered pixels. A
  generated animation alone does not satisfy a rig request.
- Reuse the user's reference, earlier approvals, requested movement and the existing project. Decide
  whether the task covers face, body, soft parts or one existing defect before touching artwork.
- Inspect the source at its original dimensions and the existing comp. With neither an accessible
  reference nor a sufficient brief, get the missing input before inventing a design. A brief-only
  request may generate a reference within scope through a connected provider (05, 17), inspected before
  rigging. Keep an accepted design. Tutorials count as studied only when their video or transcript was
  actually read; separate observed technique from inference.

## Prepare and choose the rig

- Inspect the project and comp and read the build (`resolve.GetVersionString()`); follow
  [native-execution-and-delivery](native-execution-and-delivery.md) before changes; keep the user's comp
  and animation in a versioned copy.
- New image, changed topology or thin overlap: [artwork-preparation](artwork-preparation.md) before any
  deformer. A repair corrects the affected dependency chain and keeps unaffected controls and artwork;
  recheck separation wherever the repair exposes hidden areas.
- Face controls: [face-construction](face-construction.md). Limbs or torso:
  [body-construction](body-construction.md). A new rig defaults to limited dimensional face and body
  turns where the visible anatomy supports them, unless the user asks for flat;
  [volume-and-instances](volume-and-instances.md) governs them, and yaw/pitch must change form and
  occlusion. No invented body for a portrait-only request.
- Flexible parts: [native-puppet](native-puppet.md) after preparation. Rigid parts: pivots and
  Transform chains. A requested soft deformation needs a verified deformer, never a renamed transform.

## Animate and finish

- Keep a clean manual rest rig (the group with neutral published values, unkeyed) and a separate
  animated demonstration (an instance or a second comp that keys the published inputs).
- A short performance that clearly puts each requested control to work, with holds long enough to
  read, timing chosen on purpose and secondary motion kept modest. If line boil was asked for, it can
  be dialled up or down.
- Only publish the controls that mean something for this character, each with a plain name, a neutral
  default and its tested range written in the label.
- Run the pose, instance and rendered-media checks in native-execution-and-delivery; fix and rerender.
  Deliver the saved project, required artwork, usable controls, previews and short operating notes.
  State real turn limits and missing capabilities; never call an unverified deformer, an unrendered comp
  or a routing-only test a finished rig.
