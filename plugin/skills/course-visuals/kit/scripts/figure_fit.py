#!/usr/bin/env python3
"""figure_fit.py - every kit figure of a module checked at once on its real slide, and the deterministic fixes made by
themselves, each proven by the same check (2.50.0).

  figure_fit.py <course> --module 1 [--no-fix] [--json]

WHY (IGF M01 benchmark, 2026-10-19): a module build spent most of its turns on figures found one compile at a time -
37, then 2, then 1 drawing problems; s02 took 11 spec edits; one layout change (s05 two-col -> wide-left) cost 16 spec
edits and 3 failed compiles, where the hand-built copy needed one class change. This does in one run what those
turns did:

  1  CHECK   every kit figure the build sheet puts on a slide, all at once, each on its real slide at 1280 x 800, every
             step, every drawing audit (studio.py) - plus check_kit.py's spec checks. Findings are grouped per figure
             and part, never one line per step.
  2  FIX     only what has one right answer, never by loosening a limit, and each fix is drawn and audited again:
             EMPTY    the drawing cropped to what it shows at its busiest step, in the column's shape (a window on the
                      same canvas - the parts stay where they are)
             COLUMN   a figure drawn below 0.8:1 in its column (a layout changed and the column got narrower) re-fitted
                      to it: its positions and stretchable lengths (pipes, rooms, bars) squeezed to the column, then
                      repaired part by part - a part past its room's edge moved into free room or drawn narrower (never
                      under 70 %), a part on another moved beside it, a heading too wide broken onto two lines (the
                      same words). Nothing is wrapped downwards: a column is height-bound as often as width-bound
                      (IGF M01 s05: wrapping made the drawing taller and every word smaller). Tried at four widths at
                      once; one that audits clean at every step is kept.
             A fix is written to figures\\MNN\\_fit\\<slide>.<spec> with the spec's hash and the slide's layout: the
             compiler draws it only while both are unchanged. The spec itself is never rewritten. A figure no fix makes
             clean is reported as it is, with what to do - and the closest attempt is saved beside it
             (<slide>.<spec>.candidate.kit.json) to copy over the spec and finish, instead of redrawing.
  3  SAY     one block per figure that still has a problem: the slide, the part, the check, the steps, a concrete fix.

Exit 0 every figure clean (fixed ones included), 1 problems left, 2 could not run.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import copy
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio  # noqa: E402
import check_kit  # noqa: E402

sys.path.insert(0, studio.COMPILE)
sys.path.insert(0, studio.FACTORY_SCRIPTS)

GATE = "1280x800"
SMALL_AT = "1024x768"
CONTAINERS = ("space", "panel", "ga")
# widths that stretch with the drawing (a room, a pipe run, a bar); every other part keeps its size and only moves
STRETCH = {"space": ("w",), "panel": ("w",), "pipe_section": ("w", "branchAt"), "ga": ("w",), "tank": ("w",),
           "integral_tank": ("w",), "bands": ("w",), "log": ("w",), "tree": ("w",), "composition_bar": ("w",),
           "range_bar": ("w",), "spill": ("w",), "wind": ("w",), "tank_wall": ("w",), "boil_off": ("w",),
           "drip_tray": ("w",), "gas_cloud": ("w",), "zone": ("w", "rx"), "water_curtain": ("w",)}
PATHS = ("pipe", "wire", "hose")
GAP = 14            # between a moved part and what it was moved under, in the drawing's units
PAD = 10            # a room's inside margin


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ what the module draws
def deck_figures(course, module):
    """[(screen id, spec path, build entry)] - every kit figure the build sheet puts on a slide"""
    import content_script as cs
    p = cs.paths(course, module)
    bp = os.path.join(p["dir"], cs.mid(module) + ".build.json")
    if not (os.path.isfile(bp) and os.path.isfile(p["script"])):
        return [], None
    build = cs.load(bp)
    script = cs.load(p["script"])
    slides = {s["id"] for s in script["screens"] if s["kind"] in cs.INSTRUCTOR}
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", cs.mid(module))
    out = []
    for sid, e in (build.get("screens") or {}).items():
        f = (e.get("figure") or "").replace("\\", "/")
        if sid in slides and f.endswith(".kit.json"):
            out.append((sid, os.path.join(figdir, f), e))
    return out, figdir


def all_specs(course, module):
    """every *.kit.json the build sheet names, slides and task questions (for the spec checks)"""
    import content_script as cs
    p = cs.paths(course, module)
    bp = os.path.join(p["dir"], cs.mid(module) + ".build.json")
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", cs.mid(module))
    names = set()
    if os.path.isfile(bp):
        for e in (cs.load(bp).get("screens") or {}).values():
            f = (e.get("figure") or "").replace("\\", "/")
            if f.endswith(".kit.json"):
                names.add(f)
    return [os.path.join(figdir, n) for n in sorted(names)]


# ------------------------------------------------------------------ measuring
def ctx_for(spec_path, sid):
    """the studio's slide context for THIS screen (a spec on two slides is judged on each)"""
    ctx = studio.course_context(spec_path)
    if ctx and ctx["screen"] != sid:
        e = (ctx["build"].get("screens") or {}).get(sid)
        if e:
            ctx = dict(ctx, screen=sid, entry=e)
    return ctx


def has_strip(spec_path, sid):
    """does the slide carry an L57 photo row under its drawing? - read from the slide as the compiler builds it"""
    ctx = ctx_for(spec_path, sid)
    if not ctx:
        return False
    real, _, _ = studio.real_slide(ctx)
    return bool(real) and 'class="photo-strip"' in real.get("slide", "")


