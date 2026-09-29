<!-- ui-mastery.md part 3 of 3; index: ui-mastery.md -->
## §9. TYPOGRAPHY

### 9.1 Pairings
| UI font | Numbers/code | Use case |
|---|---|---|
| Inter | JetBrains Mono | modern SaaS / B2B dashboard |
| SF Pro Display | SF Mono | premium consumer |
| Helvetica Neue | IBM Plex Mono | editorial / brutalist |
| Roboto | Roboto Mono | Android |
| Space Grotesk | Space Mono | Y2K / futuristic |
| IBM Plex Sans | IBM Plex Mono | corporate / financial |

Max 2 families. OS look: SF Pro (macOS/iOS), Roboto (Android), Inter (modern web), Segoe UI (Windows). Never
generic Arial, never Fusion's default Open Sans by accident: set `Font`/`Style` explicitly on every Text+.

### 9.2 Editable-text rules
- **Text+ stays live**: never convert to a Loader still or `sTrace Create` shapes for final UI. `sText` is fine
  when the text must enter a shape boolean (no gradient colors on sText).
- **One Text+ per independently animated unit** (word, line, stat, button label). Do not split a static unit
  into several Text+ (edits get painful), and do not pack independently moving units into one Text+.
- Per-character motion inside one unit: `StyledTextFollower` modifier (keyframe its values; spaces count as
  characters); `UseLigatures` keeps Latin letters separate by default. With a Follower attached, the text lives
  in the Follower's input: editing `StyledText` does nothing [corpus gotcha].
- Uppercase labels: type the string in caps (no reliable text-transform); tracking via CharacterSpacing.
- Tabular numerals for counters: mono family or `FontFeatures = "tnum"` [TSV input; tag format unverified].
- Units in one row with different sizes: align baselines explicitly (§1.5), not centers.
- Edit-page reuse (Essential Graphics analog): wrap the component in a GroupOperator/MacroOperator with
  `InstanceInput`s for StyledText and colors, save under Templates/Edit/Titles; publishing is unqualified.

### 9.3 Font availability (Text+ `Font` = family string, `Style` = face string)
- Strings must match Fusion's font menu exactly: `Font = "Open Sans"`, `Style = "Extrabold"` (Open Sans spells
  it that way [corpus]); Inter static cuts name it "Semi Bold" or "SemiBold" depending on version. Weight map:
  400 Regular, 500 Medium, 600 Semi Bold/SemiBold, 700 Bold, 800 Extra Bold/ExtraBold/Extrabold.
- A missing family or style silently substitutes (behavior unverified): read back `GetInput("Font")`,
  `GetInput("Style")`, and compare rendered widths with the spec. List fonts: `fusion.FontManager.GetFontList()`
  (API stub) or the macOS font folders.
- This Mac on 2026-09-26: installed families include GT Walsheim, Helvetica Neue, Neue Haas Display, DM Sans,
  Poppins, Montserrat, Barlow, Proxima Nova, Avenir Next LT Pro, Nunito Sans; system Helvetica Neue, Avenir
  Next, Menlo, New York, SF (system files). **Not installed**: Inter (a variable TTF sits in the RiTE branding
  Drive folder), JetBrains Mono, Geist, Sohne, Space Grotesk/Mono, IBM Plex, Roboto. Substitutes: Inter ->
  DM Sans or Neue Haas Display; JetBrains/SF Mono -> Menlo; Sohne -> Neue Haas Display; Geist -> DM Sans.
  Installing fonts is the user's call; prefer static weights over variable fonts in Text+, and expect to relaunch
  Resolve before new fonts appear.

---

## §10. MEASUREMENT (rebuilding a UI screenshot)

MEASURE, do not eyeball: coords, radii, gradient stops, tiny icons and font size from a picture are the #1
cause of wrong rebuilds. Local equivalents of the AE server toolkit (Pillow + numpy):

