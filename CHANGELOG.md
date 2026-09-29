# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-09-29

First public release.

### Added

- `use-fusion` MCP server: 11 `fu_*` tools over 179 checked operations in 36 categories, with read-back of every
  write, dry runs, batches as one undo step, and a worker process that is Resolve's only scripting caller.
- Scene builder: `scene.build` and `scene.update` turn a scene description into an editable native graph; films
  run as one culled comp on a film ladder with a single draft/final controller; 2D and true-3D layers, glass,
  dashed and tapered strokes, size-driven motion blur.
- Render-and-look tools: frame renders with inline previews, contact sheets, image comparison, motion audit,
  and Deliver jobs with explicit job IDs.
- Build-loop tools: disk caches with staleness warnings (`cache.*`), a graph tidier (`comp.layout`), and
  automatic dismissal of Resolve's render dialogs.
- Guard rails: project allowlist, read-only mode, category allowlist, default-off `eval.*`.
- Skills: `use-fusion`, `fusion-motion-design`, `fusion-reference` and `fusion-figma-transfer`.
- Example agent definitions, documentation, measured results and the explainer film.
- Offline test suite (172 tests) and CI.
