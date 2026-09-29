# Native layers

All conversions use the frame canvas (W x H px, the frame's local size) from the main skill.
Positions: `x = px/W`, `y = 1 - py/H` (Figma y points down). Recipes are
**status: unverified (not yet rendered)** except where marked [verified live 2026-09-26] (converter
units, gradient points, shadow softness, text spacing calibration, all on a 3840x2160 comp).

## Figma feature -> Fusion construction

| Figma | Fusion | Conversion |
|---|---|---|
| Rectangle, uniform radius | `Background` fill + `RectangleMask` on its `EffectMask` | `Center` = rect center; `Width = w/W`, `Height = h/H`; `CornerRadius = r/(min(w,h)/2)` (realities §2) |
| Rectangle, per-corner radii, smoothing | `PolylineMask` from `fillGeometry` (converter below) | never approximate with one radius |
| Ellipse | `EllipseMask` | `Width = w/W`, `Height = h/W` (both width-relative) |
| Vector / boolean result | `PolylineMask` per subpath (holes: second mask with `PaintMode` "Subtract", or even-odd per winding) or `sPolygon` + `sBoolean` (`Operation` Union/Subtract/Intersection/Xor) -> `sRender` | converter below; sShape Y is in **width** units, so divide Y by W for sPolygon |
| Solid fill | `Background` `Type` "Solid", `TopLeftRed/Green/Blue/Alpha` | hex/255; paint opacity x layer opacity into alpha or Merge `Blend` |
| Linear/radial gradient fill | `Background` `Type` "Gradient", `GradientType` "Linear"/"Radial", `Start`/`End` points, `Gradient` stops in `.setting` | handle positions from `gradientHandlePositions` (node space) -> canvas px -> normalized; keep every stop and its alpha; `GradientInterpolationMethod` RGB unless the design needs otherwise. [verified live 2026-09-26] `Start`/`End` are normalized frame points (Y up): first stop exactly at `Start`, last at `End`, 0.5 midway, clamped beyond both |
| Multiple fills (paint stack) | one Background per paint, merged bottom to top in stack order | each with its own blend mode |
| Blend modes | Merge `ApplyMode`: MULTIPLY "Multiply", SCREEN "Screen", OVERLAY "Overlay", DARKEN "Darken", LIGHTEN "Lighten", COLOR_DODGE "Color Dodge", COLOR_BURN "Color Burn", HARD_LIGHT "Hard Light", SOFT_LIGHT "Soft Light", DIFFERENCE "Difference", EXCLUSION "Exclusion", HUE/SATURATION/COLOR/LUMINOSITY same names, LINEAR_BURN "LinearBurn", LINEAR_DODGE "LinearDodge" | PASS_THROUGH on a group = no group-level Merge scope |
| Stroke center/inside/outside | `sOutline` (`Thickness` in width units = weight/W) on the shape path; inside = outline `sBoolean` Intersection with the fill shape; outside = Subtract | or a mask pair (outer `BorderWidth` +, inner `BorderWidth` -) for rectangles |
| Drop shadow | `Shadow` tool (`ShadowOffset` = (0.5 + dx/W, 0.5 - dy/H), `Softness` ~ 1.18 x radius/W [corrected live 2026-09-26: the earlier 1.18 x (radius/2)/W gave half the blur: for radius 40 px it measured a 26 px 10-90 % ramp, a Gaussian sigma of 10 px instead of 20], `Red/Green/Blue/Alpha`), `OutputMode` 1 merged under the element | spread: `ErodeDilate` on the shadow alpha (`Amount` = spread/W); calibrate softness by render |
| Inner shadow | shadow of the inverted alpha, offset, blurred, clipped by the element (Merge "In") | build once, reuse |
| Layer blur | `Blur` on the element branch (`XBlurSize` ~ sigma_px/(1.25 x W/1920), sigma ~ radius/2) | calibrate by render |
| Background blur | blur of the backdrop branch masked by the element shape | glass looks: fusion-motion-design liquid-glass |
| Image fill | `Loader`/`MediaIn` -> fit Transform -> masked by the node shape | FILL = cover, FIT = contain, CROP = explicit transform, TILE = Transform `Edges` Wrap with `Size` |
| Mask (`isMask`) | the mask node's alpha as `EffectMask` or Merge "In" for the siblings above it in the same parent | keep mask and masked content in one group scope |
| Clip content | frame/group rect as `EffectMask` on the group's final Merge | |
| Group opacity | one Merge `Blend` (or Background alpha) on the group's final Merge, applied once | never multiply into every child as well |

## Paths from Figma geometry (tested converter)

`fillGeometry[i].path` is SVG path data (M, L, H, V, C, Q, Z) in the node's space. Transform points to
canvas px with the node's absolute transform (full affine for points, linear part only for handles:
see geometry-and-hierarchy), then convert. Fusion polyline points are offsets from the tool's `Center`
in normalized width/height units; handles `LX,LY` (in) and `RX,RY` (out) are relative to their point,
as AE tangents are. Quadratic segments become cubic (control points at 2/3). One Fusion polyline per
subpath.

