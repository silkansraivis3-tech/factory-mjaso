# -*- coding: utf-8 -*-
"""test_classroom_files - the instructor-only classroom files the tablet app reads on publish (classroom_files.py).

    python test_classroom_files.py

Pinned:
  * prepare.json: the course list from intake's equipment, a module's list from its practicals done in class (a practical
    done at home is not set up by the instructor), its task papers to print and - from an approved instructor_led.json -
    its cards, form and safety brief; a module with nothing is left out; nothing at all writes no file; 60 items, 200 characters;
  * a form: one per recorded run, a code that leads with the course (form codes are global on the server) and fits 40
    characters, the critical steps as pass / fail rows, the global rating, the decision - and it passes the app's own form
    rules (a port of forms.mjs validateDefinition, broken one way at a time here);
  * check_course_package.py reads the classroom\\ folder with the app's limits (60 items, 40 forms, 200-character label,
    the form code pattern) and names a module code that is not a module; the folder is not "not a module".
The build itself (files written, moved aside, --check) is pinned in compile\\scripts\\test_additional_materials.py.
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
import classroom_files as cf  # noqa: E402
import instructor_led as il  # noqa: E402
import test_course_package as tcp  # noqa: E402  - the same good course folder and runner
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def task(code, title, where, kind="activity"):
    return {"code": code, "title": title, "where": where, "slide": {"id": code.lower(), "kind": kind}}


ARCH = {"modules": [
    {"module": 1, "practicals": [
        {"task": "Bunkering on the simulator (day 1: line up the station)", "equipment": "bunkering simulator", "place": "simulator room", "minutes": 40},
        {"task": "Course project stage 1 (evening)", "equipment": "laptop", "place": "home", "minutes": 160}]},
    {"module": 2, "practicals": [{"task": "Written plan", "equipment": "", "place": "home"}]},
    {"module": 3, "practicals": []}]}
INFOS = [{"n": 1, "code": "module01"}, {"n": 2, "code": "module02"}, {"n": 3, "code": "module03"}]
MODS = [{"n": 1, "mid": "M01", "tasks": [task("A01", "Practical - bunkering", "simulator"), task("SC1", "Self-check", "tablet", "task-slide")]},
        {"n": 2, "mid": "M02", "tasks": []}]
ENTRY = {"recorded": True, "changed_condition": "the ESD link fails", "gwo": True,
         "prebrief": {"safety": ["The ESD link is tested first.", "Second line.", "Third line."]},
         "form": {"critical": [{"step": "Tests the ESD link", "stop": False}, {"step": "Stops the transfer", "stop": True}]}}
IL = {"practicals": {"M01.A01": ENTRY}, "employer": {"can_do": ["Line up a station"]}}
INTAKE = {"equipment": "classroom, projector, instructor and trainee tablets; bunkering simulator"}


def labels(lst):
    return [x["label"] for x in lst]


def main():
    print("-- prepare.json")
    doc = cf.prepare("c", ARCH, INTAKE, INFOS, MODS, IL)
    check("the course list: intake's equipment, one item each, kinds by their words, the employer sheet and the assessor",
          labels(doc["course"]) == ["Classroom", "Projector", "Instructor and trainee tablets", "Bunkering simulator", "Print: the employer sheet",
                                    cf.W["assessor"]]
          and [x["kind"] for x in doc["course"][:4]] == ["room", "equipment", "equipment", "simulator"], doc["course"])
    m1 = doc["modules"]["module01"]
    check("module01: the simulator practical (with its place) first, a practical done at home left out, the task paper, the cards, the form, "
          "the first two safety lines", labels(m1) == [
              "Bunkering on the simulator: bunkering simulator", "Print: A01 task paper - Practical - bunkering",
              "Print: pre-brief, debrief and observation cards - A01", "Print: assessment form, one per candidate - A01",
              "Safety brief ready - A01: The ESD link is tested first.; Second line."] and m1[0]["place"] == "simulator room"
          and m1[0]["kind"] == "simulator" and all(x["kind"] == "document" for x in m1[1:4]), m1)
    check("a module with nothing to get ready (module02 done at home, module03 empty) is left out", list(doc["modules"]) == ["module01"], doc["modules"])
    check("a tablet task (a self-check) is not printed", not any("SC1" in x for x in labels(m1)))
    check("no intake equipment, no practicals, no instructor-led: nothing - no file", cf.prepare("c", {}, {}, [], [], {}) is None)
    long = {"equipment": "; ".join("Item %d" % i for i in range(80)) + "; " + "x" * 300}
    big = cf.prepare("c", {}, long, [], [], {})
    check("60 items at most, a label cut at 200 characters", len(big["course"]) == 60 and all(len(x["label"]) <= 200 for x in big["course"]))
    check("every kind is one the app knows", all(x["kind"] in cf.PREP_KINDS for x in doc["course"] + m1))

    print("\n-- the form")
    d = cf.definition(ENTRY, il.KNOW["cards"])
    crit = [c for s in d["sections"] for c in s["criteria"]]
    check("A critical steps (pass / fail, remark allowed, the stop step marked), B global rating 1-4, C decision yes / no",
          [c["label"] for c in crit] == ["Tests the ESD link", "STOP: Stops the transfer", "Global rating of the run", cf.W["decision_label"]]
          and [c["scale"] for c in crit] == ["pass_fail", "pass_fail", "0-4", "yes_no"] and all(c["remark"] is True for c in crit)
          and [m["meaning"] for m in d["scale_meanings"]["0-4"]] == ["Needs retraining", "Needs prompting", "Performs safely unprompted",
                                                                       "Performs safely and adapts"], crit)
    check("the header: date, attempt, the changed condition, the GWO level", [h["key"] for h in d["header_fields"]]
          == ["run_date", "attempt", "changed_condition", "gwo_level"])
    check("it passes the app's form rules", cf.definition_problems(d) == [], cf.definition_problems(d))
    code = cf.form_code("Basic training for ships subject to the IGF Code - advanced", "M12", "A01")
    check("the code leads with the course, cuts the course's name and never the module or task, fits 40 characters",
          code.endswith("-M12-A01") and len(code) <= 40 and cf.FORM_CODE.match(code) and code.startswith("BASIC-TRAINING"), code)
    check("a short course name is kept whole", cf.form_code("Project Management", "M05", "a01") == "PROJECT-MANAGEMENT-M05-A01")

    print("\n-- the app's form rules (validateDefinition), broken one way at a time")
    sec = lambda *c: {"sections": [{"title": "S", "criteria": list(c)}]}
    ok = {"key": "a", "label": "A", "scale": "pass_fail", "remark": True}
    cases = [
        ("no section", {"sections": []}, "at least one section"),
        ("a section with no title", {"sections": [{"title": " ", "criteria": [ok]}]}, "has no title"),
        ("a section with no criteria", {"sections": [{"title": "S", "criteria": []}]}, "has no criteria"),
        ("a key with capitals", sec(dict(ok, key="Step1")), "lowercase"),
        ("a key used twice", sec(ok, dict(ok, label="B")), "used twice"),
        ("the reserved key rank", sec(dict(ok, key="rank")), "reserved"),
        ("a scale that does not exist", sec(dict(ok, scale="1-4")), "scale must be one of"),
        ("a remark that is not true / false", sec(dict(ok, remark="yes")), "remark must be true or false"),
        ("no label", sec(dict(ok, label="")), "has no label"),
        ("a final mark that does not exist", dict(sec(ok), final_mark="best"), "final_mark must be one of"),
        ("a mean over mixed scales", dict(sec(ok, dict(ok, key="b", scale="0-4")), final_mark="mean_if_complete"), "same numeric scale"),
        ("a meaning with no words", dict(sec(ok), scale_meanings={"0-4": [{"mark": "1", "meaning": ""}]}), "each entry needs a mark and a meaning"),
        ("a header field of an unknown type", dict(sec(ok), header_fields=[{"key": "h", "label": "H", "type": "text"}]), "type must be date"),
    ]
    for name, bad, want in cases:
        probs = cf.definition_problems(bad)
        check("%s is caught" % name, any(want in p for p in probs), probs)
    check("a pass line with no final mark is caught", any("final_mark rule" in p for p in cf.definition_problems(dict(sec(ok), **{"pass": {"at_least": 1, "over": "form"}}))))

    print("\n-- the package check")
    tmp = tempfile.mkdtemp(prefix="cf_cls_")
    try:
        mf = os.path.join(tmp, "modules")
        w = lambda rel, obj: tcp.w(os.path.join(mf, *rel.split("/")), json.dumps(obj))
        good_form = {"code": "GAS-M01-A01", "title": "Form", "definition": d}
        w("classroom/prepare.json", doc)
        w("classroom/forms/GAS-M01-A01.json", good_form)
        mods = ["module01", "module02", "module03"]
        check("what the factory writes passes", cf.folder_problems(mf, mods) == [], cf.folder_problems(mf, mods))
        check("a course with no classroom folder has nothing to say", cf.folder_problems(os.path.join(tmp, "none"), mods) == [])
        w("classroom/prepare.json", {"course": [], "modules": {"module09": [{"label": "x"}]}})
        check("a module code that is not a module is named", any("module09" in p for p in cf.folder_problems(mf, mods)), cf.folder_problems(mf, mods))
        w("classroom/prepare.json", {"course": [{"label": "x"}] * 61, "modules": {}})
        check("61 items in a list is over the app's 60", any("61 items" in p for p in cf.folder_problems(mf, mods)))
        w("classroom/prepare.json", {"course": [{"label": "x" * 201}, {"label": ""}, {"label": "y", "kind": "boat"}, {"label": "z", "minutes": 0}], "modules": {}})
        probs = cf.folder_problems(mf, mods)
        check("a label over 200 characters, an empty label, an unknown kind and bad minutes are each named",
              sum(any(k in p for p in probs) for k in ("over 200", "has no label", 'kind "boat"', "minutes")) == 4, probs)
        w("classroom/prepare.json", ["not", "an", "object"])
        check("a prepare.json that is not an object is named", any("must be an object" in p for p in cf.folder_problems(mf, mods)))
        os.remove(os.path.join(mf, "classroom", "prepare.json"))
        w("classroom/forms/B.json", dict(good_form, code="!!!"))
        check("a code with no letters or digits is named", any("needs a code" in p for p in cf.folder_problems(mf, mods)), cf.folder_problems(mf, mods))
        os.remove(os.path.join(mf, "classroom", "forms", "B.json"))
        w("classroom/forms/C.json", dict(good_form, code="GAS-M01-A01"))
        check("two files with one code are named", any("used twice" in p for p in cf.folder_problems(mf, mods)), cf.folder_problems(mf, mods))
        os.remove(os.path.join(mf, "classroom", "forms", "C.json"))
        for i in range(40):
            w("classroom/forms/F%02d.json" % i, dict(good_form, code="F%02d" % i))
        check("41 forms is over the app's 40", any("at most 40" in p for p in cf.folder_problems(mf, mods)))
        shutil.rmtree(os.path.join(mf, "classroom", "forms"))
        w("classroom/forms/BROKEN.json", {"code": "BROKEN", "definition": {"sections": [{"title": "S", "criteria": [dict(ok, scale="9-9")]}]}})
        check("a form that breaks the app's rules is named with its file", any("BROKEN.json" in p and "scale must be" in p for p in cf.folder_problems(mf, mods)))

        print("\n-- check_course_package.py on a good course with the classroom folder")
        master = os.path.join(tmp, "GAS_Basic")
        os.makedirs(os.path.join(master, "source_files"))
        os.makedirs(os.path.join(master, "course", "to_review"))
        os.makedirs(os.path.join(master, "course", "working_claude"))
        c = os.path.join(master, "course", "modules")
        tcp.good_course(c)
        tcp.w(os.path.join(c, "classroom", "prepare.json"), json.dumps({"course": [{"label": "Projector", "kind": "equipment"}],
                                                                       "modules": {"module01": [{"label": "Gas bench", "kind": "equipment", "place": "lab"}]}}))
        tcp.w(os.path.join(c, "classroom", "forms", "GAS-M01-P1.json"), json.dumps({"code": "GAS-M01-P1", "title": "P1 form", "definition": d}))
        rc, out = tcp.run(master, "--no-importer")
        check("the classroom folder is not 'not a module' and a good one passes", rc == 0 and "not a module" not in out and "Ready:" in out, out)
        tcp.w(os.path.join(c, "classroom", "prepare.json"), json.dumps({"course": [], "modules": {"module07": [{"label": "x"}]}}))
        rc, out = tcp.run(master, "--no-importer")
        check("a module code that is not in the course stops the package", rc == 1 and "module07" in out, out)
        tcp.w(os.path.join(c, "classroom", "prepare.json"), json.dumps({"course": [], "modules": {}}))
        tcp.w(os.path.join(c, "classroom", "forms", "GAS-M01-P1.json"), json.dumps({"code": "GAS-M01-P1", "definition": {"sections": [{"title": "", "criteria": []}]}}))
        rc, out = tcp.run(master, "--no-importer")
        check("a form that breaks the app's rules stops the package, with its file", rc == 1 and "GAS-M01-P1.json" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
