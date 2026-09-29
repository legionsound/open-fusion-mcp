<!-- 01-interface-timeline-io.md part 1 of 2; index: 01-interface-timeline-io.md -->
# Fusion Fundamentals: Page/Timeline Relationship, Interface, Media In, Rendering Out
Scope: Fusion 21.1 manual pp. 7-110 (Ch. 1 Intro, Ch. 2 Interface, Ch. 3 Getting Clips into Fusion, Ch. 4 Rendering Using Saver Nodes), plus the I/O Nodes reference pp. 1175-1201 cross-read for Loader/MediaIn/MediaOut/Saver parameter depth. Use when: deciding how a comp is born from the Edit timeline, what resolution/range/frame numbers a comp will have, how to bring media in (MediaIn vs Loader), how to get results out (MediaOut vs Saver, EXR, network render), or when you need viewer/transport/cache/proxy behavior and shortcuts.

## Mental model

1. **A comp is a node graph document.** Nodes are image-processing engines; the graph (node tree) plus all settings is a Composition ("comp") (p. 8). In Resolve, comps live inside the `.drp` project; in Fusion Studio they are plain-text `.comp` files (p. 80).
2. **Fusion page comps belong to timeline clips, like grades.** Each clip can carry one active Fusion composition (with versions), just as each clip carries a grade. A Fusion badge appears on the clip. Slip/slide/ripple/roll/resize in the Edit page and the comp follows the clip (pp. 8, 64).
3. **MediaIn = the clip coming in; MediaOut = what goes back.** Every Fusion page comp must have a MediaOut. The first MediaOut renders back to the Edit/Cut timeline; extra MediaOuts pass mattes to the Color page (pp. 64, 1188-1189).
4. **Pipeline order in Resolve: Fusion comes before Color.** Fusion viewers show the image before any Color page grade (p. 21). If Edit-page transforms/plugins exist on the clip, the handoff is Fusion effects -> Edit page plugins -> Color effects (p. 1189).
5. **Resolution depends on how the comp was born.** Single clip = source clip resolution; Fusion clip = timeline resolution (clips are downsized); Referenced composition = source resolution (pp. 64, 66, 69). MediaOut output is scaled into the timeline per Project Settings (p. 90).
6. **Two ranges on the Time Ruler.** Global range = total duration you can scrub (for a single timeline clip: the whole source clip including handles). Render range (yellow lines) = frames that are visible/played/cached/rendered; in the Fusion page it equals the clip's timeline In/Out (pp. 22-23).
7. **Time is sub-frame capable.** Ranges and playhead accept fractional frames (e.g. -145.6 to 451.75, playhead 115.22) (p. 26).
8. **Everything in the Fusion page is 32-bit float**, regardless of source bit depth (p. 75).
9. **Loader/Saver are Fusion Studio's I/O; in Resolve they are EXR-only.** In the Fusion page, Loader imports EXR from disk (no Media Pool clip created) and Saver writes EXR sequences only (pp. 77, 93, 1176, 1192).
10. **Node flow:** inputs are arrows (can be several), output is a single square; one output can branch to many inputs; Merge nodes combine branches. Flow can go in any direction; left-to-right is the default (pp. 38-39).
11. **Only needed nodes render.** Default "Selective" update renders only nodes contributing to the viewed image; viewer RoI intersects with each node's DoD to limit pixels processed (pp. 21, 27).
12. **Interactive quality is decoupled from final quality.** HiQ, Motion Blur, Proxy, Auto Proxy only affect viewer rendering; final renders are always highest quality (pp. 27, 30).

---

## 1. How Fusion page comps relate to the Edit timeline

### Ways a comp is created (Resolve)

