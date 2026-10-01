"""Offline tests (no Resolve) for fu_catalog lookup/search/argument checks, the batch.run {op} alias and the
shortcut tools (fu_scene_build, fu_scene_plan, fu_batch, fu_contact_sheet) with generated schemas.
Run: .venv/bin/python -m unittest tests.test_catalog_tools -v"""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import jsonschema  # noqa: E402
import mcp.types as types  # noqa: E402

from fusion_connector import server  # noqa: E402
from fusion_connector.ops import OPS  # noqa: E402
from fusion_connector.schema import P, json_schema  # noqa: E402

SCENE = os.path.join(ROOT, "tests", "scenes", "title_low_tide.json")


def sc(r):
    return r.structuredContent


def err(r):
    return sc(r)["error"]


class CatalogLookup(unittest.TestCase):
    def test_found(self):
        r = sc(server.catalog({"operation": "tool.delete"}))
        self.assertEqual(r["category"], "tool")
        self.assertEqual(r["operation"], OPS["tool.delete"].public())
        self.assertIn("tool.add", r["siblings"])
        self.assertNotIn("tool.delete", r["siblings"])

    def test_unknown_suggests(self):
        e = err(server.catalog({"operation": "tool.delte"}))
        self.assertEqual(e["code"], "UNKNOWN_OPERATION")
        self.assertEqual(e["details"]["suggestion"], "tool.delete")
        self.assertIn("tool.delete", e["hint"])

    def test_blocked_by_readonly(self):
        with mock.patch.dict(os.environ, {"FUSION_MCP_READONLY": "1"}):
            e = err(server.catalog({"operation": "tool.delete"}))
            self.assertEqual(e["code"], "FORBIDDEN")
            self.assertIn("FUSION_MCP_READONLY", e["message"])
            self.assertTrue(sc(server.catalog({"operation": "tool.info"}))["ok"])

    def test_no_args_hint(self):
        self.assertIn("query", sc(server.catalog({}))["hint"])


class CatalogQuery(unittest.TestCase):
    def test_finds_and_ranks(self):
        r = sc(server.catalog({"query": "delete tool"}))
        self.assertEqual(r["matches"][0]["name"], "tool.delete")
        self.assertLessEqual(len(r["matches"]), 10)
        row = r["matches"][0]
        self.assertEqual(set(row), {"name", "category", "summary", "params", "readOnly"})
        self.assertEqual(row["params"], [p.name for p in OPS["tool.delete"].params])
        self.assertNotIn("\n", row["summary"])
        for q, want in (("Tool.Delete", "tool.delete"), ("TOOL_delete tools", "tool.delete"), ("contactsheet", "render.contact_sheet")):
            self.assertEqual(sc(server.catalog({"query": q}))["matches"][0]["name"], want, q)

    def test_category_narrows(self):
        r = sc(server.catalog({"query": "delete", "category": "tool"}))
        self.assertTrue(r["matches"])
        self.assertEqual({m["category"] for m in r["matches"]}, {"tool"})
        self.assertEqual(err(server.catalog({"query": "delete", "category": "tol"}))["code"], "UNKNOWN_CATEGORY")

    def test_no_hit(self):
        e = err(server.catalog({"query": "delte tol"}))
        self.assertEqual(e["code"], "NOT_FOUND")
        self.assertIn("tool.delete", e["details"]["suggestions"])
        e = err(server.catalog({"query": "xyzzy"}))
        self.assertEqual(e["code"], "NOT_FOUND")
        self.assertIn("tool", e["details"]["suggestions"])

    def test_deterministic(self):
        a = sc(server.catalog({"query": "render frame preview"}))["matches"]
        self.assertEqual(a, sc(server.catalog({"query": "preview frame render"}))["matches"])


class CatalogArgs(unittest.TestCase):
    def test_unknown_argument(self):
        e = err(server.catalog({"categry": "tool"}))
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertIn("categry", e["message"])
        self.assertIn("'category'", e["message"])
        schema = next(t for t in server.TOOLS if t["name"] == "fu_catalog")["schema"]
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(set(schema["properties"]), {"category", "operation", "query"})

    def test_operation_with_query(self):
        e = err(server.catalog({"operation": "tool.add", "query": "add"}))
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertIn("query", e["message"])


class BatchOpAlias(unittest.TestCase):
    def run_batch(self, args):
        return sc(asyncio.run(server.do({"operation": "batch.run", "args": args, "dryRun": True})))

    def test_inline(self):
        r = self.run_batch({"ops": [{"op": "comp.info", "args": {}}, {"operation": "tool.info", "args": {"tool": "A"}}]})
        self.assertEqual([c["operation"] for c in r["args"]["ops"]], ["comp.info", "tool.info"])
        self.assertFalse(any("rejected" in c for c in r["args"]["ops"]))
        bad = self.run_batch({"ops": [{"name": "comp.info"}, {"op": "comp.info", "operation": "comp.info"}]})["args"]["ops"]
        self.assertTrue(all(c["rejected"]["code"] == "INVALID_ARGS" for c in bad))

    def test_path_file(self):
        p = os.path.join(tempfile.mkdtemp(), "ops.json")
        with open(p, "w") as f:
            json.dump({"ops": [{"op": "comp.info", "args": {}}]}, f)
        r = self.run_batch({"path": p})
        self.assertEqual(r["args"]["ops"], [{"operation": "comp.info", "args": {}}])


