# 02 Reference analysis and faithful motion

Load when reconstructing a supplied reference, fixing extra or invented motion, preserving timing while rebuilding construction, or reducing dense keys to sparse fitted curves. Timing examples assume 24 fps (the user's timelines); convert with frames = seconds * fps.

## Establish reliable frame evidence

Tag each input with what it is: the original reference, a result the user approved, or a screenshot
of something wrong. A render of a failed Fusion rebuild documents a problem; it is never geometry to
copy. When stills disagree, the original video and whatever the user explicitly named decide.

Record the source frame index and presentation timestamp (PTS) next to every observation.
Decide motion on decoded original frames; a contact sheet made by seeking and resampling to a
round rate duplicates or omits exactly the frames that matter. Sparse sampling is for
navigation only. For variable-frame-rate media keep real PTS, never `index / avg_fps`.

```bash
ffprobe -v error -select_streams v -show_frames -show_entries frame=pts_time \
  -of csv=p=0 ref.mp4 > ref_frames.csv          # row k (0-based) = presentation-order frame k
ffmpeg -v error -i ref.mp4 -vf "select='eq(n\,120)+eq(n\,121)+eq(n\,132)'" \
  -fps_mode passthrough ref_%04d.png            # one PNG per selected frame, none duplicated
# pair each PNG with row n of ref_frames.csv (tested ffmpeg 9.0.1, B-frame H.264)
```

Do not select on `coded_picture_number`: it is decode order (differs from display order with
B-frames) and newer ffmpeg builds drop it. Extracted frames are analysis material, never source artwork (01). `scripts/contact_sheet.py`
and `scripts/measure_ref.py` read these files; keep their frame labels.

Cuts and time mapping in Fusion terms:

| Question | Fusion answer |
|---|---|
| Last visible frame N of an element | Half-open: the hidden state starts at N+1. Key Merge `Blend` 1 at N and 0 at N+1 with `StepIn`, or a Dissolve `Mix` step. [verified live 2026-09-26] Loader `GlobalOut` 20 (inclusive) handing off to a Merge `Blend` `StepIn` key at 21: frame 20 shows only the Loader, frame 21 only the incoming element; no hole, no double (`t02_hole_sheet.png`). |
| Loader/MediaIn range | `GlobalIn`/`GlobalOut` are **inclusive** (MediaIn defaults 0..287 on a 288-frame comp [TSV]). Mixing inclusive ranges with half-open keyed hides is the classic one-frame hole or double frame. [live 2026-09-26] A Loader shows nothing outside its range; a MediaIn of a 48-frame clip still reads `GlobalOut` 287 and holds its last frame to the comp end. |
| Source frame shown at comp frame f (MediaIn/Loader, no retime, no hold) | `ClipTimeStart + (f - GlobalIn)`; `Reverse`, `Loop`, `HoldFirstFrame`/`HoldLastFrame` change it. |
| Retimed branch | `TimeSpeed` (`Speed`, `Delay`) or `TimeStretcher` (`SourceTime` curve) sit between source and consumer; subtracting the shot start is valid only for an unretimed branch. Probe the real mapping by rendering a temporary Text+ counter upstream (`StyledText` expression `Text(string.format("%d", time))`) through the same retime tools. [verified live 2026-09-26: the counter, rendered to a PNG plate and read through MediaIn -> TimeStretcher, showed exactly the keyed `SourceTime` at every sampled frame] |
| Comp frame for timeline frame T | `C = C0 + (T - T0)` with C0 the verified visible comp frame at T0 ([API routing and QC](api-routing-and-qc.md)). |

Check the rendered boundary frames even when every property value reads back correctly.

## Read the editing rhythm, not only the object motion

Study the reference at scene boundaries and inside continuous camera passages, not only frame by
frame. Tell cuts, flashes (one to three white or colored frames) and transitions apart. Note the rhythm
between fast passages and the holds that explain them, where camera moves begin and end, what a change
of scale lets the viewer see, and how a repeated object links one idea to the next. Numbers measured
on one reference shape this piece only; they are not durations to reuse everywhere.

Study body text and emphasized phrases as two separate things: where they sit, how big, which style,
how much contrast, how they relate to the picture. Mark which sound accents coincide with something on
screen (timeline markers, or the `FairlightAnimator` modifier, fusion-realities §8). Settle on a single
treatment that serves this story, and list every approximation or stand-in asset before calling
anything an exact match.

## Preserve animation while changing construction

1. Inspect the actual target before editing: version (`resolve.GetVersionString()`), project, timeline, the intended item and its comp (`item.GetFusionCompCount()`, `GetFusionCompNameList()`, `GetFusionCompByIndex(i)`), comp attrs (`COMPN_GlobalStart/End`, `COMPN_RenderStart/End`), resolution from the output Merge Background/MediaOut, fps from the timeline, and media dependencies (Loader `Clip`, MediaIn `ClipName`). Export a backup (`item.ExportFusionComp(path, i)`, Resolve API; check the installed stub) and work in a named iteration (`item.AddFusionComp()` copy or a versioned comp name). Never switch, save or overwrite unrelated work as a shortcut.
2. Read the reference at real timestamps. For variable-frame-rate sources use `ffprobe -show_frames` pts, not frame index. Map time once: for equal rates and no retime, `C = C0 + (T - T0)` where C0 is the verified visible comp frame at timeline frame T0 (api-routing-and-qc.md). Inspect full frames and detail crops. Write down poses, contact and hinge points, outline, proportions, colors, text, the frames where things enter and leave, bounces, pauses, changes of state and what lines up with the audio. Keep hard cuts and stepped changes separate from continuous motion, with their exact frames.
3. Write a compact component/motion map before building:

| Component | Anchor/pivot | Parent (chain) | Moves? evidence (frames) | Motion type | Keys at |
|---|---|---|---|---|---|
| CHEST_LID | hinge (x,y) | CHEST_RIG Transform | yes f12-f30 open, overshoot f24 | rotation | 12, 22, 24, 27, 30 |
| CHEST_BODY | base center | CHEST_RIG | no | none | none |

   Shared motion belongs on one parent: a 2D `Transform` the part chains pass through, a `Merge3D`/`Transform3D` in 3D, or a controller read by expressions (06). Each independently moving part gets a stable name and a correct `Pivot`. Package semantic objects as named subgraphs or Groups; when grouping, preserve connections, mask inputs, effect order, clipping (`ClippingMode`), resolution (Merge Background) and occlusion order, then re-render.
4. When replacing an object, keep useful keys, expressions, timing, Merge order, masks and relationships. Rebind by moving the existing spline to the new tool (`.setting` edit: re-point `SourceOp` of the new input to the old `BezierSpline`), or measure again when the old construction cannot supply a rig. Tracker/Probe output is analysis: read it, set sparse keys, then disconnect. Key only at anticipation, impact, extrema, overshoot, settle and state changes; fit handles to observed motion; compare between keys. No key per frame, no every-Nth decimation, no blanket Smooth. Bake dense keys only on explicit request or a proven downstream need.
5. Validate a static pose and an extreme/deformed pose before propagating. Check which design features simplification lost and restore them. Preserve bounce direction, amplitude, easing, overlap, squash, part interaction and event order. Do not replace measured motion with a generic bounce expression or Anim Curves "Bounce" preset because it looks lively.

## Keys and curves in Fusion terms (verified 2026-09-26 unless marked)

| AE | Fusion |
|---|---|
| Keyframe + Graph Editor ease | `BezierSpline` modifier keys with RH/LH handles |
| cubic-bezier(x1,y1,x2,y2) over D frames, change V | Python: RH = {x1*D, y1*V} on the first key, LH = {(x2-1)*D, (y2-1)*V} on the second (relative). `.setting`: absolute `RH = { t0 + x1*D, v0 + y1*V }` |
| Easy Ease | handles at 1/3 duration with zero value slope: RH {D/3, 0}, LH {-D/3, 0} |
| Linear | keys without handles (Fusion fills D/3, V/3) or `Flags = { Linear = true }` |
| Hold key | `Flags = { StepIn = true }` in `.setting` (corpus syntax; Step In/Out wording contradicts in the manual: verify on the curve) or a two-key cut: value A at frame k, value B at k+1 |
| Separate dimensions | `XYPath` modifier on a Point (inputs `X`, `Y` each take a BezierSpline) |
| Spatial path + speed graph | `PolyPath` modifier: polyline shape + `Displacement` spline 0..1 (last key 1.0), `Heading` output for auto-orient |
| loopOut cycle / pingpong / offset | `.setting` key `Flags = { Loop = true }` / `{ Loop = true, Pingpong = true }` (corpus); Relative Loop from the Spline Editor |

Fusion holds the first key's value before it and the last after it (constant extrapolation). A delayed move needs its start value keyed at the start frame, or it will sit at the first pose from frame 0.

## Motion restraint and shared movement

Annotate the map with moving AND stationary parts. For each proposed motion record the reference interval and visible evidence: direction, amplitude, phase, acceleration, hold. What an object usually does is not evidence. Leave ambiguous secondary motion still until closer inspection resolves it.

Separate causes onto distinct named controls and animate only visible causes:

| Cause | Fusion home |
|---|---|
| Camera/world move | `Camera3D` (3D) or one top-level `CAM_Push` Transform on the merged scene (2D) |
| Object transform | the object's rig Transform/Transform3D |
| Genuine deformation | a few consistent-topology `sPolygon`/`PolylineMask` shape keys |
| Changing illumination | gradient `Offset`/`Start`/`End`, light transforms (04) |

A camera push must not also drift every background field. A product rotating under a fixed light gets no extra light orbit. Do not invent wing flaps, tail cycles, button pressure, text rebounds, star spin, breathing scale or evolving `FastNoise` `Seethe`. `Perturb`/`Shake` modifiers are allowed only for measured, visible jitter. Repeated motion needs a measured cycle (key one cycle, loop it); a single gesture needs one intentional curve.

Simplify noisy fits into a coherent trajectory while keeping measured entry, contact and exit beats. For 3D orientation avoid independently fitted Euler channels (precession): use one dominant axis, or `Transform3DOp.UseTarget` with `Target.X/Y/Z` for look-at, and pick `Transform3DOp.Rotate.RotOrder` deliberately. Verify projected points between poses: a `Locator3D` placed on the object outputs its 2D screen `Position` for direct comparison with tracked reference points. Review position, orientation, scale and apparent screen size together. Check each visible motion's sign changes: dropping a turnaround pose makes an object reverse early even when kept poses match.

## Match cuts: one action carried through the cut

Treat neighboring shots as one motion problem. A hard cut does not prove its elements are
static: motion can live in a stroke length (`sOutline`/`sPolygon` `WriteLength`), a tracked
point, a pose or a moving pivot while `Center` never changes. Do not swap a moving glyph for a
static Text+ character because one still looks close.

1. Inspect 6-12 decoded source frames on each side of the candidate cut, plus the whole
   gesture in real time. Mark the exact cut frame and the timeline-to-comp mapping (above).
   Record outgoing and incoming element, attention point, silhouette, stroke weight,
   direction, motion phase and visible speed. Classify: continuous action match, framing
   change, repeated gesture, or intentional unrelated cut.
2. Continuous action: the first frame after the cut picks the path up where it left off. It does not
   show the last outgoing frame again, start from a standstill or perform the gesture a second time.
   Compare where the anchor projects on screen, its size, its orientation and its speed (and its
   acceleration, when you can see it). A framing change
   alters screen speed: compare in the right space (a `Locator3D` gives screen `Position` for
   3D objects; 2D compare `Center` after all parent Transforms).
3. Share the source. In Fusion one tool output can feed both shot branches live: wire the same
   object subgraph (or Group) into two Transforms, offset time per branch with `TimeSpeed`
   `Delay` (2D branches only: never after a motion-blurred Renderer3D, realities §11 item 27), or read one controller at an offset (`Ctrl_Obj:GetValue("NumberIn1", time - 12)`).
   Otherwise write explicitly matched handoff keys on both shots. A head, arrow, bracket or glyph
   that appears in both shots comes from one source. Where the geometry really is different, line up
   the point the eye follows or the point of contact, not the two tools' `Center`s. Arrows: keep head angle and stroke weight
   (`Thickness`) and extend the shaft with `WriteLength`. Articulated characters: body
   translation agrees with leg extension and contact, then the same pose hands off.
4. Fit sparse Bezier keys to the observed trajectory. Never flat-handle (Easy Ease) every kept
   key or the edit key: it inserts stops between correct poses. Give the handoff key its
   measured slope: velocity v units/frame over neighbor spans D1 (left) and D2 (right) means
   Python `LH = {-D1/3, -v*D1/3}`, `RH = {D2/3, v*D2/3}` (relative, realities §6). Keep a rest
   the reference really shows before a graphic cut. A repeated gesture after a cut may have its
   own launch while sharing geometry, direction logic and curve character.
5. Keep intended cuts hard in framing and typography. No dissolve, morph, spin or long flying
   reposition to hide a mismatch. A replacement branch inherits the state and timing of its
   predecessor. Check for double visibility (both branches' Merge `Blend` 1 on one frame),
   one-frame holes (inclusive `GlobalOut` versus half-open keyed hides), premature incoming
   poses, reset source time (MediaIn `ClipTimeStart`, `TimeSpeed`) and bounds that change with
   font or `Pivot` expressions.
6. Render the full comp (not an inner Group's output) at consecutive frames around each boundary
   plus a real-time clip; stills alone do not validate a match cut. `render.compare` (optional) puts
   reference, render and difference side by side with MAE/PSNR/SSIM; the numbers triage, the frames
   decide. Test one real control edit
   and restore it. Record which cuts changed, which are deliberate graphic cuts, and what still
   differs. Clean expression evaluation does not mean the motion matches.

Regression cases (from the Higgsfield DevDay rebuild; the lessons transfer):
- Down arrows cut to small up arrows: scale and direction cut on a fixed frame, but both shafts
  extend fast-to-slow on each side. Keep the cut and rebuild the moving geometry (`WriteLength`
  keys), not static arrows.
- Loading bar to empty brackets: the same bracket geometry closes and shrinks, then its real
  bounds carry into the next shot's subgraph.
- Character to sprite strip: body lift agrees with leg extension; the chosen strip pose starts at
  the outgoing character's screen position and pose before the row travels.
- Constructed snake to travelling snake: same head/body/tail sources and coordinates at the
  handoff; the right bracket keeps its position and stays under the moving head in Merge order.

Technique background: School of Motion and Adobe articles on match cuts explain action and
framing continuity; every measurement and decision still comes from the supplied reference.

## Recipe: fit a measured move with sparse keys (status: unverified (not yet rendered))

Purpose: replace a per-frame tracked Center with 4 fitted keys. Graph: `OBJ -> OBJ_XF Transform -> scene Merge.Foreground`; `OBJ_XF.Center` driven by `XYPath` whose X and Y each hold a BezierSpline.

Measured (24 fps): enter x 0.20 @f0, fast; overshoot 0.64 @f14; settle 0.60 @f20; hold to f48. Y constant 0.5.

```python
def spline_for(tool, input_id):
    inp = next(v for v in tool.GetInputList().values() if v.GetAttrs()['INPS_ID'] == input_id)
    tool.AddModifier(input_id, 'BezierSpline')       # return value unreliable
    out = inp.GetConnectedOutput()
    assert out, 'modifier not attached'
    return out.GetTool()

def cb(x1, y1, x2, y2, D, V):                           # cubic-bezier -> relative handles
    return {1: x1*D, 2: y1*V}, {1: (x2-1)*D, 2: (y2-1)*V}

xf = comp.FindTool('OBJ_XF')
xf.AddModifier('Center', 'XYPath')
xy = next(v for v in xf.GetInputList().values() if v.GetAttrs()['INPS_ID'] == 'Center').GetConnectedOutput().GetTool()
sx = spline_for(xy, 'X')
rh0, lh1 = cb(0.15, 0.8, 0.35, 1.0, 14, 0.44)          # fast out, soft arrival into overshoot
rh1, lh2 = cb(0.3, 0.0, 0.5, 1.0, 6, -0.04)             # settle back
sx.SetKeyFrames({0: {1: 0.20, 'RH': rh0},
                 14: {1: 0.64, 'LH': lh1, 'RH': rh1},
                 20: {1: 0.60, 'LH': lh2}}, True)        # call twice, or set comp.CurrentTime = 0 before AddModifier (realities §6)
xy.SetInput('Y', 0.5)
print(sx.GetKeyFrames())                                # keys come back as string frames ("14.0")
print([xf.GetInput('Center', t) for t in (0, 7, 14, 17, 20, 30)])
```
Verify: keys exactly {0, 14, 20}; sampled values at 7 and 17 follow the reference within tolerance; render f0-30 at 1x and compare the overshoot frame and first settled frame against the reference at the same mapped times. Check the XYPath default `Center` offset does not shift the result (read back one frame).

## Don'ts and failure lessons

- Do not restart a whole reference-match pipeline for a local addition (06, router doctrine).
- Do not leave `Tracker` outputs connected as the final animation; do not keep dense tracked keys "because they match".
- Do not smooth a hard cut into a transition or a stepped event into a ramp.
- `AddModifier` seeds a key at the current frame; always `SetKeyFrames(..., True)` and read back. A stray key left in place silently changes easing.
- Loops set in the Spline Editor are live; Duplicate-created repeats are copies that do not update.
- Motion that only looks right in stills is unverified. Compare intermediate frames and a real-time playback against the reference.
