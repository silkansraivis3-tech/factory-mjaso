#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The Instructor-Led Course Development Guideline, checked on a course (L68, knowledge/instructor-led.json).

    instructor_led.py plan    <course> [--module 4]     BEFORE a module's script: each Sub-ILO's task type and the 1-2
                                                        TLAs to write its activities in (2.128.0), into the register
    instructor_led.py draft   <course>                  write or complete working_claude/instructor_led.json to fill in
    instructor_led.py check   <course> [--module 4]     the guideline's review checklist, module by module (section 7)
    instructor_led.py approve <course> --by "<name>"    the operator's yes to the course's instructor_led.json
    instructor_led.py status  <course>

WHAT IT CHECKS
The guideline's review checklist, item by item (knowledge/instructor-led.json "checklist"): what the factory can read from
the approved content scripts, the ILO map and the course's own instructor_led.json is checked here; what is checked
elsewhere (the Main ILOs word for word, every tablet question graded) is named with the place; what only a person can
judge (a sea story, written English in a scored item) is listed for the reviewer. Every "no" is either fixed or justified
in one line in instructor_led.json "justify" - the reviewer may reject the justification. A justified item is reported as
JUSTIFIED with its line, never as passed.

THE COURSE'S FILE (working_claude/instructor_led.json - written by the factory, approved by the operator)
    {"register":   {"10.b": {"task_type": "fixed_sequence", "must_know": ["The bump-test order"],
                             "lookup": [{"fact": "Each cargo's limit", "aid": "the SDS"}],
                             "evidence": {"practice": ["diagnostic plus two correct runs"], "scored": ["form steps 1-5"]},
                             "criteria": [{"text": "Takes a failed detector out of use", "must_pass": true, "step": "M05.A01 4"}],
                             "tla": ["Demonstration-performance (Peyton four-step)"]}},
     "practicals": {"M04.A01": {"team": false, "practice_runs": 2,
                                "cycle": [{"kind": "brief", "min": 4}, {"kind": "diagnostic", "min": 8},
                                          {"kind": "run", "min": 32}, {"kind": "debrief", "min": 11}],
                                "prebrief": {"objective": "...", "roles": "...", "safety": ["..."], "stop_word": "STOP",
                                             "intervention": "..."},
                                "debrief": {"must_observe": ["...", "...", "..."], "prompt_1": "...", "prompt_2": "..."}},
                    "M05.A01": {"recorded": true, "practice_of": "M04.A01", "changed_condition": "one planted fault of three",
                                "cycle": [...], "prebrief": {...}, "debrief": {...},
                                "form": {"critical": [{"step": "Checks the calibration date", "stop": false}, ...]}}},
     "must_pass":  ["q03", "q11", ...],                 the final's must-pass questions (its script's screen ids)
     "justify":    {"M02": {"C10": "Novices meeting the gas laws for the first time"}},
     "employer":   {"can_do": [...], "decays": "...", "drill": "...", "watch_for": [...], "refresher": "..."}}
A practical is keyed by its module and its activity screen's id, as additional_materials names it: "M04.A01". Every
simulator and real-equipment exercise needs one; a classroom exercise only when it is a drill or a team scenario (then
it is listed here). The cycle's rows add up to the activity screen's minutes exactly - brief and debrief come out of the
exercise's own time, never on top of it (R8, L1).

