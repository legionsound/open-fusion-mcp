"""Use Fusion: local MCP server for DaVinci Resolve Fusion (mirror of Higgsfield's use-after-effects).

Fifteen tools: fu_get_skill, fu_get_skill_asset, fu_project_info, fu_comp_info, fu_tool_info,
fu_render_frame, fu_comp_export, fu_version_info, fu_context, fu_catalog, fu_do, and the shortcuts
fu_scene_build, fu_scene_plan, fu_batch, fu_contact_sheet (one fu_do operation each, inputSchema
generated from its params, routed through fu_do).
Every Resolve call goes through ONE worker process behind ONE lock, so parallel MCP calls never
interleave inside Resolve (the AE connector let two scripts collide into a blocking modal)."""
import asyncio
import json
import multiprocessing as mp
import os
import re
import sys
import threading
import time
import uuid

import mcp.types as types
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from . import config
from .schema import Op, P, json_schema, summarize, suggest, validate

RETRYABLE = {"TRANSPORT"}


# ---------------------------------------------------------------- envelopes

def max_chars():
    try:
        return int(os.environ.get("FUSION_MCP_MAX_RESPONSE_CHARS") or 40000)
    except ValueError:
        return 40000


def shrink(v, depth=0, items=8, chars=600):
    """Structure-preserving preview: long lists keep their first items plus a count, long strings are cut."""
    if depth > 6:
        return "..."
    if isinstance(v, dict):
        return {k: shrink(x, depth + 1, items, chars) for k, x in v.items()}
    if isinstance(v, list):
        head = [shrink(x, depth + 1, items, chars) for x in v[:items]]
        return head + ([f"... {len(v) - items} more"] if len(v) > items else [])
    if isinstance(v, str) and len(v) > chars:
        return v[:chars] + f"... ({len(v)} chars)"
    return v


def fit(env):
    """[rebuild F1/F5/F7] A response over the MCP output budget was spilled by the harness (a 2,081-tool paste echoed
    110k chars). Over FUSION_MCP_MAX_RESPONSE_CHARS (default 40000) the full JSON goes to out/responses/ and the
    response carries a shrunk preview plus the file path. -> (env, text)."""
    text = json.dumps(env, indent=1, default=str)
    limit = max_chars()
    if len(text) <= limit:
        return env, text
    d = os.path.join(config.out_dir(), "responses")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6] + ".json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    for items, chars in ((8, 600), (3, 200), (1, 80)):
        small = dict(shrink(env, 0, items, chars), truncated={"fullResponse": path, "chars": len(text),
                                                              "note": "response over the size budget: preview only; read the file (jq) for everything, or ask for less (quiet, filters, outPath)"})
        t2 = json.dumps(small, indent=1, default=str)
        if len(t2) <= limit:
            return small, t2
    small = {"ok": env.get("ok"), "truncated": {"fullResponse": path, "chars": len(text), "topLevelKeys": list(env)}}
    return small, json.dumps(small, indent=1)


def ok_result(payload):
    env, text = fit({"ok": True, **payload})
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], structuredContent=env, isError=False)


def err_result(code, message, hint=None, details=None, **extra):
    err = {"code": code, "message": message, "retryable": code in RETRYABLE}
    if hint:
        err["hint"] = hint
    if details is not None:
        err["details"] = details
    err.update({k: v for k, v in extra.items() if v})
    env, _ = fit({"ok": False, "error": err})
    err = env.get("error") or err
    details = err.get("details")
    lines = [f"[{code}] {message}"] + ([f"hint: {hint}"] if hint else []) + ([json.dumps(details, indent=1, default=str)] if details else []) + \
        ([json.dumps({"truncated": env["truncated"]})] if env.get("truncated") else [])
    return types.CallToolResult(content=[types.TextContent(type="text", text="\n".join(lines))], structuredContent=env, isError=True)


# ---------------------------------------------------------------- worker bridge

