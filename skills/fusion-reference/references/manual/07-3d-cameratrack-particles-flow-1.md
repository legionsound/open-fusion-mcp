<!-- 07-3d-cameratrack-particles-flow.md part 1 of 2; index: 07-3d-cameratrack-particles-flow.md -->
# 3D Compositing, Camera Tracking, Particles, Optical Flow and Stereo (concepts)
Scope: Fusion 21.1 manual pp. 586-679 (Ch. 25 3D Compositing Basics, Ch. 26 3D Camera Tracking, Ch. 27 Particle Systems, Ch. 28 Optical Flow and Stereoscopic Nodes), plus targeted cross-checks from the node chapters (Camera 3D pp. 688-696, Renderer3D pp. 739-747, Alembic/FBX pp. 682-718, Fog 3D/Soft Clip pp. 719-721/762-764, 3D Light Nodes p. 800-802, Particle Nodes pp. 1429-1467), each marked with its page. Use when: building or debugging any 3D scene, camera projection, 3D text, imported FBX/Alembic, camera track/matchmove, particle system, optical-flow retime, or stereo comp in Fusion; or when choosing between the Software and OpenGL renderers.

## Mental model

1. **Every 3D node outputs a complete 3D scene**, not an object in a global world (p. 596). Scenes only combine when wired into a Merge3D (or chained object-to-object). There is no "global scene" to add things to.
2. **3D data cannot touch 2D inputs.** A Renderer3D must sit at the end of every 3D branch to turn the scene into a 2D image before Blur, Merge, etc. (p. 596). An ImagePlane3D cannot feed a Blur; a Merge3D cannot feed a 2D Merge.
3. **Canonical chain** (toolbar order, left to right = wiring order): ImagePlane3D / Shape3D / Text3D -> Merge3D -> Camera3D + SpotLight3D into the Merge3D -> Renderer3D (p. 590). Clicking the 3D toolbar buttons left to right builds a working scene.
4. **Parenting is topology.** Transforms on a Merge3D apply to everything upstream of it (geometry, lights, cameras, other Merge3Ds); transforms on an upstream Merge3D never affect downstream ones (pp. 595, 606).
5. **Lights do not cross Merge3D boundaries by default.** Pass Through Lights is off, so lights only illuminate objects in their own Merge3D unless enabled upstream (pp. 594, 611).
6. **Lighting is opt-in twice**: viewer (right-click > 3D Options > Lighting / Shadows) and render (Renderer3D Enable Lighting / Enable Shadows). With lighting off, objects look lit by 100% ambient light (p. 610). With lighting on and no lights, objects render black (p. 742).
7. **Renderer choice is a feature trade-off**: Software = soft shadows, alpha/colored shadows, huge textures, consistent cross-machine output; OpenGL = speed, supersampling, depth of field (Accumulation Effects), wireframe, Cryptomatte. You cannot get soft shadows and DOF from one renderer; render two passes and combine in 2D (pp. 597-598).
8. **Materials are RGBA per-pixel streams.** Material outputs connect into other material inputs like images, so shaders composite like images (p. 620). Default material on every geometry node is Blinn ("Standard").
9. **Fusion units are unitless "units"**; imported files keep their numeric scale, so 100 mm becomes 100 units (p. 629). Camera clip, fog and soft-clip distances are in these units from the camera.
10. **Eyespace Z is negative**: Fusion's camera sits at (0,0,0) looking down the Z-axis, so Z values get more negative with depth (p. 671). Gizmo colors: RGB = XYZ (p. 604).
11. **Camera tracking = Track (2D features) -> Camera (film gate, focal length) -> Solve (iterate) -> Export (camera + point cloud scene)** in a single Camera Tracker node (p. 642). It needs parallax.
12. **Particles**: pEmitter (source) -> optional forces/pMerge -> pRender (required). pRender outputs 2D image or 3D geometry; 3D mode feeds a Merge3D so particles can be lit and cast shadows (pp. 660-662).
13. **Optical flow and disparity live in hidden aux channels** (Vector/BackVector, Disparity) as un-normalized pixel shifts. Nodes either generate, destroy, pass through, or internally construct them (p. 672). Pre-render them to OpenEXR because they are slow.

