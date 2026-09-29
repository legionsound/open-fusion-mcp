"""Live check of cache.* and the render overhead fixes. Testbed only, own timeline SB_Cache_Lab, one call at a time, cache
root and renders inside out/live_cache (never ~/Movies). Spawns this copy's server (tests/client.py).

Run: .venv/bin/python tests/cache_live.py setup loop stale deliver restore cleanup   (about 6 minutes)
Results merge into tests/cache_live_results.json."""
import asyncio
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Client  # noqa: E402
from PIL import Image, ImageChops, ImageStat  # noqa: E402

OUT = os.path.join(ROOT, "out", "live_cache")
RES = os.path.join(ROOT, "tests", "cache_live_results.json")
TL = "SB_Cache_Lab"
ENV = {"FUSION_MCP_PROJECT_ALLOWLIST": "Testbed", "FUSION_MCP_OUT_DIR": OUT, "FUSION_MCP_CACHE_DIR": os.path.join(OUT, "cache_root")}
REF = {"timeline": TL, "track": 1, "item": 0}
# a branch with a keyed text size (so a frame-mapping slip shows) under a blur, cached at CB_Blur
GRAPH = """{ Tools = ordered() {
 CB_Base = Background { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, TopLeftRed = Input { Value = 0.05, }, TopLeftGreen = Input { Value = 0.05, }, TopLeftBlue = Input { Value = 0.08, }, }, },
 CB_BG = Background { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, TopLeftRed = Input { Value = 0.9, }, TopLeftGreen = Input { Value = 0.4, }, TopLeftBlue = Input { Value = 0.1, }, }, },
 CB_TxtSize = BezierSpline { KeyFrames = { [0] = { 0.05, Flags = { Linear = true } }, [29] = { 0.2, Flags = { Linear = true } }, }, },
 CB_Txt = TextPlus { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, StyledText = Input { Value = "CACHE ME", }, Size = Input { SourceOp = "CB_TxtSize", Source = "Value", }, }, },
 CB_Mrg = Merge { Inputs = { Background = Input { SourceOp = "CB_BG", Source = "Output", }, Foreground = Input { SourceOp = "CB_Txt", Source = "Output", }, }, },
 CB_Blur = Blur { Inputs = { Input = Input { SourceOp = "CB_Mrg", Source = "Output", }, XBlurSize = Input { Value = 4, }, }, },
 CB_Out = Merge { Inputs = { Background = Input { SourceOp = "CB_Base", Source = "Output", }, Foreground = Input { SourceOp = "CB_Blur", Source = "Output", }, Size = Input { Value = 0.8, }, }, },
} }"""
results = json.load(open(RES)) if os.path.exists(RES) else {}
state = {}


