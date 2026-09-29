<!-- ui-mastery.md part 1 of 3; index: ui-mastery.md -->
# Fusion UI Mastery: production UI design library for the Resolve 21.1 Fusion page

Port of Higgsfield `ae-ui-mastery` plus the component table of `ae-build-orchestration` "AE UI Rebuilder".
Load it when a Fusion comp must show interface design: product/landing mockups, dashboards, app screens,
cards, buttons, stat tiles, lower-third chrome, UI screenshot rebuilds. It holds shipped design tokens
(look values up here, never invent them) and the Fusion construction layer: unit conversion, per-component
node recipes, shadows, layout graphs, editable-text rules and a copy-ready `.setting` builder.

Evidence tags: **[live]** measured in Resolve Studio 21.1.0.14 on 2026-09-26; **[corpus]** seen in shipped
Blackmagic or third-party `.setting` files (syntax and IDs real, our values not rendered); **[TSV]** ID
exists in `fusion-reference/data/fusion-21.1-inputs.tsv`; **[model]** a derived formula that the calibration comp (§1.8)
must confirm. **Every recipe: status: unverified (not yet rendered).** Timing assumes 30 fps as authored in
the AE source, with 24/25 fps columns where timing matters.

Workflow (same as AE):
1. Pick a **brand archetype** (§2). 2. Use its **exact tokens** (§2, §3). 3. Adapt the **component
recipes** (§5). 4. Compose a **layout pattern** (§7). 5. Convert every px value with **§1** before writing
any input. 6. Build by **`.setting` paste** (§11), render one PNG, run the checks (§12, §13).

Hard rules (the AE "editable layers" rule, in Fusion terms):
- Every label, badge, chip, button, stat and pill = a **plate** (mask on a Background, or sShape) plus a
  **separate live Text+**. Never a Loader still or generated image with the words baked in.
- Every gradient and glow is **native**: Background `Type` Gradient/Corner, Text+ gradient shading,
  Shadow node or blurred copies. Loader/MediaIn only for wordless photos/illustrations or an authorized
  brand-logo file.
- Author at a **1920x1080 design canvas in CSS px** ("pt" in the AE text = CSS px). Convert to normalized
  values; the same numbers then hold at 3840x2160.

---

## §1. UNITS: pixel spec -> Fusion inputs

### 1.1 Canvas and scale
- Design canvas `W=1920, H=1080`. UHD timeline: `k = W_comp/1920 = 2`. All normalized inputs are identical at
  UHD. Only inputs in pixel-like units scale with `k`: Background/Text+/mask `Width`/`Height` when Auto
  Resolution is off. **Blur `XBlurSize` does not** (live 2026-09-26: blur scales with frame width, size 10 =
  FWHM 30 px at 1920 and 58 px at 3840); Glow/SoftGlow `XGlowSize` presumably the same (not measured).
- Portrait mobile UI: comp 1080x1920; an iPhone design in 390-pt units scales by `k = 1080/390 = 2.769`.
  Always use the real comp `W,H` in formulas. Text+ `Size` and EllipseMask sizes are width-relative, so a
  given px font needs a larger `Size` in portrait (`x 1920/1080`).
- Resolve conforms a Fusion clip to timeline resolution. Set `UseFrameFormatSettings = 1` on every
  Background, TextPlus, RectangleMask, EllipseMask and sRender so a build authored at 1920 follows a UHD
  timeline **[corpus gotcha]**. Expressions can read the format: `comp:GetPrefs("Comp.FrameFormat.Width")`
  **[corpus]**.
- A reference screenshot of width `W_ref` needs **no SCALE factor**: normalize its measured px by `W_ref`,
  `H_ref` directly. `CornerRadius`, `CharacterSpacing` and `LineSpacing` are ratios and scale-free.

### 1.2 Conversion table (`L,T` = top-left px, `w,h` = size px, `W,H` = frame px)

