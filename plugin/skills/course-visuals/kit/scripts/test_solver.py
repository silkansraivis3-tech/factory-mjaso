#!/usr/bin/env python3
"""test_solver.py - KIT.solveLabels, the label solver alone, in plain numbers with no SVG (2.45.0): the one a 3D figure's
label overlays will use. Run: python test_solver.py   (needs Node.js; says SKIP without it)"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KIT_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kit.js")

# kit.js wants a page: the least of one, then the solver on three cases
JS = r"""
global.window = global;
global.document = { readyState: 'complete', addEventListener: function () {}, querySelectorAll: function () { return []; },
                    querySelector: function () { return null; }, head: null };
require(%s);
var S = window.KIT.solveLabels, out = {};
function line(x1, y1, x2, y2) { var p = []; for (var i = 0; i <= 50; i++) p.push({ x: x1 + (x2 - x1) * i / 50, y: y1 + (y2 - y1) * i / 50 }); return { pts: p, r: 1 }; }
// 1 a label already clear stays where it is
var a = S([line(0, 50, 200, 50)], [{ box: { x: 20, y: 10, x2: 80, y2: 22 } }], [0, 0, 200, 100], 4);
out.stays = a.moved === 0 && a.at[0].x === 20;
// 2 a label printed on a line moves off it - beside its part - and keeps 4 clear
var anchor = { x: 90, y: 40, x2: 110, y2: 60 }, pts = [{ x: 100, y: 40 }, { x: 100, y: 60 }];
var b = S([line(0, 50, 200, 50)], [{ box: { x: 70, y: 44, x2: 130, y2: 56 }, anchor: anchor, pts: pts }], [0, 0, 200, 100], 4);
var bx = b.at[0];
out.moves = b.moved === 1 && (bx.y2 + 4 <= 49 || bx.y - 4 >= 51);
// 3 two labels wanting the same place: both placed, never on each other
var c = S([], [{ box: { x: 50, y: 40, x2: 110, y2: 52 } }, { box: { x: 52, y: 42, x2: 112, y2: 54 } }], [0, 0, 200, 100], 4);
var p = c.at[0], q = c.at[1];
out.apart = !(p.x < q.x2 + 4 && q.x < p.x2 + 4 && p.y < q.y2 + 4 && q.y < p.y2 + 4);
// 4 no room anywhere: reported, never forced over a line
var d = S([line(0, 10, 40, 10), line(0, 20, 40, 20), line(0, 30, 40, 30)], [{ box: { x: 2, y: 12, x2: 38, y2: 28 }, opt: { lead: false, near: 2 } }], [0, 0, 40, 40], 4);
out.unplaced = d.unplaced.length === 1;
// 5 far from its part: a leader joins them, and it starts on the part's outline
var e = S([{ rect: { x: 0, y: 0, x2: 200, y2: 70 } }], [{ box: { x: 80, y: 30, x2: 140, y2: 42 }, anchor: { x: 100, y: 30, x2: 104, y2: 34 }, pts: [{ x: 102, y: 32 }] }], [0, 0, 200, 140], 4);
out.leader = e.leaders === 1 && e.leader[0] && e.leader[0].x1 === 102 && e.leader[0].y1 === 32;
console.log(JSON.stringify(out));
"""


def main():
    node = shutil.which("node")
    if not node:
        print("SKIP - no Node.js")
        return 0
    p = subprocess.run([node, "-e", JS % json.dumps(KIT_JS)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        r = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("FAIL  the solver ran   -> %s" % (p.stderr or p.stdout)[-800:])
        return 1
    fails = 0
    for key, what in (("stays", "a label already clear stays where it is"),
                      ("moves", "a label printed on a line moves off it, 4 clear"),
                      ("apart", "two labels wanting one place never land on each other"),
                      ("unplaced", "with no room anywhere it is reported, never forced over a line"),
                      ("leader", "a label far from its part gets a leader that starts on the part's outline")):
        ok = r.get(key) is True
        fails += not ok
        print(("PASS  " if ok else "FAIL  ") + what)
    print("\n%s" % ("ALL PASS" if not fails else "%d FAILED" % fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