```python
import re
def parse(d):
    toks = re.findall(r'[MLHVCQZmlhvcqz]|-?\d*\.?\d+(?:e-?\d+)?', d)
    subs, cur, i, cmd, pos, start = [], None, 0, None, (0.0, 0.0), (0.0, 0.0)
    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]): cmd = toks[i]; i += 1
        if cmd in 'Zz':
            if cur: cur['closed'] = True
            pos = start; cmd = None; continue
        rel = cmd.islower(); c = cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if c == 'M':
            x, y = float(toks[i]) + ox, float(toks[i+1]) + oy; i += 2
            cur = {'pts': [[x, y, None, None]], 'closed': False}; subs.append(cur)
            pos = start = (x, y); cmd = 'l' if rel else 'L'; continue
        if c in 'LHV':
            if c == 'L': x, y = float(toks[i]) + ox, float(toks[i+1]) + oy; i += 2
            elif c == 'H': x, y = float(toks[i]) + ox, pos[1]; i += 1
            else: x, y = pos[0], float(toks[i]) + oy; i += 1
            cur['pts'].append([x, y, None, None])
        elif c in 'CQ':
            n = 6 if c == 'C' else 4
            v = [float(t) for t in toks[i:i+n]]; i += n
            if c == 'Q':
                qx, qy, x, y = v[0]+ox, v[1]+oy, v[2]+ox, v[3]+oy
                c1 = (pos[0] + 2/3*(qx-pos[0]), pos[1] + 2/3*(qy-pos[1]))
                c2 = (x + 2/3*(qx-x), y + 2/3*(qy-y))
            else:
                c1, c2, (x, y) = (v[0]+ox, v[1]+oy), (v[2]+ox, v[3]+oy), (v[4]+ox, v[5]+oy)
            cur['pts'][-1][3] = c1
            cur['pts'].append([x, y, c2, None])
        pos = (x, y)
    for s in subs:   # a closing point that repeats the first: keep its in-handle, drop the duplicate
        p = s['pts']
        if s['closed'] and len(p) > 1 and abs(p[-1][0]-p[0][0]) < 1e-9 and abs(p[-1][1]-p[0][1]) < 1e-9:
            p[0][2] = p[-1][2]; p.pop()
    return subs

def to_fusion(subs, W, H, cx=0.5, cy=0.5, yscale=None):
    """PolylineMask: yscale None (Y / H). sPolygon: yscale=W (sShapes use width units)."""
    ys = yscale or H
    out = []
    for s in subs:
        rows = []
        for x, y, hin, hout in s['pts']:
            X, Y = x/W - cx, (H - y)/ys - (cy if ys == H else 0.5*H/ys)
            r = f'{{ X = {X:.6f}, Y = {Y:.6f}'
            if hin:  r += f', LX = {(hin[0]-x)/W:.6f}, LY = {-(hin[1]-y)/ys:.6f}'
            if hout: r += f', RX = {(hout[0]-x)/W:.6f}, RY = {-(hout[1]-y)/ys:.6f}'
            if not hin and not hout: r += ', Linear = true'
            rows.append(r + ' }')
        out.append('Polyline { Closed = %s, Points = { %s } }'
                   % ('true' if s['closed'] else 'false', ', '.join(rows)))
    return out
```
Tested: a 200x100 rounded rectangle with cubic corners and one quadratic corner on a 1920x1080 canvas
converted to 8 points; the Bezier midpoint rebuilt from the Fusion values matched the SVG midpoint
exactly (294.142, 55.858), in both modes (mask units and `yscale=W` sShape units with a center origin).
[verified live 2026-09-26] Fusion reads those numbers as assumed: a rounded rectangle path (cubic and
quadratic corners) converted both ways and pasted as a `PolylineMask` on a Background and as an
`sPolygon` -> `sRender` rendered with the exact pixel bbox of a 4x-supersampled raster of the SVG path
and IoU 0.9996 (48 differing edge pixels at UHD) for each. Use the output as `Polyline = Input { Value = <text> }` on a `PolylineMask`
(realities §8: its animated shape input is `Polyline`) inside the frame's `.setting`.

Rules that stay from the AE original: keep separate paint regions, winding, holes, stroke alignment and
paint order; parametric masks only when their geometry matches; never replace unsupported segments with
straight lines; resolved boolean geometry is the visible result once, its operands are provenance.

## Editable text

- `TextPlus` with the source `characters`, `Font` (family) and `Style` exactly as Text+ lists them
  (glyph check in fusion-motion-design 14), color in `Red1/Green1/Blue1`, alignment
  (`HorizontalJustificationNew`, value order unverified: render), `LayoutType` Text Box for fixed-width
  text with `LayoutWidth`/`LayoutHeight` (canvas fractions) and `Wrap` 1, point layout for auto-width.
- Size: `Size ~= 1.70 x font_px / W` measured for Open Sans; other fonts differ, so render once and
  scale by the measured cap-height ratio against the Figma render.
- Baseline vs box origin: Figma's text node box includes line height; Text+ `Center` places the glyph box
  center (realities §2). Compare measured text bounds (alpha bbox of a render) with the source line box
  without editing the text.
- Letter spacing and line height: Text+ `CharacterSpacing` and `LineSpacing` are multipliers (default
  1). [measured live 2026-09-26, Open Sans Bold, Size 0.1, W 3840] `CharacterSpacing` adds
  (CS - 1) x `Size` x W px per letter gap (1.1 widened ten H's by 346 px = 38.4 px per gap), so Figma
  letterSpacing L px -> `CS = 1 + L/(Size x W)`, and L % of font size -> `CS ~= 1 + 0.587 x L/100`.
  `LineSpacing` scales the baseline-to-baseline distance, which is 0.80 x `Size` x W at 1.0 for Open
  Sans (1.36 em, the font's own line gap), so Figma lineHeight px -> `LS = lineHeight/(0.80 x Size x W)`.
  The default distance is font-dependent: re-measure it per font and store the factor in the transfer
  record. Keep kerning on (`UseFontKerning` 1).
- Styled ranges: separate Text+ runs laid out side by side only when layout and behavior still meet
  the request; otherwise `StyledTextCLS` per-character overrides (behavior on paste unverified). Report
  missing fonts or unsupported mixed styles before choosing.
