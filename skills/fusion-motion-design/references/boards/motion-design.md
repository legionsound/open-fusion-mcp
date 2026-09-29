# Boards: motion design

Timing at 24 fps (AE source values at 30 fps converted). Recipes are
**status: unverified (not yet rendered)**.

## Timing and motion evidence

- Video reference: inspect real timestamps around each entrance, acceleration, peak, overshoot,
  deceleration and hold (02 frame evidence). Compare component trajectories separately from the board
  camera. Fit sparse keys and check between them; rendered footage never reveals the original handles.
- Timing map: first visible frame, active movement, text and stroke intervals, settle, final
  readability per element. Groups may overlap while reading order stays clear; a "sequential" rule can
  apply to one family (the notes) without queuing every object on the board.
- For "smooth" briefs prefer medium or long moves with long deceleration; remove unmotivated short
  stop-start segments. Keep deliberately approved short keys that feed the Elastic expression; there
  is no universal minimum key interval.
- A small speed-up retimes the requested motion and its dependent reveals together, keeping
  normalized curves, order and the required total duration. With timing on controllers (animation
  principles §11 beat sheet) that is one offset change; nothing else moves.

## Printed text, handwriting and lines

- Printed text: Text+ Write On (`End` 0 -> 1 reveals whole characters, layout of the full string is
  fixed, so nothing jumps; 03). For per-character timing use a `StyledTextFollower` with `Order` set
  and a stepped per-character opacity. Keep the full editable string. If a script computes `End` from
  a character count, guard empty strings (`n > 0`). Check spaces, line breaks, punctuation and the
  last character.
- Time text reveals inside the card's own subgraph from the card's timing control
  (`CTRL_Note3:GetValue("Progress", time)` style), so moving a card's entrance moves its text; a later
  card entrance must never reveal already-finished text.
- Handwriting: clean centerline pen paths in writing order, pen lifts as separate strokes (`sPolygon`
  `Solid` 0 + `BorderWidth`, or open `PolylineMask` strokes on a colored Background). One progress per
  phrase distributed across its strokes, weighted by stroke length:
  stroke k `WriteLength` = `math.max(0, math.min(1, (CTRL_Hand.P * TOT - START_k) / LEN_k))`, with
  `START_k` the summed lengths of earlier strokes and `TOT` the total. A rectangle wipe or a trace
  around filled glyph outlines does not look like writing. [verified live 2026-09-26] Three
  `sPolygon` strokes (lengths 0.1/0.2/0.3) read WriteLength 1/0.25/0 at P 0.25, 1/1/0 at 0.5, 1/1/0.5
  at 0.75 and drew in order (`t_boards_handwriting.png`). A stroke at `WriteLength` 0 still renders
  its round cap as a dot: gate each stroke's Merge `Blend` with `iif(... > 0, 1, 0)` (or use a flat
  `CapStyle`) so unwritten strokes are invisible.
- Connectors, arrowheads, borders, underlines, selection outlines, doodles: intentional path direction
  (point order) and stagger. The arrowhead appears as its shaft finishes
  (`iif(Shaft.WriteLength >= 0.98, 1, 0)` on its Merge `Blend`, or a 3-frame scale pop). Static
  components stay static when the reference says so.

## Card and note entrances

- Photo cards: small position offset + restrained rotation + opacity + controlled scale bounce;
  final crop, placement and text intact.
- Colored notes (default): flat Elastic scale and rotation with a soft shadow (`Shadow` or a blurred
  `RectangleMask` copy). Rounded diagram nodes: flat, much subtler bounce. No folded backs, curls or
  reflective backsides unless the brief asks (curl route: artwork-and-interaction).
- A family that enters sequentially exposes `Start` and `Stagger` on its controller; let each note
  settle before the next prominent entrance. Label, heading, body, owner and edge reveals ride with
  their card and keep their internal order.

## Optional Elastic entrance profile

