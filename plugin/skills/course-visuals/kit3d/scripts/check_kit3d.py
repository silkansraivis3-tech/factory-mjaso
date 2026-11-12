#!/usr/bin/env python3
"""check_kit3d.py - is a 3D-kit scene spec drawable, and is it a good one? (the 3D twin of check_kit.py)

  check_kit3d.py spec   <file.kit3d.json> ... [--parts <module>/assets/kit3d_parts.js] [--strict] [--json]
  check_kit3d.py module <module folder> [--figures <course>/working_claude/figures/M03] [--strict] [--json]

SPEC   valid JSON; a label; every part of a type the kit has (or the module's kit3d_parts.js adds); ids unique
       (parts and their sub-parts); every label, group, step and control names something that exists; every state
       named is one the part's type has; `when` well formed; view angles numbers. What stands where: deck parts on the deck,
       parts joined by their ports, a gas carrier's tanks in their hull (none through another, out through the hull's ends
       or down through its double bottom; a membrane tank lining the hold, a Moss skirt and saddles on the inner bottom), no
       part inside a tank that is not its content, a dimension's ends on something drawn. What a label names: no box standing
       in for what the kit draws, no hull's word on a tank, "double hull" on a double hull, one dot a point, no dot hidden
       behind a tank from its step's view.
MODULE every *.kit3d.json in the figures folder; and when the module's deck holds data-kit3d: assets/kit3d.js and
       assets/kit3d.css are there and equal the factory's byte for byte, assets/vendor/three.min.js is there, and each
       scene's step lines are lines of its slide (1..n, counted from 1 as the deck counts them) up to its last line.
NOTES  (shown, but exit 0 unless --strict): a part nobody names, a step with too many or too few labels, a scene with
       nothing to walk or press, no units.

The catalogue (part type -> sub-parts, states) is read from ../kit3d.js, so this file never lists a part itself.
Exit 0 clean, 1 problems found, 2 nothing to check / bad input.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import math
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = re.compile(r"/\*\s*@@CATALOG@@\s*\*/\s*(\{.*?\})\s*/\*\s*@@END@@\s*\*/", re.S)
DEFINE = re.compile(r"KIT3D\.define\(\s*['\"](\w+)['\"]")
# inside a module's own define: k.state(self.id + '.open', ...), k.sub(self.id + '_plate', ...), {family: 'equipment'}
LOCAL_STATE = re.compile(r"\.state\(\s*[\w.]+\s*\+\s*['\"]\.(\w+)['\"]")
LOCAL_SUB = re.compile(r"\.sub\(\s*[\w.]+\s*\+\s*['\"]_(\w+)['\"]")
LOCAL_SUB_ANY = re.compile(r"\bk\.sub\(\s*[\w.]+\s*[,)]")
LOCAL_FAMILY = re.compile(r"['\"]?family['\"]?\s*:\s*['\"](\w+)['\"]")
# a label's "when": "pipe.cut > 0.5", "!tcs.open", "tcs.open"
WHEN = re.compile(r"^(!?)\s*([\w.]+)(?:\s*(?:>=|<=|==|>|<)\s*-?\d+(?:\.\d+)?)?$")
# these tank types draw their liquid (and so its sub-part) only when the part says how full it is
LIQUID_ONLY_WITH_FILL = ("tank_c", "tank_sphere", "tank_prism")
MAX_LABELS, MIN_LABELS = 9, 2
# a step's "line" is the slide's line as the deck numbers it: data-i="1" is the first line, so a scene counting from 0 lights
# each line one step late and its first step lights nothing (M01 s01: "line": 0, the highlight a step ahead of the words)
FROM_ONE = "the deck counts a slide's lines from 1 (data-i=\"1\" is the first line): the first line is \"line\": 1, never 0"
SECTION = re.compile(r'<section\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</section>', re.S)
SCENE = re.compile(r'<script type="application/json" id="k3-[^"]*">(.*?)</script>', re.S)
DATA_I = re.compile(r'\bdata-i="(\d+)"')


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def num(v):
    # a bool is an int in Python; "at": [true, 1, 2] is not a position
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def is_at(v):
    return isinstance(v, list) and len(v) == 3 and all(num(x) for x in v)


# ------------------------------------------------------------------ what the kit has
def read_catalog(kit=KIT):
    """{type: entry} from the strict-JSON block in kit3d.js, or (None, why)"""
    p = os.path.join(kit, "kit3d.js")
    if not os.path.isfile(p):
        return None, "the catalogue is not there - %s is missing" % p
    m = CATALOG.search(read(p))
    if not m:
        return None, "no /* @@CATALOG@@ */ ... /* @@END@@ */ block in %s" % p
    try:
        return json.loads(m.group(1)), None
    except ValueError as e:
        return None, "the catalogue in %s is not JSON: %s" % (p, e)


def local_types(parts_js):
    """a module's kit3d_parts.js adds types: {type: {states, subs, family}} read from each define's own body -
    k.state(<id> + '.open', ...) is a state, k.sub(<id> + '_plate', ...) a sub-part, {family: '...'} its family"""
    if not (parts_js and os.path.isfile(parts_js)):
        return {}
    src = read(parts_js)
    found = list(DEFINE.finditer(src))
    out = {}
    for i, m in enumerate(found):
        body = src[m.end():found[i + 1].start() if i + 1 < len(found) else len(src)]
        entry = out.setdefault(m.group(1), {"states": [], "subs": []})
        for key, rx in (("states", LOCAL_STATE), ("subs", LOCAL_SUB)):
            entry[key] += [n for n in rx.findall(body) if n not in entry[key]]
        # k.sub(sid) with an id of the spec's own: the ids of the part's lists ("sensors": [{"id": ...}])
        if LOCAL_SUB_ANY.search(body):
            entry["subs_from"] = sorted(set(entry.get("subs_from", [])) | set(re.findall(r"\bp\.(\w+)", body)))
        fam = LOCAL_FAMILY.search(body)
        if fam:
            entry["family"] = fam.group(1)
    return out


def load_spec(path):
    try:
        spec = json.loads(read(path))
    except (OSError, ValueError) as e:
        return None, "%s: not JSON (%s)" % (os.path.basename(path), e)
    if not isinstance(spec, dict):
        return None, "%s: a scene is a JSON object, not a %s" % (os.path.basename(path), type(spec).__name__)
    return spec, None


# ------------------------------------------------------------------ the names a spec makes
def sub_ids(part, entry, parts=None):
    """the ids of the sub-parts one part makes (SPEC.md: Parts); parts: the scene's, for a tank seated "in" a hull"""
    out, pid = [], part.get("id")
    if not isinstance(pid, str):
        return out
    given = part.get("subs") if isinstance(part.get("subs"), dict) else {}
    for s in entry.get("subs", []):
        if s == "liquid" and part.get("type") in LIQUID_ONLY_WITH_FILL:
            f = part.get("fill")
            if not (num(f) and f > 0):
                continue
        v = given.get(s)
        out.append(v if isinstance(v, str) and v else "%s_%s" % (pid, s))
    for key in entry.get("subs_from", []):
        items = part.get(key)
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict) and isinstance(it.get("id"), str):
                out.append(it["id"])
    if part.get("type") == "hull":
        out += [part[k] for k in ("bottom_id", "side_id") if isinstance(part.get(k), str)]
    return out + made_ids(part, given, [q for q in parts or [] if isinstance(q, dict)])


