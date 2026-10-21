# -*- coding: utf-8 -*-
"""test_module_plan - the instructor's plan is built from the approved script, so it can never fall behind it (2.47.0).

    python test_module_plan.py

Pinned:
  * a normal build writes instructor\\M01_PLAN.html beside the deck and the task pages - generated, instructor-only by its
    folder, in the shared document look (gb_tokens.css, gb_page.css) and the course language;
  * its face states the allocated minutes and the built minutes (the sum of every screen's minutes); a mismatch is shown
    in words, in the warning card, and reported by the compiler (exit 1) - short, over, or not stated;
  * every screen is on the timeline in order, with its start minute, minutes, theory or active (and the technique), what
    the instructor does (the script's notes) and its Sub-ILO; every task set and every question is listed with its code,
    way of answering, Sub-ILO and the set's pass mark; the room activities carry their link hints;
  * the Main ILO and Sub-ILOs come from the ILO map, each with the slides that teach it and the questions that check it;
    the equipment comes from the architecture; the sources are the script's;
  * a word corrected in the script is corrected in the plan on the next build;
  * a plan changed by hand - or made before the compiler - is never overwritten without --force;
  * --only plan builds the plan alone; the same script gives the same bytes.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_compile_module as t  # noqa: E402  - the same fixture course, the same runner
from test_compile_module import cs, run  # noqa: E402
import gate_fixture  # noqa: E402
import module_plan  # noqa: E402

sys.path.insert(0, os.path.join(t.SKILL, "scripts"))
import check_course_package as ccp  # noqa: E402

PASS, FAIL = [], []
SCREENS = [
    {"id": "s01", "kind": "slide", "title": "Gas as fuel", "text": "Some ships burn gas as fuel.", "visual_kind": "photo",
     "visual": "A ship bunkering.", "notes": "- Ask who has sailed on one.\n- Stress: fuel, not cargo.", "minutes": 3, "sub_ilo": "1.1"},
    {"id": "s02", "kind": "slide", "title": "Five new spaces", "text": "Fuel tank.\nTank connection space.",
     "visual_kind": "interactive_diagram", "visual": "General arrangement.", "active": "predict-then-reveal",
     "notes": "- Predict first, then reveal each space.", "minutes": 4, "sub_ilo": "1.1"},
    {"id": "p01", "kind": "activity", "title": "Walk the plant", "text": "Walk the fuel line from the tank to the engine.\nName each part.",
     "notes": "- Pairs; one points, one names.", "minutes": 5, "sub_ilo": "1.2"},
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the new spaces",
     "text": "Self-check on your tablet now.", "notes": "- Press OPEN TASK.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "question": "Where is the fuel prepared?", "options": ["Fuel preparation room", "Bridge"],
     "correct": "A", "feedback": "Pumps are there.", "mechanic": "single_choice", "sub_ilo": "1.1"},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the fuel path in order.",
     "answer": "Tank\nVaporizer\nEngine", "feedback": "Tank first.", "sub_ilo": "1.2"},
    {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - Module 1",
     "text": "Module check on your tablet now.", "notes": "- Press OPEN TASK.", "minutes": 5},
    {"id": "m01", "kind": "module-check", "set": "MC", "question": "Which space holds the tank valves?",
     "options": ["Tank connection space", "Galley"], "correct": "A", "feedback": "It holds every tank connection.",
     "mechanic": "single_choice", "sub_ilo": "1.1"},
]
ARCH = {"course": {"title": "Test course", "course_language": "English", "operator_language": "en", "course_type": "NEW_ENTRANT"},
        "main_ilos": [{"id": "1", "text": "Contribute to safe fuel operations"}],
        "modules": [{"module": 1, "title": "Module 1", "main_ilos": ["1"], "sub_ilos": gate_fixture.DEFAULT_SUBS,
                     "practicals": [{"task": "Dress for bunkering", "equipment": "cryogenic gloves, face shield",
                                     "place": "the safety area", "minutes": 15}]}],
        "final_assessment": {"topic": "99", "graded": True}}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def plan_course(tmp, allocated=21, language="English", screens=SCREENS, arch=True):
    sc = t.script(screens=screens)
    sc["minutes_allocated"] = allocated
    sc["course_language"] = language
    sc["sources"] = ["IGF Code 2016 (MSC.391(95)), 2.1", "SOLAS II-1/56"]
    sc.update(status="approved", approved_hash=cs.content_hash(sc), approved_by="Test", approved_on="2026-10-16")
    c, md = t.new_course(tmp, sc, build=False)
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"),
            {"module": 1, "screens": {"p01": {"link_hint": "Work in pairs at the simulator"},
                                      "s01": {"figure": "assets/img/ship.jpg"},
                                      # 2.63.0: the scale's "60 °C" is not in these screens' words - named where it is from
                                      "s02": {"figure": "assets/fig/scale.svg", "facts": {"60 °C": "the fixture's scale"}}}})
    if arch:
        cs.save(os.path.join(c, "working_claude", "architecture.json"), ARCH)
        gate_fixture.open_gate(c)
    return c, md


def plan_of(md):
    p = os.path.join(md, "instructor", "M01_PLAN.html")
    return io.open(p, encoding="utf-8").read() if os.path.isfile(p) else ""


def text_of(page):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)).strip()


def main():
    tmp = tempfile.mkdtemp(prefix="module_plan_")
    try:
        os.makedirs(os.path.join(tmp, "a"))
        c, md = plan_course(os.path.join(tmp, "a"))
        code, out = run(t.COMPILE, c, "--module", "1")
        page = plan_of(md)
        txt = text_of(page)
        print("\n-- the plan comes out of a normal build")
        check("a normal build writes instructor/M01_PLAN.html beside the deck and the task pages",
              code == 0 and page and os.path.isfile(os.path.join(md, "presentation", "index.html"))
              and os.path.isfile(os.path.join(md, "tasks", "sc1_the_new_spaces.html")) and "Built the module plan instructor/M01_PLAN.html" in out,
              (code, out))
        check("... marked generated, instructor only, <title> 'Module 1 plan — IGF ships', in the shared document look, no script",
              "GENERATED by course-factory" in page and "module_plan.py" in page and "Instructor only" in page
              and "<title>Module 1 plan — IGF ships</title>" in page and 'href="../assets/gb_tokens.css"' in page
              and 'href="../assets/gb_page.css"' in page and "<script" not in page, page[:500])
        rel = "instructor/M01_PLAN.html"
        check("... instructor-only by its folder: the classroom's importer rule takes it, the trainee folders do not",
              ccp.INSTRUCTOR_ONLY.search(rel) and not ccp.TRAINEE_FOLDERS.search(rel), rel)
        tp_pages = [io.open(os.path.join(md, f), encoding="utf-8").read() for f in ("tasks/sc1_the_new_spaces.html", "assessment/check.html")]
        check("... and no trainee page links to it", not any("M01_PLAN" in p for p in tp_pages))

        print("\n-- the face: allocated against built")
        check("allocated minutes with the academic hours of the programme, built minutes with what they are the sum of",
              "Allocated: 21 min" in txt and "Built: 21 min (the sum of the 5 screens)" in txt, txt[:400])
        check("... they match: a good card says so, and the compiler is content",
              '<div class="card good"><p>The screens add up to the allocated minutes.</p></div>' in page and "The minutes do not add up" not in page and code == 0, page[:1500])
        check("... the minutes split into plain theory, active slides, tasks and room activities",
              "Plain theory 3 min · active slides 4 min · tasks 9 min · room activities 5 min" in txt, txt[:500])

        print("\n-- what the module owes")
        check("the Main ILO and the Sub-ILOs come from the ILO map, in the map's words",
              "Contribute to safe fuel operations" in txt and "Explain why liquefied gas is carried cold" in txt
              and "Identify the cargo containment systems" in txt, txt[:900])
        row = re.search(r'<tr><td class="n">1\.1</td>.*?</tr>', page, re.S)
        row2 = re.search(r'<tr><td class="n">1\.2</td>.*?</tr>', page, re.S)
        check("... each with the slides that teach it and the questions that check it",
              row and "slide 1, slide 2" in row.group(0) and "SC1 q01, MC m01" in row.group(0)
              and row2 and "slide 3" in row2.group(0) and "SC1 q02" in row2.group(0), (row and row.group(0), row2 and row2.group(0)))

        print("\n-- the timeline: every screen, in order")
        titles = ["Gas as fuel", "Five new spaces", "Walk the plant", "Self-check 1 - the new spaces", "Module check - Module 1"]
        at = [page.find("<td>%s</td>" % x) for x in titles]
        check("every screen of the script is a row, in the script's order", all(x > 0 for x in at) and at == sorted(at), at)
        rows = re.findall(r'<tr(?: class="p")?><td class="n">(\d+)</td><td class="m">([\d.]+)</td><td>(.*?)</td><td class="m">([\d.]+)</td>', page)
        check("... with the minute each starts at and its minutes: 0, 3, 7, 12, 16 and 3, 4, 5, 4, 5, adding up to the total row",
              [(r[1], r[3]) for r in rows] == [("0", "3"), ("3", "4"), ("7", "5"), ("12", "4"), ("16", "5")]
              and '<td><b>Total</b></td><td class="m"><b>21</b></td>' in page, rows)
        check("... theory or active - and which technique - a room activity, a task with its set's code",
              "<td>Theory<br><small>Photograph</small></td>" in page and "Active · predict, then reveal" in page
              and "<td>Room activity</td>" in page and "Task · SC1" in page and "Task · MC" in page, page[page.find("<table>"):][:100])
        check("... a picture kind is named without its description", "<small>Interactive diagram</small>" in page and "tap a part" not in page)
        check("... what the instructor does is the script's notes, one bullet each",
              "<li>Ask who has sailed on one.</li>" in page and "<li>Stress: fuel, not cargo.</li>" in page
              and "<li>Predict first, then reveal each space.</li>" in page)
        check("... a task slide says OPEN TASK and how many questions the tablets will open",
              "<b>OPEN TASK</b> · Questions: 2" in page and "<b>OPEN TASK</b> · Questions: 1" in page)
        check("... the Sub-ILO each screen serves", '<td>1.1</td></tr>' in page and '<td>1.2</td></tr>' in page)

        print("\n-- the tasks")
        h = page[page.find("Tasks on the tablets"):]
        check("every set is listed with its code and what opens it: SC1 on slide 4 from minute 12, MC on slide 5 from minute 16",
              "SC1 – The new spaces" in h and "opened by slide 4, from minute 12" in h
              and "MC – Module check - Module 1" in h and "opened by slide 5, from minute 16" in h, h[:600])
        check("... every question with its id, way of answering and Sub-ILO and the question itself",
              all(x in h for x in ("<td>Where is the fuel prepared?</td>", "<td>Put the fuel path in order.</td>",
                                   "<td>Which space holds the tank valves?</td>", ">q01<", ">q02<", ">m01<"))
              and cs.mech_label("single_choice") in h and cs.mech_label("order") in h, h[:1500])
        check("... the self-check has no pass mark; nor has the module check - the final's alone (2.63.0, owner 2026-10-21)",
              "No pass mark – the trainee sees" in h and "No pass mark – the score tells" in h and "= PASSED" not in h, h[:900])
        check("... and points to the answer key, which holds the answers - the plan holds none (no option, no answer line, no feedback)",
              "answer key" in h and not any(x in page for x in ("Pumps are there.", "Tank first.", "Vaporizer", "Galley",
                                                                "It holds every tank connection.")), "")

        print("\n-- room activities, materials, sources")
        r = page[page.find("<h2>Room activities</h2>"):]
        check("a room activity carries the link hint of the build sheet",
              "Walk the plant" in r and "Work in pairs at the simulator" in r, r[:500])
        m_ = page[page.find("Materials and equipment"):]
        check("the equipment is the architecture's practical equipment, with its place and minutes",
              "Dress for bunkering – equipment: cryogenic gloves, face shield; place: the safety area; 15 min" in m_, m_[:500])
        check("... and the tablets the tasks use, named by the sets' codes",
              "one trainee tablet each for: SC1, MC." in m_)
        check("the sources are the script's own", "IGF Code 2016 (MSC.391(95)), 2.1" in page and "SOLAS II-1/56" in page)
        check("the page says who approved the script it was made from",
              "approved by Test on 2026-10-16" in page, page[-500:])

        print("\n-- every question and screen of the script is in the plan (nothing lost, nothing invented)")
        ids = {s["id"] for s in SCREENS if s["kind"] in cs.TASKS}
        check("every question id of the script is on the plan", all(">%s<" % i in page for i in ids), ids)
        invented = [x for x in re.findall(r"<li>(.*?)</li>", page) if x not in
                    sum(([y[2:].strip() for y in cs.note_lines(s.get("notes"))] for s in SCREENS), [])
                    and not x.startswith(("Dress for", "The instructor", "<b>OPEN"))]
        check("... and every bullet is a note of the script or an equipment line from the architecture", not invented, invented)

        print("\n-- the same script, the same bytes; a word fixed in the script is fixed in the plan")
        before = io.open(os.path.join(md, "instructor", "M01_PLAN.html"), "rb").read()
        code, out = run(t.COMPILE, c, "--module", "1")
        check("built again: nothing changed, the same bytes, exit 0",
              code == 0 and io.open(os.path.join(md, "instructor", "M01_PLAN.html"), "rb").read() == before, out[-300:])
        sp = os.path.join(c, "working_claude", "script", "M01.json")
        sc = cs.load(sp)
        sc["screens"][0]["notes"] = "- Ask who has sailed on a gas-fuelled ship."
        sc["screens"][0]["minutes"] = 4
        sc["minutes_allocated"] = 22
        sc.update(approved_hash=cs.content_hash(sc))
        cs.save(sp, sc)
        code, out = run(t.COMPILE, c, "--module", "1")
        page = plan_of(md)
        check("a corrected note and minutes reach the plan on the next build - the old words are gone",
              code == 0 and "<li>Ask who has sailed on a gas-fuelled ship.</li>" in page and "Ask who has sailed on one." not in page
              and "Allocated: 22 min" in page and "Built: 22 min" in page, (code, out[-300:]))

        print("\n-- minutes that do not add up are shown on the face and reported")
        for name, alloc in (("short", 30), ("over", 18)):
            os.makedirs(os.path.join(tmp, name))
            c2, md2 = plan_course(os.path.join(tmp, name), allocated=alloc)
            code, out = run(t.COMPILE, c2, "--module", "1")
            p2 = plan_of(md2)
            want = ("The screens add up to 21 min, 9 min short of the 30 min the programme allocates." if name == "short"
                    else "The screens add up to 21 min, 3 min over the 18 min the programme allocates.")
            check("%s: the face shows allocated and built, the warning card says it in words" % name,
                  "Allocated: %d min" % alloc in p2 and "Built: 21 min" in p2 and '<div class="card warn"><h3>The minutes do not add up</h3>' in p2
                  and want in p2, text_of(p2)[:500])
            check("%s: the compiler reports it (exit 1), the plan is still written" % name,
                  code == 1 and "%s plan: the screens add up to 21 min" % "M01" in out and p2, (code, out[-400:]))
        os.makedirs(os.path.join(tmp, "none"))
        c3, md3 = plan_course(os.path.join(tmp, "none"))
        s3 = cs.load(os.path.join(c3, "working_claude", "script", "M01.json"))
        s3.pop("minutes_allocated")
        cs.save(os.path.join(c3, "working_claude", "script", "M01.json"), s3)
        code, out = run(t.COMPILE, c3, "--module", "1", "--only", "plan")
        p3 = plan_of(md3)
        check("no allocated minutes in the script: the face says so, built is still shown, the compiler reports it",
              code == 1 and "Allocated: not stated in the script" in p3 and "Built: 21 min" in p3 and "does not state the minutes" in p3
              and "does not state the module's allocated minutes" in out, (code, out[-300:]))

        print("\n-- hand edits are protected")
        os.makedirs(os.path.join(tmp, "hand"))
        c4, md4 = plan_course(os.path.join(tmp, "hand"))
        run(t.COMPILE, c4, "--module", "1")
        pp = os.path.join(md4, "instructor", "M01_PLAN.html")
        good = io.open(pp, encoding="utf-8").read()
        io.open(pp, "w", encoding="utf-8").write(good.replace("Gas as fuel", "Gas as FUEL (my fix)"))
        code, out = run(t.COMPILE, c4, "--module", "1")
        check("a plan changed by hand is not overwritten: the build says so, names the file and the way out, exit 1",
              code == 1 and "instructor/M01_PLAN.html was changed by hand" in out and "--force" in out
              and "(my fix)" in io.open(pp, encoding="utf-8").read(), (code, out[-400:]))
        check("... the deck and the task pages were still built",
              os.path.isfile(os.path.join(md4, "presentation", "index.html")))
        code, out = run(t.COMPILE, c4, "--module", "1", "--force")
        check("--force overwrites it with the plan of the approved script", code == 0 and io.open(pp, encoding="utf-8").read() == good, out[-300:])
        os.makedirs(os.path.join(tmp, "old"))
        c5, md5 = plan_course(os.path.join(tmp, "old"))
        os.makedirs(os.path.join(md5, "instructor"))
        stub = "<title>Module 1 plan</title><!-- made by hand, before the compiler -->"
        io.open(os.path.join(md5, "instructor", "M01_PLAN.html"), "w", encoding="utf-8").write(stub)
        code, out = run(t.COMPILE, c5, "--module", "1", "--only", "plan")
        check("a plan made by hand before the compiler is protected the same way",
              code == 1 and "was changed by hand, or was made before the compiler" in out
              and io.open(os.path.join(md5, "instructor", "M01_PLAN.html"), encoding="utf-8").read() == stub, (code, out[-300:]))
        code, out = run(t.COMPILE, c5, "--module", "1", "--only", "plan", "--force")
        check("... and --force replaces it", code == 0 and "GENERATED by course-factory" in plan_of(md5), out[-300:])

        print("\n-- --only plan builds the plan alone")
        os.makedirs(os.path.join(tmp, "only"))
        c6, md6 = plan_course(os.path.join(tmp, "only"))
        code, out = run(t.COMPILE, c6, "--module", "1", "--only", "plan")
        check("only the plan: no deck, no task page, no answer key",
              code == 0 and plan_of(md6) and not os.path.exists(os.path.join(md6, "presentation", "index.html"))
              and not os.path.exists(os.path.join(md6, "tasks")) and not os.path.exists(os.path.join(md6, "assessment", "check.html")), out[-300:])
        code, out = run(t.COMPILE, c6, "--module", "1", "--only", "tasks")
        check("--only tasks leaves the plan alone", code == 0 and "module plan" not in out and plan_of(md6) != "", out[-300:])
        os.makedirs(os.path.join(tmp, "draft"))
        c7, md7 = plan_course(os.path.join(tmp, "draft"))
        sd = cs.load(os.path.join(c7, "working_claude", "script", "M01.json"))
        sd["status"] = "draft"
        cs.save(os.path.join(c7, "working_claude", "script", "M01.json"), sd)
        code, out = run(t.COMPILE, c7, "--module", "1", "--only", "plan", "--draft")
        check("... a draft script: the plan is a marked preview, exit 1", code == 1 and "DRAFT – the script is not approved" in plan_of(md7)
              and "DRAFT - NOT APPROVED" in plan_of(md7), (code, out[-300:]))

        print("\n-- without an ILO map or an architecture")
        os.makedirs(os.path.join(tmp, "bare"))
        c8, md8 = plan_course(os.path.join(tmp, "bare"), arch=False)
        code, out = run(t.COMPILE, c8, "--module", "1", "--only", "plan")
        p8 = plan_of(md8)
        check("the Sub-ILO ids the script names are still listed, with where they are taught and checked - and it says why there is no wording",
              code == 0 and "The ILO map is not in the course yet" in p8 and ">1.1<" in p8 and "slide 1, slide 2" in p8
              and "No practical equipment is named" in p8, (code, out[-300:], text_of(p8)[:600]))

        print("\n-- the course language")
        for lang, lc, title, only_, tasks_h in (("Latvian", "lv", "1. moduļa plāns", "Tikai instruktoram", "Uzdevumi planšetēs"),
                                                ("Russian", "ru", "План модуля 1", "Только для инструктора", "Задания на планшетах")):
            os.makedirs(os.path.join(tmp, lang))
            cl, mdl = plan_course(os.path.join(tmp, lang), language=lang)
            code, out = run(t.COMPILE, cl, "--module", "1", "--only", "plan")
            pl = plan_of(mdl)
            check("%s: the plan's own words are in the course language, <html lang> says so" % lang,
                  title in pl and only_ in pl and tasks_h in pl and "Allocated" not in pl and '<html lang="%s">' % lc in pl
                  and "Pass mark" not in pl, (code, out[-300:], text_of(pl)[:300]))
        os.makedirs(os.path.join(tmp, "German"))
        cg, mdg = plan_course(os.path.join(tmp, "German"), language="German")
        code, out = run(t.COMPILE, cg, "--module", "1", "--only", "plan")
        check("a language the factory has no words for: built in English and reported, never silent",
              code == 1 and "Module 1 plan" in plan_of(mdg) and "the plan's own words are not in the factory in that language" in out, (code, out[-300:]))
        check("every language has every word, and names every technique", all(set(module_plan.WORDS[k]) == set(module_plan.WORDS["en"]) for k in module_plan.WORDS))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