class Bridge:
    """One worker process, one call at a time. Timeout = kill the worker, report uncertain completion."""

    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.conn = None

    def _ensure(self):
        if self.proc is not None and self.proc.is_alive():
            return
        from . import worker
        ctxm = mp.get_context("spawn")
        parent, child = ctxm.Pipe()
        self.proc = ctxm.Process(target=worker.main, args=(child,), daemon=True, name="use-fusion-worker")
        self.proc.start()
        self.conn = parent

    def _kill(self):
        try:
            if self.proc is not None:
                self.proc.kill()
                self.proc.join(2)
        finally:
            self.proc = None
            self.conn = None

    def call(self, msg, timeout_s):
        from . import journal
        if msg.get("kind") == "op" and not msg.get("callId"):
            msg = dict(msg, callId=journal.new_id())   # the worker journals every step under this id [issue #1]
        with self.lock:
            self._ensure()
            t0 = time.time()
            try:
                self.conn.send(msg)
                if not self.conn.poll(timeout_s):
                    self._kill()
                    res = {"ok": False, "code": "TIMEOUT", "uncertain": True,
                           "message": f"no answer from Resolve within {timeout_s:.0f}s; the operation MAY HAVE EXECUTED (uncertain completion)",
                           "hint": "Re-read state (fu_comp_info / tool.info / fu_context) before doing anything else; do not blindly retry a mutation. "
                                   "Raise timeoutMs for long renders.", "durationMs": int((time.time() - t0) * 1000)}
                    try:   # [issue #8] an orphan on the scripting port makes every call hang, not fail: say so
                        from . import diag
                        h = diag.timeout_hint()
                        if h:
                            res["hint"] = "Scripting port problem: %s. %s" % (h, res["hint"])
                    except Exception:  # noqa: diagnostics never break the reply
                        pass
                    return with_receipt(res, msg)
                return self.conn.recv()
            except (EOFError, BrokenPipeError, OSError) as e:
                self._kill()
                return with_receipt({"ok": False, "code": "TRANSPORT", "uncertain": True,
                                     "message": f"Resolve worker died ({e}); the operation may have executed",
                                     "hint": "Re-read state before retrying. If Resolve crashed, reopen it."}, msg)

    def close(self):
        with self.lock:
            if self.conn is not None:
                try:
                    self.conn.send(None)
                except Exception:
                    pass
            self._kill()


def with_receipt(res, msg):
    """[issue #1] An uncertain reply carries the journal's receipt: what finished, what was running, what never started."""
    from . import journal
    cid = msg.get("callId")
    rec = journal.reconcile(journal.read(cid)) if cid else None
    if not rec:
        return res
    res = dict(res, details={"receipt": rec, "journal": journal.path_of(cid)})
    res["message"] += ". " + rec["summary"]
    res["hint"] = ("Before any other change, once Resolve answers: fu_do batch.recover {callId: '%s'} re-reads the comp and checks the "
                   "uncertain step against the journal; batch.rollback {callId} undoes the call's undo group and verifies the comp "
                   "(keep: true only closes an open group). Then re-run from the first unfinished step. " % cid) + res.get("hint", "")
    return res


BRIDGE = Bridge()


def _images(paths):
    import base64
    out = []
    for p in paths or []:
        try:
            with open(p, "rb") as f:
                data = f.read()
            if len(data) <= 4_000_000:
                out.append(types.ImageContent(type="image", data=base64.b64encode(data).decode("ascii"), mimeType="image/png"))
        except OSError:
            continue
    return out


def from_worker(res, extra_ok=None):
    if res.get("ok"):
        result = res.get("result")
        inline = result.pop("_inline", None) if isinstance(result, dict) else None
        if inline:
            result["inlineImages"] = inline
        payload = {"result": result, "durationMs": res.get("durationMs")}
        if res.get("context") is not None:
            payload["context"] = res["context"]
        if extra_ok:
            payload.update(extra_ok)
        r = ok_result(payload)
        if inline:
            r.content.extend(_images(inline))
        return r
    return err_result(res.get("code", "OPERATION_FAILED"), res.get("message", "unknown failure"), res.get("hint"), res.get("details"),
                      stack=res.get("stack"), notes=res.get("notes"), durationMs=res.get("durationMs"), uncertain=res.get("uncertain"))


async def worker_call(msg, timeout_ms=60000):
    msg["policy"] = config.policy()
    res = await asyncio.to_thread(BRIDGE.call, msg, timeout_ms / 1000.0)
    return from_worker(res)


# ---------------------------------------------------------------- operation gate (fu_do + batch children)

def ops():
    from .ops import OPS
    return OPS


