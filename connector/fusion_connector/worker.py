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
    ctx.journal = None
    t0 = time.time()
    try:
        if msg["kind"] == "op":
            ctx.journal = open_journal(msg)
            result = run_op(ctx, msg["name"], msg.get("args") or {}, step=ctx.journal is not None and msg["name"] != "batch.run")
        else:
            result = CALLS[msg["name"]](ctx, msg.get("args") or {})
        out = {"ok": True, "result": result, "durationMs": int((time.time() - t0) * 1000)}
        if msg.get("ambient"):
            out["context"] = ctx.ambient()
        close_journal(ctx, True)
        return out
    except OpError as e:
        close_journal(ctx, False)
        return {"ok": False, "code": e.code, "message": e.message, "hint": e.hint, "details": jv(e.details),
                "notes": ctx.notes, "durationMs": int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa
        close_journal(ctx, False)
        return {"ok": False, "code": "OPERATION_FAILED", "message": f"{type(e).__name__}: {e}",
                "stack": traceback.format_exc(limit=6), "notes": ctx.notes, "durationMs": int((time.time() - t0) * 1000)}


def open_journal(msg):
    """[issue #1] A journal per op call, so a timeout or a dead worker still leaves a receipt. Never fails the call."""
    if not msg.get("callId"):
        return None
    try:
        from .journal import Journal
        a = msg.get("args") or {}
        kids = [ch.get("operation") for ch in a.get("ops") or []] if msg["name"] == "batch.run" else None
        return Journal(msg["callId"], msg["name"], comp=a.get("comp"), children=kids)
    except Exception:  # noqa: a full disk must not stop Resolve work
        return None


def close_journal(ctx, ok):
    j, ctx.journal = getattr(ctx, "journal", None), None
    if j is not None:
        try:
            j.close(ok)
        except Exception:  # noqa
            pass


def jot(ctx, fn, *a, **kw):
    """Write one journal line if there is a journal; journal trouble never breaks the operation."""
    j = getattr(ctx, "journal", None)
    if j is not None:
        try:
            return getattr(j, fn)(*a, **kw)
        except Exception:  # noqa
            return None


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


def run_op(ctx, name, args, in_batch=False, step=False):
    """step: journal this call as step 0 (a single op; batch.run journals its own steps)."""
    from .ops import OPS
    from .ops.base import OpError, jv
    op = OPS[name]
    if step:
        jot(ctx, "start", 0, name, args)
    try:
        res = _run_op(ctx, op, name, args, in_batch)
    except OpError as e:
        if step:
            jot(ctx, "end", 0, False, error={"code": e.code, "message": e.message})
        raise
    except Exception as e:  # noqa
        if step:
            jot(ctx, "end", 0, False, error={"code": "OPERATION_FAILED", "message": f"{type(e).__name__}: {e}"})
        raise
    if step:
        jot(ctx, "end", 0, True, result=jv(res) if not isinstance(res, dict) else res)
    return res


def _run_op(ctx, op, name, args, in_batch):
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
        jot(ctx, "undo", "open")
    try:
        return op.fn(ctx, comp, args)
    finally:
        if group:
            comp.EndUndo(op.undo is True)
            jot(ctx, "undo", "closed")


def run_batch(ctx, comp, children, stop, atomic=False, snapshot=None, ref=None):
    """children were validated/policy-checked by the server; rejected ones carry 'rejected'.
    atomic [issue #2]: stop at the first failure, undo the batch's undo group and verify the comp against the snapshot taken
    before the first step. snapshot: 'count' (default) or 'names' (also every tool name; atomic batches take names)."""
    from .ops import OPS
    from .ops.base import OpError, jv
    if atomic:
        bad, rejected = [], []
        for i, ch in enumerate(children):
            if ch.get("rejected"):
                rejected.append({"index": i, "operation": ch.get("operation"), "error": ch["rejected"]})
                continue
            op = OPS.get(ch.get("operation"))
            if op is None or op.read:
                continue
            if not op.comp or not op.undo or (ch.get("args") or {}).get("comp") not in (None, "", "current", ref):
                bad.append({"index": i, "operation": ch["operation"]})
        if rejected:   # it would fail at that step anyway: refuse before touching the comp
            raise OpError("INVALID_ARGS", "atomic batch refused before any change: " + "; ".join(
                "ops[%d]: %s" % (r["index"], (r["error"] or {}).get("message", "rejected")) for r in rejected),
                hint="Fix the rejected steps and send the batch again.", details={"rejected": rejected})
        if bad:
            raise OpError("INVALID_ARGS", "atomic batches can only hold changes that one comp undo reverts: "
                          + ", ".join("ops[%d] %s" % (b["index"], b["operation"]) for b in bad),
                          hint="Run timeline, project and Deliver operations (and steps on another comp) outside the atomic batch.",
                          details={"notUndoable": bad})
        stop = True
    snap = jot(ctx, "snapshot", comp, names=atomic or snapshot == "names")
    if snap is None and atomic:   # no journal: the rollback still needs its baseline
        from .journal import take_snapshot
        snap = take_snapshot(comp, names=True)
    snap = snap or {}
    results, failed, stopped, inline = [], 0, False, []
    comp.StartUndo("use-fusion batch.run")
    jot(ctx, "undo", "open")
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
            jot(ctx, "start", i, ch["operation"], ch.get("args") or {})
            try:
                res = run_op(ctx, ch["operation"], ch.get("args") or {}, in_batch=True)
                if isinstance(res, dict) and res.get("_inline"):  # [rebuild F4/W7] children's previews reach the caller
                    inline += res.pop("_inline")
                jot(ctx, "end", i, True, result=res)
                results.append({"index": i, "ok": True, "operation": ch["operation"], "result": res})
            except OpError as e:
                failed += 1
                jot(ctx, "end", i, False, error={"code": e.code, "message": e.message})
                results.append({"index": i, "ok": False, "operation": ch["operation"],
                                "error": {"code": e.code, "message": e.message, "hint": e.hint, "details": jv(e.details)}})
                stopped = stop
            except Exception as e:  # noqa
                failed += 1
                jot(ctx, "end", i, False, error={"code": "OPERATION_FAILED", "message": str(e)})
                results.append({"index": i, "ok": False, "operation": ch["operation"], "error": {"code": "OPERATION_FAILED", "message": str(e)}})
                stopped = stop
    finally:
        comp.EndUndo(True)
        jot(ctx, "undo", "closed")
    out = {"results": results, "count": len(results), "failed": failed}
    if getattr(ctx, "journal", None) is not None:
        out["callId"] = ctx.journal.id
    if inline:
        out["previews"] = inline
        out["_inline"] = inline[:8]
    if failed and atomic:
        bad_ix = next(r["index"] for r in results if r.get("ok") is False)
        created = created_names([r.get("result") for r in results if r.get("ok")])
        mutated = [r["index"] for r in results if r.get("ok") and not OPS[r["operation"]].read]
        same, ev, _ = diff_against(comp, snap)
        if mutated or not same:
            comp.Undo(1)
            rb = verify_against(comp, snap, created)
            msg = "atomic batch: step %d failed, so the whole batch was undone (%s)" % (
                bad_ix, "verified" if rb["verified"] else "NOT verified: check the comp")
            hint = ("Fix the failing step and run the batch again." if rb["verified"] else
                    "The comp does not match the snapshot taken before the batch: inspect details.rollback before going on.")
        else:   # nothing shows a change: an undo group that recorded none may not be an undo event, so Undo(1) could revert an earlier one
            rb = {"rolledBack": False, "verified": True, "evidence": ev,
                  "note": "no step finished and the tool list matches the snapshot, so nothing was undone"}
            msg = "atomic batch: step %d failed before any step finished; the tool list matches the snapshot, so nothing was undone" % bad_ix
            hint = ("If step %d set input values before it failed, check its tools with tool.info (one comp.undo reverts them). "
                    "Otherwise fix the step and run the batch again." % bad_ix)
        jot(ctx, "write", dict({"t": "rollback"}, **rb))
        out["rollback"] = rb
        raise OpError("OPERATION_FAILED", msg, details=out, hint=hint)
    if failed:
        raise OpError("OPERATION_FAILED", f"{failed} of {len(results)} batch operations failed; completed ones were NOT rolled back "
                      "(one comp.undo reverts the whole batch, or pass atomic: true)", details=out,
                      hint="Inspect details.results (input order) before retrying only the failed children.")
    return out


def created_names(results):
    """Tool names finished steps report they created (results' created/added/pasted lists, tool.add's name)."""
    out = []
    for r in results:
        if not isinstance(r, dict):
            continue
        for k in ("created", "added", "pasted"):
            v = r.get(k)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, (list, tuple)):
                out += [x for x in v if isinstance(x, str)]
    return list(dict.fromkeys(out))


