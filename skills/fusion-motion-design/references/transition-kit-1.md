<!-- transition-kit.md part 1 of 3; index: transition-kit.md -->
# Fusion Transition Kit: reusable seams as Edit-page Fusion Transition templates

Load when building a house library of transitions for the DaVinci Resolve 21.1 Edit/Cut page (push, whip, zoom-through, blur wipe, door, flip/cube, page peel, luma wipe), or when a Fusion transition must retime to its trimmed duration and survive both 16:9 and 9:16 timelines. Port of Higgsfield `ae-transition-kit` (AE comp -> `.mogrt`). In Resolve the library piece is a `GroupOperator` saved as `.setting` under `Templates/Edit/Transitions`; it shows up in Effects Library > Video Transitions > Fusion Transitions after a relaunch.

Evidence tags: **[shipped]** = Blackmagic's own `Edit/Transitions/*.setting` (67 files from Resolve's `Templates.drfx`); **[manual]**; **[live]** = observed on 21.1.0.14; **[TSV]** = ID in `fusion-21.1-inputs.tsv`. Untagged claims are inference. fps assumption: 24 unless a table lists 25/30.

---

## 0. The contract at a glance

| Item | Rule | Evidence |
|---|---|---|
| Working comp | Edit page: apply a Fusion transition (e.g. Fusion Cross Dissolve) > Open in Fusion Page. `MediaIn1` = outgoing A, `MediaIn2` = incoming B, `MediaOut1`. Build between them. | [manual] |
| Saved template | One `GroupOperator` (or `MacroOperator`) with exactly two image inputs, `MainInput1` (A) and `MainInput2` (B), and one output `MainOutput1`. Create Macro turns the MediaIns/MediaOut into these; the saved file holds no MediaIn for A/B and no MediaOut (122/122 shipped). | [shipped] [manual] |
| Extra images | Never a third image input. For a luma clip, put a `MediaIn` inside and publish its `ClipName` (shipped Luma Wipe). | [shipped] |
| Location | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/Transitions/<Pack>/<Name>.setting`; subfolder = library group; optional `<Name>.png` 104 x 58. | [manual] |
| Appears | Only after quitting and relaunching Resolve, also after edits. | [manual] |
| Timing | No absolute keyframes. Drive everything from Anim Curves (`LUTLookup`, `Source` = `Transition`, the default), Resolve Parameter (`ResolveParameter`), or a `time`/`comp.RenderStart`/`comp.RenderEnd` expression. | [shipped] [TSV] |
| Boundary invariant | First frame = 100 % A pixels, last frame = 100 % B pixels. Proven by rendering both and diffing against the raw inputs. | kit rule |
| Resolution | Normalized units only; one file works at 1920x1080 and 1080x1920. | kit rule |
| Output | `MainOutput1` opaque on every frame; transparency lets lower tracks or black leak onto the timeline (inference). | kit rule |

AE -> Fusion: `OUT_PLATE`/`IN_PLATE` -> `MainInput1`/`MainInput2`. CTRL null + Expression Controls -> published inputs (`InstanceInput`) + expressions reading one master input or a `PublishNumber`. Essential Graphics -> `InstanceInput` with `Name`/`Default`/`MinScale`/`MaxScale`. `.mogrt` + `pr_import_mogrt` -> `.setting` + relaunch + `TimelineItem.AddTransition`. `thisComp.width` -> normalized coordinates (`comp:GetPrefs("Comp.FrameFormat.Width")` when aspect matters). CC Page Turn -> `Bender3D` (4.6). 3D layers + null -> `ImagePlane3D` + `Merge3D`/`Transform3D` + `Camera3D` + `Renderer3D`. `ae_export_frame` -> Saver render of `RenderStart`/`RenderEnd` (section 5).

Where Fusion is better: the ease is a live menu the editor can change (published `EaseIn`/`EaseOut`); one template retimes itself when the transition edge is dragged; a real perspective camera with back-face culling for flips; per-tool motion blur (`MotionBlur`/`Quality`/`ShutterAngle` on Transform and Renderer3D); true mesh bending for a curl.

---

## 1. Duration-following: the progress bus

Every motion reads a normalized progress p in 0..1, shaped by an ease.

| Driver | Output | Use | Notes |
|---|---|---|---|
| `LUTLookup` (Anim Curves) | curve(p) x `Scale` + `Offset`; `Curve` Linear/Easing/Custom; `EaseIn`/`EaseOut` None Sine Quad Cubic Quart Quint Expo Circ Back Elastic Bounce; `Mirror` (0->1->0, forward half twice as fast); `Invert`; `ClipLow`/`ClipHigh`; `TimeScale`/`TimeOffset` (fractions of duration) | everything; every shipped transition uses it | [shipped] [TSV]. Always write `Scale` and `Offset`: the TSV default column says 5 for Scale, while shipped Cross Dissolve relies on 1. |
| `ResolveParameter`, `ID` = `TRANSITION_PERCENTAGE` | linear percentage x `Scale` + `Offset` | linear drivers (plain `Dissolve.Mix`) | [manual] [TSV]. No easing. Probe whether it reads 0..1 or 0..100. |
| time expression | `(time - comp.GlobalStart)/(comp.GlobalEnd - comp.GlobalStart)` | guard switches, custom math | Third-party MrAT transitions ship `time/comp.RenderEnd`. **Live 2026-09-26: `comp.RenderStart`/`RenderEnd` are whatever the last `Render({Start, End})` or preview range set** (a single-frame QA render of frame 143 made them 143/143, so RenderStart-based guards showed 100% B mid-transition). Use `GlobalStart`/`GlobalEnd`; Anim Curves `Source "Transition"` already follows the global range in a plain comp (A_Move Center 0.4368 at 25% of 0..287 = cubic in-out). |

**Bus idiom** [shipped Slice Push: `Mix = LUTLookup {}` wired to a mask, read elsewhere as `1.0-Mix.Value`]: one `LUTLookup` per timing shape, wired by `SourceOp` to its main consumer; other inputs read it as `<Name>.Value` or read its inputs (`EaseA.Scale`). Keep every bus wired to at least one input (an unconsumed modifier may not evaluate; untested). Share ease menus by expression as Slide Left does: `EaseIn = Input { Value = FuID { "Cubic" }, Expression = "EaseA.EaseIn", }`.

| Bus | Settings | Shape |
|---|---|---|
| Ease | Easing, Cubic/Cubic, `Scale` 1, `Offset` 0 | 0 -> 1 slow-fast-slow |
| Bell | Easing, Sine/Sine, `Mirror` 1, `Scale` 1.25 x peak, `Offset` -0.25 x peak, `ClipLow` 1 | exactly 0 for the first and last ~15 %, peak at p 0.5. For blur, dip, camera pull-back. Stretch Blur ships the same trick (`Mirror` 1, `Scale` 2, `Offset` -0.4) [shipped]. |
| Window | Custom, LUTBezier keys (0,0) (0.42,0) (0.58,1) (1,1) | fast swap around the cut; Stretch Blur ships 0.4/0.6 [shipped] |

Ease menu vs cubic-bezier, assuming standard Penner curves (verify one by probing): Sine ~ (0.37,0,0.63,1), Quad ~ (0.45,0,0.55,1), Cubic ~ (0.65,0,0.35,1), Quart ~ (0.76,0,0.24,1), Quint ~ (0.83,0,0.17,1), Expo ~ (0.87,0,0.13,1); Back overshoots. Anim Curves **In** is the start of the move; AE's "slow-out of the first key" is Fusion's In.

Exact cubic-bezier: `Curve = FuID { "Custom" }` plus a two-key lookup. The domain is 0..1 on both axes and `.setting` handles are absolute, so `cubic-bezier(x1,y1,x2,y2)` should map 1:1 (format inference, unverified): `[0] = { 0, RH = { x1, y1 } }, [1] = { 1, LH = { x2, y2 } }`.

Resolve Parameter form (manual recipe): `Mix = Input { SourceOp = "RP1", Source = "Value", }` with `RP1 = ResolveParameter { Inputs = { Scale = Input { Value = 1, }, Offset = Input { Value = 0, }, }, }`.

Never use BezierSpline keys or KeyStretcher (the title tool) in a transition: keys at frames 0 and 15 finish early or late after a trim.

---

## 2. The boundary-frame invariant and the shell

Design rules:
1. Every moving part is at rest at p = 0 and p = 1: Transform `Size` 1, `Center` (0.5,0.5), 3D rotation 0 or 360, `Dissolve.Mix` 0/1, blur 0, gain 1.
2. Effects that exist only mid-transition ride a Bell bus (negative offset + `ClipLow`), so they are exactly 0 near both ends, not just small.
3. 3D rest frames are unlit (Renderer3D `RendererSoftware.LightingEnabled` 0, its default) and the plane fills the frame exactly (camera formula, section 3).
4. A moving A never uses `Edges` Canvas: Duplicate (2) for pushes, Mirror (3) for zooms (shipped slides use 3). Index order 0 Canvas, 1 Wrap, 2 Duplicate, 3 Mirror is from the manual.

**The shell.** Every build in section 4 is dropped into this template. `A_In`/`B_In` are `PipeRouter`s (registry + shipped; input ID `Input`), so the raw clips fan out to the effect and to the two guard Dissolves. The guards snap the first and last frames to the raw inputs, which removes resampling drift from 3D renderers and filtered transforms. They do not hide a design error: frames 1 and N-2 must still be continuous (checklist).
```lua
{
	Tools = ordered() {
		%NAME% = GroupOperator {
			Inputs = ordered() {
				MainInput1 = InstanceInput { SourceOp = "A_In", Source = "Input", },
				MainInput2 = InstanceInput { SourceOp = "B_In", Source = "Input", },
%INPUTS%
			},
			Outputs = { MainOutput1 = InstanceOutput { SourceOp = "GuardOut", Source = "Output", }, },
			ViewInfo = GroupInfo { Pos = { 0, 0 } },
			Tools = ordered() {
				A_In = PipeRouter { ViewInfo = PipeRouterInfo { Pos = { -110, 0 } }, },
				B_In = PipeRouter { ViewInfo = PipeRouterInfo { Pos = { -110, 99 } }, },
%TOOLS%
				GuardIn = Dissolve { Transitions = { [0] = "DFTDissolve" }, Inputs = {
					Background = Input { SourceOp = "A_In", Source = "Output", },
					Foreground = Input { SourceOp = "%FX_OUT%", Source = "Output", },
					Mix = Input { Expression = "iif(time <= comp.GlobalStart, 0, 1)", },   -- live: RenderStart follows the last Render() range
				}, },
				GuardOut = Dissolve { Transitions = { [0] = "DFTDissolve" }, Inputs = {
					Background = Input { SourceOp = "GuardIn", Source = "Output", },
					Foreground = Input { SourceOp = "B_In", Source = "Output", },
					Mix = Input { Expression = "iif(time >= comp.GlobalEnd, 1, 0)", },
				}, },
			},
		},
	},
	ActiveTool = "%NAME%",
}
```
Assembler (each build block in section 4 starts with `-- NAME <group> FX_OUT <last effect node>`, then `-- INPUTS` and `-- TOOLS` parts):
```python
import re
def assemble(shell: str, block: str) -> str:
    name, fx = re.search(r"-- NAME (\w+)\s+FX_OUT (\w+)", block).groups()
    inputs, tools = block.split("-- INPUTS\n", 1)[1].split("-- TOOLS\n", 1)
    return (shell.replace("%NAME%", name).replace("%INPUTS%", inputs.rstrip())
                 .replace("%TOOLS%", tools.rstrip()).replace("%FX_OUT%", fx))
