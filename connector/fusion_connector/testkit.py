"""Fault injection for the offline tests [issue #3]: a stand-in for Resolve/Fusion whose comp state lives in a JSON file (so, like the
real app, it survives a killed worker), and test.* operations that hang, crash the worker or apply half a change and then fail.

Active only when FUSION_MCP_FAKE_RESOLVE=<state file> (Ctx.resolve returns FakeResolve) and FUSION_MCP_TEST_FAULTS=1 (registers the
test.* ops). Every test.* op refuses to run against a real Resolve, except for the live check (tests/receipts_live.py), which also sets
FUSION_MCP_TEST_FAULTS_LIVE=1 and only works in the project named Testbed."""
import json
import os
import time

from . import config
from .ops.base import op, OpError, COMP
from .schema import P


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"tools": {}, "groups": [], "data": {}, "endUndoWithoutGroup": 0}


def _save(path, st):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class FakeTool:
    def __init__(self, comp, name):
        self.comp, self.Name = comp, name

    def GetAttrs(self):
        st = _load(self.comp.path)
        return {"TOOLS_Name": self.Name, "TOOLS_RegID": (st["tools"].get(self.Name) or {}).get("reg", "Fake")}

    def SetAttrs(self, attrs):
        new = attrs.get("TOOLS_Name")
        if new and new != self.Name:
            taken = {n.lower() for n in _load(self.comp.path)["tools"] if n != self.Name}
            base, k = new, 1
            while new.lower() in taken:   # like Fusion: a colliding name gets a suffix instead of an error (realities §9)
                new, k = "%s_%d" % (base, k), k + 1
            self.comp._act(["rename", self.Name, new])
            self.Name = new
        return True

    def Delete(self):
        self.comp._act(["delete", self.Name, (_load(self.comp.path)["tools"].get(self.Name) or {}).get("reg", "Fake")])
        return True


class FakeComp:
    """Tools are names + regIds. Undo groups behave like Fusion's: actions inside StartUndo/EndUndo form one undo event, actions
    outside a group are one event each; Undo(n) reverts the newest closed events."""

    def __init__(self, path):
        self.path = path
        self.CurrentTime, self.ActiveTool = 0, None

    # -- state
    def _apply(self, st, a, reverse=False):
        kind = a[0]
        if kind in ("add", "delete"):
            if (kind == "add") != reverse:
                st["tools"][a[1]] = {"reg": a[2]}
            else:
                st["tools"].pop(a[1], None)
        elif kind == "rename":
            src, dst = (a[2], a[1]) if reverse else (a[1], a[2])
            st["tools"][dst] = st["tools"].pop(src, {"reg": "Fake"})

    def _act(self, a):
        st = _load(self.path)
        self._apply(st, a)
        g = next((g for g in reversed(st["groups"]) if g["open"]), None)
        if g is not None:
            g["actions"].append(a)
        else:
            st["groups"].append({"name": a[0], "open": False, "actions": [a]})
        _save(self.path, st)

    # -- API used by the connector
    def GetAttrs(self):
        return {"COMPS_Name": "FakeComp", "COMPN_GlobalStart": 0, "COMPN_GlobalEnd": 100}

    def GetToolList(self, selected=False, reg=None):
        names = sorted(_load(self.path)["tools"])
        return {i + 1: FakeTool(self, n) for i, n in enumerate(names)}

    def FindTool(self, name):
        for n in _load(self.path)["tools"]:
            if n.lower() == str(name).lower():   # Fusion tool names are case-insensitive
                return FakeTool(self, n)
        return None

    def AddTool(self, reg, x=0, y=0):
        st = _load(self.path)
        k = 1
        while "%s%d" % (reg, k) in st["tools"]:
            k += 1
        name = "%s%d" % (reg, k)
        self._act(["add", name, reg])
        return FakeTool(self, name)

    def StartUndo(self, name="undo"):
        st = _load(self.path)
        st["groups"].append({"name": name, "open": True, "actions": []})
        _save(self.path, st)

    def EndUndo(self, keep=True):
        st = _load(self.path)
        g = next((g for g in reversed(st["groups"]) if g["open"]), None)
        if g is None:
            st["endUndoWithoutGroup"] = st.get("endUndoWithoutGroup", 0) + 1
        elif not g["actions"] and st.get("dropEmptyGroups"):   # the other way an app can treat a group that recorded nothing
            st["groups"].remove(g)
        else:
            g["open"] = False
        _save(self.path, st)

    def Undo(self, n=1):
        st = _load(self.path)
        for _ in range(int(n)):
            ix = next((i for i in range(len(st["groups"]) - 1, -1, -1) if not st["groups"][i]["open"]), None)
            if ix is None:
                break
            g = st["groups"].pop(ix)
            for a in reversed(g["actions"]):
                self._apply(st, a, reverse=True)
        _save(self.path, st)

    def SetData(self, k, v):
        st = _load(self.path)
        st.setdefault("data", {})[k] = v
        _save(self.path, st)

    def GetData(self, k):
        return _load(self.path).get("data", {}).get(k)

    def Lock(self):
        return True

    def SetActiveTool(self, tool):
        self.ActiveTool = tool

    def Unlock(self):
        return True

    def GetPrefs(self, *a):
        return {"Width": 1920, "Height": 1080, "Rate": 30}


