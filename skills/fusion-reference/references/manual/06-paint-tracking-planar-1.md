<!-- 06-paint-tracking-planar.md part 1 of 2; index: 06-paint-tracking-planar.md -->
# Paint, Tracker, Planar Tracker, and Plugins (OFX / Resolve FX / Fuses)
Scope: Fusion 21.1 manual pp. 513-585 (Ch. 21 Paint, Ch. 22 Using the Tracker Node, Ch. 23 Planar Tracking, Ch. 24 Open FX/Resolve FX/Fuse Plugins). Where this conceptual slice is thin, short items are cross-referenced from the node-reference chapters (Paint Node pp. 1406-1414, Tracking Nodes pp. 1589-1623, Planar Transform pp. 1640-1641) and tagged **[xref p. N]**. Use when: an agent must plan or build retouch/cleanup paint, point tracking, stabilization, match moves, corner pins, planar tracks, or install/apply plugins, and needs the workflow logic, the exact menu strings, and the traps.

## Mental model

1. **Paint is procedural vector paint.** Each stroke is a live object (a modifier) with its own Brush, Apply, and Stroke controls. You can edit, animate, reorder, or delete it long after painting (p. 514). The exceptions are **Multistroke / Clone Multistroke**: fast, but not editable after painting (p. 516).
2. **Every paint stroke has a duration.** Stroke, Polyline, and the shape strokes default to the entire global range (the whole comp). Multistroke and Clone Multistroke default to **1 frame**, and you must set their Duration *before* painting (pp. 516-518).
3. **The canvas resolution comes from the Paint node's orange Background input.** Paint needs that input (Mask Paint does not). Paint is resolution-independent, but the resolution still matters for tracking (p. 515).
4. **Paint clones from the image connected to its own input unless the Source Tool field names another node.** When you paint on a transparent Background layer, you must put the plate node into Source Tool (pp. 516, 533).
5. **A Tracker node is both analyzer and data container.** It analyzes only its background input. Its tracks are *published*, so any parameter anywhere can use them through right-click **Connect To**, with no pipe in the node tree (pp. 543-546, 548).
6. **The Tracker's Operation menu decides whether the node also transforms or merges images.** None (tracking data only; the default) / Match Move / Corner Positioning / Perspective Positioning. With Match Move plus **Merge = BG Only**, the node stabilizes (pp. 545, 557) [xref p. 1617].
7. **Published outputs are geometric inverses and re-applications.** *Offset Position* is the path plus the user offset. *Steady* outputs are the inverse of the motion and read as identity on the reference frame (0.5/0.5, 0°, size 1). *Unsteady* puts the motion back (pp. 560-562).
8. **Pattern count sets what can be solved.** One pattern gives position only. Two or more give rotation and scale (Steady Angle and Steady Size need at least 2). Corner and Perspective Positioning need 4 (pp. 553, 557, 559-561).
9. **The Tracker modifier** (right-click a point control > **Modify With > Tracker Position**) is a single-pattern tracker stored in the Modifiers tab and auto-wired to that control. It is quick, but it gives one output and cannot do stabilization (p. 563).
10. **The Planar Tracker tracks a flat surface** defined by a polygon drawn on a **reference frame**. The track is stored as a spline of 4x4 matrices. Steady, Corner Pin, and Stabilize all reuse the Track-mode data (p. 575) [xref pp. 1592-1594].
11. **Planar Transform is how you carry a planar track to other layers.** Create it from the Planar Tracker. It applies the tracked perspective to masks or masked images, and it shares the tracker's Track spline (pp. 538, 578) [xref pp. 1640-1641].
12. **Steady → work → Invert Steady** pins a moving surface so you can paint or roto on it, then puts the motion back. It resamples twice (softer image). Repeated per-frame paint can also "bubble," so a **clean plate** (one painted frame, frozen, masked, and tracked back on) is often more reliable (p. 535) [xref p. 1595].
13. **Plugins:** Third-party OFX and all Resolve FX appear in the **Open FX** category of the Effects Library. Resolve FX are not available in Fusion Studio. Fuses are Lua plugins compiled on the fly from `.fuse` files in a Fuses folder (pp. 582, 585).

