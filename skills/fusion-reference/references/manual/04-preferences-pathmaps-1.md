<!-- 04-preferences-pathmaps.md part 1 of 3; index: 04-preferences-pathmaps.md -->
# Bins, Fusion Connect, and Preferences
Scope: manual pages 326-405 (Chapters 13 "Bins", 14 "Fusion Connect", 74 "Preferences"). Use when: an agent needs Fusion Studio bin/asset-organization behavior, Avid/Fusion Connect roundtrip mechanics, or — most importantly — the exact Preferences controls that change comp defaults, automation behavior, path locations, and performance (frame format, auto-merge/auto-background, spline/keyframe defaults, GPU, memory/caching, path maps, scripting).

## Mental model
- Bins and Fusion Connect are **Fusion Studio only** (the standalone app). Neither exists in DaVinci Resolve's Fusion page. (p. 327, 345)
- Preferences has two scopes in Fusion Studio: **Global** (all comps, new and existing) and **Composition** (current comp only, overrides Global). DaVinci Resolve's Fusion page has **only Global** preferences, applied to every project. (p. 360)
- Many Preferences categories are explicitly **Fusion Studio only** and have no effect in Resolve's Fusion page: AVI, GPU, Layout, Loader, Memory, Network, Preview, QuickTime (macOS), Video Monitoring, Bins/*. Resolve routes the equivalent controls through its own Memory and GPU, Media Storage, and Project Load/Save preferences instead. (p. 361-363, 365-379, 383-384, 395)
- Path Maps are the single mechanism controlling where Fusion looks for scripts, macros, templates, fuses, LUTs, caches, and more — every one of these is a named virtual path an agent can query or override. (p. 379-382)
- Fusion always renders at **32-bit float in DaVinci Resolve**; the Frame Format color-depth menus (preview/interactive/final) only apply in Fusion Studio. (p. 369)
- Auto-merge and auto-background insertion (what happens when you drag/connect nodes) is a Preferences-level default, not a per-action choice — an agent building comps programmatically should know the user's Defaults > Auto Tools settings before assuming a Merge appears automatically. (p. 366)
- Environment variables (`FUSION_PROFILE_DIR`, `FUSION_PROFILE`, `FUSION_MasterPrefs`, `FUSION_NO_MANAGER`) control where/how preferences are loaded and can be studio-locked, overriding user changes entirely. (p. 378, 404-405)
- Variables Map preferences create named variables usable in expressions (`fu.vars.X`, `comp.vars.X`) and Saver filenames (`%{name}`), distinct from Resolve timeline metadata (`fu.vars.resolve["Name"]`). (p. 394-395)

## Bins (brief — Fusion Studio only)
Bins (File > Bins, or Command-B) are a two-pane asset browser (sidebar of folders; content panel of thumbnails/list) for clips, comps, tool settings, macros, and tool groups, similar to Resolve's Media Pool/Effects Library. Standard top-level folders: Clips, Compositions, Favorites, Projects, Reels, Settings, Templates, Tools (a mirror of the Effects Library). (p. 327-328)

