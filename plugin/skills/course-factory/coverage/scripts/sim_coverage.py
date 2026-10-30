#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simulator coverage (L66) - every model-course item a school simulator can train is trained on it.

    sim_coverage.py needed <course>                   does L66 apply, and which simulators (coverage/knowledge/simulators.json)
    sim_coverage.py init   <course> [--sims LNG,MeOH] start working_claude\\SIM_COVERAGE.json: one empty row per syllabus item
    sim_coverage.py check  <course>                   exit 0: the map is whole; exit 2: what is missing, in plain words

WHY
The advanced courses use the school's physical simulators for their practical tasks as much as possible: every
competence of the IMO model course a simulator can train is covered on one, and a simulator task may be on paper
(printed, laminated) with the instructor grading from the instructor sheet. On IGF Advanced this was first done by
hand: SIM_MAP.md (what each simulator can do, from its manuals, with pages), SIM_COVERAGE.md / .json (332
items of MC 7.14 -> COVERED / PARTLY / GAP / NOT-SIM) and five draft tasks. 18 items were GAP - the simulators can do
them and no exercise did, the biggest one fire. This script makes that a step every advanced course goes through.

WHAT check WANTS (coverage/SIMULATORS.md is the lane)
  - SIM_MAP.md and SIM_COVERAGE.md beside SIM_COVERAGE.json in working_claude\\, the map naming every simulator code;
  - one row per leaf item of the transcribed syllabus (*syllabus*.json, coverage/GUIDE.md §1) - none missing, none twice;
  - a COVERED / PARTLY / GAP row names a simulator of the course, a manual page and sim_use "assess"; COVERED and PARTLY
    name the exercise that does it; NOT-SIM says why and what is done instead;
  - the counts are the rows' counts;
  - every GAP item is in a proposed task, and every task that carries a GAP item has its draft - the Trainee and the
    Instructor form in to_review\\exercises\\sim_drafts\\MNN\\ - so the instructors review a task, not a list;
  - a task says where its minutes come from inside the module: the hours and the ILOs never change for a simulator task.
A PARTLY item no task takes up is a note, not a failure: the review page shows it.

Standard library only.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "..", "scripts")
sys.path.insert(0, SCRIPTS)
import workspace  # noqa: E402
import ilo_map  # noqa: E402

CATALOGUE = os.path.join(HERE, "..", "knowledge", "simulators.json")
VERDICTS = ("COVERED", "PARTLY", "GAP", "NOT-SIM")
ON_SIM = ("COVERED", "PARTLY", "GAP")
PAGE = re.compile(r"\bp\.?\s?\d", re.I)
MODULE = re.compile(r"\bM(\d+)\b")


def _load(p):
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def catalogue():
    return _load(CATALOGUE) or {"simulators": [], "courses": {}}


def _title_text(course):
    """the words that say what the course is: the programme's name and the course title - not its topics"""
    prog, arch = ilo_map.course_files(course)
    prog, arch = prog or {}, arch or {}
    parts = [str(prog.get(k) or "") for k in ("source", "title", "_what")]
    parts.append(str((arch.get("course") or {}).get("title") or ""))
    return " ".join(parts).lower()


def needed(course):
    """{"needed": bool, "why": str, "course_id": str|None, "codes": [...]} - L66 applies to an advanced course and to any
    course whose programme names a simulator; intake.json "simulators" settles the codes, "sim_coverage_declined" (the
    operator's reason) turns it off."""
    cat = catalogue()
    intake = _load(workspace.claude_path(course, "intake.json")) or {}
    prog, _ = ilo_map.course_files(course)
    whole = json.dumps(prog or {}, ensure_ascii=False).lower()
    title = _title_text(course)
    cid = None
    for k, v in (cat.get("courses") or {}).items():
        if any(w.lower() in title for w in v.get("match", [])):
            cid = k
            break
    if cid is None:
        for k, v in (cat.get("courses") or {}).items():
            if any(w.lower() in whole for w in v.get("match", [])):
                cid = k
                break
    codes = list(intake.get("simulators") or ((cat.get("courses") or {}).get(cid) or {}).get("simulators") or [])
    out = {"needed": False, "why": "", "course_id": cid, "codes": codes}
    if (intake.get("sim_coverage_declined") or "").strip():
        out["why"] = "declined by the operator: " + intake["sim_coverage_declined"].strip()
        return out
    if intake.get("simulators"):
        out.update(needed=True, why="intake.json names the simulators: " + ", ".join(intake["simulators"]))
    elif any(m.lower() in title for m in cat.get("advanced_markers", [])):
        out.update(needed=True, why="an advanced course (its programme title says so)")
    elif any(w.lower() in whole for w in cat.get("simulator_words", [])):
        out.update(needed=True, why="its programme names a simulator")
    else:
        out["why"] = "not an advanced course, and its programme names no simulator"
    return out


