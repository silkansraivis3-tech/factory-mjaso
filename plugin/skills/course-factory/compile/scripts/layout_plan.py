#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""layout_plan - the deck's shapes, planned over the whole module (course-module-ui layout-templates.json "shapes").

A slide's look is its shape - where its picture sits against its words - not its template's name: a picture on the left
and one on the right are one look (beside). Each teaching slide fits some shapes (its words within that shape's budget,
its picture's natural shape, the names it shows); plan() chooses among them for the whole deck so that the same shape
never comes twice in a row, beside is at most about half of the teaching slides, and a module of ten teaching slides or
more uses at least four shapes - changing as few slides as it can. A slide whose build sheet names its layout keeps it,
and so does a slide that fits only one shape. Words are never cut or moved: only the shapes a slide fits are chosen.

    python layout_plan.py <deck index.html | module folder>     the deck's shape line, its longest run and its beside share
    python test_layout_plan.py
"""
from __future__ import annotations

import html
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
LT = json.load(io.open(os.path.join(SKILLS, "course-module-ui", "knowledge", "layout-templates.json"), encoding="utf-8"))
SH = LT["shapes"]
MAP, ORDER, PLAN = SH["map"], SH["order"], SH["plan"]
BAND_TEMPLATES, BAND_ASPECT, BAND_NAMES = tuple(SH["band_templates"]), SH["band_aspect"], SH["band_names"]
BUDGETS = LT["budgets"]
STAGE_WORDS = LT["variety"]["stage_max_words"]
DENSE_WORDS = LT["dense"]["words"]
TOP_ASPECT, TOP_ROW = LT["boxes"]["top_aspect"], LT["boxes"]["top_row_aspect"]
FULL_NAMES = LT["boxes"]["need"][-1][0]           # names that need the whole slide: no box beside words shows them
MOVABLE = BAND_TEMPLATES + ("figure-stage", "photo-explain")
RIGHT = {"explain-figure": "figure-right", "reading-with-figure": "figure-right", "long-explanation": "model",
         "procedure": "with-figure", "content-in-parts": "with-figure"}
COMPARISON = re.compile(r"(?i)\b(compar\w*|versus|vs\.?|before\s*(?:and|/|&)\s*after)(?!\w)")
SECTION = re.compile(r"<section\b([^>]*)>", re.S)


def shape_of(tid, variant):
    """the shape of a template and variant: beside, top, bottom, stage, photo-full, words, two - "" for a slide that is not
    a teaching slide (a task launch, the recap), None for one the map does not know"""
    return MAP.get("%s.%s" % (tid, variant))


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
def band_budget(variant, family):
    """(words, what) the words under (figure-top) or over (figure-bottom) a band hold - measured, budgets"""
    if family in ("photo", "tiles"):
        return (BUDGETS["under_top_row"], "under the photographs on top") if variant == "figure-top" else \
            (BUDGETS["over_photo_row"], "over the photographs at the foot")
    return (BUDGETS["under_band"], "under a picture band") if variant == "figure-top" else \
        (BUDGETS["over_band"], "over a picture band")


def fits(own, tid, words, family=None, aspect=None, names=0, part_words=None, fixed=None):
    """{shape: None when the slide fits it, else why not} for a teaching slide built as `tid` in the shape `own`, with
    `words` words (part_words: its largest part, when its words are in parts), a picture of `family` (photo, tiles, drawing,
    3d; None - no picture) whose natural shape is `aspect` (None: not known yet - a picture still to be drawn is drawn for
    the shape it gets) and that shows `names` names at once. fixed: why the slide keeps its own shape."""
    out = {own: None}
    for s in ORDER:
        if s == own:
            continue
        if fixed:
            out[s] = fixed
        elif not family:
            out[s] = "no picture"
        elif tid not in MOVABLE:
            out[s] = "its template, %s, has a layout of its own" % tid
        elif s == "beside":
            out[s] = None if words <= BUDGETS["beside_picture"] and names < FULL_NAMES else \
                ("%d words, beside a picture %d" % (words, BUDGETS["beside_picture"]) if names < FULL_NAMES
                 else "%d names on the picture need the whole slide" % names)
        elif s in ("top", "bottom"):
            fam = "photo" if family == "tiles" else family
            most, what = band_budget("figure-top" if s == "top" else "figure-bottom", family)
            need = BAND_ASPECT.get(fam, BAND_ASPECT["drawing"])
            w = part_words or words
            out[s] = ("the picture is %.1f:1, a band needs %.2g:1" % (aspect, need)) if aspect is not None and aspect < need else \
                ("%d words, %s %d" % (w, what, most)) if w > most else \
                ("%d names on the picture, a band shows %d" % (names, BAND_NAMES)) if names > BAND_NAMES else None
        elif s == "stage":
            out[s] = "its words are in parts" if part_words else "several photographs" if family == "tiles" else \
                ("%d words, the stage holds %d" % (words, STAGE_WORDS)) if words > STAGE_WORDS else None
        elif s == "photo-full":
            out[s] = "not a photograph" if family != "photo" else "its words are in parts" if part_words else \
                ("%d words, on a full-screen photograph %d" % (words, BUDGETS["photo_full"])) if words > BUDGETS["photo_full"] else None
        else:
            out[s] = "a shape of its own template"
    return out


def way(shape, tid, words, family):
    """(template, variant, composition) that builds a slide of the template tid in `shape` - the compiler's own names"""
    three_d, photo = family == "3d", family == "photo"
    side = "long-explanation" if three_d and words > DENSE_WORDS else "reading-with-figure" if words > DENSE_WORDS else "explain-figure"
    if shape in ("top", "bottom"):
        return (tid if tid in BAND_TEMPLATES else side), "figure-top" if shape == "top" else "figure-bottom", \
            "wide-left" if photo else "two-col"
    if shape == "beside":
        if tid in RIGHT:
            return tid, RIGHT[tid], "wide-left" if photo else "two-col"
        return ("photo-explain", "column", "wide-left") if photo else (side, RIGHT[side], "two-col")
    if shape == "stage":
        return "figure-stage", "figure", "stage"
    if shape == "photo-full":
        return "photo-explain", "full", "photo"
    return None


# ------------------------------------------------------------------ the plan
def _breaks(items, teach):
    """the teaching slides that follow a slide that is not one (a task launch, the recap): a run starts again there"""
    return {b for a, b in zip(teach, teach[1:]) if b - a > 1}


def _dp(items, teach, opts, cap, breaks):
    """the choice with the fewest repeats, then the fewest beside past cap, then the fewest slides changed and the most
    preferred shapes - (cost, {index: shape})"""
    states = {(None, 0): ((0, 0, 0, 0), ())}
    for i in teach:
        nxt = {}
        echo = bool(items[i].get("echo"))
        for (prev, nb), (cost, path) in states.items():
            prev = None if i in breaks else prev
            for k, s in enumerate(opts[i]):
                rep = 1 if s == prev and not echo else 0
                over = 1 if s == "beside" and nb >= cap else 0
                c = (cost[0] + rep, cost[1] + over, cost[2] + (1 if k else 0), cost[3] + k)
                key = (s, min(cap, nb + (s == "beside")))
                if key not in nxt or c < nxt[key][0]:
                    nxt[key] = (c, path + (s,))
        states = nxt
    cost, path = min(states.values()) if states else ((0, 0, 0, 0), ())
    return cost, dict(zip(teach, path))


def options(item, rules=None):
    """the shapes a slide may be given, its own first, then the others it fits in the order the plan prefers them"""
    r = dict(PLAN, **(rules or {}))
    own = item["own"]
    if item.get("fixed"):
        return [own]
    ok = [s for s, why in (item.get("fits") or {}).items() if why is None]
    out = [own]
    for s in list(r["prefer"]) + ORDER:
        if s in ok and s not in out:
            out.append(s)
    return out


def score(items, choice, rules=None):
    """{"repeats": [(index before, index)], "beside", "teaching", "cap", "shapes", "missing"} of a choice {index: shape}"""
    r = dict(PLAN, **(rules or {}))
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    reps = [(a, b) for a, b in zip(teach, teach[1:]) if b not in brk and choice[a] == choice[b] and not items[b].get("echo")]
    n = len(teach)
    shapes = sorted({choice[i] for i in teach}, key=ORDER.index)
    want = r["min_shapes"] if n >= r["min_slides"] else 0
    return {"repeats": reps, "beside": sum(1 for i in teach if choice[i] == "beside"), "teaching": n,
            "cap": int(math.ceil(n * r["beside_share"])), "shapes": shapes, "missing": max(0, want - len(shapes))}


def plan(items, rules=None):
    """{index: shape} for the teaching slides of `items` (in deck order: {"id", "own" (its shape, "" for a slide that is
    not a teaching slide), "fits" {shape: None or why not}, "fixed" (why it keeps its own), "echo" (a comparison)})"""
    r = dict(PLAN, **(rules or {}))
    teach = [i for i, it in enumerate(items) if it.get("own")]
    if not teach:
        return {}
    brk = _breaks(items, teach)
    opts = {i: options(items[i], r) for i in teach}
    cap = int(math.ceil(len(teach) * r["beside_share"]))
    cost, choice = _dp(items, teach, opts, cap, brk)
    if len(teach) >= r["min_slides"]:
        while True:
            used = {choice[i] for i in teach}
            if len(used) >= r["min_shapes"]:
                break
            best = None
            for s in list(r["prefer"]) + ORDER:
                if s in used:
                    continue
                for i in teach:
                    if s not in opts[i][1:] or choice[i] == s:
                        continue
                    c, ch = _dp(items, teach, dict(opts, **{i: [s]}), cap, brk)
                    if c[:2] <= cost[:2] and len({ch[j] for j in teach}) > len(used) and (best is None or c < best[0]):
                        best = (c, ch, i, s)
            if not best:
                break
            cost, choice = best[0], best[1]
            opts[best[2]] = [best[3]]
    return choice


def notes(items, choice, rules=None):
    """the plan's notes: each rule it could not keep, naming the slides that fit only one shape and why"""
    sc = score(items, choice, rules)
    out = []

    def why(i, shape):
        it = items[i]
        if it.get("fixed"):
            return "%s keeps its %s shape - %s" % (it["id"], shape, it["fixed"])
        f = it.get("fits") or {}
        no = ["%s: %s" % (s, f[s]) for s in ORDER if s != shape and f.get(s)]
        return "%s fits only %s (%s)" % (it["id"], shape, "; ".join(no) if no else "no other shape")
    for a, b in sc["repeats"]:
        out.append("%s and %s are both %s - %s; %s" % (items[a]["id"], items[b]["id"], choice[b], why(a, choice[a]), why(b, choice[b])))
    if sc["beside"] > sc["cap"]:
        only = [i for i, s in choice.items() if s == "beside" and len(options(items[i], rules)) == 1]
        out.append("beside on %d of %d teaching slides (at most about %d): %s" % (
            sc["beside"], sc["teaching"], sc["cap"], "; ".join(why(i, "beside") for i in only[:8]) + (" ..." if len(only) > 8 else "")))
    if sc["missing"]:
        out.append("%d shape(s) in %d teaching slides (%s; at least %d) - no other slide fits another shape" % (
            len(sc["shapes"]), sc["teaching"], ", ".join(sc["shapes"]), len(sc["shapes"]) + sc["missing"]))
    return out


def line(items, choice):
    """the plan as one line: each teaching slide's shape in deck order, "|" where a task launch or the recap breaks the run"""
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    out = []
    for i in teach:
        if i in brk and out:
            out.append("|")
        out.append(choice.get(i, items[i]["own"]))
    return " ".join(out)


def summary(items, choice, rules=None):
    """'beside top words ... - longest run 2 (s05-s06 top), beside 14 of 31 (45 %), 5 shapes'"""
    sc = score(items, choice, rules)
    teach = [i for i, it in enumerate(items) if it.get("own")]
    brk = _breaks(items, teach)
    best, run, start, at = 0, 0, None, None
    for k, i in enumerate(teach):
        same = k and i not in brk and choice[teach[k - 1]] == choice[i]
        run = run + 1 if same else 1
        start = start if same else i
        if run > best:
            best, at = run, (start, i)
    where = " (%s-%s %s)" % (items[at[0]]["id"], items[at[1]]["id"], choice[at[1]]) if best > 1 else ""
    return "%s - longest run %d%s, beside %d of %d (%d %%), %d shapes" % (
        line(items, choice), best, where, sc["beside"], sc["teaching"],
        round(100.0 * sc["beside"] / sc["teaching"]) if sc["teaching"] else 0, len(sc["shapes"]))


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
        own = shape_of(t.group(1), v.group(1) if v else "") if t else ""
        sh = re.search(r'\bdata-shapes="([^"]*)"', a)
        ok = (sh.group(1).split() if sh else []) or [own]
        vis = re.search(r'\bdata-visual="([\w-]+)"', a)
        title = re.search(r'\bdata-title="([^"]*)"', a)
        out.append({"id": i.group(1) if i else "", "own": own or "", "fits": {s: (None if s in ok else "-") for s in ORDER},
                    "echo": comparison(t.group(1) if t else "", vis.group(1) if vis else "", html.unescape(title.group(1)) if title else "")})
        out[-1]["fits"][own or ""] = None
    return out


def problems(page, rules=None):
    """the shape rules a compiled deck breaks while the plan had another way that keeps them - each a must-fix line"""
    items = deck_items(page)
    teach = [i for i, it in enumerate(items) if it["own"]]
    if not teach:
        return []
    now = {i: items[i]["own"] for i in teach}
    a, b = score(items, now, rules), score(items, plan(items, rules), rules)
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
    items = deck_items(page)
    teach = [i for i, it in enumerate(items) if it["own"]]
    print(summary(items, {i: items[i]["own"] for i in teach}))
    bad = problems(page)
    for x in bad:
        print("  MUST FIX: " + x)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
