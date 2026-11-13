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
    o, why = lp.options("photo-explain.column", 55, "photo", 1.6, seed="c|M01", sid="s01")
    check("a wide photograph (1.6:1) is never planned into a side column, its own blueprint neither - a band across the slide",
          {x["shape"] for x in o} >= {"top", "bottom"} and "beside" not in {x["shape"] for x in o}
          and "1.6:1" in why.get("beside", "") and "0.85-1.3" in why.get("beside", ""), (o, why))
    for bp, wds, fam, asp, label in (("photo-explain.column", 81, "photo", 1.79, "M01 s08: a 1.79:1 photograph, 81 words"),
                                     ("photo-explain.column", 60, "photo", 1.73, "M01 s15b: a 1.73:1 photograph, 60 words"),
                                     ("photo-explain.column", 75, "photo", 1.33, "M01 s18: a 1.33:1 photograph, 75 words"),
                                     ("photo-explain.split", 45, "photo", 0.71, "M01 s04b: a 0.71:1 photograph"),
                                     ("explain-figure.figure-right", 60, "3d", 3.40, "M01 s11: a 3.40:1 3D scene"),
                                     ("figure-stage.figure", 32, "tiles", 0.80, "M16 s04: two photographs side by side"),
                                     ("content-in-parts.with-figure", 81, "photo", 1.65, "M16 s03: a 1.65:1 photograph in parts")):
        o, _ = lp.options(bp, wds, fam, asp, part_words=42 if bp.startswith("content-in-parts") else None, seed="c|M01", sid="s")
        check("%s: every blueprint the plan may give it takes its picture's real shape (the 2.131.0 trial put it in %s)" % (label, bp),
              o and all(lp.picture_fit(x["bp"], fam, asp) is None for x in o), o)
    o, _ = lp.options("explain-figure.figure-right", 40, "photo", 0.7, seed="c|M01", sid="s02")
    check("a portrait photograph (0.7:1) takes the tall box beside the words", o[0]["bp"] == "explain-figure.figure-tall", o[:3])
    o, why = lp.options("long-explanation.model", 64, "3d", 0.84, seed="c|M01", sid="s03")
    check("a tall 3D scene (a transverse section) is never put in a band - and the plan says why",
          {x["shape"] for x in o} == {"beside"} and "0.8:1" in why.get("top", ""), (o, why))
    o, why = lp.options("explain-figure.figure-right", 58, "3d", 2.0, names=20, seed="c|M01", sid="s04")
    check("a band shows at most band_names names; more stay beside", "top" not in {x["shape"] for x in o} and "names" in why.get("top", ""), why)
    o, why = lp.options("reading-with-figure.figure-right", 80, "drawing", 2.0, seed="c|M01", sid="s05")
    check("words over a band's measured budget never go into the band while a shape that holds them takes the picture",
          "top" not in {x["shape"] for x in o} and "holds" in why.get("top", "") and not any(x.get("over") for x in o), why)
    o, why = lp.options("photo-explain.column", 81, "photo", 1.79, seed="c|M01", sid="s08")
    check("words no shape its picture takes holds: the blueprints over by least, marked over - never a box the picture "
          "does not fit (the script check asks to split the slide)",
          o and all(x.get("over") == (81 - lp.BUDGETS["under_top_row"], 0, 0) and x["shape"] in ("top", "bottom") for x in o), (o, why))
    o, why = lp.options("explain-figure.figure-right", 40, "drawing", 2.0, fixed="its build sheet names its template", sid="s06")
    check("a slide whose build sheet names its template keeps it while its picture fits it", [x["bp"] for x in o] == ["explain-figure.figure-right"]
          and why["top"] == "its build sheet names its template")
    o, why = lp.options("photo-explain.column", 40, "photo", 2.5, fixed="its build sheet names its template", sid="s07")
    check("... and keeps nothing when its picture does not fit it: the compiler refuses the deck, naming the blueprints that do",
          o == [] and "0.85-1.3" in why["beside"] and "photo-explain.full" in lp.fitting("photo", 2.5, "text-figure"), (o, why))
    check("a blueprint's mirror (the picture on the left) takes the pictures and the words of its base",
          lp.LIB["reference-table.figure-left"]["fits"] == lp.LIB["reference-table.with-figure"]["fits"])
    check("one budget: a blueprint holds the measured words of layout-templates.json, never its template's word range "
          "(explain-figure's 60 is where reading-with-figure starts, not what fits)",
          lp.holds("explain-figure.figure-left", "3d")["words"] == lp.BUDGETS["beside_3d"]
          and lp.holds("explain-figure.figure-top", "3d")["words"] == lp.BUDGETS["under_band"]
          and lp.holds("photo-explain.column", "photo")["words"] == lp.BUDGETS["photo_column"]
          and lp.holds("figure-stage.figure", "photo")["words"] == lp.BUDGETS["stage"])

    print("\n-- a table is measured by its rows and its words (budgets table_...)")
    check("the table blueprints are there: beside, under and over a band, alone - each with its measured budget",
          {"reference-table.with-figure", "reference-table.figure-top", "reference-table.figure-bottom", "reference-table.text-only"} <= set(lp.LIB)
          and all(isinstance(lp.table_budget(v, f)["rows"], int) for v in ("with-figure", "figure-top", "figure-bottom", "text-only")
                  for f in ("photo", "tiles", "drawing", "3d")))
    wide = lambda rows, words, aspect=2.0: lp.options("reference-table.with-figure", words, "drawing", aspect, 3, None, None, "c|M01", "s03", rows)
    o, why = wide(4, 36)
    check("a table of 4 rows and 36 words beside or across a wide drawing fits every shape", {x["shape"] for x in o} >= {"beside", "top", "bottom"}, (o, why))
    o, why = wide(6, 48)
    check("6 rows and 48 words fit beside the picture, not a band - the plan never puts them in a band, and says why",
          {x["shape"] for x in o} == {"beside"} and "6 rows" in why.get("top", "") and "holds 4 and 40" in why.get("top", ""), (o, why))
    o, why = wide(6, 57, 1.3)
    check("M01 s14 (6 rows, 57 words) fits no shape - the plan keeps it beside, over by least, and the script check asks to split it",
          {x["shape"] for x in o} == {"beside"} and all(x.get("over") for x in o) and "holds" in why.get("top", ""), (o, why))
    o, why = wide(6, 73, 1.3)
    check("M01 s03 (6 rows, 73 words) the same", {x["shape"] for x in o} == {"beside"} and all(x.get("over") for x in o), (o, why))
    o, why = wide(3, 70)
    check("few rows, many words: over the words of every shape, even with 3 rows", {x["shape"] for x in o} == {"beside"}
          and all(x.get("over") == (22, 0, 0) for x in o), (o, why))

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

    print("\n-- a picture in a box of another shape (picture_misfits: the compiler's must-fix, the fault report's layout fault)")
    import tempfile
    from PIL import Image
    mdir = tempfile.mkdtemp(prefix="lp_")
    os.makedirs(os.path.join(mdir, "assets", "img"))
    for name, size in (("wide.jpg", (358, 200)), ("tall.jpg", (142, 200)), ("square.jpg", (220, 200))):
        Image.new("RGB", size).save(os.path.join(mdir, "assets", "img", name))
    pic = lambda sid, bp, img, extra="": ('<section class="slide" id="%s" data-template="%s.v1" data-variant="%s"><h2>T</h2>'
                                          '<div class="fill fig"><img src="../assets/img/%s"></div>%s</section>'
                                          % (sid, bp.split(".")[0], bp.split(".")[1], img, extra))
    page = (pic("s08", "photo-explain.column", "wide.jpg") + pic("s04b", "figure-stage.figure", "tall.jpg")
            + pic("s02", "photo-explain.column", "square.jpg")
            + pic("s05", "explain-figure.figure-top", "wide.jpg", '<figure class="inset"><img src="../assets/img/tall.jpg"></figure>')
            + pic("s09", "task-launch.tablet", "wide.jpg"))
    got = {x["slide"]: x for x in lp.picture_misfits(page, mdir)}
    check("a 1.79:1 photograph in photo-explain.column and a 0.71:1 one in figure-stage are misfits, with the box's range and "
          "the blueprints that take them", set(got) == {"s08", "s04b"} and got["s08"]["range"] == [0.85, 1.3]
          and "reading-with-figure.figure-top" in got["s08"]["fit"] and "explain-figure.figure-tall" in got["s04b"]["fit"], got)
    check("... a photograph of its box's shape is none, an inset photograph is not the slide's picture, and a slide the plan "
          "does not lay out (a task launch) is not judged", "s02" not in got and "s05" not in got and "s09" not in got, got)

    print("\n-- the templates that have the room answer: the same rule, a band of their own (the trial's M01 s21)")
    Image.new("RGB", (506, 200)).save(os.path.join(mdir, "assets", "img", "band.jpg"))               # 2.53:1
    one = {"scenario": "picture-left", "worked-example": "figure", "true-false": "picture", "name-parts": "picture"}
    keep = {"scenario": "figure-top", "worked-example": "figure-bottom", "true-false": "figure-top", "name-parts": "figure-bottom"}
    page = "".join(pic("s%02d" % k, "%s.%s" % tv, "band.jpg") for k, tv in enumerate(one.items(), 21)) \
        + "".join(pic("b%02d" % k, "%s.%s" % tv, "band.jpg") for k, tv in enumerate(keep.items(), 21))
    got = {x["slide"]: x for x in lp.picture_misfits(page, mdir)}
    check("a 2.53:1 photograph beside the words of a scenario, a worked example, a true or false or naming the parts is a "
          "misfit (M01 s21 in scenario.picture-left), and the blueprints that take it are the same template's bands",
          set(got) == {"s21", "s22", "s23", "s24"} and got["s21"]["bp"] == "scenario.picture-left"
          and all(x["fit"] and all(f.startswith(x["bp"].split(".")[0] + ".figure-") for f in x["fit"]) for x in got.values()), got)
    check("... and in the template's band it is none", not [s for s in got if s.startswith("b")], got)
    for tid, var in one.items():
        opts, why = lp.options("%s.%s" % (tid, var), 20, "photo", 2.53, 4, None, None, "course|M01", "s21")
        check("options() moves a %s slide with a 2.53:1 photograph to its own band, never to another template" % tid,
              opts and {o["bp"].split(".")[0] for o in opts} == {tid} and {o["shape"] for o in opts} == {"top", "bottom"}
              and "%s.%s" % (tid, var) in why.get("beside", ""), (opts, why))
        opts, _ = lp.options("%s.%s" % (tid, var), 20, "photo", 1.1, 4, None, None, "course|M01", "s21")
        check("... and keeps a 1.1:1 one beside the words, in its own box", [o["bp"] for o in opts] == ["%s.%s" % (tid, var)], opts)
    for bp in ("three-content-blocks.figure-left", "long-explanation.points", "drill.say-it", "drill.find-it", "opening.photo"):
        check("%s says the shape of picture its box takes (a mirror takes its base's)" % bp,
              bool((lp.LIB[bp].get("fits") or {}).get("aspect")))
    two = pic("s04", "figure-stage.figure", "square.jpg").replace("</div>", '<img src="../assets/img/tall.jpg"></div>', 1)
    t = lp.picture_misfits(two, mdir)
    check("two photographs in a blueprint that takes no tiles (M16 s04): a misfit, the narrowest counts",
          len(t) == 1 and t[0]["family"] == "tiles" and t[0]["range"] is None and abs(t[0]["aspect"] - 0.71) < 0.01, t)
    over = [item("s08", "photo-explain.column", 81, "photo", 1.79)]
    n = lp.notes(over, lp.plan(over))
    check("the plan's note names a slide over every shape its picture takes, and asks to split it",
          any("s08" in x and "%d words over" % (81 - lp.BUDGETS["under_top_row"]) in x and "split" in x for x in n), n)

    long_title(cs)
    print("\n%d passed, %d failed" % (len(PASSED), len(FAILS)))
    return 1 if FAILS else 0


