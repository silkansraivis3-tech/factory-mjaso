#!/usr/bin/env python3
"""test_label_layout.py - a "label the drawing" task's empty boxes are sized and placed by themselves (2.48.0).
Run: python test_label_layout.py"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile

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

# 2.50.6 (M01 benchmark run 5, m01) - five two-line labels on the 2:1 GA of s04: as wide as the drawing, the two rows held
# four (the build sheet placed all five by hand). The drawing is shown 560 of the row's 1240 px wide, so the rows reach past
# it - three boxes to a row - and the drawing keeps its size
GA = {"size": [640, 310], "label": "the GA", "parts": [
    {"id": "G", "type": "ga", "x": 20, "y": 160, "w": 600, "h": 130, "house": {"x": 34, "w": 110, "h": 80}, "funnel": {"x": 62, "w": 24, "h": 34}},
    {"id": "ER", "type": "space", "x": 150, "y": 176, "w": 110, "h": 84, "label": "Engine room"},
    {"id": "FPR", "type": "space", "x": 268, "y": 176, "w": 74, "h": 84, "label": "Fuel preparation room"},
    {"id": "TCS", "type": "space", "x": 350, "y": 176, "w": 50, "h": 84, "style": "enclosure", "label": "Tank connection space"},
    {"id": "TK", "type": "tank", "x": 406, "y": 186, "w": 140, "h": 64, "label": "Fuel tank", "value": 0.6},
    {"id": "BS", "type": "space", "x": 272, "y": 126, "w": 66, "h": 34, "style": "enclosure", "label": "Bunkering station"},
    {"id": "VP", "type": "pipe", "fluid": "gas", "d": "M375 176 V30", "value": 0},
    {"id": "VM", "type": "vent", "x": 375, "y": 30, "labelAt": "right", "label": "Vent mast"}]}
FIVE = ["Fuel tank", "Tank connection space", "Fuel preparation room", "Bunkering station", "Vent mast"]
raw = (0.0, 0.0, 640.0, 310.0)
narrow = tp.band_vb(raw)
gp = [{"t": t, "box": [100.0 * (x - narrow[0]) / narrow[2], 100.0 * (y - narrow[1]) / narrow[3], 100.0 * w_ / narrow[2], 100.0 * h_ / narrow[3]]}
      for t, (x, y, w_, h_) in zip(FIVE, [(406, 186, 140, 64), (350, 176, 50, 84), (268, 176, 74, 84), (272, 126, 66, 34), (369, 30, 12, 146)])]
if not hasattr(tp, "label_side"):
    check("task_pages.label_side - the label rows reach past a narrow drawing", False, "missing (before 2.50.6)")
else:
    check("M01 m01: as wide as the drawing, the two label rows do not hold the five boxes (the run 5 failure)",
          tp.rows_fit([dict(p) for p in gp], narrow) is not True)
    side = tp.label_side(gp, raw)
    wide = tp.band_vb(raw, side)
    check("... so the rows reach past the drawing on both sides (%.0f units each)" % side, side > 0, side)
    check("... and the drawing keeps its size on the screen", abs(tp.ppu(wide) - tp.ppu(narrow)) < 1e-9, (tp.ppu(wide), tp.ppu(narrow)))
    check("... and stays inside the screen's row (1240 px)", wide[2] * tp.ppu(wide) <= tp.WIDTH_PX + 1e-6, wide[2] * tp.ppu(wide))
    check("a drawing whose boxes already fit two to a row is not widened", tp.label_side(gp[:3], raw) == 0.0, tp.label_side(gp[:3], raw))

tmp = tempfile.mkdtemp(prefix="label_rows_")
try:
    with open(os.path.join(tmp, "ga.kit.json"), "w", encoding="utf-8") as f:
        json.dump(GA, f)
    q = {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "label_diagram", "question": "Drag each label to its place.",
         "visual": "the GA", "answer": "\n".join(FIVE), "feedback": "These are the new spaces."}
    sheet = {"figure": "ga.kit.json", "unlabel": "answers",
             "labels": {"Bunkering station": {"at": "BS"}, "Vent mast": {"at": "VM"}, "Fuel preparation room": {"at": "FPR"},
                        "Tank connection space": {"at": "TCS"}, "Fuel tank": {"at": "TK"}}}
    probs = []
    html = tp.question_html(1, q, sheet, tmp, tmp, {"_bands": {"ga.kit.json"}}, probs)
    check("M01 m01 built: no box placed by hand and nothing reported", not probs, probs)
    boxes = [[float(v) for v in m] for m in re.findall(r'class="lbox zone"[^>]*style="left:([\d.]+)%;top:([\d.]+)%;width:([\d.]+)%', html)]
    rows_ = {}
    for left, top, w_ in boxes:
        rows_.setdefault(top, []).append((left, left + w_))
    check("... five boxes, three to a row at most, none over another, none off the edge",
          len(boxes) == 5 and max(len(r) for r in rows_.values()) <= 3 and all(lo >= 0.99 and hi <= 99.01 for r in rows_.values() for lo, hi in r)
          and all(a_[1] <= b_[0] for r in rows_.values() for a_, b_ in zip(sorted(r), sorted(r)[1:])), boxes)
    vbm = re.search(r'"view":\[([-\d.,]+)\]', html)
    check("... and the drawing shown is the widened one (its view reaches past the GA on the left)",
          bool(vbm) and float(vbm.group(1).split(",")[0]) < 0, vbm and vbm.group(0))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# the build sheet still wins when it gives a box
given = [{"t": "Fuel tank", "box": [10, 60, 6, 6], "at": [5, 85, 20]}]
check("a box the build sheet gives is kept (task_pages only lays out the others)", given[0]["at"] == [5, 85, 20])

# PAV: the nearest ordered places
check("pav keeps an ordered set as it is", ll.pav([1, 2, 3], [0] * 3, [10] * 3) == [1, 2, 3])
check("pav pools what is out of order", ll.pav([3, 1], [0, 0], [10, 10]) == [2.0, 2.0])

print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
sys.exit(1 if FAILS else 0)
