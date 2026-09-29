# 15 Dependencies, cleanup and handover packages

Load for missing or unlicensed effects (OFX, Fuses, Resolve FX), project cleanup, collecting a
project with its media, and handover packages, usually around language versions (13). Port of
Higgsfield `ae-clean-rig` module 15 (local connector, 2026-09-26) into Resolve terms: AE's Collect
Files maps to a Resolve project archive plus a manifest for what the archive does not carry. The
dependency scan was run live on 2026-09-26 (corrected below); archive, restore and Remove Unused Clips
are **not verified** (they need a second project or a Media Pool purge, outside the Testbed-only test
rule); confirm Resolve API names with `get_scripting_api` first.

## Dependency audit

Keep apart: a missing tool (plugin not installed), an installed but unlicensed one (renders with a
watermark), a tool the user disabled (pass-through), an expression error, and output hidden by other
tools. An inventory of installed plugins proves none of visibility, activation or licensing.

| What | How to read it in Fusion |
|---|---|
| Tool identity | `tool.GetAttrs()["TOOLS_RegID"]`: `ofx.<vendor>...` = OFX (Resolve FX `ofx.com.blackmagicdesign.resolvefx.*` or third party), `Fuse.<name>` = Fuse script, otherwise native; the live registry (`fusion-reference/data/fusion-21.1-registry.tsv`) lists what was installed on the harvest machine, including 108 OFX and some Fuses (Kartaverse), so classify by prefix first and use the registry only for presence |
| Missing plugin | RegID not in the live registry and not in the Fuses folder (`~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Fuses/`); the comp loads a placeholder and renders nothing or black for that branch |
| Disabled by the user | `tool.GetAttrs()["TOOLB_PassThrough"]` True (Ctrl-P in the node editor) |
| Visible at all | follow the tool to `MediaOut1`: Merge `Blend`, masks, occluding Merges above it, and the frames where the item is on the timeline |
| When to look | map timeline frames to comp frames (02), through item trims, `TimeSpeed`/`TimeStretcher` and nested Fusion clips, before picking diagnostic frames |

- Identify vendor and package from the RegID and the vendor's official documentation, not from how
  the effect looks, and never reuse another project's licensing status.
- Purchase, installation, activation and enabling are four separate actions; approval to analyze
  authorizes none of them. Check the application and the vendor's license manager separately; an
  empty license list is no reason to reinstall software or switch accounts. Do not reopen a deferred
  licensing decision without new evidence.
- Restoring disabled effects: identify the specific instances from reliable history or current
  evidence (tool names, the comp export from before the change); ask if they cannot be determined.
  Never clear pass-through on every tool.
- Never disable effects or hide watermarks to get a clean-looking render without authorization. A
  render affected by an unresolved dependency is a **DRAFT**: name it so and list the dependency.
- Studio-only Resolve FX and some Fusion features watermark or refuse to render in the free edition:
  confirm the edition (`resolve.GetProductName()`/`GetVersionString()`) on the machine that renders.

```python
# dependency scan for one comp (read-only) [verified live 2026-09-26: flagged an ofx.* Resolve FX,
# Fuse.Duplicate and a pass-through Blur correctly]
import os
reg = {l.split('\t')[0] for l in open(REGISTRY_TSV) if l.strip() and not l.startswith('#')}
# the registry TSV omits spline classes; without this every keyed input's spline reads UNKNOWN
reg |= {'BezierSpline', 'BSpline', 'CubicSpline', 'NaturalCubicSpline', 'NURBSpline'}
fuses = {os.path.splitext(f)[0] for f in os.listdir(FUSE_DIR)} if os.path.isdir(FUSE_DIR) else set()
for t in comp.GetToolList(False).values():
    a = t.GetAttrs(); rid = a['TOOLS_RegID']
    kind = 'ofx' if rid.startswith('ofx.') else 'fuse' if rid.startswith('Fuse.') else 'native' if rid in reg else 'UNKNOWN'
    if kind != 'native' or a.get('TOOLB_PassThrough'):
        print(a['TOOLS_Name'], rid, kind, 'PASSTHROUGH' if a.get('TOOLB_PassThrough') else '')
```

## Cleanup on copies only

- Identify the current language projects and final timelines. Check external drives, offline media
  and free space. Preserve unsaved work; clean only a new copy (a re-imported `.drp` under a new name,
  or a duplicated project).
- Trace every source: Media Pool clips used on timelines, MediaIn tools inside comps (`MediaID`,
  `ClipName`), Loader `Clip` paths (EXR/PNG sequences, often outside the Media Pool), proxies,
  optimized media, LUT files, `KD_TextFromFile` and other externally loaded data, expressions that
  name tools in other comps. Keep uncertain dependencies and say why; invisible is not unused.
- Media Pool "Remove Unused Clips" judges usage from timelines. Media used only inside Fusion comps
  (MediaIn) or only by Loaders may be treated as unused or ignored: record those items first, and
  check for offline media after the removal (behavior unverified: not run, it would purge the
  shared test project's Media Pool).
- Remove only proven-unused items and empty bins from the copy. Do not merge look-alike clips without
  checking their interpretation (color space tags, frame rate) and proxies. Record what was excluded
  and where it can be recovered. Keep original media, the user's archives, older projects and global
  caches.

## Collection and destination

- Resolve's collector is the project archive: File > Export Project Archive, or
  `projectManager.ArchiveProject(name, path, isArchiveSrcMedia, isArchiveRenderCache,
  isArchiveProxyMedia)` (Resolve API). It gathers the project with its Media Pool media (and render
  cache/proxies when asked). File > Media Management copies or transcodes used media when a folder
  tree is wanted instead of a `.dra`.
- Not reliably collected, so copy them with a manifest: files referenced only by Fusion Loaders,
  Fuses, OFX plugins, fonts, LUTs outside the project, Edit-page templates (`.setting`/`.drfx`) and
  anything read by path from an expression or `KD_TextFromFile`.
- Create a clearly named parent folder with independent per-language folders. Choose the destination
  folder separately from the file name and verify the created path. After moving a package, restore
  or open the collected project from its final location and save it there; later edits to the
  original do not update the collected copy.

## Package verification

- Restore the archive (or open the collected project) under a new name: no offline media in the
  Media Pool, every Loader path resolves, no new expression errors (read expression inputs at two
  frames), fonts present.
- Compare timelines, comp structure, keys, text and timing against the baseline (13 comp diff).
- Hash files: `shasum -a 256` on source and copy, hashing shared sources once. Media Pool clip
  counts need not equal unique file counts.
- If asked, copy existing renders into a `Renders` folder, labelled as existing renders; never imply
  they reflect later edits without checking.
- An archive does not install fonts, plugins or licenses on another machine. Include exact
  dependency information (RegIDs, versions, font names). Bundle fonts only when needed and the
  license permits; never redistribute paid or system fonts by default. Mark incomplete languages as
  pending, and report cleanup, collection, reopening and verification as separate completion states.
