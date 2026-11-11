# -*- coding: utf-8 -*-
"""test_instructor_led - the Instructor-Led Course Development Guideline's review checklist, checked on a course (L68).

    python test_instructor_led.py

Pinned:
  * the knowledge file: twelve rules, 28 TLAs at most five per Bloom level, every checklist item auto, elsewhere or by hand;
    no active-learning pattern lets the class answer aloud (R4);
  * R4: an active slide whose notes only ask the room is counted passive; a vote, a true-or-false claim or a drill on the
    slide, or notes that say what every trainee produces, commit;
  * R5 and R6: a passive run over 15 min, a module ending on passive theory, a passive share over 20 % - each a "no"
    until fixed or justified in one line (by the checklist item or by the rule);
  * R8, R9, R10, R12 on the practicals: a simulator exercise needs brief / run / debrief rows that add up to its own
    minutes, a 3-5 min brief, a debrief of 15-20 min for a team and 5-10 alone, a show (or diagnostic) on first exposure,
    the cards' fields and stop word; a recorded run needs an earlier practice run, a changed condition and an assessment
    form of 8-12 critical steps with a stop criterion; a practice exercise at least two runs per trainee;
  * the register: an observable verb, one task type, must-know listed, every looked-up fact its aid, evidence named, at
    most five Sub-ILOs per outcome, every must-pass criterion its own form step;
  * the course: 6-8 must-pass questions in the final and its 70 % pass mark, the employer sheet complete, no claim of
    accident reduction;
  * the command line: draft adds what is missing without touching what is there, check exits 1 while an item is open,
    approve and status follow the file's hash.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import instructor_led as il  # noqa: E402

TOOL = os.path.join(HERE, "instructor_led.py")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def slide(sid, minutes, active=None, notes="- Explain.", **kw):
    s = {"id": sid, "kind": "slide", "title": "Slide " + sid, "text": "Words.", "visual_kind": "photo", "visual": "A photo.",
         "notes": notes, "minutes": minutes, "sub_ilo": kw.pop("sub_ilo", "1.a")}
    if active:
        s["active"] = active
    s.update(kw)
    return s


SIM = {"id": "a01", "kind": "activity", "title": "Practical - gas detection on the simulator", "sub_ilo": "1.b",
       "text": "Liquid cargo simulator, room K2.\nZero and bump-test the detector.", "notes": "- Pairs.", "minutes": 40}
TASKS = [{"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1", "text": "On your tablet.", "notes": "- OPEN TASK.", "minutes": 4},
         {"id": "q01", "kind": "self-check", "set": "SC1", "question": "Enter?", "options": ["No", "Yes"], "correct": "A",
          "feedback": "H2S is high.", "mechanic": "single_choice", "sub_ilo": "1.a"}]
M01 = [slide("s01", 10), slide("s02", 6),
       slide("s03", 5, "predict-then-reveal", "- Take three answers aloud, then reveal."),
       slide("s04", 5, "predict-then-reveal", "- Each trainee writes a prediction on a card; pairs compare."), SIM] + TASKS
M02 = [slide("s01", 2), slide("s02", 6, "scenario", "- Reveal the answer.", choices=["Enter", "Stop"], right="Stop"),
       dict(SIM, minutes=25, title="Recorded run - gas detection on the simulator")] + [dict(TASKS[0], minutes=5), TASKS[1]]
FINAL = [{"id": "q%02d" % i, "kind": "final", "question": "Q%d?" % i, "options": ["A", "B"], "correct": "A", "feedback": "-",
          "mechanic": "single_choice"} for i in range(1, 11)]
GOOD_CYCLE = [{"kind": "brief", "min": 4}, {"kind": "diagnostic", "min": 8}, {"kind": "run", "min": 20}, {"kind": "debrief", "min": 8}]
CARDS = {"prebrief": {"objective": "Zero and bump-test the detector.", "roles": "Pairs: one performs, one observes.",
                      "safety": ["Test gas vented to open air."], "stop_word": "STOP"},
         "debrief": {"must_observe": ["Bump test before use", "O2 read before %LEL", "A failed detector taken out of use"]}}
FORM = {"critical": [{"step": "Step %d" % i, "stop": i == 4} for i in range(1, 10)]}


def save_script(c, mid, screens, alloc=None, **kw):
    s = {"module": "final" if mid == "FINAL" else int(mid[1:]), "title": mid, "course_language": "English", "operator_language": "en",
         "minutes_allocated": alloc if alloc is not None else sum(cs.minutes(x) for x in screens if x["kind"] in cs.INSTRUCTOR),
         "status": "approved", "screens": json.loads(json.dumps(screens))}
    s.update(kw)
    cs.save(os.path.join(c, "working_claude", "script", mid + ".json"), s)


def course(tmp):
    c = os.path.join(tmp, "course")
    os.makedirs(os.path.join(c, "working_claude", "script"))
    os.makedirs(os.path.join(c, "to_review"))
    save_script(c, "M01", M01)
    save_script(c, "M02", M02)
    save_script(c, "FINAL", FINAL, alloc=20, pass_mark=70)
    wc = os.path.join(c, "working_claude")
    cs.save(os.path.join(wc, "architecture.json"), {"course": {"title": "Test", "course_language": "English"},
                                                    "modules": [{"module": 1}, {"module": 2}], "final_assessment": {"pass_mark": "70 %"}})
    cs.save(os.path.join(wc, "programme.json"), {"academic_hour_min": 40})
    rows = [{"module": "M01", "main_ilo_ids": ["1"], "sub_ilo_id": "1.a", "sub_ilo": "Decides whether a tank may be entered"},
            {"module": "M01", "main_ilo_ids": ["1"], "sub_ilo_id": "1.b", "sub_ilo": "Understand the gas detector"},
            {"module": "M02", "main_ilo_ids": ["1"], "sub_ilo_id": "2.a", "sub_ilo": "Bump-tests a portable detector"}]
    cs.save(os.path.join(wc, "ilo_map.json"), {"rows": rows})
    return c


def status(rows, where, cid):
    return next(((st, ls) for w, c, st, ls in rows if w == where and c["id"] == cid), (None, []))


def put(c, data):
    cs.save(il.path(c), data)


def main():
    tmp = tempfile.mkdtemp(prefix="instructor_led_")
    try:
        print("-- the knowledge file")
        K = il.KNOW
        check("twelve rules R1-R12", sorted(K["rules"], key=lambda x: int(x[1:])) == ["R%d" % i for i in range(1, 13)])
        pool = [t for k, v in K["tla_pool"].items() if not k.startswith("_") for t in v]
        by = {}
        for t in pool:
            by[t["bloom"]] = by.get(t["bloom"], 0) + 1
        check("the TLA pool holds 28, at most five per Bloom level", len(pool) == 28 and max(by.values()) <= 5, by)
        check("every TLA is under one of the four task types", set(k for k in K["tla_pool"] if not k.startswith("_")) == set(il.TASK_TYPES))
        check("every checklist item is auto, elsewhere (with its place) or by hand, C1-C26",
              [c["id"] for c in il.CHECKLIST] == ["C%d" % i for i in range(1, 27)]
              and all(c["how"] in ("auto", "hand") or (c["how"] == "elsewhere" and c.get("by")) for c in il.CHECKLIST))
        al = json.load(io.open(os.path.join(il.SKILL, "knowledge", "active-learning.json"), encoding="utf-8"))
        check("no active-learning pattern lets the class answer aloud (R4)",
              not any("aloud" in (p.get("does") or "") for p in al["patterns"].values()), [p["does"] for p in al["patterns"].values()])

        print("\n-- R4, R5, R6: the running order")
        s = {"course_language": "English", "screens": M01}
        pv = il.passive(s)
        check("an active slide that only asks the room counts as passive; one where each trainee writes does not",
              [i for i, _ in pv["weak"]] == ["s03"] and pv["weak"][0][1] == "aloud", pv["weak"])
        check("a vote between choices on the slide commits by itself",
              il.commit_of(slide("x", 3, "scenario", "- Reveal.", choices=["a", "b"]))[0])
        check("a pair or team output commits ('explain to a neighbour', 'teams of three, each team reports'); collecting a few "
              "predictions from the room does not - as read on a real course's notes",
              il.commit_of(slide("x", 3, "explain-then-reveal", "- Trainees explain to a neighbour before the reveal."))[0]
              and il.commit_of(slide("x", 3, "scenario", "- Teams of three; ten minutes; then each team reports one."))[0]
              and not il.commit_of(slide("x", 3, "predict-then-reveal", "- Collect predictions before you play it."))[0]
              and not il.commit_of(slide("x", 3, "explain-then-reveal", "- Take two or three explanations before you reveal."))[0])
        check("Latvian notes: 'katrs kursants uzraksta' commits",
              il.commit_of(slide("x", 3, "predict-then-reveal", "- Katrs kursants uzraksta prognozi."), "lv")[0])
        check("the passive share counts plain and weak-active slides over the theory minutes: 21 of 30",
              (pv["passive"], pv["theory"]) == (21.0, 30.0), pv)
        check("the longest passive run is s01-s03, 21 min, followed by an output",
              pv["longest"]["ids"] == ["s01", "s02", "s03"] and pv["longest"]["min"] == 21 and pv["longest"]["followed"], pv["longest"])
        end = il.passive({"screens": [slide("a", 3, "scenario", "- Each trainee votes on a card."), slide("b", 4)]})
        check("a module that ends on passive theory: its last run is not followed", end["runs"][-1]["followed"] is False, end)

        c = course(tmp)
        rows, n = il.check(c)
        check("C8 lists the active slide that only asks the room", status(rows, "M01", "C8")[0] == "no"
              and "asks only the room" in " ".join(status(rows, "M01", "C8")[1]), status(rows, "M01", "C8"))
        check("C9: 21 min of passive theory in a row is a no", status(rows, "M01", "C9")[0] == "no", status(rows, "M01", "C9"))
        check("C10: 70 % passive is a no", status(rows, "M01", "C10")[0] == "no" and "70 %" in status(rows, "M01", "C10")[1][0],
              status(rows, "M01", "C10"))
        check("M02 (a vote slide, 2 min plain of 13) passes C8, C9 and C10",
              [status(rows, "M02", x)[0] for x in ("C8", "C9", "C10")] == ["yes", "yes", "yes"], [status(rows, "M02", x) for x in ("C8", "C9", "C10")])
        check("C7: the minutes add up", status(rows, "M01", "C7")[0] == "yes", status(rows, "M01", "C7"))
        put(c, {"justify": {"M01": {"C10": "Novices meeting gas detection for the first time", "R5": "One concept, filmed"}}})
        rows, n = il.check(c)
        check("a one-line justification by the checklist item makes it JUSTIFIED, with the line shown",
              status(rows, "M01", "C10")[0] == "justified" and any("Novices" in x for x in status(rows, "M01", "C10")[1]))
        check("... and by the rule (R5 for C9)", status(rows, "M01", "C9")[0] == "justified", status(rows, "M01", "C9"))

        print("\n-- R8, R9, R10, R12: the practicals")
        check("a simulator exercise not in \"practicals\" is a no for C12 and C23",
              status(rows, "M01", "C12")[0] == "no" and "M01.A01" in status(rows, "M01", "C12")[1][0]
              and status(rows, "M01", "C23")[0] == "no", status(rows, "M01", "C12"))
        prac = {"M01.A01": dict(CARDS, cycle=GOOD_CYCLE, practice_runs=2),
                "M02.A01": dict(CARDS, recorded=True, practice_of="M01.A01", changed_condition="One planted fault of three",
                                cycle=[{"kind": "brief", "min": 3}, {"kind": "run", "min": 15}, {"kind": "debrief", "min": 7}], form=FORM)}
        base = {"practicals": prac}
        put(c, base)
        rows, n = il.check(c)
        check("a good practice and a good recorded run: C12, C13, C14, C19, C23 yes in both modules - C19 n/a in M01, no recorded run",
              all(status(rows, m, x)[0] == ("n/a" if (m, x) == ("M01", "C19") else "yes")
                  for m in ("M01", "M02") for x in ("C12", "C13", "C14", "C19", "C23")),
              [(m, x, status(rows, m, x)) for m in ("M01", "M02") for x in ("C12", "C13", "C14", "C19", "C23")])

        def one(mid, cid, change):
            d = json.loads(json.dumps(base))
            change(d["practicals"])
            put(c, d)
            r, _ = il.check(c)
            return status(r, mid, cid)

        st = one("M01", "C12", lambda p: p["M01.A01"]["cycle"].__setitem__(2, {"kind": "run", "min": 30}))
        check("rows that do not add up to the exercise's minutes", st[0] == "no" and "add up to 50 min" in " ".join(st[1]), st)
        st = one("M01", "C12", lambda p: p["M01.A01"].__setitem__("cycle", [{"kind": "brief", "min": 6}, {"kind": "show", "min": 6},
                                                                           {"kind": "run", "min": 20}, {"kind": "debrief", "min": 8}]))
        check("a 6-minute brief", st[0] == "no" and "brief is 6 min" in " ".join(st[1]), st)
        st = one("M01", "C12", lambda p: p["M01.A01"].__setitem__("team", True))
        check("a team run with an 8-minute debrief - 15-20", st[0] == "no" and "15-20" in " ".join(st[1]), st)
        st = one("M01", "C12", lambda p: p["M01.A01"].__setitem__("cycle", [{"kind": "brief", "min": 4}, {"kind": "run", "min": 28},
                                                                           {"kind": "debrief", "min": 8}]))
        check("no show or diagnostic on the first exposure", st[0] == "no" and "show row" in " ".join(st[1]), st)
        st = one("M01", "C12", lambda p: p["M01.A01"]["cycle"][2].__setitem__("recorded", True))
        check("a practice run marked recorded", st[0] == "no" and "R9" in " ".join(st[1]), st)
        st = one("M01", "C13", lambda p: p["M01.A01"].__setitem__("practice_runs", 1))
        check("one practice run per trainee - at least two", st[0] == "no", st)
        st = one("M02", "C13", lambda p: p["M02.A01"].pop("practice_of"))
        check("a recorded run with no practice run before it", st[0] == "no" and "practice_of" in " ".join(st[1]), st)
        st = one("M02", "C13", lambda p: p["M02.A01"].pop("changed_condition"))
        check("a recorded run with no changed condition", st[0] == "no" and "changed condition" in " ".join(st[1]), st)
        st = one("M01", "C13", lambda p: (p["M01.A01"].update(recorded=True, practice_of="M02.A01", changed_condition="x", form=FORM),
                                          p["M02.A01"].update(recorded=False, practice_runs=2)))
        check("a recorded run whose practice run comes after it", st[0] == "no" and "does not come before" in " ".join(st[1]), st)
        st = one("M02", "C19", lambda p: p["M02.A01"]["form"].__setitem__("critical", FORM["critical"][:7]))
        check("an assessment form of 7 critical steps - 8-12", st[0] == "no" and "8-12" in " ".join(st[1]), st)
        st = one("M02", "C19", lambda p: [x.__setitem__("stop", False) for x in p["M02.A01"]["form"]["critical"]])
        check("an assessment form with no stop criterion", st[0] == "no" and "stop criterion" in " ".join(st[1]), st)
        st = one("M01", "C14", lambda p: p["M01.A01"]["prebrief"].pop("stop_word"))
        check("a pre-brief card with no stop word (R10)", st[0] == "no", st)
        st = one("M01", "C23", lambda p: p["M01.A01"]["debrief"]["must_observe"].append("A fourth"))
        check("four must-observe items on the debrief card - two or three", st[0] == "no" and "2-3" in " ".join(st[1]), st)
        st = one("M01", "C12", lambda p: p.__setitem__("M01.A09", dict(CARDS, cycle=GOOD_CYCLE)))
        check("a practical the module does not have", st[0] == "no" and "M01.A09" in " ".join(st[1]), st)

        print("\n-- the register")
        put(c, base)
        rows, _ = il.check(c)
        st = status(rows, "M01", "C2")
        check("C2: 'Understand' cannot be watched, and no task type is set", st[0] == "no"
              and any(x.startswith("1.b") and "cannot be watched" in x for x in st[1]) and any("no task type" in x for x in st[1]), st)
        reg = {"1.a": {"task_type": "decision", "must_know": ["O2 21 % for entry"], "lookup": [{"fact": "Each cargo's limit", "aid": "the SDS"}],
                       "evidence": {"practice": ["retrieval round"], "scored": ["final must-pass item"]},
                       "criteria": [{"text": "Refuses entry when a reading fails", "must_pass": True, "step": "M02.A01 4"}]},
               "1.b": {"task_type": "fixed_sequence", "must_know": [], "evidence": {"practice": ["two correct runs"]}},
               "2.a": {"task_type": "fixed_sequence", "must_know": ["The bump-test order"], "evidence": {"scored": ["form steps 1-5"]}}}
        put(c, dict(base, register=reg))
        rows, _ = il.check(c)
        check("C2 lists only the weak verb once every task type is set",
              status(rows, "M01", "C2")[0] == "no" and len(status(rows, "M01", "C2")[1]) == 1, status(rows, "M01", "C2"))
        check("C3, C5 and C6 pass with the register filled",
              [status(rows, "M01", x)[0] for x in ("C3", "C5", "C6")] == ["yes", "yes", "yes"], [status(rows, "M01", x) for x in ("C3", "C5", "C6")])
        check("C5 still names the job test for the reviewer", any("job test" in x for x in status(rows, "M01", "C5")[1]))
        r2 = json.loads(json.dumps(reg))
        r2["1.a"]["lookup"].append({"fact": "The tube for benzene"})
        r2["1.a"]["criteria"][0]["step"] = "M02.A01 20"
        r2["1.b"].pop("must_know")
        put(c, dict(base, register=r2))
        rows, _ = il.check(c)
        check("C3: a looked-up fact with no aid, a Sub-ILO with no must-know list",
              status(rows, "M01", "C3")[0] == "no" and len(status(rows, "M01", "C3")[1]) == 2, status(rows, "M01", "C3"))
        check("C6: a must-pass criterion pointing at a form step that does not exist",
              status(rows, "M01", "C6")[0] == "no" and "no step 20" in status(rows, "M01", "C6")[1][0], status(rows, "M01", "C6"))
        m = cs.load(os.path.join(c, "working_claude", "ilo_map.json"))
        m["rows"] += [{"module": "M01", "main_ilo_ids": ["1"], "sub_ilo_id": "1.%s" % x, "sub_ilo": "Checks %s" % x} for x in "cdef"]
        cs.save(os.path.join(c, "working_claude", "ilo_map.json"), m)
        rows, _ = il.check(c)
        check("C4: six Sub-ILOs under one Main ILO, and more than one an hour", status(rows, "M01", "C4")[0] == "no"
              and len(status(rows, "M01", "C4")[1]) == 2, status(rows, "M01", "C4"))
        m["rows"] = m["rows"][:3]
        cs.save(os.path.join(c, "working_claude", "ilo_map.json"), m)

        bare = {"module": 3, "course_language": "English", "minutes_allocated": 10, "screens": [slide("s01", 6), TASKS[0], TASKS[1]]}
        res = il.module_check(c, "M03", bare, {}, *il.course_files(c))
        check("a module with no drill, run or scenario, and no must-pass criterion: n/a, never a yes",
              all(res[x][0] == "n/a" for x in ("C6", "C12", "C13", "C14", "C19", "C23")), {x: res[x] for x in ("C6", "C12", "C13", "C19")})
        res = il.module_check(c, "M01", cs.load(os.path.join(c, "working_claude", "script", "M01.json")), {}, *il.course_files(c))
        check("a simulator exercise not yet in the file: C12 and C23 no, C13 and C14 wait for it, C19 n/a",
              [res[x][0] for x in ("C12", "C23", "C13", "C14", "C19")] == ["no", "no", "n/a", "n/a", "n/a"],
              {x: res[x] for x in ("C12", "C13", "C19")})

        print("\n-- the course")
        put(c, base)
        rows, _ = il.check(c)
        check("C20: no must-pass questions marked", status(rows, "course", "C20")[0] == "no", status(rows, "course", "C20"))
        check("C25: no employer sheet", status(rows, "course", "C25")[0] == "no", status(rows, "course", "C25"))
        check("the items checked elsewhere and by hand are listed once, for the course",
              status(rows, "course", "C1")[0] == "elsewhere" and status(rows, "course", "C17")[0] == "hand"
              and status(rows, "M01", "C1")[0] is None)
        emp = {"can_do": ["Zero and bump-test a detector", "Sample at three levels", "Refuse entry when a reading fails"],
               "decays": "The bump-test order and the three entry numbers.", "drill": "15 minutes: bump test, then cue cards A and B.",
               "watch_for": ["Readings at three levels", "A standby who says no"], "refresher": "Revalidation does not retrain this skill."}
        put(c, dict(base, must_pass=["q01", "q02", "q03", "q04", "q05", "q06"], employer=emp))
        rows, _ = il.check(c)
        check("C20 and C25 pass: six must-pass questions of the final, 70 % pass mark, the employer sheet complete",
              [status(rows, "course", x)[0] for x in ("C20", "C25", "C26")] == ["yes", "yes", "yes"],
              [status(rows, "course", x) for x in ("C20", "C25", "C26")])
        check("... and C20 still says what the final does not yet do", any("training app" in x for x in status(rows, "course", "C20")[1]))
        put(c, dict(base, must_pass=["q01", "q02", "q03", "q04", "q05", "q99"], employer=dict(emp, drill="It reduces accidents on board.")))
        rows, _ = il.check(c)
        check("C20: a must-pass id that is not a question of the final", status(rows, "course", "C20")[0] == "no"
              and "q99" in " ".join(status(rows, "course", "C20")[1]))
        check("C26: the employer sheet claims accident reduction", status(rows, "course", "C26")[0] == "no", status(rows, "course", "C26"))
        save_script(c, "FINAL", FINAL, alloc=20, pass_mark=60)
        put(c, dict(base, must_pass=["q01", "q02", "q03", "q04", "q05", "q06"], employer=emp))
        rows, _ = il.check(c)
        check("C20: a 60 % pass mark", status(rows, "course", "C20")[0] == "no" and "60" in " ".join(status(rows, "course", "C20")[1]))
        save_script(c, "FINAL", FINAL, alloc=20, pass_mark=70)
        save_script(c, "M01", [dict(M01[0], notes="- This training prevents accidents.")] + M01[1:])
        rows, _ = il.check(c)
        check("C26: a slide's notes claim accident prevention", status(rows, "M01", "C26")[0] == "no", status(rows, "M01", "C26"))
        save_script(c, "M01", M01)

        print("\n-- the command line")
        os.remove(il.path(c))
        code, out = run("draft", c)
        d = il.load(c)
        check("draft writes the register rows, the simulator practicals and the course entries",
              code == 0 and set(d["register"]) == {"1.a", "1.b", "2.a"} and set(d["practicals"]) == {"M01.A01", "M02.A01"}
              and "employer" in d and d["practicals"]["M01.A01"]["prebrief"]["stop_word"] == "STOP", out)
        d["register"]["1.a"]["task_type"] = "decision"
        cs.save(il.path(c), d)
        code, out = run("draft", c)
        check("a second draft adds nothing and keeps what was filled in",
              "0 entries added" in out and il.load(c)["register"]["1.a"]["task_type"] == "decision", out)
        code, out = run("check", c)
        check("check exits 1 while an item is open, and says how to close it", code == 1 and "justify" in out and "NO" in out, out[-500:])
        code, out = run("check", c, "--module", "2")
        check("--module 2 reports module 2 only", code == 1 and "M02" in out and "\nM01" not in out and "\nCourse" not in out, out[-400:])
        code, out = run("check", c, "--json")
        check("--json is a list of items", code == 1 and isinstance(json.loads(out), list), out[:300])
        code, out = run("approve", c, "--by", "Test Operator")
        code2, out2 = run("status", c)
        check("approve, then status says who", code == 0 and "approved by Test Operator" in out2, out + out2)
        d = il.load(c)
        d["must_pass"] = ["q01"]
        cs.save(il.path(c), d)
        code, out = run("status", c)
        check("a change after the approval is said", "changed since the approval" in out, out)

        print("\n-- 2.128.0: a new course, its formats chosen while it is written (Aigars Kluga: 'the factory ... cannot vary')")
        f = os.path.join(tmp, "fresh")
        wc_ = os.path.join(f, "working_claude")
        os.makedirs(os.path.join(wc_, "script"))
        cs.save(os.path.join(wc_, "architecture.json"), {"course": {"title": "Fire party", "course_language": "English"}, "modules": [{"module": 3}]})
        subs = [("3.1", "Decides whether the hot work permit may be signed"), ("3.2", "Responds to a fire alarm during bunkering"),
                ("3.3", "Communicates the fire-team orders with closed-loop readback"), ("3.4", "Rigs a fire hose and tests the nozzle")]
        cs.save(os.path.join(wc_, "ilo_map.json"), {"rows": [{"module": "M03", "main_ilo_ids": ["3"], "sub_ilo_id": i, "sub_ilo": t} for i, t in subs]})
        code, out = run("plan", f, "--module", "3", "--json")
        picks = {p["sid"]: p for p in json.loads(out)[0]["sub_ilos"]} if code == 0 else {}
        check("plan, before any script: each Sub-ILO's task type from its verb and its formats - a case for the decision, the "
              "scenario run for the real-time outcome, a closed-loop drill with observers for the team, the demonstration for "
              "the hands-on one", code == 0 and [picks[i]["task_type"] for i, _ in subs] == ["decision", "real_time_judgement",
                                                                                            "team_behaviour", "fixed_sequence"]
              and [picks[i]["picks"][0] for i, _ in subs] == ["case-dilemma", "scenario-run", "closed-loop", "demonstration"]
              and "observer-role" in picks["3.3"]["picks"], out[:900])
        reg = il.load(f).get("register") or {}
        check("... and writes them into the register as a draft (task type, where it came from, the TLA names)",
              reg.get("3.2", {}).get("task_type") == "real_time_judgement" and reg["3.2"]["_task_type_from"] == "verb 'responds'"
              and reg["3.3"]["tla"][0] == "Closed-loop communication drill", reg.get("3.2"))
        code, out = run("plan", f)
        check("... the plain report says how each format is written in the script", code == 0 and "[scenario-run]" in out
              and "\"events\"" in out, out[:600])
        # the module, written as the plan says (what the factory does at the content-script stage)
        commit = "- Each trainee writes the answer on a card before the reveal."
        sl_ = lambda sid, sub, **kw: dict({"id": sid, "kind": "slide", "title": "Slide " + sid, "text": "Words.", "visual_kind": "photo",
                                           "visual": "A photo.", "notes": commit, "minutes": 5, "sub_ilo": sub,
                                           "active": "explain-then-reveal", "ask": "Why?", "reveal": "Because."}, **kw)
        screens = [sl_("s01", "3.1"),
                   sl_("s02", "3.1", active="scenario", choices=["Sign", "Refuse"], why=["No", "Yes"], right="B", minutes=10),
                   sl_("s03", "3.2"),
                   {"id": "a01", "kind": "activity", "format": picks["3.2"]["picks"][0], "sub_ilo": "3.2", "minutes": 60,
                    "title": "Fire alarm during bunkering", "text": "Teams of four run the alarm in the mock-up engine room.",
                    "notes": "- Planned events as listed.", "events": ["Smoke reported at 5 min", "The bunker hose parts at 15 min"]},
                   sl_("s04", "3.3"),
                   {"id": "a02", "kind": "activity", "format": picks["3.3"]["picks"][0], "sub_ilo": "3.3", "minutes": 45,
                    "title": "Fire-team orders", "text": "Groups of three: orders, readback, observer.", "notes": "- Rotate."},
                   sl_("s05", "3.4"),
                   {"id": "a03", "kind": "activity", "format": picks["3.4"]["picks"][0], "sub_ilo": "3.4", "minutes": 50,
                    "title": "Rig the fire hose", "text": "At the fire station on deck: rig the hose and test the nozzle.",
                    "notes": "- Six per hydrant.", "safety": ["Water pressure 7 bar: never point the nozzle at a person",
                                                              "Wet deck: safety shoes"]}]
        save_script(f, "M03", screens)
        script = cs.load(os.path.join(wc_, "script", "M03.json"))
        found = [x for x in cs.activity_findings(f, script) if x["level"] == cs.FAIL]
        check("the module written in those formats is not one direction, and every task type has its kind of activity",
              not found, found)
        one = dict(script, screens=[dict(x, format="write-plan") if x["kind"] == "activity" else x for x in screens])
        check("... the same module with every activity a project block is a must-fix - before anything is built",
              {x["rule"] for x in cs.activity_findings(f, one) if x["level"] == cs.FAIL} >= {"a_one_direction", "a_type_unserved"},
              cs.activity_findings(f, one))
        code, out = run("draft", f)
        d = il.load(f)
        pr = d.get("practicals") or {}
        check("draft makes a practical for every drill and team scenario - not only the simulator and equipment ones",
              set(pr) == {"M03.A01", "M03.A02", "M03.A03"} and len({pr[k]["_format"] for k in pr}) == 3, (out, sorted(pr)))
        check("... each cycle adds up to its screen's minutes; the team ones debrief 15-20 min, trainee-led; the scenario "
              "run's planned events are on its run",
              [sum(r["min"] for r in pr[k]["cycle"]) for k in ("M03.A01", "M03.A02", "M03.A03")] == [60, 45, 50]
              and pr["M03.A01"]["team"] and pr["M03.A02"]["team"] and not pr["M03.A03"]["team"]
              and "trainee-led" in pr["M03.A01"]["cycle"][-1]["what"]
              and any("Smoke reported" in (r.get("what") or "") for r in pr["M03.A01"]["cycle"]), {k: pr[k]["cycle"] for k in pr})
        check("... the hose drill's safety is the script's own lines, its intervention the Peyton stop-and-go",
              pr["M03.A03"]["prebrief"]["safety"][0].startswith("Water pressure") and "stop-and-go" in pr["M03.A03"]["prebrief"]["intervention"].lower())
        code, out = run("check", f, "--module", "3")
        check("instructor_led.py check passes the fresh module with nothing filled by hand", code == 0 and "Nothing open" in out, out[-1500:])
        code, out = run("draft", f)
        check("a second draft adds and fills nothing", "0 entries added, 0 fields filled" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
