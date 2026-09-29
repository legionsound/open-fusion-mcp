# Boards: exact animation transfer

Copy approved animation from one element onto others without re-authoring it. Recipes are
**status: unverified (not yet rendered)**.

## Resolve the exact scope

- Resolve source and targets from the live comp with the user's exact selectors. Colored notes, photo
  frames, rounded diagram nodes, badges and unrelated cards are different families; never widen a
  family from visual similarity.
- Inspect source and targets: Transform chains, expressions, effect tools and their order, controller
  values, `Pivot`s, source sizes, time offsets (`TimeSpeed`, controller `time - k` reads), masks and
  nested animation. Preserve the source and unrelated elements.
- Record each target's own content, resting `Center`, resting `Angle`, Merge position and relations.
  Decide whether timing is identical or shifted per target; record stagger as offsets from the
  source, not as a new style.

## Choose the least disruptive method

| Method | When | How |
|---|---|---|
| **Live reference with offsets** (Fusion-native, exact; [verified live 2026-09-26]: `Size` and offset `Center` read 0 error against the source 48 frames earlier at 45 samples incl. half frames) | targets must match the source forever | target inputs read the source's curve: `Note5_Xf.Size = Note1_Xf:GetValue("Size", time - 48)`; points: `Point(Note1_Xf:GetValue("Center", time - 48).X + dx, ... .Y + dy)`; angles `Note1_Xf:GetValue("Angle", time - 48) + (rest5 - rest1)` |
| **Paste Instance** | a copy that shares every parameter except a few | Paste Instance of the source group, deinstance content (`StyledText`, media) and resting transforms |
| **Copy keys** | targets must become independent | read the source splines and write them to each target with a time offset (below) |
| **Duplicate and replace content** | independent cards with compatible chains | copy the source group as `.setting`, paste with a new prefix, swap its content inputs, keep the target's final name; keep the original until the copy validates |

- Prefer editing the existing target when other tools reference it by name, when it has unique
  masks/effects/overrides, or when mattes depend on it.
- Different geometry: set the target's own `Pivot` from its own bounds, then offset `Center` values by
  the difference of resting positions and `Angle` values by the difference of resting angles. This
  constant-offset method needs compatible coordinate spaces (same chain depth, same parents); resolve
  differences first.

## Copying keys faithfully

- Capture per spline: key frames and values, both handles, and flags (`StepIn`, `Loop`, `Pingpong`,
  `LoopRel`). Python `GetKeyFrames()` does not echo flags (realities §14); [verified live 2026-09-26]
  it does return `LH`/`RH` as relative `{1: dt, 2: dv}` per key (string frame keys, value index "1"), and if anything is missing copy through `.setting` text instead (export the comp,
  cut the source spline block, re-target `SourceOp`, paste).
- Apply one constant time offset to every key and handle (relative handles in Python need no change;
  absolute handles in `.setting` shift by the same offset). Keep expressions and controller order.
  Detect absolute-time expressions (`time > 120`, `comp.RenderStart`): shifting keys does not move
  them; adjust deliberately or report why the transfer is not exact.
- Keep linear base keys linear where an Elastic expression reads their slope (motion-design).

## Keep nested reveals aligned

- Map child tools by name and function (heading Text+ to heading Text+, connector stroke to connector
  stroke). Transfer only the reveal animation (`End`/`Start` on Text+, Follower timing,
  `WriteLength`/`WritePosition` on strokes), keeping target wording, fonts, geometry, colors and layout.
- Convert offsets into each child's local time where time offsets or retimes differ; a raw global
  offset is only valid for matching time. Never copy the source's `StyledText` into a target.
- Do not restore tools absent from the approved source; the live source governs, even if an earlier
  version used a different effect.

## Validate before delivery

- Compare before and after: target key data minus the intended time/position/angle offsets should
  equal the source's; allow only floating-point tolerance.
- Re-read in a fresh call after mutation. Sample `GetInput` before the entrance, during movement,
  around extrema and after settle at the offset times (fractional frames allowed), and check the frame
  before each delayed reveal for premature visibility. State the maximum sampled error with units
  (normalized units and pixels).
- Check entrance order, that dependent text follows the new schedule, that target content stayed
  distinct, and that untouched root animation did not change. Render the changed interval (09).
- After a failure or timeout inspect the current state before retrying: a half-finished transfer must
  not be duplicated, offset twice, or mistaken for an untouched target. Never run a whole-comp
  normalization to repair a local transfer.
