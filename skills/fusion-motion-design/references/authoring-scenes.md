# Authoring scenes: design first, then describe

For the `scene.build` / `scene.update` ops of the use-fusion connector (see the `use-fusion` skill, section "Scene builder").

The builder is for original work. Nothing to copy: the description IS the design, written in the order a motion
designer decides things.

1. **Brief to beats.** Write one line per beat with its frame range and its single job ("0-20 the card rises;
   12-30 its content staggers in; 40-66 the cursor glides to the button; 70-80 click").
2. **Tokens.** Put every colour you will reuse and any number you will want to tune live in `controls`
   (`accent`, `ink`, `paper`, `bg`...). Reference them as `"$accent"`. A client colour change is then one edit.
3. **Type scale.** Define `textStyles` (`display`, `h1`, `h2`, `body`, `label`, `mono`...) with font, style,
   size, tracking, leading and colour. Layers say `textStyle: "h2"`. Real font metrics drive layout.
4. **Layout, not coordinates.** Place with `align` (to the safe area, the frame, or another layer: `place:
   below, gap: 32`), group lists in a `layout` stack or grid, and give groups a `radius` and `background` when
   they are cards. Only use raw `position` for free placement (a cursor path, a drift).
5. **Motion.** Entrances and exits with `enter`/`exit` presets tuned by `at`, `duration`, `ease`; lists with a
   group `stagger`; type with a `cascade` or `typewriter` animator; everything else with `keys` and named eases.
   Motion blur is automatic where things move.
6. **Camera (optional).** A `camera` with `lens` or `zoom`, `poi`, and `dof: {focus: "<hero layer>", aperture}`;
   put cards at depth with `position [x, y, z]`, angle them with `rotationY`, rig them with a `null` parent.
7. **Plan, sketch, build, look, edit.** `scene.plan` (fix every issue it names) with a `preview` sheet of the beats
   (layout and timing for free), `scene.build`, draft renders of the beats, then `scene.update` edits until it
   reads; `quality: final` for the last checks.

### Example 1: title sequence (brief: "a 5 s documentary title: deep tide-blue field, the title builds letter by letter, a glint line draws under it, the credit fades up, the block drifts left, then everything leaves")
File: `tests/scenes/title_low_tide.json` (45 tools). Key moves:
```json
"controls": {"tide": "#0B1E33", "deep": "#12385A", "foam": "#E9F1F2", "glint": "#F2C14E"},
"textStyles": {"title": {"font": "Helvetica Neue", "style": "Bold", "size": 168, "tracking": -30, "color": "$foam"}, ...},
"background": {"gradient": {"from": [0, 0], "to": [1920, 1080], "stops": [[0, "$tide"], [1, "$deep"]]}},
{"id": "block", "type": "group", "keys": {"position": [[0, [960, 540]], [150, [920, 540]]]}, "layers": [
  {"id": "title", "type": "text", "text": {"content": "Low Tide", "textStyle": "title"}, "align": "center",
   "animators": [{"type": "cascade", "start": 14, "stagger": 2, "duration": 18, "ease": "out_expo", "from": {"y": 60, "opacity": 0}}],
   "exit": {"preset": "fadeOutUp", "at": 126}},
  {"id": "kicker", ..., "align": {"to": "title", "place": "above", "gap": 40, "x": "left"}, "enter": {"preset": "fadeUp", "at": 8}},
  {"id": "rule", "type": "path", "points": [[0, 0], [560, 0]], "closed": false, "stroke": {"color": "$glint", "width": 4, "cap": "round"},
   "trim": {"start": 0, "end": 0}, "keys": {"trimEnd": [[30, 0, "out_expo"], [56, 100]]}, "align": {"to": "title", "place": "below", "gap": 44, "x": "left"}},
  {"id": "credit", ..., "align": {"to": "rule", "place": "below", "gap": 36, "x": "left"}, "enter": {"preset": "fadeUp", "at": 44}}]}
```
What the builder did: the gradient is a control-driven Corner Background; the drifting group's canvas is cropped
to its content (842x358, not 1920x1080); the 40 px drift is under 0.75 px per frame, so it gets no motion blur;
static sources under animated layers are frozen.

### Example 2: UI feature card (brief: "an app-launch feature card: a rounded card rises in, its icon, title, body and button stagger up, then a cursor glides to the button and clicks")
File: `tests/scenes/card_smart_folders.json` (56 tools).
```json
{"id": "card", "type": "group", "size": [600, null], "background": "$card", "radius": 32, "align": "center",
 "layout": {"type": "stack", "direction": "vertical", "gap": 28, "padding": 64},
 "effects": [{"type": "shadow", "offset": [0, 28], "blur": 56, "opacity": 16}],
 "enter": {"preset": "fadeUp", "duration": 22, "from": {"y": 90, "opacity": 0}},
 "stagger": {"each": 4, "enter": {"preset": "fadeUp", "at": 12}},
 "layers": [{"id": "icon", "type": "rect", "size": [80, 80], "radius": 22, "fill": "$accent"},
            {"id": "headline", "type": "text", "text": {"content": "Smart Folders", "textStyle": "h2"}},
            {"id": "body", "type": "text", "text": {"content": "Your footage sorts itself\nby scene, face and place.", "textStyle": "body"}},
            {"id": "cta", "type": "group", "size": [240, 68], "radius": 34, "background": "$accent",
             "keys": {"scale": [[70, 100, "ease"], [74, 94, "ease"], [80, 100]]},
             "layers": [{"id": "cta_label", "type": "text", "text": {"content": "Try it", "textStyle": "label"}, "align": "center"}]}]},
{"id": "cursor", "type": "path", "points": [[0, 0], [0, 34], [9, 26], [16, 42], [22, 39], [15, 24], [27, 24]],
 "align": {"to": "cta", "offset": [18, 10]}, "enter": {"at": 40, "duration": 26, "ease": "MOUSE", "from": {"x": 420, "y": 260, "opacity": 0}},
 "keys": {"scale": [[70, 100, "ease"], [74, 86, "ease"], [80, 100]]}}
```
No coordinates were measured: the stack hugs its content height, the cursor rests on the button through the
card's transform, and the click scales about the arrow tip (its anchor). Restyle: `{scene: {"controls.accent":
"#00A676"}}`; re-layout: `{layer: "card", set: {"layout.gap": 36}}`; retime: `{layer: "card", set:
{"stagger.each": 3}}`.

### Example 3: 3D product-style push (brief: "three cards float in depth, the side cards angled in; the camera pushes in slowly with shallow focus on the hero; soft specks drift; a line of copy settles at the bottom")
File: `tests/scenes/push_three_worlds.json` (54 tools, one Renderer3D).
```json
{"id": "cam", "type": "camera", "zoom": 2666.7, "poi": [960, 540, 0],
 "keys": {"position": [[0, [960, 540, -3300], "GLIDE"], [150, [960, 540, -2350]]]}, "dof": {"focus": "hero", "aperture": 70}},
{"id": "s1", "type": "ellipse", "size": [60, 60], "fill": "#FFFFFF", "position": [300, 260, 900], "opacity": 25},   (4 specks)
{"id": "left", "type": "group", "use": "EMBER", "position": [330, 560, 320], "rotationY": 22, "enter": {"preset": "fadeUp", "at": 8, "duration": 24}},
{"id": "right", "type": "group", "use": "MOSS", "position": [1590, 560, 320], "rotationY": -22, ...},
{"id": "hero", "type": "group", "use": "SEA", "position": [960, 540, 0], "enter": {"preset": "fadeUp", "duration": 24}},
{"id": "line", "type": "text", "text": {"content": "Three worlds. One timeline.", "textStyle": "line"}, "align": "bottom", "enter": {"preset": "fadeUp", "at": 60}}
```
What the builder did: one texture shared by the four specks (at the scale of the nearest), card textures at
1.12-1.25x (their largest on-screen size), static card textures frozen, motion blur on the 125 frames that move
enough, Z-buffer transparency, focus following the hero card.

## Side note: matching a reference

Rebuilding a reference is a benchmark, not the job. When you must match one:
- Put the reference's own eases in scene `eases` (`ARRIVE`, `GLIDE`, `ACCEL`, `DECEL`...) and its palette in
  `controls`; convert its frames to comp frames (`tests/scenes/bench_s2.json`: global - 48).
- AE point text = the default text origin (first baseline at the justification edge); AE tracking is 1/1000 em;
  AE Rise animators inside a LineBox mask = `cascade` with `stagger: 0` plus a rect mask in layer px.
- AE precomps = `assets`; AE collapsed layers with masks = groups with `masks`; AE 3D layers with camera-driven
  depth expressions = `{expr: "-18*$DepthAmount/100", value: -18}`.
- AE DOF blurs each layer in its own pixels (weaker than physical DOF on scaled-down layers); match with a
  per-scene aperture factor (S2 used 50 px x 0.65) [rebuild K8].
- Grain like AE: `grain {strength: 0.0115}` (LogProcessing 0 is written for you) [rebuild K17].
- Score with `render.compare` on the reference frames, and scan the Deliver render frame by frame.

## Glass, strokes and film controllers [live, scene builder pass 3]
- Frosted glass cards: give the card layer `glass: {blur: 20}` and a translucent `background` (`#FFFFFF21`) or fill; the frost
  follows the card's shape and animation. For a card in a 3D shot, list the cards behind it before it and the cards in front
  after it. AE's "adjustment layer with Gaussian Blur under a card matte" is this option.
- Dashed rules and rings: `stroke.dash: [12, 8]`; draw them on with `trimEnd` keys as usual. Pen-like ribbons:
  `stroke.taper: {startLength: 30, endLength: 30}` (width 0 at both ends); with trim keys the taper follows the drawn part.
- Size pops and iris/ring wipes: animate `size` freely; the builder adds the motion blur.
- A whole film in one comp: build the first scene with its `controls`, give every later scene
  `controlsFrom: "<first scene>"` and the same control names; one colour edit on the first scene recolours the film, and one
  quality flip there flips every scene.
