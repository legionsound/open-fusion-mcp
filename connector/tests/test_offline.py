"""Offline unit tests (no Resolve): arg validation, TSV checks, policy, batch gating, .setting tools,
easing math, spline writing with the stray-key rule, PNG bbox, skill manifest integrity.
Run: .venv/bin/python -m unittest tests.test_offline -v"""
import json
import math
import os
import re
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fusion_connector import config  # noqa: E402
from fusion_connector.ops import OPS  # noqa: E402
from fusion_connector.ops.base import OpError, png_bbox, png_info, color, jv  # noqa: E402
from fusion_connector.ops.build import rename_setting, validate_setting_text, wrap_macro  # noqa: E402
from fusion_connector.ops.core import ease_points, write_spline  # noqa: E402
from fusion_connector.schema import TSV, suggest, tsv_available, validate  # noqa: E402

# Tests that read the harvested Fusion data tables (not shipped; generated per machine, see
# skills/fusion-reference/data/README.md) are skipped when the tables are absent.
needs_tsv = unittest.skipUnless(tsv_available(), "Fusion data tables not generated (skills/fusion-reference/data)")
from fusion_connector import server  # noqa: E402


class Env:
    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        self.old = {k: os.environ.get(k) for k in self.kw}
        os.environ.update({k: v for k, v in self.kw.items()})

    def __exit__(self, *a):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class Validation(unittest.TestCase):
    def test_required_type_unknown(self):
        op = OPS["input.set"]
        ok, issues = validate(op, {"tool": 3, "valu": 1})
        self.assertFalse(ok)
        msgs = " ".join(i["message"] for i in issues)
        self.assertIn("missing required parameter", msgs)
        self.assertIn("must be string", msgs)
        self.assertIn("did you mean 'value'", msgs)

    def test_enum_and_null(self):
        ok, issues = validate(OPS["shape.add"], {"type": "rectangl", "name": None})
        self.assertFalse(ok)
        self.assertTrue(any("did you mean 'rectangle'" in i["message"] for i in issues))
        self.assertTrue(any("null" in i["message"] for i in issues))

    def test_union_types(self):
        self.assertTrue(validate(OPS["tool.delete"], {"tool": ["a", "b"]})[0])
        self.assertTrue(validate(OPS["tool.delete"], {"tool": "Connector_*"})[0])
        self.assertFalse(validate(OPS["tool.delete"], {"tool": 5})[0])

    def test_suggest_transposition(self):
        self.assertEqual(suggest("nmae", ["name", "regId"]), "name")
        self.assertIsNone(suggest("zzzzzz", ["name"]))

    def test_every_op_has_schema(self):
        for name, op in OPS.items():
            self.assertTrue(op.desc, name)
            self.assertEqual(len({p.name for p in op.params}), len(op.params), name)
            json.dumps(op.public())


@needs_tsv
class TsvChecks(unittest.TestCase):
    def test_registry_and_inputs(self):
        t = TSV.get()
        self.assertIsNone(t.check_reg("TextPlus"))
        self.assertIn("TextPlus", t.check_reg("Textplus"))
        self.assertIn("not a modifier", t.check_reg("Blur", "modifier"))
        self.assertIn("Size", t.check_input("TextPlus", "Sise"))
        self.assertIsNone(t.check_input("Merge", "EffectMask"))  # common input
        self.assertIn("Screen", t.check_value("Merge", "ApplyMode", "Screne"))
        self.assertIsNotNone(t.check_value("Merge", "FilterMethod", "Linear"))  # numeric combo takes index
        self.assertIn("input.connect", t.check_value("Merge", "Foreground", 1))

    def test_gate(self):
        op, v, e = server.gate("tool.add", {"regId": "Textplus"})
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertIn("TextPlus", e["message"])
        op, v, e = server.gate("modifier.add", {"tool": "a", "input": "b", "modifier": "Glow"})
        self.assertIn("not a modifier", e["message"])
        op, v, e = server.gate("keyfrme.add", {})
        self.assertEqual(e["code"], "UNKNOWN_OPERATION")
        self.assertIn("keyframe.add", e["hint"])
        op, v, e = server.gate("timeline.delete", {"name": "x", "confirm": False})
        self.assertEqual(e["code"], "FORBIDDEN")
        op, v, e = server.gate("comp.undo", {}, nested=True)
        self.assertEqual(e["code"], "INVALID_ARGS")
        op, v, e = server.gate("batch.run", {"ops": []}, nested=True)
        self.assertIsNotNone(e)


class Policy(unittest.TestCase):
    def test_readonly(self):
        with Env(FUSION_MCP_READONLY="1"):
            self.assertIsNotNone(config.deny_op(OPS["tool.add"]))
            self.assertIsNone(config.deny_op(OPS["comp.info"]))
            self.assertIsNone(config.deny_op(OPS["batch.run"]))  # children are gated individually
            self.assertIsNotNone(config.deny_op(OPS["render.frame"]))
            self.assertNotIn("fu_render_frame", [t["name"] for t in server.visible_tools()])

    def test_categories_and_eval(self):
        with Env(FUSION_MCP_ALLOW_CATEGORIES="comp, project"):
            self.assertIsNotNone(config.deny_op(OPS["tool.add"]))
            self.assertIsNone(config.deny_op(OPS["comp.info"]))
        with Env(FUSION_MCP_ENABLE_EVAL="0"):
            self.assertIsNotNone(config.deny_op(OPS["eval.python"]))
        with Env(FUSION_MCP_ENABLE_EVAL="1", FUSION_MCP_READONLY="1"):
            self.assertIsNotNone(config.deny_op(OPS["eval.lua"]))  # read-only wins
        with Env(FUSION_MCP_ALLOW_TEMPLATE_INSTALL=""):
            self.assertIsNotNone(config.deny_op(OPS["template.install"]))

    def test_policy_snapshot(self):
        with Env(FUSION_MCP_PROJECT_ALLOWLIST="Testbed, Other", FUSION_MCP_AUTO_DISMISS_RENDER_MODAL="0"):
            p = config.policy()
            self.assertEqual(p["projects"], ["Other", "Testbed"])
            self.assertFalse(p["auto_dismiss"])

    def test_catalog_hides_denied(self):
        with Env(FUSION_MCP_ENABLE_EVAL=""):
            r = server.catalog({})
            ops = [o for c in r.structuredContent["categories"] for o in c["operations"]]
            self.assertNotIn("eval.python", ops)
            self.assertEqual(server.catalog({"category": "eval"}).structuredContent["error"]["code"], "FORBIDDEN")


class Setting(unittest.TestCase):
    TEXT = ('{ Tools = ordered() { Title = TextPlus { Inputs = { StyledText = Input { Value = "Title.Size", }, '
            'Size = Input { Expression = "Ctrl.NumberIn1 * Title.Size", }, }, }, '
            'Mrg = Merge { Inputs = { Foreground = Input { SourceOp = "Title", Source = "Output", }, }, }, }, ActiveTool = "Title", }')

    def test_rename(self):
        out = rename_setting(self.TEXT, {"Title": "C_Title"})
        self.assertIn("C_Title = TextPlus {", out)
        self.assertIn('SourceOp = "C_Title"', out)
        self.assertIn('"Ctrl.NumberIn1 * C_Title.Size"', out)
        self.assertIn('ActiveTool = "C_Title"', out)
        self.assertIn('Value = "Title.Size"', out)  # plain string values are untouched

    @needs_tsv
    def test_validate(self):
        v = validate_setting_text(self.TEXT)
        self.assertTrue(v["ok"], v)
        bad = validate_setting_text('{ Tools = ordered() { A = Textplus { }, R = Renderer3D { Inputs = { }, }, } }')
        self.assertFalse(bad["ok"])
        self.assertTrue(any("320x240" in w for w in bad["warnings"]))
        self.assertFalse(validate_setting_text("{ Tools = ordered() { A = TextPlus { Inputs = { Size = Input { Expression = \"noise(time)\", }, }, }, } }")["ok"])

    @needs_tsv
    def test_wrap_macro(self):
        m = wrap_macro(self.TEXT, "Connector_M", [{"tool": "Title", "input": "StyledText", "name": "Text"}], "Mrg")
        v = validate_setting_text(m)
        self.assertTrue(v["ok"], v)
        self.assertEqual([t["regId"] for t in v["tools"]][0], "MacroOperator")
        self.assertIn('MainOutput1 = InstanceOutput { SourceOp = "Mrg"', m)

    @needs_tsv
    def test_builder_preview_validates(self):
        r = OPS["builder.preview"].fn({"builder": "title_card", "args": {"title": "Hi"}})
        self.assertTrue(r["validation"]["ok"], r["validation"])


class FakeSpline:
    """Mimics the live quirk: SetKeyFrames(replace) never removes a key sitting at `sticky`."""

    def __init__(self, sticky=0.0):
        self.keys = {sticky: {1: 0.0}}
        self.sticky = sticky
        self.data = {}

    def SetKeyFrames(self, kf, replace):
        keep = {k: v for k, v in self.keys.items() if k == self.sticky} if replace else dict(self.keys)
        keep.update({float(k): v for k, v in kf.items()})
        self.keys = keep

    def GetKeyFrames(self):
        return dict(self.keys)

    def DeleteKeyFrames(self, f, end=None):
        self.keys.pop(float(f), None)


class FakeComp:
    CurrentTime = 0.0


class Keyframes(unittest.TestCase):
    def test_ease_points(self):
        self.assertEqual(ease_points("linear", 24, 1, 24), ("linear",))
        self.assertEqual(ease_points("hold", 24, 1, 24), ("hold",))
        e = ease_points([0.42, 0, 0.58, 1], 24, 1, 24)
        self.assertEqual(e[0], "bezier")
        ae = ease_points({"outInfluence": 50, "outSpeed": 0, "inInfluence": 50, "inSpeed": 0}, 24, 1, 24)
        self.assertEqual(ae, ("bezier", 0.5, 0.0, 0.5, 1.0))
        with self.assertRaises(OpError):
            ease_points("hosue", 24, 1, 24)
        with self.assertRaises(OpError):
            ease_points([1.5, 0, 0, 1], 24, 1, 24)

    def test_write_spline_relative_handles_and_stray_key(self):
        sp = FakeSpline(sticky=0.0)
        kf = write_spline(FakeComp(), sp, [(2.0, 0.0), (26.0, 1.0)], [("bezier", 0.25, 0.1, 0.25, 1.0)])
        self.assertEqual(sorted(sp.keys), [2.0, 26.0])  # stray key at 0 removed
        self.assertEqual(kf[2.0]["RH"], {1: 6.0, 2: 0.1})
        self.assertEqual(kf[26.0]["LH"], {1: -18.0, 2: 0.0})

    def test_hold_and_loop_flags(self):
        sp = FakeSpline(sticky=-1.0)
        sp.keys = {}
        kf = write_spline(FakeComp(), sp, [(0.0, 0.0), (10.0, 1.0)], [("hold",)], loop="pingpong")
        self.assertTrue(kf[0.0]["Flags"]["StepIn"] and kf[0.0]["Flags"]["PingPong"])


def _png(path, w, h, box):
    """8-bit RGBA PNG, transparent except an opaque box (x0, y0, x1, y1)."""
    raw = b""
    for y in range(h):
        raw += b"\x00" + b"".join((b"\xff\x00\x00\xff" if box[0] <= x <= box[2] and box[1] <= y <= box[3] else b"\x00\x00\x00\x00") for x in range(w))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) +
                           chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class Pixels(unittest.TestCase):
    def test_png_bbox(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "t.png")
        _png(p, 64, 32, (10, 5, 20, 12))
        b = png_bbox(p)
        self.assertEqual((b["x"], b["y"], b["width"], b["height"]), (10, 5, 11, 8))
        _png(p, 16, 16, (99, 99, 99, 99))
        self.assertIsNone(png_bbox(p))

    def test_color_and_jv(self):
        self.assertEqual(color("#ff0000"), [1.0, 0.0, 0.0, 1.0])
        self.assertEqual(color({"r": 0.5, "g": 0, "b": 0}), [0.5, 0.0, 0.0, 1])
        self.assertEqual(jv({1: 0.3, 2: 0.7, 3: 0.0}), [0.3, 0.7, 0.0])
        self.assertEqual(jv({"a": {1.0: 2}}), {"a": [2]})


class Skills(unittest.TestCase):
    def test_manifest_integrity(self):
        from fusion_connector import skills
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "fusion-x", "references"))
        open(os.path.join(root, "fusion-x", "SKILL.md"), "w").write("---\nname: fusion-x\ndescription: test skill\n---\nbody\n")
        open(os.path.join(root, "fusion-x", "references", "a.md"), "w").write("A")
        open(os.path.join(root, "fusion-x", "tool.py"), "w").write("x=1")
        os.makedirs(os.path.join(root, "other"))
        os.makedirs(os.path.join(root, "use-fusion"))                 # the connector's entry skill is served too [fusion_v2 F1]
        open(os.path.join(root, "use-fusion", "SKILL.md"), "w").write("---\nname: use-fusion\ndescription: entry\n---\nscene builder\n")
        man = os.path.join(root, "m.json")
        with Env(FUSION_MCP_SKILLS_ROOT=root):
            skills.build_manifest(root, man)
            st = skills.SkillStore(man)
            self.assertEqual([s["name"] for s in st.index()["skills"]], ["fusion-x", "use-fusion"])
            self.assertEqual(st.read("use-fusion")["content"].strip().splitlines()[-1], "scene builder")
            self.assertEqual(st.read("fusion-x", "references/a.md")["content"], "A")
            self.assertTrue(st.resolve_file("fusion-x", "tool.py")["absolute_path"].endswith("tool.py"))
            open(os.path.join(root, "fusion-x", "references", "a.md"), "w").write("B")
            with self.assertRaises(ValueError):
                st.read("fusion-x", "references/a.md")
            with self.assertRaises(KeyError):
                st.read("fusion-y")



class RenderModalParse(unittest.TestCase):
    def _run(self, stdout, **kw):
        import fusion_connector.ops.build as b

        class R:
            pass
        R.stdout = stdout
        orig = b.subprocess.run
        b.subprocess.run = lambda *a, **k: R
        try:
            return b.dismiss_modals(timeout=0.3, **kw)
        finally:
            b.subprocess.run = orig

    def test_completed_and_failed(self):
        n, fails = self._run("1|1|WARNING! Render did not complete! Last frame successfully rendered: (none) ;; ")
        self.assertEqual(n, 1)
        self.assertEqual(len(fails), 1)
        self.assertIn("did not complete", fails[0])

    def test_nothing_up(self):
        self.assertEqual(self._run("0|0|", expect=False), (0, []))

    def test_disabled(self):
        self.assertEqual(self._run("1|0|", enabled=False), (0, []))


class SettingLexGuard(unittest.TestCase):
    @needs_tsv
    def test_raw_newline_rejected(self):
        bad = '{ Tools = ordered() { T = TextPlus { Inputs = { StyledText = Input { Value = "a\nb", }, }, }, } }'
        r = validate_setting_text(bad)
        self.assertFalse(r["ok"])
        self.assertIn("raw newline", r["problems"][0])

    def test_escaped_and_long_strings_ok(self):
        from fusion_connector.ops.build import setting_syntax_problems
        self.assertEqual(setting_syntax_problems('{ A = "a\\nb", B = [[x\ny]], --[[ c\nd ]] C = "q\\"x" }'), [])


# ---------------------------------------------------------------- gap-fix pass (rebuild friction log)

class FakeClock:
    """Stands in for the time module inside base/build so settle loops run instantly."""
    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += s


class FakeComp2:
    def __init__(self, name="Composition1"):
        self.data = {}
        self.name = name

    def SetData(self, k, v):
        self.data[k] = v

    def GetData(self, k=None):
        return self.data.get(k)

    def GetAttrs(self):
        return {"COMPS_Name": self.name}


class FakeItem:
    def __init__(self, name, start, end, comp=None):
        self.name, self.start, self.end, self.comp = name, start, end, comp or FakeComp2()

    def GetName(self):
        return self.name

    def GetStart(self):
        return self.start

    def GetEnd(self):
        return self.end

    def GetFusionCompByIndex(self, i):
        return self.comp

    def GetFusionCompByName(self, n):
        return self.comp

    def GetFusionCompNameList(self):
        return {1: "Composition 1"}

    def LoadFusionCompByName(self, n):
        return True


class FakeTimeline:
    def __init__(self, tracks):
        self.tracks = tracks  # {track: [FakeItem]}
        self.tc = "01:00:00:00"
        self.page = None

    def GetName(self):
        return "TL"

    def GetSetting(self, k):
        return {"timelineFrameRate": 30}.get(k)

    def GetStartTimecode(self):
        return "01:00:00:00"

    def GetStartFrame(self):
        return 108000

    def GetTrackCount(self, kind):
        return max(self.tracks)

    def GetItemListInTrack(self, kind, k):
        return self.tracks.get(k, [])

    def GetIsTrackEnabled(self, kind, k):
        return True

    def SetCurrentTimecode(self, tc):
        if self.page() == "edit":  # [rebuild F11] the playhead only moves on the Edit page
            self.tc = tc
        return True

    def GetCurrentTimecode(self):
        return self.tc

    def frame(self):
        h, m, s_, f = (int(x) for x in self.tc.split(":"))
        return ((h * 60 + m) * 60 + s_) * 30 + f - 108000 + 108000


class FakeResolve:
    def __init__(self, tl):
        self.tl, self.page, self.opened = tl, "fusion", []
        tl.page = lambda: self.page
        res = self

        class PM:
            def GetCurrentProject(self_):
                return Proj()

        class Proj:
            def GetCurrentTimeline(self_):
                return tl

            def SetCurrentTimeline(self_, t):
                return True

            def GetTimelineCount(self_):
                return 1

            def GetTimelineByIndex(self_, i):
                return tl

            def GetName(self_):
                return "Testbed"

        class Fu:
            def GetCurrentComp(self_):
                if res.page != "fusion":
                    return None
                f = tl.frame()
                for k in sorted(tl.tracks, reverse=True):  # topmost clip under the playhead
                    for it in tl.tracks[k]:
                        if it.start <= f < it.end:
                            return it.comp
                return None
        self.pm, self.fu = PM(), Fu()

    def GetVersionString(self):
        return "21.1"

    def GetProjectManager(self):
        return self.pm

    def Fusion(self):
        return self.fu

    def GetCurrentPage(self):
        return self.page

    def OpenPage(self, p):
        self.opened.append(p)
        self.page = p
        return True


class MakeCurrent(unittest.TestCase):
    def _ctx(self, tracks):
        from fusion_connector.ops import base
        tl = FakeTimeline(tracks)
        r = FakeResolve(tl)
        ctx = base.Ctx()
        ctx._resolve = r
        clock = FakeClock()
        self._old = base.time
        base.time = clock
        return ctx, r, tl

    def tearDown(self):
        from fusion_connector.ops import base
        base.time = self._old

    def test_v2_item_goes_through_edit_page_and_middle_frame(self):
        v1 = [FakeItem("carrier", 108000, 108750)]
        v2 = [FakeItem("S1", 108000, 108048), FakeItem("S2", 108048, 108168)]
        ctx, r, tl = self._ctx({1: v1, 2: v2})
        c = ctx.make_current({"timeline": "TL", "track": 2, "item": 1})
        self.assertIs(c, v2[1].comp)
        self.assertIn("edit", r.opened)
        self.assertEqual(r.opened[-1], "fusion")
        self.assertEqual(tl.tc, "01:00:03:17")  # 108048 + 59 = frame 107 from start = 3 s 17 f at 30 fps

    def test_fast_path_when_already_current(self):
        v1 = [FakeItem("A", 108000, 108100)]
        ctx, r, tl = self._ctx({1: v1})
        tl.tc = "01:00:01:00"
        self.assertIs(ctx.make_current({"timeline": "TL", "item": 0}), v1[0].comp)
        self.assertEqual(r.opened, [])

    def test_covered_by_upper_track_is_reported(self):
        v1 = [FakeItem("under", 108000, 108100)]
        v2 = [FakeItem("over", 108000, 108100)]
        ctx, r, tl = self._ctx({1: v1, 2: v2})
        with self.assertRaises(OpError) as e:
            ctx.make_current({"timeline": "TL", "track": 1, "item": 0})
        self.assertEqual(e.exception.code, "NOT_CURRENT")
        self.assertEqual(e.exception.details["coveredBy"], [{"track": 2, "clip": "over"}])


class FakeTool:
    def __init__(self, name, reg="Background"):
        self.name, self.reg = name, reg

    def GetAttrs(self):
        return {"TOOLS_Name": self.name, "TOOLS_RegID": self.reg}


class FakeToolComp:
    def __init__(self, names):
        self.tools = {n: FakeTool(n) for n in names}

    def GetToolList(self, sel=False, kind=None):
        return {i + 1: t for i, t in enumerate(self.tools.values())}

    def FindTool(self, n):
        return self.tools.get(n)


class ToolsMatching(unittest.TestCase):
    def test_globs_inside_lists(self):
        from fusion_connector.ops.base import Ctx
        c = FakeToolComp(["S1_A", "S1_B", "S2_A", "MediaOut1"])
        got = [n for n, _ in Ctx().tools_matching(c, ["S1_*", "MediaOut1", "S1_A"])]
        self.assertEqual(got, ["S1_A", "S1_B", "MediaOut1"])
        with self.assertRaises(OpError) as e:
            Ctx().tools_matching(c, ["Nope"])
        self.assertNotIn("tools", e.exception.details)  # capped: count + sample, never the full list
        self.assertEqual(e.exception.details["toolCount"], 4)


