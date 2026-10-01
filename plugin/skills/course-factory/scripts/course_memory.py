#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The course's memory - L32. Where it stands, what the operator corrected, what a later course may learn.

    course_memory.py start    <course folder> --title "<course>"
    course_memory.py check    <course folder>
    course_memory.py draft-pattern   <course folder>
    course_memory.py approve-pattern <course folder> --by "<operator's name>"
    course_memory.py patterns [--course-type NEW_ENTRANT|EXPERIENCED] [--also <folder>]

WHY THIS EXISTS
A course is made over days and several sessions. Without a written state, each new session
re-reads everything and asks again what was already settled - the operator answers the same
question twice and stops trusting the tool. Without a log of corrections, the factory repeats the
mistake the operator already fixed. Without patterns, the next course starts from nothing.

  start            writes COURSE_STATE.md and FEEDBACK_LOG.md into the course folder from the
                   templates - only if they are not there yet; it never overwrites.
  check            says whether COURSE_STATE.md is complete enough for a new session to resume
                   from: every section present, a stage named, a next step written, a date.
  draft-pattern    writes COURSE_PATTERN_<course>.draft.md, pre-filled with the course, course type
                   and the corrections from FEEDBACK_LOG.md, for the factory to finish and SHOW the
                   operator in plain language. A draft is never used by a later course.
  approve-pattern  only after the operator has read it and said so: fills "Approved by" with their
                   name and the date, and saves it as COURSE_PATTERN_<course>.md. Refuses while the
                   course, course type or "Made by" is empty.
  patterns         lists the APPROVED pattern files a new course may read - the factory's own
                   (resources/course-patterns/, shipped with the plugin) and any in --also - with
                   course, type, subject and who made it, so the factory can judge which fit.
                   Patterns are guidance, never rules, never above the operator's request.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TEMPLATES = os.path.join(SKILL, "templates")
PLUGIN = os.path.dirname(os.path.dirname(SKILL))
LIBRARY = os.path.join(PLUGIN, "resources", "course-patterns")

STATE_SECTIONS = ["## Now", "## The six stages", "## The course", "## Decided", "## Open questions", "## File map"]
STAGES = ["1 Intake", "2 Architecture", "3 Content script", "4 Pilot Module 1", "5 Remaining modules",
          "6 Final assessment and handover"]


