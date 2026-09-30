# -*- coding: utf-8 -*-
"""test_content_script - Stage 3: the words are approved before the HTML, the lesson is shown on the
two tablets it runs on, there is enough theory before every task, and nothing changes unasked.

    python test_content_script.py

The example module is invented but written to the floors of knowledge/theory-rules.json. The
operator's Word edits are simulated by editing the file's XML the way Word writes it (a real Word
round trip is run separately when Word is installed - see MANIFEST 4h). Pinned:
  * TWO TABLETS (L35): part 1 of the review is the instructor tablet - every slide, and a "task
    starts" slide with the OPEN TASK button where a task begins; part 2 is the trainee tablet - the
    tasks only, each opened by its task slide, one question per screen, ending on the trainee's own
    score. No question is ever on a slide;
  * ENOUGH THEORY (L36): a clean module passes; a thin slide, thin notes, a module whose words do
    not fill its minutes, a self-check after too little theory, a question whose answer was not
    taught before it, a task written onto its slide and a self-check with too few questions are all
    found, shown at the top of the page and in the Word file, and block approval unless the operator
    approves despite them - which is recorded. Every question shows the slide that teaches its answer;
  * structure: a task no task slide opens, questions not straight after their task slide, a missing
    module check, a slide after the module check and minutes that do not add up are caught;
  * the Word file and the pending list: an untouched file reads back as nothing; typed text, tracked
    changes, comments, a deleted box and text outside the boxes are found and NOT applied; apply needs
    --confirmed, logs each change, keeps the old file; approval is undone by any later change;
  * the slide-text check (2.16.1) still runs on every screen;
  * check_script_match passes a module that says exactly the approved words, and fails a changed
    word, an extra sentence, a missing screen, a wrong correct answer and an unapproved script.
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
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "content_script.py")
MATCH = os.path.join(HERE, "check_script_match.py")
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
LV, EN = cs.LABELS["lv"], cs.LABELS["en"]
PASS, FAIL = [], []

S01_TEXT = ("Liquefied gases are carried as liquids only because the ship keeps them cold, under pressure, or both.\n"
            "LNG is mostly methane and boils at about -162 °C at atmospheric pressure, so it is carried fully refrigerated.\n"
            "Propane boils at -42 °C and butane at -0.5 °C; small ships carry them fully pressurised at ambient temperature.\n"
            "If the containment fails, the liquid boils off at once and forms a heavy, cold vapour cloud that can burn, explode or displace oxygen.\n"
            "Tanks, pipes, valves, gas detection and emergency shutdown all exist to keep the cargo liquid and inside its containment.")
S01_NOTES = ("Start by asking who has sailed on a gas tanker and what cargo it carried. Write the three boiling points on the board and ask the room "
             "what happens to a liquid at -162 °C when it touches a warm steel deck. Make the point that boil-off never stops and must be managed. "
             "Link each piece of equipment named on the slide to the module where it is taught in detail, so trainees see one system, not separate topics. "
             "Finish with a real case: a small leak at a manifold flange during discharge, the white cloud on deck, the gas alarm, and the ESD "
             "that stopped the pumps and closed the valves within seconds - that is what the next modules teach them to understand.")
S02_TEXT = ("Fully pressurised ships carry LPG and ammonia at ambient temperature in pressure vessels designed for about 18 bar; most are under 5,000 m³.\n"
            "Semi-pressurised, semi-refrigerated ships cool the cargo and hold it at about 5 to 7 bar, down to about -48 °C, or -104 °C for ethylene.\n"
            "Fully refrigerated ships carry large LPG cargoes at about -50 °C and LNG at about -162 °C, just above atmospheric pressure.\n"
            "The colder the cargo, the less pressure the tank must hold - and the more insulation and boil-off handling the ship needs.")
S02_NOTES = ("Draw a simple pressure-temperature line for propane and mark the three ship types on it, so the room sees that one cargo can be carried "
             "in three ways. Ask which type suits a short coastal trade and which a long ocean voyage, and why. Point out the ethylene carrier as the "
             "special case of the semi-refrigerated ship, and say that the IGC Code sets the design standard for all three. "
             "Close by asking one trainee to explain, in their own words, why a fully refrigerated LNG tank needs no heavy pressure vessel "
             "while a small LPG ship does - if they can, the room is ready for the self-check.")
S03_TEXT = ("The IGC Code names four cargo containment systems.\n"
            "Independent type A tanks are prismatic, built for less than 0.7 bar, and need a full secondary barrier.\n"
            "Independent type B tanks - spherical Moss tanks or prismatic SPB tanks - are designed in such detail that a partial secondary barrier is enough.\n"
            "Independent type C tanks are pressure vessels, cylindrical or bilobe, and need no secondary barrier at all.\n"
            "Membrane tanks are thin metal barriers that rely on the hull, through the insulation, for their strength, and need a full secondary barrier.")
S03_NOTES = ("Show the cutaway and let the room name each tank type before you do. Ask why a pressure vessel needs no secondary barrier while a membrane "
             "tank needs a full one. The answer - how likely a leak is, and how far it could spread - is the idea the whole IGC Code is built on, "
             "so spend the time here. "
             "Then ask where on the ship they would expect the secondary barrier to be for each type, and correct the answers against the cutaway; "
             "trainees who later work on membrane ships will meet interbarrier spaces and their gas detection every day.")

SCRIPT = {
    "module": 1, "title": "Gas tankers", "course_language": "English", "operator_language": "lv", "status": "draft",
    "minutes_allocated": 23,
    "operator_facts": [{"fact": "On our simulator the ESD button is on the left console.", "where": "s03"}],
    "screens": [
        {"id": "s01", "kind": "slide", "title": "Why gas tankers are different", "text": S01_TEXT,
         "visual": "Photograph of a membrane LNG carrier alongside", "notes": S01_NOTES, "minutes": 5},
        {"id": "s02", "kind": "slide", "title": "Three ways to keep the cargo liquid", "text": S02_TEXT,
         "visual": "Pressure-temperature line for propane with the three ship types marked", "notes": S02_NOTES, "minutes": 5},
        {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - keeping the cargo liquid",
         "text": "A short self-check opens on your tablet now: three questions on why gas is carried cold or under pressure.",
         "notes": "Press OPEN TASK. Give three minutes and watch who hesitates.", "minutes": 3},
        {"id": "q01", "kind": "self-check", "set": "SC1", "question": "At what temperature is LNG carried near atmospheric pressure?",
         "options": ["About -162 °C", "At room temperature, under pressure", "About -42 °C"], "correct": "A",
         "feedback": "LNG is fully refrigerated: about -162 °C, just above atmospheric pressure.", "mechanic": "tap to choose"},
        {"id": "q02", "kind": "self-check", "set": "SC1", "question": "Which ships carry LPG at ambient temperature?",
         "options": ["Fully refrigerated ships", "Fully pressurised ships", "Membrane LNG carriers"], "correct": "B",
         "feedback": "Fully pressurised ships hold LPG at ambient temperature in pressure vessels.", "mechanic": "tap to choose"},
        {"id": "q03", "kind": "self-check", "set": "SC1", "question": "Which ship type carries ethylene at about -104 °C?",
         "options": ["Fully pressurised", "Semi-pressurised, semi-refrigerated", "None - ethylene is not carried"], "correct": "B",
         "feedback": "Ethylene is carried on semi-refrigerated ships, at about -104 °C.", "mechanic": "tap to choose"},
        {"id": "s03", "kind": "slide", "title": "Four containment systems", "text": S03_TEXT,
         "visual": "Cutaway of type A, B, C and membrane tanks", "notes": S03_NOTES, "minutes": 5},
        {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - gas tankers",
         "text": "The module check opens on your tablet now: five questions on the whole module. Your score is for you.",
         "notes": "Press OPEN TASK when the room is ready.", "minutes": 5},
        {"id": "m01", "kind": "module-check", "set": "MC", "question": "Which tank type relies on the hull for its strength?",
         "options": ["Type C", "Membrane", "Type A"], "correct": "B", "feedback": "Membrane tanks are supported by the hull.", "mechanic": "tap to choose"},
        {"id": "m02", "kind": "module-check", "set": "MC", "question": "What is LNG mostly?",
         "options": ["Propane", "Methane", "Ammonia"], "correct": "B", "feedback": "LNG is mostly methane.", "mechanic": "tap to choose"},
        {"id": "m03", "kind": "module-check", "set": "MC", "question": "Which independent tank needs no secondary barrier?",
         "options": ["Type A", "Type B", "Type C"], "correct": "C", "feedback": "Type C tanks are pressure vessels.", "mechanic": "tap to choose"},
        {"id": "m04", "kind": "module-check", "set": "MC", "question": "Roughly what pressure are fully pressurised LPG tanks designed for?",
         "options": ["About 18 bar", "About 0.25 bar", "About 1 bar"], "correct": "A", "feedback": "About 18 bar.", "mechanic": "tap to choose"},
        {"id": "m05", "kind": "module-check", "set": "MC", "question": "What forms when liquefied gas escapes its containment?",
         "options": ["A cold vapour cloud", "Solid ice only", "Nothing - it stays liquid"], "correct": "A",
         "feedback": "It boils off at once into a heavy, cold vapour cloud.", "mechanic": "tap to choose"}]}

W = cs.W


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def cs_run(*a):
    return run(TOOL, *a)


def new_course(tmp, name, script=SCRIPT):
    c = os.path.join(tmp, name)
    os.makedirs(os.path.join(c, "_factory", "script"))
    io.open(os.path.join(c, "_factory", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(script, ensure_ascii=False))
    io.open(os.path.join(c, "FEEDBACK_LOG.md"), "w", encoding="utf-8").write(
        "# log\n\n| # | Date | Stage · module · where | What the operator said | What changed | Operator-stated fact? |\n|---|---|---|---|---|---|\n"
        "| 1 | 2026-10-01 | 3 · M01 · s02 | type C tanks here are tested to 7 bar | used it | yes |\n")
    return c


def edit_docx(path, fn):
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    doc = parts["word/document.xml"].decode("utf-8")
    doc, extra = fn(doc)
    parts["word/document.xml"] = doc.encode("utf-8")
    parts.update(extra)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in parts.items():
            z.writestr(n, b)


def box(doc, tag):
    return re.search(r'<w:sdt><w:sdtPr><w:alias[^>]*/><w:tag w:val="%s"/>.*?</w:sdt>' % re.escape(tag), doc, re.S)


def screen(script, sid):
    return [x for x in script["screens"] if x["id"] == sid][0]


def rules_of(script):
    return [f["rule"] for f in cs.theory_findings(script)[0]]


def lv(key, **kw):
    return html.escape(LV[key].format(**kw) if kw else LV[key])


def main():
    tmp = tempfile.mkdtemp(prefix="cs_")
    try:
        print("-- render: the lesson on its two tablets")
        c = new_course(tmp, "c1")
        code, out = cs_run("render", c, "--module", "1")
        p = cs.paths(c, 1)
        page = io.open(p["review"], encoding="utf-8").read()
        check("render writes the review page and the Word file, with no problems", code == 0 and os.path.isfile(p["docx"]) and "problems" not in out, out)
        check("the page is in the operator's language, the course text marked English",
              '<html lang="lv">' in page and '<span class="verb" lang="en">Four containment systems</span>' in page)
        part2 = page.find(lv("s_part2"))
        part1 = page.find(lv("s_part1"))
        check("part 1 is the instructor tablet, part 2 the trainee tablet", 0 < part1 < part2, (part1, part2))
        slides_at = [page.find('<span class="sid">%s</span>' % x) for x in ("s01", "s02", "t01", "s03", "t02")]
        tasks_at = [page.find('<span class="sid">%s</span>' % x) for x in ("q01", "q02", "q03", "m01", "m05")]
        check("every slide is in part 1, in teaching order", slides_at == sorted(slides_at) and part1 < slides_at[0] and slides_at[-1] < part2, slides_at)
        check("every task is in part 2 - never among the slides", all(x > part2 for x in tasks_at), tasks_at)
        check("no question text appears on the instructor tablet part",
              all(html.escape(screen(SCRIPT, q)["question"]) not in page[:part2] for q in ("q01", "m01")))
        check("a task slide carries the OPEN TASK button and says what it opens",
              page[:part2].count('<span class="openbtn">') == 2 and lv("s_opens", set=LV["s_sc_name"].format(k=1), q=3) in page)
        check("the self-check says the trainee sees their own score, not counted",
              lv("s_self_check") in page and page.count(lv("s_result_own")) == 2 and lv("s_result", q=3) in page)
        check("one question per screen, numbered within its task", lv("s_question_n", q=2, of=3) in page and lv("s_question_n", q=5, of=5) in page)
        check("each question shows the slide that teaches its answer",
              re.search(r"q01</span>.*?%s</dt><dd>%s" % (re.escape(lv("s_taught_on")), re.escape(lv("s_slide_n", n=1))), page, re.S) is not None
              and re.search(r"m01</span>.*?%s</dt><dd>%s" % (re.escape(lv("s_taught_on")), re.escape(lv("s_slide_n", n=4))), page, re.S) is not None)
        check("the module in numbers: minutes against the programme's, words per theory minute",
              lv("s_sum_alloc", a="23") in page and lv("s_sum_title") in page)
        check("a clean module: the theory check found nothing", lv("s_theory_clean") in page and lv("s_textcheck_clean") in page)
        check("operator-stated facts listed once - from the script and from FEEDBACK_LOG.md",
              "left console" in page and "tested to 7 bar" in page and page.count(lv("s_facts_title")) == 1)
        doc = zipfile.ZipFile(p["docx"]).read("word/document.xml").decode("utf-8")
        n_boxes = doc.count("<w:sdt>")
        want = sum(len(cs.fields_of(s)) for s in SCRIPT["screens"])
        check("every editable text is its own locked Word box", n_boxes == want and doc.count('w:lock w:val="sdtLocked"') == n_boxes, (n_boxes, want))
        check("the Word file has the same two parts", doc.find(html.escape(LV["s_part1"], quote=False)) < doc.find(html.escape(LV["s_part2"], quote=False)) and 'w:val="s01.text"' in doc)
        check("the boxes carry the course language", 'w:lang w:val="en"' in doc)
        code, out = cs_run("read", c, "--module", "1")
        check("an untouched Word file reads back as nothing changed", code == 0 and "nothing" in out and not os.path.exists(p["pending"]), out)

        print("\n-- enough theory before every task (L36)")
        check("the example module is clean", rules_of(SCRIPT) == [], rules_of(SCRIPT))
        thin = copy.deepcopy(SCRIPT)
        screen(thin, "s03")["text"] = "Type A, B, C and membrane."
        screen(thin, "s03")["notes"] = "Show the cutaway."
        check("a slide too thin to teach from is found", "t_thin_slide" in rules_of(thin), rules_of(thin))
        check("instructor notes too thin to explain from are found", "t_thin_notes" in rules_of(thin), rules_of(thin))
        long_ = copy.deepcopy(SCRIPT)
        screen(long_, "s03")["text"] = S03_TEXT + "\n" + S01_TEXT
        f = [x for x in cs.theory_findings(long_)[0] if x["rule"] == "t_long_slide"]
        check("a slide the room cannot read from the screen is a note, not a must-fix", f and f[0]["level"] == cs.NOTE, f)
        slow = copy.deepcopy(SCRIPT)
        screen(slow, "s03")["minutes"] = 25
        check("a module whose words do not fill its minutes is found", "t_density" in rules_of(slow), rules_of(slow))
        early = copy.deepcopy(SCRIPT)
        order = ["s01", "t01", "q01", "q02", "q03", "s02", "s03", "t02", "m01", "m02", "m03", "m04", "m05"]
        early["screens"] = [screen(SCRIPT, x) for x in order]
        rs = rules_of(early)
        check("a self-check after too little theory is found", "t_before_sc" in rs, rs)
        nt = [x["screen"] for x in cs.theory_findings(early)[0] if x["rule"] == "t_not_taught"]
        check("... and the question whose answer only comes later is found - the ones already taught are not", nt == ["q03"], nt)
        untaught = copy.deepcopy(SCRIPT)
        screen(untaught, "q01")["options"][0] = "About -273 °C in a vacuum flask"
        f = [x for x in cs.theory_findings(untaught)[0] if x["rule"] == "t_not_taught"]
        check("a question whose answer was never taught is found, on that question", f and f[0]["screen"] == "q01"
              and f[0]["where"] == LV["s_question_in"].format(set=LV["s_sc_name"].format(k=1), q=1), f)
        onslide = copy.deepcopy(SCRIPT)
        screen(onslide, "t01")["text"] = "At what temperature is LNG carried near atmospheric pressure? A, B or C."
        check("a task written onto its slide is found", "t_task_on_slide" in rules_of(onslide), rules_of(onslide))
        small = copy.deepcopy(SCRIPT)
        small["screens"] = [s for s in small["screens"] if s["id"] not in ("q03", "m05")]
        rs = rules_of(small)
        check("a self-check or module check with too few questions is found", "t_sc_small" in rs and "t_mc_small" in rs, rs)
        cb = new_course(tmp, "thin", thin)
        code, out = cs_run("render", cb, "--module", "1")
        tpage = io.open(cs.paths(cb, 1)["review"], encoding="utf-8").read()
        check("the findings are at the top of the review page, before the slides",
              0 < tpage.find(lv("s_theory_title")) < tpage.find(lv("s_part1")) and lv("s_textcheck_must") in tpage)
        check("render reports them, naming the slide", "The theory check found" in out and "[must fix] Slide 4" not in out and LV["s_slide_n"].format(n=4) in out, out)
        tdoc = zipfile.ZipFile(cs.paths(cb, 1)["docx"]).read("word/document.xml").decode("utf-8")
        check("... and they are in the Word file too", html.escape(LV["s_theory_title"], quote=False) in tdoc)
        code, out = cs_run("read", cb, "--module", "1")
        check("the findings in the Word file are not mistaken for the operator's own text", "outside the boxes" not in out and code == 0, out)
        code, out = cs_run("approve", cb, "--module", "1", "--by", "Anna")
        check("approval is refused while the theory check has must-fix findings", code == 1 and "must be fixed first" in out, out)
        code, out = cs_run("approve", cb, "--module", "1", "--by", "Anna", "--despite-findings")
        rec = cs.load(cs.paths(cb, 1)["script"])
        check("the operator may approve despite them (L26) - and that is recorded",
              code == 0 and {"t_thin_slide", "t_thin_notes"} <= {f["rule"] for f in rec.get("approved_despite_findings", [])}, out)

        print("\n-- the lesson's structure is checked before it is shown")
        bad = copy.deepcopy(SCRIPT)
        bad["screens"] = [s for s in bad["screens"] if s["id"] != "t01"]
        probs = cs.validate(bad)
        check("a task that no task slide opens is caught (it could never open on the tablet)", any("no task slide opens it" in x for x in probs), probs)
        bad = copy.deepcopy(SCRIPT)
        bad["screens"] = [screen(SCRIPT, x) for x in ["s01", "s02", "t01", "q01", "s03", "q02", "q03", "t02", "m01", "m02", "m03", "m04", "m05"]]
        check("questions not straight after their task slide are caught", any("straight after the task slide" in x for x in cs.validate(bad)), cs.validate(bad))
        bad = copy.deepcopy(SCRIPT)
        bad["screens"] = [s for s in bad["screens"] if s.get("kind") != "module-check" and s["id"] != "t02"]
        check("a module with no module check is caught", any("no module check" in x for x in cs.validate(bad)), cs.validate(bad))
        bad = copy.deepcopy(SCRIPT)
        bad["screens"].append({"id": "s09", "kind": "slide", "title": "After the check", "text": "x", "notes": "", "minutes": 0})
        bad["screens"][8]["graded"] = True
        bad["screens"][3]["correct"] = "D"
        bad["minutes_allocated"] = 40
        cb2 = new_course(tmp, "bad", bad)
        code, out = cs_run("render", cb2, "--module", "1")
        check("a slide after the module check is caught", "slide comes after the module check" in out, out)
        check("minutes that do not add up to the programme's are caught", "the minutes add up to 23, the programme gives this module 40" in out, out)
        check("a graded module check is caught", "module check is not graded" in out, out)
        check("a correct answer that is not an option is caught", "the correct answer 'D'" in out, out)
        check("... and approval is refused", cs_run("approve", cb2, "--module", "1", "--by", "x")[0] == 1)

        print("\n-- the operator edits the Word file - read, and do NOT apply")
        def edits(doc):
            m = box(doc, "s03.text")
            new = m.group(0).replace("rely on the hull, through the insulation, for their strength", "are supported by the hull, through the insulation")
            doc = doc.replace(m.group(0), new)
            m = box(doc, "q01.opt.B")     # a tracked change: 'room' deleted, 'ambient' inserted
            new = m.group(0).replace('<w:t xml:space="preserve">At room temperature, under pressure</w:t></w:r>',
                                     '<w:t xml:space="preserve">At </w:t></w:r><w:del w:id="91" w:author="Anna"><w:r><w:delText>room</w:delText></w:r></w:del>'
                                     '<w:ins w:id="92" w:author="Anna"><w:r><w:t>ambient</w:t></w:r></w:ins><w:r><w:t xml:space="preserve"> temperature, under pressure</w:t></w:r>')
            doc = doc.replace(m.group(0), new)
            m = box(doc, "s01.title")     # a comment on the title
            new = m.group(0).replace("<w:sdtContent><w:p>", '<w:sdtContent><w:p><w:commentRangeStart w:id="5"/>', 1)
            doc = doc.replace(m.group(0), new)
            m = box(doc, "s02.visual")    # a box deleted outright
            doc = doc.replace(m.group(0), "")
            doc = doc.replace("</w:body>", '<w:p><w:r><w:t>Please add a slide on BOG.</w:t></w:r></w:p></w:body>')   # typed outside the boxes
            comments = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments xmlns:w="%s">'
                        '<w:comment w:id="5" w:author="Anna"><w:p><w:r><w:t>Say LNG and LPG carriers.</w:t></w:r></w:p></w:comment></w:comments>' % W)
            return doc, {"word/comments.xml": comments.encode("utf-8")}
        edit_docx(p["docx"], edits)
        before = io.open(p["script"], encoding="utf-8").read()
        code, out = cs_run("read", c, "--module", "1")
        check("typed text is found - named by its slide, and only the changed words",
              LV["s_slide_n"].format(n=4) + " (s03), the slide text" in out and '"rely on" becomes "are supported by"' in out, out)
        check("a tracked change is read as if accepted, and said to be tracked, by whom",
              'answer B becomes "At ambient temperature, under pressure"' in out and "tracked changes in q01.opt.B" in out and "Anna" in out, out)
        check("a question is named by its task and number", LV["s_question_in"].format(set=LV["s_sc_name"].format(k=1), q=1) + " (q01)" in out, out)
        check("a comment is placed on its screen and field", "comment on s01.title from Anna" in out, out)
        check("a deleted box is reported, not guessed", "box for s02.visual was deleted" in out, out)
        check("text typed outside the boxes is reported, not guessed", "Please add a slide on BOG." in out and "will not guess" in out, out)
        check("NOTHING was applied - the script is unchanged, a pending list waits",
              io.open(p["script"], encoding="utf-8").read() == before and os.path.isfile(p["pending"]))
        code, out = cs_run("approve", c, "--module", "1", "--by", "Anna")
        check("approval is refused while understood changes wait", code == 1 and "waiting" in out, out)
        code, out = cs_run("apply", c, "--module", "1")
        check("apply refuses without --confirmed", code == 2 and "--confirmed" in out, out)

        print("\n-- the operator confirmed: apply")
        code, out = cs_run("apply", c, "--module", "1", "--confirmed")
        s = cs.load(p["script"])
        check("the edits are applied", code == 0 and "are supported by the hull" in screen(s, "s03")["text"]
              and screen(s, "q01")["options"][1] == "At ambient temperature, under pressure", out)
        check("comments and notes are NOT applied - they come back as proposals", "were NOT applied" in out and screen(s, "s01")["title"] == "Why gas tankers are different", out)
        fb = io.open(os.path.join(c, "FEEDBACK_LOG.md"), encoding="utf-8").read()
        check("each applied change is logged in FEEDBACK_LOG.md", fb.count("| 3 · M01 ·") == 1 + 2 and fb.count("(Word file)") == 2, fb[-400:])
        check("the old Word file is kept, and a fresh one written",
              any(f.endswith(".docx") for f in os.listdir(p["old"])) and os.path.isfile(p["docx"]))

        print("\n-- a chat correction, then 'no'")
        ch = os.path.join(tmp, "changes.json")
        io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "m01.correct", "new": "C"}]))
        code, out = cs_run("propose", c, "--module", "1", "--changes", ch)
        check("a chat correction is shown as understood, not applied", "the correct answer becomes C (was B)" in out and os.path.isfile(p["pending"]), out)
        code, out = cs_run("discard", c, "--module", "1")
        check("'no' discards it and the script is unchanged",
              not os.path.isfile(p["pending"]) and screen(cs.load(p["script"]), "m01")["correct"] == "B", out)

        print("\n-- approval, and what undoes it")
        code, out = cs_run("approve", c, "--module", "1", "--by", "Anna")
        check("the operator's 'next' approves it", code == 0 and cs_run("status", c, "--module", "1")[0] == 0, out)
        io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "s01.visual", "new": "Photograph of an LPG carrier"}]))
        cs_run("propose", c, "--module", "1", "--changes", ch)
        cs_run("apply", c, "--module", "1", "--confirmed")
        check("any change after approval makes it a draft again", cs_run("status", c, "--module", "1")[0] == 1)
        for v in ("Photograph A", "Photograph of a membrane LNG carrier alongside"):   # two corrections in the same second
            io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "s01.visual", "new": v}]))
            cs_run("propose", c, "--module", "1", "--changes", ch)
            code, out = cs_run("apply", c, "--module", "1", "--confirmed")
        check("two corrections applied in the same second both succeed, and nothing is left waiting",
              code == 0 and not os.path.isfile(p["pending"]) and screen(cs.load(p["script"]), "s01")["visual"].endswith("alongside"), out)
        code, out = cs_run("approve", c, "--module", "1", "--by", "Anna")
        check("... and it can be approved again", code == 0, out)

        print("\n-- 2.16.1: the slide-text check still runs on every screen")
        dirty = copy.deepcopy(SCRIPT)
        screen(dirty, "s01")["title"] = "Why gas tankers are different - Revision 3"
        screen(dirty, "s01")["text"] = S01_TEXT + "\nSource: IMO Model Course 1.04"
        screen(dirty, "s01")["notes"] = S01_NOTES + " The IMO Model Course 1.04 covers this in section 2."
        screen(dirty, "q01")["question"] = "What does OCFAM require here?"
        screen(dirty, "q01")["feedback"] = "LNG is fully refrigerated. [VERIFY: the exact temperature]"
        cd = new_course(tmp, "dirty", dirty)
        code, out = cs_run("render", cd, "--module", "1")
        pd = cs.paths(cd, 1)
        dpage = io.open(pd["review"], encoding="utf-8").read()
        s1, q1 = LV["s_slide_n"].format(n=1), LV["s_question_in"].format(set=LV["s_sc_name"].format(k=1), q=1)
        for what, needle in (("a model course cited as a source on a slide", s1 + " · text"),
                             ("version control on the opening slide", s1 + " · title"),
                             ("an internal abbreviation in a question", q1 + " · question"),
                             ("a factory marker in the feedback", q1 + " · feedback")):
            check("found and shown on the review page: " + what, html.escape(needle) in dpage and lv("s_textcheck_title") in dpage, needle)
        notes_li = re.search(r"<li><b>%s · notes</b>.*?</li>" % re.escape(html.escape(s1)), dpage)
        check("a model course in the INSTRUCTOR notes is only a note, never a must-fix",
              notes_li is not None and lv("s_textcheck_note") in notes_li.group(0) and lv("s_textcheck_must") not in notes_li.group(0),
              notes_li and notes_li.group(0))
        code, out = cs_run("approve", cd, "--module", "1", "--by", "Anna")
        check("approval is refused while a must-fix text finding stands", code == 1 and "must be fixed first" in out, out)

        print("\n-- the built module says exactly the approved words")
        s = cs.load(p["script"])
        mdir = os.path.join(c, "modules", "m1")
        os.makedirs(os.path.join(mdir, "tasks"))
        def slide(x, extra=""):
            lines = "".join('<p data-script-field="text">%s</p>' % l for l in x["text"].split("\n"))
            return ('<section class="slide" data-script="%s" data-cue="instructor only"><div class="slide-kind">Theory · A1</div>'
                    '<h2 data-script-field="title">%s</h2>%s<svg><text>label</text></svg><p class="src">Source: SIGTTO</p>%s</section>'
                    % (x["id"], x["title"], lines, extra))
        def task(x, correct=None):
            opts = "".join('<button data-script-field="opt.%s"%s>%s</button>' % (L, ' data-correct="true"' if L == (correct or x["correct"]) else "", o)
                           for L, o in zip(cs.letters(len(x["options"])), x["options"]))
            return ('<div data-script="%s"><p data-script-field="question">%s</p>%s<p data-script-field="feedback">%s</p></div>'
                    % (x["id"], x["question"], opts, x["feedback"]))
        def build(slides_extra="", drop=None, correct=None, word=None):
            sl = [x for x in s["screens"] if x["kind"] in cs.INSTRUCTOR and x["id"] != drop]
            deck = "<html><body>%s</body></html>" % "".join(slide(x, slides_extra if x["id"] == "s01" else "") for x in sl)
            if word:
                deck = deck.replace(word[0], word[1], 1)
            io.open(os.path.join(mdir, "module.html"), "w", encoding="utf-8").write(deck)
            tk = [x for x in s["screens"] if x["kind"] in cs.TASKS]
            io.open(os.path.join(mdir, "tasks", "t1.html"), "w", encoding="utf-8").write(
                "<html><body>%s</body></html>" % "".join(task(x, correct if x["id"] == "m01" else None) for x in tk))
            return run(MATCH, c, "--module", "1")
        code, out = build()
        check("a module that says exactly the approved words passes", code == 0, out)
        code, out = build(word=("supported by the hull", "supported by the ship's hull"))
        check("one changed word fails", code == 1 and "s03" in out, out)
        code, out = build(slides_extra="<p>An extra sentence nobody approved.</p>")
        check("an extra sentence on a slide fails", code == 1 and "not in the approved script" in out, out)
        code, out = build(drop="s02")
        check("a screen that was not built fails", code == 1 and "s02) is not built" in out, out)
        code, out = build(correct="A")
        check("a wrong correct answer fails", code == 1 and "marked correct is A - approved: B" in out, out)
        code, out = build(slides_extra='<p data-script-ignore="decor">Deck furniture</p>')
        check("data-script-ignore is allowed but counted for QA", code == 0 and "data-script-ignore" in out, out)
        io.open(ch, "w", encoding="utf-8").write(json.dumps([{"field": "s01.visual", "new": "Another photograph"}]))
        cs_run("propose", c, "--module", "1", "--changes", ch)
        cs_run("apply", c, "--module", "1", "--confirmed")
        code, out = build()
        check("a script changed after approval fails the match", code == 1 and "not approved" in out, out)

        print("\n-- the review files never ship to a tablet")
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-tablet-publisher", "scripts"))
        import gates
        plat = gates.load_platform()
        repo = os.path.join(tmp, "repo")
        base = os.path.join(repo, plat["asset_roots"]["trainee"], "courses", "x", "review", "")
        for n in ("M01_SCRIPT_REVIEW.html", "M01_SCRIPT.docx"):
            check("the publisher sorts %s as INTERNAL" % n, gates.classify(repo, plat, base + n) == "INTERNAL", gates.classify(repo, plat, base + n))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe lesson is shown on the two tablets it runs on, there is enough theory before every task, every\n"
          "correction is shown before it is applied, and the built module says exactly what was approved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
