<!-- 02-node-editor-macros-templates-inspector.md part 1 of 3; index: 02-node-editor-macros-templates-inspector.md -->
# Node Editor, Groups, Macros and Templates, Viewers, Inspector (Fusion in Resolve 21.1)
Scope: Fusion manual pp. 111-249 (Ch. 5 Node Editor, Ch. 6 Groups/Macros/Templates, Ch. 7 Viewers, Ch. 8 Inspector). Use when: wiring or reorganizing node trees, building macros or Edit-page templates (Titles/Transitions/Effects/Generators, .drfx), linking parameters (Publish, Connect To, pick whip, expressions, instancing), configuring viewers (A/B, subviews, LUTs, DoD/RoI, 3D view), or explaining any Inspector control behavior.

## Mental model

1. **Node tree, not layer stack.** Order of operations is defined only by upstream/downstream connection, never by on-screen position (p. 132). Node position is purely cosmetic (p. 147).
2. **One connection per input, unlimited per output.** Branching = feeding one output to many inputs (p. 134). Every node has exactly one output (square knot); inputs are arrows (p. 126).
3. **Merge input roles are semantic.** Background (orange) is the default input and **defines output resolution**; Foreground (green) goes on top; Effect Mask (blue) limits the effect (p. 135).
4. **Selected vs viewed are different things.** Onscreen controls follow the *selected* node(s); the image comes from the *viewed* node (p. 123, 192). Classic roto setup: view the MediaIn, select the Polygon.
5. **Active node** = the one orange node whose parameters are editable; other selected nodes are white (p. 123). Inserts and many commands target the active node.
6. **Nodes are text.** Copying nodes yields a plain-text (Lua-table) representation that can be pasted into any text editor and back (p. 141). `.setting` files are the same format and can be dragged into the Node Editor to recreate nodes/groups (p. 155, 161).
7. **Macro = group with a curated control surface.** The Macro Editor chooses which internal parameters are exported, their names, defaults, min/max, and layout (p. 161-164). Groups expose everything; macros expose only what you export.
8. **Edit-page templates are macros saved into specific folders** (`.../Fusion/Templates/Edit/{Titles,Transitions,Effects,Generators}`) and require a Resolve relaunch to appear (p. 168-178).
9. **Template duration** is not driven by keyframes alone: use Resolve Parameter modifier (transitions), Anim Curves, or Keyframe Stretcher so animation adapts when trimmed on the timeline (p. 171, 178).
10. **Instancing** shares all settings between copies; you can de-instance individual parameters and re-instance them later (p. 145-146).
11. **Viewers are display-only transforms.** LUTs, gain/gamma, RoI, checker underlay never change rendered output; MediaOut/Saver always render full frame (p. 213-214).
12. **DoD vs RoI.** DoD = where the image has data (propagates downstream, travels with the image); RoI = what the viewer asks to be rendered. Render region = RoI ∩ DoD (p. 211-212).
13. **Inspector has two panels:** Tools (node parameters) and Modifiers (modifiers, expressions-as-modifiers, Paint strokes) (p. 226).
14. **Three ways to link parameters:** Connect To an existing animation curve; Publish + Connect To; pick whip / expression (p. 244). Instancing is the fourth, node-wide option.

---

## 1. Node Editor (Ch. 5)

### Navigation and bookmarks (p. 113-116)
- Pan: middle-drag, Shift+Cmd+drag, or two-finger drag. Zoom: middle+left drag, Cmd+scroll, right-click > Scale; Cmd-1 = Default Scale.
- Selecting an off-screen node (via Find or Inspector header) auto-pans the Node Editor to it (p. 114).
- Node Navigator (overview, upper right): toggle with **V** or Options > Show Navigator; Options > Auto Navigator shows it only when nodes are outside the view (p. 114, 156). Drag lower-left corner to resize; right-click > Reset Size.
- Bookmarks save pan+scale: Options menu > Add Bookmark or **Cmd-D**; name it in Manage Bookmarks. First nine bookmarks get keyboard shortcuts and appear in the Options menu; reorder in Manage Bookmarks to reassign shortcuts (Shift-select to move several). Go To Bookmarks dialog lists all, searchable (p. 115-116).
- **Underlays are automatically added as bookmarks**; hide them with the Show Underlays checkbox in Go To Bookmarks (p. 116).

