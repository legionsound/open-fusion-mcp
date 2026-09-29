"""Resolve and system memory, read from the OS (no Resolve call, so it works while Resolve is busy).

[rebuild B2/B3] Resolve sat at 26-28 GB after a 2,081-tool paste and many re-pastes/renders on a 32 GB
Mac; the same small comp went from 4-7 s/frame to 358 s/frame and a restart cleared it. This makes that
state visible before big pastes and renders."""
import os
import re
import subprocess
import time

_CACHE = {}
GB = 1024 ** 3


def _run(cmd, timeout=5):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:  # noqa
        return ""


def parse_footprint(text):
    m = re.search(r"phys_footprint:\s*(\d+)\s*B", text or "")
    p = re.search(r"phys_footprint_peak:\s*(\d+)\s*B", text or "")
    return (int(m.group(1)) if m else None), (int(p.group(1)) if p else None)


def parse_swap(text):
    m = re.search(r"used\s*=\s*([\d.]+)M", text or "")
    t = re.search(r"total\s*=\s*([\d.]+)M", text or "")
    return (float(m.group(1)) * 1024 ** 2 if m else None), (float(t.group(1)) * 1024 ** 2 if t else None)


def parse_vm_stat(text):
    page = re.search(r"page size of (\d+) bytes", text or "")
    occ = re.search(r"Pages occupied by compressor:\s*(\d+)", text or "")
    if not (page and occ):
        return None
    return int(occ.group(1)) * int(page.group(1))


def warn_threshold_gb(total_bytes):
    env = os.environ.get("FUSION_MCP_MEMORY_WARN_GB", "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return round(0.6 * (total_bytes or 32 * GB) / GB, 1)


def assess(resolve_fp, total, free_level, warn_gb):
    """-> warning text or None. Pure function (unit-tested)."""
    why = []
    if resolve_fp is not None and resolve_fp / GB >= warn_gb:
        why.append(f"Resolve holds {resolve_fp / GB:.1f} GB (warning at {warn_gb:g} GB of {(total or 0) / GB:.0f} GB)")
    if free_level is not None and free_level < 15:
        why.append(f"system free memory level {free_level} % (macOS is compressing/swapping)")
    if not why:
        return None
    return ("; ".join(why) + ". At this level renders slowed ~50x in the rebuild (4-7 s -> 358 s per frame) and Deliver "
            "stalled. First run system.purge_cache (frees Fusion's render cache, no restart). If Resolve stays above the "
            "threshold before big pastes, many renders or the final Deliver: project.save, then ask the user to approve a "
            "Resolve restart (quit and relaunch; after relaunch use project.load). Never restart without approval.")


def snapshot(process="Resolve", max_age=5.0):
    """{resolve: {pid, footprintGB, peakGB, residentGB, compressedEstGB} | None, system: {...}, warning?}."""
    now = time.time()
    if _CACHE.get("t") and now - _CACHE["t"] < max_age:
        return dict(_CACHE["v"])
    total = None
    try:
        total = int(_run(["sysctl", "-n", "hw.memsize"]).strip())
    except ValueError:
        pass
    level = None
    try:
        level = int(_run(["sysctl", "-n", "kern.memorystatus_level"]).strip())
    except ValueError:
        pass
    swap_used, swap_total = parse_swap(_run(["sysctl", "-n", "vm.swapusage"]))
    comp_bytes = parse_vm_stat(_run(["vm_stat"]))
    out = {"system": {"totalGB": round(total / GB, 1) if total else None, "freeLevelPct": level,
                      "swapUsedGB": round(swap_used / GB, 2) if swap_used is not None else None,
                      "compressorGB": round(comp_bytes / GB, 2) if comp_bytes is not None else None}}
    pid = (_run(["pgrep", "-x", process]).split() or [None])[0]
    res = None
    if pid:
        fp, peak = parse_footprint(_run(["footprint", "-p", pid, "--noCategories", "-f", "bytes"], timeout=10))
        rss = None
        try:
            rss = int(_run(["ps", "-o", "rss=", "-p", pid]).strip()) * 1024
        except ValueError:
            pass
        res = {"pid": int(pid), "footprintGB": round(fp / GB, 2) if fp else None, "peakGB": round(peak / GB, 2) if peak else None,
               "residentGB": round(rss / GB, 2) if rss else None,
               "compressedEstGB": round(max(0, fp - rss) / GB, 2) if fp and rss else None}
    out["resolve"] = res
    warn_gb = warn_threshold_gb(total)
    out["warnAtGB"] = warn_gb
    w = assess((res or {}).get("footprintGB") and res["footprintGB"] * GB, total, level, warn_gb)
    if w:
        out["warning"] = w
    _CACHE.update(t=now, v=out)
    return dict(out)


def brief(snap=None):
    """Compact block for fu_context and render results."""
    s = snap or snapshot()
    r = s.get("resolve") or {}
    b = {"resolveGB": r.get("footprintGB"), "compressedEstGB": r.get("compressedEstGB"),
         "swapUsedGB": s["system"].get("swapUsedGB"), "freeLevelPct": s["system"].get("freeLevelPct")}
    if s.get("warning"):
        b["warning"] = s["warning"]
    return b
