---
name: fusion-reference
description: Expert knowledge base for Blackmagic Fusion inside DaVinci Resolve 21.1 (Fusion page) - the full Fusion 21.1 manual distilled into agent references plus live ground truth pulled from the running app (every tool's registry ID, input IDs, defaults, ranges and option lists). Use for any Fusion question or build - compositing, Merge math, masks, roto, keying, tracking, planar, camera tracking, 3D, lights and materials, particles, shapes, Text+, modifiers, expressions, macros and templates, color management, USD, Krokodove - and before writing any Fusion script or .setting text. Pair with fusion-motion-design for motion-graphics craft.
metadata:
  routing:
    domain: filmmaking-editing
    lane:
    - fusion
    output:
    - timeline
    - file
    tool_routes:
    - resolve
    authority: reference
    status: active
    triggers:
    - fusion node
    - fusion page
    - fusion comp
    - fusion expression
    - fusion keying
    - fusion tracking
    - fusion 3d
    - .setting
    - macro
    - text+
    notes: Manual-grade Fusion 21.1 knowledge and live IDs; craft/router lives in fusion-motion-design, live control in use-fusion.
---

# Fusion reference (Resolve 21.1)

Knowledge, not procedure. `fusion-motion-design` is the creative procedure and router;
`use-fusion` covers live control through the connector (and the official DaVinci Resolve MCP beside it);
Figma frames come in through `fusion-figma-transfer`. This skill answers "what does Fusion do,
exactly, and what is it called in code".

## Evidence order

1. **[live]** facts in [fusion-realities.md](references/fusion-realities.md): observed on
   Resolve Studio 21.1.0.14 on 2026-09-26 (paste route, auto-connect trap, expression units,
   Bezier handle math, measured mask/text units, PNG Saver).
2. **Live data**: [data/fusion-21.1-inputs.tsv](data/fusion-21.1-inputs.tsv) (379 tools and
   46 modifiers: input ID, UI name, type, control, default, slider|allowed range, options,
   page) and [data/fusion-21.1-registry.tsv](data/fusion-21.1-registry.tsv) (registry ID,
   name, category, class, tool/modifier). Third-party and Resolve FX OFX tools are excluded.
3. **Manual distillations** in `references/manual/` (Fusion 21.1 manual, 1,803 pages, with
   page cites). They use UI names; when a manual file and the TSV disagree on an ID, the TSV
   wins.
4. Anything marked "(inference)" or "unverified": test before relying on it.

Current installed docs outrank all of this: `get_whats_new`, `get_scripting_api
fusion_api.pyi`, and a live `GetInputList()` on the real tool.

## Read first for any build

[fusion-realities.md](references/fusion-realities.md) (an index: read the parts you need; part 3 = render efficiency): which comp
you are touching, coordinates and units, colors, ID rules, the auto-connect trap, keyframes,
expressions, modifiers, the one-call `.setting` paste route, rendering, the silent-failure list,
and production scale (multi-scene films, render cost, Resolve memory, Deliver).
Then [setting-format.md](references/setting-format.md) when writing `.setting`/`.comp` text.

References over 40k chars (setting-format, the manual files) are split into `<name>-1.md`,
`<name>-2.md`...; the linked file is an index naming each part's sections, and `fu_get_skill`
with `section: "<heading>"` on the index finds the part.

## Look things up instead of guessing

```bash
D=~/.agents/skills/fusion-reference/data
grep -iP '^[^\t]*\t[^\t]*glow' $D/fusion-21.1-registry.tsv     # find a tool by name
grep -P '^Glow\t' $D/fusion-21.1-inputs.tsv                    # its inputs, defaults, ranges, options
grep -P '^@' $D/fusion-21.1-inputs.tsv | grep -i follower       # header: ID, instance name, category, outputs
grep -P '\tmodifier$' $D/fusion-21.1-registry.tsv              # all modifiers
grep -n 'def AddModifier' -A4 $D/fusion_api-21.1.pyi           # API signature
```

## Where the knowledge is

| Task | Read |
|---|---|
| Fusion page vs Edit timeline, MediaIn/MediaOut, Loader/Saver, render ranges, frame numbering | [01 interface, timeline, I/O](references/manual/01-interface-timeline-io.md) |
| Node editor, instancing, groups, macros, Macro Editor, publishing, Edit-page templates (titles, transitions, effects, generators), viewers, Inspector, linking | [02 node editor, macros, templates](references/manual/02-node-editor-macros-templates-inspector.md) |
| Keyframes, Spline Editor, easing, loops, motion paths, modifiers overview, SimpleExpressions, custom controls | [03 animation](references/manual/03-animation-splines-modifiers-expressions.md) |
| Preferences, path maps (Scripts:, Templates:, Macros:, Fuses:), variables, auto-merge prefs | [04 preferences](references/manual/04-preferences-pathmaps.md) |
| Resolution, DoD/ROI, proxy, bit depth, color management, channels/aux, premultiply, Merge in full, masks and roto | [05 2D compositing core](references/manual/05-2d-compositing-core.md) |
| Paint, clone, Tracker, stabilize, match move, corner pin, Planar Tracker | [06 paint and tracking](references/manual/06-paint-tracking-planar.md) |
| 3D scene model, renderers, cameras, lights/shadows, projection, FBX/Alembic, Camera Tracker, particles, optical flow | [07 3D, camera track, particles](references/manual/07-3d-cameratrack-particles-flow.md) |
| Every 3D node (Camera3D, Merge3D, Renderer3D, Shape3D, Text3D, ImagePlane3D, Duplicate3D, Fog3D ...) | [nodes: 3D](references/manual/nodes-3d.md) |
| Lights, materials (Blinn, Phong, Cook Torrance, Ward, Reflect, OpenPBR), textures, Catcher, ReliefMap | [nodes: lights, materials, textures](references/manual/nodes-3d-lights-materials-textures.md) |
| Blur, Defocus, Glow, SoftGlow, Vector Motion Blur, Color Corrector, curves, OCIO, Merge/MultiMerge/Dissolve, deep image/pixel | [nodes: blur, color, composite](references/manual/nodes-blur-color-composite-deep.md) |
| Duplicate, Rays, Shadow, Trails, Film Grain, Erode/Dilate, Custom Filter, Groups/Underlay/Pipe Router, Fuses | [nodes: effect, film, filter, flow](references/manual/nodes-effect-film-filter-flow-fuses.md) |
| Text+ (every tab and shading element), Follower and text modifiers, Background, FastNoise, MultiText, OGraf, Loader/Saver/MediaIn/MediaOut, Krokodove catalog, Layer nodes, LUTs | [nodes: generators, Text+, I/O, Krokodove](references/manual/nodes-generators-textplus-io-krokodove-layer.md) |
| Masks, Delta/Ultra/Primatte/Chroma/Luma keyers, Clean Plate, Magic Mask, Matte Control, Custom Tool, Time Speed/Stretcher, Auto Domain, optical flow nodes, Paint node | [nodes: masks, keyers, misc](references/manual/nodes-masks-keyers-misc-opticalflow-paint.md) |
| Particles (pEmitter ... pRender), sShapes (sRectangle ... sRender), Position nodes, stereo | [nodes: particles, shapes](references/manual/nodes-particles-shapes-position-stereo.md) |
| Tracker/Planar/Camera/Surface Tracker nodes, Transform, DVE, Camera Shake, Crop, Resize, USD (u*) tools | [nodes: tracking, transform, USD](references/manual/nodes-tracking-transform-usd.md) |
| Displace, Grid Warp, Corner/Perspective Positioner, Lens Distort, Vortex, every modifier (Perturb, Shake, Calculation, Offset, Anim Curves, XY Path, Probe, Resolve Parameter ...), VR | [nodes: warp, modifiers, VR](references/manual/nodes-warp-modifiers-vr.md) |

## Twenty facts agents get wrong

1. Every 3D branch ends in a Renderer3D (default renderer: Software). Soft/colored shadows need
   Software; accumulation DOF, supersampling, wireframe and Cryptomatte need OpenGL.
2. Merge `Background` sets output resolution and bit depth; a Merge with no Background outputs
   nothing. Merge expects a premultiplied foreground.
3. Positions are normalized 0-1 with Y up. RectangleMask sizes are per-axis; EllipseMask sizes
   are both relative to width; Text+ `Size` is relative to width. See realities §2.
4. SimpleExpressions: radians, `time` in frames, no `noise()`. Clearing an expression zeroes
   the input.
5. On the Fusion-page comp, `AddTool` auto-connects to the active tool unless
   `comp.SetActiveTool(None)` is called first.
6. `Paste` of `.setting` text only works on the comp current on the Fusion page; Lua
   `comp.Execute` is deferred.
7. Python Bezier handles are relative `{dt, dv}`; `.setting` handles are absolute.
8. Only Lens Correction from the Edit page reaches Fusion; Edit-page transforms, retimes,
   Resolve FX and grades apply after Fusion.
9. A Fusion clip conforms to timeline resolution; a single-clip comp runs at source
   resolution. Only the topmost clip enters Fusion unless MediaIn uses Background.
10. Nothing is color managed by default; with Resolve Color Management on, do not add
    CineonLog/Gamut conversions.
11. Effect masks apply after the effect and do not work on Saver/Time/Resize/Scale/Crop.
    Connecting an empty mask blanks the image.
12. Transform concatenates; Corner/Perspective Positioner do not. Resize/Scale/Crop change
    resolution and should not be animated.
13. The Tracker only analyzes its Background input; stabilize = Match Move with Merge set to
    BG Only. Planar Tracker data does not survive save/reload.
14. Time Speed's Speed cannot be animated (use Time Stretcher); time and flow tools destroy
    vector channels.
15. Particles depend on the previous frame: pre-roll before judging a frame; pRender and
    Renderer3D motion blur settings must match.
16. Lights only affect their own Merge3D unless Pass Through Lights is on; view a light
    through a Merge3D.
17. Follower changes do nothing until keyframed, and spaces count as characters. Only Text+
    shading element 1 is on by default.
18. Primatte's orange input is the Foreground (reversed from other nodes). Keyers
    post-multiply by default.
19. Edit-page templates: titles omit MediaIn/MediaOut, transitions need two MediaIns and a
    MediaOut, and templates appear only after Resolve restarts. Use the Resolve Parameter
    modifier so a transition follows its duration.
20. In Resolve, Bins, Fusion Connect and Composition preferences do not exist, GPU/Memory
    prefs are Resolve's, and processing is always 32-bit float.

## New in Fusion 20.x-21 (from the installed changelog)

Krokodove motion-graphics tools (100+, IDs `KD_*`), new Macro Editor with inspector view
and publishing to Edit-page effects, Fairlight-audio-driven animation (`FairlightAnimator`
modifier), native OGraf HTML graphics (`OGrafLoader`) and Lottie, emoji/color fonts and
spell check in Text+/MultiText, MultiText improvements, USD SDK 25.11 with Hydra 2 Storm and
USD Texture Projector/Catcher, Cryptomatte in Renderer3D, native Relief Maps, multi-tool
inspector edits, user metadata variables in paths/expressions/scripts, Lens Distort
checkerboard calibration, Magic Mask v2, deep compositing cache, improved shape Duplicate,
multilayer workflows (Swizzler, Layer Muxer/Regex/Remover). Edit page: 4-point Bezier
keyframing with ease/loop/ping-pong/reverse/stretch for Fusion effects, titles and
generators. Always call `get_whats_new` for the current build.

## Maintenance

The data files came from a disposable Testbed project via the official Resolve MCP. To
refresh after a Resolve update, rerun the harvest (`fusion.GetToolList()`, per-tool
`AddTool` then `GetInputList()` attrs `INPS_ID`, `INPS_Name`, `INPS_DataType`,
`INPID_InputControl`, `INPN_Default`, `INPN_MinScale/MaxScale`, `INPN_MinAllowed/MaxAllowed`,
`INPIDT_*` option tables, `INPS_ICS_ControlPage`) in a scratch project only.
