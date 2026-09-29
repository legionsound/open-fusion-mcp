# 07 Gallery, Coverflow and complex 3D sliders

Use this module when one Slide value has to place many cards under a camera you can animate: card galleries, Coverflow, sliders that wrap around, curved galleries, loops with straight runs and bends. Fusion advantage: real `Camera3D`, depth sorting and occlusion in `Renderer3D`, and one controller read by expressions on every card. Coverflow status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frame 0 at Slide 1 and Slide 2.5, 5 cards, generator below). Curved gallery and stadium loop: unverified (not yet rendered).

## Select the correct construction

Start by measuring the reference: how many cards, the size of the front card, how much they overlap, the angle of the side cards, depth, corner rounding, the edges of the stage and the camera's perspective. Curved galleries, Coverflow stacks and loops with straights and hairpin bends each need their own rig; flattening a complicated loop into a plain round carousel loses the design. From a still reference, reproduce the resting layout first, then add the simplest smooth motion that fits it and the controls the user asked for.

Each card is its own replaceable subgraph `CARDnn_CONTENT`: `MEDIA_Cardnn` (Loader/MediaIn) -> cover-fit Merge (05) -> native bottom-shading gradient + `TextPlus` caption -> rounded `RectangleMask` on the card -> card image. That image feeds `CARDnn` (`ImagePlane3D.MaterialInput`), whose aspect follows the card image. Rounded corners belong to the card, so swapping a photo cannot remove them. Never combine cards into an atlas or crop them out of the screenshot.

```
CARD01_CONTENT -> CARD01 ImagePlane3D --\
CARD02_CONTENT -> CARD02 ImagePlane3D ---+-> CARDS Merge3D -> STAGE Merge3D -> RENDER Renderer3D -> STAGE_Mask (rounded) -> scene Merge
...                                       |        CAM Camera3D -> CAM_ORBIT Transform3D --^
CTRL Custom (UserControls; not wired) ----(read by expressions)
```

## One Slide control

`CTRL.Slide`: 1 = first card centered, 2 = second, fractional = in-between. Keep this convention in every expression and the guide; a 0-100 full-loop percentage is also valid if labeled, never mixed invisibly. Every card carries two UserControls: `Idx` (its index, constant) and `D` (its wrapped signed offset from center, computed once):

```
D  = :local N=CTRL.Count; local x=Idx-CTRL.Slide; return x - N*math.floor(x/N + 0.5)
```
`D` lies in [-N/2, N/2) for any Slide, including negatives (floor-based modulo; Lua `%` is also floor-based, the explicit form is clearer). Derive position, orientation, depth, emphasis and shading from `D` only, so wraparound and front-card handoff stay continuous. Timing lives on `CTRL.Slide` as sparse editable keys; optional demo keys sit on a separate `DemoSlide` gated by `Demo` (06), manual control effective by default.

Expose only useful layout controls on CTRL: `Count`, `Spacing`, `CenterGap`, `SideAngle`, `Depth`, `StackDepth`, `Dim`, `Window`, `AngleSign` (+1/-1), plus rig-specific `Radius`, `StepAngle`, `Concave`, `Straight`, `LoopRadius`. Add per-card offsets only when needed. Publish `CTRL.Slide` (and at most a few layout controls) as macro `InstanceInput`s (06 recipe C2) so a parent comp or the Edit-page Inspector drives the rig; nested media sources still need deliberate uniqueness.

2D or 3D: the same `D` expression can drive 2D `Transform` nodes (`Center` = `Point(0.5 + x, 0.5)`, `Size`, `Angle`) for a flat slider with no camera. But a 2D Merge chain has a fixed stacking order set by wiring, so cards that exchange front/back order need the 3D route (`Merge3D` + `Renderer3D` depth sorting). Use 2D only when order never changes.

## Coverflow

Expressions on each `CARDnn` (ImagePlane3D has its own `Transform3DOp`; dotted IDs need bracket keys in `.setting`):

| Input | Expression |
|---|---|
| `Transform3DOp.Translate.X` | `:local d=D; local c=math.max(-1,math.min(1,d)); return c*CTRL.CenterGap + (d-c)*CTRL.Spacing` |
| `Transform3DOp.Translate.Z` | `-math.min(math.abs(D),1)*CTRL.Depth - math.max(math.abs(D)-1,0)*CTRL.StackDepth` |
| `Transform3DOp.Rotate.Y` | `-CTRL.AngleSign*math.max(-1,math.min(1,D))*CTRL.SideAngle` |
| `MtlStdInputs.Diffuse.Color.Red/Green/Blue` | `1 - CTRL.Dim*math.min(math.abs(D),1)` |
| `SurfacePlaneInputs.Visibility.IsVisible` | `iif(math.abs(D) <= CTRL.Window + 0.5, 1, 0)` |

