#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Accredited-hours gate. Exits non-zero when the minutes do not add up.

Why this exists: GAS BASIC was built to 2175 minutes of class time against an
accredited 1640, and nobody knew until all eight modules existed, because
nothing counted. `COURSE_START.json` - the contract that orders the whole
course factory - has no hours field at all. This script is the counting.

Usage
-----
    check_hours.py --spec COURSE_START.json
    check_hours.py --programme programme.json --plan plan.json

`--spec` reads the additive `hours` block this skill writes into
COURSE_START.json. `--programme` / `--plan` is for before that block exists.

Input shapes
------------
programme.json
    {
      "source": "Program Basic Training Gas Rev. 01",
      "academic_hour_min": 40,
      "days": 4, "slots_per_day": 11,
      "topics": { "1": {"theory": 2, "practical": 0}, ... },
      "total_row": {"theory": 35, "practical": 8, "total": 43}
    }

plan.json
    {
      "outside_modules": [{"topic": "23", "hours": 2, "why": "final assessment"}],
      "modules": [{"module": 1, "topics": ["1","2"], "built_min": 215}, ...]
    }

Checks, in order
----------------
1  the transcribed topic table reconciles with the programme's own total row
2  every topic is either claimed by a module or declared outside the modules
3  per module: built minutes == allocated minutes, exactly
4  the whole course fits days x slots_per_day x slot_min
5  practical ratio reported; below target is not fatal but must be recorded

