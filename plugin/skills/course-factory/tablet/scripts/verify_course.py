#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Structural gate for a built course: shape, counts, and the ordering rules.

Checks that need no browser and no hit-testing, so they are trustworthy
anywhere:

1  every module deck's slide openings all close, and no section holds MORE
   than one .slide-body
2  the module check is second-to-last and the hand-off is last
3  the last module ends the course; every other hand-off can leave the module
4  every "N screens" claim in the deck, its entry page and its plan agrees
   with the real screen count
5  no .bak / editor-state files inside the shipped tree

Check 1 exists because tag counts and div balance both PASSED on a deck where a
.slide-body had been duplicated into the wrong section - two bodies in one
slide, and the screens either side were destroyed. Counting bodies per section
is what catches it. Note AT MOST, not exactly: a photo screen uses .photo-wrap,
an activity launch .act-wrap, a module check .ck-wrap. Zero is a different
idiom; two is the bug.

Check 4 exists because a deck that says "20 screens" after growing to 22 lies
to the instructor reading it. It is ADVISORY, never fatal - the phrasing varies
per course and a range sentence ("over two screens") reads like a size claim.
Read the advisories; do not let them block a build.

Usage
-----
    verify_course.py --deck 1=path/to/m1.html --deck 2=... [--claims-in <glob> ...]
    verify_course.py --decks-json decks.json [--claims-in "course/Module_*/START_HERE.html"]

