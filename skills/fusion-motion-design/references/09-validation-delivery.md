# 09 Native validation, resolution and delivery

Load for final checks, resolution upgrades (2K/4K), render defects (seams, banding, shimmer), complexity audits, and delivering a Fusion iteration. Evidence gates are separate (api-routing-and-qc.md): structural, temporal, rendered, editable, exported/saved, persistence, creative acceptance. Passing one does not imply another.

## Verify and deliver an iteration

- Inspect rendered frames (always required): initial pose, motion extrema, transitions, final pose, and dense frames around fast events, against the brief and design spec, and against a supplied reference at identical mapped timestamps (`C = C0 + (T - T0)`) when one exists. Inspect full resolution and playback speed, whole frame and component crops. Numeric comparison (`render.compare`, the PSNR scan below) is optional: for a supplied reference or version-to-version regression, never a substitute for looking. A few attractive stills do not establish animation fidelity; contact sheets can miss one-frame defects, so state the sampling rate.
- Check seams, banding, shimmer, disconnected parts, font substitution, clipped effects (`ClippingMode` Frame), missing media (Loader `MissingFrames` behavior), blank frames, wrong duration and audio drift. Where surfaces overlap, run the hidden one on under the front edge: two edges fitted separately to touch will flicker with antialiasing gaps in motion. Keep the visible edge crisp instead of blurring the join.
- Only a complete file on disk counts as a render. `comp.Render(...)` returning True, a job sitting in the Deliver queue or a script that exited cleanly are not evidence of one.
- Audit real complexity recursively (script below): tools by RegID inside every group, sShape/polyline point counts, BezierSpline key counts and interpolation, expressions and their errors, modifiers and orphans, dependencies (Loader paths, MediaIn clips, fonts, Fuses). Do not hide complexity inside Groups or report only top-level node counts.
- Keep requested resolution and frame rate. Changing only the output size is not an upgrade (see below).
- Hand over a saved version with a preview or side-by-side the user can actually open, list what still differs without softening it, claim "1:1" only with proof, and make sure the previous version can always be restored.
- Apply the user's visual notes to the example they were about, not a new one. If they have not accepted it yet, or asked to keep working on it, it is not approved, and it is not time to move on to something harder. Ordinary reversible edits they already asked for need no extra sign-off.

## Check both resemblance and regressions

Run two separate comparisons. Against the supplied reference (if there is one), the question is how close
the render is; against the last saved render, the question is what changed that should not have. A
shared source can look right at the start and be broken twenty seconds in, so after editing one (06),
re-check every place that uses it, even branches you did not touch.

- Locate differences with a sparse full-range comparison, then inspect full-resolution
  consecutive frames at each suspicious event. A pixel-difference threshold is triage, not proof
  of motion quality or identity. Record the sampling rate, expected change ranges, exceptions
  reviewed and checks actually run; never widen an exclusion range to make a scan pass.

```bash
# previous vs current PNG sequences: per-frame PSNR, lowest first (triage only)
ffmpeg -v error -i prev/f_%04d.png -i cur/f_%04d.png -lavfi psnr=stats_file=psnr.log -f null -
awk '{split($6,a,":"); print a[2], $1}' psnr.log | sort -g | head   # lowest psnr_avg first; n is 1-based; inf = identical (tested ffmpeg 9.0.1)
```
- For the changed behavior cover entrance, full pose, pose changes, contact/extrema, exit and
  both sides of every cut. Inspect whole-frame layout and detail crops together. Exercise the
  advertised manual controls (pose, build, phase), ordinary Transforms and a real text/content
  edit, and restore intended values even if a check fails. Visual acceptance is separate from
  "no expression errors".
- Delivered media: confirm concrete dimensions, frame rate, frame count/duration and audio
  alignment with `ffprobe`; a corrupt or unfinished movie can exist on disk. Confirm exported
  stills exist and decode. When a review is assembled from separately rendered segments, keep
  exact frame ranges, color interpretation (Rec.709 tags), audio continuity and provenance, and
  never ship an external-only fix that the saved comp does not contain. Keep superseded
  comparisons out of the primary review set.

## Resolution and quality in Fusion terms

Treat 2K/4K as an output tier that still needs exact pixel dimensions and aspect; keep established dimensions unless the task changes them. What changes with resolution:

