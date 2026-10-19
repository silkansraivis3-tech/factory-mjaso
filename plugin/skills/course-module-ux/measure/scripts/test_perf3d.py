# -*- coding: utf-8 -*-
"""test_perf3d - perf3d.mjs measures the first frame of a deck's 3D slides in headless Chrome and turns it into an exit code.

    python test_perf3d.py

Pinned, on fixtures/deck_3d_perf.html (a fake 3D scene on a 2D canvas, no libraries):
  * --help prints the usage and exits 0; a missing deck, an unknown option or an unknown slide id exits 2;
  * "all slides with a 3D canvas" finds exactly the two fixture scenes, not the title slide;
  * the scene that draws at once is within the 1000 ms budget, the one that waits ~2 s is over it;
  * the run exits 1 (over budget), and exits 0 when only the fast slide is asked for or the budget is raised to 5000;
  * --json prints one JSON document with budgetMs, throttle and a warm and a cold first frame per slide.
Skips ('skipped: no Chrome', exit 0) when Node or Chrome is not available.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "perf3d.mjs"
DECK = HERE / "fixtures" / "deck_3d_perf.html"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(node, *args, timeout=180):
    p = subprocess.run([node, str(TOOL), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def main():
    node = shutil.which("node")
    if not node:
        print("skipped: no Node")
        return 0
    code, out, err = run(node, "--help")
    check("--help prints the usage and exits 0", code == 0 and "usage:" in out, (code, out, err))
    code, _, err = run(node, str(HERE / "fixtures" / "no_such_deck.html"))
    check("a missing deck exits 2", code == 2 and "no such deck" in err, (code, err))
    code, _, err = run(node, str(DECK), "--bogus")
    check("an unknown option exits 2", code == 2 and "unknown option" in err, (code, err))

    # a quick probe run decides whether Chrome is there at all (exit 2 and "no Chrome" on stderr)
    quick = ["--no-fps", "--no-cold", "--dwell=300", "--wait-ms=6000"]
    code, out, err = run(node, str(DECK), "--slides=s-fast", "--json", *quick)
    if code == 2 and "no Chrome" in err:
        print("skipped: no Chrome")
        return 0
    check("a bad slide id exits 2", run(node, str(DECK), "--slides=nope", *quick)[0] == 2)

    check("only the fast slide: exit 0 and within budget", code == 0, (code, out, err))
    code, out, err = run(node, str(DECK), "--json", "--dwell=300", "--wait-ms=6000", "--ms=500")
    check("the full run (3D slides found by themselves) exits 1, one slide being over budget", code == 1, (code, out, err))
    try:
        rep = json.loads(out)
    except ValueError:
        rep = {}
        check("--json prints one JSON document", False, out)
    if rep:
        by = {s["id"]: s for s in rep["slides"]}
        check("--json carries the budget and the throttle", rep["budgetMs"] == 1000 and rep["throttle"] == 4 and rep["ok"] is False, rep)
        check("all slides with a 3D canvas = the two scenes, not the title slide", sorted(by) == ["s-fast", "s-slow"], sorted(by))
        fast, slow = by.get("s-fast", {}), by.get("s-slow", {})
        check("the scene that draws at once is within the budget", fast.get("ok") is True and fast["warm"]["firstFrameMs"] < 1000, fast)
        check("the scene that waits ~2 s is over the budget", slow.get("ok") is False and slow["warm"]["firstFrameMs"] > 1000, slow)
        check("the cold run is measured too", "firstFrameMs" in fast.get("cold", {}) and "firstFrameMs" in slow.get("cold", {}), rep)
        check("fps is reported for the warm run", (fast["warm"].get("fps") or 0) > 0, fast)
    code, out, _ = run(node, str(DECK), "--budget-ms=5000", "--no-fps", "--dwell=300", "--wait-ms=6000")
    check("with the budget raised to 5000 ms both pass and the table says PASS", code == 0 and "PASS" in out and "s-slow" in out, (code, out))

    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
