"""Scene builder core (pure, no Resolve): a layer-level scene description (JSON, pixel units, AE-familiar)
-> one plain, editable native Fusion graph as .setting text.

validate() checks the JSON (schema + references); compile_scene() emits the graph with a layer map;
plan() reports node counts, cost drivers and the efficiency decisions; from_setting() reads the stored
description back (round trip); diff() turns two descriptions into minimal tool-level ops for scene.update.
Efficiency defaults come from the efficiency lab (measured numbers: docs/results.md) and are tunable per scene
under "efficiency" and "render3d"."""
import bisect
import copy
import functools
import json
import math
import re

from .schema import suggest

VERSION = 1
ROOT_KEY = "sbScene"          # CustomData key on <scene>_Out holding the source description
EPS_HOLD = 0.001              # hold = flat segment to f1 - EPS then a jump (render-verified in the benchmark rebuild)
APERTURE_W, APERTURE_H = 0.8315, 0.4677   # inches, BMD_URSA_4K_16x9, written explicitly [rebuild K2]
DEPTH = {"int8": 1, "int16": 2, "float16": 3, "float32": 4}
BLEND = {"normal": "Normal", "screen": "Screen", "multiply": "Multiply", "add": "LinearDodge", "linearDodge": "LinearDodge",
         "overlay": "Overlay", "softLight": "Soft Light", "hardLight": "Hard Light", "lighten": "Lighten", "darken": "Darken",
         "difference": "Difference", "exclusion": "Exclusion", "colorDodge": "Color Dodge", "colorBurn": "Color Burn",
         "linearBurn": "LinearBurn", "linearLight": "LinearLight", "vividLight": "VividLight", "pinLight": "PinLight",
         "hue": "Hue", "saturation": "Saturation", "color": "Color", "luminosity": "Luminosity"}
# Text+ Size = K * px / W per font/style [rebuild K1/K20, gapfix K1]; unmeasured fonts use 1.70 with a warning
FONT_K = {"Open Sans/Bold": 1.70, "Helvetica Neue/Bold": 1.478, "Helvetica Neue/Light": 1.462}
WEIGHT_STYLE = {100: "Thin", 200: "Extra Light", 300: "Light", 400: "Regular", 500: "Medium", 600: "Semibold", 700: "Bold",
                800: "Extra Bold", 900: "Black"}

DEFAULTS = {
    "quality": "draft",       # builds default to draft (CTRL.Draft = 1): motion blur and 3D accumulation off
    "ease": "linear",
    "motionBlur": {"on": True, "shutter": 180, "samples": 8},
    "efficiency": {
        "cull": True,             # in/out and fully transparent ranges -> enabled region on the CONSUMING Merge
        "cullMargin": 1,          # frames of shutter margin around each visible run (culling only: in/out is cut on the Blend)
        "hold": True,             # TimeStretcher texture hold under motion blur (animated sources only)
        "freeze": True,           # static sources/prefixes feeding animated tools: constant-time TimeStretcher (lab T03: -19 %, bit-identical)
        "adaptiveMotionBlur": True,
        "mbThresholdPx": 0.75,    # MotionBlur off on frames whose on-screen streak is under this
        "mbForm": "table",        # per-frame MotionBlur as a Lua table ("table") or as runs of on-frames ("runs"; shorter expression)
        "mb2d": True,             # motion blur on 2D layer Merges (False: only the 3D renderers blur; an A/B switch, efficiency lab item 7)
        "sizeBlur": True,         # rect/ellipse size keys motion-blur through a Transform scale (False: the pre-sb3 graph, no size blur)
        "mb2dSamples": None,      # 2D motion-blur Quality; None = min(motionBlur.samples, 8) (efficiency lab item 7: -15 % Deliver at 8 vs 12)
        "maxTextureScale": 2.0,   # 3D textures at their largest on-screen size, capped
        "sharpTexturePx": 12,     # ... measured only on frames where the card's motion-blur streak is under this (0 = all frames)
        "minTextureScale": 0.25,
        "textureMargin": 1.1,
        "batchShapes": True,      # consecutive static shape layers share one sRender
        "dedupeTextures": True,
        "mode3d": "auto",         # auto: 2.5D for flat cards under a straight camera, else real 3D
        "depth": "auto",          # int8 for flat UI/text, float16 where smooth fields (gradients, glows) exist
    },
    "render3d": {"transparency": "zbuffer", "accumQuality": 12, "mbQuality": 8},
}


class SceneError(Exception):
    def __init__(self, code, message, hint=None, details=None):
        super().__init__(message)
        self.code, self.message, self.hint, self.details = code, message, hint, details


# ================================================================ .setting emitter

class Src:
    def __init__(self, op, out="Output"):
        self.op, self.out = op, out

    def __eq__(self, o):
        return isinstance(o, Src) and (self.op, self.out) == (o.op, o.out)

    def __repr__(self):
        return "Src(%s.%s)" % (self.op, self.out)


class Expr:
    def __init__(self, e, v=None):
        self.e, self.v = e, v

    def __eq__(self, o):
        return isinstance(o, Expr) and self.e == o.e

    def __repr__(self):
        return "Expr(%s)" % self.e


class FuID(str):
    pass


class Styled(str):
    pass


class Grad(tuple):     # ((pos, (r, g, b, a)), ...)
    pass


class Poly(tuple):     # (closed, ((x, y, lx, ly, rx, ry) | (x, y), ...))
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
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r") + '"'


def _val(v):
    if isinstance(v, FuID):
        return "FuID { %s }" % _q(v)
    if isinstance(v, Styled):
        return "StyledText { Value = %s }" % _q(v)
    if isinstance(v, str):
        return _q(v)
    if isinstance(v, Grad):
        return "Gradient { Colors = { %s } }" % ", ".join("[%s] = { %s }" % (_num(p), ", ".join(_num(c) for c in col)) for p, col in v)
    if isinstance(v, Poly):
        closed, pts = v
        ps = []
        for p in pts:
            if len(p) == 2:
                ps.append("{ Linear = true, X = %s, Y = %s }" % (_num(p[0]), _num(p[1])))
            else:
                ps.append("{ X = %s, Y = %s, LX = %s, LY = %s, RX = %s, RY = %s }" % tuple(_num(x) for x in p))
        return "Polyline { Closed = %s, Points = { %s } }" % ("true" if closed else "false", ", ".join(ps))
    if isinstance(v, (tuple, list)):
        return "{ %s }" % ", ".join(_num(x) for x in v)
    return _num(v)


def _key(k):
    return k if re.fullmatch(r"[A-Za-z_]\w*", k) else '["%s"]' % k


def _inp(v):
    if isinstance(v, Src):
        return 'Input { SourceOp = "%s", Source = "%s", }' % (v.op, v.out)
    if isinstance(v, Expr):
        cached = "" if v.v is None else "Value = %s, " % _val(v.v)
        return "Input { %sExpression = %s, }" % (cached, _q(v.e))
    return "Input { Value = %s, }" % _val(v)


class Graph:
    """Tools in paste order. Each: reg, inputs {id: value|Src|Expr}, pos (node units) or None for modifiers,
    owner (host, input) for modifiers, keys (BezierSpline), extra (raw lines), custom (CustomData dict)."""

    def __init__(self):
        self.t, self.order = {}, []
        self.lower = {}       # Fusion tool names are case-insensitive: lower-case name -> the name in use
        self.underlays = []   # house-style backdrops (fusion_connector.layout boxes): emitted with the whole graph only

    def add(self, name, reg, inputs=None, pos=None, **kw):
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise SceneError("INVALID_ARGS", f"tool name '{name}' is not an identifier")
        if name in self.t:
            raise SceneError("INVALID_ARGS", f"duplicate tool name '{name}'", hint="layer ids must be unique within a scene")
        other = self.lower.get(name.lower())
        if other is not None:   # Fusion would rename one on paste (*_1) and every rebuild would leave an orphan copy
            raise SceneError("INVALID_ARGS", f"tool names '{other}' and '{name}' differ only by case; Fusion tool names are case-insensitive",
                             hint="rename one of the layer ids behind them: ids that differ only by case ('tl_mt'/'tl_Mt') collide, and so do "
                                  "the ids bg, ctrl, out and r3d with the builder's own <scene>_BG, _CTRL, _Out and _R3D tools")
        self.t[name] = dict(reg=reg, inputs=dict(inputs or {}), pos=pos, **kw)
        self.lower[name.lower()] = name
        self.order.append(name)
        return name

    def setin(self, name, iid, v):
        self.t[name]["inputs"][iid] = v

    def _emit(self, name):
        r = self.t[name]
        out = ["\t\t%s = %s {" % (name, r["reg"])]
        if r["reg"] == "BezierSpline":
            out.append("\t\t\tSplineColor = { Red = 225, Green = 0, Blue = 225 }, NameSet = true,")
            out.append("\t\t\tKeyFrames = {")
            for k in r["keys"]:
                parts = [_num(k["v"])]
                for h in ("RH", "LH"):
                    if h in k:
                        parts.append("%s = { %s, %s }" % (h, _num(k[h][0]), _num(k[h][1])))
                if k.get("lin"):
                    parts.append("Flags = { Linear = true }")
                if "poly" in k:   # a keyed polyline (setting-format: polyline keyframes carry Value = Polyline { ... })
                    parts.append("Value = " + _val(k["poly"]))
                out.append("\t\t\t\t[%s] = { %s }," % (_num(k["f"]), ", ".join(parts)))
            out += ["\t\t\t},", "\t\t},"]
            return out
        if r["reg"] == "XYPath":
            out.append('\t\t\tShowKeyPoints = false, DrawMode = "ModifyOnly",')
        if r.get("inputs"):
            out.append("\t\t\tInputs = {")
            for k, v in r["inputs"].items():
                if v is not None:
                    out.append("\t\t\t\t%s = %s," % (_key(k), _inp(v)))
            out.append("\t\t\t},")
        if r.get("pos") is not None:
            info = "PipeRouterInfo" if r["reg"] == "PipeRouter" else "OperatorInfo"
            out.append("\t\t\tViewInfo = %s { Pos = { %s, %s } }," % (info, _num(r["pos"][0] * 110), _num(r["pos"][1] * 33)))
        if r.get("uc"):
            out.append("\t\t\tUserControls = ordered() {")
            out += ["\t\t\t\t" + x for x in r["uc"]]
            out.append("\t\t\t},")
        if r.get("custom"):
            out.append("\t\t\tCustomData = { %s }," % ", ".join("%s = %s" % (k, _val(v)) for k, v in r["custom"].items()))
        out.append("\t\t},")
        return out

    def text(self, names=None, active=None):
        whole = names is None
        names = [n for n in self.order if names is None or n in names]
        lines = ["{", "\tTools = ordered() {"]
        if whole and self.underlays:
            from .layout import underlay_lines
            for b in self.underlays:
                lines += underlay_lines(b)
        for n in names:
            lines += self._emit(n)
        lines += ["\t},", '\tActiveTool = "%s",' % (active or names[-1]), "}", ""]
        return "\n".join(lines)


# ================================================================ JSON Schema (documented in the use-fusion skill)

_NUM = {"type": "number"}
_NUMREF = {"anyOf": [{"type": "number"}, {"type": "string", "pattern": r"^\$[A-Za-z_]\w*$"},
                     {"type": "object", "required": ["expr"], "properties": {"expr": {"type": "string"}, "value": _NUM}, "additionalProperties": False}]}
_COLOR = {"anyOf": [{"type": "string", "pattern": r"^(#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?|\$[A-Za-z_]\w*)$"},
                    {"type": "array", "items": _NUM, "minItems": 3, "maxItems": 4}]}
_VEC = {"type": "array", "items": _NUM, "minItems": 2, "maxItems": 3}
_EASE = {"anyOf": [{"type": "string"}, {"type": "array", "items": _NUM, "minItems": 4, "maxItems": 4}, {"type": "object"}, {"type": "null"}]}
_KEY = {"type": "array", "minItems": 2, "maxItems": 3, "prefixItems": [_NUM, {}, _EASE]}
_GRAD = {"type": "object", "required": ["stops"], "additionalProperties": False, "properties": {
    "type": {"enum": ["linear", "radial"]}, "from": _VEC, "to": _VEC,
    "stops": {"type": "array", "minItems": 2, "items": {"type": "array", "prefixItems": [_NUM, _COLOR], "minItems": 2, "maxItems": 2}}}}
_FILL = {"anyOf": [_COLOR, {"type": "null"}, {"type": "object", "required": ["gradient"], "properties": {"gradient": _GRAD}, "additionalProperties": False}]}
_PCT = {"type": "number", "minimum": 0, "maximum": 100}
_STROKE = {"type": "object", "required": ["width"], "additionalProperties": False, "properties": {
    "color": _COLOR, "width": {"anyOf": [{"type": "number"}, {"type": "string", "pattern": r"^\$[A-Za-z_]\w*$"}]}, "opacity": _NUM, "cap": {"enum": ["butt", "round", "square"]}, "join": {"enum": ["miter", "round", "bevel"]},
    "dash": {"type": "array", "items": {"type": "number", "minimum": 0}, "minItems": 1,
             "description": "Dash pattern in layer px [on, off, ...] along the outline (AE Dash/Gap); one shape node per dash; butt caps unless cap."},
    "dashOffset": {"type": "number", "description": "Shifts the dash pattern along the outline, px."},
    "taper": {"type": "object", "additionalProperties": False,
              "description": "AE stroke taper, % of the visible (trimmed) length and of the stroke width: the stroke is a filled offset polygon.",
              "properties": {"startLength": _PCT, "endLength": _PCT, "startWidth": _PCT, "endWidth": _PCT, "startEase": _PCT, "endEase": _PCT}}}}
_EFFECT = {"type": "object", "required": ["type"], "properties": {
    "type": {"enum": ["blur", "glow", "shadow", "tint", "grain"]}, "radius": _NUM, "strength": _NUM, "threshold": _NUM,
    "color": _COLOR, "opacity": _NUM, "offset": _VEC, "blur": _NUM, "amount": _NUM, "size": _NUM, "mono": {"type": "boolean"}},
    "additionalProperties": False}
_GLASS = {"type": "object", "additionalProperties": False,
          "description": "Backdrop blur (frosted glass, the AE adjustment layer under a card-shaped matte): what is below this layer in "
                         "its container is blurred and merged back inside the layer's own shape (alpha, masks, matte), following its "
                         "transform, animation and opacity. 2D layers and 2.5D cards.",
          "properties": {"blur": {"type": "number", "minimum": 0, "description": "Frost blur in px (like effects blur radius; default 20)."},
                         "saturation": {"type": "number", "minimum": 0, "description": "% (default 100)."},
                         "tint": _COLOR, "opacity": {"type": "number", "minimum": 0, "maximum": 100,
                                                     "description": "Frost strength, % (default 100)."}}}
_MASK = {"type": "object", "required": ["shape"], "additionalProperties": False, "properties": {
    "shape": {"enum": ["rect", "ellipse", "path"]},
    "box": {"type": "array", "items": _NUM, "minItems": 4, "maxItems": 4,
            "description": "[x, y, width, height] in layer px (text: from the text origin, the first baseline at the alignment point; "
                           "y up is negative). An AE mask or LineBox given as corners goes in `corners` instead."},
    "corners": {"type": "array", "items": _NUM, "minItems": 4, "maxItems": 4,
                "description": "[x0, y0, x1, y1] (left, top, right, bottom) in layer px, the AE LineBox form; instead of box."},
    "radius": _NUM, "points": {"type": "array"}, "feather": _NUM, "invert": {"type": "boolean"},
    "mode": {"enum": ["add", "subtract", "intersect"]}}}
_ANIMATOR = {"type": "object", "required": ["type", "start"], "additionalProperties": False, "properties": {
    "type": {"enum": ["typewriter", "cascade"]}, "start": _NUM, "end": _NUM, "mode": {"enum": ["step", "fade"]},
    "stagger": _NUM, "duration": _NUM, "ease": _EASE, "order": {"enum": ["left_to_right", "right_to_left", "inside_out", "outside_in", "random"]},
    "from": {"type": "object", "additionalProperties": False, "properties": {"x": _NUM, "y": _NUM, "opacity": _NUM, "scale": _NUM, "rotation": _NUM}}}}
_TOK = {"anyOf": [{"type": "number"}, {"type": "string", "pattern": r"^\$[A-Za-z_]\w*$"}]}   # number or a $control read at build time
_TEXT_PROPS = {"content": {"type": "string"}, "textStyle": {"type": "string"}, "font": {"type": "string"}, "style": {"type": "string"},
               "weight": {"type": "integer"}, "size": _TOK, "tracking": _TOK, "leading": _TOK, "color": _COLOR,
               "align": {"enum": ["left", "center", "right"]}, "sizeK": _NUM}
_TEXT = {"type": "object", "required": ["content"], "additionalProperties": False, "properties": _TEXT_PROPS}
_TEXTSTYLE = {"type": "object", "additionalProperties": False, "properties": {k: v for k, v in _TEXT_PROPS.items() if k not in ("content", "textStyle")}}
_MOVE = {"anyOf": [{"type": "string"}, {"type": "object", "additionalProperties": False, "properties": {
    "preset": {"type": "string"}, "at": _NUM, "duration": _NUM, "ease": _EASE,
    "from": {"type": "object", "additionalProperties": False, "properties": {k: _NUM for k in ("x", "y", "z", "opacity", "scale", "rotation")}},
    "to": {"type": "object", "additionalProperties": False, "properties": {k: _NUM for k in ("x", "y", "z", "opacity", "scale", "rotation")}}}}]}
_ALIGN = {"anyOf": [{"type": "string"}, {"type": "object", "additionalProperties": False, "properties": {
    "x": {"enum": ["left", "center", "right"]}, "y": {"enum": ["top", "center", "bottom"]}, "to": {"type": "string"},
    "place": {"enum": ["inside", "above", "below", "left", "right"]}, "gap": _TOK,
    "offset": {"type": "array", "items": _TOK, "minItems": 2, "maxItems": 2}}}]}
_LAYOUT = {"type": "object", "required": ["type"], "additionalProperties": False, "properties": {
    "type": {"enum": ["stack", "grid"]}, "direction": {"enum": ["vertical", "horizontal"]}, "gap": {"anyOf": [_TOK, {"type": "array", "items": _TOK}]},
    "align": {"enum": ["start", "center", "end"]}, "columns": {"type": "integer", "minimum": 1},
    "cell": {"type": "array", "items": _TOK, "minItems": 2, "maxItems": 2},
    "padding": {"anyOf": [_TOK, {"type": "array", "items": _TOK, "minItems": 2, "maxItems": 4}]}}}
_STAGGER = {"type": "object", "additionalProperties": False, "properties": {
    "each": _NUM, "order": {"enum": ["forward", "reverse", "center"]}, "enter": _MOVE, "exit": _MOVE}}
_LAYER_PROPS = {
    "id": {"type": "string", "pattern": r"^[A-Za-z_]\w*$"},
    "type": {"enum": ["text", "rect", "ellipse", "path", "solid", "image", "group", "null", "camera", "light"]},
    "name": {"type": "string"}, "in": _NUM, "out": _NUM, "parent": {"type": "string"},
    "position": _VEC,
    "anchor": dict(_VEC, description="AE anchor point in layer px: the layer point that lands on position and that scale and rotation "
                                     "pivot about, so setting it MOVES the layer. Defaults: shape/solid/image/group centre; text and "
                                     "path origin [0, 0]."),
    "scale": {"anyOf": [_NUM, _VEC]}, "rotation": _NUMREF, "rotationX": _NUMREF,
    "rotationY": _NUMREF, "opacity": _NUMREF, "threeD": {"type": "boolean"}, "visible": {"type": "boolean"},
    "keys": {"type": "object", "additionalProperties": {"type": "array", "items": _KEY}},
    "blend": {"enum": sorted(BLEND)}, "motionBlur": {"type": "boolean"}, "effects": {"type": "array", "items": _EFFECT},
    "masks": {"type": "array", "items": _MASK},
    "matte": {"type": "object", "required": ["layer"], "additionalProperties": False, "properties": {
        "layer": {"type": "string"}, "mode": {"enum": ["alpha", "alphaInverted", "luma", "lumaInverted"]}}},
    "text": _TEXT, "animators": {"type": "array", "items": _ANIMATOR},
    "size": {"type": "array", "items": {"anyOf": [_TOK, {"type": "null"}]}, "minItems": 2, "maxItems": 2}, "radius": _TOK, "fill": _FILL, "stroke": _STROKE,
    "align": _ALIGN, "offset": {"type": "array", "items": _TOK, "minItems": 2, "maxItems": 2}, "layout": _LAYOUT, "stagger": _STAGGER,
    "enter": _MOVE, "exit": _MOVE,
    "points": {"type": "array", "minItems": 2, "description": "Path points in layer px: offsets from the layer's origin, which sits on "
                                                                "position (AE shape paths); [x, y] or {p, in, out} with handles relative to p. "
                                                                "Absolute comp coordinates need position [0, 0]."},
    "closed": {"type": "boolean"},
    "trim": {"type": "object", "additionalProperties": False, "properties": {"start": _NUM, "end": _NUM}},
    "repeat": {"type": "object", "required": ["count"], "additionalProperties": False, "properties": {
        "count": {"type": "integer", "minimum": 1}, "offset": _VEC, "rotation": _NUM, "pivot": _VEC}},
    "color": _COLOR, "src": {"type": "string"}, "layers": {"type": "array"}, "use": {"type": "string"}, "background": _FILL,
    "poi": {"anyOf": [_VEC, {"type": "null"}]}, "zoom": _NUM, "lens": _NUM,
    "dof": {"type": "object", "additionalProperties": False, "properties": {
        "focus": {"anyOf": [_NUM, {"type": "string"}]}, "aperture": _NUM}},
    "light": {"enum": ["ambient", "point", "directional", "spot"]}, "intensity": _NUM, "lit": {"type": "boolean"},
    "glass": _GLASS,
    "notes": {"type": "string"},
}
LAYER_SCHEMA = {"type": "object", "required": ["id", "type"], "properties": _LAYER_PROPS, "additionalProperties": False}
SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "use-fusion scene description v1",
    "description": "Layer-level scene: pixels, top-left origin, y down, +z away from the camera; frames are comp frames; "
                   "layers are listed bottom to top (later layers draw over earlier ones); a key is [frame, value, ease] "
                   "and its ease shapes the segment that LEAVES it (CSS keyframe semantics).",
    "type": "object", "required": ["scene", "size", "duration", "layers"], "additionalProperties": False,
    "properties": {
        "version": {"const": 1}, "scene": {"type": "string", "pattern": r"^[A-Za-z_]\w*$"},
        "size": {"type": "array", "items": {"type": "integer", "minimum": 16}, "minItems": 2, "maxItems": 2},
        "fps": _NUM, "duration": {"type": "integer", "minimum": 1}, "start": {"type": "integer", "minimum": 0}, "background": _FILL,
        "controlsFrom": {"type": "string", "pattern": r"^[A-Za-z_]\w*$",
                         "description": "One controller per film: this scene's CTRL (Draft and every control of the same name) follows "
                                        "<scene id>_CTRL by expression; edit values, quality and tokens on that scene."},
        "motionBlur": {"anyOf": [{"type": "boolean"}, {"type": "object", "additionalProperties": False, "properties": {
            "on": {"type": "boolean"}, "shutter": _NUM, "samples": {"type": "integer"}}}]},
        "quality": {"enum": ["draft", "final"]}, "ease": _EASE,
        "eases": {"type": "object", "additionalProperties": {"type": "array", "items": _NUM, "minItems": 4, "maxItems": 4}},
        "controls": {"type": "object", "additionalProperties": {"anyOf": [_NUM, _COLOR]}},
        "textStyles": {"type": "object", "additionalProperties": _TEXTSTYLE},
        "safeArea": {"anyOf": [_NUM, {"type": "array", "items": _NUM, "minItems": 2, "maxItems": 2}]},
        "grain": {"type": "object", "additionalProperties": False, "properties": {"strength": _NUM, "size": _NUM, "mono": {"type": "boolean"}}},
        "efficiency": {"type": "object", "properties": {k: {} for k in DEFAULTS["efficiency"]}, "additionalProperties": False},
        "render3d": {"type": "object", "additionalProperties": False, "properties": {
            "transparency": {"enum": ["zbuffer", "sorted"]}, "accumQuality": {"type": "integer"}, "mbQuality": {"type": "integer"}}},
        "assets": {"type": "object", "additionalProperties": {"type": "object", "required": ["layers"], "additionalProperties": False,
                                                              "properties": {"size": {"type": "array", "items": _TOK}, "layers": {"type": "array"},
                                                                             "background": _FILL, "layout": _LAYOUT, "stagger": _STAGGER,
                                                                             "notes": {"type": "string"}}}},
        "layers": {"type": "array", "items": LAYER_SCHEMA},
        "notes": {"type": "string"},
    }}
RESERVED = {"BG", "Out", "CTRL", "Camera"}
# enter/exit presets (design-first defaults; any field can be overridden: {"preset": "fadeUp", "at": 12, "duration": 20})
MOVES = {
    "fadeIn": {"duration": 10, "ease": "ease", "from": {"opacity": 0}},
    "fadeUp": {"duration": 16, "ease": "out_expo", "from": {"y": 40, "opacity": 0}},
    "fadeDown": {"duration": 16, "ease": "out_expo", "from": {"y": -40, "opacity": 0}},
    "slideLeft": {"duration": 18, "ease": "out_expo", "from": {"x": 120, "opacity": 0}},
    "slideRight": {"duration": 18, "ease": "out_expo", "from": {"x": -120, "opacity": 0}},
    "pop": {"duration": 14, "ease": "out_back", "from": {"scale": 70, "opacity": 0}},
    "zoomIn": {"duration": 18, "ease": "out_expo", "from": {"scale": 118, "opacity": 0}},
    "fadeOut": {"duration": 10, "ease": "in", "to": {"opacity": 0}},
    "fadeOutUp": {"duration": 12, "ease": "in", "to": {"y": -30, "opacity": 0}},
    "fadeOutDown": {"duration": 12, "ease": "in", "to": {"y": 30, "opacity": 0}},
    "shrink": {"duration": 12, "ease": "in", "to": {"scale": 80, "opacity": 0}},
}
ALIGN_WORDS = {"center": ("center", "center"), "top": ("center", "top"), "bottom": ("center", "bottom"), "left": ("left", "center"),
               "right": ("right", "center"), "top-left": ("left", "top"), "top-right": ("right", "top"),
               "bottom-left": ("left", "bottom"), "bottom-right": ("right", "bottom")}
SCALAR_KEYS = {"opacity", "rotation", "rotationX", "rotationY", "zoom", "focus", "trimStart", "trimEnd", "radius"}
VECTOR_KEYS = {"position", "scale", "size", "poi", "fill", "color"}
TEXT_KEYS = {"text"}