---

## Part 1: 3D scene architecture

### Node roster (toolbar abbreviations from the 3D Nodes contents, p. 681)
| Node | Abbrev | Role |
|---|---|---|
| Image Plane 3D | 3Im | 2D image on an auto-scaled plane in 3D (p. 627) |
| Shape 3D | 3Sh | Primitives: plane, cube, sphere, cylinder, cone, torus (p. 627) |
| Cube 3D | 3Cb | Cube with six inputs, one texture per face (p. 627) |
| Text 3D | 3Txt | 3D Text+ with extrusion and bevel; no Text+ multi-layer shading (p. 627) |
| FBX Mesh 3D | FBX | Imports FBX/OBJ/3DS/DAE/DXF geometry (p. 716) |
| Alembic Mesh 3D | Abc | Imports .abc meshes (p. 682) |
| FBX Exporter 3D | FBX | Exports scene to .fbx/.dae (p. 629) |
| Merge 3D | 3Mg | Combines unlimited 3D inputs; parenting; light pass-through (p. 593) |
| Transform 3D | 3XF | Transform a scene branch (p. 603) |
| Camera 3D | 3Cm | Virtual camera, stereo, projection (p. 607) |
| Renderer3D | 3Rn | 3D scene to 2D image (p. 596) |
| Point Cloud 3D | 3PC | Imported tracker locator clouds (p. 637) |
| Projector 3D | 3Pj | Projects images as light or texture (p. 624) |
| UV Map 3D | 3UV | Camera-projected UVs (p. 625) |
| Override 3D | 3Ov | Batch-change IDs and similar per-object settings (p. 635) |
| Replace Material 3D | 3Rpl | Retextures every object in the incoming scene (p. 592) |
| Fog 3D | 3Fo | Depth-cued fog in 3D (p. 633) |
| Soft Clip | 3SC | Fades geometry near camera (p. 633) |
| Locator 3D | 3Lo | Single tracked point / position readout |
| Lights | 3AL, 3DL, 3PL, 3SL | Ambient, Directional, Point, Spot (p. 609). A DomeLight [3Do] also exists in 21.1 (image-based sphere light, p. 802) |
| Materials | 3Bl, 3Ph, 3CT, 3Wd, 3RR, 3Bol, 3SMM | Blinn, Phong, Cook Torrance, Ward, Reflect, Channel Boolean, Stereo Mix |
| Textures | 3Tx, 3Bu, 3Ca, 3SpM | Texture 2D, Bump Map, Catcher, Sphere Map (also Cube Map) |

### Merge3D (3Mg)
Combines any number of 3D inputs; result is ordered by each object's absolute 3D position, not by input order (p. 593).
- **Pass Through Lights** (Controls tab, off by default): lets lights connected to this Merge3D illuminate objects in downstream Merge3Ds (p. 594). Keep off to confine a light (e.g., a spot on a wall that must not spill on the ground in another sub-scene).
- **Transform tab**: moves/rotates/scales everything connected, including lights and particles, around a common pivot (p. 595).
- Merge3Ds nest: build sub-scenes, then combine them.
- **Pattern "transform upstream, light downstream"**: animate objects in upstream Merge3Ds; put camera and lights in the final Merge3D so object animation never disturbs lighting or framing (p. 595).
- You can view the scene *from* a Merge3D or Transform3D (viewer Camera > Other) and use viewer navigation to reorient that node (p. 601).

**Combining objects directly** (no Merge3D): wire a 3D object's output into another 3D object's input. The downstream node's transform also moves all upstream objects; works for lights and Camera3D too. Good for rigs that always travel together (p. 593).