| Quantity | Tool . input ID | Formula | Evidence |
|---|---|---|---|
| Position | any `Center` (Merge, Transform, TextPlus, RectangleMask, EllipseMask), Background `Start`/`End`, Transform `Pivot` | `x = px/W`, `y = 1 - py/H` (origin bottom-left, **Y up**) | [live] |
| Rect size | RectangleMask `Width`, `Height` | `w/W`, `h/H` (**each axis vs its own frame dimension**) | [live] 0.5x0.5 = 1920x1080 px on UHD |
| Rect corner | RectangleMask `CornerRadius` | `min(1, 2r/min(w,h))`; 999px pill -> 1.0 | [live] 0.2 on 1920x1080 rect = ~108 px |
| Circle | EllipseMask `Width`, `Height` | `d/W` and `d/W` (**both vs width**; equal = circle) | [live] |
| Text size | TextPlus `Size` | `K_font * font_px / W`, `K = 1.70` for Open Sans | [live] em ~= 0.587*Size*W |
| Shape system | sRectangle/sEllipse/sNGon/sStar `Translate.X`, `Translate.Y`, `Width`, `Height` | `x_c/W - 0.5`, `(H/2 - y_c)/W`, `w/W`, `h/W` (origin frame center, **all width units**) | **[live]** sRectangle W .5 H .25 T .1/.1 on 3840x2160 = 1920x960 px, +384 px right/up (2026-09-26) |
| Shape corner | sRectangle `CornerRadius` | `min(1, 2r/min(w,h))` | **[live]** 0.2 on a 1920x960 px sRectangle = ~96 px |
| Stroke | RectangleMask/sRectangle/sEllipse `BorderWidth`, sOutline `Thickness` | first guess `t/W`; whether it straddles the edge is unknown | not measured; use the Subtract ring (§4.2) for exact borders |
| Spread | ErodeDilate `XAmount` | `spread_px/W` | manual (Amount 1 = full width) |
| Feather | RectangleMask `SoftEdge`, Shadow `Softness` | `~1.18*B/W` (B = CSS blur radius, sigma = B/2) | **[live]** SoftEdge .01 at 3840 = 42 px 10-90% ramp centered on the mask edge (sigma ~16 px); Shadow Softness .01 gives about the same falloff |
| Blur | Blur `XBlurSize`, Glow/SoftGlow `XGlowSize` | `XBlurSize ~= sigma_px / (1.25*W/1920)`: width-relative, same value at HD and UHD | **[live]** Blur only (fusion-realities §2) |
| Shadow offset | Shadow `ShadowOffset` | `(0.5 + dx/W, 0.5 - dy/H)`; default {0.5,0.5} = no offset | **[live]** {0.52, 0.48} moved the shadow +77 px right, +43 px down on 3840x2160 (x in W, y in H units) |
| Layer opacity / rgba alpha | Merge `Blend` | CSS alpha 0..1 | [corpus] (Blend is a Settings-tab input; `BlendClone` mirrors it) |
| Shape fill alpha | sShape `Opacity` | CSS alpha | [TSV] |
| Tracking | TextPlus `CharacterSpacing` (Text tab mirror `CharacterSpacingClone`) | multiplier, 1 = font default; `CS ~= 1 + ls_em/adv_em` | [model] |
| Leading | TextPlus `LineSpacing` (`LineSpacingClone`) | multiplier of the font's natural line; `LS ~= css_lh / nat_lh` | [model] |
| Rotation | Transform/mask/shape `Angle` | degrees; Fusion counterclockwise with Y up, so CSS `rotate(θ)` (clockwise) -> `Angle = -θ` | **[live]** Transform Angle +30 = CCW |
| Trig in expressions | SimpleExpression | radians; `time` = frame number | [live] |

Traps: a "square" RectangleMask needs `Height = Width*W/H`; an EllipseMask circle needs `Height = Width`.
`setting-format.md` describes RectangleMask Width/Height as "1 = frame width": the live measurement wins
(each axis own dimension). Masks, Text+ and sRender default to Auto Resolution; keep it on.

### 1.3 Converter (Python, used by every snippet below)

```python
W, H = 1920, 1080                                    # DESIGN canvas, CSS px
def hx(h):  h = h.lstrip('#'); return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
def P(x, y): return (x/W, 1 - y/H)                   # any Center / Start / End / Pivot
def cr(w, h, r): return min(1.0, 2*r/min(w, h)) if r else 0.0
def rmask(L, T, w, h, r=0):                          # RectangleMask [live]
    return {"Center": P(L + w/2, T + h/2), "Width": w/W, "Height": h/H, "CornerRadius": cr(w, h, r)}
def emask(L, T, d):                                  # EllipseMask circle [live]
    return {"Center": P(L + d/2, T + d/2), "Width": d/W, "Height": d/W}
def sshape(L, T, w, h, r=0):                         # sRectangle [live-measured 2026-09-26]
    return {"Translate.X": (L + w/2)/W - 0.5, "Translate.Y": (H/2 - (T + h/2))/W,
            "Width": w/W, "Height": h/W, "CornerRadius": cr(w, h, r)}
# K is per family AND weight [live, gapfix pass, K1; from rebuild log, K20]: measure new ones with the
# connector's text.size_for_px (cached; text.set_style sizePx then uses it) or after §1.8 test 5
K_FONT = {"Open Sans/Bold": 1.70, "Helvetica Neue/Bold": 1.478, "Helvetica Neue/Light": 0.989 * 1.478}
def tsize(px, font="Open Sans/Bold"): return K_FONT.get(font, 1.70) * px / W
```