def validate(desc):
    """-> list of issues [{path, message}] (empty = valid). Schema + references + frame sanity."""
    import jsonschema
    issues = []
    v = jsonschema.Draft202012Validator(SCHEMA)
    for e in sorted(v.iter_errors(desc), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        msg = e.message
        if e.validator == "additionalProperties":
            m = re.search(r"\('([^']+)'", msg)
            allowed = list((e.schema.get("properties") or {}).keys())
            if m:
                s = suggest(m.group(1), allowed)
                msg = "unknown property '%s'" % m.group(1) + (" - did you mean '%s'?" % s if s else "")
        issues.append({"path": path, "message": msg[:300]})
    if issues:
        return issues
    ids = {}
    assets = desc.get("assets") or {}

    def walk(layers, where, in_asset=None):
        for i, L in enumerate(layers):
            p = "%s/%d" % (where, i)
            ok = list(jsonschema.Draft202012Validator(LAYER_SCHEMA).iter_errors(L))
            for e in ok:
                issues.append({"path": p + "/" + "/".join(str(x) for x in e.absolute_path), "message": e.message[:300]})
            if ok:
                continue
            if L["id"] in ids:
                issues.append({"path": p + "/id", "message": "duplicate layer id '%s' (also at %s): layer ids are one namespace across the "
                               "scene and every asset (they name the tools); prefix asset layer ids, e.g. '%s_%s'"
                               % (L["id"], ids[L["id"]], (in_asset or "asset")[:12], L["id"])})
            ids[L["id"]] = p
            for k in (L.get("keys") or {}):
                if k not in SCALAR_KEYS | VECTOR_KEYS | TEXT_KEYS:
                    s = suggest(k, sorted(SCALAR_KEYS | VECTOR_KEYS | TEXT_KEYS))
                    issues.append({"path": p + "/keys/" + k, "message": "unknown animatable property" + (" - did you mean '%s'?" % s if s else "")})
                    continue
                ks = L["keys"][k]
                fr = [x[0] for x in ks]
                if fr != sorted(fr) or len(set(fr)) != len(fr):
                    issues.append({"path": p + "/keys/" + k, "message": "key frames must be strictly increasing"})
                for j, kv in enumerate(ks):
                    want = _key_shape(k, kv[1])
                    if want:
                        issues.append({"path": "%s/keys/%s/%d/1" % (p, k, j), "message": "%s key value %s: expected %s"
                                       % (k, json.dumps(kv[1])[:40], want)})
            if L["type"] == "group" and not (L.get("layers") is not None or L.get("use")):
                issues.append({"path": p, "message": "group needs layers (inline) or use (an asset name)"})
            if L.get("use") and L["use"] not in assets:
                s = suggest(L["use"], list(assets))
                issues.append({"path": p + "/use", "message": "unknown asset '%s'" % L["use"] + (" - did you mean '%s'?" % s if s else "")})
            if L["type"] == "text" and "text" not in L:
                issues.append({"path": p, "message": "text layer needs text: {content, ...}"})
            if L["type"] == "path" and not L.get("points"):
                issues.append({"path": p, "message": "path layer needs points"})
            if L["type"] == "image" and not L.get("src"):
                issues.append({"path": p, "message": "image layer needs src (absolute path)"})
            if L.get("in", 0) >= L.get("out", 1e9):
                issues.append({"path": p, "message": "in must be before out (out is exclusive)"})
            for j, m in enumerate(L.get("masks") or []):
                mp = "%s/masks/%d" % (p, j)
                if "box" in m and "corners" in m:
                    issues.append({"path": mp, "message": "give box [x, y, width, height] or corners [x0, y0, x1, y1], not both"})
                elif "box" in m and (m["box"][2] <= 0 or m["box"][3] <= 0):
                    issues.append({"path": mp + "/box", "message": "box is [x, y, width, height]: width and height must be > 0 "
                                   "(for [x0, y0, x1, y1] use corners)"})
                elif "corners" in m and (m["corners"][2] <= m["corners"][0] or m["corners"][3] <= m["corners"][1]):
                    issues.append({"path": mp + "/corners", "message": "corners is [x0, y0, x1, y1]: x1 > x0 and y1 > y0"})
            if L.get("layers") is not None:
                walk(L["layers"], p + "/layers", in_asset)
    walk(desc["layers"], "layers")
    for lid, p in ids.items():
        if lid in RESERVED or lid.startswith(("R3D", "A_")):
            issues.append({"path": p + "/id", "message": "layer id '%s' is reserved (scene tools use it)" % lid})
    for an, a in assets.items():
        walk(a["layers"], "assets/%s/layers" % an, an)
    for p, L in _all_layers(desc):
        for ref, what in ((L.get("parent"), "parent"), ((L.get("matte") or {}).get("layer"), "matte"),
                          ((L.get("dof") or {}).get("focus") if isinstance((L.get("dof") or {}).get("focus"), str) else None, "focus")):
            if ref and ref not in ids:
                s = suggest(ref, list(ids))
                issues.append({"path": p, "message": "%s '%s' is not a layer id" % (what, ref) + (" - did you mean '%s'?" % s if s else "")})
    ctl = desc.get("controls") or {}
    styles = desc.get("textStyles") or {}
    for p, L in _all_layers(desc):
        for m in re.finditer(r"\$([A-Za-z_]\w*)", json.dumps(L)):
            if m.group(1) not in ctl:
                issues.append({"path": p, "message": "control '$%s' is not defined in controls" % m.group(1)})
        ts = (L.get("text") or {}).get("textStyle")
        if ts and ts not in styles:
            s = suggest(ts, list(styles))
            issues.append({"path": p + "/text/textStyle", "message": "unknown textStyle '%s'" % ts + (" - did you mean '%s'?" % s if s else "")})
        for kind in ("enter", "exit"):
            mv = L.get(kind)
            pre = mv if isinstance(mv, str) else (mv or {}).get("preset")
            if pre and pre not in MOVES:
                s = suggest(pre, list(MOVES))
                issues.append({"path": p + "/" + kind, "message": "unknown %s preset '%s'" % (kind, pre) + (" - did you mean '%s'?" % s if s else "")})
            if mv and set(MOVES.get(pre, {}).get("from", {}) if pre else (mv.get("from") or mv.get("to") or {})) & {"x", "y"} \
                    and "position" in (L.get("keys") or {}):
                issues.append({"path": p + "/" + kind, "message": "%s moves position but the layer also keys position: use one" % kind})
        al = L.get("align")
        to = al.get("to") if isinstance(al, dict) else None
        if to and to not in ("frame", "safe", "parent") and to not in ids:
            s = suggest(to, list(ids) + ["frame", "safe", "parent"])
            issues.append({"path": p + "/align/to", "message": "align target '%s' is not frame, safe, parent or a layer id" % to + (" - did you mean '%s'?" % s if s else "")})
        if isinstance(al, str) and al not in ALIGN_WORDS:
            s = suggest(al, list(ALIGN_WORDS))
            issues.append({"path": p + "/align", "message": "unknown align '%s'" % al + (" - did you mean '%s'?" % s if s else "")})
    return issues


def _all_layers(desc):
    out = []

    def walk(layers, where):
        for i, L in enumerate(layers):
            p = "%s/%d" % (where, i)
            out.append((p, L))
            if isinstance(L.get("layers"), list):
                walk(L["layers"], p + "/layers")
    walk(desc.get("layers") or [], "layers")
    for an, a in (desc.get("assets") or {}).items():
        walk(a.get("layers") or [], "assets/%s/layers" % an)
    return out


def _key_shape(prop, v):
    """None when a key value fits the property, else what it should be (validation with a path, fusion_v2 F5)."""
    tok = prop in Compiler.TOKEN_FIELDS  # size/radius keys may read number controls ("$w")
    num = lambda x: (isinstance(x, (int, float)) and not isinstance(x, bool)) or (tok and isinstance(x, str) and x.startswith("$"))  # noqa: E731
    if prop in SCALAR_KEYS:
        return None if num(v) else "a number"
    if prop == "scale":
        return None if num(v) or (isinstance(v, list) and len(v) in (2, 3) and all(num(x) for x in v)) else "a number or [sx, sy]"
    if prop in ("position", "size", "poi"):
        return None if isinstance(v, list) and len(v) in (2, 3) and all(num(x) for x in v) else "[x, y] or [x, y, z]"
    return None


def _mask_box(m):
    """Mask rect as [x, y, width, height] from box or corners (layer px)."""
    if m.get("corners"):
        x0, y0, x1, y1 = m["corners"]
        return [x0, y0, x1 - x0, y1 - y0]
    return list(m.get("box", [0, 0, 100, 100]))


# ================================================================ eases and tracks

_BUILTIN_CURVES = {"house": (0.22, 0.0, 0.25, 1.0), "ease": (0.25, 0.1, 0.25, 1.0), "in_out": (0.42, 0.0, 0.58, 1.0),
                   "out_expo": (0.16, 1.0, 0.3, 1.0), "out_back": (0.34, 1.56, 0.64, 1.0), "in": (0.42, 0.0, 1.0, 1.0)}


def presets():
    try:
        from .ops.core import curves
        c = curves()
    except Exception:  # noqa: skill scripts missing: the built-in subset
        c = dict(_BUILTIN_CURVES)
    return c


def bez_y(x1, y1, x2, y2, s):
    lo, hi = 0.0, 1.0
    for _ in range(48):
        u = (lo + hi) / 2
        x = 3 * (1 - u) ** 2 * u * x1 + 3 * (1 - u) * u * u * x2 + u ** 3
        lo, hi = (u, hi) if x < s else (lo, u)
    u = (lo + hi) / 2
    return 3 * (1 - u) ** 2 * u * y1 + 3 * (1 - u) * u * u * y2 + u ** 3


class Eases:
    def __init__(self, named, default, fps):
        self.named, self.default, self.fps, self._p = dict(named or {}), default, fps, None

    def curve(self, e, D=1.0, V=1.0):
        """-> ('bezier', x1, y1, x2, y2) | ('linear',) | ('hold',)."""
        if e is None:
            e = self.default
        if e is None or e == "linear":
            return ("linear",)
        if e in ("hold", "step"):
            return ("hold",)
        if isinstance(e, str) and e in self.named:
            return ("bezier",) + tuple(float(x) for x in self.named[e])
        if isinstance(e, str):
            if self._p is None:
                self._p = presets()
            if e not in self._p:
                s = suggest(e, list(self._p) + list(self.named) + ["hold", "linear"])
                raise SceneError("INVALID_ARGS", f"unknown ease '{e}'" + (f" - did you mean '{s}'?" if s else ""),
                                 hint="preset name, [x1,y1,x2,y2], 'hold', 'linear', or a scene-level eases entry")
            c = self._p[e]
            if c is None:
                return ("linear",)
            if c == "step":
                return ("hold",)
            return ("bezier",) + tuple(c)
        if isinstance(e, (list, tuple)) and len(e) == 4:
            return ("bezier",) + tuple(float(x) for x in e)
        if isinstance(e, dict):  # AE speed/influence
            xo, xi = float(e.get("outInfluence", 33.33)) / 100, float(e.get("inInfluence", 33.33)) / 100
            so, si = float(e.get("outSpeed", 0)), float(e.get("inSpeed", 0))
            y1 = (so * xo * D / self.fps) / V if V else 0
            y2 = 1 - ((si * xi * D / self.fps) / V if V else 0)
            return ("bezier", xo, y1, 1 - xi, y2)
        raise SceneError("INVALID_ARGS", f"bad ease {e!r}")


class Track:
    """keys [[frame, value, ease?]] -> value at any time (the ease of key i shapes segment i -> i+1)."""

    def __init__(self, keys, eases, fn=None):
        fn = fn or (lambda v: v)
        self.f = [float(k[0]) for k in keys]
        self.v = [fn(k[1]) for k in keys]
        self.e = [k[2] if len(k) > 2 else None for k in keys]
        self.eases = eases
        self._memo, self._curves = {}, {}

    def curve(self, i, comp=None):
        hit = self._curves.get((i, comp))
        if hit is None:
            hit = self._curves[(i, comp)] = self._curve(i, comp)
        return hit

    def _curve(self, i, comp=None):
        a, b = self.v[i], self.v[i + 1]
        if comp is not None:
            a, b = a[comp], b[comp]
        V = (b - a) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else 1.0
        return self.eases.curve(self.e[i], self.f[i + 1] - self.f[i], V)

    def at(self, t):
        if t <= self.f[0]:
            return self.v[0]
        if t >= self.f[-1]:
            return self.v[-1]
        hit = self._memo.get(t)
        if hit is not None:
            return hit
        out = self._at(t)
        self._memo[t] = out
        return out

    def _at(self, t):
        i = bisect.bisect_right(self.f, t) - 1
        f0, f1 = self.f[i], self.f[i + 1]
        s = (t - f0) / (f1 - f0)
        v0, v1 = self.v[i], self.v[i + 1]
        if isinstance(v0, str):
            return v0
        c = self.curve(i, 0 if isinstance(v0, (list, tuple)) else None)
        p = s if c[0] == "linear" else 0.0 if c[0] == "hold" else bez_y(c[1], c[2], c[3], c[4], s)
        if isinstance(v0, (list, tuple)):
            return [a + (b - a) * p for a, b in zip(v0, v1)]
        return v0 + (v1 - v0) * p

    def component(self, i, fn=lambda x: x):
        """(frames, values, curves) of one component, mapped by fn (must be affine to keep eases exact)."""
        vals = [fn(v[i] if i is not None else v) for v in self.v]
        curves = [self.curve(j, i) for j in range(len(self.f) - 1)]
        return list(self.f), vals, curves


def spline_keys(frames, vals, curves):
    """-> KeyFrames entries with ABSOLUTE handles; holds become a flat segment plus a jump."""
    pts, segs = [], []
    for j in range(len(frames)):
        pts.append((frames[j], vals[j]))
        if j < len(curves):
            c = curves[j]
            if c[0] == "hold" and vals[j + 1] != vals[j]:
                segs.append(("linear",))
                pts.append((frames[j + 1] - EPS_HOLD, vals[j]))
                segs.append(("linear",))
            else:
                segs.append(("linear",) if c[0] == "hold" else c)
    ks = [{"f": f, "v": v} for f, v in pts]
    lin = [[] for _ in pts]
    for j, c in enumerate(segs):
        (t0, v0), (t1, v1) = pts[j], pts[j + 1]
        D, V = t1 - t0, v1 - v0
        x1, y1, x2, y2 = c[1:] if c[0] == "bezier" else (1 / 3, 1 / 3, 2 / 3, 2 / 3)
        ks[j]["RH"] = (t0 + x1 * D, v0 + y1 * V)
        ks[j + 1]["LH"] = (t0 + x2 * D, v0 + y2 * V)
        lin[j].append(c[0] != "bezier")
        lin[j + 1].append(c[0] != "bezier")
    for k, l in zip(ks, lin):
        if l and all(l):
            k["lin"] = True
    return ks


# ================================================================ small helpers

def hexrgba(c, what="color"):
    if isinstance(c, (list, tuple)):
        c = [float(x) for x in c] + ([1.0] if len(c) == 3 else [])
        return tuple(c[:4])
    h = c.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", h):
        raise SceneError("INVALID_ARGS", f"bad {what} {c!r}", hint="'#rrggbb', '#rrggbbaa', [r,g,b(,a)] 0-1 or '$control'")
    v = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
    return tuple(v + ([1.0] if len(v) == 3 else []))


def _even(x):
    n = int(math.ceil(x - 1e-6))
    return max(2, n + (n % 2))


def _q8(x):
    """Round a texture scale UP to the next 1/8."""
    return math.ceil(x * 8 - 1e-9) / 8.0


@functools.lru_cache(maxsize=4096)
def _rot(rx, ry, rz):
    """AE rotation (degrees, y down) as a 3x3 matrix, Z applied first (Fusion RotOrder ZYX) [rebuild K7]."""
    a, b, c = (math.radians(x) for x in (rx, ry, rz))
    Rx = ((1, 0, 0), (0, math.cos(a), -math.sin(a)), (0, math.sin(a), math.cos(a)))
    Ry = ((math.cos(b), 0, math.sin(b)), (0, 1, 0), (-math.sin(b), 0, math.cos(b)))
    Rz = ((math.cos(c), -math.sin(c), 0), (math.sin(c), math.cos(c), 0), (0, 0, 1))

    def mm(A, B):
        return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return mm(Rx, mm(Ry, Rz))


def _mv(M, v):
    return tuple(sum(M[i][k] * v[k] for k in range(3)) for i in range(3))


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return tuple(x / n for x in a)


# ================================================================ fonts: real advance widths and cap heights for layout

FONT_DIRS = ("/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", "~/Library/Fonts")


def font_index(cache_path=None, dirs=FONT_DIRS):
    """{'Family/Style': [path, face index]} of installed fonts (PIL names), cached by directory mtimes."""
    import glob
    import os
    dirs = [os.path.expanduser(d) for d in dirs if os.path.isdir(os.path.expanduser(d))]
    stamp = [[d, os.path.getmtime(d)] for d in dirs]
    if cache_path and os.path.exists(cache_path):
        try:
            c = json.load(open(cache_path, encoding="utf-8"))
            if c.get("stamp") == stamp:
                return c["fonts"]
        except (OSError, ValueError):
            pass
    from PIL import ImageFont
    idx = {}
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "*"))):
            if not f.lower().endswith((".ttf", ".otf", ".ttc")):
                continue
            for i in range(64):
                try:
                    fam, sty = ImageFont.truetype(f, 100, index=i).getname()
                except (OSError, ValueError):
                    break
                idx.setdefault("%s/%s" % (fam, sty), [f, i])
                if not f.lower().endswith(".ttc"):
                    break
    if cache_path:
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            json.dump({"stamp": stamp, "fonts": idx}, open(cache_path, "w", encoding="utf-8"))
        except OSError:
            pass
    return idx


class FontMetrics:
    """Advance widths (kerned when PIL has raqm) and cap height of one face, in em."""

    def __init__(self, path=None, index=0):
        self.f = None
        self.cap, self.asc, self.desc = 0.72, 0.95, 0.25
        if path:
            from PIL import ImageFont
            self.f = ImageFont.truetype(path, 1000, index=index)
            x0, y0, x1, y1 = self.f.getbbox("H")
            a, d = self.f.getmetrics()
            self.cap, self.asc, self.desc = (y1 - y0) / 1000.0, a / 1000.0, d / 1000.0

    def width(self, text, px, tracking=0.0):
        em = self.f.getlength(text) / 1000.0 if self.f else len(text) * 0.58
        return (em + float(tracking) / 1000.0 * max(0, len(text) - 1)) * px


class Fonts:
    """family/style -> FontMetrics. files: {'Family/Style': path or [path, index]} (live: Fusion's FontManager list;
    offline: font_index()). Unknown faces fall back to 0.58 em per character (reported)."""

    def __init__(self, files=None):
        self.files = files or {}
        self._m = {}

    def get(self, family, style):
        key = "%s/%s" % (family, style)
        if key not in self._m:
            f = self.files.get(key)
            try:
                self._m[key] = FontMetrics(*(f if isinstance(f, (list, tuple)) else [f, 0])) if f else FontMetrics()
            except (OSError, ValueError):
                self._m[key] = FontMetrics()
            self._m[key].known = bool(f)
        return self._m[key]


# ================================================================ compiler

class Space:
    """A container's pixel space mapped onto its canvas: point (x, y) px -> normalized canvas (u, v), Y up."""

    def __init__(self, W, H, cx, cy, k, cw, ch):
        self.W, self.H, self.cx, self.cy, self.k, self.cw, self.ch = W, H, cx, cy, k, cw, ch

    def uv(self, x, y):
        return (0.5 + (x - self.cx) * self.k / self.W, 0.5 - (y - self.cy) * self.k / self.H)


class Source:
    def __init__(self, name, W, H, k, c, animated=False, smooth=False, content_motion=None):
        self.name, self.W, self.H, self.k, self.c = name, W, H, k, c
        self.animated, self.smooth, self.content_motion = animated, smooth, content_motion or []
        self.pending_masks = None


def _merged_defaults(desc):
    d = copy.deepcopy(DEFAULTS)
    mb = desc.get("motionBlur", True)
    if isinstance(mb, bool):
        d["motionBlur"]["on"] = mb
    else:
        d["motionBlur"].update(mb)
    d["efficiency"].update(desc.get("efficiency") or {})
    d["render3d"].update(desc.get("render3d") or {})
    d["quality"] = desc.get("quality", d["quality"])
    return d