### Renderer3D (3Rn)
Every 3D scene must terminate in at least one Renderer3D (p. 739). Uses the camera chosen in its **Camera** menu; **Default** = first camera found; no camera = default perspective view, which "rarely provides a useful angle" (pp. 596, 741). Output can be any resolution, with fields, color depth and pixel aspect options (p. 596).
- Inputs: SceneInput (orange, required), EffectMask (blue) (p. 739).
- **Renderer Type** menu: Software Renderer (default), OpenGL Renderer, OpenGL UV Renderer; third-party renderers can be added. Controls below the menu change per engine (pp. 597, 741).
- **Eye** menu: Mono (ignores camera stereo), Left, Right, Stacked (one above the other), Layers (eyes as separate layers) (p. 741).
- **Reporting**: four checkboxes (print warnings / errors to console; abort on warning / error); all four on by default (p. 741).
- **Multilayer output** (p. 740): Renderer3D defaults to outputting seven lighting pass layers: Shadow, Diffuse, Specular, Ambient, Reflect, Refract, Fog, while still rendering the complete result. Preview via the viewer layer control. Rebuild with Merge, MultiMerge or Channel Booleans: **add** every pass except **Shadow, which is multiplied**.
- **Motion blur** lives in the Renderer3D's Common Controls (Settings tab). With particles in the scene, pRender motion blur settings must **exactly match** the Renderer3D's, or subframe renders conflict and give incorrect results (p. 739).

#### Renderer comparison (pp. 597-598, 739-747, 617-618, 625)
| Capability | Software Renderer | OpenGL Renderer | OpenGL UV Renderer |
|---|---|---|---|
| Engine | CPU; consistent on all machines, "essential" for network rendering | GPU; output may vary by card and driver | GPU; outputs unwrapped texture |
| Speed | Slowest | Potentially orders of magnitude faster | n/a |
| Soft shadows (Constant/Variable, Spread) | Yes (required for them) | No | n/a |
| Alpha in shadow maps / colored shadows | Yes | No: shadow always cast from whole object, always black | n/a |
| Textures > ~8K (more than half GPU max texture size) | Yes, full quality | Limited | n/a |
| Depth of field | No | Yes, via Accumulation Effects | n/a |
| Supersampling anti-aliasing | Not listed | Yes, per channel, LowQ/HiQ rates, filters | n/a |
| Transparency | Always Sorted (Accurate) | Menu: Z Buffer (fast), Sorted (accurate), Quick Mode (particles) | n/a |
| Output aux channels listed | RGBA, Z, Coverage, BgColor, Normal, TexCoord, ObjectID, MaterialID | RGBA, Z, Normal, TexCoord, ObjectID, MaterialID (AA notes also mention WorldCoord, Vector, BackVector) | n/a |
| Lighting Mode | full | Per-vertex (fast, blocky on low-poly) or Per-pixel (better) | optional baked lighting |
| Wireframe render, Cryptomatte | No | Yes (Cryptomatte for objects and materials, "hardware renderer") | n/a |
| Catcher projections | Overlaps combined in Catcher (mean, median, blend...) | One catcher per projector; combine with another material | n/a |
| Color depth | per Image tab | Respects Image tab Color Depth; int16/float32 can slow some GPUs | n/a |

"Hardware Renderer" in the light-node notes refers to the GPU/OpenGL renderer (inference from context, pp. 746, 800).

**OpenGL anti-aliasing (pp. 743-745)**
- **Enable (LowQ/HiQ)** checkboxes, **Supersampling LowQ/HiQ Rate** (rate 4 at 1920x1080 renders 7680x4320 internally). "Typically 8 x 8 supersampling (64 samples per pixel) is sufficient." Tile rendering keeps memory low versus rendering big and using Resize.
- Interactive playback skips AA unless HiQ is on; final renders always supersample if enabled.
- Particles (points) and locators (lines) render at original size regardless of supersampling, so they look thinner than expected.
- Color AA is much slower than aux AA; color might be fine at 1 x 3 while Z/WorldPosition may need 4 x 12. Only anti-alias **WorldCoord and Z**; strongly disable AA on Material ID, Object ID, TexCoord, Normal, Vector, BackVector (blended values produce wrong-colored pixels). SS Z-buffer can help some tasks but hurt Merge PerformDepthMerge.
- **Filter Type**: Box, Bi-Linear (triangle), Bi-Cubic (quadratic), Bi-Spline (cubic), Catmul-Rom, Gaussian, Mitchell, Lanczos, Sinc, Bessel; **Window Method** (Hanning, Hamming, Blackman) appears only for Sinc/Bessel.
- **Accumulation Effects**: Enable Accumulation Effects + Depth of Field, then Quality and Amount of DoF Blur. Blurrier out-of-focus needs higher Quality; low Amount keeps more in focus. Focus comes from Camera3D Plane of Focus; animate it for rack focus (pp. 608, 745).
- Other OpenGL controls: Texture Depth (+ warn about unsupported depths), Shading Model (Smooth = viewer, Flat = faster), Wireframe, Wireframe Anti-Aliasing (p. 746).

