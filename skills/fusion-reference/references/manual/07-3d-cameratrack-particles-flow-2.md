<!-- 07-3d-cameratrack-particles-flow.md part 2 of 2; index: 07-3d-cameratrack-particles-flow.md -->
## Part 2: 3D Camera Tracker (CTra) (pp. 640-657)

Creates a virtual camera (motion + focal length) and a point cloud from live-action footage by tracking features "nailed to the set" and solving from parallax (pp. 641-642).

**Inspector tabs in order**: Track, Camera, Solve, Export, Options (overlay look) (p. 642).
**Outputs**: primary 2D output (tracking/solving view with toolbar); second 3D output (camera path + point cloud; connect to a Merge3D or Transform3D and view that). 2D track selection and 3D locator selection are synchronized (pp. 644-645).
**Inputs**: Track Mask (white = analyze, black = ignore) (p. 647).

### Shots that fail or need help (p. 643)
| Problem | Action |
|---|---|
| No depth / all one distance, locked-off, tripod nodal pan | No parallax: skip Camera Tracker, use another method |
| No detail (bare greenscreen) | Needs tracking markers on set |
| Heavy motion blur | Try, but know when to quit |
| Rolling shutter | Optionally rebuild frames with Optical Flow to remove wobble, then track the corrected image |
| Overlapping depths create false corners | Delete those trackers before solving |
| Moving objects (people, cars, water, clouds) | Mask them out via Track Mask |

Alternatives: 3D Equalizer, PFTrack; import their camera into Camera3D (p. 643).

### Track phase (pp. 646-648)
- Tracking points are fully automatic. **Detection Threshold** and **Minimum Feature Separation**: lower both to get more points (too many = redundant, slow).
- **Preview AutoTrack Locations**: shows green candidate points while playing.
- **Bidirectional Tracking**: forward then reverse pass to extend tracks; "very little reason not to have this enabled."
- **New Track Defaults** algorithm: **Optical Flow** (usually best, unless many criss-crossing objects), **Tracker** (second choice when criss-crossing causes motion-estimation errors), **Planar** (simple clips dominated by planar surfaces like building facades).
- Masks can be rough. For moving occluders, animate the mask with Tracker or Planar Tracker; after PlanarTracker/PlanarTransform, pass it through a **Bitmap** node to turn it back into a mask before Track Mask.

### Camera phase (pp. 648-649)
- Set **Film Gate** (at minimum the correct camera model) and **focal length**. Wrong film gate makes correct focal length solving very unlikely; focal length far off can make the solver fail to converge (p. 650).
- Metadata: in Resolve, select the MediaIn, Metadata Editor > Camera preset; in Fusion Studio, viewer metadata subview.
- The Camera tab has no "run" button; configure, then go to Solve.

### Solve phase (pp. 649-653)
Iterate: **Solve** -> filter/delete bad tracks -> re-solve.
- **Average Solve Error** (reprojection error, pixels) at top of Inspector: target **< 1.0 for HD**, **< 0.5 for 4K**; higher resolution needs lower error (p. 650).
- Good track sets: balanced across depths (not too many on sky/far background), evenly distributed, staggered start/end frames.
- **Seed frames**: Auto Select Seed Frames (default on); manual Seed Frame 1/2 should share many tracks and be far apart in perspective. Only for experienced users.
- **Minimum 8 tracks on every frame** is the mathematical floor; use many more. Deleting too many raises the error (p. 651).
- **Never hand-edit solved camera splines** except as a last resort; fix the 2D tracks instead (p. 651).
- Track colors after solve: **Green** good, **Yellow** moderate (usually OK), **Orange** low (sometimes OK), **Red** no confidence (delete). Keep green + yellow; keep the best orange only if you need track count (pp. 651-652).
- Hover a track for a tooltip with its solve error; **Reprojection Locators** button shows X marks; closer overlap = lower error.
- Delete: tracks on moving objects, parallax/false corners, reflections in windows/water, highlights sliding over surfaces, poorly following tracks; consider deleting locators at wrong Z depth (p. 652).
- Viewer toolbar: **Track Trails** (hide trails), **Darken Image**, **Delete Tracks** (or **Command-Delete**); Command-drag to add/remove discontiguous selections. Delete small groups and re-solve rather than big chunks (p. 653).
- Filters: **Minimum Track Length** (shorter tracks turn red) -> **Select Tracks Satisfying Filters** -> delete via Operations On Selected Tracks; filters also by track error and solve error (p. 653).

