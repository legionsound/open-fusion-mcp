"""fusion_kit: tested helpers for building Fusion comps in DaVinci Resolve 21.1.

The Fusion counterpart of Higgsfield's ae_* build tools. Every rule encoded here was
observed live (see fusion-reference/references/fusion-realities.md).

Use inside the official Resolve MCP (resolve/project are injected):
    exec(open("/path/to/skills/fusion-motion-design/scripts/fusion_kit.py").read())
    cc = make_current("Testbed", "FusionSkillLab")
Or from an external Python with Resolve scripting enabled:
    import sys; sys.path.append(".../scripts"); from fusion_kit import *
Needs run_script_unsafe when paste_setting/render_frames touch files.
"""
import math
import os
import re
import subprocess
import tempfile
import time

try:
    resolve  # noqa: F821  (injected by the Resolve MCP)
except NameError:  # external use
    import DaVinciResolveScript as _dvr  # type: ignore
    resolve = _dvr.scriptapp("Resolve")


# ---------------------------------------------------------------- scope

def project(expect=None):
    """Current project; assert its name when expect is given (never build in the wrong one)."""
    p = resolve.GetProjectManager().GetCurrentProject()
    if expect and p.GetName() != expect:
        raise RuntimeError(f"current project is {p.GetName()!r}, expected {expect!r}")
    return p


def timeline(p, name, create=False):
    for i in range(p.GetTimelineCount()):
        t = p.GetTimelineByIndex(i + 1)
        if t.GetName() == name:
            return t
    if not create:
        raise RuntimeError(f"timeline {name!r} not found")
    return p.GetMediaPool().CreateEmptyTimeline(name)


def fusion_item(tl, index=0, create=False):
    """The index-th video item on track 1; inserts a Fusion Composition when empty and create=True."""
    items = tl.GetItemListInTrack("video", 1) or []
    if not items and create:
        tl.InsertFusionCompositionIntoTimeline()
        items = tl.GetItemListInTrack("video", 1) or []
    if len(items) <= index:
        raise RuntimeError("no such timeline item")
    return items[index]


def make_current(project_name, timeline_name, item_index=0, create=False, settle=1.5):
    """Show the item's comp on the Fusion page and return it as the CURRENT comp.
    Required for Paste; also the safest target for everything else."""
    p = project(project_name)
    tl = timeline(p, timeline_name, create)
    item = fusion_item(tl, item_index, create)
    p.SetCurrentTimeline(tl)
    tl.SetCurrentTimecode(tl.GetStartTimecode())
    resolve.OpenPage("fusion")
    time.sleep(settle)
    cc = resolve.Fusion().GetCurrentComp()
    if cc is None:
        raise RuntimeError("no current Fusion comp")
    return cc


def names(comp):
    return sorted(t.GetAttrs()["TOOLS_Name"] for t in comp.GetToolList(False).values())


def clean(comp, keep=("MediaOut1",)):
    """Delete every tool (including orphan modifiers) except keep."""
    n = 0
    for t in list(comp.GetToolList(False).values()):
        if t.GetAttrs()["TOOLS_Name"] not in keep:
            t.Delete()
            n += 1
    return n


# ---------------------------------------------------------------- units

def rgb(hexstr):
    """'#0078d4' -> (0.0, 0.4706, 0.8314)"""
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def pt(x_px, y_px, W, H):
    """Pixel position (top-left origin, Y down) -> Fusion normalized point (Y up)."""
    return {1: x_px / W, 2: 1 - y_px / H}


def rect_mask(x, y, w, h, W, H, r=0):
    """Pixel box (top-left) -> RectangleMask inputs. Measured: Width/W, Height/H,
    CornerRadius = r / (min(w,h)/2)."""
    return {"Center": pt(x + w / 2, y + h / 2, W, H), "Width": w / W, "Height": h / H,
            "CornerRadius": min(1.0, 2 * r / min(w, h)) if r else 0.0}


