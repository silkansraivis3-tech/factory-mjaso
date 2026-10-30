#!/usr/bin/env python3
"""test_meaning.py - 2.72.0: relations in the kit, and the checks of what a figure MEANS. Run: python test_meaning.py
(node runs the kit's own resolver - kit_relate.py; without node it SKIPs)

The IGF 2.71.0 unseeded build of M01-M03 (C:\\rvt\\s266) passed every check with figures a seafarer calls wrong (Aleksis,
2026-10-26: "bunkering station is nowhere to be seen; the vent mast ... is INSIDE of the ship, the gas is not being ejected
... its not properly connected"). The eight figures he showed are fixtures/igf265/; each must now FAIL for what is wrong
with it, and each of the kit's patterns must pass:

  * relations: "on" stands a part on the deck (a vent mast's outlet above it, clear of the accommodation), "in" on a
    hold's floor, "at" along a pipe, "from"/"to" route a pipe between two ports, "for" points a callout at its part,
    "around" centres a zone on a port, a cloud grows "from" a port; a spec with no relation is left byte for byte;
  * the meaning checks (kit_meaning.py) - NAMED, LOOSE END, INSIDE, NO GAS, AIM, LEADER, GRID, MODES, TRUTH - each on the
    2.71.0 figure that showed it, and on a small spec built to show it alone;
  * the patterns (ship_ga, bunkering_line, vent_system, fuel_supply, engine_modes, fuel_types, fuel_space_access) are clean;
  * the compiler starts a slide that names a pattern's figure from that pattern (compile_module.pattern_for).
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_kit as ck  # noqa: E402
import kit_meaning as km  # noqa: E402
import kit_relate as kr  # noqa: E402

KIT = os.path.dirname(HERE)
SKILLS = os.path.dirname(os.path.dirname(KIT))
FIX = os.path.join(HERE, "fixtures", "igf265")
FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def load(p):
    return json.load(io.open(p, encoding="utf-8"))


def kinds(probs):
    return {x.split(": ")[1].split(" ")[0] if ": " in x else x for x in probs}


def has(probs, kind, word=""):
    """a BLOCK line (": KIND ...") or a NOTE line (": note KIND ...") of that kind holding the word"""
    return any(((": %s" % kind) in x or (": note %s" % kind) in x) and word.lower() in x.lower() for x in probs)


def lines(spec):
    a = km.analyse(spec)
    return a["block"] + a["note"]


def blocks(spec):
    return km.analyse(spec)["block"]


SHIP = {"id": "G", "type": "ga", "x": 14, "y": 200, "w": 612, "h": 150, "house": {"x": 22, "w": 100, "h": 80}, "funnel": {"x": 52, "w": 28, "h": 34}}


def relations_part():
    print("\n-- relations: a part placed by what it stands on")
    spec = {"size": [640, 390], "label": "t", "parts": [
        dict(SHIP),
        {"id": "H", "type": "space", "x": 290, "y": 208, "w": 236, "h": 122},
        {"id": "T", "type": "tank", "in": "H", "at": 0.5, "w": 196, "h": 66},
        {"id": "V", "type": "vent", "on": "G.deck", "at": 0.74},
        {"id": "P", "type": "pipe", "from": "T.top", "to": "V.inlet"},
        {"id": "VL", "type": "valve", "at": "P@0.2"},
        {"id": "B", "type": "manifold", "on": "G.deck", "at": 0.9, "w": 40, "h": 12, "drop": 14, "hose": 16, "outlets": [{"label": ""}]},
        {"id": "N", "type": "text", "text": "bunkering station", "for": "B"},
        {"id": "Z", "type": "zone", "around": "V.outlet", "r": 30},
        {"id": "C", "type": "gas_cloud", "from": "V.outlet", "w": 80, "h": 50}],
        "steps": [{"title": "t", "play": [["V", 1, 300]]}]}
    got = kr.run([spec])[0]
    r, geo = got["spec"], {g["id"]: g for g in got["geometry"] if g and g.get("id")}
    P = {p["id"]: p for p in r["parts"]}
    deck = 200
    check("a vent \"on\" the deck: its mast's foot on the deck line", abs(geo["V"]["foot"][1] - deck) < 0.5, geo["V"]["foot"])
    check("... and its outlet above the deck AND above the accommodation (house 80 + funnel 34)",
          geo["V"]["ports"]["outlet"][1] < deck - 114, geo["V"]["ports"]["outlet"])
    check("a tank \"in\" its hold stands on the hold's floor", abs(geo["T"]["foot"][1] - (208 + 122 - 3)) < 0.5, geo["T"]["foot"])
    pts = kr.run([r])[0]["geometry"][[g["id"] if g else None for g in kr.run([r])[0]["geometry"]].index("P")]["pts"]
    check("a pipe \"from\" the tank's top \"to\" the vent's inlet starts and ends on those ports",
          pts[0] == [round(geo["T"]["ports"]["top"][0], 1), round(geo["T"]["ports"]["top"][1], 1)]
          and abs(pts[-1][0] - geo["V"]["ports"]["inlet"][0]) < 0.2 and abs(pts[-1][1] - deck) < 0.2, pts)
    check("... and is drawn in right angles", all(a[0] == b[0] or a[1] == b[1] for a, b in zip(pts, pts[1:])), pts)
    check("a valve \"at\" the pipe sits on it", km.poly_dist([P["VL"]["x"], P["VL"]["y"]], pts) < 0.2, (P["VL"]["x"], P["VL"]["y"]))
    check("a manifold \"on\" the deck: its lowest flange on the deck", abs(geo["B"]["foot"][1] - deck) < 0.5, geo["B"]["foot"])
    check("a text \"for\" a part is a callout whose leader ends on it", km.pt_box(P["N"]["to"], geo["B"]["box"]) == 0, P["N"].get("to"))
    o = geo["V"]["ports"]["outlet"]
    check("a zone \"around\" the outlet is centred on it (its x, y the top left of its box)",
          abs(P["Z"]["x"] + 30 - o[0]) < 0.2 and abs(P["Z"]["y"] + 30 - o[1]) < 0.2, (P["Z"]["x"], P["Z"]["y"], o))
    check("a cloud \"from\" the outlet grows from over the outlet", abs(P["C"]["from"][0] - o[0]) < 0.2 and P["C"]["from"][1] < o[1], P["C"]["from"])
    check("a resolved spec keeps its relations (a reader sees what was meant)", P["V"].get("on") == "G.deck" and P["P"].get("to") == "V.inlet")
    old = load(os.path.join(FIX, "M03_s16.kit.json"))
    check("a spec with no relation is left exactly as it was", kr.run([old])[0]["spec"] == old)
    bad = kr.run([{"size": [100, 100], "parts": [{"id": "V", "type": "vent", "on": "X.deck"}]}])[0]["spec"]
    check("a relation to a part that is not there is said, not guessed", any("X" in e for e in bad.get("_relate") or []), bad.get("_relate"))
    frozen = kr.freeze(spec)
    check("freeze() writes relations out as plain x / y / d (for figure_fit.py's moves) and keeps them as _on, _to ...",
          not kr.has_relations(frozen) and any(p.get("_on") for p in frozen["parts"]), [p.get("_on") for p in frozen["parts"]])


def small(parts, steps=None, size=(640, 390)):
    return {"size": list(size), "label": "t", "parts": parts, "steps": steps or [{"title": "t", "play": [[parts[0]["id"], 1, 300]]}]}


def rules_part():
    print("\n-- each meaning check on a spec made to show it alone")
    p = lines(small([dict(SHIP), {"id": "N", "type": "text", "x": 540, "y": 168, "text": "Bunkering station"}]))
    check("NAMED: \"Bunkering station\" with no manifold, coupling or hose fails", has(p, "NAMED", "bunkering station"), p)
    p = lines(small([dict(SHIP), {"id": "V", "type": "vent", "x": 347, "y": 230, "mast": 70}]))
    check("INSIDE: a vent mast whose outlet is under the deck line fails", has(p, "INSIDE", "vent"), p)
    p = lines(small([dict(SHIP), {"id": "V", "type": "vent", "on": "G.deck", "at": 0.6}]))
    check("... and the same vent placed \"on\": \"G.deck\" passes it", not has(p, "INSIDE"), p)
    p = lines(small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60},
                        {"id": "P", "type": "pipe", "d": "M200 230 H330"}]))
    check("LOOSE END: a pipe from the tank that ends in the air fails", has(p, "LOOSE END", "(330, 230)"), p)
    p = lines(small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60},
                        {"id": "P", "type": "pipe", "d": "M200 230 H330", "open": "end"}]))
    check("... and passes when it says it is open to the air", not has(p, "LOOSE END"), p)
    tank = {"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60}
    for lab, part in (("gas valve unit", "gvu"), ("6.6 kV switchboard", "switchboard"), ("propulsion motor", "motor"),
                      ("propeller", "propeller"), ("LNG truck", "lng_truck")):
        p = lines(small([dict(tank), {"id": "B", "type": "space", "style": "enclosure", "x": 300, "y": 200, "w": 100, "h": 50, "label": lab}]))
        check("BOX: a plain box labelled %r fails and names the part (IGF Advanced M03 s07)" % lab, has(p, "BOX B", "type " + part), p)
    p = lines(small([dict(tank), {"id": "B", "type": "space", "style": "enclosure", "x": 300, "y": 200, "w": 100, "h": 50, "label": "gas valve unit"},
                     {"id": "V", "type": "valve", "x": 350, "y": 225}]))
    check("... a gas valve unit enclosure with its valve drawn inside passes", not has(p, "BOX"), p)
    p = lines(small([dict(tank), {"id": "B", "type": "space", "style": "enclosure", "x": 300, "y": 200, "w": 160, "h": 50,
                                  "label": "IAPH check-lists: ship, shore, truck"}]))
    check("... a card of words that mentions a truck passes", not has(p, "BOX"), p)
    p = lines(small([dict(tank), {"id": "B", "type": "space", "x": 300, "y": 160, "w": 160, "h": 120, "label": "switchboard room"}]))
    check("... a room named for what is in it passes", not has(p, "BOX"), p)
    piped = [dict(tank), {"id": "B", "type": "space", "style": "enclosure", "x": 300, "y": 200, "w": 100, "h": 60, "label": "seawater scrubber"},
             {"id": "P", "type": "pipe", "from": "T.right", "to": "B.left"}]
    p = lines(small(piped))
    check("BOX: a solid box a pipe runs into fails whatever its name (IGF Advanced M04 s02 'seawater scrubber', no list held it)",
          has(p, "BOX B", "pipe runs into"), p)
    piped[1] = dict(piped[1], style="room", label="fuel preparation room")
    p = lines(small(piped))
    check("... a room a pipe runs into passes", not has(p, "BOX"), p)
    words = [{"id": "W%d" % i, "type": "text", "x": 200, "y": 40 + 40 * i, "text": "ME-G%d" % i, "reveal": True} for i in range(3)]
    gear = [{"id": "E", "type": "engine", "x": 40, "y": 200, "w": 120, "h": 60}, {"id": "G", "type": "gauge", "x": 330, "y": 230, "r": 25, "label": "pressure"}]
    reveal = [{"title": "Engine %d" % i, "play": [["W%d" % i, 1, 300]]} for i in range(3)]
    p = lines(small(words + gear, reveal))
    check("STILL: steps that only bring in words beside an engine and a gauge that never move fail (IGF Advanced M03 s08)",
          has(p, "STILL E") and has(p, "STILL G", "reads nothing"), p)
    p = lines(small(words, reveal))
    check("... and so does a figure that is only words", has(p, "STILL", "only words"), p)
    p = lines(small(words + gear, reveal[:2] + [{"title": "Gas in", "play": [["E", 1, 300], ["G", 6, 600]]}]))
    check("... and passes once a step runs the engine and moves the gauge", not has(p, "STILL"), p)
    vent = [{"id": "T", "type": "tank", "x": 40, "y": 250, "w": 160, "h": 60}, {"id": "V", "type": "vent", "x": 300, "y": 80, "mast": 160},
            {"id": "P", "type": "pipe", "from": "T.top", "to": "V.inlet"}]
    p = lines(small(vent, [{"title": "The relief valve lifts and the gas vents", "play": [["T", 1, 300]]}]))
    check("NO GAS: a step that says the gas vents with no vent playing fails", has(p, "NO GAS"), p)
    p = lines(small(vent, [{"title": "The relief valve lifts and the gas vents", "play": [["V", 1, 300]]}]))
    check("... and passes when the vent plays", not has(p, "NO GAS"), p)
    p = lines(small([{"id": "W", "type": "water_curtain", "x": 400, "y": 30, "w": 40, "h": 100},
                        {"id": "T", "type": "tank", "x": 40, "y": 250, "w": 160, "h": 60}]))
    check("AIM: a water curtain hanging from nothing fails", has(p, "AIM", "water curtain"), p)
    p = lines(small([{"id": "S", "type": "spray", "x": 100, "y": 300, "angle": 60, "reach": 100},
                        {"id": "T", "type": "tank", "x": 400, "y": 250, "w": 160, "h": 60}]))
    check("AIM: a spray reaching empty space fails", has(p, "AIM", "spray"), p)
    p = lines(small([{"id": "S", "type": "spray", "x": 100, "y": 300, "aim": "T"}, {"id": "T", "type": "tank", "x": 400, "y": 250, "w": 160, "h": 60}]))
    check("... and passes when it \"aim\"s at the tank", not has(p, "AIM"), p)
    p = lines(small([dict(SHIP), {"id": "V", "type": "vent", "on": "G.deck", "at": 0.6},
                        {"id": "Z", "type": "zone", "x": 0, "y": 0, "r": 40, "value": 0}]))
    check("AIM: a round zone centred on nothing fails (a zone's x, y is its box's top left)", has(p, "AIM", "zone"), p)
    p = lines(small([{"id": "T", "type": "tank", "x": 40, "y": 250, "w": 160, "h": 60},
                        {"id": "N", "type": "text", "x": 500, "y": 40, "text": "cold surfaces burn the skin"}]))
    check("LEADER: words far from anything drawn fail", has(p, "LEADER", "float"), p)
    p = lines(small([dict(SHIP, label="ship")]))
    check("LEADER: a ship labelled \"ship\" fails (it floats under the keel and says nothing)", has(p, "LEADER", "ship"), p)
    grid = [{"id": "F%d" % i, "type": "text", "x": 107 + 213 * (i % 3), "y": 60 + 150 * (i // 3), "text": t}
            for i, t in enumerate(["LNG", "CNG", "LPG", "Methanol", "Ammonia", "Hydrogen"])]
    p = lines(small(grid + [{"id": "T", "type": "tank", "x": 30, "y": 90, "w": 150, "h": 50}]))
    check("GRID: six fuel captions over one tank fails", has(p, "GRID"), p)
    modes = [{"id": "C", "type": "cylinder", "x": 40, "y": 80, "w": 120, "h": 200}, {"id": "E", "type": "engine", "x": 260, "y": 120, "w": 100, "h": 60},
             {"id": "V", "type": "valve", "x": 540, "y": 160}, {"id": "VL", "type": "pipe", "d": "M500 160 H580"},
             {"id": "A", "type": "text", "x": 100, "y": 40, "text": "Gas mode"}, {"id": "B", "type": "text", "x": 310, "y": 40, "text": "Fuel-oil mode"},
             {"id": "D", "type": "text", "x": 540, "y": 40, "text": "Changeover"}]
    p = lines(small(modes))
    check("TRUTH engine_modes: mode captions over different parts / a valve fail", has(p, "TRUTH engine_modes"), p)
    p = lines(small([{"id": "G", "type": "ga", "x": 14, "y": 120, "w": 612, "h": 200},
                        {"id": "H", "type": "space", "x": 56, "y": 190, "w": 224, "h": 84, "label": "Hold space"},
                        {"id": "T", "type": "tank", "x": 64, "y": 214, "w": 150, "h": 48},
                        {"id": "S", "type": "space", "x": 290, "y": 190, "w": 90, "h": 84, "label": "Tank connection space"},
                        {"id": "V", "type": "vent", "on": "G.deck", "at": 0.5, "label": "vent mast"},
                        {"id": "N", "type": "text", "text": "fuel tank", "for": "T"}],
                       [{"title": "The fuel tank and its tank connection space", "play": [["S", 1, 300]]}]))
    check("TRUTH ship_plan: a tank connection space beside the tank, not on it, fails", has(p, "TRUTH ship_plan", "tank connection"), p)


EXPECT = {   # the 2.71.0 figure -> what Aleksis (and the subagent that mapped his screenshots) found wrong in it: BLOCK (the
    # build fails), NOTE (the figure reviewer judges it)
    "M01_s03": [("INSIDE", "vent", "BLOCK"), ("NAMED", "bunkering station", "BLOCK"), ("LEADER", "ship", "NOTE")],   # 7.png
    "M01_s04": [("NAMED", "bunkering station", "BLOCK"), ("LEADER", "ship", "NOTE")],                               # 6.png
    "M01_s06": [("LOOSE END", "P6L", "BLOCK"), ("TRUTH engine_modes", "changeover", "BLOCK")],                      # 8.png
    "M02_s02": [("GRID", "", "BLOCK")],                                                                             # 9.png
    "M02_s05": [("LOOSE END", "L1", "NOTE")],                                         # 10.png: 15 units short - a near miss
    "M03_s10": [("AIM", "zone", "NOTE")],                                             # 11.png: the zone beside the mast
    "M03_s11": [("LOOSE END", "NP", "BLOCK")],                                        # 12.png: nitrogen to nothing
    "M03_s16": [("AIM", "water curtain", "BLOCK"), ("LOOSE END", "P1", "NOTE")],      # 13.png: curtain floating
}


def igf265_part():
    print("\n-- the eight 2.71.0 figures Aleksis showed: each is caught for what is wrong with it - a clear error BLOCKS")
    types = ck.kit_types()
    for name, want in sorted(EXPECT.items()):
        spec = load(os.path.join(FIX, name + ".kit.json"))
        probs = ck.check_spec(spec, types, name)
        a = km.analyse(spec, name)
        for kind, word, level in want:
            got = has(probs, kind, word) if level == "BLOCK" else has(a["note"], "note " + kind, word)
            check("%s: %s %s%s" % (name, level, kind, (" (" + word + ")") if word else ""), got, (probs, a["note"]))
        check("%s: check_spec without the meaning checks (2.71.0) found it clean" % name, not ck.check_spec(spec, types, name, meaning=False))


FIX266 = os.path.join(HERE, "fixtures", "igf266")
# 2.72.3 - the 2.66 audit's 11 BROKEN figures (Desktop\IGF_course_2.66_figures\REPORT.md "your list"): what STEP and LABEL
# catch in them. The other seven need what a spec does not hold - where kit.js prints a part's own label (M01 s02 / s03), an
# animation's timing (M03 s08), an engine left running after its supply stops (M02 s15), where a leak is drawn (M01 s05),
# methods that have no part (M01 s07), a valve drawn off its tank (M03 s07): the figure review judges those
EXPECT266 = {"M03_s14": [("STEP", "checklist", "NOTE")], "M03_s17": [("STEP", "takes things away", "NOTE")],
             "M02_s05": [("LABEL", "cofferdam", "BLOCK")], "M03_s12": [("LABEL", "crane", "NOTE")]}


def igf266_part():
    print("\n-- 2.72.3 the 2.66 audit's BROKEN figures: a step that does not show its title (STEP), a label on the wrong part "
          "or naming what is not drawn (LABEL)")
    for name, want in sorted(EXPECT266.items()):
        a = km.analyse(load(os.path.join(FIX266, name + ".kit.json")), name)
        for kind, word, level in want:
            got = has(a["block"], kind, word) if level == "BLOCK" else has(a["note"], "note " + kind, word)
            check("%s: %s %s (%s)" % (name, level, kind, word), got, a["block"] + a["note"])
    check("the 11 fixtures are all there", len(glob.glob(os.path.join(FIX266, "*.kit.json"))) == 11)
    track = {"id": "CL", "type": "step_track", "x": 40, "y": 60, "w": 200, "h": 200}
    mute = small([track, {"id": "TC", "type": "text", "x": 420, "y": 300, "text": "constant contact"}],
                 [{"title": "1 · They sign the safety checklist", "play": [["TC", 1, 300]]}])
    check("STEP: a title naming the checklist, a step that only shows words elsewhere - a NOTE", has(km.analyse(mute)["note"],
                                                                                                   "note STEP step1", "checklist"), km.analyse(mute))
    lit = small([track], [{"title": "1 · They sign the safety checklist", "play": [["CL", 3, 900]]}])
    check("... the step ticks the checklist: none", not has(lines(lit), "STEP"), lines(lit))
    where = small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60}, {"id": "L", "type": "lamp", "x": 400, "y": 60}],
                  [{"title": "1 · Fuel tank - in its hold", "play": [["L", 1, 300]]}])
    check("... a tank, a room or a pipe a title names is where the step is, not what it does: none", not has(lines(where), "STEP"),
          lines(where))
    away = small([{"id": "D", "type": "detector", "x": 300, "y": 80, "value": 30}, {"id": "L", "type": "lamp", "x": 400, "y": 60, "value": 1}],
                 [{"title": "1 · A dispersal study finds the best places", "play": [["D", 0, 300], ["L", 0, 300]]}])
    check("STEP: a step that only turns things off under a title saying something happens - a NOTE",
          has(km.analyse(away)["note"], "note STEP step1", "takes things away"), lines(away))
    stop = small(away["parts"], [{"title": "1 · The alarm stops", "play": [["D", 0, 300], ["L", 0, 300]]}])
    check("... 'stops', 'shut', 'lost' in the title say so on purpose: none", not has(lines(stop), "STEP"), lines(stop))
    room = {"id": "CD", "type": "space", "x": 20, "y": 20, "w": 200, "h": 140}
    tank = {"id": "T", "type": "tank", "x": 40, "y": 40, "w": 160, "h": 100}
    on_tank = small([room, tank, {"id": "N", "type": "text", "x": 120, "y": 200, "text": "cofferdam", "for": "CD"}])
    check("LABEL: 'cofferdam' leading to its space's middle, on the tank inside it - a BLOCK", has(blocks(on_tank), "LABEL N", "tank"),
          lines(on_tank))
    on_wall = small([room, tank, {"id": "N", "type": "text", "x": 120, "y": 200, "text": "cofferdam", "for": "CD.top@0.1"}])
    check("... leading to the space's own edge: none", not has(lines(on_wall), "LABEL"), lines(on_wall))
    if CALIB and os.path.isdir(CALIB):
        specs = sorted(glob.glob(os.path.join(CALIB, "*.kit.json")))
        found = [x for f in specs for x in lines(load(f)) if ": LABEL " in x or ": note LABEL " in x]
        check("calibration: no LABEL in the hand-fixed set (%d specs) - why the wrong-part leader may BLOCK" % len(specs), not found, found)


CALIB = os.environ.get("CF_MEANING_CALIBRATION")      # a folder of hand-fixed, instructor-reviewed specs (the IGF original's)
FIX2665 = os.path.join(HERE, "fixtures", "igf2665")
# 2.72.7 - the 2.72.5 timed run's figure review (NEXT_ROUND.md): the run's own specs with the fault its first review called
# BROKEN put back (the fixers had fixed them) - each now caught for that fault
EXPECT2665 = {"M03_s05_way": [("WAY step3", "says the valve closes, and the step opens it (B1, B2)", "BLOCK")],
              "M03_s05_alone": [("JOINS B1", "joins nothing", "BLOCK"), ("JOINS B2", "joins nothing", "BLOCK"),
                                ("JOINS T", "no pipe reaches it", "NOTE")],
              "M03_s07": [("READOUT P3", "reads 60 % while the tank T is drawn 20 % full", "BLOCK")],
              "M02_s14": [("READOUT P2", "at rest the level P2 reads 20 % while the tank P1 is drawn 90 % full", "BLOCK")]}


def igf2665_part():
    print("\n-- 2.72.7 the 2.72.5 run's BROKEN figures: a step that does the opposite of its title (WAY), a readout against its "
          "tank (READOUT), a part on no line (JOINS)")
    for name, want in sorted(EXPECT2665.items()):
        a = km.analyse(load(os.path.join(FIX2665, name + ".kit.json")), name)
        for kind, word, level in want:
            got = has(a["block"], kind, word) if level == "BLOCK" else has(a["note"], "note " + kind, word)
            check("%s: %s %s (%s)" % (name, level, kind, word), got, a["block"] + a["note"])
    valve = lambda title, play, rest=1: small(
        [{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60}, {"id": "P", "type": "pipe", "from": "T.right", "to": [600, 230]},
         {"id": "V", "type": "valve", "at": "P@0.5", "value": rest}, {"id": "BL", "type": "valve", "at": "P@0.8", "value": 0}],
        [{"title": title, "play": play}])
    check("WAY: 'the valve closes' and the step opens it - a BLOCK", has(blocks(valve("1 · The valve closes", [["V", 1, 300]], 0)),
                                                                      "WAY step1"), lines(valve("1 · The valve closes", [["V", 1, 300]], 0)))
    check("... it closes it: none", not has(lines(valve("1 · The valve closes", [["V", 0, 300]])), "WAY"))
    check("... a title saying both ways ('close ... opens') is not judged",
          not has(lines(valve("1 · The block valve closes and the bleed valve opens", [["V", 1, 300], ["BL", 1, 300]], 0)), "WAY"))
    check("... 'the open deck', 'close to' are places, not a valve opening or closing",
          not has(lines(valve("1 · The valve on the open deck, close to the mast", [["V", 0, 300]])), "WAY"))
    pump = lambda title, play, rest: small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60},
                                            {"id": "P", "type": "pipe", "from": "T.right", "to": [600, 230]},
                                            {"id": "PU", "type": "pump", "at": "P@0.5", "value": rest}], [{"title": title, "play": play}])
    check("WAY: 'the pump stops' and the step starts it - a BLOCK; it stops it - none",
          has(blocks(pump("1 · The fuel pump stops", [["PU", 1, 300]], 0)), "WAY step1")
          and not has(lines(pump("1 · The fuel pump stops", [["PU", 0, 300]], 1)), "WAY"))
    tank = {"id": "T", "type": "tank", "x": 40, "y": 100, "w": 200, "h": 150, "value": 0.2}
    lv = {"id": "L", "type": "level", "x": 300, "y": 60, "w": 50, "h": 200, "label": "tank level", "unit": "%", "value": 20}
    check("READOUT: the level rises to 90 % and the tank stays drawn at 20 % - a BLOCK; the tank rises with it - none",
          has(blocks(small([tank, lv], [{"title": "1 · Filling", "play": [["L", 90, 900]]}])), "READOUT L")
          and not has(lines(small([tank, lv], [{"title": "1 · Filling", "play": [["L", 90, 900], ["T", 0.9, 900]]}])), "READOUT"))
    lel = dict(lv, type="gauge", r=40, label="gas detector", unit="% LEL", max=100)
    check("... a % LEL reading is no tank level: none", not has(lines(small([tank, lel], [{"title": "1 · Gas", "play": [["L", 90, 900]]}])),
                                                               "READOUT"))
    rv = small([dict(tank, x=40, y=150), {"id": "RV", "type": "relief_valve", "x": 120, "y": 136},
                {"id": "P", "type": "pipe", "from": "T.right", "to": [600, 200]}])
    check("JOINS: a relief valve standing on its tank's top (no pipe end on it) is mounted: none (the hand-fixed IGF M03 s07)",
          not has(lines(rv), "JOINS"), lines(rv))
    alone = small([dict(tank, x=40, y=150), {"id": "P", "type": "pipe", "from": "T.right", "to": [600, 200]},
                   {"id": "V", "type": "valve", "x": 400, "y": 60}])
    check("JOINS: a valve away from every pipe in a figure with pipes - a BLOCK", has(blocks(alone), "JOINS V"), lines(alone))
    if CALIB and os.path.isdir(CALIB):
        specs = sorted(glob.glob(os.path.join(CALIB, "*.kit.json")))
        found = [x for f in specs for x in km.analyse(load(f), os.path.basename(f))["block"] if any(": %s" % k in x for k in ("WAY", "READOUT", "JOINS"))]
        check("calibration: no WAY / READOUT / JOINS BLOCK in the hand-fixed set (%d specs; 2.72.7: 0, two JOINS notes)" % len(specs),
              not found, found)


def levels_part():
    print("\n-- two levels, a waiver with a reason (2.72.0, Aleksis: 'no flexibility')")
    loose = small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60}, {"id": "P", "type": "pipe", "d": "M200 230 H330"}])
    check("a pipe end 130 units from anything BLOCKS", has(blocks(loose), "LOOSE END P"), blocks(loose))
    near = small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60}, {"id": "P", "type": "pipe", "d": "M220 230 H330"},
                  {"id": "U", "type": "tank", "x": 345, "y": 200, "w": 160, "h": 60}])
    a = km.analyse(near)
    check("a pipe end a few units short of a part is a NOTE, not a build FAIL", not a["block"] and has(a["note"], "note LOOSE END"), a)
    lab = small([{"id": "T", "type": "tank", "x": 40, "y": 200, "w": 160, "h": 60}, {"id": "P", "type": "pipe", "d": "M200 230 H330"},
                 {"id": "N", "type": "text", "x": 360, "y": 230, "text": "to the engine room"}])
    check("... and so is one whose end carries words saying where it goes", not blocks(lab), blocks(lab))
    far = small([{"id": "T", "type": "tank", "x": 40, "y": 250, "w": 160, "h": 60},
                 {"id": "N", "type": "text", "x": 500, "y": 40, "text": "cold surfaces burn the skin"}])
    check("words floating far from the drawing are a NOTE (the reviewer judges them)", not blocks(far) and has(lines(far), "note LEADER"))
    ok = dict(loose, meaning_ok={"LOOSE END P": "the line runs on to the bunker vessel, off the picture"})
    a = km.analyse(ok, "w")
    check("\"meaning_ok\": {\"LOOSE END P\": reason} accepts it: no block, the reason kept for the reviewer",
          not a["block"] and a["waived"] and "bunker vessel" in a["waived"][0], a)
    no_reason = dict(loose, meaning_ok={"LOOSE END P": ""})
    check("a waiver with no reason is itself a BLOCK", has(km.analyse(no_reason)["block"], "WAIVER"), km.analyse(no_reason))
    stale = dict(loose, meaning_ok={"LOOSE END P": "runs on", "INSIDE Q": "left over"})
    check("a waiver for a finding the figure does not have is a NOTE", has(km.analyse(stale)["note"], "note WAIVER"))
    types = ck.kit_types()
    check("check_spec (the build) fails on BLOCKs only", ck.check_spec(near, types, "n") == [] and ck.check_spec(loose, types, "l"))
    vent_marks = {"size": [640, 390], "label": "t", "parts": [
        {"id": "T", "type": "tank", "x": 40, "y": 250, "w": 160, "h": 60}, {"id": "V", "type": "vent", "x": 300, "y": 80, "mast": 160},
        {"id": "P", "type": "pipe", "from": "T.top", "to": "V.inlet"},
        {"id": "G", "type": "gauge", "x": 500, "y": 100, "marks": [{"at": 7, "kind": "trip", "then": [["V", 1, 300]]}]}],
        "steps": [{"title": "The pressure rises - the relief valve lifts and the gas vents", "play": [["G", 8, 900]]}]}
    check("NO GAS: gas let out by a mark's \"then\" (the pressure mark lifts the vent) counts", not has(lines(vent_marks), "NO GAS"),
          lines(vent_marks))
    named = small([{"id": "T", "type": "tank", "x": 40, "y": 250, "w": 160, "h": 60},
                   {"id": "N", "type": "text", "x": 120, "y": 230, "text": "the vent mast stays shut"}],
                  [{"title": "Nitrogen into the vent mast - the flame goes out", "play": [["T", 1, 300]]}])
    check("\"the vent mast\" in a step's words is a name, not \"the gas vents\"", not has(lines(named), "NO GAS"), lines(named))
    if CALIB and os.path.isdir(CALIB):
        specs = sorted(glob.glob(os.path.join(CALIB, "*.kit.json")))
        nb = sum(len(km.analyse(load(f), os.path.basename(f))["block"]) for f in specs)
        check("calibration: the hand-fixed set (%d specs) raises at most 6 BLOCKs (2.72.0: 5)" % len(specs), nb <= 6, nb)


def patterns_part():
    print("\n-- the figure library: every pattern is clean, meaning included")
    types = ck.kit_types()
    pats = sorted(glob.glob(os.path.join(KIT, "patterns", "*.kit.json")))
    names = {os.path.basename(p).replace(".kit.json", "") for p in pats}
    want = {"ship_ga", "bunkering_line", "vent_system", "fuel_supply", "engine_modes", "fuel_types", "fuel_space_access"}
    check("the patterns are all there", want <= names, sorted(names))
    for p in pats:
        probs = ck.check_spec(load(p), types, os.path.basename(p))
        check("pattern %s passes check_kit (meaning too)" % os.path.basename(p), not probs, probs)
    T = km.truths()
    check("figure-truths.json lists a must-be-true list for each common IGF figure",
          {"ship_plan", "bunkering_line", "vent_system", "fuel_supply", "engine_modes", "fuel_types"} <= set(T["figures"]))
    k = km.figure_kinds(load(os.path.join(KIT, "patterns", "vent_system.kit.json")))
    check("figure_kinds() names a figure's kind and its truths (the FIGURE review reads them)",
          any(x["kind"] == "vent_system" and x["truths"] for x in k), k)


def starter_part():
    print("\n-- the compiler starts a slide that names a pattern's figure from that pattern")
    sys.path.insert(0, os.path.join(SKILLS, "course-factory", "compile", "scripts"))
    sys.path.insert(0, os.path.join(SKILLS, "course-factory", "scripts"))
    import compile_module as cm
    s03 = {"kind": "slide", "id": "s03", "title": "What is new on an IGF ship", "visual_kind": "comparison",
           "text": "An IGF ship has new parts.\nFuel tank - low-flashpoint fuel.\nTank connection space - round the tank valves.\n"
                   "Fuel preparation room - pumps and vaporizers.\nBunkering station and vent mast.\nProtected engine room."}
    got = cm.pattern_for(s03)
    check("M01 s03 (fuel tank, TCS, FPR, bunkering station, vent mast) -> ship_ga", got and got[0] == "ship_ga", got and got[0])
    spec = cm.pattern_starter(s03)
    check("... its starter is the pattern, marked \"_pattern\", its steps lighting the slide's lines",
          spec and spec.get("_pattern") and all(1 <= st.get("line", 1) <= 6 for st in spec["steps"]), spec and spec.get("_pattern"))
    fuels = {"kind": "slide", "id": "s02", "title": "Low-flashpoint fuels", "visual_kind": "comparison",
             "text": "LNG - cold.\nCNG - compressed.\nLPG - under pressure.\nMethanol - liquid.\nAmmonia - toxic.\nHydrogen - very cold."}
    check("M02 s02 (six fuels) -> fuel_types", (cm.pattern_for(fuels) or [None])[0] == "fuel_types", cm.pattern_for(fuels))
    supply = {"kind": "slide", "id": "s03", "title": "The LNG fuel system - tank to engine", "visual_kind": "flow_animation",
              "text": "Fuel tank.\nTank connection space - tank valves.\nVaporizer and heater in the fuel preparation room.\nGas valve unit.\nDouble-walled pipe."}
    check("M02 s03 (tank to engine) -> fuel_supply, not the ship plan", (cm.pattern_for(supply) or [None])[0] == "fuel_supply", cm.pattern_for(supply))
    other = {"kind": "slide", "id": "s07", "title": "Toxicity of ammonia", "text": "Ammonia is toxic.\nWear a respirator."}
    check("a slide no pattern fits gets none (the grid starter)", cm.pattern_for(other) is None)


def main():
    if not kr.available():
        print("SKIP - node is not installed: the kit's resolver cannot run")
        return 0
    relations_part()
    rules_part()
    igf265_part()
    igf266_part()
    igf2665_part()
    levels_part()
    patterns_part()
    starter_part()
    print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
