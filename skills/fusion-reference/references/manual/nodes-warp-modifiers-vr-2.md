<!-- nodes-warp-modifiers-vr.md part 2 of 2; index: nodes-warp-modifiers-vr.md -->
## Warp Nodes (Ch. 64, pp. 1729-1759)

Common ports unless noted: **Input** (orange, the image to warp) and **Effect Mask** (blue, optional). The mask limits the effect to pixels inside it and is **applied after the tool processes**.

**Warp Settings tab (common family, pp. 1757-1759; referenced below, not repeated):**
- Blend (at 0.0 the tool normally skips processing) / Process When Blend Is 0.0
- R/G/B/A channel selectors (usually a post-process copy-back of the original channel)
- Apply Mask Inverted / Multiply by Mask
- Use Object / Use Material with **Correct Edges** (uses the Coverage and Background Color channels) and Object/Material ID sliders with Sample
- Motion Blur, with these sub-controls:
  - **Quality** 2 = 2 samples on either side
  - **Shutter Angle** 360 = one full-frame exposure, >360 allowed
  - Center Bias (for trails)
  - Sample Spread (sample weighting/brightness)
- **Use GPU** (Disable / Enabled / Auto)
- Hide Incoming Connections
- Comments
- Scripts (3 fields that run at render)

| Node | Abbrev | Purpose |
|---|---|---|
| Coordinate Space | CdS | Rectangular ↔ Polar remap |
| Corner Positioner | CPn | 4-corner pin |
| Dent | Dnt | Circular bulge/lens-like dents |
| Displace | Dsp | Map-driven refraction/displacement with emboss light |
| Drip | DRP | Ripples/waves |
| Grid Warp | Grd | Mesh deformation, source→destination grids |
| Lens Distort | Lens | Undistort/redistort lens (3DE models, calibration) |
| Perspective Positioner | PPn | Un-pin (remove perspective) |
| Vector Distortion | Dst | Distort by vector channels (e.g. Optical Flow) |
| Vortex | Vtx | Swirl/twirl |

### Coordinate Space (CdS) (pp. 1730-1731)
Converts an image from rectangular to polar coordinates, or back.
- **Shape**: **Rectangular to Polar** | **Polar to Rectangular**.
- Tunnel effect: animate Text+ moving top→bottom, then CdS Polar to Rectangular. The text appears to come from infinite distance. You may need a Transform flip first.
- Pair idiom: two CdS with opposite Shapes and a **Drip or Transform between them**. This modifies the effect while the image stays the same.
- Mograph backgrounds: Fast Noise → Mosaic Blur → Transform → CdS → **Crop** to set the final resolution.

### Corner Positioner (CPn) (pp. 1732-1733)
Positions an image's four corners interactively, e.g. for sign or screen replacement. Connect the corners to Paths or Trackers for animation.
- **Mapping Type**: **Bi-Linear** = straight 2D warp. **Perspective** = offsets computed in 2D, then mapped into 3D perspective.
- **Corners X and Y**: four points. You can attach any modifier to them.
- **Offset X and Y**: nudges the corners, e.g. when tracker patterns sit off the true corners.
- Workflow: Planar Tracker on the background → create a **Planar Transform** → apply it after the Corner Positioner. The Planar Tracker node can then be deleted (p. 1732).

### Dent (Dnt) (pp. 1734-1735)
A circular deformation like a fish-eye. Every parameter is keyframeable.
- **Type**:
  - **Dent 1**: bulge
  - **Kaleidoscope**: dent, mirrored and inverted
  - **Dent 2**: displacement dent
  - **Dent 3**: deform dent
  - **Cosine Dent**: a fracture to the center
  - **Sine Dent**: smooth and rounded
- **Center X and Y**: default 0.5, 0.5.
- **Size**: animate it to grow the dent.
- **Strength**

