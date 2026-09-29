<!-- 03-animation-splines-modifiers-expressions.md part 1 of 2; index: 03-animation-splines-modifiers-expressions.md -->
# Fusion Animation: Keyframes Editor, Spline Editor, Motion Paths, Modifiers, Expressions, Custom Controls
Scope: Fusion 21.1 manual pp. 250-325 (Ch. 9-12), plus cross-references marked "xref" to Modifiers ch. 65 (pp. 1761-1800), Text+ modifiers (pp. 1152-1169), Keyframe Stretcher/Time Stretcher (pp. 1366-1380) and Preferences (pp. 366, 386-389). Use when: keyframing, easing, looping, retiming, building motion paths, adding procedural animation (wiggle, loops, links), writing SimpleExpressions or Expression modifiers, customizing Inspector controls, or porting After Effects animation practice to Fusion.

## Mental model

1. **Animation is a modifier.** A keyframed parameter is driven by an animation-spline modifier (Bézier Spline by default for numbers) or a Path modifier (for points such as Center X/Y). Everything that drives a parameter (splines, Path, Perturb, Expression, Publish) lives in the same "Modify With / Connect To / Insert" system and shows in the Inspector's **Modifiers** tab (pp. 274, 315-317).
2. **Default animators by type:** numbers use Bézier Spline; Center/Pivot points use a Polyline **Path** (shape in viewer + Displacement spline for timing). Change in Fusion Settings > Defaults > Default Animate: **Number With** / **Point With** (default "Nothing" = Bézier for numbers, Path for points) (p. 306; xref p. 366).
3. **Auto-key is always on after the first key.** Once a parameter has one keyframe (or has been set to Animate), changing its value at another frame creates a key there (p. 277). No separate record toggle.
4. **Two timing views, one data set.** Keyframes Editor = timeline of segments (node time ranges) plus key ticks; Spline Editor = value-over-time curves with interpolation. Both share markers, filters and autosnap settings (pp. 252, 268, 285).
5. **Interpolation lives on keys.** New Bézier keys have **linear** handles by default; make smooth with Shift-S (p. 283). Step In / Step Out (I / O) make holds (p. 289).
6. **Extrapolation is set per selected segment:** Set Loop, Ping-Pong, Relative Loop (forward), Set Pre-Loop (backward), Gradient Extrapolation (continue the slope), Duplicate (N copies, not live) (pp. 290-292).
7. **Motion paths separate space from time.** A Polyline path's shape (viewer) sets where; its **Displacement** spline (0.0-1.0 along the path) sets when/how fast. XY Path uses separate X and Y splines with no Displacement (pp. 298, 302, 305-306).
8. **Locked vs unlocked points** on Polyline paths: locked = timing keys (have a Displacement point); unlocked = shape-only points (pp. 278, 307-311).
9. **Linking has three strengths:** Connect To (bidirectional, needs the source animated or Published), SimpleExpression/pick whip (unidirectional, editable formula), modifiers like Calculation/Expression/Offset (indirect, with math) (pp. 317, 319-321).
10. **SimpleExpression = one line of Lua** typed after "=" in a number field, with Fusion shorthand (`time`, `self`, `comp`, `Tool.Input`, `iif`, `Point()`, `Text()`) (pp. 319-320).
11. **Expression modifier = separate, non-Lua formula language** (n1..n9, p1x..p9y, degree-based trig, `if()`), cannot read other frames; Calculation modifier can (xref pp. 1765-1776).
12. **Custom controls are per-tool-instance edits** (Edit Controls): renaming keeps the internal ID, so expressions keep working; save settings/macros to reuse (pp. 322-324).

---

## 1. Keyframing in the Inspector (pp. 251-252, 274-275)

