"""Offline tests for the house graph style (fusion_connector.layout, comp.layout, the scene.build/update hook).
Run: .venv/bin/python -m unittest tests.test_layout -v"""
import json
import os
import random
import re
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fusion_connector import layout as lay, scenegraph as sg  # noqa: E402
from fusion_connector.luatable import LTable, parse  # noqa: E402
from fusion_connector.ops import OPS  # noqa: E402
from fusion_connector.ops import layout as olay, scene as sops  # noqa: E402
from fusion_connector.ops.build import setting_syntax_problems, validate_setting_text  # noqa: E402
from fusion_connector.schema import TSV  # noqa: E402
from tests.test_offline import EXAMPLES, FComp, FCtx, Env, load_scene, mini, NOFONTS, fake_repaste, needs_tsv  # noqa: E402

SCENES = EXAMPLES   # the example scenes that ship (the benchmark scene is skipped when absent)


def net_of(tools, edges, scenes=()):
    net = lay.Net(scenes)
    for n, r in tools:
        net.add(n, r)
    for s, d, i in edges:
        net.edge(s, d, i)
    return net


def film(copies):
    """A film comp: copies x the six example scenes, each FILM_<scene> on one ladder into MediaOut1, plus MediaIn1."""
    tools, edges, scenes = [], [], []
    k = 0
    for _ in range(copies):
        for f in SCENES:
            d = load_scene(f)
            d["scene"] = "S%d" % k
            k += 1
            c = sg.compile_scene(d, fonts=NOFONTS, layout=False)
            g = sg.graph_net(c.g, [c.S])
            tools += list(g.reg.items())
            edges += [(s, n, i) for n in g.reg for i, s in g.ins[n]]
            scenes.append(c.S)
    tools += [("MediaIn1", "MediaIn"), ("MediaOut1", "MediaOut"), ("FILM_Base", "Background")]
    prev = "FILM_Base"
    for s in scenes:
        tools.append(("FILM_" + s, "Merge"))
        edges += [(prev, "FILM_" + s, "Background"), (s + "_Out", "FILM_" + s, "Foreground")]
        prev = "FILM_" + s
    edges.append((prev, "MediaOut1", "Input"))
    return tools, edges, scenes


def clean(t, m, where=""):
    t.assertEqual(m["overlaps"], 0, where)
    t.assertEqual(m["offLattice"], 0, where)          # Fusion snaps SetPos to half columns / whole rows: plan on that lattice
    t.assertTrue(m["spinesStraight"], where)
    t.assertEqual(m["boxProblems"], [], where)


