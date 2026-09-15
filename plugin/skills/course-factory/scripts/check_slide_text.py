#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""What a course-facing page may SAY: internal shorthand, version control, and what
may be cited as a source.

    check_slide_text.py <course_dir_or_file>
    check_slide_text.py <course_dir> --strict      exit 1 on any failure
    check_slide_text.py <course_dir> --json

WHY THIS EXISTS
A maritime subject-matter reviewer read a finished module and returned four rules.
None of them is about one course; each is about the difference between a document
the Training Centre keeps for itself and a page a trainee reads.

  1 · INTERNAL SHORTHAND.  A Training Centre abbreviation on a slide implies it is
      an IMO title or an industry term. It is neither. Write the course out in full.

  2 · INTERNAL VERSION CONTROL.  "Revision 3", "Approved programme", an internal
      authority designation. A title slide is the first thing a room sees, and it
      should look like training material rather than a version-control record.

  3 · WHAT MAY BE CITED AS A SOURCE.  An IMO model course is a training REQUIREMENT
      and a guideline for what a course must cover. It is not a source of factual
      information. A slide saying "Source: IMO Model Course 1.01" tells the room
      that a syllabus is where a fact came from. Cite the publication the fact
      actually came from, or cite nothing.

  4 · FIGURES TOO.  "Figure: IMO Model Course 1.01, 1.2" is the same error wearing
      a caption. Do not credit a model course for a drawing.

And one the factory added to itself: its own honesty markers (PLACEHOLDER,
PROVISIONAL, [VERIFY: ...]) are a message to the OWNER. They belong in
factory-notes.md, which already exists for exactly that, and never on a screen in
front of a class.

WHERE THE RULES BITE
On the PRESENTATION - the deck, tasks, handout, assessment, practicals: everything a
trainee sees. On an INSTRUCTOR-ONLY page - a module plan, a run sheet, an analysis -
citing a training requirement is legitimate and useful, so it is reported as a note
and never as a failure. `knowledge/slide-text-rules.json` decides which is which;
edit that file, not this script.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(os.path.dirname(HERE), "knowledge", "slide-text-rules.json")

FAIL, WARN, NOTE = "FAIL", "WARN", "NOTE"

SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)
TAGS = re.compile(r"<[^>]+>")
SLIDE = re.compile(r'<section[^>]*class="[^"]*\bslide\b[^"]*"[^>]*>.*?</section>', re.S | re.I)
CUE = re.compile(r'data-(?:cue|title|foot)="([^"]*)"')


class Finding:
    def __init__(self, rule, level, path, line, detail, fix=""):
        self.rule, self.level, self.path = rule, level, path
        self.line, self.detail, self.fix = line, detail, fix

    def __str__(self):
        where = "%s:%d" % (self.path, self.line) if self.line else self.path
        s = "  [%s] %s: %s - %s" % (self.level, self.rule, where, self.detail)
        if self.fix:
            s += "\n          use instead: " + self.fix
        return s

    def as_dict(self):
        return {"rule": self.rule, "level": self.level, "path": self.path,
                "line": self.line, "detail": self.detail, "fix": self.fix}