def gate(name, args, nested=False):
    """(op, validated_args, None) or (None, None, error_dict)."""
    O = ops()
    op = O.get(name)
    if op is None:
        s = suggest(name or "", list(O))
        return None, None, {"code": "UNKNOWN_OPERATION", "message": f"unknown operation '{name}'",
                            "hint": (f"Did you mean '{s}'? " if s else "") + "fu_catalog lists operations.", "details": {"suggestion": s}}
    denial = config.deny_op(op)
    if denial:
        return None, None, {"code": "FORBIDDEN", "message": denial[0], "hint": denial[1], "details": {"operation": name, "category": op.category}}
    good, v = validate(op, args)
    if not good:
        return None, None, {"code": "INVALID_ARGS", "message": f"invalid arguments for '{name}': " + "; ".join(f"{i['path']} - {i['message']}" for i in v),
                            "hint": f"fu_catalog({{operation: '{name}'}}) has the full parameter reference.",
                            "details": {"issues": v, "expected": summarize(op.params)}}
    tsv_err = _tsv_check(op, v)
    if tsv_err:
        return None, None, {"code": "INVALID_ARGS", "message": f"invalid arguments for '{name}': {tsv_err}",
                            "hint": "IDs come from the live-harvested registry (effect.list_available / effect.inputs)."}
    if op.consent and v.get("confirm") is not True:
        return None, None, {"code": "FORBIDDEN", "message": f"'{name}' changes state beyond the comp and runs only with confirm: true",
                            "hint": "Pass confirm: true only when the user explicitly asked for this."}
    if nested and (not op.batchable or name == "batch.run"):
        return None, None, {"code": "INVALID_ARGS", "message": f"'{name}' cannot run inside batch.run", "hint": "Call it as its own fu_do."}
    return op, v, None


def _tsv_check(op, v):
    """Offline registry/input validation against the live TSV before Resolve is contacted."""
    from .schema import TSV, tsv_available
    if not tsv_available():
        return None
    tsv = TSV.get()
    if isinstance(v.get("regId"), str) and op.name in ("tool.add", "effect.add"):
        err = tsv.check_reg(v["regId"])
        if err:
            return err
        for k in (v.get("inputs") or {}):
            if v["regId"] in tsv.tools and not tsv.known_input(v["regId"], k):
                return tsv.check_input(v["regId"], k)
            e2 = tsv.check_value(v["regId"], k, v["inputs"][k]) if not (isinstance(v["inputs"][k], dict) and "px" in v["inputs"][k]) else None
            if e2:
                return e2
    if op.name == "modifier.add" and isinstance(v.get("modifier"), str) and v["modifier"] != "BezierSpline":
        return tsv.check_reg(v["modifier"], "modifier")
    return None


def load_batch_file(v):
    """batch.run {path}: the ops list from a JSON file ([...] or {ops: [...]}). -> (v, error_dict)."""
    import os
    if bool(v.get("ops") is not None) == bool(v.get("path")):
        return None, {"code": "INVALID_ARGS", "message": "batch.run needs exactly one of ops or path"}
    if v.get("path"):
        p = v["path"]
        if not os.path.isabs(p) or not os.path.isfile(p):
            return None, {"code": "NOT_FOUND", "message": f"batch file {p} not found (absolute path required)"}
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except ValueError as x:
            return None, {"code": "INVALID_ARGS", "message": f"batch file is not JSON: {x}"}
        ops_ = data.get("ops") if isinstance(data, dict) else data
        if not isinstance(ops_, list):
            return None, {"code": "INVALID_ARGS", "message": "batch file must hold a list of {operation, args} or {ops: [...]}"}
        v = {k: x for k, x in v.items() if k != "path"}
        v["ops"] = ops_
    return v, None


def lift_timeout(op, a):
    """[rebuild F4] timeoutMs is an fu_do-level param; accept it inside args too instead of rejecting the call."""
    if isinstance(a, dict) and "timeoutMs" in a and op is not None and "timeoutMs" not in {p.name for p in op.params}:
        a = dict(a)
        t = a.pop("timeoutMs")
        return a, t if isinstance(t, (int, float)) and t > 0 else None
    return a, None


