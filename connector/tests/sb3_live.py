"""Live plan for scene builder pass 3 (items 1-5 and extras 7-9). Testbed only, own timeline SB3_Lab, one call at
a time, deleted at the end. Spawns THIS copy's server (tests/client.py), so the live connector is not touched. No Deliver, no save.

Run:  <repo>/connector/.venv/bin/python tests/sb3_live.py setup paste blur glass stroke mask film cleanup   (about 8 min)
Each stage is separate (pass the ones to run); results merge into tests/sb3_live_results.json, frames go to out/live_sb3/.
A stage stops when Resolve's footprint passes MEM_STOP_GB (default 22 GB)."""
import asyncio
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Client  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

OUT = os.path.join(ROOT, "out", "live_sb3")
RES = os.path.join(ROOT, "tests", "sb3_live_results.json")
TL = "SB3_Lab"
ENV = {"FUSION_MCP_PROJECT_ALLOWLIST": "Testbed", "FUSION_MCP_OUT_DIR": OUT}
MEM_STOP_GB = float(os.environ.get("MEM_STOP_GB", "22"))
LAYOUT = {"paste": (0, 60), "blur": (60, 48), "glass2d": (108, 40), "glass3d": (148, 40), "stroke": (188, 40), "mask": (228, 30),
          "film": (258, 60)}   # clip: (record frame, frames) on V1
results = json.load(open(RES)) if os.path.exists(RES) else {}


def rec(name, good, evidence):
    results[name] = {"status": "pass" if good else "fail", "evidence": evidence, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
    print(("PASS " if good else "FAIL ") + name + ": " + json.dumps(evidence, default=str)[:700])
    with open(RES, "w") as f:
        json.dump(results, f, indent=1, default=str)


class Stop(Exception):
    pass


async def mem(c, where):
    r = await c.do("system.memory", {"fresh": True})
    gb = ((r.get("result") or {}).get("resolve") or {}).get("footprintGB")
    if gb and gb > MEM_STOP_GB:
        raise Stop(f"Resolve footprint {gb} GB > {MEM_STOP_GB} GB at {where}")
    return gb


def ref(clip):
    return {"timeline": TL, "track": 1, "item": list(LAYOUT).index(clip)}


def base(scene, dur, layers, **kw):
    return dict({"scene": scene, "size": [1920, 1080], "fps": 30, "duration": dur, "quality": "final", "background": "#000000",
                 "layers": layers}, **kw)


async def timed(c, op, args, **kw):
    t0 = time.time()
    r = await c.do(op, args, **kw)
    return r, round(time.time() - t0, 2)


async def frame(c, clip, f, tag, quality="final"):
    r = await c.do("render.frame", {"comp": ref(clip), "frame": f, "quality": quality, "inline": False,
                                    "outPath": os.path.join(OUT, clip, "%s_%04d.png" % (tag, f))}, timeoutMs=300000)
    p = (r.get("result") or {}).get("path")
    return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) if p and os.path.exists(p) else None


def mae(a, b, box=None):
    if a is None or b is None:
        return None
    if box:
        x0, y0, x1, y1 = box
        a, b = a[y0:y1, x0:x1], b[y0:y1, x0:x1]
    return round(float(np.abs(a - b).mean()), 4)


def soft(im, box, lo=25, hi=230):
    """Pixels that are neither background nor full colour in box (a motion-blurred edge has many)."""
    x0, y0, x1, y1 = box
    v = im[y0:y1, x0:x1].max(axis=2)
    return int(((v > lo) & (v < hi)).sum())


def runs(row, thr=128):
    """[(start, length)] of bright runs along a pixel row."""
    out, s = [], None
    for x, v in enumerate(list(row > thr) + [False]):
        if v and s is None:
            s = x
        elif not v and s is not None:
            out.append((s, x - s))
            s = None
    return out


# ---------------------------------------------------------------- stages

async def stage_setup(c):
    tls = await c.do("timeline.list", {})
    if TL in json.dumps(tls.get("result") or {}):
        await c.do("timeline.delete", {"name": TL, "confirm": True})   # our own lab timeline from an earlier try
    r = await c.do("timeline.create", {"name": TL, "width": 1920, "height": 1080, "fps": 30, "makeCurrent": True, "fusionComp": False})
    rec("setup.timeline", r.get("ok"), r.get("result") or r.get("error"))
    for clip, (rf, n) in LAYOUT.items():
        r = await c.do("timeline.add_fusion_clip", {"timeline": TL, "frames": n, "track": 1, "recordFrame": rf, "clipName": "SB3_" + clip},
                       timeoutMs=180000)
        rec("setup.clip." + clip, r.get("ok"), r.get("result") or r.get("error"))


