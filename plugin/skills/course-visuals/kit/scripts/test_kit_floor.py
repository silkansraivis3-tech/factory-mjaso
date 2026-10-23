#!/usr/bin/env python3
"""test_kit_floor.py - no word of a kit figure is drawn under the 12.5 px floor, whatever width its column has
(2.52.0). The same figure is drawn at 100 column widths, each a little larger frame-to-panel scale than the last, with
a part past its frame so the layout grows the frame (and shows everything smaller) after it has sized the words: every
word, measured the way both audits measure it (audit_deck.js svgSmall: declared x rendered width / viewBox width;
audit_drawing.js SMALL TEXT: declared x screen scale), must be 12.5 px or more.
M01 workflow benchmark, 2026-10-20: words grown with a 0.1 % margin, and not grown again for a scale change under 1 %,
read 12.4 px at scales of 0.978-0.996 (16 deck findings in one M01 run, 56 on M02 at 1024x768).
Also (2.60.0): a flame's, a fire's and a spark's own words go with them at value 0 and come back when they burn.
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


# 2.60.0 - a part's own words at value 0: "gas burning at the mast" stood beside a mast with no flame after the fire was
# out (IGF M05 s10, M06 s12, M11 s08, M13 s02 / s04). Lit at step 1, out again at step 2.
GONE = {"size": [640, 300], "label": "words at value 0", "parts": [
    {"id": "TK", "type": "tank", "x": 30, "y": 170, "w": 170, "h": 80, "label": "Fuel tank", "value": 0},
    {"id": "FL", "type": "flame", "x": 300, "y": 120, "label": "gas burning at the mast", "value": 0},
    {"id": "FP", "type": "fire", "x": 420, "y": 250, "w": 120, "label": "pool fire", "value": 0},
    {"id": "FS", "type": "fire", "x": 250, "y": 280, "w": 80, "label": "the cargo fire", "state": True, "value": 0},
    {"id": "SK", "type": "spark", "x": 560, "y": 120, "label": "spark", "value": 0}],
    "steps": [{"title": "1", "play": [["FL", 1, 0], ["FP", 1, 0], ["SK", 1, 0]]},
              {"title": "2", "play": [["FL", 0, 0], ["FP", 0, 0], ["SK", 0, 0]]}]}
GONE_PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="%(css)s">
<style>body{margin:0;background:#0d1b2a}.w{width:900px}.w svg{display:block;width:100%%;height:auto}</style>
</head><body><div class="w"></div><pre id="out"></pre><script src="%(js)s"></script>
<script>
window.addEventListener('load', function () {
  var f = KIT.mount(document.querySelector('.w'), %(spec)s), out = {};
  setTimeout(function () {
    KIT.layoutAll(true);
    function shown(n) { var v = 1; for (; n && n.tagName.toLowerCase() !== 'svg'; n = n.parentNode) { var c = getComputedStyle(n);
      if (c.display === 'none' || c.visibility === 'hidden') { return 0; } v *= parseFloat(c.opacity); } return +v.toFixed(2); }
    [0, 1, 2].forEach(function (k) {
      f.go(k, true);
      var row = {};
      ['TK', 'FL', 'FP', 'FS', 'SK'].forEach(function (id) {
        var l = f.svg.querySelector('[data-kit-id="' + id + '"] .kit-lbl'), b = l ? l.getBBox() : null;
        row[id] = l ? [shown(l), b && b.width > 0 ? 1 : 0, l.__kitLeader ? shown(l.__kitLeader) : -1] : null;
      });
      out['s' + k] = row;
    });
    document.getElementById('out').textContent = JSON.stringify(out);
  }, 300);
});
</script></body></html>"""


# 2.60.0 - M01 benchmark s07: two revealed texts, "cool the liquid" (the last of four lines) printed on "no venting to
# atmosphere"; the studio and the drawing check were clean, only the review sheet saw it
STACK = {"size": [640, 390], "label": "boil-off", "parts": [
    {"id": "BO", "type": "boil_off", "x": 20, "y": 44, "w": 260, "h": 140, "heatLabel": "heat leaks in"},
    {"id": "TW", "type": "text", "x": 14, "y": 280, "anchor": "start", "reveal": True,
     "text": "reliquefy the vapour\nburn it in a thermal oxidiser\nlet pressure build in the tank\ncool the liquid"},
    {"id": "TV", "type": "text", "x": 14, "y": 336, "anchor": "start", "reveal": True, "text": "no venting to atmosphere,\nexcept in an emergency"}],
    "steps": [{"title": "1", "play": [["BO", 1, 0]]}, {"title": "2", "play": [["TW", 1, 0]]}, {"title": "3", "play": [["TV", 1, 0]]}]}
STACK_PAGE = """<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="%(css)s">
<style>body{margin:0;background:#0d1b2a}.w{width:560px}.w svg{display:block;width:100%%;height:auto}</style>
</head><body><div class="w"></div><pre id="out"></pre><script src="%(js)s"></script><script src="%(aud)s"></script>
<script>
window.addEventListener('load', function () {
  var f = KIT.mount(document.querySelector('.w'), %(spec)s), out = {};
  setTimeout(function () {
    KIT.layoutAll(true);
    f.go(3, true);
    function box(id) { return f.svg.querySelector('[data-kit-id="' + id + '"] text').getBoundingClientRect(); }
    function zone() { return (AuditDrawing.page().findings || []).filter(function (x) { return x.check === 'text zone' &&
      /part TW/.test(x.part + x.other) && /part TV/.test(x.part + x.other); }).length; }
    out.gap = +(box('TV').top - box('TW').bottom).toFixed(1);
    out.laid = zone();
    /* the benchmark's placement: the venting words moved up until their line box stands 4 px into the last line's */
    var g = f.svg.querySelector('[data-kit-id="TV"] .kit-lbl'), d = box('TV').top - box('TW').bottom + 4, k = f.svg.getScreenCTM().a;
    g.setAttribute('transform', 'translate(0 ' + (-d / k).toFixed(2) + ') ' + (g.getAttribute('transform') || ''));
    out.forced = +(box('TV').top - box('TW').bottom).toFixed(1);
    out.found = zone();
    document.getElementById('out').textContent = JSON.stringify(out);
  }, 300);
});
</script></body></html>"""


