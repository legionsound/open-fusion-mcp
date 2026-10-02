---
name: fusion-motion-design
description: Core procedure and router for motion design in DaVinci Resolve Fusion (21.1) - titles, kinetic type, logos, explainers, SaaS/UI animation, lower thirds, transitions, glass panels, 2D/2.5D/true-3D scenes, reference reconstruction and reusable templates - built as editable native Fusion graphs through the Resolve API or pasted .setting text, then verified in rendered pixels. The Fusion counterpart of Higgsfield's After Effects skill set (clean-rig, animation-principles, ui-mastery, design-first, depth-space, liquid-glass, transition-kit, build-orchestration). Load this first for any Fusion motion-graphics task; it names the modules a request needs.
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
    authority: router
    status: active
    triggers:
    - fusion motion design
    - fusion title
    - motion graphics in resolve
    - kinetic type
    - lower third
    - logo reveal
    - fusion transition
    - fusion template
    - after effects to fusion
    notes: Router and doctrine. Tool knowledge in fusion-reference; live control in use-fusion and the DaVinci Resolve MCP.
---

# Fusion motion design: clean construction, faithful motion

Treat the brief (or the reference) as the target and editable semantic construction as the
method. Native Text+, shapes, masks, gradients, 3D and modifiers stay live and editable;
motion is sparse, intentional and shared through controls; every claim is checked in
rendered pixels. Reducing complexity must not turn a distinctive design into a generic one.

This router is deliberately incomplete. The construction rules, motion evidence tests,
rig conventions, unit conversions and delivery gates live in the modules. Work produced
without the module a request needs is invalid even when every call succeeds.

## Essential workflow

0. **Load what the request touches** from the two tables below, plus
   [`fusion-reference/references/fusion-realities.md`](../fusion-reference/references/fusion-realities.md)
   before the first mutating call. Current explicit instructions override saved defaults.
