<!-- 06-paint-tracking-planar.md part 2 of 2; index: 06-paint-tracking-planar.md -->
## Gotchas and non-obvious behavior

1. **Multistroke and Clone Multistroke can't be edited or tracked after painting.** They default to 1 frame. Set brush, apply mode, and Duration first. To move them over time, group them with Paint Group and track the group (pp. 516, 523) [xref p. 1409].
2. **Stroke, Polyline, and shape strokes last the whole comp by default.** A clone patch painted for one frame persists on every frame until you trim it in the Keyframes Editor or use Limited Duration (pp. 517-518).
3. **Clone source defaults to the Paint node's own input.** With the transparent-Background topology you must drag the plate (or the steadied PlanarTracker) into **Source Tool**. Otherwise you clone transparency (pp. 516, 533). Time Offset cloning and **[ ]** stepping also need a Source node.
4. **The Background feeding Paint must be fully transparent (alpha 0).** Otherwise you paint over a solid color (p. 531).
5. **Strokes are unpremultiplied:** the Alpha slider doesn't change what goes into RGB, but opacity changes all four channels (p. 520).
6. **Write On keys run from the stroke's creation frame to the current playhead**, so place the playhead where the write-on should finish *before* choosing Write On (p. 525). Also, Start/End is described as 0-100% (p. 525) in one place and 0.0-1.0 in another [xref p. 1413]. Check the range before scripting it.
7. **The Tracker analyzes only the background input.** Connecting a foreground changes nothing about the analysis (p. 548).
8. **Track Forward / Track Reverse (the outer buttons) ignore the playhead.** They start at the render-range start or end. Place the pattern box on that frame, or use the "from current frame" buttons (pp. 552, 569).
9. **The tracker's move handle is only the tiny dot at the pattern box's upper-left corner** (pp. 550, 567). The magnified pattern view ignores viewer LUTs, so use a temporary Brightness Contrast for log footage (p. 551).
10. **Every Frame adaptive tracking drifts.** Prefer None or Best Match, and use Every Frame only when perspective or lighting change defeats them (p. 554). Adaptive mode applies to every enabled pattern.
11. **Suspended ≠ Disabled.** Suspended patterns keep and publish their locked data and still feed stabilization and corner pin. Disabled patterns publish nothing (p. 549).
12. **Connecting a Center to `Offset position` snaps the layer onto the track, and its own position is replaced.** Reposition with the **tracker's** X/Y Offset, not the layer's Center (pp. 571-572). (inference) That offset lives on the pattern, so every consumer of that Offset position moves with it.
13. **Steady Angle and Steady Size need at least 2 patterns.** With one pattern only (Un)Steady Position works (pp. 560-561). Steady Size is 1 − (s − 1), not 1/s (p. 561).
14. **Corner and Perspective Positioning auto-add patterns up to 4, and they do nothing with Merge = BG Only** (p. 559).
15. **Stabilizing with the Tracker node means Operation = Match Move + Merge = BG Only.** There is no separate "Stabilize" operation (pp. 556-557). For smoothing rather than lock-off, use Reference = **Start & End** (p. 558).
16. **Planar Tracker reference frame:** the node reference says it **cannot be changed without destroying all tracking data** [xref p. 1592]. The paint chapter's tip about clicking Set mid-track to set a new reference (p. 529) conflicts with that. Treat re-Set as destructive unless you verify otherwise.
17. **Planar Tracker does not save its temporary tracking state.** After a save and reload (including **autosave**), tracking may not be resumable, so finish planar tracking in one session [xref p. 1589].
18. **Steady → Invert Steady resamples the plate twice (softening).** Set Clipping Mode = **Domain** on the steadying tracker so off-frame pixels survive the round trip [xref p. 1595]. Repeated per-frame clone strokes can "bubble," and a single-frame clean plate avoids that (p. 535).
19. **Draw the planar pattern on the reference frame, and don't confuse it with the corner-pin quad** (p. 577). With the **Hybrid** tracker, occlusion masks are nearly mandatory. With **Point**, try without first (p. 578).
20. **Lens distortion is the most common cause of a sliding planar track.** Undistort before tracking (p. 576).
21. **The clean-plate example (pp. 535-539) moves only the Polygon mask.** The frozen patch pixels don't move. (inference) If the subject moves or deforms relative to frame, also transform the masked patch: put the Planar Transform after the MatteControl, or add a second Planar Transform on the patch branch, with the mask drawn on the freeze/reference frame.
22. **Fuse edits don't propagate** until you click Reload or reopen the comp (p. 585). **Resolve FX don't exist in Fusion Studio** (p. 582).
23. **Naming in the manual is inconsistent:**
    - p. 519's "Fill button" is the **Color** apply mode.
    - "Time Stretcher" vs the "Time Remap" caption (p. 535).
    - The Tracker background input is called yellow (Ch. 22) vs orange (node reference).
    - Track-button names differ between pp. 552 and 569.

