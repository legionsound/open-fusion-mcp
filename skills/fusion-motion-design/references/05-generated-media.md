# 05 Generated media: creation and Fusion packaging

Load when a Fusion job needs new photographic stills or footage, or when importing, holding, fitting or replacing generated media inside a comp. Covers the user's Higgsfield defaults and how generated media becomes a replaceable source in Fusion.

## First decide where the plate comes from

Fusion and the Resolve MCP generate nothing. Media exists already, or a separately connected
provider (Higgsfield) creates it. Decide the source before any model choice:

| Case | Action |
|---|---|
| The user supplied it | Use it. Never regenerate approved media during an unrelated correction. |
| It is already in the project (Media Pool, timeline, a MediaIn/Loader in the comp) | Reuse that item; replace only what the request names. |
| It must be created and a provider is connected this session | Defaults below, after confirming the model is available and the returned dimensions. |
| It must be created and no provider is connected | Say so, list the shots needed (the shot spec below), ask the user to supply or generate them, and finish every part of the Fusion work that does not depend on them. Never ship a screenshot, a placeholder `Background` presented as final, or a still standing in for requested motion. |

Generated content is raster: state that limit and keep replacement practical (the packaging
section below).

## This user's generated media pipeline

- Footage: Higgsfield **Seedance 2.5 at 1080p**.
- Stills: Higgsfield **Nano Banana Pro at 2K**.
- An explicit request for **Soul 2.0 at 2K** overrides the still default for that task (it was used successfully for gallery card content). It is an example of an explicit override, not a new default.
- Current explicit instructions override these defaults. Defaults are for new media, not permission to regenerate already approved media during an unrelated correction.
- Text, buttons, prompt windows, diagrams, construction lines, captions and simple graphics stay native Fusion (01). Keep clean authentic logos. Generated imagery is for image/footage content, never to flatten an editable interface.

