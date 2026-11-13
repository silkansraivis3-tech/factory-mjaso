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


GROUP = [
    {"id": "g01", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Gas detection at the bench", "paper_part": "brief",
     "title": "Practical 1.1 - the brief", "text": "Pairs, one instrument set each.\nSafety: no naked lights at the drum.",
     "notes": "- Hand out the gas-test record.", "minutes": 5},
    {"id": "g02", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Gas detection at the bench", "title": "Your turn 1 - prepare the detector",
     "text": "1. Switch on in clean air.\n2. Apply the span gas.", "notes": "- Score each step 3-2-1.", "minutes": 15},
    {"id": "g03", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Gas detection at the bench", "title": "Your turn 2 - the drum",
     "text": "1. Test the drum at three levels.", "notes": "- A reading taken too early does not count.", "minutes": 15},
    {"id": "g04", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Gas detection at the bench", "paper_part": "debrief",
     "title": "Debrief", "text": "Which readings differed, and why?", "notes": "- Close with the two errors seen most.", "minutes": 5}]
HANDOVER = {"id": "x01", "kind": "activity", "sub_ilo": ["1.1"], "exercise": "1.2", "title": "Exercise 1.2 - bunkering on the simulator",
            "text": "We now go to the bunkering simulator, room K2 - 20 minutes.\nThe instructor hands out the exercise papers.",
            "notes": "- Run it from the instructor sheet.", "minutes": 20}
FORM = {"Course": "Basic training for ships subject to the IGF Code", "Exercise No.": "1.2", "Title": "Bunkering on the simulator",
        "Reference": "IMO MC 7.13 Part D exercise 3; LNGBunk p62", "Duration": "20 min",
        "Exercise Description": ["1. Line up the bunker station from the checklist (LNGBunk p62).", "2. Start the transfer at the minimum rate."],
        "Performance Criteria": ["PC1 - the ESD link is tested before the transfer.", "PC2 - the rate is raised only after the line is cold."]}


