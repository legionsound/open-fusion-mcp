"""Scripting-port diagnosis from lsof and ps (no Resolve call, so it answers while Resolve's scripting hangs).

[open-fusion-mcp#8] After a Resolve restart an orphaned Workflow Integration plugin (Electron, parent PID 1) and the old
`fuscript -s` (parent PID 1) still held TCP 49152 through one inherited socket; the new Resolve listened on 49153 and every
scripting client hung. Healthy: Resolve and its child `fuscript -s` hold 49152. A plugin Electron launched by the RUNNING
Resolve also has parent PID 1 and shares that socket (seen live), so a holder counts as Resolve's by lineage or by socket."""
import os
import re
import shutil
import subprocess
import sys

PORTS = (49152, 49153)
_RESOLVE = re.compile(r"/(?:MacOS/Resolve|bin/resolve)(?:\s|$)")
_PLUGIN = re.compile(r"Workflow Integration Plugins/([^/]+)/")
_LEFTOVER = re.compile(r"DaVinci Resolve|Blackmagic|fuscript|Workflow Integration", re.I)


def parse_lsof(text):
    """`lsof -nP -iTCP -sTCP:LISTEN` -> [(port, pid, socket device, command)] on PORTS."""
    out = []
    for line in (text or "").splitlines():
        p = line.split()
        if len(p) < 9 or p[-1] != "(LISTEN)" or not p[1].isdigit():
            continue
        port = p[-2].rsplit(":", 1)[-1]
        if port.isdigit() and int(port) in PORTS:
            out.append((int(port), int(p[1]), p[5], p[0].replace("\\x20", " ")))
    return out


def parse_ps(text):
    """`ps -A -o pid,ppid,command` -> {pid: (ppid, command)}."""
    out = {}
    for line in (text or "").splitlines():
        m = re.match(r"\s*(\d+)\s+(\d+)\s+(.*)$", line)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), m.group(3).strip())
    return out


def short(cmd):
    m = _PLUGIN.search(cmd)
    if m:
        return "Workflow Integration plugin " + m.group(1)
    exe, sep, args = cmd.partition(" -")
    return (os.path.basename(exe.strip()) + (" -" + args if sep else ""))[:60]


def analyze(lsof_text, ps_text):
    """-> {status: ok|problem|not-running|not-listening, resolve: [pid], ports: {port: [{pid, ppid, name, role}]},
    orphans: [...], detail, problem?, fix?}. role: resolve | child (descends from it) | shared (its socket, other lineage)
    | orphan."""
    procs = parse_ps(ps_text)
    resolve = sorted(p for p, (_, cmd) in procs.items() if _RESOLVE.search(cmd))

    def ours(pid):
        for _ in range(64):
            if pid in resolve:
                return True
            if pid not in procs or pid <= 1:
                return False
            pid = procs[pid][0]
        return False
    rows = parse_lsof(lsof_text)
    socks = {(port, dev) for port, pid, dev, _ in rows if ours(pid)}
    ports, cmds = {p: [] for p in PORTS}, {}
    for port, pid, dev, name in rows:
        if any(h["pid"] == pid for h in ports[port]):
            continue                      # IPv4 and IPv6 lines of one process
        ppid, cmds[pid] = procs.get(pid, (None, name))
        role = "resolve" if pid in resolve else "child" if ours(pid) else "shared" if (port, dev) in socks else "orphan"
        ports[port].append({"pid": pid, "ppid": ppid, "name": short(cmds[pid]), "role": role})
    mine = {p: any(h["role"] in ("resolve", "child") for h in ports[p]) for p in PORTS}
    bad = [h for h in ports[49152] if h["role"] == "orphan"]
    v = {"status": "ok", "resolve": resolve, "ports": {str(p): ports[p] for p in PORTS}, "orphans": bad}
    rs = "the running Resolve (pid %d)" % resolve[0] if resolve else ""
    if bad or (mine[49153] and not mine[49152]):
        who, one = " and ".join("pid %d (%s)" % (h["pid"], h["name"]) for h in bad), len(bad) == 1
        hang = "; scripting clients connect to 49152 and hang"
        if not bad:
            p = "%s registered on 49153, not 49152, where scripting clients look for it" % rs
        elif not resolve:
            p = "Resolve is not running and %s still %s port 49152%s" % (who, "holds" if one else "hold", hang)
        elif not mine[49152]:
            p = "port 49152 is held by %s, not by %s, which registered on 49153%s" % (who, rs, hang)
        else:
            p = "port 49152 is also held by %s, outside %s; scripting clients may reach it and hang" % (who, rs)
        if all(_LEFTOVER.search(cmds[h["pid"]]) for h in bad):
            why = ("it belongs" if one else "they belong") + " to a Resolve session that has exited"
        else:
            why = ("it is" if one else "they are") + " not part of the running Resolve"
        then = "quit and reopen Resolve" if resolve else "open Resolve"
        fix = ("quit %s (kill %s; a Workflow Integration helper can ignore that, then Force Quit it in Activity Monitor): %s; then %s "
               "so it registers on 49152") % ("that process" if one else "those processes", " ".join(str(h["pid"]) for h in bad), why,
                                               then) if bad else "quit and reopen Resolve so it registers on 49152"
        v.update(status="problem", problem=p, fix=fix)
        v["detail"] = "%s. Fix: %s" % (v["problem"], fix)
    elif not resolve:
        v.update(status="not-running", detail="Resolve is not running; 49152 is free")
    elif not mine[49152]:
        v.update(status="not-listening", detail="%s does not listen on 49152 (External scripting may be off, or Resolve is still starting)" % rs)
    else:
        v["detail"] = "49152: " + ", ".join("%s pid %d%s" % (h["name"], h["pid"], " (shares Resolve's socket)" if h["role"] == "shared" else "")
                                            for h in ports[49152])
    return v


def check(timeout=5.0):
    """Run lsof and ps and analyze. Skipped on Windows, when either command is missing, slow or fails."""
    if sys.platform.startswith("win"):
        return {"status": "skipped", "detail": "not checked on Windows"}
    path = os.pathsep.join([os.environ.get("PATH", ""), "/usr/sbin", "/usr/bin", "/bin"])
    exe = {n: shutil.which(n, path=path) for n in ("lsof", "ps")}
    if not all(exe.values()):
        return {"status": "skipped", "detail": "not checked: %s not found" % " and ".join(n for n, p in exe.items() if not p)}
    try:
        a = subprocess.run([exe["lsof"], "-nP", "-iTCP", "-sTCP:LISTEN"], capture_output=True, text=True, errors="replace", timeout=timeout)
        b = subprocess.run([exe["ps"], "-A", "-ww", "-o", "pid,ppid,command"], capture_output=True, text=True, errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return {"status": "skipped", "detail": "not checked: %s" % e}
    return analyze(a.stdout, b.stdout)


def timeout_hint(verdict=None):
    """For a TIMEOUT reply: problem + fix when an orphan holds the scripting port (or Resolve sits on 49153), else None."""
    v = verdict or check()
    return v["detail"] if v.get("status") == "problem" else None
