#!/usr/bin/env python3
"""Pre-public audit checks for this repo (re-runnable; AUDIT.md records the verdicts).

  python3 scripts/audit.py                      scan every tracked file (git ls-files) for secrets,
                                                personal data, client names and local paths
  python3 scripts/audit.py --manual FILE        + verbatim overlap of skills/ with a manual text export
  python3 scripts/audit.py --higgsfield DIR,..  + near-verbatim overlap of skills/ with the Higgsfield AE skills

scan() is also the gate in scripts/sync/sync.py: a sync that would bring a finding into the repo stops.
No third-party scanner is required (gitleaks and trufflehog were not installed when this was written); the
generic patterns below plus the private terms are the checklist.
Overlap: exact runs of >= 12 words (8-word shingles chained) and near-verbatim windows (40 words with
>= 50 % of their 5-word shingles found in the reference)."""
import argparse
import json
import os
import re
import subprocess
import sys

TEXT = (".py", ".md", ".json", ".setting", ".yaml", ".yml", ".txt", ".sh", ".applescript", ".toml", ".cfg",
        ".example", ".gitignore", "")
# example domains, plus the project's public contact address (CODE_OF_CONDUCT.md)
ALLOW_EMAIL = re.compile(r"(@(example\.(com|org)|anthropic\.com)|^legionsoundofficial@gmail\.com)$")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# (label, pattern). Every hit is a finding: fix the source or add a sync redaction. Patterns are written so they
# do not match their own source line. Private terms (people, clients, local layout) are NOT listed here: they
# live in the untracked scripts/sync/private.json (see private.example.json), so the checklist leaks nothing.
PATTERNS = [
    ("home path", re.compile(r"/Users/(?!<?username>?/|you/|Shared/)[A-Za-z0-9._-]+")),
    ("temp path", re.compile(r"/privat[e]/tmp/|/var/folder[s]/")),
    ("resolve project other than Testbed", re.compile(
        r"""(?:make_current|LoadProject|GetProjectByName|project\.load)\(\s*["'](?!Testbed["']|\{)[^"']+["']""")),
    ("aws key", re.compile(r"AKI[A][0-9A-Z]{16}")),
    ("openai/anthropic style key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("google key", re.compile(r"\bAIz[a][0-9A-Za-z_-]{35}")),
    ("hugging face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("private key block", re.compile(r"-----BEGI[N] [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.")),
    ("assigned secret", re.compile(r"""(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*["'][^"'\s]{12,}["']""")),
]
PRIVATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync", "private.json")


def private_patterns():
    """Local-only scan terms: {"scan": [[label, regex], ...]} in scripts/sync/private.json (untracked)."""
    if not os.path.exists(PRIVATE):
        return []
    with open(PRIVATE, encoding="utf-8") as f:
        return [(label, re.compile(rx)) for label, rx in json.load(f).get("scan", [])]


def is_text(path):
    return os.path.splitext(path)[1].lower() in TEXT


def scan_text(rel, text, patterns):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for label, rx in patterns:
            for m in rx.finditer(line):
                out.append((rel, n, label, m.group(0)))
        for m in EMAIL.finditer(line):
            if not ALLOW_EMAIL.search(m.group(0)):
                out.append((rel, n, "email", m.group(0)))
    return out


def scan(root, files=None, skip=()):
    """Findings [(relpath, line, label, match)] for text files under root (or the given relative paths).
    skip: regexes (full match on the relative path) for local-only files that are never committed."""
    if files is None:
        files = []
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in (".git", ".venv", "__pycache__", "out")]
            files += [os.path.relpath(os.path.join(dp, f), root) for f in fns]
    found, patterns = [], PATTERNS + private_patterns()
    for rel in sorted(files):
        if not is_text(rel) or any(re.fullmatch(s, rel) for s in skip):
            continue
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as f:
                text = f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        found += scan_text(rel, text, patterns)
    return found


# ---------------------------------------------------------------- overlap

def toks(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower().replace("’", "'"))


def read_corpus(paths, n):
    grams = set()
    for p in paths:
        walk = os.walk(p) if os.path.isdir(p) else [(os.path.dirname(p), [], [os.path.basename(p)])]
        for dp, _, fns in walk:
            for fn in fns:
                if fn.endswith((".md", ".txt")):
                    with open(os.path.join(dp, fn), encoding="utf-8", errors="ignore") as f:
                        ws = toks(f.read())
                    grams |= {" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)}
    return grams


def spans(flags, width):
    out, i = [], 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            out.append((i, j + width))
            i = j + 1
        else:
            i += 1
    return out


def overlap(ref_paths, target_root, min_words=12, window=40, frac=0.5):
    """Per markdown file: exact verbatim words (runs >= min_words) and near-verbatim words (dense windows)."""
    exact_ref, near_ref = read_corpus(ref_paths, 8), read_corpus(ref_paths, 5)
    rows = []
    for dp, _, fns in os.walk(target_root):
        for fn in sorted(fns):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            with open(p, encoding="utf-8") as f:
                ws = toks(f.read())
            ex = [" ".join(ws[i:i + 8]) in exact_ref for i in range(len(ws) - 7)]
            exact = [s for s in spans(ex, 8) if s[1] - s[0] >= min_words]
            hit = [" ".join(ws[i:i + 5]) in near_ref for i in range(len(ws) - 4)]
            dense = [False] * len(hit)
            for i in range(max(0, len(hit) - window + 1)):
                if sum(hit[i:i + window]) >= frac * window:
                    dense[i:i + window] = [True] * window
            near = spans(dense, 5)
            rows.append({"file": os.path.relpath(p, target_root), "words": len(ws),
                         "exact": sum(b - a for a, b in exact), "longest_exact": max((b - a for a, b in exact), default=0),
                         "near": sum(b - a for a, b in near), "longest_near": max((b - a for a, b in near), default=0)})
    return rows


def print_overlap(title, rows, show=0.0):
    tw = sum(r["words"] for r in rows)
    te, tn = sum(r["exact"] for r in rows), sum(r["near"] for r in rows)
    print(f"\n## {title}: {len(rows)} files, {tw} words; exact runs {te} ({100 * te / max(1, tw):.1f} %), "
          f"near-verbatim {tn} ({100 * tn / max(1, tw):.1f} %)")
    print("| file | words | exact | longest exact | near-verbatim | % | longest near |")
    print("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: -r["near"] / max(1, r["words"])):
        pct = 100 * r["near"] / max(1, r["words"])
        if pct > show or r["longest_exact"] >= 25:
            print(f"| {r['file']} | {r['words']} | {r['exact']} | {r['longest_exact']} | {r['near']} | {pct:.1f} | {r['longest_near']} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manual", help="plain-text export of the Fusion manual")
    ap.add_argument("--higgsfield", help="comma-separated folders of the Higgsfield After Effects skills")
    a = ap.parse_args()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True).stdout.split("\n")
    files = [f for f in files if f]
    found = scan(repo, files)
    print(f"# scan: {len(files)} tracked files, {len(found)} findings"
          + ("" if os.path.exists(PRIVATE) else " (generic patterns only: scripts/sync/private.json not found)"))
    for rel, n, label, m in found:
        print(f"{rel}:{n}: {label}: {m}")
    skills = os.path.join(repo, "skills")
    if a.manual:
        print_overlap("manual overlap (skills/ vs manual)", overlap([a.manual], skills), show=0.5)
    if a.higgsfield:
        print_overlap("Higgsfield overlap (skills/ vs AE skills)", overlap(a.higgsfield.split(","), skills), show=5.0)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
