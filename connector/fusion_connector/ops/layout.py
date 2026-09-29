"""comp.layout: tidy any comp's node graph in the house graph style (fusion_connector.layout) in two Lua chunks whatever its size:
one reads the graph (names, regIds, groups, positions, wires, underlays), one deletes this op's previous underlays, pastes the new
ones and moves every tool (FlowView QueueSetPos, grid units). scene.build / scene.update call tidy_after()."""
import fnmatch
import json
import os
import tempfile
import time

from .. import layout as lay
from ..schema import P
from .base import COMP, OpError, op
from .build import _out
from .core import _lua_set

# One chunk: every tool's name, regId, parent group, flow position (grid units), our underlay tag, scene-builder output mark,
# then its wires found from its OUTPUTS (Output:GetConnectedInputs lists only the connected inputs; walking every input of
# every tool cost ~15 ms a tool live, since a Text+ has hundreds). Modifiers are skipped (they have no node).
READ_LUA = r"""
local flow = comp.CurrentFrame and comp.CurrentFrame.FlowView
local mods = %s
local L = {}
local function A(o) local ok, a = pcall(function() return o:GetAttrs() end) if ok then return a end end
for _, t in pairs(comp:GetToolList(false) or {}) do
  local a = A(t)
  local n, r = a and a.TOOLS_Name, a and a.TOOLS_RegID
  if n and not mods[r] then
    local p = ""
    local okp, pt = pcall(function() return t.ParentTool end)
    if okp and pt then local pa = A(pt) p = pa and pa.TOOLS_Name or "" end
    local x, y = "", ""
    if flow then
      local ok, gx, gy = pcall(function() return flow:GetPos(t) end)
      if ok and gx then x, y = gx, gy end
    end
    local tag, sb = "", ""
    if r == "Underlay" then
      local okd, dv = pcall(function() return t:GetData("fcLayout") end)
      if okd and dv then tag = tostring(dv) end
    elseif string.sub(n, -4) == "_Out" then
      local oks, v = pcall(function() return t:GetData("sbVersion") end)
      if oks and v then sb = "1" end
    end
    L[#L + 1] = table.concat({"T", n, r, p, tostring(x), tostring(y), tag, sb}, "\t")
    if r ~= "Underlay" and r ~= "Note" then
      for _, o in pairs(t:GetOutputList() or {}) do
        for _, i in pairs(o:GetConnectedInputs() or {}) do
          local ct = i:GetTool()
          local ca = ct and A(ct)
          if ca and ca.TOOLS_Name and not mods[ca.TOOLS_RegID] then
            local ia = A(i)
            L[#L + 1] = "E\t" .. ca.TOOLS_Name .. "\t" .. tostring(ia and ia.INPS_ID or "?") .. "\t" .. n
          end
        end
      end
    end
  end
end
result = table.concat(L, "\n")
"""

# One chunk: delete our old underlays, paste the new ones (Size rides on the paste; Pos is set below like every tool),
# move everything (QueueSetPos + one flush; SetPos if the queue is unavailable).
APPLY_LUA = r"""
local flow = comp.CurrentFrame and comp.CurrentFrame.FlowView
if not flow then error("no FlowView: the comp is not showing on the Fusion page") end
local nd = 0
for _, n in ipairs(%s) do
  local t = comp:FindTool(n)
  local a = t and t:GetAttrs()
  if a and a.TOOLS_RegID == "Underlay" then t:Delete() nd = nd + 1 end
end
local ul = [[%s]]
if ul ~= "" then
  local st = bmd.readfile(ul)
  if type(st) ~= "table" then error("underlay setting failed Fusion parse") end
  comp:SetActiveTool(nil) comp:Lock()
  local okp, perr = pcall(function() comp:Paste(st) end)
  comp:Unlock() comp:SetActiveTool(nil)
  if not okp then error(perr) end
end
local P = bmd.readfile([[%s]])
if type(P) ~= "table" then error("position table failed Fusion parse") end
local moved, missing, queued = 0, {}, true
for _, e in ipairs(P) do
  local t = comp:FindTool(e[1])
  if t then
    if queued then queued = pcall(function() flow:QueueSetPos(t, e[2], e[3]) end) end
    if not queued then flow:SetPos(t, e[2], e[3]) end
    moved = moved + 1
  else
    missing[#missing + 1] = e[1]
  end
end
if queued then flow:FlushSetPosQueue() end
if %s then pcall(function() flow:FrameAll() if flow:GetScale() > 0.5 then flow:SetScale(0.5) end end) end
result = moved .. ";" .. nd .. ";" .. table.concat(missing, ",")
"""


def _mods(ctx):
    return {r for r, v in ctx.tsv().registry.items() if v.get("kind") == "modifier"} | {"BezierSpline", "LUTBezier", "PolyPath", "XYPath"}


def _fusion_page(ctx):
    if ctx.resolve.GetCurrentPage() != "fusion":  # Execute and FlowView need the Fusion page
        ctx.resolve.OpenPage("fusion")
        time.sleep(1.5)