async def stage_paste(c):
    """Item 1: a curve at 0 / 1,000 / 2,000 filler tools of (a) setting.paste of 50 tools, (b) a fresh scene.build of showcase,
    (c) a replace-only scene.update (re-paste in place, no layout pass), (d) a value-only update, (e) a same-graph rebuild
    (replace: true), (f) an update that adds a layer (the layout pass reads the whole comp: expected to grow)."""
    sc = json.load(open(os.path.join(ROOT, "tests", "scenes", "showcase.json")))
    p50 = "{ Tools = ordered() { %s } }" % " ".join(
        "Probe%d = Background { Inputs = { UseFrameFormatSettings = Input { Value = 0, }, Width = Input { Value = 16, }, Height = Input { Value = 16, }, }, },"
        % i for i in range(50))
    curve = {}
    await c.do("comp.clear", {"comp": ref("paste")}, timeoutMs=300000)
    have = 0
    for n in (0, 1000, 2000):
        await mem(c, "paste %d" % n)
        if n > have:
            filler = "{ Tools = ordered() { %s } }" % " ".join(
                "Fill%d = Background { Inputs = { UseFrameFormatSettings = Input { Value = 0, }, Width = Input { Value = 16, }, "
                "Height = Input { Value = 16, }, }, }," % i for i in range(have, n))
            _, fill_s = await timed(c, "setting.paste", {"comp": ref("paste"), "text": filler, "quiet": True}, timeoutMs=600000)
            have = n
        else:
            fill_s = 0
        pt = {"fillerPasteS": fill_s}
        r, pt["settingPaste50S"] = await timed(c, "setting.paste", {"comp": ref("paste"), "text": p50, "quiet": True}, timeoutMs=300000)
        await c.do("tool.delete", {"comp": ref("paste"), "tool": "Probe*"}, timeoutMs=300000)
        r, pt["buildS"] = await timed(c, "scene.build", {"comp": ref("paste"), "description": sc}, timeoutMs=600000)
        pt["buildPasteMs"] = (r.get("result") or {}).get("pasteMs")
        pt["buildLayout"] = (r.get("result") or {}).get("layout")
        r, pt["updateReplaceS"] = await timed(c, "scene.update", {"comp": ref("paste"), "scene": "Showcase", "edits": [
            {"layer": "title", "set": {"animators.0.from": {"y": 60, "opacity": 0, "x": 20}}}]}, timeoutMs=300000)
        res = r.get("result") or {}
        pt.update(updateReplacePasteMs=res.get("pasteMs"), updateReplaceMs=res.get("ms"), updateLayout=res.get("layout"),
                  updateProblems=res.get("problems"))
        r, pt["updateValueS"] = await timed(c, "scene.update", {"comp": ref("paste"), "scene": "Showcase", "edits": [
            {"layer": "title", "set": {"text.content": "Cut to the moment %d." % n}}]}, timeoutMs=300000)
        r, pt["rebuildSameS"] = await timed(c, "scene.build", {"comp": ref("paste"), "description": sc, "replace": True}, timeoutMs=600000)
        pt["rebuildSamePasteMs"] = (r.get("result") or {}).get("pasteMs")
        pt["rebuildNotes"] = (r.get("result") or {}).get("notes")
        r, pt["updateAddS"] = await timed(c, "scene.update", {"comp": ref("paste"), "scene": "Showcase", "edits": [
            {"add": {"id": "dot", "type": "ellipse", "size": [40, 40], "fill": "#FFFFFF", "position": [100, 100]}, "after": "badge"}]},
            timeoutMs=300000)
        pt["updateAddLayout"] = (r.get("result") or {}).get("layout")
        await c.do("tool.delete", {"comp": ref("paste"), "tool": "Showcase_*"}, timeoutMs=300000)
        curve[n] = pt
        print("  curve %d: %s" % (n, json.dumps(pt, default=str)[:400]))
    flat = lambda k: curve[0][k] and curve[2000][k] and curve[2000][k] < 1.5 * curve[0][k] + 0.4   # noqa: E731
    rec("paste.curve", flat("settingPaste50S") and flat("updateReplaceS") and curve[2000]["updateReplacePasteMs"] is not None
        and curve[2000]["updateLayout"] == {"kept": True}, {"curve": curve,
        "baseline": "before sb3: scene.build pasteMs 626 empty vs 3,531 after 2,000 tools (rematch paste.flat)"})
    await c.do("comp.clear", {"comp": ref("paste")}, timeoutMs=300000)


