"""The see-your-own-work loop: contact sheets, reference comparison, numeric motion audit.
Results may carry "_inline": [png paths]; the server turns them into MCP ImageContent."""
import math
import os
import tempfile
import uuid

from .. import config
from ..schema import P
from .base import COMP, OpError, iid_of, jv, kit, op
from .build import QUALITY, ISOLATE, _default_src, _out, _safe, cache_warnings, render_one
from .. import sysmem


def _pil():
    try:
        from PIL import Image, ImageDraw
        return Image, ImageDraw
    except ImportError as e:
        raise OpError("NOT_FOUND", f"Pillow is not installed in the connector venv ({e})", hint="uv pip install pillow")


def preview(path, max_px=960, suffix="_preview"):
    """Downscaled 8-bit RGB PNG for inline viewing (alpha composited over a checker-neutral gray)."""
    Image, _ = _pil()
    im = Image.open(path)
    if im.mode in ("I;16", "I;16B", "I"):
        im = im.point(lambda v: v / 257).convert("L")
    im = im.convert("RGBA")
    bg = Image.new("RGBA", im.size, (40, 40, 40, 255))
    im = Image.alpha_composite(bg, im).convert("RGB")
    im.thumbnail((max_px, max_px), Image.LANCZOS)
    out = os.path.splitext(path)[0] + suffix + ".png"
    im.save(out)
    return out


def _frames(comp, a, default_beats=8):
    if a.get("frames"):
        return sorted({float(f) for f in a["frames"]})
    at = comp.GetAttrs()
    s = float(a.get("start", at["COMPN_GlobalStart"]))
    e = float(a.get("end", at["COMPN_GlobalEnd"]))
    n = int(a.get("beats", default_beats))
    if n < 1 or e < s:
        raise OpError("INVALID_ARGS", "beats must be >= 1 and end >= start")
    return sorted({float(round(s + (e - s) * k / max(1, n - 1))) for k in range(n)}) if n > 1 else [s]


@op("render.contact_sheet", "Render frames (list, or N evenly spaced beats over start..end / the global range) of a tool into ONE labeled grid PNG, returned inline: one look covers the whole motion. State the sampling when judging (a sheet is not playback).",
    [COMP(), P("tool", "string", "Tool (default MediaOut1's source)."), P("frames", "array", "Explicit frames."),
     P("beats", "integer", "Evenly spaced frames (default 8)."), P("start", "number", "First frame for beats."), P("end", "number", "Last frame for beats."),
     P("cols", "integer", "Columns (default 4).", default=4), P("tileWidth", "integer", "Tile width px (default 480).", default=480),
     P("labels", "object", "{frame: 'label'} extra captions."), P("outPath", "string", "Absolute .png path."),
     P("inline", "boolean", "Return the sheet as an image (default true).", default=True), ISOLATE, QUALITY], undo="discard")