async def do(args):
    name = args.get("operation")
    a = args.get("args") or {}
    a, lifted = lift_timeout(ops().get(name), a)
    op, v, e = gate(name, a)
    if e:
        return err_result(e["code"], e["message"], e.get("hint"), e.get("details"))
    timeout_ms = max(args.get("timeoutMs") or 60000, lifted or 0)
    if name == "batch.run":
        v, e = load_batch_file(v)
        if e:
            return err_result(e["code"], e["message"], e.get("hint"), e.get("details"))
        children, child_ms = [], 0
        for i, ch in enumerate(v["ops"]):
            if isinstance(ch, dict) and "op" in ch:  # {op, args} alias; both keys at once is ambiguous
                ch = None if "operation" in ch else {("operation" if k == "op" else k): x for k, x in ch.items()}
            if not isinstance(ch, dict) or not isinstance(ch.get("operation"), str):
                children.append({"operation": None, "rejected": {"code": "INVALID_ARGS", "message": f"ops[{i}] must be {{operation, args}} (or {{op, args}})"}})
                continue
            ca, clift = lift_timeout(ops().get(ch["operation"]), ch.get("args") or {})
            child_ms += clift or 0
            cop, cv, ce = gate(ch["operation"], ca, nested=True)
            children.append({"operation": ch["operation"], "args": cv} if cop else {"operation": ch["operation"], "rejected": ce})
        v = dict(v, ops=children)
        timeout_ms = max(timeout_ms, child_ms)  # children's own timeoutMs add up to the batch budget
    if args.get("dryRun"):
        return ok_result({"dryRun": True, "operation": name, "category": op.category, "readOnly": op.read, "args": v,
                          "offline": op.offline, "note": "validated and allowed by policy; nothing was sent to Resolve"})
    if op.offline:
        from .ops.base import OpError
        t0 = time.time()
        try:
            return from_worker({"ok": True, "result": op.fn(v), "durationMs": int((time.time() - t0) * 1000)}, extra_ok={"offline": True})
        except OpError as x:
            return err_result(x.code, x.message, x.hint, x.details)
        except Exception as x:  # noqa
            return err_result("OPERATION_FAILED", f"{type(x).__name__}: {x}")
    return await worker_call({"kind": "op", "name": name, "args": v, "ambient": True}, timeout_ms)


CATALOG = Op("fu_catalog", "catalog", "fu_catalog arguments", [
    P("category", "string", "One category: full params per operation. With query: search only this category."),
    P("operation", "string", "One operation's full reference (params, category, sibling operations), e.g. 'tool.delete'."),
    P("query", "string", "Keyword search over operation names and descriptions, e.g. 'delete tool': the top 10 as compact rows.")])

STOP = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "is", "it", "of", "on", "or", "the", "to", "with"}


def words(s):
    """Search tokens: lowercase alphanumeric runs ('.', '_' and case do not matter), plural 's' dropped, stop words out."""
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


def search(query, pool):
    """Deterministic ranking: a query word that is a word of the name scores 3, part of the name 2, a word of the description 1."""
    qs, hits = set(words(query)), []
    for o in pool:
        nw, flat = set(words(o.name)), re.sub(r"[^a-z0-9]", "", o.name.lower())
        s = sum(3 if w in nw else 2 if len(w) > 2 and w in flat else 0 for w in qs) + len(qs & set(words(o.desc)))
        if s:
            hits.append((-s, o.name, o))
    return [o for _, _, o in sorted(hits)]


def summary(desc, n=200):
    """First sentence ('e.g.' and 'i.e.' do not end one), cut to n chars."""
    s = re.split(r"(?<=[.!?])(?<!e\.g\.)(?<!i\.e\.)\s", desc, maxsplit=1)[0]
    return s if len(s) <= n else s[:n - 3].rstrip() + "..."


def _lookup(name, O, vis):
    op = O.get(name)
    if op is None:
        s = suggest(name, [o.name for o in vis])
        return err_result("UNKNOWN_OPERATION", f"unknown operation '{name}'",
                          (f"Did you mean '{s}'? " if s else "") + "fu_catalog({query: '<words>'}) searches names and descriptions.", {"suggestion": s})
    denial = config.deny_op(op)
    if denial:
        return err_result("FORBIDDEN", denial[0], denial[1], {"operation": name, "category": op.category})
    sc = next((t for t, o in SHORTCUTS.items() if o == name), None)
    return ok_result({"operation": op.public(), "category": op.category, **({"shortcut": sc} if sc else {}),
                      "siblings": sorted(o.name for o in vis if o.category == op.category and o is not op)})


def _find(query, cat, pool, vis):
    hits = search(query, pool)
    if not hits:
        vocab = sorted({w for o in pool for w in words(o.name)})
        fixed = " ".join(suggest(w, vocab) or w for w in words(query))
        near = [o.name for o in search(fixed, pool)[:5]]
        return err_result("NOT_FOUND", f"no operation matches '{query}'" + (f" in category '{cat}'" if cat else ""),
                          (f"Did you mean '{fixed}'? " if near else "") + "Or browse one category: fu_catalog({category}).",
                          {"suggestions": near or sorted({o.category for o in vis})})
    return ok_result({"query": query, **({"category": cat} if cat else {}), "totalMatches": len(hits),
                      "matches": [{"name": o.name, "category": o.category, "summary": summary(o.desc),
                                   "params": [p.name for p in o.params], "readOnly": o.read} for o in hits[:10]],
                      "hint": "fu_catalog({operation: '<name>'}) returns one operation's full parameter reference."})


