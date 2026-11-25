# -*- coding: utf-8 -*-
"""test_task_pages_walk - the task-page fixes of the IT course walk review (2.138.0), pinned without a browser.

    python test_task_pages_walk.py

  * the group picker's wrapper is .grp-picks - it was ".grp", the class of a sort group, so every sort group took the
    picker's margin:auto and shrank to a sliver (M03 q03 / check m04);
  * a card that said "5 Server" for a drawing whose numbers are hidden says "Server" (its key is made from what it says);
  * five steps to put in order have their bank beside them; four do not;
  * order / sort / match say to drag (M02 q04, check m02), and every other way of answering says what to do under its
    question - a multi-select how many, a calculation its unit and rounding;
  * the engine's CSS holds the compact lines after Check, the label-beside layout and the zoom button's guard.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import task_pages as tp  # noqa: E402

SKILLS = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CSS = open(os.path.join(SKILLS, "course-task-ux", "assets", "gb_answer.css"), encoding="utf-8").read()
JS = open(os.path.join(SKILLS, "course-task-ux", "assets", "gb_answer.js"), encoding="utf-8").read()
ZOOM = open(os.path.join(SKILLS, "course-module-ux", "assets", "gb_zoom.js"), encoding="utf-8").read()

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " - %s" % (detail,)))
    if not ok:
        FAILS.append(name)


# the picker is not a sort group
html_ = tp.group_screen({"N": "Ship navigators", "T": "Ship technicians"}, tp.WORDS["en"])
check("the picker's wrapper is not .grp", 'class="grp"' not in html_ and 'class="grp-picks"' in html_, html_[:300])
check("the CSS styles .grp-picks, and no bare .grp{display:grid}", ".grp-picks{display:grid" in CSS and ".grp{display:grid" not in CSS)

# numbers that name hidden markers
check("every answer numbered: the cards lose the number",
      tp.unnumbered(["1 Firewall", "2 Router", "5 Server"]) == {"1 Firewall": "Firewall", "2 Router": "Router", "5 Server": "Server"})
check("one answer unnumbered: nothing is changed", tp.unnumbered(["1 Firewall", "Router"]) == {})
check("the same number twice: nothing is changed", tp.unnumbered(["2 Stroke engine", "2 Router"]) == {})
check("one answer alone: nothing is changed", tp.unnumbered(["3 Phase"]) == {})
a = tp.chips("q02", [("Server", "hit-sv"), ("Router", "hit-rt")])
check("a card's key is made from the words it shows",
      all(tp.cs.gb_key("q02", t, v) in "".join(a) for t, v in [("Server", "hit-sv"), ("Router", "hit-rt")]), a)

# the bank beside five steps
check("five steps in order: the bank beside", tp.many(5, at=tp.ORDER_MANY) == ' data-many="1"')
check("four steps in order: the bank below", tp.many(4, at=tp.ORDER_MANY) == "")
check("five cards to match: unchanged (six or more)", tp.many(5) == "")

# the line that says to drag
for k in ("order_say", "sort_say", "match_say"):
    check("words: " + k, "rag" in tp.WORDS["en"].get(k, ""), tp.WORDS["en"].get(k))

# every way of answering says what to do: its own line, or the one under the question (what_to_do)
import json  # noqa: E402
import tempfile  # noqa: E402
MECHS = [k for k in json.load(open(os.path.join(SKILLS, "course-factory", "knowledge", "media-and-tasks.json"),
                                   encoding="utf-8"))["mechanics"] if not k.startswith("_")]
OWN = ("order", "categorise", "match", "cloze", "find_the_fault", "spot_the_error", "build_the_plan", "fill_matrix",
       "panel_operate", "timeline")
SPECIAL = ("multi_select", "hotspot", "spot_the_hazard", "calculate")
gap = [m for m in MECHS if m not in tp.SAY and m not in OWN and m not in SPECIAL and m not in tp.ip.fm.FRAMED]
check("every way of answering in media-and-tasks.json says what to do", not gap, gap)
W = tp.WORDS["en"]
check("a multi-select says how many to tap, from its answer",
      tp.what_to_do({"mechanic": "multi_select", "options": ["a", "b", "c", "d"], "correct": "A, C"}, W) == "Tap the 2 answers that are right.",
      tp.what_to_do({"mechanic": "multi_select", "options": ["a", "b", "c", "d"], "correct": "A, C"}, W))
check("tap the picture with two right places says two",
      "2 right places" in tp.what_to_do({"mechanic": "hotspot", "answer": "Valve A *\nValve B *\nPump"}, W))
check("a single hazard is 'the hazard'", tp.what_to_do({"mechanic": "spot_the_hazard", "answer": "Hose *\nRail"}, W) == W["hazard_1_say"])
calc = {"id": "q09", "mechanic": "calculate", "question": "How much a day?", "answer": "0.15 % vol ± 0.01\n! Meter: 0.006 % vol an hour",
        "feedback": "f"}
check("a calculation says its unit and rounding, from its answer",
      tp.what_to_do(calc, W) == "Work it out from what is on the screen. Give your answer in % vol, to 2 decimal places.", tp.what_to_do(calc, W))
check("... a whole number says so", "as a whole number" in tp.what_to_do(dict(calc, answer="12 t ± 1\n! Gauge: 12 t"), W))
check("a framed task (its own page says it) and a drag task (its own line) get no second line",
      tp.what_to_do({"mechanic": "deck_round"}, W) == "" and tp.what_to_do({"mechanic": "order"}, W) == "")
tmp = tempfile.mkdtemp(prefix="say_")
one = tp.question_html(1, {"id": "q01", "mechanic": "single_choice", "question": "What is LNG mostly?",
                           "options": ["Methane", "Propane"], "correct": "A", "feedback": "f"}, {}, tmp, tmp, {"_bands": set()}, [], W)
check("the line is on the page, straight under the question",
      '</h1>\n    <p class="opts-say">%s</p>' % W["one_say"] in one, one[:400])
lab = tp.question_html(2, calc, {}, tmp, tmp, {"_bands": set()}, [], W)
check("... an interactive one too (work it out)", '<p class="opts-say">Work it out from what is on the screen.' in lab, lab[:400])
check("CSS: the line spans the picture's layouts (tap the picture, label the drawing)",
      '.scr[data-pic="side"]>.opts-say' in CSS and '.scr[data-pic="lab"]>.opts-say{grid-row:2}' in CSS)

# the engine
check("CSS: the lines are shorter once checked", ".checked .doc .opt{min-height:42px" in CSS)
check("CSS: a drawing that is not wide has its cards beside it", '.scr[data-pic="lab"]' in CSS and tp.LAB_SIDE_AR > 1)
check("CSS: the label box stays visible on the Navy screens", ".th-n .ga .lbox.zone{" in CSS)
check("JS: the verdict scroll keeps the heading in sight", "from = hd;" in JS)
check("zoom: the button never goes onto the question line", "qh.getBoundingClientRect()" in ZOOM)

print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