```python
import numpy as np
from PIL import Image
ref = np.asarray(Image.open(REF).convert("RGB")).astype(int); Hr, Wr = ref.shape[:2]      # op "size" first
def crop(x, y, w, h, zoom=6, out="/tmp/crop.png"):                                        # view it with Read
    Image.fromarray(ref[y:y+h, x:x+w].astype("uint8")).resize((w*zoom, h*zoom), Image.NEAREST).save(out)
def swatch(x, y, w, h): return "#%02x%02x%02x" % tuple(np.median(ref[y:y+h, x:x+w].reshape(-1, 3), 0).astype(int))
def pixel(x, y): return "#%02x%02x%02x" % tuple(ref[y, x])
def gradient(x1, y1, x2, y2, n=5):
    return [pixel(int(x1+(x2-x1)*t), int(y1+(y2-y1)*t)) for t in np.linspace(0, 1, n)]
def radius_tl(x, y, fill_hex, tol=12):                 # bbox top-left corner (x,y); diagonal scan
    f = np.array([int(fill_hex[i:i+2], 16) for i in (1, 3, 5)])
    i = next(i for i in range(200) if np.abs(ref[y+i, x+i] - f).max() <= tol)
    return i * 3.414                                   # r = i*sqrt2/(sqrt2-1); +-3 px (r12 read 13.7), refine on a zoomed crop
def font_px(cap_px, cap_ratio=0.727): return cap_px / cap_ratio   # cap height from a zoomed crop
```
Minimum before construction: `size` once; crop-zoom every element under 40 px; `radius` for every rounded
surface; `swatch`/`pixel` for every fill, stroke and text color; `gradient` for every gradient; `font_px` for
title, body and caption tiers. Normalize by `Wr, Hr` (§1.1): no SCALE step. If the reference cannot be read
numerically, say the values are eyeballed.

Record: canvas (ref size, target comp, fps), grid (columns 4/6/8/12, gutter, outer margin, base unit 4/8),
anatomy list `E1..En` top-to-bottom with bbox `[x,y,w,h]` (top-left), content and style, each tagged with its
component archetype (§5). Be granular: every 1 px border and divider is its own plate.

---

## §11. BUILD: copy-ready code

