# -*- coding: utf-8 -*-
"""test_picture_slot - the script fixes each slide's picture slot and the words its layout holds (2.73.0).

    python test_picture_slot.py

Pinned:
  * "picture": {"kind", "aspect", "shows"} on a slide or a question answered on a picture: an unknown kind, a kind that is not
    what visual_kind needs, a photo or figure with no shape and a slot that does not say what it shows are must-fixes; a script
    written before 2.73.0 (no "picture") is read from visual_kind and only reminded;
  * a line longer than a part holds (75 words at 1024 x 768) is a must-fix - the compiler can put lines in parts, never cut one;
  * the part splitter (content_script.parts_of, which the compiler uses) keeps the old cut when it fits and otherwise makes the
    largest part as small as the lines allow (chem advanced: 78-96 words in a part on 9 slides);
  * STANDARDS.md's "Ship profile": a script naming what the course's ship does not have is said (never a stop).
"""
from __future__ import annotations

import copy
import io
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
from test_content_script import SCRIPT  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def rules(script, sid=None):
    return [(f["rule"], f["level"]) for f in cs.picture_findings(script) if sid is None or f["screen"] == sid]


def screen(script, sid):
    return next(s for s in script["screens"] if s["id"] == sid)


def main():
    sc = copy.deepcopy(SCRIPT)
    for x in sc["screens"]:
        x.pop("picture", None)
    check("a script from before 2.73.0: no must-fix, each slide reminded to write its slot",
          all(lv == cs.NOTE for _, lv in rules(sc)) and ("p_missing", cs.NOTE) in rules(sc, "s01"), rules(sc))
    check("... and its slot is read from visual_kind: a photo, a chart is a figure, model_3d is 3d, the recap has none",
          [cs.picture_of(screen(sc, x))["kind"] for x in ("s01", "s02", "s03")] == ["photo", "figure", "3d"]
          and not cs.on_picture(screen(sc, "s04")))
    check("... a question answered on a picture has a slot too, a plain choice has none",
          cs.on_picture(screen(sc, "q03")) and cs.on_picture(screen(sc, "m01")) and not cs.on_picture(screen(sc, "m02")))
    screen(sc, "s01")["picture"] = {"kind": "photo", "aspect": "16:9", "shows": "A membrane LNG carrier alongside"}
    screen(sc, "s02")["picture"] = {"kind": "figure", "aspect": "4:3", "shows": "The propane line with the three ship types"}
    screen(sc, "s03")["picture"] = {"kind": "3d", "shows": "The four tank types in a hull section"}
    check("a script with every slot written: nothing to say", rules(sc) == [], rules(sc))
    screen(sc, "s01")["picture"]["kind"] = "drawing"
    check("an unknown kind is a must-fix", ("p_kind", cs.FAIL) in rules(sc, "s01"), rules(sc, "s01"))
    screen(sc, "s01")["picture"]["kind"] = "figure"
    check("a figure slot for a planned photograph is a must-fix (the layout would be built for the wrong picture)",
          ("p_kind_differs", cs.FAIL) in rules(sc, "s01"), rules(sc, "s01"))
    screen(sc, "s01")["picture"] = {"kind": "photo", "aspect": "wide", "shows": ""}
    check("a slot's \"shows\" left empty is read from the planned visual", ("p_shows", cs.FAIL) not in rules(sc, "s01"))
    screen(sc, "s01")["visual"] = ""
    check("a photo with no shape and nothing it must show: two must-fixes",
          ("p_aspect", cs.FAIL) in rules(sc, "s01") and ("p_shows", cs.FAIL) in rules(sc, "s01"), rules(sc, "s01"))
    check("aspects read as width / height", abs(cs.aspect_of("16:9") - 16 / 9.0) < 1e-9 and cs.aspect_of("4 : 3") and
          cs.aspect_of("wide") is None and cs.aspect_of("1:0") is None)

    # the words a layout holds
    sc = copy.deepcopy(SCRIPT)
    long_line = " ".join(["word"] * 80) + "."
    screen(sc, "s02")["text"] = "A short opening line.\n" + long_line
    got = [f for f in cs.picture_findings(sc) if f["rule"] == "b_line"]
    check("a line of 80 words beside a picture is a must-fix that names the line and the budget",
          len(got) == 1 and got[0]["level"] == cs.FAIL and "80" in got[0]["detail"] and "75" in got[0]["detail"]
          and got[0]["screen"] == "s02", got)
    check("... and it blocks approval", any(f["rule"] == "b_line" for f in cs.blocking(cs.all_findings(sc))))
    screen(sc, "s02")["visual_kind"] = "none"
    screen(sc, "s02")["visual"] = ""
    screen(sc, "s02")["picture"] = {"kind": "none"}
    check("... a slide with no picture has no part budget (a text slide is measured by its own rules)",
          not [f for f in cs.picture_findings(sc) if f["rule"] == "b_line"])

    # the part splitter
    lines = ["%s." % " ".join(["w"] * n) for n in (20, 30, 28, 27, 30, 25)]          # 160 words: the old cut gave 78 + 82
    old = [[1, 2, 3], [4, 5, 6]]
    w = lambda p: sum(cs.wc(lines[i - 1]) for i in p)
    got = cs.parts_of(lines)
    check("parts: 160 words that the old cut split 78 / 82 are put in parts of 75 or fewer",
          max(w(p) for p in got) <= 75 and [i for p in got for i in p] == list(range(1, 7)), (got, [w(p) for p in got]))
    check("... with the fewest parts that fit (three)", len(got) == 3, got)
    fits = ["%s." % " ".join(["w"] * n) for n in (30, 30, 30, 30)]
    check("parts: a slide the old cut already fits is cut the same as before (no rebuilt module changes its look)",
          cs.parts_of(fits) == [[1, 2], [3, 4]], cs.parts_of(fits))
    check("parts: the build sheet's own ranges win", cs.parts_of(lines, [(1, 2), (3, 6)]) == [[1, 2], [3, 4, 5, 6]])
    one = ["%s." % " ".join(["w"] * 90), "Short."]
    check("parts: a line over the budget cannot be cut - it gets a part of its own, the rest beside it",
          cs.parts_of(one) == [[1], [2]], cs.parts_of(one))
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "compile", "scripts"))
    import compile_module as cm
    check("the compiler lays a long slide out with the same parts", cm.auto_parts(lines) == got)

    # the ship profile
    tmp = tempfile.mkdtemp(prefix="ship_")
    try:
        course = os.path.join(tmp, "course")
        os.makedirs(os.path.join(course, "working_claude"))
        sc = copy.deepcopy(SCRIPT)
        screen(sc, "s02")["notes"] += "\n- Walk the room through the cargo pump room before discharge."
        check("no STANDARDS.md: nothing said", cs.ship_findings(course, sc) == [])
        io.open(os.path.join(course, "working_claude", "STANDARDS.md"), "w", encoding="utf-8").write(
            "# Standards\n\n## Ship profile - the course's exercise ship\n\n"
            "- Pump arrangement: deepwell pumps, one in each cargo tank\n"
            "- Tank layout: 22 stainless-steel tanks, 2 slop tanks\n"
            "- Not on board: pump room, cargo pump room; booster pumps\n\n## Language\n\n- English\n")
        prof = cs.ship_profile(course)
        check("the profile is read: what the ship has, and what it has not",
              prof and ("Pump arrangement", "deepwell pumps, one in each cargo tank") in prof["rows"]
              and prof["absent"] == ["pump room", "cargo pump room", "booster pumps"], prof)
        got = cs.ship_findings(course, sc)
        check("a script naming the pump room the ship does not have is said - a note, never a stop",
              got and all(f["level"] == cs.NOTE and f["screen"] == "s02" for f in got)
              and any("pump room" in f["detail"] and "deepwell" in f["detail"] for f in got), got)
        check("... and it is in the findings the review page shows", any(f["rule"] == "sp_absent" for f in cs.all_findings(sc, course)))
        check("... never a word inside another (\"pump rooms\" counts, \"pump roomy\" does not)",
              cs.ship_findings(course, {"screens": [{"id": "s01", "kind": "slide", "text": "pump roomy"}]}) == [])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