def catalog(args):
    good, v = validate(CATALOG, args)
    if not good:
        return err_result("INVALID_ARGS", "invalid fu_catalog arguments: " + "; ".join(f"{i['path']} - {i['message']}" for i in v),
                          "fu_catalog takes category, operation or query (query may add category).", {"issues": v})
    if "operation" in v and len(v) > 1:
        return err_result("INVALID_ARGS", "operation looks up one operation and does not combine with " + " or ".join(k for k in v if k != "operation"),
                          "Pass operation alone, or query (optionally with category) to search.")
    O = ops()
    vis = [o for o in O.values() if config.deny_op(o) is None]
    if "operation" in v:
        return _lookup(v["operation"], O, vis)
    cat = v.get("category")
    if not cat and "query" not in v:
        cats = {}
        for o in vis:
            cats.setdefault(o.category, []).append(o.name)
        return ok_result({"categories": [{"category": c, "operationCount": len(n), "operations": sorted(n)} for c, n in sorted(cats.items())],
                          "totalOperations": len(vis), "policy": config.policy_summary(),
                          "hint": "fu_catalog({operation: 'tool.add'}) returns one operation's full reference; "
                                  "fu_catalog({query: 'delete tool'}) searches names and descriptions (category narrows it).",
                          "undo": "every mutating fu_do call is ONE undo event on its comp (batch.run included); comp.undo reverts it; "
                                  "comp.undo/redo run alone, never inside batch.run; batch.run with atomic: true undoes the whole batch on any failure",
                          "serialization": "calls are serialized through one Resolve worker; a timeout means uncertain completion: re-read state before retrying",
                          **({"note": "FUSION_MCP_READONLY=1: only read operations are listed"} if config.read_only() else {})})
    rows = [o for o in vis if o.category == cat] if cat else vis
    if cat and not rows:
        hidden = [o for o in O.values() if o.category == cat]
        cats = sorted({o.category for o in vis})
        if hidden:
            return err_result("FORBIDDEN", f"category '{cat}' exists but every operation in it is blocked by policy ({config.policy_summary()})",
                              config.deny_op(hidden[0])[1], {"availableCategories": cats})
        s = suggest(cat, cats)
        return err_result("UNKNOWN_CATEGORY", f"no operations in category '{cat}'", (f"Did you mean '{s}'? " if s else "") + "Available: " + ", ".join(cats))
    if "query" in v:
        return _find(v["query"], cat, rows, vis)
    return ok_result({"category": cat, "operations": [o.public() for o in sorted(rows, key=lambda o: o.name)]})


# ---------------------------------------------------------------- tools

COMP_SCHEMA = {"description": "Omit (or 'current') for the Fusion-page comp; or {timeline?, track?, item?, comp?}.",
               "anyOf": [{"type": "string"}, {"type": "object", "properties": {"timeline": {"type": "string"}, "track": {"type": "integer"},
                                                                               "item": {"type": ["integer", "string"]}, "comp": {"type": ["integer", "string"]}}}]}

RUN = {"timeoutMs": {"type": "integer", "minimum": 1, "description": "Per-call timeout (default 60000). Raise for renders and big batches."},
       "dryRun": {"type": "boolean", "description": "Validate and policy-check only; nothing reaches Resolve."}}

