# 14 Localized translation and typography

Load with [13](13-localization.md) when translating wording, choosing or checking fonts and glyph
coverage, fitting longer or shorter text, or re-anchoring counters, typewriters and key labels in
another language. Port of Higgsfield `ae-clean-rig` module 14 (local connector, 2026-09-26). The
glyph script below was run on this Mac; the Resolve behaviors marked [verified live 2026-09-26] were
rendered in Testbed; the rest is **status: unverified**.

## Terminology

Keep a glossary for the project covering every named ship, character, product and object, with
separate columns for the official name, its transliteration, what it literally means and the creative
version that was approved. Only call something established cultural or literary usage when a source
says so; when it genuinely matters, settle doubts from authoritative context and the user's preferred
approach. An approved glossary entry wins over a new transliteration, and one project's naming habits
are not rules for the next.

## Fonts and glyph coverage

- Text+ takes `Font` (family) and `Style` (style name) as text. A family name on the tool proves
  nothing: a missing glyph fails with no error. [verified live 2026-09-26] Text+ does **not** fall
  back to another font for missing glyphs: "Hi 한글 テスト" in Helvetica Neue Bold rendered the Hangul
  and kana as empty boxes (tofu); Apple SD Gothic Neo Bold rendered all of it; Geeza Pro Bold drew
  Arabic but Latin letters and digits as boxes (`t14_glyph.png`, `t14_reading_arabic.png`). A
  nonexistent family name was not tested. Verify the installed face and its
  coverage of every required character before building.
- Check mixed styles and keyed text states, and every script separately: Latin coverage says nothing
  about Hangul, kana or Arabic.
- Search the user's specified font source first; install only needed, authorized fonts; keep existing
  fonts; never accept paid terms without approval; take free fonts from official sources and check
  their license. Explain a substitution as "glyph X missing in font Y", not "language unsupported".
- Match replacements to the source's letter shape, weight, width, density and typographic role.

Coverage check (tested 2026-09-26 with fontTools 4.60.1; reports missing characters per face):
```python
# glyph_check.py FAMILY STYLE "text" ["text" ...]
import sys, glob, os
from fontTools.ttLib import TTFont, TTCollection
fam, sty, texts = sys.argv[1].lower(), sys.argv[2].lower(), sys.argv[3:]
dirs = ['/System/Library/Fonts', '/System/Library/Fonts/Supplemental', '/Library/Fonts',
        os.path.expanduser('~/Library/Fonts')]
files = [f for d in dirs for f in glob.glob(d + '/**/*', recursive=True)
         if f.lower().endswith(('.ttf', '.otf', '.ttc', '.otc'))]
def faces(p):
    try:
        return list(TTCollection(p, lazy=True).fonts) if p.lower().endswith(('.ttc', '.otc')) else [TTFont(p, lazy=True)]
    except Exception:
        return []
hits = 0
for f in files:
    for font in faces(f):
        n = font['name']
        if (n.getDebugName(16) or n.getDebugName(1) or '').lower() != fam: continue
        if sty and (n.getDebugName(17) or n.getDebugName(2) or '').lower() != sty: continue
        hits += 1; cmap = font.getBestCmap() or {}
        for t in texts:
            miss = sorted({c for c in t if not c.isspace() and ord(c) not in cmap})
            print(f'{n.getDebugName(6)} ({f}): {"OK" if not miss else "MISSING " + "".join(miss)} :: {t[:40]}')
if not hits:
    print('no installed face: Text+ will substitute; install or choose another font')
```
Observed: `"Helvetica Neue" "Bold"` covers Latin but misses every Hangul and kana character;
`"Apple SD Gothic Neo" "Bold"` covers both. Fonts Resolve bundles or loads from elsewhere are not in
these folders: add their directory. After the check, render the exact strings once (a Saver PNG at
final size) because Fusion's face matching can still differ from the name table.

## Fitting multilingual text

- When the user wants options before any edit, show what is wrong and propose two or three real
  alternatives in wording or layout; if the pick changes the design, wait for it. Routine local fixes inside an
  approved style need no stop.
- Meaning and natural phrasing first, then size and line breaks. Keep weight, hierarchy, color,
  strokes, backgrounds and safe margins.