- Adding content: right-click > New > … in the Contents panel, or drag files/comps/settings in from a file browser. Files are **linked, not copied** — the original stays in place. (p. 331-332)
- Saved tool settings: right-click a node in the Node Editor > Settings > Save As, then drag the resulting file into a bin. (p. 332)
- Image sequences are auto-detected as clips; hold Shift while dragging to import only a single frame instead of the whole sequence. (p. 332)
- Behavior when adding bin content to a comp differs by type: media -> new Loader (stills auto-loop); comps -> must right-click > Open (opens in a new window, never merges into the current comp); tools -> same as toolbar/Effects Library add, dragging over a connection line inserts the tool inline, double-click inserts after the Active tool; settings/macros -> drag-and-drop only, same inline-insert-on-connection-line behavior as tools. (p. 332-333)
- Studio Player: built-in timeline-based reel/dailies review tool inside the Bins window. Supports loop/ping-pong playback, per-clip CDL-style Lift/Gamma/Gain/Brightness/Contrast, versions (stacked icons show version count), notes, audio scratch track, custom XML guide overlays, and network Sync (Off/Slave/Master three-way toggle) so multiple Studio Players follow a master's playback/scrub. (p. 334-336, 343-344)
- Stamp files: low-res local proxies for network/large clips, created via right-click > Create Stamp (background process, queueable). (p. 333)
- Remote/shared bins: configured under Preferences > Bins/Servers (see Preferences section below); permissions and passwords are stored **in plain text** in the bin document itself. (p. 343, 393-394)
- Custom Guide files: XML text saved with `.guide` extension in the Guides path-map folder (macOS: `~/Library/Application Support/Blackmagic Design/Fusion/Guides/`; Windows: `%AppData%\Roaming\Blackmagic Design\Fusion\Guides`; Linux: `~/.fusion/BlackmagicDesign/Fusion/Guides`). Elements: `HLine`, `VLine` (Y1/X1 in `%` or `px`), `Rectangle` (X1/Y1/X2/Y2), with `Pattern` (hex, e.g. `FFFF`=solid, `EEEE`=dashed, `ECEC`=dash-dot, `ECCC`=dash-dot-dot, `AAAA`=dotted), `Color` (RGBA hex or `{R=,G=,B=,A=}`), and for rectangles `FillMode` (`None`/`Inside`/`Outside`) plus `FillColor`. (p. 340-342)

## Fusion Connect (brief — Fusion Studio only, Avid AVX2 plug-in)
Fusion Connect is an AVX2 plug-in for Avid Media Composer (8.x+) that exports Timeline clips as Fusion RAW image sequences and auto-builds a matching Fusion comp, letting an editor round-trip effects work between Avid and Fusion. Requires Fusion Studio 8.1+; installs `Fusion Connect.avx` and `BlackmagicFusionConnect.lua` into Avid's `\Avid\AVX2_Plug-ins`. (p. 346)

