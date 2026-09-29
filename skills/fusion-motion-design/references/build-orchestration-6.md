<!-- build-orchestration.md part 6 of 6; index: build-orchestration.md -->
# Scripts and copy-ready snippets (all status: unverified unless marked)

## S0. Python build helpers (inside Resolve)

```python
import math

def rgb(h):                                    # "#0078d4" -> (0.0, 0.4706, 0.8314)
    h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def add(comp, reg, name, x=0, y=0):
    comp.SetActiveTool(None)                   # [live] required on the Fusion-page comp
    t = comp.AddTool(reg, False, x, y, False, False)
    t.SetAttrs({"TOOLS_Name": name})
    assert t.GetAttrs()["TOOLS_Name"] == name, name   # invalid chars are stripped silently
    return t

def px_rect(bbox, S, W, H, r=0, ox=0, oy=0):  # passport bbox (ref px, top-left) -> RectangleMask inputs
    x, y, w, h = bbox
    cx, cy = (x + w / 2) * S + ox, (y + h / 2) * S + oy
    return {"Center": {1: cx / W, 2: 1 - cy / H}, "Width": w * S / W, "Height": h * S / H,
            "CornerRadius": min(1.0, 2 * r / min(w, h)) if r else 0}

def set_color(tool, prefix, c, a=1.0):         # prefix "TopLeft" -> TopLeftRed..., "" -> Red..., suffix style: use set_color_n
    for k, v in zip(("Red", "Green", "Blue", "Alpha"), (*c, a)):
        tool.SetInput(prefix + k, v)

def ease(tool, input_id, keys, curve=(0.22, 0.0, 0.25, 1.0)):
    """keys: [(frame, value), ...]; applies the same cubic-bezier to every segment.
    Python handles are RELATIVE {dt, dv} [live]."""
    x1, y1, x2, y2 = curve
    comp = tool.Comp()
    comp.CurrentTime = keys[0][0]               # [live] AddModifier seeds a stray key at the current time
    tool.AddModifier(input_id, "BezierSpline")
    inp = next(v for v in tool.GetInputList().values() if v.GetAttrs()["INPS_ID"] == input_id)
    sp = inp.GetConnectedOutput().GetTool()
    kf = {}
    for i, (f, v) in enumerate(keys):
        k = {1: v}
        if i + 1 < len(keys):
            D, V = keys[i + 1][0] - f, keys[i + 1][1] - v
            k["RH"] = {1: x1 * D, 2: y1 * V}
        if i > 0:
            D, V = f - keys[i - 1][0], v - keys[i - 1][1]
            k["LH"] = {1: (x2 - 1) * D, 2: (y2 - 1) * V}
        kf[f] = k
    sp.SetKeyFrames(kf, True)                  # [live] one replace can keep a stray seeded key and drop key-0 RH:
    sp.SetKeyFrames(kf, True)                  # replace twice, then assert the key set
    assert sorted(float(k) for k in sp.GetKeyFrames()) == sorted(float(f) for f, _ in keys)
    return sp

# House reveal on a unit: fade + scale on scalars; the rise lives in the Center expression (Phase D)
# ease(card_mrg, "Blend", [(0, 0.0), (6, 1.0)])
# ease(card_xf,  "Size",  [(0, 0.95), (14, 1.0)])
```

## S1. `measure_ref.py` (local PIL; the `ae_measure_reference` replacement)

