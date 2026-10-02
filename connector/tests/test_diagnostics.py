"""Offline tests for the 0.2 diagnostics: the scripting-port check (#8), the scene.build format warning (#9) and the
preview's stack order for 3D blocks (#11).
Run: .venv/bin/python -m unittest tests.test_diagnostics -v"""
import io
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fusion_connector import cli, diag, scenegraph as sg  # noqa: E402
from fusion_connector.ops import OPS  # noqa: E402
from tests import test_offline as to  # noqa: E402 (a module import: its TestCases are not collected twice)
from tests.test_offline import FCtx, comp, mini  # noqa: E402

APP = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents"
PLUGIN = (APP + "/Applications/.hidden/Electron.app/Contents/MacOS/Electron /Library/Application Support/Blackmagic Design/"
          "DaVinci Resolve/Workflow Integration Plugins/com.example.panel/main.js")
LSOF_HEAD = "COMMAND     PID      USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME\n"
PS_HEAD = "  PID  PPID COMMAND\n    1     0 /sbin/launchd\n  128     1 /usr/libexec/logd\n"

# Healthy, as seen live: Resolve and its fuscript hold 49152; a plugin the running Resolve launched has parent PID 1 and
# shares that socket.
HEALTHY_LSOF = LSOF_HEAD + """rapportd    612 editor    8u  IPv4 0x1111111111111111      0t0  TCP *:49158 (LISTEN)
Resolve     375 editor   52u  IPv4  0xa6c7954e114d095      0t0  TCP *:49152 (LISTEN)
fuscript    439 editor   52u  IPv4  0xa6c7954e114d095      0t0  TCP *:49152 (LISTEN)
Electron   7911 editor   52u  IPv4  0xa6c7954e114d095      0t0  TCP *:49152 (LISTEN)
"""
HEALTHY_PS = PS_HEAD + f"""  375     1 {APP}/MacOS/Resolve
  439   375 fuscript -s
 7911     1 {PLUGIN}
"""
# The failure (open-fusion-mcp#8): the old fuscript and plugin Electron, both orphaned, share one socket on 49152; the
# relaunched Resolve and its fuscript sit on 49153.
FAIL_LSOF = LSOF_HEAD + """Resolve    9120 editor   52u  IPv4 0xbbbbbbbbbbbbbbbb      0t0  TCP *:49153 (LISTEN)
fuscript   9188 editor   52u  IPv4 0xbbbbbbbbbbbbbbbb      0t0  TCP *:49153 (LISTEN)
fuscript    439 editor   52u  IPv4 0xaaaaaaaaaaaaaaaa      0t0  TCP *:49152 (LISTEN)
Electron   7911 editor   52u  IPv4 0xaaaaaaaaaaaaaaaa      0t0  TCP *:49152 (LISTEN)
Electron   7911 editor   53u  IPv6 0xaaaaaaaaaaaaaaab      0t0  TCP *:49152 (LISTEN)
"""
FAIL_PS = PS_HEAD + f"""  439     1 fuscript -s
 7911     1 {PLUGIN}
 9120     1 {APP}/MacOS/Resolve
 9188  9120 fuscript -s
"""


