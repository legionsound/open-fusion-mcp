"""Scene builder ops: one layer-level JSON description in, one plain native Fusion graph out (scene.build), read back
(scene.export), edited surgically by layer id or by diff (scene.update), planned offline (scene.plan, scene.diff,
scene.schema, scene.read). The compiler is pure (fusion_connector.scenegraph); these handlers only paste, wire and
apply what a paste cannot carry (tool enabled regions)."""
import json
import os
import time

from .. import scenegraph as sg
from ..schema import P, suggest
from .base import COMP, OpError, jv, op
from .build import _out, _size_k_cache, setting_copy
from .core import write_spline
from .layout import tidy_after

DESC = [P("description", "object", "Scene description (scene.schema)."), P("path", "string", "Absolute path of a scene JSON file (instead of description).")]
LAYOUT = P("layout", "boolean", "Tidy the node graph afterwards in the house graph style (comp.layout; default true): the whole comp when "
                                "it holds only scene-builder tools, else this scene's tools only. update: only when tools or wires changed.")


def _err(e):
    return OpError(e.code, e.message, e.hint, e.details)


def _load(a, key="description", pkey="path"):
    if bool(a.get(key)) == bool(a.get(pkey)):
        raise OpError("INVALID_ARGS", f"pass exactly one of {key} or {pkey}")
    if a.get(pkey):
        p = a[pkey]
        if not os.path.isabs(p) or not os.path.isfile(p):
            raise OpError("NOT_FOUND", f"scene file {p} not found (absolute path required)")
        try:
            return json.load(open(p, encoding="utf-8"))
        except ValueError as e:
            raise OpError("INVALID_ARGS", f"scene file is not JSON: {e}")
    return a[key]


def _font_k():
    """Measured Text+ size constants (text.size_for_px cache) override the built-in table."""
    return {k: v["K"] for k, v in _size_k_cache().items() if isinstance(v, dict) and v.get("K")}


_FONTS = {}


def _fonts(ctx=None):
    """Font files for text metrics: the installed-font index (path + face index, right for .ttc collections), plus, live, the
    faces only Fusion's FontManager knows (fonts bundled with Resolve)."""
    if "idx" not in _FONTS:
        from .. import config
        _FONTS["idx"] = sg.font_index(os.path.join(config.out_dir(), "font_index.json"))
    files = dict(_FONTS["idx"])
    if ctx is not None:
        try:
            from .build import _fonts as fm
            for fam, st in (fm(ctx) or {}).items():
                for sty, f in (st or {}).items():
                    key = "%s/%s" % (fam, sty)
                    if key not in files and isinstance(f, str) and not f.lower().endswith((".ttc", ".otc")):
                        files[key] = [f, 0]
        except Exception:  # noqa: the index alone
            pass
    return sg.Fonts(files)


def _compile(desc, ctx=None):
    try:
        return sg.compile_scene(desc, _font_k(), fonts=_fonts(ctx))
    except sg.SceneError as e:
        raise _err(e)


# ================================================================ offline

@op("scene.schema", "Offline: the JSON Schema of a scene description (layer level, px, top-left origin, y down, +z away from the camera; "
    "layers bottom to top; key = [frame, value, ease] with the ease shaping the segment that leaves it), the efficiency defaults, and a small example.",
    [], read=True, comp=False, offline=True)
def scene_schema(a):
    ex = {"scene": "Hello", "size": [1920, 1080], "fps": 30, "duration": 90, "background": "#0A0D14",
          "controls": {"accent": "#FF4B2B"},
          "layers": [{"id": "card", "type": "rect", "size": [720, 400], "radius": 24, "fill": "#F3F0E8", "position": [960, 560],
                      "keys": {"scale": [[0, 90, "out_back"], [18, 100]], "opacity": [[0, 0], [8, 100]]}},
                     {"id": "title", "type": "text", "position": [660, 520], "in": 6,
                      "text": {"content": "Hello.", "font": "Open Sans", "style": "Bold", "size": 96, "color": "$accent"},
                      "animators": [{"type": "cascade", "start": 6, "stagger": 2, "duration": 14, "ease": "out_expo", "from": {"y": 30, "opacity": 0}}]}]}
    return {"schema": sg.SCHEMA, "defaults": sg.DEFAULTS, "example": ex,
            "animatable": {"scalar": sorted(sg.SCALAR_KEYS), "vector": sorted(sg.VECTOR_KEYS), "text": sorted(sg.TEXT_KEYS)},
            "eases": sorted(set(sg.presets()) | {"hold", "linear"})}


@op("scene.plan", "Offline dry run of scene.build: validates the description and reports the node count (by regId, modifiers), cost drivers "
    "(renderers, accumulation passes, motion-blur tools, texture megapixels, holds, culled tools) and every efficiency decision it will make. "
    "outPath also writes the .setting it would paste.",
    DESC + [P("outPath", "string", "Absolute .setting path to write the compiled graph to."),
            P("preview", "object", "{frames: [...], width: 480, outPath?}: an offline wireframe sheet of those frames, returned inline (a layout and "
                                   "timing sketch drawn with PIL: shapes, text in the real font, groups, transforms, opacity, trims, 3D cards through "
                                   "the camera; no blur, DOF, glow, masks, mattes or motion blur)."),
            P("quiet", "boolean", "Compact reply: counts, cost, warnings and a decisions sample inline; decisions, regions and textures in "
                                  "the file named in detail (default false)."),
            P("graph", "boolean", "Also draw the node graph scene.build will paste, in the house graph style (PNG inline), with its layout "
                                  "metrics (overlaps, crossings, wires over tools, underlays).")],
    read=True, comp=False, offline=True)
