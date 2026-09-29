<!-- nodes-3d-lights-materials-textures.md part 1 of 2; index: nodes-3d-lights-materials-textures.md -->
# 3D Light, Material, and Texture Nodes (Fusion)
Scope: manual pages 796-876 (Chapters 30-32 of Fusion Page Effects Reference: 3D Light Nodes, 3D Material Nodes, 3D Texture Nodes). Use when: building or editing a Fusion 3D scene's lighting rig, assigning/authoring shaders on 3D geometry, or wiring texture/environment-map nodes into materials — via the Resolve scripting API or by writing `.comp`/`.setting` Lua tables.

## Mental model
1. **Lights only affect what shares their Merge 3D.** Lights are not viewable directly — connect a light into a Merge 3D and view the Merge 3D (or downstream) node. Selecting/viewing a light node alone shows nothing. Route different lights into different Merge 3D nodes to scope which objects they illuminate (p. 797, 799, 804, 808).
2. **Five light types, one shared Transform/Settings framework.** Ambient (no position/direction), Directional (direction only, like sunlight), DomeLight (image-based, HDRI/SDR sphere), Point (position, radiates all directions, optional decay), Spot (position + cone + shadows). Only Directional, Point, and Spot support shadows; Ambient and DomeLight do not expose shadow controls in this slice.
3. **Shadows need Hardware (OpenGL) Renderer for Directional/Point lights; Spot Light can shadow with either Hardware or Software renderer.** This is set on the Renderer3D node's Rendering Type, not on the light (p. 800, 806, 810).
4. **Materials are a distinct node type from images**, output by illumination-model nodes (Blinn, Cook Torrance, Phong, Ward, OpenPBR) or texture/utility nodes (Reflect, Falloff, Channel Boolean, Material Merge 3D, Catcher, Stereo Mix). Any material input also accepts a plain 2D image — it is silently treated as a diffuse texture map on a basic material.
5. **Every material texture input multiplies the connected map by the equivalent numeric parameter in the node.** This is the universal pattern: connect a texture to scale/modulate that channel, or leave it disconnected and just use the slider.
6. **Opacity vs. Transmittance vs. Attenuation are three separate, stackable transparency mechanisms.** Opacity = surface transparency in the render. Transmittance = how the material affects shadows/light passing through it (independent of Opacity — a fully opaque surface can still transmit 100% of the light hitting it, making it emissive-like). Attenuation = per-channel (RGB) color filtering of transmitted light/shadow, used for "stained glass" effects.
7. **Two-Sided Lighting is about normals, not culling.** Fusion does not cull backfaces by default (you always see the front face duplicated through to the back), so "two-sided" only matters for *lighting* — it adds a second, oppositely-facing set of normals so the back surface can be lit/shaded independently.
8. **Bump Map vs Height Map vs Normal Map are distinct Fusion terms** (p. 853): a Height Map is a grayscale height-per-pixel image; a Bump Map (Fusion sense) stores normals in RGB and *modifies* existing normals (typically tangent space); a Normals Map stores normals in RGB and *replaces* existing normals (tangent or object space). The Bump Map [3Bu] node's "Source Image Type" toggle switches between treating input as a Height Map vs. a (Create Bump Map–generated) Bump Map.
9. **Environment mapping (CubeMap, Sphere Map, DomeLight) assumes an infinitely distant environment** — objects cannot self-reflect or inter-reflect other objects using the same map; each object needing accurate inter-reflection needs its own rendered cube map (p. 840).
10. **Material ID is universal**: nearly every material/texture node ends with a Material ID slider that writes into the MatID auxiliary channel (if enabled in Renderer3D).
11. **Texture coordinate space is UVW**, not pixel space: U/V are the 2D texture plane, W is the third coordinate for volumetric/3D texturing (e.g., Fast Noise Texture's 3D mode, Gradient 3D). Prefer the UV Map node (XYZtoUVW mode) over Texture Transform for positioning per-vertex — it's faster and has onscreen controls.
12. **Catcher requires a Projector 3D or Camera 3D set to Texture projection mode.** Without an active texture-mode projection targeting it, a Catcher-fed material renders the object transparent/invisible — this is a common trap.
13. **The Common Controls chapters at the end of each of the three chapters describe controls repeated on nearly every node in that chapter** — Transform tab (Lights) and Settings/Comment/Scripting tabs (all three chapters) — documented once below, not repeated per node.

## Common Controls (documented once; referenced by name from each node below)

### Common Transform Tab (3D Lights and most 3D tools) (p. 812-814)
- **X, Y, Z Offset** — position the element in 3D space.
- **Rotation Order** — buttons choose axis order (e.g., XYZ = rotate X, then Y, then Z first-to-last).
- **X, Y, Z Rotation** — rotate around the pivot. If **Use Target** is checked, rotation is relative to the target position; otherwise relative to the global axis.
- **X, Y, Z Pivot** — offsets the rotation/scale pivot from the object's own center (default 0,0,0).
- **X, Y, Z Scale** — if **Lock X/Y/Z** is checked, one uniform Scale slider is shown (default state for most 3D tools); unchecked exposes independent X/Y/Z sliders. Locked scale cannot be broken even by dragging a single axis of the onscreen Transformation Widget.
- **Use Target** — enables an XYZ target the object always rotates to face; its own rotation becomes relative to the target.
- **Import Transform** — file browser to import transform-only data from `.lws` (LightWave Scene), `.ase` (Max Scene), `.ma` (Maya Ascii Scene), `.xsi` (dotXSI). For actual 3D geometry/lights/cameras, use **File > FBX Import** instead — Import Transform only brings in transform data.
- **Onscreen Transformation Controls / Viewer Transform buttons** — three viewer-toolbar buttons toggle onscreen widget mode; keyboard shortcuts **Q** (translate), **W** (rotate), **E** (scale). Drag an individual axis to affect just that axis, or the widget center to affect all three.

### Common Settings Tab (present on nearly every 3D node) (p. 814, 849, 875)
- **Hide Incoming Connections** — hides connection lines from incoming nodes for a cleaner node tree; per-input fields appear so you can drag a node into the field instead of showing the wire. Line reappears whenever the node is selected in the tree.
- **Comment Tab** — single animatable text field for node notes; adds a red dot + tooltip bubble on the node.
- **Scripting Tab** — present on every tool; holds scripts that run at render time (see the scripting docs).

### Standard Shadow Controls (first appears on Directional Light, p. 800-802; identical on Point Light p. 805-807 and Spot Light p. 810-811)
- **Enable Shadows** — checkbox, defaults **on**, required for the light to cast shadows.
- **Shadow Color** — standard color control, default black (0,0,0).
- **Density** — shadow opacity; 1.0 = fully opaque shadow, lower = more transparent.
- **Shadow Map Size** — bitmap resolution for the shadow map; larger = more detail, more memory/perf cost.
- **Shadow Map Proxy** — shadow-map size used in Proxy/Auto-Proxy render modes; e.g. 0.5 = half the Shadow Map Size resolution.
- **Multiplicative Bias / Additive Bias** — depth-offset controls to fix Z-fighting self-shadowing artifacts (shadow rendering on the same surface that casts it). Adjust Multiplicative Bias first, then fine-tune with Additive Bias. Too little bias = self-shadowing; too much = shadow visibly detaches from the surface.
- **Force All Materials Non-Transmissive** — forces a Z-only shadow map instead of the default RGBAZ shadow map. Faster, ~1/5 the memory, but disables "stained-glass" colored/transmissive shadows.
- **Shadow Map Sampling** — sets sampling quality for the shadow map.
- **Softness** — mode selector:
  - **Constant** — fixed-width filter; **Constant Softness** slider sets overall blur size (larger = slower render).
  - **Variable** — filter size grows with distance between shadow caster and receiver; exposes **Softness Falloff** (how fast the filter grows with distance), **Min Softness** (sharpest/closest limit), **Max Softness** (softest/farthest limit).
  - (Implicit hard-edge mode, no filtering, is fastest — only one shadow-map pixel sampled per lookup.)
- Gotcha: shadows are **hard-edged by default** in Fusion's underlying method — softness is purely a post-filter over the shadow map, so bigger constant-softness = proportionally slower renders.

### Standard Illumination-Material Controls (first appears on Blinn, p. 818-820; reused near-identically by Cook Torrance, Phong, Ward, OpenPBR)
**Diffuse block:**
- **Diffuse Color** — base color under ambient/indirect light; multiplied by a connected diffuse texture's color if present.
- **Alpha** — sets the material's Alpha; multiplies texture Alpha if a diffuse map is connected.
- **Opacity** — reduces diffuse+specular color and Alpha together, making the surface transparent (rendered transparency).

**Specular block** (evaluated differently per illumination model):
- **Specular Color** — color of the highlight; white for plastics/glass, tinted to the base color for metals.
- **Specular Intensity** — highlight strength; multiplied by texture Alpha if a map is connected.
- Model-specific falloff control: **Specular Exponent** (Blinn, Phong — higher = sharper/glossier falloff) or **Roughness** (Cook Torrance — higher = wider/more brushed/metallic falloff) or **Spread U / Spread V** (Ward — anisotropic, per-UV-axis falloff).

**Transmittance block** (shadow-transmission, independent of Opacity):
- **Attenuation** — RGB color of light passed through the object for transmissive shadows; (1,1,1) = fully transmissive/clear-colored shadow; e.g. (1,0,0) = only red passes → "stained glass" shadow.
- **Alpha Detail** — 0 = ignore Alpha, whole object casts shadow; 1 = Alpha determines which parts cast shadow.
- **Color Detail** — 0→1 blends in more of the diffuse color/texture into the cast shadow; ignores the object's own Alpha/Opacity when transmitting color.
- **Saturation** — saturation of the color transmitted into the shadow; 0.0 = monochrome shadows.

**Shared toggles:**
- **Receives Lighting / Receives Shadows** — checkboxes; if off, object is always fully lit and/or unshadowed.
- **Two-Sided Lighting** — adds a second, oppositely-facing set of normals to the backside (see Mental Model #7). Off by default (faster render). Gotcha: on a transparent two-sided surface lit from behind, the front view looks unlit — a known confusing interaction (p. 819-820, 835, 839, 848).
- **Material ID** — numeric identifier written to the MatID auxiliary channel if enabled in Renderer3D.

Node entries below only call out **deltas** from this shared block, plus each node's unique inputs/controls.

---

## 3D Light Nodes

### Ambient Light (3AL)
Directionless light that globally illuminates the scene; no meaningful position/rotation (onscreen widget exists only to move it out of the way of geometry). (p. 797-798)
- Inputs: `SceneInput` (orange, optional) — a 3D scene; if connected, this node's Transform applies to the whole scene.
- Key controls: **Enabled** (checkbox; same as the node's red on/off switch) - **Color** (standard color control) - **Intensity** (slider; e.g. 0.2 = 20% light — a pure-white surface lit only by 0.2 ambient renders at (0.2, 0.2, 0.2) gray).
- Modes/options: none beyond Common Transform/Settings tabs.
- Gotchas: No shadow controls (ambient light cannot cast shadows). Loading the light node itself into the viewer shows nothing — view via a Merge 3D instead.

### Directional Light (3DL)
Light with a clear direction but no source/distance — like sunlight. Onscreen control's position is meaningless; only its **rotation** sets the apparent light direction. (p. 799-802)
- Inputs: `SceneInput` (orange, optional 3D scene/geometry).
- Key controls: **Enabled**, **Color**, **Intensity** (0.2 = 20% light) — plus the full Standard Shadow Controls block (Enable Shadows default on, Shadow Color default black, Density, Shadow Map Size, Shadow Map Proxy, Multiplicative/Additive Bias, Force All Materials Non-Transmissive, Shadow Map Sampling, Softness Constant/Variable).
- Gotchas: **Requires Hardware Renderer** as the Renderer3D Rendering Type for shadows to appear in the 3D viewer (p. 800).

### DomeLight (3Do)
Image-based light (SDR or HDR) that surrounds the entire scene in a sphere, similar to environment lighting. Has an onscreen control. (p. 802-803)
- Inputs: `SceneInput` (orange, optional 3D scene) - `DomeTexture` (white) — connects an SDR or HDR image.
- Key controls: **Color**, **Intensity** (0.2 = 20% light). Position/direction/scale of the light are set in the Transform tab (not Controls tab).
- Gotchas: No shadow section documented in this slice for DomeLight (unlike Directional/Point/Spot).

### Point Light (3PL)
Point source radiating in all directions (e.g. a light bulb); only position/distance of its onscreen widget matter (rotation has no meaning since it's omnidirectional). Can fall off with distance, unlike Ambient/Directional. (p. 804-807)
- Inputs: `SceneInput` (orange, optional).
- Key controls: **Enabled**, **Color**, **Intensity** (0.2 = 20%) - **Decay Type**: defaults to **No Decay** (equal intensity everywhere); set to **Linear** or **Quadratic** to fall off with distance — plus the full Standard Shadow Controls block.
- Gotchas: **Requires Hardware Renderer** for shadows to show in the 3D viewer (p. 806).

### Spot Light (3SL)
Light from a specific point with a defined cone and edge falloff — like theatrical stage lighting. **This is explicitly called out as "the only type of light capable of casting shadows"** in the node's own intro (p. 808), though the Directional and Point Light shadow sections elsewhere in this same chapter contradict that framing — treat Spot as the most shadow-capable/flexible light (works with either renderer) and Directional/Point as also shadow-capable but Hardware-Renderer-only.
- Inputs: `SceneInput` (orange, optional).
- Key controls: **Enabled**, **Color**, **Intensity** (0.2 = 20%) - **Decay Type**: defaults to **No Falloff**; set **Linear** or **Quadratic** to fall off with distance - **Cone Angle**: width of the full-intensity cone, max 90° - **Penumbra Angle**: area beyond the cone where intensity falls to 0; 0 = hard edge, larger = softer edge - **Dropoff**: controls how quickly the penumbra falls from full intensity to 0 — plus the full Standard Shadow Controls block.
- Gotchas: Spot Light shadows work with **either Hardware or Software Renderer** (unlike Directional/Point, which need Hardware) (p. 810).

---

## 3D Material Nodes

### Blinn (3Bl)
Basic illumination material; general-purpose smooth/shiny look. Highlight computed as dot(N, H) (surface normal · half-angle vector between light and viewer) — note this may not match other 3D apps' Blinn model exactly (p. 816-820).
- Inputs: `DiffuseTexture` (orange) - `Specular Color Material` (green) - `Specular Intensity Material` (magenta; 2D image uses Alpha only, color discarded) - `Specular Exponent Material` (teal; 2D image uses Alpha only) - `Bump Map Material` (white; **3D material only** — route through a Bump Map node first).
- Key controls: Standard Illumination-Material Controls block in full, using **Specular Exponent** as the falloff control (higher = sharper falloff = smoother/glossier).
- Modes/options: none beyond the shared block.
- Gotchas: With 5 same-purpose-colored/many inputs, precise drag-connect is hard — hold **Option (macOS) / Alt (Windows)** while dragging a node's output onto the tile (keep held on mouse-up) to get a dropdown of all inputs; or drag with the **right mouse button**.

### Channel Boolean (3Bol)
Not the 2D Channel Booleans — this one remaps/modifies **3D material** channels via math operations (e.g., route a material's red channel into another model's Alpha-driven scalar like Blinn's Specular Exponent), including geometry-specific data (UV/texture-space coords, normals). (p. 820-823)
- Inputs: `BackgroundMaterial` (orange) - `ForegroundMaterial` (green); both accept a 2D image or a 3D material.
- Key controls: One **Operand A** / **Operand B** menu pair per output RGBA channel, each combined via an **Operation** menu.
  - Operand choices: Red/Green/Blue/Alpha **FG** or **BG** (reads that channel from foreground/background material) - Black/White/Mid Gray (sets channel to 0 / 0.5 / 1) - Hue/Lightness/Saturation **FG/BG** (HLS-converted) - Luminance **FG/BG** - X/Y/Z Position FG (pixel's 3D eye-space position) - U/V/W Texture FG (foreground's texture-space coords) - U/V/W EnvCoords FG (environment texture-space coords — use upstream of nodes like Reflect 3D that modify env coords) - X/Y/Z Normal (eye-space normal vector axis).
  - Operation choices: `A` - `B` - `1-A` - `1-B` - `A+B` - `A-B` - `A*B` - `A/B` - `min(A,B)` - `max(A,B)` - `avg(A,B)`.
  - **Material ID** slider.
- Gotchas: Output is always a material even though inputs can be plain images.

### Cook Torrance (3CT)
Basic illumination material tuned for **metal / shiny, highly reflective surfaces**; diffuse calc is like Blinn's, but specular uses an optimized Fresnel/Beckmann equation. (p. 823-827)
- Inputs: `Diffuse Color Material` (orange) - `Specular Color Material` (green) - `Specular Intensity Material` (magenta; Alpha-only from 2D) - `Specular Roughness Material` (white; texture Alpha × Roughness control) - `Specular Refractive Index Material` (white; RGB used directly) - `Bump Map Material` (white; 3D material only, via Bump Map node).
- Key controls: Standard Illumination-Material Controls, with **Roughness** as the specular falloff (higher = wider falloff, more brushed/metallic look), plus:
  - **Do Fresnel** — checkbox; adds Fresnel calculations for more realistic metal (accounts for the material's refractiveness).
  - **Refractive Index** — appears only when Do Fresnel is on; affects highlight calculation only (does **not** perform actual light refraction through transparent surfaces); multiplied by input Alpha if a texture is connected.
- Gotchas: Same multi-input drag-connect tip (Option/Alt-drag or right-mouse-drag) as Blinn.
- **Decision guidance: use Cook Torrance for metal.** It's the manual's stated purpose ("primarily used for shading metal or other shiny and highly reflective surfaces"), and Do Fresnel + a high Refractive Index gives realistic metallic highlight falloff (Refractive Index applies to the highlight calc only, not true refraction).

### Material Merge 3D (3MM)
Combines two materials (illumination models with texture nodes, e.g. Blinn + Bump Map/Reflection) into one shader network, with its own Material ID reassignment. (p. 828-829)
- Inputs: `Background Material` (orange) - `Foreground Material` (green; a 2D image here is treated as a diffuse texture map in the basic shading model).
- Key controls: **Blend** — single slider, behaves like the 2D Dissolve (DX) node's mix, but **both inputs are required** (unlike Dissolve). Output is always a material even if inputs are images. - **Material ID** slider.

### OpenPBR (3OP)
Consolidated physically-based-rendering material node combining multiple shading layers (base color/diffuse, metallic, roughness, bump, etc.) into one node for photoreal, real-world-surface-like results. (p. 829-836)
- Inputs: up to **29 possible inputs**, exposed by dragging a connection over the node (a menu lists all available slots); only **Base Color** (orange) is present by default.
  - **Occlusion input** (Ambient Occlusion) is only available/meaningful **when using a DomeLight or AmbientLight** in the scene.
  - Normals/Bump textures should be routed through a **Bump Map** node before connecting to OpenPBR's Bump Map input.
- Key controls, by layer (each "amount" slider multiplies its texture's Alpha if connected):
  - **Base**: Base (alpha/amount) - Base Color - Diffuse Roughness - Ambient Occlusion (strength of Occlusion texture) - Metalness (from texture or overall if unconnected).
  - **Specular**: Specular (amount) - Specular Color - Specular Roughness - Specular IOR (index of refraction for how light bends passing through) - Specular Anisotropy (strength; causes directionally rough/glossy look) - Rotation (of the anisotropy pattern).
  - **Transmission**: Transmission (amount) - Transmission Color - Extra Roughness (diffusion of the transmission layer) - Depth (distance white light travels inside before taking on the transmission color) - Scatter Color (ignored if Depth = 0).
  - **Coat**: Coat (amount) - Coat Color - Coat Roughness - Coat IOR - Affected Roughness (how much the Coat texture modulates diffusion) - Affect Color (how much the Coat texture darkens) - Coat Anisotropy (strength) - Coat Rotation.
  - **Sheen**: Sheen (amount) - Sheen Color (topmost scattering layer; produces grazing-angle highlight — think fabric) - Sheen Roughness (low = high-sheen fabric look, high = dusty look).
  - **Subsurface**: Subsurface (amount) - Subsurface Color (for dense-scattering materials like plastic, marble, skin) - Radius X/Y/Z (average travel distance of light before absorption/scatter — controls perceived density) - Scale (multiplier on Radius).
  - **Thin Film**: Thickness - IOR.
  - **Emission**: Emission (amount) - Emission Color.
  - **Opacity** — reduces all channels per-channel; reducing all three RGB channels to 0 makes the material transparent.
  - **Thin Walled** — checkbox; material behaves with no interior/underside, identical from either side.
  - **Receives Lighting/Shadows**, **Two-Sided Lighting**, **Material ID** — same semantics as the shared block.
- **Decision guidance: use OpenPBR for photoreal PBR-workflow assets** (imported textured models with base color/metalness/roughness map sets) and whenever you need coat, sheen, subsurface, or thin-film effects that the classic Blinn/Phong/Cook-Torrance/Ward models don't expose. For glass, its **Transmission** block (with Depth/Scatter Color) is the most physically-based option in this slice, though the manual gives fewer explicit glass-specific tips for OpenPBR than for Reflect + Attenuation on the classic models.

### Phong (3Ph)
Basic illumination material producing a highlight similar to Blinn's, but conventionally used for **shiny/polished plastic** surfaces. (p. 836-839)
- Inputs: `Diffuse Material` (orange) - `Specular Color Material` (green) - `Specular Intensity Material` (magenta; Alpha-only) - `Specular Exponent Material` (teal; Alpha-only) - `Bump Map Material` (white; 3D material only).
- Key controls: Standard Illumination-Material Controls block, unchanged (Specular Exponent as falloff, identical Transmittance/Attenuation/Alpha Detail/Color Detail/Saturation/Two-Sided/Material ID set to Blinn).
- **Decision guidance: use Phong for glossy plastic-like UI plates/props** — it's the manual's stated go-to for "shiny/polished plastic," which is the closest documented match for glossy UI-panel looks. Blinn is the more neutral/general default if you don't need the plastic-specific look.

### Reflect (3RR)
Adds environment-map **reflections and refractions** to a material; controls face-on vs. glancing reflection strength, falloff, per-channel refraction index, and tint. (p. 840-843)
- Inputs: `Background Material` (orange; 2D image → treated as diffuse texture on a basic material) - `Reflection Color Material` (white; RGB used, Alpha ignored) - `Reflection Intensity Material` (white; texture Alpha × intensity) - `Refraction Tint Material` (white; RGB used) - `Bump Map Texture` (white; 3D material only).
- Key controls:
  - **Reflection Strength Variability**: **Constant** (exposes **Constant Strength** slider — reflection intensity is the same regardless of view angle) or **By Angle** (exposes **Glancing Strength** — intensity where geometry faces away from camera; **Face On Strength** — intensity where geometry faces the camera directly; **Falloff** — sharpness of transition between the two, akin to a gamma curve over the gradient).
  - **Separate RGB Refraction Indices** — checkbox; when on, hides the single Refraction Index slider and exposes independent R/G/B refraction sliders (for spectral/chromatic-dispersion effects, e.g. thick imperfect glass).
  - **Refraction Index** — how strongly the environment map deforms when viewed through the surface (angle-of-incidence based); this is an approximation, not a physical simulation.
  - **Refraction Tint** — multiplies the refraction texture by a tint color (e.g., simulating tinted-glass coloring like beer-bottle glass).
- Modes/options: Refraction only has visible effect if the incoming **Background Material's opacity is < 1**.
- Gotchas: Environment mapping assumes an infinitely distant environment — no self-reflection or inter-object reflection without per-object cube maps (p. 840). Typically fed by a **Sphere Map** node into Reflection Color Material.
- **Decision guidance: use Reflect for glass-like looks.** Feed it a Sphere Map (or CubeMap) into Reflection Color, drop Background Material opacity below 1, enable Separate RGB Refraction Indices for realistic dispersion, and use Refraction Tint for colored glass. Reflect can be the sole shader on an object or feed the diffuse input of a Ward/Blinn/Phong/Cook Torrance node for a reflective-plus-lit combined look (p. 841).

### Stereo Mix (3SMM)
Swaps left/right material inputs, typically to output to the left/right eye of a 3D stereo render. (p. 843-844)
- Inputs: `LeftMaterial` (orange) - `RightMaterial` (green); either can be a 2D image (converted to a diffuse texture map on a basic material) or a 3D material. Output is always a material.
- Key controls: **Swap** — swaps the two inputs - **Material ID**.

### Ward (3Wd)
Basic illumination material specialized for **brushed-metal / anisotropic highlights** — the highlight elongates along the U or V mapping direction. (p. 844-848)
- Inputs: `Diffuse Material` (orange) - `Specular Color Material` (green) - `Specular Intensity Material` (magenta; Alpha-only) - `Spread U Material` (white; texture Alpha × Spread U control) - `Spread V Material` (white; texture Alpha × Spread V control) - `Bump Map Material` (white; 3D material only).
- Key controls: Standard Illumination-Material Controls block, with **Spread U** / **Spread V** as the (anisotropic) falloff controls — smaller value = sharper falloff = smoother/glossier in that UV direction.
- Gotchas: Manual explicitly demonstrates Ward used to build a "shiny glass surface" as well as brushed metal — it is not glass-exclusive or metal-exclusive; the anisotropic Spread U/V split is its distinguishing feature versus Blinn/Phong/Cook-Torrance's single isotropic falloff.
- **Decision guidance: use Ward when the highlight itself needs to be directional** — brushed metal (e.g., aluminum panels, machined surfaces) where the streak direction follows the UV grain. For isotropic metal, prefer Cook Torrance's Fresnel model instead.

**Material selection summary (this slice's guidance):**
| Look | Preferred node | Why |
|---|---|---|
| Glossy plastic / glossy UI plate | **Phong** | Manual states Phong is "more commonly used for shiny/polished plastic surfaces" |
| Generic smooth/shiny surface (no specific material target) | **Blinn** | Manual's baseline general-purpose illumination model |
| Metal (isotropic, e.g. chrome/gold) | **Cook Torrance** (+ Do Fresnel, Refractive Index) | Manual: "primarily used for shading metal or other shiny and highly reflective surfaces" |
| Metal with directional/brushed grain | **Ward** (Spread U ≠ Spread V) | Manual: "ideal for simulating brushed metal surfaces... anisotropic highlight" |
| Glass / transparent + reflective | **Reflect** (Background opacity < 1, Separate RGB Refraction Indices, Refraction Tint) feeding or fed by Blinn/Ward, plus Attenuation on the base material for colored "stained glass" shadows | Manual's dedicated reflection/refraction node; Ward example also builds glass |
| Full PBR asset (imported textures: basecolor/metal/rough maps) | **OpenPBR** | Consolidates PBR layers (metalness, roughness, coat, sheen, subsurface, transmission) in one node |

---

