<!-- build-orchestration.md part 4 of 6; index: build-orchestration.md -->
# Module 3: UI Rebuilder

Reconstructs a UI screenshot as a fully editable node graph: every UI element its own named unit (Background + mask or sShape, Text+), animatable independently. Never a screenshot loaded as footage. Complements the Visual Matcher; animation recipe codes (R1 Fade-Up, R3 Slide-In, R4 Typewriter/caret, R13 Counter) come from the animation module.

## Measurement procedure (fill BEFORE construction)

> MEASURE, don't eyeball. A "looks about 8 px" radius or a hand-picked hex is the #1 cause of rebuilds coming out wrong.

### 0. Measure with `measure_ref.py` (§S1)

Every coordinate, width, height, stroke width and radius it returns is in REF pixels, top-left origin, Y down. Multiply lengths by SCALE, then convert to Fusion units. Colours are not scaled. `CornerRadius` is scale-invariant (`2r/min(w,h)` uses ref values directly).

Mandatory minimum (one batched call): `size` once; `crop` zoom 6-8 on every small element (icons, badges, dense text, corners) and Read the PNG; `radius` for every rounded surface; `swatch`/`pixel` for every fill, stroke and text colour; `gradient` for every gradient; `capheight` for title, body and caption; `scanline` over repeated rows/bars.

### 0b. Live bounds rig (Fusion's `sourceRectAtTime`)

A rendered image carries its data window, readable in SimpleExpressions (verbatim from the built-in `Text Box.setting`):

```
BOX_Mask.Width  = (LBL_Txt.Output[0].DataWindow[3]-LBL_Txt.Output[0].DataWindow[1])/LBL_Txt.Output[0].Width  + 0.02
BOX_Mask.Height = (LBL_Txt.Output[0].DataWindow[4]-LBL_Txt.Output[0].DataWindow[2])/LBL_Txt.Output[0].Height + 0.02
```

- **autoFitPill** (box adapts to text: lower thirds, chips, buttons, tooltips): the two expressions above on the pill's `RectangleMask`, padding as the added constant (pad_px x 2 / W and / H). Centre it on the text by giving both the same `Center` (expression `LBL_Txt.Center`). Left-pinned growth: `Center` = `Point(left + self.Width/2, y)`. Re-flows on every copy edit. Status unverified in this build, but the pattern ships in a built-in template.
- **fitText** (text shrinks into a fixed box): measure at a reference size with an Instance of the Text+ (`LBL_Measure`, Size 0.1, not merged anywhere), then `LBL_Txt.Size = math.min(S_max, 0.1 * maxW / ((LBL_Measure.Output[0].DataWindow[3]-LBL_Measure.Output[0].DataWindow[1])/LBL_Measure.Output[0].Width))`. Unverified.
- Assign bounds only to geometry (mask `Width`/`Height`/`Center`, `_Xf` inputs). Never drive the text's own `StyledText` from its own bounds (loop).

### 0c. Pivot where you measured

Off-centre pivots are the #1 cause of a scaled element drifting. A unit Transform scales about its `Pivot` (default {0.5, 0.5} = frame centre, NOT the unit centre). Set `<Unit>_Xf.Pivot` = the unit's passport `Center` before any scale-from-centre entrance (expression `Card01_Mask.Center` keeps it glued). Bars that grow from an edge: pivot at that edge (`Point(left, y)`). After moving a pivot, re-render: the unit must not shift at Size 1.0.

### 1. Canvas

```
REF DIMENSIONS:  _____ x _____ px
TARGET COMP:     timeline res (3840x2160 lab) | 1080x1920 portrait for mobile UI | matched ref aspect
SCALE:           comp_W / ref_W = _____  (Fit: min of W and H ratios; record any letterbox offset)
FPS:             24 | 25 | 30
```

### 2. Grid and rhythm

```
COLUMNS: [4|6|8|12|bespoke]   GUTTER: __ px   MARGIN: __ px   BASE UNIT: [4|8|12|16] px
```

### 3. Anatomy: every distinct element