def render_contact_sheet(ctx, comp, a):
    Image, ImageDraw = _pil()
    src = _default_src(ctx, comp, a.get("tool"))
    name = src.GetAttrs()["TOOLS_Name"]
    frames = _frames(comp, a)
    if len(frames) > 64:
        raise OpError("INVALID_ARGS", "at most 64 frames per sheet")
    tmp = tempfile.mkdtemp(prefix="fc_sheet_", dir=config.out_dir())
    produced = render_one(ctx, comp, src, frames[0], os.path.join(tmp, "x.png"), frames=frames, isolate=a.get("isolate", True),
                          quality=a.get("quality", "final"))
    if isinstance(produced, str):
        produced = [(frames[0], produced)]
    tw = int(a.get("tileWidth", 480))
    labels = {float(k): v for k, v in (a.get("labels") or {}).items()}
    _, _, fps = ctx.fmt(comp)
    tiles = []
    for f, p in produced:
        im = Image.open(preview(p, max(tw, 64) * 2, "_t"))
        im = im.resize((tw, round(im.height * tw / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        cap = f"f{int(f)}  {f / fps:.2f}s" + (f"  {labels[f]}" if f in labels else "")
        d.rectangle([0, 0, 10 + 7 * len(cap), 18], fill=(0, 0, 0))
        d.text((5, 3), cap, fill=(255, 255, 255))
        tiles.append(im)
    cols = max(1, min(int(a.get("cols", 4)), len(tiles)))
    rows = -(-len(tiles) // cols)
    th = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cols * tw, rows * th), (18, 18, 18))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * tw, (i // cols) * th))
    path = _out(a.get("outPath"), "%s_sheet_%s.png" % (_safe(name), uuid.uuid4().hex[:6]))
    sheet.save(path)
    out = {"path": path, "tool": name, "frames": [f for f, _ in produced], "size": list(sheet.size), "sampling": f"{len(tiles)} frames, not continuous playback",
           "comp": ctx.identity(comp), "memory": sysmem.brief()}
    warn = cache_warnings(ctx, comp)
    if warn:
        out["warnings"] = warn
    if a.get("inline", True):
        out["_inline"] = [preview(path, 1600) if max(sheet.size) > 1600 else path]
    return out


def _ssim(x, y):
    """Mean SSIM on grayscale float arrays (0-255), 7x7 box windows via integral images."""
    import numpy as np
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    k = 7

    def box(m):
        c = np.cumsum(np.cumsum(np.pad(m, ((1, 0), (1, 0))), 0), 1)
        return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)
    mx, my = box(x), box(y)
    sxx = box(x * x) - mx * mx
    syy = box(y * y) - my * my
    sxy = box(x * y) - mx * my
    s = ((2 * mx * my + C1) * (2 * sxy + C2)) / ((mx * mx + my * my + C1) * (sxx + syy + C2))
    return float(s.mean())


@op("render.compare", "Render a frame and compare it with a reference image (e.g. the AE render at the same beat): returns ONE inline strip [reference | render | difference x4] plus numbers: mean abs diff (0-255), PSNR dB, SSIM (grayscale, 7x7), and size/aspect warnings. The acceptance test for rebuilds.",
    [COMP(), P("reference", "string", "Absolute path of the reference image.", required=True), P("tool", "string", "Tool (default MediaOut1's source)."),
     P("frame", "number", "Frame (default current)."), P("maxPx", "integer", "Long edge of each panel (default 960).", default=960),
     P("outDir", "string", "Absolute output directory (default out/compare)."), P("inline", "boolean", "Return the strip inline (default true).", default=True),
     ISOLATE, QUALITY], undo="discard")
def render_compare(ctx, comp, a):
    Image, ImageDraw = _pil()
    try:
        import numpy as np
    except ImportError:
        np = None
    if not os.path.isfile(a["reference"]):
        raise OpError("NOT_FOUND", f"no reference image {a['reference']}")
    src = _default_src(ctx, comp, a.get("tool"))
    f = a.get("frame", comp.CurrentTime)
    d = a.get("outDir") or os.path.join(config.out_dir(), "compare")
    os.makedirs(d, exist_ok=True)
    stem = "%s_f%04d_%s" % (_safe(src.GetAttrs()["TOOLS_Name"]), int(f), uuid.uuid4().hex[:5])
    rpath = render_one(ctx, comp, src, f, os.path.join(d, stem + "_render.png"), isolate=a.get("isolate", True), quality=a.get("quality", "final"))
    ref = Image.open(preview(a["reference"], 100000, "_rgb")).convert("RGB")  # flatten 16-bit/alpha
    ren = Image.open(preview(rpath, 100000, "_rgb")).convert("RGB")
    warnings = []
    if ref.size != ren.size:
        ra, fa = ref.width / ref.height, ren.width / ren.height
        warnings.append(f"size differs: reference {ref.size}, render {ren.size}; render resized to the reference for scoring")
        if abs(ra - fa) > 0.01:
            warnings.append(f"aspect differs: reference {ra:.4f}, render {fa:.4f} (framing will not line up)")
        ren = ren.resize(ref.size, Image.LANCZOS)
    stats = {}
    if np is not None:
        x = np.asarray(ref, dtype=np.float64)
        y = np.asarray(ren, dtype=np.float64)
        diff = np.abs(x - y)
        mse = float((diff ** 2).mean())
        stats = {"meanAbsDiff": round(float(diff.mean()), 3), "psnr": round(10 * math.log10(255 ** 2 / mse), 2) if mse > 0 else float("inf")}
        scale = 1.0
        if max(ref.size) > 1920:  # SSIM on a 1920-wide proxy keeps it fast
            scale = 1920 / max(ref.size)
        gx = np.asarray(ref.convert("L").resize((max(8, int(ref.width * scale)), max(8, int(ref.height * scale)))), dtype=np.float64)
        gy = np.asarray(ren.convert("L").resize((max(8, int(ref.width * scale)), max(8, int(ref.height * scale)))), dtype=np.float64)
        stats["ssim"] = round(_ssim(gx, gy), 4)
        dimg = Image.fromarray(np.clip(diff * 4, 0, 255).astype("uint8"))
    else:
        from PIL import ImageChops
        dimg = ImageChops.difference(ref, ren)
        warnings.append("numpy missing: numbers skipped")
    mp = int(a.get("maxPx", 960))
    panels = []
    for im, lab in ((ref, "reference"), (ren, f"render f{int(f)}"), (dimg, "difference x4")):
        p = im.copy()
        p.thumbnail((mp, mp), Image.LANCZOS)
        dr = ImageDraw.Draw(p)
        dr.rectangle([0, 0, 10 + 7 * len(lab), 18], fill=(0, 0, 0))
        dr.text((5, 3), lab, fill=(255, 255, 255))
        panels.append(p)
    strip = Image.new("RGB", (sum(p.width for p in panels), max(p.height for p in panels)), (18, 18, 18))
    x0 = 0
    for p in panels:
        strip.paste(p, (x0, 0))
        x0 += p.width
    spath = os.path.join(d, stem + "_compare.png")
    strip.save(spath)
    dpath = os.path.join(d, stem + "_diff.png")
    dimg.save(dpath)
    out = {"render": rpath, "reference": a["reference"], "strip": spath, "diff": dpath, "frame": f, "stats": stats, "warnings": warnings + cache_warnings(ctx, comp),
           "comp": ctx.identity(comp), "tool": src.GetAttrs()["TOOLS_Name"], "memory": sysmem.brief(),
           "read": "SSIM > 0.95 near-identical, 0.85-0.95 same design with small offsets, < 0.8 visibly different; check the diff panel for where."}
    if a.get("inline", True):
        out["_inline"] = [spath]
    return out


@op("audit.motion", "Numeric motion check (fusion_kit.audit_motion): samples inputs every `step` frames (subframes) and reports start/end, duration, travel (px for points), easing signature (value progress at 25/50/75% of the move: linear .25/.5/.75, flat ease .156/.5/.844, house .394/.789/.957), stagger between starts, and flags (LINEAR, slow > 2 s, micro < 100 ms).",
    [COMP(), P("specs", "object", "{toolName: [inputId, ...]}", required=True), P("start", "number", "First frame (default global start)."),
     P("end", "number", "Last frame (default global end)."), P("step", "number", "Sampling step in frames (default 0.25).", default=0.25)], read=True)
def audit_motion(ctx, comp, a):
    for tn, ins in a["specs"].items():
        t = ctx.tool(comp, tn)
        if not isinstance(ins, list):
            raise OpError("INVALID_ARGS", f"specs.{tn} must be a list of input IDs")
        for i in ins:
            ctx.inp(t, i)
    at = comp.GetAttrs()
    f0 = float(a.get("start", at["COMPN_GlobalStart"]))
    f1 = float(a.get("end", at["COMPN_GlobalEnd"]))
    if f1 <= f0:
        raise OpError("INVALID_ARGS", "end must be > start")
    step = float(a.get("step", 0.25))
    if (f1 - f0) / step > 20000:
        raise OpError("INVALID_ARGS", "too many samples; raise step or narrow the range")
    W, H, fps = ctx.fmt(comp)
    k = kit(ctx.resolve)
    try:
        res = k["audit_motion"](comp, a["specs"], f0, f1, W, H, fps, step)
    except TypeError:  # older kit without step
        res = k["audit_motion"](comp, a["specs"], int(f0), int(f1), W, H, fps)
    res = jv(res)
    res.update(range=[f0, f1], step=step, fps=fps)
    return res
