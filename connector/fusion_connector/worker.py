"""Resolve worker: the ONLY process that talks to Resolve. One request at a time over a Pipe.

The server serializes calls with a lock and enforces timeouts by killing this process; a killed call
may have executed (uncertain completion), which the server reports instead of retrying."""
import os
import platform
import sys
import time
import traceback

from . import config


def main(conn):
    os.dup2(2, 1)  # Resolve/Fusion prints must never reach the MCP stdio channel
    sys.stdout = sys.stderr
    from .ops.base import Ctx
    ctx = Ctx()
    while True:
        try:
            msg = conn.recv()
        except (EOFError, KeyboardInterrupt):
            break
        if msg is None:
            break
        conn.send(handle(ctx, msg))


def handle(ctx, msg):
    from .ops.base import OpError, jv
    ctx.policy = msg.get("policy") or {}
    ctx.notes = []
    t0 = time.time()
    try:
        if msg["kind"] == "op":
            result = run_op(ctx, msg["name"], msg.get("args") or {})
        else:
            result = CALLS[msg["name"]](ctx, msg.get("args") or {})
        out = {"ok": True, "result": result, "durationMs": int((time.time() - t0) * 1000)}
        if msg.get("ambient"):
            out["context"] = ctx.ambient()
        return out
    except OpError as e:
        return {"ok": False, "code": e.code, "message": e.message, "hint": e.hint, "details": jv(e.details),
                "notes": ctx.notes, "durationMs": int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa
        return {"ok": False, "code": "OPERATION_FAILED", "message": f"{type(e).__name__}: {e}",
                "stack": traceback.format_exc(limit=6), "notes": ctx.notes, "durationMs": int((time.time() - t0) * 1000)}


def ui_check(ctx):
    """A modal dialog makes basic calls return None. Dismiss Resolve's render modals (completed or failed);
    else report UI_BLOCKED."""
    from .ops.base import OpError
    from .ops.build import dismiss_modals, deliver_progress
    r = ctx.resolve
    if r.GetCurrentPage() is not None:
        return
    try:  # [rebuild F13/F17] a Deliver render makes GetCurrentPage None; say so instead of UI_BLOCKED
        p = r.GetProjectManager().GetCurrentProject()
        rendering = bool(p and p.IsRenderingInProgress())
    except Exception:  # noqa
        p, rendering = None, False
    if rendering:
        raise OpError("RENDERING", "Resolve is rendering a Deliver job; Fusion and page calls are blocked until it ends",
                      hint="deliver.status (progress, current frame, ETA) and deliver.stop work during a render; stop waits for "
                           "the in-flight frame. system.memory works too.", details=deliver_progress(ctx, p))
    n, fails = dismiss_modals(timeout=2.0, enabled=ctx.policy.get("auto_dismiss", True))
    for _ in range(15):
        if r.GetCurrentPage() is not None:
            ctx.notes.append(f"dismissed {n} 'Render completed!' modal(s) that blocked scripting")
            if fails:
                ctx.notes.append("dismissed %d 'Render did not complete!' warning(s): %s" % (len(fails), " | ".join(fails)))
            return
        time.sleep(0.2)
    raise OpError("UI_BLOCKED", "Resolve returned None for GetCurrentPage: a modal dialog (or a busy UI) is blocking scripting",
                  hint="Look at the Resolve window and close the dialog, then retry. This is not an empty project. If an interrupted "
                       "render.frame/range is still rendering, render.cancel aborts it and restores the comp.")


def run_op(ctx, name, args, in_batch=False):
    from .ops import OPS
    from .ops.base import OpError
    op = OPS[name]
    if op.offline:
        return op.fn(args)
    if op.ui:
        ui_check(ctx)
    if not op.read and not op.any_project:
        ctx.require_project_allowed()
    if not op.comp:
        return op.fn(ctx, args)
    ref = args.get("comp")
    if op.extra.get("paste") and ref not in (None, "", "current"):
        comp = ctx.make_current(ref)
    else:
        comp = ctx.comp(ref)
    group = op.undo and not op.read and not in_batch
    if group:
        comp.StartUndo("use-fusion " + name)
    try:
        return op.fn(ctx, comp, args)
    finally:
        if group:
            comp.EndUndo(op.undo is True)


def run_batch(ctx, comp, children, stop):
    """children were validated/policy-checked by the server; rejected ones carry 'rejected'."""
    from .ops.base import OpError, jv
    results, failed, stopped, inline = [], 0, False, []
    comp.StartUndo("use-fusion batch.run")
    try:
        for i, ch in enumerate(children):
            if stopped:
                results.append({"index": i, "skipped": True})
                continue
            if ch.get("rejected"):
                failed += 1
                results.append({"index": i, "ok": False, "operation": ch.get("operation"), "error": ch["rejected"]})
                stopped = stop
                continue
            try:
                res = run_op(ctx, ch["operation"], ch.get("args") or {}, in_batch=True)
                if isinstance(res, dict) and res.get("_inline"):  # [rebuild F4/W7] children's previews reach the caller
                    inline += res.pop("_inline")
                results.append({"index": i, "ok": True, "operation": ch["operation"], "result": res})
            except OpError as e:
                failed += 1
                results.append({"index": i, "ok": False, "operation": ch["operation"],
                                "error": {"code": e.code, "message": e.message, "hint": e.hint, "details": jv(e.details)}})
                stopped = stop
            except Exception as e:  # noqa
                failed += 1
                results.append({"index": i, "ok": False, "operation": ch["operation"], "error": {"code": "OPERATION_FAILED", "message": str(e)}})
                stopped = stop
    finally:
        comp.EndUndo(True)
    out = {"results": results, "count": len(results), "failed": failed}
    if inline:
        out["previews"] = inline
        out["_inline"] = inline[:8]
    if failed:
        raise OpError("OPERATION_FAILED", f"{failed} of {len(results)} batch operations failed; completed ones were NOT rolled back "
                      "(one comp.undo reverts the whole batch)", details=out,
                      hint="Inspect details.results (input order) before retrying only the failed children.")
    return out


# ---------------------------------------------------------------- non-op tool calls

RULES = [
    "Paste (.setting, builders, polygon masks, tool.duplicate) only works on the comp showing on the Fusion page; pass comp as {timeline, item} to auto-make it current.",
    "tool.add never auto-wires (SetActiveTool(None) + explicit flags + stray-merge cleanup); wire with connect/connectTo and read back.",
    "2D positions are normalized 0-1, origin bottom-left, Y up; use {px: [x, y]} or *Px params for top-left pixels.",
    "Measured units: RectangleMask W/H each vs own frame axis; EllipseMask both vs width; sShapes everything vs width; Text+ Size ~ 1.70*px/W; SoftEdge ~ 1.18*blurPx/W.",
    "Numeric Combo/MultiButton inputs take the 0-based index; ComboID/MultiButtonID take the option string (validated).",
    "SimpleExpressions: time = frame number, trig in radians, no noise(); clearing restores a static value (expression.clear).",
    "Keyframes: Number inputs via BezierSpline, Point inputs via XYPath; eases are cubic-bezier presets or [x1,y1,x2,y2]; the stray seeded key is removed and the key set asserted.",
    "Merge Background sets output size; a Merge without Background outputs nothing; foregrounds must be premultiplied.",
    "3D: write Camera3D ApertureW/ApertureH (a pasted FilmGate reads back but keeps the TV 0.792 x 0.594 aperture) and Renderer3D size explicitly (pasted default 320x240).",
    "render.frame/range render through one kept Saver per comp (FC_RenderSaver, bypassed with no input between renders), point MediaOut1 at the rendered tool for the render (comp.Render also renders MediaOut1's chain), dismiss Resolve's modal if one shows, restore everything; Render True is verified by the file. render.cancel cleans up an interrupted render.",
    "Heavy branches in the build loop: freeze while you still edit upstream (constant-SourceTime TimeStretcher, follows edits, -27 %); once a branch is locked, cache.to_disk renders it once and reads it back through a Loader (-42 % vs live, pixel-identical) but it is STALE after any edit above it: cache.status, render.* warnings and deliver.start say so; cache.refresh or cache.restore. Resolve's own Cache To Disk writes nothing from scripting.",
    "Multi-scene films: ONE culled comp on one clip (scene.build film: true, or per-scene Merges trimmed to their frames = the film ladder): 33 % faster than per-scene clips, pixel-identical. Trim at the consuming Merge, never a Renderer3D/generator (silent black frames); check with comp.lint_regions. A Dissolve or Merge at 0 still cooks its inputs; only a trim culls. Watch system.memory (grows with scenes rendered; restart between heavy phases).",
    "Bulk work: setting.paste is quiet above 50 tools (counts + sample), comp.clear wipes a comp in one call, rewireExternal reconnects pasted wires to existing tools; batch.run takes path: ops.json.",
    "Every mutating fu_do call is ONE undo event (batch.run included, no automatic rollback); comp.undo reverts it.",
    "A timeout means uncertain completion: re-read state (fu_comp_info / tool.info) before retrying a mutation.",
    "Name tools semantically (letters/digits/underscore); expressions reference tools by name.",
]


def _version(ctx, a):
    r = ctx.resolve
    f = ctx.fusion()
    from .ops.base import jv
    from .schema import tsv_available
    prod = r.GetProductName()
    return {"connector": config.__version__, "resolve": {"product": prod, "version": r.GetVersionString(), "studio": "Studio" in (prod or "")},
            "fusion": jv(f.GetVersion()), "python": platform.python_version(), "fusionscript": sys.modules.get("fusionscript") and sys.modules["fusionscript"].__file__,
            "skillsRoot": config.skills_root(), "tsv": tsv_available(),
            "capabilities": {"paste": True, "render": "kept render Saver (FC_RenderSaver)", "renderModalAutoDismiss": bool(ctx.policy.get("auto_dismiss", True)),
                             "eval": bool(ctx.policy.get("eval")),
                             "templateInstall": bool(ctx.policy.get("template_install")), "readOnly": bool(ctx.policy.get("readonly"))}}


def _context(ctx, a):
    from .ops.base import OpError
    from .ops.core import project_summary, comp_summary
    from . import sysmem
    try:
        ui_check(ctx)
    except OpError as e:
        if e.code != "RENDERING":
            raise
        return {"rendering": e.details, "memory": sysmem.brief(), "note": e.message + ". " + e.hint}
    out = {"project": project_summary(ctx), "policy": ctx.policy, "rules": RULES, "memory": sysmem.brief()}
    try:
        c = ctx.fusion().GetCurrentComp()
        out["currentComp"] = comp_summary(ctx, c, tools=True, limit=40) if c else None
    except Exception as e:  # noqa
        out["currentComp"] = {"error": str(e)}
    tl = ctx.project().GetCurrentTimeline()
    if tl:
        it = tl.GetCurrentVideoItem()
        out["currentItem"] = {"name": it.GetName(), "fusionComps": it.GetFusionCompCount()} if it else None
    return out


def _comp_export(ctx, a):
    """fu_comp_export: .setting text (Lua copy) and/or structured JSON of every tool."""
    import json
    from .ops.base import OpError
    from .ops.build import setting_copy, _out
    from .ops.core import comp_summary, tool_detail
    ui_check(ctx)
    comp = ctx.comp(a.get("comp"))
    fmt = a.get("format", "both")
    out = {"format": fmt}
    tools = a.get("tools") or "all"
    if fmt in ("setting", "both"):
        s = setting_copy(ctx, comp, {"tools": tools})
        out["setting"] = {"bytes": s["bytes"], "tools": s["tools"]}
        text = s["text"]
        if a.get("outPath"):
            p = _out(a["outPath"] if a["outPath"].endswith(".setting") else a["outPath"] + ".setting", "export.setting")
            open(p, "w", encoding="utf-8").write(text)
            out["setting"]["path"] = p
        else:
            out["setting"]["text"] = text
    if fmt in ("json", "both"):
        doc = {"comp": comp_summary(ctx, comp, tools=False),
               "tools": [tool_detail(ctx, comp, t, True) for _, t in ctx.tools_matching(comp, tools)]}
        if a.get("outPath"):
            p = _out(a["outPath"] if a["outPath"].endswith(".json") else a["outPath"] + ".json", "export.json")
            open(p, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
            out["json"] = {"path": p, "tools": len(doc["tools"])}
        else:
            out["json"] = doc
    if fmt not in ("setting", "json", "both"):
        raise OpError("INVALID_ARGS", "format must be setting, json or both")
    return out


CALLS = {"version": _version, "context": _context, "comp_export": _comp_export}