| Scales automatically (normalized) | Must be recomputed or re-verified |
|---|---|
| Centers, mask `Width`/`Height`/`CornerRadius`, Text+ `Size` (width-relative), sShape geometry, Erode/Dilate `Amount` (width fraction) | Generators (`Background`, `TextPlus`, `sRender`, masks) with `UseFrameFormatSettings` 0 and explicit `Width`/`Height`; Merge Background sizes; `Crop`/`BetterResize`/`Letterbox` pixel sizes; Saver/Renderer3D output size; Blur/Glow sizes (not pixel radii: calibrate by render); stroke widths that must stay optically constant; photo source resolution vs largest on-screen size |

Timeline Fusion clips are conformed to timeline resolution; a single-clip comp runs at source resolution; Referenced Compositions keep source resolution. Generators inside templates set `UseFrameFormatSettings` 1 to follow the timeline. The Fusion page processes 32-bit float; Resolve ignores Fusion depth prefs, so banding comes from sources (8-bit media, quantized gradients), `Background` `SubPixel`, or the delivery codec, not the comp depth. Distinguish viewer proxy/HiQ-off previews from a full-quality render: Resize/Scale use nearest-neighbor in non-HiQ unless "Only Use Filter in HiQ" is off; OpenGL renderer supersampling applies only in HiQ/final. Fix the local source of a defect before any blanket blur or upscale. Check nested sampling (Transform `FilterMethod`, concatenation), antialiasing (`sRender` `ShapeRasterizer.Supersampling`, Text+ `AntiAliasing`, Renderer3D supersampling) and effect bounds (DoD) when edges look rough.

## Before an expensive render

1. Structural: correct comp, tool names, connections (`GetConnectedOutput`), no orphan modifiers, no Merge without Background.
2. Expressions: every expression input evaluates (read `GetInput(id, f)` at two frames; a None/nil means a failing expression such as `noise()` in a SimpleExpression).
3. Dependencies: every Loader path exists, MediaIns resolve, fonts installed.
4. One representative frame rendered and inspected at full size.
5. Then a completed motion render of the changed span and its transitions.

## Draft while building, final to judge [live, efficiency lab]

| stage | render | judge | do not judge |
|---|---|---|---|
| building (layout, keys, text, colour) | draft: `comp.Render({..., HiQ = False, MotionBlur = False})`, or a scene controller's Draft switch (renderers' accumulation and motion blur off). 3-7x faster on a heavy 3D scene; still frames match final within MAE 0.03, moving frames lose only their blur | positions, sizes, timing, text content, colours, opacity ramps | blur, DOF, glow softness, fine edges, grain |
| before calling a beat done | final on the hero frames, the fastest in-between, and the first/last frame of every culled layer (enabled-region edges) | motion blur, DOF, edges | - |
| before delivery | Deliver of the whole range, every frame scanned against the previous version or the reference | flicker, dropouts, first frames after item boundaries | - |
Proxy, `SizeType`, `Width/Height` in the render table and a half-size Deliver do not make Resolve render faster.
For timing comparisons: Deliver jobs (the shipping path; far faster than Saver renders), purge before each
job, check other processes' CPU first, repeat A B B A (the same job measured 15.9 s and 22.9 s), pass the full
format and explicit job IDs on every job (settings persist between jobs; a start without IDs renders every
queued job). Evidence: fusion-realities §17.

## Review a draft before anyone sees it [live, explainer build 2026-09-27]

A contact sheet every 12 frames (0.4 s) hid what a viewer saw at once: text covered by floating fragments, a value cut
by the frame edge, muddy half-second gaps between beats. The user caught them; the checks below catch them first.

- Run [`scripts/draft_qc.py`](../scripts/draft_qc.py) on every full draft: `python draft_qc.py film.mp4 out/ --map
  music_map.json`. It writes 5 fps review sheets (one labelled tile every fps/5 frames, with section bar.beat when a
  music map is given) and reports DEAD runs (no subject), MUSH runs (dark soft blobs with nothing legible), LOW COVER
  runs, the flash count per second, and frozen frames. Then LOOK at every sheet; the checks only point.
- Text occlusion: nothing may cross a title's glyphs while it is readable. In a 3D scene, project every layer through
  the camera during each hero hold (start, middle, end) and test the title's box, or check it on the sheets. Keep
  floating depth fragments behind or away from type.
- Title-safe: no text or key value crosses a 5 % margin while it is meant to be read (leaving frame during a move is
  fine).
- Every frame has a subject: an incoming title forms while the camera approaches, and the outgoing one stays until the
  next landing. Transitions never pass through empty fields or blurred dark slabs.
- Photosensitivity (WCAG 2.3.1): at most 3 large luminance changes in any second. Two drafts failed it on camera whips
  across a black-and-white stripe field and on flying through a bright screen; fix by keeping stripes on a slow drift
  and fading bright planes before the camera passes them.
