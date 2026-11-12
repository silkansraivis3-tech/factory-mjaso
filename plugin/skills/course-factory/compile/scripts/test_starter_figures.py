#!/usr/bin/env python3
"""test_starter_figures.py - --init-build's starter figure-kit specs are drawn to the shape of the column the deck shows
them in, and spread over all of it (2.52.0). M01 workflow benchmark, 2026-10-20: the starters' parts kept their small
default sizes on a 640 x 390 grid, so the drawing check's EMPTY (a figure over half blank) failed ~20 of 25 failing M01
builds - every starter s02-s07 was EMPTY as written, and s04, with an L57 photo row under it, was drawn in a 682 x 292 px
panel at 0.75. Here: the canvas (no browser), then three of M01's real slides drawn by the figure studio at both sizes -
none EMPTY (each was before). Run: python test_starter_figures.py  (the studio part SKIPs without Chrome/Edge)"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILLS, "course-visuals", "kit", "scripts"))
import compile_module as cm  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


# IGF Basic M01, as approved (working_claude\script\M01.json)
B = "• "
SLIDES = {
    "s03": {"id": "s03", "kind": "slide", "title": "What is new on an IGF ship", "visual_kind": "comparison", "layout": "split",
            "text": "Compared with an oil-fuelled ship, an IGF ship has:\n" + B + "fuel with a low flashpoint, often cryogenic\n" + B
                    + "a fuel tank with a tank connection space\n" + B + "a fuel preparation room\n" + B
                    + "a bunkering station and a vent mast\n" + B + "a protected engine room - gas safe or ESD-protected\n" + B
                    + "engines that run on gas, oil or both",
            "visual": "Two ship silhouettes side by side; the IGF ship's new parts light up one by one. Authored by the factory."},
    "s04": {"id": "s04", "kind": "slide", "title": "Five new parts on board", "visual_kind": "interactive_diagram", "layout": "visual_wide",
            "text": "Fuel tank - in a fuel storage hold space or on open deck.\nTank connection space - surrounds all tank connections "
                    "and tank valves.\nFuel preparation room - pumps, compressors and vaporizers.\nBunkering station - on open deck, "
                    "where fuel is received.\nVent mast - releases fuel vapour from the relief valves, high above the weather deck.",
            "visual": "General arrangement of a typical LNG-fuelled ship; the instructor taps each of the five spaces and it lights "
                      "up with its name. Authored from the IGF Code definitions."},
    "s06": {"id": "s06", "kind": "slide", "title": "Running on gas - the dual-fuel engine", "visual_kind": "step_animation", "layout": "split",
            "text": "Many IGF ships have dual-fuel engines.\nGas mode: gas burns, lit by a small injection of pilot fuel oil.\n"
                    "Fuel-oil mode: the engine runs on oil fuel only.\nChangeover: the engine switches between modes - planned, or "
                    "automatically when the gas supply trips.\nGas-only engines exist too - they cannot switch to oil.",
            "visual": "Engine cylinder in three steps: gas mode with pilot spray igniting gas, gas valves closing on a trip, fuel-oil "
                      "mode. From the MAN ME-GI fuel gas supply manual drawings, redrawn by the factory."}}
SCRIPT = {"module": 1, "title": "IGF ship design", "screens": list(SLIDES.values())}


def boxes(spec):
    """each drawn part's box (x0, y0, x1, y1) in the spec's units, from its own size options"""
    out = []
    for p in spec["parts"]:
        t, x, y = p.get("type"), p.get("x", 0), p.get("y", 0)
        if t == "text" or t == "pipe":
            continue
        if "w" in p and "h" in p:
            out.append((x, y, x + p["w"], y + p["h"]))
        elif "r" in p:
            out.append((x - p["r"], y - p["r"], x + p["r"], y + p["r"]))
    return out


# 2.72.0 - s03, s04 and s06 name a figure of the kit's library (ship plan, engine modes): their starter IS the pattern, and
# the placeholder grid below is judged on a slide no pattern fits (s04 with its last three lines, and a line naming the ship:
# the starter no longer draws one from the visual's words)
GRID_S04 = dict(SLIDES["s04"], id="s04g", text="\n".join(SLIDES["s04"]["text"].split("\n")[2:5] + ["Ship - the hull that holds them all."]))


def canvas():
    for sid, want in (("s03", "ship_ga"), ("s04", "ship_ga"), ("s06", "engine_modes")):
        spec = cm.starter_figure(SCRIPT, SLIDES[sid])
        check("2.72.0 %s names a library figure: its starter is the %s pattern" % (sid, want),
              spec and want in (spec.get("_pattern") or ""), spec and spec.get("_pattern"))
    # 2.72.0 - the first proof run: builders redrew every starter by hand before building. A starter is built AS IT IS, so it
    # must pass the meaning checks' BLOCKs itself, and its build-sheet note must say "build it", not "replace the parts"
    sys.path.insert(0, os.path.join(cm.SKILLS, "course-visuals", "kit", "scripts"))
    import kit_meaning as km
    vent = {"id": "sv", "kind": "slide", "title": "Vent mast", "visual_kind": "schematic",
            "text": "The relief valve lifts.\nVent mast - the gas vents high above the deck.\nValve - the master valve closes."}
    for sid, sl in list(SLIDES.items()) + [("s04g", GRID_S04), ("sv", vent)]:
        spec = cm.starter_figure(SCRIPT, sl)
        check("2.72.0 %s: its starter has no BLOCK of the meaning checks (it is built as it is)" % sid,
              spec and not km.analyse(spec, sid)["block"], spec and km.analyse(spec, sid)["block"])
    sv = cm.starter_figure(SCRIPT, vent)
    valve = next((p for p in sv["parts"] if p.get("type") == "valve"), {})
    check("2.72.7 a starter's valve on a line saying it closes starts open and its step closes it (lit to 1 it opened - WAY)",
          valve.get("value") == 1 and [valve.get("id"), 0, 600] in [x for st in sv["steps"] for x in st["play"]], sv)
    screens = {s["id"]: {} for s in SCRIPT["screens"]}
    cm.starter_figures(SCRIPT, screens, tempfile.mkdtemp(prefix="sf_"), out={})
    notes = [e.get("_figure", "") for e in screens.values() if e.get("_figure")]
    check("2.72.0 the build sheet's note on a starter says BUILD it as it is (it said: replace the placeholder parts)",
          notes and all("BUILD it as it is" in n and "replace the placeholder" not in n for n in notes), notes)
    s4 = GRID_S04
    plain = cm.starter_figure(SCRIPT, s4)
    check("no photograph to show: the canvas is the figure column's shape at the width it shows at, 416 x 254 (2.66.0)", plain["size"] == [416, 254], plain["size"])
    pool = [("vm.jpg", {"shows": ["vent mast"]}, "m", "u:vm")]
    strip = cm.starter_figure(SCRIPT, s4, pool)
    check("a cleared photograph shows a thing the starter draws (the L57 row goes under it): the canvas is the column less "
          "the row, 416 x 178 (M01 s04: a 682 x 292 px panel)", strip["size"] == [416, 178], strip["size"])
    taken = cm.starter_figure(SCRIPT, s4, pool, {"u:vm": "M02 s03"})
    check("... not when the course already shows that photograph (L58: the row leaves it out)", taken["size"] == [416, 254], taken["size"])
    # (merge) s03 / s04 start from a pattern since 2.72.0: the grid's own layout is judged on a slide no pattern fits
    for sid, sl in (("s04g", GRID_S04),):              # drawn parts only (s06 is mostly text callouts: the studio judges it)
        spec = cm.starter_figure(SCRIPT, sl)
        W, H = spec["size"]
        bx = boxes(spec)
        area = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in bx)
        span = (min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx)) if bx else (0, 0, 0, 0)
        # 2.66.0: 25 %, not 30 - on the 416-wide canvas the words' fixed room beside each part is a larger share; the
        # studio's EMPTY check below (the drawing check itself, at 1280 x 800 and 1024 x 768) is the judge
        check("%s: the drawn parts are spread over the canvas (their boxes reach within 15 %% of each edge) and grown to their "
              "cells (at least 25 %% of it)" % sid,
              bx and span[0] <= 0.15 * W and span[1] <= 0.15 * H and span[2] >= 0.85 * W and span[3] >= 0.8 * H and area >= 0.25 * W * H,
              {"span": span, "share": round(area / float(W * H), 2)})
        inside = all(0 <= x0 and 0 <= y0 and x1 <= W and y1 <= H for x0, y0, x1, y1 in bx)
        overlap = any(not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]) for i, a in enumerate(bx) for b in bx[i + 1:])
        check("%s: ... every part inside the canvas, none overlapping another" % sid, inside and not overlap, bx)


def studio_part():
    import studio
    if not studio.find_browser():
        print("SKIP  the studio part - no Chrome or Edge (set CF_BROWSER)")
        return
    tmp = tempfile.mkdtemp(prefix="starter_test_")
    try:
        for sid in SLIDES:
            p = os.path.join(tmp, sid + ".kit.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(cm.starter_figure(SCRIPT, SLIDES[sid]), fh)
            r, why = studio.run(p, panel="two-col", sizes=((1280, 800), (1024, 768)), shots=False, quiet=True)
            probs = studio.problems(r) if r else [("", "", "not run", why, "")]
            empty = [x for x in probs if x[2] in ("empty", "not run")]
            check("M01 %s: its starter, as written, is not EMPTY at 1280 x 800 or 1024 x 768 (the drawing check's 50 %% blank)" % sid,
                  not empty, empty[:2])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def by_words():
    """2.67.0 - the starter picks the part the slide's own words ask for (the timed gas M02 build: 90 % of the builder's
    time went on redrawing grid placeholders - a vapour-pressure slide had got a scale, a formula slide text callouts)"""
    sc = {"module": 2, "screens": []}
    mol = cm.starter_figure(sc, {"id": "s21", "kind": "slide", "title": "Paraffins", "visual_kind": "schematic",
                                 "visual": "Structural formulas.", "text": "Methane - one carbon atom, four hydrogen atoms.\n"
                                 "Propane - three carbon atoms in a chain.\nButane - four carbon atoms."})
    check("a slide about formulas and atoms that names cargoes: one molecule each, by name, in the order the lines name them, "
          "each brought in on its own line", [p.get("type") for p in mol["parts"]] == ["molecule"] * 3
          and [p["formula"] for p in mol["parts"]] == ["methane", "propane", "butane"]
          and [st.get("line") for st in mol["steps"]] == [1, 2, 3] and "molecule" in mol.get("_note", ""), mol)
    vp = cm.starter_figure(sc, {"id": "s14", "kind": "slide", "title": "Vapour pressure", "visual_kind": "chart",
                                "visual": "Vapour pressure curves.", "notes": "Trainees drag to 45 °C and read it.",
                                "text": "Propane: 0 °C - 4.7 bar, 20 °C - 8.4 bar, 45 °C - 15.3 bar.\n"
                                        "n-Butane: 20 °C - 2.1 bar, 45 °C - 4.3 bar."})
    ch = vp["parts"][0]
    check("a vapour-pressure slide: a curve chart of its cargoes, labelled in the script's words, the points ONLY the numbers "
          "the slide states", ch["type"] == "curve_chart" and [c["label"] for c in ch["curves"]] == ["Propane", "n-Butane"]
          and ch["curves"][0]["pts"] == [[0.0, 4.7], [20.0, 8.4], [45.0, 15.3]] and ch["curves"][1]["pts"] == [[20.0, 2.1], [45.0, 4.3]], ch)
    check("... the cue says drag: the trainee drags a line that reads every curve, from the temperature the cue names",
          ch["point"] == {"curve": "all", "from": 45.0, "drag": True}, ch["point"])
    none = cm.starter_figure(sc, {"id": "s13", "kind": "slide", "title": "Boiling point", "visual_kind": "chart",
                                  "visual": "A curve.", "text": "Ammonia boils at minus 33 °C.\nIt is stored refrigerated."})
    check("... a slide that states no points gets no chart at all - never a curve made up from placeholders (gas M07 s07: a "
          "ppm slide got two)", not any(p.get("type") == "curve_chart" for p in (none or {}).get("parts") or []), none)
    plain = cm.starter_figure(sc, {"id": "s05", "kind": "slide", "title": "Tank and pump", "visual_kind": "schematic",
                                   "visual": "A tank with its pump.", "text": "Tank - holds the cargo.\nPump - moves it."})
    check("... a slide whose words name no cargo keeps the grid starter (a tank, a pump)",
          [p["type"] for p in plain["parts"]] == ["tank", "pump"] and "_note" not in plain, plain)
    sc_ = cm.starter_figure(sc, {"id": "s11", "kind": "slide", "title": "Tank temperature", "visual_kind": "schematic",
                                 "visual": "A temperature scale.", "notes": "Two trainees drag the tank marker.",
                                 "text": "Temperature - the tank at 20 degrees.\nLimit - the design limit."})
    scales = [p for p in sc_["parts"] if p.get("type") == "scale"]
    check("... a scale on a slide whose cue says drag: its marker is the trainee's to drag",
          scales and all(m.get("drag") for p in scales for m in p.get("markers") or []), sc_["parts"])


def track_part():
    """2.73.0 - a slide whose lines name no thing the kit draws gets its lines as a step track, not words floating on an empty
    panel (chem M11 on 2.70: four of five such starters failed "empty", 55-85 % blank; a tank on an hours-of-rest slide)"""
    sc = {"module": 11, "screens": []}
    rest = cm.starter_figure(sc, {"id": "s04", "kind": "slide", "title": "Hours of rest", "visual_kind": "chart",
                                  "visual": "The rules, one by one.", "text":
                                  "Chemical tanker port calls are round-the-clock: loading, discharging, tank preparation.\n"
                                  "STCW applies to watchkeepers and everyone with safety duties.\n"
                                  "at least 10 hours of rest in any 24 hours and 77 hours in any 7 days.\n"
                                  "Individual records are mandatory - Port State Control checks them."})
    tr = (rest or {}).get("parts") or [{}]
    check("a rules slide (a kit word only inside a sentence - 'tank preparation') is a step track of its lines, one step lighting "
          "each, its words never ending on a small word", len(tr) == 1 and tr[0].get("type") == "step_track"
          and tr[0]["steps"][2] == "at least 10 hours of rest in any 24 hours" and len(rest["steps"]) == 4
          and [st["play"][0][1] for st in rest["steps"]] == [1, 2, 3, 4] and all(len(x) <= cm.TRACK_CHARS for x in tr[0]["steps"]), rest)
    case = cm.starter_figure(sc, {"id": "s07", "kind": "slide", "title": "A handover", "visual_kind": "step_animation",
                                  "visual": "The case.", "text": "Case: 0400, our tanker loads three grades through three manifolds.\n"
                                  "Handover: the Second Officer hands over to the Third Officer.\nReveal: what was missing."})
    check("... a one-word term keeps the start of what its line says ('Case: 0400, our tanker loads three grades')",
          case["parts"][0]["type"] == "step_track" and case["parts"][0]["steps"][0].startswith("Case: 0400, our tanker"), case["parts"])
    pump = cm.starter_figure(sc, {"id": "s09", "kind": "slide", "title": "Deepwell pump", "visual_kind": "schematic",
                                  "visual": "The pump in its tank.", "text": "Deepwell pump: one in each cargo tank.\n"
                                  "Discharge line: from the pump to the manifold.\nStripping: the last cargo out."})
    check("... a slide that NAMES a thing the kit draws keeps it (the deepwell pump stays a pump)",
          any(p.get("type") == "pump" for p in pump["parts"]) and not any(p.get("type") == "step_track" for p in pump["parts"]), pump["parts"])
    eng = cm.starter_figure(sc, {"id": "s08", "kind": "slide", "title": "Two-stroke and four-stroke DF engines",
                                 "visual_kind": "comparison", "visual": "Comparison: one row per engine, the gas pressure on a scale.",
                                 "text": "ME-GI - Diesel cycle - gas about 300 bar.\nME-GA - Otto cycle - gas 5.5-12 bar(g).\n"
                                 "X-DF - Otto cycle - gas 6-15 bar(g)."})
    still = [p.get("type") for p in eng["parts"] if p.get("type") not in ("text", "step_track")]
    check("... lines that name nothing the kit draws get no parts guessed from the description beside them - an engine, a "
          "gauge, a scale no step moves (IGF Advanced M03 s08)", not still, eng["parts"])


def promise_part():
    """the trial of 2.133.0, gas M01 s02: the starter drew a 0-100 scale named "scale", a dial named "pressure" and a ship
    from the visual's "drawn to the same scale" and "pressure vessel", and a line's words in a box - and they shipped"""
    s02 = {"id": "s02", "kind": "slide", "title": "Three carriage conditions", "visual_kind": "comparison",
           "text": "18 bar | Fully pressurised: Type C tanks at ambient temperature, no insulation\n7 bar | Semi-pressurised / "
                   "semi-refrigerated: insulated Type C tanks, down to -48 °C\nAtmospheric | Fully refrigerated: near "
                   "atmospheric pressure, at the cargo's boiling point",
           "visual": "Three tank cross-sections side by side, drawn to the same scale - thick uninsulated pressure vessel, "
                     "thinner insulated bi-lobe tank, large insulated prismatic tank."}
    spec = cm.starter_figure({"module": 1, "screens": [s02]}, s02)
    types = [p.get("type") for p in spec["parts"]]
    check("no part is taken from the visual's words - no scale, dial or ship no line names and no step moves",
          not {"scale", "gauge", "ga"} & set(types), types)
    check("... its lines name nothing the kit draws, so they are a step track", types == ["step_track"], types)
    probs = []
    cm.kit_figure(json.dumps(spec), s02, probs, "Slide 3 (s02)")
    check("the compile refuses the figure: nothing drawn where the visual names three tanks", any("FEWER" in x for x in probs), probs)
    s05 = {"id": "s05", "kind": "slide", "title": "Pressure vessel", "visual_kind": "process",
           "text": "Cargo tank: holds the liquid at its boiling point\nThe relief valve lifts when the pressure rises\n"
                   "Boil-off is managed by the crew", "visual": "Two tanks side by side, each with its relief valve."}
    spec = cm.starter_figure({"module": 1, "screens": [s05]}, s05)
    check("a line's words in a box and a kit word inside a sentence are named in \"_starter\", so the build refuses them "
          "while they stand where it put them", sorted(x[0] for x in spec.get("_starter") or []) == ["P2", "P3"], spec.get("_starter"))
    probs = []
    cm.kit_figure(json.dumps(spec), s05, probs, "Slide 5 (s05)")
    check("... the compile refuses the stand-ins, and one tank where the visual names two",
          any("STARTER" in x for x in probs) and any("FEWER" in x for x in probs), probs)


def task_part():
    """a question answered ON a picture is drawn at --init-build when its answers name kit equipment - never a placeholder
    with its tap areas on a grid over nothing (the trial of 2.133.0: M16 q01, m01; M01 m06)"""
    import content_script as cs
    q01 = {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot",
           "question": "Tap the part of the set that sucks the foam liquid from the foam container.",
           "answer": "Foam ejector*\nFoam nozzle unit\nFire hose\nFoam container"}
    got = cm.task_figure(q01)
    check("a tap task whose answers name kit equipment gets a drawing: one part each, the answers on their part ids",
          got and [p["type"] for p in got[0]["parts"]] == ["foam_inductor", "foam_branch_pipe", "hose", "foam_container"]
          and got[1] == {"Foam ejector": "P1", "Foam nozzle unit": "P2", "Fire hose": "P3", "Foam container": "P4"}, got)
    check("... with no words on its parts - the trainee finds them", got and not any(p.get("label") for p in got[0]["parts"]), got)
    m06 = dict(q01, id="m06", answer="Bi-lobe Type C tank*\nPrismatic Type A tank\nMoss spherical Type B tank\nMembrane tank")
    got = cm.task_figure(m06)
    check("... a tank named by its containment system is that system's symbol, never four alike Type C tanks",
          got and [(p["type"], p.get("kind")) for p in got[0]["parts"]] == [("tank_type", "c"), ("tank_type", "a"),
                                                                            ("tank_type", "b"), ("tank_type", "membrane")], got)
    m01 = dict(q01, id="m01", mechanic="label_diagram", answer="Fire hose\nFoam ejector\nSmall hose\nFoam container\nFoam nozzle unit")
    got = cm.task_figure(m01)
    check("... two hoses drawn as wide as they are (a fire hose 12, a pick-up hose 6), so they can be told apart",
          got and [p.get("w") for p in got[0]["parts"] if p["type"] == "hose"] == [12, 6], got)
    check("... no drawing when an answer is a room, a ship or a thing the kit does not draw (the build then fails it)",
          cm.task_figure(dict(q01, answer="Cargo compressor room*\nElectric motor room\nAirlock")) is None
          and cm.task_figure(dict(q01, answer="Breathing apparatus*\nHelmet\nSafety lamp")) is None)
    check("... nor when two answers would be drawn alike", cm.task_figure(dict(q01, answer="Fuel tank*\nStorage tank")) is None)
    tmp = tempfile.mkdtemp(prefix="taskfig_")
    try:
        script = {"module": 16, "screens": [q01, dict(q01, id="q02", answer="Breathing apparatus*\nHelmet")]}
        sheet = {"screens": {"q01": {"figure": "", "areas": {}}, "q02": {"figure": "", "areas": {}}}}
        said = cm.task_figures(script, sheet, tmp)
        check("task_figures writes the drawing beside the module's figures and names it in the build sheet; a question it "
              "cannot draw keeps its blank", sheet["screens"]["q01"]["figure"] == "q01.kit.json"
              and os.path.isfile(os.path.join(tmp, "q01.kit.json")) and sheet["screens"]["q02"]["figure"] == ""
              and len(said) == 1, (sheet, said))
        import check_kit
        spec = json.load(open(os.path.join(tmp, "q01.kit.json"), encoding="utf-8"))
        probs = check_kit.check_spec(spec, check_kit.kit_types(), "q01.kit.json") + check_kit.why_problems(spec, "q01.kit.json")
        check("... a drawing the kit's spec and meaning checks pass (no loose hose end, its why said)", not probs, probs)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    canvas()
    by_words()
    track_part()
    task_part()
    promise_part()
    studio_part()
    print("\n%d failure(s)" % len(FAILS) if FAILS else "\nALL PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
