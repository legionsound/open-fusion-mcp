<!-- nodes-3d.md part 2 of 3; index: nodes-3d.md -->
## Renderer3D [3Rn]

Converts the full 3D environment to a 2D image; every 3D branch must terminate here (p. 739-747).
- Two (or more, via plugin) render engines:
  - **Software**: CPU-only, slower, consistent across machines (required for network rendering), required for **soft shadows**, generally supports all illumination/texture/material features.
  - **OpenGL**: GPU-accelerated, faster, output can vary slightly by graphics card/driver, offers custom supersampling and realistic DoF, cannot produce soft shadows, respects Image tab's Color Depth (can slow down at int16/float32 on some cards).
  - **OpenGL UV**: special-purpose — unwraps a textured model into a flattened 2D UV-space image (optionally with lighting baked in), typically for round-tripping into a paint app.
- Inputs: `SceneInput` (orange, required — the 3D scene to render), `EffectMask` (blue — 2D image masking the node's output).
- Multilayer support: outputs 7 separate lighting passes by default — Shadow, Diffuse, Specular, Ambient, Reflect, Refract, Fog — previewable individually via the viewer's layer preview control; recombine with Merge/MultiMerge/Channel Booleans (every pass is additive except Shadow, which must be **multiplied**).
- Controls tab (engine-agnostic):
  - `Camera` — which scene camera renders (Default = first camera found, or default perspective view if none).
  - `Eye` — Mono / Left / Right (translated per camera's stereo Separation+Convergence) / Stacked (top-bottom composite) / Layers (left/right as separate output layers).
  - `Reporting` — 2 checkboxes for console warning/error logging + 2 for abort-on-warning/error; all 4 default on.
  - `Renderer Type` — Software / OpenGL / OpenGL UV (+ third-party plugins). Remaining controls change per engine.
- **Software controls**:
  - Output Channels: `RGBA` (required, always on), `Z` (distance-from-camera; no anti-aliasing possible; overlapping depths keep the frontmost value), `Coverage` (per-pixel foreground-coverage percentage, aids Z-buffer-based AA), `BgColor` (color behind the Coverage-described foreground), `Normal` (X/Y/Z orientation per pixel, [-1,1] range), `TexCoord` (U/V mapped into R/G channels), `ObjectID` (per-object numeric ID, up to 65534, 0 = empty, multiple objects can share an ID — used for shape-based mattes), `MaterialID` (per-material numeric ID, same range/sharing rules — used for texture-based mattes).
  - `Lighting`: `Enable Lighting` (no lights present → all objects render black), `Enable Shadows` (costs render speed).
- **OpenGL controls**: same Output Channels set as Software (RGBA/Z/Normal/TexCoord/ObjectID/MaterialID, same definitions) but **no** `Coverage` or `BgColor` options.
  - **Anti-Aliasing**: supersamples by rendering larger then rescaling on the GPU (cheaper on memory than a manual oversized-render + Resize node, and faster than CPU rescale); interactive viewer skips AA unless HiQ is enabled in the Time Ruler; final renders always include supersampling if enabled.
    - Gotcha: point geometry (particles) and lines (locators) always render at native size regardless of supersampling — they end up visually thinner than expected.
    - Separate LowQ/HiQ rate controls exist for color vs. aux channels because color AA is far more expensive (shaders 10-1000x more complex, plus sorted rendering) — e.g. 1x3 may suffice for color while WorldCoord/Z may need 4x12. **Recommended to enable AA only on WorldCoord and Z** among aux channels; explicitly disable AA on **MaterialID, ObjectID, TexCoord, Normal, BackVector, and Vector** — AA on these can blend UV/normal values across differing surfaces sharing a pixel and produce oddly colored artifacts (p. 743-744).
    - `Enable (LowQ/HiQ)` checkboxes, `Supersampling LowQ/HiQ Rate` (e.g. rate 4 on a 1920x1080 target internally renders 7680x4320 then downscales; ~8x8 = 64 samples/pixel is typically enough), `Filter Type` — Box (simple, fast) / Bi-Linear (fast, clean) / Bi-Cubic (good speed/quality compromise) / Bi-Spline (better continuous-tone, can blur fine detail) / Catmul-Rom (sharp on fine detail, good for downscaling) / Gaussian (~like Bi-Cubic) / Mitchell (like Catmull-Rom but better fine detail, slower) / Lanczos (like Mitchell/Catmull-Rom, cleaner, slower) / Sinc (very sharp, can ring) / Bessel (like Sinc, slightly faster). `Window Method` (Sinc/Bessel only) — Hanning / Hamming / Blackman.
  - **Accumulation Effects**: enable both `Enable Accumulation Effects` and `Depth of Field`, then tune Quality (higher = smoother out-of-focus blur) and Amount (lower = more of scene stays in focus); works with Camera3D's `Plane of Focus` — animate Plane of Focus for a rack-focus effect.
  - `Lighting`: same Enable Lighting / Enable Shadows pair as Software.
  - `Texturing`: `Texture Depth` (bit depth of texture maps), `Warn about unsupported texture depths`.
  - `Lighting Mode` — Per-vertex (fast, can look blocky on poorly tessellated geometry) vs. Per-pixel (closer to software renderer's quality but OpenGL is still weaker on semi-transparency/soft/colored shadows; color depth limited by the GPU).
  - `Transparency` — Z Buffer/fast (adequate for opaque-only scenes; semi-transparent objects may sort incorrectly), Sorted/accurate (full scene sort, slower, correct transparency), Quick Mode (experimental, best for scenes that are almost entirely particles).
  - `Shading Model` — Smooth (matches viewers) / Flat (simpler, faster).
  - `Wireframe` (renders scene as shaded wireframe) + `Wireframe Anti-Aliasing`.
  - `Cryptomatte` — generates Cryptomatte layers/metadata for objects and materials (hardware renderer only); read natively by the Cryptomatte tool or saved to OpenEXR.
- **OpenGL UV renderer** gotchas: turn OFF lighting on an object after baking lighting into its texture (else double-lit); beware textures reused across multiple mesh areas (e.g., mirrored left/right — baking breaks this); unwrapping multiple meshes at once is risky since most models maximize UV(0,1)x(0,1) usage and will overlap; `UV Gutter Size` = 0 causes visible seams between faces on retexture — increase to hide seams.

## Replace Material 3D [3Rpl]

Replaces the material on all geometry in the input scene; lights/cameras pass through unaffected. Also the only way to give Text3D (which has no material input) an advanced material (p. 748-749).
- Inputs: `SceneInput` (orange), `MaterialInput` (green — 2D image or 3D material; 2D image becomes the diffuse texture on the node's built-in Basic Material, disabled if a 3D material is connected).
- Key controls: `Enable` (effect-only, distinct from red switch), `Replace Mode` per RGBA channel — Keep (don't replace that channel) / Replace / Blend / Multiply, `Limit by Object ID` / `Limit by Material ID` (reveals ID slider(s); if both enabled, an object must satisfy both to be affected — others keep their existing material).

## Replace Normals 3D [3RpN]

Replaces/recomputes normals and tangents on incoming geometry (adjusts smooth-vs-flat shading); only affects per-vertex normals/tangents, not per-face; passes non-mesh nodes (lights/cameras/point clouds/locators/materials) through unaffected. Tangents require texture coordinates on the input geometry to compute (p. 750-752).
- Inputs: `SceneInput` (orange only).
- Key controls: `Pre-Weld Position Vertices` (fixes duplicated-position vertices that would otherwise miscompute normals; the welding itself is discarded, only used to fix the normal computation), `Recompute` — Always / If Not Present / Never (Never is useful when animating), `Smoothing Angle` (typical range 20-60°; adjoining faces with a smaller angle between them get smoothed across the edge; `0.0` produces faceted normals for artistic effect; `360.0` is also a special case), `Ignore Smooth Groups` (False = respects the source app's Smooth Groups, e.g. keeps a cube's faces separately faceted; True + a large Smoothing Angle can smooth across a cube's faces anyway — Fusion has no way to visualize Smooth Groups), `Flip Normals`/tangent flip (only has visible effect if the mesh already has tangent vectors — most Fusion primitives don't until a Renderer3D or viewer generates them, so flipping a raw Cube3D does nothing until tangents exist).
- Notes on normals (p. 752): (1) FBX importer auto-recomputes missing normals, but Replace Normals3D gives higher quality; (2) bump maps can be "linked" to the normals they were authored against — recomputing normals after simplifying a high-poly model to low-poly+bump can break the intended look; (3) most Fusion primitives lack tangents until generated on-the-fly by a Renderer3D (then cached); (4) tangents are only needed for bump mapping — created with default settings (e.g. default Smoothing Angle) if a material needs bump mapping and none exist yet, or explicitly via Replace Normals3D; (5) all computation happens in each geometry's **local coordinates**, not the Replace Normals3D node's own coordinate system — a non-uniform scale applied upstream can cause problems.

## Replicate 3D [3Rep]

Replicates input geometry at the vertex or particle positions of a destination scene, with per-copy transforms and jitter (contrast with Duplicate3D, which chains copies rather than placing them at destination points) (p. 752-757).
- Inputs: `Destination` (orange, required — 3D scene/geometry with vertex positions, e.g. a mesh or 3D particle system), `Input[#]` (dynamically-added — geometry to replicate; at least one required; connecting one opens another for alternating geometry).
- Key controls:
  - `Step` — skips destination positions (step 3 = every third vertex); keeps performance sane on big meshes, or isolates parts of parametric geometry like a torus. For a Point Cloud (6 internal points per Make-Renderable point) use step 6 + X offset -0.5 to land on the point's center; use -0.125 for Locator3Ds (offsets may shift once scaled).
  - `Input Mode` — Loop (inputs cycle in order, looping if more positions than inputs) vs. Random (definite-but-random input per position, seeded by Jitter tab — good for visual variety from few inputs); irrelevant with only one input. Particle death changes particle IDs, which can shift copy order.
  - `Time Offset` — offsets source animation per copy, same staggering behavior as Duplicate3D.
  - `Alignment` — Not Aligned (keeps input mesh's own rotation), Aligned (uses destination point's normal + a reconstructed up-vector; best for organic/unwelded meshes like imported FBX; noticeable rotation drift across flat geometric meshes; apply at the origin before other transforms for best results), Aligned TBN (uses destination's tangent/binormal/normal — more accurate/stable, best for particles and geometric shapes; unwelded duplicate-position points can still get different alignments due to differing per-point normals).
  - `Color` — Use Object Color (ignore destination particle color), Combine Particle Color (keep input mesh's shader, modulate diffuse by destination particle color), Use Particle Color (replace input's shader entirely with a default shader driven by destination particle color).
  - Translation/`Rotation Order`/XYZ Rotation/XYZ Pivot/`Lock XYZ`+Scale — same semantics as Duplicate3D's Controls tab.
- Jitter tab: `Random Seed`/`Randomize`, `Time Offset` (random, vs. the deterministic Controls-tab Time Offset), Translation/Rotation/Pivot/Scale XYZ Jitter (Scale Jitter has its own Lock XYZ).

## Ribbon 3D [3Ri]

Generates an array of subdivided line segments (or a single line) between two points; commonly paired with Replicate3D (attach geometry to the lines) or Displace3D (lightning-bolt effects). **OpenGL-only** — produces nothing under the software renderer, and line rendering fidelity depends on the graphics card (p. 757-759).
- Inputs: `3D Scene` (orange, optional), `Material` (optional — 2D texture for the ribbon; lines get default texture coordinates usable with a 2D texture, adjustable further via UVMap3D).
- Key controls: `Number of Lines` (parallel strands between start/end), `Line Thickness` (accepts float in the UI, but many GPUs only honor integers or a card-specific minimum/maximum), `Subdivision Level` (vertices per line — higher = smoother displacement), `Ribbon Width` (spacing between the parallel lines), `Start`/`End` (XYZ endpoints), `Ribbon Rotation` (rotation around the start-end axis), `Anti-Aliasing` (can introduce visible gaps between segments, especially at high Line Thickness — card-dependent, use cautiously).

## Shape 3D [3Sh]

Produces basic primitives: Plane, Cube, Sphere, Cylinder, Cone, Torus (p. 759-762).
- Inputs: `SceneInput` (orange, optional — merges extra geometry), `MaterialInput` (green — 2D image or 3D material; disables Basic Material if 3D material connected).
- Key controls (vary by `Shape` menu selection):
  - Plane/Cube: `Lock Width/Height/Depth`, `Size`/`Width`/`Height`/`Depth`, and (Cube only) `Cube Mapping` (applies the node's texture using cube-cross mapping).
  - Sphere/Cylinder/Cone/Torus: `Radius`.
  - Cone only: `Top Radius` (for truncated cones).
  - Sphere/Cylinder/Cone/Torus: `Start/End Angle` (range control — e.g. 180°-360° draws half the shape).
  - Sphere/Torus: `Start/End Latitude` (latitudinal crop).
  - Cylinder/Cone: `Bottom Cap`/`Top Cap` checkboxes (open vs. capped ends).
  - Torus: `Section` (tube thickness).
  - All: `Subdivision Level`/`Base`/`Height` (tessellation controls), `Wireframe`.
- Gotcha (Sphere Map, p. 761-762): piping a LatLong (equirectangular) texture **directly** into a sphere (instead of through a Sphere Map node) squashes the texture when Start/End Angle or Latitude are set below 360°/180°; routing through Sphere Map instead **crops** it. Direct-piped textures are also mirrored horizontally (fix with a Transform node).

## Soft Clip [3SC]

Fades out geometry/particles as they approach the camera, avoiding visible "popping" in particle systems/flythroughs; conceptually the Soft-Clip analog of Fog3D, also distance-from-camera driven (p. 762-764).
- Inputs: `SceneInput` (orange, required — must include a Camera3D).
- Placement: typically just before the Renderer3D, so downstream lighting/texture changes don't affect the clip result; can be placed mid-tree if only part of the scene needs it.
- Key controls: `Enable` (effect-only, distinct from red switch), `Smooth Transition` (nonlinear/more natural fade curve vs. the default linear fade), `Radial` (same perpendicular-vs-radial distance tradeoff as Fog3D — Radial fixes edge-of-frame under-clipping but isn't always desired, e.g. can leave a close image-plane's center unclipped while edges clip), `Show In Display Views` (see the effect from any viewpoint, not just through a Camera node), `Transparent Distance`/`Opaque Distance` (Z-axis units from camera: 0% opacity at Transparent distance, ramping to full visibility at Opaque distance).

## Spherical Camera [3SC]

Lets Renderer3D output a full-surround (all-viewing-angle) image in a chosen cube/equirect layout — e.g. for a skybox texture, reflection map, or VR headset viewing (p. 764-767). *(Note: shares the `[3SC]` abbreviation shown in the manual's Contents with Soft Clip — verify against the actual toolbar/ID at authoring time.)*
- Inputs: `Image` (orange, optional — spherical-layout image: LatLong 2:1 equirectangular, VR180, H/V Cross, or H/V Strip), `Stereo Input` (green, optional — right stereo camera for stereo VR).
- Setup mirrors Camera3D: connect into a Merge3D, typically alongside a LatLong/Cross-formatted image (directly or via a Panomap node) wrapped around a sphere, with the camera placed inside.
- `Layout` menu: `VCross`/`HCross` (six cube faces in a vertical/horizontal cross, forward view centered, 3:4 or 4:3 image), `VStrip`/`HStrip` (six faces in a line, ordered Left/Right/Up/Down/Back/Front = +X/-X/+Y/-Y/+Z/-Z, 1:6 or 6:1 image), `LatLong` (single 2:1 equirectangular image), `VR 180` (1:1 180° stereoscopic image).
- Remaining controls (Near/Far Clip, Adaptive/Adaptively Adjust Near/Far Clip, Viewing Volume Size, Plane of Focus, Stereo Method [Toe In/Off Axis/Parallel], Eye Separation, Convergence Distance, Control Visibility) mirror Camera3D's equivalents (the `Image Width` setting lives on the Renderer3D and sets each cube face's size — the output image is a multiple of that horizontally/vertically).

## Text 3D [3Txt]

3D counterpart to the 2D Text+ node; based on a pre-3D-environment tool, so it lacks the material input and some material/lighting/matte controls found on other 3D nodes, but has a built-in material with Diffuse/Specular controls in its own Shading tab (p. 767-776).
- No material input — use **Replace Material 3D** downstream to swap in an advanced shader. Use **Override 3D** to control lighting/visibility/matte/ID for Text3D (since the node itself lacks those common controls).
- Gotcha: network rendering requires every render node to have the used fonts installed locally — Fusion does not transmit/share fonts to render slaves.
- Inputs: `SceneInput` (orange, optional), `ColorImage` (green — 2D image wrapped as texture; visible only when Shading tab's Material Type = Image), `BevelTexture` (magenta — 2D image wrapped on the bevel; visible only when "Use One Material" is off and Bevel Type = Image).
- **Text tab** (Text / Extrusion / Advanced sub-sections):
  - `Styled Text` edit box — standard OS clipboard shortcuts work; right-click for text-modifier contextual menu (see Modifiers below).
  - `Font` (family + typeface menus), `Color`, `Size` (relative to image width, not point size), `Tracking` (uniform inter-character spacing), `Line Spacing` (leading), `V Anchor`/`H Anchor` (3 alignment buttons + slider each; most relevant when Layout = Frame), `V Justify`/`H Justify` (customizes alignment toward full justification), `Direction`, `Line Direction` (top-bottom/bottom-top/left-right/right-left), `Write On` (range control — animate End 1→0 for write-on, Start 0→1 for write-off).
  - Extrusion: `Extrusion Depth` (0 = flat 2D text), `Bevel Depth` (requires extrusion), `Bevel Width`, `Smoothing Angle`, `Front`/`Back Bevel` checkboxes, `Custom Extrusion` (Smoothing Angle controls edge-normal smoothing; the profile spline controls extrusion-profile smoothing — smoothed segments via Shift-S, linear points = sharp edge; first/last spline points must have profile 0 to avoid Z-fighting from self-intersecting faces), `Custom Extrusion Subdivisions`.
  - Advanced: `Force Monospaced` (0 = font kerning, 1 = fully even spacing), `Use Font Defined Kerning` (on by default), Manual Font Kerning (Text3D can't manually kern directly — kern via a Text+ node then right-click > Copy on that node, select the Text3D node, right-click > Paste Settings).
- **Layout tab**: `Layout Type` — Point (simplest, arranged around a center point), Frame (rectangular frame, alignment justifies within it), Circle (text around a circle/oval; Alignment sets inside/outside edge + multi-line justification), Path (text follows a path; `Position on Path` can animate movement along it, values <0 or >1 continue in the last segment's direction). `Center X/Y/Z`, `Size`, `Width`/`Height` (Circle: width only meaningful in some sub-cases; Frame: both), `Rotation Order` + `X/Y/Z` angle, `Fit Characters` (Circle only — spacing method around circumference), `Position on Path` (Path only), "Right-Click Here for Shape Animation" label (Path only — links path to other paths / animates spline points).
- **Transform tab (Text3D-specific — separate from the Common Transform tab)**: `Transform` menu selects granularity — Characters / Words / Lines (each transformed about its own center axis); `Spacing` (space between the chosen unit; <1 causes overlap); `Pivot X/Y/Z` (offset from the calculated center; positive Z moves axis away from viewer, negative brings it closer); `Rotation Order` + `X/Y/Z`; `Shear X/Y`; `Size X/Y`.
- **Shading tab**: `Opacity` (reduces both diffuse and specular color+alpha uniformly, revealing objects behind), `Use One Material` (unchecking exposes a second material set for the bevel), `Type` — Solid or Image (Image reveals an external 2D input), `Specular Color`/`Specular Intensity`/`Specular Exponent` (same semantics as Common Materials tab's Specular section — no texture input on the basic shader; use 3D Material category nodes for texture-driven specular), `Image Source` — Tool (exposes a node input) / Clip (file browser) / Brush (lists Fusion\brushes folder clips), `Bevel Material` (visible only when Use One Material is off — mirrors the main Material controls for the bevel only), `Position`/`Rotation`/`Shear`/`Size` (when 2+ shading elements are enabled, these apply to whichever shading element is currently selected, letting border/fill/shadow be positioned independently).
- Gotcha: to hide the front face of extruded text, uncheck Use One Material and set the first material's color (incl. Alpha) to black.
- **Text 3D Modifiers** (right-click in the Styled Text box; only one modifier active at a time): `Animate` (keyframe + animate text content over time), `Character Level Styling` (not supported directly on Text3D — build it on a Text+ node instead, then connect/copy-paste settings across), `Comp Name` (inserts composition name, e.g. for slates), `Follower` (ripples animation across each character — see Text Modifiers, end of chapter), `Publish` (exposes text for connection to other text nodes), `Text Scramble` (randomizes characters), `Text Timer` (countdown or live date/time), `Time Code` (current-frame timecode), `Connect To` (wires this node's text to another node's published text output).

## Transform 3D [3XF]

Adds translate/rotate/scale to a scene without a Merge3D; useful for hierarchical parenting chains or offsetting geometry reused multiple times in a scene (p. 776-779).
- Inputs: `SceneInput` (orange, required).
- Controls mirror the Common Transform tab exactly: `X/Y/Z Offset`; `Rotation Order` + `X/Y/Z Rotation` (relative to Target if `Use Target` is on, else global axis); `X/Y/Z Pivot`; `X/Y/Z Scale` (+ `Lock X/Y/Z` — locked prevents per-axis scaling even via the onscreen widget); `Use Target` (object always rotates to face the target); `Import Transform` (`.lws`/`.ase`/`.ma`/`.xsi` — transform data only, not geometry/lights/cameras; use File > FBX Import for those).
- Multiple Transform3D nodes chained together = a parenting/hierarchical movement rig.
- Onscreen controls: Q = translate, W = rotate, E = scale (drag one axis or the center for all three).

## Triangulate 3D [3Tri]

Converts polygon geometry (e.g., quads) into triangles for easier downstream mesh processing; has **no controls at all** (p. 779-780).
- Inputs: `Scene Input` (orange, required).

## UV Map 3D [3UV]

Replaces the UV texture coordinates on scene geometry — does **not** itself apply any texture/material, only how existing/upstream materials map onto the surface. Cannot manipulate individual vertex UVs directly (onscreen controls are reference-only) (p. 780-784).
- Inputs: `Scene Input` (orange, required), `CameraInput` (visible only when Map Mode = Camera — the Camera3D driving camera-projected UVs).
- Key controls:
  - `Map Mode` — Planar / Cylindrical / Spherical / `XYZ to UVW` (raw position→UVW conversion, for procedural textures) / CubeMap / Camera (enables CameraInput; projects UVs through that camera — note this only sets coordinates, the actual image must still be wired to the material's diffuse input separately, and because it's a texture projection (not light) the image's Alpha correctly sets opacity, unlike light-based projection).
  - `Orientation X/Y/Z` (reference axis), `Fit` button (fit mapping object to input scene's bounding box), `Center` button (center mapping object on bounding box center).
  - `Lock UVs on Animated Objects` (locks UVs to a reference frame instead of needing the map animated every frame — reveals `Ref Time` slider). Fails if vertex count changes over time (mesh vertices can't be created/destroyed/reordered between ref time and current time) — so this does **not** work for many particle systems, primitives with animated subdivision, or Duplicate nodes using non-zero time offsets.
  - `Size X/Y/Z`, `Center X/Y/Z` (projection object size/position), `Rotation`/`Rotation Order` + `Rotation X/Y/Z` (independent of rotation order), `Tile U/V/W` (how often texture repeats across the projected UV space — pairs well with a Create Texture node; transforms the UVW coordinates, not the texture itself), `Flip U/V/W` (mirrors coordinates per axis), `Flip Faces` (Cube Map mode only — mirrors individual cube-face coordinates).
- Recommended authoring order (p. 783): `Shape 3D > UV Map 3D > Transform 3D` — leave the Shape's own Transform tab at defaults and do scene placement in a following Transform3D, otherwise animating/moving the Shape node directly slides the texture across the surface. UV changes are per-vertex, not per-pixel — poorly tessellated geometry can show mapping artifacts.

## Weld 3D [3We]

Fixes duplicated/near-duplicate position vertices left over from modeling (which cause hard shading seams, cracks under Displace3D, missing/doubled pixels, or particles leaking through invisible gaps) — a mesh-robustness tool, not a mesh-simplification or general vertex-merge tool (p. 784-786).
- Inputs: `Scene Input` (orange, required).
- Placement: after the geometry that has the vertex problem, and before Displace3D if displacement is what exposes the cracking.
- Key controls: `Weld Mode` — weld (merge coincident-position vertices) or `Fracture` (opposite: unwelds everything, destroying polygon adjacency — e.g. a connected Image Plane becomes a pile of disconnected quads); `Tolerance` — Auto-detected by default (usually sufficient), manually adjustable.
- Gotchas / limits (p. 785-786):
  - Only welds **position** vertices — normals, texcoords, and other vertex streams are left as-is on the merged vertex, which can still produce hard edges.
  - Too-large tolerance can collapse edges/faces to points; models with detail spanning many orders of magnitude may have no single workable tolerance.
  - Vertices far from the origin can fail to merge (float precision: `bignumber + epsilon == bignumber`) — prefer welding in local coordinates, not world coordinates.
  - Can make things *worse*: e.g. Fusion's built-in cone has a duplicated top vertex per adjoining face (each with a different normal); welding merges them to one normal and can make the tip's lighting look wrong.
  - Not multithreaded.
  - Explicit warning: do not use Weld3D to reduce polygon count — it's meant for sub-0.001-distance duplicate cleanup only, not mesh decimation. If you can visually see a gap between vertices you're trying to weld in the 3D view, you're likely misusing the node.

## Modifier: Coordinate Transform

Solves the problem that a 3D object's authored position (e.g. `1,2,1`) often doesn't reflect its actual current position after further scale/offset/rotation downstream in the hierarchy (e.g. absolute location `10,20,5`) (p. 786-787).
- Add via right-click on any XYZ number field → **Modify With > CoordTransform Position**.
- Controls: `Target Object` (the 3D node producing the original coordinates — drag-drop from the node tree, right-click menu, or type the node name directly), `Sub ID` (target an individual sub-element, e.g. one Text3D character or one Duplicate3D copy), `Scene Input` (the 3D node whose output scene contains the object at its *new* location — drag-drop or right-click > Connect To submenu).

