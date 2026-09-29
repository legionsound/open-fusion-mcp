"""Build/output categories: text, font, shape, mask, merge, effect, transform, 3d, media, item, marker,
render, deliver, setting, builder, template, viewer, command, pref, data, eval, batch."""
import fnmatch
import glob
import inspect
import json
import os
import re
import shutil
import subprocess
import time
import uuid

from .. import config
from ..luatable import LTable, parse as lua_parse
from ..schema import P, TSV, suggest
from .base import (COMP, FRAME, INPUT, OPS, TOOL, OpError, build_module, color, jv, kit, num, op, png_bbox, png_info)
from .core import add_modifier, expression_set, tool_add
from .. import sysmem

MODAL_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dismiss_render_modal.applescript")


def _out(path, default_name):
    p = path or os.path.join(config.out_dir(), default_name)
    if not os.path.isabs(p):
        raise OpError("INVALID_ARGS", f"path must be absolute: {p}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def _safe(s):
    return re.sub(r"[^A-Za-z0-9_]+", "_", s)[:40]


# ================================================================ text (Text+)

@op("text.set_content", "Set a Text+ (or Text3D) tool's text (StyledText) and read it back. Fails if a modifier (Follower, TextTimer...) drives the text.",
    [COMP(), TOOL(), P("text", "string", "New text (\\n for line breaks).", required=True), FRAME])
def text_set_content(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    reg = t.GetAttrs()["TOOLS_RegID"]
    if reg not in ("TextPlus", "Text3D"):
        raise OpError("INVALID_ARGS", f"{a['tool']} is {reg}, not TextPlus/Text3D")
    src = ctx.source_of(t, "StyledText")
    if src:
        raise OpError("INVALID_ARGS", f"StyledText is driven by {src[0]}", hint="Set the text on the modifier's own StyledText input (Follower Text), or modifier.remove.")
    return {"text": ctx.set_input(comp, t, "StyledText", a["text"], a.get("frame"))}


JUSTIFY = {"left": -1, "center": 0, "right": 1}
VJUSTIFY = {"top": 1, "center": 0, "bottom": -1}


@op("text.set_style", "Style a Text+ tool (whole document, shading element 1): font, style, size (Size or sizePx via the measured 1.70*px/W rule), color, tracking (CharacterSpacing), leading (LineSpacing), justify/anchor, position (Center or centerPx), opacity. Every value is read back.",
    [COMP(), TOOL(), P("font", "string", "Family (see font.list)."), P("style", "string", "Style name (Bold, Regular...)."),
     P("size", "number", "Text+ Size (relative to frame width)."),
     P("sizePx", "number", "Font size in px, converted with sizeK: Size = sizeK*px/W. The default 1.70 is Open Sans only; the constant is per font and weight [rebuild K1/K20: Helvetica Neue Bold 1.49, Light 0.989 x Bold]: calibrate by one render or pass size."),
     P("sizeK", "number", "Font-specific size constant for sizePx (default: the text.size_for_px measurement for this font/style, else 1.70 = Open Sans Bold)."),
     P("color", "string|array", "'#rrggbb' or [r,g,b(,a)] for element 1."), P("tracking", "number", "CharacterSpacing (1 = default)."),
     P("leading", "number", "LineSpacing (1 = default)."), P("justify", "string", "left|center|right (sets the H anchor; Center.x becomes that edge).", enum=("left", "center", "right")),
     P("vjustify", "string", "top|center|bottom anchor.", enum=("top", "center", "bottom")),
     P("center", "array", "[x, y] normalized, Y up."), P("centerPx", "array", "[x, y] pixels, top-left origin."),
     P("opacity", "number", "Opacity1 (0-1).")])
def text_set_style(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    if t.GetAttrs()["TOOLS_RegID"] != "TextPlus":
        raise OpError("INVALID_ARGS", f"{a['tool']} is not a TextPlus tool")
    W, H, _ = ctx.fmt(comp)
    vals = {}
    if a.get("font"):
        fonts = _fonts(ctx)
        if fonts and a["font"] not in fonts:
            s = suggest(a["font"], list(fonts))
            raise OpError("NOT_FOUND", f"font family '{a['font']}' is not installed" + (f" - did you mean '{s}'?" if s else ""))
        vals["Font"] = a["font"]
        if a.get("style") and fonts and a["style"] not in fonts[a["font"]]:
            raise OpError("NOT_FOUND", f"style '{a['style']}' not in {a['font']}: {sorted(fonts[a['font']])}")
    if a.get("style"):
        vals["Style"] = a["style"]
    k_used = None
    if a.get("sizePx") is not None:
        fam = a.get("font") or jv(t.GetInput("Font", comp.CurrentTime))
        sty = a.get("style") or jv(t.GetInput("Style", comp.CurrentTime))
        k_used = a.get("sizeK") or (_size_k_cache().get(f"{fam}/{sty}") or {}).get("K")
        vals["Size"] = float(k_used or 1.70) * a["sizePx"] / W
    if a.get("size") is not None:
        vals["Size"] = a["size"]
    if a.get("tracking") is not None:
        vals["CharacterSpacing"] = a["tracking"]
    if a.get("leading") is not None:
        vals["LineSpacing"] = a["leading"]
    if a.get("justify"):
        vals["HorizontalJustificationNew"] = 3
        vals["HorizontalLeftCenterRight"] = JUSTIFY[a["justify"]]
    if a.get("vjustify"):
        vals["VerticalJustificationNew"] = 3
        vals["VerticalTopCenterBottom"] = VJUSTIFY[a["vjustify"]]
    if a.get("center"):
        vals["Center"] = a["center"]
    if a.get("centerPx"):
        vals["Center"] = {"px": a["centerPx"]}
    if a.get("opacity") is not None:
        vals["Opacity1"] = a["opacity"]
    if a.get("color") is not None:
        c = color(a["color"])
        vals.update(Red1=c[0], Green1=c[1], Blue1=c[2], Alpha1=c[3])
    if not vals:
        raise OpError("INVALID_ARGS", "nothing to set")
    notes = ["VerticalTopCenterBottom sign unverified; check by render"] if a.get("vjustify") else []
    if a.get("sizePx") is not None and not k_used and fam != "Open Sans":
        notes.append(f"sizePx used the Open Sans constant 1.70; {fam} {sty} differs (Helvetica Neue Bold 1.49): run text.size_for_px once "
                     "for this font/style (then sizePx uses it) or pass sizeK")
    return {"tool": a["tool"], "set": {k: ctx.set_input(comp, t, k, v) for k, v in vals.items()}, "notes": notes}


FOLLOWER_ORDER = {"left_to_right": 0, "right_to_left": 1, "inside_out": 2, "outside_in": 3, "random_one_by_one": 4, "random": 5, "manual": 6, "auto": 7}


@op("text.add_follower", "Attach a Follower (StyledTextFollower) to a Text+ tool: per-character animation (the AE text animator + range selector analog). Sets Order (verified values), delay type and delay; returns the Follower name so its inputs (Opacity, Size, Center offset...) can be keyed with keyframe.add. The text moves onto the Follower's own Text input.",
    [COMP(), TOOL(), P("order", "string", "Character order.", enum=tuple(FOLLOWER_ORDER), default="left_to_right"),
     P("delay", "number", "Frames between characters (Delay)."), P("delayType", "string", "none|between_each|first_to_last.", enum=("none", "between_each", "first_to_last")),
     P("inputs", "object", "Extra Follower inputs {id: value}."), P("name", "string", "Follower name.")])
def text_add_follower(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    txt = t.GetInput("StyledText", comp.CurrentTime)
    m = add_modifier(ctx, comp, t, "StyledText", "StyledTextFollower")
    ft = comp.FindTool(m)
    if a.get("name"):
        ft.SetAttrs({"TOOLS_Name": a["name"]})
        m = ft.GetAttrs()["TOOLS_Name"]
    vals = {"Order": FOLLOWER_ORDER[a.get("order", "left_to_right")]}
    if a.get("delayType"):
        vals["DelayType"] = {"none": 0, "between_each": 1, "first_to_last": 2}[a["delayType"]]
    if a.get("delay") is not None:
        vals["Delay"] = a["delay"]
    vals.update(a.get("inputs") or {})
    got = {}
    for k, v in vals.items():
        got[k] = ctx.set_input(comp, ft, k, v)
    fin = ctx.inputs(ft)
    if txt and "Text" in fin:
        try:
            ft.SetInput("Text", txt)
        except Exception:
            pass
    return {"follower": m, "set": got, "text": jv(ft.GetInput("Text", comp.CurrentTime)) if "Text" in fin else None,
            "animatable": sorted(k for k in fin if re.fullmatch(r"(Opacity|Size|SizeX|SizeY|CharacterOffset|Offset|Angle|AngleZ|Softness|Red|Green|Blue|Alpha)\d*", k))}


# ================================================================ font

def _size_k_path():
    return os.path.join(config.out_dir(), "font_size_k.json")


def _size_k_cache():
    try:
        with open(_size_k_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def font_cap_per_em(path, family, style):
    """Cap height of 'H' per em from the font file (Pillow; .ttc faces matched by name)."""
    from PIL import ImageFont
    best = None
    for idx in range(64):
        try:
            f = ImageFont.truetype(path, 1000, index=idx)
        except OSError:
            break
        fam, sty = f.getname()
        if best is None or (fam == family and sty == style):
            best = f
        if fam == family and sty == style:
            break
        if not path.lower().endswith((".ttc", ".otc")):
            break
    if best is None:
        raise OpError("NOT_FOUND", f"could not read font file {path}")
    x0, y0, x1, y1 = best.getbbox("H")
    return (y1 - y0) / 1000.0, best.getname()


@op("text.size_for_px", "Text+ Size for a font size in px (AE/CSS em) for THIS font and style: Size = K*px/W. [rebuild K1/K20] K is per font and weight (Open Sans Bold 1.70, Helvetica Neue Bold 1.49, Light 1.1 % wider). Measures once: a temporary Text+ 'H' at Size 0.4 (its DoD cap height, no render) against the font file's cap height per em; the K is cached (out/font_size_k.json) and text.set_style sizePx then uses it.",
    [COMP(), P("font", "string", "Family (font.list).", required=True), P("style", "string", "Style (default Regular).", default="Regular"),
     P("px", "number", "Font size px to convert (optional)."), P("remeasure", "boolean", "Ignore the cache.")], undo="discard")
def text_size_for_px(ctx, comp, a):
    fonts = _fonts(ctx)
    fam, sty = a["font"], a.get("style", "Regular")
    if fonts and fam not in fonts:
        s_ = suggest(fam, list(fonts))
        raise OpError("NOT_FOUND", f"font family '{fam}' is not installed" + (f" - did you mean '{s_}'?" if s_ else ""))
    if fonts and sty not in fonts[fam]:
        raise OpError("NOT_FOUND", f"style '{sty}' not in {fam}: {sorted(fonts[fam])}")
    W, H, _ = ctx.fmt(comp)
    cache = _size_k_cache()
    key = f"{fam}/{sty}"
    if key in cache and not a.get("remeasure"):
        row = dict(cache[key], cached=True)
    else:
        S0 = 0.4
        t = ctx.add_tool(comp, "TextPlus", "FC_TmpMeasure_" + uuid.uuid4().hex[:6])
        try:
            t.SetInput("StyledText", "H")
            t.SetInput("Font", fam)
            t.SetInput("Style", sty)
            t.SetInput("Size", S0)
            t.SetInput("Center", {1: 0.5, 2: 0.5})
            d = jv(t.FindMainOutput(1).GetDoD(comp.CurrentTime))
        finally:
            t.Delete()
        if not d or len(d) < 4:
            raise OpError("OPERATION_FAILED", f"GetDoD returned {d!r} for the measuring Text+")
        cap_px = float(d[3]) - float(d[1])
        file = (fonts.get(fam) or {}).get(sty)
        if not file or not os.path.exists(str(file)):
            raise OpError("NOT_FOUND", f"no font file for {key} from FontManager", details={"file": file})
        cpe, face = font_cap_per_em(str(file), fam, sty)
        em_px = cap_px / cpe
        K = S0 * W / em_px
        row = {"K": round(K, 4), "capPx": round(cap_px, 1), "capPerEm": round(cpe, 4), "W": W, "face": list(face), "file": file}
        cache[key] = row
        with open(_size_k_path(), "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1)
    out = {"font": fam, "style": sty, **row}
    if a.get("px") is not None:
        out["size"] = round(row["K"] * float(a["px"]) / W, 6)
    return out

def _fonts(ctx):
    try:
        return jv(ctx.fusion().FontManager.GetFontList()) or {}
    except Exception:
        return {}


@op("font.list", "List installed font families and styles (Fusion FontManager). Filter by substring.",
    [P("familyContains", "string", "Case-insensitive family substring."), P("limit", "integer", "Max families (default 200).", default=200)],
    read=True, comp=False)
def font_list(ctx, a):
    fonts = _fonts(ctx)
    q = (a.get("familyContains") or "").lower()
    fams = sorted(f for f in fonts if q in f.lower())
    return {"count": len(fams), "fonts": {f: sorted(fonts[f]) for f in fams[:int(a.get("limit", 200))]}}


@op("font.info", "Styles and font files of one family.", [P("family", "string", "Family name.", required=True)], read=True, comp=False)
def font_info(ctx, a):
    fonts = _fonts(ctx)
    if a["family"] not in fonts:
        s = suggest(a["family"], list(fonts))
        raise OpError("NOT_FOUND", f"font '{a['family']}' not installed" + (f" - did you mean '{s}'?" if s else ""))
    return {"family": a["family"], "styles": fonts[a["family"]]}


@op("font.list_used", "Fonts used by Text+/Text3D tools in the comp, flagging families/styles that are not installed (list_used + list_missing).",
    [COMP()], read=True)
def font_list_used(ctx, comp, a):
    fonts = _fonts(ctx)
    used = {}
    for t in (comp.GetToolList(False) or {}).values():
        if t.GetAttrs()["TOOLS_RegID"] in ("TextPlus", "Text3D"):
            fam, sty = t.GetInput("Font", comp.CurrentTime), t.GetInput("Style", comp.CurrentTime)
            used.setdefault(f"{fam}/{sty}", {"family": fam, "style": sty, "tools": [],
                                              "installed": fam in fonts and sty in fonts.get(fam, {})})["tools"].append(t.GetAttrs()["TOOLS_Name"])
    rows = list(used.values())
    return {"used": rows, "missing": [r for r in rows if not r["installed"]]}


@op("font.replace", "Replace a font family (and optionally style) on every Text+/Text3D tool in the comp (project.replace_font analog).",
    [COMP(), P("fromFamily", "string", "Family to replace.", required=True), P("toFamily", "string", "New family.", required=True),
     P("toStyle", "string", "New style (default keep).")])
def font_replace(ctx, comp, a):
    fonts = _fonts(ctx)
    if fonts and a["toFamily"] not in fonts:
        raise OpError("NOT_FOUND", f"font '{a['toFamily']}' not installed")
    changed = []
    for t in (comp.GetToolList(False) or {}).values():
        if t.GetAttrs()["TOOLS_RegID"] in ("TextPlus", "Text3D") and t.GetInput("Font", comp.CurrentTime) == a["fromFamily"]:
            t.SetInput("Font", a["toFamily"])
            if a.get("toStyle"):
                t.SetInput("Style", a["toStyle"])
            changed.append(t.GetAttrs()["TOOLS_Name"])
    return {"changed": changed}


# ================================================================ shape (sShapes)

SHAPES = {"rectangle": "sRectangle", "ellipse": "sEllipse", "star": "sStar", "ngon": "sNGon", "polygon": "sPolygon", "text": "sText"}


@op("shape.add", "Add a vector sShape (rectangle|ellipse|star|ngon). Geometry in px is converted with the measured rule (sShape Width, Height, Translate are fractions of frame WIDTH, CornerRadius as RectangleMask). stroke > 0 draws an outline (Solid 0 + BorderWidth). Read back.",
    [COMP(), P("type", "string", "Shape type.", required=True, enum=("rectangle", "ellipse", "star", "ngon")), P("name", "string", "Tool name."),
     P("widthPx", "number", "Width in px."), P("heightPx", "number", "Height in px."), P("centerPx", "array", "[x, y] px, top-left origin (default frame center)."),
     P("radiusPx", "number", "Corner radius px (rectangle)."), P("color", "string|array", "Fill/stroke color."), P("strokePx", "number", "Outline width px (0 = filled)."),
     P("points", "integer", "Star points / ngon sides."), P("angle", "number", "Rotation degrees."), P("inputs", "object", "Extra inputs {id: value}.")])
def shape_add(ctx, comp, a):
    W, H, _ = ctx.fmt(comp)
    reg = SHAPES[a["type"]]
    vals = {}
    if a.get("widthPx") is not None:
        vals["Width"] = a["widthPx"] / W
    if a.get("heightPx") is not None:
        vals["Height"] = a["heightPx"] / W
    if a.get("centerPx"):
        x, y = a["centerPx"]
        vals["Translate.X"] = (x - W / 2) / W
        vals["Translate.Y"] = (H / 2 - y) / W
    if a.get("radiusPx") and a["type"] == "rectangle":
        w = a.get("widthPx") or W / 2
        h = a.get("heightPx") or W / 2
        vals["CornerRadius"] = min(1.0, 2 * a["radiusPx"] / min(w, h))
    if a.get("color") is not None:
        c = color(a["color"])
        vals.update(Red=c[0], Green=c[1], Blue=c[2], Alpha=c[3])
    if a.get("strokePx"):
        vals["Solid"] = 0
        vals["BorderWidth"] = a["strokePx"] / W
    if a.get("points"):
        vals["Points" if a["type"] == "star" else "Sides"] = a["points"]
    if a.get("angle") is not None:
        vals["Angle"] = a["angle"]
    vals.update(a.get("inputs") or {})
    return tool_add(ctx, comp, {"regId": reg, "name": a.get("name"), "inputs": vals})


@op("shape.modify", "Insert an sShape modifier after a shape (sOutline stroke, sTransform, sDuplicate repeater, sJitter wiggle, sExpand offset, sChangeStyle, sGrid): wires Input and reroutes the shape's consumers through it.",
    [COMP(), TOOL("Upstream shape tool."), P("regId", "string", "sOutline | sTransform | sDuplicate | sJitter | sExpand | sChangeStyle | sGrid.", required=True,
                                             enum=("sOutline", "sTransform", "sDuplicate", "sJitter", "sExpand", "sChangeStyle", "sGrid")),
     P("name", "string", "Tool name."), P("inputs", "object", "Inputs {id: value}.")])
def shape_modify(ctx, comp, a):
    return effect_add(ctx, comp, {"regId": a["regId"], "after": a["tool"], "name": a.get("name"), "inputs": a.get("inputs")})


@op("shape.combine", "Combine two shapes: sMerge (stack, keeps both styles) or sBoolean (union/intersection/subtract/xor: the AE merge-paths analog).",
    [COMP(), P("a", "string", "First shape tool.", required=True), P("b", "string", "Second shape tool.", required=True),
     P("mode", "string", "merge | Union | Intersection | Subtract | XOr ... (sBoolean Operation option).", default="merge"), P("name", "string", "Tool name.")])
def shape_combine(ctx, comp, a):
    mode = a.get("mode", "merge")
    if mode == "merge":
        return tool_add(ctx, comp, {"regId": "sMerge", "name": a.get("name"), "connect": {"Input1": a["a"], "Input2": a["b"]}})
    return tool_add(ctx, comp, {"regId": "sBoolean", "name": a.get("name"), "inputs": {"Operation": mode},
                                "connect": {"Input1": a["a"], "Input2": a["b"]}})


@op("shape.set_trim", "Trim a shape's stroke/fill path (WritePosition/WriteLength, the AE Trim Paths analog). Key it with keyframe.add on WriteLength for draw-on.",
    [COMP(), TOOL(), P("start", "number", "WritePosition 0-1."), P("length", "number", "WriteLength 0-1.")])
def shape_set_trim(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    out = {}
    if a.get("start") is not None:
        out["WritePosition"] = ctx.set_input(comp, t, "WritePosition", a["start"])
    if a.get("length") is not None:
        out["WriteLength"] = ctx.set_input(comp, t, "WriteLength", a["length"])
    return out


@op("shape.render", "Rasterize a shape tree with sRender (optionally merged over a background tool). Returns the image tool to composite.",
    [COMP(), TOOL("Shape tree tool (last shape/modifier)."), P("name", "string", "sRender name."), P("over", "string", "Background tool to Merge over (creates a Merge).")])
def shape_render(ctx, comp, a):
    r = tool_add(ctx, comp, {"regId": "sRender", "name": a.get("name"), "connect": {"Input": a["tool"]}})
    if a.get("over"):
        m = merge_add(ctx, comp, {"background": a["over"], "foreground": r["tool"]})
        r["merge"] = m["merge"]
    return r


# ================================================================ mask

MASKS = {"rectangle": "RectangleMask", "ellipse": "EllipseMask", "polygon": "PolylineMask", "bspline": "BSplineMask",
         "ranger": "RangesMask", "triangle": "TriangleMask", "wand": "WandMask"}


@op("mask.add", "Add a mask and attach it: to a tool's EffectMask (tool), or chained into another mask (chainTo) with PaintMode. Pixel geometry uses the measured rules (Rectangle Width/W, Height/H; Ellipse both /W; CornerRadius = r/(min(w,h)/2); softness px -> SoftEdge 1.18*px/W).",
    [COMP(), P("type", "string", "rectangle | ellipse | triangle | ranger | wand (polygons: mask.add_polygon).", required=True,
               enum=("rectangle", "ellipse", "triangle", "ranger", "wand")),
     P("name", "string", "Mask name."), P("tool", "string", "Tool whose EffectMask receives the mask."), P("chainTo", "string", "Mask whose EffectMask receives this mask."),
     P("boxPx", "array", "[x, y, w, h] top-left pixel box."), P("radiusPx", "number", "Corner radius px (rectangle)."),
     P("softnessPx", "number", "Edge softness (CSS-blur-like px)."), P("invert", "boolean", "Invert."),
     P("paintMode", "string", "Merge|Add|Subtract|Minimum|Maximum|Average|Multiply|Replace|Invert|None."), P("inputs", "object", "Extra inputs.")])
def mask_add(ctx, comp, a):
    W, H, _ = ctx.fmt(comp)
    k = kit()
    reg = MASKS[a["type"]]
    vals = {}
    if a.get("boxPx"):
        x, y, w, h = a["boxPx"]
        if a["type"] == "ellipse":
            m = k["ellipse_mask"](x + w / 2, y + h / 2, w, h, W, H)
        else:
            m = k["rect_mask"](x, y, w, h, W, H, a.get("radiusPx") or 0)
            if a["type"] != "rectangle":
                m.pop("CornerRadius", None)
        vals.update({kk: ([vv[1], vv[2]] if isinstance(vv, dict) else vv) for kk, vv in m.items()})
    if a.get("softnessPx") is not None:
        vals["SoftEdge"] = 1.18 * a["softnessPx"] / W
    if a.get("invert") is not None:
        vals["Invert"] = 1 if a["invert"] else 0
    if a.get("paintMode"):
        vals["PaintMode"] = a["paintMode"]
    vals.update(a.get("inputs") or {})
    ct = None
    if a.get("tool"):
        ct = {"tool": a["tool"], "input": "EffectMask"}
    elif a.get("chainTo"):
        ct = {"tool": a["chainTo"], "input": "EffectMask"}
    return tool_add(ctx, comp, {"regId": reg, "name": a.get("name"), "inputs": vals, **({"connectTo": ct} if ct else {})})


@op("mask.add_polygon", "Add a PolylineMask (or BSplineMask) from pixel points via a .setting paste (the Python bridge cannot write Polyline values). Needs the target comp current on the Fusion page (auto when comp is a reference). Optionally attaches to a tool's EffectMask.",
    [COMP(), P("points", "array", "[[x, y], ...] pixels, top-left origin (>= 3).", required=True), P("name", "string", "Mask name.", required=True),
     P("closed", "boolean", "Closed shape (default true).", default=True), P("smooth", "boolean", "BSplineMask instead of linear polygon."),
     P("softnessPx", "number", "Edge softness px."), P("invert", "boolean", "Invert."), P("tool", "string", "Attach to this tool's EffectMask.")],
    extra={"paste": True})
def mask_add_polygon(ctx, comp, a):
    W, H, _ = ctx.fmt(comp)
    pts = a["points"]
    if len(pts) < 3:
        raise OpError("INVALID_ARGS", "need at least 3 points")
    if comp.FindTool(a["name"]) is not None:
        raise OpError("INVALID_ARGS", f"a tool named '{a['name']}' already exists")
    reg = "BSplineMask" if a.get("smooth") else "PolylineMask"
    # Polyline points are relative to the mask Center (0.5, 0.5), in width units for X and height units for Y
    body = ", ".join("{ Linear = true, X = %.7f, Y = %.7f }" % (x / W - 0.5, (1 - y / H) - 0.5) for x, y in pts)
    extra = ""
    if a.get("softnessPx") is not None:
        extra += "SoftEdge = Input { Value = %.7f, }, " % (1.18 * a["softnessPx"] / W)
    if a.get("invert"):
        extra += "Invert = Input { Value = 1, }, "
    closed = "true" if a.get("closed", True) else "false"
    text = ('{ Tools = ordered() { %s = %s { Inputs = { %s Polyline = Input { Value = Polyline { Closed = %s, Points = { %s } }, }, }, }, }, }'
            % (a["name"], reg, extra, closed, body))
    res = ctx.paste(comp, text)
    name = res["renamed"].get(a["name"], a["name"])
    out = {"mask": name, "added": res["added"], "points": len(pts)}
    if a.get("tool"):
        out["wired"] = ctx.connect(ctx.tool(comp, a["tool"]), "EffectMask", comp.FindTool(name))
    return out


@op("mask.set_props", "Mask properties in friendly units: softnessPx (SoftEdge), invert, opacity (Level), expansionPx (BorderWidth), paintMode, feather filter.",
    [COMP(), TOOL(), P("softnessPx", "number", "Edge softness px."), P("invert", "boolean", "Invert."), P("opacity", "number", "Level 0-1."),
     P("expansionPx", "number", "Grow (+) / shrink (-) px (BorderWidth)."), P("paintMode", "string", "PaintMode option."),
     P("filter", "string", "Box|Bartlett|Multi-box|Gaussian|Fast Gaussian.")])
def mask_set_props(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    W, _, _ = ctx.fmt(comp)
    vals = {}
    if a.get("softnessPx") is not None:
        vals["SoftEdge"] = 1.18 * a["softnessPx"] / W
    if a.get("invert") is not None:
        vals["Invert"] = 1 if a["invert"] else 0
    if a.get("opacity") is not None:
        vals["Level"] = a["opacity"]
    if a.get("expansionPx") is not None:
        vals["BorderWidth"] = a["expansionPx"] / W
    if a.get("paintMode"):
        vals["PaintMode"] = a["paintMode"]
    if a.get("filter"):
        vals["Filter"] = a["filter"]
    if not vals:
        raise OpError("INVALID_ARGS", "nothing to set")
    return {k: ctx.set_input(comp, t, k, v) for k, v in vals.items()}


# ================================================================ merge / composite

@op("merge.add", "Merge foreground over background (Merge sets output resolution from Background; a Merge without Background outputs nothing). applyMode/operator validated against the live option lists. Optional connectTo reroutes a consumer.",
    [COMP(), P("background", "string", "Background tool.", required=True), P("foreground", "string", "Foreground tool.", required=True),
     P("name", "string", "Merge name."), P("applyMode", "string", "Normal|Screen|Multiply|Overlay|Add ... (ApplyMode)."),
     P("operator", "string", "Over|In|Held Out|Atop|XOr|... (Operator)."), P("blend", "number", "Blend 0-1."),
     P("center", "array", "[x, y] normalized foreground offset."), P("size", "number", "Foreground size."),
     P("connectTo", "object", "{tool, input} consumer to receive the Merge.")])
def merge_add(ctx, comp, a):
    vals = {"PerformDepthMerge": 0}
    for k, iid in (("applyMode", "ApplyMode"), ("operator", "Operator"), ("blend", "Blend"), ("center", "Center"), ("size", "Size")):
        if a.get(k) is not None:
            vals[iid] = a[k]
    r = tool_add(ctx, comp, {"regId": "Merge", "name": a.get("name"), "inputs": vals,
                             "connect": {"Background": a["background"], "Foreground": a["foreground"]},
                             **({"connectTo": a["connectTo"]} if a.get("connectTo") else {})})
    r["merge"] = r["tool"]
    return r


@op("merge.stack", "Stack foregrounds over a background in order (bottom first), creating one Merge per layer: the AE layer-stack analog. Optionally feeds MediaOut1.",
    [COMP(), P("background", "string", "Background tool.", required=True), P("layers", "array", "Foreground tool names, bottom to top.", required=True),
     P("prefix", "string", "Merge name prefix (default 'Stack_')."), P("toMediaOut", "boolean", "Connect the top Merge to MediaOut1.Input.")])
def merge_stack(ctx, comp, a):
    bg = a["background"]
    made = []
    for n, fg in enumerate(a["layers"]):
        m = merge_add(ctx, comp, {"background": bg, "foreground": fg, "name": "%s%d" % (a.get("prefix") or "Stack_", n + 1)})
        bg = m["merge"]
        made.append(bg)
    out = {"merges": made, "top": bg}
    if a.get("toMediaOut"):
        mo = comp.FindTool("MediaOut1")
        if mo is None:
            raise OpError("NOT_FOUND", "no MediaOut1")
        out["mediaOut"] = ctx.connect(mo, "Input", comp.FindTool(bg))
    return out


@op("merge.set_blend_mode", "Set a Merge's ApplyMode (validated against the live option list).",
    [COMP(), TOOL("Merge tool."), P("mode", "string", "Normal|Screen|Dissolve|Darken|Multiply|Color Burn|...|Overlay|Soft Light|Hard Light|Difference|...", required=True)])
def merge_set_blend_mode(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    if t.GetAttrs()["TOOLS_RegID"] != "Merge":
        raise OpError("INVALID_ARGS", f"{a['tool']} is not a Merge")
    return {"ApplyMode": ctx.set_input(comp, t, "ApplyMode", a["mode"])}


@op("merge.set_matte", "Use an image/mask as a matte for a tool (track-matte analog): connects it to the tool's EffectMask and sets the channel (alpha|luma|red|green|blue) and inversion. matte omitted = remove.",
    [COMP(), TOOL("Tool to matte."), P("matte", "string", "Matte source tool (omit to remove)."),
     P("channel", "string", "alpha|luma|red|green|blue (default alpha).", enum=("alpha", "luma", "red", "green", "blue"), default="alpha"),
     P("invert", "boolean", "Inverted matte.")])
def merge_set_matte(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    if not a.get("matte"):
        t.ConnectInput("EffectMask", None)
        return {"matte": None}
    wired = ctx.connect(t, "EffectMask", ctx.tool(comp, a["matte"]))
    ch = {"alpha": 3, "luma": 4, "red": 0, "green": 1, "blue": 2}[a.get("channel", "alpha")]
    out = {"matte": wired}
    if "MaskChannel" in ctx.inputs(t):
        t.SetInput("MaskChannel", ch)
        out["MaskChannel"] = jv(t.GetInput("MaskChannel", comp.CurrentTime))
    if a.get("invert") is not None and "ApplyMaskInverted" in ctx.inputs(t):
        t.SetInput("ApplyMaskInverted", 1 if a["invert"] else 0)
        out["ApplyMaskInverted"] = jv(t.GetInput("ApplyMaskInverted", comp.CurrentTime))
    return out


# ================================================================ effect (filters in the pipe)

@op("effect.add", "Insert a filter tool (Blur, Glow, ColorCorrector, Shadow, DirectionalBlur, FilmGrain, Resolve FX ...) after a tool: wires Input <- after and reroutes after's consumers through it (the AE 'add effect to layer' analog). Without `after` it is added unwired.",
    [COMP(), P("regId", "string", "Filter registry ID.", required=True), P("after", "string", "Upstream tool to insert after."),
     P("name", "string", "Tool name."), P("inputs", "object", "Inputs {id: value}.")])
def effect_add(ctx, comp, a):
    if a.get("after"):
        up = ctx.tool(comp, a["after"])
        consumers = [c for c in ctx.consumers(comp, up) if c[2] == (up.FindMainOutput(1).GetAttrs()["OUTS_ID"] if up.FindMainOutput(1) else "Output")]
        r = tool_add(ctx, comp, {"regId": a["regId"], "name": a.get("name"), "inputs": a.get("inputs") or {}, "connect": {"Input": a["after"]}})
        new = comp.FindTool(r["tool"])
        rerouted = []
        for cn, ci, _ in consumers:
            if cn == r["tool"]:
                continue
            rerouted.append(ctx.connect(comp.FindTool(cn), ci, new) and f"{cn}.{ci}")
        r["rerouted"] = rerouted
        return r
    return tool_add(ctx, comp, {"regId": a["regId"], "name": a.get("name"), "inputs": a.get("inputs") or {}})


@op("effect.remove", "Remove an inserted filter and heal the pipe: its consumers are reconnected to its Input source.",
    [COMP(), TOOL("Filter tool.")])
def effect_remove(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    src = ctx.source_of(t, "Input") if "Input" in ctx.inputs(t) else None
    cons = ctx.consumers(comp, t)
    healed = []
    for cn, ci, _ in cons:
        ct = comp.FindTool(cn)
        if src:
            ctx.connect(ct, ci, comp.FindTool(src[0]), src[1])
            healed.append(f"{cn}.{ci} <- {src[0]}")
        else:
            ct.ConnectInput(ci, None)
    from .core import tool_delete
    tool_delete(ctx, comp, {"tool": a["tool"]})
    return {"removed": a["tool"], "healed": healed}


@op("effect.chain", "Walk the main-input chain upstream from a tool (the AE effect stack of a layer): tool, reg ID, pass-through, mask.",
    [COMP(), TOOL(), P("depth", "integer", "Max hops (default 20).", default=20)], read=True)
def effect_chain(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    chain = []
    for _ in range(int(a.get("depth", 20))):
        ta = t.GetAttrs()
        ins = ctx.inputs(t)
        chain.append({"tool": ta["TOOLS_Name"], "regId": ta["TOOLS_RegID"], "passThrough": bool(ta.get("TOOLB_PassThrough")),
                      "effectMask": ctx.source_of(t, "EffectMask") if "EffectMask" in ins else None})
        nxt = None
        for iid in ("Input", "Foreground", "Background"):
            if iid in ins:
                s = ctx.source_of(t, iid)
                if s:
                    nxt = comp.FindTool(s[0])
                    break
        if nxt is None:
            break
        t = nxt
    return {"chain": chain}


@op("effect.list_available", "List registry tools by category/substring from the live-harvested registry (offline). Categories include Blur, Color, Composite, Effect, Filter, Generator, Mask, Matte, Shape, Transform, Warp, 3D, Particles, Resolve FX *, Krokodove.",
    [P("category", "string", "Category substring."), P("contains", "string", "ID/name substring."), P("kind", "string", "tool|modifier.", enum=("tool", "modifier"))],
    read=True, comp=False, offline=True)
def effect_list_available(a):
    tsv = TSV.get()
    out = []
    for reg, r in sorted(tsv.registry.items()):
        if a.get("category") and a["category"].lower() not in r["category"].lower():
            continue
        if a.get("contains") and a["contains"].lower() not in (reg + " " + r["name"]).lower():
            continue
        if a.get("kind") and r["kind"] != a["kind"]:
            continue
        out.append({"regId": reg, "name": r["name"], "category": r["category"], "kind": r["kind"]})
    return {"count": len(out), "tools": out[:400]}


@op("effect.inputs", "Offline input reference for a registry ID from the live TSV: ID, label, type, control, default, range, options.",
    [P("regId", "string", "Registry ID.", required=True), P("filter", "string", "Substring filter.")], read=True, comp=False, offline=True)
def effect_inputs(a):
    tsv = TSV.get()
    err = tsv.check_reg(a["regId"])
    if err:
        raise OpError("INVALID_ARGS", err)
    rows = list(tsv.tools.get(a["regId"], {}).get("inputs", {}).values())
    if a.get("filter"):
        q = a["filter"].lower()
        rows = [r for r in rows if q in r["id"].lower() or q in r["name"].lower()]
    return {"regId": a["regId"], "outputs": tsv.tools.get(a["regId"], {}).get("outputs"), "inputs": rows, "commonInputs": sorted(tsv.common)}


# ================================================================ transform

@op("transform.set", "Set 2D placement on a Transform or Merge (or 3D Transform3DOp on 3D tools) in friendly units: positionPx (top-left px) or position [x, y] normalized, scale (1 = 100%), rotation degrees (positive = counterclockwise), pivot, opacity (Merge Blend). Creates a Transform after `tool` when it has no transform inputs and insert: true.",
    [COMP(), TOOL(), P("position", "array", "[x, y] normalized (Y up)."), P("positionPx", "array", "[x, y] pixels, top-left origin."),
     P("scale", "number|array", "Uniform size, or [x, y]."), P("rotation", "number", "Degrees."), P("pivot", "array", "[x, y] normalized."),
     P("opacity", "number", "Merge Blend 0-1."), P("translate3d", "array", "[x, y, z] for 3D tools."), P("rotate3d", "array", "[x, y, z] degrees for 3D tools."),
     P("scale3d", "number", "Uniform 3D scale."), P("insert", "boolean", "Insert a Transform after tool when needed.")])
def transform_set(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    ins = ctx.inputs(t)
    if "Transform3DOp.Translate.X" in ins:
        vals = {}
        for key, base in (("translate3d", "Translate"), ("rotate3d", "Rotate")):
            if a.get(key):
                for ax, v in zip("XYZ", a[key]):
                    vals[f"Transform3DOp.{base}.{ax}"] = v
        if a.get("scale3d") is not None:
            vals["Transform3DOp.Scale.X"] = a["scale3d"]
        return {"tool": a["tool"], "set": {k: ctx.set_input(comp, t, k, v) for k, v in vals.items()}}
    if "Center" not in ins or "Angle" not in ins:
        if not a.get("insert"):
            raise OpError("INVALID_ARGS", f"{a['tool']} has no Center/Angle transform inputs", hint="Pass insert: true to add a Transform after it.")
        r = effect_add(ctx, comp, {"regId": "Transform", "after": a["tool"], "name": _safe(a["tool"]) + "_Xf"})
        t = comp.FindTool(r["tool"])
        ins = ctx.inputs(t)
    vals = {}
    if a.get("position"):
        vals["Center"] = a["position"]
    if a.get("positionPx"):
        vals["Center"] = {"px": a["positionPx"]}
    if a.get("scale") is not None:
        s = a["scale"]
        if isinstance(s, list):
            if "UseSizeAndAspect" in ins:
                vals.update(UseSizeAndAspect=0, XSize=s[0], YSize=s[1])
            else:
                raise OpError("INVALID_ARGS", "non-uniform scale needs a Transform tool")
        else:
            vals["Size"] = s
    if a.get("rotation") is not None:
        vals["Angle"] = a["rotation"]
    if a.get("pivot"):
        vals["Pivot"] = a["pivot"]
    if a.get("opacity") is not None:
        if "Blend" not in ins:
            raise OpError("INVALID_ARGS", "opacity needs a Merge (Blend)")
        vals["Blend"] = a["opacity"]
    name = t.GetAttrs()["TOOLS_Name"]
    return {"tool": name, "set": {k: ctx.set_input(comp, t, k, v) for k, v in vals.items()}}


# ================================================================ 3d

def _add3d(ctx, comp, reg, a, defaults):
    vals = dict(defaults)
    vals.update(a.get("inputs") or {})
    for key, base in (("translate", "Translate"), ("rotate", "Rotate")):
        if a.get(key):
            for ax, v in zip("XYZ", a[key]):
                vals[f"Transform3DOp.{base}.{ax}"] = v
    return tool_add(ctx, comp, {"regId": reg, "name": a.get("name"), "inputs": vals, **({"connect": a["connect"]} if a.get("connect") else {})})


P3D = [P("name", "string", "Tool name."), P("translate", "array", "[x, y, z] scene units."), P("rotate", "array", "[x, y, z] degrees."),
       P("inputs", "object", "Extra inputs.")]


@op("3d.add_camera", "Add a Camera3D with the film back WRITTEN explicitly: FilmGate plus ApertureW/ApertureH (pasted cameras default to FilmGate TV, 0.792 x 0.594 in, AoV 24.33; a pasted FilmGate alone reads back but keeps the TV aperture [rebuild K2]; AddTool gives BMD_URSA_4K_16x9, 0.8315 x 0.4677 in, AoV 19.26: never assume). Returns the resulting AoV and aperture for frustum math (visible height at distance d = 2*d*tan(AoV/2)).",
    [COMP()] + P3D + [P("filmGate", "string", "FilmGate option (default BMD_URSA_4K_16x9).", default="BMD_URSA_4K_16x9"),
                      P("apertureW", "number", "ApertureW inches (default 0.8315 for BMD_URSA_4K_16x9)."),
                      P("apertureH", "number", "ApertureH inches (default 0.4677 for BMD_URSA_4K_16x9)."),
                      P("focalLength", "number", "FLength mm (default 35).", default=35)])
def d3_add_camera(ctx, comp, a):
    gate = a.get("filmGate", "BMD_URSA_4K_16x9")
    vals = {"FilmGate": gate, "FLength": a.get("focalLength", 35)}
    aw, ah = a.get("apertureW"), a.get("apertureH")
    if aw is None and ah is None and gate == "BMD_URSA_4K_16x9":
        aw, ah = 0.8315, 0.4677
    if aw is not None:
        vals["ApertureW"] = aw
    if ah is not None:
        vals["ApertureH"] = ah
    r = _add3d(ctx, comp, "Camera3D", a, vals)
    t = comp.FindTool(r["tool"])
    r["aov"] = num(t.GetInput("AoV", comp.CurrentTime))
    r["aperture"] = [num(t.GetInput("ApertureW", comp.CurrentTime)), num(t.GetInput("ApertureH", comp.CurrentTime))]
    return r


@op("3d.add_imageplane", "Add an ImagePlane3D fed by an image tool (plane = 1 unit wide, height = image H/W).",
    [COMP()] + P3D + [P("image", "string", "Image tool for MaterialInput.")])
def d3_add_imageplane(ctx, comp, a):
    if a.get("image"):
        a = dict(a, connect={"MaterialInput": a["image"]})
    return _add3d(ctx, comp, "ImagePlane3D", a, {})


@op("3d.add_shape", "Add a 3D primitive: Shape3D (plane|cube|sphere|cylinder|cone|torus) or Text3D.",
    [COMP()] + P3D + [P("shape", "string", "plane|cube|sphere|cylinder|cone|torus|text.", required=True,
                        enum=("plane", "cube", "sphere", "cylinder", "cone", "torus", "text")),
                      P("text", "string", "Text for Text3D."), P("material", "string", "Image/material tool for MaterialInput.")])
def d3_add_shape(ctx, comp, a):
    if a["shape"] == "text":
        r = _add3d(ctx, comp, "Text3D", a, {"StyledText": a.get("text") or "TEXT"})
    else:
        sh = {"plane": "SurfacePlaneInputs", "cube": "SurfaceCubeInputs", "sphere": "SurfaceSphereInputs", "cylinder": "SurfaceCylinderInputs",
              "cone": "SurfaceConeInputs", "torus": "SurfaceTorusInputs"}[a["shape"]]
        r = _add3d(ctx, comp, "Shape3D", dict(a, connect={"MaterialInput": a["material"]} if a.get("material") else None), {"Shape": sh})
    return r


@op("3d.add_light", "Add a 3D light (ambient|directional|point|spot). Lighting needs the renderer's lighting enabled.",
    [COMP()] + P3D + [P("type", "string", "Light type.", required=True, enum=("ambient", "directional", "point", "spot")),
                      P("color", "string|array", "Light color."), P("intensity", "number", "Intensity.")])
def d3_add_light(ctx, comp, a):
    reg = {"ambient": "LightAmbient", "directional": "LightDirectional", "point": "LightPoint", "spot": "LightSpot"}[a["type"]]
    vals = {}
    if a.get("color") is not None:
        c = color(a["color"])
        vals.update(Red=c[0], Green=c[1], Blue=c[2])
    if a.get("intensity") is not None:
        vals["Intensity"] = a["intensity"]
    return _add3d(ctx, comp, reg, a, vals)


@op("3d.add_merge", "Add a Merge3D and connect scene inputs (SceneInput1..N) in order.",
    [COMP(), P("name", "string", "Tool name."), P("inputs", "array", "3D tool names to connect.", required=True)])
def d3_add_merge(ctx, comp, a):
    r = tool_add(ctx, comp, {"regId": "Merge3D", "name": a.get("name")})
    t = comp.FindTool(r["tool"])
    r["scene"] = []
    for n, src in enumerate(a["inputs"]):
        iid = "SceneInput%d" % (n + 1)
        if iid not in ctx.inputs(t):
            t.Refresh()
            t = comp.FindTool(r["tool"])
        r["scene"].append(ctx.connect(t, iid, ctx.tool(comp, src)))
    return r


@op("3d.add_renderer", "Add a Renderer3D with an EXPLICIT output size (UseFrameFormatSettings 1 = comp size, or width/height): pasted renderers default to 320x240. rendererType OpenGL for DOF/supersampling, Software for soft shadows.",
    [COMP(), P("name", "string", "Tool name."), P("scene", "string", "Merge3D/3D tool to render.", required=True),
     P("rendererType", "string", "RendererSoftware|RendererOpenGL|RendererOpenGLUV.", default="RendererOpenGL"),
     P("width", "integer", "Explicit width (else comp size)."), P("height", "integer", "Explicit height."), P("camera", "string", "CameraSelector option.")])
def d3_add_renderer(ctx, comp, a):
    vals = {"RendererType": a.get("rendererType", "RendererOpenGL")}
    if a.get("width") and a.get("height"):
        vals.update(UseFrameFormatSettings=0, Width=a["width"], Height=a["height"])
    else:
        vals["UseFrameFormatSettings"] = 1
    r = tool_add(ctx, comp, {"regId": "Renderer3D", "name": a.get("name"), "inputs": vals, "connect": {"SceneInput": a["scene"]}})
    t = comp.FindTool(r["tool"])
    if a.get("camera"):
        r["camera"] = ctx.set_input(comp, t, "CameraSelector", a["camera"])
    W, H, _ = ctx.fmt(comp)
    r["size"] = [W, H] if vals.get("UseFrameFormatSettings") == 1 else [a["width"], a["height"]]
    return r


@op("3d.scene", "One call: Camera3D (explicit film back) + Merge3D of the given 3D tools + Renderer3D (explicit size). Returns the renderer to composite.",
    [COMP(), P("prefix", "string", "Name prefix (default 'Scene_').", default="Scene_"), P("objects", "array", "3D tool names to merge.", required=True),
     P("cameraZ", "number", "Camera Z (default 3).", default=3), P("focalLength", "number", "mm (default 35).", default=35),
     P("rendererType", "string", "Renderer type (default RendererOpenGL).", default="RendererOpenGL")])
def d3_scene(ctx, comp, a):
    pre = a.get("prefix", "Scene_")
    cam = d3_add_camera(ctx, comp, {"name": pre + "Cam", "translate": [0, 0, a.get("cameraZ", 3)], "focalLength": a.get("focalLength", 35)})
    mg = d3_add_merge(ctx, comp, {"name": pre + "Merge3D", "inputs": list(a["objects"]) + [cam["tool"]]})
    rd = d3_add_renderer(ctx, comp, {"name": pre + "Render", "scene": mg["tool"], "rendererType": a.get("rendererType", "RendererOpenGL")})
    return {"camera": cam, "merge3d": mg["tool"], "renderer": rd["tool"], "size": rd["size"]}


# ================================================================ media (footage) / item (media pool)

@op("media.add_loader", "Add a Loader for a still/EXR/image sequence (Loader in Resolve is for stills/EXR; video comes in through MediaIn). Lock suppresses the file dialog; Clip is read back.",
    [COMP(), P("path", "string", "Absolute file path.", required=True), P("name", "string", "Tool name.")])
def media_add_loader(ctx, comp, a):
    if not os.path.exists(a["path"]):
        raise OpError("NOT_FOUND", f"no file {a['path']}")
    return tool_add(ctx, comp, {"regId": "Loader", "name": a.get("name"), "inputs": {"Clip": a["path"]}})


@op("media.add_mediain", "Add a MediaIn reading a Media Pool clip (MediaSource MediaPool + MediaID). Find clips with item.list.",
    [COMP(), P("clip", "string", "Media Pool clip name (or media ID).", required=True), P("name", "string", "Tool name.")])
def media_add_mediain(ctx, comp, a):
    mpi = _find_clip(ctx, a["clip"])
    r = tool_add(ctx, comp, {"regId": "MediaIn", "name": a.get("name")})
    t = comp.FindTool(r["tool"])
    t.SetInput("MediaSource", "MediaPool")
    t.SetInput("MediaID", mpi.GetMediaId())
    t.SetInput("ClipName", mpi.GetName())
    r.update(mediaId=jv(t.GetInput("MediaID", comp.CurrentTime)), source=jv(t.GetInput("MediaSource", comp.CurrentTime)),
             clip=mpi.GetName())
    return r


@op("media.replace", "Relink a Loader to another file (Clip) or a MediaIn to another Media Pool clip; downstream wiring and animation stay.",
    [COMP(), TOOL("Loader or MediaIn."), P("path", "string", "New file (Loader)."), P("clip", "string", "Media Pool clip (MediaIn).")])
def media_replace(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    reg = t.GetAttrs()["TOOLS_RegID"]
    if reg == "Loader":
        if not a.get("path") or not os.path.exists(a["path"]):
            raise OpError("INVALID_ARGS", "Loader needs an existing path")
        return {"Clip": ctx.set_input(comp, t, "Clip", a["path"])}
    if reg == "MediaIn":
        mpi = _find_clip(ctx, a.get("clip") or "")
        t.SetInput("MediaSource", "MediaPool")
        t.SetInput("MediaID", mpi.GetMediaId())
        t.SetInput("ClipName", mpi.GetName())
        return {"MediaID": jv(t.GetInput("MediaID", comp.CurrentTime)), "clip": mpi.GetName()}
    raise OpError("INVALID_ARGS", f"{a['tool']} is {reg}; expected Loader or MediaIn")


@op("media.list", "List Loader/MediaIn/Saver tools in the comp with their files/clips, flagging missing Loader files.", [COMP()], read=True)
def media_list(ctx, comp, a):
    out = []
    for t in (comp.GetToolList(False) or {}).values():
        ta = t.GetAttrs()
        reg = ta["TOOLS_RegID"]
        if reg == "Loader":
            p = t.GetInput("Clip", comp.CurrentTime)
            out.append({"tool": ta["TOOLS_Name"], "regId": reg, "path": p, "missing": bool(p) and not os.path.exists(str(p))})
        elif reg == "MediaIn":
            out.append({"tool": ta["TOOLS_Name"], "regId": reg, "clip": t.GetInput("ClipName", comp.CurrentTime),
                        "source": t.GetInput("MediaSource", comp.CurrentTime), "mediaId": t.GetInput("MediaID", comp.CurrentTime)})
        elif reg == "Saver":
            out.append({"tool": ta["TOOLS_Name"], "regId": reg, "path": t.GetInput("Clip", comp.CurrentTime)})
    return {"media": out}


def _walk_pool(folder, path=""):
    for c in folder.GetClipList() or []:
        yield path, c
    for sub in folder.GetSubFolderList() or []:
        yield from _walk_pool(sub, path + "/" + sub.GetName())


def _find_clip(ctx, name):
    mp = ctx.project().GetMediaPool()
    hits = [c for _, c in _walk_pool(mp.GetRootFolder()) if c.GetName() == name or c.GetMediaId() == name]
    if not hits:
        names = [c.GetName() for _, c in _walk_pool(mp.GetRootFolder())]
        s = suggest(name, names)
        raise OpError("NOT_FOUND", f"no Media Pool clip '{name}'" + (f" - did you mean '{s}'?" if s else ""))
    return hits[0]


@op("item.list", "List Media Pool clips (optionally in one folder / name substring / type) with media IDs and file paths.",
    [P("folder", "string", "Folder path like '/Sub/Folder' (default all)."), P("nameContains", "string", "Substring."),
     P("limit", "integer", "Max rows (default 200).", default=200)], read=True, comp=False)
def item_list(ctx, a):
    mp = ctx.project().GetMediaPool()
    out = []
    for path, c in _walk_pool(mp.GetRootFolder()):
        if a.get("folder") and not path.startswith(a["folder"].rstrip("/")):
            continue
        if a.get("nameContains") and a["nameContains"].lower() not in c.GetName().lower():
            continue
        out.append({"name": c.GetName(), "folder": path or "/", "mediaId": c.GetMediaId(),
                    "type": c.GetClipProperty("Type"), "file": c.GetClipProperty("File Path")})
        if len(out) >= int(a.get("limit", 200)):
            break
    return {"clips": out, "count": len(out)}


@op("item.import", "Import files into the Media Pool (current folder or `folder`, created if missing).",
    [P("paths", "array", "Absolute file paths.", required=True), P("folder", "string", "Media Pool subfolder name under root.")], comp=False)
def item_import(ctx, a):
    mp = ctx.project().GetMediaPool()
    for p in a["paths"]:
        if not os.path.exists(p):
            raise OpError("NOT_FOUND", f"no file {p}")
    if a.get("folder"):
        root = mp.GetRootFolder()
        sub = next((f for f in (root.GetSubFolderList() or []) if f.GetName() == a["folder"]), None) or mp.AddSubFolder(root, a["folder"])
        mp.SetCurrentFolder(sub)
    items = mp.ImportMedia(a["paths"]) or []
    return {"imported": [{"name": i.GetName(), "mediaId": i.GetMediaId()} for i in items]}


@op("item.create_folder", "Create a Media Pool subfolder (under root or a parent folder name).",
    [P("name", "string", "Folder name.", required=True), P("parent", "string", "Parent folder name under root (default root).")], comp=False)
def item_create_folder(ctx, a):
    mp = ctx.project().GetMediaPool()
    root = mp.GetRootFolder()
    parent = root
    if a.get("parent"):
        parent = next((f for f in (root.GetSubFolderList() or []) if f.GetName() == a["parent"]), None)
        if parent is None:
            raise OpError("NOT_FOUND", f"no folder '{a['parent']}' under root")
    f = mp.AddSubFolder(parent, a["name"])
    if f is None:
        raise OpError("OPERATION_FAILED", "AddSubFolder returned None")
    return {"folder": f.GetName()}


@op("item.delete", "Delete Media Pool clips by name (MediaPool.DeleteClips). Destructive: runs only with confirm: true; clips used on timelines are refused unless force.",
    [P("clips", "array", "Clip names or media IDs.", required=True), P("force", "boolean", "Delete even if used on a timeline."),
     P("confirm", "boolean", "Must be true.", required=True)], comp=False, consent=True)
def item_delete(ctx, a):
    mp = ctx.project().GetMediaPool()
    items = [_find_clip(ctx, n) for n in a["clips"]]
    if not a.get("force"):
        used = [i.GetName() for i in items if item_usages(ctx, {"clip": i.GetMediaId()})["usages"]]
        if used:
            raise OpError("FORBIDDEN", f"clips in use on timelines: {used}", hint="force: true to delete anyway")
    if not mp.DeleteClips(items):
        raise OpError("OPERATION_FAILED", "DeleteClips failed")
    return {"deleted": [n for n in a["clips"]]}


@op("item.delete_folder", "Delete an EMPTY Media Pool subfolder under root. Runs only with confirm: true.",
    [P("name", "string", "Folder name under root.", required=True), P("confirm", "boolean", "Must be true.", required=True)], comp=False, consent=True)
def item_delete_folder(ctx, a):
    mp = ctx.project().GetMediaPool()
    f = next((x for x in (mp.GetRootFolder().GetSubFolderList() or []) if x.GetName() == a["name"]), None)
    if f is None:
        raise OpError("NOT_FOUND", f"no folder '{a['name']}' under root")
    if f.GetClipList() or f.GetSubFolderList():
        raise OpError("FORBIDDEN", "folder is not empty")
    if not mp.DeleteFolders([f]):
        raise OpError("OPERATION_FAILED", "DeleteFolders failed")
    return {"deleted": a["name"]}


@op("item.usages", "Which timelines use a Media Pool clip (reverse lookup over timeline video items).",
    [P("clip", "string", "Clip name or media ID.", required=True)], read=True, comp=False)
def item_usages(ctx, a):
    mpi = _find_clip(ctx, a["clip"])
    mid = mpi.GetMediaId()
    p = ctx.project()
    out = []
    for i in range(1, p.GetTimelineCount() + 1):
        tl = p.GetTimelineByIndex(i)
        for k in range(1, tl.GetTrackCount("video") + 1):
            for j, it in enumerate(tl.GetItemListInTrack("video", k) or []):
                m = it.GetMediaPoolItem()
                if m and m.GetMediaId() == mid:
                    out.append({"timeline": tl.GetName(), "track": k, "item": j})
    return {"clip": mpi.GetName(), "usages": out}


# ================================================================ marker (timeline item markers)

MARKER_COLORS = ("Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple", "Fuchsia", "Rose", "Lavender", "Sky", "Mint", "Lemon", "Sand", "Cocoa", "Cream")


def _marker_target(ctx, a):
    if a.get("on") == "timeline":
        return ctx.timeline(a.get("timeline"))
    _, it = ctx.item({"timeline": a.get("timeline"), "item": a.get("item", 0), "track": a.get("track", 1)})
    return it


MK = [P("on", "string", "item (the clip holding the comp, frames relative to clip start; default) or timeline.", enum=("item", "timeline"), default="item"),
      P("timeline", "string", "Timeline (default current)."), P("item", "integer", "0-based V1 item index (default 0).", default=0),
      P("track", "integer", "Video track (default 1).", default=1)]


@op("marker.add", "Add a marker to the clip holding the comp (frames relative to clip start) or to the timeline. Fusion comp markers (comp.SetMarker) were probed live and ignore the time argument, so the clip marker is the model.",
    MK + [P("frame", "number", "Frame.", required=True), P("name", "string", "Name.", default=""), P("note", "string", "Note.", default=""),
          P("color", "string", "Marker color.", enum=MARKER_COLORS, default="Blue"), P("duration", "number", "Frames (default 1).", default=1),
          P("customData", "string", "Custom data.", default="")], comp=False)
def marker_add(ctx, a):
    tg = _marker_target(ctx, a)
    ok = tg.AddMarker(a["frame"], a.get("color", "Blue"), a.get("name", ""), a.get("note", ""), a.get("duration", 1), a.get("customData", ""))
    if not ok:
        raise OpError("OPERATION_FAILED", "AddMarker failed (a marker may already exist at that frame)")
    return {"markers": jv(tg.GetMarkers())}


@op("marker.list", "List markers on the clip (default) or timeline.", MK, read=True, comp=False)
def marker_list(ctx, a):
    return {"markers": jv(_marker_target(ctx, a).GetMarkers())}


@op("marker.remove", "Remove the marker at a frame (or all markers of a color with color).",
    MK + [P("frame", "number", "Marker frame."), P("color", "string", "Remove all of this color.", enum=MARKER_COLORS + ("All",))], comp=False)
def marker_remove(ctx, a):
    tg = _marker_target(ctx, a)
    if a.get("frame") is not None:
        ok = tg.DeleteMarkerAtFrame(a["frame"])
    elif a.get("color"):
        ok = tg.DeleteMarkersByColor(a["color"])
    else:
        raise OpError("INVALID_ARGS", "pass frame or color")
    if not ok:
        raise OpError("NOT_FOUND", "no marker removed")
    return {"markers": jv(tg.GetMarkers())}


@op("marker.update", "Update a marker's fields: re-adds it at the same frame with the changed name/note/color/duration/customData.",
    MK + [P("frame", "number", "Marker frame.", required=True), P("name", "string", "Name."), P("note", "string", "Note."),
          P("color", "string", "Color.", enum=MARKER_COLORS), P("duration", "number", "Frames."), P("customData", "string", "Custom data.")], comp=False)
def marker_update(ctx, a):
    tg = _marker_target(ctx, a)
    ms = tg.GetMarkers() or {}
    cur = next((v for k, v in ms.items() if float(k) == float(a["frame"])), None)
    if cur is None:
        raise OpError("NOT_FOUND", f"no marker at frame {a['frame']}", details={"markers": jv(ms)})
    new = {"color": a.get("color", cur.get("color")), "name": a.get("name", cur.get("name")), "note": a.get("note", cur.get("note")),
           "duration": a.get("duration", cur.get("duration")), "customData": a.get("customData", cur.get("customData", ""))}
    tg.DeleteMarkerAtFrame(a["frame"])
    if not tg.AddMarker(a["frame"], new["color"], new["name"], new["note"], new["duration"], new["customData"]):
        raise OpError("OPERATION_FAILED", "re-adding the marker failed", details={"previous": jv(cur)})
    return {"marker": new}


# ================================================================ render

def dismiss_modals(timeout=4.0, expect=True, enabled=True):
    """Click OK on Resolve's render modals: 'Render completed!' (every comp.Render raises one) and
    'WARNING! Render did not complete!' (a failed render). While either is up the scripting API returns
    None. Uses System Events; needs Accessibility permission for the MCP host. Off with
    FUSION_MCP_AUTO_DISMISS_RENDER_MODAL=0 (then renders leave the modal for the user).
    Returns (completed_count, [failure dialog texts])."""
    if not enabled:
        return 0, []
    t0 = time.time()
    n, fails = 0, []
    while time.time() - t0 < timeout:
        try:
            r = subprocess.run(["osascript", MODAL_SCRIPT], capture_output=True, text=True, timeout=10)
            parts = ((r.stdout or "").strip() + "||").split("|", 2)
            done, failed = int(parts[0] or 0), int(parts[1] or 0)
            texts = [x.strip() for x in parts[2].split(";;") if x.strip().strip("|")]
        except Exception:
            done, failed, texts = 0, 0, []
        n += done
        fails += texts or ["Render did not complete!"] * failed
        if n or fails or not expect:
            break
        time.sleep(0.2)
    return n, fails


def settle_render(ctx, files, auto, timeout=4.0):
    """After comp.Render: done as soon as the span's files exist and Resolve answers (a blocking modal makes GetCurrentPage None),
    so a render that raises no modal costs ~0 s here. [2026-09-27, efficiency lab] Since a Disk Cache dialog incident Resolve 21.1
    no longer shows 'Render completed!', and the old fixed 4 s wait for it ran on every render. While Resolve does not answer, the
    render modals (completed / failed) are dismissed. -> (completed dismissed, failure texts, answered)."""
    done, fails, t_end = 0, [], time.time() + timeout
    while True:
        up = ctx.resolve.GetCurrentPage() is not None
        if (up and all(os.path.exists(f) for f in files)) or fails or time.time() > t_end:
            return done, fails, up
        d, f = dismiss_modals(timeout=0.3, expect=False, enabled=auto)
        done, fails = done + d, fails + f
        if not (d or f):
            time.sleep(0.1)


RESTORE_KEY = "fc_render_restore"
RENDER_SAVER = "FC_RenderSaver"   # one Saver kept per comp between renders, parked (bypassed, no input)


def _park(sv):
    sv.ConnectInput("Input", None)
    sv.SetAttrs({"TOOLB_PassThrough": True})


def render_recover(ctx, comp):
    """Undo what an interrupted render_one left in the comp (the worker is killed on timeout, so its finally
    never ran): temporary Savers, the kept render Saver left live, passed-through Savers, render range, current time,
    MediaOut1 wiring. [rebuild B1] a timed-out render.range left its temp Saver and render range [100,104] behind."""
    raw = comp.GetData(RESTORE_KEY)
    done = {}
    keep = comp.FindTool(RENDER_SAVER)
    if keep is not None and not (keep.GetAttrs() or {}).get("TOOLB_PassThrough"):
        _park(keep)                      # a live Saver would write files during the next Deliver
        done["renderSaverParked"] = True
    tmp = [t for t in (comp.GetToolList(False, "Saver") or {}).values() if t.GetAttrs()["TOOLS_Name"].startswith("FC_TmpSaver_")]
    for t in tmp:
        t.Delete()
    if tmp:
        done["tempSaversDeleted"] = len(tmp)
    if not raw:
        return done
    try:
        d = json.loads(raw)
    except ValueError:
        d = {}
    for n in d.get("others") or []:
        t = comp.FindTool(n)
        if t is not None:
            t.SetAttrs({"TOOLB_PassThrough": False})
    if d.get("range") and None not in d["range"]:
        comp.SetAttrs({"COMPN_RenderStart": d["range"][0], "COMPN_RenderEnd": d["range"][1]})
        done["renderRange"] = d["range"]
    if d.get("time") is not None:
        comp.CurrentTime = d["time"]
    mo_d = d.get("mediaOut")
    mo = comp.FindTool("MediaOut1")
    if mo_d is not None and mo is not None:
        src = comp.FindTool(mo_d["source"]) if mo_d.get("source") else None
        if src is not None:
            try:
                ctx.connect(mo, "Input", src, mo_d.get("output") if mo_d.get("output") not in (None, "Output") else None)
            except OpError:
                mo.ConnectInput("Input", src)
        else:
            mo.ConnectInput("Input", None)
        done["mediaOut1"] = mo_d.get("source")
    comp.SetData(RESTORE_KEY, "")
    return done


def render_one(ctx, comp, src, frame, out_path, frames=None, isolate=True, quality="final"):
    """Render src (tool) through the comp's render Saver (FC_RenderSaver, created once, parked bypassed with no input
    between renders) to PNG. Other Savers are passed through, current time and render range are restored, the completion
    modal (if Resolve raises one) is dismissed. Returns path(s).
    isolate: [rebuild K11] comp.Render in Resolve also renders MediaOut1's chain, so MediaOut1 is pointed at src
    for the render and restored after (a small tool rendered in 3 s instead of minutes). The restore state is
    stored in the comp first, so render.cancel (or the next render) can repair an interrupted render."""
    frames = frames or [frame]
    rec = render_recover(ctx, comp)
    if rec:
        ctx.notes.append("repaired leftovers of an interrupted render: %s" % json.dumps(rec))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    stem = os.path.join(os.path.dirname(out_path), "fc_" + uuid.uuid4().hex[:8] + "_")
    at = comp.GetAttrs()
    keep = (comp.CurrentTime, at.get("COMPN_RenderStart"), at.get("COMPN_RenderEnd"))
    others = []
    for t in (comp.GetToolList(False, "Saver") or {}).values():
        ta = t.GetAttrs()
        if ta.get("TOOLS_Name") != RENDER_SAVER and not ta.get("TOOLB_PassThrough"):
            t.SetAttrs({"TOOLB_PassThrough": True})
            others.append(t)
    mo = comp.FindTool("MediaOut1") if isolate else None
    mo_src = ctx.source_of(mo, "Input") if mo is not None else None
    src_name = src.GetAttrs()["TOOLS_Name"]
    repoint = mo is not None and (mo_src is None or mo_src[0] != src_name) and src_name != "MediaOut1"
    state = {"others": [t.GetAttrs()["TOOLS_Name"] for t in others], "range": [keep[1], keep[2]], "time": keep[0]}
    if repoint:
        state["mediaOut"] = {"source": mo_src[0] if mo_src else None, "output": mo_src[1] if mo_src else None}
    comp.SetData(RESTORE_KEY, json.dumps(state))
    sv = None
    produced = []
    try:
        if repoint:
            try:
                ctx.connect(mo, "Input", src)
            except OpError:
                state.pop("mediaOut", None)
                comp.SetData(RESTORE_KEY, json.dumps(state))
                repoint = False
                ctx.notes.append("MediaOut1 could not take %s's output; it kept its source (the render also pays for MediaOut1's chain)" % src_name)
        # [efficiency lab H] reuse one Saver per comp: add_tool reads every tool's name twice (seconds on a big comp) and
        # add + delete per call was most of render.frame's 1.5-5 s overhead
        sv = comp.FindTool(RENDER_SAVER)
        if sv is None:
            sv = ctx.add_tool(comp, "Saver", RENDER_SAVER)
        sv.SetAttrs({"TOOLB_PassThrough": False})
        ctx.connect(sv, "Input", src)
        sv.SetInput("Clip", stem + ".png")
        sv.SetInput("OutputFormat", "PNGFormat")
        f0, f1 = min(frames), max(frames)
        contiguous = sorted(set(frames)) == list(range(int(f0), int(f1) + 1))
        spans = [(f0, f1)] if contiguous else [(f, f) for f in sorted(set(frames))]
        for s, e in spans:
            args = {"Start": s, "End": e, "Wait": True}
            if quality == "draft":
                # efficiency lab DRAFT: HiQ off + motion blur off = 3-7x faster on a heavy 3D frame; still frames match final within
                # MAE 0.03, moving frames lose only their blur (positions exact). Proxy/SizeType keys are ignored by Resolve.
                args.update(HiQ=False, MotionBlur=False)
            ok = comp.Render(args)
            auto = ctx.policy.get("auto_dismiss", True)
            done, fails, up = settle_render(ctx, ["%s%04d.png" % (stem, int(f)) for f in range(int(s), int(e) + 1) if f in frames], auto)
            if fails or not ok:
                raise OpError("RENDER_FAILED", "render of %s, frames %s-%s, did not complete" % (src_name, s, e),
                              hint="The source tool produced no image (tool error, missing input, or nothing in that frame range). "
                                   "Resolve's failure dialog was dismissed; check the tool with fu_tool_info or viewer.view.",
                              details={"dialog": fails, "renderReturned": bool(ok)})
            if not up:
                ctx.notes.append("Resolve did not answer after the render and no render modal was found to dismiss" +
                                 (" (check Accessibility permission)" if auto else " (auto-dismiss is OFF: close Resolve's render dialog)"))
        for f in sorted(set(frames)):
            got = "%s%04d.png" % (stem, int(f))
            if not os.path.exists(got):
                raise OpError("OPERATION_FAILED", f"render reported success but {got} is missing",
                              hint="Render True is not proof (realities §10); check the Saver path and the source tool.")
            produced.append((f, got))
    finally:
        if sv is not None:
            _park(sv)
        render_recover(ctx, comp)
    if repoint:
        ctx.notes.append("MediaOut1 -> %s for the render (restored)" % src_name)
    if len(frames) == 1:
        os.replace(produced[0][1], out_path)
        return out_path
    return produced


COST_KEY = "fc_render_spf"


def _note_render_cost(comp, spf):
    """Keep the slowest seconds-per-frame a connector render measured in this comp (deliver.start reads it)."""
    try:
        prev = float(comp.GetData(COST_KEY) or 0)
        if spf > prev:
            comp.SetData(COST_KEY, str(round(spf, 2)))
    except Exception:  # noqa
        pass


def cache_warnings(ctx, comp):
    """STALE disk caches of the rendered comp (cache.*): a render through a stale cache shows old pixels. Never fails a render."""
    from .cache import render_warnings
    try:
        return render_warnings(ctx, comp)
    except Exception as e:  # noqa
        return ["disk caches not checked: %s" % e]


def _default_src(ctx, comp, name):
    if name:
        return ctx.tool(comp, name)
    mo = comp.FindTool("MediaOut1")
    s = ctx.source_of(mo, "Input") if mo else None
    if not s:
        raise OpError("INVALID_ARGS", "no tool given and MediaOut1.Input is not connected", hint="Pass tool.")
    return comp.FindTool(s[0])


def _preview(path, max_px):
    if not max_px:
        return None
    from .visual import preview
    return preview(path, int(max_px))


QUALITY = P("quality", "string", "final (default): the delivered look. draft: HiQ off + motion blur off, 3-7x faster; judge layout, timing, text "
            "and colour from it, never blur, DOF, glow softness or fine edges (efficiency lab).", enum=("final", "draft"), default="final")
ISOLATE = P("isolate", "boolean", "Point MediaOut1 at the rendered tool for the render, then restore it (default true): comp.Render in Resolve also renders MediaOut1's chain, so without this a small tool pays for the whole comp.", default=True)


@op("render.cancel", "Abort a comp render (comp.AbortRender) and repair what an interrupted render.frame/range/contact_sheet/compare left behind: temporary Saver, passed-through Savers, render range, current time, MediaOut1 wiring (the worker is killed on a timeout, so its cleanup never ran). Runs without the UI check. A Deliver-page render is deliver.stop instead.",
    [COMP(), P("wait", "number", "Seconds to wait for the render to stop (default 10).", default=10)], undo=False, ui=False)
def render_cancel(ctx, comp, a):
    at = comp.GetAttrs() or {}
    was = bool(at.get("COMPB_Rendering"))
    if was:
        comp.AbortRender()
        t_end = time.time() + float(a.get("wait", 10))
        while time.time() < t_end and (comp.GetAttrs() or {}).get("COMPB_Rendering"):
            time.sleep(0.5)
    n, fails = dismiss_modals(timeout=1.0, expect=False, enabled=ctx.policy.get("auto_dismiss", True))
    still = bool((comp.GetAttrs() or {}).get("COMPB_Rendering"))
    # never delete the temp Saver under a running render: repair only once it has stopped
    return {"wasRendering": was, "stillRendering": still, "repaired": None if still else render_recover(ctx, comp),
            "dialogsDismissed": n + len(fails),
            "note": ("AbortRender did not stop it yet: the in-flight frame usually finishes first (under memory pressure this took minutes "
                     "in the rebuild); check system.memory, wait, then call render.cancel again to repair the comp") if still else None}


@op("render.frame", "Render one frame of a tool (default: what feeds MediaOut1) to PNG through the comp's render Saver (FC_RenderSaver, kept bypassed with no input between renders); returns the file (full res) and, inline, a downscaled 8-bit preview image so you SEE the result in the same call. Render True is not trusted: the file is checked. Resolve's completion modal is dismissed; time/render range restored; other Savers untouched.",
    [COMP(), P("tool", "string", "Tool to render (default MediaOut1's source)."), FRAME,
     P("outPath", "string", "Absolute .png path (default out/<tool>_<frame>.png)."),
     P("previewMaxPx", "integer", "Long edge of the preview (default 960)."),
     P("inline", "boolean", "Return the preview as an image (default true).", default=True), ISOLATE, QUALITY],
    undo="discard")
def render_frame(ctx, comp, a):
    src = _default_src(ctx, comp, a.get("tool"))
    f = a.get("frame", comp.CurrentTime)
    name = src.GetAttrs()["TOOLS_Name"]
    path = _out(a.get("outPath"), "%s_%04d.png" % (_safe(name), int(f)))
    t0 = time.time()
    q = a.get("quality", "final")
    render_one(ctx, comp, src, f, path, isolate=a.get("isolate", True), quality=q)
    info = png_info(path)
    inline = a.get("inline", True)
    pv = _preview(path, a.get("previewMaxPx") or (960 if inline else None))
    secs = round(time.time() - t0, 2)
    if q == "final":
        _note_render_cost(comp, secs)   # draft timings would under-state the Deliver preflight
    out = {"path": path, "tool": name, "frame": f, "quality": q, "width": info["width"], "height": info["height"], "bytes": os.path.getsize(path), "preview": pv,
           "renderSeconds": secs, "comp": ctx.identity(comp), "memory": sysmem.brief()}
    warn = cache_warnings(ctx, comp)
    if warn:
        out["warnings"] = warn
    if inline and pv:
        out["_inline"] = [pv]
    return out


@op("render.range", "Render a frame range (or list) of a tool to a PNG sequence in one Render call per contiguous span. inline returns up to 8 small previews; for a whole-motion overview use render.contact_sheet.",
    [COMP(), P("tool", "string", "Tool (default MediaOut1's source)."), P("start", "number", "First frame."), P("end", "number", "Last frame."),
     P("step", "integer", "Every Nth frame (default 1).", default=1), P("frames", "array", "Explicit frame list (instead of start/end)."),
     P("outDir", "string", "Absolute directory (default out/<tool>_seq)."), P("previewMaxPx", "integer", "Preview size (default 480 when inline)."),
     P("inline", "boolean", "Return up to 8 previews as images (default false)."), ISOLATE, QUALITY], undo="discard")
def render_range(ctx, comp, a):
    src = _default_src(ctx, comp, a.get("tool"))
    name = src.GetAttrs()["TOOLS_Name"]
    if a.get("frames"):
        frames = [float(f) for f in a["frames"]]
    else:
        at = comp.GetAttrs()
        s = a.get("start", at["COMPN_GlobalStart"])
        e = a.get("end", at["COMPN_GlobalEnd"])
        frames = [float(f) for f in range(int(s), int(e) + 1, int(a.get("step", 1)))]
    if len(frames) > 2000:
        raise OpError("INVALID_ARGS", "more than 2000 frames; use deliver.* for long renders")
    d = a.get("outDir") or os.path.join(config.out_dir(), _safe(name) + "_seq")
    os.makedirs(d, exist_ok=True)
    t0 = time.time()
    q = a.get("quality", "final")
    produced = render_one(ctx, comp, src, frames[0], os.path.join(d, "x.png"), frames=frames, isolate=a.get("isolate", True), quality=q)
    if isinstance(produced, str):
        produced = [(frames[0], produced)]
    secs = time.time() - t0
    out = []
    inline = a.get("inline", False)
    for n, (f, p) in enumerate(produced):
        dst = os.path.join(d, "%s_%04d.png" % (_safe(name), int(f)))
        os.replace(p, dst)
        pv = _preview(dst, a.get("previewMaxPx") or (480 if inline and n < 8 else None))
        out.append({"frame": f, "path": dst, "preview": pv})
    if q == "final":
        _note_render_cost(comp, secs / max(1, len(out)))
    res = {"frames": out, "count": len(out), "quality": q, "secondsPerFrame": round(secs / max(1, len(out)), 2), "comp": ctx.identity(comp), "memory": sysmem.brief()}
    warn = cache_warnings(ctx, comp)
    if warn:
        res["warnings"] = warn
    if inline:
        res["_inline"] = [r["preview"] for r in out[:8] if r["preview"]]
    return res


# ================================================================ deliver (Resolve render queue)

@op("deliver.list_presets", "Render presets, formats and codecs available on the Deliver page.",
    [P("format", "string", "Also list codecs for this format.")], read=True, comp=False)
def deliver_list_presets(ctx, a):
    p = ctx.project()
    out = {"presets": jv(p.GetRenderPresetList()), "formats": jv(p.GetRenderFormats()),
           "current": jv(p.GetCurrentRenderFormatAndCodec()), "mode": p.GetCurrentRenderMode()}
    if a.get("format"):
        out["codecs"] = jv(p.GetRenderCodecs(a["format"]))
    return out


@op("deliver.add_job", "Queue a Deliver-page render job for a timeline (optionally a preset, format/codec, frame range, target dir and name). Returns the job ID.",
    [P("timeline", "string", "Timeline (default current)."), P("preset", "string", "Render preset name."),
     P("format", "string", "Format (e.g. mov, mp4)."), P("codec", "string", "Codec (e.g. H264, ProRes422HQ)."),
     P("targetDir", "string", "Absolute output directory (default out/deliver).", ), P("name", "string", "Custom file name."),
     P("markIn", "integer", "First timeline frame."), P("markOut", "integer", "Last timeline frame."),
     P("settings", "object", "Extra SetRenderSettings keys.")], comp=False)
def deliver_add_job(ctx, a):
    p = ctx.project()
    tl = ctx.timeline(a.get("timeline"))
    p.SetCurrentTimeline(tl)
    if a.get("preset") and not p.LoadRenderPreset(a["preset"]):
        raise OpError("NOT_FOUND", f"render preset '{a['preset']}' not found", details={"presets": jv(p.GetRenderPresetList())})
    if a.get("format") and a.get("codec") and not p.SetCurrentRenderFormatAndCodec(a["format"], a["codec"]):
        raise OpError("INVALID_ARGS", f"format/codec {a['format']}/{a['codec']} rejected")
    d = a.get("targetDir") or os.path.join(config.out_dir(), "deliver")
    os.makedirs(d, exist_ok=True)
    st = {"TargetDir": d}
    if a.get("name"):
        st["CustomName"] = a["name"]
    if a.get("markIn") is not None:
        st["MarkIn"] = a["markIn"]
    if a.get("markOut") is not None:
        st["MarkOut"] = a["markOut"]
    st.update(a.get("settings") or {})
    if not p.SetRenderSettings(st):
        raise OpError("INVALID_ARGS", "SetRenderSettings rejected the settings", details={"settings": st})
    jid = p.AddRenderJob()
    if not jid:
        raise OpError("OPERATION_FAILED", "AddRenderJob returned nothing")
    return {"jobId": jid, "settings": st, "format": jv(p.GetCurrentRenderFormatAndCodec())}


@op("deliver.list_jobs", "List queued render jobs. Works while Resolve renders.", [], read=True, comp=False, ui=False)
def deliver_list_jobs(ctx, a):
    return {"jobs": jv(ctx.project().GetRenderJobList())}


def deliver_progress(ctx, p, job_id=None):
    """Render-queue progress readable DURING a Deliver render (no UI needed) [rebuild F13, CU1-CU4]:
    status, percent, ETA, approximate current frame (percent x the job's frame span), output file size and age,
    and seconds per frame from the previous poll in this worker."""
    if p is None:
        return {"rendering": None}
    out = {"rendering": bool(p.IsRenderingInProgress())}
    samples = ctx.__dict__.setdefault("deliver_samples", {})
    rows = []
    for j in jv(p.GetRenderJobList()) or []:
        jid = j.get("JobId")
        if job_id and jid != job_id:
            continue
        st = jv(p.GetRenderJobStatus(jid)) or {}
        row = {"jobId": jid, "timeline": j.get("TimelineName"), "status": st.get("JobStatus"), "percent": st.get("CompletionPercentage")}
        if st.get("EstimatedTimeRemainingInMs") is not None:
            row["etaSeconds"] = round(st["EstimatedTimeRemainingInMs"] / 1000)
        if st.get("TimeTakenToRenderInMs") is not None:
            row["tookSeconds"] = round(st["TimeTakenToRenderInMs"] / 1000, 1)
        if st.get("Error"):
            row["error"] = st["Error"]
        mi, mo_, pct = j.get("MarkIn"), j.get("MarkOut"), st.get("CompletionPercentage")
        if isinstance(mi, (int, float)) and isinstance(mo_, (int, float)) and isinstance(pct, (int, float)):
            total = int(mo_ - mi + 1)
            row["frames"] = total
            row["approxFrame"] = min(total - 1, int(total * pct / 100))  # 0-based within the job (1 % = total/100 frames)
            now = time.time()
            prev = samples.get(jid)
            if prev and row["approxFrame"] > prev[1]:
                row["secondsPerFrame"] = round((now - prev[0]) / (row["approxFrame"] - prev[1]), 2)
            if prev and row["approxFrame"] == prev[1] and st.get("JobStatus") in ("Rendering", "Cancelled") and out["rendering"]:
                row["noProgressForSeconds"] = round(now - prev[0])
            if not prev or row["approxFrame"] != prev[1]:
                samples[jid] = (now, row["approxFrame"])
        f = os.path.join(j.get("TargetDir") or "", j.get("OutputFilename") or "")
        if j.get("OutputFilename") and os.path.exists(f):
            row["output"] = {"path": f, "mb": round(os.path.getsize(f) / 1e6, 1), "modifiedSecondsAgo": round(time.time() - os.path.getmtime(f))}
        rows.append(row)
    out["jobs"] = [r for r in rows if r["status"] == "Rendering"] + [r for r in rows if r["status"] != "Rendering"]
    started = ctx.__dict__.get("deliver_started", {})
    for r in rows:
        t0 = started.get(r["jobId"]) or started.get("*")
        if t0 and r.get("status") == "Rendering" and not r.get("percent"):
            r["secondsWithoutAFrame"] = round(time.time() - t0)
    stuck = [r for r in rows if r.get("noProgressForSeconds", 0) > 60 or r.get("secondsWithoutAFrame", 0) > 60]
    if stuck:
        out["note"] = ("no frame finished for over 60 s: a very slow frame, or memory pressure (check system.memory). Prefer letting it "
                       "finish: deliver.stop does not interrupt the in-flight frame (a stop on a stuck CPU-heavy frame kept Resolve busy "
                       "~8 min and it then crashed, gap-fix pass). If Resolve looks stuck, tell the user rather than retrying.")
    return out


@op("deliver.status", "Deliver progress, readable WHILE Resolve renders (every other call then returns RENDERING): per job status, percent, ETA, approximate current frame, seconds per frame between polls, output file size/age, and Resolve memory. jobId limits it to one job.",
    [P("jobId", "string", "Job ID.")], read=True, comp=False, ui=False)
def deliver_status(ctx, a):
    out = deliver_progress(ctx, ctx.project(), a.get("jobId"))
    out["memory"] = sysmem.brief()
    return out


def _job_comps(p, ids):
    """(timeline, track, item index, item, comp) for every Fusion comp on the jobs' timelines."""
    names = {j.get("TimelineName") for j in (jv(p.GetRenderJobList()) or []) if not ids or j.get("JobId") in ids}
    for i in range(1, p.GetTimelineCount() + 1):
        tl = p.GetTimelineByIndex(i)
        if tl.GetName() not in names:
            continue
        for k in range(1, (tl.GetTrackCount("video") or 0) + 1):
            for j, it in enumerate(tl.GetItemListInTrack("video", k) or []):
                for ci in range(1, (it.GetFusionCompCount() or 0) + 1):
                    c = it.GetFusionCompByIndex(ci)
                    if c:
                        yield tl, k, j, it, c


def _slow_comps(ctx, p, ids):
    """Comps on the jobs' timelines whose connector renders measured slow frames (seconds per Saver-rendered frame)."""
    out = []
    for tl, k, j, it, c in _job_comps(p, ids):
        spf = float(c.GetData(COST_KEY) or 0)
        if spf >= 20:
            out.append({"timeline": tl.GetName(), "track": k, "item": j, "clip": it.GetName(), "slowestSecondsPerFrame": spf})
    return out


def _stale_caches(ctx, p, ids):
    """Disk caches (cache.*) on the jobs' timelines whose upstream changed since they were rendered (bridge fingerprint)."""
    from .cache import check, load
    out = []
    for tl, k, j, it, c in _job_comps(p, ids):
        for name, e in load(c).items():
            r = check(ctx, c, e, current=False) if c.FindTool(name) is not None else {"stale": True, "changed": [name]}
            if r["stale"]:
                out.append({"timeline": tl.GetName(), "track": k, "item": j, "clip": it.GetName(), "cache": e["loader"], "changed": r["changed"][:5]})
    return out


@op("deliver.start", "Start rendering jobs named by jobIds (required; all: true starts every queued job). Refuses to overwrite an existing output file unless overwrite: true [2026-09-27: a bare start ran a stale queued job and overwrote a verified MP4]. Preflight: comps on the job's timeline whose connector renders measured 20+ s per frame are listed, and 60+ s refuses without confirm: true; a STALE disk cache (cache.*) on the timeline refuses without confirm: true [live, gapfix pass: stopping a Deliver stuck in one slow frame kept Resolve rendering ~8 min, then Resolve crashed]. wait: poll until done (bounded by the call timeout). While it renders, poll deliver.status; deliver.stop cancels between frames only in effect.",
    [P("jobIds", "array", "Job IDs to start (required unless all: true)."), P("all", "boolean", "Start every queued job."),
     P("overwrite", "boolean", "Allow jobs whose output file already exists."), P("wait", "boolean", "Block until finished."),
     P("confirm", "boolean", "Start even though a comp measured 60+ s per frame or a disk cache is stale.")], comp=False)
def deliver_start(ctx, a):
    p = ctx.project()
    ids = a.get("jobIds") or []
    if not ids and a.get("all") is not True:
        raise OpError("INVALID_ARGS", "deliver.start needs jobIds (or all: true)",
                      hint="Other jobs may sit in the queue with outputs you must not overwrite; list them with deliver.list_jobs.")
    jobs = [j for j in (jv(p.GetRenderJobList()) or []) if not ids or j.get("JobId") in ids]
    if a.get("overwrite") is not True:
        import glob as _glob
        clash = []
        for j in jobs:
            d, n = j.get("TargetDir") or "", j.get("OutputFilename") or ""
            if d and n and _glob.glob(os.path.join(d, n) + "*"):
                clash.append({"jobId": j.get("JobId"), "timeline": j.get("TimelineName"), "output": os.path.join(d, n)})
        if clash:
            raise OpError("FORBIDDEN", "output file already exists for %d job(s)" % len(clash), details={"jobs": clash},
                          hint="Pick a new output name (versioned), or pass overwrite: true if replacing it is intended.")
    slow = _slow_comps(ctx, p, ids)
    worst = max([s_["slowestSecondsPerFrame"] for s_ in slow] or [0])
    if worst >= 60 and a.get("confirm") is not True:
        raise OpError("FORBIDDEN", f"a comp on this timeline rendered at {worst:.0f} s per frame through the connector",
                      hint="Make it cheaper first (texture hold, fewer samples, GPU tools) or pass confirm: true. Do not plan to stop a Deliver "
                           "mid-frame: the in-flight frame finishes first (minutes) and a heavy one crashed Resolve in the gap-fix pass.",
                      details={"slowComps": slow})
    for _tl, _k, _j, _it, c in _job_comps(p, ids):   # an interrupted render.* can leave the kept Saver live: it would write every frame
        sv = c.FindTool(RENDER_SAVER)
        if sv is not None and not (sv.GetAttrs() or {}).get("TOOLB_PassThrough"):
            _park(sv)
            ctx.notes.append("parked %s in %s before Deliver" % (RENDER_SAVER, _it.GetName()))
    stale = _stale_caches(ctx, p, ids)
    if stale and a.get("confirm") is not True:
        raise OpError("FORBIDDEN", f"{len(stale)} disk cache(s) on this timeline are STALE: Deliver would write their old pixels",
                      hint="cache.refresh (re-render) or cache.restore (live branch back) on those comps, or pass confirm: true.",
                      details={"staleCaches": stale})
    ok = p.StartRendering(ids) if ids else p.StartRendering()
    if not ok:
        raise OpError("OPERATION_FAILED", "StartRendering returned False")
    ctx.__dict__.setdefault("deliver_started", {}).update({j: time.time() for j in ids} or {"*": time.time()})
    if a.get("wait"):
        while p.IsRenderingInProgress():
            time.sleep(0.5)
    out = {"started": True, "rendering": bool(p.IsRenderingInProgress()),
           "status": {j: jv(p.GetRenderJobStatus(j)) for j in ids}, "memory": sysmem.brief()}
    if slow:
        out["slowComps"] = slow
    if stale:
        out["staleCaches"] = stale
    return out


@op("deliver.stop", "Stop the Deliver render. Works while Resolve renders. [rebuild F13] The job reads Cancelled at once, but Resolve finishes the in-flight frame first (IsRenderingInProgress stays true; minutes under memory pressure): poll deliver.status until rendering is false.",
    [P("wait", "number", "Seconds to wait for rendering to end (default 5).", default=5)], comp=False, ui=False)
def deliver_stop(ctx, a):
    p = ctx.project()
    if not p.IsRenderingInProgress():
        return dict(deliver_progress(ctx, p), note="nothing was rendering; no stop sent")
    p.StopRendering()  # sent once: repeated stops do not speed up the in-flight frame
    t_end = time.time() + float(a.get("wait", 5))
    while time.time() < t_end and p.IsRenderingInProgress():
        time.sleep(0.5)
    out = deliver_progress(ctx, p)
    if out.get("rendering"):
        out["note"] = "stop requested; Resolve is finishing the in-flight frame. Poll deliver.status until rendering is false."
    return out


@op("deliver.remove_job", "Remove one render job by ID.", [P("jobId", "string", "Job ID.", required=True)], comp=False)
def deliver_remove_job(ctx, a):
    if not ctx.project().DeleteRenderJob(a["jobId"]):
        raise OpError("NOT_FOUND", f"no job {a['jobId']}")
    return {"removed": a["jobId"], "jobs": jv(ctx.project().GetRenderJobList())}


@op("deliver.set_format", "Set the current render format and codec.", [P("format", "string", "Format.", required=True), P("codec", "string", "Codec.", required=True)], comp=False)
def deliver_set_format(ctx, a):
    p = ctx.project()
    if not p.SetCurrentRenderFormatAndCodec(a["format"], a["codec"]):
        raise OpError("INVALID_ARGS", "format/codec rejected", details={"formats": jv(p.GetRenderFormats())})
    return {"current": jv(p.GetCurrentRenderFormatAndCodec())}


@op("deliver.save_preset", "Save the current render settings as a named preset (user-level, persists beyond the project). Runs only with confirm: true.",
    [P("name", "string", "Preset name.", required=True), P("confirm", "boolean", "Must be true.", required=True)], comp=False, consent=True)
def deliver_save_preset(ctx, a):
    if not ctx.project().SaveAsNewRenderPreset(a["name"]):
        raise OpError("OPERATION_FAILED", "SaveAsNewRenderPreset failed (name taken?)")
    return {"saved": a["name"]}


# ================================================================ setting (.setting text)

def _ident(n):
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n or "") is not None


def setting_tool_names(text):
    root = lua_parse(text)
    tools = root.get("Tools") if isinstance(root, LTable) else None
    if not isinstance(tools, LTable):
        raise OpError("INVALID_ARGS", "setting text has no Tools = ordered() { ... } table")
    return [k for k, v in tools.items if isinstance(k, str)], tools


def rename_setting(text, mapping):
    """Rename tools inside .setting text: definitions, SourceOp refs, ActiveTool, expressions (word-bounded)."""
    for old, new in mapping.items():
        if not (_ident(old) and _ident(new)):
            raise OpError("INVALID_ARGS", f"rename {old!r} -> {new!r}: names must be identifiers")
        text = re.sub(r"(^|[\s{,])%s(\s*=\s*[A-Za-z_]\w*\s*\{)" % re.escape(old), r"\g<1>%s\2" % new, text, flags=re.M)
        text = re.sub(r'(SourceOp\s*=\s*")%s(")' % re.escape(old), r"\g<1>%s\2" % new, text)
        text = re.sub(r'(ActiveTool\s*=\s*")%s(")' % re.escape(old), r"\g<1>%s\2" % new, text)

        def fix(m):
            return m.group(1) + re.sub(r"\b%s\b" % re.escape(old), new, m.group(2)) + m.group(3)
        text = re.sub(r'(Expression\s*=\s*")((?:\\.|[^"\\])*)(")', fix, text)
    return text


def setting_graph(text):
    """-> ({toolName: regId} for every tool defined in the text, groups included,
           [(tool, input, sourceOp, source)] for SourceOp wires that name a tool NOT defined in the text)."""
    root = lua_parse(text)
    tools = root.get("Tools") if isinstance(root, LTable) else None
    if not isinstance(tools, LTable):
        raise OpError("INVALID_ARGS", "setting text has no Tools = ordered() { ... } table")
    defined = {}

    def walk(tbl):
        for k, v in tbl.items:
            if isinstance(k, str) and isinstance(v, LTable) and v.ctor:
                defined[k] = v
                if isinstance(v.get("Tools"), LTable):
                    walk(v.get("Tools"))
    walk(tools)
    external = []
    for name, t in defined.items():
        ins = t.get("Inputs")
        if not isinstance(ins, LTable) or t.ctor in ("GroupOperator", "MacroOperator"):
            continue
        for k, iv in ins.items:
            if isinstance(k, str) and isinstance(iv, LTable):
                src = iv.get("SourceOp")
                if isinstance(src, str) and src not in defined:
                    external.append((name, k, src, iv.get("Source") or "Output"))
    return {n: t.ctor for n, t in defined.items()}, external


QUIET_OVER = 50


@op("setting.paste", "Paste .setting text (or a file) into the comp: the one-call native build. Optional rename map / prefix is applied to tool names, SourceOps and expressions BEFORE paste; collisions still get Fusion's _1 suffix (reported in renamed). Paste only works on the comp showing on the Fusion page: comp references are made current automatically. Output is quiet above 50 tools (counts by regId, renamed, a sample). A paste DROPS SourceOp wires to tools outside the text: they are reported (droppedExternal), or re-connected with rewireExternal: true.",
    [COMP(), P("text", "string", ".setting text."), P("path", "string", "Absolute .setting path (instead of text)."),
     P("rename", "object", "{oldName: newName}."), P("prefix", "string", "Prefix every top-level tool name."),
     P("quiet", "boolean", "Counts + renamed + a 10-name sample instead of every added tool (default: true above 50 tools)."),
     P("rewireExternal", "boolean", "After the paste, re-connect SourceOp wires in the text that name tools already in the comp (Fusion drops them). Default false."),
     P("connect", "array", "[[tool, input, sourceTool(, output)], ...] connections made after the paste (pasted names are mapped through renames).")],
    extra={"paste": True})
def setting_paste(ctx, comp, a):
    if bool(a.get("text")) == bool(a.get("path")):
        raise OpError("INVALID_ARGS", "pass exactly one of text or path")
    text = a.get("text") or open(a["path"], encoding="utf-8").read()
    names, _ = setting_tool_names(text)
    mapping = dict(a.get("rename") or {})
    if a.get("prefix"):
        for n in names:
            mapping.setdefault(n, a["prefix"] + n)
    if mapping:
        text = rename_setting(text, mapping)
    regs, external = setting_graph(text)
    res = ctx.paste(comp, text, names=[mapping.get(n, n) for n in names])
    renamed = {k: v for k, v in res["renamed"].items() if k != v}
    by_reg = {}
    for n in res["added"]:
        base = n if n in regs else re.sub(r"_\d+$", "", n)
        r = regs.get(base) or regs.get(n) or "?"
        by_reg[r] = by_reg.get(r, 0) + 1
    quiet = a.get("quiet") if a.get("quiet") is not None else len(res["added"]) > QUIET_OVER
    out = {"count": len(res["added"]), "renamed": renamed}
    if quiet:
        out.update(byRegId=dict(sorted(by_reg.items(), key=lambda kv: -kv[1])), sample=res["added"][:10], quiet=True)
    else:
        out["added"] = [{"name": n, "regId": regs.get(n if n in regs else re.sub(r"_\d+$", "", n))} for n in res["added"]]

    def live(n):  # a pasted name after Fusion's collision rename
        return renamed.get(n, n)
    if external:
        if a.get("rewireExternal"):
            done, missing = [], []
            for tn, iid, src, output in external:
                dst, st = comp.FindTool(live(tn)), comp.FindTool(src)
                if dst is None or st is None:
                    missing.append([live(tn), iid, src])
                    continue
                try:
                    ctx.connect(dst, iid, st, None if output in ("Output", None) else output)
                    done.append([live(tn), iid, src])
                except OpError as e:
                    missing.append([live(tn), iid, src, e.message])
            out["rewired"] = done if len(done) <= 40 else {"count": len(done), "sample": done[:10]}
            if missing:
                out["unresolved"] = missing[:40]
        else:
            out["droppedExternal"] = {"count": len(external), "sample": [[live(t), i, s] for t, i, s, _ in external[:10]],
                                      "hint": "Fusion drops SourceOp wires to tools outside the pasted text; rewireExternal: true reconnects them"}
    if a.get("connect"):
        made = []
        for c in a["connect"]:
            if not (isinstance(c, list) and len(c) >= 3):
                raise OpError("INVALID_ARGS", f"connect entries are [tool, input, sourceTool(, output)], got {c!r}")
            made.append(ctx.connect(ctx.tool(comp, live(c[0])), c[1], ctx.tool(comp, live(c[2])), c[3] if len(c) > 3 else None))
        out["connected"] = len(made)
    return out


@op("setting.copy", "Serialize tools to .setting text (Lua comp:CopySettings + bmd.writestring; Python SaveSettings returns empty through the bridge). Optional file output. tools: list, glob or 'all'.",
    [COMP(), P("tools", "string|array", "Names, glob, or 'all'.", required=True), P("outPath", "string", "Absolute .setting path to write.")], read=True)
def setting_copy(ctx, comp, a):
    targets = [n for n, _ in ctx.tools_matching(comp, a["tools"])]
    if not targets:
        raise OpError("NOT_FOUND", "no tools matched")
    lua_list = "{" + ", ".join("comp:FindTool(%s)" % json.dumps(n) for n in targets) + "}"
    text = ctx.lua(comp, "local s = comp:CopySettings(%s); result = bmd.writestring(s)" % lua_list)
    out = {"tools": targets, "bytes": len(text)}
    if a.get("outPath"):
        p = _out(a["outPath"], "copy.setting")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        out["path"] = p
    else:
        out["text"] = text
    return out


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


# [live, gapfix pass] pasted without UseFrameFormatSettings/Width these came up UseFrameFormatSettings 0 at 320x240
# (measured: Background, TextPlus, FastNoise, sRender; the rest are the same generator family, unmeasured)
PASTE_320 = {"Background", "TextPlus", "FastNoise", "sRender", "Plasma", "DaySky", "Mandelbrot", "pRender", "MultiText"}


def validate_setting_text(text):
    """Parse + audit RegIDs, input IDs, SourceOp/Source and expression refs against the live TSV."""
    tsv = TSV.get()
    problems, warnings = [], []
    lex = setting_syntax_problems(text)
    if lex:
        return {"ok": False, "problems": lex + ["Fusion's parser rejects this; a paste would fall back to the system clipboard"], "tools": []}
    try:
        root = lua_parse(text)
    except Exception as e:  # noqa
        return {"ok": False, "problems": [f"parse error: {e}"], "tools": []}
    tools = {}

    def walk(tbl):
        if not isinstance(tbl, LTable):
            return
        for k, v in tbl.items:
            if isinstance(k, str) and isinstance(v, LTable) and v.ctor:
                tools[k] = v
                if v.ctor in ("GroupOperator", "MacroOperator"):
                    walk(v.get("Tools"))
    walk(root.get("Tools") if isinstance(root, LTable) else None)
    if not tools:
        problems.append("no tools found (expected { Tools = ordered() { Name = RegID { ... } } })")
    for name, t in tools.items():
        reg = t.ctor
        if not _ident(name):
            problems.append(f"{name}: invalid tool name")
        if reg in ("GroupOperator", "MacroOperator", "BezierSpline", "PolyPath", "PipeRouter"):
            pass
        elif not tsv.is_tool(reg):
            problems.append(tsv.check_reg(reg) + f" (tool {name})")
            continue
        ins = t.get("Inputs")
        if not isinstance(ins, LTable):
            ins = LTable()  # no Inputs block: the pasted-default checks below still apply
        for k, iv in ins.items:
            if not isinstance(k, str):
                continue
            if reg not in ("GroupOperator", "MacroOperator", "PipeRouter", "BezierSpline") and not tsv.known_input(reg, k) \
                    and not re.fullmatch(r"(SceneInput|Input|Layer)\d+", k) and not re.search(r"\d$", k):
                warnings.append(f"{name}.{k}: not in the live TSV for {reg} (mode-dependent or user control?)")
            if isinstance(iv, LTable):
                op_ = iv.get("SourceOp")
                if op_ and op_ not in tools:
                    warnings.append(f"{name}.{k} <- SourceOp '{op_}' is not in this setting (must exist in the comp)")
                elif op_:
                    src_reg = tools[op_].ctor
                    outs = tsv.tools.get(src_reg, {}).get("outputs") or []
                    s = iv.get("Source")
                    if outs and s and s not in outs + ["Output", "Value", "Mask", "StyledText", "Position", "Heading"]:
                        problems.append(f"{name}.{k} <- {op_}.{s}: {src_reg} outputs are {outs}")
                ex = iv.get("Expression")
                if isinstance(ex, str) and re.search(r"\bnoise\s*\(", ex):
                    problems.append(f"{name}.{k}: noise() is not available in SimpleExpressions")
        if reg == "Renderer3D" and not (isinstance(ins, LTable) and ins.get("UseFrameFormatSettings")) and not (isinstance(ins, LTable) and ins.get("Width")):
            warnings.append(f"{name}: pasted Renderer3D without UseFrameFormatSettings/Width renders 320x240 (realities §11.16)")
        elif reg in PASTE_320 and not (isinstance(ins, LTable) and (ins.get("UseFrameFormatSettings") or ins.get("Width"))):
            warnings.append(f"{name}: pasted {reg} without UseFrameFormatSettings = 1 (or Width/Height) comes up 320x240 "
                            "(live, gapfix pass: Background, TextPlus, FastNoise, sRender)")
        if reg == "Camera3D" and not (isinstance(ins, LTable) and ins.get("ApertureW") and ins.get("ApertureH")):
            warnings.append(f"{name}: pasted Camera3D without ApertureW/ApertureH keeps the TV aperture 0.792 x 0.594 in (AoV 24.33 at 35 mm) "
                            "even when FilmGate is written (rebuild K2): write ApertureW = 0.8315, ApertureH = 0.4677 for BMD_URSA_4K_16x9 (realities §11.17)")
        rl = ins.get("MtlStdInputs.ReceivesLighting") if isinstance(ins, LTable) else None
        if isinstance(rl, LTable) and rl.get("Value") == 0:
            warnings.append(f"{name}: MtlStdInputs.ReceivesLighting = 0 renders the RGB black in the OpenGL renderer (rebuild K4); "
                            "for an unlit card set SurfacePlaneInputs.Lighting.IsAffectedByLights = 0 instead")
    return {"ok": not problems, "tools": [{"name": n, "regId": t.ctor} for n, t in tools.items()], "problems": problems, "warnings": warnings[:60]}


@op("setting.validate", "Offline check of .setting text: parses it and audits RegIDs, input IDs, SourceOp/Source outputs, noise() and the pasted-default traps (Renderer3D 320x240, Camera3D FilmGate) against the live TSV.",
    [P("text", "string", ".setting text."), P("path", "string", "Absolute .setting path.")], read=True, comp=False, offline=True)
def setting_validate(a):
    if bool(a.get("text")) == bool(a.get("path")):
        raise OpError("INVALID_ARGS", "pass exactly one of text or path")
    return validate_setting_text(a.get("text") or open(a["path"], encoding="utf-8").read())


# ================================================================ builder (fusion_build twins)

def _ptype(default):
    if isinstance(default, bool):
        return "boolean"
    if isinstance(default, (int, float)):
        return "number"
    if isinstance(default, str):
        return "string"
    if isinstance(default, dict):
        return "object"
    if isinstance(default, (list, tuple)):
        return "array"
    return "any"


def register_builders():
    """One first-class op per fusion_build builder (signature -> schema), plus preview/list. Called at import."""
    try:
        mod = build_module()
    except Exception as e:  # noqa
        return str(e)
    for bname, fn in mod.get("BUILDERS", {}).items():
        sig = inspect.signature(fn)
        doc = (fn.__doc__ or bname).strip().split("\n\n")[0].replace("\n", " ")
        params = [COMP()]
        for pn, pr in sig.parameters.items():
            if pn in ("W", "H", "fps"):
                continue
            d = None if pr.default is inspect.Parameter.empty else pr.default
            params.append(P(pn, _ptype(d) if d is not None else "any", f"default {d!r}" if d is not None else "optional",
                            default=d if isinstance(d, (str, int, float, bool)) else None))
        params.append(P("W", "integer", "Override width (default comp)."))
        params.append(P("H", "integer", "Override height (default comp)."))
        params.append(P("fps", "number", "Override fps (default comp)."))

        def handler(ctx, comp, a, _b=bname):
            if not ctx.is_current(comp):
                raise OpError("NOT_CURRENT", "builders paste: the comp must show on the Fusion page", hint="Pass comp as {timeline, item} or call comp.set_current.")
            m = build_module()
            kw = {k: v for k, v in a.items() if k != "comp"}
            try:
                res = m["build"](comp, _b, **kw)
            except (RuntimeError, KeyError, TypeError, ValueError) as e:
                raise OpError("OPERATION_FAILED", f"builder {_b}: {e}")
            info = res.get("info", {})
            ren = res.get("renamed", {})
            out = info.get("output")
            return {"builder": _b, "added": res.get("added"), "renamed": {k: v for k, v in ren.items() if k != v},
                    "output": ren.get(out, out), "animated": info.get("animated"), "post": res.get("post"),
                    "info": {k: v for k, v in info.items() if k not in ("tools", "post", "output")}}
        from ..schema import Op
        OPS["builder." + bname] = Op("builder." + bname, "builder", "fusion_build twin of Higgsfield's builder: " + doc, params, handler,
                                     extra={"paste": True})
    return None


@op("builder.preview", "Offline: return the .setting text and info a builder would paste (no Resolve). Validate with setting.validate or paste with setting.paste.",
    [P("builder", "string", "Builder name (builder.list).", required=True), P("args", "object", "Builder arguments.")], read=True, comp=False, offline=True)
def builder_preview(a):
    m = build_module()
    if a["builder"] not in m["BUILDERS"]:
        s = suggest(a["builder"], list(m["BUILDERS"]))
        raise OpError("UNKNOWN_OPERATION", f"no builder '{a['builder']}'" + (f" - did you mean '{s}'?" if s else ""))
    try:
        text, info = m["BUILDERS"][a["builder"]](**(a.get("args") or {}))
    except TypeError as e:
        raise OpError("INVALID_ARGS", str(e))
    return {"text": text, "info": {k: v for k, v in info.items() if k != "post"}, "post": info.get("post"), "validation": validate_setting_text(text) if text else None}


@op("builder.list", "Offline: builders with their parameters and defaults (Higgsfield twins: title_card, lower_third, logo_reveal, text_animator, transition, liquid_glass, effect_template, expression_template, reveal_floor; extras stat_card, cta_pill, ui_card, camera_push_3d).",
    [], read=True, comp=False, offline=True)
def builder_list(a):
    m = build_module()
    out = {}
    for n, fn in m["BUILDERS"].items():
        out[n] = {"doc": (fn.__doc__ or "").strip().split("\n")[0],
                  "params": {k: (None if v.default is inspect.Parameter.empty else v.default) for k, v in inspect.signature(fn).parameters.items()}}
    return {"builders": out}


# ================================================================ template / macro (EGP analog)

def _find_close(text, i):
    """Index of the brace closing the one opening at text[i] (string-aware)."""
    depth, n, q = 0, len(text), None
    while i < n:
        ch = text[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
        elif ch == "[" and text[i:i + 2] == "[[":
            j = text.find("]]", i)
            i = j + 2
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise OpError("INVALID_ARGS", "unbalanced braces in setting text")


def wrap_macro(text, macro, publish, output, main_inputs=()):
    """Wrap copied tools into a MacroOperator with published InstanceInputs and one MainOutput."""
    m = re.search(r"Tools\s*=\s*ordered\(\)\s*\{", text)
    if not m:
        raise OpError("INVALID_ARGS", "setting text has no Tools = ordered() table")
    open_i = m.end() - 1
    inner = text[open_i + 1:_find_close(text, open_i)]
    ins = []
    for n, (tool, iid) in enumerate(main_inputs):
        ins.append('MainInput%d = InstanceInput { SourceOp = "%s", Source = "%s", },' % (n + 1, tool, iid))
    for p in publish:
        key = p.get("id") or (p["tool"] + "_" + p["input"].replace(".", "_"))
        extra = ', Name = "%s"' % p["name"].replace('"', "") if p.get("name") else ""
        ins.append('%s = InstanceInput { SourceOp = "%s", Source = "%s"%s, },' % (key, p["tool"], p["input"], extra))
    return ("{\n\tTools = ordered() {\n\t\t%s = MacroOperator {\n\t\t\tCtrlWZoom = false,\n\t\t\tInputs = ordered() {\n\t\t\t\t%s\n\t\t\t},\n"
            "\t\t\tOutputs = {\n\t\t\t\tMainOutput1 = InstanceOutput { SourceOp = \"%s\", Source = \"Output\", },\n\t\t\t},\n"
            "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 } },\n\t\t\tTools = ordered() {%s},\n\t\t},\n\t},\n\tActiveTool = \"%s\",\n}\n") % (
        macro, "\n\t\t\t\t".join(ins), output, inner, macro)


@op("template.write_macro", "Package tools as a reusable macro (.setting with a MacroOperator): published controls (the Essential Graphics / MOGRT analog) and one main output. Writes the file (default out/<macro>.setting); installing into Resolve is template.install.",
    [COMP(), P("macro", "string", "Macro name (identifier).", required=True), P("tools", "string|array", "Tools to include (names/glob).", required=True),
     P("output", "string", "Tool whose Output becomes MainOutput1.", required=True),
     P("publish", "array", "[{tool, input, name?, id?}] controls to expose.", default=None),
     P("mainInputs", "array", "[[tool, input], ...] image inputs exposed as MainInput1..N (effects/transitions)."),
     P("outPath", "string", "Absolute .setting path.")], read=True)
def template_write_macro(ctx, comp, a):
    if not _ident(a["macro"]):
        raise OpError("INVALID_ARGS", "macro must be an identifier")
    copied = setting_copy(ctx, comp, {"tools": a["tools"]})
    names = set(copied["tools"])
    if a["output"] not in names:
        raise OpError("INVALID_ARGS", f"output '{a['output']}' is not among the included tools")
    for p in a.get("publish") or []:
        if p.get("tool") not in names:
            raise OpError("INVALID_ARGS", f"publish tool '{p.get('tool')}' is not among the included tools")
        ctx.inp(ctx.tool(comp, p["tool"]), p["input"])
    text = wrap_macro(copied["text"], a["macro"], a.get("publish") or [], a["output"], [tuple(x) for x in (a.get("mainInputs") or [])])
    v = validate_setting_text(text)
    path = _out(a.get("outPath"), a["macro"] + ".setting")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return {"path": path, "bytes": len(text), "tools": sorted(names), "published": len(a.get("publish") or []), "validation": v}


TEMPLATE_KINDS = {"title": "Edit/Titles", "effect": "Edit/Effects", "transition": "Edit/Transitions", "generator": "Edit/Generators", "fusion": "Fusion"}


@op("template.install", "Copy a .setting macro into Resolve's Templates folder (Edit/Titles, Effects, Transitions, Generators, or Fusion). Disabled unless FUSION_MCP_ALLOW_TEMPLATE_INSTALL=1, and runs only with confirm: true. Resolve may need a restart or Effects refresh to list it.",
    [P("path", "string", "Absolute .setting path.", required=True), P("kind", "string", "title|effect|transition|generator|fusion.", required=True, enum=tuple(TEMPLATE_KINDS)),
     P("subfolder", "string", "Optional subfolder (e.g. 'My Templates')."), P("overwrite", "boolean", "Replace an existing file."),
     P("confirm", "boolean", "Must be true.", required=True)], comp=False, consent=True)
def template_install(ctx, a):
    if not os.path.isfile(a["path"]) or not a["path"].endswith(".setting"):
        raise OpError("INVALID_ARGS", "path must be an existing .setting file")
    v = validate_setting_text(open(a["path"], encoding="utf-8").read())
    if not v["ok"]:
        raise OpError("INVALID_ARGS", "setting failed validation", details=v)
    d = os.path.join(config.TEMPLATES_ROOT, TEMPLATE_KINDS[a["kind"]], *( [a["subfolder"]] if a.get("subfolder") else []))
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, os.path.basename(a["path"]))
    if os.path.exists(dst) and not a.get("overwrite"):
        raise OpError("INVALID_ARGS", f"{dst} exists", hint="overwrite: true to replace")
    shutil.copy2(a["path"], dst)
    return {"installed": dst}


@op("template.list", "List .setting templates installed in Resolve's user Templates folders.", [P("kind", "string", "Filter kind.", enum=tuple(TEMPLATE_KINDS))],
    read=True, comp=False, offline=True)
def template_list(a):
    root = config.TEMPLATES_ROOT
    out = []
    for kind, sub in TEMPLATE_KINDS.items():
        if a.get("kind") and kind != a["kind"]:
            continue
        for p in glob.glob(os.path.join(root, sub, "**", "*.setting"), recursive=True):
            out.append({"kind": kind, "path": p, "name": os.path.basename(p)[:-8]})
    return {"root": root, "templates": out}


# ================================================================ viewer / command

@op("viewer.view", "Show a tool in the Fusion page viewer (left or right; view 1 or 2). Needs the comp current.",
    [COMP(), TOOL(), P("viewer", "integer", "1 (left) or 2 (right) (default 1).", default=1)], undo=False)
def viewer_view(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    cf = comp.CurrentFrame
    if cf is None:
        raise OpError("NOT_CURRENT", "no frame for this comp", hint="comp.set_current first")
    cf.ViewOn(t, int(a.get("viewer", 1)))
    return {"viewing": a["tool"], "viewer": a.get("viewer", 1)}


@op("viewer.get_state", "Viewer state for the current comp: views present, the current view, and the active tool.", [COMP()], read=True)
def viewer_get_state(ctx, comp, a):
    cf = comp.CurrentFrame
    out = {"hasFrame": cf is not None}
    if cf is not None:
        try:
            out["views"] = sorted(jv(cf.GetViewList() or {}).keys()) if isinstance(jv(cf.GetViewList() or {}), dict) else jv(cf.GetViewList())
        except Exception as e:  # noqa
            out["views"] = str(e)
    act = comp.ActiveTool
    out["activeTool"] = act.GetAttrs()["TOOLS_Name"] if act else None
    return out


def _actions(ctx):
    acts = ctx.fusion().ActionManager.GetActions() or {}
    out = []
    for a in acts.values():
        try:
            out.append({"id": a.ID, "name": a.Name})
        except Exception:
            try:
                out.append({"id": jv(a.Get("ID")), "name": jv(a.Get("Name"))})
            except Exception:
                continue
    return out


@op("command.list", "List Fusion actions (the menu-command analog) with IDs; filter by substring.",
    [P("contains", "string", "Substring of ID or name."), P("limit", "integer", "Max rows (default 200).", default=200)], read=True, comp=False)
def command_list(ctx, a):
    q = (a.get("contains") or "").lower()
    rows = [r for r in _actions(ctx) if q in (str(r["id"]) + " " + str(r["name"])).lower()]
    return {"count": len(rows), "actions": rows[:int(a.get("limit", 200))]}


@op("command.find", "Find a Fusion action ID by name (case-insensitive, best match).", [P("name", "string", "Action name or ID fragment.", required=True)],
    read=True, comp=False)
def command_find(ctx, a):
    rows = _actions(ctx)
    q = a["name"].lower()
    hits = [r for r in rows if q in (str(r["id"]) + " " + str(r["name"])).lower()]
    if not hits:
        s = suggest(a["name"], [str(r["name"]) for r in rows] + [str(r["id"]) for r in rows])
        raise OpError("NOT_FOUND", f"no action matching '{a['name']}'" + (f" - did you mean '{s}'?" if s else ""))
    return {"matches": hits[:30]}


@op("command.execute", "Run a Fusion action on the comp (comp:DoAction(id, args)), e.g. 'Time_Goto_GlobalStart'. Undo actions ('Undo'/'Redo') must run alone, not in batch.run.",
    [COMP(), P("id", "string", "Action ID (command.list).", required=True), P("args", "object", "Action arguments.")], undo=False)
def command_execute(ctx, comp, a):
    ids = {str(r["id"]) for r in _actions(ctx)}
    if ids and a["id"] not in ids:
        s = suggest(a["id"], list(ids))
        raise OpError("NOT_FOUND", f"unknown action '{a['id']}'" + (f" - did you mean '{s}'?" if s else ""))
    ok = comp.DoAction(a["id"], a.get("args") or {})
    return {"action": a["id"], "result": jv(ok), "currentTime": num(comp.CurrentTime)}


# ================================================================ pref / data

@op("pref.get", "Read a preference: scope comp (comp.GetPrefs) or app (fusion.GetPrefs). key like 'Comp.FrameFormat' or 'Global.UserInterface'.",
    [COMP(), P("key", "string", "Pref path.", required=True), P("scope", "string", "comp or app (default comp).", enum=("comp", "app"), default="comp")], read=True)
def pref_get(ctx, comp, a):
    src = comp if a.get("scope", "comp") == "comp" else ctx.fusion()
    return {"key": a["key"], "value": jv(src.GetPrefs(a["key"]))}


@op("pref.set", "Write a preference. scope comp changes this comp; scope app changes Fusion's application prefs (persists beyond the project) and runs only with confirm: true. Read back.",
    [COMP(), P("key", "string", "Pref path.", required=True), P("value", "any", "Value.", required=True),
     P("scope", "string", "comp or app (default comp).", enum=("comp", "app"), default="comp"), P("confirm", "boolean", "Required true for scope app.")])
def pref_set(ctx, comp, a):
    if a.get("scope", "comp") == "app":
        if a.get("confirm") is not True:
            raise OpError("FORBIDDEN", "app preferences persist beyond the project; pass confirm: true only on the user's explicit request")
        src = ctx.fusion()
    else:
        src = comp
    before = jv(src.GetPrefs(a["key"]))
    src.SetPrefs(a["key"], a["value"])
    return {"key": a["key"], "before": before, "value": jv(src.GetPrefs(a["key"]))}


@op("data.get", "Read custom data stored on the comp or a tool (GetData): the script-scoped settings store.",
    [COMP(), P("key", "string", "Data key (omit for all)."), P("tool", "string", "Tool (default the comp).")], read=True)
def data_get(ctx, comp, a):
    obj = ctx.tool(comp, a["tool"]) if a.get("tool") else comp
    return {"key": a.get("key"), "value": jv(obj.GetData(a["key"]) if a.get("key") else obj.GetData())}


@op("data.set", "Store custom data on the comp or a tool (SetData; saved with the comp).",
    [COMP(), P("key", "string", "Data key.", required=True), P("value", "any", "String/number/bool/object.", required=True), P("tool", "string", "Tool (default the comp).")])
def data_set(ctx, comp, a):
    obj = ctx.tool(comp, a["tool"]) if a.get("tool") else comp
    v = a["value"]
    obj.SetData(a["key"], json.dumps(v) if isinstance(v, (dict, list)) else v)
    return {"key": a["key"], "value": jv(obj.GetData(a["key"]))}


# ================================================================ eval (opt-in)

@op("eval.python", "Run arbitrary Python in the connector's Resolve worker with resolve, fusion, project, comp bound; assign `result` to return JSON. Disabled unless FUSION_MCP_ENABLE_EVAL=1. Runs inside the call's undo group; never open undo groups yourself.",
    [COMP(), P("code", "string", "Python source.", required=True)])
def eval_python(ctx, comp, a):
    ns = {"resolve": ctx.resolve, "fusion": ctx.fusion(), "project": ctx.project(), "comp": comp, "result": None, "ctx": ctx}
    exec(compile(a["code"], "<eval.python>", "exec"), ns)
    return {"result": jv(ns.get("result"))}


@op("eval.lua", "Run arbitrary Lua inside the comp (comp:Execute, deferred, polled); assign `result` (string) to return it. Disabled unless FUSION_MCP_ENABLE_EVAL=1.",
    [COMP(), P("code", "string", "Lua source; set `result`.", required=True), P("wait", "number", "Seconds to wait (default 5).", default=5)])
def eval_lua(ctx, comp, a):
    return {"result": ctx.lua(comp, a["code"], wait=float(a.get("wait", 5)))}


# ================================================================ batch

@op("batch.run", "Run several operations in ONE call and ONE undo group on the batch comp (a single comp.undo reverts them). Children are validated and policy-checked like top-level calls. Not transactional: completed children stay when a later one fails (no automatic rollback); set stopOnError to stop at the first failure. Read/verify children (comp.info, tool.info, render.frame) can ride along; their inline previews come back with the batch (first 8 as images, all paths in previews). comp.undo/redo cannot. timeoutMs covers the whole batch (pass it on fu_do).",
    [COMP(), P("ops", "array", "[{operation, args}] in order."),
     P("path", "string", "Absolute path of a JSON file holding the ops list (or {ops: [...]}) instead of ops: for long generated batches."),
     P("stopOnError", "boolean", "Stop at the first failure (default false).")],
    read=True, undo=False)
def batch_run(ctx, comp, a):
    return ctx.run_batch(comp, a["ops"], bool(a.get("stopOnError")))


_BUILDER_ERR = register_builders()