### Export phase (pp. 653-657)
The Camera Tracker stores every 2D track in the comp (can exceed 1 GB). Export a "low memory" scene, then delete the Camera Tracker unless you need to re-solve.
1. **3D Scene Transform** menu: set **Unaligned** (Aligned locks orientation/scale).
2. **Ground plane**: go to a frame with many green locators showing ground, drag-select ground marks, Orientation section > **Set from Selection**. No ground visible: set the **Selection** menu to **XY** to use wall points.
3. **Origin**: select one point or a few marks where the scene center should be, Origin section > **Set from Selection**.
4. **Scale**: set scene scale (also to match multiple clips).
5. Set 3D Scene Transform back to **Aligned** (required before export).
6. Click **Export**: creates **Camera 3D, Point Cloud, Ground Plane, Merge 3D, Camera Tracker Renderer** (a normal Renderer3D).
7. View the Merge3D in one viewer and the renderer in another. With the Merge3D selected, a toolbar adds test geometry (image plane, cube) to verify lock. Use the point cloud to place CG.

---

## Part 3: Particle systems (pp. 658-666, node details pp. 1429-1467)

### Architecture
- Minimum: **pEmitter -> pRender**. Toolbar order pEmitter, pMerge, pRender = wiring order (p. 659). All particle nodes start with "p".
- Particle nodes (except pRender) output a particle set, not an image; view the pRender (p. 1429).
- **pMerge** has no parameters; combines emitters into one system (p. 665).
- **Forces**: self-acting rules pDirectionalForce, pFlock, pFriction, pTurbulence, pVortex; geometry-interacting pAvoid, pBounce, pFollow, pKill (use 3D shapes/planes) (p. 664).
- Attach a 2D image (with good alpha) for custom particle shapes (Style = Bitmap); attach Shape3D or other geometry with Region = Mesh to emit from a mesh (pp. 660-661).
- Templates bin has 20+ particle examples (e.g., Blowing Leaves); drag in, view last node (p. 665).

### pEmitter (pEm) tabs (pp. 664, 1429-1434)
| Tab | Contents |
|---|---|
| Controls | Random Seed/Randomize, **Number** (new particles per frame), Number Variance, **Lifespan** (default 100 frames) + Variance, Color (Use Style Color / Use Color From Region), Position Variance, **Temporal Distribution** (At The Same Time; Randomly Distributed; Evenly Distributed subframe births), **Velocity** + Variance, Inherit (emitter velocity; 1 = match, 2 = ahead, negative = opposite), **Angle / Angle Variance, Angle Z / Angle Z Variance** (direction and spread), Rotation Mode (Absolute / Relative To Motion), Rotation XYZ + Variance, Spin XYZ + Variance (degrees per frame) |
| Sets | Assign particles to numbered sets so other particle nodes can target them |
| Style | Particle look (below) |
| Region | Emission shape, volume vs surface, Translation/Rotation/Pivot (animatable); Winding Rule / Winding Ray Direction for non-closed meshes that "leak" particles. 2D pRender emits on a flat Z plane |

Key numbers: Number 1 = one particle per frame; to emit 25 total, keyframe Number 5 on frames 0-4 then 0 (p. 1430). Number Variance > 2x Number can yield zero on some frames. **Velocity 10 crosses the full image width in one frame; 1.0 takes 10 frames** (p. 1431). Same settings + same seed = identical system.

### Styles (Style tab, pp. 1461-1466)
| Style | Notes |
|---|---|
| Point | 1 px; Apply Mode Add/Merge (2D only); Sub Pixel Rendered |
| Point Cluster | Clusters of points, more efficient for huge counts; Number of Points + Variance; Size = density |
| Bitmap | Image input; keep small and square (e.g., 256x256); Animate Over Time: Over Time / Particle Age / Particle Birth Time; Time Offset; Gain. Size 1.0 = bitmap size |
| Blob | Soft spheres; Noise (2D only) |
| Brush | Images from the Brushes directory (Path Maps); Use Aspect From |
| Line | Lines with falloff; pairs with Size to Velocity |

Common style controls: Color Variance (Lock Color Variance), **Color Over Life** gradient, Size + Variance, Size to Velocity, **Size Z Scale** (1.0 realistic, 0 = no perspective, 2 = exaggerated), **Size Over Life** (0-200% over 0-100% life), **Fade In/Out** (fraction of life), Merge controls (Subtractive/Additive, Burn-In), Blur/Blur Over Life/Z Blur/DoF Focus. **Merge and Blur controls have no effect on 3D particle systems.**
Conditions tab (all particle nodes): **Probability** (per particle per frame), **Start/End Age** (fraction of life), **Set Mode** (Ignore Sets / Affect Specified Sets / Ignore Specified Sets) (p. 1467).