# the gas trial's M01 s11 and s20: under or over a picture band at 1024 x 768 their words were cut 29 and 65 px - the
# words within the band's budget, the title on two lines
S11 = {"id": "s11", "kind": "slide", "title": "The IGC Code - one standard for gas tankers", "visual_kind": "video_real",
       "layout": "visual_wide", "picture": {"kind": "photo", "aspect": "16:9", "shows": "Film still: gas carriers at sea"},
       "visual": "A short clip from the old course film - gas carriers at sea and alongside.", "minutes": 1,
       "text": "The IGC Code is the international standard for the safe carriage of liquefied gases in bulk by sea.\n"
               "From the products carried, it sets the design and construction of the ship and the equipment it carries, to "
               "minimise the risk to the ship, its crew and the environment.\nWhat a gas tanker looks like on deck follows from it."}
S20 = {"id": "s20", "kind": "slide", "title": "Integral, membrane and semi-membrane tanks", "visual_kind": "model_3d",
       "layout": "split", "picture": {"kind": "3d", "aspect": "4:3", "shows": "Three hull sections"}, "minutes": 2,
       "visual": "3D hull sections, turnable: an integral tank, a membrane tank, a semi-membrane tank.",
       "text": "Integral - part of the hull, stressed by the same loads; design pressure normally below 0.25 bar; not normally "
               "allowed for cargo below -10 °C.\nMembrane - not self-supporting: a thin gastight layer supported through "
               "insulation by the inner hull.\nSemi-membrane - flat parts supported by the hull, rounded edges that take "
               "expansion and contraction.\nMembrane and semi-membrane need a complete secondary barrier."}
