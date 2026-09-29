<!-- ui-mastery.md part 2 of 3; index: ui-mastery.md -->
## §4. CONSTRUCTION PRIMITIVES

### 4.1 Which plate system

| Need | Use | Why |
|---|---|---|
| Rect/rounded plates, cards, bars, dividers, rings, soft shadows | **Background + RectangleMask** (`Background.EffectMask <- RectangleMask.Mask`) | qualified plate pattern in the skill; units measured [live]; mask `SoftEdge` gives shadows; `Level`, `PaintMode` combine; DoD shrinks to the mask so merges stay cheap |
| Circles, avatars, dots, traffic lights | **Background + EllipseMask** | measured; circle = equal Width/Height |
| Icons, compound shapes, booleans (cut-outs, rings), repeated grids, arcs (donuts), path draw-on | **sShape chain -> sRender** (sRectangle/sEllipse/sNGon/sStar -> sBoolean/sMerge/sOutline/sDuplicate/sGrid/sTransform -> sRender) | vector, resolution independent, many shapes in one raster; units unmeasured, run §1.8 tests 1-3 first |
| Gradient-filled shape | **sRender -> BitmapMask.Image -> Background(Gradient).EffectMask** | Blackmagic idiom [corpus]; sShapes and sText have no gradient fill |
| Chip/tag/button whose box must follow editable text | **Text+ Border Fill element** or a mask sized by **DataWindow expression** (§4.6) | the Fusion `sourceRectAtTime`/autoFitPill |
| Text | **TextPlus** (MultiText for static tables/CSV lists) | live, per-character modifiers |

### 4.2 Fill and exact border (ring)
- **Fill**: `X_M = RectangleMask {Center, Width, Height, CornerRadius}` -> `X_Fill = Background {UseFrameFormatSettings 1,
  TopLeftRed/Green/Blue, EffectMask <- X_M}`.
- **Exact inside border** (CSS `border: t solid`, drawn inside the box): outer mask (w,h,r) -> inner mask
  (`w-2t, h-2t, r_in = max(0, r-t)`, same Center) with `EffectMask <- outer` and `PaintMode = "Subtract"`
  [TSV option; corpus idiom] -> border Background. Inner CornerRadius uses the inner size:
  `2*(r-t)/min(w-2t, h-2t)`. Order: fill, then ring merged over it (CSS paints the background under the border).
- **rgba border** (pill `1px rgba(accent,.3)`): ring Background in the accent color, its Merge `Blend = 0.3`.
- **sShape alternative**: `sBoolean {Input1 <- outer sRectangle, Input2 <- inner sRectangle, Operation = "Subtract"}`
  -> sRender; color on the sBoolean (`Red/Green/Blue`, Style Mode Replace).
- Avoid `BorderWidth`/`sOutline` for spec-exact 1 px borders until test 3 shows where the stroke sits. They are
  fine for decorative outlines and draw-on (`WritePosition`/`WriteLength`, Solid 0).

### 4.3 Gradients
- **2-stop 135deg across a card**: Background `Type = "Gradient"`, `GradientType = "Linear"`,
  `Start = P(L, T)`, `End = P(L+w, T+h)`, masked by the card mask. Stops: `.setting`
  `Gradient = Input { Value = Gradient { Colors = { [0] = { r,g,b,1 }, [0.5] = {...}, [1] = { r,g,b,1 } } } }`
  [corpus format]. A Python `SetInput` form for Gradient values is unverified: paste it.
- CSS angle mapping: `to right` Start `P(L, T+h/2)` End `P(L+w, T+h/2)`; `180deg` (top->bottom) Start
  `P(L+w/2, T)` End `P(L+w/2, T+h)`; `135deg` top-left -> bottom-right (exact for squares; CSS "magic corners"
  on non-square boxes differ slightly).
- Radial glow/mesh: `GradientType = "Radial"`, Start = center, End = radius point; transparent outer stop.
- Scrolling/animated gradient: animate `Offset` with `Repeat = "Repeat"` or `"Ping-Pong"`; raise `SubPixel` if
  repeat edges shimmer. Stripes/scanlines: Start/End a few px apart with Repeat (Blackmagic callout uses
  `Start {0.5,0.5}`, `End {0.503,0.5}`, Ping-Pong) [corpus].
- Gradient text: Text+ `Type1 = 2`, `ShadingGradient1 = Gradient {...}`, `ShadingMappingLevel1` (Text/Line/
  Word/Character) [TSV].

### 4.4 Soft shadows: routes and choice