def practical_on_paper(tmp):
    """one practical over four screens is one paper; an approved simulator form is the simulator's paper"""
    print("\n-- a practical on paper: one paper for its screens, the approved form for a simulator exercise")
    c = course(os.path.join(tmp, "grp"))
    wc = os.path.join(c, "working_claude")
    sp = os.path.join(wc, "script", "M01.json")
    s = cs.load(sp)
    s["screens"] = t.SCREENS[:4] + GROUP + [HANDOVER] + t.SCREENS[4:]
    s["sources"].append("IMO Model Course 7.13: Part D, exercise 3")
    s["approved_hash"] = cs.content_hash(s)
    cs.save(sp, s)
    check("the script check passes a practical over four screens and a simulator screen that is only the handover",
          not [p for p in cs.validate(s) if "paper" in p or "handover" in p], cs.validate(s))
    arch = cs.load(os.path.join(wc, "architecture.json"))
    arch["modules"][0]["practicals"] = [
        {"task": "Gas detection at the bench (exercise 1.1)", "equipment": "M8 Tanku atmosfēras mērinstrumenti; M9 Pārnēsājamais skābekļa mēraparāts",
         "place": "practical room"},
        {"task": "Bunkering on the simulator (exercise 1.2)", "equipment": "Liquid cargo simulator (A2)", "place": "K2"}]
    cs.save(os.path.join(wc, "architecture.json"), arch)
    il_data = {"register": {"1.1": {"criteria": [{"text": "Zeroes the detector in clean air", "must_pass": True, "step": "M01.G02 1"}]}},
               "practicals": {"M01.G04": {"debrief": {"must_observe": ["Readings taken only after the sample arrived"]}}}}
    cs.save(os.path.join(wc, "instructor_led.json"), dict(il_data, status="approved", approved_by="Test", approved_hash=am.il.content_hash(il_data)))
    content = os.path.join(wc, "exercises", "sim_drafts", "M01", "content")
    os.makedirs(content)
    for who in ("trainee", "instructor"):
        cs.save(os.path.join(content, "EX_1.2_%s.json" % who), dict(FORM, **({"Instructor notes": ["Inject the ESD fault at 10 min."]}
                                                                              if who == "instructor" else {})))
    cov = {"proposed_tasks": [{"id": "P1", "module": "M01", "draft": "1.2"}]}
    cs.save(os.path.join(wc, "SIM_COVERAGE.json"), cov)
    code, out = run(TOOL, c, "--no-pdf")
    root = os.path.join(c, am.FOLDER)
    names = sorted(f for _, _, fs in os.walk(os.path.join(root, "simulator-and-equipment")) for f in fs)
    stem = "M01_G01-G04_gas_detection_at_the_bench"
    check("the four screens of one practical are one paper - its trainee card and its instructor sheet (the gas course printed "
          "six cards for one 80-minute practical, its brief and debrief among them)",
          stem + "_TRAINEE.docx" in names and not any(x.startswith(("M01_G01_", "M01_G02_", "M01_G04_")) for x in names), names)
    papers = os.path.join(c, "modules", "module01", "instructor", "papers")
    card, sheet = read(papers, stem + "_TRAINEE.html"), read(papers, stem + "_INSTRUCTOR.html")
    check("... the trainee card holds the trainees' parts, their own numbers once - no brief, no debrief, no instructor note",
          "<p>1. Switch on in clean air.</p>" in card and "Test the drum at three levels" in card and "Pairs, one instrument set" not in card
          and "Which readings differed" not in card and "Score each step" not in card, card[card.find("<h2"):][:900])
    check("... the instructor sheet holds every part in order, the brief and the debrief marked as the instructor's, each part's notes",
          all(x in sheet for x in ("Pairs, one instrument set", "the brief - the instructor's", "Score each step 3-2-1",
                                   "Which readings differed", "the debrief - the instructor's"))
          and sheet.find("Pairs, one instrument set") < sheet.find("Switch on") < sheet.find("Which readings differed"), sheet[:1500])
    check("... and the approved criteria (must pass, at its step), what the debrief must observe, the IMO model course and the sources",
          all(x in sheet for x in ("Assessment criteria", "Zeroes the detector in clean air", "must pass, step 1 of G02",
                                   "Must observe (G04):", "Readings taken only after the sample arrived", "IMO model course",
                                   "IMO Model Course 7.13: Part D, exercise 3", "ISGOTT, 6th edition"))
          and sheet.find("IMO Model Course 7.13") < sheet.find(">Sources<") < sheet.find("ISGOTT"), sheet[sheet.find("Marking"):][:1500])
    every = card + sheet + "".join(docx_text(os.path.join(dp, f)) for dp, _, fs in os.walk(root) for f in fs if f.endswith(".docx"))
    prep = json.dumps(cs.load(os.path.join(c, "modules", "classroom", "prepare.json")), ensure_ascii=False)
    check("the programme's Latvian equipment never prints on an English paper or list: its codes, and it is said",
          "Tanku" not in every + prep and "the programme's M8, M9" in sheet and "the programme's equipment M8, M9" in prep
          and "write \"equipment_en\"" in out, (out[-500:], prep[:600]))
    mp = read(c, "modules", "module01", "instructor", "advanced_module_plan.html")
    check("the module plan: the practical is one step with its parts, linked to its one paper",
          "G01-G04 - Gas detection at the bench" in mp and "Its parts" in mp and 'href="papers/%s_TRAINEE.html"' % stem in mp
          and mp.count("Practical exercise with real equipment") == 1, mp[mp.find("G01"):][:900])
    check("... the Prepare list prints it once", "Print: G01-G04 trainee card and instructor sheet - Gas detection at the bench" in prep, prep)
    x = "M01_X01_exercise_1_2_bunkering_on_the_simulator"
    check("a simulator draft nobody accepted is not printed - the handover screen's own card", "Performance Criteria" not in
          read(papers, x + "_INSTRUCTOR.html") and "hands out the exercise papers" in read(papers, x + "_TRAINEE.html"))
    cov["proposed_tasks"][0]["accepted_by"] = "A. Director"
    cs.save(os.path.join(wc, "SIM_COVERAGE.json"), cov)
    code, out = run(TOOL, c, "--no-pdf")
    tc, ic = read(papers, x + "_TRAINEE.html"), read(papers, x + "_INSTRUCTOR.html")
    check("accepted, the approved exercise form is the simulator's paper - its fields, its performance criteria, the manual's steps",
          all(x_ in tc for x_ in ("Trainee card 1.2", "Performance Criteria", "PC1 - the ESD link is tested", "<p>1. Line up the bunker station",
                                  "IMO MC 7.13 Part D exercise 3")) and "Inject the ESD fault" not in tc
          and "Inject the ESD fault" in ic and "Instructor sheet 1.2" in ic and "printed from its own fields" in ic, tc[:1500])
    bad = lambda **k: [p for p in cs.validate(dict(s, screens=t.SCREENS[:4] + k["screens"] + t.SCREENS[4:])) if "practical" in p or "handover" in p or "paper_part" in p]
    check("the script check: a screen between two parts of a practical", bad(screens=GROUP[:2] + [dict(HANDOVER, id="x09")] + GROUP[2:]))
    check("... a part that is none of brief, show, debrief", bad(screens=[dict(GROUP[0], paper_part="setup")] + GROUP[1:]))
    check("... a practical with nothing for the trainees", bad(screens=[GROUP[0], GROUP[3]]))
    check("... a simulator exercise's screen that lists steps instead of handing over",
          bad(screens=[dict(HANDOVER, text="We go to the simulator.\n1. Line up the station.\n2. Start the transfer.")]))