def made_ids(part, given, parts):
    """the sub-parts a gas carrier's hull and tanks make by their settings (kit3d.js hull, bilobe, tank_sphere, tank_prism)"""
    pid, t = part["id"], part.get("type")
    sid = lambda n: given.get(n) if isinstance(given.get(n), str) and given.get(n) else "%s_%s" % (pid, n)
    out = []
    if t == "hull":
        sec = hold_section(part)
        if sec["inner"]:
            if not isinstance(part.get("bottom_id"), str):
                out.append(sid("bottom"))
            if not isinstance(part.get("side_id"), str):
                out.append(sid("outer"))
            out.append(sid("inner"))
            out += [sid(n) for n, on in (("wing", sec["zi"] < sec["hz"] - 1e-6), ("hopper", sec["hh"] > 0), ("topwing", sec["th"] > 0)) if on]
    elif t == "tank_c" and nv(part.get("lobes"), 1) >= 2:
        out.append(sid("bulkhead"))
    elif t == "tank_sphere":
        q = seat(part, parts)
        base = nv(q.get("base"), -nv(q.get("r"), 5) * 1.25)
        if part.get("drip") and base < 0:
            out.append(sid("drip"))
        if part.get("cover") and (num(part["cover"]) or "_deck" in q):
            out.append(sid("cover"))
    elif t == "tank_prism" and seat(part, parts).get("_hold"):
        kind = part.get("kind") or "membrane"
        if kind in LINING:
            if not isinstance(part.get("layers"), list):
                out += [sid(n) for n in ("ins2", "barrier2", "ins1", "barrier1")]
        else:
            if not isinstance(part.get("layers"), list):
                out += [sid("insulation"), sid("shell")]
            if part.get("bulkhead") is not False:
                out.append(sid("bulkhead"))
            if kind == "type_b" or part.get("drip"):
                out.append(sid("drip"))
            if nv(part.get("clear"), 0.8) > 0.05:
                out.append(sid("chocks"))
    return out


# ------------------------------------------------------------------ one scene
def check_spec(spec, types):
    """-> (problems, notes), each a list of plain sentences"""
    P, N = [], []

    def view_ok(v, where):
        if v is None:
            return
        if not isinstance(v, dict):
            P.append("%s: view must be an object {az, el, ...}" % where)
            return
        for k in ("az", "el"):
            if k in v and not num(v[k]):
                P.append("%s: view %s must be a number, not %r" % (where, k, v[k]))

    if not (isinstance(spec.get("label"), str) and spec["label"].strip()):
        P.append("no \"label\" - what the scene shows, for a screen reader")
    parts = spec.get("parts")
    if not isinstance(parts, list) or not parts:
        P.append("no \"parts\" list")
        return P, N
    view_ok(spec.get("view"), "scene")

    # -- parts, their sub-parts, the states they offer
    ids, part_ids, states, seen = set(), set(), set(), set()
    for i, p in enumerate(parts):
        tag = "part %d" % (i + 1)
        if not isinstance(p, dict):
            P.append("%s is not an object" % tag)
            continue
        pid = p.get("id")
        tag = "part %r" % pid if pid else tag
        t = p.get("type")
        if not isinstance(t, str) or t not in types:
            P.append("%s: type %r is not a part the kit has (kit3d.js catalogue%s)" % (tag, t, ", or kit3d_parts.js"))
            entry = {}
        else:
            entry = types[t]
        if "at" in p and not is_at(p["at"]):
            P.append("%s: \"at\" must be 3 numbers [x, y, z], not %r" % (tag, p["at"]))
        if pid is None:
            continue
        mine = ([pid] if isinstance(pid, str) else []) + sub_ids(p, entry, parts)
        if not isinstance(pid, str):
            P.append("%s: id must be a string" % tag)
        # the same id on several entries is ONE part made of them all - a space's pipes and valves are that space
        # (kit3d.js build loop; IGF M01 'tcs' is a hull space and its three pipes and valves) - so a repeat is no problem
        seen |= set(mine)
        if isinstance(pid, str):
            part_ids.add(pid)
            states |= {"%s.%s" % (pid, s) for s in entry.get("states", []) + ["ghost"]}   # every part can turn see-through
        ids |= set(mine)

    # -- groups
    groups = spec.get("groups") if isinstance(spec.get("groups"), dict) else {}
    if spec.get("groups") is not None and not isinstance(spec.get("groups"), dict):
        P.append("groups must be an object {name: [part ids]}")
    for g, members in groups.items():
        for m in members if isinstance(members, list) else []:
            if not isinstance(m, str) or m not in ids:
                P.append("group %r: member %r is not a part" % (g, m))
    named = ids | set(groups)

    def states_ok(d, where):
        if not isinstance(d, dict):
            P.append("%s: states must be an object {\"part.state\": value}" % where)
            return
        for k in d:
            if k not in states:
                P.append("%s: state %r does not exist (states come from the part's type: %s)"
                         % (where, k, ", ".join(sorted(states)) or "no part here has one"))

    def names_ok(v, where, what):
        for n in v if isinstance(v, list) else [v]:
            if not isinstance(n, str) or n not in named:
                P.append("%s: %s %r is no part, sub-part or group" % (where, what, n))

    states_ok(spec.get("states", {}), "scene")

    # -- labels
    labels = spec.get("labels") if isinstance(spec.get("labels"), list) else []
    label_parts = set()
    for i, lb in enumerate(labels):
        tag = "label %d" % (i + 1)
        if not isinstance(lb, dict):
            P.append("%s is not an object" % tag)
            continue
        if not (isinstance(lb.get("text"), str) and lb["text"].strip()):
            P.append("%s has no \"text\" - the script's own words for the part" % tag)
        else:
            tag = "label %r" % lb["text"]
        if "part" in lb:
            if isinstance(lb["part"], str):
                label_parts.add(lb["part"])
            if not isinstance(lb["part"], str) or lb["part"] not in named:
                P.append("%s: part %r is neither a part id, a sub-part id nor a group" % (tag, lb["part"]))
        elif "at" not in lb:
            P.append("%s has neither a \"part\" nor an \"at\" - nothing to sit on" % tag)
        if "at" in lb and not is_at(lb["at"]):
            P.append("%s: \"at\" must be 3 numbers [x, y, z], not %r" % (tag, lb["at"]))
        if "when" in lb:
            m = WHEN.match(lb["when"].strip()) if isinstance(lb["when"], str) else None
            if not m:
                P.append("%s: \"when\" %r is not of the form [!]name [> < >= <= == number]" % (tag, lb["when"]))
            elif m.group(2) not in states:
                P.append("%s: \"when\" names state %r that does not exist" % (tag, m.group(2)))

    # -- steps
    steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
    for i, st in enumerate(steps):
        tag = "step %d" % i
        if not isinstance(st, dict):
            P.append("%s is not an object" % tag)
            continue
        view_ok(st.get("view"), tag)
        if isinstance(st.get("view"), dict) and "frame" in st["view"]:
            names_ok(st["view"]["frame"], tag + " view.frame", "frame part")
        if "state" in st:
            states_ok(st["state"], tag)
        if "select" in st:
            names_ok(st["select"], tag + " select", "part")
        if "labels" in st:
            names_ok(st["labels"], tag + " labels", "label part")
            label_parts |= {x for x in st["labels"] if isinstance(x, str)} if isinstance(st["labels"], list) else set()
        ln = st.get("line")
        if "line" in st and not (isinstance(ln, list) and ln and all(isinstance(x, int) and not isinstance(x, bool) for x in ln)
                                 or (isinstance(ln, int) and not isinstance(ln, bool))):
            P.append("%s: \"line\" must be an integer or a list of integers (the slide's data-i), not %r" % (tag, ln))
        elif min(step_lines(st) or [1]) < 1:
            P.append("%s: \"line\" %d is not a line of the slide - %s" % (tag, min(step_lines(st)), FROM_ONE))

    # -- controls
    controls = spec.get("controls") if isinstance(spec.get("controls"), list) else []
    for i, c in enumerate(controls):
        tag = "control %d" % (i + 1)
        if not isinstance(c, dict):
            P.append("%s is not an object" % tag)
            continue
        if isinstance(c.get("text"), str):
            tag = "control %r" % c["text"]
        if not any(k in c for k in ("state", "select", "step")):
            P.append("%s does nothing - give it a state, a select or a step" % tag)
        if "state" in c:
            states_ok(c["state"], tag)
        if "select" in c:
            names_ok(c["select"], tag + " select", "part")
        if "step" in c and not (isinstance(c["step"], int) and not isinstance(c["step"], bool)
                                and 0 <= c["step"] < len(steps)):
            P.append("%s: step %r is out of range (the scene has %d step(s))" % (tag, c["step"], len(steps)))
        view_ok(c.get("view"), tag)
        if isinstance(c.get("view"), dict) and "frame" in c["view"]:
            names_ok(c["view"]["frame"], tag + " view.frame", "frame part")

    # ---------------------------------------------------------------- notes
    # a part is "named" when a label names it, one of its sub-parts, or a group it is in
    covered = set(label_parts)
    for p in parts:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            if set(sub_ids(p, types.get(p.get("type"), {}), parts)) & label_parts:
                covered.add(p["id"])
    for g, members in groups.items():
        if g in label_parts and isinstance(members, list):
            covered |= set(members)
    for p in parts:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or p.get("pick") is False:
            continue
        fam = types.get(p.get("type"), {}).get("family")
        # a measure writes its own value on the screen; it needs no label of ours
        if p["id"] not in covered and fam not in ("measures", "effects"):     # gas and flow are never tapped
            N.append("part %r: a part nobody names - give it a label or \"pick\": false" % p["id"])
    for i, st in enumerate(steps):
        if not isinstance(st, dict):
            continue
        # approximate: "when" is ignored (it depends on states that move while the step plays)
        n = 0
        for lb in labels:
            if not isinstance(lb, dict) or lb.get("tap_only"):
                continue
            if isinstance(lb.get("steps"), list) and i not in lb["steps"]:
                continue
            if isinstance(st.get("labels"), list) and lb.get("part") not in st["labels"]:
                continue
            n += 1
        if n > MAX_LABELS or n < MIN_LABELS:
            N.append("step %d shows %d label(s) - %s" % (
                i, n, "more than %d is a second step" % MAX_LABELS if n > MAX_LABELS
                else "fewer than %d: what is there to read?" % MIN_LABELS))
    if not steps and not controls:
        N.append("one view only - is there an inside to open or a part to show?")
    if not spec.get("units"):
        N.append("\"units\" missing - say \"m\": one unit is a metre")
    P.extend(deck_problems(spec))
    P.extend(join_problems(spec, types))
    P.extend(stand_in_problems(spec))
    P.extend(construction_problems(spec))
    P.extend(label_problems(spec, types))
    return P, N


