<!-- 02-node-editor-macros-templates-inspector.md part 2 of 3; index: 02-node-editor-macros-templates-inspector.md -->
## 5. Viewers (Ch. 7)

### Layout and outputs (p. 185-187)
- Single/Dual viewer toggle button. Fusion Studio only: floating viewers via Window > New View.
- Video Output: with Blackmagic hardware, preview a node on a calibrated display (no onscreen control manipulation there).
- **Clean Feed** (Resolve, dual monitors): disable Workspace > Dual Screen, then Workspace > Video Clean Feed > pick display. Adds a **third view indicator** under each node.
- Active viewer has a light purple outline.

### Zoom/pan (p. 187-188)
Same pan/zoom as Node Editor, plus **=** / **-**, middle-hold + left/right click (zoom in/out at cursor). **Cmd-1 = 100%**, **Cmd-2 = 200%**, **Cmd-F = fit** (manual also lists Cmd-1 for fit). Scale menu has Custom Scale.

### Custom guides (p. 188-189)
Cmd-G or right-click > Guides > Show Guides. Guides > **Add Resolve Guide** (visible on other Resolve pages): Units (pixel or percentage), Position, Orientation (horizontal/vertical). Right-click a line: Remove Guide, Edit Guide, Lock Guide; Guides > Lock All Resolve Guides; Guides > **Snap to Guides** makes moved image edges snap. Viewer-only, never rendered.

### Standard guides and frame format (p. 209-211)
Guides submenu: Monitor Safety, Safe Title, Center, Film. Guides > Frame Aspect: Default = image's own aspect; a specific value darkens (gray) everything outside that format. Fusion Settings > Frame Format: **Guide 1** = four offsets (left, top, right, bottom) in resolution-independent units (**1 = full image width, 0.5 = half**); **Guide 2** = projection aspect ratio.

### Flipbook (RAM) previews (p. 189-192)
- Create: **Option-drag** node into a viewer, or right-click node > Create/Play Preview. **Shift-Option-drag** skips the dialog (defaults/last used).
- Dialog: **HiQ** (full quality), **MB** (motion blur), **Some** (render only nodes needed for this node); Size (shows how many frames fit in RAM, lower resolution to fit more); Network (Studio only); **Shoot On** Step (every Nth frame); Frame Range (defaults to Render Range In/Out); Configurations > Add to save presets.
- Playback: double-click or Spacebar; Shift-Space reverse; right-drag scrubs; Left/Right arrows step; Shift-arrows 10 frames; Cmd-Left/Right first/last. Right-click: Play, Loop, Ping-Pong, Full Screen, Show Frame Numbers, **Update** (auto-refreshes modified frames, for paint/roto), Remove Preview.
- Flipbooks respect the viewer's RoI.

### Onscreen controls and toolbars (p. 192-194)
- Controls shown = **selected** node(s), all selected nodes at once. Toggle: viewer Options > Show Controls, right-click > Options > Show Controls, **Cmd-K**.
- Some nodes (e.g., Polygon) allow per-node disabling of onscreen controls.
- Nudge: Up/Down arrows move vertically by small steps; +Cmd = 1/10 step; +Shift = 10x step.
- Node toolbar (under viewer toolbar) appears for Text, masks, paths, Paint, 3D.

