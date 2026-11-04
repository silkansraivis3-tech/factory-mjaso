# -*- coding: utf-8 -*-
"""test_pedagogy_review - the experts' pedagogy documents: Bloom now, Bloom proposed, teaching and learning activities.

    python test_pedagogy_review.py

Pinned:
  * draft adds one empty row per topic of the architecture - every Sub-ILO bloom_map reads, a module without any by its
    Main ILOs - and
    keeps every row already judged; the final-assessment module has none;
  * check stops on: a topic not judged, a level outside 0-6 now / 1-6 proposed, an empty how / checked / where / why, a
    proposal below what the old course reached, a row for a topic the architecture no longer has, empty summaries,
    no upgrade or an upgrade without its why;
  * check only notes: a proposal still below what the outcome asks, Create, a module with no activity proposed;
  * render writes the three documents as Word and HTML, the outcomes' words read from the architecture, never from the
    judgement file; the activities with the experts' status; a sign-off block; level 0 says "not taught";
  * the Stage 2 approval is refused until the documents are clean and written from the current files, and an edit to the
    judgement after render asks for them again.
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
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "pedagogy_review.py")
sys.path.insert(0, HERE)
import pedagogy_review as pr  # noqa: E402
import test_architecture_page as tap  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def complete(course):
    """Judge every topic of a course's draft and write its documents - a clean review, as the factory leaves it."""
    pr.draft(course)
    f = pr.files(course)
    rev = json.load(io.open(f["review"], encoding="utf-8"))
    rev.update(now_summary="Slides read out, a final test of recall questions.",
               proposed_summary="Every topic is done on the tablet or the simulator.",
               upgrades=[{"what": "Every self-check in two parts", "why": "recall first, then a harder task", "modules": "all"}])
    for m in rev["modules"].values():
        for r in m["rows"].values():
            r["now"] = {"level": 1, "how": "slides", "checked": "final test Q1", "where": "deck S1-S5"}
            r["proposed"] = {"level": 3, "how": "sets the value on the panel", "why": "it is what the job needs"}
    io.open(f["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
    pr.render(course, pdf=False)
    return rev


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


def main():
    tmp = tempfile.mkdtemp(prefix="pedagogy_")
    try:
        arch = copy.deepcopy(tap.ARCH)
        arch["final_assessment"]["topic"] = "4"
        arch["modules"].append({"module": 4, "title": "Final assessment", "main_ilos": ["1"]})
        arch["modules"][0]["active_learning"] = [
            {"id": "A1.1", "subtopic": "1.1.a", "technique": "explore", "status": "approved", "minutes": 10,
             "does": "Each trainee opens the hull section in 3D and finds the tank that leans on the hull.",
             "instead_of": "the tank-type slides stay"},
            {"id": "A1.2", "subtopic": "1.1.b", "technique": "predict-then-reveal", "status": "struck", "minutes": 5,
             "does": "Predict the pressure in the tropics."}]
        c = tap.write_course(os.path.join(tmp, "course"), tap.PROGRAMME, arch)
        f = pr.files(c)

        print("-- draft")
        code, out = run("check", "--course", c)
        check("check before draft says the documents are not started", code == 2 and "not started yet" in out, out)
        code, out = run("draft", "--course", c)
        rev = json.load(io.open(f["review"], encoding="utf-8"))
        rows = {n: sorted(m["rows"]) for n, m in rev["modules"].items()}
        check("one row per Sub-ILO as bloom_map reads them; a module without Sub-ILOs by its Main ILO; no final assessment",
              code == 0 and rows == {"1": ["1.1", "1.1.a", "1.1.b"], "2": ["1.3"], "3": ["1"]}, rows)
        check("the outcomes' words are not in the judgement file", tap.SUB_NEW not in io.open(f["review"], encoding="utf-8").read())
        rev["modules"]["1"]["rows"]["1.1.a"]["now"]["how"] = "kept"
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(rev, ensure_ascii=False))
        run("draft", "--course", c)
        again = json.load(io.open(f["review"], encoding="utf-8"))
        check("draft again keeps what is judged", again["modules"]["1"]["rows"]["1.1.a"]["now"]["how"] == "kept")

        print("\n-- check")
        probs, notes = pr.check(c)
        for want in ("module 1, topic 1.1.a: now level must be 0-6", "module 2, topic 1.3: proposed 'why' is empty",
                     "now_summary is empty", "upgrades is empty"):
            check("stops on: " + want, any(want in p for p in probs), probs[:6])
        check("a module with no activity is only a note", not any("activity" in p for p in probs)
              and any("module 2: no teaching and learning activity" in n for n in notes), notes)
        rev = complete(c)
        probs, notes = pr.check(c)
        check("a judged course is clean", probs == [], probs)
        bad = copy.deepcopy(rev)
        bad["modules"]["1"]["rows"]["1.1.a"]["proposed"]["level"] = 1
        bad["modules"]["1"]["rows"]["1.1.a"]["now"]["level"] = 2
        bad["modules"]["2"]["rows"]["9.9"] = bad["modules"]["2"]["rows"]["1.3"]
        bad["upgrades"].append({"what": "More 3D"})
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(bad, ensure_ascii=False))
        probs, notes = pr.check(c)
        check("stops on a proposal below the old course", any("below what the old course reached" in p for p in probs), probs)
        check("stops on a row for a topic the architecture no longer has", any("topic 9.9: not a topic" in p for p in probs), probs)
        check("stops on an upgrade without its why", any("upgrade 2 needs" in p for p in probs), probs)
        low = copy.deepcopy(rev)
        low["modules"]["2"]["rows"]["1.3"]["proposed"]["level"] = 1
        low["modules"]["3"]["rows"]["1"]["proposed"]["level"] = 6
        low["modules"]["1"]["rows"]["1.1.b"]["now"] = {"level": 0, "how": "not in the old course", "checked": "not checked", "where": "-"}
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(low, ensure_ascii=False))
        probs, notes = pr.check(c)
        check("below what the outcome asks and Create are notes, never stops; level 0 is allowed now",
              probs == [] and any("still below what the outcome asks" in n for n in notes)
              and any("Create is reached by a practical exercise" in n for n in notes), (probs, notes))

        print("\n-- render")
        code, out = run("render", "--course", c, "--no-pdf")
        names = sorted(os.listdir(f["out"]))
        check("three documents, Word and HTML each", code == 0 and names == sorted(
            [d + x for d, _ in pr.DOCS for x in (".docx", ".html")] + ["fingerprint.txt"]), (out, names))
        now = docx_text(os.path.join(f["out"], "1_BLOOM_NOW.docx"))
        check("Bloom now: the outcome from the architecture, how it was taught and checked, where",
              tap.SUB_NEW in now and "slides" in now and "Checked: final test Q1" in now and "deck S1-S5" in now)
        check("... level 0 reads 'not taught'", "not taught" in now)
        new = io.open(os.path.join(f["out"], "2_BLOOM_PROPOSED.html"), encoding="utf-8").read()
        check("Bloom proposed: now -> proposed, how and why", "1 Remember -&gt; 3 Apply" in new and "sets the value on the panel" in new
              and "it is what the job needs" in new, new[:200])
        act = docx_text(os.path.join(f["out"], "3_TEACHING_ACTIVITIES.docx"))
        check("activities: what the trainees do, its kind, kept or struck, and the upgrades",
              "finds the tank that leans on the hull" in act and "Predict then reveal" in act and "kept" in act
              and "struck" in act and "Every self-check in two parts" in act)
        check("activities: minutes moved count only what is not struck", "doing, with every activity kept: 10 minutes" in act)
        check("every document has the expert's sign-off", all("Reviewed by" in docx_text(os.path.join(f["out"], d + ".docx"))
                                                                for d, _ in pr.DOCS))

        print("\n-- the Stage 2 approval")
        check("written from the current files, nothing stops the approval", pr.approval_problems(c) == [], pr.approval_problems(c))
        low["modules"]["2"]["rows"]["1.3"]["proposed"]["why"] = "changed after render"
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(low, ensure_ascii=False))
        check("an edit after render asks for the documents again",
              any("not written from the current files" in p for p in pr.approval_problems(c)), pr.approval_problems(c))
        n2 = tap.write_course(os.path.join(tmp, "none"), tap.PROGRAMME, copy.deepcopy(tap.ARCH))
        p = subprocess.run([sys.executable, os.path.join(HERE, "make_architecture_page.py"), "--course", n2, "--approve", "--by", "Anna"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("make_architecture_page --approve is refused without the documents",
              p.returncode == 2 and "pedagogy documents" in p.stdout and "NOT recorded" in p.stdout, p.stdout[-400:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