# 2.72.0 - parts that stand on the open deck: never below it, inside the hull (IGF 2.71.0's 2D vent mast inside the ship)
ON_DECK = ("vent_mast", "drip_tray", "esd_button", "air_intake")


def deck_level(h, lvl="deck"):
    """the world height of a hull's (or a deck plate's) deck, floor or bottom - as kit3d.js deckLevel()"""
    n = lambda v, d: v if isinstance(v, (int, float)) and not isinstance(v, bool) else d
    y0 = (h.get("at") or [0, 0, 0])[1] if is_at(h.get("at")) else 0
    if h.get("type") == "deck_plate":
        return y0
    bot = n(h.get("bottom"), 0)
    fl = n(h.get("floor"), bot + 1.2)
    return y0 + {"floor": fl, "bottom": bot}.get(lvl, n(h.get("top"), fl + 9))


def deck_problems(spec):
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    hulls = {p.get("id"): p for p in parts if p.get("type") in ("hull", "deck_plate") and p.get("id")}
    out = []
    for p in parts:
        on = p.get("on")
        if isinstance(on, str):
            hid, _, lvl = on.partition(".")
            if hid not in hulls or lvl not in ("deck", "floor", "bottom"):
                out.append("part %s is \"on\": %r - name a hull or deck_plate and its deck, floor or bottom (\"H.deck\")" % (p.get("id") or p.get("type"), on))
            continue                                         # placed by the relation: on its level by construction
        if p.get("type") not in ON_DECK or not is_at(p.get("at")):
            continue
        x, y, z = p["at"]
        for h in hulls.values():
            if h.get("type") != "hull":
                continue
            hx = h.get("x") or [-10, 10]
            ox, _, oz = h["at"] if is_at(h.get("at")) else (0, 0, 0)
            half = h.get("half") or (h.get("breadth") or 12) / 2.0
            if ox + hx[0] <= x <= ox + hx[1] and abs(z - oz) <= half and y < deck_level(h) - 0.05:
                out.append("the %s %s stands at y %g, below the deck of %s (y %g) - inside the hull: it stands ON the open deck - "
                           "\"on\": \"%s.deck\"" % (p["type"], p.get("id") or "", y, h.get("id"), deck_level(h), h.get("id")))
    return out


# parts that join end to end by their ports ("<id>.<port>"): a branch pipe on the inductor's outlet, a hose from the
# hydrant to the inductor, the pick-up wand in the container's mouth - never two pieces set side by side by hand with a
# gap between them
REF = re.compile(r"^([\w-]+)\.(\w+)$")
JOIN_KEYS = ("connect", "from", "to", "pickup")


def join_refs(p):
    """[(key, "<id>.<port>")] a part names: its "connect" (a string or {"to"}), a hose's "from" / "to" / path points, an
    inductor's "pickup" """
    out = []
    for key in JOIN_KEYS:
        v = p.get(key)
        if key == "connect" and isinstance(v, dict):
            v = v.get("to")
        if isinstance(v, str):
            out.append((key, v))
    for v in p.get("path") if isinstance(p.get("path"), list) else []:
        if isinstance(v, str):
            out.append(("path", v))
    return out


def join_problems(spec, types):
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    by_id = {p["id"]: p for p in parts if isinstance(p.get("id"), str)}
    out, joined = [], set()
    for p in parts:
        who = p.get("id") or p.get("type")
        for key, ref in join_refs(p):
            m = REF.match(ref)
            q = by_id.get(m.group(1)) if m else None
            if not m or q is None:
                out.append("part %s: %s %r names no part's port - \"<id>.<port>\"" % (who, key, ref))
                continue
            ports = types.get(q.get("type"), {}).get("ports") or []
            if m.group(2) not in ports:
                out.append("part %s: %s %r - a %s has no port %r (it has %s)" % (who, key, ref, q.get("type"), m.group(2),
                                                                             ", ".join(ports) or "none"))
                continue
            joined.add(ref)
            if key == "connect":
                c = p.get("connect")
                own = c.get("port", "in") if isinstance(c, dict) else "in"
                if own not in (types.get(p.get("type"), {}).get("ports") or []):
                    out.append("part %s: \"connect\" joins its port %r - a %s has none (PARTS.md)" % (who, own, p.get("type")))
                elif isinstance(p.get("id"), str):
                    joined.add("%s.%s" % (p["id"], own))
            elif key == "from" and isinstance(p.get("id"), str):
                joined.add(p["id"] + ".start")
    containers = [i for i, q in by_id.items() if q.get("type") == "foam_container"]
    for i, q in by_id.items():
        t = q.get("type")
        if t == "foam_branch_pipe" and i + ".in" not in joined:
            out.append("the foam branch pipe %s is joined to nothing: \"connect\": \"<inductor>.out\" (or a hose \"to\": \"%s.in\") - "
                       "parts set side by side by hand leave a gap between them" % (i, i))
        if t == "foam_inductor":
            for port, how in (("in", "a fire hose \"to\": \"%s.in\"" % i), ("out", "the branch pipe's \"connect\": \"%s.out\" "
                                                                                     "(or a hose \"from\": \"%s.out\")" % (i, i))):
                if "%s.%s" % (i, port) not in joined:
                    out.append("the inductor %s: its %s is joined to nothing - %s" % (i, "inlet" if port == "in" else "outlet", how))
            if containers and not isinstance(q.get("pickup"), str):
                out.append("the inductor %s: its pick-up tube goes nowhere - \"pickup\": \"%s.mouth\"" % (i, containers[0]))
    return out


