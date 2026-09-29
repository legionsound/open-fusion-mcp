#!/usr/bin/env python3
"""Assemble connector/, skills/ and agents/ from the development sources. Re-runnable and idempotent.

Sources come from the environment (scripts/sync_from_dev.sh loads scripts/sync.local.env):
  CONNECTOR_SRC  the live connector checkout      SKILLS_SRC  folder holding the six fusion skills
  AGENTS_SRC     folder holding the example agent definitions (optional)

Steps: copy the include list into a fresh staging tree -> redact (private.json) -> apply patches/<root>/*.patch
(written against the redacted text, so they hold no private terms; skipped once the source already has them) ->
overlay overrides/ -> scan (scripts/audit.py) -> mirror into the repo. Only connector/, skills/ and agents/ are written. Local-only files (the harvested TSV dumps,
.venv, out/, skills-manifest.json) are kept and git-ignored. Exit 1 on any scan finding or patch conflict."""
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(HERE))
import audit  # noqa: E402

# ---------------------------------------------------------------- what ships

CONNECTOR = [                                   # relative to CONNECTOR_SRC; a trailing /** copies a folder
    "fusion_connector/**", "bin/fusion-connector", "bin/use-fusion-mcp", "requirements.txt", "PARITY.md",
    "scripts/parity.py",
    "tests/test_offline.py", "tests/test_layout.py", "tests/client.py", "tests/smoke.py", "tests/smoke_results.json",
    "tests/cache_live.py", "tests/layout_live.py", "tests/sb3_live.py", "tests/luajit.py", "tests/scenes/*.json",
    "tests/scenes/*.png",
]
# Files that must not ship for private reasons (a client's benchmark fixture) are listed as "root/path" globs
# under "exclude" in private.json, so their names stay out of tracked files too.
# Not copied at all: .venv/, out/, prior-art/ (third-party checkouts), study/ (another vendor's op registry),
# skill/ (stale copy; skills/use-fusion is canonical), GAPFIX.md / PROGRESS.md (dev logs with local paths),
# tests/*_results.json except smoke_results.json, the one-off live probes (gapfix_*, rematch_live, scene_live).
# fusion-cleanup and fusion-matte-painting stay in the development sources only: their text still follows the
# Higgsfield After Effects skills too closely to publish (see docs/maintaining.md). patches/skills/ removes the
# router lines that point at them.
SKILLS = ["fusion-motion-design", "fusion-reference", "use-fusion", "fusion-figma-transfer"]
AGENTS = ["fusion-motion-builder.md", "fusion-connector-dev.md", "fusion-researcher.md"]
ALWAYS_EXCLUDE = [".DS_Store", "__pycache__", "*.pyc", "*.bak", "*~", ".venv", "out", "*.log"]
LOCAL_ONLY = [                                  # copied for local tests, git-ignored, never committed
    r"skills/fusion-reference/data/.*\.(tsv|pyi)",
]
PRESERVE = [                                    # repo files the mirror never deletes
    r"connector/\.venv(/.*)?", r"connector/out(/.*)?", r"connector/skills-manifest\.json",
    r".*/__pycache__(/.*)?", r".*\.pyc", r".*\.DS_Store",
]
TEXT = audit.TEXT


def excluded(rel):
    return any(fnmatch.fnmatch(part, pat) for part in rel.split("/") for pat in ALWAYS_EXCLUDE)


def expand(src, patterns):
    out = []
    for pat in patterns:
        if pat.endswith("/**"):
            base = os.path.join(src, pat[:-3])
            for dp, dns, fns in os.walk(base):
                dns[:] = sorted(d for d in dns if not excluded(d))
                out += [os.path.relpath(os.path.join(dp, f), src) for f in sorted(fns)]
        else:
            hits = sorted(os.path.relpath(p, src) for p in glob.glob(os.path.join(src, pat)))
            if not hits and not any(c in pat for c in "*?["):
                raise SystemExit(f"sync: missing source file {os.path.join(src, pat)}")
            out += hits
    return [r for r in out if not excluded(r)]


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------- steps