def scene_plan(a):
    desc = _load(a)
    try:
        out = sg.plan(desc, _font_k(), fonts=_fonts())
    except sg.SceneError as e:
        raise _err(e)
    if out.get("ok") and (a.get("outPath") or a.get("preview") or a.get("graph")):
        c = _compile(desc)
        if a.get("outPath"):
            p = _out(a["outPath"], desc["scene"] + ".setting")
            with open(p, "w", encoding="utf-8") as f:
                f.write(c.g.text())
            out["path"] = p
        if a.get("preview"):
            pv = a["preview"]
            fr = pv.get("frames") or [int(c.dur * i / 5) for i in range(5)] + [c.dur - 1]
            pp = _out(pv.get("outPath"), "preview_%s.png" % desc["scene"])
            sg.preview(c, fr, int(pv.get("width", 480)), pp)
            out["preview"] = pp
            out["_inline"] = [pp]
        if a.get("graph"):
            from .. import layout as lay
            gp = _out(None, "graph_%s.png" % desc["scene"])
            lay.preview(c.graph, c.net, gp)
            m = lay.metrics(c.graph, c.net)
            out["graph"] = {"png": gp, "underlays": [b["name"] for b in c.graph["boxes"]],
                            **{k: m[k] for k in ("tools", "overlaps", "crossings", "wiresOverTools", "spinesStraight", "bbox")}}
            out["_inline"] = out.get("_inline", []) + [gp]
    if a.get("quiet") and out.get("ok"):
        return _quiet(out, out["scene"], "plan")
    return out


@op("scene.diff", "Offline: the minimal tool-level ops that turn one scene description into another (what scene.update would do): "
    "set (static inputs), expr, keys (splines rewritten in place), connect/disconnect, replace (delete + re-paste), add, remove, regions.",
    [P("old", "object", "Current description.", required=True), P("new", "object", "New description (or pass edits)."),
     P("edits", "array", "Edits applied to old (scene.update grammar) instead of new.")], read=True, comp=False, offline=True)
def scene_diff(a):
    old = a["old"]
    try:
        new = a.get("new") or sg.apply_edits(old, a.get("edits") or [])
        oc, nc = _compile(old), _compile(new)
    except sg.SceneError as e:
        raise _err(e)
    ops = sg.diff(oc, nc)
    return _summary(ops, oc, nc, detail=True)


@op("scene.read", "Offline: read the scene description(s) stored in .setting text or a file (setting.copy / fu_comp_export output): "
    "{scene: description}. The description rides on <scene>_Out as CustomData.",
    [P("text", "string", ".setting text."), P("path", "string", "Absolute .setting path."), P("scene", "string", "Only this scene.")],
    read=True, comp=False, offline=True)
def scene_read(a):
    if bool(a.get("text")) == bool(a.get("path")):
        raise OpError("INVALID_ARGS", "pass exactly one of text or path")
    text = a.get("text") or open(a["path"], encoding="utf-8").read()
    found = sg.from_setting(text, a.get("scene"))
    if not found:
        raise OpError("NOT_FOUND", "no scene description in this setting text", hint="scene.build stores it on <scene>_Out (CustomData sbScene)")
    return {"scenes": found}


def _cap(xs, n):
    return xs[:n] + (["... %d more (scene.plan lists all)" % (len(xs) - n)] if len(xs) > n else [])


def _summary(ops, oc, nc, detail=False):
    rg_old, rg_new = oc.regions, nc.regions
    regions = {t: r for t, r in rg_new.items() if rg_old.get(t) != r or t in set(ops.get("replace", [])) | set(ops.get("add", []))}
    reset = [t for t in rg_old if t not in rg_new and t in nc.g.t]
    out = {"counts": {k: len(v) for k, v in ops.items() if isinstance(v, list)}, "regions": regions, "resetRegions": reset}
    if detail:
        out["ops"] = {k: (v if len(v) <= 40 else v[:40] + ["... %d more" % (len(v) - 40)]) for k, v in ops.items() if k != "keys"}
        if ops.get("keys"):
            out["ops"]["keys"] = [{"host": k["host"], "input": k["input"], "keys": len(k["keys"])} for k in ops["keys"][:40]]
    return out


# ================================================================ live

def _apply_regions(ctx, comp, regions, reset=()):
    """Tool enabled regions (the Keyframes-editor trim): SetAttrs with 1-element tables [efficiency lab T04, live]."""
    done, bad = 0, []
    for name, (s, e) in regions.items():
        t = comp.FindTool(name)
        if t is None:
            bad.append([name, "missing"])
            continue
        t.SetAttrs({"TOOLNT_EnabledRegion_Start": {1: s}, "TOOLNT_EnabledRegion_End": {1: e}})
        got = jv(t.GetAttrs().get("TOOLNT_EnabledRegion_Start"))
        got = got[0] if isinstance(got, list) and got else got
        if got is None or abs(float(got) - s) > 1e-6:
            bad.append([name, "readback %r" % got])
        else:
            done += 1
    for name in reset:
        t = comp.FindTool(name)
        if t is not None:
            t.ResetEnabledRegion()
    return done, bad


def _root(ctx, comp, scene):
    t = comp.FindTool(scene + "_Out")
    if t is None:
        found = _scenes(ctx, comp)
        s = suggest(scene, list(found))
        raise OpError("NOT_FOUND", f"no scene '{scene}' in this comp" + (f" - did you mean '{s}'?" if s else ""),
                      details={"scenes": list(found)}, hint="scene.export without scene lists the scenes in the comp")
    raw = t.GetData(sg.ROOT_KEY)
    if not raw:
        raise OpError("NOT_FOUND", f"{scene}_Out carries no scene description (CustomData {sg.ROOT_KEY})")
    return t, json.loads(raw)


def _scenes(ctx, comp):
    out = {}
    for n in ctx.names(comp):
        if n.endswith("_Out"):
            raw = comp.FindTool(n).GetData(sg.ROOT_KEY)
            if raw:
                d = json.loads(raw)
                out[d.get("scene")] = d
    return out


