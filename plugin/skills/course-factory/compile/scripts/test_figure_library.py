# -*- coding: utf-8 -*-
"""test_figure_library - a drawing a module passed with is the next slide's starter when it names the same things (2.67.0).

    python test_figure_library.py
"""
from __future__ import annotations

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
import test_compile_module as tc  # noqa: E402
import compile_module as cm  # noqa: E402
import figure_library as fl  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def main():
    tmp = tempfile.mkdtemp(prefix="figlib_")
    home = os.path.join(tmp, "computer-library")
    os.environ["NOVIKONTAS_FIGURE_LIBRARY"] = home
    try:
        os.makedirs(os.path.join(tmp, "a"))
        c, md = tc.new_course(os.path.join(tmp, "a"), tc.script(screens=tc.SCREENS))
        figs = os.path.join(c, "working_claude", "figures", "M01")
        os.makedirs(figs, exist_ok=True)
        passed = {"size": [416, 254], "label": "Fuel system", "parts": [
            {"id": "T", "type": "tank", "x": 20, "y": 30, "w": 150, "h": 80, "label": "Fuel tank", "value": 0.4},
            {"id": "S", "type": "space", "x": 200, "y": 30, "w": 180, "h": 90, "label": "Tank connection space"},
            {"id": "V", "type": "vent", "x": 300, "y": 200, "label": "Vent mast"}],
            "steps": [{"title": "old", "line": 9, "play": [["T", 0.9, 600]]}]}
        io.open(os.path.join(figs, "fs.kit.json"), "w", encoding="utf-8").write(json.dumps(passed))
        tc.build_of(c, lambda b: b["screens"].update({"s02": {"figure": "fs.kit.json"}}))
        kept = fl.save(c, 1)
        check("a module that passed: its kit drawings go into the course's library and this computer's", kept >= 1
              and os.path.isfile(os.path.join(home, "index.json"))
              and os.path.isfile(os.path.join(c, "working_claude", "figure_library", "index.json")), kept)
        s = {"id": "s07", "kind": "slide", "title": "The fuel system", "visual_kind": "schematic", "visual": "The fuel system.",
             "text": "Fuel tank - holds the LNG.\nTank connection space - around its connections.\nVent mast - high above the deck."}
        cm.STARTER_COURSE[0] = c
        got = cm.starter_figure({"module": 2, "screens": []}, s)
        ids = [p.get("id") for p in got["parts"]]
        check("the next slide that names those things starts from that drawing - its parts as they passed",
              ids == ["T", "S", "V"] and "figure library" in got.get("_note", ""), got)
        check("... its steps made again for THIS slide's lines (never the old slide's line 9)",
              [st["line"] for st in got["steps"]] == [1, 2, 3] and [st["play"][0][0] for st in got["steps"]] == ["T", "S", "V"],
              got["steps"])
        other = dict(s, text="Engine room - the main engines.\nBoiler - steam for the heaters.")
        g2 = cm.starter_figure({"module": 2, "screens": []}, other)
        check("... a slide that names other things keeps the grid starter", "figure library" not in (g2 or {}).get("_note", ""), g2)
        os.makedirs(os.path.join(tmp, "b"))
        c2, _ = tc.new_course(os.path.join(tmp, "b"), tc.script(screens=tc.SCREENS))
        cm.STARTER_COURSE[0] = c2
        g3 = cm.starter_figure({"module": 1, "screens": []}, s)
        check("... and another course finds it in this computer's library", "figure library" in (g3 or {}).get("_note", ""), g3)
        cm.STARTER_COURSE[0] = None
        g4 = cm.starter_figure({"module": 1, "screens": []}, s)
        check("... a starter made with no course in hand reads no library", "figure library" not in (g4 or {}).get("_note", ""), g4)
        del os.environ["NOVIKONTAS_FIGURE_LIBRARY"]
        check("a course in the temp folder (a test's) never reads or fills this computer's real library",
              fl.dirs(c) == [os.path.join(c, "working_claude", "figure_library")], fl.dirs(c))
    finally:
        os.environ.pop("NOVIKONTAS_FIGURE_LIBRARY", None)
        cm.STARTER_COURSE[0] = None
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