### Adding, inserting, replacing nodes (p. 116-121)

| Action | Result |
|---|---|
| Click toolbar button / Effects Library item with a node selected | New node added **after** the selected node |
| Same with nothing selected | Disconnected node |
| Drag button/item onto a connection line (line highlights) | Inserted into that connection |
| Drag into empty Node Editor space, or into the Inspector | Disconnected node |
| Drag onto a **viewer** | Inserted after whichever node is viewed, regardless of selection |
| Drag onto an existing node (node highlights) + confirm OK | **Replace**; identical settings are copied (e.g., Transform to Merge keeps Center and Angle) |
| Right-click empty area > Add Tool / right-click node > Insert Tool / Replace Tool | Add / insert / replace via contextual menu |
| **Shift-Space** (Select Tool window), type name or keyword/category (e.g., "keyer", "materials"), Return | Inserts after selected node or adds disconnected. Remembers last text: Shift-Space, Return adds another of the same (p. 118) |

- Compatibility matters: 2D tools (Blur, Color, Filter, Paint, Position) insert after nearly any 2D op, but e.g. a Merge3D after a Glow **won't auto-connect** (p. 116).
- Effects Library categories: Tools, Open FX (Resolve FX + third-party OFX), Templates (presets/macros: Backgrounds, Lens Flares, Particles, Shaders, "How to", etc.), LUTs. Adding a LUT creates a **FileLUT (FLUT)** node preloaded with that file (p. 119-120).
- Some templates (e.g., "How to" > LightWrap) add an entire node tree, all nodes pre-selected so you can move it (p. 121).

### Deleting and disconnected nodes (p. 122)
- Delete (macOS) / Backspace (Windows). Nodes on the deleted node's **primary input and output are reconnected**; nodes on other inputs (masks) become disconnected.

### Selecting (p. 122-123)
- Cmd-click add/remove; box-drag; Cmd-box-drag deselects; Cmd-A / Cmd-Shift-A; right-click > Select > Upstream/Downstream Nodes. Set the active node within a selection: Option-click it or click its Inspector header.

### Loading nodes into viewers (p. 124-126, 185-186)
- View indicators (dots under node, visible on hover or when viewed): left dot = left viewer, right dot = right viewer. White = loaded.
- Keys **1** / **2** toggle selected node into left/right viewer; additional viewers get indicators numbered **3-9**.
- Drag node onto a viewer; right-click > View On > None/Left/Right; also from Inspector header context menu; dragging an Inspector header into a viewer also loads it (p. 230).
- Clear: press 1/2 again, or **`** (accent) with a viewer active clears it; with no viewer active, ` clears all (p. 125, 186).
- Right-click node > Create/Play Preview On > viewer: renders a RAM preview. Hold Shift when choosing the viewer to skip the Render Settings dialog (p. 126).