# [sb3] ONE Lua chunk per scene.build / scene.update: delete the old tools with their own modifiers, paste, restore outside consumers,
# wire, keep re-pasted tools where they stood, set expressions and enabled regions, and find the splines to rewrite. Every step walks
# the tools it names (FindTool, their outputs, the inputs their modifiers hang on), never the comp: the old path listed every tool for
# the paste name diff and scanned every modifier of the comp for the delete, so a small update into a 2,000-tool comp took 3.5 s.
REPASTE_LUA = r"""
local S = bmd.readfile([[%s]])
if type(S) ~= 'table' then error('repaste spec failed Fusion parse') end
local paste_path = [[%s]]
local flow = comp.CurrentFrame and comp.CurrentFrame.FlowView
local function A(o) local ok, a = pcall(function() return o:GetAttrs() end) if ok then return a end end
local function set(l) local s = {} for _, n in ipairs(l or {}) do s[n] = true end return s end
local function input(t, id)   -- Input by ID: t[id] first, the input list as the fallback (dotted IDs, groups)
  local ok, i = pcall(function() return t[id] end)
  if ok and i and type(i) ~= 'function' and type(i) ~= 'number' and type(i) ~= 'string' then
    local a = A(i)
    if a and a.INPS_ID == id then return i end
  end
  for _, x in pairs(t:GetInputList() or {}) do local a = A(x) if a and a.INPS_ID == id then return x end end
end
local function src_of(t, id) local i = input(t, id) local o = i and i:GetConnectedOutput() return o and o:GetTool(), o end
local victims, keep, pasted = set(S.victims), set(S.keep), set(S.names)
local problems, pos, ext, mods = {}, {}, {}, {}
local function collect(t, specs)   -- the modifiers hanging on t's animated inputs (named by the compiled graph), parents first
  for _, sp in ipairs(specs or {}) do
    local m = src_of(t, sp.id)
    if m then mods[#mods + 1] = m collect(m, sp.sub) end
  end
end
local live = {}
for _, n in ipairs(S.victims or {}) do
  local t = comp:FindTool(n)
  if t then
    live[#live + 1] = t
    if flow and pasted[n] then local ok, x, y = pcall(function() return flow:GetPos(t) end) if ok and x then pos[n] = {x, y} end end
    for _, o in pairs(t:GetOutputList() or {}) do
      for _, i in pairs(o:GetConnectedInputs() or {}) do
        local ct = i:GetTool()
        local cn = ct and A(ct) and A(ct).TOOLS_Name
        local ia = A(i)
        if cn and not keep[cn] and not victims[cn] and ia then ext[#ext + 1] = {cn, ia.INPS_ID, n, (A(o) or {}).OUTS_ID} end
      end
    end
    collect(t, (S.mods or {})[n])
  end
end
local going = {}
for _, m in ipairs(mods) do local a = A(m) if a then going[a.TOOLS_Name] = true end end
local clash = {}
for _, n in ipairs(S.names or {}) do if not victims[n] and not going[n] and comp:FindTool(n) then clash[#clash + 1] = n end end
if #clash > 0 then error('CLASH:' .. table.concat(clash, ',')) end
local nd, nm, np = 0, 0, 0
comp:SetActiveTool(nil) comp:Lock()
local okx, errx = pcall(function()
  for _, t in ipairs(live) do if pcall(function() t:Delete() end) then nd = nd + 1 end end
  for _, m in ipairs(mods) do   -- parents before children: a modifier goes once nothing reads it (Fusion may have taken it already)
    local ok, used = pcall(function()
      for _, o in pairs(m:GetOutputList() or {}) do local c = o:GetConnectedInputs() if c and next(c) ~= nil then return true end end
      return false
    end)
    if ok and not used and pcall(function() m:Delete() end) then nm = nm + 1 end
  end
  if paste_path ~= '' then
    local st = bmd.readfile(paste_path)
    if type(st) ~= 'table' then error('setting failed Fusion parse; nothing pasted') end
    comp:Paste(st)
  end
end)
comp:Unlock() comp:SetActiveTool(nil)
if not okx then error(errx) end
local miss = {}
for _, n in ipairs(S.names or {}) do if comp:FindTool(n) then np = np + 1 else miss[#miss + 1] = n end end
local function connect(dn, id, sn, out)
  local d, s = comp:FindTool(dn), comp:FindTool(sn)
  if not d or not s then problems[#problems + 1] = dn .. '.' .. id .. '<-' .. sn .. ' missing' return end
  local target = s
  if out and out ~= '' and out ~= 'Output' then
    for _, o in pairs(s:GetOutputList() or {}) do local a = A(o) if a and a.OUTS_ID == out then target = o end end
  end
  pcall(function() d:ConnectInput(id, target) end)
  local got = src_of(d, id)
  if not got then   -- generic-typed inputs (a pasted Switch): the Output object, then Input:ConnectTo [rebuild F8]
    local mo = s:FindMainOutput(1)
    pcall(function() d:ConnectInput(id, mo) end)
    got = src_of(d, id)
    if not got then local i = input(d, id) if i and mo then pcall(function() i:ConnectTo(mo) end) got = src_of(d, id) end end
  end
  if not got or (A(got) or {}).TOOLS_Name ~= sn then problems[#problems + 1] = dn .. '.' .. id .. '<-' .. sn end
end
comp:Lock()
local oky, erry = pcall(function()
  for _, e in ipairs(ext) do if comp:FindTool(e[1]) and comp:FindTool(e[3]) then connect(e[1], e[2], e[3], e[4]) end end
  for _, w in ipairs(S.wires or {}) do connect(w[1], w[2], w[3], w[4]) end
  for _, w in ipairs(S.cuts or {}) do local d = comp:FindTool(w[1]) if d then d:ConnectInput(w[2], nil) end end
  for _, e in ipairs(S.exprs or {}) do
    local t = comp:FindTool(e[1])
    local i = t and input(t, e[2])
    if i then i:SetExpression(e[3]) else problems[#problems + 1] = e[1] .. '.' .. e[2] .. ' expression' end
  end
  for _, r in ipairs(S.regions or {}) do
    local t = comp:FindTool(r[1])
    if t then
      t:SetAttrs({TOOLNT_EnabledRegion_Start = {r[2]}, TOOLNT_EnabledRegion_End = {r[3]}})
      local g = (A(t) or {}).TOOLNT_EnabledRegion_Start
      g = type(g) == 'table' and g[1] or g
      if not g or math.abs(g - r[2]) > 1e-6 then problems[#problems + 1] = r[1] .. ' region' end
    else
      problems[#problems + 1] = r[1] .. ' region missing'
    end
  end
  for _, n in ipairs(S.reset or {}) do local t = comp:FindTool(n) if t then t:ResetEnabledRegion() end end
end)
comp:Unlock()
if not oky then error(erry) end
if flow then
  local queued = true
  for n, p in pairs(pos) do
    local t = comp:FindTool(n)
    if t then
      if queued then queued = pcall(function() flow:QueueSetPos(t, p[1], p[2]) end) end
      if not queued then flow:SetPos(t, p[1], p[2]) end
    end
  end
  if queued then pcall(function() flow:FlushSetPosQueue() end) end
end
local found = {}
for _, f in ipairs(S.paths or {}) do   -- splines to rewrite, reached through their host inputs (pasted splines may be renamed)
  local t = comp:FindTool(f[2][1][1])
  for _, hop in ipairs(f[2]) do if t then t = src_of(t, hop[2]) end end
  local a = t and A(t)
  if a then found[#found + 1] = f[1] .. '=' .. a.TOOLS_Name else problems[#problems + 1] = f[1] .. ' spline not found' end
end
result = nd .. ',' .. nm .. ',' .. np .. '\n' .. table.concat(miss, ',') .. '\n' .. table.concat(problems, ';') .. '\n' .. table.concat(found, ',')
"""


