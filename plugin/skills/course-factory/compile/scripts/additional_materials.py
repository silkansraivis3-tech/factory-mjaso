#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The course's additional materials - the paper an auditor, the office and the instructor need beside the tablets.

    additional_materials.py <course folder>            build course\\additional-materials\\ and the two plan pages
    additional_materials.py <course folder> --no-pdf   the same without the PDF files (no browser)
    additional_materials.py <course folder> --check    say what is missing or out of date; writes nothing

compile_course.py runs it on every build, so a course is never handed over without it.

WHAT IT WRITES
  course\\additional-materials\\
      INDEX.html                                  what is here, with a link to every file - the office's way in
      acp\\ACP_<course>.docx                       the Advanced Course Plan for the auditor: day by day, each module's
      acp\\ACP_<course>.html                       programme topic, training method, outcomes, used material, the
                                                  practical exercises and questions to check the day's objectives
      practical-tasks\\pdf\\M04_SC1_<title>.pdf     one description per task of the course - every self-check, team
      practical-tasks\\docx\\M04_SC1_<title>.docx   task, module check and room, simulator or equipment exercise: what
                                                  the trainee does, the right answers, how it is marked
      simulator-and-equipment\\Day_2\\             what the instructor prints at the start of the day for every
          M04_A01_<title>_TRAINEE.pdf / .docx     simulator and real-equipment exercise of that day: the trainee card
          M04_A01_<title>_INSTRUCTOR.pdf          (no answers) and the instructor sheet (the full description)
      practical-kit\\Day_2\\                       the guideline's paper (L68), from the approved instructor_led.json, one
          M04_A01_<title>_PREBRIEF.pdf / .docx    page each: the pre-brief card read aloud before the run, the debrief card
          M04_A01_<title>_DEBRIEF.pdf / .docx     with the observation card under it, and for a recorded run the
          M05_A01_<title>_ASSESSMENT.pdf / .docx  assessment form, one per candidate
      practical-kit\\EMPLOYER_SHEET_<course>.pdf / .docx   one page for the company: what the trainee can now do, what decays
                                                  fastest, an on-board drill at 1-3 months, what to watch for
  course\\modules\\_course_shell\\advanced_course_plan.html   the same plan for the instructor's tablet
  course\\modules\\moduleNN\\instructor\\advanced_module_plan.html   one module explained step by step, for the tablet
  course\\modules\\moduleNN\\instructor\\papers\\M04_A01_<title>_TRAINEE.html / .pdf   the module's simulator and
      ..._INSTRUCTOR.html / .pdf                  equipment papers again, on the instructor's tablet: the module plan's
                                                  step links each, to open in the viewer and to print the PDF
  The tablet pages are self-contained (their style inline, no script, no link but the module plan's to its papers): the
  instructor panel opens them over itself and closes them again. All are instructor-only by their folder (_course_shell,
  instructor) - the app's import never copies them to a trainee.

EVERY WORD IS FROM AN APPROVED FILE, NOTHING IS TYPED
  the course, its hours, days, rooms, equipment, literature, films, group and assessment   programme.json
  the Main ILOs and the modules                                                          architecture.json
  the Sub-ILOs                                                                           ilo_map.json (else the ids)
  the Main ILOs and Sub-ILOs in English (L19): a programme in another language by the rendering written beside its
                                    words at Stage 2 (ilo_map.english) - a missing one shows the programme's words and is said
  every screen, task, question, answer, feedback and instructor note                     working_claude\\script\\MNN.json
  the exercise's equipment and place                                                     architecture.json "practicals"
  which day a module falls on       course.build.json "days": [[1, 2, 3, 4], [4, 5, 6]] - delivery, like module_order;
                                    else the modules in the course's order fill each day up to the programme's
                                    max_hours_per_day, a module split across two days where the day ends
  who answers for the programme     course.build.json "responsible" - else a line to sign
  a task's kind on paper            simulator / equipment / room from its words and its practical's equipment;
                                    course.build.json "paper_tasks": {"M09.A02": "equipment"} when the words mislead
  one paper for a practical's screens   the script's "paper" (its name) and "paper_part" (brief, show, debrief: the
                                    instructor sheet only)
  a simulator exercise's paper      its approved exercise form, working_claude\\exercises\\[sim_drafts\\]MNN\\content\\
  the instructor sheet's criteria   the approved instructor_led.json; the IMO model course and the sources: the script
A module whose script is not approved gets nothing and is said. The words of the documents are English only so far; a
course in another language is said, never silently written in English.

THE PDF
Printed by the same hidden Chrome or Edge the factory measures with (browser_slots), from an HTML copy kept in
working_claude\\additional_materials\\. A PDF is printed again only when its page changed (the record
working_claude\\additional_materials.json), so a rebuild costs seconds. A file the factory wrote before and no longer
makes (a task renamed) is moved to working_claude\\additional_materials\\old\\, never deleted (L8).

Exit 0 built; 1 built, with problems to fix; 2 nothing built.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "scripts"))
import answer_key as ak  # noqa: E402
import classroom_files as cf  # noqa: E402
import compile_module as cm  # noqa: E402
import content_script as cs  # noqa: E402
import ilo_map  # noqa: E402
import instructor_led as il  # noqa: E402
import task_pages as tp  # noqa: E402
import workspace  # noqa: E402

FOLDER = workspace.ADDITIONAL
RECORD = "additional_materials.json"
COURSE_PLAN = os.path.join("_course_shell", "advanced_course_plan.html")
MODULE_PLAN = os.path.join("instructor", "advanced_module_plan.html")
PAPERS = os.path.join("instructor", "papers")       # beside the module plan, which opens them
PAPERS_LIST = "papers.json"                         # in it: the papers' names and kinds, for the instructor's list
# a simulator, never a "simulated" fire or a "real-life simulation" on the fire ground or the rescue rig
SIM_WORDS = re.compile(r"simulator|симулятор|тренаж", re.I)
EQUIPMENT_WORDS = re.compile(r"\b(?:rig|bench|detectors?|meters?|apparatus|instruments?|equipment|facility|monitor|"
                             r"tripod|stretcher|resuscitator|extinguisher|hoses?|iekārt\w*|aprīkojum\w*|mērinstrument\w*|"
                             r"оборудован\w*|прибор\w*|стенд\w*)\b", re.I)