def stage(env, tmp, private_excludes=()):
    plan = [("connector", env["CONNECTOR_SRC"], expand(env["CONNECTOR_SRC"], CONNECTOR))]
    plan.append(("skills", env["SKILLS_SRC"], expand(env["SKILLS_SRC"], [s + "/**" for s in SKILLS])))
    if env.get("AGENTS_SRC"):
        plan.append(("agents", env["AGENTS_SRC"], expand(env["AGENTS_SRC"], AGENTS)))
    n = 0
    for root, src, files in plan:
        for rel in files:
            if any(fnmatch.fnmatch(f"{root}/{rel}", pat) for pat in private_excludes):
                continue
            dst = os.path.join(tmp, root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(src, rel), dst)
            n += 1
    return [p[0] for p in plan], n


def run_patch(cwd, patch, *flags):
    return subprocess.run(["patch", "-p1", "-s", "-f", *flags, "-i", patch], cwd=cwd, capture_output=True, text=True)


def apply_patches(tmp):
    """patches/<root>/*.patch against the staged root. Already in the source (reverse applies) -> skipped."""
    report = []
    pdir = os.path.join(HERE, "patches")
    for root in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        for name in sorted(os.listdir(os.path.join(pdir, root))):
            if not name.endswith(".patch"):
                continue
            p, cwd = os.path.join(pdir, root, name), os.path.join(tmp, root)
            if run_patch(cwd, p, "-R", "--dry-run").returncode == 0:
                report.append(f"{root}/{name}: already in source, skipped")
            elif run_patch(cwd, p, "--dry-run").returncode == 0:
                run_patch(cwd, p)
                for dp, _, fns in os.walk(cwd):   # drop .orig backups from fuzzy applies
                    for f in fns:
                        if f.endswith((".orig", ".rej")):
                            os.remove(os.path.join(dp, f))
                report.append(f"{root}/{name}: applied")
            else:
                raise SystemExit(f"sync: patch {root}/{name} no longer applies to the source; refresh it "
                                 f"(or ask for it to be upstreamed):\n{run_patch(cwd, p, '--dry-run').stdout}")
    return report


def apply_overrides(tmp, sources):
    """overrides/<root>/<path> replaces (or adds) a staged file. overrides.json records the sha256 of the raw
    source file each override was written against; a changed source is reported so the override can be reviewed."""
    odir = os.path.join(HERE, "overrides")
    with open(os.path.join(HERE, "overrides.json"), encoding="utf-8") as f:
        known = json.load(f)
    report = []
    for dp, _, fns in os.walk(odir):
        for fn in fns:
            if fn == ".DS_Store":
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, odir)
            dst = os.path.join(tmp, rel)
            root, _, sub = rel.partition(os.sep)
            raw = os.path.join(sources.get(root) or "", sub)
            before = sha(raw) if sources.get(root) and os.path.exists(raw) else None
            expect = known.get(rel, {}).get("source_sha256")
            if before != expect:
                report.append(f"REVIEW {rel}: source changed since the override was written "
                              f"(recorded {str(expect)[:12]}, now {str(before)[:12]})")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(full, dst)
            report.append(f"{rel}: override applied")
    return report


def cap_at_sentence_start(m, repl):
    """Capitalize at a sentence start: after . ! ?, after a list/heading/table marker, or at the start of a
    paragraph. A wrapped line that continues the previous line's sentence stays lower case."""
    cap = repl[:1].upper() + repl[1:]
    head = m.string[:m.start()]
    line = head[head.rfind("\n") + 1:]
    if re.fullmatch(r"[\s>*\-|#0-9.)`]*", line):
        if line.strip():                                   # "- ", "1. ", "# ", "| " ...
            return cap
        prev = head[:head.rfind("\n")].rstrip(" \t") if "\n" in head else ""
        if not prev or prev.endswith("\n") or prev[-1] in ".!?:|":
            return cap                                     # new paragraph, or the previous line ended a sentence
        return repl                                        # continuation of a wrapped sentence
    if re.search(r"[.!?]\s+$", head[-4:] if head else ""):
        return cap
    return repl


