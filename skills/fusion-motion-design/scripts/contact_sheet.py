#!/usr/bin/env python3
"""contact_sheet.py OUT.png IMG [IMG ...] [--cols 4] [--width 480] [--labels]

Grid of downscaled frames with filename/frame labels, for reviewing motion at a glance.
State the sampling in the receipt: a contact sheet is not continuous playback.
Example: contact_sheet.py sheet.png renders/title_*.png --cols 6 --labels
"""
import argparse
import os
import re

from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("images", nargs="+")
ap.add_argument("--cols", type=int, default=4)
ap.add_argument("--width", type=int, default=480)
ap.add_argument("--labels", action="store_true")
a = ap.parse_args()

paths = sorted(a.images, key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", p)])
tiles = []
for p in paths:
    im = Image.open(p).convert("RGB")
    im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)
    if a.labels:
        d = ImageDraw.Draw(im)
        label = os.path.splitext(os.path.basename(p))[0]
        d.rectangle([0, 0, 8 + 7 * len(label), 18], fill=(0, 0, 0))
        d.text((4, 3), label, fill=(255, 255, 255))
    tiles.append(im)

cols = min(a.cols, len(tiles))
rows = -(-len(tiles) // cols)
th = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * a.width, rows * th), (24, 24, 24))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * a.width, (i // cols) * th))
sheet.save(a.out)
print(a.out, sheet.size, f"{len(tiles)} frames")
