<!-- nodes-tracking-transform-usd.md part 2 of 2; index: nodes-tracking-transform-usd.md -->
## USD Nodes
Fusion imports/authors **Universal Scene Description** (`.usdc`, `.usdz`, `.usda`) — geometry, lighting, cameras, materials, animation — via `u`-prefixed nodes, manipulable/re-lightable/renderable without leaving the 2D tree. Minimal pattern: uLoader → uMerge (+ uCamera/uLights) → uRenderer → MediaOut (p. 1656). **USD Scene Tree dialog** (Pick button on a Prim Selection control): full hierarchy + Type column; Cmd-click multi-selects, Shift-click range-selects (p. 1657).

### uCamera (uCa)
Virtual camera for viewing/rendering the USD scene, modeled on real-camera settings. (p. 1658)
- Inputs: yellow **Scene Input** (optional — **Override Selection > Pick** adjusts an existing camera in the attached scene).
- Setup: connect into a uMerge with the rest of the scene. Viewing uCamera directly shows nothing — view the uMerge (or downstream) and viewer right-click > **uCamera > [name]**, or right-click the axis label. Frame guides: viewer right-click > **Guides > Frame Aspect** (default follows Composition > Frame Format prefs); toggle Cmd-G/Ctrl-G.
- Key controls: **Projection Type**: Perspective vs **Orthographic** (parallel projection; exposes only near/far clip + viewing scale). **Near/Far Clip** (scene units; ignored unless **Adaptive Near/Far Clip** is off; smaller range = better depth accuracy — widen Near Clip if distant objects show artifacts). **Exposure** (auto-fits Near/Far to scene extents per render, overriding manual values; not for orthographic). **Focal Length** (mm; `angle = 2 * arctan(aperture/2/focal_length)`, vertical aperture → vertical FOV, horizontal → horizontal FOV). **Focal Distance** (for DoF). **F Stop** (synthetic aperture; affects exposure and DoF). **Film Back**: Horizontal/Vertical Aperture, **Lens Shift X/Y**, **Shutter Close/Open** (affects exposure and motion blur), **Stereo Role** (left/center/right). **Control Visibility**: Show View Controls (master), Frustum, View Vector, Near Clip, Far Clip, Focal Plane, Convergence Distance (stereo).

