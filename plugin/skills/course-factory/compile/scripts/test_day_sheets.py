# -*- coding: utf-8 -*-
"""test_day_sheets - every instructor-led course gets its day sheets and the course on one page, from its own scripts.

    python test_day_sheets.py

Pinned (course lead Aigars Kluga, 2026-11-12):
  * the course build writes additional-materials\\day-sheets\\: one sheet per day of course.build.json "days" (HTML, PDF,
    Word) and the course on one page; INDEX.html links them;
  * "Today, in this order" follows the scripts: the course's opening slides = Course start, a run of teaching slides and
    self-checks = one Theory row, each activity a row, the module check a row; a project block's briefing slides and the
    recap make no row; NO clock time and NO break or lunch row anywhere;
  * with no day_sheets.json each activity is a task and its own lines are the requirements;
  * day_sheets.json: a task lands on the day of the activity that names "Task N" (or its "at"), with its "where" in the
    row; "rows" replaces a row in the course lead's words ([] drops it); sections and "@" lines; an unplaced task is said;
  * the one-page overview: lecture and practical hours per day from the scripts' minutes, the order of the work.
"""
from __future__ import annotations

import copy
import io
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_additional_materials as tam  # noqa: E402  - the same fixture course
import test_compile_module as t  # noqa: E402
from test_compile_module import cs, run  # noqa: E402
import additional_materials as am  # noqa: E402
import day_sheets as ds  # noqa: E402