| Action | How | Notes |
|---|---|---|
| Add key | Click gray **Keyframe** button right of the parameter | Button turns orange; key at playhead (p. 251). |
| Delete key at playhead | Click the **orange** Keyframe button | Returns to gray (p. 251). |
| Jump to keys | Small arrows left/right of the Keyframe button | Only shown when keys exist in that direction (p. 251). |
| Animate without a key | Right-click parameter > **Animate** | Connects default spline type (Bézier unless changed in Defaults) (p. 274). xref p. 1764: right-click number field > **BezierSpline** adds a key at current frame. |
| Choose spline type first | Right-click > **Modify With** > B-Spline / Cubic Spline / Natural Cubic Spline | Do this before creating keys (p. 275). |
| Remove animation | Right-click the parameter/keyframe control > **Remove [Parameter Name]** | Deletes the spline only if no other parameter is connected to it (pp. 251, 275). |
| Share one curve between params | On 2nd param: right-click > **Connect To** > [animated parameter] | Both follow one curve (p. 252). |

- A keyframed node shows a **Keyframe badge** in the Node Editor when Show Modes/Options is on (p. 251).
- Deleting all keys in the Spline Editor does not remove the spline; use Remove [param] (p. 279).

---

## 2. Keyframes Editor (Ch. 9, pp. 250-266)

Open: **Keyframes** button in UI toolbar or **F7** (p. 252). Undock icon opens it in a resizable window (p. 254).

### Tracks, header, playhead
- One track per clip/effect node, color-coded like the node. Keyframes show overlaid on the node segment (collapsed) or on one sub-track per animated parameter/modifier/mask (disclosure arrow) (pp. 252-253, 256).
- Each track shows a miniature, non-editable curve overlay (p. 256).
- Header per track: name, lock button, disclosure. **Expand/Collapse Tool Controls** in the Option menu opens/closes all (p. 253).
- Playhead is locked to the viewer. You must grab the playhead itself; click-drag elsewhere in the ruler **scales** the timeline. **Cmd-Option-click** in the track area jumps the playhead (p. 253).
- Framing controls: Zoom Height slider, Zoom to Fit button, Zoom to Rect tool, Sort pop-up, Option menu (p. 254).

### Segments (node time ranges) (pp. 255-256)
- Select: click name in header (also selects node + Inspector) or click segment; Cmd-click discontiguous; Shift-click range; Cmd-click to deselect.
- Move: drag segment (changes where the clip starts/ends in the comp).
- Trim: drag segment ends. On Loader/MediaIn = change media in/out. On effect nodes = limits where the effect runs; **outside the trimmed range the node behaves as if disabled** (use to skip processing, e.g. a Defocus animated 80-100 trimmed to start at 80).
- Hold first/last frame (freeze): **Cmd-drag** beyond the first/last frame of a Loader segment.

### Keyframe editing (pp. 256-258)
- Select: click; drag box; Cmd-click discontiguous; Shift-click first and last for range.
- Drag keys left/right to retime. Right-click selected keys for interpolation changes, copy/paste, and new keys.
- **Duplicate keys:** select, then **Cmd-drag** one of them to a new position (same or other track) (p. 257).
- **Time Editor** (bottom right dropdown + field) (p. 257):
  - **Time** (default): type a frame number for the selected key.
  - **T Offset**: offset selected keys by N frames.
  - **T Scale**: scale selected keys (manual text says "enter a frame offset"; Spline Editor equivalent scales relative to the playhead, see 3.5).
- **Time Stretch** tool (lower left): with a range of keys selected, shows a box to squeeze/stretch timing while keeping relative spacing; or enable it and draw a box around keys. Click again to turn off (p. 258).
- **Show Values** (Option menu): editable value fields under each key when tracks/splines are open (p. 258).

### Spreadsheet (pp. 254, 257, 264)
- Toggle with the **Spreadsheet** button; it splits the work area under the Keyframes Editor.
- Click a node name in the header to show its Start/End; click a parameter to show keys: each **column = one keyframe**, rows = Key Frame (time) and value(s). Row names follow tool+input, e.g. `Blur1BlurSize` (p. 254).
- Edit the Key Frame cell to move a key in time; edit value cells for values.
- **Subframe keys:** type decimals, e.g. 10.25, 15.75 (p. 264).
- **Insert a key:** click an empty keyframe cell, type the time, then type the value below (p. 264).
- **Multiple params:** Cmd-click more parameters (even on other nodes) in the header to add them (p. 264).

