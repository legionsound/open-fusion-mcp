"""Disk caches for locked branches (efficiency lab, 2026-09-27, S5 7-step edit/check loop with render.frame):
live 39.2 s / 8.9 GB, freeze (constant-SourceTime TimeStretcher) 32.6 s / 6.9 GB and it follows upstream edits, disk (the
branch rendered to PNG once, a Loader in its place) 20.9 s / 7.2 GB and pixel-identical (MAE 0.0) but STALE after an edit above
it. So: freeze while you still edit upstream; cache to disk once a branch is locked; refresh or restore when you edit above one.

cache.to_disk renders a branch once (the render.* path and its kept Saver, no Deliver) into
<cache root>/<project>/<timeline>/<comp>/<tool>/, puts a Loader in its place (every consumer rewired to it) and leaves the live
branch intact but unconsumed (nothing pulls it, so it does not cook), so cache.restore can wire it back. The manifest rides in the
comp's CustomData (fc_cache): range, files, the rewired inputs and a fingerprint of the branch's upstream graph (the settings of
every upstream tool: regId, static values, keys, expressions, wiring; UI state such as node positions is ignored). A changed
fingerprint = STALE: cache.status reports it, render.* results warn, deliver.start refuses without confirm.
Method 'loader' only: Resolve 21.1's built-in Output:EnableDiskCache returns True from scripting, sets TOOLB_CacheToDisk, and
writes no files (efficiency lab), so it is not offered."""
import datetime
import hashlib
import json
import os
import shutil
import tempfile
import time

from .. import config
from ..luatable import LTable, parse
from ..schema import P
from .base import COMP, OpError, op
from .build import _safe, render_one
from .core import tool_add

KEY = "fc_cache"
UI_KEYS = {"ViewInfo", "CtrlWZoom", "CtrlWShown", "CtrlWHidden", "ActiveTool", "Colors"}

# Upstream of a tool inside Fusion: wired inputs (modifiers included) and tools named in expressions (a scene's CTRL).
WALK_LUA = """
local seen, order, stack = {}, {}, {comp:FindTool(%s)}
while #stack > 0 do
  local t = table.remove(stack)
  local ok, a = pcall(function() return t:GetAttrs() end)
  local n = ok and a and a.TOOLS_Name
  if n and not seen[n] then
    seen[n] = true
    order[#order + 1] = n
    for _, inp in pairs(t:GetInputList() or {}) do
      local o = inp:GetConnectedOutput()
      local st = o and o:GetTool()
      if st then stack[#stack + 1] = st end
      local e = inp:GetExpression()
      if e and e ~= "" then
        for id in string.gmatch(e, "([%%a_][%%w_]*)%%.") do
          local rt = comp:FindTool(id)
          if rt then stack[#stack + 1] = rt end
        end
      end
    end
  end
end
result = table.concat(order, ",")
"""

# The settings of the listed tools (CopySettings, as setting.copy) written to a file: hashed per tool in Python.
FP_LUA = """
local list = {}
for _, n in ipairs({%s}) do local t = comp:FindTool(n) if t then list[#list + 1] = t end end
local f = io.open([[%s]], "w")
f:write(#list > 0 and bmd.writestring(comp:CopySettings(list)) or "")
f:close()
result = #list
"""


def cache_root():
    return config.cache_dir()


def _inside_root(path):
    root, p = cache_root(), os.path.realpath(path)
    return p != root and p.startswith(root + os.sep)


def load(comp):
    raw = comp.GetData(KEY)
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


def _save(comp, m):
    comp.SetData(KEY, json.dumps(m, separators=(",", ":")) if m else "")


def _where(ctx, comp, ref):
    """[project, timeline, comp] folder names (item comps are all 'Composition1': the clip name identifies them)."""
    try:
        p = ctx.project()
        tl, item = ctx.item(ref) if isinstance(ref, dict) else (p.GetCurrentTimeline(), None)
        if item is None and tl is not None:
            item = tl.GetCurrentVideoItem()
        names = [p.GetName(), tl.GetName() if tl else "no_timeline", item.GetName() if item else (comp.GetAttrs() or {}).get("COMPS_Name")]
    except Exception:  # noqa: a comp outside a timeline (or a test double)
        names = ["project", "timeline", (comp.GetAttrs() or {}).get("COMPS_Name") or "comp"]
    return [_safe(str(x or "unnamed")) for x in names]