```
All seven assembled files parse with the connector's Lua-table parser (`connector/fusion_connector/luatable.py`). Inner tools carry no `ViewInfo`: positions are cosmetic, and paste is expected to tolerate their absence (untested; add `ViewInfo = OperatorInfo { Pos = { x, y } },` if a paste refuses). Use Node Editor > Arrange to tidy the result.

---

## 3. Exposed-controls discipline and resolution-agnostic units

- **Publish, don't re-bake.** Publish the real master input (`InstanceInput`) and make every dependent input follow it by expression (`B_Move.ShutterAngle = "A_Move.ShutterAngle"`). When one value has no natural home, use a `PublishNumber` (Slice Push's `PublishAngle` feeds three inputs by `SourceOp`) [shipped]. For a menu, Spin uses a `Fuse.Wireless` node named `Controls` with a `MultiButtonControl` user control, read as `Controls.Direction` [shipped].
- **Cap at 5 controls** (a color row counts as one): direction, ease in, ease out, one intensity, motion blur.
- **Human names, stable across the library**: `Direction (deg)`, `Ease In`, `Ease Out`, `Motion Blur`, `Shutter`, `Smear`, `Depth Dip`, `Softness`, `Border Color`. Same name, same meaning everywhere, so an agent can predict IDs.
- `InstanceInput` keys: `SourceOp`, `Source`, `Name`, `Default`, `MinScale`/`MaxScale`, `Width = 0.5` (pairs two controls on one row), `ControlGroup` (same number = one row, e.g. R/G/B), `Page`. `ordered()` order = Inspector order [shipped].
- Internal names are semantic, alphanumeric/underscore (`A_Move`, `EaseA`, `GuardOut`). Expressions reference names: renaming breaks them, and pasting a second copy into one comp renames colliding nodes.

| Quantity | Resolution-agnostic rule |
|---|---|
| Push distance | Normalized: 1.0 = one frame on either axis at any aspect. `Vector` with `ImageAspect` 1 = one frame per unit on both axes. Shipped slides use 1.777778 with `Scale` 0.562 for vertical (fine axis-aligned, wrong on diagonals). |
| Half-frame mask | `RectangleMask` is per-axis: `Width` 0.5, `Height` 1 = exact half at any aspect [live]. |
| Circle | `EllipseMask` is width-relative on both axes; covering diameter = `sqrt(1 + (H/W)^2)` width units. |
| Blur size | Width-relative; calibrate once by render. |
| 3D fill | Default Camera3D (AoV 19.26427 vertical, `ResolutionGateFit` Height [TSV]; **only the AddTool default**: a Camera3D created by `.setting` paste comes up `FilmGate "TV"`, AoV 24.33 [live], so the builds write `FilmGate "BMD_URSA_4K_16x9"` plus `ApertureW` 0.8315 / `ApertureH` 0.4677, because FilmGate alone left the TV apertures in a later rebuild [from rebuild log, K2]) fills the frame with a 1-unit-wide ImagePlane3D at `Translate.Z = 2.94614*H/W` (1.6572 at 16:9, 5.2376 at 9:16). Spin encodes the same curve as a cubic in aspect [shipped]. |
| Aspect | `comp:GetPrefs("Comp.FrameFormat.Width")/comp:GetPrefs("Comp.FrameFormat.Height")`; escape quotes inside `.setting` strings (`\"`) [shipped]. |
| Generators | `UseFrameFormatSettings = 1` [shipped]. |

---