S20_ASPECT = 1.96          # its scene's home view: three hull sections in a row (kit3d_aspect of the built spec)


def long_title(cs):
    print("\n-- a title on two lines at 1024 x 768 takes its line from the words under or over a band")
    one, two = "Independent tanks - Type A, B and C", "Keeping gas out of the accommodation"
    check("a title of up to 35 characters stands on one line at 1024 x 768, of 36 on two (measured on the trial's M01 deck)",
          (lp.title_lines(one), lp.title_lines(two), lp.title_lines(S11["title"]), lp.title_lines("")) == (1, 2, 2, 1))
    band = lp.holds("explain-figure.figure-top", "photo", S11["title"])
    check("under a two-line title a band holds 53 words, not 65; beside a picture the measured budget stands",
          band["words"] == 53 and lp.holds("explain-figure.figure-top", "photo", one)["words"] == lp.BUDGETS["under_top_row"]
          and lp.holds("long-explanation.model", "3d", S20["title"])["words"] == lp.BUDGETS["beside_3d"]
          and lp.holds("reference-table.figure-top", "drawing", S20["title"])["rows"] == 3, band)
    w11, w20 = cs.wc(" ".join(cs.lines_of(S11["text"]))), cs.wc(" ".join(cs.lines_of(S20["text"])))
    o20, why20 = lp.options("long-explanation.figure-top", w20, "3d", S20_ASPECT, 14, None, None, "c|M01", "s20", title=S20["title"])
    check("s20 (64 words, a wide 3D scene, a 42-character title): planned beside, where its words fit - never in a band",
          o20 and {o["shape"] for o in o20} == {"beside"} and not any(o.get("over") for o in o20)
          and "top" in why20 and "53" in why20["top"], (o20, why20))
    o, _ = lp.options("long-explanation.figure-top", w20, "3d", S20_ASPECT, 14, None, None, "c|M01", "s20", title="Membrane tanks")
    check("... under a one-line title its band fits as before", {"top", "bottom"} <= {x["shape"] for x in o}, o)
    o11, _ = lp.options("explain-figure.figure-right", w11, "photo", 16 / 9.0, 0, None, None, "c|M01", "s11", title=S11["title"])
    check("s11 (59 words, a 16:9 photograph, a 43-character title): no shape its photograph takes holds them - every option "
          "is over, so the plan says it and the fit gate is not the first to find it",
          o11 and all(x.get("over") for x in o11), o11)
    plan = lp.plan([{"id": "s11", "own": "beside", "own_bp": "explain-figure.figure-right", "options": o11, "why": {}},
                    {"id": "s20", "own": "beside", "own_bp": "long-explanation.figure-top", "options": o20, "why": why20}])
    check("... and s20's plan is beside", lp.shapes_of(plan).get(1) == "beside", lp.shapes_of(plan))
    found = [f for f in cs.theory_findings({"module": 1, "screens": [S11, S20]})[0] if f["rule"] == "t_no_shape"]
    check("the script check makes s11 a must-fix before approval - split it, or a title of one line gives the words their "
          "room; s20 fits beside, nothing to say",
          [(f["screen"], f["level"]) for f in found] == [("s11", cs.FAIL)] and "title of up to 35 characters" in found[0]["fix"]
          and "53" in found[0]["fix"], found)


if __name__ == "__main__":
    sys.exit(main())
