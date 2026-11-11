#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simulator coverage (L66) - every model-course item a school simulator can train is trained on it.

    sim_coverage.py needed <course>                   does L66 apply, and which simulators (coverage/knowledge/simulators.json)
    sim_coverage.py practical <course>                which modules have simulator or equipment exercises, and which none
    sim_coverage.py init   <course> [--sims LNG,MeOH] start working_claude\\SIM_COVERAGE.json: one empty row per syllabus item
    sim_coverage.py check  <course>                   exit 0: the map is whole; exit 2: what is missing, in plain words
    sim_coverage.py accept <course> --task P1 --by "<name>"   the course director accepts a task's draft

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
A PARTLY item no task takes up is a note, not a failure: the review page shows it. So is a drafted task the course
director has not accepted: nothing is built from its draft, and the module's screen that names it holds its minutes
with no exercise behind it (pending; check_course_package.py says it too).

WHAT practical SAYS
Module by module, the practice minutes the programme gives it (programme.json topics, by plan.json), the practicals
architecture.json names with their kind on paper (simulator / equipment / room, the rule additional_materials.py prints
by), and its simulator tasks (SIM_COVERAGE.json). A module with practice minutes and no practical named is said. A
course with none of these has no practical work: no paper exercise is printed for it, and it is said.
factory_trial.py picks its practical module from it.

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

if hasattr(sys.stdout, "reconfigure"):
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
    given = intake.get("simulators")
    given = [str(x) for x in given] if isinstance(given, list) else []      # codes; a sentence names them, it lists none
    codes = list(given or ((cat.get("courses") or {}).get(cid) or {}).get("simulators") or [])
    out = {"needed": False, "why": "", "course_id": cid, "codes": codes}
    if (intake.get("sim_coverage_declined") or "").strip():
        out["why"] = "declined by the operator: " + intake["sim_coverage_declined"].strip()
        return out
    if intake.get("simulators"):
        out.update(needed=True, why="intake.json names the simulators: " + (", ".join(given) or str(intake["simulators"])))
    elif any(m.lower() in title for m in cat.get("advanced_markers", [])):
        out.update(needed=True, why="an advanced course (its programme title says so)")
    elif any(w.lower() in whole for w in cat.get("simulator_words", [])):
        out.update(needed=True, why="its programme names a simulator")
    else:
        out["why"] = "not an advanced course, and its programme names no simulator"
    mc, entry = model_course(course)
    if entry and entry.get("simulator_topics"):
        # L28: every simulator of the IMO model course is assumed available - its simulator topics are planned as
        # simulator exercises even where L66's full map does not apply
        out["model_course"] = dict(entry, id=mc)
        if not out["needed"] and not given:
            out["codes"] = list(entry.get("simulators") or [])
    if out["needed"] or out.get("model_course"):
        out["manuals"] = manuals_in_sources(course, out["codes"])
    return out


def model_course(course):
    """(its number, its entry in simulators.json "model_courses") of the course's IMO model course, or (None, None)"""
    prog, arch = ilo_map.course_files(course)
    text = " ".join(str(x or "") for x in ((prog or {}).get("imo_model_course"), (prog or {}).get("model_course"),
                                            ((arch or {}).get("course") or {}).get("model_course")))
    for k, v in (catalogue().get("model_courses") or {}).items():
        if re.search(r"(?<![\d.])%s(?![\d])" % re.escape(k), text):
            return k, v
    return None, None


def manuals_in_sources(course, codes):
    """{"found": {code: [file]}, "missing": [code]} - the simulators' manuals (simulators.json) in the course's own
    source_files and old course; a simulator exercise is written from its manual, never without it"""
    names = {}
    for s in catalogue().get("simulators", []):
        if s.get("code") in codes:
            for m in s.get("manuals") or []:
                names[(m.get("file") or "").lower()] = s["code"]
    master = workspace.master_of(course)
    found = {}
    for sub in ("source_files", "old_course"):
        for dp, _, fs in os.walk(os.path.join(master, sub)):
            for f in fs:
                code = names.get(f.lower())
                if code:
                    found.setdefault(code, []).append(f)
    return {"found": found, "missing": [c for c in codes if c not in found]}


def model_course_lines(n):
    """what the IMO model course asks of a simulator, and which manuals the sources hold - [] when it asks nothing"""
    mc = n.get("model_course")
    if not mc:
        return []
    out = ["IMO Model Course %s marks topics to be taught on a simulator (%s): %s. Exercises: %s. Every simulator of the model "
           "course is assumed available (L28): Stage 2 plans these topics as simulator exercises (architecture.json "
           "\"practicals\", inside the theory minutes where the programme gives them no practice hours), each written on "
           "paper from the simulator's manual and the model course, its activity screen in the deck where the class goes to it."
           % (mc["id"], mc.get("pages", ""), "; ".join(mc["simulator_topics"]), mc.get("exercises", "-"))]
    if mc.get("equipment_topics"):
        out.append("Its real-equipment practicals: %s - paper exercises too." % "; ".join(mc["equipment_topics"]))
    man = n.get("manuals") or {}
    if man.get("found"):
        out.append("Manuals in the sources: %s." % "; ".join("%s %s" % (c, ", ".join(f)) for c, f in man["found"].items()))
    if not man.get("found"):
        out.append("No simulator manual in the sources (%s): ask the operator for it - unattended, write it to "
                   "OPEN_EXPERT_QUESTIONS.md - and never write a simulator procedure without it." % ", ".join(n["codes"]))
    return out


