<!-- design-first.md part 3 of 3; index: design-first.md -->
## 8. OGraf and Lottie: the asset route

The user's rule: **native editable Fusion nodes are the goal; imported OGraf/Lottie files are assets, not editable native graphs.** Use this route only for an explicitly chosen existing animation whose whole-unit editing boundary is acceptable.

### 8.1 What exists (TSV/registry, 21.1.0.14)

- One loader for both formats: **`OGrafLoader`** (Generator, output `Output`). There is no separate Lottie registry ID.
- Manual (I2): OGraf is the EBU open HTML5 broadcast-graphics spec (manifest `.json`); Lottie loads as `.lottie`; alpha is preserved; both can also come in from the Media Pool on the Edit page. Whether a plain Lottie `.json` loads is unverified.
- Inputs (TSV): `TemplatePath` (Text, File control), `TrimIn`, `TrimOut`, `TimeScale` (0.01-20; changes the Global Range to match), `HoldFirstFrame`, `HoldLastFrame`, `Loop`, `ReloadAction`, `AddPlayAction`/`AddStopAction`, `ScheduledAction_0..19.Name/Value/Time`, and template-exposed parameters `DynParamText0..19`, `DynParamNum0..19`, `DynParamCheck0..19`, `DynParamColor0..19_R/_G/_B/_A`. Global In/Out behaves like Loader (shrinking trims, extending adds holds).
- Rules from the manual: no Reverse; Play/Stop scheduled actions mark where the template's own ease-in/out begin; **a single-step template's Play only works if preceded by a Stop**.

### 8.2 Editability boundary

| Editable in Fusion | Baked inside the asset (not editable) |
|---|---|
| File path; Global In/Out, Trim, Time Scale, Hold, Loop; Play/Stop actions (OGraf) | Internal layers, shapes, paths |
| Parameters the template exposes (DynParam text/number/checkbox/color) | Copy not exposed as a parameter, font, kerning, layout |
| Everything downstream: Transform, Merge, masks, color, glow, motion blur, 3D (ImagePlane3D) | Easing and the timing relationships between internal elements |
| Timeline placement and trims on the Edit page | Colors not exposed as parameters |

**Choose the asset route** for a supplied brand sting or logo animation that must match its source exactly, an OGraf package with data fields, or illustrative vector animation nobody will retime internally. **Choose native** for anything whose copy, layout, colors or timing the editor must change (every SaaS/UI/title frame, including the §4 template). Never send raw HTML/CSS/JS, React, Remotion or HyperFrames source to Fusion; OGraf loads only OGraf-packaged graphics.

```lua
-- status: unverified (TemplatePath set from text is untested; the node may open a browser when added in the UI)
Logo_Sting = OGrafLoader {
	NameSet = true,
	Inputs = {
		TemplatePath = Input { Value = "/abs/assets/logo_sting.lottie", },
		TimeScale = Input { Value = 1, },
		Loop = Input { Value = 0, },
		HoldLastFrame = Input { Value = 48, },
	},
	ViewInfo = OperatorInfo { Pos = { 330, 330 } },
},
-- downstream: Logo_Sting -> Logo_Sting_Xf (Transform) -> Logo_Sting_Mrg.Foreground
```

Python alternative: `comp.SetActiveTool(None); comp.Lock(); t = comp.AddTool("OGrafLoader", False, x, y, False, False); comp.Unlock(); t.SetInput("TemplatePath", path)` (Lock suppresses file dialogs **[live]** for loader-type tools). **Verify:** render a mid and an end frame over a colored Background (checks alpha and premultiplication: no dark or bright fringe), confirm duration against the source (`TimeScale` = source fps / timeline fps if it plays at the wrong speed), confirm fonts in Lottie text layers rendered.

### 8.3 Lottie -> native nodes by translation (the `ae_build_scene_from_lottie` analog)

There is no converter. When a Lottie must become editable, translate it into `.setting` text. Fusion is more faithful than AE's converter here: BezierSpline segments are true 2D cubic Beziers, so Lottie easing converts exactly, overshoot included.

