#!/usr/bin/env python3
"""test_label_layout.py - a "label the drawing" task's empty boxes are sized and placed by themselves (2.48.0).
Run: python test_label_layout.py"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label_layout as ll  # noqa: E402
import task_pages as tp  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def places(spec):
    """[(words, cx %, cy %)] -> places as task_pages makes them (a 6 % square tap area round each point)"""
    return [{"t": t, "box": [x - 3, y - 3, 6, 6], "at": None} for t, x, y in spec]


def clean(ps, what):
    rows = {}
    for p in ps:
        left, top, w = p["at"]
        check("%s: %s inside the drawing" % (what, p["t"]), 1.0 - 1e-6 <= left and left + w <= 99.0 + 1e-6, p["at"])
        rows.setdefault(top, []).append(p)
    for top, row in rows.items():
        row.sort(key=lambda p: p["at"][0])
        for a, b in zip(row, row[1:]):
            check("%s: %s and %s do not touch" % (what, a["t"], b["t"]), a["at"][0] + a["at"][2] + 0.99 <= b["at"][0], (a["at"], b["at"]))
        order = [p["box"][0] for p in row]
        check("%s: the boxes keep the order of their places (no crossed leaders)" % what, order == sorted(order), order)
    return rows


# the IGF pilot's M03 q06 (five boxes in one band ran off the right edge; placed by hand in the build sheet)
VB = (0, -40, 900, 380)
q06 = places([("Remote-operated shutdown valve", 18, 40), ("Manual stop valve", 35, 42), ("Dry-disconnect coupling", 62, 45),
              ("Breakaway coupling", 80, 44), ("Drip tray", 66, 70)])
probs = []
tp.label_boxes(q06, VB, probs, "q06")
rows = clean(q06, "M03 q06")
w = {p["at"][2] for p in q06}
check("one width for every box of the question (the size never tells which is which)", len(w) == 1, w)
need = max(tp.label_px(p["t"]) for p in q06) * 100.0 / (VB[2] * tp.ppu(VB))
check("the boxes are as wide as the longest label needs (task_pages.label_px - the one sizing)", abs(w.pop() - need) < 0.05, need)
check("five boxes that fit are not reported", not probs, probs)
corner = tp.CORNER_PX * 100.0 / (VB[2] * tp.ppu(VB))
check("the top row keeps clear of the drawing's full-screen button",
      all(p["at"][0] + p["at"][2] <= 100 - corner + 1e-6 for p in q06 if p["at"][1] < 50), [p["at"] for p in q06])

# M01 m01 (boxes 17 % wide cut "Tank connection space" off)
m01 = places([("Tank connection space", 30, 70), ("Fuel preparation room", 45, 72), ("Fuel tank", 62, 75),
              ("Vent mast", 40, 20), ("Bunkering station", 55, 25)])
VB1 = (0, -30, 1000, 300)
tp.label_boxes(m01, VB1)
clean(m01, "M01 m01")
px = m01[0]["at"][2] / 100.0 * VB1[2] * tp.ppu(VB1)
check("'Tank connection space' gets a box that holds it with its tick (%.0f px)" % px, px >= tp.label_px("Tank connection space") - 0.5, px)
c3, c4 = (m01[k]["at"][0] + m01[k]["at"][2] / 2 for k in (3, 4))
check("two boxes too close for their places move apart evenly - as near them as they can be (least squares)",
      abs((c3 + c4) / 2 - 47.5) < 0.05, [p["at"] for p in m01])

# IGF M02 m01: five boxes in the band below, the last place near the right edge - the row was pushed off the edge (109 %)
m02 = places([("Fuel tank", 20, 60), ("Tank connection space", 22, 75), ("Vaporizer and heater", 38, 30),
              ("Gas valve unit", 72, 55), ("Double-walled pipe", 82, 58), ("Dual-fuel engine", 92, 60)])
VB2 = (0, -64, 1200, 441)
tp.label_boxes(m02, VB2)
clean(m02, "M02 m01")

# a band that cannot hold its boxes hands the ones nearest the middle to the other band
crowd = places([("Gas valve unit with double block and bleed %d" % i, 10 + i * 14, 20 + i) for i in range(6)])
probs = []
tp.label_boxes(crowd, VB1, probs, "crowd")
r = clean(crowd, "six in the upper half")
check("six long labels in the upper half use both bands", len(r) == 2, sorted(r))
check("none is reported when two bands hold them", not probs and not any(p.get("crowded") for p in crowd), probs)
many = places([("Tank connection space %d" % i, 5 + i * 10, 20) for i in range(14)])
probs = []
tp.label_boxes(many, VB1, probs, "many")
check("more than two bands hold is reported, and still nothing runs off the drawing",
      probs and "do not fit" in probs[0] and all(1 - 1e-6 <= p["at"][0] and p["at"][0] + p["at"][2] <= 99 + 1e-6 for p in many), probs)

# the build sheet still wins when it gives a box
given = [{"t": "Fuel tank", "box": [10, 60, 6, 6], "at": [5, 85, 20]}]
check("a box the build sheet gives is kept (task_pages only lays out the others)", given[0]["at"] == [5, 85, 20])

# PAV: the nearest ordered places
check("pav keeps an ordered set as it is", ll.pav([1, 2, 3], [0] * 3, [10] * 3) == [1, 2, 3])
check("pav pools what is out of order", ll.pav([3, 1], [0, 0], [10, 10]) == [2.0, 2.0])

print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
