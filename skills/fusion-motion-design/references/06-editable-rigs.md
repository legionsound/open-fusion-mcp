# 06 Practical editability and exposed controls

Load when packaging semantic objects, making elements replaceable, building a controller, exposing controls to the Edit page, or deciding what is shared versus independent. AE precomps map to named subgraphs/Groups/macros; null + Expression Controls map to a controller tool with UserControls; Essential Properties map to macro published inputs (`InstanceInput`) shown in the Edit-page Inspector.

## Fusion's sharing model is the opposite of AE's

In AE, duplicating a precomp layer shares its source. In Fusion, copy/paste makes independent deep copies. Sharing is explicit and must be chosen:

| Want | Fusion mechanism |
|---|---|
| Several consumers of one source (same word, same photo) | Fan-out: one tool's output wired to many inputs |
| Copies that stay in sync except a few parameters | Paste Instance (`Instance_X` with tool-level `SourceOp`); per-parameter Deinstance for the differences, Reinstance to relink |
| One value driving many parameters | SimpleExpression reading `CTRL.<ID>`, or Publish + Connect To (bidirectional) |
| Independent sets (card A vs card B) | Plain copies, each with its own MEDIA tool |

Test the choice: replace one item and check that the other did (or did not) change as intended.

## Make normal edits practical

Native nodes alone do not establish editability. Give each meaningful component a clear, named source for wording (`TextPlus.StyledText`, or the Follower's `Text` when a Follower is attached), color (one controller color group), geometry (controller numbers) and replaceable media (`MEDIA_<name>`, 05). Link construction copies of one word to one source. Keep independently meaningful elements individually selectable.

Where content changes affect layout, make bounds, cursors, anchors, padding and media fit follow content. Corpus idiom (built-in `Text Box.setting`) sizes a box from rendered text bounds:

```lua
Width  = Input { Expression = "(Label.Output[0].DataWindow[3]-Label.Output[0].DataWindow[1])/Label.Output[0].Width + CTRL.PadX", },
Height = Input { Expression = "(Label.Output[0].DataWindow[4]-Label.Output[0].DataWindow[2])/Label.Output[0].Height + CTRL.PadY", },
```
Preserve deliberate framing and motion when adding automatic fitting.

Before delivery, test a real edit in a temporary duplicate (or on the item with a noted restore): a longer word, a changed color or dimension, a replaced photo. Render during an animated state, confirm dependents still align, then restore the original. Report fixed layouts or baked material that limit editing. A particle field may legitimately contain many simple circles; one object's surface built from traced fragments is not the same thing.

## Separate artwork reuse from playback reuse

A shared source (fan-out, Paste Instance, one Group feeding several shots) can be consumed at
different times. An intro scene may build a character from zero while a later montage samples
the same source expecting the complete pose; giving the source a new entrance then erases most
of the later shot with no error anywhere.

- Before changing a shared source, enumerate its consumers: `tool.Output.GetConnectedInputs()`
  (dict of inputs fed by this output), Paste Instance copies (`Instance_<name>` tools), and any
  expression that names the tool. For each, note retime tools on the way (`TimeSpeed` `Delay`,
  `TimeStretcher` `SourceTime`, MediaIn `ClipTimeStart`) and which source frame it shows.
- Keep the complete pose independently addressable from the entrance: drive the entrance by a
  controller progress (`CTRL.Build` 0..1) and let a pose consumer use a Paste Instance with
  `Build` deinstanced and set to 1, instead of sampling the entrance at a late time.
- Duplicate a small pose library only when two scenes need independent timing or artwork. Keep
  intentional shared palette and artwork links. Do not duplicate every dependency blindly, and
  do not freeze all instances to fix one montage shot. Check every affected consumer at its
  actual visible frames.

## Keep ordinary transforms and content edits working

Put automatic motion on a helper Transform upstream (`OBJ_Auto`) and leave the user-facing
Transform (`OBJ_XF`) free for keys. Chained Transforms concatenate (one resample, realities §13)
and combine like a parent-child pair: `Size` multiplies, `Angle` adds, and the downstream
Transform scales and rotates the upstream offset about its own `Pivot`. [corrected live
2026-09-26] `Center` offsets add only while `OBJ_XF` is at `Size` 1 and `Angle` 0: with `OBJ_Auto`
(Center 0.6, Size 1.5) then `OBJ_XF` (Center 0.55, Size 2) a centered 100 px square landed at x 0.75
(0.5 + 2 x 0.1 + 0.05), not 0.65, at 300 px (1.5 x 2). That is what a user expects from "scale
the whole object", but compute positions with the chain, not by summing offsets. That is the Fusion form of AE's "additive offsets for Position/Rotation, ratios for
Scale", with no expression. Fusion has no parent-compensation step, so AE's "parent before
keying the parent" trap does not exist; the Fusion trap is putting an expression on the input
the user will key (an input holds either a spline or an expression, not both).

When one input must carry both, keep a stored neutral and read the user's raw value from a
separate control: `Center = Point(CTRL.UserX + autoX, CTRL.UserY + autoY)`,
`Size = CTRL.UserSize * autoS`. Use one declared coordinate space and never measure the current
animated bounds to redefine the neutral.

- Test during an automatic pose, not only with demo playback off: move `OBJ_XF` (or the promised
  editable part) by a known amount (`Center` x +0.05), render, confirm the visible shift, restore.
- An expression that writes `StyledText` unconditionally (counters, formatted labels) swallows
  manual text edits. Keep the editable words on a text control (`TextEditControl` UserControl on
  `CTRL`) and read it. [corrected live 2026-09-26] A text UserControl reads as a Text object, not a
  Lua string: `Text(CTRL.Label .. " " .. ...)` evaluates to nil (the expression fails) and
  `Text(CTRL.Label)` prints `cdata<struct Text *>`. Use `.Value` for the string:
  `Text(CTRL.Label.Value .. " " .. string.format("%d", CTRL.Value))` returned "Revenue 42" and followed
  a label edit to "Profit 42"; bare `CTRL.Label` (no concatenation) also works.
- Selection backgrounds and pills follow the visible label's rendered bounds (the DataWindow
  idiom above), including padding and any intentional Text+ `CharacterSpacing`/Transform scale;
  a guide input and the visible label can sit on different Transforms.