class SettingGraph(unittest.TestCase):
    TEXT = ('{ Tools = ordered() { S1_Card = ImagePlane3D { Inputs = { MaterialInput = Input { SourceOp = "GA_SpeckTex", Source = "Output", }, '
            '["MtlStdInputs.ReceivesLighting"] = Input { Value = 0, }, }, }, '
            'S1_Cam = Camera3D { Inputs = { FilmGate = Input { Value = "BMD_URSA_4K_16x9", }, }, }, '
            'S1_M = Merge3D { Inputs = { SceneInput1 = Input { SourceOp = "S1_Card", Source = "Output", }, }, }, }, }')

    def test_external_wires_found(self):
        from fusion_connector.ops.build import setting_graph
        regs, ext = setting_graph(self.TEXT)
        self.assertEqual(regs["S1_M"], "Merge3D")
        self.assertEqual(ext, [("S1_Card", "MaterialInput", "GA_SpeckTex", "Output")])

    @needs_tsv
    def test_validate_camera_aperture_and_lighting(self):
        v = validate_setting_text(self.TEXT)
        w = " ".join(v["warnings"])
        self.assertIn("ApertureW = 0.8315", w)  # rebuild K2: FilmGate alone keeps the TV aperture
        self.assertIn("renders the RGB black", w)  # rebuild K4
        v2 = validate_setting_text('{ Tools = ordered() { B = Background { }, T = TextPlus { Inputs = { UseFrameFormatSettings = Input { Value = 1, }, }, }, }, }')
        self.assertEqual(sum("320x240" in x for x in v2["warnings"]), 1)  # live: pasted generators default to 320x240

    def test_paste_schema(self):
        self.assertTrue(validate(OPS["setting.paste"], {"path": "/x.setting", "quiet": True, "rewireExternal": True, "connect": [["A", "Input", "B"]]})[0])


class BatchFile(unittest.TestCase):
    def test_path_and_exclusivity(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "ops.json")
        json.dump({"ops": [{"operation": "comp.info", "args": {}}]}, open(p, "w"))
        v, e = server.load_batch_file({"path": p})
        self.assertIsNone(e)
        self.assertEqual(v["ops"][0]["operation"], "comp.info")
        self.assertIsNotNone(server.load_batch_file({"ops": [], "path": p})[1])
        self.assertEqual(server.load_batch_file({"path": "rel.json"})[1]["code"], "NOT_FOUND")
        self.assertTrue(validate(OPS["batch.run"], {"path": p})[0])

    def test_timeout_lifted_from_args(self):
        a, t = server.lift_timeout(OPS["render.range"], {"start": 0, "end": 4, "timeoutMs": 600000})
        self.assertEqual(t, 600000)
        self.assertNotIn("timeoutMs", a)
        self.assertTrue(validate(OPS["render.range"], a)[0])


class ResponseBudget(unittest.TestCase):
    def test_big_response_spills_to_file(self):
        with Env(FUSION_MCP_MAX_RESPONSE_CHARS="5000", FUSION_MCP_OUT_DIR=tempfile.mkdtemp()):
            env = {"ok": True, "result": {"added": [{"name": "T%d" % i, "regId": "TextPlus"} for i in range(2000)], "count": 2000}}
            small, text = server.fit(env)
            self.assertLessEqual(len(text), 5000)
            self.assertTrue(os.path.exists(small["truncated"]["fullResponse"]))
            self.assertEqual(small["result"]["count"], 2000)
            with open(small["truncated"]["fullResponse"]) as f:
                self.assertEqual(len(json.load(f)["result"]["added"]), 2000)
            same, _ = server.fit({"ok": True, "result": {"x": 1}})
            self.assertNotIn("truncated", same)

    def test_error_details_capped(self):
        with Env(FUSION_MCP_MAX_RESPONSE_CHARS="3000", FUSION_MCP_OUT_DIR=tempfile.mkdtemp()):
            r = server.err_result("OPERATION_FAILED", "x", details={"results": list(range(5000))})
            self.assertLess(len(r.content[0].text), 4000)


class SkillPaging(unittest.TestCase):
    def _store(self, body):
        from fusion_connector import skills
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "fusion-x", "references"))
        open(os.path.join(root, "fusion-x", "SKILL.md"), "w").write("---\nname: fusion-x\ndescription: t\n---\nbody\n")
        open(os.path.join(root, "fusion-x", "references", "big.md"), "w").write(body)
        man = os.path.join(root, "m.json")
        self.env = Env(FUSION_MCP_SKILLS_ROOT=root)
        self.env.__enter__()
        skills.build_manifest(root, man)
        return skills.SkillStore(man)

    def tearDown(self):
        if getattr(self, "env", None):
            self.env.__exit__()

    def test_toc_section_and_pages(self):
        from fusion_connector import skills
        body = "# Title\n\nintro\n\n## 1. Alpha\n\n" + ("a" * 50 + "\n") * 800 + "## R8. Real DOF\n\nDoFBlur is a radius\n\n```\n## not a heading\n```\n\n## 3. Gamma\n\ng\n"
        st = self._store(body)
        page = st.read("fusion-x", "references/big.md")
        self.assertTrue(page["truncated"])
        self.assertLessEqual(len(page["content"]), skills.PAGE)
        self.assertTrue(page["content"].endswith("\n"))
        nxt = st.read("fusion-x", "references/big.md", offset=page["nextOffset"])
        self.assertEqual(page["content"] + nxt["content"], body)
        sec = st.read("fusion-x", "references/big.md", section="R8")
        self.assertEqual(sec["section"], "R8. Real DOF")
        self.assertIn("DoFBlur is a radius", sec["content"])
        self.assertNotIn("Gamma", sec["content"])
        toc = st.read("fusion-x", "references/big.md", toc=True)["toc"]
        self.assertNotIn("not a heading", [h["title"] for h in toc])
        with self.assertRaises(KeyError):
            st.read("fusion-x", "references/big.md", section="zzz")

    def test_section_found_in_split_parts(self):
        from fusion_connector import skills
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "fusion-x", "references"))
        files = {"SKILL.md": "---\nname: fusion-x\ndescription: t\n---\nbody\n",
                 "references/ds.md": "# DS\n\nIndex.\n| [ds-1.md](ds-1.md) | 1k | R1 |\n",
                 "references/ds-1.md": "## R1. One\n\none\n", "references/ds-2.md": "## R8. Real DOF\n\nradius\n\n## R9. Next\n\nx\n"}
        for k, v in files.items():
            with open(os.path.join(root, "fusion-x", k), "w") as f:
                f.write(v)
        man = os.path.join(root, "m.json")
        with Env(FUSION_MCP_SKILLS_ROOT=root):
            skills.build_manifest(root, man)
            r = skills.SkillStore(man).read("fusion-x", "references/ds.md", section="R8")
        self.assertEqual(r["document"], "references/ds-2.md")
        self.assertEqual(r["content"], "## R8. Real DOF\n\nradius\n\n")


class SysMem(unittest.TestCase):
    def test_parsers_and_warning(self):
        from fusion_connector import sysmem
        self.assertEqual(sysmem.parse_footprint("phys_footprint: 252806080 B\n    phys_footprint_peak: 293274608 B"), (252806080, 293274608))
        used, total = sysmem.parse_swap("total = 8192.00M  used = 6481.50M  free = 1710.50M  (encrypted)")
        self.assertAlmostEqual(used / 1024 ** 3, 6.33, places=2)
        self.assertEqual(sysmem.parse_vm_stat("(page size of 16384 bytes)\nPages occupied by compressor:   10."), 163840)
        gb = sysmem.GB
        self.assertIsNone(sysmem.assess(8 * gb, 32 * gb, 60, 19.2))
        self.assertIn("restart", sysmem.assess(28 * gb, 32 * gb, 40, 19.2))
        self.assertIn("system.purge_cache", sysmem.assess(28 * gb, 32 * gb, 40, 19.2))
        self.assertIn("free memory level", sysmem.assess(4 * gb, 32 * gb, 9, 19.2))
        with Env(FUSION_MCP_MEMORY_WARN_GB="12"):
            self.assertEqual(sysmem.warn_threshold_gb(32 * gb), 12.0)
        self.assertEqual(sysmem.warn_threshold_gb(32 * gb) if not os.environ.get("FUSION_MCP_MEMORY_WARN_GB") else 19.2, 19.2)


class FakeDeliverProject:
    def __init__(self, pct):
        self.pct = pct

    def IsRenderingInProgress(self):
        return True

    def GetRenderJobList(self):
        return [{"JobId": "j1", "TimelineName": "FILM", "MarkIn": 108000, "MarkOut": 108749, "TargetDir": "/nonexistent", "OutputFilename": "a.mp4"}]

    def GetRenderJobStatus(self, jid):
        return {"JobStatus": "Rendering", "CompletionPercentage": self.pct, "EstimatedTimeRemainingInMs": 90000}


class Deliver(unittest.TestCase):
    def test_progress_frame_and_rate(self):
        from fusion_connector.ops import build
        from fusion_connector.ops.base import Ctx
        ctx = Ctx()
        clock = FakeClock()
        old = build.time
        build.time = clock
        try:
            r1 = build.deliver_progress(ctx, FakeDeliverProject(10))
            clock.sleep(30)
            r2 = build.deliver_progress(ctx, FakeDeliverProject(12))
            clock.sleep(200)
            r3 = build.deliver_progress(ctx, FakeDeliverProject(12))
        finally:
            build.time = old
        self.assertEqual(r1["jobs"][0]["approxFrame"], 75)
        self.assertEqual(r2["jobs"][0]["approxFrame"], 90)
        self.assertEqual(r2["jobs"][0]["secondsPerFrame"], 2.0)
        self.assertEqual(r2["jobs"][0]["etaSeconds"], 90)
        self.assertIn("no frame finished", r3["note"])
        ctx.deliver_started = {"j1": clock.t - 90}
        build.time = clock
        try:
            r4 = build.deliver_progress(ctx, FakeDeliverProject(0))
        finally:
            build.time = old
        self.assertGreaterEqual(r4["jobs"][0]["secondsWithoutAFrame"], 90)  # first frame never finished

    def test_status_and_stop_skip_ui_check(self):
        for n in ("deliver.status", "deliver.stop", "deliver.list_jobs", "render.cancel"):
            self.assertFalse(OPS[n].ui, n)
        self.assertTrue(OPS["deliver.start"].ui)
        self.assertTrue(OPS["project.load"].any_project)


class FakeFmtTimeline:
    def __init__(self, lock_fps=False):
        self.s = {"timelineResolutionWidth": "3840", "timelineResolutionHeight": "2160", "timelineFrameRate": "24"}
        self.lock_fps = lock_fps
        self.calls = []

    def SetSetting(self, k, v):
        self.calls.append(k)
        if k == "timelineFrameRate" and self.lock_fps:
            return False
        self.s[k] = v
        return True

    def GetSetting(self, k):
        return self.s.get(k)


class TimelineFormat(unittest.TestCase):
    def test_custom_settings_first_and_readback(self):
        from fusion_connector.ops.core import set_timeline_format
        tl = FakeFmtTimeline()
        self.assertEqual(set_timeline_format(tl, 1920, 1080, 30), {"width": 1920, "height": 1080, "fps": 30.0})
        self.assertEqual(tl.calls[0], "useCustomSettings")
        with self.assertRaises(OpError) as e:
            set_timeline_format(FakeFmtTimeline(lock_fps=True), None, None, 30)
        self.assertIn("fps", e.exception.message)

    def test_schemas(self):
        self.assertTrue(validate(OPS["timeline.create"], {"name": "x", "width": 1920, "height": 1080, "fps": 30, "fusionFrames": 750})[0])
        self.assertTrue(validate(OPS["timeline.add_fusion_clip"], {"frames": 48, "track": 2, "recordFrame": 0})[0])
        self.assertTrue(validate(OPS["comp.create"], {"onItem": 3, "track": 2})[0])
        self.assertTrue(validate(OPS["tool.delete"], {"tool": ["S1_*", "Grain"]})[0])


class FakeTrackItem:
    def __init__(self, name, start, end):
        self.n, self.s, self.e = name, start, end

    def GetName(self):
        return self.n

    def GetStart(self):
        return self.s

    def GetEnd(self):
        return self.e

    def GetUniqueId(self):
        return self.n


class FakeTrackTimeline:
    def __init__(self, items):
        self.items = items

    def GetStartFrame(self):
        return 108000

    def GetName(self):
        return "TL"

    def GetTrackCount(self, kind):
        return 1

    def GetItemListInTrack(self, kind, track):
        return self.items if track == 1 else []


class AppendOverlap(unittest.TestCase):
    """[scene builder pass] timeline.add_fusion_clip threw TypeError (NoneType - int) when its record range overlapped a clip."""

    def test_overlap_is_a_clear_error(self):
        from fusion_connector.ops.core import append_item
        tl = FakeTrackTimeline([FakeTrackItem("Fusion Composition", 108000, 108360)])

        class Ctx3:
            def project(self):
                class P:
                    def GetCurrentTimeline(self_):
                        return tl
                return P()
        with self.assertRaises(OpError) as e:
            append_item(Ctx3(), tl, None, 0, 120, 1, 0)
        self.assertEqual(e.exception.code, "INVALID_ARGS")
        self.assertIn("overlaps 'Fusion Composition' (0..359)", e.exception.message)
        self.assertEqual(e.exception.details["nextFreeFrame"], 360)
        self.assertEqual(e.exception.details["freeTrack"], 2)

    def test_create_adds_no_clip_unless_asked(self):
        p = {x.name: x for x in OPS["timeline.create"].params}
        self.assertFalse(p["fusionComp"].default)


class Carrier(unittest.TestCase):
    def test_ffmpeg_black_carrier(self):
        import shutil
        from fusion_connector.ops import core
        try:
            core._ffmpeg()
        except OpError:
            self.skipTest("no ffmpeg")
        out = tempfile.mkdtemp()

        class TL:
            def GetSetting(self, k):
                return {"timelineResolutionWidth": "64", "timelineResolutionHeight": "36", "timelineFrameRate": 30.0}[k]

        class Clip:
            def __init__(self, p):
                self.p = p

            def GetClipProperty(self, k):
                return self.p

        class MP:
            imported = []

            def GetRootFolder(self):
                return self

            def GetClipList(self):
                return [Clip(p) for p in self.imported]

            def GetSubFolderList(self):
                return []

            def GetCurrentFolder(self):
                return self

            def AddSubFolder(self, root, n):
                return self

            def SetCurrentFolder(self, f):
                return True

            def ImportMedia(self, paths):
                self.imported += paths
                return [Clip(p) for p in paths]

        class Ctx2:
            def project(self):
                class P:
                    def GetMediaPool(self_):
                        return mp
                return P()
        mp = MP()
        with Env(FUSION_MCP_OUT_DIR=out):
            clip, path, length = core.carrier_clip(Ctx2(), TL(), 48)
            self.assertEqual(length, 48)  # exact: the item comp's global range is the carrier's source range
            self.assertTrue(os.path.getsize(path) > 0)
            clip2, path2, _ = core.carrier_clip(Ctx2(), TL(), 48)  # reused file, imported once
            self.assertEqual(path2, path)
            self.assertEqual(MP.imported, [path])
        shutil.rmtree(out, ignore_errors=True)


class RenderRecover(unittest.TestCase):
    def test_restores_range_time_mediaout_and_savers(self):
        from fusion_connector.ops import build
        from fusion_connector.ops.base import Ctx

        class T:
            def __init__(self, n, reg):
                self.n, self.reg, self.attrs, self.deleted, self.wired = n, reg, {}, False, None

            def GetAttrs(self):
                return {"TOOLS_Name": self.n, "TOOLS_RegID": self.reg, **self.attrs}

            def SetAttrs(self, d):
                self.attrs.update(d)

            def Delete(self):
                self.deleted = True

            def ConnectInput(self, iid, src):
                self.wired = src
                return True

        class C:
            def __init__(self):
                self.tools = {"FC_TmpSaver_ab12": T("FC_TmpSaver_ab12", "Saver"), "Keep_Saver": T("Keep_Saver", "Saver"),
                              "MediaOut1": T("MediaOut1", "MediaOut"), "S2_Grain": T("S2_Grain", "FilmGrain")}
                self.tools["Keep_Saver"].attrs["TOOLB_PassThrough"] = True
                self.data = {build.RESTORE_KEY: json.dumps({"others": ["Keep_Saver"], "range": [0, 749], "time": 12,
                                                            "mediaOut": {"source": "S2_Grain", "output": "Output"}})}
                self.set_attrs, self.CurrentTime = {}, 100

            def GetData(self, k):
                return self.data.get(k)

            def SetData(self, k, v):
                self.data[k] = v

            def GetToolList(self, sel=False, kind=None):
                return {i + 1: t for i, t in enumerate(x for x in self.tools.values() if not t_del(x) and (kind is None or x.reg == kind))}

            def FindTool(self, n):
                return self.tools.get(n)

            def SetAttrs(self, d):
                self.set_attrs.update(d)

        def t_del(x):
            return x.deleted
        c = C()
        ctx = Ctx()
        ctx.connect = lambda dst, iid, src, output=None: dst.ConnectInput(iid, src)
        done = build.render_recover(ctx, c)
        self.assertTrue(c.tools["FC_TmpSaver_ab12"].deleted)
        self.assertFalse(c.tools["Keep_Saver"].attrs["TOOLB_PassThrough"])
        self.assertEqual(c.set_attrs, {"COMPN_RenderStart": 0, "COMPN_RenderEnd": 749})
        self.assertEqual(c.CurrentTime, 12)
        self.assertIs(c.tools["MediaOut1"].wired, c.tools["S2_Grain"])
        self.assertEqual(c.data[build.RESTORE_KEY], "")
        self.assertEqual(done["mediaOut1"], "S2_Grain")


class FontK(unittest.TestCase):
    def test_cap_per_em_matches_rebuild_constant(self):
        from fusion_connector.ops.build import font_cap_per_em
        path = "/System/Library/Fonts/HelveticaNeue.ttc"
        if not os.path.exists(path):
            self.skipTest("no Helvetica Neue")
        cpe, face = font_cap_per_em(path, "Helvetica Neue", "Bold")
        self.assertEqual(face, ("Helvetica Neue", "Bold"))
        # rebuild K1: Size 1.70*280/1920 rendered a 228 px cap height -> K = S*W/(cap/cpe) = 1.49
        S, W = 1.70 * 280 / 1920, 1920
        self.assertAlmostEqual(S * W / (228 / cpe), 1.49, delta=0.01)


class BatchPreviews(unittest.TestCase):
    def test_children_inline_previews_reach_the_batch(self):
        from fusion_connector import worker

        class C:
            def StartUndo(self, n):
                pass

            def EndUndo(self, keep):
                pass
        old = worker.run_op
        worker.run_op = lambda ctx, name, args, in_batch=False: {"path": "/x/%d.png" % args["n"], "_inline": ["/x/%d_p.png" % args["n"]]}
        try:
            out = worker.run_batch(None, C(), [{"operation": "render.frame", "args": {"n": i}} for i in range(10)], False)
        finally:
            worker.run_op = old
        self.assertEqual(len(out["previews"]), 10)
        self.assertEqual(len(out["_inline"]), 8)
        self.assertNotIn("_inline", out["results"][0]["result"])


class NewOpsSchema(unittest.TestCase):
    def test_new_ops_registered(self):
        for n in ("project.load", "system.memory", "system.purge_cache", "timeline.set_format", "timeline.append_clip", "timeline.add_fusion_clip",
                  "comp.clear", "render.cancel", "controller.sync"):
            self.assertIn(n, OPS)
        self.assertTrue(OPS["system.memory"].offline)
        self.assertTrue(OPS["comp.clear"].extra.get("paste"))
        for n in ("render.frame", "render.range", "render.contact_sheet", "render.compare"):
            self.assertIn("isolate", [p.name for p in OPS[n].params], n)

    def test_bulk_lua_template(self):
        from fusion_connector.ops.core import BULK_LUA, _lua_set
        code = BULK_LUA % (_lua_set({"S1_A", "S1_B"}), _lua_set({"BezierSpline"}), "true")
        self.assertIn('["S1_A"] = true', code)
        self.assertEqual(code.count("comp:Lock()"), 1)
        self.assertEqual(code.count("comp:Unlock()"), 1)
        self.assertGreaterEqual(code.count("pcall(function()"), 4)


# ================================================================ scene builder (scene.*)

from fusion_connector import scenegraph as sg  # noqa: E402
import fusion_connector.ops.scene as sops  # noqa: E402
from fusion_connector.ops.build import setting_syntax_problems  # noqa: E402

SCENES = os.path.join(ROOT, "tests", "scenes")
NOFONTS = sg.Fonts()   # deterministic tests: estimated text widths, no installed-font dependency


# Example scene descriptions; a fixture that is not shipped (the benchmark scene stays private) is skipped.
EXAMPLES = tuple(n for n in ("showcase", "title_low_tide", "card_smart_folders", "push_three_worlds", "bench_s2", "kitchen_sink")
                 if os.path.exists(os.path.join(SCENES, n + ".json")))