TOOLS = [
    dict(name="fu_get_skill", title="Fusion skills", effect="read", readonly_ok=True,
         description="Read the local Fusion skills (use-fusion for the connector and scene builder, fusion-motion-design router, fusion-reference, any fusion-* skill) without Resolve or the network. Omit name for the index; name for the entry; reference for one listed module. Long documents come back in pages of ~34k chars with nextOffset and a heading TOC; section returns one heading's section ('R8', '§16', 'Phase D'), toc lists headings only. Start with fusion-motion-design and fusion-reference/references/fusion-realities.md before building. Files are hash-verified.",
         schema={"type": "object", "properties": {"name": {"type": "string", "minLength": 1, "description": "Exact skill name from the index, e.g. fusion-motion-design."},
                                                  "reference": {"type": "string", "minLength": 1, "description": "Exact reference path listed by the skill, e.g. references/fusion-realities.md. Requires name."},
                                                  "section": {"type": "string", "minLength": 1, "description": "Heading text to return (exact, prefix or substring match, case-insensitive)."},
                                                  "offset": {"type": "integer", "minimum": 0, "description": "Char offset (into the section when section is given): the nextOffset of the previous page."},
                                                  "limit": {"type": "integer", "minimum": 1, "description": "Max chars to return (default one page, ~34k)."},
                                                  "toc": {"type": "boolean", "description": "Return only the headings with their offsets and sizes."}}}),
    dict(name="fu_get_skill_asset", title="Skill asset path", effect="read", readonly_ok=True,
         description="Locate a file bundled with a Fusion skill (scripts, components/*.setting, data TSVs) and return its absolute path after verifying its hash. Path only, never content.",
         schema={"type": "object", "required": ["name", "path"], "properties": {"name": {"type": "string", "minLength": 1}, "path": {"type": "string", "minLength": 1, "description": "e.g. components/title_card.setting"}}}),
    dict(name="fu_project_info", title="Project info", effect="read", readonly_ok=True,
         description="Current Resolve project: name, allowlist status, timelines with item counts, current timeline and page. Start here.",
         schema={"type": "object", "properties": {}}),
    dict(name="fu_comp_info", title="Comp info", effect="read", readonly_ok=True,
         description="Comp details: frame format, global/render range, current time, and every tool (reg ID, image wiring, animated/expression counts). Omit comp for the Fusion-page comp.",
         schema={"type": "object", "properties": {"comp": COMP_SCHEMA, "includeTools": {"type": "boolean"}}}),
    dict(name="fu_tool_info", title="Tool info", effect="read", readonly_ok=True,
         description="Full tool info (the ae_layer_info analog): every input with value, source, modifier, keyframes (with handles) and expression; outputs with consumers. tool = name, list, glob or 'all'.",
         schema={"type": "object", "required": ["tool"], "properties": {"comp": COMP_SCHEMA, "tool": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                                                                        "includeInputs": {"type": "boolean"}, "frame": {"type": "number"}}}),
    dict(name="fu_render_frame", title="Render frame", effect="write", readonly_ok=False,
         description="Render one frame of a tool (default: what feeds MediaOut1) to PNG through a temporary Saver; returns the full-res path + size AND the downscaled preview inline as an image, so you see the result in the same call. The eyes of the build loop: render, look, fix (render.contact_sheet for a whole motion, render.compare against a reference, audit.motion for timing/easing numbers). Resolve's 'Render completed!' modal is dismissed automatically; time and render range are restored.",
         schema={"type": "object", "properties": {"comp": COMP_SCHEMA, "tool": {"type": "string"}, "frame": {"type": "number"},
                                                  "outPath": {"type": "string", "description": "Absolute .png path."}, "previewMaxPx": {"type": "integer", "description": "Preview long edge (default 960)."},
                                                  "inline": {"type": "boolean", "description": "Return the preview as an image in this response (default true)."},
                                                  "timeoutMs": {"type": "integer", "minimum": 1}}}),
    dict(name="fu_comp_export", title="Export comp", effect="read", readonly_ok=True,
         description="Serialize a comp (or some tools) to .setting text (Fusion-native, pasteable) and/or structured JSON (inputs, wiring, keyframes, expressions). Write to outPath or return inline.",
         schema={"type": "object", "properties": {"comp": COMP_SCHEMA, "tools": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]},
                                                  "format": {"type": "string", "enum": ["setting", "json", "both"]}, "outPath": {"type": "string"}}}),
    dict(name="fu_version_info", title="Version info", effect="read", readonly_ok=True,
         description="Resolve product/version (Studio?), Fusion version, Python, fusionscript path, skills root and capabilities. Call at session start.",
         schema={"type": "object", "properties": {}}),
    dict(name="fu_context", title="Session context", effect="read", readonly_ok=True,
         description="Ambient context: project, timeline, page, current comp with tools, current clip, policy, and the live-verified Fusion rules (units, paste, keyframes, undo, timeouts). Call at session start; fu_do responses carry a lighter context.",
         schema={"type": "object", "properties": {}}),
    dict(name="fu_catalog", title="Operation catalog", effect="read", readonly_ok=True,
         description="Discover fu_do operations. No args: categories with operation names. category: full params per operation. operation: one operation's full reference with its siblings. query: keyword search over names and descriptions (top 10; category narrows it). Only operations the current policy allows are listed.",
         schema=json_schema(CATALOG.params)),
    dict(name="fu_do", title="Execute operation", effect="destructive", readonly_ok=True,
         description="Execute one operation from fu_catalog. Args are validated against its declared params before Resolve is contacted (missing, wrong type, unknown key with suggestion, enum), then against the live input TSV in Resolve. Several steps? Use ONE batch.run (one call, one undo event; read/verify children like tool.info or render.frame can ride along; atomic: true undoes it all on any failure). Each mutating call is one undo event (comp.undo reverts it). dryRun: validate only. Typed shortcuts for the most-used operations (same path, schema generated from the params): fu_scene_build, fu_scene_plan, fu_batch, fu_contact_sheet. A timeout means uncertain completion: the reply carries a receipt, and batch.recover re-reads the comp before any retry. Example: fu_do({operation: 'keyframe.add', args: {tool: 'Title', input: 'Size', keys: [[0, 0.05], [24, 0.1]], ease: 'house'}})",
         schema={"type": "object", "required": ["operation"], "properties": {
             "operation": {"type": "string", "description": "Operation name from fu_catalog, e.g. 'tool.add', 'keyframe.add', 'setting.paste'."},
             "args": {"type": "object", "additionalProperties": True, "description": "Operation arguments (see fu_catalog)."}, **RUN}}),
    # shortcuts: one fu_do operation each; inputSchema = tool_schema(), visibility = the operation's policy
    dict(name="fu_scene_build", title="Build scene", effect="destructive", operation="scene.build",
         description="Shortcut for fu_do scene.build: build a whole scene from one layer-level description (or a scene JSON path) as a native graph in one quiet paste, one undo event. Same validation, policy and dryRun as fu_do; full reference: fu_catalog({operation: 'scene.build'}), description format: fu_do scene.schema."),
    dict(name="fu_scene_plan", title="Plan scene", effect="read", operation="scene.plan",
         description="Shortcut for fu_do scene.plan: offline dry run of scene.build that validates a scene description and reports node counts, cost drivers and efficiency decisions without touching Resolve. Full reference: fu_catalog({operation: 'scene.plan'})."),
    dict(name="fu_batch", title="Batch", effect="destructive", operation="batch.run",
         description="Shortcut for fu_do batch.run: several operations ({operation or op, args} each, or a JSON file path) in one call and one undo event, each child validated and policy-checked; not transactional unless atomic: true. Full reference: fu_catalog({operation: 'batch.run'}); timeoutMs covers the whole batch."),
    dict(name="fu_contact_sheet", title="Contact sheet", effect="write", operation="render.contact_sheet",
         description="Shortcut for fu_do render.contact_sheet: render frames of a tool into one labeled grid PNG returned inline, so one look covers the whole motion (adds a temporary Saver, so it is withheld in read-only mode like fu_render_frame). Full reference: fu_catalog({operation: 'render.contact_sheet'}); raise timeoutMs for many or heavy frames."),
]
SHORTCUTS = {t["name"]: t["operation"] for t in TOOLS if "operation" in t}