def read_net(ctx, comp):
    mods = _mods(ctx)
    return lay.parse_dump(ctx.lua(comp, READ_LUA % _lua_set(mods), wait=180.0), mods)


def _owned(net, n):
    """Scene-builder tools, the film ladder, Resolve's MediaIn/MediaOut and the connector's own helpers (FC_*, e.g. the
    parked render Saver)."""
    return net.prefix(n) in net.scenes or n.startswith(("FILM_", "FC_")) or net.reg[n] in ("MediaIn", "MediaOut")


def _place(p, full, scoped, anchor):
    """Scoped layouts keep their spot: 'keep' = the scoped tools' old top left, 'below' = under every other tool, or a tool name
    that stays where it is."""
    xs = [p["pos"][n][0] for n in p["pos"]] or [0.0]
    ys = [p["pos"][n][1] for n in p["pos"]] or [0.0]
    x0, y0 = min(xs), min(ys)
    others = [full.old[n] for n in full.reg if n not in scoped and n in full.old]

    def move(dx, dy):  # stay on Fusion's SetPos lattice (half columns, whole rows)
        return lay.translate(p, round(dx * 2) / 2.0, float(round(dy)))
    if anchor in p["pos"] and anchor in full.old:
        ox, oy = full.old[anchor]
        return move(ox - p["pos"][anchor][0], oy - p["pos"][anchor][1])
    if anchor == "below" and others:
        return move(min(o[0] for o in others) - x0, max(o[1] for o in others) + lay.ISLAND_GAP + 2 - y0)
    old = [full.old[n] for n in scoped if n in full.old]
    if old:
        return move(min(o[0] for o in old) - x0, min(o[1] for o in old) - y0)
    return p


def _intruders(p, full, scoped):
    """Tools outside the scope whose tiles sit inside the new layout area (the scoped layout grew into them)."""
    rs = [b["rect"] for b in p["boxes"]]
    xs = [v[0] for v in p["pos"].values()]
    ys = [v[1] for v in p["pos"].values()]
    if xs:
        rs.append([min(xs) - lay.H, min(ys) - lay.H, max(xs) + lay.H, max(ys) + lay.TB])
    out = []
    for n, (x, y) in full.old.items():
        if n not in scoped and any(r[0] < x + lay.H and x - lay.H < r[2] and r[1] < y + lay.TB and y - lay.H < r[3] for r in rs):
            out.append(n)
    return sorted(out)


def layout_live(ctx, comp, scene=None, tools=None, underlays=True, dry=False, fit=False, anchor="keep", preview=False, own_scene=None,
                full=None):
    """Read, plan, apply. own_scene (scene.build/update): the whole comp when every tool belongs to scene-builder scenes, the
    film ladder or MediaIn/MediaOut; else only that scene's tools (a user's hand-placed tools are never moved unasked)."""
    t0 = time.time()
    _fusion_page(ctx)
    if not ctx.is_current(comp):
        raise OpError("NOT_CURRENT", "comp.layout works on the comp showing on the Fusion page",
                      hint="Pass comp as {timeline, item} (made current automatically) or call comp.set_current first.")
    full = full or read_net(ctx, comp)
    notes = []
    if own_scene is not None:
        foreign = [n for n in full.reg if not _owned(full, n)]
        if foreign:
            scene = own_scene
            notes.append("%d tools are not scene-builder tools (e.g. %s): only scene %s was laid out" % (len(foreign), foreign[:3], own_scene))
    scoped = None
    if scene:
        scoped = {n for n in full.reg if full.prefix(n) == scene}
    elif tools:
        pats = tools if isinstance(tools, list) else [tools]
        scoped = {n for n in full.reg if any(fnmatch.fnmatchcase(n, pt) for pt in pats)}
    if scoped is not None and not scoped:
        raise OpError("NOT_FOUND", "no tools in the layout scope", details={"scene": scene, "tools": tools},
                      hint="scene ids come from scene.export; tools takes names or globs")
    net = full.sub(scoped) if scoped is not None else full
    ours = {n for n, tag in full.underlays.items() if tag}
    taken = set(full.reg) | (set(full.underlays) - ours)
    p = lay.plan(net, taken=taken)
    if scoped is not None:
        p = _place(p, full, scoped, anchor)
    if not underlays:
        p["boxes"] = []
        drop = []
    elif scoped is None:
        drop = sorted(ours)
    else:
        mine = {b["name"] for b in p["boxes"]}
        drop = sorted(n for n in ours if n in mine or (scene and n.startswith(scene + "_")))
    m = lay.metrics(p, net)
    if not m["boxProblems"]:
        m.pop("boxProblems")
    out = {"tools": len(p["pos"]), "scope": scene or (tools if scoped is not None else "comp"), "bands": len(p["bands"]),
           "mainSpine": len(p["bands"][0]["spine"]) if p["bands"] else 0, "underlays": len(p["boxes"]),
           "shared": p["shared"][:10], "metrics": m}
    foreign_ul = sorted(set(full.underlays) - ours)
    if foreign_ul:
        notes.append("%d underlays not made by comp.layout were left where they are: %s" % (len(foreign_ul), foreign_ul[:5]))
    if scoped is not None:
        intr = _intruders(p, full, scoped)
        if intr:
            notes.append("%d tools outside the scope sit inside the new layout area (e.g. %s): run comp.layout on the whole comp"
                         % (len(intr), intr[:5]))
    detail = _out(None, "layout_%s.json" % (scene or "comp"))
    with open(detail, "w", encoding="utf-8") as f:
        json.dump(dict(p, metrics=m), f, indent=1)
    out["detail"] = detail
    if preview:
        pp = _out(None, "layout_%s.png" % (scene or "comp"))
        lay.preview(p, net, pp)
        out["preview"] = pp
        out["_inline"] = [pp]
    if dry:
        out.update(dryRun=True, boxes=[{"name": b["name"], "kind": b["kind"]} for b in p["boxes"][:40]], notes=notes,
                   ms=int((time.time() - t0) * 1000))
        return out
    moved, nd, missing = apply(ctx, comp, p, drop, fit)
    out.update(moved=moved, underlaysRemoved=nd, ms=int((time.time() - t0) * 1000), notes=notes)
    if missing:
        out["missing"] = missing[:20]
    return out