def load_scene(name):
    path = os.path.join(SCENES, name + ".json")
    if not os.path.exists(path):
        raise unittest.SkipTest(f"fixture tests/scenes/{name}.json is not shipped")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def mini(**kw):
    d = {"scene": "T", "size": [1920, 1080], "fps": 30, "duration": 60, "background": "#101010", "controls": {"accent": "#FF4B2B"},
         "layers": [{"id": "box", "type": "rect", "size": [400, 200], "radius": 20, "fill": "$accent", "position": [960, 540],
                     "keys": {"position": [[0, [960, 700], "out_expo"], [20, [960, 540]]]}},
                    {"id": "title", "type": "text", "position": [200, 300], "text": {"content": "Hello", "font": "Helvetica Neue", "style": "Bold", "size": 80}}]}
    d.update(kw)
    return d


def comp(d):
    return sg.compile_scene(d, fonts=NOFONTS)


class SceneSchema(unittest.TestCase):
    def test_examples_valid(self):
        for n in EXAMPLES:
            self.assertEqual(sg.validate(load_scene(n)), [], n)

    def test_unknown_property_suggests(self):
        d = mini()
        d["layers"][0]["postion"] = [1, 2]
        iss = sg.validate(d)
        self.assertTrue(any("did you mean 'position'" in i["message"] for i in iss), iss)

    def test_references_and_duplicates(self):
        d = mini()
        d["layers"].append({"id": "box", "type": "null"})
        d["layers"][1]["parent"] = "bxo"
        d["layers"][1]["opacity"] = "$acent"
        msgs = " ".join(i["message"] for i in sg.validate(d))
        self.assertIn("duplicate layer id 'box'", msgs)
        self.assertIn("parent 'bxo' is not a layer id - did you mean 'box'?", msgs)
        self.assertIn("control '$acent' is not defined", msgs)

    def test_reserved_ids_and_bad_ease(self):
        d = mini()
        d["layers"][0]["id"] = "Out"
        self.assertTrue(any("reserved" in i["message"] for i in sg.validate(d)))
        d = mini()
        d["layers"][0]["keys"]["position"][0][2] = "out_expoo"
        with self.assertRaises(sg.SceneError) as cm:
            comp(d)
        self.assertIn("did you mean 'out_expo'", cm.exception.message)

    def test_schema_op(self):
        r = OPS["scene.schema"].fn({})
        self.assertEqual(r["schema"]["title"], "use-fusion scene description v1")
        self.assertEqual(sg.validate(r["example"]), [])
        self.assertIn("fadeUp", " ".join(sg.MOVES))


class SceneCompile(unittest.TestCase):
    @needs_tsv
    def test_examples_emit_valid_setting_and_round_trip(self):
        for n in EXAMPLES:
            d = load_scene(n)
            c = comp(d)
            self.assertFalse([t for t in c.g.t if t.endswith("_Freeze_Freeze")], n)
            text = c.g.text()
            self.assertEqual(setting_syntax_problems(text), [], n)
            v = validate_setting_text(text)
            self.assertTrue(v["ok"], (n, v["problems"]))
            self.assertEqual(sg.from_setting(text)[d["scene"]], d, n)
            names = [t["name"] for t in v["tools"]]
            self.assertEqual(len(names), len(set(names)), n)

    def test_units_2d(self):
        c = comp(mini())
        t = c.g.t
        # rect: sShape in a tight canvas at k 1, placed by the Merge Center (keys map 1:1, ease kept)
        self.assertEqual(t["T_box_Src"]["reg"], "sRender")
        self.assertEqual((t["T_box_Src"]["inputs"]["Width"], t["T_box_Src"]["inputs"]["Height"]), (400, 200))
        path = t["T_boxCenterPath"]["inputs"]
        ky = t[path["Y"].op]["keys"]
        self.assertAlmostEqual(ky[0]["v"], 1 - 700 / 1080, 6)
        self.assertAlmostEqual(ky[-1]["v"], 0.5, 6)
        self.assertAlmostEqual(ky[0]["RH"][0], 0.16 * 20, 6)            # out_expo x1 * D, absolute handle
        self.assertAlmostEqual(ky[1]["LH"][0], 0.3 * 20, 6)
        # color control -> expression with the cached value
        self.assertEqual(t["T_box_Fill"]["inputs"]["Red"].e, "T_CTRL.accentRed")
        # text: Text+ Size = K * px * k / W with the measured Helvetica Neue Bold K, baseline anchor at the text origin
        tp = t["T_title_Src"]["inputs"]
        self.assertAlmostEqual(tp["Size"], 1.478 * 80 / tp["Width"], 6)
        self.assertEqual(tp["CenterOnBaseOfFirstLine"], 1)
        self.assertEqual(tp["HorizontalLeftCenterRight"], -1)

    def test_camera_and_card_units(self):
        c = comp(load_scene("showcase"))
        cam = c.g.t["Showcase_camera"]["inputs"]
        self.assertAlmostEqual(cam["FLength"], 0.4677 * 25.4 / 2 * 2666.7 / 540, 4)   # 29.33 mm, explicit aperture [rebuild K2]
        self.assertEqual((cam["ApertureW"], cam["ApertureH"]), (0.8315, 0.4677))
        card = c.g.t["Showcase_card_Card"]["inputs"]
        self.assertAlmostEqual(card["Transform3DOp.Scale.X"], 960 / 1080, 6)           # plane 1 unit wide = texture width
        self.assertEqual(card["Transform3DOp.Rotate.RotOrder"], "ZYX")                   # [rebuild K7]
        self.assertEqual(card["SurfacePlaneInputs.Lighting.IsAffectedByLights"], 0)     # unlit, not ReceivesLighting [rebuild K4]
        r3 = c.g.t["Showcase_R3D"]["inputs"]
        self.assertEqual(r3["RendererOpenGL.TransparencySorting"], 0)                   # Z buffer default (efficiency lab B5)
        self.assertEqual(r3["UseFrameFormatSettings"], 1)
        self.assertIn("Showcase_CTRL.Draft", r3["MotionBlur"].e)
        # opacity is held per frame under the renderer (AE never motion-blurs opacity) [rebuild K15]
        ks = c.g.t["Showcase_card_CardMtlStdInputsDiffuseOpacity"]["keys"]
        self.assertTrue(all(k["f"] == 0 or abs(k["f"] - round(k["f"]) - (-0.5)) < 1e-9 or k["f"] % 1 for k in ks))

    def test_sorted_transparency_override(self):
        d = load_scene("showcase")
        d["render3d"] = {"transparency": "sorted"}
        self.assertEqual(comp(d).g.t["Showcase_R3D"]["inputs"]["RendererOpenGL.TransparencySorting"], 1)

    def test_culling_regions_on_consuming_merge(self):
        d = mini()
        d["layers"][1].update({"in": 10, "out": 30})
        c = comp(d)
        self.assertEqual(c.regions["T_title"], [9, 30])          # [in - margin, out - 1 + margin] on the Merge, never the source
        self.assertNotIn("T_title_Src", c.regions)
        d["layers"][1]["opacity"] = 0
        self.assertEqual(comp(d).regions["T_title"], [-2, -1])  # never visible
        d = mini(efficiency={"cull": False})
        d["layers"][1].update({"in": 10, "out": 30})
        c = comp(d)
        self.assertEqual(c.regions, {})
        self.assertIn("Blend", c.g.t["T_title"]["inputs"])      # in/out as Blend steps instead

    def test_adaptive_motion_blur_and_hold(self):
        c = comp(mini())
        mb = c.g.t["T_box"]["inputs"]["MotionBlur"]
        self.assertIn("T_CTRL.Draft", mb.e)
        table = [int(x) for x in re.search(r"\{([01,]+)\}", mb.e).group(1).split(",")]
        self.assertEqual(len(table), 60)
        self.assertEqual(table[0], 1)
        self.assertEqual(sum(table[25:]), 0)                  # at rest: no motion blur
        self.assertNotIn("MotionBlur", c.g.t["T_title"]["inputs"])
        d = mini(motionBlur=False)
        self.assertNotIn("MotionBlur", comp(d).g.t["T_box"]["inputs"])

    def test_draft_default_and_quality(self):
        self.assertEqual(comp(mini()).g.t["T_CTRL"]["inputs"]["Draft"], 1)
        self.assertEqual(comp(mini(quality="final")).g.t["T_CTRL"]["inputs"]["Draft"], 0)

    def test_batching_and_texture_dedupe(self):
        c = comp(load_scene("showcase"))
        self.assertEqual(c.g.t["Showcase_app_surface_Shapes_sMrg"]["reg"], "sMerge")
        c = comp(load_scene("push_three_worlds"))
        srcs = {c.g.t[n]["inputs"]["MaterialInput"].op for n in ("ThreeWorlds_s1_Card", "ThreeWorlds_s2_Card", "ThreeWorlds_s3_Card", "ThreeWorlds_s4_Card")}
        self.assertEqual(len(srcs), 1)

    def test_texture_scale_follows_screen_size(self):
        c = comp(load_scene("push_three_worlds"))
        tex = {t["layer"]: t for t in c.textures}
        self.assertLessEqual(tex["hero"]["scale"], 2.0)
        self.assertGreater(tex["hero"]["scale"], 1.0)        # pushed in past 1:1
        self.assertEqual(tex["s1"]["scale"], 2.0)            # the near speck hits the cap

    def test_2_5d_for_flat_cards(self):
        d = load_scene("showcase")
        d["layers"][1]["keys"].pop("rotationY")
        c = comp(d)
        self.assertEqual(c.stats["renderers"], 0)
        self.assertEqual(c.stats["renderers2_5d"], 1)
        self.assertNotIn("Renderer3D", {r["reg"] for r in c.g.t.values()})
        self.assertIn("XBlurSize", c.g.t["Showcase_card_DOF"]["inputs"])
        d["efficiency"] = {"mode3d": "real"}
        self.assertEqual(comp(d).stats["renderers"], 1)

    def test_corner_gradient_follows_controls(self):
        d = mini(background={"gradient": {"from": [0, 0], "to": [1920, 1080], "stops": [[0, "$accent"], [1, "#000000"]]}})
        bg = comp(d).g.t["T_BG"]["inputs"]
        self.assertEqual(bg["Type"], "Corner")
        self.assertIn("T_CTRL.accentRed", bg["TopLeftRed"].e)


class SceneKitchenSink(unittest.TestCase):
    """Every feature once: mattes, masks, 2D parent bake, non-uniform scale, effects, image, lights, 3D rig, typewriter."""

    def setUp(self):
        cwd = os.getcwd()
        os.chdir(ROOT)  # the image src is relative to the repo
        self.addCleanup(os.chdir, cwd)
        self.c = comp(load_scene("kitchen_sink"))

    def test_features_emit(self):
        t = self.c.g.t
        self.assertEqual(t["Sink_masked_Matte"]["reg"], "BitmapMask")
        self.assertEqual(t["Sink_masked_Matte"]["inputs"]["Channel"], "Luminance")
        self.assertEqual(t["Sink_masked"]["inputs"]["EffectMask"].op, "Sink_masked_Matte")
        self.assertEqual(t["Sink_masked_Src"]["inputs"]["EffectMask"].op, "Sink_masked_Mask2")
        self.assertEqual(t["Sink_masked_Mask2"]["inputs"]["PaintMode"], "Subtract")
        self.assertEqual(t["Sink_masked"]["inputs"]["ApplyMode"], "Screen")
        self.assertEqual(t["Sink_squash_Scale"]["reg"], "Transform")                   # non-uniform scale
        self.assertEqual(t["Sink_squash_Scale"]["inputs"]["UseSizeAndAspect"], 0)
        self.assertEqual(len(t["Sink_orbitCenterPathX"]["keys"]), 50)                  # animated 2D parent: baked
        self.assertEqual(t["Sink_hang_Rig"]["reg"], "Merge3D")                        # 3D parent: native rig
        self.assertEqual(t["Sink_R3D"]["inputs"]["RendererOpenGL.LightingEnabled"], 1)
        self.assertEqual(t["Sink_lit_card_Card"]["inputs"]["SurfacePlaneInputs.Lighting.IsAffectedByLights"], 1)
        self.assertEqual(t["Sink_img_Src"]["reg"], "Loader")
        self.assertIn("time*Sink_CTRL.spin/10", t["Sink_roll"]["inputs"]["Angle"].e)
        self.assertEqual(t["Sink_Out"]["reg"], "FilmGrain")
        self.assertAlmostEqual(t["Sink_cam"]["inputs"]["FLength"], 0.4677 * 25.4 / 2 * (1280 * 35 / 36) / 360, 4)   # lens 35 mm


class SceneAuthoring(unittest.TestCase):
    def test_text_styles_and_tokens(self):
        d = mini(controls={"accent": "#FF4B2B", "gap": 30}, textStyles={"h1": {"font": "Helvetica Neue", "style": "Bold", "size": 120, "color": "$accent"}})
        d["layers"][1]["text"] = {"content": "Hi", "textStyle": "h1"}
        d["layers"][0]["radius"] = "$gap"
        c = comp(d)
        self.assertAlmostEqual(c.g.t["T_title_Src"]["inputs"]["Size"] * c.g.t["T_title_Src"]["inputs"]["Width"], 1.478 * 120, 4)
        self.assertEqual(c.desc["layers"][0]["radius"], 30.0)
        self.assertEqual(c.authored["layers"][0]["radius"], "$gap")    # stored as authored

    def test_align_safe_and_relative(self):
        d = mini(safeArea=100)
        d["layers"][0].pop("keys")
        d["layers"][0]["align"] = "bottom-right"
        d["layers"][1]["align"] = {"to": "box", "place": "above", "gap": 20, "x": "left"}
        c = comp(d)
        box = c.desc["layers"][0]
        self.assertEqual(box["position"], [1920 - 100 - 200, 1080 - 100 - 100])
        t = c.desc["layers"][1]
        self.assertEqual(t["text"]["align"], "left")
        self.assertAlmostEqual(t["position"][0], 1920 - 100 - 400)          # left edge of the box
        self.assertAlmostEqual(t["position"][1], 1080 - 100 - 200 - 20)     # last baseline 20 px above the box top

    def test_stack_layout_and_stagger(self):
        d = load_scene("card_smart_folders")
        c = comp(d)
        L = {x["id"]: x for _, x in sg._all_layers(c.desc)}
        ys = [L[i]["position"][1] for i in ("icon", "headline", "body", "cta")]
        self.assertEqual(ys, sorted(ys))
        self.assertEqual(L["icon"]["position"], [64 + 40, 64 + 40])          # padding + half the icon
        self.assertEqual([L[i]["keys"]["opacity"][0][0] for i in ("icon", "headline", "body", "cta")], [12, 16, 20, 24])
        self.assertEqual(c.desc["layers"][0]["size"][0], 600)
        # the cursor rests on the button (inside the card) + offset, entering from its offset
        cur = L["cursor"]["keys"]["position"]
        self.assertEqual(cur[0][0], 40)
        self.assertAlmostEqual(cur[1][1][0] - cur[0][1][0], -420)

    def test_multiline_text_runs_down_from_the_last_baseline(self):
        # [live, scene builder pass] CenterOnBaseOfFirstLine 1 stacks extra lines upward
        d = mini()
        d["layers"][1]["text"].update(content="One\nTwo\nThree", leading=100)
        tp = comp(d).g.t["T_title_Src"]["inputs"]
        self.assertEqual((tp["CenterOnBaseOfFirstLine"], tp["VerticalTopCenterBottom"]), (0, 1))
        self.assertAlmostEqual((0.5 - tp["Center"][1]) * tp["Height"], 200)     # Center on the third baseline
        self.assertAlmostEqual(tp["LineSpacing"], 100 / (0.8 * 1.478 * 80))

    def test_whole_line_rise_moves_the_merge(self):
        d = mini()
        d["layers"][1].update(animators=[{"type": "cascade", "start": 5, "stagger": 0, "duration": 8, "ease": "out_expo", "from": {"y": 60}}],
                              masks=[{"shape": "rect", "box": [-20, -90, 400, 110]}])
        c = comp(d)
        t = c.g.t
        self.assertNotIn("T_title_Src_Fol", t)                                  # no per-character re-render
        self.assertIn("T_title_Src_Freeze", t)                                  # the text raster is static
        self.assertEqual(t["T_title"]["inputs"]["EffectMask"].op, "T_title_Mask1")   # the reveal box stays put
        self.assertEqual(t["T_title"]["inputs"]["Center"].op, "T_titleCenterPath")
        self.assertEqual(c.authored["layers"][1]["animators"][0]["stagger"], 0)  # stored as authored

    def test_enter_exit_presets(self):
        d = mini()
        d["layers"][1].update(enter="pop", exit={"preset": "fadeOut", "at": 40})
        L = comp(d).desc["layers"][1]
        self.assertEqual(L["keys"]["scale"], [[0.0, 70.0, "out_back"], [14.0, 100.0]])
        self.assertEqual(L["keys"]["opacity"], [[0.0, 0.0, "out_back"], [14.0, 100.0], [40.0, 100.0, "in"], [50.0, 0.0]])
        d["layers"][1]["exit"] = {"preset": "fadeOut", "at": 5}
        with self.assertRaises(sg.SceneError):
            comp(d)

    def test_group_canvas_cropped_to_content(self):
        c = comp(load_scene("title_low_tide"))
        base = c.g.t["LowTide_block_Base"]["inputs"]
        self.assertLess(base["Width"], 1920)
        self.assertLess(base["Height"], 1080)


class SceneBenchS2(unittest.TestCase):
    """The benchmark scene agrees with the render-verified rebuild's numbers (its render-verified .setting)."""

    def test_matches_rebuild_constants(self):
        c = comp(load_scene("bench_s2"))
        cam = c.g.t["S2_CAM"]["inputs"]
        self.assertAlmostEqual(cam["FLength"], 29.337, 2)
        r3 = c.g.t["S2_R3D"]["inputs"]
        self.assertAlmostEqual(r3["RendererOpenGL.DoFBlur"].v, 32.5 / 2 / 1080, 9)
        self.assertEqual(r3["RendererOpenGL.AccumQuality"], 12)
        self.assertIn("S2_FOCUS.Transform3DOp.Translate.Z", cam["PlaneOfFocus"].e)
        bg = c.g.t["S2_BG"]["inputs"]
        self.assertEqual(bg["Type"], "Corner")
        self.assertIn("S2_CTRL.NIGHT_ARed", bg["TopLeftRed"].e)
        rows = {c.g.t["S2_%s_Card" % r]["inputs"]["MaterialInput"].op for r in ("RowA", "RowB", "RowC")}
        self.assertEqual(len(rows), 1)                                        # one filmstrip texture for three rows
        self.assertAlmostEqual(c.g.t["S2_RowA_Card"]["inputs"]["Transform3DOp.Rotate.Y"].v, 18)   # AE -18 x Depth/100, sign flipped
        self.assertEqual(c.g.t["S2_Out"]["inputs"]["MasterStrength"], 0.0115)


class SceneStart(unittest.TestCase):
    def test_start_shifts_keys_expressions_and_regions(self):
        a = mini()
        a["layers"][1].update({"in": 10, "out": 30})
        b = dict(a, start=100)
        ca, cb = comp(a), comp(b)
        ka = ca.g.t["T_boxCenterPathY"]["keys"]
        kb = cb.g.t["T_boxCenterPathY"]["keys"]
        self.assertEqual([k["f"] + 100 for k in ka], [k["f"] for k in kb])
        self.assertAlmostEqual(kb[0]["RH"][0], ka[0]["RH"][0] + 100)
        self.assertEqual(cb.regions["T_title"], [109, 130])
        self.assertIn("(time - 100)", cb.g.t["T_box"]["inputs"]["MotionBlur"].e)
        self.assertEqual(sg.from_setting(cb.g.text())["T"]["start"], 100)

    def test_film_ladder(self):
        live = SceneLive("test_build_one_call")
        live.setUp()
        try:
            live.ctx.source_of = lambda tool, iid: [tool.ins[iid][1], "Output"] if isinstance(tool.ins.get(iid), tuple) else None
            d1, d2 = mini(), dict(mini(scene="U"), start=60)
            live.build(d1, film=True)
            live.build(d2, film=True)
            t = live.comp.tools
            self.assertEqual(t["MediaOut1"].ins["Input"], ("src", "FILM_U"))
            self.assertEqual(t["FILM_U"].ins["Background"], ("src", "FILM_T"))
            self.assertEqual(t["FILM_T"].ins["Background"], ("src", "FILM_Base"))
            self.assertEqual(t["FILM_U"].attrs["TOOLNT_EnabledRegion_Start"], {1: 60})
            self.assertEqual(t["FILM_T"].attrs["TOOLNT_EnabledRegion_End"], {1: 59})
        finally:
            live.tearDown()