| Method | What you get in the Node Editor | Resolution | Notes |
|---|---|---|---|
| Park playhead on a clip (Edit/Cut), click Fusion page | `MediaIn1 -> MediaOut1` ("single-clip composition") | Source clip resolution, not timeline (p. 64) | Only the topmost visible clip is taken; lower covered clips are ignored unless you disable the clips/tracks above (p. 64). |
| Select stacked/consecutive clips, right-click > **New Fusion Clip** | One MediaIn per clip, auto-wired into cascading Merge nodes reproducing the stack order | Timeline resolution (4K clips in an HD timeline become HD; full res unavailable) (p. 66) | New clip "Fusion Clip X" replaces the selection in the timeline and is added to the current Media Pool bin (p. 65). Bottom-of-stack clips appear at the top of the Node Editor, but BG/FG wiring is correct (p. 66). |
| Select one clip or overlapping stack, right-click > **Create Referenced Fusion Composition** | One MediaIn per track; `MediaIn1` = top selected clip, subsequent MediaIns = tracks below | Source resolution maintained (p. 69) | Lives in the Media Pool; reusable across clips and timelines (pp. 66-70). See rules below. |
| Edit page Effects Library > Generators > **Fusion Composition** | Only a `MediaOut` node (blank) | (not stated) | Dragged in = "Standard generator duration" preference, 5 s default; or use In/Out + edit overlays for a specific duration (p. 70). |
| Media Pool bin right-click > **New Fusion Composition** | Blank comp | (not stated) | Dialog asks Name, duration, frame rate. Open by double-click or right-click > Open in Fusion Page. For motion graphics/titles with no timeline or used in several timelines (p. 70). |
| Edit page Effects Library > Video Transitions (bottom of list) > Fusion Transition, then right-click > **Open in Fusion Page** | Two MediaIn nodes (both sides of the cut) into a dissolve or node group | (not stated) | Can be modified and saved back, or saved as a new reusable transition (p. 71). |
| Drag clip from Media Pool into Node Editor | Extra disconnected MediaIn | Source resolution (use this to keep full res alongside a Fusion clip) (p. 66) | Dropped on a connection line: becomes the foreground of a new Merge; several clips dropped on a line get enough Merges to connect all (pp. 53, 72). |
| Drag from OS file browser into Node Editor | MediaIn; file is also added to the currently selected Media Pool bin (p. 73) | Source | |
| Effects Library > Tools > I/O > Loader | Loader linked to an EXR sequence; no Media Pool clip (p. 77) | Source | Resolve's Loader is EXR-only (p. 1176). |
| Fusion > Import > PSD | One MediaIn per PSD layer + Merges set to the PSD Apply modes, auto-named by mode (pp. 87, 1184) | Source | Transformation and adjustment layers unsupported (pp. 87, 1184). |

- Nodes get numeric suffixes (`MediaIn1`, `MediaIn2`...) to distinguish instances (p. 65).
- The MediaIn tool in the Effects Library I/O category "is not used as a method to import clips" (p. 1184).
- **Reset:** right-click a Fusion clip in the Edit timeline > **Reset Fusion Composition** (multi-select allowed) (p. 71). Thumbnail timeline > Reset Current Composition (p. 53).
- **Versions:** Thumbnail timeline (Clips button) > right-click thumbnail: Create New Composition, "NameOfVersion" > Load / Delete / Rename; Reset Current Composition. Double-click under a thumbnail cycles label among clip format, clip name, comp version name. Current clip is outlined orange (p. 53).

### Referenced Fusion Compositions (rules, pp. 66-70)

