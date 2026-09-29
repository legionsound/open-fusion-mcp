# 03 Typography, layout and construction diagrams

Load for font matching, kinetic type, tracking, glyph deformation, reveals and cuts, counters, echoes and construction diagrams. `TextPlus` is the default; Follower (`StyledTextFollower`) is Fusion's text animator. Timing at 24 fps.

## Resolve identity before fitting motion

When a distinctive typeface matters, check the source project's credits or case study before substituting. If the original is unavailable, compare full words and diagnostic glyphs (counters, terminals, M/N construction, numerals) in the actual Fusion render. Pixel overlap supports but does not replace visual review; whole-word alignment can mis-rank weights. Confirm the family and style exist (`fusion.FontManager.GetFontList()`, stub-listed; output format unverified) and that every visible `TextPlus` resolves them: set `Font` (family) and `Style` (face) explicitly, then render; a wrong style name may silently fall back (unverified; check the render). State material substitutions.

Size and metrics (live-verified, Open Sans Bold): `Size` is relative to image WIDTH; `Size ~= 1.70 * font_px / W`, cap height `~= 0.42 * Size * W`. `Center` is the layout center, Y up. Tracking is `CharacterSpacing` (default 1.0; below 1 overlaps), leading is `LineSpacing`. `HorizontalLeftCenterRight` / `VerticalTopCenterBottom` (-1..1) set the anchor that tracking and rotation pivot about. `UseLigatures` default is none for Latin so letters stay separable; keep it for per-character animation.