- Applied via Avid's Blackmagic Effects Palette to a clip, filler, video-track layer (up to 8 layers via the Layer Input dialog), or a transition point (auto-applies, no dialog). (p. 346-347)
- **Export Clips** button: writes all associated clips to disk as image sequences (overwriting prior exports). Without it, Fusion Connect writes source frames on the fly during scrub/playback, potentially half-resolution depending on Avid Timeline proxy settings — set Timeline Video Quality to Full Quality (green) + 10-bit to avoid subsampled images. (p. 348)
- **Edit Effect** button: first click creates the Fusion comp (Loaders + Savers + Merge for layers, or Dissolve for a transition); subsequent clicks do not overwrite it; launches Fusion and opens the comp.
- Key toggles in the Effects Editor: **Browse for Location** (choose/remember media folder, defaults to root of the Avid media drive), **Auto Render in Fusion** (renders from within Avid; slower than native Fusion render, used for batch rendering, auto-exports media first), **Red on Missing Frames** (flags unrendered/low-res frames red in the Avid Timeline monitor), **Compress Exported Frames** (smaller Fusion RAW files, slower write), **Edit Effect Also Launches Fusion** (disable when Fusion runs on a separate machine — still creates the .comp). (p. 349)
- **Versioning**: "Create New Version" checkbox copies the comp without touching the original (new render folder per version); a **Version** slider switches which version's render feeds the Avid Timeline for comparison. (p. 350)
- Images are always remapped/rendered as **16-bit float** in Fusion regardless of source Avid bit depth (8/10-bit). (p. 350)
- Manual vs Auto-Render: manual workflow does NOT require Fusion Studio on the Avid machine (can be remote) and renders faster with more control; Auto-Render requires Fusion Studio installed locally. Manual steps: Add effect -> Export Clip -> Edit Effect -> edit+save comp in Fusion -> render comp in Fusion -> render clip in Avid. Auto steps: Add effect (Auto-Render ticked) -> Edit Effect (also exports) -> edit+save comp -> render clip in Avid (renders simultaneously; missing full-res frames trigger auto re-export). (p. 350-351)
- Media/comp directory structure is auto-built: `AvidProjectName/AvidSequenceName/<ClipName>_v01.comp` plus subfolders `Avid` (source raws) and `Fusion/Render_v01`, `Render_v02`, ... (rendered raws per comp version). Transition clips default to Avid's generic "Clip_001"/"Clip_002" naming, auto-incremented on collision. (p. 353-355)
- **Advanced Project Paths**: pathing is controlled via OS environment variables, editable through the plug-in's Configure Path Defaults dialog (per-field entry on macOS; Windows also supports direct env vars). Fields/variables table: `$PROJECT`/`CONNECT_PROJECT` (override Avid project name), `$DRIVE`/`CONNECT_DRIVE` (Connect projects drive/folder), `$SEQUENCE` (Avid sequence name, no env var), `$SEQPATH`/`CONNECT_SEQUENCE_PATH` (per-sequence Connect folder), `$GROUP` (unique Connect-instance name, no env var), `$CLIP` (exported clip name, no env var), `CONNECT_CLIP_PATH` (exported-clips folder), `CONNECT_OUT_PATH` (Fusion render output folder), `CONNECT_COMP_PATH` (location/name of the .comp file). (p. 356)
- Env var scope: Windows — edit via Control Panel "env" search (user vs system scope); macOS — Terminal, user vars in `~/.bash_profile`, system vars in `/etc/profile`. **User variables always win over system variables** on a name collision. Typing directly into Fusion Connect's Path Editor sets the value without needing the variable name and doesn't require restarting Media Composer to change — but removing a variable does require exiting Media Composer and clearing it at the OS level, then restarting. (p. 357)
- Derived values usable in paths: `$DRIVE` (Avid media's drive), `$PROJECT` (Avid project name), `$SEQUENCE` (Avid sequence name). (p. 358)
- Fusion Connect's icon is a green-dot (real-time) Avid effect; render it in Avid anyway to force an MXF precompute and guarantee real-time playback. (p. 355)
- (inference) Because Fusion Connect auto-builds Loader/Merge/Dissolve/Saver trees, an agent scripting Fusion Connect comps should not change the Saver's file format or output path — the manual states this breaks the round-trip render. (p. 352)

## Preferences — categories overview
Opened via Fusion Studio > Preferences (macOS) / File > Preferences (Windows/Linux) in Fusion Studio, or Fusion > Fusion Settings on the Fusion page in DaVinci Resolve (all platforms). (p. 359-360)

| Category | Scope note |
|---|---|
| 3D View | Global |
| AVI | Fusion Studio, Windows only |
| Defaults | Global — new-tool and animation defaults |
| Flow | Global — Node Editor behavior |
| Frame Format | Global — Resolve always renders 32-bit float regardless |
| General | Global |
| GPU | Fusion Studio only (Resolve: Memory and GPU prefs) |
| Layout | Fusion Studio only (Resolve: Workspace > Layout Presets) |
| Loader | Fusion Studio only |
| Memory | Fusion Studio only (Resolve: Memory and GPU prefs) |
| Network | Fusion Studio only |
| Path Map | Global/Composition, both apps |
| Preview | Fusion Studio only (Resolve: Media Storage scratch disk) |
| QuickTime | Fusion Studio, macOS only |
| Script | Global, both apps |
| Spline Editor | Global |
| Splines | Global |
| Timeline | Global — Keyframes/Spline Editor defaults |
| Tweaks | Fusion Studio only |
| User Interface | Global |
| Variables Map | Global/Composition |
| Video Monitoring | Fusion Studio only (Resolve: Resolve prefs) |
| View | Global |
| VR Headsets | Global |
| Bins/Security, Bins/Server, Bins/Settings | Fusion Studio only |
| Import (EDL) | Global |

(p. 361-363)

