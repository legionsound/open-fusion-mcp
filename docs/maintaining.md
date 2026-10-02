# Maintaining this repository

The connector and the skills are developed elsewhere and change often. This repository is rebuilt from those
sources by a script, never edited by hand inside `connector/`, `skills/` or `agents/`.

## Sync

```sh
scripts/sync_from_dev.sh             # copy, redact, patch, scan, mirror, then run the offline tests
scripts/sync_from_dev.sh --no-tests  # the same without tests
```

It needs two local, git-ignored files:

- `scripts/sync.local.env`: where the sources are and which Python runs the tests
  (template: `scripts/sync.env.example`).
- `scripts/sync/private.json`: redaction rules and extra scan terms for people, clients and local folders
  (template: `scripts/sync/private.example.json`). The sync refuses to run without it, so private terms never
  have to live in a tracked file.

Steps (`scripts/sync/sync.py`):

1. **Copy** the explicit include list into a fresh staging folder. Everything else stays out, including
   `.venv/`, `out/`, caches, logs, third-party checkouts, another vendor's operation registry, development logs
   with local paths, live-test results and the private benchmark fixture.
2. **Redact** shipped text with the rules in `private.json`.
3. **Patch** with `scripts/sync/patches/<root>/*.patch` (written against the redacted text). A patch the source
   already contains is skipped; one that no longer applies stops the sync.
4. **Override** files from `scripts/sync/overrides/` (repo-owned rewrites and additions). `overrides.json` records
   the source hash each override was written against, and the sync prints `REVIEW` when the source moved on.
5. **Scan** the staging folder with `scripts/audit.py`. Any finding stops the sync before the repository is
   touched.
6. **Mirror** staging into `connector/`, `skills/` and `agents/` (adds, updates and deletions), keeping local-only
   files: the harvested data tables, `connector/.venv`, `connector/out`, `skills-manifest.json`.
7. **Test**: the offline suite runs inside `connector/` against this repository's `skills/`.

A second run with unchanged sources reports `0 added, 0 updated, 0 removed`. The script never commits or pushes.

## Audit

```sh
python3 scripts/audit.py                                         # scan tracked files
python3 scripts/audit.py --manual fusion.txt --higgsfield dir1,dir2  # plus text-overlap tables
```

The overlap tables compare `skills/` with a plain-text export of the Fusion manual and with the Higgsfield After
Effects skills (neither is included). Keep verdicts in the maintainer's private notes, not in this repository.

Publication bar used for 0.1: 0 scan findings; no near-verbatim window against either source except short
functional text (paths, shortcut lists, formulas); exact shared runs under 16 words. Skills that do not meet
it stay out of `SKILLS` in `scripts/sync/sync.py` (currently `fusion-cleanup` and `fusion-matte-painting`),
and `scripts/sync/patches/skills/` removes the router lines that point at them.

## Releases

1. On a release branch, update `CHANGELOG.md` and the version in `connector/fusion_connector/config.py`, run the
   sync with tests and the audit, and commit.
2. Push the branch to the public repository and open a pull request. CI runs the offline tests on Linux and macOS
   and the privacy scan; `main` accepts the pull request only when all three pass.
3. Run the live checks that cover the change in a scratch project (`Testbed`) and note the results in the pull
   request.
4. Merge, tag the merge commit (`git tag -a v0.2.0 -m "open-fusion-mcp 0.2.0"`) and publish a GitHub release
   from the changelog entry.

The public history started from a fresh single commit (0.1.0), so nothing from the private development history
is carried over. Never push the private development branch to the public remote.