class HouseStyle(unittest.TestCase):
    def test_example_scenes(self):
        for f in SCENES:
            c = sg.compile_scene(load_scene(f), fonts=NOFONTS)
            m = lay.metrics(c.graph, c.net)
            clean(self, m, f)
            self.assertEqual(set(c.graph["pos"]), set(c.net.reg), f)                     # every node placed
            main = c.graph["bands"][0]["spine"]
            self.assertEqual(main[-1], c.S + "_Out", f)                                   # the spine ends at the scene output
            self.assertEqual(main[0], c.S + "_BG", f)
            kinds = {b["kind"] for b in c.g.underlays}
            self.assertTrue({"scene", "controller"} <= kinds, (f, kinds))
            ctrl = c.graph["pos"][c.S + "_CTRL"]
            bg = c.graph["pos"][c.S + "_BG"]
            self.assertLessEqual(ctrl[0], bg[0])                                          # controls: top-left corner
            self.assertLess(ctrl[1], bg[1])
            if f != "bench_s2":                                                            # bench: wires from shared textures only
                self.assertEqual(m["crossings"], 0, f)

    @needs_tsv
    def test_setting_carries_positions_and_underlays(self):
        c = sg.compile_scene(load_scene("kitchen_sink"), fonts=NOFONTS)
        text = c.g.text()
        self.assertEqual(setting_syntax_problems(text), [])
        v = validate_setting_text(text)
        self.assertTrue(v["ok"], v["problems"][:3])
        tools = parse(text).get("Tools")
        ul = [n for n, t in tools.items if isinstance(t, LTable) and t.ctor == "Underlay"]
        self.assertEqual(len(ul), len(c.g.underlays))
        u = tools.get(ul[0])
        info = u.get("ViewInfo")
        self.assertEqual(info.ctor, "UnderlayInfo")
        x0, y0, x1, y1 = c.g.underlays[0]["rect"]
        self.assertAlmostEqual(info.get("Pos").positional()[0], (x0 + x1) / 2 * 110, places=2)   # center x, TOP edge
        self.assertAlmostEqual(info.get("Pos").positional()[1], y0 * 33, places=2)
        self.assertEqual(u.get("CustomData").get(lay.TAG), c.g.underlays[0]["kind"])
        pos = c.graph["pos"]["Sink_plate"]
        self.assertIn("ViewInfo = OperatorInfo { Pos = { %s, %s } }" % (sg._num(pos[0] * 110), sg._num(pos[1] * 33)), text)
        part = c.g.text(["Sink_plate"])                                                   # partial pastes (scene.update) carry no underlays
        self.assertNotIn("Underlay", part)
        self.assertEqual(sg.graph_stats(c.g)["tools"], len(c.g.t))                         # underlays are not graph tools

    def test_masks_opposite_side_and_side_inputs_left(self):
        net = net_of([("BG", "Background"), ("M1", "Merge"), ("Txt", "TextPlus"), ("Blur", "Blur"), ("TMask", "RectangleMask"),
                      ("Plate", "Background"), ("Cut", "EllipseMask"), ("Cut2", "RectangleMask"), ("Out", "MediaOut")],
                     [("BG", "M1", "Background"), ("Blur", "M1", "Foreground"), ("Txt", "Blur", "Input"), ("TMask", "Txt", "EffectMask"),
                      ("Plate", "Blur", "Blur2"), ("Cut2", "Cut", "EffectMask"), ("Cut", "M1", "EffectMask"), ("M1", "Out", "Input")])
        p = lay.plan(net)
        P = p["pos"]
        self.assertEqual(P["BG"][1], P["M1"][1])
        self.assertEqual(P["M1"][1], P["Out"][1])
        self.assertEqual(P["Blur"][0], P["M1"][0])            # the layer column stands straight above its Merge
        self.assertLess(P["Blur"][1], P["M1"][1])
        self.assertEqual(P["Txt"][0], P["Blur"][0])
        self.assertGreater(P["Cut"][1], P["M1"][1])           # spine masks below the spine, chained downward
        self.assertGreater(P["Cut2"][1], P["Cut"][1])
        self.assertGreater(P["TMask"][0], P["Txt"][0])        # a column tool's mask to the right
        self.assertLess(P["Plate"][0], P["Blur"][0])          # its side input to the left
        clean(self, lay.metrics(p, net))

    def test_stepped_fan_has_no_crossings(self):
        tools = [("R", "Renderer3D"), ("M3", "Merge3D"), ("Out", "MediaOut"), ("BG", "Background"), ("Mg", "Merge")]
        edges = [("M3", "R", "SceneInput"), ("BG", "Mg", "Background"), ("R", "Mg", "Foreground"), ("Mg", "Out", "Input")]
        for i in range(1, 9):
            tools += [("Card%d" % i, "ImagePlane3D"), ("Tex%d" % i, "Background"), ("Blur%d" % i, "Blur")]
            edges += [("Card%d" % i, "M3", "SceneInput%d" % i), ("Blur%d" % i, "Card%d" % i, "MaterialInput"), ("Tex%d" % i, "Blur%d" % i, "Input")]
        net = net_of(tools, edges)
        p = lay.plan(net)
        m = lay.metrics(p, net)
        clean(self, m)
        self.assertEqual((m["crossings"], m["wiresOverTools"]), (0, 0))
        self.assertEqual({b["kind"] for b in p["boxes"]}, {"3d"})

    def test_corner_controls_and_shared_assets(self):
        tools = [("S_BG", "Background"), ("S_a", "Merge"), ("S_b", "Merge"), ("S_Out", "PipeRouter"), ("S_CTRL", "Custom"),
                 ("S_tex", "Background"), ("S_a_Xf", "Transform"), ("S_b_Xf", "Transform"), ("Note1", "Note"), ("MediaOut1", "MediaOut")]
        edges = [("S_BG", "S_a", "Background"), ("S_a", "S_b", "Background"), ("S_b", "S_Out", "Input"), ("S_Out", "MediaOut1", "Input"),
                 ("S_tex", "S_a_Xf", "Input"), ("S_tex", "S_b_Xf", "Input"), ("S_a_Xf", "S_a", "Foreground"), ("S_b_Xf", "S_b", "Foreground")]
        net = net_of(tools, edges, ["S"])
        p = lay.plan(net)
        P = p["pos"]
        self.assertEqual(p["shared"], ["S_tex"])
        for n in ("S_CTRL", "S_tex"):
            self.assertLessEqual(P[n][0], P["S_BG"][0], n)
            self.assertLess(P[n][1], P["S_BG"][1], n)
        kinds = {b["kind"]: b for b in p["boxes"]}
        self.assertIn("S_CTRL", kinds["controller"]["members"])
        self.assertEqual(kinds["shared"]["members"], ["S_tex"])
        self.assertEqual(kinds["scene"]["name"], "S_SCENE")
        self.assertNotIn("MediaOut1", kinds["scene"]["members"])
        self.assertEqual(sorted(x[0] for x in p["cross"]), ["S_tex", "S_tex"])   # wires from the corner are the only long ones
        clean(self, lay.metrics(p, net))

    def test_deterministic_whatever_the_dump_order(self):
        tools, edges, scenes = film(1)
        a = lay.plan(net_of(tools, edges, scenes))
        self.assertEqual(a, lay.plan(net_of(tools, edges, scenes)))
        rnd = random.Random(7)
        t2 = tools[:]
        rnd.shuffle(t2)
        by_dst = {}
        for e in edges:
            by_dst.setdefault(e[1], []).append(e)
        order = list(by_dst)
        rnd.shuffle(order)
        e2 = [e for d in order for e in by_dst[d]]   # a tool's inputs keep their input order; tools come in any order
        self.assertEqual(a, lay.plan(net_of(t2, e2, scenes)))

    def test_film_3000_tools(self):
        tools, edges, scenes = film(8)
        if len(tools) <= 3000:                                   # fewer example scenes ship than exist locally
            tools, edges, scenes = film(3000 * 8 // len(tools) + 1)
        self.assertGreater(len(tools), 3000)
        net = net_of(tools, edges, scenes)
        t0 = time.time()
        p = lay.plan(net)
        dt = time.time() - t0
        m = lay.metrics(p, net)
        self.assertLess(dt, 3.0)                                 # measured ~0.1 s
        clean(self, m, "film")
        P = p["pos"]
        ladder = ["FILM_Base"] + ["FILM_" + s for s in scenes] + ["MediaOut1"]
        self.assertEqual(p["bands"][0]["spine"], ladder)          # the film ladder is the main spine
        self.assertEqual(len({P[n][1] for n in ladder}), 1)
        tops = {b["name"]: b for b in p["boxes"] if b["parent"] is None}
        self.assertIn("FILM_LADDER", tops)
        for s in scenes:
            box = tops[s + "_SCENE"]
            x0, y0, x1, y1 = box["rect"]
            for n in net.reg:
                if n.startswith(s + "_"):
                    self.assertTrue(x0 <= P[n][0] - 0.5 and P[n][0] + 0.5 <= x1 and y0 <= P[n][1] - 0.5 and P[n][1] + 0.5 <= y1, n)
            self.assertLess(y1, P["FILM_" + s][1] - 0.5)           # each scene's backdrop sits above its ladder Merge
            self.assertLessEqual(x0, P["FILM_" + s][0])
            self.assertGreaterEqual(x1, P["FILM_" + s][0])
        cross = {(s, d) for s, d, _ in p["cross"]}
        self.assertTrue(all("Freeze" in s or "Mrg" in s for s, _ in cross))   # long wires come only from shared textures

    def test_deep_chain_and_random_graphs(self):
        tools = [("BG", "Background"), ("M", "Merge"), ("Out", "MediaOut")] + [("CC%d" % i, "ColorCorrector") for i in range(3000)]
        edges = [("BG", "M", "Background"), ("M", "Out", "Input"), ("CC2999", "M", "Foreground")]
        edges += [("CC%d" % i, "CC%d" % (i + 1), "Input") for i in range(2999)]
        net = net_of(tools, edges)
        clean(self, lay.metrics(lay.plan(net), net), "chain")                      # no recursion limit on long chains
        regs = ["Merge", "Blur", "Transform", "RectangleMask", "Background", "TextPlus", "Merge3D", "Custom", "Note", "Dissolve",
                "PipeRouter"]
        net = net_of([("A", "Background"), ("B", "Merge3D"), ("C", "Blur"), ("O", "MediaOut")],
                     [("A", "C", "Input"), ("A", "C", "EffectMask"), ("B", "C", "Foreground"), ("C", "O", "Input")])
        clean(self, lay.metrics(lay.plan(net), net), "one source into two inputs")      # placed once (a fuzz find)
        for seed in list(range(25)) + [386]:
            rnd = random.Random(seed)
            n = rnd.randint(5, 300)
            tools = [("T%d_%s" % (i, rnd.choice("ABC")), rnd.choice(regs)) for i in range(n)]
            edges = []
            for i, (d, r) in enumerate(tools):
                for iid in rnd.sample(["Background", "Foreground", "Input", "EffectMask", "SceneInput2", "SceneInput3",
                                          "GarbageMatte"], rnd.randint(0, 3)):
                    if i and rnd.random() < 0.7:
                        edges.append((tools[rnd.randrange(i)][0], d, iid))
            net = net_of(tools, edges)
            p = lay.plan(net)
            self.assertEqual(set(p["pos"]), set(net.reg), seed)
            clean(self, lay.metrics(p, net), "seed %d" % seed)

    def test_fuzz_with_scene_prefixes(self):
        """Random graphs mixing scene prefixes, FILM_/FC_ tools, 3D, masks and groups (seeds that once broke backdrop nesting)."""
        regs = ["Merge", "Blur", "Transform", "RectangleMask", "BitmapMask", "Background", "TextPlus", "Merge3D", "Custom", "Note",
                "Dissolve", "PipeRouter", "ImagePlane3D", "Renderer3D", "sMerge", "Loader", "MediaOut", "Saver", "GroupOperator"]
        iids = ["Background", "Foreground", "Input", "EffectMask", "SceneInput", "SceneInput1", "SceneInput2", "SceneInput3",
                "SceneInput10", "GarbageMatte", "SolidMatte", "Input1", "Input2", "Input3", "MaterialInput", "Image"]
        for seed in (1500, 1504, 1505, 1507, 1510, 1513, 1519, 1520, 1542, 1550):
            rnd = random.Random(seed)
            n = rnd.randint(3, 600)
            pfx = rnd.choice(["S1_", "S2_", "Film_", "", "X"])
            tools = [("%s%sT%d" % (rnd.choice([pfx, "S3_", ""]), rnd.choice(["", "FILM_", "FC_"]) if rnd.random() < 0.05 else "", i),
                      rnd.choice(regs)) for i in range(n)]
            tools = list(dict(tools).items())
            edges = []
            for i, (d, r) in enumerate(tools):
                for iid in rnd.sample(iids, rnd.randint(0, 4)):
                    if i and rnd.random() < 0.75:
                        edges.append((tools[rnd.randrange(max(0, i - rnd.choice([3, 30, i])), i)][0], d, iid))
            net = net_of(tools, edges, rnd.sample(["S1", "S2", "S3"], rnd.randint(0, 3)))
            p = lay.plan(net)
            self.assertEqual(set(p["pos"]), set(net.reg), seed)
            clean(self, lay.metrics(p, net), "seed %d" % seed)

    def test_underlay_names_avoid_existing_tools(self):
        net = net_of([("BG", "Background"), ("M", "Merge"), ("T", "TextPlus"), ("O", "MediaOut")],
                     [("BG", "M", "Background"), ("T", "M", "Foreground"), ("M", "O", "Input")])
        p = lay.plan(net, taken={"M_TEXT"})
        self.assertEqual([b["name"] for b in p["boxes"]], ["M_TEXT_2"])


DUMP = "\n".join([
    "T\tS_BG\tBackground\t\t0\t0\t\t", "T\tS_title\tMerge\t\t1\t0\t\t", "T\tS_title_Src\tTextPlus\t\t1\t-1\t\t",
    "T\tS_Out\tPipeRouter\t\t2\t0\t\t1", "T\tMediaOut1\tMediaOut\t\t3\t0\t\t", "T\tS_CTRL\tCustom\t\t-1\t-1\t\t",
    "T\tGrp\tGroupOperator\t\t5\t5\t\t", "T\tInner\tBlur\tGrp\t0\t0\t\t", "T\tS_SCENE\tUnderlay\t\t0\t-3\tscene\t",
    "T\tMine\tUnderlay\t\t9\t9\t\t", "T\tS_titleCenterPath\tXYPath\t\t\t\t\t",
    "E\tS_title\tBackground\tS_BG", "E\tS_title\tForeground\tS_title_Src", "E\tS_Out\tInput\tS_title", "E\tMediaOut1\tInput\tS_Out",
    "E\tInner\tInput\tS_BG", "E\tS_BG\tEffectMask\tInner", "E\tS_title\tCenter\tS_titleCenterPath"])


class DumpParse(unittest.TestCase):
    def test_parse_dump(self):
        net = lay.parse_dump(DUMP, {"XYPath"})
        self.assertEqual(net.scenes, ["S"])                              # S_Out carries sbVersion
        self.assertNotIn("Inner", net.reg)                               # a group's tools: the group is the node
        self.assertIn(("EffectMask", "Grp"), net.ins["S_BG"])            # a wire from inside a group maps to the group
        self.assertNotIn("S_titleCenterPath", net.reg)                   # modifiers have no node
        self.assertEqual(net.underlays, {"S_SCENE": "scene", "Mine": ""})
        self.assertEqual(net.old["S_title_Src"], (1.5, -0.5))                 # GetPos (cell top-left) -> tile center
        self.assertEqual(net.ins["S_title"], [("Background", "S_BG"), ("Foreground", "S_title_Src")])


class FakeLayoutCtx:
    """The Ctx surface comp.layout uses: one READ chunk (answered with DUMP), one APPLY chunk (its files are read back)."""

    def __init__(self, dump):
        self.dump, self.applied, self.notes = dump, [], []
        self.resolve = type("R", (), {"GetCurrentPage": lambda s: "fusion", "OpenPage": lambda s, p: None})()

    def tsv(self):
        return TSV.get()

    def is_current(self, comp):
        return True

    def lua(self, comp, code, wait=5.0, key=None):
        if "GetConnectedInputs" in code:
            return self.dump
        paths = re.findall(r"\[\[(.*?)\]\]", code)
        drop = json.loads("[" + re.search(r"ipairs\(\{(.*?)\}\)", code).group(1) + "]")
        ul = ""
        if paths[0]:
            with open(paths[0], encoding="utf-8") as f:
                ul = f.read()
        with open(paths[1], encoding="utf-8") as f:
            rows = parse(f.read()).positional()
        self.applied.append({"drop": drop, "underlays": ul, "rows": {r.positional()[0]: r.positional()[1:] for r in rows},
                             "fit": "if true then" in code})
        return "%d;%d;" % (len(rows), len(drop))


class CompLayoutOp(unittest.TestCase):
    def setUp(self):
        self.env = Env(FUSION_MCP_OUT_DIR=tempfile.mkdtemp())
        self.env.__enter__()

    def tearDown(self):
        self.env.__exit__()

    def test_registered(self):
        o = OPS["comp.layout"]
        self.assertTrue(o.extra.get("paste"))
        self.assertEqual({p.name for p in o.params}, {"comp", "scene", "tools", "underlays", "fit", "dryRun", "preview"})
        for n in ("scene.build", "scene.update"):
            self.assertIn("layout", {p.name for p in OPS[n].params})
        self.assertIn("graph", {p.name for p in OPS["scene.plan"].params})

    @needs_tsv
    def test_whole_comp_two_chunks(self):
        ctx = FakeLayoutCtx(DUMP)
        r = OPS["comp.layout"].fn(ctx, None, {})
        self.assertEqual(len(ctx.applied), 1)
        ap = ctx.applied[0]
        self.assertEqual(ap["drop"], ["S_SCENE"])                           # our old underlays go; the user's "Mine" stays
        self.assertTrue(any("Mine" in n for n in r["notes"]))
        self.assertIn("S_SCENE = Underlay", ap["underlays"])
        self.assertIn("S_CONTROLS = Underlay", ap["underlays"])
        self.assertEqual(setting_syntax_problems(ap["underlays"]), [])
        for n in ("S_BG", "S_title", "S_title_Src", "S_Out", "MediaOut1", "S_CTRL", "Grp", "S_SCENE"):
            self.assertIn(n, ap["rows"], n)
        self.assertNotIn("Inner", ap["rows"])
        self.assertFalse(ap["fit"])                                         # the user's view is left alone unless asked
        OPS["comp.layout"].fn(ctx, None, {"fit": True})
        self.assertTrue(ctx.applied[1]["fit"])
        self.assertEqual(r["metrics"]["overlaps"], 0)
        with open(r["detail"], encoding="utf-8") as f:
            self.assertIn("pos", json.load(f))

    @needs_tsv
    def test_dry_run_and_preview_touch_nothing(self):
        ctx = FakeLayoutCtx(DUMP)
        r = OPS["comp.layout"].fn(ctx, None, {"dryRun": True, "preview": True})
        self.assertTrue(r["dryRun"])
        self.assertEqual(ctx.applied, [])
        self.assertTrue(os.path.getsize(r["preview"]) > 0)

    @needs_tsv
    def test_scene_scope_keeps_its_spot(self):
        ctx = FakeLayoutCtx(DUMP)
        r = OPS["comp.layout"].fn(ctx, None, {"scene": "S", "underlays": False})
        rows = ctx.applied[0]["rows"]
        self.assertNotIn("MediaOut1", rows)
        self.assertEqual(min(v[0] for v in rows.values()), -1.0)            # the old top-left of the S_ tools
        self.assertEqual(min(v[1] for v in rows.values()), -1.0)
        self.assertEqual(ctx.applied[0]["drop"], [])
        self.assertEqual(r["scope"], "S")

    @needs_tsv
    def test_scene_hook_scope(self):
        ctx = FakeLayoutCtx(DUMP)
        w = []
        r = olay.tidy_after(ctx, None, "S", "update", w)
        self.assertEqual(w, [])
        self.assertEqual(r["scope"], "S")                                  # Grp is a user's tool: only the scene moves
        self.assertEqual(ctx.applied[0]["rows"]["S_Out"], [2.0, 0.0])        # update: the scene output stays put
        clean_dump = "\n".join([l for l in DUMP.splitlines() if "Grp" not in l and "Inner" not in l] +
                               ["T\tFC_RenderSaver\tSaver\t\t7\t7\t\t"])            # the connector's parked render Saver is not a user's
        ctx = FakeLayoutCtx(clean_dump)
        self.assertEqual(olay.tidy_after(ctx, None, "S", "build", w)["scope"], "comp")   # all scene-builder tools: the whole comp


class SceneHook(unittest.TestCase):
    def setUp(self):
        self.saved = (sops.repaste, sops.tidy_after, sops._fonts)
        self.calls = []
        sops.repaste = fake_repaste
        sops.tidy_after = lambda ctx, comp, scene, mode, warnings: self.calls.append((scene, mode)) or {"scope": "comp"}
        sops._fonts = lambda ctx=None: NOFONTS
        self.comp = FComp()
        self.ctx = FCtx(self.comp)
        self.env = Env(FUSION_MCP_OUT_DIR=tempfile.mkdtemp())
        self.env.__enter__()

    def tearDown(self):
        sops.repaste, sops.tidy_after, sops._fonts = self.saved
        self.env.__exit__()

    def test_build_and_update_tidy(self):
        d = mini()
        r = OPS["scene.build"].fn(self.ctx, self.comp, {"description": d})
        self.assertEqual(r["layout"], {"scope": "comp"})
        self.assertIn("T_SCENE", self.comp.tools)                            # the pasted text carried the underlays
        self.assertEqual(self.comp.tools["T_SCENE"].reg, "Underlay")
        up = OPS["scene.update"].fn
        up(self.ctx, self.comp, {"scene": "T", "edits": [{"layer": "title", "set": {"text.content": "Hi"}}]})
        self.assertEqual(self.calls, [("T", "build")])                        # a value edit moves nothing
        up(self.ctx, self.comp, {"scene": "T", "edits": [{"add": {"id": "dot", "type": "ellipse", "size": [40, 40]}, "after": "box"}]})
        self.assertEqual(self.calls[-1], ("T", "update"))
        up(self.ctx, self.comp, {"scene": "T", "edits": [{"remove": "dot"}], "layout": False})
        self.assertEqual(len(self.calls), 2)
        OPS["scene.build"].fn(self.ctx, self.comp, {"description": d, "replace": True, "layout": False})
        self.assertEqual(len(self.calls), 2)
        self.assertIn("T_SCENE", self.comp.tools)                            # replaced, not renamed T_SCENE_1
        self.assertNotIn("T_SCENE_1", self.comp.tools)

    def test_plan_graph_preview(self):
        r = OPS["scene.plan"].fn({"description": load_scene("title_low_tide"), "graph": True})
        g = r["graph"]
        self.assertEqual((g["overlaps"], g["crossings"]), (0, 0))
        self.assertTrue(g["spinesStraight"])
        self.assertIn("LowTide_SCENE", g["underlays"])
        self.assertTrue(os.path.getsize(g["png"]) > 0)


if __name__ == "__main__":
    unittest.main()