OWN_NUMBER = re.compile(r"^\s*(?:\d{1,2}|[a-z])[.)]\s")
INSTRUCTOR_PARTS = ("brief", "show", "debrief")     # a practical's parts that go on the instructor sheet only
OPTION_MECHS = ("single_choice", "multi_select", "read_instrument", "choose_and_justify", "investigate")
W = {
    "acp": "Advanced Course Plan", "programme": "Programme", "standard": "Standard", "model": "IMO model course",
    "duration": "Duration", "hours": "{h} academic hours of {m} min, {d} days", "language": "Course language",
    "group": "Group", "group_v": "theory up to {t} trainees; practical work up to {p} trainees per instructor",
    "rooms": "Rooms", "equipment": "Equipment", "assessment": "Final assessment",
    "assessment_v": "{q} questions, pass mark {p}", "main_ilos": "Main intended learning outcomes",
    "day": "Day {n}", "objectives": "Training objectives", "cols": ["No", "Programme topic", "Training method", "Notes"],
    "title": "Title", "description": "Description", "used": "Used material", "minutes_day": "{m} min on this day",
    "part": "part {k} of {n}", "presentation": "Presentation on the classroom screen ({n} slides)",
    "self_checks": "Self-checks on the trainee tablets: {codes}", "team": "Team tasks on the trainee tablets: {codes}",
    "module_check": "Module check on the trainee tablets", "exercise": "Practical exercise {code}: {title}",
    "where": {"simulator": "on the simulator", "equipment": "with real equipment", "room": "in the classroom"},
    "questions": "Questions to check the objectives", "final": "Final assessment",
    "responsible": "The person responsible for implementation of the programme",
    "responsible_blank": "______________________________  (name, surname and position)",
    "literature": "Literature", "films": "Training films", "made": "Made from the approved course files by course-factory "
    "{v} on {d}. Never edit it by hand: correct the content script or the course files and build again.",
    # the module plan
    "mplan": "Module {n} - step by step", "instr": "Instructor only", "time": "{m} min ({h} academic hours)",
    "on_days": "Day {d}", "can": "By the end of the module the trainees can", "prepare": "Before you start",
    "tablets": "A trainee tablet for each trainee: {codes}.", "film": "Film on slide {n}: {what}",
    "step": "Step {k}", "mins": "minutes {a}-{b}", "teach": "You teach", "they_do": "The trainees do",
    "on_tablets": "On the tablets", "say": "The trainees are told", "you": "You", "exercise_h": "Practical exercise",
    "papers": "To print at the start of the day", "instructor_sheet": "Instructor sheet",
    "parts": "Its parts", "how_runs": "How the practical runs, part by part",
    "part_roles": {"brief": "the brief - the instructor's", "show": "the demonstration - the instructor's",
                   "debrief": "the debrief - the instructor's"},
    "criteria": "Assessment criteria", "must_pass": "must pass", "at_step": "step {n} of {code}",
    "observe": "Must observe ({code}):", "model_ref": "IMO model course", "sources_h": "Sources",
    "form_made": "The approved exercise form {no}, printed from its own fields.",
    "equip_codes": "equipment: the programme's {codes} (their English names are not in the course files yet)", "questions_n": "{n} questions",
    "plan_made": "Made from the approved content script ({m}.json) by course-factory {v}. Never edit it by hand.",
    "active": {"explain-then-reveal": "explain, then see the answer", "predict-then-reveal": "predict, then see what happens",
               "worked-example": "a worked example, then their own attempt", "scenario": "a scenario",
               "explore": "explore", "self-check": "a self-check", "other": "an activity"},
    # the task papers
    "task": "Practical task", "course": "Course", "module": "Module", "code": "Task", "kind": "Kind",
    "kinds": {"self-check": "Self-check on the trainee tablet", "module-check": "Module check on the trainee tablet",
              "final": "Final assessment on the trainee tablet", "team": "Team task on the trainee tablets",
              "simulator": "Practical exercise on the simulator", "equipment": "Practical exercise with real equipment",
              "room": "Practical exercise in the classroom"},
    "minutes": "Time", "min": "{m} min", "place": "Place and equipment", "outcomes": "Learning outcomes it serves",
    "intro": "What the trainee is told", "how_q": "Question {n} of {t} - {how}", "shows": "The screen shows: {x}",
    "choices": "Choices", "level": "Bloom level {b}", "steps": "What the trainee does", "instructor_h": "For the instructor",
    "notes": "Running it", "answers": "Right answers and what the trainee is shown", "answer": "Right answer",
    "feedback": "Shown after the answer", "marking": "Marking",
    "mark_self": "One point per question, no pass mark. The trainee sees their own score; it is not recorded as a grade.",
    "mark_check": "One point per question; a question with several parts counts only when every part is right. No pass "
                  "mark: the score tells the trainee and the instructor what was understood.",
    "mark_final": "One point per question. Pass mark {p} %: {need} of {total} right = PASSED.",
    "mark_room": "The instructor checks each step at the station before the next one starts.",
    "team_v": "teams of {size}; roles: {roles}", "trainee_card": "Trainee card", "no_answers": "No answers on this card.",
    "sign": "Trainee: ______________________   Instructor: ______________________   Date: ____________",
    # the index
    "index": "Additional materials", "index_sub": "{course} - every document beside the tablets",
    "i_acp": "Advanced Course Plan (Word for the auditor, HTML for reading)",
    "i_tasks": "Practical task descriptions - {n} tasks, each as PDF and Word",
    "i_sim": "Simulator and equipment exercises to print, by day", "i_none": "This course has no simulator or equipment exercise.",
    "i_plans": "On the instructor's tablet: the course plan (_course_shell) and each module's step-by-step plan (instructor)",
    # the practical kit (L68)
    "i_kit": "Practical kit - pre-brief, debrief and observation cards, assessment forms, by day; the employer sheet",
    "i_kit_none": "No practical kit: the course's instructor_led.json names no practical, or is not approved.",
    "prebrief": "Pre-brief card", "prebrief_sub": "{code} - read aloud before the run, {m} min",
    "objective": "Objective", "p_or_r": "Practice or recorded", "practice_v": "Today is practice. Nothing is marked.",
    "recorded_v": "This run is recorded on the assessment form. Changed condition: {c}.", "roles": "Roles",
    "safety": "Safety rules", "stop_word": "Stop word", "stop_v": "{w}. Anyone says it, everyone stops and hands off.",
    "will_do": "What I will do",
    "debrief": "Debrief card", "debrief_sub": "{code} - {m} min, after the run", "stage": "Stage", "script": "Script",
    "reactions": "Reactions (2 min)", "observe_items": "Must-observe items", "prompt_1": "Analysis prompt 1",
    "prompt_2": "Analysis prompt 2", "feedback_form": "Feedback", "close": "Close",
    "obs": "Observation card - filled by the observers, practice only", "obs_cols": ["Watch for", "Time / step", "What was said or done"],
    "form": "Assessment form", "form_sub": "{code} - one per candidate, filled by the assessor during the recorded run",
    "candidate": "Candidate", "assessor": "Assessor", "blank": "______________________________",
    "critical": "A. Critical steps", "crit_cols": ["#", "Critical step", "Done", "Not done", "Not observed"],
    "crit_rule": "One Not done = Not yet.", "stop": "STOP", "global": "B. Global rating", "decision_h": "C. Decision",
    "gwo": "D. Standard levels", "gwo_v": "GWO 0-3: ____", "details": "Run details", "changed": "Changed condition: {c}",
    "employer": "Employer sheet", "can_now": "What the trainee can now do", "decays": "What decays fastest",
    "drill": "On-board drill at 1-3 months", "watch": "What to watch for", "refresher": "Refresher position",
}


def e(x):
    return html.escape(str(x if x is not None else ""), quote=False)


class H(str):
    """a piece of text that is already HTML (escaped, maybe with <b>) - everything else is plain text"""


def b_(label):
    return H("<b>%s</b>" % e(label))


def num(x):
    return "%g" % round(float(x), 2)


def load_or(path, default):
    try:
        return cs.load(path) if os.path.isfile(path) else default
    except (OSError, ValueError):
        return default


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


WRITER = sha_file(os.path.abspath(__file__))          # this tool's own code - part of every Word file's record


# ------------------------------------------------------------------ what the course is
def approved(script):
    return script.get("status") == "approved" and script.get("approved_hash") == cs.content_hash(script)


def sub_ilo_texts(course, arch, no_en=None):
    """{sub-ILO id: its words in English (L19)} - the ILO map first, then the architecture's added Sub-ILOs; one with no
    English rendering keeps the programme's words, and is named in no_en"""
    out = {}
    for am in arch.get("modules") or []:
        for s in am.get("sub_ilos") or []:
            if isinstance(s, dict) and s.get("text"):
                out[str(s.get("id"))] = s.get("text_en") or s["text"]
    m = ilo_map.read(course)
    for r in ilo_map.with_english(course, [r for r in (m or {}).get("rows") or [] if isinstance(r, dict)]):
        if r.get("sub_ilo"):
            out[str(r.get("sub_ilo_id"))] = r.get("sub_ilo_en") or r["sub_ilo"]
            if not r.get("sub_ilo_en") and r.get("sub_ilo_status") != "main" and no_en is not None:   # a Main ILO is said as one
                no_en.append("Sub-ILO %s" % r.get("sub_ilo_id"))
    return out


def classify(text, override=None):
    """simulator, equipment or room - an exercise on paper, by its own words (and its practical's equipment)"""
    if override in ("simulator", "equipment", "room"):
        return override
    if SIM_WORDS.search(text):
        return "simulator"
    return "equipment" if EQUIPMENT_WORDS.search(text) else "room"


def match_practicals(acts, practicals):
    """{activity id: practical} - first by an exercise number both name (9.1), then in order"""
    nums = lambda t: set(re.findall(r"\b\d+\.\d+\b", t or ""))
    out, left = {}, list(practicals)
    for s in acts:
        hit = next((p for p in left if nums(s.get("title")) & nums(p.get("task"))), None)
        if hit:
            out[s["id"]] = hit
            left.remove(hit)
    for s in acts:
        if s["id"] not in out and left:
            out[s["id"]] = left.pop(0)
    return out


def tasks_of(m, sheet):
    """every task of a module in the order the class meets it - [{code, title, kind, where, minutes, start, ...}]"""
    script = m["script"]
    screens = [s for s in script["screens"] if s.get("kind") in cs.INSTRUCTOR]
    start, t = {}, 0.0
    for s in screens:
        start[s["id"]] = t
        t += cs.minutes(s)
    found = {c: (sl, qs) for sl, c, qs in tp.sets(script)}
    acts = [s for s in screens if s["kind"] == "activity"]
    prac = match_practicals(acts, m["practicals"])
    over = sheet.get("paper_tasks") or {}
    out = []
    for s in screens:
        if s["kind"] == "task-slide" and (s.get("opens") or "").strip() in found:
            code = s["opens"].strip()
            sl, qs = found[code]
            kind = qs[0]["kind"] if qs else "self-check"
            if isinstance(sl.get("team"), dict) and sl["team"]:
                kind = "team"
            title = tp.short_title(sl.get("title")) if code.startswith(("SC", "TT")) else (sl.get("title") or code)
            out.append({"code": code, "title": title, "kind": kind, "where": "tablet", "slide": sl, "questions": qs,
                        "minutes": cs.minutes(sl), "start": start[sl["id"]]})
        elif s["kind"] == "activity":
            code = s["id"].upper()
            p = prac.get(s["id"]) or {}
            words = " ".join(str(x or "") for x in (s.get("title"), s.get("text"), p.get("task"), p.get("equipment")))
            where = classify(words, over.get("%s.%s" % (m["mid"], code)))
            out.append({"code": code, "title": s.get("title") or code, "kind": where, "where": where, "slide": s,
                        "questions": [], "minutes": cs.minutes(s), "start": start[s["id"]], "practical": p})
    for x in out:
        x["stem"] = "%s_%s_%s" % (m["mid"], x["code"], stem_title(x["title"]))
        subs = []
        for q in [x["slide"]] + x["questions"]:
            subs += [i for i in cs.sub_ilos_of(q) if i not in subs]
        x["sub_ilos"] = subs
    return group_papers(m, out)


