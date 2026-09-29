"""Core categories: project, timeline, page, comp, tool, input, modifier, expression, keyframe."""
import fnmatch
import json
import os
import re
import time

from .. import config
from ..schema import P
from .base import (iid_of, oid_of, COMP, FRAME, INPUT, TOOL, OpError, color, jv, kit, num, op)

# ================================================================ project / page / timeline


def project_summary(ctx):
    p = ctx.project()
    tls = []
    for i in range(1, p.GetTimelineCount() + 1):
        t = p.GetTimelineByIndex(i)
        tls.append({"name": t.GetName(), "videoTracks": t.GetTrackCount("video"),
                    "items": sum(len(t.GetItemListInTrack("video", k) or []) for k in range(1, t.GetTrackCount("video") + 1))})
    cur = p.GetCurrentTimeline()
    allowed = ctx.policy.get("projects")
    return {"name": p.GetName(), "allowlisted": (p.GetName() in allowed) if allowed else True,
            "timelines": tls, "currentTimeline": cur.GetName() if cur else None,
            "page": ctx.resolve.GetCurrentPage(),
            "settings": {k: p.GetSetting(k) for k in ("timelineResolutionWidth", "timelineResolutionHeight", "timelineFrameRate")}}


@op("project.info", "Project summary: name, allowlist status, timelines with item counts, current timeline and page (same payload as fu_project_info).",
    read=True, comp=False)
def project_info(ctx, a):
    return project_summary(ctx)


@op("project.save", "Save the current Resolve project (ProjectManager.SaveProject). Not undoable.", comp=False)
def project_save(ctx, a):
    ok = ctx.resolve.GetProjectManager().SaveProject()
    if not ok:
        raise OpError("OPERATION_FAILED", "SaveProject returned False")
    return {"saved": True, "project": ctx.project().GetName()}


@op("project.load", "Load another project (ProjectManager.LoadProject). Only projects on FUSION_MCP_PROJECT_ALLOWLIST (without an allowlist: confirm: true on the user's request). [rebuild F9] After a Resolve restart Resolve may open 'Untitled Project'; this brings the working project back. Resolve closes the current project: project.save it first if it has changes you keep. Runs from any project.",
    [P("name", "string", "Project name.", required=True), P("folder", "string", "Project Manager folder path 'A/B' (default: current folder, then root)."),
     P("confirm", "boolean", "Required when no project allowlist is configured.")], comp=False, any_project=True)
def project_load(ctx, a):
    name = a["name"]
    allowed = ctx.policy.get("projects")
    if allowed and name not in allowed:
        raise OpError("FORBIDDEN", f"project '{name}' is not in FUSION_MCP_PROJECT_ALLOWLIST", details={"allowlist": allowed})
    if not allowed and a.get("confirm") is not True:
        raise OpError("FORBIDDEN", "no project allowlist is configured: project.load runs only with confirm: true",
                      hint="Pass confirm: true only when the user asked to open that project.")
    pm = ctx.resolve.GetProjectManager()
    cur = pm.GetCurrentProject()
    prev = cur.GetName() if cur else None
    if prev == name:
        return {"loaded": name, "already": True}
    if a.get("folder"):
        pm.GotoRootFolder()
        for part in [x for x in a["folder"].split("/") if x]:
            if not pm.OpenFolder(part):
                raise OpError("NOT_FOUND", f"no Project Manager folder '{part}' in '{a['folder']}'",
                              details={"folders": jv(pm.GetFolderListInCurrentFolder())})
    p = pm.LoadProject(name)
    if p is None and not a.get("folder"):
        pm.GotoRootFolder()
        p = pm.LoadProject(name)
    if p is None:
        raise OpError("NOT_FOUND", f"LoadProject('{name}') failed",
                      hint="Pass folder if the project lives in a Project Manager folder. A save prompt for the previous project blocks it: answer it in Resolve.",
                      details={"projectsHere": (jv(pm.GetProjectListInCurrentFolder()) or [])[:40], "folders": (jv(pm.GetFolderListInCurrentFolder()) or [])[:40]})
    tl = p.GetCurrentTimeline()
    return {"loaded": p.GetName(), "previous": prev, "timelines": p.GetTimelineCount(), "currentTimeline": tl.GetName() if tl else None}


@op("system.memory", "Resolve's memory footprint (physical, peak, resident, compressed estimate) and the Mac's free level and swap, read from the OS: works while Resolve is busy or rendering. [rebuild B2/B3] At 26-28 GB on a 32 GB Mac renders slowed ~50x; the warning (FUSION_MCP_MEMORY_WARN_GB, default 60 % of RAM) carries the restart advice. Restart only with the user's approval.",
    [P("fresh", "boolean", "Ignore the 5 s cache.")], read=True, comp=False, offline=True)
def system_memory(a):
    from .. import sysmem
    return sysmem.snapshot(max_age=0 if a.get("fresh") else 5.0)


@op("system.purge_cache", "Free Fusion's render/image cache without a restart: fusion.CacheManager.Purge() then fusion._Memory_Purge(0) (undocumented; the second finds nothing after the first). Reports Resolve's footprint before and after. [live, gapfix pass] 30 heavy 1080p frames added ~1.1 GB and either purge gave it back (17.09 -> 16.0 GB); CacheManager.GetSize() under-reports (3.5 KB while ~1 GB was held) and read 0 in the rebuild, so judge by the footprint. It does not undo memory held for other reasons (the rebuild's 26-28 GB after a 2,081-tool comp): then save and ask the user about a restart. Never writes prefs.",
    [P("wait", "number", "Seconds to let the OS settle before the after-reading (default 2).", default=2)], read=True, comp=False)
def system_purge_cache(ctx, a):
    from .. import sysmem
    before = sysmem.snapshot(max_age=0)
    f = ctx.fusion()
    cm = f.CacheManager
    size0 = cm.GetSize() if cm is not None else None
    steps = []
    if cm is not None:
        cm.Purge()
        steps.append("CacheManager.Purge")
    try:
        f._Memory_Purge(0)
        steps.append("_Memory_Purge(0)")
    except Exception:  # noqa: undocumented, may vanish in a later build
        pass
    time.sleep(float(a.get("wait", 2)))
    after = sysmem.snapshot(max_age=0)
    b, c = (before.get("resolve") or {}).get("footprintGB"), (after.get("resolve") or {}).get("footprintGB")
    return {"freedGB": round(b - c, 2) if b is not None and c is not None else None, "resolveGB": {"before": b, "after": c},
            "fusionCacheBytesBefore": size0, "fusionCacheBytesAfter": cm.GetSize() if cm is not None else None, "steps": steps,
            "warning": after.get("warning")}


@op("page.get", "Return the Resolve page currently shown (media, cut, edit, fusion, color, fairlight, deliver).", read=True, comp=False)
def page_get(ctx, a):
    return {"page": ctx.resolve.GetCurrentPage()}


@op("page.open", "Switch Resolve to a page. Paste-based operations need the Fusion page.",
    [P("page", "string", "Page name.", required=True, enum=("media", "cut", "edit", "fusion", "color", "fairlight", "deliver"))],
    comp=False)
def page_open(ctx, a):
    ctx.resolve.OpenPage(a["page"])
    time.sleep(0.8)
    got = ctx.resolve.GetCurrentPage()
    if got != a["page"]:
        raise OpError("OPERATION_FAILED", f"page is '{got}' after OpenPage('{a['page']}')",
                      hint="A modal dialog in Resolve blocks page changes; check the Resolve window.")
    return {"page": got}


def _tc_to_frames(tc, fps):
    h, m, sec, f = (int(x) for x in re.split(r"[:;]", tc))
    return ((h * 60 + m) * 60 + sec) * fps + f


