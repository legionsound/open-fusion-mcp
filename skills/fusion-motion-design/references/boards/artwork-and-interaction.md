# Boards: artwork and interaction

Recipes are **status: unverified (not yet rendered)**.

## Board construction and missing UI

- Inventory the reference first: notes, text, arrows, highlights, annotations, cursors, labels,
  reactions, panels. Verify the static layout against that inventory (one still render) before any
  dependent motion.
- Group by meaning, named from the content: each note = paper + text + reaction badge
  (`Note_Roadmap_*`), each cursor = pointer + nameplate + name (`Cur_Maya_*`), each panel = its
  contents (`Panel_Vote_*`). Every group ends in one Transform (design-first unit contract).
- Missing icons: vector sShapes with consistent stroke (`sOutline` `Thickness`), caps, spacing and
  alignment (ui-mastery §6: recognize, never trace). An empty button or a generic stand-in symbol is
  not a finished icon.
- Header: rebuild its visible controls, separators, avatars and text from the reference; portraits
  and participant details only from supplied or authorized assets.

## Note details and reactions

- Staggered note entrances: uniform scale, restrained overshoot, clear settle (motion-design Elastic
  profile if no reference). Reaction badges merge inside the note group so they stay attached.
- Emoji reactions: separate copies that drift up and fade (`XYPath` Y rise + Merge `Blend` fade);
  keep the artwork recognizable. A counter change (Text+ step key) is separate from the bounce that
  emphasizes it.
- Paper curl, only when asked: Fusion has no 2D page-turn node. Route A: the paper alone as an
  `ImagePlane3D` with enough subdivisions, bent by `Bender3D` (`Bender` "Bend", `Amount`, `Axis`,
  `Angle`, `RangeMin`/`RangeMax`) and rendered in its own small 3D branch, as the shipped Page Curl
  transition does (transition-kit). Route B (flat look): a clipped corner (`PolylineMask` Subtract on
  the paper), a back-face triangle shape and a local shadow. Match the requested corner and scale the
  fold to each note. Check one curl at its board rotation and close-up scale before copying it; text
  and badges must stay flat and unaffected.
- Arrows, highlights and decorative marks: editable paths revealed in drawing order (`WriteLength`),
  arrowheads after shafts, hand-drawn contours preserved.

## Printed text and handwriting

- Typed text: Text+ Write On or a Follower (motion-design); explicit line breaks, alignment, spacing and
  transforms stay intact. Never rewrite `StyledText` every frame by expression when Write On works.
- A third-party preset pack (the AE brief mentioned Animation Composer) has no Fusion equivalent;
  installed Fusion Title templates or Fuses may cover it. If what the user names is not installed, say
  so and build the native equivalent only within the authorized scope.
- Handwriting: finalize wording, font and layout first. Keep the editable Text+ and add a separate
  reveal matte aligned to the rendered glyphs: centerline strokes traced in pen order (pen lifts,
  crossbars, dots, words as separate strokes), `BorderWidth` wide enough to cover each glyph without
  uncovering the neighbor, animated with staggered `WriteLength` (motion-design length-weighted
  formula). Apply as the Text+ `EffectMask` (or Merge "In"), then inspect partial strokes as well as
  the finished word. Rebuild the strokes when wording or font metrics change: traced paths do not
  reflow with the text.

## Cursors and panels

- One motion owner per cursor: pointer, nameplate and name merge first, then one `Cur_<name>_Xf`.
  Keep label offsets local; never apply the route to both the unit and a child.
- Distinct geometry, pauses, phase and travel per cursor; no synchronized copies, no jitter; featured
  note text stays readable while cursors pass.
- Looping cursors: closed `PolyPath` routes or periodic expressions with matching end position and
  velocity; `Perturb`/`Shake` do not loop (animation principles §9). Stagger entrances without
  detaching names.
- Sidebar icons reveal top to bottom with a readable stagger and the reference's acceleration; the
  panel stays put unless panel motion is requested.
- Hover highlights switch on when the simulated cursor crosses the control: drive the highlight's
  `Blend` from the cursor's position (`iif(math.abs(Cur_Maya_Xf.Center.X - 0.31) < 0.02 and
  math.abs(Cur_Maya_Xf.Center.Y - 0.72) < 0.02, 1, 0)`) or key it at the measured crossing frames.
  [verified live 2026-09-26] `and` works inside `iif`; with the cursor keyed 0.2 -> 0.4 over 20 frames
  the highlight `Blend` was 1 exactly at frames 10-12 (X 0.30-0.32).
- Voting panel: enters as one coherent group (restrained position or scale plus opacity); labels,
  spacing and counters stay readable throughout.

## Project-wide font replacement

- Resolve source family, target family and scope (one comp, a timeline, the whole project, templates)
  from the request. Keep weights and styles mapped (`Style` Bold -> Bold). Leave other families alone.
- Fusion has no replace-font command: iterate tools whose `Font` input equals the source family
  (Text+, Text 3D, sText, MultiText `Text1.Font`...) in every comp in scope, set `Font`/`Style`, and
  read back. Also check `Font`/`Style` inputs driven by expressions and `StyledTextCLS` per-character
  overrides; stored values do not describe expression-selected fonts. Back up first (no reliable
  undo through the bridge).
- Audit the scope afterwards (nested Groups, every timeline item, Edit-page title items). Separate "not
  processed" from "glyph fell back because the target font lacks it" (glyph check in 14).
- A symbol glyph the target font lacks: keep that one character in the original font with a
  `StyledTextCLS` per-character font override, or rebuild it as a small sShape; never show a tofu box
  or a duplicate glyph.
- Confirm target fonts are installed (not substituted), no source-family usage remains, and line
  wrapping, labels and badges still fit.
