<!-- design-first.md part 1 of 3; index: design-first.md -->
# Fusion design-first: author the whole frame once (`.setting` scene build)

Port of Higgsfield `ae-design-first` (HTML -> scene with a `data-anim` contract, plus Lottie -> native scene) to the DaVinci Resolve 21.1 Fusion page. **Load when** a whole frame or multi-unit layout (SaaS hero, title card, stat card, lower third, dashboard panel) should land in one paste instead of dozens of `AddTool`/`SetInput` calls, when the build needs UserControls, modifiers, splines and expressions that the Python API sets awkwardly, or when an OGraf/Lottie file must come in as an asset. Companions: `fusion-reference/references/fusion-realities.md` (live API facts, units), `setting-format.md` (grammar, idioms), the clean-rig and orchestration modules (incremental route, surgical edits).

Assumptions: reference frame 1920x1080 (all values normalized, so they hold at 3840x2160); 24 fps primary with 30 fps columns; Resolve Studio 21.1.0.14. Items marked **[live]** were observed on 2026-09-26. **The §4 template: status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frames 0, 6, 12, 18, 24, 32, 48).** Other recipes: unverified (not yet rendered).

---

## 0. What transfers, what changes

| AE design-first | Fusion equivalent | Note |
|---|---|---|
| `ae_build_scene_from_html(html)`, one call | Write the graph as `.setting` Lua-table text, then `comp.Execute('comp:Paste(bmd.readfile([[path]]))')` **[live]** | No DOM walk. The text IS the graph: exact names, wires, keys, expressions |
| `ae_html_to_spec` (inspect only) | Dry run: list tool names, check collisions, `bmd.readfile` returns non-nil; paste into a scratch Fusion Composition item first | |
| `usePrecomps` + hint class names | **Unit contract** (§3.2): every 2+ node unit ends in one `<Unit>_Xf` Transform and enters its parent through one `<Unit>_Mrg`; shared name prefix | Nothing auto-groups; you write it. GroupOperator wrapper optional |
| `data-anim` / `-delay` / `-dur` / `-stagger` | Master eased curves on the controller + per-unit time-offset expressions (§3.6), or baked BezierSplines with absolute handles | Retime a whole frame with two sliders |
| `userText` mood keywords | No NLP. Pick verbs from the preset table (§3.6) | |
| Gradient Ramp, 2 stops | Background `Type` "Gradient", any stop count, `GradientType` Linear/Radial/Angle/..., `GradientInterpolationMethod` LAB | Fusion is better here |
| `box-shadow` -> Drop Shadow | `Shadow` tool, or a soft `RectangleMask` copy (`SoftEdge`) on a black Background | |
| Text -> editable text layers | Text+ (`TextPlus`) | |
| Lottie -> native layers | No converter. Translate keys into `.setting` by table (§8.3), or load the file with `OGrafLoader` as an asset (§8) | Fusion keeps Lottie easing exactly, overshoot included |
| Result envelope `{success, errors}` | Healthy-paste checklist (§5.2) | |
| Auto-glow sweep on saturated plates | Not needed: a paste adds nothing you did not write | |
| "Restart AE" for a stale engine | Make the comp current on the Fusion page; treat `Execute` as deferred | §11 |

---

## 1. When the one-call route beats incremental calls

