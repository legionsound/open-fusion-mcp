"""Per-call journal: the worker writes one JSON line per step as it runs (flushed and fsynced), so when a call times out or the
worker dies, the server can still say which steps finished, which one was running and which never started [issue #1].

Files: <out>/journal/<callId>.jsonl, newest KEEP kept. Lines:
  {"t": "call", "id", "op", "comp", "children": [op names], "argsHash": [per child], "resumes": callId, "at"}   header
  {"t": "snapshot", "tools": count, "names": [...] | absent}          comp state before the call's first change
  {"t": "undo", "state": "open" | "closed"}                           the call's undo group
  {"t": "start", "i", "op", "targets": [...]}                         a step began
  {"t": "end", "i", "ok", "changed": {...} | "error": {...}}          a step finished
  {"t": "skip", "i", "reason"}                                       a resumed batch skipped a step that already ran
  {"t": "rollback", ...}                                              an atomic batch undid itself (or batch.rollback, "by")
  {"t": "resumed", "by"}                                              appended when batch.run resume picked the call up
  {"t": "done", "ok"}                                                 the call returned normally"""
import hashlib
import json
import os
import time
import uuid

from . import config

KEEP = 200
TARGET_KEYS = ("tool", "tools", "name", "names", "to", "from", "target", "source", "host", "parent", "into", "merge", "node")
CHANGE_KEYS = ("created", "added", "deleted", "removed", "renamed", "tool", "tools", "name", "names", "set", "pasted", "connected",
               "disconnected", "keys", "output")


def journal_dir():
    d = os.path.join(config.out_dir(), "journal")
    os.makedirs(d, exist_ok=True)
    return d


def path_of(call_id):
    return os.path.join(journal_dir(), "%s.jsonl" % call_id)


def new_id():
    return time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]


