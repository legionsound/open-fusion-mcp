"""Live check of the house graph style (comp.layout + the scene.build hook). Testbed only, own timeline Layout_Lab, one call at a
time, no Deliver, no project save. About 5-8 minutes for all stages; node-editor screenshots are taken with computer use between
stages (Resolve only).

Run:  .venv/bin/python tests/layout_live.py <stage> [<stage> ...]
Stages: base setup pile probe showcase cost film cleanup
Results merge into tests/layout_live_results.json."""
import asyncio
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Client  # noqa: E402
from fusion_connector.luatable import LTable, parse  # noqa: E402

OUT = os.path.join(ROOT, "out", "live_layout")
SCENES = os.path.join(ROOT, "tests", "scenes")
RES = os.path.join(ROOT, "tests", "layout_live_results.json")
TL = "Layout_Lab"
ENV = {"FUSION_MCP_PROJECT_ALLOWLIST": "Testbed", "FUSION_MCP_OUT_DIR": OUT}
PROBE = {"timeline": TL, "track": 1, "item": 0}
FILM = {"timeline": TL, "track": 1, "item": 1}

# a deliberately piled graph: every tool at the origin (what agents' ad-hoc builds look like)
PILE = """{ Tools = ordered() {
  LL_BG = Background { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, TopLeftRed = Input { Value = 0.1, }, }, ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  LL_Text = TextPlus { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, StyledText = Input { Value = "Layout", }, }, ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  LL_Blur = Blur { Inputs = { XBlurSize = Input { Value = 2, }, Input = Input { SourceOp = "LL_Text", Source = "Output", }, }, ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  LL_Mask = RectangleMask { Inputs = { Width = Input { Value = 0.6, }, }, ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  LL_Merge = Merge { Inputs = { Background = Input { SourceOp = "LL_BG", Source = "Output", }, Foreground = Input { SourceOp = "LL_Blur", Source = "Output", },
                                EffectMask = Input { SourceOp = "LL_Mask", Source = "Mask", }, }, ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
  LL_CTRL = Custom { ViewInfo = OperatorInfo { Pos = { 0, 0 } }, },
} }"""

results = json.load(open(RES)) if os.path.exists(RES) else {}