def tool_schema(t):
    """A shortcut's inputSchema: its operation's params plus fu_do's timeoutMs/dryRun (an operation param of that name wins)."""
    if "operation" not in t:
        return t["schema"]
    s = json_schema(ops()[t["operation"]].params)
    s["properties"].update({k: x for k, x in RUN.items() if k not in s["properties"]})
    return s


async def handle(name, args):
    args = args or {}
    if name == "fu_catalog":
        return catalog(args)
    if name == "fu_do":
        return await do(args)
    if name in SHORTCUTS:  # exactly fu_do({operation, args, timeoutMs, dryRun})
        own = {p.name for p in ops()[SHORTCUTS[name]].params}
        top = {k: args[k] for k in RUN if k in args and k not in own}
        return await do({"operation": SHORTCUTS[name], "args": {k: x for k, x in args.items() if k not in top}, **top})
    if name in ("fu_get_skill", "fu_get_skill_asset"):
        from .skills import SkillStore
        try:
            st = SkillStore()
            if name == "fu_get_skill":
                if args.get("reference") and not args.get("name"):
                    return err_result("INVALID_ARGS", "reference requires a skill name")
                if not args.get("name"):
                    return ok_result(st.index())
                return ok_result(st.read(args["name"], args.get("reference") or "SKILL.md", section=args.get("section"),
                                         offset=args.get("offset"), limit=args.get("limit"), toc=bool(args.get("toc"))))
            return ok_result(st.resolve_file(args["name"], args["path"]))
        except KeyError as e:
            return err_result("INVALID_ARGS", str(e).strip("'\""))
        except (ValueError, PermissionError, OSError) as e:
            return err_result("IO", str(e))
    if name == "fu_project_info":
        return await worker_call({"kind": "op", "name": "project.info", "args": {}})
    if name == "fu_comp_info":
        return await worker_call({"kind": "op", "name": "comp.info", "args": args})
    if name == "fu_tool_info":
        return await worker_call({"kind": "op", "name": "tool.info", "args": args})
    if name == "fu_render_frame":
        a = {k: v for k, v in args.items() if k != "timeoutMs"}
        op, v, e = gate("render.frame", a)
        if e:
            return err_result(e["code"], e["message"], e.get("hint"), e.get("details"))
        return await worker_call({"kind": "op", "name": "render.frame", "args": v}, args.get("timeoutMs") or 120000)
    if name == "fu_comp_export":
        return await worker_call({"kind": "call", "name": "comp_export", "args": args}, 120000)
    if name == "fu_version_info":
        return await worker_call({"kind": "call", "name": "version", "args": {}})
    if name == "fu_context":
        return await worker_call({"kind": "call", "name": "context", "args": {}})
    return err_result("UNKNOWN_TOOL", f"unknown tool '{name}'")


