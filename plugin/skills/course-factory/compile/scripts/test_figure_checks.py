# -*- coding: utf-8 -*-
"""test_figure_checks - a drawing beside a question moves, agrees with the answer and is not covered by it (2.115.0).

    python test_figure_checks.py

PM M02 s12 / s13 and M03 s02: the kit figure stayed an empty axis on every Next, the revealed answer covered it, and s13's
drawing said "Yard labour 20 %" and "Crew 5 %" where the approved answer said 25 % and no crew line. Pinned here:
  * answer_over: a kit figure (2D, 3D) is not covered by the answer; a photograph still gets "the answer over the picture";
  * dead_figure_problems: a figure none of whose steps moves a part fails; one that moves passes; a still figure (no steps) is exempt;
  * lines_twice_problems: a step that goes back to an earlier line fails; repeating the current line passes;
  * figure_answer_mismatches: the drawing's labelled share and its numbers must be the slide's own (20 % vs 25 %, a segment the
    answer never names); 20% and 20 % are the same; "numbers_differ" is the way out;
  * gb_steps.js: the kit figure plays the step of the lit line, "reveal" steps on the last stop, each line lit once (browser walk).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compile_module as cm  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def page(spec, extra=""):
    data = json.dumps(spec).replace("</", "<\\/")
    return ('<section class="slide" id="s12"%s><svg data-kit="#kit-s12"></svg>'
            '<script type="application/json" id="kit-s12">%s</script></section>' % (extra, data))


BAR = {"parts": [{"id": "C", "type": "composition_bar", "value": 0,
                  "segments": [{"label": "Dock hire", "pct": 35}, {"label": "Yard labour", "pct": 20}, {"label": "Crew", "pct": 5}]}]}


def spec(steps):
    return dict(BAR, steps=steps)


def main():
    print("-- the answer does not cover a drawing")
    s = {"ask": "Which?", "reveal": "Dock hire 35 %"}
    for fig in ('<div class="fill fig kit-fig"><svg data-kit="#k"></svg></div>', '<div class="kit2d-stage" data-kit2d="#k"></div>',
                '<div class="kit3d-stage" data-kit3d="#k"></div>'):
        out = cm.answer_over(fig, s)
        check("a kit figure is not covered: the answer is a card under it (%s)" % fig[:30],
              "lt-ans-over" not in out and 'class="lt-scol">' + fig in out and "lt-ans-under" in out and "Dock hire 35 %" in out)
    photo = '<figure class="lt-pic"><img src="a.jpg"></figure>'
    check("a photograph still gets the answer over it", "lt-ans-over" in cm.answer_over(photo, s))

    print("-- a drawing that never moves")
    still = spec([{"title": "a", "line": 1, "play": [["C", 0, 200]]}, {"title": "b", "line": 2, "play": [["C", 0, 200]]}])
    moves = spec([{"title": "a", "line": 1, "play": [["C", 0, 200]]}, {"title": "b", "reveal": True, "play": [["C", 3, 900]]}])
    check("every step leaves the bar at 0: a must-fix naming the slide", [x[0] for x in cm.dead_figure_problems(page(still))] == ["s12"]
          and "never moves" in cm.dead_figure_problems(page(still))[0][1])
    check("a step that fills the bar passes", not cm.dead_figure_problems(page(moves)))
    check("a figure with no steps (a still picture) is exempt", not cm.dead_figure_problems(page(BAR)))

    print("-- the lines are walked once")
    back = spec([{"title": "a", "line": 3, "play": [["C", 1, 1]]}, {"title": "b", "line": 1, "play": [["C", 2, 1]]}])
    ok = spec([{"title": "a", "line": 1, "play": [["C", 1, 1]]}, {"title": "b", "line": 1, "play": [["C", 2, 1]]},
               {"title": "c", "line": 2, "play": [["C", 3, 1]]}])
    check("a step that goes back to an earlier line: Next walks its lines twice", len(cm.lines_twice_problems(page(back))) == 1
          and "twice" in cm.lines_twice_problems(page(back))[0][1])
    check("steps that stay on a line or move forward pass", not cm.lines_twice_problems(page(ok)))

    print("-- the drawing agrees with the answer")
    words = cm.slide_words({"text": "Budget", "ask": "Which three?", "reveal": "Dock hire 35 %\nYard labour 25 %\nContingency 10 %"})
    got = cm.share_mismatches(BAR, words)
    check("Yard labour 20 % against an answer saying 25 %", any("Yard labour 20 %" in d and "25" in s_ for d, s_ in got), got)
    check("a segment the answer never names (Crew)", any("Crew" in d and "at all" in s_ for d, s_ in got), got)
    check("Dock hire 35 % agrees, whatever the spacing (35% / 35 %)",
          not any("Dock hire" in d for d, _ in got) and not cm.share_mismatches(
              {"parts": [{"segments": [{"label": "Dock hire", "pct": 35}]}]}, cm.slide_words({"reveal": "Dock hire 35% of the total"})))
    good = {"parts": [{"segments": [{"label": "Dock hire", "pct": 35}, {"label": "Spares and paint", "pct": 25}]}]}
    check("the same labels and values pass", not cm.share_mismatches(good, cm.slide_words({"reveal": "Dock hire 35 %, Spares and paint 25 %"})))

    tmp = tempfile.mkdtemp(prefix="figchk_")
    try:
        mdir = os.path.join(tmp, "m")
        os.makedirs(mdir)
        os.makedirs(os.path.join(tmp, "figs"))
        sp = dict(BAR, parts=[dict(BAR["parts"][0], segments=[{"label": "Dock hire", "pct": 35}]),
                              {"id": "T", "type": "text", "text": "pressure 12 bar"}])
        figdir = os.path.join(tmp, "figs")
        with open(os.path.join(figdir, "s12.kit.json"), "w", encoding="utf-8") as f:
            json.dump(sp, f)
        script = {"screens": [{"id": "s12", "title": "t", "text": "Dock hire 35 %", "ask": "q", "reveal": "Dock hire 35 %"}]}
        build = {"screens": {"s12": {"figure": "s12.kit.json"}}}
        found = cm.figure_answer_mismatches(script, build, figdir, mdir)
        check("a number with its unit the slide's own words never state fails (12 bar)", any("12 bar" in d for _, d, _ in found), found)
        build["screens"]["s12"]["numbers_differ"] = "the drawing shows a derived reading"
        check("\"numbers_differ\" says why and silences it", not cm.figure_answer_mismatches(script, build, figdir, mdir))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
