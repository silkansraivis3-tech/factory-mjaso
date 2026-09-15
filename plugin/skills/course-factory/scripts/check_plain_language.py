#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""L25 - can the person this was written for actually act on it?

    check_plain_language.py <file-or-folder> [--strict] [--json]

WHY THIS EXISTS
The person who reads what this factory produces is a maritime professional with no IT
background. A line reading

    FAIL check_visual_first.py module.html:412 missing lead figure

is not a report to them, it is a wall. They cannot act on it, so they either ignore it
or come and ask - and both of those are the factory failing to finish its own job. A
finding nobody can act on is the same as a finding nobody made.

WHAT IT CHECKS
Three things, all of them mechanical:

  1 JARGON WITH NO PLAIN WORDS BESIDE IT.  "stylesheet", "commit", "repository",
    "exit code". Each is fine once the sentence has said what it means; bare, it stops
    the reader. The plain form for each is in knowledge/plain-language.json.

  2 A PATH NOBODY CAN FIND.  "module.html:412" or "./modules/m4/" tells a person
    nothing. A path starts at the drive letter, or it is not a path to them.

  3 A PROBLEM WITH NO WAY OUT.  A section that names something wrong and never says
    what to do about it. This is the one that actually costs a course.

WHAT IT CANNOT CHECK
Whether the explanation is any good. That is read by a person, and the five parts in
the rules file are what they are reading for.

`knowledge/plain-language.json` is the authority. Edit that file, not this script.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(os.path.dirname(HERE), "knowledge", "plain-language.json")

FAIL, WARN = "FAIL", "WARN"

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
HTML_TAG = re.compile(r"<[^>]+>")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)

# A path a person can find starts at a drive letter (C:\... or C:/...).
FULL_PATH = re.compile(r"[A-Za-z]:[\\/]")
# A path a person cannot find: a bare file:line, or a relative folder reference.
BARE_REF = re.compile(
    r"(?<![\w./\\:])(?:\./|\.\./)?(?:[\w-]+/)*[\w-]+\.(?:html?|css|js|json|py|md)"
    r"(?::\d+)?(?![\w/\\])")

# Something is wrong here, and here is what happens next.
#
# Both vocabularies live in the rules file, not here. Each one started in this script
# and each one was too narrow: the next-step list had no "find", no "finish" and no
# "fix", so the checker complained about a handoff page that said "find a real
# photograph" - text that was already perfectly actionable. Widening a list has to be
# an edit, not a code change, or nobody widens it.
PROBLEM = REMEDY = None  # built from the rules file in main()


def vocab(words):
    """Longest first, so "could not" is matched before "not found" can claim part of it."""
    return re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(
        re.escape(w) for w in sorted(words, key=len, reverse=True)), re.I)


class Finding:
    def __init__(self, level, path, line, what, fix):
        self.level, self.path, self.line, self.what, self.fix = level, path, line, what, fix

    def __str__(self):
        return "  [%s] %s:%d\n        %s\n        %s" % (
            self.level, self.path, self.line, self.what, self.fix)

    def as_dict(self):
        return {"level": self.level, "path": self.path, "line": self.line,
                "what": self.what, "fix": self.fix}