# equipment the kit draws, built instead from boxes and cylinders: a red cylinder named "Fire hydrant", a grey one named
# "Inductor" - the stand-in shows nothing of the real thing (no jet, no couplings, no mesh) and joins nothing
STAND_IN = ((re.compile(r"\b(inductor|eductor|ejector|proportioner)\b", re.I), "foam_inductor"),
            (re.compile(r"\b(branch\s*pipe|foam\s*(nozzle|branch|applicator|maker))\b", re.I), "foam_branch_pipe"),
            (re.compile(r"\b(foam|concentrate)\b.*\b(container|can|drum|jerrycan|tank)\b|\bjerry\s*can\b", re.I), "foam_container"),
            (re.compile(r"\bhydrant\b", re.I), "fire_hydrant"),
            # a gas carrier's hull and containment, drawn by the hull and the tanks themselves (M01: wing boxes named
            # "Double hull", a cylinder named "Skirt at the equator", a plate named "Centreline bulkhead")
            (re.compile(r"\bcent(re|er)\s*-?\s*line\s+bulkhead\b", re.I),
             "a tank_prism \"kind\": \"type_a\" \"in\" its hull, or a tank_c \"lobes\": 2 - its sub-part <tank>_bulkhead"),
            (re.compile(r"\bskirt\b", re.I), "a tank_sphere - its sub-part <tank>_skirt, at the equator"),
            (re.compile(r"\bdrip\s+(pan|tray)\b", re.I), "a tank_sphere (or a type_b tank_prism) with \"drip\": true - <tank>_drip"),
            (re.compile(r"\btank\s+cover\b", re.I), "a tank_sphere with \"cover\": true - <tank>_cover"),
            (re.compile(r"\bchocks?\b", re.I), "a tank_prism \"kind\": \"type_a\" \"in\" its hull - <tank>_chocks"),
            (re.compile(r"\b(double\s*-?\s*hull|inner\s+hull|(side|outer)\s+shell|double\s+bottom|wing|hopper|ballast|"
                        r"secondary\s+barrier|hull)\b", re.I),
             "a \"hull\" with \"double\" / \"hopper\" / \"topwing\" - its sub-parts <hull>_outer, _inner, _bottom, _wing, _hopper, _topwing"))
PRIMITIVE = ("box", "cylinder", "sphere")


def stand_in_problems(spec):
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    kinds = {}
    for p in parts:
        if isinstance(p.get("id"), str):
            kinds.setdefault(p["id"], set()).add(p.get("type"))
    out = []
    for lb in spec.get("labels") or []:
        if not isinstance(lb, dict) or not isinstance(lb.get("text"), str):
            continue
        k = kinds.get(lb.get("part"))
        if not k or not k <= set(PRIMITIVE):
            continue
        for rx, kit in STAND_IN:
            if rx.search(lb["text"]):
                out.append("part %s (%s) is named %r - the kit draws that: %s (PARTS.md), not a stand-in"
                           % (lb["part"], "/".join(sorted(k)), lb["text"], kit if " " in kit else "\"type\": \"%s\"" % kit))
                break
    return out


# ------------------------------------------------------------------ gas carrier construction: what stands where
# A gas carrier's hull, its tanks and what is measured between them, judged from the numbers the kit draws with (kit3d.js
# holdSection / inRelation): two tanks through each other or out through their hull's end wall (M01 s11), a membrane tank
# standing free in its hold (s08, s11), a Moss skirt that does not reach the inner bottom (s13), saddles that end in the air,
# a part inside a tank that is not its content, a dimension ending where nothing is drawn after the cut (s09, s19)
TANKS = ("tank_c", "tank_sphere", "tank_prism")
LINING = ("membrane", "semi_membrane")
# parts that are not judged as standing inside a tank: what measures or flows, pipes (a fill line starts inside), the hull
NOT_CONTENT = ("dimension", "limit_box", "zone", "gas", "arrow", "flow", "pipe", "pipe_dw", "hose", "hull", "deck_plate") + TANKS
# parts whose "at" is the centre of their floor and whose "size" is [w, h, d]
BASE_SIZED = ("room", "enclosure", "cabinet", "accommodation")


def nv(v, d):
    return v if num(v) else d


def hold_section(h):
    """the hull's numbers and its hold's section [[z, y] ...] in its own coordinates - as kit3d.js holdSection()"""
    hz = nv(h.get("half"), nv(h.get("breadth"), 12) / 2.0)
    bot = nv(h.get("bottom"), 0)
    fl = nv(h.get("floor"), bot + 1.2)
    top = nv(h.get("top"), fl + 9)
    zi = hz - nv(h.get("double"), 0)
    hp = h.get("hopper") if isinstance(h.get("hopper"), list) and len(h["hopper"]) == 2 else [0, 0]
    tw = h.get("topwing") if isinstance(h.get("topwing"), list) and len(h["topwing"]) == 2 else [0, 0]
    a, b, c, e = nv(hp[0], 0), nv(hp[1], 0), nv(tw[0], 0), nv(tw[1], 0)
    raw = [[-(zi - a), fl], [zi - a, fl], [zi, fl + b], [zi, top - e], [zi - c, top], [-(zi - c), top], [-zi, top - e], [-zi, fl + b]]
    pts = []
    for q in raw:
        if not pts or abs(pts[-1][0] - q[0]) + abs(pts[-1][1] - q[1]) > 1e-6:
            pts.append(q)
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) + abs(pts[0][1] - pts[-1][1]) < 1e-6:
        pts.pop()
    return {"hz": hz, "zi": zi, "bot": bot, "fl": fl, "top": top, "hw": a, "hh": b, "tw": c, "th": e, "pts": pts,
            "inner": zi < hz - 1e-6 or b > 0 or e > 0}


def turned(p):
    """a part turned round the vertical by other than a half turn: its box is not judged here"""
    r = nv(p.get("rot"), 0) % 180
    return abs(r) > 1e-6


def hold_of(parts, ref):
    """(hull, [x0, x1] in the hull's coordinates) a tank's "in" names: a hull, or one of its spaces"""
    for q in parts:
        if q.get("type") != "hull":
            continue
        if q.get("id") == ref:
            return q, q.get("x") or [-10, 10]
        for s in q.get("spaces") or []:
            if isinstance(s, dict) and s.get("id") == ref and isinstance(s.get("x"), list):
                return q, s["x"]
    return None, None


def seat(p, parts):
    """the tank as the kit builds it: its "in" applied (kit3d.js inRelation) - a copy with at, base, len and _hold"""
    if p.get("type") not in TANKS or not isinstance(p.get("in"), str):
        return p
    h, x = hold_of(parts, p["in"])
    if h is None:
        return p
    q = dict(p)
    o = h["at"] if is_at(h.get("at")) else [0, 0, 0]
    sec = hold_section(h)
    X0, X1 = o[0] + x[0], o[0] + x[1]
    own = is_at(p.get("at"))
    ax, az = (p["at"][0], p["at"][2]) if own else ((X0 + X1) / 2.0, o[2])
    R = nv(p.get("r"), 5 if p["type"] == "tank_sphere" else 3)
    ins = nv(p.get("insulation"), 0)
    fl = o[1] + sec["fl"]
    q["_hold"] = {"sec": sec, "x0": X0, "x1": X1, "y0": o[1], "z0": o[2], "hull": h.get("id")}
    if p["type"] == "tank_prism":
        q["at"] = [(X0 + X1) / 2.0, o[1], o[2]]
    elif p["type"] == "tank_sphere":
        hh = nv(p.get("skirt"), (R + ins) * 1.25)
        q["at"], q["base"], q["_deck"] = [ax, fl + hh, az], -hh, o[1] + sec["top"] - (fl + hh)
    else:
        hh = nv(p.get("clear"), max(0.5, R * 0.15)) + R + ins
        q["at"], q["base"] = [ax, fl + hh, az], -hh
        if p.get("len") is None:
            q["len"] = max(1, (X1 - X0) - 2 * nv(p.get("head"), R / 2.0) - 2)
    return q