def apply(ctx, comp, p, drop, fit=False):
    """-> (moved, underlays deleted, [names not found]). Positions and underlays go through two temp files read by bmd.readfile."""
    rows = lay.set_pos(p)
    tmp = []
    try:
        ul = ""
        if p["boxes"]:
            fd, ul = tempfile.mkstemp(suffix=".setting")
            tmp.append(ul)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(lay.underlay_setting(p["boxes"]))
        fd, pp = tempfile.mkstemp(suffix=".lua")
        tmp.append(pp)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("{\n" + "\n".join("{ %s, %s, %s }," % (json.dumps(n), lay._num(x), lay._num(y)) for n, x, y in rows) + "\n}\n")
        code = APPLY_LUA % ("{" + ", ".join(json.dumps(n) for n in drop) + "}", ul, pp, "true" if fit else "false")
        r = ctx.lua(comp, code, wait=min(600.0, 30.0 + 0.02 * len(rows)))
    finally:
        for t in tmp:
            os.unlink(t)
    moved, nd, miss = (r.split(";", 2) + ["0", "0", ""])[:3]
    return int(moved), int(nd), [x for x in miss.split(",") if x]


def tidy_after(ctx, comp, scene, mode, warnings):
    """scene.build / scene.update hook: house-style layout after the paste; a failure is a warning, never a failed build."""
    try:
        r = layout_live(ctx, comp, own_scene=scene, anchor="below" if mode == "build" else scene + "_Out", fit=mode == "build")
        return {k: r[k] for k in ("scope", "tools", "underlays", "ms") if k in r}
    except OpError as e:
        warnings.append("node layout skipped: %s" % e.message)
    except Exception as e:  # noqa: a cosmetic pass never fails the build it follows; the reason is reported
        warnings.append("node layout skipped: %s: %s" % (type(e).__name__, e))
    return None


@op("comp.layout", "Tidy the node graph of ANY comp in the house graph style (fusion-motion-design 'House graph style'): the compositing "
    "pipe (Merge Background chain, film ladder) as one straight left-to-right spine; each layer's source chain as a vertical column above "
    "the Merge it feeds (side inputs left, masks right), masks of spine tools below it; controllers, unwired tools and shared assets in "
    "the band's top-left corner; labeled, colour-coded underlays (UI only, no render cost) per scene/prefix, layer group, controls and "
    "shared assets, refreshed on every run (a user's own underlays are left alone). Two Lua chunks whatever the size (one read, one "
    "apply); one undo event. dryRun returns the plan and its metrics (overlaps, crossings, wires over tools, spines straight) without "
    "touching the comp; preview draws it.",
    [COMP(), P("scene", "string", "Only this scene's tools (name prefix '<scene>_'); they keep their spot in the comp."),
     P("tools", "string|array", "Only these tools (names or globs); they keep their spot."),
     P("underlays", "boolean", "Add/refresh the labeled underlays (default true; false leaves underlays untouched)."),
     P("fit", "boolean", "Frame the whole graph in the node editor afterwards (FrameAll, zoom capped at 0.5: FrameAll alone zooms in "
                         "too far when node thumbnails are on). Default false: the user's view is left alone."),
     P("dryRun", "boolean", "Plan only: tools, bands, underlays, metrics; nothing moves."),
     P("preview", "boolean", "Draw the planned graph (PNG, returned inline).")],
    extra={"paste": True})
def comp_layout(ctx, comp, a):
    if a.get("scene") and a.get("tools"):
        raise OpError("INVALID_ARGS", "pass scene or tools, not both")
    return layout_live(ctx, comp, scene=a.get("scene"), tools=a.get("tools"), underlays=a.get("underlays", True),
                       dry=bool(a.get("dryRun")), fit=bool(a.get("fit")), preview=bool(a.get("preview")))