### 11.1 `.setting` generator + one-call paste (Python; paste route verified live, this graph unverified)
```python
import time
W, H = 1920, 1080
def hx(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
def P(x, y): return (x/W, 1 - y/H)
def cr(w, h, r): return min(1.0, 2*r/min(w, h)) if r else 0.0

def _in(v):
    if isinstance(v, tuple): return "Input { Value = { %.6f, %.6f }, }" % v
    if isinstance(v, (int, float)): return "Input { Value = %.6f, }" % v
    if v.startswith("@"):                                  # "@Tool" or "@Tool.Mask"
        t, _, o = v[1:].partition("."); return 'Input { SourceOp = "%s", Source = "%s", }' % (t, o or "Output")
    if v.startswith("="): return 'Input { Expression = "%s", }' % v[1:].replace('"', '\\"')
    if v.startswith("fuid:"): return 'Input { Value = FuID { "%s" }, }' % v[5:]
    return 'Input { Value = "%s", }' % v.replace('\\', '\\\\').replace('"', '\\"')

class G:
    def __init__(s): s.t, s.n = [], 0
    def add(s, name, regid, **inp):
        x, y = 110*(s.n % 14), 45*(s.n // 14); s.n += 1
        keys = "".join("\t\t\t\t%s = %s,\n" % (k if k.isidentifier() else '["%s"]' % k, _in(v)) for k, v in inp.items())
        s.t.append("\t\t%s = %s {\n\t\t\tInputs = {\n%s\t\t\t},\n\t\t\tViewInfo = OperatorInfo { Pos = { %d, %d } },\n\t\t},\n" % (name, regid, keys, x, y))
        return name
    def raw(s, text): s.t.append(text)
    def text(s): return "{\n\tTools = ordered() {\n" + "".join(s.t) + "\t},\n}\n"

def rgb(prefix, h): return dict(zip((prefix+"Red", prefix+"Green", prefix+"Blue"), hx(h)))
def plate(g, n, L, T, w, h, r, col, soft=0.0, dy=0):
    g.add(n+"_M", "RectangleMask", UseFrameFormatSettings=1, Center=P(L+w/2, T+h/2+dy),
          Width=w/W, Height=h/H, CornerRadius=cr(w, h, r), SoftEdge=soft)
    return g.add(n, "Background", UseFrameFormatSettings=1, EffectMask="@%s_M.Mask" % n, **rgb("TopLeft", col))
def ring(g, n, L, T, w, h, r, t, col):
    g.add(n+"_Mo", "RectangleMask", UseFrameFormatSettings=1, Center=P(L+w/2, T+h/2), Width=w/W, Height=h/H, CornerRadius=cr(w, h, r))
    wi, hi, ri = w-2*t, h-2*t, max(0, r-t)
    g.add(n+"_Mi", "RectangleMask", UseFrameFormatSettings=1, Center=P(L+w/2, T+h/2), Width=wi/W, Height=hi/H,
          CornerRadius=cr(wi, hi, ri), PaintMode="fuid:Subtract", EffectMask="@%s_Mo.Mask" % n)
    return g.add(n, "Background", UseFrameFormatSettings=1, EffectMask="@%s_Mi.Mask" % n, **rgb("TopLeft", col))
def text(g, n, s, font, style, px, x, y, col, left=False, cs=1.0, K=1.70):
    kw = dict(UseFrameFormatSettings=1, StyledText=s, Font=font, Style=style, Size=K*px/W,
              Center=P(x, y), CharacterSpacing=cs, **dict(zip(("Red1", "Green1", "Blue1"), hx(col))))
    if left: kw.update(HorizontalJustificationNew=3, HorizontalLeftCenterRight=-1)
    return g.add(n, "TextPlus", **kw)
def over(g, n, bg, fg, blend=1.0): return g.add(n, "Merge", Background="@"+bg, Foreground="@"+fg, Blend=blend)

# ---- stat card on Archetype A (tokens from sections 2-3) ----
g = G()
page = g.add("Page_BG", "Background", UseFrameFormatSettings=1, **rgb("TopLeft", "#08090b"))
L, T, w, h, r = 352, 320, 384, 240, 12
sh  = plate(g, "Card_Sh", L, T, w, h, r, "#000000", soft=12/W, dy=4)        # S1 md; SoftEdge guess B/W
m   = over(g, "Page_MCardSh", page, sh, 0.12)
c   = plate(g, "Card_Fill", L, T, w, h, r, "#131418")
c   = over(g, "Card_M1", c, ring(g, "Card_Border", L, T, w, h, r, 1, "#26282e"))
c   = over(g, "Card_M2", c, text(g, "Card_Label", "REVENUE", "Inter", "Semi Bold", 11, L+24, T+24+4, "#a1a1aa", left=True, cs=1.20))
c   = over(g, "Card_M3", c, text(g, "Card_Value", "$48,210", "JetBrains Mono", "Bold", 40, L+24, T+60+14.6, "#fafafa", left=True))
xf  = g.add("Card_Xf", "Transform", Input="@"+c, Pivot=P(L+w/2, T+h/2))
out = over(g, "Page_MCard", m, xf)

path = "/abs/scratch/ui_statcard.setting"            # scratch path; ASCII text is safest
open(path, "w").write(g.text())
cc = resolve.Fusion().GetCurrentComp()               # the target comp must be current on the Fusion page
cc.Execute('comp:Paste(bmd.readfile([[%s]]))' % path)
for _ in range(40):                                  # Execute is deferred
    if cc.FindTool(out): break
    time.sleep(0.1)
cc.FindTool("MediaOut1").ConnectInput("Input", cc.FindTool(out))
```
`T+24+4` = cap-center of an 11 px label (0.36 x 11); `T+60+14.6` = cap-center of a 40 px
value whose cap top sits at T+60. Replace `K=1.70` per family after §1.8 test 5.

