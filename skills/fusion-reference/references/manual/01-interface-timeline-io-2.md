<!-- 01-interface-timeline-io.md part 2 of 2; index: 01-interface-timeline-io.md -->
## 5. I/O node reference

The Select Tool abbreviations `[LD]`, `[MI]`, `[MO]`, `[SV]` "can be used in the Select Tool dialog when searching for tools and in scripting references" (p. 1175).

### MediaIn (MI) - Resolve only
The clip entry point for every Fusion page comp. Use for timeline clips and any Media Pool / file-system footage.
- Inputs: Effect Mask (blue) only. Connecting a mask creates/limits alpha; mask applied after the tool processes (pp. 73, 1185).
- Image tab (timeline clip, reduced set because timing is set by the edit) (p. 74):
  - Clip Name.
  - Process Mode - Full Frames or field modes (see Loader Import tab list) (p. 1186).
  - Media Source - **Timeline** (default, linked to the edit), **Background** (pulls the composited result of all lower video tracks), **Media Pool** (links directly to the Media Pool clip, bypassing the timeline) (p. 74).
  - Layer - PSD/multilayer layer; for Fusion clips built from several tracks, the layer index (p. 74).
- Extra controls when the MediaIn came from the Media Pool / OS / Import PSD (pp. 76-77, 1186-1187):
  - Global In/Out - where the clip sits in comp time; Media Pool clips land at frame 0. Drag the middle of the range to slide without changing length. Shrinking the range below available frames auto-trims (adjusts the Trim/Clip Time range); enlarging beyond available frames auto-extends via Hold First/Last Frame (held frames colored purple per p. 76, green per p. 1186). No image outside this range (p. 1186).
  - Trim In/Out - offsets into the source: Trim In 5 starts on the 5th frame (skips 4); Trim Out 95 stops after the 95th.
  - Hold First Frame / Hold Last Frame - freeze for N frames; held frames are included in a loop.
  - Reverse - plays last frame first.
  - Loop - loops to the end of the project, including holds/trims.
- Source Color Space (Color Space Type): Auto / Space. p. 74 says Auto passes existing metadata; p. 1187 says Auto uses the Timeline color space or the RCM-assigned space. Tags metadata only; no conversion (downstream Gamut "From Image" or Saver output spaces use it) (p. 74).
- Source Gamma Space (Curve Type): Auto (timeline/RCM gamma per p. 1187), Space, Log (Log Type menu; Cineon adds Lock RGB, Level, Soft Clip, Film Stock Gamma, Conversion Gamma, Conversion table) (pp. 74-75, 1187).
  - Remove Curve - removes the gamma curve / does log-lin, giving linear output.
  - Pre-Divide/Post-Multiply - converts straight alpha to premultiplied (p. 75).
- Audio tab: Audio Track, Sound Offset, Purge Audio Cache (p. 75).
- EXR options appear in a separate tab even on MediaIn; other format options appear in the Image tab (p. 86).
- Find the Media Pool source of a selected MediaIn: Clip > Find Clip in Media Pool (Option-F) (p. 73).

### Loader (LD) - Fusion Studio's main input; EXR-only in Resolve
- Inputs: Effect Mask (blue) (p. 1176).
- Adding: Effects Library Tools > I/O > Loader, toolbar (Studio), right-click Add Tool > I/O > Loader, drag files from OS (one Loader per file), File > Import > Footage (new comp + Loader, comp named after media). Auto file browser on add; disable with Global > General > **Auto Clip Browse** (pp. 82, 1176).
- File tab (pp. 1177-1179):
  - Global In/Out - as MediaIn above; Loader starts at comp frame 0 by default. Global In always decides when the clip starts: Global In 0 + trimmed to start at source frame 10 shows source frame 10 on comp frame 0 (p. 83).
  - Filename - path with completion; Browse.
  - Proxy Filename - see Section 3.
  - Trim, Hold First Frame/Hold Last Frame, Reverse, Loop - as MediaIn. Trim context menu can force a clip length or rescan the folder (p. 1178).
  - **Missing Frames**: **Fail** (no image; render aborts), **Hold Previous Output** (holds last valid frame; fails if none seen yet, e.g. first frame missing), **Output Black**, **Wait** (polls every few seconds until the frame exists; all rendering stops meanwhile; for comping alongside a running 3D render) (p. 1179).