---

## Recipes / workflows

**R1. Clone out an object on the same frame (pp. 520-521)**
1. Select Paint. In the toolbar, pick **Stroke** for a persistent fix or **Clone Multistroke** for a one-frame fix.
2. Set the brush size (Inspector size slider or Command-drag in the viewer).
3. Set Apply Mode to **Clone**.
4. **Option-click** the source area.
5. Paint over the object. Undo with Command-Z.

**R2. Clone from another frame to reveal the background (pp. 521-523)**
1. Pick a stroke type and set Apply Mode to **Clone**.
2. Drag the MediaIn/Loader into **Source Tool**.
3. Turn on **Overlay** (or hold **O**).
4. Drag **Time Offset** to a frame where the background is revealed.
5. Option-click to align the source.
6. Paint.
7. Turn off Overlay.

**R3. Paint as a separate layer (pp. 515-516, 531-533, 579)**
1. Add a **Background** set to fully transparent (alpha 0). Connect Background → Paint.
2. Connect Paint → Merge **FG**, and the plate → Merge **BG**.
3. For Clone or Smear, drag the plate node into Paint's **Source Tool**.
4. Use Merge Apply modes, or semi-transparent strokes, as needed.

**R4. Track one paint stroke (pp. 525-526)**
1. Paint with **Stroke**, then pick the **Select** tool and box-select the stroke.
2. Right-click its Center > **Stroke1:Center > Modify With > Tracker Position**.
3. In the Modifiers tab, drag the plate into **Tracker Source**.
4. Adjust the pattern box and click **Track Forward**.
5. Nudge with **Tracker 1 X Offset / Y Offset**.

**R5. Track many strokes as one (p. 527)**
1. Select the strokes (box, Shift-click, or Command-click).
2. Click **Paint Group**.
3. In the Modifiers tab, right-click the group's **Center X** label, then use **Connect To** (Tracker node) or **Modify With > Tracker Position**.
4. To edit individual strokes later, use **Show Subgroup Controls**.

**R6. Handwriting write-on (p. 525)**
1. Draw the stroke with **Stroke** or **Polyline Stroke** on the frame where it should start.
2. Move the playhead to the frame where it should finish.
3. Set **Stroke Animation = Write On**. Alternatively, keyframe **End** 0→100 (or 0→1; check the scale).
4. To adjust timing, use the Spline or Keyframes Editor [xref p. 1413].

**R7. Planar steady → paint → unsteady (manual example, pp. 528-535)**
1. Connect MediaIn1 → **PlanarTracker1** (Background input). Operation Mode = **Track**.
2. On the first frame, click **Set**, then draw a polygon over the forehead.
3. Motion Type = **Perspective**. Click Track from First Frame / Track To End.
4. Set Operation Mode = **Steady**. The plate warps so the forehead is pinned.
5. (xref p. 1595) Set Clipping Mode = Domain.
6. Build the paint layer: PlanarTracker1 → **Merge1 BG**. Transparent **Background1** → **Paint1** → Merge1 **FG**.
7. In Paint1, choose **Stroke** and Apply Mode **Clone**. Drag PlanarTracker1 into **Source Tool**. Option-click the source, then paint out the blemishes.
8. Copy PlanarTracker1 and paste the copy after Merge1 (all its tracking data comes with it). On the copy, check **Invert Steady Transform**.
9. (inference, to avoid double-resampling the whole plate) Unsteady only the paint layer: apply the inverting tracker to the Paint branch, or use a Planar Transform on it, then merge over the untouched MediaIn1. See R9.