---

## Paint

### Paint vs Mask Paint (p. 514)
| Node | Library category | Paints on | Needs an input? |
|---|---|---|---|
| Paint | Paint | Any or all channels (it has channel selector buttons) | Yes. The orange Background input sets the canvas. Also has a blue Effect Mask input (p. 515) |
| Mask Paint | Mask | Alpha only (no channel buttons) | No |

The two nodes otherwise share identical parameters.

### Canvas topologies (pp. 515-516, 531, 579)
| Setup | How | Use when | Requirements |
|---|---|---|---|
| Direct | Plate → Paint (Background input) | Quick fixes. Cleanest tree | None |
| Paint as foreground | Background node (fully transparent) → Paint → Merge **FG**, with the plate on Merge **BG** | You want Merge apply/composite modes, semi-transparent strokes, or a paint layer you can transform or track separately | The Background must be fully transparent, or you are painting on a solid color (p. 531). Unless you are just painting Color strokes, put the plate node into Paint's **Source Tool** field so clone and smear have pixels to sample (p. 516) |

### Stroke types (toolbar above the viewer)
The manual counts **ten stroke types plus two tools** (Select and Paint Group) (p. 516). The toolbar order is [xref pp. 1408-1409]: Multistroke (the default selection), Clone Multistroke, Stroke, Polyline Stroke, Circle, Rectangle, Copy Polyline, Copy Circle/Rectangle, Fill, Paint Group.

| Type | Editable after painting | Default duration | Best for | Notes |
|---|---|---|---|---|
| **Multistroke** | No | 1 frame. Set **Stroke Duration** / Duration before painting | Hundreds of strokes per frame: dust, scratches, raindrops, tracking markers | The fastest type. Shows as **one** item in the Modifiers tab however many strokes you paint (pp. 516, 523). Can't be tracked directly, so group it with Paint Group and track the group [xref p. 1409] |
| **Clone Multistroke** | No | 1 frame | Same as Multistroke, for cloning | Comes pre-configured for cloning. Plain Multistroke needs manual clone setup (p. 516) |
| **Stroke** | Yes, fully animatable | Entire global range (edit in the Keyframes Editor) | Cloning, beauty, creative paint, fixes that must hold for the whole shot (pp. 516, 532) | Control points are hidden by default. Stroke Controls > **Make Editable** exposes them (p. 517). Center and rotation are trackable. Slow with hundreds of strokes (p. 517) |
| **Polyline Stroke** | Yes | Entire global range | Drawn click-by-click like a mask or motion path. Paint-on of SVG outlines | Can adopt an existing published polyline (mask or motion path): right-click the **Shape Animation** label in Stroke Controls > **Connect To** (p. 517) |
| **Circle, Rectangle** | Yes | Entire global range | Filled shapes | [xref p. 1409] |
| **Copy Polyline, Copy Circle/Rectangle** | Yes | Entire global range | Cloning a shaped region with an animatable offset | Requires the source node connected to Paint and **Fill Type = Image** (p. 518) |
| **Fill** | Yes | Entire global range | Wand-like flood fill of similar adjacent pixels | Uses the **Color Space** and **Channel** menus [xref pp. 1409, 1412] |

**Multistroke vs Stroke, decision rule:** if it is a static, single-frame fix and you need many strokes, use Multistroke or Clone Multistroke, and set size, apply mode, and duration first because you can't change them later. If the fix must persist across frames, animate, follow a track, or be tweaked later, use Stroke (p. 517).

### Apply modes
The manual says there are **eight** Apply Mode buttons: paint a color, clone, smudge, remove thin wires, and so on (p. 519). By name [xref p. 1412]:

| Apply Mode | What it does |
|---|---|
| Color | Paints solid color strokes. With an image brush, it tints |
| Clone | Copies from an offset position and/or time offset, in the same image or any node in the tree |
| Emboss | Embosses the pixels under the stroke |
| Erase | Reveals the underlying image through all other strokes, without destroying them |
| Merge | Like Color but with no color controls. Best with an Image brush |
| Smear | Smears along the stroke direction and strength |
| Stamp | Stamps the brush and ignores alpha. Good for decals |
| **Wire** | Wire Removal Mode. Removes wires, rigging, and small elements by sampling adjacent pixels and drawing them in toward the stroke |

- Note: p. 519 says to use "the **Fill** button in the row of Apply modes" to paint a solid color. In the Apply Mode row that button is **Color** (p. 516 says "Stroke tool set to Color"). **Fill** is a stroke type.
- Color picking (p. 520): click the swatch (opens the OS picker), drag the Eyedropper into the viewer, or drag inside the color chooser (saturation/luminance) and on the sidebars (hue/transparency).
- **Strokes are unpremultiplied.** The Alpha slider does not change what goes into RGB, but **opacity affects all four channels** (p. 520).
- Brush tips [xref p. 1411]: Soft, Circular, Image (from a node, a clip, or the Fusion > Brushes folder), Single Pixel (no anti-aliasing), Square.

### Brush size
- In the viewer, **Command-drag** (Ctrl on Windows/Linux) to resize the brush. The circle outline shows the size (pp. 519, 534). There is also the size slider in the Brush controls section of the Inspector (p. 520).
- **Size** only applies to Soft and Circle brushes. **Spacing** sets the distance between dabs: raise it for a denser stroke, lower it for a dotted look [xref p. 1413].

### Cloning (pp. 520-523, 533)
- **Option-click** (Alt-click) sets the clone source. A dot/X marks the sample center and the circle shows the brush (pp. 520-521).
- The default source is the Paint node's own input. To clone from another node or another time, **drag that node from the Node Editor into the Source Tool field** in the Inspector. Any node works (p. 533).
- **Time Offset** slider: clone from another frame of the same clip, which is ideal when a moving object reveals the background (pp. 521-522). This needs a node in Source Tool.
- **Overlay** checkbox: superimposes the current and offset frames. **Hold O** for a temporary overlay (p. 523). More overlay keys (P, arrows, [ ]) are in the keyboard table under Scripting hooks.
- **Command-Z** undoes a bad stroke (p. 533).

### Editing and deleting strokes (pp. 523-524)
- Switch to the **Select** tool in the Paint toolbar, then click a stroke or drag a box around it. Shift-click or Command-click to add or remove strokes from the selection (p. 523). [xref p. 1409] Switch to Select when you finish so you don't add strokes by accident.
- **Tools tab** creates new strokes and edits the stroke selected in the viewer. **Modifiers tab** lists every stroke (Stroke1, Stroke2, ...) with the same controls, and each can be animated (pp. 523-524).
- **The Modifiers tab always shows one more stroke than exists.** The extra entry is the "next stroke" whose settings the Tools tab is preparing (p. 524).
- To delete one stroke: Paint node > Modifiers tab > right-click the Stroke header > **Delete**. To delete all strokes on all frames: use the Inspector's reset button (upper right) or delete the Paint node (p. 524).
- Flip a single selected stroke with **X** or **Y** (not multi or polyline strokes) [xref p. 1414].

### Animating strokes (p. 525) [xref p. 1413]
- The keyframe diamond sets a key on the current frame **and enables auto-keyframing for that parameter** (p. 525).
- **Stroke Animation** menu (Stroke and Polyline only). It has six options:

| Option | Behavior |
|---|---|
| All Frames | The default. The stroke shows on all frames |
| Limited Duration | Shows for the number of frames set by **Duration** |
| Write On | Adds two keys: **Start at the frame where the stroke was created, End at the current frame when you pick the menu item**. Reproduces the drawing timing |
| Write Off | The reverse, drawn from end to start |
| Write On Then Off | Both |
| Trail | Start and End animate together, offset by Duration, so a segment travels along the path |