### Displace (Dsp) (pp. 1736-1738)
Uses a map image to displace or refract the main image: bevels, heat haze, glass, water, even simple morphs (XY mode).
- Inputs: **Input** (orange, **required**), **Foreground Image** (green, **required**, the displacement map), Effect Mask (blue).
- **Type**: **Radial** pushes pixels in/out from Center. **X/Y** displaces per axis from two channels, which gives more precision.
- **Center**: Radial only.
- **Refraction Channel**: Red/Green/Blue/Alpha/Luminance. In X/Y mode it appears twice, once per axis.
- **Refraction Strength**: Radial. In X/Y mode it becomes separate **X Refraction** and **Y Refraction** sliders.
- **Light Power**: emboss light intensity.
- **Light Angle**
- **Spread**: widens the effect and softens map edges.
- **Light Channel**: Color/Red/Green/Blue/Alpha/Luminance.
- Heat haze / flag wave: use a Fast Noise map and raise its **Seethe Rate** (p. 1736).

### Drip (DRP) (pp. 1738-1740)
Ripples over the whole image that can animate outward.
- **Shape**:
  - **Circular** (default)
  - **Square**
  - **Random**: noise-like, particle-ish
  - **Horizontal**: one-direction waves
  - **Vertical**: one-direction waves
  - **Exponential**: diamond with inverted curved sides
  - **Star**: 8-way symmetric, kaleidoscopic when Phase animates
  - **Radial**: star ripple from a fixed pattern
- **Center X and Y**: default 0.5, 0.5.
- **Aspect**: 1.0 = symmetric. <1 is taller/narrower, >1 is shorter/wider.
- **Amplitude**: ripple height. 0.0 = no effect. The slider max is **10**, and higher values can be typed.
- **Dampening**: amplitude falloff away from center. It limits the affected area.
- **Frequency**: ripple count, 0 to 100 on the slider.
- **Phase**: **animate it** to make ripples emanate from the center.

### Grid Warp (Grd) (pp. 1741-1747)
A 2D mesh deformation. The image is deformed so the **Source** grid matches the **Destination** grid. Uses: reframing areas, adding life to stills, lip/face tweaks.

**Controls tab**
- **Source / Destination**: which grid is active. Only one is shown and edited at a time, and all other controls act on it.
- **Selection Type**:
  - **Selected**: normal polyline behavior.
  - **Region**: points in the magnet area move. Points that enter during the drag are ignored.
  - **Magnetic**: points that enter during the drag are also affected.
  - Region and Magnetic show **Magnet Distance** and **Magnet Strength**.
- **Magnet Distance**: the magnet circle size. **Hold D and drag** to resize it in the viewer.
- **Magnet Strength**: falloff. 0.0 = nothing moves.
- **X and Y Grid Size**: divisions, with vertices at the intersections. **Changing either after edits resets the whole grid.** Set the resolution first.
- **Subdivision Level**: subdivisions between divisions, without extra vertices. Smoother deformation but slower.
- **Center**: moves the grid without disturbing vertex animation. It is invisible while editing; switch to Edit Rect to see it. Connect it to a Tracker to follow a head while you deform the lips.
- **Angle**: rotates the whole grid.
- **Size**: scales the whole grid.
- **Edit buttons**:
  - **Edit None**: hides the controls.
  - **Edit Grid** (default): shows the Grid Warp toolbar.
  - **Edit Rectangle**: grid bounds and Center.
  - **Edit Line**: draw a spline around an organic shape and a grid is auto-built to fit. This reveals **Point Tolerance** (lower = fewer, more uniform vertices), **Oversize Amount** (border around the spline, useful for blending back) and **Snap Distance** (how strongly the spline pulls vertices).
- **Set Mesh to Entire Image**: resizes the grid to the image and **resets all vertex edits**.
- **Copy buttons**: Source→Destination or Destination→Source. Copy after setting the source so the destination starts identical.
- **Right-Click Here for Mesh Animation**: **grids are static by default**. Use this to animate the mesh or connect it to another grid. The grid uses a **Polychange spline**, so moving any point keys **all** points.
- **Right-Click Here for Shape Animation**: Edit Line mode only.