- Import tab (pp. 1180-1183):
  - Process Mode: Full frames, NTSC fields, PAL/HD fields, PAL/HD fields (reversed), NTSC fields (reversed). Default and height come from Frame Format "Has Fields". Reversed modes swap fields in time and vertical position.
  - Depth: **Format** (default; from file: JPEG 8-bit, EXR float; else Frame Format default), **Default** (comp Frame Format), Int 8 Bit, Int 16 Bit, Float 16, Float 32.
  - Pixel Aspect: From File (TIFF, JPEG, OpenEXR can carry it; else default), Default (ignore header), Custom (reveals X/Y Pixel Aspect; right-click for common formats).
  - Import Mode (pulldown): **Normal**, **Pull Up** (removes 3:2 pulldown, 30 -> 24 fps), **Pull Down** (applies pulldown 24 -> 30, five frames from four; Process Mode must be Full Frames). **First Frame** menu (which 3:2 cadence frame starts the clip) and **Detect Pull-Down Sequence** button appear only in Pull Up/Pull Down.
  - Make Alpha Solid (alpha = opaque white); Invert Alpha (with Make Alpha Solid gives fully transparent); **Post-Multiply by Alpha** (multiply RGB by alpha: straight/"subtractive" -> premultiplied/"additive"); Swap Field Dominance (time order only, no scanline swap).
  - Color Space Type (Auto/Space; metadata tag only), Curve Type (Auto/Space/Log), Remove Curve.
- Format tab: per-format controls; OpenEXR channel mapping (type an EXR channel name next to each Fusion channel; channel names can be dumped with the openexr.com command-line utility); QuickTime track selection; CinemaDNG; PSD layer select (pp. 1183-1184). Only DPX, OpenEXR, PSD and QuickTime have options (p. 86). In Resolve the Format tab toggles EXR aux channels (p. 77).
- Image-sequence detection (p. 1178): last characters before the extension must be numeric (`image.0001.braw`, `image151.exr` OK; `shot.1.fg.jpg` not a sequence). Any frame can be picked; length = first to last number found; gaps ignored (`image.0001.exr` + `image.0100.exr` = 100-frame clip, gaps handled by Missing Frames). Shift-drag a single file to load just that frame.

### MediaOut (MO) - Resolve only
- Input: Input (orange, required): any 2D image to render back (p. 1189).
- Every Fusion page comp must include one; first MediaOut renders to Edit/Cut timeline; additional ones send mattes to Color (p. 1189).
- Color Grade view options (previews only; output unchanged): **None** (default; Fusion output at source/comp resolution), **Color** (includes Color page adjustments, timeline resolution), **Mix** (includes Cut/Edit effects + Color, timeline resolution) (pp. 1190-1191).
- Exported to Fusion Studio as a Saver (p. 80).