def ellipse_mask(cx, cy, w, h, W, H):
    """EllipseMask: BOTH axes relative to frame width (measured)."""
    return {"Center": pt(cx, cy, W, H), "Width": w / W, "Height": h / W}


def text_size(font_px, W):
    """Text+ Size from a CSS-style font px (measured with Open Sans Bold; check cap height by render)."""
    return 1.70 * font_px / W


# ---------------------------------------------------------------- build

def add(comp, reg_id, name, inputs=None, x=None, y=None):
    """Create a tool without auto-wiring. SetActiveTool(None) first is REQUIRED on the
    Fusion-page comp; Lock suppresses file pickers."""
    comp.SetActiveTool(None)
    comp.Lock()
    try:
        t = comp.AddTool(reg_id, False, -32768 if x is None else x, -32768 if y is None else y, False, False)
    finally:
        comp.Unlock()
    if t is None:
        raise RuntimeError(f"AddTool failed for {reg_id!r} (check the registry TSV)")
    t.SetAttrs({"TOOLS_Name": name})
    got = t.GetAttrs()["TOOLS_Name"]
    if got != name:
        raise RuntimeError(f"name {name!r} became {got!r} (alnum/underscore, no leading digit, unique)")
    for k, v in (inputs or {}).items():
        t.SetInput(k, v)
    return t


def _input(tool, input_id):
    i = next((v for v in tool.GetInputList().values() if v.GetAttrs()["INPS_ID"] == input_id), None)
    if i is None:
        raise KeyError(f"{tool.GetAttrs()['TOOLS_Name']} has no input {input_id!r} (check the inputs TSV)")
    return i


def connect(tool, input_id, src, output=None):
    """ConnectInput that fails loudly (it returns False on loops/type mismatch).
    output: a non-main output ID, e.g. Tracker 'SteadyPosition'."""
    target = src
    if output is not None:
        target = next(o for o in src.GetOutputList().values() if o.GetAttrs()["OUTS_ID"] == output)
    if not tool.ConnectInput(input_id, target):
        raise RuntimeError(f"ConnectInput {tool.GetAttrs()['TOOLS_Name']}.{input_id} failed")
    return True


def source_of(tool, input_id):
    o = _input(tool, input_id).GetConnectedOutput()
    return o.GetTool().GetAttrs()["TOOLS_Name"] if o else None


# ---------------------------------------------------------------- animation

EASE = {  # cubic-bezier control points (x1, y1, x2, y2)
    "house": (0.22, 0.0, 0.25, 1.0),
    "ease": (0.25, 0.1, 0.25, 1.0),
    "in_out": (0.42, 0.0, 0.58, 1.0),
    "out_expo": (0.16, 1.0, 0.3, 1.0),
    "out_back": (0.34, 1.56, 0.64, 1.0),
    "in": (0.42, 0.0, 1.0, 1.0),
    "linear": None,
}


def ease(comp, tool, input_id, keys, curve="house"):
    """Animate a Number input through keys [(frame, value), ...] with one cubic-bezier per
    segment. Handles are RELATIVE {dt, dv} in Python. Avoids the stray seeded key by moving
    comp time to the first key before AddModifier, then asserts the exact key set.
    Point inputs: animate via expressions/XYPath instead (Points take no BezierSpline)."""
    cb = EASE[curve] if isinstance(curve, str) else curve
    comp.CurrentTime = keys[0][0]
    tool.AddModifier(input_id, "BezierSpline")
    sp = _input(tool, input_id).GetConnectedOutput().GetTool()
    kf = {}
    for i, (f, v) in enumerate(keys):
        k = {1: v}
        if cb:
            x1, y1, x2, y2 = cb
            if i + 1 < len(keys):
                D, V = keys[i + 1][0] - f, keys[i + 1][1] - v
                k["RH"] = {1: x1 * D, 2: y1 * V}
            if i > 0:
                D, V = f - keys[i - 1][0], v - keys[i - 1][1]
                k["LH"] = {1: (x2 - 1) * D, 2: (y2 - 1) * V}
        kf[f] = k
    want = sorted(float(f) for f, _ in keys)
    for _ in range(3):
        sp.SetKeyFrames(kf, True)
        got = sorted(float(x) for x in (sp.GetKeyFrames() or {}).keys())
        if got == want:
            return sp
        # SetKeyFrames(dict, True) does not remove a seeded stray key (even twice);
        # single-frame DeleteKeyFrames(f) does, with comp time moved off that frame.
        stale = [f for f in got if f not in want]
        if comp.CurrentTime in stale:
            comp.CurrentTime = want[0]
        for f in stale:
            sp.DeleteKeyFrames(f)
    raise RuntimeError(f"key set mismatch on {input_id}: {got}")