class ScriptingPort(unittest.TestCase):
    def test_healthy(self):
        v = diag.analyze(HEALTHY_LSOF, HEALTHY_PS)
        self.assertEqual(v["status"], "ok", v)
        self.assertEqual([(h["pid"], h["role"]) for h in v["ports"]["49152"]], [(375, "resolve"), (439, "child"), (7911, "shared")])
        self.assertEqual((v["orphans"], v["ports"]["49153"], v["resolve"]), ([], [], [375]))
        self.assertIn("Workflow Integration plugin com.example.panel pid 7911 (shares Resolve's socket)", v["detail"])
        self.assertIsNone(diag.timeout_hint(v))

    def test_orphans_hold_49152_resolve_on_49153(self):
        v = diag.analyze(FAIL_LSOF, FAIL_PS)
        self.assertEqual(v["status"], "problem")
        self.assertEqual([(h["pid"], h["ppid"], h["name"]) for h in v["orphans"]],
                         [(439, 1, "fuscript -s"), (7911, 1, "Workflow Integration plugin com.example.panel")])
        self.assertEqual([(h["pid"], h["role"]) for h in v["ports"]["49153"]], [(9120, "resolve"), (9188, "child")])
        self.assertIn("not by the running Resolve (pid 9120), which registered on 49153", v["problem"])
        self.assertIn("kill 439 7911", v["fix"])
        self.assertIn("they belong to a Resolve session that has exited; then quit and reopen Resolve so it registers on 49152", v["fix"])
        h = diag.timeout_hint(v)
        self.assertTrue(h.startswith("port 49152 is held by pid 439 (fuscript -s) and pid 7911 (Workflow Integration plugin"), h)

    def test_resolve_not_running(self):
        v = diag.analyze(LSOF_HEAD, PS_HEAD)
        self.assertEqual((v["status"], v["resolve"]), ("not-running", []))
        self.assertIsNone(diag.timeout_hint(v))
        v = diag.analyze(FAIL_LSOF, "\n".join(x for x in FAIL_PS.splitlines() if "9120" not in x))
        self.assertEqual(v["status"], "problem")                      # the leftovers would push the next Resolve to 49153
        self.assertIn("Resolve is not running", v["problem"])
        self.assertIn("then open Resolve so it registers on 49152", v["fix"])

    def test_resolve_alone_on_49153_and_not_listening(self):
        v = diag.analyze(LSOF_HEAD + "Resolve 9120 u 52u IPv4 0xb 0t0 TCP *:49153 (LISTEN)\n", PS_HEAD + f" 9120 1 {APP}/MacOS/Resolve\n")
        self.assertEqual(v["status"], "problem")
        self.assertEqual(v["fix"], "quit and reopen Resolve so it registers on 49152")
        v = diag.analyze(LSOF_HEAD, PS_HEAD + f" 9120 1 {APP}/MacOS/Resolve\n")
        self.assertEqual(v["status"], "not-listening")

    def test_skipped_on_windows_or_missing_commands(self):
        with mock.patch.object(diag.sys, "platform", "win32"):
            v = diag.check()
        self.assertEqual(v["status"], "skipped")
        self.assertIsNone(diag.timeout_hint(v))
        with mock.patch.object(diag.shutil, "which", return_value=None), mock.patch.object(diag.subprocess, "run") as run:
            v = diag.check()
        self.assertEqual((v["status"], v["detail"]), ("skipped", "not checked: lsof and ps not found"))
        run.assert_not_called()

    def test_doctor_reports_and_never_calls_resolve(self):
        calls = []
        fake = types.ModuleType("DaVinciResolveScript")
        fake.scriptapp = lambda *a: calls.append(a)
        out = io.StringIO()
        with mock.patch.object(cli.diag, "check", return_value=diag.analyze(FAIL_LSOF, FAIL_PS)), \
                mock.patch.object(cli.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stderr="")), \
                mock.patch("fusion_connector.skills.build_manifest", return_value={"skills": []}), \
                mock.patch.dict(sys.modules, {"DaVinciResolveScript": fake}), redirect_stdout(out):
            rc = cli.doctor(live=True)
        lines = out.getvalue().splitlines()
        self.assertEqual((rc, calls), (1, []))
        self.assertTrue(any(x.startswith("FAIL  scripting port: port 49152 is held by pid 439") for x in lines), lines)
        self.assertIn("FAIL  Resolve reachable: not tried: a scripting client would hang (see scripting port)", lines)
        with mock.patch.object(cli.diag, "check", return_value={"status": "skipped", "detail": "not checked on Windows"}), \
                mock.patch.object(cli.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stderr="")), \
                mock.patch("fusion_connector.skills.build_manifest", return_value={"skills": []}), \
                mock.patch.dict(sys.modules, {"DaVinciResolveScript": fake}), redirect_stdout(io.StringIO()) as o2:
            cli.doctor(live=True)
        self.assertIn("WARN  scripting port: not checked on Windows", o2.getvalue().splitlines())


class FmtCtx(FCtx):
    def fmt(self, comp):
        return 1920, 1080, 30.0


class FormatWarning(unittest.TestCase):
    """A comp on a clip keeps the clip's size: the warning points to a new Fusion clip, not timeline.set_format (#9)."""
    setUp, tearDown, build = to.SceneLive.setUp, to.SceneLive.tearDown, to.SceneLive.build

    def test_vertical_scene_on_landscape_comp(self):
        self.ctx = FmtCtx(self.comp)
        w = [x for x in self.build(mini(size=[1080, 1920]))["warnings"] if x.startswith("comp frame format")]
        self.assertEqual(w, ["comp frame format is 1920x1080, the scene is 1080x1920: the scene was built for its own size. A comp keeps "
                             "its clip's frame size (timeline.set_format does not resize existing Fusion clips): timeline.add_fusion_clip "
                             "on a 1080x1920 timeline makes a new clip at that size; rebuild there"])
        self.assertIn("Existing Fusion clips keep their size", OPS["timeline.set_format"].desc)


class PreviewStackOrder(unittest.TestCase):
    """The preview composites 3D blocks at their place in the stack, as split_3d builds them (#11)."""
    RED, GREEN = (255, 0, 0), (0, 255, 0)

    def px(self, layers, xy, **kw):
        from PIL import Image
        d = mini(layers=layers, background="#000000", **kw)
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "p.png")
            sg.preview(comp(d), [0], 480, p)
            with Image.open(p) as im:
                return im.convert("RGB").getpixel(xy)

    def near(self, got, want):
        self.assertTrue(all(abs(a - b) <= 8 for a, b in zip(got, want)), (got, want))

    def test_2d_layer_above_3d_block(self):
        card = {"id": "card", "type": "rect", "size": [800, 600], "fill": "#FF0000", "position": [960, 540, 0]}
        top = {"id": "top", "type": "rect", "size": [200, 200], "fill": "#00FF00", "position": [960, 540]}
        self.near(self.px([card, top], (240, 135)), self.GREEN)        # overlap: the 2D layer is on top
        self.near(self.px([card, top], (160, 135)), self.RED)          # the 3D card itself is drawn
        self.near(self.px([top, card], (240, 135)), self.RED)          # and still covers a 2D layer below it

    def test_inside_a_group(self):
        card = {"id": "gcard", "type": "rect", "size": [800, 600], "fill": "#FF0000", "position": [960, 540, 0]}
        top = {"id": "gtop", "type": "rect", "size": [200, 200], "fill": "#00FF00", "position": [960, 540]}
        g = {"id": "g", "type": "group", "size": [1920, 1080], "position": [960, 540], "layers": [card, top]}
        self.near(self.px([g], (240, 135)), self.GREEN)
        self.near(self.px([g], (160, 135)), self.RED)


if __name__ == "__main__":
    unittest.main()
