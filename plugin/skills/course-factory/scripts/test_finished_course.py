# -*- coding: utf-8 -*-
"""test_finished_course - L72: a finished course goes into Course Libraries\\Finished courses\\<name>\\.

    python test_finished_course.py

A small built course is invented (two modules, additional materials). Pinned:
  * trainee\\ gets the deck, handout, self-checks, module check, day sheets, project-pack trainee files, pre-brief cards;
  * trainee\\ never gets instructor plans, answer keys, START_HERE pages, debrief cards, task cards, the ACP,
    assessment forms, model files, the materials index or the course shell;
  * complete\\ gets every delivered file; to_review\\ and working_claude\\ are never copied; audit snapshots are dropped;
  * a second run replaces trainee\\ and complete\\ (a file gone from the course is gone from the copy);
  * an answer key that slips past the rules stops the run before anything is written.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import finished_course as fc  # noqa: E402

TRAINEE = [
    "modules/module01/presentation/index.html", "modules/module01/handout/index.html",
    "modules/module01/tasks/sc1.html", "modules/module01/assessment/check.html", "modules/module01/assets/img/a.webp",
    "additional-materials/day-sheets/Day_1.pdf", "additional-materials/project-pack/trainee/Project brief D1.html",
    "additional-materials/practical-kit/Day_1/M01_S19_PREBRIEF.pdf",
    "additional-materials/simulator-and-equipment/Day_2/M02_W03_TRAINEE.pdf",
]
INSTRUCTOR = [
    "modules/module01/instructor/M01_PLAN.html", "modules/module01/assessment/check_answer_key.html",
    "modules/module01/START_HERE.html", "modules/module01/START_HERE_EXTENDED.html", "modules/COURSE.html",
    "modules/_course_shell/advanced_course_plan.html", "modules/classroom/prepare.json",
    "additional-materials/practical-kit/Day_1/M01_S19_DEBRIEF.pdf", "additional-materials/practical-tasks/pdf/M01_SC1.pdf",
    "additional-materials/acp/ACP.html", "additional-materials/practical-kit/Day_5/FINAL_A04_ASSESSMENT.pdf",
    "additional-materials/project-pack/instructor/Model file D1.xlsx", "additional-materials/INDEX.html",
    "additional-materials/practical_pack_LINKS.md", "additional-materials/practical-kit/EMPLOYER_SHEET.pdf",
    "additional-materials/simulator-and-equipment/Day_2/M02_W03_INSTRUCTOR.pdf",
]
NEVER = ["modules/module02/presentation/_audit_1_1040x863.html", "to_review/M01_SCRIPT.docx",
         "working_claude/COURSE_STATE.md"]


def make(root, files):
    for f in files:
        p = os.path.join(root, *f.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("x")


def listing(root):
    out = set()
    for r, _, fs in os.walk(root):
        for f in fs:
            out.add(os.path.relpath(os.path.join(r, f), root).replace("\\", "/"))
    return out


def main():
    tmp = tempfile.mkdtemp()
    fails = []
    try:
        course, libs = os.path.join(tmp, "Demo course", "course"), os.path.join(tmp, "libs")
        os.makedirs(libs)
        make(course, TRAINEE + INSTRUCTOR + NEVER)
        r = fc.run(course, "Demo", libs, False)
        dest = os.path.join(libs, fc.FINISHED, "Demo")
        tr, co = listing(os.path.join(dest, "trainee")), listing(os.path.join(dest, "complete"))
        if tr != set(TRAINEE):
            fails.append(f"trainee/ wrong: extra {sorted(tr - set(TRAINEE))}, missing {sorted(set(TRAINEE) - tr)}")
        if co != set(TRAINEE + INSTRUCTOR):
            fails.append(f"complete/ wrong: {sorted(co ^ set(TRAINEE + INSTRUCTOR))}")
        if not os.path.isfile(os.path.join(dest, "00_READ_ME.md")):
            fails.append("no 00_READ_ME.md")
        if (r["trainee"], r["complete"]) != (len(TRAINEE), len(TRAINEE + INSTRUCTOR)):
            fails.append(f"counts {r}")
        os.remove(os.path.join(course, "modules", "module01", "handout", "index.html"))
        fc.run(course, "Demo", libs, False)
        if "modules/module01/handout/index.html" in listing(os.path.join(dest, "trainee")):
            fails.append("a second run kept a file that is gone from the course")
        make(course, ["modules/module01/presentation/answer_key.html"])     # the deck's folder is kept whole
        before = listing(dest)
        try:
            fc.run(course, "Demo", libs, False)
            fails.append("a review page in trainee/ did not stop the run")
        except SystemExit:
            if listing(dest) != before:
                fails.append("the stopped run wrote files")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("FAIL", f)
    print("test_finished_course:", "FAIL" if fails else "ok")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
