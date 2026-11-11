# -*- coding: utf-8 -*-
"""test_additional_materials - the paper beside the tablets is made from the approved course, for every task.

    python test_additional_materials.py

Pinned:
  * the folder course\\additional-materials\\ holds the ACP (Word and HTML), one PDF and one Word file per task - every
    self-check, module check and room, simulator or equipment exercise - and, by day, the trainee card and instructor
    sheet of every simulator and equipment exercise; INDEX.html links every one of them;
  * the ACP goes day by day: the day's objectives (the Main ILOs, word for word), each module's topic, method, Sub-ILOs
    and used material, a module split across two days in both;
  * L19: a programme in Latvian - the ACP and the two tablet pages show its Main ILOs and Sub-ILOs in English, by the
    rendering beside them in architecture.json; one missing shows the programme's words and is said (exit 1);
  * the trainee card carries no answer and no instructor note; the task description carries both;
  * the two tablet pages (_course_shell\\advanced_course_plan.html, moduleNN\\instructor\\advanced_module_plan.html) stand
    alone - no stylesheet, script or link out - so the instructor panel can open them over itself;
  * days come from course.build.json "days" (a module, or a module's part in minutes) or fill the programme's day;
  * --check finds a missing file; a second build changes nothing; a task that is no longer made is moved aside, never
    deleted; an unapproved module gets nothing and is said;
  * the practical kit (L68) comes only from an approved instructor_led.json: by day, the pre-brief card (the stop word,
    the intervention rule), the debrief card with the observation card, the assessment form of a recorded run (its stop
    criterion marked, the changed condition), and the employer sheet with the honest decay figure.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_compile_module as t  # noqa: E402  - the same fixture script, the same runner
from test_compile_module import cs, run  # noqa: E402
import additional_materials as am  # noqa: E402

TOOL = os.path.join(HERE, "additional_materials.py")
PASS, FAIL = [], []
TITLE = "Basic training for ships subject to the IGF Code"
MAIN = [{"id": "1", "text": "Pārzināt gāzes kā degvielas īpašības;"}, {"id": "2", "text": "Droši veikt bunkurēšanu;"}]
OUT_LV = "Nosaukt jaunās telpas uz kuģa, kas izmanto gāzi kā degvielu"
SIM = {"id": "a01", "kind": "activity", "sub_ilo": ["1.1"], "title": "Practical - bunkering on the simulator",
       "text": "Liquid cargo simulator, room K2.\nPart 1 - line up the bunker station.\nPart 2 - start the transfer.",
       "notes": "- Key: the ESD link is tested first.", "minutes": 20}
ROOM = {"id": "a02", "kind": "activity", "sub_ilo": ["1.1"], "title": "Practical - read the bunker plan",
        "text": "Room K1. In pairs, read the plan on the exercise form.", "notes": "- Pairs compare.", "minutes": 10}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def read(*p):
    return io.open(os.path.join(*p), encoding="utf-8").read()


def docx_text(p):
    with zipfile.ZipFile(p) as z:
        return re.sub(r"<[^>]+>", "", z.read("word/document.xml").decode("utf-8"))


def course(tmp, minutes=None, days=None):
    """two approved modules: module 1 the fixture with a simulator and a room exercise, module 2 the fixture again"""
    c = os.path.join(tmp, "course")
    sdir = os.path.join(c, "working_claude", "script")
    os.makedirs(sdir)
    os.makedirs(os.path.join(c, "to_review"))
    screens = t.SCREENS[:4] + [SIM, ROOM] + t.SCREENS[4:]
    for n, sc in ((1, screens), (2, t.SCREENS)):
        s = t.script(screens=sc)
        s["module"], s["title"] = n, "IGF ships" if n == 1 else "Fuel systems"
        s["sources"] = ["IGF Code, 2016 edition: 2.2, 5.3 (spaces)", "ISGOTT, 6th edition"]
        s["approved_hash"], s["approved_on"] = cs.content_hash(s), "2026-11-01"
        cs.save(os.path.join(sdir, "M%02d.json" % n), s)
        os.makedirs(os.path.join(c, "modules", "module%02d" % n, "instructor"))
    wc = os.path.join(c, "working_claude")
    cs.save(os.path.join(wc, "architecture.json"), {
        "course": {"title": TITLE, "course_language": "English", "title_programme": "IGF pamatkurss"}, "main_ilos": MAIN,
        "modules": [{"module": 1, "main_ilos": ["2", "1"], "sub_ilos": [{"id": "1.1", "text": "Name the new spaces."}],
                     "practicals": [{"task": "Bunkering on the simulator", "equipment": "Liquid cargo simulator (A2)", "place": "K2"}]},
                    {"module": 2, "main_ilos": ["2"]}],
        "final_assessment": {"questions": 20, "pass_mark": "70 %"}})
    cs.save(os.path.join(wc, "programme.json"), {
        "academic_hour_min": 45, "max_hours_per_day": minutes / 45.0 if minutes else 8, "days": 3,
        "total_row": {"total": 2}, "rooms": {"K2": "Simulator room"}, "literature": {"L1": "IGF Code"}})
    if days:
        cs.save(os.path.join(wc, "course.build.json"), {"days": days})
    return c


def main():
    tmp = tempfile.mkdtemp(prefix="additional_materials_")
    try:
        # ---- the days, the kinds, the practicals
        mods = [{"n": 1, "minutes": 300.0}, {"n": 2, "minutes": 200.0}]
        probs = []
        d = am.days_of(mods, {"academic_hour_min": 40, "max_hours_per_day": 10}, {}, 0, probs)
        check("days fill the programme's day: 400 min, module 1 whole, module 2 split 100 + 100",
              [[(m["n"], take, k, of, at) for m, take, k, of, at in row] for row in d]
              == [[(1, 300.0, 1, 1, 0.0), (2, 100.0, 1, 2, 0.0)], [(2, 100.0, 2, 2, 100.0)]], d)
        d = am.days_of(mods, {"academic_hour_min": 40}, {"days": [[1, {"module": 2, "minutes": 50}], [2]]}, 0, probs)
        check("course.build.json \"days\" places a module's part by its minutes, the rest on its next day",
              [[(m["n"], take, at) for m, take, k, of, at in row] for row in d] == [[(1, 300.0, 0.0), (2, 50.0, 0.0)], [(2, 150.0, 50.0)]], d)
        probs = []
        am.days_of(mods, {}, {"days": [[1, {"module": 2, "minutes": 50}]]}, 0, probs)
        check("... and minutes that do not add up to the script's are said", any("module 2 50 min" in p for p in probs), probs)
        check("a task is simulator, equipment or room by its words",
              [am.classify(x) for x in ("Liquid cargo simulator, room K2", "At the enclosed space rig with the gas detectors",
                                        "Room K1, in pairs, on the exercise form", "Šķidras kravas simulators (A2)")]
              == ["simulator", "equipment", "room", "simulator"])
        check("... and course.build.json \"paper_tasks\" overrides it", am.classify("Room K1", "equipment") == "equipment")
        acts = [{"id": "a01", "title": "Practical 9.2 - stowage"}, {"id": "a02", "title": "Practical 9.1 - loading plan"}]
        prac = [{"task": "Cargo planning (old exercise 9.1)"}, {"task": "Stowage (old exercise 9.2)"}]
        got = am.match_practicals(acts, prac)
        check("an exercise is matched to its practical by the number both name, else in order",
              got["a01"] is prac[1] and got["a02"] is prac[0], got)
        steps = {"n": 8, "title": "Gas measuring", "script": {"screens": []}, "build": {}}
        task = {"code": "A03", "title": "Prepare the detector", "kind": "equipment", "where": "equipment", "minutes": 15, "questions": [],
                "sub_ilos": [], "practical": {}, "slide": {"id": "a03", "kind": "activity",
                                                         "text": "Each trainee, with their own detector:\n1. Switch on in clean air.\n2. Apply the gas."}}
        page = am.to_html("card", am.task_paper(steps, task, "Gas", {}, trainee=True))
        check("steps that carry their own numbers are printed once numbered (the gas course's cards read \"2. 1. Check the battery\")",
              "<p>1. Switch on in clean air.</p>" in page and "<ol>" not in page, page[page.find("<h2"):][:400])

        # ---- a built folder
        c = course(os.path.join(tmp, "one"), minutes=30)
        code, out = run(TOOL, c)
        root = os.path.join(c, am.FOLDER)
        check("built: exit 0", code == 0, out)
        files = sorted(os.path.relpath(os.path.join(dp, f), root).replace("\\", "/") for dp, _, fs in os.walk(root) for f in fs)
        tasks = ["M01_SC1_the_new_spaces", "M01_A01_practical_bunkering_on_the_simulator", "M01_A02_practical_read_the_bunker_plan",
                 "M01_MC_module_check_module_1", "M02_SC1_the_new_spaces", "M02_MC_module_check_module_1"]
        want = ["INDEX.html", "acp/ACP_basic_training_for_ships_subject_to_the_igf_code.docx",
                "acp/ACP_basic_training_for_ships_subject_to_the_igf_code.html"] + \
               ["practical-tasks/%s/%s.%s" % (k, s, k) for s in tasks for k in ("pdf", "docx")]
        missing = [x for x in want if x not in files]
        check("the folder: the ACP in Word and HTML, every task (2 self-checks, 2 module checks, 2 exercises) as PDF and Word",
              not missing, missing or files)
        sim = [x for x in files if x.startswith("simulator-and-equipment/")]
        check("the simulator exercise, and only it, is in its day's print folder: trainee card (PDF, Word), instructor sheet",
              len(sim) == 3 and all("M01_A01" in x for x in sim) and any(x.endswith("_TRAINEE.pdf") for x in sim)
              and any(x.endswith("_TRAINEE.docx") for x in sim) and any(x.endswith("_INSTRUCTOR.pdf") for x in sim)
              and re.match(r"simulator-and-equipment/Day_\d/", sim[0]), sim)
        pdfs = [os.path.join(root, x) for x in files if x.endswith(".pdf")]
        check("every PDF is a PDF", pdfs and all(open(p, "rb").read(5) == b"%PDF-" for p in pdfs), [p for p in pdfs if open(p, "rb").read(5) != b"%PDF-"])
        index = read(root, "INDEX.html")
        check("INDEX.html links every file", all(x in index for x in want[1:] + sim), index[:800])

        acp = docx_text(os.path.join(root, want[1]))
        check("the ACP in Word: the auditor's columns, each day, the Main ILOs word for word, a module's Sub-ILOs and used material",
              all(x in acp for x in ("Advanced Course Plan", "Training objectives", "Programme topic", "Training method", "Day 1",
                                     "Day 2", MAIN[0]["text"], "1.1 Name the new spaces.", "IGF Code, 2016 edition", "IGF pamatkurss")), acp[:900])
        check("... a source's cited sections stay in the script - the ACP names the book", "5.3 (spaces)" not in acp, acp[:900])
        check("... a module split across two days is in both, with its part", "part 1 of 2" in acp and "part 2 of 2" in acp, acp[:1500])
        check("... the day's objectives in the Main ILOs' order", acp.find(MAIN[0]["text"], acp.find("Training objectives")) <
              acp.find(MAIN[1]["text"], acp.find("Training objectives")), acp[:900])
        check("... the exercise and the module check name their way of training", "Practical exercise A01" in acp
              and "on the simulator" in acp and "Module check on the trainee tablets" in acp, acp[:1500])
        with zipfile.ZipFile(os.path.join(root, want[1])) as z:
            numbering, body = z.read("word/numbering.xml").decode("utf-8"), z.read("word/document.xml").decode("utf-8")
        used = set(re.findall(r'<w:numId w:val="(\d+)"/>', body)) - {"1"}
        check("... every numbered list in Word counts from 1, never on from the list before",
              len(used) >= 3 and all(re.search(r'<w:num w:numId="%s"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0">'
                                               r'<w:startOverride w:val="1"/>' % n, numbering) for n in used), (used, numbering[-400:]))
        check("... the final assessment and a line for the person responsible", "20 questions, pass mark 70 %" in acp
              and "person responsible for implementation" in acp, acp[-600:])

        desc = docx_text(os.path.join(root, "practical-tasks", "docx", "M01_SC1_the_new_spaces.docx"))
        check("a task description: what the trainee does, the choices, the right answer, the feedback, the instructor's note",
              all(x in desc for x in ("Where is the fuel prepared?", "Fuel preparation room", "Right answer", "Pumps and vaporizers",
                                      "Press OPEN TASK", "Self-check on the trainee tablet", "Marking")), desc)
        card = [x for x in sim if x.endswith("_TRAINEE.docx")][0]
        ct = docx_text(os.path.join(root, card))
        check("the trainee card: the steps, the place and equipment - no answer, no instructor note",
              "line up the bunker station" in ct and "Liquid cargo simulator (A2)" in ct and "ESD link is tested" not in ct
              and "Right answer" not in ct and "For the instructor" not in ct, ct)
        sheet = docx_text(os.path.join(root, "practical-tasks", "docx", "M01_A01_practical_bunkering_on_the_simulator.docx"))
        check("... the instructor sheet carries the note", "ESD link is tested" in sheet, sheet)

        cp = read(c, "modules", "_course_shell", "advanced_course_plan.html")
        mp = read(c, "modules", "module01", "instructor", "advanced_module_plan.html")
        alone = lambda p: not re.search(r"<link\b|<script\b|\bsrc=", p) and all(h.startswith("papers/") for h in re.findall(r'\bhref="([^"]*)"', p))
        check("the tablet's course plan and module plan stand alone: no stylesheet, script or link out - the module plan's "
              "only links are to its own papers", alone(cp) and alone(mp) and "href=" not in cp)
        stem = "M01_A01_practical_bunkering_on_the_simulator"
        papers = os.path.join(c, "modules", "module01", "instructor", "papers")
        on_tablet = sorted(os.listdir(papers)) if os.path.isdir(papers) else []
        check("the simulator exercise's trainee card and instructor sheet are on the instructor's tablet too, beside the module "
              "plan, to open and to print (the instructor app had no way to reach the papers: additional-materials never ships)",
              on_tablet == sorted(stem + x for x in ("_INSTRUCTOR.html", "_INSTRUCTOR.pdf", "_TRAINEE.html", "_TRAINEE.pdf"))
              and all(open(os.path.join(papers, x), "rb").read(5) == b"%PDF-" for x in on_tablet if x.endswith(".pdf")), on_tablet)
        check("... the module plan's step for it links each one, and nothing else is linked",
              all('href="papers/%s%s"' % (stem, x) in mp for x in ("_TRAINEE.html", "_TRAINEE.pdf", "_INSTRUCTOR.html", "_INSTRUCTOR.pdf"))
              and len(re.findall(r"\bhref=", mp)) == 4, re.findall(r'href="[^"]*"', mp))
        tc, ic = read(papers, stem + "_TRAINEE.html"), read(papers, stem + "_INSTRUCTOR.html")
        check("... the trainee card holds no answer and no instructor note, the sheet holds the note; both stand alone in the viewer",
              "line up the bunker station" in tc and "ESD link is tested" not in tc and "ESD link is tested" in ic
              and all('name="gb-standalone"' in x and "<script" not in x and "@page{size:A4" in x for x in (tc, ic)), tc[:600])
        check("... a room exercise has no paper on the tablet", not any("M01_A02" in x for x in on_tablet), on_tablet)
        check("... the module plan goes step by step: what is taught, the self-check, the exercise and its paper, the check",
              all(x in mp for x in ("Module 1 - step by step", "Step 1", "You teach", "The Code (4 min)", "SC1",
                                    "Practical exercise on the simulator A01", "M01_A01_practical_bunkering_on_the_simulator_TRAINEE.pdf",
                                    "Module check")), mp[:1500])
        check("... its Sub-ILOs in words, and the day each part falls on", "Name the new spaces." in mp and "Day 1" in mp, mp[:900])

        code, out = run(TOOL, c)
        check("built again: nothing changed", code == 0 and "Nothing changed" in out, out)
        code, out = run(TOOL, c, "--check")
        check("--check: complete and up to date", code == 0 and "complete and up to date" in out, out)
        os.remove(os.path.join(root, "practical-tasks", "pdf", "M01_SC1_the_new_spaces.pdf"))
        code, out = run(TOOL, c, "--check")
        check("--check finds a missing PDF, and writes nothing", code == 1 and "M01_SC1_the_new_spaces.pdf" in out
              and not os.path.isfile(os.path.join(root, "practical-tasks", "pdf", "M01_SC1_the_new_spaces.pdf")), out)

        # ---- the practical kit (L68): cards, assessment form, employer sheet - from the approved instructor_led.json
        k = course(os.path.join(tmp, "kit"), minutes=30)
        kroot = os.path.join(k, am.FOLDER)
        guide = {"practicals": {"M01.A01": {
            "cycle": [{"kind": "brief", "min": 3}, {"kind": "show", "min": 4}, {"kind": "run", "min": 8}, {"kind": "debrief", "min": 5}],
            "practice_runs": 2, "prebrief": {"objective": "Line up the bunker station and start the transfer.", "roles": "Pairs.",
                                             "safety": ["The ESD link is tested first."], "stop_word": "STOP"},
            "debrief": {"must_observe": ["ESD link tested first", "Hoses purged before connection"]}}},
            "employer": {"can_do": ["Line up a bunker station", "Test the ESD link", "Start a transfer"],
                         "decays": "The line-up order.", "drill": "15 minutes: the ESD test with the ship's own link.",
                         "watch_for": ["The ESD link tested every time", "A standby who says no"], "refresher": "Revalidation does not retrain it."}}
        cs.save(il_path := os.path.join(k, "working_claude", "instructor_led.json"), guide)
        code, out = run(TOOL, k, "--no-pdf")
        check("instructor_led.json not approved: no kit, and it is said", "practical kit (cards, assessment forms, employer sheet) waits" in out
              and not os.path.isdir(os.path.join(kroot, "practical-kit")), out)
        approve = lambda d: cs.save(il_path, dict(d, status="approved", approved_by="Test", approved_hash=am.il.content_hash(d)))
        approve(guide)
        code, out = run(TOOL, k, "--no-pdf")
        kit_files = sorted(os.path.relpath(os.path.join(dp, f), kroot).replace("\\", "/") for dp, _, fs in os.walk(kroot) for f in fs
                           if "practical-kit" in dp)
        stem = "M01_A01_practical_bunkering_on_the_simulator"
        check("the simulator exercise's pre-brief and debrief cards in its day's folder, the employer sheet - no assessment form "
              "for a practice run", any(re.match(r"practical-kit/Day_\d/%s_PREBRIEF\.docx$" % stem, x) for x in kit_files)
              and any(x.endswith(stem + "_DEBRIEF.docx") for x in kit_files) and not any("ASSESSMENT" in x for x in kit_files)
              and "practical-kit/EMPLOYER_SHEET_basic_training_for_ships_subject_to_the_igf_code.docx" in kit_files, kit_files)
        kd = lambda suffix: docx_text(os.path.join(kroot, next(x for x in kit_files if x.endswith(suffix))))
        pb = kd("_PREBRIEF.docx")
        check("the pre-brief card: objective, practice, roles, safety, the stop word, the intervention rule (R10)",
              all(x in pb for x in ("Line up the bunker station", "Today is practice. Nothing is marked.", "Pairs.",
                                    "The ESD link is tested first.", "STOP. Anyone says it", "I will watch and stay quiet",
                                    "read aloud before the run, 3 min")), pb)
        db = kd("_DEBRIEF.docx")
        check("the debrief card: reactions first, the must-observe items, the two prompts, the close - and the observation card",
              all(x in db for x in ("Reactions (2 min)", "1. ESD link tested first", "2. Hoses purged", "what did you see, and what did you decide",
                                    "One change for the next run", "Observation card", "Time / step", "5 min, after the run")), db)
        emp = kd("EMPLOYER_SHEET_basic_training_for_ships_subject_to_the_igf_code.docx")
        check("the employer sheet: can do, decays (with the honest figure in comparable training), drill, watch for, refresher",
              all(x in emp for x in ("Line up a bunker station", "The line-up order.", "In comparable training", "15 minutes: the ESD test",
                                     "A standby who says no", "Revalidation does not retrain it.")), emp)
        # ---- the classroom files the tablet app reads on publish: prepare.json always, a form only for a recorded run
        import classroom_files as cf
        cdir = os.path.join(k, "modules", "classroom")
        prep = json.loads(read(cdir, "prepare.json"))
        m1 = [x["label"] for x in prep["modules"].get("module01", [])]
        check("prepare.json is written beside the modules: the practice run's cards to print, its safety brief - no assessment form yet",
              any(x.startswith("Print: pre-brief, debrief and observation cards - A01") for x in m1)
              and any(x.startswith("Safety brief ready - A01: The ESD link is tested first.") for x in m1)
              and not any("assessment form" in x for x in m1), m1)
        check("the employer sheet is on the course list; no recorded run, so no assessor line and no forms folder",
              [x["label"] for x in prep["course"]].count("Print: the employer sheet") == 1
              and not any("assessor" in x["label"] for x in prep["course"]) and not os.path.isdir(os.path.join(cdir, "forms")), prep["course"])
        check("what the build wrote passes the package checks (limits, kinds, module codes)", cf.folder_problems(os.path.join(k, "modules"),
              ["module01"]) == [], cf.folder_problems(os.path.join(k, "modules"), ["module01"]))
        check("INDEX.html lists the kit by day", "Practical kit" in read(kroot, "INDEX.html")
              and stem + "_PREBRIEF.pdf" in read(kroot, "INDEX.html"))
        rec = json.loads(json.dumps(guide))
        rec["practicals"]["M01.A01"].update(recorded=True, practice_of="M00.A01", changed_condition="the ESD link fails on the first test",
                                            form={"critical": [{"step": "Tests the ESD link", "stop": False},
                                                               {"step": "Stops the transfer when the link fails", "stop": True}]})
        approve(rec)
        code, out = run(TOOL, k, "--no-pdf")
        form = docx_text(os.path.join(kroot, "practical-kit", "Day_1", stem + "_ASSESSMENT.docx")) \
            if os.path.isfile(os.path.join(kroot, "practical-kit", "Day_1", stem + "_ASSESSMENT.docx")) else ""
        check("a recorded run gets its assessment form: critical steps with the stop criterion marked, global rating, decision, "
              "run details with the changed condition",
              all(x in form for x in ("A. Critical steps", "Tests the ESD link", "STOP: Stops the transfer", "3 Performs safely unprompted",
                                      "Yes / Not yet", "two re-attempts at most", "the ESD link fails on the first test")), form or out)
        check("... and its pre-brief card says it is recorded", "This run is recorded on the assessment form" in kd("_PREBRIEF.docx"))
        forms_dir = os.path.join(cdir, "forms")
        fnames = sorted(os.listdir(forms_dir)) if os.path.isdir(forms_dir) else []
        ft = json.loads(read(forms_dir, fnames[0])) if fnames else {}
        fd = ft.get("definition") or {}
        crit = [c for s in fd.get("sections", []) for c in s["criteria"]]
        check("a recorded run gets one form file named by its code (course, module, task), with its critical steps as pass / fail rows "
              "and the stop step marked", len(fnames) == 1 and fnames[0] == ft.get("code", "?") + ".json" and cf.FORM_CODE.match(ft["code"])
              and ft["code"].endswith("-M01-A01") and [c["label"] for c in crit[:2]] == ["Tests the ESD link", "STOP: Stops the transfer when the link fails"]
              and all(c["scale"] == "pass_fail" for c in crit[:2]), (fnames, ft))
        check("... with the global rating (1-4 with the paper's words), the decision (yes / no) and the changed condition in the header; "
              "the app's form rules accept it", [c["key"] for c in crit[2:]] == ["global_rating", "decision"]
              and [m["mark"] for m in fd["scale_meanings"]["0-4"]] == ["1", "2", "3", "4"]
              and any("the ESD link fails on the first test" in h["label"] for h in fd["header_fields"])
              and cf.definition_problems(fd) == [] and cf.folder_problems(os.path.join(k, "modules"), ["module01"]) == [], cf.definition_problems(fd))
        prep = json.loads(read(cdir, "prepare.json"))
        check("the recorded run adds the form to print and an assessor to name",
              any(x["label"].startswith("Print: assessment form, one per candidate - A01") for x in prep["modules"]["module01"])
              and any("assessor" in x["label"] for x in prep["course"]), prep)
        code, out = run(TOOL, k, "--no-pdf", "--check")
        check("--check finds both files current after a build", not any("classroom" in x for x in out.splitlines()), out[-400:])
        approve(guide)
        code, out = run(TOOL, k, "--no-pdf")
        check("the run no longer recorded: its form file is moved aside, never deleted",
              (not os.path.isdir(forms_dir) or not os.listdir(forms_dir))
              and any(f == fnames[0] for _, _, fs in os.walk(os.path.join(k, "working_claude", "additional_materials", "old")) for f in fs), out[-400:])
        approve(rec)
        code, out = run(TOOL, k, "--no-pdf")

        # ---- L19: the programme is in Latvian, the course is in English
        lv = course(os.path.join(tmp, "lv"), minutes=30)
        wl = os.path.join(lv, "working_claude")
        prog = cs.load(os.path.join(wl, "programme.json"))
        cs.save(os.path.join(wl, "programme.json"), dict(prog, language="Latvian", outcomes={"1.1": OUT_LV}))
        arch = cs.load(os.path.join(wl, "architecture.json"))
        arch["main_ilos"] = [dict(x, text_en=en) for x, en in zip(MAIN, ("Know the properties of gas as fuel", "Bunker safely"))]
        arch["modules"][0]["sub_ilos"] = [{"id": "1.1", "status": "original", "text_en": "Name the new spaces of a gas-fuelled ship"}]
        cs.save(os.path.join(wl, "architecture.json"), arch)
        am.ilo_map.build(lv, quiet=True)
        code, out = run(TOOL, lv, "--no-pdf")
        lroot = os.path.join(lv, am.FOLDER)
        acp_lv = docx_text(os.path.join(lroot, want[1]))
        tab = read(lv, "modules", "_course_shell", "advanced_course_plan.html") + read(lv, "modules", "module01", "instructor",
                                                                                      "advanced_module_plan.html")
        check("the ACP and the tablet's two plans: the Main ILOs and the kept Sub-ILO in English - the rendering written at Stage 2",
              "English rendering" not in out and all(x in acp_lv + tab for x in ("Know the properties of gas as fuel", "Bunker safely",
                                                             "1.1 Name the new spaces of a gas-fuelled ship"))
              and "Name the new spaces of a gas-fuelled ship" in tab, (code, out[-500:], acp_lv[:900]))
        check("... and no word of the programme's Latvian", not any(x in acp_lv + tab for x in (MAIN[0]["text"], MAIN[1]["text"], OUT_LV)),
              [x for x in (MAIN[0]["text"], MAIN[1]["text"], OUT_LV) if x in acp_lv + tab])
        del arch["main_ilos"][1]["text_en"], arch["modules"][0]["sub_ilos"][0]["text_en"]
        cs.save(os.path.join(wl, "architecture.json"), arch)
        code, out = run(TOOL, lv, "--no-pdf")
        check("a rendering missing: the programme's words are shown, and it is said - never silent (exit 1)",
              code == 1 and MAIN[1]["text"] in docx_text(os.path.join(lroot, want[1]))
              and "the programme is in Latvian and Main ILO 2, Sub-ILO 1.1 have no English rendering" in out, (code, out[-600:]))

        s = cs.load(os.path.join(c, "working_claude", "script", "M01.json"))
        s["screens"] = [x for x in s["screens"] if x["id"] != "a02"]
        s["minutes_allocated"] -= 10
        s["approved_hash"] = cs.content_hash(s)
        cs.save(os.path.join(c, "working_claude", "script", "M01.json"), s)
        code, out = run(TOOL, c)
        old = os.path.join(c, "working_claude", "additional_materials", "old")
        moved = [f for _, _, fs in os.walk(old) for f in fs]
        check("a task no longer in the script: its files are moved aside, never deleted",
              code == 0 and not os.path.isfile(os.path.join(root, "practical-tasks", "docx", "M01_A02_practical_read_the_bunker_plan.docx"))
              and "M01_A02_practical_read_the_bunker_plan.docx" in moved and "Moved aside" in out, out)

        s["status"] = "draft"
        cs.save(os.path.join(c, "working_claude", "script", "M02.json"), dict(s, module=2))
        code, out = run(TOOL, c, "--no-pdf")
        check("an unapproved module gets nothing, and it is said", code == 1 and "module02: its content script is not approved" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
