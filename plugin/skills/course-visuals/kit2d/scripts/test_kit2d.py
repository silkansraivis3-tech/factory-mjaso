#!/usr/bin/env python3
"""test_kit2d.py - the 2D kit in a hidden browser: every figure of the three demo pages (demos.html, pm.html, more.html)
(and courses.html, gas-basic.html) walked step by step at 1280 x 800 and 1024 x 768, and KIT2D.audit clean at the end of each step - no words over words,
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

PAGES = ["demos.html", "pm.html", "more.html", "courses.html", "gas-basic.html"]
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

# every <text> and <tspan> of a figure shown small, as the deck's audit measures it: its own font size by the scale it is drawn at
SMALL = """() => { const h = document.createElement('div'); h.style.width = '403px'; h.style.height = '227px'; document.body.prepend(h);
  const f = KIT2D.mount(h, {size: [960, 540], parts: [{type: 'callout', at: [300, 200], text: 'Gas-dangerous', sub: 'open deck'},
    {type: 'node', x: 520, y: 300, w: 300, h: 120, text: 'Cargo tank', sub: 'Type C'},
    {type: 'chart', id: 'C', x: 80, y: 360, w: 300, h: 120, xaxis: {min: 0, max: 20, step: 10, label: 'Pressure', unit: 'bar'},
     yaxis: {min: 0, max: 2, step: 1}}]});
  f.resize(); f.frame(true, 0);
  const px = [], under = [];
  f.svg.querySelectorAll('text, tspan').forEach(t => { if (!t.textContent.trim()) return; const m = t.getScreenCTM();
    const v = parseFloat(getComputedStyle(t).fontSize) * Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)); px.push(v);
    if (v < 12.45) under.push([t.tagName, t.getAttribute('class'), t.textContent.trim().slice(0, 20), +v.toFixed(2)]); });
  h.remove(); return {px: px.length, under}; }"""

# a figure built in a hidden box, then shown with no observation delivered: a window resize lays it out, and the drawing
# check lays out one that never had any
LATE = """() => { const mk = () => { const h = document.createElement('div'); h.style.cssText = 'display:none;width:420px;height:240px';
    document.body.prepend(h); return [h, KIT2D.mount(h, {size: [960, 540], parts: [{type: 'callout', at: [240, 270], text: 'Integral', sub: 'part of the hull'},
      {type: 'callout', at: [700, 270], text: 'Membrane', sub: 'a thin layer'}]})]; };
  const [h, f] = mk(); h.style.display = 'block'; window.dispatchEvent(new Event('resize'));
  const up = +getComputedStyle(f.svg).getPropertyValue('--k2-up') > 1, placed = f.labels.every(L => L.off);
  h.remove();
  const [h2, f2] = mk(); h2.style.display = 'block';
  const res = AuditDrawing.page(), over = (res.findings || []).filter(x => x.check === 'text zone' && /over each other/.test(x.detail || ''));
  const placed2 = f2.labels.every(L => L.off); h2.remove();
  return {up, placed, placed2, over: over.map(x => x.part)}; }"""

# where the deck is: the slide, its stop, the figure's step, the lit line, the part shown, the why and the figure's height
STOP = """() => { const s = document.querySelector('.slide.active'), F = s.__fig, why = s.querySelector('.lt-why');
  const st = s.querySelector('.kit2d-stage');
  return {id: s.id, cur: [...s.querySelectorAll('[data-i].cur')].map(x => x.getAttribute('data-i')).join(','), part: s.getAttribute('data-part-at'),
    fig: F ? F.at() : null, last: s.hasAttribute('data-last'), why: !!(why && why.getClientRects().length),
    figH: st ? st.getBoundingClientRect().height : 0}; }"""


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

        pg = b.new_page(viewport={"width": 1280, "height": 800})
        pg.goto((KIT / "gas-basic.html").as_uri())
        pg.wait_for_timeout(900)
        print("\n-- words that change with the story, readouts in words, a zone a route crosses, a crowded time line")
        said = pg.evaluate("""() => { const f = KIT2D.figures.find(x => x.svg.querySelector('.k2-bubble') && x.spec.parts.some(q => q.type === 'events'));
          const t = () => Array.from(f.svg.querySelectorAll('text.k2-t-face')).map(n => n.textContent).join(' | ');
          f.goStep(1, true); f.frame(true, 0); const a = t(); f.goStep(2, true); f.frame(true, 0); return [a, t()]; }""")
        check("a person's {pick, of} line changes when the step does", said[0] != said[1] and "ESD done" in said[1], said)
        burn = pg.evaluate("""() => { const f = KIT2D.figures.find(x => x.byId && x.spec.parts.some(q => q.type === 'region'));
          f.goStep(5, true); const at = v => { f.setT('left', v, true); f.frame(true, 0); f.readouts();
            return [f.out.Z.hit, f.reads[1].b.textContent, KIT2D.audit(f).length]; };
          return [at(2), at(25)]; }""")
        check("air after a little methane passes the zone (No), after a lot it crosses it (Yes), audit clean both ways",
              burn[0][:2] == [0, "No"] and burn[1][:2] == [1, "Yes"] and burn[0][2] == 0 and burn[1][2] == 0, burn)
        crowd = pg.evaluate("""() => { const h = document.createElement('div'); h.style.height = '600px'; document.body.prepend(h);
          const f = KIT2D.mount(h, {size: [1000, 600], parts: [{type: 'events', x: 90, y: 300, w: 820, start: 0, end: 30, step: 5, tick: '{v} min',
            events: [{at: 2, label: 'Gas alarm', sub: 'at the manifold'}, {at: 3, label: 'ESD', sub: 'pumps stop, valves shut'},
                     {at: 4, label: 'Water spray', sub: 'knocks the gas down'}, {at: 5, label: 'Muster', sub: 'upwind, doors shut'},
                     {at: 6, label: 'Head count', sub: 'everyone there'}]}]});
          f.goStep(f.steps.length - 1, true); f.frame(true, 0); const out = KIT2D.audit(f); h.remove(); return out; }""")
        check("five events a minute apart: each takes a free side or lane, no words on each other", crowd == [], crowd)

        print("\n-- every word at least 12.5 px on screen, a label's own <text> too (M01 s03, s15, s19: 11.5-12 px at 1024 x 768)")
        small = pg.evaluate(SMALL)
        check("a figure shown at 0.42 of its size: no <text> or <tspan> drawn under 12.5 px", small["px"] and not small["under"], small)
        pg.close()

        print("\n-- a page that draws no frames (a hidden browser's checks): the figure is laid out all the same")
        pg = b.new_page(viewport={"width": 1024, "height": 768})
        pg.add_init_script("window.ResizeObserver = function () { this.observe = function () {}; this.disconnect = function () {}; };")
        pg.goto((KIT / "demos.html").as_uri())
        pg.wait_for_timeout(600)
        pg.add_script_tag(path=str(SKILLS / "course-module-ux" / "measure" / "scripts" / "audit_drawing.js"))
        late = pg.evaluate(LATE)
        check("a window resize lays out a figure first built in a hidden box: its type grown, its labels placed",
              late["up"] and late["placed"], late)
        check("the drawing check lays a 2D-kit figure out before it judges its labels: none on top of another (M01 s19)",
              late["placed2"] and not late["over"], late)
        pg.close()

        print("\n-- in a deck: the steps light the slide's lines from 1, the part that holds the line shows, the answer comes last")
        pg = b.new_page(viewport={"width": 1280, "height": 800})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((HERE / "fixtures" / "deck_kit2d.html").as_uri())
        pg.wait_for_timeout(600)
        pg.click("#startBtn")
        walk = []
        for _ in range(14):                                 # to the last stop of s4
            if pg.locator("#btnNext").is_disabled():
                break
            pg.click("#btnNext")
            pg.wait_for_timeout(250)
            walk.append(pg.evaluate(STOP))
        by = lambda sid: [x for x in walk if x["id"] == sid]
        s2 = [(x["cur"], x["part"], x["fig"]) for x in by("s2")]
        check("words in two parts: Next lights lines 1-3 on part 1, then line 4 turns to part 2 with the figure's step 1, line 5 step 2",
              s2 == [("", "0", 0), ("1", "0", 0), ("2", "0", 0), ("3", "0", 0), ("4", "1", 1), ("5", "1", 2)], s2)
        s3 = [(x["cur"], x["fig"], x["last"]) for x in by("s3")]
        check("a scenario: the figure's steps light the situation's lines first, the answer shows on the last Next",
              s3 == [("", 0, False), ("1", 1, False), ("2", 2, False), ("2", 2, True)], s3)
        s4 = [(x["cur"], x["fig"], x["why"], x["figH"] > 120) for x in by("s4")]
        check("true or false: the why opens first - its lines are the ones the steps light - under the figure, never over it",
              s4 == [("", 0, False, True), ("", 0, True, True), ("1", 1, True, True), ("2", 2, True, True)], s4)
        back = []
        for _ in range(3):
            if pg.locator("#btnPrev").is_disabled():
                break
            pg.click("#btnPrev")
            pg.wait_for_timeout(250)
            back.append(pg.evaluate(STOP))
        back = [(x["id"], x["fig"], x["why"]) for x in back]
        check("... and Back the other way round: the steps after the why, then the why closes",
              back == [("s4", 1, True), ("s4", 0, True), ("s4", 0, False)], back)
        check("in a deck: no page error", not errs, errs)
        pg.close()
        b.close()
    print("\n%d failed" % len(FAILS) if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
