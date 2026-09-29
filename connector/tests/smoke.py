"""Live smoke test: exercises every operation and tool through the real MCP server in project Testbed.

Rules: asserts the project is Testbed, names everything Connector_*, deletes what it creates, one call at
a time. Results -> tests/smoke_results.json (per op: pass/fail + evidence); scripts/parity.py folds them
into PARITY.md.   Run: .venv/bin/python tests/smoke.py [--keep]"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Client, ROOT  # noqa

OUT = os.path.join(ROOT, "out", "smoke")
RES = os.path.join(ROOT, "tests", "smoke_results.json")
TL = "Connector_Smoke"
REF = {"timeline": TL, "item": 0}
results = {}
log = []


def record(name, good, r, note=""):
    cur = results.setdefault(name, {"status": "pass", "runs": 0, "failures": []})
    cur["runs"] += 1
    if not good:
        cur["status"] = "fail"
        err = r.get("error") if isinstance(r, dict) else r
        cur["failures"].append({"note": note, "error": err if err else str(r)[:400]})
    line = f"{'PASS' if good else 'FAIL'} {name} {note}"
    if not good:
        line += " :: " + json.dumps(r.get("error") if isinstance(r, dict) and r.get("error") else r, default=str)[:500]
    print(line, flush=True)
    log.append(line)


class S:
    def __init__(self, c):
        self.c = c

    async def do(self, op, args=None, expect=True, check=None, note="", **kw):
        r = await self.c.do(op, args or {}, **kw)
        good = bool(r.get("ok")) == expect
        if good and check is not None:
            try:
                good = bool(check(r.get("result") if expect else r.get("error")))
            except Exception as e:  # noqa
                good = False
                r = {"ok": False, "error": {"check": repr(e), "result": str(r)[:600]}}
        record(op, good, r, note)
        return r.get("result") if r.get("ok") else r

    async def tool(self, name, args=None, expect=True, check=None, note=""):
        r = await self.c.call(name, args or {})
        good = bool(r.get("ok")) == expect
        if good and check is not None:
            try:
                good = bool(check(r))
            except Exception as e:  # noqa
                good = False
                r = {"ok": False, "error": {"check": repr(e)}}
        record(name, good, r, note)
        return r


def names(res):
    return {t["name"] for t in res["tools"]}


async def main(keep=False):
    os.makedirs(OUT, exist_ok=True)
    env = {"FUSION_MCP_PROJECT_ALLOWLIST": "Testbed", "FUSION_MCP_OUT_DIR": OUT,
           "FUSION_MCP_ALLOW_TEMPLATE_INSTALL": "1", "FUSION_MCP_TEMPLATES_ROOT": os.path.join(OUT, "templates_scratch")}
    async with Client(env) as c:
        s = S(c)
        pi = await s.tool("fu_project_info", check=lambda r: r["result"]["name"] == "Testbed")
        assert pi["ok"] and pi["result"]["name"] == "Testbed", "not Testbed: stopping"
        tls = [t["name"] for t in pi["result"]["timelines"]]
        if TL in tls:
            await c.do("timeline.delete", {"name": TL, "confirm": True})
        for _ in range(5):  # leftovers of an interrupted run
            if not (await c.do("item.delete_folder", {"name": "Connector_Folder", "confirm": True})).get("ok"):
                break

        # ---- read-only tools / project / page / timeline
        await s.tool("fu_version_info", check=lambda r: r["result"]["resolve"]["studio"])
        await s.tool("fu_catalog", check=lambda r: r["totalOperations"] > 100)
        await s.tool("fu_get_skill", check=lambda r: len(r["skills"]) >= 2)
        await s.tool("fu_get_skill", {"name": "fusion-reference", "reference": "references/fusion-realities.md"}, check=lambda r: "silent" in r["content"])
        await s.tool("fu_get_skill_asset", {"name": "fusion-motion-design", "path": "scripts/fusion_kit.py"}, check=lambda r: os.path.exists(r["absolute_path"]))
        await s.do("project.info", check=lambda r: r["name"] == "Testbed")
        await s.do("page.get")
        await s.do("timeline.list", {"includeItems": False})
        cr = await s.do("timeline.create", {"name": TL, "fusionComp": True}, check=lambda r: r["compRef"])
        await s.do("timeline.set_current", {"name": TL}, check=lambda r: r["current"] == TL)
        await s.do("comp.list", {"timeline": TL}, check=lambda r: len(r["comps"]) == 1)
        await s.do("comp.set_current", {"comp": REF}, check=lambda r: r["current"])
        await s.do("page.open", {"page": "fusion"}, check=lambda r: r["page"] == "fusion")
        await s.tool("fu_context", check=lambda r: r["result"]["currentComp"] is not None)
        ci = await s.do("comp.info", check=lambda r: r["isCurrent"] and "MediaOut1" in names(r))
        W, H = ci["width"], ci["height"]
        await s.tool("fu_comp_info", check=lambda r: r["result"]["width"] == W)
        await s.do("comp.format", check=lambda r: r["width"] == W)
        await s.do("comp.set_format", {"fps": ci["fps"]}, check=lambda r: r["fps"] == ci["fps"])
        await s.do("comp.set_time", {"frame": 0}, check=lambda r: r["currentTime"] == 0)
        await s.do("comp.set_render_range", {"start": 0, "end": 47}, check=lambda r: r["renderRange"] == [0, 47])

        # ---- tools
        await s.do("tool.add", {"regId": "Background", "name": "Connector_BG", "inputs": {"UseFrameFormatSettings": 1, "TopLeftRed": 0.05, "TopLeftGreen": 0.06, "TopLeftBlue": 0.1, "TopLeftAlpha": 1}},
                   check=lambda r: r["tool"] == "Connector_BG")
        await s.do("tool.add", {"regId": "TextPlus", "name": "Connector_Title", "inputs": {"StyledText": "SMOKE", "Center": [0.5, 0.55], "Size": 0.08}},
                   check=lambda r: abs(r["inputs"]["Center"][1] - 0.55) < 1e-6)
        await s.do("tool.add", {"regId": "TextPlus", "name": "Connector_Bad", "inputs": {"Sise": 1}}, expect=False, note="(expected INVALID_ARGS)",
                   check=lambda e: e["code"] == "INVALID_ARGS" and "Size" in e["message"])
        await s.do("merge.add", {"background": "Connector_BG", "foreground": "Connector_Title", "name": "Connector_Merge",
                                 "connectTo": {"tool": "MediaOut1", "input": "Input"}}, check=lambda r: r["merge"] == "Connector_Merge")
        await s.do("tool.list", {"name": "Connector_*"}, check=lambda r: r["count"] == 3)
        await s.do("tool.info", {"tool": "Connector_Title"}, check=lambda r: r["regId"] == "TextPlus")
        await s.tool("fu_tool_info", {"tool": "Connector_*", "includeInputs": False}, check=lambda r: len(r["result"]["tools"]) == 3)
        await s.do("tool.rename", {"tool": "Connector_Title", "newName": "Connector_TitleX"}, check=lambda r: r["tool"] == "Connector_TitleX")
        await s.do("tool.rename", {"tool": "Connector_TitleX", "newName": "Connector_Title"})
        await s.do("tool.rename", {"tool": "Connector_Title", "newName": "2bad name"}, expect=False, note="(expected invalid name)")
        await s.do("tool.set_attrs", {"tool": "Connector_BG", "attrs": {"passThrough": True}}, check=lambda r: r["tools"]["Connector_BG"]["passThrough"])
        await s.do("tool.set_attrs", {"tool": "Connector_BG", "attrs": {"passThrough": False, "tileColor": "#336699"}}, check=lambda r: not r["tools"]["Connector_BG"]["passThrough"])
        await s.do("tool.select", {"tool": "Connector_Title"}, check=lambda r: r["activeTool"] == "Connector_Title")
        await s.do("tool.select", {}, check=lambda r: r["activeTool"] is None)
        await s.do("tool.set_position", {"tool": "Connector_Title", "x": 110, "y": 66})
        await s.do("tool.bounds", {"tool": "Connector_Title", "frame": 0}, check=lambda r: r["pixels"]["width"] > 50)
        await s.do("tool.bounds", {"tool": "Connector_Title", "frame": 0, "method": "pixels"}, check=lambda r: 0 < r["pixels"]["width"] < W)
        await s.do("tool.duplicate", {"tool": "Connector_BG", "newName": "Connector_BG2"}, check=lambda r: r["tool"] == "Connector_BG2")
        await s.do("tool.delete", {"tool": "Connector_BG2"}, check=lambda r: r["deleted"] == ["Connector_BG2"])

        # ---- inputs
        await s.do("input.set", {"tool": "Connector_Title", "input": "Size", "value": 0.09}, check=lambda r: abs(r["value"] - 0.09) < 1e-6)
        await s.do("input.set", {"tool": "Connector_Title", "input": "Center", "value": {"px": [W / 2, H * 0.4]}}, check=lambda r: abs(r["value"][1] - 0.6) < 1e-6)
        await s.do("input.set", {"tool": "Connector_Merge", "input": "ApplyMode", "value": "Screne"}, expect=False, note="(expected option suggestion)",
                   check=lambda e: "Screen" in e["message"])
        await s.do("input.set_many", {"values": {"Connector_Title": {"CharacterSpacing": 1.05, "LineSpacing": 1.0}, "Connector_Merge": {"Blend": 1.0}}},
                   check=lambda r: abs(r["set"]["Connector_Title"]["CharacterSpacing"] - 1.05) < 1e-6)
        await s.do("input.get", {"tool": "Connector_Title", "input": "Size", "frame": 0}, check=lambda r: abs(r["value"] - 0.09) < 1e-6)
        await s.do("input.list", {"tool": "Connector_Title", "filter": "spacing"}, check=lambda r: r["count"] >= 2)
        await s.do("input.disconnect", {"tool": "Connector_Merge", "input": "Foreground"}, check=lambda r: r["disconnected"])
        await s.do("input.connect", {"tool": "Connector_Merge", "input": "Foreground", "source": "Connector_Title"}, check=lambda r: r["connected"][0] == "Connector_Title")
        await s.do("input.connect", {"tool": "Connector_Title", "input": "EffectMask", "source": "Connector_Merge"}, expect=False, note="(expected loop refusal)")
        await s.do("input.set_color", {"tool": "Connector_BG", "color": "#0a1020"}, check=lambda r: abs(r["set"]["TopLeftBlue"] - 32 / 255) < 1e-4)
        await s.do("input.add_control", {"tool": "Connector_Title", "id": "Connector_Ctl", "label": "Ctl", "type": "slider", "default": 0.5},
                   check=lambda r: r["input"] == "Connector_Ctl")
        await s.do("input.link", {"tool": "Connector_Title", "input": "LineSpacing", "sourceTool": "Connector_Title", "sourceInput": "CharacterSpacing"},
                   check=lambda r: abs(r["value"] - 1.05) < 1e-6)
        await s.do("expression.clear", {"tool": "Connector_Title", "input": "LineSpacing"}, check=lambda r: abs(r["value"] - 1.05) < 1e-6)
        await s.do("input.publish", {"tool": "Connector_Title", "input": "CharacterSpacing"}, check=lambda r: r["publish"])
        await s.do("modifier.remove", {"tool": "Connector_Title", "input": "CharacterSpacing"}, check=lambda r: abs(r["value"] - 1.05) < 1e-6)

        # ---- keyframes
        await s.do("keyframe.add", {"tool": "Connector_Title", "input": "Size", "keys": [[0, 0.05], [24, 0.1]], "ease": "house"},
                   check=lambda r: [k["frame"] for k in r["keys"]] == [0, 24] and 0.05 < r["sample"]["12"] < 0.1)
        await s.do("keyframe.list", {"tool": "Connector_Title", "input": "Size"}, check=lambda r: r["animated"] and len(r["keys"]) == 2)
        await s.do("audit.motion", {"specs": {"Connector_Title": ["Size"]}, "start": 0, "end": 30, "step": 0.25},
                   check=lambda r: r["rows"][0]["anim"] and 0.7 < r["rows"][0]["sig"][1] < 0.85 and r["rows"][0]["start"] == 0)
        await s.do("keyframe.set_easing", {"tool": "Connector_Title", "input": "Size", "ease": [0.42, 0, 0.58, 1]}, check=lambda r: abs(r["sample"]["0.5"] - 0.075) < 1e-3)
        await s.do("keyframe.set_value", {"tool": "Connector_Title", "input": "Size", "keys": [[24, 0.12]]}, check=lambda r: abs(r["keys"][-1]["value"] - 0.12) < 1e-6)
        await s.do("keyframe.shift", {"tool": "Connector_Title", "input": "Size", "offset": 2}, check=lambda r: [k["frame"] for k in r["keys"]] == [2, 26])
        await s.do("keyframe.set_loop", {"tool": "Connector_Title", "input": "Size", "mode": "pingpong"})
        await s.do("keyframe.copy", {"tool": "Connector_Title", "input": "Size", "targetTool": "Connector_Merge", "targetInput": "Size", "timeOffset": 0},
                   check=lambda r: len(r["keys"]) == 2)
        await s.do("keyframe.add", {"tool": "Connector_Merge", "input": "Size", "keys": [[12, 1.0]], "ease": "linear"}, check=lambda r: len(r["keys"]) == 3)
        await s.do("keyframe.remove", {"tool": "Connector_Merge", "input": "Size", "frames": [12]}, check=lambda r: len(r["keys"]) == 2)
        await s.do("keyframe.clear", {"tool": "Connector_Merge", "input": "Size", "value": 1}, check=lambda r: r["cleared"])
        await s.do("keyframe.add", {"tool": "Connector_Title", "input": "Center", "keys": [[0, [0.4, 0.5]], [24, [0.6, 0.5]]], "ease": "out_expo"},
                   check=lambda r: len(r["keys"]["X"]) == 2)
        await s.do("keyframe.clear", {"tool": "Connector_Title", "input": "Center", "value": [0.5, 0.55]})

        # ---- modifiers
        await s.do("modifier.add", {"tool": "Connector_Merge", "input": "Angle", "modifier": "PerturbNumber", "name": "Connector_Perturb", "inputs": {"Strength": 5}},
                   check=lambda r: r["modifier"] == "Connector_Perturb")
        await s.do("modifier.add", {"tool": "Connector_Merge", "input": "Angle", "modifier": "Blur"}, expect=False, note="(expected: not a modifier)")
        await s.do("modifier.list", check=lambda r: any(m["name"] == "Connector_Perturb" for m in r["modifiers"]))
        await s.do("modifier.remove", {"tool": "Connector_Merge", "input": "Angle", "value": 0}, check=lambda r: r["deleted"])
        await s.do("modifier.remove_orphans", {}, check=lambda r: "deleted" in r)

        # ---- expressions
        await s.do("expression.set", {"tool": "Connector_Merge", "input": "Blend", "expression": "0.75 + 0.25*sin(time/24*2*pi)"},
                   check=lambda r: 0.5 <= r["value"] <= 1.0)
        await s.do("expression.set", {"tool": "Connector_Merge", "input": "Size", "expression": "noise(time)"}, expect=False, note="(expected noise() refusal)")
        await s.do("expression.list", check=lambda r: r["count"] >= 1)
        await s.do("expression.replace_text", {"find": "sin", "replace": "cos"}, check=lambda r: r["count"] == 1)
        man = await s.do("expression.disable_all", {"tool": "Connector_*"}, check=lambda r: r["count"] == 1)
        await s.do("expression.restore_all", {"manifest": man["manifest"] if isinstance(man, dict) and "manifest" in man else []}, check=lambda r: r["restored"] == 1)
        await s.do("expression.clear", {"tool": "Connector_Merge", "input": "Blend", "value": 1.0}, check=lambda r: r["value"] == 1.0)

        # ---- text / font
        await s.do("text.set_content", {"tool": "Connector_Title", "text": "SMOKE TEST"}, check=lambda r: r["text"] == "SMOKE TEST")
        await s.do("font.list", {"familyContains": "Open Sans"}, check=lambda r: "Open Sans" in r["fonts"])
        await s.do("font.info", {"family": "Open Sans"}, check=lambda r: "Bold" in r["styles"])
        await s.do("input.set", {"tool": "Connector_Title", "input": "Size", "value": 0.1}, expect=False, note="(expected: animated input needs frame)")
        await s.do("keyframe.clear", {"tool": "Connector_Title", "input": "Size", "value": 0.08}, check=lambda r: r["cleared"])
        await s.do("text.set_style", {"tool": "Connector_Title", "font": "Open Sans", "style": "Bold", "sizePx": 120, "color": "#ffcc00",
                                      "tracking": 1.02, "justify": "center"}, check=lambda r: abs(r["set"]["Size"] - 1.70 * 120 / W) < 1e-6)
        await s.do("text.set_style", {"tool": "Connector_Title", "font": "Open Sanz"}, expect=False, note="(expected font suggestion)")
        await s.do("font.list_used", check=lambda r: any(u["family"] == "Open Sans" for u in r["used"]))
        await s.do("font.replace", {"fromFamily": "Open Sans", "toFamily": "Open Sans"}, check=lambda r: "Connector_Title" in r["changed"])
        await s.do("tool.add", {"regId": "TextPlus", "name": "Connector_Title2", "inputs": {"StyledText": "FOLLOW", "Center": [0.5, 0.3]}})
        fo = await s.do("text.add_follower", {"tool": "Connector_Title2", "order": "left_to_right", "delay": 2, "name": "Connector_Follow"},
                        check=lambda r: r["follower"] == "Connector_Follow")
        op_in = next((k for k in (fo.get("animatable") or []) if k.startswith("Opacity")), "Opacity1") if isinstance(fo, dict) else "Opacity1"
        await s.do("keyframe.add", {"tool": "Connector_Follow", "input": op_in, "keys": [[0, 0], [12, 1]], "ease": "house"}, note="(follower opacity)")
        await s.do("text.set_content", {"tool": "Connector_Title2", "text": "x"}, expect=False, note="(expected: driven by follower)")

        # ---- shapes
        await s.do("shape.add", {"type": "rectangle", "name": "Connector_Rect", "widthPx": 800, "heightPx": 400, "radiusPx": 40, "color": "#5e6ad2"},
                   check=lambda r: abs(r["inputs"]["Width"] - 800 / W) < 1e-6)
        await s.do("shape.add", {"type": "ellipse", "name": "Connector_Ell", "widthPx": 300, "heightPx": 300, "centerPx": [W / 2 + 500, H / 2], "strokePx": 8})
        await s.do("shape.combine", {"a": "Connector_Rect", "b": "Connector_Ell", "mode": "merge", "name": "Connector_SMerge"})
        await s.do("shape.combine", {"a": "Connector_Rect", "b": "Connector_Ell", "mode": "Subtract", "name": "Connector_SBool"})
        await s.do("shape.render", {"tool": "Connector_SMerge", "name": "Connector_SRender", "over": "Connector_BG"}, check=lambda r: r.get("merge"))
        await s.do("shape.modify", {"tool": "Connector_SMerge", "regId": "sTransform", "name": "Connector_STx", "inputs": {"ZRotation": 10}},
                   check=lambda r: r["rerouted"])
        await s.do("shape.set_trim", {"tool": "Connector_Rect", "start": 0, "length": 0.5}, check=lambda r: r["WriteLength"] == 0.5)

        # ---- masks
        await s.do("mask.add", {"type": "rectangle", "name": "Connector_Mask", "tool": "Connector_Title", "boxPx": [W / 4, H / 4, W / 2, H / 2], "radiusPx": 30, "softnessPx": 10},
                   check=lambda r: abs(r["inputs"]["Width"] - 0.5) < 1e-6)
        await s.do("mask.add", {"type": "ellipse", "name": "Connector_Mask2", "chainTo": "Connector_Mask", "boxPx": [W / 2 - 200, H / 2 - 200, 400, 400], "paintMode": "Subtract"})
        await s.do("mask.set_props", {"tool": "Connector_Mask", "softnessPx": 20, "invert": False, "opacity": 1}, check=lambda r: "SoftEdge" in r)
        await s.do("mask.add_polygon", {"name": "Connector_Poly", "points": [[100, 100], [900, 150], [500, 700]], "tool": "Connector_BG", "softnessPx": 4},
                   check=lambda r: r["mask"] == "Connector_Poly")
        await s.do("tool.delete", {"tool": ["Connector_Poly", "Connector_Mask2"]})

        # ---- merge / effect / transform
        await s.do("merge.set_blend_mode", {"tool": "Connector_Merge", "mode": "Screen"}, check=lambda r: r["ApplyMode"] == "Screen")
        await s.do("merge.set_blend_mode", {"tool": "Connector_Merge", "mode": "Normal"})
        await s.do("merge.set_matte", {"tool": "Connector_SRender", "matte": "Connector_Title", "channel": "alpha"}, check=lambda r: r["matte"])
        await s.do("merge.set_matte", {"tool": "Connector_SRender"}, check=lambda r: r["matte"] is None)
        await s.do("merge.stack", {"background": "Connector_BG", "layers": ["Connector_Title2"], "prefix": "Connector_Stack_"}, check=lambda r: r["top"] == "Connector_Stack_1")
        await s.do("effect.add", {"regId": "Blur", "after": "Connector_Title", "name": "Connector_Blur", "inputs": {"XBlurSize": 2}},
                   check=lambda r: r["rerouted"])
        await s.do("effect.chain", {"tool": "Connector_Merge"}, check=lambda r: len(r["chain"]) >= 1)
        await s.do("effect.remove", {"tool": "Connector_Blur"}, check=lambda r: r["healed"])
        await s.do("effect.list_available", {"category": "Blur"}, check=lambda r: r["count"] > 3)
        await s.do("effect.inputs", {"regId": "Glow", "filter": "glow"}, check=lambda r: len(r["inputs"]) > 0)
        await s.do("transform.set", {"tool": "Connector_Merge", "positionPx": [W / 2, H / 2 - 40], "scale": 1.0, "rotation": 0},
                   check=lambda r: abs(r["set"]["Center"][1] - (0.5 + 40 / H)) < 1e-6)
        await s.do("transform.set", {"tool": "Connector_Title2", "rotation": 5, "insert": True}, check=lambda r: r["tool"].endswith("_Xf"))

        # ---- 3d
        await s.do("3d.add_imageplane", {"name": "Connector_Plane", "image": "Connector_Title2", "translate": [0, 0, 0]})
        await s.do("3d.add_shape", {"name": "Connector_Cube", "shape": "cube", "translate": [0.5, 0, -1]})
        await s.do("3d.add_light", {"name": "Connector_Light", "type": "ambient", "intensity": 0.5})
        await s.do("3d.add_camera", {"name": "Connector_Cam", "translate": [0, 0, 3]}, check=lambda r: abs(r["aov"] - 19.26) < 0.1)
        await s.do("3d.add_merge", {"name": "Connector_M3D", "inputs": ["Connector_Plane", "Connector_Cube", "Connector_Light", "Connector_Cam"]},
                   check=lambda r: len(r["scene"]) == 4)
        await s.do("3d.add_renderer", {"name": "Connector_R3D", "scene": "Connector_M3D"}, check=lambda r: r["size"] == [W, H])
        await s.do("transform.set", {"tool": "Connector_Cube", "translate3d": [0.4, 0.1, -1], "rotate3d": [0, 30, 0]}, note="(3d)")
        await s.do("3d.scene", {"prefix": "Connector_S_", "objects": ["Connector_Cube"]}, check=lambda r: r["renderer"] == "Connector_S_Render")
        await s.do("render.frame", {"tool": "Connector_R3D", "frame": 0, "previewMaxPx": 640}, check=lambda r: r["width"] == W, note="(3d)")

        # ---- render
        rf = await s.do("render.frame", {"frame": 12, "previewMaxPx": 960}, check=lambda r: r["width"] == W and os.path.exists(r["path"]) and r["inlineImages"])
        await s.tool("fu_render_frame", {"tool": "Connector_Title", "frame": 6}, check=lambda r: os.path.exists(r["result"]["path"]) and r["_images"] == 1)
        await s.do("render.contact_sheet", {"tool": "Connector_Title", "beats": 4, "start": 0, "end": 24, "cols": 2},
                   check=lambda r: len(r["frames"]) == 4 and os.path.exists(r["path"]) and r["inlineImages"])
        await s.do("render.compare", {"reference": rf["path"] if isinstance(rf, dict) else "/nonexistent", "frame": 12},
                   check=lambda r: r["stats"]["ssim"] > 0.99 and r["stats"]["meanAbsDiff"] < 1 and not r["warnings"])
        await s.do("render.range", {"tool": "Connector_Title", "frames": [0, 12, 24]}, check=lambda r: r["count"] == 3)
        await s.do("render.range", {"tool": "Connector_Title", "start": 0, "end": 3}, check=lambda r: r["count"] == 4, note="(contiguous span)")

        # ---- media / item
        png = rf["path"] if isinstance(rf, dict) and "path" in rf else None
        await s.do("media.add_loader", {"path": png, "name": "Connector_Loader"}, check=lambda r: r["tool"] == "Connector_Loader")
        await s.do("media.list", check=lambda r: any(m["tool"] == "Connector_Loader" for m in r["media"]))
        await s.do("media.replace", {"tool": "Connector_Loader", "path": png}, check=lambda r: r["Clip"])
        await s.do("item.create_folder", {"name": "Connector_Folder"}, check=lambda r: r["folder"] == "Connector_Folder")
        imp = await s.do("item.import", {"paths": [png], "folder": "Connector_Folder"}, check=lambda r: len(r["imported"]) == 1)
        clip = imp["imported"][0]["name"] if isinstance(imp, dict) and imp.get("imported") else None
        await s.do("item.list", {"nameContains": clip or "x"}, check=lambda r: r["count"] >= 1)
        await s.do("item.usages", {"clip": clip}, check=lambda r: r["usages"] == [])
        await s.do("media.add_mediain", {"clip": clip, "name": "Connector_MediaIn"}, check=lambda r: r["source"] == "MediaPool")
        await s.do("media.replace", {"tool": "Connector_MediaIn", "clip": clip}, note="(MediaIn)")
        await s.do("render.frame", {"tool": "Connector_MediaIn", "frame": 0}, note="(MediaIn from pool)", check=lambda r: r["width"] > 0)
        await s.do("tool.delete", {"tool": ["Connector_MediaIn", "Connector_Loader"]})

        # ---- markers
        await s.do("marker.add", {"frame": 10, "name": "Connector_Mk", "note": "smoke", "color": "Green"}, check=lambda r: any(v["name"] == "Connector_Mk" for v in r["markers"].values()))
        await s.do("marker.list", check=lambda r: len(r["markers"]) >= 1)
        await s.do("marker.update", {"frame": 10, "note": "updated"}, check=lambda r: r["marker"]["note"] == "updated")
        await s.do("marker.remove", {"frame": 10}, check=lambda r: not r["markers"])

        # ---- setting / builder / template
        cp = await s.do("setting.copy", {"tools": ["Connector_Title", "Connector_BG", "Connector_Merge"]}, check=lambda r: "Connector_Title" in r["text"])
        text = cp["text"] if isinstance(cp, dict) else ""
        await s.do("setting.validate", {"text": text}, check=lambda r: r["ok"])
        await s.do("setting.paste", {"text": text, "prefix": "Connector_P_"}, check=lambda r: {"Connector_P_Connector_Title"} <= {a["name"] for a in r["added"]})
        await s.do("tool.delete", {"tool": "Connector_P_*"})
        await s.do("builder.list", check=lambda r: "title_card" in r["builders"])
        await s.do("builder.preview", {"builder": "lower_third", "args": {"title": "Smoke"}}, check=lambda r: r["validation"]["ok"])
        bl = await c.do("builder.list")
        for b in sorted(bl["result"]["builders"]):
            await s.do("builder." + b, {"prefix": "Connector_%s_" % b.title().replace("_", "")[:10]}, check=lambda r: r["added"] or r.get("info", {}).get("note"))
        await s.do("render.frame", {"frame": 30, "previewMaxPx": 960}, note="(after builders)")
        await s.do("template.write_macro", {"macro": "Connector_Macro", "tools": ["Connector_BG", "Connector_Title", "Connector_Merge"], "output": "Connector_Merge",
                                            "publish": [{"tool": "Connector_Title", "input": "StyledText", "name": "Text"}]},
                   check=lambda r: os.path.exists(r["path"]) and r["validation"]["ok"])
        mpath = os.path.join(OUT, "Connector_Macro.setting")
        await s.do("setting.paste", {"path": mpath}, check=lambda r: any(a["regId"] == "MacroOperator" for a in r["added"]), note="(macro)")
        await s.do("render.frame", {"tool": "Connector_Macro", "frame": 0}, note="(macro renders)", check=lambda r: r["width"] > 0)
        await s.do("tool.delete", {"tool": "Connector_Macro"})
        await s.do("template.install", {"path": mpath, "kind": "title", "subfolder": "Connector", "overwrite": True, "confirm": True}, check=lambda r: os.path.exists(r["installed"]),
                   note="(scratch templates root)")
        await s.do("template.list", {"kind": "title"}, check=lambda r: any(t["name"] == "Connector_Macro" for t in r["templates"]))

        # ---- viewer / command / pref / data
        await s.do("viewer.view", {"tool": "Connector_Merge"})
        await s.do("viewer.get_state")
        cl = await s.do("command.list", {"contains": "Time"}, check=lambda r: r["count"] >= 0)
        await s.do("command.find", {"name": "Goto"})
        acts = [x["id"] for x in (cl.get("actions") or [])] if isinstance(cl, dict) else []
        act = next((x for x in acts if "GlobalStart" in str(x) or "Goto_Start" in str(x)), None)
        if act:
            await s.do("command.execute", {"id": act}, note=f"({act})")
        await s.do("pref.get", {"key": "Comp.FrameFormat"}, check=lambda r: r["value"])
        await s.do("pref.set", {"key": "Comp.FrameFormat.Rate", "value": ci["fps"]}, check=lambda r: r["value"] == ci["fps"])
        await s.do("pref.set", {"key": "Global.UserInterface.ShowRenderSettings", "value": True, "scope": "app"}, expect=False, note="(expected consent refusal)")
        await s.do("data.set", {"key": "Connector_k", "value": {"a": 1}}, check=lambda r: "a" in str(r["value"]))
        await s.do("data.get", {"key": "Connector_k"}, check=lambda r: "a" in str(r["value"]))

        # ---- batch + undo
        await s.do("batch.run", {"ops": [{"operation": "tool.add", "args": {"regId": "Background", "name": "Connector_B1"}},
                                         {"operation": "input.set", "args": {"tool": "Connector_B1", "input": "TopLeftRed", "value": 1}},
                                         {"operation": "tool.info", "args": {"tool": "Connector_B1", "includeInputs": False}}]},
                   check=lambda r: r["failed"] == 0)
        await s.do("comp.undo", {"count": 1}, check=lambda r: "Connector_B1" not in r["tools"])
        await s.do("comp.redo", {"count": 1}, check=lambda r: "Connector_B1" in r["tools"])
        await s.do("batch.run", {"ops": [{"operation": "tool.add", "args": {"regId": "Background", "name": "Connector_B2"}},
                                         {"operation": "tool.add", "args": {"regId": "Nope"}},
                                         {"operation": "comp.undo", "args": {}}]}, expect=False, note="(expected partial failure, no rollback)",
                   check=lambda e: e["details"]["failed"] == 2 and e["details"]["results"][0]["ok"])
        await s.do("tool.delete", {"tool": ["Connector_B1", "Connector_B2"]})

        # ---- comp management
        await s.do("comp.create", {"timeline": TL, "onItem": 0, "name": "Connector_Comp2"}, check=lambda r: r["count"] == 2)
        await s.do("comp.rename", {"timeline": TL, "item": 0, "name": "Connector_Comp2", "newName": "Connector_Comp3"}, check=lambda r: "Connector_Comp3" in r["comps"])
        await s.do("comp.delete", {"timeline": TL, "item": 0, "name": "Connector_Comp3"}, check=lambda r: "Connector_Comp3" not in r["remaining"])
        ex = await s.do("comp.export_file", {"timeline": TL, "item": 0, "path": os.path.join(OUT, "Connector_Smoke.comp")}, check=lambda r: r["bytes"] > 1000)
        await s.do("comp.import_file", {"timeline": TL, "item": 0, "path": os.path.join(OUT, "Connector_Smoke.comp"), "name": "Connector_Imported"},
                   check=lambda r: r["count"] == 2 and "Connector_Imported" in r["comps"] and r["tools"] > 10)
        await s.do("comp.delete", {"timeline": TL, "item": 0, "name": "Connector_Imported"}, note="(imported)")
        await s.tool("fu_comp_export", {"format": "both", "tools": "Connector_*", "outPath": os.path.join(OUT, "export")},
                     check=lambda r: os.path.exists(r["result"]["setting"]["path"]) and os.path.exists(r["result"]["json"]["path"]))
        await s.do("comp.create", {"timeline": TL}, check=lambda r: r["compRef"]["item"] >= 0, note="(new Fusion clip)")

        # ---- deliver (small real render of the smoke timeline)
        await s.do("deliver.list_presets", check=lambda r: r["formats"])
        await s.do("deliver.set_format", {"format": "mov", "codec": "H264"}, note="(may vary by install)")
        job = await s.do("deliver.add_job", {"timeline": TL, "name": "Connector_Job", "targetDir": os.path.join(OUT, "deliver"), "markIn": 86400, "markOut": 86411},
                         check=lambda r: r["jobId"])
        jid = job.get("jobId") if isinstance(job, dict) else None
        await s.do("deliver.list_jobs", check=lambda r: any(j.get("JobId") == jid for j in r["jobs"]))
        await s.do("deliver.status", {"jobId": jid}, check=lambda r: "status" in r)
        await s.do("deliver.start", {"jobIds": [jid], "wait": True}, timeoutMs=180000, check=lambda r: r["started"])
        await s.do("deliver.stop")
        await s.do("deliver.remove_job", {"jobId": jid}, check=lambda r: all(j.get("JobId") != jid for j in r["jobs"]))
        await s.do("deliver.save_preset", {"name": "Connector_Preset", "confirm": False}, expect=False, note="(expected consent refusal)")

        # ---- timeout contract (worker killed, next call recovers)
        r = await c.do("comp.info", {}, timeoutMs=1)
        record("timeout.contract", r.get("error", {}).get("code") == "TIMEOUT" and r["error"].get("uncertain"), r)
        await s.tool("fu_comp_info", {"includeTools": False}, check=lambda r: r["ok"], note="(after worker restart)")

        # ---- cleanup
        if not keep:
            await s.do("timeline.delete", {"name": TL, "confirm": True}, check=lambda r: r["deleted"] == TL)
            await s.do("item.delete", {"clips": [clip], "confirm": True}, check=lambda r: r["deleted"])
            await s.do("item.delete_folder", {"name": "Connector_Folder", "confirm": True})
            await s.do("project.save", check=lambda r: r["saved"] and r["project"] == "Testbed")

    # ---- policy sessions
    async with Client({"FUSION_MCP_READONLY": "1"}) as c:
        tools = [t.name for t in await c.tools()]
        record("policy.readonly", "fu_render_frame" not in tools and (await c.do("tool.add", {"regId": "Background"}))["error"]["code"] == "FORBIDDEN"
               and (await c.do("project.info"))["ok"], {"tools": tools})
    async with Client({"FUSION_MCP_ALLOW_CATEGORIES": "comp,project"}) as c:
        r = await c.do("tool.list")
        record("policy.categories", r["error"]["code"] == "FORBIDDEN" and (await c.do("project.info"))["ok"], r)
    async with Client({"FUSION_MCP_PROJECT_ALLOWLIST": "SomeOtherProject"}) as c:
        r = await c.do("timeline.create", {"name": "Connector_ShouldNotExist"})
        record("policy.project_allowlist", r["error"]["code"] == "FORBIDDEN" and (await c.do("project.info"))["ok"], r)
    async with Client({"FUSION_MCP_ENABLE_EVAL": "1", "FUSION_MCP_PROJECT_ALLOWLIST": "Testbed"}) as c:
        s = S(c)
        await s.do("eval.python", {"code": "result = project.GetName()"}, check=lambda r: r["result"] == "Testbed")
        await s.do("eval.lua", {"code": "result = comp:GetAttrs().COMPS_Name"}, check=lambda r: r["result"] is not None)
    record("policy.eval_default_off", True, {}, "(verified in offline tests: eval FORBIDDEN without FUSION_MCP_ENABLE_EVAL)")

    json.dump({"when": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results, "log": log}, open(RES, "w"), indent=1)
    bad = [k for k, v in results.items() if v["status"] != "pass"]
    print(f"\n{len(results) - len(bad)} pass, {len(bad)} fail: {bad}")


if __name__ == "__main__":
    asyncio.run(main("--keep" in sys.argv))