def measure(spec_path, sid, spec=None, strip=True):
    """(problems at the gate, the gate's result) of a spec drawn on its slide; problems None when it could not run.
    strip=False: drawn without the slide's L57 photo row (a candidate that needs the row's height)"""
    ctx = ctx_for(spec_path, sid)
    if ctx and not strip:
        ctx = dict(ctx, entry=dict(ctx["entry"], _no_strip=True))
    res, why = studio.run(spec_path, sizes=((1280, 800), (1024, 768)), shots=False, spec=spec, ctx=ctx)
    if not res:
        return None, {"error": why}
    r = res["sizes"].get(GATE) or {}
    if r.get("error"):
        return None, r
    # judged as the build judges: every drawing audit at 1280 x 800 (the drawing check, L54), and words under the floor at
    # 1024 x 768 too (run_audits.py's svgSmall - the kit grows words at most 2x, so a narrow column there fails the build)
    return [x for x in studio.problems(res) if x[0] == GATE or (x[0] == SMALL_AT and x[2] == "small text")], r


# ------------------------------------------------------------------ geometry
def shift_path(d, fx, fy=None):
    """an SVG path with every x coordinate mapped by fx and every y by fy (absolute commands; a relative one keeps its
    offsets)"""
    out, cmd = [], "M"
    fy = fy or (lambda v: v)
    toks = re.findall(r"[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?", d or "")
    nums = []

    def flush():
        if not nums:
            return
        c = cmd.upper()
        gx, gy = fx, fy
        if cmd.islower():                  # a relative step: scaled, never shifted
            gx, gy = (lambda v: fx(v) - fx(0)), (lambda v: fy(v) - fy(0))
        vals = list(nums)
        if c in "MLTCSQ":
            vals = [gx(v) if k % 2 == 0 else gy(v) for k, v in enumerate(vals)]
        elif c == "H":
            vals = [gx(v) for v in vals]
        elif c == "V":
            vals = [gy(v) for v in vals]
        elif c == "A":
            vals = [gx(v) if k % 7 == 5 else gy(v) if k % 7 == 6 else v for k, v in enumerate(vals)]
        out.append(" ".join(fmt(v) for v in vals))
        del nums[:]

    for t in toks:
        if re.match(r"[A-Za-z]", t):
            flush()
            cmd = t
            out.append(t)
        else:
            nums.append(float(t))
    flush()
    return re.sub(r"([A-Za-z]) ", r"\1", " ".join(out))