def expr(tool, input_id, expression):
    """SimpleExpression: radians, `time` = frame, no noise(). Returns the value at frame 0.
    expression=None clears it cleanly. Never clear with "": that leaves 0 and silently blocks
    later SetInput on the input."""
    _input(tool, input_id).SetExpression(expression)
    return tool.GetInput(input_id, 0)


_DISMISS = """tell application "System Events"
  if not (exists process "Resolve") then return 0
  tell process "Resolve"
    set n to 0
    repeat with w in (every window)
      try
        if exists (static text "Render completed!" of w) then
          click button "OK" of w
          set n to n + 1
        end if
      end try
    end repeat
    return n
  end tell
end tell"""


def dismiss_render_dialogs():
    """Click OK on Resolve's "Render completed!" modals, and nothing else. Every comp.Render
    raises one; while it is up the scripting API returns None. Returns the count dismissed.
    Needs Accessibility permission for the calling process."""
    r = subprocess.run(["osascript", "-e", _DISMISS], capture_output=True, text=True, timeout=15)
    try:
        return int(r.stdout.strip() or 0)
    except ValueError:
        return 0


# ---------------------------------------------------------------- paste (one-call build)

def setting_syntax_problems(text):
    """Lua lexical traps that Fusion's .setting parser rejects but lenient parsers accept.
    Today: a raw newline inside a quoted string (write \\n). On such text bmd.readfile returns nil,
    and comp:Paste(nil) pastes the SYSTEM CLIPBOARD instead while reporting success."""
    out, i, n, line = [], 0, len(text), 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
        elif text.startswith("--", i):
            m = re.match(r"--\[(=*)\[", text[i:i + 64])
            close = ("]" + m.group(1) + "]") if m else "\n"
            end = text.find(close, i + 2)
            end = n if end < 0 else end
            line += text.count("\n", i, end)
            i = end + (len(close) if m else 0)
        elif c == "[" and re.match(r"\[(=*)\[", text[i:i + 64]):
            m = re.match(r"\[(=*)\[", text[i:i + 64])
            close = "]" + m.group(1) + "]"
            end = text.find(close, i + len(m.group(0)))
            end = n if end < 0 else end
            line += text.count("\n", i, end)
            i = end + len(close)
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    line += text[j + 1:j + 2] == "\n"
                    j += 2
                    continue
                if text[j] == "\n":
                    out.append("line %d: raw newline inside a quoted string (write \\n)" % line)
                    line += 1
                j += 1
            i = j + 1
        else:
            i += 1
    return out