| Lottie | Fusion `.setting` |
|---|---|
| `fr`, `ip`, `op` (frames; `op` exclusive) | keys in frames; if `fr` differs from the timeline, scale `t * fps/fr` (fractional keys are legal) |
| key `t`, `s`, `o{x,y}`, `i{x,y}` | BezierSpline key at `t`; `RH = {t0 + o.x*D, v0 + o.y*V}`, `LH = {t0 + i.x*D, v0 + i.y*V}` (absolute; D = t1 - t0, V = v1 - v0) |
| `h: 1` hold | Step Out on that key / Step In on the next (`Flags = { StepIn = true }` seen in shipped files; manual wording contradictory, verify on the curve) |
| position `p` [x, y] px, Y down | XYPath with separate X and Y BezierSplines (per-dimension `o`/`i`); `x/W`, `1 - y/H` |
| `ks.o` 0-100 | Merge `Blend` (/100) |
| `ks.s` [100, 100] | Transform `Size` (/100), or `XSize`/`YSize` with `UseSizeAndAspect` 0 |
| `ks.r` degrees | Transform `Angle` degrees; negate (Lottie clockwise-positive, Fusion Y-up counter-clockwise; inference, verify) |
| `ks.a` anchor | Transform `Pivot` (normalized, Y flipped) |
| `ty 1` solid (`sc`) | Background solid (hex / 255) |
| `rc` rect with `r` / `el` ellipse | Background + RectangleMask (`CornerRadius` formula) / EllipseMask (both axes width-relative) |
| `sh` path | PolylineMask points (relative to the mask `Center`, Y flipped, handles relative to their point) |
| `fl` / `st` | Background color / mask `Solid` 0 + `BorderWidth` |
| `tm` trim | mask `WritePosition` / `WriteLength` |
| `ty 5` text | Text+ (`Size` = 1.70 x px / W for Open Sans) |
| `ty 3` null + `parent` | unit `_Xf` Transform chain, or controller expressions |
| `ty 0` precomp (`refId`) | a unit subgraph, optionally a GroupOperator |
| `gf`/`gs` gradients | Background Type "Gradient" (native, any stops; AE's converter dropped these) |
| masks, mattes | `EffectMask`, Merge `Operator` "In"/"Held Out", ChannelBoolean |
| expressions | SimpleExpressions (Lua, radians, `time` in frames) |

---

## 9. Predict-don't-probe gotchas

AE's list, ported, plus the Fusion-specific traps that bite a one-call build.

- **Colors and opacities are 0-1 floats everywhere.** No 0-255 inputs (AE Drop Shadow's 0-255 trap has no Fusion twin). Shadow `Alpha` 0-1, Merge `Blend` 0-1.
- **Points never take a BezierSpline.** `Center`/`Pivot`/`CharacterOffset` animate through XYPath (per-axis splines), PolyPath (`Displacement`), or a `Point(...)` expression (AE's "easy ease errors on 2D Position" becomes this).
- **Stacking = Merge wiring.** Foreground sits over everything upstream in Background. Author bottom-up: background trunk first, units in stacking order. Reorder by rewiring (or MultiMerge `LayerOrder`), not by list order in the file.
- **Mask space.** A mask on a plate's `EffectMask` lives in that plate's frame (normalized to the plate image); put it before the unit `_Xf` so it travels with the unit. Polyline points are relative to the mask `Center`. An empty or shape-less mask blanks the image.
- **Anchor = `Pivot`.** Units not at frame center need `_Xf.Pivot` at their own center before any scale or rotation.
- **Glow on light UI.** Keep SoftGlow `Threshold` high (0.8+) and `Gain` near 1 on light backgrounds, and glow a branch (the pill), not the whole merge. The Fusion page is 32-bit float: values above 1 survive until the 8-bit PNG clips them; judge the render, not the viewer.
- **Paste lands only on the current Fusion-page comp; `Execute` is deferred and silent on Lua errors.** Poll, and report through `comp:SetData`.
- **Name collisions rename silently** (`Card_BG` -> `Card_BG_1`), and expression strings are not rewritten: they keep reading the old tools. Check names before pasting.
- **UserControl IDs must not equal a built-in input ID** of the host (they override it).
- **Handles: absolute in `.setting`, relative in Python.** A relative handle in a file makes a curve that overshoots backwards in time or goes flat.
- **Text+ Write On IDs are `Start`/`End`.** Follower text lives in the Follower's `Text`; setting Text+ `StyledText` does nothing while a Follower is wired. Follower values act only when keyed.
- **Expression semantics:** radians, `time` in frames, `noise()` unavailable (input goes nil), `SetExpression("")` leaves the input at 0. Frame-rate literals (`time/24`) must match the timeline.
- **Merge `Background` sets output resolution;** a Merge with no Background outputs nothing. Background and Text+ outputs are premultiplied; a bright fringe means a straight foreground somewhere.
- **Generators need `UseFrameFormatSettings` 1** (set explicitly in authored text) or they keep an authored size in a UHD timeline.
- **Non-Latin copy and emoji:** write the file as UTF-8 and check those strings on the render; if they break, set them with `SetInput("StyledText", ...)` from Python after the paste.
- **Only the first MediaOut feeds the timeline.** Do not paste a MediaOut into an item comp that already has `MediaOut1`; connect `MediaOut1.Input` from Python.

---

## 10. Color discipline

- **Measure the reference swatch, do not guess** (§2 pixel probe). Author hex, convert with `/255`, 4 decimals.
- **UI accents are muted:** HSL **S 40-65 %, L 45-60 %**. #4F5BD5 (S 61, L 57) reads premium; #5B6CF0 (S 83) already looks like a debug color. Over-saturation is the most common reason a faithful layout looks cheap.
- **Text contrast at least 4.5:1** on its plate; secondary text uses a desaturated tint of the ink, not gray-on-gray.
- **Dark surfaces:** keep background, card and border within about 6-10 % L of each other and separate them with shadow and a soft glow, not with saturated fills.
- **Glows are tints of the accent at 10-35 % strength** through Screen, never the full accent.
- **Nothing is color managed by default.** With RCM off, a hex/255 value renders as that hex in an 8-bit PNG. If Resolve Color Management puts the Fusion page in a linear working space, convert sRGB hex to linear first (`c <= 0.04045 ? c/12.92 : ((c+0.055)/1.055)^2.4`) or plates render too light. Verify one swatch pixel per build either way (unverified behavior per project setting).
- **One palette lives on `Ctrl_Main`.** Plates and text read it by expression, so a rebrand is three color pickers. Gradients (BG, glow) cannot take per-stop expressions: note their hex beside the controller values and update them together.

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `fmd_paste` stays `"pending"`, nothing created | Comp not current, or Edit page showing | `SetCurrentTimecode` inside the item, `OpenPage("fusion")`, wait 1.5 s, re-get `GetCurrentComp()`; test with `cc.Execute("comp:SetData('ping','pong')")` |
| `fmd_paste` = `"ERR readfile nil..."` | Lua table syntax error (missing comma or brace, unbracketed dotted key, unescaped quote) | Bracket dotted keys `["A.B"]`, check braces; paste a halved file to bisect |
| `fmd_paste` = `"false"` | Paste refused (non-current comp) | As row 1 |
| Tools named `X_1`, expressions read wrong values | Name collision | Delete the old set by prefix (tools and splines), or use a fresh item; re-paste |
| `in_target_item` False | Pasted into whatever comp was open | Make the intended item current first; delete the stray set |
| Probe returns `None` | Expression error: unknown tool/control name, `noise()`, degrees assumption, typo | `GetExpression()`, retype in Inspector with `=`, fix the source |
| Everything static, entrances missing | Rendered at frame 0, or `AnimStart` beyond the render frame, or a master curve not connected to its UserControl | Probe `Ctrl_Main.AnimMove` at 2; render at 18 and 48 |
| Easing looks linear | `Flags = { Linear = true }` left on keys, or handles on the straight line | Rewrite handles per §3.6 |
| Easing runs backward or kinks | Relative handles written into `.setting` | Convert to absolute (`S + x*D`, `v0 + y*V`) |
| CTA pop has no overshoot | `RH` y written as 1 instead of `v0 + 1.56*V` | Recompute; probe Size at start+6 > 1 |
| Headline shows no cascade | Follower values not keyed, text set on Text+, ligatures on, or Delay/DelayType mismatch | Key Opacity1; text in Follower `Text`; read DelayType label (§3.7) |
| Headline cascade takes seconds | DelayType is "Between Each Character" with a large Delay | Delay 0.5 f/char or total spread <= 14 f |
| Card is the wrong shape or size | Pixels in Width/Height, or ellipse convention used for a rect | RectangleMask per-axis fractions; CornerRadius = r/(min(w,h)/2) |
| Card scales from the wrong point | `Pivot` left at frame center for an off-center unit | Set `_Xf.Pivot` to the unit center |
| Text far too large/small | Size treated as points | `Size = 1.70 x px / W` (Open Sans); calibrate other fonts once |
| Card shadow invisible or huge | `ShadowOffset` treated as an absolute offset, `Softness` beyond 0.05 | Offset = point minus {0.5,0.5}; Softness 0.01-0.03; or use the soft-mask shadow (§3.8) |
| Bright fringe on card corners | Straight alpha reaching a Merge | Keep Background+mask (premultiplied); check any imported PNG's premult |
| Output black in the timeline | `MediaOut1` not connected, or connected to a tool with no Background chain | `mo.ConnectInput("Input", Card_Mrg)` and read back |
| Render True but no PNG | Wrong `Clip` path or format | Absolute path to an existing dir, `FormatID` "PNGFormat" + `OutputFormat` FuID; files are `name_0048.png` |
| Colors off by a constant | RCM linear working space | Convert hex to the working space (§10) |
| UserControl missing in Inspector | Entry lacks `LINKID_DataType` or `INPID_InputControl`, or collides with a built-in ID | Fix entry; prefix IDs |
| OGrafLoader renders nothing | Outside Global In/Out, single-step template without Stop before Play, unsupported file type | Check range; add Stop then Play; confirm `.lottie`/OGraf manifest |
| Lottie plays too fast/slow | Source `fr` differs from the timeline | `TimeScale` = source fps / timeline fps (or retime by translation, §8.3) |

---

## 12. Don'ts

- Don't rebuild with incremental calls what one paste produces, and don't re-paste over an existing build (collisions).
- Don't paste into a client project or into whatever comp happens to be open; guard the project name and verify `in_target_item`.
- Don't treat `comp.Execute` as synchronous or assume silence means success.
- Don't write pixels into `Center`, `Width`, `Height` or `Size`; normalize and flip Y.
- Don't write relative handles into `.setting` text or absolute handles into `SetKeyFrames`.
- Don't hand-key entrances after a paste; put them in the spec (master curves + offsets or baked splines) and re-paste.
- Don't add nodes, keys or effects the spec could have expressed; fix the spec.
- Don't put a MediaOut or a Saver in a template meant for the Edit page; QA Savers are `QA_*` and get deleted.
- Don't invent input IDs; grep the TSV. Don't guess Combo indices (Follower `Order`/`DelayType`); read the labels.
- Don't hand-build icons from rectangles or invent glyph paths; use an icon font in Text+ or converted real path data.
- Don't bake copy into an image or an OGraf/Lottie asset when the editor may need to change it.
- Don't author neon accents; measure and keep S 40-65 %, L 45-60 %.
- Don't render at frame 0, and don't pass image arrays to a vision check; composite one side-by-side.

---

## 13. Unverified IDs and semantics (resolve in the verification pass)

All tool and input IDs used above exist in `fusion-21.1-inputs.tsv` or the 21.1 registry, except where noted. Open semantics:

1. Follower `Order` and `DelayType` index-to-label mapping (live defaults 7 and 1); Follower `CharacterOffset` units (-0.02 chosen to be harmless either way).
   **Resolved live 2026-09-26:** Order 0 L->R, 1 R->L, 2 Inside out, 3 Outside in, 4 Random one by one, 5 Completely random, 6 Manual curve, 7 Automatic (default, L->R); DelayType 0 None, 1 Between each character, 2 Between first and last. `CharacterOffset` Y -0.02 visibly drops characters below the baseline and they rise into place (render f18/f24).
2. UserControls on a plain Background controller, splines driving UserControls, and `Ctrl_Main:GetValue('<UserControl>', t)` on them (the pattern is verified for built-in inputs and for group-level controls).
   **Resolved live 2026-09-26: works** (probes above). Pasted splines on UserControls are renamed `<Tool><LINKS_Name stripped>`.
3. `Shadow` `ShadowOffset` meaning (default {0.5,0.5} read as zero offset) and `Softness` scale.
4. Transform `Pivot` scaling without shifting the image.
   **Live 2026-09-26:** the CTA pop scales about its own center (pill position identical at f24 and f48).
5. XYPath output equals (X, Y) with default `Center`/`Size`/`Angle`.
6. Open Sans "Regular" style name; `CharacterSpacing` to CSS `letter-spacing` mapping.
   **Live 2026-09-26:** `Style "Regular"` renders the regular weight (subline). Spacing mapping not measured.
7. `OGrafLoader` `TemplatePath` set from text or `SetInput`; plain Lottie `.json` support.
8. `comp:AddSettingAction` as a paste alternative on non-current comps; `Render` `proxy` effect on Saver output.
9. Lottie/AE rotation sign in Fusion (negate assumed); Step In/Out hold semantics.
10. Color management behavior under RCM for hex-authored values; emoji and non-Latin strings through `bmd.readfile`.