def fmt(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def squeeze(spec, k, x0=0.0):
    """every x position mapped x0 + (x - x0) * k, stretchable widths times k; sizes of everything else kept"""
    s = copy.deepcopy(spec)
    fx = lambda v: x0 + (v - x0) * k   # noqa: E731
    for p in s.get("parts", []):
        t = p.get("type")
        if t in PATHS:
            if p.get("d"):
                p["d"] = shift_path(p["d"], fx)
            if "x" in p:
                p["x"] = round(fx(p["x"]), 1)
            continue
        if "x" in p:
            p["x"] = round(fx(p["x"]), 1)
        for key in STRETCH.get(t, ()):
            if isinstance(p.get(key), (int, float)):
                p[key] = round(p[key] * k, 1)
        if isinstance(p.get("to"), list) and len(p["to"]) == 2:
            p["to"] = [round(fx(p["to"][0]), 1), p["to"][1]]
        if t == "gas_cloud" and isinstance(p.get("from"), list) and p.get("fromIn") == "figure":
            p["from"] = [round(fx(p["from"][0]), 1), p["from"][1]]
    s["size"] = [round(spec["size"][0] * k), spec["size"][1]]
    return s


def overlap(a, b, m=4):
    return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m


def inside(b, c):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return c[0] <= cx <= c[2] and c[1] <= cy <= c[3] and (b[2] - b[0]) * (b[3] - b[1]) < (c[2] - c[0]) * (c[3] - c[1])


def rows_of(ids, bx):
    """the parts as rows: a part joins a row when it shares at least a third of the smaller height with it"""
    rows = []
    for i in sorted(ids, key=lambda i: (bx[i][1], bx[i][0])):
        b = bx[i]
        for r in rows:
            top, bot = min(bx[j][1] for j in r), max(bx[j][3] for j in r)
            share = min(b[3], bot) - max(b[1], top)
            if share > 0.33 * min(b[3] - b[1], bot - top):
                r.append(i)
                break
        else:
            rows.append([i])
    return [sorted(r, key=lambda i: bx[i][0]) for r in rows]


def owners(parts, bx):
    """{part: the smallest room it sits in} - decided ONCE, on the spec as written, and kept through every round of a
    re-fit: a part that drifted out of its room in one round must not become a part of the room's neighbour in the next
    (IGF M01 s05: the engine and the lamp left the ESD-protected space and the audits could no longer see it)"""
    conts = [i for i in bx if parts[i].get("type") in CONTAINERS]
    owner = {}
    for i in bx:
        best = None
        for c in conts:
            if c != i and inside(bx[i], bx[c]) and (best is None or (bx[c][2] - bx[c][0]) < (bx[best][2] - bx[best][0])):
                best = c
        if best is not None:
            owner[i] = best
    return owner


def hosts(parts, bx, owner):
    """{small part: the part it is drawn ON} - a vent on its pipe section, a valve or a badge on a tank: it is not laid out
    by itself but keeps its place on its host. Decided once, on the spec as written, like owners()"""
    area = lambda b: max(1.0, (b[2] - b[0]) * (b[3] - b[1]))   # noqa: E731
    out = {}
    for i in bx:
        if parts[i].get("type") in CONTAINERS + PATHS:
            continue
        on = [j for j in bx if j != i and parts[j].get("type") not in CONTAINERS + PATHS and owner.get(j) == owner.get(i)
              and overlap(bx[i], bx[j], 2) and area(bx[i]) < 0.25 * area(bx[j])]      # on it, or touching it
        if on:
            out[i] = max(on, key=lambda j: area(bx[j]))
    return out


def pack(spec, boxes, width, margin=6, owner=None, host=None):
    """2.50.1 - a figure laid into a narrower width, row by row, room by room (lever 7, IGF M01 s05): in each row the parts
    keep their order; a part of fixed size (a readout, an engine, a lamp, a heading) keeps its width; the stretchable ones
    (STRETCH: a pipe section, a cloud, a tank ...) and the gaps give way, a stretchable part never under SHRINK_MIN; a room
    is as wide as the room it gets and lays out its own parts the same way. A pipe's x follows the parts of its row - its
    points are mapped piecewise between the parts' edges, so a pipe that ran into the engine still runs into it. Nothing
    moves up or down. Returns (spec, True) or (spec, False) when a row cannot fit even at the floor."""
    s = copy.deepcopy(spec)
    parts = s["parts"]
    bx = {int(k): list(v[:4]) for k, v in boxes.items() if int(k) < len(parts)}
    conts = [i for i in bx if parts[i].get("type") in CONTAINERS]
    owner = dict(owner) if owner is not None else owners(parts, bx)
    new = {}                                          # i -> new [x0, x1]
    ok = [True]
    host = {i: h for i, h in (hosts(parts, bx, owner) if host is None else host).items() if i in bx and h in bx}

    def lay(cid, left, right):
        kids = [i for i in bx if owner.get(i) == cid and parts[i].get("type") not in PATHS and i not in host]
        for row in rows_of(kids, bx):
            ws = [bx[i][2] - bx[i][0] for i in row]
            gaps = [max(0.0, bx[row[k + 1]][0] - bx[row[k]][2]) for k in range(len(row) - 1)]
            stretch = [parts[i].get("type") in STRETCH or parts[i].get("type") in CONTAINERS for i in row]
            avail = right - left
            if len(row) == 1 and parts[row[0]].get("type") in CONTAINERS and ws[0] > avail:
                ws[0] = avail          # a room alone in its row takes the width it gets: its own parts are laid out in it
            fixed = sum(w for w, st in zip(ws, stretch) if not st)
            flex = sum(w for w, st in zip(ws, stretch) if st)
            gap_min = [min(g, GAP) for g in gaps]
            room = avail - fixed - sum(gaps)
            if room >= flex:                           # it fits as it is: only shifted to start at the left edge
                k_s, k_g = 1.0, 1.0
            elif avail - fixed - sum(gap_min) >= flex * SHRINK_MIN:
                k_g = 1.0 if room >= flex * SHRINK_MIN else 0.0
                k_s = (avail - fixed - (sum(gaps) if k_g else sum(gap_min))) / flex if flex else 1.0
                k_s = min(1.0, k_s)
            else:
                ok[0] = False
                k_s, k_g = SHRINK_MIN, 0.0
            x = left + (bx[row[0]][0] - left if room >= flex and bx[row[0]][0] >= left else 0)
            x = max(left, min(x, right - (fixed + flex * k_s + sum(gaps if k_g else gap_min))))
            for k, i in enumerate(row):
                w = ws[k] * (k_s if stretch[k] else 1.0)
                new[i] = [x, x + w]
                x += w + (gaps[k] if k_g else gap_min[k]) if k < len(gaps) else w
        for i in kids:
            if parts[i].get("type") in CONTAINERS:
                lay(i, new[i][0] + PAD, new[i][1] - PAD)

    lay(None, margin, width - margin)
    for i, h in host.items():                        # on its host, at the same share of the host's width
        if h in new:
            hw0, hw1 = bx[h][2] - bx[h][0], new[h][1] - new[h][0]
            x0 = new[h][0] + (bx[i][0] - bx[h][0]) * (hw1 / hw0 if hw0 else 1.0)
            new[i] = [x0, x0 + bx[i][2] - bx[i][0]]

    def interp(pts, x):
        if x <= pts[0][0]:
            return pts[0][1] + (x - pts[0][0])
        if x >= pts[-1][0]:
            return pts[-1][1] + (x - pts[-1][0])
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            if a0 <= x <= a1:
                return b0 if a1 == a0 else b0 + (x - a0) * (b1 - b0) / (a1 - a0)
        return x

    def pipe_map(i, cid):
        """a pipe follows what it touches: the parts within 12 units of it, and its room's walls - never a part it only
        passes in another row (the gas pipe that ran into the engine still runs into it, and ends inside its room)"""
        if cid is not None and cid in new:
            pts = [(bx[cid][0] + PAD, new[cid][0] + PAD), (bx[cid][2] - PAD, new[cid][1] - PAD)]
        else:
            pts = [(0.0, float(margin)), (float(spec["size"][0]), float(width - margin))]
        pb = bx.get(i)
        for j in new:
            if pb and j != i and owner.get(j) == cid and overlap(pb, bx[j], 12):
                pts += [(bx[j][0], new[j][0]), (bx[j][2], new[j][1])]
        pts.sort()
        mono = []
        for a, b in pts:                              # increasing both ways, or the pipe would fold back on itself
            if not mono or (a > mono[-1][0] + 0.5 and b > mono[-1][1]):
                mono.append((a, b))
        return lambda x: interp(mono, x)

    for i, (x0, x1) in new.items():
        p = parts[i]
        dx = x0 - bx[i][0]
        p["x"] = round((p.get("x") or 0) + dx, 1)
        neww, oldw = x1 - x0, bx[i][2] - bx[i][0]
        if abs(neww - oldw) > 0.5:
            t = p.get("type")
            if isinstance(p.get("w"), (int, float)):
                p["w"] = round(max(p["w"] - (oldw - neww), 1), 1)
                if t == "pipe_section" and isinstance(p.get("branchAt"), (int, float)):
                    p["branchAt"] = round(p["branchAt"] * p["w"] / float(p["w"] + (oldw - neww)), 1)
        if isinstance(p.get("to"), list):
            p["to"] = [round(p["to"][0] + dx, 1), p["to"][1]]
    for i, p in enumerate(parts):                     # pipes, and what is placed in figure units, follow their row
        cid = owner.get(i)
        if p.get("type") in PATHS and p.get("d"):
            p["d"] = shift_path(p["d"], pipe_map(i, cid))
        if p.get("type") == "gas_cloud" and isinstance(p.get("from"), list) and p.get("fromIn") == "figure" and i in new:
            w0_, w1_ = bx[i][2] - bx[i][0], new[i][1] - new[i][0]   # the same point of the cloud
            p["from"] = [round(new[i][0] + (p["from"][0] - bx[i][0]) * (w1_ / w0_ if w0_ else 1.0), 1), p["from"][1]]
    s["size"] = [int(round(width)), spec["size"][1]]
    return s, ok[0]


def keep_in(spec, boxes, owner=None):
    """every part inside the room it sits in, after a pack: a part past the room's floor grows the room downwards (and the
    frame with it, when the room reaches the frame's edge); a part past a side or the ceiling is moved in. Returns (spec,
    repairs)"""
    s = copy.deepcopy(spec)
    parts = s["parts"]
    bx = {int(k): list(v[:4]) for k, v in boxes.items() if int(k) < len(parts)}
    conts = [i for i in bx if parts[i].get("type") in CONTAINERS]
    n = 0
    for i in bx:
        p = parts[i]
        if p.get("type") in CONTAINERS + PATHS:
            continue
        if owner is not None:
            c = owner.get(i)
            if c is None or c not in bx:
                continue
        else:
            cs_ = [c for c in conts if inside(bx[i], bx[c])]
            if not cs_:
                continue
            c = min(cs_, key=lambda c: (bx[c][2] - bx[c][0]) * (bx[c][3] - bx[c][1]))
        b, r = bx[i], bx[c]
        down = b[3] - (r[3] - PAD / 2.0)
        if down > 0.5 and isinstance(parts[c].get("h"), (int, float)):
            parts[c]["h"] = round(parts[c]["h"] + down, 1)
            r[3] += down
            s["size"][1] = max(s["size"][1], int(round(r[3] + 4)))
            n += 1
        dx = (r[0] + PAD / 2.0 - b[0]) if b[0] < r[0] + PAD / 2.0 else -(b[2] - (r[2] - PAD / 2.0)) if b[2] > r[2] - PAD / 2.0 else 0
        dy = (r[1] + PAD / 2.0 - b[1]) if b[1] < r[1] + PAD / 2.0 else 0
        if abs(dx) > 0.5 or abs(dy) > 0.5:
            p["x"] = round((p.get("x") or 0) + dx, 1)
            p["y"] = round((p.get("y") or 0) + dy, 1)
            if p.get("type") == "gas_cloud" and isinstance(p.get("from"), list) and p.get("fromIn") == "figure":
                p["from"] = [round(p["from"][0] + dx, 1), round(p["from"][1] + dy, 1)]
            n += 1
    return s, n


SHRINK = ("engine", "tank", "readout", "pump", "exchanger", "space", "integral_tank", "gas_cloud", "drip_tray")
SHRINK_MIN = 0.7          # a part is drawn at least this share of the size the spec gave it


def tidy(spec, boxes, width, w0=None, owner=None, skip=()):
    """one round of local repairs, after a squeeze - nothing is wrapped, so the drawing keeps its shape:
    a part past its room's right edge (or the frame's) moves left into free room, else is drawn narrower (never under
    SHRINK_MIN of its size); a part on top of the one before it moves beside it, or down inside its room; a free text
    wider than the frame breaks onto two lines at the space nearest its middle (the same words).
    Returns (new spec, number of repairs)"""
    s = copy.deepcopy(spec)
    parts = s["parts"]
    w0 = w0 or {}
    bx ={int(k): list(v[:4]) for k, v in boxes.items() if int(k) < len(parts)}
    conts = [i for i in bx if parts[i].get("type") in CONTAINERS]
    if owner is None:
        owner = {}
        for i in bx:
            if parts[i].get("type") not in CONTAINERS:
                for c in conts:
                    if inside(bx[i], bx[c]):
                        owner[i] = c
    else:
        owner = {i: c for i, c in owner.items() if c in bx and parts[i].get("type") not in CONTAINERS}
    fixes = 0
    order = sorted((i for i in bx if parts[i].get("type") not in CONTAINERS + PATHS), key=lambda i: (bx[i][0], bx[i][1]))

    def move(i, dx, dy):
        p = parts[i]
        p["x"] = round((p.get("x") or 0) + dx, 1)
        p["y"] = round((p.get("y") or 0) + dy, 1)
        if isinstance(p.get("to"), list):
            p["to"] = [round(p["to"][0] + dx, 1), round(p["to"][1] + dy, 1)]
        if p.get("type") == "gas_cloud" and isinstance(p.get("from"), list) and p.get("fromIn") == "figure":
            p["from"] = [round(p["from"][0] + dx, 1), round(p["from"][1] + dy, 1)]
        bx[i] = [bx[i][0] + dx, bx[i][1] + dy, bx[i][2] + dx, bx[i][3] + dy]

    for i in order:
        if i in skip:                                   # drawn on its host: it goes where the host goes
            continue
        p = parts[i]
        c = owner.get(i)
        left, right = (bx[c][0] + PAD, bx[c][2] - PAD) if c is not None else (4, width - 4)
        top, bottom = (bx[c][1] + PAD, bx[c][3] - PAD) if c is not None else (4, 1e9)
        mates = [j for j in order if j != i and owner.get(j) == c]
        b = bx[i]
        w = b[2] - b[0]
        if p.get("type") == "text" and not p.get("to") and w > right - left and " " in (p.get("text") or "") \
                and "\n" not in p.get("text"):
            t = p["text"]
            mid = len(t) / 2.0
            cut = min((k for k, ch in enumerate(t) if ch == " "), key=lambda k: abs(k - mid))
            p["text"] = t[:cut] + "\n" + t[cut + 1:]
            fixes += 1
            continue
        if b[2] > right + 0.5:                                   # past the right edge
            over = b[2] - right
            cand = [b[0] - over, b[1], b[2] - over, b[3]]
            if cand[0] >= left - 0.5 and not any(overlap(cand, bx[j]) for j in mates):
                move(i, -over, 0)
                fixes += 1
                continue
            if p.get("type") in SHRINK and isinstance(p.get("w"), (int, float)):
                nw = max(p["w"] - over, w0.get(i, p["w"]) * SHRINK_MIN)
                if nw < p["w"] - 0.5:
                    bx[i][2] -= p["w"] - nw
                    p["w"] = round(nw, 1)
                    fixes += 1
                    continue
        hit = [j for j in mates if overlap(bx[i], bx[j], 2) and bx[j][0] <= bx[i][0]]
        if hit and p.get("type") != "text":
            j = max(hit, key=lambda j: bx[j][2])
            for dx, dy in ((bx[j][2] + GAP - b[0], 0), (0, bx[j][3] + GAP - b[1])):
                cand = [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]
                if cand[2] <= right + 0.5 and cand[3] <= bottom + 0.5 and not any(overlap(cand, bx[k], 2) for k in mates if k != i):
                    move(i, dx, dy)
                    fixes += 1
                    break
    return s, fixes


def crop(spec, boxes, panel):
    """EMPTY: a window on the canvas around what the figure shows, in its panel's shape (the parts are not moved)"""
    bb = [v[:4] for v in boxes.values() if v[5] not in ("panel",)]
    if not bb:
        return None
    x0, y0 = min(b[0] for b in bb) - 8, min(b[1] for b in bb) - 8
    x1, y1 = max(b[2] for b in bb) + 8, max(b[3] for b in bb) + 8
    w, h = x1 - x0, y1 - y0
    a = panel[0] / float(panel[1]) if panel and panel[1] else w / h
    if w / h > a:
        nh = w / a
        y0 -= (nh - h) / 2
        h = nh
    else:
        nw = h * a
        x0 -= (nw - w) / 2
        w = nw
    full = spec["size"]
    if w >= full[0] - 1 and h >= full[1] - 1:
        return None                         # nothing to crop
    s = copy.deepcopy(spec)
    s["view"] = [round(x0, 1), round(y0, 1), round(w, 1), round(h, 1)]
    return s


# ------------------------------------------------------------------ fixing one figure
COVERS = ("gas_cloud", "flame", "fire", "spray", "spill", "wind", "text")   # drawn over other parts by their nature


def extent(p):
    """a part's box (x0, y0, x1, y1) from the spec alone: x y w h, a radius, the corners of an absolute path, else its point"""
    num = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)  # noqa: E731
    x, y = p.get("x") or 0, p.get("y") or 0
    if num(p.get("w")) and num(p.get("h")):
        return (x, y, x + p["w"], y + p["h"])
    r = p.get("r") if num(p.get("r")) else p.get("size") if num(p.get("size")) else None
    if r:
        return (x - r, y - r, x + r, y + r)
    if isinstance(p.get("d"), str):
        xs, ys, cx, cy = [], [], 0.0, 0.0
        for cmd, args in re.findall(r"([MLHVmlhv])([^MLHVmlhv]*)", p["d"]):
            v = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", args)]
            if cmd.islower() or not v:                   # a relative step: its corner is not known here
                continue
            if cmd in "ML" and len(v) >= 2:
                cx, cy = v[-2], v[-1]
            elif cmd == "H":
                cx = v[-1]
            elif cmd == "V":
                cy = v[-1]
            xs.append(cx)
            ys.append(cy)
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None
    return (x, y, x, y) if num(p.get("x")) or num(p.get("y")) else None


