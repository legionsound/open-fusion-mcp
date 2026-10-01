# Fusion realities: the facts that cause silent failures

Index. This reference is split into 3 parts so each fits one `fu_get_skill` call. Open the part that holds the section you need, or call `fu_get_skill` with `section: "<heading>"` on this file (the connector searches the parts). Parts keep the original headings and links.

| Part | Size | Sections |
|---|---|---|
| [fusion-realities-1.md](fusion-realities-1.md) | 27k | §1. Which comp you are touching; §2. Coordinates and units; §3. Colors and pixels; §4. IDs: registry, inputs, options; §5. Creating, naming, connecting; §6. Keyframes and Bezier splines [live]; §7. Expressions [live]; §8. Modifiers [live]; §9. One-call build: paste a `.setting` graph [live]; §10. Rendering and checking pixels [live] |
| [fusion-realities-2.md](fusion-realities-2.md) | 22k | §11. Silent-failure list; §12. Not available or needs another route; §13. Cheap, preview-friendly construction; §14. Verification pass findings [live]; §15. Transport, completion and retries; §16. Production scale: multi-scene films, render cost, memory [from rebuild log] |
| [fusion-realities-3.md](fusion-realities-3.md) | 8k | §17. Render efficiency [live, efficiency lab]: what costs time, culling with enabled regions, Z-buffer transparency, things that do nothing in Resolve, draft vs final, harness facts |
| this file, below | 3k | Newest findings [live]: tool names ignore case, a Fusion clip keeps its carrier's frame size, an orphan on port 49152 hangs every scripting client |

## Newest findings: names, clip size, the scripting port [live]

Observed on 2026-10-01 while building a 9:16 version of the explainer film (Resolve Studio 21.1, macOS).
Kept in this index until they are filed into a part.

1. **Tool names are case-insensitive** **[live, 2026-10-01]**. Fusion treats `S1_tl_mt` and `S1_tl_Mt` as one
   name: a paste renames one of them with a `_1` suffix (the collision rule in §9), and a scene rebuilt with
   `replace` left one more renamed copy each time. Keep tool names unique when case is ignored; the scene
   builder rejects ids that collide this way.
2. **A Fusion clip keeps its carrier's frame size** **[live, 2026-10-01]**. A comp on a carrier media clip (the
   black carrier of `timeline.add_fusion_clip`) takes the carrier's frame size, not the timeline's. After the
   timeline was switched from 1920x1080 to 1080x1920, its existing comp stayed 1920x1080 and the film ladder
   cropped the vertical scene. Changing the timeline format does not resize existing Fusion clips: make a new
   clip on the reformatted timeline (its carrier is made at the new size) and rebuild there.
3. **An orphan on scripting port 49152 makes scripting hang, not fail** **[live, 2026-10-01]**. After Resolve
   was quit and reopened, a Workflow Integration plugin helper (Electron) and the old `fuscript -s` from the
   exited session, both with parent PID 1, still held TCP 49152 through one inherited socket. The new Resolve
   registered on 49153, and every scripting client (the connector, the official Resolve MCP, plain
   `DaVinciResolveScript`) waited with no error. Find the holders with `lsof -nP -iTCP:49152 -sTCP:LISTEN` and
   their parents with `ps -o ppid= -p <pid>`. Quit the orphans (a plugin helper can ignore a normal quit: Force
   Quit it), then quit and reopen Resolve so it registers on 49152. `fusion-connector doctor` runs this check,
   and the connector's `TIMEOUT` replies report it.
4. **A healthy plugin helper also has parent PID 1** **[live, 2026-10-01]**. A Workflow Integration plugin that
   the running Resolve launched shows parent PID 1 too, and it holds 49152 through Resolve's own socket (the
   same DEVICE value in `lsof`). Parent PID 1 alone does not make a holder an orphan: an orphan neither
   descends from the running Resolve nor shares its socket.
