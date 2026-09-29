"""Operation registry, the worker-side Resolve context, and shared helpers.

Handlers run in the worker process (fusion_connector.worker) with a live Ctx. Every live-verified
rule from fusion-reference/references/fusion-realities.md that affects correctness is enforced here,
not only documented: SetActiveTool(None) before AddTool (the auto-connect trap), Lock/Unlock around
AddTool (no file dialogs), checked ConnectInput + readback, paste only on the current Fusion-page comp
with deferred-Execute polling, AddModifier success judged by GetConnectedOutput, the stray seeded
key fix, expression clear with value restore, measured units, pasted-default differences."""
import math
import os
import re
import struct
import sys
import tempfile
import time
import uuid

from .. import config
from ..schema import Op, P, TSV

OPS = {}


def iid_of(i):
    """Input ID; group/macro instance inputs may lack INPS_ID."""
    a = i.GetAttrs() or {}
    return a.get("INPS_ID") or a.get("INPS_Name") or "?"


def oid_of(o):
    a = o.GetAttrs() or {}
    return a.get("OUTS_ID") or a.get("OUTS_Name") or "?"


class OpError(Exception):
    def __init__(self, code, message, hint=None, details=None):
        super().__init__(message)
        self.code, self.message, self.hint, self.details = code, message, hint, details


def op(name, desc, params=(), category=None, **kw):
    def deco(fn):
        OPS[name] = Op(name, category or name.split(".")[0], desc, list(params), fn, **kw)
        return fn
    return deco


# ---------------------------------------------------------------- common params

def COMP():
    return P("comp", "string|object",
             "Target comp. Omit (or 'current') for the comp showing on the Fusion page. Or an object "
             "{timeline?: name (default current), track?: 1, item?: 0-based index or clip name (default 0), comp?: name or 1-based index (default 1)}.")


def TOOL(desc="Tool name in the comp (exact, as shown in the node editor)."):
    return P("tool", "string", desc, required=True)


def INPUT(desc="Input ID (TSV/registry ID, e.g. 'Center', 'Size', 'StyledText', 'Transform3DOp.Translate.Z'), not the UI label."):
    return P("input", "string", desc, required=True)


FRAME = P("frame", "number", "Comp frame (not seconds). Default: the comp's current time.")


# ---------------------------------------------------------------- value conversion