Before submitting, verify the exact model and resolution in the connected Higgsfield catalog (the Higgsfield MCP `models_explore`, or the `higgsfield-generate` skill's current route). Connector availability varies by session: if Higgsfield is unreachable or the configuration is unavailable, do not silently swap model, provider, resolution, or footage for a still. Report the unavailable setting, resolve the alternative with the user, and continue independent Fusion work meanwhile.

## Describe each shot from the reference

| Field | Example |
|---|---|
| Framing, aspect, lens feel | 3:4 portrait card, 50 mm look, subject centered in upper two thirds |
| Subject and composition | one person, shoulders up, clean negative space right |
| Light | soft key camera left, warm rim |
| Camera movement | slow push-in, no pan |
| Subject movement | turns head toward lens f0-f40, holds |
| Duration and fps | 5 s, confirm the generator's output fps |
| Entry/exit poses | starts profile, ends 3/4 |

Generate a clean plate with no baked UI, logos or typography that belong in Fusion. Moving footage must preserve the observed motion; a still with invented pan/zoom is not an equivalent. Review the entire returned clip for unwanted motion and temporal defects (warping hands, flicker, identity drift). Verify actual downloaded dimensions, duration and fps rather than trusting prompt wording:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration -of json clip.mp4
sips -g pixelWidth -g pixelHeight still.png
```

A portrait output can have different pixel dimensions than a square output of the same marketed tier. Plan fit math from measured pixels.

## Bring media into Fusion: choose the route

| Route | Use when | Facts and cautions |
|---|---|---|
| Timeline clip as the shot's `MediaIn1` | Full-frame generated footage is the shot; overlays go on top | Resolve conforms the clip to timeline fps/res; only the topmost clip enters the comp; Edit-page zoom/position/grade happen after Fusion |
| `MediaIn` from the Media Pool inside a Fusion Composition | Footage used as an inset, card or layer | Import first (`mediaPool.ImportMedia([path])`, Resolve API). Media Pool MediaIns start at comp frame 0 and have audio muted. Inputs: `MediaSource` "MediaPool", `MediaID` (text), `ClipName`, `GlobalIn/Out`, trims, holds. Creating one by script and setting `MediaID` from `item.GetMediaId()` is unverified: test once, or drag it in via UI |
| `Loader` with a file path | Stills (verified 2026-09-17), EXR/PNG sequences; scriptable replacement | Manual: Resolve Loader is for EXR/stills. Do not use Loader for MP4/MOV footage without a verified test. Loader reads frames 1:1 into comp frames with no fps conform |
| `MediaIn` `MediaSource` "Background" | Pull the composite of lower video tracks into the comp | Output is whatever the edit below contains |

Frame-rate trap: a Loader (or any frame-for-frame path) plays a 30 fps source one frame per comp frame, so it runs 25 percent slow in a 24 fps comp. Route footage through the Media Pool/timeline, or retime deliberately (`TimeStretcher` source-time spline; `TimeSpeed` `Speed` cannot be animated).

Holds and ranges (Loader and MediaIn share these inputs): `GlobalIn`/`GlobalOut` place the clip in comp time; extending past the source holds; `HoldFirstFrame`/`HoldLastFrame`, `ClipTimeStart`/`ClipTimeEnd` (Trim In/Out), `Loop`, `Reverse`. Qualified still-image pattern (2026-09-17): `Clip` path, `ClipTimeEnd` 0, `HoldLastFrame` = final frame, `GlobalOut` = final frame; read back `TOOLST_Clip_Name`, `TOOLNT_Clip_End`, `TOOLIT_Clip_TrimOut`, `TOOLIT_Clip_ExtendLast`. Numeric filenames (`card_0001.png`) are detected as sequences: use alphabetic names for stills. Changing an existing clip's length can open a trim-reset modal: handle it, or create a fresh Loader and reconnect confirmed consumers before deleting the old one. In `.setting` text, Loader media is a tool-level `Clips` table, not an Input.

## Package as replaceable media

Import approved results into a named media subgraph with editable overlays above it:

```
MEDIA_Card03 (Loader or MediaIn)  ->  FIT_Card03 Merge.Foreground
CARD03_Frame Background (card pixel size, alpha 0) -> FIT_Card03 Merge.Background
FIT_Card03 -> CARD03_Round (Background EffectMask <- RectangleMask CornerRadius) -> card output
CAPTION_Card03 TextPlus (native) merged after the media, never baked into it
```

Cover/fit follows the source automatically when the fit is an expression, so replacing the file needs no manual rescale. Merge `Size` 1.0 places the foreground pixel-for-pixel; image members `Width`/`Height` are readable in SimpleExpressions:

- Cover: `FIT_Card03.Size` = `max(Background.Width/Foreground.Width, Background.Height/Foreground.Height) * CTRL.Card03Zoom`
- Fit: replace `max` with `min`.
- Framing: `FIT_Card03.Center` = `Point(0.5 + CTRL.Card03PanX, 0.5 + CTRL.Card03PanY)`.
- Non-square pixel aspect: multiply widths by the image's pixel-aspect member (`Foreground.XScale` is manual-named; semantics unverified). Preserve verified source metadata; do not force square pixels to hide wrong fitting.

`Letterbox` (`Mode` Letterbox vs Pan-and-Scan, `Width`/`Height`, `Center`) is a native alternative when the aspect relation is fixed, but it changes resolution and must not be animated.

Keep faces, subjects and important detail inside the intended Cover crop. Review the asset inside the animated card at its largest and smallest visible states before accepting it. When replacing only an image, keep the approved card's caption, rounded corners, shading and timing.

For Edit-page templates, publish the MediaIn `ClipName` (drop zone: the editor drags a Media Pool clip onto that field) or a `Loader` `Clip` path control (06). Built-in templates use `MediaSource` "MediaPool" + `MediaID` for embedded picks; bundled files use the `Setting:` path map (`Filename = "Setting:/media/card.png"`) inside a `.drfx`.

## Recipe M1: replaceable 3:4 card photo (status: unverified (not yet rendered))

Purpose: a 1200x1600 px card in a 3840x2160 comp whose photo can be swapped by path without refitting.

```python
comp.SetActiveTool(None)
ld = comp.AddTool('Loader', False, 0, 0, False, False)          # inside comp.Lock()/Unlock() to avoid dialogs
ld.SetAttrs({'TOOLS_Name': 'MEDIA_Card03'})
ld.SetInput('Clip', '/abs/project/media/card03_portrait.png', 1)
for k, v in {'ClipTimeEnd': 0, 'HoldLastFrame': 287, 'GlobalOut': 287}.items():
    ld.SetInput(k, v, 1)
# FIT_Card03 is a Merge whose Background is a 1200x1600 transparent Background (Width/Height set, UseFrameFormatSettings 0)
fit = comp.FindTool('FIT_Card03')
size_in = next(v for v in fit.GetInputList().values() if v.GetAttrs()['INPS_ID'] == 'Size')
size_in.SetExpression('max(Background.Width/Foreground.Width, Background.Height/Foreground.Height) * CTRL.Card03Zoom')
print(fit.GetInput('Size', 10))   # e.g. 2048x2048 source -> max(0.586, 0.781) = 0.781
```
Verify: swap to a 1920x1080 landscape still and confirm the card stays fully covered with the subject framed; `Size` recalculates; corners stay rounded (mask belongs to the card, not the photo); caption untouched. Restore the original path afterwards.

## Manifest (per portable project)

One row per generated asset, stored beside the project media:

| Field | Example |
|---|---|
| file (relative) | `media/card03_portrait.png` |
| purpose / card / shot | Card 3 portrait, gallery |
| provider, model | Higgsfield, Soul 2.0 |
| requested configuration | 2K, 3:4, prompt summary |
| returned pixels / duration / fps | 1536x2048, still |
| generation ID | if available |
| source / approval | approved by the user 2026-09-26 |

Never put credentials, access tokens or expiring signed download URLs in the manifest. Keep font names and their redistribution terms separate from generated imagery. A generator's scene content is raster: say so, and make ordinary media replacement practical.

## Don'ts and failure lessons

- Do not regenerate approved media during an unrelated fix.
- Do not accept a clip from its first frame; scrub the whole duration.
- Do not trust "2K"/"1080p" wording; measure the file.
- Do not bake captions, buttons or logos into generated plates.
- Do not crop a subject in the card's Cover fit without checking the animated extreme states.
- Do not play footage through a Loader at the wrong fps; route through the Media Pool or retime explicitly.