| Route | Graph | Use when | Notes |
|---|---|---|---|
| **S1 mask shadow** | `Sh_M = RectangleMask(same geometry, Center.y - dy/H, SoftEdge)` -> `Sh = Background(shadow color)` -> `Merge(BG=page, FG=Sh, Blend=a)` under the component | rect/rounded components (cards, modals, buttons, windows) | no dependency on rendered alpha; 3 nodes; geometry can be expression-linked: `Sh_M.Width = "Card_M.Width"`, `Center = "Point(Card_M.Center.X, Card_M.Center.Y - 0.003704)"` (`.X` accessor unverified) |
| **S2 Shadow node** | `component -> Shadow {ShadowOffset, Softness, Red/Green/Blue, Alpha, OutputMode 0}` -> page Merge FG | any alpha shape incl. text, icons, assembled components; colored glows (offset 0, accent color) | one node; output 0 = image with its shadow (manual order image+shadow / shadow only; index inferred). Shipped: `ShadowOffset {0.505,0.496}`, `Softness 0.0063`, `Blend 0.5` [corpus]. Use `Alpha` for density, keep `Blend` 1 |
| **S3 blurred offset copy** | `component -> Sh_Xf (Transform Center 0.5, 0.5-dy/H) -> Sh_Blur (Blur XBlurSize) -> BitmapMask.Image`, `BitmapMask -> Background(color).EffectMask` -> Merge under with `Blend = a` | calibrated exact sigma, CSS spread (insert `ErodeDilate XAmount = spread/W` before the blur), stacked two-layer shadows (e.g. `0 1 2 .06` + `0 4 12 .12`) | most control, most nodes |
| **S4 Text+ element** | Text+ element 3 ("Black Shadow" preset name) `Enabled3 1`, `Offset3`, `SoftnessX3/Y3`, `Opacity3` | text over live footage only | pro UI rule: no text shadows in clean UI; over busy video, legibility wins |
| **S5 inset shadow** (finance inputs) | `In_A = field mask (hard)` -> `In_B = same geometry, Center.y - dy/H, SoftEdge, PaintMode "Subtract", EffectMask <- In_A` -> Background black, Merge Blend .06-.10 | "subtle inner shadows on inputs" | band along the top inside edge; AE's negative-distance trick |
| **Focus ring** | rect `w+6, h+6, r+3` accent plate, Merge `Blend .15`, behind the field; border recolored to accent | CSS `0 0 0 3px rgba(accent,.15)` | a spread ring with no blur: never a Glow |

Default: S1 for rect components, S2 for everything else and for colored glows. Do not use the Glow/SoftGlow
tools for CSS glows: they bloom the whole element including its label. ResolveFX Drop Shadow
(`ofx.com.blackmagicdesign.resolvefx.DropShadow`, params `shadowStrength`, `shadowAngle`, `ShadowDistance`,
`shadowBlur`, `shadowColorRed/Green/Blue`, image input `Source`) exists [corpus, not in TSV]; units unverified.

### 4.5 Component assembly (the precomp analog) and its animation handle
```
X_Fill (masked Background: full-frame, transparent outside) -> X_M1.Background
X_Border -> X_M1.Foreground ; X_M1 -> X_M2.Background ; X_Label -> X_M2.Foreground ; ... (one Merge per part, bottom-up)
X_Mlast -> X_Xf (Transform: the component's animation handle) -> [X_Shadow (S2)] -> Page_MX.Foreground
Page chain: Page_BG -> Page_MShA (S1 shadow) -> Page_MA (component A) -> Page_MShB -> Page_MB -> ... -> MediaOut1
```
- The fill plate is the component canvas: no extra transparent Background needed. Z-order = merge order.
- Transform translation is `Center - (0.5,0.5)`; set `Pivot` = component center for scale/rotation. If the plate
  jumps when Pivot changes, your build maps Pivot onto Center: then also set Center = Pivot. Verify once.
- Static components that never move as a unit: merge parts straight onto the page (fewer nodes).
- Name nodes `<Component>_<Part>` with letters, digits, underscore (no hyphens, spaces, leading digit):
  AE `card-revenue-bg` -> `CardRevenue_BG`. Expressions reference these names.
- Many layers: a Merge chain is the proven route. MultiMerge (`Background`, `LayerN.Foreground`,
  `LayerN.Blend`, `LayerOrder` ScriptVal) [corpus] is optional and unqualified.

### 4.6 Content-aware sizing (sourceRectAtTime, autoFitPill, fitText)
- **Border Fill element** (native, no expressions): Text+ element 2 `Enabled2 1`, `ElementShape2 2` (Border
  Fill), `Level2 0` (box around the whole Text; 1 Line, 2 Word), `ExtendHorizontal2`/`ExtendVertical2`
  (padding), `Round2` (corner, 1 = pill in shipped titles), `Red2/Green2/Blue2`, `Opacity2`. A 1 px keyline:
  element 3 `ElementShape3 3` (Border Outline) + `Thickness3`. Element 1 (text fill) renders on top. These IDs
  are **absent from the TSV** (it lists only `EnabledN`/`NameN` for elements 2-8) but appear in Blackmagic's
  "Simple Box 1 Line Lower Third": `ElementShape2 2, Level2 0, ExtendHorizontal2 0.66, ExtendVertical2 0.1,
  Round2 0.079, Alpha2 0.298` [corpus]. Enable the element first, then set its inputs; Extend units: §1.8 test 8.
