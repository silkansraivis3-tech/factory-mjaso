# -*- coding: utf-8 -*-
"""finished_course - L72: every finished course goes into the Course Libraries, with all its material.

    python finished_course.py <course folder> [--name "<Course name>"] [--to <Course Libraries folder>] [--dry-run]

Writes <Course Libraries>\\Finished courses\\<Course name>\\ :

    trainee\\      only what a trainee sees or uses - the decks (projected to the class), handouts, self-checks, module
                  checks without their answer keys, day sheets, project pack, pre-brief cards. This is the folder to give
                  to anyone building the trainee side (the trainee app, the LMS) or to a trainee.
    complete\\     everything delivered - modules\\ and additional-materials\\ as built, instructor material included.
    00_READ_ME.md  what is where, and the date and folder it was copied from.

trainee\\ and complete\\ are made again on every run (nothing else in the course's folder is touched). The course's own
to_review\\ and working_claude\\ are never copied. A trainee file that still looks instructor-only (an answer key, a
review page) stops the run before anything is written.

<course folder>: the master folder or its course\\ folder. The Course Libraries folder: --to, else
NOVIKONTAS_COURSE_LIBRARIES, else the factory's default places (course-visuals subject-libraries.json).
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-visuals", "scripts"))
import workspace  # noqa: E402
from check_course_package import INSTRUCTOR_ONLY, DECK_PAGE, INSTRUCTOR_NAMES  # noqa: E402

FINISHED = "Finished courses"
PARTS = ("modules", "additional-materials")
NEVER = re.compile(r"(^|/)(_audit_[^/]*|desktop\.ini|Thumbs\.db|\.DS_Store|__pycache__)(/|$)", re.I)
# modules\: the classroom app's instructor files and the course shell (plans, maps) are not trainee material
MODULES_INSTRUCTOR = re.compile(r"^(classroom|_course_shell)(/|$)|(^|/)START_HERE[^/]*\.html$", re.I)
# additional-materials\: the instructor's cards, plans, forms and keys, by folder and by name
EXTRA_INSTRUCTOR = re.compile(
    r"(^|/)(instructor[^/]*|acp|practical-tasks|classroom)(/|$)|^INDEX\.html$|_LINKS\.md$"
    r"|debrief|instructor|_assessment\.|assessment form|employer[_ ]sheet|answer|model[ _]file|marking|question bank"
    r"|event texts|trainee_folders|project draw", re.I)


def trainee_file(part: str, rel: str) -> bool:
    """True when a file of modules\\ or additional-materials\\ is something a trainee sees or uses."""
    if part == "modules":
        if MODULES_INSTRUCTOR.search(rel):
            return False
        if DECK_PAGE.search(rel):            # the deck is projected to the class
            return True
        if re.search(r"(^|/)presentation/", rel, re.I):
            return True                      # the deck's own files
        return not INSTRUCTOR_ONLY.search(rel)
    return not EXTRA_INSTRUCTOR.search(rel)


def libraries_root(given: str | None) -> str:
    if given:
        return given
    import subject_library                                                    # noqa: E402
    places = subject_library.parents(subject_library.config(), os.environ)
    for p in places:
        if os.path.isdir(p):
            return p
    raise SystemExit("No Course Libraries folder can be reached (Google Drive not mounted?). Give it with --to.")


def plan(work: str):
    """[(part, rel, trainee?)] for every file the course delivers."""
    out = []
    for part in PARTS:
        base = os.path.join(work, part)
        for root, dirs, files in os.walk(base):
            dirs.sort()
            for f in sorted(files):
                rel = os.path.relpath(os.path.join(root, f), base).replace("\\", "/")
                if NEVER.search(rel):
                    continue
                out.append((part, rel, trainee_file(part, rel)))
    return out


def readme(name: str, work: str, items) -> str:
    def tops(trainee_only):
        seen = []
        for part, rel, tr in items:
            if trainee_only and not tr:
                continue
            top = part + "/" + (rel.split("/")[0] + "/" if "/" in rel else rel)
            if top not in seen:
                seen.append(top)
        return "\n".join("- `" + t + "`" for t in seen)
    n_tr = sum(1 for i in items if i[2])
    return (f"# {name} - finished course\n\n"
            f"Copied {datetime.date.today().isoformat()} from `{work}` by the Course Factory (`finished_course.py`, L72).\n"
            "Made again on every run - change the course in its own folder, not here.\n\n"
            f"## trainee/ - what a trainee sees or uses ({n_tr} files)\n\n"
            "Safe to give to a trainee, or to anyone building the trainee side. Decks, handouts, self-checks, module "
            "checks (no answer keys), day sheets, project pack, pre-brief cards. Open an `.html` page in a browser; keep "
            "the folder layout, the pages read their pictures from `assets/`.\n\n" + tops(True) + "\n\n"
            f"## complete/ - everything delivered ({len(items)} files)\n\n"
            "Instructor material included (plans, answer keys, debrief cards, assessment forms, model files). "
            "Never give this folder to trainees.\n\n" + tops(False) + "\n")


def run(course: str, name: str | None, to: str | None, dry: bool) -> dict:
    work = workspace.work_folder(course, create=False)
    if not os.path.isdir(os.path.join(work, "modules")):
        raise SystemExit(f"No modules\\ folder in {work} - is the course built?")
    if not name:
        name = re.sub(r"\s+course$", "", os.path.basename(workspace.master_of(work).rstrip("\\/")), flags=re.I)
    items = plan(work)
    leaks = [p + "/" + r for p, r, tr in items if tr and INSTRUCTOR_NAMES.search(r)]
    if leaks:
        raise SystemExit("Instructor-only files would reach trainee/ - fix the rules first:\n  " + "\n  ".join(leaks))
    dest = os.path.join(libraries_root(to), FINISHED, name)
    result = {"dest": dest, "trainee": sum(1 for i in items if i[2]), "complete": len(items)}
    if dry:
        return result
    for sub in ("trainee", "complete"):
        shutil.rmtree(os.path.join(dest, sub), ignore_errors=True)
    for part, rel, tr in items:
        src = os.path.join(work, part, *rel.split("/"))
        for sub in (("trainee", "complete") if tr else ("complete",)):
            dst = os.path.join(dest, sub, part, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    with open(os.path.join(dest, "00_READ_ME.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(readme(name, work, items))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("course")
    ap.add_argument("--name")
    ap.add_argument("--to")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    r = run(a.course, a.name, a.to, a.dry_run)
    print(("Would copy" if a.dry_run else "Copied") + f" {r['complete']} files ({r['trainee']} for trainees) to {r['dest']}")


if __name__ == "__main__":
    main()