### Filtering and sorting (pp. 258-261)
- Option menu filters: **Show All**, **Show None**, **Show Tools at Current Time**, plus custom filters (alphabetical). **Show only selected tools** toggles filtering to selected nodes (updates as you select).
- Custom filter: Option menu > **Create/Edit Filters** (opens Fusion Settings > Timeline) > **New** > name > tick node categories/nodes in "Settings for filters" (**Invert All** turns all categories off) > **Save**. Delete: pick in Filter pop-up > **Delete** > OK. Filters apply to Keyframes Editor and Spline Editor (p. 285).
- **Tree Item Order Selection** (right-click a track): **Start**, click items in order (#1, #2...), then **End**; **Restart** / **Cancel**. Root nodes always list first (p. 260).
- **Sort** menu:

| Sort | Result |
|---|---|
| All Tools (default) | All tools, Node Editor scanned left-right, top-bottom |
| Hierarchy | Background-most at top to foreground-most at bottom, following connections |
| Reverse | Opposite of Hierarchy |
| Names | Alphabetical |
| Start | By start time in the comp |
| Animated | Only animated layers; best for retiming several nodes at once |

### Display customizing (pp. 265-266)
- Right-click > **Line Size** (one track) or **All Line Size** (all tracks, incl. audio): Minimum, Small, Medium, Large, Huge.
- Options > **Display Point Values**: keys as points instead of bars.
- **Audio waveforms:** disclose a MediaIn track to see its waveform; scrub slowly over it to hear audio for beat/cue placement. Fusion Studio: expand the Saver track.

### Markers (pp. 261-263; Spline Editor pp. 272-274)
- Resolve timeline markers (Cut/Edit/Fairlight/Color) appear in Keyframes and Spline Editors and are editable in Fusion; edits sync back. Markers on **clips** in the Edit timeline show on MediaIn in the Keyframes Editor but are **not editable** and do not show in the Spline Editor (pp. 262, 272).
- Add: right-click Time Ruler > **Add Marker**. Hover shows frame; drag to move.
- Jump: double-click marker; or right-click marker > **Set Current Time To [frame]** (Spline Editor).
- Rename: right-click > **Rename Guide** (Keyframes Editor) / **Rename Marker** (Spline Editor), or double-click the Name column in the Marker List.
- **Marker List:** right-click ruler > **Show Marker List** or **Shift-G**; floating; double-click/click entry to jump; **Add** button + Time field to add; **Del** to delete; per-marker checkboxes for Spline Editor / Keyframes Editor visibility.
- Delete: drag marker up off the ruler; right-click > **Delete Marker**; select + Delete/Backspace (Spline Editor).
- Spline Editor: Options > **Enable Marker Grab** lets you drag the marker's vertical line.

### Autosnap (pp. 263, 274; xref prefs p. 389)

| Menu (right-click > Options) | Choices | Effect |
|---|---|---|
| Autosnap Points (keys, segment edges) | None / Frame (default) / Field / Guides (Keyframes Ed.) or Markers (Spline Ed.) | None = subframe freedom; Field = 0.5 frame; Guides/Markers = snap to markers |
| Autosnap Markers | None / Frame (default) / Field | Marker placement snapping |

---

## 3. Spline Editor (Ch. 10, pp. 267-295)

Open: **Spline** button in UI toolbar, or right-click a node / Keyframes Editor segment > **Edit Splines** (p. 268). Can also show functions that are not splines (text changes, expressions) (p. 268).

### 3.1 Layout and navigation (pp. 269-272)
- **Header** (left): animated parameters under their tool; status checkbox per spline. **Graph**: X = time, Y = value; red playhead. **Toolbar** (bottom): interpolation, reverse, loop, time stretch, shape box, key markers, Time/Value editors. Status bar shows pointer time/value.
- Two context menus: **Spline** menu (right-click graph) and **Guide** menu (right-click Time Ruler).
- Rename: right-click spline name > **Rename Spline**. Color: click the round swatch or right-click > **Change Color** (p. 270).
- Zoom Height / Zoom Width sliders; **Fit** button; **Zoom to Rectangle** (**Cmd-R**); drag on a ruler to scale that axis; **+ / -** keys; **Cmd + mouse wheel** zooms at pointer; hold middle button + left click (in) / right click (out); middle-drag or scrollbars to pan.
- Spline menu **Scale** submenu: Scale to Fit (**Cmd-F**), Scale to Rectangle (Cmd-R), Default, Zoom In/Zoom Out, **Auto Fit** (refit as splines shown/hidden), **Auto Scroll** (scroll while playing), **Manual** (no auto framing).
- **Options > Fit Times** / **Fit Values**: auto-scale X / Y to the selected spline (all visible splines considered).
- Undock icon opens a resizable window.

### 3.2 Spline types (pp. 275-277; xref pp. 1764-1769, 1784)

| Type (menu) | Behavior | Use |
|---|---|---|
| **Bézier Spline** (default; also context item BezierSpline) | Key + two handles; mix curves and straight lines | Nearly all animation; the only type with handles for custom easing |
| **Modify With > B-Spline** | One control point sets value and smoothness; curve does not pass through the point (xref: a key of 0 can yield 0.33) | Very smooth motion; **hold W and drag left/right** on a point to change tension (works on multiple selected) |
| **Modify With > Cubic Spline** | Passes through points, no handles, always smoothest curve | "Almost never used" |
| **Modify With > Natural Cubic Spline** | Like Cubic but changes stay local (only adjacent tangents affected) | Smooth auto curves with local edits |

- You **cannot copy/paste between spline types** (p. 281).

### 3.3 Creating keys (pp. 274, 277)
- Auto-key: change the value at a new frame once animated.
- Click on the spline in the graph to add a key there.
- **Cmd-K** or right-click > **Set Key**: key at playhead.
- Right-click > **Set Key Equal To** > next / previous: new key holding the neighbor's value (flat hold).

### 3.4 Selecting, moving, deleting, copying (pp. 279-281)
- Select: click or box-drag; **Cmd-click toggles** keys in/out of selection; **Cmd-A** or Select Points > Select All (active splines).
- Move: drag (keys may pass over other keys); **Option-drag** constrains to one axis; **Up/Down arrows** nudge value (amount depends on zoom; **Shift** for larger); **comma / period** nudge time left/right; Time/Value editors for exact numbers.
- Delete: Delete/Backspace (spline remains).
- **Show Key Markers** (toolbar button or Show > Key Markers): colored ticks on the time axis matching spline colors, to retime without touching curves (p. 280).
- Copy/paste:
  - **Copy Points** (Cmd-C) copies all selected; **Copy Value** copies only the point under the pointer without losing the selection.
  - Same spline: copy, click empty graph to deselect, put playhead where wanted, **Cmd-V**, or hover the spline until highlighted > **Paste Points/Value**. Or **Cmd-drag** the selected keys along the spline.
  - Other spline: set source spline to viewed/disabled with its status checkbox, make destination active, select the key to paste at, **Paste Points/Value** / Cmd-V.
  - **Paste with Offset**: dialog adds a Y value to pasted keys (manual says X or Y offset possible; the dialog described takes Y) (p. 281).

### 3.5 Time and Value Editors (toolbar, lower right) (pp. 281-283)

| Field / mode | Behavior | Example from manual |
|---|---|---|
| **Time** | Frame of the single selected key; empty if none or multiple selected | type 12 to move key |
| **T Offset** | Shift all selected keys by +/- N frames | offset 2: frame 10 -> 12 |
| **T Scale** | Scale key times relative to the **playhead** (keys left of playhead scale negatively) | key 10, playhead 5, scale 2 -> key at 15 |
| **Value** | Shows average of selected; typing sets **all** selected to that value | |
| **Offset** (Value Offset) | Add +/- to all selected values | -2: 10 -> 8 |
| **Scale** (Value Scale) | Multiply selected values | 0.5: 10 -> 5 |

### 3.6 Handles, easing, smoothing (p. 283, 294; xref p. 1764-1765)
- Bézier handles are shown only when the key is selected. **New handles are linear.** Right-click > **Smooth** or **Shift-S** to smooth; **Shift-L** / **Linear** for straight.
- Handles are locked together (constant tension through the key). **Cmd-drag a handle** to break it temporarily; right-click > Options > **Independent Handles** makes all handles independent until turned off (also a prefs default, xref p. 386).
- **Ease In/Out** (the "Spline Ease" dialog): select key(s), right-click > **Edit > Ease In/Out** (xref p. 1765: "Ease In/Out...") or press **T**. Number fields appear above the graph; drag or type to set handle **length** for In and Out. **Lock In/Out** button collapses both into one slider. The manual gives no units or value range (p. 294).
- **Smoothing filter (xref p. 1764):** select points > right-click > **Smooth Points -Y Dialog** smooths a spline with a Savitzky-Golay convolution filter (useful on noisy tracked/recorded curves).
- **Reduce Points:** select a range > right-click > **Reduce Points** > drag the slider lower; **100 removes nothing**, lower removes more; keep as low as the shape allows (pp. 283-284).

### 3.7 Interpolation (toolbar: Smooth, Linear, Invert, Step In, Step Out) (pp. 288-289)

| Mode | Key / menu | Result |
|---|---|---|
| **Smooth** | Shift-S / button / context | Slightly extended handles; motion slows through the key (ease) |
| **Linear** | Shift-L / button | Straight line between keys (constant rate) |
| **Invert** | button | Only for non-animated LUT splines (LUT Editor) |
| **Step In** | **I** / button / context | "Value of the previous keyframe holds, then jumps straight to the value of the next keyframe" |
| **Step Out** | **O** / button / context | "Value of the selected keyframe holds right up to the next keyframe" |

- Figure captions on p. 289 describe Step In as holding until the next key and Step Out as switching immediately; the body text above is authoritative. (inference) For an AE-style Hold keyframe on key K, apply **Step Out** to K; verify on the curve.

### 3.8 Reverse, loops, extrapolation (pp. 289-292)
- **Reverse** (button, context, or **V**): mirrors the selected keys horizontally; neighboring points can be affected.
- **Set Loop** (button or context): repeats the selected segment forward to the end of the global range or until another key ends it. Loops are **live**: edit an originating key and repeats update. **Remove:** select the originating keys and click the Loop button again.
- **Ping-Pong**: repeat, reversing every other cycle.
- **Relative Loop**: each repeat starts from the last value of the previous cycle, so values climb steadily (cumulative).
- **Set Pre-Loop** (context): same loop modes but repeating **backward** in time.
- **Duplicate** (context submenu with the same loop modes): asks for a repetition count; repeats are **copies**, not instances (editing the original does not update them).
- **Gradient Extrapolation** (context): continues the trajectory (slope) of the last two keys.

### 3.9 Time Stretching and Shape Box (pp. 292-294)
- **Time Stretching**: select keys > **Modes > Time Stretching** or toolbar **Time Stretch**; two white vertical bars bracket the outer keys; drag to stretch/squash while keeping relative spacing. If nothing selected, drag a rectangle to define bounds. Toggle off with the same button/menu.
- **Shape Box**: select keys > **Modes > Shape Box**, toolbar button, or **Shift-B** (toggle). White rectangle: drag corner/edge handles to scale, skew, stretch in time **and value**; drag box edges to move all keys. Drag a new rectangle anytime.

### 3.10 Import/Export splines (.spl, ASCII) (pp. 294-295)
- Export: right-click active spline > **Export** > **Samples** (a key every frame, accurate), **Key Points** (key positions/values, linear interpolation), or **All Points** (exact keys and interpolation as seen) > save `.spl`.
- Import: add an animation spline to the parameter first, right-click it > **Import Spline** > choose `.spl`. **Replaces** existing animation.

### 3.11 Header: which splines show and are editable (pp. 284-288)
- Status checkbox cycles **Active** (check: visible + editable) > **Viewed** (solid gray: visible, read-only) > **Disabled** (clear: hidden). Parent node checkbox sets all its splines.
- Options menu (upper right): **Show Only Selected Tool**; **Show All / Show None**; **Expose All Controls** (lists every parameter of every node; clicking one can add a spline to it; slow in big comps, pair with Show Only Selected Tool); right-click > Options > **Follow Active** (header lists all, graph enables only the active tool's splines); custom filters (Create/Edit Filters: New, category/tool checkboxes, **Invert All**, **Set/Reset All**, Save); pick a filter by name; **Show All** to clear.
- Selection states: **Select All Tools**, **Deselect All Tools**, **Select One Tool** (toggle; clicking one checkbox activates only that spline).
- Selection groups: right-click > **Save Current Selection** (name it); reapply via **Set Selection**; rename/delete from the same menu.

### 3.12 Relevant preferences (xref pp. 366, 386-389)
- Spline Editor Options: Independent Handles, Follow Active, Show Key Markers, Show Tips, Autosnap Points, Guides, Autosnap Guides, Autoscale / Scroll / Fit.
- Splines: **Autosmooth** (auto-smooth new keys on animation splines, B-Splines, polyline mattes, LUTs, paths, meshes), **B-Spline Modifier Degree** (Cubic or Quadratic), B-Spline Polyline Degree, Tracker Path (Bézier default; B-Spline or XY Spline), Polyline Edit Mode on Done.
- Timeline: Filter / Filter to Use, Settings for Filters (New, Copy, Delete), Timeline Options defaults, **Tools Display Mode** (default sort).
- Defaults: Default Animate **Number With** / **Point With** (lists installed modifiers valid for the type, incl. third-party).

---

## 4. Motion Paths (Ch. 11, pp. 296-313)

### 4.1 What can take a path (p. 297)
Path modifiers attach to point (X/Y) parameters: Transform/DVE/Merge **Center X/Y**, Paint Stroke Controls > Center X/Y, Camera 3D and Shape 3D **Translation X/Y/Z**, Directional Blur Center, Hot Spot Primary Center, Rays Center, Polygon/BSpline/Ellipse/Rectangle/Triangle mask Center, Corner Positioner corners, Vortex Center (list "not limited to"). **One-dimensional values (blur strength, merge angle) cannot take a motion path** (p. 298).

### 4.2 Path types (p. 298)

| Type | Splines | Timing control |
|---|---|---|
| **Polyline path** (default "Path" modifier) | Shape polyline in viewer + **Displacement** spline in Spline Editor | Displacement 0.0-1.0 = position along path; speed decoupled from shape |
| **XY Path** | Separate X and Y splines | Speed tied to key timing; no Displacement |
| 3D motion paths | Positional controls in 3D scenes | n/a in this chapter |

Convert: right-click the path in the viewer > **Path#: Polyline > Convert to X/Y Path** (p. 278); XY and Poly paths convert both ways from the context menu without redoing animation (p. 306).

### 4.3 Creating a Polyline path (pp. 298-301)
1. **Keyframe method:** at start frame click the Center X/Y **Keyframe** button (adds the Path modifier in the Modifiers tab), set position; move playhead, change Center (auto-keys a new locked point); refine shape in viewer; adjust speed on the Displacement spline.
2. **Path menu method:** right-click the onscreen center control (or Center X/Y in Inspector) > **Path**; now drag the control without setting a key; move playhead and drag again to add keys. The path can stay open. When done, select a point and press **Cmd-I** (Insert and Modify) to add/modify shape points.
3. **Existing shape as path** (mask or paint stroke):
   1. Draw a Polygon mask (open is fine) or paint stroke; click **Insert and Modify** to leave it open; Shift-S / Shift-L points as needed.
   2. Masks auto-animate their shape: right-click "**Right-click here for shape animation**" at the bottom of the Inspector > **Remove Polygon1Polyline**.
   3. Right-click the same label > **Publish** (paint strokes need **Make Editable** in Stroke Controls first). A Published Polyline appears in the Modifiers tab.
   4. On the Transform that should follow: right-click Center X/Y > **Path**.
   5. Modifiers tab > open **Path1**: Displacement already has an automatic key; click its red Keyframe button to remove it.
   6. Bottom of the Modifiers tab: right-click "Right-click here for shape animation" > **Connect To > Polygon1Polyline**.
   7. Keyframe **Displacement** to move along the path; **Size** scales the whole path.

### 4.4 Path modifier controls (p. 302; xref pp. 1788-1789)
- **Center** (moves whole path, animatable), **Size**, **X Y Z Rotation**, **Displacement** (0.0 start, 1.0 end), **Heading Offset** (adds to auto-orientation), "Right-click here for shape animation" (animate the path shape or connect to masks/paint strokes).

### 4.5 Speed (Displacement) and orientation (Heading) (pp. 302-304)
- Displacement spline = acceleration along the path. Closer keys horizontally = faster; longer flatter curve = slower; drag a key up/down to change **where** on the path the object is at that time without changing timing.
- Keyframe it directly: at start set Displacement 0.0 and key; move playhead, drag Displacement to the desired spot, repeat to 1.0.
- **Option-click on the path in the viewer** adds a shape point **without** a Displacement key (reshape without changing speed) (p. 304).
- Last locked point must be **1.0**; you cannot set it to 0.75 (p. 309). Moving the end key in time (e.g. 45 to 50) lengthens the move without changing shape.
- **Auto-orient:** right-click the object's Angle (e.g. Transform Angle) > **Connect To > Path > Heading** (p. 304).
- Perturb on Displacement (via Insert) makes motion jitter back and forth along the path without leaving it (xref p. 1789).

### 4.6 XY Path (pp. 305-306; xref pp. 1799-1800)
- Apply: right-click control or Center X/Y > **Modify With > XY Path**. Animate by moving playhead + dragging.
- Controls: **X Y Z** values (object position), **Center** (whole path), **Size**, **Angle**, **Heading Offset**, **Plot Path in View** (show path). Original Inspector controls act as an offset to the path.
- Viewer points and X/Y spline keys are 1:1 locked; no unlocked points. Advantage: exact XY at exact times, easy single-axis motion.
- Make XY default: Fusion > Fusion Settings > **Defaults** > **Point With** = **XY Path** (p. 306).

### 4.7 Locked vs unlocked points (Polyline paths) (pp. 278, 307-311)

| | Locked | Unlocked |
|---|---|---|
| Created by | Moving playhead + moving the control (keyframing) | Insert and Modify clicks on the path (viewer), or clicking on the Displacement spline (Spline Editor) |
| Viewer look | Larger **hollow** squares | Smaller **solid** squares |
| Spline Editor look | Larger lock icons; move only horizontally (time) | Normal points |
| Has Displacement point | Yes | No |
| Deleting it | Changes overall timing | Changes shape only |

- **Pause on a path:** select a locked point on the Displacement spline, **Cmd-drag** it horizontally; it is copied as an unlocked point (flat hold) (p. 311).
- Toggle: select point(s) > right-click > **Lock Point** (pp. 278, 311).
- Tab cycles controls until the path is selected (p. 310).

### 4.8 Compound, copy, remove, record, save (pp. 311-313)
- **Compound paths** (e.g. figure-eight + forward travel): make path A; draw a smooth polyline mask, Remove its Polygon Polyline animation, Publish it; in the object's Modifiers tab right-click **Path1 Center X/Y > Path** (creates Path2); at bottom of Path2 **Connect To > Polygon: Polyline**; keyframe **Path2 Displacement**.
- Copy / Cut / Paste a whole path: right-click the path header in the Modifiers tab. Paste overwrites the target path.
- Remove: Modifiers tab right-click Path1 header > **Delete**; or right-click Center X/Y > **Remove Path1**; or viewer control > [Object]: Center > **Remove Path1**. Object and shape stay; animation goes.
- **Record:** right-click path > **Record** > choose data (e.g. **Record Time** with **Draw Append**) to capture position and speed as you draw; clean up on the Displacement spline.
- Save shape: right-click the Mask node header in the Inspector > **Settings > Save As** (`.setting`, includes point animation); load via **Settings > Load** on a new polyline of the same type or drag the `.setting` into the Node Editor. Import also accepts **FXF, SSF, Nuke** shape files.

---