def paste_setting(comp, setting, wait=5.0, debug_key="fk_dbg"):
    """Paste .setting text (or a path to a .setting file) into the CURRENT Fusion-page comp.
    Returns {"added": [...names...], "renamed": {...}} after the deferred Execute lands.
    Colliding names get a _1 suffix; expressions inside the pasted set are rewritten."""
    if os.path.exists(str(setting)):
        path = setting
        with open(path) as f:
            problems = setting_syntax_problems(f.read())
    else:
        problems = setting_syntax_problems(setting)
    if problems:
        raise ValueError("setting text would fail Fusion's parser: " + "; ".join(problems[:5]))
    if not os.path.exists(str(setting)):
        fd, path = tempfile.mkstemp(suffix=".setting")
        with os.fdopen(fd, "w") as f:
            f.write(setting)
    before = set(names(comp))
    comp.SetData(debug_key, "pending")
    comp.Execute(
        "local ok, err = pcall(function() local t = bmd.readfile([[" + path + "]]) "
        "if type(t) ~= 'table' then error('setting failed Fusion parse; nothing pasted') end "
        "comp:SetActiveTool(nil) comp:Paste(t) comp:SetActiveTool(nil) end) "
        f"comp:SetData('{debug_key}', ok and 'ok' or ('ERR ' .. tostring(err)))"
    )
    t0 = time.time()
    while time.time() - t0 < wait:
        state = comp.GetData(debug_key)
        if state and state != "pending":
            break
        time.sleep(0.25)
    time.sleep(0.25)
    state = comp.GetData(debug_key)
    if state != "ok":
        raise RuntimeError(f"paste failed or timed out: {state} (is this the Fusion-page current comp?)")
    added = sorted(set(names(comp)) - before)
    if not added:
        raise RuntimeError("paste reported ok but created nothing (comp not current?)")
    # Paste auto-merges onto the active tool like AddTool does; drop any Merge the text did not define.
    text = open(path).read()
    for n in [n for n in added if re.match(r"^Merge\d*(_\d+)?$", n)]:
        if not re.search(r"(?m)^\s*" + re.escape(re.sub(r"_\d+$", "", n)) + r"\s*=\s*Merge\s*\{", text):
            t = comp.FindTool(n)
            if t:
                t.Delete()
            added.remove(n)
    renamed = {n: n for n in added}
    for n in added:
        m = re.match(r"^(.*)_(\d+)$", n)
        if m and m.group(1) in before:
            renamed[m.group(1)] = n
    return {"added": added, "renamed": renamed}


# ---------------------------------------------------------------- render and inspect

def render_frames(comp, src, frames, out_dir, stem, keep_saver=False):
    """Render specific frames of `src` (tool or name) to PNG via a temporary Saver.
    Returns the file paths that actually exist. Render()'s True alone is not proof."""
    src = comp.FindTool(src) if isinstance(src, str) else src
    os.makedirs(out_dir, exist_ok=True)
    sv = add(comp, "Saver", "FK_Saver_" + re.sub(r"\W", "_", stem))
    connect(sv, "Input", src)
    sv.SetInput("Clip", os.path.join(out_dir, stem + "_.png"))
    paths = []
    try:
        for f in sorted(set(int(x) for x in frames)):
            comp.Render({"Start": f, "End": f, "Wait": True})
            dismiss_render_dialogs()
            p = os.path.join(out_dir, f"{stem}_{f:04d}.png")
            if os.path.exists(p):
                paths.append(p)
    finally:
        if not keep_saver:
            sv.Delete()
    return paths


