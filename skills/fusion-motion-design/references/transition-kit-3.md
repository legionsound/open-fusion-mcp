<!-- transition-kit.md part 3 of 3; index: transition-kit.md -->
## 5. Python: iterate, install, apply, verify

Route: author the `.setting` text, test it inside a real transition comp, write it into Templates, relaunch, then apply with `AddTransition`. `AddTransition` and `TransitionOptions` (`type`, `category` 'simple'/'fusion'/'ofx'/'audio', `position` 'start'/'end', `alignment` 'left'/'center'/'right', `duration`) come from the 21.1 stub and have not been exercised live.
```python
tl = project.GetCurrentTimeline()
a = tl.GetItemListInTrack("video", 1)[0]          # needs ~N/2 frames of handle past each cut
tr = a.AddTransition({"type": "Cross Dissolve", "category": "fusion",
                      "position": "end", "alignment": "center", "duration": 16})
assert tr and tr.GetType() == "transition"
# Paste works only on the Fusion-page current comp (realities §1/§9):
tl.SetCurrentTimecode(tc_inside_transition); resolve.OpenPage("fusion")
cc = resolve.Fusion().GetCurrentComp()
cc.Execute('comp:Paste(bmd.readfile([[' + setting_path + ']]))')   # deferred: poll cc.FindTool
g = cc.FindTool("TK_Push")
assert all([g.ConnectInput("MainInput1", cc.FindTool("MediaIn1")),
            g.ConnectInput("MainInput2", cc.FindTool("MediaIn2")),
            cc.FindTool("MediaOut1").ConnectInput("Input", g)])   # then delete the old Dissolve
at = cc.GetAttrs(); s, e = at["COMPN_GlobalStart"], at["COMPN_GlobalEnd"]    # live: RenderStart/End follow the last Render() call
print(cc.FindTool("A_Move").GetInput("Center", s), cc.FindTool("A_Move").GetInput("Center", e))
print([cc.FindTool("GuardOut").GetInput("Mix", f) for f in (e - 1, e)])    # expect [0, 1]
```
If a LUTLookup value is not at rest at `s` or not complete at `e`, the transition span and Anim Curves disagree. Correct it with `TimeScale`/`TimeOffset`, or rely on the guards and check frames s+1 and e-1 for a pop.

Boundary render (a Saver works on a non-current comp; PNG is valid in 21.1 [live]):
```python
def grab(comp, src, f, path):
    comp.SetActiveTool(None)
    sv = comp.AddTool("Saver", False, -32768, -32768, False, False)
    sv.SetInput("Clip", path); sv.ConnectInput("Input", src)
    comp.Render({"Start": f, "End": f, "Wait": True}); sv.Delete()
for f in (s, s + 1, e - 1, e): grab(cc, g, f, f"/tmp/tk/out{f}_.png")
grab(cc, cc.FindTool("MediaIn1"), s, "/tmp/tk/A_.png"); grab(cc, cc.FindTool("MediaIn2"), e, "/tmp/tk/B_.png")
```
Diff `out<s>` against A and `out<e>` against B with any pixel tool (Pillow if present). Native check with no dependencies: `Merge` (`ApplyMode` "Difference", Background = output, Foreground = MediaIn1) -> `BrightnessContrast` `Gain` 50 -> Saver; the result must be black.

Install: quitting Resolve affects the user's session, so save the project and ask before quitting on their behalf.
```python
from pathlib import Path
d = Path.home() / "Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Transitions/Transition Kit"
d.mkdir(parents=True, exist_ok=True)
(d / "TK Push.setting").write_text(assemble(shell, push_block))   # thumbnail: "TK Push.png", 104 x 58
# after relaunch: a.AddTransition({"type": "TK Push", "category": "fusion", ...})  (type = display name, unverified)
```
Distribute by zipping `Edit/Transitions/<Pack>/*.setting` + `.png` into a `.drfx` in `.../Fusion/Templates/`.

---

## 6. When NOT to reach for this kit

- **Hard cut is the default seam.** A 3D transition on every cut reads as a 2010 wedding video.
- **One family per project** (style lock covers motion too), used at chapter changes, not between every shot. Never mix a 3D family with 2D pushes.
- **Plain crossfade or dip:** use the Edit page's built-in Cross Dissolve / Dip To Color. They are cheaper than any Fusion transition.
- **Continuous action or dialogue across the seam:** cut.
- **Direction carries meaning:** left-to-right push for forward progression, the reverse for going back; stay consistent.
- **Beat:** the hidden or fastest frame is p 0.5. With `alignment` "center" that frame sits on the cut, so put the cut on the beat.
- **Length:** 0.5-0.8 s. Door, peel and cube may reach 1.0-1.2 s only as deliberate chapter moments.
- **No handles:** a centered transition needs ~N/2 frames of media past each cut. Otherwise align left/right or trim; don't let frames freeze.

---

## 7. Verification checklist

