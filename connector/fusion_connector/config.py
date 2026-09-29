"""Paths and capability policy for the Use Fusion connector.

Policy env vars (mirror of AE_MCP_*):
  FUSION_MCP_READONLY=1             nothing may modify the Resolve project (render is withheld too:
                                    it needs a temporary Saver)
  FUSION_MCP_ALLOW_CATEGORIES=a,b   operation-category allowlist
  FUSION_MCP_ENABLE_EVAL=1          opt in to eval.python / eval.lua (arbitrary code in Resolve)
  FUSION_MCP_PROJECT_ALLOWLIST=a,b  mutating ops only run when the current project name is listed
  FUSION_MCP_ALLOW_TEMPLATE_INSTALL=1  opt in to template.install (writes Resolve Templates folders)
  FUSION_MCP_AUTO_DISMISS_RENDER_MODAL=0  turn OFF the automatic OK click on Resolve's "Render completed!"
                                    modal (default on; needs Accessibility permission for the server process;
                                    clicks only windows containing that text)
Other:
  FUSION_MCP_SKILLS_ROOT            where fusion-* skills live (default ~/.agents/skills, then ../skills
                                    beside the connector, as in the open-fusion-mcp repo)
  FUSION_MCP_OUT_DIR                default render/export dir (default <project>/out)
  FUSION_MCP_CACHE_DIR              disk-cache root (cache.*; default ~/Movies/FusionCache); cache.clear deletes only inside it
  RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB  standard Resolve scripting overrides
"""
import os

__version__ = "0.1.0"
SERVER_ID = "use-fusion"
SERVER_TITLE = "Use Fusion"

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
MANIFEST_PATH = os.path.join(PROJECT_DIR, "skills-manifest.json")
MODULES_DIR = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
REPO_SKILLS = os.path.join(os.path.dirname(PROJECT_DIR), "skills")  # open-fusion-mcp layout: connector/ beside skills/
TEMPLATES_ROOT = os.path.expanduser(os.environ.get("FUSION_MCP_TEMPLATES_ROOT") or
                                    "~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates")


def skills_root():
    env = os.environ.get("FUSION_MCP_SKILLS_ROOT")
    if env:
        return os.path.expanduser(env)
    home = os.path.expanduser("~/.agents/skills")
    if os.path.isdir(os.path.join(home, "fusion-reference")):
        return home
    return REPO_SKILLS if os.path.isdir(os.path.join(REPO_SKILLS, "fusion-reference")) else home


def data_file(name):
    return os.path.join(skills_root(), "fusion-reference", "data", name)


def scripts_dir():
    return os.path.join(skills_root(), "fusion-motion-design", "scripts")


def out_dir():
    d = os.environ.get("FUSION_MCP_OUT_DIR") or os.path.join(PROJECT_DIR, "out")
    os.makedirs(d, exist_ok=True)
    return d


def cache_dir():
    return os.path.realpath(os.path.expanduser(os.environ.get("FUSION_MCP_CACHE_DIR") or "~/Movies/FusionCache"))


# ---------------------------------------------------------------- policy

def _flag(name):
    return os.environ.get(name, "").strip() == "1"


def _csv(name):
    raw = os.environ.get(name, "").strip()
    items = [s.strip() for s in raw.split(",") if s.strip()]
    return set(items) or None


def read_only():
    return _flag("FUSION_MCP_READONLY")


def eval_enabled():
    return _flag("FUSION_MCP_ENABLE_EVAL") and not read_only()


def template_install_enabled():
    return _flag("FUSION_MCP_ALLOW_TEMPLATE_INSTALL") and not read_only()


def auto_dismiss():
    return os.environ.get("FUSION_MCP_AUTO_DISMISS_RENDER_MODAL", "1").strip() != "0"


def allowed_categories():
    return _csv("FUSION_MCP_ALLOW_CATEGORIES")


def project_allowlist():
    return _csv("FUSION_MCP_PROJECT_ALLOWLIST")


def policy():
    """Snapshot shipped to the worker with every call."""
    return {"readonly": read_only(), "projects": sorted(project_allowlist() or []) or None,
            "eval": eval_enabled(), "template_install": template_install_enabled(), "auto_dismiss": auto_dismiss()}


def deny_op(op):
    """(message, hint) when the policy refuses op, else None. Shared by fu_catalog, fu_do, batch.run."""
    if read_only() and not op.read:
        return (f"operation '{op.name}' modifies the project (or adds a temporary tool) and FUSION_MCP_READONLY=1 is set",
                "Unset FUSION_MCP_READONLY to allow mutations; fu_catalog lists only read operations in read-only mode.")
    cats = allowed_categories()
    if cats and op.category not in cats:
        return (f"operation category '{op.category}' is not in FUSION_MCP_ALLOW_CATEGORIES",
                "Allowed categories: " + ", ".join(sorted(cats)))
    if op.category == "eval" and not eval_enabled():
        return ("eval operations are disabled on this server",
                "Set FUSION_MCP_ENABLE_EVAL=1 (and unset FUSION_MCP_READONLY) to allow arbitrary Python/Lua, "
                "or use a dedicated operation from fu_catalog.")
    if op.name == "template.install" and not template_install_enabled():
        return ("template.install is disabled on this server (it writes into Resolve's Templates folders)",
                "Set FUSION_MCP_ALLOW_TEMPLATE_INSTALL=1 to allow it; template.write_macro writes the file anywhere else.")
    return None


def policy_summary():
    parts = ["readonly=ON (no project mutations)" if read_only() else "readonly=off"]
    cats = allowed_categories()
    parts.append("categories=" + ("|".join(sorted(cats)) if cats else "all"))
    parts.append("eval=ENABLED" if eval_enabled() else "eval=disabled")
    pa = project_allowlist()
    parts.append("projects=" + ("|".join(sorted(pa)) if pa else "any"))
    parts.append("template.install=" + ("enabled" if template_install_enabled() else "disabled"))
    parts.append("render-modal auto-dismiss=" + ("on" if auto_dismiss() else "OFF"))
    return ", ".join(parts)
