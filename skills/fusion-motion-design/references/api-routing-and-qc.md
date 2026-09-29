# Routing, timing, QC and recovery

## Ownership and actual control surfaces

Read the installed host version/edition and current project, timeline, item and
comp before writes. Record an execution contract with their stable identities,
the comp name/index, created tool names and recovery files. No project-specific
IDs belong in reusable instructions.

The active Fusion-page comp and an item's comp can differ. Resolve the item
through the intended timeline, then GetFusionCompCount/GetFusionCompNameList
and GetFusionCompByIndex/GetFusionCompByName. Re-check around bounded mutation
batches. Current UI selection is not a durable addressing contract.

Discover current tool schemas; provider hashes are runtime details. The routes below are
one toolbox: mix them freely in one task and pick per step whatever takes the fewest calls at
the least risk. Route:

- use-fusion connector (`fu_*`): validated ops with readback, quiet bulk pastes and deletes,
  builders, one-call render and inspect, Deliver status/stop, memory, safety rails.
- Official MCP: status, get_whats_new, installed scripting stubs/docs, supported
  run_script (the full Resolve API; one script can beat many ops). A filtered changelog is
  not necessarily the complete release log. A run_script pattern that keeps recurring is a
  candidate connector op.
- Guarded community MCP: documented scoped compound helpers when useful.
  Advertised safe operations are not transactions or automatic qualification.
- Native API: verify signatures/types in the installed stubs before scripting.
  Use unsafe execution only for an authorized need the normal route cannot meet.
- UI: operations not reliably exposed elsewhere, visible state and modal handling.
- Offline files: inspect/export/package source. Instructions describing another
  integration do not prove that integration is callable in this session.

Connector gaps are not application limits. A running-process ping is not UI
health. Preserve unrelated projects, files and manual edits.

## Frame mapping before animation or comparison

Record timeline fps/origin, clip start/end, source in/out, comp range, tool
GlobalOut, Loader holds, Saver range and final export range separately.

For equal frame rates and no retime, let T0 be the clip's first timeline frame
and C0 the *verified visible comp frame at T0*. Then:

`C = C0 + (T - T0)`

Do not substitute COMPN_GlobalStart for C0 without checking it. Trims, handles,
nested comps, speed changes and frame-rate conversion can change the mapping.
For those cases derive the actual source/retime mapping instead of assuming an
offset. Verify two known timeline positions using existing markers or an
authorized temporary frame counter, plus boundaries. The recorded session did
not qualify arbitrary retime/source-offset mappings.

Timeline item end values may be exclusive; export frame ranges may be inclusive.
For a confirmed inclusive range [a,b], frame count is b-a+1 and duration is
count/fps. Verify delivered media with ffprobe rather than trusting a dialog.
SetMarkInOut was observed with timeline-relative marks, not absolute timeline
timecode frames. Re-check that convention on other scopes/builds.

Extra timeline handles are acceptable if deliberate and documented; verify that
delivery marks and export settings select only the intended cut.

## Evidence gates are separate

| Gate | Required evidence |
| --- | --- |
| Documented/exposed | Installed docs/schema or registry |
| Structural | Correct target, tools, connections, scalar inputs, exact keys |
| Temporal | Values and visible behavior at multiple mapped times |
| Rendered | Actual output pixels, not only graph readback |
| Editable | Change a requested control/content value, render, restore |
| Exported/saved | Successful receipt plus actual source/output file |
| Persistence | Reopened/imported artifact retains intended state |
| Creative acceptance | User review or explicitly defined acceptance test |

Passing one gate does not imply the others. Source export is not a reopen test;
sampled QC is not continuous playback; user acceptance is not inferred.

## Efficient visual loop

Batch deterministic work for one semantic unit. Check structure, then render
the smallest informative range. Inspect a full-size hero pose and risky
in-betweens: first visible frame, overshoot, text overlap, exit/entry collision,
mask edge, state change and last frame. Use denser samples where motion is fast.
Render the changed span after a focused correction, then verify final assembly.

Rendered-frame inspection is required for every change; numeric comparison (`render.compare`,
PSNR scans) is optional, for a supplied reference or a regression check against the previous render.
Contact sheets summarize motion economically but can miss one-frame defects.
State the sampling rate/range. Never claim uninterrupted 1x viewing from stills.
For the delivered movie, verify frame count/rate/resolution/duration, decode it,
and inspect pixels from the encoded result. Audio needs its own checks if in scope.

## Partial writes, modals and hangs

On timeout or contradictory readback, stop new mutations. If responsive, inspect
the exact target and named partial state; repair only confirmed intended work.
Do not repeat a whole build blindly or accumulate duplicate nodes.

Inspect connection metadata instead of GetInput on Image/Material/Scene ports.
A synchronous material-input read preceded the recorded UI hang; the OS stack
supported a blocked input evaluation, but did not prove its root cause.

Creation/import and render-completion dialogs can appear late. Recheck observed
UI before a save/export when returns are null or inconsistent. Clear intended
modals, verify no blocker remains, then confirm the receipt and file. Do not
convert null or a tool success string into completion.

IsRendering can include viewer playback. Check IsPlaying and actual progress.
Use supported comp.Stop only for confirmed playback; do not stop a real render
merely because output files already exist.

If UI and calls are unresponsive, stop queuing requests. Establish latest
checkpoint and unsaved scope. Use bounded read-only diagnosis; a supported
abort is appropriate only when an active operation is identified. Force quit
requires explicit approval. Verify responsive UI and persisted state after
recovery; another hang requires reassessment, not automatic restart loops.

A missing-depth red X can be the viewer set to Z. Restore the observed RGB
control, preserving user selection where appropriate; do not alter the graph
to manufacture a depth channel.

Exact native mechanics: [tested recipes](tested-native-recipes.md).
Historical receipts and qualification limits:
[session evidence](qualification-evidence.md).
