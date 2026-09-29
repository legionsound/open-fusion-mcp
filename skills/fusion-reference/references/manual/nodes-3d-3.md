<!-- nodes-3d.md part 3 of 3; index: nodes-3d.md -->
## The Common Controls

These control families recur (with identical semantics) across nearly every 3D node's Controls/Materials/Transform/Settings tabs (p. 787-795). Individual node entries above reference this section instead of repeating it.

### Common Controls tab (bottom of many nodes' Controls tab)
- **Visibility**: `Visible` (governs viewer + Renderer3D output + shadow casting — off means fully excluded from all three); `Unseen by Cameras` (visible in viewers except through a camera, and excluded from Renderer3D output; shadows from an unseen object still render in the **software** renderer but not OpenGL); `Cull Front Face`/`Cull Back Face` (excludes matching-facing polygons from render, display, **and** shadow casting; enabling both ≈ disabling Visible); `Suppress Aux Channels for Transparent Pixels` (older versions always excluded transparent pixels from aux channels — software renderer excluded RGBA=0 pixels, GL renderer excluded Alpha=0 pixels; this is now optional so aux data like UVs/Normals/Z can be read from otherwise-transparent regions, e.g. for retexturing partially-transparent objects or correct DoF Z on transparent areas; note the exclusion test uses final lit pixel color, so a specular highlight on clear glass is unaffected by this checkbox).
- **Lighting**: `Affected by Lights` (off = ignores scene lights, doesn't cast/receive shadows, renders at full unlit brightness), `Shadow Caster` (off = doesn't cast shadows on others), `Shadow Receiver` (off = doesn't receive others' shadows).
- **Matte**: `Is Matte` (object's pixels become invisible to camera, and everything directly behind the camera through those pixels also becomes invisible — overrides all textures), with `Opaque Alpha` (forces the matte's Alpha to 1; visible only when Is Matte is on) and `Infinite Z` (sets Z-channel to infinity; visible only when Is Matte is on).
- **Blend Mode**: `OpenGL Blend Mode` (limited mode set, used by both the OpenGL renderer and the viewers) and `Software Blend Mode` (supports the full Merge-node blend-mode set except Dissolve). Blend modes were designed for 2D and can behave oddly in a lit 3D scene — for predictable results, use them in unlit 3D scenes with the software renderer.
- **Normals/Tangents**: `Scale` (length of displayed normal/tangent vectors), `Show Normals` (blue vectors — illustrate per-surface lighting angle), `Show Tangents` (green = Y, red = X vectors — texture direction).
- **Object ID**: numeric slider identifying the object for masking; `Sample` button works like a color picker against the viewer image (source must have been rendered with the ObjectID channel).