- **Write-On Start / End** are manual controls for the stroke extent. The conceptual chapter describes them in **percent**: Start 50 = the stroke begins mid-path, and End keyed from 0→100 creates a handwriting write-on (p. 525). The node reference describes the same range slider as **0.0-1.0** [xref p. 1413]. (inference: the UI or stored scale may be 0-1, so check the actual range before scripting keys.)

### Tracking strokes (pp. 525-527)
- **Single stroke:** select it with the Select tool, right-click its Center in the viewer > **Stroke1:Center > Modify With > Tracker Position**. Then, in the Modifiers tab, drag the plate (MediaIn) into **Tracker Source**, click **Track Forward**, and fine-tune with **Tracker 1 X Offset / Y Offset** (p. 526).
- **Many strokes on one rigid surface:** select them, then click **Paint Group**. The group gets **Center, Angle, Size** controls. Connect the tracker there by right-clicking the Paint Group's **Center X** label in the Modifiers tab or using the onscreen control. Individual strokes stay editable through **Show Subgroup Controls** (p. 527). Command-drag moves the group's crosshair without moving the group [xref p. 1414].
- This works when all the objects move consistently ("nailed to the set") (p. 527).

### Wire removal
This slice only says an Apply mode removes thin wires (p. 519). The mode is **Wire** [xref p. 1412]: paint along the wire and it pulls adjacent pixels in toward the stroke. For a wire that persists over time, use an editable Stroke or Polyline Stroke so it can be tracked (inference, consistent with pp. 517, 525).

---

## Tracker node (point tracking)

### Which tracker? (pp. 542-543, 575)
| Node | Tracks | Output | Prefer for |
|---|---|---|---|
| Tracker | A small, distinct pattern (point tracking) | 2D path(s) | Position, rotation, and scale follow. Stabilization. Driving any point parameter |
| Planar Tracker | A flat surface | 2.5D (includes perspective). More tolerant of pixels going offscreen or being occluded | Sign or screen replacement, license plates, walls. **Often a better first choice than Tracker Corner or Perspective Positioning** (pp. 542-543) |
| Camera Tracker | Many patterns | A 3D virtual camera | 3D integration (covered in its own chapter) |

### Inputs and topology (pp. 543-545, 548)
- **Background** input (called yellow in this chapter and orange in the node reference) is **the only image analyzed**. The foreground input is ignored during analysis (p. 548).
- The foreground (green) receives the motion when Operation is Match Move, Corner Position, or Perspective Position. The Tracker contains **full Merge functionality**, so it can replace a Merge (p. 545).
- **Serial:** the tracker both tracks and transforms or merges. **Branch** (output left unconnected): a "data repository" for Connect To consumers. Branching is optional, because serial trackers can publish too (p. 543).
- Tabs: **Tracker Control** (patterns and analysis), **Operations** (how the data is used), **Display Options** (onscreen look), plus the common Settings tab (pp. 547-548).

### Tracker List (pp. 548-549)
- **Add** / **Delete** buttons sit above the list. One node can hold many patterns, and each produces its own path.
- Rename a pattern by double-clicking it, typing, and pressing Return. Names appear in Connect To menus, so name them after what they track (pp. 546, 549, 570).
- The checkbox cycles through three states:

| State | Re-tracks when you run a track? | Data available to other nodes? | Used for stabilization / corner positioning? |
|---|---|---|---|
| Enabled | Yes | Yes | Yes |
| Suspended (gray) | No. The data is locked | Yes | Yes |
| Disabled | No, and it creates no path | No | No |

### Pattern box and search area (pp. 549-551, 567)
- The **inner solid box is the pattern**. The **outer dashed box is the search area**. A selected tracker is red and an unselected one is green. The pattern name shows at the bottom right of the search box.
- **Move the tracker only by the tiny handle at the upper-left corner of the pattern box.** It is easy to miss (pp. 550, 567). While you drag, a magnified pop-up with crosshairs helps placement.
- Resizing an edge resizes from the center (p. 550). Fit the pattern to the detail you want: every pixel on the same plane, with no occluding edges in front.
- The magnified view **ignores viewer LUTs**. For log footage, temporarily insert a Brightness Contrast node before the tracker's input to see the detail (p. 551).
- **Search area:** it must exceed the per-frame motion, or the track jumps to the wrong pixels. Bigger is more robust but slower. Shape it to the motion, for example wide but short for horizontal moves (p. 551).