def _lua_lit(v):
    """Python -> Lua literal for the repaste spec file (read with bmd.readfile)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return sg._num(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'
    if isinstance(v, dict):
        return "{ " + ", ".join("%s = %s" % (k if k.isidentifier() else '["%s"]' % k, _lua_lit(x)) for k, x in v.items()
                                if x is not None) + " }"
    return "{ " + ", ".join(_lua_lit(x) for x in v) + " }"


def _mod_specs(g, host):
    """[{id, sub}] of the modifiers the compiled graph hangs on host's inputs (splines, paths, followers), nested."""
    return [{"id": g.t[n]["owner"][1], "sub": _mod_specs(g, n)} for n in g.order if (g.t[n].get("owner") or (None,))[0] == host]


def repaste(ctx, comp, spec, text=None, wait=None):
    """Run REPASTE_LUA. spec: victims, mods {victim: specs}, keep (graph names), names (pasted top-level names), wires
    [[dst, input, src, output]], cuts, exprs [[tool, input, expr]], regions [[tool, s, e]], reset, paths [[key, [[host, input]...]]].
    -> {deleted, modifiers, pasted, missing, problems, splines {key: live name}, ms}."""
    import tempfile
    if not ctx.is_current(comp):
        raise OpError("NOT_CURRENT", "paste only works on the comp showing on the Fusion page (realities §1)",
                      hint="Pass comp as {timeline, item} to auto-make it current, or call comp.set_current first.")
    if ctx.resolve.GetCurrentPage() != "fusion":  # Execute runs on the Fusion-page comp
        ctx.resolve.OpenPage("fusion")
        time.sleep(1.5)
    if text:
        from .build import setting_syntax_problems
        lex = setting_syntax_problems(text)   # Fusion would reject it and Paste(nil) would paste the clipboard
        if lex:
            raise OpError("INVALID_ARGS", "setting text would fail Fusion's parser: " + "; ".join(lex[:5]))
    tmp = []
    try:
        fd, sp = tempfile.mkstemp(suffix=".lua")
        tmp.append(sp)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(_lua_lit(spec))
        pp = ""
        if text:
            fd, pp = tempfile.mkstemp(suffix=".setting")
            tmp.append(pp)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
        n = len(spec.get("victims") or []) + len(spec.get("names") or [])
        t0 = time.time()
        try:
            r = ctx.lua(comp, REPASTE_LUA % (sp, pp), wait=wait or min(600.0, 15.0 + 0.08 * n))
        except OpError as e:
            if "CLASH:" in e.message:
                names = e.message.split("CLASH:", 1)[1].split(",")
                raise OpError("INVALID_ARGS", f"{len(names)} tools to paste already exist (e.g. {names[:3]}); nothing was changed",
                              hint="scene.update edits a built scene surgically; replace: true rebuilds it; rename colliding hand-made tools",
                              details={"exist": names[:20]})
            raise
    finally:
        for p in tmp:
            os.unlink(p)
    counts, miss, probs, found = (r.split("\n") + ["", "", ""])[:4]
    d, m, p = (int(x) for x in (counts.split(",") + ["0", "0", "0"])[:3])
    return {"deleted": d, "modifiers": m, "pasted": p, "missing": [x for x in miss.split(",") if x],
            "problems": [x for x in probs.split(";") if x], "splines": dict(x.split("=", 1) for x in found.split(",") if "=" in x),
            "ms": int((time.time() - t0) * 1000)}


def build_spec(c, og, replace, same):
    """scene.build -> (repaste spec, .setting text). replace: the previous build's tools (og: its compiled graph, or None) and this
    build's names go first; same: the graph did not change shape, so its underlays stay and are not re-pasted."""
    names = list(c.g.order)
    tops = [n for n in names if not c.g.t[n].get("owner")]
    victims = []
    if replace:
        victims = sorted({n for n in (og.order if og else []) if not og.t[n].get("owner")} | set(tops) |
                         ({b["name"] for b in og.underlays} if og and not same else set()))
    mods = {}
    for n in victims:   # the old build's modifiers, else (no stored description) the ones this build would hang on n
        sp = _mod_specs(og, n) if og is not None and n in og.t else _mod_specs(c.g, n) if n in c.g.t else []
        if sp:
            mods[n] = sp
    spec = {"victims": victims, "mods": mods, "keep": sorted(set(names) | set(victims)), "names": tops,
            "regions": [[t, s, e] for t, (s, e) in c.regions.items()]}
    return spec, c.g.text(names if same else None)