def rd(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def wr(p, s):
    with io.open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def plugin_version():
    try:
        return json.loads(rd(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"))).get("version", "")
    except (OSError, ValueError):
        return ""


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:60] or "course"


def field(text, name):
    m = re.search(r"^\|\s*\*\*%s\*\*\s*\|\s*(.*?)\s*\|\s*$" % re.escape(name), text, re.M)
    v = m.group(1).strip() if m else ""
    return "" if (not v or v.startswith("<")) else v


# ------------------------------------------------------------------ start / check
def cmd_start(course, title):
    if not os.path.isdir(course):
        print("Stopped - that folder does not exist:\n    %s" % course)
        return 2
    made = []
    for name in ("COURSE_STATE.md", "FEEDBACK_LOG.md"):
        p = os.path.join(course, name)
        if os.path.exists(p):
            continue
        s = rd(os.path.join(TEMPLATES, name)).replace("<COURSE>", title)
        s = s.replace("<YYYY-MM-DD>", date.today().isoformat(), 1).replace("<version>", plugin_version(), 1)
        wr(p, s)
        made.append(name)
    print(("Started %s in\n    %s" % (" and ".join(made), course)) if made else
          "Both files were already there and were left exactly as they are:\n    %s" % course)
    return 0


def cmd_check(course):
    p = os.path.join(course, "COURSE_STATE.md")
    if not os.path.isfile(p):
        print("There is no COURSE_STATE.md in\n    %s\n  so a new session would have to start from nothing.\n"
              "  What to do: tell me to start it and I will (course_memory.py start)." % course)
        return 1
    s = rd(p)
    problems = [("the section \"%s\" is missing" % h[3:]) for h in STATE_SECTIONS if h not in s]
    m = re.search(r"\*\*Stage:\*\*\s*(.+)", s)
    stage = (m.group(1).strip() if m else "")
    if not stage or stage.startswith("<") or not any(stage.startswith(x.split()[0]) for x in STAGES):
        problems.append("the current stage is not named (\"Stage:\" under \"Now\")")
    m = re.search(r"\*\*Next step:\*\*\s*(.+)", s)
    if not m or m.group(1).strip().startswith("<"):
        problems.append("there is no next step written under \"Now\"")
    m = re.search(r"\*\*Last updated\*\*\s*(\d{4}-\d{2}-\d{2})", s)
    if not m:
        problems.append("there is no \"Last updated\" date")
    if not os.path.isfile(os.path.join(course, "FEEDBACK_LOG.md")):
        problems.append("FEEDBACK_LOG.md is missing - corrections have nowhere to go")
    if problems:
        print("COURSE_STATE.md is not yet enough for a new session to pick up from:\n    %s\n" % p)
        for x in problems:
            print("    - " + x)
        print("\n  What to do: the factory fills these in at the end of the stage it is on. Tell me to do it\n"
              "  and I will. You will see the stage, what was decided and what comes next at the top of the file.")
        return 1
    print("COURSE_STATE.md is complete: a new session can resume from it.\n    %s\n  Stage: %s" % (p, stage))
    return 0


# ------------------------------------------------------------------ patterns
def cmd_draft(course):
    sp, fp = os.path.join(course, "COURSE_STATE.md"), os.path.join(course, "FEEDBACK_LOG.md")
    if not os.path.isfile(sp):
        print("Stopped - there is no COURSE_STATE.md yet, so the course and its type are unknown.")
        return 2
    s = rd(sp)
    get = lambda label: (re.search(r"^\|\s*%s\s*\|\s*(.*?)\s*\|" % re.escape(label), s, re.M) or [None, ""])[1]
    title = get("Course")
    ctype = get("Course type")
    corrections = []
    if os.path.isfile(fp):
        for line in rd(fp).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 5 and cells[0].isdigit() and cells[3]:
                corrections.append("- \"%s\" → %s  *(%s)*" % (cells[3], cells[4] or "—", cells[2] or "—"))
    t = rd(os.path.join(TEMPLATES, "COURSE_PATTERN.md"))
    t = t.replace("<COURSE>", title or "<COURSE>", 1)
    t = t.replace("| **Course** | <the course's title, as in the approved programme> |", "| **Course** | %s |" % (title or "<the course's title, as in the approved programme>"))
    if ctype and not ctype.startswith("<"):
        t = t.replace("| **Course type** | <NEW_ENTRANT / EXPERIENCED> |", "| **Course type** | %s |" % ctype)
    t = t.replace("| **Factory version** | <version> |", "| **Factory version** | %s |" % plugin_version())
    if corrections:
        t = t.replace("## What they changed, and why\n", "## What they changed, and why\n\n*All %d corrections from FEEDBACK_LOG.md, for the factory "
                      "to sort: keep the ones that say how a course should be made, drop the one-off fixes.*\n\n%s\n"
                      % (len(corrections), "\n".join(corrections)), 1)
    out = os.path.join(course, "COURSE_PATTERN_%s.draft.md" % slug(title or os.path.basename(os.path.abspath(course))))
    wr(out, t)
    print("A draft pattern is ready, not yet saved as a pattern:\n    %s\n  Next: the factory finishes it and shows it to "
          "the operator in plain language. They may change or remove any point. Only their approval makes it a pattern."
          % out)
    return 0


def cmd_approve(course, by):
    drafts = glob.glob(os.path.join(course, "COURSE_PATTERN_*.draft.md"))
    if not drafts:
        print("Stopped - there is no draft pattern in\n    %s\n  Make one first (course_memory.py draft-pattern)." % course)
        return 2
    if not by.strip():
        print("Stopped - the approval needs the name of the person approving it.")
        return 2
    d = drafts[0]
    t = rd(d)
    missing = [n for n in ("Course", "Course type", "Made by") if not field(t, n)]
    if missing:
        print("Not saved - the pattern must say %s, so a later course can judge whether it fits. Fill in:\n    %s"
              % (", ".join(missing), "\n    ".join(missing)))
        return 1
    t = re.sub(r"^\|\s*\*\*Approved by\*\*\s*\|.*\|\s*$", "| **Approved by** | %s on %s |" % (by.strip(), date.today().isoformat()),
               t, count=1, flags=re.M)
    final = d.replace(".draft.md", ".md")
    wr(final, t)
    os.remove(d)
    print("Saved, approved by %s:\n    %s\n  A later course reads it as guidance once it is in the factory's pattern folder "
          "(plugin/resources/course-patterns/) - the owner copies it there, commits and pushes, and every colleague "
          "gets it with the next update." % (by.strip(), final))
    return 0


def read_pattern(p):
    t = rd(p)
    return {"file": p, "course": field(t, "Course"), "course_type": field(t, "Course type"),
            "subject": field(t, "Subject area"), "made_by": field(t, "Made by"), "approved": field(t, "Approved by")}


def cmd_patterns(ctype, also):
    files = glob.glob(os.path.join(LIBRARY, "COURSE_PATTERN_*.md")) + sum((glob.glob(os.path.join(a, "COURSE_PATTERN_*.md")) for a in also), [])
    usable, skipped = [], []
    for f in sorted(set(files)):
        if f.endswith(".draft.md"):
            skipped.append((f, "a draft - never approved"))
            continue
        r = read_pattern(f)
        if not r["approved"]:
            skipped.append((f, "no approval written in it"))
            continue
        usable.append(r)
    if not usable:
        print("No approved course patterns yet. That is fine - the course is made from its own sources.")
    else:
        print("Approved course patterns - GUIDANCE for this course, never rules, never above the operator's request:\n")
        for r in usable:
            fit = "" if not ctype else ("  <- same course type" if r["course_type"] == ctype else "  (a different course type)")
            print("  - %s · %s · %s · made by %s%s\n      %s" % (r["course"], r["course_type"], r["subject"] or "subject not given",
                                                              r["made_by"], fit, r["file"]))
    for f, why in skipped:
        print("  (not used: %s - %s)" % (os.path.basename(f), why))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("start"); a.add_argument("course"); a.add_argument("--title", required=True)
    b = sub.add_parser("check"); b.add_argument("course")
    c = sub.add_parser("draft-pattern"); c.add_argument("course")
    d = sub.add_parser("approve-pattern"); d.add_argument("course"); d.add_argument("--by", required=True)
    e = sub.add_parser("patterns"); e.add_argument("--course-type", default=""); e.add_argument("--also", action="append", default=[])
    n = ap.parse_args(argv)
    if getattr(n, "course", None):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import workspace
        n.course = workspace.work_folder(n.course)    # course\ beside the operator's material (L40)
    return {"start": lambda: cmd_start(n.course, n.title), "check": lambda: cmd_check(n.course),
            "draft-pattern": lambda: cmd_draft(n.course), "approve-pattern": lambda: cmd_approve(n.course, n.by),
            "patterns": lambda: cmd_patterns(n.course_type, n.also)}[n.cmd]()


if __name__ == "__main__":
    sys.exit(main())