### Saver (SV) - Fusion Studio's renderer; EXR-only in Resolve
- Input: Image Input (orange) (p. 1192). Place at the end, or anywhere to write intermediate branches; any number per comp; several Savers on one node = several formats (pp. 90-91).
- Adding a Saver opens a Save dialog (p. 91).
- File tab (pp. 1193-1194):
  - Filename - extension sets the format (`.exr` -> EXR, `.mov` -> H264 QuickTime) (p. 92).
  - **Output Format** - changing this menu does **not** change the filename extension; fix the name manually (p. 1193).
  - **Save Frames**: **Full Renders Only** (normal; writes only on final render) or **High Quality Interactive** (writes each frame to disk as you process interactively, for paint/roto; already-written frames do not re-render if splines change later; step through again or do a final render) (pp. 1193-1194).
  - **Frame Offset** thumbwheel - explicit start number for file numbering (manual's example: Global Start 1, frames 1-30 normally numbered 0001-0030; with "Sequence Start Frame" 100 the output starts at 100) (p. 1194).
- Export tab (pp. 1194-1195): Process Mode (same five field options); **Export Mode** (normal or SMPTE 3:2 pulldown, 24 -> 30 fps); **Clipping Mode**: **Frame** (default; clips to frame, breaks infinite workspace, area outside a smaller upstream DoD = black/transparent) or **None** (no clipping; can produce huge files); **Save Alpha to Color** (alpha written as grayscale into RGB, overwriting color); Color Space Type (output conversion applied only to written files, e.g. deliver linear EXR and Rec.709 QuickTime from one comp); Curve Type (Auto/Space/Log); **Apply Curve** (applies the gamma, converting from linear).
- Audio tab (Studio only): Source Filename (WAV), Sound Offset (p. 1196).
- Legal tab: Video Type (NTSC, NHK, PAL/SECAM); Action: Adjust to Legal, Indicate as Black, Indicate as White, No Changes; Adjust Based On 75% or 100% amplitude (leave at 75% for most markets); Soft Clip (pp. 1196-1197).
- Format tab: format-specific. DPX: when Bypass Conversion is on because data is already log, keep **Data Is Linear** off; turning it on flags the DPX header as linear so readers skip log-lin (pp. 1197-1198).

### Common I/O Settings tab (documented once, pp. 1199-1201)
Blend (0.0 normally skips processing), Process When Blend Is 0.0, Red/Green/Blue/Alpha selectors (usually applied after processing by copying the original channel back; some tools skip the channel entirely and mirror these buttons on their Controls tab), Apply Mask Inverted, Multiply by Mask, Use Object/Use Material + Correct Edges + Object ID/Material ID sliders (EXR ID channels), **Hide Incoming Connections** (hides input wires unless the node is selected; drag nodes into Inspector fields), Comments (red square on node), Scripts (three script fields per tool that run when the tool renders).

---

## 6. Rendering

### Fusion page (pp. 90, 93)
- Output path is MediaOut -> Edit/Cut timeline (render cache per Project Settings) -> Deliver page. No Render Settings dialog.
- Saver in the Fusion page: EXR only. Type the filename with `.exr`, Browse for location, then **Fusion > Render All Savers**. Uses: manual disk cache of heavy branches (render, re-import with Loader, keep original branch for re-edits; these files are never auto-purged), multi-channel mattes, EXRs with AOVs for other apps (pp. 78, 93).

### Fusion Studio (pp. 90-94)
- All rendering goes through Savers. Click Render (transport) or File > Render All Savers to open **Render Settings**; Shift-click Render skips the dialog with defaults (full resolution, high quality, motion blur on) (p. 30).
- Render Settings dialog (pp. 93-94):
  - **Configurations**: Final (locks quality options) or Preview (unlocks them); save named preview configs with Add.
  - Settings (Preview only): HiQ, MB, **Some** (render only nodes needed for the previewed node).
  - Size (Preview only): lower than full resolution (useful for proxies).
  - Network: distribute to render nodes (Use Network checkbox, group list).
  - Shoot On (Preview only): every 2nd/3rd/4th frame; Step parameter.
  - Frame Range: defaults to the Time Ruler Render In/Out in both configurations.
- Flipbook previews (RAM only): right-click node > Create > Play/Preview on > Left/Right viewer, or Option-drag a node into a viewer (opens dialog); Option-Shift-drag skips the dialog and reuses previous settings (pp. 94-95).

### Frame numbering and padding
- Image sequences get a frame number inserted before the extension; default 4 digits (for numbers below 10000): `image_name.exr` -> `image_name0000.exr`, `image_name0001.exr`... (pp. 92, 1193).
- Explicit padding by typing digits: `image_name_000.exr` -> `_000`, `_001`... (3-digit); `image000000.exr` = 6-digit; `image.001.exr` = 3-digit; `image1.exr` = no padding (pp. 78, 92, 1193).
- **Starting number always uses the Time Ruler start frame number** (p. 92), unless Frame Offset is set (p. 1194).

---

## 7. Network rendering (Fusion Studio, pp. 95-110)

- Render nodes = machines running the free-licensed Fusion Render Node software (unlimited licenses; installer inside the Fusion Studio .dmg/.zip). It auto-starts at login (macOS menu bar / Windows Start Menu / Linux launcher) (p. 95).
- **Render Master**: Preferences > Global > Network: Name, IP, "Make This Machine a Render Master", optionally "Allow This Machine to Be Used as a Render Node". Negligible overhead. Render Manager: select node > Set Default Master (p. 96).
- Enable a render node: File > Allow Network Renders, or the Network pref checkbox; on Render Node machines use the tray/menu-bar icon > Allow Network Renders (p. 97).
- **Render Manager** (File > Render Manager): master is always first in the node list; right-click > Scan for Render Nodes (scans the subnet port; node software must be running) or Add Render Node (name or IP, works offline); Remove Render Node(s). Node lists and queues save to `Documents > Blackmagic Design > Fusion > Queue`; Render Node > Save/Load Render Node List; File > Save Queue As / Load Queue (pp. 97-100).
- Submit: Render Settings > Use Network (appends to queue on the submitting workstation's configured master), Render Manager Add Comp / drag .comp in, or third-party managers (p. 99).
- Queue renders top-down; comps may render simultaneously by group/priority. A comp marked Done moved down does not re-render; right-click > Clear Completed frames to re-render (pp. 99-100).
- **Groups**: every node is in "All"; assign via Render Node > Assign Group (comma-separated list; order = priority, e.g. "All, Hi-Performance" gives All jobs priority and overrides in-progress Hi-Performance work). Submit to a group via Pause Render > right-click comp > Assign Group > Resume, or pick in Render Settings "Available groups" (pp. 100-101).
- Render Log: bottom of Render Manager, or Misc > Show Render Log (console); Misc > Verbose Logging toggles Verbose vs Brief (p. 101).
- **Only image sequences distribute (EXR, TIFF, DPX...). QuickTime, H264, ProRes, MXF cannot be network rendered**; render a sequence, then compile to a movie on one workstation (pp. 99, 109). Network previews are the exception (they spool) (p. 109).
- Requirements checklist (p. 103): dongle, master and nodes on the same subnet; Fusion Server running as a background service on the dongle machine; all media, comp and Saver destinations on network volumes mounted on every node with identical paths and read/write access; fonts for Text+/3D text installed on every node; third-party OFX (licensed) installed on every node.
- Paths: use Path Maps; `Comp:\` = folder of the saved comp. Example: comp `Volumes\Project\Shot0810\Fusion\Shot0810.comp`, media `...\Fusion\Greenscreen\0810Green_0000.exr` -> `Comp:\Greenscreen\0810Green_0000.exr`; media in sibling Footage folder -> `Comp:\..\Footage\Greenscreen\0810Green_0000.exr` (`..` = up one folder) (pp. 104-105). "Enable Reverse Mapping of Paths" in Path Map prefs inserts `Comp:\` automatically (p. 1179). Some path maps (e.g. macros) must be added manually on render nodes (p. 105). Windows mapped drive letters must match on all nodes; macOS: Go > Connect to Server (smb://), Login Items to auto-mount (p. 105).
- Network flipbooks: render to Preferences Global > Path > **Preview Renders** (default `Temp\`, must be changed to a shared folder); frames are spooled into local RAM and deleted from disk. Disk cache: right-click node > Cache to Disk > Use Network > Pre-Render (p. 106). Third-party managers lose network flipbooks and disk caches (p. 102).
- Reliability: failed node's frames are reassigned; nodes rejoin when back (set the master in each node's prefs so they know whom to contact). Render Node Preferences > Tweaks > **Last Render Node Restart Timeout** (seconds before aborting a queue after the last node goes offline). **Fusion Server** relaunches a crashed (not hung) Render Node. **Frame timeout** default 60 min, per comp: right-click comp > Set Frame Timeout, or Misc > Set Frame Time Out (seconds). **Heartbeats**: missed-count and interval in master's Network prefs; raise them for swapping machines (pp. 106-108).
- Render Node memory prefs (tray icon > Preferences > Memory): Override Composition Settings; **Render Several Frames at Once** (typically 2-3; memory use multiplies); **Simultaneous Branching** (renders layers in parallel; disable on low-RAM nodes) (p. 108).
- Poor network candidates: Time Stretcher / Time Speed (fetch many frames; pre-render first); "linear tools" whose frames depend on the previous frame (Fusion **Trails**, third-party particle systems such as GenArts Smoke/Rain) cannot render correctly over the network (pp. 108-109).
- Troubleshooting causes: No Render Nodes Could Be Found, Composition Could Not Be Loaded (path/plugins), Nodes Stop Responding, Failed to Render a Frame (retry on single machine). Restart a hung node to trigger reassignment. Ping nodes / Scan from master's Network prefs. Send render.log to support (pp. 109-110).

---

## Gotchas and non-obvious behavior

1. **Fusion clips throw away resolution.** New Fusion Clip conforms every layer to timeline resolution (4K in HD timeline = HD). For full-res plates, open a single clip and bring the rest in from the Media Pool, or use a Referenced Composition (pp. 66, 69).
2. **Single-clip comps run at source resolution, not timeline resolution**; MediaOut is scaled into the timeline by Project Settings (pp. 64, 90). Do not size Backgrounds/Text to timeline res by assumption.
3. **Only the topmost visible clip enters Fusion** from a playhead park; covered lower clips are ignored (p. 64). Use Media Source > Background on a MediaIn to pull the composite of lower tracks (p. 74).
4. **Render range is not a trim.** Changing it in the Fusion page never trims the timeline clip; handle frames outside the yellow lines are invisible in the Fusion page (pp. 22-23).
5. **Media Pool MediaIns start at frame 0** while the timeline MediaIn may start later; align with Global In (p. 76). Media Pool MediaIn audio is muted by default (p. 72).
6. **Referenced comps reject clips of differing frame rates or with speed changes**, and require overlap with the top clip to be created (pp. 69-70). Reset Reference Composition resets it for every linked clip (p. 70).
7. **Loader and Saver in Resolve are EXR-only.** Loader EXR imports do not appear in the Media Pool; Fusion page Saver needs `.exr` typed in the name and Fusion > Render All Savers (pp. 77, 93).
8. **Saver Output Format menu does not rename the file extension**; mismatched name/format is possible (p. 1193). The extension you type chooses the format (p. 92).
9. **Saver numbering starts at the Time Ruler start frame**, 4-digit default padding, padding set by zeros typed in the name; Frame Offset overrides the start (pp. 92, 1193-1194).
10. **Global In/Out auto-edits Trim and Hold.** Shrinking the range trims; growing it adds Hold First/Last frames (pp. 76, 1177).
11. **Trim In/Out are 1-based frame offsets** in the manual's wording (Trim In 5 = start on 5th frame) (p. 76). (inference: verify against the Inspector readout before scripting exact trims.)
12. **Loop includes held and trimmed frames**; held frames are looped too (p. 77).
13. **Sequence length comes from the first and last numbers found**; gaps count as frames and are handled by Missing Frames (default behavior not stated; set it explicitly). "Wait" blocks all rendering until the file appears (pp. 1178-1179).
14. **Pull Down import requires Process Mode = Full Frames** (p. 1182). Swap Field Dominance swaps time order only; the "(reversed)" Process Modes swap spatially and temporally (pp. 1181-1182).
15. **Color Space Type / Curve Type on MediaIn/Loader only tag metadata**; Remove Curve is what linearizes (p. 74, 1182-1183). Saver Color Space converts only the written file, not the comp (p. 1195).
16. **Connecting an empty mask to a MediaIn/Loader blanks the image.** Draw the mask disconnected with the MediaIn in the viewer, close the shape, then connect (pp. 73, 84).
17. **Selecting several nodes (or none) and adding a node creates it disconnected**; only a single selected node gets an auto-connected successor (p. 36).
18. **Keyframes Editor layer order is meaningless**; the graph wiring decides compositing order (p. 44).
19. **HiQ cache persists when HiQ is turned off** (stays green and is used) (p. 33). Viewer settings never change final renders (p. 27).
20. **The Current Time field cannot do `+` math** (Feet + Frames separator) (p. 30).
21. **Shift-Arrow mapping conflicts in the manual**: Fusion page Shift-Back = Global Start, Shift-Forward = Global End (p. 25); the Fusion Studio list states the reverse (p. 28). Treat as a probable doc error and test.
22. **Import Fusion Composition replaces the whole existing comp**; to merge, copy/paste nodes instead (p. 80). Export to `.comp` drops ResolveFX and any clips not in the Node Editor; MediaIn -> Loader (relinks if the path matches), MediaOut -> Saver (p. 80).
23. **Network rendering cannot write movie files** (QuickTime/H264/ProRes/MXF); Trails and history-dependent particle tools render wrong on a farm (pp. 99, 109).
24. **Custom toolbar edits are not undoable** (p. 35). Undo history dies with the project close (p. 62).
25. **Audio changes need Purge Audio Cache**, including level changes made on Edit/Cut/Fairlight pages (p. 75).
26. Manual inconsistencies to be aware of: Global In/Out held-frame color (purple p. 76 vs green p. 1177); Saver numbering example lists `image0000.tga` and skips 0002 (p. 1193); Frame Offset example says 30 frames from 100 end at 131 (p. 1194). Trust behavior, not the examples.

---

## Recipes / workflows

### A. Full-resolution multi-plate comp from the timeline
1. Park on the hero plate in the Edit page; open the Fusion page (single-clip comp keeps source resolution) (p. 64).
2. Open the Media Pool (UI toolbar) and drag each additional plate into the Node Editor; drop onto the MediaIn -> MediaOut line to get it as Merge foreground (p. 72).
3. For each added MediaIn, set Global In so it lines up with the timeline MediaIn (easiest in the Keyframes Editor); use Trim In/Out, Hold First/Last Frame, Loop as needed (p. 76).
4. For audio from an added clip: Inspector > Audio tab > Audio Track, then right-click the speaker icon and choose that MediaIn (p. 72).

### B. Key and pass transparency back to the edit
1. Single-clip comp: insert DeltaKeyer between MediaIn1 and MediaOut1 (p. 65).
2. Return to the Edit page; place the background on a lower track. The keyed clip is transparent there (p. 65).

### C. Reusable comp across many clips (Referenced Composition)
1. Stack overlapping clips (hero on top); select all; right-click > Create Referenced Fusion Composition (p. 67).
2. Double-click it in the Media Pool; build the comp (`MediaIn1` = top clip, others = lower tracks) (p. 69).
3. For each other target: select the comp in the Media Pool, right-click the target clip > Link to Referenced Composition (p. 69).
4. To swap an element, replace-edit the new clip onto its track; MediaIn refreshes (p. 68). Avoid mixed frame rates and speed ramps (p. 70).

### D. Manual disk cache of a heavy branch (Fusion page or Studio)
1. Add a Saver after the finished branch; filename `branch_0000.exr` (explicit 4-digit padding) (pp. 78, 92).
2. Fusion page: Fusion > Render All Savers. Studio: Render button > Configurations Final > Start Render (pp. 92-93).
3. Add a Loader pointing at the rendered sequence; wire it where the branch fed in; keep the original branch disconnected for later re-renders (pp. 78, 93).

### E. Rotoscope directly onto footage without blanking it
1. Add the mask node (Polygon/BSpline) unconnected; select it; load MediaIn/Loader in the viewer (p. 73).
2. Draw and close the shape.
3. Connect the mask to the MediaIn/Loader Effect Mask input (p. 73).

### F. Fusion Studio: set up a new comp for delivery
1. Preferences > comp's Frame Format (or Global Frame Format for future comps): resolution, pixel aspect, frame rate, Has Fields (p. 81).
2. Set Global Start/End (transport fields) to the shot length; set time display in Defaults if you want timecode (pp. 23, 31).
3. Load plates with Loaders (drag from OS; Shift-drag for a single still) (p. 82). Use `Comp:\` relative paths if it will go to the farm (p. 104).
4. Add Saver(s): name with extension and padding; set Export tab Color Space/Curve Type + Apply Curve for the delivery space (pp. 92, 1195).
5. Render button > Render Settings: Final, check Frame Range (defaults to render range) > Start Render (pp. 93-94).

### G. Linear workflow tagging on input
1. MediaIn/Loader: set Color Space Type (Space) and Curve Type (Space or Log) to match the source.
2. Enable Remove Curve to output linear; enable Pre-Divide/Post-Multiply (MediaIn) or Post-Multiply by Alpha (Loader) if the source alpha is straight (pp. 74-75, 1182).
3. Use the viewer LUT to preview a normalized image without baking it (p. 21).
4. On output, Saver Curve Type + Apply Curve re-applies the delivery gamma (p. 1195).

### H. Farm render from the command line (third-party manager)
1. Ensure all Loaders/Savers use shared, identical or `Comp:\` paths; fonts and OFX installed on nodes (pp. 103-105).
2. Run: `FusionRenderNode.exe <path>/exampleV001.comp -render -start 101 -end 110 -quit` (p. 102). Only image-sequence Savers.
3. Add `-log <file>` (appends; `-cleanlog` to clear), `-verbose`, `-quiet` for unattended runs; `-pri idle` to deprioritize (pp. 102-103).
4. Headless Linux needs an X11 virtual frame buffer (p. 103).

---

## Scripting and automation hooks

### Stated in the manual
- Console: Lua 5.1 default; Python 2.x/3.x selectable if installed; single-line immediate execution in the current comp context (p. 58). FusionScript output appears there (p. 17). Full API is in the "Fusion Studio Scripting Guide" (p. 58).
- Tool abbreviations for Select Tool and scripting references: `LD` Loader, `MI` MediaIn, `MO` MediaOut, `SV` Saver (p. 1175).
- Every tool's Settings tab has three Scripts fields that run when the tool renders (p. 1201). "Process When Blend Is 0.0" exists so scripted side-effects still fire at Blend 0 (p. 1200).
- Composition files are plain text (`.comp`); autosaves are `.autosave`; Resolve stores comps in `.drp` projects; File > Export Fusion Composition / File > Import Fusion Composition move comps between Resolve and Studio (pp. 79-80).
- Path maps: `Comp:\` (folder of the saved comp), `..` for parent, `Temp\` (system temp; default Preview Renders path) (pp. 104-106).
- Queue/render-node lists folder: `Documents > Blackmagic Design > Fusion > Queue` (pp. 99-100).
- Render Node command line (pp. 102-103):

| Argument | Meaning |
|---|---|
| `"Fusion Server -i"` | Install license server as service/daemon at boot |
| `"Fusion Server -S"` | Run Fusion Server persistently until force-quit |
| `<filename.comp>` | Full path to comp |
| `-render` | Render |
| `-frames <frameset>` | e.g. `101..110,120,121,130..150` |
| `-start <frame>` / `-end <frame>` | Range |
| `-step <step>` | Normally 1; 2 = every second frame |
| `-quit` | Quit when done |
| `-join <host>` | Connect to manager at host/IP and (re)join renders |
| `-listen` | Stay running and wait for manager requests |
| `-log <filename>` / `-cleanlog` / `-verbose` | Logging (log appends) |
| `-quiet` | Suppress pop-ups/interaction |
| `-version` | Print version |
| `-pri high\|above\|normal\|below\|idle` | Process priority |
| `-args <arg1> [, <arg2> ...]` | Custom values readable by script function `GetArgs()`, returns `{ <arg1>, <arg2>, ... }` |

### Keyboard shortcuts stated in this slice

| Keys | Action | Page |
|---|---|---|
| 1 / 2 | Load selected node into left/right viewer (again = clear) | 20 |
| ` (accent) / Tilde | Clear active viewer / all viewers (no viewer active) | 20 |
| = / - | Zoom viewer in/out | 19 |
| Cmd-1 / Cmd-2 / F | Viewer 100% / 200% / fit | 19 |
| / | Split wipe; , = A buffer; . = B buffer | 20 |
| C / A; R G B A | Toggle Color/Alpha; show channel | 21 |
| Shift-V | Swap SubView with viewer | 21 |
| Space; J K L | Play toggle; reverse/stop/forward | 24 |
| Left/Right Arrow | -1 / +1 frame | 24-25 |
| Shift-Left/Right | Global Start/End (mapping contradicts between p. 25 and p. 28) | 25, 28 |
| Cmd-Left/Right | Render Range In/Out | 25 |
| Option-[ / Option-] | Previous/next keyframe | 32 |
| Shift-Space | Select Tool dialog (add node by name) | 36 |
| Delete/Backspace | Delete selected nodes / control points | 38, 48 |
| V | Toggle Node Editor Navigator | 39 |
| Cmd-1 (Node Editor) | Reset Node Editor scale | 40 |
| Option-F | Clip > Find Clip in Media Pool | 73 |
| Cmd-C / Cmd-V | Copy/paste nodes (also between Studio and Resolve) | 80 |
| Cmd-Z / Shift-Cmd-Z | Undo / Redo | 62 |
| Shift-click Render | Render with defaults, skip dialog (Studio) | 30 |
| Option-drag node to viewer / Option-Shift-drag | Flipbook preview with / without dialog | 94-95 |
| Cmd-drag in Time Ruler | Set render range | 23 |
| Middle+Right drag (3D viewer), Shift + two-finger drag | Orbit 3D Perspective view | 19 |

### Not stated in this slice (inference, verify before use)
- The slice gives no Inspector input IDs or registry IDs for these nodes. Before `SetInput`/`.setting` authoring, enumerate them on a live tool: create with `comp.AddTool("Saver")` / `comp.AddTool("Loader")`, then read `tool.GetAttrs()["TOOLS_RegID"]` and `tool.GetInputList()` (inference; standard Fusion scripting API, not documented in these pages).
- Because Fusion page Saver is EXR-only, scripted Savers in Resolve should always use an `.exr` filename and be triggered by the equivalent of Fusion > Render All Savers (inference from pp. 77, 93).
