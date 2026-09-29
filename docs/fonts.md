# Fonts

No font files ship in this repository. Examples name fonts only:

| Where | Fonts named |
|---|---|
| `skills/fusion-motion-design/components/*.setting` (builder defaults) | Open Sans (Regular, Bold) |
| `connector/tests/scenes/*.json` (scene-builder examples) | Helvetica Neue (Light, Regular, Medium, Bold) |
| connector text-size constants and their comments | measured on Open Sans Bold and Helvetica Neue Bold |

- **Open Sans** is an open-source family (current releases under the SIL Open Font License) that you can install
  and share.
- **Helvetica Neue** is an Apple system font on macOS. It is fine for local tests on a Mac, but do not ship it,
  embed it or rely on it in projects you share: it is licensed with the operating system, and other machines
  may not have it. Before sharing a comp or a template, switch its Text+ tools to a font you are allowed to
  distribute (or that the recipient owns), and re-measure text sizes with `text.size_for_px`.
- The builders take a `fontFamily` parameter and scene descriptions a `font` per text style, so switching is a
  one-line change. The offline tests use estimated widths and need no installed font.
