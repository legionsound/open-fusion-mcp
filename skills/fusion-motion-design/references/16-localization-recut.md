# 16 Recut from a video reference

Load when rendered language versions must match a supplied short edit (a banner, a cutdown) in
separate timelines. Keep the user's chosen workflow; do not start a new text localization unless asked
(that is [13](13-localization.md)). Port of Higgsfield `ae-clean-rig` module 16 (local connector,
2026-09-26). In Resolve most of this is Edit-page work; Fusion takes over only where frame selection
must be exact (retimes, holds). The matcher script was tested on synthetic media on this Mac; the
Resolve steps marked [verified live 2026-09-26] were run in Testbed; the rest are **status: unverified**.

## Establish the reference and the frame map

- Inspect real media type, duration, frame rate, resolution and content with `ffprobe`, even when the
  reference is called an image or a banner. A reference clip can define the requested edit, camera and
  framing even when it is disabled on the final timeline. Equal durations do not prove the language
  versions are in sync. Save the project state with the imported sources before building timelines.
- Review the reference and locate its scenes. Match reference frames to the longer source on reduced
  images, masking translated text regions so language differences do not drive the match. Contact
  sheets are navigation, not proof of an exact cut.
- Infer continuous segments, cuts, speed changes, repeats and freezes from the sequence of matches.
  Unstable nearest-frame matches in a static shot do not establish variable speed. Refine each cut
  boundary and offset at larger image size, and validate every language version independently. Use
  rational rates (2x, 1/2, 24/25), and when frames cannot be matched reliably, say which source is
  missing or which method is still unresolved rather than claiming frame accuracy.
- Record the plan in integer frames: output start (inclusive), output end (exclusive), source start,
  playback rate, frame-selection method (normal, nearest-frame retime, hold, blend). Derive it from the
  current sources; never reuse an earlier edit's scene count, durations or speeds.

Matcher (tested 2026-09-26 on a synthetic reference built from normal, freeze, 2x and repeated
segments with a masked text box: it returned exactly `0 48 24 1 normal`, `48 54 100 0 freeze`,
`54 74 150 2 rate 2x`, `74 86 30 1 normal`):
```python
# match_ref.py REF SRC [ignore boxes x,y,w,h in 0-1 units ...]
# Finds, for every reference frame, the best-matching source frame (small grayscale MSE),
# then groups the matches into segments: normal speed, other rate, freeze, cut.
import sys, subprocess, numpy as np
def frames(path, w=64, h=36):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={w}:{h},format=gray',
                          '-fps_mode', 'passthrough', '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
ref, src = frames(sys.argv[1]), frames(sys.argv[2])
mask = np.ones(ref.shape[1:], np.float32)
for box in sys.argv[3:]:                      # mask translated text regions, e.g. 0,0,0.5,0.2
    x, y, w, h = map(float, box.split(',')); H, W = mask.shape
    mask[int(y*H):int((y+h)*H)+1, int(x*W):int((x+w)*W)+1] = 0
best, err = [], []
for f in ref:
    d = (((src - f) ** 2) * mask).sum(axis=(1, 2)) / mask.sum()
    i = int(d.argmin()); best.append(i); err.append(float(d[i]))
# segment: consecutive output frames whose source step stays constant
segs, s = [], 0
for k in range(1, len(best) + 1):
    if k == len(best) or (k - s >= 2 and best[k] - best[k-1] != best[s+1] - best[s]) or (k - s == 1 and abs(best[k] - best[k-1]) > 3 and k < len(best)):
        step = best[s+1] - best[s] if k - s > 1 else 1
        kind = 'freeze' if step == 0 else 'normal' if step == 1 else f'rate {step}x'
        segs.append((s, k, best[s], step, kind, round(max(err[s:k]), 1)))
        s = k
print('out_start(incl) out_end(excl) src_start step kind max_err')
for g in segs: print(*g)
```
Run `python3 match_ref.py ref.mp4 source_de.mp4 0.05,0.8,0.9,0.15` (mask boxes as x,y,w,h fractions
from the top-left). Output frames index the reference; source frames are 0-based decode order of the
source file. Treat the table as a first plan: confirm every boundary on full-size frames (02 frame
evidence), and expect false "rate" segments inside static shots.

## Timeline and audio assembly

- One timeline per requested version plus a separate reference timeline for comparison; follow
  the user's language and source naming, keep sources, put the new timelines in a clear bin, and mark
  cuts (timeline markers).
- Normal-speed segments: trimmed, unretimed clips. With the Resolve API,
  `mediaPool.AppendToTimeline([{"mediaPoolItem": clip, "startFrame": s, "endFrame": e,
  "recordFrame": r, "trackIndex": 1}])`. [verified live 2026-09-26] `endFrame` is **exclusive**:
  `startFrame` 0, `endFrame` 23 appended 23 frames (source 0..22; `GetSourceEndFrame()` 23, `GetEnd()`
  = `GetStart()` + 23). To include source frame e pass `endFrame` e + 1, then still read back
  `item.GetDuration()` once. Appending a video+audio clip returned only the video item.
- Changed speed: reproduce the observed frame selection exactly. On the Edit page, Change Clip Speed
  with retime process Nearest (no frame blend, no optical flow). When the reference skips or holds
  frames irregularly, build the segment as a Fusion clip: `MediaIn -> TimeStretcher` with
  `SourceTime` keyed from the plan (`StepIn` keys for holds; linear keys for constant rates) and
  `InterpolateBetweenFrames` 0 (Nearest). Never add frame blending or optical interpolation unless
  the reference shows it. [verified live 2026-09-26] MediaIn (a 48-frame PNG counter plate) ->
  TimeStretcher with `StepIn` keys and Nearest showed exactly the keyed source frames (10 held through
  frame 5, 30 from frame 6, then a 2x linear run 20, 22 ... 36); a fractional `SourceTime` 10.5 shows
  frame 11 in Nearest and a 10/11 mix in Blend (`t16_ts_sheet.png`, `t16_fracN.png`, `t16_fracB.png`).
  A MediaIn of a clip shorter than the comp still reads `GlobalOut` 287 and **holds its last frame**
  after the clip ends (`t16_mediain_beyond.png`); a Loader shows nothing after its `GlobalOut`. Follow the retime-key rules in [10](10-fusion-scripting.md).
- Audio is a decision, not a side effect. Cutting the long source's music at arbitrary points breaks
  accents: for a matched banner with no speech to replace, keep the reference's continuous audio and
  say so. When speech languages or tracks differ, resolve which source carries each language; never
  swap the spoken language silently. With one master audio track, disable the other audio tracks
  (`timeline.SetTrackEnable("audio", i, False)`; [verified live 2026-09-26] returns True and
  `timeline.GetIsTrackEnabled("audio", i)` reads False; re-enable with True) so the mix is not
  doubled. Check audio enablement and active range separately from picture, then listen during
  preview and the authorized export check.

## Branch acceptance

- Verify the source frame shown at every output frame (a temporary Text+ counter upstream of any
  Fusion retime, 02), and check the start, the end and both sides of every cut.
- Hard cuts: exactly one active video clip per frame, no gaps, no accidental overlap. Intentional
  transitions: validate their real overlap.
- Output dimensions, frame rate, duration and playback speed match the plan (`ffprobe` on the export).
- Save, reopen, visual verification, export approval and delivery follow [13](13-localization.md).
  Record whether complete playback with sound was done; structural checks do not establish visual
  accuracy. To show where the versions live, open the timelines; do not export video or duplicate
  files just to demonstrate location.