def lining(p):
    """a tank_prism drawn as a membrane or semi-membrane tank: its kind, the kit's default kind, or a membrane layer"""
    if p.get("kind") in LINING:
        return True
    lay = p.get("layers")
    if isinstance(lay, list):
        return any(isinstance(x, dict) and x.get("mat") == "membrane" for x in lay)
    return p.get("kind") is None


def tank_box(p):
    """a tank's body [x0, y0, z0, x1, y1, z1] in the world (a seated copy): its insulation, both lobes of a bilobe, a sphere
    without its skirt; a tank_prism cut "end" is the half that is drawn"""
    x, y, z = p["at"]
    t = p["type"]
    ins = nv(p.get("insulation"), 0)
    if t == "tank_c":
        R = nv(p.get("r"), 3)
        e = nv(p.get("len"), 10) / 2.0 + nv(p.get("head"), R / 2.0)
        w = R + ins + (nv(p.get("spread"), R * 0.55) if nv(p.get("lobes"), 1) >= 2 else 0)
        return [x - e, y - R - ins, z - w, x + e, y + R + ins, z + w]
    if t == "tank_sphere":
        R = nv(p.get("r"), 5) + ins
        return [x - R, y - R, z - R, x + R, y + R, z + R]
    hold = p.get("_hold")
    if hold:
        sec = hold["sec"]
        clear = 0 if lining(p) else nv(p.get("clear"), 0.8)
        return [hold["x0"] + clear, hold["y0"] + sec["fl"] + clear, hold["z0"] - sec["zi"] + clear,
                hold["x1"] - clear, hold["y0"] + sec["top"] - clear, hold["z0"] + sec["zi"] - clear]
    s = p.get("size") if isinstance(p.get("size"), list) and len(p["size"]) == 3 else [20, 12, 14]
    b = [x - s[0] / 2.0, y - s[1] / 2.0, z - s[2] / 2.0, x + s[0] / 2.0, y + s[1] / 2.0, z + s[2] / 2.0]
    if p.get("cut", "end") == "end":
        b[3] = x
    return b


def overlap(a, b, tol=0.1):
    return all(min(a[i + 3], b[i + 3]) - max(a[i], b[i]) > tol for i in range(3))


def inside_tank(pt, p):
    """is the point inside the tank's body (its true shape)"""
    x, y, z = (pt[i] - p["at"][i] for i in range(3))
    t = p["type"]
    if t == "tank_c":
        R = nv(p.get("r"), 3)
        L2, A = nv(p.get("len"), 10) / 2.0, nv(p.get("head"), R / 2.0)
        d = nv(p.get("spread"), R * 0.55) if nv(p.get("lobes"), 1) >= 2 else 0
        rho = min((y * y + (z - c) ** 2) ** 0.5 for c in ((-d, d) if d else (0,)))
        u = max(0.0, abs(x) - L2) / A if A > 0 else 0
        return (u * u + (rho / R) ** 2) < 1
    if t == "tank_sphere":
        return (x * x + y * y + z * z) ** 0.5 < nv(p.get("r"), 5)
    b = tank_box(p)
    return all(b[i] < pt[i] < b[i + 3] for i in range(3))


def hull_box(h):
    o = h["at"] if is_at(h.get("at")) else [0, 0, 0]
    sec = hold_section(h)
    x = h.get("x") or [-10, 10]
    return [o[0] + x[0], o[1] + sec["bot"], o[2] - sec["hz"], o[0] + x[1], o[1] + sec["top"], o[2] + sec["hz"]], sec, o


def in_hull(pt, h, pad=0.0):
    b, _, _ = hull_box(h)
    return all(b[i] - pad <= pt[i] <= b[i + 3] + pad for i in range(3))


def tank_hull(p, hulls):
    """the hull a tank stands in: its centre over the hull's length and breadth, between its bottom and a tank radius above
    its deck (a Moss sphere's centre is at the deck)"""
    for h in hulls:
        b, sec, o = hull_box(h)
        x, y, z = p["at"]
        if b[0] <= x <= b[3] and b[2] <= z <= b[5] and b[1] <= y <= b[4]:
            return h
    return None


def construction_problems(spec):
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    hulls = [p for p in parts if p.get("type") == "hull" and not turned(p)]
    ids = {p.get("id") for p in parts if isinstance(p.get("id"), str)}
    out = []
    tanks = []
    for p in parts:
        if p.get("type") in TANKS and isinstance(p.get("in"), str):
            h, _ = hold_of(parts, p["in"])
            if h is None:
                out.append("part %s is \"in\": %r - no hull or hull space of that id: a tank is \"in\" the hull (or the space) it "
                           "stands in" % (p.get("id") or p["type"], p["in"]))
        q = seat(p, parts)
        if q.get("type") in TANKS and is_at(q.get("at")) and not turned(q):
            tanks.append(q)
    # -- two tanks through each other
    for i, a in enumerate(tanks):
        for b in tanks[i + 1:]:
            ba, bb = tank_box(a), tank_box(b)
            if not overlap(ba, bb):
                continue
            side = a["type"] == b["type"] == "tank_c" and abs(a["at"][0] - b["at"][0]) < 0.5 and abs(a["at"][1] - b["at"][1]) < 0.5
            out.append("tanks %s and %s pass through each other (x %g..%g and %g..%g) - %s" % (
                a.get("id") or a["type"], b.get("id") or b["type"], round(ba[0], 2), round(ba[3], 2), round(bb[0], 2), round(bb[3], 2),
                "a bilobe tank is ONE tank_c with \"lobes\": 2 (its centreline bulkhead comes with it)" if side
                else "each tank needs its own room: \"in\": \"<hull>\" with its own \"at\" x, or a shorter \"len\""))
    for q in tanks:
        who = q.get("id") or q["type"]
        h = next((x for x in hulls if x.get("id") == (q.get("_hold") or {}).get("hull")), None) or tank_hull(q, hulls)
        if h is None:
            continue
        hb, sec, o = hull_box(h)
        tb = tank_box(q)
        fl, top = o[1] + sec["fl"], o[1] + sec["top"]
        # -- out through the hull's end walls or its sides, down through its double bottom
        if tb[0] < hb[0] - 0.05 or tb[3] > hb[3] + 0.05:
            out.append("tank %s runs out through the end walls of hull %s (the tank x %g..%g, the hull x %g..%g) - \"in\": \"%s\" "
                       "fits it to the hold" % (who, h.get("id"), round(tb[0], 2), round(tb[3], 2), hb[0], hb[3], h.get("id")))
        if tb[2] < hb[2] - 0.05 or tb[5] > hb[5] + 0.05:
            out.append("tank %s runs out through the side shell of hull %s - it is wider than the hull" % (who, h.get("id")))
        if q["type"] != "tank_prism" and tb[1] < fl - 0.05 and q["at"][1] < top:
            out.append("tank %s goes down through the double bottom of hull %s (its bottom y %g, the inner bottom y %g) - "
                       "\"in\": \"%s\" seats it" % (who, h.get("id"), round(tb[1], 2), fl, h.get("id")))
        if q.get("_hold"):
            continue                                        # seated by the kit: the rest holds by construction
        hid = h.get("id")
        if q["type"] == "tank_prism" and lining(q):
            out.append("membrane tank %s stands free in hull %s - a membrane (or semi-membrane) tank is not self-supporting: it "
                       "lines the inner hull with no gap, its load through the insulation into the hull - \"in\": \"%s\"" % (who, hid, hid))
        elif q["type"] == "tank_prism":
            out.append("prismatic tank %s is placed by hand in hull %s - \"in\": \"%s\" with \"kind\": \"type_a\" (or \"type_b\") "
                       "stands it clear of the hull on its chocks, insulated, with its centreline bulkhead" % (who, hid, hid))
        elif q["type"] == "tank_sphere":
            base = nv(q.get("base"), -nv(q.get("r"), 5) * 1.25)
            foot = q["at"][1] + base
            if base >= 0 or abs(foot - fl) > 0.15:
                out.append("Moss sphere %s: its skirt %s - the skirt carries the sphere at its equator and stands on the inner "
                           "bottom (y %g): \"in\": \"%s\"" % (who, "has no height (\"base\" %g is not below the centre)" % base
                                                             if base >= 0 else "ends at y %g" % round(foot, 2), fl, hid))
        else:
            R = nv(q.get("r"), 3)
            foot = q["at"][1] + nv(q.get("base"), -R - 0.6)
            ground = top if q["at"][1] - R > top - 0.05 else fl
            if abs(foot - ground) > 0.15:
                out.append("tank %s: its saddles end at y %g, the %s is at y %g - the tank %s: \"in\": \"%s\" stands it on its saddles"
                           % (who, round(foot, 2), "deck" if ground == top else "inner bottom", ground,
                              "stands on nothing" if foot > ground else "sinks into the hull", hid))
    # -- a part inside a tank that is not its content
    for p in parts:
        t = p.get("type")
        if t in NOT_CONTENT or not is_at(p.get("at")) or isinstance(p.get("on"), str):
            continue
        for q in tanks:
            if p.get("id") is not None and p.get("id") == q.get("id"):
                continue
            box = prim_box(p)
            if all(inside_tank(c, q) for c in (corners(box) if box else [p["at"]])) and p.get("in") != q.get("id"):
                out.append("%s %s stands inside tank %s - only the tank's own content goes there (a submerged pump: \"in\": \"%s\"); "
                           "put it where it is on board" % (t, p.get("id") or "", q.get("id") or q["type"], q.get("id") or q["type"]))
    out += dimension_problems(parts, hulls, tanks)
    return sorted(set(out), key=out.index)              # two entries of one id: one sentence