### 1.4 Worked examples (1920 design; UHD gives identical values with every px doubled)

| Element (L,T,w,h,r px) | Center | Width | Height | CornerRadius | sShape model (TX, TY, W, H) |
|---|---|---|---|---|---|
| Button 120,480,180,44,r8 | 0.109375, 0.535185 | 0.093750 | 0.040741 | 0.363636 | -0.390625, 0.019792, 0.093750, 0.022917 |
| Button inner ring (t=1): 121,481,178,42,r7 | same | 0.092708 | 0.038889 | 0.333333 | |
| Card 352,320,384,240,r12 | 0.283333, 0.592593 | 0.200000 | 0.222222 | 0.100000 | -0.216667, 0.052083, 0.2, 0.125 |
| Card inner ring (t=1): 353,321,382,238,r11 | same | 0.198958 | 0.220370 | 0.092437 | |
| Input 800,520,320,44,r6 | 0.500000, 0.498148 | 0.166667 | 0.040741 | 0.272727 | |
| Input focus ring (+3): 797,517,326,50,r9 | same | 0.169792 | 0.046296 | 0.360000 | |
| Pill 120,160,88,24,r999 | 0.085417, 0.840741 | 0.045833 | 0.022222 | 1.0 | |
| Modal 640,340,640,400,r16 | 0.5, 0.5 | 0.333333 | 0.370370 | 0.080000 | |
| Nav bar 0,0,1920,64 | 0.5, 0.970370 | 1.0 | 0.059259 | 0 | |
| Nav divider 0,63,1920,1 | 0.5, 0.941204 | 1.0 | 0.000926 | 0 | |
| Sidebar active item 16,120,224,40,r6 | 0.066667, 0.870370 | 0.116667 | 0.037037 | 0.300000 | |
| Progress track 800,600,320,8,r4 | 0.5, 0.440741 | 0.166667 | 0.007407 | 1.0 | |
| Avatar 40 at 1848,12 (EllipseMask) | 0.972917, 0.970370 | 0.020833 | 0.020833 | n/a | |

UHD check (button): 360x88 at (240,960) on 3840x2160 gives Center x `420/3840 = 0.109375`, y
`1 - 1004/2160 = 0.535185`, Width `360/3840 = 0.09375`, CornerRadius `32/88 = 0.3636`, Text+ Size for
28 px `1.70*28/3840 = 0.0124`. Same numbers.

### 1.5 Type: Size, anchors, tracking, leading

**Text+ `Size` per type token** (`1.70*px/1920`, Open Sans constant; other families: §1.8 test 5):

| px | 10 | 11 | 12 | 13 | 14 | 16 | 17 | 18 | 20 | 24 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Size | .00887 | .00976 | .01065 | .01153 | .01242 | .01420 | .01508 | .01597 | .01775 | .02130 | .02484 |

| px | 32 | 36 | 40 | 48 | 56 | 64 | 72 | 80 | 96 | 128 | 144 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Size | .02839 | .03194 | .03549 | .04259 | .04969 | .05679 | .06388 | .07098 | .08518 | .11357 | .12777 |

Font dependence **[model]**: the measured constant fits "line height (hhea ascender+descender) = 0.8 x Size x W"
for Open Sans (1.362 em line). If Fusion scales by line height, Inter (1.21 em line) would need `K ~= 1.51`,
not 1.70 (12% larger glyphs otherwise). Measure `K` per family before trusting sizes.

**Anchoring** **[live]/[corpus]**:
- Default justification centers the glyph box on `Center` (verified for single-line caps). A label centered
  in a plate: `Center` = plate center. With descenders (g, p, y) the ink box drops; if the cap band reads
  high, move `Center` down by `~0.1*font_px/H` and confirm in the render.
- Left-aligned text (Blackmagic lower-third idiom **[corpus]**): `HorizontalJustificationNew = 3`,
  `HorizontalLeftCenterRight = -1`; `Center.x` = left edge. Right-aligned: `HorizontalLeftCenterRight = 1`.
- Vertical anchor slider `VerticalTopCenterBottom` (-1..1; sign of top vs bottom unverified). Baseline
  anchoring: `CenterOnBaseOfFirstLine = 1` **[TSV, untested]**, then `y = 1 - baseline_px/H` with
  `baseline_px = cap_top_px + capRatio*font_px`.