def _canon(v):
    """Deterministic JSON-able form of a CopySettings table (Lua text via LTable, or a bridge dict) without UI state."""
    if isinstance(v, LTable):
        return [v.ctor, [[str(k), _canon(x)] for k, x in v.items if k not in UI_KEYS]]
    if isinstance(v, dict):
        return sorted([str(k), _canon(x)] for k, x in v.items() if k not in UI_KEYS)
    if isinstance(v, (list, tuple)):
        return [_canon(x) for x in v]
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return type(v).__name__        # a live object: its identity is not content


def _h(x):
    return hashlib.sha256(json.dumps(x, default=str).encode()).hexdigest()[:16]


def fingerprint_lua(ctx, comp, names):
    """{tool: hash} from one Lua chunk (fast; needs the comp on the Fusion page)."""
    fd, path = tempfile.mkstemp(suffix=".setting")
    os.close(fd)
    try:
        ctx.lua(comp, FP_LUA % (", ".join(json.dumps(n) for n in sorted(names)), path), wait=60.0)
        with open(path, encoding="utf-8") as f:
            text = f.read()
    finally:
        os.unlink(path)
    tools = parse(text).get("Tools") if text.strip() else None
    got = {k: v for k, v in (tools.items if isinstance(tools, LTable) else []) if isinstance(k, str)}
    return {n: _h(_canon(got[n])) if n in got else "missing" for n in names}


def fingerprint_bridge(comp, names):
    """{tool: hash} over the scripting bridge (tool.SaveSettings to a temp file, 2 calls per tool; any comp, current or not, any
    page). Not comp.CopySettings: over the bridge it returns {Tools: None} (live, 21.1), a constant that never goes stale."""
    out = {}
    fd, path = tempfile.mkstemp(suffix=".setting")
    os.close(fd)
    try:
        for n in names:
            t = comp.FindTool(n)
            if t is None:
                out[n] = "missing"
                continue
            if not t.SaveSettings(path):
                out[n] = "unsaved"      # never equal to a recorded hash: reported as changed, not silently fresh
                continue
            with open(path, encoding="utf-8") as f:
                tools = parse(f.read()).get("Tools")
            got = {k: v for k, v in (tools.items if isinstance(tools, LTable) else []) if isinstance(k, str)}
            out[n] = _h(_canon(got[n])) if n in got else "missing"
    finally:
        os.unlink(path)
    return out


def upstream(ctx, comp, tool):
    r = ctx.lua(comp, WALK_LUA % json.dumps(tool), wait=60.0)
    return [x for x in r.split(",") if x]


def lua_ok(ctx, comp):
    """The Lua fingerprint needs the comp on the Fusion page (Execute runs there); reads never switch pages."""
    return ctx.is_current(comp) and ctx.resolve.GetCurrentPage() == "fusion"


def _fusion_page(ctx):
    if ctx.resolve.GetCurrentPage() != "fusion":  # Execute runs on the Fusion-page comp (as setting.paste)
        ctx.resolve.OpenPage("fusion")
        time.sleep(1.5)


def check(ctx, comp, entry, current=None):
    """-> {stale, changed: [tools], via} for one manifest entry."""
    if current is None:
        current = lua_ok(ctx, comp)
    names = entry.get("upstream") or [entry["tool"]]
    via = "lua" if current else "bridge"
    now = fingerprint_lua(ctx, comp, names) if current else fingerprint_bridge(comp, names)
    was = (entry.get("fp") or {}).get(via) or {}
    changed = sorted(n for n in names if now.get(n) != was.get(n))
    return {"stale": bool(changed), "changed": changed[:20], "via": via}


def _frames(entry):
    s, e = entry["range"]
    return [(f, os.path.join(entry["dir"], entry["pattern"] % f)) for f in range(int(s), int(e) + 1)]


def _render(ctx, comp, t, entry):
    """Render the live branch over the entry's range into its dir as <tool>_r<rev>_####.png."""
    os.makedirs(entry["dir"], exist_ok=True)   # before anything asks Fusion to write there (a missing folder raised a modal)
    s, e = entry["range"]
    frames = [float(f) for f in range(int(s), int(e) + 1)]
    produced = render_one(ctx, comp, t, frames[0], os.path.join(entry["dir"], "fc_tmp.png"), frames=frames, isolate=True)
    if isinstance(produced, str):
        produced = [(frames[0], produced)]
    for f, p in produced:
        os.replace(p, os.path.join(entry["dir"], entry["pattern"] % int(f)))
    return sum(os.path.getsize(p) for _, p in _frames(entry))