# the rule additional_materials.classify prints a practical's paper by (test_sim_coverage.py keeps the two the same)
SIM_WORDS = re.compile(r"simulator|симулятор|тренаж", re.I)
EQUIPMENT_WORDS = re.compile(r"\b(?:rig|bench|detectors?|meters?|apparatus|instruments?|equipment|facility|monitor|"
                             r"tripod|stretcher|resuscitator|extinguisher|hoses?|iekārt\w*|aprīkojum\w*|mērinstrument\w*|"
                             r"оборудован\w*|прибор\w*|стенд\w*)\b", re.I)


def _paper_kind(words):
    """simulator, equipment or room"""
    if SIM_WORDS.search(words):
        return "simulator"
    return "equipment" if EQUIPMENT_WORDS.search(words) else "room"


def practical(course):
    """{"modules": {n: {"minutes", "practicals": [{"name", "kind", "place", "minutes"}], "sim_tasks": [{"id", "minutes",
    "accepted"}], "kind"}}, "l66": needed(course)} - every module with practice minutes in the programme, a practical in
    the architecture or a simulator task. A module's kind: simulator when a simulator does part of it, else equipment, else
    room; "unnamed" when the programme gives it practice minutes and the architecture names no practical"""
    prog, arch = ilo_map.course_files(course)
    prog, arch = prog or {}, arch or {}
    hour = float(prog.get("academic_hour_min") or 45)
    topics = prog.get("topics") or {}
    if isinstance(topics, list):
        topics = {str(t.get("id") or t.get("no") or i): t for i, t in enumerate(topics, 1) if isinstance(t, dict)}
    plan = [m for m in (_load(workspace.claude_path(course, "plan.json")) or {}).get("modules") or []
            if isinstance(m, dict) and m.get("module") is not None]
    # a module per topic until Stage 2's plan says which topics each module holds
    by_topic = {str(m["module"]): [str(t) for t in m.get("topics") or []] for m in plan} if plan else \
        {str(k): [str(k)] for k in topics}
    mods = {}

    def row(n):
        return mods.setdefault(n, {"minutes": 0, "practicals": [], "sim_tasks": [], "kind": ""})
    for n, keys in by_topic.items():
        try:
            n = int(str(n).lstrip("Mm"))
        except ValueError:
            continue
        mins = sum(float((topics.get(k) or {}).get("practical") or 0) for k in keys if isinstance(topics.get(k), dict)
                   and not topics[k].get("assessment")) * hour
        if mins:
            row(n)["minutes"] = int(round(mins))
    for am in arch.get("modules") or []:
        try:
            n = int(str(am.get("module")).lstrip("Mm"))
        except (TypeError, ValueError):
            continue
        for p in am.get("practicals") or []:
            if not isinstance(p, dict):
                continue
            words = " ".join(str(p.get(k) or "") for k in ("task", "equipment", "place"))
            name = re.split(r"\s\(|:", str(p.get("task") or ""), maxsplit=1)[0].strip()
            row(n)["practicals"].append({"name": name, "kind": _paper_kind(words), "place": p.get("place") or "",
                                         "minutes": p.get("minutes")})
    for t in (_load(path(course)) or {}).get("proposed_tasks") or []:
        m = MODULE.search(t.get("module") or "")
        if m:
            row(int(m.group(1)))["sim_tasks"].append({"id": t.get("id"), "minutes": t.get("minutes"),
                                                       "accepted": bool((t.get("accepted_by") or "").strip())})
    for r in mods.values():
        kinds = [p["kind"] for p in r["practicals"]]
        r["kind"] = ("simulator" if r["sim_tasks"] or "simulator" in kinds else "equipment" if "equipment" in kinds
                     else "room" if kinds else "unnamed")
    return {"modules": dict(sorted(mods.items())), "l66": needed(course)}


