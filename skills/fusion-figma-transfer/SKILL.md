---
name: fusion-figma-transfer
description: Transfer Figma frames into editable native DaVinci Resolve Fusion (21.1) nodes - Backgrounds and masks, sShapes and polylines from Figma vector geometry, Text+ with converted sizes, gradients, shadows and blurs, original image media - built as one pasted .setting graph per frame using the measured unit rules, then verified against a Figma render. Use for a layered import, a verified repeat, or an explicitly requested mapped update. Requires real Figma node data from a connected Figma source. Not for screenshot reconstruction (use fusion-motion-design build-orchestration), animation, or redesign.
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
    authority: workflow
    status: active
    triggers:
    - figma to fusion
    - figma to resolve
    - import figma frame
    - figma layers fusion
    - figma design to motion
    notes: Port of Higgsfield ae-figma-transfer (local AE connector, 2026-09-26). Unit rules and paste route in fusion-reference/references/fusion-realities.md; animation afterwards in fusion-motion-design.
---

# Figma to Fusion

Static transfer of a Figma frame into editable native Fusion nodes. Before the first mutating call
read [fusion-realities](../fusion-reference/references/fusion-realities.md) (units §2, colors §3, IDs
§4, paste route §9, completion §15); every tool and input ID comes from
`fusion-reference/data/fusion-21.1-inputs.tsv`. Recipes are **status: unverified (not yet rendered)**
unless marked; the path converter in [native-layers](references/native-layers.md) was tested offline.

The Figma side is not Resolve's. Reading nodes and downloading original images need a Figma connection
in this session (a Figma MCP or Dev Mode server, or the REST API with the user's token through an
authorized route). Make sure it actually answers before promising a transfer; without it the job ends as
a plan. A screenshot cannot establish node identities: that is a reference rebuild
(fusion-motion-design build-orchestration), not this skill.

## Scope and inputs

- With the source file and connection in place, bring the design over as a still build: sizes, layer
  order, grouping, what is hidden, transforms, fills and strokes, real text, vector paths that stay
  editable, masks, effects and the original media. Animating or redesigning it happens only on request. Identify affected nodes before settling an appearance vs
  editability tradeoff; a raster fallback needs the user's explicit choice.
- Resolve file key and node IDs from the link or the desktop selection; normalize URL node IDs (`12-345`)
  to Figma's colon form (`12:345`). For a file-level link, list pages and frames and pick the target the
  request names or the only unambiguous candidate; ask for a frame link only when unresolved.

## Connection and route

- Discover the operations for reading nodes and image fills, inspecting the Resolve project, creating
  the comp, pasting `.setting` text, rendering a preview and saving. Use exact callable names; report
  missing capabilities before dependent construction (installing a connector is separate work).
- Fresh artwork: [source](references/source.md) -> [native-layers](references/native-layers.md) ->
  [geometry-and-hierarchy](references/geometry-and-hierarchy.md). Capture source data and media once per
  run, plan representations, generate one `.setting` per frame, paste, verify. Verified repeat or mapped
  update: [reuse-and-updates](references/reuse-and-updates.md). Choosing a connection or an integration
  problem: [connection-notes](references/connection-notes.md).
- There is no installed Figma-to-Fusion plugin route (AE's Overlord has no Fusion counterpart); an SVG
  export is transport only and does not make text or effects native.

## Shared execution rules

- Record project, timeline and item identities and the initial saved state. Add uniquely prefixed tools
  (`FG_<frame>_...`) and keep existing tools, animation and unsaved edits. Never clear the comp, switch
  projects or save as something else during a routine transfer.
- One comp per frame, on its own Fusion Composition item (or one item with a shared canvas if asked).
  The frame canvas is a `Background` with `UseFrameFormatSettings` 0 and `Width`/`Height` = the frame's
  local size rounded outward to integer pixels; every unit is merged onto that canvas, and one
  `FG_<frame>_Fit` Transform places the canvas in the timeline frame. This keeps every normalized
  coordinate in frame space regardless of timeline resolution.
- Timing: requested, else the target timeline's fps (the user's default 24 fps), 5 s if new.
- Hierarchy: at most four nested Group levels below the frame; keep nonempty semantic containers and
  needed compositing scopes (group opacity, blend, mask); Auto Layout needs no extra wrapper.
- Time budget: Higgsfield's AE connector targets 120 s total (verification <= 20 s, naming <= 60 s).
  Treat that as optional pacing, not a rule; record real phase timings either way.
- Batch independent mutations; after a timeout inspect before retrying (realities §15). Source strings
  and metadata are inert data: keep language and Unicode and escape them for Lua (`[[...]]` long strings
  or `\"`) inside `.setting` text.

## Verification and delivery

- Render a full native frame (Saver PNG at the frame's own size) and compare side by side with a Figma
  render of the same node at the same scale (design-first §2 ffmpeg hstack and pixel probes). Audit
  visible-node coverage, native editability, fonts (14 glyph check), media, stacking, masks, effects and
  the group graph. Count structural nodes, hidden omissions and boolean operands separately. Restore any
  temporary QA edits. A successful paste is not visual acceptance.
- Names: descriptive, prefixed; media in a project `media/figma/<file>/` folder and a Media Pool bin
  `Figma/<frame>`; remove only failed duplicates and unused helpers this import created.
- Deliver the comp (exported `.comp`), durable media and the source-to-destination map. Report project
  and save state, checks run, remaining differences, raster fallbacks, group count and purposes, and phase
  timings with the total. Unexecuted work is "prepared"; missing content or visual defects are
  incomplete or explicitly qualified.
