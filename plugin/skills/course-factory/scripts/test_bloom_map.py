# -*- coding: utf-8 -*-
"""test_bloom_map - the Bloom map (L48, 2.25.0): what level the ILOs ask for, what level the tasks
reach, where a task sits below its ILO, and which tablet task type would lift it.

    python test_bloom_map.py

Pinned:
  * an ILO's level is its highest verb that leads a clause - in English, Latvian and Russian; a noun in
    the object is not read as a verb; 'veicināt' (to promote) is not 'veikt' (to carry out); weak verbs
    (know, understand, zināt, знать) are marked; a verb the list leaves out is 'not known', never guessed;
    a level written on the Sub-ILO ("bloom": 3) wins;
  * a task's level is its task type's usual level, or the level its author stated - and a stated level
    above what the type can reach is pointed out;
  * the lift: Apply is reached by operating, setting and reading; Create by no task type yet - said so;
  * the course map (Stage 2) and the module map (Stage 3) find: a weak Sub-ILO verb, a weak Main ILO
    (noted only - it stays verbatim, L2), planned tasks below the module's ILOs, a module with less than
    half its questions at Apply, a question below the Sub-ILO it checks, a Sub-ILO no module-check
    question reaches - and nothing on a module that already fits;
  * every finding is a suggestion: the architecture check's exit code and the content script's approval
    do not change;
  * both review pages show the Bloom section in the operator's language, and the command runs.
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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bloom_map as bm  # noqa: E402
import content_script as cs  # noqa: E402
import make_architecture_page as ap  # noqa: E402
import test_architecture_page as tap  # noqa: E402
import test_content_script as tcs  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def lvl(text, lang):
    return bm.ilo_level(text, lang)


def keys(found):
    return [k for k, _ in found]


def main():
    print("-- the level of an ILO, from its verb")
    for text, lang, want in (
            ("Identify the types of gas tankers and describe their construction", "en", 2),
            ("Knowledge of the properties of LNG and ability to operate the reliquefaction plant", "en", 3),
            ("1.2 Carry out a gas test before entry into an enclosed space", "en", 3),
            ("Evaluate the risk before entering an enclosed space", "en", 5),
            ("Describe the use of cargo pumps", "en", 2),
            ("Plan the cargo loading sequence", "en", 6),
            ("Identificēt sašķidrinātās gāzes tankkuģu tipus un aprakstīt to uzbūvi", "lv", 2),
            ("Kursants spēj darbināt kravas sūkni", "lv", 3),
            ("Описать порядок выполнения грузовых операций", "ru", 2),
            ("Знать свойства сжиженных газов и уметь применять средства защиты", "ru", 3),
            ("Оценить риск перед входом в закрытое помещение", "ru", 5)):
        got = lvl(text, lang)["level"]
        check("%s -> %s" % (text[:60], bm.level_name(want)), got == want, got)
    check("'Veicināt' (to promote) is not read as 'veikt' (to carry out)", lvl("Veicināt drošas kravas operācijas", "lv")["level"] is None)
    check("a verb the list leaves out on purpose (select) is not known - never guessed",
          lvl("Select the appropriate extinguishing agent", "en")["level"] is None)
    for text, lang in (("Understand the hazards of liquefied gas", "en"), ("Zināt sašķidrināto gāzu īpašības", "lv"),
                       ("Знать свойства сжиженных газов", "ru")):
        r = lvl(text, lang)
        check("weak verb marked: %s" % text[:40], r["weak"] and r["level"] in (1, 2), r)
    check("a strong verb beside a weak one is not weak", not lvl("Know and apply the procedure", "en")["weak"])
    check("the language may be given as a name", lvl("Aprakstīt kravas sistēmu", "Latvian")["level"] == 2)

    print("\n-- the level of a task")
    check("choose one is Remember", bm.task_level("single_choice")["level"] == 1)
    check("operate the panel is Apply", bm.task_level("panel_operate")["level"] == 3)
    check("choose-and-justify is Evaluate", bm.task_level("choose_and_justify")["level"] == 5)
    t = bm.task_level("single_choice", 4)
    check("a stated level is used, and marked as stated", t["level"] == 4 and t["stated"] and not t["over"], t)
    check("a stated level above what the type can reach is pointed out", bm.task_level("cloze", 5)["over"])
    check("every task type in the factory has a Bloom level", all(k in bm.B["mechanics"] for k in cs.MECHANICS),
          [k for k in cs.MECHANICS if k not in bm.B["mechanics"]])
    usual, _ = bm.lift_options(3)
    check("Apply is reached by hands-on task types", usual and all(bm.MEDIA["mechanics"][k]["hands_on"] for k in usual), usual)
    six = bm.lift_text(6, "en")
    check("Create: only 'build the plan' comes near it (2.28.0) - and the lift says real creation is the practical exercise",
          bm.mech_label("build_the_plan", "en") in six and bm.T("en", "b_lift_create") in six, six)

    print("\n-- the words, in three languages")
    fkeys = ("b_weak_main", "b_weak_sub", "b_unknown", "b_create", "b_plan_below", "b_share_low", "b_q_below", "b_sub_unchecked", "b_q_over")
    kw = dict(i="1", verb="x", m=1, s="1.1", ex="x", want="x", got="x", how="x", wantn="x", pct="1", min="50", ids="x", w="x", now="x", lvl="x", ceil="x")
    for L in ("en", "lv", "ru"):
        try:
            for k in fkeys:
                bm.LABELS[L][k].format(**kw)
            ok = all(k in bm.LABELS[L] for k in fkeys)
        except (KeyError, IndexError) as err:
            ok = err
        check("every Bloom finding is written in %s" % L, ok is True, ok)
        check("every level has a name and example verbs in %s" % L,
              all(bm.LEVELS[n].get(L) and bm.LEVELS[n]["examples"].get(L) for n in bm.LEVELS))

    print("\n-- the course map (Stage 2)")
    prog, arch = copy.deepcopy(tap.PROGRAMME), copy.deepcopy(tap.ARCH)
    cm = bm.course_map(prog, arch)
    check("the Main ILO 'Veicināt ...' has no level read - and no finding, it stays verbatim",
          cm["main"][0]["level"] is None and "b_weak_main" not in keys(cm["findings"]), cm["main"])
    m1 = cm["modules"][0]
    check("module 1: Sub-ILOs read in their own language - programme (lv) and course (en)",
          [s["level"] for s in m1["subs"]] == [2, 1, 1], [(s["id"], s["level"], s["verb"]) for s in m1["subs"]])
    check("module 1 asks up to Understand; its planned task types reach Understand - fits",
          m1["top"] == 2 and m1["got"] == 2 and not any(kw.get("m") == 1 for k, kw in cm["findings"] if k == "b_plan_below"), m1)
    a2 = copy.deepcopy(arch)
    a2["modules"][0]["sub_ilos"].append({"id": "1.1.c", "status": "added", "text": "Operate the cargo valves to line up for loading", "why": "x"})
    cm2 = bm.course_map(prog, a2)
    hit = [kw for k, kw in cm2["findings"] if k == "b_plan_below" and kw["m"] == 1]
    check("an Apply Sub-ILO with only Understand tasks planned is found, with the task types that lift it",
          hit and bm.mech_label("panel_operate", "lv") in hit[0]["how"], cm2["findings"])
    a3 = copy.deepcopy(arch)
    a3["modules"][0]["sub_ilos"].append({"id": "1.1.d", "status": "added", "text": "Understand the boil-off", "why": "x"})
    cm3 = bm.course_map(prog, a3)
    w = [kw for k, kw in cm3["findings"] if k == "b_weak_sub"]
    check("a weak Sub-ILO verb is found, with example verbs to re-express it", w and w[0]["s"] == "1.1.d" and "describe" in w[0]["ex"], w)
    a3["modules"][0]["sub_ilos"][-1]["bloom"] = 2
    check("... and a level written on it (\"bloom\") is taken as judged", "b_weak_sub" not in keys(bm.course_map(prog, a3)["findings"]))
    a4 = copy.deepcopy(arch)
    a4["modules"][0]["sub_ilos"].append({"id": "1.1.e", "status": "added", "text": "Select the extinguishing agent", "why": "x"})
    check("a Sub-ILO whose level cannot be read is said so", ("b_unknown", {"m": 1, "s": "1.1.e"}) in bm.course_map(prog, a4)["findings"])
    p_main = copy.deepcopy(prog); a5 = copy.deepcopy(arch)
    p_main["main_ilos"]["1"] = a5["main_ilos"][0]["text"] = "Zināt kravas operāciju drošības prasības"
    check("a weak Main ILO is noted - only noted", "b_weak_main" in keys(bm.course_map(p_main, a5)["findings"]))
    a = ap.analyse(prog, a2)
    check("Bloom findings never become problems - the architecture check's result does not change",
          not any(k.startswith("b_") for k, _ in a["problems"]) and a["problems"] == ap.analyse(prog, arch)["problems"], a["problems"])
    page = ap.build(prog, a2, a)
    check("the architecture page shows the Bloom section in the operator's language",
          bm.LABELS["lv"]["b_title"] in page and bm.level_name(3, "lv") in page and bm.LABELS["lv"]["b_below"] in page)

    print("\n-- the module map (Stage 3)")
    script = copy.deepcopy(tcs.SCRIPT)
    mm = bm.module_map(script, mech=cs.mech)
    n = len(mm["rows"])
    want = sum(1 for q in script["screens"] if q.get("kind") in bm.TASK_KINDS and bm.B["mechanics"][cs.mech(q)]["typical"] >= 3) / float(n)
    check("the share at Apply or higher is counted over every question", abs(mm["share"] - want) < 1e-9, (mm["share"], want))
    check("... and below half it is a suggestion, naming the questions to lift", "b_share_low" in keys(mm["findings"]), mm["findings"])
    am = {"module": 1, "sub_ilos": [{"id": "1.1", "status": "added", "text": "Describe the four containment systems", "why": "x"},
                                     {"id": "1.2", "status": "added", "text": "Operate the cargo valves for loading", "why": "x"}]}
    mm = bm.module_map(script, am, {}, {"course": {"course_language": "English"}}, mech=cs.mech)
    check("without links, the whole module check is compared with each Sub-ILO",
          not mm["linked"] and [s["ok"] for s in mm["subs"]] == [True, False], mm["subs"])
    check("... and a Sub-ILO it does not reach is found", any(k == "b_sub_unchecked" and kw["s"] == "1.2" for k, kw in mm["findings"]))
    s2 = copy.deepcopy(script)
    for q in s2["screens"]:
        if q["id"] == "m02":
            q["sub_ilo"] = "1.2"
    mm = bm.module_map(s2, am, {}, {"course": {"course_language": "English"}}, mech=cs.mech, where=lambda sid: cs.place(s2, sid))
    hit = [kw for k, kw in mm["findings"] if k == "b_q_below"]
    check("a question linked to a Sub-ILO above it is found, with how to lift it",
          hit and hit[0]["s"] == "1.2" and bm.mech_label("panel_operate", "lv") in hit[0]["how"], mm["findings"])
    for q in s2["screens"]:
        if q["id"] == "m02":
            q.update(mechanic="panel_operate", answer="Valve 1 = open", visual_kind="schematic", visual="the loading line", options=None, correct=None)
    mm = bm.module_map(s2, am, {}, {"course": {"course_language": "English"}}, mech=cs.mech)
    check("lifted to operate-the-panel, the gap is gone", "b_q_below" not in keys(mm["findings"])
          and [s["ok"] for s in mm["subs"] if s["id"] == "1.2"] == [True], mm["findings"])
    s3 = copy.deepcopy(script)
    s3["screens"][[q["id"] for q in s3["screens"]].index("m02")].update(bloom=4, bloom_why="the trainee works out the cargo from a boiling point")
    row = [r for r in bm.module_map(s3, mech=cs.mech)["rows"] if r["id"] == "m02"][0]
    check("a stated level is shown with its reason", row["level"] == 4 and "boiling point" in bm.question_line(row, "en"), row)

    print("\n-- the review page and the command")
    tmp = tempfile.mkdtemp(prefix="bloom_")
    try:
        c = tcs.new_course(tmp, "course")
        io.open(os.path.join(c, "working_claude", "architecture.json"), "w", encoding="utf-8").write(json.dumps(
            {"course": {"course_language": "English", "operator_language": "lv"}, "modules": [am]}, ensure_ascii=False))
        code = cs.render(c, "1", quiet=True)
        page = io.open(cs.paths(c, "1")["review"], encoding="utf-8").read()
        check("the review page shows the Bloom card and every question's level, in the operator's language",
              bm.LABELS["lv"]["b_title_module"] in page and page.count(bm.LABELS["lv"]["b_q_level"]) == len(bm.module_map(script, mech=cs.mech)["rows"]), code)
        check("Bloom findings do not block approval", not any("b_" in f.get("rule", "") for f in cs.blocking(cs.all_findings(cs.load(cs.paths(c, "1")["script"])))))
        for args in (["--course", c, "--module", "1"], ["--course", c]):
            p = subprocess.run([sys.executable, os.path.join(HERE, "bloom_map.py")] + args, capture_output=True, text=True, encoding="utf-8")
            check("bloom_map.py %s runs and prints in Latvian" % " ".join(args[2:]) or "(course)",
                  p.returncode == 0 and "Blūma" in p.stdout, p.stdout + p.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe factory reads what level every ILO asks for and every task reaches, and says how the tablet can lift it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