### pRender (pRn) (pp. 661-662, 665, 1447-1451)
- Inputs: orange (particles only), green Camera (Camera3D or scene with camera; frames particles in 2D or 3D), blue Effect Mask.
- **Output Mode 2D / 3D** at top of Controls. The reference chapter says default is 3D. Connecting to a Merge3D **locks** it to 3D (particles can be lit, shadowed, interact with 3D). Ch. 27 warns that once set and any Inspector change is made, you cannot change the mode (p. 662).
- **In 3D mode only Restart, Pre-Roll, Automatic Pre-Roll, Sub-Frame Calculation Accuracy and Pre-Generate Frames have any effect**; everything else is 2D-only (p. 1449).
- **Pre-Roll**: particles depend on previous frame state; jumping frames without pre-roll gives wrong results. **Automatic Pre-Roll** (recommended for light systems; manual for heavy/long ones). **Restart** starts the sim at the current frame.
- **Pre-Generate Frames**: simulate N frames before the first frame (e.g., chimney smoke already present).
- **Sub-Frame Calculation Accuracy**: subsamples per frame; also governs pEmitter subframe births.
- Only Render in Hi-Q (Point proxies otherwise), View (Scene Perspective / ortho; ignored if camera connected or 3D mode), Blur/Glow/Blur Blend (2D, same as a Blur after), Kill Particles That Leave the View, **Generate Z Buffer** (for Depth Blur/Fog/Z merge; can be much slower), Depth Merge Particles.
- Tabs: Controls, **Scene** (transform whole system; **Z Clip** plane in front of camera), **Grid** (non-rendering 2D-in-3D guide), **Image** (process mode, resolution, color space).
- In 3D, the Renderer3D renders particles (p. 627); match pRender motion blur settings to the Renderer3D's exactly (p. 739).

---

## Part 4: Optical flow and stereoscopic nodes (pp. 668-679)

### Optical flow concepts
- OpticalFlow analyzes motion between neighboring frames and writes **Vector** (current -> next) and **BackVector** (current -> previous) X/Y vectors (p. 670).
- Used for smooth slow motion, variable retiming, repairing frames, and stereo disparity correction.
- Slow, non-real-time: pre-render OpticalFlow into an **OpenEXR** sequence via Saver (overnight/render farm), then load with vectors in aux channels (p. 672).
- **Method** menu on Optical Flow, Repair Frame, Tween: **Advanced** = GPU algorithm, same as other Resolve pages; **Classic** = older CPU algorithm for compatibility with old comps, maybe better for some Stereo3D work (p. 673).
- Fusion-page stereo nodes are independent of Resolve's other-page stereo tools (p. 670).

| Node (abbrev) | Aux behavior | Purpose |
|---|---|---|
| Optical Flow (OF) | **Generates** Vector/BackVector | Analysis |
| Time Speed (TSpd), Time Stretcher (TST) | Use then **destroy** vectors | Constant / variable retime with Interpolation = Flow; need upstream OpticalFlow or EXR with vectors |
| Smooth Motion (SM) | Passes through / modifies / generates, never destroys | Smooth color, vector or disparity channels |
| Repair Frame (REP), Tween (Tw) | **Construct internally**, then destroy; cannot use input vectors (non-sequential frames) | Tween: in-between of two frames (missing/flawed frame). Repair Frame: fix dust/scratches from neighbors. Computationally expensive |
| Copy Aux (CpA) | Copies aux into RGBA | Viewing, EXR mapping |
| Disparity (Dis) | Generates Disparity | Stereo analysis; L and R to correct inputs |
| New Eye (NE), Stereo Align (SA) | Use then destroy Disparity | Rebuild an eye; vertical align, convergence, eye separation |
| DisparityToZ, ZToDisparity | Pass through / generate, never destroy | Depth conversion |
| Anaglyph (ANA), Combiner (Com), Splitter (Spl), Global Align (GA) | n/a | View anaglyph; stack L/R; unstack; manual shift alignment |

