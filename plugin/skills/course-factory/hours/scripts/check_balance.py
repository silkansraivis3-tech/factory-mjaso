#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The two-track balance gate: what the programme allocated, and how it is delivered.

Why this exists
---------------
The ETPB3 pilot read "80/20 practical" as one number and tried to satisfy it by
counting screens. Two different things were being confused, and confusing them
produces either a false pass or a false failure:

  TRACK A  ALLOCATION.  The approved programme says 12 academic hours theory and
           20 practice. That is a fixed, external, auditable fact. It is never
           edited to make a build look better. What this script checks is that
           the module as BUILT claims those same minutes against those same
           buckets - that a module claiming 20 practice hours actually puts
           800 minutes of trainee practice in front of the room.

           ETPB3 failed this and nothing caught it: it built 650 minutes of
           theory delivery against an allocated 480, under-delivering practice
           by 170 minutes, while check_hours.py passed because the TOTAL was
           right. A total-only check cannot see a bucket swap.

  TRACK B  MODALITY.  Of the minutes in front of the room, how many have the
           trainee doing, deciding, producing or saying something, and how many
           have them receiving? This is a DESIGN metric, not a compliance one.
           It has no effect on Track A: a theory-allocated minute delivered as
           an activity is still a theory minute. It is simply the difference
           between a theory hour that teaches and one that is talked at.

The 80 % target belongs to Track B. Track A is whatever the programme says.

Markup contract
---------------
On the screen that carries `data-mins` (the first screen of a block):

    data-track   "theory" | "practice"   which allocation bucket these minutes
                                         are claimed against. Required.
    data-active  integer minutes         of this block's minutes, how many are
                                         learner-active. Required. 0 is a legal
                                         and sometimes honest answer.

`data-active` is a declaration, not a measurement, and it is checked against
the things that would make it a lie:

  * it may not exceed data-mins
  * a practice block declaring less than half its minutes active is flagged -
    if trainees are receiving for most of a practical, it is not a practical
  * a theory block declaring 100 % active is flagged - somebody has to set the
    task, and a block that never pauses to do so is a rename, not a redesign
  * the instructor plan must show, for each block, what the trainees do in
    those minutes. That part a human checks; this script cannot.

Usage
-----
    check_balance.py <module.html> --theory-min 480 --practice-min 800
    check_balance.py <course_dir> --programme _work/programme.json
    check_balance.py <module.html> --programme p.json --target-active 0.8

Exit code 1 on a Track A mismatch or any Track B defect. Track B shortfall
against the target is reported, not failed - the programme can make 80 %
unreachable, and the rule then is that it is recorded, not faked.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SLIDE = re.compile(r"<section[^>]*\bclass=[\"'][^\"']*\bslide\b[^\"']*[\"'][^>]*>", re.I)
PRACTICE_KINDS = {"practical", "practical-run", "task", "activity-launch", "assessment",
                  "drill", "check", "marking"}
THEORY_KINDS = {"theory", "teaching", "opener", "summary", "debrief", "hand-off"}


def attr(tag, name):
    m = re.search(name + r"=[\"']([^\"']*)[\"']", tag)
    return m.group(1) if m else ""


def read_blocks(path):
    """Every screen that carries data-mins, i.e. every timetable block."""
    html = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for tag in SLIDE.findall(html):
        mins = attr(tag, "data-mins")
        if not mins:
            continue
        out.append({
            "block": attr(tag, "data-block") or "?",
            "kind": attr(tag, "data-kind") or "?",
            "title": attr(tag, "data-title") or "",
            "mins": int(mins),
            "track": attr(tag, "data-track"),
            "active": attr(tag, "data-active"),
        })
    return out


