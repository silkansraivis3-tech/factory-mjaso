# -*- coding: utf-8 -*-
"""test_ilo_coverage - the ILO coverage file the admin panel reads is made by the factory (2.83.0).

    python test_ilo_coverage.py

Pinned: the file's shape (kind, version, course, approved, main, modules, rows); a row's taught slides, checked sets,
exercises and final count read off the scripts and assessment_map.json; a screen that serves two Sub-ILOs counts for
both; a tag no row owns is reported; "whole" and "exam" rows; the output is Unicode, one-space indented, and the same
twice; a course with no ILO map or no modules folder gets no file and no crash. compile_course.py's call of it: test_compile_course.py.
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import gate_fixture  # noqa: E402
import ilo_coverage  # noqa: E402
import test_content_script as tcs  # noqa: E402  - its example module (two Sub-ILOs, tagged slides and questions)
import workspace  # noqa: E402

PASS, FAIL = [], []
TOOL = os.path.join(HERE, "ilo_coverage.py")


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable, "-I"] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def put(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False))


def row(doc, module, id_):
    return [r for r in doc["rows"] if r["module"] == module and r["id"] == id_][0]


def main():
    tmp = tempfile.mkdtemp(prefix="ilo_cov_")
    try:
        c = os.path.join(tmp, "course")
        wc = os.path.join(c, "working_claude")
        script = copy.deepcopy(tcs.SCRIPT)
        for s in script["screens"]:
            if s["id"] == "s03":
                s["sub_ilo"] = ["1.2", "1.1"]                      # one slide, two Sub-ILOs (a list, as a script may write it)
            if s["id"] == "s04":
                s["sub_ilo"] = "9.9"                               # a tag no row owns
        script["screens"].append({"id": "a01", "sub_ilo": "1.2", "kind": "activity", "exercise": "EX1", "title": "Walk the tank deck"})
        put(os.path.join(wc, "script", "M01.json"), script)
        put(os.path.join(wc, "script", "FINAL.json"), {"screens": [{"id": "f01", "sub_ilo": "1.1", "set": "FINAL", "kind": "final"},
                                                                    {"id": "f02", "sub_ilo": "1.1,1.2", "set": "FINAL", "kind": "final"}]})
        two = [{"id": "2.1", "status": "added", "text": "Name the ESD triggers.", "why": "x"}]
        gate_fixture.open_gate(c, sub_ilos={1: gate_fixture.DEFAULT_SUBS, 2: two})
        ap = workspace.claude_path(c, "architecture.json")
        arch = json.load(io.open(ap, encoding="utf-8"))
        arch["course"]["title"] = "Gāzes kuģi - Drošība"
        put(ap, arch)
        put(os.path.join(wc, "assessment_map.json"), {"final_test": {"rule": "80 % to pass"},
                                                      "exercises": [{"id": "EX2", "module": 2, "title": "ESD drill", "sub_ilos": ["2.1"], "place": "simulator"}]})

        print("-- no modules folder: no file, no crash")
        code, out = run(TOOL, c)
        check("a course with no modules\\ is told so (exit 1), nothing is written", code == 1 and "No published course here" in out
              and not os.path.exists(os.path.join(c, "modules")), out)
        nomap = os.path.join(tmp, "nomap")
        os.makedirs(os.path.join(nomap, "working_claude"))
        os.makedirs(os.path.join(nomap, "modules"))
        code, out = run(TOOL, nomap)
        check("a course with no ILO map is told so (exit 1), nothing is written", code == 1 and "No ILO map" in out
              and not os.path.exists(os.path.join(nomap, "modules", "_course_shell")), out)

        print("\n-- the file")
        os.makedirs(os.path.join(c, "modules"))
        code, out = run(TOOL, c)
        target = os.path.join(c, "modules", "_course_shell", "ilo_coverage.json")
        check("written to modules\\_course_shell\\ilo_coverage.json, _course_shell made on the way", code == 0 and os.path.isfile(target), out)
        raw = io.open(target, encoding="utf-8").read()
        doc = json.loads(raw)
        check("the shape the admin reads: kind, version 1, course, built, approved, final_rule",
              doc["kind"] == "ilo-coverage" and doc["version"] == 1 and doc["course"] == "Gāzes kuģi - Drošība" and len(doc["built"]) == 10
              and doc["approved"] == {"by": "Test", "on": doc["approved"]["on"]} and doc["final_rule"] == "80 % to pass", doc)
        check("one-space indent, Unicode kept as it is, a final newline", raw.startswith('{\n "kind"') and "Gāzes" in raw and raw.endswith("}\n"))
        check("main ILOs and modules, in the map's order", doc["main"] == [{"id": "1", "text": "Contribute to safe cargo operations"}]
              and [m["code"] for m in doc["modules"]] == ["M01", "M02"], doc["main"])
        r11, r12, r21 = row(doc, "M01", "1.1"), row(doc, "M01", "1.2"), row(doc, "M02", "2.1")
        check("taught: the slide's place in the deck (task slides do not count) and its title",
              r11["taught"][0] == {"slide": 1, "title": "Why gas tankers are different", "module": "M01"} and r11["taught"][1]["slide"] == 2, r11["taught"])
        check("a slide that serves two Sub-ILOs counts for each", any(t["title"] == "Four containment systems" for t in r11["taught"])
              and [t["slide"] for t in r12["taught"]] == [r12["taught"][0]["slide"]] and r12["taught"][0]["title"] == "Four containment systems", (r11["taught"], r12["taught"]))
        sets = {k["set"]: k for k in r11["checked"]}
        check("checked: one entry per question set, with its kind and its questions in order",
              sets["SC1"]["q"] == ["q01", "q02", "q03"] and sets["SC1"]["kind"] == "self-check" and sets["MC"]["kind"] == "module-check"
              and sets["MC"]["q"] == ["m02", "m04", "m05"], r11["checked"])
        check("practical: an activity slide (its exercise id), and an exercise the assessment map assigns",
              r12["practical"] == [{"id": "EX1", "title": "Walk the tank deck", "module": "M01"}]
              and r21["practical"] == [{"id": "EX2", "title": "ESD drill", "module": "M02", "place": "simulator"}], (r12["practical"], r21["practical"]))
        check("final: the final bank's questions counted per Sub-ILO (a double tag counts for both)", r11["final"] == 2 and r12["final"] == 1, (r11.get("final"), r12.get("final")))
        check("an empty column is left out of a row, not written as []", "practical" not in r11 and "final" not in r21 and "taught" not in r21, r21)
        code, out = run(TOOL, c)
        check("the report names a tag no row owns, and what is taught or checked nowhere",
              "Tagged with a Sub-ILO the map does not have (1): M01 s04 -> 9.9" in out and "Not taught on any slide: none" in out, out)
        m = json.load(io.open(os.path.join(wc, "ilo_map.json"), encoding="utf-8"))
        m["rows"].append({"module": "M02", "module_title": "Module 2", "main_ilo_ids": ["1"], "sub_ilo_id": "2.2", "sub_ilo": "Never taught."})
        put(os.path.join(wc, "ilo_map.json"), m)
        code, out = run(TOOL, c)
        check("a Sub-ILO taught and checked nowhere is named in both lists",
              "Not taught on any slide: M02 2.2" in out and "Not checked by any question or exercise: M02 2.2" in out, out)
        m["rows"].pop()
        put(os.path.join(wc, "ilo_map.json"), m)
        run(TOOL, c)
        check("run again, the same bytes", io.open(target, encoding="utf-8").read() == raw)

        print("\n-- whole and exam rows")
        mp = os.path.join(wc, "ilo_map.json")
        m = json.load(io.open(mp, encoding="utf-8"))
        m["rows"] += [{"module": "M01", "module_title": "Gas tankers", "main_ilo_ids": ["1"], "sub_ilo_id": "1", "sub_ilo": "1. Whole outcome;"},
                      {"module": "final", "module_title": "Final assessment", "sub_ilo_id": "-", "sub_ilo": "", "main_ilo": "7. Examined"}]
        put(mp, m)
        doc, rep = ilo_coverage.build(c)
        check("a module's own outcome row beside its Sub-ILOs is whole; the final assessment's row is whole and exam",
              row(doc, "M01", "1").get("whole") is True and row(doc, "final", "-").get("exam") is True and "whole" not in row(doc, "M01", "1.1"), doc["rows"][-2:])
        check("... and neither is reported as untaught", not any(r["id"] in ("1", "-") for r in rep["not_taught"] + rep["not_checked"]))
        check("a Main ILO's text is the architecture's, else the map's row, cleaned of its number and trailing ';'",
              {x["id"]: x["text"] for x in doc["main"]}["7"] == "Examined", doc["main"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe ILO coverage is read off the approved scripts and the map - nothing is typed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
