#!/usr/bin/env python3
"""test_patterns.py - 2.66.0: the figure library drawn, and what the FIGURE review is shown. Run: python test_patterns.py
(SKIPs without Chrome/Edge)

  * every pattern (patterns/*.kit.json) is drawn clean by the studio at 1280 x 800, every step;
  * a venting vent shows its gas in a STILL picture (reduced motion, a task page, a screenshot): its plume is painted - the
    puffs are animation from opacity 0, so before 2.66.0 a still venting mast showed no gas at all ("the gas is not being
    ejected", IGF 2.65.0);
  * a tank with two pipes on its top has a dome under each (the second ended 10 units over the shell, on nothing);
  * figure_review.py photographs a figure at projector size, one picture per step (the rest state and every step), each
    1017 px wide - the figure's panel on a 1920 x 1080 projector - and writes the figure's words and must-be-true list.
"""
from __future__ import annotations

import glob
import io
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio  # noqa: E402
import test_studio as ts  # noqa: E402
import figure_review  # noqa: E402

KIT = os.path.dirname(HERE)
FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


PLUME_JS = ("f.go(f.steps(),true);f.layout(true);var v=svg.querySelector('[data-kit-id=\"V\"] .kit-plume');"
            "var tops=svg.querySelectorAll('[data-kit-id=\"T\"] .kit-eq rect');"
            "return {plume: v ? +getComputedStyle(v).opacity : -1, circles: v ? v.querySelectorAll('circle').length : 0};")


def studio_part(tmp):
    print("\n-- every pattern is drawn clean at 1280 x 800, every step")
    for p in sorted(glob.glob(os.path.join(KIT, "patterns", "*.kit.json"))):
        r = studio.run(p, panel="two-col", sizes=((1280, 800),), out=os.path.join(tmp, "s"), quiet=True, shots=False)[0]
        probs = [x for x in studio.problems(r) if x[0] == "1280x800"] if r else ["no result"]
        check("%s clean at 1280 x 800" % os.path.basename(p), not probs, probs[:3])


def plume_part():
    print("\n-- a venting vent shows its gas in a still picture")
    spec = {"size": [400, 300], "label": "t", "parts": [
        {"id": "G", "type": "ga", "x": 10, "y": 240, "w": 380, "h": 50, "cut": True, "water": False},
        {"id": "V", "type": "vent", "on": "G.deck", "at": 0.5, "mast": 150},
        {"id": "T", "type": "tank", "on": "G.deck", "at": 0.25, "w": 140, "h": 50},
        {"id": "P1", "type": "pipe", "from": "T.top@0.1", "to": [60, 30]}, {"id": "P2", "type": "pipe", "from": "T.top@0.9", "to": [200, 30]}],
        "steps": [{"title": "vents", "play": [["V", 1, 300]]}]}
    got = ts.kit_eval(spec, PLUME_JS, 400)
    check("the plume over the outlet is painted once the vent vents (no animation needed)",
          got and got.get("plume", 0) > 0.3 and got.get("circles") == 3, got)
    domes = ts.kit_eval(spec, "return svg.querySelectorAll('[data-kit-id=\"T\"] [data-may-cross] rect').length;", 400)
    check("a tank with two pipes on its top draws a dome under each (2 x 2 shapes)", domes is not None and domes >= 4, domes)


def review_part(tmp):
    print("\n-- figure_review.py: projector size, one picture per step")
    p = os.path.join(KIT, "patterns", "vent_system.kit.json")
    out = os.path.join(tmp, "fr")
    ents = figure_review.review([("vent_system", p, {"title": "t"})], out)
    e = ents[0]
    n = len(json.load(io.open(p, encoding="utf-8"))["steps"]) + 1
    check("one picture per step, the rest state included (%d)" % n, len(e["pictures"]) == n, e["pictures"])
    sizes = [ts.png_size(x) for x in e["pictures"] if os.path.isfile(x)]
    check("each the width of the figure's panel at 1920 x 1080 (1017 px)", sizes and all(w == 1017 for w, h in sizes), sizes)
    check("figures.json carries the words, the step titles and the must-be-true list",
          os.path.isfile(os.path.join(out, "figures.json")) and e["step_titles"][0].startswith("Start")
          and any(k["kind"] == "vent_system" for k in e["kinds"]) and e["meaning"]["block"] == []
          and set(e["meaning"]) == {"block", "note", "waived"}, (e["kinds"], e["meaning"]))


def main():
    if not studio.find_browser():
        print("SKIP - no Chrome or Edge (set CF_BROWSER)")
        return 0
    tmp = tempfile.mkdtemp(prefix="test_patterns_")
    try:
        studio_part(tmp)
        plume_part()
        review_part(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
