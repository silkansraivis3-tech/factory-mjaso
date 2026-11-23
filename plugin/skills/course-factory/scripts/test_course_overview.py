# -*- coding: utf-8 -*-
"""test_course_overview - the course's whole picture for LND (2.138.0): outline and hours, ILO -> module, the programme
document found from the free-text fields, the materials copied, and nothing that would reach a trainee.

    python test_course_overview.py
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import course_overview as co  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, str):
        io.open(path, "w", encoding="utf-8", newline="\n").write(data)
    elif isinstance(data, bytes):
        open(path, "wb").write(data)
    else:
        io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(data, ensure_ascii=False))


PROG = {"source": "College, programme rev 3 (source_files/Study_Programme_rev3.docx), brief (source_files/brief.md)",
        "academic_hour_min": 40, "language": "English",
        "topics": {"1": {"title": "Data", "theory": 2, "practical": 0, "subtopics": [{"ref": "1.1", "title": "Bits"}]},
                   "2": {"title": "Networks", "theory": 4, "practical": 6},
                   "3": {"title": "Project and defence", "theory": 0, "practical": 8, "assessment": True}},
        "total_row": {"theory": 6, "practical": 14, "total": 20, "note": "defence 2"},
        "main_ilos": {"1": "Understand data.", "2": "Build a network.", "3": "Defend a project."},
        "ilo_topic": {"1": "1", "2": "2", "3": "3"}}
ARCH = {"course": {"title": "Demo", "course_language": "English",
                   "programme_file": "source_files/Study_Programme_rev3.docx (rev 3 DRAFT); revision 2: source_files/Old Study plan.pdf; source_files/missing.docx"}}


def course(tmp, prog=PROG):
    c = os.path.join(tmp, "Demo", "course")
    os.makedirs(os.path.join(c, "modules", "_course_shell"))
    w(os.path.join(c, "working_claude", "architecture.json"), ARCH)
    if prog is not None:
        w(os.path.join(c, "working_claude", "programme.json"), prog)
    w(os.path.join(c, "working_claude", "project_work.json"), {"projects": [{"code": "D1", "department": "Deck", "title": "ECDIS"}]})
    s = os.path.join(tmp, "Demo", "source_files")
    w(os.path.join(s, "Study_Programme_rev3.docx"), b"docx-bytes")
    w(os.path.join(s, "Old Study plan.pdf"), b"pdf-bytes")
    a = os.path.join(c, "additional-materials")
    w(os.path.join(a, "project-cards", "pdf", "D1_ECDIS.pdf"), b"card")
    w(os.path.join(a, "acp", "ACP_demo.docx"), b"acp")
    w(os.path.join(a, "acp", "ACP_demo.html"), "<p>not shipped</p>")
    w(os.path.join(a, "day-sheets", "Day_1_x.pdf"), b"day")
    w(os.path.join(a, "day-sheets", "Day_1_x.html"), "<title>Day 1 - Data &amp; networks</title>")
    return c


def main():
    tmp = tempfile.mkdtemp(prefix="co_")
    try:
        c = course(tmp)
        mods = os.path.join(c, "modules")
        print("-- the overview of a course with a programme")
        rec = {}
        written, probs = co.build(c, "Demo", rec, quiet=True)
        doc = json.load(io.open(os.path.join(mods, "_course_shell", "overview.json"), encoding="utf-8"))
        check("it builds with no problem and says kind course-overview, version 1", not probs and doc["kind"] == "course-overview" and doc["version"] == 1, probs)
        check("the outline is one row per topic, module M01.. in order, hours summed",
              [(r["module"], r["theory"], r["practical"], r["total"]) for r in doc["outline"]] == [("M01", 2, 0, 2), ("M02", 4, 6, 10), ("M03", 0, 8, 8)], doc["outline"])
        check("the assessment topic is marked and subtopics carried", doc["outline"][2]["assessment"] is True and doc["outline"][0]["topics"] == [{"ref": "1.1", "title": "Bits"}])
        check("hours are the programme's total row with its note", doc["hours"] == {"theory": 6, "practical": 14, "total": 20, "note": "defence 2"}, doc["hours"])
        check("every ILO is there with the module that teaches it, and each row lists its ILOs",
              [(i["id"], i["modules"]) for i in doc["ilos"]] == [("1", ["M01"]), ("2", ["M02"]), ("3", ["M03"])] and doc["outline"][1]["ilos"] == ["2"], doc["ilos"])
        check("course title, language and the programme's own words are carried", doc["course"] == {"title": "Demo", "language": "English"}
              and doc["programme"]["academic_hour_min"] == 40 and "rev 3" in doc["programme"]["source"])
        files = [(m["group"], m["file"]) for m in doc["materials"]]
        check("the programme documents are found from the free text, a name with spaces included, a missing one skipped",
              files[:2] == [("programme", "materials/programme/Study_Programme_rev3.docx"), ("programme", "materials/programme/Old_Study_plan.pdf")], files)
        check("project card, course plan (Word only) and day sheet follow, in their group folders",
              files[2:] == [("project", "materials/project-work/D1_ECDIS.pdf"), ("plan", "materials/course-plan/ACP_demo.docx"),
                            ("day-sheets", "materials/day-sheets/Day_1_x.pdf")], files)
        check("titles: the card from project_work.json, the day sheet from its page", [m["title"] for m in doc["materials"][2:]] ==
              ["Project work card D1 - ECDIS (Deck)", "Course plan (ACP)", "Day 1 - Data & networks"], [m["title"] for m in doc["materials"]])
        check("every listed file is in _course_shell with its size", all(os.path.getsize(os.path.join(mods, "_course_shell", *m["file"].split("/"))) == m["size"] for m in doc["materials"]))
        check("no file name has a space and no path would reach a trainee (tasks, handout, documents, assets, assessment)",
              all(" " not in m["file"] and not co.TRAINEE_PATH.search("_course_shell/" + m["file"]) for m in doc["materials"]))
        check("the hashes are in the record, the overview's too", "_course_shell/overview.json" in rec and "_course_shell/materials/programme/Study_Programme_rev3.docx" in rec, list(rec))
        check("it passes the package check", co.package_problems(mods) == [], co.package_problems(mods))
        w2, p2 = co.build(c, "Demo", {}, quiet=True)
        check("a second build writes nothing and keeps the day", w2 == [] and not p2)

        print("\n-- a course whose files change")
        os.remove(os.path.join(c, "additional-materials", "acp", "ACP_demo.docx"))
        co.build(c, "Demo", rec, quiet=True)
        check("a copy no longer made is moved aside, not deleted, and leaves the record",
              not os.path.exists(os.path.join(mods, "_course_shell", "materials", "course-plan", "ACP_demo.docx"))
              and "_course_shell/materials/course-plan/ACP_demo.docx" not in rec
              and any(f == "ACP_demo.docx" for _, _, fs in os.walk(os.path.join(c, "working_claude", "additional_materials", "old")) for f in fs))

        print("\n-- hours that do not add up")
        bad = dict(PROG, total_row={"theory": 6, "practical": 14, "total": 21})
        c2 = course(os.path.join(tmp, "b"), bad)
        _, probs = co.build(c2, "Demo", {}, quiet=True)
        check("a total row that is not the topics' sum is said at compile time", any("total row says" in p for p in probs), probs)
        check("... and the package check refuses the file", any("add up to" in p for p in co.package_problems(os.path.join(c2, "modules"))))

        print("\n-- no programme document")
        c3 = course(os.path.join(tmp, "d"))
        os.remove(os.path.join(tmp, "d", "Demo", "source_files", "Study_Programme_rev3.docx"))
        os.remove(os.path.join(tmp, "d", "Demo", "source_files", "Old Study plan.pdf"))
        _, probs = co.build(c3, "Demo", {}, quiet=True)
        check("said at compile time, and the package check says the overview lists none",
              any("programme document was not found" in p for p in probs) and any("lists no programme document" in p for p in co.package_problems(os.path.join(c3, "modules"))), probs)

        print("\n-- a very old course: no programme.json, or no topics")
        for name, prog in (("none", None), ("empty", {"topics": {}, "main_ilos": {}})):
            c4 = course(os.path.join(tmp, "e_" + name), prog)
            written, probs = co.build(c4, "Demo", {}, quiet=True)
            m4 = os.path.join(c4, "modules")
            check("%s: nothing is written and the line says why, without crashing" % name,
                  written == [] and len(probs) == 1 and "No course overview was written" in probs[0] and not os.path.exists(os.path.join(m4, "_course_shell", "overview.json")), probs)
            check("%s: the package check fails - the overview is missing" % name, any("overview.json is missing" in p for p in co.package_problems(m4)))

        print("\n-- the package check, one break at a time")
        good = os.path.join(mods, "_course_shell", "overview.json")
        base = json.load(io.open(good, encoding="utf-8"))

        def broken(label, fn, needle):
            m = os.path.join(tmp, "x_%d" % len(PASS + FAIL), "modules")
            shutil.copytree(mods, m)
            d = json.loads(json.dumps(base))
            fn(d, m)
            w(os.path.join(m, "_course_shell", "overview.json"), d)
            probs = co.package_problems(m)
            check("caught: " + label, any(needle in p for p in probs), probs)

        broken("an empty outline", lambda d, m: d.update(outline=[]), "empty outline")
        broken("a wrong kind", lambda d, m: d.update(kind="x"), "course-overview")
        broken("hours that differ from the outline", lambda d, m: d["hours"].update(practical=99), "practical hours add up")
        broken("no programme material", lambda d, m: d.update(materials=[x for x in d["materials"] if x["group"] != "programme"]), "lists no programme document")
        broken("a listed file that is not there", lambda d, m: os.remove(os.path.join(m, "_course_shell", "materials", "project-work", "D1_ECDIS.pdf")), "which is not in _course_shell")
        broken("a material in a folder the importer gives to the trainees", lambda d, m: (
            shutil.copytree(os.path.join(m, "_course_shell", "materials", "programme"), os.path.join(m, "_course_shell", "materials", "documents")),
            d["materials"].__setitem__(0, dict(d["materials"][0], file="materials/documents/Study_Programme_rev3.docx"))), "would be copied to the trainee tablets")
        m = os.path.join(tmp, "nofile", "modules")
        shutil.copytree(mods, m)
        os.remove(os.path.join(m, "_course_shell", "overview.json"))
        check("caught: no overview.json at all", any("overview.json is missing" in p for p in co.package_problems(m)))
        w(os.path.join(m, "_course_shell", "overview.json"), "{not json")
        check("caught: an overview that is not JSON", any("not valid JSON" in p for p in co.package_problems(m)))
        # a long title (a day sheet names every module of its day) is cut at a whole word, never mid-word
        long = "Day 1 - Information, data and computers / Working with documents and data / Networks and shipboard digital systems"
        cut = co.short(long)
        check("a long title is cut at a whole word", len(cut) <= 94 and cut.endswith(" ...") and long.startswith(cut[:-4]) and long[len(cut) - 4] in " /", cut)
        check("a short title is left as it is", co.short("Course  plan (ACP)") == "Course plan (ACP)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