**R8. Clean plate plus planar-tracked mask (pp. 535-539)**
1. Track the region with PlanarTracker1 on MediaIn1, as in R7 steps 1-3.
2. Branch MediaIn1 → **Time Stretcher**. Disable its default keyframe and enter the freeze frame. The Planar reference frame is a good choice.
3. Connect Time Stretcher → **Paint1**. Clone-paint a single clean frame.
4. Connect Paint1 → **MatteControl1**, and **Polygon1** → MatteControl1 **Garbage Matte** input.
5. On the first frame, draw the forehead shape and raise **Soft Edge** slightly.
6. In MatteControl1 > Garbage Matte, check **Invert**. The patch is otherwise inverted.
7. Connect PlanarTracker1 (still in Track mode, so it outputs the plate) → **Merge1 BG**, and MatteControl1 → Merge1 **FG**.
8. On PlanarTracker1 (Track mode), click **Create Planar Transform**.
9. Shift-drag the new **PlanarTransform1** onto the Polygon1 → MatteControl1 link to insert it. The mask now follows the forehead.
10. PlanarTracker1 is no longer needed for data.
11. See Gotcha 21 about also moving the patch pixels.

Alternate mask route (p. 536): the image goes into a Brightness Contrast node with a Polygon on its effect mask, Alpha enabled and Gain lowered. Or use Channel Booleans to copy the Polygon's channel into alpha.

**R9. Planar match move of a graphic or paint layer (pp. 577-579)**
1. Plate → PlanarTracker (Track).
2. Go to the best frame, click **Set**, and draw the polygon on a plane the foreground won't cross.
3. Optionally connect an occlusion mask to the white input.
4. Go back to the reference frame and click **Track To End**. The node reference adds: click **Go**, then **Track To Start** [xref p. 1591].
5. QC in **Steady** mode, then return to Track.
6. Click **Create Planar Transform**.
7. Connect transparent Background → Paint (or a logo/MediaIn) → **PlanarTransform** → Merge **FG** over the plate.

**R10. Planar Corner Pin (screen or sign replacement) [xref p. 1595]**
1. Track the plane as in R9.
2. Set Operation Mode = **Corner Pin**. The polygon hides and a corner-pin quad appears.
3. Connect the replacement image to **Corner Pin 1** (green). Add more with the **Number of Corner Pins** +/-.
4. Drag the four corners to fit the target. **Show Grid** helps. You can also scrub and adjust (the **Reference Time Positions** are animatable).
5. Set the Merge Mode: BG only / FG only / FG over BG / BG over FG.
6. Play back to confirm it sticks.

**R11. Planar Stabilize (smooth, not lock) [xref p. 1597]**
1. Track a roughly planar region that represents the *camera* motion, for example the road rather than a moving truck.
2. Set Operation Mode = **Stabilize**.
3. Set **Parameters to Smooth** (X/Y Translation, Rotation, Scale), **Smoothing Window** (Box / Gaussian), and **Smoothing Radius (Frames)**. A larger radius gives more smoothing and wider transparent edges.
4. Click **Compute Stabilization**, then review.
5. Set **Frame Mode** = Zoom or Crop, then click **Auto Zoom** / **Auto Crop**.

**R12. Tracker lock-off stabilization (pp. 556-558)**
1. Plate → Tracker (serial).
2. Track 1 pattern for position only, or 2+ same-depth, rigidly related patterns for rotation and scale.
3. Operations tab: Operation = **Match Move**, **Merge = BG Only**.
4. Tick **Position / Rotation / Scaling** as needed.
5. **Pivot Type** = Tracker Average or Selected Tracker.
6. **Reference** = Start, End, or Select Time.
7. Choose **Edges** (Black Edges / Duplicate / Mirror; Wrap is rarely right).

**R13. Tracker smoothing of a shaky move (p. 558)**
Same as R12, but **Reference = Start & End** with Pivot = Tracker Average. Raise **Reference Intermediate Points** to keep more of the original curvature.