## A new aspect ratio is a rebuild, not a crop

Changing the frame format does not restage anything by itself: normalized `Center`s keep their
fractions, Text+ `Size` and sShapes stay width-relative (a 1080-wide portrait frame renders
Size 0.1 text at 56 % of its 1920-wide pixel size), RectangleMask sizes are per-axis, and a
Camera3D keeps its gate. For a new aspect, restage each scene's objects, diagrams, camera and
phrase groups for the new frame, preserving the meaning of axes, comparisons, silhouettes and
connections. Reframing a source photo can be right; cropping a flattened master and delivering it
as the rebuild is an editability regression.

## A usable controller is part of the design

- One controller per rig, named `CTRL` (or `CTRL_<Object>`). Host: a `Custom` tool (RegID `Custom`), not wired into the image path. Its built-in `NumberIn1..8`/`PointIn1..4` were a verified expression source (2026-09-17: `Point(UNIT_CTRL.NumberIn1, UNIT_CTRL.NumberIn2)`); named UserControls are clearer and preferred.
- Controls: `SliderControl`/`ScrewControl` numbers, `CheckboxControl`, `ColorControl` (header + R/G/B/A entries sharing `IC_ControlGroup`, `IC_ControlID` -1/0/1/2/3), `MultiButtonControl`, `LabelControl` with `LBLC_DropDownButton`/`LBLC_NumInputs` to fold advanced groups. Everyday controls first. Put units and range in the label ("Turn lag (frames)"). `INP_MinScale`/`INP_MaxScale` = soft slider range; `INP_MinAllowed`/`INP_MaxAllowed` = hard clamp.
- Everything downstream reads the controller by SimpleExpression (`CTRL.Slide`, `CTRL:GetValue("Look", time - CTRL.Lag)`). Compute shared values once on the controller (an extra user control with an expression) instead of re-evaluating big math in every consumer.
- Manual control must work directly. The user keys the control itself (`CTRL.AddModifier("Slide", "BezierSpline")`). Optional demo playback lives on a separate spline gated by a `Demo` checkbox (default 0): consumers read `CTRL.Slide + CTRL.Demo * CTRL.DemoSlide`. Never hide a time-driven expression on the control the user animates. Preserve existing user keys during cosmetic fixes.
- Shared phase controls drive the parts of one gesture; do not give each sub-part its own unrelated timer.
- Source default vs instance override: a macro's `InstanceInput` `Default` (and the saved template file) is the source; the value on a timeline instance or on a group's published input overrides it. Editing the inner CTRL value can look ineffective when the published input already holds a value. Which wins, and whether re-saving a template updates existing timeline instances, is unverified: test once and state it in the guide. Paste Instance has the same structure: shared unless deinstanced.