- **DataWindow expression** (Blackmagic "Text Box" title [corpus]): a RectangleMask that fits the text:
  `Width = "(T.Output[0].DataWindow[3]-T.Output[0].DataWindow[1])/T.Output[0].Width + padW"`,
  `Height = "(T.Output[0].DataWindow[4]-T.Output[0].DataWindow[2])/T.Output[0].Height + padH"`,
  with `padW = 2*pad_px/W`, `padH = 2*pad_px/H`. DataWindow is `{left, bottom, right, top}` in pixels.
  Center to follow off-center text: `Point((T.Output[0].DataWindow[1]+T.Output[0].DataWindow[3])/2/T.Output[0].Width, (T.Output[0].DataWindow[2]+T.Output[0].DataWindow[4])/2/T.Output[0].Height)`.
  `Output[0]` samples frame 0 (static text); `Output[time]` for animated text is unverified.
- **Read bounds from Python**: put the width expression on a spare `Custom` tool `NumberIn1`, then
  `GetInput("NumberIn1", frame)` (cross-tool expressions [live]). Compare against the spec bbox x k.
- **fitText** (shrink text to a fixed box): `Size` expression `min(S0, S0*box_w/((self.Output[0].DataWindow[3]-self.Output[0].DataWindow[1])/self.Output[0].Width))`
  risks self-reference feedback; prefer computing Size once in the build script from a measured width.

### 4.7 Design tokens as live controls
- Script-side token dict is the source of truth (§11). For live retheming, add swatch tools and link colors by
  expression, the Blackmagic idiom `TopLeftRed = Expression "sChangeStyle1.Red"` [corpus]:
  `Tok_Accent` (Background, unconnected) and in every accent plate `TopLeftRed = "Tok_Accent.TopLeftRed"`
  (x3 channels). Or a `Custom` controller `UI_Tokens` with `NumberIn1..8` [live pattern].
- Font strings cannot be expression-linked reliably: set `Font`/`Style` per Text+ from the token dict.

---

## §5. COMPONENT RECIPES

Coordinates: the §1.4 examples. Graph notation `A -> B.Input`. 5.1 (CTA) and 5.3/5.9 (card + stat card): see
their status lines. Every other recipe: **status: unverified (not yet rendered)**.

### 5.1 Button: primary CTA
Spec: heights 40 | 44 | 48 | 56 (ONE per page); padding-x 40->24, 44->24, 48->32, 56->32 (grid-safe, not
h x 0.7); radius 8 (web) | 980 pill | 6 utility (or page radius); font 14-16 weight 500 (not 600+, shouty);
white text on accent; hover lift `0 4px 12px rgba(accent,.3)`; active = slightly darker accent. Modern flat
has no shadow, or the accent glow in dark themes. Background may be `linear-gradient(135deg, accent, accent-dark)`.
Example: 180x44 at (120,480), r8, #5e6ad2, "Get started ->" Inter 500 14 white, shadow `0 8 32 accent .35`.
```
Btn_M (RectangleMask) -> Btn_Fill.EffectMask ; Btn_Fill -> Btn_ML.Background ; Btn_Label -> Btn_ML.Foreground
Btn_ML -> Btn_Xf (Transform) -> Btn_Glow (Shadow) -> Page_MBtn.Foreground
```
- `Btn_M`: Center {0.109375, 0.535185}, Width 0.09375, Height 0.040741, CornerRadius 0.363636.
- `Btn_Fill` (Background): TopLeftRed .3686, TopLeftGreen .4157, TopLeftBlue .8235.
- `Btn_Label` (TextPlus): StyledText, Font "Inter", Style "Medium", Size .012422 (x K_Inter/1.70), Center
  = plate center, Red1/Green1/Blue1 1.
- `Btn_Xf`: Pivot {0.109375, 0.535185}.
- `Btn_Glow` (Shadow): Red .3686 Green .4157 Blue .8235, Alpha .35, ShadowOffset {0.5, 0.492593},
  Softness ~.0167 (calibrate).
- Dynamic label width: `Btn_M.Width` DataWindow expression + `padW = 48/1920` (24 px each side).
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frame 0 at 3840x2160) with Open Sans Bold instead of Inter (Inter not installed on this Mac): plate measured exactly 360x88 px at (240,960); label centered; `Btn_Glow` Shadow halo sits below the plate as intended.
Verify: plate 180x44 (360x88 UHD) +-1 px; cap band centered +-1 px; white on #5e6ad2 = 4.70:1 (passes;
white on #6366f1 is 4.47 and fails at 14 px; white on #10b981 is 2.54, never).

### 5.2 Button: secondary (outlined), ghost, icon, toggle
- **Secondary**: same geometry, no fill; ring `t=1` #26282e (outer = 5.1 plate values, inner Width .092708,
  Height .038889, CornerRadius .333333); label #fafafa.
