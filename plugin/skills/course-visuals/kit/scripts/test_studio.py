#!/usr/bin/env python3
"""test_studio.py - the figure studio draws one spec, audits every step at both sizes and photographs it, and the
kit's own layout moves a label off a part by itself (2.45.0). Run: python test_studio.py  (SKIP without Chrome/Edge)"""
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
import studio  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


# a valve whose name the spec puts right on the tank under it, and a room's name inside it: the layout must move the
# first clear of the tank and keep the second inside its room
GOOD = {"size": [520, 300], "label": "studio test", "parts": [
    {"id": "R", "type": "space", "x": 20, "y": 20, "w": 480, "h": 260, "label": "FUEL PREPARATION ROOM"},
    {"id": "T", "type": "tank", "x": 60, "y": 120, "w": 260, "h": 120, "label": "fuel tank", "value": 0.5},
    {"id": "P", "type": "pipe", "d": "M320 180 H470", "value": 0},
    {"id": "V", "type": "valve", "x": 400, "y": 180, "label": "master valve", "value": 1}],
    "steps": [{"title": "The valve closes", "play": [["V", 0, 600]]}]}
GOOD["parts"].append({"type": "text", "x": 190, "y": 186, "text": "words printed on the tank's own outline", "fixed": True})
BAD = json.loads(json.dumps(GOOD))
GOOD["parts"].pop()


def main():
    if not studio.find_browser():
        print("SKIP - no Chrome or Edge (set CF_BROWSER)")
        return 0
    tmp = tempfile.mkdtemp(prefix="kit_studio_test_")
    try:
        good, bad = os.path.join(tmp, "good.kit.json"), os.path.join(tmp, "bad.kit.json")
        io.open(good, "w", encoding="utf-8").write(json.dumps(GOOD))
        io.open(bad, "w", encoding="utf-8").write(json.dumps(BAD))
        r, why = studio.run(good, panel="two-col", out=os.path.join(tmp, "shots"))
        check("the studio runs", r is not None, why)
        if r:
            text, probs = studio.summary(r, good)
            check("a well-made figure is clean at 1280 x 800, every step", not probs, text)
            big = r["sizes"].get("1280x800", {})
            check("both sizes are drawn", set(r["sizes"]) == {"1280x800", "1024x768"}, sorted(r["sizes"]))
            check("each step is audited (2 states)", len(big.get("states", [])) == 2, big.get("states"))
            rep = big.get("report") or {}
            check("the layout reports what it did", {"scale", "up", "labels", "moved", "unplaced", "theme"} <= set(rep), rep)
            check("on a deck's dark panel the figure is dark", rep.get("theme") == "dark", rep.get("theme"))
            check("no word under 12.5 px", (rep.get("minTextPx") or 0) >= 12.45, rep.get("minTextPx"))
            check("a screenshot per size", all(os.path.isfile(v.get("shot") or "") for v in r["sizes"].values()),
                  [v.get("shot") for v in r["sizes"].values()])
        r2, _ = studio.run(good, panel="task", sizes=((1280, 800),), out=os.path.join(tmp, "shots2"))
        check("on a task page's white card the figure takes the light colours", r2 and
              (r2["sizes"]["1280x800"].get("report") or {}).get("theme") == "light")
        r3, _ = studio.run(bad, panel="two-col", sizes=((1280, 800),), out=os.path.join(tmp, "shots3"))
        _, p3 = studio.summary(r3, bad) if r3 else (None, [])
        check("words fixed on a line are found (text zone)", any(c == "text zone" for _, _, c, _, _ in p3), p3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
