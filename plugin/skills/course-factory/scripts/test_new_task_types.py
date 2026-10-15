# -*- coding: utf-8 -*-
"""test_new_task_types - five tablet tasks for the higher Bloom levels (L49 step 4, 2.28.0).

    python test_new_task_types.py

Owner, 2026-10-15: "tablet interactive tasks - not only drag n drop, choose e.c., something completely different,
interesting and creative". Pinned for each of find the fault, spot the errors, build the plan, rebuild the incident
and compare:
  * a well-written one passes the script's own check; each way it can be written wrong is caught, in plain words;
  * its pieces (answer_items) are what a built page must show - and check_script_match passes the approved build,
    and fails a missing item or the wrong one marked right;
  * the review page draws it, in the operator's language;
  * its Bloom level is above Remember, and the module's share at Apply or higher rises with it;
  * none of them asks the trainee to type.
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
import test_content_script as tcs  # noqa: E402

PASS, FAIL = [], []
LV = cs.LABELS["lv"]
NEW = ("find_the_fault", "spot_the_error", "build_the_plan", "timeline", "compare")

TASKS = {
    "m01": {"question": "Tank 2 pressure keeps rising at sea. Check the parts, then name the fault.", "mechanic": "find_the_fault",
            "visual_kind": "schematic", "visual": "The reliquefaction plant: compressor, condenser and the two tank gauges",
            "answer": "! Tank 2 pressure rises about 0.05 bar an hour\n! The compressor is running\n"
                      "Compressor: running at 1,450 rpm, suction -45 °C\nCondenser: sea-water outlet 32 °C, 10 °C above normal *\n"
                      "Pressure gauge: reads the same as the second gauge",
            "feedback": "A fouled condenser cannot take the heat away, so the boil-off is not reliquefied and the pressure rises."},
    "m02": {"question": "This entry permit was filled in for cargo tank 2. Tap every wrong line.", "mechanic": "spot_the_error",
            "answer": "Space: cargo tank 2\nOxygen: 18.5 % * => below 20.9 % - nobody enters\nHydrocarbon: 0 % LFL\nToxic gas: H2S 0 ppm\n"
                      "Rescue team: not assigned * => a rescue team stands by before anyone enters\nSigned: Chief Officer",
            "feedback": "Oxygen must read 20.9 % and a rescue team must stand by before anyone enters."},
    "m03": {"question": "Build the plan for preparing cargo tank 2 for entry. Not every card belongs.", "mechanic": "build_the_plan",
            "answer": "Ventilate the tank *\nMeasure oxygen, hydrocarbon and toxic gas *\nIssue the entry permit *\nPost a stand-by person at the entrance *\n"
                      "Start loading cargo\nOpen the manifold valve",
            "feedback": "Ventilate, measure, permit, stand-by - and no cargo operation on that tank."},
    "m04": {"question": "Rebuild the night of the incident, then tap where it should have been stopped.", "mechanic": "timeline",
            "answer": "The compressor tripped at 02:10\nTank pressure rose past the alarm set point *\nThe alarm was silenced and not reported\n"
                      "The relief valve lifted at 04:30",
            "feedback": "The alarm was the barrier: reported at once, the compressor is restarted long before the relief valve lifts."},
    "m05": {"question": "Two loading plans for the same cargo. Which one do you sign?", "mechanic": "compare",
            "options": ["Plan A - load tank 1 first", "Plan B - load tanks 1 and 3 together"], "correct": "B",
            "answer": "Trim at the end: 1.2 m by the stern | 0.3 m by the stern\nHighest shear force: 92 % | 71 %",
            "feedback": "Plan B keeps the shear force well inside the limit and the trim small."},
}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def script_with_new():
    s = copy.deepcopy(tcs.SCRIPT)
    for q in s["screens"]:
        if q["id"] in TASKS:
            keep = {k: q[k] for k in ("id", "kind", "set")}
            q.clear()
            q.update(keep, **copy.deepcopy(TASKS[keep["id"]]))
    return s


def screen(s, sid):
    return next(x for x in s["screens"] if x["id"] == sid)


def probs_of(q):
    return cs.read_answer(q)[0]


def main():
    print("-- the five are known everywhere")
    for m in NEW:
        mk = cs.MEDIA["mechanics"].get(m) or {}
        check("%s: named in en / lv / ru, with its answer format" % m, all(mk.get(L) for L in ("en", "lv", "ru", "answer")), mk)
        check("%s: has a Bloom level above Remember" % m, bm.B["mechanics"][m]["typical"] >= 4, bm.B["mechanics"][m])
        check("%s: the script knows which parts it uses" % m, m in cs.USES)
    s = script_with_new()
    check("a module checked with all five passes the script's own check", cs.validate(s) == [], cs.validate(s))

    print("\n-- each way of writing one wrong is caught")
    bad = []
    q = copy.deepcopy(screen(s, "m01")); q["answer"] = q["answer"].replace("! ", "")
    bad.append(("find the fault without a symptom", q, "at least one symptom"))
    q = copy.deepcopy(screen(s, "m01")); q["answer"] = q["answer"].replace(" *", "")
    bad.append(("find the fault with no faulty part", q, "exactly one faulty part"))
    q = copy.deepcopy(screen(s, "m01")); q["answer"] = q["answer"].replace("Pressure gauge: reads", "Pressure gauge reads")
    bad.append(("a part with no 'what you see'", q, "part: what you see"))
    q = copy.deepcopy(screen(s, "m01")); q["visual"] = ""
    bad.append(("find the fault with no drawing", q, "needs the picture"))
    q = copy.deepcopy(screen(s, "m02")); q["answer"] = q["answer"].replace(" => below 20.9 % - nobody enters", "")
    bad.append(("a wrong line that does not say why", q, "says why after =>"))
    q = copy.deepcopy(screen(s, "m02")); q["answer"] = q["answer"].replace(" *", "")
    bad.append(("a document with no wrong line", q, "at least one wrong line"))
    q = copy.deepcopy(screen(s, "m03")); q["answer"] = "\n".join(l for l in q["answer"].split("\n") if l.endswith("*"))
    bad.append(("a plan with no cards that do not belong", q, "two that do not"))
    q = copy.deepcopy(screen(s, "m04")); q["answer"] = q["answer"].replace(" *", "")
    bad.append(("an incident with no stop point", q, "exactly one moment"))
    q = copy.deepcopy(screen(s, "m04")); q["answer"] = "\n".join(q["answer"].split("\n")[:3])
    bad.append(("an incident with three events", q, "at least four events"))
    q = copy.deepcopy(screen(s, "m05")); q["answer"] = "Trim at the end: 1.2 m by the stern\nHighest shear force: 92 % | 71 %"
    bad.append(("a compare row with a value missing", q, "one per option"))
    q = copy.deepcopy(screen(s, "m05")); q["answer"] = "Trim at the end: 1.2 m | 0.3 m"
    bad.append(("a compare table of one row", q, "at least two lines of figures"))
    for name, q, needle in bad:
        p = probs_of(q)
        check("caught: " + name, any(needle in x for x in p), p)

    print("\n-- what the built page must show")
    items, right = cs.answer_items(screen(s, "m01"))
    check("find the fault: symptoms, parts and what each shows; the faulty part is the right one",
          "Tank 2 pressure rises about 0.05 bar an hour" in items and "Condenser" in items and "sea-water outlet 32 °C, 10 °C above normal" in items
          and right == ["Condenser"], (items, right))
    items, right = cs.answer_items(screen(s, "m02"))
    check("spot the errors: every line and every why; the wrong lines are the right taps",
          "Oxygen: 18.5 %" in items and "below 20.9 % - nobody enters" in items and right == ["Oxygen: 18.5 %", "Rescue team: not assigned"], (items, right))
    items, right = cs.answer_items(screen(s, "m03"))
    check("build the plan: every card; the ones that belong are right", len(items) == 6 and len(right) == 4 and "Start loading cargo" not in right)
    items, right = cs.answer_items(screen(s, "m04"))
    check("rebuild the incident: every event; the stop point is right", len(items) == 4 and right == ["Tank pressure rose past the alarm set point"])
    items, right = cs.answer_items(screen(s, "m05"))
    check("compare: every figure and what it is", items == ["Trim at the end", "1.2 m by the stern", "0.3 m by the stern",
                                                        "Highest shear force", "92 %", "71 %"] and right == [], items)
    _, r, _ = cs.read_answer(screen(s, "m05"))
    check("compare: only the right option counts as taught - the figures are given in the task", r == ["Plan B - load tanks 1 and 3 together"], r)

    print("\n-- the review page, the Bloom map, and the built module")
    tmp = tempfile.mkdtemp(prefix="newtasks_")
    try:
        c = tcs.new_course(tmp, "course", s)
        cs.render(c, "1", quiet=True)
        page = io.open(cs.paths(c, "1")["review"], encoding="utf-8").read()
        for k in ("mm_symptoms", "mm_fault", "mm_error", "mm_plan", "mm_plan_out", "mm_timeline", "mm_stop", "mm_compare"):
            check("the review page draws it: %s" % LV[k], LV[k] in page)
        for m in NEW:
            check("... and names it in Latvian: %s" % cs.mech_label(m, "lv"), cs.mech_label(m, "lv") in page)
        before = bm.module_map(tcs.SCRIPT, mech=cs.mech)["share"]
        after = bm.module_map(s, mech=cs.mech)["share"]
        check("the module's share at Apply or higher rises with them", after > before and after >= 0.5, (before, after))

        sc = cs.load(cs.paths(c, "1")["script"])
        sc["status"], sc["approved_hash"] = "approved", cs.content_hash(sc)
        io.open(cs.paths(c, "1")["script"], "w", encoding="utf-8").write(json.dumps(sc, ensure_ascii=False))
        mdir = os.path.join(c, "modules", "m1")
        os.makedirs(os.path.join(mdir, "tasks"))

        def task(x, drop=False, flip=None):
            opts = "".join('<button data-script-field="opt.%s"%s>%s</button>' % (L, ' data-correct="true"' if L in cs.correct_letters(x) else "", o)
                           for L, o in zip(cs.letters(len(x.get("options", []))), x.get("options", []))) if cs.uses(x, "options") else ""
            if cs.uses(x, "answer") and cs.mech(x) != "set_value":
                items, right = cs.answer_items(x)
                items = list(reversed(items))[1 if drop else 0:]
                mark = (lambda t: t == flip) if flip else (lambda t: t in right)
                opts += "".join('<span data-script-field="answer"%s>%s</span>' % (' data-correct="true"' if mark(t) else "", t) for t in items)
            return '<div data-script="%s"><p data-script-field="question">%s</p>%s<p data-script-field="feedback">%s</p></div>' % (
                x["id"], x["question"], opts, x["feedback"])

        def build(drop=None, flip=None):
            deck = "".join('<section class="slide" data-script="%s"><h2 data-script-field="title">%s</h2>%s</section>' % (
                x["id"], x["title"], "".join('<p data-script-field="text">%s</p>' % l for l in x["text"].split("\n")))
                for x in sc["screens"] if x["kind"] in cs.INSTRUCTOR)
            io.open(os.path.join(mdir, "module.html"), "w", encoding="utf-8").write("<html><body>%s</body></html>" % deck)
            io.open(os.path.join(mdir, "tasks", "t1.html"), "w", encoding="utf-8").write("<html><body>%s</body></html>" % "".join(
                task(x, drop == x["id"], flip[1] if flip and flip[0] == x["id"] else None) for x in sc["screens"] if x["kind"] in cs.TASKS))
            p = subprocess.run([sys.executable, os.path.join(HERE, "check_script_match.py"), c, "--module", "1"],
                               capture_output=True, text=True, encoding="utf-8")
            return p.returncode, p.stdout + p.stderr

        code, out = build()
        check("a module built exactly as approved passes the word-for-word check", code == 0, out)
        code, out = build(drop="m02")
        check("a document line missing from the built page fails", code == 1 and "m02" in out and "items are not the approved ones" in out, out)
        code, out = build(flip=("m01", "Compressor"))
        check("the wrong part marked as the fault fails", code == 1 and "m01" in out and "marked right are" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n-- no typing")
    check("none of the five has a typed answer on the tablet - the factory's answer formats are tap and drag",
          all("typ" not in (cs.MEDIA["mechanics"][m]["en"] + cs.MEDIA["mechanics"][m]["answer"]).lower() for m in NEW))

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nFive new ways of answering on the tablet - investigate, judge, build, rebuild, compare - checked end to end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
