# 12 Symbol characters, pose catalogues and typographic scenery

Load when glyphs form an animal or object, when text assembles into a figure, or when a reference
shows a sheet of changing poses. These are designed figures made of parts; treating them as
multi-line ASCII strings in one Text+ loses their anatomy and motion. Narrow add-on, unrelated to
drawn artwork (that is [characters/overview](characters/overview.md)). Port of Higgsfield
`ae-clean-rig` module 12 (local connector, 2026-09-26). Timing at 24 fps. Recipes are
**status: unverified (not yet rendered)**.

## Establish the visual vocabulary

- Frame selection and cut mapping follow [02](02-reference-motion.md). Measure clean held poses
  before fast in-betweens. Separate body parts, labels, counters, selection blocks and scenery.
- Per visible glyph record: role (ear, knee, eye), font, weight, bounds, baseline, orientation,
  color. Verify each glyph in a native render and with the coverage check in
  [14](14-localization-typography.md): a character missing from the font renders as an empty box
  (tofu, no fallback font; verified live 2026-09-26) with no expression error.
- Replace an unsuitable glyph with a small semantic path when needed: a three-point knee as an
  `sPolygon` (`Solid` 0, `BorderWidth`) or a rounded neck corner as a short `PolylineMask` stroke.
- Give the character one root that never jumps, plus anchors where it touches things or looks. Place
  the authored parts once; do not re-center or re-scale the whole figure from rendered bounds that
  change every frame (Fusion's counterpart of AE `sourceRectAtTime` is `Tool.Output[0].DataWindow`).
  Folding an ear, blinking or growing legs leaves the figure where it is unless the reference moves it.
- Treat background scenery as its own set of symbols. A V-shaped stem, an arrow-shaped stem, a trio of
  dots and a lone sprout are four motifs even if each reads as "a flower", and a table of biography
  facts is not a block of code. Before any motion, match the kind of content, its hierarchy, how it
  clusters, how dense it is, its relative scale and the empty space around it; give every measured
  motif family its own source.

## Model complete states, then connect them

Each part is its own tool with a stable name (`FROG_Head`, `FROG_LegL`, one `TextPlus` or small
sShape per part), merged in a character subgraph that ends in one `FROG_Root` Transform. Store only
what changes per state: `Center`, `Angle`, `Size`, visibility (Merge `Blend`), and sometimes the
glyph (`StyledText`).

Keep three controls independent on `CTRL_Frog`:

| Control | Meaning | Drives |
|---|---|---|
| `Build` (0..N, stepped) | which semantic parts exist yet | each part's Merge `Blend`: `iif(CTRL_Frog.Build >= 3, 1, 0)` |
| `Pose` (index, stepped) | the full arrangement of visible anatomy | per-part pose tables |
| Root motion | where the whole figure travels, including lift and contact | `FROG_Root` Transform keys (or `XYPath`) |

Pose tables, two native routes:

- **Lua table in a `:` expression** on each changing input (compact, one place to edit):
  `:local p = {Point(0.52,0.61), Point(0.53,0.64), Point(0.50,0.58)} return p[math.floor(CTRL_Frog.Pose) + 1]`
- **Switch modifiers**: `SwitchPoint`/`SwitchNumber`/`SwitchText` (`NumberOfInputs`, `Source`,
  `Input0..n`) on the input, `Source` linked to `CTRL_Frog.Pose`. Each option stays a visible,
  editable input.

Stepped changes use `StepIn` keys on `Pose`/`Build` (hold keys); continuous curves only for motion
the reference shows as continuous. A table with a drawing for every source frame is dense animation
hidden in an expression, not a pose library.

- When text assembles into a character, the same part tools travel through every line wrap into the
  finished figure; do not cut to a separately drawn whole string at the end.
- A crouched frog, legs springing loose, a full stretch, the tucked mid-air shape and the landing may
  each need their own glyph combinations and joins; one long leg string pulled longer cannot say all
  of that. Lift the root in step with the feet and the body pose, and judge foot contact, body
  position and the hand-off from one pose to the next as a set. Add short head/body offsets (a
  turtle's head trailing its shell as it lands) only where you measured them, as `time - k` samples of
  the root curve.
- Say exactly when the figure is visible, before the first part lands and after the last (`Build`
  keyed to 0 until the build begins). Later scenes reuse a finished pose library that is kept apart
  from the build animation ([06](06-editable-rigs.md) artwork vs playback reuse), so a montage that
  samples frame 0 gets a whole figure, never an empty or half-assembled one.

## Pose sheets and catalogues

- Count the states the sheet actually shows before choosing how many poses to build. A column might
  hold lopsided ears, a wink, a side view, folded wings or a different walk; rotating two or three
  near-matches through a long row of labelled columns does not recreate that range. The reverse
  holds too: many cells are no reason to make up states the reference never shows.
- When the reference moves them in lockstep, run the row labels and every character row off a single
  `Index` on the sheet controller, and get each row's pose from an explicit mapping
  (`pose = map[row][(Index + col) % n]` in a `:` block, Lua `%` is already non-negative).
- Keep four things apart: pose index, the time that index represents, movement of the sheet, and any
  framing or scale cut. Keep authored foot/body anchors fixed across a row.
- Build the grid by generated `.setting` text (one subgraph per cell with unique prefixes, the
  07 card-generation pattern) or Paste Instance copies with `Pose` deinstanced per cell. Expose
  manual `Index` and row size once, not per copy. Labels: Text+ with
  `Text(string.format("%02d", CTRL_Sheet.Index + col))`.
- Measure how many rows there are, their order, spacing, crop and numbering, the order they appear
  in and how long the last frame holds. A moving sheet may crop at its edges on purpose; a hero figure
  drifting out of frame by accident is a bug. Check the hero pose at the moment it shrinks into a
  cell, and compare the final catalogue frame with the opening frame of the next scene,
  including one-frame overlays (02 cut rules).

## Scenery assembly and large glyphs

- Plants, bubbles, bugs, seeds: key measured births and state changes (Merge `Blend` step, `Size`
  pop with the [animation-principles](animation-principles.md) §16 house reveal only if the
  reference pops). First-frame population, growth stages
  and the held end state matter. No drifting, blinking or periodic motion because the motif suggests
  it.
- Many symbols building a larger numeral or word: match coarse silhouette, occupied cells, motif
  families and stroke weight before tuning births. Keep strokes, corners, seeds and blossoms that
  change separately as separate tools. One whole-cell pop repeated everywhere misses an assembly made
  of independent parts. `sDuplicate`/`sGrid` suit one motif family on a regular lattice, not a mixed
  mosaic.
- Fixed reference artwork is not a text generator. A control named `Number` must really regenerate
  the numeral (drive cell occupancy from a digit bitmap table); otherwise label the value as
  reference information and expose a working `Build`/`Phase` control. Never advertise arbitrary
  text or number replacement for an authored fixed mosaic.

## Recipe S1: glyph creature with Build, Pose and root [verified live 2026-09-26, except root lift]

```
FROG_Head (TextPlus "@") -> M1.Foreground     FROG_Body (TextPlus "(  )") -> M1.Background
FROG_LegL (TextPlus "/") -> M2.Foreground  <- M1 ...   FROG_Knee (sPolygon 3 points -> sRender)
... -> FROG_Root (Transform) -> scene Merge.Foreground
CTRL_Frog (Custom): NumberIn1 = Build (StepIn keys), NumberIn2 = Pose (StepIn keys)
```
Each part's merge `Blend` = `iif(CTRL_Frog.NumberIn1 >= k, 1, 0)`; each changing `Center` uses a pose
table read by `CTRL_Frog.NumberIn2`. Verify: frame before the build shows no part; each `Build` step
adds exactly one part; each `Pose` value renders the measured arrangement without moving the root;
root lift keeps the feet on the contact line at landing; a montage consumer with `Pose` fixed shows
the complete figure at every frame.

[verified live 2026-09-26] Pasted as one `.setting`: `StepIn` keys on `Build`/`Pose` hold (Build read
0 at frames 0-3, 1 at 4-7, 2 at 8); the Lua pose table `p[math.floor(CTRL_Frog.NumberIn2) + 1]`
returns the listed `Point` per pose; a `SwitchPoint` (`NumberOfInputs` 3, `Input0..2`) whose
`Source` carries the expression `CTRL_Frog.NumberIn2` feeds a Text+ `Center` and switches with the
pose; Merge `Blend` `iif(... >= k, 1, 0)` adds exactly one part per Build step and the frame before
the build is empty. A `TimeStretcher` consumer (`InterpolateBetweenFrames` 0) sampling source frame 0
shows an empty figure (the trap); sampling a frame after the build completes shows the whole figure
at every output frame. Pasted splines get renamed `CTRL_FrogNumberIn1/2` (realities §14). Root lift
and foot contact were not tested (needs a designed scene). Evidence: `renders/skillsgap/t12_s1_sheet.png`,
`t12_mont0.png`, `t12_mont30.png`.

## Evidence and limits

Render the full comp, not isolated parts. Check initial assembly, completed pose, one asymmetric or
extreme pose, a manual override and the cut into the next scene; inspect later consumers of the same
sources; keep visual fidelity separate from control checks ([09](09-validation-delivery.md)).

Failures seen in an earlier study of this style (take the lessons, not the counts or fonts): spiders
that appeared half-built because an entrance animation was reused at frame 0; knees with no glyph; a
body and legs that drifted apart because the pose logic was incomplete; catalogue states shown twice;
one generic arrow standing in for several different flower families; biographies rendered as code; a catalogue exiting six frames early (10 premature-cut checklist).

## Don'ts

- Don't put a whole figure in one multi-line Text+ and animate it as a block.
- Don't re-center a figure from `DataWindow` bounds every frame.
- Don't encode one drawing per frame in an expression and call it a rig.
- Don't cycle a few poses across a catalogue that shows more; don't invent states it does not show.
- Don't advertise a `Number`/`Text` control that does not regenerate the artwork.