def _point_loader(ctx, comp, ld, entry):
    """Loader on the sequence: trims 0..n-1, comp frames s..e (read back)."""
    s, e = int(entry["range"][0]), int(entry["range"][1])
    ctx.set_input(comp, ld, "Clip", _frames(entry)[0][1])
    for k, v in (("ClipTimeStart", 0), ("ClipTimeEnd", e - s), ("GlobalIn", s), ("GlobalOut", e)):
        ld.SetInput(k, v)
    got = [ld.GetInput(k) for k in ("GlobalIn", "GlobalOut")]
    return None if got == [s, e] else "Loader reads GlobalIn/Out %s, expected [%d, %d]" % (got, s, e)


def _sign(ctx, comp, entry):
    """Walk the upstream again and store both fingerprints (lua for the Fusion-page comp, bridge for any other)."""
    _fusion_page(ctx)
    entry["upstream"] = upstream(ctx, comp, entry["tool"])
    entry["fp"] = {"lua": fingerprint_lua(ctx, comp, entry["upstream"]), "bridge": fingerprint_bridge(comp, entry["upstream"])}


def _delete_files(entry, keep_rev=None):
    """Cache files of an entry (all revisions, or all but keep_rev); only inside the cache root."""
    d = entry["dir"]
    if not _inside_root(d) or not os.path.isdir(d):
        return 0
    stem = entry["pattern"].rsplit("_r", 1)[0] + "_r"
    n = 0
    for fn in os.listdir(d):
        if fn.startswith(stem) and fn.endswith(".png") and not (keep_rev and fn.startswith("%s%d_" % (stem, keep_rev))):
            os.remove(os.path.join(d, fn))
            n += 1
    return n


def _stamp():
    return datetime.datetime.now().isoformat(timespec="seconds")


# ================================================================ ops

@op("cache.to_disk", "Cache a LOCKED branch to disk: render the tool's output once (the render.* Saver, no Deliver) to PNGs under the cache root "
    "(FUSION_MCP_CACHE_DIR, default ~/Movies/FusionCache/<project>/<timeline>/<comp>/<tool>/), then swap a Loader in: every consumer of "
    "the tool is rewired to <tool>_Cache and the live branch stays intact but unconsumed, so cache.restore puts it back. Range: start/end, "
    "else the union of the consumers' enabled regions, else the comp render range. Efficiency lab S5 loop: 20.9 s vs 39.2 s live, "
    "pixel-identical; STALE once anything above it changes (cache.status, render.* warnings, deliver.start preflight). Still editing "
    "upstream? Freeze instead (a constant-SourceTime TimeStretcher follows edits).",
    [COMP(), P("tool", "string", "Branch output tool (an image output; its consumers get the Loader).", required=True),
     P("start", "integer", "First comp frame."), P("end", "integer", "Last comp frame.")], extra={"paste": True})