def leaf_items(syllabus):
    """the syllabus rows that are items - a heading, or a line that only introduces child lines ("such as:"), is not
    counted: its children are the items"""
    every = [it for items in (syllabus.get("items_by_topic") or {}).values() for it in items or []]
    ids = [str(it.get("id") or "").strip() for it in every]
    parents = {i for i in ids if i and any(j.startswith(i + ".") for j in ids)}
    return [it for it, i in zip(every, ids) if i and not it.get("heading") and i not in parents]


def path(course, name="SIM_COVERAGE.json"):
    return workspace.claude_path(course, name)


def _codes_in(text, codes):
    toks = set(re.findall(r"[A-Za-z][A-Za-z0-9-]*", text or ""))
    return [c for c in codes if c in toks]


def _short_names(codes):
    names = set(codes)
    for s in catalogue().get("simulators", []):
        if s.get("code") in codes:
            names.update(m.get("short", "") for m in s.get("manuals", []))
    return {n for n in names if n}


def drafts_for(course, task):
    """the draft's Trainee and Instructor forms, [] where missing"""
    m = MODULE.search(task.get("module") or "")
    no = (task.get("draft") or "").strip()
    if not m or not no:
        return [], []
    d = os.path.join(workspace.review_dir(course), "exercises", "sim_drafts", "M%02d" % int(m.group(1)))
    find = lambda who: sorted(glob.glob(os.path.join(d, "*Exercise_%s_%s*.docx" % (glob.escape(no), who))))
    return find("Trainee"), find("Instructor")


