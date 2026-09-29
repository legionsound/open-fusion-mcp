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
