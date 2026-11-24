# -*- coding: utf-8 -*-
"""test_ilo_elevation - every learning outcome raised or kept on purpose, one outcome at a time (2.142.0).

    python test_ilo_elevation.py

Pinned (knowledge/ilo-elevation.json, scripts/ilo_elevation.py, the elevation method of pedagogy_review.py):
  * the knowledge: six rules that each say where the factory carries them; eight keep codes, each allowed for some
    original levels; a raise lands on Apply-Create; every verb a raised outcome may start with is read at its own level,
    belongs to one level, and none is a verb the Bloom Verb Guide says to avoid or replace; the task is a TLA of the pool;
  * the seven checks on one outcome proposal: no decision; a keep without a code, with a code not allowed for the level,
    without a reason, with a re-wording or at another level; a raise below Apply or not above the original, without what
    the learner does, without its wording, not starting with a verb of its level in the third person, with two verbs,
    leaving out or adding a number or an abbreviation, losing the content words, or much longer;
  * the TLA of an outcome: tagged at its final level, not the TLA of either of the two outcomes before, none above 15 %
    of the course once 20 outcomes have tasks - the share block dropped first when fewer than three are left, then the
    other; at most 60 words; a fit, and a note when it is not strong;
  * one outcome at a time: next gives ONE outcome, then ONE task; propose and task save nothing when a check fails and
    name the check; a kept outcome is never re-worded by the command; a changed level puts the task out of date; status
    and check count decided n / total; an expert's decision is only warned about; "attention" flags a wording check for
    the expert instead of stopping; a Main ILO is raised without re-wording (L2);
  * a review started before 2.142.0 is untouched by all of it; draft --elevation moves it;
  * ratify writes the raised outcome's level on the Sub-ILO; the documents and the editor's form show the decision;
  * the golden set scorer: decisions against the reference, each answer checked like any proposal.
"""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "pedagogy_review.py")
sys.path.insert(0, HERE)
import bloom_map as bm  # noqa: E402
import ilo_elevation as el  # noqa: E402
import pedagogy_review as pr  # noqa: E402
import test_architecture_page as tap  # noqa: E402

PASS, FAIL = [], []
O = {"1.1": "States that a cargo tank is entered only when the oxygen reading is 21 % and the permit is signed by the master",
     "1.2": "Lists the three parts of the entry permit: gas readings, isolation and rescue plan",
     "1.3": "Describes the bump test of a portable gas detector",
     "1.4": "Operates the portable gas detector",
     "2.1": "States that the ESD system closes the manifold valves within 30 seconds",
     "2.2": "States the meaning of the general emergency alarm",
     "2.3": "Explains why the vent mast is led clear of the accommodation"}
RAISED = "Verifies that a cargo tank is entered only when the oxygen reading is 21 % and the permit is signed by the master"


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def course(tmp, name="course"):
    prog = copy.deepcopy(tap.PROGRAMME)
    prog.update(language="English", outcomes=dict(O), main_ilos={"1": "Contribute to safe cargo operations on liquefied gas tankers"})
    arch = copy.deepcopy(tap.ARCH)
    arch["main_ilos"] = [{"id": "1", "text": prog["main_ilos"]["1"]}]
    arch["final_assessment"]["topic"] = "4"
    arch["modules"] = [{"module": 1, "title": "Tank entry", "main_ilos": ["1"], "sub_ilos": [{"id": i, "status": "original"} for i in ("1.1", "1.2", "1.3", "1.4")]},
                       {"module": 2, "title": "Alarms and shutdown", "main_ilos": ["1"], "sub_ilos": [{"id": i, "status": "original"} for i in ("2.1", "2.2", "2.3")]},
                       {"module": 3, "title": "Extinguishing agents", "main_ilos": ["1"]},
                       {"module": 4, "title": "Final assessment", "main_ilos": ["1"]}]
    return tap.write_course(os.path.join(tmp, name), prog, arch)


def probs_of(original, orig, **p):
    return el.outcome_problems(original, orig, p)


def nums(found):
    return sorted({n for n, _ in found})