- Cap-height ratios (font-file metrics, approximate): Open Sans .714 (matches the live .42/.587), Inter .727,
  Roboto .711, Helvetica Neue .714, SF Pro .705, IBM Plex Sans .698, JetBrains Mono .730, Space Grotesk .70.

**Tracking** **[model]**: Fusion spacing multiplies the character advance (default 1; "<1 usually overlaps").
CSS letter-spacing adds a constant, so `CS ~= 1 + ls_em/adv_em` with average advance `adv_em` ~.67 for
UI-sans caps, ~.55 for mixed case, .60 for mono. Shipped Blackmagic titles use 1.039-1.228 on caps **[corpus]**.

| Token (AE) | ls (em) | CharacterSpacing |
|---|---|---|
| Eyebrow 11px, +1.5px | +0.136 | 1.20 |
| Caps label +0.1em / +0.15em / +0.2em | +0.10 / .15 / .20 | 1.15 / 1.22 / 1.30 |
| Logo-wall label / chip caption 11px, +2px | +0.18 | 1.27 |
| Brutalist mono meta 11px, +3px | +0.27 | 1.45 (mono) |
| Body | 0 | 1.00 |
| Consumer display -0.005em | -0.005 | 0.99 |
| Display -0.02 / -0.03 / -0.04em | | 0.964 / 0.945 / 0.927 |
| Finance display -2px at 64-72px | -0.03 | 0.945 |

**Leading** **[model]**: `LS ~= css_line_height / nat_lh`, `nat_lh` = the family's hhea ascender+descender
(+lineGap) in em: Inter 1.21, Open Sans 1.362, Roboto 1.172, SF Pro ~1.19, Helvetica Neue ~1.2, IBM Plex
Sans 1.30, JetBrains Mono 1.32. Shipped display titles use LS 0.66-0.91 **[corpus]**, consistent with this.

| CSS line-height | 1.0 | 1.1 | 1.15 | 1.25 | 1.4 | 1.5 |
|---|---|---|---|---|---|---|
| Inter | 0.826 | 0.909 | 0.950 | 1.033 | 1.157 | 1.240 |
| Open Sans | 0.734 | 0.808 | 0.844 | 0.918 | 1.028 | 1.101 |
| SF Pro | 0.840 | 0.924 | 0.966 | 1.050 | 1.176 | 1.261 |
| JetBrains Mono | 0.758 | 0.833 | 0.871 | 0.947 | 1.061 | 1.136 |

Exactness rule: display headlines use **one Text+ per line** with explicit baselines (`baseline_{n+1} =
baseline_n + lh*font_px`), which is exact, edit-safe and animates per line. Paragraphs use one Text+ with
`LayoutType = 1` (Frame), `LayoutWidth` for max-width (units unmeasured; first guess `maxw/W`), `Wrap = 1`
and calibrated `LineSpacing`.

### 1.6 Crisp edges and hairlines
- Keep `L,T,w,h` integers on the 1920 grid (the 4/8 px tokens guarantee it): edges land on pixel boundaries
  at 1920 and at UHD. Write normalized values with 6 decimals; never round them to 3.
- A 1 px line at row `T`: `Center.y = 1 - (T+0.5)/H`, `Height = 1/H`. It becomes 2 px at UHD. Never go below
  1 design px.
- Transform `Size > 1` on a rasterized plate softens it. Animate up **to** 1.0, or animate vector inputs
  (mask `Width/Height`, Text+ `Size`, `sTransform` sizes). A static "scale 1.05" is built at the larger
  geometry, not with a Transform.

### 1.7 Color
- `hex/255` per channel into `TopLeftRed/Green/Blue` (Background), `Red1/Green1/Blue1` (Text+ element 1),
  `Red/Green/Blue` (sShapes, Shadow).
- Unmanaged Fusion page (default): values are display code values and merges/blurs happen on them, like a
  browser compositing CSS in sRGB. That is why web shadows and alpha tints match. With Resolve Color
  Management or a linear working space the same hex and soft shadows render differently: sample the render.
- Keep generator alpha 1 and express `rgba()` alpha with Merge `Blend` (or sShape `Opacity`). Whether
  Background `TopLeftAlpha` premultiplies is unverified.

Archetype A floats (reuse the pattern for others):