Exit codes: 0 all checks pass · 1 a check failed · 2 bad input
"""
import argparse
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TARGET_PRACTICAL_RATIO = 0.80


def die(msg, code=2):
    print("INPUT ERROR: %s" % msg)
    sys.exit(code)


def load(p):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception as e:
        die("cannot read %s (%s)" % (p, e))


def from_spec(spec):
    h = spec.get("hours")
    if not h:
        die("COURSE_START.json has no `hours` block. Write it first - shape is in "
            "hours/knowledge/hours-rules.json. This is the field the contract lacks.")
    prog = {
        "source": h.get("programme", {}).get("source", "UNKNOWN"),
        "academic_hour_min": h.get("academic_hour_min"),
        "days": h.get("days"),
        "delivery_days": h.get("delivery_days"),
        "slots_per_day": h.get("slots_per_day"),
        "topics": h.get("topics", {}),
        "total_row": {
            "theory": h.get("programme", {}).get("theory_h"),
            "practical": h.get("programme", {}).get("practical_h"),
            "total": h.get("programme", {}).get("total_h"),
        },
    }
    plan = {"outside_modules": h.get("outside_modules", []),
            "modules": h.get("modules", [])}
    return prog, plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec")
    ap.add_argument("--programme")
    ap.add_argument("--plan")
    a = ap.parse_args()

    if a.spec:
        prog, plan = from_spec(load(a.spec))
    elif a.programme and a.plan:
        prog, plan = load(a.programme), load(a.plan)
    else:
        die("give --spec, or both --programme and --plan")

    ah = prog.get("academic_hour_min")
    if not ah:
        die("academic_hour_min is missing. Read it from the programme - it is NOT "
            "necessarily 60. Do not guess; every number below is a multiple of it.")
    print("academic hour = %d min   (source: %s)" % (ah, prog.get("source", "UNKNOWN")))

    fails = []

    # ---- 1 - does the transcription reconcile with the programme's own total? ----
    topics = prog.get("topics") or {}
    if not topics:
        die("no topics transcribed from the programme")
    th = sum(float(v.get("theory", 0) or 0) for v in topics.values())
    pr = sum(float(v.get("practical", 0) or 0) for v in topics.values())
    row = prog.get("total_row") or {}
    print("\n1 · transcription")
    print("    transcribed: %.2f theory + %.2f practical = %.2f h" % (th, pr, th + pr))
    if row.get("theory") is None:
        print("    programme total row: NOT GIVEN  ->  cannot reconcile [VERIFY: copy the "
              "table's own Total row into total_row]")
        fails.append("transcription unreconciled - no total_row supplied")
    else:
        print("    programme says:      %.2f theory + %.2f practical = %.2f h"
              % (float(row["theory"]), float(row["practical"]), float(row["total"])))
        if abs(th - float(row["theory"])) > 0.01 or abs(pr - float(row["practical"])) > 0.01:
            print("    MISMATCH - the transcription is wrong, not the table.")
            fails.append("transcription does not match the programme's total row")
        else:
            print("    reconciles  OK")

    # ---- 2 - every topic accounted for ----
    claimed, dupes = {}, []
    for m in plan.get("modules", []):
        for t in m.get("topics", []):
            t = str(t)
            if t in claimed:
                dupes.append((t, claimed[t], m.get("module")))
            claimed[t] = m.get("module")
    outside = {str(o.get("topic")): o for o in plan.get("outside_modules", [])}
    unaccounted = [t for t in topics if t not in claimed and t not in outside]
    print("\n2 · coverage")
    print("    %d topic(s) in %d module(s); %d declared outside the modules"
          % (len(claimed), len(plan.get("modules", [])), len(outside)))
    for t, o in sorted(outside.items()):
        print("      outside: topic %-4s %.2f h  - %s" % (t, float(o.get("hours", 0)), o.get("why", "no reason given")))
    if dupes:
        for t, a1, b1 in dupes:
            print("    TOPIC %s claimed by module %s AND module %s" % (t, a1, b1))
        fails.append("a topic is claimed by more than one module")
    if unaccounted:
        print("    UNACCOUNTED: %s" % unaccounted)
        fails.append("topics neither in a module nor declared outside: %s" % unaccounted)
    if not dupes and not unaccounted:
        print("    every topic accounted for  OK")

    # ---- 3 - the budget, per module ----
    print("\n3 · budget   (built must EQUAL allocated - tolerance is zero by design)")
    print("    %-4s %-16s %10s %10s %9s" % ("mod", "topics", "alloc_min", "built_min", "diff"))
    tot_alloc = tot_built = tot_pract = 0
    for m in sorted(plan.get("modules", []), key=lambda x: x.get("module", 0)):
        ts = [str(t) for t in m.get("topics", [])]
        alloc_h = sum(float(topics.get(t, {}).get("theory", 0) or 0)
                      + float(topics.get(t, {}).get("practical", 0) or 0) for t in ts)
        pract_h = sum(float(topics.get(t, {}).get("practical", 0) or 0) for t in ts)
        alloc = int(round(alloc_h * ah))
        built = m.get("built_min")
        tot_alloc += alloc
        tot_pract += int(round(pract_h * ah))
        flag = ""
        if built is None:
            flag = "  built_min MISSING"
            fails.append("module %s has no built_min" % m.get("module"))
            built_s, diff_s = "-", "-"
        else:
            tot_built += built
            d = built - alloc
            built_s, diff_s = str(built), "%+d" % d
            if d != 0:
                flag = "  OVER" if d > 0 else "  UNDER"
                fails.append("module %s is %+d min against its allocation"
                             % (m.get("module"), d))
        print("    %-4s %-16s %10d %10s %9s%s"
              % (m.get("module"), ",".join(ts)[:16], alloc, built_s, diff_s, flag))
    print("    %-4s %-16s %10d %10d %+9d" % ("TOT", "", tot_alloc, tot_built, tot_built - tot_alloc))
    if tot_built != tot_alloc:
        print("    -> %+d min = %+.2f academic hours. Move the excess to the handout as "
              "self-study; class time is fixed." % (tot_built - tot_alloc,
                                                    (tot_built - tot_alloc) / float(ah)))

    # ---- 4 - does it fit the accredited days? ----
    print("\n4 · the day shape")
    days, spd = prog.get("days"), prog.get("slots_per_day")
    if not days or not spd:
        print("    days/slots_per_day not given - cannot check the timetable "
              "[VERIFY: read the programme's own timetable]")
    else:
        cap = days * spd * ah
        outside_min = int(round(sum(float(o.get("hours", 0)) for o in outside.values()) * ah))
        need_alloc = tot_alloc + outside_min
        need_built = tot_built + outside_min
        print("    accredited    %d min (%d days x %d slots x %d min)" % (cap, days, spd, ah))
        print("    as accredited %d min" % need_alloc)
        print("    as built      %d min" % need_built)
        if need_alloc > cap:
            print("    the ACCREDITED hours do not fit their own timetable - report to the owner")
            fails.append("the accredited %d min exceeds the timetable's %d min" % (need_alloc, cap))

        # The days a school actually sells may differ from the days the programme was
        # accredited with. `days` is a transcription and is never edited to make this
        # pass; delivery_days is a decision, and if it is larger the accreditor should
        # be told the timetable run is not the one described.
        ddays = prog.get("delivery_days")
        if ddays and ddays != days:
            dcap = ddays * spd * ah
            print("    delivered as  %d days = %d min capacity" % (ddays, dcap))
            if ddays > days:
                print("    NOTE the course is delivered over more days than the programme's "
                      "own timetable describes - tell the accreditor [VERIFY]")
            if need_built > dcap:
                over_days = (need_built - dcap) / float(spd * ah)
                print("    IT DOES NOT FIT EVEN THE DELIVERED DAYS - about %.1f more"
                      % over_days)
                fails.append("as built the course needs %d min but %d delivered days hold %d"
                             % (need_built, ddays, dcap))
            else:
                print("    fits the delivered days, %d min spare  OK" % (dcap - need_built))
        elif need_built > cap:
            over_days = (need_built - cap) / float(spd * ah)
            print("    AS BUILT IT DOES NOT FIT - about %.1f extra day(s) of teaching" % over_days)
            fails.append("as built the course needs %d min but the accredited days hold %d"
                         % (need_built, cap))
        elif need_alloc <= cap:
            print("    fits, %d min spare  OK" % (cap - need_built))

    # ---- 5 - the ratio ----
    print("\n5 · practical ratio")
    if tot_alloc:
        r = tot_pract / float(tot_alloc)
        print("    %d of %d allocated min are practical = %.1f %%" % (tot_pract, tot_alloc, r * 100))
        if r + 1e-9 < TARGET_PRACTICAL_RATIO:
            print("    below the %.0f %% target. NOT a failure - but the theory hours MUST"
                  % (TARGET_PRACTICAL_RATIO * 100))
            print("    be delivered as active learning (a trainee activity inside the theory")
            print("    block), and the achieved ratio must be recorded in the companion file.")
    else:
        print("    no allocation to measure")

    # ---- verdict ----
    print("\n" + "=" * 72)
    if fails:
        print("%d PROBLEM(S) - the plan is not 1:1 with the programme" % len(fails))
        for f in fails:
            print("   - %s" % f)
        sys.exit(1)
    print("minutes are 1:1 with the accredited programme")
    sys.exit(0)


if __name__ == "__main__":
    main()