def paper_of(x):
    """the practical an activity screen is part of ("paper": its name, the script's), "" for a screen on its own"""
    return str(x["slide"].get("paper") or "").strip() if x["slide"].get("kind") == "activity" else ""


def group_papers(m, tasks):
    """the activity screens of one practical (the same "paper", one after another) become one task with one paper - its
    parts in order; the brief, show and debrief parts go on the instructor sheet only. A screen with no "paper" is a
    task and a paper of its own, as the scripts before the field are"""
    out = []
    for x in tasks:
        name, prev = paper_of(x), (out[-1] if out else None)
        if name and prev and prev.get("paper") == name:
            prev["parts"].append(x)
            continue
        out.append(dict(x, paper=name, parts=[dict(x)]))
    for t in out:
        parts = t["parts"]
        if len(parts) < 2:
            continue
        kinds = [p["where"] for p in parts]
        where = "simulator" if "simulator" in kinds else "equipment" if "equipment" in kinds else "room"
        code = "%s-%s" % (parts[0]["code"], parts[-1]["code"])
        subs = []
        for p in parts:
            subs += [i for i in p["sub_ilos"] if i not in subs]
        t.update(code=code, title=t["paper"], kind=where, where=where, minutes=sum(p["minutes"] for p in parts),
                 practical=next((p["practical"] for p in parts if p.get("practical")), {}), sub_ilos=subs,
                 stem="%s_%s_%s" % (m["mid"], code, stem_title(t["paper"])))
    return out


def role(part):
    """what a part of a practical is: brief, show, debrief (the instructor's) or do (the trainees')"""
    r = str(part["slide"].get("paper_part") or "").strip().lower()
    return r if r in INSTRUCTOR_PARTS else "do"


def exercise_form(course, m, t):
    """{"no", "trainee", "instructor"} - the approved exercise form (its content file, the form's own fields) of the
    exercise a screen of this task names ("exercise": "<no>"), or None. A simulator draft counts only once the course
    director has accepted it (L66): working_claude\\exercises\\MNN\\content\\ first, then sim_drafts\\MNN\\content\\"""
    nos = [str(p["slide"].get("exercise") or "").strip() for p in t["parts"]]
    no = next((x for x in nos if x), "")
    if not no:
        return None
    accepted = {str(x.get("draft") or "").strip() for x in (load_or(workspace.claude_path(course, "SIM_COVERAGE.json"), {})
                                                            .get("proposed_tasks") or []) if (x.get("accepted_by") or "").strip()}
    dirs = [workspace.claude_path(course, "exercises", m["mid"], "content")]
    if no in accepted:
        dirs.append(workspace.claude_path(course, "exercises", "sim_drafts", m["mid"], "content"))
    for d in dirs:
        both = [load_or(os.path.join(d, "EX_%s_%s.json" % (no, who)), None) for who in ("trainee", "instructor")]
        if all(isinstance(x, dict) for x in both):
            return {"no": no, "trainee": both[0], "instructor": both[1]}
        one = load_or(os.path.join(d, "EX_%s.json" % no), None)
        if isinstance(one, dict) and isinstance(one.get("trainee"), dict) and isinstance(one.get("instructor"), dict):
            return {"no": no, "trainee": one["trainee"], "instructor": one["instructor"]}
    return None


def modules_of(course, arch, infos, probs):
    """the approved modules in the course's order - [{n, mid, code, title, minutes, script, build, practicals, tasks}]"""
    planned = {ilo_map.mkey(x.get("module")): x for x in arch.get("modules") or []}
    out = []
    for i in infos:
        script = i.get("script") or {}
        if not script or not approved(script):
            probs.append("%s: its content script is not approved - its plan and its task papers wait for it" % i["code"])
            continue
        n = i["n"]
        p = cs.paths(course, n)["script"]
        build = load_or(p[:-5] + ".build.json", {})
        am = planned.get(ilo_map.mkey(n)) or {}
        m = {"n": n, "mid": cs.mid(n), "code": i["code"], "title": i["title"], "minutes": cs.minutes({"minutes": script.get("minutes_allocated")}),
             "script": script, "build": build, "main_ilos": am.get("main_ilos") or [],
             "practicals": [x for x in am.get("practicals") or [] if isinstance(x, dict)]}
        out.append(m)
    return out


def days_of(mods, prog, sheet, final_min, probs):
    """[[(module, minutes on the day, part k, of n, from minute)]] - course.build.json "days", else filled by hours"""
    hour = float(prog.get("academic_hour_min") or 45)
    given = sheet.get("days")
    by = {m["n"]: m for m in mods}
    if given:
        days, count = [], {}
        # a module number, or {"module": 14, "minutes": 80} for the part of a module the day holds
        entry = lambda x: (x.get("module"), x.get("minutes")) if isinstance(x, dict) else (x, None)
        for d in given:
            for x in d:
                count[entry(x)[0]] = count.get(entry(x)[0], 0) + 1
        seen, at = {}, {}
        for d in given:
            row = []
            for x in d:
                n, mins = entry(x)
                if n not in by:
                    probs.append("course.build.json \"days\" names module %s, which is not an approved module" % n)
                    continue
                seen[n] = seen.get(n, 0) + 1
                k, of = seen[n], count[n]
                take = float(mins) if mins else (by[n]["minutes"] - at.get(n, 0.0)) / (of - k + 1)
                row.append((by[n], take, k, of, at.get(n, 0.0)))
                at[n] = at.get(n, 0.0) + take
            days.append(row)
        for n, used in at.items():
            if abs(used - by[n]["minutes"]) > 0.5:
                probs.append("course.build.json \"days\" gives module %s %s min, its script %s min" % (n, num(used), num(by[n]["minutes"])))
        return days
    cap = float(prog.get("max_hours_per_day") or 8) * hour
    days, row, used = [], [], 0.0
    for m in mods:
        left, at, parts = m["minutes"], 0.0, []
        while left > 1e-6:
            room = cap - used
            if room <= 1e-6:
                days.append(row)
                row, used = [], 0.0
                continue
            take = min(left, room)
            parts.append([m, take, 0, 0, at])
            row.append(parts[-1])
            used += take
            at += take
            left -= take
        for k, p in enumerate(parts, 1):
            p[2], p[3] = k, len(parts)
    if row:
        days.append(row)
    days = [[tuple(p) for p in d] for d in days]
    want = prog.get("days")
    if want and final_min is not None and len(days) != int(want):
        probs.append("the modules fill %d day(s) of %s academic hours, the programme says %s days - set course.build.json "
                     "\"days\" if the timetable differs" % (len(days), num(cap / hour), want))
    return days


def day_of(days, m, minute):
    """the day (1-based) a minute of a module falls on"""
    for d, row in enumerate(days, 1):
        for mm, take, k, of, at in row:
            if mm is m and at - 1e-6 <= minute < at + take - 1e-6:
                return d
    return len(days) or 1


# ------------------------------------------------------------------ one document, two formats
# A document is a list of blocks: ("h1"|"h2"|"h3"|"p"|"small", text), ("facts", [(label, value)]), ("ul"|"ol", [items]),
# ("table", [head], [[cells]] (, [Word column widths])). Text is plain; a cell or item may be a list of lines. "<b>" from answer_key is kept bold.
def inline_html(x):
    if isinstance(x, (list, tuple)):
        return "<br>".join(inline_html(y) for y in x)
    return str(x) if isinstance(x, H) else e(x)


def to_html(title, blocks, lang="en", screen=False, viewer=False):
    """screen: a tablet page that stands alone (no script, no link but to its module's papers - the instructor's viewer
    shows it and closes it); it says so with <meta name="gb-standalone">, so check_navigation does not call it a trap
    (Project Management, 2026-11-06: every module failed navigation on advanced_module_plan.html). viewer: a paper the
    module plan opens in that viewer - the same mark, the paper's A4 print style"""
    o = ["<!DOCTYPE html>", '<html lang="%s">' % lang, "<head>",
         "<!-- GENERATED by course-factory %s additional_materials.py - never edit by hand: change the course files "
         "and build again -->" % cm.plugin_version(), '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">', "<title>%s</title>" % e(title)]
    if screen or viewer:
        o.append('<meta name="gb-standalone" content="viewer">')
    o += ["<style>%s</style>" % (CSS + (SCREEN_CSS if screen else PAPER_CSS)), "</head>", "<body>", '<div class="wrap">']
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            o.append("<%s>%s</%s>" % (k, inline_html(b[1]), k))
        elif k == "p":
            o.append("<p>%s</p>" % inline_html(b[1]))
        elif k == "small":
            o.append('<p class="small">%s</p>' % inline_html(b[1]))
        elif k == "card":
            o.append('<div class="card%s">' % ((" " + b[1]) if b[1] else ""))
        elif k == "end":
            o.append("</div>")
        elif k == "facts":
            o.append('<table class="facts">%s</table>' % "".join("<tr><th>%s</th><td>%s</td></tr>" % (e(l), inline_html(v)) for l, v in b[1]))
        elif k in ("ul", "ol"):
            o.append("<%s>%s</%s>" % (k, "".join("<li>%s</li>" % inline_html(x) for x in b[1]), k))
        elif k == "table":
            o.append('<table class="grid"><tr>%s</tr>%s</table>' % ("".join("<th>%s</th>" % e(h) for h in b[1]), "".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % inline_html(c) for c in r) for r in b[2])))
    o += ["</div>", "</body>", "</html>", ""]
    return "\n".join(o)