def spoiled(spec, cand, tol=1.0):
    """why a re-fit is no drawing at all - [] when it is one. A part moved outside the frame, or onto a part it was clear of
    in the spec as written (M01 benchmark run 4, s05: a "candidate" with the lamp at x 635 in a 600-wide spec and the engine
    over the valve - the kit grows its frame to hold a stray part, so the audits passed it). Never kept, never saved."""
    def frame(s):
        v = s.get("view")
        return (v[0], v[1], v[0] + v[2], v[1] + v[3]) if isinstance(v, list) and len(v) == 4 else (0, 0, s["size"][0], s["size"][1])

    def out_of(b, f):
        return b and (b[0] < f[0] - tol or b[1] < f[1] - tol or b[2] > f[2] + tol or b[3] > f[3] + tol)

    def on(b, a):                                        # b's middle inside a, and a box, not a point
        return a and b and a[2] > a[0] and a[3] > a[1] and a[0] < (b[0] + b[2]) / 2 < a[2] and a[1] < (b[1] + b[3]) / 2 < a[3]

    why, f0, f1 = [], frame(spec), frame(cand)
    old, new = spec.get("parts") or [], cand.get("parts") or []
    if len(old) != len(new):
        return ["the re-fit has %d parts, the spec %d" % (len(new), len(old))]
    e0, e1 = [extent(p) for p in old], [extent(p) for p in new]
    name = lambda i: "%s (%s)" % (new[i].get("id") or i + 1, new[i].get("type"))  # noqa: E731
    for i in range(len(new)):
        if e1[i] != e0[i] and out_of(e1[i], f1) and not out_of(e0[i], f0):     # moved (a crop moves nothing)
            why.append("%s moved outside the %s x %s frame (to x %s, y %s)" % (name(i), fmt(f1[2] - f1[0]), fmt(f1[3] - f1[1]),
                                                                               fmt(e1[i][0]), fmt(e1[i][1])))
    solid = [i for i, p in enumerate(new) if p.get("type") not in CONTAINERS + PATHS + COVERS]
    for a in solid:
        for b in solid:
            if a != b and on(e1[b], e1[a]) and not on(e0[b], e0[a]):
                why.append("%s moved onto %s" % (name(b), name(a)))
    return why