class SceneDiff(unittest.TestCase):
    def test_restyle_is_a_set(self):
        a = mini()
        b = sg.apply_edits(a, [{"layer": "title", "set": {"text.content": "Hello!"}}])
        ops = sg.diff(comp(a), comp(b))
        self.assertEqual(ops.get("replace"), None)
        self.assertEqual([x["input"] for x in ops["set"]], ["StyledText"])

    def test_retime_rewrites_the_spline(self):
        a = mini()
        b = sg.apply_edits(a, [{"layer": "box", "keys": {"position": [[5, [960, 700], "out_expo"], [30, [960, 540]]]}}])
        ops = sg.diff(comp(a), comp(b))
        self.assertEqual({k["host"] for k in ops["keys"]}, {"T_boxCenterPath"})
        self.assertEqual(ops["keys"][0]["path"][0], ["T_box", "Center"])
        self.assertNotIn("replace", ops)

    def test_add_and_remove_layers_rewire_the_stack(self):
        a = mini()
        b = sg.apply_edits(a, [{"add": {"id": "dot", "type": "ellipse", "size": [40, 40], "position": [100, 100]}, "after": "box"}])
        ops = sg.diff(comp(a), comp(b))
        self.assertIn("T_dot", ops["add"])
        self.assertIn(["T_title", "Background", "T_dot", "Output"], ops["connect"])
        ops = sg.diff(comp(b), comp(a))
        self.assertIn("T_dot", ops["remove"])
        self.assertIn(["T_title", "Background", "T_box", "Output"], ops["connect"])

    def test_quality_final_flips_only_the_draft_control(self):
        a = mini()
        ops = sg.diff(comp(a), comp(sg.apply_edits(a, [{"scene": {"quality": "final"}}])))
        self.assertEqual(ops["set"], [{"tool": "T_CTRL", "input": "Draft", "value": 0}])
        self.assertEqual([d["tool"] for d in ops["data"]], ["T_Out"])

    def test_token_and_style_edits_are_sets(self):
        a = mini(textStyles={"h1": {"font": "Helvetica Neue", "style": "Bold", "size": 80}})
        a["layers"][1]["text"] = {"content": "Hello", "textStyle": "h1"}
        ops = sg.diff(comp(a), comp(sg.apply_edits(a, [{"scene": {"controls.accent": "#00A676"}}])))
        self.assertEqual({x["tool"] for x in ops["set"]}, {"T_CTRL"})
        self.assertNotIn("replace", ops)
        ops = sg.diff(comp(a), comp(sg.apply_edits(a, [{"scene": {"textStyles.h1.size": 96}}])))
        self.assertNotIn("replace", ops)
        self.assertIn("Size", [x["input"] for x in ops["set"]])

    def test_structural_change_replaces_only_that_tool(self):
        a = mini()
        b = sg.apply_edits(a, [{"layer": "box", "set": {"fill": {"gradient": {"stops": [[0, "#000000"], [1, "#FFFFFF"]]}}}}])
        ops = sg.diff(comp(a), comp(b))
        self.assertTrue(set(ops["replace"]) | set(ops["add"]) | set(ops["remove"]))
        self.assertNotIn("T_title", ops.get("replace", []))

    def test_apply_edits_grammar(self):
        a = mini()
        b = sg.apply_edits(a, [{"layer": "box", "keys": {"position": None}, "in": 3}, {"remove": "title"}])
        self.assertNotIn("keys", b["layers"][0])
        self.assertEqual(b["layers"][0]["in"], 3)
        self.assertEqual(len(b["layers"]), 1)
        self.assertEqual(len(a["layers"]), 2)            # input untouched
        with self.assertRaises(sg.SceneError):
            sg.apply_edits(a, [{"layer": "titel", "set": {}}])

    def test_diff_op_offline(self):
        r = OPS["scene.diff"].fn({"old": mini(), "edits": [{"layer": "title", "set": {"text.color": "#00FF00"}}]})
        self.assertEqual(r["counts"]["set"], 2)            # white -> green: red and blue change


class ScenePlanOp(unittest.TestCase):
    def test_plan_reports_costs_and_writes_setting(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "s.setting")
            r = OPS["scene.plan"].fn({"path": os.path.join(SCENES, "push_three_worlds.json"), "outPath": out})
            self.assertTrue(r["ok"])
            self.assertEqual(r["cost"]["renderers3d"], 1)
            self.assertGreater(r["nodes"]["tools"], 20)
            self.assertTrue(any("Z buffer" in x for x in r["decisions"]))
            self.assertTrue(os.path.exists(out))
            self.assertIn("ThreeWorlds", OPS["scene.read"].fn({"path": out})["scenes"])
        bad = mini()
        bad["layers"][0]["type"] = "rectangle"
        self.assertFalse(OPS["scene.plan"].fn({"description": bad})["ok"])

    def test_wireframe_preview(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "p.png")
            r = OPS["scene.plan"].fn({"path": os.path.join(SCENES, "card_smart_folders.json"), "preview": {"frames": [0, 74], "width": 320, "outPath": out}})
            self.assertEqual(r["_inline"], [out])
            info = png_info(out)
            self.assertEqual((info["width"], info["height"]), (2 * 320 + 4, 180))


# ---------------------------------------------------------------- live handlers against a fake Fusion comp

class FIn:
    def __init__(self, tool, iid):
        self.tool, self.iid = tool, iid

    def GetAttrs(self):
        return {"INPS_ID": self.iid, "INPS_DataType": "Point" if self.iid in ("Center", "Pivot") else "Number"}

    def GetConnectedOutput(self):
        v = self.tool.ins.get(self.iid)
        if isinstance(v, tuple) and v and v[0] == "src":
            t = self.tool.comp.tools.get(v[1])
            return FOut(t) if t else None
        return None

    def SetExpression(self, e):
        self.tool.expr[self.iid] = e

    def GetExpression(self):
        return self.tool.expr.get(self.iid)


class FOut:
    def __init__(self, tool):
        self.tool = tool

    def GetTool(self):
        return self.tool

    def GetAttrs(self):
        return {"OUTS_ID": "Output"}

    def GetConnectedInputs(self):
        return {}


class FTool:
    def __init__(self, comp, name, reg):
        self.comp, self.name, self.reg = comp, name, reg
        self.ins, self.expr, self.data, self.attrs, self.keys = {}, {}, {}, {}, None

    def GetAttrs(self):
        return dict(self.attrs, TOOLS_Name=self.name, TOOLS_RegID=self.reg)

    def SetAttrs(self, a):
        self.attrs.update(a)

    def ResetEnabledRegion(self):
        self.attrs.pop("TOOLNT_EnabledRegion_Start", None)
        self.attrs.pop("TOOLNT_EnabledRegion_End", None)

    def GetInputList(self):
        ids = set(self.ins) | {"Input", "Background", "Foreground", "Center", "StyledText", "Draft", "MotionBlur"}
        return {i + 1: FIn(self, k) for i, k in enumerate(sorted(ids))}

    def SetInput(self, iid, v, *a):
        self.ins[iid] = v

    def GetInput(self, iid, *a):
        return self.ins.get(iid)

    def ConnectInput(self, iid, src):
        self.ins[iid] = ("src", src.name) if src is not None else None
        return True

    def FindMainOutput(self, i):
        return FOut(self)

    def GetOutputList(self):
        return {1: FOut(self)}

    def SetData(self, k, v):
        self.data[k] = v

    def GetData(self, k):
        return self.data.get(k)

    def Delete(self):
        self.comp.tools.pop(self.name, None)


class FComp:
    def __init__(self):
        self.tools = {}
        self.CurrentTime = 0
        mo = FTool(self, "MediaOut1", "MediaOut")
        self.tools["MediaOut1"] = mo

    def FindTool(self, n):
        return self.tools.get(n)

    def GetToolList(self, sel=False):
        return {i + 1: t for i, t in enumerate(self.tools.values())}


class FCtx:
    """The Ctx surface scene ops use, over FComp. Pastes like Fusion: SourceOps to tools outside the text are dropped and pasted
    BezierSplines/XYPaths are renamed (<name>_R), so live code must find modifiers through their host input."""

    def __init__(self, comp):
        self.c, self.notes, self.pastes = comp, [], []

    def source_of(self, tool, iid):
        v = getattr(tool, "ins", {}).get(iid)
        return [v[1], "Output"] if isinstance(v, tuple) and len(v) > 1 else None

    def paste(self, comp, text, wait=6.0):
        from fusion_connector.luatable import LTable, parse
        self.pastes.append(text)
        tools = parse(text).get("Tools")
        names = [k for k, v in tools.items if isinstance(v, LTable)]
        ren = {n: (n + "_R" if tools.get(n).ctor in ("BezierSpline", "XYPath") else n) for n in names}
        for n in names:
            t = tools.get(n)
            ft = FTool(comp, ren[n], t.ctor)
            ins = t.get("Inputs")
            for k, iv in (ins.items if isinstance(ins, LTable) else []):
                if isinstance(iv, LTable):
                    if iv.get("SourceOp"):
                        if iv.get("SourceOp") in ren:
                            ft.ins[k] = ("src", ren[iv.get("SourceOp")])
                    else:
                        ft.ins[k] = iv.get("Value")
                        if iv.get("Expression"):
                            ft.expr[k] = iv.get("Expression")
            cd = t.get("CustomData")
            for k, v in (cd.items if isinstance(cd, LTable) else []):
                ft.data[k] = v
            if t.ctor == "BezierSpline":
                ft.keys = t.get("KeyFrames")
            comp.tools[ft.name] = ft
        return {"added": [ren[n] for n in names], "renamed": {n: n for n in names}}

    def names(self, comp):
        return sorted(comp.tools)

    def tool(self, comp, n):
        t = comp.FindTool(n)
        if t is None:
            raise OpError("NOT_FOUND", n)
        return t

    def inp(self, t, iid):
        return FIn(t, iid)

    def connect(self, dst, iid, src, output=None):
        dst.ConnectInput(iid, src)
        return [src.name, output or "Output"]

    def consumers(self, comp, tool, output=None):
        out = []
        for t in comp.tools.values():
            for k, v in t.ins.items():
                if v == ("src", tool.name):
                    out.append((t.name, k, "Output"))
        return out

    def fmt(self, comp):
        return 1920, 1080, 30.0

    def to_fusion(self, comp, tool, iid, v):
        return {1: v[0], 2: v[1]} if isinstance(v, list) else v


def fake_repaste(ctx, comp, spec, text=None, wait=None, log=None):
    """scene.repaste over FComp, step for step what REPASTE_LUA does in Fusion (the Lua itself runs in LuaJIT in RepasteChunk)."""
    victims = list(spec.get("victims") or [])
    vset, keep, names = set(victims), set(spec.get("keep") or []), list(spec.get("names") or [])
    live = [n for n in victims if n in comp.tools]
    going, ext, pos = [], [], {}

    def collect(t, specs):
        for sp in specs or []:
            v = t.ins.get(sp["id"])
            if isinstance(v, tuple) and v[0] == "src" and v[1] in comp.tools:
                m = comp.tools[v[1]]
                collect(m, sp.get("sub"))
                going.append(m.name)
    for n in live:
        t = comp.tools[n]
        if n in names:
            pos[n] = getattr(t, "pos", None)
        for cn, ct in comp.tools.items():
            for iid, v in ct.ins.items():
                if v == ("src", n) and cn not in keep and cn not in vset:
                    ext.append((cn, iid, n))
        collect(t, (spec.get("mods") or {}).get(n))
    clash = [n for n in names if n not in vset and n not in going and n in comp.tools]
    if clash:
        raise OpError("INVALID_ARGS", "%d tools to paste already exist (e.g. %s); nothing was changed" % (len(clash), clash[:3]),
                      details={"exist": clash[:20]})
    for n in live:
        comp.tools.pop(n, None)
    nm = 0
    for m in going:
        if m in comp.tools and not any(v == ("src", m) for x in comp.tools.values() for v in x.ins.values()):
            comp.tools.pop(m)
            nm += 1
    if log is not None:
        log.append(list(victims))
    if text:
        ctx.paste(comp, text)
    problems = []
    for cn, iid, src in ext:
        if cn in comp.tools and src in comp.tools:
            comp.tools[cn].ins[iid] = ("src", src)
    for dst, iid, src, out in spec.get("wires") or []:
        if dst in comp.tools and src in comp.tools:
            comp.tools[dst].ins[iid] = ("src", src)
        else:
            problems.append("%s.%s<-%s missing" % (dst, iid, src))
    for dst, iid in spec.get("cuts") or []:
        if dst in comp.tools:
            comp.tools[dst].ins[iid] = None
    for t, iid, e in spec.get("exprs") or []:
        comp.tools[t].expr[iid] = e
    for t, s, e in spec.get("regions") or []:
        if t in comp.tools:
            comp.tools[t].SetAttrs({"TOOLNT_EnabledRegion_Start": {1: s}, "TOOLNT_EnabledRegion_End": {1: e}})
        else:
            problems.append(t + " region missing")
    for t in spec.get("reset") or []:
        if t in comp.tools:
            comp.tools[t].ResetEnabledRegion()
    for n, p in pos.items():
        if n in comp.tools:
            comp.tools[n].pos = p
    found = {}
    for key, path in spec.get("paths") or []:
        t = comp.tools.get(path[0][0])
        for host, iid in path:
            v = t.ins.get(iid) if t is not None else None
            t = comp.tools.get(v[1]) if isinstance(v, tuple) else None
        if t is not None:
            found[key] = t.name
        else:
            problems.append(key + " spline not found")
    return {"deleted": len(live), "modifiers": nm, "pasted": sum(1 for n in names if n in comp.tools),
            "missing": [n for n in names if n not in comp.tools], "problems": problems, "splines": found, "ms": 1}


class SceneLive(unittest.TestCase):
    def setUp(self):
        self.saved = (sops.repaste, sops.write_spline, sops.setting_copy, sops._fonts)
        self.deleted, self.splines = [], []

        def repaste(ctx, comp, spec, text=None, wait=None):
            return fake_repaste(ctx, comp, spec, text, wait, log=self.deleted)

        def write_spline(comp, sp, keys, eases, loop=None, fps=24):
            self.splines.append((sp.name, keys))

        def setting_copy(ctx, comp, a):
            lines = []
            from fusion_connector.luatable import LTable

            def lua(v):
                if isinstance(v, LTable):
                    return ("%s { %s }" % (v.ctor, json.dumps(v.positional()[0])) if v.ctor else "{ %s }" % ", ".join(str(x) for x in v.positional()))
                return json.dumps(v)
            for n in a["tools"]:
                t = comp.tools[n]
                ins = ", ".join('%s = Input { Value = %s }' % (k if re.fullmatch(r"\w+", k) else '["%s"]' % k, lua(v))
                                for k, v in t.ins.items() if v is not None and not isinstance(v, tuple))
                lines.append("%s = %s { Inputs = { %s } }," % (n, t.reg, ins))
            return {"tools": a["tools"], "text": "{ Tools = ordered() { %s } }" % " ".join(lines)}
        sops.repaste, sops.write_spline, sops.setting_copy = repaste, write_spline, setting_copy
        sops._fonts = lambda ctx=None: NOFONTS
        self.comp = FComp()
        self.ctx = FCtx(self.comp)
        self.env = Env(FUSION_MCP_OUT_DIR=tempfile.mkdtemp())   # quiet builds write their detail file there
        self.env.__enter__()

    def tearDown(self):
        sops.repaste, sops.write_spline, sops.setting_copy, sops._fonts = self.saved
        self.env.__exit__()

    def build(self, d, **kw):
        return OPS["scene.build"].fn(self.ctx, self.comp, dict({"description": d}, **kw))

    def test_build_one_call(self):
        d = mini()
        d["layers"][1].update({"in": 10, "out": 30})
        r = self.build(d)
        self.assertEqual(r["scene"], "T")
        self.assertTrue(r["mediaOut"])
        self.assertEqual(self.comp.tools["MediaOut1"].ins["Input"], ("src", "T_Out"))
        self.assertEqual(json.loads(self.comp.tools["T_Out"].data[sg.ROOT_KEY]), d)
        self.assertEqual(self.comp.tools["T_title"].attrs["TOOLNT_EnabledRegion_Start"], {1: 9})
        self.assertEqual(r["regions"], 1)
        self.assertEqual(r["layers"], {"count": 2})                # quiet: counts inline, the map in the detail file
        with open(r["detail"], encoding="utf-8") as f:
            self.assertIn("title", json.load(f)["layers"])
        self.assertEqual(len(self.ctx.pastes), 1)
        with self.assertRaises(OpError):
            self.build(d)                                         # exists: refuse
        r2 = self.build(d, replace=True)
        self.assertTrue(any("replaced" in n for n in r2["notes"]))
        self.assertEqual(self.comp.tools["MediaOut1"].ins["Input"], ("src", "T_Out"))

    def test_export_and_drift(self):
        d = mini()
        self.build(d)
        r = OPS["scene.export"].fn(self.ctx, self.comp, {})
        self.assertEqual(r["scenes"]["T"], d)
        self.comp.tools["T_title_Src"].ins["Size"] = 0.5          # a hand edit
        r = OPS["scene.export"].fn(self.ctx, self.comp, {"scene": "T", "drift": True})
        ch = r["drift"]["T"]["changed"]
        self.assertEqual([(x["tool"], x["input"]) for x in ch], [("T_title_Src", "Size")])

    @needs_tsv
    def test_drift_ignores_defaults_omitted_by_copy(self):
        d = mini()
        self.build(d)
        self.comp.tools["T_BG"].ins.pop("TopLeftAlpha", None)      # CopySettings leaves out inputs at their default
        self.comp.tools["T_title_Src"].ins.pop("CenterOnBaseOfFirstLine", None)
        r = OPS["scene.export"].fn(self.ctx, self.comp, {"scene": "T", "drift": True})
        ch = [(x["tool"], x["input"]) for x in r["drift"]["T"]["changed"]]
        self.assertNotIn(("T_BG", "TopLeftAlpha"), ch)                 # 1 = the default
        self.assertIn(("T_title_Src", "CenterOnBaseOfFirstLine"), ch)  # 1 != the default 0: a real change

    def test_update_restyle_retime_add_remove(self):
        d = mini()
        self.build(d)
        up = OPS["scene.update"].fn
        r = up(self.ctx, self.comp, {"scene": "T", "edits": [{"layer": "title", "set": {"text.content": "Hallo"}}]})
        self.assertEqual(r["counts"]["set"], 1)
        self.assertEqual(self.comp.tools["T_title_Src"].ins["StyledText"], "Hallo")
        self.assertEqual(json.loads(self.comp.tools["T_Out"].data[sg.ROOT_KEY])["layers"][1]["text"]["content"], "Hallo")
        r = up(self.ctx, self.comp, {"scene": "T", "edits": [{"layer": "box", "keys": {"position": [[4, [960, 800], "out_expo"], [24, [960, 540]]]}}]})
        self.assertEqual(r["counts"]["keys"], 2)
        self.assertEqual(sorted(n for n, _ in self.splines), ["T_boxCenterPathX_R", "T_boxCenterPathY_R"])  # found through the renamed path
        r = up(self.ctx, self.comp, {"scene": "T", "edits": [{"add": {"id": "dot", "type": "ellipse", "size": [40, 40]}, "after": "box"}]})
        self.assertIn("T_dot", self.comp.tools)
        self.assertEqual(self.comp.tools["T_title"].ins["Background"], ("src", "T_dot"))
        self.assertEqual(self.comp.tools["T_dot"].ins["Background"], ("src", "T_box"))   # rewired after the paste dropped it
        r = up(self.ctx, self.comp, {"scene": "T", "edits": [{"remove": "dot"}]})
        self.assertNotIn("T_dot", self.comp.tools)
        self.assertEqual(self.comp.tools["T_title"].ins["Background"], ("src", "T_box"))
        r = up(self.ctx, self.comp, {"scene": "T", "edits": [{"scene": {"quality": "final"}}]})
        self.assertEqual(self.comp.tools["T_CTRL"].ins["Draft"], 0)
        dry = up(self.ctx, self.comp, {"scene": "T", "edits": [{"remove": "title"}], "dryRun": True})
        self.assertTrue(dry["dryRun"])
        self.assertIn("T_title", self.comp.tools)

    def test_update_diff_mode_and_grain_rewires_mediaout(self):
        d = mini()
        self.build(d)
        d2 = dict(d, grain={"strength": 0.01})
        OPS["scene.update"].fn(self.ctx, self.comp, {"scene": "T", "description": d2})
        self.assertEqual(self.comp.tools["T_Out"].reg, "FilmGrain")
        self.assertEqual(self.comp.tools["MediaOut1"].ins["Input"], ("src", "T_Out"))

    def test_scene_ops_registered(self):
        for n in ("scene.schema", "scene.plan", "scene.diff", "scene.read", "scene.build", "scene.export", "scene.update"):
            self.assertIn(n, OPS)
        self.assertTrue(OPS["scene.build"].extra.get("paste"))
        self.assertTrue(OPS["scene.plan"].offline)


# ---------------------------------------------------------------- efficiency lab follow-ups (SCENE_BUILDER_CHANGES.md)