def practical_lines(p):
    """the practical work of a course in plain lines - the last one says when it has none"""
    out = []
    for n, r in p["modules"].items():
        what = "; ".join("%s: %s%s" % (x["kind"], x["name"] or "-", (" (%s)" % x["place"]) if x["place"] else "")
                         for x in r["practicals"])
        if r["sim_tasks"]:
            what += ("; " if what else "") + "simulator tasks: " + ", ".join(
                "%s %s min%s" % (t["id"], t["minutes"], "" if t["accepted"] else " (draft)") for t in r["sim_tasks"])
        if not what:
            what = "no practical named in architecture.json - Stage 2 names what the trainees do in these minutes"
        out.append("M%02d  %s min practice - %s" % (n, r["minutes"], what))
    if not p["modules"]:
        out.append("No practical work in this course: the programme gives no practice minutes and names no simulator or "
                   "equipment exercise - no paper exercise is printed and no activity screen sends the class to one.")
    elif not any(r["kind"] == "simulator" for r in p["modules"].values()):
        out.append(("No simulator exercise in the architecture yet, and L66 applies - %s: sim_coverage.py check <course>."
                    if p["l66"]["needed"] else "No simulator exercise in the architecture; L66's coverage map does not apply - %s.")
                   % p["l66"]["why"])
    return out + model_course_lines(p["l66"])


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
    notes += [pending_line(x) for x in pending(course)]
    summary = {"rows": len(rows), "counts": counts, "tasks": len(tasks), "sim_minutes": (sm.get("now_total"), sm.get("proposed_total"))}
    return probs, notes, summary


def pending(course):
    """[{task, module, minutes, draft, screens}] - every drafted task the course director has not accepted ("accepted_by"):
    nothing is built from its draft (L66), so the activity screens of its module's script that name it (in a title, the
    words or the notes) hold its minutes with no exercise behind them"""
    out = []
    for t in (_load(path(course)) or {}).get("proposed_tasks") or []:
        m = MODULE.search(t.get("module") or "")
        tid = str(t.get("id") or "").strip()
        if not m or not tid or not (t.get("draft") or "").strip() or (t.get("accepted_by") or "").strip():
            continue
        script = _load(workspace.claude_path(course, "script", "M%02d.json" % int(m.group(1)))) or {}
        named = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(tid))
        screens = [s.get("id") for s in script.get("screens") or []
                   if (s.get("kind") == "activity" or s.get("track") == "practical" or s.get("practice_minutes"))
                   and named.search(" ".join(str(s.get(k) or "") for k in ("title", "text", "notes")))]
        out.append({"task": tid, "module": int(m.group(1)), "minutes": t.get("minutes"), "draft": t["draft"].strip(),
                    "screens": screens})
    return out


def pending_line(p):
    held = ("its minutes are held by " + ", ".join(p["screens"])) if p["screens"] else "no screen of its module's script names it"
    return ("%s (M%02d, %s min) is a draft awaiting the course director - %s, no exercise behind it (L66): "
            "to_review\\exercises\\sim_drafts\\M%02d\\, draft %s" % (p["task"], p["module"], p["minutes"], held, p["module"], p["draft"]))


def accept(course, tid, by):
    """the course director's acceptance of a task's draft - never an unattended build's"""
    if os.environ.get("NOVIKONTAS_AUTO_BUILD") == "1":
        return 2, ("Stopped - a simulator draft is accepted by the course director in their own session, never by an "
                   "unattended build (L66). It stays pending; the course check lists it.")
    if not (by or "").strip():
        return 2, "Stopped - say who accepts it: --by \"<the course director's name>\"."
    p = path(course)
    data = _load(p)
    task = next((t for t in (data or {}).get("proposed_tasks") or [] if str(t.get("id")) == tid), None)
    if task is None:
        return 2, "Stopped - there is no proposed task %s in working_claude\\SIM_COVERAGE.json." % tid
    if not (task.get("draft") or "").strip():
        return 2, "Stopped - task %s has no draft to accept (coverage/SIMULATORS.md §4)." % tid
    from datetime import date
    task.update(accepted_by=by.strip(), accepted=date.today().isoformat())
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    m = MODULE.search(task.get("module") or "")
    return 0, ("Task %s accepted by %s. Its draft %s becomes the module's exercise: its forms in to_review\\exercises\\%s\\ "
               "(novikontas-practical-exercises), and the screen that holds its minutes says \"exercise\": \"<its number>\"."
               % (tid, by.strip(), task["draft"], "M%02d" % int(m.group(1)) if m else "MNN"))


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
    ap.add_argument("cmd", choices=("needed", "practical", "init", "check", "accept"))
    ap.add_argument("course")
    ap.add_argument("--sims", help="simulator codes, comma-separated (init)")
    ap.add_argument("--task", help="the proposed task's id (accept)")
    ap.add_argument("--by", help="the course director's name (accept)")
    a = ap.parse_args(argv)
    course = workspace.work_folder(a.course, create=False)
    if a.cmd == "accept":
        code, msg = accept(course, a.task or "", a.by or "")
        print(msg)
        return code
    if a.cmd == "practical":
        print("\n".join(practical_lines(practical(course))))
        return 0
    if a.cmd == "needed":
        n = needed(course)
        print("%s - %s.%s" % ("L66 applies" if n["needed"] else "L66 does not apply", n["why"],
                              (" Simulators: %s." % ", ".join(n["codes"])) if n["needed"] and n["codes"] else
                              (" Which simulators is not known - see coverage/knowledge/simulators.json." if n["needed"] else "")))
        for line in model_course_lines(n):
            print(line)
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