### Common Materials tab
- **Diffuse**: `Diffuse Color` (base lit/ambient color; multiplied by any diffuse texture's RGB if connected; texture's Alpha can control surface transparency), `Alpha` (material's alpha channel value — affects diffuse+specular equally and the rendered output alpha; multiplied by the diffuse texture's alpha if present), `Opacity` (reduces diffuse+specular color/alpha equally, letting hidden objects show through — distinct from Alpha).
- **Specular**: `Specular Color` (reflected highlight color — plastics/glass ≈ white highlights, metals ≈ material-colored highlights; no texture input on the basic shader — use 3D Material category nodes for texture control), `Specular Intensity` (highlight strength; multiplied by the specular-intensity texture's alpha if connected), `Specular Exponent` (highlight falloff sharpness — higher = sharper/glossier; no texture input on basic shader).
- **Transmittance**: how light passes through the material (distinct from surface Opacity — you can have a fully opaque surface that transmits 100% of light, i.e. luminous/emissive). `Attenuation` (RGB — how much of each channel transmits through for colored "stained glass" shadows; (1,1,1) = fully transmissive, (1,0,0) = red-only transmission), `Alpha Detail` (0 = ignore Alpha, whole object casts shadow; 1 = Alpha determines which portions cast shadow), `Color Detail` (0→1 blends in more of diffuse color+texture into the cast shadow; note Alpha/Opacity are ignored when transmitting color, so a solid-alpha object can still color its shadow), `Saturation` (0 = monochrome transmitted shadow color).
- `Receives Lighting`/`Receives Shadows` checkboxes — off means the object is always fully lit and/or unshadowed regardless of scene lights.
- `Two-Sided Lighting` — adds a second, oppositely-facing normal set to the back of the surface (off by default for render speed). Fusion does **not** cull backfaces by default, so a one-sided plane viewed from behind still shows the front image (as if transparent) rather than vanishing — Two-Sided instead genuinely lights the back face independently. Gets confusing combined with transparency: a transparent two-sided surface lit only from behind can look unlit from the front.
- `Material ID` — numeric identifier rendered into the Renderer3D's `MatID` aux channel when that channel is enabled.

### Common Transform tab
- Translation: `X/Y/Z Offset`.
- Rotation: `Rotation Order` (order axes are applied, e.g. XYZ = X then Y then Z) + `X/Y/Z Rotation` (relative to Target if Use Target is enabled, else global axis).
- Pivot: `X/Y/Z Pivot` (offsets the rotation center from the object's own center/origin).
- Scale: `X/Y/Z Scale` + `Lock X/Y/Z` (locked = single uniform Scale slider, and per-axis scaling is blocked even via the onscreen widget's individual-axis drag).
- `Use Target` — object always rotates to face a target point; rotation becomes relative to that target.
- `Import Transform` — imports transform-only data (not geometry/lights/cameras) from `.lws`/`.ase`/`.ma`/`.xsi`; use File > FBX Import for full scene import.
- Onscreen controls: **Q** = translate, **W** = rotate, **E** = scale; drag one axis handle for single-axis, or the center for all three. Scale defaults to locked/uniform across most 3D nodes — unlock `Lock X/Y/Z Scale` for single-axis scaling.

### Common Settings tab
- `Hide Incoming Connections` — visually hides a node's incoming connection lines in the Node Editor (shows empty per-input fields in the Inspector instead); drag a node into the field to hide its line as long as that source node isn't itself selected (selecting it re-shows the line).
- **Comment tab** — free-text notes per tool; adds a small red-dot icon + tooltip bubble on the node; can be animated over time.
- **Scripting tab** — present on every Fusion tool; holds script edit boxes that run at render time (see scripting documentation for details — not elaborated in this slice).

## Gotchas and non-obvious behavior

- The manual's own Contents list shows **both** Soft Clip and Spherical Camera under the abbreviation `[3SC]` (p. 681 contents list, and again at their respective headers) — this looks like a manual typo/collision; verify the actual internal tool ID before scripting against it rather than trusting the printed abbreviation.
- `Camera 3D`'s image-plane `Depth` control sets distance from camera, but the camera's own **Z position does not** move the image plane's distance — don't expect moving Camera Z to push the image plane away.
- Enabling **Two-Sided Lighting** plus transparency is one of the more counter-intuitive combos in Fusion 3D: a transparent two-sided surface lit only from behind can appear unlit when viewed from the front, because the same one-directional-normal lighting rules still apply per face.
- `Weld 3D` can actively **degrade** a model (e.g. Fusion's own cone primitive) by merging vertices that were intentionally duplicated with different normals for correct per-face shading.
- AA (supersampling) on aux channels is a *quality trap*: enabling it on ObjectID/MaterialID/TexCoord/Normal/BackVector/Vector can blend values from multiple overlapping surfaces into one artifact pixel — only WorldCoord and Z are recommended for AA.
- `Point to Camera` in Displace3D is specifically meant for camera image planes: it lets the plane look visually unchanged through its own camera while actually being deformed in Z for correct 3D-layer interaction.
- `Replicate 3D`'s Step-based centering trick: step 6 + X offset -0.5 centers on a Point Cloud's internal representation; step 6 + X offset -0.125 does the analogous thing for Locator3Ds (offsets shift again once scaled).
- FBX Mesh 3D and raw Alembic Mesh 3D nodes both collapse imported files into a **single mesh/pivot**; only the File > Import menu path preserves per-object hierarchy and (for Alembic) animation.
- `UV Map 3D`'s Camera mode only sets UV coordinates — it does **not** project the image itself; you still have to wire the image to the material's diffuse (or other) texture input separately.
- Projector3D / Camera3D projection Alpha handling differs by mode: Light/Ambient projection alpha does **not** clip geometry; Texture-mode projection alpha **does** clip geometry.
- The OpenGL renderer cannot do soft shadows at all — if soft shadows are required, the scene (or at least that Renderer3D) must use the Software renderer.
- Particle systems require the pRender node's Motion Blur settings to **exactly match** the Renderer3D's Motion Blur settings, or subframe renders conflict and produce incorrect results.

## Recipes / workflows

1. **Bring a 2D clip into 3D as a card**: MediaIn/Loader → `Image Plane 3D` (green MaterialInput) → `Merge 3D` (with camera/lights) → `Renderer 3D`.
2. **Texture a primitive without letting the texture slide when the object moves**: `Shape 3D` (leave its own Transform tab at default) → `UV Map 3D` (author mapping here) → `Transform 3D` (do all scene placement here).
3. **Build an isolated falloff/lighting pass**: scene → `Override 3D` (enable "Do Affected by Lights", set to off) → `Replace Material 3D` (feed a Falloff-type 3D Material shader into the green MaterialInput).
4. **Give Text3D an advanced material**: `Text 3D` → `Replace Material 3D` (green MaterialInput = your 3D Material shader) → `Merge 3D`.
5. **Fix cracking when displacing geometry with duplicated vertices**: geometry → `Weld 3D` (Tolerance = Auto first) → `Displace 3D`.
6. **True parallel stereo rig** (pick one): (a) connect an external right Camera3D to the green RightStereoCamera input; (b) author fully separate left/right Camera3D nodes; (c) in Toe-In/Off Axis mode, set Convergence Distance to ~999999999.
7. **Render with overscan**: manually increase the scene's Camera3D `Aperture Width`/`Height` (Film Back) by the overscan factor — this also applies to cameras imported via `.fbx`/`.ma`, since overscan metadata is never exported by 3D apps.
8. **Rack focus**: enable Renderer3D's OpenGL `Enable Accumulation Effects` + `Depth of Field`, tune Quality/Amount, then animate the scene's Camera3D `Plane of Focus` across the frames needing the focus pull.
9. **Recommended Renderer3D aux-channel AA policy**: enable Anti-Aliasing only for `WorldCoord` and `Z`; explicitly leave AA disabled for `MaterialID`, `ObjectID`, `TexCoord`, `Normal`, `BackVector`, `Vector`.
10. **Project a re-lightable texture** (rather than a light-based projection): route the projected image through a `Catcher` node into the target material's texture input (e.g. Specular Texture on a Blinn) using `Projector 3D` or `Camera 3D` set to `Texture` projection mode.

## Scripting and automation hooks

- Text-modifier attach point: `Modify With > CoordTransform Position` (right-click any XYZ number field) creates the Coordinate Transform modifier, with `Target Object`, `Sub ID`, and `Scene Input` controls (p. 786-787).
- Locator3D 2D output wiring: right-click a 2D position control (e.g. a mask center) → `Connect To > Locator 3D > Position` (p. 724).
- Custom Vertex 3D expression variables and functions (p. 700-704):
  - Position: `px, py, pz`; Normals: `nx, ny, nz`; Vertex color: `vcr, vcg, vcb, vca`.
  - Numbers: `n1..n8` (current time) / `n1_at(float t) .. n8_at(float t)`.
  - Points: `p1x, p1y, p1z, p2x, ...` (current time) / `p1x_at(float t)`, etc.
  - LUTs: `getlut1(float x) .. getlut4(float x)`, x in [0,1].
  - Setup tab results: `s1, s2, s3, s4` (evaluated once per frame; only frame-level vars/functions valid, e.g. `n1..n8`, `time`, `W`, `H`, `sin()`, `getr1d()` — no per-pixel/per-vertex vars).
  - Intermediate tab results: `i1..i8` (evaluated once per vertex, after Setup; can reference Setup results).
  - Random: `rand()`, `rands()`, seeded by the Config tab's `Random Seed` (+ Reseed button).
- FBX camera/scene import menu path: `File > Import > FBX Scene` (Fusion Studio) / `Fusion > Import > FBX Scene` (Resolve) — preserves per-object hierarchy and animation, unlike the raw `FBXMesh3D` node.
- Alembic import menu path: `File > Import > Alembic Scene` (Fusion Studio) / `Fusion > Import > Alembic Scene` (Resolve).
- Auto-open file browser on node creation: `Preferences > Global > General > Auto Clip Browse` (Fusion Studio) / `Fusion > Fusion Settings > General > Auto Clip Browse` (Resolve) — affects `FBX Exporter 3D` and `FBX Mesh 3D`.
- Supported external transform/scene import formats seen across nodes: `.lws` (LightWave Scene), `.ase` (3DS Max ASCII Scene Export), `.ma` (Maya Ascii Scene), `.xsi` (dotXSI/Softimage XSI) — used by `Camera 3D` (Import Camera), `Point Cloud 3D` (Import Point Cloud), and `Transform 3D`/Common Transform tab (Import Transform).
- FBX Mesh 3D / FBX Exporter 3D supported file types: `.fbx` (ascii and 5.0 binary), `.dxf` (AutoCAD), `.3ds` (3D Studio), `.obj` (Alias), `.dae` (Collada).
- Keyboard shortcuts:
  - Viewer camera/onscreen transform mode: `Q` translate, `W` rotate, `E` scale (Transform 3D / Common Transform tab).
  - Toggle viewer camera guides: `Cmd-G` (macOS) / `Ctrl-G` (Windows) — Show Guides for camera frame aspect.
  - Point Cloud 3D viewer contextual actions: `Del` delete selected points, `Shift+A` select all, `Shift+F` find points, `F2` rename selected, `Shift+C` create new point, `Shift+N` toggle names (None/Selected/Published/All), `Shift+L` toggle locations, `Shift+P` publish selected, `Shift+U` unpublish selected, `Shift+S` create a Shape at selected points, `Shift+I` create and fit an ImagePlane to selected points, `Shift+O` create a Locator at selected points.
  - Manual text kerning workflow (Text3D lacks direct manual kerning): author/kern in a `Text+` node, right-click its name in the Inspector → `Copy`, select the `Text 3D` node, right-click → `Paste Settings`.
- Renderer3D multilayer output layer names (for compositing math): `Shadow` (combine via multiply), `Diffuse`, `Specular`, `Ambient`, `Reflect`, `Refract`, `Fog` (combine via add).
- Aux-channel names referenced by the manual for scripting/lookup: `Z`, `Coverage`, `BgColor` (software only), `Normal` (X/Y/Z, range [-1,1]), `TexCoord` (U/V mapped to R/G), `ObjectID` (0 = empty, max 65534), `MaterialID` (0 = empty, max 65534, rendered from each Material's `Material ID` control), `WorldCoord`, `BackVector`, `Vector`, `MatID` (Renderer3D's output name for Material ID).
