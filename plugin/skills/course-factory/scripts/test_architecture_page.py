# -*- coding: utf-8 -*-
"""test_architecture_page - the Stage 2 page shows what the operator's "next" approves, in two
languages that never mix.

    python test_architecture_page.py

The example is invented - an English course reviewed by a Latvian-speaking operator. Pinned:
  * programme text, Main ILOs and Sub-ILO wording appear EXACTLY as written, marked with the course
    language; headings and explanations are in the operator's language;
  * every Sub-ILO is shown beside the programme's own wording, marked kept / re-expressed / added;
  * every module's hours list the programme topics and rows they come from, and a plan that
    disagrees with the programme is shown as a problem at the top;
  * a graded module check, an ungraded final assessment, a re-expressed Sub-ILO with no programme
    wording, an added one with no reason, and an unclaimed topic are all caught;
  * the page is one file, fetches nothing, and has a print layout.
"""
from __future__ import annotations

import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "make_architecture_page.py")
PASS, FAIL = [], []

MAIN1 = "Contribute to the safe cargo operation of liquefied gas tankers"
SUB_PROG = "Describe the basic design features of liquefied gas tankers"
SUB_NEW = "Identify the cargo containment system of a liquefied gas tanker from its general arrangement plan"

PROGRAMME = {
    "source": "Programme X, Rev. 1", "academic_hour_min": 45,
    "topics": {
        "1": {"theory": 2, "practical": 0, "title": "Design and characteristics of gas tankers", "ref": "Table 1, row 1"},
        "2": {"theory": 1, "practical": 1, "title": "Physical properties of liquefied gases", "ref": "Table 1, row 2"},
        "3": {"theory": 1, "practical": 0, "title": "Final assessment", "ref": "Table 1, row 3"}},
    "total_row": {"theory": 4, "practical": 1, "total": 5},
    "main_ilos": {"1": MAIN1}}
PLAN = {"outside_modules": [{"topic": "3", "hours": 1, "why": "final assessment"}],
        "modules": [{"module": 1, "topics": ["1"], "built_min": 90}, {"module": 2, "topics": ["2"], "built_min": 90}]}
ARCH = {
    "course": {"title": "Basic training for liquefied gas tanker cargo operations", "course_language": "English",
               "operator_language": "lv", "course_type": "NEW_ENTRANT", "programme_file": "source_files/programme.pdf",
               "model_course": "IMO model course 1.04"},
    "main_ilos": [{"id": "1", "text": MAIN1, "ref": "p. 2"}],
    "modules": [
        {"module": 1, "title": "Gas tankers", "main_ilos": ["1"],
         "sub_ilos": [{"id": "1.1", "status": "re-expressed", "programme_text": SUB_PROG, "text": SUB_NEW,
                       "why": "Lai to varētu apgūt praktiski, pie rasējuma"},
                      {"id": "1.2", "status": "added", "text": "Recognise the tank type from a photograph", "why": "Operatora lūgums"},
                      {"id": "1.3", "status": "original", "programme_text": "List the types of gas tankers"}],
         "active_learning": [{"where": "tank types", "instead_of": "lecture", "technique": "predict-then-reveal"}],
         "practicals": [{"task": "Identify the containment system", "equipment": "LNG membrane tanker simulator", "place": "simulator", "minutes": 30}],
         "self_checks": 3, "module_check": {"questions": 8, "graded": False}},
        {"module": 2, "title": "Properties of liquefied gases", "main_ilos": ["1"],
         "sub_ilos": [{"id": "2.1", "status": "original", "programme_text": "Explain boiling point and vapour pressure"}],
         "self_checks": 2, "module_check": {"questions": 6, "graded": False}}],
    "final_assessment": {"questions": 30, "pass_mark": "70 %", "graded": True, "ref": "Programme, section 5"},
    "notes": ["Piezīme operatoram."]}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:300]) if detail and not ok else ""))


