# -*- coding: utf-8 -*-
"""test_task_cover - every self-check and module-check question judged against the slides before it (task_cover.py).

    python test_task_cover.py

Pinned:
  * next gives each set with only the slides before its task slide, their words apart from their notes;
  * judge refuses covered without the slides before it, a quote those slides do not show, a quote only the notes hold,
    partly or not covered without what is missing and its mend, and a line added to a slide after the task;
  * the approval: a module never judged is only noted; once judged, an unjudged question is must-fix, a question judged
    not covered or partly is must-fix, a covered one is clean; a changed slide before a question, or a changed question,
    is judged again; a slide after it changes nothing;
  * fixes adds the missing line to its slide - a change list content_script propose accepts; a question is never
    changed, only listed; --apply is for an unattended build only;
  * the review page says the verdict under the question.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import task_cover as tc  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


SCRIPT = {"module": 1, "title": "Gas tankers", "operator_language": "en", "status": "draft", "screens": [
    {"id": "s01", "kind": "slide", "title": "Car engines", "text": "A car engine burns petrol in four strokes.\nThe spark plug lights the mixture.",
     "notes": "- Type C tanks are designed for about 18 bar gauge.", "minutes": 3},
    {"id": "s02", "kind": "slide", "title": "Type C tanks", "text": "Type C tanks are pressure vessels.\nThey need no secondary barrier.",
     "notes": "- Ask the room first.", "minutes": 3},
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Which tank needs no secondary barrier?",
     "options": ["Type C", "Membrane"], "correct": "A", "feedback": "Type C tanks are pressure vessels."},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Which frame holds a spaceship's hull?",
     "options": ["The truss", "The keel"], "correct": "A", "feedback": "A spaceship hangs on its truss."},
    {"id": "s03", "kind": "slide", "title": "Membrane tanks", "text": "A membrane tank is held by the hull.\nIt needs a full secondary barrier.",
     "notes": "- Show the wall.", "minutes": 3},
    {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check", "text": "Module check on your tablet now.", "minutes": 4},
    {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "single_choice", "question": "What holds a membrane tank?",
     "options": ["The hull", "Its own walls"], "correct": "A", "feedback": "The hull holds a membrane tank."}]}


def main():
    tmp = tempfile.mkdtemp(prefix="taskcover_")
    try:
        c = os.path.join(tmp, "course")
        os.makedirs(os.path.join(c, "working_claude", "script"))
        cs.save(cs.paths(c, 1)["script"], json.loads(json.dumps(SCRIPT)))
        script = cs.load(cs.paths(c, 1)["script"])

        print("-- what the agent is given")
        u = {sid: (kind, [s["id"] for s in slides], [q["id"] for q in qs]) for sid, kind, slides, qs in tc.units(script)}
        check("each set gets only the slides before its task slide",
              u == {"SC1": ("self-check", ["s01", "s02"], ["q01", "q02"]), "MC": ("module-check", ["s01", "s02", "s03"], ["m01"])}, u)
        v = tc.shows(script["screens"][0])
        check("... a slide's words apart from its notes", "18 bar" not in v["shows"] and "18 bar" in v["notes"], v)
        check("the final assessment is not judged here", tc.units(dict(script, module="final")) == [])
        cs.save(os.path.join(c, "working_claude", "ilo_map.json"), {"rows": [
            {"module": 1, "sub_ilo_id": "1.2", "sub_ilo": "Beschreiben ...", "sub_ilo_en": "Describe each containment system "
             "- membrane, semi-membrane, Type C - and whether it needs a secondary barrier"}]})
        qv = tc.question_view(dict(script["screens"][3], sub_ilo="1.2"), tc.outcomes(c, 1))
        check("a question is given with its outcome's words, in English - so every part the outcome names, and the method "
              "of what it has the trainee do, is judged taught (semi-membrane's barrier, M01; the foam on a spill fire, M16)",
              qv.get("outcome", "").startswith("1.2 Describe each containment system") and "sub_ilo" not in qv, qv)
        os.remove(os.path.join(c, "working_claude", "ilo_map.json"))

        print("\n-- the approval before the check has run")
        f = cs.task_cover_findings(c, script)
        check("a module never judged is noted, not held", [(x["rule"], x["level"]) for x in f] == [("t_task_cover_not_run", cs.NOTE)], f)
        check("... and with no course folder nothing is checked", cs.task_cover_findings(None, script) == [])
        code = tc.main(["next", c, "--module", "1"])
        f = cs.task_cover_findings(c, script)
        check("once next has run, every unjudged question is must-fix", code == 0 and sorted(x["screen"] for x in f if x["level"] == cs.FAIL
              and x["rule"] == "t_task_not_covered") == ["m01", "q01", "q02"], f)

        print("\n-- judge")
        done, probs = tc.judge(c, 1, [{"id": "q01", "verdict": "covered", "slides": ["s03"], "quote": "needs a full secondary barrier"}])
        check("covered citing a slide after the task is refused", done == 0 and "slides before the question" in probs[0], probs)
        done, probs = tc.judge(c, 1, [{"id": "q01", "verdict": "covered", "slides": ["s02"], "quote": "Type C tanks never leak"}])
        check("... a quote the cited slides do not show is refused", done == 0 and "not on the cited slides" in probs[0], probs)
        done, probs = tc.judge(c, 1, [{"id": "q01", "verdict": "covered", "slides": ["s01"], "quote": "designed for about 18 bar gauge"}])
        check("... a quote only the instructor's notes hold is refused (a question asks what the slides show)",
              done == 0 and "only the instructor's notes" in probs[0], probs)
        done, probs = tc.judge(c, 1, [{"id": "q02", "verdict": "not_covered"}])
        check("not covered without what is missing is refused", done == 0 and "needs \"missing\"" in probs[0], probs)
        done, probs = tc.judge(c, 1, [{"id": "q02", "verdict": "not_covered", "missing": "spaceship frames"}])
        check("... and without its mend", done == 0 and "needs its mend" in probs[0], probs)
        done, probs = tc.judge(c, 1, [{"id": "q02", "verdict": "not_covered", "missing": "x", "add": {"slide": "s03", "line": "y"}}])
        check("... a line added to a slide after the task is refused", done == 0 and "before the task" in probs[0], probs)
        pts = json.loads(json.dumps(SCRIPT))
        pts["screens"][1]["points"] = "Pressure vessels\nNo secondary barrier"
        cp = os.path.join(tmp, "points")
        os.makedirs(os.path.join(cp, "working_claude", "script"))
        cs.save(cs.paths(cp, 1)["script"], pts)
        done, probs = tc.judge(cp, 1, [{"id": "q02", "verdict": "not_covered", "missing": "x", "add": {
            "slide": "s02", "line": "A spaceship's hull hangs on its truss, a long and light frame of welded steel tubes."}}])
        check("... a line added to a slide of short points that is longer than a point is refused (factory trial M19 s01, s08)",
              done == 0 and "short points" in probs[0], probs)
        done, probs = tc.judge(c, 1, [
            {"id": "q01", "verdict": "covered", "slides": ["s02"], "quote": ["They need no secondary barrier."]},
            {"id": "q02", "verdict": "not_covered", "missing": "The slides teach car engines and tanks, not what holds a spaceship's hull.",
             "add": {"slide": "s02", "line": "A spaceship's hull hangs on its truss."}, "question": "ask about tanks instead"},
            {"id": "m01", "verdict": "covered", "slides": ["s03"], "quote": "A membrane tank is held by the hull"}])
        check("verdicts that cite the slides before the question are recorded", done == 3 and not probs, probs)

        print("\n-- the approval")
        f = cs.task_cover_findings(c, script)
        check("not covered is must-fix; covered is clean", [(x["rule"], x["screen"], x["level"]) for x in f]
              == [("t_task_not_covered", "q02", cs.FAIL)] and "not covered" in f[0]["detail"], f)
        check("... and blocks the approval", any(x["rule"] == "t_task_not_covered" for x in cs.blocking(cs.all_findings(script, c))))
        tc.judge(c, 1, [{"id": "q02", "verdict": "partly", "missing": "what a truss is", "add": {"slide": "s02", "line": "A truss is a frame."}}])
        f = cs.task_cover_findings(c, script)
        check("partly is must-fix too", [(x["screen"], x["level"]) for x in f] == [("q02", cs.FAIL)] and "partly" in f[0]["detail"], f)
        html = cs.render_html(c, script)
        check("the review page says the verdict under each question",
              "Theory before it: covered on s02" in html and "cover it partly: what a truss is" in html)

        print("\n-- a changed script is judged again")
        changed = json.loads(json.dumps(script))
        changed["screens"][5]["text"] += "\nIt is the most common LNG tank."           # s03 - after SC1, before MC
        f = cs.task_cover_findings(c, changed)
        check("a slide changed before a question: that question is judged again; one after it changes nothing",
              sorted(x["screen"] for x in f) == ["m01", "q02"] and all(x["level"] == cs.FAIL for x in f), f)
        changed = json.loads(json.dumps(script))
        changed["screens"][1]["notes"] += "\n- Point at the dome."                     # s02 - before every set
        check("... a slide's notes too - for the questions whose covered verdict cites it, and the partly one; m01 (covered "
              "on s03) holds: a slide it does not cite takes nothing from what s03 teaches (the factory trial: one corrected line "
              "voided all 14 verdicts, four check rounds a module)",
              sorted(x["screen"] for x in cs.task_cover_findings(c, changed)) == ["q01", "q02"], cs.task_cover_findings(c, changed))
        changed = json.loads(json.dumps(script))
        changed["screens"][0]["text"] += "\nA diesel engine needs no spark."          # s01 - cited by no covered verdict
        check("... a slide no covered verdict cites: only the partly question is judged again",
              sorted(x["screen"] for x in cs.task_cover_findings(c, changed)) == ["q02"], cs.task_cover_findings(c, changed))
        changed = json.loads(json.dumps(script))
        changed["screens"][1], changed["screens"][5] = changed["screens"][5], changed["screens"][1]
        check("... a cited slide moved after its question voids that verdict",
              "q01" in [x["screen"] for x in cs.task_cover_findings(c, changed)], cs.task_cover_findings(c, changed))
        changed = json.loads(json.dumps(script))
        changed["screens"][3]["options"] = ["Type C", "Type B"]
        check("... and a changed question", sorted(x["screen"] for x in cs.task_cover_findings(c, changed)) == ["q01", "q02"])

        print("\n-- fixes")
        changes, asks = tc.fixes(c, 1)
        check("fixes adds the missing line at the end of its slide",
              changes == [{"screen": "s02", "field": "text", "new": "Type C tanks are pressure vessels.\nThey need no secondary barrier.\n"
                           "A truss is a frame."}], changes)
        ch, work = cs.build_changes(script, changes)
        check("... as a change list content_script propose understands", len(ch) == 1 and "A truss is a frame." in work["screens"][1]["text"])
        tc.judge(c, 1, [{"id": "q02", "verdict": "not_covered", "missing": "spaceships", "question": "ask about tanks instead"}])
        changes, asks = tc.fixes(c, 1)
        check("a question is never changed by fixes, only listed for the person", changes == [] and asks == [("q02", "spaceships",
              "ask about tanks instead")], (changes, asks))
        tc.judge(c, 1, [{"id": "q02", "verdict": "partly", "missing": "what a truss is", "add": {"slide": "s02", "line": "A truss is a frame."}}])
        reworded = cs.load(cs.paths(c, 1)["script"])
        reworded["screens"][0]["text"] += "\nA diesel engine needs no spark."
        cs.save(cs.paths(c, 1)["script"], reworded)
        changes, _ = tc.fixes(c, 1)
        check("a slide before the question reworded after the verdict (the fact check's rewrite) keeps the theory to add - "
              "the factory trial's apply changed nothing with four lines in its list",
              [x["screen"] for x in changes] == ["s02"] and changes[0]["new"].endswith("A truss is a frame."), changes)
        check("attended, fixes --apply is refused: the operator sees the changes first", tc.main(["fixes", c, "--module", "1", "--apply"]) == 2)
        os.environ["NOVIKONTAS_AUTO_BUILD"] = "1"
        try:
            code = tc.main(["fixes", c, "--module", "1", "--apply"])
        finally:
            del os.environ["NOVIKONTAS_AUTO_BUILD"]
        after = cs.load(cs.paths(c, 1)["script"])
        check("an unattended build adds the theory itself - exit 0, the apply worked", code == 0
              and after["screens"][1]["text"].endswith("A truss is a frame.") and not os.path.isfile(cs.paths(c, 1)["pending"]),
              after["screens"][1])
        s = tc.status(c, 1)
        check("... and the questions that rely on the changed slide are judged again - m01, covered on s03, keeps its verdict",
              sorted(s["unjudged"]) == ["q01", "q02"], s)
        check("the store is the module's own file", os.path.isfile(os.path.join(c, "working_claude", "task_cover", "M01.json")))

        print("\n-- the briefs name the commands that exist")
        skill = os.path.dirname(HERE)
        briefs = {p: io.open(p, encoding="utf-8").read() for p in [os.path.join(skill, "SKILL.md"), os.path.join(skill, "script", "GUIDE.md")]
                  + [os.path.join(skill, "..", "..", "agents", n) for n in ("task-coverage-checker.md", "fact-checker.md")]}
        wrong = [os.path.basename(p) for p, t in briefs.items() if "content_script.py fixes" in t or "(unattended: `fixes --apply`)" in t]
        guide = briefs[os.path.join(skill, "script", "GUIDE.md")]
        check("no brief sends a checker to content_script.py fixes - the command is task_cover.py fixes / fact_check.py fixes "
              "(the factory trial's checkers were sent there)", not wrong and "task_cover.py fixes --apply" in guide
              and "fact_check.py fixes" in guide, wrong)
        check("... and a checker's batch file goes in the course's working_claude/scratch/, never the system temp folder",
              all("working_claude/scratch/" in t and "file in the system temp folder" not in t
                  for p, t in briefs.items() if p.endswith("checker.md")))
        tcc = next(t for p, t in briefs.items() if p.endswith("task-coverage-checker.md"))
        fcc = next(t for p, t in briefs.items() if p.endswith("fact-checker.md"))
        check("the coverage checker is told a key the slides contradict is not covered, and an outcome's every part and "
              "the method of what it has the trainee do must be taught (M01 q01, the semi-membrane barrier; M16 the spill fire)",
              "key disagrees with the slides" in tcc and "part its `outcome` names" in tcc and "never teach how" in tcc)
        check("... and the fact-checker that steps in an order are found only in that same order (M16 a02, the dressing order)",
              "found only when a passage gives the same order" in fcc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
