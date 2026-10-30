# -*- coding: utf-8 -*-
"""test_sim_coverage - the simulator coverage map of an advanced course is whole, and every GAP becomes a drafted task (L66).

    python test_sim_coverage.py

A small advanced course: four syllabus items (one a parent line with children, which is not an item), two simulators.
The complete map passes; each way of leaving it incomplete fails with its own sentence - a missing row, a GAP in no
task, a GAP task without its forms, a page-less verdict, counts that disagree, minutes with no source. A basic course
does not need it; course_gate.py says it loud on an advanced one, and never stops.
"""
from __future__ import annotations

import copy
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import sim_coverage  # noqa: E402
import course_gate  # noqa: E402

PASS, FAIL = [], []

SYLLABUS = {"source": "IMO Model Course 7.14 (2019)", "items_by_topic": {"1": [
    {"id": "C1", "requirement": "Plan and monitor safe bunkering", "heading": True},
    {"id": "1.1.a", "requirement": "explain the bunkering checklist"},
    {"id": "1.1.b", "requirement": "list the methods of controlling vapour pressure such as:"},
    {"id": "1.1.b.i", "requirement": "pressure build-up"},
    {"id": "1.1.c", "requirement": "describe fire control at the bunkering station"},
    {"id": "1.1.d", "requirement": "state the IGF Code's chapters"}]}}

ROW = {"competence": "C1 Plan and monitor safe bunkering", "scenario": "", "note": ""}
MAP = {
    "_what": "test", "sim_codes": {"LNG": "LCHS-5000 LNG Bunkering", "ERS": "ERS DF tanker"},
    "counts": {"COVERED": 1, "PARTLY": 1, "GAP": 1, "NOT-SIM": 1},
    "counts_by_competence": {"C1": {"COVERED": 1, "PARTLY": 1, "GAP": 1, "NOT-SIM": 1}},
    "total_leaf_items": 4,
    "kup_items": [
        dict(ROW, kup_id="1.1.a", kup_text="explain the bunkering checklist", sim="LNG", pages="LNGBunk p29", covered_by="EX 12.1", verdict="COVERED", sim_use="assess"),
        dict(ROW, kup_id="1.1.b.i", kup_text="pressure build-up", sim="LNG, ERS", pages="LNG p62", covered_by="EX 8.1 (paper)", verdict="PARTLY", sim_use="assess"),
        dict(ROW, kup_id="1.1.c", kup_text="describe fire control", sim="LNG", pages="LNG p67", covered_by="-", verdict="GAP", sim_use="assess"),
        dict(ROW, kup_id="1.1.d", kup_text="state the chapters", sim="-", pages="MC 7.14 p24", covered_by="-", verdict="NOT-SIM", sim_use="none",
             note="the Code itself; classroom")],
    "proposed_tasks": [{"id": "P1", "title": "Fire at the bunkering station", "simulator": "LNG", "kup": ["1.1.c"], "module": "M29 (day 4)",
                        "minutes": 20, "net_sim_minutes": 20, "scenario": "fire fault during the transfer", "pages": "LNG p67",
                        "minutes_from": "20 min of M29 theory", "draft": "29.1"}],
    "sim_minutes": {"now_total": 100, "proposed_total": 120, "by_module": [{"module": "M12", "now": 100, "proposed": 100},
                                                                           {"module": "M29", "now": 0, "proposed": 20}]}}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def write(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False))


def course(tmp, title, sim_map=MAP, drafts=True):
    c = os.path.join(tmp, title.replace(" ", "_"))
    w = os.path.join(c, "working_claude")
    write(os.path.join(w, "programme.json"), {"source": title, "topics": {"1": {"title": "Bunkering"}}})
    write(os.path.join(w, "mc714_syllabus.json"), SYLLABUS)
    write(os.path.join(w, "SIM_MAP.md"), "# SIM_MAP\nLNG: LNGBunk p29 ...\nERS: p141 ...\n")
    write(os.path.join(w, "SIM_COVERAGE.md"), "# SIM_COVERAGE\n")
    if sim_map is not None:
        write(os.path.join(w, "SIM_COVERAGE.json"), sim_map)
    if drafts:
        for who in ("Trainee", "Instructor"):
            write(os.path.join(c, "to_review", "exercises", "sim_drafts", "M29", "IGFA_Exercise_29.1_%s_DRAFT.docx" % who), "x")
    return c


def fails_with(name, c, words):
    probs = sim_coverage.check(c)[0]
    check(name, any(words in p for p in probs), probs)


