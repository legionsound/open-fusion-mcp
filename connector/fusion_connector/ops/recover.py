"""batch.recover / batch.rollback: pick up after a call whose reply was lost (TIMEOUT, dead worker) using its journal [issue #1].
Both resolve the comp the journaled call targeted (or comp: to override)."""
import json
import os

from .base import op, OpError, COMP, OPS
from ..schema import P
from .. import journal

CALL_ID = P("callId", "string", "Journal id from the receipt of a TIMEOUT or TRANSPORT reply (details.receipt.callId). Default: the newest "
                                "call that never finished.")


def _load(a):
    cid = a.get("callId") or journal.latest_uncertain()
    if not cid:
        raise OpError("NOT_FOUND", "no unfinished call in the journal", hint="Pass callId from the receipt of the uncertain reply.")
    lines = journal.read(cid)
    rec = journal.reconcile(lines)
    if rec is None:
        d = journal.journal_dir()
        recent = sorted((f[:-6] for f in os.listdir(d) if f.endswith(".jsonl")), reverse=True)[:10]
        raise OpError("NOT_FOUND", f"no journal for call '{cid}'", details={"recent": recent},
                      hint="Journals live in <out>/journal (the newest 200 calls are kept).")
    snap = next((r for r in lines if r.get("t") == "snapshot"), {})
    return cid, lines, rec, snap


def _same_comp(a, b):
    norm = lambda r: None if r in (None, "", "current") else json.dumps(r, sort_keys=True)   # noqa: E731
    return norm(a) == norm(b)


def _later_changes(cid, ref):
    """Finished mutating calls journaled after cid on the same comp: undoing now would revert those first."""
    d = journal.journal_dir()
    head = journal.read(cid)[:1]
    t0 = head[0].get("at") if head and head[0].get("t") == "call" else None   # start times: rollback appends to cid's file
    if t0 is None:
        return []
    out = []
    for f in os.listdir(d):
        if not f.endswith(".jsonl") or f[:-6] == cid or os.path.getmtime(os.path.join(d, f)) < t0:
            continue
        ls = journal.read(f[:-6])
        h = ls[0] if ls and ls[0].get("t") == "call" else None
        o = OPS.get(h.get("op")) if h else None
        if not h or (h.get("at") or 0) <= t0 or o is None or o.read or h.get("op", "").startswith("batch.r"):
            continue
        if not _same_comp(h.get("comp"), ref):
            continue
        if any(r.get("t") == "end" and r.get("ok") for r in ls) or any(r.get("t") == "done" and r.get("ok") for r in ls):
            out.append({"callId": h.get("id"), "operation": h.get("op")})
    return out


def _names(comp):
    return sorted(t.GetAttrs()["TOOLS_Name"] for t in (comp.GetToolList(False) or {}).values())


@op("batch.recover", "After a TIMEOUT or a dead worker: read the call's journal (what finished, what was running, what never started) and "
    "re-read the comp it targeted: tool count against the snapshot taken before the call, added/removed tools when the snapshot holds "
    "names, whether the uncertain step's target tools exist, and whether the call's undo group was left open. Read-only; ends with "
    "plain advice (rollback, keep, or finish the batch with resume).",
    [CALL_ID, COMP(), P("names", "boolean", "Diff tool names against the snapshot when it holds names (one call per tool; default true).")],
    read=True, comp=False, category="batch")
def batch_recover(ctx, a):
    cid, lines, rec, snap = _load(a)
    ref = a.get("comp") if a.get("comp") not in (None, "") else rec.get("comp")
    comp = ctx.comp(ref)
    tools = comp.GetToolList(False) or {}
    live = {"tools": len(tools), "toolsBefore": snap.get("tools")}
    if snap.get("tools") is not None:
        live["delta"] = len(tools) - snap["tools"]
    if "names" in snap and a.get("names", True) and len(tools) <= journal.snapshot_limit():
        now = _names(comp)
        live["added"] = sorted(set(now) - set(snap["names"]))[:40]
        live["removed"] = sorted(set(snap["names"]) - set(now))[:40]
    unc = []
    for u in rec["uncertain"]:
        unc.append({"index": u["index"], "operation": u["operation"],
                    "targets": {t: comp.FindTool(t) is not None for t in u.get("targets") or []}})
    live["uncertain"] = unc
    later = _later_changes(cid, ref)
    advice = []
    if rec["undoGroup"] == "open":
        advice.append("The call's undo group is still open: batch.rollback {callId} closes and undoes it (verified against the snapshot); "
                      "batch.rollback {callId, keep: true} only closes it and keeps the changes; a batch resumed with resume closes it "
                      "and finishes. Do one of these before any other change.")
    for u in unc:
        if u["targets"]:
            hit = [t for t, e in u["targets"].items() if e]
            advice.append("Step %d (%s): %s. Inspect with tool.info before re-running it." % (
                u["index"], u["operation"], ("target%s %s exist%s" % ("s" if len(hit) > 1 else "", ", ".join(hit), "" if len(hit) > 1 else "s"))
                if hit else "none of its targets exist yet, so it most likely did not apply"))
        else:
            advice.append("Step %d (%s) names no target tools: compare the comp with the snapshot (live.added/removed) or inspect it." %
                          (u["index"], u["operation"]))
    first = rec["uncertain"][0]["index"] if rec["uncertain"] else (rec["notStarted"][0] if rec["notStarted"] else None)
    if first is not None and rec.get("steps", 1) > 1:
        advice.append("To finish the batch, send the same ops again with resume: '%s' (step %d on; finished steps are skipped and "
                      "nothing is duplicated)." % (cid, first))
    if later:
        advice.append("%d later change%s ran on this comp after the call, so an undo would revert those first." % (len(later), "s" if len(later) > 1 else ""))
    return {"callId": cid, "receipt": rec, "live": live, "laterChanges": later, "advice": advice}