# ------------------------------------------------------------------ a dimension measures between two things drawn
def seg_dist(p, a, b):
    """distance from point p to the segment a-b (2D)"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1e-12
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return ((p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2) ** 0.5


def box_dist(pt, b):
    """distance from a point to a box (0 inside)"""
    d = [max(b[i] - pt[i], 0, pt[i] - b[i + 3]) for i in range(3)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def face_dist(pt, b):
    """distance from a point to a box's surface"""
    if box_dist(pt, b) > 0:
        return box_dist(pt, b)
    return min(min(pt[i] - b[i], b[i + 3] - pt[i]) for i in range(3))


def on_hull(pt, h, tol):
    b, sec, o = hull_box(h)
    if box_dist(pt, b) > tol:
        return False
    x, y, z = pt[0], pt[1] - o[1], pt[2] - o[2]
    if face_dist(pt, b) <= tol or abs(y - sec["fl"]) <= tol:
        return True
    xs = [b[0], b[3]] + [o[0] + s["x"][k] for s in h.get("spaces") or [] if isinstance(s, dict) and isinstance(s.get("x"), list) for k in (0, 1)]
    if any(abs(x - v) <= tol for v in xs):
        return True
    if sec["inner"]:
        pts = sec["pts"]
        return any(seg_dist((z, y), pts[i], pts[(i + 1) % len(pts)]) <= tol for i in range(len(pts)))
    return False


def on_tank(pt, q, tol):
    """on the tank's drawn surface - not on the half a cut took away"""
    x, y, z = (pt[i] - q["at"][i] for i in range(3))
    t = q["type"]
    ins = nv(q.get("insulation"), 0)
    if t == "tank_c":
        R = nv(q.get("r"), 3)
        two = nv(q.get("lobes"), 1) >= 2
        if q.get("cut") and (x > tol if two else z > tol):
            return False
        L2, A = nv(q.get("len"), 10) / 2.0, nv(q.get("head"), R / 2.0)
        d = nv(q.get("spread"), R * 0.55) if two else 0
        rho = min((y * y + (z - c) ** 2) ** 0.5 for c in ((-d, d) if d else (0,)))
        for r in (R, R + ins):
            if abs(x) <= L2 and abs(rho - r) <= tol:
                return True
            if abs(x) > L2 and A > 0 and abs((((abs(x) - L2) / A * r) ** 2 + rho ** 2) ** 0.5 - r) <= tol:
                return True
        base = nv(q.get("base"), -R - 0.6)                  # a saddle's foot or its side
        return base - tol <= y <= 0 and abs(z) <= R + tol and abs(x) <= L2
    if t == "tank_sphere":
        if q.get("cut") and z > tol:
            return False
        R = nv(q.get("r"), 5)
        r = (x * x + y * y + z * z) ** 0.5
        if abs(r - R) <= tol or abs(r - R - ins) <= tol:
            return True
        base = nv(q.get("base"), -R * 1.25)
        return base - tol <= y <= 0 and abs((x * x + z * z) ** 0.5 - R - ins) <= tol
    b = tank_box(q)
    if q.get("cut") in ("front", True) and pt[2] > q["at"][2] + tol:
        return False
    return face_dist(pt, b) <= tol


def prim_box(p):
    """the box of a box, cylinder or sphere primitive, a limit_box (world), else None"""
    t, a = p.get("type"), p.get("at") if is_at(p.get("at")) else [0, 0, 0]
    if turned(p):
        return None
    if t == "box":
        s = p.get("size") if isinstance(p.get("size"), list) and len(p["size"]) == 3 else [1, 1, 1]
        return [a[i] - s[i] / 2.0 for i in range(3)] + [a[i] + s[i] / 2.0 for i in range(3)]
    if t == "cylinder":
        r, ln, ax = nv(p.get("r"), 0.5), nv(p.get("len"), 1), p.get("axis") or "y"
        e = [r, r, r]
        e["xyz".index(ax) if ax in ("x", "y", "z") else 1] = ln / 2.0
        return [a[i] - e[i] for i in range(3)] + [a[i] + e[i] for i in range(3)]
    if t == "sphere":
        r = nv(p.get("r"), 0.5)
        return [a[i] - r for i in range(3)] + [a[i] + r for i in range(3)]
    if t == "limit_box" and is_at(p.get("min")) and is_at(p.get("max")):
        return [a[i] + p["min"][i] for i in range(3)] + [a[i] + p["max"][i] for i in range(3)]
    if t == "deck_plate":                                   # its top at "at", the ship's side at z, inboard -z
        s = p.get("size") if isinstance(p.get("size"), list) and len(p["size"]) == 2 else [6, 5]
        return [a[0] - s[0] / 2.0, a[1] - nv(p.get("thick"), 0.3), a[2] - s[1], a[0] + s[0] / 2.0, a[1], a[2]]
    if t in BASE_SIZED and isinstance(p.get("size"), list) and len(p["size"]) == 3:
        s = p["size"]
        return [a[0] - s[0] / 2.0, a[1], a[2] - s[2] / 2.0, a[0] + s[0] / 2.0, a[1] + s[1], a[2] + s[2] / 2.0]
    return None


def corners(b):
    return [[b[0] if i & 1 else b[3], b[1] if i & 2 else b[4], b[2] if i & 4 else b[5]] for i in range(8)]