TOOL = os.path.join(HERE, "additional_materials.py")
PASS, FAIL = [], []
CLOCK = re.compile(r"\b\d{1,2}[:.]\d{2}\b|\bbreak\b|\blunch\b", re.I)


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def text(p):
    x = io.open(p, encoding="utf-8").read()
    x = re.sub(r"<style>.*?</style>|<title>.*?</title>|<!--.*?-->", "", x, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", x))


def screens():
    tc, q, mc, m = (copy.deepcopy(x) for x in t.SCREENS[4:8])
    sl = lambda i, title, mins, **k: dict({"id": i, "kind": "slide", "title": title, "minutes": mins, "text": title}, **k)
    m1 = [sl("s01", "Welcome: two days, one bunker plan", 5),
          sl("s02", "Five new spaces", 20, sub_ilo="1.1"), sl("s03", "Spot the space", 20, sub_ilo="1.1", active="scenario"),
          tc, q,
          sl("p1", "Practical block 1", 3),
          {"id": "a01", "kind": "activity", "format": "write-plan", "minutes": 60, "title": "Draw your bunker plan",
           "text": "Task 1: draw the bunker plan alone.\nPairs: agree one plan.", "notes": "- Timing: show 10, work 50."},
          sl("s09", "What to take away", 2, recap=True),
          mc, m]
    m2 = [sl("s01", "Bunkering sequence", 30, sub_ilo="1.1"),
          {"id": "a01", "kind": "activity", "format": "walkthrough", "minutes": 90, "title": "Run the transfer on paper",
           "text": "Tasks 2 and 3: the transfer plan and the checklist.\nA partner checks it.", "notes": "- Timing: work 80, debrief 10."},
          copy.deepcopy(mc), copy.deepcopy(m)]
    return m1, m2


def course(tmp):
    c = tam.course(tmp, days=[[1], [2]])
    sdir = os.path.join(c, "working_claude", "script")
    for n, sc in zip((1, 2), screens()):
        s = cs.load(os.path.join(sdir, "M%02d.json" % n))
        s["screens"] = sc
        s["minutes_allocated"] = sum(cs.minutes(x) for x in sc)
        s["approved_hash"] = cs.content_hash(s)
        cs.save(os.path.join(sdir, "M%02d.json" % n), s)
    return c


DATA = {
    "sheet_name": "Day {n} task sheet - {title}", "where_head": "Where (form)",
    "lines": {"log": "Log: three lines on what you checked."},
    "tasks": [{"n": 1, "name": "Bunker plan", "where": "Form 1", "title": "Task 1 Bunker plan (form 1)",
               "requirements": ["Every valve named.", "@log"]},
              {"n": 2, "name": "Transfer plan", "where": "Form 2", "requirements": ["Rates and quantities."]},
              {"n": 3, "name": "Checklist", "where": "Form 3"},
              {"n": 4, "name": "Debrief", "where": "Form 4"}],
    "rows": {"M01.S01": [["Course start in my own words", "Instructor"]], "M02.A01": [["Transfer, the lead's row", "Forms 2-3"]]},
    "days": {"1": {"title": "Plan the bunkering", "intro": "You plan one bunkering.", "sections": ["rubric"],
                   "before_leave": ["@log"], "lecture": "Spaces, in the lead's words.", "output": "A bunker plan"},
             "2": {"title": "Run it"}},
    "sections": {"rubric": [["h2", "How it is marked"], ["table", ["Item", "Points"], [["Plan", "5"]]]]},
    "one_page": {"order": "Plan  >  Transfer  >  Checklist"},
}


def main():
    tmp = tempfile.mkdtemp(prefix="day_sheets_")
    try:
        # ---- from the scripts alone, through the course build
        c = course(os.path.join(tmp, "one"))
        code, out = run(TOOL, c)
        root = os.path.join(c, am.FOLDER, ds.FOLDER)
        files = sorted(os.listdir(root)) if os.path.isdir(root) else []
        want = ["Day_1_igf_ships.%s" % k for k in ("docx", "html", "pdf")] + ["Day_2_fuel_systems.%s" % k for k in ("docx", "html", "pdf")]
        check("the course build writes a sheet per day of course.build.json \"days\" (HTML, PDF, Word) and the one-page overview",
              all(x in files for x in want) and "Course_on_one_page.html" in files, (code, files, out[-800:]))
        shell = os.path.join(c, "modules", ds.TABLET_DIR)
        tab = sorted(os.listdir(shell)) if os.path.isdir(shell) else []
        check("... and a tablet page of each in modules\\_course_shell\\documents\\day_sheets\\ - the uploaded folder carries "
              "them to both roles", tab == ["Course_on_one_page.html", "Day_1_igf_ships.html", "Day_2_fuel_systems.html"], tab)
        raw = io.open(os.path.join(shell, "Day_1_igf_ships.html"), encoding="utf-8").read() if tab else ""
        check("the tablet page stands alone: gb-standalone, no link, no script, no build note",
              'name="gb-standalone"' in raw and "<a " not in raw and "<script" not in raw and "Never edit it by hand" not in raw, raw[:400])
        check("a day whose title holds an instructor-only word is called Day_N alone (the importer would hide it from trainees)",
              ds.tablet_stem("Day_3_the_safety_brief", 3) == "Day_3" and ds.tablet_stem("Day_2_plan_the_project", 2) == "Day_2_plan_the_project"
              and ds.tablet_stem("Day_1_an_old_course", 1) == "Day_1")          # "...course.html" is the importer's COURSE.html
        index = io.open(os.path.join(c, am.FOLDER, "INDEX.html"), encoding="utf-8").read()
        check("INDEX.html links the day sheets", "day-sheets/Day_1_igf_ships.html" in index and "Course_on_one_page" in index)
        d1 = text(os.path.join(root, "Day_1_igf_ships.html"))
        order = ["Course start: Welcome: two days, one bunker plan", "Theory, IGF ships: Five new spaces - with one class exercise and one self-check",
                 "Draw your bunker plan", "Module check on the tablet (practice, not graded)"]
        at = [d1.find(x) for x in order]
        check("Today, in this order: course start, one theory row, the activity, the module check - in the scripts' order",
              all(a >= 0 for a in at) and at == sorted(at), list(zip(order, at)))
        check("the briefing slide and the recap make no row", "Practical block 1" not in d1 and "What to take away" not in d1, d1[:900])
        check("no clock time, no break, no lunch on any sheet",
              not any(CLOCK.search(text(os.path.join(root, f))) for f in files if f.endswith(".html")))
        check("no day_sheets.json: the activity is the task, its own lines the requirements",
              "| Tasks |" in d1 and "Task 1: draw the bunker plan alone." in d1 and "Before you leave" not in d1, d1[-900:])
        one = text(os.path.join(root, "Course_on_one_page.html"))
        check("the one-page overview: lecture and practical hours per day from the minutes (45 + 3 + 2 + 9 min lecture, 60 practical)",
              "lecture about 1.5 h, practical about 1.5 h" in one and "lecture about 1 h, practical about 2 h" in one, one[:900])

        # ---- with the course's day_sheets.json
        probs = []
        cs.save(ds.path(c), DATA)
        title, prog, mods, days = ds.course_parts(c, probs)
        docs = {stem: blocks for stem, _, blocks in ds.documents(c, title, prog, mods, days, probs)}
        check("day_sheets.json names the sheets", sorted(docs) == ["Course_on_one_page", "Day_1_plan_the_bunkering", "Day_2_run_it"], sorted(docs))
        flat = lambda bl: " ".join(str(x) for b in bl for x in b[1:])
        b1, b2 = flat(docs.get("Day_1_plan_the_bunkering", [])), flat(docs.get("Day_2_run_it", []))
        check("a task lands on the day of the activity that names it, with its where in the row",
              "Task 1 Bunker plan (form 1)" in b1 and "Draw your bunker plan (Task 1 Bunker plan)" in b1 and "Form 1" in b1, b1[:900])
        check("\"Tasks 2 and 3\" places both on day 2", "Task 2 Transfer plan" in b2 and "Task 3 Checklist" in b2, b2[:900])
        check("\"rows\" replaces a row in the lead's words", "Course start in my own words" in b1 and "Transfer, the lead's row" in b2
              and "Run the transfer on paper" not in [r[0] for b in docs["Day_2_run_it"] if b[0] == "table" for r in b[2]])
        check("sections, intro, before you leave and \"@\" lines", "How it is marked" in b1 and "You plan one bunkering." in b1
              and b1.count("Log: three lines on what you checked.") == 2 and "Where (form)" in b1, b1)
        check("a task no activity names is said", any("task 4 is named by no activity" in p for p in probs), probs)
        o = flat(docs["Course_on_one_page"])
        check("the one-page words come from day_sheets.json where it has them", "Plan  >  Transfer  >  Checklist" in o
              and "Spaces, in the lead's words." in o and "A bunker plan" in o and "Task 2 Transfer plan, Task 3 Checklist" in o, o)

        # ---- the preview writes outside the course only
        before = sorted(os.listdir(root))
        code, out = run(os.path.join(HERE, "day_sheets.py"), c, "--out", os.path.join(tmp, "preview"))
        check("the preview writes its HTML to --out and nothing in the course", sorted(os.listdir(root)) == before
              and os.path.isfile(os.path.join(tmp, "preview", "Day_1_plan_the_bunkering.html")), out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
