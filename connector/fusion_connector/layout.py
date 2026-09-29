"""House graph style for Fusion node graphs (pure: no Resolve). A wired graph in, tool positions and labeled underlays out.

The style (grid units: 1 column = 110 flow px, 1 row = 33 flow px; ViewInfo Pos = grid * (110, 33); FlowView GetPos/SetPos
and AddTool x/y take grid units):
- The compositing pipe (the Merge Background chain, the film ladder) is a straight horizontal SPINE, flowing left to right like
  Resolve's default build direction and MediaIn -> MediaOut; it suits the wide, short node panel of the Fusion page.
- Each input that is not the main input (a Merge Foreground, a Merge3D scene input) hangs ABOVE its consumer as a tidy tree:
  its main chain is a straight vertical column flowing down into the consumer, its own side inputs sit to the LEFT, its masks
  to the RIGHT. Masks of spine tools hang BELOW the spine and flow up. A branch whose main chain composites again (two or more
  merges: a whole scene feeding the film ladder, a group's sub-stack) is laid out as its own horizontal band.
- Controllers, unwired tools, notes and shared assets (a tool feeding two or more layer groups) sit in the top-left corner of
  their band; modifiers are never placed (they have no node).
- Underlays (UI only, no render cost) box each scene/film ladder, each layer group, the controls and the shared assets,
  named <label>_<KIND> and coloured by kind. Tree edges never cross by construction; the only crossings left are wires from a
  shared source to its other consumers (counted by metrics()). No PipeRouters are inserted: a router edits the wiring."""
import collections
import math
import re

COL, ROW = 110.0, 33.0            # flow px per grid column / row
H = 0.5                           # half a grid cell; a tile is one cell wide, its name bar sits in its cell
TB = 1.8                          # rows a tile reaches below its center: with node thumbnails on (the Fusion page default) the
                                  # thumbnail hangs under the name bar, about 2.3 rows tall in all (live, 21.1); without, 1 row
SPINE = 1.5                       # min columns between spine tools
VGAP, VGAP_BOX = 0.7, 2.7         # clear rows under a tile before the next (a 3-row chain pitch); boxed band: room for pads
GAP, GAP_BOX = 0.5, 1.5           # columns between sibling blocks (boxed band involved)
# Underlay padding. Fusion snaps SetPos to a lattice (x: half columns, y: whole rows; measured live), so every tile corner and
# every underlay's left/top edge sits on it: a layer box hugs its tiles' cells (the tile is drawn narrower than its cell) with
# half a row above (title) and below; a scene box adds half a column each side, a row on top (its own title) and half a row
# below.
PAD = {"layer": (0.0, 0.5, 0.0, 0.3), "band": (0.5, 1.0, 0.5, 0.5)}   # left, top, right, bottom (bottom: past the thumbnail)
ISLAND_GAP = 5.7                  # rows between top-level bands (disconnected branches below the main one); keeps rows whole
STAIR = 2.0                       # rows between the steps of a stepped fan (a tool with 3+ side inputs): more than a tile's depth

MASK_IN = {"EffectMask", "GarbageMatte", "SolidMatte"}
MAIN_IN = ("Background", "Input", "SceneInput", "SceneInput1", "Input1", "Input0", "MaterialInput", "Image", "Source")
MASK_REGS = {"BitmapMask", "BSplineMask", "EllipseMask", "PaintMask", "PolylineMask", "RangesMask", "RectangleMask", "TriangleMask",
             "WandMask", "MagicMask", "VolumeMask"}
KINDS = {  # kind -> (underlay name suffix, TileColor)
    "scene": ("SCENE", (0.24, 0.27, 0.34)), "film": ("LADDER", (0.45, 0.24, 0.22)), "controller": ("CONTROLS", (0.62, 0.47, 0.14)),
    "shared": ("SHARED", (0.38, 0.38, 0.42)), "text": ("TEXT", (0.46, 0.31, 0.60)), "ui": ("UI", (0.17, 0.45, 0.47)),
    "3d": ("3D", (0.20, 0.35, 0.64)), "cache": ("CACHE", (0.24, 0.52, 0.28)), "branch": ("BRANCH", (0.33, 0.33, 0.33))}
TAG = "fcLayout"                  # CustomData key marking the underlays this module made (refreshed, never a user's)


