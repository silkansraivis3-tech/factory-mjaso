#!/usr/bin/env python3
"""kit_meaning.py - does a figure-kit spec MEAN what a seafarer would see? (2.66.0, run by check_kit.py spec, every build)

Every check before 2.66.0 was about LOOK (overlap, contrast, size, fit), and "module clean" meant those passed - so the
2.65.0 IGF M01-M03 build drew a vent mast inside the hull, a "Bunkering station" that was only words, pipes ending in the
air, a water curtain hanging from nothing, six fuel names over one tank. These are build FAILs now, judged on the geometry
kit.js itself resolves (kit_relate.py), against course-visuals/knowledge/figure-truths.json:

  NAMED      words on the figure, a part's label or a step's title name a thing the figure does not draw (or not there)
  LOOSE END  a pipe or hose end that meets no part, port or other pipe
  INSIDE     a deck-mounted part (vent mast, manifold, hatch) inside the hull; a tank across the deck line
  NO GAS     a vent the words say vents (or a relief valve that lifts) with no step that lets gas out of its outlet
  AIM        a spray aimed at nothing; a water curtain or a detector attached to nothing
  LEADER     a callout's leader ending on nothing; words floating with nothing drawn near them
  GRID       a row of captions with a drawing under only some of them; a table of words with one drawing
  MODES      engine-mode captions not each over its own engine / cylinder
  SMALL      a small drawing lost in a big panel part (the figure's frame: the drawing audit's EMPTY)
  TRUTH      the figure kind's own must-be-true list (ship plan, bunkering line, vent system, fuel supply, engine modes,
             fuel types) - figure-truths.json "figures"
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit_relate  # noqa: E402

TRUTHS_PATH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "knowledge", "figure-truths.json")
_TRUTHS = None

CONTAINERS = ("ga", "space", "zone", "panel")
WORDLESS = ("text", "pipe", "hose", "wire")
CHARTS = ("scale", "bands", "range_bar", "composition_bar", "curve_chart", "flammability", "tree", "step_track", "log")
INSTRUMENTS = ("gauge", "level", "readout", "panel", "log", "well", "badge") + CHARTS
NEAR = 80          # a free text this close to its part names it
FLOAT = 80         # words further than this from anything drawn float
EDGE = 40          # a pipe end this close to the frame runs on off the picture (calibrated on the hand-fixed IGF figures)
LOOSE_FAR = 30     # a pipe end further than this from every part and pipe is on NOTHING (a BLOCK); nearer, a near miss (a NOTE)
AIM_FAR = 40       # a spray reaching, or a curtain hanging, further than this from every part aims at nothing (a BLOCK)
BLOCK, NOTE = "BLOCK", "NOTE"
MODIFIERS = ("cleaning|inspection|entry|pressure|level|top|bottom|temperature|types?|walls?|design|filling|venting|cooling|"
             "warming|inerting|room|space|area|zone|plan|data|capacity|contents|mode|modes|operation|rules?|code")
PORT = 9           # a pipe end this close to a port, or a part, meets it
TOUCH = 5          # a pipe end this close to another pipe meets it (a tee)


def truths():
    global _TRUTHS
    if _TRUTHS is None:
        _TRUTHS = json.load(io.open(TRUTHS_PATH, encoding="utf-8"))
    return _TRUTHS


# ------------------------------------------------------------------ geometry
def text_box(p):
    """the box of a text part's words, estimated (12.5 px caption, 16 a line; a heading wider)"""
    t = str(p.get("text") or "")
    ls = t.split("\n") or [""]
    k = 1.3 if p.get("style") == "h" else 1.0
    w = max(len(x) for x in ls) * 7.2 * k
    h = 16 * len(ls)
    x, y = float(p.get("x") or 0), float(p.get("y") or 0)
    a = p.get("anchor") or "middle"
    x0 = x - w / 2 if a == "middle" else x - w if a == "end" else x
    return [x0, y - 12, x0 + w, y - 12 + h]


def gap(a, b):
    """distance between two boxes (0 when they touch or overlap)"""
    dx = max(0.0, a[0] - b[2], b[0] - a[2])
    dy = max(0.0, a[1] - b[3], b[1] - a[3])
    return math.hypot(dx, dy)


def pt_box(p, b):
    return gap([p[0], p[1], p[0], p[1]], b)


def seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    L = (bx - ax) ** 2 + (by - ay) ** 2
    t = 0 if not L else max(0, min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / L))
    return math.hypot(p[0] - (ax + t * (bx - ax)), p[1] - (ay + t * (by - ay)))


