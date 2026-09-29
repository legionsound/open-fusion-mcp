<!-- nodes-3d.md part 1 of 3; index: nodes-3d.md -->
# Fusion 3D Nodes (Chapter 29)

Scope: manual pages 680-795 (Fusion Page Effects, Chapter 29 "3D Nodes", plus the start of the Modifiers chapter). Use when: building, editing, or troubleshooting any Fusion 3D scene node tree (Merge3D hierarchies, cameras, primitives, imported geometry, text, texture/UV/material replacement, or the Renderer3D output stage) via the Resolve scripting API or `.comp`/`.setting` text.

## Mental model

1. **Everything terminates in Renderer3D.** Every 3D branch must end at a `Renderer3D` (`3Rn`) node, which converts the 3D scene to a 2D image. Nothing downstream of it is 3D anymore.
2. **Merge3D (`3Mg`) is the scene hub, not a blend.** It combines cameras, lights, geometry, and other Merge3D nodes into one shared space. Transform changes on a Merge3D move *everything* feeding it — this is how parenting/hierarchy works in Fusion 3D. Merge3D's own Controls tab does only one thing: `Pass Through Lights` (p. 727-728).
3. **Colored inputs are semantic, not decorative.** Orange = 3D scene/geometry input (nearly universal). Green = material/image input (2D image or 3D material). Other colors are node-specific (magenta = image/bevel, blue = effect mask, teal = extra image, white = required projective image). Always check per-node input lists below rather than assuming color meaning.
4. **A 2D image becomes a material or a plane depending on which input it hits.** Feed an image into a geometry node's green `MaterialInput` and it textures existing geometry; feed it into an `Image Plane 3D` and it also defines the plane's aspect ratio/geometry.
5. **Lighting is per-vertex by default, so subdivision = lighting quality.** The 3D viewers/renderer use vertex lighting unless per-pixel is chosen in the OpenGL renderer; low-subdivision primitives show faceted/fractured lighting. Increase `Subdivision Level` on primitives (Cube3D, Shape3D, Image Plane3D) before relying on lighting realism, especially before deforming with Bender3D or Displace3D (neither node adds vertices).
6. **Two render engines, different guarantees.** Software renderer = CPU, consistent cross-machine, required for soft shadows, needed for network rendering. OpenGL renderer = GPU-accelerated, faster, supports realistic DoF and custom supersampling, but cannot produce soft shadows and varies slightly by graphics card/driver (p. 739).
7. **Lights only affect the next Merge3D downstream**, unless that Merge3D's `Pass Through Lights` is enabled — critical for isolating projections/lighting passes (p. 728, p. 734).
8. **Common Controls families repeat on almost every node** — Visibility/Lighting/Matte/Blend Mode/Normals-Tangents/Object ID (Controls tab), Materials tab (Diffuse/Specular/Transmittance/Material ID), Transform tab (Translation/Rotation/Pivot/Scale/Use Target/Import Transform), and Settings tab (Hide Incoming Connections/Comments/Scripting). Documented once at the end; individual node entries only note deviations.
9. **Object ID / Material ID are per-scene numeric tags**, not per-node properties you read back directly — they render into aux channels (`ObjectID`, `MaterialID`) from the Renderer3D and are used to build mattes downstream (Object ID max 65534, 0 = empty).
10. **Texture coordinates (UV) are separate from materials.** A material node supplies pixels; a `UV Map 3D` node supplies/replaces the coordinates used to look those pixels up. They are usually authored in the reverse order they're applied: `Shape 3D > UV Map 3D > Transform 3D`, keeping the shape's own Transform tab untouched so texture doesn't slide when the object is later moved (p. 783).
11. **Two ways to project an image onto geometry**: Light-based projection (Camera3D's Projection tab, or Projector3D as a spotlight-like light — requires lighting enabled) vs. Texture-mode projection through a `Catcher` node (re-lightable, respects alpha as a hard clip). Camera Mapping in UV Map 3D is a third option that only sets UVs — the actual image must still be wired to the material's diffuse input separately.
12. **Normals/tangents are computed, not stored, for most primitives** — they're generated on demand (e.g., by a Renderer3D, or when a bump map needs tangents) and can be recomputed/fixed explicitly with `Replace Normals 3D`.
13. **Alembic and FBX import differently.** File > Import (Alembic Scene / FBX Scene) explodes a model into individual per-object nodes and preserves animation via Fusion transform nodes/splines (recommended for cameras/lights/animation). The raw `SurfaceAlembicMesh`/`FBXMesh3D` nodes import everything as a single mesh with one pivot, and FBXMesh3D specifically ignores animation.
14. **"Enable" checkboxes on effect nodes (Fog3D, Projector3D, Soft Clip, Replace Material 3D) are not the same as the node's red power switch.** The red switch disables the whole tool (pure pass-through, including Settings-tab scripts). The Enable/Enabled checkbox only turns off that node's effect while Settings-tab scripts etc. keep running.
15. **Radial vs. Perpendicular distance recurs in Fog3D and Soft Clip.** Default is perpendicular-to-a-plane-through-the-eye (can under/over-fog objects near frame edges); Radial fixes this by using true distance from the eye point but isn't always wanted.

## Alembic Mesh 3D [Abc]

Imports 3D geometry (mesh/camera/points/UV/normals with baked animation) from a .abc file exported by Blender/Cinema4D/Maya/etc. (p. 682-684).
- Preferred import path is **File > Import > Alembic Scene** (Fusion Studio) / **Fusion > Import > Alembic Scene** (Resolve) — explodes model/lights/camera/animation into individual nodes and saves transforms into Fusion splines/Transform3D nodes (re-editable, and reloaded from the comp, not the file, next session). The raw `SurfaceAlembicMesh` node imports the whole model as one object and always reloads meshes fresh from the file.
- Inputs: `SceneInput` (orange, optional — merges in extra 3D geometry), `MaterialInput` (green, optional — applies a 2D image as material to the imported geometry).
- Key controls (Controls tab):
  - `Filename` — path to the .abc file, editable.
  - `Object Name` — name of imported mesh; blank = entire Alembic contents import as one mesh; auto-set by Fusion when using the Import menu.
  - `Wireframe` — wireframe-only display/render (OpenGL renderer only), with a sub-option for wireframe anti-aliasing.
- Import Dialog options (shown once at import): `Hierarchy` (full parenting via Transform3D nodes vs. flattened transforms into one Merge — disable for animated files to avoid a rig-node explosion), `Orphaned Transforms` (Hierarchy-only — imports transform nodes that merely parent a mesh/camera, e.g. a skeleton rig), `Cameras` (imports Aperture/Angle of View/Plane of Focus/Near-Far clip; check Camera3D's Resolution Gate Fit if import fails; stereo info NOT imported), `InverseTransform` (World-to-Model inverse for cameras), `Points` (position-only — particle direction/orientation is lost), `Meshes` (enables UV/normals sub-options), `Animation > Resampling rate` (auto-detected fps; keep matched to source unless deliberately creating slow motion).
- Gotchas: Lights, Materials, Curves, multiple UV sets, and Velocities are **not supported** on Alembic import — use FBX for lights/cameras/materials, Alembic for meshes only (p. 683).

## Bender 3D [3Bn]

Bends, tapers, twists, or shears 3D geometry based on its bounding box; affects only geometry, passes lights/cameras/materials through unaffected (p. 685-687).
- Inputs: `SceneInput` (orange, required).
- Key controls:
  - `Bender Type` — Bend / Taper / Twist / Shear.
  - `Amount` — deformation strength.
  - `Axis` — meaning depends on Bender Type (e.g., the "elbow" axis for Bend, in conjunction with Angle).
  - `Angle` — direction of bend/shear about the axis; not shown for Taper/Twist.
  - `Range` — limits the effect to a portion of the geometry; unavailable when Bender Type = Shear.
  - `Group Objects` — treat multiple input objects (from a Merge3D or chained) as one object using their common center, instead of deforming each individually.
- Gotchas: Bender does **not** add vertices — increase `Subdivision Level` on the source primitive (Shape3D, Text3D, etc.) for quality results.

## Camera 3D [3Cm]

Virtual camera modeled on real-world camera controls (aperture, focal length, clip planes); can also project a 2D image (as an aligned image plane or as a true camera projection) and supports stereoscopic rigs (p. 688-696).
- Inputs: `SceneInput` (orange, optional — geometry linked to the camera's FOV), `ImageInput` (magenta, optional 2D image — enables Image Plane / Projection tabs), `RightStereoCamera` (green, optional — overrides the internal right-eye camera for stereo).
- Basic setup: connect Camera3D output into a Merge3D; view the Merge3D and right-click the viewer (or the axis label) → Camera > [name] to look through it. Dragging the camera icon from the toolbar onto the 3D view auto-connects it to the viewed Merge3D and switches the viewer to look through it. "Copy PoV To" in the viewer's contextual menu (Camera submenu) copies the current viewer angle onto a camera/spotlight/etc.
- Controls tab:
  - `Projection Type` — Perspective or Orthographic. Orthographic exposes only Near/Far clip and `Viewing Volume Size` (camera Z-distance doesn't change object scale, only viewing size does).
  - `Near/Far Clip` — distance units from the camera's focal point; objects outside are invisible. Ignored by the default perspective camera unless `Adaptive Near/Far Clip` is disabled. Smaller near-far range = more depth accuracy; widen Near Clip if distant objects show artifacts.
  - `Adaptive Near/Far Clip` — auto-fits clip planes to scene extents, overriding manual values; unavailable for orthographic cameras.
  - `Angle of View Type` — choose vertical/horizontal/diagonal measurement basis; recalculates `Angle of View`.
  - `Angle of View` / `Focal Length` — linked controls; `angle = 2 * arctan(aperture / 2 / focal_length)`. Use vertical aperture for vertical AOV, horizontal aperture for horizontal AOV.
  - `Plane of Focus` — distance used by the OpenGL renderer for depth-of-field.
  - **Stereo**: `Mode` = Mono / Toe-In / Off Axis / Parallel.
    - Toe-In: cameras rotate inward to a single focal point; simple but introduces vertical parallax/keystoning at edges; useful when focus point must equal convergence point or to match a live rig.
    - Off Axis (default, recommended): lenses shift inward (skewed frustum), no vertical parallax.
    - Parallel: cameras shift purely parallel; no vertical parallax but **no Convergence Distance control**.
    - `Rig Attached To` — Center / Left / Right: chooses which camera carries the onscreen transform controls, useful for matching a crane move.
    - `Eye Separation` — distance between stereo cameras (>0 reveals per-eye viewer controls).
    - `Convergence Distance` — Z-axis point where both eyes converge; only available in Toe-In/Off Axis.
  - **Film Back**: `Film Gate` (preset menu, auto-sets Aperture Width/Height), `Aperture Width/Height` (inches), `Resolution Gate Fit` — Inside/Width/Height/Outside/Stretch, mapping to Maya's Overscan/Horizontal/Vertical/Fill respectively (see full definitions p. 693 — Inside = scale to fit inside on the constrained axis possibly cropping the other; Width/Height = fit that one axis exactly; Outside = scale so image fully covers the gate; Stretch = non-uniform, may distort).
  - **Control Visibility**: `Show View Controls`, `Frustum`, `View Vector`, `Near Clip`, `Far Clip`, `Focal Plane`, `Convergence Distance` — each toggles/subdivides an onscreen guide.
  - `Import Camera` — supports `.lws`, `.ase`, `.ma`, `.xsi`. (FBX cameras import via File/Fusion > Import > FBX Scene instead.)
- Image tab (appears once ImageInput is connected): `Enable Image Plane`, `Fill Method` (Inside/Width/Height/Outside/Depth — same fit logic as Film Gate; `Depth` sets the image plane's distance from camera — note the camera's Z position does **not** affect image-plane distance).
- Materials tab: standard common Materials controls (Diffuse/Specular/Transmittance/Material ID).
- Projection tab (appears once ImageInput connected): `Enable Camera Projection`, `Projection Fit Method` (same 5 options), `Projection Mode` — Light (spotlight-style), Ambient Light, or Texture (re-lightable; requires a Catcher node on the material).
- Gotchas / Tips (p. 696):
  - Camera Projection: when importing a camera also used as a projector from a 3D app, the Controls-tab Resolution Gate Fit auto-matches the source app but the Projection-tab Fit Method does **not** — set it manually.
  - The camera's image plane is real geometry you can project onto, not just a viewer guide; to swap its image, insert a **Replace Material** node after the Camera node.
  - True Parallel Stereo: connect an external right camera to the green input, OR build separate left/right cameras, OR (Toe-In/Off Axis) set Convergence Distance to a very large value like 999999999.
  - Rendering overscan requires manually increasing the Film Back width/height by the overscan factor — overscan settings are never exported from 3D apps, so this applies to `.fbx`/`.ma` imported cameras too.

## Cube 3D [3Cb]

Basic primitive cube with six independently-textureable faces; commonly used as a shadow-caster or 3D-tracking placeholder (p. 697-699).
- Inputs: `SceneInput` (orange, optional — adds geometry), `NameMaterialInput` ×6 (one per face — 2D image or 3D material each; textures on these do not propagate to anything connected via SceneInput).
- Key controls: `Lock Width/Height/Depth` (locks to single `Size` slider), `Size`/`Width`/`Height`/`Depth`, `Subdivision Level` (raise for smoother vertex-lit shading), `Cube Mapping` (wraps the *first* texture across all six faces using a cross-layout texture), `Wireframe` (OpenGL renderer only).

## Custom Vertex 3D [3CV]

Advanced per-vertex geometry manipulation via scripted math expressions/LUTs; a code-like tool for C++/scripting-literate users (p. 699-704).
- Inputs: `SceneInput` (orange, required), `ImageInput1/2/3` (green/magenta/teal, optional compositing sources).
- Vertex attributes exposed: Position (`px,py,pz`), Normals (`nx,ny,nz`), Vertex Color (`vcr,vcg,vcb,vca`); also Texture Coordinates, Environment Coordinates, UV Tangents, Velocity. Missing attributes on input geometry default (e.g., missing normals → `(0,0,1)`); use `ReplaceNormals` beforehand to generate real ones. Modifying X/Y/Z does not update normals/tangents automatically — follow with `ReplaceNormals3D`.
- Tabs and variables:
  - **Numbers tab** (Numbers 1-8): dial controls; expression access `n1..n8` (current time) or `n#_at(float t)`.
  - **Points tab** (Points 1-8): 3D XYZ position controls; access `p1x,p1y,p1z...` or `p#x_at(t)` etc. — useful e.g. as a rotation-center reference.
  - **LUT tab** (LUTs 1-4): lookup-table splines; access via `getlut1(x)...getlut4(x)`, x = 0..1. Example: `R,G,B,A = getlut1(r1), getlut2(g1), getlut3(b1), getlut4(a1)` mimics a Color Curves node.
  - **Setup tab** (Setups 1-8): evaluated once per **frame** before anything else; results available as `s1..s4` to other expressions. Only frame-level variables are valid here (no per-pixel/per-vertex vars like X, Y, r1, g1...).
  - **Intermediate tab** (Intermediates 1-8): evaluated once per **vertex**, after Setup; results as `i1..i8`, usable by channel scripts (e.g., to build the new vertex position/normal/tangent/UV, or transform world-to-model space).
  - **Config tab**: `Random Seed` (+ Reseed button) for `rand()`/`rands()`; per-Number and per-Point `Show`/`Name` overrides (renaming doesn't change the expression variable name, still `n1`/`p1x` etc.).
- Gotcha: not all geometry has every attribute — most Fusion geometry lacks vertex colors (except particles/some FBX-Alembic imports); no geometry has environment coordinates; only particles have velocities.

## Displace 3D [3Di]

Displaces existing vertices along their normals using a reference image sampled via the geometry's texture coordinates (p. 705-706).
- Inputs: `SceneInput` (orange, required), `Input` (green, 2D displacement image — without it the node is a pass-through).
- Key controls: `Channel` (which image channel drives displacement), `Scale`/`Bias` (Bias applied first, then Scale), `Point to Camera` (displaces each vertex toward the camera instead of along its normal — e.g. for a camera's image plane, so the displaced plane looks unchanged through that camera but interacts correctly in Z with other 3D layers) + `Camera` (menu to pick which camera drives Point to Camera).
- Gotchas: Does not subdivide — raise the source geometry's Subdivision for finer displacement detail. Displacement image pixels may hold negative values. Passing a particle system through Displace3D disables the pEmitter's "Always Face Camera" option since each of a particle's four vertices is displaced individually.

## Duplicate 3D [3Dp]

Creates successive, transformable copies of connected geometry (arrays/patterns), with a separate Jitter tab for randomization and a Region tab to gate where copies appear (p. 707-711).
- Inputs: `SceneInput` (orange, required), `MeshInput` (green, appears only when Region tab's Region = Mesh).
- Controls tab:
  - `Copies` — range control; each copy is copied from the previous copy (chained). Setting First Copy > 0 hides the original.
  - `Time Offset` — offsets source animation per copy (e.g., -1.0 staggers a rotating cube's animation one frame per copy; useful for showing successive video frames on textured planes).
  - `Transform Method` — Linear (each copy's transform = base transform × copy index, independent) vs. Accumulated (each copy starts from the previous copy's result and transforms again).
  - `Transform Order` — order of Scale/Rotation/Translation application; defaults to SRT.
  - Translation (X/Y/Z Offset), Rotation (order buttons + XYZ sliders), Pivot (XYZ), Scale (`Lock XYZ` toggle + Scale slider(s)).
- Jitter tab: `Random Seed` + `Randomize` button, `Jitter Probability` (0-1, fraction of copies affected), `Time Offset` (random per-copy animation offset), Translation/Rotation/Pivot/Scale Jitter controls (Scale Jitter has its own Lock XYZ).
- Region tab: `Region Mode` — Ignore Region (default, no effect) / When Inside Region / When Not Inside Region. `Region` shape — Cube, Sphere, Rectangle, Mesh (reveals green mesh input), or All (whole scene — lets copies pop on/off if Region Mode is animated). Mesh-only sub-options: `Winding Rule` (technique for treating mesh as a volume — try alternates if irregular fit), `Winding Ray Direction` (alignment direction for treating polygon volume, like a depth-extrude), `Limit by Object ID` + `Object ID` slider (restrict region to one mesh when multiple meshes feed the green input).

## Extrude 3D [3Ex]

Converts a flat Fusion Shape node into 3D geometry via extrusion (Z-axis push) plus optional beveling (p. 711-713).
- Inputs: `BevelMaterialInput` (pink, 2D image or 3D material for the bevel faces — disables Basic Material tab if a 3D material is connected), `ShapeInput` (yellow, required — a Shape node), `MaterialInput` (green, 2D image or 3D material for the main faces — same disable behavior).
- Key controls: `Extrusion Style` — Classic (uniform) or Custom (exposes an editable Extrusion Profile graph for shapes like picture frames/knurled buttons); `Extrusion Depth`; `Extrusion Subdivisions`; `Bevel Depth`; `Bevel Width`; `Smoothing Angle`; `Bevel Front`/`Bevel Back` (independent front/back bevel toggles).

## FBX Exporter 3D [FBX]

Exports a Fusion 3D scene to FBX (and .3ds/.dae/.dxf/.obj); each Fusion node becomes one object in the file, named after the node (p. 714-716).
- Auto-Clip-Browse preference (Preferences > Global > General, Fusion Studio; Fusion > Fusion Settings > General, Resolve) auto-opens a save dialog when the node is added.
- Used like a Saver — Render button in the toolbar triggers export.
- Inputs: `Input` (orange, required — the 3D scene to export).
- Key controls: `Filename` (+ Browse), `Format` (FBX/3ds/dae/dxf/obj — obj does not support animation), `Version` (per-format; hidden if only one option; FBX "Default" = FBX2011), `Frame Rate`, `Scale Units By`, `Geometry`/`Lights`/`Cameras` checkboxes (selectively export scene element types), `Render Range` (embeds range metadata), `Reduce Constant Keys` (strips redundant keyframes), `File Per Frame (No Animation)` (exports numbered file sequence, disables animation export; reveals `Sequence Start Frame`).

## FBX Mesh 3D [FBX]

Imports polygonal geometry from FBX/OBJ/3DS/DAE/DXF as a single combined mesh with one pivot; ignores animation (p. 716-718).
- Alternative: File > Import > FBX Scene creates individual per-object nodes and preserves animation.
- Auto Clip Browse preference (see FBX Exporter) auto-opens the import file browser.
- Inputs: `SceneInput` (orange, optional — merges extra geometry), `Material Input` (green — 2D image or 3D material; disables Basic Material tab if 3D material connected).
- Key controls: `Size` (rescale — FBX meshes tend to be much larger than Fusion's default unit scale), `FBX File` (+ Browse; supports `.fbx` ascii/binary 5.0, `.dxf`, `.3ds`, `.obj`, `.dae`), `Object Name` (read-only, set by Fusion on Import menu use; blank = whole file as one mesh), `Take Name` (read-only — FBX animation "Take" to import; blank = no animation), `Wireframe` (OpenGL renderer only).

## Fog 3D [3Fo]

3D-space depth-cue fog that retextures geometry by distance-from-camera color correction; fully compatible with anti-aliasing/DoF, unlike 2D Fog (p. 719-721).
- Inputs: `SceneInput` (orange, required), `FogDensityTex` (green, optional — multiplies fog color; image is effectively projected from the camera).
- Placement: after the Merge3D containing the scene.
- Key controls: `Enable` (effect-only toggle, distinct from the node's red power switch), `Show Fog in View` (by default fog only shows through a Camera node view; enable to see it from any viewpoint), `Color`, `Radial` (perpendicular-distance fog by default — can under-fog frame edges as camera pans; Radial uses true eye-point distance instead, at the cost of e.g. unevenly fogging a close image plane's center vs. edges), `Type` — Linear / Exp / Exp2 falloff, `Near/Far Fog Distance` (units from camera; fog starts at Near, maxes at Far; cumulative with object distance).

## Image Plane 3D [3Im]

Produces 2D planar "card" geometry in 3D space, most often to bring a 2D clip into a 3D composite; aspect ratio is driven by the connected material image (use Shape3D instead if you don't want image aspect to affect geometry) (p. 722-723).
- Inputs: `SceneInput` (orange, optional — not required since the node makes its own geometry), `MaterialInput` (green — 2D image or 3D material; supplies texture + aspect ratio; disables Basic Material tab if 3D material connected).
- Key controls: `Lock Width/Height` (even X/Y subdivision when on, default on; unlocked exposes separate X/Y subdivision sliders), `Subdivision Level`, `Wireframe` (OpenGL renderer only).

## Locator 3D [3Lo]

Converts a 3D point to 2D screen-space coordinates for use by other nodes' expressions/modifiers (p. 724-726).
- Inputs: `SceneInput` (orange, required — must include the camera through which coordinates project; best placed right after the Merge3D that introduces that camera), `Target` (green, optional — when connected, the Locator sits at the target object's transform center and the Transform tab's translation XYZ become *offsets in the object's local space*, useful for tracking a moving object downstream of further transforms).
- Key controls: `Size` (crosshair size), `Color`, `Sub ID` (select a subelement, e.g. one character of a Text3D or one Duplicate3D copy), `Make Renderable` (OpenGL-only visible rendering; ignored by software renderer), `Unseen by Camera` (visible in viewers, excluded from Renderer3D output — only shown once Make Renderable is on), `Camera` (which scene camera defines the 2D projection space), `Use Frame Format Settings` (override W/H/pixel-aspect with the comp's Frame Format prefs), `Width`/`Height`/`Pixel Aspect` (must match the target renderer's output dimensions for correct 2D transform; right-click for a frame-format preset menu).
- Scripting hook: right-click a 2D control (e.g., a Mask center) → Connect To > Locator 3D > Position to wire it to the Locator's output.

## Merge 3D [3Mg]

The hub node that combines separate 3D elements (planes, cameras, lights, other Merge3Ds) into one shared environment; forms the basis of all parenting (p. 726-728).
- Inputs: `SceneInput[#]` — dynamically-added multicolored inputs, unlimited count, always one free slot.
- Controls tab: only `Pass Through Lights` — when enabled, lights connected to this Merge3D propagate to its output to affect downstream elements (normally lights stop here); commonly toggled off to keep projections from leaking onto geometry introduced later in the tree.
- Multiple Merge3D nodes can be chained for lighting control/organization; the final one in a chain must feed a Renderer3D.

## Override 3D [3Ov]

Applies object-specific option overrides (wireframe, visibility, lighting, matte, ID, etc.) to **every** object in the input scene simultaneously; the only way to set wireframe/visibility/lighting/matte/ID on 3D particle systems and on Text3D (p. 728-729).
- Inputs: `SceneInput` (orange — Merge3D output or any 3D-scene-producing node).
- Controls: pairs of `Do [Option]` (enables the override) + `[Option]` (the value applied to all upstream objects once enabled). Individual option semantics are documented under whichever geometry node normally hosts them (Image Plane, Cube, Shape, etc.), not repeated here.
- Common workflow: Override3D (turn off "Affected by Lights") → Replace Material 3D (apply a Falloff shader) to build an isolated falloff pass.

## Point Cloud 3D [3PC]

Represents null-object point clouds from 3D tracking/modeling apps (e.g., tracked feature positions from a camera solve), imported from file or generated by Camera Tracker (p. 730-733).
- Inputs: `SceneInput` (orange only).
- Key controls: `Style` (crosshairs vs. points), `Lock X/Y/Z` + `Size X/Y/Z` (crosshair arm sizes), `Density` (probability a given point displays; 1 = all, 0.2 ≈ every fifth point), `Color`, `Import Point Cloud` (supports `.ma`, `.ase`, `.lws`, `.xsi`), `Make Renderable` (OpenGL viewer/render only — software renderer can't render crosshairs), `Unseen by Camera`.
- Onscreen contextual menu (when node selected) + shortcuts: Find (Shift+F, search by name), Rename (F2, appends 4-digit suffix e.g. `window0000`, `window0001`; names must be valid Fusion identifiers — no spaces, can't start with a number), Delete (Del), Publish (Shift+P, exposes a coordinate control for the point's live position — points aren't exposed by default), Unpublish (Shift+U), Select All (Shift+A), Create New Point (Shift+C), Toggle Names None/Selected/Published/All (Shift+N), Toggle Locations (Shift+L), Create a Shape at Selected Points (Shift+S), Create and Fit an ImagePlane to Selected Points (Shift+I), Create a Locator at Selected Points (Shift+O).

## Projector 3D [3Pj]

Projects a 2D image onto 3D geometry as a spotlight-like light (or as a re-lightable texture via Catcher); distinct from Camera3D's built-in projection, which is aligned precisely to a camera instead (p. 734-738).
- Behaves like a variant of the SpotLight node: lighting must be enabled to see results; emitted light is diffuse/specular (affects normals, can cause specular highlights — switch to Ambient Light channel to avoid); casts shadows if Enable Shadows is on; only affects objects feeding the first downstream Merge3D unless that Merge3D's Pass Through Lights is enabled; alpha in the projected image does **not** clip geometry in Light/Ambient modes (use Texture mode for that); overlapping projections add their light contributions.
- Texture-mode projections only strike objects whose material uses a Catcher node, and Texture-mode alpha **does** clip geometry.
- Inputs: `SceneInput` (orange, optional — if connected, spotlight transforms also move the rest of the attached scene), `ProjectiveImage` (white, required — the 2D image to project).
- Controls tab: `Enabled` (effect-only toggle, distinct from red power switch), `Color` (multiplies input image before projecting), `Intensity` (Light/Ambient modes: projection brightness; Texture mode: scales Color-multiplied output), `Decay Type` — No Falloff (default) / Linear / Quadratic, `Angle` (cone angle of full intensity, max 90°), `Fit Method` — Inside/Width/Height/Outside/Stretch, same 5 options and logic as Camera3D's Resolution Gate Fit (see that entry); key difference: the Projector3D's "cone" is actually a **square** pyramid of light (equal X/Y angle of view) whose apex sits at the projector, whereas Camera3D's pyramid can be non-square per its Film Back — image aspect never changes the pyramid's X/Y angles, only how the image is scaled to fit it. `Projection Mode` — Light / Ambient Light / Texture (Texture mode pairs with a Catcher node; a handy trick is wiring a Catcher into a 3D Material's Specular Texture input so a Blinn-type material picks up the projection as part of its specular highlight).
- **Shadows** (spotlight-derived): `Enable Shadows` (default on), `Shadow Color` (default black), `Density` (shadow transparency; 1.0 = fully transparent — read literally from manual, i.e. higher density = more see-through), `Shadow Map Size`, `Shadow Map Proxy` (proxy/auto-proxy shadow map scale, e.g. 0.5 = 50% size), `Multiplicative Bias`/`Additive Bias` (fixes Z-fighting between shadow and receiving surface — tune multiplicative first, then additive; too little causes self-shadowing, too much detaches the shadow), `Force All Materials Non-Transmissive` (Z-only shadow map instead of RGBAZ — much faster, 1/5th memory, but no "stained glass" colored shadows), `Shadow Map Sampling` quality, `Softness` — None (hard edge, 1-sample, fastest) / Constant (fixed-width filter via `Constant Softness` slider) / Variable (softness grows with caster-receiver distance; exposes `Softness Falloff`, `Min Softness`, `Max Softness`).
- Camera3D projection vs. Projector3D: use Camera3D's projection when it must match a real/virtual camera exactly (more control over aperture/film-back/clip planes); use Projector3D when you want a dedicated light-like layering/texturing tool with intensity/color/decay/shadow control.