**OpenGL UV Renderer** (pp. 598, 747): outputs an unwrapped texture of upstream objects at the Image tab resolution. Uses: bake projections to speed renders; paint/fix in 2D then re-apply via Texture2D (e.g., change a phone number on a tracked shop sign; retouch seams of multiple DSLR projections; temporal-median a clean road plate from projected footage). Cautions: turn object lighting off when reusing a lighting-baked texture; mirrored/shared UV regions break baked lighting; unwrapping several meshes at once overlaps in 0-1 UV space; **UV Gutter Size** 0 causes seams, increase it.

### Transparency sorting (p. 602)
OpenGL renderer and viewers default to fast Z-buffer sorting, which can mis-order semi-transparent objects. Right-click viewer > Transparency > Z-buffer (fast) or Sorted (accurate). Renderer3D shows the same menu in OpenGL mode. Sorted mode **does not support shadows in OpenGL**. Software renderer always sorts accurately. Rule: overlapping transparency -> Sorted/Quick; otherwise Z-buffer.

### The 3D Viewer (pp. 599-603)
- Viewing any node with 3D output switches the viewer to 3D; performance depends on GPU/OpenGL.
- **Viewpoint**: right-click > Camera submenu, or right-click the axis label in the viewer corner: Perspective, Front, Top, Left, Right, any cameras and lights, and Camera > Other for Merge3D/Transform3D.
- **Navigation**: pan = middle-drag; dolly = middle+left drag left/right, or Command + scroll; orbit = Option + middle-drag. **Shift-F** fit all, **F** fit selection (all if none), **D** rotate view to look at selected object's center without moving.
- Selecting a 3D node in the Node Editor selects it in the viewer.
- **Looking through a camera or light and navigating moves that camera/light** (p. 601). Useful for framing; dangerous if you only meant to look.
- Viewer frame aspect may differ from the render: enable Guides > Frame Aspect; toggle guides with **Command-G** (p. 689).
- Dragging the camera toolbar icon onto the 3D view auto-connects it to the viewed Merge3D and looks through it; **Copy PoV To** (Camera submenu) copies the current view to a camera/spotlight/object (p. 688).
- **Material Viewer**: viewing a 3D > Material node shows it on a lit OpenGL sphere. Right-click for Shape, Renderer, Lighting > Enable Lighting / Light Position; Option+middle-drag rotates; middle-drag moves the light; A/B buffers compare materials; no pan/zoom (pp. 602-603).

### Transforms, pivot, target, parenting (pp. 603-606)
- Transform tab on Merge3D, all 3D objects, Transform3D: Translation (local space), Rotation (around own center), Scale (Lock XYZ).
- Onscreen modes: **Q** position, **W** rotation, **E** scale. Drag a colored axis to constrain; drag center for free; **Option-drag** anywhere translates freely in XYZ. With Lock XYZ on, only red/center handles scale (uniform).
- **Pivot** X/Y/Z offsets rotation/scale center.
- **Use Target** (Transform tab) + Target Position X/Y/Z: object always faces the target. Example: connect a spotlight's target XYZ to an image plane's XYZ so it always aims at it (p. 606).
- Parenting example: two spheres in a Merge3D (moon orbiting earth), that Merge3D into another Merge3D (orbiting the sun).

### Camera3D (3Cm) essentials (pp. 607-609, 688-696)
Inputs: **SceneInput** (orange; geometry linked to camera FOV / receives projection), **ImageInput** (magenta; 2D image for image plane or projection), **RightStereoCamera** (green; another Camera3D overriding the right eye) (p. 688). Connect to a Merge3D; viewing the camera node alone shows an empty scene.

