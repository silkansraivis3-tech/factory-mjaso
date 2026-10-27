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


def canvas():
    s4 = SLIDES["s04"]
    plain = cm.starter_figure(SCRIPT, s4)
    check("no photograph to show: the canvas is the figure column's shape at the width it shows at, 416 x 254 (2.66.0)", plain["size"] == [416, 254], plain["size"])
    pool = [("vm.jpg", {"shows": ["vent mast"]}, "m", "u:vm")]
    strip = cm.starter_figure(SCRIPT, s4, pool)
    check("a cleared photograph shows a thing the starter draws (the L57 row goes under it): the canvas is the column less "
          "the row, 416 x 178 (M01 s04: a 682 x 292 px panel)", strip["size"] == [416, 178], strip["size"])
    taken = cm.starter_figure(SCRIPT, s4, pool, {"u:vm": "M02 s03"})
    check("... not when the course already shows that photograph (L58: the row leaves it out)", taken["size"] == [416, 254], taken["size"])
    for sid in ("s03", "s04"):                          # drawn parts only (s06 is mostly text callouts: the studio judges it)
        spec = cm.starter_figure(SCRIPT, SLIDES[sid])
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


def main():
    canvas()
    by_words()
    studio_part()
    print("\n%d failure(s)" % len(FAILS) if FAILS else "\nALL PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