def _frames_to_tc(n, fps):
    f, s = n % fps, n // fps
    return "%02d:%02d:%02d:%02d" % (s // 3600, (s // 60) % 60, s % 60, f)


@op("timeline.grab_frame", "Grab the frame under the timeline playhead to an image file (Project.ExportCurrentFrameAsStill) and return it inline: a fast look at what the TIMELINE shows. Works on the Edit/Color page only, so this switches there and restores the page and playhead afterwards. Output is color-managed 8-bit timeline output without alpha: use it to see the cut, not for Fusion pixel values (use render.frame for those). No render modal.",
    [P("frame", "integer", "Frame offset from the timeline start (0 = first frame). Omit for the current playhead."),
     P("timecode", "string", "Record timecode HH:MM:SS:FF instead of frame."),
     P("outPath", "string", "Absolute path ending .png, .jpg or .tif (default out/grab_<timecode>.jpg; .png is ~25 MB at UHD)."),
     P("page", "string", "Page to grab from (default edit).", default="edit", enum=("edit", "color")),
     P("previewMaxPx", "integer", "Long edge of the preview (default 960)."),
     P("inline", "boolean", "Return the preview as an image (default true).", default=True)],
    read=True, comp=False)
def timeline_grab_frame(ctx, a):
    r = ctx.resolve
    tl = ctx.timeline()
    page0, tc0 = r.GetCurrentPage(), None
    fps = int(round(float(tl.GetSetting("timelineFrameRate") or 24)))
    try:
        if page0 != a.get("page", "edit"):
            r.OpenPage(a.get("page", "edit"))
            time.sleep(0.6)
        tc0 = tl.GetCurrentTimecode()
        tc = a.get("timecode")
        if tc is None and a.get("frame") is not None:
            tc = _frames_to_tc(_tc_to_frames(tl.GetStartTimecode(), fps) + int(a["frame"]), fps)
        if tc and not tl.SetCurrentTimecode(tc):
            raise OpError("INVALID_ARGS", "SetCurrentTimecode(%s) failed" % tc, hint="Use a record timecode inside the timeline.")
        tc = tl.GetCurrentTimecode()
        path = a.get("outPath") or os.path.join(config.out_dir(), "grab_%s.jpg" % re.sub(r"[:;]", "-", tc or "now"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not ctx.project().ExportCurrentFrameAsStill(path) or not os.path.exists(path):
            raise OpError("OPERATION_FAILED", "ExportCurrentFrameAsStill returned False or wrote nothing",
                          hint="Needs the Edit or Color page and a clip under the playhead; the extension must be .png, .jpg or .tif.")
    finally:
        try:
            if tc0:
                tl.SetCurrentTimecode(tc0)
            if page0 and r.GetCurrentPage() != page0:
                r.OpenPage(page0)
                time.sleep(0.6)
        except Exception:
            pass
    from .build import _preview
    inline = a.get("inline", True)
    pv = _preview(path, a.get("previewMaxPx") or (960 if inline else None))
    out = {"path": path, "timecode": tc, "page": a.get("page", "edit"), "restoredPage": page0, "bytes": os.path.getsize(path), "preview": pv,
           "note": "color-managed 8-bit timeline output, no alpha; not Fusion pixel values"}
    if inline and pv:
        out["_inline"] = [pv]
    return out


@op("timeline.list", "List timelines in the current project with their Fusion-capable video items.",
    [P("timeline", "string", "Only this timeline (default all)."),
     P("includeItems", "boolean", "Include video items per track (default true).", default=True)], read=True, comp=False)
def timeline_list(ctx, a):
    p = ctx.project()
    out = []
    for i in range(1, p.GetTimelineCount() + 1):
        t = p.GetTimelineByIndex(i)
        if a.get("timeline") and t.GetName() != a["timeline"]:
            continue
        row = {"name": t.GetName(), "start": t.GetStartFrame(), "end": t.GetEndFrame(), "startTimecode": t.GetStartTimecode(),
               "fps": t.GetSetting("timelineFrameRate")}
        if a.get("includeItems", True):
            row["tracks"] = []
            for k in range(1, t.GetTrackCount("video") + 1):
                row["tracks"].append([{"index": j, "name": it.GetName(), "start": it.GetStart(), "end": it.GetEnd(),
                                       "fusionComps": it.GetFusionCompCount()}
                                      for j, it in enumerate(t.GetItemListInTrack("video", k) or [])])
        out.append(row)
    return {"timelines": out, "current": (p.GetCurrentTimeline() or None) and p.GetCurrentTimeline().GetName()}


def _fps_str(fps):
    return str(int(round(fps))) if abs(fps - round(fps)) < 1e-6 else ("%g" % fps)


def set_timeline_format(tl, width=None, height=None, fps=None):
    """[rebuild F2] Custom timeline format (a new timeline inherits the project's): useCustomSettings first, then
    width/height/frame rate, each read back. The frame rate only changes while the timeline has no clips."""
    want = [("useCustomSettings", "1")]
    if width:
        want.append(("timelineResolutionWidth", str(int(width))))
    if height:
        want.append(("timelineResolutionHeight", str(int(height))))
    if fps:
        want.append(("timelineFrameRate", _fps_str(float(fps))))
    returned = {k: bool(tl.SetSetting(k, v)) for k, v in want}
    got = {"width": int(float(tl.GetSetting("timelineResolutionWidth") or 0)), "height": int(float(tl.GetSetting("timelineResolutionHeight") or 0)),
           "fps": float(tl.GetSetting("timelineFrameRate") or 0)}
    bad = {}
    if width and got["width"] != int(width):
        bad["width"] = got["width"]
    if height and got["height"] != int(height):
        bad["height"] = got["height"]
    if fps and abs(got["fps"] - float(fps)) > 0.01:
        bad["fps"] = got["fps"]
    if bad:
        raise OpError("OPERATION_FAILED", f"timeline format did not stick: {bad}",
                      hint="The frame rate is locked once a timeline holds clips; set it on an empty timeline (timeline.create width/height/fps).",
                      details={"requested": dict(want), "setReturned": returned, "readback": got})
    return got


def _ffmpeg():
    import shutil
    for c in ("ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        p = shutil.which(c) or (c if os.path.isfile(c) else None)
        if p:
            return p
    raise OpError("NOT_FOUND", "ffmpeg is needed to make the black carrier clip", hint="brew install ffmpeg")


def _fps_rate(fps):
    for base in (24, 30, 48, 60, 120):
        if abs(fps - base * 1000 / 1001) < 0.005:
            return "%d/1001" % (base * 1000)
    return _fps_str(fps)


def carrier_clip(ctx, tl, frames):
    """A black ProRes Proxy clip at the timeline's size and rate, exactly `frames` long (reused per length),
    imported once into the Media Pool folder _fc_carriers. [rebuild F3] No API sets a Fusion Composition clip's
    length, so an exact-length Fusion item = this carrier trimmed by AppendToTimeline + AddFusionComp."""
    import glob
    import subprocess
    from .build import _walk_pool
    W = int(float(tl.GetSetting("timelineResolutionWidth")))
    H = int(float(tl.GetSetting("timelineResolutionHeight")))
    fps = float(tl.GetSetting("timelineFrameRate"))
    d = os.path.join(config.out_dir(), "carriers")
    os.makedirs(d, exist_ok=True)
    tag = ("%dx%d_%s" % (W, H, ("%g" % fps).replace(".", "p")))
    have = []
    for f in glob.glob(os.path.join(d, "fc_carrier_%s_*f.mov" % tag)):
        m = re.search(r"_(\d+)f\.mov$", f)
        if m and int(m.group(1)) == int(frames):
            have.append((int(m.group(1)), f))
    if have:
        length, path = min(have)
    else:
        # [live, gapfix pass] exact length: an item comp's global range is the carrier's whole source range (a 900-frame
        # carrier gave 0..899 on a 42-frame item), and render.range / contact sheets / audits default to that range
        length = int(frames)
        path = os.path.join(d, "fc_carrier_%s_%df.mov" % (tag, length))
        tmp = path + ".part.mov"
        r = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=%dx%d:r=%s" % (W, H, _fps_rate(fps)),
                            "-frames:v", str(length), "-c:v", "prores_ks", "-profile:v", "0", "-pix_fmt", "yuv422p10le", tmp],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0 or not os.path.exists(tmp):
            raise OpError("OPERATION_FAILED", "ffmpeg could not make the carrier clip", details={"stderr": (r.stderr or "")[-800:]})
        os.replace(tmp, path)
    mp = ctx.project().GetMediaPool()
    mpi = next((c for _, c in _walk_pool(mp.GetRootFolder()) if c.GetClipProperty("File Path") == path), None)
    if mpi is None:
        root = mp.GetRootFolder()
        cur = mp.GetCurrentFolder()
        sub = next((f for f in (root.GetSubFolderList() or []) if f.GetName() == "_fc_carriers"), None) or mp.AddSubFolder(root, "_fc_carriers")
        mp.SetCurrentFolder(sub)
        try:
            got = mp.ImportMedia([path]) or []
        finally:
            if cur is not None:
                mp.SetCurrentFolder(cur)
        if not got:
            raise OpError("OPERATION_FAILED", f"ImportMedia({path}) returned nothing")
        mpi = got[0]
    return mpi, path, length


def track_spans(tl, track):
    """[(clip name, start, end_exclusive)] on a video track, in frames from the timeline start."""
    t0 = tl.GetStartFrame()
    return [(x.GetName(), int(x.GetStart() - t0), int(x.GetEnd() - t0)) for x in (tl.GetItemListInTrack("video", track) or [])
            if x.GetStart() is not None and x.GetEnd() is not None] or [("", 0, 0)]


def track_overlaps(tl, track, record, frames):
    return [(n, a, b) for n, a, b in track_spans(tl, track) if n and a < record + frames and record < b]


def append_item(ctx, tl, mpi, source_in, frames, track, record=None, video_only=True):
    """MediaPool.AppendToTimeline with an explicit source range, track and record frame, then read back.
    endFrame is exclusive (realities §14: 0..23 appends 23 frames). record = frames from the timeline start."""
    p = ctx.project()
    cur = p.GetCurrentTimeline()
    if cur is None or cur.GetName() != tl.GetName():
        p.SetCurrentTimeline(tl)
    while (tl.GetTrackCount("video") or 0) < track:
        if not tl.AddTrack("video"):
            raise OpError("OPERATION_FAILED", f"AddTrack('video') failed while making track {track}")
    if record is not None:
        busy = track_overlaps(tl, track, int(record), int(frames))
        if busy:
            free = next(k for k in range(1, (tl.GetTrackCount("video") or 0) + 2) if not track_overlaps(tl, k, int(record), int(frames)))
            end = max(b for _, _, b in track_spans(tl, track))
            raise OpError("INVALID_ARGS", "record range %d..%d on V%d overlaps %s" % (
                int(record), int(record) + int(frames) - 1, track, ", ".join("'%s' (%d..%d)" % (n, a, b - 1) for n, a, b in busy[:3])),
                hint="Use a free record frame (V%d is free from %d) or track %d." % (track, end, free),
                details={"overlaps": [{"clip": n, "start": a, "end": b - 1} for n, a, b in busy], "nextFreeFrame": end, "freeTrack": free})
    info = {"mediaPoolItem": mpi, "startFrame": int(source_in), "endFrame": int(source_in) + int(frames), "trackIndex": int(track)}
    if video_only:
        info["mediaType"] = 1
    if record is not None:
        info["recordFrame"] = tl.GetStartFrame() + int(record)
    items = p.GetMediaPool().AppendToTimeline([info]) or []
    if not items:
        raise OpError("OPERATION_FAILED", "AppendToTimeline returned no item",
                      hint="The source range must lie inside the clip, and the record range on that track should be empty.",
                      details={"sourceIn": source_in, "frames": frames, "track": track, "recordFrame": record})
    it = items[0]
    uid = it.GetUniqueId()
    idx = next((j for j, x in enumerate(tl.GetItemListInTrack("video", track) or []) if x.GetUniqueId() == uid), None)
    if idx is None or it.GetStart() is None:
        raise OpError("OPERATION_FAILED", f"AppendToTimeline returned an item that is not on V{track}",
                      hint="Read the timeline (timeline.list) before retrying: the record range may have been taken.",
                      details={"recordFrame": record, "frames": frames, "track": track})
    got = {"track": track, "item": idx, "recordFrame": int(it.GetStart() - tl.GetStartFrame()), "frames": int(it.GetDuration())}
    warn = []
    if got["frames"] != int(frames):
        warn.append(f"length is {got['frames']} frames, asked {frames}")
    if record is not None and got["recordFrame"] != int(record):
        warn.append(f"landed at record frame {got['recordFrame']}, asked {record}")
    return it, got, warn


@op("timeline.create", "Create an empty timeline, optionally at its own format (width/height/fps as custom timeline settings, read back; a new timeline otherwise inherits the project's), and optionally a Fusion clip on V1: fusionFrames makes it exactly that long (black carrier + AddFusionComp, as timeline.add_fusion_clip), fusionComp: true the fixed-length Fusion Composition clip (12 s). No clip unless asked. Name must be unique.",
    [P("name", "string", "Timeline name (use a 'Connector_' prefix for scratch work).", required=True),
     P("width", "integer", "Timeline width px (custom setting)."), P("height", "integer", "Timeline height px."),
     P("fps", "number", "Timeline frame rate (only settable while the timeline is empty, so it is set before any clip)."),
     P("fusionComp", "boolean", "Add the 12 s Fusion Composition clip on V1 (default false; fusionFrames adds an exact-length one).", default=False),
     P("fusionFrames", "integer", "Exact length of that Fusion clip in frames (default: the 12 s Fusion Composition clip)."),
     P("makeCurrent", "boolean", "Make it the current timeline (default true).", default=True)], comp=False)
def timeline_create(ctx, a):
    p = ctx.project()
    if ctx.timeline(a["name"], required=False):
        raise OpError("INVALID_ARGS", f"timeline '{a['name']}' already exists")
    tl = p.GetMediaPool().CreateEmptyTimeline(a["name"])
    if tl is None:
        raise OpError("OPERATION_FAILED", "CreateEmptyTimeline returned None",
                      hint="A modal dialog in Resolve blocks the API; check the Resolve window.")
    fmt = None
    if a.get("width") or a.get("height") or a.get("fps"):
        fmt = set_timeline_format(tl, a.get("width"), a.get("height"), a.get("fps"))
    want_clip = bool(a.get("fusionComp") or a.get("fusionFrames"))  # [scene builder pass] never a clip nobody asked for
    if a.get("makeCurrent", True) or want_clip:
        p.SetCurrentTimeline(tl)
    out = {"timeline": tl.GetName(), "format": fmt or {"width": int(float(tl.GetSetting("timelineResolutionWidth") or 0)),
                                                       "height": int(float(tl.GetSetting("timelineResolutionHeight") or 0)),
                                                       "fps": float(tl.GetSetting("timelineFrameRate") or 0), "inherited": True}}
    if want_clip:
        if a.get("fusionFrames"):
            out.update(timeline_add_fusion_clip(ctx, {"timeline": tl.GetName(), "track": 1, "recordFrame": 0, "frames": a["fusionFrames"]}))
            return out
        tl.InsertFusionCompositionIntoTimeline()
        items = tl.GetItemListInTrack("video", 1) or []
        if not items:
            raise OpError("OPERATION_FAILED", "InsertFusionCompositionIntoTimeline created no item")
        out.update(item=items[0].GetName(), comps=items[0].GetFusionCompCount(), frames=int(items[0].GetDuration()),
                   compRef={"timeline": tl.GetName(), "item": 0})
    return out


@op("timeline.set_format", "Set a timeline's own resolution and/or frame rate (useCustomSettings + timelineResolutionWidth/Height + timelineFrameRate, read back). Resolve locks the frame rate once the timeline holds clips.",
    [P("timeline", "string", "Timeline (default current)."), P("width", "integer", "Width px."), P("height", "integer", "Height px."),
     P("fps", "number", "Frame rate.")], comp=False)
def timeline_set_format(ctx, a):
    if not (a.get("width") or a.get("height") or a.get("fps")):
        raise OpError("INVALID_ARGS", "pass width, height and/or fps")
    tl = ctx.timeline(a.get("timeline"))
    return {"timeline": tl.GetName(), "format": set_timeline_format(tl, a.get("width"), a.get("height"), a.get("fps"))}


@op("timeline.append_clip", "Put a Media Pool clip on a timeline: source range (sourceIn + frames), video track (created if missing) and record frame (frames from the timeline start; default: after the track's last clip). MediaPool.AppendToTimeline, read back (index on the track, record frame, length).",
    [P("timeline", "string", "Timeline (default current)."), P("clip", "string", "Media Pool clip name or media ID (item.list).", required=True),
     P("sourceIn", "integer", "First source frame (default 0).", default=0), P("frames", "integer", "Length in frames (default: the rest of the clip)."),
     P("track", "integer", "Video track (default 1).", default=1), P("recordFrame", "integer", "Record position, frames from the timeline start."),
     P("audio", "boolean", "Also append the clip's audio (default false: video only).")], comp=False)
def timeline_append_clip(ctx, a):
    from .build import _find_clip
    tl = ctx.timeline(a.get("timeline"))
    mpi = _find_clip(ctx, a["clip"])
    frames = a.get("frames")
    if not frames:
        try:
            frames = int(float(mpi.GetClipProperty("Frames"))) - int(a.get("sourceIn", 0))
        except (TypeError, ValueError):
            raise OpError("INVALID_ARGS", "pass frames (the clip's frame count could not be read)")
    it, got, warn = append_item(ctx, tl, mpi, a.get("sourceIn", 0), frames, int(a.get("track", 1)), a.get("recordFrame"),
                                video_only=not a.get("audio"))
    out = {"timeline": tl.GetName(), "clip": it.GetName(), **got,
           "compRef": {"timeline": tl.GetName(), "track": got["track"], "item": got["item"]}}
    if warn:
        out["warnings"] = warn
    return out


@op("timeline.add_fusion_clip", "Make a Fusion item of EXACT length on any video track at a record frame: a black carrier clip at the timeline's size and rate (ffmpeg, made once, reused) is appended and trimmed, then AddFusionComp gives it a comp (MediaIn1 reads the black carrier; delete or ignore it). [rebuild F3/F10] The Fusion Composition clip has a fixed length and comp.create only reached V1. Returns compRef for comp.set_current / paste ops.",
    [P("timeline", "string", "Timeline (default current)."), P("frames", "integer", "Length in frames.", required=True),
     P("track", "integer", "Video track (created if missing; default 1).", default=1),
     P("recordFrame", "integer", "Record position, frames from the timeline start (default: after the track's last clip)."),
     P("compName", "string", "Rename the new comp."), P("clipName", "string", "Rename the timeline clip.")], comp=False)
def timeline_add_fusion_clip(ctx, a):
    tl = ctx.timeline(a.get("timeline"))
    frames = int(a["frames"])
    if frames < 1:
        raise OpError("INVALID_ARGS", "frames must be >= 1")
    mpi, path, length = carrier_clip(ctx, tl, frames)
    track = int(a.get("track", 1))
    it, got, warn = append_item(ctx, tl, mpi, 0, frames, track, a.get("recordFrame"))
    c = it.AddFusionComp()
    if c is None:
        raise OpError("OPERATION_FAILED", "AddFusionComp returned None on the carrier item", details=got)
    names = jv(it.GetFusionCompNameList()) or []
    if a.get("compName") and names:
        it.RenameFusionCompByName(names[-1], a["compName"])
        names = jv(it.GetFusionCompNameList()) or []
    if a.get("clipName"):
        try:
            it.SetName(a["clipName"])
        except Exception:  # noqa
            warn.append("clip rename not supported by this Resolve build")
    ca = c.GetAttrs() or {}
    out = {"timeline": tl.GetName(), "clip": it.GetName(), **got, "comps": names,
           "compRange": [num(ca.get("COMPN_GlobalStart")), num(ca.get("COMPN_GlobalEnd"))],
           "compRef": {"timeline": tl.GetName(), "track": track, "item": got["item"], "comp": len(names) or 1},
           "carrier": {"path": path, "frames": length}}
    if warn:
        out["warnings"] = warn
    return out


@op("timeline.delete", "Delete a timeline from the project (MediaPool.DeleteTimelines). Destructive: runs only with confirm: true.",
    [P("name", "string", "Timeline name.", required=True), P("confirm", "boolean", "Must be true.", required=True)],
    comp=False, consent=True)
def timeline_delete(ctx, a):
    tl = ctx.timeline(a["name"])
    p = ctx.project()
    cur = p.GetCurrentTimeline()
    if cur and cur.GetName() == a["name"]:
        for i in range(1, p.GetTimelineCount() + 1):
            o = p.GetTimelineByIndex(i)
            if o.GetName() != a["name"]:
                p.SetCurrentTimeline(o)
                break
    ok = p.GetMediaPool().DeleteTimelines([tl])
    if not ok or ctx.timeline(a["name"], required=False):
        raise OpError("OPERATION_FAILED", "DeleteTimelines failed")
    return {"deleted": a["name"]}


@op("timeline.set_current", "Make a timeline current (Project.SetCurrentTimeline).",
    [P("name", "string", "Timeline name.", required=True)], comp=False)
def timeline_set_current(ctx, a):
    tl = ctx.timeline(a["name"])
    ctx.project().SetCurrentTimeline(tl)
    return {"current": ctx.project().GetCurrentTimeline().GetName()}


# ================================================================ comp

def comp_summary(ctx, comp, tools=True, limit=None):
    a = comp.GetAttrs() or {}
    W, H, fps = ctx.fmt(comp)
    out = {"name": a.get("COMPS_Name"), "width": W, "height": H, "fps": fps,
           "pixelAspect": [num(comp.GetPrefs("Comp.FrameFormat.AspectX") or 1), num(comp.GetPrefs("Comp.FrameFormat.AspectY") or 1)],
           "globalRange": [num(a.get("COMPN_GlobalStart")), num(a.get("COMPN_GlobalEnd"))],
           "renderRange": [num(a.get("COMPN_RenderStart")), num(a.get("COMPN_RenderEnd"))],
           "currentTime": num(comp.CurrentTime), "modified": a.get("COMPB_Modified"), "locked": a.get("COMPB_Locked"),
           "isCurrent": ctx.is_current(comp)}
    if tools:
        tl = []
        allt = []
        for t in (comp.GetToolList(False) or {}).values():
            ta = t.GetAttrs()
            allt.append((ta["TOOLS_Name"], ta["TOOLS_RegID"], ta, t))
        allt.sort(key=lambda x: x[0])
        by = {}
        for _, reg, _, _ in allt:
            by[reg] = by.get(reg, 0) + 1
        # [live, gapfix pass] the per-input walk costs ~80 bridge calls per tool: on a 1,100-tool scene comp an
        # uncapped summary took over 60 s (fu_context timed out). Only the first `limit` tools get the walk.
        for name, reg, ta, t in (allt[:limit] if limit else allt):
            row = {"name": name, "regId": reg, "passThrough": bool(ta.get("TOOLB_PassThrough"))}
            main = {}
            anim = 0
            exprs = 0
            for i in (t.GetInputList() or {}).values():
                ia = i.GetAttrs()
                o = i.GetConnectedOutput()
                if o:
                    ot = o.GetTool()
                    src = ot.GetAttrs() if ot else {"TOOLS_Name": "<group output>"}
                    if ia.get("INPS_DataType") in ("Image", "Mask", "DataType3D", "MtlGraph3D", "Particles"):
                        main[ia.get("INPS_ID") or ia.get("INPS_Name", "?")] = src["TOOLS_Name"]
                    else:
                        anim += 1
                try:
                    if i.GetExpression():
                        exprs += 1
                except Exception:
                    pass
            row["inputs"] = main
            if anim:
                row["modifiedInputs"] = anim
            if exprs:
                row["expressions"] = exprs
            if ctx.tsv().kind(reg) == "modifier" or reg == "BezierSpline":
                row["modifier"] = True
            tl.append(row)
        out["tools"] = tl
        if limit and len(allt) > limit:  # a 2,000-tool comp summary is ~100k chars and minutes of bridge calls
            out["toolsTruncated"] = {"total": len(allt), "shown": limit, "byRegId": dict(sorted(by.items(), key=lambda kv: -kv[1])[:30]),
                                     "hint": "tool.list with a name glob or regId, or fu_tool_info on a glob, for the rest"}
        mo = comp.FindTool("MediaOut1")
        out["output"] = ctx.source_of(mo, "Input") if mo else None
    return out


@op("comp.info", "Comp details: frame format, global/render range, current time, and a summary of every tool (reg ID, image wiring, animated/expression input counts), capped at toolLimit rows with counts by regId. Same payload as fu_comp_info.",
    [COMP(), P("includeTools", "boolean", "Include tool summaries (default true).", default=True),
     P("toolLimit", "integer", "Max tool rows with wiring detail (default 150; each costs ~80 bridge calls).", default=150)], read=True)
def comp_info(ctx, comp, a):
    return comp_summary(ctx, comp, a.get("includeTools", True), int(a.get("toolLimit", 150)))


@op("comp.list", "List Fusion comps on a timeline's video items: {track, item index, clip name, comp names}.",
    [P("timeline", "string", "Timeline name (default current).")], read=True, comp=False)
def comp_list(ctx, a):
    tl = ctx.timeline(a.get("timeline"))
    out = []
    for k in range(1, tl.GetTrackCount("video") + 1):
        for j, it in enumerate(tl.GetItemListInTrack("video", k) or []):
            n = it.GetFusionCompCount()
            if n:
                names = it.GetFusionCompNameList() or []
                out.append({"track": k, "item": j, "clip": it.GetName(), "comps": list(names.values()) if isinstance(names, dict) else list(names),
                            "compRef": {"timeline": tl.GetName(), "track": k, "item": j}})
    return {"timeline": tl.GetName(), "comps": out}


@op("comp.set_current", "Make a timeline item's comp (any video track) the current Fusion-page comp: SetCurrentTimeline, Edit page + settle, playhead to the item's middle frame (read back; [rebuild F11] SetCurrentTimecode does not move the playhead until the Edit page has settled), Fusion page, identity check by token. A clip on a higher track under the playhead is reported (the Fusion page shows the topmost clip). Required before paste-based ops if you address comps by reference; paste ops do it automatically.",
    [P("comp", "object", "{timeline?, track?, item?, comp?} (see COMP).", required=True),
     P("settle", "number", "Seconds to wait after opening the Fusion page (default 1.5).", default=1.5)], comp=False)
def comp_set_current(ctx, a):
    c = ctx.make_current(a["comp"], a.get("settle", 1.5))
    return {"current": True, "comp": comp_summary(ctx, c, tools=False)}


@op("comp.create", "Add a Fusion comp: on a new Fusion Composition clip in a timeline (default), or as an extra comp on an existing item on any video track (item.AddFusionComp). For a Fusion item of exact length on V2+, use timeline.add_fusion_clip.",
    [P("timeline", "string", "Timeline (default current)."),
     P("onItem", "integer", "0-based item index on `track` to add a comp to; omit to insert a new Fusion Composition clip at the playhead."),
     P("track", "integer", "Video track of onItem (default 1).", default=1),
     P("name", "string", "Name for the new comp (item comps only).")], comp=False)
def comp_create(ctx, a):
    tl = ctx.timeline(a.get("timeline"))
    ctx.project().SetCurrentTimeline(tl)
    if a.get("onItem") is None:
        before = len(tl.GetItemListInTrack("video", 1) or [])
        it = tl.InsertFusionCompositionIntoTimeline()
        items = tl.GetItemListInTrack("video", 1) or []
        if it is None and len(items) <= before:
            raise OpError("OPERATION_FAILED", "InsertFusionCompositionIntoTimeline failed")
        idx = next((j for j, x in enumerate(items) if it is not None and x.GetUniqueId() == it.GetUniqueId()), len(items) - 1)
        return {"compRef": {"timeline": tl.GetName(), "item": idx, "comp": 1}, "clip": items[idx].GetName()}
    track = int(a.get("track", 1))
    _, it = ctx.item({"timeline": tl.GetName(), "item": a["onItem"], "track": track})
    c = it.AddFusionComp()
    if c is None:
        raise OpError("OPERATION_FAILED", "AddFusionComp returned None")
    n = it.GetFusionCompCount()
    if a.get("name"):
        names = it.GetFusionCompNameList() or {}
        last = list(names.values())[-1] if isinstance(names, dict) else names[-1]
        it.RenameFusionCompByName(last, a["name"])
    return {"compRef": {"timeline": tl.GetName(), "track": track, "item": a["onItem"], "comp": a.get("name") or n}, "count": n,
            "clip": it.GetName()}


@op("comp.delete", "Delete a named comp from a timeline item (DeleteFusionCompByName). The item keeps at least one comp.",
    [P("timeline", "string", "Timeline (default current)."), P("item", "integer", "0-based item index on track.", required=True),
     P("track", "integer", "Video track (default 1).", default=1), P("name", "string", "Comp name.", required=True)], comp=False)
def comp_delete(ctx, a):
    _, it = ctx.item({"timeline": a.get("timeline"), "item": a["item"], "track": a.get("track", 1)})
    names = list(jv(it.GetFusionCompNameList()) or [])
    if a["name"] not in names:
        raise OpError("NOT_FOUND", f"no comp '{a['name']}' on the item", details={"comps": names})
    ok = it.DeleteFusionCompByName(a["name"])
    if not ok:  # the item's active comp cannot be deleted: load another one first
        other = next((n for n in names if n != a["name"]), None)
        if other:
            it.LoadFusionCompByName(other)
            ok = it.DeleteFusionCompByName(a["name"])
    if not ok:
        raise OpError("OPERATION_FAILED", f"DeleteFusionCompByName('{a['name']}') failed",
                      details={"comps": it.GetFusionCompNameList()})
    return {"deleted": a["name"], "remaining": jv(it.GetFusionCompNameList())}


@op("comp.rename", "Rename a comp on a timeline item (RenameFusionCompByName).",
    [P("timeline", "string", "Timeline (default current)."), P("item", "integer", "0-based item index on track.", required=True),
     P("track", "integer", "Video track (default 1).", default=1),
     P("name", "string", "Current comp name.", required=True), P("newName", "string", "New name.", required=True)], comp=False)
def comp_rename(ctx, a):
    _, it = ctx.item({"timeline": a.get("timeline"), "item": a["item"], "track": a.get("track", 1)})
    if not it.RenameFusionCompByName(a["name"], a["newName"]):
        raise OpError("OPERATION_FAILED", "RenameFusionCompByName failed", details={"comps": jv(it.GetFusionCompNameList())})
    return {"comps": jv(it.GetFusionCompNameList())}


@op("comp.set_time", "Set the comp's current time (frame). Also the frame AddModifier seeds its first key at.",
    [COMP(), P("frame", "number", "Frame.", required=True)], undo=False)
def comp_set_time(ctx, comp, a):
    comp.CurrentTime = a["frame"]
    return {"currentTime": num(comp.CurrentTime)}


@op("comp.set_render_range", "Set the comp's render range (COMPN_RenderStart/End). The global range follows the clip length in Resolve (lengthen the clip on the Edit page).",
    [COMP(), P("start", "number", "First frame.", required=True), P("end", "number", "Last frame.", required=True)])
def comp_set_render_range(ctx, comp, a):
    comp.SetAttrs({"COMPN_RenderStart": a["start"], "COMPN_RenderEnd": a["end"]})
    at = comp.GetAttrs()
    return {"renderRange": [num(at["COMPN_RenderStart"]), num(at["COMPN_RenderEnd"])],
            "globalRange": [num(at["COMPN_GlobalStart"]), num(at["COMPN_GlobalEnd"])]}


@op("comp.format", "Read the comp frame format (width, height, fps, pixel aspect, depth) from comp prefs.", [COMP()], read=True)
def comp_format(ctx, comp, a):
    ff = jv(comp.GetPrefs("Comp.FrameFormat")) or {}
    W, H, fps = ctx.fmt(comp)
    return {"width": W, "height": H, "fps": fps, "frameFormat": ff}


@op("comp.set_format", "Set comp frame-format prefs (Comp.FrameFormat.Width/Height/Rate). In Resolve the timeline resolution usually wins; the readback says what stuck.",
    [COMP(), P("width", "integer", "Pixels."), P("height", "integer", "Pixels."), P("fps", "number", "Frame rate.")])
def comp_set_format(ctx, comp, a):
    prefs = {}
    if a.get("width"):
        prefs["Comp.FrameFormat.Width"] = int(a["width"])
    if a.get("height"):
        prefs["Comp.FrameFormat.Height"] = int(a["height"])
    if a.get("fps"):
        prefs["Comp.FrameFormat.Rate"] = float(a["fps"])
    if not prefs:
        raise OpError("INVALID_ARGS", "pass width, height and/or fps")
    comp.SetPrefs(prefs)
    W, H, fps = ctx.fmt(comp)
    return {"requested": prefs, "width": W, "height": H, "fps": fps}


@op("comp.undo", "Undo the last N undo events in the comp (each fu_do call is one event). Runs outside any undo group; cannot ride in batch.run.",
    [COMP(), P("count", "integer", "Events to undo (default 1).", default=1)], undo=False, batchable=False)
def comp_undo(ctx, comp, a):
    comp.Undo(int(a.get("count", 1)))
    n = ctx.names(comp)
    return {"undone": int(a.get("count", 1)), "toolCount": len(n), "tools": n if len(n) <= 60 else n[:20] + ["... %d more" % (len(n) - 20)]}


@op("comp.redo", "Redo N undo events. Runs outside any undo group; cannot ride in batch.run.",
    [COMP(), P("count", "integer", "Events to redo (default 1).", default=1)], undo=False, batchable=False)
def comp_redo(ctx, comp, a):
    comp.Redo(int(a.get("count", 1)))
    n = ctx.names(comp)
    return {"redone": int(a.get("count", 1)), "toolCount": len(n), "tools": n if len(n) <= 60 else n[:20] + ["... %d more" % (len(n) - 20)]}


@op("comp.export_file", "Save a timeline item's comp to a .comp file (TimelineItem.ExportFusionComp). Not undoable (writes a file).",
    [P("timeline", "string", "Timeline (default current)."), P("item", "integer", "0-based V1 item index (default 0).", default=0),
     P("track", "integer", "Video track (default 1).", default=1), P("index", "integer", "1-based comp index (default 1).", default=1),
     P("path", "string", "Absolute .comp path (default out/<clip>.comp).")], read=True, comp=False)
def comp_export_file(ctx, a):
    _, it = ctx.item({"timeline": a.get("timeline"), "item": a.get("item", 0), "track": a.get("track", 1)})
    path = a.get("path") or os.path.join(config.out_dir(), re.sub(r"\W+", "_", it.GetName()) + ".comp")
    if not os.path.isabs(path):
        raise OpError("INVALID_ARGS", "path must be absolute")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ok = it.ExportFusionComp(path, int(a.get("index", 1)))
    if not ok or not os.path.exists(path):
        raise OpError("OPERATION_FAILED", f"ExportFusionComp failed for {path}")
    return {"path": path, "bytes": os.path.getsize(path)}


@op("comp.import_file", "Import a .comp file onto a timeline item as a NEW comp. [live 21.1] TimelineItem.ImportFusionComp does not add a comp: it replaces the item's ACTIVE comp, so this op adds a blank comp first (AddFusionComp) and imports into it. replaceActive: true imports over the active comp instead (destructive, needs confirm).",
    [P("timeline", "string", "Timeline (default current)."), P("item", "integer", "0-based V1 item index (default 0).", default=0),
     P("track", "integer", "Video track (default 1).", default=1), P("path", "string", "Absolute .comp path.", required=True),
     P("name", "string", "Name for the new comp."), P("replaceActive", "boolean", "Overwrite the active comp instead of adding one."),
     P("confirm", "boolean", "Required with replaceActive.")], comp=False)
def comp_import_file(ctx, a):
    if not os.path.isfile(a["path"]):
        raise OpError("NOT_FOUND", f"no file {a['path']}")
    _, it = ctx.item({"timeline": a.get("timeline"), "item": a.get("item", 0), "track": a.get("track", 1)})
    if a.get("replaceActive"):
        if a.get("confirm") is not True:
            raise OpError("FORBIDDEN", "replaceActive overwrites the item's active comp; pass confirm: true only on the user's request")
    else:
        if it.AddFusionComp() is None:
            raise OpError("OPERATION_FAILED", "AddFusionComp returned None")
    before = it.GetFusionCompCount()
    c = it.ImportFusionComp(a["path"])
    if c is None:
        raise OpError("OPERATION_FAILED", "ImportFusionComp returned None")
    names = list(jv(it.GetFusionCompNameList()) or [])
    if a.get("name") and not a.get("replaceActive"):
        it.RenameFusionCompByName(names[-1], a["name"])
        names = list(jv(it.GetFusionCompNameList()) or [])
    return {"comps": names, "count": it.GetFusionCompCount(), "imported": names[-1] if not a.get("replaceActive") else "active comp",
            "tools": len(c.GetToolList(False) or {}), "note": None if before == it.GetFusionCompCount() else "comp count changed during import"}


# ================================================================ tool (layer analog)

def tool_detail(ctx, comp, t, include_inputs=True, frame=None):
    ta = t.GetAttrs()
    reg = ta["TOOLS_RegID"]
    f = comp.CurrentTime if frame is None else frame
    out = {"name": ta["TOOLS_Name"], "regId": reg, "passThrough": bool(ta.get("TOOLB_PassThrough")),
           "locked": bool(ta.get("TOOLB_Locked")), "kind": ctx.tsv().kind(reg) or "tool"}
    try:
        fv = t.Composition.CurrentFrame.FlowView if False else None  # FlowView read is optional; see tool.set_position
    except Exception:
        fv = None
    outs = []
    for o in (t.GetOutputList() or {}).values():
        oa = o.GetAttrs()
        cons = []
        for i in (o.GetConnectedInputs() or {}).values():
            ct = i.GetTool()  # None for inputs owned by a group/macro instance
            cons.append([ct.GetAttrs()["TOOLS_Name"] if ct else "<group input>", iid_of(i)])
        outs.append({"id": oa.get("OUTS_ID") or oa.get("OUTS_Name", "?"), "type": oa.get("OUTS_DataType"), "consumers": cons})
    out["outputs"] = outs
    if not include_inputs:
        return out
    ins = []
    for i in (t.GetInputList() or {}).values():
        ia = i.GetAttrs()
        iid = ia.get("INPS_ID") or ia.get("INPS_Name", "?")
        dt = ia.get("INPS_DataType")
        row = {"id": iid, "name": ia.get("INPS_Name"), "type": dt}
        o = i.GetConnectedOutput()
        st = o.GetTool() if o else None
        if o and st is None:
            row["source"] = ["<group output>", oid_of(o)]
        elif o:
            sa = st.GetAttrs()
            row["source"] = [sa["TOOLS_Name"], oid_of(o)]
            if sa["TOOLS_RegID"] == "BezierSpline":
                row["keyframes"] = spline_keys(st)
            elif dt not in ("Image", "Mask", "DataType3D", "MtlGraph3D", "Particles"):
                row["modifier"] = sa["TOOLS_RegID"]
        try:
            e = i.GetExpression()
            if e:
                row["expression"] = e
        except Exception:
            pass
        if dt not in ("Image", "Mask", "DataType3D", "MtlGraph3D", "Particles", "Material", "Gradient", "LookUpTable", "ScriptVal"):
            try:
                row["value"] = jv(t.GetInput(iid, f))
            except Exception:
                pass
        ins.append(row)
    out["inputs"] = ins
    return out


@op("tool.info", "Full tool info: every input (ID, label, type, value at frame, source/modifier, keyframes, expression) and outputs with consumers. Same payload as fu_tool_info. tool may be 'all' or a glob.",
    [COMP(), P("tool", "string|array", "Tool name, list of names, 'all', or glob like 'Title_*'.", required=True),
     P("includeInputs", "boolean", "Include the input table (default true).", default=True), FRAME], read=True)
def tool_info(ctx, comp, a):
    tools = ctx.tools_matching(comp, a["tool"])
    res = [tool_detail(ctx, comp, t, a.get("includeInputs", True), a.get("frame")) for _, t in tools]
    return res[0] if isinstance(a["tool"], str) and len(res) == 1 and not any(c in a["tool"] for c in "*?[") and a["tool"] != "all" else {"tools": res}


@op("tool.add", "Add a tool WITHOUT auto-wiring (SetActiveTool(None) + Lock + explicit no-connect flags; stray auto-merges are removed). regId and inputs are validated against the live TSV; inputs are set with readback; optional wiring.",
    [COMP(), P("regId", "string", "Registry ID (TextPlus, Merge, Background, Transform, RectangleMask, sRectangle, Camera3D, ...).", required=True),
     P("name", "string", "Unique name: letters/digits/underscore, no leading digit. Default: Fusion's."),
     P("inputs", "object", "{inputId: value} set after creation (validated, read back). Points [x,y] normalized Y-up or {px:[x,y]}."),
     P("connect", "object", "{inputId: 'SourceTool' | ['SourceTool','OutputId']} wiring into the new tool."),
     P("connectTo", "object", "{tool: 'Consumer', input: 'Background'} wires the new tool's main output into a consumer."),
     P("position", "array", "[x, y] node position in the flow (optional).")])
def tool_add(ctx, comp, a):
    pos = a.get("position") or [None, None]
    t = ctx.add_tool(comp, a["regId"], a.get("name"), pos[0], pos[1])
    name = t.GetAttrs()["TOOLS_Name"]
    set_ = {}
    try:
        for k, v in (a.get("inputs") or {}).items():
            set_[k] = ctx.set_input(comp, t, k, v)
        wired = {}
        for k, src in (a.get("connect") or {}).items():
            s, o = (src, None) if isinstance(src, str) else (src[0], src[1])
            wired[k] = ctx.connect(t, k, ctx.tool(comp, s), o)
        if a.get("connectTo"):
            ct = a["connectTo"]
            wired["->" + ct["tool"]] = ctx.connect(ctx.tool(comp, ct["tool"]), ct["input"], t)
    except OpError:
        t.Delete()
        raise
    return {"tool": name, "regId": a["regId"], "inputs": set_, "wired": wired}


BULK_LUA = """
local del = %s
local mods = %s
local withmods = %s
local all = comp:GetToolList(false)
local function nameof(t)
  local ok, a = pcall(function() return t:GetAttrs() end)
  if ok and a then return a.TOOLS_Name, a.TOOLS_RegID end
end
local function feeders(t, into)
  local ok, ins = pcall(function() return t:GetInputList() end)
  if not ok or not ins then return end
  for _, inp in pairs(ins) do
    local o = inp:GetConnectedOutput()
    if o then
      local st = o:GetTool()
      if st then
        local n, r = nameof(st)
        if n and mods[r] and not del[n] then into[n] = true end
      end
    end
  end
end
local n, m = 0, 0
local cand = {}
if withmods then  -- modifiers whose every consumer is being deleted (scanning modifiers, not every input of every target)
  for _, t in pairs(all) do
    local nm, r = nameof(t)
    if nm and mods[r] and not del[nm] then
      local used, feeds = false, false
      for _, o in pairs(t:GetOutputList() or {}) do
        for _, i in pairs(o:GetConnectedInputs() or {}) do
          local ct = i:GetTool()
          local cn = ct and nameof(ct)
          if cn and del[cn] then feeds = true elseif cn then used = true end
        end
      end
      if feeds and not used then cand[nm] = true end
    end
  end
end
comp:Lock()
local ok2, e2 = pcall(function()
  for _, t in pairs(all) do
    local nm = nameof(t)
    if nm and del[nm] and pcall(function() t:Delete() end) then n = n + 1 end
  end
  for pass = 1, 5 do
    local nextc, any = {}, false
    for nm, _ in pairs(cand) do
      local t = comp:FindTool(nm)
      if t then
        local used = false
        for _, o in pairs(t:GetOutputList() or {}) do
          local c = o:GetConnectedInputs()
          if c and next(c) ~= nil then used = true end
        end
        if not used then
          feeders(t, nextc)
          if pcall(function() t:Delete() end) then m = m + 1 end
          any = true
        end
      end
    end
    cand = nextc
    if not any or next(cand) == nil then break end
  end
end)
comp:Unlock()
if not ok2 then error(e2) end
result = n .. "," .. m
"""


def _lua_set(names):
    return "{" + ", ".join("[%s] = true" % json.dumps(n) for n in sorted(names)) + "}"


def bulk_delete(ctx, comp, names, with_mods=True):
    """[rebuild F6/F12] Delete many tools in ONE deferred Lua chunk inside Fusion (1,100 tools one by one over the
    bridge took 130 s). Modifiers that fed only deleted tools go too (chains included). Needs the comp current.
    -> (deleted_count, modifiers_deleted_count)."""
    tsv = ctx.tsv()
    mods = {r for r, v in tsv.registry.items() if v.get("kind") == "modifier"} | {"BezierSpline", "LUTBezier", "PolyPath", "XYPath"}
    if ctx.resolve.GetCurrentPage() != "fusion":  # Execute runs on the Fusion-page comp
        ctx.resolve.OpenPage("fusion")
        time.sleep(1.5)
    code = BULK_LUA % (_lua_set(names), _lua_set(mods), "true" if with_mods else "false")
    r = ctx.lua(comp, code, wait=min(600.0, 30.0 + 0.1 * len(names)))
    d, m = (int(x) for x in (r.split(",") + ["0", "0"])[:2])
    return d, m


def _quiet_list(xs, over=50, sample=10):
    xs = sorted(xs)
    return xs if len(xs) <= over else {"count": len(xs), "sample": xs[:sample]}


@op("tool.delete", "Delete tools by name, glob (e.g. 'Connector_*') or a list of names and globs. withModifiers (default true) also deletes modifiers/splines that only drive the deleted tools (deleting a host never deletes its modifiers, realities §8). 40+ tools on the Fusion-page comp go in one Lua chunk (fast); big results are counts + a sample.",
    [COMP(), P("tool", "string|array", "Name, glob, or list of names/globs.", required=True),
     P("withModifiers", "boolean", "Also delete modifiers feeding only these tools (default true).", default=True)])
def tool_delete(ctx, comp, a):
    targets = ctx.tools_matching(comp, a["tool"])
    if not targets:
        raise OpError("NOT_FOUND", f"no tools match {a['tool']!r}" if not isinstance(a["tool"], list) or len(a["tool"]) <= 10
                      else f"no tools match the {len(a['tool'])} given names/globs")
    names = {n for n, _ in targets}
    if len(names) >= 40 and ctx.is_current(comp):
        d, m = bulk_delete(ctx, comp, names, a.get("withModifiers", True))
        left = sorted(names & set(ctx.names(comp)))
        if left:
            raise OpError("OPERATION_FAILED", f"{len(left)} tools still present after the bulk delete", details={"sample": left[:20]})
        return {"deleted": _quiet_list(names), "modifiersDeleted": m, "via": "lua bulk"}
    # Deleting a group deletes its children: skip children whose parent group is also a target
    # (their handles go stale, and walking them is wasted bridge calls).
    def _parent(t):
        try:
            p = t.ParentTool
            return p.GetAttrs()["TOOLS_Name"] if p else None
        except Exception:  # noqa
            return None
    kept = [(n, t) for n, t in targets if _parent(t) not in names]
    children = sorted(names - {n for n, _ in kept})
    targets = kept
    mods = set()
    if a.get("withModifiers", True):
        mods = _feeding_modifiers(ctx, comp, names)
    comp.Lock()  # no re-render per deletion (mass deletes on a displayed comp crawl otherwise)
    try:
        for n, t in targets:
            t.Delete()
        for m in mods:
            mt = comp.FindTool(m)
            if mt is not None and not _has_consumers(ctx, comp, mt):
                mt.Delete()
    finally:
        comp.Unlock()
    remaining = set(ctx.names(comp))
    left = sorted(names & remaining)
    if left:
        raise OpError("OPERATION_FAILED", f"still present after Delete: {left[:20]}" + (f" (+{len(left) - 20})" if len(left) > 20 else ""))
    return {"deleted": _quiet_list(names), "viaGroup": _quiet_list(children), "modifiersDeleted": _quiet_list(m for m in mods if m not in remaining)}


@op("comp.clear", "Delete every tool in the comp except `keep` (names/globs; default every MediaIn, MediaOut and Resolve's AudioDisplay tool) in ONE Lua chunk: the fast way to wipe a comp before re-pasting a scene [rebuild F6/F12]. One undo event. The comp is made current automatically (Lua runs on the Fusion-page comp); raise timeoutMs above ~1,000 tools.",
    [COMP(), P("keep", "array", "Tool names or globs to keep (default: MediaIn, MediaOut and AudioDisplay tools by regId)."),
     P("dryRun", "boolean", "Only count what would go.")], extra={"paste": True})
def comp_clear(ctx, comp, a):
    allt = {}
    for t in (comp.GetToolList(False) or {}).values():
        ta = t.GetAttrs()
        allt[ta["TOOLS_Name"]] = ta["TOOLS_RegID"]
    if a.get("keep") is not None:
        pats = a["keep"]
        keep = {n for n in allt if any(fnmatch.fnmatchcase(n, pt) for pt in pats)}
    else:
        keep = {n for n, r in allt.items() if r in ("MediaIn", "MediaOut", "AudioDisplay")}  # Resolve adds AudioDisplay to item comps
    tsv = ctx.tsv()
    frontier = list(keep)
    while frontier:  # modifiers/splines driving a kept tool stay with it
        t = comp.FindTool(frontier.pop())
        for i in ((t.GetInputList() or {}).values() if t is not None else []):
            o = i.GetConnectedOutput()
            st = o.GetTool() if o else None
            if st is None:
                continue
            sa = st.GetAttrs()
            if (sa["TOOLS_RegID"] == "BezierSpline" or tsv.kind(sa["TOOLS_RegID"]) == "modifier") and sa["TOOLS_Name"] not in keep:
                keep.add(sa["TOOLS_Name"])
                frontier.append(sa["TOOLS_Name"])
    kill = set(allt) - keep
    if a.get("dryRun") or not kill:
        return {"wouldDelete" if a.get("dryRun") else "deleted": len(kill), "kept": sorted(keep)[:40], "keptCount": len(keep)}
    d, m = bulk_delete(ctx, comp, kill, with_mods=False)
    remaining = ctx.names(comp)
    left = sorted(set(remaining) & kill)
    if left:
        raise OpError("OPERATION_FAILED", f"{len(left)} tools survived comp.clear", details={"sample": left[:20]})
    return {"deleted": len(kill), "kept": sorted(keep)[:40], "remaining": len(remaining)}


def _has_consumers(ctx, comp, t):
    for o in (t.GetOutputList() or {}).values():
        if o.GetConnectedInputs():
            return True
    return False


def _feeding_modifiers(ctx, comp, names):
    """Modifiers (splines, paths, followers...) whose outputs feed only tools in names, recursively."""
    found = set()
    frontier = set(names)
    while frontier:
        nxt = set()
        for n in frontier:
            t = comp.FindTool(n)
            if t is None:
                continue
            for i in (t.GetInputList() or {}).values():
                o = i.GetConnectedOutput()
                if not o:
                    continue
                st = o.GetTool()
                if st is None:
                    continue
                sa = st.GetAttrs()
                kind = "modifier" if sa["TOOLS_RegID"] == "BezierSpline" else ctx.tsv().kind(sa["TOOLS_RegID"])
                if kind != "modifier" or sa["TOOLS_Name"] in found:
                    continue
                consumers = {c[0] for c in ctx.consumers(comp, st)}
                if consumers <= (names | found | {sa["TOOLS_Name"]}):
                    found.add(sa["TOOLS_Name"])
                    nxt.add(sa["TOOLS_Name"])
        frontier = nxt
    return found


@op("tool.rename", "Rename a tool (SetAttrs TOOLS_Name) and verify; invalid characters are rejected up front (Fusion strips them silently). Expressions that referenced the old name are reported (use expression.replace_text to retarget).",
    [COMP(), TOOL(), P("newName", "string", "New unique name.", required=True)])
def tool_rename(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    nn = a["newName"]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nn):
        raise OpError("INVALID_ARGS", f"'{nn}' is invalid: letters, digits, underscore; no leading digit")
    if comp.FindTool(nn) is not None:
        raise OpError("INVALID_ARGS", f"a tool named '{nn}' already exists")
    t.SetAttrs({"TOOLS_Name": nn})
    got = t.GetAttrs()["TOOLS_Name"]
    if got != nn:
        raise OpError("OPERATION_FAILED", f"name became '{got}'")
    refs = [r for r in _all_expressions(ctx, comp) if re.search(r"\b%s\b" % re.escape(a["tool"]), r["expression"])]
    return {"tool": got, "staleExpressionRefs": refs}


@op("tool.list", "List tools with reg ID and pass-through state. Filters: regId, name glob, kind (tool|modifier).",
    [COMP(), P("regId", "string", "Only this registry ID."), P("name", "string", "Name glob."),
     P("kind", "string", "tool or modifier.", enum=("tool", "modifier"))], read=True)
def tool_list(ctx, comp, a):
    out = []
    for t in (comp.GetToolList(False) or {}).values():
        ta = t.GetAttrs()
        reg = ta["TOOLS_RegID"]
        kind = "modifier" if reg == "BezierSpline" or ctx.tsv().kind(reg) == "modifier" else "tool"
        if a.get("regId") and reg != a["regId"]:
            continue
        if a.get("name") and not fnmatch.fnmatchcase(ta["TOOLS_Name"], a["name"]):
            continue
        if a.get("kind") and kind != a["kind"]:
            continue
        out.append({"name": ta["TOOLS_Name"], "regId": reg, "kind": kind, "passThrough": bool(ta.get("TOOLB_PassThrough"))})
    return {"tools": sorted(out, key=lambda r: r["name"]), "count": len(out)}


ATTR_MAP = {"passThrough": "TOOLB_PassThrough", "locked": "TOOLB_Locked", "holdOutput": "TOOLB_HoldOutput",
            "cacheToDisk": "TOOLB_CacheToDisk", "showControls": "TOOLB_ShowControls"}


@op("tool.set_attrs", "Set tool attributes: passThrough (enable/disable), locked, holdOutput, name; tileColor '#hex'. Read back.",
    [COMP(), P("tool", "string|array", "Name, list, or glob.", required=True),
     P("attrs", "object", "{passThrough?, locked?, holdOutput?, tileColor?: '#rrggbb'}", required=True)])
def tool_set_attrs(ctx, comp, a):
    res = {}
    for n, t in ctx.tools_matching(comp, a["tool"]):
        sa = {}
        for k, v in a["attrs"].items():
            if k == "tileColor":
                c = color(v)
                t.TileColor = {"R": c[0], "G": c[1], "B": c[2]}
            elif k in ATTR_MAP:
                sa[ATTR_MAP[k]] = bool(v)
            else:
                raise OpError("INVALID_ARGS", f"unknown attr '{k}'", hint="Allowed: " + ", ".join(list(ATTR_MAP) + ["tileColor"]))
        if sa:
            t.SetAttrs(sa)
        ta = t.GetAttrs()
        res[n] = {k: bool(ta.get(v)) for k, v in ATTR_MAP.items() if k in a["attrs"]}
        if "tileColor" in a["attrs"]:
            res[n]["tileColor"] = jv(t.TileColor)
    return {"tools": res}


@op("tool.duplicate", "Duplicate a tool with its settings (Lua comp:Copy + comp:Paste on the current Fusion-page comp). The copy gets Fusion's next free name unless newName is given; inputs from outside the copied set stay unconnected.",
    [COMP(), TOOL(), P("newName", "string", "Name for the copy.")], extra={"paste": True})
def tool_duplicate(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    text = ctx.lua(comp, "local s = comp:CopySettings(comp:FindTool(%s)); result = bmd.writestring(s)" % json.dumps(a["tool"]))
    res = ctx.paste(comp, text)
    added = [n for n in res["added"] if comp.FindTool(n).GetAttrs()["TOOLS_RegID"] == t.GetAttrs()["TOOLS_RegID"]]
    if not added:
        raise OpError("OPERATION_FAILED", "copy was not created", details=res)
    new = added[0]
    if a.get("newName"):
        nt = comp.FindTool(new)
        nt.SetAttrs({"TOOLS_Name": a["newName"]})
        new = nt.GetAttrs()["TOOLS_Name"]
    return {"tool": new, "added": res["added"]}


@op("tool.set_position", "Place a tool in the node editor (FlowView.SetPos). GRID units: x + 1 = the next column (110 flow px), y + 1 = the "
    "next row (33 flow px); (x, y) is the tool's cell top-left, so its ViewInfo Pos (tile center) = ((x + 0.5) * 110, (y + 0.5) * 33); "
    "Fusion snaps x to half columns and y to whole rows (live, 21.1). comp.layout tidies a whole comp. Needs the comp showing on the Fusion page.",
    [COMP(), TOOL(), P("x", "number", "Grid X (columns).", required=True), P("y", "number", "Grid Y (rows).", required=True)], undo=False)
def tool_set_position(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    fv = comp.CurrentFrame.FlowView if comp.CurrentFrame else None
    if fv is None:
        raise OpError("NOT_CURRENT", "no FlowView for this comp", hint="comp.set_current first")
    fv.SetPos(t, a["x"], a["y"])
    return {"position": jv(fv.GetPosTable(t))}


@op("tool.select", "Make a tool the active tool (Inspector shows it) and/or select it in the flow. tool omitted = clear the active tool.",
    [COMP(), P("tool", "string", "Tool to activate (omit to clear)."), P("select", "boolean", "Also flow-select it (default true).", default=True)], undo=False)
def tool_select(ctx, comp, a):
    if not a.get("tool"):
        comp.SetActiveTool(None)
        return {"activeTool": None}
    t = ctx.tool(comp, a["tool"])
    comp.SetActiveTool(t)
    if a.get("select", True):
        try:
            comp.CurrentFrame.FlowView.Select(t, True)
        except Exception:
            pass
    act = comp.ActiveTool
    return {"activeTool": act.GetAttrs()["TOOLS_Name"] if act else None}


@op("tool.bounds", "Measure a tool's image bounds at a frame. method 'dod' = Output.GetDoD (domain of definition, cheap); 'pixels' = render a PNG and measure visible alpha (exact, slower). Returns pixel box (top-left origin) and normalized box (Y up).",
    [COMP(), TOOL(), FRAME, P("method", "string", "dod or pixels (default dod).", enum=("dod", "pixels"), default="dod")], undo="discard")
def tool_bounds(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    W, H, _ = ctx.fmt(comp)
    f = a.get("frame", comp.CurrentTime)
    if a.get("method", "dod") == "dod":
        o = t.FindMainOutput(1)
        d = jv(o.GetDoD(f)) if o else None
        if not d or len(d) < 4:
            raise OpError("OPERATION_FAILED", f"GetDoD returned {d!r}", hint="Try method 'pixels'.")
        x0, y0, x1, y1 = [float(v) for v in d[:4]]  # Fusion DataWindow: left, bottom, right, top (pixels, Y up)
        box = {"x": x0, "y": H - y1, "width": x1 - x0, "height": y1 - y0}
        raw = d
    else:
        from .build import render_one
        path = render_one(ctx, comp, t, f, os.path.join(config.out_dir(), "_bounds_%s_%d.png" % (a["tool"], int(f))))
        from .base import png_bbox
        b = png_bbox(path)
        if b is None:
            return {"empty": True, "method": "pixels", "path": path}
        sx, sy = W / b["imageWidth"], H / b["imageHeight"]
        box = {"x": b["x"] * sx, "y": b["y"] * sy, "width": b["width"] * sx, "height": b["height"] * sy}
        raw = b
    norm = {"center": [(box["x"] + box["width"] / 2) / W, 1 - (box["y"] + box["height"] / 2) / H],
            "width": box["width"] / W, "height": box["height"] / H}
    return {"method": a.get("method", "dod"), "frame": f, "pixels": {k: round(v, 2) for k, v in box.items()}, "normalized": norm, "raw": raw}


# ================================================================ input (property analog)

@op("input.set", "Set one input (static value, or a key at `frame` when the input is animated). Validated against the live TSV (ID, type, ComboID options) and the live input list; read back. Points: [x, y] normalized Y-up, or {px: [x, y]} top-left pixels.",
    [COMP(), TOOL(), INPUT(), P("value", "any", "Number | string | [x, y] | {px: [x, y]}.", required=True), FRAME])
def input_set(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    return {"tool": a["tool"], "input": a["input"], "value": ctx.set_input(comp, t, a["input"], a["value"], a.get("frame"))}


@op("input.set_many", "Set several inputs on one or more tools in one call (transform.set/layer.set_props analog). values = {tool: {input: value}}. Each is validated and read back; the first failure stops the call.",
    [COMP(), P("values", "object", "{toolName: {inputId: value, ...}, ...}", required=True), FRAME])
def input_set_many(ctx, comp, a):
    out = {}
    for tn, vals in a["values"].items():
        if not isinstance(vals, dict):
            raise OpError("INVALID_ARGS", f"values.{tn} must be an object")
        t = ctx.tool(comp, tn)
        out[tn] = {k: ctx.set_input(comp, t, k, v, a.get("frame")) for k, v in vals.items()}
    return {"set": out}


@op("input.get", "Read an input value at a frame (fractional frames allowed), plus its expression and source.",
    [COMP(), TOOL(), INPUT(), FRAME], read=True)
def input_get(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    i = ctx.inp(t, a["input"])
    f = a.get("frame", comp.CurrentTime)
    dt = i.GetAttrs().get("INPS_DataType")
    out = {"tool": a["tool"], "input": a["input"], "type": dt, "frame": f, "source": ctx.source_of(t, a["input"])}
    if dt not in ("Image", "Mask", "DataType3D", "MtlGraph3D", "Particles"):
        out["value"] = jv(t.GetInput(a["input"], f))
    e = i.GetExpression()
    if e:
        out["expression"] = e
    return out


@op("input.list", "List a tool's inputs (ID, label, type, control, value, source, expression). Filter by substring or type.",
    [COMP(), TOOL(), P("filter", "string", "Case-insensitive substring of ID or label."), P("type", "string", "Only this INPS_DataType (Number, Point, Text, FuID, Image, ...).")],
    read=True)
def input_list(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    d = tool_detail(ctx, comp, t, True)
    rows = d["inputs"]
    if a.get("filter"):
        q = a["filter"].lower()
        rows = [r for r in rows if q in r["id"].lower() or q in (r.get("name") or "").lower()]
    if a.get("type"):
        rows = [r for r in rows if r["type"] == a["type"]]
    return {"tool": a["tool"], "regId": d["regId"], "inputs": rows, "count": len(rows)}


@op("input.connect", "Connect an input to another tool's output (checked ConnectInput + readback; loops and type mismatches fail loudly). Generic-typed inputs (a pasted Switch's Input0..N) that refuse the tool are retried with the source's Output object and Input.ConnectTo [rebuild F8].",
    [COMP(), TOOL("Destination tool."), INPUT("Destination input (Input, Background, Foreground, EffectMask, SceneInput1, ...)."),
     P("source", "string", "Source tool name.", required=True), P("output", "string", "Source output ID (default main output).")])
def input_connect(ctx, comp, a):
    return {"connected": ctx.connect(ctx.tool(comp, a["tool"]), a["input"], ctx.tool(comp, a["source"]), a.get("output"))}


@op("input.disconnect", "Disconnect an input (ConnectInput(id, None)). For an animated/modified value input this removes the driver: prefer keyframe.clear / modifier.remove which also restore the value.",
    [COMP(), TOOL(), INPUT()])
def input_disconnect(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    ctx.inp(t, a["input"])
    t.ConnectInput(a["input"], None)
    got = ctx.source_of(t, a["input"])
    if got:
        raise OpError("OPERATION_FAILED", f"still connected to {got}")
    return {"disconnected": True}


PUBLISH = {"Number": "PublishNumber", "Point": "PublishPoint", "Text": "PublishText", "FuID": "PublishFuID",
           "Gradient": "PublishGradient", "PolyLine": "PublishPolyLine"}


@op("input.publish", "Publish an input (right-click > Publish): adds a Publish<Type> modifier so other inputs can link to it with input.link. Returns the publish modifier name.",
    [COMP(), TOOL(), INPUT()])
def input_publish(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    dt = ctx.inp(t, a["input"]).GetAttrs().get("INPS_DataType")
    reg = PUBLISH.get(dt)
    if not reg:
        raise OpError("INVALID_ARGS", f"cannot publish a {dt} input", hint="Publishable: " + ", ".join(PUBLISH))
    m = add_modifier(ctx, comp, t, a["input"], reg)
    return {"publish": m, "value": jv(t.GetInput(a["input"], comp.CurrentTime))}


@op("input.link", "Drive an input from another tool's input (expression link `Other.Input`, the scriptable form of Connect To). Clearing restores a static value (expression.clear).",
    [COMP(), TOOL(), INPUT(), P("sourceTool", "string", "Tool to follow.", required=True), P("sourceInput", "string", "Input to follow.", required=True),
     P("scale", "number", "Optional multiplier (numbers only)."), P("offset", "number", "Optional additive offset (numbers only).")])
def input_link(ctx, comp, a):
    st = ctx.tool(comp, a["sourceTool"])
    ctx.inp(st, a["sourceInput"])
    e = "%s.%s" % (a["sourceTool"], a["sourceInput"])
    if a.get("scale") is not None:
        e = "(%s) * %s" % (e, a["scale"])
    if a.get("offset") is not None:
        e = "(%s) + %s" % (e, a["offset"])
    return expression_set(ctx, comp, {"tool": a["tool"], "input": a["input"], "expression": e})


@op("input.add_control", "Add a user control (slider/checkbox/point/text/combo) to a tool via Tool.UserControls + Refresh (verified through the bridge). The AE slider/checkbox/color control-effect analog; drive other inputs from it with input.link or expressions.",
    [COMP(), TOOL(), P("id", "string", "New input ID (letters/digits).", required=True),
     P("label", "string", "UI label (default id)."),
     P("type", "string", "slider | checkbox | point | text | combo | screw.", enum=("slider", "checkbox", "point", "text", "combo", "screw"), default="slider"),
     P("default", "any", "Default value."), P("min", "number", "Slider min (default 0)."), P("max", "number", "Slider max (default 1)."),
     P("options", "array", "Combo option labels."), P("page", "string", "Inspector page (default 'Controls').")])
def input_add_control(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", a["id"]):
        raise OpError("INVALID_ARGS", "id must be letters/digits/underscore")
    if a["id"] in ctx.inputs(t):  # [live, gapfix pass] a control named "Depth" on a Background became its bit-depth input (73 read back 4)
        raise OpError("INVALID_ARGS", f"{a['tool']} already has an input '{a['id']}'",
                      hint="Pick an id no built-in input uses (input.list shows them), e.g. prefix it: 'Ctl" + a["id"] + "'.")
    kind = a.get("type", "slider")
    spec = {"LINKS_Name": a.get("label") or a["id"], "ICS_ControlPage": a.get("page", "Controls")}
    if kind in ("slider", "screw", "checkbox", "combo"):
        spec.update(LINKID_DataType="Number", INPID_InputControl={"slider": "SliderControl", "screw": "ScrewControl",
                                                                  "checkbox": "CheckboxControl", "combo": "ComboControl"}[kind])
        if kind in ("slider", "screw"):
            spec.update(INP_MinScale=a.get("min", 0.0), INP_MaxScale=a.get("max", 1.0), INP_Default=a.get("default", 0.0))
        elif kind == "checkbox":
            spec.update(INP_Default=1 if a.get("default") else 0, INP_Integer=True)
        else:
            opts = a.get("options") or []
            if not opts:
                raise OpError("INVALID_ARGS", "combo needs options")
            for k, o in enumerate(opts):
                spec[k + 1] = {"CCS_AddString": o}
            spec.update(INP_Default=a.get("default", 0), INP_Integer=True)
    elif kind == "point":
        spec.update(LINKID_DataType="Point", INPID_InputControl="OffsetControl", INPID_PreviewControl="CrosshairControl",
                    INP_DefaultX=(a.get("default") or [0.5, 0.5])[0], INP_DefaultY=(a.get("default") or [0.5, 0.5])[1])
    else:
        spec.update(LINKID_DataType="Text", INPID_InputControl="TextEditControl", TEC_Lines=1)
    uc = t.UserControls or {}
    uc = dict(uc) if isinstance(uc, dict) else {}
    uc[a["id"]] = spec
    t.UserControls = uc
    t.Refresh()
    t = comp.FindTool(a["tool"])
    if a["id"] not in ctx.inputs(t):
        raise OpError("OPERATION_FAILED", "user control did not appear after Refresh")
    return {"tool": a["tool"], "input": a["id"], "value": jv(t.GetInput(a["id"], comp.CurrentTime))}


@op("input.set_color", "Set a color from '#hex' or [r,g,b(,a)] 0-1 onto the right channel inputs for the tool type (Background TopLeft*, Text+ element 1 Red1.., sShapes Red.., or an explicit prefix/suffix).",
    [COMP(), TOOL(), P("color", "string|array", "'#rrggbb' or [r,g,b(,a)].", required=True),
     P("prefix", "string", "Channel name prefix (e.g. 'TopLeft', 'Tint')."), P("suffix", "string", "Channel suffix (e.g. '1' for Text+ element 1)."),
     P("alpha", "boolean", "Also set Alpha (default true when 4 channels given).")])
def input_set_color(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    reg = t.GetAttrs()["TOOLS_RegID"]
    c = color(a["color"])
    pre, suf = a.get("prefix"), a.get("suffix")
    if pre is None and suf is None:
        pre, suf = {"Background": ("TopLeft", ""), "TextPlus": ("", "1")}.get(reg, ("", ""))
    pre, suf = pre or "", suf or ""
    ins = ctx.inputs(t)
    chans = ["Red", "Green", "Blue"] + (["Alpha"] if a.get("alpha", len(a["color"]) == 4 if isinstance(a["color"], list) else False) else [])
    names = [pre + ch + suf for ch in chans]
    missing = [n for n in names if n not in ins]
    if missing:
        raise OpError("NOT_FOUND", f"{reg} has no inputs {missing}", hint="Pass prefix/suffix (see input.list filter 'Red').")
    got = {n: ctx.set_input(comp, t, n, c[k]) for k, n in enumerate(names)}
    return {"tool": a["tool"], "set": got}


# ================================================================ modifier

def add_modifier(ctx, comp, t, iid, reg, first_frame=None):
    """AddModifier judged by GetConnectedOutput changing (its return value is unreliable, realities §8);
    orphans from a failed attempt are deleted."""
    err = ctx.tsv().check_reg(reg, "modifier") if reg != "BezierSpline" else None
    if err:
        raise OpError("INVALID_ARGS", err)
    i = ctx.inp(t, iid)
    if i.GetExpression():
        raise OpError("INVALID_ARGS", f"{iid} has an expression", hint="expression.clear first")
    before_src = ctx.source_of(t, iid)
    before = set(ctx.names(comp))
    if first_frame is not None:
        comp.CurrentTime = first_frame  # stray seeded key lands on the first key frame (realities §6)
    t.AddModifier(iid, reg)
    after_src = ctx.source_of(t, iid)
    new = set(ctx.names(comp)) - before
    if not after_src or after_src == before_src or after_src[0] not in new:
        for n in new:
            x = comp.FindTool(n)
            if x is not None:
                x.Delete()
        raise OpError("OPERATION_FAILED", f"AddModifier({iid}, {reg}) did not attach (input type may not accept it)",
                      details={"orphansRemoved": sorted(new)})
    return after_src[0]


@op("modifier.add", "Attach a modifier (StyledTextFollower, PerturbPoint, Shake, XYPath, PolyPath, Calculation, Offset, LUTLookup (Anim Curves), TextScramble, TimeCode, ...) to an input. Success is judged by the input's connection, orphans from a failed attempt are removed; optional modifier inputs are set with readback.",
    [COMP(), TOOL(), INPUT(), P("modifier", "string", "Modifier registry ID.", required=True),
     P("inputs", "object", "{inputId: value} for the new modifier."), P("name", "string", "Rename the modifier.")])
def modifier_add(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    m = add_modifier(ctx, comp, t, a["input"], a["modifier"])
    mt = comp.FindTool(m)
    if a.get("name"):
        mt.SetAttrs({"TOOLS_Name": a["name"]})
        m = mt.GetAttrs()["TOOLS_Name"]
    got = {k: ctx.set_input(comp, mt, k, v) for k, v in (a.get("inputs") or {}).items()}
    return {"modifier": m, "regId": a["modifier"], "drives": [a["tool"], a["input"]], "inputs": got,
            "modifierInputs": sorted(ctx.inputs(mt))[:60]}


@op("modifier.list", "List modifiers (and splines) in the comp with the inputs they drive; orphans (driving nothing) are flagged.",
    [COMP()], read=True)
def modifier_list(ctx, comp, a):
    out = []
    for t in (comp.GetToolList(False) or {}).values():
        ta = t.GetAttrs()
        reg = ta["TOOLS_RegID"]
        if reg != "BezierSpline" and ctx.tsv().kind(reg) != "modifier":
            continue
        cons = ctx.consumers(comp, t)
        out.append({"name": ta["TOOLS_Name"], "regId": reg, "drives": [[c[0], c[1]] for c in cons], "orphan": not cons})
    return {"modifiers": sorted(out, key=lambda r: r["name"])}


@op("modifier.remove", "Remove the modifier/spline driving an input and restore a static value (the value at the current frame, or `value`).",
    [COMP(), TOOL(), INPUT(), P("value", "any", "Static value to restore (default: value at current frame)."),
     P("deleteModifier", "boolean", "Delete the modifier tool if nothing else uses it (default true).", default=True)])
def modifier_remove(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    src = ctx.source_of(t, a["input"])
    if not src:
        raise OpError("NOT_FOUND", f"{a['tool']}.{a['input']} has no modifier")
    keep = a["value"] if "value" in a else jv(t.GetInput(a["input"], comp.CurrentTime))
    t.ConnectInput(a["input"], None)
    mt0 = comp.FindTool(src[0])
    if mt0 is not None:  # '<Input>Clone' mirrors on the same host keep their own link: drop them too
        for cn, ci, _ in ctx.consumers(comp, mt0):
            if cn == a["tool"] and ci == a["input"] + "Clone":
                t.ConnectInput(ci, None)
    deleted = False
    mt = comp.FindTool(src[0])
    auto = mt is None  # [live] Fusion deletes a modifier on its own once its last consumer is disconnected
    deleted = auto
    if a.get("deleteModifier", True) and mt is not None and not _has_consumers(ctx, comp, mt):
        mods = _feeding_modifiers(ctx, comp, {src[0]})
        mt.Delete()
        for m in mods:
            x = comp.FindTool(m)
            if x is not None and not _has_consumers(ctx, comp, x):
                x.Delete()
        deleted = True
    val = ctx.set_input(comp, t, a["input"], keep) if keep is not None else None
    return {"removed": src[0], "deleted": deleted, "autoRemovedByFusion": auto, "value": val}


@op("modifier.remove_orphans", "Delete modifiers/splines whose outputs drive nothing (left by failed AddModifier calls or deleted hosts, realities §8/§13).",
    [COMP(), P("dryRun", "boolean", "Only report (default false).")])
def modifier_remove_orphans(ctx, comp, a):
    gone = []
    for _ in range(5):  # chains of modifiers become orphans in turn
        found = [r["name"] for r in modifier_list(ctx, comp, {})["modifiers"] if r["orphan"]]
        if not found or a.get("dryRun"):
            return {"orphans": found if a.get("dryRun") else [], "deleted": gone}
        for n in found:
            x = comp.FindTool(n)
            if x is not None:
                x.Delete()
                gone.append(n)
    return {"deleted": gone}


# ================================================================ expression

def _all_expressions(ctx, comp):
    """Every expression; '<Input>Clone' mirrors of a listed input are skipped (they follow their base)."""
    out = []
    for t in (comp.GetToolList(False) or {}).values():
        tn = t.GetAttrs()["TOOLS_Name"]
        ids = {iid_of(i) for i in (t.GetInputList() or {}).values()}
        for i in (t.GetInputList() or {}).values():
            iid = iid_of(i)
            if iid.endswith("Clone") and iid[:-5] in ids:
                continue
            try:
                e = i.GetExpression()
            except Exception:
                e = None
            if e:
                out.append({"tool": tn, "input": iid_of(i), "expression": e})
    return out


@op("expression.set", "Set a SimpleExpression on an input and verify it evaluates (nil = error, reverted). Rules: `time` is the frame number, trig is radians, no noise(); Point results use Point(x, y); other tools by name (Title.Size), other frames via Tool:GetValue('Input', time - 5).",
    [COMP(), TOOL(), INPUT(), P("expression", "string", "SimpleExpression text (without the leading '=').", required=True),
     P("allowNil", "boolean", "Keep the expression even if it evaluates to nil at the current frame (default false).")])
def expression_set(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    i = ctx.inp(t, a["input"])
    e = a["expression"].lstrip("=").strip()
    if re.search(r"\bnoise\s*\(", e):
        raise OpError("INVALID_ARGS", "noise() is not available in SimpleExpressions (realities §7)",
                      hint="Use the PerturbNumber/PerturbPoint/Shake modifiers or a sum of incommensurate sines.")
    if ctx.source_of(t, a["input"]):
        raise OpError("INVALID_ARGS", f"{a['input']} is driven by {ctx.source_of(t, a['input'])[0]}", hint="modifier.remove or keyframe.clear first")
    prev_expr = i.GetExpression()
    prev = jv(t.GetInput(a["input"], comp.CurrentTime))
    i.SetExpression(e)
    got = i.GetExpression()
    val = t.GetInput(a["input"], comp.CurrentTime)
    if val is None and not a.get("allowNil"):
        i.SetExpression(prev_expr or None)  # None, never "" (realities: "" blocks later SetInput)
        if not prev_expr and prev is not None:
            try:
                ctx.set_input(comp, t, a["input"], prev)
            except OpError:
                pass
        raise OpError("OPERATION_FAILED", f"expression evaluates to nil at frame {num(comp.CurrentTime)}; reverted",
                      hint="Check names (Tool.Input), radians, `time` in frames, Point(x, y) for points.")
    return {"tool": a["tool"], "input": a["input"], "expression": got, "value": jv(val)}


def clear_expression(ctx, comp, t, iid, value=None, restore="evaluated"):
    """[live 2026-09-26] SetExpression(None) clears cleanly and brings back the pre-expression static value;
    SetExpression("") leaves 0 AND silently blocks every later SetInput on that input until SetExpression(None).
    restore: 'evaluated' keeps what the expression showed at the current frame (default), 'previous' keeps the
    pre-expression value, or pass value."""
    i = ctx.inp(t, iid)
    evaluated = jv(t.GetInput(iid, comp.CurrentTime))
    i.SetExpression(None)
    keep = value if value is not None else (evaluated if restore == "evaluated" else None)
    if keep is not None:
        return ctx.set_input(comp, t, iid, keep)
    return jv(t.GetInput(iid, comp.CurrentTime))


@op("expression.clear", "Remove an input's expression with value restore: keeps the value it evaluated to at the current frame (restore 'evaluated', default), the pre-expression value ('previous'), or `value`. Uses SetExpression(None): SetExpression('') leaves 0 and blocks later SetInput (live-verified).",
    [COMP(), TOOL(), INPUT(), P("value", "any", "Value to restore."),
     P("restore", "string", "evaluated | previous (default evaluated).", enum=("evaluated", "previous"), default="evaluated")])
def expression_clear(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    if not ctx.inp(t, a["input"]).GetExpression():
        raise OpError("NOT_FOUND", f"{a['tool']}.{a['input']} has no expression")
    v = clear_expression(ctx, comp, t, a["input"], a.get("value"), a.get("restore", "evaluated"))
    return {"tool": a["tool"], "input": a["input"], "value": v}


@op("expression.list", "List every expression in the comp with its current value.", [COMP()], read=True)
def expression_list(ctx, comp, a):
    rows = _all_expressions(ctx, comp)
    for r in rows:
        try:
            r["value"] = jv(comp.FindTool(r["tool"]).GetInput(r["input"], comp.CurrentTime))
        except Exception:
            r["value"] = None
    return {"expressions": rows, "count": len(rows)}


@op("expression.disable_all", "Clear every expression in the comp (value-restoring) and return a manifest for expression.restore_all.",
    [COMP(), P("tool", "string", "Only tools matching this glob.")])
def expression_disable_all(ctx, comp, a):
    man = []
    for r in _all_expressions(ctx, comp):
        if a.get("tool") and not fnmatch.fnmatchcase(r["tool"], a["tool"]):
            continue
        t = comp.FindTool(r["tool"])
        clear_expression(ctx, comp, t, r["input"])
        man.append(r)
    return {"manifest": man, "count": len(man)}


@op("expression.restore_all", "Re-apply expressions from a manifest (expression.disable_all), optionally with text replacements {old: new}.",
    [COMP(), P("manifest", "array", "[{tool, input, expression}]", required=True), P("replacements", "object", "{old: new} applied to each expression.")])
def expression_restore_all(ctx, comp, a):
    done, failed = [], []
    for r in a["manifest"]:
        e = r["expression"]
        for old, new in (a.get("replacements") or {}).items():
            e = e.replace(old, new)
        try:
            done.append(expression_set(ctx, comp, {"tool": r["tool"], "input": r["input"], "expression": e, "allowNil": True}))
        except OpError as err:
            failed.append({"tool": r.get("tool"), "input": r.get("input"), "error": err.message})
    if failed:
        raise OpError("OPERATION_FAILED", f"{len(failed)} of {len(a['manifest'])} expressions failed", details={"failed": failed, "restored": done})
    return {"restored": len(done)}


@op("expression.replace_text", "Find/replace text in every expression of the comp (e.g. after renaming a tool). Word-boundary match when wholeWord (default true).",
    [COMP(), P("find", "string", "Text to find.", required=True), P("replace", "string", "Replacement.", required=True),
     P("wholeWord", "boolean", "Match whole identifiers only (default true).", default=True)])
def expression_replace_text(ctx, comp, a):
    pat = r"\b%s\b" % re.escape(a["find"]) if a.get("wholeWord", True) else re.escape(a["find"])
    changed = []
    for r in _all_expressions(ctx, comp):
        e2 = re.sub(pat, a["replace"], r["expression"])
        if e2 != r["expression"]:
            ctx.inp(comp.FindTool(r["tool"]), r["input"]).SetExpression(e2)
            changed.append({"tool": r["tool"], "input": r["input"], "expression": e2})
    return {"changed": changed, "count": len(changed)}


# ================================================================ keyframe

def curves():
    """Cubic-bezier presets: fusion_build.CURVES when available (superset of fusion_kit.EASE)."""
    try:
        from .base import build_module
        c = dict(build_module()["CURVES"])
    except Exception:
        c = dict(kit()["EASE"])
    c.setdefault("linear", None)
    c["hold"] = "step"
    c["step"] = "step"
    return c


def ease_points(ease, D, V, fps):
    """-> ('bezier', x1, y1, x2, y2) | ('linear',) | ('hold',). Accepts a preset name, [x1,y1,x2,y2],
    or AE-style {outInfluence, outSpeed, inInfluence, inSpeed} (influence %, speed units/second)."""
    if ease is None:
        return ("linear",)
    if isinstance(ease, str):
        cv = curves()
        if ease not in cv:
            from ..schema import suggest
            s = suggest(ease, list(cv))
            raise OpError("INVALID_ARGS", f"unknown ease '{ease}'" + (f" - did you mean '{s}'?" if s else ""), details={"presets": sorted(cv)})
        ease = cv[ease]
        if ease is None:
            return ("linear",)
        if ease == "step":
            return ("hold",)
    if isinstance(ease, dict):
        xo = float(ease.get("outInfluence", 33.33)) / 100
        xi = float(ease.get("inInfluence", 33.33)) / 100
        so, si = float(ease.get("outSpeed", 0)), float(ease.get("inSpeed", 0))
        y1 = (so * xo * D / fps) / V if V else 0
        y2 = 1 - ((si * xi * D / fps) / V if V else 0)
        return ("bezier", xo, y1, 1 - xi, y2)
    if isinstance(ease, (list, tuple)) and len(ease) == 4:
        x1, y1, x2, y2 = (float(v) for v in ease)
        if not (0 <= x1 <= 1 and 0 <= x2 <= 1):
            raise OpError("INVALID_ARGS", "cubic-bezier x values must be within 0..1")
        return ("bezier", x1, y1, x2, y2)
    raise OpError("INVALID_ARGS", f"bad ease {ease!r}", hint="preset name, [x1,y1,x2,y2], or {outInfluence,outSpeed,inInfluence,inSpeed}")


def fkey(f):
    return str(int(f)) if float(f).is_integer() else str(round(float(f), 3))


def _key_frames(raw):
    """Numeric frame keys only: some splines (Planar Tracker) also carry a "Value" entry."""
    out = []
    for k in (raw or {}):
        try:
            out.append(float(k))
        except (TypeError, ValueError):
            pass
    return sorted(out)


def spline_keys(sp):
    """GetKeyFrames -> sorted [(frame, {value, RH?, LH?, flags?})]. Non-numeric entries are skipped."""
    raw = sp.GetKeyFrames() or {}
    out = []
    for k, v in raw.items():
        try:
            f = float(k)
        except (TypeError, ValueError):
            continue
        row = {"frame": f}
        if isinstance(v, dict):
            row["value"] = jv(v.get(1, v.get("1")))
            for h in ("RH", "LH"):
                if h in v:
                    row[h] = jv(v[h])
            if "Flags" in v:
                row["flags"] = jv(v["Flags"])
        else:
            row["value"] = jv(v)
        out.append(row)
    return sorted(out, key=lambda r: r["frame"])


def _meta(sp):
    try:
        m = sp.GetData("fc_ease")
        return json.loads(m) if m else {}
    except Exception:
        return {}


def write_spline(comp, sp, keys, eases, loop=None, fps=24):
    """keys: sorted [(frame, value)], eases: per segment ('bezier'...)/('linear',)/('hold',).
    Handles are RELATIVE {dt, dv} in Python (realities §6). Replace twice, assert the key set."""
    kf = {}
    for n, (f, v) in enumerate(keys):
        kf[f] = {1: v}
    for s in range(len(keys) - 1):
        (f0, v0), (f1, v1) = keys[s], keys[s + 1]
        D, V = f1 - f0, v1 - v0
        e = eases[s]
        if e[0] == "bezier":
            _, x1, y1, x2, y2 = e
            kf[f0]["RH"] = {1: x1 * D, 2: y1 * V}
            kf[f1]["LH"] = {1: (x2 - 1) * D, 2: (y2 - 1) * V}
        elif e[0] == "linear":
            kf[f0]["RH"] = {1: D / 3, 2: V / 3}
            kf[f1]["LH"] = {1: -D / 3, 2: -V / 3}
        elif e[0] == "hold":
            kf[f0].setdefault("Flags", {})["StepIn"] = True
            kf[f1].setdefault("Flags", {})["StepIn"] = True
    if loop and keys:
        flag = {"loop": {"Loop": True}, "loop_rel": {"Loop": True, "LoopRel": True}, "pingpong": {"Loop": True, "PingPong": True}}.get(loop)
        if flag:
            kf[keys[0][0]].setdefault("Flags", {}).update(flag)
    want = sorted(float(f) for f, _ in keys)
    got = None
    for attempt in range(3):
        # [live 2026-09-26] SetKeyFrames(dict, True) does NOT remove a stray/seeded key (e.g. frame 0) and a
        # range DeleteKeyFrames can miss it; single-frame DeleteKeyFrames(f) removes it (with time moved away).
        sp.SetKeyFrames(kf, True)
        got = _key_frames(sp.GetKeyFrames())
        stale = [f for f in got if f not in want]
        if not stale:
            break
        if comp.CurrentTime in stale and want:
            comp.CurrentTime = want[0]
        for f in stale:
            sp.DeleteKeyFrames(f)
        sp.SetKeyFrames(kf, True)
        got = _key_frames(sp.GetKeyFrames())
        if got == want:
            break
    if got != want:
        raise OpError("OPERATION_FAILED", f"key set mismatch after SetKeyFrames: {got} != {want}")
    return kf


def _encode_ease(e):
    return list(e)


def _decode_ease(e):
    return tuple(e)


def get_spline(ctx, comp, t, iid, create=False, first_frame=None):
    src = ctx.source_of(t, iid)
    if src:
        st = comp.FindTool(src[0])
        reg = st.GetAttrs()["TOOLS_RegID"]
        if reg in ("BezierSpline", "XYPath"):
            return st
        raise OpError("INVALID_ARGS", f"{t.GetAttrs()['TOOLS_Name']}.{iid} is driven by {reg} '{src[0]}', not keyframes",
                      hint="modifier.remove first (PolyPath points: use keyframe.clear then key again; XYPath is used for points).")
    if not create:
        return None
    dt = ctx.inp(t, iid).GetAttrs().get("INPS_DataType")
    if dt == "Point":
        m = add_modifier(ctx, comp, t, iid, "XYPath", first_frame)
        return comp.FindTool(m)
    if dt != "Number":
        raise OpError("INVALID_ARGS", f"{iid} is {dt}; keyframes are supported on Number and Point inputs",
                      hint="Text: use modifiers (StyledTextFollower, TextTimer); FuID/Combo values: key an expression instead.")
    m = add_modifier(ctx, comp, t, iid, "BezierSpline", first_frame)
    return comp.FindTool(m)


def _axis_splines(ctx, comp, host, first_frame, create=True):
    """XYPath host -> (X spline, Y spline)."""
    out = []
    for ax in ("X", "Y"):
        out.append(get_spline(ctx, comp, host, ax, create, first_frame))
    return out


def _key_spline(ctx, comp, sp, new_keys, ease, fps, loop=None, per_key=None):
    """Merge new (frame, value) keys into spline sp; recompute touched segments; keep others via stored meta."""
    meta = _meta(sp)
    old = {r["frame"]: r["value"] for r in spline_keys(sp)}
    old_seg = {float(k): _decode_ease(v) for k, v in meta.get("seg", {}).items()}
    merged = dict(old)
    touched = set()
    for f, v in new_keys:
        merged[float(f)] = v
        touched.add(float(f))
    keys = sorted(merged.items())
    eases = []
    for s in range(len(keys) - 1):
        f0, f1 = keys[s][0], keys[s + 1][0]
        D, V = f1 - f0, (keys[s + 1][1] or 0) - (keys[s][1] or 0)
        if f0 in touched or f1 in touched:
            e = (per_key or {}).get(f0, ease)
            eases.append(ease_points(e, D, V, fps))
        elif f0 in old_seg:
            e = old_seg[f0]
            if e[0] == "bezier":
                eases.append(e)
            else:
                eases.append(e)
        else:
            eases.append(("linear",))
    write_spline(comp, sp, keys, eases, loop or meta.get("loop"), fps)
    sp.SetData("fc_ease", json.dumps({"seg": {str(keys[s][0]): _encode_ease(eases[s]) for s in range(len(eases))},
                                      "loop": loop or meta.get("loop")}))
    return keys


def _norm_keys(a):
    keys = a.get("keys")
    if keys is None:
        if "frame" not in a or "value" not in a:
            raise OpError("INVALID_ARGS", "pass keys: [[frame, value], ...] or frame + value")
        keys = [[a["frame"], a["value"]]]
    out, per = [], {}
    for k in keys:
        if isinstance(k, dict):
            f, v = k.get("frame"), k.get("value")
            if k.get("ease") is not None:
                per[float(f)] = k["ease"]
        elif isinstance(k, (list, tuple)) and len(k) >= 2:
            f, v = k[0], k[1]
        else:
            raise OpError("INVALID_ARGS", f"bad key {k!r}: use [frame, value] or {{frame, value, ease?}}")
        if not isinstance(f, (int, float)):
            raise OpError("INVALID_ARGS", f"key frame must be a number, got {f!r}")
        out.append((float(f), v))
    return sorted(out), per


KEY_PARAMS = [P("keys", "array", "[[frame, value], ...] or [{frame, value, ease?}]. Values: number, or [x, y] for Point inputs (normalized, Y up)."),
              P("frame", "number", "Single key frame (with value)."), P("value", "any", "Single key value."),
              P("ease", "string|array|object", "Segment ease for touched segments: preset (linear, hold, house, ease, in_out, out_expo, out_back, in, sine_io, cubic_out, quart_out, expo_io, ...), [x1,y1,x2,y2] cubic-bezier, or AE-style {outInfluence,outSpeed,inInfluence,inSpeed}. Default linear."),
              P("loop", "string", "none | loop | loop_rel | pingpong.", enum=("none", "loop", "loop_rel", "pingpong"))]


@op("keyframe.add", "Add/replace keyframes on a Number input (BezierSpline) or Point input (XYPath with keyed X/Y). Merges with existing keys; segments touching new keys get `ease`, others keep theirs. Encodes the stray-seeded-key fix (time moved to the first key before AddModifier, replace twice, exact key-set assert) and relative Python handles.",
    [COMP(), TOOL(), INPUT()] + KEY_PARAMS)
def keyframe_add(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    keys, per = _norm_keys(a)
    _, _, fps = ctx.fmt(comp)
    loop = a.get("loop") if a.get("loop") not in (None, "none") else None
    host = get_spline(ctx, comp, t, a["input"], True, keys[0][0])
    reg = host.GetAttrs()["TOOLS_RegID"]
    if reg == "XYPath":
        for f, v in keys:
            if not (isinstance(v, (list, tuple)) and len(v) >= 2):
                raise OpError("INVALID_ARGS", f"{a['input']} is a Point: key values must be [x, y]")
        sx, sy = _axis_splines(ctx, comp, host, keys[0][0])
        _key_spline(ctx, comp, sx, [(f, float(v[0])) for f, v in keys], a.get("ease"), fps, loop, per)
        _key_spline(ctx, comp, sy, [(f, float(v[1])) for f, v in keys], a.get("ease"), fps, loop, per)
        res = {"path": host.GetAttrs()["TOOLS_Name"], "keys": {"X": spline_keys(sx), "Y": spline_keys(sy)}}
    else:
        for f, v in keys:
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise OpError("INVALID_ARGS", f"{a['input']} is a Number: key values must be numbers")
        _key_spline(ctx, comp, host, keys, a.get("ease"), fps, loop, per)
        res = {"spline": host.GetAttrs()["TOOLS_Name"], "keys": spline_keys(host)}
    mid = (keys[0][0] + keys[-1][0]) / 2 if len(keys) > 1 else keys[0][0]
    res["sample"] = {fkey(keys[0][0]): jv(t.GetInput(a["input"], keys[0][0])), fkey(mid): jv(t.GetInput(a["input"], mid)),
                     fkey(keys[-1][0]): jv(t.GetInput(a["input"], keys[-1][0]))}
    return res


def _splines_of(ctx, comp, t, iid):
    host = get_spline(ctx, comp, t, iid)
    if host is None:
        raise OpError("NOT_FOUND", f"{t.GetAttrs()['TOOLS_Name']}.{iid} is not animated")
    if host.GetAttrs()["TOOLS_RegID"] == "XYPath":
        return host, [s for s in _axis_splines(ctx, comp, host, None, create=False) if s is not None]
    return host, [host]


@op("keyframe.list", "List keyframes on an input (frame, value, handles as returned, flags). Point inputs report X/Y splines of their XYPath.",
    [COMP(), TOOL(), INPUT()], read=True)
def keyframe_list(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host = get_spline(ctx, comp, t, a["input"])
    if host is None:
        return {"animated": False, "keys": []}
    if host.GetAttrs()["TOOLS_RegID"] == "XYPath":
        sx, sy = _axis_splines(ctx, comp, host, None, create=False)
        return {"animated": True, "path": host.GetAttrs()["TOOLS_Name"],
                "keys": {"X": spline_keys(sx) if sx else [], "Y": spline_keys(sy) if sy else []}}
    return {"animated": True, "spline": host.GetAttrs()["TOOLS_Name"], "keys": spline_keys(host), "eases": _meta(host).get("seg")}


def _rewrite(ctx, comp, sp, fn_keys, fn_ease=None, fps=24):
    meta = _meta(sp)
    keys = [(r["frame"], r["value"]) for r in spline_keys(sp)]
    old_seg = {float(k): _decode_ease(v) for k, v in meta.get("seg", {}).items()}
    eases = [old_seg.get(keys[s][0], ("linear",)) for s in range(len(keys) - 1)]
    keys, eases = fn_keys(keys, eases)
    if fn_ease:
        eases = fn_ease(keys, eases)
    write_spline(comp, sp, keys, eases, meta.get("loop"), fps)
    sp.SetData("fc_ease", json.dumps({"seg": {str(keys[s][0]): _encode_ease(eases[s]) for s in range(len(eases))}, "loop": meta.get("loop")}))
    return keys


@op("keyframe.remove", "Remove keys at the given frames (all keys when frames is omitted and all: true). Removing the last key removes the animation and keeps the value at the current frame.",
    [COMP(), TOOL(), INPUT(), P("frames", "array", "Frames to remove."), P("all", "boolean", "Remove every key.")])
def keyframe_remove(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host, sps = _splines_of(ctx, comp, t, a["input"])
    _, _, fps = ctx.fmt(comp)
    frames = {float(f) for f in (a.get("frames") or [])}
    if not frames and not a.get("all"):
        raise OpError("INVALID_ARGS", "pass frames or all: true")
    remaining = None
    for sp in sps:
        def fk(keys, eases):
            keep = [(f, v) for f, v in keys if not a.get("all") and f not in frames]
            idx = {f for f, _ in keep}
            e2 = [eases[s] for s in range(len(keys) - 1) if keys[s][0] in idx][:max(0, len(keep) - 1)]
            e2 += [("linear",)] * (max(0, len(keep) - 1) - len(e2))
            return keep, e2
        cur = [(r["frame"], r["value"]) for r in spline_keys(sp)]
        keep = [k for k in cur if not a.get("all") and k[0] not in frames]
        if not keep:
            remaining = 0
            break
        remaining = len(_rewrite(ctx, comp, sp, fk, fps=fps))
    if remaining == 0:
        return keyframe_clear(ctx, comp, {"tool": a["tool"], "input": a["input"]})
    return keyframe_list(ctx, comp, {"tool": a["tool"], "input": a["input"]})


@op("keyframe.clear", "Remove all animation from an input (spline or XYPath) and keep a static value (value at the current frame, or `value`).",
    [COMP(), TOOL(), INPUT(), P("value", "any", "Static value to keep.")])
def keyframe_clear(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    if get_spline(ctx, comp, t, a["input"]) is None:
        raise OpError("NOT_FOUND", f"{a['tool']}.{a['input']} is not animated")
    r = modifier_remove(ctx, comp, {"tool": a["tool"], "input": a["input"], **({"value": a["value"]} if "value" in a else {})})
    return {"cleared": True, **r}


@op("keyframe.set_easing", "Re-ease segments: every segment (default) or the segments starting at `frames`. ease = preset, [x1,y1,x2,y2] cubic-bezier, AE-style influence/speed object, 'linear' or 'hold'.",
    [COMP(), TOOL(), INPUT(), P("ease", "string|array|object", "Ease spec (see keyframe.add).", required=True),
     P("frames", "array", "Segment start frames (default all).")])
def keyframe_set_easing(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host, sps = _splines_of(ctx, comp, t, a["input"])
    _, _, fps = ctx.fmt(comp)
    only = {float(f) for f in a["frames"]} if a.get("frames") else None
    for sp in sps:
        def fe(keys, eases):
            out = []
            for s in range(len(keys) - 1):
                if only is None or keys[s][0] in only:
                    D, V = keys[s + 1][0] - keys[s][0], keys[s + 1][1] - keys[s][1]
                    out.append(ease_points(a["ease"], D, V, fps))
                else:
                    out.append(eases[s])
            return out
        _rewrite(ctx, comp, sp, lambda k, e: (k, e), fe, fps)
    res = keyframe_list(ctx, comp, {"tool": a["tool"], "input": a["input"]})
    ks = res["keys"] if isinstance(res["keys"], list) else res["keys"]["X"]
    if len(ks) > 1:
        f0, f1 = ks[0]["frame"], ks[1]["frame"]
        res["sample"] = {q: jv(t.GetInput(a["input"], f0 + (f1 - f0) * q)) for q in (0.25, 0.5, 0.75)}
    return res


@op("keyframe.set_value", "Change the value of existing keys without moving them (frames with new values). Segment eases are preserved (handles are recomputed from the stored curve).",
    [COMP(), TOOL(), INPUT(), P("keys", "array", "[[frame, value], ...] for existing frames.", required=True)])
def keyframe_set_value(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host, sps = _splines_of(ctx, comp, t, a["input"])
    _, _, fps = ctx.fmt(comp)
    newv = {float(k[0]): k[1] for k in a["keys"]}
    axes = ["X", "Y"] if len(sps) == 2 else [None]
    for n, sp in enumerate(sps):
        existing = {r["frame"] for r in spline_keys(sp)}
        missing = sorted(set(newv) - existing)
        if missing:
            raise OpError("NOT_FOUND", f"no keys at frames {missing}", hint="keyframe.add creates keys")

        def fk(keys, eases, n=n):
            ks = [(f, (float(newv[f][n]) if axes[0] else newv[f]) if f in newv else v) for f, v in keys]
            return ks, eases
        _rewrite(ctx, comp, sp, fk, fps=fps)
    return keyframe_list(ctx, comp, {"tool": a["tool"], "input": a["input"]})


@op("keyframe.shift", "Retime keys: newFrame = (frame - pivot) * scale + pivot + offset. Eases are kept (handles scale with the segment).",
    [COMP(), TOOL(), INPUT(), P("offset", "number", "Frames to add (default 0)."), P("scale", "number", "Time scale (default 1)."),
     P("pivot", "number", "Scale pivot frame (default first key).")])
def keyframe_shift(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host, sps = _splines_of(ctx, comp, t, a["input"])
    _, _, fps = ctx.fmt(comp)
    off, sc = float(a.get("offset", 0)), float(a.get("scale", 1))
    if sc <= 0:
        raise OpError("INVALID_ARGS", "scale must be > 0")
    for sp in sps:
        keys0 = spline_keys(sp)
        piv = float(a.get("pivot", keys0[0]["frame"] if keys0 else 0))

        def fk(keys, eases):
            return [((f - piv) * sc + piv + off, v) for f, v in keys], eases
        _rewrite(ctx, comp, sp, fk, fps=fps)
    return keyframe_list(ctx, comp, {"tool": a["tool"], "input": a["input"]})


@op("keyframe.set_loop", "Loop the animation after its last key: none | loop (cycle) | loop_rel (cycle with offset) | pingpong (flags on the first key; verified to behave like AE loopOut cycle/offset/pingpong).",
    [COMP(), TOOL(), INPUT(), P("mode", "string", "Loop mode.", required=True, enum=("none", "loop", "loop_rel", "pingpong"))])
def keyframe_set_loop(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host, sps = _splines_of(ctx, comp, t, a["input"])
    _, _, fps = ctx.fmt(comp)
    for sp in sps:
        meta = _meta(sp)
        meta["loop"] = None if a["mode"] == "none" else a["mode"]
        sp.SetData("fc_ease", json.dumps(meta))
        _rewrite(ctx, comp, sp, lambda k, e: (k, e), fps=fps)
    keys = spline_keys(sps[0])
    last = keys[-1]["frame"] if keys else 0
    span = (last - keys[0]["frame"]) if keys else 0
    first_v, mid_after = t.GetInput(a["input"], keys[0]["frame"] + span / 2) if keys else None, t.GetInput(a["input"], last + span / 2)
    check = {"lastKey": jv(t.GetInput(a["input"], last)), "afterLast+half": jv(mid_after), "firstCycle+half": jv(first_v)}
    def _near(x, y):
        x, y = jv(x), jv(y)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return abs(x - y) < 1e-4
        if isinstance(x, dict) and isinstance(y, dict):
            return all(_near(x.get(k), y.get(k)) for k in set(x) | set(y))
        return x == y
    if a["mode"] == "loop" and keys and len(keys) > 2 and not _near(mid_after, first_v):
        raise OpError("OPERATION_FAILED", "loop flags did not make this %d-key spline cycle (value half a cycle after the last key "
                      "does not repeat the first cycle)" % len(keys), details=check,
                      hint="Known Fusion limit (skills-gap pass): loop flags cycle 2-key splines only. Use an expression "
                           "(e.g. a modulo on time) or build the cycle as 2-key segments; see fusion-realities.")
    return {"mode": a["mode"], "check": check}


@op("keyframe.copy", "Copy all keys (with eases) from one input to another (same or different tool), optionally time-offset. Existing target keys are merged.",
    [COMP(), TOOL("Source tool."), INPUT("Source input."), P("targetTool", "string", "Target tool.", required=True),
     P("targetInput", "string", "Target input (default same ID)."), P("timeOffset", "number", "Frames to add (default 0).")])
def keyframe_copy(ctx, comp, a):
    t = ctx.tool(comp, a["tool"])
    host, sps = _splines_of(ctx, comp, t, a["input"])
    tt = ctx.tool(comp, a["targetTool"])
    ti = a.get("targetInput") or a["input"]
    off = float(a.get("timeOffset", 0))
    _, _, fps = ctx.fmt(comp)
    if len(sps) == 2:
        kx, ky = spline_keys(sps[0]), spline_keys(sps[1])
        keys = [[r["frame"] + off, [r["value"], ky[n]["value"]]] for n, r in enumerate(kx)]
        seg = _meta(sps[0]).get("seg", {})
    else:
        keys = [[r["frame"] + off, r["value"]] for r in spline_keys(sps[0])]
        seg = _meta(sps[0]).get("seg", {})
    per = [{"frame": f, "value": v, "ease": seg.get(str(f - off))} for f, v in keys]
    per = [{k: v for k, v in d.items() if v is not None} for d in per]
    for d in per:
        e = d.get("ease")
        if isinstance(e, list) and e and e[0] in ("bezier", "linear", "hold"):
            d["ease"] = e[1:] if e[0] == "bezier" else ("linear" if e[0] == "linear" else "hold")
    return keyframe_add(ctx, comp, {"tool": a["targetTool"], "input": ti, "keys": per, "loop": _meta(sps[0]).get("loop") or "none"})


# ================================================================ controller (one controller across a film's comps)

@op("controller.sync", "Copy a controller tool's control values (default: its UserControls; or `inputs`) from one comp to the tool of the same name in every other comp on a timeline. [rebuild F14] Expressions cannot cross comps, so a film built as one comp per beat carries one CTRL copy per comp; edit one, then sync. Static values only (animated or expression-driven inputs are skipped and reported); every value is set with readback. Each target comp changes separately (no shared undo).",
    [P("timeline", "string", "Timeline whose item comps receive the values (default current)."),
     P("tool", "string", "Controller tool name (default CTRL).", default="CTRL"),
     P("inputs", "array", "Input IDs to copy (default: the tool's UserControls)."),
     P("from", "object", "Source comp ref {timeline?, track?, item?, comp?} (default: the Fusion-page comp)."),
     P("dryRun", "boolean", "Report values and targets without setting anything.")], comp=False)
def controller_sync(ctx, a):
    import uuid
    name = a.get("tool", "CTRL")
    src = ctx.comp(a.get("from"))
    st = ctx.tool(src, name)
    ids = a.get("inputs")
    if not ids:
        uc = jv(st.UserControls) or {}
        ids = sorted(uc) if isinstance(uc, dict) else []
        if not ids:
            raise OpError("INVALID_ARGS", f"{name} has no UserControls; pass inputs: [ids]")
    values, skipped = {}, []
    for iid in ids:
        i = ctx.inp(st, iid)
        if i.GetConnectedOutput() or i.GetExpression():
            skipped.append({"input": iid, "why": "animated or expression-driven in the source"})
            continue
        dt = (i.GetAttrs() or {}).get("INPS_DataType")
        if dt in ("Image", "Mask", "DataType3D", "MtlGraph3D", "Particles", "Gradient"):
            skipped.append({"input": iid, "why": f"{dt} is not copyable"})
            continue
        v = jv(st.GetInput(iid, src.CurrentTime))
        values[iid] = v[:2] if dt == "Point" and isinstance(v, list) else v
    tok = uuid.uuid4().hex
    src.SetData("fc_sync_src", tok)
    tl = ctx.timeline(a.get("timeline"))
    updated, errors = [], []
    try:
        for k in range(1, (tl.GetTrackCount("video") or 0) + 1):
            for j, it in enumerate(tl.GetItemListInTrack("video", k) or []):
                for ci in range(1, (it.GetFusionCompCount() or 0) + 1):
                    c = it.GetFusionCompByIndex(ci)
                    if c is None or c.GetData("fc_sync_src") == tok:
                        continue
                    t = c.FindTool(name)
                    if t is None:
                        continue
                    where = {"track": k, "item": j, "comp": ci, "clip": it.GetName()}
                    if a.get("dryRun"):
                        updated.append(where)
                        continue
                    n, bad = 0, []
                    for iid, v in values.items():
                        try:
                            ctx.set_input(c, t, iid, v)
                            n += 1
                        except OpError as e:
                            bad.append({"input": iid, "error": e.message})
                    updated.append(dict(where, set=n))
                    if bad:
                        errors.append(dict(where, failed=bad))
    finally:
        src.SetData("fc_sync_src", "")
    out = {"tool": name, "values": values, "targets": updated, "skipped": skipped}
    if errors:
        out["errors"] = errors
    if not updated:
        out["note"] = f"no other comp on '{tl.GetName()}' has a tool named {name}"
    return out
