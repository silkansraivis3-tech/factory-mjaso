# -*- coding: utf-8 -*-
"""test_debrief_map - the instructor's map of misconceptions and safety questions, end to end.

    python test_debrief_map.py

The example self-check of test_interact_types (every task type) is compiled into a throwaway course, and debrief_map.py
is run on it. Pinned:
  * draft lists only the wrong choices: an option, each true-or-false statement on its wrong side only, a claim's
    wrong corrections and "keep" for a wrong claim, an investigation's wrong sources;
  * check refuses a tag on a right choice, an unknown misconception, one no choice uses, a choice that does not exist;
  * approve, then build: the map holds keys, misconception ids and safety, and no right answer;
  * tags changed after the approval: the map is removed, never left saying something nobody approved;
  * compiling the module's tasks builds the map by itself.
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
import debrief_map as dm  # noqa: E402
import test_interact_types as ti  # noqa: E402

tcm, cs = ti.tcm, ti.cs
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def quiet(fn, *a, **k):
    out = io.StringIO()
    old, sys.stdout = sys.stdout, out
    try:
        return fn(*a, **k), out.getvalue()
    finally:
        sys.stdout = old


def main():
    tmp = tempfile.mkdtemp(prefix="debrief_map_")
    try:
        c, md, code, out = ti.course(os.path.join(tmp, "a"))
        check("the example set compiles", code == 0, out[-600:])
        P = dm.paths(c, 1)
        fin = dm.paths(c, "final")
        check("the final's paths are its FINAL script, not a number (a build of the final crashed on int('final'))",
              fin["script"].endswith("FINAL.json") and fin["tags"].endswith("FINAL.debrief.json"), fin)
        page = io.open(os.path.join(md, "tasks", "sc2_cargo_hazards.html"), encoding="utf-8").read()
        ch = dm.choices(page)

        print("\n-- draft: the wrong choices only")
        quiet(dm.cmd_draft, c, 1)
        d = json.load(io.open(P["tags"], encoding="utf-8"))
        qs = d["questions"]
        w21 = qs["q21"]["_wrong"]
        check("an option: the wrong one is listed, the right one is not", "-0.5 °C" in w21 and "-42 °C" not in w21, w21)
        sw = [q for q, rows in ch.items() if any(r["label"].endswith(" => true") for r in rows)]
        ok = bool(sw)
        for q in sw:
            sts = {r["label"].rsplit(" => ", 1)[0] for r in ch[q]}
            ok = ok and all(sum(1 for l in qs[q]["_wrong"] if l.rsplit(" => ", 1)[0] == s) == 1 for s in sts)
        check("true or false: each statement once, on its wrong side", ok, [qs[q]["_wrong"] for q in sw])
        cr = [q for q, rows in ch.items() if any(" => keep" in r["label"] for r in rows)]
        kept = [l for q in cr for l in qs[q]["_wrong"] if l.endswith(" => keep")]
        claims = {r["label"].rsplit(" => ", 1)[0] for q in cr for r in ch[q]}
        check("check a colleague: 'keep' is wrong for a wrong claim, never for the right one",
              cr and 0 < len(kept) < len(claims), [kept, len(claims)])
        ev = [q for q, rows in ch.items() if any(r["label"] == "Engine room log" for r in rows)]
        check("investigate: the sources are among the choices, the wrong ones listed",
              ev and any(not r["wrong"] for r in ch[ev[0]]) and qs[ev[0]]["_wrong"], ev and qs[ev[0]]["_wrong"])
        check("every listed choice is wrong by its key", all(r["wrong"] for q, rows in ch.items() for r in rows if r["label"] in qs[q]["_wrong"]))

        print("\n-- check")
        d["misconceptions"] = {"thermometer-lies": "A gauge reading is the boiling point"}
        d["questions"]["q21"]["choices"] = {"-0.5 °C": "thermometer-lies"}
        d["questions"]["q21"]["safety"] = True
        dm.save(P["tags"], d)
        r, _ = quiet(dm.cmd_check, c, 1)
        check("sound tags pass (an untagged wrong choice is allowed)", r == 0)
        bad = json.loads(json.dumps(d))
        bad["questions"]["q21"]["choices"]["-42 °C"] = "thermometer-lies"
        dm.save(P["tags"], bad)
        probs, _ = dm.problems(c, 1)
        check("a tag on a right choice is refused", any("is a right answer" in p for p in probs), probs)
        bad = json.loads(json.dumps(d))
        bad["questions"]["q21"]["choices"]["-0.5 °C"] = "nobody-said-this"
        bad["misconceptions"]["unused-one"] = "Something nobody picks"
        bad["questions"]["q21"]["choices"]["-7 °C"] = "thermometer-lies"
        dm.save(P["tags"], bad)
        probs, _ = dm.problems(c, 1)
        check("an unknown misconception, an unused one and a choice that does not exist are refused",
              any("not in the list" in p for p in probs) and any("not used" in p for p in probs) and any("no choice reads" in p for p in probs), probs)
        r, _ = quiet(dm.cmd_approve, c, 1, "Tester")
        check("tags with problems cannot be approved", r == 1)

        print("\n-- approve and build")
        dm.save(P["tags"], d)
        r, _ = quiet(dm.build, c, 1)
        check("not approved: no map", r == 0 and not os.path.isfile(P["map"]))
        quiet(dm.cmd_approve, c, 1, "Tester")
        r, _ = quiet(dm.build, c, 1)
        m = json.load(io.open(P["map"], encoding="utf-8")) if os.path.isfile(P["map"]) else {}
        q21 = ((m.get("pages") or {}).get("tasks/sc2_cargo_hazards.html") or {}).get("q", {}).get("q21") or {}
        check("approved: the map gives the wrong choice's key its misconception, and the safety flag",
              q21.get("k") == {cs.gb_key("q21", "-0.5 °C", 0): "thermometer-lies"} and q21.get("safety") is True, q21)
        raw = io.open(P["map"], encoding="utf-8").read() if os.path.isfile(P["map"]) else ""
        check("the map holds keys and ids, never a choice's words or the right answer", "-42" not in raw and "-0.5" not in raw, raw[:300])
        check("it is in the module's instructor folder", os.path.dirname(P["map"]).endswith(os.path.join("module01", "instructor")))

        print("\n-- changed after the approval")
        d2 = json.load(io.open(P["tags"], encoding="utf-8"))
        d2["misconceptions"]["thermometer-lies"] = "Something else now"
        dm.save(P["tags"], d2)
        r, outp = quiet(dm.cmd_status, c, 1)
        check("status says the tags changed since the approval", "changed since the approval" in outp, outp)
        quiet(dm.build, c, 1)
        check("the old map is removed", not os.path.isfile(P["map"]))

        print("\n-- the compile builds it")
        dm.save(P["tags"], d)
        quiet(dm.cmd_approve, c, 1, "Tester")
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
        check("compile --only tasks writes the map from the approved tags", code == 0 and os.path.isfile(P["map"]), out[-500:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