```python
#!/usr/bin/env python3
# measure_ref.py IMAGE 'JSON_OPS'   -> JSON. Coordinates in REF pixels, top-left origin, Y down.
# ops: size | pixel{x,y} | swatch{x,y,w,h} | gradient{x1,y1,x2,y2,n} | radius{x,y,w,h,corner:tl|tr|bl|br}
#      capheight{x,y,w,h} (tight crop of one line of CAPITALS/digits) | crop{x,y,w,h,zoom,out?} | scanline{x1,y1,x2,y2}
import sys, json, math, os
import numpy as np
from PIL import Image

img = Image.open(sys.argv[1]).convert("RGB")
A = np.asarray(img, dtype=np.float64) / 255.0
H, W = A.shape[:2]

def col(c):
    c = [float(v) for v in c[:3]]
    return {"hex": "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in c), "rgb": [round(v, 4) for v in c]}

def med(x, y, w, h):
    x0, y0 = max(0, int(round(x))), max(0, int(round(y)))
    return np.median(A[y0:y0 + max(1, int(h)), x0:x0 + max(1, int(w))].reshape(-1, 3), axis=0)

out = []
for o in json.loads(sys.argv[2]):
    k = o["op"]; r = {"op": k}
    if k == "size":
        r.update(w=W, h=H)
    elif k == "pixel":
        r.update(col(A[o["y"], o["x"]]))
    elif k == "swatch":
        r.update(col(med(o["x"], o["y"], o["w"], o["h"])))
    elif k == "gradient":
        r["stops"] = []
        for t in np.linspace(0, 1, o.get("n", 5)):
            x = o["x1"] + (o["x2"] - o["x1"]) * t; y = o["y1"] + (o["y2"] - o["y1"]) * t
            r["stops"].append(dict(pos=round(float(t), 3), **col(med(x - 1, y - 1, 3, 3))))
    elif k == "radius":
        x, y, w, h, c = o["x"], o["y"], o["w"], o["h"], o.get("corner", "tl")
        fill = med(x + w * 0.4, y + h * 0.4, w * 0.2, h * 0.2)
        cx, dx = (x, 1) if c[1] == "l" else (x + w - 1, -1)
        cy, dy = (y, 1) if c[0] == "t" else (y + h - 1, -1)
        bg, t = A[cy, cx], 0
        while t < min(w, h) / 2:
            p = A[cy + dy * t, cx + dx * t]
            if np.linalg.norm(p - fill) < np.linalg.norm(p - bg): break
            t += 1
        r.update(px=round(t / (1 - 1 / math.sqrt(2)), 1), diag_inset=t)   # arc meets the diagonal at r(1-1/sqrt2)
    elif k == "capheight":
        x, y, w, h = o["x"], o["y"], o["w"], o["h"]; R = A[y:y + h, x:x + w]
        bg = np.median(np.concatenate([R[0], R[-1], R[:, 0], R[:, -1]]), axis=0)
        d = np.linalg.norm(R - bg, axis=2); ink = d > d.max() * 0.5
        rows = np.where(ink.any(axis=1))[0]
        r.update(cap_px=int(rows[-1] - rows[0] + 1) if len(rows) else 0,
                 ink=col(np.median(R[ink], axis=0)) if ink.any() else None)
    elif k == "crop":
        x, y, w, h, z = o["x"], o["y"], o["w"], o["h"], o.get("zoom", 6)
        p = o.get("out", os.path.splitext(sys.argv[1])[0] + "_crop_%d_%d.png" % (x, y))
        img.crop((x, y, x + w, y + h)).resize((w * z, h * z), Image.NEAREST).save(p); r["path"] = p
    elif k == "scanline":
        n = int(max(abs(o["x2"] - o["x1"]), abs(o["y2"] - o["y1"]))) + 1
        xs = np.linspace(o["x1"], o["x2"], n).round().astype(int)
        ys = np.linspace(o["y1"], o["y2"], n).round().astype(int)
        L = A[ys, xs] @ np.array([0.2126, 0.7152, 0.0722]); on = L > (L.min() + L.max()) / 2
        runs, s = [], None
        for i, v in enumerate(on):
            if v and s is None: s = i
            if s is not None and (not v or i == n - 1):
                e = i if not v else i + 1
                runs.append({"center": round((s + e - 1) / 2, 1), "width": e - s}); s = None
        r.update(count=len(runs), runs=runs)
    out.append(r)
print(json.dumps(out, indent=1))
```

Example: `python3 measure_ref.py ref.png '[{"op":"size"},{"op":"swatch","x":20,"y":20,"w":200,"h":40},{"op":"radius","x":1180,"y":40,"w":160,"h":44,"corner":"tl"},{"op":"capheight","x":1210,"y":52,"w":100,"h":20}]'`

