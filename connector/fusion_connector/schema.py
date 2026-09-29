"""Operation specs, argument validation (mirror of AE opschema) and the live-harvested TSV index.

The declared params are the single source of truth: fu_catalog publishes them and fu_do / batch.run
enforce them before anything reaches Resolve (missing required, wrong type, unknown key with a
spelling suggestion, enum membership)."""
import math
import os
import re
from dataclasses import dataclass, field

from . import config

TYPES = ("string", "number", "integer", "boolean", "array", "object", "any")


@dataclass
class P:
    name: str
    type: str
    desc: str
    required: bool = False
    default: object = None
    enum: tuple = None
    nullable: bool = False

    def public(self):
        d = {"name": self.name, "type": self.type, "required": self.required, "description": self.desc}
        if self.default is not None:
            d["default"] = self.default
        if self.enum:
            d["enum"] = list(self.enum)
        if self.nullable:
            d["nullable"] = True
        return d


@dataclass
class Op:
    name: str
    category: str
    desc: str
    params: list
    fn: object = None            # handler(ctx, comp, args) in the worker, or fn(args) when offline
    read: bool = False           # cannot modify the project
    comp: bool = True            # resolves args["comp"] and passes the comp to the handler
    undo: bool = True            # wrap in StartUndo/EndUndo (mutating comp ops)
    offline: bool = False        # runs in the server process, no Resolve needed
    consent: bool = False        # requires confirm: true (changes outside the comp/project)
    batchable: bool = True
    ui: bool = True              # needs a responsive Resolve UI (ui_check); False = also works while Resolve renders
    any_project: bool = False    # mutating op that does its own project check (project.load)
    extra: dict = field(default_factory=dict)

    def public(self):
        d = {"name": self.name, "description": self.desc, "readOnly": self.read,
             "params": [p.public() for p in self.params]}
        if self.offline:
            d["offline"] = True
        if self.consent:
            d["consent"] = "requires confirm: true, only on the user's explicit request"
        if not self.batchable:
            d["batchable"] = False
        if not self.ui and not self.offline:
            d["worksWhileRendering"] = True
        return d


def type_ok(t, v):
    if t == "any":
        return True
    if t == "string":
        return isinstance(v, str)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool) or (isinstance(v, float) and v.is_integer())
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
    if t == "array":
        return isinstance(v, list)
    if t == "object":
        return isinstance(v, dict)
    if "|" in t:
        return any(type_ok(x, v) for x in t.split("|"))
    return False