Starting values (ImagePlane3D is **1 unit wide with height = width x image H/W**, live-measured: a 900x1200 card image gives a 1 x 1.333 plane, a square image 1 x 1): `CenterGap` 0.75, `Spacing` 0.28, `SideAngle` 65, `Depth` 0.6, `StackDepth` 0.02 (farther side cards sit slightly behind to avoid coplanar fighting), `Dim` 0.35, `Window` 4 with `Count` 9 (the wrap jump at |D| = N/2 happens while the card is invisible, so no teleport or opacity pop). Verify `AngleSign`: set one right-side card to Rotate.Y +30 and check which edge recedes; the outer edge must recede. **Live 2026-09-26:** with `AngleSign 1` and the expression above, right-side cards get `Rotate.Y -65` and their outer (right) edge recedes, so `AngleSign 1` is correct for this rig. Read-back at Slide 1 (N 5): D = 0, 1, 2, -2, -1 for cards 1..5 (wrap correct); at Slide 2.5: D = -1.5, -0.5, 0.5, 1.5, -2.5, `Translate.X` -0.89, -0.375, 0.375, 0.89, -1.17. Renderer3D depth-sorted the crossing cards correctly. Camera used: default Camera3D at `Translate.Z 4.5`. Keep the front card facing the camera, the reference's spacing, rotation and overlap, and native editable bottom shading/caption inside each card. For a rounded black stage on a larger background, render the scene, then apply the stage boundary once at the parent (`RENDER -> Merge` with a rounded `RectangleMask` stage); never flatten or clip cards individually.

## Curved gallery

| Input | Expression |
|---|---|
| `Transform3DOp.Translate.X` | `CTRL.Radius*math.sin(math.rad(D*CTRL.StepAngle))` |
| `Transform3DOp.Translate.Z` | `CTRL.Concave*CTRL.Radius*(1-math.cos(math.rad(D*CTRL.StepAngle)))` |
| `Transform3DOp.Rotate.Y` | `-CTRL.Concave*CTRL.AngleSign*D*CTRL.StepAngle` |

`Concave` +1 brings edges toward the camera (gallery wall), -1 recedes (carousel). Keep the center card readable while side cards follow the measured fan. Keep surrounding headings and labels as live Text+ outside the 3D scene. Test the largest visible card and the smallest side card with real content: a good source image can still crop badly in perspective.

## A loop with straight segments and bends (stadium)

Build the actual topology: two straights of length `Straight` (L) joined by semicircles of radius `LoopRadius` (r), perimeter P = 2L + 2*pi*r. Parameterize by arc length so spacing and apparent speed stay uniform (an arbitrary curve parameter is not distance). Per card add a third UserControl `S` (arc position):

```
S  = :local N,L,r=CTRL.Count,CTRL.Straight,CTRL.LoopRadius; local P=2*L+2*math.pi*r; local u=(Idx-CTRL.Slide)/N; return (u-math.floor(u))*P
X  = :local L,r,s=CTRL.Straight,CTRL.LoopRadius,S; local a=math.pi*r; if s<L then return -L/2+s end; s=s-L; if s<a then return L/2+r*math.sin(s/r) end; s=s-a; if s<L then return L/2-s end; s=s-L; return -L/2-r*math.sin(s/r)
Z  = :local L,r,s=CTRL.Straight,CTRL.LoopRadius,S; local a=math.pi*r; if s<L then return r end; s=s-L; if s<a then return r*math.cos(s/r) end; s=s-a; if s<L then return -r end; s=s-L; return -r*math.cos(s/r)
RY = :local L,r,s=CTRL.Straight,CTRL.LoopRadius,S; local a=math.pi*r; local h; if s<L then h=0 elseif s<L+a then h=math.deg((s-L)/r) elseif s<2*L+a then h=180 else h=180+math.deg((s-2*L-a)/r) end; return CTRL.AngleSign*h
```
Orientation comes from the tangent (card plane tangent to the path, face outward). Verify the rotation convention on one card at the start of the right bend, inspect both joins between straight and curve (position and heading continuous), and the 360 -> 0 heading wrap (same orientation; check motion blur does not smear it). Each card stays its own object and content. Rigid cards stay rigid; if the reference shows cards bending around the bend, raise `SurfacePlaneInputs.SubdivisionWidth` and add `Bender3D` per card, verified in the renderer. Never move an image atlas over stationary surfaces.