## S2. `audit_frame.py` (the `ae_audit_frame` replacement) + alpha bbox

```python
#!/usr/bin/env python3
# audit_frame.py REF.png RENDER.png [GX GY CELL_DE]  -> JSON {ok, flaggedPct, meanDE, worstCells}
# Gate: ok = flaggedPct <= 5 and meanDE <= 8. Reference must already match the comp aspect (same Fit/Cover as the passport).
import sys, json
import numpy as np
from PIL import Image

def lab(a):
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = (a @ M.T) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

ren = Image.open(sys.argv[2]).convert("RGB"); W, H = ren.size
ref = Image.open(sys.argv[1]).convert("RGB").resize((W, H), Image.LANCZOS)
gx, gy, thr = (int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (32, 18, 10.0)
R = np.asarray(ref, np.float64) / 255; N = np.asarray(ren, np.float64) / 255
LR, LN = lab(R), lab(N)
hexc = lambda c: "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in c)
cells = []
for j in range(gy):
    for i in range(gx):
        ys, xs = slice(j * H // gy, (j + 1) * H // gy), slice(i * W // gx, (i + 1) * W // gx)
        de = float(np.linalg.norm(LR[ys, xs].reshape(-1, 3).mean(0) - LN[ys, xs].reshape(-1, 3).mean(0)))
        cells.append({"box": [xs.start, ys.start, xs.stop, ys.stop], "de": round(de, 2),
                      "ref": hexc(R[ys, xs].reshape(-1, 3).mean(0)), "render": hexc(N[ys, xs].reshape(-1, 3).mean(0))})
des = np.array([c["de"] for c in cells]); flagged = float((des > thr).mean() * 100)
print(json.dumps({"ok": bool(flagged <= 5 and des.mean() <= 8), "flaggedPct": round(flagged, 2),
                  "meanDE": round(float(des.mean()), 2), "grid": [gx, gy], "cellThreshold": thr,
                  "worstCells": sorted(cells, key=lambda c: -c["de"])[:8]}, indent=1))
```

Alpha bbox of an isolated unit render (bounds check): `a = np.asarray(Image.open(p).convert("RGBA"))[..., 3]; ys, xs = np.where(a > 8); print(xs.min(), ys.min(), xs.max() - xs.min() + 1, ys.max() - ys.min() + 1)` (render pixels, top-left origin; compare to passport bbox x SCALE).

Render the audit frame (Python, inside Resolve; Saver PNG route **[live]**):

```python
sv = add(comp, "Saver", "AUDIT_Saver")
sv.SetInput("Clip", "/abs/audit/Shot_.png")                      # -> Shot_0096.png at frame 96
assert sv.ConnectInput("Input", comp.FindTool("GR_Final"))       # the node MediaOut1 sees
ok = comp.Render({"Start": 96, "End": 96, "Wait": True})
# then: os.path.exists("/abs/audit/Shot_0096.png"), check size with sips, Read a downscaled copy
```

If the PNG format is not picked up from the extension, set it in `.setting` form: `Clip = Input { Value = Clip { Filename = "/abs/audit/Shot_.png", FormatID = "PNGFormat" } }` **[live]**.

## S3. Contact sheet (motion summary)

```bash
# every 4th frame of a rendered range, 6x4 tiles, 480 px wide each
ffmpeg -y -framerate 24 -start_number 0 -i /abs/audit/Shot_%04d.png \
  -vf "select='not(mod(n\,4))',scale=480:-1,tile=6x4" -frames:v 1 /abs/audit/contact.png
sips -Z 1600 /abs/audit/contact.png --out /abs/audit/contact_view.png
```

State the sampling (every 4th frame = 6 samples per second at 24 fps). Add frame labels with PIL if needed (`ImageDraw.text`); ffmpeg `drawtext` needs a font file.

## S4. `audit_motion` (the `ae_audit_motion` replacement; inside Resolve)

status: verified 2026-09-26 (Resolve 21.1.0.14, sampled frames 0..20 of a 3-input test comp) after one fix: the curve signature sampled integer frames, so a linear 0 -> 6 f Blend read 0.333/0.5/0.667 and a linear 0 -> 14 f Size 0.286/0.5/0.714, and the LINEAR flag never fired on short moves. It now samples fractional frames (`GetInput` accepts them). Point rows report travel only (`sig` None).

