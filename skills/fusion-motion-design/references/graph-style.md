# House graph style: node layout, backdrops, tidy graphs

Load this when a comp will be opened by a person (every hand-off), or when a graph came out messy. The connector's
`scene.build` / `scene.update` apply it automatically and `comp.layout` applies it to any comp (use-fusion skill,
"Graph layout"). Live-checked in Resolve Studio 21.1, 2026-09-27.

A comp you hand over should read like a senior compositor's graph. Someone opening the node editor should find the
main pipe, then each layer, then the controls, without tracing wires. Node position never changes the render;
it only helps the reader.

- **One spine, left to right.** The compositing pipe is one straight horizontal row: the Merge Background chain,
  or in a film the FILM_ ladder. Left to right matches Resolve's default build direction and MediaIn -> MediaOut,
  and it fits the Fusion page's node panel, which is wide and short.
- **Each layer is a column above its Merge.** Its source chain (generator -> effects -> transform/hold) runs
  straight down into the Merge's Foreground. The column's own side inputs sit to its left and its masks to
  its right. Masks of a spine tool (a Merge EffectMask, a track matte) hang **below** the spine and flow up, so
  the layer column and its masks are on opposite sides.
- **Pipes inside a layer get their own band.** A branch that composites again (2+ merges: a group's sub-stack, a
  card textured with a precomp) is laid out as its own small horizontal band. So is a branch from another
  scene, which also gets its own backdrop. Each film scene sits in its own labeled backdrop above its FILM_
  merge, and the ladder runs along the bottom.
- **Fans are stepped.** When a tool has 3+ side inputs (a Merge3D gathering cards), each farther input sits 2 rows
  lower, so its wire passes under the nearer blocks instead of through them.
- **Controls and shared assets in the top-left corner** of their scene: the CTRL tool, notes, unwired tools,
  and any tool that feeds two or more layer groups. Modifiers (splines, paths, followers) have no node and are
  never placed.
- **Grid.** One column = 110 flow px, one row = 33 flow px.
  - Spine tools are at least 1.5 columns apart, and sibling blocks 0.5 columns apart (1.5 next to another scene's
    backdrop).
  - Chain tools are 3 rows apart. With node thumbnails on (the user's Fusion page), a tile is about 2.3 rows tall,
    because the thumbnail hangs under the name bar. 3 rows leaves a visible wire; 2 rows made tiles touch.
- **Backdrops (Underlays), named `<label>_<KIND>` and colour-coded by kind.** Fusion draws the colour as the box's
  border and title.
  - Kinds: scene `_SCENE` slate, film ladder `_LADDER` red-brown, controls `_CONTROLS` amber, shared assets
    `_SHARED` grey, text layer `_TEXT` violet, 2D/UI layer `_UI` teal, 3D rig `_3D` blue, disk cache `_CACHE`
    green, loose branch `_BRANCH` grey.
  - A layer box is labeled with its Merge's name (for example `S5_title_TEXT`). Every tool sits wholly inside
    its box, the box is centered on its tiles with equal side margins, and layer boxes nest inside their scene
    box.
  - Underlays are UI only. Measured live: the same frame rendered with and without 12 underlays was
    pixel-identical (MAE 0.0, SSIM 1.0), at 2.58 s vs 2.53 s mean over 3 fresh frames each (noise). They double
    as Go To Bookmarks, which is how you jump between scenes in a film comp.
- **No automatic PipeRouters.** The layout avoids crossings by construction, and a router would edit the wiring.
  The only long wires left come from a shared source to its other consumers, and `comp.layout` counts them.
  The user's node editor draws orthogonal (elbow) pipes, and the style reads cleanly with them. A stepped fan's
  wires meet only in the last few pixels at the Merge3D.
- **No MultiMerge for tidiness.** Folding a stack into a MultiMerge shrinks the graph but made a real animated scene
  render about 2x slower (realities §17 item 20). Keep Merge chains and let the backdrops carry the order.
- **No automatic Groups.** Collapsing a layer into a GroupOperator is not offered, for two reasons.
  `scene.update` re-pastes changed tools at the comp root, and a paste cannot land inside a group, so an update
  would pull tools out of it. Wires into a group go through its instance ports, which the surgical
  connect/rewire path does not create. Keep groups for hand-finished, locked comps; use underlays for the
  compact view.

Agents never place nodes by hand. `scene.build` places them, and `comp.layout` places them for anything else. Moving
nodes changes no wiring, values, names or expressions.

## Placing nodes yourself (only when no op fits)

Units (measured live, Resolve 21.1):
  - `FlowView:GetPos` / `SetPos` / `QueueSetPos` and `comp:AddTool(id, x, y)` take GRID units.
  - `SetPos(x, y)` puts the tool's cell TOP-LEFT at (x, y), so the .setting
    `ViewInfo = OperatorInfo { Pos }` (the tile center, in px) = ((x + 0.5) * 110, (y + 0.5) * 33).
  - Fusion snaps SetPos: x to half columns, y to whole rows.
  - For an Underlay, `SetPos` x is the box's LEFT edge. `UnderlayInfo { Pos, Size }` is px, with Pos =
    (horizontal center, TOP edge), and Size is kept exactly.
  - Paste does not keep an underlay's Pos (y moved), so place it with SetPos after the paste.
  - `tool.set_position` now documents grid units. Its old text said "~110 per node column", which was wrong.
- **Underlay drawing order**: the underlay created FIRST draws on top. Paste inner boxes before the box around
  them, or the scene box hides them.
- **Deleting**: script `Delete()` on an underlay removes only the box; in the live check, 3 boxes were refreshed and
  the tool count stayed the same. In the UI, deleting a normally selected underlay deletes everything inside it.
  Option-click its title to select the box alone.

## Measured (offline, thumbnail-size tiles as on the user's Fusion page)

| scene (tools) | overlapping tiles before -> after | wires over tools before -> after | crossings before -> after |
|---|---|---|---|
| showcase (41) | 60 -> 0 | 65 -> 0 | 0 -> 0 |
| kitchen_sink (77) | 193 -> 0 | 150 -> 1 | 5 -> 0 |
| push_three_worlds (42) | 41 -> 0 | 58 -> 1 | 4 -> 0 |
| bench_s2 (172) | 250 -> 0 | 443 -> 50 | 70 -> 30 (all from shared-texture wires) |
| title_low_tide (21) | 19 -> 0 | 20 -> 0 | 0 -> 0 |
| card_smart_folders (30) | 36 -> 0 | 38 -> 0 | 2 -> 0 |

"Before" is where the compiler used to place tools. Crossings are counted with straight wires.

- A film of 48 scenes (3,115 tools) plans in 0.11 s, with metrics in 0.3 s. It has 0 overlaps, a straight
  ladder, every tool inside its box, and every position on Fusion's snap lattice.
- 1,400 fuzzed random graphs, run after the final changes, had 0 overlaps, 0 box problems and 0 off-lattice
  positions. There were 1,000 plain graphs of up to 300 tools and 400 graphs of up to 400 tools that mixed scene
  prefixes, FILM_/FC_ tools, 3D, masks and groups.