1. One GroupOperator with exactly `MainInput1`, `MainInput2`, `MainOutput1`; no MediaOut, no Saver, no footage Loader.
2. Every animated input traces to LUTLookup, ResolveParameter or a time expression; `grep -c BezierSpline` on the file returns 0.
3. Every LUTLookup has explicit `Scale`/`Offset`.
4. `GlobalStart` frame = A and `GlobalEnd` frame = B (the difference render is black).
5. Frames s+1 and e-1 differ only slightly from their neighbours (no pop hidden by a guard).
6. Output alpha = 1 at the midpoint and three other frames.
7. Trim test (16 -> 24 -> 12 frames): motion stretches, the midpoint stays centered, and nothing finishes early.
8. On 1920x1080 and 1080x1920: pushes fully exit, 3D rest frames show no border, wipes cover the corners, masks split at the true center.
9. Mid-transition effects are exactly 0 on the first and last ~15 % of frames.
10. Five or fewer controls with human names and sane defaults.
11. Appears after relaunch in the intended pack folder with its thumbnail, and applies by display name.
12. Acceptable render cost at final quality (Transform `Quality` 8 preview, 16 final for whips).
13. Out-of-range progress is handled on purpose: a manual `Progress` control below 0 or above 1 is
    clamped (`math.max(0, math.min(1, p))`) or deliberately wrapped (`p % 1`), never left to
    extrapolate a push past the frame. [verified live 2026-09-26] In a plain SimpleExpression both
    forms evaluate as written: p -0.2 / 1.3 clamp to 0 / 1 and wrap to 0.8 / 0.3 (Lua `%` is floored).
14. Replace A and B with clips of a different aspect (vertical into 16:9, a 4:3 still) and with
    content longer than the transition: fit, crop, alpha and overlap still hold. [live 2026-09-26:
    this check catches a real defect] The shipped `components/transition.setting` (a `Dissolve`
    fed straight from the two PipeRouters) followed its inputs' size: with a 1080x1920 A and a
    1440x1080 B it rendered 1080x1920 at 0 %, 1440x1920 at 50 % and 1440x1080 at 100 %. Conform each
    input to the output frame first (Merge over an output-size Background, or a Letterbox/Resize)
    so the transition's size never changes.
15. Render the frame just before and just after each seam as well as 0 %, 50 % and 100 %; at a
    reused seam, placement, opacity and motion agree with the neighbouring shot (02 match cuts).

Local Higgsfield connector revision (2026-09-26): keep the content rig (A/B placeholders) apart from
decorative shading, never flatten footage into one clip when editability was asked for, and build an
Edit-page transition template only when the user asks for one (there is no Premiere/.mogrt path here).

---

## 8. Don'ts and failure lessons

- Don't key absolute frames in a template: they finish early or late after a trim.
- Don't trust LUTLookup defaults (the TSV lists 5 as the Scale default).
- Don't publish a third image input; don't include a MediaOut or Saver.
- Don't expect a new or edited template to appear without a relaunch.
- Don't let transparency reach the output: 3D renders, B below Size 1, Canvas edges.
- Don't put Canvas edges on a moving A (dark seam): Duplicate for pushes, Mirror for zooms.
- Don't rely on Renderer3D's implicit view: add a Camera3D at 2.94614*H/W, or use Page Curl's camera image-plane trick.
- Don't light the rest frame; fade lighting in and out with a bell (4.6).
- Don't leave back faces unculled on back-to-back cards (mirrored ghost, z-fighting).
- Don't hard-code `ImageAspect` 1.7778 for diagonal moves.
- Don't use `noise()` or degrees in expressions [live].
- Don't test `Source` = Transition curves in a plain Fusion Composition clip; test inside a real transition comp.
- Don't read Anim Curves "In" as AE's ease-in keyframe: In is the start of the move.
- Don't build a curl from masks or GridWarp; use Bender3D or the shipped Page Curl.
- Don't quit Resolve to reload templates unsaved or without the user's go-ahead.

---

## 9. Not yet verified live

- `DirectionalBlur.Type` indices (2 Centered, 3 Zoom) are inferred from the manual order.
- `DFTLumaRamp.*` sub-inputs are shipped but absent from the TSV (dynamic). `RendererOpenGL.*` rows were appended to the TSV on 2026-09-26. `PipeRouter` works as a group input router (live: `A_In`/`B_In` took `MainInput1/2`).
- `AddTransition` type strings for user templates; `GetFusionCompByIndex` on a transition item; whether the comp's global range equals the transition span on the Edit page (lab: `COMPN_RenderStart`/`RenderEnd` track the last Render call, so the shell now guards on `comp.GlobalStart`/`GlobalEnd`; the Edit-page behavior is untested because templates were not installed).
- Whether Anim Curves hits exactly 1.0 on the last frame; `ResolveParameter` output range.
- Unprefixed `cos` in SimpleExpressions: works (live 2026-09-26, `EaseA.Scale` expression evaluated; `cos` also used in the glass rig).
- Reads such as `EaseA.Scale` and `CurlE.Value` follow the shipped `Mix.Value` pattern; every bus is wired to a consumer because unconsumed modifiers are untested.
- Door rotation signs, camera formula at 9:16, radial corner coverage, luma-ramp leak at Mix 0, and paste without inner `ViewInfo`: settle each on the first render.
- LUTBezier Custom curve = CSS cubic-bezier 1:1 (format inference).
