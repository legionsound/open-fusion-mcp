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
