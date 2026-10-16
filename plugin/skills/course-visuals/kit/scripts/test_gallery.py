#!/usr/bin/env python3
"""test_gallery.py - every figure in GALLERY.html draws, and is clean at every step on the dark AND the light panel
(2.48.0). Run: python test_gallery.py   (needs Chrome or Edge; says SKIP without one)

Each card and demo is judged with course-module-ux/measure/scripts/audit_drawing.js at the end of every step, as the
kit lays it out at 1280 x 800: inside, cut off, text zone, contrast and small text. EMPTY is not judged here - a card
is a small sample, not a panel a slide shows. Also: every part merged into kit.js has its card, no card failed to
draw, and the kit's own layout found a clear place for every label.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
SKILLS = os.path.dirname(os.path.dirname(KIT))
AUDIT = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "audit_drawing.js")
sys.path.insert(0, os.path.join(SKILLS, "course-factory", "compile", "scripts"))
import drawing_check as dc  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


PROBE = r"""<script src="%s"></script><script>
setTimeout(function () {
  var out = { figures: 0, errors: document.querySelectorAll('.kit-error').length, findings: [], unplaced: [], added: Object.keys(KIT.added) };
  KIT.layoutAll(true);
  KIT.figures.forEach(function (f, i) {
    var svg = f.svg, card = svg.closest('.card'), name = card && card.querySelector('h3') ? card.querySelector('h3').textContent : ('figure ' + (i + 1));
    out.figures++;
    for (var k = 0; k <= f.steps(); k++) {
      f.go(k, true);
      var r = AuditDrawing.figure(svg, name + ' step ' + k);
      (r.findings || []).forEach(function (x) {
        if (x.check !== 'empty') out.findings.push(x.where + ': ' + x.check + ' - ' + x.part + ' ' + (x.detail || '') + (x.other ? ' (' + x.other + ')' : ''));
      });
    }
    var rep = f.layout(true);
    ((rep && rep.unplaced) || []).forEach(function (u) { out.unplaced.push(name + ': "' + u.text + '"'); });
  });
  var p = document.createElement('pre'); p.id = '__gal'; p.textContent = JSON.stringify(out); document.body.appendChild(p);
}, 800);
</script>"""


def run(theme):
    exe = dc.find_browser()
    tmp = tempfile.mkdtemp(prefix="kit_gal_")
    try:
        t = io.open(os.path.join(KIT, "GALLERY.html"), encoding="utf-8").read()
        t = re.sub(r"<head>", '<head><base href="%s/">' % Path(KIT).as_uri(), t, count=1)
        i = t.lower().rfind("</body>")
        t = t[:i] + PROBE % Path(AUDIT).as_uri() + t[i:]
        page = os.path.join(tmp, "gallery.html")
        io.open(page, "w", encoding="utf-8").write(t)
        url = Path(page).as_uri() + ("?theme=light" if theme == "light" else "")
        p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                            "--user-data-dir=" + os.path.join(tmp, "p"), "--allow-file-access-from-files",
                            "--window-size=%d,%d" % dc.window_for(exe), "--virtual-time-budget=60000", "--dump-dom", url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        m = re.search(r'<pre id="__gal">(.*?)</pre>', p.stdout, re.S)
        return json.loads(html.unescape(m.group(1))) if m else None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if not dc.find_browser():
        print("SKIP - no Chrome or Edge (set CF_BROWSER)")
        return 0
    sys.path.insert(0, HERE)
    import check_kit as ck
    merged = [n for n, _ in ck.blocks(ck.read(ck.KIT_JS))]
    for theme in ("dark", "light"):
        r = run(theme)
        check("the gallery draws on the %s panel" % theme, r is not None, "no answer from the page")
        if not r:
            continue
        check("%s: no figure failed to draw" % theme, r["errors"] == 0, r["errors"])
        check("%s: every merged part has its card (%d)" % (theme, len(merged)), set(merged) <= set(r["added"]),
              sorted(set(merged) - set(r["added"])))
        check("%s: every figure is clean at every step (%d figures)" % (theme, r["figures"]), not r["findings"],
              "\n      " + "\n      ".join(r["findings"][:40]))
        check("%s: every label found a clear place" % theme, not r["unplaced"], r["unplaced"][:20])
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
