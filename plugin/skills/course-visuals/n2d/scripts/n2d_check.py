#!/usr/bin/env python3
"""n2d_check.py - the check of a 2D figure spec (SPEC.md): within its form's capacity, every thing has a picture, every
name short enough to read from the back of the room, every step names what is drawn. A spec that asks for more is
refused with the reason; nothing is shrunk to fit. The same rules as check() in n2d.js.

    python n2d_check.py figures/M03/s14.n2d.json [--worlds figures/M03/worlds.n2d.json] [--lines 4]
"""
from __future__ import annotations

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THINGS = json.load(io.open(os.path.join(HERE, "..", "things.json"), encoding="utf-8"))
LIMIT = {"name": 3, "chars": 24, "tag": 4, "act": 4, "read": 14, "words": 2}
FORMS = ("path", "zones", "steps", "options", "amounts")
SCENES = {"pump_line": ("filter", "pump", "gauge", "valve"), "crossing": ()}
WORLDS_FILE = "worlds.n2d.json"


def known(thing):
    k = str(thing or "").lower().strip()
    return k in THINGS["names"] or k in THINGS["alias"]


def nwords(s):
    return len(str(s or "").split())


def _name(P, where, s, most=LIMIT["name"]):
    if not s:
        return
    if nwords(s) > most:
        P.append('%s: "%s" is %d words; at most %d - the picture says the rest' % (where, s, nwords(s), most))
    elif len(str(s)) > LIMIT["chars"] + (most - LIMIT["name"]) * 6:
        P.append('%s: "%s" is too long for the back of the room' % (where, s))


def _thing(P, where, thing):
    if not known(thing):
        P.append('%s: no picture for "%s" - pick a thing from the library (n2d/things.json), or add this one to it' % (where, thing))


def _tags(P, steps):
    for i, x in enumerate(steps, 1):
        tag = x.get("tag")
        for t in (tag.values() if isinstance(tag, dict) else [tag] if tag else []):
            _name(P, "step %d tag" % i, t, LIMIT["tag"])


def _chain(s):
    return [x.strip() for x in str(s).split(">")]


def links(spec):
    out = []
    for s in spec.get("links") or []:
        s = str(s).split(":")[0]
        ids = _chain(s)
        out += [(a, b) for a, b in zip(ids, ids[1:])]
    return out


def check_path(spec):
    P, th = [], spec.get("things") or []
    if len(th) < 2:
        P.append("a path needs at least two things")
    if len(th) > 7:
        P.append("%d things; a path holds at most 7 - show the part this slide teaches" % len(th))
    ids = {t.get("id") for t in th}
    for t in th:
        _name(P, "thing %s" % t.get("id"), t.get("name"))
        if t.get("is") != "decision":
            _thing(P, "thing %s" % t.get("id"), t.get("is"))
    L = links(spec)
    for a, b in L:
        if a not in ids or b not in ids:
            P.append("link %s>%s names a thing that is not drawn" % (a, b))
    # a long single chain folds into two rows; a longer path with branches would shrink its pictures past reading
    rank = {i: 0 for i in ids}
    for _ in ids:
        for a, b in L:
            if a in rank and b in rank and rank[b] < rank[a] + 1:
                rank[b] = rank[a] + 1
    cols = max(rank.values() or [0]) + 1
    chain = all(sum(1 for a, _ in L if a == i) <= 1 and sum(1 for _, b in L if b == i) <= 1 for i in ids) and cols == len(ids)
    if cols > 5 and not chain:
        P.append("%d things in a row with branches; a path with branches is at most 5 long - show the part this slide teaches" % cols)
    for i, x in enumerate(spec.get("steps") or [], 1):
        for key in ("go", "bug", "add", "fail", "mark"):
            for c in ([x[key]] if isinstance(x.get(key), str) else x.get(key) or []):
                for tid in _chain(c):
                    if tid not in ids:
                        P.append('step %d %s names "%s", not drawn' % (i, key, tid))
        tag = x.get("tag")
        if isinstance(tag, dict):
            P += ['step %d tag names "%s", not drawn' % (i, k) for k in tag if k not in ids]
    return P


def check_zones(spec):
    P, Z = [], spec.get("zones") or []
    if not 2 <= len(Z) <= 4:
        P.append("%d zones; zones hold 2 to 4" % len(Z))
    for z in Z:
        _name(P, "zone %s" % z.get("id"), z.get("name"))
        if len(z.get("things") or []) > 3:
            P.append("zone %s has %d things; at most 3" % (z.get("id"), len(z["things"])))
        for t in z.get("things") or []:
            _name(P, "zone %s" % z.get("id"), t.get("name"))
            _thing(P, "zone %s" % z.get("id"), t.get("is"))
    return P


def check_steps(spec):
    P, S = [], spec.get("steps") or []
    if not 2 <= len(S) <= 7:
        P.append("%d steps; a procedure shows 2 to 7 - group the rest" % len(S))
    for i, x in enumerate(S, 1):
        _thing(P, "step %d" % i, x.get("is"))
        if not x.get("do"):
            P.append('step %d: "do", the action in 4 words or less' % i)
        _name(P, "step %d" % i, x.get("do"), LIMIT["act"])
        if x.get("read") and len(str(x["read"])) > LIMIT["read"]:
            P.append('step %d reading "%s" is too long' % (i, x["read"]))
    return P