- Create: select one or more timeline clips that overlap the top selected clip at least partially > right-click > "Create Referenced Fusion Composition". Without overlap the menu item is unavailable (pp. 67, 69).
- One composition is created, associated with the top selected clip; appears in the Media Pool. Double-click it to open in Fusion (p. 67).
- Link other clips (any timeline): select the referenced comp in the Media Pool, right-click target clip > "Link to Referenced Composition". Changes propagate to all linked clips (pp. 67, 69).
- The track contents are treated as a source: when you edit clips, effects, or transitions on a referenced track, the corresponding MediaIn refreshes automatically (p. 69). Example: replace-edit a new logo onto V3 and the comp picks it up with the same settings (p. 68).
- Removing a timeline clip does not remove the composition (p. 69). Media Pool right-click > Usage shows/navigates linked clips; comps can be duplicated for iteration (p. 67).
- Timeline clip context menu: **Reset Reference Composition** (affects all referenced clips), **Unlink Reference Composition** (clears the clip's effect; comp stays in Media Pool), **Find Reference Composition in Media Pool** (p. 70).
- **Not supported:** clips of differing frame rates, clips with speed changes (p. 70).

### Resolution and frame-rate summary

| Situation | Working resolution | Source |
|---|---|---|
| Single clip opened from timeline | Source clip resolution | p. 64 |
| Fusion clip (New Fusion Clip) | Timeline resolution; sources resized | p. 66 |
| Referenced composition | Original source resolution | p. 69 |
| Media Pool / file-system MediaIn | Source resolution | p. 66 (workaround text) |
| MediaOut back to timeline | Scaled to timeline per Project Settings (cache format + resolution scaling) | p. 90 |
| MediaOut viewer preview "Color"/"Mix" | Displayed at timeline resolution; "None" at source/comp resolution | pp. 1190-1191 |
| Fusion Studio new Creator tools (Text, Background, fractals) | Frame Format preferences (default resolution, pixel aspect, playback frame rate) | p. 81 |

Frame rate: bin-created Fusion Compositions take the frame rate you set in the creation dialog (p. 70). Referenced comps refuse mixed frame rates/speed changes (p. 70). Fusion Studio playback frame rate comes from Frame Format prefs (p. 81). The slice does not describe how the Fusion page handles a clip whose frame rate differs from the timeline for single-clip or Fusion-clip comps.

### Timing inside a timeline-born comp

- Time Ruler, single clip: global range = total source duration of the clip; yellow render range = the clip's timeline In/Out; frames outside it are the unused head/tail handles, not visible in the Fusion page (p. 22). You cannot move the playhead outside the global range (p. 22).
- Fusion clip or compound clip: the "working range" is the entire duration of that clip (p. 22).
- Changing the render range affects preview/playback only; it never trims the clip in the Edit/Cut timeline (p. 23).
- A MediaIn added from the Media Pool starts at comp frame 0, whereas the timeline MediaIn "may not start until a much later frame, based on where it is edited into the Timeline"; align with Global In (p. 76). (inference: the timeline MediaIn's comp frame numbers are not guaranteed to start at 0; read the Time Ruler before setting Global In or keyframes.)

### MediaOut, color management, mattes

- Whatever the MediaOut shows in the viewer is what renders back to the Edit/Cut page; Smart Render Cache starts caching MediaOut almost immediately on return to the Edit/Cut timeline (p. 90). Final delivery is the Deliver page (p. 90).
- With Resolve Color Management or ACES, each MediaOut converts the output back to timeline color space for handoff to Color (p. 1189).
- A keyer (e.g. DeltaKeyer) placed alone between MediaIn and MediaOut passes its alpha out: the Edit page clip gets transparency so a lower-track clip shows through (p. 65).
- Extra MediaOut nodes (added from the Effects Library) pass mattes to the Color page (p. 1189).

---

## 2. Time Ruler, ranges, transport

### Ranges

| | Fusion page | Fusion Studio |
|---|---|---|
| Global range | Set by the selected timeline clip (source duration) | Global Start/End: Preferences > Global and Default Settings (new comps) or the Global Start/End fields left of transport (current comp) (p. 23) |
| Render range | Timeline clip In/Out by default; only frames visible in Fusion page (p. 22) | Frames rendered/played/cached; frames outside can still be scrubbed (p. 23) |
| Set render range | Cmd-drag in Time Ruler; drag yellow lines; right-click > Set Render Range; Range In/Out fields; drag a node onto the Time Ruler (node duration) (p. 23) | Cmd-drag; right-click > Set Render Range (uses selected node's duration); Range In/Out fields; drag node onto Time Ruler (sets both Global and Render range to the node's extent) (pp. 23-24) |
| Restore | Right-click > Auto Render Range, or leave to Edit/Cut page and come back (p. 23) | n/a |

- Fusion page transport: 6 buttons (First Frame, Play Reverse, Stop, Play Forward, Last Frame, Loop); Studio: 8 (adds Step Backward/Forward) plus 4 range fields (Global Start/End, Render Start/End) and a Render button (pp. 24, 28-29).
- Loop button right-click: Playback Loop or Ping-pong Loop (pp. 25, 29).
- Right-click Play/Step buttons: frame increment for playhead moves (multi-frame for roto; 0.5 for field-by-field) (pp. 25, 28).
- Keyframes of the selected node show as white ticks on the Time Ruler; Option-[ / Option-] jump to previous/next keyframe (pp. 31-32).
- Zoom/scroll bar under the ruler; middle-drag in the ruler scrolls (p. 24).
- Time display: frames by default; SMPTE timecode or Feet + Frames via Fusion Settings > Defaults (Timecode option), then Frame Format panel: frame rate, "has fields" for interlaced, Film Size (frames per foot) (p. 31).
- Many numeric fields evaluate math (typing `2 + 4` enters 6.0), but the Current Time field will not evaluate `+` expressions even in Frames mode because Feet + Frames uses `+` as a separator (p. 30).
- No guaranteed real-time playback unless cached (pp. 25, 28).

### Audio

- Fusion page plays Edit/Cut timeline audio; muted timeline tracks are not heard; waveforms show in the Keyframes Editor (p. 26).
- Audio toolbar button toggles mute; right-click selects which MediaIn (page) or external WAV (Studio) plays, with offset in Studio (pp. 26, 29).
- MediaIn Audio tab: choose track, Sound Offset wheel slips audio in sub-frame increments (Fusion page only; other pages keep original placement), **Purge Audio Cache** button (p. 75).
- Purge the audio cache after changing tracks, after slipping, or after changing levels in Edit/Cut/Fairlight (p. 75).
- Media Pool MediaIn audio is muted by default: select node > Inspector Audio tab > pick clip in Audio Track menu > right-click speaker icon and choose that MediaIn (p. 72). If several MediaIns exist, the audio last selected in the Inspector is heard (p. 1188).
- Fusion Studio: WAV (AIFF on macOS) loaded whole into RAM, so use the shortest file; load via speaker icon > Choose, or Saver > Audio tab > Browse (waveform then visible by expanding the Saver track in the Keyframes Editor; drag over it to scrub-listen) (p. 88). Scratch-track use only; final renders should almost always be without audio. Audio is included in the saved file if QuickTime is the Saver format (p. 1196).

---

## 3. Viewer quality, proxies, RAM cache

| Control | Fusion page location | Studio button | Effect |
|---|---|---|---|
| High Quality | Right-click empty transport area | HiQ | Off skips area sampling, anti-aliasing, interpolation in viewer. On = identical to final output (pp. 27, 30) |
| Motion Blur | same menu | MB | Global kill switch for motion blur; nodes must have MB enabled for it to matter (pp. 27, 30) |
| Proxy | same menu; ratio: Fusion > Fusion Settings > General > Proxy slider | Prx; right-click for ratio (e.g. 5 = 5:1) or Preferences General | Processes 1 of every x pixels (pp. 27, 31, 85) |
| Auto Proxy | same menu; ratio in same Proxy section | Aprx; right-click for ratio | Reduced res only while dragging a control (pp. 27, 31, 85) |
| Selective Updates | Fusion Settings > General > Proxy section | 5th button, three-way | Update All (All: renders every node, updates all thumbnails), Selective (Some, default), No Update (None) (pp. 27, 31) |

- Viewers scale proxy images so they refer to original resolution (p. 85). Proxy settings never affect final render quality (p. 85).
- Loader **Proxy Filename**: a separate (e.g. 1/4-scale) clip loaded when Proxy mode is on. Must have the same number of frames and identical start/end sequence numbers; same format strongly suggested; format options (Cineon, DPX, OpenEXR) are shared with the primary (pp. 85, 1178-1179). Field appears only once Filename points to a valid clip (p. 1178).
- Other performance paths: Resolve Optimized Media; Studio: render proxies with Savers (p. 84).
- **RAM cache:** frames are cached as they render/play; priority goes to nodes loaded in viewers (p. 32). Green line on Time Ruler = cached for current node (real-time playable). Toggling quality/proxy turns the line red (cache preserved for that setting, overwritten if you play through at the new setting). Exception: HiQ-cached frames stay green and are reused after HiQ is turned off (p. 33).
- Limits: Resolve Preferences > Memory and GPU > **Limit Fusion Memory Cache To** (subset of Resolve RAM, max 75%, released when leaving the Fusion page). Studio Preferences > Memory: **Limit Caching To** (default 60%, max 80% of system RAM) and **Leave at least # MBytes** (0 = ignore other apps). At the limit, lower-priority frames are discarded; Status bar shows cache % (p. 32).

---

## 4. Interface essentials

### Layout and focus
- Four regions: viewers (top), work area (bottom: Node Editor, Spline Editor, Keyframes Editor), Inspector (right), Effects Library (left; shares with Media Pool in Resolve) (pp. 15-16).
- UI toolbar buttons: Media Pool/Effects Library Full Height, Media Pool (Resolve), Effects Library, Clips (Thumbnail timeline, Resolve), Nodes, Console (Studio), Spline, Keyframes, Metadata (Resolve), Inspector, Inspector Height (pp. 16-17).
- Focused panel captures shortcuts; Resolve needs "Show focus indicators in the User Interface" (User Preferences > UI Settings) to show the highlight (p. 17).

### Viewers (pp. 18-22)
- One or two viewers; each shows one node's output. 3D nodes switch the viewer to Perspective (or Quad) view.
- Load a node: hover node and click the viewer buttons at its bottom-left; select + press 1 or 2; right-click > View On > None/Left View/Right View; drag node onto a viewer. Pressing the viewer number again on the viewed node clears it (pp. 19-20).
- Clear active viewer: ` (accent). Clear all: press Tilde with no viewer active (p. 20).
- Fusion page opens with MediaOut1 usually in viewer 2 (p. 19).
- Title bar: Zoom menu; Split Wipe (/) + A/B buffer menu (Comma = A, Period = B); SubView (Navigator, Magnifier, 2D viewer, 3D Histogram, Color Inspector, Histogram, Image Info, Metadata, Vectorscope, Waveform; Shift-V swaps); RoI (Auto default = visible area; Set; Lock; Reset); Color channel (C/A toggle Color/Alpha; R, G, B, A; aux channels such as Z, Object ID, Material ID, Normals); Viewer LUT (preview only, does not bake); Option menu: Snap to Pixel, Show Controls, Region, Smooth Resize, Show Square Pixels, Checker Underlay, Normalized Color Range (see out-of-range float/aux values), Gain/Gamma, 360 View, Stereo (pp. 20-22).
- RoI x DoD: each node renders only the intersection of viewer RoI and its Domain of Definition (p. 21).

### Node Editor (pp. 35-41)
- Adding nodes: toolbar button, Effects Library click, right-click node > Insert Tool (after that node), right-click background (disconnected), **Shift-Space** Select Tool dialog (type name, Return). With exactly one node selected, new nodes attach after it; with none or several selected, they are added disconnected (p. 36).
- Remove: Delete/Backspace (p. 38). Hovering an input/output shows its name in the Status bar (p. 38).
- Navigator appears when nodes are offscreen; V toggles it (p. 39). Cmd-1 resets Node Editor scale (p. 40).
- Vertical layouts: Workspace > Layout Presets (Resolve only); Fusion Settings Flow > Build Direction > Vertical makes new trees build top-down. Return: Workspace > Layout Presets > Fusion Presets > Default (pp. 40-41).
- Status bar: node info on hover, playback fps, RAM cache %, Console-message badge (p. 41).

### Toolbar (pp. 33-35)
- Default groups: Loader/Saver (Studio only); Background, FastNoise, Text, Paint; ColorCorrector, ColorCurves, HueCurves, BrightnessContrast, Blur; Merge, ChannelBooleans, MatteControl, Resize, Transform; Rectangle, Ellipse, Polygon, BSpline; pEmitter, pMerge, pRender (click left-to-right to build a system); ImagePlane3D, Shape3D, Text3D, Merge3D, Camera3D, SpotLight, Renderer3D (auto-attach when clicked left-to-right).
- **Resize permanently changes resolution; Transform is resolution-independent and traces back to the source's original resolution** (p. 34).
- Custom toolbars: right-click > Customize > Create Toolbar / Add Divider / Rename / Remove; Remove [tool], Remove Group, Lock; switch via right-click. Toolbar edits are not undoable (p. 35).

### Effects Library (p. 42)
- Sections: Tools (all native nodes), OpenFX (third-party + ResolveFX in Resolve), Templates (Resolve only: Lens Flares, Backgrounds, Generators, Particle Systems, Shaders, etc.).

### Inspector (pp. 43-44)
- Tools panel (node parameters) and Modifiers panel (modifiers such as Perturb; Paint strokes appear here individually).
- Header: Set Color (16 colors), Versions (6 per-node version slots), Pin (keep node's controls when deselected), Lock, Reset. Multiple selected nodes show at once. Tabs appear as icons.

### Keyframes Editor (pp. 44-47)
- Every node is a layer; order is irrelevant (the graph defines processing order). Drag ends to trim In/Out, drag body to slide. Trimming an effect layer makes the effect cut in/out at those frames.
- Keyframes: click/box-select, drag in time, right-click for interpolation/copy/paste/new, Cmd-drag duplicates.
- Time/TOffset/TScale fields: TScale multiplies distance from playhead (playhead 10, key 30, TScale 2 -> key at 50) (p. 46).
- Time Stretch tool; Spreadsheet (e.g. rows "Key Frame" and "Path1Displacement") (pp. 46-47).

### Spline Editor (pp. 47-51)
- Option menu: Expose All Controls, Show Only Selected Tool.
- Click spline adds point; Shift-drag constrains; Cmd-drag handle breaks tangent; Delete removes.
- Interpolation buttons: Smooth, Linear, Invert (LUT splines only, not animation), Step In, Step Out, Reverse (time-reverses selected keys).
- Loop modes (applied after last point, selected points only): Set Loop, Set Ping Pong, Set Relative (each cycle offset by the trend).
- Tools: Select All, Click Append, Time Stretch, Shape Box (Cmd-drag corners = corner stretch), Show Key Markers.

### Console (p. 58)
- Resolve: Workspace > Console; Studio: View > Console or toolbar button. Filters: errors, logs, script messages, input echo. Languages: **Lua 5.1 (default, bundled)**, Python 2.x, Python 3.x (require installed Python). Entry field executes one line at a time, immediately, in the current comp context.

### Customization (pp. 59-62)
- Settings: Resolve Fusion > Fusion Settings; Studio Fusion Studio > Preferences (macOS) or File > Preferences (Win/Linux).
- Layouts: Resolve Workspace > Layout Presets > Save Layout Presets; Studio Preferences > Layout: Grab Document Layout, Grab Program Layout, Create Floating Views; Window > New Floating Frame > right-click > Add View.
- Hotkeys: Resolve DaVinci Resolve > Keyboard Customization > Panels > Fusion Page; Studio Views > Customize Hotkeys (Hotkey Manager; e.g. target Views > Effect, New, choose Tools > Blur > Glow, type G).
- Undo: unlimited, Cmd-Z / Shift-Cmd-Z; history purged when the project closes (p. 62).

### Fusion Studio comps and bins (pp. 55-57, 78-82)
- Multiple comps open as tabs; unsaved = asterisk. File > Save Version appends a 3-digit version number that auto-increments, same folder (p. 79).
- Auto Save: Preferences > Global > General > Auto Save; writes `<name>.autosave` beside the `.comp`; unsaved comps autosave to the Comp: path in Paths prefs; on load you are asked which to open (pp. 79-80).
- `.comp` is plain text; edit with a text editor, never a word processor (p. 80).
- Frame Format prefs: Global (defaults for new comps only) vs per-comp (listed under the comp's name). Set these to the delivery format first (p. 81).
- Bins (File > Bins): links to files, no copying; folders Clips, Compositions, Favorites, Settings, Tools; New Folder/Reel/Clip, Studio Player (pp. 55-57).

---