| Token | Hex | R, G, B |
|---|---|---|
| bg-canvas | #08090b | 0.0314, 0.0353, 0.0431 |
| bg-surface | #131418 | 0.0745, 0.0784, 0.0941 |
| bg-elevated | #1c1d22 | 0.1098, 0.1137, 0.1333 |
| border-default | #26282e | 0.1490, 0.1569, 0.1804 |
| border-strong | #3a3b42 | 0.2275, 0.2314, 0.2588 |
| text-primary | #fafafa | 0.9804 x3 |
| text-secondary | #a1a1aa | 0.6314, 0.6314, 0.6667 |
| text-muted | #71717a | 0.4431, 0.4431, 0.4784 |
| accent indigo | #5e6ad2 | 0.3686, 0.4157, 0.8235 |
| accent purple | #7c3aed | 0.4863, 0.2275, 0.9294 |
| success | #10b981 | 0.0627, 0.7255, 0.5059 |
| warning | #f59e0b | 0.9608, 0.6196, 0.0431 |
| danger | #ef4444 | 0.9373, 0.2667, 0.2667 |

### 1.8 Calibration comp (one render, before trusting any [model] row)

Build each test on a black Background at the working resolution, render one PNG through a Saver
(`FormatID = "PNGFormat"`, verified), measure with §12 helpers.

| # | Test | Measure | Derive |
|---|---|---|---|
| 1 | sRectangle Width .25, Height .25, Translate.X .25, Translate.Y .1 -> sRender | bbox | width-units model holds if bbox = `.25W x .25W` centered at x=`.75W`, y_top-down=`H/2 - .1W` |
| 2 | sRectangle 0.25x0.125, CornerRadius 0.5 | corner radius (diagonal scan) | expect `r = 0.5*min/2` |
| 3 | RectangleMask Solid 0, BorderWidth .002; sRectangle Solid 0, BorderWidth .002; sOutline Thickness .002 | stroke px and inside/outside split vs the solid edge | `t_px = c*value*W` |
| 4 | Hard white rect with RectangleMask SoftEdge .01; hard rect -> Blur XBlurSize 10; hard rect -> Shadow Softness .01 | 10%-90% edge width `e` on a row | `sigma = e/2.563`; store `c_soft = sigma/(value*W)`, `c_blur = sigma/value` |
| 5 | Text+ "HHHH", family F, Size 0.1 | cap height px | `K_F = 0.1*W*capRatio_F/cap_px` (Open Sans gives 1.70) |
| 6 | "HHHHHHHHHH" at CS 1.0 vs 1.2; "IIIIIIIIII" vs "WWWWWWWWWW" | width delta / 9 gaps | is spacing proportional to advance? |
| 7 | "H" newline "H" at LS 1.0 | baseline gap px | `nat_lh = gap/em_px` |
| 8 | Text+ element 2 Border Fill, ExtendHorizontal2 0 vs 0.5, Round2 1 | box width delta | Extend units (em or W) |
| 9 | Shadow ShadowOffset {0.52, 0.48} on a square | shadow shift px | confirms `(dx/W, dy/H)` |

Then CSS blur `B` maps to `SoftEdge = (B/2)/(c_soft*W_comp)` and `XBlurSize = (B/2)*k/c_blur`.

---

## §2. BRAND ARCHETYPES (pick one per design)

Tokens are verbatim from the AE library. "Fusion" lines add construction and availability notes.

### A. Modern Dark Tech (SaaS, AI, dev tools)
```
PALETTE  bg-canvas #08090b (deeper than pure black) | bg-surface #131418 (cards) | bg-elevated #1c1d22
         (modals, popovers) | border-default #26282e (subtle 1px) | border-strong #3a3b42 (hover)
         text-primary #fafafa | text-secondary #a1a1aa (zinc-400) | text-muted #71717a (zinc-500)
         accent-primary #5e6ad2 (indigo) OR #7c3aed (purple) | success #10b981 | warning #f59e0b | danger #ef4444
TYPE     "Inter" (UI), "JetBrains Mono" (code/data)
         Display 72-96 700 leading 0.95 | H1 48-56 700 leading 1.0 | H2 32-36 600 | Body 16 400 leading 1.5
         Label 13 500 letter-spacing 0 | Tiny/eyebrow 11 600 UPPERCASE letter-spacing 1.5
RADIUS   Cards 12 (most common) or 8 (tighter) | Buttons 8 | Pills 999 | Inputs 6
SPACING  4, 8, 12, 16, 24, 32, 48, 64, 96, 128
SHADOW   sm 0 1px 2px rgba(0,0,0,.06) | md 0 4px 12px rgba(0,0,0,.12) | lg 0 16px 48px rgba(0,0,0,.24)
         glow 0 0 32px rgba(94,106,210,.35) on accent CTAs
```
Fusion: text-muted #71717a is **4.12:1 on the canvas, 3.81:1 on the surface**, so it fails AA for body and
small labels (the AE note claims 4.8:1). Use #a1a1aa (7.18:1 on surface) for 11-14 px labels and keep #71717a
for >=24 px or decorative text. Radius -> CornerRadius per element (§3.3). Shadow route S1 for cards, S2
(Shadow node, colored) for the CTA glow.