```python
import math

def audit_motion(comp, specs, f0, f1, W, H, fps):
    """specs: {"Card01_Xf": ["Center", "Size"], "Card01_Mrg": ["Blend"], ...}
    Samples every frame via GetInput(id, frame). Returns one row per input."""
    rows = []
    for name, inputs in specs.items():
        t = comp.FindTool(name)
        for iid in inputs:
            v = [t.GetInput(iid, f) for f in range(f0, f1 + 1)]
            pt = isinstance(v[0], dict)                         # Point -> {1: x, 2: y, 3: 0} [live]
            if pt:
                xy = [(p[1] * W, p[2] * H) for p in v]
                d = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(xy, xy[1:])]
            else:
                d = [abs(b - a) for a, b in zip(v, v[1:])]
            mv = [i for i, x in enumerate(d) if x > 1e-6]
            if not mv:
                rows.append({"tool": name, "input": iid, "anim": False}); continue
            s, e = mv[0], mv[-1] + 1                            # indices into v
            pk = max(range(len(d)), key=lambda i: d[i])
            sig = None
            if not pt and v[e] != v[s]:
                # fractional-frame sampling (live fix: integer rounding read a linear 0-6 f move as 0.333/0.5/0.667)
                sig = [round((t.GetInput(iid, f0 + s + (e - s) * q) - v[s]) / (v[e] - v[s]), 3) for q in (0.25, 0.5, 0.75)]
            rows.append({"tool": name, "input": iid, "anim": True, "start": f0 + s, "end": f0 + e,
                         "dur_s": round((e - s) / fps, 3), "peak": f0 + pk,
                         "travel_px" if pt else "change": round(sum(d), 3), "sig": sig})
    starts = sorted({r["start"] for r in rows if r.get("anim")})
    stagger_ms = [round((b - a) / fps * 1000) for a, b in zip(starts, starts[1:])]
    flags = []
    for r in rows:
        if not r.get("anim"): continue
        if r["dur_s"] > 2.0: flags.append((r["tool"], r["input"], "slow > 2 s"))
        if r["dur_s"] < 0.1: flags.append((r["tool"], r["input"], "micro < 100 ms"))
        if r["sig"] and all(abs(a - b) < 0.02 for a, b in zip(r["sig"], (0.25, 0.5, 0.75))):
            flags.append((r["tool"], r["input"], "LINEAR"))
        if r["sig"] and all(abs(a - b) < 0.02 for a, b in zip(r["sig"], (0.156, 0.5, 0.844))):
            flags.append((r["tool"], r["input"], "flat symmetric 1/3 ease"))
    flags += [("stagger", ms, "too tight < 30 ms") for ms in stagger_ms if ms < 30]
    flags += [("stagger", ms, "drags > 180 ms") for ms in stagger_ms if ms > 180]
    return {"rows": rows, "stagger_ms": stagger_ms, "flags": flags}
```

Signatures for comparison: house settle 0.394/0.789/0.957; entrance 0.522/0.828/0.963; elegant 0.287/0.745/0.949; continuous 0.167/0.5/0.833; exit 0.041/0.190/0.511. Expression-driven inputs are sampled the same way, so the report covers staggered-expression rigs too. Stagger computed across ALL animated inputs mixes units: filter `specs` to one reveal group per call.

## S5. `finalize` (the `ae_finalize_build` replacement; inside Resolve, once per build)

status: verified 2026-09-26 (Resolve 21.1.0.14, test comp, no render needed): reported `Background1` as a default name, eased both linear splines (`Card01_Xf.Size`, `Card01_Mrg.Blend`) to HOUSE with exact handles (Size key 0 `RH {3.08, 0}`, key 14 `LH {-10.5, 0}`; f7 = 0.98947 = house 0.789), floored motion blur on `Card01_Xf` and `Card01_Mrg`, found no orphans. One `SetKeyFrames(kf, True)` on an existing spline (no `AddModifier`) kept exactly the intended keys.