class GeneratedSchemas(unittest.TestCase):
    def test_json_schema_types(self):
        s = json_schema([P("a", "string|object", "A", required=True), P("b", "any", "B"), P("c", "integer", "C", default=4),
                         P("d", "string", "D", enum=("x", "y"), nullable=True), P("e", "number|array", "E")])
        pr = s["properties"]
        self.assertEqual(pr["a"]["type"], ["string", "object"])
        self.assertNotIn("type", pr["b"])
        self.assertEqual((pr["c"]["type"], pr["c"]["default"]), ("integer", 4))
        self.assertEqual((pr["d"]["type"], pr["d"]["enum"]), (["string", "null"], ["x", "y", None]))
        self.assertEqual((s["required"], s["additionalProperties"]), (["a"], False))
        jsonschema.validate({"a": {}, "b": [1], "d": None, "e": 2.5}, s)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate, {"a": 1}, s)

    def test_shortcuts_match_ops(self):
        for name, opn in server.SHORTCUTS.items():
            t = next(t for t in server.TOOLS if t["name"] == name)
            s, op = server.tool_schema(t), OPS[opn]
            jsonschema.Draft202012Validator.check_schema(s)
            self.assertEqual(set(s["properties"]), {p.name for p in op.params} | {"timeoutMs", "dryRun"}, name)
            self.assertEqual(s.get("required", []), [p.name for p in op.params if p.required], name)
            for p in op.params:
                want = p.type.split("|")
                self.assertEqual(s["properties"][p.name].get("type"), None if p.type == "any" else want[0] if len(want) == 1 else want, (name, p.name))
                self.assertEqual(s["properties"][p.name].get("enum"), list(p.enum) if p.enum else None)
        plan = server.tool_schema(next(t for t in server.TOOLS if t["name"] == "fu_scene_plan"))
        self.assertEqual({k: v for k, v in plan["properties"].items() if k not in server.RUN}, json_schema(OPS["scene.plan"].params)["properties"])

    def test_effects(self):
        eff = {t["name"]: t["effect"] for t in server.TOOLS if "operation" in t}
        self.assertEqual(eff, {"fu_scene_build": "destructive", "fu_scene_plan": "read", "fu_batch": "destructive", "fu_contact_sheet": "write"})
        self.assertEqual(len(server.TOOLS), 15)


class ShortcutRouting(unittest.TestCase):
    def call(self, name, args):
        return sc(asyncio.run(server.handle(name, args)))

    def test_scene_plan_offline(self):
        r = self.call("fu_scene_plan", {"path": SCENE, "quiet": True})
        self.assertTrue(r["ok"] and r["offline"])
        direct = sc(asyncio.run(server.do({"operation": "scene.plan", "args": {"path": SCENE, "quiet": True}})))
        self.assertEqual(r["result"], direct["result"])

    def test_dry_runs(self):
        r = self.call("fu_scene_build", {"path": SCENE, "replace": True, "dryRun": True})
        self.assertEqual((r["dryRun"], r["operation"], r["args"]), (True, "scene.build", {"path": SCENE, "replace": True}))
        r = self.call("fu_batch", {"ops": [{"op": "comp.info", "args": {}}], "timeoutMs": 5000, "dryRun": True})
        self.assertEqual(r["args"], {"ops": [{"operation": "comp.info", "args": {}}]})
        r = self.call("fu_contact_sheet", {"beats": 4, "quality": "draft", "dryRun": True})
        self.assertEqual((r["operation"], r["readOnly"]), ("render.contact_sheet", False))
        e = err(asyncio.run(server.handle("fu_scene_build", {"pth": SCENE, "dryRun": True})))
        self.assertEqual(e["code"], "INVALID_ARGS")
        self.assertIn("'path'", e["message"])

    def test_policy(self):
        with mock.patch.dict(os.environ, {"FUSION_MCP_READONLY": "1"}):
            vis = {t["name"] for t in server.visible_tools()}
            self.assertTrue({"fu_scene_plan", "fu_batch"} <= vis)
            self.assertFalse({"fu_scene_build", "fu_contact_sheet", "fu_render_frame"} & vis)
            self.assertEqual(err(asyncio.run(server.handle("fu_scene_build", {"path": SCENE, "dryRun": True})))["code"], "FORBIDDEN")
            kids = self.call("fu_batch", {"ops": [{"op": "tool.delete", "args": {"tool": "A"}}], "dryRun": True})["args"]["ops"]
            self.assertEqual(kids[0]["rejected"]["code"], "FORBIDDEN")
        with mock.patch.dict(os.environ, {"FUSION_MCP_ALLOW_CATEGORIES": "comp"}):
            self.assertFalse(set(server.SHORTCUTS) & {t["name"] for t in server.visible_tools()})
        self.assertEqual(sc(server.catalog({"operation": "scene.plan"}))["shortcut"], "fu_scene_plan")

    def test_mcp_layer(self):
        """list_tools serves the generated schemas and the SDK validates calls against them before routing."""
        srv = server.build_server()

        async def go():
            lt = await srv.request_handlers[types.ListToolsRequest](types.ListToolsRequest(method="tools/list"))
            call = srv.request_handlers[types.CallToolRequest]

            def req(n, a):
                return call(types.CallToolRequest(method="tools/call", params=types.CallToolRequestParams(name=n, arguments=a)))
            return lt.root.tools, (await req("fu_scene_plan", {"path": SCENE, "quiet": True})).root, (await req("fu_batch", {"ops": [], "bogus": 1})).root
        tools, ok, bad = asyncio.run(go())
        plan = next(t for t in tools if t.name == "fu_scene_plan")
        self.assertTrue(plan.annotations.readOnlyHint)
        self.assertIn("quiet", plan.inputSchema["properties"])
        self.assertFalse(ok.isError)
        self.assertTrue(bad.isError)
        self.assertIn("bogus", bad.content[0].text)


if __name__ == "__main__":
    unittest.main()