async def stage_blur(c):
    """Item 3: size keys blur through a Transform scale. Rest frames and draft frames are identical to the pre-sb3 graph
    (efficiency.sizeBlur false); moving frames get a soft (blurred) edge."""
    d = base("SZB", 48, [{"id": "iris", "type": "ellipse", "fill": "#FF7A3D", "size": [52, 52], "position": [960, 540],
                          "keys": {"size": [[0, [2000, 2000], "out_expo"], [10, [52, 52]]]}},
                         {"id": "chip", "type": "rect", "fill": "#C6F432", "size": [320, 26], "position": [960, 900],
                          "keys": {"size": [[20, [0, 26], "out_expo"], [26, [320, 26]]]}}])
    r = await c.do("scene.build", {"comp": ref("blur"), "description": d, "replace": True}, timeoutMs=600000)
    rec("blur.build", r.get("ok"), (r.get("result") or {}).get("decisions") or r.get("error"))
    shots = {}
    for tag, eff in (("new", True), ("old", False)):
        if not eff:
            u = await c.do("scene.update", {"comp": ref("blur"), "scene": "SZB", "edits": [{"scene": {"efficiency.sizeBlur": False}}]})
            rec("blur.switch_off", u.get("ok"), (u.get("result") or {}).get("counts") or u.get("error"))
        shots[tag] = {f: await frame(c, "blur", f, tag) for f in (2, 21, 30, 40)}
        shots[tag]["d2"] = await frame(c, "blur", 2, tag + "_draft", "draft")
    if any(v is None for sh in shots.values() for v in sh.values()):
        rec("blur.frames", False, {t: [k for k, v in sh.items() if v is None] for t, sh in shots.items()})
        return
    iris, chip = (560, 140, 1360, 940), (700, 870, 1220, 930)
    ev = {"restMAE": {f: mae(shots["new"][f], shots["old"][f]) for f in (30, 40)},
          "draftMAE_f2": mae(shots["new"]["d2"], shots["old"]["d2"]),
          "movingMAE": {"f2": mae(shots["new"][2], shots["old"][2]), "f21": mae(shots["new"][21], shots["old"][21])},
          "softEdgePx": {"f2": [soft(shots["new"][2], iris), soft(shots["old"][2], iris)],
                         "f21": [soft(shots["new"][21], chip), soft(shots["old"][21], chip)]}}
    rec("blur.identical_at_rest", all(v is not None and v < 0.05 for v in ev["restMAE"].values()) and ev["draftMAE_f2"] is not None
        and ev["draftMAE_f2"] < 0.05, ev)
    rec("blur.moving_frames_blur", ev["softEdgePx"]["f2"][0] > 1.5 * max(1, ev["softEdgePx"]["f2"][1])
        and ev["softEdgePx"]["f21"][0] > 1.2 * max(1, ev["softEdgePx"]["f21"][1]), ev["softEdgePx"])


def barcode(n=24):
    return [{"id": "bar%d" % i, "type": "rect", "size": [18, 1080], "fill": "#FFFFFF", "position": [40 + 80 * i, 540]} for i in range(n)]


async def glass_case(c, clip, scene, d, box, outside):
    r = await c.do("scene.build", {"comp": ref(clip), "description": d, "replace": True}, timeoutMs=600000)
    rec("glass.%s.build" % scene, r.get("ok"), {k: (r.get("result") or {}).get(k) for k in ("tools", "warnings", "notes")}
        if r.get("ok") else r.get("error"))
    with_g = {f: await frame(c, clip, f, "glass") for f in (2, 20)}
    u = await c.do("scene.update", {"comp": ref(clip), "scene": scene, "edits": [{"layer": "card", "set": {"glass": None}}]})
    no_g = {f: await frame(c, clip, f, "plain") for f in (2, 20)}
    x0, y0, x1, y1 = box
    var = lambda im: float(im[y0:y1, x0:x1].std()) if im is not None else None   # noqa: E731
    ev = {"update": u.get("ok"), "insideStd": {"glass": var(with_g[20]), "plain": var(no_g[20])},
          "outsideMAE": mae(with_g[20], no_g[20], outside), "beforeInMAE_f2": mae(with_g[2], no_g[2])}
    rec("glass.%s.frost" % scene, ev["insideStd"]["glass"] is not None and ev["insideStd"]["glass"] < 0.6 * ev["insideStd"]["plain"]
        and ev["outsideMAE"] < 0.05 and ev["beforeInMAE_f2"] < 0.05, ev)