| Control | Behavior |
|---|---|
| Projection Type | Perspective or Orthographic. Ortho shows only Near/Far clip and **Viewing Volume Size** (Z distance does not change ortho scale) |
| Near/Far Clip | In scene units from camera. **Ignored by the default perspective camera unless Adaptive Near/Far Clip is disabled.** Smaller range = more depth precision; artifacts on distant objects -> increase Near Clip |
| Adaptive Near/Far Clip | Auto-fits clip planes to scene extents; overrides Near/Far; not for ortho |
| Angle of View Type | Vertical / Horizontal / Diagonal measurement; switching recalculates Angle of View |
| Angle of View / Focal Length | Linked. Focal length in mm. `angle = 2 * arctan(aperture / 2 / focal_length)`; use vertical aperture for vertical AoV, horizontal for horizontal |
| Plane of Focus | Distance used by the OpenGL renderer for DOF; show it via Control Visibility > Focal Plane (green plane) |
| Stereo Mode | Mono (default), Toe In (converging rotation; keystoning/vertical parallax), Off Axis (default stereo method, "correct way", lens shift, no vertical parallax), Parallel (no convergence control) |
| Rig Attached To | Center / Left / Right: which camera carries the transform |
| Eye Separation, Convergence Distance | Convergence only in Toe In / Off Axis |
| Film Gate | Preset camera list; sets Aperture Width/Height |
| Aperture Width/Height | **Inches** |
| Resolution Gate Fit | Inside, Width, Height, Outside, Stretch (= Maya Overscan, Horizontal, Vertical, Fill); matters only when film gate aspect differs from output |
| Control Visibility | Show View Controls, Frustum, View Vector, Near Clip, Far Clip, Focal Plane, Convergence Distance |
| Import Camera | .lws, .ase, .ma, .xsi. FBX cameras come via Fusion > Import > FBX Scene |

Image tab (appears only when a 2D image is on the magenta input): Enable Image Plane, Fill Method (Inside/Width/Height/Outside), **Depth** slider sets plane distance; **camera Z position does not change image-plane distance**. The image plane is real geometry you can project onto; to use a different image on it, add Replace Material after the camera (pp. 694-696).
Projection tab: Enable Camera Projection, Projection Fit Method, Projection Mode = Light (spotlight), Ambient Light, Texture (needs a Catcher on the material). Light projection needs Renderer3D lighting enabled (p. 695).
Tips (p. 696): sync Fit Resolution Gate in Controls and Projection tabs manually for imported projector cameras. True parallel stereo: connect a right camera to RightStereoCamera, build separate L/R cameras, or set Convergence Distance to 999999999. **Overscan**: enlarge film back width/height by the needed factor (overscan is not exported from 3D apps).

**Importing cameras** (p. 609): Maya and XSI splines import natively; 3ds Max and LightWave animation is sampled and keyed every frame. Inspector bottom > Import Camera; **Force Sampling** samples every frame for any format. Bake parented or rigged cameras in the 3D app first.

### Lighting and shadows (pp. 609-618, 800-802)
| Light | What matters | Shadows |
|---|---|---|
| Ambient | Uniform base level; position has no effect | Never; fills shadows |
| Directional | Parallel rays (sun); rotation only, position/scale ignored | Yes in 21.1, needs OpenGL ("Hardware") renderer for shadows (pp. 612, 800) |
| Point | Bulb; ignores rotation | Yes, needs OpenGL renderer (p. 612) |
| Spot | Cone with falloff; position + rotation | Yes, Software or OpenGL |

- A scene with no lights uses a default directional light that disappears when you add any light (p. 609).
- Per-object **Lighting** controls on ImagePlane3D, Cube3D, Shape3D, Text3D, FBXMesh3D: **Affected By Lights**, **Shadow Caster**, **Shadow Receiver** (pp. 610-612).
- Shadows need: light's **Enable Shadows** (on by default), viewer shadows toggle, and Renderer3D **Enable Shadows** (p. 612).
- **Shadow Map Size** = depth map pixels; wider cones need larger maps; stop at diminishing returns (p. 613). **Shadow Map Proxy** scales the map for proxy/LoQ (Ch. 25 says "a value of 4 ... represents a 40% proxy"; the light-node chapter says 0.5 = half resolution; treat as a fraction/percentage and verify in the UI).
- **Softness**: None (hard, fastest, may alias), Constant (uniform), Variable (softer with distance; reveals **Spread**, **Min Softness**, **Max Softness**, **Filter Size**). Soft shadows = Software renderer only. Filter Size caps blur as a percentage of shadow map size; smaller = faster but can clip softness (pp. 613-614).
- **Z-fighting fix**: raise **Multiplicative Bias** until most fighting is gone, then **Additive Bias** for the rest. Too little bias = self-shadowing; too much = detached shadow; softer shadows need more; bias may need animating (p. 614).
- **Force All Materials Non-Transmissive** (spotlight): shadow map ignores material transmittance (p. 614).