class EfficiencyLab(unittest.TestCase):
    def test_shift_moves_time_valued_spline_values(self):
        c = comp(mini())
        c.g.add("T_Warp", "BezierSpline", {}, keys=[{"f": 0, "v": 0, "RH": (4, 3)}, {"f": 10, "v": 12, "LH": (6, 9)}])
        c.g.add("T_WarpTS", "TimeStretcher", {"SourceTime": sg.Src("T_Warp", "Value")}, pos=(0, 0))
        before = [dict(k) for k in c.g.t["T_boxCenterPathY"]["keys"]]
        c.shift(100)
        w = c.g.t["T_Warp"]["keys"]
        self.assertEqual([(k["f"], k["v"]) for k in w], [(100, 100), (110, 112)])   # times AND values moved
        self.assertEqual(w[0]["RH"], (104, 103))
        self.assertEqual(w[1]["LH"], (106, 109))
        after = c.g.t["T_boxCenterPathY"]["keys"]
        self.assertEqual([k["v"] for k in after], [k["v"] for k in before])        # ordinary splines: values untouched

    def test_never_visible_region_stays_outside_after_shift(self):
        d = mini(start=100)
        d["layers"][1]["opacity"] = 0
        c = comp(d)
        self.assertEqual(c.regions["T_title"], [-2, -1])
        d["layers"][1].update({"opacity": 100, "in": 10, "out": 30})
        self.assertEqual(comp(d).regions["T_title"], [109, 130])

    def test_renderer_quality_not_used_under_accumulation(self):
        c = comp(load_scene("showcase"))
        r3 = c.g.t["Showcase_R3D"]["inputs"]
        self.assertIn("RendererOpenGL.AccumQuality", r3)
        self.assertEqual(r3["Quality"], 1)
        self.assertTrue(any("Quality is not used under accumulation" in x for x in c.decisions))
        d = load_scene("showcase")
        d["render3d"] = {"accumQuality": 4, "mbQuality": 8}          # fewer passes than MB samples: Quality still counts
        self.assertEqual(comp(d).g.t["Showcase_R3D"]["inputs"]["Quality"], 8)

    def test_mb_form_runs_and_2d_switch(self):
        d = mini(efficiency={"mbForm": "runs", "mbThresholdPx": 0.75})
        e = comp(d).g.t["T_box"]["inputs"]["MotionBlur"].e
        self.assertIn("t >= 0 and t <=", e)
        self.assertNotIn("local q = {", e)
        self.assertIn("T_CTRL.Draft", e)
        self.assertNotIn("MotionBlur", comp(mini(efficiency={"mb2d": False})).g.t["T_box"]["inputs"])

    def test_render_ops_take_quality(self):
        for n in ("render.frame", "render.range", "render.contact_sheet", "render.compare"):
            q = [p for p in OPS[n].params if p.name == "quality"]
            self.assertTrue(q, n)
            base = {"reference": "/tmp/ref.png"} if n == "render.compare" else {}
            self.assertTrue(validate(OPS[n], dict(base, quality="draft"))[0], n)
            self.assertFalse(validate(OPS[n], dict(base, quality="proxy"))[0], n)

    def test_render_one_draft_args(self):
        from fusion_connector.ops import build as b
        calls = []

        class Sv:
            def __init__(self):
                self.ins, self.attrs = {}, {}

            def SetInput(self, k, v):
                self.ins[k] = v

            def ConnectInput(self, k, v):
                self.ins[k] = v

            def SetAttrs(self, a):
                self.attrs.update(a)

            def GetAttrs(self):
                return dict(self.attrs, TOOLS_Name=b.RENDER_SAVER)

            def Delete(self):
                raise AssertionError("the render Saver is kept, not deleted")

        class C:
            CurrentTime = 0
            data, tools = {}, {}

            def GetAttrs(self):
                return {"COMPN_RenderStart": 0, "COMPN_RenderEnd": 10}

            def GetToolList(self, sel=False, kind=None):
                return {}

            def FindTool(self, n):
                return self.tools.get(n)

            def GetData(self, k):
                return self.data.get(k)

            def SetData(self, k, v):
                self.data[k] = v

            def SetAttrs(self, a):
                pass

            def Render(self, args):
                calls.append(dict(args))
                with open("%s%04d.png" % (sv.ins["Clip"][:-4], int(args["Start"])), "wb") as fh:
                    fh.write(b"x")
                return True

        class Src:
            def GetAttrs(self):
                return {"TOOLS_Name": "X"}

        sv, added = Sv(), []

        class Ctx:
            notes, policy = [], {"auto_dismiss": False}
            resolve = type("R", (), {"GetCurrentPage": lambda self: "fusion"})()

            def add_tool(self, comp, reg, name):
                added.append(name)
                comp.tools[name] = sv
                return sv

            def connect(self, dst, iid, src, *a):
                dst.ins[iid] = src

            def source_of(self, *a):
                return None
        c = C()
        with tempfile.TemporaryDirectory() as d:
            b.render_one(Ctx(), c, Src(), 5, os.path.join(d, "f.png"), isolate=False, quality="draft")
            b.render_one(Ctx(), c, Src(), 6, os.path.join(d, "g.png"), isolate=False)
        self.assertEqual((calls[0]["HiQ"], calls[0]["MotionBlur"]), (False, False))
        self.assertNotIn("HiQ", calls[1])
        self.assertEqual(added, [b.RENDER_SAVER])                                # one Saver per comp, reused
        self.assertEqual((sv.attrs["TOOLB_PassThrough"], sv.ins["Input"]), (True, None))   # parked: Deliver cannot write through it

    def _lint(self, setup):
        c = FComp()
        ctx = FCtx(c)
        for name, reg, ins, reg_ in setup:
            t = FTool(c, name, reg)
            t.ins.update(ins)
            if reg_:
                t.attrs.update({"TOOLNT_EnabledRegion_Start": {1: reg_[0]}, "TOOLNT_EnabledRegion_End": {1: reg_[1]}})
            c.tools[name] = t
        return OPS["comp.lint_regions"].fn(ctx, c, {})

    def test_lint_film_ladder_merges_not_traps(self):
        # a trimmed Merge with a Background passes it through outside the trim (the film ladder): no trap
        r = self._lint([("BG", "Background", {}, None),
                        ("FA", "Merge", {"Background": ("src", "BG")}, (0, 29)),
                        ("FB", "Merge", {"Background": ("src", "FA")}, (30, 59)),
                        ("OUT", "Merge", {"Background": ("src", "FB")}, None)])
        self.assertEqual(r["traps"], [])

    def test_lint_black_frame_trap(self):
        r = self._lint([("R3D", "Renderer3D", {}, (10, 20)), ("M", "Merge", {"Foreground": ("src", "R3D")}, None)])
        self.assertEqual([(x["tool"], x["consumer"], x["input"]) for x in r["traps"]], [("R3D", "M", "Foreground")])
        r = self._lint([("R3D", "Renderer3D", {}, (10, 20)), ("M", "Merge", {"Foreground": ("src", "R3D")}, (10, 20))])
        self.assertTrue(r["ok"])                                     # trimmed at the consuming Merge: fine
        r = self._lint([("R3D", "Renderer3D", {}, (10, 20)), ("BM", "BitmapMask", {"Image": ("src", "R3D")}, None)])
        self.assertTrue(r["ok"])                                     # feeding a mask: fine (efficiency lab T04)
        r = self._lint([("FILM_A", "Merge", {}, (0, 50)), ("FILM_B", "Merge", {}, (40, 90))])
        self.assertEqual(r["filmOverlaps"], [["FILM_A", "FILM_B"]])

    def test_film_overlap_warning(self):
        live = SceneLive("test_build_one_call")
        live.setUp()
        try:
            live.ctx.source_of = lambda tool, iid: [tool.ins[iid][1], "Output"] if isinstance(tool.ins.get(iid), tuple) else None
            live.build(mini(), film=True)
            r = live.build(dict(mini(scene="U"), start=40), film=True)
            self.assertTrue(any("overlaps FILM_T" in w for w in r["warnings"]), r["warnings"])
        finally:
            live.tearDown()



# ---------------------------------------------------------------- cold rematch (fixes F1-F12 from the second benchmark build)

def spline_at(keys, f):
    """Value of linear/hold KeyFrames (scenegraph.spline_keys) at frame f."""
    if f <= keys[0]["f"]:
        return keys[0]["v"]
    for k0, k1 in zip(keys, keys[1:]):
        if k0["f"] <= f <= k1["f"]:
            return k0["v"] + (k1["v"] - k0["v"]) * (f - k0["f"]) / (k1["f"] - k0["f"])
    return keys[-1]["v"]


def blend_at(c, merge, f):
    v = c.g.t[merge]["inputs"].get("Blend", 1.0)
    return spline_at(c.g.t[v.op]["keys"], f) if isinstance(v, sg.Src) else v


def shows(c, merge, f):
    """What Fusion draws: the Merge is inside its enabled region AND its Blend is above 0."""
    r = c.regions.get(merge)
    return (r is None or r[0] <= f <= r[1]) and blend_at(c, merge, f) > 0


def norm(v):
    if hasattr(v, "positional"):
        v = v.positional()
    if isinstance(v, dict):
        v = [v[k] for k in sorted(v)]
    if isinstance(v, (list, tuple)):
        return [round(float(x), 6) for x in v]
    return round(float(v), 6)


class _CountTool:
    def __init__(self, comp, name):
        self.comp, self.name = comp, name

    def GetAttrs(self):
        self.comp.calls += 1
        return {"TOOLS_Name": self.name, "TOOLS_RegID": "Background"}


class _PasteComp:
    """A comp whose Execute does what the paste Lua chunk does inside Fusion; bridge calls from Python are counted."""

    def __init__(self, n):
        self.tools = {"T%d" % i: _CountTool(self, "T%d" % i) for i in range(n)}
        self.data, self.calls, self.code = {}, 0, None

    def SetData(self, k, v):
        self.data[k] = v

    def GetData(self, k):
        return self.data.get(k)

    def GetToolList(self, sel=False):
        self.calls += 1
        return dict(enumerate(self.tools.values(), 1))

    def FindTool(self, n):
        return self.tools.get(n)

    def Execute(self, code):
        from fusion_connector.luatable import LTable, parse
        self.code = code
        key = re.search(r"comp:SetData\('(\w+)', 'OK:'", code).group(1)
        path = re.search(r"bmd\.readfile\(\[\[(.+?)\]\]\)", code).group(1)
        before = set(self.tools)
        with open(path, encoding="utf-8") as f:
            tools = parse(f.read()).get("Tools")
        for n in [k for k, v in tools.items if isinstance(v, LTable)]:
            new, i = n, 0
            while new in self.tools:
                i += 1
                new = "%s_%d" % (n, i)
            self.tools[new] = _CountTool(self, new)
        added = [n for n in self.tools if n not in before]
        ren = ["%s=%s" % (m.group(1), n) for n in added for m in [re.match(r"^(.*)_\d+$", n)] if m and m.group(1) in before]
        self.data[key] = "OK:" + ",".join(added) + ";" + ",".join(ren)


class _Resolve:
    def __init__(self, comp):
        self.c = comp

    def GetVersionString(self):
        return "21.1"

    def GetCurrentPage(self):
        return "fusion"

    def Fusion(self):
        return self

    def GetCurrentComp(self):
        return self.c


class Rematch(unittest.TestCase):
    # ---- F12: a hard in-point is frame exact whatever the cull margin
    def test_hard_cut_is_frame_exact_whatever_the_margin(self):
        for margin in (0, 1, 3):
            for start in (0, 600):
                d = {"scene": "C", "size": [1920, 1080], "fps": 30, "duration": 48, "start": start, "efficiency": {"cullMargin": margin},
                     "layers": [{"id": "A", "type": "solid", "color": "#FF0000", "out": 24},
                                {"id": "B", "type": "solid", "color": "#00FF00", "in": 24}]}
                c = comp(d)
                self.assertEqual([shows(c, "C_A", start + f) for f in (22, 23, 24, 25)], [True, True, False, False], (margin, start))
                self.assertEqual([shows(c, "C_B", start + f) for f in (22, 23, 24, 25)], [False, False, True, True], (margin, start))
                vis = c.visible_frames(c.byid["B"])                          # region math: the frame before the in-point is not visible
                self.assertEqual((vis[23], vis[24]), (False, True))
                self.assertEqual(c.regions["C_B"][0], start + 24 - margin)   # the margin only culls; the Blend step is the gate

    def test_culled_layer_opacity_control_stays_live(self):
        d = mini(start=100)
        d["controls"]["fade"] = 80
        d["layers"][1].update({"in": 10, "out": 30, "opacity": "$fade"})
        e = comp(d).g.t["T_title"]["inputs"]["Blend"].e
        self.assertIn("T_CTRL.fade", e)
        self.assertIn("(time - 100) > 9.5 and (time - 100) < 29.5", e)

    # ---- F6: text mask box = [x, y, width, height] from the text origin; corners for the AE form; build == update
    def test_text_mask_box_geometry_corners_and_warning(self):
        d = mini()
        d["layers"][1].update(animators=[{"type": "cascade", "start": 5, "stagger": 0, "duration": 8, "ease": "out_expo", "from": {"y": 60}}],
                              masks=[{"shape": "rect", "box": [-20, -90, 400, 110]}])
        c = comp(d)
        m = c.g.t["T_title_Mask1"]["inputs"]
        self.assertEqual(norm(m["Center"]), norm(((200 - 20 + 200) / 1920, 1 - (300 - 90 + 55) / 1080)))
        self.assertAlmostEqual(m["Width"], 400 / 1920)
        self.assertAlmostEqual(m["Height"], 110 / 1080)
        self.assertFalse(any(isinstance(v, sg.Src) for v in m.values()))       # the reveal box stays put ...
        ky = c.g.t["T_titleCenterPathY"]["keys"]                                 # ... while the Merge rises into it
        self.assertAlmostEqual(spline_at(ky, 13), 1 - 300 / 1080)                 # rest: on its position, inside the box
        self.assertAlmostEqual(spline_at(ky, 5), 1 - 360 / 1080)                  # start: 60 px low, clipped by the box
        self.assertTrue(spline_at(ky, 5) < spline_at(ky, 7) < spline_at(ky, 13))  # mid-rise
        self.assertFalse([w for w in c.warnings if "rect mask shows" in w])
        d["layers"][1]["masks"] = [{"shape": "rect", "corners": [-20, -90, 380, 20]}]
        self.assertEqual(comp(d).g.t["T_title_Mask1"]["inputs"], m)            # corners = the same box
        d["layers"][1]["masks"] = [{"shape": "rect", "box": [-20, -90, 380, 20]}]  # corners given as a box: a 20 px band
        self.assertTrue([w for w in comp(d).warnings if "rect mask shows" in w and "corners" in w])
        for bad, where in (({"shape": "rect", "box": [0, 0, 10, 10], "corners": [0, 0, 10, 10]}, "not both"),
                           ({"shape": "rect", "box": [0, 0, -10, 10]}, "width and height"),
                           ({"shape": "rect", "corners": [10, 0, 0, 10]}, "x1 > x0")):
            d["layers"][1]["masks"] = [bad]
            self.assertTrue(any(where in i["message"] for i in sg.validate(d)), where)
        self.assertIn("[x, y, width, height]", sg._MASK["properties"]["box"]["description"])

    def test_text_mask_build_and_update_agree(self):
        target = load_scene("bench_s2")

        def heavy(d):
            return [L for L in d["assets"]["TYPE_S2"]["layers"] if L["id"] == "s2_heavy"][0]
        good = heavy(target)["masks"]
        wrong = json.loads(json.dumps(target))
        heavy(wrong)["masks"] = [{"shape": "rect", "box": [-40, -148, 1400, 47]}]
        bare = json.loads(json.dumps(target))
        heavy(bare).pop("masks")

        def state(start=None):
            live = SceneLive("test_build_one_call")
            live.setUp()
            try:
                live.build(start or target)
                if start is not None:
                    OPS["scene.update"].fn(live.ctx, live.comp, {"scene": "S2", "edits": [{"layer": "s2_heavy", "set": {"masks": good}}]})
                t = live.comp.tools
                return {k: norm(t["S2_s2_heavy_Mask1"].ins[k]) for k in ("Center", "Width", "Height")}, t["S2_s2_heavy"].ins.get("EffectMask")
            finally:
                live.tearDown()
        want = state()
        self.assertEqual(want[1], ("src", "S2_s2_heavy_Mask1"))
        self.assertEqual(state(wrong), want)      # a wrong box fixed by scene.update = a fresh build
        self.assertEqual(state(bare), want)       # a mask added by scene.update = a fresh build

    # ---- F2: one asset at two scales
    @needs_tsv
    def test_asset_at_two_scales_gets_its_own_names(self):
        d = mini()
        d["assets"] = {"POSTER": {"size": [480, 270], "layers": [{"id": "sky", "type": "rect", "size": [480, 270], "fill": "#3366FF"},
                                                                 {"id": "sun", "type": "ellipse", "size": [60, 60], "fill": "#FFCC00",
                                                                  "position": [360, 90], "keys": {"opacity": [[0, 0], [10, 100]]}}]},
                       "WALL": {"size": [960, 540], "layers": [{"id": "wp", "type": "group", "use": "POSTER", "position": [480, 270]}]}}
        d["layers"] += [{"id": "big", "type": "group", "use": "POSTER", "position": [500, 500]},
                        {"id": "small", "type": "group", "use": "POSTER", "position": [1400, 500], "scale": 50},
                        {"id": "small2", "type": "group", "use": "POSTER", "position": [1400, 800], "scale": 50},
                        {"id": "w1", "type": "group", "use": "WALL", "position": [960, 540], "scale": 80},
                        {"id": "w2", "type": "group", "use": "WALL", "position": [960, 540], "scale": 40}]
        c = comp(d)
        self.assertEqual(len(c.g.order), len(set(c.g.order)))
        v = validate_setting_text(c.g.text())
        self.assertTrue(v["ok"], v["problems"][:5])
        self.assertIn("T_A_POSTER_Base", c.g.t)
        self.assertIn("T_POSTER_v2_A_POSTER_Base", c.g.t)                       # the 50 % raster
        self.assertEqual(sum(1 for n in c.g.t if n.endswith("_A_POSTER_Base")), 4)   # 100, 50 (shared by small2), 80, 40
        self.assertIn("T_WALL_v2_A_WALL_Base", c.g.t)
        self.assertEqual(comp(d).g.order, c.g.order)                             # deterministic
        d2 = json.loads(json.dumps(d))
        d2["layers"][3]["scale"] = 60
        self.assertIn("set", sg.diff(c, comp(d2)))                               # a re-scale edits the variant in place

    # ---- F7: non-uniform scale inside a supersampled container
    def test_nonuniform_scale_carries_the_container_texture_scale(self):
        d = mini()
        d["assets"] = {"CHIP": {"size": [800, 200], "layers": [
            {"id": "chip", "type": "rect", "size": [369, 26], "anchor": [0, 13], "position": [20, 100], "fill": "#FFFFFF",
             "keys": {"scale": [[0, [0, 100]], [6, [100, 100]]]}},
            {"id": "frame", "type": "group", "size": [300, 100], "position": [400, 100], "scale": [91.67, 92.6],
             "layers": [{"id": "frame_fill", "type": "rect", "size": [300, 100], "fill": "#FF0000", "keys": {"opacity": [[0, 0], [4, 100]]}}]}]}}
        d["layers"].append({"id": "card", "type": "group", "use": "CHIP", "position": [960, 540], "scale": 200})
        c = comp(d)
        self.assertAlmostEqual(c.g.t["T_chip_ScaleXSize"]["keys"][-1]["v"], 1.0)   # rasterized at 2x: 1.0 at rest, not 0.5
        self.assertAlmostEqual(c.g.t["T_chip_ScaleYSize"]["keys"][0]["v"], 1.0)
        fr = c.g.t["T_frame_Scale"]["inputs"]
        self.assertAlmostEqual(fr["YSize"], 1.0)                                  # raster at the larger scale, shrunk in X only
        self.assertAlmostEqual(fr["XSize"], 91.67 / 92.6)

    # ---- F9: paste time must not grow with the comp
    def test_paste_name_diff_runs_inside_fusion(self):
        from fusion_connector.ops.base import Ctx
        pc = _PasteComp(300)
        ctx = Ctx()
        ctx._resolve = _Resolve(pc)
        res = ctx.paste(pc, "{ Tools = ordered() { A = Background { }, T5 = Background { }, }, }")
        self.assertEqual(res["added"], ["A", "T5_1"])
        self.assertEqual(res["renamed"]["T5"], "T5_1")
        self.assertEqual(pc.calls, 0)                                             # no per-tool bridge reads of the 300 existing tools
        self.assertIn("n:match('^(.*)_%d+$')", pc.code)
        with self.assertRaises(OpError):
            ctx.paste(pc, '{ Tools = ordered() { B = TextPlus { Inputs = { StyledText = Input { Value = "a\nb" } } } } }')

    def test_film_build_does_not_scan_the_comp(self):
        live = SceneLive("test_build_one_call")
        live.setUp()
        try:
            live.ctx.source_of = lambda tool, iid: [tool.ins[iid][1], "Output"] if isinstance(tool.ins.get(iid), tuple) else None
            calls = []
            for i in range(400):
                t = FTool(live.comp, "Hand%d" % i, "Background")
                t.GetAttrs = lambda t=t: calls.append(t.name) or {"TOOLS_Name": t.name, "TOOLS_RegID": "Background"}
                live.comp.tools[t.name] = t
            live.build(mini(), film=True)
            r = live.build(dict(mini(scene="U"), start=40), film=True)
            self.assertEqual(calls, [])
            self.assertTrue(any("overlaps FILM_T" in w for w in r["warnings"]))
            self.assertEqual(live.comp.tools["FILM_U"].ins["Background"], ("src", "FILM_T"))
        finally:
            live.tearDown()

    # ---- F3, F4, F5, F8
    def test_duplicate_ids_across_assets_say_why(self):
        d = mini(assets={"P1": {"size": [100, 100], "layers": [{"id": "Sky", "type": "solid", "color": "#0000FF"}]},
                         "P2": {"size": [100, 100], "layers": [{"id": "Sky", "type": "solid", "color": "#0000FF"}]}})
        msg = [i["message"] for i in sg.validate(d) if "duplicate" in i["message"]][0]
        self.assertIn("one namespace across the scene and every asset", msg)
        self.assertIn("'P2_Sky'", msg)

    def test_preview_survives_tiny_rounded_boxes(self):
        d = mini()
        d["layers"].append({"id": "dot", "type": "rect", "size": [9, 6], "radius": 2, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 1},
                            "position": [100, 100]})
        with tempfile.TemporaryDirectory() as tmp:
            sg.preview(comp(d), [0, 30], 480, os.path.join(tmp, "p.png"))
            self.assertTrue(os.path.getsize(os.path.join(tmp, "p.png")) > 0)

    def test_mixed_scale_keys_and_key_value_paths(self):
        d = mini()
        d["layers"][1]["keys"] = {"scale": [[0, 50], [10, [100, 80]]]}
        c = comp(d)
        self.assertAlmostEqual(c.g.t["T_title_ScaleXSize"]["keys"][0]["v"] / c.g.t["T_title_ScaleYSize"]["keys"][0]["v"], 1.0)
        self.assertEqual(c.authored["layers"][1]["keys"]["scale"][0], [0, 50])    # stored as authored
        d["layers"][0]["keys"]["position"][0][1] = 5
        with self.assertRaises(sg.SceneError) as e:
            comp(d)
        self.assertIn("layers/0/keys/position/0/1", e.exception.message)

    def test_quiet_plan_and_build_are_compact(self):
        with Env(FUSION_MCP_OUT_DIR=tempfile.mkdtemp()):
            full = OPS["scene.plan"].fn({"description": load_scene("bench_s2")})
            q = OPS["scene.plan"].fn({"description": load_scene("bench_s2"), "quiet": True})
            self.assertLess(len(json.dumps(q)), 4000)
            self.assertLess(len(json.dumps(q)), len(json.dumps(full)) / 2)
            self.assertEqual(q["decisions"]["count"], len(full["decisions"]))
            with open(q["detail"], encoding="utf-8") as f:
                self.assertEqual(json.load(f)["decisions"], full["decisions"])

    # ---- feature gap: a shape size animation motion-blurs [sb3: through a Transform scale; the Merge's own MB did not blur it live]
    def test_size_animation_gets_motion_blur(self):
        d = mini()
        d["layers"].append({"id": "bar", "type": "rect", "size": [100, 20], "fill": "#FFFFFF", "position": [960, 900],
                            "keys": {"size": [[30, [100, 20], "in_out"], [40, [900, 20]]]}})
        t = comp(d).g.t
        table = [int(x) for x in re.search(r"\{([01,]+)\}", t["T_bar_SizeMB"]["inputs"]["MotionBlur"].e).group(1).split(",")]
        self.assertEqual(table[29], 0)
        self.assertEqual(table[35], 1)
        self.assertEqual(table[45], 0)
        self.assertNotIn("MotionBlur", t["T_bar"]["inputs"])       # the bar does not move: its Merge stays unblurred