def diff_against(comp, snap):
    """The comp against a journal snapshot: (same, evidence, compared). Tool count, and names when the snapshot has them."""
    tools = comp.GetToolList(False) or {}
    ev = {"toolsBefore": snap.get("tools"), "toolsNow": len(tools)}
    same = snap.get("tools") is None or len(tools) == snap["tools"]
    if "names" in snap:
        now = sorted(t.GetAttrs()["TOOLS_Name"] for t in tools.values())
        ev["added"] = sorted(set(now) - set(snap["names"]))[:20]
        ev["removed"] = sorted(set(snap["names"]) - set(now))[:20]
        same = same and not ev["added"] and not ev["removed"]
    return same, ev, snap.get("tools") is not None or "names" in snap


def verify_against(comp, snap, created):
    """Did the comp go back to the snapshot? Tool count, names when the snapshot has them, and no created tool left.
    verified is None when there was nothing to compare (no snapshot, no created names)."""
    same, ev, compared = diff_against(comp, snap)
    left = [n for n in created if comp.FindTool(n) is not None]
    if created:
        ev["createdStillThere"] = left[:20]
    return {"rolledBack": True, "verified": (same and not left) if compared or created else None, "evidence": ev}


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
    "Every mutating fu_do call is ONE undo event (batch.run included; atomic: true undoes the whole batch on any failure); comp.undo reverts it.",
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