**Render tab**
- **Render Method**: three settings ordered by quality, from **Wireframe** (fastest) to **Render** (default, full quality).
- **Anti-Aliasing**: a checkbox in Wireframe mode. Otherwise a 3-level menu; Low is for setup only.
- **Filter Type**: **Area Sample** (default, good) or **Super Sample** (better, much slower).
- **Wireframe Width**, **Anti-Aliased**: Wireframe mode only.
- **Black Background**: whether pixels outside the grid are black or preserved.
- **Object ID / Material ID**: outputs ID channels.
- **Set Image Coordinates at Subdivision Level**: default on.
- **Force Destination Render**: default on.

**Viewer context menu / toolbar** (for the active grid)
- Modify Only / Done
- Smooth / Linear
- Auto Smooth Points (usually on)
- Z Under / Z Same / Z Over (which overlapping vertices draw on top)
- Select All
- Show Key Points / Handles / Grid / Subdivisions
- Reset Selected Points / Reset All Points
- **Stop Rendering** (freezes rendering while you fine-tune a heavy grid)

### Lens Distort (Lens) (pp. 1748-1751)
Removes or adds lens distortion. Undistort the plate, comp CG/3D on the flat plate, then apply a second Lens Distort with **the same settings** in Distort mode at the end.
- **Mode**: **Undistort** | **Distort**.
- **Edges**: **Canvas** (outside pixels = canvas color, usually black with no alpha) | **Duplicate** (smeared edges; prevents black bleeding into blurs).
- **Clipping Mode**: **Domain** keeps pixels pushed outside the frame for later re-distortion. **Frame** discards them. Use Domain on the undistort pass of a round trip (inference from the description).
- **Output Distortion Map**: outputs pixel locations as a warped screen-coordinate map.
- **Camera Settings**: the Camera 3D options, set manually or **connected to an existing Camera 3D**.
- **Lens Distortion Model**:
  - **3DE Classic Model**: its sliders suit manual eyeballing without imported data.
  - **3DE4 Anamorphic**
  - **3DE4 Radial Fisheye**
  - **3DE4 Radial**
  - **Fusion Division Radial**, **Fusion Radial**: these add a **Calibration** tab.
- **Supersampling [HiQ]**: samples per destination pixel. 1×1 bilinear is usually enough, but strong edge distortion benefits from more.
- **Supersampling Mode [HiQ]**: **Nearest** (crisper, aliased) | **Bi-Linear** (softer).
- **Load Distortion Data**: imports a profile, e.g. from 3D Equalizer.
- **Calibration tab**:
  - **Calibrate Type**: **Checkerboard** (default) | **Lines** (draw lines that should be straight). Pressing **Start Calibration** repeatedly refines, because each run starts from the current parameters.
  - **Calibrate Mode**: **Auto** | **Manual** (you choose the frames).
- Manual method: straighten lines that should be straight, or shoot a full-frame checkerboard on set.

### Perspective Positioner (PPn) (pp. 1751-1752)
The complement of Corner Positioner. It **un-pins** a perspective-distorted area to a flat rectangle, e.g. to paint on a flat texture and then corner-pin it back. Animating the points also gives wobble/warp.
- **Mapping Type**: **Perspective** (strongly recommended) | Bi-Linear (legacy projects).
- **Corners X and Y**: four points. Refine them with the **Top, Bottom, Left, Right** controls.
- **PPn and CPn do not concatenate.** An un-pin/re-pin round trip softens the image (p. 1751).