# ---------------------------------------------------------------- disk caches (cache.*, efficiency lab DISK/FREEZE loop)

class CComp(FComp):
    def __init__(self):
        super().__init__()
        self.data = {}
        self.attrs = {"COMPN_RenderStart": 0, "COMPN_RenderEnd": 9, "COMPS_Name": "Composition1"}

    def SetData(self, k, v):
        self.data[k] = v

    def GetData(self, k):
        return self.data.get(k)

    def GetAttrs(self):
        return dict(self.attrs)

    def CopySettings(self, t):   # what the bridge hands back (live, 21.1): no tools, so it can't fingerprint anything
        return {"Tools": None, "ActiveTool": t.name}


def _setting_of(comp, names):
    """.setting text of the listed tools, like bmd.writestring(comp:CopySettings(list))."""
    parts = []
    for n in names:
        t = comp.tools.get(n)
        if t is None:
            continue
        ins = ['%s = Input { SourceOp = "%s", Source = "Output", }' % (k, v[1]) if isinstance(v, tuple) else
               "%s = Input { Value = %s, }" % (k, json.dumps(v)) for k, v in t.ins.items() if v is not None]
        ins += ["%s = Input { Expression = %s, }" % (k, json.dumps(e)) for k, e in t.expr.items()]
        parts.append("%s = %s { Inputs = { %s }, ViewInfo = OperatorInfo { Pos = { %s, 0 } }, }," % (n, t.reg, ", ".join(ins), getattr(t, "pos", 0)))
    return "{ Tools = ordered() { %s } }" % " ".join(parts)


def _save_settings(self, path):   # tool.SaveSettings over the bridge: the tool's .setting text (inputs, expressions, UI state)
    with open(path, "w", encoding="utf-8") as f:
        f.write(_setting_of(self.comp, [self.name]))
    return True


FTool.SaveSettings = _save_settings


class CCtx(FCtx):
    """FCtx plus what cache.* uses; lua() does inside Python what the two cache chunks do inside Fusion."""

    def __init__(self, comp):
        super().__init__(comp)
        self.current, self.policy = True, {}
        self.resolve = type("R", (), {"GetCurrentPage": lambda s: "fusion", "OpenPage": lambda s, p: None})()

    def is_current(self, comp):
        return self.current

    def set_input(self, comp, t, iid, v):
        t.ins[iid] = v
        return v

    def add_tool(self, comp, reg, name=None, x=None, y=None):
        return comp.tools.setdefault(name, FTool(comp, name, reg))

    def lua(self, comp, code, wait=5.0):
        if "local seen, order, stack" in code:
            stack, seen, order = [re.search(r'comp:FindTool\("(\w+)"\)', code).group(1)], set(), []
            while stack:
                n = stack.pop()
                t = comp.tools.get(n)
                if t is None or n in seen:
                    continue
                seen.add(n)
                order.append(n)
                stack += [v[1] for v in t.ins.values() if isinstance(v, tuple)]
                stack += [m for e in t.expr.values() for m in re.findall(r"([A-Za-z_]\w*)\.", e)]
            return ",".join(order)
        names = json.loads("[%s]" % re.search(r"ipairs\(\{(.*?)\}\)", code).group(1))
        with open(re.search(r"io\.open\(\[\[(.+?)\]\]", code).group(1), "w", encoding="utf-8") as f:
            f.write(_setting_of(comp, names))
        return str(len(names))


def _fake_render(ctx, comp, t, frame, out_path, frames=None, isolate=True, quality="final"):
    """render_one stand-in: one PNG per frame whose bytes carry the branch's state (so a refresh really rewrites them)."""
    out = []
    for f in frames:
        p = os.path.join(os.path.dirname(out_path), "fc_x_%04d.png" % int(f))
        with open(p, "w") as fh:
            fh.write(_setting_of(comp, [n for n in comp.tools]))
        out.append((f, p))
    return out


class DiskCache(unittest.TestCase):
    def setUp(self):
        from fusion_connector.ops import cache as cm
        self.cm, self.saved = cm, cm.render_one
        cm.render_one = _fake_render
        self.root = os.path.realpath(tempfile.mkdtemp())
        self.env = Env(FUSION_MCP_CACHE_DIR=self.root)
        self.env.__enter__()
        c = self.comp = CComp()
        for n, reg in (("CTRL", "Custom"), ("BG", "Background"), ("Blur", "Blur"), ("Base", "Background"), ("M", "Merge")):
            c.tools[n] = FTool(c, n, reg)
        c.tools["CTRL"].ins["Amount"] = 3
        c.tools["BG"].ins["TopLeftRed"] = 0.5
        c.tools["Blur"].ins["Input"] = ("src", "BG")
        c.tools["Blur"].expr["XBlurSize"] = "CTRL.Amount * 2"
        c.tools["M"].ins.update(Background=("src", "Base"), Foreground=("src", "Blur"))
        c.tools["MediaOut1"].ins["Input"] = ("src", "M")
        self.ctx = CCtx(c)

    def tearDown(self):
        self.cm.render_one = self.saved
        self.env.__exit__()

    def op(self, name, **a):
        return OPS[name].fn(self.ctx, self.comp, a)

    def test_to_disk_swaps_a_loader_in_and_keeps_the_branch(self):
        r = self.op("cache.to_disk", tool="Blur", start=0, end=4)
        t = self.comp.tools
        d = os.path.join(self.root, "project", "timeline", "Composition1", "Blur")
        self.assertEqual(r["dir"], d)
        self.assertEqual(sorted(os.listdir(d)), ["Blur_r1_%04d.png" % f for f in range(5)])
        ld = t["Blur_Cache"]
        self.assertEqual((ld.reg, ld.ins["Clip"], ld.ins["GlobalIn"], ld.ins["GlobalOut"]), ("Loader", os.path.join(d, "Blur_r1_0000.png"), 0, 4))
        self.assertEqual(t["M"].ins["Foreground"], ("src", "Blur_Cache"))       # consumers read the Loader ...
        self.assertEqual(t["Blur"].ins["Input"], ("src", "BG"))                 # ... the live branch stays intact
        e = json.loads(self.comp.data["fc_cache"])["Blur"]
        self.assertEqual(set(e["upstream"]), {"Blur", "BG", "CTRL"})           # wiring AND the expression's CTRL
        self.assertEqual(e["rewired"], [["M", "Foreground"]])
        self.assertEqual(set(e["fp"]), {"lua", "bridge"})
        with self.assertRaises(OpError):
            self.op("cache.to_disk", tool="Blur")                               # already cached
        with self.assertRaises(OpError):
            self.op("cache.to_disk", tool="CTRL")                               # nothing consumes it (an expression is no wire)

    def test_default_range_is_the_consumers_regions(self):
        self.comp.tools["M"].attrs.update({"TOOLNT_EnabledRegion_Start": {1: 3}, "TOOLNT_EnabledRegion_End": {1: 6}})
        r = self.op("cache.to_disk", tool="Blur")
        self.assertEqual((r["range"], r["warnings"]), ([3, 6], []))
        self.op("cache.restore", tool="Blur")
        r = self.op("cache.to_disk", tool="Blur", start=4, end=5)                # a consumer active outside the range: warned
        self.assertTrue(any("outside 4-5" in w for w in r["warnings"]))
        self.op("cache.restore", tool="Blur")
        self.comp.tools["M"].attrs.clear()                                     # unbounded consumer, whole comp range: fine
        self.assertEqual(self.op("cache.to_disk", tool="Blur")["warnings"], [])

    def test_stale_on_upstream_edits_not_on_node_moves(self):
        self.op("cache.to_disk", tool="Blur", start=0, end=2)
        for current in (True, False):                                          # lua on the Fusion page, bridge elsewhere
            self.ctx.current = current
            st = self.op("cache.status")
            self.assertEqual((st["stale"], st["caches"][0]["via"], st["caches"][0]["framesOnDisk"]), ([], "lua" if current else "bridge", 3))
            self.comp.tools["BG"].pos = 7                                      # moved in the flow: not an edit
            self.assertEqual(self.op("cache.status")["stale"], [])
            self.comp.tools["CTRL"].ins["Amount"] = 4                           # an expression's source changed
            self.assertEqual(self.op("cache.status")["caches"][0]["changed"], ["CTRL"])
            self.comp.tools["CTRL"].ins["Amount"] = 3
            self.comp.tools["BG"].ins["TopLeftRed"] = 0.9                       # a static value upstream
            self.assertEqual(self.op("cache.status")["caches"][0]["changed"], ["BG"])
            self.comp.tools["BG"].ins["TopLeftRed"] = 0.5
        self.comp.tools["Blur"].ins["Input"] = ("src", "Base")                  # rewired upstream
        self.assertTrue(self.op("cache.status")["caches"][0]["stale"])

    def test_refresh_rerenders_a_new_revision(self):
        self.op("cache.to_disk", tool="Blur", start=0, end=2)
        self.assertEqual(self.op("cache.refresh")["refreshed"], [])            # fresh: nothing to do
        self.comp.tools["BG"].ins["TopLeftRed"] = 0.9
        r = self.op("cache.refresh")
        self.assertEqual([x["rev"] for x in r["refreshed"]], [2])
        d = os.path.join(self.root, "project", "timeline", "Composition1", "Blur")
        self.assertEqual(sorted(os.listdir(d)), ["Blur_r2_%04d.png" % f for f in range(3)])   # old revision deleted
        self.assertEqual(self.comp.tools["Blur_Cache"].ins["Clip"], os.path.join(d, "Blur_r2_0000.png"))
        self.assertEqual(self.op("cache.status")["stale"], [])

    def test_restore_and_clear_stay_inside_the_root(self):
        self.op("cache.to_disk", tool="Blur", start=0, end=1)
        with self.assertRaises(OpError):
            self.op("cache.clear", tool="Blur")                                # active: its Loader reads these files
        r = self.op("cache.restore", tool="Blur")
        t = self.comp.tools
        self.assertEqual((t["M"].ins["Foreground"], "Blur_Cache" in t, self.comp.data["fc_cache"]), (("src", "Blur"), False, ""))
        self.assertEqual(r["rewired"], [["M", "Foreground"]])
        r = self.op("cache.clear", tool="Blur")
        self.assertEqual(len(r["deleted"]), 1)
        self.assertFalse(os.path.exists(os.path.join(self.root, "project", "timeline", "Composition1", "Blur")))
        outside = tempfile.mkdtemp()
        self.assertFalse(self.cm._inside_root(outside))
        self.assertFalse(self.cm._inside_root(self.root))                      # never the root itself
        self.assertEqual(self.cm._delete_files({"dir": outside, "pattern": "X_r1_%04d.png"}), 0)

    def test_render_and_deliver_warn_on_stale(self):
        from fusion_connector.ops.build import cache_warnings
        self.assertEqual(cache_warnings(self.ctx, self.comp), [])              # no caches: nothing (one GetData)
        self.op("cache.to_disk", tool="Blur", start=0, end=1)
        self.assertEqual(cache_warnings(self.ctx, self.comp), [])
        self.comp.tools["BG"].ins["TopLeftRed"] = 0.9
        w = cache_warnings(self.ctx, self.comp)
        self.assertTrue(w and "Blur_Cache is STALE" in w[0] and "BG" in w[0])
        comp, started = self.comp, []
        item = type("I", (), {"GetName": lambda s: "clip", "GetFusionCompCount": lambda s: 1, "GetFusionCompByIndex": lambda s, i: comp})()
        tl = type("T", (), {"GetName": lambda s: "TL", "GetTrackCount": lambda s, k: 1, "GetItemListInTrack": lambda s, k, n: [item]})()

        class Proj:
            def GetRenderJobList(self):
                return {1: {"JobId": "j1", "TimelineName": "TL"}}

            def GetTimelineCount(self):
                return 1

            def GetTimelineByIndex(self, i):
                return tl

            def StartRendering(self, ids=None):
                started.append(ids)
                return True

            def IsRenderingInProgress(self):
                return False

            def GetRenderJobStatus(self, j):
                return {"JobStatus": "Rendering"}
        self.ctx.project = lambda: Proj()
        with self.assertRaises(OpError) as e:
            OPS["deliver.start"].fn(self.ctx, {"jobIds": ["j1"], "overwrite": True})
        self.assertEqual(e.exception.code, "FORBIDDEN")
        self.assertEqual(e.exception.details["staleCaches"][0]["cache"], "Blur_Cache")
        sv = comp.tools["FC_RenderSaver"] = FTool(comp, "FC_RenderSaver", "Saver")   # left live by an interrupted render
        sv.ins["Input"] = ("src", "M")
        r = OPS["deliver.start"].fn(self.ctx, {"jobIds": ["j1"], "overwrite": True, "confirm": True})
        self.assertEqual((started, r["staleCaches"][0]["changed"]), ([["j1"]], ["BG"]))
        self.assertEqual((sv.attrs.get("TOOLB_PassThrough"), sv.ins["Input"]), (True, None))   # parked before Deliver

    def test_settle_render_no_modal_costs_nothing_modal_path_still_dismisses(self):
        import time as _t
        from fusion_connector.ops import build as b
        saved, calls, page = b.dismiss_modals, [], {"v": "fusion"}
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            ctx = type("C", (), {"resolve": type("R", (), {"GetCurrentPage": lambda s: page["v"]})()})()
            try:
                b.dismiss_modals = lambda **k: calls.append(k) or (0, [])
                t0 = _t.time()
                self.assertEqual(b.settle_render(ctx, [f.name], True), (0, [], True))
                self.assertLess(_t.time() - t0, 0.2)                            # no modal: no 4 s wait, no osascript
                self.assertEqual(calls, [])

                def modal(**k):                                                 # 'Render completed!' up: scripting answers None
                    calls.append(k)
                    page["v"] = "fusion"
                    return 1, []
                page["v"], b.dismiss_modals = None, modal
                self.assertEqual(b.settle_render(ctx, [f.name], True), (1, [], True))
                page["v"], b.dismiss_modals = None, lambda **k: (0, ["WARNING! Render did not complete!"])
                self.assertEqual(b.settle_render(ctx, [f.name], True)[1], ["WARNING! Render did not complete!"])
            finally:
                b.dismiss_modals = saved



# ---------------------------------------------------------------- scene builder pass 3

from tests import luajit  # noqa: E402

# The paste chunk before pass 3 (names before + after the paste): the baseline of the call-count curve.
OLD_PASTE_LUA = """
local function nameof(t) local ok, a = pcall(function() return t:GetAttrs() end) if ok and a then return a.TOOLS_Name end end
local before = {}
for _, t in pairs(comp:GetToolList(false)) do local n = nameof(t) if n then before[n] = true end end
local s = bmd.readfile([[%s]])
comp:SetActiveTool(nil) comp:Lock()
local okp, perr = pcall(function() comp:Paste(s) end)
comp:Unlock() comp:SetActiveTool(nil)
local added = {}
for _, t in pairs(comp:GetToolList(false)) do local n = nameof(t) if n and not before[n] then added[#added + 1] = n end end
result = table.concat(added, ',') .. ';'
"""


def _tmpfile(text, suffix):
    fd, p = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def lua_repaste(L, spec, text):
    """Run the real REPASTE_LUA in LuaJIT against the mock comp -> repaste()'s parsed result (or raises on ERR)."""
    from fusion_connector.ops.base import lua_wrap
    sp = _tmpfile(sops._lua_lit(spec), ".lua")
    pp = _tmpfile(text, ".setting") if text else ""
    try:
        st = L.execute(lua_wrap(sops.REPASTE_LUA % (sp, pp), "k"), "k")
    finally:
        os.unlink(sp)
        if pp:
            os.unlink(pp)
    if not st.startswith("OK:"):
        raise RuntimeError(st)
    counts, miss, probs, found = (st[3:].split("\n") + ["", "", ""])[:4]
    d, m, n = (int(x) for x in counts.split(","))
    return {"deleted": d, "modifiers": m, "pasted": n, "missing": [x for x in miss.split(",") if x],
            "problems": [x for x in probs.split(";") if x], "splines": dict(x.split("=", 1) for x in found.split(",") if "=" in x)}


def ln(L, expr):
    return L.run("return tostring(" + expr + ")")