def _nat(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def kind_of(names, regs):
    """Layer-group kind from its tools: cache > 3d > text (Text+ are at least half its generators) > ui."""
    rs = [regs[n] for n in names]
    if any(r == "Loader" and n.endswith("_Cache") for n, r in zip(names, rs)):
        return "cache"
    if any(r.endswith("3D") or r.startswith("Light") for r in rs):
        return "3d"
    txt = sum(r in ("TextPlus", "Text3D") for r in rs)
    gen = sum(r in ("Background", "sRender", "Loader", "MediaIn", "FastNoise", "Plasma") for r in rs)
    return "text" if txt and txt >= gen else "ui"


def is_controller(name, reg):
    return reg == "Custom" or bool(re.search(r"(^|_)(CTRL|Controls?|Controller)(_?\d+)?$", name))


def _corner_kind(net, n):
    """0 = an unwired controller or note (the controls box), 1 = a shared asset (it has consumers), 2 = other unwired tools."""
    if net.cons.get(n):
        return 1
    return 0 if is_controller(n, net.reg[n]) or net.reg[n] == "Note" else 2


class Net:
    """The wired graph of placeable tools: reg IDs, inputs in input order [(input, source)], old positions (grid units)."""

    def __init__(self, scenes=()):
        self.reg, self.ins, self.old, self.cons = {}, {}, {}, collections.defaultdict(list)
        self.scenes = sorted(set(scenes), key=lambda s: (-len(s), s))
        self.underlays = {}       # existing Underlay tools: name -> TAG value ('' = a user's)

    def add(self, name, reg, pos=None):
        self.reg[name] = reg
        self.ins.setdefault(name, [])
        if pos is not None:
            self.old[name] = (float(pos[0]), float(pos[1]))

    def edge(self, src, dst, iid):
        if src in self.reg and dst in self.reg and src != dst:
            self.ins[dst].append((iid, src))
            self.cons[src].append((dst, iid))

    def prefix(self, n):
        for s in self.scenes:
            if n.startswith(s + "_"):
                return s
        return n.split("_", 1)[0] if "_" in n else None

    def sub(self, names):
        out = Net(self.scenes)
        for n in self.reg:
            if n in names:
                out.add(n, self.reg[n], self.old.get(n))
        for n in out.reg:
            for iid, s in self.ins[n]:
                out.edge(s, n, iid)
        return out


def parse_dump(text, mods=()):
    """READ_LUA output -> Net. Tools inside groups are skipped (their group is the node); wires from inside a group map to it.
    A group's wires into its own children are dropped."""
    tools, edges, parent, underlays = {}, [], {}, {}
    for line in text.splitlines():
        c = line.split("\t")
        if c[0] == "T" and len(c) >= 6:
            n, r, p = c[1], c[2], c[3]
            if r in mods:
                continue
            if r == "Underlay":
                underlays[n] = c[6] if len(c) > 6 else ""
                continue
            parent[n] = p
            try:
                pos = (float(c[4]) + H, float(c[5]) + H)   # GetPos = cell top-left (grid); the plan works in tile centers
            except ValueError:
                pos = None
            tools[n] = (r, pos, len(c) > 7 and c[7] == "1")
        elif c[0] == "E" and len(c) >= 4:
            edges.append((c[3], c[1], c[2]))

    def top(n):
        seen = set()
        while parent.get(n) and n not in seen:
            seen.add(n)
            n = parent[n]
        return n
    scenes = [n[:-4] for n, v in tools.items() if v[2]]
    net = Net(scenes)
    for n, (r, pos, _) in tools.items():
        if not parent.get(n):
            net.add(n, r, pos)
    for s, d, iid in sorted(edges, key=lambda e: (e[1], _nat(e[2]), e[0])):   # dump order varies; input order = natural
        if parent.get(d):  # wiring inside a group
            continue
        net.edge(top(s), d, iid)
    net.underlays = underlays
    return net


class Blk:
    """A placed block: anchor tool n at (0, 0), kids [(Blk, dx, dy)], bounding box l, r, t, b relative to the anchor."""
    __slots__ = ("n", "kids", "l", "r", "t", "b", "band", "boxed", "prefix", "rec")

    def __init__(self, n):
        self.n, self.kids = n, []
        self.l, self.r, self.t, self.b = -H, H, -H, TB
        self.band = self.boxed = False
        self.prefix = self.rec = None

    def put(self, k, dx, dy):
        self.kids.append((k, dx, dy))
        self.l, self.r = min(self.l, dx + k.l), max(self.r, dx + k.r)
        self.t, self.b = min(self.t, dy + k.t), max(self.b, dy + k.b)


def _walk(B, x, y, out):
    stack = [(B, x, y)]
    while stack:
        b, bx, by = stack.pop()
        if b.n is not None:
            out[b.n] = (bx, by)
        for k, dx, dy in b.kids:
            stack.append((k, bx + dx, by + dy))


def _nodes(B):
    out = {}
    _walk(B, 0.0, 0.0, out)
    return out


class _Engine:
    def __init__(self, net, corner=None, reserved=()):
        self.net = net
        self.claim = set()
        self.reserved = set(reserved)        # corner tools: only a band corner may place them
        self.corner = corner or {}           # band prefix (None = main band) -> [corner tool names]
        self.bands = []                      # band records
        self.group_of = {}                   # tool -> its layer group (spine tool), for shared-asset detection
        self.tree_edges = set()              # (source, consumer) wires drawn as tree/spine links
        self._split, self._merges = {}, {}
        cnt = collections.Counter(net.prefix(n) for n in net.reg)
        self.scenes = set(net.scenes) | {p for p, k in cnt.items() if p and k >= 5}   # scene-like prefixes (S5_*)

    # -- inputs
    def split(self, n):
        """(main source, [side sources], [mask sources]) in input order, static (claims ignored)."""
        if n in self._split:
            return self._split[n]
        ins = self.net.ins[n]
        conn = {}
        for iid, s in ins:
            conn.setdefault(iid, s)
        if self.net.reg[n] in MASK_REGS:
            main = "EffectMask" if "EffectMask" in conn else None
        else:
            main = next((i for i in MAIN_IN if i in conn), None)
        if main is None:   # no known main input: the first image input in natural order (independent of dump order)
            main = min((i for i in conn if i not in MASK_IN), key=_nat, default=None)
        sides = sorted((i for i in conn if i != main and i not in MASK_IN), key=_nat)
        masks = sorted((i for i in conn if i != main and i in MASK_IN), key=_nat)
        seen = {conn[main]} if main else set()   # a tool wired into two inputs of one consumer is placed once
        sides = [conn[i] for i in sides if conn[i] not in seen and not seen.add(conn[i])]
        masks = [conn[i] for i in masks if conn[i] not in seen and not seen.add(conn[i])]
        r = (conn[main] if main else None, sides, masks)
        self._split[n] = r
        return r

    def merges(self, n):
        """Tools with a side input along n's main chain (memoized, iterative)."""
        chain, cur, seen = [], n, set()
        while cur is not None and cur not in self._merges and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = self.split(cur)[0]
        acc = self._merges.get(cur, 0) if cur is not None else 0
        for c in reversed(chain):
            acc += 1 if self.split(c)[1] else 0
            self._merges[c] = acc
        return self._merges[n]

    def take(self, xs, force=False):
        out = []
        for x in xs:
            if x is not None and x not in self.claim and (force or x not in self.reserved):
                self.claim.add(x)
                out.append(x)
        return out

    # -- blocks
    def is_band(self, n, consumer):
        pn = self.net.prefix(n)
        return self.merges(n) >= 2 or (pn in self.scenes and pn != self.net.prefix(consumer))  # a pipe, or another scene

    def block(self, n, sgn, consumer, boxable=False):
        """boxable: a direct side input of a band's spine; only such a band (another scene) gets its own backdrop. Deeper ones
        stay inside the backdrop of the layer that holds them, so backdrops nest at most scene > layer."""
        if self.is_band(n, consumer):
            B = self.band(n)
            B.boxed = boxable and B.prefix is not None and B.prefix != self.net.prefix(consumer)
            self.bands[B.rec]["boxed"] = B.boxed
            return B
        return self.tree(n, sgn)

    @staticmethod
    def vstep(C, sgn):
        g = VGAP_BOX if C.boxed else VGAP
        return -H - g - C.b if sgn < 0 else TB + g - C.t

    def tree(self, n, sgn):
        """n at (0, 0); main chain straight (above for sgn -1, below for +1); side inputs to the left, masks to the right.
        The main chain is walked iteratively (claims top-down, blocks built from its far end back), so chain length never
        meets Python's recursion limit; only nesting of side branches recurses."""
        chain, cur = [], n
        while True:
            m, sides, masks = self.split(cur)
            got = set(self.take([m] + sides + masks))
            self.tree_edges.update((c, cur) for c in got)
            m = m if m in got else None
            sides = [x for x in sides if x in got]
            masks = [x for x in masks if x in got]
            if m is None and sides:
                m, sides = sides[0], sides[1:]
            chain.append((cur, m, sides, masks))
            if m is None or self.is_band(m, cur):
                break
            cur = m
        up = None
        for cur, m, sides, masks in reversed(chain):
            B = Blk(cur)
            # a fan of 3+ side inputs is stepped: the farther a side input, the closer its block sits to cur, so every wire
            # passes under the nearer blocks instead of through them (no crossings, no wire over a tool)
            k = len(sides)
            step = STAIR if k >= 3 else 0.0
            lo, hi = -H, H
            if m is not None:
                M = up if up is not None else self.block(m, sgn, cur)
                B.put(M, 0.0, self.vstep(M, sgn) + sgn * step * k)
                lo, hi = M.l, M.r
            for j, x in enumerate(sides):
                S = self.block(x, sgn, cur)
                dx = lo - (GAP_BOX if S.boxed else GAP) - S.r
                B.put(S, dx, self.vstep(S, sgn) + sgn * step * (k - 1 - j))
                lo = dx + S.l
            for x in masks:
                K = self.block(x, sgn, cur)
                dx = hi + (GAP_BOX if K.boxed else GAP) - K.l
                B.put(K, dx, self.vstep(K, sgn))
                hi = dx + K.r
            up = B
        return up

    def band(self, root, top=False):
        """Horizontal spine from root upstream (root at the right end, anchor (0, 0)); each spine tool's side inputs above it,
        masks below it; the band's corner tools above its first spine tool, further left."""
        spine, cur = [root], root
        self.claim.add(root)
        while True:
            m = self.split(cur)[0]
            if m is None or m in self.claim or m in self.reserved:
                break
            self.claim.add(m)
            self.tree_edges.add((m, cur))
            spine.append(m)
            cur = m
        spine.reverse()
        cnt = collections.Counter(self.net.prefix(s) for s in spine)
        pfx, k = cnt.most_common(1)[0]
        pfx = pfx if pfx and k >= 2 and k >= 0.5 * len(spine) else None
        rec = {"root": root, "spine": spine, "prefix": pfx, "top": top, "boxed": False, "own": set(spine),
               "corner": [], "groups": [], "children": []}
        self.bands.append(rec)
        ri = len(self.bands) - 1
        clusters, x, prev_r, prev_box = [], 0.0, None, False
        for i, s in enumerate(spine):
            C = Blk(s)
            _, sides, masks = self.split(s)
            got = set(self.take(sides + masks))
            above = [self.block(c, -1, s, True) for c in sides if c in got]
            below = [self.block(c, 1, s, True) for c in masks if c in got]
            self.tree_edges.update((c, s) for c in got)
            corner = []
            if i == 0:
                want = list(self.corner.get(pfx, [])) if pfx else []
                if top:
                    want = want + [n for n in self.corner.get(None, []) if n not in want]
                # nearest the spine: controllers and notes, then shared assets, then other unwired tools (each kind contiguous,
                # so its underlay holds only its own tools)
                want.sort(key=lambda n: (_corner_kind(self.net, n), self.net.prefix(n) != pfx, _nat(n)))
                for c in self.take(want, force=True):
                    T = self.tree(c, -1)
                    corner.append(T)
                    rec["corner"].append((c, set(_nodes(T))))
            hi = H
            for j, K in enumerate(below):
                dx = 0.0 if j == 0 else hi + GAP - K.l
                C.put(K, dx, self.vstep(K, 1))
                hi = max(hi, dx + K.r)
            lo = -H
            for j, A in enumerate(above):             # the first side input straight above s, the others to its left
                dx = 0.0 if j == 0 else lo - (GAP_BOX if A.boxed else GAP) - A.r
                C.put(A, dx, self.vstep(A, -1))
                lo = min(lo, dx + A.l)
            lo = min(lo, C.l)
            for A in corner:                          # corner tools left of everything s owns (its underlay stays clear)
                dx = lo - GAP - A.r
                C.put(A, dx, self.vstep(A, -1))
                lo = dx + A.l
            boxed = any(A.boxed for A in above + below)
            if prev_r is not None:
                x = max(x + SPINE, x + prev_r + (GAP_BOX if (boxed or prev_box) else GAP) - C.l)
            clusters.append((C, x))
            prev_r, prev_box = C.r, boxed
            grp = [s]
            for A in above + below:
                if A.boxed:
                    rec["children"].append(A.rec)
                else:
                    grp += list(_nodes(A))
            rec["own"].update(grp)
            if len(grp) > 1 and not boxed:   # beside another scene's backdrop a layer box would reach under it
                rec["groups"].append((s, grp))
                for n in grp:
                    self.group_of[n] = s
        for _, ns in rec["corner"]:
            rec["own"].update(ns)
        B = Blk(root)
        B.band, B.prefix, B.rec = True, pfx, ri
        x_end = clusters[-1][1]
        for C, cx in clusters:
            B.put(C, cx - x_end, 0.0)
        return B


def _spine_ok(pos, spine):
    ys = {round(pos[s][1], 6) for s in spine}
    xs = [pos[s][0] for s in spine]
    return len(ys) == 1 and all(b > a for a, b in zip(xs, xs[1:]))


def plan(net, top_left=(0.0, 0.0), taken=()):
    """-> {pos: {tool: [x, y]} (tile centers, grid units), boxes: [{name, kind, rect: [x0, y0, x1, y1], members, parent}],
    bands: [{root, spine, prefix}], corner, shared, cross (wires drawn as long wires, not tree links)}. Deterministic: tools
    are visited in sorted order and inputs in input order, never in the order a dump listed the tools."""
    names = sorted(net.reg)
    loose = [n for n in names if not net.ins[n] and not net.cons.get(n)]
    eng = _Engine(net)                                   # pass 1: bands and layer groups
    _run(eng, net, names)
    band_pfx = {b["prefix"] for b in eng.bands if b["prefix"]}
    spine_tools = {s for b in eng.bands for s in b["spine"]}
    shared = []
    for n in names:
        if n in spine_tools or n in loose:
            continue
        keys = {eng.group_of.get(d) for d, _ in net.cons.get(n, [])}
        if len(keys) >= 2 and None not in keys:
            shared.append(n)
    corner = collections.defaultdict(list)             # pass 2: corner tools to the band of their prefix, else the main band
    for n in loose + shared:
        p = net.prefix(n)
        corner[p if p in band_pfx else None].append(n)
    eng = _Engine(net, corner=dict(corner), reserved=set(loose) | set(shared))
    tops = _run(eng, net, names)
    pos = {}
    y = top_left[1]
    for B in tops:
        _walk(B, top_left[0] - B.l, y - B.t, pos)
        y += (B.b - B.t) + ISLAND_GAP
    x = top_left[0] + H
    for n in names:                                      # corner tools of a comp with no wired graph at all: one row
        if n not in pos:
            pos[n] = (x, y + H)
            x += 1 + GAP
    pos = {n: [round(p[0], 4), round(p[1], 4)] for n, p in pos.items()}
    cross = [[s, d, i] for d in names for i, s in net.ins[d] if (s, d) not in eng.tree_edges]
    return {"pos": pos, "boxes": _boxes(eng, net, pos, set(shared), taken),
            "bands": [{"root": b["root"], "spine": b["spine"], "prefix": b["prefix"]} for b in eng.bands],
            "corner": {str(k): v for k, v in corner.items()}, "shared": shared, "cross": cross}


def _run(eng, net, names):
    """Main band from the main root (MediaOut first, else the sink with the most upstream tools), then islands (wired parts
    not upstream of it) as bands below it."""
    def upstream(n):
        seen, st = {n}, [n]
        while st:
            c = st.pop()
            for _, s in net.ins[c]:
                if s not in seen:
                    seen.add(s)
                    st.append(s)
        return len(seen)
    wired = [n for n in names if net.ins[n] or net.cons.get(n)]
    sinks = [n for n in wired if not net.cons.get(n)]
    tops = []
    if sinks or wired:
        main = min(sinks, key=lambda n: (net.reg[n] != "MediaOut", -upstream(n), _nat(n))) if sinks else wired[0]
        tops.append(eng.band(main, top=True))
    while True:
        rest = [n for n in wired if n not in eng.claim]
        if not rest:
            break
        cand = [n for n in rest if all(d in eng.claim for d, _ in net.cons.get(n, []))] or rest
        pick = min(cand, key=lambda n: (-upstream(n), _nat(n)))
        tops.append(eng.band(pick, top=True))
        eng.bands[-1]["island"] = True
    if not tops and any(eng.corner.values()):            # nothing wired: the corner tools in one row
        B, x = Blk(None), 0.0
        for n in eng.take([n for v in eng.corner.values() for n in v], force=True):
            B.put(eng.tree(n, -1), x, 0.0)
            x += 1 + GAP
        tops.append(B)
    return tops


def _label(s):
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    return s if re.match(r"[A-Za-z_]", s) else "U_" + s


def _rect(pos, members, inner=(), level="layer"):
    """Box around member tiles (and inner boxes). A band box sits a further pad outside its inner boxes; around bare tiles
    it takes the inner pads plus its own, so its edge is the same whether a tile is boxed inside it or not."""
    l, t, r, b = PAD[level]
    if level == "band":
        il, it, ir, ib = PAD["layer"]
        l, t, r, b = l + il, t + it, r + ir, b + ib
    bl, bt, br, bb = PAD["band"] if level == "band" else (0, 0, 0, 0)
    x0 = min([pos[n][0] - H - l for n in members] + [q[0] - bl for q in inner])
    y0 = min([pos[n][1] - H - t for n in members] + [q[1] - bt for q in inner])
    x1 = max([pos[n][0] + H + r for n in members] + [q[2] + br for q in inner])
    y1 = max([pos[n][1] + TB + b for n in members] + [q[3] + bb for q in inner])
    return [round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4)]