def update_spec(oc, nc, ops, summ):
    """scene.update ops (scenegraph.diff) -> (repaste spec, .setting text of the tools to paste or None)."""
    gone = [n for n in ops.get("remove", []) + ops.get("replace", []) if n in oc.g.t]   # a new name is never a victim: a hand-made
    tops = [n for n in ops.get("pasteTools", []) if not nc.g.t[n].get("owner")]              # tool holding it is a clash, not deleted
    spec = {"victims": gone, "mods": {n: sp for n in gone for sp in [_mod_specs(oc.g, n)] if sp},
            "keep": sorted(set(nc.g.t) | set(oc.g.t)), "names": tops,
            "wires": [list(w) for w in ops.get("rewire", []) + ops.get("connect", [])],
            "cuts": [list(x) for x in ops.get("disconnect", [])],
            "exprs": [[e["tool"], e["input"], e["expression"]] for e in ops.get("expr", [])],
            "regions": [[t, s, e] for t, (s, e) in summ["regions"].items()], "reset": summ["resetRegions"],
            "paths": [[str(i), k["path"]] for i, k in enumerate(ops.get("keys", []))]}
    return spec, (nc.g.text(ops["pasteTools"]) if ops.get("pasteTools") else None)


def _same_topology(og, ng):
    """The placeable tools and their wires are the same: the house layout would not move anything, so an update keeps the
    re-pasted tools where they stood and skips the layout pass (a whole-comp read) [sb3]."""
    a, b = sg.graph_net(og), sg.graph_net(ng)
    return a.reg == b.reg and {n: sorted(v) for n, v in a.ins.items()} == {n: sorted(v) for n, v in b.ins.items()}


@op("scene.build", "Build a whole scene from ONE layer-level description (text, shapes, solids, images, groups/assets, nulls, 3D camera, "
    "lights; keys with cubic-bezier eases; text animators; masks, track mattes, blend modes, effects; controller) as a plain native graph in "
    "one quiet paste. Efficiency is built in: culling (enabled regions on the consuming Merge), adaptive motion blur, texture holds, 3D textures "
    "at their largest on-screen size, 2.5D for flat cards, Z-buffer transparency, draft by default (CTRL.Draft). Returns node counts, "
    "warnings and a decisions sample; the layer id -> tools map and all decisions are in the detail file (quiet: false returns them inline). The description is stored on <scene>_Out for scene.export / scene.update.",
    [COMP()] + DESC + [P("replace", "boolean", "Delete this scene's existing tools first (rebuild). Default false: refuse when they exist."),
                       P("connectOutput", "boolean", "Connect MediaOut1 to <scene>_Out (default true)."),
                       P("film", "boolean", "One comp for a whole film: instead of wiring MediaOut1 directly, add FILM_<scene> (a Merge trimmed to this "
                                            "scene's frames, description start .. start + duration - 1) to the ladder feeding MediaOut1. Outside its range a "
                                            "trimmed Merge passes its Background and does not cook the scene (efficiency lab T04/F)."),
                       P("quiet", "boolean", "Compact reply (default true): counts, warnings and a decisions sample inline; the full layer "
                                             "map, decisions and regions go to the file named in detail."),
                       LAYOUT],
    extra={"paste": True})
def scene_build(ctx, comp, a):
    desc = _load(a)
    c = _compile(desc, ctx)
    names = list(c.g.order)
    tops = [n for n in names if not c.g.t[n].get("owner")]
    notes = []
    victims, og = [], None
    if a.get("replace"):
        old = None
        try:
            old = _root(ctx, comp, c.S)[1]
        except OpError:
            pass
        og = _compile(old, ctx).g if old else None
    same = og is not None and _same_topology(og, c.g)   # re-pasted tools keep their spots; boxes stay; no layout pass
    spec, text = build_spec(c, og, bool(a.get("replace")), same)
    victims = spec["victims"]
    res = repaste(ctx, comp, spec, text, wait=min(600.0, 15.0 + 0.08 * (len(names) + len(victims))))
    ms = res["ms"]
    if victims:
        notes.append(f"replaced: deleted {res['deleted']} tools and {res['modifiers']} modifiers of the previous build")
    if res["missing"]:
        notes.append("not found after the paste: %s" % res["missing"][:10])
    out_t = comp.FindTool(c.n("Out"))
    if out_t is not None and not out_t.GetData(sg.ROOT_KEY):
        out_t.SetData(sg.ROOT_KEY, json.dumps(desc, separators=(",", ":"), sort_keys=True))
        notes.append("CustomData did not survive the paste: stored with SetData")
    bad = [p for p in res["problems"] if p.endswith("region") or p.endswith("region missing")]
    notes += ["could not restore " + p for p in res["problems"] if p not in bad][:10]
    done = len(c.regions) - len(bad)
    wired = None
    mo = comp.FindTool("MediaOut1")
    film_warn = []
    if a.get("film") and mo is not None and out_t is not None:
        wired = _film_ladder(ctx, comp, c, mo, out_t, film_warn)
        notes.append("film ladder: %s" % wired)
    elif a.get("connectOutput", True):
        if mo is not None and out_t is not None:
            wired = ctx.connect(mo, "Input", out_t)
    lw = []
    tidy = tidy_after(ctx, comp, c.S, "build", lw) if a.get("layout", True) and not same else None
    if same:
        notes.append("same graph as the previous build: tools re-pasted in place, layout kept")
    W, H, fps = ctx.fmt(comp)
    warn = list(sorted(set(c.warnings))) + film_warn + lw + _controls_from_check(ctx, comp, desc)
    if (W, H) != (c.W, c.H):
        warn.append(f"comp frame format is {W}x{H}, the scene is {c.W}x{c.H}: the scene was built for its own size (timeline.set_format)")
    if abs(fps - c.fps) > 1e-3:
        warn.append(f"comp runs at {fps} fps, the scene at {c.fps}")
    if bad:
        warn.append(f"enabled regions not confirmed on {len(bad)} tools: {bad[:5]}")
    st = sg.graph_stats(c.g)
    out = {"scene": c.S, "output": c.n("Out"), "quality": c.cfg["quality"], "tools": st["tools"], "nodes": st["nodes"],
           "modifiers": st["modifiers"], "byRegId": st["byRegId"], "pasted": res["pasted"], "pasteMs": ms,
           "layers": sg.layer_map(c), "regions": done, "mediaOut": wired is not None,
           "decisions": list(dict.fromkeys(c.decisions)), "warnings": warn, "notes": notes, "layout": tidy}
    if a.get("quiet", True):
        return _quiet(out, c.S, "build", {"regions": c.regions})
    return dict(out, decisions=_cap(out["decisions"], 25))