def usable(spec, new, how, best):
    """(fix, how, closest attempt) with anything spoiled() taken out: never a fit, never a saved "candidate", with a part
    out of its frame or on another part - and the words say why nothing was saved"""
    bad = spoiled(spec, new) if new else []
    if bad:
        new, how = None, "no fix: the re-fit %s" % "; ".join(bad)
    bad = spoiled(spec, best[0]) if best else []
    if bad:
        how, best = "%s - no candidate saved: it %s" % (how, "; ".join(bad)), None
    return new, how, best


def classify(probs):
    checks = {p[2] for p in probs}
    return checks


def try_fixes(spec_path, sid, spec, r0, probs0, log):
    """(fixed spec, how) or (None, why not) - the deterministic fixes, each measured again on the real slide"""
    checks = classify(probs0)
    panel = (r0.get("states") or [{}])[-1].get("panel") or [0, 0]
    boxes = r0.get("parts") or {}
    tried = []
    if checks <= {"empty"} and boxes:                     # only EMPTY: crop to what the steps show
        c = crop(spec, boxes, panel)
        if c:
            p, r = measure(spec_path, sid, c)
            tried.append("cropped to what it shows")
            if p == []:
                return c, "EMPTY: cropped to what it shows at its busiest step (%s), the parts not moved" % " ".join(fmt(v) for v in c["view"]), None
    # COLUMN: the spec is drawn below 0.8:1 in its column, so its words were grown past what the drawing holds - laid into
    # the column row by row (pack), kept inside its rooms, tidied; at a few widths, in parallel. When it does not fit with
    # the slide's L57 photo row under it, tried again without the row (its height goes to the drawing)
    scale = (r0.get("report") or {}).get("scale") or 1
    best = None
    if (scale < 0.8 or any(x[0] == SMALL_AT for x in probs0)) and panel[0]:
        bx0 = {int(k): list(v[:4]) for k, v in boxes.items() if int(k) < len(spec["parts"])}
        own = owners(spec["parts"], bx0)
        hst = hosts(spec["parts"], bx0, own)

        def attempt(arg):
            wt, strip, boxes0 = arg
            if wt >= spec["size"][0] * 0.98:
                return None
            cand, boxes, out, n = spec, boxes0, None, 0
            w0 = {i: q["w"] for i, q in enumerate(spec["parts"]) if isinstance(q.get("w"), (int, float))}
            for _ in range(3):
                cand, _ok = pack(cand, boxes, wt, owner=own, host=hst)   # laid into the width, by the boxes the words need
                for step in ("pack", "keep_in", "tidy"):
                    if step != "pack":
                        nxt, k = (keep_in(cand, boxes, own) if step == "keep_in" else tidy(cand, boxes, cand["size"][0], w0, own, set(hst)))
                        if not k:
                            continue
                        cand = nxt
                    p, r = measure(spec_path, sid, cand, strip)
                    if p is None:
                        return out
                    n += 1
                    boxes = r.get("parts") or {}
                    if spoiled(spec, cand):              # a part sent out of the frame or onto another: never the answer
                        continue
                    if out is None or len(p) < len(out[1]):
                        out = (cand, p, n, strip, (r.get("states") or [{}])[-1].get("panel") or panel)
                    if not p:
                        return out
            return out

        args = [(panel[0] * f, True, boxes) for f in (0.88, 1.0, 1.14)]
        if has_strip(spec_path, sid):                    # the same slide without its photo row, tried at the same time
            p_ns, r_ns = measure(spec_path, sid, None, False)
            pn = (r_ns.get("states") or [{}])[-1].get("panel") or panel
            if p_ns is not None:
                args += [(pn[0] * f, False, r_ns.get("parts") or boxes) for f in (0.88, 1.0, 1.14)]
        with cf.ThreadPoolExecutor(max_workers=len(args)) as ex:
            outs = [x for x in ex.map(attempt, args) if x]
        for o in outs:
            if best is None or len(o[1]) < len(best[1]) or (len(o[1]) == len(best[1]) and o[3] and not best[3]):
                best = o
        if best and not best[1]:
            cand, _, n, strip, pn = best
            if not strip:
                cand = dict(cand, _strip=False)
            return cand, ("COLUMN: re-fitted to its %d x %d px column%s - drawn %d units wide (was %d), %d round(s); the spec is "
                          "unchanged; look at it in the review sheet" % (pn[0], pn[1], "" if strip else (
                              ", with the L57 photo row under it LEFT OFF this slide (the drawing needs its height; a "
                              "wider column brings the row back)"),
                              cand["size"][0], spec["size"][0], n)), None
        if best:
            tried.append("re-fitted to its %d px column: %d finding(s) left (was %d)" % (panel[0], len(best[1]), len(probs0)))
    return None, "; ".join(tried) or "no deterministic fix for %s" % ", ".join(sorted(checks)), best