def _boxes(eng, net, pos, shared, taken=()):
    """Per boxed band (the main band, islands, and bands of another scene fed straight into a spine): one box per layer group,
    the controls, the shared assets, then the band's own box (scene / film ladder / branch / cache) around them and around
    the boxes of the scene bands it feeds from. Inner boxes come first: Fusion draws the first-created underlay on top."""
    taken = set(net.reg) | set(taken)
    made = {}

    def mk(label, kind, members, inner=()):
        base = _label("%s_%s" % (label, KINDS[kind][0]))
        name, i = base, 2
        while name in taken:
            name, i = "%s_%d" % (base, i), i + 1
        taken.add(name)
        level = "band" if kind in ("scene", "branch", "cache") else "layer"
        return {"name": name, "kind": kind, "rect": _rect(pos, members, [b["rect"] for b in inner], level),
                "members": sorted(members, key=_nat), "parent": None}
    for ri in range(len(eng.bands) - 1, -1, -1):       # children (created later) before their parent
        rec = eng.bands[ri]
        if not (rec["top"] or rec["boxed"]):
            continue
        pfx, lab = rec["prefix"], rec["prefix"] or rec["root"]
        inner = [mk(s, kind_of(g, net.reg), g) for s, g in rec["groups"]]
        ctl = [n for c, ns in rec["corner"] if _corner_kind(net, c) == 0 for n in ns]
        shr = [n for c, ns in rec["corner"] if _corner_kind(net, c) == 1 for n in ns]
        if ctl:
            inner.append(mk(lab, "controller", ctl))
        if shr:
            inner.append(mk(lab, "shared", shr))
        kids = [b for ci in rec["children"] for b in made.get(ci, []) if b["parent"] is None]
        box = None
        if pfx or rec.get("island"):
            kind = "film" if pfx == "FILM" else "scene" if pfx else "branch"
            if kind == "branch" and net.reg.get(rec["root"] + "_Cache") == "Loader":
                kind = "cache"
            mem = [n for n in rec["own"] if n in pos and (not pfx or net.prefix(n) == pfx)]
            if mem:
                wrap = inner + ([] if kind == "film" else kids)   # the film ladder box is the ladder row only
                box = mk(lab, kind, mem, wrap)
                for b in wrap:
                    b["parent"] = box["name"]
        # Fusion draws the underlay created FIRST on top (live, 21.1): inner boxes before the box around them
        made[ri] = inner + [b for ci in rec["children"] for b in made.get(ci, [])] + ([box] if box else [])
    out = []
    for ri in sorted(made):
        if eng.bands[ri]["top"]:
            out += made[ri]
    return out


