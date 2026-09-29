<!-- build-orchestration.md part 1 of 6; index: build-orchestration.md -->
# Fusion Build Orchestration: the mandatory pipeline (follow IN ORDER)

What it is: the glue every Fusion craft module assumes. A reference-match or whole-frame build in the Resolve 21.1 Fusion page runs MEASURE -> PASSPORT -> BUILD -> GENERATE -> MOTION -> AUDIT -> FINALIZE, plus five modules: Draw-vs-Generate (with a native texture cookbook), Visual Matcher (Visual Passport + Effect Atlas), UI Rebuilder, Scene Director, Multi-scene films (one comp per beat). Load it before building any frame a reference image or a mood brief describes as a whole. Load `fusion-realities.md` first (units, auto-connect trap, paste route) and keep `api-routing-and-qc.md` open (execution contract, frame mapping, evidence gates).

Status: every recipe, script and `.setting` snippet here is **unverified (not yet rendered)** unless it says otherwise. Facts marked **[live]** were observed on Resolve Studio 21.1.0.14 on 2026-09-26. IDs were checked against `fusion-21.1-inputs.tsv` and the 21.1 registry; anything not found there says "unverified".

Conventions used throughout:

- Comp W x H is the timeline/comp resolution (the user's lab: 3840x2160, 24 fps). Timing tables give 24 / 25 / 30 fps. Frames are comp frames.
- Positions (`Center`, `Pivot`, `Start`, `End`) are normalized 0-1, origin bottom-left, **Y up**: `x = px/W`, `y = 1 - py/H`.
- RectangleMask `Width = w/W`, `Height = h/H`; EllipseMask `Width = w/W`, `Height = h/W` (both against width); `CornerRadius = r / (min(w,h)/2)`, 1.0 = pill. Text+ `Size ~= 1.70 x font_px / W` (Open Sans; cap px ~= 0.42 x Size x W). **[live]**
- Colors are float 0-1 per channel in split inputs (`TopLeftRed`, `Red1`, `Red`). Hex -> `int(hh,16)/255`. Values above 1 are legal (32-bit float).
- Blur/Glow sizes (`XBlurSize`, `XGlowSize`, slider 0..100) are **not** proven pixel radii. Every AE pixel radius below is given as a starting value scaled to your width; calibrate by render.
- SimpleExpressions: `time` is the frame number, trig is radians, `noise()` does not exist. **[live]**

> **Gate rule.** Each phase has an objective exit condition. Do not advance until it is met. The audit (Phase E) is a numeric gate, not a vibe: "looks close" is not a pass.
>
> **Gates are mandatory, ceremony is not.** A small build (one card, a badge, a title) may measure and build in one pass and paste one `.setting`, as long as every gate is still checked: measured colors, native editable nodes, eased motion, a passing audit, finalize. Skip a phase's work only when its gate is trivially met; never skip the check.

Before Phase A, write the execution contract (from `api-routing-and-qc.md`): host version/edition, project, timeline, item, comp name/index, fps, resolution, created tool names, recovery files. Work only in a scratch project/timeline the user opened for this; never mutate a client project.

---

## Phase A: MEASURE -> write the Fidelity Passport (before any build)

Vision misreads pixels (coordinates off 4-8 px, radii guessed, gradient stops wrong, fonts misidentified). Measure with a tool, write the numbers down, then build only from those numbers.

1. **Measure the reference with `measure_ref.py`** (local PIL, §S1). There is no server-side measuring tool in the Fusion stack; the reference is a local file, so reachability is never the blocker. Batch all ops in one call. Mandatory minimum:
   - `size` FIRST (ref pixel space; `SCALE = comp_W / ref_W`; if the aspect differs, choose Fit or Cover once and record the offset).
   - `swatch` or `pixel` for EVERY fill, stroke and text color (returns hex and rgb 0-1; never name a color by eye).
   - `radius` for EVERY rounded surface.
   - `gradient` with `n:5` for EVERY gradient (real stops plus axis).
   - `capheight` for title / body / caption tiers.
   - `crop` with `zoom:6` for any element under 40 px, then Read the saved PNG. Never read a tiny element off the full image.
   - `scanline` across any repeating geometry (rings, bars, grids) to get exact stripe count, centers and widths.
   If the reference exists only as a chat image with no file, save it or ask for the file. If that is impossible, take the passport from vision, SAY SO in the passport ("vision-derived"), rescale every coordinate by SCALE, and compensate in Phase E with the numeric self-audit of your own render.
2. **Write the FIDELITY PASSPORT.** One row per element, in reference pixels AND converted Fusion values, so Phase B copies numbers verbatim:
   ```
   CANVAS:   ref 1440x900; comp 3840x2160 @24; SCALE 2.6667 (Fit, x-offset 0, y-offset 0)
   PALETTE:  bg_dark -> (0.071,0.071,0.071)  accent -> (0.000,0.471,0.831)  text_hi -> (1,1,1)
   E1  BG_Canvas     bbox [0,0,1440,900]    fill bg_dark                                        [DRAW]
   E7  CTA_Pill      bbox [1180,40,160,44]  fill accent  r 22px  -> Center {0.8750,0.9235}
                     W 0.1111 H 0.0543 CornerRadius 1.0                                         [DRAW]
   E8  CTA_Label     text "Get Started" Inter Medium 14px -> Size 0.0165 Center {0.8750,0.9235} [DRAW]
   E12 Hero_Product  bbox [820,210,480,420] glossy 3D render, wordless                          [GEN]
   ```
   (Worked math for E7: center px = (1180+80, 40+22) x 2.6667 = (3360, 165.3); Center = {3360/3840, 1 - 165.3/2160}; Width = 160x2.6667/3840; Height = 44x2.6667/2160; CornerRadius = 2x22/44. Colors are never scaled. Text size 14 x 2.6667 = 37.3 px -> 1.70 x 37.3/3840.)
   Mark each element **[DRAW]** (geometry, text, gradients, textures: build natively) or **[GEN]** (character, product/3D render, detailed illustration, map, photographic content: generate and composite). See Module 1.
3. **Exit gate:** every element has measured numbers (not guesses), its Fusion-unit conversion, and a DRAW/GEN mark. A vision-derived passport says so on its first line.

Supporting modules: Visual Matcher (style passport, Module 2) and UI Rebuilder (per-element measurement table, Module 3).

---

## Phase B: BUILD strictly from the passport

Copy passport values verbatim; do not re-measure or re-guess mid-build.

- **Default route: paste one `.setting` per semantic unit** (fusion-realities §9, **[live]**): write the Lua-table text to a file, make the item comp current on the Fusion page, `cc.Execute('comp:Paste(bmd.readfile([[/abs/unit.setting]]))')`, then poll `cc.FindTool("<first node>")` for up to ~3 s (Execute is deferred). This avoids the auto-connect trap and keeps names exactly as written.
- **Python route** for small edits: `comp.SetActiveTool(None)` before EVERY `AddTool(id, False, x, y, False, False)`, `SetAttrs({"TOOLS_Name": ...})`, check every `ConnectInput` return, read wiring back with `GetConnectedOutput()`. **[live]**
- **No HTML step.** There is no HTML-to-Fusion importer in this stack. A frame that is easier to author as HTML can go through the OGraf/Lottie route (see `html-ograf-lottie.md`) only when that route is qualified for the job; default is native nodes.
- Every word is a `TextPlus`; every flat surface is a `Background` with a mask or an sShape; every gradient is a `Background` gradient. Nothing is a baked PNG. Follow the clean-rig construction rules (simplest representation that preserves the design, meaningful primitives, one named unit per component).
- **Each semantic unit terminates in ONE output node** (its unit Merge) followed by ONE unit Transform (`<Unit>_Xf`) that the motion phase animates. That pair is the Fusion equivalent of an AE precomp: the unit moves, scales and fades as one while its text stays editable inside.
- **Composition order is the Merge chain.** BG first; each unit merges as Foreground over the running result in Z order. `Merge.Background` sets resolution: the first Background must be comp-sized (`UseFrameFormatSettings` 1 or explicit `Width`/`Height`). `MultiMerge` (`Background`, `Layer1.Foreground`, `Layer1.Center`, `Layer1.Size`...) is the layer-stack alternative when many flat units share one level.

**Name the graph on the way in (MANDATORY).** Fusion node names allow only letters, digits and underscore, no leading digit; anything else is stripped silently **[live]**, so AE's `#`/`>`/`//` symbols cannot be used. Fusion schema:

| AE schema | Fusion equivalent | Example |
|---|---|---|
| `# Main` root comp | the item comp itself; its top level holds only group Underlays and the final chain | comp "Promo_Main" |
| `## Sequence` | `SEQ<nn>_<Name>` GroupOperator or Underlay | `SEQ01_Intro` |
| `### Scene` | `SC<nn>_<Name>` group inside the sequence | `SC02_Hero` |
| `> Parent` link | name prefix = parent unit: `<Unit>_<Part>_<Role>` | `Card01_Price_Txt`, `Card01_BG_Fill`, `Card01_BG_Mask`, `Card01_Mrg`, `Card01_Xf` |
| `()` clarification | trailing word | `SC01_Hero_AboveFold` |
| `//` parked/disabled | `X_` prefix + PassThrough | `X_OldIntro` |
| `> GlobalAsset` | `GA_<Name>`; reuse with **Instance** tools (edits propagate) or `Fuse.Wireless` links instead of long pipes | `GA_Logo`, `GA_Watermark` |
| controller null | `CTRL_<Scope>` (`Custom` tool NumberIn1..4 or UserControls) | `CTRL_Main`, `CTRL_Reveal` |

Role suffixes: `_Fill` Background, `_Mask` mask, `_Shp` sShape chain, `_Txt` Text+, `_Mrg` unit Merge, `_Xf` unit Transform, `_Glow`, `_Shd` shadow, `_Grd` grade. Groups: `GRP_BG`, `GRP_ENV`, `GRP_CT_<Unit>`, `GRP_FX`, `GRP_LT`, `GRP_CAM`, `GRP_GR`.

- **Exit gate:** the node set matches the passport element list (same count, same structure, nothing invented or missing), every image node carries a schema name (no `Background1`, `Merge3`, `Text1`, `Rectangle2` leftovers; the finalize name check in §S5 lists offenders), wiring reads back as intended.

Call sequence for a complex scene (port of the AE §9 workflow; order is load-bearing):

```
1.  Resolve item + comp (GetFusionCompByIndex); record fps/res; make it current for paste
2.  paste BG unit            BG_Canvas Background (+ gradient) -> MAIN_Mrg01.Background
3.  paste ENV unit(s)        textures/grids merged over BG
4.  paste CONTENT units      one .setting per unit, bottom-up by Z; each ends in <Unit>_Mrg -> <Unit>_Xf
5.  wire units into the main Merge chain (Foreground inputs, Z order)
6.  paste FX / LIGHT / CAMERA / GRADE units on the merged stream
7.  MediaOut1.Input <- final GRADE node (only the first MediaOut feeds the timeline)
8.  keys: BezierSpline SetKeyFrames (numbers), PolyPath/XYPath (points); expressions
9.  Saver (audit only) -> comp.Render({"Start":f,"End":f,"Wait":True}) -> inspect PNG
If any step fails or reads back wrong: stop, inspect the named partial state, repair only confirmed work.
```

---

## Phase C: GENERATE only the [GEN] elements (then composite)

- **NO [CROP].** Never cut pieces out of the reference as assets. The reference is for measuring, not harvesting: low-res crops turn to mush next to native 4K nodes and ship as dead non-editable blocks. Recreate ([DRAW]) or generate ([GEN]). Saving credits never justifies a worse frame. Exception: the user hands over a high-res asset (a clean authentic logo, a product shot) and asks for it verbatim.
- **STYLE LOCK first.** Write ONE style descriptor for the whole task (render style, palette hexes, lighting, materials, background treatment) and prepend it verbatim to EVERY generation prompt. An off-style return is regenerated with the descriptor tightened, never composited as is.
- **The user's defaults (Higgsfield):** footage = **Seedance 2.5 at 1080p**; stills = **Nano Banana Pro at 2K**. An explicit instruction naming another model wins for that task. Verify the exact model and resolution in the connected Higgsfield catalog before submitting (`models_explore`, or the `higgsfield-generate` skill route). If Higgsfield or that setting is unavailable, do not silently swap model, resolution, or footage for a still: report it, resolve with the user, continue independent Fusion work.
- **Content vs chrome:** generate only the detailed wordless object; build the surrounding UI chrome and ALL text natively. Never generate a whole card, never generate text, never generate a gradient, glow, plate, pill, badge or button. Flat icon/logo/pictogram content is [DRAW] in Fusion (sShapes: `sRectangle`, `sEllipse`, `sNGon`, `sStar`, `sPolygon`, `sBoolean`, `sOutline`).
- **Prompt:** object only + "isolated on a plain flat background, no text, no letters, no numbers, no watermark, exact art style of the reference". Use the reference crop as a style reference. If the model returns no alpha, cut it out with the Higgsfield `remove_background` tool (verify availability) or key it natively (`DeltaKeyer`/`UltraKeyer` on a flat backdrop), never with a hand-painted matte.
- **Hard cap ~4-6 generated assets per frame**, fired as one parallel batch. If you "need" 15, you are generating chrome you should build.
- **Import** (details and fit expressions: port_cleanrig `05-generated-media.md`): stills via `Loader` (qualified 2026-09-17: `Clip` path, `ClipTimeEnd` 0, `HoldLastFrame` = last frame, `GlobalOut` = last frame; alphabetic filenames only); footage via Media Pool `MediaIn` or the timeline clip as `MediaIn1` (Loader has no fps conform). Verify downloaded dimensions/fps with `ffprobe`/`sips`.
- **Clip into its frame:** `MEDIA_x -> FIT_x Merge.Foreground` over a card-sized transparent `Background`, cover-fit by expression `max(Background.Width/Foreground.Width, Background.Height/Foreground.Height)` on Merge `Size`, rounded by a `RectangleMask` on the card output (`MultiplyByMask` 1, see Phase D render-order fix).
- **Exit gate:** each [GEN] object looks like the reference in the style lock; every word and every piece of chrome is a native editable node; no reference crops in the graph.

---

## Phase D: MOTION (house reveal + settle easing + units)

- **A reference outranks the house defaults.** When the reference shows motion, fit timing and curves to what it does: an element the reference keeps still stays still, a hard cut stays a cut, a measured bounce keeps its amplitude and curve. House defaults apply only where nothing observed dictates motion.
- **Entrance = the house reveal by default:** rise from 42 px below (at 1080 lines = **0.0389 of frame height**, so the same fraction at any resolution), scale 95 -> 100 %, fast fade, staggered **0.12-0.18 s**, never simultaneous.

| House value | 24 fps | 25 fps | 30 fps | Fusion input |
|---|---|---|---|---|
| Reveal duration (0.5-0.75 s) | 12-18 f | 13-19 f | 15-23 f | unit `_Xf` |
| Rise | Center.Y -0.0389 -> 0 (relative to rest) | same | same | `<Unit>_Xf.Center` |
| Scale | Size 0.95 -> 1.0 | same | same | `<Unit>_Xf.Size` |
| Fade (first ~40 % of the move) | Blend 0 -> 1 over 5-7 f | 5-7 f | 6-9 f | `<Unit>_Mrg.Blend` (the Merge that brings the unit in) |
| Stagger 0.12-0.18 s | 3-4 f | 3-4 f | 4-5 f | key offset per unit |

- **Easing = settle-weighted, never flat.** House curve: fast departure, long soft arrival = start key outgoing handle 22 % of the span, rest key incoming handle 75 % of the span, both flat = `cubic-bezier(0.22, 0, 0.25, 1)`. Python handles are relative **[live]**: `RH = {1: 0.22*D, 2: 0}` on the first key, `LH = {1: -0.75*D, 2: 0}` on the rest key. Signature for the audit: progress 0.394 / 0.789 / 0.957 at 25 / 50 / 75 % of the span. The flat symmetric 1/3 ease (0.156 / 0.5 / 0.844) reads mechanical; linear keys (Fusion's default for new keys) read robotic. A curve fitted to a reference is finished work: do not normalize it back. If the animation module defines a different house curve, it wins.
- **Points animate through paths, numbers through splines.** `Center` takes `PolyPath` (ease its `Displacement` 0..1 BezierSpline) or `XYPath` (ease X and Y splines identically) or an expression; never a BezierSpline directly. `Size`, `Angle`, `Blend` take BezierSpline or `LUTLookup` (Anim Curves).
- **Better than AE: one master curve, staggered by time.** Put the 0..1 reveal curve once on `CTRL_Reveal.NumberIn1` (a `Custom` tool; the controller pattern is qualified 2026-09-17) and drive every unit by expression with its own delay, so re-timing the whole reveal is one spline edit:
  ```
  Card01_Xf.Center  = Point(0.5, 0.5 - 0.0389*(1 - CTRL_Reveal:GetValue("NumberIn1", time - 0)))
  Card02_Xf.Center  = Point(0.5, 0.5 - 0.0389*(1 - CTRL_Reveal:GetValue("NumberIn1", time - 4)))
  Card01_Xf.Size    = 0.95 + 0.05*CTRL_Reveal:GetValue("NumberIn1", time - 0)
  Card01_Mrg.Blend  = math.min(1, 2.5*CTRL_Reveal:GetValue("NumberIn1", time - 0))
  ```
  (Center here is relative to the unit's rest pose because the unit Transform sits after a unit already placed at its passport Center; `GetValue(..., time - n)` on another tool's input is **[live]** for Text+ Size; on Custom `NumberIn1` it is unverified.)
- **Every labelled small plate is its own unit.** Badges, stat pills, info tags, pill buttons, CTAs (`Background` + `RectangleMask` + `TextPlus` + optional icon) end in their own `_Mrg` + `_Xf` pair inside their own Underlay/Group, even with only two parts. "Only 2 nodes, not worth it" is not a valid skip. The only things left without a unit wrapper are genuinely standalone single nodes (a lone BG, a lone heading).
- **Grouping threshold.** When one flow level exceeds ~20 image nodes, group by function (one GroupOperator or Underlay per card/panel/section). Groups cost nothing at render; they keep the graph navigable and let the audit address units by name. Viewer ROI and proxy are viewer-only in Fusion, so there is nothing to clear before a Saver render.
- **Render-order fix (contain an effect inside a shape).** Fusion effect masks are post-process: an Effect Mask on a Glow blends glowed and unglowed input, so the glow halo still extends to the mask edge but the original image remains outside. To CLIP a finished glow/blur/gradient inside a rounded card: build the card chain, then on its LAST node connect the rounded `RectangleMask` to `EffectMask` and set `MultiplyByMask` 1 (outside becomes black/transparent), or route the finished card through `MatteControl` with the mask on `Garbage.Matte` and `Garbage.MaskInverted` 1 (keep inside). Use this whenever a glow, blur or ramp must stay inside a rounded card or shaped frame. For a glow that must spread beyond a restricted source, use the white `GlowMask` pre-mask instead (Glow/SoftGlow).
- **Shape strategy: parametric vs Bezier.** Parametric (`RectangleMask`/`EllipseMask` `Width`/`Height`/`CornerRadius`, `sRectangle`, `sEllipse`, `sNGon`) animate smoothly and draw on with `WritePosition`/`WriteLength`. `PolylineMask`/`sPolygon` allow per-point editing but morph poorly. Default to parametric for anything that grows, expands or morphs corners.
- **Parametrize, do not re-bake.** Values the user will predictably tweak (accent color, duration scale, direction, reveal delay) live on one controller (`CTRL_Main` Custom tool `NumberIn1..4`, or UserControls on a macro) referenced by expressions. Cap at a handful. These become the published controls of an Edit-page template in Phase F.
- **Exit gate:** every entering unit is keyed or expression-driven, eased and staggered; nothing linear on spatial motion unless the reference is linear; flow levels over ~20 nodes are grouped by function; every labelled plate is its own unit with editable text inside; every effect that must stay inside a shape uses the clip recipe.

---

## Phase E: AUDIT (numeric gate) -> fix -> re-audit

Render real pixels; never judge from graph readback alone.

1. **Render audit frames.** Add one audit Saver on the final node (`Saver.Input` <- the node MediaOut sees), `Clip` = `/abs/audit/<Shot>_.png`, `OutputFormat` "PNGFormat" **[live]**, then `comp.Render({"Start": f, "End": f, "Wait": True})`. Output is `<Shot>_0000.png` style (4-digit comp frame). `Render` returning True is not proof: check the file exists, its dimensions, and look at it. Render at a frame after entrances settle. If comparing to a timeline position, map it with `C = C0 + (T - T0)` after verifying C0 (api-routing-and-qc).
2. **Pixel audit (only when a reference file was supplied):** `python3 audit_frame.py ref.png audit/Shot_0096.png` (§S2) scores reference vs render cell by cell in CIE-Lab (32x18 grid by default). Crop/letterbox the reference to the comp aspect with the same Fit/Cover as the passport first, or the grid misaligns.
   **No reference file (the default for original design from a brief)?** Run the numeric SELF-audit instead: `measure_ref.py` on your own render with swatch/pixel/capheight/gradient/scanline probes at the passport's key points, and compare each reading to the passport. This also catches silent no-ink failures (missing glyphs, emoji, a Background whose colour never landed).
3. **Gate:** `ok` == (`flaggedPct <= 5 %` AND `meanDE <= 8`), cell flag threshold dE > 10 (house choice; keep it fixed across passes). If `ok`, move on.
4. **If not:** fix the specific `worstCells`. The ref/render hex pair says what is wrong (wrong fill, missing element, misplaced node); the box says where (render pixels). Re-measure that region if you mis-measured. For a stripe-count mismatch, copy the reference stripe centers/widths/count from `scanline` numerically. Re-audit. Up to ~6 passes; if `meanDE` stops dropping across two passes, re-measure the region instead of nudging.
5. **Vision pass:** downscale (`sips -Z 960 in.png --out view.png`) and Read it for what the grid cannot score: layout sense, copy, alignment, spacing rhythm, text overlap.

Rendered-frame inspection (steps 1 and 5, `fu_render_frame`, contact sheets) is always required. `render.compare` is optional: use it to score against a supplied reference or to check a new version against the previous render; it never replaces looking at the frames.

**Motion-semantic regression (run even when the pixel audit passes).** A still cannot tell that motion moves wrong.

- Run `audit_motion` (§S4) over the settled range: it samples each unit's `Center`/`Size`/`Angle`/`Blend` every frame through `GetInput(id, frame)` and reports travel in px, start/end/peak frames, duration, and the curve signature at 25/50/75 %. A unit that should move but reports `anim False` or travel ~0 did not land; fix it. As a safety net for units still missing an entrance, apply the house reveal expression from Phase D to their `_Xf`/`_Mrg` (the Fusion "reveal floor"); never to BG.
- **Keyframe-graph diff:** compare each signature to the spec. Linear (0.25/0.5/0.75) or flat symmetric (0.156/0.5/0.844) on spatial motion is a finding unless the reference is linear; a reference-fitted curve reading differently from the house curve is a pass.
- **Critical-beat frames:** render 4 frames per animation: 0 % (rest before), the peak-speed frame (`peak` in the report), the settle start (first frame after the peak where per-frame change falls below half the peak), 100 %. Overshoot, clipping and mid-flight collisions only show here. Summarize a whole move with a contact sheet (§S3); state the sampling rate; a contact sheet can miss one-frame defects.
- **Stagger validation:** inter-unit start deltas. Flag < 30 ms (same frame at 24/25/30: reads simultaneous) and > 180 ms (> 4 f at 24, > 4 f at 25, > 5 f at 30: drags). The AE source also flags > 150 ms; treat 150-180 ms as a warning. House range 120-180 ms.
- **Timing gate:** penalize any single animation > 2 s (> 48 f at 24, 50 at 25, 60 at 30) and any micro-interaction < 100 ms (< 3 f at 24/25/30: reads as a jump). Re-time to the window.

**Structure validation:** every image node carries a schema name; flow levels over ~20 nodes are grouped; no orphan modifiers (`comp.GetToolList(False)` entries with no consumer); animated shapes are parametric; audit Savers are the only Savers.

Evidence gates stay separate (api-routing-and-qc): this phase proves Structural, Temporal and Rendered. Editable (change a published control, render, restore), Exported/saved and Persistence belong to Phase F; Creative acceptance is the user's review.

- **Exit gate:** pixel `ok` true (reference audit or self-audit) AND the vision pass is clean AND the motion checks pass (signatures match spec, beats look right, stagger in range, no out-of-window timing) AND structure validation passes.

---

## Phase F: FINALIZE (deterministic, once per build)

Run `finalize()` (§S5) ONCE per build, not once per request. A later correction to an accepted comp does not re-enter this phase unless the correction itself created new mechanical motion; never tidy a comp the user already accepted. It is deterministic Python, idempotent, and does five things:

1. **Name check.** Lists every image node still carrying a default name (`Background1`, `Merge3`, `Text1`, `Rectangle2`...). Rename via `SetAttrs({"TOOLS_Name": ...})` and re-check (expressions reference names, so rename before wiring expressions or update them). The AE "brand the comp hf_<ts>" step is vendor-specific and dropped.
2. **Repairs mechanical easing, and only that.** For each BezierSpline driving a spatial input (`Center` via PolyPath `Displacement` or XYPath `X`/`Y`, `Size`, `XSize`, `YSize`, `Angle`, `Blend`, Text+ `Start`/`End`, Follower `Opacity1`...), if EVERY segment samples as linear, it rewrites the keys with the house handles (relative, `SetKeyFrames(dict, True)`). A spline with any deliberately shaped, stepped or held segment is preserved untouched and reported. `policy="preserve"` touches no curve; `policy="force"` rewrites everything and destroys fitted curves (reserve for deliberately mechanical builds).
3. **Floors motion blur** on the Transform/Merge/Text+ hosts whose curves it just repaired: `MotionBlur` 1, `Quality` 8 for preview (raise to 12-16 for final), `ShutterAngle` 180. A host whose deliberate timing it preserved keeps its blur decision (a crisp stepped move stays crisp). 3D: Renderer3D motion blur must match the scene's; particles: pRender blur must match Renderer3D.
4. **Hygiene.** Reports orphan modifiers and default-named nodes; deletes or disables only the audit Savers this build created (MediaOut delivers; Savers are for checks).
5. **Save and deliver.** Save the Resolve project only when authorized (`projectManager.SaveProject()`). Export the comp: `item.ExportFusionComp("/abs/Promo_Main.comp", 1)` and confirm the file exists and contains the unit names. For an Edit-page template: wrap the final graph as a `MacroOperator`/`GroupOperator` with published controls (`InstanceInput`), save under `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Titles|Generators|Effects|Transitions/`, relaunch Resolve (templates appear only after relaunch), drop it on a scratch timeline, change one published control, render, restore (Editable gate), then reopen (Persistence gate). Timeline delivery is a Deliver-page render; verify the movie with `ffprobe` (frame count, rate, resolution, duration) and inspect decoded pixels.

**Rig space check** (port of `ae_rig_rebase`): if rendered content sits mostly off frame (alpha coverage inside the frame < 50 % on a settled frame), you almost certainly stacked a unit Transform on top of an already-offset Center (double offset) or keyed a unit in comp space under a moving `CAM_Rig`. Fix the offending `_Xf` so it animates relative to rest (Center 0.5,0.5 = no offset), then re-audit. Safe to check speculatively after finalize.

---

## The one-line contract

MEASURE (never eyeball) -> BUILD from the passport as native named units -> GENERATE only the [GEN] content on the user's Higgsfield defaults and composite -> MOTION (house reveal, settle ease, one unit Transform per unit) -> AUDIT rendered PNGs to a number, fix the worst cells, check motion signatures -> FINALIZE once (names, mechanical easing, motion blur, export). Skipping a phase is why a build "is not close to the reference".

### Build discipline (local Higgsfield connector revision, 2026-09-26)

1. Classify the job first: new build, reference match, or local correction (the router's
   "adding to an existing composition" rules). Preserve unrelated content.
2. Plan the scene before the first call: which subgraphs and groups, what every tool is called, which
   content sources stand alone, the visual tokens, the controllers and the beats of the motion. Keep
   fixed layout values apart from the controls that animate, and build the smallest rig that does the
   job.
3. Look up every tool and input in the TSV before writing a call. Do not assume a tool created in
   the same `comp.Execute`/paste can be addressed by its authored name: execution is deferred and
   collisions rename (`_1`), so read names back before wiring (realities §9).
4. **Representative component first.** Build one unit (one card, one button, one character
   head), render it at the intended state, fix it, and only then clone the pattern across the
   scene. Cloning an unverified unit multiplies the defect.
5. Dependency order: sources, component geometry, hierarchy (Transforms/Merge3D), controls,
   expressions, keys, effects. Small coherent batches; check each result; stop at the first
   failure and inspect the partial work before retrying (10).
6. Drive shared components through controllers. Test every control at zero, a fractional value,
   a typical value and an extreme; manual editing stays independent of optional demo playback.
7. Render representative frames at the real comp fps; check nested Groups, alpha, fonts, edge
   clipping and loop seams; save/export the deliverable with its dependencies and state what was
   actually verified.

For a reference recreation keep an evidence list: viewport/crop, object bounds, typography,
palette, motion start/stop frames and stationary elements, each observed item next to its frame,
every inferred detail labelled "inference". A screenshot is a reference, not a reason to trace
hundreds of fragments: match the largest geometry and rhythm before microdetails.

---

