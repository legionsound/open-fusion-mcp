# Characters: native execution

Scoped to illustrated-character builds; general rules in [10](../10-fusion-scripting.md) and
[fusion-realities](../../../fusion-reference/references/fusion-realities.md).

## Select the supported path

- Routes: `.setting` paste for whole character groups (the most reliable way to author polylines,
  their shape keys and handles in one call), Resolve API Python for surgical edits, `fusion_kit.py`
  helpers. No privilege escalation to get around a call that failed for a real reason.
- Resolve targets from the live project every time: comp, group and tool names. Never reuse an earlier
  project's names, coordinates or absolute paths as defaults.
- Vector import (SVG or other artwork): after import check that polylines, masks, gradients, Merge order
  and grouping arrived and that shape keys animate. An importer that brings static shapes and
  transforms alone has not transferred shape animation (import route and behavior unverified on 21.1).

## Build native contours and controls

- Polyline text form (setting-format): `Polyline { Closed = true, Points = { { X = ..., Y = ..., LX,
  LY, RX, RY }, ... } }`; point `X,Y` are offsets from the owning tool's `Center`, handles are relative
  to their point. Shape animation is a spline whose keys carry whole polylines
  (`[48] = { 0, Flags = {...}, Value = Polyline { ... } }`); every key needs the same point count and
  order.
- The animated shape input is `Polyline` on `PolylineMask` (realities §8: it carries a BezierSpline by
  default; the TSV lists only `Polyline2`) and, on `sPolygon`, also `Polyline` (data type "Polyline",
  missing from the TSV harvest; [verified live 2026-09-26] via `GetInputList()` and by pasting
  `Polyline = Input { Value = Polyline {...} }` on sPolygon strokes).
- `PublishID = "PointN"` on a polyline point exposes it as an input for expressions (hands attached to a
  deforming arm contour, pupils riding an eye shape).
- Keep transform controls, contour keys and material controls separately editable. Re-resolve tool and
  input references after grouping or pasting (collision renames, realities §9).
- Keep a builder's changes inside the requested comp; save to a new iteration, never over the only
  approved comp.

## Verify execution and handoff

- Check script syntax and every referenced name before running; after running, read expression
  inputs at two frames and read back real key sets. Offline numeric tests prove only what they tested.
- Render a static pose and a deformed pose from the actual comp (Saver PNG) and look: contour
  deformation, materials, reflection clipping and the chosen cadence must survive the route.
- A timeout is an unknown state: inspect the comp before any retry (realities §15).
- If direct execution is not available and the user wants a script, deliver the `.setting` or Python
  builder with its assets and the exact manual route (paste into the Fusion page node editor, or run
  from Workspace > Scripts), and mark native execution unverified until it has actually run. Never
  present an external vector preview as a Fusion render.