async def stage_glass(c):
    """Item 2: a 2D glass card and a glass card in a real 3D block (split render) over a sharp barcode. Inside the card the
    backdrop is blurred (lower pixel std than without glass), outside and before the card's in-point nothing changes."""
    card = {"id": "card", "type": "group", "size": [640, 320], "radius": 32, "background": "#FFFFFF21", "position": [960, 540],
            "glass": {"blur": 20}, "in": 4, "layers": [{"id": "lbl", "type": "text", "align": "center",
                                                        "text": {"content": "Glass", "font": "Helvetica Neue", "style": "Bold", "size": 64}}]}
    d2 = base("GL2", 40, barcode() + [card])
    await glass_case(c, "glass2d", "GL2", d2, (700, 420, 1220, 480), (0, 0, 600, 1080))
    cam = {"id": "cam", "type": "camera", "zoom": 2666.7, "poi": [960, 540, 0], "keys": {"position": [[0, [960, 540, -2667]], [39, [960, 540, -2500]]]}}
    wall = {"id": "wall", "type": "group", "size": [1920, 1080], "position": [960, 540, 300], "rotationY": 8, "threeD": True, "layers": barcode()}
    d3 = base("GL3", 40, [cam, wall, dict(card, position=[960, 540, 0], threeD=True)])
    await glass_case(c, "glass3d", "GL3", d3, (760, 450, 1160, 500), (0, 0, 500, 1080))


