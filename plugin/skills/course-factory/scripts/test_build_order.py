# -*- coding: utf-8 -*-
"""test_build_order - the modules of a parallel build, biggest first (2.71.0). No browser.

    python test_build_order.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_order  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def course(root, scripts, sheets=None):
    d = os.path.join(root, "working_claude", "script")
    os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(root, "modules"), exist_ok=True)
    for mid, screens in scripts.items():
        json.dump({"screens": screens}, open(os.path.join(d, mid + ".json"), "w", encoding="utf-8"))
    for mid, sheet in (sheets or {}).items():
        json.dump({"screens": sheet}, open(os.path.join(d, mid + ".build.json"), "w", encoding="utf-8"))
    return root


def slide(i, kind=None, title="T", text="words"):
    return {"id": "s%02d" % i, "kind": "slide", "title": title, "text": text, "visual_kind": kind}


def main():
    tmp = tempfile.mkdtemp(prefix="test_border_")
    try:
        small = [slide(1, "photo"), slide(2, "none")]
        big = [slide(i, "schematic") for i in range(1, 9)] + [slide(9, "model_3d")]
        mid = [slide(i, "comparison + photo") for i in range(1, 5)] + [slide(5, "photo")] * 0
        c = course(os.path.join(tmp, "c"), {"M01": small, "M02": big, "M03": mid})
        rows = build_order.order(c, [1, 2, 3])
        check("biggest first: the module with the most drawn screens and a 3D scene leads, the photo-only one is last",
              [r["id"] for r in rows] == [2, 3, 1], rows)
        r2 = next(r for r in rows if r["id"] == 2)
        check("... its cost: 9 screens + 3 x 8 drawn + 6 x one 3D scene = 39",
              r2["cost"] == 9 + 3 * 8 + 6 and r2["drawn"] == 8 and r2["scenes"] == 1, r2)
        check("... a visual kind with a photo beside it counts by its first word (\"comparison + photo\" is drawn)",
              next(r for r in rows if r["id"] == 3)["drawn"] == 4, rows)
        # a predecessor drew the same words: those screens are seeded and cost less (compile_module.py --init-build copies them)
        old = course(os.path.join(tmp, "old"), {"M02": big}, {"M02": {s["id"]: {"figure": "%s.kit.json" % s["id"]} for s in big[:6]}})
        seeded = build_order.order(c, [2], old)[0]
        check("seed_from: the 6 screens a predecessor drew for the same words are seeded, each costing 1 instead of 3",
              seeded["seeded"] == 6 and seeded["cost"] == 9 + 3 * 2 + 1 * 6 + 6, seeded)
        changed = [dict(s, text="new words") if s["id"] == "s01" else s for s in big]
        c2 = course(os.path.join(tmp, "c2"), {"M02": changed})
        check("... a screen whose words changed is not seeded", build_order.order(c2, [2], old)[0]["seeded"] == 5,
              build_order.order(c2, [2], old))
        json.dump({"seed_from": "../old"}, open(os.path.join(c, "working_claude", "course.build.json"), "w"))
        check("... the course's own course.build.json \"seed_from\" is used when none is given (a relative path from the course)",
              build_order.order(c, [2])[0]["seeded"] == 6, build_order.order(c, [2]))
        check("a module with no script costs nothing and goes last", build_order.order(c, [9, 1])[-1]["id"] == 9)
        # the weights against the builder minutes of the two IGF whole-course runs (2.63.0 / 2.63.2, REVIEW.md), when the
        # course is on this computer: the biggest by cost is among the three slowest
        igf = os.path.join(os.path.expanduser("~"), "Desktop", "IGF_course_2.63.2", "course")
        if os.path.isfile(os.path.join(igf, "working_claude", "script", "M02.json")):
            minutes = {1: 60.5, 2: 83.5, 3: 70.5, 4: 23.5, 5: 34.5, 6: 53.5, 7: 41, 8: 23.5, 9: 25.5, 10: 11, 11: 24, 12: 18.5,
                       13: 37.5, 14: 17.5, 15: 17}
            rows = build_order.order(igf, list(minutes))
            slow = sorted(minutes, key=lambda k: -minutes[k])
            top4 = [r["id"] for r in rows[:4]]
            check("IGF: the cost's biggest module (M%02d) is among the three slowest of the 2.63.0 / 2.63.2 runs, and its top four "
                  "are all among the five slowest" % rows[0]["id"],
                  rows[0]["id"] in slow[:3] and set(top4) <= set(slow[:5]), (top4, slow[:5]))
        else:
            print("  skip  the IGF check (no Desktop\\IGF_course_2.63.2 on this computer)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
