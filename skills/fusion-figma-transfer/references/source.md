# Source capture

## Complete source

- Read the whole selected subtree without modifying, detaching or flattening it. Capture node IDs,
  types, local size, `relativeTransform`/absolute transform, child order, `visible`, fills and strokes
  (paint stacks with blend modes and opacities), `strokeWeight`/`strokeAlign`, corner radii (including
  per-corner), vector geometry, text (`characters`, style, styled ranges, `lineHeight`,
  `letterSpacing`, alignment, auto-resize), masks (`isMask`), `clipsContent`, effects (drop/inner
  shadow, layer/background blur) and image references. Include hidden nodes and boolean operands for
  provenance even when they produce no tool. Keep text and line breaks exactly before applying range
  styles.
- Prefer resolved geometry (`fillGeometry`/`strokeGeometry` SVG path data from the REST API with
  `geometry=paths`) for booleans and outlined strokes; keep vector networks where native reconstruction
  needs them. An exported image of a frame cannot replace its geometry. Separately fetch a PNG render of
  the exact root node at 1x (or the comparison scale) for final verification.
- Resolve read errors and missing geometry before construction. Respect the connection's payload limits
  and use its pagination or full-file retrieval; never rebuild a "complete" capture from truncated
  responses. Keep one source revision (file `version`/`lastModified`) across reads and recapture if it
  changes mid-extraction.

## Original media

- Resolve original bytes for every image paint used by visible content (fills, strokes, text fills,
  patterns) through the image-fill endpoint, download, and verify non-empty data, pixel dimensions and
  content identity (hash). Store in a durable per-transfer folder the Resolve machine can read
  (`<project>/media/figma/<file>/<imageRef>.png`); a temporary URL or a path on another host is not
  footage. Import stills through a `Loader` (`Clip` path) or into the Media Pool for a `MediaIn`.
- A reference render may support review but never substitutes for an original photograph.

## Transfer plan and identity

- Before mutation classify each node: native content, image media, retained container (Group), structural
  node (flattened), boolean operand, intentional hidden omission, or unsupported feature. Match features to
  actual Fusion constructions ([native-layers](native-layers.md)); resolve material unsupported cases
  before building affected content.
- Record file key, root and node IDs, representation, a fingerprint per node (hash of its captured
  JSON), child order, media dependencies and limitations. After pasting, bind them to the real tool names
  (paste can rename on collision, realities §9). Tool names derive from node IDs so the map survives:
  `12:345` -> `FG_n12_345_<Label>` (alnum and underscore only). Keep source state apart from verification
  state. Store the map in a Markdown sidecar next to the exported comp (and optionally per tool with
  `tool.SetData("figma.id", "12:345")`; [verified live 2026-09-26] it is written into the exported comp
  as tool `CustomData = { figma = { id = "12:345" } }` (a dotted key becomes a nested table) and
  `GetData("figma.id")` reads it back; a full project save and reload was not run). Save the reference render
  and media as workflow outputs, outside the skill.