```python
import re

HOUSE = (0.22, 0.0, 0.25, 1.0)
SPATIAL = {"Center", "Size", "XSize", "YSize", "Angle", "Blend", "Displacement", "X", "Y",
           "Start", "End", "Opacity1", "Width", "Height", "WriteLength"}
DEFAULT = re.compile(r"^(Background|Merge|MultiMerge|Transform|Text|Rectangle|Ellipse|Polygon|BSpline|Blur|Glow|"
                     r"SoftGlow|ColorCorrector|BrightnessContrast|ColorGain|FastNoise|Shadow|Duplicate|Displace|"
                     r"Saver|Loader|MediaIn|Camera3D|Merge3D|Renderer3D|ImagePlane3D|Shape3D|Transform3D|"
                     r"sRectangle|sEllipse|sRender|sMerge|pEmitter|pRender|CustomTool|FilmGrain|Defocus|"
                     r"DirectionalBlur|Underlay)\d+$")

def _consumers(comp):
    m = {}
    for t in comp.GetToolList(False).values():
        for inp in t.GetInputList().values():
            o = inp.GetConnectedOutput()
            if o:
                m.setdefault(o.GetTool().GetAttrs()["TOOLS_Name"], []).append((t, inp.GetAttrs()["INPS_ID"]))
    return m

def _is_linear(host, iid, frames):
    for a, b in zip(frames, frames[1:]):
        va, vb = host.GetInput(iid, a), host.GetInput(iid, b)
        if isinstance(va, dict) or va == vb: continue               # holds count as fine
        for q in (0.25, 0.5, 0.75):
            f = a + (b - a) * q
            if abs((host.GetInput(iid, f) - va) / (vb - va) - q) > 0.02: return False
    return True

def finalize(comp, policy="repair"):
    rep = {"default_names": [], "eased": [], "preserved": [], "blur_floored": [], "orphans": []}
    cons = _consumers(comp)
    for t in comp.GetToolList(False).values():
        a = t.GetAttrs(); name = a["TOOLS_Name"]
        if DEFAULT.match(name): rep["default_names"].append(name)
        if a["TOOLS_RegID"] != "BezierSpline":
            if a["TOOLS_RegID"] in ("PolyPath", "XYPath", "PerturbPoint", "PerturbNumber", "Shake") and name not in cons:
                rep["orphans"].append(name)
            continue
        if name not in cons: rep["orphans"].append(name); continue
        host, iid = cons[name][0]
        if iid not in SPATIAL or policy == "preserve": continue
        frames = sorted(float(k) for k in t.GetKeyFrames().keys())  # string keys "0.0" [live]
        if len(frames) < 2: continue
        if policy == "force" or _is_linear(host, iid, frames):
            keys = [(f, host.GetInput(iid, f)) for f in frames]
            x1, y1, x2, y2 = HOUSE; kf = {}
            for i, (f, v) in enumerate(keys):
                k = {1: v}
                if i + 1 < len(keys): k["RH"] = {1: x1 * (keys[i+1][0] - f), 2: y1 * (keys[i+1][1] - v)}
                if i > 0:             k["LH"] = {1: (x2 - 1) * (f - keys[i-1][0]), 2: (y2 - 1) * (v - keys[i-1][1])}
                kf[f] = k
            t.SetKeyFrames(kf, True)
            rep["eased"].append(f"{host.GetAttrs()['TOOLS_Name']}.{iid}")
            # motion-blur floor on the image tool that owns the motion (walk up path modifiers)
            img = host
            while img.GetAttrs()["TOOLS_RegID"] in ("PolyPath", "XYPath") and img.GetAttrs()["TOOLS_Name"] in cons:
                img = cons[img.GetAttrs()["TOOLS_Name"]][0][0]
            if img.GetAttrs()["TOOLS_RegID"] in ("Transform", "Merge", "TextPlus") and not img.GetInput("MotionBlur"):
                img.SetInput("MotionBlur", 1); img.SetInput("Quality", 8); img.SetInput("ShutterAngle", 180)
                rep["blur_floored"].append(img.GetAttrs()["TOOLS_Name"])
        else:
            rep["preserved"].append(f"{host.GetAttrs()['TOOLS_Name']}.{iid}")
    return rep
```

