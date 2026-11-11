#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""layout_plan - each slide's blueprint, chosen over the whole module like an engineer would (course-module-ui
knowledge/blueprints/, layout-templates.json "shapes").

A slide's look is its shape - where its picture sits against its words - not its template's name: a picture on the left
and one on the right are one look (beside). Every blueprint file says what it is good for: the slides it can stand in for
(its group), the pictures it takes and the picture shapes its box suits, the words it holds. For each teaching slide every
blueprint of its group is scored - the picture's real shape (a photograph's pixels, a 2D drawing's size, a 3D scene's
home view) against the box's, the words against the budget, the names it shows. plan() then chooses across the deck: the
same shape never twice in a row, beside on at most about half of the teaching slides, at least four shapes in a module of
ten teaching slides or more, and among near-equal fits a choice seeded by the course and the module, so a rebuild is the
same and two modules do not look alike. A slide whose build sheet names its template, variant or layout keeps it; so does
a slide that fits one blueprint only. Words are never cut or moved: only blueprints the slide already fits are chosen.

    python layout_plan.py <deck index.html | module folder>     the deck's shape line, its longest run and its beside share
    python test_layout_plan.py
"""
from __future__ import annotations

import glob
import hashlib
import html
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
KNOW = os.path.join(SKILLS, "course-module-ui", "knowledge")
with io.open(os.path.join(KNOW, "layout-templates.json"), encoding="utf-8") as _f:
    LT = json.load(_f)
SH = LT["shapes"]
ORDER, PLAN = SH["order"], SH["plan"]
BAND_TEMPLATES = tuple(SH["band_templates"])
BUDGETS = LT["budgets"]
DENSE_WORDS = LT["dense"]["words"]
COMPARISON = re.compile(r"(?i)\b(compar\w*|versus|vs\.?|before\s*(?:and|/|&)\s*after)(?!\w)")
SECTION = re.compile(r"<section\b([^>]*)>", re.S)


def library(folder=None):
    """{blueprint id: blueprint} - every file of course-module-ui/knowledge/blueprints/, a mirror filled from its base"""
    out = {}
    for p in sorted(glob.glob(os.path.join(folder or os.path.join(KNOW, "blueprints"), "*.json"))):
        with io.open(p, encoding="utf-8") as f:
            b = json.load(f)
        out[b["id"]] = b
    for b in out.values():
        base = out.get(b.get("mirror") or "")
        if base:
            for k in ("for", "fill", "grid", "cols", "rows"):
                b.setdefault(k, base.get(k))
    return out


LIB = library()
MAP = {k: b.get("shape", "") for k, b in LIB.items()}


def shape_of(tid, variant):
    """the shape of a template and variant: beside, top, bottom, stage, photo-full, words, two - "" for a slide that is not
    a teaching slide (a task launch, the recap), None for one the library does not know"""
    return MAP.get("%s.%s" % (tid, variant))


def variants(tid):
    """the variants the library has for a template, in file order"""
    return [b["variant"] for b in LIB.values() if b.get("template") == tid]


def comparison(tid, visual_kind, title):
    """a slide the script marks as a comparison: the compare-two or before-after template, a comparison picture, or a title
    that compares - it may take the shape of the slide before it on purpose"""
    return tid in ("compare-two", "before-after") or visual_kind == "comparison" or bool(COMPARISON.search(title or ""))


# ------------------------------------------------------------------ a picture's natural shape
def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _vec(v, n=3):
    try:
        out = [float(x) for x in v][:n]
        return out if len(out) == n else None
    except (TypeError, ValueError):
        return None


def _local_box(p):
    """a 3D kit part's box in its own frame (PARTS.md: where its "at" is), roughly - [lo, hi] or a list of points"""
    t = p.get("type")
    size = p.get("size") if isinstance(p.get("size"), list) else []
    sz = [_num(x) for x in size] + [0.0] * (3 - len(size))
    r = _num(p.get("r"), 0.5)
    if t == "box" or t == "tank_prism":
        return [-sz[0] / 2, -sz[1] / 2, -sz[2] / 2], [sz[0] / 2, sz[1] / 2, sz[2] / 2]
    if t in ("room", "enclosure", "cabinet", "accommodation", "air_intake"):
        return [-sz[0] / 2, 0, -sz[2] / 2], [sz[0] / 2, sz[1], sz[2] / 2]
    if t == "panel":
        return [-sz[0] / 2, -sz[1] / 2, 0], [sz[0] / 2, sz[1] / 2, 0]
    if t == "deck_plate":
        return [-sz[0] / 2, -_num(p.get("side"), 3.2), -sz[1]], [sz[0] / 2, 0, 0]
    if t == "hull":
        x = _vec(p.get("x"), 2) or [-10, 10]
        half = _num(p.get("half"), 5)
        return [x[0], _num(p.get("bottom"), 0), -half], [x[1], _num(p.get("top"), 10), half]
    if t in ("tank_c", "vessel", "pipe_dw"):
        ln = _num(p.get("len"), 4) / 2 + (_num(p.get("head"), r / 2) if t == "tank_c" else 0)
        rr = _num(p.get("r_out"), r) if t == "pipe_dw" else r
        return [-ln, -rr, -rr], [ln, rr, rr]
    if t in ("sphere", "tank_sphere"):
        return [-r, -r, -r], [r, r, r]
    if t == "cylinder":
        ln, ax = _num(p.get("len"), 1) / 2, str(p.get("axis") or "y")
        lo, hi = [-r, -r, -r], [r, r, r]
        k = "xyz".index(ax) if ax in "xyz" else 1
        lo[k], hi[k] = -ln, ln
        return lo, hi
    if t in ("pipe", "hose", "flow"):
        pts = [q for q in (_vec(x) for x in p.get("path") or []) if q]
        return pts or None
    if t in ("dimension", "arrow"):
        return [q for q in (_vec(p.get("a")), _vec(p.get("b"))) if q] or None
    if t == "limit_box":
        lo, hi = _vec(p.get("min")), _vec(p.get("max"))
        return [lo, hi] if lo and hi else None
    if t == "vent_mast":
        return [-0.5, 0, -0.5], [0.5, _num(p.get("h"), 8), 0.5]
    if t == "person":
        return [-0.3, 0, -0.3], [0.3, _num(p.get("h"), 1.8), 0.3]
    if t == "gas":
        a = _vec(p.get("area"), 4)
        if a:
            return [a[0], 0, a[1]], [a[2], _num(p.get("to"), 2), a[3]]
    return [-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]