# ------------------------------------------------------------------ the report
HINT = {
    "empty": "fill the frame: crop what the steps never show, spread the parts, or add the context the slide's lines name",
    "text zone": "give the part room for its words (a larger w/h, or move it clear) - the label layout places words, not parts",
    "inside": "the part pokes out of the room it sits in: make the room larger or move the part in",
    "cut off": "something reaches past the drawing's frame or the slide: make it smaller or the frame larger",
    "small text": "too many words for the room the figure has: give it a wider column or fewer words",
    "label": "a label found no clear place: give the figure more room around that part, or shorter words",
    "contrast": "colour the part for the dark panel (kit tokens only) or mark one meant to be quiet data-low-contrast",
}
# 2.50.7 (M01 benchmark run 5, s03) - the kit rises a vent's puffs only into free air; a puff still in the way means the outlet
# has almost none: it stood 8 units under the other ship's keel
PUFF_HINT = ("a vent's puffs need about 57 units of free air above its outlet (they start 12 above it, rise up to 34 and "
             "grow 10.5 across); the kit rises them only as far as the air is free, and here there is too little - lower the "
             "outlet (a shorter mast: the vent's y and the end of the pipe under it) or move what is drawn above it")


def short(part):
    m = re.search(r'"([^"]+)"', part or "")
    return m.group(1) if m else (part or "")