Number top-to-bottom, left-to-right. `[x, y, w, h]` is the TOP-LEFT of the measured bbox in ref pixels, never a Fusion value. Hex in these rows is measured-input notation; convert before use. Be granular: a 1 px border is its own element.

```
E1  Top bar            [0,0,1920,64]    bg #1e1e1e, border-bottom #3c3c3c 1px
E2    Window controls  [20,20,60,14]    3 circles d12 gap 6: #ff5f57 #febc2e #28c840
E3    Tab "AE-MCP"     [200,40,120,28]  12px SF Pro Medium #cccccc, underline #0078d4 2px
E4    Tab "pinterest"  [340,40,100,28]  12px #888888 (inactive)
```

**Convert bbox -> Fusion (MANDATORY before every node):**

| Element | Fusion inputs |
|---|---|
| Rect surface (RectangleMask on a Background) | `Center` = {(x + w/2)S/W, 1 - (y + h/2)S/H}; `Width` = wS/W; `Height` = hS/H; `CornerRadius` = 2r/min(w,h) (clamp 1) |
| Circle / ellipse (EllipseMask) | same `Center`; `Width` = wS/W; `Height` = hS/**W** (equal values = circle) |
| Text+ single line | `Center` = bbox centre (default justification centres the glyph box on it **[live]**); `Size` = 1.70 x font_px x S / W, or from cap height `Size` = cap_px x S / (0.42 W) (Open Sans; other fonts: render once and correct by the measured/rendered cap ratio) |
| Text+ left-aligned block | `HorizontalLeftCenterRight` -1 and `Center.X` = left edge (anchor behaviour unverified: render and check the bbox) |
| 1 px line | `RectangleMask` `Height` = max(1, S)/H; or `sRectangle` |
| Border / stroke | second `RectangleMask` with `Solid` 0 and `BorderWidth` = stroke width (units unverified: calibrate by render), or a slightly larger rect behind |

### 4. Component types

Mark each E# with its archetype from the table below; the archetype drives construction.

## UI anatomy table: component -> Fusion construction

Every component is a named unit: `<Name>_Fill` Background + `<Name>_Mask` (or `_Shp` sShape chain) + `<Name>_Txt` + `<Name>_Mrg` + `<Name>_Xf`. Fusion has real strokes, polygons, stars, booleans and draw-on, so none of AE MCP's "no stroke / no path / no polystar" workarounds apply.

### Containers and surfaces

| Component | Construction |
|---|---|
| Solid panel / card / sheet | `Background` fill + `RectangleMask` (measured `CornerRadius`; the 8/12/16/24 px scale is only a sanity check) |
| Stroked card (1-2 px border) | fill unit + a second `RectangleMask` `Solid` 0 with `BorderWidth` on a border-colour Background, same Center/size; or `sRectangle` -> `sOutline` (`Thickness`) |
| Floating card with shadow | card unit -> `Shadow` (`Alpha` 0.15-0.25, offset 0 / 8 px down x S, `Softness` ~0.012 for 24 px blur) |
| Glassmorphic | BG copy -> `Blur` (`XBlurSize` 20-40 scaled) clipped by the card mask (`MultiplyByMask`), card fill `Blend` 0.6-0.8, white 1 px `Solid` 0 border at alpha 0.2-0.4; full native rig in the glass module |
| Gradient header | `Background` `Type` "Vertical" (2 stops from the passport) + `RectangleMask` |
| Inset / sunken field | field fill + inner shadow (C. Inner shadow row) or `KD_Bevel` with the light inverted |
| Divider / 1 px line | `RectangleMask` `Height` 1 px/H or `sRectangle` |

### Text elements

| Component | Construction |
|---|---|
| Body | `TextPlus`; `Font` by OS look: "SF Pro" (macOS/iOS), "Roboto" (Android), "Inter" (web), "Segoe UI" (Windows); verify installed names. Sizes (ref px): 12-14 body, 16-20 headers, 24-48 display, 64-120 hero. Tracking: `CharacterSpacing` (1.0 = normal; display -10 to -25 -> ~0.97-0.99; caps +25 to +50 -> ~1.03-1.05, calibrate) |
| Label / caption | 10-11 px, #888-#aaa, often UPPERCASE (uppercase the string), `CharacterSpacing` ~1.05 |
| Hyperlink | accent colour; underline = Text+ `Underline` 1 (native) or a 1 px rect |
| Heading hierarchy | H1 32-48 bold, H2 24-32 semibold, H3 18-20 medium, body 14 regular (`Style` = the font's style name) |
| Code / mono | "SF Mono" / "JetBrains Mono" / "Menlo"; syntax colours VSCode dark: strings #ce9178 (0.808,0.569,0.471), keywords #569cd6 (0.337,0.612,0.839), comments #6a9955 (0.416,0.600,0.333) |
| Numeric ticker | mono Text+ + counter expression on `StyledText` (Scene Director §5) or `TextTimer`/`TimeCode` modifiers |

### Buttons

| Component | Construction |
|---|---|
| Primary CTA | pill unit: accent `Background` + `RectangleMask` (`CornerRadius` from 6-8 px measured, or 1.0 for a pill) + white Text+ 14 px medium centred; optional elevated `Shadow` in the accent colour at `Alpha` ~0.3 |
| Secondary outlined | `Solid` 0 border mask + Text+ in the border colour, no fill |
| Ghost / minimal | Text+ only; hover state = alternate keyed look |
| Icon button | circle/rect unit + icon sShapes |
| Toggle / switch | pill `RectangleMask` `CornerRadius` 1.0, width 2.5 x height, height 16-20 px; thumb `EllipseMask` diameter = height - 4 px; thumb `Center.X` animates |

### Lists and data

| Component | Construction |
|---|---|
| List row | one row unit (48-56 px tall) built once, then `Fuse.Duplicate` (`Copies` n-1, `Center` offset {0.5, 0.5 - (row+gap)S/H}) for identical rows, or Instances with per-row Text+ for different copy |
| Avatar | photo `Loader` -> fit Merge -> `EllipseMask` (`MultiplyByMask` 1); flat avatar = coloured `EllipseMask` fill |
| Progress bar | track unit (#2a2a2a pill) + fill unit whose mask `Width` animates 0 -> target with `Center.X` = left + Width/2 expression (grows rightward) |
| Tag / chip | autoFitPill (0b) or Text+ Border Fill element (`Level` Text, `Round`, `ExtendHorizontal` for 8-12 px padding), height 24-28 px |
| Tab bar | Text+ per tab + an underline rect unit whose `Center.X` animates between tab centres |

### Charts and data viz

| Component | Construction |
|---|---|
| Line chart | `PolylineMask` `Solid` 0, `BorderWidth` = line width, points from data (author the `Polyline` in `.setting`; points are relative to the mask `Center`); draw-on = key `WriteLength` 0 -> 1 over 24-36 f at 24 fps, easeInOut (AE Trim Paths End 0 -> 100 % over 30-45 f at 30) |
| Bar chart | one `RectangleMask` per bar (or `sRectangle` + `sDuplicate`), each bar's `Height` keyed 0 -> value with `Center.Y` = base + Height/2 expression; stagger 3 f at 24 (AE 4 f at 30) |
| Area chart | closed `PolylineMask` on a `Background` "Vertical" gradient (accent top -> transparent bottom) |
| Pie / donut | `sEllipse` `Solid` 0, `BorderWidth` = ring thickness, `WriteLength` = share (0-1) per segment, segment start via `WritePosition`; stack segments with different colours. Or `EllipseMask` `Solid` 0 |
| Pixel grid / heatmap | `sRectangle` -> `sGrid` (`CellsX`, `CellsY`) -> `sRender` for uniform cells; per-cell colour = one unit per colour class or a `Custom` tool lookup |

### Icons: RECOGNIZE, never trace from the raster

1. `crop` zoom 8 the icon and Read it; name it ("search", "hamburger", "chevron-right", "gear", "bell").
2. Note bbox, stroke vs filled, stroke width (measured on the zoomed crop), colour.
3. Rebuild from the canonical recipe; a crisp recognizable icon beats a pixel-accurate blob.

Recipes in a 24 x 24 box centred at 0, built as sShapes (units relative to the sShape canvas; `Translate.X/Y` place parts; `sMerge` combines; `sRender` -> Background `EffectMask`), scale to the measured size with the unit `_Xf.Size`:

| Icon | sShape construction |
|---|---|
| close | two thin `sRectangle` (2 x 18) rotated +/-45 via `sTransform` `ZRotation`, round ends via `CornerRadius` |
| check | two thin `sRectangle` forming (-8,0) -> (-3,5) -> (8,-6), or `sPolygon` open with `sOutline` |
| play | `sNGon` `Sides` 3 (native triangle), rotated to point right |
| pause | two rounded `sRectangle` 3 x 16 at x -5 / +5 |
| plus | two thin `sRectangle` 2 x 18, one rotated 90 |
| hamburger | three `sRectangle` 18 x 2 at y -6, 0, 6 (or one + `sDuplicate` `Copies` 2, `YOffset`) |
| gear | `sStar` (`Points` 8, `Depth` small) `sBoolean` "Subtract" an `sEllipse` d7 hole |
| home | `sRectangle` body + `sNGon` 3 roof, `sMerge` |
| search | `sEllipse` d11 `Solid` 0 ring + thin `sRectangle` handle at 45 deg |
| heart | two `sEllipse` d11 at (-5,-3)/(5,-3) + `sNGon` 3 pointing down, `sMerge` |
| bell | rounded `sRectangle` body + `sEllipse` clapper |
| user | `sEllipse` head d9 at (0,-5) + half `sEllipse` shoulders (`WriteLength` 0.5) |
| chevron | `sPolygon` open 3 points + `sOutline` (rotate for the other directions) |
| arrow | `sRectangle` shaft + chevron head |
| brand / product logo | never redraw: import the clean authentic logo file via `Loader` (`GA_Logo`), place by `Center` |

### Effects per archetype (top of the unit stack or the GRADE group)

| Archetype | Mandatory treatment |
|---|---|
| macOS app window | window `Shadow`: offset 0, `Softness` ~0.03 (AE 60 px), `Alpha` 0.3; title bar `Background` "Vertical" dark gradient |
| Modern web app | no vignette; subtle `Shadow` on cards (`Alpha` 0.15-0.25, 8 px down, 24 px soft); clean type |
| Dashboard / SaaS | optional blacks lift `MasterRGBOutputLow` 0.02; `FilmGrain` `MasterStrength` 0.01 (AE grain 0.2) |
| Sci-fi / HUD | `SoftGlow` on text and lines (`Threshold` 0.7, `XGlowSize` 15 x W/1920, `Gain` 1.2); scanlines (`KD_Lines`); vignette `Gain` 0.8 (AE -20); single-hue cast via duotone `ColorCorrector` |
| Terminal / code editor | mono font, syntax-coloured Text+ units, subtle `SoftGlow`; optional CRT wobble: FastNoise -> `Displace` `XRefraction` 0.001 (AE Turbulent Displace 2) |
| Mobile app screen | status bar top 44 px (iOS) / 24 px (Android) in ref px; whole-phone view: device mask `CornerRadius` from 50-60 px measured |
| Game UI | heavy `SoftGlow`, heavy `Shadow`, `KD_Bevel` on buttons |

## Build sequence for a UI reference

1. Resolve the item comp; confirm W/H/fps (mobile 1080x1920, web 1920x1080 or timeline res, app 1440x900 scaled).
2. **Build bottom-up by Z order** as pasted units: canvas BG -> surfaces (`HeaderBar`, `Sidebar`, `Card01`) -> dividers -> text -> buttons (one unit each) -> icons -> effects per archetype.
3. **Repeating components:** build one row/card unit, then `Fuse.Duplicate` or Instances for the rest. Faster and still editable.
4. **Name semantically:** `CardRevenue_BG_Fill`, `CardRevenue_Title_Txt`, `CardRevenue_Value_Txt`. Never `Background3`.
5. **Final touch:** archetype treatment on the merged stream or GRADE group.
6. Audit frame (Phase E). Saving is Phase F.

## Animation patterns specific to UI (frames at 24 fps; AE source was 30 fps)

Ease ids refer to Phase D / Scene Director handles; "easeOut" = house settle curve.

| Element | Animation |
|---|---|
| Card entrance | R1 fade-up: `Blend` 0 -> 1 + Y -30 px (0.028 H at 1080) -> 0 over 10 f (AE 12 f at 30), easeOut; stagger 3 f per card (AE 4 f) |
| Counter / stat | R13 counter: `StyledText` expression from a 0..1 controller: `Text(math.floor(1250*CTRL_Count.NumberIn1) .. "")` (the `Text(...)` expression form ships in built-in templates; this exact line unverified); monospaced font so digits don't jitter |
| Progress bar | fill mask `Width` 0 -> target over 19 f (AE 24 f), easeOut |
| Line chart draw | `WriteLength` 0 -> 1 over 24-36 f (AE 30-45 f), easeInOut `cubic-bezier(0.30,0,0.70,1)` |
| Bar chart bars | bar `Height` 0 -> value, 3 f offset per bar |
| Cursor blink | caret `Blend` expression `iif((time/24*2) % 1 < 0.5, 1, 0)` (2 Hz, R4) |
| Click feedback | button `_Xf.Size` 1.0 -> 0.95 -> 1.0 over 5 f (AE 6 f), hard cut + white flash (`Background` white, `Blend` 0.6 -> 0 over 3 f) |
| Modal entrance | backdrop `Blend` 0 -> 0.6 over 6 f (AE 8 f) + modal `_Xf.Size` 0.92 -> 1.0 and `Blend` 0 -> 1 over 10 f (AE 12 f), easeOut |
| Toast | R3 slide in from top, hold 72 f (AE 90 f = 3 s), slide out reversed |
| Tab switch | underline `Center.X` to the new tab centre over 10 f easeInOut; content crossfade 6 f (`Dissolve` `Mix` or two Merge Blends) |

## Close the loop: measure -> build -> AUDIT -> fix

1. Build from measured values only.
2. **Pixel audit** (`audit_frame.py`, with a supplied reference; otherwise the Phase E self-audit against the passport): gate `flaggedPct <= 5` AND `meanDE <= 8`; `worstCells` in render pixels; stripe mismatches from `scanline`.
3. **Bounds check** (catches geometry drift the colour gate misses): render each unit isolated (a Saver on `<Unit>_Mrg`, or temporarily set other Merges' `Blend` 0) and read its alpha bbox (`alpha_bbox` in §S2); compare against the passport bbox x SCALE. A title whose rendered width overruns its card means the font/size/copy is wrong, not the card: fix the measurement, not the container.
4. **Vision pass** on a downscaled render: layout sense, copy, alignment, spacing rhythm.
5. **Fix specifics:** re-`swatch`/`radius`/`capheight` the region behind each worst cell; copy stripe numbers verbatim.
6. **Re-audit** until `ok` and the vision pass is clean; if `meanDE` stalls for two passes, re-measure instead of nudging.

## Don'ts (UI)

- Don't load a screenshot as footage and call it done.
- Don't generate a label, badge, chip, stat pill or plate as an image, even small or glowing ones; surface = Background + mask, label = separate Text+.
- Don't use a generic font: match the OS/brand (SF Pro, Roboto, Inter, Segoe UI), identify it on a zoomed crop, size it from `capheight`.
- Don't trace icons; recognize and rebuild from sShapes.
- Don't eyeball colours or radii.
- Don't skip 1 px borders and dividers; they are most of what makes UI feel real.
- Don't ship perfectly clean rectangles for premium UI: subtle shadow (0 / 8 / 24 px, alpha 0.15-0.25).
- Don't forget rounded corners; fall back to 8 px web / 12-16 px mobile only when a corner truly cannot be measured.
- Don't glow a clean SaaS UI; glow belongs to HUD/gaming/sci-fi.
- Don't animate every element; 2-3 hero animations, the rest just appear.
- Don't leave default node names.

---

