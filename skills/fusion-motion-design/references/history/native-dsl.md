# Native authoring model and construction outlines

> Historical (superseded 2026-09-26 by the module set in ../ and the fusion-reference skill). Kept for provenance.

The filename is retained for compatibility. This is a planning vocabulary,
not an executable DSL, compiler or HTML translation layer.

## Component record

For each unit record its stable name, purpose, contents, bounds/anchor, style,
motion beats, controls and intended tool chain. Keep image coordinates,
normalized tool coordinates, 3D units and FlowView layout separate. Probe actual
tool inputs before assigning values.

Construct complete semantic units, then animate their explicit transform
chains. A named subgraph is sufficient when its internals should remain visible.
Group/macro packaging is optional and requires its own control/persistence test.
Preserve intentional manual changes when iterating.

## Construction outlines, not blanket tested recipes

| Unit | Construction outline | Recorded qualification |
| --- | --- | --- |
| Plate and label | Background + RectangleMask + TextPlus + Merge | Basic rendered/editable pattern qualified; arbitrary border/gradient styles are not |
| Photo card | Loader, native resize/crop/mask, separate chrome/text | Still loading, resize/mask/compositing qualified; re-check fit and aspect for each asset |
| Shared 2D motion | Custom scalar controls, splines, Transform expressions | X/Y/scale/angle pattern qualified; published Edit-page interface is not |
| Dimensional display | Imported geometry + live ImagePlane3D screen + camera/lights/renderer | Specific classic 3D/OBJ construction qualified |
| Path draw-on | Native shape/polyline with discovered progress input | Construction outline only |
| Scrolling viewport | Move content branch beneath a stationary viewport mask/chrome | Construction outline only; long-content replacement/scroll tests remain open |
| Kinetic type | Separate TextPlus words/phrases, or discovered follower/write-on | Unit transforms qualified; follower/per-character behavior remains open |
| Gradients/glass/particles | Native tools selected for the actual visual need | Qualify controls, compositing and render behavior before scaling up |
| Reusable macro | Group/UserControls and exported .setting/template | Publishing and import round trip remain open |

Use [tested native recipes](../tested-native-recipes.md) for exact observed API
mechanics. An outline proposes a graph; it does not prove the graph renders.

## Build discipline

1. Qualify the hardest representative unit for the requested brief.
2. Set explicit connections and meaningful names; avoid accidental auto-merges.
3. Verify scalar inputs, key sets and relevant bounds.
4. Render the unit in context, including alpha and a non-settled frame.
5. Expand the qualified pattern; batch deterministic work by semantic unit.
6. Check a real content/control edit and restore defaults.

Keep text and graphic chrome native when editability is required. Preserve
external media and provenance. Imported OGraf/Lottie remains an input/source
asset, not a promise of native editable internal shapes.

Choose modules from the brief. Do not require a phone overlay, 3D device or
macro before delivering an unrelated title or diagram.
