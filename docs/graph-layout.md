# Graph layout

Node positions never change a render, but a comp that someone opens should read like a senior compositor's
graph. The house style is described in `fusion-motion-design` `references/graph-style.md`.

- **One spine, left to right**: the Merge Background chain (in a film, the ladder of scene Merges).
- **Each layer is a column above its Merge**; side inputs to the left, masks to the right; masks of spine tools
  hang below the spine.
- **Branches that composite again get their own band**, and each film scene its own labeled backdrop.
- **Fans are stepped** so far inputs pass under near blocks. Controls and shared assets sit top left.
- **Grid**: one column is 110 flow px, one row 33; positions sit on Fusion's snap lattice.

## Operations

- `scene.build` and `scene.update` lay out their own graphs. If the comp also holds hand-made tools, only the
  scene moves, and a user's tools never move unasked. Value, key and expression edits move nothing.
- `comp.layout` tidies any comp: the whole comp, one scene or a tool list. `dryRun` returns the plan and metrics
  (overlaps, crossings, wires over tools, straight spines, off-lattice positions); `preview` draws it.
  Backdrops it made are refreshed; a user's own backdrops are left alone.
- `scene.plan {graph: true}` draws the planned graph offline.

## Measured

- Live: 97 tools laid out in about 0.3 s, 560 tools in 1.27 s (two Lua calls whatever the size, one undo event).
- Offline: a 48-scene film of 3,115 tools plans in 0.11 s with 0 overlaps; 1,400 fuzzed graphs of up to 400
  tools had 0 overlaps and 0 off-lattice positions.
- The example scenes had 19 to 250 overlapping tiles each with the compiler's old placement, and 0 after.
