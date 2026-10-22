#!/usr/bin/env python3
"""test_airlock.py - 2.63.2 (item 12), IGF M02 s10 "Getting into the fuel spaces" ("a bad quality diagram: pastel boxes,
a bunkering station drawn as a cart, pale tiny labels, everything greyed out on the last step").
Run: python test_airlock.py   (the browser checks SKIP without Chrome/Edge)

Pinned:
  * the kit has an `airlock` (two doors with the space between, the safe side and the hazardous side named, "two doors
    never open at once") and a `hatch` (the bolted hatch over a tank connection space), both built to the part contract
    (look: equipment, drawn in a material) and each with its gallery card;
  * the airlock's two doors are never open together, at any value of its state, and its words say how many are open;
  * the spec pattern patterns/fuel_space_access.kit.json (ship section, type C tank in its hold with the tank
    connection space on top and its bolted hatch, the fuel preparation room with its own access or the airlock, the
    bunkering station as a manifold with its drip tray, one colour for every hazardous space) passes check_kit and is
    drawn clean by the studio at 1280 x 800 and 1024 x 768 - on the dark panel and on the task page's;
  * a figure's LAST step may not leave every part dimmed (check_kit): the old pattern fails, the new one ends with every
    hazardous space at full strength.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_kit as ck  # noqa: E402
import studio  # noqa: E402
import test_studio as ts  # noqa: E402  - kit_eval: a spec drawn by the factory's kit.js, and what a script finds in it

FAILS = []
KIT = os.path.dirname(HERE)
PATTERN = os.path.join(KIT, "patterns", "fuel_space_access.kit.json")


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def parts_part():
    print("\n-- the airlock and the hatch are kit parts")
    merged = dict(ck.blocks(ck.read(ck.KIT_JS)))
    for name in ("airlock", "hatch"):
        block = merged.get(name)
        check("%s is merged into kit.js between its markers" % name, block is not None)
        if block is None:
            continue
        probs = ck.check_part(name, block)
        check("check_kit accepts %s (contract, look, material, example)" % name, not probs, probs)
        check("%s is drawn as equipment in its materials (L63)" % name,
              ck.meta_field(block, "look") == "equipment" and "h.body(" in block and "h.equip(" in block)
    types = ck.kit_types()
    check("a spec may name an airlock and a hatch", {"airlock", "hatch"} <= types, types)
    spec = json.load(io.open(PATTERN, encoding="utf-8"))
    probs = ck.check_spec(spec, types, "fuel_space_access")
    check("the pattern spec is a good spec (types, ids, steps, moves)", not probs, probs)
    check("the pattern uses the airlock, the hatch, a manifold with its drip tray, a type C tank and one hazard colour (zone)",
          {"airlock", "hatch", "manifold", "drip_tray", "tank", "zone", "ga"} <= {p["type"] for p in spec["parts"]},
          sorted({p["type"] for p in spec["parts"]}))
    check("every figure of the kit docs names the airlock", all(
        "airlock" in ck.read(os.path.join(KIT, f)) for f in ("SPEC.md", "CATALOGUE.md", "PARTS.md")), "")


def last_step_part():
    print("\n-- a figure's last step may not leave every part dimmed")
    types = ck.kit_types()
    spec = json.load(io.open(PATTERN, encoding="utf-8"))
    ids = [p["id"] for p in spec["parts"] if p["type"] in ck.PICKED]
    new = ck.check_spec(spec, types, "pattern")
    check("the pattern's last step shows every hazardous space at full strength - accepted", not new, new)
    last = spec["steps"][-1]["play"]
    check("... its last step lifts every one it dimmed before (Zf, Zh, T, X)", {a[0] for a in last} == {"Zf", "Zh", "T", "X"}, last)
    # the old slide: each step picks one thing out and the last one puts them all back to quiet
    old = json.loads(json.dumps(spec))
    old["steps"][-1] = {"title": "Every space again", "play": [[i, 0, 600] for i in ids]}
    probs = ck.check_spec(old, types, "old")
    check("the old pattern - the last step greys every space out - is refused, with the step and the way out",
          len(probs) == 1 and "last step (5)" in probs[0] and "dimmed" in probs[0] and "full strength" in probs[0], probs)
    # one step in a longer figure that ends dimmed through a reset
    reset = json.loads(json.dumps(spec))
    reset["steps"][-1] = {"title": "Start again", "reset": True, "play": [["A", 0, 300]]}
    check("a last step that resets everything to quiet is refused too", len(ck.check_spec(reset, types, "r")) == 1, ck.check_spec(reset, types, "r"))
    one = json.loads(json.dumps(spec))
    one["steps"][-1] = {"title": "Only the bunkering station", "play": [["Zf", 0, 300], ["Zh", 0, 300], ["T", 0, 300], ["X", 0, 300], ["Zb", 1, 300]]}
    check("a last step that leaves one thing picked out is not 'every part dimmed' - accepted", not ck.check_spec(one, types, "o"), ck.check_spec(one, types, "o"))
    # figures that never pick parts out one at a time are not judged: a valve closing, one room lit and left lit
    quiet = {"size": [300, 200], "label": "x", "parts": [{"id": "V", "type": "valve"}, {"id": "R", "type": "space", "w": 100, "h": 80},
                                                         {"id": "S", "type": "space", "x": 120, "w": 100, "h": 80}],
             "steps": [{"title": "close", "play": [["V", 0, 300]]}, {"title": "again", "play": [["V", 1, 300]]}]}
    check("a figure whose steps pick nothing out is not judged", not ck.check_spec(quiet, types, "q"), ck.check_spec(quiet, types, "q"))
    lit_then_off = json.loads(json.dumps(quiet))
    lit_then_off["parts"][1]["value"] = 1
    lit_then_off["steps"] = [{"title": "one", "play": [["R", 0, 300], ["S", 1, 300]]}, {"title": "all off", "play": [["S", 0, 300]]}]
    check("rooms picked out one at a time, the last step puts the last one out: refused",
          len(ck.check_spec(lit_then_off, types, "l")) == 1, ck.check_spec(lit_then_off, types, "l"))


DOORS_JS = (
    "var A=svg.querySelector('[data-kit-id=\"A\"]'),h=function(){return [].map.call(A.querySelectorAll('.kit-airlock-hole'),"
    "function(x){return +x.style.opacity;});},out=[];f.layout(true);"
    "[0,0.5,1,1.25,1.5,1.75,2,1.5,0].forEach(function(v){f.parts.A.render(v);"
    "out.push({v:v,h:h(),st:A.querySelector('.kit-state').textContent});});return out;")


def doors_part():
    print("\n-- the airlock's two doors are never open together")
    spec = {"size": [340, 186], "label": "airlock", "parts": [{"id": "A", "type": "airlock", "x": 13, "y": 20}],
            "steps": [{"title": "in", "play": [["A", 1, 400]]}]}
    rows = ts.kit_eval(spec, DOORS_JS, 640)
    if not rows or isinstance(rows, dict):
        check("the airlock is drawn and driven", False, rows)
        return
    both = [r for r in rows if r["h"][0] > 0.01 and r["h"][1] > 0.01]
    check("at no value of its state are both doors open (the one that is open shuts first)", not both, both)
    by = {r["v"]: r for r in rows}
    check("0: both doors shut, the words say so", by[0]["h"] == [0, 0] and by[0]["st"] == "BOTH DOORS SHUT", by[0])
    check("1: the safe-side door is open, the other shut: ONE DOOR OPEN", by[1]["h"][0] == 1 and by[1]["h"][1] == 0 and by[1]["st"] == "ONE DOOR OPEN", by[1])
    check("2: the hazardous-side door is open, the other shut: ONE DOOR OPEN", by[2]["h"][1] == 1 and by[2]["h"][0] == 0 and by[2]["st"] == "ONE DOOR OPEN", by[2])
    check("between the two, at 1.5, both doors are shut for a moment", by[1.5]["h"] == [0, 0], by[1.5])


def studio_part(tmp):
    print("\n-- the studio draws the pattern, the airlock and the hatch clean")
    for panel in ("two-col", "task"):
        r = studio.run(PATTERN, panel=panel, out=os.path.join(tmp, "pat_" + panel), quiet=True)[0]
        check("the pattern: the studio runs on the %s panel" % panel, r is not None)
        if not r:
            continue
        found = [p for p in studio.problems(r) if p[2] != "empty"]
        check("the pattern on the %s panel: clean at 1280 x 800 and at 1024 x 768, every step (%d findings)" % (panel, len(found)),
              not found, found[:8])
        sizes = r["sizes"]
        check("... the words are the 12.5 px floor or more at both sizes",
              all((sizes[s].get("report") or {}).get("minTextPx", 0) >= 12.49 for s in sizes),
              [(s, (sizes[s].get("report") or {}).get("minTextPx")) for s in sizes])
        check("... and every label found a clear place",
              all(not ((sizes[s].get("report") or {}).get("unplaced")) for s in sizes), [(s, (sizes[s].get("report") or {}).get("unplaced")) for s in sizes])


def main():
    parts_part()
    last_step_part()
    if not studio.find_browser():
        print("\nSKIP - no Chrome or Edge (set CF_BROWSER): the doors and the studio were not driven")
    else:
        doors_part()
        tmp = tempfile.mkdtemp(prefix="airlock_")
        try:
            studio_part(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