@unittest.skipUnless(luajit.available(), "LuaJIT (inside DaVinci Resolve.app) not found")
class SB3PasteCost(unittest.TestCase):
    """Item 1: paste and update cost follows the pasted set, not the comp. The chunks run in LuaJIT against a mock comp that counts
    API calls; a live timing curve is tests/sb3_live.py stage 'paste'."""

    def setUp(self):
        self.text = "{ Tools = ordered() { %s } }" % " ".join(
            "P%d = Background { Inputs = { Width = Input { Value = 16, }, }, }," % i for i in range(50))
        self.path = _tmpfile(self.text, ".setting")
        self.names = ["P%d" % i for i in range(50)]

    def tearDown(self):
        os.unlink(self.path)

    def paste_calls(self, code, n):
        from fusion_connector.ops.base import lua_wrap
        L = luajit.Lua()
        try:
            L.fill(n)
            L.reset_calls()
            st = L.execute(lua_wrap(code, "k"), "k")
            return st, L.calls()
        finally:
            L.close()

    def test_paste_chunk_cost_does_not_grow_with_the_comp(self):
        from fusion_connector.ops.base import PASTE_LUA, lua_list
        curve = {}
        for n in (0, 1000, 2000):
            st, new = self.paste_calls(PASTE_LUA % (lua_list(self.names), self.path), n)
            self.assertTrue(st.startswith("OK:P") and st.count(",") == 49 and st.endswith(";;"), st[:80])
            _, old = self.paste_calls(OLD_PASTE_LUA % self.path, n)
            curve[n] = (old.get("GetAttrs", 0), new.get("GetAttrs", 0) + new.get("GetToolList", 0), new.get("FindTool", 0))
        self.assertEqual([curve[n][0] for n in (0, 1000, 2000)], [50, 2050, 4050])   # before: every tool, twice
        self.assertEqual({curve[n][1:] for n in curve}, {(0, 100)})                  # now: 2 FindTool per pasted name, flat

    def test_paste_collision_falls_back_to_the_diff_and_reports_renames(self):
        from fusion_connector.ops.base import PASTE_LUA, lua_list
        from fusion_connector.ops.base import lua_wrap
        L = luajit.Lua()
        try:
            L.fill(3, prefix="P")                       # P0..P2 exist: Fusion renames the pasted ones P0_1..P2_1
            st = L.execute(lua_wrap(PASTE_LUA % (lua_list(self.names), self.path), "k"), "k")
            added, ren, miss = st[3:].split(";")
            self.assertEqual(sorted(ren.split(",")), ["P0=P0_1", "P1=P1_1", "P2=P2_1"])
            self.assertEqual(len(added.split(",")), 50)
            self.assertEqual(miss, "")
            self.assertGreater(L.calls().get("GetToolList", 0), 0)
        finally:
            L.close()

    def scene_in(self, L, d):
        c = comp(d)
        spec, text = sops.build_spec(c, None, False, False)
        r = lua_repaste(L, spec, text)
        self.assertEqual((r["pasted"], r["missing"], r["problems"]), (len(spec["names"]), [], []))
        L.run("MockNewTool('MediaOut1', 'MediaOut') MockTool('MediaOut1'):ConnectInput('Input', MockTool('%s_Out'))" % d["scene"])
        return c

    def test_update_is_one_chunk_whose_cost_follows_the_change(self):
        d = mini()
        d["layers"][1].update({"in": 10, "out": 30})
        d2 = sg.apply_edits(d, [{"layer": "title", "set": {"animators": [{"type": "cascade", "start": 2, "stagger": 1, "duration": 8,
                                                                            "from": {"y": 30, "opacity": 0}}]}},
                                {"layer": "box", "keys": {"position": None}, "in": 4},
                                {"add": {"id": "dot", "type": "ellipse", "size": [40, 40], "in": 5}, "after": "box"}])
        oc, nc = comp(d), comp(d2)
        ops = sg.diff(oc, nc)
        spec, text = sops.update_spec(oc, nc, ops, sops._summary(ops, oc, nc))
        costs = {}
        for n in (0, 1000, 2000):
            L = luajit.Lua()
            try:
                L.fill(n)
                self.scene_in(L, d)
                L.run("MockTool('T_title_Src')._pos = {41, 7}")        # hand-placed
                L.reset_calls()
                r = lua_repaste(L, spec, text)
                c = L.calls()
                costs[n] = tuple(c.get(k, 0) for k in ("GetToolList", "GetAttrs", "FindTool", "GetInputList", "Delete", "Paste"))
                self.assertEqual(r["problems"], [])
                self.assertEqual(r["modifiers"], 3)                          # T_box's Center XYPath and its X/Y splines went with it
                self.assertEqual(ln(L, "MockTool('T_boxCenterPath') == nil and MockTool('T_boxCenterPathX') == nil"), "true")
                self.assertEqual(ln(L, "MockTool('MediaOut1')._ins.Input.src._t._name"), "T_Out")
                self.assertEqual(ln(L, "MockTool('T_title')._ins.Background.src._t._name"), nc.g.t["T_title"]["inputs"]["Background"].op)
                self.assertEqual(ln(L, "MockTool('T_title')._ins.Foreground.src._t._name"), "T_title_Src")   # rewired to the re-paste
                self.assertEqual(ln(L, "MockTool('T_title_Src')._pos[1] .. ',' .. MockTool('T_title_Src')._pos[2]"), "41,7")  # kept
                self.assertEqual(ln(L, "MockTool('T_dot'):GetAttrs().TOOLNT_EnabledRegion_Start[1]"), str(nc.regions["T_dot"][0]))
                have = set(L.tools())
                self.assertEqual([x for x in nc.g.t if x not in have and not nc.g.t[x].get("owner")], [])   # every new tool is there
                self.assertEqual([x for x in oc.g.t if x not in nc.g.t and x in have], [])                  # nothing stale is left
            finally:
                L.close()
        self.assertEqual(len(set(costs.values())), 1, costs)                   # identical work at 0, 1,000 and 2,000 tools
        self.assertEqual(costs[0][0], 0)                                       # never lists the comp

    def test_a_clash_changes_nothing(self):
        d = mini()
        d2 = sg.apply_edits(d, [{"add": {"id": "dot", "type": "ellipse", "size": [40, 40], "keys": {"opacity": [[0, 0], [9, 100]]}},
                                 "after": "box"}])
        oc, nc = comp(d), comp(d2)
        ops = sg.diff(oc, nc)
        spec, text = sops.update_spec(oc, nc, ops, sops._summary(ops, oc, nc))
        self.assertNotIn("T_dot", spec["victims"])          # a new name is never a victim, so a hand-made T_dot is not deleted
        L = luajit.Lua()
        try:
            self.scene_in(L, d)
            L.run("MockNewTool('T_dot', 'Blur')")
            before = L.tools()
            with self.assertRaises(RuntimeError) as e:
                lua_repaste(L, spec, text)
            self.assertIn("CLASH:T_dot", str(e.exception))
            self.assertEqual(L.tools(), before)
            self.assertEqual(ln(L, "MockTool('T_dot')._reg"), "Blur")
        finally:
            L.close()

    def test_build_replace_of_the_same_graph_keeps_spots_and_boxes(self):
        d = mini()
        c = comp(d)
        L = luajit.Lua()
        try:
            self.scene_in(L, d)
            boxes = [b["name"] for b in c.g.underlays]
            L.run("MockTool('T_box')._pos = {12, 34}")
            spec, text = sops.build_spec(c, c.g, True, sops._same_topology(c.g, c.g))
            self.assertNotIn("Underlay", text)
            r = lua_repaste(L, spec, text)
            self.assertEqual((r["missing"], r["problems"]), ([], []))
            self.assertEqual(ln(L, "MockTool('T_box')._pos[1] .. ',' .. MockTool('T_box')._pos[2]"), "12,34")
            self.assertEqual([b for b in boxes if b + "_1" in L.tools()], [])
            self.assertEqual(ln(L, "MockTool('MediaOut1')._ins.Input.src._t._name"), "T_Out")   # the outside consumer came back
        finally:
            L.close()


class SB3UpdateHandler(unittest.TestCase):
    """scene.update / scene.build handlers on FComp (fake_repaste): the layout pass only runs when the graph changed shape."""

    def setUp(self):
        self.live = SceneLive("test_build_one_call")
        self.live.setUp()
        from fusion_connector.ops import scene as s_
        self.saved_tidy, self.tidy = s_.tidy_after, []
        s_.tidy_after = lambda ctx, comp, scene, mode, w: self.tidy.append(mode) or {"scope": "comp"}

    def tearDown(self):
        sops.tidy_after = self.saved_tidy
        self.live.tearDown()

    def test_replace_only_update_keeps_the_layout_and_never_lists_the_comp(self):
        L = self.live
        d = mini()
        L.build(d)
        self.assertEqual(self.tidy, ["build"])
        listed = []
        L.comp.GetToolList = lambda sel=False: listed.append(1) or {}
        up = OPS["scene.update"].fn
        r = up(L.ctx, L.comp, {"scene": "T", "edits": [{"layer": "title", "set": {"text.style": "Regular"}},
                                                       {"layer": "title", "set": {"animators": [{"type": "cascade", "start": 2, "stagger": 1,
                                                                                               "duration": 8, "from": {"y": 30}}]}}]})
        self.assertGreaterEqual(r["counts"]["replace"], 1)            # T_title_Src re-pasted (a Follower now drives its text)
        self.assertEqual(r["layout"], {"kept": True})
        self.assertEqual(self.tidy, ["build"])                       # same graph shape: no layout pass
        self.assertEqual(listed, [])
        r = up(L.ctx, L.comp, {"scene": "T", "edits": [{"add": {"id": "dot", "type": "ellipse", "size": [40, 40]}, "after": "box"}]})
        self.assertEqual(self.tidy, ["build", "update"])             # new tools: the house layout runs
        r = up(L.ctx, L.comp, {"scene": "T", "edits": [{"remove": "dot"}], "layout": False})
        self.assertEqual(self.tidy, ["build", "update"])

    def test_film_update_keeps_the_ladder(self):
        L = self.live
        L.ctx.source_of = lambda tool, iid: [tool.ins[iid][1], "Output"] if isinstance(tool.ins.get(iid), tuple) else None
        L.build(mini(), film=True)
        L.build(dict(mini(scene="U"), start=40), film=True)
        OPS["scene.update"].fn(L.ctx, L.comp, {"scene": "T", "description": dict(mini(), grain={"strength": 0.01})})
        self.assertEqual(L.comp.tools["T_Out"].reg, "FilmGrain")
        self.assertEqual(L.comp.tools["FILM_T"].ins["Foreground"], ("src", "T_Out"))   # the ladder input came back after the re-paste
        self.assertEqual(L.comp.tools["FILM_U"].ins["Background"], ("src", "FILM_T"))
        self.assertEqual(L.comp.tools["MediaOut1"].ins["Input"], ("src", "FILM_U"))


class SB3FreezeGuard(unittest.TestCase):
    """Item 5: the freeze optimisation never wraps a mask branch (lab rule: a frozen *Mask feeds nothing and its consumer silently
    loses its EffectMask)."""

    SCENE = {"scene": "M", "size": [1920, 1080], "fps": 30, "duration": 30, "layers": [
        {"id": "bg", "type": "solid", "color": "#222222"},
        {"id": "wipe", "type": "ellipse", "size": [400, 400], "fill": "#FFFFFF", "keys": {"position": [[0, [200, 540]], [20, [1700, 540]]]}},
        {"id": "grp", "type": "group", "size": [800, 400], "keys": {"position": [[0, [900, 540]], [20, [1000, 540]]]},
         "layers": [{"id": "g1", "type": "rect", "size": [800, 400], "fill": "#FFFFFF"},
                    {"id": "g2", "type": "rect", "size": [100, 100], "fill": "#FF0000", "keys": {"opacity": [[0, 0], [10, 100]]}}]},
        {"id": "card", "type": "rect", "size": [900, 500], "fill": "#FF8800", "matte": {"layer": "wipe"}},
        {"id": "card2", "type": "rect", "size": [900, 500], "fill": "#0088FF", "matte": {"layer": "grp", "mode": "luma"}},
        {"id": "word", "type": "text", "position": [300, 800], "text": {"content": "Rise", "font": "Helvetica Neue", "size": 90},
         "masks": [{"shape": "rect", "box": [-10, -80, 300, 100]}],
         "animators": [{"type": "cascade", "start": 3, "stagger": 0, "duration": 10, "from": {"y": 80}}]}]}

    def test_no_freeze_on_a_mask_branch(self):
        c = comp(json.loads(json.dumps(self.SCENE)))
        self.assertEqual(sg.mask_freezes(c.g), [])
        frz = [n for n, r in c.g.t.items() if r["reg"] == "TimeStretcher" and not isinstance(r["inputs"]["SourceTime"], sg.Expr)]
        self.assertIn("M_bg_Freeze", frz)                                    # ordinary freezes still happen
        self.assertIn("M_card_Src_Freeze", frz)
        for n in ("M_wipe_Src", "M_g1", "M_g2_Src"):                          # matte image chains: never frozen
            self.assertNotIn(n + "_Freeze", c.g.t)
            self.assertIn("%s: not frozen (mask branch)" % n, c.decisions)

    def test_the_guard_refuses_mask_tools_and_the_check_catches_a_regression(self):
        c = comp(mini())
        c.g.add("T_M", "RectangleMask", {}, pos=(0, 0))
        self.assertEqual(c.freeze("T_M", "test"), "T_M")                        # refused
        c.g.add("T_Bad", "TimeStretcher", {"Input": sg.Src("T_M", "Mask"), "SourceTime": 0}, pos=(0, 0))
        c.g.add("T_Img", "Background", {}, pos=(0, 0))
        c.g.add("T_Frz", "TimeStretcher", {"Input": sg.Src("T_Img"), "SourceTime": 0}, pos=(0, 0))
        c.g.add("T_BM", "BitmapMask", {"Image": sg.Src("T_Frz")}, pos=(0, 0))
        c.g.add("T_Use", "Merge", {"EffectMask": sg.Src("T_BM", "Mask")}, pos=(0, 0))
        bad = sg.mask_freezes(c.g)
        self.assertIn(("T_Bad", "T_M", "Input"), bad)
        self.assertIn(("T_Frz", "T_BM", "Image"), bad)
        self.assertIn("mask_freezes", open(sg.__file__, encoding="utf-8").read().split("def compile_scene")[1][:600])   # checked on every compile

    def test_every_example_scene_is_clean(self):
        for name in ("showcase", "kitchen_sink", "bench_s2", "push_three_worlds", "card_smart_folders", "title_low_tide"):
            self.assertEqual(sg.mask_freezes(comp(load_scene(name)).g), [], name)


class SB3SizeBlur(unittest.TestCase):
    """Item 3: size keys blur through a Transform scale whose ratio is 1 at every integer frame (rest pixels unchanged)."""

    IRIS = {"id": "iris", "type": "ellipse", "size": [52, 52], "fill": "#FF7A3D", "position": [957, 447],
            "keys": {"size": [[0, [2000, 2000], "out_expo"], [10, [52, 52]]]}}

    def scene(self, **eff):
        d = mini()
        d["layers"].append(json.loads(json.dumps(self.IRIS)))
        if eff:
            d["efficiency"] = eff
        return d

    def test_ratio_is_one_on_every_frame_and_the_shutter_sees_the_scale(self):
        c = comp(self.scene())
        t = c.g.t
        self.assertEqual(t["T_iris_Src_SizeHold"]["inputs"]["SourceTime"].e, "floor(time + 0.5)")   # the shape is held per frame
        mb = t["T_iris_SizeMB"]
        self.assertEqual(mb["reg"], "Transform")
        self.assertEqual(mb["inputs"]["Input"], sg.Src("T_iris_Src_SizeHold"))
        self.assertEqual(t["T_iris"]["inputs"]["Foreground"], sg.Src("T_iris_SizeMB"))
        tr = c.track(c.byid["iris"], "size")
        table = [int(x) for x in re.search(r"\{([01,]+)\}", mb["inputs"]["MotionBlur"].e).group(1).split(",")]
        on = [f for f, x in enumerate(table) if x]
        self.assertEqual(on[0], 0)
        self.assertTrue(7 <= len(on) <= 11, on)                                       # the frames whose size changes >= 0.75 px
        for ax in ("XSize", "YSize"):
            ks = t["T_iris_SizeMB" + ax]["keys"]
            self.assertTrue(all(k.get("lin") for k in ks))
            for f in range(-2, 30):
                self.assertAlmostEqual(spline_at(ks, f), 1.0, 9)                      # integer frames: exactly the drawn shape
            for f in on:                                                               # shutter +-0.25 f: size(t) / size(frame)
                for off in (-0.25, -0.125, 0.125, 0.25):
                    self.assertAlmostEqual(spline_at(ks, f + off), tr.at(f + off)[0] / tr.at(f)[0], 6)
            self.assertLess(spline_at(ks, 0.25), 0.9)                                  # the first frame shrinks hard across the shutter
        self.assertIn("T_CTRL.Draft > 0.5", mb["inputs"]["MotionBlur"].e)             # off in draft
        self.assertEqual(norm(mb["inputs"]["Pivot"]), norm(mb["inputs"]["Center"]))    # scales about the disc center
        self.assertEqual(sg.mask_freezes(c.g), [])

    def test_switch_off_is_the_old_graph(self):
        old = comp(self.scene(sizeBlur=False)).g
        self.assertNotIn("T_iris_SizeMB", old.t)
        self.assertNotIn("T_iris_Src_SizeHold", old.t)
        self.assertEqual(old.t["T_iris"]["inputs"]["Foreground"], sg.Src("T_iris_Src"))
        new = comp(self.scene()).g
        for n in ("T_iris_Src", "T_iris_Fill"):                                     # the shape itself is drawn the same way
            self.assertEqual((new.t[n]["reg"], new.t[n]["inputs"]), (old.t[n]["reg"], old.t[n]["inputs"]))

    def test_width_only_chip_and_matte_and_no_blur_cases(self):
        d = mini()
        d["layers"] += [{"id": "chip", "type": "rect", "size": [320, 26], "fill": "#C6F432", "position": [700, 343],
                         "keys": {"size": [[52, [0, 26], "out_expo"], [58, [320, 26]]]}},
                        {"id": "ring", "type": "ellipse", "fill": None, "stroke": {"color": "#FFE2B8", "width": 40}, "size": [40, 40],
                         "position": [960, 540], "keys": {"size": [[0, [40, 40]], [11, [2600, 2600]]]}},
                        {"id": "card", "type": "rect", "size": [900, 500], "fill": "#FF8800", "matte": {"layer": "ring"}},
                        {"id": "slow", "type": "rect", "size": [100, 100], "keys": {"size": [[0, [100, 100]], [59, [100.5, 100.5]]]}}]
        c = comp(d)
        ys = c.g.t["T_chip_SizeMBYSize"]["keys"]
        self.assertEqual({round(k["v"], 9) for k in ys}, {1.0})                     # height never changes: Y stays 1
        self.assertIn("T_ring_SizeMB", c.g.t)                                         # the matte shape blurs too
        self.assertNotIn("T_slow_SizeMB", c.g.t)                                      # under the streak threshold: no blur, no nodes
        d["motionBlur"] = False
        self.assertNotIn("T_chip_SizeMB", comp(d).g.t)


class SB3Strokes(unittest.TestCase):
    """Item 4: dashed strokes (one open sPolygon per dash, cut from the outline) and tapered strokes (a filled offset polygon);
    extra item 7: a trimmed rect/ellipse stroke is drawn from its bezier outline, and trimStart keys are honoured."""

    def poly_px(self, c, name):
        """sPolygon points back in scene px (the scene canvas is 1920 wide, sShape units are canvas-width fractions, Y up)."""
        pts = c.g.t[name]["inputs"]["Polyline"][1]
        return [(960 + p[0] * 1920, 540 - p[1] * 1920) for p in pts]

    @needs_tsv
    def test_dashes_follow_the_outline_and_the_pattern(self):
        d = mini()
        d["layers"] += [{"id": "line", "type": "path", "points": [[0, 0], [500, 0]], "closed": False, "position": [300, 900],
                         "stroke": {"color": "#FFFFFF", "width": 6, "dash": [30, 10]}},
                        {"id": "circ", "type": "ellipse", "fill": None, "size": [652, 652], "position": [960, 540],
                         "stroke": {"color": "#BDB8AE", "opacity": 60, "width": 2, "dash": [12, 8], "dashOffset": 5}}]
        c = comp(d)
        line = sorted((n for n in c.g.t if re.fullmatch(r"T_line_Dash\d+", n)), key=lambda n: int(n.rsplit("Dash", 1)[1]))
        self.assertEqual(len(line), 13)                                            # 500 px / (30 + 10) = 12.5 -> 13 dashes
        spans = [(min(p[0] for p in self.poly_px(c, n)), max(p[0] for p in self.poly_px(c, n))) for n in line]
        self.assertEqual([tuple(round(v, 3) for v in sp) for sp in spans[:3]], [(300, 330), (340, 370), (380, 410)])
        self.assertEqual(round(spans[-1][1], 3), 800)                              # the last dash is cut at the end of the line
        t = c.g.t[line[0]]["inputs"]
        self.assertEqual((t["Solid"], t["CapStyle"], t["Polyline"][0]), (0, 0, False))   # open strokes, butt caps (AE default)
        self.assertAlmostEqual(t["BorderWidth"], 6 / 1920)
        circ = [n for n in c.g.t if re.fullmatch(r"T_circ_Dash\d+", n)]
        self.assertEqual(len(circ), math.ceil((math.pi * 652) / 20 + 0.25))        # 2,048 px / 20 px period (5 px offset)
        for n in circ[:5]:
            pts = self.poly_px(c, n)
            self.assertTrue(all(abs(math.hypot(x - 960, y - 540) - 326) < 0.15 for x, y in pts))   # on the circle (kappa bezier)
            L_ = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
            self.assertLess(abs(L_ - 12), 0.05) if n != circ[0] else None
        self.assertAlmostEqual(c.g.t[circ[0]]["inputs"]["Opacity"], 0.6)
        v = validate_setting_text(c.g.text())
        self.assertTrue(v["ok"], v["problems"][:3])

    def test_trimmed_dashes_draw_on_in_order(self):
        d = mini()
        d["layers"].append({"id": "circ", "type": "ellipse", "fill": None, "size": [300, 300], "position": [960, 540],
                            "stroke": {"width": 3, "dash": [40, 20]}, "keys": {"trimEnd": [[4, 0, "out_expo"], [22, 100]]}})
        c = comp(d)
        dashes = sorted((n for n in c.g.t if re.fullmatch(r"T_circ_Dash\d+", n)), key=lambda n: int(n.rsplit("Dash", 1)[1]))
        first = [None] * len(dashes)
        for i, n in enumerate(dashes):
            wl = c.g.t[n]["inputs"]["WriteLength"]
            ks = c.g.t[wl.op]["keys"]
            self.assertAlmostEqual(spline_at(ks, 4), 0.0)
            self.assertAlmostEqual(spline_at(ks, 22), 1.0)
            first[i] = next(f for f in range(4, 23) if spline_at(ks, f) > 0)
        self.assertEqual(first, sorted(first))                                    # later dashes appear later

    def test_trimmed_ellipse_and_rect_use_their_outline_and_trim_start_keys_work(self):
        d = mini()
        d["layers"] += [{"id": "ring", "type": "ellipse", "fill": None, "size": [300, 200], "position": [960, 540],
                         "stroke": {"width": 8}, "keys": {"trimEnd": [[0, 0], [20, 100]]}},
                        {"id": "frame", "type": "rect", "fill": None, "size": [400, 200], "radius": 20, "position": [500, 300],
                         "stroke": {"width": 4}, "keys": {"trimStart": [[0, 0], [10, 50]], "trimEnd": [[0, 50], [10, 100]]}},
                        {"id": "dot", "type": "ellipse", "size": [50, 50], "fill": "#FFFFFF", "keys": {"size": [[0, [50, 50]], [9, [80, 80]]]},
                         "stroke": {"width": 2}, "trim": {"end": 50}}]
        c = comp(d)
        ring = c.g.t["T_ring_Stroke"]
        self.assertEqual(ring["reg"], "sPolygon")                                  # was sEllipse: its write-on did not draw (DEEP FIELD)
        pts = ring["inputs"]["Polyline"][1]                                         # (its own canvas: compare the points)
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[0][1], max(p[1] for p in pts))                        # starts at 12 o'clock (Y up) ...
        self.assertAlmostEqual(pts[0][0], (pts[1][0] + pts[3][0]) / 2)
        self.assertGreater(pts[1][0], pts[0][0])                                   # ... and runs clockwise on screen
        fr = c.g.t["T_frame_Stroke"]["inputs"]
        self.assertEqual(len(fr["Polyline"][1]), 8)                                # rounded rect: 8 bezier points
        wp, wl = c.g.t[fr["WritePosition"].op]["keys"], c.g.t[fr["WriteLength"].op]["keys"]
        self.assertAlmostEqual(spline_at(wp, 10), 0.5)
        self.assertAlmostEqual(spline_at(wl, 10), 0.5)
        self.assertAlmostEqual(spline_at(wl, 5), 0.5)                              # both edges move together here
        self.assertEqual(c.g.t["T_dot_Stroke"]["reg"], "sEllipse")                 # size-keyed: keeps its native size animation

    def test_taper_is_a_filled_offset_polygon(self):
        d = mini()
        d["layers"].append({"id": "rib", "type": "path", "closed": False, "position": [200, 200], "points": [[0, 0], [600, 0]],
                            "stroke": {"color": "#7E8FE0", "width": 40, "taper": {"startLength": 50, "endLength": 50}}})
        c = comp(d)
        t = c.g.t["T_rib_Taper"]["inputs"]
        self.assertEqual((t["Solid"], t["Polyline"][0]), (1, True))
        pts = self.poly_px(c, "T_rib_Taper")
        half = len(pts) // 2
        top, bot = pts[:half], pts[half:][::-1]
        widths = {round(a[0]): abs(a[1] - b[1]) for a, b in zip(top, bot)}
        self.assertAlmostEqual(widths[200], 0.0, 3)                               # pointed at both ends (width 0 %)
        self.assertAlmostEqual(widths[800], 0.0, 3)
        self.assertAlmostEqual(max(widths.values()), 40.0, 1)                      # full width in the middle
        self.assertAlmostEqual(widths[min(widths, key=lambda x: abs(x - 350))], 20.0, 0)   # linear ramp: half width at 25 %
        self.assertNotIn("T_rib_Stroke", c.g.t)

    @needs_tsv
    def test_tapered_write_on_keys_polylines_and_updates_by_replace(self):
        d = mini()
        d["layers"].append({"id": "rib", "type": "path", "closed": False, "position": [200, 500],
                            "points": [{"p": [0, 0], "out": [100, -80]}, {"p": [400, 100], "in": [-100, -80]}],
                            "stroke": {"width": 40, "taper": {"startLength": 30, "endLength": 20}},
                            "keys": {"trimEnd": [[4, 0, "out_expo"], [20, 100]]}})
        c = comp(d)
        sp = c.g.t["T_rib_TaperPolyline"]
        self.assertEqual(sp["owner"], ("T_rib_Taper", "Polyline"))
        self.assertEqual(len({len(k["poly"][1]) for k in sp["keys"]}), 1)          # one point count for every key
        self.assertEqual([k["f"] for k in sp["keys"]], list(range(4, 21)))
        text = c.g.text()
        self.assertIn("Value = Polyline { Closed = true", text)
        v = validate_setting_text(text)
        self.assertTrue(v["ok"], v["problems"][:3])
        d2 = json.loads(json.dumps(d))
        d2["layers"][-1]["keys"]["trimEnd"][1][0] = 26
        ops = sg.diff(c, comp(d2))
        self.assertIn("T_rib_Taper", ops["replace"])                               # write_spline writes numbers: re-paste instead
        self.assertFalse([k for k in ops.get("keys", []) if k["host"] == "T_rib_Taper"])

    def test_schema(self):
        d = mini()
        d["layers"][0]["stroke"] = {"width": 2, "dash": [-4, 2]}
        self.assertTrue(sg.validate(d))
        d["layers"][0]["stroke"] = {"width": 2, "taper": {"startLen": 10}}
        self.assertTrue(any("startLength" in i["message"] for i in sg.validate(d)))
        d["layers"][0]["stroke"] = {"width": 2, "dash": [0, 12], "cap": "round"}   # dots
        self.assertEqual(sg.validate(d), [])


