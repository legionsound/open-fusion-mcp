# Contributing

Thanks for helping make Fusion a first-class home for agent-built motion design. This guide covers how the
repository is organized, how to set up, and what a good pull request looks like.

## Ways to help

- **Report a bug** with the operation, its arguments, the error and your Resolve version
  (`fu_version_info`). Use the bug template.
- **Report a Fusion "reality"**: an API behavior that surprised you, with a minimal reproduction. These become
  entries in `skills/fusion-reference/references/fusion-realities*.md`.
- **Improve a skill** when an agent followed it and got it wrong. Say what the agent did, what it should have
  done, and how you verified the fix in rendered frames.
- **Add or fix an operation** in `connector/fusion_connector/ops/`.

## How this repository is maintained

The connector and skills are developed in the maintainer's working sources and published here by
`scripts/sync_from_dev.sh` (see [docs/maintaining.md](docs/maintaining.md)). Pull requests against
`connector/`, `skills/` and `agents/` are welcome: once accepted, the maintainer carries the change into the
working sources so the next sync keeps it. Documentation and everything outside those three folders is edited
here directly.

## Setup

```sh
cd connector
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Live work needs DaVinci Resolve Studio 21.1 with external scripting set to Local, and a scratch project (the
tests and the examples use one called `Testbed`). Keep `FUSION_MCP_PROJECT_ALLOWLIST=Testbed` set so nothing
can touch your real projects.

## Tests

Offline tests need no Resolve and run in CI:

```sh
cd connector
FUSION_MCP_SKILLS_ROOT="$PWD/../skills" .venv/bin/python -m unittest tests.test_offline tests.test_layout tests.test_catalog_tools tests.test_receipts tests.test_diagnostics
```

Tests that need the harvested Fusion data tables skip themselves until you generate the tables
([how](skills/fusion-reference/data/README.md)); run them with the tables before you change ID checks, layout or
`.setting` output.

Live checks (`tests/smoke.py`, `tests/cache_live.py`, `tests/layout_live.py`, `tests/sb3_live.py`,
`tests/receipts_live.py`) drive a real Resolve through the server. Run the ones that cover your change, in the
scratch project, and say in the pull request which ran and what they reported.

## Pull requests

- Keep each pull request to one change, and explain what it fixes or adds and how you checked it.
- New or changed operations need an offline test, a read-back of every write, and a clear error message for
  wrong arguments (see how existing operations do it).
- Skills are read by agents: short, concrete, in plain English, with verified facts marked as verified and
  guesses marked as unverified. Rendered evidence beats a successful return value.
- Do not commit harvested Blackmagic data (`*.tsv`, `*.pyi`), third-party media, fonts, client material,
  credentials or machine-specific paths. `python3 scripts/audit.py` checks the tracked files.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). By taking part you agree to it.