### B. Trustworthy Premium Finance
```
PALETTE  bg #0a2540 (deep navy) or #ffffff | surface #163753 (dark) / #f6f9fc (light) | border #1f4068 / #e3e8ee
         text #ffffff / #0a2540 | muted #adbdcc / #425466 | accent #635bff (violet) | accent-2 #00d4ff (cyan) | green #00d924
TYPE     "Sohne", "Inter"; display weight, generous tracking | Display 64-80 700 tight tracking -2px | Body 18 400
RADIUS   Cards 8 (utilitarian), NOT 16+
SIGNATURE Gradient surfaces linear-gradient(135deg, #00d4ff, #635bff, #00d924) | 3D card hover lifts
         | subtle inner shadows on inputs
```
Fusion: 3-stop 135deg gradient = Background `Type "Gradient"`, `GradientType "Linear"`, `Start`/`End` at the
surface's top-left/bottom-right corners (§4.3), stops via `.setting` Gradient table. Inner shadow: §4.4 S5.
Hover lift: Transform Center up 4 px + shadow lg. Sohne is not installed on this Mac; Neue Haas Display is
(§10.3). Contrast: muted #adbdcc on #163753 = 6.41:1; #425466 on #f6f9fc = 7.38:1; white on #635bff = 4.70:1.

### C. Minimal Developer Monochrome
```
PALETTE  bg #000000 or #ffffff | surface #0a0a0a | border #1f1f1f / #eaeaea | text #ffffff / #000000
         muted #888 | accent minimal, occasional blue #0070f3
TYPE     "Geist Sans", "Inter" | Mono "Geist Mono", "JetBrains Mono"
RADIUS   4-8 on cards, never 16+ (geometric)
SIGNATURE aggressive monochrome | geist mono for everything numeric | single accent #0070f3 sparingly
         | hairline borders #1f1f1f
```
Fusion: hairlines = 1 px Subtract rings; #888 on #0a0a0a = 5.58:1 (passes). Mono numerals: a mono family or
Text+ `FontFeatures = "tnum"` [TSV] on the UI sans.

### D. Premium Consumer Polish
```
PALETTE  bg light #fbfbfd | bg dark #000000 (OLED) | surface light #ffffff | surface dark #1d1d1f
         text-primary #1d1d1f / #f5f5f7 | text-secondary #6e6e73 | accent #0071e3 (system blue), SPARINGLY
TYPE     "SF Pro Display" 72+ headlines, "SF Pro Text" body, Mono "SF Mono"
         Display 96 700 tracking -0.005em | Subheadline 28 400 | Body 17 400
RADIUS   Buttons 980 (full pill) | Cards 18 (continuous corner) | Modal 24
SIGNATURE vast negative space (40% empty) | tiny "Learn more ->" links in #0071e3 | ALWAYS centered hero
         text | generous 96-128px padding
```
Fusion: RectangleMask corners are circular arcs, not continuous (squircle) curves; at 18 px on UI cards the
difference is invisible, on a large phone frame use `KD_ShapeRound` or accept arcs. SF Pro is a system font
file (SFNS.ttf) that usually does not appear as a selectable family; test, else Helvetica Neue.
#6e6e73 on #fbfbfd = 4.91:1.

### E. Warm Productivity
```
PALETTE  bg-canvas #191919 / #ffffff | bg-surface #2f2f2f / #f7f6f3 (warm gray) | text #ffffff / #37352f
         muted #9b9a97 | accent brown #d97706 OR purple #9b59b6
TYPE     "Inter", "GT Walsheim" (friendly) | Body 16 with 1.5 leading
RADIUS   4-6 (utilitarian, low key)
SIGNATURE warm undertones (5-10% brown tint in grays)
```
Fusion: GT Walsheim is installed on this Mac. #9b9a97 on #2f2f2f = 4.76:1 (passes, barely).

### F. Vibrant Nostalgia (glossy gradient)
```
PALETTE  gradients everywhere (mesh backgrounds) | hot magenta #ff3e9d | electric cyan #00d4ff
         acid lime #c8ff5e | royal blue #4ea0ff | deep purple #7050ff
TYPE     "Space Grotesk" / "Space Mono"
SIGNATURE glassmorphism (rgba(255,255,255,.12) bgs with thick borders) | big chunky shapes | liquid metal
```
Fusion: mesh background = 2-3 Radial `Background` gradients merged with ApplyMode "Screen", or FastNoise with a
color gradient, slowly drifting via Offset. Glass panels: see the glass module (blurred content branch under a
mask). Space Grotesk/Mono are not installed here.

