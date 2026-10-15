#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The person's design choices - where they wanted the look their way after hearing the risk (L26, 2.30.0).

    design_choices.py rules                      the design rules a choice can depart from, with the risk to say
    design_choices.py list  <course>             every choice this course has made
    design_choices.py add   <course> --rule <id> --choice "<what they want>" --said "<their words>" [--risk "<the risk told>"]

WHY THIS EXISTS
The owner, 2026-10-15: "if person who uses plugin somehow tells you that he does not like it, you need to listen to
this, if some of persons ideas conflicts with plugin rules, claude should tell person about this risk, but still after
person reviews and tells that he wants his way, plugin listens to that." Before this, the factory did what was asked -
and then the next build or fix ran a check, the check called the person's wish a FAIL, and the wish was quietly
"repaired" back. A choice written here is read by every check that enforces that rule, which then reports the place
as the person's choice and never as a problem.

ONLY DESIGN. The rules a choice can depart from are listed in knowledge/design-rules.json - how a course looks and
behaves on the screen. The course material keeps its own rules (programme, Main ILOs, hours, sources, approved words).

WHERE IT LIVES
In the course's working_claude/STANDARDS.md (L50), the file every new module is built to, as a standard with a tag:

    S7 No recap slide - the module check follows the last teaching slide (2026-10-15, operator: "I don't want it"). [departs from: recap; risk told: the modules end differently]

So one file says both what the person wants everywhere and where that departs from the factory. A choice is removed
only by the person (delete its line).

Standard library only.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import workspace  # noqa: E402

SKILL = os.path.dirname(HERE)
RULES = json.load(io.open(os.path.join(SKILL, "knowledge", "design-rules.json"), encoding="utf-8"))["rules"]
FILE = "STANDARDS.md"
STANDARDS_HEAD = """# Course standards - what the operator decided once for every module

Every module is built to these, and every fix keeps them. Newest last. Written by `fix.py standard`;
the operator's own words in quotes. A standard is never silently dropped - the operator removes it.
A standard tagged [departs from: ...] is the operator's design choice against a factory rule, made after
hearing the risk (L26): every check reports it as their choice, and nothing changes it back.

"""
LINE = re.compile(r'^S(\d+) (.*?) \((\d{4}-\d\d-\d\d)(?:, operator: "(.*)")?\)(?: \[departs from: ([\w-]+)(?:; risk told: (.*))?\])?\s*$')


def path(course):
    return workspace.claude_path(course, FILE)


def work_of(folder):
    """The work folder (course\\) for any folder a check is given: the master folder, course\\, course\\modules\\ or
    one module inside it."""
    g = os.path.abspath(folder)
    for up in (g, os.path.dirname(g), os.path.dirname(os.path.dirname(g))):
        if os.path.basename(up).lower() == workspace.MODULES.lower():
            return os.path.dirname(up)
        if workspace.is_master(up) or os.path.isdir(os.path.join(up, workspace.CLAUDE)):
            return workspace.work_folder(up, create=False)
    return g


def standards(course):
    p = path(course)
    out = []
    if not os.path.isfile(p):
        return out
    for line in io.open(p, encoding="utf-8").read().splitlines():
        m = LINE.match(line.strip())
        if m:
            out.append({"n": int(m.group(1)), "text": m.group(2), "date": m.group(3), "said": m.group(4) or "",
                        "rule": m.group(5) or "", "risk": m.group(6) or ""})
    return out


def load(folder):
    """{rule id: the latest choice that departs from it} for the course a folder belongs to."""
    out = {}
    for s in standards(work_of(folder)):
        if s["rule"]:
            out[s["rule"]] = s
    return out


def label(choice):
    return "the operator's choice S%d (%s%s)" % (choice["n"], choice["date"], (', "%s"' % choice["said"]) if choice["said"] else "")


def split(problems, choices, rule, match):
    """Move the problems a choice covers into notes. match(problem) says whether a problem is about `rule`."""
    if rule not in choices:
        return problems, []
    keep, waived = [], []
    for p in problems:
        (waived if match(p) else keep).append(p)
    return keep, ["%s - %s" % (p, label(choices[rule])) for p in waived]


def add(course, rule, choice, said, risk=""):
    if rule not in RULES:
        raise ValueError("%r is not a design rule - one of: %s" % (rule, ", ".join(sorted(RULES))))
    p = path(course)
    text = io.open(p, encoding="utf-8").read() if os.path.isfile(p) else STANDARDS_HEAD
    n = max([int(x) for x in re.findall(r"^S(\d+) ", text, re.M)] or [0]) + 1     # never reuse a removed number
    clean = lambda s: re.sub(r"\s+", " ", (s or "").replace('"', "'").replace("]", ")")).strip()
    tag = " [departs from: %s%s]" % (rule, ("; risk told: %s" % clean(risk)) if risk else "")
    text = text.rstrip("\n") + "\n\nS%d %s (%s%s)%s\n" % (n, clean(choice), date.today().isoformat(),
                                                         (', operator: "%s"' % clean(said)) if said else "", tag)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rules")
    s = sub.add_parser("list"); s.add_argument("course")
    s = sub.add_parser("add"); s.add_argument("course"); s.add_argument("--rule", required=True)
    s.add_argument("--choice", required=True); s.add_argument("--said", required=True); s.add_argument("--risk", default="")
    a = ap.parse_args(argv)
    if a.cmd == "rules":
        for k, r in RULES.items():
            print("%-15s %s (%s)\n%15s risk to say: %s" % (k, r["says"], r["law"], "", r["risk"]))
        return 0
    course = workspace.work_folder(a.course, create=False)
    if a.cmd == "list":
        mine = [s for s in standards(course) if s["rule"]]
        if not mine:
            print("This course has no design choices - it follows the factory's design everywhere.")
        for s in mine:
            print("S%d  %s\n     against: %s - %s\n     said %s: \"%s\"%s" % (s["n"], s["text"], s["rule"], RULES.get(s["rule"], {}).get("says", "?"),
                                                                       s["date"], s["said"], ("\n     risk told: " + s["risk"]) if s["risk"] else ""))
        return 0
    try:
        n = add(course, a.rule, a.choice, a.said, a.risk)
    except ValueError as e:
        print("Stopped - %s" % e)
        return 2
    print("Choice S%d written to %s - every check now reports it as the operator's choice, and nothing changes it back." % (n, path(course)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
