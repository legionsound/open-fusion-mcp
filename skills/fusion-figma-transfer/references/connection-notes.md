# Connection behavior

- Read the selected Figma connection's current schemas and guidance before mutation: operation names,
  node-read depth, geometry flags (`geometry=paths`), image-fill retrieval, rate and payload limits
  belong to that connection. A connection must expose usable source data before the transfer is
  executable, and the Resolve side must expose comp access plus the paste route.
- The Fusion build is additive by construction: one `.setting` per frame pasted into the current
  Fusion-page comp (realities §1, §9). Confirm the paste created every planned tool (`FindTool` for each
  name; `comp.Execute` is deferred) and that nothing pre-existing was renamed or rewired.
- Read back Text+ `StyledText`, `Font`, `Style`, `Size`, `CharacterSpacing`, `LineSpacing` and the
  rendered bounds; paste can normalize values. Check gradient `Start`/`End` against the rendered
  element, not only the numbers. Inner shadows, group blur and background blur must use the intended
  compositing scope (branch-local vs over the backdrop), not a similarly named tool.
- Only handle behavior relevant to the chosen connection and the source features in play. An SVG or PDF
  export can be useful transport (a Loader still, or path data), but it does not make text or effects
  native. Re-render a preview after the comp settles only when stale output is observed; unresolved
  differences stay verification failures.
