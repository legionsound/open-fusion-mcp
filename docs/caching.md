# Caching in the build loop

Rule: freeze while you still edit upstream; pre-render to disk once a branch is locked; refresh or restore
after any edit above a cache. Details live in `fusion-motion-design` `references/build-loop-caching.md` and the
`use-fusion` skill (section "Disk caches for the build loop").

## Operations

| op | what it does |
|---|---|
| `cache.to_disk` | renders a tool's branch once (Saver to PNG), adds a Loader `<tool>_Cache` and rewires every consumer to it; the live branch stays in the comp, unconsumed |
| `cache.status` | per cache: range, frames, bytes, `stale`, and which upstream tools changed |
| `cache.refresh` | re-renders stale caches (or one, or all) as a new file revision |
| `cache.restore` | puts the live branch back and deletes the Loader (optionally the files) |
| `cache.clear` | deletes cache files, only ever inside `FUSION_MCP_CACHE_DIR` |

Renders and `deliver.start` warn about stale caches. Staleness comes from a fingerprint of the upstream settings,
keys, expressions and wiring, never from pixel differences (a changed text line measured MAE 0.135).

## Measured (heaviest benchmark scene: 1,254 tools, cached branch 829 tools at 3640x2440)

| variant | build-loop renders | memory after | follows upstream edits |
|---|---|---|---|
| live | 12.3 / 11.2 s | 8.9 GB | yes |
| freeze (constant-time TimeStretchers) | 8.7 / 8.3 s (-27 %) | 6.9 GB | yes |
| disk cache | 6.9 / 6.7 s (-42 % vs live) | 7.2 GB | no, until refreshed |

Pixels were identical (MAE 0.0). Writing the cache costs about 0.63 s a frame; it pays off after about two renders
per cached frame. Final Deliver gains only 6 to 11 %, so caches are a build-loop tool.

Resolve's own Cache To Disk does nothing when driven from scripting in 21.1 (it reports success and writes no
files), which is why the connector uses Saver, PNG and Loader.