def _runs(text, size=None):
    out = []
    parts = re.split(r"</?b>", str(text)) if isinstance(text, H) else [str(text if text is not None else "")]
    for i, part in enumerate(parts):
        if isinstance(text, H):
            part = html.unescape(re.sub(r"<[^>]+>", "", part))
        if part:
            rpr = ("<w:b/>" if i % 2 else "") + ('<w:sz w:val="%d"/>' % size if size else "")
            out.append('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % ("<w:rPr>%s</w:rPr>" % rpr if rpr else "",
                                                                         html.escape(part, quote=False)))
    return "".join(out)


def _p(text, style=None, size=None, num_id=None):
    ppr = ('<w:pStyle w:val="%s"/>' % style if style else "") + \
          ('<w:numPr><w:ilvl w:val="0"/><w:numId w:val="%d"/></w:numPr>' % num_id if num_id else "")
    return "<w:p>%s%s</w:p>" % ("<w:pPr>%s</w:pPr>" % ppr if ppr else "", _runs(text, size))


def _cell(x, head=False, width=None):
    lines = x if isinstance(x, (list, tuple)) else [x]
    paras = "".join(_p(b_(y) if head else y, size=20) for y in lines) or "<w:p/>"
    shade = '<w:shd w:val="clear" w:color="auto" w:fill="E6F5FE"/>' if head else ""
    return "<w:tc><w:tcPr>%s%s</w:tcPr>%s</w:tc>" % ('<w:tcW w:w="%d" w:type="dxa"/>' % width if width else "", shade, paras)


def _table(rows, widths, head=True):
    borders = "".join('<w:%s w:val="single" w:sz="4" w:space="0" w:color="D3DBE5"/>' % s
                      for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    return ('<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>%s</w:tblBorders>'
            '<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            '<w:tblGrid>%s</w:tblGrid>%s</w:tbl><w:p/>' % (
                borders, "".join('<w:gridCol w:w="%d"/>' % x for x in widths),
                "".join("<w:tr>%s</w:tr>" % "".join(_cell(c, head and i == 0, w_) for c, w_ in zip(r, widths))
                        for i, r in enumerate(rows))))


def to_docx(blocks, out):
    body, full, ols = [], 9638, 0             # A4 less 2 cm margins, in twentieths of a point
    for b in blocks:
        k = b[0]
        if k in ("h1", "h2", "h3"):
            body.append(_p(b[1], style={"h1": "Title", "h2": "Heading1", "h3": "Heading2"}[k]))
        elif k in ("p", "small"):
            body.append(_p(b[1], size=18 if k == "small" else None))
        elif k == "facts":
            body.append(_table([[b_(l), v] for l, v in b[1]], [2600, full - 2600], head=False))
        elif k in ("ul", "ol"):
            ols += k == "ol"                  # every numbered list is its own, counting from 1
            body += [_p(x if not isinstance(x, (list, tuple)) else x[0], num_id=1 if k == "ul" else 1 + ols) for x in b[1]]
        elif k == "table":
            n = len(b[1])
            widths = b[3] if len(b) > 3 else [full // n] * n if n != 4 else [700, 2600, 2400, full - 5700]
            body.append(_table([b[1]] + list(b[2]), widths))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s"><w:body>%s'
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" '
           'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>' % (cs.W, "".join(body)))
    write_docx(doc, out, ols)


def write_docx(doc, out, ols=1):
    """content_script's Word package, with bullets, numbered lists that each start at 1 and a second heading"""
    W_ = cs.W
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="%s">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="80"/></w:pPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:rPr><w:b/><w:color w:val="0A2463"/><w:sz w:val="36"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="320" w:after="120"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="0A2463"/><w:sz w:val="28"/></w:rPr></w:style>'
              '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="415C8F"/><w:sz w:val="24"/></w:rPr></w:style>'
              '</w:styles>' % W_)
    numbering = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="%s">'
                 '<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="360" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
                 '<w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%%1."/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="360" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>'
                 '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>%s</w:numbering>' % (W_, "".join(
                     '<w:num w:numId="%d"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/>'
                     '</w:lvlOverride></w:num>' % (2 + i) for i in range(max(1, ols)))))
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in (("[Content_Types].xml", ct), ("_rels/.rels", rels), ("word/document.xml", doc),
                           ("word/styles.xml", styles), ("word/numbering.xml", numbering), ("word/_rels/document.xml.rels", drels)):
            z.writestr(zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)


CSS = ("*{box-sizing:border-box}body{margin:0;background:#fff;color:#011111;font:15px/1.5 Raleway,'Segoe UI',Calibri,Arial,"
       "sans-serif}.wrap{max-width:960px;margin:0 auto;padding:18px 18px 48px}h1{color:#0A2463;font-size:26px;margin:0 0 6px}"
       "h2{color:#0A2463;font-size:20px;margin:26px 0 8px;border-bottom:2px solid #2EB6F8;padding-bottom:4px}"
       "h3{color:#415C8F;font-size:16.5px;margin:18px 0 6px}p{margin:0 0 8px}ul,ol{margin:0 0 10px;padding-left:1.3em}"
       "li{margin:0 0 3px}.small{font-size:12.5px;color:#41556A}table{border-collapse:collapse;width:100%;margin:0 0 14px}"
       "th,td{border:1px solid #D3DBE5;padding:6px 8px;text-align:left;vertical-align:top}th{background:#E6F5FE;color:#0A2463}"
       "table.facts th{width:28%}.card{border:1px solid #D3DBE5;border-left:5px solid #2EB6F8;border-radius:10px;"
       "padding:10px 14px;margin:0 0 12px}.card.task{border-left-color:#E9A51E}.card.room{border-left-color:#12805A}"
       ".card h3{margin-top:0}")
SCREEN_CSS = "body{font-size:17px}th,td{font-size:16px}"
PAPER_CSS = "@page{size:A4;margin:16mm}@media print{.wrap{max-width:none;padding:0}h2,h3{break-after:avoid}tr,li{break-inside:avoid}}"


# ------------------------------------------------------------------ the course plan
def course_plan(course, title, arch, prog, sheet, mods, days, subs, v, today):
    w = W
    hour = prog.get("academic_hour_min") or 45
    tot = (prog.get("total_row") or {}).get("total")
    facts = [(w["programme"], " · ".join(x for x in ((arch.get("course") or {}).get("title_programme"), sheet.get("programme")) if x) or title)]
    for label, val in ((w["standard"], prog.get("standard") or sheet.get("regulation")), (w["model"], prog.get("model_course")),
                       (w["duration"], w["hours"].format(h=tot, m=hour, d=len(days)) if tot else None),
                       (w["language"], (arch.get("course") or {}).get("course_language"))):
        if val:
            facts.append((label, val))
    g = prog.get("group") or {}
    if g.get("theory_max"):
        facts.append((w["group"], w["group_v"].format(t=g.get("theory_max"), p=g.get("practical_per_instructor", "-"))))
    for label, key in ((w["rooms"], "rooms"), (w["equipment"], "equipment")):
        d = {k: x for k, x in (prog.get(key) or {}).items() if k != "ref"}
        if d:
            facts.append((label, ["%s - %s" % (k, x) for k, x in d.items()]))
    fa = arch.get("final_assessment") or {}
    if fa.get("questions"):
        facts.append((w["assessment"], w["assessment_v"].format(q=fa["questions"], p=fa.get("pass_mark", "-"))))
    blocks = [("h1", w["acp"]), ("p", b_(title)), ("facts", facts)]
    mains = arch.get("main_ilos") or []
    en = ilo_map.english(prog, arch)["main"]
    said = lambda x: en.get(str(x.get("id"))) or x.get("text")         # L19: English, the programme's words when it has none
    if mains:
        blocks += [("h2", w["main_ilos"]), ("ol", [said(x) for x in mains])]
    main_by = {str(x.get("id")): said(x) for x in mains}
    for d, row in enumerate(days, 1):
        blocks.append(("h2", w["day"].format(n=d)))
        objs = []
        for m, *_ in row:
            for i in m["main_ilos"]:
                t = main_by.get(str(i))
                if t and (i, t) not in objs:
                    objs.append((i, t))
        if objs:
            order = [str(x.get("id")) for x in mains]
            objs.sort(key=lambda x: order.index(str(x[0])) if str(x[0]) in order else len(order))
            blocks += [("h3", w["objectives"]), ("ol", [t for _, t in objs])]
        rows, qs = [], []
        for m, take, k, of, at in row:
            tasks = m["tasks"]
            sc = [t["code"] for t in tasks if t["kind"] == "self-check"]
            tt = [t["code"] for t in tasks if t["kind"] == "team"]
            method = [w["presentation"].format(n=sum(1 for s in m["script"]["screens"] if s.get("kind") in cs.INSTRUCTOR))]
            if sc:
                method.append(w["self_checks"].format(codes=", ".join(sc)))
            if tt:
                method.append(w["team"].format(codes=", ".join(tt)))
            for t in tasks:
                if t["where"] != "tablet" and at - 1e-6 <= t["start"] < at + take - 1e-6:
                    method.append(w["exercise"].format(code=t["code"], title=t["title"]) + " - " + w["where"][t["where"]])
            if any(t["kind"] == "module-check" for t in tasks) and k == of:
                method.append(w["module_check"])
            ids = []
            for t in tasks:
                ids += [i for i in t["sub_ilos"] if i not in ids]
            for s in m["script"]["screens"]:
                ids += [i for i in cs.sub_ilos_of(s) if i not in ids]
            desc = ["%s %s" % (i, subs[i]) if i in subs else i for i in ids]
            used = []                  # each source by its title - the sections it is cited for stay in the script
            for x in m["script"].get("sources") or []:
                x = re.split(r":\s", str(x).strip(), maxsplit=1)[0].strip()
                if x and x not in used:
                    used.append(x)
            topic = (m["script"].get("title") or m["title"])
            notes = [H("<b>%s:</b> %s %d - %s" % (e(w["title"]), e(w["module"]), m["n"], e(topic))),
                     w["minutes_day"].format(m=num(take)) + ((" (" + w["part"].format(k=k, n=of) + ")") if of > 1 else ""),
                     b_(w["description"] + ":")] + ["- " + x for x in desc] + \
                    ([b_(w["used"] + ":")] + ["- " + x for x in used] if used else [])
            rows.append([str(m["n"]), topic, method, notes])
            if k == 1:
                qs += [q.get("question") for t in tasks if t["kind"] == "module-check" for q in t["questions"][:2]]
        if d == len(days) and fa:
            rows.append(["", w["final"], [w["assessment_v"].format(q=fa.get("questions", "-"), p=fa.get("pass_mark", "-"))],
                         [fa.get("built_by") or ""]])
        blocks.append(("table", w["cols"], rows))
        if qs:
            blocks += [("h3", w["questions"]), ("ol", qs)]
    for key, head in (("literature", "literature"), ("films", "films")):
        d = {k: x for k, x in (prog.get(key) or {}).items() if k != "ref"}
        if d:
            blocks += [("h2", w[head]), ("ul", ["%s - %s" % (k, x) for k, x in d.items()])]
    blocks += [("p", H("<b>%s:</b> %s" % (e(w["responsible"]), e(sheet.get("responsible") or w["responsible_blank"])))),
               ("small", w["made"].format(v=v, d=today))]
    return blocks