| Situation | Route | Why |
|---|---|---|
| New frame, 5+ tools, layout known | **Paste** | One write, one paste. No auto-connect trap (fusion-realities §5), wiring exact, names exact |
| Needs UserControls, controller, macro/group, published inputs | **Paste** | UserControls are table entries; the Python API has no clean way to add them |
| Needs splines with precise easing, modifiers (Follower, XYPath) | **Paste** | Absolute handles written once; no `AddModifier` return-value ambiguity or orphan modifiers |
| Edit-page template (Title/Generator/Effect) | **Paste**, then save the same text into `Templates/Edit/<Category>` | A template is a `.setting` anyway |
| Reproducible, diffable, re-pasteable build | **Paste** | The text is the source of truth (AE's `design.html`) |
| Change one value, retime a key, recolor | **Incremental** (`SetInput`, `SetKeyFrames`, `SetExpression`) | Re-pasting duplicates tools (`_1` renames) and breaks expression links |
| Target comp is not current and switching page/playhead would disturb the user's session | **Incremental** | `AddTool`/`SetInput`/`ConnectInput`/`AddModifier`/`SetExpression`/`Render` work on non-current item comps **[live]**; `Paste` does not |
| Values depend on live state (text bounds, media size, tracker output) | **Incremental** or an expression (`Text1.Output[0].DataWindow`) | Read first, then set |
| Unknown serialized form (OFX params, Krokodove inputs) | **Incremental** once, then `comp:CopySettings` in Lua to learn the text | Never invent input IDs |
| 1-3 tools on a non-current comp | **Incremental** | File + poll overhead not worth it |

**Commit to one path per build.** Paste the structure once; tune values with `SetInput`; write every tuned value back into the `.setting` source. For a structural change, edit the source, delete the old unit set by name prefix, re-paste. Never interleave hand-added nodes with a pasted build.

**UI side effect.** Paste needs the comp current on the Fusion page, which means `OpenPage("fusion")` and moving the playhead. Do it only in a scratch project the user opened for this, and say so. Route B (`pbcopy` + `cc.Paste()`) also clobbers the clipboard: save with `pbpaste` and restore. `comp:AddSettingAction(filename, x, y)` exists in the 21.1 stub and might paste into a non-current comp: unverified, test before relying on it.

---

## 2. Reference intake: measure, then author

If the request has a visual reference (image, screenshot of a site, Figma frame), measure before writing a single value.

- **Ask vision for fractions (0-1), not pixels.** Fusion consumes fractions directly: `Center.X = fx`, `Center.Y = 1 - fy` (fy measured from top), `RectangleMask Width = fw`, `Height = fh` (each axis against its own frame dimension **[live]**). Only three values need pixels: `EllipseMask` Height (`= fh*H/W`, both axes width-relative **[live]**), `CornerRadius` (`= r_px / (min(w_px,h_px)/2)` **[live]**), Text+ `Size` (`~= 1.70 * font_px / W`, Open Sans **[live]**; other fonts: calibrate by render).
- **Sample exact colors from pixels**, never name them by eye: `ffmpeg -v error -i ref.png -vf "crop=1:1:X:Y" -frames:v 1 -f rawvideo -pix_fmt rgb24 - | xxd -p` gives the RGB bytes; divide by 255.
- **Inventory** every element with a semantic name (plate, headline, subline, CTA, icon names) before writing the spec.
- **Close the loop after the render (numbers, then eyes):** probe the same points in the render and the reference (flat plates within 4/255 per channel), then make ONE side-by-side image per compare round and look once:
  `ffmpeg -v error -i ref.png -i render.png -filter_complex "[0]scale=960:-2[a];[1]scale=960:-2[b];[a][b]hstack" -y cmp.png`. One image in, one verdict out; do not pass image arrays to a vision tool.
- In-comp overlay alternative: bring the reference in as a MediaIn from the Media Pool, merge over the output at `Blend` 0.5 in a `QA_Ref_Mrg`, delete before delivery.
- **Record the comparison frame of reference.** Note the reference crop/viewport and, for video
  references, the sampled frame indices and timestamps (02 frame evidence) so every later compare
  uses the same view and time.

**Pipeline order (local Higgsfield connector revision, 2026-09-26):** scene spec -> TSV lookup of
every tool and input -> one representative unit pasted and rendered as a still -> assemble the
remaining units -> motion. Resolve the static design (aspect, safe areas, baseline grid, dominant
blocks, wrapping, contrast, Merge order) before investing in motion, and fix composition-level
hierarchy before decorative detail. After motion is added, render again: keyed masks, `Pivot`s
and DataWindow-driven expressions can break a layout that was correct as a still. Do not claim
pixel equivalence before comparing the native render against the reference.

---

## 3. Scene spec -> `.setting`: the authoring contract

### 3.1 Write a spec first (the HTML analog)

A flat, pixel-space spec is easy to reason about and converts mechanically (helpers in §6). Pixel values use a top-left origin like CSS; conversion flips Y.

```python
SPEC = {
  "frame": {"W": 1920, "H": 1080, "fps": 24},
  "ctrl":  {"start": 4, "stagger": 3, "rise_px": 32,
            "accent": "#4F5BD5", "ink": "#F2F4FA", "card": "#1E2640"},
  "units": [   # reading order = k index for stagger
    {"name": "Card", "kind": "plate", "box": [400, 310, 1120, 460], "radius": 28,
     "fill": "@card", "shadow": True, "enter": "fadeUp", "k": 0},
    {"name": "Card_Headline", "kind": "text", "parent": "Card", "text": "Ship your launch in minutes",
     "center": [960, 455], "px": 56, "font": ["Open Sans", "Bold"], "fill": "@ink", "enter": "charRise", "k": 2},
    {"name": "Card_Subline", "kind": "text", "parent": "Card",
     "text": "Automations, analytics and approvals in one place.",
     "center": [960, 520], "px": 28, "font": ["Open Sans", "Regular"], "fill": "#A7AFC4", "enter": "fadeUp", "k": 3},
    {"name": "Card_CTA", "kind": "pill", "parent": "Card", "box": [800, 579, 320, 72], "radius": "pill",
     "fill": "@accent", "label": "Start free trial", "label_px": 24, "enter": "chipBounce", "k": 4},
  ],
}
```

Put EVERYTHING visible in the spec: plates, gradients, real copy, icons, shadows. The spec plus the `.setting` generated from it is the single source of truth for the frame.

### 3.2 Unit contract (the precomp rule, Fusion form)

**House rule: any unit of 2+ nodes (plate + text is already a unit) ends in exactly one unit-head Transform `<Unit>_Xf` and joins its parent through exactly one Merge `<Unit>_Mrg`.** Children merge onto the unit's own plate first, so the unit moves, scales and fades as one piece.

- `<Unit>_Xf` carries group motion (`Center`, `Size`, `Angle`). Set its `Pivot` to the unit's center (AE: anchor at the precomp's center), otherwise scale-ins grow from the frame center.
- `<Unit>_Mrg` carries the unit's opacity (`Blend`) and its stacking position (Background = everything under it).
- Masks shape the plate BEFORE the unit Transform (mask on the plate's `EffectMask`) so the rounded rect travels with the unit. A mask on a Merge's `EffectMask` stays in frame space.
- A single-node unit (lone text line) may skip `_Xf` and animate its Merge `Center` (Point offset, default {0.5,0.5}) and `Blend`.
- Optional: wrap a finished unit in a `GroupOperator` for a tidy node view. The `_Xf` is the motion handle either way; expressions still address inner tools by name.

### 3.3 Naming convention

Pattern `<Unit>[_<Sub>]_<Role>`, alphanumerics and underscore, no spaces, no leading digit (invalid characters are stripped silently and expressions then miss). One shared prefix per unit lets you select, delete and re-paste a unit by prefix.

| Role suffix | Node | Example |
|---|---|---|
| `_BG` | plate generator (Background) | `Card_BG`, `Card_Price_BG` |
| `_Mask` | its RectangleMask/EllipseMask/PolylineMask | `Card_BG_Mask`, `Card_CTA_Mask` |
| `_Shadow`, `_Glow` | effect on the plate | `Card_Shadow` |
| role word | Text+ named by its job | `Card_Headline`, `Card_Subline`, `Card_CTA_Label` |
| `_Flw` | Follower on that text | `Card_Headline_Flw` |
| `_Xf` | unit-head Transform | `Card_Xf`, `Card_CTA_Xf` |
| `_Mrg` | Merge that brings THIS node or unit onto what is below | `Card_Headline_Mrg`, `Card_CTA_Mrg`, `Card_Mrg` |
| `<Tool><InputID>` | spline/modifier (Fusion's own convention) | `Ctrl_MainAnimMove`, `Card_Headline_FlwOpacity1` |
| `Ctrl_Main` | the controller | |
| `QA_*` | verification-only nodes, deleted before delivery | `QA_Saver`, `QA_Ref_Mrg` |

### 3.4 Node layout grid (readable graph)

- Data flows left to right; x step **110** per stage in flow order.
- The trunk (background -> unit merges -> output) is the top row, y = 0.
- Each unit gets its own horizontal band below the trunk (y = 115.5, 231, ...; about 66 to 115 apart); its text/generators sit one half-band lower (+49.5) under the Merge they feed.
- The unit head `_Xf` sits at the right end of its band, directly under or left of the trunk Merge it feeds.
- Controller top-left (x = -165, y = -66) with a tile color; QA nodes right of the trunk output.
- Modifiers and splines have no `ViewInfo` (they do not appear as nodes).

### 3.5 Controller contract (`Ctrl_Main`)

One unconnected tool holds every shared value as UserControls; everything else reads it by expression. A tool that is never connected downstream is never rendered, but its inputs still evaluate when referenced (inference; confirmed indirectly by the template probes in §5).

| UserControl ID | Type | Default | Used by |
|---|---|---|---|
| `AnimStart` | Slider, frames | 4 (24 fps) / 5 (30 fps) | every unit's time offset |
| `AnimStagger` | Slider, frames | 3 / 4 | `k * AnimStagger` per unit |
| `AnimRise` | Slider, fraction of H | 0.03 (32 px at 1080) | fadeUp distance |
| `AnimMove`, `AnimFade`, `AnimPop` | Slider 0-1, **driven by keyed BezierSplines** | curves in §3.6 | the master eased curves |
| `Accent*`, `Ink*`, `Card*` (Red/Green/Blue) | ColorControl group (header with `IC_ControlID = -1`, then 0/1/2) | measured hex /255 | plate and text colors |

Rules: never give a UserControl the ID of a built-in input of the host tool (a same-ID UserControl overrides the built-in: `Start`, `End`, `Offset` exist on Background). Prefix controls (`Anim*`, `Accent*`). The host here is a Background (cheap, has no required inputs); any tool can carry UserControls.

### 3.6 Entrance contract (the `data-anim` equivalent)

Two equivalent encodings. Prefer **A** for components; use **B** where a modifier needs its own keys (Follower) or a single element needs a unique curve.

**A. Master curve + time offset (controller-driven).** Author each eased curve ONCE on `Ctrl_Main` as a normalized 0 -> 1 BezierSpline starting at frame 0. Every animated input reads it at its own delay:

```
p   = Ctrl_Main:GetValue('AnimMove', time - (Ctrl_Main.AnimStart + k*Ctrl_Main.AnimStagger))
out = from + (to - from) * p
```

Before its start `GetValue` returns the first key (0), after the end the last key (1). `time` is in frames and cross-frame `:GetValue(...)` works in SimpleExpressions **[live]**. Retiming the whole frame = edit `AnimStart`/`AnimStagger`; changing the feel = edit one curve.

**B. Baked BezierSpline per input.** Keys at absolute frames with absolute handles (the `.setting` form).

**Handle math.** For cubic-bezier(x1, y1, x2, y2), start frame S, duration D, values v0 -> v1, V = v1 - v0:

| Form | Right handle of first key | Left handle of last key |
|---|---|---|
| Python `SetKeyFrames` (relative) **[live]** | `RH = {x1*D, y1*V}` | `LH = {(x2-1)*D, (y2-1)*V}` |
| `.setting` (absolute) | `RH = {S + x1*D, v0 + y1*V}` | `LH = {S + x2*D, v0 + y2*V}` |

Both absolute handles are simply "start plus fraction of the segment". Never write relative handles into a `.setting` or absolute handles into Python.

**Curves.**

| Name | cubic-bezier | Use | Source |
|---|---|---|---|
| `settle` | 0.22, 0, 0.25, 1 | position/scale settle, counters | AE house in22/out75 (Lottie `o.x 0.22`, `i.x 0.25`) |
| `decel` | 0.22, 1, 0.36, 1 | entrances that should arrive soft (easeOutQuint) | web standard |
| `snap` | 0.16, 1, 0.30, 1 | punchier entrances (easeOutExpo) | optional taste |
| `fade` | 0.33, 1, 0.68, 1 | opacity (easeOutCubic) | |
| `pop` | 0.34, 1.56, 0.64, 1 | chips, buttons, badges (easeOutBack, peak ~1.10 of the change) | Fusion keeps the overshoot exactly; AE's Lottie path could not |
| `smooth` | 1/3, 0, 2/3, 1 | AE Easy Ease | handles at thirds, flat |
| linear | omit handles, or `Flags = { Linear = true }` | typewriter, drifts | |

**Duration tokens** (Figma Motion tokens map straight in; round to whole frames, fractional keys are legal but whole frames read better):

| Token | Seconds | 24 fps | 30 fps | Use |
|---|---|---|---|---|
| fast | 0.15 | 4 | 5 | chips, icons, fade on buttons |
| base | 0.25 | 6 | 8 | opacity, rows, cards' fade |
| slow | 0.40 | 10 | 12 | pops, scale-ins, per-char offset |
| hero | 0.60 | 14 | 18 | card/headline moves |
| stagger (units) | 0.125 | 3 | 4 | between semantic units |
| stagger (rows, AE 0.06) | 0.06 | 1.5 | 2 | list rows; Follower per-char 0.5-1 |

**Ready keys, normalized 0 -> 1, S = 0 (paste into a master curve; for B shift x by S and scale y as `v0 + y*V`):**

| Curve / token | 24 fps | 30 fps |
|---|---|---|
| decel / hero (Move) | `[0]={0,RH={3.08,1}}, [14]={1,LH={5.04,1}}` | `[0]={0,RH={3.96,1}}, [18]={1,LH={6.48,1}}` |
| decel / slow | `[0]={0,RH={2.2,1}}, [10]={1,LH={3.6,1}}` | `[0]={0,RH={2.64,1}}, [12]={1,LH={4.32,1}}` |
| fade / base (Fade) | `[0]={0,RH={1.98,1}}, [6]={1,LH={4.08,1}}` | `[0]={0,RH={2.64,1}}, [8]={1,LH={5.44,1}}` |
| fade / fast | `[0]={0,RH={1.32,1}}, [4]={1,LH={2.72,1}}` | `[0]={0,RH={1.65,1}}, [5]={1,LH={3.4,1}}` |
| pop / slow (Pop) | `[0]={0,RH={3.4,1.56}}, [10]={1,LH={6.4,1}}` | `[0]={0,RH={4.08,1.56}}, [12]={1,LH={7.68,1}}` |
| settle / slow | `[0]={0,RH={2.2,0}}, [10]={1,LH={2.5,1}}` | `[0]={0,RH={2.64,0}}, [12]={1,LH={3,1}}` |
| snap / hero | `[0]={0,RH={2.24,1}}, [14]={1,LH={4.2,1}}` | `[0]={0,RH={2.88,1}}, [18]={1,LH={5.4,1}}` |

Sanity values (computed from the curves, use them as probes): decel/hero at 24 fps gives 0.534 at frame 2, 0.815 at 4, 0.979 at 8; fade/base gives 0.422 at 1, 0.961 at 4; pop/slow mapped 0.8 -> 1 peaks at 1.019 around frames 5-6.

Worked baked example (B, fadeUp rise of a Point through an XYPath Y spline, S = 4, 24 fps, 0.47 -> 0.5): `.setting` `[4] = { 0.47, RH = { 7.08, 0.5 } }, [18] = { 0.5, LH = { 9.04, 0.5 } }`; Python `{4: {1: 0.47, "RH": {1: 3.08, 2: 0.03}}, 18: {1: 0.5, "LH": {1: -8.96, 2: 0.0}}}`.

**Preset verbs** (AE `data-anim` -> Fusion channels):

| Verb | Channels | From -> to | Curve / token | Notes |
|---|---|---|---|---|
| `fadeIn` | `<Unit>_Mrg.Blend` | 0 -> 1 | fade / base | |
| `fadeUp` | `_Mrg.Blend` + `_Xf.Center` (or `_Mrg.Center` for one-node units) | Blend 0 -> 1; y0 - Rise -> y0 | fade/base + decel/hero | Rise 24-40 px = 0.022-0.037 of H; text lines use 0.6 x Rise |
| `slideIn` | `_Xf.Center` X + Blend | x0 - 0.042 -> x0 (80 px at 1920) | decel/hero + fade/base | slide from reading direction |
| `scaleIn` | `_Xf.Size` + Blend | 0.92 -> 1 | settle/slow + fade/fast | `_Xf.Pivot` = unit center |
| `chipBounce` | `_Xf.Size` + Blend | 0.6 (chips) or 0.8 (buttons) -> 1 | pop/slow + fade/fast | overshoot lives in the RH handle (y 1.56) |
| `count` | Ctrl `CountValue` keyed 0 -> N; Text+ `StyledText` expression `Text(math.floor(Ctrl_Main.CountValue + 0.5) .. "")` | 0 -> N | settle, 1.2 s (29 f / 36 f) | alternatives: `TextTimer`, `KD_TextFormula` modifiers |
| `typeOn` | Text+ `End` (UI "Write On End") | 0 -> 1 | linear, 1 f per char at 24 | TSV IDs are `Start`/`End`, not `WriteOnStart`/`WriteOnEnd` |
| `charRise` (kinetic) | Follower `Opacity1` + `CharacterOffset` (via XYPath Y) | 0 -> 1; -0.02 -> 0 | fade/base + decel/slow | Follower `Delay` 0.5 f/char |
| `drawOn` (trimPath) | mask `WriteLength` with `Solid` 0 | 0 -> 1 | settle/slow | RectangleMask/PolylineMask outline draw-on |
| `chartGrow` | `_Xf` with `UseSizeAndAspect` 0, `YSize` 0 -> 1, `Pivot` at bar base | 0 -> 1 | decel/hero | stagger bars by k |

### 3.7 Stagger

- **Components: time offsets.** Unit index k in reading order (plate 0, eyebrow 1, headline 2, subline 3, CTA 4, footnote 5). Default `AnimStagger` 3 f at 24 (0.125 s): each unit starts when the previous is about 20 % into its 14 f move, which reads as one cascade, not a queue.
- **Text: Follower (`StyledTextFollower`).** The text lives in the Follower's `Text` input; Text+ `StyledText` is wired to the Follower's `StyledText` output. Follower values only act when KEYED (a static change is invisible). Each character replays the Follower's key curve shifted by `Delay`. Spaces count as characters. Keep the total spread at or under 0.6 s: `Delay ~= min(1, 14 / (chars - 1))` at 24 fps (use 18 at 30). Leave Text+ `UseLigatures` at its default ("None for Latin" per the manual) so letters animate separately.
- **Follower `Order` and `DelayType` are numeric Combos whose index mapping is unverified** (live default `Order` = 7 while the manual lists 7 labels; `DelayType` default 1). Leave them at default in authored text, then read the labels in the Inspector: you want "Left to right" and "Between Each Character" (Delay = frames per char). If DelayType reads "Between First and Last Character", Delay is the total spread instead: set it to about 13.
- Rows of a list: either k-offsets per row unit, or one Text+ with line-level Follower transforms (`LineOffset`, `LineSizeY`) keyed once.

### 3.8 What maps to what (author-the-whole-frame mandate)

| Web/spec construct | Fusion build | Status |
|---|---|---|
| solid fill | Background (`TopLeftRed/Green/Blue/Alpha`) + mask on `EffectMask` | |
| linear/radial gradient, any stops | Background `Type` "Gradient", `GradientType` "Linear"/"Radial"/"Angle"/..., `Start`/`End` points, `Gradient { Colors = { [pos] = {r,g,b,a} } }` | IDs in TSV |
| `border-radius` (uniform) | RectangleMask `CornerRadius` = r / (min(w,h)/2); 1.0 = pill | **[live]** formula |
| per-corner radii | PolylineMask with explicit points | build by points |
| `box-shadow` | `Shadow` tool (`ShadowOffset` point, `Softness` 0-0.05, `Alpha`), or black Background masked by a copy of the rect with `SoftEdge` and offset `Center`, merged under | Shadow semantics unverified |
| `opacity` | Merge `Blend` | |
| `filter: blur()` | `Blur` `XBlurSize` (not pixels; calibrate) | |
| 1 px border | second RectangleMask, `Solid` 0, `BorderWidth` | |
| `mix-blend-mode: screen` | Merge `ApplyMode` "Screen" | |
| `letter-spacing` | Text+ `CharacterSpacing` (1 = normal; -0.02 em ~ 0.98, calibrate) | mapping unverified |
| font size/weight/color | Text+ `Size` (1.70 x px / W), `Font`, `Style`, `Red1/Green1/Blue1` | Size **[live]** for Open Sans |
| `<img>`, photos, logos | MediaIn from the Media Pool (Loader is EXR-oriented in Resolve) | |
| icons | (1) icon font glyph in Text+ (install the font, e.g. Lucide's `lucide.ttf`; editable, recolorable, Follower-animatable); (2) SVG path converted to PolylineMask/sPolygon points (center-relative, Y flipped; flatten booleans, strip masks/clipPaths, flatten groups first); (3) PNG via MediaIn as last resort | No native SVG importer is documented in the manual distillations; font availability unverified |
| texture (dot grid, hatch) | sShapes + `sGrid`/`sDuplicate` -> `sRender` as a mask, or `FastNoise` | |
| emoji | Resolve 21 adds emoji/color-font support to Text+ (feature list) | verify by render; AE's "no emoji" rule may not apply |

After a successful paste you may only tweak existing nodes (values, keys, colors) and must write those tweaks back to the source. Never hand-add a node, key or effect the spec could have expressed; fix the spec and re-paste.

---