### G. Brutalist Editorial
```
PALETTE  off-white #f4f1ea (paper) | ink black #0a0a0a | single red accent #c8230a | ochre #d4a93a
TYPE     Helvetica Neue Black 144 headlines | IBM Plex Mono metadata 11 UPPERCASE letter-spacing 3
RADIUS   0 (NEVER round)
SIGNATURE asymmetric, harsh contrast, oversized text
```
Fusion: CornerRadius 0, no shadows, CS 0.93-0.96 on the 144 px headline, 1.45 on mono meta.
#0a0a0a on #f4f1ea = 17.55:1; #c8230a on #f4f1ea = 5.03:1.

---

## §3. DESIGN-SYSTEM SCALES (the invisible rules)

### 3.1 Spacing: 8 px grid
Only these values for any gap, padding, margin or offset. `x` = px/1920, `y` = px/1080 (a vertical offset in a
`Center` or a Height); sShape offsets use px/1920 on both axes.

| Token | Use | x | y |
|---|---|---|---|
| 4 | tight inline gap (icon->text, chip siblings) | .002083 | .003704 |
| 8 | small gap (related items in a row) | .004167 | .007407 |
| 12 | compact gap (list rows, item padding y) | .006250 | .011111 |
| 16 | default gap (paragraphs, card padding minimum) | .008333 | .014815 |
| 24 | section item gap (cards in a grid) | .012500 | .022222 |
| 32 | section internal padding (premium card padding x) | .016667 | .029630 |
| 48 | section separation (header -> first section) | .025000 | .044444 |
| 64 | major separation | .033333 | .059259 |
| 96 | page-level breathing room | .050000 | .088889 |
| 128 | extreme separation (rare) | .066667 | .118519 |

If you write 20, 28 or 40 px: STOP and round to 16, 32 or 48. All coordinates multiples of 4 (prefer 8). AE
source values that break this (stat-card padding 20, stats-strip padding 80, pricing "scale 1.05") are
flagged where they appear.

### 3.2 Type scale (hand-tuned display scale, not a uniform ratio)
`10 micro | 11 caption (uppercase + tracking 2px for chip labels) | 12 small | 14 body small (UI default,
button text) | 16 body | 20 body large | 24 h4 | 32 h3 | 40 h2 | 56 h1 | 72 display | 96 XL display |
128 XXL display`. Step ratios vary (~1.1 small, ~1.33 display); do NOT extend by x1.25 (the "major third"
list in the AE pairing section is superseded by this). Sizes in §1.5.
Weights: display 700 or 800 | subhead 500 | body 400 | labels/captions 500. **Max 3 weights per design.**
Line-height: display 56-128 -> 1.0 (the pairing section allows 1.0-1.1) | headings 24-40 -> 1.15 (1.15-1.25)
| body 14-20 -> 1.5 | captions 10-12 -> 1.4. LineSpacing values in §1.5.
Letter-spacing: display 48+ -0.02 to -0.04em | body 0 | small uppercase labels +0.1 to +0.2em.

### 3.3 Radius: one vibe
`0 brutalist/editorial | 2-4 utilitarian SaaS | 6-8 modern web default | 12 premium cards | 16 soft/friendly
| 24 mobile-first/playful | 32+ very rounded | 999 pill`. ONE primary radius from {0,4,6,8,12,16,24} on all
cards/panels/containers, plus 999 for pills. Two radii max.
Fusion: CornerRadius depends on the element's short side: `2r/min(w,h)`.

| r | h=24 | h=40 | h=44 | h=48 | h=56 | 240 | 400 | 560 |
|---|---|---|---|---|---|---|---|---|
| 4 | .333 | .200 | .182 | .167 | .143 | .033 | .020 | .014 |
| 6 | .500 | .300 | .273 | .250 | .214 | .050 | .030 | .021 |
| 8 | .667 | .400 | .364 | .333 | .286 | .067 | .040 | .029 |
| 12 | 1.0 | .600 | .545 | .500 | .429 | .100 | .060 | .043 |
| 16 | 1.0 | .800 | .727 | .667 | .571 | .133 | .080 | .057 |
| 24 | 1.0 | 1.0 | 1.0 | 1.0 | .857 | .200 | .120 | .086 |

Consequence: the same token gives different CornerRadius values per element. Never copy a CornerRadius
between elements of different size; recompute (or drive it by expression from a radius controller:
`2*UI_Tokens.NumberIn1/1920/min(self.Width, self.Height*1080/1920)` for RectangleMask; [model], verify).