**R14. Tracker match move and merge in one node (pp. 544-545, 558-559)**
1. Connect the plate to the Tracker background and the element to the Tracker **foreground**.
2. Track.
3. Set Operation = **Match Move** and **Merge = FG Over BG**. Or use **FG Only** to output just the moved element for further work before a separate Merge.

**R15. Match move via Connect To, text example (pp. 565-572)**
1. Right-click the Node Editor > **Add Tool > Tracking > Tracker**. Drag MediaIn1 onto Tracker1 (branch; background input).
2. Place the pattern on a high-contrast feature.
3. **Adaptive Mode = Every Frame** here, because the drone orbits and perspective changes.
4. Click **Track from First Frame**, then OK in the completion dialog.
5. Double-click the pattern name and rename it, for example "Bridge Track".
6. Text1 > **Layout** panel (second icon). Right-click the **Center X/Y** row > **Connect To > Tracker1 > Bridge Track: Offset position**.
7. Select Tracker1 and raise **Y Offset 1** to place the text above the feature. The dotted red line shows the offset.

**R16. Stabilize → composite → restore motion with published outputs (pp. 561-562)**
1. Track the plate with 2+ patterns (Tracker1, branched).
2. Branch the plate → **Transform1**. Right-click its Center > **Connect To > Tracker1 > Steady Position**. (Supported by pp. 560-561) Also connect Angle → Steady Angle and Size → Steady Size if rotation or scale must be removed.
3. Add the new element, for example corner-positioned, over the stabilized plate with a Merge.
4. After the Merge, add **Transform2** with Center → **Tracker1 > Unsteady Position**. The motion returns with the element attached.
5. (xref p. 1623) Rotation and scale can be restored the same way: script IDs `UnsteadyAngle` and `UnsteadySize` exist. Check the Connect To menu for their UI labels.

**R17. Tracker modifier on a mask (eye glow) (pp. 563-564)**
1. Add an Ellipse over the eye.
2. Right-click its Center > **Ellipse1 Center > Modify With > Tracker Position**.
3. In the Modifiers tab, drag MediaIn1 into **Tracker Source**, then click **Track Forward**.
4. Insert a **Soft Glow** after MediaIn1 and connect Ellipse1 to its white **Glow Mask** input.

**R18. Rescue a track that is occluded or leaves the frame (pp. 554-555)**
- **Occluded:** split the render range, track each side, and let the gap interpolate. Fix nonlinear motion with the path's Insert and Modify modes.
- **Leaves frame:**
  1. Stop and move the playhead to the last good frame.
  2. Set **Path Center = Track Center (Append)**.
  3. Move the pattern to a nearby feature at the same depth.
  4. Track forward from the current frame.

**R19. Install a Fuse (p. 585)**
1. Save the file with the `.fuse` extension into the Fuses path for your app and OS (below).
2. Restart or reopen the comp so the Fuse loads (inference for first install).
3. After editing a Fuse, click **Reload** in its Inspector (or reopen the comp).

---

## Scripting and automation hooks

**Tracker output IDs for scripts and `.setting` connections (manual, node reference p. 1623):**
`SteadyPosition`, `UnsteadyPosition`, `SteadyAxis`, `SteadySize`, `UnsteadySize`, `SteadyAngle`, `UnsteadyAngle`, and per pattern *n*: `Position<n>` (Offset position), `PerspectivePosition<n>`, `PositionX<n>`, `PositionY<n>`, `PerspectivePositionX<n>`, `PerspectivePositionY<n>`, `SteadyPosition<n>`, `UnsteadyPosition<n>`.

(inference) *n* is the pattern's list index, not its renamed display name.

(inference: standard Fusion `.setting` connection syntax. The IDs are from p. 1623)
```lua
Transform1 = Transform {
    Inputs = {
        Center = Input { SourceOp = "Tracker1", Source = "SteadyPosition", },
        Angle  = Input { SourceOp = "Tracker1", Source = "SteadyAngle", },
        Size   = Input { SourceOp = "Tracker1", Source = "SteadySize", },
    },
},
-- follow one pattern instead (Offset position of pattern 1):
-- Center = Input { SourceOp = "Tracker1", Source = "Position1", },
```
(inference) Python/Lua via the API: connect an input to a specific output with `Input:ConnectTo(Output)`, for example `xf.Center.ConnectTo(trk.SteadyPosition)`. Verify with `trk.GetOutputList()` / `xf.GetInputList()` before relying on it. The manual gives **no** input IDs for Paint strokes, Planar Tracker, or Tracker controls, so discover those at runtime rather than guessing.