Hidden surfaces: set `SurfacePlaneInputs.Visibility.CullBackFace` 1 where back faces must disappear; drive `IsVisible` to 0 for cards that should vanish. The AE rig needed zero scale because zero opacity still occluded; in Fusion check whether a zero-opacity plane still writes depth in the chosen `RendererType` before relying on opacity.

## Camera

Keep `CAM` (Camera3D) free of expressions so the user can key `Transform3DOp.Translate.*`, `Rotate.*`, `FLength`/`AoV`. An optional `CAM_ORBIT` Transform3D downstream of the camera gives a clean orbit around the stage center (downstream 3D transforms move upstream objects). Name both in the guide. Separate camera control from Slide. Test from a modest alternate angle (orbit 15 degrees, tilt 8 degrees): a rig that survives only its original view fails a request for an animatable camera. Depth of field needs `RendererType` "RendererOpenGL" with accumulation effects; soft shadows need the Software renderer (default).

## Build N cards by generated `.setting` text

```python
N = 9
def exprs(i):
    return {
      'D': ':local N=CTRL.Count; local x=Idx-CTRL.Slide; return x - N*math.floor(x/N + 0.5)',
      'Transform3DOp.Translate.X': ':local d=D; local c=math.max(-1,math.min(1,d)); return c*CTRL.CenterGap + (d-c)*CTRL.Spacing',
      'Transform3DOp.Translate.Z': '-math.min(math.abs(D),1)*CTRL.Depth - math.max(math.abs(D)-1,0)*CTRL.StackDepth',
      'Transform3DOp.Rotate.Y': '-CTRL.AngleSign*math.max(-1,math.min(1,D))*CTRL.SideAngle',
      'SurfacePlaneInputs.Visibility.IsVisible': 'iif(math.abs(D) <= CTRL.Window + 0.5, 1, 0)',
    }
def card(i):
    ins = ''.join(f'["{k}"] = Input {{ Expression = "{v}", }}, ' for k, v in exprs(i).items())
    uc = ('UserControls = ordered() { '
          'Idx = { LINKS_Name = "Card index", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = %d, ICS_ControlPage = "Controls", }, '
          'D = { LINKS_Name = "Offset (read only)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0, ICS_ControlPage = "Controls", }, }' % i)
    return (f'CARD{i:02d} = ImagePlane3D {{ Inputs = {{ Idx = Input {{ Value = {i}, }}, {ins}}}, '
            f'ViewInfo = OperatorInfo {{ Pos = {{ 0, {i*40} }} }}, {uc} }},\n')
text = '{ Tools = ordered() {\n' + ''.join(card(i) for i in range(1, N+1)) + '} }'
open(path, 'w').write(text)
cc.Execute('comp:Paste(bmd.readfile([[' + path + ']]))')   # current Fusion-page comp only; deferred: poll FindTool('CARD09')
```
Then wire `CARDnn.MaterialInput` from each content subgraph and each card into `CARDS` (`SceneInput1..N`) with `ConnectInput`, checking every return value. Expressions contain no double quotes, so they embed safely in the Lua text. **Live 2026-09-26:** this generator pasted as typed (content Merges and `MaterialInput`/`SceneInput` connections added inside the same text also work); bare `Idx` and `D` inside a tool's own expressions resolve to that tool's UserControls, and `:` statement blocks evaluate.

## Verify the control, not only the demo

- Slide = 1, 2, N (integers), 1.5 (fractional), -0.5 (negative), N + 0.5 (seam), a keyed full cycle 1 -> N+1 forward and N+1 -> 1 reverse, repeated cycles, and a hand-keyed sequence with Demo 0.
- Interpolation between cards: no pop at the depth-order exchange, no extra sway, front-card handoff continuous; card order changes only where cards actually cross.
- Camera move from an alternate angle; stage mask stays at the parent.
- Replace one card's media with a different aspect ratio; lengthen one caption; confirm other cards keep their own content; restore originals.
- Read back `D` on two cards at a seam frame (`card.GetInput('D', f)`) to confirm the wrap math, then render.
- Explain any genuinely fixed layout limits.

## Don'ts and failure lessons

- No generic circular carousel for a measured loop; no atlas; no cards cropped from the reference.
- No expressions on the camera the user wants to animate.
- No per-card timers: everything reads one Slide.
- No clipping cards individually to fake a stage.
- Degrees on inputs, radians inside expression trig (`math.rad`).