def check_options(spec):
    P, O, Q = [], spec.get("options") or [], spec.get("qualities") or []
    if not 2 <= len(O) <= 3:
        P.append("%d options; 2 or 3" % len(O))
    if not 1 <= len(Q) <= 3:
        P.append("%d qualities; 1 to 3" % len(Q))
    for i, o in enumerate(O, 1):
        _name(P, "option %d" % i, o.get("name"))
        _thing(P, "option %d" % i, o.get("is"))
    for q in Q:
        _name(P, "quality %s" % q.get("name"), q.get("name"), 2)
        vals = q.get("values") or []
        if len(vals) != len(O) or any(not isinstance(v, (int, float)) or not 0 <= v <= 3 for v in vals):
            P.append("quality %s: one value 0 to 3 for each option" % q.get("name"))
        for w in q.get("words") or []:
            _name(P, "quality %s" % q.get("name"), w, LIMIT["words"])
    return P


def check_amounts(spec):
    P, S = [], spec.get("series") or []
    if not 1 <= len(S) <= 3:
        P.append("%d series; 1 to 3" % len(S))
    for q in S:
        _name(P, "series", q.get("name"))
        pts = q.get("pts") or []
        if not 2 <= len(pts) <= 24:
            P.append("series %s: 2 to 24 points" % q.get("name"))
        if any(not isinstance(p, (list, tuple)) or len(p) != 2 for p in pts):
            P.append("series %s: each point is [x, y], measured values from the source" % q.get("name"))
    bands = (spec.get("scale") or {}).get("bands") or []
    if len(bands) > 5:
        P.append("a scale has at most 5 bands")
    return P


def check_scene(spec):
    P, name = [], spec.get("scene")
    if name not in SCENES:
        return ['no scene "%s" (%s)' % (name, ", ".join(SCENES))]
    if name == "pump_line":
        for k in ("from", "to"):
            _name(P, k, (spec.get(k) or {}).get("name"))
            if not (spec.get(k) or {}).get("name"):
                P.append('"%s": the tank\'s name and level' % k)
        P += ['pump_line has no part "%s" (%s)' % (p, ", ".join(SCENES[name])) for p in spec.get("parts") or [] if p not in SCENES[name]]
    if name == "crossing":
        for k in ("own", "other"):
            _name(P, k, (spec.get(k) or {}).get("name"))
        P += ["step %d: crossing shows start, bearing, lights or alter" % i for i, x in enumerate(spec.get("steps") or [], 1)
              if (x.get("show") or "start") not in ("start", "bearing", "lights", "alter")]
    return P


def resolve(spec, worlds=None):
    """a slide that draws one of the module's systems ("world": "bridge") gets that system's things and links, then its own"""
    if not isinstance(spec, dict) or not spec.get("world"):
        return spec, []
    w = (worlds or {}).get(spec["world"])
    if not w:
        return spec, ['"world": "%s" is not in the module\'s %s' % (spec["world"], WORLDS_FILE)]
    out = dict(spec)
    out["things"] = list(w.get("things") or []) + list(spec.get("things") or [])
    out["links"] = list(w.get("links") or []) + list(spec.get("links") or [])
    out.pop("world", None)
    return out, []


def check(spec, worlds=None, n_lines=None):
    """-> [problem, ...]; empty when the figure can be drawn as it is"""
    if not isinstance(spec, dict):
        return ["the figure is not a JSON object"]
    spec, P = resolve(spec, worlds)
    form = spec.get("form")
    if form not in FORMS and form != "scene":
        return P + ['no form "%s" (%s, scene)' % (form, ", ".join(FORMS))]
    if not spec.get("say"):
        P.append('"say": the one point this figure makes, in one sentence')
    steps = spec.get("steps") or []
    if not steps:
        P.append("a figure needs at least its arrival step")
    if len(steps) > 7:
        P.append("%d steps; at most 7" % len(steps))
    for i, x in enumerate(steps, 1):
        for ln in ([x.get("line")] if not isinstance(x.get("line"), list) else x["line"]):
            if ln is not None and (not isinstance(ln, int) or ln < 1 or (n_lines and ln > n_lines)):
                P.append("step %d: line %s is not one of the slide's lines" % (i, ln))
    _tags(P, steps)
    P += {"path": check_path, "zones": check_zones, "steps": check_steps, "options": check_options,
          "amounts": check_amounts, "scene": check_scene}[form](spec)
    return P


def load_worlds(figdir):
    p = os.path.join(figdir, WORLDS_FILE)
    if not os.path.isfile(p):
        return {}
    return json.load(io.open(p, encoding="utf-8"))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    path, worlds, n_lines = argv[0], None, None
    if "--worlds" in argv:
        worlds = json.load(io.open(argv[argv.index("--worlds") + 1], encoding="utf-8"))
    else:
        worlds = load_worlds(os.path.dirname(os.path.abspath(path)))
    if "--lines" in argv:
        n_lines = int(argv[argv.index("--lines") + 1])
    P = check(json.load(io.open(path, encoding="utf-8")), worlds, n_lines)
    for p in P:
        print("  - " + p)
    print("PASS" if not P else "REFUSED: %d" % len(P))
    return 0 if not P else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