def cache_to_disk(ctx, comp, a):
    name = a["tool"]
    t = ctx.tool(comp, name)
    m = load(comp)
    if name in m:
        raise OpError("INVALID_ARGS", f"{name} is already cached ({m[name]['loader']})", hint="cache.refresh re-renders it; cache.restore swaps it back.")
    cons = ctx.consumers(comp, t)
    if not cons:
        raise OpError("INVALID_ARGS", f"nothing consumes {name}: there is no branch to replace")
    odd = [c for c in cons if c[2] not in (None, "Output")]
    if odd:
        raise OpError("INVALID_ARGS", f"{name} feeds non-image outputs {odd[:3]}: only image branches cache to PNG")
    ld_name = name + "_Cache"
    if comp.FindTool(ld_name) is not None:
        raise OpError("INVALID_ARGS", f"a tool named {ld_name} already exists", hint="Rename or delete it (a leftover of an earlier cache?).")
    from .scene import _region
    regs = [_region(comp.FindTool(c[0])) for c in cons]
    at = comp.GetAttrs() or {}
    if a.get("start") is not None or a.get("end") is not None:
        s, e = int(a.get("start", at.get("COMPN_RenderStart", 0))), int(a.get("end", at.get("COMPN_RenderEnd", 0)))
    elif all(regs):
        s, e = int(min(r[0] for r in regs)), int(max(r[1] for r in regs))
    else:
        s, e = int(at.get("COMPN_RenderStart", 0)), int(at.get("COMPN_RenderEnd", 0))
    if e < s:
        raise OpError("INVALID_ARGS", f"empty range {s}-{e}")
    d = os.path.join(cache_root(), *_where(ctx, comp, a.get("comp")), _safe(name))
    entry = {"tool": name, "loader": ld_name, "dir": d, "pattern": _safe(name) + "_r1_%04d.png", "rev": 1, "range": [s, e],
             "method": "loader", "created": _stamp()}
    _sign(ctx, comp, entry)       # the state about to be rendered; a failure here leaves the comp untouched
    t0 = time.time()
    entry["bytes"] = _render(ctx, comp, t, entry)
    entry["renderSeconds"] = round(time.time() - t0, 2)
    ld = comp.FindTool(tool_add(ctx, comp, {"regId": "Loader", "name": ld_name})["tool"])
    warn = [x for x in [_point_loader(ctx, comp, ld, entry)] if x]
    entry["rewired"] = []
    for cn, iid, oid in cons:
        ctx.connect(ctx.tool(comp, cn), iid, ld)
        entry["rewired"].append([cn, iid])
    m[name] = entry
    _save(comp, m)
    cs, ce = int(at.get("COMPN_RenderStart", s)), int(at.get("COMPN_RenderEnd", e))
    loose = [c[0] for c, r in zip(cons, regs) if (r or (cs, ce))[0] < s or (r or (cs, ce))[1] > e]
    if loose:
        warn.append(f"{loose[:5]} can request frames outside {s}-{e}, where the Loader has no image: cache their whole active range "
                    "(start/end) or trim them")
    return {"tool": name, "loader": ld_name, "range": [s, e], "frames": e - s + 1, "dir": d, "bytes": entry["bytes"],
            "renderSeconds": entry["renderSeconds"], "rewired": entry["rewired"], "upstreamTools": len(entry["upstream"]), "warnings": warn}


@op("cache.status", "List this comp's disk caches: tool, Loader, range, frames on disk, size, created, and STALE (the fingerprint of the "
    "branch's upstream graph changed since the render; changed lists the tools). Lua fingerprint on the Fusion-page comp, bridge "
    "fingerprint (slower, 2 calls per upstream tool) on any other.", [COMP(), P("tool", "string", "Only this cache.")], read=True)
def cache_status(ctx, comp, a):
    m = load(comp)
    cur = lua_ok(ctx, comp) if m else False
    out = []
    for name, e in m.items():
        if a.get("tool") and name != a["tool"]:
            continue
        files = [p for _, p in _frames(e)]
        present = [p for p in files if os.path.exists(p)]
        row = {"tool": name, "loader": e["loader"], "loaderPresent": comp.FindTool(e["loader"]) is not None, "range": e["range"],
               "frames": len(files), "framesOnDisk": len(present), "bytes": sum(os.path.getsize(p) for p in present),
               "created": e["created"], "refreshed": e.get("refreshed"), "dir": e["dir"]}
        row.update(check(ctx, comp, e, cur) if comp.FindTool(name) is not None else {"stale": True, "changed": [name], "via": "missing"})
        out.append(row)
    return {"caches": out, "root": cache_root(), "stale": [r["tool"] for r in out if r["stale"]]}


@op("cache.refresh", "Re-render stale caches (or the named tool, or all: true) from the live branch into a new file revision, point the Loader "
    "at it, delete the old revision, store the new fingerprint.",
    [COMP(), P("tool", "string", "One cache (default: every stale one)."), P("all", "boolean", "Refresh every cache, stale or not.")],
    extra={"paste": True})
def cache_refresh(ctx, comp, a):
    m = load(comp)
    if a.get("tool") and a["tool"] not in m:
        raise OpError("NOT_FOUND", f"no cache for {a['tool']}", details={"caches": list(m)})
    done, skipped = [], []
    for name, e in m.items():
        if a.get("tool") and name != a["tool"]:
            continue
        if not a.get("tool") and not a.get("all") and not check(ctx, comp, e)["stale"]:
            skipped.append(name)
            continue
        t, ld = comp.FindTool(name), comp.FindTool(e["loader"])
        if t is None or ld is None:
            raise OpError("NOT_FOUND", f"{name if t is None else e['loader']} is gone", hint="cache.restore (or cache.clear) the entry.")
        _sign(ctx, comp, e)
        old = e["rev"]
        e["rev"] = old + 1
        e["pattern"] = e["pattern"].replace("_r%d_" % old, "_r%d_" % e["rev"])
        e["bytes"] = _render(ctx, comp, t, e)
        w = _point_loader(ctx, comp, ld, e)
        _delete_files(e, keep_rev=e["rev"])
        e["refreshed"] = _stamp()
        _save(comp, m)            # per cache: a later failure must not orphan this one's new revision
        done.append({"tool": name, "rev": e["rev"], "bytes": e["bytes"], **({"warning": w} if w else {})})
    return {"refreshed": done, "fresh": skipped}


