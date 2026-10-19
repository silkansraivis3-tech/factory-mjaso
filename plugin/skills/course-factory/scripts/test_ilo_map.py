# -*- coding: utf-8 -*-
"""test_ilo_map - the ILO map's slide and question rows are built from the content scripts' "sub_ilo" tags (F23, 2.49.2).

    python test_ilo_map.py

refresh writes where_taught / checked_by / taught_on / checked_on and nothing else: the approved Main ILO and Sub-ILO
wording, the other fields of a row and the approval stay exactly as they were.
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
import ilo_map  # noqa: E402
import test_content_script as tcs  # noqa: E402  - its example module (two Sub-ILOs, tagged slides and questions)
import workspace  # noqa: E402

PASS, FAIL = [], []
TOOL = os.path.join(HERE, "ilo_map.py")


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def row(m, mod, sid):
    return [r for r in ilo_map.module_rows(m, mod) if str(r["sub_ilo_id"]) == sid][0]


def main():
    tmp = tempfile.mkdtemp(prefix="ilo_")
    try:
        c = os.path.join(tmp, "course")
        os.makedirs(os.path.join(c, "working_claude", "script"))
        script = copy.deepcopy(tcs.SCRIPT)
        io.open(os.path.join(c, "working_claude", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(script, ensure_ascii=False))
        two = [{"id": "2.1", "status": "added", "text": "Name the ESD triggers.", "why": "x"}]
        gate_fixture.open_gate(c, sub_ilos={1: gate_fixture.DEFAULT_SUBS, 2: two})
        mp = ilo_map.path(c)
        m = ilo_map.load(mp)
        r0 = row(m, 1, "1.1")
        r0["how_taught"] = "the pilot's own words about how it is taught"
        ilo_map.save(mp, m)                                          # a field the course's own tool keeps on the row
        before = ilo_map.load(mp)
        core = lambda m: [{k: r.get(k) for k in ilo_map.CORE} for r in m["rows"]]

        print("-- refresh: the slide and question rows, from the script's tags")
        lines, err = ilo_map.refresh(c)
        after = ilo_map.load(mp)
        a1, a2 = row(after, 1, "1.1"), row(after, 1, "1.2")
        check("no error, one report line for the module with a script and one for the module without", err is None
              and any(x.startswith("M01: 2 of 2 row(s) refreshed") for x in lines) and any(x.startswith("M02: no content script yet") for x in lines), lines)
        t11 = [s for s in script["screens"] if s.get("kind") == "slide" and s.get("sub_ilo") == "1.1"]
        check("where_taught names every slide tagged with the Sub-ILO, by its number on the tablet and its title",
              a1["where_taught"] == "; ".join("slide %d %s" % (i, s["title"]) for i, s in
                                             [(n, x) for n, x in enumerate([y for y in script["screens"] if y["kind"] in ("slide", "task-slide", "activity")], 1)
                                              if x.get("kind") == "slide" and x.get("sub_ilo") == "1.1"]) and "slide 1 Why gas tankers are different" in a1["where_taught"]
              and len(t11) == 2, a1["where_taught"])
        check("... a slide's id is kept too, and the second Sub-ILO is its own slide", a1["taught_on"] == [s["id"] for s in t11] and a2["taught_on"] == ["s03"], (a1, a2))
        check("checked_by lists the questions per set: self-check 1, then the module check",
              a1["checked_by"].startswith("SC1 q01, q02, q03 · MC ") and "m02" in a1["checked_by"] and a2["checked_on"] == ["m01", "m03"], a1["checked_by"])
        check("the module with no script is left as it was", row(after, 2, "2.1") == row(before, 2, "2.1"))
        print("\n-- ... and nothing else changes")
        check("the Main ILO, the Sub-ILO, their status and wording, and every core field are exactly as approved", core(after) == core(before))
        check("the map's fingerprint and the architecture approval still match - the operator's approval stands",
              ilo_map.fingerprint(after["rows"]) == ilo_map.fingerprint(before["rows"]) and after.get("ilo_map_hash") == before.get("ilo_map_hash")
              and ilo_map.stale(c, after) == [])
        check("a field the course's own tool keeps on a row is kept", row(after, 1, "1.1").get("how_taught") == "the pilot's own words about how it is taught")
        check("a second refresh changes nothing", ilo_map.refresh(c)[0][0].startswith("M01: 0 of 2 row(s) refreshed"), ilo_map.refresh(c)[0])
        ilo_map.build(c, quiet=True)
        check("a rebuild from the Stage 2 files keeps the refreshed columns", row(ilo_map.load(mp), 1, "1.2").get("where_taught") == a2["where_taught"])

        print("\n-- the script changes, the rows follow")
        moved = copy.deepcopy(script)
        moved["screens"].insert(0, {"id": "s00", "kind": "slide", "title": "A new opening", "text": "x", "visual_kind": "none", "minutes": 2})
        for s in moved["screens"]:
            if s["id"] == "s03":
                s["sub_ilo"] = ["1.1", "1.2"]
            if s["id"] == "m02":
                s["sub_ilo"] = "1.2"
        io.open(os.path.join(c, "working_claude", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(moved, ensure_ascii=False))
        code, out = run("refresh", c, "--dry-run")
        check("--dry-run says what would change and writes nothing", code == 0 and "M01: " in out and "Nothing written" in out
              and ilo_map.load(mp) == after, out)
        code, out = run("refresh", c, "--module", "1")
        moved_map = ilo_map.load(mp)
        m1, m2 = row(moved_map, 1, "1.1"), row(moved_map, 1, "1.2")
        check("the CLI refreshes the module: slides move up by one, a slide may teach two Sub-ILOs",
              code == 0 and "slide 2 Why gas tankers are different" in m1["where_taught"] and "s03" in m1["taught_on"] and "s03" in m2["taught_on"], (out, m1["where_taught"]))
        check("... a question moved to the other Sub-ILO is listed there", "m02" in m2["checked_on"] and "m02" not in m1["checked_on"], (m1["checked_on"], m2["checked_on"]))
        check("... and the wording is still the approved wording", core(moved_map) == core(before) and moved_map["script_synced"])

        print("\n-- what the report says")
        bad = copy.deepcopy(script)
        for s in bad["screens"]:
            if s.get("sub_ilo") == "1.2":
                s["sub_ilo"] = "9.9" if s["kind"] == "slide" else "1.1"
        io.open(os.path.join(c, "working_claude", "script", "M01.json"), "w", encoding="utf-8").write(json.dumps(bad, ensure_ascii=False))
        code, out = run("refresh", c)
        check("a tag no row owns and a Sub-ILO taught or checked nowhere are reported, not hidden",
              "unknown tag(s): 9.9 on s03" in out and "1.2 not taught on any slide" in out and "1.2 not checked by any question" in out, out)
        nomap = os.path.join(tmp, "nomap")
        os.makedirs(os.path.join(nomap, "working_claude"))
        code, out = run("refresh", nomap)
        check("a course without an ILO map: stopped, told how it is made", code == 2 and "no ILO map yet" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nThe ILO map's slide and question rows come from the scripts, and the approved wording is never touched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