Exit codes: 0 clean · 1 problems · 2 bad input
"""
import argparse
import glob
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
        "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        "twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
        "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27}
# A DECK-SIZE claim, not any sentence containing a number and "screens".
# `(\d+)\s+screens?` matched "the next five screens are the description" - a
# range - and produced 13 wrong claims on a course whose counts were correct.
# These are the phrasings that really do state a deck's size.
NUM = re.compile(
    r"\b(?:is|are|of)?\s*(\d+|" + "|".join(WORD) + r")\s+screens?"
    r"(?=\s*(?:$|[.,;:]|for\b|in total\b|long\b|the last\b|&mdash;|-|\u2014))",
    re.I)


def die(m):
    print("INPUT ERROR: %s" % m)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", action="append", default=[])
    ap.add_argument("--decks-json")
    ap.add_argument("--claims-in", action="append", default=[],
                    help="glob of files that may state a screen count")
    ap.add_argument("--last-module", type=int)
    ap.add_argument("--day-mode", action="append", default=[], type=int,
                    help="module number whose hand-off is a day step, not a slide "
                         "(a simulator-day deck). Repeatable.")
    a = ap.parse_args()

    decks = {}
    if a.decks_json:
        for k, v in json.loads(pathlib.Path(a.decks_json).read_text(encoding="utf-8")).items():
            decks[int(k)] = pathlib.Path(v)
    for d in a.deck:
        if "=" not in d:
            die("--deck wants N=path")
        k, v = d.split("=", 1)
        decks[int(re.sub(r"\D", "", k))] = pathlib.Path(v)
    if not decks:
        die("give --deck or --decks-json")
    last_mod = a.last_module or max(decks)

    problems = []
    advisories = []
    sizes = {}
    print("%-5s %-8s %-22s %-22s %s" % ("mod", "screens", "structure", "order", "chain"))
    print("-" * 96)

    for n in sorted(decks):
        p = decks[n]
        if not p.exists():
            problems.append("M%d: deck not found (%s)" % (n, p))
            print("%-5d DECK MISSING %s" % (n, p))
            continue
        s = p.read_text(encoding="utf-8", errors="replace")

        opens = [m.start() for m in re.finditer(r'<section class="slide', s)]
        # </section> also closes any other <section> in the file - a simulator
        # day deck has sdstep sections - so count the closings that actually
        # terminate a SLIDE, not every closing in the document.
        closes = sum(1 for at in opens if s.find("</section>", at) > 0)
        all_sections = len(re.findall(r"<section\b", s))
        sizes[n] = len(opens)

        # ---- 1 structure: one .slide-body per section, divs balanced
        struct = []
        for i, at in enumerate(opens, 1):
            end = s.find("</section>", at)
            seg = s[at:end if end > 0 else len(s)]
            nb = seg.count('class="slide-body')
            o, c = len(re.findall(r"<div\b", seg)), seg.count("</div>")
            # AT MOST one. A photo screen uses .photo-wrap, a launch .act-wrap,
            # a check .ck-wrap - zero is a different idiom, not a defect. TWO
            # is the bug that destroyed two screens while every tag count and
            # div balance still passed.
            if nb > 1:
                struct.append("s%d has %d .slide-body" % (i, nb))
                problems.append("M%d screen %d has %d .slide-body - a duplicated body, "
                                "which destroys the screens either side" % (n, i, nb))
            if o != c:
                struct.append("s%d divs %d/%d" % (i, o, c))
                problems.append("M%d screen %d div imbalance %d/%d" % (n, i, o, c))
        st_txt = "ok" if not struct else "; ".join(struct[:2])

        # ---- 2 order: check second-to-last, hand-off last
        kinds = [(re.search(r'data-kind="([^"]*)"', s[at:s.index(">", at) + 1]) or ["", ""])[1].lower()
                 for at in opens]
        ho_last = bool(kinds) and kinds[-1].startswith("hand-off")
        chk_2nd = len(kinds) > 1 and "check" in kinds[-2]
        if n in a.day_mode:
            order = "day-mode (declared)"
        elif ho_last and chk_2nd:
            order = "check->handoff ok"
        elif ho_last:
            order = "handoff last, no check before"
        else:
            order = "NO HAND-OFF LAST"
            problems.append("M%d: the last screen is not the hand-off (kind=%r). If this is a "
                            "simulator-day deck whose hand-off is a day step, declare it with "
                            "--day-mode %d" % (n, kinds[-1] if kinds else None, n))

        # ---- 3 chain
        has_go = 'id="chainGo"' in s
        tgt = bool(re.search(r'data-next-module="[^"]+"', s))
        if n == last_mod:
            chain = "ends course" if not (has_go or tgt) else "SHOULD NOT LINK ONWARD"
            if has_go or tgt:
                problems.append("M%d is the last module and still links onward" % n)
        else:
            chain = "ok" if (has_go and tgt) else "cannot leave the module"
            if not (has_go and tgt):
                problems.append("M%d: hand-off cannot leave the module (button=%s target=%s)"
                                % (n, has_go, tgt))

        print("%-5d %-8d %-22s %-22s %s" % (n, len(opens), st_txt[:22], order[:22], chain))
        if closes != len(opens):
            problems.append("M%d: %d slide opening(s) but only %d close" % (n, len(opens), closes))
        if all_sections != len(opens):
            print("      note: %d other <section> element(s) in this file (day steps, panels)"
                  % (all_sections - len(opens)))

    # ---- 4 count claims
    print("\nscreen-count claims")
    files = []
    for g in a.claims_in:
        files.extend(pathlib.Path(x) for x in glob.glob(g))
    files.extend(decks.values())
    for f in sorted(set(files)):
        if not f.exists():
            continue
        # which module does this file belong to?
        mm = re.search(r"(?:Module_|module_|m)(\d{1,2})", str(f))
        if not mm:
            continue
        n = int(mm.group(1))
        if n not in sizes:
            continue
        plain = re.sub(r"<[^>]+>", " ", f.read_text(encoding="utf-8", errors="replace"))
        for m in NUM.finditer(plain):
            tok = m.group(1).lower()
            v = int(tok) if tok.isdigit() else WORD.get(tok)
            if v is None or v == sizes[n]:
                continue
            ctx = re.sub(r"\s+", " ", plain[max(0, m.start() - 70):m.end() + 40])
            # a range or a per-item count is not a deck-size claim
            if re.search(r"screens?\s+\d+\s*(?:to|-|–|and)\s*\d+", ctx, re.I) \
               or "screens each" in ctx.lower():
                continue
            print("   ADVISORY  M%-3d %-30s says %-4d (real: %d)"
                  % (n, f.name[:30], v, sizes[n]))
            print("             ...%s" % ctx[:104])
            advisories.append("M%d: %s may claim %d screens, deck has %d"
                              % (n, f.name, v, sizes[n]))
    if not advisories:
        print("   no disagreement found")
    else:
        print("   %d advisory item(s) - READ THEM, but they are not failures: the phrasing"
              % len(advisories))
        print("   varies per course and a range sentence reads like a size claim.")

    # ---- 5 stray files beside the decks
    print("\nstray files in the shipped tree")
    stray = []
    for p in set(d.parent for d in decks.values()):
        for x in p.rglob("*"):
            if x.is_file() and re.search(r"\.bak|\.orig|~$|\.swp$", x.name):
                stray.append(x)
    if stray:
        for x in stray[:8]:
            print("   %s" % x)
        print("   %d file(s) - fine in a working tree, NEVER inside a shipped asset root" % len(stray))
    else:
        print("   none")

    print("\n" + "=" * 96)
    if problems:
        print("%d PROBLEM(S)" % len(problems))
        for x in problems:
            print("   - %s" % x)
        sys.exit(1)
    print("every module is structurally sound and its counts agree")
    sys.exit(0)


if __name__ == "__main__":
    main()