def _corners(lo, hi):
    return [[(hi if i & 1 else lo)[0], (hi if i & 2 else lo)[1], (hi if i & 4 else lo)[2]] for i in range(8)]


def scene_points(spec):
    """the points that bound a 3D kit scene: its "box", else every part's box (scaled, turned round the vertical, moved to
    its "at") and every label's place"""
    box = _vec(spec.get("box"), 6)
    if box:
        return _corners(box[:3], box[3:])
    pts = []
    parts = spec.get("parts") or []
    for p in parts.values() if isinstance(parts, dict) else parts:
        if not isinstance(p, dict):
            continue
        got = _local_box(p)
        if not got:
            continue
        local = _corners(*got) if len(got) == 2 and not isinstance(got[0][0], list) and p.get("type") not in (
            "pipe", "hose", "flow", "dimension", "arrow") else got
        sc = p.get("scale")
        sc = _vec(sc) or [_num(sc, 1.0)] * 3
        rot = math.radians(_num(p.get("rot")))
        at = _vec(p.get("at")) or [0.0, 0.0, 0.0]
        c, s = math.cos(rot), math.sin(rot)
        for x, y, z in local:
            x, y, z = x * sc[0], y * sc[1], z * sc[2]
            pts.append([at[0] + x * c + z * s, at[1] + y, at[2] - x * s + z * c])
    for lab in spec.get("labels") or []:
        q = _vec((lab or {}).get("at")) if isinstance(lab, dict) else None
        if q:
            pts.append(q)
    return pts


def kit3d_aspect(spec):
    """a 3D kit scene's width over its height as its home view shows it (kit3d.js basis: the spec's view az / el) - None
    when it has nothing to measure"""
    pts = scene_points(spec or {})
    if len(pts) < 2:
        return None
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    view = spec.get("view") or {}
    az, el = math.radians(_num(view.get("az"), 30)), math.radians(_num(view.get("el"), 24))
    d = [math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)]
    f = [-x for x in d]
    r = [f[1] * 0 - f[2] * 1, f[2] * 0 - f[0] * 0, f[0] * 1 - f[1] * 0]       # f x up
    n = math.sqrt(sum(x * x for x in r)) or 1.0
    r = [x / n for x in r]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    xs = [sum(a * b for a, b in zip(q, r)) for q in _corners(lo, hi)]
    ys = [sum(a * b for a, b in zip(q, u)) for q in _corners(lo, hi)]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    return w / h if h > 1e-6 else None