@op("cache.restore", "Swap the live branch back: every consumer of <tool>_Cache is rewired to the tool, the Loader is deleted and the manifest "
    "entry dropped. clear: true also deletes the cache files (inside the cache root only).",
    [COMP(), P("tool", "string", "Cached tool.", required=True), P("clear", "boolean", "Delete the files too.")])
def cache_restore(ctx, comp, a):
    m = load(comp)
    e = m.get(a["tool"])
    if e is None:
        raise OpError("NOT_FOUND", f"no cache for {a['tool']}", details={"caches": list(m)})
    t = ctx.tool(comp, a["tool"])
    ld = comp.FindTool(e["loader"])
    back = []
    for cn, iid, _oid in (ctx.consumers(comp, ld) if ld is not None else []):
        ctx.connect(ctx.tool(comp, cn), iid, t)
        back.append([cn, iid])
    if ld is None:  # the Loader was deleted by hand: reconnect what the manifest recorded
        for cn, iid in e.get("rewired") or []:
            if comp.FindTool(cn) is not None:
                ctx.connect(ctx.tool(comp, cn), iid, t)
                back.append([cn, iid])
    else:
        ld.Delete()
    del m[a["tool"]]
    _save(comp, m)
    return {"tool": a["tool"], "rewired": back, "filesDeleted": _delete_files(e) if a.get("clear") else 0, "dir": e["dir"]}


@op("cache.clear", "Delete disk-cache files, only inside the cache root: tool (a restored cache's folder, or an active one with restore: true), "
    "or all: true (every cache folder of this comp that no Loader uses).",
    [COMP(), P("tool", "string", "Cache folder of this tool."), P("all", "boolean", "Every unused cache folder of this comp."),
     P("restore", "boolean", "Restore an active cache first.")])
def cache_clear(ctx, comp, a):
    if bool(a.get("tool")) == bool(a.get("all")):
        raise OpError("INVALID_ARGS", "pass tool or all: true")
    m = load(comp)
    base = os.path.join(cache_root(), *_where(ctx, comp, a.get("comp")))
    if a.get("tool"):
        if a["tool"] in m:
            if not a.get("restore"):
                raise OpError("INVALID_ARGS", f"{a['tool']} is cached and its Loader reads these files",
                              hint="cache.restore first, or pass restore: true.")
            cache_restore(ctx, comp, {"tool": a["tool"]})
        dirs = [m[a["tool"]]["dir"] if a["tool"] in m else os.path.join(base, _safe(a["tool"]))]
    else:
        used = {os.path.realpath(e["dir"]) for e in m.values()}
        dirs = [os.path.join(base, x) for x in (os.listdir(base) if os.path.isdir(base) else [])
                if os.path.realpath(os.path.join(base, x)) not in used]
    gone, freed = [], 0
    for d in dirs:
        if not _inside_root(d) or not os.path.isdir(d):
            continue
        freed += sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(d) for f in fs)
        shutil.rmtree(d)
        gone.append(d)
    return {"deleted": gone, "bytesFreed": freed, "root": cache_root()}


# ================================================================ warnings for render.* and deliver.start

def render_warnings(ctx, comp):
    """STALE caches of this comp, one line each (nothing when it has none: one GetData)."""
    m = load(comp)
    if not m:
        return []
    cur = lua_ok(ctx, comp)
    out = []
    for name, e in m.items():
        c = check(ctx, comp, e, cur) if comp.FindTool(name) is not None else {"stale": True, "changed": [name]}
        if c["stale"]:
            out.append(f"disk cache {e['loader']} is STALE: {', '.join(c['changed'][:5])} changed since it was rendered ({e.get('refreshed') or e['created']}); "
                       f"this render shows the old pixels. cache.refresh re-renders it, cache.restore swaps the live branch back")
    return out