# ------------------------------------------------------------------ the module plan
def module_plan(m, days, subs, v):
    w, script = W, m["script"]
    screens = [s for s in script["screens"] if s.get("kind") in cs.INSTRUCTOR]
    slide_no, _, _ = cs.plan_of(script)
    hour = m.get("hour") or 45
    on = sorted({d for d, row in enumerate(days, 1) for p in row if p[0] is m})
    meta = [w["time"].format(m=num(m["minutes"]), h=num(m["minutes"] / hour))] + [w["on_days"].format(d=d) for d in on]
    blocks = [("h1", w["mplan"].format(n=m["n"])), ("p", H("<b>%s</b> · %s" % (e(m["title"]), e(w["instr"])))), ("p", " · ".join(meta))]
    ids = []
    for t in m["tasks"]:
        ids += [i for i in t["sub_ilos"] if i not in ids]
    for s in screens:
        ids += [i for i in cs.sub_ilos_of(s) if i not in ids]
    can = [subs[i] for i in ids if i in subs]
    if can:
        blocks += [("card", ""), ("h3", w["can"]), ("ul", can), ("end",)]
    prep = []
    for t in m["tasks"]:
        p = t.get("practical") or {}
        if p:
            prep.append("%s: %s%s" % (t["code"], p.get("equipment") or "", (" - " + p["place"]) if p.get("place") else ""))
    codes = [t["code"] for t in m["tasks"] if t["where"] == "tablet"]
    if codes:
        prep.append(w["tablets"].format(codes=", ".join(codes)))
    for s in screens:
        if s.get("visual_kind") == "video_real" and s.get("visual"):
            prep.append(w["film"].format(n=slide_no[s["id"]], what=s["visual"]))
    if prep:
        blocks += [("card", ""), ("h3", w["prepare"]), ("ul", prep), ("end",)]
    by_slide = {t["slide"]["id"]: t for t in m["tasks"]}
    later = {p["slide"]["id"] for t in m["tasks"] for p in t["parts"][1:]}     # a practical's parts are its one step
    k, group = 0, []

    def teach_step(group, start):
        nonlocal k
        if not group:
            return []
        k += 1
        end = start + sum(cs.minutes(s) for s in group)
        out = [("card", ""), ("h3", "%s · %s" % (w["step"].format(k=k), w["mins"].format(a=num(start), b=num(end)))),
               ("p", b_(w["teach"])), ("ol", ["%s (%s)" % (s.get("title"), w["min"].format(m=num(cs.minutes(s)))) for s in group])]
        act = ["%s - %s" % (s.get("title"), w["active"].get(s["active"], w["active"]["other"]))
               for s in group if isinstance(s.get("active"), str)]
        if act:
            out += [("p", b_(w["they_do"])), ("ul", act)]
        return out + [("end",)]

    start, day = 0.0, None
    for s in screens:
        if s["id"] in later:
            continue
        now = day_of(days, m, start + sum(cs.minutes(x) for x in group)) if len(on) > 1 else None
        if now != day:                              # a module over two days says where each day starts
            blocks += teach_step(group, start)
            start += sum(cs.minutes(x) for x in group)
            group, day = [], now
            blocks.append(("h2", w["on_days"].format(d=now)))
        if s["id"] in by_slide:
            blocks += teach_step(group, start)
            start += sum(cs.minutes(x) for x in group)
            group = []
            t = by_slide[s["id"]]
            k += 1
            head = "%s · %s · %s %s - %s" % (w["step"].format(k=k), w["mins"].format(a=num(start), b=num(start + t["minutes"])),
                                             w["kinds"][t["kind"]], t["code"], t["title"])
            blocks += [("card", "task" if t["where"] == "tablet" else "room"), ("h3", head)]
            if t["questions"]:
                blocks.append(("p", w["questions_n"].format(n=len(t["questions"]))))
            lines = cs.lines_of(s.get("text"))
            if len(t["parts"]) > 1:
                blocks += [("p", b_(w["parts"])), ("ol", ["%s (%s)%s" % (p["title"], w["min"].format(m=num(p["minutes"])),
                                                                         (" - " + w["part_roles"][role(p)]) if role(p) != "do" else "")
                                                         for p in t["parts"]])]
                lines = []
            if lines:
                blocks += [("p", b_(w["say"] if t["where"] == "tablet" else w["steps"])), ("ul", lines)]
            notes = ["%s%s" % (("%s: " % p["code"]) if len(t["parts"]) > 1 else "", x[2:].strip())
                     for p in t["parts"] for x in cs.note_lines(p["slide"].get("notes"))]
            if notes:
                blocks += [("p", b_(w["you"])), ("ul", notes)]
            if t["where"] in ("simulator", "equipment"):
                a = lambda f, label: '<a href="%s">%s</a>' % (html.escape("papers/" + t["stem"] + f), e(label))
                blocks.append(("p", H("<b>%s:</b> %s (%s) · %s (%s)" % (
                    e(w["papers"]), a("_TRAINEE.html", w["trainee_card"]), a("_TRAINEE.pdf", "PDF"),
                    a("_INSTRUCTOR.html", w["instructor_sheet"]), a("_INSTRUCTOR.pdf", "PDF")))))
            blocks.append(("end",))
            start += t["minutes"]
        else:
            group.append(s)
    blocks += teach_step(group, start)
    blocks.append(("small", w["plan_made"].format(m=m["mid"], v=v)))
    return blocks


# ------------------------------------------------------------------ one task on paper
def steps(lines, numbered=True):
    """a list of lines; lines that carry their own numbers are printed as they are - a numbered list would count twice"""
    if any(OWN_NUMBER.match(x) for x in lines):
        return [("p", x) for x in lines]
    return [("ol" if numbered else "ul", lines)]


STEM_TITLE = 40


def stem_title(title):
    """a paper's file name part from its title: whole words, at most STEM_TITLE letters - a long title made a path past the
    260 characters Windows allows in a deep folder (the code beside it keeps each name its own)"""
    s = cm.slug(title)
    if len(s) <= STEM_TITLE:
        return s
    cut = s[:STEM_TITLE + 1].rsplit("_", 1)[0]
    return cut if cut and "_" in s[:STEM_TITLE + 1] else s[:STEM_TITLE]


def place_line(p):
    """the practical's place and equipment in English: equipment the course files hold only in the programme's language
    is left out and named by the programme's codes"""
    eq, codes = cf.english_equipment(p, None)
    if not eq and codes:
        eq = W["equip_codes"].format(codes=", ".join(codes))
    return " - ".join(x for x in (cf.english(p.get("place"), None), eq) if x)


def practical_parts(t, trainee):
    """a practical of several screens, part by part: the trainee card holds what the trainees do, the instructor sheet
    every part - the brief, the demonstration and the debrief marked as the instructor's - with its notes"""
    out = [("h2", W["steps"] if trainee else W["how_runs"])]
    for p in t["parts"]:
        r = role(p)
        if trainee and r != "do":
            continue
        out.append(("h3", " · ".join([p["title"], W["min"].format(m=num(p["minutes"]))] + ([W["part_roles"][r]] if r != "do" else []))))
        out += steps(cs.lines_of(p["slide"].get("text")))
        notes = [x[2:].strip() for x in cs.note_lines(p["slide"].get("notes"))]
        if notes and not trainee:
            out += [("p", b_(W["you"])), ("ul", notes)]
    return out


