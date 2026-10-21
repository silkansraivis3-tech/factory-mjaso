#!/usr/bin/env python3
"""test_kit_floor.py - no word of a kit figure is drawn under the 12.5 px floor, whatever width its column has
(2.52.0). The same figure is drawn at 100 column widths, each a little larger frame-to-panel scale than the last, with
a part past its frame so the layout grows the frame (and shows everything smaller) after it has sized the words: every
word, measured the way both audits measure it (audit_deck.js svgSmall: declared x rendered width / viewBox width;
audit_drawing.js SMALL TEXT: declared x screen scale), must be 12.5 px or more.
M01 workflow benchmark, 2026-10-20: words grown with a 0.1 % margin, and not grown again for a scale change under 1 %,
read 12.4 px at scales of 0.978-0.996 (16 deck findings in one M01 run, 56 on M02 at 1024x768).
Run: python test_kit_floor.py  (SKIP without Chrome/Edge)"""
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
KIT = Path(__file__).resolve().parent.parent
FAILS = []
sys.path.insert(0, str(KIT.parent.parent / "course-factory" / "scripts"))
import browser_slots  # noqa: E402  - one pool of hidden browsers for the whole computer (2.57.0)


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


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


# a side view in the M01 manner: rooms with their names inside, a tank, a vent mast, and an engine block that reaches
# 50 units past the 640-wide frame - the layout grows the frame to hold it after the words were sized for the first scale
SPEC = {"size": [640, 390], "label": "floor test", "parts": [
    {"id": "R1", "type": "space", "x": 20, "y": 120, "w": 250, "h": 200, "label": "Tank connection space"},
    {"id": "R2", "type": "space", "x": 290, "y": 120, "w": 250, "h": 200, "label": "Fuel preparation room"},
    {"id": "T", "type": "tank", "x": 50, "y": 200, "w": 180, "h": 90, "label": "Fuel tank", "value": 0.6},
    {"id": "P", "type": "pipe", "d": "M230 245 H560", "value": 0},
    {"id": "V", "type": "valve", "x": 420, "y": 245, "label": "Master valve", "value": 1},
    {"id": "E", "type": "space", "x": 560, "y": 150, "w": 130, "h": 170, "label": "Engine room"},
    {"type": "text", "x": 30, "y": 60, "text": "LNG-fuelled ship, side view"}]}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="%(css)s">
<style>body{margin:0;background:#0d1b2a;font-family:Arial,sans-serif}.w{margin:0 0 4px}.w svg{display:block;width:100%%;height:auto}</style>
</head><body>%(hosts)s<pre id="out"></pre>
<script src="%(js)s"></script>
<script>
var SPEC = %(spec)s;
window.addEventListener('load', function () {
  var hosts = document.querySelectorAll('.w');
  [].forEach.call(hosts, function (h) { KIT.mount(h, JSON.parse(JSON.stringify(SPEC))); });
  setTimeout(function () {
    KIT.layoutAll(true);
    var rows = [];
    [].forEach.call(hosts, function (h) {
      var svg = h.querySelector('svg.kit'), vb = svg.getAttribute('viewBox').split(/[\\s,]+/).map(Number);
      var sc = svg.getBoundingClientRect().width / vb[2], low = 1e9, lowScr = 1e9, word = '';
      [].forEach.call(svg.querySelectorAll('text'), function (t) {
        if (!(t.textContent || '').trim() || getComputedStyle(t).display === 'none') return;
        var f = parseFloat(getComputedStyle(t).fontSize), m = t.getScreenCTM();
        var scr = f * (m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1);
        if (f * sc < low) { low = f * sc; word = t.textContent.trim(); }
        lowScr = Math.min(lowScr, scr);
      });
      rows.push({ w: h.clientWidth, scale: +sc.toFixed(4), deckPx: +low.toFixed(3), drawPx: +lowScr.toFixed(3), word: word,
                  up: svg.__kitUp || null });
    });
    document.getElementById('out').textContent = JSON.stringify(rows);
  }, 300);
});
</script></body></html>"""


def main():
    exe = browser()
    if not exe:
        print("SKIP  no Chrome/Edge")
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="kitfloor_"))
    try:
        widths = list(range(560, 760, 2))
        hosts = "".join('<div class="w" style="width:%dpx"></div>' % w for w in widths)
        page = tmp / "floor.html"
        page.write_text(PAGE % {"css": (KIT / "kit.css").as_uri(), "js": (KIT / "kit.js").as_uri(),
                                "spec": json.dumps(SPEC), "hosts": hosts}, encoding="utf-8")
        p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + str(tmp / "prof"),
                            "--allow-file-access-from-files", "--window-size=1280,2600", "--virtual-time-budget=8000",
                            "--dump-dom", page.as_uri()], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=180)
        m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
        rows = json.loads(unescape(m.group(1))) if m and m.group(1).strip() else []
        check("the page laid out all %d figures" % len(widths), len(rows) == len(widths), "%d rows" % len(rows))
        if rows:
            grown = [r for r in rows if r["scale"] < 1]
            check("the sweep reaches the scales the benchmark hit (0.978-0.996) - frames grown below 1:1",
                  any(0.97 < r["scale"] < 1 for r in grown), [r["scale"] for r in rows][:12])
            deck = [r for r in rows if r["deckPx"] < 12.5]
            check("no word under 12.5 px as audit_deck.js measures it (declared x rendered width / viewBox width)",
                  not deck, ["w %d scale %.3f: %r %.2f px" % (r["w"], r["scale"], r["word"], r["deckPx"]) for r in deck][:8])
            draw = [r for r in rows if r["drawPx"] < 12.45]
            check("no word under 12.5 px as audit_drawing.js measures it (declared x screen scale)",
                  not draw, ["w %d scale %.3f: %.2f px" % (r["w"], r["scale"], r["drawPx"]) for r in draw][:8])
            big = max([r["deckPx"] for r in grown] or [0])
            check("the margin stays small: shown below 1:1, a figure's smallest word is grown to 13.2 px at most", big <= 13.2, big)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failure(s)" % len(FAILS) if FAILS else "\nALL PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