### 11.2 Literal `.setting` for one button (unverified)
```lua
{
	Tools = ordered() {
		Btn_M = RectangleMask { Inputs = {
			UseFrameFormatSettings = Input { Value = 1, },
			Center = Input { Value = { 0.109375, 0.535185 }, },
			Width = Input { Value = 0.09375, }, Height = Input { Value = 0.040741, },
			CornerRadius = Input { Value = 0.363636, }, },
			ViewInfo = OperatorInfo { Pos = { 0, -45 } }, },
		Btn_Fill = Background { Inputs = {
			UseFrameFormatSettings = Input { Value = 1, },
			TopLeftRed = Input { Value = 0.368627, }, TopLeftGreen = Input { Value = 0.415686, },
			TopLeftBlue = Input { Value = 0.823529, },
			EffectMask = Input { SourceOp = "Btn_M", Source = "Mask", }, },
			ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
		Btn_Label = TextPlus { Inputs = {
			UseFrameFormatSettings = Input { Value = 1, },
			StyledText = Input { Value = "Get started", },
			Font = Input { Value = "Inter", }, Style = Input { Value = "Medium", },
			Size = Input { Value = 0.012422, },
			Center = Input { Value = { 0.109375, 0.535185 }, }, },
			ViewInfo = OperatorInfo { Pos = { 0, 45 } }, },
		Btn_ML = Merge { Inputs = {
			Background = Input { SourceOp = "Btn_Fill", Source = "Output", },
			Foreground = Input { SourceOp = "Btn_Label", Source = "Output", }, },
			ViewInfo = OperatorInfo { Pos = { 110, 0 } }, },
		Btn_Xf = Transform { Inputs = {
			Input = Input { SourceOp = "Btn_ML", Source = "Output", },
			Pivot = Input { Value = { 0.109375, 0.535185 }, }, },
			ViewInfo = OperatorInfo { Pos = { 220, 0 } }, },
		Btn_Glow = Shadow { Inputs = {
			Input = Input { SourceOp = "Btn_Xf", Source = "Output", },
			ShadowOffset = Input { Value = { 0.5, 0.492593 }, },
			Softness = Input { Value = 0.0167, },
			Red = Input { Value = 0.368627, }, Green = Input { Value = 0.415686, },
			Blue = Input { Value = 0.823529, }, Alpha = Input { Value = 0.35, }, },
			ViewInfo = OperatorInfo { Pos = { 330, 0 } }, },
	},
}
```
Merge `Btn_Glow` over the page; a gradient stop table goes in as
`Gradient = Input { Value = Gradient { Colors = { [0] = { 0, 0.831, 1, 1 }, [0.5] = { 0.388, 0.357, 1, 1 }, [1] = { 0, 0.851, 0.141, 1 } } }, }`
(Archetype B signature) with `Type = Input { Value = FuID { "Gradient" }, }`.

### 11.3 Direct API edits (retoken, tweak)
```python
cc.SetActiveTool(None)                                # before EVERY AddTool on the Fusion-page comp [live trap]
t = cc.FindTool("Card_Fill")
for k, v in zip(("TopLeftRed", "TopLeftGreen", "TopLeftBlue"), hx("#16181f")): t.SetInput(k, v)
cc.FindTool("Card_Label").SetInput("Center", {1: 0.195833, 2: 0.677778})   # Point as {1:x, 2:y}
ok = cc.FindTool("Page_MCard").ConnectInput("Foreground", cc.FindTool("Card_Xf"))
assert ok, "ConnectInput returned False: check for loops or stray auto-merges"
```

### 11.4 Build sequence
1. Orient: confirm the target timeline item comp is current on the Fusion page; never a client project.
2. Tokens: archetype, page radius, BG/surface/border, accent, font pair, type top size, spacing rhythm,
   shadow depth (§13 order). Convert with §1.
3. Build bottom-up by Z-order: page BG -> surfaces (header, sidebar, cards, each named) -> shadows under their
   component -> strokes/dividers -> text -> buttons (plate + label) -> icons -> archetype effects (§7.8) on the
   final merge.
4. Repeating components: one row/card as a named subgraph, copy by generating it N times from the script
   (names suffixed 1..N), or `Fuse.Duplicate` for identical static rows.
5. Name semantically; no default `Background3`/`Text1` names left.
6. Connect the final merge to `MediaOut1.Input`; render a still (§12).

---

## §12. UI ANIMATION PATTERNS (Fusion mechanisms)