**The size constant K is per font and per weight [live, gapfix pass, K1].** `Size = K * font_px / W`. Open Sans Bold K = 1.70 **[live]** (FontManager returned no font file for Open Sans, so `text.size_for_px` cannot measure it: keep 1.70). Helvetica Neue Bold K = **1.478**, cap/em 0.714, measured by `text.size_for_px` (the rebuild's calibration by render gave 1.49); `text.set_style sizePx 280` then rendered a 201 px cap against 199.9 px predicted **[live, gapfix pass]**. Helvetica Neue Light = 0.989 x the Bold K (Light sets 1.1 % wider at the same K) [from rebuild log, K20]. Using 1.70 for Helvetica Neue makes glyphs about 15 % too big. Why it varies (the rebuild's explanation): Text+ normalises the em by the font's ascent+descent, so K follows each font's vertical metrics; treat it as a measurement, not a formula. Measure with `text.size_for_px {font, style, px}` (a temporary Text+ "H", its DoD cap height against the font file's cap height per em; cached per font and style); `text.set_style sizePx` then uses that K (else 1.70, and it says so); `sizeK` overrides. Without the connector: one Text+ with `CenterOnBaseOfFirstLine` 1 (puts `Center` on the first baseline) and `HorizontalLeftCenterRight` -1 (left anchor), render, measure cap height or a known word width, scale K (or read the rendered bounds, `Tool.Output[0].DataWindow`, realities §7). Check the first title by render either way.

**Pasted Text+ needs `UseFrameFormatSettings = 1`** (like every generator), or it comes up 320x240 **[live, gapfix pass]** (realities §11 item 31).

## Tracking and translation without breathing

Keep glyph proportions stable. Animate `CharacterSpacing` (or Follower `CharacterOffset`) with fixed `Size`; never key a fitted width/height against changing text bounds, which makes type breathe or squash. Put the shared phase on one controller value (06) that both the spacing and any companion move read. Let content edits reflow naturally (`LayoutType` Frame with `Wrap` and `LayoutWidth`), or expose an explicit Fit control; do not turn a spacing change into glyph width change. Preserve a real scale cut or deformation when the reference shows one.

## Choose the representation before easing it

| Reference shows | Rig |
|---|---|
| Glyphs rotate/offset/scale individually | Follower keys on `CharacterAngleZ`, `CharacterOffset`, `CharacterSizeX/Y`, `Opacity1`; Timing `Order`, `DelayType`, `Delay` |
| Whole line/word moves as a unit | `TextPlus` `Center`/`LayoutSize` or a downstream `Transform` |
| Weight change | Two `TextPlus` copies (Paste Instance, deinstance `Style`) crossfaded, or a variable-font route if verified (unverified) |
| Bespoke contour deformation of one glyph | Native font for normal states; a few consistent-topology `sPolygon` contour poses for that glyph only, swapped in at a cut |
| Text changes | Key `StyledText` (right-click Animate) or cut between copies at exact frames |
| Text follows a curve with rigid glyphs | `LayoutType` Path + `PositionOnPath` (values beyond 0..1 continue off the path) |
| Vector ops on text (booleans, point jitter, write-on) | `sText` -> sShape tools -> `sRender` (no gradient fill; Krokodove `KD_ShapeWriteOn`, `KD_ShapeResample` exist) |

Easing the wrong representation cannot recover the reference. Compare an ordinary and an extreme pose first. Keep construction overlays separate from editable wording and say when they are specific to one logo or glyph.

## Reveals, cuts and montage cards

Write down, for every reveal, the frame where it first shows and how long it holds at the end. Fusion holds the first key's value before it: a type-on starting at f24 needs `End`=0 keyed at f24 (and the tool visible only from there), otherwise frames 0-23 show the first key's state. `TextPlus` write-on inputs are `Start` / `End` (Write On Start/End, 0..1); a left-to-right reveal is normally `End` 0 -> 1 (the manual prints the reverse direction: verify on frame). `End` reveals whole characters (a hard typewriter); a soft, faded typewriter needs the Follower route below [from rebuild log, K21]. Check three frames around every event: the one just before a reveal, the last one before a cut and the first one after it. A collage that keeps growing tells you nothing about the camera; measure landmarks that stay on screen. When tracking particles, read a steady color from inside each one separately from its shape (a `Probe` modifier on an interior region), so a fade from black to color does not swap which particle is which.

## Spatial typography and motion with a destination

A phrase stays in one piece, reads in an obvious order and stays up long enough to read the actual
words (timing tables in [animation-principles](animation-principles.md)). Give it room, and set the few
keywords that matter clearly apart from the supporting copy. The type treatment comes from the
visual direction you chose and from any reference; one favourite font pairing is not a house style for
every job.

If the scene contains a surface (a page, a wall, a card, a screen, an object), text can sit on it and
inherit its perspective, its movement and whatever passes in front of it. Fusion routes, cheapest first:

| Surface | Route |
|---|---|
| Flat card that only moves in 2D | Text+ merged inside the card's subgraph before the card's Transform, so both ride one transform |
| Static perspective plane in a still or locked shot | `CornerPositioner` (`TopLeft`/`TopRight`/`BottomLeft`/`BottomRight` points, `MappingType` 1 Perspective) on the Text+ output. [verified live 2026-09-26] The corners map the Text+ tool's **whole frame**, not the glyph bounds: "SIGN" in the middle of its frame landed foreshortened in the middle of the quad, not filling it. Lay the text out to fill its own frame (or crop it) first (`t03_cornerpos_annot.png`) |
| Moving plate with a planar surface | `Dimension.PlanarTracker` on the plate, then `Dimension.PlanarTransform` on the text in the same session (tracks do not survive reload, realities §12). [verified live 2026-09-26] A Text+ placed on the surface at the reference frame, through a copy of the tracker's `PlanarTransform` (`tool.duplicate` keeps the track), stayed on the tracked spot within 1 px at frames 0, 12 and 23 of a moving, rotating plate |
| Object in a 3D scene | Text+ into `ImagePlane3D` parented under the object's `Transform3D`/`Merge3D`, or `Text3D` for real extruded depth; occlusion comes from the renderer's depth |
| Surface occluded by a foreground element | put the occluder above the text in Merge order or cut the text with the occluder's matte (`Operator` "Held Out" / mask input) |

Keep phrases complete; never cover a meaningful face or the evidence the shot is about. Solve
legibility with placement, scale, timing and a timed contrast change before reaching for heavy
glows, strokes or boxes.

Give continuous motion a destination that reveals or connects information: a push that lands
on the keyword, a line that arrives at the number it explains. Check the easing, where the
motion stops, the carry-through and the motion blur (Text+ `MotionBlur`, 09). Follow busy passages
with room to read, and resist giving every beat the same word bounce or camera pulse unless the
treatment is built on that repetition.

## Construction diagrams

Tie every anchor, tangent, dimension and label to the geometry it explains. In Fusion: publish polyline points (`.setting` point field `PublishID = "Point0"`, corpus) or drive dots and labels by expression from the same controller values that define the curve. Separate lines stay separate paths; drawing two vertical rules as one polyline sneaks in a diagonal between them. Get circle proportions right (both EllipseMask sizes are relative to width) and line up any shared angle before anything moves. A chart that grows along a curve draws a path progressively (`sPolygon` Solid 0 with `WriteLength` 0 -> 1, or a `PolylineMask` `WriteLength`) alongside its values; a spinning pointer is a different design. Compare the real font weight with the reference outline before faking it with scale or strokes. For stacked type echoes, measure every copy's offset, scale, first outline, first fill and exit; evenly spaced copies often produce the wrong overall shape. Build echoes as Paste Instance copies of one `TextPlus` (shared `StyledText`, deinstanced transform/shading) or as extra shading elements (`Enabled2..8` with `Offset2`...) when they share timing.

Show only meaningful curve extrema and corner anchors, not every intermediate font point. Preserve optical stroke and node sizes after scaling: set `BorderWidth`/`Thickness` at final display scale, since a correct pre-scale stroke can vanish on a small glyph. Validate the nested render at intended viewing size.

## Glyphs, line blocks, typewriters and eased cascades [from rebuild log]

- **No per-glyph font fallback [from rebuild log, K6].** Text+ does not substitute a missing glyph from another font (only emoji fall back, to the colour emoji font): ✦ and ✓ rendered as empty boxes in Helvetica Neue, ▶ came out as a colour emoji. Check every symbol by render. Put symbols in their own Text+ in a font that has them (Menlo has ✦ ▶ ✓), positioned next to the word run.
- **One Text+ per line when lines reveal or move separately [from rebuild log, K9].** Real line breaks, one Text+ per line of a multi-line block, so each line's position, timing and reveal is explicit.
- **Typewriter: Follower opacity, not `End` [from rebuild log, K21, corrects K9].** Text+ `End` reveals whole characters: a hard, stepped typewriter. For a soft typewriter, where the character under the cursor fades in over its slot (a partly typed character is partly visible), give each line a `StyledTextFollower` with `Order` 0 (left to right), `DelayType` 1 (between each character), `Delay` = one slot (frames per character) and `Opacity1` keyed as a linear 0 -> 1 ramp lasting one slot. Line k starts where line k-1's last character finished (the line break takes no slot): f0 + (characters in the lines before k) x slot. This matched a reference typewriter to the glyph; `End` keys split by character count left a whole extra character on screen.
- **Eased per-letter cascades: a warped clock [from rebuild log, K16].** A Follower's constant `Delay` spaces letters evenly in time, so it cannot follow a sweep that eases across the word (with an ease-out sweep the late letters land late: 3-4 frames in the rebuild). Build the cascade with linear per-letter ramps in a linear clock tau (`Order` 0, `DelayType` 1, `Opacity1` and `CharacterOffset` ramps with linear handles; for n letters, ramp length R and sweep span S, `Delay` = (S - R)/(n - 1) so the last letter lands at f0 + S), then put a `TimeStretcher` after the Text+ whose `SourceTime` spline carries the ease: tau = f0 + S x EASE(u), u = (t - f0)/S, two keys (f0, f0) and (f0 + S, f0 + S) with the ease's cubic-bezier handles, `InterpolateBetweenFrames` 0 (Nearest, so tau lands on whole source frames). Letters then land on the eased sweep (reference frame MAE 6.9 -> 3.16). Keep other motion of that text (position, scale) downstream of the TimeStretcher or it is warped too. (Rebuilding an existing AE comp: ae-matching.md.)
  ```lua
  TITLE_Fol = StyledTextFollower { Inputs = { Text = Input { Value = StyledText { Value = "EVERY SHOT." }, },
      Order = Input { Value = 0, }, DelayType = Input { Value = 1, }, Delay = Input { Value = 1.090909, },
      Opacity1 = Input { SourceOp = "TITLE_Fol_Op", Source = "Value", }, }, },
  TITLE_Fol_Op = BezierSpline { KeyFrames = { [6.545455] = { 0, RH = { 10.545455, 0.333333 } }, [18.545455] = { 1, LH = { 14.545455, 0.666667 } }, }, },
  TITLE_TWarpS = BezierSpline { KeyFrames = { [6] = { 6, RH = { 9.6, 6 } }, [30] = { 30, LH = { 9.6, 30 } }, }, },
  TITLE_TWarp = TimeStretcher { Inputs = { Input = Input { SourceOp = "TITLE_Txt", Source = "Output", },
      SourceTime = Input { SourceOp = "TITLE_TWarpS", Source = "Value", }, InterpolateBetweenFrames = Input { Value = 0, }, }, },
  ```
  (From the rebuild's pasted scene, names shortened; `TITLE_Txt` is the Text+ whose `StyledText` comes from `TITLE_Fol`. 11 letters, ramps 12 f, over a sweep f6-f30; the warp keys encode cubic-bezier(0.15, 0, 0.15, 1) as absolute handles. Its `Delay` 1.0909 and first key at f6.545 follow the reference's character-centre timing (ae-matching.md); the general rule above gives `Delay` 1.2 from f6.)

## Recipe T1: per-character rise with stagger (status: unverified (not yet rendered))
Purpose: letters rise 40 px and fade in, 2 frames apart, each over 10 frames with an ease-out.

```
TITLE TextPlus StyledText <- TITLE_Follow (StyledTextFollower)
TITLE_Follow: Text "LAUNCH DAY"; Order = left-to-right index; DelayType = between-each-character index; Delay 2
  CharacterOffset keyed: f0 {0, -0.0185} -> f10 {0, 0}    (40/2160 if Y is height-relative; unit unverified, measure once)
  Opacity1 keyed: f0 0 -> f10 1
TITLE -> scene Merge.Foreground
```

```python
fol_name = 'TITLE_Follow'
t = comp.FindTool('TITLE')
t.AddModifier('StyledText', 'StyledTextFollower')
fol = next(v for v in t.GetInputList().values()
           if v.GetAttrs()['INPS_ID'] == 'StyledText').GetConnectedOutput().GetTool()
fol.SetAttrs({'TOOLS_Name': fol_name})
fol.SetInput('Text', 'LAUNCH DAY')      # the Follower now owns the text source
fol.SetInput('Delay', 2)
op = next(v for v in fol.GetInputList().values() if v.GetAttrs()['INPS_ID'] == 'Opacity1')
fol.AddModifier('Opacity1', 'BezierSpline')
op.GetConnectedOutput().GetTool().SetKeyFrames(
    {0: {1: 0.0, 'RH': {1: 1.0, 2: 0.9}}, 10: {1: 1.0, 'LH': {1: -4.0, 2: 0.0}}}, True)
```
Verify: `Order` and `DelayType` are combos whose option indices are not in the TSV (defaults 7 and 1; corpus files use 1, 2, 4): set them in the Inspector once and read back the numbers before scripting. Spaces count as characters in the delay. Changing a Follower value without a key has no visible effect. Render f0, f5, f12, f30; confirm the last letter finishes at 2*(n-1)+10 frames.

`.setting` shape (corpus-derived, unverified):
```lua
TITLE_Follow = StyledTextFollower { Inputs = { DelayType = Input { Value = 1, }, Delay = Input { Value = 2, },
    Text = Input { Value = StyledText { Value = "LAUNCH DAY" }, },
    Opacity1 = Input { SourceOp = "TITLE_FollowOpacity1", Source = "Value", }, }, },
TITLE_FollowOpacity1 = BezierSpline { KeyFrames = { [0] = { 0, RH = { 1, 0.9 } }, [10] = { 1, LH = { 6, 1 } }, }, },
TITLE = TextPlus { Inputs = { StyledText = Input { SourceOp = "TITLE_Follow", Source = "StyledText", }, }, },
```
Note `.setting` handles are absolute (RH {1, 0.9} = frame 1, value 0.9).

## Recipe T2: counter with formatted text (status: unverified (not yet rendered))
`COUNT TextPlus` with `StyledText` SimpleExpression reading a controller number, following the Number+ corpus macro pattern:

```python
t = comp.FindTool('COUNT')
inp = next(v for v in t.GetInputList().values() if v.GetAttrs()['INPS_ID'] == 'StyledText')
inp.SetExpression('Text(string.format("%.0f", CTRL.Value) .. "%")')
```
Key `CTRL.Value` 0 -> 87 over 36 frames with an ease-out (handles as in 02). Verify: frame 36 reads exactly "87%", no decimals flicker, `Size` stays fixed as digit count grows (anchor right or center deliberately). Clearing the expression later leaves an empty/zero value: SetInput the intended text afterwards.

## Don'ts and failure lessons

- Do not outline editable wording into shapes for ordinary states; use outlines only for the glyph that genuinely deforms.
- Do not key `Size` and `CharacterSpacing` independently to chase a bounding box.
- Do not let a delayed element show its first pose from frame 0 (constant pre-extrapolation).
- Do not trust a font name in the Inspector: verify weight and case in the render, and reset styles when creating new `TextPlus` tools by script.
- Character Level Styling selections are viewer-only; they cannot be set in the Modifiers-tab text box.
- Do not reuse 1.70 for a font other than Open Sans; measure K per font and weight (`text.size_for_px`) [live, gapfix pass, K1; from rebuild log, K20].
- Do not assume a symbol renders because the font name is right: missing glyphs draw as boxes, with no fallback except emoji [from rebuild log, K6].
- Do not use `End` keys for a soft typewriter or a constant Follower delay for an eased cascade [from rebuild log, K16, K21].
- The open-ended "Apple-style" and font-substitution exercises earned weak feedback in AE: reuse their concrete lessons, not a promise that an effect stack will pass.
