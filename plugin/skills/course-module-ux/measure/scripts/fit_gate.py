#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fit_gate - the deck walked as the instructor walks it, and every step measured: Start, then Next to the end, through
every figure step and every question's answer. A word the trainee cannot see, or a picture shown only in part, fails it.

    python fit_gate.py <deck index.html | module folder> [--viewport 1280x800 ...] [--min-shown 0.8] [--json out.json]

run_audits.py measures each slide as it first opens; a slide whose last Next shows more (the answer to the room's
question, the last line of a list) was never measured there - GAS BASIC's 37 answers were cut at the tablet's size and
every audit passed. This gate presses Next.

Fails on, at each step of each slide:
  cut     words cut off by the box that holds them, or by the screen (more than 8 px)
  spill   a card, a line or a picture past the edge of the slide
  picture shown in part - less than --min-shown of it (0.8) - or stretched, or its box cut; a picture inside
          data-fit="cover" is a backdrop and may be cropped; a picture that does not load
Sizes: 1280x800 (the tablets), 1024x768 and 1280x720 unless --viewport is given.

It drives the Chrome or Edge already on the computer through Playwright (python -m pip install playwright - no browser
download). Exit 0 every step fits, 1 something does not (each slide, step and size named), 2 nothing could be measured.
The deck is never changed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_audit_drawing import browser  # noqa: E402  - the one place that finds Chrome or Edge
sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
import browser_slots  # noqa: E402  - one pool of hidden browsers for the whole computer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SIZES = ("1280x800", "1024x768", "1280x720")
MAX_STEPS = 3000
PROBE = (HERE / "fit_probe.js").read_text(encoding="utf-8")
SETTLE = """() => { for (const a of document.getAnimations()) { try { const t = a.effect && a.effect.getComputedTiming();
  if (t && t.endTime !== Infinity) a.finish(); } catch (e) {} } }"""


def find_deck(arg):
    p = Path(arg)
    for d in (p, p / "presentation" / "index.html", p / "index.html"):
        if d.is_file():
            return d.resolve()
    return None


# the 2D kit's own check (kit2d.js KIT2D.audit) on the figures of the slide in front: words over words, words or shapes cut
# at the edge, a label on a line - measured once the figure has stopped moving
KIT2D = """(id) => { const s = document.getElementById(id); if (!window.KIT2D || !s) { return null; }
  const fs = KIT2D.figures.filter(f => s.contains(f.host)); if (!fs.length) { return null; }
  return { idle: fs.every(f => f.idle()), found: [].concat.apply([], fs.map(f => KIT2D.audit(f))) }; }"""


def walk(page, deck, min_shown):
    """[(slide id, step on that slide, kind, what)] for one deck at the page's size"""
    found, at = [], {}
    page.goto(deck.as_uri())
    page.wait_for_timeout(600)
    if page.locator("#startBtn").count():
        page.click("#startBtn")
    for _ in range(MAX_STEPS):
        page.wait_for_timeout(450)
        page.evaluate(SETTLE)
        page.wait_for_timeout(120)
        r = page.evaluate("() => window.FitProbe()")
        if r and any(r[k] for k in ("cut", "spill")):
            # a step still moving (a card opening after its delay) is measured again once it has settled
            page.wait_for_timeout(1500)
            page.evaluate(SETTLE)
            r = page.evaluate("() => window.FitProbe()")
        if r:
            step = at[r["id"]] = at.get(r["id"], 0) + 1
            for k in ("cut", "spill"):
                for f in r[k]:
                    found.append((r["id"], step, k, "%s px %s: \"%s\"%s" % (f["px"], f["el"], f["words"],
                                                                         " (cut by %s)" % f["by"] if f.get("by") else "")))
            for f in r["pic"]:
                if f.get("broken"):
                    found.append((r["id"], step, "picture", "%s does not load" % f["src"]))
                elif not f["backdrop"] and f["part"] < min_shown:
                    found.append((r["id"], step, "picture", "%s shows %d %% of itself (%s picture in a %s box, %s)"
                                  % (f["src"], round(f["part"] * 100), f["natural"], f["box"], f["fit"])))
                elif f["stretch"] > 1.1:
                    found.append((r["id"], step, "picture", "%s stretched x%.2f" % (f["src"], f["stretch"])))
                elif f["seen"] < 0.9:
                    found.append((r["id"], step, "picture", "%s: only %d %% of its box is seen (cut by %s)"
                                  % (f["src"], round(f["seen"] * 100), f["by"])))
            k2 = page.evaluate(KIT2D, r["id"])
            for _ in range(12):                       # a 2D-kit figure still moving is measured once it has settled
                if not k2 or k2["idle"]:
                    break
                page.wait_for_timeout(250)
                k2 = page.evaluate(KIT2D, r["id"])
            for what in (k2 or {}).get("found", []):
                found.append((r["id"], step, "figure", what))
        nxt = page.locator("#btnNext")
        if not nxt.count() or nxt.is_disabled():
            break
        nxt.click()
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--viewport", action="append", default=[])
    ap.add_argument("--min-shown", type=float, default=0.8)
    ap.add_argument("--json")
    o = ap.parse_args(argv)
    deck = find_deck(o.deck)
    if not deck:
        print("fit_gate: no deck at %s (give the deck's index.html, or the module folder)" % o.deck)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("fit_gate: Playwright is not installed - python -m pip install playwright (it drives the Chrome or Edge "
              "already here, nothing else to download)")
        return 2
    exe = browser()
    if not exe:
        print("fit_gate: no Chrome or Edge found - nothing measured")
        return 2
    sizes = []
    for v in o.viewport or SIZES:
        try:
            w, h = (int(x) for x in v.lower().split("x"))
        except ValueError:
            print("fit_gate: --viewport wants WxH, like 1280x800 - not %r" % v)
            return 2
        sizes.append((w, h))
    res = {}
    try:
        with browser_slots.slot(), sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=exe, headless=True, args=["--allow-file-access-from-files"])
            for w, h in sizes:
                page = b.new_page(viewport={"width": w, "height": h})
                page.add_init_script(PROBE)
                res["%dx%d" % (w, h)] = walk(page, deck, o.min_shown)
                page.close()
            b.close()
    except Exception as err:                                # the browser did not start or the page did not answer
        print("fit_gate: could not measure %s - %s" % (deck, str(err).splitlines()[0] if str(err) else type(err).__name__))
        return 2
    if o.json:
        Path(o.json).write_text(json.dumps({k: [list(x) for x in v] for k, v in res.items()}, indent=1), encoding="utf-8")
    bad = 0
    for size, found in res.items():
        slides = {}
        for sid, step, kind, what in found:
            slides.setdefault(sid, {}).setdefault((kind, what), []).append(step)
        bad += len(slides)
        print("%-9s fit  %s" % (size, "PASS" if not slides else "FAIL %d slide(s)" % len(slides)))
        for sid, kinds in slides.items():
            for (kind, what), steps in list(kinds.items())[:4]:
                print("  %s step %s  %-7s %s" % (sid, ",".join(str(x) for x in sorted(set(steps))[:4]), kind, what))
            if len(kinds) > 4:
                print("  %s  ... and %d more" % (sid, len(kinds) - 4))
    print("fit_gate: %s" % ("every step fits" if not bad else "words or pictures the trainee cannot fully see - fix the "
                                                             "slides named above"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
