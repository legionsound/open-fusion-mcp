# Fusion realities, part 3: render efficiency

Part of [fusion-realities.md](fusion-realities.md) (index). §17 holds the render-cost facts measured in
the efficiency lab (2026-09-27, Resolve Studio 21.1, 32 GB Mac, the benchmark ad scenes as workloads). Every
timing is a Deliver job (the path that ships), with the cache purged before each job and repeats where
run-to-run noise mattered (the same 12-frame job measured 15.9 s and 22.9 s). Measured numbers are summarized in the
repository's `docs/results.md`.

## §17. Render efficiency [live, efficiency lab]

### What costs time
1. **Motion-blur time samples are the cost; accumulation DOF is nearly free** [live, efficiency lab, P0].
   On a 1,107-tool 3D scene (3 Renderer3Ds, OpenGL, accumulation 12): accumulation on vs off with motion
   blur off: +0.07 s/frame. Motion blur on vs off: about +0.7 s/frame on a 0.6 s/frame base. They do not
   multiply: passes at one time reuse the uploaded textures, each distinct time re-requests the held
   textures.
2. **With accumulation effects on, the Renderer3D motion-blur `Quality` does not add samples above
   `RendererOpenGL.AccumQuality`** [live, efficiency lab, T02, T18]. At AccumQuality 12, Quality 1 and 8 gave the
   same pixels (MAE 0.07 on the fastest frame, via Deliver and via comp.Render) and the same time. The
   accumulation passes carry both the time and the lens samples (Quality 1 + AccumQuality 12 still shows a
   smooth 12-sample blur). With accumulation off, `Quality` works normally (Q1 vs Q8: MAE 4.0).
3. **At a low AccumQuality, Quality does count** [live, efficiency lab, T18]: on a still frame, Quality 8 x
   AccumQuality 2 looked like Quality 1 x AccumQuality 16 (MAE 0.19) and unlike Quality 1 x AccumQuality 2
   (MAE 0.59). Both observations fit "samples = max(Quality, AccumQuality)" (inference, not a documented
   rule). Practical rule: set the sample count with `AccumQuality`; leave `Quality` at or below it.
   AccumQuality 12 -> 6 on fast camera moves gave SSIM 0.93 (visible stepping): keep 12 for fast moves.
4. **A static texture branch is re-rendered every frame** [live, efficiency lab, T03]: Fusion has no
   automatic static detection in Deliver. A TimeStretcher with a constant `SourceTime` (and
   `InterpolateBetweenFrames` 0) at the point where a static branch feeds an animated tool is served from
   the cache on every later frame, also in Deliver: 73 such freezes on a 1,100-tool scene gave
   bit-identical output and -19 % (freezing the whole 829-tool window texture: -38 %). For a card whose
   whole texture is static, give its per-frame hold a constant `SourceTime` instead of `floor(time + 0.5)`.
5. **Timeline item boundaries cost time** [live, efficiency lab, one-comp]: the same eight scenes Delivered
   in 21.9 min as 8 timeline items (8 comps) and in 14.6 min as one comp on one item with culling
   (item 7). Peak memory was the same (~24 GB); CPU 182 % vs 115 %, GPU 55 % vs 66 %. The first frames after
   each item boundary also rendered differently (further from the reference) on the 8-item timeline.
6. **Fusion's Deliver renders one frame at a time and is GPU-bound** [live, efficiency lab]: Resolve used
   1.2-1.8 cores and 55-66 % GPU; After Effects' render queue (multi-frame rendering) used ~4.3 cores on the
   same Mac. Do not expect core count to help a Fusion Deliver.

### Culling: layer in/out points inside one comp
7. **The tool enabled region stops evaluation** [live, efficiency lab, T04, one-comp]. Set it with
   `tool.SetAttrs({"TOOLNT_EnabledRegion_Start": {1: s}, "TOOLNT_EnabledRegion_End": {1: e}})` (Python; the
   values must be 1-element tables, a bare number is ignored without error; Lua `{s}`); reset with
   `tool.ResetEnabledRegion()`; read back through `GetAttrs()`. It is the Keyframes-editor trim, and it is
   saved with the comp (survived save + restart). Outside its region:
   - a **Merge passes its Background through and does not request its Foreground** (its FG branch costs
     nothing; the S5 glass-card chain culled this way saved 12 % with identical pixels);
   - a Blur feeding a Merge FG, or a Renderer3D feeding a mask image, just delivers nothing and the
     consumer copes;
   - **trap: a Renderer3D (or generator) outside its region that feeds the Foreground of an active Merge
     makes that Merge fail: `comp.Render` reports "Render did not complete" and Deliver writes black
     frames with no error.** Always trim the consuming Merge, never the renderer.
   Unlike a Dissolve at Mix 0/1 or a Merge at Blend 0 (item 24 of §11: those still cook every input), a
   trimmed Merge is a real switch. One comp holding a whole film is therefore safe when each scene enters
   through a trimmed Merge (build-orchestration Module 5).

### Correctness under accumulation
8. **Use Z-buffer transparency with accumulation effects** [live, efficiency lab, B5 root cause].
   `RendererOpenGL.TransparencySorting` 1 (Sorted) re-sorts near-tied cards per accumulation pass; the
   order flips with the jitter and with cache state, so cards drop out of some passes: a card missing on
   every odd frame (motion blur off), a headline at 40 % or on a 4-frame brightness cycle (motion blur on),
   and different pixels from two Deliver jobs of the same range (the first frame of every job differed
   even after a purge). `TransparencySorting` 0 (Z buffer) was bit-identical over three runs, matched the
   reference, cost nothing, and mis-ordered nothing on a full 750-frame film of flat cards (glass card
   over a window included). If a pair of semi-transparent cards ever mis-orders, separate them in depth.
