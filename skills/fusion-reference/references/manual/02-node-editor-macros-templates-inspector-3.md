<!-- 02-node-editor-macros-templates-inspector.md part 3 of 3; index: 02-node-editor-macros-templates-inspector.md -->
## Scripting and automation hooks

### Stated in this slice
- **Node text format**: copied nodes are plain text identical to Fusion's internal save format; paste text into the Node Editor to recreate (p. 141-142). `.setting` files (node settings, groups, macros, templates) use it and can be dragged into the Node Editor (p. 155, 161).
- **Node naming constraint** for scripts/expressions: alphanumeric, no spaces, not starting with a digit (p. 148). Instances: `Instance_<Name>`, `Instance_<Name>_01` (p. 145).
- **Find** matches tool name, tool type name, or **tool type ID**; supports regex (p. 153).
- **Defaults file naming**: `INTERNALNAME_PUBLICNAME.setting`, e.g. `Blur_Blur.setting`; folder = Path Map > Defaults (p. 154).
- **Path maps named**: Path Map > Defaults; `LUTs:` folder; Preferences > Global > Path Map > LUTS (p. 154, 165, 220).
- **Input/parameter IDs named in the slice**: MediaIn `ClipName`, MediaIn `Layer` (Macro Editor Tool/Input column shows internal names, p. 163, 178-179); Directional Blur `Center`, `Length`, `Angle`, `Type` (p. 248-249); new user IDs `Centered`, `TypeNew`.
- **Expression namespace examples**: `Center.X`, `Center.Y`, `Input.XScale`, `Input.YScale`, `Input.Width`, `Input.Height`, `Input.OriginalWidth`, `Input.X`, functions `sqrt`, `atan2`, `iif(cond, a, b)`, constant `pi`, power `^` (p. 248-249).
- **Input control class names**: `CheckboxControl`, `MultiButtonControl`; data types `Number`, `Point`; page `Controls` (p. 249).
- **Animated value encodings**: checkbox 0 / >=1.0; dropdown 0-based index (p. 237-238).
- **Fuse LUT name**: `CT_ViewLUTPlugin` (p. 216).
- **Modifier names**: Resolve Parameter (Scale, Offset), Anim Curves, Keyframe Stretcher, From Image, Perturb (p. 171, 178, 199).
- **File types**: `.setting`, `.drfx` (zip), `.png` template icon (104 x 58), `.viewlut`, `.alut`, `.alut3`, `.lut`, `.cube`, `.shlut`, `.look`, `.3dl`, `.itx`.

### Keyboard shortcuts (as printed for macOS; Windows equivalents Ctrl/Alt are inference)