def write_course(d, prog, plan, arch):
    os.makedirs(d, exist_ok=True)
    for n, v in (("programme.json", prog), ("plan.json", plan), ("architecture.json", arch)):
        io.open(os.path.join(d, n), "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False))
    return d


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="arch_")
    try:
        print("-- a correct course: the page, in two languages")
        c = write_course(os.path.join(tmp, "ok"), PROGRAMME, PLAN, ARCH)
        code, out = run("--course", c, "--check")
        check("a correct course has no problems", code == 0, out)
        code, out = run("--course", c)
        page = io.open(os.path.join(c, "ARCHITECTURE_REVIEW.html"), encoding="utf-8").read()
        check("the page is written into the course folder", code == 0, out)
        check("the page is in the operator's language (lv)", '<html lang="lv">' in page and "Kursa uzbūve" in page)
        check("the Main ILO appears word for word, marked as the course language",
              '<span class="verb" lang="en">%s</span>' % MAIN1 in page)
        check("programme topic titles appear word for word", "Design and characteristics of gas tankers" in page)
        check("each module's hours name the programme rows they come from",
              "Table 1, row 1" in page and "Table 1, row 2" in page)
        check("a plan that matches the programme says so", "atbilst programmai" in page)
        row = re.search(r"<tr><td>1\.1</td>.*?</tr>", page, re.S)
        check("a re-expressed Sub-ILO shows the programme wording and the new wording side by side",
              row and SUB_PROG in row.group(0) and SUB_NEW in row.group(0) and "pārformulēts" in row.group(0), row and row.group(0))
        row = re.search(r"<tr><td>1\.2</td>.*?</tr>", page, re.S)
        check("an added Sub-ILO is marked added, with no programme wording and its reason",
              row and "pievienots" in row.group(0) and "programmā nav" in row.group(0) and "Operatora lūgums" in row.group(0))
        check("the count of changes is in what 'next' approves", "1 pārformulēti, 1 pievienoti, 2 atstāti" in page)
        check("the test plan: module checks not graded, the final graded",
              page.count("bez vērtējuma") >= 2 and "vienīgais vērtētais" in page)
        check("equipment is taken as available", "uzskatīts par pieejamu" in page)
        check("the page fetches nothing from the internet", not re.search(r"""(src|href)\s*=\s*["']?https?:""", page) and "@import" not in page)
        check("the page has a print layout", "@media print" in page)
        check("the style is inside the page (it opens anywhere)", "--navy" in page and "<link" not in page)

        print("\n-- the same course for an English-speaking operator")
        a2 = copy.deepcopy(ARCH); a2["course"]["operator_language"] = "en"
        c2 = write_course(os.path.join(tmp, "en"), PROGRAMME, PLAN, a2)
        run("--course", c2)
        p2 = io.open(os.path.join(c2, "ARCHITECTURE_REVIEW.html"), encoding="utf-8").read()
        check("headings follow the operator; the course text does not change",
              "Course architecture" in p2 and "Kursa uzbūve" not in p2 and '<span class="verb" lang="en">%s</span>' % MAIN1 in p2)

        print("\n-- what the page must catch before the operator approves")
        bad_plan = copy.deepcopy(PLAN); bad_plan["modules"][0]["built_min"] = 120
        bad = copy.deepcopy(ARCH)
        bad["modules"][0]["module_check"]["graded"] = True
        bad["final_assessment"]["graded"] = False
        del bad["modules"][0]["sub_ilos"][0]["programme_text"]
        del bad["modules"][0]["sub_ilos"][1]["why"]
        bad["main_ilos"][0]["text"] = MAIN1 + " and terminals"
        bad["course"]["operator_language"] = "en"
        bad_prog = copy.deepcopy(PROGRAMME); bad_prog["topics"]["4"] = {"theory": 1, "practical": 0, "title": "Extra"}
        c3 = write_course(os.path.join(tmp, "bad"), bad_prog, bad_plan, bad)
        code, out = run("--course", c3, "--check")
        check("--check fails", code == 1, out)
        for what, needle in (("hours that do not match the programme", "the programme rows give 90 min, the plan says 120 min"),
                             ("a topic in no module", "Programme topic 4 is in no module"),
                             ("a re-expressed Sub-ILO without the programme wording", "Sub-ILO 1.1: marked \"re-expressed\""),
                             ("an added Sub-ILO without a reason", "Sub-ILO 1.2: added, but the reason"),
                             ("a Main ILO that is not word for word", "Main ILO 1 is not word for word"),
                             ("a graded module check", "Module checks are not graded"),
                             ("an ungraded final assessment", "It is the only graded test")):
            check("caught: " + what, needle in out, out)
        run("--course", c3)
        p3 = io.open(os.path.join(c3, "ARCHITECTURE_REVIEW.html"), encoding="utf-8").read()
        check("the problems are at the top of the page, before what 'next' approves",
              0 <= p3.find("the factory found these") < p3.find("What your &quot;next&quot; approves") and "does NOT match the programme" in p3)
        print("\n-- the review page and its inputs never ship to a tablet")
        skills = os.path.dirname(os.path.dirname(HERE))
        sys.path.insert(0, os.path.join(skills, "course-tablet-publisher", "scripts"))
        import gates
        plat = gates.load_platform()
        repo = os.path.join(tmp, "repo")
        base = os.path.join(repo, plat["asset_roots"]["trainee"], "courses", "x", "")
        for n in ("ARCHITECTURE_REVIEW.html", "programme.json", "plan.json", "architecture.json"):
            check("the publisher sorts %s as INTERNAL" % n, gates.classify(repo, plat, base + n) == "INTERNAL",
                  gates.classify(repo, plat, base + n))
        check("... while a trainee page still ships", gates.classify(repo, plat, base + "index.html") != "INTERNAL")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe page shows what the operator's \"next\" approves: the hours with their programme rows, every\n"
          "Sub-ILO beside its programme wording, the test plan - course text exact, the rest in their language.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