def dimension_problems(parts, hulls, tanks):
    """each end of a dimension sits on something drawn: a hull's plating, a tank's wall (not on the half a cut took away),
    a box, a limit. Judged where the end is inside a hull or within a metre of a part the checker can draw; elsewhere (a
    deckhouse, a mast) it is not judged"""
    out, boxes = [], [b for b in (prim_box(p) for p in parts if p.get("type") != "dimension") if b]
    for p in parts:
        if p.get("type") != "dimension" or not (is_at(p.get("a")) and is_at(p.get("b"))):
            continue
        o = p["at"] if is_at(p.get("at")) else [0, 0, 0]
        a = [o[i] + p["a"][i] for i in range(3)]
        b = [o[i] + p["b"][i] for i in range(3)]
        ln = sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5
        tol = max(0.25, 1.5 * nv(p.get("r"), max(0.02, ln * 0.02)))
        for end, pt in (("a", a), ("b", b)):
            near = any(in_hull(pt, h, tol) for h in hulls) or any(box_dist(pt, tank_box(q)) <= 1.0 for q in tanks) \
                or any(box_dist(pt, x) <= 1.0 for x in boxes)
            if not near:
                continue
            if any(on_hull(pt, h, tol) for h in hulls) or any(on_tank(pt, q, tol) for q in tanks) \
                    or any(face_dist(pt, x) <= tol for x in boxes):
                continue
            hit = next((q for q in tanks if box_dist(pt, tank_box(q)) <= 1.5), None)
            out.append("dimension %s: its end %s [%s] ends in the air - on no hull plating, %s - a dimension runs between two "
                       "surfaces you can see (with a cut, the half that is drawn)" % (
                           p.get("id") or "", end, ", ".join("%g" % round(v, 2) for v in pt),
                           "not on tank %s (%s)" % (hit.get("id") or hit["type"], "past its end" if abs(pt[0] - hit["at"][0]) > nv(hit.get("len"), 10) / 2.0
                                                    else "on the half its cut took away" if hit.get("cut") else "off its wall")
                           if hit else "no part"))
    return out


# ------------------------------------------------------------------ a label names the part its dot is on
HULL_WORDS = re.compile(r"\b(double\s*-?\s*hull|inner\s+hull|hull\s+(steel|structure|plating)|side\s+shell|outer\s+shell|"
                        r"double\s+bottom|wing\s+(tank|ballast)|top\s*-?\s*wing|hopper|secondary\s+barrier)\b", re.I)
NEGATION = re.compile(r"\b(no|not|without|never|none)\b", re.I)
DOUBLE_HULL = re.compile(r"\bdouble\s*-?\s*hull", re.I)
SINGLE_HULL = re.compile(r"\bsingle\s*-?\s*(hull|side|skin)", re.I)
HULL_SUBS = ("bottom", "outer", "inner", "wing", "hopper", "topwing")


def hull_roles(parts, types):
    """{id: (hull spec, role)} for a hull and every sub-part it makes: role "hull", "bottom", "side", "space", or one of the
    double hull's (outer, inner, wing, hopper, topwing)"""
    roles = {}
    for h in parts:
        if h.get("type") != "hull" or not isinstance(h.get("id"), str):
            continue
        hid = h["id"]
        roles[hid] = (h, "hull")
        sec = hold_section(h)
        given = h.get("subs") if isinstance(h.get("subs"), dict) else {}
        if isinstance(h.get("bottom_id"), str):
            roles[h["bottom_id"]] = (h, "bottom")
        if isinstance(h.get("side_id"), str):
            roles[h["side_id"]] = (h, "outer" if sec["inner"] else "side")
        for s in h.get("spaces") or []:
            if isinstance(s, dict) and isinstance(s.get("id"), str):
                roles[s["id"]] = (h, "space")
        if sec["inner"]:
            for name in HULL_SUBS:
                sid = given.get(name) or "%s_%s" % (hid, name)
                if name == "bottom" and isinstance(h.get("bottom_id"), str) or name == "outer" and isinstance(h.get("side_id"), str):
                    continue
                roles[sid] = (h, name)
    return roles


def label_problems(spec, types):
    parts = [p for p in spec.get("parts") or [] if isinstance(p, dict)]
    roles = hull_roles(parts, types)
    tank_ids = {}
    for p in parts:
        if p.get("type") in TANKS and isinstance(p.get("id"), str):
            tank_ids[p["id"]] = p["type"]
            f = p.get("fill")
            if num(f) and f > 0:
                given = p.get("subs") if isinstance(p.get("subs"), dict) else {}
                tank_ids[given.get("liquid") or p["id"] + "_liquid"] = p["type"]
    out = []
    labels = [lb for lb in spec.get("labels") or [] if isinstance(lb, dict) and isinstance(lb.get("text"), str)]
    for lb in labels:
        txt, part = lb["text"], lb.get("part")
        if part in tank_ids and HULL_WORDS.search(txt) and not NEGATION.search(txt):
            out.append("label %r names the hull's structure but its dot is on tank %s - name the hull's own sub-part (a hull with "
                       "\"double\" / \"hopper\" / \"topwing\": <hull>_outer, _inner, _bottom, _wing, _hopper, _topwing)" % (txt, part))
        r = roles.get(part)
        if DOUBLE_HULL.search(txt) and not NEGATION.search(txt):
            if r and (r[1] in ("bottom", "space", "side") or not hold_section(r[0])["inner"]):
                out.append("label %r is on %s, %s - a double hull is the inner hull and the outer shell with the wing tanks between "
                           "them: give the hull \"double\" and name <hull>_inner / _outer / _wing" % (
                               txt, part, "the double bottom" if r[1] == "bottom" else "a hull drawn with one side shell"))
        if SINGLE_HULL.search(txt) and r and (r[1] == "bottom" or r[1] in HULL_SUBS and hold_section(r[0])["zi"] < hold_section(r[0])["hz"]):
            out.append("label %r is on %s, %s - a single hull is the side shell of a hull with no \"double\"" % (
                txt, part, "the double bottom" if r[1] == "bottom" else "a part of a double hull"))
    # -- two dots of one part on one spot: the second name reads as the first's
    steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
    seen = set()
    for i in range(max(1, len(steps))):
        st = steps[i] if i < len(steps) and isinstance(steps[i], dict) else {}
        shown = []
        for lb in labels:
            if lb.get("tap_only") or lb.get("tag") or isinstance(lb.get("steps"), list) and steps and i not in lb["steps"]:
                continue
            if isinstance(st.get("labels"), list) and lb.get("part") not in st["labels"]:
                continue
            shown.append(lb)
        for j, a in enumerate(shown):
            for b in shown[j + 1:]:
                if (a["text"], b["text"]) in seen:
                    continue
                if a.get("part") is None or a.get("part") != b.get("part") or a.get("when") != b.get("when"):
                    continue
                same = (is_at(a.get("at")) and is_at(b.get("at")) and sum((a["at"][k] - b["at"][k]) ** 2 for k in range(3)) ** 0.5 < 1.0) \
                    or (not a.get("at") and not b.get("at") and a.get("anchor") == b.get("anchor"))
                if same:
                    seen.add((a["text"], b["text"]))
                    out.append("step %d: labels %r and %r put two dots on one spot of %s - one label a point: the second fact is "
                               "the first label's words, another part's label or another step" % (i, a["text"], b["text"], a["part"]))
        out += hidden_dots(spec, types, parts, st, i, shown, seen)
    return out


# ------------------------------------------------------------------ a dot hidden behind a tank
# A label's pill is drawn over the picture wherever its dot is: a dot behind a solid tank looks as if it were on the tank, and
# the name reads as the tank's (M01 s12: "Low-temperature hull steel" on the far side shell, seen on the tank's wall)
def removed(q, pt):
    """is the point on the half of the tank its cut took away"""
    x, z = pt[0] - q["at"][0], pt[2] - q["at"][2]
    c = q.get("cut")
    if q["type"] == "tank_c":
        return bool(c) and (x > 0 if nv(q.get("lobes"), 1) >= 2 else z > 0)
    if q["type"] == "tank_sphere":
        return bool(c) and z > 0
    if not q.get("_hold") and q.get("cut", "end") == "end":
        return x > 0
    return c in ("front", True) and z > 0


def solid(q, pt):
    return inside_tank(pt, q) if q["type"] in TANKS else all(q["_box"][i] <= pt[i] <= q["_box"][i + 3] for i in range(3))


