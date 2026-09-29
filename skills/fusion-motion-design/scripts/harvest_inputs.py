"""harvest_inputs.py: refresh the live tool/input tables after a Resolve update.

Run inside the official Resolve MCP with run_script_unsafe, in a SCRATCH project only:
    exec(open(".../fusion_kit.py").read())
    exec(open(".../harvest_inputs.py").read())
    cc = make_current("Testbed", "FusionSkillLab")
    dump(cc, ["Blur", "Glow"], "/abs/out.json")                       # default mode
    dump(cc, ["Renderer3D"], "/abs/r3d_gl.json", modes={"Renderer3D": {"RendererType": "RendererOpenGL"}})
Batch 60-100 tools per call (60 s limit). Build the TSV afterwards with the same columns
as fusion-reference/data/fusion-21.1-inputs.tsv. Some inputs only exist in a mode
(Renderer3D OpenGL settings, Text+ shading elements 2-8): pass `modes` to set them first.
"""
import json

KEEP = ("INPS_ID", "INPS_Name", "INPS_DataType", "INPID_InputControl", "INPN_Default",
        "INPN_MinScale", "INPN_MaxScale", "INPN_MinAllowed", "INPN_MaxAllowed", "INPB_Integer",
        "INPS_ICS_ControlPage")


def dump_inputs(tool):
    out = []
    for inp in tool.GetInputList().values():
        a = inp.GetAttrs()
        d = {k: a[k] for k in KEEP if k in a and isinstance(a[k], (str, int, float, bool))}
        for k, v in a.items():
            if k.startswith("INPIDT_") and isinstance(v, dict) and v:
                d["options"] = [v[x] for x in sorted(v)][:40]
        if a.get("INPS_DataType") in ("Number", "Point", "Text", "FuID"):  # never GetInput on Image/3D ports
            try:
                v = tool.GetInput(a["INPS_ID"])
                if isinstance(v, dict):
                    v = [v.get(1), v.get(2)]
                if isinstance(v, (str, int, float, bool, list)):
                    d["value"] = v[:200] if isinstance(v, str) else v
            except Exception:
                pass
        out.append(d)
    outs = [o.GetAttrs().get("OUTS_ID") for o in tool.GetOutputList().values()]
    return out, outs


def dump(comp, reg_ids, path, modes=None):
    res, errs = {}, {}
    for rid in reg_ids:
        try:
            t = add(comp, rid, "HV_" + rid.replace(".", "_"))  # noqa: F821 (from fusion_kit)
        except Exception as e:
            errs[rid] = str(e)[:120]
            continue
        try:
            for k, v in (modes or {}).get(rid, {}).items():
                t.SetInput(k, v)
            ins, outs = dump_inputs(t)
            res[rid] = {"name": t.GetAttrs().get("TOOLS_Name"), "inputs": ins, "outputs": outs,
                        "mode": (modes or {}).get(rid)}
        finally:
            t.Delete()
    with open(path, "w") as f:
        json.dump({"tools": res, "errors": errs}, f)
    return {"ok": len(res), "errors": errs}