1. **Inspect and scope.** Confirm Resolve is up with whichever tool answers fastest
   (`fu_version_info` / `fu_context`, or `get_resolve_status`); read project, timeline, item and
   comp (`fu_comp_info`, `fu_tool_info`, or one `run_script`). Never test
   in a client project: use a scratch project or a named lab timeline, say which, and back up
   before structural changes (export the comp or duplicate the item's comp). Keep unrelated
   work untouched.
2. **Establish the baseline.** The default job is **original design from a brief, with no
   reference**: audience, one message, context, duration, aspect, fps, assets, editability
   ([architecture](references/architecture.md)), then write the design decisions down before
   building (palette, type scale, layout grid, motion language, beats;
   [design-first](references/design-first.md), [ui-mastery](references/ui-mastery.md)). For a new
   original piece, run the visual foundation first (module 17: concepts with realistic style frames
   rendered locally, the user picks, a beat-mapped storyboard, the user approves; no Resolve time needed);
   skip it only when the user says so. A supplied reference image or video: measure real timestamps, poses,
   stationary elements, holds and cuts (module 02). An existing comp: it is the baseline; see
   "Adding to an existing composition". Rebuilding an existing After Effects comp is the rare
   case: [ae-matching](references/ae-matching.md).
3. **Choose the simplest faithful representation** (module 01): Text+ for words,
   sShapes or Background+mask for graphics, real 3D (ImagePlane3D/Shape3D/Camera3D/Renderer3D)
   when depth is visible, generated media only for photographic content (module 05).
4. **Build.** A new piece from a brief: describe it once and build it in one call with
   `scene.build` ([authoring-scenes](references/authoring-scenes.md)); efficiency defaults (culling,
   adaptive motion blur, texture holds, draft mode) come built in, and edits go through `scene.update`.
   Other whole components: write `.setting` text and paste it in one call
   (`fu_do setting.paste` or a `builder.*` op; [design-first](references/design-first.md),
   realities §9). Surgical edits: `fu_do` ops in one `batch.run`, or API calls with
   `comp.SetActiveTool(None)` before every `AddTool`, checked `ConnectInput` returns and
   read-back wiring. Named semantic subgraphs; IDs from the live TSV, never guessed.
5. **Animate** with sparse intentional keys (BezierSpline handles mapped from cubic-bezier),
   modifiers (Follower, Perturb/Shake, Anim Curves, Resolve Parameter) and expressions tied
   to one controller. Motion only where the brief or reference asks for it
   ([animation principles](references/animation-principles.md), module 02).
6. **Validate and deliver** (module 09): render and look (`fu_render_frame` returns the frame
   inline; `render.contact_sheet` for the whole motion; `audit.motion` for timing and easing),
   inspect the hero pose and risky in-betweens, test one real content/control edit and restore
   it, verify timing against the timeline, save/export, and report what was and was not verified.
   `render.compare` is optional: use it when a reference was supplied or to catch regressions
   between versions, not as a required gate.

## Read the module that changes the current decision

| When the task involves | Read |
|---|---|
| Choosing Text+ vs sShapes vs masks vs 3D vs media; building logos, UI, products | [01 Construction](references/01-construction.md) |
| Reconstructing a reference, timing fidelity, extra motion, sparse keys and curves | [02 Reference and motion](references/02-reference-motion.md) |
| Fonts, Text+ layout, Follower kinetic type, character styling, diagrams | [03 Typography](references/03-typography.md) |
| Gradients, color flow, glows, light sweeps, native effects | [04 Gradients and effects](references/04-gradients-effects.md) |
| Generated stills/footage (Higgsfield), MediaIn packaging, replaceable sources | [05 Generated media](references/05-generated-media.md) |
| Controllers, UserControls, macros, published inputs, Edit-page templates | [06 Editable rigs](references/06-editable-rigs.md) |
| Gallery, coverflow, cyclic slider, curved 3D loop driven by one control | [07 Controlled sliders](references/07-controlled-sliders.md) |
| Mascots/agents, blink, gaze, head-turn parallax | [08 Characters](references/08-characters.md) |
| Render checks, contact sheets, edit tests, frame mapping, delivery | [09 Validation and delivery](references/09-validation-delivery.md) |
| API patterns, timeouts, modals, partial writes, ID lookup | [10 Fusion scripting](references/10-fusion-scripting.md) and [realities](../fusion-reference/references/fusion-realities.md) |
| Pop-up dialogs, stuck calls, Macro Editor/template UI, looking at the app | [UI layer (computer use)](references/ui-layer.md) |
| Production wrap around a character rig: measured motion, two-bone IK, reference playback with free manual controls, light/shadow/texture passes (add-on to rigging) | [11 Character production](references/11-character-production.md) |
| Figures made of type and glyphs, pose sheets, scenery built from characters (a narrow add-on; drawn artwork lives elsewhere) | [12 Symbol characters](references/12-symbol-characters.md) |
| Language versions of a project: translation, glossary, what must be localized | [13 Localization](references/13-localization.md) |
| Making translated text fit: font choice, missing glyphs, counters, optical alignment | [14 Localized typography](references/14-localization-typography.md) |
| OFX plug-ins or Fuses that are missing or unlicensed, tidying a project, archiving and handover | [15 Dependencies and collection](references/15-localization-collect.md) |
| Re-cutting language versions to follow a short reference video | [16 Recut from a video reference](references/16-localization-recut.md) |
| Any new original piece, or a text-only brief: concept directions with realistic style frames (rendered locally), the user's pick, a beat-mapped storyboard with captions, sound plan and photosensitivity check, approval, optional HyperFrames animatic, then the build | [17 Visual foundation](references/17-visual-foundation.md) |
| Picking up work from elsewhere: a spec, build notes, a .comp or .setting from another machine or pipeline | [18 Adopting a handoff](references/18-handoff-adoption.md) |
| Whiteboards and sticky-note canvases: notes, cursors, notes arriving in stages, a camera moving over the board | [Boards](references/boards/overview.md) |
| Drawn or illustrated characters from artwork to final animation (start here; the rigging pipeline builds the rig; 08, 11 and 12 are add-ons) | [Characters pipeline](references/characters/overview.md) |
| Magazine-style photo collage: paper and print texture, travel through depth, animated prompt UIs | [Collage](references/collage/overview.md) |
| Building or fixing a 2D character rig: splitting the artwork, face and body controls, deformers for soft parts (Fusion has no Puppet tool), turns, the rig test (start here for any rig) | [Rigging pipeline](references/rigging/overview.md) |

Grouped modules keep their folder in links (`references/boards/overview.md` and so on). Each
pack's `native-execution` file is scoped to that pack; it does not replace module 10 or the
realities file.

References over 40k chars are split so each part fits one `fu_get_skill` call: the linked file
(for example `depth-space.md`) is an index naming the sections in `depth-space-1.md`,
`depth-space-2.md` and so on. Open the part you need, or call `fu_get_skill` with
`section: "R8"` on the index (the connector searches the parts).

## What the user asked for decides which companion module to load

Check this on every request, including follow-ups. Load only the rows the request hits.

| The user wants | Load |
|---|---|
| something to move, or move differently: timing, easing, stagger, entrances, loops, springs, counters, typewriter, expression motion | [animation-principles](references/animation-principles.md) |
| a new screen, card, component or layout with no reference: spacing, type sizes, color roles, component specs | [ui-mastery](references/ui-mastery.md) |
| a frame rebuilt from a reference image, or a full piece that needs the measure-build-audit pipeline, an effect look matched ("make it glow like this"), or a multi-scene piece | [build-orchestration](references/build-orchestration.md) |
| a film of several beats or camera setups: one comp per film with each scene entering through a Merge trimmed to its frames (culling), one controller, quiet pastes, memory budget; render efficiency (Z-buffer, freezes, adaptive motion blur, draft checks) | [build-orchestration](references/build-orchestration.md) Module 5, then [realities §16-§17](../fusion-reference/references/fusion-realities.md) |
| a heavy branch slowing the check loop while you work below it: freeze vs pre-render to disk (Saver -> Loader), stale caches after upstream edits, what to do before Deliver | [build-loop-caching](references/build-loop-caching.md) with the connector's `cache.*` ops |
| a graph someone will open, or a messy one: node layout, spine and layer columns, labeled backdrops (Underlays), tidying a comp | [graph-style](references/graph-style.md) with the connector's `comp.layout` (the scene builder lays out its own graphs) |
| (rare) an EXISTING After Effects comp rebuilt or scored in Fusion: AE coordinate, rotation-order and camera mapping, AE-specific looks, reading render.compare | [ae-matching](references/ae-matching.md) (the general rules live in depth-space, 03, 04) |
| a new piece built from a brief in one call (layers, tokens, type styles, layout, enter/exit, stagger, camera), then edited by description | [authoring-scenes](references/authoring-scenes.md) with the connector's `scene.build` / `scene.update` |
| a whole frame or component written once and pasted; a template for reuse; Lottie/OGraf import | [design-first](references/design-first.md) |
| depth or space: parallax, push-in, camera move, atmosphere, defocus, floor/shadow, "it looks flat" | [depth-space](references/depth-space.md) |
| glass, frosted, glassmorphic or refractive panels, pills, buttons | [liquid-glass](references/liquid-glass.md) |
| a transition between shots, a seam effect, an Edit-page transition template | [transition-kit](references/transition-kit.md) |
| how a node, keyer, tracker, 3D/particle/USD tool or modifier works; an exact input ID, default, range or option | skill `fusion-reference` |
| a Figma frame turned into native Fusion nodes | skill `fusion-figma-transfer` |
| other compositing, keying, roto, tracking or color-managed VFX rather than motion graphics | skill `fusion-reference` first, then modules 01/09 here |

## Adding to an existing composition

An addition or correction is not a new build; accepted work constrains it.

- Load the module for what is being added; apply it to that element only.
- Do not re-measure or rebuild what is not being changed. Do not re-run whole-comp passes for
  a local change.
- Preserve existing keys and fitted curves, controllers and their values, tool names,
  macros, published controls and approved media. A module loaded for the addition does not
  authorize normalizing them.
- Paste new components with unique names. A colliding paste renames the pasted tools
  (`Ctrl_A` becomes `Ctrl_A_1`) and rewrites expressions inside the pasted set, but your
  script and any outside expression still point at the old names. Re-read names after pasting.
- Tidy only what you added: `comp.layout {tools: [...]}` or `{scene: "S5"}` places the new tools in the house
  style ([graph-style](references/graph-style.md)) without moving the user's own nodes.
- If the new instruction conflicts with earlier work, say so and change only what it
  requires. Validate the change and what depends on it, not the whole comp.

## The user's saved preferences

- Keep text, buttons, panels, captions, diagrams and simple graphics native and editable.
  Use authentic clean logo assets when available. Never cut an object out of a reference
  screenshot and ship it as the asset; never rasterize UI into an image plate.
- Photographic footage via Higgsfield **Seedance 2.5 at 1080p**; stills via **Nano Banana Pro
  at 2K**; an explicit **Soul 2.0 at 2K** request overrides. Verify model availability and
  returned dimensions; never silently substitute a model or a still for footage.
- Preserve requested resolution, aspect and frame rate through the whole graph and delivery.
- A controllable rig must work directly for manual edits: document units and ranges, keep
  demo timing separate, no hidden duplicate tools to repair.
- If the user reserves acceptance or asks to stay on one case, continue that case until they
  accept. Routine reversible work inside the agreed scope needs no extra approval.
- Prefer probing Fusion natively over translation layers (no HTML/Remotion compiler in the
  native path). OGraf/Lottie imports are assets with an editability boundary.

## Control surfaces: one toolbox

Pick whatever is fastest and most reliable for each step and mix freely inside one task. Rule of
thumb: fewest calls, least risk. None of these is the "real" path with the others as fallbacks.

- **use-fusion connector** (`fu_*`; entry skill `use-fusion`): fast validated ops with readback,
  `batch.run` (one undo event; `atomic: true` all or nothing), `.setting` paste with quiet output, builders
  (`builder.*`), one-call render and inspect (`fu_render_frame`, `render.contact_sheet`,
  `audit.motion`, optional `render.compare`), Deliver status/stop, memory (`system.memory`,
  `system.purge_cache`), and safety rails (serialized calls, render-modal dismissal, project
  allowlist, timeouts answered with a step receipt plus `batch.recover`, `batch.rollback` and `resume`).
- **Official Resolve MCP** (`DaVinci_Resolve` / `DaVinci_Resolve_Studio`): the full Resolve API
  through `run_script` (sandboxed Python with `resolve`/`project`) and `run_script_unsafe` (files):
  Edit, Color, Fairlight, Media Pool, Deliver, anything the catalog lacks, or one script that beats
  many ops. Also `get_whats_new`, `get_scripting_api fusion_api.pyi`, status. When the same
  `run_script` pattern keeps recurring, note it as a candidate connector op: that is how the
  connector grows, not a failure.
- **Computer use** ([UI layer](references/ui-layer.md)): see and touch what the API cannot: the node
  graph, Inspector, viewer, dialogs and UI-only controls. If a call hangs or returns nonsense
  (`UI_BLOCKED`), stop calling, screenshot Resolve and clear the dialog before anything else; stop
  on any dialog you do not recognise and tell the user.
- **Community MCP** (`davinci-resolve`, `davinci-resolve-advanced`): guarded `fusion_comp`
  helpers and offline `.comp` authoring.
- **Toolkit**: `scripts/fusion_kit.py` (exec inside `run_script_unsafe`): `make_current`,
  `add` (no auto-wiring), `connect` (fails loudly), `ease` (cubic-bezier keys, stray-key safe),
  `expr`, `paste_setting` (one-call build with error capture and rename map),
  `render_frames` (PNG via temporary Saver), `audit_motion`, `finalize_report`, `export_comp`,
  unit converters (`rect_mask`, `ellipse_mask`, `text_size`, `pt`, `rgb`). Local helpers:
  `scripts/contact_sheet.py`, `scripts/measure_ref.py`, `scripts/audit_frame.py`,
  `scripts/harvest_inputs.py`. Drop-in components: `components/` (catalog in its README).
- **Knowledge**: `fusion-reference` (realities, `.setting` format, manual) and these modules;
  live data in `fusion-reference/data/fusion-21.1-inputs.tsv` and `-registry.tsv`.
- Evidence gates, frame mapping and recovery: [API routing and QC](references/api-routing-and-qc.md).
  Earlier observed mechanics: [tested native recipes](references/tested-native-recipes.md);
  historical session evidence: [qualification evidence](references/qualification-evidence.md).

Safety rules hold on every surface: scratch project or named lab timeline for tests (the
connector's allowlist enforces it), never write Fusion or Resolve prefs, save and restart only
with the user's approval.

## Closeout receipt

Deliver the source (comp/.setting/template), assets and a preview, plus a short receipt:
what changed; which frames were rendered and inspected (state sampling); which control or
content edit was tested and restored; what was saved/exported and where; what remains
unverified (look, continuous playback, template round trip, user acceptance). Keep
project-specific IDs in the handoff, not in this skill.