JSON_DATA = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.S)


def figure_aspect(fig):
    """the natural shape of a figure as it goes into the page: a 3D kit scene's home view, a kit or 2D-kit drawing's size,
    an SVG's viewBox - None when it has none"""
    if " data-kit3d=" in (fig or ""):
        for m in JSON_DATA.finditer(fig):
            try:
                return kit3d_aspect(json.loads(m.group(1).replace("<\\/", "</")))
            except ValueError:
                continue
    import layout_fit
    return layout_fit.aspect(fig)


# ------------------------------------------------------------------ what a slide fits
def budget(key):
    """a blueprint's budget: a number, or a key of layout-templates.json "budgets" (measured)"""
    return key if isinstance(key, (int, float)) else BUDGETS.get(key)


def band_budget(variant, family):
    """(words, what) the words under (figure-top) or over (figure-bottom) a band hold - measured, budgets"""
    if family in ("photo", "tiles"):
        return (BUDGETS["under_top_row"], "under the photographs on top") if variant == "figure-top" else \
            (BUDGETS["over_photo_row"], "over the photographs at the foot")
    return (BUDGETS["under_band"], "under a picture band") if variant == "figure-top" else \
        (BUDGETS["over_band"], "over a picture band")


def aspect_score(rng, aspect, hard):
    """how well a picture of this shape sits in a box made for rng [lo, hi]: 1 inside, less the further out (None: it
    cannot - a band is never given a picture that is not wide); an unknown shape (a picture still to be drawn) 0.7"""
    if aspect is None:
        return 0.7
    lo, hi = rng
    if lo <= aspect <= hi:
        return 1.0
    if hard or aspect <= 0:
        return None
    return max(0.1, 1 - 1.2 * abs(math.log(aspect / (lo if aspect < lo else hi))))


def jitter(seed, *keys):
    """a number in [0, 1) fixed by the seed and the keys - the near-equal choice, the same on every build"""
    h = hashlib.sha1(("|".join([str(seed)] + [str(k) for k in keys])).encode("utf-8")).hexdigest()
    return int(h[:12], 16) / float(16 ** 12)


def options(own_bp, words=0, family=None, aspect=None, names=0, part_words=None, fixed=None, seed="", sid=""):
    """([{"bp", "shape", "cost"}], {shape: why not}) - the blueprints a teaching slide built as own_bp fits, cheapest first:
    every blueprint of its group (blueprints/*.json "fits") that takes its picture (family: photo, tiles, drawing, 3d) and
    its words (part_words: its largest part, when they are in parts), whose box suits the picture's shape (aspect, None
    while it is not drawn yet) and that shows its names. The cost: 0 a perfect fit, up to 10, and a seeded fraction that
    settles near-equal fits. fixed: why the slide keeps its own blueprint."""
    own = LIB.get(own_bp) or {}
    own_shape = own.get("shape") or "beside"
    group = (own.get("fits") or {}).get("group")
    why = {}
    if fixed or not group or not family:
        why.update({s: fixed or ("no picture" if not family else "its template, %s, has a layout of its own" % own_bp.split(".")[0])
                    for s in ORDER if s != own_shape})
        return [{"bp": own_bp, "shape": own_shape, "cost": 0.0}], why
    out = []
    for bid, b in LIB.items():
        f = b.get("fits") or {}
        if f.get("group") != group:
            continue
        shape, no, stage = b.get("shape"), None, 0
        w = part_words if part_words is not None and group == "parts" else words
        most = budget((f.get("budget") or {}).get(family))
        lo, hi = f.get("words") or [0, 999]
        if family not in (f.get("pictures") or []):
            no = "takes no %s" % family
        elif f.get("ground") == "dark" and bid != own_bp:
            no = "on the dark ground"
        elif not lo <= words <= hi:
            no = "for %d-%d words" % (lo, hi)
        elif most is not None and w > most:
            no, stage = "%d words, it holds %d" % (w, most), 2
        elif f.get("names") and names > f["names"]:
            no, stage = "%d names on the picture, it shows %d" % (names, f["names"]), 3
        sc = None
        if not no:
            sc = aspect_score((f.get("aspect") or {}).get(family) or [0, 99], aspect, f.get("hard"))
            if sc is None:
                no, stage = "the picture is %.1f:1, its box is for %s:1" % (aspect, "-".join("%g" % x for x in f["aspect"][family])), 4
        if no and bid != own_bp:
            if stage >= why.get(shape, (-1, ""))[0]:          # the reason of the blueprint that came nearest to fitting
                why[shape] = (stage, "%s - %s" % (bid, no))
            continue
        cost = round((1 - (sc if sc is not None else 0.0)) * 10) + 0.9 * jitter(seed, sid, bid)
        out.append({"bp": bid, "shape": shape, "cost": cost})
    if not any(o["bp"] == own_bp for o in out):
        out.append({"bp": own_bp, "shape": own_shape, "cost": 10.0})
    out.sort(key=lambda o: o["cost"])
    why = {s: w[1] for s, w in why.items() if s not in {o["shape"] for o in out}}
    for s in ORDER:
        if s not in {o["shape"] for o in out} and s not in ("words", "two"):     # a picture slide is never words-only
            why.setdefault(s, "no blueprint of its kind")
    return out, why