def jv(v, _d=0):
    """Fusion/Lua value -> JSON. 1..n int-keyed tables become lists (points -> [x, y])."""
    if _d > 12:
        return str(v)
    if v is None or isinstance(v, (bool, str, int)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else str(v)
    if isinstance(v, dict):
        ks = list(v.keys())
        try:
            ints = sorted(int(float(k)) for k in ks)
            if ks and ints == list(range(1, len(ks) + 1)) and all(float(k) == int(float(k)) for k in ks):
                return [jv(v[k], _d + 1) for k in sorted(ks, key=lambda k: float(k))]
        except (TypeError, ValueError):
            pass
        return {str(k): jv(x, _d + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jv(x, _d + 1) for x in v]
    try:
        a = v.GetAttrs() or {}
        return "<%s>" % (a.get("TOOLS_Name") or a.get("INPS_ID") or a.get("OUTS_ID") or type(v).__name__)
    except Exception:
        return str(v)


def num(x, nd=6):
    return round(float(x), nd) if isinstance(x, (int, float)) and math.isfinite(x) else x


def hex_rgb(h):
    h = h.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", h):
        raise OpError("INVALID_ARGS", f"bad hex color '{h}'", hint="use '#rrggbb' or [r, g, b] floats 0-1")
    c = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
    return c


def color(c, default=None):
    """'#hex' | [r,g,b(,a)] 0-1 | {r,g,b,a} -> [r,g,b,a]."""
    if c is None:
        c = default
    if c is None:
        return None
    if isinstance(c, str):
        c = hex_rgb(c)
    elif isinstance(c, dict):
        c = [c.get("r", 0), c.get("g", 0), c.get("b", 0), c.get("a", 1)]
    c = [float(x) for x in c]
    if len(c) == 3:
        c.append(1.0)
    if len(c) != 4:
        raise OpError("INVALID_ARGS", f"color needs 3 or 4 channels, got {len(c)}")
    return c


# ---------------------------------------------------------------- PNG (no PIL)

def png_info(path):
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise OpError("OPERATION_FAILED", f"{path} is not a PNG")
    w, h, bd, ct = struct.unpack(">IIBB", head[16:26])
    return {"width": w, "height": h, "bitDepth": bd, "colorType": ct, "alpha": ct in (4, 6)}


def png_bbox(path, threshold=1):
    """Bounding box of visible pixels (alpha > threshold/255; any channel when there is no alpha).
    macOS sips converts the PNG to an uncompressed 32-bit BMP (~0.1 s at UHD); rows are scanned with
    C-level bytes ops. Without sips (Linux, Windows) Pillow does the same job. Returns a pixel box with a
    TOP-LEFT origin, or None when nothing is visible."""
    import shutil
    import subprocess
    import tempfile
    info = png_info(path)
    if not shutil.which("sips"):
        return _png_bbox_pillow(path, threshold, info)
    fd, bmp = tempfile.mkstemp(suffix=".bmp")
    os.close(fd)
    try:
        subprocess.run(["sips", "-s", "format", "bmp", path, "--out", bmp], check=True, capture_output=True, timeout=60)
        d = open(bmp, "rb").read()
    finally:
        os.unlink(bmp)
    off = struct.unpack("<I", d[10:14])[0]
    hsize, w, h, _, bpp, comp = struct.unpack("<IiiHHI", d[14:34])
    if bpp != 32:                                   # sips writes 24-bit BMP for PNGs without alpha
        return _png_bbox_pillow(path, threshold, info)
    top_down = h < 0
    h = abs(h)
    masks = struct.unpack("<IIII", d[54:70]) if comp == 3 and hsize >= 56 else (0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    amask = masks[3]
    use_alpha = info["alpha"] and amask
    idx = {0xFF: 0, 0xFF00: 1, 0xFF0000: 2, 0xFF000000: 3}
    table = bytes(0 if v <= threshold else 255 for v in range(256))
    px = d[off:off + w * h * 4]
    chans = [idx[amask]] if use_alpha else [idx[m] for m in masks[:3]]
    x0, y0, x1, y1 = w, h, -1, -1
    for ch in chans:
        plane = px[ch::4].translate(table)
        for r in range(h):
            row = plane[r * w:(r + 1) * w]
            if row.count(0) == w:
                continue
            y = r if top_down else h - 1 - r
            first = len(row) - len(row.lstrip(b"\x00"))
            last = len(row.rstrip(b"\x00")) - 1
            x0, x1, y0, y1 = min(x0, first), max(x1, last), min(y0, y), max(y1, y)
    if x1 < 0:
        return None
    return {"x": x0, "y": y0, "width": x1 - x0 + 1, "height": y1 - y0 + 1, "imageWidth": w, "imageHeight": h,
            "alphaUsed": bool(use_alpha)}


def _png_bbox_pillow(path, threshold, info):
    from PIL import Image, ImageChops
    im = Image.open(path)
    w, h = im.size
    use_alpha = bool(info["alpha"]) and "A" in im.getbands()
    if use_alpha:
        plane = im.getchannel("A")
    else:
        r, g, b = im.convert("RGB").split()
        plane = ImageChops.lighter(ImageChops.lighter(r, g), b)
    box = plane.point(lambda v: 255 if v > threshold else 0).getbbox()
    if box is None:
        return None
    x0, y0, x1, y1 = box
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0, "imageWidth": w, "imageHeight": h,
            "alphaUsed": use_alpha}


# ---------------------------------------------------------------- skills scripts (one source of truth)

# One chunk: the paste plus its name check, done in Lua, not over the bridge. [sb3] The check costs FindTool per PASTED name: listing
# every tool before and after (GetToolList + GetAttrs each) made a paste into a 2,000-tool comp 3.5 s vs 626 ms empty. Only when a
# pasted name already exists (Fusion then renames the pasted tool: Name_1, Name_2 ...) does it diff the whole comp as before.
PASTE_LUA = """
local names = %s
local function nameof(t) local ok, a = pcall(function() return t:GetAttrs() end) if ok and a then return a.TOOLS_Name end end
local clash = false
for _, n in ipairs(names) do if comp:FindTool(n) then clash = true break end end
local before = nil
if clash then
  before = {}
  for _, t in pairs(comp:GetToolList(false)) do local n = nameof(t) if n then before[n] = true end end
end
local s = bmd.readfile([[%s]])
if type(s) ~= 'table' then error('setting failed Fusion parse; nothing pasted') end
-- Lock: a pasted Loader otherwise opens a modal file browser that blocks scripting (live, 21.1).
comp:SetActiveTool(nil) comp:Lock()
local okp, perr = pcall(function() comp:Paste(s) end)
comp:Unlock() comp:SetActiveTool(nil)
if not okp then error(perr) end
local added, ren, miss = {}, {}, {}
if clash then
  for _, t in pairs(comp:GetToolList(false)) do
    local n = nameof(t)
    if n and not before[n] then
      added[#added + 1] = n
      local b = n:match('^(.*)_%%d+$')
      if b and before[b] then ren[#ren + 1] = b .. '=' .. n end
    end
  end
else
  for _, n in ipairs(names) do if comp:FindTool(n) then added[#added + 1] = n else miss[#miss + 1] = n end end
end
result = table.concat(added, ',') .. ';' .. table.concat(ren, ',') .. ';' .. table.concat(miss, ',')
"""


def lua_list(names):
    """Python strings -> a Lua array literal."""
    import json
    return "{" + ", ".join(json.dumps(n) for n in names) + "}"


def lua_wrap(code, key):
    """The Execute body of Ctx.lua: run code (which sets `result`) and report through comp CustomData `key` (Execute is deferred and
    silent, realities §9). Module level so the offline LuaJIT tests run exactly what Resolve runs."""
    return ("local ok, err = pcall(function() local result = nil; %s; comp:SetData('%s', 'OK:' .. tostring(result)) end) "
            "if not ok then comp:SetData('%s', 'ERR:' .. tostring(err)) end") % (code, key, key)

_KIT = {}


def kit(resolve=None):
    """fusion_kit.py loaded from the installed skill (never copied). resolve is injected per call."""
    path = os.path.join(config.scripts_dir(), "fusion_kit.py")
    if not os.path.exists(path):
        raise OpError("NOT_FOUND", f"fusion_kit.py not found at {path}",
                      hint="Install the fusion-motion-design skill or set FUSION_MCP_SKILLS_ROOT.")
    mt = os.path.getmtime(path)
    if _KIT.get("mtime") != mt:
        ns = {"resolve": None, "__name__": "fusion_kit", "__file__": path}
        exec(compile(open(path, encoding="utf-8").read(), path, "exec"), ns)
        _KIT.clear()
        _KIT.update(ns=ns, mtime=mt)
    if resolve is not None:
        _KIT["ns"]["resolve"] = resolve
    return _KIT["ns"]


_BUILD = {}


def build_module():
    """fusion_build.py loaded from the installed skill (it loads fusion_kit itself when standalone)."""
    path = os.path.join(config.scripts_dir(), "fusion_build.py")
    if not os.path.exists(path):
        raise OpError("NOT_FOUND", f"fusion_build.py not found at {path}",
                      hint="Install the fusion-motion-design skill or set FUSION_MCP_SKILLS_ROOT.")
    mt = os.path.getmtime(path)
    if _BUILD.get("mtime") != mt:
        ns = {"__name__": "fusion_build", "__file__": path}
        exec(compile(open(path, encoding="utf-8").read(), path, "exec"), ns)
        _BUILD.clear()
        _BUILD.update(ns=ns, mtime=mt)
    return _BUILD["ns"]


# ---------------------------------------------------------------- worker context

def _tc_to_frames(tc, fps):
    parts = re.split(r"[:;]", tc)
    h, m, s, f = (int(x) for x in parts)
    r = int(round(fps))
    return ((h * 60 + m) * 60 + s) * r + f


def _frames_to_tc(n, fps, sep=":"):
    r = int(round(fps))
    f = n % r
    s = n // r
    return "%02d:%02d:%02d%s%02d" % (s // 3600, (s // 60) % 60, s % 60, sep, f)


class Ctx:
    """Live Resolve access for one worker. Reconnects lazily after a restart."""

    def __init__(self):
        self._resolve = None
        self.policy = {}
        self.notes = []

    # -- connection
    @property
    def resolve(self):
        if self._resolve is not None:
            try:
                self._resolve.GetVersionString()
                return self._resolve
            except Exception:
                self._resolve = None
        mod = os.environ.get("RESOLVE_SCRIPT_API")
        paths = [os.path.join(mod, "Modules")] if mod else []
        paths.append(config.MODULES_DIR)
        for p in paths:
            if p not in sys.path:
                sys.path.append(p)
        try:
            import DaVinciResolveScript as dvr  # noqa
        except ImportError as e:
            raise OpError("RESOLVE_UNAVAILABLE", f"cannot import DaVinciResolveScript: {e}",
                          hint="Install DaVinci Resolve Studio; set RESOLVE_SCRIPT_API/RESOLVE_SCRIPT_LIB for a custom install.")
        r = dvr.scriptapp("Resolve")
        if r is None:
            raise OpError("RESOLVE_UNAVAILABLE", "DaVinci Resolve is not reachable through external scripting",
                          hint="Open DaVinci Resolve Studio (the free edition has no external scripting) and set "
                               "Preferences > System > General > External scripting using = Local.")
        self._resolve = r
        return r

    def fusion(self):
        f = self.resolve.Fusion()
        if f is None:
            raise OpError("RESOLVE_UNAVAILABLE", "resolve.Fusion() returned None")
        return f

    def project(self):
        p = self.resolve.GetProjectManager().GetCurrentProject()
        if p is None:
            raise OpError("NOT_FOUND", "no project is open in Resolve")
        return p

    def require_project_allowed(self):
        allowed = self.policy.get("projects")
        if not allowed:
            return
        name = self.project().GetName()
        if name not in allowed:
            raise OpError("FORBIDDEN", f"current project '{name}' is not in FUSION_MCP_PROJECT_ALLOWLIST",
                          hint="Open an allowlisted project (" + ", ".join(allowed) + ") or widen the allowlist.",
                          details={"project": name, "allowlist": allowed})

    # -- timelines / items
    def timeline(self, name=None, required=True):
        p = self.project()
        if not name:
            tl = p.GetCurrentTimeline()
            if tl is None and required:
                raise OpError("NOT_FOUND", "no current timeline", hint="Open a timeline or pass comp.timeline")
            return tl
        for i in range(1, p.GetTimelineCount() + 1):
            t = p.GetTimelineByIndex(i)
            if t.GetName() == name:
                return t
        if required:
            names = [p.GetTimelineByIndex(i).GetName() for i in range(1, p.GetTimelineCount() + 1)]
            from ..schema import suggest
            s = suggest(name, names)
            raise OpError("NOT_FOUND", f"timeline '{name}' not found" + (f" - did you mean '{s}'?" if s else ""),
                          details={"timelines": names[:50]})
        return None

    def item(self, ref):
        tl = self.timeline(ref.get("timeline"))
        track = int(ref.get("track", 1))
        items = tl.GetItemListInTrack("video", track) or []
        it = ref.get("item", 0)
        if isinstance(it, str):
            hits = [x for x in items if x.GetName() == it]
            if not hits:
                raise OpError("NOT_FOUND", f"no clip named '{it}' on video track {track} of '{tl.GetName()}'",
                              details={"clips": [x.GetName() for x in items][:50]})
            return tl, hits[0]
        it = int(it)
        if it < 0 or it >= len(items):
            raise OpError("NOT_FOUND", f"video track {track} of '{tl.GetName()}' has {len(items)} items; index {it} is out of range",
                          hint="item is 0-based")
        return tl, items[it]

    def comp(self, ref=None):
        if ref in (None, "", "current"):
            c = self.fusion().GetCurrentComp()
            if c is None:
                raise OpError("NOT_FOUND", "no current Fusion comp",
                              hint="Open the Fusion page on a Fusion clip, or call comp.set_current with {timeline, item}.")
            return c
        if isinstance(ref, str):
            raise OpError("INVALID_ARGS", f"comp '{ref}' is ambiguous: pass 'current' or an object {{timeline, item, comp}}")
        tl, item = self.item(ref)
        cref = ref.get("comp", 1)
        c = item.GetFusionCompByName(cref) if isinstance(cref, str) else item.GetFusionCompByIndex(int(cref))
        if c is None:
            raise OpError("NOT_FOUND", f"item '{item.GetName()}' has no Fusion comp {cref!r}",
                          details={"comps": list((item.GetFusionCompNameList() or {}).values()) if hasattr(item, "GetFusionCompNameList") else None},
                          hint="comp.create adds one; comp.list shows what exists.")
        return c

    def identity(self, comp):
        """[rebuild F15] Which comp a render/compare ran in: item comps are all 'Composition1', so name the MediaOut1 source."""
        a = comp.GetAttrs() or {}
        mo = comp.FindTool("MediaOut1")
        return {"name": a.get("COMPS_Name"), "mediaOutSource": (self.source_of(mo, "Input") or [None])[0] if mo else None,
                "tools": len(comp.GetToolList(False) or {}), "globalRange": [num(a.get("COMPN_GlobalStart")), num(a.get("COMPN_GlobalEnd"))]}

    def is_current(self, comp):
        """Identity check through a SetData token (remote objects do not compare by value)."""
        tok = uuid.uuid4().hex
        comp.SetData("fc_ident", tok)
        try:
            cur = self.fusion().GetCurrentComp()
            return cur is not None and cur.GetData("fc_ident") == tok
        finally:
            comp.SetData("fc_ident", "")

    def make_current(self, ref, settle=1.5):
        """Show an item's comp on the Fusion page (required for Paste). realities §1.
        [rebuild F11] For items on V2+ the playhead only moves reliably on the Edit page after it settles, so:
        Edit page, settle, playhead to the item's MIDDLE frame (read back), Fusion page, identity check by token."""
        r = self.resolve
        if ref in (None, "", "current"):
            c = self.comp(None)
            if r.GetCurrentPage() != "fusion":
                r.OpenPage("fusion")
                time.sleep(settle)
            return c
        tl, item = self.item(ref)
        target = self.comp(ref)
        if r.GetCurrentPage() == "fusion" and self.is_current(target):
            return target  # already showing: no page round trip
        p = self.project()
        cur = p.GetCurrentTimeline()
        if cur is None or cur.GetName() != tl.GetName():
            p.SetCurrentTimeline(tl)
        cref = ref.get("comp", 1)
        if isinstance(cref, str):
            item.LoadFusionCompByName(cref)
        elif int(cref) > 1:
            names = jv(item.GetFusionCompNameList()) or []
            if len(names) >= int(cref):
                item.LoadFusionCompByName(names[int(cref) - 1])
        fps = float(tl.GetSetting("timelineFrameRate") or 24)
        start_tc = tl.GetStartTimecode()
        s0, e0 = int(item.GetStart()), int(item.GetEnd())
        mid = s0 + max(0, (e0 - s0 - 1) // 2)
        tc = _frames_to_tc(_tc_to_frames(start_tc, fps) + (mid - tl.GetStartFrame()), fps, ";" if ";" in start_tc else ":")
        track = int(ref.get("track", 1))
        cover = []
        for k in range(track + 1, (tl.GetTrackCount("video") or 0) + 1):
            try:
                if not tl.GetIsTrackEnabled("video", k):
                    continue
            except Exception:  # noqa
                pass
            for it in tl.GetItemListInTrack("video", k) or []:
                if it.GetStart() <= mid < it.GetEnd():
                    cover.append({"track": k, "clip": it.GetName()})
        for attempt, edit_settle in enumerate((max(settle, 1.5), 3.0)):
            if r.GetCurrentPage() != "edit":
                r.OpenPage("edit")
                time.sleep(edit_settle)
            moved = False
            t_end = time.time() + 4
            while time.time() < t_end:
                tl.SetCurrentTimecode(tc)
                time.sleep(0.3)
                if tl.GetCurrentTimecode() == tc:
                    moved = True
                    break
            r.OpenPage("fusion")
            time.sleep(settle)
            deadline = time.time() + 4
            while time.time() < deadline:
                if self.is_current(target):
                    return target
                time.sleep(0.25)
            if cover:
                break
        raise OpError("NOT_CURRENT", "could not make the requested comp current on the Fusion page" +
                      (" (a clip on a higher video track covers the playhead)" if cover else ""),
                      hint=("The Fusion page shows the topmost clip under the playhead: disable or move the covering track's clip, then retry."
                            if cover else "Open the Fusion page on that clip manually (Edit page: park the playhead inside it), then retry with comp omitted."),
                      details={"timeline": tl.GetName(), "track": track, "item": item.GetName(), "timecode": tc,
                               "playheadMoved": moved, "coveredBy": cover})

    # -- tools / inputs
    def names(self, comp):
        return sorted(t.GetAttrs()["TOOLS_Name"] for t in (comp.GetToolList(False) or {}).values())

    def tool(self, comp, name):
        if not isinstance(name, str) or not name:
            raise OpError("INVALID_ARGS", "tool name must be a non-empty string")
        t = comp.FindTool(name)
        if t is None:
            from ..schema import suggest
            names = self.names(comp)
            s = suggest(name, names)
            raise OpError("NOT_FOUND", f"no tool named '{name}' in the comp" + (f" - did you mean '{s}'?" if s else ""),
                          details={"toolCount": len(names), "sample": names[:20]}, hint="tool.list (name glob) shows the tools, including modifiers.")
        return t

    def tools_matching(self, comp, pattern):
        """'all', exact name, glob ('Connector_*') or list of names."""
        import fnmatch
        if isinstance(pattern, list):  # [rebuild F6] globs inside lists; exact names must exist
            out, seen = [], set()
            for pt in pattern:
                for n, t in self.tools_matching(comp, pt):
                    if n not in seen:
                        seen.add(n)
                        out.append((n, t))
            return out
        if pattern == "all" or any(ch in pattern for ch in "*?["):
            allt = {t.GetAttrs()["TOOLS_Name"]: t for t in (comp.GetToolList(False) or {}).values()}
            if pattern == "all":
                return sorted(allt.items())
            return sorted((n, t) for n, t in allt.items() if fnmatch.fnmatchcase(n, pattern))
        return [(pattern, self.tool(comp, pattern))]

    def inputs(self, tool):
        return {iid_of(i): i for i in (tool.GetInputList() or {}).values()}

    def inp(self, tool, iid):
        ins = self.inputs(tool)
        if iid in ins:
            return ins[iid]
        from ..schema import suggest
        reg = tool.GetAttrs()["TOOLS_RegID"]
        s = suggest(iid, list(ins))
        by_label = [k for k, i in ins.items() if (i.GetAttrs().get("INPS_Name") or "").lower().replace(" ", "") == iid.lower().replace(" ", "")]
        s = by_label[0] if by_label else s
        raise OpError("NOT_FOUND", f"{tool.GetAttrs()['TOOLS_Name']} ({reg}) has no input '{iid}'" + (f" - did you mean '{s}'?" if s else ""),
                      hint="input.list shows live IDs; Text+ shading elements 2-8 exist only after a .setting paste with EnabledN = 1.")

    def outputs(self, tool):
        return {oid_of(o): o for o in (tool.GetOutputList() or {}).values()}

    def fmt(self, comp):
        w = comp.GetPrefs("Comp.FrameFormat.Width")
        h = comp.GetPrefs("Comp.FrameFormat.Height")
        r = comp.GetPrefs("Comp.FrameFormat.Rate")
        return int(w or 1920), int(h or 1080), float(r or 24)

    def tsv(self):
        return TSV.get()

    # -- creation (the auto-connect trap, realities §5)
    def add_tool(self, comp, reg, name=None, x=None, y=None):
        err = self.tsv().check_reg(reg)
        if err:
            raise OpError("INVALID_ARGS", err)
        before = set(self.names(comp))
        comp.SetActiveTool(None)
        comp.Lock()
        try:
            t = comp.AddTool(reg, False, -32768 if x is None else x, -32768 if y is None else y, False, False)
        finally:
            comp.Unlock()
        if t is None:
            raise OpError("OPERATION_FAILED", f"AddTool('{reg}') returned None")
        if name:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                t.Delete()
                raise OpError("INVALID_ARGS", f"tool name '{name}' is invalid: letters, digits, underscore; no leading digit")
            if comp.FindTool(name) is not None and name not in (t.GetAttrs()["TOOLS_Name"],):
                t.Delete()
                raise OpError("INVALID_ARGS", f"a tool named '{name}' already exists", hint="Names must be unique per comp.")
            t.SetAttrs({"TOOLS_Name": name})
            got = t.GetAttrs()["TOOLS_Name"]
            if got != name:
                t.Delete()
                raise OpError("OPERATION_FAILED", f"name '{name}' became '{got}'")
        stray = sorted(set(self.names(comp)) - before - {t.GetAttrs()["TOOLS_Name"]})
        if stray:  # auto-merge side effects despite the flags: remove them
            for n in stray:
                s = comp.FindTool(n)
                if s is not None:
                    s.Delete()
            self.notes.append(f"removed auto-created tools {stray}")
        return t

    def connect(self, dst, iid, src, output=None):
        """ConnectInput that fails loudly and reads back (it returns False on loops/type mismatch)."""
        self.inp(dst, iid)
        target = src
        if output:
            outs = self.outputs(src)
            if output not in outs:
                raise OpError("NOT_FOUND", f"{src.GetAttrs()['TOOLS_Name']} has no output '{output}'",
                              details={"outputs": list(outs)})
            target = outs[output]
        ok = dst.ConnectInput(iid, target)
        got = self.source_of(dst, iid)
        if not got and output is None:  # [rebuild F8] generic-typed inputs (pasted Switch Input0..N): try the Output object
            mo = src.FindMainOutput(1)
            if mo is not None:
                ok = dst.ConnectInput(iid, mo)
                got = self.source_of(dst, iid)
                if not got:
                    try:
                        self.inp(dst, iid).ConnectTo(mo)
                        got = self.source_of(dst, iid)
                        ok = bool(got)
                    except Exception:  # noqa
                        pass
        want = src.GetAttrs()["TOOLS_Name"]
        grouped = src.GetAttrs()["TOOLS_RegID"] in ("MacroOperator", "GroupOperator")  # readback names the inner tool
        if not ok or not got or (got[0] != want and not grouped):
            raise OpError("OPERATION_FAILED",
                          f"ConnectInput {dst.GetAttrs()['TOOLS_Name']}.{iid} <- {want} failed (loop, type mismatch, or wrong port)",
                          details={"readback": got})
        return got

    def source_of(self, tool, iid):
        try:
            o = self.inp(tool, iid).GetConnectedOutput()
        except OpError:
            return None
        if not o:
            return None
        ot = o.GetTool()
        return [ot.GetAttrs()["TOOLS_Name"] if ot else "<group output>", oid_of(o)]

    def consumers(self, comp, tool, output=None):
        """[(consumer_name, input_id, output_id)] reading from tool. Reads the tool's own outputs
        (Output.GetConnectedInputs); the whole-comp input scan is only a fallback (it is O(all inputs)
        in bridge calls and made mass deletes on a 130-tool comp time out)."""
        name = tool.GetAttrs()["TOOLS_Name"]
        try:
            found = []
            for o in (tool.GetOutputList() or {}).values():
                if output is not None and oid_of(o) != output:
                    continue
                for i in (o.GetConnectedInputs() or {}).values():
                    ct = i.GetTool()
                    if ct is not None:
                        found.append((ct.GetAttrs()["TOOLS_Name"], iid_of(i), oid_of(o)))
            return found
        except Exception:  # noqa: fall back to the full scan
            pass
        found = []
        for t in (comp.GetToolList(False) or {}).values():
            tn = t.GetAttrs()["TOOLS_Name"]
            for i in (t.GetInputList() or {}).values():
                o = i.GetConnectedOutput()
                ot = o.GetTool() if o else None
                if ot is not None and ot.GetAttrs()["TOOLS_Name"] == name and (output is None or oid_of(o) == output):
                    found.append((tn, iid_of(i), oid_of(o)))
        return found

    # -- values
    def to_fusion(self, comp, tool, iid, v):
        """JSON -> SetInput value, using the live input type. Points accept [x,y], {x,y}, {'px':[x,y]}."""
        dt = (self.inp(tool, iid).GetAttrs() or {}).get("INPS_DataType")
        if dt == "Point":
            if isinstance(v, dict) and "px" in v:
                W, H, _ = self.fmt(comp)
                x, y = v["px"][:2]
                return {1: x / W, 2: 1 - y / H}
            if isinstance(v, dict):
                return {1: float(v.get("x", v.get("1", 0.5))), 2: float(v.get("y", v.get("2", 0.5)))}
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                return {1: float(v[0]), 2: float(v[1])}
            raise OpError("INVALID_ARGS", f"{iid} is a Point: pass [x, y] (0-1, Y up) or {{'px': [x, y]}} (top-left pixels)")
        if dt == "Number":
            if isinstance(v, bool):
                return 1 if v else 0
            if not isinstance(v, (int, float)):
                raise OpError("INVALID_ARGS", f"{iid} is a Number; got {type(v).__name__}",
                              hint="ComboID inputs take strings; numeric Combo/MultiButton inputs take the 0-based index.")
            return v
        if dt in ("Image", "Mask", "DataType3D", "MtlGraph3D", "Particles"):
            raise OpError("INVALID_ARGS", f"{iid} is a {dt} port; use input.connect")
        if dt == "Gradient":
            raise OpError("INVALID_ARGS", f"{iid} is a Gradient; set it via setting.paste (Gradient {{ Colors = {{...}} }}) or builder ops",
                          hint="The Python bridge cannot construct Gradient values.")
        return v

    def set_input(self, comp, tool, iid, v, frame=None):
        """Validated SetInput + readback. Returns the readback value."""
        reg = tool.GetAttrs()["TOOLS_RegID"]
        tsv = self.tsv()
        if reg in tsv.tools and not tsv.known_input(reg, iid) and iid not in self.inputs(tool):
            raise OpError("NOT_FOUND", tsv.check_input(reg, iid))
        err = tsv.check_value(reg, iid, v) if not (isinstance(v, dict) and "px" in v) else None
        if err:
            raise OpError("INVALID_ARGS", err)
        inp = self.inp(tool, iid)
        if inp.GetExpression():
            raise OpError("INVALID_ARGS", f"{tool.GetAttrs()['TOOLS_Name']}.{iid} is driven by an expression",
                          hint="expression.clear first (it restores a static value).")
        drv = inp.GetConnectedOutput()
        if drv and frame is None and (inp.GetAttrs() or {}).get("INPS_DataType") not in ("Image", "Mask", "DataType3D"):
            dt_ = drv.GetTool()
            da = dt_.GetAttrs() if dt_ else {"TOOLS_RegID": "group", "TOOLS_Name": "<group output>"}
            raise OpError("INVALID_ARGS", f"{tool.GetAttrs()['TOOLS_Name']}.{iid} is animated/driven by {da['TOOLS_RegID']} '{da['TOOLS_Name']}'",
                          hint="Pass frame to set a key at that frame (keyframe.add), or keyframe.clear / modifier.remove for a static value.")
        fv = self.to_fusion(comp, tool, iid, v)
        if frame is None:
            tool.SetInput(iid, fv)
        else:
            tool.SetInput(iid, fv, frame)
        got = tool.GetInput(iid, frame if frame is not None else comp.CurrentTime)
        if isinstance(fv, dict) and not self._same(got, fv):  # Point encoding fallback (bridge variance)
            alt = [fv[1], fv[2]]
            tool.SetInput(iid, alt) if frame is None else tool.SetInput(iid, alt, frame)
            got = tool.GetInput(iid, frame if frame is not None else comp.CurrentTime)
        return jv(got)

    @staticmethod
    def _same(got, want, tol=1e-4):
        g = jv(got)
        w = jv(want)
        if isinstance(w, list) and isinstance(g, list):
            return all(abs(float(a) - float(b)) <= tol for a, b in zip(g, w))
        if isinstance(w, (int, float)) and isinstance(g, (int, float)):
            return abs(g - w) <= tol
        return g == w

    # -- deferred Lua (realities §9: Execute is deferred and silent)
    def lua(self, comp, code, wait=5.0, key=None):
        """Run Lua inside comp via Execute; the chunk must assign `result` (string). Errors come back."""
        key = key or "fc_lua_" + uuid.uuid4().hex[:8]
        comp.SetData(key, "pending")
        comp.Execute(lua_wrap(code, key))
        t0 = time.time()
        state = comp.GetData(key)
        while (state in (None, "pending")) and time.time() - t0 < wait:
            time.sleep(0.1)
            state = comp.GetData(key)
        comp.SetData(key, "")
        if state in (None, "pending"):
            raise OpError("TIMEOUT", "Lua chunk did not report back (comp not current, or still running)",
                          hint="Execute is deferred; make the comp current (comp.set_current) and retry.")
        if state.startswith("ERR:"):
            raise OpError("OPERATION_FAILED", "Lua error: " + state[4:])
        return state[3:]

    def paste(self, comp, text, wait=6.0, names=None):
        """Paste .setting text into the CURRENT Fusion-page comp -> {added: [names], renamed: {name: name, base: new}, missing}
        (the fusion_kit.paste_setting contract). The name check runs inside Fusion in the same Lua chunk and costs one FindTool per
        pasted top-level name (names: known names, else read from the text); the whole-comp before/after diff runs only when a
        pasted name already exists [fusion_v2 F9, sb3]."""
        from .build import setting_syntax_problems, setting_tool_names
        if not self.is_current(comp):
            raise OpError("NOT_CURRENT", "paste only works on the comp showing on the Fusion page (realities §1)",
                          hint="Pass comp as {timeline, item} to auto-make it current, or call comp.set_current first.")
        if self.resolve.GetCurrentPage() != "fusion":  # Paste returns False while another page shows
            self.resolve.OpenPage("fusion")
            time.sleep(1.5)
            self.notes.append("opened the Fusion page for paste")
        lex = setting_syntax_problems(text)  # Fusion would reject it and Paste(nil) would paste the clipboard
        if lex:
            raise OpError("INVALID_ARGS", "setting text would fail Fusion's parser: " + "; ".join(lex[:5]),
                          hint="Escape newlines inside quoted strings as \\n; check with setting.validate.")
        if names is None:
            names = setting_tool_names(text)[0]
        fd, path = tempfile.mkstemp(suffix=".setting")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            try:
                r = self.lua(comp, PASTE_LUA % (lua_list(names), path), wait=wait)
            except OpError as e:
                raise OpError("OPERATION_FAILED", "paste failed: " + e.message, hint="Validate the text with setting.validate.")
        finally:
            os.unlink(path)
        got, ren, miss = (r.split(";") + ["", ""])[:3]
        added = sorted(x for x in got.split(",") if x)
        for n in [n for n in added if re.match(r"^Merge\d*(_\d+)?$", n)]:  # an auto-merge onto the active tool, not in the text
            if not re.search(r"(?m)^\s*" + re.escape(re.sub(r"_\d+$", "", n)) + r"\s*=\s*Merge\s*\{", text):
                t = comp.FindTool(n)
                if t:
                    t.Delete()
                added.remove(n)
        if not added:
            raise OpError("OPERATION_FAILED", "paste reported ok but created nothing (comp not current?)", hint="Validate the text with setting.validate.")
        renamed = {n: n for n in added}
        renamed.update(x.split("=", 1) for x in ren.split(",") if "=" in x)
        missing = [x for x in miss.split(",") if x]
        if missing:
            self.notes.append("paste: %d pasted names not found afterwards (%s)" % (len(missing), missing[:5]))
        return {"added": added, "renamed": renamed, "missing": missing}

    def run_batch(self, comp, children, stop):
        from ..worker import run_batch
        return run_batch(self, comp, children, stop)

    # -- ambient context (appended to every fu_do response)
    def ambient(self):
        ctx = {}
        try:
            r = self.resolve
            ctx["page"] = r.GetCurrentPage()
            p = r.GetProjectManager().GetCurrentProject()
            ctx["project"] = p.GetName() if p else None
            tl = p.GetCurrentTimeline() if p else None
            ctx["timeline"] = tl.GetName() if tl else None
            if tl:
                it = tl.GetCurrentVideoItem()
                ctx["currentItem"] = it.GetName() if it else None
            c = r.Fusion().GetCurrentComp()
            if c is not None:
                a = c.GetAttrs() or {}
                W, H, fps = self.fmt(c)
                act = c.ActiveTool
                ctx["currentComp"] = {"name": a.get("COMPS_Name"), "width": W, "height": H, "fps": fps,
                                      "currentTime": num(c.CurrentTime), "tools": len(c.GetToolList(False) or {}),
                                      "activeTool": act.GetAttrs()["TOOLS_Name"] if act else None,
                                      "globalRange": [num(a.get("COMPN_GlobalStart")), num(a.get("COMPN_GlobalEnd"))]}
            else:
                ctx["currentComp"] = None
        except OpError as e:
            ctx["error"] = e.message
        except Exception as e:  # noqa
            ctx["error"] = str(e)
        if self.notes:
            ctx["notes"] = list(self.notes)
        return ctx