def main():
    tmp = tempfile.mkdtemp(prefix="simcov_")
    try:
        print("\n-- needed: an advanced course, a basic one, a declined one")
        adv = course(tmp, "Advanced training for ships subject to the IGF Code")
        n = sim_coverage.needed(adv)
        check("an advanced IGF course needs the map, with the IGF simulators", n["needed"] and n["codes"] == ["LNG", "MeOH", "ERS"], n)
        basic = course(tmp, "Basic training for ships subject to the IGF Code", sim_map=None)
        check("a basic course does not", not sim_coverage.needed(basic)["needed"], sim_coverage.needed(basic))
        write(os.path.join(basic, "working_claude", "programme.json"),
              {"source": "Basic training", "topics": {"1": {"title": "Bunkering on the LNG simulator"}}})
        check("a basic course whose programme names a simulator does", sim_coverage.needed(basic)["needed"])
        write(os.path.join(basic, "working_claude", "intake.json"), {"sim_coverage_declined": "no simulator time in this course"})
        check("the operator's reason turns it off", not sim_coverage.needed(basic)["needed"])

        print("\n-- the complete map passes")
        probs, notes, s = sim_coverage.check(adv)
        check("a complete map has no problem", probs == [], probs)
        check("a parent line with children is not an item", s.get("rows") == 4 and
              [i["id"] for i in sim_coverage.leaf_items(SYLLABUS)] == ["1.1.a", "1.1.b.i", "1.1.c", "1.1.d"], s)
        check("a PARTLY item no task takes up is a note, not a failure", any("PARTLY" in x for x in notes), notes)
        try:
            import jsonschema
            schema = json.load(io.open(os.path.join(HERE, "..", "knowledge", "sim_coverage.schema.json"), encoding="utf-8"))
            jsonschema.validate(MAP, schema)
            check("the map matches sim_coverage.schema.json", True)
        except ImportError:
            print("  skip  jsonschema not installed")
        except Exception as ex:  # noqa: BLE001
            check("the map matches sim_coverage.schema.json", False, ex)

        print("\n-- every way of leaving it incomplete is said")
        m = copy.deepcopy(MAP)
        del m["kup_items"][3]
        fails_with("a syllabus item with no row", course(tmp, "Advanced a", m), "1.1.d")
        m = copy.deepcopy(MAP)
        m["proposed_tasks"] = []
        fails_with("a GAP item in no task", course(tmp, "Advanced b", m), "in no proposed task")
        fails_with("a GAP task without its forms", course(tmp, "Advanced c", drafts=False), "missing its Trainee form")
        m = copy.deepcopy(MAP)
        del m["proposed_tasks"][0]["draft"]
        fails_with("a GAP task that names no draft", course(tmp, "Advanced d", m), "has no draft")
        m = copy.deepcopy(MAP)
        m["kup_items"][0]["pages"] = "the manual"
        fails_with("a COVERED item with no manual page", course(tmp, "Advanced e", m), "no manual page")
        m = copy.deepcopy(MAP)
        m["counts"]["GAP"] = 3
        fails_with("counts that disagree with the rows", course(tmp, "Advanced f", m), "The counts say")
        m = copy.deepcopy(MAP)
        m["proposed_tasks"][0]["minutes_from"] = ""
        fails_with("a task that does not say where its minutes come from", course(tmp, "Advanced g", m), "approved hours")
        m = copy.deepcopy(MAP)
        m["kup_items"][2]["sim"] = "LCC"
        fails_with("a verdict on a simulator the course does not have", course(tmp, "Advanced h", m), "names none of the course's simulators")
        fails_with("no map at all", course(tmp, "Advanced i", None), "no simulator coverage map yet")

        print("\n-- init starts one empty row per item")
        check("init without known simulators asks for them", sim_coverage.init(course(tmp, "Advanced j", None), [])[0] == 2)
        c = course(tmp, "Advanced IGF j", None)
        code, msg = sim_coverage.init(c, [])
        d = json.load(io.open(sim_coverage.path(c), encoding="utf-8"))
        check("init writes the four items with the course's simulators", code == 0 and [r["kup_id"] for r in d["kup_items"]] ==
              ["1.1.a", "1.1.b.i", "1.1.c", "1.1.d"] and list(d["sim_codes"]) == ["LNG", "MeOH", "ERS"], (code, msg))
        check("init never writes over a map", sim_coverage.init(c, [])[0] == 2)
        check("an empty row has no verdict yet", any("no verdict" in p for p in sim_coverage.check(c)[0]))

        print("\n-- course_gate says it, never stops on it")
        note = course_gate.sim_note(course(tmp, "Advanced k", None))
        check("the gate names L66 on an advanced course with no map", note and "L66" in note, note)
        check("and is quiet on a complete one", course_gate.sim_note(adv) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nEvery item a simulator can train is mapped, and every GAP becomes a drafted task.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