def rec(name, good, evidence):
    results[name] = {"status": "pass" if good else "fail", "evidence": evidence, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
    print(("PASS " if good else "FAIL ") + name + ": " + json.dumps(evidence, default=str)[:900])
    with open(RES, "w") as f:
        json.dump(results, f, indent=1, default=str)


def R(r):
    return r.get("result") if r.get("ok") else {"error": r.get("error") or r}


def view_info(text):
    """{tool: (ctor, Pos, Size)} from .setting text."""
    out = {}
    for n, t in (parse(text).get("Tools").items):
        vi = t.get("ViewInfo") if isinstance(t, LTable) else None
        if isinstance(vi, LTable):
            pos = vi.get("Pos").positional() if isinstance(vi.get("Pos"), LTable) else None
            size = vi.get("Size").positional() if isinstance(vi.get("Size"), LTable) else None
            out[n] = (vi.ctor, pos, size)
    return out


async def stage_base(c):
    ctx = await c.call("fu_context")
    p = (ctx.get("result") or ctx).get("project") or {}
    rec("base", p.get("name") == "Testbed", {"project": p.get("name"), "timeline": p.get("currentTimeline"), "page": p.get("page")})


async def stage_setup(c):
    tls = await c.do("timeline.list", {})
    if TL in json.dumps(tls.get("result") or {}):
        rec("setup.reset", (await c.do("timeline.delete", {"name": TL, "confirm": True})).get("ok"), "own lab timeline from an earlier try")
    r = await c.do("timeline.create", {"name": TL, "width": 1920, "height": 1080, "fps": 30, "makeCurrent": True, "fusionComp": False})
    rec("setup.timeline", r.get("ok"), R(r))
    for i, (rf, n) in enumerate(((0, 90), (100, 420))):
        r = await c.do("timeline.add_fusion_clip", {"timeline": TL, "frames": n, "track": 1, "recordFrame": rf, "clipName": "LL_%d" % i},
                       timeoutMs=180000)
        rec("setup.clip%d" % i, r.get("ok"), R(r))


async def stage_pile(c):
    """The 'before': a small graph with every tool at the origin (screenshot it)."""
    await c.do("comp.clear", {"comp": PROBE})
    r = await c.do("setting.paste", {"comp": PROBE, "text": PILE})
    rec("pile.paste", r.get("ok"), R(r))
    r = await c.do("input.connect", {"comp": PROBE, "tool": "MediaOut1", "input": "Input", "source": "LL_Merge"})
    rec("pile.connect", r.get("ok"), R(r))


async def stage_probe(c):
    """Units and anchors: FlowView grid units vs ViewInfo px; underlay Pos = (center x, top y); refresh deletes only the boxes."""
    r = await c.do("tool.set_position", {"comp": PROBE, "tool": "LL_CTRL", "x": 2, "y": 3})
    vi = view_info(R(await c.do("setting.copy", {"comp": PROBE, "tools": ["LL_CTRL"]}))["text"])
    pos = vi.get("LL_CTRL", (None, None, None))[1]
    rec("probe.units", pos is not None and abs(pos[0] - 275) < 1 and abs(pos[1] - 115.5) < 1,
        {"setPos": [2, 3], "getPosTable": R(r), "viewInfoPx": pos,
         "expect": "grid units, SetPos = cell top-left: ViewInfo (tile center) = ((x + 0.5) * 110, (y + 0.5) * 33)"})
    dry = R(await c.do("comp.layout", {"comp": PROBE, "dryRun": True}))
    t0 = time.time()
    r = await c.do("comp.layout", {"comp": PROBE})
    lay1 = R(r)
    rec("probe.layout", r.get("ok") and lay1.get("metrics", {}).get("overlaps") == 0,
        dict(lay1, wall=round(time.time() - t0, 2), dryMetrics=dry.get("metrics")))
    plan = json.load(open(lay1["detail"]))
    names = sorted(plan["pos"]) + [b["name"] for b in plan["boxes"]]
    vi = view_info(R(await c.do("setting.copy", {"comp": PROBE, "tools": names}))["text"])
    bad = []
    for n, (x, y) in plan["pos"].items():
        got = vi.get(n, (None, None))[1]
        if not got or abs(got[0] - x * 110) > 1 or abs(got[1] - y * 33) > 1:
            bad.append([n, [x * 110, y * 33], got])
    for b in plan["boxes"]:
        x0, y0, x1, y1 = b["rect"]
        got = vi.get(b["name"], (None, None, None))
        want = [(x0 + x1) / 2 * 110, y0 * 33, (x1 - x0) * 110, (y1 - y0) * 33]
        if not got[1] or not got[2] or max(abs(a - w) for a, w in zip(list(got[1]) + list(got[2]), want)) > 1:
            bad.append([b["name"], want, got])
    rec("probe.readback", not bad, {"mismatch": bad[:10], "checked": len(names)})
    before = len(R(await c.do("tool.list", {"comp": PROBE})).get("tools") or [])
    lay2 = R(await c.do("comp.layout", {"comp": PROBE}))
    after = len(R(await c.do("tool.list", {"comp": PROBE})).get("tools") or [])
    rec("probe.refresh", lay2.get("underlaysRemoved") == lay1.get("underlays") and before == after,
        {"underlaysRemoved": lay2.get("underlaysRemoved"), "made": lay2.get("underlays"), "toolsBefore": before, "toolsAfter": after})


async def stage_units(c):
    """How FlowView SetPos maps to ViewInfo Pos (tools and underlays), and whether a paste keeps ViewInfo."""
    await c.do("setting.paste", {"comp": PROBE, "text": "{ Tools = ordered() { LL_U = Underlay { NameSet = true, ViewInfo = UnderlayInfo { "
                                                       "Pos = { 1100, 330 }, Size = { 440, 165 } }, }, } }"})
    rows = {}

    async def vi(n):
        return view_info(R(await c.do("setting.copy", {"comp": PROBE, "tools": [n]}))["text"]).get(n)
    rows["underlay pasted at Pos {1100, 330} Size {440, 165}"] = await vi("LL_U")
    for x, y in ((0, 0), (1, 1), (2, 3), (0.25, 0.25), (0.5, 0.5), (0.75, 0.75), (-1.3, -2.6)):
        g = R(await c.do("tool.set_position", {"comp": PROBE, "tool": "LL_CTRL", "x": x, "y": y}))
        rows["tool SetPos %s,%s" % (x, y)] = [g.get("position"), await vi("LL_CTRL")]
        g = R(await c.do("tool.set_position", {"comp": PROBE, "tool": "LL_U", "x": x, "y": y}))
        rows["underlay SetPos %s,%s" % (x, y)] = [g.get("position"), await vi("LL_U")]
    await c.do("tool.delete", {"comp": PROBE, "tool": "LL_U"})
    rec("units", True, rows)


async def stage_showcase(c):
    """The kitchen-sink scene built with the hook (masks, groups, 3D, text, matte): the screenshot target."""
    await c.do("comp.clear", {"comp": PROBE})
    t0 = time.time()
    with open(os.path.join(SCENES, "kitchen_sink.json"), encoding="utf-8") as f:
        desc = json.load(f)
    # live 21.1: pasting a Loader (scene.build image layer; also a one-Loader setting.paste) opens a modal "Open File" browser
    # that blocks scripting, so the showcase drops its image layer (a connector paste issue, reported, not a layout one)
    desc["layers"] = [L for L in desc["layers"] if L.get("type") != "image"]
    r = await c.do("scene.build", {"comp": PROBE, "description": desc}, timeoutMs=300000)
    b = R(r)
    rec("showcase.build", r.get("ok") and (b.get("layout") or {}).get("scope") == "comp",
        {"layout": b.get("layout"), "tools": b.get("tools"), "warnings": b.get("warnings"), "wall": round(time.time() - t0, 2)})
    d = R(await c.do("comp.layout", {"comp": PROBE, "dryRun": True, "preview": True}))
    m = d.get("metrics") or {}
    rec("showcase.metrics", m.get("overlaps") == 0 and m.get("spinesStraight"), {"metrics": m, "preview": d.get("preview"),
                                                                                  "boxes": d.get("boxes")})


async def stage_cost(c):
    """Underlays are UI only: the same frame rendered with and without them, pixels and time."""
    d = R(await c.do("comp.layout", {"comp": PROBE, "dryRun": True}))
    boxes = [b["name"] for b in d.get("boxes") or []]
    ref = os.path.join(OUT, "cost_with.png")
    times = {}
    for tag in ("with1", "with2"):
        t0 = time.time()
        await c.do("render.frame", {"comp": PROBE, "frame": 40, "outPath": ref, "inline": False}, timeoutMs=300000)
        times[tag] = round(time.time() - t0, 2)
    await c.do("tool.delete", {"comp": PROBE, "tool": boxes})
    cmp = {}
    for tag in ("without1", "without2"):
        t0 = time.time()
        cmp = R(await c.do("render.compare", {"comp": PROBE, "reference": ref, "frame": 40, "inline": False, "outDir": OUT},
                           timeoutMs=300000))
        times[tag] = round(time.time() - t0, 2)
    await c.do("comp.layout", {"comp": PROBE})
    mae = (cmp.get("stats") or {}).get("meanAbsDiff")
    rec("cost.render", mae == 0 or (isinstance(mae, (int, float)) and mae < 1e-9), {"underlays": len(boxes), "times": times, "compare": cmp})


async def stage_film(c):
    """Three scenes on one clip as a film (scene.build film: true): the hook lays the whole comp out after each build."""
    await c.do("comp.clear", {"comp": FILM})
    starts = {"title_low_tide": 0, "card_smart_folders": 150, "showcase": 270}
    for f, s in starts.items():
        with open(os.path.join(SCENES, f + ".json"), encoding="utf-8") as fh:
            desc = json.load(fh)
        desc["start"] = s
        t0 = time.time()
        r = await c.do("scene.build", {"comp": FILM, "description": desc, "film": True}, timeoutMs=300000)
        b = R(r)
        rec("film.build." + f, r.get("ok"), {"layout": b.get("layout"), "wall": round(time.time() - t0, 2), "warnings": (b.get("warnings") or [])[:5]})
    t0 = time.time()
    d = R(await c.do("comp.layout", {"comp": FILM, "dryRun": True, "preview": True}))
    t1 = time.time()
    a = R(await c.do("comp.layout", {"comp": FILM}))
    m = a.get("metrics") or {}
    rec("film.layout", m.get("overlaps") == 0 and m.get("spinesStraight") and not m.get("boxProblems"),
        {"tools": a.get("tools"), "underlays": a.get("underlays"), "applyMs": a.get("ms"), "dryWall": round(t1 - t0, 2),
         "metrics": m, "preview": d.get("preview")})
    lint = R(await c.do("comp.lint_regions", {"comp": FILM}))
    rec("film.lint", lint.get("ok"), lint)


async def stage_cleanup(c):
    r = await c.do("timeline.delete", {"name": TL, "confirm": True})
    back = (results.get("base", {}).get("evidence") or {})
    restored = None
    if back.get("timeline"):   # hand the UI back where the slot found it
        restored = R(await c.do("timeline.set_current", {"name": back["timeline"]}))
    if back.get("page"):
        await c.do("page.open", {"page": back["page"]})
    rec("cleanup", r.get("ok"), {"delete": R(r), "restoredTimeline": restored})


STAGES = {"base": stage_base, "setup": stage_setup, "pile": stage_pile, "probe": stage_probe, "units": stage_units, "showcase": stage_showcase, "cost": stage_cost,
          "film": stage_film, "cleanup": stage_cleanup}


async def main(names):
    os.makedirs(OUT, exist_ok=True)
    async with Client(ENV) as c:
        for n in names:
            print("== " + n)
            await STAGES[n](c)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["base"]))
