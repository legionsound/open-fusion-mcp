"""Live check of batch receipts, batch.recover / batch.rollback and atomic batches [issues #1, #2] against real Fusion: what the
offline fake cannot prove. Testbed only, own timeline Receipts_Lab, one call at a time. Spawns this copy's server (tests/client.py)
with the test.* fault ops enabled for the live Testbed (FUSION_MCP_TEST_FAULTS_LIVE=1; they refuse any other project).

Questions it answers:
  stall     a worker killed inside a batch: does Fusion keep the batch's undo group open, and do the finished steps' tools exist?
  rollback  batch.rollback after the stall: EndUndo then Undo(1) -> are exactly the batch's tools gone (verified)?
  keep      batch.rollback keep: true closes the group: does one comp.undo afterwards remove the batch's tools as ONE event?
  atomic    atomic batch failing at step 1 -> verified rollback in real Fusion
  paste     atomic batch whose first step is setting.paste (a deferred Lua Execute): is the paste inside the undo group?
  probe     is an undo group that recorded no change an undo event in Fusion? (test.undo_probe; also records GetUndoStack)
  noop      atomic batch failing at step 0 before any change: an earlier change must survive (nothing is undone)
  resume    a batch applies two steps, times out, and is finished with resume: no step repeats, nothing is renamed RL_R1_1

Run: .venv/bin/python tests/receipts_live.py setup stall rollback keep atomic paste probe noop resume cleanup   (about 3 minutes)
Results merge into tests/receipts_live_results.json."""
import asyncio
import json
import os
import shutil
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Client  # noqa: E402

OUT = os.path.join(ROOT, "out", "live_receipts")
RES = os.path.join(ROOT, "tests", "receipts_live_results.json")
TL = "Receipts_Lab"
ENV = {"FUSION_MCP_PROJECT_ALLOWLIST": "Testbed", "FUSION_MCP_OUT_DIR": OUT, "FUSION_MCP_TEST_FAULTS": "1", "FUSION_MCP_TEST_FAULTS_LIVE": "1"}
REF = {"timeline": TL, "track": 1, "item": 0}
PASTE = """{ Tools = ordered() {
 RL_PasteA = Background { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, }, },
 RL_PasteB = Background { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, }, },
} }"""
results = json.load(open(RES)) if os.path.exists(RES) else {}


def rec(name, good, evidence):
    results[name] = {"status": "pass" if good else "fail", "evidence": evidence, "when": time.strftime("%Y-%m-%d %H:%M:%S")}
    print(("PASS " if good else "FAIL ") + name + ": " + json.dumps(evidence, default=str)[:900])
    json.dump(results, open(RES, "w"), indent=1, default=str)


async def exists(c, names):
    r = await c.do("tool.list", {"comp": REF, "name": "RL_*"})
    have = {t["name"] for t in (r.get("result") or {}).get("tools", [])}
    return {n: n in have for n in names}


def batch(*steps):
    return [{"operation": o, "args": a} for o, a in steps]


STALL = batch(("test.add", {"names": ["RL_A"]}), ("test.add", {"names": ["RL_B"]}), ("test.hang", {"seconds": 20, "tool": "RL_X"}),
              ("test.add", {"names": ["RL_C"]}))


async def stall(c):
    r = await c.do("batch.run", {"comp": REF, "ops": STALL, "snapshot": "names"}, timeoutMs=6000)
    e = r.get("error") or {}
    await asyncio.sleep(16)   # let the hang end inside the dead worker's slot; Fusion itself never stalled
    return e, (e.get("details") or {}).get("receipt") or {}


async def stage_setup(c):
    shutil.rmtree(os.path.join(OUT, "test_hang_once"), ignore_errors=True)   # one-time stalls start fresh
    tls = await c.do("timeline.list", {})
    if TL in json.dumps(tls.get("result") or {}):
        await c.do("timeline.delete", {"name": TL, "confirm": True})
    r1 = await c.do("timeline.create", {"name": TL, "width": 1920, "height": 1080, "fps": 30, "makeCurrent": True, "fusionComp": False})
    r2 = await c.do("timeline.add_fusion_clip", {"timeline": TL, "frames": 60, "track": 1})
    r3 = await c.do("comp.set_current", {"comp": REF})
    rec("setup", all(x.get("ok") for x in (r1, r2, r3)), {"create": r1.get("ok"), "clip": r2.get("ok"), "current": r3.get("ok")})


async def stage_stall(c):
    e, r = await stall(c)
    ex = await exists(c, ["RL_A", "RL_B", "RL_C"])
    rec("stall", e.get("code") == "TIMEOUT" and [s["index"] for s in r.get("completed", [])] == [0, 1] and r.get("notStarted") == [3]
        and ex == {"RL_A": True, "RL_B": True, "RL_C": False},
        {"code": e.get("code"), "summary": r.get("summary"), "undoGroup": r.get("undoGroup"), "exists": ex})
    state["stall"] = r.get("callId")
    rv = await c.do("batch.recover", {"callId": r.get("callId")})
    rec("recover", rv.get("ok") and (rv["result"]["live"].get("added") == ["RL_A", "RL_B"]),
        {"live": (rv.get("result") or {}).get("live"), "advice": (rv.get("result") or {}).get("advice"), "error": rv.get("error")})