@op("batch.rollback", "Undo the undo group of a journaled call (normally one whose reply was lost) and verify the comp against the "
    "snapshot taken before it: tool count, names when the snapshot holds them, and that tools the finished steps created are gone. "
    "Closes the group first when the worker died inside it (keep: true stops there and keeps the changes). Undoes only when a step "
    "finished or the comp differs from the snapshot (an undo group that recorded no change may not be an undo event, so an undo could "
    "revert an earlier change), and refuses when later changes ran on the same comp (an undo would revert those first); force: true "
    "overrides both.",
    [CALL_ID, COMP(), P("keep", "boolean", "Only close an open undo group; keep the call's changes (default false)."),
     P("force", "boolean", "Undo even when a safety check says not to: later changes ran on the comp, or nothing shows the call "
                           "changed anything (default false).")],
    comp=False, undo=False, category="batch")
def batch_rollback(ctx, a):
    from ..worker import created_names, diff_against, verify_against
    cid, lines, rec, snap = _load(a)
    ref = a.get("comp") if a.get("comp") not in (None, "") else rec.get("comp")
    later = _later_changes(cid, ref)
    if later and not a.get("force") and not a.get("keep"):
        raise OpError("CONFLICT", "%d change%s ran on this comp after call %s: an undo now would revert those first"
                      % (len(later), "s" if len(later) > 1 else "", cid), details={"laterChanges": later},
                      hint="Undo by hand in the right order (comp.undo), or pass force: true if you mean to.")
    done = rec.get("rollback") or {}
    if done.get("rolledBack") and not a.get("keep") and not a.get("force"):
        raise OpError("CONFLICT", f"call {cid} was already rolled back" + (" by batch.rollback" if done.get("by") else " (atomic batch)"),
                      details={"rollback": done}, hint="A second undo would revert an earlier change; force: true if you mean to.")
    comp = ctx.comp(ref)
    out = {"callId": cid, "closedUndoGroup": False, "rolledBack": False}
    if rec["undoGroup"] == "open":
        comp.EndUndo(True)
        journal.append(cid, {"t": "undo", "state": "closed", "by": "batch.rollback"})
        out["closedUndoGroup"] = True
    if a.get("keep"):
        out["note"] = "kept the call's changes" + ("; closed its open undo group" if out["closedUndoGroup"] else " (no open undo group)")
        return out
    if rec["undoGroup"] == "none":
        raise OpError("INVALID_ARGS", f"call {cid} never opened an undo group (a read, or it stopped before its first change): nothing to undo")
    finished = [s["index"] for s in rec["completed"] if OPS.get(s.get("operation")) is not None and not OPS[s["operation"]].read]
    same, ev, compared = diff_against(comp, snap)
    if not finished and same and not a.get("force"):
        out["evidence"] = ev
        out["note"] = ("nothing undone: no step of the call finished, and %s. An undo group that recorded no change may not be an "
                       "undo event, so an undo could revert an earlier change. If batch.recover shows the uncertain step did apply, "
                       "pass force: true." % ("the tool list matches the snapshot" if compared else "it took no snapshot to compare with"))
        return out
    created = created_names([s.get("changed") for s in rec["completed"]])
    comp.Undo(1)
    out.update(verify_against(comp, snap, created))
    journal.append(cid, {"t": "rollback", "by": "batch.rollback", "rolledBack": True, "verified": out["verified"]})
    if out["verified"] is False:
        out["warning"] = "the comp does not match the snapshot taken before the call: inspect evidence before going on"
    elif out["verified"] is None:
        out["note"] = "nothing to verify against: the call took no snapshot (single operations take none); inspect the comp"
    return out