def args_hash(args):
    """Fingerprint of one step's arguments: a resumed batch must send the finished steps unchanged [issue #14]."""
    return hashlib.sha1(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _strings(v, out, limit=20):
    if isinstance(v, str) and v:
        out.append(v)
    elif isinstance(v, (list, tuple)):
        for x in v:
            if len(out) >= limit:
                break
            _strings(x, out, limit)
    elif isinstance(v, dict):   # {tool, input} pairs in connect-style args: the tool, never the input id
        _strings([v[k] for k in ("tool", "name") if k in v], out, limit)
    return out


def targets_of(args):
    """Tool names an operation's arguments point at (best effort): what to look for when its outcome is uncertain."""
    out = []
    for k in TARGET_KEYS:
        if isinstance(args, dict) and k in args:
            _strings(args[k], out)
    return list(dict.fromkeys(out))[:20]


def changes_of(result):
    """What a finished step reports it changed: the result keys that name tools, inputs or counts, trimmed."""
    if not isinstance(result, dict):
        return {}
    out = {}
    for k in CHANGE_KEYS:
        if k in result:
            v = result[k]
            if isinstance(v, (list, tuple)):
                out[k] = list(v)[:20] + (["... %d more" % (len(v) - 20)] if len(v) > 20 else [])
            elif isinstance(v, dict):
                out[k] = dict(list(v.items())[:20])
            elif isinstance(v, (str, int, float, bool)) or v is None:
                out[k] = v
    return out


class Journal:
    """Worker side. Every write is flushed and fsynced: the server reads the file after killing the worker."""

    def __init__(self, call_id, op, comp=None, children=None, hashes=None, resumes=None):
        self.id = call_id
        self.path = path_of(call_id)
        _prune()
        self.f = open(self.path, "a", encoding="utf-8")
        head = {"t": "call", "id": call_id, "op": op, "comp": comp, "children": children, "pid": os.getpid()}
        if hashes is not None:
            head["argsHash"] = hashes
        if resumes:
            head["resumes"] = resumes
        self.write(head)

    def skip(self, i, reason):
        self.write({"t": "skip", "i": i, "reason": reason})

    def write(self, rec):
        rec = dict(rec, at=round(time.time(), 3))
        self.f.write(json.dumps(rec, separators=(",", ":"), default=str) + "\n")
        self.f.flush()
        os.fsync(self.f.fileno())

    def snapshot(self, comp, names=False, limit=None):
        rec = take_snapshot(comp, names, limit)
        self.write(rec)
        return rec

    def start(self, i, op, args):
        self.write({"t": "start", "i": i, "op": op, "targets": targets_of(args)})

    def end(self, i, ok, result=None, error=None):
        rec = {"t": "end", "i": i, "ok": ok}
        if ok:
            rec["changed"] = changes_of(result)
        else:
            rec["error"] = error
        self.write(rec)

    def undo(self, state):
        self.write({"t": "undo", "state": state})

    def close(self, ok):
        try:
            self.write({"t": "done", "ok": ok})
        finally:
            self.f.close()


def take_snapshot(comp, names=False, limit=None):
    """Tool count (cheap) and, when asked and the comp is small enough, every tool name (one call per tool)."""
    tools = comp.GetToolList(False) or {}
    rec = {"t": "snapshot", "tools": len(tools)}
    limit = limit if limit is not None else snapshot_limit()
    if names and len(tools) <= limit:
        rec["names"] = sorted(t.GetAttrs()["TOOLS_Name"] for t in tools.values())
    elif names:
        rec["namesSkipped"] = "%d tools > the %d-tool snapshot limit (FUSION_MCP_SNAPSHOT_LIMIT)" % (len(tools), limit)
    return rec


def snapshot_limit():
    try:
        return int(os.environ.get("FUSION_MCP_SNAPSHOT_LIMIT", "1500"))
    except ValueError:
        return 1500


def _prune():
    try:
        d = journal_dir()
        files = sorted((f for f in os.listdir(d) if f.endswith(".jsonl")), key=lambda f: os.path.getmtime(os.path.join(d, f)))
        for f in files[:max(0, len(files) - KEEP + 1)]:
            os.unlink(os.path.join(d, f))
    except OSError:
        pass


def append(call_id, rec):
    """Add a line to an earlier call's journal: batch.rollback records what it did, so a second rollback never repeats it."""
    with open(path_of(call_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(rec, at=round(time.time(), 3)), separators=(",", ":"), default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


# ---------------------------------------------------------------- server side

def read(call_id):
    """Journal lines; a torn last line (the worker died mid-write) is dropped."""
    try:
        with open(path_of(call_id), encoding="utf-8") as f:
            raw = f.read().splitlines()
    except OSError:
        return []
    out = []
    for ln in raw:
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def _ranges(ix):
    """[0, 1, 2, 5] -> '0-2, 5'"""
    out, s = [], None
    for i, x in enumerate(ix):
        if s is None:
            s = x
        if i + 1 == len(ix) or ix[i + 1] != x + 1:
            out.append(str(s) if s == x else "%d-%d" % (s, x))
            s = None
    return ", ".join(out)


def reconcile(lines):
    """Journal lines -> the receipt: what definitely finished, what was running, what never started."""
    head = next((r for r in lines if r.get("t") == "call"), None)
    if head is None:
        return None
    children = head.get("children") or [head.get("op")]
    steps = {}
    undo, snap, rollback, done = None, None, None, None
    for r in lines:
        t = r.get("t")
        if t == "start":
            steps[r["i"]] = {"index": r["i"], "operation": r.get("op"), "targets": r.get("targets") or []}
        elif t == "end" and r.get("i") in steps:
            s = steps[r["i"]]
            s["ok"] = r.get("ok")
            if r.get("ok"):
                s["changed"] = r.get("changed") or {}
            else:
                s["error"] = r.get("error")
        elif t == "undo":
            undo = r.get("state")
        elif t == "snapshot":
            snap = {k: v for k, v in r.items() if k not in ("t", "at")}
        elif t == "rollback":
            rollback = {k: v for k, v in r.items() if k not in ("t", "at")}
        elif t == "done":
            done = r.get("ok")
    completed = [s for s in steps.values() if s.get("ok") is True]
    failed = [s for s in steps.values() if s.get("ok") is False]
    running = [s for s in steps.values() if "ok" not in s]
    skipped = sorted({r["i"] for r in lines if r.get("t") == "skip"})
    not_started = [i for i in range(len(children)) if i not in steps and i not in skipped]
    rec = {"callId": head.get("id"), "operation": head.get("op"), "comp": head.get("comp"), "steps": len(children),
           "completed": [{k: s[k] for k in ("index", "operation", "changed") if k in s} for s in completed],
           "failed": [{k: s[k] for k in ("index", "operation", "error") if k in s} for s in failed],
           "uncertain": [{k: s[k] for k in ("index", "operation", "targets") if k in s} for s in running],
           "notStarted": not_started, "undoGroup": undo or "none", "finished": done is not None}
    if skipped:
        rec["skipped"] = skipped
    if head.get("resumes"):
        rec["resumes"] = head["resumes"]
    if snap:
        rec["snapshot"] = {k: v for k, v in snap.items() if k != "names"} | ({"names": len(snap["names"])} if "names" in snap else {})
    if rollback:
        rec["rollback"] = rollback
    rec["summary"] = summary(rec, head.get("children") is not None)
    return rec


def summary(rec, batch):
    """One plain sentence or three for the reply message."""
    if not batch:
        if rec["completed"]:
            return "The operation finished before the reply was lost; its result is in the receipt."
        if rec["uncertain"]:
            u = rec["uncertain"][0]
            on = " on %s" % ", ".join("'%s'" % t for t in u["targets"][:3]) if u.get("targets") else ""
            return "%s%s started and never reported back: it may have partly applied." % (u["operation"], on)
        return "The operation never started (the worker stopped before reaching it)."
    parts = []
    if rec.get("skipped"):
        parts.append("step%s %s skipped (done before)" % ("s" if len(rec["skipped"]) > 1 else "", _ranges(rec["skipped"])))
    if rec["completed"]:
        parts.append("step%s %s finished" % ("s" if len(rec["completed"]) > 1 else "", _ranges([s["index"] for s in rec["completed"]])))
    if rec["failed"]:
        parts.append("step%s %s failed" % ("s" if len(rec["failed"]) > 1 else "", _ranges([s["index"] for s in rec["failed"]])))
    for u in rec["uncertain"]:
        on = " on %s" % ", ".join("'%s'" % t for t in u["targets"][:3]) if u.get("targets") else ""
        parts.append("step %d (%s%s) was running and may have partly applied" % (u["index"], u["operation"], on))
    if rec["notStarted"]:
        parts.append("step%s %s never started" % ("s" if len(rec["notStarted"]) > 1 else "", _ranges(rec["notStarted"])))
    s = "Receipt: " + "; ".join(parts) + "." if parts else "Receipt: no step started."
    if rec["undoGroup"] == "open":
        s += " The batch's undo group was left open."
    return s


def latest_uncertain(lines_of=None):
    """The newest journal that never reached 'done' (what batch.recover inspects when no callId is given)."""
    d = journal_dir()
    files = sorted((f for f in os.listdir(d) if f.endswith(".jsonl")), key=lambda f: os.path.getmtime(os.path.join(d, f)), reverse=True)
    for f in files:
        cid = f[:-6]
        ls = read(cid)
        if ls and ls[0].get("op") in ("batch.recover", "batch.rollback"):   # never the recovery call itself
            continue
        if ls and not any(r.get("t") in ("done", "resumed") or r.get("by") for r in ls):   # finished, or handled by rollback/resume
            return cid
    return None