class Compiler:
    def __init__(self, desc, font_k=None, image_size=None, fonts=None):
        issues = validate(desc)
        if issues:
            raise SceneError("INVALID_ARGS", "scene description is invalid: " + "; ".join("%s: %s" % (i["path"], i["message"]) for i in issues[:8]),
                             details={"issues": issues[:60]}, hint="scene.schema has the JSON Schema; scene.plan validates offline.")
        self.authored = desc
        self.fonts = fonts or Fonts()
        self.S = desc["scene"]
        self.W, self.H = desc["size"]
        self.fps = float(desc.get("fps", 30))
        self.dur = int(desc["duration"])
        self.cfg = _merged_defaults(desc)
        self.eff = self.cfg["efficiency"]
        self.eases = Eases(desc.get("eases"), desc.get("ease", self.cfg["ease"]), self.fps)
        self.font_k = dict(FONT_K, **(font_k or {}))
        self.image_size = image_size or _image_size
        self.g = Graph()
        self.warnings, self.decisions, self._box = [], [], {}
        self.cont_size = {}
        desc = self.desc = self.expand(desc)
        self._box = {}
        self.byid = {L["id"]: L for _, L in _all_layers(desc)}
        self.parent_of = {}
        self.layers, self.regions, self.textures = {}, {}, []
        self.mattes = {(L.get("matte") or {}).get("layer") for _, L in _all_layers(desc)} - {None}
        self.asset_cache, self.tex_cache = {}, {}
        self.ns, self.asset_variants = "", {}   # tool-name namespace of the asset raster variant being built
        self.row = 0
        self._tracks = {}
        self._mask_depth = 0   # > 0 while a mask branch (track matte image) is being built: freeze() refuses there
        self.ctrl = None
        self.stats = {"renderers": 0, "mbMerges": 0, "holds": 0, "freezes": 0, "batched": 0, "renderers2_5d": 0}

    # ------------------------------------------------------------ authoring: tokens, type styles, layout, align, enter/exit, stagger
    TOKEN_FIELDS = {"size", "radius", "width", "tracking", "leading", "gap", "padding", "cell", "offset"}

    def expand(self, desc):
        """The authored description (design intent) -> plain positions and keys the compiler consumes. The authored JSON is what
        is stored and exported, so re-layout and retiming stay edits of intent."""
        d = copy.deepcopy(desc)
        self._ctl = d.get("controls") or {}
        styles = d.get("textStyles") or {}
        for _, L in _all_layers(d):
            tx = L.get("text")
            if tx and tx.get("textStyle"):
                t2 = dict(styles[tx["textStyle"]])
                t2.update({k: v for k, v in tx.items() if k != "textStyle"})
                L["text"] = t2
        d = self.tokens(d)
        for _, L in _all_layers(d):  # a scale track mixing 100 and [sx, sy]: all [sx, sy] (fusion_v2 F5)
            ks = (L.get("keys") or {}).get("scale") or []
            if len({isinstance(k[1], list) for k in ks}) > 1:
                for k in ks:
                    k[1] = k[1] if isinstance(k[1], list) else [k[1], k[1]]
        self.byid = {L["id"]: L for _, L in _all_layers(d)}
        self.desc = d
        self.holder = {}
        for name, a in (d.get("assets") or {}).items():
            size = self.lay_container(a, a.get("size"), "assets/" + name)
            a["size"] = list(size)
        self.lay_container(d, d["size"], "scene", root=True)
        return d

    def tokens(self, obj, key=None):
        if isinstance(obj, dict):
            return {k: self.tokens(v, k) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.tokens(v, key) for v in obj]
        if isinstance(obj, str) and key in self.TOKEN_FIELDS and obj.startswith("$"):
            v = self._ctl.get(obj[1:])
            if not isinstance(v, (int, float)):
                raise SceneError("INVALID_ARGS", f"{key} {obj}: geometry tokens must be number controls")
            return float(v)
        return obj

    def lbox(self, L):
        """Layout box in container px relative to the layer position (text: cap top to last baseline), static scale applied."""
        if L["type"] in ("camera", "light", "null"):
            return [0.0, 0.0, 0.0, 0.0]
        self._box.pop(L["id"], None)
        b = self.text_box(L, layout=True) if L["type"] == "text" else self.content_box(L)
        A = self.anchor(L, b if L["type"] != "text" else [0, 0, 0, 0])
        s = L.get("scale", 100)
        sx, sy = (float(s[0]) / 100, float(s[1]) / 100) if isinstance(s, (list, tuple)) else (float(s) / 100, float(s) / 100)
        return [(b[0] - A[0]) * sx, (b[1] - A[1]) * sy, (b[2] - A[0]) * sx, (b[3] - A[1]) * sy]

    def place(self, L, x=None, y=None):
        p = list(L.get("position") or [None, None])
        p += [None] * (2 - len(p))
        if x is not None:
            p[0] = x
        if y is not None:
            p[1] = y
        cw, ch = self.container_size_of(L)
        p[0] = cw / 2 if p[0] is None else p[0]
        p[1] = ch / 2 if p[1] is None else p[1]
        L["position"] = p

    def lay_container(self, C, size, where, root=False, outer=None):
        layers = C.get("layers") or []
        draw = [L for L in layers if L["type"] not in ("camera", "light", "null")]
        lay = C.get("layout")
        if size is None and not lay:
            if root:
                size = self.desc["size"]
            elif outer:
                size = outer  # a group without size or layout is as big as its container (a full-frame precomp)
            else:
                raise SceneError("INVALID_ARGS", f"{where}: a group or asset needs size (or a layout that sizes it)")
        for L in layers:
            self.holder[L["id"]] = C if C is not self.desc else None
            if L["type"] == "group" and L.get("layers") is not None:
                L["size"] = list(self.lay_container(L, L.get("size"), where + "/" + L["id"], outer=size))
        cw, ch = (float(size[0] or 0), float(size[1] or 0)) if size else (0.0, 0.0)
        for L in layers:
            self.cont_size[L["id"]] = (cw, ch)
            if L["type"] == "camera" and L.get("lens") and not L.get("zoom"):
                L["zoom"] = cw * float(L["lens"]) / 36.0  # AE: zoom = comp width x focal length / 36 mm film back
        if lay:
            cw, ch = self.layout(C, lay, draw, size)
            for L in layers:
                self.cont_size[L["id"]] = (cw, ch)
        pending = {L["id"]: L for L in layers if L.get("align")}
        for L in layers:
            if L["id"] in pending:
                if lay and L in draw:
                    self.warnings.append("%s: align is ignored inside a layout container" % L["id"])
                    continue
                self.align(L, pending, cw, ch, root)
        for L in layers:
            if L.get("offset"):
                self.place(L)
                L["position"][0] += float(L["offset"][0])
                L["position"][1] += float(L["offset"][1])
        st = C.get("stagger")
        if st:
            n = len(draw)
            order = list(range(n))
            rank = {"forward": order, "reverse": order[::-1],
                    "center": [abs(i - (n - 1) / 2.0) for i in order]}[st.get("order", "forward")]
            each = float(st.get("each", 3))
            for i, L in enumerate(draw):
                for kind in ("enter", "exit"):
                    if st.get(kind) and not L.get(kind):
                        mv = self.move_spec(st[kind], kind)
                        mv["at"] = mv.get("at", 0) + rank[i] * each
                        L[kind] = mv
        for L in layers:
            self.line_moves(L)
            self.moves(L)
        return (cw, ch)

    def layout(self, C, lay, draw, size):
        pad = lay.get("padding", 0)
        pad = [float(pad)] * 4 if isinstance(pad, (int, float)) else [float(x) for x in pad]
        if len(pad) == 2:
            pad = [pad[0], pad[1], pad[0], pad[1]]
        pt, pr, pb, pl = (pad + pad)[:4]
        align = lay.get("align", "start")
        if lay["type"] == "stack":
            vert = lay.get("direction", "vertical") == "vertical"
            gap = float(lay.get("gap", 0) if not isinstance(lay.get("gap"), list) else lay["gap"][0])
            for L in draw:
                if L["type"] == "text" and not (L.get("text") or {}).get("align") and vert:
                    L["text"]["align"] = {"start": "left", "center": "center", "end": "right"}[align]
            boxes = [self.lbox(L) for L in draw]
            cross = max([(b[2] - b[0]) if vert else (b[3] - b[1]) for b in boxes] or [0])
            main = sum((b[3] - b[1]) if vert else (b[2] - b[0]) for b in boxes) + gap * max(0, len(boxes) - 1)
            cw = float(size[0]) if size and size[0] is not None else (pl + (cross if vert else main) + pr)
            ch = float(size[1]) if size and size[1] is not None else (pt + (main if vert else cross) + pb)
            cur = pt if vert else pl
            for L, b in zip(draw, boxes):
                if vert:
                    x0, x1 = pl, cw - pr
                    x = {"start": x0 - b[0], "center": (x0 + x1) / 2 - (b[0] + b[2]) / 2, "end": x1 - b[2]}[align]
                    self.place(L, x, cur - b[1])
                    cur += (b[3] - b[1]) + gap
                else:
                    y0, y1 = pt, ch - pb
                    y = {"start": y0 - b[1], "center": (y0 + y1) / 2 - (b[1] + b[3]) / 2, "end": y1 - b[3]}[align]
                    self.place(L, cur - b[0], y)
                    cur += (b[2] - b[0]) + gap
        else:
            n = int(lay.get("columns", 3))
            g = lay.get("gap", 0)
            gx, gy = (float(g[0]), float(g[1])) if isinstance(g, list) else (float(g), float(g))
            boxes = [self.lbox(L) for L in draw]
            cell = lay.get("cell") or [max([b[2] - b[0] for b in boxes] or [0]), max([b[3] - b[1] for b in boxes] or [0])]
            cwc, chc = float(cell[0]), float(cell[1])
            rows = (len(draw) + n - 1) // n
            cw = float(size[0]) if size and size[0] is not None else pl + n * cwc + (n - 1) * gx + pr
            ch = float(size[1]) if size and size[1] is not None else pt + rows * chc + (rows - 1) * gy + pb
            for i, (L, b) in enumerate(zip(draw, boxes)):
                r, c = divmod(i, n)
                x0, y0 = pl + c * (cwc + gx), pt + r * (chc + gy)
                if align == "start":
                    self.place(L, x0 - b[0], y0 - b[1])
                elif align == "end":
                    self.place(L, x0 + cwc - b[2], y0 + chc - b[3])
                else:
                    self.place(L, x0 + cwc / 2 - (b[0] + b[2]) / 2, y0 + chc / 2 - (b[1] + b[3]) / 2)
        self.decisions.append("layout %s (%s): %d items in %gx%g" % (lay["type"], C.get("id", "scene"), len(draw), cw, ch))
        return cw, ch

    def safe_rect(self, cw, ch):
        sa = self.desc.get("safeArea", 0.05)
        sx, sy = (sa, sa) if isinstance(sa, (int, float)) else sa
        mx = sx * cw if sx <= 1 else sx
        my = sy * ch if sy <= 1 else sy
        return [mx, my, cw - mx, ch - my]

    def align(self, L, pending, cw, ch, root):
        pending.pop(L["id"], None)
        al = L["align"]
        if isinstance(al, str):
            ax, ay = ALIGN_WORDS[al]
            al = {"x": ax, "y": ay}
        to = al.get("to", "safe" if root else "frame")
        if to == "frame" or to == "parent" or (to == "safe" and not root):
            T = [0.0, 0.0, cw, ch]
        elif to == "safe":
            T = self.safe_rect(cw, ch)
        else:
            O = self.byid[to]
            chain, G = [O], self.holder.get(O["id"])
            while G is not None and G.get("id"):
                chain.append(G)
                G = self.holder.get(G["id"])
            for X in chain:
                if X["id"] in pending:
                    self.align(X, pending, cw, ch, root)
            T = self.rect_out(O, self.holder.get(L["id"]))
        place = al.get("place", "inside")
        gap = float(al.get("gap", 0))
        ax = al.get("x", "center" if place in ("inside", "above", "below") else None)
        ay = al.get("y", "center" if place in ("inside", "left", "right") else None)
        tx = L.get("text")
        authored = (self.authored_layer(L["id"]).get("text") or {})
        if tx is not None and not authored.get("align") and not (authored.get("textStyle") and
                                                                  (self.desc.get("textStyles") or {}).get(authored["textStyle"], {}).get("align")):
            tx["align"] = {"left": "left", "center": "center", "right": "right", None: tx.get("align", "left")}[
                ax if place in ("inside", "above", "below") else ("right" if place == "left" else "left")]
        b = self.lbox(L)
        x = y = None
        if place in ("inside", "above", "below"):
            x = {"left": T[0] - b[0], "center": (T[0] + T[2]) / 2 - (b[0] + b[2]) / 2, "right": T[2] - b[2], None: None}[ax]
        if place in ("inside", "left", "right"):
            y = {"top": T[1] - b[1], "center": (T[1] + T[3]) / 2 - (b[1] + b[3]) / 2, "bottom": T[3] - b[3], None: None}[ay]
        if place == "above":
            y = T[1] - gap - b[3]
        elif place == "below":
            y = T[3] + gap - b[1]
        elif place == "left":
            x = T[0] - gap - b[2]
        elif place == "right":
            x = T[2] + gap - b[0]
        off = al.get("offset") or [0, 0]
        self.place(L, None if x is None else x + float(off[0]), None if y is None else y + float(off[1]))

    def rect_out(self, O, where):
        """Layout rect of layer O in the container `where` (None = the scene), through the static rest transforms of the groups
        that hold it (a cursor at the scene level can target a button inside a card)."""
        cw, ch = self.container_size_of(O)
        ob = self.lbox(O)
        op = O.get("position") or [cw / 2, ch / 2]
        r = [op[0] + ob[0], op[1] + ob[1], op[0] + ob[2], op[1] + ob[3]]
        G = self.holder.get(O["id"])
        while G is not where and G is not None and G.get("id"):
            gw, gh = G.get("size") or self.container_size_of(G)
            A = G.get("anchor") or [gw / 2, gh / 2]
            s = G.get("scale", 100)
            s = (float(s[0]) if isinstance(s, (list, tuple)) else float(s)) / 100
            gp = G.get("position") or list(self.container_size_of(G))
            if not G.get("position"):
                gp = [gp[0] / 2, gp[1] / 2]
            r = [gp[0] + (r[0] - A[0]) * s, gp[1] + (r[1] - A[1]) * s, gp[0] + (r[2] - A[0]) * s, gp[1] + (r[3] - A[1]) * s]
            G = self.holder.get(G["id"])
        return r

    def authored_layer(self, lid):
        for _, L in _all_layers(self.authored):
            if L["id"] == lid:
                return L
        return {}

    def move_spec(self, mv, kind):
        mv = {"preset": mv} if isinstance(mv, str) else dict(mv)
        base = dict(MOVES.get(mv.pop("preset", None), {}))
        base.update(mv)
        base.setdefault("duration", 12)
        if kind == "enter":
            base.setdefault("at", 0)
        return base

    def line_moves(self, L):
        """A cascade with stagger 0 that only offsets and fades moves the whole line: animate the Merge (the rasterized text stays
        static, frozen, and motion blur resamples the transform) instead of re-rendering Text+ per motion-blur sample; layer-space
        masks stay put by drawing them in container space at the rest pose (the AE LineBox reveal)."""
        ans = L.get("animators") or []
        if L["type"] != "text" or len(ans) != 1 or ans[0]["type"] != "cascade" or float(ans[0].get("stagger", 2)) != 0:
            return
        an = ans[0]
        fr = an.get("from") or {"y": 40, "opacity": 0}
        if set(fr) - {"x", "y", "opacity"} or set(L.get("keys") or {}) & {"position", "opacity"} or L.get("parent") or self.is3d(L) \
                or set(L.get("keys") or {}) & {"scale", "rotation"}:
            return
        L.pop("animators")
        if L.get("enter"):
            self.warnings.append("%s: enter is ignored: the line animator already moves the layer" % L["id"])
        L["enter"] = {"at": float(an["start"]), "duration": float(an.get("duration", 12)), "ease": an.get("ease"), "from": dict(fr)}
        if L.get("masks"):
            L["_containerMasks"] = True
        self.decisions.append("%s: whole-line rise as a Merge move (static text, frozen; masks in container space)" % L["id"])

    def moves(self, L):
        """enter/exit -> keys around the laid-out rest state (position, opacity, scale, rotation)."""
        specs = [(k, self.move_spec(L[k], k)) for k in ("enter", "exit") if L.get(k)]
        if not specs:
            return
        cw, ch = self.container_size_of(L)
        rest = list(L.get("position") or [cw / 2, ch / 2])
        op = L.get("opacity", 100)
        rop = float(op) if isinstance(op, (int, float)) else 100.0
        sc = L.get("scale", 100)
        rsc = float(sc) if isinstance(sc, (int, float)) else float(sc[0])
        rot = L.get("rotation", 0)
        rrot = float(rot) if isinstance(rot, (int, float)) else 0.0
        keys = L.setdefault("keys", {})
        own = set(keys)
        for kind, mv in specs:
            if kind == "exit" and "at" not in mv:
                raise SceneError("INVALID_ARGS", f"{L['id']}: exit needs at (the frame it starts)")
            a = float(mv["at"])
            b = a + float(mv["duration"])
            e = mv.get("ease")
            delta = mv.get("from") if kind == "enter" else mv.get("to")
            for prop, rv, fn in (("position", rest, lambda d: [rest[0] + d.get("x", 0), rest[1] + d.get("y", 0)] + (
                                     [rest[2] + d.get("z", 0)] if len(rest) > 2 else [])),
                                 ("opacity", rop, lambda d: float(d["opacity"])),
                                 ("scale", rsc, lambda d: float(d["scale"])),
                                 ("rotation", rrot, lambda d: rrot + float(d["rotation"]))):
                touched = {"position": ("x", "y", "z"), "opacity": ("opacity",), "scale": ("scale",), "rotation": ("rotation",)}[prop]
                if not any(t in delta for t in touched):
                    continue
                if prop in own:
                    self.warnings.append("%s: %s keys given explicitly; %s leaves %s alone" % (L["id"], prop, kind, prop))
                    continue
                if prop == "opacity" and not isinstance(op, (int, float)):
                    self.warnings.append("%s: opacity is a control; %s animates from 100" % (L["id"], kind))
                v = fn(delta)
                seg = [[a, v, e], [b, rv]] if kind == "enter" else [[a, rv, e], [b, v]]
                ks = keys.setdefault(prop, [])
                if ks and ks[-1][0] >= seg[0][0]:
                    raise SceneError("INVALID_ARGS", f"{L['id']}: exit at {a} starts before the enter ends ({ks[-1][0]})")
                ks += seg

    # ------------------------------------------------------------ names, controls
    def n(self, *parts):
        return "_".join([self.S] + [p for p in (self.ns,) + parts if p])

    def lset(self, L, name):
        self.layers.setdefault(L["id"], []).append(name)
        return name

    def ctrl_ref(self, name, ch=None):
        return "%s_CTRL.%s%s" % (self.S, name, ch or "")

    def color(self, c, ch_names=("Red", "Green", "Blue", "Alpha")):
        """-> {chan: value|Expr} for a color value (hex, list, or $control)."""
        if isinstance(c, str) and c.startswith("$"):
            name = c[1:]
            base = hexrgba(self.desc["controls"][name])
            out = {}
            for i, ch in enumerate(ch_names[:3]):
                out[ch] = Expr(self.ctrl_ref(name, ("Red", "Green", "Blue")[i]), base[i])
            out[ch_names[3]] = base[3]
            return out
        r = hexrgba(c)
        return dict(zip(ch_names, r))

    def bg_color(self, c, prefix="TopLeft"):
        """Background tool colour inputs, premultiplied: Fusion reads a Background's RGB as premultiplied by its alpha, so an
        unpremultiplied #FFFFFF21 card composited as solid white [sb3, live]. Shape fills are unaffected (Alpha 1 + Opacity)."""
        ins = self.color(c, tuple(prefix + ch for ch in ("Red", "Green", "Blue", "Alpha")))
        a = ins[prefix + "Alpha"]
        if isinstance(a, (int, float)) and a < 1:
            for ch in ("Red", "Green", "Blue"):
                v = ins[prefix + ch]
                ins[prefix + ch] = Expr("(%s)*%s" % (v.e, _num(a)), (v.v or 0) * a) if isinstance(v, Expr) else v * a
        return ins

    def scalar(self, v, sign=1.0, scale=1.0, offset=0.0):
        """number | '$ctrl' | {expr, value} -> float or Expr (value * scale * sign + offset)."""
        if isinstance(v, (int, float)):
            return offset + sign * scale * v
        if isinstance(v, str):
            e = self.ctrl_ref(v[1:])
            base = float(self.desc["controls"][v[1:]])
        else:
            e = re.sub(r"\$([A-Za-z_]\w*)", lambda m: self.ctrl_ref(m.group(1)), v["expr"])
            base = float(v.get("value", 0))
        f = sign * scale
        ex = "(%s)" % e if f == 1 else "(%s)*%s" % (e, _num(f))
        if offset:
            ex = "%s + %s" % (ex, _num(offset))
        return Expr(ex, offset + f * base)

    @staticmethod
    def sval(v):
        """Static numeric value of a scalar field (for analysis)."""
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict):
            return float(v.get("value", 0))
        return 0.0

    def build_ctrl(self):
        name = self.n("CTRL")
        inputs, uc, grp = {}, [], 0
        draft = 1 if self.cfg["quality"] == "draft" else 0
        inputs["Draft"] = draft
        uc.append('Draft = { LINKS_Name = "Draft (1 = motion blur and 3D accumulation off)", LINKID_DataType = "Number", '
                  'INPID_InputControl = "SliderControl", INP_Integer = true, INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 1, '
                  'ICS_ControlPage = "Controls", },')
        if self.has_dof:
            inputs["FocusBlur"] = 100
            uc.append('FocusBlur = { LINKS_Name = "Focus Blur (%, 0 = all sharp)", LINKID_DataType = "Number", '
                      'INPID_InputControl = "SliderControl", INP_Default = 100, INP_MinScale = 0, INP_MaxScale = 200, ICS_ControlPage = "Controls", },')
        for k, v in (self.desc.get("controls") or {}).items():
            # user-control definitions never carry the values (values live in Inputs), so a token edit is a plain set
            if isinstance(v, (int, float)):
                inputs[k] = v
                uc.append('%s = { LINKS_Name = "%s", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", '
                          'ICS_ControlPage = "Controls", },' % (k, k))
            else:
                grp += 1
                r = hexrgba(v)
                uc.append('%s = { LINKS_Name = "%s", LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = %d, '
                          'IC_ControlID = -1, ICS_ControlPage = "Palette", },' % (k, k, grp))
                for cid, ch in enumerate(("Red", "Green", "Blue")):
                    inputs[k + ch] = r[cid]
                    uc.append('%s%s = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", IC_ControlGroup = %d, '
                              'IC_ControlID = %d, ICS_ControlPage = "Palette", },' % (k, ch, grp, cid))
        src = self.desc.get("controlsFrom")
        if src and src != self.S:   # [sb3 item 8] one controller per film: this CTRL's values follow <src>_CTRL by expression
            linked = [k for k in inputs if k != "FocusBlur"]
            for k in linked:
                inputs[k] = Expr("%s_CTRL.%s" % (src, k), inputs[k])
            self.decisions.append("controls follow %s_CTRL (Draft%s): edit them there" % (src, "".join(", " + k for k in (self.desc.get("controls") or {}))))
        self.g.add(name, "Custom", inputs, pos=(-2, -3), uc=uc)
        self.ctrl = name

    def draft_off(self, on_expr="1"):
        """Expression: 0 in draft, else on_expr."""
        return "iif(%s > 0.5, 0, %s)" % (self.ctrl_ref("Draft"), on_expr)

    # ------------------------------------------------------------ properties
    def track(self, L, prop):
        ks = (L.get("keys") or {}).get(prop)
        if not ks:
            return None
        key = (L["id"], prop)
        tr = self._tracks.get(key)
        if tr is None or tr.src is not ks:
            tr = self._tracks[key] = Track(ks, self.eases)
            tr.src = ks
        return tr

    def prop_at(self, L, prop, t, default):
        tr = self.track(L, prop)
        if tr:
            return tr.at(t)
        v = L.get(prop, default)
        return v

    def scale_at(self, L, t):
        s = self.prop_at(L, "scale", t, 100)
        if isinstance(s, (list, tuple)):
            return float(s[0]), float(s[1])
        return float(s), float(s)

    def is3d(self, L):
        if L["type"] in ("camera", "light"):
            return True
        pos = L.get("position") or []
        kpos = (L.get("keys") or {}).get("position") or []
        return bool(L.get("threeD") or len(pos) == 3 or any(len(k[1]) == 3 for k in kpos) or "rotationX" in L or "rotationY" in L
                    or "rotationX" in (L.get("keys") or {}) or "rotationY" in (L.get("keys") or {}))

    def span(self, L):
        return max(0, int(math.ceil(L.get("in", 0)))), min(self.dur, int(math.ceil(L.get("out", self.dur))))

    def visible_frames(self, L):
        """Per comp frame: visible (inside in/out and opacity > 0 at f or across the shutter)."""
        a, b = self.span(L)
        tr = self.track(L, "opacity")
        st = self.sval(L.get("opacity", 100))
        out = []
        for f in range(self.dur):
            if not (a <= f < b):
                out.append(False)
            elif tr:
                out.append(any(tr.at(f + d) > 1e-6 for d in (-0.5, 0, 0.5)))
            else:
                out.append(st > 1e-6 or isinstance(L.get("opacity"), (str, dict)))
        return out

    def default_anchor(self, L, box):
        if L["type"] in ("text", "path", "null"):
            return (0.0, 0.0)
        return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    def anchor(self, L, box):
        a = L.get("anchor")
        return (float(a[0]), float(a[1])) if a else self.default_anchor(L, box)

    def has_pivot(self, L):
        """Rotation or non-identity scale anywhere: the canvas is centered on the anchor (Merge scales/rotates about its FG center)."""
        k = L.get("keys") or {}
        s = L.get("scale", 100)
        if "scale" in k or "rotation" in k:
            return True
        if isinstance(s, (list, tuple)) and any(abs(float(x) - 100) > 1e-9 for x in s[:2]):
            return True
        if isinstance(s, (int, float)) and abs(s - 100) > 1e-9:
            return True
        return bool(self.sval(L.get("rotation", 0))) or isinstance(L.get("rotation"), (str, dict))

    def max_scale(self, L):
        tr = self.track(L, "scale")
        if tr:
            vals = [max(v) if isinstance(v, (list, tuple)) else v for v in tr.v]
            ts = [tr.at(f) for f in range(self.dur)]
            vals += [max(v) if isinstance(v, (list, tuple)) else v for v in ts]
            return max(abs(float(x)) for x in vals) / 100.0
        s = L.get("scale", 100)
        return max(abs(float(x)) for x in (s[:2] if isinstance(s, (list, tuple)) else [s])) / 100.0

    # ------------------------------------------------------------ entry
    def run(self):
        d = self.desc
        self.has_dof = any(L["type"] == "camera" and L.get("dof") for _, L in _all_layers(d))
        self.build_ctrl()
        root = Space(self.W, self.H, self.W / 2.0, self.H / 2.0, 1.0, self.W, self.H)
        smooth = self.container_smooth(d.get("layers") or [], d.get("background"))
        depth = self.depth_for(smooth)
        base = self.n("BG")
        bg = d.get("background")
        self.background(base, bg, root, depth, pos=(0, 0), full=True)
        out = self.stack(d["layers"], root, base, x0=1, y0=0, path="")
        final = self.n("Out")
        if d.get("grain"):
            gr = d["grain"]
            self.g.add(final, "FilmGrain", {"Input": Src(out), "LogProcessing": 0, "MasterStrength": gr.get("strength", 0.012),
                                            "MasterXSize": gr.get("size", 1.0), "Monochrome": 1 if gr.get("mono", True) else 0},
                       pos=(self.col_end + 1, 0))
            self.decisions.append("grain: FilmGrain LogProcessing 0 (grain does not scale with brightness, rebuild K17)")
        else:
            self.g.add(final, "PipeRouter", {"Input": Src(out)}, pos=(self.col_end + 1, 0))
        self.g.t[final]["custom"] = {ROOT_KEY: json.dumps(self.authored, separators=(",", ":"), sort_keys=True), "sbVersion": VERSION}
        self.placement_check()
        self.start = int(d.get("start", 0))
        if self.start:
            self.shift(self.start)
        return self

    def placement_check(self):
        """[sb3 item 9] Warn when a description looks like it assumes the opposite of the AE conventions the builder follows: path
        points are offsets from the layer's position, and an anchor moves the layer onto the position."""
        for _, L in _all_layers(self.desc):
            if L["type"] in ("camera", "light", "null") or self.is3d(L):
                continue
            A0 = self.authored_layer(L["id"])
            cw, ch = self.container_size_of(L)
            box = self.box(L)
            pos = self.prop_at(L, "position", 0, [cw / 2, ch / 2])
            A = self.anchor(L, box)

            def out(dx, dy):
                return box[0] + dx < -0.1 * cw or box[1] + dy < -0.1 * ch or box[2] + dx > 1.1 * cw or box[3] + dy > 1.1 * ch
            if L["type"] == "path" and "position" in A0 and not out(0, 0) and out(pos[0] - A[0], pos[1] - A[1]) \
                    and math.hypot(pos[0], pos[1]) > 0.1 * min(cw, ch):
                self.warnings.append("%s: path points are offsets from the layer's position (AE shape paths); these look like absolute "
                                     "coordinates and land off frame at position %s: use position [0, 0] or subtract it" % (L["id"], list(pos)[:2]))
            elif A0.get("anchor") is not None and not (set(L.get("keys") or {}) & {"scale", "rotation"}) and not self.has_pivot(L) \
                    and L["type"] != "path":
                d0 = self.default_anchor(L, box)
                if out(pos[0] - A[0], pos[1] - A[1]) and not out(pos[0] - d0[0], pos[1] - d0[1]):
                    self.warnings.append("%s: anchor %s moves the layer (AE anchor point: that layer point lands on position) and puts it "
                                         "off frame; without scale or rotation it pivots nothing: drop it or move position too"
                                         % (L["id"], list(A0["anchor"])))

    def shift(self, S):
        """Place the scene at comp frame S (one comp for a whole film): keys and handles +S, `time` in expressions -> time - S,
        enabled regions +S. Texture holds keep absolute time; freezes sample the scene's first frame."""
        # splines whose VALUES are times (a TimeStretcher SourceTime warp) move in value too, or the warp samples the wrong
        # frames (efficiency lab one-comp: a title cascade re-timed by the scene start when only key times moved)
        warp = {v.op for r in self.g.t.values() if r["reg"] == "TimeStretcher"
                for iid, v in r["inputs"].items() if iid == "SourceTime" and isinstance(v, Src)}
        for n, r in self.g.t.items():
            if r["reg"] == "BezierSpline":
                dv = S if n in warp else 0
                for k in r["keys"]:
                    k["f"] += S
                    k["v"] += dv
                    for h in ("RH", "LH"):
                        if h in k:
                            k[h] = (k[h][0] + S, k[h][1] + dv)
                continue
            for iid, v in list(r["inputs"].items()):
                if r["reg"] == "TimeStretcher" and iid == "SourceTime":
                    if not isinstance(v, Expr):
                        r["inputs"][iid] = S
                    continue
                if isinstance(v, Expr) and re.search(r"\btime\b", v.e):
                    r["inputs"][iid] = Expr(re.sub(r"\btime\b", "(time - %d)" % S, v.e), v.v)
        # a never-visible region ([-2, -1]) stays before the comp: shifted it would land in the previous scene's frames
        self.regions = {t: ([a, b] if b < 0 else [a + S, b + S]) for t, (a, b) in self.regions.items()}
        self.decisions.append("scene placed at comp frame %d: keys, expressions and regions shifted" % S)

    # ------------------------------------------------------------ containers
    def container_smooth(self, layers, bg):
        def smooth(L):
            if isinstance(L.get("fill"), dict) or any(e["type"] in ("glow", "blur", "shadow") for e in L.get("effects") or []):
                return True
            return False
        return isinstance(bg, dict) or any(smooth(L) for L in layers)

    def depth_for(self, smooth):
        p = self.eff["depth"]
        if p == "auto":
            return DEPTH["float16"] if smooth else DEPTH["int8"]
        return DEPTH.get(p, DEPTH["int8"])

    def background(self, name, bg, space, depth, pos, full=False, radius=0.0):
        """Container base canvas: color, gradient or transparent. When the canvas is larger than the container rect (anchor-centered
        or padded group), a colored background is cut to the rect by a RectangleMask."""
        ins = {"Width": _even(space.W), "Height": _even(space.H), "UseFrameFormatSettings": 0, "Depth": depth}
        if full and space.W == self.W and space.H == self.H:
            ins = {"UseFrameFormatSettings": 1, "Depth": depth}
        if bg is None:
            ins.update(TopLeftRed=0, TopLeftGreen=0, TopLeftBlue=0, TopLeftAlpha=0)
        elif isinstance(bg, dict):
            ins.update(self.gradient_inputs(bg["gradient"], space))
        else:
            ins.update(self.bg_color(bg))
        exact = abs(space.cx - space.cw / 2) < 1e-6 and abs(space.cy - space.ch / 2) < 1e-6 and \
            _even(space.cw * space.k) == _even(space.W) and _even(space.ch * space.k) == _even(space.H)
        if bg is not None and (not exact or radius):
            mi = {"Center": space.uv(space.cw / 2, space.ch / 2), "Width": space.cw * space.k / space.W, "Height": space.ch * space.k / space.H}
            if radius:
                mi["CornerRadius"] = min(1.0, float(radius) / (min(space.cw, space.ch) / 2.0))
            m = self.g.add(name + "_Rect", "RectangleMask", mi, pos=(pos[0], pos[1] - 1))
            ins["EffectMask"] = Src(m, "Mask")
        self.g.add(name, "Background", ins, pos=pos)
        return name

    def gradient_inputs(self, gr, space):
        """Linear 2-stop ramps whose corner parameters stay in [0, 1] become a Corner Background (exact: a bilinear blend of a
        linear field; corners can follow controls). Other gradients use the Gradient type (static colors)."""
        typ = gr.get("type", "linear")
        a = gr.get("from", [0, 0])
        b = gr.get("to", [space.cw, space.ch] if typ == "linear" else [space.cw / 2 + space.cw / 2, space.ch / 2])
        if typ == "linear" and len(gr["stops"]) == 2:
            (p0, c0), (p1, c1) = gr["stops"]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dy * dy
            corners = {}
            for nm, (u, v) in (("TopLeft", (0, 1)), ("TopRight", (1, 1)), ("BottomLeft", (0, 0)), ("BottomRight", (1, 0))):
                x = space.cx + (u - 0.5) * space.W / space.k
                y = space.cy - (v - 0.5) * space.H / space.k
                t = ((x - a[0]) * dx + (y - a[1]) * dy) / L2 if L2 else 0.0
                corners[nm] = (t - p0) / (p1 - p0) if p1 != p0 else 0.0
            if all(-1e-6 <= t <= 1 + 1e-6 for t in corners.values()):
                ins = {"Type": FuID("Corner")}
                ca = self.color(c0, ("Red", "Green", "Blue", "Alpha"))
                cb = self.color(c1, ("Red", "Green", "Blue", "Alpha"))
                for nm, t in corners.items():
                    t = min(1.0, max(0.0, t))
                    for ch in ("Red", "Green", "Blue", "Alpha"):
                        va, vb = ca[ch], cb[ch]
                        if isinstance(va, Expr) or isinstance(vb, Expr):
                            ea = va.e if isinstance(va, Expr) else _num(va)
                            eb = vb.e if isinstance(vb, Expr) else _num(vb)
                            fa = va.v if isinstance(va, Expr) else va
                            fb = vb.v if isinstance(vb, Expr) else vb
                            ins[nm + ch] = Expr("%s + %s*(%s - %s)" % (ea, _num(t), eb, ea), fa + t * (fb - fa))
                        else:
                            ins[nm + ch] = va + t * (vb - va)
                    al = ins[nm + "Alpha"]
                    if isinstance(al, (int, float)) and al < 1:   # premultiplied like every Background colour (bg_color)
                        for ch in ("Red", "Green", "Blue"):
                            v = ins[nm + ch]
                            ins[nm + ch] = Expr("(%s)*%s" % (v.e, _num(al)), (v.v or 0) * al) if isinstance(v, Expr) else v * al
                return ins
        stops = []
        for pos, c in gr["stops"]:
            if isinstance(c, str) and c.startswith("$"):
                c = self.desc["controls"][c[1:]]
                self.warnings.append("gradient stops read controls once (static): Fusion gradients cannot hold expressions")
            stops.append((float(pos), hexrgba(c)))
        return {"Type": FuID("Gradient"), "GradientType": FuID("Radial" if typ == "radial" else "Linear"),
                "Start": space.uv(*a[:2]), "End": space.uv(*b[:2]), "Gradient": Grad(stops)}

    def is_static(self, L):
        """Same image on every frame: no keys or animators, whole-scene in/out, no time expressions, no grain; groups: all
        children static. (Controls are static values: editing one re-renders the frozen frame.)"""
        if L.get("keys") or L.get("animators") or any(e["type"] == "grain" for e in L.get("effects") or []):
            return False
        a, b = self.span(L)
        if a > 0 or b < self.dur:
            return False
        if any(isinstance(L.get(p), dict) and "time" in L[p].get("expr", "") for p in ("opacity", "rotation", "rotationX", "rotationY")):
            return False
        if any(P.get("keys") for P in self.parent_chain(L)) if L.get("parent") else False:
            return False
        if L.get("matte") and not self.is_static(self.byid[L["matte"]["layer"]]):
            return False
        if L["type"] == "group":
            body = self.desc["assets"][L["use"]] if L.get("use") else L
            return all(self.is_static(C) for C in body.get("layers") or [] if C["type"] not in ("light",)) and \
                not any(C["type"] == "camera" for C in body.get("layers") or [])
        return L["type"] not in ("camera",)

    def src_static(self, L):
        body = dict(L)
        for k in ("keys", "in", "out", "opacity", "rotation", "rotationX", "rotationY", "parent", "matte", "enter", "exit"):
            body.pop(k, None)
        ks = {k: v for k, v in (L.get("keys") or {}).items() if k in ("size", "trimStart", "trimEnd", "fill", "color", "text", "radius")}
        if ks:
            return False
        return self.is_static(body)

    def freeze(self, name, why):
        """Constant-time TimeStretcher: evaluated once and served from the cache on later frames, also in Deliver [lab T03].
        Never on a mask branch (lab rule, one-comp v3): a *Mask tool's output is Mask, so a freeze on it feeds nothing and its
        consumer silently loses its EffectMask; a track matte's image chain stays live too (mask_freezes() checks the graph)."""
        if self._mask_depth or self.g.t[name]["reg"].endswith("Mask"):
            self.decisions.append("%s: not frozen (mask branch)" % name)
            return name
        fz = name + "_Freeze"
        if fz not in self.g.t:
            pos = self.g.t[name].get("pos") or (self.cur_col, self.cur_y)
            self.g.add(fz, "TimeStretcher", {"Input": Src(name), "SourceTime": 0, "InterpolateBetweenFrames": 0}, pos=(pos[0] + 0.5, pos[1] - 0.5))
            self.stats["freezes"] += 1
            self.decisions.append("%s: frozen (%s)" % (name, why))
        return fz

    def stack(self, layers, space, base, x0, y0, path):
        """Composite layers (bottom to top) over base in one container. Returns the top tool. The static prefix (background and
        static layers under the first animated one) is frozen once."""
        cur, col = base, x0
        blocks = self.split_3d(layers)
        prefix, merged = True, False

        def gate(L):
            nonlocal cur, prefix
            if prefix and not self.is_static(L):
                prefix = False
                if merged and self.eff["freeze"]:
                    cur = self.freeze(cur, "static prefix of %s" % (path or "the scene"))
        for blk in blocks:
            if blk["kind"] == "3d":
                if prefix:
                    gate({"id": "_3d", "type": "null", "keys": {"x": 1}})
                cur = self.block3d(blk["layers"], blk["camera"], blk["lights"], space, cur, col, y0, path)
                col += 2
                continue
            batch = []
            for L in blk["layers"]:
                if self.batchable(L):
                    batch.append(L)
                    continue
                if batch:
                    cur = self.flush_batch(batch, space, cur, col, y0)
                    merged = True
                    col += 1
                    batch = []
                if L["type"] == "null" or (L["id"] in self.mattes and not L.get("visible")):
                    continue
                gate(L)
                cur = self.layer2d(L, space, cur, col, y0)
                merged = True
                col += 1
            if batch:
                cur = self.flush_batch(batch, space, cur, col, y0)
                merged = True
                col += 1
        self.col_end = col
        return cur

    def split_3d(self, layers):
        """Consecutive 3D layers form one render block (AE: 2D layers between 3D layers split the 3D stack)."""
        blocks, cur = [], None
        cams = [L for L in layers if L["type"] == "camera"]
        lights = [L for L in layers if L["type"] == "light"]
        for L in layers:
            if L["type"] in ("camera", "light"):
                continue
            if self.is3d(L) and L["type"] != "null":
                if cur is None or cur["kind"] != "3d":
                    cur = {"kind": "3d", "layers": [], "camera": cams[0] if cams else None, "lights": lights}
                    blocks.append(cur)
                cur["layers"].append(L)
            elif self.is3d(L) and L["type"] == "null":
                continue
            else:
                if cur is None or cur["kind"] != "2d":
                    cur = {"kind": "2d", "layers": []}
                    blocks.append(cur)
                cur["layers"].append(L)
        return blocks

    # ------------------------------------------------------------ shape batching
    def batchable(self, L):
        if not self.eff["batchShapes"] or L["type"] not in ("rect", "ellipse", "path"):
            return False
        if L.get("keys") or L.get("effects") or L.get("masks") or L.get("matte") or L.get("parent") or L["id"] in self.mattes or L.get("glass"):
            return False
        if L.get("blend", "normal") != "normal" or self.sval(L.get("opacity", 100)) != 100 or not isinstance(L.get("opacity", 100), (int, float)):
            return False
        if isinstance(L.get("fill"), dict) or L.get("trim") or not isinstance(L.get("rotation", 0), (int, float)):
            return False
        a, b = self.span(L)
        return a <= 0 and b >= self.dur

    def flush_batch(self, batch, space, cur, col, y0):
        name = self.n(batch[0]["id"], "Shapes") if len(batch) > 1 else self.n(batch[0]["id"], "Shape")
        items = []
        for j, L in enumerate(batch):
            items += self.sshapes(L, space, None, (col, y0 - 2 - j))
            self.lset(L, name)
        rend = self.srender(name, items, space.W, space.H, (col, y0 - 1))
        mname = self.n(batch[0]["id"]) if len(batch) == 1 else name + "_Mrg"
        self.g.add(mname, "Merge", {"Background": Src(cur), "Foreground": Src(rend), "PerformDepthMerge": 0}, pos=(col, y0))
        for L in batch:
            self.lset(L, mname)
        self.stats["batched"] += len(batch)
        if len(batch) > 1:
            self.decisions.append("%s: %d static shape layers share one sRender (%s)" % (name, len(batch), ", ".join(L["id"] for L in batch)))
        return mname

    def srender(self, name, items, W, H, pos):
        if len(items) > 1:
            sm = self.g.add(name + "_sMrg", "sMerge", {("Input%d" % (i + 1)): Src(it) for i, it in enumerate(items)}, pos=(pos[0], pos[1] - 1))
            src = sm
        else:
            src = items[0]
        return self.g.add(name, "sRender", {"Input": Src(src), "UseFrameFormatSettings": 0, "Width": _even(W), "Height": _even(H),
                                            "Depth": self.depth_for(False)}, pos=pos)

    def shape_geom(self, L):
        """(box in layer px, geometry center) for rect/ellipse/path."""
        if L["type"] in ("rect", "ellipse"):
            w, h = L.get("size", [100, 100])
            sizes = [L.get("size", [100, 100])] + [k[1] for k in (L.get("keys") or {}).get("size", [])]
            mw = max(float(s[0]) for s in sizes)
            mh = max(float(s[1]) for s in sizes)
            cx, cy = w / 2.0, h / 2.0
            box = [cx - mw / 2, cy - mh / 2, cx + mw / 2, cy + mh / 2]
        else:
            pts = [self.pt(p) for p in L["points"]]
            xs = [p[0] + d for p in pts for d in (0, p[2], p[4])]
            ys = [p[1] + d for p in pts for d in (0, p[3], p[5])]
            box = [min(xs), min(ys), max(xs), max(ys)]
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        sw = (L.get("stroke") or {}).get("width", 0) / 2.0 if L.get("stroke") else 0
        rep = L.get("repeat")
        if rep:
            dx, dy = (rep.get("offset") or [0, 0])[:2]
            n = rep["count"] - 1
            box = [min(box[0], box[0] + n * dx), min(box[1], box[1] + n * dy), max(box[2], box[2] + n * dx), max(box[3], box[3] + n * dy)]
        return [box[0] - sw, box[1] - sw, box[2] + sw, box[3] + sw], (cx, cy)

    @staticmethod
    def poly_pt(p, to_c, T):
        """Layer-px bezier point (x, y, in dx, in dy, out dx, out dy) -> sShape polyline point (canvas width units, Y up)."""
        x, y = to_c(p[0], p[1])
        px, py = T(x, y)
        if tuple(p[2:]) == (0, 0, 0, 0):
            return (px, py)
        L_ = T(*to_c(p[0] + p[2], p[1] + p[3]))
        R_ = T(*to_c(p[0] + p[4], p[1] + p[5]))
        return (px, py, L_[0] - px, L_[1] - py, R_[0] - px, R_[1] - py)

    # ------------------------------------------------------------ outlines: trims, dashes and tapers [sb3 items 4 and 7]
    KAPPA = 0.5522847498

    def outline_stroke(self, L):
        """A rect/ellipse stroke that is trimmed is drawn from its bezier outline (sPolygon): the write-on follows the outline
        from its documented start (ellipse: 12 o'clock, rect: top-left corner, both clockwise). Size-keyed shapes keep sRectangle /
        sEllipse (their size animates)."""
        ks = L.get("keys") or {}
        return L["type"] in ("rect", "ellipse") and "size" not in ks and bool(L.get("trim") or "trimEnd" in ks or "trimStart" in ks)

    def outline(self, L):
        """-> ([(x, y, in dx, in dy, out dx, out dy)], closed) in layer px: the path's points, or a rect/ellipse at its rest size."""
        if L["type"] == "path":
            return [self.pt(q) for q in L["points"]], bool(L.get("closed", True))
        w, h = (float(v) for v in L.get("size", [100, 100]))
        cx, cy, K = w / 2, h / 2, self.KAPPA
        if L["type"] == "ellipse":
            a, b = w / 2, h / 2
            return [(cx, cy - b, -K * a, 0, K * a, 0), (cx + a, cy, 0, -K * b, 0, K * b),
                    (cx, cy + b, K * a, 0, -K * a, 0), (cx - a, cy, 0, K * b, 0, -K * b)], True
        r = min(float(L.get("radius") or 0), w / 2, h / 2)
        if r <= 0:
            return [(0, 0, 0, 0, 0, 0), (w, 0, 0, 0, 0, 0), (w, h, 0, 0, 0, 0), (0, h, 0, 0, 0, 0)], True
        k = K * r
        return [(r, 0, -k, 0, 0, 0), (w - r, 0, 0, 0, k, 0), (w, r, 0, -k, 0, 0), (w, h - r, 0, 0, 0, k),
                (w - r, h, k, 0, 0, 0), (r, h, 0, 0, -k, 0), (0, h - r, 0, k, 0, 0), (0, r, 0, 0, 0, -k)], True

    @staticmethod
    def flatten(pts, closed, step=2.0, split_lines=False):
        """Bezier outline -> ([(x, y)] about `step` px apart, [arc length at each]) in layer px. Straight segments stay one piece
        unless split_lines (a taper needs widths along them)."""
        segs = list(zip(pts, pts[1:] + (pts[:1] if closed else [])))
        out = [(pts[0][0], pts[0][1])]
        for p0, p1 in segs:
            c = [(p0[0], p0[1]), (p0[0] + p0[4], p0[1] + p0[5]), (p1[0] + p1[2], p1[1] + p1[3]), (p1[0], p1[1])]
            approx = sum(math.hypot(c[i + 1][0] - c[i][0], c[i + 1][1] - c[i][1]) for i in range(3))
            straight = tuple(p0[4:6]) == (0, 0) and tuple(p1[2:4]) == (0, 0)
            n = 1 if straight and not split_lines else max(1 if straight else 4, int(math.ceil(approx / step)))
            for j in range(1, n + 1):
                u = j / float(n)
                if straight:   # even spacing (a cubic with coincident handles crowds its ends)
                    out.append((c[0][0] + u * (c[3][0] - c[0][0]), c[0][1] + u * (c[3][1] - c[0][1])))
                    continue
                out.append(tuple((1 - u) ** 3 * c[0][q] + 3 * (1 - u) ** 2 * u * c[1][q] + 3 * (1 - u) * u * u * c[2][q] + u ** 3 * c[3][q]
                                 for q in (0, 1)))
        cum = [0.0]
        for a, b in zip(out, out[1:]):
            cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        return out, cum

    @staticmethod
    def cut(flat, cum, a, b):
        """The polyline between arc lengths a and b (px), ends interpolated."""
        def at(s):
            i = max(0, min(len(cum) - 2, bisect.bisect_right(cum, s) - 1))
            d = cum[i + 1] - cum[i]
            u = 0.0 if d <= 0 else (s - cum[i]) / d
            return (flat[i][0] + u * (flat[i + 1][0] - flat[i][0]), flat[i][1] + u * (flat[i + 1][1] - flat[i][1]))
        inner = [flat[i] for i in range(len(flat)) if a < cum[i] < b]
        return [at(a)] + inner + [at(b)]

    def trim_frames(self, L):
        ks = [k[0] for p in ("trimStart", "trimEnd") for k in ((L.get("keys") or {}).get(p) or [])]
        return list(range(int(math.floor(min(ks))), int(math.ceil(max(ks))) + 1)) if ks else [0]

    def trim_at(self, L, t):
        """(start, end) visible fractions of the outline at time t."""
        tr = L.get("trim") or {}
        s = self.prop_at(L, "trimStart", t, tr.get("start", 0))
        e = self.prop_at(L, "trimEnd", t, tr.get("end", 100))
        return float(s) / 100, float(e) / 100

    def stroke_shapes(self, L, st, to_c, T, wscale, name, pos):
        """Dashed stroke: one open sPolygon per dash (the dash's own piece of the outline, so dash lengths do not depend on how
        Fusion parameterizes a write-on); a trim window clips each dash (WritePosition/WriteLength per dash, splines when trimmed
        in time). Tapered stroke: one filled sPolygon, the outline offset by the local half width; with trim keys the polygon is
        keyed per frame over the visible part (AE: the taper follows the trimmed stroke) [unverified live]."""
        pts, closed = self.outline(L)
        flat, cum = self.flatten(pts, closed)
        total = cum[-1]
        if st.get("taper"):
            flat, cum = self.flatten(pts, closed, max(2.0, total / 120.0), split_lines=True)
        keyed = bool(set(L.get("keys") or {}) & {"trimStart", "trimEnd"})
        fr = self.trim_frames(L) if keyed else [0]
        win = {f: self.trim_at(L, f) for f in fr}
        if "size" in (L.get("keys") or {}):
            self.warnings.append("%s: dash/taper follow the rest size; the size animation scales them" % L["id"])
        cc = self.color(st.get("color", "#FFFFFF"), ("Red", "Green", "Blue", "Alpha"))
        op = float(cc.pop("Alpha")) * float(st.get("opacity", 100)) / 100

        def style(ins, solid):
            ins.update(cc)
            ins["Alpha"] = 1
            if op != 1:
                ins["Opacity"] = op
            ins["Solid"] = 1 if solid else 0
            if not solid:
                ins["BorderWidth"] = float(st["width"]) * wscale
                ins["CapStyle"] = {"butt": 0, "round": 1, "square": 2}[st.get("cap", "butt")]
                if st.get("join"):
                    ins["JoinStyle"] = {"miter": 0, "round": 1, "bevel": 2}[st["join"]]
            return ins
        items = []
        if st.get("taper"):
            if st.get("dash"):
                self.warnings.append("%s: dash and taper together: the taper is drawn, the dash is ignored" % L["id"])
            nm = self.lset(L, name + "_Taper")
            polys = {f: self.taper_poly(L, st, flat, cum, *win[f], closed=closed) for f in fr}
            M = max(len(p) for p in polys.values())
            ins = style({}, True)
            if keyed and len({tuple(p) for p in polys.values()}) > 1:
                polys = {f: p + [p[-1]] * (M - len(p)) for f, p in polys.items()}   # a keyed polyline keeps its point count
                self.g.add(nm + "Polyline", "BezierSpline", owner=(nm, "Polyline"),
                           keys=[{"f": f, "v": 0, "lin": True, "poly": Poly((True, tuple(self.poly_pt(q + (0, 0, 0, 0), to_c, T) for q in polys[f])))}
                                 for f in fr])
                ins["Polyline"] = Src(nm + "Polyline", "Value")
                self.decisions.append("%s: tapered stroke keyed per frame over its trim (%d keys) [unverified live]" % (L["id"], len(fr)))
            else:
                ins["Polyline"] = Poly((True, tuple(self.poly_pt(q + (0, 0, 0, 0), to_c, T) for q in polys[fr[-1]])))
                self.decisions.append("%s: tapered stroke as a filled offset polygon (%d points)" % (L["id"], len(polys[fr[-1]])))
            self.g.add(nm, "sPolygon", ins, pos=(pos[0], pos[1] - 1))
            return [nm]
        pat = [float(x) for x in st["dash"]]
        pat = pat * 2 if len(pat) % 2 else pat
        period = sum(pat)
        if period <= 0 or max(pat[0::2]) < 0:
            raise SceneError("INVALID_ARGS", f"{L['id']}: stroke dash needs a positive pattern [on, off, ...] in px")
        dashes, s0, i = [], -float(st.get("dashOffset", 0)) % period - period, 0
        while s0 < total and len(dashes) <= 400:
            on = pat[i % len(pat)]
            a, b = max(0.0, s0), min(total, s0 + on)
            if b > a or (on == 0 and 0 <= s0 < total):
                dashes.append((a, max(b, a + 1e-3)))
            s0 += on + pat[(i + 1) % len(pat)]
            i += 2
        if len(dashes) > 400:
            raise SceneError("INVALID_ARGS", f"{L['id']}: the dash pattern makes over 400 dashes on a {total:.0f} px outline",
                             hint="lengthen the dash or the gap (each dash is one shape node)")
        n_drawn = 0
        for j, (a, b) in enumerate(dashes):
            lim = {f: (max(a, win[f][0] * total), min(b, win[f][1] * total)) for f in fr}
            if not any(e > s for s, e in lim.values()):
                continue   # never inside the trim window
            nm = self.lset(L, "%s_Dash%d" % (name, j + 1))
            ins = style({"Polyline": Poly((False, tuple(self.poly_pt(q + (0, 0, 0, 0), to_c, T) for q in self.cut(flat, cum, a, b))))}, False)
            pos_ = [max(0.0, (lim[f][0] - a) / (b - a)) for f in fr]
            len_ = [max(0.0, (lim[f][1] - lim[f][0]) / (b - a)) for f in fr]
            for iid, vals, full in (("WritePosition", pos_, 0.0), ("WriteLength", len_, 1.0)):
                if max(vals) - min(vals) > 1e-6:
                    ins[iid] = self.spline(nm, iid, *self.compress(fr, vals))
                elif abs(vals[0] - full) > 1e-6:
                    ins[iid] = vals[0]
            self.g.add(nm, "sPolygon", ins, pos=(pos[0] + 0.1 * j, pos[1] - 1))
            items.append(nm)
            n_drawn += 1
        self.decisions.append("%s: dashed stroke %s px: %d dashes on a %.0f px outline" % (L["id"], st["dash"], n_drawn, total))
        return items

    def taper_poly(self, L, st, flat, cum, fs, fe, closed=False):
        """Filled outline of a variable-width stroke over the visible part [fs, fe] (fractions) of the flattened path, as layer-px
        (x, y) points. Width along the visible part u in [0, 1] (AE taper): ramps from startWidth % over startLength % and to
        endWidth % over endLength %, eased by startEase/endEase %."""
        tp = st["taper"]
        W = float(st["width"])
        total = cum[-1]
        a, b = fs * total, fe * total
        if b - a < 1e-3:
            p = self.cut(flat, cum, a, a)[0]
            return [p, p, p]
        line = self.cut(flat, cum, a, b)
        acc = [0.0]
        for p, q in zip(line, line[1:]):
            acc.append(acc[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
        sl, el = float(tp.get("startLength", 0)) / 100, float(tp.get("endLength", 0)) / 100
        sw, ew = float(tp.get("startWidth", 0)) / 100, float(tp.get("endWidth", 0)) / 100
        se, ee = float(tp.get("startEase", 0)) / 100, float(tp.get("endEase", 0)) / 100

        def ease(x, e):
            return (1 - e) * x + e * (x * x * (3 - 2 * x))

        def width(u):
            f = 1.0
            if sl > 0 and u < sl:
                f = min(f, sw + (1 - sw) * ease(u / sl, se))
            if el > 0 and u > 1 - el:
                f = min(f, ew + (1 - ew) * ease((1 - u) / el, ee))
            return W * f / 2
        left, right = [], []
        for i, p in enumerate(line):
            p0, p1 = line[max(0, i - 1)], line[min(len(line) - 1, i + 1)]
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            ln = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / ln, dx / ln
            h = width(acc[i] / acc[-1] if acc[-1] else 0.0)
            left.append((p[0] + nx * h, p[1] + ny * h))
            right.append((p[0] - nx * h, p[1] - ny * h))
        return left + right[::-1]

    @staticmethod
    def pt(p):
        if isinstance(p, dict):
            q, i, o = p["p"], p.get("in", [0, 0]), p.get("out", [0, 0])
            return (float(q[0]), float(q[1]), float(i[0]), float(i[1]), float(o[0]), float(o[1]))
        return (float(p[0]), float(p[1]), 0.0, 0.0, 0.0, 0.0)

    def sshapes(self, L, space, local, pos, xf=None):
        """sShape tools (fill, stroke) for a shape layer drawn into a canvas. space maps canvas px; local maps layer px to
        canvas px (None = batch: bake the layer's static transform into container px)."""
        (box, (gcx, gcy)) = self.shape_geom(L)
        if local is None:
            s = self.scale_at(L, 0)
            rot = self.sval(L.get("rotation", 0))
            A = self.anchor(L, box)
            P = [float(x) for x in (L.get("position") or [space.cw / 2, space.ch / 2])[:2]]
            R = math.radians(rot)

            def to_c(x, y):
                dx, dy = (x - A[0]) * s[0] / 100, (y - A[1]) * s[1] / 100
                return (P[0] + dx * math.cos(R) - dy * math.sin(R), P[1] + dx * math.sin(R) + dy * math.cos(R))
            sx, sy, ang = s[0] / 100, s[1] / 100, -rot
        else:
            to_c, sx, sy, ang = local, 1.0, 1.0, 0.0
        k, CW = space.k, space.W

        def T(x, y):  # container px -> sShape units (fractions of canvas WIDTH from the canvas center, Y up)
            u, v = space.uv(x, y)
            return ((u - 0.5), (v - 0.5) * space.H / CW)
        items = []
        cx, cy = to_c(gcx, gcy)
        tx, ty = T(cx, cy)
        fill, st = L.get("fill", "#FFFFFF" if not L.get("stroke") else None), L.get("stroke")
        name = self.n(L["id"])
        for role, solid in (("Fill", True), ("Stroke", False)):
            if solid and fill is None or (not solid and not st):
                continue
            if not solid and (st.get("dash") or st.get("taper")):
                items += self.stroke_shapes(L, st, to_c, T, min(sx, sy) * k / CW, name, pos)
                continue
            nm = self.lset(L, name + "_" + role)
            ins = {}
            if not solid and self.outline_stroke(L):   # a trimmed rect/ellipse stroke: its bezier outline (sb3 item 7)
                pts = [self.poly_pt(p, to_c, T) for p in self.outline(L)[0]]
                ins["Polyline"] = Poly((True, tuple(pts)))
                reg = "sPolygon"
            elif L["type"] in ("rect", "ellipse"):
                w, h = L.get("size", [100, 100])
                ins.update({"Translate.X": tx, "Translate.Y": ty, "Width": w * sx * k / CW, "Height": h * sy * k / CW})
                if L["type"] == "rect" and L.get("radius"):
                    ins["CornerRadius"] = min(1.0, float(L["radius"]) / (min(w, h) / 2.0)) if min(w, h) > 0 else 0
                if ang:
                    ins["Angle"] = ang
                reg = "sRectangle" if L["type"] == "rect" else "sEllipse"
                sz = self.track(L, "size")
                if sz and local is not None:
                    f, vals, curves = sz.component(0, lambda v: v * k / CW)
                    ins["Width"] = self.spline(nm, "Width", f, vals, curves)
                    f, vals, curves = sz.component(1, lambda v: v * k / CW)
                    ins["Height"] = self.spline(nm, "Height", f, vals, curves)
            else:
                pts = [self.poly_pt(self.pt(q), to_c, T) for q in L["points"]]
                ins["Polyline"] = Poly((bool(L.get("closed", True)), tuple(pts)))
                reg = "sPolygon"
            col = fill if solid else st.get("color", "#FFFFFF")
            cc = self.color(col, ("Red", "Green", "Blue", "Alpha"))
            op = float(cc.pop("Alpha")) * (1.0 if solid else float(st.get("opacity", 100)) / 100)
            ins.update(cc)
            ins["Alpha"] = 1
            if op != 1:
                ins["Opacity"] = op
            ins["Solid"] = 1 if solid else 0
            if not solid:
                ins["BorderWidth"] = st["width"] * min(sx, sy) * k / CW
                if st.get("cap"):
                    ins["CapStyle"] = {"butt": 0, "round": 1, "square": 2}[st["cap"]]
                if st.get("join"):
                    ins["JoinStyle"] = {"miter": 0, "round": 1, "bevel": 2}[st["join"]]
                trim = L.get("trim")
                ks = L.get("keys") or {}
                if trim or "trimEnd" in ks or "trimStart" in ks:
                    t0 = float((trim or {}).get("start", 0)) / 100
                    ins["WritePosition"] = t0
                    ins["WriteLength"] = float((trim or {}).get("end", 100)) / 100 - t0
                    if "trimStart" in ks:   # [sb3] trimStart keys used to be dropped silently: position and length per frame
                        fr = self.trim_frames(L)
                        S, E = [self.trim_at(L, f)[0] for f in fr], [self.trim_at(L, f)[1] for f in fr]
                        ins["WritePosition"] = self.spline(nm, "WritePosition", *self.compress(fr, S))
                        ins["WriteLength"] = self.spline(nm, "WriteLength", *self.compress(fr, [max(0.0, e - a) for a, e in zip(S, E)]))
                    elif "trimEnd" in ks:
                        tr = self.track(L, "trimEnd")
                        f, vals, curves = tr.component(None, lambda v: v / 100 - t0)
                        ins["WriteLength"] = self.spline(nm, "WriteLength", f, vals, curves)
            self.g.add(nm, reg, ins, pos=(pos[0], pos[1] - (0 if solid else 1)))
            items.append(nm)
        rep = L.get("repeat")
        if rep:
            out = []
            for it in items:
                dx, dy = (rep.get("offset") or [0, 0])[:2]
                pv = T(*to_c(*(rep.get("pivot") or [gcx, gcy])[:2]))
                ins = {"Input": Src(it), "Copies": rep["count"] - 1, "XOffset": dx * sx * k / CW, "YOffset": -dy * sy * k / CW}
                if rep.get("rotation"):
                    ins.update(ZRotation=-float(rep["rotation"]), XPivot=pv[0], YPivot=pv[1], AxisMode=FuID("Absolute"))
                out.append(self.lset(L, self.g.add(it + "_Rep", "sDuplicate", ins, pos=(pos[0] + 0.5, pos[1]))))
            items = out
        return items

    def spline(self, host, iid, frames, vals, curves):
        name = host + iid.replace(".", "")
        self.g.add(name, "BezierSpline", keys=spline_keys(frames, vals, curves), owner=(host, iid))
        return Src(name, "Value")

    def xypath(self, host, iid, xs, ys):
        """Point animation: XYPath with X/Y splines (each (frames, vals, curves)) or statics."""
        name = host + iid.replace(".", "") + "Path"
        ins = {}
        for ax, data in (("X", xs), ("Y", ys)):
            if isinstance(data, tuple):
                sp = name + ax
                self.g.add(sp, "BezierSpline", keys=spline_keys(*data), owner=(name, ax))
                ins[ax] = Src(sp, "Value")
            else:
                ins[ax] = data
        self.g.add(name, "XYPath", ins, owner=(host, iid))
        return Src(name, "Value")

    # ------------------------------------------------------------ sources (layer image, anchor-aware canvas)
    def canvas(self, box, c, k, pad=0.0):
        x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
        hx = max(c[0] - x0, x1 - c[0], 1)
        hy = max(c[1] - y0, y1 - c[1], 1)
        return _even(2 * hx * k), _even(2 * hy * k)

    def effect_pad(self, L):
        pad = 0.0
        for e in L.get("effects") or []:
            if e["type"] == "blur":
                pad = max(pad, 3 * e.get("radius", 4))
            elif e["type"] == "glow":
                pad = max(pad, 3 * e.get("radius", 10))
            elif e["type"] == "shadow":
                off = e.get("offset", [0, 8])
                pad = max(pad, math.hypot(*off[:2]) + 2 * e.get("blur", 16))
        return pad

    def box(self, L):
        b = self._box.get(L["id"])
        if b is None:
            b = self._box[L["id"]] = self.content_box(L)
        return b

    def content_box(self, L):
        t = L["type"]
        if t in ("rect", "ellipse", "path"):
            return self.shape_geom(L)[0]
        if t == "text":
            return self.text_box(L)
        if t == "solid":
            w, h = L.get("size") or self.container_size_of(L)
            return [0, 0, w, h]
        if t == "image":
            w, h = L.get("size") or self.image_size(L["src"])
            return [0, 0, w, h]
        if t == "group":
            w, h = self.group_size(L)
            return [0, 0, w, h]
        return [0, 0, 1, 1]

    def container_size_of(self, L):
        return self.cont_size.get(L["id"], (self.W, self.H))

    def group_size(self, L):
        if L.get("use"):
            return tuple(self.desc["assets"][L["use"]]["size"])
        return tuple(L.get("size") or self.container_size_of(L))

    def text_metrics(self, tx):
        m = self.fonts.get(tx.get("font", "Open Sans"), self.text_style(tx))
        if not m.known:
            self.warnings.append("font %s %s: no font file for metrics; text widths are estimated (0.58 em per character)"
                                 % (tx.get("font", "Open Sans"), self.text_style(tx)))
        return m

    def text_lead(self, tx):
        px = float(tx.get("size", 48))
        return float(tx["leading"]) if tx.get("leading") else 0.8 * self.text_k(tx)[0] * px

    def text_box(self, L, layout=False):
        """Layer px around the text origin (first baseline at the align edge). layout: [edge, cap top, edge, last baseline]
        (what align/stack use); else the raster box with ascender, descender and overhang margins."""
        tx = L["text"]
        px = float(tx.get("size", 48))
        lines = tx["content"].split("\n")
        m = self.text_metrics(tx)
        w = max(m.width(s, px, tx.get("tracking", 0)) for s in lines)
        a = {"left": 0.0, "center": 0.5, "right": 1.0}[tx.get("align", "left")]
        lead = self.text_lead(tx)
        if layout:
            return [-w * a, -m.cap * px, w * (1 - a), lead * (len(lines) - 1)]
        slack = (0.08 if m.known else 0.25) * w + 0.1 * px
        b = [-w * a - slack, -m.asc * px - 0.05 * px, w * (1 - a) + slack, m.desc * px + lead * (len(lines) - 1) + 0.05 * px]
        for an in L.get("animators") or []:  # per-character offsets travel inside the Text+ canvas
            fr = an.get("from") or {}
            dx, dy = float(fr.get("x", 0)), float(fr.get("y", 0))
            b = [b[0] + min(0, dx), b[1] + min(0, dy), b[2] + max(0, dx), b[3] + max(0, dy)]
            if float(fr.get("scale", 100)) > 100:
                g = (float(fr["scale"]) / 100 - 1) * px
                b = [b[0] - g, b[1] - g, b[2] + g, b[3] + g]
        return b

    def text_k(self, tx):
        """Text+ Size = K * px / W. Measured (text.size_for_px, rebuild K1/K20) > estimated from the font file: K = 1.243 x
        (ascent + descent) / em (Open Sans Bold 1.248, Helvetica Neue Bold 1.240, Light 1.239: within 0.6 %) > 1.70."""
        fam, sty = tx.get("font", "Open Sans"), self.text_style(tx)
        if tx.get("sizeK"):
            return float(tx["sizeK"]), True
        key = "%s/%s" % (fam, sty)
        if key in self.font_k:
            return float(self.font_k[key]), True
        m = self.fonts.get(fam, sty)
        if m.known:
            k = round(1.243 * (m.asc + m.desc), 4)
            self.decisions.append("%s: Text+ size constant %.4g estimated from font metrics (text.size_for_px measures it)" % (key, k))
            return k, True
        return 1.70, False

    @staticmethod
    def text_style(tx):
        if tx.get("style"):
            return tx["style"]
        return WEIGHT_STYLE.get(int(tx.get("weight", 700)), "Bold")

    TEX_FIELDS = ("type", "size", "radius", "fill", "stroke", "points", "closed", "trim", "repeat", "color", "src", "use", "layers",
                  "text", "animators", "masks", "effects", "background")

    def tex_sig(self, L):
        """Identical visuals (13 bokeh specks, 3 rows of one filmstrip) share one texture."""
        d = {k: L.get(k) for k in self.TEX_FIELDS if k in L}
        d["keys"] = {k: v for k, v in (L.get("keys") or {}).items() if k in ("size", "trimStart", "trimEnd", "fill", "color", "text")}
        if L.get("anchor") is not None:
            d["anchor"] = L["anchor"]
        return json.dumps(d, sort_keys=True)

    def shared_scales(self, layers, cam, space):
        """Texture scale per layer; layers with identical visuals get the largest of their scales (one shared texture)."""
        ks = {L["id"]: self.tex_scale(L, cam, space) for L in layers}
        if not self.eff["dedupeTextures"]:
            return ks
        best = {}
        for L in layers:
            sig = self.tex_sig(L)
            best[sig] = max(best.get(sig, 0), ks[L["id"]])
        return {L["id"]: best[self.tex_sig(L)] for L in layers}

    def source(self, L, k, pivot, mode3d=False):
        """Build the layer image with its anchor (pivot) or content center at the canvas center."""
        key = (self.tex_sig(L), round(k, 5), bool(pivot), bool(mode3d)) if self.eff["dedupeTextures"] else None
        if key and key in self.tex_cache:
            s0 = self.tex_cache[key]
            self.lset(L, s0.name)
            self.decisions.append("%s: shares the texture of %s" % (L["id"], s0.owner))
            out = Source(s0.name, s0.W, s0.H, s0.k, s0.c, s0.animated, s0.smooth, s0.content_motion)
            out.pending_masks, out.owner = s0.pending_masks, s0.owner
            return out
        src = self._source(L, k, pivot, mode3d)
        src.owner = L["id"]
        if key:  # cache a copy: callers retarget src.name to their holds/freezes
            s0 = Source(src.name, src.W, src.H, src.k, src.c, src.animated, src.smooth, src.content_motion)
            s0.pending_masks, s0.owner = src.pending_masks, src.owner
            self.tex_cache[key] = s0
        return src

    def group_extent(self, L, rect):
        """Tight canvas for a transparent 2D group: the union of its children's raster boxes over time, clipped to the group rect
        (a full-frame transparent canvas is a full-DoD generator: the efficiency lab's oversized-pad trap)."""
        body = self.desc["assets"][L["use"]] if L.get("use") else L
        if body.get("background") is not None or L.get("radius"):
            return rect
        kids = [C for C in body.get("layers") or [] if C["type"] not in ("null", "camera", "light")]
        if not kids or any(self.is3d(C) for C in kids) or any(C["type"] == "camera" for C in body.get("layers") or []):
            return rect
        xs, ys = [], []
        for C in kids:
            b = self.box(C)
            pd = self.effect_pad(C)
            corners = [(b[0] - pd, b[1] - pd), (b[2] + pd, b[1] - pd), (b[0] - pd, b[3] + pd), (b[2] + pd, b[3] + pd)]
            par = self.parent_chain(C)
            moving = bool(C.get("keys")) or any(P.get("keys") for P in par)
            a0, b0 = self.span(C)
            frames = sorted(set(list(range(a0, max(a0 + 1, b0), 2)) + [max(a0, b0 - 1)])) if moving else [0]
            for f in frames:
                for p in corners:
                    x, y = self.world2d(C, f, p, par)
                    xs.append(x)
                    ys.append(y)
        x0, y0, x1, y1 = max(rect[0], min(xs)), max(rect[1], min(ys)), min(rect[2], max(xs)), min(rect[3], max(ys))
        if x1 - x0 < 1 or y1 - y0 < 1:
            return [rect[0], rect[1], rect[0] + 2, rect[1] + 2]
        if (x1 - x0) * (y1 - y0) < 0.9 * (rect[2] - rect[0]) * (rect[3] - rect[1]):
            self.decisions.append("%s: group canvas cropped to its content %dx%d of %dx%d" % (
                L["id"], x1 - x0, y1 - y0, rect[2] - rect[0], rect[3] - rect[1]))
        return [x0, y0, x1, y1]

    def _source(self, L, k, pivot, mode3d=False):
        box = self.content_box(L)
        A = self.anchor(L, box)
        pad = self.effect_pad(L)
        if L["type"] == "group":
            box = self.group_extent(L, box)
        c = A if pivot else ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
        t = L["type"]
        name = self.n(L["id"], "Src")
        smooth = self.container_smooth([L], None)
        if t == "image":
            k = 1.0
        if t == "text" and not mode3d:
            # 2D text: canvas centered on the text origin, half extents in 128 px steps, so editing the words changes only
            # StyledText (a Text+ canvas is cheap: its DoD is the glyphs)
            c = A
            x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
            hx = math.ceil(max(c[0] - x0, x1 - c[0], 1) * k / 128.0) * 128
            hy = math.ceil(max(c[1] - y0, y1 - c[1], 1) * k / 128.0) * 128
            W, H = int(2 * hx), int(2 * hy)
        else:
            W, H = self.canvas(box, c, k, pad)
        sp = Space(W, H, c[0], c[1], k, W / k, H / k)
        animated = False
        motion = []
        pos = (self.cur_col, self.cur_y - 1)
        if t == "text":
            name, animated, motion = self.text_source(L, sp, name, pos)
        elif t in ("rect", "ellipse", "path"):
            if isinstance(L.get("fill"), dict):
                name, animated = self.plate(L, sp, name, pos)
            else:
                items = self.sshapes(L, sp, lambda x, y: (x, y), (pos[0], pos[1] - 2))
                self.srender(name, items, W, H, pos)
                self.lset(L, name)
                animated = bool(set(L.get("keys") or {}) & {"size", "trimEnd", "trimStart", "fill"})
                motion = self.size_motion(L) if "size" in (L.get("keys") or {}) else []
                if motion and self.eff["sizeBlur"] and L["type"] in ("rect", "ellipse"):
                    name, motion = self.size_blur(L, name, motion, sp, pos), []
        elif t == "solid":
            w, h = L.get("size") or self.container_size_of(L)
            if abs(c[0] - w / 2) < 1e-6 and abs(c[1] - h / 2) < 1e-6 and not pad:
                ins = {"UseFrameFormatSettings": 0, "Width": _even(w * k), "Height": _even(h * k), "Depth": self.depth_for(False)}
                ins.update(self.bg_color(L.get("color", "#FFFFFF")))
                self.lset(L, self.g.add(name, "Background", ins, pos=pos))
                W, H = ins["Width"], ins["Height"]
            else:
                name, animated = self.plate(dict(L, type="rect", size=[w, h], fill=L.get("color", "#FFFFFF")), sp, name, pos)
        elif t == "image":
            ins = {"Clip": _clip(L["src"]), "Loop": 1, "HoldLastFrame": 100000, "GlobalIn": 0, "GlobalOut": self.dur - 1}
            self.lset(L, self.g.add(name, "Loader", ins, pos=pos))
            self.warnings.append("%s: still Loader hold (Loop/HoldLastFrame) is unverified live" % L["id"])
            w, h = L.get("size") or self.image_size(L["src"])
            if abs(c[0] - w / 2) > 1e-6 or abs(c[1] - h / 2) > 1e-6 or pad:
                base = self.g.add(name + "_Pad", "Background", {"UseFrameFormatSettings": 0, "Width": W, "Height": H, "Depth": self.depth_for(smooth),
                                                                 "TopLeftAlpha": 0}, pos=(pos[0], pos[1] - 1))
                u, v = sp.uv(w / 2, h / 2)
                name = self.lset(L, self.g.add(name + "_Place", "Merge", {"Background": Src(base), "Foreground": Src(name), "Center": (u, v),
                                                                          "PerformDepthMerge": 0}, pos=pos))
            else:
                W, H = int(w), int(h)
        elif t == "group":
            name, animated = self.group_source(L, sp, k, pos)
        src = Source(name, W, H, k, c, animated, smooth, motion)
        src = self.masks(L, src, sp, mode3d)
        src = self.effects(L, src, sp)
        return src

    def plate(self, L, sp, name, pos):
        """Background (color or gradient) cut by a Rectangle/Ellipse mask: gradient fills and offset solids."""
        (box, (gcx, gcy)) = self.shape_geom(L)
        w, h = L.get("size", [100, 100])
        mname = self.lset(L, name + "_Shape")
        u, v = sp.uv(gcx, gcy)
        mi = {"Center": (u, v), "Width": w * sp.k / sp.W, "Height": h * sp.k / (sp.H if L["type"] == "rect" else sp.W)}
        if L["type"] == "rect" and L.get("radius"):
            mi["CornerRadius"] = min(1.0, float(L["radius"]) / (min(w, h) / 2.0))
        st = L.get("stroke")
        if st and L.get("fill") is None:
            mi.update(Solid=0, BorderWidth=st["width"] * sp.k / sp.W)
        self.g.add(mname, "RectangleMask" if L["type"] == "rect" else "EllipseMask", mi, pos=(pos[0], pos[1] - 1))
        ins = {"UseFrameFormatSettings": 0, "Width": sp.W, "Height": sp.H, "EffectMask": Src(mname, "Mask")}
        fill = L.get("fill") if L.get("fill") is not None else (st or {}).get("color", "#FFFFFF")
        if isinstance(fill, dict):
            ins.update(self.gradient_inputs(fill["gradient"], sp))
            ins["Depth"] = self.depth_for(True)
        else:
            ins.update(self.bg_color(fill))
            ins["Depth"] = self.depth_for(False)
        self.lset(L, self.g.add(name, "Background", ins, pos=pos))
        if st and L.get("fill") is not None:
            self.warnings.append("%s: gradient fill with a stroke: the stroke is not drawn (use a separate stroke layer)" % L["id"])
        return name, False

    def text_source(self, L, sp, name, pos):
        tx = L["text"]
        K, measured = self.text_k(tx)
        fam, sty = tx.get("font", "Open Sans"), self.text_style(tx)
        if not measured:
            self.warnings.append("%s: no measured Text+ size constant for %s %s; using 1.70 (Open Sans). Run text.size_for_px once or pass text.sizeK"
                                 % (L["id"], fam, sty))
        px = float(tx.get("size", 48))
        size = K * px * sp.k / sp.W
        a = {"left": -1, "center": 0, "right": 1}[tx.get("align", "left")]
        u, v = sp.uv(0, 0)
        ins = {"UseFrameFormatSettings": 0, "Width": sp.W, "Height": sp.H, "Depth": self.depth_for(False),
               "StyledText": tx["content"], "Font": fam, "Style": sty, "Size": size, "Center": (u, v),
               "CenterOnBaseOfFirstLine": 1, "HorizontalJustificationNew": 3, "HorizontalLeftCenterRight": a}
        n_lines = tx["content"].count("\n") + 1
        if n_lines > 1:
            # [live, scene builder pass] CenterOnBaseOfFirstLine 1 stacks extra lines UPWARD (reversed order). With it off and
            # VerticalTopCenterBottom 1 the lines run downward and the LAST baseline sits on Center; line pitch at LineSpacing 1
            # = 0.80 x Size x W (measured on Helvetica Neue Bold: 51.2 px at Size 0.08 on 800 px)
            lead = self.text_lead(tx)
            ins["CenterOnBaseOfFirstLine"] = 0
            ins["VerticalTopCenterBottom"] = 1
            ins["Center"] = sp.uv(0, lead * (n_lines - 1))
            ins["HorizontalJustification" + {-1: "Left", 0: "Center", 1: "Right"}[a]] = 1
            if tx.get("leading"):
                ins["LineSpacing"] = float(tx["leading"]) / (0.8 * K * px)
        if tx.get("tracking"):
            ins["CharacterSpacing"] = 1 + float(tx["tracking"]) / (1000.0 * K)
        ins.update(self.color(tx.get("color", "#FFFFFF"), ("Red1", "Green1", "Blue1", "Alpha1")))
        animated, motion = False, []
        tk = (L.get("keys") or {}).get("text")
        if tk:
            tbl = ", ".join("{%s, %s}" % (_num(k[0]), _q(k[1])) for k in tk)
            ins["StyledText"] = Expr(":local t = {%s}; local s = t[1][2]; for i = 1, #t do if time >= t[i][1] then s = t[i][2] end end; return Text(s)" % tbl,
                                     tk[0][1])
            animated = True
        self.lset(L, self.g.add(name, "TextPlus", ins, pos=pos))
        for j, an in enumerate(L.get("animators") or []):
            if j:
                self.warnings.append("%s: only the first animator is applied (one Follower per Text+)" % L["id"])
                break
            motion = self.follower(L, an, name, sp, K, px)
            animated = True
        return name, animated, motion

    def follower(self, L, an, host, sp, K, px):
        """Per-character animation with a StyledTextFollower (the Text+ text moves onto the Follower)."""
        fol = self.lset(L, host + "_Fol")
        content = L["text"]["content"]
        n = max(1, len(content.replace("\n", "")))
        order = {"left_to_right": 0, "right_to_left": 1, "inside_out": 2, "outside_in": 3, "random": 5}[an.get("order", "left_to_right")]
        ins = {"Text": Styled(content), "Order": order, "DelayType": 1}
        s = float(an["start"])
        motion = []
        if an["type"] == "typewriter":
            e = float(an.get("end", s + n * 2))
            slot = (e - s) / n
            ins["Delay"] = slot
            if an.get("mode", "step") == "fade":
                ins["Opacity1"] = self.spline(fol, "Opacity1", [s, s + slot], [0.0, 1.0], [("linear",)])
            else:
                ins["Opacity1"] = self.spline(fol, "Opacity1", [s - 1, s], [0.0, 1.0], [("hold",)])
            self.decisions.append("%s: typewriter = Follower opacity per character (%s, %.3g f per character)" % (L["id"], an.get("mode", "step"), slot))
        else:
            st = float(an.get("stagger", 2))
            du = float(an.get("duration", 12))
            ins["Delay"] = st
            fr = an.get("from") or {"y": 40, "opacity": 0}
            c = self.eases.curve(an.get("ease"), du, 1)
            if "opacity" in fr:
                ins["Opacity1"] = self.spline(fol, "Opacity1", [s, s + du], [float(fr["opacity"]) / 100, 1.0], [c])
            if "x" in fr or "y" in fr:
                dx, dy = float(fr.get("x", 0)), float(fr.get("y", 0))
                xs = ([s, s + du], [dx * sp.k / sp.W, 0.0], [c]) if dx else 0.0
                ys = ([s, s + du], [-dy * sp.k / sp.W, 0.0], [c]) if dy else 0.0
                ins["CharacterOffset"] = self.xypath(fol, "CharacterOffset", xs, ys)
                motion = [(int(s), int(math.ceil(s + du + st * (n - 1))))]
            if "scale" in fr:
                sc = float(fr["scale"]) / 100
                for ax in ("CharacterSizeX", "CharacterSizeY"):
                    ins[ax] = self.spline(fol, ax, [s, s + du], [sc, 1.0], [c])
            if "rotation" in fr:
                ins["CharacterAngleZ"] = self.spline(fol, "CharacterAngleZ", [s, s + du], [-float(fr["rotation"]), 0.0], [c])
            self.decisions.append("%s: cascade = Follower, %g f per character, %g f stagger" % (L["id"], du, st))
        self.g.add(fol, "StyledTextFollower", ins, owner=(host, "StyledText"))
        self.g.setin(host, "StyledText", Src(fol, "StyledText"))
        return motion

    def group_source(self, L, sp, k, pos):
        asset = L.get("use")
        key = (asset, round(k, 4), round(sp.cx, 3), round(sp.cy, 3), sp.W, sp.H) if asset else None
        if key and key in self.asset_cache:
            self.decisions.append("%s: reuses asset %s texture (built once)" % (L["id"], asset))
            name, animated = self.asset_cache[key]
            self.lset(L, name)
            return name, animated
        body = self.desc["assets"][asset] if asset else L
        w, h = self.group_size(L)
        prefix = ("A_" + asset) if asset else L["id"]
        ns = self.ns
        if asset:  # a second raster of the same asset (another scale): its own deterministic names [fusion_v2 F2]
            nv = self.asset_variants[asset] = self.asset_variants.get(asset, 0) + 1
            if nv > 1:
                self.ns = "%s_v%d" % (asset, nv)
                self.decisions.append("%s: asset %s rasterized again at k %.3g (variant %d, tools %s_*)" % (L["id"], asset, k, nv, self.n()))
        space = Space(sp.W, sp.H, sp.cx, sp.cy, k, w, h)
        for C in body.get("layers") or []:
            self.cont_size[C["id"]] = (w, h)
        base = self.n(prefix, "Base")
        save_col, save_y = self.cur_col, self.cur_y
        self.row -= 8
        y = self.row
        smooth = self.container_smooth(body.get("layers") or [], body.get("background"))
        bg = body.get("background")
        self.background(base, bg, space, self.depth_for(smooth), pos=(pos[0], y), radius=L.get("radius") or 0.0)
        if bg is None:
            self.decisions.append("%s: group canvas %dx%d on a transparent base" % (prefix, space.W, space.H))
        out = self.stack(body.get("layers") or [], space, base, x0=pos[0] + 1, y0=y, path=prefix)
        self.ns = ns
        self.cur_col, self.cur_y = save_col, save_y
        animated = any(C.get("keys") or C.get("animators") or C.get("layers") for C in (body.get("layers") or []))
        if key:
            self.asset_cache[key] = (out, animated)
        self.lset(L, out)
        return out, animated

    # ------------------------------------------------------------ masks and effects (layer space, before the transform)
    def static2d(self, L):
        return not (set(L.get("keys") or {}) & {"position", "scale", "rotation"}) and not L.get("parent") and not self.is3d(L) \
            and not isinstance(L.get("rotation"), (str, dict))

    def mask_tools(self, L, ms, sp, to_c=None, s=1.0, ang=0.0):
        """Mask chain for masks in layer px. sp maps the target canvas; to_c maps layer px into sp's px (None = identity)."""
        to_c = to_c or (lambda x, y: (x, y))
        prev = None
        for j, m in enumerate(ms):
            nm = self.lset(L, self.n(L["id"], "Mask%d" % (j + 1)))
            ins = {}
            if m["shape"] in ("rect", "ellipse"):
                x, y, w, h = _mask_box(m)
                u, v = sp.uv(*to_c(x + w / 2, y + h / 2))
                w, h = w * s, h * s
                ins.update(Center=(u, v), Width=w * sp.k / sp.W, Height=h * sp.k / (sp.H if m["shape"] == "rect" else sp.W))
                if m["shape"] == "rect" and m.get("radius"):
                    ins["CornerRadius"] = min(1.0, float(m["radius"]) * s / (min(w, h) / 2.0))
                if ang:
                    ins["Angle"] = ang
                reg = "RectangleMask" if m["shape"] == "rect" else "EllipseMask"
            else:
                pts = []
                for p in m.get("points") or []:
                    u, v = sp.uv(*to_c(p[0], p[1]))
                    pts.append((u - 0.5, v - 0.5))
                ins["Polyline"] = Poly((True, tuple(pts)))
                reg = "PolylineMask"
            if m.get("feather"):
                ins["SoftEdge"] = 1.18 * float(m["feather"]) * s * sp.k / sp.W
            if m.get("invert"):
                ins["Invert"] = 1
            if prev:
                ins["EffectMask"] = Src(prev, "Mask")
                ins["PaintMode"] = FuID({"add": "Merge", "subtract": "Subtract", "intersect": "Minimum"}[m.get("mode", "add")])
            self.g.add(nm, reg, ins, pos=(self.cur_col + 0.5, self.cur_y - 3 - j))
            prev = nm
        return prev

    def masks(self, L, src, sp, mode3d=False):
        ms = L.get("masks") or []
        if not ms:
            return src
        if L["type"] == "text":
            self.text_mask_check(L, ms)
        target = src.name
        tgt = self.g.t[target]
        takes = tgt["reg"] in ("TextPlus", "sRender", "Background", "Loader") and "EffectMask" not in tgt["inputs"]
        if (not takes or L.get("_containerMasks")) and not mode3d and (self.static2d(L) or L.get("_containerMasks")):
            src.pending_masks = ms  # drawn in container space as the consuming Merge's EffectMask (no extra canvas)
            return src
        prev = self.mask_tools(L, ms, sp)
        if takes:
            self.g.setin(target, "EffectMask", Src(prev, "Mask"))
            return src
        # the source already has an EffectMask (plates): cut the layer image with a masked Merge onto a clear canvas
        clear = self.g.add(self.n(L["id"], "MaskBase"), "Background", {"UseFrameFormatSettings": 0, "Width": src.W, "Height": src.H,
                                                                       "Depth": self.depth_for(src.smooth), "TopLeftAlpha": 0},
                           pos=(self.cur_col + 0.5, self.cur_y - 2))
        nm = self.lset(L, self.g.add(self.n(L["id"], "Masked"), "Merge", {"Background": Src(clear), "Foreground": Src(src.name),
                                                                          "EffectMask": Src(prev, "Mask"), "PerformDepthMerge": 0},
                                     pos=(self.cur_col + 0.5, self.cur_y - 1)))
        self.lset(L, clear)
        src.name = nm
        return src

    def text_mask_check(self, L, ms):
        """Warn when add-mode rect masks leave the text's rest glyphs (cap top to baseline) partly outside: the usual cause is an
        AE LineBox given as corners in box [fusion_v2 F6]."""
        if any(m["shape"] != "rect" or m.get("invert") or m.get("mode", "add") != "add" for m in ms):
            return
        x0, y0, x1, y1 = self.text_box(L, layout=True)
        area = max(1e-6, (x1 - x0) * (y1 - y0))
        cov = 0.0
        for m in ms:
            bx, by, bw, bh = _mask_box(m)
            cov = max(cov, max(0.0, min(x1, bx + bw) - max(x0, bx)) * max(0.0, min(y1, by + bh) - max(y0, by)) / area)
        if cov < 0.9:
            self.warnings.append("%s: its rect mask shows %d %% of the text at rest (cap top to baseline = layer px [%d, %d, %d, %d]); box is "
                                 "[x, y, width, height] from the text origin (first baseline); AE LineBox corners go in corners: "
                                 "[x0, y0, x1, y1]" % (L["id"], round(100 * cov), x0, y0, x1, y1))

    def size_motion(self, L):
        """Runs of frames whose size change across the shutter reaches the motion-blur threshold: content motion, so the Merge
        re-renders the shape per motion-blur sample (no texture hold) and a size animation blurs like AE's."""
        mbc = self.cfg["motionBlur"]
        if not mbc["on"] or L.get("motionBlur") is False:
            return []
        tr, d = self.track(L, "size"), mbc["shutter"] / 720.0
        thr = max(self.eff["mbThresholdPx"] if self.eff["adaptiveMotionBlur"] else 0.0, 1e-6)
        ms = self.max_scale(L)
        on = [max(abs(a - b) for a, b in zip(tr.at(f + d), tr.at(f - d))) * ms >= thr for f in range(self.dur)]
        runs, s0 = [], None
        for f, x in enumerate(on + [False]):
            if x and s0 is None:
                s0 = f
            elif not x and s0 is not None:
                runs.append((s0, f - 1))
                s0 = None
        return runs

    def size_blur(self, L, img, runs, sp, pos):
        """[sb3] Motion blur for a size animation. Fusion blurs a tool's own transform, not an upstream shape's Width/Height (the
        benchmark S1 iris and S7 ring rendered crisp where AE smears), so: the shape is held at integer frames, then a Transform scales
        it by size(t) / size(frame) about the shape center with its own motion blur on the frames that change. That ratio is exactly
        1 at every integer frame, so still frames, draft renders and frames at rest are the pixels the shape draws itself; only the
        shutter samples see the scale. A stroke width scales with the samples (under one frame of growth)."""
        tr = self.track(L, "size")
        e = min(self.cfg["motionBlur"]["shutter"] / 720.0, 0.45)
        hold = self.lset(L, self.g.add(img + "_SizeHold", "TimeStretcher", {"Input": Src(img), "SourceTime": Expr("floor(time + 0.5)", 0),
                                                                            "InterpolateBetweenFrames": 0}, pos=(pos[0], pos[1] + 0.5)))
        on = sorted({f for a, b in runs for f in range(a, b + 1)})
        pts = {}
        for f in on:
            base = tr.at(f)
            for off in (-e, -e / 2, 0.0, e / 2, e):
                v = tr.at(f + off)
                pts[f + off] = [v[i] / base[i] if abs(base[i]) > 0.5 else 1.0 for i in (0, 1)]
            for g in (f - 1, f + 1):
                pts.setdefault(float(g), [1.0, 1.0])
        fr = sorted(pts)
        name = self.lset(L, self.n(L["id"], "SizeMB"))
        box, (gcx, gcy) = self.shape_geom(L)
        ctr = sp.uv(gcx, gcy)
        lin = [("linear",)] * (len(fr) - 1)
        ins = {"Input": Src(hold), "UseSizeAndAspect": 0, "Center": ctr, "Pivot": ctr,
               "XSize": self.spline(name, "XSize", fr, [pts[t][0] for t in fr], lin),
               "YSize": self.spline(name, "YSize", fr, [pts[t][1] for t in fr], lin)}
        ins.update(self.mb_inputs([f in set(on) for f in range(self.dur)], self.mb2d_samples()))
        self.g.add(name, "Transform", ins, pos=(pos[0], pos[1] + 1))
        self.stats["mbMerges"] += 1
        self.decisions.append("%s: size animation motion-blurred through a Transform scale on %d frames (rest pixels unchanged)"
                              % (L["id"], len(on)))
        return name

    def effects(self, L, src, sp):
        for j, e in enumerate(L.get("effects") or []):
            t = e["type"]
            nm = self.lset(L, self.n(L["id"], t.capitalize() + ("" if j == 0 else str(j + 1))))
            w = src.W / 1920.0 * 1.25
            if t == "blur":
                ins = {"Input": Src(src.name), "XBlurSize": e.get("radius", 4) * src.k / w}
                reg = "Blur"
            elif t == "glow":
                ins = {"Input": Src(src.name), "XGlowSize": e.get("radius", 10) * src.k / w, "Gain": e.get("strength", 1.0),
                       "Threshold": e.get("threshold", 0.0)}
                reg = "SoftGlow"
            elif t == "shadow":
                off = e.get("offset", [0, 8])
                ins = {"Input": Src(src.name), "ShadowOffset": (0.5 + off[0] * src.k / src.W, 0.5 - off[1] * src.k / src.H),
                       "Softness": 1.18 * e.get("blur", 16) * src.k / src.W}
                ins.update(self.color(e.get("color", "#000000"), ("Red", "Green", "Blue", "Alpha")))
                ins["Alpha"] = float(e.get("opacity", 35)) / 100
                reg = "Shadow"
            elif t == "tint":
                c = self.color(e.get("color", "#FFFFFF"), ("MasterRedGain", "MasterGreenGain", "MasterBlueGain", "_a"))
                c.pop("_a")
                ins = dict({"Input": Src(src.name)}, **c)
                if e.get("amount", 100) != 100:
                    ins["Blend"] = float(e["amount"]) / 100
                reg = "ColorCorrector"
            else:
                ins = {"Input": Src(src.name), "LogProcessing": 0, "MasterStrength": e.get("strength", 0.012), "MasterXSize": e.get("size", 1.0),
                       "Monochrome": 1 if e.get("mono", True) else 0}
                reg = "FilmGrain"
            self.g.add(nm, reg, ins, pos=(self.cur_col, self.cur_y - 1 + 0.5 * (j + 1)))
            src.name = nm
        return src

    # ------------------------------------------------------------ 2D layer: source -> (hold) -> Merge (Center/Size/Angle/Blend/MB)
    def layer2d(self, L, space, cur, col, y0):
        self.cur_col, self.cur_y = col, y0
        pivot = self.has_pivot(L)
        parent = self.parent_chain(L)
        if parent:
            pivot = True
        ms = self.max_scale(L) * (max(self.max_scale(P) for P in parent) if parent else 1.0)
        static = not (set(L.get("keys") or {}) & {"scale"}) and not any("scale" in (P.get("keys") or {}) for P in parent)
        k = space.k * min(4.0, max(1.0 / 16, ms if static else _q8(ms))) if L["type"] != "image" else 1.0
        src = self.source(L, k, pivot)
        img = src.name
        mname = self.n(L["id"])
        mb_frames = self.mb_frames_2d(L, src, space, parent)
        if src.content_motion:
            for a, b in src.content_motion:
                for f in range(max(0, a), min(self.dur, b + 1)):
                    mb_frames[f] = True
        mb_any = self.cfg["motionBlur"]["on"] and self.eff["mb2d"] and L.get("motionBlur", True) and any(mb_frames)
        if mb_any and src.animated and self.eff["hold"] and not src.content_motion:
            img = self.lset(L, self.g.add(self.n(L["id"], "Hold"), "TimeStretcher", {"Input": Src(img), "SourceTime": Expr("floor(time + 0.5)", 0),
                                                                                    "InterpolateBetweenFrames": 0}, pos=(col - 0.5, y0 - 1)))
            self.stats["holds"] += 1
        elif self.eff["freeze"] and self.src_static(L) and not self.is_static(L):
            img = self.lset(L, self.freeze(img, "static source under an animated layer"))
        src.name = img
        ins = {"Background": Src(cur), "Foreground": Src(img), "PerformDepthMerge": 0}
        ins.update(self.place2d(L, src, space, mname, parent))
        blend = L.get("blend", "normal")
        if blend != "normal":
            ins["ApplyMode"] = FuID(BLEND[blend])
        ins.update(self.opacity_in(L, mname, "Blend", 1.0 / 100))
        if getattr(src, "pending_masks", None):
            s = self.scale_at(L, 0)[0] / 100
            rest = dict(L, keys={k: v for k, v in (L.get("keys") or {}).items() if k not in ("position",)})
            ins["EffectMask"] = Src(self.mask_tools(L, src.pending_masks, space, lambda x, y: self.world2d(rest, 0, (x, y), []), s,
                                                    -self.sval(L.get("rotation", 0))), "Mask")
            if L.get("matte"):
                self.warnings.append("%s: a layer with masks on a group source cannot also take a track matte; the matte is ignored" % L["id"])
        elif L.get("matte"):
            ins["EffectMask"] = Src(self.matte(L, space, col, y0), "Mask")
        if mb_any:
            ins.update(self.mb_inputs(mb_frames, self.mb2d_samples()))
            self.stats["mbMerges"] += 1
        if L.get("glass"):
            ins["Background"] = Src(self.glass(L, cur, ins, space, mname, col, y0))
        self.lset(L, self.g.add(mname, "Merge", ins, pos=(col, y0)))
        self.cull(L, mname)
        return mname

    def glass(self, L, cur, card, space, mname, col, y0):
        """[sb3] Backdrop blur: Blur(what is below) -> [saturation] -> [tint] merged over it under a BitmapMask of the layer's own
        alpha, drawn by a Merge whose Center/Size/Angle/Blend follow the layer's Merge by expression (so it follows any transform,
        animation, parent bake or opacity) and which shares its Foreground, EffectMask and motion blur. The frost is processed full
        frame and cut once by the mask (blurring after masking pulls black into the edge: liquid-glass rig). Culled to the layer's
        visible frames; frozen when everything below is a frozen static prefix."""
        gl = L["glass"]
        n = lambda s: self.lset(L, self.n(L["id"], s))  # noqa: E731
        W, H = _even(space.W), _even(space.H)
        base = self.g.add(n("GlassBase"), "Background", {"UseFrameFormatSettings": 0, "Width": W, "Height": H, "Depth": DEPTH["int8"],
                                                         "TopLeftAlpha": 0}, pos=(col - 0.5, y0 + 2))
        link = {k: Expr("%s.%s" % (mname, k), card[k] if not isinstance(card[k], (Src, Expr)) else None) for k in ("Center", "Size", "Angle")
                if k in card}
        for k in ("Center", "Size", "Angle"):
            link.setdefault(k, Expr("%s.%s" % (mname, k)))
        shape = dict(link, Background=Src(base), Foreground=card["Foreground"], PerformDepthMerge=0)
        for k in ("EffectMask", "MotionBlur", "Quality", "ShutterAngle", "CenterBias"):
            if k in card:
                shape[k] = card[k]
        self.g.add(n("GlassShape"), "Merge", shape, pos=(col - 0.5, y0 + 3))
        self.g.add(n("GlassMask"), "BitmapMask", dict(self.COVERAGE, Image=Src(self.n(L["id"], "GlassShape")), UseFrameFormatSettings=0,
                                                      Width=W, Height=H), pos=(col - 0.5, y0 + 1))
        return self.frost(L, cur, space, col, y0)

    # the glass mask is the layer's COVERAGE: alpha from 5 % up counts as inside (a glass body is translucent: #FFFFFF21 would
    # frost at 13 %); the layer's opacity and in/out fade the Glass Merge instead
    COVERAGE = {"Channel": FuID("Alpha"), "Low": 0.0, "High": 0.05}

    def frost(self, L, cur, space, col, y0):
        """Blur(cur) -> [saturation] -> [tint] merged over cur under <id>_GlassMask; culled with the layer. -> the Glass Merge."""
        gl = L["glass"]
        n = lambda s: self.lset(L, self.n(L["id"], s))  # noqa: E731
        W, H = _even(space.W), _even(space.H)
        frost = self.g.add(n("Frost"), "Blur", {"Input": Src(cur), "XBlurSize": float(gl.get("blur", 20)) * space.k / (space.W / 1920.0 * 1.25)},
                           pos=(col - 1, y0 - 1))
        if float(gl.get("saturation", 100)) != 100:
            frost = self.g.add(n("FrostSat"), "BrightnessContrast", {"Input": Src(frost), "Saturation": float(gl["saturation"]) / 100},
                               pos=(col - 1, y0 - 1.5))
        if gl.get("tint"):
            c = self.color(gl["tint"], ("TopLeftRed", "TopLeftGreen", "TopLeftBlue", "TopLeftAlpha"))
            a = c.pop("TopLeftAlpha")
            tint = self.g.add(n("TintColor"), "Background", dict(c, UseFrameFormatSettings=0, Width=W, Height=H, Depth=DEPTH["int8"]),
                              pos=(col - 1.5, y0 - 2))
            frost = self.g.add(n("FrostTint"), "Merge", {"Background": Src(frost), "Foreground": Src(tint), "Blend": a, "PerformDepthMerge": 0},
                               pos=(col - 1, y0 - 2))
        r = self.g.t.get(cur, {})
        if self.eff["freeze"] and r.get("reg") == "TimeStretcher" and not isinstance(r["inputs"].get("SourceTime"), (Expr, Src)):
            frost = self.freeze(frost, "frost of a static backdrop")
        gname = n("Glass")
        gi = {"Background": Src(cur), "Foreground": Src(frost), "EffectMask": Src(self.n(L["id"], "GlassMask"), "Mask"), "PerformDepthMerge": 0}
        gi.update(self.opacity_in(L, gname, "Blend", float(gl.get("opacity", 100)) / 10000.0, stepped=self.is3d(L)))
        self.g.add(gname, "Merge", gi, pos=(col - 0.5, y0))
        self.cull(L, gname)
        self.decisions.append("%s: backdrop blur %g px under its own shape (Glass Merge, culled with the layer)" % (L["id"], gl.get("blur", 20)))
        return gname

    def parent_chain(self, L):
        out, p = [], L.get("parent")
        while p:
            P = self.byid[p]
            out.append(P)
            p = P.get("parent")
        return out

    def world2d(self, L, t, p, parents):
        """Container px of layer-local point p at time t (AE transform, then parents outward)."""
        box = self.box(L) if L["type"] != "null" else [0, 0, 0, 0]
        A = self.anchor(L, box)
        cw, ch = self.container_size_of(L)
        pos = self.prop_at(L, "position", t, [cw / 2, ch / 2])
        s = self.scale_at(L, t)
        r = math.radians(self.sval(self.prop_at(L, "rotation", t, 0)))
        dx, dy = (p[0] - A[0]) * s[0] / 100, (p[1] - A[1]) * s[1] / 100
        x, y = pos[0] + dx * math.cos(r) - dy * math.sin(r), pos[1] + dx * math.sin(r) + dy * math.cos(r)
        if parents:
            return self.world2d(parents[0], t, (x, y), parents[1:])
        return (x, y)

    def place2d(self, L, src, space, mname, parents):
        """Merge Center/Size/Angle (+XSize/YSize via Transform for non-uniform scale). Keys map 1:1 (eases kept) unless a parent
        is animated (then baked per frame)."""
        ins = {}
        box = self.content_box(L)
        A = self.anchor(L, box)
        off = (src.c[0] - A[0], src.c[1] - A[1])
        ks = L.get("keys") or {}
        ratio = space.k / src.k
        anim_parent = any(P.get("keys") for P in parents)
        if parents and anim_parent:
            fr = [f for f in range(self.dur)]
            cs = [space.uv(*self.world2d(L, f, src.c, parents)) for f in fr]
            lin = [("linear",)] * (len(fr) - 1)
            ins["Center"] = self.xypath(mname, "Center", (fr, [c[0] for c in cs], lin), (fr, [c[1] for c in cs], lin))
            sz = []
            ang = []
            for f in fr:
                s = self.scale_at(L, f)[0] / 100
                a = self.sval(self.prop_at(L, "rotation", f, 0))
                for P in parents:
                    s *= self.scale_at(P, f)[0] / 100
                    a += self.sval(self.prop_at(P, "rotation", f, 0))
                sz.append(s * ratio)
                ang.append(-a)
            ins["Size"] = self.spline(mname, "Size", fr, sz, lin) if len(set(sz)) > 1 else sz[0]
            if any(ang):
                ins["Angle"] = self.spline(mname, "Angle", fr, ang, lin) if len(set(ang)) > 1 else ang[0]
            self.decisions.append("%s: parent %s is animated: placement baked per frame (%d keys)" % (L["id"], parents[0]["id"], len(fr)))
            return ins
        if parents:  # static parents: fold into a static placement
            c = space.uv(*self.world2d(L, 0, src.c, parents))
            ins["Center"] = c
            s = self.scale_at(L, 0)[0] / 100
            a = self.sval(L.get("rotation", 0))
            for P in parents:
                s *= self.scale_at(P, 0)[0] / 100
                a += self.sval(P.get("rotation", 0))
            if abs(s * ratio - 1) > 1e-9:
                ins["Size"] = s * ratio
            if a:
                ins["Angle"] = -a
            return ins
        # position
        s0 = self.scale_at(L, 0)
        r0 = self.sval(L.get("rotation", 0))
        # the canvas is centered on the anchor whenever the layer rotates/scales, so off != 0 only for pure translation
        if "position" in ks:
            tr = self.track(L, "position")
            fx = lambda v: space.uv(v + off[0], 0)[0]  # noqa: E731 (affine: eases stay exact)
            fy = lambda v: space.uv(0, v + off[1])[1]  # noqa: E731
            ins["Center"] = self.xypath(mname, "Center", tr.component(0, fx), tr.component(1, fy))
        else:
            ins["Center"] = space.uv(*self.world2d(L, 0, src.c, []))
        # scale
        if "scale" in ks:
            tr = self.track(L, "scale")
            if isinstance(tr.v[0], (list, tuple)) and any(abs(v[0] - v[1]) > 1e-9 for v in tr.v):
                ins.update(self.nonuniform(L, src, tr, mname, ratio))
            else:
                comp = 0 if isinstance(tr.v[0], (list, tuple)) else None
                ins["Size"] = self.spline(mname, "Size", *tr.component(comp, lambda v: v / 100 * ratio))
        elif abs(s0[0] - s0[1]) > 1e-9:
            ins.update(self.nonuniform(L, src, None, mname, ratio))
        elif abs(s0[0] / 100 * ratio - 1) > 1e-9:
            ins["Size"] = s0[0] / 100 * ratio
        # rotation
        if "rotation" in ks:
            ins["Angle"] = self.spline(mname, "Angle", *self.track(L, "rotation").component(None, lambda v: -v))
        elif isinstance(L.get("rotation"), (str, dict)):
            ins["Angle"] = self.scalar(L["rotation"], sign=-1)
        elif r0:
            ins["Angle"] = -r0
        return ins

    def nonuniform(self, L, src, tr, mname, ratio):
        """Non-uniform scale: a Transform (XSize/YSize, UseSizeAndAspect 0) before the Merge, shrinking only (raster at the max scale).
        ratio = container k / source k, as for a uniform Merge Size [fusion_v2 F7: without the container's k a 2x asset drew at half size]."""
        name = self.lset(L, self.n(L["id"], "Scale"))
        ins = {"Input": Src(src.name), "UseSizeAndAspect": 0}
        if tr:
            ins["XSize"] = self.spline(name, "XSize", *tr.component(0, lambda v: v / 100 * ratio))
            ins["YSize"] = self.spline(name, "YSize", *tr.component(1, lambda v: v / 100 * ratio))
        else:
            s = self.scale_at(L, 0)
            ins["XSize"], ins["YSize"] = s[0] / 100 * ratio, s[1] / 100 * ratio
        self.g.add(name, "Transform", ins, pos=(self.cur_col - 0.5, self.cur_y - 0.5))
        src.name = name
        return {"Foreground": Src(name)}

    def opacity_in(self, L, host, iid, scale, stepped=False):
        """Opacity and in/out -> a static value, an expression or a spline on host.iid. In/out is ALWAYS cut here, frame
        exact (0 before in - 0.5 and from out - 0.5): the enabled region only culls, and its margin must never show a layer
        outside in/out [fusion_v2 F12: with the region as the only gate, every hard cut landed a frame early]."""
        ks = (L.get("keys") or {}).get("opacity")
        a, b = self.span(L)
        cut = a > 0 or b < self.dur
        v = L.get("opacity", 100)
        if not ks and isinstance(v, (str, dict)):
            e = self.scalar(v, scale=scale)
            if not cut:
                return {iid: e}
            return {iid: Expr("iif(time > %s and time < %s, %s, 0)" % (_num(a - 0.5), _num(b - 0.5), e.e), e.v if a <= 0 else 0.0)}
        if not ks and not cut:
            return {iid: v * scale} if v != 100 else {}
        tr = self.track(L, "opacity") if ks else None
        if stepped or cut:
            # AE never motion-blurs opacity [rebuild K15]: hold one value per frame, 0 outside in/out
            vals, fr, last = [], [], None
            for f in range(self.dur):
                v = 0.0 if not (a <= f < b) else (tr.at(f) if tr else self.sval(L.get("opacity", 100)))
                v = round(v * scale, 6)
                if v != last:
                    fr.append(f - 0.5 if f else 0)
                    vals.append(v)
                    last = v
            if len(vals) == 1:
                return {iid: vals[0]}
            return {iid: self.spline(host, iid.replace(".", ""), fr, vals, [("hold",)] * (len(fr) - 1))}
        return {iid: self.spline(host, iid.replace(".", ""), *tr.component(None, lambda v: v * scale))}

    def cull(self, L, tool, frames=None):
        """Enabled region of the CONSUMING Merge = hull of the visible frames +- margin (applied live after the paste). Culling
        only: in/out visibility rides on the Merge Blend / card opacity (opacity_in), so the margin frames draw nothing."""
        if not self.eff["cull"]:
            return
        vis = frames if frames is not None else self.visible_frames(L)
        if all(vis):
            return
        idx = [i for i, v in enumerate(vis) if v]
        m = int(self.eff["cullMargin"])
        if not idx:
            self.regions[tool] = [-2, -1]
            self.decisions.append("%s: never visible: region outside the scene" % tool)
            return
        s, e = max(0, idx[0] - m), min(self.dur - 1, idx[-1] + m)
        if s == 0 and e == self.dur - 1:
            return
        self.regions[tool] = [s, e]

    def matte(self, L, space, col, y0):
        """Track matte: the matte layer drawn into a clear container canvas -> BitmapMask on the consumer Merge."""
        m = L["matte"]
        ML = self.byid[m["layer"]]
        base = self.g.add(self.n(L["id"], "MatteBase"), "Background", {"UseFrameFormatSettings": 0, "Width": _even(space.W), "Height": _even(space.H),
                                                                       "Depth": DEPTH["int8"], "TopLeftAlpha": 0}, pos=(col + 0.5, y0 + 2))
        self.lset(L, base)
        save = self.layers.get(ML["id"])
        self._mask_depth += 1   # the matte's image chain is a mask branch: no freezes inside it
        try:
            top = self.layer2d(ML, space, base, col + 0.5, y0 + 3)
        finally:
            self._mask_depth -= 1
        self.cur_col, self.cur_y = col, y0
        mode = m.get("mode", "alpha")
        bm = self.lset(L, self.g.add(self.n(L["id"], "Matte"), "BitmapMask", {
            "Image": Src(top), "Channel": FuID("Luminance" if mode.startswith("luma") else "Alpha"),
            "Invert": 1 if mode.endswith("Inverted") else 0, "UseFrameFormatSettings": 0, "Width": _even(space.W), "Height": _even(space.H)},
            pos=(col + 0.5, y0 + 1)))
        if save is None:
            self.layers.setdefault(ML["id"], [])
        return bm

    # ------------------------------------------------------------ motion blur tables
    def mb_frames_2d(self, L, src, space, parents):
        """Per frame: on-screen streak across the shutter above the threshold (corners of the canvas)."""
        mbc = self.cfg["motionBlur"]
        if not mbc["on"] or L.get("motionBlur") is False:
            return [False] * self.dur
        ks = set(L.get("keys") or {}) & {"position", "scale", "rotation"}
        if not ks and not any(P.get("keys") for P in parents):
            return [False] * self.dur
        d = mbc["shutter"] / 720.0
        hw, hh = src.W / src.k / 2, src.H / src.k / 2
        corners = [(src.c[0] + sx * hw, src.c[1] + sy * hh) for sx in (-1, 1) for sy in (-1, 1)]
        thr = self.eff["mbThresholdPx"] if self.eff["adaptiveMotionBlur"] else 0.0
        out = []
        for f in range(self.dur):
            m = 0.0
            for p in corners:
                a = self.world2d(L, f - d, p, parents)
                b = self.world2d(L, f + d, p, parents)
                m = max(m, math.hypot(a[0] - b[0], a[1] - b[1]))
            out.append(m >= thr and m > 1e-6)
        return out

    def mb2d_samples(self):
        """Motion-blur Quality of 2D tools (layer Merges, 2.5D cards, size-blur Transforms): efficiency.mb2dSamples, else the scene's
        samples capped at 8 [efficiency lab item 7: bench_s2 Delivered 72 frames in 42.1 s at 8 vs 49.9 s at 12, pixels within tile 0.5;
        4 was 35.5 s but borderline, tile 2]. The Renderer3D keeps render3d.mbQuality."""
        v = self.eff.get("mb2dSamples")
        return int(v) if v else min(int(self.cfg["motionBlur"]["samples"]), 8)

    def mb_inputs(self, frames, samples):
        """MotionBlur on the frames that move (a per-frame table expression, efficiency lab T02), always off in draft."""
        on = [1 if x else 0 for x in frames]
        ins = {"Quality": samples, "ShutterAngle": self.cfg["motionBlur"]["shutter"], "CenterBias": 0}
        if all(on):
            ins["MotionBlur"] = Expr(self.draft_off("1"), 1)
        elif self.eff.get("mbForm") == "runs":
            runs, s0 = [], None
            for f, x in enumerate(on + [0]):
                if x and s0 is None:
                    s0 = f
                elif not x and s0 is not None:
                    runs.append((s0, f - 1))
                    s0 = None
            cond = " or ".join("(t >= %d and t <= %d)" % r for r in runs) or "false"
            ins["MotionBlur"] = Expr(":local t = floor(time + 0.5); if %s > 0.5 then return 0 end; if %s then return 1 end; return 0"
                                     % (self.ctrl_ref("Draft"), cond), 1)
        else:
            ins["MotionBlur"] = Expr(":local q = {%s}; if %s > 0.5 then return 0 end; return q[floor(time + 0.5) + 1] or 0"
                                     % (",".join(str(x) for x in on), self.ctrl_ref("Draft")), 1)
        return ins

    # ------------------------------------------------------------ 3D
    def cam_state(self, cam, t, space):
        """Camera position, target (or None), zoom in container px at time t."""
        zoom0 = float(cam.get("zoom", space.cw * 2666.7 / 1920.0)) if cam else space.cw * 2666.7 / 1920.0
        if cam is None:
            return (space.cw / 2, space.ch / 2, -zoom0), (space.cw / 2, space.ch / 2, 0.0), zoom0
        P = self.prop_at(cam, "position", t, [space.cw / 2, space.ch / 2, -zoom0])
        T = self.prop_at(cam, "poi", t, cam.get("poi", [space.cw / 2, space.ch / 2, 0.0]) if "poi" in cam else [space.cw / 2, space.ch / 2, 0.0])
        if "poi" in cam and cam["poi"] is None and "poi" not in (cam.get("keys") or {}):
            T = None
        z = float(self.prop_at(cam, "zoom", t, zoom0))
        return tuple(float(x) for x in P[:3]), (tuple(float(x) for x in T[:3]) if T is not None else None), z

    def project(self, cam, t, space, p):
        C, T, z = self.cam_state(cam, t, space)
        f = _norm(_sub(T, C)) if T is not None else _mv(_rot(self.sval(self.prop_at(cam, "rotationX", t, 0)),
                                                              self.sval(self.prop_at(cam, "rotationY", t, 0)),
                                                              self.sval(self.prop_at(cam, "rotation", t, 0))), (0, 0, 1))
        r = _norm(_cross(f, (0, -1, 0)))
        dn = _cross(f, r)
        v = _sub(p, C)
        depth = _dot(v, f)
        if depth <= 1e-3:
            return None, depth
        return (space.cw / 2 + z * _dot(v, r) / depth, space.ch / 2 + z * _dot(v, dn) / depth), depth

    def world3d(self, L, t, p, space):
        box = self.box(L)
        A = self.anchor(L, box)
        pos = list(self.prop_at(L, "position", t, [space.cw / 2, space.ch / 2, 0]))
        pos += [0.0] * (3 - len(pos))
        s = self.scale_at(L, t)
        R = _rot(self.sval(self.prop_at(L, "rotationX", t, 0)), self.sval(self.prop_at(L, "rotationY", t, 0)),
                 self.sval(self.prop_at(L, "rotation", t, 0)))
        v = _mv(R, ((p[0] - A[0]) * s[0] / 100, (p[1] - A[1]) * s[1] / 100, 0.0))
        w = tuple(a + b for a, b in zip(pos, v))
        P = L.get("parent")
        if P:
            PL = self.byid[P]
            return self.world3d_parent(PL, t, w, space)
        return w

    def world3d_parent(self, P, t, w, space):
        pos = list(self.prop_at(P, "position", t, [space.cw / 2, space.ch / 2, 0]))
        pos += [0.0] * (3 - len(pos))
        A = list(P.get("anchor") or [0, 0, 0]) + [0.0] * 3
        s = self.scale_at(P, t)
        R = _rot(self.sval(self.prop_at(P, "rotationX", t, 0)), self.sval(self.prop_at(P, "rotationY", t, 0)),
                 self.sval(self.prop_at(P, "rotation", t, 0)))
        v = _mv(R, ((w[0] - A[0]) * s[0] / 100, (w[1] - A[1]) * s[1] / 100, w[2] - A[2]))
        out = tuple(a + b for a, b in zip(pos, v))
        if P.get("parent"):
            return self.world3d_parent(self.byid[P["parent"]], t, out, space)
        return out

    def card_screen(self, L, cam, t, space, box):
        pts = [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]
        out = []
        for p in pts:
            q, d = self.project(cam, t, space, self.world3d(L, t, p, space))
            out.append((q, d))
        return out

    def flat_ok(self, layers, cam, space):
        """2.5D eligibility: cards face the camera (no X/Y rotation, no 3D parent), camera looks straight down +z."""
        for L in layers:
            ks = L.get("keys") or {}
            if L.get("rotationX") or L.get("rotationY") or "rotationX" in ks or "rotationY" in ks or L.get("parent") or L.get("lit"):
                return False, "%s rotates in 3D or has a 3D parent" % L["id"]
            if L.get("matte") or L.get("blend", "normal") != "normal":
                pass
        for f in range(self.dur):
            C, T, _ = self.cam_state(cam, f, space)
            if cam and (cam.get("rotationX") or cam.get("rotationY") or cam.get("rotation")):
                return False, "camera rotates"
            if T is not None and (abs(T[0] - C[0]) > 1e-6 or abs(T[1] - C[1]) > 1e-6):
                return False, "camera does not look straight down +z (point of interest off axis)"
        order = None
        for f in range(self.dur):
            depths = []
            for L in layers:
                pos = list(self.prop_at(L, "position", f, [0, 0, 0])) + [0, 0, 0]
                depths.append(pos[2])
            o = sorted(range(len(layers)), key=lambda i: (-depths[i], i))
            if order is not None and o != order:
                return False, "card depth order changes over the shot"
            order = o
        return True, None

    def tex_scale(self, L, cam, space):
        """Texture px per layer px = the largest on-screen scale over the visible frames where the card is SHARP (its motion-blur
        streak under efficiency.sharpTexturePx; a card smeared across 30 px shows no texture detail), x margin, clamped."""
        box = self.content_box(L)
        vis = self.visible_frames(L)
        w = max(box[2] - box[0], 1e-6)
        mbc = self.cfg["motionBlur"]
        d = mbc["shutter"] / 720.0
        lim = self.eff.get("sharpTexturePx")
        blur_on = mbc["on"] and L.get("motionBlur", True) and lim
        sharp, soft = 0.0, 0.0
        for f in range(self.dur):
            if not vis[f]:
                continue
            sc = self.card_screen(L, cam, f, space, box)
            if all(q is None for q, _ in sc):
                continue  # entirely behind the camera: not seen
            if any(q is None for q, _ in sc):
                s_ = self.eff["maxTextureScale"]
            else:
                (a, _), (b, _), (c, _), (e, _) = sc
                s_ = max(math.hypot(b[0] - a[0], b[1] - a[1]) / w, math.hypot(e[0] - c[0], e[1] - c[1]) / w,
                         math.hypot(c[0] - a[0], c[1] - a[1]) / max(box[3] - box[1], 1e-6))
            streak = 0.0
            if blur_on:
                p0, p1 = self.card_screen(L, cam, f - d, space, box), self.card_screen(L, cam, f + d, space, box)
                streak = max((math.hypot(u[0][0] - v[0][0], u[0][1] - v[0][1]) if u[0] and v[0] else 1e9) for u, v in zip(p0, p1))
            if blur_on and streak > lim:
                soft = max(soft, s_)
            else:
                sharp = max(sharp, s_)
        best = sharp if sharp > 0 else soft
        if soft > sharp > 0:
            self.decisions.append("%s: texture sized for its sharp frames (%.2gx); frames smeared over %g px would ask %.2gx"
                                  % (L["id"], sharp, lim, soft))
        k = best * self.eff["textureMargin"]
        return min(self.eff["maxTextureScale"], max(self.eff["minTextureScale"], _q8(k))) * space.k

    def block3d(self, layers, cam, lights, space, cur, col, y0, path):
        mode = self.eff["mode3d"]
        if mode in ("auto", "2.5d"):
            ok, why = self.flat_ok(layers, cam, space)
            if ok:
                self.stats["renderers2_5d"] += 1
                self.decisions.append("3D block (%s): 2.5D, no Renderer3D (flat cards, straight camera)" % ", ".join(L["id"] for L in layers))
                return self.block25d(layers, cam, space, cur, col, y0)
            if mode == "2.5d":
                self.warnings.append("mode3d 2.5d refused: %s; real 3D used" % why)
            else:
                self.decisions.append("3D block (%s): real 3D (%s)" % (", ".join(L["id"] for L in layers), why))
        if any(L.get("glass") for L in layers):
            return self.block_real_glass(layers, cam, lights, space, cur, col, y0, path)
        return self.block_real(layers, cam, lights, space, cur, col, y0, path)

    def block_real_glass(self, layers, cam, lights, space, cur, col, y0, path):
        """[sb3] Glass on cards inside a Renderer3D: the block is split at each glass card. The cards listed before it render in one
        pass; everything under it (that pass and the 2D stack) is frosted inside the glass card's silhouette (the card alone through the
        same camera, DOF and motion blur, over a clear canvas); the glass card and the cards listed after it render in the next pass
        over that. Depth order must follow list order around a glass card (a later card always draws over an earlier one)."""
        cuts = [i for i, L in enumerate(layers) if L.get("glass")]
        if cuts[0] > 0:
            cur = self.block_real(layers[:cuts[0]], cam, lights, space, cur, col, y0, path)
        for j, i in enumerate(cuts):
            G = layers[i]
            grp = layers[i:cuts[j + 1] if j + 1 < len(cuts) else len(layers)]
            W, H = _even(space.W), _even(space.H)
            base = self.lset(G, self.g.add(self.n(G["id"], "GlassBase"), "Background", {
                "UseFrameFormatSettings": 0, "Width": W, "Height": H, "Depth": DEPTH["int8"], "TopLeftAlpha": 0}, pos=(col + j + 0.5, y0 + 2)))
            below = cur   # the front pass first (the textures get their plain names), over the Glass Merge frost() adds below
            cur = self.block_real(grp, cam, lights, space, self.n(G["id"], "Glass"), col + j + 1, y0, path)
            ns = self.ns
            self.ns = (ns + "_" if ns else "") + "Sil"   # the silhouette pass: its own card, renderer and rig names
            try:
                sil = self.block_real([G], cam, [], space, base, col + j + 0.5, y0 + 4, path)
            finally:
                self.ns = ns
            self.lset(G, self.g.add(self.n(G["id"], "GlassMask"), "BitmapMask", dict(self.COVERAGE, Image=Src(sil), UseFrameFormatSettings=0,
                                                                                     Width=W, Height=H), pos=(col + j + 0.5, y0 + 1)))
            self.frost(G, below, space, col + j, y0)
        self.decisions.append("3D glass: the Renderer3D block is split at %s (a pass behind, a silhouette pass, a pass in front)"
                              % ", ".join(layers[i]["id"] for i in cuts))
        return cur

    def camera(self, cam, space, pos):
        name = self.n(cam["id"] if cam else "Camera")
        if name in self.g.t:
            return name
        zoom0 = float(cam.get("zoom", space.cw * 2666.7 / 1920.0)) if cam else space.cw * 2666.7 / 1920.0
        f_of = lambda z: (APERTURE_H * 25.4 / 2) * z / (space.ch / 2)  # noqa: E731 (gate fit Height)
        ins = {"FilmGate": FuID("BMD_URSA_4K_16x9"), "ApertureW": APERTURE_W, "ApertureH": APERTURE_H,
               "ResolutionGateFit": FuID("Height"), "PerspAdaptiveClip": 0, "PerspNearClip": 0.01, "PerspFarClip": 200}
        ks = (cam or {}).get("keys") or {}
        if "zoom" in ks:
            ins["FLength"] = self.spline(name, "FLength", *self.track(cam, "zoom").component(None, f_of))
        else:
            ins["FLength"] = f_of(zoom0)
        P0 = (cam or {}).get("position") or [space.cw / 2, space.ch / 2, -zoom0]
        self.xyz(cam or {}, "position", P0, name, "Transform3DOp.Translate", space, ins)
        has_poi = cam is None or cam.get("poi", True) is not None or "poi" in ks
        if has_poi:
            ins["Transform3DOp.UseTarget"] = 1
            T0 = (cam or {}).get("poi") or [space.cw / 2, space.ch / 2, 0]
            self.xyz(cam or {}, "poi", T0, name, "Transform3DOp.Target", space, ins)
        else:
            ins["Transform3DOp.Rotate.RotOrder"] = FuID("ZYX")
            for prop, ax, sgn in (("rotationX", "X", 1), ("rotationY", "Y", -1), ("rotation", "Z", -1)):
                if prop in ks:
                    ins["Transform3DOp.Rotate." + ax] = self.spline(name, "Rotate" + ax, *self.track(cam, prop).component(None, lambda v, s=sgn: s * v))
                elif cam.get(prop):
                    ins["Transform3DOp.Rotate." + ax] = self.scalar(cam[prop], sign=sgn)
        dof = (cam or {}).get("dof")
        if dof:
            fo = dof.get("focus", zoom0)
            if isinstance(fo, str):
                ins["PlaneOfFocus"] = self.focus_expr(name, self.focus_null(self.byid[fo], space), space, cam)
            else:
                ins["PlaneOfFocus"] = float(fo) / space.ch
        self.g.add(name, "Camera3D", ins, pos=pos)
        return name

    def xyz(self, L, prop, static, host, base, space, ins):
        tr = self.track(L, prop) if L else None
        for i, ax in enumerate("XYZ"):
            fn = [lambda v: (v - space.cw / 2) / space.ch, lambda v: (space.ch / 2 - v) / space.ch, lambda v: -v / space.ch][i]
            if tr and any(abs(v[i] - tr.v[0][i]) > 1e-9 for v in tr.v):
                ins[base + "." + ax] = self.spline(host, (base + ax).replace("Transform3DOp", ""), *tr.component(i, fn))
            else:
                v = (tr.v[0] if tr else static)
                v = list(v) + [0.0] * (3 - len(v))
                val = fn(float(v[i]))
                if abs(val) > 1e-12:
                    ins[base + "." + ax] = val

    def focus_null(self, F, space):
        name = self.n(F["id"])
        if name in self.g.t:
            return name
        ins = {}
        self.xyz(F, "position", F.get("position") or [space.cw / 2, space.ch / 2, 0], name, "Transform3DOp.Translate", space, ins)
        self.g.add(name, "Transform3D", ins, pos=(self.cur_col, self.cur_y - 4))
        self.lset(F, name)
        return name

    def focus_expr(self, cam, focus, space, camL):
        n = cam
        e = (":local cx, cy, cz = {n}.Transform3DOp.Translate.X, {n}.Transform3DOp.Translate.Y, {n}.Transform3DOp.Translate.Z; "
             "local dx, dy, dz = {n}.Transform3DOp.Target.X - cx, {n}.Transform3DOp.Target.Y - cy, {n}.Transform3DOp.Target.Z - cz; "
             "local l = math.sqrt(dx*dx + dy*dy + dz*dz); "
             "return math.max(0.05, (({f}.Transform3DOp.Translate.X - cx)*dx + ({f}.Transform3DOp.Translate.Y - cy)*dy + "
             "({f}.Transform3DOp.Translate.Z - cz)*dz) / l)").format(n=n, f=focus)
        return Expr(e, 2.469)

    def block_real(self, layers, cam, lights, space, cur, col, y0, path):
        self.stats["renderers"] += 1
        base = self.n(path, "R3D") if path else self.n("R3D")
        i = 1
        while base in self.g.t:
            i += 1
            base = (self.n(path, "R3D") if path else self.n("R3D")) + str(i)
        cam_name = self.camera(cam, space, (col, y0 - 6))
        if cam:
            self.lset(cam, cam_name)
        items = []
        vis_all = [False] * self.dur
        mb = [False] * self.dur
        mbc = self.cfg["motionBlur"]
        d = mbc["shutter"] / 720.0
        thr = self.eff["mbThresholdPx"] if self.eff["adaptiveMotionBlur"] else 0.0
        kk = self.shared_scales(layers, cam, space)
        for j, L in enumerate(layers):
            self.cur_col, self.cur_y = col + j * 0.5, y0 - 8 - j
            k = kk[L["id"]]
            box = self.content_box(L)
            src = self.source(L, k, pivot=False, mode3d=True)
            if src.owner == L["id"] and not any(t["tool"] == src.name for t in self.textures):
                self.textures.append({"layer": L["id"], "tool": src.name, "size": [src.W, src.H], "scale": round(k / space.k, 3)})
                self.decisions.append("%s: 3D texture %dx%d (%.3gx of design px: largest on-screen size)" % (L["id"], src.W, src.H, k / space.k))
            img = src.name
            if self.eff["hold"] and src.animated:
                hn, n2 = src.name + "_Hold", 2
                # a group whose last child is an animated group: the child's own 2D hold already took this name with a
                # different input (the 3D card then showed only the child); never reuse a hold of another source
                while hn in self.g.t and self.g.t[hn]["inputs"].get("Input") != Src(src.name):
                    hn, n2 = "%s_Hold%d" % (src.name, n2), n2 + 1
                if hn not in self.g.t:
                    self.g.add(hn, "TimeStretcher", {"Input": Src(src.name), "SourceTime": Expr("floor(time + 0.5)", 0),
                                                     "InterpolateBetweenFrames": 0}, pos=(self.cur_col, self.cur_y + 0.5))
                    self.stats["holds"] += 1
                img = self.lset(L, hn)
            elif self.eff["freeze"] and self.src_static(L):
                img = self.lset(L, self.freeze(src.name, "static texture of a 3D card"))
            items.append(self.card(L, img, src, space, box))
            vis = self.visible_frames(L)
            vis_all = [a or b for a, b in zip(vis_all, vis)]
            if mbc["on"] and L.get("motionBlur", True):
                for f in range(self.dur):
                    if vis[f] and not mb[f]:
                        a = self.card_screen(L, cam, f - d, space, box)
                        b = self.card_screen(L, cam, f + d, space, box)
                        m = max((math.hypot(p[0][0] - q[0][0], p[0][1] - q[0][1]) if p[0] and q[0] else 1e9) for p, q in zip(a, b))
                        mb[f] = m >= thr and m > 1e-6
        light_names = [self.light(Lt, space, (col + 1, y0 - 6 - i)) for i, Lt in enumerate(lights)]
        items = self.rigs(layers, items, space, (col - 0.5, y0 - 3))
        m3 = self.g.add(base + "_Scene", "Merge3D", dict({("SceneInput%d" % (i + 1)): Src(n) for i, n in enumerate(items + [cam_name] + light_names)}),
                        pos=(col, y0 - 2))
        r3 = self.render3d(base, m3, cam, space, mb, (col, y0 - 1), lit=bool(light_names))
        mname = base + "_Mrg"
        self.g.add(mname, "Merge", {"Background": Src(cur), "Foreground": Src(r3), "PerformDepthMerge": 0}, pos=(col, y0))
        for L in layers:
            self.lset(L, mname)
        self.cull(None, mname, frames=vis_all) if self.eff["cull"] else None
        return mname

    def xform3d(self, L, host, origin, space, shift=(0.0, 0.0, 0.0), scale_mul=1.0):
        """Transform3DOp inputs of an AE-style 3D layer: position relative to origin (the container center, or the parent's
        anchor), rotations with the ZYX order and Y/Z sign flip [rebuild K7], uniform scale x scale_mul."""
        out = {}
        ks = L.get("keys") or {}
        ox, oy, oz = origin
        P0 = list(L.get("position") or [space.cw / 2, space.ch / 2, 0]) + [0.0]
        tr = self.track(L, "position")
        for i, ax in enumerate("XYZ"):
            fn = [lambda v: (v + shift[0] - ox) / space.ch, lambda v: (oy - v - shift[1]) / space.ch,
                  lambda v: -(v + shift[2] - oz) / space.ch][i]
            if tr and any(abs((list(v) + [0])[i] - (list(tr.v[0]) + [0])[i]) > 1e-9 for v in tr.v):
                tr3 = Track([[k_[0], list(k_[1]) + [0.0] * (3 - len(k_[1]))] + list(k_[2:]) for k_ in ks["position"]], self.eases)
                out["Transform3DOp.Translate." + ax] = self.spline(host, "Translate" + ax, *tr3.component(i, fn))
            else:
                v = (list(tr.v[0]) + [0.0])[i] if tr else float(P0[i])
                val = fn(float(v))
                if abs(val) > 1e-12:
                    out["Transform3DOp.Translate." + ax] = val
        out["Transform3DOp.Rotate.RotOrder"] = FuID("ZYX")
        for prop, ax, sgn in (("rotationX", "X", 1), ("rotationY", "Y", -1), ("rotation", "Z", -1)):
            if prop in ks:
                out["Transform3DOp.Rotate." + ax] = self.spline(host, "Rotate" + ax, *self.track(L, prop).component(None, lambda v, s=sgn: s * v))
            elif isinstance(L.get(prop), (str, dict)) or self.sval(L.get(prop, 0)):
                out["Transform3DOp.Rotate." + ax] = self.scalar(L[prop], sign=sgn)
        s0 = self.scale_at(L, 0)
        if "scale" in ks:
            tr_s = self.track(L, "scale")
            comp = 0 if isinstance(tr_s.v[0], (list, tuple)) else None
            out["Transform3DOp.Scale.X"] = self.spline(host, "ScaleX", *tr_s.component(comp, lambda v: v / 100 * scale_mul))
        elif abs(s0[0] / 100 * scale_mul - 1) > 1e-9:
            out["Transform3DOp.Scale.X"] = s0[0] / 100 * scale_mul
        if abs(s0[0] - s0[1]) > 1e-9:
            self.warnings.append("%s: non-uniform scale on a 3D layer uses the X scale only" % L["id"])
        return out

    def origin3d(self, L, space):
        """Where a 3D layer's position is measured from: its parent's anchor (AE parenting) or the container center."""
        if L.get("parent"):
            A = list(self.byid[L["parent"]].get("anchor") or [0, 0, 0]) + [0.0, 0.0]
            return (float(A[0]), float(A[1]), float(A[2]))
        return (space.cw / 2, space.ch / 2, 0.0)

    def card(self, L, img, src, space, box):
        """ImagePlane3D (unlit, 1 unit wide = texture width) placed like an AE 3D layer; a Merge3D carries the transform when
        the anchor is off the texture center and the layer rotates or scales."""
        name = self.lset(L, self.n(L["id"], "Card"))
        A = self.anchor(L, box)
        wu = src.W / src.k / space.ch
        ins = {"MaterialInput": Src(img), "Transform3DOp.Scale.X": wu, "Transform3DOp.Rotate.RotOrder": FuID("ZYX"),
               "SurfacePlaneInputs.Lighting.IsAffectedByLights": 1 if L.get("lit") else 0,
               "SurfacePlaneInputs.Lighting.IsShadowCaster": 0, "SurfacePlaneInputs.Lighting.IsShadowReceiver": 0}
        ks = L.get("keys") or {}
        off = (src.c[0] - A[0], src.c[1] - A[1])
        rot_anim = bool(set(ks) & {"rotation", "rotationX", "rotationY", "scale"}) or any(
            isinstance(L.get(p), (str, dict)) or self.sval(L.get(p, 0)) for p in ("rotation", "rotationX", "rotationY"))
        parent_needed = (abs(off[0]) > 1e-9 or abs(off[1]) > 1e-9) and rot_anim
        origin = self.origin3d(L, space)
        if parent_needed:
            tname = self.lset(L, self.n(L["id"], "Xf"))
            ins["Transform3DOp.Translate.X"] = off[0] / space.ch
            ins["Transform3DOp.Translate.Y"] = -off[1] / space.ch
            target = self.xform3d(L, tname, origin, space)
        else:
            # position P + R*S*offset: static rotation/scale folded, keys shifted by a constant
            s0 = self.scale_at(L, 0)
            R0 = _rot(self.sval(L.get("rotationX", 0)), self.sval(L.get("rotationY", 0)), self.sval(L.get("rotation", 0)))
            shift = _mv(R0, (off[0] * s0[0] / 100, off[1] * s0[1] / 100, 0.0))
            ins.update(self.xform3d(L, name, origin, space, shift, scale_mul=wu))
            ins["Transform3DOp.Scale.X"] = ins.get("Transform3DOp.Scale.X", wu)
        ins.update(self.opacity_in(L, name, "MtlStdInputs.Diffuse.Opacity", 1.0 / 100, stepped=True))
        if L.get("blend", "normal") != "normal" or L.get("matte"):
            self.warnings.append("%s: blend modes and track mattes are not applied to 3D layers" % L["id"])
        self.g.add(name, "ImagePlane3D", ins, pos=(self.cur_col, self.cur_y + 1))
        if parent_needed:
            target["SceneInput1"] = Src(name)
            self.g.add(tname, "Merge3D", target, pos=(self.cur_col, self.cur_y + 1.5))
            self.decisions.append("%s: anchor off the texture center under 3D rotation/scale: a Merge3D carries the transform" % L["id"])
            return tname
        return name

    def rigs(self, layers, items, space, pos):
        """3D parenting: one Merge3D per parent null carrying its transform (native Fusion parenting); children sit in its space."""
        by_parent, tops = {}, []
        for L, it in zip(layers, items):
            (by_parent.setdefault(L["parent"], []) if L.get("parent") else tops).append(it)
        nulls = set()
        for L in layers:
            p = L.get("parent")
            while p:
                nulls.add(p)
                p = self.byid[p].get("parent")
        made = {}

        def rig(pid):
            if pid in made:
                return made[pid]
            N = self.byid[pid]
            kids = list(by_parent.get(pid, [])) + [rig(c) for c in sorted(nulls) if self.byid[c].get("parent") == pid]
            name, r = self.n(pid, "Rig"), 1
            while name in self.g.t:   # a null parenting cards in two render passes of a split block: one rig per pass
                r += 1
                name = self.n(pid, "Rig%d" % r)
            self.lset(N, name)
            ins = self.xform3d(N, name, self.origin3d(N, space), space)
            ins.update({("SceneInput%d" % (i + 1)): Src(k) for i, k in enumerate(kids)})
            self.g.add(name, "Merge3D", ins, pos=(pos[0], pos[1] - 0.5 * len(made)))
            made[pid] = name
            return name
        for pid in sorted(nulls):
            if not self.byid[pid].get("parent"):
                tops.append(rig(pid))
        if nulls:
            self.decisions.append("3D parents %s: Merge3D rigs carry the null transforms" % sorted(nulls))
        return tops

    def light(self, Lt, space, pos):
        kind = Lt.get("light", "ambient")
        reg = {"ambient": "LightAmbient", "point": "LightPoint", "directional": "LightDirectional", "spot": "LightSpot"}[kind]
        ins = dict(self.color(Lt.get("color", "#FFFFFF"), ("Red", "Green", "Blue", "_a")))
        ins.pop("_a")
        ins["Intensity"] = float(Lt.get("intensity", 100)) / 100
        name = self.n(Lt["id"])
        if name in self.g.t:   # one light node feeds every render pass of a split block
            return name
        if kind != "ambient":
            self.xyz(Lt, "position", Lt.get("position") or [space.cw / 2, space.ch / 2, -1000], name, "Transform3DOp.Translate", space, ins)
        self.lset(Lt, self.g.add(name, reg, ins, pos=pos))
        return name

    def render3d(self, base, scene, cam, space, mb, pos, lit=False):
        r3 = self.render3d_cfg = self.cfg["render3d"]
        dof = (cam or {}).get("dof")
        ins = {"SceneInput": Src(scene), "RendererType": FuID("RendererOpenGL"),
               "RendererOpenGL.TransparencySorting": 1 if r3["transparency"] == "sorted" else 0}
        if space.W == self.W and space.H == self.H and space.k == 1:
            ins["UseFrameFormatSettings"] = 1
        else:
            ins.update(UseFrameFormatSettings=0, Width=_even(space.W), Height=_even(space.H))
        if lit:
            ins["RendererOpenGL.LightingEnabled"] = 1
        if dof:
            ap = float(dof.get("aperture", 50))
            ins["RendererOpenGL.EnableAccumEffects"] = Expr(self.draft_off("1"), 1)
            ins["RendererOpenGL.EnableAccumDepthOfField"] = 1
            ins["RendererOpenGL.AccumQuality"] = r3["accumQuality"]
            ins["RendererOpenGL.DoFBlur"] = Expr("%s*%s/100" % (_num(ap / 2 / space.ch), self.ctrl_ref("FocusBlur")), ap / 2 / space.ch)  # [rebuild K3]
            self.decisions.append("%s: accumulation DOF (AccumQuality %d; nearly free in Deliver, efficiency lab P0)" % (base, r3["accumQuality"]))
        if any(mb):
            ins.update(self.mb_inputs(mb, r3["mbQuality"]))
            if dof and r3["accumQuality"] >= r3["mbQuality"]:
                # with accumulation on, the passes carry time and lens samples: samples fit max(Quality, AccumQuality), so Quality
                # adds nothing here (efficiency lab T02: Quality 1 and 8 identical at AccumQuality 12; T18)
                ins["Quality"] = 1
                self.decisions.append("%s: motion-blur samples = AccumQuality %d (Quality is not used under accumulation)" % (base, r3["accumQuality"]))
            self.stats["mbMerges"] += 0
            n_on = sum(1 for x in mb if x)
            self.decisions.append("%s: motion blur on %d of %d frames (adaptive, streak >= %g px)" % (base, n_on, self.dur, self.eff["mbThresholdPx"]))
        if r3["transparency"] == "zbuffer":
            self.decisions.append("%s: TransparencySorting 0 (Z buffer): Sorted + accumulation drops cards non-deterministically "
                                  "(efficiency lab B5); overlapping semi-transparent cards may mis-order: render3d.transparency 'sorted' per scene" % base)
        return self.g.add(base, "Renderer3D", ins, pos=pos)

    def block25d(self, layers, cam, space, cur, col, y0):
        """Flat cards under a straight camera: each card is a 2D Merge with per-frame projected Center/Size; DOF = per-card Blur
        sized from the circle of confusion (AE's own per-layer method)."""
        order = sorted(layers, key=lambda L: -float((list(L.get("position") or [0, 0, 0]) + [0, 0, 0])[2]))
        dof = (cam or {}).get("dof")
        mbc = self.cfg["motionBlur"]
        d = mbc["shutter"] / 720.0
        thr = self.eff["mbThresholdPx"] if self.eff["adaptiveMotionBlur"] else 0.0
        kk = self.shared_scales(layers, cam, space)
        for j, L in enumerate(order):
            self.cur_col, self.cur_y = col + j, y0
            k = kk[L["id"]]
            box = self.content_box(L)
            src = self.source(L, k, pivot=False)
            if src.owner == L["id"]:
                self.textures.append({"layer": L["id"], "tool": src.name, "size": [src.W, src.H], "scale": round(k / space.k, 3)})
            vis = self.visible_frames(L)
            mname = self.n(L["id"])
            fr, cx, cy, sz, blur, mb = [], [], [], [], [], []
            for f in range(self.dur):
                q, depth = self.project(cam, f, space, self.world3d(L, f, src.c, space))
                if q is None:
                    q, depth = (space.cw / 2, space.ch / 2), 1e-3
                _, _, zoom = self.cam_state(cam, f, space)
                s = self.scale_at(L, f)[0] / 100
                fr.append(f)
                u, v = space.uv(*q)
                cx.append(u)
                cy.append(v)
                sz.append(zoom / depth * s * space.k / src.k)
                if dof:
                    fd = self.focus_distance(cam, f, space)
                    coc = float(dof.get("aperture", 50)) * zoom * abs(1 / fd - 1 / depth)
                    sigma_screen = 0.536 * coc / 2
                    sigma_tex = sigma_screen / max(zoom / depth * s, 1e-6) * src.k
                    blur.append(sigma_tex / (1.25 * src.W / 1920.0))
                if mbc["on"] and L.get("motionBlur", True):
                    a = self.card_screen(L, cam, f - d, space, box)
                    b = self.card_screen(L, cam, f + d, space, box)
                    m = max((math.hypot(p[0][0] - q_[0][0], p[0][1] - q_[0][1]) if p[0] and q_[0] else 1e9) for p, q_ in zip(a, b))
                    mb.append(vis[f] and m >= thr and m > 1e-6)
                else:
                    mb.append(False)
            img = src.name
            if dof and max(blur) > 0.01:
                bn = self.lset(L, self.n(L["id"], "DOF"))
                bv = self.compress(fr, blur)
                self.g.add(bn, "Blur", {"Input": Src(img), "XBlurSize": self.spline(bn, "XBlurSize", *bv) if len(bv[0]) > 1 else bv[1][0]},
                           pos=(col + j, y0 - 0.5))
                img = bn
            if any(mb) and src.animated and self.eff["hold"]:
                img = self.lset(L, self.g.add(self.n(L["id"], "Hold"), "TimeStretcher", {"Input": Src(img), "SourceTime": Expr("floor(time + 0.5)", 0),
                                                                                        "InterpolateBetweenFrames": 0}, pos=(col + j - 0.5, y0 - 1)))
                self.stats["holds"] += 1
            elif self.eff["freeze"] and self.src_static(L) and not (dof and max(blur) > 0.01):
                img = self.lset(L, self.freeze(img, "static texture of a 2.5D card"))
            ins = {"Background": Src(cur), "Foreground": Src(img), "PerformDepthMerge": 0}
            cxv, cyv, szv = self.compress(fr, cx), self.compress(fr, cy), self.compress(fr, sz)
            if len(cxv[0]) > 1 or len(cyv[0]) > 1:
                ins["Center"] = self.xypath(mname, "Center", cxv if len(cxv[0]) > 1 else cxv[1][0], cyv if len(cyv[0]) > 1 else cyv[1][0])
            else:
                ins["Center"] = (cxv[1][0], cyv[1][0])
            ins["Size"] = self.spline(mname, "Size", *szv) if len(szv[0]) > 1 else szv[1][0]
            if "rotation" in (L.get("keys") or {}):
                ins["Angle"] = self.spline(mname, "Angle", *self.track(L, "rotation").component(None, lambda v: -v))
            elif self.sval(L.get("rotation", 0)):
                ins["Angle"] = self.scalar(L["rotation"], sign=-1)
            ins.update(self.opacity_in(L, mname, "Blend", 1.0 / 100, stepped=bool(any(mb))))
            if any(mb):
                ins.update(self.mb_inputs(mb, self.mb2d_samples()))
                self.stats["mbMerges"] += 1
            if L.get("glass"):   # a 2.5D card is a 2D Merge over everything behind it: the 2D backdrop blur applies as is
                ins["Background"] = Src(self.glass(L, cur, ins, space, mname, col + j, y0))
            self.lset(L, self.g.add(mname, "Merge", ins, pos=(col + j, y0)))
            self.cull(L, mname)
            cur = mname
        return cur

    def focus_distance(self, cam, f, space):
        dof = cam.get("dof") or {}
        fo = dof.get("focus")
        C, T, zoom = self.cam_state(cam, f, space)
        if isinstance(fo, str):
            F = self.byid[fo]
            p = list(self.prop_at(F, "position", f, [space.cw / 2, space.ch / 2, 0])) + [0.0]
            fwd = _norm(_sub(T, C)) if T else (0, 0, 1)
            return max(1.0, _dot(_sub(tuple(p[:3]), C), fwd))
        return float(fo) if fo is not None else zoom

    @staticmethod
    def compress(fr, vals, tol=1e-5):
        """Per-frame samples -> the fewest linear keys that reproduce them within tol."""
        if max(vals) - min(vals) <= tol:
            return [fr[0]], [vals[0]], []
        keep = [0]
        i = 0
        n = len(vals)
        while i < n - 1:
            j = i + 1
            while j + 1 < n:
                ok = True
                for m in range(i + 1, j + 1):
                    p = vals[i] + (vals[j + 1] - vals[i]) * (fr[m] - fr[i]) / (fr[j + 1] - fr[i])
                    if abs(p - vals[m]) > tol:
                        ok = False
                        break
                if not ok:
                    break
                j += 1
            keep.append(j)
            i = j
        f2 = [fr[i] for i in keep]
        v2 = [vals[i] for i in keep]
        return f2, v2, [("linear",)] * (len(f2) - 1)


def _clip(path):
    fmt = {"png": "PNGFormat", "jpg": "JpegFormat", "jpeg": "JpegFormat", "exr": "OpenEXRFormat", "tif": "TiffFormat", "tiff": "TiffFormat"}
    ext = path.rsplit(".", 1)[-1].lower()
    return _ClipVal(path, fmt.get(ext, "PNGFormat"))


class _ClipVal(tuple):
    def __new__(cls, path, fmt):
        return tuple.__new__(cls, (path, fmt))


_orig_val = _val


def _val(v):  # noqa: F811 (extends the emitter with Clip values)
    if isinstance(v, _ClipVal):
        return "Clip { Filename = %s, FormatID = %s, StartFrame = -1, LengthSetManually = true, TrimIn = 0, TrimOut = 0, " \
               "ExtendFirst = 0, ExtendLast = 0, Loop = 1, AspectMode = 0, Depth = 0, TimeCode = 0, GlobalStart = -2000000000, " \
               "GlobalEnd = 0 }" % (_q(v[0]), _q(v[1]))
    return _orig_val(v)


def _image_size(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception as e:  # noqa
        raise SceneError("NOT_FOUND", f"cannot read image size of {path}: {e}", hint="pass size: [w, h] on the image layer")


# ================================================================ public API

MASK_INPUTS = ("EffectMask", "GarbageMatte", "SolidMatte")


def mask_freezes(g):
    """[(freeze, mask tool or consumer, input)] for every constant-time TimeStretcher on a mask branch: one that wraps a *Mask tool,
    feeds a mask input directly, or serves only masks (every path downstream ends in a mask tool or mask input, e.g. a track matte's
    image chain into its BitmapMask). A freeze of an image that is also drawn (a card texture that also shapes its glass mask) is
    fine. Must be empty (lab rule: never freeze a mask branch)."""
    cons = {}
    for n, r in g.t.items():
        for iid, v in r["inputs"].items():
            if isinstance(v, Src):
                cons.setdefault(v.op, []).append((n, iid))
    out = []
    for n, r in g.t.items():
        if r["reg"] != "TimeStretcher" or isinstance(r["inputs"].get("SourceTime"), (Expr, Src)):
            continue
        src = r["inputs"].get("Input")
        if isinstance(src, Src) and src.op in g.t and g.t[src.op]["reg"].endswith("Mask"):
            out.append((n, src.op, "Input"))
        out += [(n, c, iid) for c, iid in cons.get(n, []) if iid in MASK_INPUTS]
        seen, todo, drawn, masks = {n}, [n], False, []
        while todo and not drawn:
            x = todo.pop()
            if not cons.get(x):
                drawn = True          # reaches a sink (the scene output) through image inputs only
            for c, iid in cons.get(x, []):
                if iid in MASK_INPUTS or g.t[c]["reg"].endswith("Mask"):
                    masks.append((n, c, iid))
                elif c not in seen:
                    seen.add(c)
                    todo.append(c)
        if not drawn and masks:
            out += masks[:1]
    return out


def compile_scene(desc, font_k=None, image_size=None, fonts=None, layout=True):
    c = Compiler(desc, font_k, image_size, fonts)
    c.cur_col, c.cur_y, c.col_end = 0, 0, 0
    c.run()
    bad = mask_freezes(c.g)
    if bad:  # an internal invariant: freeze() refuses mask branches, so this only fires on a compiler regression
        raise SceneError("INTERNAL", "a freeze sits on a mask branch: %s" % bad[:3],
                         hint="efficiency.freeze false builds without freezes; report the scene")
    if layout:  # house graph style: tool positions and labeled underlays (fusion_connector.layout)
        from . import layout as lay
        c.net = graph_net(c.g, [c.S])
        c.graph = lay.plan(c.net)
        for n, xy in c.graph["pos"].items():
            c.g.t[n]["pos"] = tuple(xy)
        c.g.underlays = c.graph["boxes"]
    return c


def graph_net(g, scenes=()):
    """The placeable tools of a compiled graph (modifiers have no node) and their wires, for fusion_connector.layout."""
    from .layout import Net
    net = Net(scenes)
    for n in g.order:
        if g.t[n].get("owner") is None and g.t[n]["reg"] not in ("BezierSpline", "XYPath"):
            net.add(n, g.t[n]["reg"])
    for n in list(net.reg):
        for iid, v in g.t[n]["inputs"].items():
            if isinstance(v, Src):
                net.edge(v.op, n, iid)
    return net


def graph_stats(g):
    by = {}
    mods = 0
    for n, r in g.t.items():
        by[r["reg"]] = by.get(r["reg"], 0) + 1
        if r.get("owner") is not None or r["reg"] in ("BezierSpline", "XYPath"):
            mods += 1
    return {"tools": len(g.t), "nodes": len(g.t) - mods, "modifiers": mods, "byRegId": dict(sorted(by.items(), key=lambda kv: -kv[1]))}


def plan(desc, font_k=None, image_size=None, fonts=None):
    """Offline dry run: validity, node counts, cost drivers and the efficiency decisions."""
    issues = validate(desc)
    if issues:
        return {"ok": False, "issues": issues[:60]}
    c = compile_scene(desc, font_k, image_size, fonts)
    st = graph_stats(c.g)
    tex_mp = sum(t["size"][0] * t["size"][1] for t in c.textures) / 1e6
    gen_mp = 0.0
    for n, r in c.g.t.items():
        if r["reg"] in ("Background", "sRender", "TextPlus") and r["inputs"].get("Width"):
            gen_mp += r["inputs"]["Width"] * r["inputs"]["Height"] / 1e6
    frames_culled = sum(c.dur - (e - s + 1) for s, e in c.regions.values() if e >= s) + sum(c.dur for s, e in c.regions.values() if e < s)
    passes = c.stats["renderers"] * (c.cfg["render3d"]["accumQuality"] if c.has_dof else 1)
    return {"ok": True, "scene": c.S, "size": [c.W, c.H], "fps": c.fps, "duration": c.dur, "quality": c.cfg["quality"],
            "nodes": st, "layers": len(c.layers),
            "cost": {"renderers3d": c.stats["renderers"], "blocks2_5d": c.stats["renderers2_5d"], "accumPassesPerFrame": passes,
                     "motionBlurTools": c.stats["mbMerges"], "textureHolds": c.stats["holds"], "freezes": c.stats["freezes"],
                     "batchedShapeLayers": c.stats["batched"],
                     "texture3dMegapixels": round(tex_mp, 2), "generatorCanvasMegapixels": round(gen_mp, 2),
                     "culledTools": len(c.regions), "toolFramesSkipped": frames_culled},
            "textures": sorted(c.textures, key=lambda t: -t["size"][0] * t["size"][1])[:12],
            "regions": c.regions, "decisions": list(dict.fromkeys(c.decisions)), "warnings": sorted(set(c.warnings)), "output": c.n("Out")}


# ================================================================ offline wireframe preview (layout and timing, not Fusion's render)

def _ordered(a, b):
    return [(min(a[0], b[0]), min(a[1], b[1])), (max(a[0], b[0]), max(a[1], b[1]))]


def _rrect(d, a, b, r, **kw):
    """PIL rejects tiny or inverted rounded boxes (a 3 px dot at preview scale, a size key through 0) [fusion_v2 F4]."""
    box = _ordered(a, b)
    try:
        d.rounded_rectangle(box, radius=max(0.0, min(r, (box[1][0] - box[0][0]) / 2, (box[1][1] - box[0][1]) / 2)), **kw)
    except ValueError:
        d.rectangle(box, **kw)


def preview(c, frames, width=480, path=None, cols=None):
    """Draw the resolved scene at a few frames with PIL: shapes, text (real font files when known), groups, 2D transforms,
    opacity, trims, and 3D cards projected through the camera. A layout/timing sketch before any paste; blur, DOF, glow,
    masks, mattes and motion blur are not drawn."""
    from PIL import Image, ImageDraw, ImageFont
    sc = width / float(c.W)
    tiles = []

    def rgba(col, op=1.0):
        if isinstance(col, dict):
            col = col["gradient"]["stops"][0][1]
        if isinstance(col, str) and col.startswith("$"):
            col = c.desc["controls"][col[1:]]
        r = hexrgba(col)
        return tuple(int(round(x * 255)) for x in r[:3]) + (int(round(255 * r[3] * max(0.0, min(1.0, op)))),)

    def draw_layer(L, t, k):
        """-> (RGBA image of the layer in layer px at scale k, its origin offset (layer px of the image's top-left))."""
        box = c.box(L)
        if L["type"] == "group":
            box = [0, 0] + list(c.group_size(L))
        x0, y0 = math.floor(box[0]) - 4, math.floor(box[1]) - 4
        w, h = max(2, int((box[2] - x0 + 4) * k)), max(2, int((box[3] - y0 + 4) * k))
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        P = lambda x, y: ((x - x0) * k, (y - y0) * k)  # noqa: E731
        ty = L["type"]
        if ty in ("rect", "ellipse", "solid"):
            sz = c.prop_at(L, "size", t, L.get("size") or list(c.container_size_of(L))) if ty != "solid" else (L.get("size") or c.container_size_of(L))
            gw, gh = (L.get("size") or sz)[0] / 2.0, (L.get("size") or sz)[1] / 2.0
            a, b = P(gw - sz[0] / 2, gh - sz[1] / 2), P(gw + sz[0] / 2, gh + sz[1] / 2)
            fill = L.get("color") if ty == "solid" else L.get("fill", "#FFFFFF" if not L.get("stroke") else None)
            st = L.get("stroke")
            kw = {"fill": rgba(fill) if fill is not None else None, "outline": rgba(st.get("color", "#FFFFFF")) if st else None,
                  "width": max(1, int((st or {}).get("width", 0) * k))}
            if ty == "ellipse":
                d.ellipse(_ordered(a, b), **kw)
            else:
                _rrect(d, a, b, float(L.get("radius") or 0) * k, **kw)
        elif ty == "path":
            pts = []
            raw = [c.pt(q) for q in L["points"]]
            for i in range(len(raw) - (0 if L.get("closed", True) else 1)):
                p0, p1 = raw[i], raw[(i + 1) % len(raw)]
                c1, c2 = (p0[0] + p0[4], p0[1] + p0[5]), (p1[0] + p1[2], p1[1] + p1[3])
                for j in range(12):
                    u = j / 12.0
                    pts.append(tuple(((1 - u) ** 3 * p0[q] + 3 * (1 - u) ** 2 * u * c1[q] + 3 * (1 - u) * u * u * c2[q] + u ** 3 * p1[q]) for q in (0, 1)))
            pts.append(raw[-1][:2] if not L.get("closed", True) else raw[0][:2])
            te = c.prop_at(L, "trimEnd", t, (L.get("trim") or {}).get("end", 100))
            n = max(2, int(len(pts) * float(te) / 100.0)) if L.get("trim") or "trimEnd" in (L.get("keys") or {}) else len(pts)
            xy = [P(*q) for q in pts[:n]]
            if L.get("fill") is not None and L.get("closed", True) and len(xy) > 2:
                d.polygon(xy, fill=rgba(L.get("fill", "#FFFFFF")))
            if L.get("stroke"):
                d.line(xy, fill=rgba(L["stroke"].get("color", "#FFFFFF")), width=max(1, int(L["stroke"]["width"] * k)))
        elif ty == "text":
            tx = L["text"]
            px = float(tx.get("size", 48)) * k
            f = c.fonts.files.get("%s/%s" % (tx.get("font", "Open Sans"), c.text_style(tx)))
            try:
                fp, fi = (f if isinstance(f, (list, tuple)) else [f, 0]) if f else (None, 0)
                font = ImageFont.truetype(fp, max(1, int(px)), index=fi) if fp else ImageFont.load_default()
            except OSError:
                font = ImageFont.load_default()
            lead = c.text_lead(tx) * k
            a = {"left": "ls", "center": "ms", "right": "rs"}[tx.get("align", "left")]
            vis = 1.0
            for an in L.get("animators") or []:
                st_ = float(an["start"])
                vis = max(0.0, min(1.0, (t - st_) / max(1.0, float(an.get("end", st_ + an.get("duration", 12))) - st_ + 1e-9)))
            content = tx["content"]
            if (L.get("keys") or {}).get("text"):
                content = [v for f_, v in [(k_[0], k_[1]) for k_ in L["keys"]["text"]] if f_ <= t][-1:] or [content]
                content = content[0]
            for i, line in enumerate(content.split("\n")):
                d.text(P(0, i * lead / k), line, font=font, anchor=a, fill=rgba(tx.get("color", "#FFFFFF"), 0.35 + 0.65 * vis))
        elif ty == "group":
            body = c.desc["assets"][L["use"]] if L.get("use") else L
            bg = body.get("background")
            if bg is not None:
                _rrect(d, P(0, 0), P(*c.group_size(L)), float(L.get("radius") or 0) * k, fill=rgba(bg))
            gw, gh = c.group_size(L)
            stack(im, body.get("layers") or [], t, k, P, Space(gw, gh, gw / 2.0, gh / 2.0, 1.0, gw, gh))
        return im, (x0, y0)

    def place(canvas, L, t, k, to_px, base_op):
        a, b = c.span(L)
        if not (a <= t < b):
            return
        op = c.sval(c.prop_at(L, "opacity", t, L.get("opacity", 100))) / 100.0 * base_op
        if op <= 0:
            return
        im, (x0, y0) = draw_layer(L, t, k)
        par = c.parent_chain(L)
        # affine map from layer px to canvas px through the layer (and parent) transforms
        o = c.world2d(L, t, (0, 0), par)
        ex = c.world2d(L, t, (1, 0), par)
        ey = c.world2d(L, t, (0, 1), par)
        O, X, Y = to_px(*o), to_px(*ex), to_px(*ey)
        ax, ay = X[0] - O[0], X[1] - O[1]
        bx, by = Y[0] - O[0], Y[1] - O[1]
        det = ax * by - ay * bx
        if abs(det) < 1e-12:
            return
        # canvas pixel (u, v) -> layer px (lx, ly) -> image px ((lx - x0) * k, (ly - y0) * k)
        ia, ib, ic, id_ = by / det, -bx / det, -ay / det, ax / det
        coeffs = (k * ia, k * ib, k * (-(ia * O[0] + ib * O[1]) - x0), k * ic, k * id_, k * (-(ic * O[0] + id_ * O[1]) - y0))
        layer = im.transform(canvas.size, Image.AFFINE, coeffs, resample=Image.BILINEAR)
        if op < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * op)))
        canvas.alpha_composite(layer)

    def cards3d(canvas, layers, cam, space, t, k, to_px):
        """One 3D block: its cards far to near, projected through cam in the container's px (space), onto canvas via to_px."""
        import numpy as np
        order = []
        for L in layers:
            if L["id"] in c.mattes and not L.get("visible"):
                continue
            box = c.box(L) if L["type"] != "group" else [0, 0] + list(c.group_size(L))
            q = c.card_screen(L, cam, t, space, box)
            if any(p is None for p, _ in q):
                continue
            order.append((-sum(dd for _, dd in q) / 4, L, box, q))
        for _, L, box, q in sorted(order, key=lambda r: r[0]):
            a0, b0 = c.span(L)
            op = c.sval(c.prop_at(L, "opacity", t, L.get("opacity", 100))) / 100.0
            if not (a0 <= t < b0) or op <= 0:
                continue
            kk = max(0.05, math.hypot(q[1][0][0] - q[0][0][0], q[1][0][1] - q[0][0][1]) / max(1.0, box[2] - box[0])) * k
            im, (x0, y0) = draw_layer(L, t, kk)
            dst = [to_px(*p) for p, _ in q]   # tl, tr, bl, br of the box
            src = [((box[0] - x0) * kk, (box[1] - y0) * kk), ((box[2] - x0) * kk, (box[1] - y0) * kk),
                   ((box[0] - x0) * kk, (box[3] - y0) * kk), ((box[2] - x0) * kk, (box[3] - y0) * kk)]
            A, B = [], []
            for (u, v), (x, y) in zip(dst, src):
                A += [[u, v, 1, 0, 0, 0, -x * u, -x * v], [0, 0, 0, u, v, 1, -y * u, -y * v]]
                B += [x, y]
            try:
                co = np.linalg.solve(np.array(A, float), np.array(B, float))
            except np.linalg.LinAlgError:
                continue
            layer = im.transform(canvas.size, Image.PERSPECTIVE, tuple(co), resample=Image.BILINEAR)
            if op < 1:
                layer.putalpha(layer.getchannel("A").point(lambda v, o=op: int(v * o)))
            canvas.alpha_composite(layer)

    def stack(canvas, layers, t, k, to_px, space):
        """Bottom to top in split_3d blocks, as the build composites them: a 2D layer above a 3D block covers it [open-fusion-mcp#11]."""
        for blk in c.split_3d(layers):
            if blk["kind"] == "3d":
                cards3d(canvas, blk["layers"], blk["camera"], space, t, k, to_px)
                continue
            for L in blk["layers"]:
                if L["type"] != "null" and not (L["id"] in c.mattes and not L.get("visible")):
                    place(canvas, L, t, k, to_px, 1.0)

    root = Space(c.W, c.H, c.W / 2.0, c.H / 2.0, 1.0, c.W, c.H)
    for t in frames:
        img = Image.new("RGBA", (int(c.W * sc), int(c.H * sc)), rgba(c.desc.get("background") or "#000000"))
        stack(img, c.desc["layers"], t, sc, lambda x, y: (x * sc, y * sc), root)
        dr = ImageDraw.Draw(img)
        dr.text((6, 4), "f%s" % _num(t), fill=(255, 255, 0, 255))
        sx0, sy0, sx1, sy1 = c.safe_rect(c.W, c.H)
        dr.rectangle([sx0 * sc, sy0 * sc, sx1 * sc, sy1 * sc], outline=(255, 255, 255, 60))
        tiles.append(img)
    cols = cols or min(len(tiles), 4)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * tiles[0].width + (cols - 1) * 4, rows * tiles[0].height + (rows - 1) * 4), (30, 30, 30, 255))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * (im.width + 4), (i // cols) * (im.height + 4)))
    if path:
        sheet.convert("RGB").save(path)
    return sheet


def layer_map(c, limit=None):
    items = list(c.layers.items())
    if limit and len(items) > limit:
        return {"count": len(items), "sample": dict(items[:limit])}
    return dict(items)


def from_setting(text, scene=None):
    """Stored description(s) from .setting text (setting.copy / fu_comp_export output): {scene: desc}."""
    from .luatable import LTable, parse
    root = parse(text)
    tools = root.get("Tools") if isinstance(root, LTable) else None
    out = {}
    if not isinstance(tools, LTable):
        return out
    for name, t in tools.items:
        if not isinstance(t, LTable):
            continue
        cd = t.get("CustomData")
        if isinstance(cd, LTable) and isinstance(cd.get(ROOT_KEY), str):
            d = json.loads(cd.get(ROOT_KEY))
            if scene is None or d.get("scene") == scene:
                out[d.get("scene")] = d
    return out


# ================================================================ diff / update

SETTABLE = (int, float, str)


def _static(v):
    return v is None or isinstance(v, SETTABLE) or (isinstance(v, tuple) and not isinstance(v, (Grad, Poly, _ClipVal)))


def diff(old, new):
    """Two compiled graphs (or descriptions) -> minimal tool-level ops.
    set: static input changes; keys: spline key changes (surgical); connect: wire changes on kept tools; replace: tools deleted and
    re-pasted (reg/structure/non-settable changes); add/remove; regions."""
    og = old.g if isinstance(old, Compiler) else compile_scene(old).g if isinstance(old, dict) else old
    ng = new.g if isinstance(new, Compiler) else compile_scene(new).g if isinstance(new, dict) else new
    ops = {"remove": [], "add": [], "replace": [], "set": [], "expr": [], "keys": [], "connect": [], "disconnect": []}
    replace = set()
    for n in ng.order:
        if n not in og.t:
            continue
        a, b = og.t[n], ng.t[n]
        if a["reg"] != b["reg"] or a.get("uc") != b.get("uc") or (a.get("owner") != b.get("owner")):
            replace.add(n)
            continue
        if a["reg"] == "BezierSpline":
            continue
        for iid in set(a["inputs"]) | set(b["inputs"]):
            va, vb = a["inputs"].get(iid), b["inputs"].get(iid)
            if va == vb:
                continue
            if isinstance(vb, Src) or isinstance(va, Src):
                sa = og.t.get(va.op) if isinstance(va, Src) else None
                sb = ng.t.get(vb.op) if isinstance(vb, Src) else None
                mod_a = bool(sa and sa.get("owner")) if sa else False
                mod_b = bool(sb and sb.get("owner")) if sb else False
                if mod_a or mod_b:
                    if isinstance(va, Src) and isinstance(vb, Src) and va.op == vb.op and og.t[va.op]["reg"] == ng.t[vb.op]["reg"]:
                        continue  # same modifier: its own changes are handled below
                    replace.add(n)
                elif vb is None:
                    ops["disconnect"].append([n, iid])
                elif isinstance(vb, Src):
                    ops["connect"].append([n, iid, vb.op, vb.out])
                else:
                    replace.add(n)
            elif isinstance(va, Expr) or isinstance(vb, Expr):
                if isinstance(va, Expr) and isinstance(vb, Expr) or (isinstance(vb, Expr) and _static(va)):
                    ops["expr"].append({"tool": n, "input": iid, "expression": vb.e})
                else:
                    replace.add(n)
            elif _static(va) and _static(vb) and vb is not None:
                ops["set"].append({"tool": n, "input": iid, "value": list(vb) if isinstance(vb, tuple) else vb})
            elif _static(va) and vb is None and _tsv_default(b["reg"], iid) is not None:
                ops["set"].append({"tool": n, "input": iid, "value": _tsv_default(b["reg"], iid)})
            else:
                replace.add(n)
        if a.get("custom") != b.get("custom"):
            ops.setdefault("data", []).append({"tool": n, "custom": b.get("custom")})
    # modifiers: a changed spline is rewritten in place; structure changes replace the host
    for n in ng.order:
        b = ng.t[n]
        if not b.get("owner"):
            continue
        host = _host(ng, n)
        if n not in og.t:
            replace.add(host)
            continue
        a = og.t[n]
        if a["reg"] == "BezierSpline" and a.get("keys") != b.get("keys") and any("poly" in k for k in a["keys"] + b["keys"]):
            replace.add(host)   # a keyed polyline (tapered trim) is re-pasted: write_spline writes numbers only
        elif a["reg"] == "BezierSpline" and a.get("keys") != b.get("keys"):
            ops["keys"].append({"host": b["owner"][0], "input": b["owner"][1], "spline": n, "keys": b["keys"],
                                "root": host, "path": _owner_path(ng, n)})
        elif a["reg"] != "BezierSpline" and a != b:
            replace.add(host)
    for n in og.order:
        if og.t[n].get("owner") and n not in ng.t and _host(og, n) in ng.t:
            replace.add(_host(og, n))
    replace = {r for r in replace if not ng.t[r].get("owner")}
    removed = [n for n in og.order if n not in ng.t and not og.t[n].get("owner")]
    added = [n for n in ng.order if n not in og.t and not ng.t[n].get("owner")]
    ops["remove"] = removed
    ops["replace"] = [n for n in ng.order if n in replace]
    ops["add"] = added
    skip = replace | set(added)
    for k in ("set", "expr", "connect", "disconnect", "data"):
        if k in ops:
            ops[k] = [x for x in ops[k] if (x[0] if isinstance(x, list) else x["tool"]) not in skip]
    ops["keys"] = [x for x in ops["keys"] if x["root"] not in skip]
    # wires INTO pasted tools from kept tools (the paste drops them) and FROM kept tools into pasted ones
    pasted = set(ops["replace"]) | set(added)
    paste_all = [n for n in ng.order if n in pasted or (ng.t[n].get("owner") and _host(ng, n) in pasted)]
    ops["pasteTools"] = paste_all
    rewire = []
    for n in paste_all:
        for iid, v in ng.t[n]["inputs"].items():
            if isinstance(v, Src) and v.op not in paste_all:
                rewire.append([n, iid, v.op, v.out])
    for n in ng.order:
        if n in paste_all:
            continue
        for iid, v in ng.t[n]["inputs"].items():
            if isinstance(v, Src) and v.op in paste_all and [n, iid, v.op, v.out] not in ops["connect"]:
                ops["connect"].append([n, iid, v.op, v.out])
    ops["rewire"] = rewire
    return {k: v for k, v in ops.items() if v}


def _tsv_default(reg, iid):
    """The live-harvested default of an input (for an input the new graph no longer writes)."""
    from .schema import TSV, tsv_available
    if not tsv_available():
        return None
    r = TSV.get().input_row(reg, iid)
    if not r or r["default"] in ("", None):
        return None
    d = r["default"]
    m = re.fullmatch(r"\{\s*(-?[\d.e+-]+)\s*,\s*(-?[\d.e+-]+)\s*\}", d)
    if m:
        return [float(m.group(1)), float(m.group(2))]
    try:
        return float(d)
    except ValueError:
        return d if r["type"] == "FuID" else None


def _host(g, n):
    while g.t[n].get("owner"):
        n = g.t[n]["owner"][0]
    return n


def _owner_path(g, n):
    """[(tool, input), ...] from the root host down to the spline: how to find it live (pasted modifiers are renamed)."""
    path = []
    while g.t[n].get("owner"):
        h, i = g.t[n]["owner"]
        path.insert(0, [h, i])
        n = h
    return path


def _set_path(d, path, value):
    parts = path.split(".")
    for p in parts[:-1]:
        key = int(p) if p.isdigit() and isinstance(d, list) else p
        if isinstance(d, dict) and key not in d:
            d[key] = {}
        d = d[key]
    last = parts[-1]
    key = int(last) if last.isdigit() and isinstance(d, list) else last
    if value is None and isinstance(d, dict):
        d.pop(key, None)
    else:
        d[key] = value


def _find_layer(layers, lid):
    for i, L in enumerate(layers):
        if L["id"] == lid:
            return layers, i
        if isinstance(L.get("layers"), list):
            r = _find_layer(L["layers"], lid)
            if r:
                return r
    return None


def apply_edits(desc, edits):
    """Surgical edits by layer id -> a new description (the input is not modified)."""
    d = copy.deepcopy(desc)
    containers = [d["layers"]] + [a["layers"] for a in (d.get("assets") or {}).values()]

    def find(lid):
        for c in containers:
            r = _find_layer(c, lid)
            if r:
                return r
        ids = [L["id"] for _, L in _all_layers(d)]
        s = suggest(lid, ids)
        raise SceneError("NOT_FOUND", f"no layer '{lid}'" + (f" - did you mean '{s}'?" if s else ""))
    for i, e in enumerate(edits):
        if not isinstance(e, dict):
            raise SceneError("INVALID_ARGS", f"edits[{i}] must be an object")
        if "scene" in e:
            for k, v in e["scene"].items():
                _set_path(d, k, v)
            continue
        if "remove" in e:
            lst, j = find(e["remove"])
            lst.pop(j)
            continue
        if "add" in e:
            L = e["add"]
            if e.get("into"):
                lst, j = find(e["into"])
                tgt = lst[j].setdefault("layers", [])
                tgt.insert(len(tgt) if e.get("index") is None else e["index"], L)
            elif e.get("after") or e.get("before"):
                lst, j = find(e.get("after") or e.get("before"))
                lst.insert(j + 1 if e.get("after") else j, L)
            else:
                d["layers"].append(L)
            continue
        if "layer" in e:
            lst, j = find(e["layer"])
            L = lst[j]
            for k, v in (e.get("set") or {}).items():
                _set_path(L, k, v)
            for k, v in (e.get("keys") or {}).items():
                if v is None:
                    (L.get("keys") or {}).pop(k, None)
                else:
                    L.setdefault("keys", {})[k] = v
            for k in ("in", "out"):
                if k in e:
                    L[k] = e[k]
            if "keys" in L and not L["keys"]:
                L.pop("keys")
            continue
        raise SceneError("INVALID_ARGS", f"edits[{i}]: use {{layer, set?, keys?, in?, out?}}, {{add, after?|before?|into?}}, {{remove}} or {{scene: {{...}}}}")
    return d
