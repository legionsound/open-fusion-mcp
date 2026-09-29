# Tested native mechanics

Observed on Resolve Studio 21.1.0.14/macOS in the
[recorded session](qualification-evidence.md). Re-check installed signatures,
registry IDs and inputs elsewhere. These snippets assume an already verified,
authorized comp/tool target; they are not standalone connection scripts.

Ownership, timing and recovery rules live in [API routing and QC](api-routing-and-qc.md).
Construction outlines without qualification live in [native authoring](history/native-dsl.md).

## Tool creation and connections

```python
tool = comp.AddTool(reg_id, False, x, y, False, False)
# id, defsettings, xpos, ypos, autoconnect, automerge
tool.SetAttrs({'TOOLS_Name': stable_name})
tool.SetInput(input_id, value)
tool.ConnectInput(port_id, upstream_tool)
```

The guessed three-argument form created unwanted auto-merges in this build.
Use explicit flags. Inspect the created graph and resolve partial state before
retrying. UI names and registry IDs differ: Custom, BetterResize,
SurfaceFBXMesh, ImagePlane3D, Shape3D, Camera3D, Merge3D, Transform3D,
Renderer3D, LightDirectional and LightAmbient were used.

Discover IDs with fusion.GetRegList() and registry-entry GetAttrs(); return only
needed names/IDs. Do not dump the whole registry into context.

Loader/Saver/mesh creation can open file pickers. Short locks around creation
and path assignment avoided those dialogs in the observed build. Guarantee
unlocking even on failure, then verify lock state and pixels. Lock is not a
transaction, and older locked-write/render discrepancies are not disproved.

## Scalar Bezier animation

```python
tool.AddModifier(input_id, 'BezierSpline')
inp = next(v for v in tool.GetInputList().values()
           if v.GetAttrs()['INPS_ID'] == input_id)
spline = inp.GetConnectedOutput().GetTool()
spline.SetKeyFrames({
    0: {1: 0, 'RH': {1: 10, 2: 0}},
    48: {1: 1, 'LH': {1: -30, 2: 0}},
}, True)
```

Use this on a known scalar input whose animation you own. Do not replace
someone else's existing modifier merely because this example calls AddModifier.

True replaces existing keys. AddModifier seeded an unwanted current-frame key;
DeleteKeyFrames followed by default merge-style SetKeyFrames did not reliably
remove it. Verify the exact returned key set and scalar values at endpoints and
an intermediate frame, then inspect motion pixels.

Python RH/LH values are relative time/value offsets in this observed API.
Zero value offset gives a horizontal tangent. Serialized .comp handles are
absolute coordinates. Do not mix those representations. When removing a stray
key, reconstruct intended tangents; deleting the key alone can leave bad easing.

A named Custom controller can own NumberIn1/2/3/4 for X/Y/scale/angle. The
downstream Transform Center expression used:
`Point(UNIT_CTRL.NumberIn1, UNIT_CTRL.NumberIn2)`.
Size and Angle used NumberIn3 and NumberIn4. The observed group-scale edit
rendered correctly. Meaningful labels, published timing controls and macro
packaging require separate qualification.

## Dimensional geometry and editable display

Observed chain:

1. Authored rounded OBJ meshes loaded through SurfaceFBXMesh.ImportFile.
2. Native UI subgraph connected to ImagePlane3D.MaterialInput.
3. Geometry/display merged with Merge3D and moved by Transform3D.
4. Rig, Camera3D and lights merged into a world, then Renderer3D.
5. Rendered image composited over a native background and under graphic overlays.

Retain mesh sources and assets. This established real thickness, rounded edges,
perspective and lighting, not photoreal CAD or arbitrary 3D format support.

For this classic renderer, the display used
`SurfacePlaneInputs.Lighting.IsAffectedByLights = 0` and
`MtlStdInputs.ReceivesLighting = 1`.
Disabling both produced black; enabling both overlit the UI. Verify this
combination in pixels with the chosen renderer. It is not a general material rule.

## Still images and mask geometry

Numeric filenames can be interpreted as sequences. Prefer alphabetic names and
inspect Loader clip metadata. For the observed zero-based still range:

```python
loader.SetInput('Clip', path, 1)
loader.SetInput('ClipTimeEnd', 0, 1)
loader.SetInput('HoldLastFrame', final_frame, 1)
loader.SetInput('GlobalOut', final_frame, 1)
```

Read TOOLST_Clip_Name, TOOLNT_Clip_End, TOOLIT_Clip_TrimOut and
TOOLIT_Clip_ExtendLast. Loop writes did not prove a loop was enabled.
Changing an existing clip's length can open a trim-reset modal. Handle it, or
create a fresh Loader and reconnect confirmed consumers before removing the old
one. Do not ignore a timeout and repeat the import.

The observed EllipseMask needed equal Width/Height values for a circle at
square pixels. Rectangle and ellipse normalization must be checked individually;
do not mechanically apply the frame aspect ratio.

## Saver and output

Connect Saver.Input to the intended final image. PNGFormat and an explicit
Clip path were qualified. For a short check:

```python
comp.Render({'Start': frame, 'End': frame, 'Wait': True})
```

A longer pass used Wait false. Neither return is sufficient proof of completion:
inspect render/playback state, expected file range and actual images. Completion
notices may appear after the first UI snapshot. Clear them before save/export;
null receipts were observed while a completion notice remained open.

PNG sequence encoding produced the review movie; the movie's metadata and full
decode were checked separately. Saver output does not certify timeline color
management or another delivery path. Re-qualify those when used.

Use the [QC gates](api-routing-and-qc.md) and
[qualification evidence](qualification-evidence.md) to state exactly what passed.