MODEL_SOURCE = re.compile(r"model course", re.I)
MODEL_PAREN = re.compile(r"\(((?:IMO )?(?:MC|Model Course) \d+\.\d+[^)]*)\)", re.I)


def criteria_and_sources(m, t):
    """the instructor sheet's last part: the approved instructor_led.json's criteria for the Sub-ILOs it serves (must pass
    and its step marked) and what each part's debrief must observe; the IMO model course's part in it; the module's
    sources - each as the approved files say it"""
    w, data = W, m.get("il") or {}
    out, crit = [], []
    for i in t["sub_ilos"]:
        for c in ((data.get("register") or {}).get(i) or {}).get("criteria") or []:
            c = c if isinstance(c, dict) else {"text": str(c)}
            if not str(c.get("text") or "").strip():
                continue
            extra = [w["must_pass"]] if c.get("must_pass") else []
            at = re.match(r"^\s*M\d+\.(\w+)\s+(\d+)\s*$", str(c.get("step") or ""))
            if at:
                extra.append(w["at_step"].format(n=at.group(2), code=at.group(1).upper()))
            crit.append(H("<b>%s</b> %s%s" % (e(i), e(c["text"]), (" - <b>%s</b>" % e(", ".join(extra))) if extra else "")))
    for p in t["parts"]:
        entry = (data.get("practicals") or {}).get(il.key(m["mid"], p["slide"]["id"])) or {}
        crit += [H("<b>%s</b> %s" % (e(w["observe"].format(code=p["code"])), e(x)))
                 for x in (entry.get("debrief") or {}).get("must_observe") or [] if str(x).strip()]
    if crit:
        out += [("h3", w["criteria"]), ("ul", crit)]
    srcs = [str(x) for x in m["script"].get("sources") or [] if str(x).strip()]
    words = " ".join(str(x or "") for p in t["parts"] for x in (p["slide"].get("title"), p["slide"].get("text"))) + \
        " " + str((t.get("practical") or {}).get("task") or "")
    model = [x for x in srcs if MODEL_SOURCE.search(x)] + [x for x in MODEL_PAREN.findall(words)]
    if model:
        out += [("h3", w["model_ref"]), ("ul", list(dict.fromkeys(model)))]
    rest = [x for x in srcs if x not in model]
    if rest:
        out += [("h3", w["sources_h"]), ("ul", rest)]
    return out


def form_paper(form, trainee):
    """an approved exercise form as the paper: its own fields in its own order - the short ones as the facts, the rest
    each under its own heading (the performance criteria, the steps from the simulator's manual ...)"""
    d = form["trainee" if trainee else "instructor"]
    short = lambda v: isinstance(v, (str, int, float)) and len(str(v)) <= 160
    facts = [(k, str(v)) for k, v in d.items() if not str(k).startswith("_") and short(v)]
    blocks = [("h1", "%s %s" % (W["trainee_card"] if trainee else W["instructor_sheet"], form["no"])),
              ("p", b_(d.get("Title") or "")), ("facts", facts)]
    for k, v in d.items():
        if str(k).startswith("_") or short(v) or v in (None, "", []):
            continue
        blocks.append(("h2", k[:1] + k[1:].lower() if k.isupper() else k))
        if isinstance(v, dict):
            v = ["%s: %s" % (a, b) for a, b in v.items()]
        blocks += steps([str(x) for x in v] if isinstance(v, list) else [str(v)], numbered=False)
    blocks.append(("small", W["form_made"].format(no=form["no"])))
    return blocks + ([("small", W["no_answers"]), ("p", W["sign"])] if trainee else [])


def task_paper(m, t, course_title, subs, trainee=False):
    w = W
    if t.get("form"):
        return form_paper(t["form"], trainee)
    facts = [(w["course"], course_title), (w["module"], "%d - %s" % (m["n"], m["title"])),
             (w["code"], "%s - %s" % (t["code"], t["title"])), (w["kind"], w["kinds"][t["kind"]]),
             (w["minutes"], w["min"].format(m=num(t["minutes"])))]
    place = place_line(t.get("practical") or {})
    if place:
        facts.append((w["place"], place))
    team = t["slide"].get("team")
    if isinstance(team, dict) and team:
        facts.append((w["kinds"]["team"], w["team_v"].format(size=team.get("size", "-"), roles=", ".join(cs.team_roles(team)) or "-")))
    blocks = [("h1", "%s %s" % (w["trainee_card"] if trainee else w["task"], t["code"])), ("p", b_(t["title"])), ("facts", facts)]
    if t["sub_ilos"]:
        blocks += [("h2", w["outcomes"]), ("ul", ["%s %s" % (i, subs.get(i, "")) for i in t["sub_ilos"]])]
    grouped = len(t.get("parts") or []) > 1
    lines = cs.lines_of(t["slide"].get("text"))
    if grouped:
        blocks += practical_parts(t, trainee)
    elif lines:
        blocks.append(("h2", w["intro"] if t["questions"] else w["steps"]))
        blocks += [("ul", lines)] if t["questions"] else steps(lines)
    sheet = m["build"].get("screens") or {}
    for n, q in enumerate(t["questions"], 1):
        mech = cs.mech(q)
        blocks += [("h3", w["how_q"].format(n=n, t=len(t["questions"]), how=cs.mech_label(mech, "en"))), ("p", q.get("question"))]
        if q.get("visual"):
            blocks.append(("small", w["shows"].format(x=q["visual"])))
        opts = q.get("options") or []
        if opts and mech in OPTION_MECHS + ("compare",):
            pairs = list(zip(cs.letters(len(opts)), opts))
            if mech != "compare":
                pairs = tp.shuffle(q["id"], pairs, key=lambda x: x[1])
            blocks.append(("ul", [H("<b>%s</b> - %s" % (L, e(o))) for L, (_, o) in zip(cs.letters(len(pairs)), pairs)]))
        if not trainee:
            info = [H("<b>%s:</b> %s" % (e(w["answer"]), "; ".join(ak.right_answer(q, sheet.get(q["id"]) or {}, ak.WORDS["en"]))))]
            if q.get("feedback"):
                info.append(H("<b>%s:</b> %s" % (e(w["feedback"]), e(q["feedback"]))))
            if q.get("bloom"):
                info.append(w["level"].format(b=q["bloom"]))
            blocks.append(("ul", info))
    if trainee:
        return blocks + [("small", w["no_answers"]), ("p", w["sign"])]
    notes = [] if grouped else [x[2:].strip() for x in cs.note_lines(t["slide"].get("notes"))]
    blocks.append(("h2", w["instructor_h"]))
    if notes:
        blocks += [("h3", w["notes"]), ("ul", notes)]
    if t["kind"] == "final":
        pm = tp.pass_mark_for(m["script"], m["build"], t["code"]) or 0
        mark = w["mark_final"].format(p=pm, need=-(-len(t["questions"]) * pm // 100), total=len(t["questions"]))
    else:
        mark = {"self-check": w["mark_self"], "team": w["mark_self"], "module-check": w["mark_check"]}.get(t["kind"], w["mark_room"])
    blocks += [("h3", w["marking"]), ("p", mark)]
    return blocks + (criteria_and_sources(m, t) if t["where"] != "tablet" else [])


# ------------------------------------------------------------------ the practical kit (L68)
def kit(course, title, mods, days, root, probs):
    """the pre-brief, debrief and observation cards and the assessment forms of every practical the approved
    instructor_led.json names, by day, and the employer sheet - [(path, kind, payload)]"""
    data = il.load(course)
    if not data:
        return []
    if not il.approved(data):
        probs.append("instructor_led.json is not approved - the practical kit (cards, assessment forms, employer sheet) waits for it")
        return []
    pracs = data.get("practicals") or {}
    out = []
    pair = lambda path, name, doc: [(path + ".pdf", "pdf", to_html(name, doc)), (path + ".docx", "docx", doc)]
    for m in mods:
        for t in [p for x in m["tasks"] for p in x["parts"]]:          # a screen of a practical has its own cycle
            entry = pracs.get(il.key(m["mid"], t["slide"]["id"])) if t["slide"].get("kind") == "activity" else None
            if not entry:
                continue
            base = os.path.join(root, "practical-kit", "Day_%d" % day_of(days, m, t["start"]), t["stem"])
            code = "%s %s - %s" % (m["mid"], t["code"], t["title"])
            out += pair(base + "_PREBRIEF", "%s - %s" % (W["prebrief"], code), prebrief_card(entry, code))
            out += pair(base + "_DEBRIEF", "%s - %s" % (W["debrief"], code), debrief_card(entry, code))
            if entry.get("recorded"):
                out += pair(base + "_ASSESSMENT", "%s - %s" % (W["form"], code), assessment_form(entry, code))
    emp = data.get("employer") or {}
    if any(emp.get(k) for k in ("can_do", "decays", "drill", "watch_for", "refresher")):
        out += pair(os.path.join(root, "practical-kit", "EMPLOYER_SHEET_" + cm.slug(title)), "%s - %s" % (W["employer"], title),
                    employer_sheet(emp, title))
    return out


def _rows_min(entry, kind):
    return sum(float(r.get("min") or 0) for r in il.cycle_rows(entry) if r.get("kind") == kind)


def prebrief_card(entry, code):
    pb = entry.get("prebrief") or {}
    pr = W["recorded_v"].format(c=entry.get("changed_condition") or "-") if entry.get("recorded") else W["practice_v"]
    safety = pb.get("safety") or []
    facts = [(W["objective"], pb.get("objective") or ""), (W["p_or_r"], pb.get("practice_or_recorded") or pr),
             (W["roles"], pb.get("roles") or ""), (W["safety"], safety if isinstance(safety, list) else [safety]),
             (W["stop_word"], W["stop_v"].format(w=pb.get("stop_word") or "STOP")),
             (W["will_do"], pb.get("intervention") or il.KNOW["cards"]["intervention_default"])]
    return [("h1", W["prebrief"]), ("p", b_(code)), ("p", W["prebrief_sub"].format(code=code.split(" - ")[0], m=num(_rows_min(entry, "brief")))),
            ("facts", facts)]


def debrief_card(entry, code):
    db = entry.get("debrief") or {}
    d = il.KNOW["cards"]["debrief_default"]
    items = [x for x in db.get("must_observe") or [] if str(x).strip()]
    rows = [[W["reactions"], db.get("reactions") or d["reactions"]], [W["observe_items"], ["%d. %s" % (i, x) for i, x in enumerate(items, 1)]],
            [W["prompt_1"], db.get("prompt_1") or d["prompt_1"]], [W["prompt_2"], db.get("prompt_2") or d["prompt_2"]],
            [W["feedback_form"], db.get("feedback") or d["feedback"]], [W["close"], db.get("close") or d["close"]]]
    watch = [x for x in entry.get("observe") or items if str(x).strip()]
    return [("h1", W["debrief"]), ("p", b_(code)), ("p", W["debrief_sub"].format(code=code.split(" - ")[0], m=num(_rows_min(entry, "debrief")))),
            ("table", [W["stage"], W["script"]], rows),
            ("h2", W["obs"]), ("table", W["obs_cols"], [[x, "", ""] for x in watch])]


def assessment_form(entry, code):
    cards = il.KNOW["cards"]
    crit = [c for c in (entry.get("form") or {}).get("critical") or [] if isinstance(c, dict) and str(c.get("step") or "").strip()]
    rows = [[str(i), ("%s: %s" % (W["stop"], c["step"])) if c.get("stop") else c["step"], "☐", "☐", "☐"] for i, c in enumerate(crit, 1)]
    blocks = [("h1", W["form"]), ("p", b_(code)), ("p", W["form_sub"].format(code=code.split(" - ")[0])),
              ("facts", [(W["candidate"], W["blank"]), (W["assessor"], W["blank"])]),
              ("h2", W["critical"]), ("table", W["crit_cols"], rows), ("small", W["crit_rule"]),
              ("h2", W["global"]), ("ul", ["☐ " + x for x in cards["global_rating"]]),
              ("h2", W["decision_h"]), ("p", cards["decision"])]
    if entry.get("gwo"):
        blocks += [("h2", W["gwo"]), ("p", W["gwo_v"])]
    details = [cards["run_details"]] + ([W["changed"].format(c=entry["changed_condition"])] if entry.get("changed_condition") else [])
    return blocks + [("h2", W["details"]), ("ul", details), ("p", W["sign"])]


def employer_sheet(emp, title):
    lst = lambda x: x if isinstance(x, list) else [x]
    decays = emp.get("decays") or ""
    if decays and "comparable training" not in decays:
        decays = [decays, il.KNOW["cards"]["decay_default"]]
    facts = [(W["can_now"], lst(emp.get("can_do") or [])), (W["decays"], decays), (W["drill"], emp.get("drill") or ""),
             (W["watch"], lst(emp.get("watch_for") or [])), (W["refresher"], emp.get("refresher") or "")]
    return [("h1", W["employer"]), ("p", b_(title)), ("facts", facts)]


# ------------------------------------------------------------------ the PDF
def browser():
    import measure_slides
    return measure_slides.find_browser()


def print_pdf(exe, src, out):
    import browser_slots
    prof = tempfile.mkdtemp(prefix="cf_pdf_")
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.isfile(out):
            os.remove(out)
        browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                           "--user-data-dir=" + prof, "--print-to-pdf=" + out, Path(src).as_uri()],
                          capture_output=True, timeout=120)
        return os.path.isfile(out) and os.path.getsize(out) > 0
    except (OSError, subprocess.TimeoutExpired):
        return False
    finally:
        shutil.rmtree(prof, ignore_errors=True)