def rec(name, good, evidence):
    results[name] = {"status": "pass" if good else "fail", "evidence": evidence, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
    print(("PASS " if good else "FAIL ") + name + ": " + json.dumps(evidence, default=str)[:700])
    json.dump(results, open(RES, "w"), indent=1, default=str)


def mae(a, b):
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    return round(sum(ImageStat.Stat(ImageChops.difference(ia, ib)).mean) / 3, 4)


async def frame(c, f, tag):
    t0 = time.time()
    r = await c.do("render.frame", {"comp": REF, "frame": f, "inline": False, "outPath": os.path.join(OUT, "%s_%04d.png" % (tag, f))},
                   timeoutMs=300000)
    res = r.get("result") or {}
    return {"path": res.get("path"), "s": round(time.time() - t0, 2), "warnings": res.get("warnings") or [], "error": r.get("error")}


async def stage_setup(c):
    tls = await c.do("timeline.list", {})
    if TL in json.dumps(tls.get("result") or {}):
        await c.do("timeline.delete", {"name": TL, "confirm": True})   # our own lab timeline from an earlier try
    r = await c.do("timeline.create", {"name": TL, "width": 1920, "height": 1080, "fps": 30, "makeCurrent": True, "fusionComp": False})
    rec("setup.timeline", r.get("ok"), r.get("result") or r.get("error"))
    r = await c.do("timeline.add_fusion_clip", {"timeline": TL, "frames": 30, "track": 1, "recordFrame": 0, "clipName": "SB_cache"}, timeoutMs=180000)
    rec("setup.clip", r.get("ok"), r.get("result") or r.get("error"))
    r = await c.do("setting.paste", {"comp": REF, "text": GRAPH, "connect": [["MediaOut1", "Input", "CB_Out"]]})
    rec("setup.graph", r.get("ok"), r.get("result") or r.get("error"))


async def stage_loop(c):
    """Live renders (render.frame overhead: kept Saver + no 4 s modal poll), then cache.to_disk and the same frames through
    the Loader: pixel-identical at the range ends and the middle (a GlobalIn/Out slip would show)."""
    live = {f: await frame(c, f, "live") for f in (0, 10, 29)}
    rec("loop.live", all(v["path"] for v in live.values()), {f: v["s"] for f, v in live.items()})
    t0 = time.time()
    r = await c.do("cache.to_disk", {"comp": REF, "tool": "CB_Blur", "start": 0, "end": 29}, timeoutMs=600000)
    res = r.get("result") or {}
    rec("loop.to_disk", r.get("ok") and not res.get("warnings"), dict(res, callSeconds=round(time.time() - t0, 2)) if r.get("ok") else r.get("error"))
    cached = {f: await frame(c, f, "cached") for f in (0, 10, 29)}
    d = {f: mae(live[f]["path"], cached[f]["path"]) for f in cached if live[f]["path"] and cached[f]["path"]}
    rec("loop.pixel_identical", len(d) == 3 and max(d.values()) < 0.5 and not any(v["warnings"] for v in cached.values()),
        {"mae": d, "seconds": {f: v["s"] for f, v in cached.items()}})
    st = await c.do("cache.status", {"comp": REF})
    row = ((st.get("result") or {}).get("caches") or [{}])[0]
    rec("loop.status_fresh", row.get("stale") is False and row.get("framesOnDisk") == 30, row)


async def stage_stale(c):
    """An upstream edit: status STALE (Lua fingerprint here), render.frame warns, refresh re-renders and matches live."""
    await c.do("input.set", {"comp": REF, "tool": "CB_Txt", "input": "StyledText", "value": "EDITED"})
    st = await c.do("cache.status", {"comp": REF})
    row = ((st.get("result") or {}).get("caches") or [{}])[0]
    rec("stale.status", row.get("stale") is True and "CB_Txt" in (row.get("changed") or []), row)
    f = await frame(c, 10, "stale")
    rec("stale.render_warns", any("STALE" in w for w in f["warnings"]), f["warnings"])
    r = await c.do("cache.refresh", {"comp": REF}, timeoutMs=600000)
    rec("stale.refresh", r.get("ok") and [x.get("rev") for x in (r.get("result") or {}).get("refreshed") or []] == [2], r.get("result") or r.get("error"))
    state["refreshed"] = await frame(c, 10, "refreshed")
    rec("stale.fresh_again", not state["refreshed"]["warnings"], state["refreshed"])


async def stage_deliver(c):
    """deliver.start preflight with a stale cache (bridge fingerprint), then a 3-frame Deliver of our own job with the cache fresh:
    the parked FC_RenderSaver must write nothing."""
    await c.do("input.set", {"comp": REF, "tool": "CB_BG", "input": "TopLeftRed", "value": 0.8})
    tgt = os.path.join(OUT, "deliver")
    os.makedirs(tgt, exist_ok=True)
    j = await c.do("deliver.add_job", {"timeline": TL, "format": "tif", "codec": "RGB16", "targetDir": tgt, "name": "cache_check",
                                       "markIn": 108000, "markOut": 108002})
    jid = (j.get("result") or {}).get("jobId")
    r = await c.do("deliver.start", {"jobIds": [jid], "overwrite": True})
    rec("deliver.refuses_stale", not r.get("ok") and "FORBIDDEN" in json.dumps(r) and "staleCaches" in json.dumps(r), r.get("error") or r)
    await c.do("cache.refresh", {"comp": REF}, timeoutMs=600000)
    state["refreshed"] = await frame(c, 10, "refreshed2")
    before = set(os.listdir(OUT))
    r = await c.do("deliver.start", {"jobIds": [jid], "overwrite": True, "wait": True}, timeoutMs=600000)
    new = sorted(set(os.listdir(OUT)) - before)
    rec("deliver.parked_saver_silent", r.get("ok") and not [n for n in new if n.startswith("fc_")], {"start": r.get("result") or r.get("error"),
                                                                                                    "newFilesInOut": new, "deliverDir": os.listdir(tgt)})
    await c.do("deliver.remove_job", {"jobId": jid})


async def stage_restore(c):
    r = await c.do("cache.restore", {"comp": REF, "tool": "CB_Blur", "clear": True})
    rec("restore", r.get("ok") and (r.get("result") or {}).get("rewired") == [["CB_Out", "Foreground"]], r.get("result") or r.get("error"))
    live = await frame(c, 10, "restored")
    ref = state.get("refreshed", {}).get("path")
    d = mae(ref, live["path"]) if ref and live["path"] else None
    rec("restore.matches_refreshed", d is not None and d < 0.5, {"mae": d})
    r = await c.do("cache.clear", {"comp": REF, "all": True})
    rec("clear", r.get("ok"), r.get("result") or r.get("error"))


async def stage_loaderpaste(c):
    """A pasted Loader must not open Resolve's modal file browser (paste runs under comp:Lock()). With the modal up, the
    next call hangs; here it must answer in seconds and the Loader must exist."""
    png = os.path.join(OUT, "live_0000.png")
    text = '{ Tools = ordered() { CB_PasteLd = Loader { Clips = { Clip { Filename = "%s", FormatID = "PNGFormat", Length = 1, }, }, }, } }' % png
    r = await c.do("setting.paste", {"comp": REF, "text": text}, timeoutMs=30000)
    t0 = time.time()
    info = await c.do("tool.info", {"comp": REF, "tool": "CB_PasteLd"}, timeoutMs=15000)
    rec("loaderpaste.no_modal", r.get("ok") and info.get("ok") and time.time() - t0 < 10,
        {"paste": (r.get("result") or {}).get("added") or r.get("error"), "infoSeconds": round(time.time() - t0, 2)})
    await c.do("tool.delete", {"comp": REF, "tool": "CB_PasteLd"})


async def stage_cleanup(c):
    r = await c.do("timeline.delete", {"name": TL, "confirm": True})
    rec("cleanup", r.get("ok"), r.get("result") or r.get("error"))


async def main(stages):
    os.makedirs(OUT, exist_ok=True)
    async with Client(ENV) as c:
        for s in stages:
            await globals()["stage_" + s](c)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["setup", "loop", "stale", "deliver", "restore", "cleanup"]))