## Exposing controls to the Edit page (Essential Properties analog)

1. Group the rig (Cmd-G). Keep `CTRL` inside the group.
2. Publish only the useful controls: `InstanceInput { SourceOp = "CTRL", Source = "Slide", Name = "Slide", Default = 1, Page = "Controls" }`. Order in `Inputs = ordered()` is Inspector order; `ControlGroup` puts several inputs on one row (color); `Type = "Separator"`/`"BeginNest"` structure the panel.
3. Template structure (observed across 358 installed templates): Titles and Generators have no image input; Effects publish `MainInput1` (the clip); Transitions publish `MainInput1` (outgoing, to Background) and `MainInput2` (incoming, to Foreground); output is `MainOutput1`. Built-in templates contain no MediaOut. Generators/Text+/masks inside set `UseFrameFormatSettings = 1` so output follows timeline resolution.
4. Save to `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/<Titles|Generators|Effects|Transitions>/<Vendor>/<Name>.setting` (Macro Editor "Save to", or write the file). Quit and relaunch Resolve before it appears.
5. Duration safety: keyed intros/outros need `KeyStretcherMod` (hold stretches, intro/outro keep length) or `LUTLookup` Anim Curves with `Source` "Duration"; transitions use `Source` "Transition" or `ResolveParameter`.
6. Media drop zones: publish a MediaIn `ClipName` (05).

Alternative: group-level `UserControls` with plain `Input { Value = ... }` entries in the group's own Inputs, read inside by `GroupName.Control` (built-in `Car Paint.setting` pattern).

## Keep the graph readable and portable

- Top level: semantic groups (`CHEST`, `BTN_Primary`, `CARD03`), one controller per rig, camera if relevant, background, output. Inside a group keep body parts, captions and media easy to find; tuck helpers away without hiding controls the user needs. Use Underlay boxes, node colors and a `Note` tool with the control guide.
- Names are identities: expressions and `SourceOp` resolve by name file-wide, and modifiers may live outside their group. Keep names unique and semantic. Read back names after `SetAttrs` (invalid characters are stripped).
- A group that references tools outside itself by name is not portable. Keep references inside the group or on published inputs. Test by pasting the group into a blank comp and rendering.
- Package any shared motion library tool (08) inside the group or document it as a dependency; do not rely on a name reference to another comp or project.

## Recipe C1: controller with named controls (status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frame 0): pasted as typed; `CTRL` exposes `Slide`, `Demo`, `Accent`, `AccentRed/Green/Blue` as real inputs; `CTRL.SetInput("AccentRed", 0.9)` changed the consumer `BTN_Fill.TopLeftRed` expression to 0.9. Inspector layout not inspected (UI))