### Vector Distortion (Dst) (pp. 1752-1754)
Distorts X and Y separately from vector channels.
- Inputs: **Input** (orange, required; its vector channels are used if present), **Distort** (green, optional; **overrides** the input's vector channels), Effect Mask.
- Typical setup: **Optical Flow** node generates the vectors → Dst distorts another plate, which is then comped over.
- **X Channel / Y Channel**: which channel of the Distort (or main) input drives each axis.
- **Flip Channel X / Y**: reverses the direction.
- **Lock Scale X/Y**: a checkbox that toggles one **Scale** slider vs separate Scale X/Y.
- **Scale**: a multiplier on the vector values.
- **Lock Bias X/Y**: separate Bias X/Y.
- **Center Bias**: nudges the distortion along an axis.
- **Edges**: Canvas | Duplicate.
- **Glow**: adds glow to the result.

### Vortex (Vtx) (pp. 1755-1756)
A swirling whirlpool.
- **Center X and Y**: default 0.5, 0.5.
- **Size**: the affected area. Drag the circumference in the viewer.
- **Angle**: amount of rotation. Use the viewer handle or the thumbwheel; higher values swirl more.
- **Power**: higher values make the vortex smaller and tighter.
- Put a **Set Domain** before Vortex on text so swirled pixels outside the text's DoD are not cropped (p. 1755).

---

## VR Nodes (Ch. 63, pp. 1716-1728), brief

Studio-only (Fusion Studio / DaVinci Resolve Studio). Spherical layouts:
- **LatLong**: 2:1 equirectangular. X = 0-360° longitude, Y = -90 to +90° latitude.
- **VCross / HCross**: 6 cube faces in a cross, 3:4 or 4:3, with the forward view at the center.
- **VStrip / HStrip**: 1:6 or 6:1 strips in the order Left, Right, Up, Down, Back, Front (+X, -X, +Y, -Y, +Z, -Z).
- **VR 180**: 1:1, 180° stereoscopic.
- **Immersive**: Apple Vision Pro format.

Stereo VR = two stacked Lat Long images, one per eye. Headsets (Oculus Rift, HTC Vive) can display spherical video and live 3D scenes. The viewer option menu has **360° View > Immersive**, which decodes Apple Immersive content in 2D viewers (p. 1718). VR 180 support exists across several VR tools (Studio).

| Node | Abbrev | Key controls |
|---|---|---|
| Immersive Patcher | ImP | Inputs: orange Input (immersive or 2D) + **Metadata** input. **Mode** Distort / Undistort; **Rotation**; **Angle of View**. Undistort → fix flat → second ImP Distort → Merge over original. **Both ImPs must share Rotation and Angle of View**; copy-paste the first (pp. 1718-1719). |
| Lat Long Patcher | LLP | **Mode**: **Extract** (de-warped **90° square** from the lat-long), **Apply** (warps it back and merges **using its alpha**, so paint/text on transparent black can be applied without double-filtering the plate), **Apply180** (VR180). **Rotation Order** (6 orderings, e.g. XYZ = pitch, then yaw, then roll), **Rotation** X/Y/Z dials, **Angle of View**. Use an Extract/Apply pair with the same rotations (pp. 1720-1721). |
| PanoMap | PAM | **From / To**: Auto (from metadata + aspect), VCross, HCross, VStrip, HStrip, LatLong, VR 180, Immersive. **Rotation Order**, **Rotation**. Converts layouts and rotates (pp. 1722-1723). |
| Spherical Camera | 3SC | Lives in the 3D category. Makes the Renderer 3D output all view angles in cube/spherical layouts (skybox, reflection map, headset). Renderer **Image Width** = the size of each cube face (p. 1724). |
| Spherical Stabilizer | - | Single orange input (LatLong, VR180, H/V Cross, H/V Strip). Details below. |

Spherical Stabilizer controls (pp. 1724-1726):
- **Reject Dominant Motion Outliers While Tracking**: default on. It ignores subject motion.
- **Track controls**: Track Backward from End Frame / from Current Time, Stop, Track Forward from Current Time / from Start Frame. (The manual's descriptions of the two Forward buttons appear swapped.) **The stabilization reference frame is the first frame tracked.**
- **Append to Track**: Replace | Append.
- **Stabilization Strength**: 0.0 (no change) to 1.0 (max).
- **Smoothing**: 0.0 = **Still** (removes all rotation and locks the forward view) up to 1.0 = **Smooth** (gentle smoothing for viewer comfort).
- **Offset Rotation** X (pitch) / Y (yaw) / Z (roll): relevel the horizon or reintroduce a pan. It always applies in X, Y, Z order.

VR Settings tab (common family, pp. 1727-1728): Apply Mask Inverted, **Use GPU** (Disable / Auto; the text says three settings), Hide Incoming Connections, Comments, Scripts.

---

## Gotchas and non-obvious behavior

1. **Expression trig is in degrees**, including the inverse functions (p. 1774). `sin(time*50)` advances 50° per frame.
2. **Expression can't read other frames.** For lag, echo or delay, use Calculation or Offset Time tabs (pp. 1766, 1772).
3. **`rand()` changes every frame** and depends on Config > Random Seed. Use `noise()` for smooth motion, and `rands(x,y,s)` for an explicit seed.
4. **Time Offset sign conventions conflict** between Calculation ("+10 = forward", p. 1767) and Offset ("10 is 10 frames back", p. 1787). Test before relying on either.
5. **Connect To lists only animated or published controls.** Publish static controls first (p. 1793).
6. **B-Spline does not hit key values** (a 0 key gives 0.33, p. 1765). Cubic and Natural Cubic splines have no handles.
7. **Shake Min/Max are absolute values, not offsets.** Shake on a Center with 0-1 throws the object anywhere in frame. For jitter around existing animation, use **Perturb** (Insert).
8. **Perturb cannot smooth**, only add jitter. It is the only random modifier that works on polylines, meshes and gradients (p. 1789).
9. **Anim Curves Mirror halves the forward time** (p. 1762). **Time Offset is a fraction of duration, not frames.** Clip Low/High clamp to 0-1 exactly.
10. The manual's bounce recipe says **Scale ".05"** to bounce halfway down (p. 1763). Halfway suggests 0.5; treat 0.05 as a probable typo (inference).
11. **Gradient Color with Start = End = 0 returns the gradient start value** instead of animating (p. 1779).
12. **The Tracker modifier tracks the node upstream of its host by default.** If the host is a Glow or blur, the source is the already-processed image, so set **Track Source** to the clean plate (p. 1797).
13. **MIDI Extractor times are seconds, not frames. Beat mode needs Release > 0** (p. 1783).
14. **Probe Out of Image Value** only kicks in once the **whole** rectangle is off-frame (p. 1793).
15. **Grid Warp:**
    - Changing X/Y Grid Size, or using Set Mesh to Entire Image, **resets all vertex edits**.
    - The grid is **static until you use "Right-Click Here for Mesh Animation"**.
    - Once animated, one point move keys every point (Polychange).
16. **Corner Positioner and Perspective Positioner don't concatenate**, so each pass softens (p. 1751). **Perspective Positioner Bi-Linear is legacy only.**
17. **Displace needs both inputs.** The green map is required, not optional (p. 1736).
18. **Vector Distortion's green input overrides the main input's vector channels** (p. 1753).
19. **Lens Distort round trip:** use identical settings on both nodes. Use Clipping Mode **Domain** to keep pushed-out pixels, and Edges **Duplicate** before blurs.
20. **Vortex/Dent/Drip can push pixels outside the DoD.** Expand it with Set Domain before the warp (p. 1755).
21. **VR patch pairs (ImP, LLP) must share identical Rotation/Angle of View.** Copy-paste the node. LLP Apply composites via the patch's **alpha**.
22. **Spherical Stabilizer's reference frame = the first frame tracked**, and Offset Rotation is always in XYZ order.
23. The **From Image** and **Custom Poly** modifiers are not in Modify With. From Image lives on the Gradient bar right-click, and Custom Poly on shape-animation Insert.
24. **Key Stretcher and Resolve Parameter only matter for templates** used on the Edit/Cut page. Anim Curves' Transition/Duration Source also relies on the comp's Edit page origin.
25. **Menu-label typos to expect:**
    - The Offset Mode list includes "Invert Sugar" (p. 1786).
    - The Expression operator glyphs `*`, `/`, `<`, `<=` are missing in the extracted text, and the `x>=y` rows are duplicated. Use normal math operators.

## Recipes / workflows

**1. Duration-aware scale transition (Anim Curves) (p. 1763)**
1. On the Edit page, add a cross dissolve. Right-click it > **Convert to Fusion Cross Dissolve**, then > **Open in Fusion page**.
2. Add a Transform after MediaIn1 and after MediaIn2.
3. On MediaIn2's Transform, right-click **Size** > **Modify With > Anim Curves**. Size now animates 0→1 over the transition.
4. Do the same on MediaIn1's Transform, then Modifiers tab > **Invert**.
5. Set **Curve = Easing** and try the In/Out types.
6. Make a macro and save it as a Transition template. It retimes when the transition is trimmed.

**2. Bouncing drop on a Path (Anim Curves) (p. 1763)**
1. Keyframe the text Center from top to bottom. This creates a Path.
2. Modifiers tab, right-click **Displacement** > **Insert > Anim Curves**.
3. Set **Source = Duration**, **Curve = Easing**, **Out = Bounce**.
4. **Scale** sets where the bounce lands. The manual says .05 for halfway; 0.5 is likely (inference).
5. **Time Scale 2.0** makes it twice as fast.
6. Save it as a Title macro, and it retimes with clip trims.

**3. Fusion transition template via Resolve Parameter (p. 1794)**
1. Edit page: Effects Library > add a **Fusion Composition** to the timeline and open it in Fusion.
2. Add a **Dissolve** node. Right-click **Background/Foreground** > **Resolve Parameter** (Modifier context menu).
3. Right-click the node > **Macro > Create Macro**. Enable **Output, Background, Foreground**. A transition macro needs **exactly two inputs and one output**.
4. Name it and save from the File menu into:
   - macOS: `$TEMPLATE_MAC_OS_PATH/Transitions` or `$TEMPLATE_MAC_USER_PATH/Transitions`
   - Windows: `$TEMPLATE_WIN_OS_PATH\Transitions` or `$TEMPLATE_WIN_USER_PATH\Transitions`
5. **Quit and reopen Resolve.** The transition appears in Effects Library > Video Transitions > Fusion Transitions.

**4. Inverse-proportional link (Calculation) (pp. 1767-1768)**
1. Comp frames 0-100. Text+ Size keyed **0.05** at frame 0 and **0.50** at frame 100. Add a Blur after it.
2. Blur Size > **Modify With > Calculation**. On the Modifiers tab (F11), right-click **First Operand** > **Connect To > Text 1 > Size**.
3. Set **Operator = Multiply** and **Second Operand = 100**.
4. Time tab: **First Operand Time Scale = -1.0** and **First Operand Time Offset = 100**. The blur now falls as the text grows.

**5. Camera shake on an existing move (Perturb) (p. 1789)**
1. Right-click the animated crosshair > **Insert > Perturb**.
2. Lower **Strength** to taste. **Speed** sets the frequency and **Wobble** the roughness.
3. Change **Random Seed** (or click **Randomize**) for a different take.
4. For jitter along the path only, Insert Perturb on **Displacement** instead.

**6. Settling shake (Shake) (p. 1796)**
1. In the viewer, right-click the Text Center > **Modify With > Shake Position**.
2. Set Smoothness **5.0**, Min **0.1**, Max **0.9**, and keyframe Min/Max at frame 0.
3. At frame 90, set Min **0.45** and Max **0.55**.

**7. Orbit (Vector Result) (p. 1799)**
1. Merge Center > **Modify With > Vector Result**.
2. Set **Distance** to taste.
3. Give **Origin** a path from bottom-left at frame 0 to top-left at frame 100.
4. Key **Angle** at 10 on frame 0 and 1000 on frame 100.

**8. Sign replacement (Corner Positioner) (p. 1732)**
1. Insert: MediaIn2 → **Corner Positioner**. Drag the four corners onto the sign in MediaIn1 (use **Mapping Type = Perspective**).
2. Planar Track MediaIn1 and create a **Planar Transform**. Apply it after the Corner Positioner, then Merge over MediaIn1.
3. Delete the Planar Tracker.

**9. Heat haze (p. 1736)**
1. **Fast Noise** → green input of **Displace** (Type X/Y or Radial). Plate → orange input.
2. Animate/raise the Fast Noise **Seethe Rate**.
3. Keep **Refraction Strength** low. Add **Light Power** for a glassy emboss.

**10. VR cleanup (pp. 1718-1721)**
1. Plate → **LLP Mode = Extract**. Set **Rotation** to aim the 90° window at the rig/tripod.
2. Paint or patch on the flat image, ideally on a transparent layer.
3. Copy-paste the LLP and set **Mode = Apply**, feeding it the patch with the original plate as the base. It merges using alpha.
4. For Apple Immersive, use an **ImP** pair (Undistort → fix → Distort with the same Rotation/AoV) and Merge over the original.

## Scripting and automation hooks

- **Toolbar / Select Tool abbreviations** (also used "in scripting references", p. 1729):
  - VR: `ImP` Immersive Patcher, `LLP` Lat Long Patcher, `PAM` PanoMap, `3SC` Spherical Camera.
  - Warp: `CdS` Coordinate Space, `CPn` Corner Positioner, `Dnt` Dent, `Dsp` Displace, `DRP` Drip, `Grd` Grid Warp, `Lens` Lens Distort, `PPn` Perspective Positioner, `Dst` Vector Distortion, `Vtx` Vortex.
  - No abbreviation is given for Spherical Stabilizer.
- **Registry IDs (for `comp.AddTool`) and modifier IDs (for `AddModifier`) are not stated in this slice.** Read them from a live tool, e.g. `tool:GetAttrs().TOOLS_RegID`, or from a `.setting` copied to the clipboard (inference; verify).
- **Menu labels as the manual prints them** (useful for UI-driven steps and for guessing IDs, but not guaranteed to equal IDs):
  - `BezierSpline`, `B-Spline`, `Natural Cubic Spline`
  - `Anim Curves`, `Calculation`, `CoordTransform Position`, `Expression`
  - `Gradient Color`, `KeyStretcher`, `MIDI Extractor`
  - `Offset` / `Offset Distance`, `Path`, `XY Path`
  - `Perturb`, `Probe`, `Publish`, `Resolve Parameter`
  - `Shake` / `Shake Position`, `Tracker` > `Position` / Tracker Position / Steady Position / Unsteady Position
  - `Vector` / `Vector Result`, `From Image`, `Custom Poly`
- **Expression variables:** `n1`-`n9`, `p1x`-`p9x`, `p1y`-`p9y`, `time`, `pi`, `e`, plus the functions table above.
- **Custom Poly adds:** `px`, `py`, `disp`, `index`, `num`, `getx(disp)`, `gety(disp)`, `getx_at(disp,time)`, `gety_at(disp,time)`, `get2x/get2y`, `get3x/get3y` (and their `_at` forms).
- **Copy-ready Expression snippets** (the syntax is from the manual; the numbers are illustrative, inference):
  - Wiggle-style, Number Out: `n1 + n2*noise(time*n3)`. n1 = base, n2 = amplitude, n3 = speed.
  - Point wiggle, Point Out X: `p1x + n2*noise2(time*n3, 0)`, Y: `p1y + n2*noise2(0, time*n3)`.
  - Cycle every N frames (`loopOut` cycle substitute): `frac(time/n1)`. Or ping-pong: `abs(2*frac(time/n1)-1)`.
  - Clamp: `min(max(x, lo), hi)` (there is no clamp function).
  - Conditional: `if(time > 24, 1, 0)`.
- **Keyboard:**
  - **F11** = Inspector Modifiers tab (p. 1767).
  - **Shift-S** / **Shift-L** = smooth/linear the selected spline points (p. 1764).
  - **W+drag** = B-spline weight (p. 1765).
  - **D+drag** = Grid Warp magnet size (p. 1743).
  - Spacebar = play (p. 1768).
- **Template paths:** `$TEMPLATE_MAC_OS_PATH/Transitions`, `$TEMPLATE_MAC_USER_PATH/Transitions`, `$TEMPLATE_WIN_OS_PATH\Transitions`, `$TEMPLATE_WIN_USER_PATH\Transitions`. Restart Resolve after saving (p. 1794).
- **Preferences:** Global Settings > **Default > Point With** = Path or XY Path. This sets what Animate creates on point controls (pp. 1789, 1800).
- **Settings-tab Scripts:** every tool has 3 script fields that run at render (pp. 1728, 1759).
