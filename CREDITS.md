# Credits

open-fusion-mcp is MIT-licensed, Copyright (c) 2026 Legion Media LLC (see [LICENSE](LICENSE)). It builds on the
work and ideas below. Each item was checked before publication: text-overlap scans against the sources named
here, a line-by-line code comparison with the prior-art servers, and a secrets and personal-data scan
(`scripts/audit.py`).

## Inspiration: Higgsfield's After Effects connector and skills

This project is the Fusion counterpart of Higgsfield's local After Effects connector (`use-after-effects`) and
its After Effects skill set (`ae-clean-rig`, `ae-animation-principles`, `ae-ui-mastery`, `ae-design-first`,
`ae-depth-space`, `ae-liquid-glass`, `ae-transition-kit`, `ae-build-orchestration`, `ae-cleanup`,
`ae-figma-transfer`, `ae-matte-painting`).

- The connector mirrors that connector's shape: eleven of the `fu_*` tools correspond to its `ae_*` tools, and
  `connector/PARITY.md` maps each of its operations to a Fusion operation. `scripts/parity.py` reads that
  connector's operation registry, which is not included here.
- The builders in `skills/fusion-motion-design/scripts/fusion_build.py` keep the parameter names and enums of
  Higgsfield's After Effects builders, so the same brief drives either host.
- The Fusion skills follow the structure and much of the craft doctrine of the Higgsfield skills, written in our
  own words for Fusion's nodes, API and measured behavior. Passages that had stayed close to the original
  wording were rewritten before publication. The Fusion counterparts of `ae-cleanup` and `ae-matte-painting`
  are not part of this release while they are rewritten.

No code or text in this repository is licensed from Higgsfield. Higgsfield is a trademark of its owner, and this
project is not affiliated with or endorsed by Higgsfield.

## Prior art: open-source DaVinci Resolve MCP servers

These projects were studied before the connector was written. No code was copied from them (a line-by-line
comparison found no shared code beyond one-line Python idioms).

- **lordhoell/davinci-resolve-mcp** (MIT). Its list of 104 Fusion functions is the checklist for the second
  comparison table in `connector/PARITY.md`, and its code confirmed several API calls (for example the font
  manager, `GetDoD`, `AdjustKeyFrames` and flow-view positioning). Its license notice:

  ```
  MIT License

  Copyright (c) 2026 DaVinci Resolve MCP Contributors

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.
  ```

- **samuelgursky/davinci-resolve-mcp** (MIT, Copyright (c) 2025-2026 DaVinci Resolve MCP Contributors and
  Bradford Operations LLC). Its guarded Fusion kernel suggested three things the connector does its own way:
  dry runs (`fu_do dryRun`), read-back after every input change, and checked connections.
- **CiprianSpiridon/davinci-resolve-mcp** (MIT, Copyright (c) 2026 davinci-resolve-mcp contributors). Its
  offline `.comp` parser is the counterpart of `setting.validate`, which uses this project's own Lua-table parser
  (`fusion_connector/luatable.py`).
- **apvlv/davinci-resolve-mcp** (MIT, Copyright (c) 2026 Sage Choi). Studied for node-chain helpers.

## Blackmagic Design

DaVinci Resolve, DaVinci Resolve Studio and Fusion are trademarks of Blackmagic Design Pty. Ltd. This project is
not affiliated with or endorsed by Blackmagic Design.

- `skills/fusion-reference/references/manual/` distills the Fusion 21.1 Reference Manual into agent notes in
  our own words, with page references. Short functional facts are kept as printed where rewording would make
  them wrong: install paths, keyboard shortcuts, Merge operator formulas, colorimetry numbers and a six-line
  example script.
- The harvested tool and input tables and the API stubs describe Blackmagic's software and are not shipped; each
  user generates them from their own install (`skills/fusion-reference/data/README.md`).
- The connector talks to Resolve through Blackmagic's scripting module (`DaVinciResolveScript`), which ships
  with Resolve and is not included here.

## The explainer film

`docs/media/open-fusion-mcp-explainer.mp4` was built in Fusion by agents using this toolkit and directed and
mixed by Legion Media. Music: "Ender" by Lucas Pluim, licensed through Artlist for use in this film. Some sound
effects were generated with [MMAudio](https://github.com/hkchengrex/MMAudio) (Cheng et al.), whose model weights
are licensed CC BY-NC 4.0; open-fusion-mcp is a free, non-commercial project. The film is shared with this
repository for viewing; the MIT license covers the code and documentation, not the music, which must not be
extracted or reused.

## Python dependencies (installed by pip, not vendored)

- `mcp`, the Model Context Protocol Python SDK (MIT)
- `pillow` (MIT-CMU)
- `numpy` (BSD-3-Clause and compatible licenses)

## Other names

The skills mention third-party tools and services by name (for example Figma, Higgsfield generation models,
HyperFrames, Remotion, OGraf, Lottie, USD). They are trademarks of their owners and are named for
interoperability only. Fonts are named, never shipped; see [docs/fonts.md](docs/fonts.md).
