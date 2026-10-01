"""Skill serving with hash verification (mirror of the AE connector's manifest).

Served: every directory named fusion-* under the skills root (default ~/.agents/skills), plus use-fusion (the connector's
own entry skill, which documents the scene builder). The manifest
(skills-manifest.json in the project) records sha256 + size of every file; reads verify the hash, so a
file edited after the manifest was built is refused until `fusion-connector skills-manifest` runs."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from . import config

SKIP = re.compile(r"(^|/)(\.|__pycache__)|\.pyc$|\.bak|~$")
PAGE = 34000  # chars per fu_get_skill page: stays under the MCP output budget after JSON escaping


def headings(text):
    """Markdown headings outside code fences: [{level, title, offset, chars}] where chars runs to the next
    heading of the same or a higher level."""
    out, fence, pos = [], False, 0
    for line in text.splitlines(keepends=True):
        st = line.lstrip()
        if st.startswith("```") or st.startswith("~~~"):
            fence = not fence
        elif not fence:
            m = re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if m:
                out.append({"level": len(m.group(1)), "title": m.group(2).strip(), "offset": pos})
        pos += len(line)
    for i, x in enumerate(out):
        nxt = next((y["offset"] for y in out[i + 1:] if y["level"] <= x["level"]), len(text))
        x["chars"] = nxt - x["offset"]
    return out


def find_section(heads, query):
    """Heading match: exact, then prefix, then substring (case-insensitive); '§16', 'R8', 'Phase D' all work."""
    q = query.strip().lower().lstrip("#").strip()
    for test in (lambda t: t == q, lambda t: t.startswith(q), lambda t: q in t):
        for x in heads:
            if test(x["title"].lower()):
                return x
    return None


def heads_start(section, heads):
    hit = find_section(heads, section)
    return hit["offset"] if hit else 0


def served(name):
    """fusion-* skills and use-fusion [fusion_v2 F1: fu_get_skill did not serve the entry skill]."""
    return name.startswith("fusion-") or name == "use-fusion"


def build_manifest(root=None, path=None):
    root = os.path.realpath(root or config.skills_root())
    skills = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not (served(name) and os.path.isfile(os.path.join(d, "SKILL.md"))):
            continue
        docs, files = {}, {}
        for dp, dns, fns in os.walk(d):
            dns[:] = sorted(x for x in dns if not x.startswith(".") and x != "__pycache__")
            for fn in sorted(fns):
                full = os.path.join(dp, fn)
                rel = os.path.relpath(full, d).replace(os.sep, "/")
                if SKIP.search(rel):
                    continue
                data = Path(full).read_bytes()
                h = hashlib.sha256(data).hexdigest()
                if rel.endswith(".md"):
                    docs[rel] = h
                else:
                    files[rel] = {"sha256": h, "bytes": len(data)}
        desc = _description(os.path.join(d, "SKILL.md"))
        skills.append({"name": name, "description": desc, "documents": docs, "files": files})
    man = {"schemaVersion": 1, "root": root, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "skills": skills}
    with open(path or config.MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1)
    return man


def _description(skill_md):
    text = Path(skill_md).read_text(encoding="utf-8")
    m = re.search(r"^description:\s*(.+?)(?=^\w[\w-]*:|^---)", text, re.S | re.M)
    if not m:
        return ""
    d = m.group(1).strip()
    if d.startswith(("|", ">")):
        d = d[1:].strip()
    return " ".join(d.strip("'\"").split())


class SkillStore:
    def __init__(self, path=None):
        path = path or config.MANIFEST_PATH
        root = os.path.realpath(config.skills_root())
        if not os.path.exists(path):
            build_manifest(root, path)
        self.man = json.loads(Path(path).read_text(encoding="utf-8"))
        present = sorted(n for n in os.listdir(root) if served(n) and os.path.isfile(os.path.join(root, n, "SKILL.md")))
        if self.man.get("root") != root or present != sorted(x["name"] for x in self.man["skills"]):
            self.man = build_manifest(root, path)  # new/removed skills are picked up; edited files still fail the hash
        self.root = self.man["root"]

    def index(self):
        return {"root": self.root, "built": self.man["built"],
                "skills": [{"name": s["name"], "description": s["description"],
                            "references": sorted(k for k in s["documents"] if k != "SKILL.md"),
                            "files": sorted(s["files"])} for s in self.man["skills"]],
                "start": "use-fusion for the connector and the scene builder; fusion-motion-design (router) for any build; fusion-reference for API/IDs; references/fusion-realities.md (an index of three parts) before the first mutation.",
                "paging": "documents over ~34k chars come back in pages (nextOffset); references over 40k are split into <name>-N.md parts behind an index; section: '<heading>' finds a section in the parts"}

    def skill(self, name):
        for s in self.man["skills"]:
            if s["name"] == name:
                return s
        names = [s["name"] for s in self.man["skills"]]
        raise KeyError(f"Unknown skill '{name}'. Available: {', '.join(names)}. Call fu_get_skill with no arguments for the index.")

    def _locate(self, skill, rel, expected):
        full = os.path.realpath(os.path.join(self.root, skill["name"], rel))
        if not full.startswith(os.path.join(self.root, skill["name"]) + os.sep):
            raise PermissionError("path escapes the skill folder")
        data = Path(full).read_bytes()
        h = hashlib.sha256(data).hexdigest()
        if h != expected:
            raise ValueError(f"Skill integrity mismatch: {skill['name']}/{rel} changed since the manifest was built "
                             f"({self.man['built']}). Run `fusion-connector skills-manifest` (or restart the server) after editing skills.")
        return full, data, h

    def read(self, name, document="SKILL.md", section=None, offset=None, limit=None, toc=False):
        """[rebuild F1] Big references (70-130k chars) overflowed the MCP output limit. Documents over PAGE chars
        come back one page at a time (with nextOffset and the heading TOC); section returns one heading's
        section, offset/limit a char slice, toc only the headings."""
        s = self.skill(name)
        if document not in s["documents"]:
            raise KeyError(f"Unknown reference '{document}' for '{name}'. References: {sorted(k for k in s['documents'] if k != 'SKILL.md')[:60]}")
        _, data, h = self._locate(s, document, s["documents"][document])
        text = data.decode("utf-8")
        out = {"name": name, "document": document, "sha256": h, "chars": len(text)}
        heads = headings(text)
        if toc:
            out["toc"] = heads
            return out
        start, end = 0, len(text)
        if section:
            hit = find_section(heads, section)
            if hit is None:  # a split reference: <stem>.md is an index, the sections live in <stem>-<n>.md
                stem = document[:-3] if document.endswith(".md") else document
                parts = sorted((d for d in s["documents"] if re.fullmatch(re.escape(stem) + r"-\d+\.md", d)),
                               key=lambda d: int(re.search(r"-(\d+)\.md$", d).group(1)))
                for part in parts:
                    _, pdata, _ = self._locate(s, part, s["documents"][part])
                    if find_section(headings(pdata.decode("utf-8")), section):
                        return self.read(name, part, section=section, offset=offset, limit=limit)
            if hit is None:
                raise KeyError(f"No heading matching '{section}' in {name}/{document}. Headings: " +
                               "; ".join(x["title"] for x in heads if x["level"] <= 3)[:1500])
            start, end = hit["offset"], hit["offset"] + hit["chars"]
            out["section"] = hit["title"]
        if offset is not None:
            start = max(0, min(len(text), start + int(offset))) if section else max(0, min(len(text), int(offset)))
        size = int(limit) if limit else PAGE
        stop = min(end, start + size)
        if not limit:  # page on a line boundary, and keep the JSON-escaped page under the response budget
            while True:
                if stop < end:
                    nl = text.rfind("\n", start, stop)
                    stop = nl + 1 if nl > start else stop
                if len(json.dumps(text[start:stop])) <= PAGE + 2000 or stop - start < 2000:
                    break
                stop = start + int((stop - start) * 0.9)
        out["content"] = text[start:stop]
        out["range"] = [start, stop]
        if stop < end:
            out["truncated"] = True
            out["nextOffset"] = stop - (heads_start(section, heads) if section else 0)
            out["how"] = ("more of this section: same call with offset %d" if section else "next page: offset %d") % out["nextOffset"] + \
                "; toc: true lists headings; section: '<heading text>' returns one section"
            if not section and offset is None:
                out["toc"] = [x for x in heads if x["level"] <= 2] or heads[:40]
        if document == "SKILL.md" and not section and offset is None and not limit:  # the listing only with the entry doc
            out["references"] = sorted(k for k in s["documents"] if k != "SKILL.md")
            out["files"] = sorted(s["files"])
        return out

    def resolve_file(self, name, path):
        s = self.skill(name)
        if path not in s["files"]:
            raise KeyError(f"Unknown file '{path}' for '{name}'. Files: {sorted(s['files'])[:80]}")
        full, _, h = self._locate(s, path, s["files"][path]["sha256"])
        return {"name": name, "path": path, "absolute_path": full, "sha256": h, "bytes": s["files"][path]["bytes"]}