### Materials and textures (pp. 615-624)
Material components (shared by illumination models):
| Component | Meaning |
|---|---|
| Diffuse | Base color/texture; opacity usually set here |
| Alpha | Transparency to diffuse only; near-zero alpha drops the pixel including specular |
| Opacity | Fades whole material including specular; **cannot be mapped** |
| Specular Color / Intensity / Exponent | Highlight color, brightness, falloff (higher exponent = smaller sharper). Plastics/glass: white specular; metals: tinted by material color |
| Transmittance (Software renderer) | How light passes through for shadows (stained glass). Color (1,1,1) = fully transmissive, (1,0,0) = only red passes. Opaque + 100% transmittance behaves emissive |
| Alpha Detail | 0 = opaque parts cast full shadow; 1 = alpha sets shadow density |
| Color Detail | 0 to 1 brings diffuse color/texture into the shadow |
| Saturation | Blend shadow tint between full color and luminance only |

Illumination models (3D > Material, p. 619):
| Model | Use |
|---|---|
| Standard | Built-in Material tab of every geometry node; Blinn with one diffuse texture (alpha = opacity). Connecting any material to the Material input hides it |
| Blinn | General purpose, metal or dielectric; adds texture inputs for specular color, intensity, exponent, bump |
| Phong | Same diffuse; wider highlights at grazing angles, sharper at high exponent |
| Cook-Torrance | Microfacet + Fresnel specular; mappable Roughness and Refractive Index |
| Ward | Anisotropic highlights (brushed metal, fabric) elongated in U or V; **requires good UVs** |

Textures use the geometry's UVs; Texture2D translates in UV space and sets filtering/wrap (p. 620). Composite materials: e.g., Blinn output into Ward's diffuse, or add Ward's anisotropic specular onto Blinn with a Channel Boolean material (p. 621).

**Reflect (3RR)** (pp. 621-622): environment-map reflection/refraction, no illumination model (does not respond to lights), so combine with Blinn/Phong/Cook-Torrance/Ward. Inputs: Background Material (opacity for refraction + base color), Reflection Color Material, Reflection Intensity Material, Refraction Tint Material, Bump Map Texture. Blinn into Reflect's Background = reflection added on top; Reflect into Blinn's Diffuse Color = reflection multiplied by diffuse and lit. Environment maps assume infinite distance: no self-reflection, no inter-object reflection; each object needs its own cube map. Cube Map and Sphere Map nodes build env maps. Tips: reflection strength 0.1-0.3 (chrome higher); 128x128 blurred cube map when detail is not needed; refracted pixels get alpha 1; no refraction visible -> check the background material's alpha/opacity.

**Bump maps** (pp. 623-624): Image -> **BumpMap** node -> material's Bump input. Fusion blocks connecting a normal map directly to a material's bump input. Set type **HeightMap** or **BumpMap** explicitly (Fusion cannot detect). Height map: white high, black low; slope matters, not value. Normals pack [-1,1] to [0,1] via x0.5+0.5. Imported normal maps must be packed [0-1] and in **tangent space** (Fusion cannot convert to tangent space). Use float32 on low-frequency height maps to avoid banding; adjust Height scale; turn on High Quality (Text+ antialiases in HiQ).