Keep 2-3 hero animations max; the rest simply appear. Easing: entrances ease-out `cubic-bezier(0,0,0.2,1)`,
moves ease-in-out `(0.4,0,0.2,1)`; Python handles (verified mapping) `RH = {x1*D, y1*V}`,
`LH = {(x2-1)*D, (y2-1)*V}`. Point inputs never take a BezierSpline: drive them by expression from a keyed
number (or XYPath). Detailed easing lives in the animation module.

**Progress rig** (one keyed number per component, everything else by expression [live patterns]):
```
Card1_Anim (Custom) NumberIn1: keys 0 -> 1 over D frames, eased
Card1_Xf.Center    = "Point(0.5, 0.5 - (1 - Card1_Anim.NumberIn1) * 30/1080)"     -- fade-up 30 px
Page_MCard1.Blend  = "Card1_Anim.NumberIn1"                                       -- opacity 0 -> 1
Card2_Anim.NumberIn1 = "Card1_Anim:GetValue('NumberIn1', time - 4)"               -- stagger 4 f, no extra keys
```

| Element | AE timing (30 fps) | 24 fps | 25 fps | Fusion construction |
|---|---|---|---|---|
| Card entrance (R1 fade-up) | Opacity 0->1 + Y +30->0 px over 12 f, ease-out, stagger 4 f | 10 f, 3 f | 10 f, 3 f | progress rig above |
| Counter / stat (R13) | count over the entrance | | | `Card_Value.StyledText = "Text(string.format('$%d', math.floor(48210*Stat_Anim.NumberIn1)))"` (Text() with math.floor is [corpus]; string.format unverified); tabular figures |
| Progress bar | width 0 -> target over 24 f, ease-out | 19 f | 20 f | `Bar_FillM.Width = "0.166667*Bar_Anim.NumberIn1"`, `Center = "Point(0.416667 + self.Width/2, 0.440741)"` |
| Line chart draw | Trim End 0->100% over 30-45 f, ease-in-out | 24-36 f | 25-38 f | `WriteLength` 0 -> 1 on PolylineMask/sOutline |
| Bar chart | Scale Y 0->1, 4 f offset per bar | 3 f | 3 f | bar `Height` from 0, bottom pinned (§5.13), `GetValue(time - 4*i)` stagger |
| Cursor blink (R4) | on/off every 0.25 s | | | caret Merge `Blend = "iif(time % 15 < 7.5, 1, 0)"` (30), `iif(time % 12 < 6, 1, 0)` (24), `iif(time % 12.5 < 6.25, 1, 0)` (25) |
| Click feedback | Scale 1 -> .95 -> 1 over 6 f, hard cut + white flash | 5 f | 5 f | `Btn_Xf.Size` keys (Pivot = button center); white plate with the button mask, Blend .25 -> 0 over 3 f |
| Modal entrance | backdrop 0 -> .6 over 8 f; modal scale .92 -> 1 + opacity 0 -> 1 over 12 f, ease-out | 6 f, 10 f | 7 f, 10 f | `Page_MBackdrop.Blend` keys (anatomy value .7 if the brief follows the modal spec); `Modal_Xf.Size` .92 -> 1 (never above 1); page merge Blend |
| Toast / notification | slide in from top (R3), hold 90 f, slide out | hold 72 f | hold 75 f | `Toast_Xf.Center = Point(0.5, 0.5 + (1 - p)*(toast_h + 24)/1080)` |
| Tab switch | underline X to the new tab over 12 f, ease-in-out; contents crossfade 8 f | 10 f, 6 f | 10 f, 7 f | underline `Center = Point(xA + (xB - xA)*Tab_Anim.NumberIn1, y)`; two content branches, Merge Blend |

Motion blur on UI moves: Transform `MotionBlur 1`, `Quality 4-8` preview, `ShutterAngle 180`.

---

## §13. HIERARCHY OF DECISIONS and PRE-RENDER CHECK

Decide in this order, then lay out, and every value comes from these tokens:
1. Page radius: one of {4, 8, 12, 16, 24} (+999 pills). 2. Comp BG, then surface, surface-2, border.
3. ONE accent. 4. Font pairing: max 2 families; confirm both are installed (§9.3). 5. Type-scale top (56, 72
or 96 = hero). 6. Spacing rhythm: inside cards 24, between cards 32, between sections 64. 7. Shadow depth: none,
md or lg, one value (+ glow only on the CTA). 8. Now lay out. Tempted by 22 px? Round to 24.

