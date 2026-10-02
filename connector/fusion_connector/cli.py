"""fusion-connector CLI: doctor | config | skills-manifest | serve."""
import json
import os
import shutil
import subprocess
import sys

from . import config, diag

PY = sys.executable
SERVER = os.path.join(config.PROJECT_DIR, "bin", "use-fusion-mcp")


def doctor(live=True):
    ok = True
    rows = []

    def row(name, good, detail):  # good None = WARN (reported, not a failure)
        nonlocal ok
        ok = ok and good is not False
        rows.append(("WARN" if good is None else "OK  " if good else "FAIL") + f"  {name}: {detail}")

    row("python", sys.version_info >= (3, 9), f"{sys.version.split()[0]} at {PY}")
    try:
        import mcp  # noqa
        from importlib.metadata import version
        row("mcp sdk", True, version("mcp"))
    except Exception as e:  # noqa
        row("mcp sdk", False, str(e))
    row("scripting module", os.path.exists(os.path.join(config.MODULES_DIR, "DaVinciResolveScript.py")), config.MODULES_DIR)
    root = config.skills_root()
    for s in ("fusion-motion-design", "fusion-reference"):
        row(f"skill {s}", os.path.isfile(os.path.join(root, s, "SKILL.md")), os.path.join(root, s))
    from .schema import tsv_available
    have = tsv_available()
    row("Fusion data tables", have, config.data_file("fusion-21.1-inputs.tsv")
        + ("" if have else " missing; generate them from your Resolve install: skills/fusion-reference/data/README.md"))
    try:
        from .skills import build_manifest
        m = build_manifest()
        row("skills manifest", True, f"{len(m['skills'])} skills hashed -> {config.MANIFEST_PATH}")
    except Exception as e:  # noqa
        row("skills manifest", False, str(e))
    try:
        from .ops import OPS
        from .ops import build
        row("operation catalog", True, f"{len(OPS)} operations" + (f" (builders unavailable: {build._BUILDER_ERR})" if build._BUILDER_ERR else ""))
    except Exception as e:  # noqa
        row("operation catalog", False, str(e))
    r = subprocess.run(["osascript", "-e", 'tell application "System Events" to count processes'], capture_output=True, text=True)
    row("System Events (render modal auto-dismiss " + ("on" if config.auto_dismiss() else "OFF") + ")", r.returncode == 0 or not config.auto_dismiss(), "ok" if r.returncode == 0 else (r.stderr.strip() or "no Accessibility permission"))
    if live:  # lsof + ps, no Resolve call: a held port makes the scriptapp call below hang, so it is skipped then
        v = diag.check()
        row("scripting port", {"ok": True, "problem": False}.get(v["status"]), v["detail"])
        if v["status"] == "problem":
            live = False
            row("Resolve reachable", False, "not tried: a scripting client would hang (see scripting port)")
    if live:
        sys.path.append(config.MODULES_DIR)
        try:
            import DaVinciResolveScript as dvr
            res = dvr.scriptapp("Resolve")
            if res is None:
                row("Resolve reachable", False, "not reachable: open DaVinci Resolve Studio and set Preferences > System > General > External scripting using = Local")
            else:
                prod = res.GetProductName()
                row("Resolve reachable", True, f"{prod} {res.GetVersionString()}")
                row("Resolve Studio", "Studio" in (prod or ""), prod)
                p = res.GetProjectManager().GetCurrentProject()
                page = res.GetCurrentPage()
                row("project", p is not None, p.GetName() if p else "none open")
                row("UI not blocked", page is not None, f"page {page}" if page else "GetCurrentPage returned None: a modal dialog is open in Resolve")
                pa = config.project_allowlist()
                if pa and p is not None:
                    row("project allowlist", p.GetName() in pa, f"{p.GetName()} vs {sorted(pa)} (mutations refused outside it)")
        except Exception as e:  # noqa
            row("Resolve reachable", False, str(e))
    row("policy", True, config.policy_summary())
    print("\n".join(rows))
    return 0 if ok else 1


def config_cmd():
    env = {"FUSION_MCP_PROJECT_ALLOWLIST": "Testbed"}
    cmd = ["claude", "mcp", "add", "use-fusion", "--scope", "user"] + sum((["-e", f"{k}={v}"] for k, v in env.items()), []) + ["--", SERVER]
    print("# Claude Code registration (id use-fusion, display name 'Use Fusion'):")
    print(" ".join(cmd))
    print("\n# Widen or clear the project allowlist by editing FUSION_MCP_PROJECT_ALLOWLIST (comma-separated) or removing -e.")
    print("# Other env: FUSION_MCP_READONLY=1, FUSION_MCP_ALLOW_CATEGORIES=a,b, FUSION_MCP_ENABLE_EVAL=1, FUSION_MCP_ALLOW_TEMPLATE_INSTALL=1, FUSION_MCP_AUTO_DISMISS_RENDER_MODAL=0 (default on: clicks OK only on Resolve's 'Render completed!' windows; needs Accessibility permission for the server process), FUSION_MCP_SKILLS_ROOT=...")
    print("\n# Generic MCP client JSON:")
    print(json.dumps({"mcpServers": {"use-fusion": {"command": SERVER, "args": [], "env": env}}}, indent=2))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "help"
    if cmd == "doctor":
        return doctor(live="--offline" not in argv)
    if cmd == "config":
        return config_cmd()
    if cmd == "skills-manifest":
        from .skills import build_manifest
        m = build_manifest()
        print(f"{len(m['skills'])} skills, {sum(len(s['documents']) + len(s['files']) for s in m['skills'])} files hashed -> {config.MANIFEST_PATH}")
        return 0
    if cmd == "serve":
        from .server import main as serve
        serve()
        return 0
    print("usage: fusion-connector doctor [--offline] | config | skills-manifest | serve")
    return 0 if cmd in ("help", "-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main())
