# -*- coding: utf-8 -*-
"""test_task_pages_walk - the task-page fixes of the IT course walk review (2.138.0), pinned without a browser.

    python test_task_pages_walk.py

  * the group picker's wrapper is .grp-picks - it was ".grp", the class of a sort group, so every sort group took the
    picker's margin:auto and shrank to a sliver (M03 q03 / check m04);
  * a card that said "5 Server" for a drawing whose numbers are hidden says "Server" (its key is made from what it says);
  * five steps to put in order have their bank beside them; four do not;
  * order / sort / match say to drag (M02 q04, check m02);
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

# the engine
check("CSS: the lines are shorter once checked", ".checked .doc .opt{min-height:42px" in CSS)
check("CSS: a drawing that is not wide has its cards beside it", '.scr[data-pic="lab"]' in CSS and tp.LAB_SIDE_AR > 1)
check("CSS: the label box stays visible on the Navy screens", ".th-n .ga .lbox.zone{" in CSS)
check("JS: the verdict scroll keeps the heading in sight", "from = hd;" in JS)
check("zoom: the button never goes onto the question line", "qh.getBoundingClientRect()" in ZOOM)

print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
