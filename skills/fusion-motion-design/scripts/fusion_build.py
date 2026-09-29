"""fusion_build: parametric Fusion builders, one-to-one twins of Higgsfield's After Effects
builder tools (ae_create_title_card, ae_create_lower_third, ae_create_logo_reveal,
ae_create_text_animator, ae_create_transition, ae_build_liquid_glass, ae_apply_effect_template,
ae_apply_expression_template, ae_reveal_floor) plus extras (stat_card, cta_pill, ui_card,
camera_push_3d).

Every builder is PURE: same parameter names as its Higgsfield twin (camelCase kept) plus Fusion
extras W, H, fps, start (frame), prefix, target. It returns (setting_text, info). build(comp, name,
**kw) pastes the text into the CURRENT Fusion-page comp (fusion_kit.paste_setting) and then runs the
few API-side steps a paste cannot do (attach to an existing tool, reroute that tool's consumers,
set expressions on existing inputs). A paste silently DROPS any SourceOp that names a tool outside the
pasted text [live], so every wire to an existing tool is a post step. Pasted splines are renamed
<Host><control label> and a pasted Custom tool also creates <Host>LUTIn1..4 [live]: find splines via
the driven input's GetConnectedOutput(). Units: colors {r,g,b} 0-1 (AE style) or "#hex"; positions
and sizes in comp px (top-left origin, like AE); fontSize px; durations seconds.

Inside the Resolve MCP (run_script_unsafe), after fusion_kit.py:
    K = "/path/to/skills/fusion-motion-design/scripts"
    exec(open(K + "/fusion_kit.py").read()); exec(open(K + "/fusion_build.py").read())
    cc = make_current("Testbed", "FusionSkillLab")
    r = build(cc, "title_card", title="Launch Day", subtitle="September 26")
    r["info"]["output"]  -> the tool to connect downstream (after r["renamed"])
Offline:
    python3 fusion_build.py --components ../components   # default .setting per builder
    python3 fusion_build.py --check [corpus_dir]          # parse + TSV ID audit, all builders
"""
import math
import os
import re

if "paste_setting" not in globals():  # imported/run standalone: load the kit without Resolve
    _here = os.path.dirname(os.path.abspath(__file__))
    _kit = {"resolve": None, "__name__": "fusion_kit"}
    exec(open(os.path.join(_here, "fusion_kit.py")).read(), _kit)
    rgb, pt, rect_mask, ellipse_mask, text_size, EASE, paste_setting, connect = (
        _kit[k] for k in ("rgb", "pt", "rect_mask", "ellipse_mask", "text_size", "EASE", "paste_setting", "connect"))


# ================================================================ .setting emitter

class Src:
    """A wire: Input { SourceOp = op, Source = out }."""
    def __init__(self, op, out="Output"):
        self.op, self.out = op, out


class Expr:
    """A SimpleExpression (radians, `time` = frame, no noise()); v = cached display value."""
    def __init__(self, e, v=None):
        self.e, self.v = e, v


class FuID(str):
    pass


class Styled(str):  # StyledText { Value = ... } (Follower Text)
    pass


class Grad(dict):   # {pos: (r, g, b, a)}
    pass


class Poly(list):   # [(x, y), ...] linear polyline, points relative to the owner's Center
    pass