class _Project:
    def GetName(self):
        return "Testbed"

    def GetCurrentTimeline(self):
        return None

    def IsRenderingInProgress(self):
        return False


class _PM:
    def GetCurrentProject(self):
        return _Project()


class _Fusion:
    def __init__(self, path):
        self.path = path

    def GetCurrentComp(self):
        return FakeComp(self.path)


class FakeResolve:
    def __init__(self, path):
        self.path = path

    def GetVersionString(self):
        return "21.1.0.14 (fake)"

    def GetProduct(self):
        return "DaVinci Resolve Studio"

    def GetCurrentPage(self):
        return "fusion"

    def OpenPage(self, page):
        return True

    def GetProjectManager(self):
        return _PM()

    def Fusion(self):
        return _Fusion(self.path)


def state(path):
    """The fake comp's tools and undo groups (for assertions)."""
    return _load(path)


def _guard(ctx):
    """Returns the regId to add (the fake takes anything; a live Testbed check adds Backgrounds)."""
    if isinstance(ctx.resolve, FakeResolve):
        return "Fake"
    if os.environ.get("FUSION_MCP_TEST_FAULTS_LIVE") == "1" and ctx.project().GetName() == "Testbed":
        return "Background"
    raise OpError("FORBIDDEN", "test.* fault-injection operations only run against the offline fake Resolve "
                               "(or the live check in the Testbed project with FUSION_MCP_TEST_FAULTS_LIVE=1)")


@op("test.add", "Test only: add tools with these names.", [P("names", "array", "Tool names.", required=True)], category="test")
def t_add(ctx, comp, a):
    reg = _guard(ctx)
    if any(not isinstance(n, str) or not n for n in a["names"]):
        raise OpError("INVALID_ARGS", "tool names must be non-empty strings")
    for n in a["names"]:
        comp.SetActiveTool(None)   # AddTool would auto-wire to the active tool (realities)
        comp.AddTool(reg, -32768, -32768).SetAttrs({"TOOLS_Name": n})
    return {"added": list(a["names"])}


@op("test.partial", "Test only: add the first failAfter names, then fail.",
    [P("names", "array", "Tool names.", required=True), P("failAfter", "integer", "How many to add before failing.", default=1)], category="test")
def t_partial(ctx, comp, a):
    reg = _guard(ctx)
    for n in a["names"][:int(a.get("failAfter", 1))]:
        comp.SetActiveTool(None)   # AddTool would auto-wire to the active tool (realities)
        comp.AddTool(reg, -32768, -32768).SetAttrs({"TOOLS_Name": n})
    raise OpError("OPERATION_FAILED", "injected failure after a partial change")


@op("test.hang", "Test only: stall like a Resolve call that never returns.",
    [P("seconds", "number", "How long.", default=30), P("tool", "string", "A target name for the receipt."),
     P("once", "boolean", "Stall only the first time for this tool (a transient stall); later runs go straight on."),
     P("add", "string", "Also add the tool named by tool, before or after the stall.", enum=("before", "after"))], category="test")
def t_hang(ctx, comp, a):
    reg = _guard(ctx)
    tool, s = a.get("tool"), float(a.get("seconds", 30))
    if a.get("add") == "before":
        comp.SetActiveTool(None)
        comp.AddTool(reg, -32768, -32768).SetAttrs({"TOOLS_Name": tool})
    mark = os.path.join(config.out_dir(), "test_hang_once", str(tool))
    if not (a.get("once") and os.path.exists(mark)):
        if a.get("once"):
            os.makedirs(os.path.dirname(mark), exist_ok=True)
            open(mark, "w").close()
        time.sleep(s)
    if a.get("add") == "after":
        comp.SetActiveTool(None)
        comp.AddTool(reg, -32768, -32768).SetAttrs({"TOOLS_Name": tool})
    return {"slept": s, **({"added": [tool]} if a.get("add") else {})}


@op("test.crash", "Test only: kill the worker process mid-call.", [], category="test")
def t_crash(ctx, comp, a):
    _guard(ctx)
    os._exit(3)


@op("test.undo_probe", "Test only: is an undo group that recorded no change an undo event? Adds a probe tool in its own group, opens "
    "and closes an empty group, undoes once and reports whether the probe survived (the probe is deleted afterwards).",
    [COMP(), P("name", "string", "Probe tool name.", default="FC_UndoProbe")], undo=False, category="test")
def t_undo_probe(ctx, comp, a):
    reg, n = _guard(ctx), a.get("name") or "FC_UndoProbe"

    def stack():
        try:
            return repr(comp.GetUndoStack())[:400]
        except Exception as e:  # noqa: undocumented call; record what it does
            return "error: %s" % e
    comp.StartUndo("probe add")
    comp.SetActiveTool(None)
    comp.AddTool(reg, -32768, -32768).SetAttrs({"TOOLS_Name": n})
    comp.EndUndo(True)
    before = stack()
    comp.StartUndo("probe empty")
    comp.EndUndo(True)
    after = stack()
    comp.Undo(1)
    t = comp.FindTool(n)
    if t is not None:
        t.Delete()
    return {"emptyGroupIsUndoEvent": t is not None, "undoStackBefore": before, "undoStackAfterEmptyGroup": after}