CHOSEN WHILE WRITING, NOT ONLY CHECKED (2.128.0, Aigars Kluga: "the factory ... cannot vary")
plan reads the ILO map before a module's script is written: each Sub-ILO's task type (the register's, or read from its
verb - knowledge/instructor-led.json "formats" "verbs") picks one or two TLAs near its Bloom level, varied across the
module (scripts/activity_formats.py), and the register gets them where it has none. The script then writes each
activity screen in its format ("format": the key). draft makes a practical for every activity that needs one - simulator,
equipment, and every room drill, team scenario and project block (the format's "practical") - with cycle rows that add
up to the screen's minutes and the cards' fields from the screen's own words or the format's catalogue entry; it fills the
register's task type, TLAs and evidence where they are empty. Everything it writes is a draft the operator approves.

Exit codes: check 0 nothing open, 1 an item is "no", 2 nothing to check. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import activity_formats as af  # noqa: E402  - the formats chosen while a module is written (2.128.0)
import bloom_map  # noqa: E402
import content_script as cs  # noqa: E402
import ilo_map  # noqa: E402
import workspace  # noqa: E402

KNOW = json.load(io.open(os.path.join(SKILL, "knowledge", "instructor-led.json"), encoding="utf-8"))
LIM = KNOW["limits"]
CHECKLIST = KNOW["checklist"]
TASK_TYPES = [k for k in KNOW["task_types"] if not k.startswith("_")]
CYCLE_KINDS = ("brief", "show", "diagnostic", "run", "debrief")
NAME = "instructor_led.json"
SCRIPT_FILE = re.compile(r"^(M\d\d|FINAL)\.json$")
APPROVAL = ("status", "approved_by", "approved_on", "approved_hash")


# ------------------------------------------------------------------ the course's file
def path(course):
    return workspace.claude_path(course, NAME)


def load(course):
    p = path(course)
    if not os.path.isfile(p):
        return {}
    try:
        d = cs.load(p)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def content_hash(d):
    body = {k: v for k, v in d.items() if k not in APPROVAL}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def approved(d):
    return bool(d) and d.get("status") == "approved" and d.get("approved_hash") == content_hash(d)


def key(mid, screen_id):
    return "%s.%s" % (mid, str(screen_id).upper())


def scripts(course):
    """[(mid, script)] - every content script of the course, in the course's order, the final last"""
    d = workspace.claude_path(course, "script")
    out = []
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if SCRIPT_FILE.match(f):
            try:
                out.append((f[:-5], cs.load(os.path.join(d, f))))
            except (OSError, ValueError):
                continue
    return sorted(out, key=lambda x: (x[0] == "FINAL", x[0]))


def course_files(course):
    rd = lambda n: (cs.load(workspace.claude_path(course, n)) if os.path.isfile(workspace.claude_path(course, n)) else {})
    return rd("architecture.json"), rd("programme.json"), rd("course.build.json")


# ------------------------------------------------------------------ R4, R5, R6 - the running order
def _cue(text, words):
    for w in words:
        if re.search(r"(?<!\w)" + re.escape(w), text or "", re.I):
            return w
    return None


def commit_of(s, lang="en"):
    """R4 on an active slide - (commits, the 'no' word that asks only the room or None)"""
    c = KNOW["commit"]
    if any(s.get(f) for f in c["fields"]):
        return True, None
    notes = s.get("notes") or ""
    yes = _cue(notes, c["yes"].get(lang) or c["yes"]["en"])
    no = _cue(notes, c["no"].get(lang) or c["no"]["en"])
    return bool(yes), no


def lang_of(script):
    return bloom_map.lang_code(script.get("course_language") or "English")


def passive(script):
    """the passive share of the theory minutes and the passive runs (R5, R6). A slide is passive when it is not active, or
    when it is marked active and names no output every trainee produces (R4: counted as the guideline counts it)."""
    lang = lang_of(script)
    sc = [s for s in script.get("screens", []) if s.get("kind") in cs.INSTRUCTOR]
    theory = [s for s in sc if s.get("kind") != "activity"]
    weak = []
    for s in theory:
        if s.get("kind") == "slide" and s.get("active"):
            ok, no = commit_of(s, lang)
            if not ok:
                weak.append((s["id"], no))
    weak_ids = {i for i, _ in weak}
    is_passive = lambda s: s.get("kind") == "slide" and (not s.get("active") or s["id"] in weak_ids)
    p_min = sum(cs.minutes(s) for s in theory if is_passive(s))
    t_min = sum(cs.minutes(s) for s in theory)
    runs, cur = [], []
    for s in sc:
        if is_passive(s):
            cur.append(s)
        else:
            if cur:
                runs.append((cur, True))
            cur = []
    if cur:
        runs.append((cur, False))                # the module ends on it: nothing follows
    runs = [{"ids": [s["id"] for s in r], "min": sum(cs.minutes(s) for s in r), "followed": f} for r, f in runs]
    longest = max(runs, key=lambda r: r["min"]) if runs else {"ids": [], "min": 0.0, "followed": True}
    return {"passive": p_min, "theory": t_min, "share": (p_min / t_min) if t_min else 0.0, "runs": runs,
            "longest": longest, "weak": weak}


# ------------------------------------------------------------------ R8, R9, R10 - the practicals
def activities(course, mid, script, arch, sheet):
    """[(key, screen, where)] - every activity of a module, and whether it is on the simulator, with equipment or in the
    room, by the same reading the additional materials make of it"""
    sys.path.insert(0, os.path.join(SKILL, "compile", "scripts"))
    import additional_materials as am            # here, not at the top: additional_materials reads this file
    am_mod = next((m for m in arch.get("modules") or [] if ilo_map.mkey(m.get("module")) == ilo_map.mkey(mid)), {})
    m = {"mid": mid, "script": script, "practicals": [x for x in am_mod.get("practicals") or [] if isinstance(x, dict)]}
    return [(key(mid, t["slide"]["id"]), t["slide"], t["where"]) for t in am.tasks_of(m, sheet) if t["slide"].get("kind") == "activity"]


def cycle_rows(entry):
    return [r for r in (entry or {}).get("cycle") or [] if isinstance(r, dict)]


def cycle_problems(entry, minutes_):
    """R8 - what is wrong with a practical's brief / show / run / debrief rows"""
    out = []
    rows = cycle_rows(entry)
    if not rows:
        return ["no brief / run / debrief rows (\"cycle\")"]
    bad = [r.get("kind") for r in rows if r.get("kind") not in CYCLE_KINDS]
    if bad:
        out.append("unknown row kind %s - use %s" % (", ".join(map(repr, bad)), ", ".join(CYCLE_KINDS)))
    num = lambda r: float(r.get("min") or 0)
    total = sum(num(r) for r in rows)
    if abs(total - minutes_) > 1e-6:
        out.append("the rows add up to %g min, the exercise has %g min - brief and debrief come out of its own time" % (total, minutes_))
    by = lambda k: [r for r in rows if r.get("kind") == k]
    lo, hi = LIM["brief_min"]
    if not by("brief"):
        out.append("no brief row")
    elif not lo <= sum(num(r) for r in by("brief")) <= hi:
        out.append("the brief is %g min - %d-%d min" % (sum(num(r) for r in by("brief")), lo, hi))
    if not by("run"):
        out.append("no run row")
    lo, hi = LIM["debrief_team_min" if entry.get("team") else "debrief_individual_min"]
    if not by("debrief"):
        out.append("no debrief row")
    elif not lo <= sum(num(r) for r in by("debrief")) <= hi:
        out.append("the debrief is %g min - %d-%d min for %s" % (sum(num(r) for r in by("debrief")), lo, hi,
                                                                 "a team drill or simulator run" if entry.get("team") else "an individual drill"))
    if entry.get("first_exposure", True) and not entry.get("recorded") and not (by("show") or by("diagnostic")):
        out.append("no show row on the first exposure (or a diagnostic row for an experienced group)")
    if not entry.get("recorded") and any(r.get("recorded") for r in by("run")):
        out.append("a practice run is marked recorded - the recorded run is a later run under a changed condition (R9)")
    return out


def card_problems(entry):
    """R10 and the cards - what the pre-brief and debrief cards still lack"""
    out = []
    pb, db = entry.get("prebrief") or {}, entry.get("debrief") or {}
    for f in ("objective", "roles", "safety", "stop_word"):
        if not pb.get(f):
            out.append("the pre-brief card has no %s" % f.replace("_", " "))
    lo, hi = LIM["must_observe_items"]
    n = len([x for x in db.get("must_observe") or [] if str(x).strip()])
    if not lo <= n <= hi:
        out.append("the debrief card has %d must-observe item(s) - %d-%d" % (n, lo, hi))
    return out


def form_problems(entry):
    """R12 - the assessment form of a recorded run"""
    crit = [c for c in (entry.get("form") or {}).get("critical") or [] if isinstance(c, dict) and str(c.get("step") or "").strip()]
    lo, hi = LIM["critical_steps"]
    out = []
    if not lo <= len(crit) <= hi:
        out.append("the assessment form has %d critical step(s) - %d-%d" % (len(crit), lo, hi))
    if crit and not any(c.get("stop") for c in crit):
        out.append("no stop criterion among the critical steps (\"stop\": true - recognises when to stop)")
    return out


# ------------------------------------------------------------------ the checklist
def _status(found, cid, mid, justify):
    """"no" with the problems, or "justified" with the line, or "yes" """
    if not found:
        return ("yes", [])
    why = ((justify.get(mid) or {}).get(cid) or "").strip()
    if not why:
        for c in CHECKLIST:                        # a justification may be keyed by the rule too: "R6"
            if c["id"] == cid:
                for r in re.findall(r"R\d+", c.get("rules") or ""):
                    why = why or ((justify.get(mid) or {}).get(r) or "").strip()
    return ("justified", found + ["justified: " + why]) if why else ("no", found)


def module_check(course, mid, script, data, arch, prog, sheet):
    """{checklist id: (status, [lines])} for one module"""
    res = {}
    justify = data.get("justify") or {}
    reg = data.get("register") or {}
    pracs = data.get("practicals") or {}
    lang = lang_of(script)
    rows = ilo_map.module_rows(ilo_map.read(course), mid)
    leaves = ilo_map.leaves(rows) if rows else []
    text_of = {str(r.get("sub_ilo_id")): r.get("sub_ilo") or "" for r in rows}
    if not leaves:
        for s in script.get("screens", []):
            leaves += [x for x in cs.sub_ilos_of(s) if x not in leaves]
    put = lambda cid, found: res.__setitem__(cid, _status(found, cid, mid, justify))

    # C2 - an observable verb and one task type; C3 - must-know listed, every other fact its aid; C5 - evidence named
    c2, c3, c5 = [], [], []
    for sid in leaves:
        r = reg.get(sid) or {}
        lv = bloom_map.ilo_level(text_of.get(sid) or "", lang) if text_of.get(sid) else None
        if lv and lv.get("weak"):
            c2.append("%s: %r cannot be watched - re-express the Sub-ILO with a verb an assessor can see" % (sid, lv["verb"]))
        if r.get("task_type") not in TASK_TYPES:
            c2.append("%s: no task type - one of %s" % (sid, ", ".join(TASK_TYPES)))
        if "must_know" not in r:
            c3.append("%s: no must-know list (an empty list when every fact is looked up)" % sid)
        for x in r.get("lookup") or []:
            if not (isinstance(x, dict) and str(x.get("aid") or "").strip()):
                c3.append("%s: a looked-up fact names no aid: %r" % (sid, x.get("fact") if isinstance(x, dict) else x))
        ev = r.get("evidence") or {}
        if not any(ev.get(k) for k in ("practice", "scored")):
            c5.append("%s: no evidence named - how will we see it, inside the hours, with our equipment?" % sid)
    put("C2", c2)
    put("C3", c3)
    c5_status = _status(c5, "C5", mid, justify)
    res["C5"] = (c5_status[0], c5_status[1] + ["by hand: the job test - does someone at this certificate level do this on board?"])

    # C4 - about one sub-outcome per allocated hour, at most five per outcome
    c4 = []
    hour = float(prog.get("academic_hour_min") or 45)
    hours = cs.minutes({"minutes": script.get("minutes_allocated")}) / hour
    cap = math.ceil(hours * 1.5 * LIM["sub_outcomes_per_hour"]) if hours else None
    if cap is not None and len(leaves) > max(cap, 1):
        c4.append("%d Sub-ILOs for %g allocated hour(s) - about one an hour; merge criteria written as Sub-ILOs" % (len(leaves), round(hours, 2)))
    per = {}
    for r in rows:
        if str(r.get("sub_ilo_id")) in leaves:
            for i in r.get("main_ilo_ids") or []:
                per.setdefault(str(i), []).append(str(r.get("sub_ilo_id")))
    for i, subs in per.items():
        if len(subs) > LIM["sub_outcomes_per_outcome_max"]:
            c4.append("Main ILO %s has %d Sub-ILOs - at most %d" % (i, len(subs), LIM["sub_outcomes_per_outcome_max"]))
    put("C4", c4)

    # C7 - minutes add up, the passive % on the plan's face
    sc = [s for s in script.get("screens", []) if s.get("kind") in cs.INSTRUCTOR]
    built = sum(cs.minutes(s) for s in sc)
    alloc = script.get("minutes_allocated")
    c7 = []
    if alloc in (None, ""):
        c7.append("the script states no allocated minutes")
    elif abs(cs.minutes({"minutes": alloc}) - built) > 1e-6:
        c7.append("the screens add up to %g min, the programme allocates %g min" % (built, cs.minutes({"minutes": alloc})))
    put("C7", c7)

    # C8 R4, C9 R5, C10 R6
    pv = passive(script)
    place = lambda sid: cs.place(script, sid)
    put("C8", ["%s: %s" % (place(i), ("asks only the room (%r) - every trainee writes, votes or answers first" % no) if no
                           else "the notes do not say what every trainee produces") for i, no in pv["weak"]])
    c9 = []
    for r in pv["runs"]:
        if r["min"] > LIM["passive_run_max_min"]:
            c9.append("%g min of passive theory in a row (%s) - at most %d, then a trainee output"
                      % (r["min"], ", ".join(place(i) for i in r["ids"]), LIM["passive_run_max_min"]))
        elif not r["followed"]:
            c9.append("the module ends on passive theory (%s) - no output follows it" % ", ".join(place(i) for i in r["ids"]))
    put("C9", c9)
    put("C10", ["passive %.0f %% of the theory minutes (%g of %g) - at most %.0f %%, or a one-line justification"
                % (100 * pv["share"], pv["passive"], pv["theory"], 100 * LIM["passive_share_max"])]
        if pv["share"] > LIM["passive_share_max"] + 1e-9 else [])

    # C12 R8, C13 R9, C14 R10, C19 R12, C23 the cards
    c12, c13, c14, c19, c23 = [], [], [], [], []
    keys, needed, entries, recorded = [], 0, 0, 0
    for k, s, where in activities(course, mid, script, arch, sheet):
        keys.append(k)
        e = pracs.get(k)
        needed += e is not None or where in ("simulator", "equipment")
        entries += e is not None
        recorded += bool((e or {}).get("recorded"))
        if e is None:
            if where in ("simulator", "equipment"):
                for lst in (c12, c23):
                    lst.append("%s (%s, %s): not in instructor_led.json \"practicals\"" % (k, s.get("title"), where))
            continue
        c12 += ["%s: %s" % (k, x) for x in cycle_problems(e, cs.minutes(s))]
        c23 += ["%s: %s" % (k, x) for x in card_problems(e)]
        if not (e.get("prebrief") or {}).get("stop_word"):
            c14.append("%s: the pre-brief card names no stop word" % k)
        if e.get("recorded"):
            po = e.get("practice_of")
            if not po:
                c13.append("%s: a recorded run with no practice run before it (\"practice_of\")" % k)
            elif po not in pracs:
                c13.append("%s: its practice run %s is not in \"practicals\"" % (k, po))
            elif not _before(po, k, course):
                c13.append("%s: its practice run %s does not come before it" % (k, po))
            if not str(e.get("changed_condition") or "").strip():
                c13.append("%s: no changed condition for the recorded run" % k)
            c19 += ["%s: %s" % (k, x) for x in form_problems(e)]
        elif int(e.get("practice_runs") or 0) < 2:
            c13.append("%s: %s practice run(s) per trainee - at least two after the first correct run"
                       % (k, e.get("practice_runs") or "no"))
    for k in pracs:
        if k.startswith(mid + ".") and k not in keys:
            c12.append("%s: in \"practicals\", but the module has no such activity" % k)
    for cid, found in (("C12", c12), ("C13", c13), ("C14", c14), ("C19", c19), ("C23", c23)):
        put(cid, found)
    na = lambda why: ("n/a", [why])                # nothing to judge is never reported as passed
    if not needed and not c12:
        for cid in ("C12", "C13", "C14", "C19", "C23"):
            res[cid] = na("no drill, simulator run or team scenario in this module")
    else:
        if not entries:
            for cid in ("C13", "C14"):
                res[cid] = na("waits for the module's practicals in instructor_led.json (C12)")
        if not recorded:
            res["C19"] = na("no recorded run in this module")

    # C6 - every must-pass criterion has its own form step
    c6 = []
    for sid in leaves:
        for c in (reg.get(sid) or {}).get("criteria") or []:
            if not (isinstance(c, dict) and c.get("must_pass")):
                continue
            ref = str(c.get("step") or "").split()
            if len(ref) != 2 or ref[0] not in pracs:
                c6.append("%s: must-pass %r names no form step (\"step\": \"M05.A01 4\")" % (sid, c.get("text")))
                continue
            crit = (pracs[ref[0]].get("form") or {}).get("critical") or []
            if not (ref[1].isdigit() and 1 <= int(ref[1]) <= len(crit)):
                c6.append("%s: must-pass %r - %s has no step %s" % (sid, c.get("text"), ref[0], ref[1]))
    put("C6", c6)
    if not any(isinstance(c, dict) and c.get("must_pass") for sid in leaves for c in (reg.get(sid) or {}).get("criteria") or []):
        res["C6"] = ("n/a", ["no must-pass criterion in this module's register"])

    # C24 - this module's misconceptions in the course list (the debrief tags)
    tags = workspace.claude_path(course, "script", "%s.debrief.json" % mid)
    has_tasks = any(s.get("kind") in cs.TASKS for s in script.get("screens", []))
    ms = {}
    if os.path.isfile(tags):
        try:
            ms = cs.load(tags).get("misconceptions") or {}
        except (OSError, ValueError):
            ms = {}
    c24 = _status([] if ms or not has_tasks else ["no misconception tags for this module's tasks (debrief_map.py draft)"], "C24", mid, justify)
    res["C24"] = (c24[0], c24[1] + ["by hand: the glossary"])

    # C26 - behaviour change, never accident reduction
    put("C26", claim_problems(script))
    return res


def _before(a, b, course):
    """a practical key comes before another - an earlier module, or an earlier screen of the same module"""
    ma, sa = a.split(".", 1)
    mb, sb = b.split(".", 1)
    if ma != mb:
        return (ma == "FINAL", ma) < (mb == "FINAL", mb)
    p = workspace.claude_path(course, "script", ma + ".json")
    try:
        ids = [str(s.get("id")).upper() for s in cs.load(p).get("screens", [])]
    except (OSError, ValueError):
        return False
    return sa in ids and sb in ids and ids.index(sa) < ids.index(sb)


def claim_problems(script, extra=()):
    rx = [re.compile(x, re.I) for x in KNOW["claims"]["no"]]
    out = []
    for s in script.get("screens", []):
        for f in ("title", "text", "notes", "question", "feedback"):
            for x in rx:
                m = x.search(str(s.get(f) or ""))
                if m:
                    out.append("%s %s: %r - claim behaviour change, not accident reduction" % (s.get("id"), f, m.group(0)))
    for label, text in extra:
        for x in rx:
            m = x.search(str(text or ""))
            if m:
                out.append("%s: %r - claim behaviour change, not accident reduction" % (label, m.group(0)))
    return out


def course_check(course, data, arch, scr):
    """{checklist id: (status, [lines])} for the course as a whole - the final's must-pass items, the employer sheet"""
    res = {}
    justify = data.get("justify") or {}
    final = dict(scr).get("FINAL")
    c20 = []
    if final:
        ids = {s.get("id") for s in final.get("screens", []) if s.get("kind") == "final"}
        mp = [x for x in data.get("must_pass") or []]
        lo, hi = LIM["must_pass_per_course"]
        if not lo <= len(mp) <= hi:
            c20.append("%d must-pass question(s) in the final - %d-%d per course" % (len(mp), lo, hi))
        c20 += ["must-pass %r is not a question of the final" % x for x in mp if x not in ids]
        pm = final.get("pass_mark") or (arch.get("final_assessment") or {}).get("pass_mark")
        n = re.search(r"\d+", str(pm or ""))
        if not n or int(n.group(0)) < LIM["pass_mark"]:
            c20.append("the final's pass mark is %s - the programme's %d %%" % (pm or "not stated", LIM["pass_mark"]))
    else:
        c20.append("no final assessment script yet")
    st = _status(c20, "C20", "course", justify)
    res["C20"] = (st[0], st[1] + ["by hand: vignette or key-feature items; three surface variants per decision; the final does not "
                                  "yet fail a candidate on one must-pass question - the marking is the training app's"])
    emp = data.get("employer") or {}
    c25 = []
    if not 3 <= len([x for x in emp.get("can_do") or [] if str(x).strip()]) <= 5:
        c25.append("\"can_do\": three to five things the trainee can now do, as the company can observe them")
    for f, what in (("decays", "what decays fastest"), ("drill", "one on-board drill at 1-3 months"), ("refresher", "the refresher position")):
        if not str(emp.get(f) or "").strip():
            c25.append("\"%s\": %s" % (f, what))
    if not 2 <= len([x for x in emp.get("watch_for") or [] if str(x).strip()]) <= 3:
        c25.append("\"watch_for\": two or three behaviours on board that show the training held")
    res["C25"] = _status(c25, "C25", "course", justify)
    res["C26"] = _status(claim_problems({"screens": []}, [("employer " + k, v if isinstance(v, str) else " ".join(map(str, v)))
                                                          for k, v in emp.items()]), "C26", "course", justify)
    return res


def check(course, only=None):
    """(report rows, open count) - rows: [(where, checklist item, status, lines)]"""
    data = load(course)
    arch, prog, sheet = course_files(course)
    scr = scripts(course)
    rows, n_open = [], 0
    items = {c["id"]: c for c in CHECKLIST}
    for mid, script in scr:
        if mid == "FINAL" or (only is not None and ilo_map.mkey(mid) != ilo_map.mkey(only)):
            continue
        res = module_check(course, mid, script, data, arch, prog, sheet)
        for c in CHECKLIST:
            if c["id"] in res:
                st, lines = res[c["id"]]
                rows.append((mid, c, st, lines))
                n_open += st == "no"
    if only is None:                               # the course as a whole, and once: what is checked elsewhere or by hand
        res = course_check(course, data, arch, scr)
        for c in CHECKLIST:
            if c["id"] in res:
                st, lines = res[c["id"]]
            elif c["how"] == "elsewhere":
                st, lines = "elsewhere", [c.get("by", "")]
            elif c["how"] == "hand":
                st, lines = "hand", []
            else:
                continue
            rows.append(("course", items[c["id"]], st, lines))
            n_open += st == "no"
    return rows, n_open


MARK = {"yes": "yes      ", "no": "NO       ", "justified": "JUSTIFIED", "elsewhere": "elsewhere", "hand": "by hand  ",
        "n/a": "n/a      "}


def report(rows):
    out, last = [], None
    for where, c, st, lines in rows:
        if where != last:
            out.append("\n%s" % ("Course" if where == "course" else where))
            last = where
        out.append("  %s  %-4s %s%s" % (MARK[st], c["id"], c["item"], (" (%s)" % c["rules"]) if c.get("rules") else ""))
        out += ["               - %s" % x for x in lines if x]
    return "\n".join(out)


# ------------------------------------------------------------------ draft, approve, status
def experienced(arch):
    return str((arch.get("course") or {}).get("course_type") or "").upper() == "EXPERIENCED"


def leaf_rows(m, mid):
    """the ILO map rows of a module's Sub-ILOs (the leaves), in the map's order"""
    rows = ilo_map.module_rows(m, mid)
    ids = set(ilo_map.leaves(rows)) if rows else set()
    return [r for r in rows if str(r.get("sub_ilo_id")) in ids]


def ilo_modules(m):
    """the modules of the ILO map, in order ("M01" ...; the final is not one)"""
    out = []
    for r in (m or {}).get("rows") or []:
        k = ilo_map.mkey(r.get("module")) if isinstance(r, dict) else None
        if isinstance(k, int) and "M%02d" % k not in out:
            out.append("M%02d" % k)
    return sorted(out)


def _empty_row():
    return {"task_type": "", "must_know": [], "lookup": [], "evidence": {"practice": [], "scored": []}, "criteria": [], "tla": []}


def _tla_names(keys):
    return [af.label(k) for k in keys if af.get(k) and k != af.UNNAMED["key"]]


def plan(course, only=None, write=True):
    """[(mid, [{sid, text, task_type, source, level, picks}])] - BEFORE a module's script is written: each Sub-ILO's task
    type and the TLAs its activities are to be written in, varied across the module. The register gets the task type and
    the TLA names where it has none (a draft - the operator approves the file); what is set is never changed."""
    data = load(course)
    arch, _, _ = course_files(course)
    reg = data.setdefault("register", {})
    m = ilo_map.read(course)
    lang = bloom_map.lang_code((arch.get("course") or {}).get("course_language") or "English")
    out, changed = [], 0
    for mid in ilo_modules(m):
        if only is not None and ilo_map.mkey(mid) != ilo_map.mkey(only):
            continue
        rows = af.plan(leaf_rows(m, mid), reg, lang, experienced(arch))
        out.append((mid, rows))
        for p in rows:
            r = reg.setdefault(p["sid"], _empty_row())
            if not r.get("task_type"):
                r["task_type"], r["_task_type_from"] = p["task_type"], p["source"]
                changed += 1
            if not r.get("tla"):
                r["tla"] = _tla_names(p["picks"])
                changed += 1
    if write and changed:
        if data.get("status") == "approved":
            data["status"] = "draft"
        cs.save(path(course), data)
    return out


def plan_report(out):
    lines_ = []
    for mid, rows in out:
        lines_.append("\n%s - write its activities in these formats (\"format\" on an activity screen: the key in [ ])" % mid)
        for p in rows:
            lines_.append("  %s  %s (%s), Bloom %s - %s" % (p["sid"], af.KNOW["task_types"][p["task_type"]]["label"].lower(),
                                                       p["source"], p["level"], (p["text"] or "")[:90]))
            for k in p["picks"]:
                f = af.get(k)
                lines_.append("        [%s] %s - %s: %s" % (k, f["label"], f["drafts"], f["write"]))
    return "\n".join(lines_)


def _evidence(mid, script, final, sid):
    """{"practice": [...], "scored": [...]} - how the course already shows the Sub-ILO: the module's activities and tablet
    sets that name it, and the final's questions that name it"""
    practice, scored = [], []
    for s in script.get("screens", []):
        if sid not in cs.sub_ilos_of(s):
            continue
        if s.get("kind") == "activity":
            practice.append("%s - %s" % (key(mid, s["id"]), af.label(af.format_of(s))))
        elif s.get("kind") == "slide" and af.format_of(s) and commit_of(s, lang_of(script))[0]:
            practice.append("%s %s - %s, every trainee commits" % (mid, s["id"], af.label(af.format_of(s))))
        elif s.get("kind") in ("self-check", "module-check") and s.get("set"):
            x = "%s %s on the tablet" % (mid, s["set"])
            if x not in practice:
                practice.append(x)
    for s in (final or {}).get("screens", []):
        if s.get("kind") == "final" and sid in cs.sub_ilos_of(s):
            scored.append("final %s" % s.get("id"))
    return {"practice": practice, "scored": scored}


def draft(course):
    """write instructor_led.json, or add what it lacks, from the approved scripts and the ILO map: a register row per
    Sub-ILO (its task type from the verb, its TLAs from the formats the script used or picks, its evidence from the screens
    that name it - each only where empty), a practical per simulator or equipment exercise and per room drill, team
    scenario and project block (2.128.0), with cycle rows inside the screen's minutes. What the material does not give -
    must-know facts, a simulator's or equipment's safety, a recorded run's form - is left empty for the operator, never
    invented. -> (entries added, fields filled, [warnings])"""
    data = load(course)
    arch, prog, sheet = course_files(course)
    reg = data.setdefault("register", {})
    prac = data.setdefault("practicals", {})
    m = ilo_map.read(course)
    exp = experienced(arch)
    lang = bloom_map.lang_code((arch.get("course") or {}).get("course_language") or "English")
    scr = scripts(course)
    final = dict(scr).get("FINAL")
    added, filled, warns = 0, 0, []
    for mid, script in scr:
        if mid == "FINAL":
            continue
        rows = leaf_rows(m, mid)
        text_of = {str(r.get("sub_ilo_id")): r.get("sub_ilo_en") or r.get("sub_ilo") or "" for r in rows}
        picked = {p["sid"]: p for p in af.plan(rows, reg, lang, exp)}
        used = af.moments(script)
        for sid in text_of:
            if sid not in reg:
                reg[sid] = _empty_row()
                added += 1
            r = reg[sid]
            if not r.get("task_type"):
                r["task_type"], r["_task_type_from"] = picked[sid]["task_type"], picked[sid]["source"]
                filled += 1
            if not r.get("tla"):
                mine = [f for s, f in used if sid in cs.sub_ilos_of(s)]
                feats = [x for f in mine for x in (af.get(f) or {}).get("features") or []]
                r["tla"] = _tla_names(list(dict.fromkeys(mine + feats))) or _tla_names(picked[sid]["picks"])
                filled += 1
            ev = r.setdefault("evidence", {"practice": [], "scored": []})
            if not any(ev.get(k) for k in ("practice", "scored")):
                got = _evidence(mid, script, final, sid)
                if any(got.values()):
                    ev.update(got)
                    filled += 1
            r.setdefault("must_know", [])
        for k, s, where in activities(course, mid, script, arch, sheet):
            fmt = af.format_of(s)
            if not af.needs_practical(fmt, where):
                continue
            subs = [text_of.get(x) for x in cs.sub_ilos_of(s) if text_of.get(x)]
            crit = [c.get("text") for x in cs.sub_ilos_of(s) for c in (reg.get(x) or {}).get("criteria") or []
                    if isinstance(c, dict) and c.get("text")]
            new, w = af.practical(s, fmt, where, subs, crit, exp, minutes=cs.minutes(s))
            if k not in prac:
                prac[k] = new
                added += 1
                warns += ["%s: %s" % (k, x) for x in w]
                continue
            e = prac[k]                                   # fill only what is empty; what is there stays
            for f, v in new.items():
                if isinstance(v, dict):
                    have = e.setdefault(f, {})
                    for g, x in v.items():
                        if have.get(g) in (None, "", []):
                            have[g] = x
                            filled += 1
                elif e.get(f) in (None, "", []):
                    e[f] = v
                    filled += 1
            if not (e.get("prebrief") or {}).get("safety"):
                warns += ["%s: %s" % (k, x) for x in w if x.startswith("safety")]
    data.setdefault("must_pass", [])
    data.setdefault("justify", {})
    data.setdefault("employer", {"can_do": [], "decays": "", "drill": "", "watch_for": [], "refresher": ""})
    if (added or filled) and data.get("status") == "approved":
        data["status"] = "draft"
    cs.save(path(course), data)
    return added, filled, warns


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("plan", "draft", "check", "approve", "status"))
    ap.add_argument("course")
    ap.add_argument("--module")
    ap.add_argument("--by")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    course = workspace.work_folder(o.course, create=False)
    if o.cmd == "plan":
        if not ilo_map.read(course):
            print("No ILO map yet (working_claude/ilo_map.json) - the formats are picked from its Sub-ILOs")
            return 2
        out = plan(course, o.module)
        if o.json:
            print(json.dumps([{"module": mid, "sub_ilos": rows} for mid, rows in out], ensure_ascii=False, indent=1))
        else:
            print("Practical-activity formats, by Sub-ILO (L68, knowledge/instructor-led.json \"formats\") - a draft: the task "
                  "type is the operator's to confirm in %s" % path(course))
            print(plan_report(out))
        return 0
    if o.cmd == "draft":
        n, filled, warns = draft(course)
        print("%s: %d entr%s added, %d field%s filled from the scripts and the ILO map - check them (instructor-led/GUIDE.md)"
              % (path(course), n, "y" if n == 1 else "ies", filled, "" if filled == 1 else "s"))
        for w in warns:
            print("  to fill: " + w)
        return 0
    if o.cmd == "approve":
        if not o.by:
            print("approve needs --by \"<the operator's name>\"")
            return 2
        d = load(course)
        if not d:
            print("No %s yet - run draft first" % NAME)
            return 2
        d.update(status="approved", approved_by=o.by, approved_on=date.today().isoformat())
        d["approved_hash"] = content_hash(d)
        cs.save(path(course), d)
        print("instructor_led.json approved by %s" % o.by)
        return 0
    if o.cmd == "status":
        d = load(course)
        print("instructor_led.json: %s" % ("missing" if not d else "approved by %s on %s" % (d.get("approved_by"), d.get("approved_on"))
                                         if approved(d) else "changed since the approval" if d.get("approved_hash") else "not approved"))
        return 0
    if not scripts(course):
        print("No content script in %s - nothing to check" % workspace.claude_path(course, "script"))
        return 2
    rows, n_open = check(course, o.module)
    if o.json:
        print(json.dumps([{"where": w, "id": c["id"], "status": st, "lines": ls} for w, c, st, ls in rows], ensure_ascii=False, indent=1))
    else:
        print("The Instructor-Led Course Development Guideline - review checklist%s" % ("" if approved(load(course)) else
              " (instructor_led.json is %s)" % ("missing" if not load(course) else "not approved")))
        print(report(rows))
        print("\n%d item(s) open: fix each, or justify it in one line in instructor_led.json \"justify\"." % n_open if n_open
              else "\nNothing open.")
    return 1 if n_open else 0


if __name__ == "__main__":
    sys.exit(main())