def redact(tmp, rules):
    """rules: [[regex, replacement], ...] from private.json; a replacement starting with 'the ' is capitalized at
    a sentence start. LOCAL_ONLY files are not touched (they never ship)."""
    compiled = [(re.compile(rx), rep) for rx, rep in rules]
    changed = 0
    for dp, _, fns in os.walk(tmp):
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, tmp)
            if not audit.is_text(rel) or any(re.fullmatch(s, rel) for s in LOCAL_ONLY):
                continue
            with open(full, encoding="utf-8") as f:
                text = f.read()
            new = text
            for rx, rep in compiled:
                if rep.startswith("the "):
                    new = rx.sub(lambda m, rep=rep: cap_at_sentence_start(m, rep), new)
                else:
                    new = rx.sub(rep, new)
            if new != text:
                with open(full, "w", encoding="utf-8") as f:
                    f.write(new)
                changed += 1
    return changed


def mirror(tmp, roots):
    """Make REPO/<root> equal staging/<root>, keeping PRESERVE paths. Returns (added, updated, removed)."""
    added = updated = removed = 0
    for root in roots:
        src_root, dst_root = os.path.join(tmp, root), os.path.join(REPO, root)
        want = set()
        for dp, _, fns in os.walk(src_root):
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), src_root)
                want.add(rel)
                s, d = os.path.join(src_root, rel), os.path.join(dst_root, rel)
                if os.path.exists(d) and sha(s) == sha(d) and os.stat(s).st_mode == os.stat(d).st_mode:
                    continue
                if os.path.exists(d):
                    updated += 1
                else:
                    added += 1
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)
        for dp, dns, fns in os.walk(dst_root, topdown=False):
            for fn in fns:
                rel = os.path.relpath(os.path.join(dp, fn), dst_root)
                if rel not in want and not any(re.fullmatch(p, f"{root}/{rel}") for p in PRESERVE):
                    os.remove(os.path.join(dp, fn))
                    removed += 1
            if dp != dst_root and not os.listdir(dp):
                os.rmdir(dp)
    return added, updated, removed


def main():
    env = {k: os.path.expanduser(os.environ.get(k, "")) for k in ("CONNECTOR_SRC", "SKILLS_SRC", "AGENTS_SRC")}
    for k in ("CONNECTOR_SRC", "SKILLS_SRC"):
        if not os.path.isdir(env[k]):
            raise SystemExit(f"sync: {k} is not a folder ({env[k]!r}); set it in scripts/sync.local.env")
    private = os.path.join(HERE, "private.json")
    if not os.path.exists(private):
        raise SystemExit("sync: scripts/sync/private.json is missing (local-only redaction rules and scan terms; "
                         "see private.example.json). Refusing to sync without them.")
    with open(private, encoding="utf-8") as f:
        priv = json.load(f)
    rules = priv.get("redact", [])
    tmp = tempfile.mkdtemp(prefix="ofm_sync_")
    try:
        roots, n = stage(env, tmp, priv.get("exclude", []))
        print(f"staged {n} files from {len(roots)} sources")
        print(f"redacted {redact(tmp, rules)} files")
        for line in apply_patches(tmp) + apply_overrides(tmp, {"connector": env["CONNECTOR_SRC"], "skills": env["SKILLS_SRC"],
                                                                "agents": env.get("AGENTS_SRC")}):
            print("  " + line)
        found = audit.scan(tmp, skip=LOCAL_ONLY)
        if found:
            for rel, ln, label, m in found:
                print(f"  FINDING {rel}:{ln}: {label}: {m}")
            raise SystemExit(f"sync: {len(found)} scan findings; nothing was written to the repo. Add a redaction "
                             "rule, an override or an exclude, then re-run.")
        a, u, r = mirror(tmp, roots)
        print(f"repo: {a} added, {u} updated, {r} removed")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
