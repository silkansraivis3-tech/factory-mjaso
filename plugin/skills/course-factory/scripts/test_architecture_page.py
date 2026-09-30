# -*- coding: utf-8 -*-
"""test_architecture_page - the Stage 2 page: one module per programme topic, the two tablets, and
what the operator's "next" approves, in two languages that never mix.

    python test_architecture_page.py

The example is invented - a four-topic programme written in Latvian, taught in English, reviewed by
a Latvian-speaking operator. Pinned (owner, 2026-09-30 - L34, L35, L36):
  * every programme topic is its own module, in the programme's order, with the programme's hours;
    the final-assessment topic is the LAST module and the assessment only; the modules total to the
    programme's own total row; an academic hour is 40 min when the programme is silent;
  * the page says how the course runs: slides on the instructor tablet, tasks only on the trainee
    tablet, opened by OPEN TASK, no task list; the trainee sees their own score on self-checks and
    module checks, which do not count; only the final assessment is graded;
  * every module shows where its minutes go; a module too short for a self-check has none, and a
    plan with more self-checks than the theory time allows is caught;
  * programme text appears exactly as written, marked with the programme's language; module titles
    with the course language; headings in the operator's language; Sub-ILOs beside the programme
    wording, kept / re-expressed / added;
  * merged topics, teaching inside the assessment, a missing module check, an assessment that is not
    last, hours that do not match, a total that does not match, and the older checks are all caught;
  * the page is one file, fetches nothing, has a print layout, and never ships to a tablet.
"""
from __future__ import annotations

import copy
import html
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
LABELS = json.load(io.open(os.path.join(os.path.dirname(HERE), "knowledge", "page-labels.json"), encoding="utf-8"))
LV, EN = LABELS["lv"], LABELS["en"]
PASS, FAIL = [], []

MAIN1 = "Veicināt drošas kravas operācijas uz sašķidrinātās gāzes tankkuģiem"
OUT11 = "Identificēt sašķidrinātās gāzes tankkuģu tipus un aprakstīt to uzbūvi"
SUB_NEW = "Identify the cargo containment system of a liquefied gas tanker from its general arrangement plan"

PROGRAMME = {
    "source": "Programma X, Rev. 1", "academic_hour_min": 40, "language": "Latvian",
    "topics": {
        "1": {"theory": 2, "practical": 0, "title": "Sašķidrinātās gāzes tankkuģi", "ref": "6. Mācību plāns, p. 5",
              "subtopics": [{"ref": "1.1", "title": "Sašķidrinātās gāzes tankkuģu tipi"}]},
        "2": {"theory": 1, "practical": 1, "title": "Gāzu mērinstrumenti", "ref": "6. Mācību plāns, p. 5"},
        "3": {"theory": 0.25, "practical": 0, "title": "Ugunsdzēšanas vielas", "ref": "6. Mācību plāns, p. 6"},
        "4": {"theory": 1, "practical": 0, "title": "Noslēguma pārbaudījums", "ref": "6. Mācību plāns, p. 7", "assessment": True}},
    "total_row": {"theory": 4.25, "practical": 1, "total": 5.25},
    "main_ilos": {"1": MAIN1}, "outcomes": {"1.1": OUT11, "1.3": "Aprakstīt sašķidrināto gāzu vielu fizikālās īpašības"}}
ARCH = {
    "course": {"title": "Basic training for liquefied gas tanker cargo operations", "course_language": "English",
               "operator_language": "lv", "course_type": "NEW_ENTRANT", "programme_file": "source_files/programme.pdf",
               "model_course": "IMO model course 1.04"},
    "main_ilos": [{"id": "1", "text": MAIN1, "ref": "p. 2"}],
    "modules": [
        {"module": 1, "title": "Gas tankers", "main_ilos": ["1"],
         "sub_ilos": [{"id": "1.1", "status": "original"},
                      {"id": "1.1.a", "status": "re-expressed", "programme_text": OUT11, "text": SUB_NEW,
                       "why": "Lai to varētu apgūt praktiski, pie rasējuma"},
                      {"id": "1.1.b", "status": "added", "text": "Recognise the tank type from a photograph", "why": "Operatora lūgums"}],
         "active_learning": [{"where": "tank types", "instead_of": "lecture", "technique": "predict-then-reveal"}],
         "self_checks": [{"questions": 4, "after": "after 1.1"}, {"questions": 4}], "module_check": {"questions": 6}},
        {"module": 2, "title": "Gas measuring instruments", "main_ilos": ["1"],
         "sub_ilos": [{"id": "1.3", "status": "original"}],
         "practicals": [{"task": "Take an oxygen reading", "equipment": "Pārnēsājamais skābekļa mēraparāts", "place": "bench", "minutes": 40}],
         "self_checks": 1, "module_check": {"questions": 5}},
        {"module": 3, "title": "Extinguishing agents", "main_ilos": ["1"], "module_check": {"questions": 5}}],
    "final_assessment": {"questions": 30, "pass_mark": "70 %", "graded": True, "ref": "3. p. 4"},
    "notes": ["Piezīme operatoram."]}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:300]) if detail and not ok else ""))