async def stage_stroke(c):
    """Item 4 and extra 7: dash lengths along a row, a trimmed ellipse drawing on, a static taper's width profile, and a tapered
    write-on (keyed polyline, unverified before this run)."""
    d = base("STK", 40, [
        {"id": "dl", "type": "path", "points": [[0, 0], [500, 0]], "closed": False, "position": [200, 150], "stroke": {"color": "#FFFFFF", "width": 8, "dash": [30, 10]}},
        {"id": "dc", "type": "ellipse", "fill": None, "size": [400, 400], "position": [1400, 300], "stroke": {"color": "#FFFFFF", "width": 4, "dash": [12, 8]}},
        {"id": "ring", "type": "ellipse", "fill": None, "size": [300, 300], "position": [500, 650], "stroke": {"color": "#FFFFFF", "width": 10},
         "keys": {"trimEnd": [[0, 0], [20, 100]]}},
        {"id": "tp", "type": "path", "points": [[0, 0], [600, 0]], "closed": False, "position": [1100, 700],
         "stroke": {"color": "#FFFFFF", "width": 40, "taper": {"startLength": 50, "endLength": 50}}},
        {"id": "tw", "type": "path", "closed": False, "position": [1100, 950], "points": [[0, 0], [600, 0]],
         "stroke": {"color": "#FFFFFF", "width": 30, "taper": {"startLength": 30, "endLength": 30}}, "keys": {"trimEnd": [[0, 0], [20, 100]]}}])
    r = await c.do("scene.build", {"comp": ref("stroke"), "description": d, "replace": True}, timeoutMs=600000)
    rec("stroke.build", r.get("ok"), {k: (r.get("result") or {}).get(k) for k in ("tools", "warnings")} if r.get("ok") else r.get("error"))
    im = await frame(c, "stroke", 30, "rest")
    mid = await frame(c, "stroke", 10, "mid")
    if im is None or mid is None:
        rec("stroke.frames", False, "render failed")
        return
    dl = runs(im[150, 150:760].max(axis=1))
    rec("stroke.dash_line", len(dl) == 13 and all(abs(n - 30) <= 2 for _, n in dl[:-1]), {"runs": dl})
    circle = im[100:500, 1200:1600].max(axis=2)
    ring_row = runs(circle[200, :])
    rec("stroke.dash_circle", len(runs(circle[:, 200])) >= 2, {"row": ring_row})
    ring = mid[500:800, 350:650].max(axis=2) > 128
    ys, xs = np.nonzero(ring)
    ang = (np.degrees(np.arctan2(xs - 150, -(ys - 150))) + 360) % 360 if len(xs) else np.array([])
    cover = len(set((ang // 10).astype(int).tolist())) / 36.0 if len(ang) else 0
    rec("stroke.ellipse_trim", 0.3 < cover < 0.8, {"arcCoverAt10": round(cover, 2)})
    col = lambda x: int((im[640:760, x].max(axis=1) > 128).sum())   # noqa: E731
    prof = {x: col(x) for x in (1102, 1250, 1400, 1550, 1698)}
    rec("stroke.taper_static", prof[1400] >= 36 and prof[1102] <= 6 and prof[1698] <= 6 and 14 <= prof[1250] <= 26, prof)
    wl = runs(mid[950, 1090:1720].max(axis=1))
    wf = runs(im[950, 1090:1720].max(axis=1))
    rec("stroke.taper_write_on", wl and wf and wl[-1][0] + wl[-1][1] < wf[-1][0] + wf[-1][1] - 100, {"mid": wl, "final": wf})


async def stage_mask(c):
    """Item 5: a moving ellipse matte and a group used as a luma matte; the builder refuses freezes on them (decisions) and the
    cut renders (the card shows only inside the wipe)."""
    from test_offline import SB3FreezeGuard
    d = dict(json.loads(json.dumps(SB3FreezeGuard.SCENE)), quality="final")
    r = await c.do("scene.build", {"comp": ref("mask"), "description": d, "replace": True, "quiet": True}, timeoutMs=600000)
    det = (r.get("result") or {}).get("detail")
    decisions = json.load(open(det))["decisions"] if det and os.path.exists(det) else []
    refused = [x for x in decisions if "not frozen (mask branch)" in x]
    info = await c.do("tool.info", {"comp": ref("mask"), "tool": ["M_card", "M_card2"], "includeInputs": True})
    im = await frame(c, "mask", 10, "matte")
    wipe_x = 200 + (1700 - 200) * 10 / 20.0
    inside = im[540, int(wipe_x)] if im is not None else None
    outside = im[300, 700] if im is not None else None
    rec("mask.no_freeze_and_cut", len(refused) == 3 and inside is not None and inside[0] > 150 and outside is not None and outside[0] < 80,
        {"refused": refused, "inside": None if inside is None else inside.tolist(), "outside": None if outside is None else outside.tolist(),
         "effectMasks": json.dumps(info.get("result"))[:300]})


async def stage_film(c):
    """Extra 8: FB follows FA's CTRL (controlsFrom); a colour edit on FA recolours FB; a structural update of FB keeps the ladder."""
    for sc, st, col, kw in (("FA", 0, "#FF0000", {}), ("FB", 30, "#00FF00", {"controlsFrom": "FA"})):
        d = base(sc, 30, [{"id": "S", "type": "rect", "size": [1920, 1080], "fill": "$accent"}], start=st, controls={"accent": col}, **kw)
        r = await c.do("scene.build", {"comp": ref("film"), "description": d, "film": True, "replace": True}, timeoutMs=600000)
        rec("film.build." + sc, r.get("ok"), (r.get("result") or {}).get("warnings") if r.get("ok") else r.get("error"))
    px = {}

    async def at(tag, x=960):
        im = await frame(c, "film", 45, tag)
        return im[540, x].tolist() if im is not None else [0, 0, 0]
    px["fb_linked"] = await at("linked")
    await c.do("scene.update", {"comp": ref("film"), "scene": "FA", "edits": [{"scene": {"controls.accent": "#0000FF"}}]})
    px["fb_after_fa_edit"] = await at("recoloured")
    u = await c.do("scene.update", {"comp": ref("film"), "scene": "FB", "edits": [
        {"add": {"id": "dot", "type": "ellipse", "size": [80, 80], "fill": "#FFFFFF"}, "after": "S"}]})
    lint = await c.do("comp.lint_regions", {"comp": ref("film")})
    px["fb_after_update"] = await at("updated", 900)
    ok = px["fb_linked"][0] > 200 and px["fb_after_fa_edit"][2] > 200 and px["fb_after_update"][2] > 200
    rec("film.one_controller", ok and u.get("ok") and (lint.get("result") or {}).get("ok"), {"pixels": px, "lint": lint.get("result")})


async def stage_cleanup(c):
    r = await c.do("timeline.delete", {"name": TL, "confirm": True})
    rec("cleanup", r.get("ok"), r.get("result") or r.get("error"))


async def main(stages):
    os.makedirs(OUT, exist_ok=True)
    async with Client(ENV) as c:
        for s in stages:
            try:
                await globals()["stage_" + s](c)
            except Stop as e:
                rec("stopped." + s, False, str(e))
                break


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["setup", "paste", "blur", "glass", "stroke", "mask", "film", "cleanup"]))