9. **`MotionBlur` itself can be animated** (expression or keys) and Deliver honours it per frame
   [live, efficiency lab, T02]: switching it off on frames whose on-screen streak is under ~0.75 px saved
   24 % on a hold-heavy range with pixels at noise level (MAE <= 0.09).

### Things that do nothing in Resolve
10. **`Depth` inputs do not change processing depth**: an int8 (`Depth` 1) Background/Text+ branch reports
    `TOOLI_ImageDepth` 5 (float32) in the Fusion page, which processes 32-bit float. An image costs width x
    height x 16 bytes (a 3640x2440 canvas: 142 MB). Texture size, not Depth, is the memory lever.
11. **`comp.Render` table keys `Proxy`, `ProxyScale`, `SizeType`, `Width`/`Height` are ignored** (output stays
    full size, pixels identical); `HiQ` and `MotionBlur` work (item 13). A half-size Deliver
    (`FormatWidth`/`FormatHeight`) is not faster: Fusion renders at comp size and Resolve scales.
12. **`TOOLN_LastFrameTime` mislabels GPU work**: the time lands on the tool where the CPU waits for the GPU
    queue (a "0.4-0.8 s Merge" that `UseGPU` 0/1/2 did not change). Profile by Deliver A/B, not by that attr.

### Draft vs final
13. **Draft check renders** [live, efficiency lab, DRAFT]: `comp.Render({Start, End, Wait, HiQ = False,
    MotionBlur = False})` rendered a heavy 3D frame in ~0.8 s vs 2.3-5.7 s final (3-7x); still frames matched
    final (MAE <= 0.03), moving frames lose only their blur (positions exact: the shutter is centred).
    `HiQ = False` alone: MAE <= 0.06, ~2x faster. An in-comp draft switch (renderers' accumulation and
    motion blur off) made Deliver 0.59 vs 1.33 s/frame; the scene builder's `CTRL.Draft` measured 0.045 vs
    ~0.7 s/frame on a lighter scene. Draft answers layout, timing, text, colour and opacity; only final
    answers blur, DOF, glow softness, fine edges and grain.

### Harness facts (for anyone timing renders)
14. Deliver job settings persist: a `FormatWidth` 960 set for one job was inherited by the next job that
    did not set it. Pass the full format on every job.
15. `StartRendering()` with no job IDs renders every queued job in the project, including stale ones
    that write to old paths (an old job overwrote a delivered MP4). Always pass job IDs and remove jobs
    after they finish.
16. Purge (`system.purge_cache`) before each timed job, sample CPU of other processes first (another app
    at 400-500 % CPU distorted a whole-film timing), and repeat A/B jobs (A B B A).

### 2D motion blur, freezes and Multi tools [live, efficiency lab, 2026-09-27]
17. **2D Merge motion blur: 8 samples look like 12** on type rises (worst tile 0.5) and render 15 % faster (72-frame S2
    Deliver 49.9 -> 42.1 s); 4 is borderline (tile 2). Cap 2D Merge motion-blur Quality at 8 unless a close-up needs more.
18. **Renderer3D motion blur does not re-sample an animated texture at subframes**: the accumulation passes move
    geometry only. A 2D animation mapped onto a 3D card needs its own 2D blur, or its motion moved onto the card.
19. **Never freeze a mask branch.** A constant-SourceTime TimeStretcher around a `*Mask` tool disconnected the Merge's
    EffectMask in the lab's generator (12 masks lost); freeze image branches only.
20. **MultiMerge: use Merge chains for animated stacks.** A MultiMerge re-composites every layer whenever any layer
    changes, while a chain keeps its static lower Merges cached: 209 real Merges folded into 5 MultiMerges made the
    check loop 15.6-16.0 s vs 7.7-8.0 s and Deliver 260 vs 128 s (pixels equal). Static stacks: 7-13 % slower. It is a
    tidiness tool; tidy with labeled backdrops instead (fusion-motion-design `references/graph-style.md`). Facts if you
    use one: `LayerEnabledN` = 0 culls that layer (a stepped key culls per frame), `LayerN.Blend` 0 still cooks;
    motion blur is tool-level (a layer that already blurs upstream is blurred twice); no per-layer EffectMask;
    `LayerOrder = ScriptVal { { [0] = 1, 2, ... } }` lists layers bottom to top and must be written in a `.setting`
    (Python `SetInput` on it breaks the stack to nothing).
21. **MultiText and MultiPoly are for tidiness, not speed.** MultiText: same speed as separate Text+ (1.07-1.18 vs
    1.04-1.13 s); a paste resets each `TextN.HorizontalLeftCenterRight` (set `TextN.HorizontalJustification*` and the
    slider after pasting); it has no baseline anchor (shift Center Y up by 0.263 x Size x canvas width, Helvetica Neue);
    no per-layer masks. MultiPoly: bit-identical and 5 % faster than chained polygon masks, but it outputs one mask
    and holds polylines only.
22. **A Background tool's colour is premultiplied by its alpha** when composited: RGB 1 with `TopLeftAlpha` 0.13 composites
    as white. Premultiply the colour yourself (or draw translucent fills with sShapes: Alpha 1 + Opacity) [live, sb3].
23. **Transform motion blur covers a tool's own transform only**: a size or shape change upstream of a moving Merge renders
    crisp. Put the change into a Transform with its own MotionBlur, held upstream at integer frames [live, sb3].
24. **A BezierSpline whose keys carry `Value = Polyline { ... }`** (same point count per key) animates an sPolygon's
    `Polyline` through a paste (a tapered write-on rendered live) [live, sb3].