def _controls_from_check(ctx, comp, desc):
    """[sb3 item 8] controlsFrom: the film controller must exist and hold this scene's controls, or the linked values read 0."""
    src = desc.get("controlsFrom")
    if not src or src == desc.get("scene"):
        return []
    try:
        sd = _root(ctx, comp, src)[1]
    except OpError:
        return [f"controlsFrom {src}: scene {src} is not in this comp; build it first (its CTRL drives this scene's controls and Draft)"]
    miss = [k for k in (desc.get("controls") or {}) if k not in (sd.get("controls") or {})]
    return [f"controlsFrom {src}: {src}_CTRL has no {miss[:8]}; add them to {src}'s controls or they read 0"] if miss else []


def _quiet(out, scene, what, extra=None):
    """[fusion_v2 F8] Compact reply: counts, warnings (20) and 8 decisions inline; the full layer map, decisions, regions and
    warnings go to out/scene_<scene>_<what>.json (path in detail)."""
    full = {k: out[k] for k in ("layers", "decisions", "regions", "warnings", "textures") if k in out}
    full.update(extra or {})
    p = _out(None, "scene_%s_%s.json" % (scene, what))
    with open(p, "w", encoding="utf-8") as f:
        json.dump(full, f, indent=1)
    dec, warn = out.get("decisions") or [], out.get("warnings") or []
    out = dict(out, decisions={"count": len(dec), "sample": dec[:8]}, detail=p)
    if isinstance(out.get("layers"), dict):
        out["layers"] = {"count": len(out["layers"])}
    if isinstance(out.get("regions"), dict):
        out["regions"] = len(out["regions"])
    if len(warn) > 20:
        out["warnings"] = warn[:20] + ["... %d more in detail" % (len(warn) - 20)]
    out.pop("textures", None)
    return out


def _region(t):
    """(start, end) of a tool's enabled region, or None when it is unbounded (the -1e9..1e9 default)."""
    at = t.GetAttrs() or {}
    v = []
    for k in ("TOOLNT_EnabledRegion_Start", "TOOLNT_EnabledRegion_End"):
        x = jv(at.get(k))
        x = x[0] if isinstance(x, list) and x else x
        v.append(float(x) if x is not None else None)
    if v[0] is None or v[1] is None or (v[0] <= -1e8 and v[1] >= 1e8):
        return None
    return v[0], v[1]


def _film_ladder(ctx, comp, c, mo, out_t, warn=None):
    """FILM_<scene> = Merge(BG = what feeds MediaOut1 now, or a clear FILM_Base; FG = <scene>_Out), trimmed to the scene's frames.
    New ladder tools arrive in one small paste and the overlap check walks the ladder: no whole-comp scans (add_tool reads every
    tool's name twice, a cost that grew with the film comp) [fusion_v2 F9]."""
    name = "FILM_" + c.S
    t = comp.FindTool(name)
    if t is None:
        src = ctx.source_of(mo, "Input")
        bg = comp.FindTool(src[0]) if src and src[0] not in (c.n("Out"),) else None
        if bg is None:
            bg = comp.FindTool("FILM_Base")
        base = "" if bg is not None else ("FILM_Base = Background { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, "
                                          "TopLeftAlpha = Input { Value = 0, }, }, }, ")
        wire = 'Background = Input { SourceOp = "FILM_Base", Source = "Output", }, ' if base else ""
        res = ctx.paste(comp, "{ Tools = ordered() { %s%s = Merge { Inputs = { %s}, }, }, }" % (base, name, wire))
        if res["renamed"].get(name, name) != name:
            raise OpError("OPERATION_FAILED", f"{name} collided on paste ({res['renamed'][name]})")
        t = comp.FindTool(name)
        if bg is not None:
            ctx.connect(t, "Background", bg)
        ctx.connect(mo, "Input", t)
    ctx.connect(t, "Foreground", out_t)
    s0, s1 = c.start, c.start + c.dur - 1
    t.SetAttrs({"TOOLNT_EnabledRegion_Start": {1: s0}, "TOOLNT_EnabledRegion_End": {1: s1}})
    if warn is not None:
        seen, cur = set(), ctx.source_of(mo, "Input")
        while cur and cur[0].startswith("FILM_") and cur[0] != "FILM_Base" and cur[0] not in seen:
            seen.add(cur[0])
            other = comp.FindTool(cur[0])
            if other is None:
                break
            r = _region(other) if cur[0] != name else None
            if r and r[0] <= s1 and s0 <= r[1]:
                warn.append(f"{name} [{s0}, {s1}] overlaps {cur[0]} [{r[0]:g}, {r[1]:g}]: both scenes cook on the overlap "
                            "(give each scene its own frames)")
            cur = ctx.source_of(other, "Background")
    return [name, s0, s1]


MASK_REGS = ("BitmapMask", "RectangleMask", "EllipseMask", "PolylineMask", "BSplineMask", "TriangleMask", "WandMask", "RangesMask")


def _bg_connected(ctx, tool):
    try:
        return bool(ctx.source_of(tool, "Background"))
    except Exception:  # noqa
        return False