def load_rules():
    with open(RULES, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _blank(m):
    """Keep the newlines so every reported line is the line in the file."""
    return "\n" * m.group(0).count("\n")


def readable(raw):
    """What a person reads. Code blocks are exempt - a command IS technical, and the
    rule is about the sentences around it, not the command itself."""
    t = FENCE.sub(_blank, raw)
    t = HTML_COMMENT.sub(_blank, t)
    t = HTML_TAG.sub(" ", t)
    t = INLINE.sub(lambda m: " " * len(m.group(0)), t)
    return t


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def near(text, pos, before=160, after=160):
    return text[max(0, pos - before):pos + after]


def scan(path, rel, rules, out):
    raw = open(path, encoding="utf-8", errors="replace").read()
    text = readable(raw)

    # ---- 1 · jargon with no plain words beside it -------------------------
    seen = set()
    for t in rules["never_say_without_explaining"]["terms"]:
        term = t["term"]
        rx = re.compile(r"\b" + re.escape(term) + r"\b", re.I if term.islower() else 0)
        for m in rx.finditer(text):
            key = term.lower()
            if key in seen:
                break
            # Explained if the plain wording, or a bracketed gloss, is right beside it.
            window = near(text, m.start()).lower()
            plain_words = [w for w in re.findall(r"[a-z]{4,}", t["plain"].lower())][:4]
            glossed = ("(" in window and ")" in window) or \
                      sum(w in window for w in plain_words) >= 2
            if glossed:
                break
            seen.add(key)
            out.append(Finding(
                FAIL, rel, line_of(text, m.start()),
                'the word "%s" is used with nothing beside it saying what it means.' % term,
                'Write it as: %s (%s).' % (t["plain"], term)))
            break

    # ---- 2 · a path nobody can find ---------------------------------------
    said = set()
    for m in BARE_REF.finditer(text):
        ref = m.group(0)
        if ref in said or FULL_PATH.search(near(text, m.start(), 90, 20)):
            continue
        said.add(ref)
        out.append(Finding(
            WARN, rel, line_of(text, m.start()),
            '"%s" is not a place a person can find.' % ref,
            "Give the whole path from the drive letter - C:\\Users\\...\\%s - and say "
            "what opens it." % ref.split("/")[-1]))
        if len(said) >= 6:
            break

    # ---- 3 · a problem with no way out ------------------------------------
    # Paragraph by paragraph: if it says something is wrong and never says what to do,
    # the reader is left holding it.
    pos = 0
    for para in text.split("\n\n"):
        start, pos = pos, pos + len(para) + 2
        if len(para.strip()) < 40 or para.lstrip().startswith(("|", "#")):
            continue
        if PROBLEM.search(para) and not REMEDY.search(para):
            out.append(Finding(
                FAIL, rel, line_of(text, start),
                "this says something is wrong and never says what to do about it.",
                "Add the four missing parts: where it is (full path), how to open it, "
                "what to change, and what they will see when it is right. If the factory "
                "can fix it, offer to."))


def walk(target, rules):
    facing = [x.lower() for x in rules["surfaces"]["operator_facing"]]
    if os.path.isfile(target):
        yield target, os.path.basename(target)
        return
    for dp, dn, fn in os.walk(target):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".git", "node_modules")]
        for f in fn:
            if any(x in f.lower() for x in facing):
                p = os.path.join(dp, f)
                yield p, os.path.relpath(p, target).replace("\\", "/")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("target", help="a report or notes file, or a course folder")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any FAIL")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.exists(a.target):
        sys.stderr.write("no such path: %s\n" % a.target)
        return 2
    rules = load_rules()
    global PROBLEM, REMEDY
    w = rules["a_problem_with_no_way_out"]
    PROBLEM = vocab(w["something_is_wrong"])
    REMEDY = vocab(w["and_here_is_what_happens_next"])

    out: list[Finding] = []
    n = 0
    for path, rel in walk(a.target, rules):
        n += 1
        scan(path, rel, rules, out)

    if a.json:
        print(json.dumps({"files": n, "findings": [f.as_dict() for f in out]},
                         indent=1, ensure_ascii=False))
        return 1 if (a.strict and any(f.level == FAIL for f in out)) else 0

    print("=" * 72)
    print("check_plain_language - can the person this was written for act on it?")
    print("=" * 72)
    print("%d operator-facing file(s)" % n)

    fails = [f for f in out if f.level == FAIL]
    warns = [f for f in out if f.level == WARN]
    for g, name in ((fails, "STOPS THE READER"), (warns, "HARD TO FIND")):
        if g:
            print("\n%s (%d):" % (name, len(g)))
            for f in g:
                print(str(f))

    print()
    if not out:
        print("Nothing here needs an IT background to act on.")
    else:
        print("%d that stop the reader, %d that are hard to find.\n" % (len(fails), len(warns)))
        print("The person reading this does not work in IT. Every problem needs five things:\n"
              "what is wrong, where it is, how to open it, what to do, and how they will\n"
              "know it worked. Most fixes belong to the factory - offer to do them.")
    return 1 if (a.strict and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