def way(bp, family):
    """(template, variant, composition, picture first) that builds a slide in the blueprint bp - the compiler's own names"""
    b = LIB[bp]
    tid, var, shape = b["template"], b["variant"], b.get("shape")
    photo = family == "photo"
    first = var == "figure-left" or b.get("mirror") is not None and var != "figure-right"
    if shape in ("top", "bottom"):
        return tid, var, "wide-left" if photo else "two-col", False
    if shape == "stage" or tid == "figure-stage":
        return tid, var, "stage", False
    if shape == "photo-full" or var == "split":
        return tid, var, "photo", False
    if var == "figure-tall":
        return tid, var, "two-col", first
    return tid, var, "wide-left" if photo else "two-col", first


# ------------------------------------------------------------------ the plan
def _breaks(items, teach):
    """the teaching slides that follow a slide that is not one (a task launch, the recap): a run starts again there"""
    return {b for a, b in zip(teach, teach[1:]) if b - a > 1}


def _shape_opts(item):
    """[(shape, cost, option)] - the cheapest blueprint of each shape the slide fits, cheapest shape first"""
    best = {}
    for o in item.get("options") or [{"bp": None, "shape": item["own"], "cost": 0.0}]:
        if o["shape"] not in best or o["cost"] < best[o["shape"]]["cost"]:
            best[o["shape"]] = o
    return sorted(((s, o["cost"], o) for s, o in best.items()), key=lambda x: x[1])


def _dp(items, teach, opts, cap, breaks):
    """the choice with the fewest repeats, then the fewest beside past cap, then the best fits - (cost, {index: option})"""
    states = {(None, 0): ((0, 0, 0.0), ())}
    for i in teach:
        nxt = {}
        echo = bool(items[i].get("echo"))
        for (prev, nb), (cost, path) in states.items():
            prev = None if i in breaks else prev
            for s, c, o in opts[i]:
                rep = 1 if s == prev and not echo else 0
                over = 1 if s == "beside" and nb >= cap else 0
                cc = (cost[0] + rep, cost[1] + over, round(cost[2] + c, 6))
                key = (s, min(cap, nb + (s == "beside")))
                if key not in nxt or cc < nxt[key][0]:
                    nxt[key] = (cc, path + (o,))
        states = nxt
    cost, path = min(states.values(), key=lambda x: x[0]) if states else ((0, 0, 0.0), ())
    return cost, dict(zip(teach, path))