SIM_GROUP = [
    {"id": "s01", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Cargo plant layout", "paper_part": "brief", "track": "theory",
     "title": "To the LPG simulator", "text": "We now go to the LPG cargo handling simulator, room K2 - 20 minutes.",
     "notes": "- Load the cargo plant layout exercise before the class arrives.", "minutes": 3},
    {"id": "s02", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Cargo plant layout", "track": "theory",
     "title": "Trace the cargo lines", "text": "1. Open the cargo mimic (LCHS LPG manual p12).\n2. Trace the liquid line from the "
     "manifold to tank 1.", "notes": "- Check every pair traces the vapour return too.", "minutes": 14},
    {"id": "s03", "kind": "activity", "sub_ilo": ["1.1"], "paper": "Cargo plant layout", "paper_part": "debrief", "track": "theory",
     "title": "Debrief", "text": "Which valves did you pass?", "notes": "- Close with the ESD valves.", "minutes": 3}]


def model_course_simulator(tmp):
    """a simulator exercise the architecture plans from the model course is printed like any practical: its screens are its
    paper; a room activity before it is never taken for it, and one left unwritten is said"""
    print("\n-- a simulator exercise planned from the model course, on paper")
    c = course(os.path.join(tmp, "mcsim"))
    wc = os.path.join(c, "working_claude")
    arch = cs.load(os.path.join(wc, "architecture.json"))
    arch["modules"][0]["practicals"] = [{"task": "Cargo plant layout on the LPG cargo handling simulator", "track": "theory",
                                         "equipment": "LPG cargo handling simulator", "place": "K2", "model_course": ["1.2"]}]
    cs.save(os.path.join(wc, "architecture.json"), arch)
    sp = os.path.join(wc, "script", "M01.json")

    def build(screens):
        s = cs.load(sp)
        s["screens"] = t.SCREENS[:4] + screens + t.SCREENS[4:]
        s["approved_hash"] = cs.content_hash(s)
        cs.save(sp, s)
        return run(TOOL, c, "--no-pdf")
    code, out = build([ROOM] + SIM_GROUP)
    papers = os.path.join(c, "modules", "module01", "instructor", "papers")
    listing = json.loads(read(papers, "papers.json")) if os.path.isfile(os.path.join(papers, "papers.json")) else {}
    stem = "M01_S01-S03_cargo_plant_layout"
    check("its screens are one simulator paper - trainee card and instructor sheet on the instructor's tablet, listed in "
          "papers.json with their HTML and PDF; the room activity before it is not taken for the simulator's",
          listing == {"papers": [{"id": "S01-S03", "title": "Cargo plant layout", "kind": "simulator",
                                  "trainee": {"html": stem + "_TRAINEE.html", "pdf": stem + "_TRAINEE.pdf"},
                                  "instructor": {"html": stem + "_INSTRUCTOR.html", "pdf": stem + "_INSTRUCTOR.pdf"}}]}
          and "Trace the liquid line" in read(papers, stem + "_TRAINEE.html")
          and "Load the cargo plant layout" in read(papers, stem + "_INSTRUCTOR.html")
          and "simulator exercise(s)" not in out, (listing, out[-600:]))
    code, out = build([ROOM])
    check("... a simulator exercise the architecture plans and the script leaves out is said - nothing would print its papers",
          "M01: the architecture plans 1 simulator exercise(s) (Cargo plant layout on the LPG cargo handling simulator) and the "
          "script has 0 on paper" in out, out[-800:])
    code, out = build([dict(HANDOVER, exercise="4.1", title="Exercise 4.1 - cargo plant layout on the simulator")])
    check("... and a simulator screen naming an exercise whose approved form is not there - its paper would be the handover alone",
          "names exercise 4.1 and no approved form" in out, out[-800:])