- **Ghost**: label only, hover simulated by a second state (alternate frame or Blend crossfade).
- **Icon button**: EllipseMask or RectangleMask plate + icon (§6) via sRender merged on top.
- **Toggle**: track pill width 2.5 x height, height 16-20: e.g. 50x20, CornerRadius 1, off #3a3b42 / on
  accent (two tracks, on-track Merge `Blend` = state); thumb EllipseMask d = h-4 = 16, `Center.x` from
  `P(L+2+8, .)` to `P(L+w-2-8, .)` by expression `Point(x_off + (x_on-x_off)*Tgl_Anim.NumberIn1, y)`.

### 5.3 Card: surface
Spec: padding 24-32; radius 12 (most) | 16 (premium) | 8 (utility), or page radius; border 1px border-default;
optional shadow `0 1px 2px rgba(0,0,0,.04)` or md; background = surface (one step lighter than canvas).
Anatomy: top label 11 600 UPPERCASE muted tracking 1.5 | title 20-28 600 primary | body 14-16 400 secondary |
optional bottom action row.
Example 384x240 at (352,320) r12, padding 24, shadow md.
```
Card_Sh_M -> Card_Sh ; Page_BG -> Page_MCardSh.Background ; Card_Sh -> Page_MCardSh.Foreground (Blend .12)
Card_M -> Card_Fill ; Card_Ro -> Card_Ri.EffectMask (PaintMode Subtract) ; Card_Ri -> Card_Border
Card_Fill -> Card_M1.BG <- Card_Border ; -> Card_M2.BG <- Card_Label ; -> Card_M3.BG <- Card_Title ; -> Card_M4.BG <- Card_Body
Card_M4 -> Card_Xf -> Page_MCard.Foreground ; Page_MCardSh -> Page_MCard.Background
```
- `Card_M`/`Card_Ro`: Center {0.283333, 0.592593}, Width .2, Height .222222, CornerRadius .1.
- `Card_Ri`: Width .198958, Height .220370, CornerRadius .092437, PaintMode "Subtract".
- `Card_Sh_M`: Center {0.283333, 0.588889} (dy 4 px), same size/radius, SoftEdge ~.00625.
- `Card_Label` "REVENUE": left anchor (§1.5), Center {0.195833, 0.677778} (x = 376, cap-center y = 348),
  Size .00976, Style "Semi Bold", CharacterSpacing 1.20, color #a1a1aa (not #71717a: 3.81:1 on surface).
- `Card_Title` 24 600: Center {0.195833, 0.651181} (cap top 368), Size .021295.
- Body 14 400 #a1a1aa: cap top = title cap bottom + 16; Frame layout width 336 px if it wraps.
Verify: fill bbox 384x240; ring 1 px on all four sides with even corners; label left edge at x=376 +-1 px.
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frame 0 at UHD, as part of a 5.9 stat card): card edge at x 704 / y 640 (UHD), the Subtract ring is exactly 2 UHD px (1 design px) on the left and top edges with even corners, the left-anchored label (`HorizontalJustificationNew 3`, `HorizontalLeftCenterRight -1`) starts at x 752 = 376 design px. S1 shadow (SoftEdge .00625) darkens a band about 40 UHD px below the card (Blend raised to .5 for measurement).

### 5.4 Card: pricing tier
Spec: width 320-400, height 480-600; top tier name + price (~140) | divider 1px | feature list, 24 px pitch
(~280) | divider | CTA 56 at bottom. Highlighted tier: border 2px accent, glow `0 0 40px rgba(accent,.2)`,
"Most popular" pill at top.
Fusion: build as 5.3 with `t=2` ring in accent, S2 glow (offset 0, accent, Alpha .2) or S1 with dy 0; price
`Text+` 48 700 + period subscript as a separate Text+ (baseline aligned); each feature row = check icon (§6)
+ one Text+ per row, or one multi-line Text+ with `LineSpacing = 24/(nat_lh*14)` (Inter: 1.417) plus one
check icon sGrid column (`CellsX 1`, `CellsY 8`, `YOffset = 24/1920`).

### 5.5 Input field
Spec: height = button height (40 | 44 | 48); padding x 16, y = (h - font)/2; border 1px border-default;
background surface or transparent; radius 6-8 (matches buttons, or 999 pill); focus: border -> accent + ring
`0 0 0 3px rgba(accent,.15)`; placeholder muted; font 14-15 400.
Example 320x44 at (800,520) r6: fill/ring as 5.3 values from §1.4; focus ring plate Width .169792,
Height .046296, CornerRadius .36, accent, Blend .15, merged under the field; placeholder Text+ left anchor
Center {0.425, 0.498148} (x = 816); caret = RectangleMask 2x20 px (Width .001042, Height .018519) accent plate,
x = text right edge (DataWindow of the value Text+ + 2 px), blink §12.
Finance archetype: add S5 inset shadow.