### Projection mapping (pp. 624-626)
| Method | How | Notes |
|---|---|---|
| Projector/Camera as light | Camera3D projection or Projector3D in Light / Ambient Light mode; lighting enabled | No alpha projection; overlapping projections add |
| Texture onto Catcher | Projection Mode Texture + Catcher material on receivers | Projects alpha; can drive specular, roughness; Software: Catcher combines overlaps (mean, median, blend...); OpenGL: one catcher per projector |
| UVMap3D (Map mode Camera) | UVMap3D downstream of geometry + camera | Writes UVs into vertices: needs tessellation. **Ref Time** locks UVs to a frame; breaks if vertices are created/destroyed/reordered (particles, animated Cube3D subdivision) |

- An internal clipping plane at about 0.01 units stops projectors getting closer to receivers (pp. 624-625).
- Textures slide if the object moves relative to the projector; group projector and object in a Merge3D to lock them (p. 626).
- Example: project a street plate onto five Shape3D planes via UVMap + Camera3D, then drop a CG car in to receive reflections and cast shadows (p. 626).

### Geometry, visibility, mattes, IDs (pp. 591-592, 627-636)
- Texture primitives by connecting an image or Templates > Shader preset to the **material input** of Shape3D/Cube3D/etc. (p. 591).
- Text3D is a scene of per-character objects: texture it with **ReplaceMaterial3D** downstream. After a Merge3D, ReplaceMaterial3D retextures every object in that Merge3D (p. 592).
- **Visibility** (Controls tab disclosure): **Visible** (off = not in viewer or render, casts no shadows); **Unseen by Cameras** (visible in viewers, not rendered, **still casts shadows**); **Cull Back Face / Cull Front Face** (both = invisible); **Ignore Transparent Pixels in Aux Channels** (default on: transparent pixels do not write Z/normals/UVs; turn off to fill aux channels for fully transparent regions, e.g., retexturing via UVs) (pp. 627-628).
- **Matte objects** (Matte disclosure): **Is Matte** (anything behind it in Z is not rendered; a "3D garbage matte"); **Opaque Alpha** (matte alpha = 1, else 0); **Infinite Z** (writes infinite Z, else normal Z). Matte objects still write Z and Object ID. Select in viewer only with 3D Options > Show Matte Objects (pp. 633-634).
- **Object ID / Material ID**: auto-assigned from 1; range 0-65534; 0 = "assign an unused ID at render", so do not set 0 manually; multiple objects may share an ID; Override 3D batch-sets IDs; written only when those renderer output channels are enabled; most effect-maskable nodes can mask by them in Common Controls (p. 635).

### Text3D (pp. 629-632)
- Each Text3D = self-contained scene; styling in the Text tab affects the whole node, so use separate Text3D nodes for differently styled words, merged in Merge3D.
- Toolbar trick: click Text icon, then click it again while that Text3D is selected: a Merge3D is created and connected; further clicks add more Text3Ds to it.
- Text tab: **Styled Text** field, Font, Color, Size, Tracking; **Extrusion** disclosure: Extrusion Style, Extrusion Depth, Bevel parameters (text is flat by default).
- All new Text3Ds sit at 0,0,0; use each node's Transform tab.
- **Layout** tab: line, frame, circle, custom spline path. "Sub" Transform tab: transforms by characters, words, lines simultaneously. **Shading** tab: standard material controls.

### Importing and exporting geometry
| Path | Result |
|---|---|
| **Fusion > Import > FBX Scene** (Resolve; File > Import in Fusion Studio) | Individual nodes per camera, light, mesh; **preserves animation** (p. 716) |
| FBX Mesh 3D node | All geometry merged into one mesh, one pivot; **ignores animation**; imports first texture; formats FBX ascii, FBX 5.0 binary, DXF, 3DS, OBJ, DAE; **Size** slider rescales; Take Name blank = no animation; Wireframe renders only in OpenGL (pp. 628-629, 716-718) |
| **Fusion > Import > Alembic Scene** (preferred) | Breaks .abc into mesh, camera, transform nodes; transforms become Fusion splines/Transform3D saved in the comp, meshes always reloaded from the .abc (p. 682) |
| Alembic Mesh 3D node | Whole file as one mesh if Object Name blank |
| FBX Exporter 3D | On render writes geometry, cameras, lights, animation to .fbx/.dae (one file or baked per frame); **no textures or materials** (p. 629) |