def group(probs):
    """{(check, part words): [steps]} - one line per problem, not one per step"""
    g = {}
    for size, step, check, part, detail in probs:
        g.setdefault((check, short(part), re.sub(r"\s+\d+ px|\(\d+/\d+ points\)", "", detail or "")[:90]), []).append(str(step))
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--no-fix", action="store_true", help="only check; make no fix")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    code, text, data = run_all(o.course, o.module, fix=not o.no_fix)
    print(json.dumps(data, ensure_ascii=False, indent=1) if o.json else text)
    return code


def run_all(course, module, fix=True, jobs=4):
    """(exit code, report text, data) - the spec checks, then every slide figure measured at once, then the fixes"""
    import compile_module as cm
    lines, data = [], {"figures": {}}
    # the spec checks (check_kit.py): a spec that would not draw is said first, and not measured
    types = check_kit.kit_types()
    import content_script as cs
    mdir = os.path.join(course, "modules", "module%02d" % int(module)) if str(module).isdigit() else None
    if mdir and os.path.isfile(os.path.join(mdir, "assets", "kit_parts.js")):
        types |= check_kit.local_types(os.path.join(mdir, "assets", "kit_parts.js"))
    broken = set()
    spec_probs = []
    for sp in all_specs(course, module):
        name = os.path.basename(sp)
        if not os.path.isfile(sp):
            spec_probs.append("%s: the build sheet names it and it is not there" % name)
            broken.add(sp)
            continue
        spec, err = check_kit.load_spec(sp)
        if err:
            spec_probs.append("%s: %s" % (name, err))
            broken.add(sp)
            continue
        for x in check_kit.check_spec(spec, types, name):
            spec_probs.append(x)
            if " is not a kit part" in x or "not valid" in x:
                broken.add(sp)
    figs, figdir = deck_figures(course, module)
    todo = [(sid, sp, e) for sid, sp, e in figs if sp not in broken and os.path.isfile(sp)]
    # 2.50.1 - a figure clean at the last run, whose slide (as the compiler builds it: words, layout, fit, photo row),
    # spec and kit files have not changed since, is not measured again: a review-driven build changes one or two
    keys, cache_path = {}, os.path.join(figdir or "", cm.FIT_DIR, "_clean.json")
    try:
        cache = json.load(io.open(cache_path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    try:
        p = cs.paths(course, module)
        script, build = cs.load(p["script"]), cs.load(os.path.join(p["dir"], cs.mid(module) + ".build.json"))
        deck, _, _ = cm.compile_deck(script, build, mdir, figdir, "CACHE", True)
        files = "".join(io.open(f, "rb").read().decode("utf-8", "replace") for f in
                        (os.path.join(studio.KIT, "kit.js"), os.path.join(studio.KIT, "kit.css"), studio.AUDIT)
                        + tuple(os.path.join(studio.TOKENS, x) for x in cm.STYLES) if os.path.isfile(f))
        base = sha(files)
        for sid, sp, e in todo:
            m = re.search(r'<section [^>]*\bid="%s"[^>]*>.*?</section>' % re.escape(sid), deck, re.S)
            keys[sid] = sha(base + (m.group(0) if m else "") + io.open(sp, encoding="utf-8").read())
    except Exception:                                    # noqa: BLE001 - no cache: every figure is measured
        keys = {}
    skipped = [x for x in todo if keys.get(x[0]) and cache.get(x[0]) == keys[x[0]]]
    todo = [x for x in todo if x not in skipped]
    results, entry = {}, {}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(measure, sp, sid): (sid, sp) for sid, sp, e in todo}
        for sid, sp, e in todo:
            entry[(sid, sp)] = e
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()
    left, fixed = [], []

    # a fix is tried per failing figure, in parallel too
    def fix_one(key):
        sid, sp = key
        e = entry[key]
        item = (sid, sp, e)
        probs, r = results[key]
        text = io.open(sp, encoding="utf-8").read().strip()      # as the compiler reads it (read_figure)
        spec = json.loads(text)
        fp = cm.fit_path(figdir, os.path.basename(sp), sid)
        cand_path = re.sub(r"\.kit\.json$", ".candidate.kit.json", fp)
        if probs == [] or probs is None or not fix:
            return item, probs, r, None, None
        sc = cs.load(cs.paths(course, module)["script"])
        s = next((x for x in sc["screens"] if x["id"] == sid), {})
        column = cm.composition_key(s, e)
        old = cm.fitted(figdir, os.path.basename(sp), text, column, sid)
        if old:                                       # a fit made before for this spec and this column: still clean?
            rec_old = json.load(io.open(fp, encoding="utf-8"))
            p, _ = measure(sp, sid, json.loads(old), rec_old.get("strip") is not False)
            if p == []:
                return item, probs, r, json.loads(old), rec_old.get("how", "re-fitted")
        new, how, best = try_fixes(sp, sid, spec, r, probs, None)
        if os.path.isfile(cand_path):
            os.remove(cand_path)
        new, how, best = usable(spec, new, how, best)
        if new:
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            rec = {"source": cm.sha(text), "column": column, "how": how, "made_by": "figure_fit.py"}
            if new.get("_strip") is False:
                rec["strip"] = False
                new = {k: v for k, v in new.items() if k != "_strip"}
            rec["spec"] = new
            io.open(fp, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=1))
        elif best and len(best[1]) < len(probs):      # the closest attempt, to edit instead of redrawing
            os.makedirs(os.path.dirname(cand_path), exist_ok=True)
            io.open(cand_path, "w", encoding="utf-8").write(json.dumps(best[0], ensure_ascii=False, indent=1))
            how += (" - saved as %s: copy it over %s and fix what it leaves:\n%s"
                    % (os.path.normpath(cand_path), os.path.basename(sp),
                       "\n".join("        %s - %s: %s (step %s)" % (c, pt, dt, ",".join(sorted(set(st))))
                                 for (c, pt, dt), st in sorted(group(best[1]).items()))))
        return item, probs, r, new, how
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        outs = list(ex.map(fix_one, sorted(results, key=lambda t: t[0])))
    for (sid, sp, e), probs, r, new, how in outs:
        name = os.path.basename(sp)
        d = data["figures"].setdefault(sid, {"spec": name})
        if probs is None:
            left.append("%s (%s): the figure could not be measured - %s" % (sid, name, r.get("error")))
            d["error"] = r.get("error")
            continue
        rep = r.get("report") or {}
        st = (r.get("states") or [{}])[-1]
        d.update({"panel": st.get("panel"), "scale": rep.get("scale"), "problems": len(probs)})
        if new:
            fixed.append("%s (%s): fixed by itself - %s" % (sid, name, how))
            d["fixed"] = how
            continue
        if probs:
            block = ["%s (%s) on its slide - drawn %s px in a %s px panel, scale %.2f:" % (
                sid, name, "x".join(map(str, st.get("svg") or [])), "x".join(map(str, st.get("panel") or [])), rep.get("scale") or 0)]
            seen = set()
            for (check, part, detail), steps in sorted(group(probs).items()):
                block.append("    %s - %s: %s (step %s)" % (check, part, detail, ",".join(sorted(set(steps)))))
            for check in sorted({c for c, _, _ in group(probs)}):
                if HINT.get(check) and check not in seen:
                    seen.add(check)
                    block.append("    fix (%s): %s" % (check, HINT[check]))
            if any("kit-puffs" in (part or "") for _, _, _, part, _ in probs):
                block.append("    fix (vent): %s" % PUFF_HINT)
            bb = [v[:4] for v in (r.get("parts") or {}).values() if v[5] not in CONTAINERS]
            if any(c == "empty" for c, _, _ in group(probs)) and bb:
                w_ = max(b[2] for b in bb) - min(b[0] for b in bb)
                h_ = max(b[3] for b in bb) - min(b[1] for b in bb)
                pa = (st.get("panel") or [1, 1])[0] / float((st.get("panel") or [1, 1])[1] or 1)
                if h_ and (w_ / h_) < 0.6 * pa:       # IGF M01 s02: a thin upright scale in a wide panel took 5 builds
                    block.append("    why EMPTY: what it draws is %d x %d units - %s - in a %s frame: draw it across the panel (a "
                                 "scale with \"orient\": \"h\", the parts side by side), or give the slide \"composition\": "
                                 "\"wide-left\" so its column has the drawing's shape; moving parts a few units will not fill it"
                                 % (w_, h_, "tall and narrow", "wide"))
                elif h_ and (w_ / h_) > 1.6 * pa:
                    block.append("    why EMPTY: what it draws is %d x %d units - wide and flat - in a taller frame: stack the "
                                 "parts, or give the spec a flatter \"size\" so the frame has the drawing's shape" % (w_, h_))
            if how:
                block.append("    tried by itself: %s" % how)
            left.append("\n".join(block))
            d["left"] = [list(x) for x in probs]
    for sid, sp, e in figs:            # a figure clean as written needs no fit: an old one is removed
        fp = cm.fit_path(figdir, os.path.basename(sp), sid)
        dd = data["figures"].get(sid) or {}
        if os.path.isfile(fp) and dd.get("problems") == 0:
            os.remove(fp)
    # the cache: clean as written, or clean by a fit (its key taken again - the slide now carries the fit)
    for sid, sp, e in figs:
        dd = data["figures"].get(sid) or {}
        if dd.get("problems") == 0 and keys.get(sid):
            cache[sid] = keys[sid]
        elif not dd.get("fixed"):
            cache.pop(sid, None)
    if any(d.get("fixed") for d in data["figures"].values()):
        try:
            deck, _, _ = cm.compile_deck(script, build, mdir, figdir, "CACHE", True)
            for sid, sp, e in figs:
                if (data["figures"].get(sid) or {}).get("fixed"):
                    m = re.search(r'<section [^>]*\bid="%s"[^>]*>.*?</section>' % re.escape(sid), deck, re.S)
                    cache[sid] = sha(base + (m.group(0) if m else "") + io.open(sp, encoding="utf-8").read())
        except Exception:                                # noqa: BLE001
            pass
    if figdir and keys:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        io.open(cache_path, "w", encoding="utf-8").write(json.dumps(cache, indent=1, sort_keys=True))
    n = len(todo) + len(skipped)
    lines += ["Figures: %d on slides, %d spec(s) checked" % (n, len(all_specs(course, module)))]
    lines += ["  spec: " + x for x in spec_probs]
    lines += ["  " + x for x in fixed]
    lines += ["  " + x for x in left]
    code = 1 if (left or spec_probs) else 0
    lines.append("Figures: %s" % ("every figure clean%s" % (" (%d fixed by itself)" % len(fixed) if fixed else "") if code == 0
                                  else "%d figure(s) to fix" % (len(left) + len(spec_probs))))
    data.update({"fixed": fixed, "left": left, "spec_problems": spec_probs})
    return code, "\n".join(lines), data


if __name__ == "__main__":
    sys.exit(main())
