# Measured results

All numbers were measured on one Mac (Apple Silicon, 32 GB) with DaVinci Resolve Studio 21.1, September 2026.
"Agent time" is wall-clock for an AI agent working from a brief; tokens and tool calls are the agent's own.

## The benchmark ad

A 25 s 3D SaaS product ad (1920x1080, 30 fps, 750 frames: eight beats with camera moves, depth of field, motion
blur, kinetic type and UI cards) was first built in After Effects with Higgsfield's connector and skills, then
rebuilt cold in other stacks from the same written spec. The client's material is not part of this repository.
Match is the mean grayscale difference (MAE, 0-255) against the After Effects render; lower is closer.

| build | agent time | tool calls | tokens | render of 25 s | 21-frame MAE / SSIM | whole-film MAE |
|---|---|---|---|---|---|---|
| After Effects (reference) | ~1 h 55 min + spec | ~200 | ~0.7M | 133 s cold / 33 s warm | reference | reference |
| Fusion v1, cold, before the scene builder | ~5.6 h | ~830 | ~1.26M | 13-19 min (8 clips) | 2.14 / 0.954 | 1.29 |
| Fusion v1 graph as one culled comp | n/a | n/a | n/a | 14.6 min vs 21.9 min as 8 clips (-33 %) | same frames | 1.22 |
| HyperFrames (HTML/GSAP), cold | 1 h 16 min | ~214 | ~0.61M | 37 s (+16 min for 16-pass motion blur) | 2.30 / 0.951 | 1.55 |
| Remotion (React), cold | ~50 min | ~170 | ~0.58M | 136 s (machine shared) | 2.14 / 0.937 | 1.11 |
| **Fusion v2, cold, scene builder, one comp** | **1 h 19 min** (first full render at 53 min) | **~156** | **~0.69M** | 10.4 min final (0.83 s/frame), 18 GB peak | 2.48 / 0.948 | 1.51 |

What the v2 numbers mean: with the scene builder, an agent builds a 2,911-tool Fusion film in about the time the
After Effects build took, with about a fifth of the first Fusion build's tool calls. Remaining visual differences were
mostly missing features (no backdrop blur, shape-size animation was not motion-blurred at the time; both are
tracked in the scene builder's limits and the second is fixed).

## The explainer film

The film in `docs/media/` (59.3 s, 1,779 frames at 30 fps, seven scenes) was designed from a written brief and
built by agents with the scene builder, then revised over twelve rounds of notes left on the edit timeline.

- One Fusion comp on one timeline clip holds the whole film: about 9,000 tools, with each scene culled to its own
  frames on the film ladder. One controller flips every scene between draft and final quality.
- Final quality: 12-pass accumulation depth of field in the 3D scenes and adaptive 8-sample motion blur.
- Final-quality Deliver ran at about 1 to 7 s per frame, depending on the scene, while Resolve's memory was
  healthy, and slowed to 40 to 60 s per frame once its footprint passed the Mac's 32 GB. Restarting Resolve between parts of the render
  restored full speed. Watch the process footprint (`footprint -p <pid>` or Activity Monitor's Memory column),
  not the resident size, which stayed low while the real footprint grew.
- Frosted-glass cards under accumulation depth of field and motion blur cost 1 to 40 minutes per frame. Turning
  depth of field off in the scene with glass, and motion blur off on the glass cards themselves, fixed it.
- Resolve's render cache (the timeline's Fusion output cache) held memory low and let Deliver reuse 1,050 cached
  frames in about two minutes; frames it had not cached were rendered live.

## Render efficiency (efficiency lab)

Measured as Deliver jobs with the cache purged before each job; details in `fusion-reference`
`references/fusion-realities-3.md`.

- One culled comp for a whole film renders about 33 % faster than one comp per beat, with identical frames.
- Motion-blur time samples are the render cost; accumulation depth of field is nearly free.
- Adaptive motion blur (off on frames that do not move): -24 %. Freezing static card textures: -19 %,
  bit-identical.
- Z-buffer transparency fixed random card dropouts that sorted transparency caused under accumulation.
- Draft renders (high quality and motion blur off) are 3 to 7 times faster; scene-builder drafts about 16 times.
- For full ranges, Deliver is about 70 times faster than Saver renders.
- Resolve's memory grows with each scene rendered and a cache purge frees only about 1 GB, so restart Resolve
  between heavy phases.

## Build loop

- Disk caches: -42 % per build-loop render against live, identical pixels ([caching.md](caching.md)).
- Graph layout: 560 tools tidied in 1.27 s live ([graph-layout.md](graph-layout.md)).
- Scene builder, live: 45 to 58 tools per example scene in one call of 2 to 8 s; restyle plus retime by
  `scene.update` in 2.5 s; flipping to final quality 52 ms.

## Tests

- Offline: 172 unit tests (`tests.test_offline`, `tests.test_layout`). With the data tables generated, 166 pass
  and 6 skip (private benchmark fixture, LuaJIT); on a fresh clone without the tables, 147 pass and 25 skip.
- Live: the smoke test exercised every operation through the real server (164 pass, 0 fail, 8 untested at the
  time of `PARITY.md`, 172 operations); the cache and layout live checks passed in full. `connector/PARITY.md`
  maps every After Effects connector operation to its Fusion counterpart (110 implemented, 40 a different
  model, 47 not applicable).
