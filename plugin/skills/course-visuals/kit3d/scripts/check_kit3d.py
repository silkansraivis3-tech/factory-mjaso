#!/usr/bin/env python3
"""check_kit3d.py - is a 3D-kit scene spec drawable, and is it a good one? (the 3D twin of check_kit.py)

  check_kit3d.py spec   <file.kit3d.json> ... [--parts <module>/assets/kit3d_parts.js] [--strict] [--json]
  check_kit3d.py module <module folder> [--figures <course>/working_claude/figures/M03] [--strict] [--json]

SPEC   valid JSON; a label; every part of a type the kit has (or the module's kit3d_parts.js adds); ids unique
       (parts and their sub-parts); every label, group, step and control names something that exists; every state
       named is one the part's type has; `when` well formed; view angles numbers.
MODULE every *.kit3d.json in the figures folder; and when the module's deck holds data-kit3d: assets/kit3d.js and
       assets/kit3d.css are there and equal the factory's byte for byte, and assets/vendor/three.min.js is there.
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
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = re.compile(r"/\*\s*@@CATALOG@@\s*\*/\s*(\{.*?\})\s*/\*\s*@@END@@\s*\*/", re.S)
DEFINE = re.compile(r"KIT3D\.define\(\s*['\"](\w+)['\"]")
# a label's "when": "pipe.cut > 0.5", "!tcs.open", "tcs.open"
WHEN = re.compile(r"^(!?)\s*([\w.]+)(?:\s*(?:>=|<=|==|>|<)\s*-?\d+(?:\.\d+)?)?$")
# these tank types draw their liquid (and so its sub-part) only when the part says how full it is
LIQUID_ONLY_WITH_FILL = ("tank_c", "tank_sphere", "tank_prism")
MAX_LABELS, MIN_LABELS = 9, 2


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
    """a module's kit3d_parts.js adds types; all we can know of them is the name (no states, no sub-parts)"""
    if parts_js and os.path.isfile(parts_js):
        return {n: {} for n in DEFINE.findall(read(parts_js))}
    return {}


def load_spec(path):
    try:
        spec = json.loads(read(path))
    except (OSError, ValueError) as e:
        return None, "%s: not JSON (%s)" % (os.path.basename(path), e)
    if not isinstance(spec, dict):
        return None, "%s: a scene is a JSON object, not a %s" % (os.path.basename(path), type(spec).__name__)
    return spec, None


# ------------------------------------------------------------------ the names a spec makes
def sub_ids(part, entry):
    """the ids of the sub-parts one part makes (SPEC.md: Parts)"""
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
        mine = ([pid] if isinstance(pid, str) else []) + sub_ids(p, entry)
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
            if set(sub_ids(p, types.get(p.get("type"), {}))) & label_parts:
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
    return P, N


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
    if not specs and not has_scene:
        print("nothing to check - no *.kit3d.json (give --figures) and no data-kit3d in the deck")
        return 2
    return report(found, notes, "%d spec(s)%s" % (len(specs), ", assets checked" if has_scene else ""), o.strict, o.json)


if __name__ == "__main__":
    sys.exit(main())