def check(course):
    """(problems, notes, summary) - problems are plain sentences, each saying what to do"""
    probs, notes = [], []
    p = path(course)
    data = _load(p)
    if data is None:
        return (["There is no simulator coverage map yet (working_claude\\SIM_COVERAGE.json). Start it: sim_coverage.py init "
                 "<course>, then fill every row from SIM_MAP.md (coverage/SIMULATORS.md)."], notes, {})
    for name in ("SIM_MAP.md", "SIM_COVERAGE.md"):
        if not os.path.isfile(path(course, name)):
            probs.append("working_claude\\%s is missing - coverage/SIMULATORS.md §%s says what goes in it."
                         % (name, "2" if name == "SIM_MAP.md" else "4"))
    codes = list((data.get("sim_codes") or {}).keys())
    if not codes:
        probs.append("SIM_COVERAGE.json names no simulator (\"sim_codes\"). Take them from coverage/knowledge/simulators.json.")
    known = {s.get("code") for s in catalogue().get("simulators", [])}
    for c in codes:
        if c not in known:
            notes.append("Simulator %s is not in coverage/knowledge/simulators.json - add it there (name, manuals) so the next "
                         "course finds it." % c)
    smap = path(course, "SIM_MAP.md")
    if os.path.isfile(smap):
        text = io.open(smap, encoding="utf-8", errors="replace").read()
        for c in codes:
            if c not in text:
                probs.append("SIM_MAP.md does not mention simulator %s - its capabilities, with manual pages, come first." % c)
    rows = data.get("kup_items") or []
    ids = [str(r.get("kup_id") or "") for r in rows]
    seen, twice = set(), set()
    for i in ids:
        (twice if i in seen else seen).add(i)
    if twice:
        probs.append("These syllabus items have more than one row: %s. Keep one row per item." % ", ".join(sorted(twice)[:12]))
    syl = ilo_map.find_syllabus(course)
    if syl is None:
        probs.append("There is no transcribed model-course syllabus in working_claude (*syllabus*.json, coverage/GUIDE.md §1) - "
                     "the map is checked item by item against it.")
    else:
        want = [str(it["id"]) for it in leaf_items(syl)]
        miss = [i for i in want if i not in seen]
        extra = sorted(seen - set(want))
        if miss:
            probs.append("%d syllabus item(s) have no row: %s%s. Every item gets a verdict, NOT-SIM included."
                         % (len(miss), ", ".join(miss[:12]), " ..." if len(miss) > 12 else ""))
        if extra:
            probs.append("%d row(s) are not items of the syllabus: %s. Use the syllabus's own numbers."
                         % (len(extra), ", ".join(extra[:12])))
    shorts = _short_names(codes)
    counts, by_comp = {}, {}
    for r in rows:
        v, k = r.get("verdict"), r.get("kup_id")
        if v not in VERDICTS:
            probs.append("Item %s has no verdict (COVERED, PARTLY, GAP or NOT-SIM)." % k)
            continue
        counts[v] = counts.get(v, 0) + 1
        comp = (str(r.get("competence") or "").split() or ["?"])[0]
        by_comp.setdefault(comp, {})
        by_comp[comp][v] = by_comp[comp].get(v, 0) + 1
        if v in ON_SIM:
            if not _codes_in(r.get("sim"), codes):
                probs.append("Item %s is %s but names none of the course's simulators (%s)." % (k, v, ", ".join(codes)))
            pg = r.get("pages") or ""
            if not (PAGE.search(pg) and any(s in pg for s in shorts)):
                probs.append("Item %s is %s but gives no manual page (\"LNG p62\") - a simulator can do only what its manual "
                             "describes." % (k, v))
            if r.get("sim_use") != "assess":
                probs.append("Item %s is %s, so the simulator trains or assesses it: sim_use \"assess\"." % (k, v))
            if v != "GAP" and (r.get("covered_by") or "-").strip() in ("", "-"):
                probs.append("Item %s is %s but names no exercise that does it on the simulator (covered_by)." % (k, v))
        elif not (r.get("note") or "").strip() and (r.get("covered_by") or "-").strip() in ("", "-"):
            probs.append("Item %s is NOT-SIM with no note - say why, and what the course does instead." % k)
    if rows and data.get("total_leaf_items") != len(rows):
        probs.append("total_leaf_items says %s, the map has %d rows." % (data.get("total_leaf_items"), len(rows)))
    if {k: v for k, v in (data.get("counts") or {}).items() if v} != counts:
        probs.append("The counts say %s; the rows give %s. Write the rows' counts." % (data.get("counts"), counts))
    if {c: {k: v for k, v in d.items() if v} for c, d in (data.get("counts_by_competence") or {}).items()} != by_comp:
        probs.append("counts_by_competence does not match the rows - recount it from the rows.")
    verdict = {str(r.get("kup_id")): r.get("verdict") for r in rows}
    tasks = data.get("proposed_tasks") or []
    in_task, tids = set(), set()
    for t in tasks:
        tid = t.get("id") or "?"
        if tid in tids:
            probs.append("Two proposed tasks are called %s." % tid)
        tids.add(tid)
        kup = [str(x) for x in t.get("kup") or []]
        in_task.update(kup)
        bad = [x for x in kup if x not in verdict]
        if bad:
            probs.append("Task %s names item(s) the map does not have: %s." % (tid, ", ".join(bad)))
        if not _codes_in(t.get("simulator"), codes):
            probs.append("Task %s names none of the course's simulators." % tid)
        closes_gap = any(verdict.get(x) == "GAP" for x in kup)
        if not MODULE.search(t.get("module") or ""):
            if closes_gap:
                probs.append("Task %s closes a GAP but names no module (M08 ...) - say where it runs." % tid)
            else:
                notes.append("Task %s has no module yet - an option for the review." % tid)
        if not isinstance(t.get("minutes"), int) or t["minutes"] < 0:
            probs.append("Task %s has no minutes (0 for an inject inside an exercise that already runs)." % tid)
        if not (t.get("minutes_from") or "").strip():
            probs.append("Task %s does not say where its minutes come from inside the module's approved hours - the hours "
                         "never change for a simulator task." % tid)
        if not (t.get("scenario") or "").strip() or not PAGE.search(t.get("pages") or ""):
            probs.append("Task %s needs its scenario and the manual pages it runs from." % tid)
        if closes_gap:
            trainee, instructor = drafts_for(course, t)
            if not (t.get("draft") or "").strip():
                probs.append("Task %s closes a GAP but has no draft - write it as an exercise (Trainee + Instructor form) in "
                             "to_review\\exercises\\sim_drafts\\MNN\\ and give the task \"draft\": \"<exercise no>\"." % tid)
            elif not (trainee and instructor):
                probs.append("Task %s's draft %s is missing its %s form in to_review\\exercises\\sim_drafts\\%s\\." % (
                    tid, t["draft"], "Trainee" if not trainee else "Instructor",
                    "M%02d" % int(MODULE.search(t.get("module") or "M0").group(1))))
    gaps = [k for k, v in verdict.items() if v == "GAP" and k not in in_task]
    if gaps:
        probs.append("%d GAP item(s) are in no proposed task: %s. A simulator can train them - propose the task (L66)."
                     % (len(gaps), ", ".join(gaps[:12])))
    partly = [k for k, v in verdict.items() if v == "PARTLY" and k not in in_task]
    if partly:
        notes.append("%d PARTLY item(s) no task takes up (%s) - shown for review, not a failure."
                     % (len(partly), ", ".join(partly[:8]) + (" ..." if len(partly) > 8 else "")))
    sm = data.get("sim_minutes") or {}
    mods = sm.get("by_module") or []
    for k, tot in (("now", "now_total"), ("proposed", "proposed_total")):
        s = sum(int(m.get(k) or 0) for m in mods)
        if mods and s != sm.get(tot):
            probs.append("sim_minutes: the modules' %s minutes add up to %d, %s says %s." % (k, s, tot, sm.get(tot)))
    summary = {"rows": len(rows), "counts": counts, "tasks": len(tasks), "sim_minutes": (sm.get("now_total"), sm.get("proposed_total"))}
    return probs, notes, summary