def poly_dist(p, pts):
    if len(pts) == 1:
        return math.hypot(p[0] - pts[0][0], p[1] - pts[0][1])
    return min(seg_dist(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 1e9


def center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


# ------------------------------------------------------------------ words
def _rx(word):
    return re.compile(r"(?<![a-z0-9])" + re.escape(word) + r"(?:s|es)?(?![a-z0-9])")


def names_in(text, strict_only=False):
    """[(word, entry)] - the things these words name, longest phrase first, each stretch of words used once"""
    s = " " + re.sub(r"\s+", " ", str(text or "").lower().replace("‑", "-").replace("‐", "-")) + " "
    found, used = [], []
    allw = sorted(((w, e) for e in truths()["names"] for w in e["words"]), key=lambda x: -len(x[0]))
    for w, e in allw:                     # a loose name ("tank connection space") still uses its words up
        for m in _rx(w).finditer(s):
            if any(m.start() < b and a < m.end() for a, b in used):
                continue
            used.append((m.start(), m.end()))
            # "from the tank", "to the vaporizer": where a line comes from or goes, off the picture - not a thing drawn here
            if re.search(r"\b(?:from|to|towards|into)\s+(?:the\s+|a\s+|an\s+)?(?:[\w'’-]+\s+){0,2}$", s[:m.start()]):
                continue
            # "tank pressure", "tank cleaning": the word qualifies another - a reading, a task, a place - not the thing
            if re.match(r"\s+(?:%s)\b" % MODIFIERS, s[m.end():]):
                continue
            if e.get("strict") or not strict_only:
                found.append((w, e))
    return found


def words_of(spec):
    out = [str(spec.get("label") or "")]
    out += [str(s.get("title") or "") for s in spec.get("steps") or [] if isinstance(s, dict)]
    out += [str(p.get("text") or "") for p in spec.get("parts") or [] if isinstance(p, dict) and p.get("type") == "text"]
    out += [str(p.get("label") or "") for p in spec.get("parts") or [] if isinstance(p, dict) and isinstance(p.get("label"), str)]
    return " \n ".join(out).lower()


# ------------------------------------------------------------------ the values a figure's steps reach
def reached(spec):
    """{part id: the largest value it has at rest or after any step}, and [(step no, {id: value})] per step"""
    top, per = {}, []
    for p in spec.get("parts") or []:
        if isinstance(p, dict) and p.get("id") and isinstance(p.get("value"), (int, float)):
            top[p["id"]] = float(p["value"])
    for k, s in enumerate(spec.get("steps") or [], 1):
        if not isinstance(s, dict):
            continue
        now = {}
        for ref, v in (s.get("set") or {}).items():
            if isinstance(v, (int, float)):
                now[ref] = max(now.get(ref, -1e9), float(v))
        for a in s.get("play") or []:
            if isinstance(a, list) and len(a) >= 2 and isinstance(a[1], (int, float)):
                now[a[0]] = max(now.get(a[0], -1e9), float(a[1]))
        for m_part in spec.get("parts") or []:                       # moves a mark starts ("then")
            for m in (m_part.get("marks") or []) if isinstance(m_part, dict) else []:
                for a in m.get("then") or []:
                    if isinstance(a, list) and len(a) >= 2 and isinstance(a[1], (int, float)) and (m_part.get("id") in now):
                        now[a[0]] = max(now.get(a[0], -1e9), float(a[1]))
        per.append((k, now))
        for ref, v in now.items():
            top[ref] = max(top.get(ref, -1e9), v)
    return top, per


def states(spec):
    """[(step no, {id: value at the end of that step}, {id: the highest value it reaches DURING the step})] - each step from
    the end of the one before, a `reset` from rest; in a step the moves of one part queue up and the last wins; a value
    crossing a mark starts the mark's "then" moves (SPEC.md Marks: the relief valve a pressure mark lifts)"""
    rest, marks = {}, {}
    for p in spec.get("parts") or []:
        if isinstance(p, dict) and p.get("id"):
            rest[p["id"]] = float(p["value"]) if isinstance(p.get("value"), (int, float)) and not isinstance(p.get("value"), bool) else 0.0
            marks[p["id"]] = [m for m in p.get("marks") or [] if isinstance(m, dict) and isinstance(m.get("at"), (int, float))]
    now, out = dict(rest), []
    for k, s in enumerate(spec.get("steps") or [], 1):
        if not isinstance(s, dict):
            continue
        if s.get("reset"):
            now = dict(rest)
        during = {}
        moves = [(ref, v) for ref, v in (s.get("set") or {}).items() if isinstance(v, (int, float))]
        moves += [(a[0], a[1]) for a in s.get("play") or [] if isinstance(a, list) and len(a) >= 2 and isinstance(a[1], (int, float))]
        i = 0
        while i < len(moves) and i < 200:
            ref, v = moves[i]
            i += 1
            old = now.get(ref, 0.0)
            for m in marks.get(ref, []):
                up = m.get("dir", "up") != "down"
                if (up and old < m["at"] <= v) or (not up and old > m["at"] >= v):
                    moves += [(a[0], a[1]) for a in m.get("then") or [] if isinstance(a, list) and len(a) >= 2 and isinstance(a[1], (int, float))]
            now[ref] = float(v)
            during[ref] = max(during.get(ref, -1e9), float(v))
        out.append((k, dict(now), during))
    return out


# ------------------------------------------------------------------ the checks
class Fig:
    def __init__(self, spec, rspec, geo):
        self.spec, self.r, self.geo = spec, rspec, geo
        self.parts = [p for p in rspec.get("parts") or []]
        self.items = []                                  # (part, geometry) for every part
        for p, g in zip(self.parts, geo):
            if isinstance(p, dict) and g:
                if p.get("type") == "text":
                    g = dict(g, box=text_box(p))
                self.items.append((p, g))
        size = rspec.get("size") or [600, 400]
        self.W, self.H = float(size[0]), float(size[1])
        self.said, self.grid = set(), False             # captions a GRID finding already names

    def of(self, *types):
        return [(p, g) for p, g in self.items if p.get("type") in types]

    def drawn(self, containers=False):
        """the parts that draw a thing (not words, not pipes) - with the rooms and the ship when asked"""
        return [(p, g) for p, g in self.items if p.get("type") not in WORDLESS and g.get("box")
                and (containers or p.get("type") not in CONTAINERS)]

    def pipes(self):
        return [(p, g) for p, g in self.items if p.get("type") in ("pipe", "hose") and len(g.get("pts") or []) >= 2]

    def side_ships(self):
        return [(p, g) for p, g in self.items if p.get("type") == "ga" and g.get("ga") and not g["ga"].get("plan")]

    def ship_for(self, b):
        """the side-view ship a part at box b belongs to: over its length, between well above its deck and its keel"""
        cx, cy = center(b)
        best = None
        for p, g in self.side_ships():
            G = g["ga"]
            if g["box"][0] - 4 <= cx <= g["box"][2] + 4 and G["houseTop"] - 170 <= cy <= G["keel"] + 4:
                if best is None or abs(cy - G["deck"]) < abs(center(best[1]["box"])[1] - best[1]["ga"]["deck"]):
                    best = (p, g)
        return best


def components(F):
    """union-find over the drawn parts and the pipes: a pipe end on a part, a part sitting on a pipe, a pipe end on a pipe"""
    eq = [(i, p, g) for i, (p, g) in enumerate(F.items) if p.get("type") not in ("text", "wire") + CONTAINERS and (g.get("box") or g.get("pts"))]
    par = {i: i for i, _, _ in eq}

    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def u(a, b):
        par[f(a)] = f(b)

    pipes = [(i, p, g) for i, p, g in eq if g.get("pts")]
    things = [(i, p, g) for i, p, g in eq if g.get("box")]
    for i, p, g in pipes:
        ends = [g["pts"][0], g["pts"][-1]]
        for j, q, h in things:
            if any(pt_box(e, h["box"]) <= PORT for e in ends) or poly_dist(center(h["box"]), g["pts"]) <= 6 or \
                    any(poly_dist(pp[:2], g["pts"]) <= 4 for pp in (h.get("ports") or {}).values()):
                u(i, j)
        for j, q, h in pipes:
            if j != i and any(poly_dist(e, h["pts"]) <= TOUCH for e in ends):
                u(i, j)
    groups = {}
    for i, p, g in eq:
        groups.setdefault(f(i), set()).add(p.get("id") or "#%d" % i)
    return [s for s in groups.values()]


def connected(F, a_ids, b_ids):
    for comp in components(F):
        if comp & set(a_ids) and comp & set(b_ids):
            return True
    return False


def chk_named(F, bad):
    have = {}
    for p, g in F.items:
        have.setdefault(p.get("type"), []).append((p, g))
    rspec = F.r
    # words ON the figure: a free text names a thing drawn beside it; a callout's leader ends on it
    for p, g in F.of("text"):
        short = len(str(p.get("text") or "").split()) <= 4           # a label - a sentence says, it does not name a place
        for w, e in names_in(p.get("text"), strict_only=True):
            ok_parts = [(q, h) for t in e["parts"] for q, h in have.get(t, [])]
            what = "/".join(e["parts"][:3])
            if not ok_parts:                               # a kin part BESIDE the words may stand for it (a box on deck for
                kin = [t for t in e.get("kin") or [] for q, h in have.get(t, [])   # the bunkering station, a hose drawn as a pipe): a note
                       if gap(g["box"], h.get("box") or _pbox(h)) <= NEAR]
                bad("NAMED", "the words %r name the %s, and the figure draws none%s - draw it (type %s) and put the words on "
                    "it (\"for\": \"<its id>\"), or take the words out" % (str(p.get("text"))[:40], w,
                                                                           " (a %s stands for it)" % kin[0] if kin else "", what),
                    p, NOTE if kin else BLOCK)
                continue
            if p.get("to"):
                t = p["to"]
                if not any(pt_box(t, h["box"]) <= 14 for q, h in ok_parts if h.get("box")) and \
                        not any(poly_dist(t, h["pts"]) <= 8 for q, h in ok_parts if h.get("pts")):
                    bad("NAMED", "the callout %r (a %s) leads to (%g, %g), and no %s is there - point it at the part (\"for\": "
                        "\"<its id>\")" % (str(p.get("text"))[:40], w, t[0], t[1], what), p)
                continue
            near = [pt for pt in ok_parts if gap(g["box"], pt[1].get("box") or _pbox(pt[1])) <= NEAR]
            if not near and short:
                dmin = min(gap(g["box"], h.get("box") or _pbox(h)) for q, h in ok_parts)
                bad("NAMED", "the words %r stand %d units from the nearest %s - words that name a thing go on it: \"for\": "
                    "\"%s\" on the text (a callout), or move them beside it" % (str(p.get("text"))[:40], dmin, w,
                                                                                  ok_parts[0][0].get("id") or "its id"), p)
    # a part's own label naming a thing the part is not: a room called "Bunkering station" holds a manifold
    for p, g in F.items:
        lab = p.get("label")
        if p.get("type") in ("text",) + INSTRUMENTS or not isinstance(lab, str) or not g.get("box") or g.get("approx") \
                or len(lab.split()) > 4:
            continue                                       # a gauge reads "Tank pressure" - it names what it measures
        got = names_in(lab, strict_only=True)
        if any(p.get("type") in e["parts"] for w, e in got):
            continue                                       # "Tank valve" is a valve
        if p.get("type") == "space" and any(e.get("room") and re.search(_rx(w).pattern + r"\s*$", lab.lower()) for w, e in got):
            continue                                       # an "OIL FUEL TANK" drawn as a space IS a (structural) tank
        for w, e in got:
            inside = [q for t in e["parts"] for q, h in have.get(t, []) if h.get("box") and gap(h["box"], g["box"]) <= 12]
            if not inside:                                 # none anywhere: the thing is missing; elsewhere: the room may stand for it
                kin_in = [q for t in e.get("kin") or [] if t != p.get("type") for q, h in have.get(t, [])
                          if h.get("box") and gap(h["box"], g["box"]) <= 12 or h.get("pts") and gap(_pbox(h), g["box"]) <= 12]
                anywhere = any(have.get(t) for t in e["parts"]) or kin_in or \
                    (p.get("type") in (e.get("kin") or []) and not e.get("needs_inside"))
                bad("NAMED", "the %s %s is labelled %r - it names the %s, and none is drawn %s; draw the %s there (type %s), "
                    "or name the %s for what it is" % (p.get("type"), p.get("id") or "", lab[:40], w,
                                                        "in it" if anywhere else "anywhere in the figure", w,
                                                        "/".join(e["parts"][:2]), p.get("type")), p, NOTE if anywhere else BLOCK)
    # a step's title naming a thing the figure never draws (not on a screen: an HMI names what it reads)
    inst = [p for p, g in F.items if p.get("type") in ("gauge", "level", "readout", "well")]
    if have.get("panel") or have.get("log") or (len(inst) >= 2 and len(F.drawn()) - len(inst) <= 2):
        return
    read = " ".join(str(p.get("label") or "") for p in inst).lower()     # "Detector 1" on a readout: the thing it reads
    for k, s in enumerate(rspec.get("steps") or [], 1):
        if not isinstance(s, dict):
            continue
        for w, e in names_in(s.get("title"), strict_only=True):
            if not any(have.get(t) for t in e["parts"]) and not _rx(w).search(read):
                bad("NAMED", "step %d (%r) names the %s, and the figure draws none - draw it (type %s) or say it in "
                    "the slide's words, not the step's" % (k, str(s.get("title"))[:50], w, "/".join(e["parts"][:2])), "step%d" % k)


def _pbox(g):
    pts = g.get("pts") or [[0, 0]]
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def chk_loose(F, bad):
    others = F.pipes()
    eqp = [(p, g) for p, g in F.items if p.get("type") not in ("text", "wire", "pipe", "hose", "zone", "gas_cloud") and g.get("box")]
    for p, g in others:
        if p.get("open") is True:
            continue
        pts = g["pts"]
        for which, e in (("start", pts[0]), ("end", pts[-1])):
            if p.get("open") in (which, "both"):
                continue
            if e[0] <= EDGE or e[1] <= EDGE or e[0] >= F.W - EDGE or e[1] >= F.H - EDGE:
                continue                                   # it runs on off the picture
            ok = False
            for q, h in eqp:
                b = h["box"]
                if q.get("type") in ("space", "panel"):    # through a room's wall, never ending in its middle
                    on_wall = pt_box(e, b) <= 4 and not (b[0] + 4 < e[0] < b[2] - 4 and b[1] + 4 < e[1] < b[3] - 4)
                    if on_wall:
                        ok = True
                elif q.get("type") == "ga":
                    G = h.get("ga") or {}
                    if abs(e[1] - G.get("deck", -1e9)) <= 4 or pt_box(e, b) <= 4 and not (b[0] + 4 < e[0] < b[2] - 4 and G.get("deck", b[1]) + 4 < e[1] < b[3] - 4):
                        ok = True
                elif pt_box(e, b) <= PORT or any(math.hypot(e[0] - pp[0], e[1] - pp[1]) <= PORT for pp in (h.get("ports") or {}).values()):
                    ok = True
                if ok:
                    break
            if not ok:
                ok = any(poly_dist(e, h["pts"]) <= TOUCH for q, h in others if q is not p)
            if not ok:                                     # a leak or a fire at the open end: the line is broken there on purpose
                ok = any((h.get("from") and math.hypot(e[0] - h["from"][0], e[1] - h["from"][1]) <= 30) or
                         (q.get("type") in ("flame", "fire", "spill", "spark") and pt_box(e, h["box"]) <= 24)
                         for q, h in F.of("gas_cloud", "flame", "fire", "spill", "spark"))
            if not ok:                                     # how far it is from the nearest thing it could end on
                d = min([pt_box(e, h["box"]) for q, h in eqp if q.get("type") not in ("space", "panel", "ga")] +
                        [poly_dist(e, h["pts"]) for q, h in others if q is not p] + [1e9])
                # on nothing, plainly: far from every part, not near the frame (it may run on off the picture), no words at
                # its end saying where it goes ("nitrogen", "hot exhaust"), not in a cloud (a leak) - else a near miss to judge
                said = any(pt_box(e, h["box"]) <= 70 for q, h in F.of("text"))
                edge = min(e[0], e[1], F.W - e[0], F.H - e[1]) <= 2 * EDGE
                leak = any(pt_box(e, h["box"]) <= 30 for q, h in F.of("gas_cloud"))
                far = d > LOOSE_FAR and not said and not edge and not leak
                bad("LOOSE END", "the %s %s ends at (%g, %g) %s - a pipe runs from a part to a part: \"from\": "
                    "\"<id>.<port>\", \"to\": \"<id>.<port>\" (SPEC.md Relations), or end it on another pipe; a line open to "
                    "the air says \"open\": \"%s\"" % (p.get("type"), p.get("id") or "", round(e[0], 1), round(e[1], 1),
                                                       "on nothing" if far else "%d units from the nearest part%s" % (
                                                           min(d, 9999), " (words at its end say where it goes?)" if said else
                                                           " (near the edge: it runs on off the picture?)" if edge else
                                                           " (a leak into the cloud?)" if leak else ""), which),
                    p, BLOCK if far else NOTE)


def chk_deck(F, bad):
    T = truths()["deck_mounted"]
    for p, g in F.items:
        t = p.get("type")
        if not g.get("box"):
            continue
        if t in T["types"]:
            s = F.ship_for(g["box"])
            if not s:
                continue
            G, sb = s[1]["ga"], s[1]["box"]
            deck = G["deck"]
            hull = _hull_at(G, deck)
            if not (hull[0] - 2 <= center(g["box"])[0] <= hull[1] + 2):
                continue
            if t == "vent":
                out = (g.get("ports") or {}).get("outlet", [0, g["box"][1]])[1]
                rise = max(T.get("vent_rise_min", 30), 0.15 * (G["keel"] - deck))
                if out > deck - rise:
                    bad("INSIDE", "the vent %s's outlet is at y %g - %s the deck (y %g): a vent mast stands on the open deck, its "
                        "outlet well above it - \"on\": \"%s.deck\" (and \"at\") places it" % (
                            p.get("id") or "", round(out, 1), "below" if out > deck else "only %d units above" % (deck - out),
                            deck, s[0].get("id") or "G"), p, BLOCK if out > deck + 2 else NOTE)
            else:
                low = g.get("foot", [0, g["box"][3]])[1]
                if low > deck + 6:
                    bad("INSIDE", "the %s %s stands at y %g, inside the hull (deck at y %g) - it belongs on the open deck: "
                        "\"on\": \"%s.deck\"" % (t, p.get("id") or "", round(low, 1), deck, s[0].get("id") or "G"), p, BLOCK)
                elif t == "hatch" and low < deck - 8:
                    bad("INSIDE", "the hatch %s floats %d units over the deck (y %g) - it is IN the deck: \"on\": \"%s.deck\""
                        % (p.get("id") or "", deck - low, deck, s[0].get("id") or "G"), p)
        if t in ("tank", "integral_tank"):
            s = F.ship_for(g["box"])
            if s:
                deck = s[1]["ga"]["deck"]
                if g["box"][1] < deck - 6 and g["box"][3] > deck + 6:
                    bad("INSIDE", "the tank %s crosses the deck line (y %g): a fuel tank stands in its hold (\"in\": \"%s\") or "
                        "on the open deck (\"on\": \"%s.deck\"), not half through it" % (p.get("id") or "", deck,
                                                                                           s[0].get("id") or "G", s[0].get("id") or "G"), p, BLOCK)


def _hull_at(G, y):
    rows = G.get("hull") or []
    best = min(rows, key=lambda r: abs(r[0] - y)) if rows else [y, -1e9, 1e9]
    return best[1], best[2]


VENT_WORDS = re.compile(r"\bvent(?:s|ed|ing)?\b|\breliev|\brelease|\bblow|\beject|\bescap|\bgoes up\b|\bleaves the (?:mast|outlet)")
# words that SAY the gas is let out now - not "the vent mast", "a vent line", "the relief valve" (a name)
SAID_WORDS = re.compile(r"\bvents\b(?! mast| line| pipe| outlet| system)|\bvented\b|\bventing\b(?! system| line)|\bvent(?:s)? (?:to|into|out)\b|"
                        r"\bgas (?:leaves|escapes|goes up|goes out)\b|\bvapou?r (?:leaves|goes (?:up|to|out))\b|"
                        r"\breleas(?:e|es|ed|ing) (?:the )?(?:gas|vapou?r)|\b(?:gas|vapou?r) is released\b|\breliev(?:es|ing)\b")


def chk_gas(F, bad):
    vents = F.of("vent")
    if not vents:
        return
    top, per = reached(F.r)
    clouds = F.of("gas_cloud")
    fl = F.of("flame", "fire")

    def gas_at(vids, now=None):
        vals = top if now is None else now
        if any(vals.get(p.get("id"), -1) > 0.05 for p, g in vents if p.get("id") in vids):
            return True
        for p, g in clouds + fl:
            if vals.get(p.get("id"), -1) > 0.05 and any(_near_vent(p, g, h) for q, h in vents if q.get("id") in vids):
                return True
        return False

    vids = {p.get("id") for p, g in vents}
    talk = " ".join([str(s.get("title") or "") for s in F.r.get("steps") or [] if isinstance(s, dict)] +
                    [str(p.get("text") or "") for p, g in F.of("text")]).lower()
    vid = sorted(x for x in vids if x)[0] if any(vids) else "V"
    for k, end, during in states(F.r):                   # marks' "then" moves count too
        for i, v in during.items():
            top[i] = max(top.get(i, -1e9), v)
    if SAID_WORDS.search(talk) and not gas_at(vids):
        bad("NO GAS", "the words say the gas vents, and no step lets it out: play the vent (%s, 1) - its puffs leave the "
            "outlet - or grow a gas cloud from it (\"from\": \"%s.outlet\")" % (vid, vid), vid, BLOCK)
        return
    rv = {p.get("id") for p, g in F.of("relief_valve")}
    steps = [s for s in F.r.get("steps") or [] if isinstance(s, dict)]
    for k, now, during in states(F.r):                   # at the END of each step (a vent left venting still vents) or during it
        title = str(steps[k - 1].get("title") or "").lower() if k <= len(steps) else ""
        said = SAID_WORDS.search(title) and not re.search(r"\bno (?:gas )?vent|\bwithout vent|\bstops?\b|\bshuts?\b|\bcloses?\b", title)
        lifted = any(max(now.get(r, -1), during.get(r, -1)) > 0.1 for r in rv)
        if (said or lifted) and not gas_at(vids, now) and not gas_at(vids, during):
            bad("NO GAS", "step %d %s and no gas leaves the vent in that step - play the vent too (%s, 1) or a gas cloud "
                "from its outlet" % (k, "says the gas vents" if said else "lifts the relief valve", vid),
                "step%d" % k, BLOCK if said else NOTE)


def _near_vent(p, g, vg):
    out = (vg.get("ports") or {}).get("outlet")
    if not out:
        return False
    if g.get("from"):
        return math.hypot(g["from"][0] - out[0], g["from"][1] - out[1]) <= 30
    return pt_box(out[:2], g.get("box") or [0, 0, 0, 0]) <= 20


def chk_aim(F, bad):
    targets = [(p, g) for p, g in F.items if p.get("type") not in ("text", "wire", "zone") and (g.get("box") or g.get("pts"))]
    for p, g in F.of("spray"):
        r = g.get("reach")
        if not r:
            continue
        aimed = [q for q, h in targets if q is not p and q.get("type") not in ("ga", "space", "panel")]
        d = min([pt_box(r, h["box"]) for q, h in targets if q in aimed and h.get("box")] +
                [poly_dist(r, h["pts"]) for q, h in targets if q in aimed and h.get("pts")] + [1e9])
        off = not (0 <= r[0] <= F.W and 0 <= r[1] <= F.H) or any(      # it sprays on past the picture, or over an area
            pt_box(r, h["box"]) == 0 for q, h in F.of("space", "zone", "gas_cloud") if h.get("box"))
        if d > 12:
            bad("AIM", "the spray %s reaches (%g, %g), %s - aim it at what it cools or steers: \"aim\": \"<id>\"" % (
                p.get("id") or "", round(r[0], 1), round(r[1], 1),
                "where nothing is drawn" if d > AIM_FAR else "%d units short of the nearest part" % d), p,
                BLOCK if d > AIM_FAR and not off else NOTE)
    for p, g in F.of("zone"):                             # a hazardous zone round its source: centred on it
        if p.get("r") is None:
            continue
        c, r = center(g["box"]), float(p["r"])
        srcs = []
        for q, h in targets:
            if q is p or q.get("type") in CONTAINERS + ("gas_cloud",):
                continue
            srcs += [pp[:2] for pp in (h.get("ports") or {}).values()] + ([center(h["box"])] if h.get("box") else [])
            srcs += [h["pts"][0], h["pts"][-1]] if h.get("pts") else []
        if srcs and min(math.hypot(c[0] - s[0], c[1] - s[1]) for s in srcs) > max(12, 0.4 * r):
            near = min(srcs, key=lambda s: math.hypot(c[0] - s[0], c[1] - s[1]))
            bad("AIM", "the round zone %s is centred on (%g, %g), on nothing - a zone is drawn round its source (the vent outlet, "
                "the flange): \"around\": \"<id>.outlet\" with its \"r\" (its x, y is the top left of its box, not its middle); the "
                "nearest source is at (%g, %g)" % (p.get("id") or "", round(c[0], 1), round(c[1], 1), round(near[0], 1), round(near[1], 1)), p)
    for p, g in F.of("water_curtain"):
        top = (g.get("ports") or {}).get("header") or [center(g["box"])[0], g["box"][1]]
        d = min([pt_box(top[:2], h["box"]) for q, h in targets if q is not p and h.get("box")] +
                [poly_dist(top[:2], h["pts"]) for q, h in targets if q is not p and h.get("pts")] + [1e9])
        side = any(h.get("box") and q is not p and q.get("type") not in CONTAINERS and gap(g["box"], h["box"]) <= 4 for q, h in targets)
        if d > 10 and not side:
            bad("AIM", "the water curtain %s hangs from %s at (%g, %g) - its spray header is on the deck edge under the "
                "bunkering station, the water down the ship's side: \"on\": \"<ship>.deck\", \"at\": ..." % (
                    p.get("id") or "", "nothing" if d > AIM_FAR else "%d units off the nearest part" % d,
                    round(top[0], 1), round(top[1], 1)), p, BLOCK if d > AIM_FAR else NOTE)
    for p, g in F.of("detector"):
        b = g["box"]
        rooms = [q for q, h in F.items if q.get("type") in ("space", "ga") and h.get("box") and
                 h["box"][0] <= center(b)[0] <= h["box"][2] and h["box"][1] <= center(b)[1] <= h["box"][3]]
        near = [q for q, h in targets if q is not p and h.get("box") and gap(b, h["box"]) <= 60]
        if not rooms and not near:
            bad("AIM", "the detector %s watches nothing - put it in the space it guards (\"on\": \"<space>.ceiling\")" % (p.get("id") or ""), p)


def chk_words(F, bad):
    drawn = F.drawn(containers=True) + F.pipes()
    for p, g in F.of("text"):
        if p.get("to"):
            t = p["to"]
            if not any((h.get("box") and pt_box(t, h["box"]) <= 10) or (h.get("pts") and poly_dist(t, h["pts"]) <= 8) for q, h in drawn):
                bad("LEADER", "the callout %r leads to (%g, %g), where nothing is drawn - \"for\": \"<id>\" points it at its part"
                    % (str(p.get("text"))[:40], t[0], t[1]), p)
            continue
        if p.get("style") == "h" and g["box"][1] < F.H * 0.2 or id(p) in F.said:
            continue                                      # the figure's heading; a caption the GRID check named
        if not drawn or F.of(*CHARTS):                    # a chart's words are its axes and notes
            continue
        d = min(gap(g["box"], h.get("box") or _pbox(h)) for q, h in drawn)
        if d > FLOAT:
            bad("LEADER", "the words %r float %d units from anything drawn - put them on their part (\"for\": \"<id>\", a "
                "callout) or in the slide's text" % (str(p.get("text"))[:40], d), p)
    for p, g in F.of("ga"):
        if isinstance(p.get("label"), str) and p["label"].strip().lower() in truths()["generic_ship_labels"]:
            bad("LEADER", "the ship %s is labelled %r - a word that says what the picture obviously is floats under the "
                "keel; leave the label out" % (p.get("id") or "", p["label"]), p)


def _under(F, cap_box, cell):
    """the drawn things under (or over) a caption, in its column"""
    cx = center(cap_box)[0]
    out = []
    for q, h in F.drawn(containers=True) + F.pipes():
        if q.get("type") in CHARTS + ("badge", "ga", "panel"):
            continue
        b = h.get("box") or _pbox(h)
        if abs(center(b)[0] - cx) <= max(46, cell / 2) and cap_box[1] - 150 <= center(b)[1] <= cap_box[3] + 170:
            out.append((q, h))
    return out


def _rows(items, axis):
    """groups of 3+ captions on one line (axis 1: same y, a row) or in one column (axis 0: same x)"""
    pts = sorted(items, key=lambda it: (center(it[1]["box"])[axis], center(it[1]["box"])[1 - axis]))
    groups, cur = [], []
    for it in pts:
        if cur and abs(center(it[1]["box"])[axis] - center(cur[-1][1]["box"])[axis]) > 7:
            groups.append(cur)
            cur = []
        cur.append(it)
    if cur:
        groups.append(cur)
    return [g for g in groups if len(g) >= 3]


def chk_grid(F, bad):
    caps = [(p, g) for p, g in F.of("text") if not p.get("to") and len(str(p.get("text") or "")) <= 60]
    rows = _rows(caps, 1)
    eqs = [q for q, h in F.drawn() if q.get("type") not in CHARTS + ("badge",)]
    charts = [q for q, h in F.drawn() if q.get("type") in CHARTS]
    for row in rows:
        xs = sorted(center(g["box"])[0] for p, g in row)
        cell = min((b - a) for a, b in zip(xs, xs[1:])) if len(xs) > 1 else 120
        if cell < 50:
            continue
        has = [bool(_under(F, g["box"], cell)) for p, g in row]
        words = ", ".join(repr(str(p.get("text"))[:18]) for p, g in row)
        if sum(has) < len(has) and (sum(has) or (len(eqs) <= 1 and not charts)):
            F.said.update(id(p) for p, g in row)
            F.grid = True
        if 0 < sum(has) < len(has):
            miss = ", ".join(repr(str(p.get("text"))[:18]) for (p, g), h in zip(row, has) if not h)
            # BLOCK when the captions over nothing NAME things (fuels, equipment: "six fuels, one tank"); arrows and headings: a note
            named = any(names_in(p.get("text"), strict_only=True) or any(_rx(f).search(" %s " % str(p.get("text") or "").lower())
                                                                          for f in truths()["fuels"])
                        for (p, g), h in zip(row, has) if not h)
            # a TABLE (two or more rows of words under the captions) is words in columns, not drawings missing
            table = any(sum(1 for q, k in F.of("text") if q is not p and abs(center(k["box"])[0] - center(g["box"])[0]) <= cell / 2
                            and k["box"][1] > g["box"][1]) >= 2 for (p, g), h in zip(row, has) if not h)
            named = named and not table
            bad("GRID", "a row of %d captions (%s) has a drawing under only %d of them - %s stand over nothing: each caption "
                "gets its own drawing, or the row is the slide's text, not a figure" % (len(row), words, sum(has), miss),
                next(p for (p, g), h in zip(row, has) if not h), BLOCK if named else NOTE)
        elif not any(has) and len(eqs) <= 1 and not charts:
            bad("GRID", "%d captions in a row (%s) and %d drawing(s) - a table of words is not a figure: draw each, or put "
                "the table in the slide's text" % (len(row), words, len(eqs)), row[0][0])


def chk_small(F, bad):
    """a small drawing lost in a big `panel` part (the figure's own frame is the drawing audit's EMPTY, on what is drawn)"""
    for p, g in F.of("panel"):
        pb = g["box"]
        inner = [h["box"] for q, h in F.items if q is not p and h.get("box") and q.get("type") != "text" and
                 pb[0] <= center(h["box"])[0] <= pb[2] and pb[1] <= center(h["box"])[1] <= pb[3]]
        if inner:
            u = [min(b[0] for b in inner), min(b[1] for b in inner), max(b[2] for b in inner), max(b[3] for b in inner)]
            if area(u) / max(1, area(pb)) < 0.3:
                bad("SMALL", "the panel %s is %d %% filled - its drawing is small in a big empty box" % (
                    p.get("id") or "", area(u) / max(1, area(pb)) * 100), p)


# ------------------------------------------------------------------ the figure kinds' truths
def kinds(F):
    T, words, types = truths()["figures"], words_of(F.r), {p.get("type") for p, g in F.items}
    out = []
    for key, k in T.items():
        if k.get("when_fuels"):
            fuels = set()
            for p, g in F.of("text"):
                for f in truths()["fuels"]:
                    if _rx(f).search(" " + str(p.get("text") or "").lower() + " "):
                        fuels.add(p.get("id") or id(p))
            if len(fuels) >= k["when_fuels"]:
                out.append(key)
            continue
        hits = sum(1 for w in k.get("when") or [] if w in words)
        if hits >= k.get("min_words", 1) and (not k.get("needs_one_of") or types & set(k["needs_one_of"])):
            out.append(key)
    return out


def chk_truths(F, bad):
    T = truths()["figures"]
    for key in kinds(F):
        k = T[key]
        rules = {r["rule"]: r["says"] for r in k["truths"]}
        tag = "TRUTH %s" % key

        def say(rule, detail, pid=None, level=None):
            bad(tag, "%s - %s (%s)" % (detail, rules[rule], k["title"]), pid or rule, level or NOTE)
        if "tcs_on_tank" in rules:
            tcs = [(p, g) for p, g in F.of("space") if re.search(r"tank connection|\btcs\b", str(p.get("label") or "").lower())]
            tanks = F.of("tank", "integral_tank")
            for p, g in tcs:
                if tanks and min(gap(g["box"], h["box"]) for q, h in tanks) > 12:
                    say("tcs_on_tank", "the tank connection space %s does not touch the tank" % (p.get("id") or ""))
        if "vent_connected" in rules:
            vents, src = F.of("vent"), [p.get("id") for p, g in F.of("relief_valve", "tank", "integral_tank", "boil_off")]
            if src and any(not connected(F, [p.get("id")], src) for p, g in vents):
                say("vent_connected", "a vent mast is not joined by pipes to the relief valve or the tank it vents")
        if "vent_highest" in rules:
            for p, g in F.of("vent"):
                out = (g.get("ports") or {}).get("outlet", [0, g["box"][1]])[1]
                low = [q.get("id") for q, h in F.of("relief_valve", "tank") if h["box"][1] < out]
                if low:
                    say("vent_highest", "the vent %s's outlet is lower than %s" % (p.get("id") or "", ", ".join(map(str, low))))
        if "supply_path" in rules:
            tanks = [p.get("id") for p, g in F.of("tank", "integral_tank", "boil_off", "gas_cylinder")]
            eng = [p.get("id") for p, g in F.of("engine", "cylinder")]
            if tanks and eng and not connected(F, tanks, eng):
                say("supply_path", "no pipe path joins the tank to the engine")
            if "valve_on_path" in rules and tanks and eng:
                vs = [p.get("id") for p, g in F.of("valve")]
                comp = [c for c in components(F) if c & set(tanks) and c & set(eng)]
                if vs and comp and not (comp[0] & set(vs)):
                    say("valve_on_path", "the valves are not on the path from the tank to the engine")
        if "drip_tray_under" in rules:
            heads = F.of("coupling", "manifold")
            for p, g in F.of("drip_tray"):
                if heads and not any(g["box"][0] - 8 <= center(h["box"])[0] <= g["box"][2] + 8 and g["box"][1] >= center(h["box"])[1]
                                     for q, h in heads):
                    say("drip_tray_under", "the drip tray %s is not under the coupling or the manifold" % (p.get("id") or ""))
        if "curtain_on_hull" in rules:
            for p, g in F.of("water_curtain"):
                s = F.ship_for(g["box"])
                if s and abs(g["box"][1] + 0 - s[1]["ga"]["deck"]) > 14:
                    say("curtain_on_hull", "the water curtain %s does not hang from the deck edge (its header at y %g, the deck at "
                        "y %g)" % (p.get("id") or "", round(g["box"][1], 1), s[1]["ga"]["deck"]))
        if "line_connected" in rules:
            heads = [p.get("id") for p, g in F.of("coupling", "manifold")]
            hoses = [p.get("id") for p, g in F.of("hose")]
            if heads and hoses and not connected(F, hoses, heads):
                say("line_connected", "the hose does not meet the coupling / manifold")
        if "modes_drawn" in rules:
            modes = [(p, g) for p, g in F.of("text") if not p.get("to") and
                     re.search(r"\b(gas|fuel[- ]oil|diesel|oil|dual[- ]fuel)\s+mode\b|\bchangeover\b", str(p.get("text") or "").lower())]
            if len(modes) >= 2:
                kinds_under = set()
                for p, g in modes:
                    under = [q.get("type") for q, h in _under(F, g["box"], 140)]
                    eng = [t for t in under if t in ("engine", "cylinder")]
                    kinds_under.update(eng[:1])
                    if not eng:                    # a mode caption over no engine is a caption over the wrong thing
                        say("modes_drawn", "the caption %r heads %s" % (str(p.get("text"))[:30], ("a " + "/".join(sorted(set(under))))
                                                                         if under else "nothing"), p, BLOCK)
                if len(kinds_under) > 1:
                    say("modes_drawn", "the mode captions head different things (%s) - one engine, or one cylinder, in each mode"
                        % ", ".join(sorted(kinds_under)))
        if "each_fuel_drawn" in rules and not F.of(*CHARTS) and not F.grid:
            for p, g in F.of("text"):
                t = " " + str(p.get("text") or "").lower() + " "
                if p.get("to") or not any(_rx(f).search(t) for f in truths()["fuels"]):
                    continue
                if not _under(F, g["box"], 120):
                    say("each_fuel_drawn", "the fuel %r has no drawing of its own" % str(p.get("text"))[:30])


# ------------------------------------------------------------------ entry
def analyse(spec, where="", resolved=None):
    """{"block": [lines], "note": [lines], "waived": [lines], "findings": [dicts]} - every meaning finding of one spec.
    BLOCK (a build FAIL, BROKEN for the reviewer) only for a clear physical error; NOTE for the figure reviewer to judge in
    context. A spec's "meaning_ok": {"<KIND> <part id>": "<why it is right>"} accepts one finding on purpose - the reviewer
    sees the reason, the build counts it; a waiver with no reason is itself a BLOCK (2.66.0, Aleksis: "if even a minuscule
    detail is off it flags it and there isn't any flexibility")"""
    res = {"block": [], "note": [], "waived": [], "findings": []}
    if not isinstance(spec, dict) or not spec.get("parts"):
        return res
    if resolved is None:
        try:
            got = kit_relate.run([spec])
        except Exception as err:                         # noqa: BLE001 - a resolver that cannot run is said, not hidden
            res["block"].append("%s: the relations could not be resolved - %s" % (where, err))
            return res
        if not got:
            return res
        resolved = got[0]
    if resolved.get("error"):
        res["block"].append("%s: the relations could not be resolved - %s" % (where, resolved["error"]))
        return res
    rspec, geo = resolved["spec"], resolved["geometry"]
    found, seen = [], set()

    def bad(kind, msg, part=None, level=NOTE):
        pid = part if isinstance(part, str) else ((part or {}).get("id") or (part or {}).get("type") or "-") if part is not None else "-"
        key = "%s %s" % (kind, pid)
        if (key, msg) not in seen:
            seen.add((key, msg))
            found.append({"kind": kind, "part": pid, "key": key, "level": level, "msg": msg})
    for e in rspec.get("_relate") or []:
        bad("RELATION", e, None, BLOCK)
    F = Fig(spec, rspec, geo)
    for fn in (chk_named, chk_loose, chk_deck, chk_gas, chk_aim, chk_grid, chk_words, chk_small, chk_truths):
        fn(F, bad)
    ok = spec.get("meaning_ok") if isinstance(spec.get("meaning_ok"), dict) else {}
    norm = {re.sub(r"\s+", " ", str(k)).strip().lower(): (k, v) for k, v in ok.items()}
    used = set()
    for f in found:
        w = norm.get(f["key"].lower())
        if w and str(w[1] or "").strip():
            used.add(w[0])
            f["waived"] = str(w[1]).strip()
            res["waived"].append("%s: waived %s (meaning_ok: %s) - %s" % (where, f["key"], f["waived"], f["msg"]))
        elif w:
            used.add(w[0])
            res["block"].append("%s: WAIVER %s: \"meaning_ok\" accepts it with no reason - say why it is right, or fix it" % (where, f["key"]))
        else:
            res["block" if f["level"] == BLOCK else "note"].append(
                "%s: %s%s: %s" % (where, "" if f["level"] == BLOCK else "note ", f["key"] if f["part"] != "-" else f["kind"], f["msg"]))
    for k in ok:
        if k not in used:
            res["note"].append("%s: note WAIVER %s: \"meaning_ok\" names a finding the figure does not have (left over?)" % (where, k))
    res["findings"] = found
    return res


def check(spec, where="", resolved=None):
    """the BLOCKING meaning problems of one spec, as "<where>: <KIND> <part>: ..." lines (check_kit.py: a build FAIL) - the
    notes and the waived ones are analyse()'s; [] when node is not there (the build needs it)"""
    return analyse(spec, where, resolved)["block"]


def figure_kinds(spec):
    """the figure kinds (figure-truths.json) a spec is, with their must-be-true sentences - for the FIGURE review"""
    got = kit_relate.run([spec]) or [{"spec": spec, "geometry": []}]
    F = Fig(spec, got[0].get("spec", spec), got[0].get("geometry") or [])
    T = truths()["figures"]
    return [{"kind": k, "title": T[k]["title"], "truths": [r["says"] for r in T[k]["truths"]]} for k in kinds(F)]


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    want_kinds = "--kinds" in argv
    files = [a for a in argv if not a.startswith("--")]
    specs = [json.load(io.open(f, encoding="utf-8")) for f in files]
    got = kit_relate.run(specs) or [None] * len(specs)
    n = nn = nw = 0
    for f, s, r in zip(files, specs, got):
        if want_kinds:
            print(os.path.basename(f), json.dumps(figure_kinds(s), ensure_ascii=False))
            continue
        a = analyse(s, os.path.basename(f), r)
        for x in a["block"]:
            print("  - " + x)
        for x in a["note"] + a["waived"]:
            print("    " + x)
        n, nn, nw = n + len(a["block"]), nn + len(a["note"]), nw + len(a["waived"])
    if not want_kinds:
        print("%s, %d note(s), %d waived - %d spec(s)" % (("%d BLOCK(s)" % n) if n else "no block", nn, nw, len(files)))
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