async def stage_rollback(c):
    r = await c.do("batch.rollback", {"callId": state.get("stall")})
    ex = await exists(c, ["RL_A", "RL_B"])
    res = r.get("result") or {}
    rec("rollback", r.get("ok") and res.get("verified") and not any(ex.values()), {"result": res, "error": r.get("error"), "exists": ex})


async def stage_keep(c):
    e, r = await stall(c)
    k = await c.do("batch.rollback", {"callId": r.get("callId"), "keep": True})
    before = await exists(c, ["RL_A", "RL_B"])
    u = await c.do("comp.undo", {"comp": REF, "count": 1})
    after = await exists(c, ["RL_A", "RL_B"])
    rec("keep", k.get("ok") and all(before.values()) and not any(after.values()),
        {"keep": k.get("result") or k.get("error"), "before": before, "afterOneUndo": after, "undo": u.get("ok")})


async def stage_atomic(c):
    r = await c.do("batch.run", {"comp": REF, "atomic": True, "ops": batch(("test.add", {"names": ["RL_D"]}),
                                                                           ("test.partial", {"names": ["RL_E", "RL_F"], "failAfter": 1}))})
    rb = ((r.get("error") or {}).get("details") or {}).get("rollback") or {}
    ex = await exists(c, ["RL_D", "RL_E"])
    rec("atomic", rb.get("verified") is True and not any(ex.values()), {"rollback": rb, "exists": ex, "message": (r.get("error") or {}).get("message")})


async def stage_paste(c):
    r = await c.do("batch.run", {"comp": REF, "atomic": True, "ops": batch(("setting.paste", {"text": PASTE}),
                                                                           ("test.partial", {"names": ["RL_G"], "failAfter": 0}))})
    rb = ((r.get("error") or {}).get("details") or {}).get("rollback") or {}
    ex = await exists(c, ["RL_PasteA", "RL_PasteB"])
    rec("paste_in_undo_group", rb.get("verified") is True and not any(ex.values()), {"rollback": rb, "exists": ex,
                                                                                     "message": (r.get("error") or {}).get("message")})


async def stage_probe(c):
    r = await c.do("test.undo_probe", {"comp": REF, "name": "RL_Probe"})
    res = r.get("result") or {}
    ex = await exists(c, ["RL_Probe"])
    rec("probe", r.get("ok") and not ex["RL_Probe"], {"emptyGroupIsUndoEvent": res.get("emptyGroupIsUndoEvent"),
                                                      "undoStackBefore": res.get("undoStackBefore"),
                                                      "undoStackAfterEmptyGroup": res.get("undoStackAfterEmptyGroup"), "error": r.get("error")})


async def stage_noop(c):
    pre = await c.do("batch.run", {"comp": REF, "ops": batch(("test.add", {"names": ["RL_Pre"]}))})
    r = await c.do("batch.run", {"comp": REF, "atomic": True, "ops": batch(("test.partial", {"names": ["RL_N"], "failAfter": 0}))})
    rb = ((r.get("error") or {}).get("details") or {}).get("rollback") or {}
    ex = await exists(c, ["RL_Pre", "RL_N"])
    rec("noop_atomic_keeps_earlier_change", pre.get("ok") and rb.get("rolledBack") is False and ex == {"RL_Pre": True, "RL_N": False},
        {"rollback": rb, "exists": ex, "message": (r.get("error") or {}).get("message")})


async def stage_resume(c):
    ops = batch(("test.add", {"names": ["RL_R1"]}), ("test.add", {"names": ["RL_R2"]}),
                ("test.hang", {"seconds": 20, "tool": "RL_R3", "once": True, "add": "after"}), ("test.add", {"names": ["RL_R4"]}))
    r = await c.do("batch.run", {"comp": REF, "ops": ops}, timeoutMs=6000)
    cid = (((r.get("error") or {}).get("details") or {}).get("receipt") or {}).get("callId")
    await asyncio.sleep(16)
    rs = await c.do("batch.run", {"comp": REF, "ops": ops, "resume": cid}, timeoutMs=60000)
    res = (rs.get("result") or {}).get("resume") or {}
    lst = await c.do("tool.list", {"comp": REF, "name": "RL_R*"})
    names = sorted(t["name"] for t in (lst.get("result") or {}).get("tools", []))
    rec("resume_no_duplicates", bool(cid) and rs.get("ok") and res.get("verified") is True and names == ["RL_R1", "RL_R2", "RL_R3", "RL_R4"],
        {"timeout": (r.get("error") or {}).get("code"), "resume": res, "tools": names, "error": rs.get("error")})


async def stage_cleanup(c):
    r = await c.do("timeline.delete", {"name": TL, "confirm": True})
    rec("cleanup", r.get("ok"), {"error": r.get("error")})


state = {}


async def main(stages):
    async with Client(ENV) as c:
        for s in stages:
            await globals()["stage_" + s](c)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["setup", "stall", "rollback", "keep", "atomic", "paste", "probe", "noop", "resume", "cleanup"]))