def main():
    print("-- the knowledge")
    check("six rules, each with where the factory carries it", sorted(el.E["rules"]) == ["E%d" % i for i in range(1, 7)]
          and all(r["rule"] and r["where"] for r in el.E["rules"].values()))
    check("eight keep codes; ALR only for Apply and above, the others only for Remember and Understand",
          sorted(el.CODES) == ["ALR", "CNF", "FRQ", "LOD", "PRE", "REC", "SAF", "THN"] and el.allowed_codes(3) == ["ALR"]
          and "ALR" not in el.allowed_codes(1) and len(el.allowed_codes(2)) == 7, (el.allowed_codes(1), el.allowed_codes(3)))
    check("a raise lands on Apply, Analyse, Evaluate or Create", el.RAISE == [3, 4, 5, 6])
    seen = [v for n in el.WRITE for v in el.WRITE[n]]
    check("each verb a raised outcome may start with belongs to one level", len(seen) == len(set(seen)), sorted(v for v in seen if seen.count(v) > 1))
    two_level = set(k for k in bm.VG["depends"] if not k.startswith("_"))
    off = [(n, v, bm.ilo_level("%s the thing" % el.third_person(v)[0].capitalize(), "en")["level"]) for n in el.WRITE for v in el.WRITE[n]
           if v not in two_level and bm.ilo_level("%s the thing" % el.third_person(v)[0].capitalize(), "en")["level"] != n]
    check("... and is read at that level by the Bloom map (select, check, prepare, calculate have one home here, two when read)", not off, off)
    bad = [v for v in seen if bm.avoided("%s the thing" % el.third_person(v)[0].capitalize())]
    check("... and none is a verb the Bloom Verb Guide says to avoid or replace (demonstrates, assesses, discusses)", not bad, bad)
    check("every verb the Verb Guide writes Apply-Create with is in the list of its level",
          all(v in el.WRITE[n] for n in el.RAISE for v in bm.LEVELS[n]["write"]), [(n, v) for n in el.RAISE for v in bm.LEVELS[n]["write"] if v not in el.WRITE[n]])
    check("the third person: carries out, analyses (and analyzes), finds the cause of, justifies",
          [el.third_person(v) for v in ("carry out", "analyse", "find the cause of", "justify")]
          == [["carries out"], ["analyses", "analyzes"], ["finds the cause of"], ["justifies"]])
    check("the task of an outcome is one of the 28 TLAs of the pool, by its key or its name",
          len(el.TLAS) == 28 and el.tla("case-dilemma")["level"] == 5 and el.tla("Key-feature problem")["key"] == "key-feature" and el.tla("Concept Mapping") is None)

    print("\n-- the checks on one outcome proposal")
    o = O["1.1"]
    ok = dict(decision="raise", level=5, does="Checks a permit and a reading against the rule and says whether entry is allowed.", why="x", revised_outcome=RAISED)
    check("a correct raise passes: the verb changed, the content in the original words", el.outcome_problems(o, 1, ok) == [], el.outcome_problems(o, 1, ok))
    check("1 - no decision", nums(probs_of(o, 1)) == [1])
    check("1 - an original level that is not known is said first", nums(el.outcome_problems(o, None, ok)) == [1] and "original_level" in el.outcome_problems(o, None, ok)[0][1])
    check("2 - a keep without a code, and without a reason", nums(probs_of(o, 1, decision="keep", level=1)) == [2] and len(probs_of(o, 1, decision="keep", level=1)) == 2)
    check("2 - a keep with ALR on a Remember outcome, or PRE on an Apply one",
          "not allowed" in probs_of(o, 1, decision="keep", level=1, keep_codes=["ALR"], why="x")[0][1]
          and "not allowed" in probs_of(O["1.4"], 3, decision="keep", level=3, keep_codes=["PRE"], why="x")[0][1])
    check("2 - a kept outcome is not re-worded, and stays at its level",
          len(probs_of(o, 1, decision="keep", level=2, keep_codes=["SAF"], why="x", revised_outcome=RAISED)) == 2)
    check("a keep with its code and reason passes - at Remember, and at Apply with ALR",
          probs_of(o, 1, decision="keep", level=1, keep_codes=["SAF", "REC"], why="The limit is recalled at the tank hatch.") == []
          and probs_of(O["1.4"], 3, decision="keep", level=3, keep_codes=["ALR"], why="Already a doing.") == [])
    check("3 - Remember to Understand is not a raise; nor is the same level", nums(el.outcome_problems(o, 1, dict(ok, level=2))) == [3]
          and nums(el.outcome_problems(O["1.4"], 3, dict(ok, level=3))) == [3])
    check("3 - a raise without what the learner does (the honesty test)", 3 in nums(el.outcome_problems(o, 1, dict(ok, does=""))))
    check("4 - a raise without its wording", nums(el.outcome_problems(o, 1, dict(ok, revised_outcome=""))) == [4])
    v4 = el.outcome_problems(o, 1, dict(ok, revised_outcome=RAISED.replace("Verifies", "Differentiates")))
    check("4 - a verb of another level (Differentiates, at Evaluate): named, with the verbs of the level", nums(v4) == [4] and "Analyse" in v4[0][1] and "Verifies" in v4[0][1], v4)
    check("4 - a verb the Verb Guide replaces (Assesses, Demonstrates) or not in the third person (Verify)",
          all(nums(el.outcome_problems(o, 1, dict(ok, revised_outcome=RAISED.replace("Verifies", w)))) == [4] for w in ("Assesses", "Demonstrates", "Verify")))
    check("4 - one verb only: 'Verifies and justifies ...'",
          any("one verb only" in w for _, w in el.outcome_problems(o, 1, dict(ok, revised_outcome=RAISED.replace("Verifies", "Verifies and justifies")))))
    check("5 - a number left out, and a number or an abbreviation added",
          nums(el.outcome_problems(o, 1, dict(ok, revised_outcome=RAISED.replace("21 %", "safe")))) == [5]
          and any("adds SOLAS" in w for _, w in el.outcome_problems(o, 1, dict(ok, revised_outcome=RAISED + " as SOLAS requires"))))
    added = "Verifies the entry conditions of a cargo tank and completes an enclosed-space permit from the gas readings"
    check("6 - a re-write that adds a task and drops the content is refused", 6 in nums(el.outcome_problems(o, 1, dict(ok, revised_outcome=added))),
          el.outcome_problems(o, 1, dict(ok, revised_outcome=added)))
    long = RAISED + ", by comparing the reading on the instrument with the limit in the company procedure before anyone goes in"
    check("7 - a re-write much longer than the original", 7 in nums(el.outcome_problems(o, 1, dict(ok, revised_outcome=long))))
    check("a Main ILO is raised without re-wording; an original in another language skips only the wording checks",
          el.outcome_problems(o, 1, dict(ok, revised_outcome=""), main=True) == []
          and el.outcome_problems("Aprakstīt mērinstrumentu", 2, dict(ok, level=3, revised_outcome="Uses the gas detector"), comparable=False) == [])

    print("\n-- the TLA of an outcome, and variety counted by code")
    a5, _ = el.allowed_tlas(5, {}, [])
    check("at Evaluate the pool has five; all allowed when nothing is used yet", sorted(a5) == ["case-dilemma", "challenge-response", "critique", "scenario-run", "trainee-debrief"], a5)
    a, blocked = el.allowed_tlas(5, {"case-dilemma": 1, "critique": 1}, ["case-dilemma", "critique"])
    check("the TLAs of the two outcomes before are blocked", "case-dilemma" not in a and "critique" not in a and len(a) == 3 and set(blocked) == {"case-dilemma", "critique"}, (a, blocked))
    a, _ = el.allowed_tlas(5, {}, ["key-feature", "case-dilemma", "hazard-map", "walkthrough"])
    check("... only the two before: one three outcomes back is free again", "case-dilemma" in a)
    used = {"case-dilemma": 8, "scenario-run": 2, "key-feature": 10}
    a, blocked = el.allowed_tlas(5, used, [])
    check("once 20 outcomes have tasks, a TLA above 15 % is blocked", "case-dilemma" not in a and "15 %" in blocked["case-dilemma"], (a, blocked))
    check("... not before 20", "case-dilemma" in el.allowed_tlas(5, {"case-dilemma": 8, "scenario-run": 2}, [])[0])
    a, _ = el.allowed_tlas(6, {"write-plan": 9, "key-feature": 11}, ["rewrite-procedure", "design-scenario"])
    check("fewer than three left: the share block is dropped first, then the block of the two before", sorted(a) == ["design-scenario", "rewrite-procedure", "write-plan"], a)
    t_ok = dict(tla="case-dilemma", how="Given a permit and three readings, the trainee decides go or no-go and says which reading decides it.", fit="strong")
    check("a task at the outcome's level passes", el.task_problems(t_ok, 5, {}, []) == ([], "case-dilemma"), el.task_problems(t_ok, 5, {}, []))
    check("no TLA; not a TLA of the pool; a TLA of another level - each says which are allowed",
          all("one of:" in el.task_problems(dict(t_ok, tla=x), 5, {}, [])[0][0] for x in ("", "Concept Mapping", "retrieval-round")))
    check("blocked for variety is said with its reason", "blocked for variety" in el.task_problems(t_ok, 5, {}, ["case-dilemma"])[0][0])
    check("more than 60 words; no fit; a fit that is not strong without its note",
          any("at most 60" in w for w in el.task_problems(dict(t_ok, how="word " * 61), 5, {}, [])[0])
          and any("no fit" in w for w in el.task_problems(dict(t_ok, fit=""), 5, {}, [])[0])
          and any("fit_note" in w for w in el.task_problems(dict(t_ok, fit="gap"), 5, {}, [])[0])
          and el.task_problems(dict(t_ok, fit="gap", fit_note="an instructor checklist is assumed"), 5, {}, [])[0] == [])

    tmp = tempfile.mkdtemp(prefix="elevation_")
    try:
        c = course(tmp)
        f = pr.files(c)
        load = lambda: json.load(io.open(f["review"], encoding="utf-8"))

        print("\n-- one outcome at a time")
        pr.draft(c)
        code, out = run("next", "--course", c)
        check("next gives ONE outcome: the first, with its level, the levels it may be raised to and the keep codes allowed",
              code == 0 and "ONE OUTCOME - module 1, topic 1.1" in out and O["1.1"] in out and "1 Remember" in out and "Verifies" in out
              and "PRE" in out and "ALR" not in out and O["1.2"] not in out and "decided 0 / 8" in out, out)
        code, out = run("propose", "--course", c, "--module", "1", "--topic", "1.1", "--decision", "raise", "--level", "5", "--why", "The officer signs the permit.",
                        "--does", "Checks a permit and a reading against the rule.", "--text", added)
        check("a re-write that fails a check is not saved, and the check is named", code == 2 and "Not saved" in out and "check 6" in out
              and not (load()["modules"]["1"]["rows"]["1.1"]["proposed"].get("decision")), out)
        code, out = run("propose", "--course", c, "--module", "1", "--topic", "1.1", "--decision", "raise", "--level", "5", "--why", "The officer signs the permit.",
                        "--does", "Checks a permit and a reading against the rule.", "--text", RAISED)
        check("the corrected answer is saved on its outcome, and the count goes up", code == 0 and "raised at 5 Evaluate" in out and "decided 1 / 8" in out
              and load()["modules"]["1"]["rows"]["1.1"]["proposed"]["revised_outcome"] == RAISED, out)
        code, out = run("next", "--course", c)
        check("next goes on to the next outcome - never back, never two", "topic 1.2" in out and "topic 1.1" not in out and O["1.3"] not in out, out)
        code, out = run("propose", "--course", c, "--module", "1", "--topic", "1.2", "--decision", "keep", "--codes", "PRE", "--why", "x", "--text", "Sorts the parts")
        check("a kept outcome is never re-worded by the command", code == 2 and "character for character" in out, out)
        answers = [("1", "1.2", ["--decision", "keep", "--codes", "pre,cnf", "--why", "The three parts are the frame of every later permit task."]),
                   ("1", "1.3", ["--decision", "raise", "--level", "3", "--does", "Bump-tests a detector with the test gas.", "--why", "It is done before every entry.",
                                 "--text", "Carries out the bump test of a portable gas detector"]),
                   ("1", "1.4", ["--decision", "keep", "--codes", "ALR", "--why", "Already a doing; no judgement is asked at this rank."]),
                   ("2", "2.1", ["--decision", "raise", "--level", "4", "--does", "Works out from a trip log why the valves closed late.", "--why", "A slow closure is found from the log.",
                                 "--text", "Predicts that the ESD system closes the manifold valves within 30 seconds"]),
                   ("2", "2.2", ["--decision", "keep", "--codes", "SAF,REC", "--why", "The signal is recalled at once, with no aid."]),
                   ("2", "2.3", ["--decision", "raise", "--level", "4", "--does", "Traces where vented vapour goes in a given wind.", "--why", "Vapour at the air intakes is the hazard.",
                                 "--text", "Analyses why the vent mast is led clear of the accommodation"]),
                   ("3", "1", ["--decision", "raise", "--level", "3", "--does", "Selects the agent for a named cargo fire.", "--why", "The choice is made on deck.",
                               "--original-level", "2"])]             # "Contribute to ..." - its verb is not in the list: the level is said
        codes = [run("propose", "--course", c, "--module", m, "--topic", t, *rest) for m, t, rest in answers]
        check("the other seven outcomes: three kept with their codes, four raised - a Main ILO without re-wording",
              [x[0] for x in codes] == [0] * 7 and "decided 8 / 8" in codes[-1][1] and "revised_outcome" not in load()["modules"]["3"]["rows"]["1"]["proposed"],
              [x[1][-200:] for x in codes if x[0]])
        code, out = run("next", "--course", c)
        check("with every outcome decided, next gives ONE task: the outcome as decided and only the TLAs the code allows",
              "ONE TASK - module 1, topic 1.1" in out and RAISED in out and "case-dilemma" in out and "retrieval-round" not in out and "none yet" in out, out)
        code, out = run("task", "--course", c, "--module", "1", "--topic", "1.1", "--tla", "key-feature", "--how", "x", "--fit", "strong")
        check("a TLA of another level is not saved", code == 2 and "4 Analyse activity" in out and "one of:" in out, out)
        tasks = [("1", "1.1", "case-dilemma", "strong"), ("1", "1.2", "retrieval-round", "strong"), ("1", "1.3", "demonstration", "strong"),
                 ("1", "1.4", "desktop-sim", "strong"), ("2", "2.1", "fault-finding", "strong"), ("2", "2.2", "number-drill", "strong"),
                 ("2", "2.3", "hazard-map", "strong"), ("3", "1", "walkthrough", "strong")]
        codes = [run("task", "--course", c, "--module", m, "--topic", t, "--tla", k, "--fit", fit, "--how",
                     "Each trainee works on the permit, the detector and the 30 second closure of this outcome, then says what decides it.") for m, t, k, fit in tasks]
        check("eight tasks, each a TLA at its outcome's level", [x[0] for x in codes] == [0] * 8 and "Tasks 8 / 8" in codes[-1][1], [x[1][-300:] for x in codes if x[0]])
        code, out = run("task", "--course", c, "--module", "2", "--topic", "2.3", "--tla", "fault-finding", "--how", "x y", "--fit", "strong")
        check("variety is enforced in syllabus order: the TLA of the outcome two before is refused", code == 2 and "blocked for variety" in out, out)
        code, out = run("status", "--course", c)
        check("status counts by code: decided, raised and kept, each keep code, each level before and after, each TLA",
              "decided: 8 / 8" in out and "Raised 5, kept 3" in out and "PRE 1" in out and "SAF 1" in out and "case-dilemma 1" in out and "Fit: strong 8" in out, out)

        print("\n-- check, the documents, the editor")
        rev = load()
        rev.update(now_summary="Slides read out, a recall test.", proposed_summary="Most outcomes are raised to a doing or a judgement.",
                   upgrades=[{"what": "Every self-check in two parts", "why": "recall first, then a harder task", "modules": "all"}])
        for m in rev["modules"].values():
            for r in m["rows"].values():
                r["now"] = {"level": 1, "how": "slides", "checked": "final test Q1", "where": "deck S1-S5"}
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        probs, notes = pr.check(c)
        check("a review decided one outcome at a time is clean - three levels up in one course is no longer refused", probs == [], probs)
        code, out = run("check", "--course", c)
        check("check shows the count: outcomes decided 8 / 8, tasks 8 / 8", "Outcomes decided 8 / 8, tasks 8 / 8." in out, out)
        code = pr.render(c, pdf=False)
        html = io.open(os.path.join(f["out"], "2_BLOOM_PROPOSED.html"), encoding="utf-8").read()
        check("the proposed document shows the original beside the raise, the keep codes in words, what the trainee does and the activity",
              code == 0 and O["1.1"] in html and "Raised, proposed wording: " + RAISED in html and "prerequisite for a higher-level outcome" in html
              and "The trainee: Checks a permit" in html and "Case dilemma" in html and "<td>Raised</td>" in html, html[-900:])
        v = pr.view(c)
        row = next(r for t in v["content"]["topics"] for r in t["rows"] if r.get("ref") == "1.1")
        check("the editor's form: the original beside the proposed wording, its level, the decision and the TLA as the task",
              row["original"]["text"] == O["1.1"] and row["proposed"]["text"] == RAISED and row["proposed"]["level"] == 5
              and row["decision"] == "raise" and row["task"]["name"].startswith("Case dilemma") and row["task"]["id"] == "case-dilemma"
              and row["task"]["fit"] == "strong" and "Scored" in row["task"]["route"] and "kept" not in row and v["review"]["counts"]["decided"] == 8, row)
        kept = next(r for t in v["content"]["topics"] for r in t["rows"] if r.get("ref") == "2.2")
        check("... a kept outcome keeps its words and carries its codes and its reason",
              kept["proposed"]["text"] == O["2.2"] and kept["decision"] == "keep" and kept["kept"] == {"criteria": ["SAF", "REC"], "why": "The signal is recalled at once, with no aid."}, kept)
        fm = v["content"]
        check("... and the form carries the rules the editor shows and checks a Regenerate with: the 28 TLAs, the keep codes, the verbs of each level, the thresholds",
              fm["method"] == "elevation" and len(fm["archetypes"]) == 28 and fm["archetypes"][0].keys() >= {"id", "name", "level", "levels", "route"}
              and [c["code"] for c in fm["keep_codes"]][:2] == ["PRE", "SAF"] and "Verifies" in fm["write_verbs"]["5"] and fm["checks"]["length_max"] == 1.3
              and fm["counts"]["raise"] == 5, {k: fm[k] for k in ("method", "write_verbs")})

        bad = copy.deepcopy(rev)
        bad["modules"]["1"]["rows"]["1.2"]["proposed"].pop("keep_codes")
        bad["modules"]["2"]["rows"]["2.1"]["proposed"]["revised_outcome"] = "Predicts that the ESD system closes the manifold valves within 25 seconds"
        bad["modules"]["2"]["rows"]["2.3"]["proposed"]["tla"] = "fault-finding"
        bad["modules"]["1"]["rows"]["1.3"]["proposed"].pop("decision")
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(bad, ensure_ascii=False))
        probs, notes = pr.check(c)
        for want in ("topic 1.2: kept without a keep code", "topic 2.1: leaves out 30", "topic 2.3: fault-finding is blocked for variety", "topic 1.3: no decision"):
            check("check stops on: " + want, any(want in p for p in probs), probs)
        flag = copy.deepcopy(rev)
        flag["modules"]["2"]["rows"]["2.1"]["proposed"].update(revised_outcome="Predicts that the ESD system closes the manifold valves within 25 seconds",
                                                               attention="The procedure in force says 25 seconds; the programme is older.")
        flag["modules"]["2"]["rows"]["2.3"]["proposed"].update(level=6, revised_outcome="Rebuilds the mast", expert={"by": "Anna", "on": "2026-11-24", "said": "Make it a design task."})
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(flag, ensure_ascii=False))
        probs, notes = pr.check(c)
        check("'attention' hands a wording check to the expert, flagged, instead of stopping", not any("2.1" in p for p in probs)
              and any(n.startswith("FLAGGED for the expert") and "25 seconds" in n for n in notes), (probs, notes))
        check("an expert's own decision is only warned about", not any("2.3" in p for p in probs) and any("topic 2.3" in n and "warning" in n for n in notes), (probs, notes))
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))

        code, out = run("propose", "--course", c, "--module", "1", "--topic", "1.1", "--decision", "raise", "--level", "4", "--why", "x",
                        "--does", "Works out which reading fails.", "--text", RAISED.replace("Verifies", "Analyses"))
        p11 = load()["modules"]["1"]["rows"]["1.1"]["proposed"]
        check("a changed level puts the task out of date: it is asked again", code == 0 and "tla" not in p11 and p11["how"] == "" and "ONE TASK - module 1, topic 1.1" in run("next", "--course", c)[1], p11)
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        check("ratify writes the raised outcome and its level on the Sub-ILO, the programme's words kept beside it",
              pr.ratify(c, 1, "1.1", RAISED, "Anna") and (lambda s: (s["text"], s["bloom"], s["programme_text"], s["status"]) == (RAISED, 5, O["1.1"], "re-expressed"))(
                  next(s for s in pr._load(f["arch"])["modules"][0]["sub_ilos"] if s["id"] == "1.1")))
        probs, _ = pr.check(c)
        check("... and the review still checks the raise against the programme's own words", probs == [], probs)

        print("\n-- the expert's answer from the editor keeps the counts true")
        before = pr.counts(c)
        r2 = load()
        row21 = r2["modules"]["2"]["rows"]["2.1"]
        pr.carry_out(row21, 1, "Keep the original wording and level.", "Anna Berzina", how=row21["proposed"]["how"], decision="keep", keep_codes=["saf", "XXX"])
        row13 = r2["modules"]["1"]["rows"]["1.3"]
        pr.carry_out(row13, 4, "Make it a comparison.", "Anna Berzina", how="Pairs compare two bump tests.", decision="raise")
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(r2, ensure_ascii=False))
        after = pr.counts(c)
        check("Keep old ILO makes the row a keep, with the keep codes Regenerate named (only real ones); a re-wording taken stays a raise",
              row21["proposed"]["decision"] == "keep" and row21["proposed"]["keep_codes"] == ["SAF"] and "revised_outcome" not in row21["proposed"]
              and row13["proposed"]["decision"] == "raise" and (after["raise"], after["keep"]) == (before["raise"] - 1, before["keep"] + 1), (before, after))
        probs, notes = pr.check(c)
        check("... and the expert's rows never stop the documents", not any("2.1" in p or "1.3" in p for p in probs), probs)
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))

        print("\n-- a review started before 2.142.0")
        old = course(tmp, "old")
        fo = pr.files(old)
        pr.draft(old)
        r0 = json.load(io.open(fo["review"], encoding="utf-8"))
        r0.pop("method")
        r0.update(now_summary="a", proposed_summary="b", upgrades=[{"what": "w", "why": "y"}])
        for m in r0["modules"].values():
            for r in m["rows"].values():
                r["now"] = {"level": 1, "how": "slides", "checked": "test", "where": "deck"}
                r["proposed"] = {"level": 1, "how": "a recall round", "why": "kept"}
        r0["modules"]["3"]["rows"]["1"]["proposed"].update(level=3)
        r0["modules"]["3"]["rows"]["1"]["now"].update(level=2)
        io.open(fo["review"], "w", encoding="utf-8").write(json.dumps(r0, ensure_ascii=False))
        probs, _ = pr.check(old)
        check("is finished by the rules it was started with: no decision, no code and no TLA is asked", not any("decision" in p or "TLA" in p for p in probs), probs)
        code, out = run("next", "--course", old)
        check("next, propose and status say so, and how to move it", code == 2 and "draft --course <course> --elevation" in out, out)
        run("draft", "--course", old)
        check("draft again does not move it", "method" not in json.load(io.open(fo["review"], encoding="utf-8")))
        run("draft", "--course", old, "--elevation")
        probs, _ = pr.check(old)
        check("draft --elevation moves it: every outcome is then decided", json.load(io.open(fo["review"], encoding="utf-8"))["method"] == "elevation"
              and sum("no decision" in p for p in probs) == 8, probs[:3])

        print("\n-- the three frameworks, enforced for a course judged by this method")
        import content_script as cs
        import check_course_package as ccp
        check("enforced: the course judged by the elevation method - not the one started before", el.enforced(c) and not el.enforced(os.path.join(tmp, "none")))
        r0.pop("method", None)
        io.open(fo["review"], "w", encoding="utf-8").write(json.dumps(r0, ensure_ascii=False))
        check("... a review without the method is not enforced", not el.enforced(old))

        def stage2(extra, where=c):
            a = pr._load(pr.files(where)["arch"])
            a["modules"][1]["sub_ilos"] += extra
            return el.stage2_problems(where, pr._load(pr.files(where)["prog"]), a)

        check("Stage 2: the course as it is has nothing that stops it", stage2([]) == [], stage2([]))
        s2 = stage2([{"id": "2.4", "status": "added", "text": "Discusses the importance of teamwork on deck", "why": "x"},
                     {"id": "2.5", "status": "added", "text": "Understands the vent system", "why": "x"},
                     {"id": "2.6", "status": "added", "text": "Selects the PPE for a named cargo", "why": "x"},
                     {"id": "2.7", "status": "added", "text": "Selects the PPE for a named cargo from the SDS", "why": "x", "bloom": 3},
                     {"id": "2.8", "status": "added", "text": "Dons the breathing apparatus within the set time", "why": "x"}])
        check("Stage 2 stops on a Sub-ILO we wrote with a verb no assessor can see (discuss; understand), with what to write instead",
              any("2.4" in p and "explain, compare or justify" in p for p in s2) and any("2.5" in p and "cannot be watched" in p for p in s2), s2)
        check("... and on a Sub-ILO with no Bloom level, with the question that tells its two levels apart", any("2.6" in p and "trade-off" in p and "\"bloom\": n" in p for p in s2), s2)
        check("... not on one whose level is written, nor on an action of the hands (no Bloom level needed)", not any("2.7" in p or "2.8" in p for p in s2) and len(s2) == 3, s2)
        check("... and never on a course started before", stage2([{"id": "2.4", "status": "added", "text": "Discusses teamwork", "why": "x"}], old) == [])
        cs.save(os.path.join(c, "ilo_map.json"), {"rows": [{"module": "M01", "main_ilo_ids": ["1"], "sub_ilo_id": "1.1", "sub_ilo": RAISED}]})
        cs.save(os.path.join(old, "ilo_map.json"), {"rows": [{"module": "M01", "main_ilo_ids": ["1"], "sub_ilo_id": "1.1", "sub_ilo": RAISED}]})
        script = {"module": 1, "course_language": "English", "operator_language": "en", "sources": ["the programme"], "screens": [
            {"id": "s01", "kind": "slide", "title": "Entry", "text": "Words.", "notes": "- Explain.", "minutes": 5, "sub_ilo": "1.1"},
            {"id": "m01", "kind": "module-check", "mechanic": "single_choice", "question": "Enter?", "options": ["No", "Yes"], "correct": "A", "feedback": "x", "sub_ilo": "1.1"}]}
        must = {x["rule"] for x in cs.ilo_findings(c, script) if x["level"] == cs.FAIL}
        check("Stage 3: an outcome raised to Evaluate and checked only by a recall question is a must-fix (rule B5)", "b_sub_unchecked" in must, must)
        old_must = {x["rule"] for x in cs.ilo_findings(old, script) if x["level"] == cs.FAIL}
        check("... a suggestion, as before, for a course started before", "b_sub_unchecked" not in old_must, old_must)
        fp = ccp.framework_problems(c)
        check("the package: an enforced course without its instructor-led register is told to draft one", len(fp) == 1 and "instructor_led.py draft" in fp[0], fp)
        check("... nothing is asked of a course started before", ccp.framework_problems(old) == [])

        print("\n-- the golden set")
        gold = [{"ref": k, "original_text": v, "original_level": "Remember" if v.startswith(("States", "Lists")) else "Understand" if v.startswith(("Describes", "Explains")) else "Apply",
                 "expected_decision": "keep" if k in ("1.2", "1.4", "2.2") else "raise",
                 "expected_level": {"1.1": "Evaluate", "1.2": "Remember", "1.3": "Apply", "1.4": "Apply", "2.1": "Analyze", "2.2": "Remember", "2.3": "Analyze"}[k]} for k, v in O.items()]
        gp = os.path.join(tmp, "golden.json")
        io.open(gp, "w", encoding="utf-8").write(json.dumps(gold))
        code, out = run("golden", "--set", gp, "--packet", "1.1")
        check("golden --packet asks one outcome, without the reference's answer", code == 0 and "ONE OUTCOME - 1.1" in out and O["1.1"] in out and "expected" not in out and "Evaluate. Starts" in out.replace("5 Evaluate - the learner checks, verifies, justifies or decides against a criterion. Starts", "Evaluate. Starts"), out)
        ans = {k: {kk: vv for kk, vv in rev["modules"][k[0]]["rows"][k]["proposed"].items()} for k in O}
        ap_ = os.path.join(tmp, "answers.json")
        io.open(ap_, "w", encoding="utf-8").write(json.dumps(ans))
        code, out = run("golden", "--set", gp, "--answers", ap_)
        check("the answers are scored: every decision and level matches, no check fails - PASS", code == 0 and "match the reference: 7" in out and out.strip().endswith("PASS"), out)
        ans["1.1"] = {"decision": "keep", "level": 1, "keep_codes": ["SAF"], "why": "x"}
        ans["2.1"]["revised_outcome"] = added
        io.open(ap_, "w", encoding="utf-8").write(json.dumps(ans))
        code, out = run("golden", "--set", gp, "--answers", ap_)
        check("a mismatch is listed with the reference; an answer that fails a check stops the pass", code == 2 and "1.1" in out and "the reference: raise at 5 Evaluate" in out
              and "check 5" in out and "NOT PASSED" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