- Continuous-camera pieces also get a frozen-frame count of 0: holds stay alive (drift, handheld shake, focus breathe).
- Send the reviewer a phone-size copy too (720p H.264, under 30 MB) next to the full file.

## Render and deliver routes

| Need | Route |
|---|---|
| Frame checks from a comp | `Saver` (`Clip` path, `FormatID` "PNGFormat", 4-digit padding `name_0000.png`) + `comp.Render({"Start": a, "End": b, "Wait": True})` (live-verified 2026-09-26) |
| Frame checks through the shipping path | Deliver an image sequence (TIFF RGB 16 or PNG) of the frames: 1-2 s/frame on a heavy scene vs ~4-6 s per Saver `render.frame` [live, efficiency lab]; marks are timeline frames (timecode start + comp frame, e.g. 108000 + f at 01:00:00:00, 30p) |
| Timeline delivery | `MediaOut1` feeds the timeline; render on the Deliver page (Resolve API: `project.SetRenderSettings`, `AddRenderJob`, `StartRendering`, `IsRenderingInProgress`, `GetRenderJobStatus`; check the installed stub). Only the first MediaOut goes to the timeline |
| Review movie from PNGs | `ffmpeg -framerate 24 -i name_%04d.png -c:v libx264 -pix_fmt yuv420p review.mp4` |
| Proof of delivery | `ffprobe` frame count, rate, resolution, duration; full decode `ffmpeg -v error -i out.mov -f null -`; inspect pixels from the encoded file |

Frame ranges: Saver/`comp.Render` use comp frames; Deliver uses timeline marks (`SetMarkInOut` observed timeline-relative). Inclusive range [a, b] has b - a + 1 frames. Timeline item end values can be exclusive. Completion dialogs may appear late; clear them before save/export and do not treat a null receipt as completion.

## Complexity audit (read-only; status: unverified (not yet run))

```python
from collections import Counter
tools = comp.GetToolList(False)                      # includes modifiers and splines
by_id = Counter(t.GetAttrs()['TOOLS_RegID'] for t in tools.values())
keys, exprs = {}, []
for t in tools.values():
    a = t.GetAttrs()
    if a['TOOLS_RegID'] == 'BezierSpline':
        k = t.GetKeyFrames() or {}
        keys[a['TOOLS_Name']] = len(k)
    for inp in t.GetInputList().values():
        e = inp.GetExpression() if hasattr(inp, 'GetExpression') else None
        if e:
            exprs.append((a['TOOLS_Name'], inp.GetAttrs()['INPS_ID'], e[:60]))
dense = {n: c for n, c in keys.items() if c > 12}
print(by_id.most_common(15)); print('splines', len(keys), 'dense', dense); print('exprs', len(exprs))
```
Report per semantic group: tool count, shape/polyline count, spline count and max keys, expression count. Flag any spline with a key on most frames, any polyline with dozens of points for a simple silhouette, and modifiers whose host no longer exists. Polyline point counts are best read from an exported comp text (`item.ExportFusionComp`) since Python `SaveSettings` returns empty.

## Package and hand off

- Save the iteration: export the comp text (`item.ExportFusionComp(path, i)`) next to the project media; project saves/exports (.drp) stay within the user's authorization and chosen project.
- Media: keep generated and source files in a project `media/` folder with the 05 manifest; Loader paths absolute in the comp but recorded relatively in the manifest; templates use `Setting:` relative paths inside `.drfx`.
- Retain editable 3D sources (OBJ/FBX/Alembic, textures) and any required renders.
- List fonts and Fuse/plugin/renderer dependencies (e.g. OpenGL-only features); include font files only when redistribution is permitted, with their terms.
- Guide: which controller and controls to animate, units and ranges, how to replace text and media, camera location, known fixed limits and material substitutions. Do not describe an unverified result as exact.

## Learn from feedback without overstating

Lessons the user confirmed become defaults for later work: simpler geometry that means something, text and media left editable, motion backed by the reference, gradients placed on purpose, rigs run from controllers, and checks made on real renders. One accepted piece does not prove every style is solved. Two earlier exercises (an open-ended Apple-style text piece and a font-substitution case) were received less well; keep their specific failure lessons rather than assuming a similar effect stack will work next time.

With an open brief, settle the visual direction, the type system and the rules of motion first; effects come after. Routine reversible work keeps moving without stopping for approval. When the user supplies a reference, its design and timing beat any general style recipe.

## Don'ts

- Do not judge from the viewer; judge from a completed render or decoded delivery file.
- Do not upscale by changing one size field; audit every pixel-unit input.
- Do not claim continuous 1x review from sampled stills.
- Do not overwrite the only previous version.