# ------------------------------------------------------------------ the build
def papers_list(tasks):
    """papers.json of a module's papers folder: each paper's code, name and kind and its four files, in teaching order"""
    return json.dumps({"papers": [
        {"id": t["code"], "title": t["title"], "kind": t["where"],
         "trainee": {"html": t["stem"] + "_TRAINEE.html", "pdf": t["stem"] + "_TRAINEE.pdf"},
         "instructor": {"html": t["stem"] + "_INSTRUCTOR.html", "pdf": t["stem"] + "_INSTRUCTOR.pdf"}} for t in tasks]},
        ensure_ascii=False, indent=2) + "\n"


def plan(course, infos, title, probs):
    """everything to write - [(path, kind, payload)], and the modules (for compile_course's module plans)"""
    arch = load_or(workspace.claude_path(course, "architecture.json"), {})
    prog = load_or(workspace.claude_path(course, "programme.json"), {})
    sheet = load_or(workspace.claude_path(course, "course.build.json"), {})
    plan_j = load_or(workspace.claude_path(course, "plan.json"), {})
    lang = (arch.get("course") or {}).get("course_language") or "English"
    if (cm.lang_code(lang) or lang.lower()) != "en":           # said on every build, not a stop: the course's words are
        print("Note: the course is in %s - the additional materials' headings and labels exist in English only so far; "
              "the course's own words are as approved" % lang)
    no_en = []
    subs = sub_ilo_texts(course, arch, no_en)
    en = ilo_map.english(prog, arch)["main"]
    no_en = ["Main ILO %s" % x.get("id") for x in arch.get("main_ilos") or [] if not en.get(str(x.get("id")))] + no_en
    if no_en:
        probs.append("the programme is in %s and %s %s no English rendering - the ACP and the module plans show the programme's "
                     "words. Write the English in architecture.json beside them (\"text_en\" of a Main ILO or Sub-ILO), then build "
                     "again (L19: everything in the course is English)"
                     % (prog.get("language"), ", ".join(no_en), "has" if len(no_en) == 1 else "have"))
    mods = modules_of(course, arch, infos, probs)
    il_data = il.load(course)
    for m in mods:
        m["hour"] = float(prog.get("academic_hour_min") or 45)
        m["tasks"] = tasks_of(m, sheet)
        m["il"] = il_data if il.approved(il_data or {}) else {}
        for t in m["tasks"]:
            if t["where"] == "tablet":
                continue
            form = exercise_form(course, m, t)
            if form:                                   # the approved form is the paper (simulator exercises, L66)
                t["form"] = form
                t["where"] = t["kind"] = classify(json.dumps(form, ensure_ascii=False), (sheet.get("paper_tasks") or {}).get(
                    "%s.%s" % (m["mid"], t["code"])))
            p = t.get("practical") or {}
            if (p.get("equipment") or p.get("equipment_en")) and not cf.english_equipment(p)[0]:
                probs.append("%s %s: its practical's equipment is in the programme's language only - the papers name the "
                             "programme's codes; write \"equipment_en\" beside it in architecture.json" % (m["mid"], t["code"]))
    final = sum(float(x.get("hours") or 0) for x in plan_j.get("outside_modules") or []) * float(prog.get("academic_hour_min") or 45)
    days = days_of(mods, prog, sheet, final, probs) if mods else []
    v = cm.plugin_version()
    today = max([str(m["script"].get("approved_on") or "") for m in mods] or [""])    # the newest approval: a rebuild is the same
    root = os.path.join(course, FOLDER)
    out = []
    if mods:
        cp = course_plan(course, title, arch, prog, sheet, mods, days, subs, v, today)
        stem = "ACP_" + cm.slug(title)
        out.append((os.path.join(course, workspace.MODULES, COURSE_PLAN), "html", to_html(W["acp"] + " - " + title, cp, screen=True)))
        out.append((os.path.join(root, "acp", stem + ".html"), "html", to_html(W["acp"] + " - " + title, cp)))
        out.append((os.path.join(root, "acp", stem + ".docx"), "docx", cp))
    for m in mods:
        out.append((os.path.join(course, workspace.MODULES, m["code"], MODULE_PLAN), "html",
                    to_html("%s - %s" % (W["mplan"].format(n=m["n"]), m["title"]), module_plan(m, days, subs, v), screen=True)))
        listed = []
        for t in m["tasks"]:
            doc = task_paper(m, t, title, subs)
            out.append((os.path.join(root, "practical-tasks", "pdf", t["stem"] + ".pdf"), "pdf", to_html("%s %s - %s" % (m["mid"], t["code"], t["title"]), doc)))
            out.append((os.path.join(root, "practical-tasks", "docx", t["stem"] + ".docx"), "docx", doc))
            if t["where"] in ("simulator", "equipment"):
                dd = os.path.join(root, "simulator-and-equipment", "Day_%d" % day_of(days, m, t["start"]))
                card = task_paper(m, t, title, subs, trainee=True)
                out.append((os.path.join(dd, t["stem"] + "_TRAINEE.pdf"), "pdf", to_html("%s %s - %s" % (m["mid"], t["code"], W["trainee_card"]), card)))
                out.append((os.path.join(dd, t["stem"] + "_TRAINEE.docx"), "docx", card))
                out.append((os.path.join(dd, t["stem"] + "_INSTRUCTOR.pdf"), "pdf", to_html("%s %s - %s" % (m["mid"], t["code"], t["title"]), doc)))
                # the same two papers on the instructor's tablet: the module plan opens each, and its PDF is there to print
                pd = os.path.join(course, workspace.MODULES, m["code"], PAPERS, t["stem"])
                for who, name, d in (("_TRAINEE", W["trainee_card"], card), ("_INSTRUCTOR", t["title"], doc)):
                    page = to_html("%s %s - %s" % (m["mid"], t["code"], name), d, viewer=True)
                    out += [(pd + who + ".html", "html", page), (pd + who + ".pdf", "pdf", page)]
                listed.append(t)
        if listed:                                     # the instructor app reads each paper's name and kind from this list
            out.append((os.path.join(course, workspace.MODULES, m["code"], PAPERS, PAPERS_LIST), "json", papers_list(listed)))
    out += kit(course, title, mods, days, root, probs)
    # the instructor-only classroom files the tablet app reads on publish (classroom_files.py): the Prepare lists and the
    # recorded runs' assessment forms - in the modules folder, beside _course_shell, never in additional-materials
    out += cf.files(course, title, infos, mods, il.load(course), il)
    if mods:
        out.append((os.path.join(root, "INDEX.html"), "html", to_html(W["index"], index_blocks(title, root, out, mods))))
    return out, mods, days