@op("comp.lint_regions", "Read-only check of tool enabled regions (the culling trims): lists every trimmed tool whose output feeds an image "
    "input (a Merge Foreground/Background or any non-mask consumer) that is still active outside that trim: BLACK_FRAME_TRAP, because "
    "outside its region such a tool delivers nothing and Deliver then writes black frames without an error (efficiency lab T04). Trims "
    "that feed masks are fine. Also lists FILM_ ladder Merges whose frames overlap.",
    [COMP()], read=True)
def comp_lint_regions(ctx, comp, a):
    tools = {t.GetAttrs().get("TOOLS_Name"): t for t in (comp.GetToolList(False) or {}).values()}
    trimmed = {n: r for n, r in ((n, _region(t)) for n, t in tools.items()) if r}
    traps = []
    for n, (s0, s1) in trimmed.items():
        t_reg = tools[n].GetAttrs().get("TOOLS_RegID")
        if t_reg in ("Merge", "Dissolve") and _bg_connected(ctx, tools[n]):
            continue    # a trimmed Merge passes its Background through outside the trim (the film ladder): no trap
        for cname, iid, _out_id in ctx.consumers(comp, tools[n]):
            ct = tools.get(cname)
            if ct is None:
                continue
            creg = ct.GetAttrs().get("TOOLS_RegID")
            if iid in ("EffectMask", "Mask", "GarbageMatte", "SolidMatte") or creg in MASK_REGS:
                continue
            cr = trimmed.get(cname)
            if cr and cr[0] >= s0 and cr[1] <= s1:
                continue    # the consumer is itself trimmed inside the region: never requests outside it
            traps.append({"trap": "BLACK_FRAME_TRAP", "tool": n, "region": [s0, s1], "consumer": cname, "input": iid,
                          "consumerRegion": list(cr) if cr else None,
                          "fix": f"trim {cname} (the consuming Merge) instead of {n}, or reset {n}'s region"})
    film = sorted((n, r) for n, r in trimmed.items() if n.startswith("FILM_") and n != "FILM_Base")
    overlaps = [[x[0], y[0]] for i, x in enumerate(film) for y in film[i + 1:] if x[1][0] <= y[1][1] and y[1][0] <= x[1][1]]
    return {"trimmed": len(trimmed), "traps": traps, "filmOverlaps": overlaps, "ok": not traps and not overlaps}


@op("scene.export", "Read a built scene back as its description (stored on <scene>_Out). Without scene: every scene in the comp. drift: true "
    "also compares the live tools' static values with what the description compiles to and lists hand edits (tool, input, expected, live).",
    [COMP(), P("scene", "string", "Scene id (default: all)."), P("drift", "boolean", "Report hand edits (one Lua copy of the scene's tools)."),
     P("outPath", "string", "Absolute .json path to write the description(s) to.")], read=True)