Pre-render checklist:
```
[ ] Every spacing value in {4, 8, 12, 16, 24, 32, 48, 64, 96}; every type size in {10,11,12,14,16,20,24,32,40,56,72,96,128}
[ ] Every radius in {0,4,6,8,12,16,24,999}; at most 2 radii; CornerRadius recomputed per element (2r/min(w,h))
[ ] At most 2 families, 3 weights, 2 shadow depths; 1 accent on ~10% of pixels, repeated in ~3 places
[ ] No coordinate off the 4 px grid; normalized with the right axis (RectangleMask h/H, EllipseMask d/W, Text+ Size/W)
[ ] UseFrameFormatSettings = 1 on every generator, mask and sRender
[ ] Every label/badge/chip/stat is a plate + a live Text+ (no baked text); every gradient/glow native
[ ] Contrast computed against the actual surface (section 8), not assumed
[ ] Negative space generous; hero obviously largest; asymmetric unless the archetype says centered
[ ] Fonts read back correctly (Font/Style) and rendered widths plausible
[ ] Nodes named <Component>_<Part>; no stray Merge1..N from auto-connect; MediaOut1 fed by the final merge
```

Close the loop (measure -> build -> AUDIT -> fix): render a PNG with a Saver (`FormatID "PNGFormat"`,
`comp.Render({"Start": f, "End": f, "Wait": True})`, verify the file exists and view it), then:
```python
import numpy as np
from PIL import Image
def lab(a):
    c = a/255.0; c = np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
    xyz = c @ np.array([[.4124, .3576, .1805], [.2126, .7152, .0722], [.0193, .1192, .9505]]).T / [.95047, 1, 1.08883]
    f = np.where(xyz > 216/24389, np.cbrt(xyz), (24389/27*xyz + 16)/116)
    return np.stack([116*f[..., 1]-16, 500*(f[..., 0]-f[..., 1]), 200*(f[..., 1]-f[..., 2])], -1)
def audit(render, ref, flag=10.0):                      # 16x9 grid of 60 px cells at 960x540
    a, b = (np.asarray(Image.open(p).convert("RGB").resize((960, 540))).astype(float) for p in (render, ref))
    cells = np.linalg.norm(lab(a) - lab(b), axis=-1).reshape(9, 60, 16, 60).mean((1, 3))
    worst = np.dstack(np.unravel_index(np.argsort(cells, None)[::-1][:5], cells.shape))[0]*60
    return dict(meanDE=cells.mean(), flaggedPct=100*(cells > flag).mean(), worst_yx=worst.tolist(),
                ok=cells.mean() <= 8 and (cells > flag).mean() <= 0.05)
def bbox_of(png, hex_col, tol=6):                        # the sourceRectAtTime check, in render px
    a = np.asarray(Image.open(png).convert("RGB")).astype(int)
    ys, xs = np.nonzero(np.abs(a - [int(hex_col[i:i+2], 16) for i in (1, 3, 5)]).max(2) <= tol)
    return xs.min(), ys.min(), xs.max()+1-xs.min(), ys.max()+1-ys.min()
```
Gate (AE values): `flaggedPct <= 5%` and `meanDE <= 8` (cell flag threshold 10 is this port's choice).
Bounds: every plate's `bbox_of` equals spec `x k` within 1 px; text widths from DataWindow (§4.6) inside
their containers. A title overrunning its card means the font/size/copy is wrong: fix the source value,
not the container. Then a vision pass on the PNG (layout sense, copy, alignment, rhythm), fix the specific
worst cells (re-measure that region), re-audit. If meanDE stops dropping for two passes, re-measure instead of
nudging.

---

### Local Higgsfield connector revision (2026-09-26)

- Tokens are for net-new design. When rebuilding a reference or a brand system, extract its
  spacing, type, palette, radii, strokes and elevation first and preserve measured dimensions;
  do not round a measured 22 px to 24. Align optically where grid arithmetic looks wrong (round
  glyphs and play icons sit visibly off-center when mathematically centered).
- One direction per piece (dark tech, editorial monochrome, warm consumer, premium finance...);
  do not mix their type and surface conventions without intent.
- Editability test before delivery: in a temporary duplicate, put a longer label and an
  alternate image into one component and render; padding, container fit and alignment must
  follow (06 DataWindow idiom) without animated layout jitter. Restore.
- Keep source defaults (macro `InstanceInput` `Default`, `CTRL` values) distinct from instance
  overrides; expose a small semantic control set (repeated colors, radius, spacing) and leave
  component internals nested but findable.
- Judge legibility at final frame size (render the PNG at comp resolution and view it at 1:1 or
  downscaled to the delivery size), never from a zoomed-in viewer.

## §14. DON'TS and FAILURE LESSONS

Design (from AE, still true):
- Five radii, mixed 20/24 paddings, four weights, drop shadows on text in clean UI, centering everything,
  full-width body text, a button touching a card edge, accent on >10% of pixels, 2+ glows, random positions
  (37, 113 px). Snap to the grid; token values only.
- Skipping 1 px borders and dividers (80% of what makes UI feel real); perfectly clean premium rectangles with
  no subtle shadow; 0-radius modern UI (measure radii; only fall back to 8 web / 12-16 mobile if unmeasurable);
  Glow on clean SaaS; animating every element; unnamed layers/nodes.
- A screenshot pasted as footage is not a rebuild. A generated plate with its label baked in is the
  "labelled plate came back flat" bug.

Fusion-specific:
- **Pixels in normalized inputs** (Center 120 instead of .0625): the element leaves the frame.
- **Wrong axis**: RectangleMask `Height = h/W` (must be h/H); EllipseMask `Height = d/H` (must be d/W); copying
  CornerRadius between different-size elements; `CornerRadius = r_px`.
- **Assuming sRectangle behaves like RectangleMask**: its size units are unmeasured and probably width-based on
  both axes. Run §1.8 test 1 before a shape-system build.
- **Blur Size as pixels**, BorderWidth as an exact CSS border, SoftEdge as CSS blur: all uncalibrated.
- **Scaling rasterized UI above 1.0** with Transform (soft plates and text). Build at the final size.
- **Glow/SoftGlow for a CSS box-shadow glow**: it blooms the label too. Use Shadow (colored) or S1.
- **AddTool on the Fusion-page comp without `comp.SetActiveTool(None)`**: silent auto-wiring, stray Merges,
  later `ConnectInput` returns False. Prefer the `.setting` paste for whole components; check every
  ConnectInput return.
- **Treating `comp.Execute` as synchronous**: poll `FindTool` after a paste.
- **Paste on a non-current comp**: returns False and creates nothing.
- **Keying a Point with BezierSpline** (Center): use expressions from a keyed number, XYPath or PolyPath.
- **Editing StyledText under a Follower**: the text lives in the Follower.
- **Hyphens or spaces in node names**: silently stripped, expressions break.
- **Trusting archetype muted grays**: #71717a fails AA on its own dark surfaces (3.81-4.12); white on #6366f1
  (4.47) and on #10b981 (2.54) fail at body size.
- **Font fallback**: a missing Inter or Style name renders as something else; widths and layout drift.
- **Color management on**: hex values and soft shadows no longer match the web look; sample the render.
- **Forgetting UseFrameFormatSettings = 1**: a 1920 build renders small or cropped in a UHD timeline.
- **Status colors as accents**, accent text on tinted plates without a contrast check.

Unverified IDs and behaviors in this module: Text+ element 2-8 inputs (`ElementShapeN`, `LevelN`,
`ExtendHorizontalN`, `ExtendVerticalN`, `RoundN`, `RedN/GreenN/BlueN/AlphaN`, `OpacityN`, `ThicknessN`,
`OffsetN`, `SoftnessXN`) are [corpus] only, not in the TSV; ResolveFX DropShadow params [corpus]; MultiMerge
`LayerN.*` [corpus]; `Output[time].DataWindow` (templates use `Output[0]`); Shadow `OutputMode` index order;
`CenterOnBaseOfFirstLine`, `FontFeatures` tag syntax; Transform Pivot/Center coupling; all sShape units.