### 3.4 Color system: value-driven hierarchy
6-8 colors total. Roles: BG canvas (very dark or very light, low chroma) | SURFACE (one step toward mid) |
SURFACE-2 elevated (one more step) | BORDER (1-2% brighter than surface) | TEXT primary | TEXT secondary
(~60% opacity of primary or brand-muted hex) | ACCENT primary (ONE vivid hue, sparingly) | ACCENT secondary
(status only: green success, red error, yellow warn).
Dark recipe: BG #0d0e12 or #0a0a0c | surface #16181f | elevated #1d2028 | border #2a2d38 | text #fafafa |
muted #8b8e98 | accent one of #6366f1, #a855f7, #10b981, #f59e0b, #ef4444.
Light recipe: BG #fafafa or #ffffff | surface #f5f5f7 | elevated #ffffff with shadow | border #e5e5e7 |
text #0a0a0c | muted #6b6f78 | same accents.
**60-30-10**: 60% BG, 30% surface/text, 10% accent. Big accent areas = wrong.
Contrast floor: body >= 4.5:1 against the surface it sits on (not the canvas); large text (>=24) and UI/icons
>= 3:1. Verified: #8b8e98 = 5.90 (canvas), 5.42 (surface), 4.98 (elevated); #6b6f78 = 4.82 on #fafafa,
4.62 on #f5f5f7. All pass.

### 3.5 Shadow scale, converted
CSS `0 dy B rgba(c, a)` = offset `dy` down, Gaussian `sigma = B/2`, opacity `a`. Fusion: offset
`dCenterY = -dy/1080`; opacity `a` -> Merge `Blend` (S1/S3) or Shadow `Alpha` (S2); softness per §1.8
(first guess `B/1920`). Max 2 shadow levels per design; default cards md, hero/elevated lg.

| Token | CSS | dCenterY / ShadowOffset.y | sigma px @1920 (@UHD) | first-guess SoftEdge / Softness | Blend/Alpha |
|---|---|---|---|---|---|
| none | flat | | | | |
| xs | 0 1 2 .10 (form inputs) | -.000926 / .499074 | 1 (2) | .00104 | .10 |
| sm | 0 2 4 .08 (rows, hover) | -.001852 / .498148 | 2 (4) | .00208 | .08 |
| md | 0 4 12 .12 (default cards) | -.003704 / .496296 | 6 (12) | .00625 | .12 |
| lg | 0 8 24 .16 (elevated, modals) | -.007407 / .492593 | 12 (24) | .0125 | .16 |
| xl | 0 16 48 .24 (hero, dropdowns) | -.014815 / .485185 | 24 (48) | .025 | .24 |
| glow | 0 0 32 accent .40 (dark CTAs) | 0 / .5 | 16 (32) | .0167 | .40 |
| A sm / A lg / A glow | .06 / 0 16 48 .24 / .35 | as sm / xl / glow | | | .06 / .24 / .35 |
| CTA example | 0 8 32 accent .35 | -.007407 | 16 (32) | .0167 | .35 |
| Button hover | 0 4 12 accent .30 | -.003704 | 6 (12) | .00625 | .30 |
| Modal | 0 24 80 .50 | -.022222 | 40 (80) | .0417 | .50 |
| Code window | 0 32 80 .50 | -.029630 | 40 (80) | .0417 | .50 |
| Pricing highlight | 0 0 40 accent .20 | 0 | 20 (40) | .0208 | .20 |
| Rebuilder default | Distance 8, Softness 24, 15-25% | -.007407 | 12 (24) | .0125 | .15-.25 |
| macOS window | Distance 0, Softness 60, 30% | 0 | 30 (60) | .03125 | .30 |

(AE Drop Shadow's 0-255 "Opacity" scale does not exist here: Fusion opacity is 0..1.)

### 3.6 Layout principles
1. **8 px grid**: every `L,T,w,h` divisible by 8 (at least 4); sizes 240, 320, 400, 480, 560, 640, 720, 800.
2. **Content max-width**: body text 640-720 px; dashboard main 1280-1440 px centered on 1920.
3. **Optical centering**: a play triangle shifts right 1-2 px; single-line button text is centered on the cap
   band (Text+ glyph-box centering already approximates this, §1.5).
4. **Vertical rhythm**: header -> 24 -> body -> 16 -> footer inside a card; 32 between cards; 64 between sections.
5. **3-2-1 hierarchy**: max 3 elements competing (headline, key visual, primary CTA), 2 supporting (subtitle,
   secondary CTA), 1 accent color on the primary CTA.
6. **Asymmetric balance** beats centering everything (except archetype D's centered hero).
7. **Negative space**: 30-50% empty; 96 px hero padding, 64 px section tops.

---

