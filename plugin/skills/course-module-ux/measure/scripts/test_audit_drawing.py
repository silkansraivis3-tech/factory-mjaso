# -*- coding: utf-8 -*-
"""test_audit_drawing - every drawing whole and clean (L50), proven in a real browser.

    python test_audit_drawing.py

Opens measure/fixtures/drawing_defects.html and drawing_fit.html in headless Chrome or Edge (--dump-dom) and reads
what audit_drawing.js and gb_fit.js wrote into the page. Skips, and says so, when no Chrome or Edge is installed.
Pinned:
  * a room drawn as a rectangle in a sloping hull is found poking out - also when the hull is a shared <use>;
  * a tank cut off at the drawing's edge is found, and a ring that only shows in a later step;
  * a label printed over a line, and a label touching its own box's edge, are found;
  * a clean drawing - a room along the slope, a marked pipe through a bulkhead, a roof overhanging its deckhouse,
    liquid clipped to its tank, a label with its clearance - is silent;
  * gb_fit.js widens the frame of a drawing that reaches past it, leaves one that fits, and leaves data-fit="off".
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
FIX = HERE.parent / "fixtures"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def browser():
    for name in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if os.path.isfile(p):
            return p
    return None


def page_out(exe, html, prof):
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                        "--window-size=1280,2600", "--virtual-time-budget=4000", "--dump-dom", html.as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    return json.loads(unescape(m.group(1))) if m and m.group(1).strip() else None


def main():
    exe = browser()
    if not exe:
        print("  skip  no Chrome or Edge found - audit_drawing.js was not run (install Chrome, or run it by hand in a browser)")
        return 0
    prof = tempfile.mkdtemp(prefix="audit_drawing_")
    try:
        out = page_out(exe, FIX / "drawing_defects.html", prof)
        check("the probe ran in the browser and wrote its findings", out is not None, out)
        f = (out or {}).get("findings", [])
        has = lambda check_, svg, part=None: any(x["check"] == check_ and x["svg"] == svg and (part is None or x["part"] == part) for x in f)
        check("a rectangle room in a sloping hull pokes out (inside)", has("inside", "bad-inside", "room"), f)
        check("... also when the hull is a shared <use>", has("inside", "bad-use", "room-u"), f)
        check("a tank cut off at the drawing's edge (cut off)", has("cut off", "bad-cut", "tank"), f)
        check("a ring that only shows in a later step, cut off at the top", has("cut off", "bad-later", "zone")
              and any("later step" in x["detail"] for x in f if x["svg"] == "bad-later"), f)
        check("a label printed over a line (text zone)", has("text zone", "bad-text-over", "over"), f)
        check("a label touching the edge of its own box (text zone)", has("text zone", "bad-text-edge", "edge"), f)
        check("a clean drawing is silent - slope, marked pipe, overhanging roof, clipped liquid, clear label",
              not [x for x in f if x["svg"] == "good"], [x for x in f if x["svg"] == "good"])
        check("a clean drawing through a shared <use> is silent", not [x for x in f if x["svg"] == "good-use"],
              [x for x in f if x["svg"] == "good-use"])
        check("the verdict fails the page", (out or {}).get("verdict", "").startswith("VERDICT: FAIL"), out)

        fit = page_out(exe, FIX / "drawing_fit.html", prof) or {}
        sp = [float(v) for v in (fit.get("spills") or "0 0 0 0").split()]
        check("gb_fit widens a frame a drawing reaches past (up and right)", sp[1] < -16 and sp[0] + sp[2] > 108, fit)
        check("gb_fit leaves a drawing that fits", fit.get("fits") == "0 0 100 60", fit)
        check("gb_fit leaves data-fit=\"off\" alone", fit.get("off") == "0 0 100 60", fit)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
