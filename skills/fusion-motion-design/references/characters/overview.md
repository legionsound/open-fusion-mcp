# Characters: illustrated character motion pipeline (Fusion)

Everything needed to animate a drawn or illustrated character in Fusion, end to end: how to read the
artwork, deforming outlines while their vertices stay matched, keeping limbs and joints connected,
grain and shading that hold up in motion, stepped timing, and worked recipes for whole scenes. Its
structure follows the characters module of Higgsfield's After Effects skills (credited in
CREDITS.md). Recipes are
**status: unverified (not yet rendered)**.

Read this first; the numbered modules are add-ons, not alternative plans:

- [08 Characters](../08-characters.md): one mascot/agent with blink, gaze and head-turn parallax when
  this pipeline is more than the task needs.
- [rigging/overview](../rigging/overview.md): building or repairing the rig itself (artwork
  separation, face and body controls, Fusion's pin-warp substitutes, dimensional turns).
- [11 Character production](../11-character-production.md): motion measured before the rig, reference
  playback with free manual controls, compositing passes, two-bone IK.
- [12 Symbol characters](../12-symbol-characters.md): unrelated; glyph-built figures.

This module owns artwork, deformation, cadence and delivery; the others contribute one technique each.

## Scope and inputs

- Resolve target project/comp, approved artwork, requested actions, appearance and motion references,
  output format, timing and delivery location from the request and the project. Character names,
  colors, clothing, companions and tool selectors are runtime inputs.
- Revisions keep the approved version: user-edited polylines, keys, expressions, controls, framing and
  material settings outside the requested change stay untouched.
- Dimensions, aspect, duration, scene count and output fps come from the delivery and existing work;
  none is mandatory. For a new unspecified format choose and state one, and recompose for that canvas
  without stretching anatomy (06 aspect rule).
- Delivery fps is not animation cadence. For a requested stepped illustration look with no cadence
  given, start at 12 updates per second (every 2nd frame at 24 fps); keep an existing cadence when
  editing unless asked.
- Classify references: appearance (design, anatomy), motion (timing, performance) or editable
  animation sources. Watch real playback before trusting a video reference.
- If the designated approved source cannot be found, ask for it before attempting an exact match;
  keep inspecting the project meanwhile. Resolve other open choices from context rather than adding
  approval stops.

## Execution

1. Inspect the target comp: groups, polylines, Transform chains, effects, expressions, modifiers,
   timing (10 discover-before-mutate). Do not assume a tool or route works because an earlier session
   used it.
2. Before structural changes export the comp (`item.ExportFusionComp`) and work in a named iteration;
   leave unrelated comps and render jobs alone.
3. Record approved pose, silhouette, depth order (Merge order), contacts, moving and stationary parts,
   and the requested beats. A local motion edit keeps the existing artwork as its baseline.
4. Appearance or construction change: [artwork-and-materials](artwork-and-materials.md). New or
   revised motion: [character-performance](character-performance.md), only the relevant branches.
   Builder scripts, `.setting` delivery or SVG/vector import: [native-execution](native-execution.md).
5. Build and animate: each independently useful character or prop is a named group ending in one
   Transform (or a Merge3D branch); expose the controls the user needs on one controller without two
   owners for the same motion.
6. When progress is requested, show meaningful construction stages and rendered motion checks, and
   label an unfinished test as a test.

## Stepped cadence in one place (Fusion-native)

Route the whole character branch (every part, mask, reflection and material pass) through one
`TimeStretcher` whose `SourceTime` is an expression `floor(time/2)*2` (12 updates/s at 24 fps) with
`InterpolateBetweenFrames` 0 (Nearest). Everything upstream steps together, so masks and reflections
cannot drift out of cadence. Keep camera moves, rack focus and screen-space grain downstream of it
unless they should step too. [verified live 2026-09-26] A counter plus a mask whose `Center` moves
by expression, routed through one such TimeStretcher, showed 10, 10, 12, 12, 14 at frames 10-14 with
the masked square holding position across each pair (`t_chars_cadence.png`). Check that motion blur
upstream is disabled or intended, since stepped frames carry the blur of their source frame.

## Completion

- Check the opening pose, action extrema, in-betweens and settle at playback speed, plus each loaded
  reference's own checks. For revisions, compare untouched artwork and animation with the baseline
  (09 regression comparison).
- Project or video delivery: save/export the editable comp and render from the actual comp (Saver
  PNGs for frame proof, Deliver page for the movie). Verify the output's dimensions, duration, fps and
  visible performance with `ffprobe` and eyes; confirm an asynchronous render finished before
  reporting it.
- Deliver the requested scope: saved project/comp, local assets, a preview, and a short note naming
  groups and controls; separate scene renders, a combined sequence or a builder script when asked.
  Pick codec and container from the delivery requirement and say so if an alternative was needed.
- Keep static validation, execution, rendered inspection and the user's acceptance separate; report
  unperformed checks as unverified.