# ---------------------------------------------------------------- checks

def _seg_x(a, b, c, d):
    """Proper intersection of segments ab and cd (shared endpoints and touching do not count)."""
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    if a in (c, d) or b in (c, d):
        return False
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return o1 * o2 < 0 and o3 * o4 < 0


def metrics(p, net):
    """overlaps (tile pairs sharing space), crossings (wire pairs, straight wires), wiresOverTools (a wire through a tool it does
    not connect), spinesStraight, boxes (members inside, nested inside their parent, siblings apart), bbox (grid units)."""
    pos = {n: tuple(v) for n, v in p["pos"].items()}
    cells = collections.defaultdict(list)
    for n, (x, y) in pos.items():
        cells[(math.floor(x), math.floor(y))].append(n)
    overlaps = 0
    for (cx, cy), ns in cells.items():   # a tile covers x +- 0.5 and y - 0.5 .. y + TB (thumbnail included)
        near = [m for dx in (-1, 0, 1) for dy in range(-3, 4) for m in cells.get((cx + dx, cy + dy), ())]
        for n in ns:
            x, y = pos[n]
            for m in near:
                if m > n and abs(pos[m][0] - x) < 1 - 1e-6 and abs(pos[m][1] - y) < H + TB - 1e-6:
                    overlaps += 1
    segs = sorted(((pos[s], pos[d], s, d) for d in net.reg for _, s in net.ins[d] if s in pos and d in pos),
                  key=lambda t: min(t[0][0], t[1][0]))
    crossings, active = 0, []
    for a, b, s, d in segs:
        x0 = min(a[0], b[0])
        active = [t for t in active if max(t[0][0], t[1][0]) >= x0]
        for c, e, _, _ in active:
            if max(min(a[1], b[1]), min(c[1], e[1])) <= min(max(a[1], b[1]), max(c[1], e[1])) and _seg_x(a, b, c, e):
                crossings += 1
        active.append((a, b, s, d))
    over = set()
    for a, b, s, d in segs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        steps = max(1, int(L / 0.2))
        for i in range(1, steps):
            x, y = a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps
            fx, fy = math.floor(x), math.floor(y)
            for m in (m for dx in (-1, 0, 1) for dy in range(-3, 2) for m in cells.get((fx + dx, fy + dy), ())):
                if m not in (s, d) and abs(pos[m][0] - x) < 0.45 and -0.4 < y - pos[m][1] < TB - 0.1:
                    over.add((s, d, m))
    spines = [b["spine"] for b in p["bands"] if len(b["spine"]) > 1]
    rects = {b["name"]: b["rect"] for b in p["boxes"]}
    bad = []
    for b in p["boxes"]:
        x0, y0, x1, y1 = b["rect"]
        for n in b["members"]:
            x, y = pos[n]
            if not (x0 <= x - H and x + H <= x1 and y0 <= y - H and y + TB <= y1):
                bad.append([b["name"], n, "outside"])
        if b["parent"]:
            px0, py0, px1, py1 = rects[b["parent"]]
            if not (px0 <= x0 and x1 <= px1 and py0 <= y0 and y1 <= py1):
                bad.append([b["name"], b["parent"], "not inside parent"])
    sib = collections.defaultdict(list)
    for b in p["boxes"]:
        sib[b["parent"]].append(b["rect"])
    for rs in sib.values():
        for i, r in enumerate(rs):
            for q in rs[i + 1:]:
                if r[0] < q[2] and q[0] < r[2] and r[1] < q[3] and q[1] < r[3]:
                    bad.append([r, q, "siblings overlap"])
    xs = [v[0] for v in pos.values()] or [0]
    ys = [v[1] for v in pos.values()] or [0]
    off = [r[0] for r in set_pos(p) if abs(r[1] * 2 - round(r[1] * 2)) > 1e-6 or abs(r[2] - round(r[2])) > 1e-6]
    return {"tools": len(pos), "wires": len(segs), "overlaps": overlaps, "crossings": crossings, "wiresOverTools": len(over),
            "offLattice": len(off),
            "crossWires": len(p["cross"]), "spines": len(spines), "spinesStraight": all(_spine_ok(pos, s) for s in spines),
            "boxes": len(p["boxes"]), "boxProblems": bad[:20], "bbox": [min(xs) - H, min(ys) - H, max(xs) + H, max(ys) + TB]}