### Connecting (p. 126-129)
- Output knot color: **white** = connected, **gray** = disconnected, **red** = error, node cannot process (p. 126).
- Drag output to input or input to output (direction doesn't matter).
- **Drop a connection onto a node's body**: 1st drop = default input (Background/Input); next drop = second input (Foreground on multi-input nodes; Effect Mask on single-input nodes); on Merge the 3rd = Effect Mask (p. 127, 135).
- Merge3D (and similar) **adds a new input** every time you drop onto it (p. 128).
- **Option-drag and drop onto a node body**: after release, a popup lists inputs by name (p. 128). Tip variant: right mouse + Option drag from output to node center (p. 129).
- **Mask nodes** (Polygon, B-Spline, Ellipse, Rectangle) dropped on a node body connect to the default *mask* input, usually the Effect Mask, even on a MatteControl where you may want Garbage Matte (p. 129).
- Hover a knot for its name; hovering a node colors its connections by input type (p. 129, 133).

### Merge wiring shortcuts (p. 134-136)
- Adding a Merge after a selected node (toolbar, Effects Library, Insert Tool > Composite > Merge) always connects the **upstream node to Background**.
- Drag a clip from an OS window or a Generator from the Effects Library **onto a connection line**: auto-creates a Merge; BG = upstream side of the line, FG = new node.
- Drag 2+ files from an OS window at once: Merges chain them automatically.
- **Drag one node's output onto another node's output**: auto-creates a Merge (dragged node = Foreground, dropped-on node = Background).
- Pasting a MediaIn, Loader, or Generator "after" a selected node auto-creates a Merge (pasted node on FG). Configurable: Fusion Settings > Defaults > Auto tools (p. 141).

### Disconnecting, reconnecting, routers, pipes (p. 132-138)
- Each connection has an output half and input half (blue highlight on hover). Click the **input half** once to disconnect; drag either half to another knot to overwrite/reconnect.
- Pipes: Options > Direct Pipes or Orthogonal Pipes (visual only).
- **Routers**: Option-click a connection to add one. Single input/output, no parameters except Comments. Branch a router's output to any number of nodes. Delete like a node. Options > Auto Remove Routers (default on) deletes orphaned routers.
- **Swap inputs**: Cmd-T or right-click > Swap Inputs (Merge, Merge 3D, Dissolve). Only FG/BG swap if more than two inputs are connected. Lines don't move; knot **colors** change (p. 138-139).
- **Extract**: Shift-drag a node (or selection) up/down out of the tree, drop, then release Shift; upstream and downstream auto-rejoin. **Insert**: Shift-drag a disconnected node onto a connection, drop, release Shift. Only one node can be inserted at a time; one Shift-drag can extract and re-insert (p. 139-140).

### Cut, copy, paste, settings (p. 140-142)
- Cmd-C / Cmd-X / Cmd-V. Paste with a node selected = inserted after it; nothing selected = disconnected (click empty area first to choose location).
- **Paste-to-replace** only via right-click node > Paste (then OK).
- **Paste Settings**: copy node A, right-click node B > Paste Settings. Works across different node types; only matching parameters transfer (e.g., animated Center from Transform to a mask's Center).
- Nodes copy as plain text (same as saved internally) into any text editor/email; paste text back into the Node Editor to recreate them (p. 141-142).

### Instancing (p. 145-146)
- Copy, then **Paste Instance** (Cmd-Shift-V, or right-click background/connection line > Paste Instance). Select an upstream node first to insert.
- Naming: `Instance_NameOfNode`; multiple: `Instance_NameOfNode_01` etc.
- Green link lines show instance relationships; toggle with Options > Show Instance Links.
- Right-click node > **Deinstance**: permanent (undo only). After relaunch, the only way back is copy original + Paste Instance again.
- Per-parameter: right-click a parameter name/value in Inspector > **Deinstance** / **Reinstance** (reinstance immediately inherits the original's value).

### Naming rules (p. 147-148)
- Auto names: type + counter (Blur1, Blur2...).
- Rename: right-click > Rename or **F2** (multiple selected = one dialog per node).
- Names must be scriptable: **alphanumeric only, no spaces, no special characters, cannot start with a number**. Invalid characters/spaces are **silently deleted**.
- Hold **Cmd-Shift-E** to display node types instead of names.

### Organization (p. 146-150)
- Node color: Inspector header Node Color popup (16 colors) or right-click > Set Color; Clear Color resets.
- Snap: right-click > Arrange Tools > To Grid / To Connected; default for new comps via Fusion Settings > Fusion > Node Editor > Arrange To Grid / Arrange to Connected. Right-click empty > Line Up All Tools to Grid; right-click selected node > Line Up to Grid.
- **Sticky Notes**: Shift-Space, type "sticky", Return (or Effects Library > Tools > Node Editor). Double-click to expand/edit; close box minimizes; F2 rename; Delete removes.
- **Underlay Boxes**: Shift-Space, type "under", Return. With nodes selected first, the underlay is sized to enclose them. Nodes fully inside move with it (drag by title bar). **Option-click** selects the box without its contents (needed to rename, recolor, or delete the box only). Shrinking the box until nodes stick out removes them from it.
  - **Delete with underlay selected (normal click) deletes the box AND all nodes inside.** Option-click then Delete keeps the nodes.

### Thumbnails (p. 150-152)
- Right-click background: Force All / Force Active / Force Source (MediaIn, Loader, generators) / Force Mask Tile Pictures. Per node: Show > Show Tile Pictures, Show > Show Modes/Options. Uncheck Show Thumbnails to show icons instead.
- 3D and particle nodes show icons only, except **pRender** and **Renderer 3D**. Upstream Transforms that **concatenate** don't process, so no thumbnail. Pass Through nodes and Loaders out of range show no thumbnail. With thumbnails on, nodes may not refresh until the playhead moves.

### Find (p. 152-153)
- Cmd-F or right-click > Find. Options: whole phrase, match case, sequence number, regular expression. Search by **tool name, tool type name, or tool type ID**.
- Find Next = downstream, Find Previous = upstream, Find All selects all matches. Then Cmd-P bypasses them all (e.g., disable every Resize).
- Regex character sets: `[a-z]`, `[a-d]`, `[aeiou]`, `[0-9]`, `[5-7]`, `[Tt]`.

### Custom defaults and saved settings (p. 154-155)
- Right-click node or Inspector header > Settings > **Save Default** makes current values the default for new nodes of that type.
- Stored under Path Map > Defaults. Defaults:
  - macOS: `/UserName/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Defaults`
  - Windows: `C:\Users\<username>\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Fusion\Defaults`
  - Linux: `~/.fusion/BlackmagicDesign/DaVinci Resolve/Fusion/Defaults`
  - File name `INTERNALNAME_PUBLICNAME.setting`, e.g. `Blur_Blur.setting` (manual prints both `.settings` and `.setting`; the example uses `.setting`).
- Right-click a parameter > **Set to Default** resets one parameter. Settings > **Reset Default** resets the node **and deletes the saved default .setting file**. Deleting the file manually also resets.
- Settings > Save As writes an alternate `.setting` anywhere; Settings > Load applies one. Dragging a `.setting` file into the Node Editor creates the node; dropping onto a connection inserts it.
- Six in-node versions via the Inspector Version buttons (see Inspector).

### Node Modes (right-click > Modes) (p. 155-156)

| Mode | Shortcut | Default | Behavior |
|---|---|---|---|
| Show Controls | - | On | Whether parameters show in Inspector and onscreen controls in viewers |
| Pass Through | Cmd-P | Manual says "On by default" (inference: means the node is enabled, not bypassed) | Same as Inspector header toggle; bypassed node passes upstream image downstream unaltered |
| Locked | Cmd-L | Off | Same as header Lock; no edits possible |
| Update | Cmd-U | On | Off = parameter edits don't re-render; last image held as freeze frame. Use for heavy particle systems or to play downstream animation without re-rendering upstream |
| Force Cache | - | Off | Current-frame output gets extremely high cache priority |

Each active mode shows a badge on the node.

### Node Editor Options menu (right-click background > Options) (p. 156)
Pipes Always Visible (lines drawn over nodes); Show Hidden Pipes (overrides per-node Hide Incoming Connections); Aspect Correct Tile Pictures (default on); Full Tile Render Indicators (thumbnail flashes green while rendering); Show Grid; Show Instance Links; Auto Remove Routers (default on); Show Navigator; Auto Navigator; Build Flow Vertically/Horizontally (where new nodes are placed); Orthogonal/Direct Pipes.

### Tooltips and status bar (p. 157)
Hover a node: status bar shows name, frame size, pixel aspect, resolution, color depth. After a moment, a floating tooltip adds **Domain (Image and DoD)** and data range. DoD appears there only when it differs from frame size (p. 212).

### Multilayer images (Studio only) (p. 142-145, 201)
- Viewer layer dropdown selects which layer of EXR/stereo/PSD to view; non-layered files show only "default".
- Settings tab > Layer category:
  - **Process Layers**: Default Layer (default; base/unnamed layer only), All Layers, Custom (pick a layer).
  - **Input Layer**, **Effect Mask Layer**, **Image Layer** (and other `<InputName> Layer`) per input: **Auto** (default; requests the Process Layers layer, falls back to default layer if missing), **Match** (same but **fails** if missing), or an **explicit layer**.
- Connecting a multilayer source to both the image input and Effect Mask of a node lets you mask by any layer.
- Renderer3D: Eye control > Layers outputs stereo eyes as separate layers. MultiMerge, Channel Booleans, MatteControl get BG/FG layer selectors. **Combiner** with Mode = Layer creates named custom layers.
- Fusion plugins get Process Layer/Input Layer controls auto-generated in the Settings tab.

---

## 2. Groups (Ch. 6, p. 159-161)
- Create: select nodes, right-click > Group or **Cmd-G**. Unlimited nodes, nestable.
- Group node shows **inputs/outputs only for internal nodes already connected outside** the group; unconnected internal inputs get no knot.
- Open/close: double-click or **Cmd-E**; opens a floating, independently zoomable Node Editor where you can add/insert/delete. Position button on the group title bar: off = group scale locked to main tree; on = independent.
- Delete: Delete/Backspace/Forward-Delete removes group and contents. Right-click > **Ungroup** keeps contents.
- Save: right-click > Settings > Save As (`.setting`). Reuse: drag the file into the Node Editor (new group). Right-click group > Settings > Load applies saved settings to a group with the same nodes (hand-off workflow between artists).
- Saving a group `.setting` into the Macros folder makes it appear under Insert Tool > Macros (macOS example: `Macintosh HD/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Macros/`) (p. 165).
- Fusion Studio: drag a group into an open Bin to save it as a `.setting`.

## 3. Macros and the Macro Editor (p. 161-165)

**Create:** select node(s), right-click > **Macro > Create Macro**. Tip: **Cmd-click nodes one by one in the order you want their controls to appear**; the Macro Editor orders nodes by selection order (p. 167, 173).

**Macro Editor layout:**
- **Macro Name** field (top). Prefixes with `/` create folders inside a `.drfx`: `Bundle One/CustomMacro` puts CustomMacro in a "Bundle One" folder (p. 162).
- **Thumbnail**: right-click the magic-wand icon > Choose Thumbnail / Clear Thumbnail.
- **"Save to" dropdown** (left of name): save as a plain `.setting` macro or into one of the **four template categories** (Titles, Transitions, Effects, Generators) (p. 162).
- **Parameter columns (left pane)**, one row per internal parameter:

| Column | Meaning |
|---|---|
| Tool/Input | Internal Fusion parameter name or input connection |
| Export | Checkbox: include in macro |
| Name | Display name in the macro |
| Type | Expected data type |
| Default | Preset default value |
| Minimum | Minimum allowed value |
| Maximum | Maximum allowed value |

- **Live Inspector Preview (right pane)**: interactive; drag controls to reorder, move to another page, add/rename pages, add/remove/edit controls.
- Layout buttons (lower left): **Add Separator** (line), **Add Spacer** (blank), **Add Nest** (collapsible disclosure group; Default column 1 = open, 0 = closed). Remove any by unchecking its Export box.
- **Options (three-dot) menu**: Open; Open Template Bundle (loads a macro from a `.drfx`, pick one if several); Save (overwrites original location); Save As; Choose/Clear Thumbnail; Show in Folder; **Copy Macro** (clipboard, paste into Node Editor to test live without saving); **Update from Selected Tools** (edit the original nodes, select them, update the macro while **preserving control selection and layout**).
- Close button triggers the Save Macro As dialog (p. 168, 173).

**Using:** Add Tool > Macros or Replace Tool > Macros (p. 165). Re-edit: right-click Node Editor > Macro submenu > pick macro.

**Macro as viewer LUT:** copy its `.setting` into the `LUTs:` folder; must have **exactly one image input and one image output**; exported controls become editable via the LUT Edit option (p. 165, 215). Can be color, YUV 4:2:2 resampling, resize, sharpen, watermark.

## 4. Fusion Templates for the Edit/Cut page (p. 165-181)

### Per-type requirements

| Template | What to select before Macro > Create Macro | Save folder (under `.../Fusion/Templates/Edit/`) | Appears in Edit page | Notes |
|---|---|---|---|---|
| Title | All nodes **except** MediaIn/MediaOut (Loader/Saver in Studio) | `Titles` | Effects Library > Titles > Fusion Titles | Export only the controls the editor should touch (e.g., Text3D Styled Text, material color, light rotation) (p. 166-169) |
| Transition | All nodes **including both MediaIn nodes and the MediaOut** | `Transitions` | Video Transitions > Fusion Transitions | MediaIn1 = outgoing clip, MediaIn2 = incoming. **Must be saved from Resolve's Fusion page, not Fusion Studio** (needs MediaIn/MediaOut). Zero exported controls is allowed (duration-only) (p. 171-173) |
| Generator | All nodes **including the MediaOut** | `Generators` | Generators > Fusion Generators | Start from Noise Gradient generator, or an empty Fusion Composition effect (single MediaOut) (p. 173-176) |
| Effect | Select the effect node, then Cmd-A (i.e., **MediaIn + effect + MediaOut**) | `Effects` (subfolders allowed; they show as sections) | Effects section | Clip used to build it isn't saved (p. 177-178) |
| Multi-layer effect | Build inside a Fusion clip with N layers | `Effects` | Effects | Export the **Layer** checkbox on every MediaIn to allow re-mapping tracks. Track 1 (bottom) = MediaIn1, track 2 = MediaIn2... Apply by making a Fusion clip with the same layer count (p. 178) |

- **Always quit and relaunch Resolve** after saving a template before it shows in the Effects Library (p. 169, 173, 176, 178).
- Starting points: apply a Fusion transition (Cross Dissolve simplest, Slice Push most complex) or the Noise Gradient generator on the Edit page, right-click > **Open in Fusion Page** (p. 170-174). Editing an applied transition in Fusion updates that timeline instance on returning to the Edit page; to reuse it you must save a macro (p. 172).

### Template save paths (as printed, p. 168, 173, 176, 178)
- macOS: `Macintosh HD/Users/username/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/<Titles|Transitions|Generators|Effects>`
- Windows: `C:\Users\username\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates\Edit\<type>`
- Linux: `home/username/.local/share/DaVinciResolve/Fusion/Templates/Edit/<type>`
- Right-click any Effects Library bin > **Show Folder** to find the live path (p. 180).

### Duration behavior (p. 171, 178-179)
- **Transitions:** to make duration follow the Edit-page trim, apply the **Resolve Parameter** modifier to animated parameters and animate via its **Scale** and **Offset** parameters instead of keyframes.
- **Anim Curves** modifier: stretches/squishes keyframed animation as the template's duration changes (also easing, bounce, mirror).
- **Keyframe Stretcher** modifier (mainly titles): the hold between intro and outro stretches; intro/outro timing is preserved.

### Media drop zones (p. 179)
In the Macro Editor, export the **ClipName** parameter of each MediaIn that should accept media. In the Edit page, dragging a Media Pool clip onto the Inspector's Clip Name field swaps it in. Works for effects, plugins, transitions (e.g., both sides of a transition).

### Custom icon (p. 180)
`.png` with the **exact same base name** as the `.setting`, in the same folder. Recommended **104 x 58 px** (any size is resized). Default icon otherwise is the first three letters of the name. Relaunch.

### .drfx bundles (p. 180-181)
- Folder structure: `Edit/Effects`, `Edit/Generators`, `Edit/Titles`, `Edit/Transitions` for Edit-page templates; `Fusion` for Fusion-page templates. Include only needed folders.
- Build: create structure, copy `.setting` files (plus icons/assets), zip, rename `.zip` to `.drfx`.
- Install: double-click the `.drfx` (Resolve launches and asks) or drag it into the Fusion page.
- **The bundle is not unpacked.** Deleting the `.drfx` from the template directory removes every template in it.

---