def hidden_dots(spec, types, parts, st, i, shown, seen):
    view = st.get("view") if isinstance(st.get("view"), dict) else spec.get("view") if isinstance(spec.get("view"), dict) else {}
    az, el = nv(view.get("az"), 24) * 0.0174533, nv(view.get("el"), 23) * 0.0174533
    d = [math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el)]
    owner = {}
    for p in parts:
        if isinstance(p.get("id"), str):
            for s in sub_ids(p, types.get(p.get("type"), {}), parts):
                owner[s] = p["id"]
    walls = [q for q in (seat(p, parts) for p in parts) if q.get("type") in TANKS and is_at(q.get("at")) and not turned(q)]
    for p in parts:
        b = prim_box(p) if p.get("type") in PRIMITIVE and not (num(p.get("opacity")) and p["opacity"] < 0.95) else None
        if b:
            walls.append(dict(p, _box=b))
    out = []
    for lb in shown:
        if not is_at(lb.get("at")) or ("hidden", lb["text"]) in seen:
            continue
        mine = {lb.get("part"), owner.get(lb.get("part"))}
        for q in walls:
            if q.get("id") in mine:
                continue
            p0, t, prev, hit = lb["at"], 0.2, None, False
            while t < 90 and not hit:
                pt = [p0[k] + d[k] * t for k in range(3)]
                cur = solid(q, pt)
                hit = prev is not None and cur != prev and not (q["type"] in TANKS and removed(q, pt))
                prev, t = cur, t + 0.1
            if hit:
                seen.add(("hidden", lb["text"]))
                out.append("step %d: label %r has its dot behind %s %s from this view - the name reads as that part's: put the dot "
                           "where its own part shows, or turn the view" % (i, lb["text"], q["type"], q.get("id") or ""))
                break
    return out


# ------------------------------------------------------------------ the steps and the slide's lines
def step_lines(st):
    """the slide lines a step lights: its "line", one number or a list"""
    ln = st.get("line") if isinstance(st, dict) else None
    return [x for x in (ln if isinstance(ln, list) else [] if ln is None else [ln]) if isinstance(x, int) and not isinstance(x, bool)]


def line_problems(spec, lines, first=0, what="scene"):
    """the scene's steps against its slide's lines 1..lines (gb_deck.js lockFor walks them with one counter): a step lighting
    a line the slide does not have lights nothing, and the lines after the last one a step lights come with the scene standing
    at its last step. Steps that light no line are walked with the lines by the deck, one line each Next. A 2D kit figure is
    walked the same way: first=1 (its steps are counted from the first Next), what="figure\""""
    steps = spec.get("steps") if isinstance(spec.get("steps"), list) else []
    named = sorted({x for st in steps for x in step_lines(st)})
    if not named:
        return []
    out = []
    for i, st in enumerate(steps, first):
        bad = [x for x in step_lines(st) if not 1 <= x <= lines]
        if bad:
            out.append("step %d lights line %d, and the slide has %s - %s" % (
                i, bad[0], "lines 1-%d" % lines if lines > 1 else "one line" if lines else "no line", FROM_ONE))
    last = max([x for x in named if 1 <= x <= lines] or [0])
    if last and last < lines:
        out.append("lines %s come after line %d, the last a step lights: Next reaches %s with the %s standing at its last "
                   "step - give each a step that shows what it says (\"line\": %d ...)" % (
                       ", ".join(str(x) for x in range(last + 1, lines + 1)), last, "them" if lines - last > 1 else "it", what,
                       last + 1))
    return out


def deck_line_problems(page):
    """[(slide id, sentence)] - every 3D-kit scene of a built deck against the lines of its own slide"""
    out = []
    for sid, body in SECTION.findall(page):
        if "data-kit3d=" not in body:
            continue
        lines = len(set(DATA_I.findall(re.sub(r"<svg\b.*?</svg>", "", body, flags=re.S))))
        for m in SCENE.finditer(body):
            try:
                spec = json.loads(m.group(1).replace("<\\/", "</"))
            except ValueError:
                continue
            if isinstance(spec, dict):
                out += [(sid, x) for x in line_problems(spec, lines)]
    return out


# ------------------------------------------------------------------ a module's files
def check_assets(module_dir, kit):
    """when the deck holds a 3D scene: the engine, its stylesheet and three.js ship with it, and they are the factory's"""
    probs = []
    deck = os.path.join(module_dir, "presentation", "index.html")
    if not (os.path.isfile(deck) and "data-kit3d" in read(deck)):
        return probs, False
    # the deck's assets folder sits beside index.html; some modules keep it at the module root
    roots = [os.path.join(module_dir, "presentation", "assets"), os.path.join(module_dir, "assets")]

    def find(rel):
        for r in roots:
            if os.path.isfile(os.path.join(r, rel)):
                return os.path.join(r, rel)
        return None

    for name in ("kit3d.js", "kit3d.css"):
        mine, factory = find(name), os.path.join(kit, name)
        if not mine:
            probs.append("the deck holds a 3D scene but assets/%s is not in the module - copy it from the factory" % name)
        elif not os.path.isfile(factory):
            probs.append("the factory's %s is not there to compare with (%s)" % (name, factory))
        else:
            with open(mine, "rb") as a, open(factory, "rb") as b:
                if a.read() != b.read():
                    probs.append("assets/%s is not the factory's kit3d (a changed copy) - copy it again, never edit it "
                                 "in a module" % name)
    if not find(os.path.join("vendor", "three.min.js")):
        probs.append("the deck holds a 3D scene but assets/vendor/three.min.js is not in the module")
    return probs, True


# ------------------------------------------------------------------ CLI
def report(found, notes, checked, strict, as_json):
    """found / notes: [(file, sentence)]"""
    probs = found + (notes if strict else [])
    if as_json:
        print(json.dumps({"ok": not probs, "checked": checked,
                          "problems": [{"file": f, "text": t} for f, t in found],
                          "notes": [{"file": f, "text": t} for f, t in notes],
                          "strict": strict}, indent=2, ensure_ascii=False))
        return 1 if probs else 0
    for f, t in found:
        print("  - %s%s" % (f + ": " if f else "", t))
    for f, t in notes:
        print("  %s %s%s" % ("-" if strict else "note", f + ": " if f else "", t))
    print(("%d problem(s)" % len(probs)) if probs else "clean", "-", checked)
    return 1 if probs else 0


def check_files(files, types, found, notes):
    for f in files:
        spec, err = load_spec(f)
        if err:
            found.append(("", err))
            continue
        p, n = check_spec(spec, types)
        base = os.path.basename(f)
        found += [(base, x) for x in p]
        notes += [(base, x) for x in n]


def main(argv=None, kit=KIT):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("spec")
    a.add_argument("files", nargs="+")
    a.add_argument("--parts")
    c = sub.add_parser("module")
    c.add_argument("module_dir")
    c.add_argument("--figures")
    for s in (a, c):
        s.add_argument("--strict", action="store_true", help="notes count as problems")
        s.add_argument("--json", action="store_true", help="print a machine report")
    o = ap.parse_args(argv)
    types, why = read_catalog(kit)
    if why:
        print("cannot check - " + why)
        return 2
    found, notes = [], []
    if o.cmd == "spec":
        types.update(local_types(o.parts))
        missing = [f for f in o.files if not os.path.isfile(f)]
        if missing:
            print("nothing to check - not there: %s" % ", ".join(missing))
            return 2
        check_files(o.files, types, found, notes)
        return report(found, notes, "%d spec(s)" % len(o.files), o.strict, o.json)
    if not os.path.isdir(o.module_dir):
        print("nothing to check - %s is not a folder" % o.module_dir)
        return 2
    for r in ("presentation/assets", "assets"):
        types.update(local_types(os.path.join(o.module_dir, r, "kit3d_parts.js")))
    specs = sorted(glob.glob(os.path.join(o.figures, "*.kit3d.json"))) if o.figures else []
    check_files(specs, types, found, notes)
    asset_probs, has_scene = check_assets(o.module_dir, kit)
    found += [("", x) for x in asset_probs]
    if has_scene:
        found += deck_line_problems(read(os.path.join(o.module_dir, "presentation", "index.html")))
    if not specs and not has_scene:
        print("nothing to check - no *.kit3d.json (give --figures) and no data-kit3d in the deck")
        return 2
    return report(found, notes, "%d spec(s)%s" % (len(specs), ", assets checked" if has_scene else ""), o.strict, o.json)


if __name__ == "__main__":
    sys.exit(main())