Only for a new board when no reference or live user edit sets different behavior. Every value is a
control.

| Parameter | Starting value (24 fps) |
|---|---|
| Position ease | zero end speeds; out influence 45 %, in 100 % = cubic-bezier(0.45, 0, 0, 1) |
| Opacity ease | out 40 %, in 60 % = cubic-bezier(0.40, 0, 0.40, 1) |
| Scale rest | `Size` 1.008 |
| Photo scale | 0.06 -> 1.008; colored note 0 -> 1.008 |
| Scale key interval | 1/6 s = 4 frames (5 at 30 fps); linear base keys |
| Note rotation | rest + 46 deg -> rest over the same interval, linear |
| Elastic amplitude / frequency / decay | 0.1 / 4/3 Hz / 6 per s (AE controls 20/200, 40/30, 60/10) |
| Velocity sample | 0.1 frame before the last key |
| Photo translation | small diagonal offset -> rest over ~1.4 s (34 f) |
| Note translation | small rise over ~1.87 s (45 f), starting ~0.31 s (7 f) before the scale |
| Sequential stagger | 2 s (48 f) when duration allows |
| Motion blur | `ShutterAngle` 180 on moving Transforms |

Fusion form: an input holds keys or an expression, not both, so the linear base keys live on the note
controller (`CTRL_Note3.ScaleBase`, `CTRL_Note3.RotBase`) with the last key frame stored as a control
(`KeyEnd`), and the consumer adds the decaying bounce:
```
Note3_Xf.Size =
:local fps = comp:GetPrefs("Comp.FrameFormat.Rate")
local tk = CTRL_Note3.KeyEnd
local b = CTRL_Note3:GetValue("ScaleBase", time)
if time <= tk then return b end
local v = (CTRL_Note3:GetValue("ScaleBase", tk) - CTRL_Note3:GetValue("ScaleBase", tk - 0.1)) * fps / 0.1
local t = (time - tk) / fps
return b + v * CTRL_Note3.Amp * math.sin(CTRL_Note3.Freq * t * 2 * math.pi) / math.exp(CTRL_Note3.Decay * t)
```
Expected (offline simulation of 0 -> 1.008 over 4 frames at 24 fps): velocity 6.05/s, peak `Size`
~1.257 about 2.75 frames after the key, undershoot ~0.98 near +12 frames, within 0.01 of rest by +24
frames. [verified live 2026-09-26] This multi-line `:` expression (newlines kept, set through
`SetExpression`) with `ScaleBase`/`KeyEnd`/`Amp`/`Freq`/`Decay` as UserControls on a `Custom`
controller read 1.2571 at +2.75 f, 0.9819 at +12 f and 1.0093 at +24 f, matching the offline numbers
to 1e-9; `CTRL:GetValue("ScaleBase", tk - 0.1)` reads a UserControl's spline at a fractional frame. Rotation uses the same form on `Angle` with `RotBase`. Expose `Amp`, `Freq`, `Decay` as named
UserControls (06); scale the displacement to card size if a card is rescaled after build.

## Collaborative cursors

- Cursor count, names, colors, entrance start and stagger are inputs. Each cursor unit (pointer,
  nameplate, name) sits above the board artwork and below nothing it must not cover.
- Default for an 18 s assembly: cursor entrances from 10 s (f240) with 1 s (24 f) stagger and a ~0.7 s
  (17 f) fade; each name shortly after its arrow. Recompute for other durations or counts so every
  cursor is readable before the end; explicit timing wins.
- After entry each cursor follows its own irregular route: `PolyPath` (path shape + `Displacement`
  0..1 with gentle speed changes) or `XYPath` with sparse keys and smooth handles; varied distances,
  pauses and phase. No per-frame randomness, no synchronized copies.
- Motion running to the last frame: continue the route past the comp end instead of a zero-speed stop
  inside it; keep cursor bounds inside frame along the whole route (render the extremes).