def init(course, sims):
    p = path(course)
    if os.path.exists(p):
        return 2, "working_claude\\SIM_COVERAGE.json already exists - nothing was written. Fill it, then: sim_coverage.py check <course>"
    syl = ilo_map.find_syllabus(course)
    if syl is None:
        return 2, ("There is no transcribed model-course syllabus in working_claude (*syllabus*.json) - transcribe it first "
                   "(coverage/GUIDE.md §1, build order step 2).")
    n = needed(course)
    codes = sims or n["codes"]
    if not codes:
        return 2, ("Which simulators? None is known for this course in coverage/knowledge/simulators.json - give them: "
                   "--sims LNG,MeOH (codes from that file), or add the course's simulators there.")
    names = {s["code"]: s["name"] for s in catalogue().get("simulators", [])}
    comp, rows, leaves = {}, [], {id(it) for it in leaf_items(syl)}
    for topic, items in (syl.get("items_by_topic") or {}).items():
        for it in items or []:
            if it.get("heading") and re.match(r"^C?\d+$", str(it.get("id"))):
                comp[topic] = "%s %s" % (it["id"], it.get("requirement", ""))
            if id(it) not in leaves:
                continue
            rows.append({"competence": comp.get(topic, str(topic)), "kup_id": str(it["id"]), "kup_text": it.get("requirement", ""),
                         "sim": "-", "scenario": "", "pages": "", "covered_by": "-", "verdict": "", "note": "", "sim_use": "none"})
    data = {"_what": "Simulator coverage map of this course against %s (L66). One row per leaf syllabus item." % syl.get("source", "the model course"),
            "sim_codes": {c: names.get(c, c) for c in codes}, "counts": {}, "counts_by_competence": {},
            "total_leaf_items": len(rows), "kup_items": rows, "proposed_tasks": [],
            "sim_minutes": {"now_total": 0, "proposed_total": 0, "by_module": []}}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return 0, ("Started working_claude\\SIM_COVERAGE.json: %d items, simulators %s. Next: SIM_MAP.md from the manuals, a verdict "
               "on every row, the GAP tasks and their drafts (coverage/SIMULATORS.md), then sim_coverage.py check <course>."
               % (len(rows), ", ".join(codes)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("needed", "init", "check"))
    ap.add_argument("course")
    ap.add_argument("--sims", help="simulator codes, comma-separated (init)")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    if a.cmd == "needed":
        n = needed(course)
        print("%s - %s.%s" % ("L66 applies" if n["needed"] else "L66 does not apply", n["why"],
                              (" Simulators: %s." % ", ".join(n["codes"])) if n["needed"] and n["codes"] else
                              (" Which simulators is not known - see coverage/knowledge/simulators.json." if n["needed"] else "")))
        return 0
    if a.cmd == "init":
        code, msg = init(course, [s.strip() for s in (a.sims or "").split(",") if s.strip()])
        print(msg)
        return code
    probs, notes, s = check(course)
    if probs:
        print("Simulator coverage is not complete yet (L66):\n" + "\n".join("  - " + x for x in probs))
    else:
        c = s["counts"]
        print("Simulator coverage complete: %d items - %s; %d proposed task(s); simulator minutes %s now, %s proposed." % (
            s["rows"], ", ".join("%s %d" % (v, c.get(v, 0)) for v in VERDICTS), s["tasks"], s["sim_minutes"][0], s["sim_minutes"][1]))
    for n in notes:
        print("  note: " + n)
    return 2 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
