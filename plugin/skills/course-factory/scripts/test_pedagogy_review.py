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
  * keep or lift: a proposal above both the old course and what the outcome asks is refused without 'above_why' (the
    task on board that needs it); a lift on an outcome whose level is unknown is refused; keeping the old level, also
    Remember, is always allowed;
  * a proposal below what the outcome asks is refused until 'limit' says what stops the course reaching it; an expert's
    decision (pedagogy_review.py expert) is carried out as it is, and asks for what the trainee does at that level;
  * one level a course: a lift of two or more levels is refused unless the expert decided it; a topic lifted one level
    and still below its outcome needs no 'limit' (the cap is the limit) - it is a note;
  * check only notes: a proposal below the outcome with its limit, Create, a module with no activity proposed;
  * the outcomes are the programme's: a proposal never re-words one ('revised_outcome' stops the check); an expert's
    decision may, in English - one in the programme's language (Latvian) stops the check (L19); the documents show the
    programme's own words beside it;
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
REVISED = "Apply the physical properties of liquefied gases to choose a safe cargo-handling step"


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
    asks = {(str(m["n"]), r["id"]): r["asks"] for m in pr.modules(pr._load(f["prog"], {}), pr._load(f["arch"])) for r in m["rows"]}
    for n, m in rev["modules"].items():
        for i, r in m["rows"].items():
            r["now"] = {"level": 1, "how": "slides", "checked": "final test Q1", "where": "deck S1-S5"}
            r["proposed"] = {"level": min(2, max(1, asks[(n, i)] or 1)), "how": "sets the value on the panel", "why": "it is what the job needs"}
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
        low["modules"]["1"]["rows"]["1.1.a"]["now"]["level"] = 5
        low["modules"]["1"]["rows"]["1.1.a"]["proposed"].update(level=6, above_why="the officer writes the containment plan")
        low["modules"]["1"]["rows"]["1.1.b"]["now"] = {"level": 0, "how": "not in the old course", "checked": "not checked", "where": "-"}
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(low, ensure_ascii=False))
        probs, notes = pr.check(c)
        check("below what the outcome asks is refused until 'limit' says what stops it",
              any("1.3: proposed 1 Remember is below what the outcome asks" in p for p in probs), probs)
        low["modules"]["2"]["rows"]["1.3"]["proposed"]["limit"] = "no detector to hand in the classroom"
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(low, ensure_ascii=False))
        probs, notes = pr.check(c)
        check("... with its limit, and Create, only notes; level 0 is allowed now",
              probs == [] and any("stays below what the outcome asks" in n and "no detector" in n for n in notes)
              and any("Create is reached by a practical exercise" in n for n in notes), (probs, notes))
        unknown = copy.deepcopy(rev)
        unknown["modules"]["3"]["rows"]["1"]["proposed"]["level"] = 2
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(unknown, ensure_ascii=False))
        check("a lift on an outcome whose level is unknown is refused", any("module 3, topic 1: a lift needs the level" in p
                                                                           for p in pr.check(c)[0]), pr.check(c)[0])

        print("\n-- keep or lift")
        asks = {r["id"]: r["asks"] for m in pr.modules(tap.PROGRAMME, arch) for r in m["rows"]}
        up = copy.deepcopy(low)
        top = up["modules"]["2"]["rows"]["1.3"]
        top["now"]["level"] = asks["1.3"] or 1
        top["proposed"]["level"] = (asks["1.3"] or 1) + 1
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        probs, _ = pr.check(c)
        check("above what the outcome asks is refused without above_why",
              any("1.3" in p and "above what the outcome asks" in p for p in probs), probs)
        top["proposed"]["above_why"] = "the officer zeroes the meter before every entry"
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        check("... and allowed with the task on board that needs it", pr.check(c)[0] == [], pr.check(c)[0])
        check("a lift above the outcome's verb never asks to re-word the outcome",
              not any("revised_outcome" in n for n in pr.check(c)[1]), pr.check(c)[1])
        top["proposed"]["revised_outcome"] = REVISED
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        check("the outcomes are the programme's: a proposal that re-words one stops the check (GAS BASIC: 7 re-worded)",
              any("1.3: the outcome is the programme's" in p for p in pr.check(c)[0]), pr.check(c)[0])
        top["proposed"]["expert"] = {"by": "Anna", "said": "Say it as it is done on board.", "on": "2026-11-06"}
        top["proposed"]["revised_outcome"] = "Pielietot zināšanas par sašķidrināto gāzu fizikālajām īpašībām"
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        check("... an expert's decision may, but one in the programme's language (Latvian) stops the check (L19)",
              any("1.3: 'revised_outcome' is in the programme's language" in p for p in pr.check(c)[0]), pr.check(c)[0])
        top["proposed"]["revised_outcome"] = REVISED
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        check("... in English it passes", pr.check(c)[0] == [], pr.check(c)[0])

        print("\n-- one level a course (GAS BASIC: 33 topics lifted two or three levels at once)")
        cap = copy.deepcopy(up)
        row = cap["modules"]["2"]["rows"]["1.3"]
        row["now"]["level"], row["proposed"]["level"] = 1, 3
        for k in ("above_why", "expert", "revised_outcome"):
            row["proposed"].pop(k, None)
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(cap, ensure_ascii=False))
        check("a lift of two levels is refused", any("1.3: 1 Remember to 3 Apply lifts it 2 levels" in p for p in pr.check(c)[0]),
              pr.check(c)[0])
        row["proposed"]["level"] = 2
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(cap, ensure_ascii=False))
        real_modules = pr.modules

        def asks_analyse(prog, arch_):                  # the outcome of 1.3 asks Analyse: one level up stays below it
            out = real_modules(prog, arch_)
            for m in out:
                for r in m["rows"]:
                    if r["id"] == "1.3":
                        r["asks"] = 4
            return out
        pr.modules = asks_analyse
        try:
            probs, notes = pr.check(c)
        finally:
            pr.modules = real_modules
        check("... one level is the lift, and below the outcome it needs no 'limit' - a note says the next course or the expert "
              "takes it further", not any("1.3" in p for p in probs) and any("1.3: proposed 2 Understand, one level above" in n
                                                                            for n in notes), (probs, notes))
        row["proposed"].update(level=4, expert={"by": "Anna", "said": "They run this on the simulator already.", "on": "2026-11-06"})
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(cap, ensure_ascii=False))
        check("... and the expert's decision lifts it further", not any("1.3" in p for p in pr.check(c)[0]), pr.check(c)[0])
        keep = copy.deepcopy(low)
        keep["modules"]["2"]["rows"]["1.3"]["now"]["level"] = 1
        keep["modules"]["2"]["rows"]["1.3"]["proposed"]["level"] = 1
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(keep, ensure_ascii=False))
        check("keeping Remember is allowed, with what stops more", not any("1.3" in p for p in pr.check(c)[0]), pr.check(c)[0])
        check("the decision is read the same way the documents say it",
              (pr.decision({"level": 2}, {"level": 2}, 3), pr.decision({"level": 1}, {"level": 2}, 2),
               pr.decision({"level": 1}, {"level": 4}, 2)) == ("kept", "lifted", "above the outcome"))
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        code, out = run("expert", "--course", c, "--module", "1", "--topic", "1.1.b", "--level", "5", "--said", "", "--by", "Anna")
        check("an expert's decision without their words records nothing", code == 2 and "nothing was recorded" in out, out)
        code, out = run("expert", "--course", c, "--module", "1", "--topic", "1.1.b", "--level", "5",
                        "--said", "They can judge a real loading plan here", "--by", "Anna")
        probs, _ = pr.check(c)
        ex = json.load(io.open(f["review"], encoding="utf-8"))["modules"]["1"]["rows"]["1.1.b"]["proposed"]
        check("the expert's decision is recorded and asks for what the trainee does at that level",
              code == 0 and ex["level"] == 5 and ex["expert"]["by"] == "Anna" and any("1.1.b: proposed 'how' is empty" in p for p in probs), (out, probs))
        up = json.load(io.open(f["review"], encoding="utf-8"))
        up["modules"]["1"]["rows"]["1.1.b"]["proposed"]["how"] = "judges a real loading plan and marks what is wrong"
        met = up["modules"]["1"]["rows"]["1.1"]
        met["now"]["level"] = met["proposed"]["level"] = asks["1.1"]
        io.open(f["review"], "w", encoding="utf-8").write(json.dumps(up, ensure_ascii=False))
        check("... and is carried out as it is: no keep-or-lift rule stops it", pr.check(c)[0] == [], pr.check(c)[0])
        low = up

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
        check("Bloom proposed: now -> proposed with its decision, how, why and the reason above the outcome",
              "-&gt;" in new and "kept" in new and "above the outcome" in new and "sets the value on the panel" in new
              and "it is what the job needs" in new and "Above the outcome: the officer zeroes the meter" in new, new[:200])
        check("the expert's decision shows with their words; a kept topic shows why it is kept",
              "the expert's decision" in new and "They can judge a real loading plan here" in new
              and "Kept because the old course already reaches what the outcome asks" in new and "Not higher because: no detector" in new,
              [x for x in ("the expert's decision", "They can judge", "Kept because the old course", "Not higher because")
               if x not in new])
        t13 = next((t for m in pr.view(c)["content"]["modules"] for t in m["topics"] if t["id"] == "1.3"), {})
        check("L19: the experts read the revised outcome in English, the programme's own words beside it",
              (t13.get("revised"), t13.get("intended")) == (REVISED, "Aprakstīt sašķidrināto gāzu vielu fizikālās īpašības")
              and t13.get("revised_verb", "").startswith("apply"), t13)
        check("... and the course's count of kept, lifted and above, and of each level before and after",
              "<td>Kept</td>" in new and "<td>Lifted</td>" in new and "<td>Above the outcome</td>" in new and "Old course" in new)
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