def audit_motion(comp, specs, f0, f1, W, H, fps, step=0.25):
    """Sample inputs every `step` frames (subframes: short moves hide between whole frames) and report
    timing, travel, easing signature and stagger.
    specs: {"Title_Xf": ["Center", "Size"], "Title_Mrg": ["Blend"]}.
    Signatures (value progress at 25/50/75% of the move): linear .25/.5/.75,
    flat 1/3 ease .156/.5/.844, house .394/.789/.957."""
    rows = []
    for name, inputs in specs.items():
        t = comp.FindTool(name)
        if t is None:
            rows.append({"tool": name, "error": "missing"})
            continue
        for iid in inputs:
            v = [t.GetInput(iid, f0 + k * step) for k in range(int(round((f1 - f0) / step)) + 1)]
            is_pt = isinstance(v[0], dict)
            if is_pt:
                xy = [(q[1] * W, q[2] * H) for q in v]
                d = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(xy, xy[1:])]
            else:
                d = [abs(b - a) for a, b in zip(v, v[1:])]
            mv = [i for i, x in enumerate(d) if x > 1e-6]
            if not mv:
                rows.append({"tool": name, "input": iid, "anim": False})
                continue
            s, e = mv[0], mv[-1] + 1
            sig = None
            if not is_pt and v[e] != v[s]:
                sig = [round((v[s + round((e - s) * q)] - v[s]) / (v[e] - v[s]), 3) for q in (0.25, 0.5, 0.75)]
            rows.append({"tool": name, "input": iid, "anim": True, "start": f0 + s * step, "end": f0 + e * step,
                         "dur_s": round((e - s) * step / fps, 3), "travel": round(sum(d), 3), "sig": sig})
    starts = sorted({r["start"] for r in rows if r.get("anim")})
    stagger_ms = [round((b - a) / fps * 1000) for a, b in zip(starts, starts[1:])]
    flags = []
    for r in rows:
        if not r.get("anim"):
            continue
        if r["dur_s"] > 2.0:
            flags.append(f"{r['tool']}.{r['input']}: slow > 2 s")
        if r["dur_s"] < 0.1:
            flags.append(f"{r['tool']}.{r['input']}: micro < 100 ms")
        if r["sig"] and all(abs(a - b) < 0.02 for a, b in zip(r["sig"], (0.25, 0.5, 0.75))):
            flags.append(f"{r['tool']}.{r['input']}: LINEAR")
    return {"rows": rows, "stagger_ms": stagger_ms, "flags": flags}


def _default_stems():
    """Default instance-name stems (Text, Merge, Rectangle, ...) from the live inputs TSV."""
    root = os.environ.get("FUSION_MCP_SKILLS_ROOT") or os.path.expanduser("~/.agents/skills")
    p = os.path.join(root, "fusion-reference", "data", "fusion-21.1-inputs.tsv")
    stems = {"Merge", "Text", "Background", "Transform", "Rectangle", "Ellipse", "Polygon", "Blur",
             "Glow", "Saver", "Loader", "MediaIn", "Follower", "BezierSpline", "Path", "XYPath"}
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                if line.startswith("@"):
                    stems.add(re.sub(r"\d+$", "", line.split("\t")[1]))
    return stems


_DEFAULT_NAME = re.compile(r"^(" + "|".join(sorted(map(re.escape, _default_stems()), key=len, reverse=True)) + r")\d+$")


def finalize_report(comp, keep_default=("MediaOut1",)):
    """Pre-delivery report (read-only): default-named tools, orphan modifiers, unconsumed
    tools, expressions that evaluate to nil. Fix what it lists, then re-render."""
    tools = list(comp.GetToolList(False).values())
    consumed = set()
    exprs, bad_expr = 0, []
    for t in tools:
        for inp in t.GetInputList().values():
            o = inp.GetConnectedOutput()
            if o:
                consumed.add(o.GetTool().GetAttrs()["TOOLS_Name"])
            try:
                e = inp.GetExpression()
            except Exception:
                e = None
            if e:
                exprs += 1
                if t.GetInput(inp.GetAttrs()["INPS_ID"], 0) is None:
                    bad_expr.append(f"{t.GetAttrs()['TOOLS_Name']}.{inp.GetAttrs()['INPS_ID']}")
    rep = {"tools": len(tools), "expressions": exprs, "nil_expressions": bad_expr,
           "default_names": [], "unconsumed": []}
    for t in tools:
        a = t.GetAttrs()
        n = a["TOOLS_Name"]
        if _DEFAULT_NAME.match(n) and n not in keep_default:
            rep["default_names"].append(n)
        if n not in consumed and a["TOOLS_RegID"] not in ("MediaOut", "Saver") and not n.startswith("CTRL"):
            rep["unconsumed"].append(n)
    return rep


def export_comp(item, path, index=1):
    """Save the item's comp to a .comp file and confirm it exists."""
    ok = item.ExportFusionComp(path, index)
    if not (ok and os.path.exists(path)):
        raise RuntimeError(f"export failed: {path}")
    return path