def allocation_from_programme(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    h = d.get("academic_hour_min", 40)
    t = d["total_row"]
    return t["theory"] * h, t["practical"] * h


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a module.html, or a folder containing one")
    ap.add_argument("--programme", help="programme.json, to read the allocation from")
    ap.add_argument("--theory-min", type=int, help="allocated theory minutes")
    ap.add_argument("--practice-min", type=int, help="allocated practice minutes")
    ap.add_argument("--target-active", type=float, default=0.8,
                    help="Track B target, default 0.80")
    args = ap.parse_args()

    p = Path(args.target)
    if p.is_dir():
        cands = sorted(p.glob("module.html")) or sorted(p.rglob("module.html"))
        if not cands:
            print("No module.html under %s" % p)
            return 1
        p = cands[0]

    blocks = read_blocks(p)
    if not blocks:
        print("No screens with data-mins in %s" % p)
        return 1

    alloc_t = alloc_p = None
    if args.programme:
        base = Path(args.programme)
        if not base.is_absolute() and not base.exists():
            base = p.parent / args.programme
        alloc_t, alloc_p = allocation_from_programme(base)
    if args.theory_min is not None:
        alloc_t = args.theory_min
    if args.practice_min is not None:
        alloc_p = args.practice_min

    failures, warnings = [], []

    # ---- markup completeness ------------------------------------------------
    for b in blocks:
        if b["track"] not in ("theory", "practice"):
            failures.append("%s %s - data-track missing or not theory|practice (%r)"
                            % (b["block"], b["title"][:38], b["track"]))
        if not b["active"].isdigit():
            failures.append("%s %s - data-active missing or not a number (%r)"
                            % (b["block"], b["title"][:38], b["active"]))
    if failures:
        print("=" * 72)
        print("check_balance - allocation and delivery modality")
        print("=" * 72)
        for f in failures:
            print("  FAIL  %s" % f)
        print("\nEvery block needs data-track and data-active. See the docstring.")
        return 1

    for b in blocks:
        b["active"] = int(b["active"])

    # ---- TRACK A ------------------------------------------------------------
    built_t = sum(b["mins"] for b in blocks if b["track"] == "theory")
    built_p = sum(b["mins"] for b in blocks if b["track"] == "practice")
    total = built_t + built_p

    print("=" * 72)
    print("check_balance - %s" % p)
    print("=" * 72)
    print("\nTRACK A - allocation (the programme's, not ours)")
    if alloc_t is None:
        print("   no allocation given; reporting the build only")
        print("   built   theory %4d min   practice %4d min   total %4d min"
              % (built_t, built_p, total))
    else:
        print("   allocated   theory %4d min   practice %4d min   total %4d min"
              % (alloc_t, alloc_p, alloc_t + alloc_p))
        print("   built       theory %4d min   practice %4d min   total %4d min"
              % (built_t, built_p, total))
        if built_t != alloc_t or built_p != alloc_p:
            failures.append(
                "the build does not deliver the allocation: theory %+d min, practice %+d min. "
                "The allocation is the programme's and is not editable; the BUILD moves."
                % (built_t - alloc_t, built_p - alloc_p))

    # a kind that contradicts its declared track is how a bucket swap hides
    for b in blocks:
        if b["track"] == "practice" and b["kind"] in THEORY_KINDS:
            warnings.append("%s claims the practice allocation with kind=%s - say what the "
                            "trainees physically do, or move it back to theory"
                            % (b["block"], b["kind"]))
        if b["track"] == "theory" and b["kind"] in PRACTICE_KINDS:
            warnings.append("%s claims the theory allocation with kind=%s - probably a "
                            "mis-set data-track" % (b["block"], b["kind"]))

    # ---- TRACK B ------------------------------------------------------------
    act = sum(b["active"] for b in blocks)
    ratio = act / total if total else 0
    print("\nTRACK B - delivery modality (a design metric; changes nothing in Track A)")
    print("   learner-active %4d min of %d   = %.0f%%   (target %.0f%%)"
          % (act, total, 100 * ratio, 100 * args.target_active))
    act_t = sum(b["active"] for b in blocks if b["track"] == "theory")
    act_p = sum(b["active"] for b in blocks if b["track"] == "practice")
    if built_t:
        print("     within theory    %4d of %4d = %.0f%%" % (act_t, built_t, 100 * act_t / built_t))
    if built_p:
        print("     within practice  %4d of %4d = %.0f%%" % (act_p, built_p, 100 * act_p / built_p))

    for b in blocks:
        if b["active"] > b["mins"]:
            failures.append("%s declares %d active minutes in a %d minute block"
                            % (b["block"], b["active"], b["mins"]))
        elif b["track"] == "practice" and b["active"] * 2 < b["mins"]:
            failures.append("%s is a practice block with %d of %d minutes active - "
                            "if the room is receiving for most of it, it is not practice"
                            % (b["block"], b["active"], b["mins"]))
        elif b["track"] == "theory" and b["active"] == b["mins"] and b["mins"] > 10:
            failures.append("%s declares 100%% of a %d minute theory block active - somebody "
                            "sets the task. A rename is not a redesign." % (b["block"], b["mins"]))
        elif b["track"] == "theory" and b["active"] == 0 and b["mins"] >= 20:
            warnings.append("%s - %d theory minutes with nothing for the trainee to do. "
                            "Allowed, but it is the defect the active-learning rule names."
                            % (b["block"], b["mins"]))

    # ---- report -------------------------------------------------------------
    print()
    for f in failures:
        print("  FAIL  %s" % f)
    for w in warnings:
        print("  warn  %s" % w)
    if not failures and not warnings:
        print("  the build delivers the allocation, and every block says what the room does")

    if not failures and ratio < args.target_active:
        print("\n  Track B is %.0f%%, below the %.0f%% target. That is a report, not a failure:"
              % (100 * ratio, 100 * args.target_active))
        print("  the programme can make it unreachable. Record the figure and the reason in")
        print("  factory-notes.md. Do not reach it by renaming screens.")

    print("\n%d block(s) - %d failure(s), %d warning(s)" % (len(blocks), len(failures), len(warnings)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
