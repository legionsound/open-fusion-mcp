# Build-loop caching: freezes, disk caches, stale checks

Measured in the efficiency lab (2026-09-27, Resolve Studio 21.1) on the benchmark ad's heaviest scene, and live-checked
through the connector's `cache.*` ops. Load this when a heavy branch slows the check loop while you work downstream
of it.

## The rule


Freeze while you're still editing upstream; pre-render to disk once a branch is locked; refresh or restore
when you edit above a cache.

- **Still editing inside a heavy branch:** freeze its static parts with constant-time TimeStretchers. They are
  cache hints, stay live, follow every upstream edit and cost nothing to keep.
- **Branch locked** (its look is approved and the remaining work is downstream: layout, camera, grade,
  grain): `cache.to_disk` renders it once over the frames where it is used. A Loader then reads it back in its
  place. The build loop runs about 20 % faster than with freezes and about 40 % faster than live, with
  identical pixels.
- **A disk copy does not see upstream edits.** The connector records what the cache was made from. After any
  edit above it, run `cache.refresh` (re-render) or `cache.restore` (the live branch back).
- **Never judge staleness by full-frame MAE.** A changed text line was MAE 0.135 with a worst tile of 22.
  Staleness comes from the upstream state, which the connector fingerprints.
- **Resolve's own Cache To Disk does nothing from scripting.** `Output:EnableDiskCache` returns True and sets
  `TOOLB_CacheToDisk`, but in Resolve 21.1 it writes 0 files and gives no speedup. Use Saver -> PNG -> Loader,
  which is what `cache.to_disk` does.

## The numbers (S5: 1,254 tools; window branch 829 tools at 3640x2440)

| variant | clean A-B-B-A loop (comp.Render timed) | 7-step loop through render.frame | memory after | follows upstream edits |
|---|---|---|---|---|
| live | 12.3 / 11.2 s | 39.2 s | 8.9 GB | yes |
| freeze | 8.7 / 8.3 s (-27 %) | 32.6 s | 6.9 GB | yes |
| disk (Saver -> PNG -> Loader) | 6.9 / 6.7 s (-42 % vs live, -20 % vs freeze) | 20.9 s | 7.2 GB | **no: stale** |

- **Where the savings land:** on frames the loop has not rendered yet. Downstream tweaks of an
  already-rendered frame cost the same in all three (about 0.9 s).
- **Pixels:** bit-identical (MAE 0.0).
- **Write cost:** 0.63 s per frame. 31 frames of the 3640x2440 branch took 19.5 s and 11 MB of PNG.
- **Break-even against freezes:** about 2 renders per cached frame.
- **Final Deliver:** only 6 to 11 % faster, and the disk copy holds about 1.8 GB more (the Loader frames at
  3640x2440). The disk copy is a build-loop tool; for the final render it is optional. `cache.restore`
  before Deliver is fine.
- **Format:** PNG RGBA 8-bit was exact for a UI branch. EXR half is suggested for values outside 0-1 or soft
  gradients that would band. That is untested, and `cache.to_disk` writes PNG only today.

## Dialog traps (each one blocks scripting until someone clicks)

- A raw-script `comp.AddTool("Loader")` without `comp:Lock()` opens a modal file browser. The connector adds
  its Loader Lock-wrapped (`tool.add` path) and sets `Clip` in the same call.
- Pasting a Loader opens the same browser. The connector's paste (`setting.paste`, `scene.build`, `comp.layout`)
  runs under `comp:Lock()` / `comp:Unlock()` since 2026-09-27 (live: a pasted Loader, next call answered in 0.1 s).
  In a raw script, wrap `comp:Paste` the same way.
- `EnableDiskCache` pointed at a missing folder raises a modal "Could not save Disk Cache". Create folders
  first; `cache.to_disk` makes its folder before anything asks Fusion to write there.
- Since that Disk Cache dialog incident, Resolve 21.1 no longer shows "Render completed!" after `comp.Render`.
  The connector used to wait 4 s for it on every render. It now stops as soon as the frame's file exists and
  Resolve answers, and it still dismisses a modal when one does show.