def load_rules(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _blank(m):
    """Erase a region but KEEP its newlines, so every reported line number still
    matches the file on disk.

    Stripping markup naively shifts every line below it. The first version of this
    file did that and sent a reviewer to an SVG polygon while claiming a citation was
    there. A checker that points at the wrong line costs the same trust as one that
    misses the defect."""
    return "\n" * m.group(0).count("\n")


def _detag(m):
    """A tag becomes whitespace - except the attributes a person HEARS.

    An instructor cue is read aloud in the room, so an internal abbreviation in one
    reaches the trainees just as surely as one printed on the slide. It is kept in
    place rather than appended, so it is reported where it actually lives."""
    tag = m.group(0)
    keep = " ".join(CUE.findall(tag))
    return keep + "\n" * tag.count("\n")


def visible_text(raw):
    """What a person reads or hears, with the file's own line numbers intact."""
    t = COMMENT.sub(_blank, raw)
    t = SCRIPT_STYLE.sub(_blank, t)
    t = TAGS.sub(_detag, t)
    return t


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


# Every occurrence, not just the first. The reviewer's instruction was to check
# the slides already built and remove these "if they appear anywhere" - a checker
# that names one of four does not let anyone finish the job. Capped so one runaway
# file cannot bury the rest of the report.
MAX_PER_RULE_PER_FILE = 6


def each(rx, text, claimed=None):
    """Matches, capped - and never the same words twice.

    Two patterns in the same rule legitimately overlap: "IMO Model Course" and
    "Model Course 1.04" are both true of the same seven words. Reporting both turned
    24 real citations into 47 findings on GAS BASIC, and a reviewer sent to chase 47
    sites finds 24 and stops trusting the count. `claimed` is the character span
    already reported for this rule in this file; an overlap is the same finding.
    """
    n = 0
    for m in rx.finditer(text):
        if claimed is not None:
            if any(m.start() < e and s < m.end() for s, e in claimed):
                continue
            claimed.append((m.start(), m.end()))
        n += 1
        if n > MAX_PER_RULE_PER_FILE:
            break
        yield m


def classify(rel, surfaces):
    """presentation | instructor | skip"""
    r = rel.replace("\\", "/")
    low = r.lower()
    if any(x.lower() in low for x in surfaces["not_course_facing"]):
        return "skip"
    # instructor-only wins: a plan inside a course folder is still a plan
    if any(x.lower() in low for x in surfaces["instructor_only"]):
        return "instructor"
    if any(x.lower() in low for x in surfaces["presentation"]):
        return "presentation"
    return "skip"


def opening_slide_span(raw):
    """(start, end) of the FIRST slide, where version control fails hardest."""
    m = SLIDE.search(raw)
    return (m.start(), m.end()) if m else (None, None)


def scan_file(path, rel, kind, rules, out):
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    text = visible_text(raw)
    first_s, first_e = opening_slide_span(raw)
    opening = visible_text(raw[first_s:first_e]) if first_s is not None else ""

    presentation = kind == "presentation"

    # ---- 1 · internal shorthand -------------------------------------------
    claimed_abbrev = []
    for t in rules["internal_abbreviations"]["terms"]:
        rx = re.compile(r"\b" + re.escape(t["term"]) + r"\b", re.I)
        for m in each(rx, text, claimed_abbrev):
            out.append(Finding(
                "abbrev", FAIL if presentation else NOTE, rel, line_of(text, m.start()),
                '"%s" is %s' % (t["term"], t["why"]),
                t["instead"] if presentation else ""))

    # ---- 2 · what may be cited as a source --------------------------------
    claimed_source = []
    for p in rules["never_cite_as_source"]["patterns"]:
        rx = re.compile(p["pattern"], re.I)
        for m in each(rx, text, claimed_source):
            out.append(Finding(
                "source", FAIL if presentation else NOTE, rel, line_of(text, m.start()),
                "%s is cited on a course-facing page - %s. Cite the publication the "
                "fact came from, or cite nothing." % (p["label"], p["why"])
                if presentation else
                "%s is referred to here. On an instructor page that is legitimate "
                "guidance; it must not appear on a slide." % p["label"]))

    # ---- 3 · internal version control -------------------------------------
    if presentation:
        claimed_version = []
        for p in rules["no_version_control_on_slides"]["patterns"]:
            rx = re.compile(p["pattern"], re.I)
            m = rx.search(opening)
            if m:
                out.append(Finding(
                    "version", FAIL, rel, 0,
                    "the OPENING slide carries %s. A title slide should look like "
                    "training material, not a version-control record." % p["label"]))
                continue
            if p.get("title_only"):
                # legitimate prose elsewhere - see _title_only_note in the rules
                continue
            for m in each(rx, text, claimed_version):
                out.append(Finding(
                    "version", WARN, rel, line_of(text, m.start()),
                    "%s appears on a course-facing page. Approval and revision belong "
                    "in the course plan and factory-notes.md." % p["label"]))

    # ---- 4 · the factory's own markers ------------------------------------
    claimed_marker = []
    for p in rules["honesty_markers"]["patterns"]:
        rx = re.compile(p["pattern"])
        for m in each(rx, text, claimed_marker):
            out.append(Finding(
                "markers", FAIL if presentation else WARN, rel, line_of(text, m.start()),
                "%s is on a course-facing page. Markers are a message to the owner and "
                "belong in factory-notes.md." % p["label"]))


def walk(target):
    if os.path.isfile(target):
        # Classify a single file by its PATH, not its basename: "tasks/T1.html" is a
        # trainee page and "T1.html" is nothing at all. Pointing the checker at one
        # page must give the same verdict as pointing it at the folder above.
        yield target, os.path.abspath(target).replace("\\", "/")
        return
    for dp, dn, fn in os.walk(target):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "node_modules")]
        for f in fn:
            if os.path.splitext(f)[1].lower() in (".html", ".htm"):
                p = os.path.join(dp, f)
                yield p, os.path.relpath(p, target)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="a course folder, or one page")
    ap.add_argument("--rules", default=RULES)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on any FAIL (default: report and exit 0)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.exists(a.target):
        sys.stderr.write("no such path: %s\n" % a.target)
        return 2
    rules = load_rules(a.rules)

    out: list[Finding] = []
    seen = {"presentation": 0, "instructor": 0, "skip": 0}
    for path, rel in walk(a.target):
        kind = classify(rel, rules["surfaces"])
        seen[kind] += 1
        if kind == "skip":
            continue
        scan_file(path, rel.replace("\\", "/"), kind, rules, out)

    if a.json:
        print(json.dumps({"findings": [f.as_dict() for f in out],
                          "counts": seen}, indent=1, ensure_ascii=False))
        return 1 if (a.strict and any(f.level == FAIL for f in out)) else 0

    print("=" * 72)
    print("check_slide_text - what a course-facing page may say")
    print("=" * 72)
    print("%d presentation page(s), %d instructor page(s), %d skipped"
          % (seen["presentation"], seen["instructor"], seen["skip"]))

    fails = [f for f in out if f.level == FAIL]
    warns = [f for f in out if f.level == WARN]
    notes = [f for f in out if f.level == NOTE]
    for group, name in ((fails, "FAIL"), (warns, "WARN"), (notes, "NOTE")):
        if group:
            print("\n%s (%d):" % (name, len(group)))
            for f in group:
                print(str(f))

    print()
    if not out:
        print("Nothing internal, nothing mis-cited. Every source on a slide is a "
              "publication,\nnot a syllabus.")
    else:
        print("%d failure(s), %d warning(s), %d note(s)."
              % (len(fails), len(warns), len(notes)))
        if notes and not fails and not warns:
            print("Notes are instructor-only pages, where this is legitimate guidance.")
    return 1 if (a.strict and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