### uCatcher (uCa)
Material that "catches" **Texture-mode** projections from a uProjector/uCamera and converts them to a texture map on the geometry it's connected to — the mechanism for Alpha-respecting, re-lightable projections. (p. 1661)
- Inputs: yellow **Scene input** (USD geometry — uShape or uLoader asset).
- Distinction (p. 1661-1662): **Light-mode** projection adds RGB to diffuse of anything in the cone, **ignoring Alpha** (can't clip geometry, e.g. a rotoscoped "windows" mask stays opaque). **Texture-mode**, into a uCatcher wired to a material input (diffuse or otherwise), respects Alpha for clipping, needs no lighting enabled, and can drive non-diffuse channels (specular intensity, reflection, refraction).
- Key controls: **Color Mode** / **Alpha Mode** (how overlapping projectors combine; no effect with one projector). **Threshold** (excludes low values from the accumulation calc). **Restrict by Projector ID** (only receives matching-ID projectors).
- Gotcha: with no active Texture-mode projection hitting it, a uCatcher-connected object is simply transparent/invisible.

### uDuplicate (uDp)
USD equivalent of 2D/3D Duplicate — repeats an asset with successive transforms, optionally jittered/randomized. (p. 1664)
- Inputs: orange **SceneInput** (required); green **MeshInput** (only when Region tab's Region = Mesh).
- Controls tab: **USD Instancing** (reuses USD data per copy for efficiency; disable if copies diverge too much, which can hurt efficiency). **Copies** (range; each copy is copied from the *previous* copy, not the original; First Copy > 0 hides the original). **Time Offset** (offsets source animation per copy, e.g. -1.0 staggers a rotating cube per copy — good for showing successive clip frames on textured planes). **Transform Method**: Linear (each copy independently = copy_number × transform) vs **Accumulated** (each copy starts from the previous copy's result). **Transform Order** (default **SRT** = Scale-Rotation-Transform; order changes final positions). **Translation/Rotation (+ own axis-order buttons)/Pivot/Scale (+ Lock XYZ)** per-copy.
- Jitter tab: **Random Seed** + **Randomize**; **Jitter Probability** (fraction of copies affected); **Time Offset** (jitter-scoped); **Translation/Rotation/Pivot/Scale Jitter** (Pivot Jitter affects only the extra jitter rotation, not base Rotation; Scale Jitter has its own Lock XYZ).
- Region tab: **Region Mode**: Ignore region (default) / When inside region / When not Inside region. **Region**: Cube/Sphere/Rectangle/Mesh (exposes green Mesh input)/All (whole scene — animate Region Mode to pop copies on/off). Mesh region adds **Limit by Object ID** + **Object ID** slider to pick one mesh as the region.

### uExport (uEx)
Exports a USD scene (geometry, materials, animation, lighting) to file, including as a linked hierarchy of USD files. (p. 1669)
- Inputs: one USD scene input.
- Key controls: **Export Stage** (file browser); **Format**: USD (`*.usd`) / USD UTF-8 (`*.usda`) / USD binary (`*.usdc`) / USD packaged (`*.usdz`).

### uImage Plane (uIm)
Flat 2D planar geometry ("card") in 3D space, textured with a 2D image; aspect follows the input image. (p. 1670)
- Inputs: yellow **Input** (image — see shared Image Input behavior below).
- Key controls: **Filename** (Browse, hidden when Image Input is connected); **Size** (plane size in the scene).

### uLoader (uLd)
Imports `.usd/.usda/.usdc/.usdz` files; also loads MaterialX (`.mtlx`) for hand-off to **uReplaceMaterial**. (p. 1671)
- Inputs: none.
- Key controls: **Filename** (Browse); **Trim** (In/Out to import only a range); **Time Scale** (speed up/down animation); **Frame Offset** (shift animation start); **Reverse**; **Loop**; **Reload** (re-reads from disk after external edits).

### uMaterialX (uMX)
Loads a standalone `.mtlx` file, exposing it as USD material(s) — no other inputs. Typical chain: uMaterialX → uReplaceMaterial. (p. 1673)

### uMerge (uMg)
Primary node to combine separate USD elements (geometry, cameras, lights, sub-scenes, other uMerge nodes) into one environment — **and** the parenting mechanism (transforming uMerge transforms everything feeding it). (p. 1674)
- Inputs: **SceneInput[#]** — starts with three, dynamically adds more so one slot is always free; unlimited.
- Gotcha: elements are invisible/unlit to each other until merged (a camera can't "see" an image plane, a light won't affect it, until both pass through the same uMerge).

### uProjector (uPj)
Projects an image onto USD geometry — multi-layer texturing, one texture across several objects, camera-viewpoint background projection, image-based rendering. Best understood as a variant of a spotlight/disk light. (p. 1675)
- Inputs: orange **SceneInput** (optional — if connected, transforms on the projector move that sub-scene too); white **ProjectiveImage** (required).
- Light-mode restrictions (p. 1676): lighting must be enabled to see results; behaves as diffuse/specular light (surface-normal dependent, can create highlights); **Enable Shadows** lets it cast shadows; affects everything downstream in the USD tree; Alpha does **not** clip geometry; overlapping projections' light adds.
- **uCamera projection vs. uProjector** (p. 1676): use uCamera's projection when it must match an actual camera (more control over aperture/film back/clip planes); use uProjector as a general-purpose light for layering/texturing (better intensity/color/decay/shadow control).
- Key controls: **Color** (multiplies image before projecting); **Intensity**; **Exposure**; **Color Temperature/Enable** (default 6500K); **Diffuse/Specular Response**; **Decay Type**: **Quadratic** (default, realistic falloff) / Linear / No Decay; **Decay Rate** (lower = stronger); **Shaping Focus** (edge-to-center focus); **Shaping Cone Angle** (up to 180°); **Normalize Intensity**. **Fit Method** (how the image fills the projector's — always-square — or camera's — possibly non-square — light "pyramid," relevant whenever pyramid aspect ≠ image aspect): Inside (uniform scale, fits fully inside — nothing outside the cone is ever lit) / Width / Height (may overflow the other axis) / Outside (uniform scale, fully covers the cone — everything inside is always lit) / Stretch (non-uniform, exact fill). **Projection Mode**: Light / Texture (paired with uCatcher; tip — feed a uCatcher into a Blinn material's Specular Texture input so any object using it receives the projection as a specular highlight). **Shadows**: Enable Shadows (default on), Shadow Color (default black), Density (1.0 = fully transparent shadow, per the manual's literal wording), Softness, Softness Quality, Shadow Map Size, Shadow Map Bias, Shadow Map Offset.

### uRenderer (uRn)
Converts the USD 3D scene to a 2D image via a scene camera or a default perspective view. **Every USD branch must terminate here.** (p. 1680)
- Inputs: orange **SceneInput** (required); blue **EffectMask**.
- Controls tab: **Camera** (Default = first camera found, else default perspective). **Renderer Type** (Storm, currently the only option). **Output AOVs As Layers**. **AOV**: Color (full render) / Depth (normalized per-frame black-white map) / PrimID (numeric per-prim value) / Camera Depth (accurate float32 camera-relative depth, appears black at a glance). **Lighting**: None / Camera / Scene / **Enable Sky Dome**. **Complexity**: Low/Medium/High. **Aux Channel Z** (renders camera depth to Z). **Film Back Fit**. **Max Iterations**.
- Image tab: **Process Mode** (Full Frames vs interlaced); **Width/Height**, **Pixel Aspect XY**, **Auto Resolution** (syncs Timeline resolution), **Depth**; **Domain Overscan** / **Overscan** (extra pixels outside data/display window, for later stabilization/lens work); **Render Color Space** (Linear/sRGB); **Source Color Space** (Auto passes incoming metadata; Space sets one explicitly — tags metadata only, doesn't convert); **Source Gamma Space** (Auto / Space / Log [Cineon adds Lock RGB, Level, Soft Clip, Film Stock Gamma, Conversion Gamma, Conversion table] / Remove Curve / Pre-Divide-Post-Multiply for straight↔premultiplied alpha).

### uReplaceMaterial (uRM)
Overrides an object's material (Color, Texture, or MaterialX), globally or restricted via Prim Selection. (p. 1684)
- Inputs: yellow **Scene Input** (uLoader scene); green **Material Input** (uMaterialX, uShader, or picked from another uLoader'd scene); **Image Input** (shared behavior, see below).
- Key controls: **Prim Selection > Pick** + **Invert Prim Selection**. **Type**: Color / Texture (Browse) / MaterialX (Browse, or pick from Material Input — closes all other controls). **Diffuse** (Color + R/G/B). **Emissive** (global lighting/glow layer over existing texture, adjustable intensity; Color + R/G/B). **Workflow Mode**: Metallic (Metallic slider, reflective/metal look) vs Specular (Specular Color, glossiness). **Roughness**. **Clearcoat** + **Clearcoat Roughness** (car-paint/polished-metal look). **Opacity** + **Opacity Threshold**. **Matte** ("Is Matte" — occludes background / clean alpha cutouts).

### uShape (uSh)
Basic USD primitives: Capsule, Cone, Cube, Cylinder, Ico sphere, Plane, Sphere, Torus. (p. 1686)
- Inputs: **Image Input** (shared behavior, see below).
- Controls tab: **Shape** menu (remaining controls adapt). **Double Sided**. **Lock Width/Height/Depth** + **Size Width/Height/Depth** (Plane/Cube). **Radius** (Capsule/Sphere/Cylinder/Cone/Torus). **Height** (Capsule/Cone/Cylinder). **Top Radius** (Cone, for truncation). **Subdivision Level/Base/Height/Cap/Cylinder** (tessellation). **Subdivision Scheme**: None/Bilinear/Loop/Catmull-Clark. **Angle** (partial-shape range, e.g. 180-360° = half shape). **Latitude** (Sphere/Torus crop). **Cap Bottom/Top** (Cylinder/Cone). **Section** (Torus tube thickness). **Matte**.
- Material tab: **Diffuse Mode** (Color/Texture), **Emissive**, **Workflow Mode** (Metallic/Specular), **Roughness**, **Clearcoat** + **Clearcoat Roughness**, **Opacity** — same semantics as uReplaceMaterial.

### uSwitch (uSw)
USD analogue of 2D Switch — selects one of several USD sources to pass through. (p. 1690)
- Inputs: up to **9** dynamically-added, renameable inputs (type a number manually in Config for more than 9).
- Key controls: **Source** switcher (Controls tab); **Number of Inputs** slider + **Name X** fields (Config tab).

### uTransform (uXF)
Adds an independent second set of 3D position/rotation/scale on top of upstream transforms, targeted via Prim Selection — chain multiple for parenting/hierarchical movement. (p. 1692)
- Inputs: orange **Scene Input** (required).
- Key controls: **Pick** (Scene Tree) + shared Transform-tab set (Translation, Rotation Order, Rotation [+Use Target for target-relative rotation], Pivot, Scale [+Lock X/Y/Z]). **Use Target** additionally exposes an XYZ target — object continuously rotates to face it, Rotation becomes relative to it.

### uVariant (uVa)
Switches between pre-authored "variants" baked into the USD scene. (p. 1694)
- Inputs: one required Scene Input.
- Key controls: **Pick** + **Selected Prims** + **Invert Prim Selection** (animatable). **Variant Set** dropdown (shows "No Selection" if none exist); **Variant** dropdown (choices under the selected set).

### uVisibility (uVis)
Shows/hides an object or branch within a USD scene. (p. 1696)
- Inputs: orange **Scene Input** (required).
- Key controls: **Pick** (prims highlight in viewer) + **Selected Prims** + **Invert Prim Selection** (animatable). **Visible** checkbox (animatable).

### uVolume (uVo)
Imports volumetric **VDB** files (single or animated sequence) with density/temperature/color control. (p. 1697)
- Usage: adding the node opens a file browser immediately; supports trim/loop/speed like uLoader. **Scale** adjusts density.
- **Emission** modes: **Color** (flat diffuse color — note: white makes it immune to USD lights); **Field** (scatters color across a nominated Emission Field); **Blackbody** (temperature-driven color+intensity, for fire/explosions); **Gradient** (maps colors over a targeted field). Has the standard USD Transform tab.

### USD Lights (family overview)
Six geometric light types share: **Override Selection** (Pick an existing light to adjust), **Color**, **Intensity** (e.g. 0.2 = 20% light), **Exposure** (like Intensity), **Color Temperature/Enable** (default 6500K), **Diffuse Response**, **Specular Response**, **Normalize** (normalizes scene contribution) — plus the standard Transform tab for position/direction/scale. Only shape-specific extras are listed:
- **uCylinder Light (uCL)** — fluorescent-tube analogue (length+diameter). Extra: **Treat As Line**; **Length**; **Radius** (p. 1699).
- **uDisk Light (uDi)** — round flat light (umbrella/softlight). Extra: **Shaping Focus**; **Shaping Cone Angle**; **Radius** (p. 1700).
- **uDistant Light (uDL)** — directional/sunlight analogue; control rotation sets direction. Extra: **Angular Size** (p. 1702).
- **uDome Light (uDo)** — SDR/HDR image-mapped environment light around the whole scene; rotation sets orientation; adds an **Image Input** (shared behavior). Extra: **Guide Radius** (dome size; shrink to simulate a room); **Texture File/Browse**; **Texture Format** (Lat-Long/MirrorBall/Angular/Cube Mapped Vertical Cross) (p. 1703).
- **uRectangle Light (uRL)** — flat softbox/window analogue. Extra: **Shaping Focus**; **Shaping Cone Angle**; **Width**; **Height** (p. 1705).
- **uSphere Light (uSL)** — point light with radius. Extra: **Treat as Point**; **Radius** (p. 1707).

### USD Material tools (uTexture / uTextureTransform / uNormalMap / uShader)
Build/iterate a texture-driven material inside Fusion without pre-baking it into the source USD file. Standard chain: **uTexture → (uTextureTransform and/or uNormalMap) → uShader → uReplaceMaterial**. (p. 1709)
- **uNormalMap (uNm)**: modifies a "normals" texture before uShader. Must sit directly between a uTexture and a uShader node — placement-dependent (p. 1709).
- **uShader (uSd)**: builds the material. **Shader Model**: **USD** (Diffuse Mode=Color, Emissive, Workflow Mode Metallic/Specular, Roughness, Clearcoat+Clearcoat Roughness, Opacity) or **MaterialX** (open standard from the Academy Software Foundation; spec at materialx.org). Connecting a uTexture exposes a drop-list of every material input it can feed; connecting to one disables that input's slider and exposes **Channel**, **Scale**, **Bias** controls (p. 1710).
- **uTexture (uTx)**: sources an image via **Browse**, drag from Media Pool onto **File Name**, or a live **Image Input** (shared behavior). **Source Color Space** sets interpretation — **select Linear for a Normals image**. **U/V Address Mode** sets edge behavior when scaled beyond bounds (p. 1713).
- **uTextureTransform (uTXF)**: Scale/Rotation/Position for a loaded texture; same placement rule as uNormalMap — only works between uTexture and uShader (p. 1714).

### Shared "Image Input" behavior (uImage Plane, uShape, uReplaceMaterial, uDome Light, uTexture)
These nodes expose an **Image Input** alongside a static Filename field: piping in any live Fusion node overrides/hides Filename and — unlike a Filename-loaded still — supports **animated** textures, applied as a diffuse texture (uShape/uReplaceMaterial) or as the dome's environment map (uDome Light). One shared mechanism, stated near-verbatim at each node.

### Common Controls — USD nodes
**Transform tab** (most USD nodes; identical to uTransform's Controls tab): **Translation**; **Rotation Order**; **Rotation** (relative to Use Target if enabled, else global); **Pivot** (offsets rotation center, default 0,0,0); **Scale** (Lock X/Y/Z or independent). **Settings tab** (every USD tool) is a reduced subset of the Tracking/Transform one: **Hide Incoming Connections**, **Comments**, **Scripts** only — no Blend/RGBA-channel/Motion-Blur/Use-GPU controls.

---

## Gotchas and non-obvious behavior
- Camera Tracker: **Reset** (Track tab) wipes everything including solve data; **Delete** (Solve tab) wipes only solve data, keeps tracking. Pick deliberately.
- Camera Tracker Average Solve Error is a real go/no-go number: <1.0 px generally good, 0.6-0.8 px excellent (p. 1578) — don't eyeball it.
- Planar Tracker per-point data does not survive save/reload (autosave included) — finish a planar track in one sitting and immediately create a Planar Transform to lock in the usable result.
- Surface Tracker: mesh points can't be added/removed once tracking has begun — reset tracking first.
- Surface Tracker: source frame rate ≠ Timeline rate can make tracking stutter — bake retiming first (Edit page > right-click > Render In Place).
- Tracker's "Flatten Transformation" and Transform/Camera Shake's "Flatten Transform" all mean the same thing: stop concatenating the *outgoing* transform; none of them stop concatenation of transforms coming *in*.
- Crop, Resize, Scale, Letterbox all explicitly warn against animating because they change resolution frame to frame — use Transform (or DVE/Camera Shake) for animated moves instead.
- Resize/Scale silently use fast Nearest Neighbor on non-HiQ (draft) renders unless **Only Use Filter in HiQ** is disabled.
- USD: Light-mode projections (uProjector/uCamera) ignore the projected image's Alpha entirely — a common trap when trying to "cut a hole" with a projected mask; switch to Texture mode + uCatcher.
- USD: a uCatcher renders its target fully transparent/invisible with no active Texture-mode projector hitting it — an easy "why did my object disappear" trap.
- USD: uMerge is the parenting mechanism — transforming it moves everything feeding it; objects in separate uMerge branches don't light/see each other until combined into one uMerge.
- USD: uNormalMap and uTextureTransform only function specifically wedged between a uTexture and a uShader node.
- USD: uRenderer's Camera menu defaults to "first camera found in scene" — connection/assembly order can silently decide which camera renders if you don't explicitly pick one.

## Recipes / workflows
1. **Camera Tracker match-move loop** (p. 1587-1588): Track > Solve > Refine Filters (Minimum Track Length ~5-10, or ~3 for fast rotation) > Solve > Cleanup tracks (delete worst ~20% Maximum Solve Error) > Solve > Cleanup from 3D point-cloud viewer > Solve > repeat until Average Solve Error < 1.0 (lower for >HD) > Export > Update Previous Export on later re-solves.
2. **Set a Camera Tracker ground plane** (p. 1584-1585): Solve first > 3D Scene Transform = Unaligned > find the frame with the largest/clearest ground locators > box-select them in the 2D viewer (Shift-drag adds) > confirm **Selection Is** matches locator orientation > **Set from Selection** under Orientation > set 3D Scene Transform back to Aligned.
3. **Planar Tracker → rotoscope hand-off** (p. 1640): track the object fully > **Create Planar Transform** on the Planar Tracker > on the new node, at any tracked frame connect a Polygon node and roto the object > scrub and refine the polyline per-frame.
4. **Planar Tracker "lock an effect" (paint-and-restore)** (p. 1596): Planar Tracker #1, Steady mode, Clipping Mode = Domain, Steady Time = reference frame > Paint (or other edit) on the now-motionless surface > Planar Tracker #2, Invert Steady Transform on, same tracking data, Clipping Mode = Domain, to reintroduce the original motion.
5. **Surface Tracker composite** (p. 1599-1607): Bounds (draw on the flattest/closest reference frame, ≥3 points, avoid object edges) > Mesh (Automatic or Uniform; >5 points inside boundary is a good sign) > Track (Forwards/Backwards; fix drift by repositioning mesh points at the frame it starts, then continue) > Result (pick Output mode, e.g. Warp Input 2 Onto 1; set Overlay Placement/Positioning; set blend mode + Opacity).
6. **USD minimal scene** (p. 1656): uLoader (browse to file) → uMerge → add uCamera/uLights into further uMerge inputs → uRenderer → MediaOut. View through the camera via viewer right-click > uCamera > [name] on the uMerge (or downstream) node.
7. **USD re-lightable texture projection** (p. 1661-1662, 1678-1679): target geometry with a **uCatcher** material on its shader's diffuse (or other) input > add a **uProjector**/uCamera with **Projection Mode = Texture** projecting the desired image > the uCatcher-using geometry now clips by the projected image's Alpha and can be relit.
8. **USD material iteration without touching the source file** (p. 1709-1714): uTexture (load image; Source Color Space = Linear for normal maps) > optionally uTextureTransform and/or uNormalMap (both must sit directly between uTexture and uShader) > uShader (pick Shader Model; connecting the texture exposes Channel/Scale/Bias per target input) > uReplaceMaterial (Prim Selection targets which object(s) in the source uLoader'd scene receive it).

## Scripting and automation hooks
- Tracker **Connect To** published outputs, verbatim IDs (p. 1623-1624): `SteadyPosition`, `UnsteadyPosition`, `SteadyAxis`, `SteadySize`, `UnsteadySize`, `SteadyAngle`, `UnsteadyAngle`, `Position1`, `PerspectivePosition1`, `PositionX1`, `PositionY1` (3D space), `PerspectivePositionX1`, `PerspectivePositionY1` (3D space), `SteadyPosition1`, `UnsteadyPosition1` (pattern repeats per-tracker-index for Tracker 2, 3...).
- Transform's **Center** control is always stored/returned as a normalized 0-1 value via scripting or when published for another node to connect to, regardless of what **Reference Size** currently displays in the UI (p. 1652).
- Planar Tracker/Planar Transform: right-click the "Track spline" label for the raw 4x4-matrix spline in the Spline Editor; Planar Tracker's Stabilize mode also exposes a "Stable Track spline" (also 4x4 matrices) via right-click.
- Preferences path for split X/Y tracker paths (instead of one displacement path) in the Spline Editor: **Preferences > Globals > Splines**.
- Node abbreviations (Select Tool dialog / scripting references), as stated in this slice: Camera Tracker `CTra`, Planar Tracker `PTRA`, Surface Tracker `SFt`, Tracker `Tra`, Camera Shake `CSh`, Crop `Crp`, DVE `DVE`, Letterbox `LBX`, Planar Transform `PXF`, Resize `Rsz`, Scale `SCL`, Transform `XF`, uCamera `uCa`, uCatcher `uCa` (manual states both as `uCa` — verify against the live tool list before relying on this for disambiguation; not an inferred correction, just flagging the apparent duplication), uDuplicate `uDp`, uExport `uEx`, uImage Plane `uIm`, uLoader `uLd`, uMaterialX `uMX`, uMerge `uMg`, uProjector `uPj`, uRenderer `uRn`, uReplaceMaterial `uRM`, uShape `uSh`, uSwitch `uSw`, uTransform `uXF`, uVariant `uVa`, uVisibility `uVis`, uVolume `uVo`, uCylinder Light `uCL`, uDisk Light `uDi`, uDistant Light `uDL`, uDome Light `uDo`, uRectangle Light `uRL`, uSphere Light `uSL`, uNormalMap `uNm`, uShader `uSd`, uTexture `uTx`, uTextureTransform `uTXF`.
- File formats stated verbatim: USD `.usd`, `.usda` (UTF-8/ASCII), `.usdc` (binary), `.usdz` (packaged); MaterialX `.mtlx`; volumetric `.vdb`.
- Keyboard shortcuts stated: Shift-D toggles Darken Image in the Planar Tracker viewer; Cmd-G (macOS)/Ctrl-G (Windows) toggles camera frame-aspect Guides in a USD viewer.