def _num(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    v = float(v)
    if v == int(v) and abs(v) < 1e12:
        return str(int(v))
    s = ("%.7f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _val(v):
    if isinstance(v, FuID):
        return "FuID { %s }" % _q(v)
    if isinstance(v, Styled):
        return "StyledText { Value = %s }" % _q(v)
    if isinstance(v, str):
        return _q(v)
    if isinstance(v, Grad):
        return "Gradient { Colors = { %s } }" % ", ".join(
            "[%s] = { %s }" % (_num(k), ", ".join(_num(c) for c in c4)) for k, c4 in sorted(v.items()))
    if isinstance(v, Poly):
        return "Polyline { Points = { %s } }" % ", ".join(
            "{ Linear = true, X = %s, Y = %s }" % (_num(x), _num(y)) for x, y in v)
    if isinstance(v, dict):  # fusion_kit point dict {1: x, 2: y}
        v = (v[1], v[2])
    if isinstance(v, (tuple, list)):
        return "{ %s }" % ", ".join(_num(x) for x in v)
    return _num(v)


def _key(k):
    return k if re.fullmatch(r"[A-Za-z_]\w*", k) else '["%s"]' % k


def _inp(v):
    if v is None:
        return "Input { }"
    if isinstance(v, Src):
        return 'Input { SourceOp = "%s", Source = "%s", }' % (v.op, v.out)
    if isinstance(v, Expr):
        cached = "" if v.v is None else "Value = %s, " % _val(v.v)
        return "Input { %sExpression = %s, }" % (cached, _q(v.e))
    return "Input { Value = %s, }" % _val(v)


CURVES = dict(EASE)  # cubic-bezier (x1, y1, x2, y2); None = linear; "step" = hold then jump
CURVES.update(sine_io=(.37, 0, .63, 1), cubic_out=(.33, 1, .68, 1), cubic_io=(.65, 0, .35, 1),
              quart_out=(.25, 1, .5, 1), quint_out=(.22, 1, .36, 1), expo_io=(.87, 0, .13, 1),
              in_70=(.7, 0, .99, 1), io_60=(.6, 0, .4, 1), count_up=(.25, .25, .4, 1),
              settle=(.45, 0, .15, 1), linear=None, step="step")


def _keys(pts, curves="house", flags=None):
    """[(frame, value), ...] + one curve per segment -> KeyFrames with ABSOLUTE handles."""
    segs = curves if isinstance(curves, list) else [curves] * (len(pts) - 1)
    # loop flags go on the two keys bounding the loop only: on a middle key Fusion loops that segment [live]
    ks = [{"f": f, "v": v, "fl": dict(flags or {}) if j in (0, len(pts) - 1) else {}, "lin": []} for j, (f, v) in enumerate(pts)]
    for i, c in enumerate(segs):
        (t0, v0), (t1, v1) = pts[i], pts[i + 1]
        D, V = t1 - t0, v1 - v0
        cb = CURVES[c] if isinstance(c, str) else c
        if cb == "step":
            ks[i]["fl"]["StepIn"] = ks[i + 1]["fl"]["StepIn"] = True
            cb = None
        x1, y1, x2, y2 = cb or (1 / 3, 1 / 3, 2 / 3, 2 / 3)
        ks[i]["RH"] = (t0 + x1 * D, v0 + y1 * V)
        ks[i + 1]["LH"] = (t0 + x2 * D, v0 + y2 * V)
        ks[i]["lin"].append(cb is None)
        ks[i + 1]["lin"].append(cb is None)
    for k in ks:
        if k["lin"] and all(k["lin"]) and "StepIn" not in k["fl"]:
            k["fl"]["Linear"] = True
    return ks


class G:
    """Tool graph for one builder call. Names are prefixed; positions on a 110 x 33 flow grid."""

    def __init__(self, prefix, W, H, fps, start):
        self.p, self.W, self.H, self.fps, self.start = prefix, W, H, fps, start
        self.t, self.order, self.post = {}, [], []
        self.col = self.row = 0

    def n(self, name):
        return self.p + name

    def fr(self, sec):  # key frame for a time in seconds (each key rounded independently)
        return self.start + round(sec * self.fps)

    def xy(self, x, y):  # comp px (top-left) -> normalized point (Y up)
        return (x / self.W, 1 - y / self.H)

    def add(self, name, reg, inputs=None, at=None, mod=False, **extra):
        full = self.p + name
        at = at if at is not None else (self.col, self.row)
        self.col, self.row = at[0] + 1, at[1]
        self.t[full] = dict(reg=reg, inputs=dict(inputs or {}), pos=None if mod else at, extra=extra)
        self.order.append(full)
        return full

    def spline(self, host, iid, pts, curves="house", flags=None, also=()):
        """Key a Number input. Named <host><input> (what Fusion renames pasted splines to)."""
        name = host + iid.replace(".", "")
        self.t[name] = dict(reg="BezierSpline", keys=_keys(pts, curves, flags), host=host)
        self.order.append(name)
        for i in (iid,) + tuple(also):
            self.t[host]["inputs"][i] = Src(name, "Value")
        return name

    def group(self, name, members, inputs, outputs, at=(0, 0)):
        members = list(members) + [s for s in self.order if self.t[s].get("host") in members]
        full = self.p + name
        self.t[full] = dict(reg="GroupOperator", members=members, ginputs=inputs, goutputs=outputs, pos=at)
        self.order = [x for x in self.order if x not in members] + [full]
        return full

    def _emit(self, name, d):
        T, r, out = "\t" * d, self.t[name], []
        if r["reg"] == "BezierSpline":
            out.append("%s%s = BezierSpline {" % (T, name))
            out.append("%s\tSplineColor = { Red = 225, Green = 0, Blue = 225 }, NameSet = true," % T)
            out.append("%s\tKeyFrames = {" % T)
            for k in r["keys"]:
                parts = [_num(k["v"])]
                for h in ("RH", "LH"):
                    if h in k:
                        parts.append("%s = { %s, %s }" % (h, _num(k[h][0]), _num(k[h][1])))
                if k["fl"]:
                    parts.append("Flags = { %s }" % ", ".join("%s = true" % f for f in sorted(k["fl"])))
                out.append("%s\t\t[%s] = { %s }," % (T, _num(k["f"]), ", ".join(parts)))
            out += ["%s\t}," % T, "%s}," % T]
            return out
        if r["reg"] == "GroupOperator":
            out.append("%s%s = GroupOperator {" % (T, name))
            out.append("%s\tInputs = ordered() {" % T)
            for key, op, src, opts in r["ginputs"]:
                o = "".join(", %s = %s" % (k, _val(v)) for k, v in opts.items())
                out.append('%s\t\t%s = InstanceInput { SourceOp = "%s", Source = "%s"%s, },' % (T, key, op, src, o))
            out.append("%s\t}," % T)
            out.append("%s\tOutputs = {" % T)
            for key, (op, src) in r["goutputs"].items():
                out.append('%s\t\t%s = InstanceOutput { SourceOp = "%s", Source = "%s", },' % (T, key, op, src))
            out.append("%s\t}," % T)
            out.append("%s\tViewInfo = GroupInfo { Pos = { %s, %s } }," % (T, _num(r["pos"][0] * 110), _num(r["pos"][1] * 33)))
            out.append("%s\tTools = ordered() {" % T)
            for m in r["members"]:
                out += self._emit(m, d + 2)
            out += ["%s\t}," % T, "%s}," % T]
            return out
        out.append("%s%s = %s {" % (T, name, r["reg"]))
        out.append("%s\tInputs = {" % T)
        for k, v in r["inputs"].items():
            out.append("%s\t\t%s = %s," % (T, _key(k), _inp(v)))
        out.append("%s\t}," % T)
        if r["pos"] is not None:
            info = "PipeRouterInfo" if r["reg"] == "PipeRouter" else "OperatorInfo"
            out.append("%s\tViewInfo = %s { Pos = { %s, %s } }," % (T, info, _num(r["pos"][0] * 110), _num(r["pos"][1] * 33)))
        out.append("%s}," % T)
        return out

    def text(self, active=None):
        lines = ["{", "\tTools = ordered() {"]
        for name in self.order:
            lines += self._emit(name, 2)
        lines += ["\t},", '\tActiveTool = "%s",' % (active or self.order[-1]), "}", ""]
        return "\n".join(lines)


# ================================================================ shared pieces

def _col(c, default):
    c = default if c is None else c
    if isinstance(c, str):
        return rgb(c)
    if isinstance(c, dict):
        return (float(c.get("r", 0)), float(c.get("g", 0)), float(c.get("b", 0)))
    return tuple(float(x) for x in c[:3])


def _bg(c, a=1.0):
    return {"UseFrameFormatSettings": 1, "TopLeftRed": c[0], "TopLeftGreen": c[1], "TopLeftBlue": c[2], "TopLeftAlpha": a}


def _txt(g, text, font, style, px, color, center=None, left=False, spacing=None):
    d = {"UseFrameFormatSettings": 1, "StyledText": text, "Font": font, "Style": style,
         "Size": text_size(px, g.W), "Red1": color[0], "Green1": color[1], "Blue1": color[2]}
    if center is not None:
        d["Center"] = center
    if left:  # corpus lower-third idiom: Center.x = left edge
        d["HorizontalJustificationNew"], d["HorizontalLeftCenterRight"] = 3, -1
    if spacing:
        d["CharacterSpacing"] = spacing
    return d


def _mrg(bg, fg, blend=None, **kw):
    d = {"Background": Src(bg), "Foreground": Src(fg), "PerformDepthMerge": 0}
    if blend is not None:
        d["Blend"] = blend
    d.update(kw)
    return d


def _plate(g, name, color, mask, at, reg="RectangleMask", **bg_extra):
    """Background clipped by a mask (the UI plate primitive). mask = mask inputs dict."""
    m = g.add(name + "M", reg, mask, at=(at[0], at[1] - 1))
    return g.add(name, "Background", dict(_bg(color), EffectMask=Src(m, "Mask"), **bg_extra), at=at)


def _base(g, target, color=None, alpha=1.0):
    """What the builder composites over: an existing tool (post-wired PipeRouter) or a new plate."""
    if target:
        b = g.add("In", "PipeRouter", {"Input": None}, at=(0, 0))
        g.post.append(("connect", b, "Input", target, None))
        return b
    return g.add("BG", "Background", _bg(color or (0, 0, 0), alpha), at=(0, 0))


def _rv(c, n, off=0.0):
    """Controller channel n read `off` frames late (the verified stagger idiom)."""
    return "%s:GetValue('NumberIn%d', time - %s)" % (c, n, _num(off))


def _reveal_ctrl(g, exit_at=None, window=0.70, at=(0, -3)):
    """House reveal controller: NumberIn1 rise/scale (0.70 s, HOUSE), NumberIn2 opacity
    (0.21 -> 0.33 s), NumberIn3 exit (0.4 s, IN_70) when exit_at is given."""
    c = g.add("Ctrl", "Custom", {"NameforNumber1": "Reveal", "NameforNumber2": "Opacity", "NameforNumber3": "Exit"}, at=at)
    g.spline(c, "NumberIn1", [(g.fr(0), 0), (g.fr(window), 1)], "house")
    g.spline(c, "NumberIn2", [(g.fr(0.21), 0), (g.fr(0.33), 1)], "house")
    if exit_at is not None:
        g.spline(c, "NumberIn3", [(g.fr(exit_at), 0), (g.fr(exit_at + 0.4), 1)], "in_70")
    return c


def _house(c, x, y, off, rise, scale=True, has_exit=False):
    """(transform inputs, merge Blend) for one element: rise + 0.95->1 scale + fast fade."""
    P, O = _rv(c, 1, off), _rv(c, 2, off)
    X = "%s.NumberIn3" % c if has_exit else None
    cy = "%s - %s*(1 - %s)" % (_num(y), _num(rise), P) + (" - %s*%s" % (_num(rise), X) if X else "")
    xf = {"Center": Expr("Point(%s, %s)" % (_num(x), cy), (x, y)), "MotionBlur": 1, "Quality": 4, "ShutterAngle": 180}
    if scale:
        xf["Size"] = Expr("0.95 + 0.05*%s" % P + (" - 0.05*%s" % X if X else ""), 1)
    return xf, Expr(O + ("*(1 - %s)" % X if X else ""), 1)


def _finish(g, builder, output, target=None, **info):
    if target:
        g.post.append(("reroute", target, output))
    info.update(builder=builder, output=output, tools=list(g.t), post=g.post)
    return g.text(), info


def _est_w(text, px, bold=True):  # Open Sans advance estimate (em ~= font px)
    return len(text) * px * (0.60 if bold else 0.53)


# ================================================================ Higgsfield twins

def title_card(title="Your Title Here", subtitle=None, color=None, backgroundColor=None, fontFamily="Open Sans",
               fontSize=None, duration=5.0, W=1920, H=1080, fps=24, start=0, prefix="TC_", target=None, style="Bold"):
    """ae_create_title_card: centered title (+ subtitle) with the house reveal, staggered 0.15 s, and an
    IN_70 exit in the last 0.45 s. backgroundColor adds a full-frame solid; target = image to title over."""
    g = G(prefix, W, H, fps, start)
    col = _col(color, (1, 1, 1))
    fs = fontSize or round(0.089 * H)
    fs2 = round(0.42 * fs)
    exit_at = duration - 0.45 if duration >= 1.6 else None
    c = _reveal_ctrl(g, exit_at)
    base = _base(g, None if backgroundColor else target, _col(backgroundColor, (0, 0, 0)), 1.0 if backgroundColor else 0.0)
    total = fs + (0.30 * fs + fs2 if subtitle else 0)
    ty = H / 2 - total / 2 + fs / 2
    rise = 42 / 1080
    t = g.add("Title", "TextPlus", _txt(g, title, fontFamily, style, fs, col), at=(1, 1))
    xf, bl = _house(c, 0.5, 1 - ty / H, 0, rise, True, exit_at is not None)
    xf["Input"] = Src(t)
    g.add("TitleXf", "Transform", xf, at=(2, 1))
    out = g.add("TitleMrg", "Merge", _mrg(base, g.n("TitleXf"), bl), at=(3, 0))
    animated = [c + ".NumberIn1", c + ".NumberIn2", g.n("TitleXf") + ".Center", g.n("TitleXf") + ".Size", out + ".Blend"]
    if subtitle:
        sy = H / 2 + total / 2 - fs2 / 2
        s = g.add("Sub", "TextPlus", _txt(g, subtitle, fontFamily, "Regular", fs2, col, spacing=1.04), at=(1, 2))
        xf, bl = _house(c, 0.5, 1 - sy / H, 0.15 * fps, rise, True, exit_at is not None)
        xf["Input"] = Src(s)
        g.add("SubXf", "Transform", xf, at=(2, 2))
        out = g.add("SubMrg", "Merge", _mrg(out, g.n("SubXf"), bl), at=(4, 0))
        animated += [g.n("SubXf") + ".Center", out + ".Blend"]
    return _finish(g, "title_card", out, target if not backgroundColor else None, controller=c, animated=animated,
                   edit={"title": g.n("Title") + ".StyledText", "subtitle": g.n("Sub") + ".StyledText"})


def lower_third(title="Jane Doe", subtitle="Director of Photography", primaryColor=None, textColor=None,
                fontFamily="Open Sans", fontSize=None, duration=5.0, barWidth=None, x=None, y=None,
                W=1920, H=1080, fps=24, start=0, prefix="LT_", target=None):
    """ae_create_lower_third: primaryColor bar wipes on from the left (HOUSE, left edge pinned), then title
    and subtitle rise+fade in (0.25 / 0.40 s), IN_70 exit at the end. x, y = bar left / bottom px."""
    g = G(prefix, W, H, fps, start)
    pc, tc = _col(primaryColor, (0.0, 0.47, 0.84)), _col(textColor, (1, 1, 1))
    fs = fontSize or round(0.041 * H)
    fs2 = round(0.62 * fs)
    pad = 0.5 * fs
    bw = barWidth or max(_est_w(title, fs), _est_w(subtitle or "", fs2, False)) + 2 * pad
    bh = 1.8 * pad + 1.15 * fs + ((0.25 * fs + 1.2 * fs2) if subtitle else 0)
    L = 0.06 * W if x is None else x
    B = 0.86 * H if y is None else y
    T = B - bh
    exit_at = duration - 0.45 if duration >= 1.6 else None
    c = _reveal_ctrl(g, exit_at)
    X = "%s.NumberIn3" % c if exit_at is not None else "0"
    base = _base(g, target, (0, 0, 0), 0.0)
    P0 = _rv(c, 1, 0)
    bar = _plate(g, "Bar", pc, {
        "Center": Expr("Point(%s + %s*%s, %s)" % (_num(L / W), _num(bw / 2 / W), P0, _num(1 - (T + bh / 2) / H)), g.xy(L + bw / 2, T + bh / 2)),
        "Width": Expr("%s*%s" % (_num(bw / W), P0), bw / W), "Height": bh / H}, at=(1, 1))
    out = g.add("BarMrg", "Merge", _mrg(base, bar, Expr("1 - %s" % X, 1)), at=(2, 0))
    rise = 20 / 1080
    ty = T + 0.9 * pad + 0.575 * fs
    rows = [("Title", title, fs, "Bold", ty, 0.25)]
    if subtitle:
        rows.append(("Sub", subtitle, fs2, "Regular", ty + 0.575 * fs + 0.25 * fs + 0.6 * fs2, 0.40))
    animated = [c + ".NumberIn1", bar + "M.Width", out + ".Blend"]
    for i, (nm, text, px, sty, cy, off) in enumerate(rows):
        t = g.add(nm, "TextPlus", _txt(g, text, fontFamily, sty, px, tc, center=g.xy(L + pad, cy), left=True), at=(1, 2 + i))
        P, O = _rv(c, 1, off * fps), _rv(c, 2, off * fps)
        xf = g.add(nm + "Xf", "Transform", {"Input": Src(t), "Center": Expr("Point(0.5, 0.5 - %s*(1 - %s) - %s*%s)" % (_num(rise), P, _num(rise), X), (0.5, 0.5)),
                                            "MotionBlur": 1, "Quality": 4, "ShutterAngle": 180}, at=(2, 2 + i))
        out = g.add(nm + "Mrg", "Merge", _mrg(out, xf, Expr("%s*(1 - %s)" % (O, X), 1)), at=(3 + i, 0))
        animated += [xf + ".Center", out + ".Blend"]
    return _finish(g, "lower_third", out, target, controller=c, animated=animated,
                   edit={"title": g.n("Title") + ".StyledText", "subtitle": g.n("Sub") + ".StyledText", "bar": bar + ".TopLeftRed/Green/Blue"})


def logo_reveal(text="LOGO", layerName=None, color=None, duration=2.5, style="scale", fontFamily="Open Sans",
                fontSize=None, backgroundColor=None, W=1920, H=1080, fps=24, start=0, prefix="LR_", target=None):
    """ae_create_logo_reveal: style scale (anticipation 0.90->0.92, action ->1.05 with a glow peak, settle
    ->1.00), fade, slide (from the left, QUART_OUT) or spin (180 deg -> 0 with scale 0.4 -> 1).
    target/layerName = an existing logo image: the chain is inserted after it and its consumers rerouted.
    Opacity = BrightnessContrast Gain on RGBA (premultiplied fade), so the reveal works in place."""
    target = target or layerName
    g = G(prefix, W, H, fps, start)
    k = min(1.0, duration / 1.2)  # compress the move for very short durations
    f = lambda s: g.fr(s * k)
    col = _col(color, (1, 1, 1))
    src = None
    if not target:
        base = g.add("BG", "Background", _bg(_col(backgroundColor, (0.043, 0.051, 0.071))), at=(0, 0))
        src = g.add("Logo", "TextPlus", _txt(g, text, fontFamily, "Bold", fontSize or round(0.15 * H), col, spacing=1.06), at=(0, 2))
    first = None
    if style == "scale":
        glow = g.add("Glow", "SoftGlow", {"Threshold": 0.4, "XGlowSize": 12, "Gain": 0}, at=(1, 2))
        g.spline(glow, "Gain", [(f(0.2), 0), (f(0.54), 1.2), (f(0.9), 0.35)], "sine_io")
        first = glow
    xf = g.add("Xf", "Transform", {"MotionBlur": 1, "Quality": 6, "ShutterAngle": 180}, at=(2, 2))
    fade = g.add("Fade", "BrightnessContrast", {"Input": Src(xf), "Alpha": 1}, at=(3, 2))
    first = first or xf
    if first != xf:
        g.t[xf]["inputs"]["Input"] = Src(first)
    if src:
        g.t[first]["inputs"]["Input"] = Src(src)
    else:
        g.post.append(("connect", first, "Input", target, None))
    anim = [fade + ".Gain"]
    if style == "scale":
        g.spline(xf, "Size", [(f(0), .9), (f(.125), .92), (f(.54), 1.05), (f(.79), 1.0)], ["cubic_out", "cubic_out", "sine_io"])
        g.spline(fade, "Gain", [(f(0), 0), (f(0.25), 1)], "linear")
        anim += [xf + ".Size", first + ".Gain"]
    elif style == "fade":
        g.spline(xf, "Size", [(f(0), .97), (f(1.0), 1)], "house")
        g.spline(fade, "Gain", [(f(0), 0), (f(0.6), 1)], "sine_io")
        anim += [xf + ".Size"]
    elif style == "slide":
        c = g.add("Ctrl", "Custom", {"NameforNumber1": "Slide"}, at=(2, 0))
        g.spline(c, "NumberIn1", [(f(0), 0), (f(0.6), 1)], "quart_out")
        g.t[xf]["inputs"]["Center"] = Expr("Point(0.5 - 0.3*(1 - %s.NumberIn1), 0.5)" % c, (0.5, 0.5))
        g.spline(fade, "Gain", [(f(0), 0), (f(0.25), 1)], "linear")
        anim += [xf + ".Center"]
    elif style == "spin":
        g.spline(xf, "Angle", [(f(0), 180), (f(0.8), 0)], "cubic_out")
        g.spline(xf, "Size", [(f(0), 0.4), (f(0.8), 1)], "cubic_out")
        g.spline(fade, "Gain", [(f(0), 0), (f(0.3), 1)], "linear")
        anim += [xf + ".Angle", xf + ".Size"]
    else:
        raise ValueError("style must be scale|fade|slide|spin")
    out = fade if target else g.add("Mrg", "Merge", _mrg(base, fade), at=(4, 0))
    return _finish(g, "logo_reveal", out, target, animated=anim)


def text_animator(layerName=None, animatorType="typewriter", duration=1.5, text="MAKE IT MOVE", fontFamily="Open Sans",
                  fontSize=None, color=None, W=1920, H=1080, fps=24, start=0, prefix="TA_", target=None):
    """ae_create_text_animator on a Text+ (target/layerName; build() reads its text). Follower-based:
    typewriter (1-frame step per char), fadeInChars, scaleInChars (0.70->1.05->1.00 pop), slideInChars
    (rise via Offset1 PolyPath, the shipped Rise Fade idiom); randomize = TextScramble resolving over
    `duration`; wave = looping per-char bob. Characters spread over `duration` (Follower DelayType 2)."""
    target = target or layerName
    g = G(prefix, W, H, fps, start)
    n = max(1, len(text))
    D = duration * fps
    s = g.fr(0)
    if not target:
        base = g.add("BG", "Background", _bg((0.043, 0.051, 0.071)), at=(0, 0))
        host = g.add("Text", "TextPlus", _txt(g, text, fontFamily, "Bold", fontSize or round(0.09 * H), _col(color, (1, 1, 1))), at=(1, 1))
    anim = []
    if animatorType == "randomize":
        mod = g.add("Scr", "TextScramble", {"InputText": text, "AnimateOnTime": 1}, mod=True)
        g.spline(mod, "Randomness", [(s, 1), (g.fr(duration), 0)], "linear")
        out_id, anim = "ScrambledText", [mod + ".Randomness"]
    else:
        mod = g.add("Fol", "StyledTextFollower", {"Text": Styled(text), "Order": 0}, mod=True)
        clip = {"typewriter": 1, "fadeInChars": 0.3 * fps, "scaleInChars": 6, "slideInChars": 0.4 * fps, "wave": 0}[animatorType] \
            if animatorType in ("typewriter", "fadeInChars", "scaleInChars", "slideInChars", "wave") else None
        if clip is None:
            raise ValueError("animatorType must be typewriter|fadeInChars|scaleInChars|slideInChars|randomize|wave")
        spread = max(0.0, (0.5 * D if animatorType == "wave" else D - clip))
        g.t[mod]["inputs"].update({"DelayType": 2 if n > 1 else 0, "Delay": round(spread, 3)})
        fi = g.t[mod]["inputs"]
        if animatorType == "typewriter":
            g.spline(mod, "Opacity1", [(s, 0), (s + 1, 1)], "step")
        elif animatorType == "fadeInChars":
            g.spline(mod, "Opacity1", [(s, 0), (s + clip, 1)], "sine_io")
        elif animatorType == "scaleInChars":
            g.spline(mod, "CharacterSizeX", [(s, .7), (s + 4, 1.05), (s + 6, 1.0)], ["cubic_out", "sine_io"], also=("CharacterSizeY",))
            g.spline(mod, "Opacity1", [(s, 0), (s + 3, 1)], "linear")
        else:  # slideInChars / wave: Offset1 through a PolyPath (Points take no BezierSpline)
            a = 0.5 if animatorType == "slideInChars" else 0.12  # Offset1 unit ~ text Size x frame width [live]
            path = g.add("Path", "PolyPath", {"PolyLine": Poly([(-0.5, -0.5 - a), (-0.5, -0.5 + (a if animatorType == "wave" else 0))])}, mod=True)
            fi["Offset1"] = Src(path, "Position")
            if animatorType == "slideInChars":
                g.spline(path, "Displacement", [(s, 0), (s + clip, 1)], "quart_out")
                g.spline(mod, "Opacity1", [(s, 0), (s + 0.2 * fps, 1)], "linear")
            else:
                q = round(0.3 * fps)
                g.spline(path, "Displacement", [(s, .5), (s + q, 1), (s + 3 * q, 0), (s + 4 * q, .5)], "sine_io", flags={"Loop": True})
            anim.append(path + ".Displacement")
        out_id = "StyledText"
        anim.append(mod + " (per-char keys)")
    if target:
        g.post.append(("connect", target, "StyledText", mod, out_id))
        return _finish(g, "text_animator", target, animated=anim, modifier=mod, note="text now lives in %s" % mod)
    g.t[host]["inputs"]["StyledText"] = Src(mod, out_id)
    out = g.add("Mrg", "Merge", _mrg(base, host), at=(2, 0))
    return _finish(g, "text_animator", out, animated=anim, modifier=mod)


def transition(type="dissolve", color=None, duration=0.75, inputA=None, inputB=None,
               W=1920, H=1080, fps=24, start=0, prefix="TR_", target=None):
    """ae_create_transition between two tools (inputA -> inputB; placeholders when omitted). dissolve
    (cubic in-out), wipe_left / wipe_right (soft mask, exact end frames), zoom (zoom-through: A 1->3,
    B 1/3->1, Mirror edges, motion blur, swap window 0.42-0.58). color (AE default black) = the accent:
    dip-to-color on dissolve, a leading color band on wipes, a flash at the zoom cut."""
    g = G(prefix, W, H, fps, start)
    c = g.add("Ctrl", "Custom", {"NameforNumber1": "Progress"}, at=(0, -2))
    g.spline(c, "NumberIn1", [(g.fr(0), 0), (g.fr(duration), 1)], "expo_io" if type == "zoom" else "cubic_io")
    P = c + ".NumberIn1"
    ends = {}
    for nm, given, cols, label, row in (("A", inputA, ((0.06, 0.09, 0.16), (0.12, 0.23, 0.54)), "A", 0),
                                        ("B", inputB, ((0.96, 0.62, 0.04), (0.71, 0.33, 0.04)), "B", 3)):
        r = g.add(nm + "In", "PipeRouter", {"Input": None}, at=(2, row))
        if given:
            g.post.append(("connect", r, "Input", given, None))
        else:
            bg = g.add(nm + "Plate", "Background", {"UseFrameFormatSettings": 1, "Type": FuID("Gradient"), "Start": (0.5, 1), "End": (0.5, 0),
                                                    "Gradient": Grad({0: cols[0] + (1,), 1: cols[1] + (1,)})}, at=(0, row))
            tx = g.add(nm + "Label", "TextPlus", _txt(g, label, "Open Sans", "Bold", round(0.3 * H), (1, 1, 1)), at=(0, row + 1))
            m = g.add(nm + "Mrg", "Merge", _mrg(bg, tx), at=(1, row))
            g.t[r]["inputs"]["Input"] = Src(m)
        ends[nm] = r
    A, B = ends["A"], ends["B"]
    cc = _col(color, (0, 0, 0)) if color is not None else None
    if type == "dissolve":
        out = g.add("Mix", "Dissolve", {"Background": Src(A), "Foreground": Src(B),
                                        "Mix": Expr("iif(%s < 0.5, 0, 1)" % P if cc else P, 0)}, at=(3, 1))
        if cc:
            dip = g.add("Dip", "Background", _bg(cc), at=(3, 2))
            out = g.add("DipMrg", "Merge", _mrg(out, dip, Expr("1 - abs(2*%s - 1)" % P, 0)), at=(4, 1))
    elif type in ("wipe_left", "wipe_right"):
        s, sg = 0.01, 1 if type == "wipe_left" else -1
        span = 1 + 4 * s
        cx = "0.5 + %d*(1 - %s)*%s" % (sg, P, _num(span))
        m = g.add("WipeM", "RectangleMask", {"Center": Expr("Point(%s, 0.5)" % cx, (0.5 + sg * span, 0.5)), "Width": span, "Height": span, "SoftEdge": s}, at=(3, 2))
        out = g.add("Wipe", "Merge", _mrg(A, B, EffectMask=Src(m, "Mask")), at=(3, 1))
        if cc:
            band = _plate(g, "Band", cc, {"Center": Expr("Point(%s - %d*%s, 0.5)" % (cx, sg, _num(span / 2)), (1.0, 0.5)), "Width": 0.035, "Height": 1.2}, at=(4, 3))
            out = g.add("BandMrg", "Merge", _mrg(out, band, Expr("min(1, 3*sin(pi*%s))" % P, 0)), at=(4, 1))
    elif type == "zoom":
        mb = {"Edges": 3, "MotionBlur": 1, "Quality": 8, "ShutterAngle": 270}
        az = g.add("AZoom", "Transform", dict(mb, Input=Src(A), Size=Expr("1 + 2*%s" % P, 1)), at=(3, 0))
        bz = g.add("BZoom", "Transform", dict(mb, Input=Src(B), Size=Expr("1/(3 - 2*%s)" % P, 1)), at=(3, 3))
        out = g.add("Cross", "Dissolve", {"Background": Src(az), "Foreground": Src(bz),
                                          "Mix": Expr("min(1, max(0, (%s - 0.42)/0.16))" % P, 0)}, at=(4, 1))
        if cc:
            fl = g.add("Flash", "Background", _bg(cc), at=(4, 2))
            out = g.add("FlashMrg", "Merge", _mrg(out, fl, Expr("max(0, 1 - abs(%s - 0.5)*8)" % P, 0)), at=(5, 1))
    else:
        raise ValueError("type must be dissolve|wipe_left|wipe_right|zoom")
    return _finish(g, "transition", out, controller=c, animated=[P], inputs={"A": A + ".Input", "B": B + ".Input"})


def liquid_glass(backgroundLayerName=None, centerX=None, centerY=None, width=None, height=None, roundness=None,
                 frost=40, refraction=-110, magnify=110, saturation=130, tintColor=None, tintOpacity=40,
                 shadow=True, shine=True, animatable=False, name="LG", shapeType="rectangle", refractionMode="radial",
                 rimWidth=None, sourceLayerName=None, hideSource=False, W=1920, H=1080, fps=24, start=0, prefix=None, target=None):
    """ae_build_liquid_glass, PILL mode: the verified liquid-glass.md section 7 rig as one GroupOperator
    with published controls, geometry driven by GlassCtrl expressions. AE units in, Fusion out:
    frost (AE blur) x0.3 -> Blur size (40 -> 12, width-relative), refraction -110 -> 0.06, magnify/
    saturation/tintOpacity in %, center/size/roundness in px. rimWidth = bezel band (px, UHD scale).
    Tint = a masked color plate merged at tintOpacity (AE `Color` layer; white == the verified Lift 0.4).
    SOURCE mode (sourceLayerName) is not built: use liquid-glass.md R10."""
    if sourceLayerName:
        raise NotImplementedError("SOURCE mode: build the pill rig, then follow liquid-glass.md R10 (alpha mode)")
    target = target or backgroundLayerName
    p = prefix if prefix is not None else name + "_"
    g = G(p, W, H, fps, start)
    w = width or 0.35 * W
    h = height or w / 2.2
    r = roundness if roundness is not None else h / 2
    cx, cy = (centerX if centerX is not None else W / 2), (centerY if centerY is not None else H / 2)
    ell = shapeType == "ellipse"
    N = g.n
    GC, GL = N("GlassCtrl"), N("GlassLook")
    S = GC + ".NumberIn3"
    geo_c = lambda dy="": Expr("Point(%s.NumberIn1, %s.NumberIn2%s)" % (GC, GC, dy), (cx / W, 1 - cy / H))

    def geo(extra=None, dy=""):
        d = {"Center": geo_c(dy), "Width": Expr("%s.NumberIn4*%s" % (GC, S), w / W)}
        if ell:  # EllipseMask: both axes width-relative
            d["Height"] = Expr("%s.NumberIn5*%s*%s" % (GC, S, _num(H / W)), h / W)
        else:
            d["Height"] = Expr("%s.NumberIn5*%s" % (GC, S), h / H)
            d["CornerRadius"] = Expr("%s.NumberIn6" % GC, min(1.0, 2 * r / min(w, h)))
        d.update(extra or {})
        return d
    mreg = "EllipseMask" if ell else "RectangleMask"
    bezel = 35 if rimWidth is None else rimWidth
    ctrl = {"NumberIn1": cx / W, "NumberIn2": 1 - cy / H, "NumberIn3": 1, "NumberIn4": w / W, "NumberIn5": h / H,
            "NumberIn6": min(1.0, 2 * r / min(w, h)), "NumberIn7": bezel, "NumberIn8": -refraction * 0.06 / 110}
    for i, lab in enumerate(("Center X", "Center Y", "Scale", "Width (w/W)", "Height (h/H)", "Roundness", "Bezel px", "Refraction"), 1):
        ctrl["NameforNumber%d" % i] = lab
    g.add("GlassCtrl", "Custom", ctrl, at=(0, -6))
    look = {"NumberIn%d" % i: v for i, v in enumerate((154, 0.0156, 0.00156, 0.0139, 0.0208, 0.0039, 0.00078, 1), 1)}
    for i, lab in enumerate(("Rim Angle", "Rim Arc", "Rim Thickness", "Shadow Drop", "Shadow Soft", "Edge Soft", "Edge Choke", "Lens k"), 1):
        look["NameforNumber%d" % i] = lab
    g.add("GlassLook", "Custom", look, at=(1, -6))
    g.add("GlassIn", "PipeRouter", {"Input": None}, at=(0, 0))
    g.add("PillMask", mreg, geo(), at=(9, -3))
    g.add("ShadowMask", mreg, geo({"SoftEdge": Expr("%s.NumberIn5*%s" % (GL, S), 0.0208)}, " - %s.NumberIn4*%s" % (GL, S)), at=(1, -3))
    g.add("EdgeDarkOuter", mreg, geo({"BorderWidth": 0.001, "SoftEdge": Expr("%s.NumberIn6*%s" % (GL, S), 0.0039)}), at=(11, -4))
    g.add("EdgeDarkHole", mreg, geo({"PaintMode": FuID("Subtract"), "BorderWidth": Expr("-%s.NumberIn7*%s" % (GL, S), -0.00078),
                                     "EffectMask": Src(N("EdgeDarkOuter"), "Mask")}), at=(11, -3))
    aspect = 'comp:GetPrefs("Comp.FrameFormat.Width")/comp:GetPrefs("Comp.FrameFormat.Height")'
    g.add("RimGradient", "Background", {"UseFrameFormatSettings": 1, "Type": FuID("Gradient"), "GradientType": FuID("Reflect"),
                                         "Start": Expr("Point(%s.NumberIn1, %s.NumberIn2)" % (GC, GC), (0.5, 0.5)),
                                         "End": Expr("Point(%s.NumberIn1 + %s.NumberIn2*%s*cos((%s.NumberIn1-90)*pi/180), %s.NumberIn2 + %s.NumberIn2*%s*sin((%s.NumberIn1-90)*pi/180)*%s)"
                                                     % (GC, GL, S, GL, GC, GL, S, GL, aspect), (0.5068, 0.5249)),
                                         "Gradient": Grad({0: (0, 0, 0, 1), 1: (1, 1, 1, 1)})}, at=(12, -7))
    g.add("RimArc", "BitmapMask", {"Image": Src(N("RimGradient")), "Channel": FuID("Luminance"), "Invert": 1}, at=(12, -6))
    g.add("RimOuter", mreg, geo({"SoftEdge": 0.0003, "PaintMode": FuID("Multiply"), "EffectMask": Src(N("RimArc"), "Mask")}), at=(12, -5))
    g.add("RimHole", mreg, geo({"PaintMode": FuID("Subtract"), "BorderWidth": Expr("-%s.NumberIn3*%s" % (GL, S), -0.00156),
                                "EffectMask": Src(N("RimOuter"), "Mask")}), at=(12, -4))
    g.add("ShadowDarken", "BrightnessContrast", {"Gain": 0.7 if shadow else 1.0, "Input": Src(N("GlassIn")), "EffectMask": Src(N("ShadowMask"), "Mask")}, at=(1, 0))
    g.add("GlassMagnify", "Transform", {"Center": Expr("Point(%s.NumberIn1, %s.NumberIn2)" % (GC, GC), (0.5, 0.5)),
                                        "Pivot": Expr("Point(%s.NumberIn1, %s.NumberIn2)" % (GC, GC), (0.5, 0.5)),
                                        "Size": magnify / 100.0, "Input": Src(N("ShadowDarken"))}, at=(2, 0))
    g.add("GlassLens", "Dent", {"Type": 5, "Center": Expr("Point(%s.NumberIn1, %s.NumberIn2)" % (GC, GC), (0.5, 0.5)),
                                "Size": Expr("%s.NumberIn8*%s.NumberIn4*%s" % (GL, GC, S), w / W), "Strength": 0.3, "Input": Src(N("GlassMagnify"))}, at=(3, 0))
    g.add("BodyHeight", "Blur", {"XBlurSize": 25, "Input": Src(N("GlassLens"))}, at=(3, 2))
    g.add("BodyNormal", "CreateBumpMap", {"HeightScale": 3, "Input": Src(N("BodyHeight"))}, at=(4, 2))
    g.add("BodyCenter", "BrightnessContrast", {"Brightness": -0.5, "Input": Src(N("BodyNormal"))}, at=(5, 2))
    g.add("BodyRefract", "Displace", {"Type": 1, "XRefraction": 0.006, "YRefraction": Expr("XRefraction", 0.006), "LightPower": 0.5, "LightAngle": 135,
                                      "Input": Src(N("GlassLens")), "Foreground": Src(N("BodyCenter"))}, at=(4, 0))
    g.add("BezelSrc", "Background", dict(_bg((1, 1, 1)), EffectMask=Src(N("PillMask"), "Mask")), at=(3, 4))
    g.add("BezelHeight", "Blur", {"XBlurSize": Expr("%s.NumberIn7*%s" % (GC, S), bezel), "Input": Src(N("BezelSrc"))}, at=(4, 4))
    g.add("BezelNormal", "CreateBumpMap", {"WrapMode": FuID("Clamp"), "HeightScale": Expr("0.85*%s.NumberIn7*%s" % (GC, S), 0.85 * bezel), "Input": Src(N("BezelHeight"))}, at=(5, 4))
    g.add("BezelCenter", "BrightnessContrast", {"Brightness": -0.5, "Input": Src(N("BezelNormal"))}, at=(6, 4))
    g.add("RimRefract", "Displace", {"Type": 1, "XRefraction": 0 if refractionMode == "vertical" else Expr("%s.NumberIn8" % GC, ctrl["NumberIn8"]),
                                     "YRefraction": Expr("%s.NumberIn8" % GC, ctrl["NumberIn8"]),
                                     "Input": Src(N("BodyRefract")), "Foreground": Src(N("BezelCenter"))}, at=(5, 0))
    g.add("GlassFrost", "Blur", {"Filter": FuID("Fast Gaussian"), "XBlurSize": round(frost * 0.3, 3), "Input": Src(N("RimRefract"))}, at=(6, 0))
    g.add("GlassSat", "BrightnessContrast", {"Saturation": saturation / 100.0, "Input": Src(N("GlassFrost"))}, at=(7, 0))
    g.add("GlassGrain", "FilmGrain", {"MasterStrength": 0.03, "MasterXSize": 0.8, "LogProcessing": 0, "Input": Src(N("GlassSat"))}, at=(8, 0))
    g.add("GlassComp", "Merge", _mrg(N("ShadowDarken"), N("GlassGrain"), EffectMask=Src(N("PillMask"), "Mask")), at=(9, 1))
    g.add("GlassTintPlate", "Background", dict(_bg(_col(tintColor, (1, 1, 1))), EffectMask=Src(N("PillMask"), "Mask")), at=(10, 2))
    g.add("GlassTint", "Merge", _mrg(N("GlassComp"), N("GlassTintPlate"), tintOpacity / 100.0), at=(10, 1))
    g.add("EdgeDarken", "BrightnessContrast", {"Gain": 0.92, "Input": Src(N("GlassTint")), "EffectMask": Src(N("EdgeDarkHole"), "Mask")}, at=(11, 1))
    g.add("RimLight", "BrightnessContrast", {"Brightness": 0.6 if shine else 0.0, "Input": Src(N("EdgeDarken")), "EffectMask": Src(N("RimHole"), "Mask")}, at=(12, 1))
    g.add("RimBloom", "SoftGlow", {"Threshold": 0.6, "Gain": 1 if shine else 0, "XGlowSize": 8, "Input": Src(N("RimLight")), "GlowMask": Src(N("RimHole"), "Mask")}, at=(13, 1))
    g.add("GlassFade", "Merge", _mrg(N("GlassIn"), N("RimBloom"), 1), at=(14, 1))
    members = list(g.order)
    anim = []
    if animatable:
        g.spline(GC, "NumberIn3", [(g.fr(0), 0.9), (g.fr(0.7), 1)], "house")
        g.spline(N("GlassFade"), "Blend", [(g.fr(0.21), 0), (g.fr(0.33), 1)], "house")
        anim = [GC + ".NumberIn3", N("GlassFade") + ".Blend"]
    pub = [("MainInput1", N("GlassIn"), "Input", {})]
    for key, op, src, lab, extra in (
            ("CenterX", GC, "NumberIn1", "Center X", {}), ("CenterY", GC, "NumberIn2", "Center Y", {}),
            ("Scale", GC, "NumberIn3", "Scale", {"MinScale": 0.5, "MaxScale": 1.5}),
            ("PanelWidth", GC, "NumberIn4", "Width (w/W)", {}), ("PanelHeight", GC, "NumberIn5", "Height (h/H)", {}),
            ("Roundness", GC, "NumberIn6", "Roundness", {"MinScale": 0, "MaxScale": 1}),
            ("Bezel", GC, "NumberIn7", "Bezel (px)", {"MinScale": 0, "MaxScale": 100}),
            ("Refraction", GC, "NumberIn8", "Refraction", {"MinScale": -0.1, "MaxScale": 0.1}),
            ("Magnify", N("GlassMagnify"), "Size", "Magnify", {"MinScale": 1, "MaxScale": 1.2}),
            ("Lens", N("GlassLens"), "Strength", "Lens", {"MinScale": 0, "MaxScale": 1}),
            ("BodyTexture", N("BodyRefract"), "XRefraction", "Body Texture", {"MinScale": 0, "MaxScale": 0.02}),
            ("Frost", N("GlassFrost"), "XBlurSize", "Frost", {"MinScale": 0, "MaxScale": 40}),
            ("Saturation", N("GlassSat"), "Saturation", "Backdrop Saturation", {"MinScale": 1, "MaxScale": 2}),
            ("Tint", N("GlassTint"), "Blend", "Tint Opacity", {"MinScale": 0, "MaxScale": 1}),
            ("EdgeDark", N("EdgeDarken"), "Gain", "Edge Darkness (gain)", {"MinScale": 0.8, "MaxScale": 1}),
            ("RimIntensity", N("RimLight"), "Brightness", "Rim Intensity", {"MinScale": 0, "MaxScale": 1.5}),
            ("RimAngle", GL, "NumberIn1", "Rim Angle", {"MinScale": 90, "MaxScale": 180}),
            ("RimArc", GL, "NumberIn2", "Rim Arc", {"MinScale": 0, "MaxScale": 0.05}),
            ("ShadowGain", N("ShadowDarken"), "Gain", "Shadow (gain)", {"MinScale": 0.5, "MaxScale": 1}),
            ("ShadowDrop", GL, "NumberIn4", "Shadow Drop", {"MinScale": 0, "MaxScale": 0.05}),
            ("Grain", N("GlassGrain"), "MasterStrength", "Frost Grain", {"MinScale": 0, "MaxScale": 0.1}),
            ("Opacity", N("GlassFade"), "Blend", "Glass Opacity", {})):
        pub.append((key, op, src, dict(Name=lab, **extra)))
    grp = g.group("Glass", members, pub, {"MainOutput1": (N("GlassFade"), "Output")}, at=(2, 0))
    if target:
        g.post.append(("connect", grp, "MainInput1", target, None))
    else:  # demo backdrop, wired straight into the group's router
        bd = g.add("Backdrop", "Background", {"UseFrameFormatSettings": 1, "Type": FuID("Corner"),
                                              "TopLeftRed": 0.95, "TopLeftGreen": 0.35, "TopLeftBlue": 0.2,
                                              "TopRightRed": 0.2, "TopRightGreen": 0.5, "TopRightBlue": 0.95,
                                              "BottomLeftRed": 0.1, "BottomLeftGreen": 0.8, "BottomLeftBlue": 0.6,
                                              "BottomRightRed": 0.9, "BottomRightGreen": 0.8, "BottomRightBlue": 0.1}, at=(0, 2))
        bt = g.add("BackdropTxt", "TextPlus", _txt(g, "LIQUID GLASS", "Open Sans", "Bold", round(0.13 * H), (1, 1, 1)), at=(0, 3))
        bm = g.add("BackdropMrg", "Merge", _mrg(bd, bt), at=(1, 2))
        g.t[N("GlassIn")]["inputs"]["Input"] = Src(bm)
        g.order.remove(bd), g.order.remove(bt), g.order.remove(bm)
        g.order[0:0] = [bd, bt, bm]
    return _finish(g, "liquid_glass", grp, target, controller=GC, animated=anim, published=[k for k, *_ in pub],
                   note="connect downstream from %s (group MainOutput1)" % grp)


def effect_template(template="cinematicLook", layerName=None, intensity=1.0, color=None,
                    W=1920, H=1080, fps=24, start=0, prefix="FX_", target=None):
    """ae_apply_effect_template: a curated stack appended after target (its consumers are rerouted to the
    stack's output). cinematicLook = contrast/saturation grade + teal-shadow/warm-highlight ColorGain +
    soft vignette + light grain; glow = SoftGlow; filmGrain = FilmGrain; neonGlow = tight + wide Glow
    color: highlights keyed (BrightnessContrast Low 0.55 + ClipBlack), tinted (ColorGain), blurred tight + wide and
    Screen-merged over the source (the Glow tool's color scales tint the whole frame [live], so not used);
    vibrance = BrightnessContrast Saturation (Fusion has no vibrance op)."""
    target = target or layerName
    g = G(prefix, W, H, fps, start)
    i = float(intensity)
    if not target:  # demo source: gradient, bright text, a hot disc
        bg = g.add("DemoBG", "Background", {"UseFrameFormatSettings": 1, "Type": FuID("Gradient"), "Start": (0.5, 1), "End": (0.5, 0),
                                            "Gradient": Grad({0: (0.16, 0.2, 0.32, 1), 1: (0.55, 0.36, 0.3, 1)})}, at=(0, 0))
        tx = g.add("DemoTxt", "TextPlus", _txt(g, "EFFECT", "Open Sans", "Bold", round(0.16 * H), (1, 1, 1)), at=(0, 1))
        disc = _plate(g, "DemoDisc", (1, 0.85, 0.5), ellipse_mask(0.8 * W, 0.28 * H, 0.1 * W, 0.1 * W, W, H), at=(0, 3), reg="EllipseMask")
        m1 = g.add("DemoMrg1", "Merge", _mrg(bg, tx), at=(1, 0))
        src = g.add("DemoMrg2", "Merge", _mrg(m1, disc), at=(2, 0))
    chain, feeds = [], []  # feeds: extra (tool, input) pairs that also read the source
    if template == "cinematicLook":
        chain.append(g.add("Grade", "BrightnessContrast", {"Contrast": 0.12 * i, "Saturation": 1 - 0.12 * i, "Gamma": 1 - 0.04 * i}, at=(3, 0)))
        chain.append(g.add("Tone", "ColorGain", {"GainRed": 1 + 0.04 * i, "GainBlue": 1 - 0.04 * i, "LiftGreen": 0.008 * i, "LiftBlue": 0.02 * i}, at=(4, 0)))
        vm = g.add("VigM", "EllipseMask", {"Width": 1.3, "Height": 1.3 * H / W, "SoftEdge": 0.3, "Invert": 1}, at=(5, 1))
        vig = g.add("Vig", "Background", dict(_bg((0, 0, 0)), EffectMask=Src(vm, "Mask")), at=(5, 2))
        chain.append(g.add("VigMrg", "Merge", {"Foreground": Src(vig), "PerformDepthMerge": 0, "Blend": 0.5 * i}, at=(5, 0)))
        chain.append(g.add("Grain", "FilmGrain", {"MasterStrength": 0.03 * i, "LogProcessing": 0}, at=(6, 0)))
    elif template == "glow":
        chain.append(g.add("Glow", "SoftGlow", {"Threshold": 0.55, "Gain": 1.2 * i, "XGlowSize": 14}, at=(3, 0)))
    elif template == "filmGrain":
        chain.append(g.add("Grain", "FilmGrain", {"MasterStrength": 0.08 * i, "MasterXSize": 1.1, "Monochrome": 1, "LogProcessing": 0}, at=(3, 0)))
    elif template == "neonGlow":
        nc = _col(color, (0.2, 0.9, 1.0))
        # float levels: Low pushes darker pixels NEGATIVE and Screen then subtracts them [live]: ClipBlack
        key = g.add("NeonKey", "BrightnessContrast", {"Low": 0.55, "High": 1.0, "ClipBlack": 1}, at=(3, 1))
        tint = g.add("NeonTint", "ColorGain", {"Input": Src(key), "GainRed": nc[0], "GainGreen": nc[1], "GainBlue": nc[2]}, at=(4, 1))
        bt = g.add("NeonTightBlur", "Blur", {"Input": Src(tint), "XBlurSize": 4}, at=(5, 1))
        bw = g.add("NeonWideBlur", "Blur", {"Input": Src(tint), "XBlurSize": 24}, at=(5, 2))
        chain.append(g.add("NeonTight", "Merge", {"Foreground": Src(bt), "ApplyMode": FuID("Screen"), "PerformDepthMerge": 0, "Blend": min(1.0, 1.0 * i)}, at=(5, 0)))
        chain.append(g.add("NeonWide", "Merge", {"Foreground": Src(bw), "ApplyMode": FuID("Screen"), "PerformDepthMerge": 0, "Blend": min(1.0, 0.9 * i)}, at=(6, 0)))
        feeds.append((key, "Input"))
    elif template == "vibrance":
        chain.append(g.add("Vibrance", "BrightnessContrast", {"Saturation": 1 + 0.3 * i, "Contrast": 0.04 * i}, at=(3, 0)))
    else:
        raise ValueError("template must be cinematicLook|glow|filmGrain|neonGlow|vibrance")
    for a, b in zip(chain, chain[1:]):
        g.t[b]["inputs"]["Background" if g.t[b]["reg"] == "Merge" else "Input"] = Src(a)
    first_in = "Background" if g.t[chain[0]]["reg"] == "Merge" else "Input"
    for tool, iid in [(chain[0], first_in)] + feeds:
        if target:
            g.post.append(("connect", tool, iid, target, None))
        else:
            g.t[tool]["inputs"][iid] = Src(src)
    return _finish(g, "effect_template", chain[-1], target, stack=chain)


_EXPR_MAP = {  # AE propertyName -> input ID per target type
    "Transform": {"Position": "Center", "Scale": "Size", "Rotation": "Angle", "Anchor Point": "Pivot"},
    "Merge": {"Position": "Center", "Scale": "Size", "Rotation": "Angle", "Opacity": "Blend"},
    "TextPlus": {"Position": "Center", "Scale": "Size", "Rotation": "AngleZ", "Opacity": "Opacity1"},
}
_EXPR_AMP = {"Position": 120, "Scale": 20, "Rotation": 30, "Opacity": 60, "Anchor Point": 120}


def expression_template(template="wiggle", propertyName="Position", layerName=None, params=None, targetType=None, base=None, baseCenter=None,
                        W=1920, H=1080, fps=24, start=0, prefix="EX_", target=None):
    """ae_apply_expression_template as SimpleExpressions (radians, `time` = frame, no noise()). params:
    frequency (Hz), amplitude (px | % | deg | %), period (s), decay, fadeIn (s), rate (units/s),
    overshoot (%), settle (s), gain. wiggle = sum of incommensurate sines; loopCycle/Pingpong/Offset =
    controller keys with spline Loop / Pingpong / LoopRel flags; loopContinue = extrapolation past the
    last key; bounce = decaying |cos|; inertia = velocity-matched decaying sine after a keyed move;
    overshoot = damped spring. Target: expression set on the target's own input (Merge/Transform/Text+);
    no target: a demo card over a background."""
    target = target or layerName
    g = G(prefix, W, H, fps, start)
    pm = dict(params or {})
    F, K0 = _num(fps), g.fr(0)
    A = float(pm.get("amplitude", 360 if template in ("loopOffset", "loopContinue") and propertyName == "Rotation" else _EXPR_AMP[propertyName]))
    f = float(pm.get("frequency", 2.0))
    if not target:
        bg = g.add("BG", "Background", _bg((0.043, 0.051, 0.071)), at=(0, 0))
        card = _plate(g, "Card", (0.37, 0.42, 0.82), rect_mask(W / 2 - 0.1 * W, H / 2 - 0.09 * H, 0.2 * W, 0.18 * H, W, H, 0.02 * W), at=(0, 3))
        lab = g.add("Label", "TextPlus", _txt(g, template, "Open Sans", "Bold", round(0.035 * H), (1, 1, 1)), at=(0, 4))
        cm = g.add("CardMrg", "Merge", _mrg(card, lab), at=(1, 3))
        xf = g.add("Xf", "Transform", {"Input": Src(cm), "MotionBlur": 1, "Quality": 4}, at=(2, 3))
        mrg = g.add("Mrg", "Merge", _mrg(bg, xf), at=(3, 0))
        host, ttype = (mrg, "Merge") if propertyName == "Opacity" else (xf, "Transform")
    else:
        host, ttype = target, targetType or "Merge"
    iid = _EXPR_MAP[ttype].get(propertyName)
    if iid is None:
        raise ValueError("%s has no %s (use a Merge, Transform or Text+)" % (ttype, propertyName))
    point = propertyName in ("Position", "Anchor Point")
    if base is None:
        base = (0.5, 0.5) if point else {"Scale": 1.0, "Rotation": 0.0, "Opacity": 1.0}[propertyName]
    if isinstance(base, dict):
        base = (base.get(1, base.get("1")), base.get(2, base.get("2")))

    def sig(k=0):  # wiggle signal in [-1, 1]; k picks an independent set of phases
        m = ((1, 2.37, 0.61, 0, 1.3, 4.1), (1.13, 2.71, 0.47, 2.2, 0.7, 5.3))[k]
        w = "2*pi*%s*time/%s" % (_num(f), F)
        if template == "wiggleSmooth":
            return "(0.75*sin(%s*%s + %s) + 0.25*sin(%s*%s + %s))" % (w, _num(m[0]), _num(m[3]), w, _num(m[2] * 0.87), _num(m[5]))
        return "(0.5*sin(%s*%s + %s) + 0.3*sin(%s*%s + %s) + 0.2*sin(%s*%s + %s))" % (
            w, _num(m[0]), _num(m[3]), w, _num(m[1]), _num(m[4]), w, _num(m[2]), _num(m[5]))

    def apply(u, v=None):  # u, v = normalized signal expressions (v = second axis for points)
        if point:
            bx, by = base
            return "Point(%s + %s*%s, %s + %s*%s)" % (_num(bx), _num(A / W), u, _num(by), _num(A / H), v if v else "0")
        if propertyName == "Scale":
            return "%s*(1 + %s*%s)" % (_num(base), _num(A / 100), u)
        if propertyName == "Rotation":
            return "%s + %s*%s" % (_num(base), _num(A), u)
        return "min(1, max(0, %s - %s*%s))" % (_num(base), _num(A / 100), u)  # Opacity: dips by amplitude %

    c = None
    if template in ("wiggle", "wiggleSmooth", "wiggleFadeIn"):
        env = "" if template != "wiggleFadeIn" else "*min(1, max(0, (time - %s)/(%s*%s)))" % (K0, _num(pm.get("fadeIn", 1.0)), F)
        if propertyName == "Opacity":
            e = apply("(0.5 + 0.5*%s)%s" % (sig(0), env))
        else:
            e = apply("%s%s" % (sig(0), env), "%s%s" % (sig(1), env))
    elif template == "time":
        rate = float(pm.get("rate", {"Position": 200, "Scale": 10, "Rotation": 90, "Opacity": 20, "Anchor Point": 200}[propertyName]))
        u = "(time - %s)/%s*%s" % (K0, F, _num(rate / A))
        e = apply(u, None)
    elif template in ("loopCycle", "loopPingpong", "loopOffset", "loopContinue"):
        P = round(float(pm.get("period", 1.0)) * fps)
        c = g.add("Ctrl", "Custom", {"NameforNumber1": template}, at=(1, -2))
        if template == "loopCycle":
            g.spline(c, "NumberIn1", [(K0, 0), (K0 + P // 2, 1), (K0 + P, 0)], "sine_io", flags={"Loop": True})
        elif template == "loopPingpong":
            g.spline(c, "NumberIn1", [(K0, 0), (K0 + P, 1)], "sine_io", flags={"Loop": True, "Pingpong": True})
        elif template == "loopOffset":
            g.spline(c, "NumberIn1", [(K0, 0), (K0 + P, 1)], "linear", flags={"Loop": True, "LoopRel": True})
        else:
            g.spline(c, "NumberIn1", [(K0, 0), (K0 + P, 1)], "linear")
        p = "%s.NumberIn1" % c
        if template == "loopContinue":  # AE loopOut("continue"): keep the last key's velocity
            K = K0 + P
            p = "iif(time <= %d, %s, 1 + (time - %d)*(%s:GetValue('NumberIn1', %d) - %s:GetValue('NumberIn1', %d)))" % (K, p, K, c, K, c, K - 1)
        e = apply(p, None)
    elif template == "bounce":
        Wb = math.pi * float(pm.get("frequency", 3.0))
        dec = float(pm.get("decay", 4.0))
        u = "iif(time < %d, 1, abs(cos(%s*(time - %d)/%s))*exp(-%s*(time - %d)/%s))" % (K0, _num(Wb), K0, F, _num(dec), K0, F)
        e = apply(u, u) if point else apply(u)
        if point:  # drop from above: X stays
            e = "Point(%s, %s + %s*%s)" % (_num(base[0]), _num(base[1]), _num(A / H), u)
    elif template == "inertia":
        D = round(float(pm.get("duration", 0.5)) * fps)
        hz, dec, gain = float(pm.get("frequency", 2.6)), float(pm.get("decay", 5.5)), float(pm.get("gain", 1.0))
        c = g.add("Ctrl", "Custom", {"NameforNumber1": "Move"}, at=(1, -2))
        g.spline(c, "NumberIn1", [(K0, 0), (K0 + D, 1)], "linear")
        K = K0 + D
        v = "(%s:GetValue('NumberIn1', %d) - %s:GetValue('NumberIn1', %d))*%s" % (c, K, c, K - 1, F)
        u = "iif(time <= %d, %s.NumberIn1, 1 + %s*%s*sin(2*pi*%s*(time - %d)/%s)/(2*pi*%s*exp(%s*(time - %d)/%s)))" % (
            K, c, _num(gain), v, _num(hz), K, F, _num(hz), _num(dec), K, F)
        e = apply("(%s - 1)" % u, None)  # arrive at base: offset runs -1 -> 0 (+ overshoot)
    elif template == "overshoot":
        os_ = max(0.001, float(pm.get("overshoot", 10)) / 100)
        Z = -math.log(os_) / math.sqrt(math.pi ** 2 + math.log(os_) ** 2)
        Wn = 4 / (Z * float(pm.get("settle", 0.8)))
        Wd = Wn * math.sqrt(1 - Z * Z)
        tt = "(time - %d)/%s" % (K0, F)
        u = "iif(time < %d, -1, -exp(-%s*%s)*(cos(%s*%s) + %s*sin(%s*%s)))" % (
            K0, _num(Z * Wn), tt, _num(Wd), tt, _num(Z * Wn / Wd), _num(Wd), tt)
        e = apply(u, None)
    else:
        raise ValueError("unknown template %r" % template)
    extra = []
    if propertyName == "Anchor Point":  # Pivot alone does not move the image [live]: AE shifts the layer, so
        bc = baseCenter or (0.5, 0.5)    # Center takes the opposite offset (image moves, pivot rides along)
        if isinstance(bc, dict):
            bc = (bc.get(1, bc.get("1")), bc.get(2, bc.get("2")))
        ce = re.sub(r"^Point\(%s \+ (.*), %s \+ (.*)\)$" % (re.escape(_num(base[0])), re.escape(_num(base[1]))),
                    lambda m: "Point(%s - %s, %s - %s)" % (_num(bc[0]), m.group(1), _num(bc[1]), m.group(2)), e)
        extra.append(("Center", ce, bc))
    if target:
        g.post.append(("expr", host, iid, e))
        g.post += [("expr", host, i2, e2) for i2, e2, _ in extra]
        if not g.order:
            return "", dict(builder="expression_template", output=host, tools=[], post=g.post, input=iid, expression=e)
        return _finish(g, "expression_template", host, controller=c, input=iid, expression=e)
    g.t[host]["inputs"][iid] = Expr(e, base)
    for i2, e2, b2 in extra:
        g.t[host]["inputs"][i2] = Expr(e2, b2)
    return _finish(g, "expression_template", mrg, controller=c, animated=["%s.%s" % (host, iid)], input=iid, expression=e)


def reveal_floor(merges=None, rise_px=42, stagger=0.15, W=1920, H=1080, fps=24, start=0, prefix="RF_", target=None):
    """ae_reveal_floor: give un-animated merged elements the house rise + fade (stagger 0.15 s, in chain
    order). API-side: build(comp, "reveal_floor") finds the Merges whose Blend/Center and foreground chain
    carry no animation (skipping full-frame Background plates), pastes one controller and sets
    Merge.Center/Blend expressions. merges = [{"merge": name, "center": (x, y)}]; none = a static demo
    scene with the same expressions baked in (the default component)."""
    g = G(prefix, W, H, fps, start)
    c = _reveal_ctrl(g)
    rise = rise_px / 1080
    exprs = []
    if merges is None:
        out = g.add("BG", "Background", _bg((0.043, 0.051, 0.071)), at=(0, 0))
        for i, (txt, px, y) in enumerate((("Static headline", 0.075, 0.42), ("Supporting line", 0.035, 0.55), ("Call to action", 0.03, 0.66))):
            t = g.add("El%d" % i, "TextPlus", _txt(g, txt, "Open Sans", "Bold" if i != 1 else "Regular", round(px * H), (1, 1, 1), center=(0.5, 1 - y)), at=(i + 1, 1))
            out = g.add("El%dMrg" % i, "Merge", _mrg(out, t), at=(i + 1, 0))
            merges = (merges or []) + [{"merge": out, "center": (0.5, 0.5), "_local": True}]
    for i, m in enumerate(merges):
        off = stagger * fps * i
        cx, cy = m.get("center", (0.5, 0.5))
        ce = "Point(%s, %s - %s*(1 - %s))" % (_num(cx), _num(cy), _num(rise), _rv(c, 1, off))
        be = _rv(c, 2, off)
        if m.get("_local"):
            g.t[m["merge"]]["inputs"].update(Center=Expr(ce, (cx, cy)), Blend=Expr(be, 1))
        else:
            g.post += [("expr", m["merge"], "Center", ce), ("expr", m["merge"], "Blend", be)]
        exprs.append(m["merge"])
    out = merges[-1]["merge"] if merges and merges[-1].get("_local") else c
    return _finish(g, "reveal_floor", out, controller=c, revealed=exprs)


# ================================================================ extras (beyond Higgsfield)

_UI = dict(page="#08090b", surface="#131418", border="#26282e", text="#fafafa", muted="#a1a1aa", accent="#5e6ad2", success="#10b981")


def _card_frame(g, w, h, r, surface, border, t=1, shadow=0.35, at_row=2):
    """Component canvas (transparent) + S1 mask shadow + fill + 1 px inside ring, assembled at frame
    centre (component-local); returns the last merge. The component's Xf places it at (cx, cy)."""
    W, H = g.W, g.H
    L, T = W / 2 - w / 2, H / 2 - h / 2
    canvas = g.add("Canvas", "Background", _bg((0, 0, 0), 0), at=(0, at_row))
    sh = _plate(g, "Shadow", (0, 0, 0), dict(rect_mask(L, T + 10 * W / 1920, w, h, W, H, r), SoftEdge=0.0125), at=(1, at_row + 2))
    out = g.add("ShadowMrg", "Merge", _mrg(canvas, sh, shadow), at=(1, at_row))
    fill = _plate(g, "Fill", surface, rect_mask(L, T, w, h, W, H, r), at=(2, at_row + 2))
    out = g.add("FillMrg", "Merge", _mrg(out, fill), at=(2, at_row))
    ro = g.add("RingOuterM", "RectangleMask", rect_mask(L, T, w, h, W, H, r), at=(3, at_row + 3))
    ri = g.add("RingM", "RectangleMask", dict(rect_mask(L + t, T + t, w - 2 * t, h - 2 * t, W, H, max(0, r - t)),
                                                PaintMode=FuID("Subtract"), EffectMask=Src(ro, "Mask")), at=(3, at_row + 4))
    ring = g.add("Ring", "Background", dict(_bg(border), EffectMask=Src(ri, "Mask")), at=(3, at_row + 2))
    out = g.add("RingMrg", "Merge", _mrg(out, ring), at=(3, at_row))
    return out, L, T


def _place(g, c, comp_out, cx, cy, base, col):
    """Component Xf (house reveal about the component centre) + page merge."""
    xf, bl = _house(c, cx / g.W, 1 - cy / g.H, 0, 42 / 1080)
    xf["Input"] = Src(comp_out)
    x = g.add("Xf", "Transform", xf, at=(col, 1))
    return g.add("Mrg", "Merge", _mrg(base, x, bl), at=(col + 1, 0))


def stat_card(label="REVENUE", value=1234, valuePrefix="$", valueSuffix="", trend="+24.8%", caption="vs last month",
              x=None, y=None, width=None, height=None, radius=None, countDuration=1.5, fontFamily="Open Sans",
              backgroundColor=None, surfaceColor=None, borderColor=None, textColor=None, mutedColor=None, accentColor=None,
              W=1920, H=1080, fps=24, start=0, prefix="SC_", target=None):
    """ui-mastery 5.9 stat card: surface + 1 px ring + S1 shadow, caps label, counting number (Text+
    StyledText expression with thousands separators, controller 0->1 so the 1e6 clamp never bites),
    trend pill (accent 15 % plate) + caption. House reveal on the whole card, count starts at 0.3 s."""
    g = G(prefix, W, H, fps, start)
    s = W / 1920
    w, h, r = (width or 400 * s), (height or 220 * s), (radius if radius is not None else 16 * s)
    cx, cy = (W / 2 if x is None else x), (H / 2 if y is None else y)
    tc, mc, ac = _col(textColor, _UI["text"]), _col(mutedColor, _UI["muted"]), _col(accentColor, _UI["success"])
    c = _reveal_ctrl(g)
    g.spline(c, "NumberIn4", [(g.fr(0.3), 0), (g.fr(0.3 + countDuration), 1)], "count_up")
    g.t[c]["inputs"]["NameforNumber4"] = "Count"
    base = _base(g, target, _col(backgroundColor, _UI["page"]))
    out, L, T = _card_frame(g, w, h, r, _col(surfaceColor, _UI["surface"]), _col(borderColor, _UI["border"]))
    pad = 28 * s
    lab = g.add("Label", "TextPlus", _txt(g, label, fontFamily, "Bold", 14 * s, mc, center=g.xy(L + pad, T + pad + 8 * s), left=True, spacing=1.08), at=(4, 4))
    out = g.add("LabelMrg", "Merge", _mrg(out, lab), at=(4, 2))
    v = "%s:GetValue('NumberIn4', time)*%s" % (c, _num(value))
    cnt = (":local s=string.format('%%d', math.floor(%s + 0.5)); local l,n,r=string.match(s,'^(.-%%d)(%%d*)(.*)'); "
           "return Text(%s..l..(n:reverse():gsub('%%d%%d%%d','%%0,'):reverse())..r..%s)") % (v, _q(valuePrefix).replace('"', "'"), _q(valueSuffix).replace('"', "'"))
    num = g.add("Number", "TextPlus", dict(_txt(g, "0", fontFamily, "Bold", 56 * s, tc, center=g.xy(L + pad, T + pad + 64 * s), left=True),
                                           StyledText=Expr(cnt, valuePrefix + "0")), at=(5, 4))
    out = g.add("NumberMrg", "Merge", _mrg(out, num), at=(5, 2))
    ph, pw = 30 * s, _est_w(trend, 14 * s) + 24 * s
    py = T + h - pad - ph / 2
    pill = _plate(g, "Pill", ac, rect_mask(L + pad, py - ph / 2, pw, ph, W, H, ph / 2), at=(6, 4))
    out = g.add("PillMrg", "Merge", _mrg(out, pill, 0.15), at=(6, 2))
    tr = g.add("Trend", "TextPlus", _txt(g, trend, fontFamily, "Bold", 14 * s, ac, center=g.xy(L + pad + 12 * s, py), left=True), at=(7, 4))
    out = g.add("TrendMrg", "Merge", _mrg(out, tr), at=(7, 2))
    cap = g.add("Caption", "TextPlus", _txt(g, caption, fontFamily, "Regular", 14 * s, mc, center=g.xy(L + pad + pw + 12 * s, py), left=True), at=(8, 4))
    out = g.add("CaptionMrg", "Merge", _mrg(out, cap), at=(8, 2))
    out = _place(g, c, out, cx, cy, base, 9)
    return _finish(g, "stat_card", out, target, controller=c, animated=[c + ".NumberIn1/2/4", g.n("Number") + ".StyledText"])


def cta_pill(text="Get started", color=None, textColor=None, x=None, y=None, height=None, width=None, fontSize=None,
             fontFamily="Open Sans", glow=True, backgroundColor=None, W=1920, H=1080, fps=24, start=0, prefix="CTA_", target=None):
    """ui-mastery 5.1 primary CTA as a pill: accent plate (CornerRadius 1), label, accent glow (Shadow
    tool, offset 0, alpha 0.4) and the house reveal. Width auto-estimated from the label unless given."""
    g = G(prefix, W, H, fps, start)
    s = W / 1920
    fs = fontSize or 24 * s
    ph = height or 64 * s
    pw = width or _est_w(text, fs) + 2 * 36 * s
    cx, cy = (W / 2 if x is None else x), (H / 2 if y is None else y)
    ac, tc = _col(color, _UI["accent"]), _col(textColor, (1, 1, 1))
    c = _reveal_ctrl(g)
    base = _base(g, target, _col(backgroundColor, _UI["page"]))
    plate = _plate(g, "Plate", ac, rect_mask(W / 2 - pw / 2, H / 2 - ph / 2, pw, ph, W, H, ph / 2), at=(1, 3))
    lab = g.add("Label", "TextPlus", _txt(g, text, fontFamily, "Bold", fs, tc), at=(1, 4))
    out = g.add("LabelMrg", "Merge", _mrg(plate, lab), at=(2, 3))
    if glow:
        out = g.add("Glow", "Shadow", {"Input": Src(out), "ShadowOffset": (0.5, 0.5 - 8 * s / H), "Softness": 0.02,
                                       "Red": ac[0], "Green": ac[1], "Blue": ac[2], "Alpha": 0.45}, at=(3, 3))
    out = _place(g, c, out, cx, cy, base, 4)
    return _finish(g, "cta_pill", out, target, controller=c, animated=[g.n("Xf") + ".Center/Size", out + ".Blend"])


def ui_card(label="NEW FEATURE", title="Ship your launch in minutes", body="Native Fusion motion, one call.",
            x=None, y=None, width=None, height=None, radius=None, fontFamily="Open Sans", backgroundColor=None,
            surfaceColor=None, borderColor=None, textColor=None, mutedColor=None, accentColor=None,
            W=1920, H=1080, fps=24, start=0, prefix="UC_", target=None):
    """ui-mastery 5.3 surface card: S1 shadow, fill, 1 px ring, accent caps label, title, muted body.
    The card rises + scales in (house) and its three text rows fade in 50 ms apart after it."""
    g = G(prefix, W, H, fps, start)
    s = W / 1920
    w, h, r = (width or 560 * s), (height or 180 * s), (radius if radius is not None else 16 * s)
    cx, cy = (W / 2 if x is None else x), (H / 2 if y is None else y)
    c = _reveal_ctrl(g)
    base = _base(g, target, _col(backgroundColor, _UI["page"]))
    out, L, T = _card_frame(g, w, h, r, _col(surfaceColor, _UI["surface"]), _col(borderColor, _UI["border"]))
    pad = 32 * s
    rows = (("Label", label, 14 * s, "Bold", _col(accentColor, _UI["accent"]), T + pad + 8 * s, 1.08),
            ("Title", title, 30 * s, "Bold", _col(textColor, _UI["text"]), T + pad + 50 * s, None),
            ("Body", body, 18 * s, "Regular", _col(mutedColor, _UI["muted"]), T + pad + 96 * s, None))
    for i, (nm, txt, px, sty, col, ty, sp) in enumerate(rows):
        t = g.add(nm, "TextPlus", _txt(g, txt, fontFamily, sty, px, col, center=g.xy(L + pad, ty), left=True, spacing=sp), at=(4 + i, 4))
        out = g.add(nm + "Mrg", "Merge", _mrg(out, t, Expr(_rv(c, 2, (0.2 + 0.05 * i) * fps), 1)), at=(4 + i, 2))
    out = _place(g, c, out, cx, cy, base, 7)
    return _finish(g, "ui_card", out, target, controller=c, animated=[g.n("Xf") + ".Center/Size", out + ".Blend", "row Blends"])


def camera_push_3d(cards=None, push=1.0, duration=4.0, flength=35, fontFamily="Open Sans", backgroundColor=None,
                   cardColor=None, textColor=None, W=1920, H=1080, fps=24, start=0, prefix="CP_", target=None):
    """depth-space R1 + R3a: card textures on ImagePlane3D at real depths (z = distance, camera at the
    origin looking down -Z), Merge3D + Camera3D + Renderer3D (Software), camera dollies Translate.Z
    0 -> -push over `duration` (settle ease), sky gradient behind. cards = [{label, x, y, z}] with x, y
    as fractions of the visible width/height at that depth. Growth per card = z/(z - push)."""
    g = G(prefix, W, H, fps, start)
    cards = cards or [{"label": "Analytics", "x": -0.27, "y": 0.2, "z": 7.0},
                      {"label": "Revenue", "x": 0.02, "y": -0.04, "z": 10.0},
                      {"label": "Growth", "x": 0.28, "y": 0.24, "z": 15.0}]
    cc, tc = _col(cardColor, _UI["surface"]), _col(textColor, _UI["text"])
    wz = 0.6034 * 35 / flength  # visible width per unit depth (default aperture)
    stage = {}
    for i, cd in enumerate(cards):
        z = float(cd["z"])
        plate = _plate(g, "Card%dPlate" % i, cc, dict(rect_mask(0.27 * W, 0.25 * H, 0.46 * W, 0.5 * H, W, H, 0.04 * W)), at=(0, 3 * i + 1))
        ring = g.add("Card%dAccent" % i, "Background", dict(_bg(_col(_UI["accent"], None)),
                                                             EffectMask=Src(g.add("Card%dAccentM" % i, "RectangleMask", rect_mask(0.31 * W, 0.33 * H, 0.08 * W, 0.012 * H, W, H, 0.006 * H), at=(1, 3 * i + 2)), "Mask")), at=(1, 3 * i + 1))
        m1 = g.add("Card%dMrgA" % i, "Merge", _mrg(plate, ring), at=(2, 3 * i + 1))
        lab = g.add("Card%dLabel" % i, "TextPlus", _txt(g, cd.get("label", "Card %d" % (i + 1)), fontFamily, "Bold", round(0.09 * H), tc), at=(2, 3 * i + 2))
        m2 = g.add("Card%dMrg" % i, "Merge", _mrg(m1, lab), at=(3, 3 * i + 1))
        sc = wz * z * 0.6  # plane width = 60 % of the visible width at its depth (card = 46 % of it)
        stage["SceneInput%d" % (i + 1)] = Src(g.add("Card%d" % i, "ImagePlane3D", {
            "MaterialInput": Src(m2), "Transform3DOp.Translate.X": cd.get("x", 0) * wz * z, "Transform3DOp.Translate.Y": cd.get("y", 0) * wz * z * H / W,
            "Transform3DOp.Translate.Z": -z, "Transform3DOp.Scale.X": sc}, at=(4, 3 * i + 1)))
    # pasted Camera3D defaults to FilmGate "TV" (AoV 24.33) [live]: write the film back explicitly
    cam = g.add("Cam", "Camera3D", {"FilmGate": FuID("BMD_URSA_4K_16x9"), "ApertureW": 0.8315, "ApertureH": 0.4677,
                                    "FLength": flength}, at=(4, 3 * len(cards) + 1))
    g.spline(cam, "Transform3DOp.Translate.Z", [(g.fr(0), 0), (g.fr(duration), -push)], "settle")
    stage["SceneInput%d" % (len(cards) + 1)] = Src(cam)
    st = g.add("Stage", "Merge3D", stage, at=(5, 1))
    # pasted Renderer3D defaults to 320x240 [live]: follow the comp format
    rn = g.add("Render", "Renderer3D", {"UseFrameFormatSettings": 1, "Width": W, "Height": H, "SceneInput": Src(st),
                                        "MotionBlur": 1, "Quality": 4, "ShutterAngle": 180}, at=(6, 1))
    if target:
        base = _base(g, target)
    else:
        top, bot = _col(backgroundColor, (0.06, 0.07, 0.12)), (0.16, 0.18, 0.28)
        base = g.add("Sky", "Background", {"UseFrameFormatSettings": 1, "Type": FuID("Gradient"), "Start": (0.5, 1), "End": (0.5, 0),
                                           "Gradient": Grad({0: top + (1,), 1: bot + (1,)})}, at=(6, 0))
    out = g.add("Comp", "Merge", _mrg(base, rn), at=(7, 0))
    return _finish(g, "camera_push_3d", out, target, animated=[cam + ".Transform3DOp.Translate.Z"],
                   growth={c.get("label", i): round(c["z"] / (c["z"] - push), 3) for i, c in enumerate(cards)})


BUILDERS = {f.__name__: f for f in (title_card, lower_third, logo_reveal, text_animator, transition, liquid_glass,
                                    effect_template, expression_template, reveal_floor, stat_card, cta_pill, ui_card, camera_push_3d)}


# ================================================================ live build (Resolve)

def _unanimated_merges(comp, skip_prefix="RF_"):
    """Merges with no animation on Blend/Center/Size/Angle or up their Foreground chain, in chain order;
    full-frame Background plates (no EffectMask) are the BG, not elements."""
    tools = {t.GetAttrs()["TOOLS_Name"]: t for t in comp.GetToolList(False).values()}

    def inputs(t):
        return {i.GetAttrs()["INPS_ID"]: i for i in t.GetInputList().values()}

    def live(t, ids):
        ins = inputs(t)
        for iid in ids:
            i = ins.get(iid)
            if i is None:
                continue
            o = i.GetConnectedOutput()
            if i.GetExpression() or (o and o.GetAttrs()["OUTS_ID"] not in ("Output", "Mask")):
                return True
        return False

    def src(t, iid):
        i = inputs(t).get(iid)
        o = i.GetConnectedOutput() if i else None
        return o.GetTool() if o else None

    found = []
    for n, m in tools.items():
        if m.GetAttrs()["TOOLS_RegID"] != "Merge" or n.startswith(skip_prefix):
            continue
        if live(m, ("Blend", "Center", "Size", "Angle")):
            continue
        fg, animated, hops = src(m, "Foreground"), False, 0
        if fg is None:
            continue
        if fg.GetAttrs()["TOOLS_RegID"] == "Background" and src(fg, "EffectMask") is None:
            continue
        while fg is not None and hops < 12:
            if live(fg, ("Center", "Size", "Angle", "Opacity1", "StyledText", "Blend", "Pivot")):
                animated = True
                break
            fg = src(fg, "Input") or src(fg, "Foreground")
            hops += 1
        if animated:
            continue
        depth, b = 0, src(m, "Background")
        while b is not None and depth < 64:
            if b.GetAttrs()["TOOLS_RegID"] == "Merge":
                depth += 1
            b = src(b, "Background") or src(b, "Input")
        c = m.GetInput("Center")
        found.append((depth, n, (c[1], c[2]) if isinstance(c, dict) else (0.5, 0.5)))
    return [{"merge": n, "center": ctr} for _, n, ctr in sorted(found)]


def _run_post(comp, actions, ren):
    def N(n):
        return ren.get(n, n)

    def R(e):  # retarget pasted names inside expressions
        for old, new in ren.items():
            if old != new:
                e = re.sub(r"\b%s\b" % re.escape(old), new, e)
        return e
    done = []
    for a in actions:
        kind = a[0]
        if kind == "connect":
            _, dst, iid, src, out = a
            connect(comp.FindTool(N(dst)), iid, comp.FindTool(N(src)), out)
        elif kind == "expr":
            _, tool, iid, e = a
            t = comp.FindTool(N(tool))
            i = next(v for v in t.GetInputList().values() if v.GetAttrs()["INPS_ID"] == iid)
            i.SetExpression(R(e))
        elif kind == "reroute":  # consumers of target's main output now read our output
            _, target, new = a
            prefix_tools = set(ren.values())
            new_t = comp.FindTool(N(new))
            for t in comp.GetToolList(False).values():
                tn = t.GetAttrs()["TOOLS_Name"]
                if tn in prefix_tools or tn == N(new):
                    continue
                for i in t.GetInputList().values():
                    o = i.GetConnectedOutput()
                    if o and o.GetTool().GetAttrs()["TOOLS_Name"] == target and o.GetAttrs()["OUTS_ID"] == "Output":
                        t.ConnectInput(i.GetAttrs()["INPS_ID"], new_t)  # returns falsy for a group target yet connects [live]
                        done.append("%s.%s" % (tn, i.GetAttrs()["INPS_ID"]))
        done.append(kind)
    return done


def build(comp, builder, **kw):
    """Paste builder(**kw) into the CURRENT Fusion-page comp and run its API-side steps.
    W/H/fps default to the comp's frame format. Returns {"added", "renamed", "info", "post"}."""
    name = builder if isinstance(builder, str) else builder.__name__
    fn = BUILDERS[name]
    kw.setdefault("W", int(comp.GetPrefs("Comp.FrameFormat.Width")))
    kw.setdefault("H", int(comp.GetPrefs("Comp.FrameFormat.Height")))
    kw.setdefault("fps", float(comp.GetPrefs("Comp.FrameFormat.Rate")))
    tgt = kw.get("target") or kw.get("layerName") or kw.get("backgroundLayerName")
    if tgt and comp.FindTool(tgt) is None:
        raise RuntimeError("target %r not found in the comp" % tgt)
    if name == "text_animator" and tgt and not kw.get("text"):
        kw["text"] = comp.FindTool(tgt).GetInput("StyledText") or ""
    if name == "expression_template" and tgt:
        t = comp.FindTool(tgt)
        kw.setdefault("targetType", t.GetAttrs()["TOOLS_RegID"])
        iid = _EXPR_MAP.get(kw["targetType"], {}).get(kw.get("propertyName", "Position"))
        if iid and "base" not in kw:
            kw["base"] = t.GetInput(iid)
        if kw.get("propertyName") == "Anchor Point" and "baseCenter" not in kw:
            kw["baseCenter"] = t.GetInput("Center")
    if name == "reveal_floor" and kw.get("merges") is None:
        kw["merges"] = _unanimated_merges(comp, kw.get("prefix", "RF_"))
        if not kw["merges"]:
            return {"added": [], "renamed": {}, "info": {"builder": name, "note": "nothing un-animated"}, "post": []}
    setting, info = fn(**kw)
    res = paste_setting(comp, setting) if setting else {"added": [], "renamed": {}}
    ren = {n: n for n in info.get("tools", [])}
    ren.update(res["renamed"])
    res["post"] = _run_post(comp, info.get("post", []), ren)
    res["info"] = info
    return res


# ================================================================ offline: components + check

VARIANTS = {
    "title_card": [dict(), dict(title="Launch Day", subtitle="September 26", backgroundColor={"r": 0.05, "g": 0.06, "b": 0.1}, fontSize=120),
                   dict(title="Solo", duration=1.0, color="#ffcc00", target="MediaIn1")],
    "lower_third": [dict(), dict(title="Alex Kim", subtitle=None, primaryColor="#e11d48"), dict(target="MediaIn1", W=3840, H=2160)],
    "logo_reveal": [dict(style=s) for s in ("scale", "fade", "slide", "spin")] + [dict(layerName="Loader1", style="spin")],
    "text_animator": [dict(animatorType=a) for a in ("typewriter", "fadeInChars", "scaleInChars", "slideInChars", "randomize", "wave")]
    + [dict(layerName="Title1", text="Hello", animatorType="fadeInChars")],
    "transition": [dict(type=t) for t in ("dissolve", "wipe_left", "wipe_right", "zoom")]
    + [dict(type=t, color={"r": 0, "g": 0, "b": 0}) for t in ("dissolve", "wipe_left", "zoom")] + [dict(inputA="MediaIn1", inputB="MediaIn2")],
    "liquid_glass": [dict(), dict(animatable=True, shapeType="ellipse", width=500, height=500, tintColor="#88ccff", refractionMode="vertical"),
                     dict(backgroundLayerName="MediaIn1", shadow=False, shine=False, name="Nav")],
    "effect_template": [dict(template=t) for t in ("cinematicLook", "glow", "filmGrain", "neonGlow", "vibrance")] + [dict(template="glow", layerName="Merge1")],
    "expression_template": [dict(template=t, propertyName=p) for t in ("wiggle", "wiggleSmooth", "wiggleFadeIn", "loopCycle", "loopPingpong", "loopOffset",
                                                                        "loopContinue", "time", "bounce", "inertia", "overshoot")
                            for p in ("Position", "Scale", "Rotation", "Opacity")]
    + [dict(template="wiggle", propertyName="Anchor Point"), dict(template="loopCycle", layerName="Merge1", targetType="Merge", base={1: 0.3, 2: 0.6})],
    "reveal_floor": [dict(), dict(merges=[{"merge": "Merge1", "center": (0.5, 0.5)}, {"merge": "Merge2", "center": (0.4, 0.6)}])],
    "stat_card": [dict(), dict(value=1234567, valuePrefix="", valueSuffix=" users", trend="+3.1%", W=3840, H=2160)],
    "cta_pill": [dict(), dict(text="Start free trial", glow=False, target="Merge1")],
    "ui_card": [dict(), dict(title="Pricing that scales", x=600, y=400, target="MediaIn1")],
    "camera_push_3d": [dict(), dict(push=1.0, cards=[{"label": "A", "z": 6}, {"label": "B", "z": 12, "x": 0.2}])],
}


def write_components(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for n, fn in BUILDERS.items():
        text, info = fn()
        p = os.path.join(out_dir, n + ".setting")
        with open(p, "w") as f:
            f.write(text)
        paths.append((p, info["output"], len(info["tools"])))
    return paths


def check(corpus_dir=None, tsv=None):
    """Build every builder x VARIANTS; parse each .setting (corpus luatable parser when given, else a
    brace/string balance check); audit every RegID, input ID, Source output and SourceOp."""
    here = os.path.dirname(os.path.abspath(__file__))
    tsv = tsv or os.path.join(here, "..", "..", "fusion-reference", "data", "fusion-21.1-inputs.tsv")
    reg_tsv = os.path.join(os.path.dirname(tsv), "fusion-21.1-registry.tsv")
    inputs, outs, common = {}, {}, set()
    for line in open(tsv):
        f = line.rstrip("\n").split("\t")
        if line.startswith("# common_inputs:"):
            common = set(line.split(":", 1)[1].split())
        elif line.startswith("@"):
            outs[f[0][1:]] = f[3].replace("outputs=", "").split(",")
        elif not line.startswith("#") and len(f) > 1:
            inputs.setdefault(f[0], set()).add(f[1])
    regs = {l.split("\t")[0] for l in open(reg_tsv) if not l.startswith("#")}
    # IDs the TSV filter drops or never harvested, each with a real-file citation
    frame = {"GlobalIn", "GlobalOut", "ProcessMode", "Width", "Height", "PixelAspect", "UseFrameFormatSettings", "Depth"}
    extra_regs = {"BezierSpline": "setting-format 1.7 (every keyed .setting)", "GroupOperator": "setting-format 1.10 / liquid-glass sec 7 [live]"}
    extra_in = {("PipeRouter", "Input"): "liquid-glass sec 7 [live]", ("PolyPath", "PolyLine"): "Rise Fade.setting / setting-format 4.2"}
    extra_out = {"BezierSpline": ["Value"], "PipeRouter": ["Output"], "StyledTextFollower": ["StyledText"], "PolyPath": ["Position", "Heading"]}
    parse = None
    if corpus_dir and os.path.exists(os.path.join(corpus_dir, "luatable.py")):
        import sys
        sys.path.insert(0, corpus_dir)
        from luatable import parse  # noqa
    problems, n = [], 0
    for bname, fn in BUILDERS.items():
        for kw in VARIANTS.get(bname, [dict()]):
            n += 1
            try:
                text, info = fn(**kw)
            except Exception as e:  # noqa
                problems.append("%s %s: raised %r" % (bname, kw, e))
                continue
            if not text:
                continue
            tag = "%s %s" % (bname, kw)
            depth, ins = 0, False
            for ch in re.sub(r'"(\\.|[^"\\])*"', '""', text):
                depth += (ch == "{") - (ch == "}")
                if depth < 0:
                    break
            if depth:
                problems.append(tag + ": unbalanced braces")
            tools = {}  # name -> (reg, LTable)
            if parse:
                try:
                    root = parse(text)
                except Exception as e:  # noqa
                    problems.append(tag + ": parse error %s" % e)
                    continue

                def walk(tbl):
                    for k, v in tbl.items:
                        if isinstance(k, str) and hasattr(v, "ctor"):
                            tools[k] = (v.ctor, v)
                            if v.ctor == "GroupOperator":
                                walk(v.get("Tools"))
                walk(root.get("Tools"))
            else:
                for m in re.finditer(r"^\t+(\w+) = (\w+) \{$", text, re.M):
                    tools[m.group(1)] = (m.group(2), None)
            for name, (reg, t) in tools.items():
                if reg not in regs and reg not in extra_regs:
                    problems.append("%s: %s unknown RegID %s" % (tag, name, reg))
                if t is None:
                    continue
                if reg == "GroupOperator":
                    for k, ii in t.get("Inputs").items:
                        op, src = ii.get("SourceOp"), ii.get("Source")
                        if op not in tools:
                            problems.append("%s: group input %s -> missing %s" % (tag, k, op))
                        elif src not in inputs.get(tools[op][0], set()) | common | frame and (tools[op][0], src) not in extra_in:
                            problems.append("%s: group input %s -> %s.%s not in TSV" % (tag, k, tools[op][0], src))
                    continue
                for k, ii in (t.get("Inputs").items if t.get("Inputs") else []):
                    dyn = reg == "Merge3D" and re.fullmatch(r"SceneInput\d+", k)  # setting-format sec 3: SceneInput1..N
                    if k not in inputs.get(reg, set()) | common | frame and (reg, k) not in extra_in and not dyn:
                        problems.append("%s: %s.%s (%s) not in TSV" % (tag, name, k, reg))
                    op = ii.get("SourceOp") if hasattr(ii, "get") else None
                    if op:
                        if op not in tools:
                            problems.append("%s: %s.%s <- missing tool %s" % (tag, name, k, op))
                        else:
                            valid = outs.get(tools[op][0], []) + extra_out.get(tools[op][0], [])
                            if ii.get("Source") not in valid:
                                problems.append("%s: %s.%s <- %s.%s (valid %s)" % (tag, name, k, op, ii.get("Source"), valid))
                    ex = ii.get("Expression") if hasattr(ii, "get") else None
                    for ref in re.findall(r"\b([A-Z][A-Za-z]*_\w+)[.:]", ex or ""):
                        if ref not in tools:
                            problems.append("%s: %s.%s expression references missing %s" % (tag, name, k, ref))
    return n, problems


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--components":
        for p, o, k in write_components(sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components")):
            print("%-60s output=%s tools=%d" % (p, o, k))
    elif len(sys.argv) > 1 and sys.argv[1] == "--check":
        n, probs = check(sys.argv[2] if len(sys.argv) > 2 else None)
        print("%d builds checked, %d problems" % (n, len(probs)))
        for p in probs:
            print(" -", p)
        sys.exit(1 if probs else 0)
    else:
        print(__doc__)