def score(items, choice, rules=None):
    """{"repeats": [(index before, index)], "beside", "teaching", "cap", "shapes", "missing"} of a choice {index: shape}"""
    r = dict(PLAN, **(rules or {}))
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    reps = [(a, b) for a, b in zip(teach, teach[1:]) if b not in brk and choice[a] == choice[b] and not items[b].get("echo")]
    n = len(teach)
    shapes = sorted({choice[i] for i in teach}, key=lambda s: ORDER.index(s) if s in ORDER else 99)
    want = r["min_shapes"] if n >= r["min_slides"] else 0
    return {"repeats": reps, "beside": sum(1 for i in teach if choice[i] == "beside"), "teaching": n,
            "cap": int(math.ceil(n * r["beside_share"])), "shapes": shapes, "missing": max(0, want - len(shapes))}


def plan(items, rules=None):
    """{index: the chosen option {"bp", "shape", "cost"}} for the teaching slides of `items` (in deck order: {"id", "own"
    (its own shape, "" for a slide that is not a teaching slide), "options" (options()), "why", "fixed", "echo" (a
    comparison)})"""
    r = dict(PLAN, **(rules or {}))
    teach = [i for i, it in enumerate(items) if it.get("own")]
    if not teach:
        return {}
    brk = _breaks(items, teach)
    opts = {i: _shape_opts(items[i]) for i in teach}
    cap = int(math.ceil(len(teach) * r["beside_share"]))
    cost, choice = _dp(items, teach, opts, cap, brk)
    if len(teach) >= r["min_slides"]:
        # too few shapes: a shape not used yet is given to the slide where it costs least, and that slide keeps it - each
        # round fixes one more slide, so a shape the new plan drops is given back in the next round
        while True:
            used = {choice[i]["shape"] for i in teach}
            if len(used) >= r["min_shapes"]:
                break
            best = None
            for i in teach:
                for s, c, o in opts[i]:
                    if s in used or len(opts[i]) == 1:
                        continue
                    cc, ch = _dp(items, teach, {**opts, i: [(s, c, o)]}, cap, brk)
                    n = len({ch[j]["shape"] for j in teach})
                    if cc[:2] <= cost[:2] and n >= len(used) and (best is None or (-n, cc) < (-best[3], best[0])):
                        best = (cc, ch, (i, (s, c, o)), n)
            if not best:
                break
            cost, choice = best[0], best[1]
            opts[best[2][0]] = [best[2][1]]
    return choice


def shapes_of(choice):
    return {i: o["shape"] for i, o in choice.items()}


def notes(items, choice, rules=None):
    """the plan's notes: each rule it could not keep, naming the slides that fit one shape only and why"""
    sh = shapes_of(choice)
    sc = score(items, sh, rules)
    out = []

    def why(i, shape):
        it = items[i]
        if it.get("fixed"):
            return "%s keeps its %s shape - %s" % (it["id"], shape, it["fixed"])
        w = it.get("why") or {}
        no = ["%s: %s" % (s, w[s]) for s in ORDER if s != shape and w.get(s)]
        return "%s fits only %s (%s)" % (it["id"], shape, "; ".join(no) if no else "no other shape")
    for a, b in sc["repeats"]:
        out.append("%s and %s are both %s - %s; %s" % (items[a]["id"], items[b]["id"], sh[b], why(a, sh[a]), why(b, sh[b])))
    if sc["beside"] > sc["cap"]:
        only = [i for i, s in sh.items() if s == "beside" and len(_shape_opts(items[i])) == 1]
        out.append("beside on %d of %d teaching slides (at most about %d): %s" % (
            sc["beside"], sc["teaching"], sc["cap"], "; ".join(why(i, "beside") for i in only[:8]) + (" ..." if len(only) > 8 else "")))
    if sc["missing"]:
        out.append("%d shape(s) in %d teaching slides (%s; at least %d) - no other slide fits another shape" % (
            len(sc["shapes"]), sc["teaching"], ", ".join(sc["shapes"]), len(sc["shapes"]) + sc["missing"]))
    return out


def line(items, shapes):
    """the plan as one line: each teaching slide's shape in deck order, "|" where a task launch or the recap breaks the run"""
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    out = []
    for i in teach:
        if i in brk and out:
            out.append("|")
        out.append(shapes.get(i, items[i]["own"]))
    return " ".join(out)