### Choosing patterns (pp. 552-553)
- Look for patterns that are high-contrast, unique, visible through the whole range, and don't change shape. Note the frames with the largest motion so you can size the search area.
- **Channel:** chosen automatically by contrast, clarity, and reliability, and shown as highlighted bars beside the pattern thumbnail. To override, use the buttons under the bars: any color channel, luminance, or alpha. Avoid noisy or grainy channels. Bright-on-dark subjects often track best on luminance.
- **Stabilization patterns:** keep them at the same depth (parallax confuses the math) and fixed relative to each other (four corners of a sign is good; two different people's faces is bad). p. 553 says 2 patterns correct rotation and 3 correct scale, but pp. 557 and 561 say 2 or more are enough for rotation and scale.
- **Pattern Flipbooks:** the left thumbnail is the selected pattern and the right one updates each frame. Play the flipbook after tracking, since jumps indicate errors (p. 553).

### Running the analysis (pp. 551-552, 569)
- First set the **render range** to the frames where the pattern is visible (p. 551). You can't work in the Node Editor while tracking.
- Buttons, left to right (p. 569 naming / p. 552 naming):

| Button | Starts from |
|---|---|
| Track from Last Frame / **Track Reverse** | **The end of the render range, wherever the playhead is** |
| Track Backward / Track Backward from Current Frame | The playhead |
| Stop Tracking | (also **Stop Render** or **Esc**) |
| Track Forward from Current Frame | The playhead |
| Track from First Frame / **Track Forward** | **The start of the render range, wherever the playhead is** |

- Make sure the pattern box is placed correctly on the frame where the track will start (p. 569).
- The result is one keyframe per frame for the Tracked Center X/Y, drawn as a path with tick marks (p. 544). [xref p. 1613] **Frames Per Point** defaults to 1. Use 2 for field-rendered footage.

### Adaptive Mode (p. 554) [xref p. 1614]
| Mode | Behavior | Use |
|---|---|---|
| None | Uses only the pattern from when it was selected | Stable patterns |
| Every Frame | Re-acquires the pattern each frame | Changing perspective or lighting (the drone example uses it, p. 569). Slower and **prone to sub-pixel drift**, so "not recommended unless other methods fail" |
| Best Match | Re-acquires only if the new pattern is close enough to the original (threshold = Match Tolerance [xref p. 1614]) | Transient changes, for example a shadow crossing the pattern |

The Adaptive mode applies to **all active patterns**. To limit it, disable the other patterns before tracking (p. 554).

### Occlusion, patterns leaving frame, offsets (pp. 554-556)
- **Temporarily occluded pattern:** track the before and after ranges separately, and the Tracker interpolates the gap. For nonlinear motion in the gap, select the path and use the viewer toolbar's **Insert** and **Modify** modes to add points (pp. 554-555).
- **Pattern leaves frame:** move the playhead to the last good frame, set **Path Center = Track Center (Append)**, drag the pattern to a new feature nearby at the same depth, and track on from the current frame. The offset is computed automatically, so the path stays continuous (p. 555). The other option is **Pattern Center**, which continues from the new pattern's center and is meant to replace the path [xref p. 1614].
- **Tracker offsets:** **X Offset / Y Offset** (per pattern; the UI shows e.g. "Y Offset 1") give a constant or animated offset from the pattern center. They appear as a dashed/dotted red line in the viewer. You can also use the **Tracker Offset** button in the viewer toolbar to move the path while the pattern stays put. The tracked path itself stays at the pattern center. Consumers pick up the offset through **Offset Position** (pp. 555-556, 572).

### Operation menu and Merge (Operations tab) (pp. 542-545, 556-559) [xref pp. 1617-1622]
| Operation | Does | Min patterns |
|---|---|---|
| **None** (the manual's name for the track-only operation) | Tracks only. The default. Data drives other parameters | 1 |
| **Match Move** | With BG only connected, stabilizes. With FG connected, moves the FG to match | 1 for position, 2+ for rotation and scale |
| **Corner Positioning** | Maps the FG's 4 corners onto 4 patterns (sign replacement) | 4. Patterns are **auto-added** up to 4 |
| **Perspective Positioning** | The inverse: maps the 4 patterns to the image corners, which removes perspective (flatten, then paint, then another tracker adds the perspective back) | 4 (auto-added) |

- Corner and Perspective Positioning show four dropdowns to pick which pattern drives each corner, plus Rotate CW/CCW 90° buttons [xref p. 1622]. **They do nothing when Merge = BG Only** (p. 559).
- **Mapping Type** (Corner Positioning): **Perspective** (preferred) or Bi_Linear (legacy, no perspective correction) [xref p. 1622].
- **Merge menu:**

| Merge | Result |
|---|---|
| BG Only | FG ignored. Transforms the background, so this is **stabilize/smooth** |
| FG Only | Outputs only the transformed FG, so you can grade or modify it before a later Merge (p. 559) |
| FG Over BG | Transformed FG merged over BG using Apply Mode / Operator (same options as the Merge node) |
| BG Over FG | Rare. BG over the moved FG, for example a tracked layer with alpha over a static background |

- **Edges** (revealed borders): Black Edges / Wrap / Duplicate / Mirror [xref p. 1621]. Wrap suits some match moves and rarely suits stabilization (p. 557).
- **Position / Rotation / Scaling** checkboxes choose what gets corrected (p. 557).
- **Flatten Transformation** (Match Move) breaks concatenation and applies the transform immediately [xref p. 1621].
- **Match Move Settings** are always visible, because Steady and Unsteady outputs are always published (p. 557):
  - **Pivot Type:** Tracker Average (the usual) / Selected Tracker / Manual (pp. 557-558) [xref p. 1622].
  - **Reference:** Start / End / Select Time (Custom Time in the node reference, with Set and Go buttons) lock the image to that frame. **Start & End** *smooths* instead: it simplifies the path between its ends, and the **Reference Intermediate Points** slider keeps more of the original curvature (p. 558).

### Published outputs and Connect To (pp. 545-546, 556, 560-562) [script IDs: xref p. 1623]
Right-click a parameter **label** in the Inspector (or a control in the viewer) > **Connect To > Tracker1 > ...**. Every tracker node and every pattern appears there. The Tracker's output does not need to be wired anywhere (p. 546).

| Connect To entry (UI) | Script output ID | What it gives | Default at the reference frame | Needs |
|---|---|---|---|---|
| `<PatternName>: Offset position`, e.g. "Bridge Track: Offset position" | `Position1` (Tracker 1 Offset position), `Position2`, ... | The pattern path **plus** its X/Y Offset. The consumer follows the feature exactly | The tracked position | 1 pattern |
| Steady Position (per node) | `SteadyPosition` | Inverse translation. Stabilizes X/Y | 0.5, 0.5 | 1 |
| Steady Position (per pattern) | `SteadyPosition1`, ... | The same for one pattern | 0.5, 0.5 | 1 |
| Unsteady Position | `UnsteadyPosition`, `UnsteadyPosition1`, ... | Puts the original motion back after steadying | n/a | 1 |
| Steady Angle | `SteadyAngle` | Opposite rotation (15° at frame 10 becomes −15°) | 0° | **2+** |
| Steady Size | `SteadySize` | Counter-scale: result = 1 − (s − 1). For s = 1.15 that gives **0.85**. The manual says "inverse," but this is not 1/s | 1 | **2+** |
| (script-listed only) | `UnsteadyAngle`, `UnsteadySize`, `SteadyAxis`, `PerspectivePosition1`, `PositionX1`, `PositionY1`, `PerspectivePositionX1`, `PerspectivePositionY1` | Unsteady rotation/scale, the steady axis, perspective-offset and 3D-space X/Y variants | n/a | n/a |

- The node-level outputs are computed from **all** patterns using the Match Move Settings (Pivot and Reference). Per-pattern outputs use that pattern only (p. 561).
- The Reference mode (Operation tab) changes the frame on which the Steady outputs equal identity (pp. 560-561).
- **Worked math (p. 562):** a pattern at (0.5, 0.5) on frames 1-2 moves to (0.6, 0.5) on frame 3. A Transform Center connected to Steady Position reads 0.5, 0.5 on frames 1-2 and **0.4, 0.5** on frame 3, pushing the image back.
- **Spline Editor:** tracks show as a **displacement spline** by default. It is good for velocity, but it carries no direction information. To convert it, right-click in the viewer > **Tracker1Tracker1Path:Polyline > Convert to XY Path** (pp. 546-547). [xref p. 1623] Preferences > Globals > Splines shows X/Y paths by default.

### Tracker modifier vs Tracker node (pp. 563-565)
| | Tracker node | Tracker modifier (`Modify With > Tracker Position`) |
|---|---|---|
| Patterns | Many | **One** |
| Source | Its background input | The **Tracker Source** field. Type a node name or drag a node in. It auto-fills with the upstream node if one is connected to the host node (p. 565) |
| Outputs | All the published outputs above | A single value, already connected to the host control |
| Stabilization, corner pin | Yes | No |
| Where the controls are | Its own node | The host node's **Modifiers** tab |

---

## Planar Tracker

### Operation Mode (p. 575) [xref pp. 1591-1592]
| Mode | Does | Notes |
|---|---|---|
| **Track** | Analyzes the plane. The **Create Planar Transform** button is here | The only mode that tracks |
| **Steady** | Warps the plate so the plane is pinned still, ready for paint or roto, then "unsteady" to restore the motion | Also the best **QC tool**: a good track shows the pattern motionless while the frame warps around it (p. 578) [xref p. 1595] |
| **Corner Pin** | Warps an image connected to the **Corner Pin 1** (green) input with the tracked perspective and merges it over the plate | The corner-pin quad is separate from the tracking polygon (p. 577) |
| **Stabilize** | Smooths translation, rotation, and scale while keeping the intended camera move | Smooths only. Steady tries to lock off completely [xref p. 1596] |

**No two modes can be combined.** For example, you can't corner pin and stabilize in one node, or track while in Corner Pin [xref p. 1592].

**Inputs** [xref p. 1590]: Background (orange; the plate to track) · Corner Pin 1..n (green; adding pins adds inputs) · **Occlusion Mask (white; white = ignore)** · Effect Mask (blue).

### Track controls (pp. 529-530, 577-578) [xref pp. 1592-1594]
- **Set** (under Operation Mode) makes the current frame the **reference frame**. Use the frame where the plane is largest, unoccluded, and clearly planar. **Go** jumps back to it.
- **Pattern polygon:** when a Planar Tracker is first created you can draw immediately. Click the corners, then click the first point to close. Any closed polygon works. **It must be drawn on the reference frame** (p. 577).
- **Motion Type:** Translation / Translation, Rotation / Translation, Rotation, Scale / Affine (with skew) / **Perspective**. Start with Perspective. Drop to a simpler model when trackable points cluster on one side or the region is small (p. 530) [xref p. 1593].
- **Tracker** [xref p. 1593]: **Point** is fast and auto-rejects outliers (green = kept, red = rejected), so try it first without a mask. **Hybrid Point/Area** tracks all pixels: it is more accurate and has less jitter or drift, but it is slower, and **an occlusion mask is nearly mandatory** (p. 578).
- **Track Channel:** red / green / blue / luminance.
- Buttons [xref p. 1594]: Track to start, Step to previous frame, Stop, Step to next frame, Track to end, Trim to start, Delete (all data), Trim to end, Show Splines. **Only track to a new frame if the current frame is already tracked or is the reference frame.**
- While tracking, dots appear on trackable pixels and a green progress bar runs along the Time Ruler. **If nothing happens, or it starts and stops, there is not enough detail**, so pick another region (p. 530).

### Steady-mode controls [xref p. 1595]
- **Steady Time:** the frame where the pattern is frozen, usually the reference frame.
- **Invert Steady Transform:** a second, identical Planar Tracker with this checked restores the original motion. Anything placed between the two is locked to the plane. Because the plate is **resampled twice (softer)**, use this only for effects that corner pinning can't do.
- **Clipping Mode:** **Domain** keeps off-frame pixels and **Frame** discards them. **Use Domain on the first (steadying) tracker** in steady→paint→unsteady setups, so the second tracker can map those pixels back into frame.

### Planar Transform node (pp. 538-539, 578-579) [xref pp. 1594, 1640-1641]
- Created (disconnected) by **Create Planar Transform** on the Planar Tracker in Track mode. The tracking data is embedded, and the node can be cut and pasted into other comps.
- It **shares the Track spline**, so re-tracking in the Planar Tracker updates it automatically [xref p. 1641]. After creating it, the Planar Tracker "can be disconnected or deleted" (p. 538).
- Inputs: orange Image input (a mask, a masked image, or a paint layer) and a blue Effect Mask. Its control is **Reference Time** (from the source tracker).
- Use it for anything that isn't a full-frame plate matching the raster: masks, roto, paint layers, logos [xref p. 1594]. Roto aid: connect a Polygon into the Planar Transform, roto while viewing the Planar Transform, and the polygon follows the plane approximately. Then refine [xref p. 1640].

### Choosing planes, and lens distortion (pp. 575-576, 580)
- The region should be physically planar ("approximately planar" degrades quality). It should also be:
  - as large and as in-frame as possible;
  - unoccluded;
  - at its maximum size (pick the frame where it is 400×200 px rather than 80×40);
  - as face-on as possible.
- Too few pixels leads to jitter, wobble, and slippage.
- **Lens distortion makes planar tracks slide and wobble.** Insert **Lens Distort** between the plate and the Planar Tracker. It can import lens data from SynthEyes, PFTrack, or 3D Equalizer. In Resolve, the **Lens Corrections** control on the Cut or Edit page (**Analyze** sets the **Distortion** slider) carries through to the Fusion MediaIn (p. 576).
- Know when to give up and fall back to the Tracker node or manual keyframing, because no tracker is a 100% solution (p. 575).

---

## Open FX, Resolve FX, Fuses (pp. 581-585)
- **OFX:** third-party plugins (BorisFX, Red Giant, RE:Vision...) work in Fusion Studio and in Resolve's Fusion page. They appear in the Effects Library **Open FX** category (p. 582).
- **Resolve FX:** Fusion page only (**not in Fusion Studio**). They are also in the Open FX category. Some are specific to the Color page and need the **Color page tracker** for full functionality (p. 582).
- **Apply either kind:** click it in the Effects Library, or drag it onto a connection line to insert it. Settings are in the Inspector (p. 582).
- **DaVinci Resolve OFX Renderer (Fusion Studio)** (pp. 583-584): this makes an installation of Resolve Studio behave like one large OFX plugin that applies a grade from a **.DRX** Gallery still.
  - Install it with Resolve Studio's **Custom Install** by checking "DaVinci Resolve Open FX Renderer".
  - Grade in the Color page, save a Gallery still, and export a .DRX.
  - In Fusion Studio, insert the DaVinci Resolve Renderer node and pick the .DRX in its Inspector.
  - Transfers: all native color palettes (Primaries, HDR, Curves...), all sizing palettes (Input, Output, Node), most Resolve FX, and most third-party OFX. **Does not transfer:** temporal Resolve FX or OFX, and **Magic Mask**.
- **Fuses** (p. 585): Lua plugins compiled on the fly, with no dev environment needed. They are slower than equivalent C++ SDK OFX but still use Fusion's nodes and GPU acceleration.
  - Save them with the `.fuse` extension in the Fuses folder (paths under Scripting hooks).
  - The Inspector's **Edit** button opens the file in the editor set in **Global Preferences > Scripting**.
  - **Saved edits don't update existing instances** until the comp is reopened or you click the **Reload** button in the Inspector.

---