### A/B buffers and split wipe (p. 194-196)
- Each viewer has A and B buffers; A is default. **Comma (,)** = A, **period (.)** = B, or Buffer menu.
- Each buffer keeps independent display settings (channel, LUT) even on the same node.
- Split wipe: load different nodes (or same node with different options) into A and B; **/** or the Split Wipe button toggles. Drag center handle to move; drag divider to rotate (Shift snaps to 45 degrees); **Cmd-Option-click** jumps the divider to the pointer. Pan/zoom affect both. Drag nodes onto either half to change that side. Click a half to change its own channel/LUT.

### Subviews (p. 196-200)
- Toggle: Subview button, Views > Subview > Enabled, or **V** in a viewer. Pick type from the button's arrow menu or right-click in the subview. **Shift-V** or Views > SubView > Swap swaps with main view (not for subview-only types).

| Type | Where | Notes |
|---|---|---|
| Navigator | Subview only | Overview rectangle for panning when zoomed |
| Magnifier | Subview only | Zoomed pixels under cursor |
| 2D Viewer | Both | **Only subview that can show a different node** (drag node into subview) |
| 3D Image Viewer | Both | For 3D-category nodes |
| Image Info | Subview only | Frame size, pixel aspect, color depth |
| Color Inspector | Subview only | Values under cursor, including aux channels (Z, XYZ normals, UV) |
| 3D Histogram | Both | Shows out-of-range float/HDR and vector data (position, normal, velocity); rotate with Option+middle-drag or middle+right drag |
| Histogram | Both | Includes out-of-range float values; drag a From Image or Perturb modifier's title bar into it to see its gradient |
| Metadata | Both | Loaders usually give color space, file path |
| Vectorscope / Waveform | Both | Chroma / luminance scopes |

### Channels (p. 200-201)
Color button toggles RGB/alpha; arrow menu lists all channels. Keys: **C** RGB, **R**, **G**, **B**, **A**, **Z**. Auxiliary channels (OpenEXR etc.) via the arrow menu or right-click > Channels.

### 3D Viewer (p. 203-209)
- Appears when a 3D node (or some particle nodes) is viewed; GPU-accelerated.
- Pan changes point of view (and pivot). Zooming past the lower scale limit **dollies** forward (wheel slow, keyboard fast). Rotate: **Option + middle-drag** or **middle+right drag**, centered on view.
- Right-click > 3D Options > **Wireframe** (e.g., check ImagePlane3D Subdivision).
- Right-click > Camera: Perspective, Front, Top, Left, Right; scene cameras listed; lights/other objects under **Other**. While looking through an object, navigating **moves that camera/light**.
- Camera > **Copy PoV To** > Camera3D name: copies viewer position/angle into the camera. Uses the object's **own coordinate space; downstream transforms are ignored**.
- POV label bottom-left; right-click it or the axis control for the Camera menu.
- Lighting: default flat lights until you toggle 3D Options > **Lighting**; 3D Options > Default Lights shows default light. 3D Options > **Shadows** (auto-enables Lighting). **Viewing a light node alone shows an empty scene**: view the Merge3D it connects to.
- Transparency: Z-buffer default (fast, can be wrong with stacked transparency); Transparency submenu **Quick Sort** (back to front) or **Full Sort** (every polygon, most accurate, slowest).
- Grid: default **24 x 24 units** centered at (0,0,0), major squares 2 units, minor 0.25 units; change in Fusion Settings > 3D View. Toggle 3D Options > Grid.
- 3D Options > **Vertex Normals**.
- **Quad View**: Shift-Q or Views > Quad View; per-pane POV via its label (Front, Left, Top, Bottom, Perspective, cameras, spotlights); Views > Quad Layouts. For 2D, each pane can show a channel or subview type.

### Domain of Definition and Region of Interest (p. 211-213)
- **DoD**: rectangular region containing actual pixel data, shown as two XY pixel coordinates (axis-aligned bbox). Enables skipping empty pixels and processing pixels **outside** the frame. Generators set it automatically (FastNoise, Mandelbrot, Background = full frame; Text+ and most masks = smaller or larger).
- OpenEXR data window is read as DoD by Loader and written by Saver. **Resolve clips from the timeline/Media Pool default to full-frame DoD, except OpenEXR.**
- DoD changes node to node (shrink/expand/move). Show it: node tooltip (if different from frame) or viewer right-click > **Region > Show DoD**.
- Manual DoD: **Auto Domain** node (Tools > Miscellaneous), e.g., animate a DoD around a CG character.
- **RoI**: which pixels the viewer requests; node renders RoI ∩ DoD. Enable with the RoI button or Region > Show Region (first time = full frame; then last position). Drag edges/corners; drag the small top-left circle to move. **Set Region** (draw), **Auto Region** (fit to visible zoom/pan), **Reset Region** (or disable RoI).
- RoI is preview-only: **MediaOut and Saver always render full frame**. Loaders/MediaIn only read RoI pixels if the format supports direct pixel access (Cineon, DPX, many uncompressed; OpenEXR and TIFF in limited cases).
- Changing viewed image size, color depth, or Proxy (incl. Auto Proxy) resets pixels outside the RoI to canvas color; otherwise stale outside pixels remain (useful for before/after).
- Manual tip: enabling Options > Show Controls overrides the RoI and forces full-image renders (as stated on p. 213).

### Viewer LUTs (p. 214-221)
- Viewer LUTs affect display only.
- **Image LUT**: per viewer, and separately per **A/B buffer**; **2D only** (not 3D scenes). Typical: preview log or scene-linear in the final space.
- **Buffer LUT**: one only; applies to everything including 3D scenes, materials, subviews; applied after the Image LUT. Typical: display calibration (e.g., DCI-P3 projector showing sRGB look). To use: **disable the LUT button first**, then right-click > Global Options > Buffer LUT > Enable, then choose type. Remove by unchecking Enable.
- Recommended workflow: convert to linear at the start of the tree, composite, then view through an Image or Buffer LUT for the target space (p. 214).
- Types:
  - **Fusion View LUT** (default): RGBA curves like Color Curves, **not animatable**; Gain slider, **Color Gamma** and **Alpha Gamma** (alpha gamma only when viewing alpha/masks). Manual cites video monitors ~1.7, computer monitors 1.6-2.2.
  - **Log-Lin View LUT**: Mode (Log to Lin / Lin to Log), Log Type, lock RGB, level, Soft Clip (Knee), Film Stock Gamma, Conversion Gamma, Conversion Table + Browse.
  - **Gamut View LUT**: Source and Output color space; Remove Gamma / Add Gamma checkboxes; **Pre-Divide/Post-Multiply** (avoid illegal additive values on keyed/CG edges). Commonly used when working in linear.
  - **Macro LUTs**: any macro with one image in/out saved into the LUTs folder; CPU-rendered (slowest).
  - **LUT presets**: all Resolve LUTs, including the **VFX IO** category (to/from Linear transforms).
  - **Fuse LUTs**: fuse named `CT_ViewLUTPlugin`; GPU shaders only, cannot run in software.
- Enable/disable: LUT button; choose from the arrow menu; **Edit** at top of menu or right-click > LUT > Edit opens the editor.
- Processing order (p. 219): Image output > Image LUTs (Macro LUTs, Fusion View LUT) > post-processing (checker underlay, dithering) > Buffer LUT (single) > viewer output; onscreen controls drawn last. 3D scenes are rendered with OpenGL.
- Stacking: right-click > LUT > Add New > pick; LUT > Delete > pick (not the first). A full stack saves as `.viewlut`.
- Save/Load: right-click > LUT > Save writes ASCII `.viewlut` to the LUTs folder (appears in menus); LUT > Load for others. In the LUT editor, right-click curve > Export LUT as **ASCII `.alut`** (share with other apps) or **Saved `.lut`** (Fusion-preferred, compact, editable); Import LUT loads back. Also moves curves between viewers and Color Curves nodes.
- Supported LUT files in the LUTs folder: `.lut`, `.alut`, `.alut3`, `.cube`, `.shlut`, `.look`, `.3dl`, `.itx`.
- Any node/group/macro as LUT: select, Settings > Save As, into the folder set in Preferences > Global > Path Map > LUTS.
- LUT folder paths (as printed, p. 215): Resolve macOS `Macintosh HD/Users/username/Library/Application Support/Blackmagic Design/Fusion/LUTs/`; Resolve Windows `C:\Program Files\Blackmagic Design\Fusion\LUTs`; Resolve Linux `home/username/.local/share/DaVinciResolve/Fusion/LUTs`. Fusion Studio: macOS same as above; Windows `C:\Users\username\AppData\Roaming\Blackmagic Design\Fusion\LUTs`; Linux `home/username/.fusion/BlackmagicDesign/Fusion/LUTs`.
- Default LUT for new comps: Fusion Settings > View(er) panel > **Enable Display LUT** + choose from Display LUT plugins.

### Viewer settings and options (p. 221-224)
- Right-click > Settings > Save New (whole viewer config incl. LUT curves, gain/gamma); load via Settings > filename; Save Defaults / Load Defaults.
- Options: Show Controls (Cmd-K); **Checker Underlay** (default on in 2D; off = black); Show Pixel Grid (off); **Smooth Resize** (bilinear, default on, **SmR** button; off = nearest neighbor for true pixels); **Show Square Pixels** (**1:1** button; disables aspect correction); **Gain/Gamma** sliders (gamma-slam checks); **360° View**: Disable, Auto, LatLong, Vert Cross, Horiz Cross, Vert Strip, Horiz Strip.
- **Lock viewer: Cmd-L** (node still processes; display doesn't update).
- Options submenu: **Alpha Overlay** (off by default) + Overlay Color (default white); **Follow Active** (off by default: viewer shows the active node); **Show Full Color Range** (normalizes brightest to 1.0, darkest to 0.0; for float, Z, aux); Show Labels.
- Status bar: RGBA and Z under pointer, X/Y coordinates and pixel position.

---

## 6. Inspector (Ch. 8)

### Panels, preferences, pinning (p. 226-230)
- **Tools** panel = parameters; **Modifiers** panel = modifiers and expression-based modifiers attached to parameters, plus data like Paint Strokes.
- Height toggle (arrow at right of UI toolbar): full-height vs half-height.
- Fusion Settings > User Interface:

| Preference | Default | Effect |
|---|---|---|
| Auto Control Open | On | Active node's controls open automatically |
| Auto Control Hide | On | Deselected nodes leave the Inspector (off = they accumulate) |
| Auto Control Close Tools | On | Only the active node's parameters can be expanded (off = several open at once) |
| Auto Controls for Selected | On | Multi-selection shows a header per node (off = only active node) |

- **Pin** button keeps a node's parameters in the Inspector regardless of selection; newly selected nodes appear above pinned ones.
- Hide a node's Inspector controls: right-click node or header > Modes > Show Controls (alternative to locking).
- Selecting a node from Node Editor, Keyframes Editor, or Spline Editor opens it.

### Inspector header (p. 230-231)
Enable/disable toggle (same as Pass Through); name (right-click > Rename or F2); color popup (16 colors, Clear Color); **Versions** button; **Pin**; **Lock**; **Reset** (rightmost; resets whole node to defaults). Click header = make active; drag header into a viewer = view it; **drag header into Spline Editor = show all its animated splines**. Right-click header = same contextual menu as the node.

### Versions (p. 231)
Versions button shows a bar of **six** version buttons, each storing a full parameter set, saved with the node. Orange underline = version in use. Right-click a number > Clear.

### Settings tab common controls (canonical reference; other slices point here) (p. 232-235)
- **Blend**: all nodes except Loader, MediaIn, generators. 0.0 = output equals input and the node usually **skips processing**; default 1.0.
- **Process When Blend Is 0.0**: forces processing at Blend 0; needed for nodes/plugins that carry state frame to frame.
- **Red/Green/Blue/Alpha checkboxes**: unchecked channels are copied from input. Most nodes still compute all channels then copy; nodes with linked RGBA(Y) boxes on their main tab (**Blur, Brightness/Contrast, Erode/Dilate, Filter**) truly skip unchecked channels.
- **Apply Mask Inverted**: inverts the Effect Mask input only (**not garbage masks**).
- **Multiply By Mask**: RGB multiplied by mask, outside becomes black (premultiplied result).
- **Use Object / Use Material**: mask by OpenEXR Object ID / Material ID; reveals Sample (drag from button into viewer to pick ID) and **Correct Edges** (uses Coverage and Background Color channels to reduce aliasing).
- **Motion Blur** (motion-capable nodes like Transform, Warp): **Quality** (samples each side of motion, default 2), **Shutter Angle** (default 100; 360 = full-frame exposure; higher allowed), **Center Bias** (shifts blur center, trails), **Sample Spread** (sample weighting/brightness).
- **Scripting**: per-node script fields run at render time (see Scripting docs).
- **Comments**: text field, animatable; shows an icon in the header and in the node tooltip.

### Control types (p. 236-242)
- **Edit Control**: right-click in Inspector (or on the header) > Edit Control opens the Control Editor (see User Controls).
- **Slider**: click gutter to step; Cmd = smaller, Shift = larger steps. **Typing a value beyond the slider range is allowed and expands the slider** (e.g., Blur Size 500 though slider max is 100). Circle under the gutter appears when changed; click to reset.
- **Thumbwheel**: no min/max (typical for angles). Up/Down arrows adjust; Cmd/Shift for fine/coarse; reset circle.
- **Range control**: drag ends for Low/High; drag center to move both; Cmd-drag an end = symmetric expand/contract; type floats into Low/High boxes (Matte Control, Chroma Keyer, Ultra Keyer).
- **Checkbox**: animatable; **0 = off, 1.0 or greater = on**.
- **Dropdown**: animatable; value **0 = first item**, 1 = second, etc.
- **Button array**: dropdown equivalent with visible options (e.g., Defocus Lens Type).
- **Color**: swatch (opens OS color picker, must click OK), built-in chooser (grayscale, sat/value, hue bar, alpha bar), Eyedropper: drag from it into the viewer; Cmd+drag a rectangle sets sample size, which persists for all pickers. Display range 0-1, 0-255, or 0-65000 via Preferences > General.
- **Gradient**: Gradient Type (Linear, Reflect, Square, Cross, Radial, Angle = counter-clockwise sweep); Start/End Position (X/Y + onscreen crosshairs); color stops (click bottom of bar to add; drag to move; **Cmd-drag copies**; drag up off bar or red X deletes); Interpolation Space; Offset; **Once / Repeat / Ping-Pong** (behavior past ends when offset); **1x1-5x5** sub-pixel precision (higher = slower). Right-click the bar for animate/publish/connect and a modifier that samples a gradient from a node's output.

### Modifiers and keyframing (p. 242-244)
- Attach a modifier: right-click parameter > Modifier submenu; its controls appear in the Modifiers tab.
- Keyframe button right of each parameter: gray click = key at playhead (turns orange). After the first key, **changing the value on another frame auto-creates a key**. Orange click = delete that key. Side arrows jump to adjacent keys. Keyframe badge shows on the node if Show Modes/Options is on.
- Remove all keys: right-click parameter name > **Remove "node name:parameter name"** (label changes if default spline type isn't Bezier).

### Linking parameters (p. 244-245)
- **Attach to existing animation curve**: right-click the second parameter > **Connect To** > choose the animated parameter. Both share one curve.
- **Publish + Connect To**: right-click the first parameter's name > **Publish**; right-click the second > Connect To > the published name. Adjusting one adjusts the other.
- **Pick whip (simple expression)**: double-click the field, type **=**, press Return; Pick Whip controls appear under the parameter; drag a whip from the **Add** button to the target parameter. Result: the original parameter follows the target. The Expression field can then add math to the received value.
- Cross-node pick whip: disable the **Auto Control Close** preference (called "Auto Control Close Tools" on p. 228; p. 245 calls it a "General" preference), select both nodes so both are open, then whip.
- Expressions can also be entered via right-click parameter label > **Expression** (used in the Directional Blur example, p. 248).

### Multi-Inspector (p. 246-247)
- Select multiple tools; the **Combine Selected Tools** toggle in the header shows only shared controls; edits apply to all.
- If values differ, some knobs/values hide. Dragging the value field **adds/subtracts an offset** to each (keeps differences); Size/Scale controls apply a **scale factor** (keeps ratios). **Opt/Alt-drag** switches between offset and scale mode.
- Right-click > **Set Values To**: First, Middle, Minimum, Maximum, Spread (even distribution), Jitter (random).

### User Controls / Edit Control (p. 247-249)
- Right-click node name in the Inspector header > **Edit Control** opens the Edit Control window (a.k.a. running the UserControls script).
- Sections: **Input attributes** (pick existing control or create new, Name, Type, Page/tab), **Type attributes** (input control kind, defaults, ranges, onscreen preview control), **Input Ctrl attributes** (e.g., button names), **View Ctrl attributes** (onscreen preview control).
- Selecting an existing ID prompts **Replace, Hide, or Change ID**. Replace keeps the ID, so existing expressions keep working.
- **IDs must be unique; Names need not be** (two controls can both be labeled "Type").
- User controls are stored in the node instance: survive copy/paste, `.setting` save, Bins, favorites.

**Worked example (Directional Blur driven by Center):**
1. Length expression: `-sqrt(((Center.X-.5)*(Input.XScale))^2+((Center.Y-.5)*(Input.YScale)*(Input.Height/Input.Width))^2)`
2. Angle expression (as printed; parentheses look malformed, verify before use): `atan2(Center.Y-.5)/(Input.OriginalWidth/Input.X , .5-Center.X) * 180 / pi`
3. Edit Control: select ID `Center` > Replace > Name "Blur Vector", Type Point, Page Controls.
4. Edit Control: `Length`, `Angle` > Hide.
5. Checkbox route: new Name/ID `Centered`, Type Number, Page Controls, Input Ctrl **CheckboxControl**; on `Type` add SimpleExpression `iif(Centered==1, 2, 0)`; then Hide `Type`.
6. MultiButton route: new ID `TypeNew`, Name "Type", Type Number, Page Controls, Input Ctrl **MultiButtonControl**, buttons "Linear", "Centered" (Add each); on `Type` add `iif(TypeNew==0, 0, 2)`; Hide original `Type`.
(Implied by the expressions: Directional Blur Type values 0 = Linear, 2 = Centered.)

---

## Gotchas and non-obvious behavior

- **Merge Background sets output resolution.** Wiring a small graphic to BG crops the whole comp to it (p. 135).
- **Mask nodes auto-connect to the Effect Mask**, even on MatteControl where you may want the Garbage Matte (p. 129).
- **Drop order on a node body is fixed**: BG, then FG, then Effect Mask. Use Option-drop for an explicit input (p. 127-128, 135).
- **Deleting a node** reconnects primary in/out only; mask connections are dropped (p. 122).
- **Swap Inputs doesn't move lines**, only changes knot colors; and only swaps FG/BG (p. 139).
- **Renaming silently strips** spaces and special characters; names can't start with a digit. Always read back the actual name before referencing it in expressions/scripts (p. 148).
- **Deinstance (whole node) is one-way**; per-parameter Deinstance is reversible via Reinstance (p. 146).
- **Deleting a normally-selected Underlay deletes all nodes inside it**; Option-click the box first to delete only the box (p. 150).
- **Settings > Reset Default deletes** the custom default `.setting` file (p. 155).
- **Pasting a MediaIn/Loader/Generator after a node auto-builds a Merge** (FG). Disable in Fusion Settings > Defaults > Auto tools if unwanted (p. 141).
- **Selected vs viewed**: onscreen controls come from selection, not the viewed node. Follow Active is off by default (p. 192, 223).
- **Title templates exclude MediaIn/MediaOut; Transition, Generator and Effect templates include them.** Transitions need both MediaIns and the MediaOut and must be saved from Resolve's Fusion page (p. 166, 172, 175, 177).
- **Templates need a full Resolve relaunch** to appear (p. 169, 173, 176, 178).
- **Keyframed templates don't retime on trim** unless you use Resolve Parameter (Scale/Offset), Anim Curves, or Keyframe Stretcher (p. 171, 178).
- **Media drop zones require exporting ClipName** on each MediaIn; multi-layer track remapping requires exporting the MediaIn Layer checkbox (p. 178-179).
- **Deleting a `.drfx` removes every template it contains**; bundles are never unpacked (p. 181).
- **Control order in macros = node selection order** unless rearranged in the Macro Editor preview (p. 167, 173).
- **Update mode off holds a freeze frame**; easy to forget and misdiagnose as a broken node (p. 156).
- **A light viewed alone renders nothing**; view the Merge3D (p. 206). Shadows only after 3D Options > Shadows (which also enables Lighting) (p. 206).
- **Z-buffer transparency can be wrong** with stacked transparent planes; switch the viewer to Quick/Full Sort (viewer display only) (p. 206-207).
- **Copy PoV To ignores downstream transforms** (object's own coordinate space) (p. 204).
- **RoI is preview-only**; outputs always render full frame. Changing proxy/size/depth resets outside-RoI pixels (p. 213).
- **Resolve timeline clips have full-frame DoD** (except EXR); use Auto Domain to tighten it (p. 212).
- **Image LUTs don't apply to 3D scenes**; use a Buffer LUT, and disable the LUT button before enabling a Buffer LUT (p. 214).
- **Fusion View LUT curves can't be animated** (p. 215). Macro/node LUTs render on CPU (slow); others are GPU (p. 220).
- **Slider ranges are soft**: typed values beyond max are accepted (p. 236). Macro Editor Minimum/Maximum columns are where you set enforced limits for macro controls (p. 163).
- **Dropdown/checkbox animation values are numeric**: dropdown index starts at 0; checkbox on = 1.0 or greater (p. 237-238).
- **Apply Mask Inverted affects effect masks only**, not garbage masks (p. 234).
- **Blend 0 skips processing**, which breaks stateful nodes unless Process When Blend Is 0.0 is checked (p. 233).
- **Shortcut collisions by context**: Cmd-G = Group (Node Editor) vs Show Guides (viewer); Cmd-F = Find (Node Editor) vs Fit (viewer); Cmd-L = Lock node vs Lock viewer; V = Node Navigator (Node Editor) vs Subview (viewer); Cmd-1 = Node Editor default scale vs viewer 100%.
- Manual inconsistencies to be aware of: Generator section says "enter the name of the Transition" (copy error, p. 176); Effects step says "Create Macros" (menu is Create Macro, p. 177); defaults file named `.settings` vs `.setting` (p. 154).

## Recipes / workflows

**A. Quick composite from a loose node**
1. Drag the FG node's output knot onto the BG node's **output** knot. A Merge is created (FG green, BG orange) (p. 136).
2. If reversed, select the Merge and press Cmd-T (p. 138).

**B. Roto setup with correct viewing**
1. MediaIn > MatteControl; Polygon > MatteControl Garbage Matte (Option-drop to choose the input explicitly; default drop goes to Effect Mask) (p. 123-124, 128-129).
2. Select the Polygon (controls), view the MediaIn (image) with key 1 or 2 on the MediaIn.

**C. Identical grade on several clips, with one exception**
1. Copy the ColorCorrector; Cmd-Shift-V after each target (names become `Instance_...`).
2. On one instance, right-click the differing parameter > Deinstance; Reinstance later if needed (p. 145-146).

**D. Build a reusable macro**
1. Cmd-click nodes in desired control order (exclude MediaIn/MediaOut unless it's a template type that requires them).
2. Right-click > Macro > Create Macro. Enter Macro Name (use `Folder/Name` for .drfx folders).
3. Check Export for each control; set Name, Default, Minimum, Maximum; arrange in the preview; add Separator/Spacer/Nest (Nest Default 1 open, 0 closed).
4. Options > Copy Macro, paste into the Node Editor to test. Adjust originals and use Update from Selected Tools if needed.
5. Set "Save to" (plain .setting or a template category), Close > save. For Add Tool > Macros access, save into the Macros folder (p. 161-165).

**E. Edit-page Title template**
1. Build the title comp in the Fusion page.
2. Select all nodes **except** MediaIn/MediaOut; Macro > Create Macro.
3. Export only editable controls (text, colors, key animation controls). If animated, add Keyframe Stretcher (hold stretches) or Anim Curves to animated params.
4. Save to `.../Fusion/Templates/Edit/Titles` (or "Save to" > Titles). Optional `<SameName>.png` icon, 104 x 58.
5. Quit and relaunch Resolve; find it in Effects Library > Titles > Fusion Titles (p. 166-169, 178-180).

**F. Edit-page Transition template**
1. Apply Fusion Cross Dissolve on the Edit page; right-click > Open in Fusion Page.
2. Rebuild between MediaIn1 (outgoing), MediaIn2 (incoming), MediaOut1. Drive animation with the **Resolve Parameter** modifier's Scale/Offset instead of keyframes so duration follows the edit.
3. Select both MediaIns, the MediaOut and all effect nodes; Macro > Create Macro. Export ClipName on MediaIns for drop zones (optional). Zero exported controls is fine.
4. Save to `.../Templates/Edit/Transitions`; relaunch; find under Video Transitions > Fusion Transitions (p. 170-173, 179).

**G. Edit-page Generator / Effect template**
- Generator: Edit page > Fusion Composition (or Noise Gradient) > Open in Fusion Page; build; select all **including MediaOut**; Create Macro; save to `Generators` (p. 174-176).
- Effect: clip into Fusion; insert effect between MediaIn and MediaOut; select effect node, Cmd-A; Create Macro; export controls; name at top; Close > Yes; save to `Effects` (subfolders allowed); relaunch (p. 177-178).
- Multi-input effect: build in an N-layer Fusion clip; export each MediaIn's Layer checkbox; apply to a Fusion clip with the same number of layers (bottom track = MediaIn1) (p. 178).

**H. Distribute templates as .drfx**
1. Create `Edit/Titles`, `Edit/Transitions`, etc. (and/or `Fusion`), copy `.setting` + `.png` + assets.
2. Zip the top folder, rename `.zip` to `.drfx`.
3. Install: double-click or drag into the Fusion page (p. 180-181).

**I. Compare before/after in one viewer**
1. Load node X into A (`,`), node Y into B (`.`), press `/`.
2. Drag divider (Shift = 45-degree snap); Cmd-Option-click to recenter. Set different LUTs/channels per half (p. 194-196).

**J. Speed up heavy work on a small area**
1. RoI button > Set, draw a box (or Auto for current zoom). Optional: Update off on heavy upstream nodes; Force Cache on a key node (p. 156, 212-213).

**K. Match a Camera3D to the viewer**
1. Navigate the 3D Perspective view (Option+middle-drag rotate).
2. Right-click > Camera > Copy PoV To > your Camera3D (p. 204).