| Context | Key | Action |
|---|---|---|
| Node Editor | Shift-Space | Select Tool window (also "sticky", "under") |
| Node Editor | V | Toggle Node Navigator |
| Node Editor | Cmd-1 | Default scale |
| Node Editor | Cmd-D | Add bookmark |
| Node Editor | Cmd-A / Cmd-Shift-A | Select all / deselect all |
| Node Editor | Option-click node | Make active node |
| Node Editor | Option-click connection | Add router |
| Node Editor | Option-drop connection | Choose input by name |
| Node Editor | Shift-drag | Extract / insert node |
| Node Editor | Cmd-T | Swap inputs |
| Node Editor | Cmd-C / X / V | Copy / cut / paste |
| Node Editor | Cmd-Shift-V | Paste Instance |
| Node Editor | F2 | Rename |
| Node Editor | hold Cmd-Shift-E | Show node types instead of names |
| Node Editor | Cmd-F | Find |
| Node Editor | Cmd-P / Cmd-L / Cmd-U | Pass Through / Lock / Update |
| Node Editor | Cmd-G / Cmd-E | Group / open-close group |
| Node Editor | Delete (mac) / Backspace (Win) | Delete |
| Node Editor or viewer | 1, 2 (3-9) | View selected node in viewer N / clear |
| Viewer | ` | Clear active viewer (all if none active) |
| Viewer | = / - | Zoom in / out |
| Viewer | Cmd-1 / Cmd-2 / Cmd-F | 100% / 200% / fit |
| Viewer | Cmd-K | Show/hide onscreen controls |
| Viewer | Cmd-G | Show guides |
| Viewer | Cmd-L | Lock viewer |
| Viewer | , / . | A / B buffer |
| Viewer | / | Split wipe |
| Viewer | Cmd-Option-click | Move wipe divider to pointer |
| Viewer | V / Shift-V | Subview on/off / swap |
| Viewer | C R G B A Z | Channel display |
| Viewer | Shift-Q | Quad view |
| Viewer | Option+middle-drag or middle+right drag | Rotate 3D view / 3D Histogram |
| Viewer | Option-drag node in / Shift-Option-drag | Flipbook with / without dialog |
| Flipbook | Space / Shift-Space / arrows / Shift-arrows / Cmd-arrows | Play / reverse / step / 10 frames / ends |
| Onscreen controls | Up/Down (+Cmd 1/10, +Shift 10x) | Nudge |
| Inspector | Cmd / Shift click slider gutter | Fine / coarse step |
| Inspector | Cmd-drag range end | Symmetric range |
| Inspector | Cmd-drag gradient stop | Copy stop |
| Inspector | Cmd-drag rectangle with eyedropper | Set picker sample size |
| Multi-Inspector | Opt/Alt-drag | Toggle offset vs scale mode |

Paths: templates in section 4, Macros folder in section 2, Defaults in section 1, LUTs in section 5.

### Inferred mapping to scripting and .setting text (inference; this slice does not document file structure or API calls, verify against the Resolve/Fusion scripting docs)
- A macro `.setting` is a Lua table whose tool is a `MacroOperator` (a group is `GroupOperator`) containing `Inputs = ordered() { ... InstanceInput { SourceOp = "<node>", Source = "<inputID>", Name = "...", Default = ... } }`, `Outputs = { MainOutput1 = InstanceOutput { SourceOp = "<node>", Source = "Output" } }`, and an inner `Tools = ordered() { ... }`. Each Macro Editor row with Export checked becomes one `InstanceInput`; image inputs are conventionally `MainInput1...`. (inference)
  ```lua
  {
    Tools = ordered() {
      MyBlurMacro = MacroOperator {
        Inputs = ordered() {
          MainInput1 = InstanceInput { SourceOp = "Blur1", Source = "Input", },
          Input1 = InstanceInput { SourceOp = "Blur1", Source = "XBlurSize", Name = "Size", Default = 5, },
        },
        Outputs = { MainOutput1 = InstanceOutput { SourceOp = "Blur1", Source = "Output", }, },
        ViewInfo = GroupInfo { Pos = { 0, 0 }, },
        Tools = ordered() {
          Blur1 = Blur { Inputs = { XBlurSize = Input { Value = 5, }, }, ViewInfo = OperatorInfo { Pos = { 0, 0 }, }, },
        },
      },
    },
  }
  ```
- Edit Control / UserControls are stored per tool as `UserControls = ordered() { <ID> = { LINKID_DataType = "Number", INPID_InputControl = "CheckboxControl", LINKS_Name = "...", ICS_ControlPage = "Controls", ... } }`; MultiButton entries add `{ MBTNC_AddButton = "Linear" }` items; hiding uses `IC_Visible = false`. Expressions are stored on the input as `Type = Input { Expression = "iif(Centered==1, 2, 0)", }`. (inference)
- Node Modes map to tool attributes: Pass Through `TOOLB_PassThrough`, Locked `TOOLB_Locked`; rename via `tool:SetAttrs({ TOOLS_Name = "NewName" })` (same naming rules apply). Expressions via `tool.<InputID>:SetExpression("...")`. Save/Load node settings via `tool:SaveSettings(path)` / `tool:LoadSettings(path)`; paste a `.setting` into a comp with `comp:Paste(bmd.readfile(path))`. (inference)