- `render.*` now keeps one Saver per comp (`FC_RenderSaver`, bypassed with no input between renders) instead
  of adding and deleting a Saver per call. Leave it in the comp; `render.cancel`, the next render and
  `deliver.start` re-park it if a render was interrupted (a live Saver would write every Deliver frame).

## Op usage

Cache a locked branch. Omit `start`/`end` and the range becomes the union of its consumers' enabled regions,
else the comp render range:

```json
{"operation": "cache.to_disk", "args": {"comp": {"timeline": "FILM", "track": 1, "item": 0}, "tool": "S5_Window_Shd", "start": 60, "end": 90}, "timeoutMs": 600000}
```

- **Files:** `FUSION_MCP_CACHE_DIR` (default `~/Movies/FusionCache`) + `<project>/<timeline>/<clip>/<tool>/<tool>_r1_####.png`.
- **Loader:** `<tool>_Cache` reads that sequence at comp frames `start..end`, and every consumer of the tool
  is rewired to it.
- **Live branch:** stays in the comp, intact but unconsumed, so it does not cook.
- **Manifest:** comp CustomData `fc_cache`, holding the range, revision, rewired inputs and the upstream
  fingerprint.
- **Out-of-range warning:** a consumer that can request frames outside the range is named in `warnings`,
  because the Loader has no image there.

Check what is cached and what is stale:

```json
{"operation": "cache.status", "args": {}}
```

- **Reply:** per cache: range, frames on disk, bytes, created or refreshed, `stale`, and `changed` (the
  upstream tools whose settings, keys, expressions or wiring differ). Node moves and other UI state do not
  count.
- **Also warned by:** `render.frame/range/contact_sheet/compare` (under `warnings`) and `deliver.start`, which
  refuses without `confirm: true`.

Re-render stale caches (a new file revision; the old one is deleted), or one cache or all:

```json
{"operation": "cache.refresh", "args": {}}
{"operation": "cache.refresh", "args": {"tool": "S5_Window_Shd"}}
```

Put the live branch back (consumers of the Loader rewired to the tool, Loader deleted), optionally deleting
the files:

```json
{"operation": "cache.restore", "args": {"tool": "S5_Window_Shd", "clear": true}}
```

Delete cache files, only ever inside the cache root. `tool` is a restored cache's folder (`restore: true` for
an active one); `all: true` deletes every unused cache folder of this comp:

```json
{"operation": "cache.clear", "args": {"all": true}}
```

## Workflow in a film build

1. Build and edit with freezes (the scene builder adds them).
2. When a heavy branch's look is approved, run `cache.to_disk` on it over its scene's frames (the default range
   does this when its consumers are culled).
3. Iterate downstream with `render.frame` / `render.contact_sheet` (draft or final).
4. Edited something above a cache? The next render's `warnings` say STALE. Run `cache.refresh`, or
   `cache.restore` if you will keep editing up there.
5. Before the final Deliver: `cache.status`. Stale caches block `deliver.start`. Fresh ones are fine to keep
   (6-11 % faster, +1.8 GB), or restore them.
6. A cache made while the scene was in draft is stale once you flip `quality: final`. The scene's CTRL is part
   of the fingerprint, so refresh after the flip.

## Live check (2026-09-27, Resolve Studio 21.1, Testbed, 18 of 18 pass)

`tests/cache_live.py` in the connector: cache.to_disk (30 frames, 7.7 s) read back pixel-identical at the range ends
and middle (MAE <= 0.003); an upstream text edit made the cache STALE in `cache.status`, in `render.frame` warnings and
in the `deliver.start` preflight (refused); `cache.refresh` wrote revision 2; the parked render Saver wrote nothing
during a Deliver; `cache.restore` matched the refreshed pixels (MAE 0.0015); `cache.clear` stayed inside the cache
root. The first live run caught a real bug: `comp.CopySettings(tool)` over the Python bridge returns `{Tools: None}`,
so the off-page fingerprint never changed. It now reads `tool.SaveSettings(path)`.