def index_blocks(title, root, out, mods):
    rel = lambda p: os.path.relpath(p, root).replace("\\", "/")
    link = lambda p: H('<a href="%s">%s</a>' % (html.escape(rel(p)), e(os.path.basename(p))))
    acp = [link(p) for p, k, _ in out if rel(p).startswith("acp/")]
    tasks = [t for m in mods for t in m["tasks"]]
    rows = []
    for m in mods:
        for t in m["tasks"]:
            rows.append([m["mid"], t["code"], t["title"], W["kinds"][t["kind"]],
                         H('<a href="practical-tasks/pdf/%s.pdf">PDF</a> · <a href="practical-tasks/docx/%s.docx">Word</a>' % (t["stem"], t["stem"]))])
    by_day = {}
    for p, k, _ in out:
        if rel(p).startswith("simulator-and-equipment/"):
            by_day.setdefault(rel(p).split("/")[1].replace("_", " "), []).append(link(p))
    blocks = [("h1", W["index"]), ("p", W["index_sub"].format(course=title)), ("h2", W["i_acp"]), ("ul", acp),
              ("h2", W["i_sim"])]
    if by_day:
        for d, items in by_day.items():
            blocks += [("h3", d), ("ul", items)]
    else:
        blocks.append(("p", W["i_none"]))
    kit_ = {}
    for p, k, _ in out:
        if rel(p).startswith("practical-kit/"):
            parts = rel(p).split("/")
            kit_.setdefault(parts[1].replace("_", " ") if len(parts) > 2 else "", []).append(link(p))
    blocks += [("h2", W["i_kit"])]
    if kit_:
        for d, items in sorted(kit_.items()):
            blocks += ([("h3", d)] if d else []) + [("ul", items)]
    else:
        blocks.append(("p", W["i_kit_none"]))
    blocks += [("h2", W["i_tasks"].format(n=len(tasks))), ("table", ["Module", "Task", "Title", "Kind", "Files"], rows),
               ("small", W["i_plans"])]
    return blocks


def build(course, infos, title, pdf=True, check=False, quiet=False):
    """write (or with check, only compare) everything - (written paths, problems)"""
    probs = []
    out, mods, days = plan(course, infos, title, probs)
    rec_p = workspace.claude_path(course, RECORD)
    rec = load_or(rec_p, {})
    files = rec.get("files") or {}
    src_dir = workspace.claude_path(course, "additional_materials")
    root = os.path.join(course, FOLDER)
    key = lambda p: os.path.relpath(p, course).replace("\\", "/")
    written, to_print, missing = [], [], []
    for path, kind, payload in out:
        k = key(path)
        if kind in ("html", "json"):
            text = payload
            same = os.path.isfile(path) and read(path) == text
            if check:
                if not same:
                    missing.append(k)
                continue
            if not same:
                write(path, text)
                written.append(path)
            files[k] = cm.sha(text)
        elif kind == "docx":
            sig = cm.sha(json.dumps(payload, ensure_ascii=False) + WRITER)      # a Word file is written again when its writer changes
            if check:
                if not os.path.isfile(path) or files.get(k) != sig:
                    missing.append(k)
                continue
            if files.get(k) != sig or not os.path.isfile(path):
                to_docx(payload, path)
                written.append(path)
            files[k] = sig
        else:
            sig = cm.sha(payload)
            if check:
                if not os.path.isfile(path) or files.get(k) != sig:
                    missing.append(k)
                continue
            rel = os.path.relpath(path, root)
            if rel.startswith(".."):                      # a paper on the tablet, beside its module plan (its name says the module)
                rel = os.path.join("tablet", os.path.basename(path))
            src = os.path.join(src_dir, rel)[:-4] + ".html"
            write(src, payload)
            if pdf and (files.get(k) != sig or not os.path.isfile(path)):
                to_print.append((src, path, k, sig))
            elif not pdf and not os.path.isfile(path):
                missing.append(k)
    if check:
        made = set(key(p) for p, _, _ in out)
        return [], probs + ["not built or out of date: %s" % k for k in missing] + \
            ["%s: the record names it, the course no longer makes it" % k for k in files if k not in made and os.path.isfile(os.path.join(course, k))]
    if to_print:
        exe = browser()
        if not exe:
            probs.append("no Chrome or Edge found - %d PDF file(s) were not printed (set CF_BROWSER)" % len(to_print))
        else:
            import browser_slots
            if not quiet:
                print("Printing %d PDF file(s) ..." % len(to_print))
            with concurrent.futures.ThreadPoolExecutor(max(1, browser_slots.count())) as pool:
                done = list(pool.map(lambda x: (x, print_pdf(exe, x[0], x[1])), to_print))
            for (src, path, k, sig), ok in done:
                if ok:
                    files[k] = sig
                    written.append(path)
                else:
                    probs.append("%s was not printed - the browser gave no PDF" % k)
    if not pdf and any(kind == "pdf" for _, kind, _ in out):
        probs.append("built without PDF files (--no-pdf) - build again without it before the folder is handed over")
    # a file this tool made before and no longer makes is moved aside, never deleted (L8)
    made = set(key(p) for p, _, _ in out)
    old = os.path.join(src_dir, "old", time.strftime("%Y-%m-%d"))
    for k in [k for k in files if k not in made]:
        p = os.path.join(course, k)
        if os.path.isfile(p):
            dst = os.path.join(old, k)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(p, dst)
            if not quiet:
                print("Moved aside (no longer made): %s -> %s" % (k, os.path.relpath(dst, course)))
        del files[k]
    rec["files"] = files
    cs.save(rec_p, rec)
    return written, probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--no-pdf", action="store_true", help="the HTML and Word files only")
    ap.add_argument("--check", action="store_true", help="say what is missing or out of date; write nothing")
    o = ap.parse_args(argv)
    import compile_course as cc
    course = workspace.work_folder(o.course, create=False)
    arch = load_or(workspace.claude_path(course, "architecture.json"), {})
    title = ((arch.get("course") or {}).get("title") or "").strip()
    if not title:
        print("Stopped - there is no approved architecture with a course title (working_claude\\architecture.json).")
        return 2
    root = os.path.join(course, workspace.MODULES)
    mods = sorted(d for d in (os.listdir(root) if os.path.isdir(root) else []) if cc.MODULE.match(d)
                  and not os.path.isfile(os.path.join(root, d, cm.DRAFT_MARK)))
    if not mods:
        print("Stopped - no built module folders (module01 ...) in\n    %s" % root)
        return 2
    probs = []
    sheet = load_or(workspace.claude_path(course, "course.build.json"), {})
    infos = cc.ordered(sheet, [cc.module_info(course, arch, m, probs) for m in mods], probs)
    written, more = build(course, infos, title, pdf=not o.no_pdf, check=o.check)
    probs += more
    if not o.check:
        print("Built %d file(s) in %s and the plan pages on the tablet" % (len(written), os.path.join(course, FOLDER))
              if written else "Nothing changed - every file is as the last build wrote it.")
    if probs:
        print("\nTo fix before it is handed over:" if not o.check else "\nNot in order:")
        for x in probs:
            print("  - " + x)
        return 1
    if o.check:
        print("The additional materials are complete and up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