def scene_export(ctx, comp, a):
    scenes = {a["scene"]: _root(ctx, comp, a["scene"])[1]} if a.get("scene") else _scenes(ctx, comp)
    if not scenes:
        raise OpError("NOT_FOUND", "no scene-builder scene in this comp")
    out = {"scenes": scenes}
    if a.get("drift"):
        out["drift"] = {s: _drift(ctx, comp, d) for s, d in scenes.items()}
    if a.get("outPath"):
        p = _out(a["outPath"], "scenes.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(scenes if len(scenes) > 1 else next(iter(scenes.values())), f, indent=1)
        out = {"path": p, "scenes": list(scenes), **({"drift": out["drift"]} if "drift" in out else {})}
    return out


def _drift(ctx, comp, desc):
    from ..luatable import LTable, parse
    c = _compile(desc, ctx)
    tops = [n for n in c.g.order if not c.g.t[n].get("owner")]
    present = [n for n in tops if comp.FindTool(n) is not None]
    missing = [n for n in tops if n not in present]
    live = parse(setting_copy(ctx, comp, {"tools": present})["text"]).get("Tools") if present else None
    diffs = []
    for name, t in (live.items if isinstance(live, LTable) else []):
        want = c.g.t.get(name)
        if not want or not isinstance(t, LTable):
            continue
        ins = t.get("Inputs")
        for iid, v in want["inputs"].items():
            if isinstance(v, (sg.Src, sg.Expr)) or not sg._static(v):
                continue
            lv = ins.get(iid) if isinstance(ins, LTable) else None
            got = lv.get("Value") if isinstance(lv, LTable) else None
            if isinstance(got, LTable):
                got = got.positional()[0] if got.ctor in ("FuID",) and got.positional() else [x for x in got.positional()]
            if got is None:  # CopySettings omits inputs at their default: compare with the live-harvested default
                dflt = sg._tsv_default(want["reg"], iid)
                if dflt is None or _same(v, dflt):
                    continue
                got = dflt
            if not _same(v, got):
                diffs.append({"tool": name, "input": iid, "expected": list(v) if isinstance(v, tuple) else v, "live": got})
    return {"missing": missing, "changed": diffs[:60], "changedCount": len(diffs)}


def _same(want, got, tol=1e-4):
    if got is None:
        return False
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return abs(float(want) - float(got)) <= tol * max(1.0, abs(float(want)))
    if isinstance(want, (int, float)) and isinstance(got, str):
        return False
    if isinstance(want, tuple) and isinstance(got, list):
        return len(want) <= len(got) and all(abs(float(a) - float(b)) <= tol for a, b in zip(want, got))
    return str(want) == str(got)


def _spline_from_path(comp, path):
    t = comp.FindTool(path[0][0])
    for host, iid in path:
        if t is None:
            return None
        o = None
        for i in (t.GetInputList() or {}).values():
            if (i.GetAttrs() or {}).get("INPS_ID") == iid:
                o = i.GetConnectedOutput()
                break
        t = o.GetTool() if o else None
    return t


def _keys_to_eases(ks):
    """Absolute-handle keys (scenegraph.spline_keys) -> ([(f, v)], per-segment eases) for core.write_spline."""
    keys = [(k["f"], k["v"]) for k in ks]
    eases = []
    for j in range(len(ks) - 1):
        a, b = ks[j], ks[j + 1]
        D, V = b["f"] - a["f"], b["v"] - a["v"]
        if a.get("lin") and b.get("lin") or "RH" not in a or "LH" not in b:
            eases.append(("linear",))
        else:
            eases.append(("bezier", (a["RH"][0] - a["f"]) / D, (a["RH"][1] - a["v"]) / V if V else 0.0,
                          (b["LH"][0] - a["f"]) / D, (b["LH"][1] - a["v"]) / V if V else 1.0))
    return keys, eases


@op("scene.update", "Edit a built scene surgically by layer id, without rebuilding: edits [{layer, set: {path: value}, keys: {prop: [...]|null}, "
    "in, out} | {add: layer, after|before|into} | {remove: id} | {scene: {field: value}}], or description: a whole new JSON (diff mode). "
    "Static values are set in place, changed splines rewritten in place, only structurally changed tools are deleted and re-pasted, wires and "
    "enabled regions follow. dryRun returns the ops without touching the comp. quality: 'final' flips CTRL.Draft only.",
    [COMP(), P("scene", "string", "Scene id.", required=True), P("edits", "array", "Surgical edits (see description)."),
     P("description", "object", "Whole new description (diff mode)."), P("dryRun", "boolean", "Plan only."), LAYOUT],
    extra={"paste": True})
def scene_update(ctx, comp, a):
    root, old = _root(ctx, comp, a["scene"])
    try:
        new = a.get("description") or sg.apply_edits(old, a.get("edits") or [])
    except sg.SceneError as e:
        raise _err(e)
    if new.get("scene") != old.get("scene"):
        raise OpError("INVALID_ARGS", "the scene id cannot change in scene.update (build a new scene instead)")
    oc, nc = _compile(old, ctx), _compile(new, ctx)
    ops = sg.diff(oc, nc)
    summ = _summary(ops, oc, nc, detail=bool(a.get("dryRun")))
    if a.get("dryRun"):
        return dict(summ, dryRun=True)
    t0 = time.time()
    gone = ops.get("remove", []) + ops.get("replace", [])
    wires = [list(w) for w in ops.get("rewire", []) + ops.get("connect", [])]
    small = len(ops.get("keys", [])) + len(ops.get("expr", [])) + len(summ["regions"]) + len(summ["resetRegions"]) <= 8
    structural = bool(gone or ops.get("pasteTools") or wires or ops.get("disconnect"))
    same = _same_topology(oc.g, nc.g)   # only tools re-pasted in place: they keep their spots and the layout pass is skipped
    chunk = structural or not small
    pasted = ms = 0
    failed, bad, splines = [], [], {}
    if chunk:   # [sb3] one Lua chunk: delete, paste, wire, keep spots, expressions, regions, spline lookup
        spec, text = update_spec(oc, nc, ops, summ)
        res = repaste(ctx, comp, spec, text)
        pasted, ms, splines = res["pasted"], res["ms"], res["splines"]
        bad = [p for p in res["problems"] if p.endswith("region") or p.endswith("region missing")]
        failed = [[p] for p in res["problems"] if p not in bad and not p.endswith("spline not found")]
        if res["missing"]:
            failed.append(["not found after the paste"] + res["missing"][:10])
        done = len(summ["regions"]) - len(bad)
    else:   # a few values, keys or regions: plain bridge calls (no deferred Execute round trip)
        for e in ops.get("expr", []):
            ctx.inp(ctx.tool(comp, e["tool"]), e["input"]).SetExpression(e["expression"])
        done, bad = _apply_regions(ctx, comp, summ["regions"], summ["resetRegions"])
        bad = [["region"] + b for b in bad]
    for s in ops.get("set", []):   # the compiled value's own type decides the encoding (no per-input type lookup)
        t = ctx.tool(comp, s["tool"])
        v = s["value"]
        t.SetInput(s["input"], {1: v[0], 2: v[1]} if isinstance(v, list) and len(v) == 2 else v)
    for i, k in enumerate(ops.get("keys", [])):
        nm = splines.get(str(i))
        sp = comp.FindTool(nm) if nm else (None if chunk else _spline_from_path(comp, k["path"]))
        if sp is None:
            failed.append([k["host"], k["input"], "spline not found"])
            continue
        keys, eases = _keys_to_eases(k["keys"])
        write_spline(comp, sp, keys, eases, fps=nc.fps)
    for d in ops.get("data", []):
        t = comp.FindTool(d["tool"])
        for kk, vv in (d.get("custom") or {}).items():
            t.SetData(kk, vv)
    lw = []
    if new.get("controlsFrom") and new.get("controlsFrom") != new.get("scene") and \
            (new.get("controls") != old.get("controls") or new.get("quality") != old.get("quality")):
        lw.append("%s follows %s_CTRL (controlsFrom): control values and quality are set on scene %s"
                  % (new["scene"], new["controlsFrom"], new["controlsFrom"]))
    tidy = tidy_after(ctx, comp, a["scene"], "update", lw) if structural and not same and a.get("layout", True) else None
    out = dict(summ, pasted=pasted, pasteMs=ms, regionsApplied=done, ms=int((time.time() - t0) * 1000), layout=tidy)
    if structural and same and a.get("layout", True):
        out["layout"] = {"kept": True}
    if len(summ["regions"]) > 8 or len(summ["resetRegions"]) > 8:   # [sb3 item 6] quiet: counts and samples, the lists in detail
        p = _out(None, "scene_%s_update.json" % a["scene"])
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"regions": summ["regions"], "resetRegions": summ["resetRegions"], "counts": summ["counts"]}, f, indent=1)
        out.update(regions={"count": len(summ["regions"]), "sample": dict(list(summ["regions"].items())[:5])},
                   resetRegions={"count": len(summ["resetRegions"]), "sample": summ["resetRegions"][:5]}, detail=p)
    if lw:
        out["warnings"] = lw
    if failed or bad:
        out["problems"] = failed[:20] + [b if isinstance(b, list) else ["region", b] for b in bad[:10]]
    return out