```lua
{ Tools = ordered() {
  CTRL = Custom {
    Inputs = { Slide = Input { Value = 1, }, Demo = Input { Value = 0, },
               AccentRed = Input { Value = 0.16, }, AccentGreen = Input { Value = 0.47, }, AccentBlue = Input { Value = 1, }, },
    ViewInfo = OperatorInfo { Pos = { 0, -150 } },
    UserControls = ordered() {
      Slide = { LINKS_Name = "Slide (1 = first card)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl",
                INP_Default = 1, INP_MinScale = 1, INP_MaxScale = 9, INP_MinAllowed = -1000000, INP_MaxAllowed = 1000000,
                INP_Integer = false, ICS_ControlPage = "Controls", },
      Demo  = { LINKS_Name = "Play demo timing", LINKID_DataType = "Number", INPID_InputControl = "CheckboxControl",
                INP_Default = 0, ICS_ControlPage = "Controls", },
      Accent = { LINKS_Name = "Accent", LINKID_DataType = "Number", INPID_InputControl = "ColorControl",
                 IC_ControlGroup = 1, IC_ControlID = -1, ICS_ControlPage = "Controls", },
      AccentRed   = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = 0, INP_Default = 0.16, ICS_ControlPage = "Controls", },
      AccentGreen = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = 1, INP_Default = 0.47, ICS_ControlPage = "Controls", },
      AccentBlue  = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = 1, IC_ControlID = 2, INP_Default = 1, ICS_ControlPage = "Controls", },
    },
  },
} }
```
Paste with Route A (10). Then wire consumers: `BTN_Fill.TopLeftRed` expression `CTRL.AccentRed` (same for Green/Blue).
Verify: the Inspector shows one color row and two labeled controls; changing Accent recolors every consumer in a render; keying Slide works with Demo 0.

Python alternative (**live-verified 2026-09-26 through the Resolve bridge**: `UserControls` read `{}` on a fresh Custom, the setter plus `Refresh()` returned a tool handle, the new `Spacing` input existed, `SetInput("Spacing", 0.75)` returned None but read back 0.75, and `UserControls` read back the dict):
```python
uc = dict(ctrl.UserControls or {})
uc['Spacing'] = {'LINKS_Name': 'Spacing', 'LINKID_DataType': 'Number', 'INPID_InputControl': 'SliderControl',
                 'INP_Default': 0.6, 'INP_MinScale': 0, 'INP_MaxScale': 2, 'ICS_ControlPage': 'Controls'}
ctrl.UserControls = uc
ctrl = ctrl.Refresh()                       # use the returned handle afterwards
ctrl.SetInput('Spacing', 0.6)
```

## Recipe C2: publish the rig as an Edit-page Title (status: unverified (not yet rendered))

```lua
{ Tools = ordered() {
  GalleryTitle = GroupOperator {
    Inputs = ordered() {
      Input1 = InstanceInput { SourceOp = "CTRL", Source = "Slide", Name = "Slide", Default = 1, Page = "Controls", },
      Input2 = InstanceInput { SourceOp = "CAPTION", Source = "StyledText", Name = "Caption", },
      Input3 = InstanceInput { SourceOp = "CTRL", Source = "AccentRed", Name = "Accent", ControlGroup = 3, Default = 0.16, },
      Input4 = InstanceInput { SourceOp = "CTRL", Source = "AccentGreen", ControlGroup = 3, Default = 0.47, },
      Input5 = InstanceInput { SourceOp = "CTRL", Source = "AccentBlue", ControlGroup = 3, Default = 1, },
    },
    Outputs = { MainOutput1 = InstanceOutput { SourceOp = "OUT_Merge", Source = "Output", }, },
    ViewInfo = GroupInfo { Pos = { 0, 0 } },
    Tools = ordered() { --[[ CTRL, CAPTION, cards, OUT_Merge ... ]] },
  },
} }
```
Verify: after relaunch the title appears under Effects > Titles; on a timeline item the Inspector shows Slide, Caption, Accent; keying Slide in the Edit-page Inspector animates the render; a second instance keeps its own values.

## Don'ts and failure lessons

- Do not require the user to repair hidden copies or dependent keys for a routine edit.
- Do not assume a copied group shares its media; do not assume fan-out media is independent.
- Do not bury the user-facing control behind a time expression.
- Do not renumber published `InputN` keys casually: button scripts (`BTNCS_Execute`) address them by ID.
- Do not publish every inner parameter; expose the few everyday controls with units and ranges.