def describe(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number" if math.isfinite(v) else "non-finite number"
    return {str: "string", list: "array", dict: "object"}.get(type(v), type(v).__name__)


def levenshtein(a, b):
    """Optimal-string-alignment distance (a transposition counts as one edit)."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            c = a[i - 1] != b[j - 1]
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def suggest(key, candidates):
    """Nearest candidate within a length-scaled edit budget, else None."""
    best, dist = None, 10 ** 9
    for c in candidates:
        d = levenshtein(key.lower(), c.lower())
        if d < dist:
            best, dist = c, d
    if best is None:
        return None
    return best if dist <= max(1, int(max(len(key), len(best)) * 0.4)) else None


def summarize(params):
    return [f"{p.name}: {p.type} ({'required' if p.required else 'optional'})" for p in params]


def validate(op, raw):
    """(ok, value_or_issues). Defaults are NOT filled here; handlers own them."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return False, [{"path": "args", "message": f"must be an object, got {describe(raw)}"}]
    issues = []
    names = [p.name for p in op.params]
    for p in op.params:
        if p.name not in raw:
            if p.required:
                issues.append({"path": p.name, "message": f"missing required parameter ({p.type}) - {p.desc}"})
            continue
        v = raw[p.name]
        if v is None:
            if not p.nullable and p.type != "any":
                issues.append({"path": p.name, "message": f"must be {p.type}, got null - omit the key instead"})
            continue
        if not type_ok(p.type, v):
            issues.append({"path": p.name, "message": f"must be {p.type}, got {describe(v)}"})
        elif p.enum and v not in p.enum:
            s = suggest(str(v), [str(e) for e in p.enum])
            issues.append({"path": p.name, "message": f"must be one of {list(p.enum)}" + (f" - did you mean '{s}'?" if s else "")})
    for k in raw:
        if k not in names:
            s = suggest(k, names)
            issues.append({"path": k, "message": f"unknown parameter - did you mean '{s}'?" if s else
                           f"unknown parameter (this operation accepts: {', '.join(names) or 'no parameters'})"})
    return (False, issues) if issues else (True, raw)


# ---------------------------------------------------------------- live-harvested TSV index

FRAME_INPUTS = {"GlobalIn", "GlobalOut", "ProcessMode", "Width", "Height", "PixelAspect", "UseFrameFormatSettings", "Depth"}


class TSV:
    """fusion-21.1-inputs.tsv + fusion-21.1-registry.tsv (harvested live from Resolve 21.1.0.14)."""
    _cache = {}

    def __init__(self, inputs_path=None, registry_path=None):
        self.inputs_path = inputs_path or config.data_file("fusion-21.1-inputs.tsv")
        self.registry_path = registry_path or config.data_file("fusion-21.1-registry.tsv")
        self.tools, self.registry, self.common = {}, {}, set()
        with open(self.registry_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                c = line.rstrip("\n").split("\t")
                self.registry[c[0]] = {"name": c[1], "category": c[2], "kind": c[4] if len(c) > 4 else ""}
        with open(self.inputs_path, encoding="utf-8") as f:
            for line in f:
                c = line.rstrip("\n").split("\t")
                if line.startswith("# common_inputs:"):
                    self.common = set(line.split(":", 1)[1].split())
                elif line.startswith("#"):
                    continue
                elif line.startswith("@"):
                    self.tools[c[0][1:]] = {"default_name": c[1], "category": c[2],
                                            "outputs": c[3].replace("outputs=", "").split(",") if len(c) > 3 else [],
                                            "inputs": {}}
                elif len(c) > 3:
                    t = self.tools.setdefault(c[0], {"default_name": "", "category": "", "outputs": [], "inputs": {}})
                    t["inputs"].setdefault(c[1], {
                        "id": c[1], "name": c[2], "type": c[3], "control": c[4] if len(c) > 4 else "",
                        "default": c[5] if len(c) > 5 else "", "range": c[6] if len(c) > 6 else "",
                        "options": [o for o in c[7].split("|") if o] if len(c) > 7 and c[7] else []})

    @classmethod
    def get(cls):
        key = (config.data_file("fusion-21.1-inputs.tsv"), config.data_file("fusion-21.1-registry.tsv"))
        if key not in cls._cache:
            cls._cache[key] = cls(*key)
        return cls._cache[key]

    def kind(self, reg):
        if reg in ("BezierSpline",):
            return "modifier"
        r = self.registry.get(reg)
        return r["kind"] if r else None

    def is_tool(self, reg):
        return reg in self.registry or reg in self.tools

    def check_reg(self, reg, kind=None):
        """None when valid, else an error string with a suggestion."""
        if self.is_tool(reg) and (kind is None or self.kind(reg) == kind):
            return None
        pool = [r for r in self.registry if kind is None or self.registry[r]["kind"] == kind]
        # also match UI names (Text+ -> TextPlus)
        by_ui = [r for r in pool if self.registry[r]["name"].lower().replace(" ", "") == reg.lower().replace(" ", "")]
        s = by_ui[0] if by_ui else suggest(reg, pool)
        what = f"{kind} " if kind else ""
        if self.is_tool(reg) and kind:
            return f"'{reg}' is a {self.kind(reg)}, not a {kind}"
        return f"unknown {what}registry ID '{reg}'" + (f" - did you mean '{s}'?" if s else " (see fusion-21.1-registry.tsv)")

    def input_row(self, reg, iid):
        return self.tools.get(reg, {}).get("inputs", {}).get(iid)

    def known_input(self, reg, iid):
        return bool(self.input_row(reg, iid)) or iid in self.common or iid in FRAME_INPUTS

    def input_ids(self, reg):
        return list(self.tools.get(reg, {}).get("inputs", {}))

    def check_input(self, reg, iid):
        if self.known_input(reg, iid):
            return None
        s = suggest(iid, self.input_ids(reg) + sorted(self.common))
        # UI label match: HorizontalJustificationNew etc. are labelled differently
        by_label = [r["id"] for r in self.tools.get(reg, {}).get("inputs", {}).values()
                    if r["name"].lower().replace(" ", "") == iid.lower().replace(" ", "")]
        s = by_label[0] if by_label else s
        return f"{reg} has no input '{iid}' in the live TSV" + (f" - did you mean '{s}'?" if s else "")

    def check_value(self, reg, iid, v):
        """Type/option check for a static value against the TSV row. None = ok (or unknown row)."""
        r = self.input_row(reg, iid)
        if not r:
            return None
        t, ctl = r["type"], r["control"]
        if t == "Number":
            if isinstance(v, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", v or ""):
                return f"{reg}.{iid} is a Number; set color channels separately (input.set_color converts hex)"
            if not type_ok("number", v) and not isinstance(v, bool):
                opts = f" (options by index: {r['options']})" if r["options"] else ""
                return f"{reg}.{iid} is a Number ({ctl or 'value'}); got {describe(v)}{opts}"
        elif t == "FuID":
            if not isinstance(v, str):
                return f"{reg}.{iid} is a FuID ({ctl}); pass the option string, got {describe(v)}" + (
                    f" - options: {r['options']}" if r["options"] else "")
            if r["options"] and ctl in ("ComboID", "MultiButtonID") and v not in r["options"]:
                s = suggest(v, r["options"])
                return f"{reg}.{iid} option '{v}' not in {r['options']}" + (f" - did you mean '{s}'?" if s else "")
        elif t == "Point":
            if not (isinstance(v, (list, dict)) and len(v) >= 2):
                return f"{reg}.{iid} is a Point; pass [x, y] (normalized, Y up) or {{'px': [x, y]}}"
        elif t in ("Text", "Clip") and not isinstance(v, str):
            return f"{reg}.{iid} is {t}; pass a string"
        elif t in ("Image", "Mask", "DataType3D", "Material", "Particles"):
            return f"{reg}.{iid} is a {t} port; use input.connect, not input.set"
        return None


def tsv_available():
    return os.path.exists(config.data_file("fusion-21.1-inputs.tsv"))
