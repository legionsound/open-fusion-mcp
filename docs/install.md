# Install

## Requirements

- macOS (tested on Apple Silicon). The server is plain Python, but the render-dialog helper uses AppleScript.
- DaVinci Resolve Studio 21.1 (external scripting is a Studio feature), with
  Preferences > System > General > External scripting using = Local.
- Python 3.12 and an MCP client (tested with Claude Code).

## 1. Python environment

```sh
cd connector
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt      # mcp (1.x), pillow, numpy
```

`bin/use-fusion-mcp` and `bin/fusion-connector` run `connector/.venv/bin/python`, so registration needs only
one absolute path.

## 2. Skills

The server serves every `fusion-*` skill plus `use-fusion` from its skills root, in this order:

1. `FUSION_MCP_SKILLS_ROOT` if set,
2. `~/.agents/skills` if it holds `fusion-reference`,
3. `skills/` beside `connector/` (this repository).

To use the skills from your agent directly as well, copy or symlink `skills/*` into your agent's skills folder
(Claude Code: `~/.claude/skills`). Files are hash-checked: after editing a skill run
`connector/bin/fusion-connector skills-manifest` (or restart the server).

## 3. Fusion data tables

`skills/fusion-reference/data/` needs `fusion-21.1-registry.tsv`, `fusion-21.1-inputs.tsv` and
`fusion_api-21.1.pyi`, generated from your own Resolve install. How: that folder's
[README](../skills/fusion-reference/data/README.md). Without them the server starts, but ID checks, pasted
defaults and graph layout are degraded, and the 19 offline tests that read the tables are skipped.

## 4. Check and register

```sh
connector/bin/fusion-connector doctor            # Python, SDK, Resolve reachable, Studio, UI, skills, tables, manifest
connector/bin/fusion-connector doctor --offline  # same without touching Resolve
connector/bin/fusion-connector config            # prints the registration command and a generic JSON block
```

Claude Code example (restart the session afterwards):

```sh
claude mcp add use-fusion --scope user -e FUSION_MCP_PROJECT_ALLOWLIST=Testbed -- /abs/path/to/connector/bin/use-fusion-mcp
```

`FUSION_MCP_PROJECT_ALLOWLIST` makes every mutating operation refuse projects outside the list; reads still
work everywhere. Use a scratch project while you learn the tools.

## 5. Permissions

Every `comp.Render` in Resolve 21.1 opens a "Render completed!" dialog that blocks scripting until someone
clicks OK. The server clicks OK on that dialog (and on "Render did not complete") through System Events, which
needs Accessibility permission for the app that runs the server (your MCP client). Turn it off with
`FUSION_MCP_AUTO_DISMISS_RENDER_MODAL=0` and close the dialogs yourself.

## 6. Policy switches

| Variable | Effect |
|---|---|
| `FUSION_MCP_READONLY=1` | read operations only |
| `FUSION_MCP_ALLOW_CATEGORIES=comp,tool,...` | operation-category allowlist |
| `FUSION_MCP_PROJECT_ALLOWLIST=Testbed,...` | mutating operations refuse other projects |
| `FUSION_MCP_ENABLE_EVAL=1` | allow `eval.python` / `eval.lua` (off by default) |
| `FUSION_MCP_ALLOW_TEMPLATE_INSTALL=1` | allow `template.install` into Resolve's Templates folders |
| `FUSION_MCP_AUTO_DISMISS_RENDER_MODAL=0` | stop clicking OK on Resolve's render dialogs |
| `FUSION_MCP_OUT_DIR` | renders and exports (default `connector/out`) |
| `FUSION_MCP_CACHE_DIR` | disk caches for `cache.*` (default `~/Movies/FusionCache`); `cache.clear` deletes only inside it |
| `FUSION_MCP_MAX_RESPONSE_CHARS` | response budget (default 40000); bigger replies spill to `out/responses/` |

## 7. First session

Call `fu_version_info` (expects `resolve.studio: true`), then `fu_get_skill {name: "use-fusion"}` and follow its
working loop. Fonts: see [fonts.md](fonts.md).