Notes: `_is_linear` samples through the host input, so it is independent of how `GetKeyFrames` encodes handles (that encoding is unverified in Python). A spline with any shaped, stepped or held-then-jump segment is preserved. Point inputs are skipped by `_is_linear`; their motion lives in the PolyPath `Displacement` or XYPath `X`/`Y` splines, which this pass eases. After finalize, re-run `audit_motion` and one audit render: finalize changes motion, so the Temporal and Rendered gates must be re-proven. Then export: `item.ExportFusionComp("/abs/Promo_Main.comp", 1)` and confirm the file contains the unit names.

## S6. `.setting` skeleton: one card unit inside a visual group (unverified)

Built from the verified idioms (Background + RectangleMask + TextPlus + Merge + Underlay). Positions/values from the E7/E8 passport rows. Paste with Route A.

```lua
{ Tools = ordered() {
  GRP_CT_CTA = Underlay { ViewInfo = UnderlayInfo { Pos = { -20, -80 }, Size = { 420, 160 } }, },
  CTA_Mask = RectangleMask { Inputs = {
      Center = Input { Value = { 0.875, 0.9235 }, }, Width = Input { Value = 0.1111, },
      Height = Input { Value = 0.0543, }, CornerRadius = Input { Value = 1, }, },
    ViewInfo = OperatorInfo { Pos = { 0, -50 } }, },
  CTA_Fill = Background { Inputs = {
      TopLeftRed = Input { Value = 0, }, TopLeftGreen = Input { Value = 0.4706, }, TopLeftBlue = Input { Value = 0.8314, },
      TopLeftAlpha = Input { Value = 1, }, UseFrameFormatSettings = Input { Value = 1, },
      EffectMask = Input { SourceOp = "CTA_Mask", Source = "Mask", }, },
    ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  CTA_Txt = TextPlus { Inputs = {
      StyledText = Input { Value = "Get Started", }, Font = Input { Value = "Inter", }, Style = Input { Value = "Medium", },
      Size = Input { Value = 0.0165, }, Center = Input { Value = { 0.875, 0.9235 }, },
      UseFrameFormatSettings = Input { Value = 1, }, },
    ViewInfo = OperatorInfo { Pos = { 110, -50 } }, },
  CTA_Mrg = Merge { Inputs = {
      Background = Input { SourceOp = "CTA_Fill", Source = "Output", },
      Foreground = Input { SourceOp = "CTA_Txt", Source = "Output", }, },
    ViewInfo = OperatorInfo { Pos = { 110, 0 } }, },
  CTA_Xf = Transform { Inputs = {
      Input = Input { SourceOp = "CTA_Mrg", Source = "Output", },
      Pivot = Input { Value = { 0.875, 0.9235 }, },
      MotionBlur = Input { Value = 1, }, Quality = Input { Value = 8, }, ShutterAngle = Input { Value = 180, }, },
    ViewInfo = OperatorInfo { Pos = { 220, 0 } }, },
} }
```

Verify: after paste, `FindTool("CTA_Xf")` exists, `CTA_Mrg.Background` reads back connected, and a rendered frame shows a 427 x 117 px pill (at 3840x2160) centred at (3360, 165) with the label centred inside. Then merge `CTA_Xf` as a Foreground into the main chain. Font/Style strings must match installed font names; a missing font falls back silently.

---

# Cheap, preview-friendly construction (port of AE §12)

Fusion's cheap path is the Transform path, not a GPU layer pipeline:

