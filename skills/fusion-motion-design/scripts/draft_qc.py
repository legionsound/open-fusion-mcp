"""Draft QC for a rendered MP4 (fusion-motion-design module 09): 5 fps review sheets plus automated checks.

Writes contact sheets with one labelled tile every (fps / 5) frames and prints:
  DEAD      runs of 2+ frames with almost no crisp edges (no subject on screen)
  MUSH      runs where large dark, soft, featureless areas dominate and nothing crisp reads
  LOW COVER runs where under 5 % of the frame differs from its dominant colour
  FLASH     frames with a large luminance jump, and the maximum inside any 1 s window (keep <= 3, WCAG 2.3.1)
  FROZEN    consecutive frames that are practically identical (a "dead" hold)
Look at the sheets before sending a draft to anyone: these checks find candidates, the eye decides.

Usage: python draft_qc.py film.mp4 out_dir [--map music_map.json] [--dead 0.012]
The optional music map (sections with startFrame, endFrame, startSeconds, beatSeconds) adds section bar.beat to
each tile label. Needs opencv-python and numpy. Written from the open-fusion-mcp explainer build, 2026-09-27."""
import argparse, json, os
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("mp4"); ap.add_argument("out")
ap.add_argument("--map"); ap.add_argument("--dead", type=float, default=0.012)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
M = json.load(open(a.map)) if a.map else None
cap = cv2.VideoCapture(a.mp4)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
step = max(1, int(round(fps / 5)))


def label(f):
    if not M:
        return f"f{f}"
    for s in M["sections"]:
        if s["startFrame"] <= f < s["endFrame"]:
            b = (f / fps - s["startSeconds"]) / s["beatSeconds"]
            return f"f{f} {s['id']} {int(b // 4) + 1}.{int(b % 4) + 1}"
    return f"f{f}"


tiles, edge, mush, cover, lum = [], [], [], [], []
f = 0
while True:
    ok, im = cap.read()
    if not ok:
        break
    if f % step == 0:
        t = cv2.resize(im, (320, 180))
        cv2.rectangle(t, (0, 0), (130, 16), (0, 0, 0), -1)
        cv2.putText(t, label(f), (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)
    g = cv2.cvtColor(cv2.resize(im, (480, 270)), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    e = float((np.sqrt(gx * gx + gy * gy) > 0.25).mean())
    blur = cv2.GaussianBlur(g, (0, 0), 6)
    var = cv2.GaussianBlur((g - blur) ** 2, (0, 0), 6)
    edge.append(e)
    mush.append(float(((blur < 0.16) & (var < 0.0006)).mean()))
    s = cv2.resize(im, (160, 90)).reshape(-1, 3).astype(np.int32)
    keys = (s // 24) @ np.array([10000, 100, 1])
    vals, cnt = np.unique(keys, return_counts=True)
    dom = s[keys == vals[cnt.argmax()]].mean(0)
    cover.append(float((np.abs(s - dom).sum(1) > 60).mean()))
    lum.append(cv2.resize(g, (192, 108)))
    f += 1

cols = 10
for i in range(0, len(tiles), 100):
    ch = tiles[i:i + 100]
    while len(ch) % cols:
        ch.append(np.zeros_like(tiles[0]))
    cv2.imwrite(os.path.join(a.out, f"sheet_{i // 100 + 1}.png"),
                np.vstack([np.hstack(ch[r * cols:(r + 1) * cols]) for r in range(len(ch) // cols)]))


def runs(idx, minlen=2):
    out, s0, p = [], None, None
    for x in idx:
        if s0 is None:
            s0 = p = x
        elif x == p + 1:
            p = x
        else:
            if p - s0 + 1 >= minlen:
                out.append((s0, p))
            s0 = p = x
    if s0 is not None and p - s0 + 1 >= minlen:
        out.append((s0, p))
    return out


n = len(edge)
flash = [i for i in range(1, n) if ((lum[i] - lum[i - 1]) >= 0.1).mean() > 0.25 or ((lum[i] - lum[i - 1]) <= -0.1).mean() > 0.25]
win = int(round(fps))
report = {
    "frames": n, "fps": fps, "sheetsEveryFrames": step, "sheets": (len(tiles) - 1) // 100 + 1,
    "dead": runs([i for i in range(n) if edge[i] < a.dead]),
    "mush": runs([i for i in range(n) if mush[i] > 0.30 and edge[i] < 0.03]),
    "lowCover": runs([i for i in range(n) if cover[i] < 0.05]),
    "flashFrames": flash,
    "flashMaxPerSecond": max((sum(1 for e in flash if s <= e < s + win) for s in range(n)), default=0),
    "frozen": sum(1 for i in range(1, n) if np.abs(lum[i] - lum[i - 1]).mean() < 0.0006),
}
json.dump(report, open(os.path.join(a.out, "qc.json"), "w"), indent=1)
for k in ("dead", "mush", "lowCover"):
    print(f"{k.upper():9s} {report[k] or 'none'}")
print(f"FLASH     max {report['flashMaxPerSecond']} per second (limit 3) at {flash[:20]}")
print(f"FROZEN    {report['frozen']} near-identical consecutive frames")
print(f"sheets    {report['sheets']} in {a.out} (one tile every {step} frames)")
