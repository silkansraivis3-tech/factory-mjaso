# -*- coding: utf-8 -*-
"""test_layout_plan - every blueprint a file, scored like an engineer would (the picture's real shape against each box, the
words against each budget), and the deck's plan: never the same shape twice in a row, beside on at most about half of
the teaching slides, at least four shapes in ten, the same plan for the same input.

    python test_layout_plan.py
"""
from __future__ import annotations

import json
import os
import sys

import layout_plan as lp

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS, PASSED = [], []
HERE = os.path.dirname(os.path.abspath(__file__))


def check(name, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  -> %s" % (detail,)))
    (PASSED if ok else FAILS).append(name)


def item(sid, own_bp, words, family, aspect, names=3, fixed=None, seed="course|M01"):
    opts, why = lp.options(own_bp, words, family, aspect, names, None, fixed, seed, sid)
    return {"id": sid, "own": lp.MAP[own_bp], "own_bp": own_bp, "options": opts, "why": why, "fixed": fixed}


def section(sid, bp, shapes=None):
    t, v = bp.split(".", 1)
    return ('<section class="slide" id="%s" data-template="%s.v1" data-variant="%s" data-title="T"%s></section>'
            % (sid, t, v, ' data-shapes="%s"' % " ".join(shapes) if shapes else ""))


def main():
    print("\n-- the library: one file a blueprint")
    lt = json.load(open(os.path.join(lp.KNOW, "layout-templates.json"), encoding="utf-8"))
    missing = ["%s.%s" % (t, v) for t, x in lt["templates"].items() for v in x["variants"] if "%s.%s" % (t, v) not in lp.LIB]
    check("every template and variant of layout-templates.json has its blueprint file", not missing, missing)
    check("every blueprint names its shape, one of %s" % ", ".join(lp.ORDER),
          all(b.get("shape") in lp.ORDER + [""] for b in lp.LIB.values()), [k for k, b in lp.LIB.items() if b.get("shape") not in lp.ORDER + [""]])
    check("the new layouts are there: words over a band, a band over words (a drawing or 3D too), a tall box beside",
          {"explain-figure.figure-bottom", "long-explanation.figure-top", "procedure.figure-bottom", "explain-figure.figure-tall",
           "content-in-parts.figure-bottom"} <= set(lp.LIB)
          and lp.shape_of("explain-figure", "figure-bottom") == "bottom" and lp.shape_of("explain-figure", "figure-tall") == "beside"
          and "3d" in lp.LIB["explain-figure.figure-top"]["fits"]["pictures"])
    check("a picture on the left and one on the right are one look (beside); a task launch and the recap are none",
          lp.shape_of("explain-figure", "figure-left") == lp.shape_of("explain-figure", "figure-right") == "beside"
          and lp.shape_of("task-launch", "tablet") == "" and lp.shape_of("recap", "cards") == "")

    print("\n-- a picture's real shape")
    hull = {"view": {"az": 24, "el": 23}, "parts": [{"type": "hull", "x": [-20, 20], "half": 7, "top": 12}]}
    section_ = {"view": {"az": 8, "el": 10}, "parts": [{"type": "hull", "x": [-3, 3], "half": 7, "top": 12}]}
    a1, a2 = lp.kit3d_aspect(hull), lp.kit3d_aspect(section_)
    check("a 3D scene's shape is its home view's: a ship cut open is wide, a transverse section is not", a1 > 1.6 and a2 < 1.1, (a1, a2))
    check("a 2D drawing's shape is its size", abs(lp.figure_aspect('<script type="application/json">{"size": [900, 300], "parts": []}</script>') - 3.0) < 1e-6)

    print("\n-- each slide scored like an engineer would")
    o, _ = lp.options("photo-explain.column", 55, "photo", 1.6, seed="c|M01", sid="s01")
    best = {}
    for x in o:
        best.setdefault(x["shape"], x["cost"])
    check("a wide photograph (1.6:1) costs more in a side column than in a band across the slide - never letterboxed beside",
          best.get("top", 99) < best.get("beside", 0) and best.get("bottom", 99) < best.get("beside", 0), best)
    o, _ = lp.options("explain-figure.figure-right", 40, "photo", 0.7, seed="c|M01", sid="s02")
    check("a portrait photograph (0.7:1) takes the tall box beside the words", o[0]["bp"] == "explain-figure.figure-tall", o[:3])
    o, why = lp.options("long-explanation.model", 64, "3d", 0.84, seed="c|M01", sid="s03")
    check("a tall 3D scene (a transverse section) is never put in a band - and the plan says why",
          {x["shape"] for x in o} == {"beside"} and "0.8:1" in why.get("top", ""), (o, why))
    o, why = lp.options("explain-figure.figure-right", 58, "3d", 2.0, names=20, seed="c|M01", sid="s04")
    check("a band shows at most band_names names; more stay beside", "top" not in {x["shape"] for x in o} and "names" in why.get("top", ""), why)
    o, why = lp.options("reading-with-figure.figure-right", 95, "drawing", 2.5, seed="c|M01", sid="s05")
    check("words over a band's measured budget never go into the band - the words are never cut",
          "top" not in {x["shape"] for x in o} and "holds" in why.get("top", ""), why)
    o, why = lp.options("explain-figure.figure-right", 40, "drawing", 2.5, fixed="its build sheet names its template", sid="s06")
    check("a slide whose build sheet names its template keeps it", [x["bp"] for x in o] == ["explain-figure.figure-right"]
          and why["top"] == "its build sheet names its template")

    print("\n-- a table is measured by its rows and its words (budgets table_...)")
    check("the table blueprints are there: beside, under and over a band, alone - each with its measured budget",
          {"reference-table.with-figure", "reference-table.figure-top", "reference-table.figure-bottom", "reference-table.text-only"} <= set(lp.LIB)
          and all(isinstance(lp.table_budget(v, f)["rows"], int) for v in ("with-figure", "figure-top", "figure-bottom", "text-only")
                  for f in ("photo", "tiles", "drawing", "3d")))
    wide = lambda rows, words, aspect=2.5: lp.options("reference-table.with-figure", words, "drawing", aspect, 3, None, None, "c|M01", "s03", rows)
    o, why = wide(4, 36)
    check("a table of 4 rows and 36 words beside or across a wide drawing fits every shape", {x["shape"] for x in o} >= {"beside", "top", "bottom"}, (o, why))
    o, why = wide(6, 48)
    check("6 rows and 48 words fit beside the picture, not a band - the plan never puts them in a band, and says why",
          {x["shape"] for x in o} == {"beside"} and "6 rows" in why.get("top", "") and "holds 4 and 40" in why.get("top", ""), (o, why))
    o, why = wide(6, 57, 1.3)
    check("M01 s14 (6 rows, 57 words) fits no shape - the plan keeps its own, and the script check asks to split it",
          [x["bp"] for x in o] == ["reference-table.with-figure"] and "holds" in why.get("top", ""), (o, why))
    o, why = wide(6, 73, 1.3)
    check("M01 s03 (6 rows, 73 words) the same", [x["bp"] for x in o] == ["reference-table.with-figure"], (o, why))
    o, why = wide(3, 70)
    check("few rows, many words: over the words of every shape, even with 3 rows", [x["bp"] for x in o] == ["reference-table.with-figure"], (o, why))

    print("\n-- the deck's plan")
    deck = [item("s%02d" % k, "explain-figure.figure-right", 50, "3d", 2.0) for k in range(1, 32)]
    plan = lp.plan(deck)
    sh = lp.shapes_of(plan)
    sc = lp.score(deck, sh)
    before = lp.score(deck, {i: "beside" for i in range(len(deck))})
    check("27 of 31 slides the same shape is what the owner saw; the plan of the same 31 slides: no shape twice in a row",
          len(before["repeats"]) == 30 and not sc["repeats"], lp.line(deck, sh))
    check("... beside on at most about half of them", sc["beside"] <= sc["cap"], sc)
    four = []
    for k in range(1, 13):
        opts = [{"bp": None, "shape": s, "cost": 0.0} for s in ("beside", "top", "bottom")]
        if k == 7:
            opts.append({"bp": None, "shape": "stage", "cost": 5.0})       # a worse fit, the one slide that has it
        four.append({"id": "s%02d" % k, "own": "beside", "options": opts})
    got = lp.shapes_of(lp.plan(four))
    check("... and at least four shapes in a module of ten slides or more: the one slide that fits a fourth shape takes it, "
          "even when it fits it less well", sorted(set(got.values())) == ["beside", "bottom", "stage", "top"] and got[6] == "stage"
          and not lp.score(four, got)["repeats"], got)
    check("the same input gives the same plan", lp.plan(deck) == plan)
    other = [item(x["id"], x["own_bp"], 50, "3d", 2.0, seed="course|M02") for x in deck]
    check("another module's seed settles near-equal fits another way, so two decks do not look alike",
          lp.shapes_of(lp.plan(other)) != sh)
    fixed = [item("s%02d" % k, "explain-figure.figure-right", 50, "3d", 1.0) for k in range(1, 4)]
    fp = lp.plan(fixed)
    n = lp.notes(fixed, fp)
    check("slides that fit one shape only keep it, and the note names each and why",
          set(lp.shapes_of(fp).values()) == {"beside"} and any("s01 fits only beside" in x and "1.0:1" in x for x in n), n)
    echo = [item("s01", "explain-figure.figure-right", 50, "3d", 1.0), dict(item("s02", "explain-figure.figure-right", 50, "3d", 1.0), echo=True)]
    check("a comparison may take the shape of the slide before it", not lp.score(echo, lp.shapes_of(lp.plan(echo)))["repeats"])
    brk = [item("s01", "explain-figure.figure-right", 50, "3d", 1.0), {"id": "t01", "own": ""},
           item("s02", "explain-figure.figure-right", 50, "3d", 1.0)]
    check("a task launch between two slides breaks the run", not lp.score(brk, lp.shapes_of(lp.plan(brk)))["repeats"])
    st = lp.stats(deck, {i: "beside" for i in range(len(deck))})
    check("the scorecard's numbers: shapes, the longest run by shape, the beside share",
          st == {"look_shapes": 1, "same_look_in_a_row": 31, "beside_share": 100}, st)

    print("\n-- the script stage (content_script.py render)")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
    import content_script as cs
    words = "A gas carrier carries its cargo as a liquid, under pressure, refrigerated or both.\n" \
            "The cargo containment system sets the hull arrangement in the cargo area of the ship."
    screens = [{"id": "s%02d" % k, "kind": "slide", "title": "Slide %d" % k, "layout": "split", "visual_kind": "model_3d",
                "visual": "A ship.", "text": words, "minutes": 2} for k in range(1, 11)]
    screens.insert(5, {"id": "t01", "kind": "task-slide", "title": "SC1 - x", "text": "Do it.", "opens": "SC1", "minutes": 4})
    got = cs.shape_line({"module": 1, "course_title": "T", "screens": screens})
    seq = got.split(" - ")[0].split()
    check("render prints the module's planned shapes as one line, with its longest run and its beside share - before approval",
          len([x for x in seq if x != "|"]) == 10 and "|" in seq and "longest run" in got and "beside" in got
          and all(a != b for a, b in zip(seq, seq[1:])), got)

    print("\n-- the built deck, read back (check_course_package.py)")
    page = "".join(section("s%02d" % k, "explain-figure.figure-right", ["beside", "top", "bottom"]) for k in range(1, 13))
    bad = lp.problems(page)
    check("a deck of twelve beside slides that fit a band too: a must-fix, naming the run", bad and "s01-s02 beside" in bad[0], bad)
    page2 = "".join(section("s%02d" % k, "explain-figure.figure-right", ["beside"]) for k in range(1, 13))
    check("... and none when the slides fit beside only - nothing the plan could have done", lp.problems(page2) == [])
    alt = "".join(section("s%02d" % k, ("explain-figure.figure-right", "explain-figure.figure-top", "explain-figure.figure-bottom",
                                         "figure-stage.figure")[k % 4], ["beside", "top", "bottom", "stage"]) for k in range(1, 13))
    check("a planned deck passes", lp.problems(alt) == [], lp.problems(alt))

    print("\n%d passed, %d failed" % (len(PASSED), len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