def visible_tools():
    """Shortcuts are listed when their operation's policy allows it (as fu_catalog lists it); the rest by readonly_ok."""
    return [t for t in TOOLS if (config.deny_op(ops()[t["operation"]]) is None if "operation" in t else t["readonly_ok"] or not config.read_only())]


INSTRUCTIONS = ("Use Fusion: a fast, validated path into DaVinci Resolve Fusion. It sits beside the official DaVinci Resolve MCP "
                "(run_script: the full Resolve API) and computer use (node graph, Inspector, dialogs); combine them freely, picking "
                "whatever takes the fewest calls at the least risk for each step. Read fu_get_skill(name: fusion-motion-design) before "
                "creating or editing a comp (and fusion-reference references/fusion-realities.md, an index of three parts, before the first "
                "mutation); load only relevant references (long ones page; section: '<heading>' fetches one section). Discover operations "
                "with fu_catalog, inspect state with fu_context / fu_comp_info / fu_tool_info, act with fu_do (batch.run for multi-step "
                "work; fu_batch, fu_scene_build, fu_scene_plan and fu_contact_sheet are typed shortcuts), and verify with "
                "fu_render_frame. Skills and catalog work offline. A batch is one undo event; atomic: true undoes it all on any failure. A "
                "timeout reply carries a receipt: batch.recover re-reads the comp, batch.rollback undoes; never blindly retry.")


def build_server():
    server = Server(config.SERVER_ID, version=config.__version__, instructions=INSTRUCTIONS)

    @server.list_tools()
    async def list_tools():
        out = []
        for t in visible_tools():
            ann = {"read": types.ToolAnnotations(readOnlyHint=True), "write": types.ToolAnnotations(destructiveHint=False),
                   "destructive": types.ToolAnnotations(destructiveHint=True)}[t["effect"]]
            out.append(types.Tool(name=t["name"], title=t["title"], description=t["description"], inputSchema=tool_schema(t), annotations=ann))
        return out

    @server.call_tool(validate_input=True)
    async def call_tool(name, arguments):
        if name not in {t["name"] for t in visible_tools()} and name not in SHORTCUTS:  # a hidden shortcut gets fu_do's policy error
            return err_result("FORBIDDEN" if name in {t["name"] for t in TOOLS} else "UNKNOWN_TOOL",
                              f"tool '{name}' is not available" + (" in read-only mode" if config.read_only() else ""))
        try:
            return await handle(name, arguments)
        except Exception as e:  # a bug in this server, never a retryable Resolve hiccup
            import traceback
            return err_result("INTERNAL", f"{type(e).__name__}: {e}", stack=traceback.format_exc(limit=5))

    return server


async def main_async():
    server = build_server()
    print(f"[use-fusion] policy: {config.policy_summary()}", file=sys.stderr)
    print(f"[use-fusion] skills: {config.skills_root()}", file=sys.stderr)
    if not config.read_only():
        print("[use-fusion] WRITE ACCESS IS ON: operations can create, change and delete Fusion content. "
              "Set FUSION_MCP_READONLY=1 for inspection-only sessions.", file=sys.stderr)
    try:
        from .skills import build_manifest
        m = build_manifest()  # snapshot at start; reads verify against it (edits later need `fusion-connector skills-manifest`)
        print(f"[use-fusion] skills manifest: {len(m['skills'])} skills", file=sys.stderr)
    except Exception as e:  # noqa
        print(f"[use-fusion] skills manifest: {e}", file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (r, w):
        await server.run(r, w, InitializationOptions(server_name=config.SERVER_ID, server_version=config.__version__,
                                                    capabilities=server.get_capabilities(NotificationOptions(), {}),
                                                    instructions=INSTRUCTIONS))
    BRIDGE.close()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