def stack_part(exe, tmp):
    page = tmp / "stack.html"
    aud = KIT.parent.parent / "course-module-ux" / "measure" / "scripts" / "audit_drawing.js"
    page.write_text(STACK_PAGE % {"css": (KIT / "kit.css").as_uri(), "js": (KIT / "kit.js").as_uri(), "aud": aud.as_uri(),
                                  "spec": json.dumps(STACK)}, encoding="utf-8")
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + str(tmp / "prof3"),
                        "--allow-file-access-from-files", "--window-size=1000,700", "--virtual-time-budget=8000",
                        "--dump-dom", page.as_uri()], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    r = json.loads(unescape(m.group(1))) if m and m.group(1).strip() else {}
    check("2.60.0: the kit lays two revealed texts apart - the venting words stand clear of the four-line text's last line",
          r.get("gap", -9) >= 0 and r.get("laid") == 0, r)
    check("... and the drawing audit reports two different labels whose lines stand into each other (4 px), stacked as they were",
          r.get("forced", 9) < -3 and r.get("found", 0) >= 1, r)


def gone_part(exe, tmp):
    page = tmp / "gone.html"
    page.write_text(GONE_PAGE % {"css": (KIT / "kit.css").as_uri(), "js": (KIT / "kit.js").as_uri(), "spec": json.dumps(GONE)},
                    encoding="utf-8")
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + str(tmp / "prof2"),
                        "--allow-file-access-from-files", "--window-size=1000,700", "--virtual-time-budget=8000",
                        "--dump-dom", page.as_uri()], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    r = json.loads(unescape(m.group(1))) if m and m.group(1).strip() else {}
    s0, s1, s2 = r.get("s0") or {}, r.get("s1") or {}, r.get("s2") or {}
    check("2.60.0: the flame's, the fire's and the spark's own words are not shown while the part is out (at rest and after "
          "it goes out again)", all((s.get(i) or [1])[0] == 0 for s in (s0, s2) for i in ("FL", "FP", "SK")), r)
    check("... and shown, laid out, while it burns (step 1) - the audit sees them at their visible step",
          all((s1.get(i) or [0, 0])[:2] == [1, 1] for i in ("FL", "FP", "SK")), s1)
    check("... a leader line, where one was drawn, goes with its words", all((s.get(i) or [0, 0, -1])[2] in (-1, 0)
                                                                            for s in (s0, s2) for i in ("FL", "FP", "SK")), r)
    check("... a part that still draws at 0 keeps its name (an empty tank), and a fire with a state line keeps its words "
          "(it says OUT)", all((s.get("TK") or [0])[0] == 1 and (s.get("FS") or [0])[0] == 1 for s in (s0, s1, s2)), r)


def main():
    exe = browser()
    if not exe:
        print("SKIP  no Chrome/Edge")
        return 0
    tmp = Path(tempfile.mkdtemp(prefix="kitfloor_"))
    try:
        gone_part(exe, tmp)
        stack_part(exe, tmp)
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
        # 2.63.3 (item 4 - the 2.63.2 run: "tiny labels" in 14 of 15 modules) - a deck figure (--kit-floor: 16, kit.css on a
        # slide) keeps 16 px at every width, measured as both audits measure it; a task page's figure keeps 12.5
        hosts16 = "".join('<div class="w" style="width:%dpx;--kit-floor:16"></div>' % w for w in widths)
        page16 = tmp / "floor16.html"
        page16.write_text(PAGE % {"css": (KIT / "kit.css").as_uri(), "js": (KIT / "kit.js").as_uri(),
                                  "spec": json.dumps(SPEC), "hosts": hosts16}, encoding="utf-8")
        p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + str(tmp / "prof16"),
                               "--allow-file-access-from-files", "--window-size=1280,2600", "--virtual-time-budget=8000",
                               "--dump-dom", page16.as_uri()], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=180)
        m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
        r16 = json.loads(unescape(m.group(1))) if m and m.group(1).strip() else []
        low16 = [r for r in r16 if r["deckPx"] < 16 or r["drawPx"] < 15.95]
        check("2.63.3 a deck figure (--kit-floor: 16) keeps every word at 16 px or more at all %d widths" % len(r16),
              len(r16) == len(widths) and not low16, ["w %d scale %.3f: %r %.2f px" % (r["w"], r["scale"], r["word"], r["deckPx"]) for r in low16][:8])
        css = (KIT / "kit.css").read_text(encoding="utf-8")
        sys.path.insert(0, str(KIT.parent.parent / "course-factory" / "compile" / "scripts"))
        import compile_module as cm
        check("... the floor is the course's choice (\"deck_label_px\" in its build sheet), never set by kit.css: the default "
              "stays 12.5 (16 failed 16 of 34 finished IGF figures)", "--kit-floor:" not in css.replace("--kit-floor:16\"", "")
              and cm.deck_floor({"deck_label_px": 16}) == 16 and cm.deck_floor({}) == 0 and cm.deck_floor({"deck_label_px": 10}) == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d failure(s)" % len(FAILS) if FAILS else "\nALL PASS")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
