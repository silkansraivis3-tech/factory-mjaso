#!/usr/bin/env python3
"""test_kit2d.py - the 2D kit in a hidden browser: every figure of the three demo pages (demos.html, pm.html, more.html)
(and courses.html) walked step by step at 1280 x 800 and 1024 x 768, and KIT2D.audit clean at the end of each step - no words over words,
no words out of their box, nothing cut at the edge, no label on a line, no box on another. Then that the audit itself
still finds each of those, that Next and Previous both move things (never a jump to the end), and that kit2d.css has no
colour defined as itself.

    python -I test_kit2d.py

Drives the Chrome or Edge already on the computer (Playwright, the factory's browser finder). About 3 minutes.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
KIT = HERE.parent
SKILLS = KIT.parents[1]
sys.path.insert(0, str(SKILLS / "course-module-ux" / "measure" / "scripts"))
from test_audit_drawing import browser  # noqa: E402  - the one place that finds Chrome or Edge

PAGES = ["demos.html", "pm.html", "more.html", "courses.html"]
SIZES = [(1280, 800), (1024, 768)]
FAILS = []


def check(what, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", what, "" if ok else "  -> %s" % str(detail)[:600]))
    if not ok:
        FAILS.append(what)


BROKEN = """() => { const h = document.createElement('div'); h.style.height = '600px'; document.body.prepend(h);
  const f = KIT2D.mount(h, {size: [1000, 600], parts: [
    {type: 'node', x: 30, y: 100, w: 200, h: 70, text: 'Half off the edge'},
    {type: 'node', x: 400, y: 300, w: 200, h: 70, text: 'Two'}, {type: 'node', x: 420, y: 310, w: 200, h: 70, text: 'Words'},
    {type: 'node', x: 760, y: 120, w: 110, h: 70, text: 'Interdepartmentalisation'},
    {type: 'person', x: 230, y: 560, name: 'A', say: 'Port twenty.', side: 'right', bubbleW: 220, bubbleH: 70},
    {type: 'person', x: 560, y: 560, name: 'B', say: 'Port twenty, sir.', side: 'left', bubbleW: 240, bubbleH: 70}]});
  const out = KIT2D.audit(f); h.remove(); return out; }"""


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("test_kit2d: Playwright is not installed - python -m pip install playwright")
        return 2
    exe = browser()
    if not exe:
        print("test_kit2d: no Chrome or Edge found - nothing tested")
        return 2

    print("-- kit2d.css: no colour defined as itself (a cycle paints nothing)")
    css = (KIT / "kit2d.css").read_text(encoding="utf-8")
    selfref = [m.group(1) for m in re.finditer(r"--([\w-]+)\s*:\s*var\(--([\w-]+)\)", css) if m.group(1) == m.group(2)]
    check("no --name: var(--name)", not selfref, selfref)

    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe, headless=True, args=["--allow-file-access-from-files"])
        for W, H in SIZES:
            print("\n-- every figure, every step, %d x %d: the audit is clean" % (W, H))
            for name in PAGES:
                pg = b.new_page(viewport={"width": W, "height": H})
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto((KIT / name).as_uri())
                pg.wait_for_timeout(900)
                found = []
                for i in range(pg.evaluate("KIT2D.figures.length")):
                    pg.evaluate("i => KIT2D.figures[i].svg.scrollIntoView()", i)
                    for s in range(pg.evaluate("i => KIT2D.figures[i].steps.length", i)):
                        pg.evaluate("([i, s]) => KIT2D.figures[i].goStep(s, true)", [i, s])
                        pg.wait_for_timeout(250)
                        found += ["fig %d step %d: %s" % (i, s, x) for x in pg.evaluate("i => KIT2D.audit(KIT2D.figures[i])", i)]
                check("%s: %d figure(s), no page error, nothing overlapping, spilling or cut" % (name, pg.evaluate("KIT2D.figures.length")),
                      not found and not errs, (found + errs)[:6])
                pg.close()

        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto((KIT / "demos.html").as_uri())
        pg.wait_for_timeout(900)
        print("\n-- the audit still finds what it is for")
        got = pg.evaluate(BROKEN)
        for kind in ("words cut at the edge", "words over words", "words spill out of their box", "boxes on each other", "a shape cut at the edge"):
            check("a broken figure: '%s' is found" % kind, any(x.startswith(kind) for x in got), got)

        print("\n-- Next and Previous move things - never a jump to the end")
        moved = pg.evaluate("""async () => {
          const f = KIT2D.figures[2], c = () => f.svg.querySelector('.k2-node-ring').closest('g').getAttribute('transform');
          f.goStep(0, true); const a = c(); f.next(); await new Promise(r => setTimeout(r, 120)); const mid = c();
          await new Promise(r => setTimeout(r, 1800)); const end = c(); f.prev(); await new Promise(r => setTimeout(r, 120));
          const back = c(); return [a, mid, end, back]; }""")
        check("the triangle's corner is part-way 120 ms after Next, and part-way back 120 ms after Previous",
              len(set(moved)) == 4, moved)
        resized = pg.evaluate("""async () => {
          const f = KIT2D.figures[2], c = () => f.svg.querySelector('.k2-node-ring').closest('g').getAttribute('transform');
          f.goStep(0, true); await new Promise(r => setTimeout(r, 100)); f.next(); await new Promise(r => setTimeout(r, 60));
          f.host.style.height = (f.host.offsetHeight - 40) + 'px'; f.resize(); const mid = c();
          await new Promise(r => setTimeout(r, 1800)); const end = c(); f.host.style.height = ''; return [mid, end]; }""")
        check("a resize mid-step (a step title wrapping) lets the step play on, never a jump to its end",
              resized[0] != resized[1], resized)
        pg.close()

        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto((KIT / "more.html").as_uri())
        pg.wait_for_timeout(900)
        print("\n-- a pipe joined to a pump and a tank starts at the pump's flange and ends at the tank's wall")
        ends = pg.evaluate("""() => { const f = KIT2D.figures.find(x => x.byId.U && x.byId.L && x.byId.T), u = f.byId.U.port, t = f.byId.T.port;
          const d = f.svg.querySelector('.k2-l-back path[stroke-linejoin]').getAttribute('d').match(/-?[0-9.]+/g).map(Number);
          return [Math.hypot(d[0] - u.x, d[1] - u.y), Math.hypot(d[d.length - 2] - t.x, d[d.length - 1] - t.y)]; }""")
        check("the pipe meets the pump's nozzle and the tank's inlet, not a point in the casing or on a corner", max(ends) < 1, ends)
        pg.close()
        b.close()
    print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