- No blanket per-language `Size` reduction, `CharacterSpacing` or `LineSpacing` change: fit each
  element in the real frame. Avoid disproportionate horizontal scaling: Text+ `FitCharacters`
  "Horizontal Size" and Transform `Aspect` squash glyphs; prefer a rewrite, a line break or a small
  size change.
- Text Box layout (`LayoutType` Text Box, `Wrap` 1) wraps at the box; for CJK, line-break rules
  (kinsoku) are not guaranteed, so place manual breaks at meaningful word groups and check that no
  line starts with closing punctuation.
- Keep locale punctuation and word groups. Adjust spacing around embedded Latin and numbers locally,
  never inside protected identifiers. Do not apply Latin tracking habits to Chinese, Japanese or
  Korean.
- Complex scripts: `UseLigatures` "Non-Latin" or "All Scripts" for shaping (Arabic, Indic);
  `ReadingDirection`/`Direction`/`LineDirection` for right-to-left or vertical layouts.
  [verified live 2026-09-26, `t14_direction.png`, `t14_linedir.png`] `Direction` 0 Automatic,
  1 Horizontal, 2 Reversed Horizontal ("ABC" -> "CBA"), 3 Vertical, 4 Reversed Vertical;
  `LineDirection` 0 Automatic, 1 Top Down, 2 Bottom Up (line order flips). `ReadingDirection` lists
  0 Automatic, 1 Left to Right, 2 Right to Left, but no value changed a Latin line or a mixed
  Arabic/Latin line: its effect is unverified. Arabic stayed joined with `UseLigatures` 0 (None).
- Browser typography advice is a visual goal at most. Diagnose the real font, tracking, leading,
  `DataWindow` bounds and the render; do not claim browser or OS validation from a comp inspection.

## Optical alignment and animated text

- Identify the intended anchor: the whole line, the number itself, number plus image, a key label,
  or the card. The text box's geometric center can differ from its visual center; apply the same
  anchor the user approved in the source language.
- Counters: split prefix, numeric value and suffix into separate Text+ tools when needed so the
  number keeps its optical center as digit count changes. `ForceMonospaced` (0..1) or a font with
  tabular figures stops proportional digits from jittering. [verified live 2026-09-26] Georgia
  (proportional figures), centered: "X1111X" vs "X8888X" measured 848 vs 1028 px wide at
  `ForceMonospaced` 0 and 786 vs 786 px (same left edge) at 1. It monospaces every character,
  letters included, so split the number into its own Text+ when the label must keep its spacing. Account for separators and glyph widths
  per locale (`1,000` vs `1 000` vs `1.000`). Check the start, middle and end of the count. Keep the
  control value and its animation; never replace a counter with static text.
- When asked to change the spacing around a live number, the request is about its separators or the
  blocks beside it; keep rounding, formatting, speed and unrelated tracking. Check narrower spacing with the
  actual font.
- Typewriters: Text+ Write On (`Start`/`End`, 03) lays out the full string and reveals it, so the line
  never jumps: prefer it. An expression that grows `StyledText` character by character re-lays out
  every frame and a centered line drifts [verified live 2026-09-26: centered "Hello World", `End`
  0 -> 1 kept the ink left edge at 1285 px at frames 5, 10 and 20; the substring expression's left
  edge moved 1752 -> 1619 -> 1285 px (`t14_writeon.png`, `t14_substring.png`)]; if that route is required, left-justify or anchor to the
  full string's measured width.
- Key labels: the key cap follows the label's rendered bounds (06 DataWindow idiom); check cap
  padding relative to the glyph and spacing to neighboring words.
- Account for `Pivot`, `Center`, `Size`, the Transform chain, 3D transforms and camera projection.
  Compare before and after at the same viewing scale through entrance, hold and exit. Isolate a
  local correction to its tool or keyed range (13 change boundaries) and confirm the boundary adds
  no jump. Do not re-center a whole list or chat for a change to one item.

## Don'ts

- Don't trust the `Font` field; check coverage and render.
- Don't shrink a whole language by a fixed percentage.
- Don't squash glyphs horizontally to make a translation fit.
- Don't animate a centered line by substring expression.
- Don't replace a live counter with typed digits.