- **Animate unit Transforms (`Center`, `Size`, `Angle`, `Pivot`) and Merge `Blend`/`Center`/`Size`.** Consecutive Transforms concatenate into one resample (sharp and fast); `Resize`/`Scale`/`Crop`/Corner/Perspective Positioner break concatenation. Cubic easing on keys costs nothing.
- **Generators are resolution-independent** (Background, Text+, masks, sShapes, FastNoise): animating their parameters re-renders only that small branch; keep DoD tight and blur/glow branch-local on the smallest image instead of full-frame after the Merge.
- **Heavy paths:** animating `StyledText` re-lays-out the text every frame (use `End` write-on or Follower instead); keying five effect parameters at once (keep one signature parameter animated, bake the rest); animated polyline shapes (prefer a moving mask `Center`/`Width` reveal or `WriteLength` on a parametric shape); per-frame expressions that sample other frames (`GetValue(..., time - n)`) and particles/`Trails` (need pre-roll).
- **Motion blur costs samples:** `Quality` 4-8 while iterating, 12-16 for final (on an OpenGL Renderer3D with accumulation the count is `AccumQuality`, and `MotionBlur` can be off on frames where nothing moves [live, efficiency lab]). For build checks render drafts with `HiQ False, MotionBlur False` (3-7x faster, layout exact; fusion-realities §17).
- **Triage when previews crawl:** count simultaneously animated units (over ~10, group finished units and consider Fusion's disk cache on a finished group); move motion off `StyledText`/polylines onto Transforms or masks; one keyed parameter per effect; use viewer proxy/ROI (viewer-only, nothing to clear for renders).

---

# Don'ts and failure lessons (consolidated)

1. **AddTool without `comp.SetActiveTool(None)` on the Fusion-page comp** auto-wires into the active tool and spawns stray Merges; later `ConnectInput` fails silently as a loop **[live]**. Paste `.setting` units instead.
2. **Treating `comp.Execute` as synchronous:** the next line sees no tools. Poll `FindTool`.
3. **Pasting into a non-current comp:** `Paste` returns False and creates nothing **[live]**.
4. **Pixel coordinates in `Center`**, or forgetting the Y flip: units fly off frame. Always `1 - py/H`.
5. **RectangleMask vs EllipseMask units:** a square RectangleMask needs `Height = Width x W/H`; a circle EllipseMask needs `Height = Width` **[live]**.
6. **Seconds for `time` or degrees in `sin`:** 24x too fast / wrong motion. `time` = frames, trig = radians **[live]**.
7. **`noise()` in an expression:** input reads nil. Use Perturb/Shake or a sum of sines **[live]**.
8. **Relative handles in `.setting` or absolute handles in Python:** broken easing. `.setting` = absolute `{frame, value}`, Python = relative `{dt, dv}` **[live]**.
9. **Merge with no Background:** empty output; the first Background also sets resolution.
10. **Straight (unpremultiplied) foreground:** bright fringes; double premultiply: dark halos.
11. **Mask connected before it has a shape:** blanks the image.
12. **Clearing an expression leaves 0:** SetInput the intended value after `SetExpression("")` **[live]**.
13. **Orphan modifiers** after a failed `AddModifier` or deleting the host; clean via `GetToolList(False)` **[live]**.
14. **`Render` returned True** is not proof: check file, size, pixels.
15. **Baking to hedge:** a PIL-drawn plate or a generated gradient "just in case" ships dead pixels. Native first, always.
16. **Disabling a node because its colour "did not apply":** read back and render; the fix is the input, never removal.
17. **Glow/blur must stay inside a rounded card:** clip the finished card with `MultiplyByMask` or `MatteControl`, not a mask on the source.
18. **Blurring a full-frame BG in place:** edges fall off to transparent; oversize the BG before blurring.
19. **Particles, Trails and Displace-by-noise judged on the first frame:** set pre-roll/reset first.
20. **Loader for 30 fps footage in a 24 fps comp:** plays 25 % slow; route footage through the Media Pool/timeline.
21. **Normalizing a reference-fitted curve to the house ease** or letting finalize `force` it: destroys observed motion.
22. **Declaring done without the numeric audit and the motion report**, or claiming 1x playback from sampled frames.
23. **A multi-scene film switched by Dissolves or Blend-0 Merges:** hidden scenes still cook, memory and render time explode [from rebuild log, B1, B2]. Switch scenes with Merges trimmed to their frames (one culled comp per film Delivered 33 % faster than one comp per beat) (Module 5) [live, efficiency lab].