Alembic dialog (p. 683): **Hierarchy** (recreate parenting with Transform3Ds; disable for animated files to avoid node explosion), Orphaned Transforms, **Cameras** (aperture, AoV, plane of focus, clip; no stereo), InverseTransform, **Points** (position only, orientation lost), **Meshes** (UVs, normals), **Resample Rate** (keep the exported fps). Not supported: lights, materials, curves, multiple UVs, velocities. Manual advice: **FBX for lights, cameras, materials; Alembic for meshes only**.
Units: FBX in mm imports at face value (100 mm = 100 units); scale with Size (p. 629).

### Fog3D, SoftClip, and fog alternatives (pp. 633, 719-721, 762-764)
| Tool | Where | Needs |
|---|---|---|
| Fog 3D (3D node) | After the Merge3D, before render | Nothing extra; supports transparency, OpenGL DOF and AA |
| Volume Fog (Position category, VLF) | 2D, post-render | World Position pass + matching camera |
| Fog (Deep Pixel category) | 2D, post-render | Z channel |

Fog3D controls: Enable, **Show Fog in View** (fog normally visible only through a camera), Color, **Radial** (radial vs perpendicular distance; radial keeps fog constant as objects move across frame but can fog the edges of a near image plane), Type Linear / Exp / Exp2, **Near/Far Fog Distance** (units from camera). Optional green DensityTexture multiplies fog color, projected from the camera.
SoftClip: fades objects/particles near the camera to stop "popping" on fly-throughs; needs a camera in its scene; place just before Renderer3D. Controls: Smooth Transition (nonlinear), Radial, Show In Display Views, **Transparent/Opaque Distance** (opacity 0 at Transparent, 1 at Opaque, along camera Z).

### Aux channels, render passes, World Position (pp. 635-636, 671)
| Channel | Content |
|---|---|
| Z | Eyespace depth, negative into scene; not anti-aliased (frontmost depth wins) |
| Coverage | % of pixel covered by frontmost object (AA Z-compositing) |
| BgColor | Color behind the frontmost layer (AA Z-compositing) |
| Object ID / Material ID | Integers per mesh / material |
| TexCoord | Normalized (u,v) in R,G |
| Normal | (nx,ny,nz) in [-1,1] |
| Vector / BackVector | Forward / backward optical flow (vx,vy) |
| World Position | (wx,wy,wz), always 32-bit float |
| Disparity | (dx,dy) L>R or R>L |

Consumers: Merge depth merge uses Z (+ Coverage/BgColor for AA edges); common controls limit by Object/Material ID; Fog and DepthBlur use Z; Texture uses TexCoord; Shader uses Normal; AmbientOcclusion, DepthBlur, Fog give pseudo-3D in 2D (pp. 598, 671). OpenEXR imports/exports aux via CopyAux mapping.
**World Position Pass**: position nodes Volume Fog, Volume Mask, Z to World Pos. Volume Fog and Z to World need a camera (Camera3D or scene containing one) matching the render camera; Volume Fog can instead use world-space Camera Position inputs; Volume Mask needs none. **"Dark Box"**: empty pixels get Position (0,0,0), so add a big bounding sphere/box so background has distant values, else fog fills the background wrongly (p. 636).

### Point clouds (pp. 637-639)
PointCloud3D imports tracker locator clouds (SynthEyes, PFTrack, scanners) as one fast object instead of thousands of Locator3Ds. **Import Point Cloud** button > choose scene > choose cloud. Viewer right-click > Point Cloud > **Find** (case-sensitive: "tracker15" is not "Tracker15"; found point highlights yellow), **Rename** (single point only), **Publish** (exposes that point's XYZ to drive other controls).

### Integrating 3D into 2D
- Renderer3D output is a normal 2D image; merge it over plates like any layer (p. 596).
- Split conflicting needs across renderers: soft-shadow pass in Software, DOF pass in OpenGL, composite in 2D (p. 598).
- Use Multilayer passes (Shadow multiply, others add) for per-pass grading (p. 740).
- Use aux channels (Z, IDs, Normal, World Position) for post fog, DOF, ID mattes; use Cryptomatte from the OpenGL renderer for soft object/material mattes (p. 746).
- Camera Tracker export gives a matched Camera3D + Merge3D + Renderer3D to drop CG into plates (Part 2).

---