# ---------------------------------------------------------------- emit / apply

def _num(v):
    s = ("%.3f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def underlay_lines(b, indent="\t\t"):
    """One Underlay tool in .setting syntax. UnderlayInfo Pos is (horizontal center, TOP edge) in flow px, Size in flow px."""
    x0, y0, x1, y1 = b["rect"]
    r, g, bl = KINDS[b["kind"]][1]
    return [indent + "%s = Underlay {" % b["name"],
            indent + "\tNameSet = true,",
            indent + "\tViewInfo = UnderlayInfo { Pos = { %s, %s }, Size = { %s, %s } }," % (
                _num((x0 + x1) / 2 * COL), _num(y0 * ROW), _num((x1 - x0) * COL), _num((y1 - y0) * ROW)),
            indent + "\tColors = { TileColor = { R = %s, G = %s, B = %s } }," % (_num(r), _num(g), _num(bl)),
            indent + '\tCustomData = { %s = "%s" },' % (TAG, b["kind"]),
            indent + "},"]


def underlay_setting(boxes):
    lines = ["{", "\tTools = ordered() {"]
    for b in boxes:
        lines += underlay_lines(b)
    return "\n".join(lines + ["\t},", "}", ""])


def set_pos(p):
    """FlowView SetPos arguments, measured live (Resolve 21.1): SetPos(x, y) puts a tool's cell top-left at (x, y) grid, so its
    ViewInfo Pos (the tile center) = (x + 0.5, y + 0.5) cells; for an Underlay it puts the LEFT edge at x and the top edge at
    y + 0.5 rows (ViewInfo Pos = horizontal center, top edge). -> [(name, x, y)] for tools, then underlays."""
    rows = [(n, x - H, y - H) for n, (x, y) in sorted(p["pos"].items())]
    return rows + [(b["name"], b["rect"][0], b["rect"][1] - H) for b in p["boxes"]]


def translate(p, dx, dy):
    p["pos"] = {n: [round(x + dx, 4), round(y + dy, 4)] for n, (x, y) in p["pos"].items()}
    for b in p["boxes"]:
        x0, y0, x1, y1 = b["rect"]
        b["rect"] = [round(x0 + dx, 4), round(y0 + dy, 4), round(x1 + dx, 4), round(y1 + dy, 4)]
    return p


def preview(p, net, path, width=1600):
    """PNG of the planned graph: underlays (kind colours, names), wires (red: not a tree edge), tools (name, regId)."""
    from PIL import Image, ImageDraw
    pos = p["pos"]
    xs = [v[0] for v in pos.values()] + [b["rect"][0] for b in p["boxes"]] + [b["rect"][2] for b in p["boxes"]]
    ys = [v[1] for v in pos.values()] + [b["rect"][1] for b in p["boxes"]] + [b["rect"][3] for b in p["boxes"]]
    if not xs:
        xs, ys = [0, 1], [0, 1]
    x0, y0, x1, y1 = min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1
    sx = min(width / ((x1 - x0) * COL), 1.0)
    W, Hh = max(64, int((x1 - x0) * COL * sx)), max(64, int((y1 - y0) * ROW * sx))
    im = Image.new("RGB", (W, Hh), (40, 40, 43))
    d = ImageDraw.Draw(im, "RGBA")

    def P(x, y):
        return ((x - x0) * COL * sx, (y - y0) * ROW * sx)
    for b in p["boxes"]:
        c = tuple(int(v * 255) for v in KINDS[b["kind"]][1])
        a, bb = P(b["rect"][0], b["rect"][1]), P(b["rect"][2], b["rect"][3])
        d.rectangle([a, bb], fill=c + (110,), outline=c + (255,))
        if sx * COL > 25:
            d.text((a[0] + 3, a[1] + 2), b["name"], fill=(235, 235, 235))
    cross = {(s, dd) for s, dd, _ in p["cross"]}
    for dst in net.reg:
        for _, s in net.ins[dst]:
            if s in pos and dst in pos:
                d.line([P(*pos[s]), P(*pos[dst])], fill=(230, 80, 70) if (s, dst) in cross else (170, 170, 170), width=1)
    for n, (x, y) in pos.items():
        a, bb = P(x - 0.45, y - 0.4), P(x + 0.45, y + TB - 0.1)
        d.rectangle([a, bb], fill=(78, 78, 84), outline=(20, 20, 20))
        if sx * COL > 40:
            d.text((a[0] + 2, a[1] + 1), n[-int(18 * sx * COL / 110):] if len(n) > 18 else n, fill=(240, 240, 240))
    im.save(path)
    return path