### 5.6 Nav: top bar
Spec: height 64-72 (modern) | 56 (compact); padding 24-32 horizontal; logo left (max-width 120-160), nav
center or right, CTA far right; border-bottom 1px; background canvas or `rgba(canvas,.7)` +
`backdrop-blur(20px)`; items 14 500, gap 32, muted (active = primary); right cluster search + avatar + CTA
with 40 gaps.
Graph: `Nav_M(0,0,1920,64) -> Nav_Fill` ; divider plate at row 63 (Center y .941204, Height .000926);
one Text+ per item (left anchor) so each can highlight; item `x_{i+1} = x_i + w_i + 32` from measured widths
(render once, read DataWindow, write fixed x); avatar EllipseMask d40 at (1848,12); CTA = 5.1 at height 36-40.
Frosted variant: `content branch -> Nav_Blur (Blur, sigma ~10 px, calibrate) -> BitmapMask/Merge limited by
Nav_M`, then canvas tint plate `Blend .7` (see the glass module).

### 5.7 Sidebar: vertical nav
Spec: width 240-280 (standard) | 64-72 (icon-only); padding 16-24; background canvas (deeper than main);
border-right 1px; items 36-40 tall, icon 20x20 + label 14 500, gap 12, padding 8/12, radius 6 on hover bg;
active: bg accent at 15% alpha, text accent.
Example width 256, items 224x40 at L 16, first top 96, pitch 44: active plate Center {0.066667, 0.870370} for
the item at top 120 (Width .116667, Height .037037, CornerRadius .3), accent Merge `Blend .15`; icon 20 px
centered at x 38 (sShape Translate.X -0.480208); label left anchor x 60 (.03125). Right divider: Center
{0.133073, 0.5}, Width .000521, Height 1. Accent text on the tint: check contrast (accent #5e6ad2 on
#131418 is 3.92: UI-large only; lighten the active text or use primary).

### 5.8 Modal / dialog
Spec: width 480 | 640 | 800; padding 32-40; radius 12-16; surface; border 1px; shadow `0 24px 80px rgba(0,0,0,.5)`;
backdrop `rgba(0,0,0,.7)` full screen. Inside: header title 20-24 600 + close X (24x24 hit area) | optional
divider | body 24 top margin | footer buttons right-aligned, 24 top margin.
Example 640x400 centered r16 (Center .5,.5, Width .333333, Height .370370, CornerRadius .08):
```
Page -> Page_MBackdrop.BG <- Modal_Backdrop (Background black, full frame) Blend .7
-> Page_MModalSh.BG <- Modal_Sh (S1: dy 24, SoftEdge ~.0417) Blend .5
-> Page_MModal.BG <- Modal_Xf <- Modal_M4 (fill, ring, title, body, close icon, footer buttons)
```
Title left anchor Center {0.35, 0.647478} (x 672, cap top 372), close icon at sShape (0.14375, 0.08125),
footer buttons bottom = 740 - 32.

### 5.9 Stat card
Spec: min height 120; padding 20-24 (use 24; 20 is off-grid); top label "REVENUE" 11 600 UPPERCASE muted
tracking 1.5; center BIG number 32-48 700 mono (JetBrains Mono / SF Mono); bottom trend pill up-arrow
"+24.8%" green + "vs last month" muted.
status: verified 2026-09-26 (Resolve 21.1.0.14, rendered frame 0 at UHD): 5.3 plate + "REVENUE" label + Menlo Bold "$48,210" + green 15-18% trend pill with "+24.8%" rendered as designed (`renders/verify/ui_0000.png`). Counter animation and baseline alignment not measured.
Fusion: 5.3 plate; number Text+ in a mono family (or UI sans with `FontFeatures "tnum"` so counting digits do
not jitter); counter via StyledText expression (§12); trend pill = 5.10 in success color with an arrow glyph
or sShape chevron; baselines of pill text and caption aligned (same baseline y).

### 5.10 Trend chip / status pill / tag
Anatomy spec: 60-100 x 24-28; padding 4/10; radius 999 or 6; background `rgba(accent,.15)` (low alpha tint);
optional border `1px rgba(accent,.3)`; text 11-12 600 in solid accent; icon arrows for trends, filled dot for
status. Design-system spec: height 22-32, padding x 8-12 y 2-4, radius 999 always, bg 10-15%, border 40%,
text 11-12 UPPERCASE 500. (Pick one weight per design.) Never reuse status colors as accents.
- Fixed: 88x24 at (120,160): mask CornerRadius 1 (Center {0.085417, 0.840741}, Width .045833, Height .022222);
  fill accent `Blend .15`; ring t=1 accent `Blend .3` (or .4); Text+ 11 px caps, CS 1.15-1.27, accent color;
  status dot EllipseMask d6-8.
- Auto-fit: one Text+ with element 2 Border Fill (`Level2 0`, `Round2 1`, accent, `Opacity2 .15`) and element 3
  Border Outline (`Opacity3 .3`, Thickness3 ~1 px): editable label, box follows the text (§4.6).

### 5.11 Avatar
Spec: sizes 24 | 32 | 40 | 48 | 64 (one per context); always circular; colored: bg
`linear-gradient(135deg, c1, c2)` + white initials (bold); image: cover fit; stacked groups get a 2px
white/bg border.
- Initials: EllipseMask `Width = Height = d/1920` on a Background `Type "Gradient"`, Linear, `Start = P(L,T)`,
  `End = P(L+d, T+d)`; Text+ bold white, Size from `0.4*d` px, Center = circle center.
- Photo: `Loader/MediaIn -> Transform (cover: Size so the short side = d) -> Merge.Foreground`,
  `Merge.Background = circle plate`, `Operator = "In"` (FG kept only inside BG alpha; the track-matte analog)
  [TSV option; behavior unverified]; or MatteControl with the EllipseMask as `Garbage.Matte`.
- Stack: behind each avatar a canvas-colored EllipseMask plate `d+4`; overlap by 8 px.

### 5.12 Divider
Spec: height 1px; border token color; vertical margin 16-48 (density); optional center label: small text with
16 px horizontal padding cutting the line.
Fusion: 1 px plate (§1.6). Label variant: two segments left/right of the label (segment widths from the
label's DataWindow + 16 px), not an opaque patch over one line (a patch breaks on gradients or glass).

### 5.13 Lists, progress, tabs, charts (rebuilder table)
| Component | Fusion construction |
|---|---|
| List row | plate 48-56 tall full width + children; repeat rows with `y + (row_h + gap)`; identical static rows: `Fuse.Duplicate` (Copies, Center offset per copy [corpus]) on the assembled row, text rows stay separate Text+ |
| Progress bar | track pill #2a2a2a + fill pill accent; fill `Width` animated, left edge pinned by `Center = Point(x_left + self.Width/2, y)` (Width and Center.x share width units) |
| Tab bar | plate + Text+ per tab; active underline = 2 px accent plate under the active label; move by Center.x expression |
| Bar chart | one RectangleMask plate per bar, `Height` animated, bottom pinned: `Center = Point(x, y_bottom + self.Height/2)` (Height and Center.y share height units on RectangleMask) |
| Line chart | `PolylineMask` Solid 0 + BorderWidth (or `sPolygon` + sOutline) with `WriteLength` 0 -> 1 (Trim Paths analog); polyline points are offsets from the mask Center: `X = x/W - 0.5`, `Y = 0.5 - y/H` [corpus grammar] |
| Area chart | same path closed + Background Vertical gradient (accent -> transparent) masked by it |
| Pie / donut | `sEllipse` Solid 0, `BorderWidth` = ring thickness, `WriteLength` = share, `WritePosition` = start: true arcs (the AE route had none) |
| Heatmap / pixel grid | `sRectangle -> sGrid (CellsX, CellsY, XOffset, YOffset)`; per-cell colors need separate shapes or `sDuplicate` Jitter Gain |

---

## §6. ICONS: recognize, never trace

Crop and zoom the reference icon, name it semantically, then rebuild from primitives. Never trace a 16-24 px
bitmap. Brand/product logos: never redraw; use the authorized logo file (Loader still) or a text wordmark.

Construction rule: a stroke segment from p1 to p2 with round caps = `sRectangle {Width = |p2-p1| + s,
Height = s, CornerRadius 1, Angle = segment angle}` centered at the midpoint. Icon box 24 units, `u =
icon_px/24` design px, stroke `s = 2u` (Lucide weight); sShape size = `n*u/1920`. Coordinates below are
**Y up** (the AE table's y-down values are flipped). Combine with `sMerge` (Input1..N), recolor the whole
icon with one `sChangeStyle` (muted -> accent on active), move with `sTransform`, one `sRender` per icon set.

| Icon | Primitives (24u box, centered 0,0, Y up) |
|---|---|
| close | 2 bars W 24.63u, Angle 45 and -45 |
| plus / add | 2 bars W 20u, Angle 0 and 90 |
| hamburger | 3 bars W 20u at y +6u, 0, -6u |
| check | bar A W 9.07u at (-5.5, -2.5) Angle -45; bar B W 17.56u at (2.5, 0.5) Angle 45 |
| chevron right | bars W 11.22u at (0.5, 3) Angle -40.6 and (0.5, -3) Angle 40.6; rotate the group with sTransform for left/up/down |
| play | sNGon Sides 3, 16u, one vertex toward +x (orientation of Angle 0 unverified), shifted +1u right (optical) |
| pause | 2 sRectangle 3u x 16u, CornerRadius 1, at x -5u and +5u |
| search | ring = sBoolean Subtract(sEllipse 11u, sEllipse 7u) at (-2, 2); handle bar W 9.07u at (6.5, -6.5) Angle -45 |
| heart | sRectangle 11u square Angle 45 at (0, -0.81) + 2 sEllipse 11u at (+-3.89, 3.08), sMerge |
| gear | sStar Points 8, Depth ~0.75, 20u, minus sEllipse 7u hole (sBoolean Subtract): real teeth, unlike AE's rect ring |
| home | body sRectangle 16x12u at (0, -2) + roof sNGon Sides 3 (20u wide) above, or sPolygon points |
| bell | sRectangle 14x14u CornerRadius ~0.5 body + sEllipse 4u clapper at (0, -9) |
| user | sEllipse 9u head at (0, 5) + shoulders: sEllipse 16x12u at (0, -8) sBoolean Intersection with a box below y=-2 |
| arrow up-right | shaft bar + 2 head bars, group rotated by sTransform ZRotation |

Match measured stroke width and color (swatch). Many primitives across one sMerge per icon is fine.

---

## §7. LAYOUT PATTERNS as node graphs (1920x1080)

Each pattern: pixel layout, graph outline, notes. Build components with §5, merge onto `Page_BG` bottom-up.

### 7.1 Hero with code visual
Layout: split, text left ~880 px, code window right 720x540 (55/45). Margins 96: text column L 96-976,
gap 128, window L 1104, T 270 (vertically centered), `96 + 880 + 128 + 720 + 96 = 1920`.
LEFT: eyebrow pill "NEW . Multi-region support" | 96 px headline in 3 lines (2 white + 1 gradient-fill accent
line) | 20 px subtitle muted, max-width 640 | button row primary + secondary, gap 16 | optional logo strip
"Trusted by ..." 1140 wide muted. RIGHT: macOS title bar with 3 traffic lights + filename | 12-line code
block with syntax highlighting | floating shadow `0 32px 80px rgba(0,0,0,.5)`.
```
Page_BG -> [Eyebrow pill 5.10] -> [Hero_L1, Hero_L2 (Text+ white), Hero_L3 (Text+ Type1 2 gradient)] (one Text+ per line, baselines 96 px apart)
-> [Sub (Text+ Frame, LayoutWidth ~640/1920)] -> [Btn primary 48h][Btn secondary 48h, x + w + 16]
-> Code_Sh (S1 dy 32, sigma 40) -> Code window: Win_M (Center {0.7625, 0.5}, Width .375, Height .5, CornerRadius .0444 for r12)
   -> title bar plate 40 tall + 3 EllipseMask d12 at x 1126/1146/1166 (Center.x .586458/.596875/.607292, y .731481),
      colors #ff5f57 #febc2e #28c840 -> filename Text+ 13 muted
   -> code: one Text+ per syntax color, all multi-line, same Center/Size/LineSpacing, mono font; each layer keeps
      only its color's characters and replaces the rest with spaces (monospace keeps columns aligned)
```
Syntax colors (VSCode dark): default #d4d4d4, strings #ce9178, keywords #569cd6, comments #6a9955. Four Text+
nodes render the whole block, all live-editable. Vertical budget ~500 px -> top ~288.

### 7.2 Feature grid (3-up or 4-up)
Container 1200-1440 centered; 3 columns, gap 24-32. Grid-safe choice: container 1216, gap 32, columns 384 at
L = 352, 768, 1184. Card: padding 32; icon 48x48 accent shape at top (accent-tint plate `Blend .15` + sShape
icon); title 20 600 (4-6 words); body 14 400 muted, 2-3 lines (Frame width 320); optional "Learn more ->".
Graph: three 5.3 components; stagger entrance via the §12 rig (4 f offset).

### 7.3 Stats strip
Full-width strip, padding 80 top/bottom (AE value; 80 is off-token, use 96 or 64), surface or transparent;
4 columns evenly spaced: BIG number 48-72 700 mono in accent, tiny label below 12 UPPERCASE muted.
Examples "99.99%" UPTIME SLA | "45M+" API CALLS/DAY | "30+" EDGE REGIONS | "<50ms" P99 LATENCY.
Grid: 4 x 296 in a 1280 container, gap 32: L = 320, 648, 976, 1304 (centers x .24375, .414583, .585417,
.75625). Number Text+ centered on the column center; label Text+ below with 12 px gap. Counters §12.

### 7.4 Pricing table
3 tiers centered, 360 wide, gap 24: L = 396, 780, 1164. Middle tier elevated: border 2px accent, "+scale
1.05", "Popular" badge. Each tier: name, BIG price 48 700 + period subscript, divider, 8-item checklist
(check icon + 14 px text), CTA at bottom.
Fusion: build the middle tier at the larger geometry (376x584, a grid-safe x1.044; exact 1.05 = 378x588),
never a Transform 1.05 on a raster. Glow S2 accent Alpha .2.

### 7.5 Footer (4-column link grid)
Background surface; padding 64-96 top, 48 bottom. Top row 4 columns (Product/Company/Resources/Legal):
heading 12 600 UPPERCASE muted + links 14 400 with 12 px gap. Bottom strip: logo + copyright left, social
icons right (24x24 muted).
Fusion: one multi-line Text+ per column with baseline pitch `p` px (14 px links + 12 px gap: p ~= 33 at line
height 1.5) via `LineSpacing = p/(nat_lh*14)` (Inter: 1.95; confirm with §1.8 test 7), or one Text+ per link
when links animate. Taller-than-frame
landing pages: build each section as a frame-sized branch and move sections with Transforms, or use a custom
tall resolution (`UseFrameFormatSettings 0`) on the page branch; unqualified.

### 7.6 Testimonial block
Centered, max-width 720; big curly quote 96 px weight 200, muted accent (decoration); quote text 28-32 400
italic primary (Frame width 720); author block: avatar 48 + name 14 600 / title 12 muted.

### 7.7 Logo wall ("Trusted by")
Label centered top "TRUSTED BY ENGINEERING TEAMS AT" 11 500 UPPERCASE muted, letter-spacing 2 (CS 1.27);
row of 6 logos evenly spaced, muted color at 40% (Merge `Blend .4`); each logo a wordmark Text+ 18-22 600
muted, or the authorized logo file; row width 1140-1280.

### 7.8 Effects per archetype (the "top adjustment layer", Fusion tools)
| Archetype | Treatment (applied on the final page merge unless noted) |
|---|---|
| macOS app window | S2/S1 shadow Distance 0, sigma 30 px, 30%; title bar Background `Type "Vertical"` or Gradient top->bottom dark |
| Modern web app | no vignette; subtle md shadows on cards; clean type |
| Dashboard / SaaS | optional blacks lift `BrightnessContrast` `Lift` ~0.01-0.02 (AE used Levels Output Black); slight grain `FilmGrain` (strength by eye) |
| Sci-fi / HUD | `Glow` on text and lines (AE Threshold 70, Radius 15, Intensity 1.2 -> Glow `ApplyMode` Threshold with `Low` .7, `Glow` ~1, XGlowSize calibrated); scanlines = repeating Background gradient (§4.3) merged Multiply; vignette = inverted soft EllipseMask on a black Background; single-hue tint via ColorCorrector or Merge ApplyMode "Color" |
| Terminal / code editor | mono font; syntax-colored Text+ layers; subtle `SoftGlow` (Threshold ~.5, Gain ~1); CRT wobble = `Displace` driven by a low FastNoise |
| Mobile app screen | status bar 44 px (iOS) / 24 px (Android); whole-phone frame corner radius 50-60 px -> CornerRadius `2r/min(w,h)` |
| Game UI | heavy Glow, heavy Shadow, `KD_Bevel` on buttons |

Glow belongs to HUD/gaming/sci-fi only, never clean SaaS.

---

## §8. COLOR HARMONY

Palette from one accent: pick ONE vivid accent (e.g. #5e6ad2) | surface from the accent at 4% saturation, 12%
lightness -> #16181f | border at 8% saturation, 18% lightness -> #26282e | text white #fafafa | muted = white
at 50% opacity, equivalent #71717a. Five colors, harmonious. (Fusion: the muted equivalent fails AA for
small text on these darks; see below.)

WCAG contrast (computed 2026-09-26, WCAG 2.x relative luminance): body >= 4.5, large (24+) >= 3.

| Pair | Ratio | Verdict |
|---|---|---|
| #fafafa on #08090b | 19.08 | pass (AE said 18.7) |
| #71717a on #08090b / #131418 / #1c1d22 | 4.12 / 3.81 / 3.48 | **fails body** (AE claimed 4.8); large text only |
| #a1a1aa on #131418 | 7.18 | pass: use for small muted labels |
| #8b8e98 on #0d0e12 / #16181f / #1d2028 | 5.90 / 5.42 / 4.98 | pass |
| #6b6f78 on #fafafa / #f5f5f7 | 4.82 / 4.62 | pass |
| white on #5e6ad2 / #635bff / #0071e3 | 4.70 / 4.70 / 4.70 | pass |
| white on #6366f1 | 4.47 | fails at body sizes |
| white on #10b981 | 2.54 | fails: dark text on emerald |
| #5e6ad2 as text on #131418 | 3.92 | UI/large only |
| #10b981 on #131418 | 7.26 | pass |

```python
def lum(h):
    c = [int(h[i:i+2], 16)/255 for i in (1, 3, 5)]
    c = [x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c]
    return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]
def contrast(a, b): hi, lo = sorted((lum(a), lum(b)), reverse=True); return (hi+0.05)/(lo+0.05)
```
Status colors (universal): success #22c55e or #10b981 | warning #f59e0b or #f97316 | danger #ef4444 or
#f87171 | info = accent or #3b82f6. NEVER reuse status colors as accents.

---