def write_course(d, prog, arch, plan=None):
    os.makedirs(d, exist_ok=True)
    for n, v in (("programme.json", prog), ("architecture.json", arch), ("plan.json", plan)):
        if v is not None:
            io.open(os.path.join(d, n), "w", encoding="utf-8").write(json.dumps(v, ensure_ascii=False))
    return d


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def page_of(c):
    return io.open(os.path.join(c, "ARCHITECTURE_REVIEW.html"), encoding="utf-8").read()


def en(key, **kw):
    return EN[key].format(**kw) if kw else EN[key]


def main():
    tmp = tempfile.mkdtemp(prefix="arch_")
    try:
        print("-- one module per programme topic; the last is the assessment only")
        c = write_course(os.path.join(tmp, "ok"), PROGRAMME, ARCH)
        code, out = run("--course", c, "--check")
        check("a correct course has no problems - and needs no plan.json", code == 0, out)
        code, out = run("--course", c)
        page = page_of(c)
        check("the page is written, and says how many modules", code == 0 and "4 modules - one per programme topic" in out, out)
        rows = re.findall(r'<tr(?: class="assess")?><td class="n">(\d+)</td>', page)
        check("the overview has one row per programme topic, in the programme's order", rows == ["1", "2", "3", "4"], rows)
        check("the programme's final assessment is the last module, marked assessment only",
              re.search(r'<tr class="assess"><td class="n">4</td>.*?%s' % re.escape(LV["assessment_only"]), page, re.S) is not None)
        check("... and its section says: no slides, no teaching", LV["assessment_only_long"] in page)
        check("minutes are the programme's hours x 40 min", '<td class="n">80</td>' in page and '<td class="n">10</td>' in page)
        check("the modules total to the programme's own total row, and it says so",
              LV["total_row_line"].format(th="4.25", pr="1", tot="5.25") in page and LV["matches"] in page)
        check("what 'next' approves names the split", LV["approves_split"].format(n=4, t=3, last=4) in page)

        print("\n-- how the course runs: two tablets")
        for k in ("tablets_title", "tab_i1", "tab_i3", "tab_t2", "tab_t3", "tab_t4", "tab_scores"):
            check("the page says: " + EN[k][:60], html.escape(LV[k]) in page, k)
        check("self-checks: the trainee sees their own score, not counted", LV["test_sc"].format(k=1, q=4) in page)
        check("the final assessment is the only graded test", LV["graded"] in page)

        print("\n-- where every module's minutes go")
        m1 = page[page.find('<div class="module"><h2>'):]
        m1 = m1[:m1.find('<div class="module">', 10)]
        check("module 1: slides + two self-checks + the module check = 80 min",
              LV["budget_slides"] in m1 and "66 min" in m1 and LV["budget_sc"].format(k=2, q=4, after=LV["after_theory"].format(min=10)) in m1
              and LV["budget_mc"].format(q=6) in m1 and "80 min" in m1, m1[:1200])
        check("a module with practice shows the practice minutes", LV["budget_practice"] in page)
        check("a 10-minute module has no self-check - its module check covers it", LV["test_no_sc"].format(min=10) in page)

        print("\n-- two languages that never mix")
        check("the page is in the operator's language (lv)", '<html lang="lv">' in page and LV["page_title"] in page)
        check("programme text is word for word, marked with the programme's language",
              '<span class="verb" lang="lv">%s</span>' % MAIN1 in page and '<span class="verb" lang="lv">Sašķidrinātās gāzes tankkuģi</span>' in page)
        check("sub-topics are shown word for word", '<span class="verb" lang="lv">Sašķidrinātās gāzes tankkuģu tipi</span>' in page)
        check("module titles are in the course language", '<span class="verb" lang="en">Gas tankers</span>' in page)
        row = re.search(r"<tr><td>1\.1</td>.*?</tr>", page, re.S)
        check("a kept Sub-ILO takes its wording from the programme's own outcomes", row and OUT11 in row.group(0) and LV["status_original"] in row.group(0))
        row = re.search(r"<tr><td>1\.1\.a</td>.*?</tr>", page, re.S)
        check("a re-expressed Sub-ILO shows the programme wording and the new wording side by side",
              row and OUT11 in row.group(0) and SUB_NEW in row.group(0) and LV["status_re-expressed"] in row.group(0))
        row = re.search(r"<tr><td>1\.1\.b</td>.*?</tr>", page, re.S)
        check("an added Sub-ILO is marked added, with its reason",
              row and LV["status_added"] in row.group(0) and "Operatora lūgums" in row.group(0))
        a2 = copy.deepcopy(ARCH); a2["course"]["operator_language"] = "en"
        c2 = write_course(os.path.join(tmp, "en"), PROGRAMME, a2)
        run("--course", c2)
        p2 = page_of(c2)
        check("headings follow the operator; the programme text does not change",
              EN["page_title"] in p2 and LV["page_title"] not in p2 and '<span class="verb" lang="lv">%s</span>' % MAIN1 in p2)
        p_no_ahm = copy.deepcopy(PROGRAMME); del p_no_ahm["academic_hour_min"]
        c4 = write_course(os.path.join(tmp, "noahm"), p_no_ahm, a2)
        run("--course", c4)
        check("a programme that does not state the academic hour: 40 min, and the page says so",
              "40 min — " + EN["ahm_assumed"] in page_of(c4) and '<td class="n">80</td>' in page_of(c4))

        print("\n-- what the page must catch before the operator approves")
        bad = copy.deepcopy(ARCH)
        bad["course"]["operator_language"] = "en"
        bad["modules"][0]["module_check"]["graded"] = True
        bad["modules"][1].pop("module_check")
        bad["modules"][2]["self_checks"] = 1
        bad["modules"].append({"module": 4, "title": "Final", "self_checks": 1, "sub_ilos": [{"id": "9", "status": "added", "why": "x"}]})
        bad["modules"].append({"module": 7, "title": "Not in the programme", "module_check": {"questions": 5}})
        bad["modules"][0]["topics"] = ["1", "2"]
        bad["final_assessment"]["graded"] = False
        bad["modules"][0]["sub_ilos"][1].pop("programme_text")
        bad["modules"][0]["sub_ilos"][1]["id"] = "1.9"
        del bad["modules"][0]["sub_ilos"][2]["why"]
        bad["modules"][0]["sub_ilos"].append({"id": "1.3", "status": "original", "programme_text": "Aprakstīt īpašības"})
        bad["main_ilos"][0]["text"] = MAIN1 + " un terminālos"
        bad_prog = copy.deepcopy(PROGRAMME)
        bad_prog["total_row"]["practical"] = 2
        c3 = write_course(os.path.join(tmp, "bad"), bad_prog, bad, {"modules": [{"module": 1, "built_min": 120}]})
        code, out = run("--course", c3, "--check")
        check("--check fails", code == 1, out)
        for what, needle in (
                ("two topics merged into one module", en("p_one_topic", m=1, ts="1, 2")),
                ("teaching inside the final assessment", en("p_assessment_only", m=4)),
                ("a teaching module with no module check", en("p_no_module_check", m=2)),
                ("more self-checks than the theory time allows", en("p_selfcheck_room", m=3, k=1, need="18", have="10", min=10)),
                ("a module the programme does not have", en("p_module_not_topic", m=7)),
                ("a total that does not match the programme's total row", en("p_total_row", th="4.25", pr="1", pth="4.25", ppr="2")),
                ("hours that do not match the programme", en("p_hours", m=1, alloc="80", built="120")),
                ("a re-expressed Sub-ILO without the programme wording", en("p_no_wording", m=1, s="1.9", st="re-expressed")),
                ("an added Sub-ILO without a reason", en("p_added_why", m=1, s="1.1.b")),
                ("a 'kept' Sub-ILO that is not the programme's wording", en("p_sub_not_verbatim", m=1, s="1.3")),
                ("a Main ILO that is not word for word", en("p_main_not_verbatim", i="1")),
                ("a graded module check", en("p_module_check_graded", m=1)),
                ("an ungraded final assessment", en("p_final_not_graded"))):
            check("caught: " + what, needle in out, out)
        p5 = copy.deepcopy(PROGRAMME)
        p5["topics"]["5"] = {"theory": 1, "practical": 0, "title": "Pēc pārbaudījuma"}
        p5["total_row"] = {"theory": 5.25, "practical": 1}
        a5 = copy.deepcopy(a2); a5["modules"].append({"module": 5, "module_check": {"questions": 5}})
        code, out = run("--course", write_course(os.path.join(tmp, "notlast"), p5, a5), "--check")
        check("caught: the final assessment is not the last module", en("p_assessment_not_last", t="4") in out, out)
        p6 = copy.deepcopy(PROGRAMME); p6["topics"]["4"].pop("assessment")
        code, out = run("--course", write_course(os.path.join(tmp, "noassess"), p6, a2), "--check")
        check("caught: no final-assessment topic marked", en("p_no_assessment") in out, out)
        run("--course", c3)
        p3 = page_of(c3)
        check("the problems are at the top of the page, before what 'next' approves",
              0 <= p3.find(EN["problems_title"]) < p3.find(EN["approves_title"].replace('"', "&quot;")))

        print("\n-- one file that opens anywhere")
        check("the page fetches nothing from the internet", not re.search(r"""(src|href)\s*=\s*["']?https?:""", page) and "@import" not in page)
        check("the page has a print layout", "@media print" in page)
        check("the style is inside the page", "--navy" in page and "<link" not in page)

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
    print("\nOne module per programme topic, the assessment last and alone, the two tablets on the page, and\n"
          "every module's minutes accounted for - programme text exact, the rest in the operator's language.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