def main():
    tmp = tempfile.mkdtemp(prefix="additional_materials_")
    try:
        # ---- the days, the kinds, the practicals
        long = "Practical - foam applicator and foam extinguisher on the training ship's deck"
        short_stem = am.stem_title(long)
        check("a long paper title is cut at a whole word to %d letters, and a short one is left as it is (a path past 260 "
              "characters could not be written)" % am.STEM_TITLE,
              len(short_stem) <= am.STEM_TITLE and short_stem == "practical_foam_applicator_and_foam" and long.lower().startswith(
                  "practical - foam applicator and foam") and am.stem_title("Bunkering") == "bunkering", short_stem)
        eq = ("Portable foam applicator set (medium-expansion branch pipe, inline inductor with pick-up tube, foam concentrate "
              "container, hose) and a portable foam extinguisher; the spare concentrate drums are kept in the foam store on deck")
        check("the paper's 'Place and equipment' shows the equipment whole, never cut mid-sentence",
              am.place_line({"place": "Training ship deck", "equipment": eq}).endswith(eq.replace("  ", " ")))
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
              on_tablet == sorted(["papers.json"] + [stem + x for x in ("_INSTRUCTOR.html", "_INSTRUCTOR.pdf", "_TRAINEE.html", "_TRAINEE.pdf")])
              and all(open(os.path.join(papers, x), "rb").read(5) == b"%PDF-" for x in on_tablet if x.endswith(".pdf")), on_tablet)
        listing = json.loads(read(papers, "papers.json")) if "papers.json" in on_tablet else {}
        check("... papers.json names each paper for the instructor app: code, title, kind and its four files, all present",
              listing == {"papers": [{"id": "A01", "title": "Practical - bunkering on the simulator", "kind": "simulator",
                                      "trainee": {"html": stem + "_TRAINEE.html", "pdf": stem + "_TRAINEE.pdf"},
                                      "instructor": {"html": stem + "_INSTRUCTOR.html", "pdf": stem + "_INSTRUCTOR.pdf"}}]}
              and all(f in on_tablet for p in listing["papers"] for w in ("trainee", "instructor") for f in p[w].values()), listing)
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

        practical_on_paper(tmp)
        model_course_simulator(tmp)

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