def summary(items, shapes, rules=None):
    """'beside top words ... - longest run 2 (s05-s06 top), beside 14 of 31 (45 %), 5 shapes' for {index: shape}"""
    sc = score(items, shapes, rules)
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    best, run, start, at = 0, 0, None, None
    for k, i in enumerate(teach):
        same = k and i not in brk and shapes[teach[k - 1]] == shapes[i]
        run = run + 1 if same else 1
        start = start if same else i
        if run > best:
            best, at = run, (start, i)
    where = " (%s-%s %s)" % (items[at[0]]["id"], items[at[1]]["id"], shapes[at[1]]) if best > 1 else ""
    return "%s - longest run %d%s, beside %d of %d (%d %%), %d shapes" % (
        line(items, shapes), best, where, sc["beside"], sc["teaching"],
        round(100.0 * sc["beside"] / sc["teaching"]) if sc["teaching"] else 0, len(sc["shapes"]))


def stats(items, shapes):
    """the scorecard's numbers: {"look_shapes", "same_look_in_a_row", "beside_share"} for {index: shape}"""
    sc = score(items, shapes)
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    best = run = 0
    for k, i in enumerate(teach):
        run = run + 1 if k and i not in brk and shapes[teach[k - 1]] == shapes[i] else 1
        best = max(best, run)
    return {"look_shapes": len(sc["shapes"]), "same_look_in_a_row": best,
            "beside_share": round(100.0 * sc["beside"] / sc["teaching"]) if sc["teaching"] else 0}


# ------------------------------------------------------------------ a built deck
def deck_items(page):
    """the plan's items read back from a compiled deck: each slide's shape (its template and variant), the shapes it fit
    (data-shapes, written by the compiler) and whether it is a comparison"""
    out = []
    for m in SECTION.finditer(page or ""):
        a = m.group(1)
        if not re.search(r'\bclass="[^"]*\bslide\b', a):
            continue
        t = re.search(r'\bdata-template="([\w-]+)\.v\d+"', a)
        v = re.search(r'\bdata-variant="([\w-]+)"', a)
        i = re.search(r'\bid="([^"]+)"', a)
        own = (shape_of(t.group(1), v.group(1) if v else "") if t else "") or ""
        sh = re.search(r'\bdata-shapes="([^"]*)"', a)
        ok = (sh.group(1).split() if sh else []) or [own]
        vis = re.search(r'\bdata-visual="([\w-]+)"', a)
        title = re.search(r'\bdata-title="([^"]*)"', a)
        out.append({"id": i.group(1) if i else "", "own": own,
                    "options": [{"bp": None, "shape": s, "cost": 0.0 if s == own else 1.0} for s in dict.fromkeys([own] + ok) if s],
                    "echo": comparison(t.group(1) if t else "", vis.group(1) if vis else "", html.unescape(title.group(1)) if title else "")})
    return out


def deck_shapes(page):
    """(items, {index: shape}) of a compiled deck as it is built"""
    items = deck_items(page)
    return items, {i: it["own"] for i, it in enumerate(items) if it["own"]}


def problems(page, rules=None):
    """the shape rules a compiled deck breaks while the plan had another way that keeps them - each a must-fix line"""
    items, now = deck_shapes(page)
    if not now:
        return []
    a, b = score(items, now, rules), score(items, shapes_of(plan(items, rules)), rules)
    out = []
    if len(a["repeats"]) > len(b["repeats"]):
        out.append("the same shape twice in a row where the slides fit another: %s" % ", ".join(
            "%s-%s %s" % (items[x]["id"], items[y]["id"], now[y]) for x, y in a["repeats"]))
    if a["beside"] > a["cap"] and b["beside"] < a["beside"]:
        out.append("beside on %d of %d teaching slides (at most about %d) where %d could take another shape"
                   % (a["beside"], a["teaching"], a["cap"], a["beside"] - b["beside"]))
    if a["missing"] > b["missing"]:
        out.append("%d shape(s) (%s) in %d teaching slides where the slides fit %d" % (
            len(a["shapes"]), ", ".join(a["shapes"]), a["teaching"], len(b["shapes"])))
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(__doc__)
        return 2
    p = args[0]
    for c in (p, os.path.join(p, "presentation", "index.html"), os.path.join(p, "index.html")):
        if os.path.isfile(c):
            p = c
            break
    else:
        print("Stopped - no deck at %s" % args[0])
        return 2
    page = io.open(p, encoding="utf-8").read()
    items, now = deck_shapes(page)
    print(summary(items, now))
    bad = problems(page)
    for x in bad:
        print("  MUST FIX: " + x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