### Channel conventions (pp. 676, 678-679)
- Flow and Disparity are **un-normalized pixel shifts** (breaks Fusion's resolution-independence). Proxied images still store full-size shifts, so scripts/probes must scale by `(image.Width/image.OriginalWidth, image.Height/image.OriginalHeight)`.
- Sequential rule for frames A, B, C: A.Vector = A>B; A.BackVector = zeros; B.Vector = B>C; B.BackVector = B>A; C.Vector = zeros; C.BackVector = C>B. Missing neighbor frames (not on disk or outside a Loader's global range) fill zeros. TimeStretcher and friends assume 1-frame flow; breaking the rule breaks them.
- Disparity: left image maps L>R, right maps R>L; Dleft is approximately -Dright for non-occluded pixels; stores X and Y because rigs are rarely perfectly registered in Y.
- View aux channels via the viewer Channel menu or **CopyAux** (static normalization avoids viewer flicker; can kill aux channels to save cache memory). Memory: float32 1080p RGBA about 32 MB; with all aux channels about 200 MB.
- DoD/RoI is not supported by all Fusion nodes (p. 679).

### Best practices (pp. 677-678)
- Algorithms assume one layer per pixel: semi-transparency (clouds, lens flares), motion blur, and defocused foreground edges confuse flow/disparity and nearby regions.
- **Order**: compute flow/disparity **before** compositing (flares, etc.), **after** L/R color matching or deflicker, and decide deliberately about lens distortion (removing it after disparity bakes distortion into the disparity map). Rule of thumb: only initial color match and lens-distortion removal come first.
- Compute before cropping, then crop flow/disparity with the color; crop black borders away.

### Stereo workflows (pp. 669, 673-678)
- Stereo camera: one Camera3D with Eye Separation / Convergence Distance, or connect a second camera to **RightStereoCamera**. **Stereo Mix** material assigns different textures per eye. Renderer3D **Eye** menu picks the output eye.
- Disparity workflow: L and R into Disparity -> NewEye / StereoAlign directly, or render Disparity to intermediate EXRs and reload for fast interactive work.
- Color match first: Color Corrector (image to change in orange, reference in green) Histogram **Match** + **Snapshot Match Time**, or Color Curves **Match Reference**; need not be perfect.
- **Separate vs Stack**: Stack puts L/R side by side or top/bottom in one double-size image. In Stack mode connect to the Left input and use the Left output; Right ports are hidden.
- Viewing a stereo node always shows the **Left** output; to see Right, attach e.g. a BrightnessContrast to the Right output and view that.
- **Picking** disparity/Z (e.g., in StereoAlign): pick from a node **upstream** of StereoAlign (it destroys Disparity) and from the **left eye**. Workflow: StereoAlign in left viewer, upstream node in right viewer, pick left-eye value in the right viewer. Exceptions: left output of DisparityToZ, left/right outputs of ZToDisparity.

---

## Gotchas and non-obvious behavior
- A 3D output cannot plug into any 2D input; forgetting the Renderer3D is the most common broken tree (p. 596).
- Renderer3D with no camera renders a default perspective view, not your intended framing; the Camera menu Default picks the **first** camera found (pp. 596, 741).
- Lighting must be enabled in the Renderer3D (and separately in the viewer); enabling lighting with no lights gives black objects (pp. 610, 742).
- Pass Through Lights is **off**: lights in an upstream Merge3D will not light downstream geometry (p. 594).
- Transforming an upstream Merge3D never moves downstream sub-scenes; transforming a downstream one moves everything upstream, including lights and cameras (p. 595).
- Navigating a viewer that is looking through a camera or light **moves that camera or light** (p. 601).
- Near/Far Clip values are ignored on a perspective camera until **Adaptive Near/Far Clip** is turned off (p. 690).
- Aperture Width/Height are in **inches**; focal length in mm (pp. 691, 693).
- Camera image-plane distance is set by the Image tab **Depth** slider, not camera Z (p. 695).
- Overscan and Resolution Gate Fit in the Projection tab are not carried from 3D apps; adjust manually (p. 696).
- Soft shadows, alpha-driven and colored shadows, Transmittance and textures above ~8K need the **Software** renderer; DOF, supersampling, wireframe and Cryptomatte need **OpenGL** (pp. 597-598, 617-618, 746).
- Ch. 25 says the spotlight is "the only light that produces shadows" (p. 611), but the same chapter (p. 612) and the light-node chapter (p. 800) say Point and Directional lights also cast shadows with the OpenGL ("Hardware") renderer; trust the newer statement and test.
- Sorted (Accurate) transparency does not support shadows in OpenGL (p. 602).
- OpenGL supersampling does not thicken particles/locator lines; they look thinner at high rates (p. 744). Never anti-alias ID, TexCoord, Normal or vector channels (p. 744).
- Material **Opacity** cannot be mapped; use Alpha/diffuse alpha for mapped transparency (p. 616).
- Reflect alone ignores scene lights; combine it with an illumination model (p. 622). Environment maps never inter-reflect.
- Bump maps must go through a BumpMap node set to the right type; normal maps must be tangent space (p. 624).
- UVMap3D Ref Time locking fails on particles or geometry whose vertex count changes (p. 625).
- Unseen by Cameras objects still cast shadows; invisible (Visible off) ones do not (pp. 627-628).
- Setting Object/Material ID to 0 means "auto-assign"; IDs only land in the image if the renderer's ID output channels are enabled (p. 635).
- Empty render areas have World Position (0,0,0): add a bounding "dark box" before Volume Fog etc. (p. 636).
- FBX Mesh 3D node flattens to one mesh and drops animation; use Import > FBX Scene to keep animation and separate nodes. FBX Exporter drops textures and materials (pp. 629, 716).
- Alembic imports no lights, materials, curves, multiple UVs or velocities; camera stereo is not imported (p. 683).
- Imported scene scale is literal (mm -> units); fix with FBX Mesh Size (p. 629).
- Point Cloud Find is case-sensitive; Rename works on a single point only (pp. 638-639).
- Camera Tracker: fewer than 8 tracks on any frame cannot solve; solve error targets are resolution dependent (HD < 1.0, 4K < 0.5); the 3D Scene Transform must be **Unaligned** to set ground/origin and **Aligned** again before Export (pp. 650-655).
- Camera Tracker comps can exceed 1 GB from stored 2D tracks; export and delete the node (pp. 653, 657).
- pRender in 3D ignores almost all its own controls and all particle Merge/Blur style controls (pp. 1449, 1465-1466).
- Particle sims are stateful; scrubbing without (Automatic) Pre-Roll shows wrong particles (p. 1449).
- pRender and Renderer3D motion blur settings must match exactly (p. 739).
- Flow/Disparity values are pixel shifts, not normalized; TimeSpeed/TimeStretcher, NewEye and StereoAlign destroy the aux channels they consume; Tween/Repair Frame cannot use precomputed vectors (pp. 672, 674, 676).
- Stereo nodes display their Left output only; stacks go into the Left input (pp. 675, 678).

## Recipes / workflows

**A. Minimal lit 3D title (p. 590, 608-610)**
1. Add Text3D; type in Styled Text; open Extrusion and set Extrusion Depth / Bevel.
2. Add Merge3D; connect Text3D. Add Camera3D and SpotLight3D into the Merge3D.
3. Add Renderer3D after the Merge3D. In Renderer3D, turn on Enable Lighting (and Enable Shadows if wanted).
4. View the Merge3D, right-click the axis label > pick the camera to frame. Enable Guides > Frame Aspect (Command-G) to see the true frame.
5. Merge the Renderer3D output over your 2D plate.

**B. Depth of field (p. 608, 745)**
1. Renderer3D > Renderer Type = OpenGL Renderer.
2. Open Accumulation Effects > Enable Accumulation Effects > Depth of Field; set Quality and Amount of DoF Blur.
3. Camera3D > Control Visibility > Focal Plane; set Plane of Focus to the subject distance (green plane). Animate for rack focus.

**C. Soft shadows plus DOF (p. 598)**
1. Duplicate the Renderer3D: one Software (soft shadows, Variable softness) and one OpenGL (DOF).
2. Combine in 2D, or render aux Z from one and use DepthBlur in 2D.

**D. Rebuild Renderer3D passes (p. 740)**
1. Pull the Diffuse, Specular, Ambient, Reflect, Refract, Fog layers; add them together using Merge, MultiMerge or Channel Booleans.
2. Multiply the Shadow layer over the sum. Grade passes individually before combining.

**E. Clean plate via UV render (p. 598)**
1. Project tracked footage onto matching geometry (UVMap3D in Camera mode or Catcher texture projection).
2. Renderer3D > OpenGL UV Renderer; set Image tab resolution and UV Gutter Size > 0.
3. Paint or temporal-median the unwrapped texture in 2D; apply back through Texture2D onto the mesh.

**F. Camera track to CG (pp. 646-657)**
1. Camera Tracker on the plate; mask moving areas into Track Mask (white = keep). Enable Bidirectional Tracking; algorithm Optical Flow (Tracker if criss-crossing motion). Adjust Detection Threshold / Minimum Feature Separation using Preview AutoTrack Locations. Track.
2. Camera tab: correct Film Gate and focal length from metadata.
3. Solve. Delete red tracks, suspicious ones, and short tracks (Minimum Track Length > Select Tracks Satisfying Filters). Re-solve in small steps until Average Solve Error < 1.0 (HD) / < 0.5 (4K), keeping at least 8 (ideally many more) tracks per frame.
4. Export tab: 3D Scene Transform = Unaligned; select ground points > Orientation Set from Selection (XY selection for walls); select origin points > Origin Set from Selection; set Scale; back to Aligned; Export.
5. Connect CG into the exported Merge3D; verify with test geometry; merge the Camera Tracker Renderer over the plate; delete the Camera Tracker node.

**G. Particles in a 3D scene (pp. 661-662, 1447-1451)**
1. pEmitter -> pRender -> Merge3D (locks pRender to 3D) with lights and camera -> Renderer3D.
2. pEmitter: set Number, Lifespan, Velocity, Angle/Angle Variance; Region Mesh with a Shape3D if emitting from geometry.
3. pRender: Automatic Pre-Roll on (light systems), Pre-Generate Frames if the effect must already be running at frame 1; raise Sub-Frame Calculation Accuracy for fast particles.
4. Match pRender and Renderer3D motion blur settings. Add Soft Clip before the Renderer3D for fly-throughs.

**H. Optical-flow slow motion (pp. 672-673)**
1. Loader -> Optical Flow (Method Advanced) -> Saver to OpenEXR with vector aux channels; render.
2. Load the EXRs -> Time Speed (constant) or Time Stretcher (variable) with Interpolation = Flow.
3. Do color matching/deflicker before step 1; add flares and other comp elements after.

**I. Stereo new eye (pp. 675-676)**
1. Color match R to L (Color Corrector Histogram Match + Snapshot Match Time).
2. L and R into Disparity (correct inputs); optionally render to EXR and reload.
3. NewEye or StereoAlign downstream; pick disparity values from the upstream node's left eye.

## Scripting and automation hooks
- **Registry/input IDs**: this slice states none. Node display names and toolbar abbreviations are in the roster table above. Discover real IDs from the live comp before scripting (Fusion scripting API, not from this manual):
  ```python
  t = comp.ActiveTool
  print(t.GetAttrs()["TOOLS_RegID"])
  for inp in t.GetInputList().values():
      a = inp.GetAttrs(); print(a["INPS_ID"], "|", a["INPS_Name"])
  ```
- **Aux-channel scaling for scripts/probes** (verbatim rule, p. 676): multiply Flow/Disparity values by `(image.Width/image.OriginalWidth, image.Height/image.OriginalHeight)` on proxied images.
- **Focal length formula** (p. 691): `angle = 2 * arctan[aperture / 2 / focal_length]`.
- **Normal packing** (p. 623): packed = n * 0.5 + 0.5; unpack with Brightness Contrast or a Custom node.
- **Stereo parallel trick** (p. 696): Convergence Distance = 999999999.
- **Keyboard**: Q/W/E transform modes; Shift-F fit all; F fit selection; D look at selection; Command-G toggle guides; Command-Delete delete tracks (Camera Tracker); Command-click/drag to add/remove track selections; middle-drag pan; middle+left drag or Command+scroll dolly; Option+middle-drag orbit; Option-drag free translate.
- **Menus**: Fusion > Import > FBX Scene / Alembic Scene (Resolve), File > Import > ... (Fusion Studio); viewer right-click > Camera > [name] / Other / Copy PoV To; 3D Options > Lighting / Shadows / Show Matte Objects; Transparency > Z-buffer / Sorted; Guides > Frame Aspect / Show Guides; Point Cloud > Find / Rename / Publish.
- **Preference**: Fusion > Fusion Settings > General > Auto Clip Browse (FBX node opens a file browser on add) (p. 716).
- **Brush directory** for Brush-style particles: Preferences > Path Maps (default Brushes subfolder of the install) (p. 1462).
- **File formats**: camera import .lws, .ase, .ma, .xsi; FBX Mesh reads .fbx (ascii, 5.0 binary), .dxf, .3ds, .obj, .dae; FBX Exporter writes .fbx/.dae; Alembic .abc; aux-channel interchange via OpenEXR + CopyAux.