class SB3FilmController(unittest.TestCase):
    """Extra item 8: one controller per film. controlsFrom links a scene's CTRL (Draft and same-named controls) to another scene's
    CTRL by expression; scene.update keeps the links (the compiler re-emits the same expressions) and says where to edit."""

    def test_links_and_update_keeps_them(self):
        d = dict(mini(scene="U"), controlsFrom="T", start=60)
        c = comp(d)
        ins = c.g.t["U_CTRL"]["inputs"]
        self.assertEqual(ins["Draft"], sg.Expr("T_CTRL.Draft"))
        self.assertEqual(ins["accentRed"], sg.Expr("T_CTRL.accentRed"))
        self.assertIn("U_CTRL.Draft > 0.5", json.dumps([str(v) for r in c.g.t.values() for v in r["inputs"].values()]))  # the scene reads its own CTRL
        d2 = sg.apply_edits(d, [{"scene": {"controls.accent": "#00FF00"}}, {"layer": "title", "set": {"text.content": "Hi"}}])
        ops = sg.diff(c, comp(d2))
        self.assertFalse([s_ for s_ in ops.get("set", []) if s_["tool"] == "U_CTRL"])   # the links stay: no value is set on U_CTRL
        self.assertFalse([e for e in ops.get("expr", []) if e["tool"] == "U_CTRL"])
        self.assertIn("T_CTRL", comp(mini()).g.t)                                         # the film controller is an ordinary scene CTRL

    def test_build_checks_the_film_controller(self):
        live = SceneLive("test_build_one_call")
        live.setUp()
        try:
            r = live.build(dict(mini(scene="U"), controlsFrom="T"))
            self.assertTrue(any("scene T is not in this comp" in w for w in r["warnings"]))
            live.build(mini())
            v = dict(mini(scene="V"), controlsFrom="T")
            v["controls"] = dict(v["controls"], glow=0.4)
            r = live.build(v)
            self.assertTrue(any("T_CTRL has no ['glow']" in w for w in r["warnings"]), r["warnings"])
            live.build(mini(scene="W"))
            u = OPS["scene.update"].fn(live.ctx, live.comp, {"scene": "V", "edits": [{"scene": {"quality": "final"}}]})
            self.assertTrue(any("set on scene T" in w for w in u.get("warnings", [])))
        finally:
            live.tearDown()


class SB3Placement(unittest.TestCase):
    """Extra item 9: path points are offsets from position and an anchor moves the layer (AE). Documented in the schema; a
    description that looks like it assumes otherwise gets a warning."""

    def test_schema_says_it(self):
        self.assertIn("offsets from the layer's origin", sg._LAYER_PROPS["points"]["description"])
        self.assertIn("MOVES the layer", sg._LAYER_PROPS["anchor"]["description"])

    def test_warnings_fire_only_on_the_trap(self):
        d = mini()
        d["layers"] += [{"id": "abs", "type": "path", "points": [[1400, 800], [1800, 900]], "closed": False, "position": [960, 540],
                         "stroke": {"width": 3}},
                        {"id": "ok", "type": "path", "points": [[1400, 800], [1800, 900]], "closed": False, "position": [0, 0], "stroke": {"width": 3}},
                        {"id": "anc", "type": "rect", "size": [400, 200], "position": [1800, 900], "anchor": [0, 0]},
                        {"id": "anc_ok", "type": "rect", "size": [400, 200], "position": [200, 200], "anchor": [0, 0]},
                        {"id": "piv", "type": "rect", "size": [400, 200], "position": [1800, 900], "anchor": [0, 0],
                         "keys": {"scale": [[0, 50], [10, 100]]}}]
        w = [x.split(":")[0] for x in comp(d).warnings if "(AE" in x]
        self.assertEqual(sorted(w), ["abs", "anc"])
        for name in ("showcase", "kitchen_sink", "bench_s2", "push_three_worlds", "card_smart_folders", "title_low_tide"):
            self.assertEqual([x for x in comp(load_scene(name)).warnings if "(AE" in x], [], name)


class SB3Glass(unittest.TestCase):
    """Item 2: glass (backdrop blur) on 2D layers and 2.5D cards: Blur(what is below) merged back under a BitmapMask of the layer's
    own alpha, drawn by a Merge that follows the layer's Merge by expression."""

    CARD = {"id": "card", "type": "group", "size": [600, 300], "radius": 32, "background": "#FFFFFF21", "position": [960, 540],
            "glass": {"blur": 24, "saturation": 130, "tint": "#FFFFFF1A", "opacity": 90},
            "keys": {"position": [[0, [960, 700], "out_expo"], [20, [960, 540]]], "opacity": [[0, 0], [8, 100]]}, "in": 2, "out": 50,
            "layers": [{"id": "lbl", "type": "text", "text": {"content": "Glass", "font": "Helvetica Neue", "size": 60}, "align": "center"}]}

    def scene(self, card=None, **kw):
        d = mini(**kw)
        d["layers"].insert(1, {"id": "stripes", "type": "rect", "size": [1920, 200], "fill": "#FF0044", "position": [960, 540],
                               "keys": {"position": [[0, [700, 540]], [59, [1200, 540]]]}})
        d["layers"].append(json.loads(json.dumps(card or self.CARD)))
        return d

    @needs_tsv
    def test_2d_glass_graph(self):
        c = comp(self.scene())
        t = c.g.t
        below = "T_title"
        self.assertEqual(t["T_card"]["inputs"]["Background"], sg.Src("T_card_Glass"))
        g = t["T_card_Glass"]["inputs"]
        self.assertEqual((g["Background"], g["Foreground"], g["EffectMask"]), (sg.Src(below), sg.Src("T_card_FrostTint"), sg.Src("T_card_GlassMask", "Mask")))
        bl = c.g.t[g["Blend"].op]["keys"]                                                     # the layer's fade x glass opacity 90 %
        self.assertEqual([round(spline_at(bl, f), 4) for f in (1, 2, 8, 30, 49, 50)], [0, 0.225, 0.9, 0.9, 0.9, 0])
        self.assertEqual((t["T_card_GlassMask"]["inputs"]["Low"], t["T_card_GlassMask"]["inputs"]["High"]), (0.0, 0.05))   # coverage
        self.assertEqual(t["T_card_Frost"]["inputs"]["Input"], sg.Src(below))
        self.assertAlmostEqual(t["T_card_Frost"]["inputs"]["XBlurSize"], 24 / 1.25)            # the effects.blur px convention
        self.assertAlmostEqual(t["T_card_FrostSat"]["inputs"]["Saturation"], 1.3)
        self.assertAlmostEqual(t["T_card_FrostTint"]["inputs"]["Blend"], 0x1A / 255)
        sh = t["T_card_GlassShape"]["inputs"]
        for k in ("Center", "Size", "Angle"):
            self.assertEqual(sh[k], sg.Expr("T_card.%s" % k))                                     # follows the card, whatever drives it
        self.assertNotIn("Blend", sh)                                                             # full coverage; the fade is on the Glass
        self.assertEqual(sh["Foreground"], t["T_card"]["inputs"]["Foreground"])                   # the card's own image = the shape
        self.assertEqual(sh["MotionBlur"], t["T_card"]["inputs"]["MotionBlur"])                   # smears with it
        self.assertEqual(t["T_card_GlassMask"]["inputs"]["Image"], sg.Src("T_card_GlassShape"))
        self.assertEqual(c.regions["T_card_Glass"], c.regions["T_card"])                          # culled with the layer
        self.assertEqual(sg.mask_freezes(c.g), [])
        v = validate_setting_text(c.g.text())
        self.assertTrue(v["ok"], v["problems"][:3])

    def test_masks_mattes_and_a_static_backdrop(self):
        card = dict(self.CARD, masks=[{"shape": "rect", "box": [0, 0, 300, 300]}], glass={"blur": 10})
        card.pop("keys")
        d = self.scene(card)
        d["layers"].pop(1)                                                                     # nothing below moves
        d["layers"][0].pop("keys")
        c = comp(d)
        t = c.g.t
        self.assertEqual(t["T_card_GlassShape"]["inputs"]["EffectMask"], t["T_card"]["inputs"]["EffectMask"])   # the same cut
        self.assertNotIn("T_card_FrostSat", t)
        bl = c.g.t[t["T_card_Glass"]["inputs"]["Blend"].op]["keys"]                             # in 2 / out 50 only
        self.assertEqual([spline_at(bl, f) for f in (1, 2, 49, 50)], [0, 1, 1, 0])
        self.assertTrue(t["T_card_Glass"]["inputs"]["Foreground"].op.endswith("_Freeze"))       # a static backdrop blurs once
        self.assertEqual(sg.mask_freezes(c.g), [])

    @needs_tsv
    def test_2_5d_card_and_real_3d_split(self):
        d = mini()
        d["layers"] += [{"id": "cam", "type": "camera", "zoom": 2666.7, "poi": [960, 540, 0],
                         "keys": {"position": [[0, [960, 540, -3000]], [59, [960, 540, -2600]]]}},
                        {"id": "back", "type": "rect", "size": [1600, 900], "fill": "#3366FF", "position": [960, 540, 400]},
                        dict(self.CARD, position=[960, 540, 0], keys={"opacity": [[0, 0], [8, 100]]})]
        c = comp(d)
        self.assertIn("T_card_Glass", c.g.t)
        self.assertEqual(c.g.t["T_card"]["inputs"]["Background"], sg.Src("T_card_Glass"))
        self.assertEqual(c.g.t["T_card_Frost"]["inputs"]["Input"], sg.Src("T_back"))           # blurs the card behind it
        d["layers"][-2]["rotationY"] = 20                                                     # a real 3D block: split at the card
        d["layers"].append({"id": "chip", "type": "rect", "size": [200, 40], "fill": "#C6F432", "position": [900, 600, -50]})
        c = comp(d)
        t = c.g.t
        self.assertEqual(c.stats["renderers"], 3)                                            # behind, silhouette, in front
        self.assertEqual(t["T_R3D_Mrg"]["inputs"]["Background"], sg.Src("T_title"))            # pass 1: the cards listed before
        self.assertEqual({t[i.op]["reg"] for i in t["T_R3D_Scene"]["inputs"].values() if isinstance(i, sg.Src)}, {"ImagePlane3D", "Camera3D"})
        self.assertEqual(t["T_card_Frost"]["inputs"]["Input"], sg.Src("T_R3D_Mrg"))            # frost of everything under the card
        self.assertEqual(t["T_card_GlassMask"]["inputs"]["Image"], sg.Src("T_Sil_R3D_Mrg"))     # the card alone through the camera
        self.assertEqual(t["T_Sil_R3D_Mrg"]["inputs"]["Background"], sg.Src("T_card_GlassBase"))
        self.assertEqual(t["T_Sil_card_Card"]["inputs"]["MaterialInput"], t["T_card_Card"]["inputs"]["MaterialInput"])   # one texture
        self.assertEqual(t["T_R3D2_Mrg"]["inputs"]["Background"], sg.Src("T_card_Glass"))       # pass 2: the card and what follows
        cards = {t[i.op]["reg"] and i.op for i in t["T_R3D2_Scene"]["inputs"].values() if isinstance(i, sg.Src)}
        self.assertTrue({"T_card_Card", "T_chip_Card"} <= cards)
        self.assertEqual(t["T_R3D_Scene"]["inputs"]["SceneInput2"], t["T_R3D2_Scene"]["inputs"]["SceneInput3"])   # one camera
        self.assertEqual(c.regions["T_card_Glass"], c.regions["T_Sil_R3D_Mrg"])
        self.assertEqual(sg.mask_freezes(c.g), [])
        v = validate_setting_text(c.g.text())
        self.assertTrue(v["ok"], v["problems"][:3])

    def test_glass_shape_layers_are_not_batched_and_update_adds_it(self):
        d = mini()
        d["layers"].append({"id": "pill", "type": "rect", "size": [300, 80], "radius": 40, "fill": "#FFFFFF20", "position": [960, 300]})
        c = comp(d)
        d2 = sg.apply_edits(d, [{"layer": "pill", "set": {"glass": {"blur": 12}}}])
        c2 = comp(d2)
        self.assertIn("T_pill_Glass", c2.g.t)
        ops = sg.diff(c, c2)
        self.assertIn("T_pill_Glass", ops["add"])
        self.assertIn(["T_pill", "Background", "T_pill_Glass", "Output"], ops["connect"])


class SB3QuietUpdate(unittest.TestCase):
    """Item 6: scene.update replies stay compact on big edits (counts and samples inline, lists in the detail file)."""

    def test_many_regions_go_to_the_detail_file(self):
        live = SceneLive("test_build_one_call")
        live.setUp()
        try:
            d = mini()
            d["layers"] += [{"id": "d%d" % i, "type": "ellipse", "size": [20, 20], "position": [100 + 40 * i, 900], "in": 5 + i, "out": 40,
                             "keys": {"opacity": [[5 + i, 0], [9 + i, 100]]}} for i in range(20)]
            live.build(d)
            r = OPS["scene.update"].fn(live.ctx, live.comp, {"scene": "T", "edits": [{"scene": {"efficiency.cullMargin": 0}}]})
            self.assertEqual(r["regions"]["count"], 20)
            self.assertEqual(len(r["regions"]["sample"]), 5)
            self.assertLess(len(json.dumps(r)), 2500)
            with open(r["detail"], encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)["regions"]), 20)
            self.assertEqual(r["regionsApplied"], 20)
        finally:
            live.tearDown()


class SB3Mb2dSamples(unittest.TestCase):
    """Efficiency lab item 7: 2D motion-blur Quality defaults to min(motionBlur.samples, 8); efficiency.mb2dSamples overrides; the
    Renderer3D keeps render3d.mbQuality."""

    def test_default_cap_and_override(self):
        s2 = load_scene("bench_s2")
        self.assertEqual(s2["motionBlur"]["samples"], 12)
        c = comp(s2)
        q2d = {r["inputs"]["Quality"] for r in c.g.t.values() if r["reg"] in ("Merge", "Transform") and "MotionBlur" in r["inputs"]}
        self.assertEqual(q2d, {8})
        r3 = [r for r in c.g.t.values() if r["reg"] == "Renderer3D" and "Quality" in r["inputs"]]
        self.assertTrue(all(r["inputs"]["Quality"] in (1, c.cfg["render3d"]["mbQuality"]) for r in r3))
        s2["efficiency"] = dict(s2.get("efficiency") or {}, mb2dSamples=12)
        q2d = {r["inputs"]["Quality"] for r in comp(s2).g.t.values() if r["reg"] == "Merge" and "MotionBlur" in r["inputs"]}
        self.assertEqual(q2d, {12})
        d = mini(motionBlur={"samples": 4})
        self.assertEqual(comp(d).g.t["T_box"]["inputs"]["Quality"], 4)                  # fewer samples than the cap stay


class SB3Premultiplied(unittest.TestCase):
    """Found live in the glass stage: a Background's colour is read as premultiplied, so a #FFFFFF21 card background composited as
    solid white. Background colours (group backgrounds, solids, plates, corner gradients) are now premultiplied; shape fills keep
    Alpha 1 + Opacity."""

    def test_translucent_backgrounds_are_premultiplied(self):
        d = mini()
        d["layers"] += [{"id": "card", "type": "group", "size": [600, 300], "radius": 32, "background": "#FFFFFF21", "position": [960, 540],
                         "layers": [{"id": "lbl", "type": "text", "text": {"content": "x", "size": 40}}]},
                        {"id": "veil", "type": "solid", "color": "#80808080", "size": [200, 200], "position": [300, 300]},
                        {"id": "ramp", "type": "rect", "size": [400, 100], "position": [960, 900],
                         "fill": {"gradient": {"from": [0, 50], "to": [400, 50], "stops": [[0, "#FF000000"], [1, "#FF0000FF"]]}}}]
        t = comp(d).g.t
        b = t["T_card_Base"]["inputs"] if "T_card_Base" in t else t[[n for n in t if n.endswith("card_Base")][0]]["inputs"]
        a = 0x21 / 255
        self.assertAlmostEqual(b["TopLeftAlpha"], a)
        self.assertAlmostEqual(b["TopLeftRed"], a)                                # 1 x alpha
        v = t["T_veil_Src"]["inputs"]
        self.assertAlmostEqual(v["TopLeftRed"], (0x80 / 255) * (0x80 / 255))
        r = t["T_ramp_Src"]["inputs"]
        self.assertEqual(r["Type"], "Corner")
        for corner in ("TopLeft", "BottomLeft"):                                 # left edge: transparent red -> 0
            self.assertAlmostEqual(r[corner + "Red"], 0.0)
        self.assertAlmostEqual(r["TopRightRed"], r["TopRightAlpha"])
        self.assertEqual(t["T_BG"]["inputs"]["TopLeftRed"], 0x10 / 255)           # opaque colours are unchanged
        d2 = mini(controls={"accent": "#FF4B2B", "glassc": "#FFFFFF"})
        d2["layers"].append({"id": "g", "type": "group", "size": [100, 100], "background": "$glassc", "layers": []})
        self.assertIsInstance(comp(d2).g.t["T_g_Base"]["inputs"]["TopLeftRed"], sg.Expr)   # control colours stay live


if __name__ == "__main__":
    unittest.main()