**Context-menu strings (exact, from the manual):**
- `Stroke1:Center > Modify With > Tracker Position` (p. 526)
- `Ellipse1 Center > Modify With > Tracker Position` (p. 564)
- `Modify With > Tracker Position` works on any center-coordinate control (p. 563)
- `Connect To > Tracker1 > Steady Position` / `Unsteady Position` (pp. 561-562)
- `Transform 1: Center > Connect To > Tracker 1 > Offset Position` (p. 560)
- `Connect To > Tracker1 > <Pattern Name>: Offset position`, for example `Ray Gun Glow: Offset position` (p. 546) and `Bridge Track: Offset position` (p. 571)
- `Connect To > Tracker: Offset Position` (p. 556)
- Viewer right-click > `Tracker1Tracker1Path:Polyline > Convert to XY Path` (p. 547)
- Node Editor right-click > `Add Tool > Tracking > Tracker` (p. 566)
- Polyline Stroke: right-click the `Shape Animation` label > `Connect To` (p. 517)

**Node names used in the chapters:** Paint (Paint category), Mask Paint (Mask category), Background, Merge, Tracker, PlanarTracker, PlanarTransform (node reference abbreviation **[PXF]**, p. 1640; Tracker **[Tra]**, p. 1608), Time Stretcher, MatteControl, Polygon, Ellipse, Soft Glow, Brightness Contrast, Channel Booleans, Lens Distort, Transform, Text (Text1), MediaIn / Loader, DaVinci Resolve Renderer (OFX, Fusion Studio).

**Keyboard and mouse:**
| Keys | Action |
|---|---|
| Command/Ctrl-drag in the viewer | Brush size (pp. 519, 534) |
| Option/Alt-click | Set clone source (p. 520) or pick a color while painting [xref p. 1414] |
| Hold O | Clone overlay, 50% (p. 523) |
| P | Toggle opaque clone overlay [xref p. 1414] |
| Arrows | Move clone source (overlay showing) [xref p. 1414] |
| Option+Left/Right | Clone source angle [xref p. 1414] |
| Option+Up/Down | Clone source size [xref p. 1414] |
| Shift+Command (with the above) | Finer/coarser adjustment [xref p. 1414] |
| [ / ] | Clone Time Offset [xref p. 1414] |
| Shift-drag (Copy Rect/Ellipse) | Constrain shape [xref p. 1414] |
| X / Y | Flip selected stroke [xref p. 1414] |
| Command-drag (Paint Group) | Move the group's crosshair only [xref p. 1414] |
| Shift/Command-click | Multi-select strokes (p. 523) |
| Command-Z | Undo stroke (p. 533) |
| Esc | Stop tracking (p. 552) |
| Shift-drag a node onto a link | Insert it (p. 539) |
| Double-click a tracker name | Rename (p. 549) |

**Preferences and settings:**
- `Tweaks.CloneOverlayBlend`: the O-overlay opacity [xref p. 1414].
- Preferences > Globals > Splines: show tracker X/Y paths instead of the displacement spline [xref p. 1623].
- Global Preferences > Scripting: the text editor used by a Fuse's **Edit** button (p. 585).

**Fuse install paths (p. 585):**
| App | macOS | Windows | Linux |
|---|---|---|---|
| DaVinci Resolve | `/Users/<username>/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Fuses` | `C:\Users\<username>\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Fuses` | `/home/<username>/.local/share/DaVinciResolve/Fusion/Fuses` |
| Fusion Studio | `/Users/<username>/Library/Application Support/Blackmagic Design/Fusion/Fuses/` | `C:\Users\<username>\AppData\Roaming\Blackmagic Design\Fusion\Fuses` | `/home/<username>/.fusion/BlackmagicDesign/Fusion/Fuses` |

**Other files:** DaVinci Resolve Renderer OFX reads a `.DRX` still exported from the Resolve Gallery (pp. 583-584). Image brushes come from the Fusion > Brushes directory [xref p. 1412].
