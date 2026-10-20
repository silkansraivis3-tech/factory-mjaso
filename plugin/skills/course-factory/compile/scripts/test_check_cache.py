# -*- coding: utf-8 -*-
"""test_check_cache - a slide or task page judged clean is skipped only while nothing it loads has changed (2.57.0).

The guard against a loosened check: on a small module (a four-slide deck and a task page, the factory's own design
files in assets\\), in a real hidden browser -
  * the first run judges every slide and page; a run with nothing changed judges none and still passes;
  * a defect planted on ONE slide re-checks that slide only - and the defect IS found, naming the slide;
  * a failing slide is never recorded clean: the next run, unchanged, judges it again and finds it again;
  * a picture a slide shows, changed, re-checks that slide; a design file in assets\\ changed re-checks every slide;
  * --full / full=True judges everything; a defect planted on the task page is found the same way;
  * the audits (run_audits.py --cache) do the same per slide and viewport: a slide given text too small is measured
    again and FAILS, the unchanged ones are not measured, and its failure is never recorded clean.
Skips, and says so, when no Chrome or Edge is installed.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
import drawing_check  # noqa: E402
import check_cache  # noqa: E402  - on the path drawing_check put it on
sys.path.insert(0, os.path.join(SKILLS, "course-module-ux", "measure", "scripts"))
import run_audits  # noqa: E402

TEMPLATES = os.path.join(SKILLS, "course-module-ui", "templates")
UX = os.path.join(SKILLS, "course-module-ux", "assets")
FAILS = []

SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>check cache fixture</title>
<link rel="stylesheet" href="../assets/gb_tokens.css"><link rel="stylesheet" href="../assets/gb_shell.css">
<link rel="stylesheet" href="../assets/gb_compose.css"><link rel="stylesheet" href="../assets/extra.css">
</head><body>
<div id="landing"><button id="startBtn" type="button">Start</button></div>
<div id="progress"></div><div id="blockTag"></div>
<div id="overview"><button class="fbtn" id="ovClose" type="button">Close</button><div class="ov-grid" id="ovGrid"></div></div>
<div id="cue"></div>
<div id="chrome"><button class="cbtn" id="btnPrev" type="button" aria-label="Back">&lt;</button>
<span id="counter"><b>1</b> / 1</span><button class="cbtn" id="btnNext" type="button" aria-label="Next">&gt;</button></div>
<main id="stage">
%s
</main>
<script src="../assets/gb_deck.js"></script>
<script>GBDeck.init({ hooks: {} });</script>
</body></html>
"""
SLIDE = """<section class="slide" id="s%(n)02d" data-block="FX · %(n)d" data-title="Slide %(n)d">
  <div class="slide-kind"><b>Theory</b> · FX · %(n)d / 4</div>
  <h2>The fuel system, part %(n)d</h2>
  <div class="slide-body two-col">
    <div class="copy">
      <p class="lead">The gas valve unit stands between the bunker line and the engine.</p>
      <ul class="support"><li>It shuts the gas off when a leak is found.</li><li>It vents the line to a safe place.</li>
      <li>It is tested before every start.</li></ul>
    </div>
    <div class="fill fig">%(fig)s</div>
  </div>
</section>"""
DRAWING = ('<svg viewBox="0 0 400 260" width="400" height="260"><rect x="4" y="4" width="392" height="252" fill="#c9d6ea" '
           'stroke="#0A2463" stroke-width="2"/>' + "".join('<rect x="%d" y="%d" width="64" height="64" fill="#7f9cc4" stroke="#0A2463" '
                                                           'stroke-width="2"/>' % (x, y) for x in (14, 90, 166, 242, 318)
                                                           for y in (14, 96, 178))
           + '%s</svg>')
CUT = '<circle cx="392" cy="130" r="40" fill="#fff" stroke="#0A2463" stroke-width="2"/>'       # a tank cut off at the edge
TASK = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>task</title>
<link rel="stylesheet" href="../assets/extra.css"></head><body>
<div class="scr on" data-script="q01"><p>Tap the gas valve unit.</p>%s</div>
</body></html>"""


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (str(detail)[:900],)))
    if not ok:
        FAILS.append(what)


def module(root):
    mdir = os.path.join(root, "module01")
    for d in ("presentation", "assets/img", "tasks"):
        os.makedirs(os.path.join(mdir, d), exist_ok=True)
    for f in ("gb_tokens.css", "gb_shell.css", "gb_compose.css"):
        shutil.copy(os.path.join(TEMPLATES, f), os.path.join(mdir, "assets", f))
    if os.path.isdir(os.path.join(TEMPLATES, "fonts")):
        shutil.copytree(os.path.join(TEMPLATES, "fonts"), os.path.join(mdir, "assets", "fonts"))
    shutil.copy(os.path.join(UX, "gb_deck.js"), os.path.join(mdir, "assets", "gb_deck.js"))
    write(os.path.join(mdir, "assets", "extra.css"), "/* fixture */\n")
    write(os.path.join(mdir, "assets", "img", "pump.svg"), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                                                          '<rect width="10" height="10" fill="#9ab"/></svg>')
    deck(mdir, {})
    write(os.path.join(mdir, "tasks", "t1.html"), TASK % (DRAWING % ""))
    return mdir


def deck(mdir, figs):
    """the deck; figs = {slide number: what its figure holds besides the clean drawing}"""
    slides = []
    for n in range(1, 5):
        fig = DRAWING % figs.get(n, "")
        if n == 3:
            fig = '<img src="../assets/img/pump.svg" alt="pump" style="width:120px">' + fig
        slides.append(SLIDE % {"n": n, "fig": fig})
    write(os.path.join(mdir, "presentation", "index.html"), SHELL % "\n".join(slides))


def write(path, text):
    io.open(path, "w", encoding="utf-8").write(text)


def cached(path):
    try:
        return json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def drawing_part(root):
    mdir = module(root)
    deck_p, task_p = os.path.join(mdir, "presentation", "index.html"), os.path.join(mdir, "tasks", "t1.html")
    cache = os.path.join(root, "_build", "M01_drawing_clean.json")

    def run(full=False):
        probs, note = drawing_check.check([deck_p, task_p], root=mdir, cache=cache, full=full)
        return probs, note, dict(drawing_check.LAST)

    probs, note, last = run()
    check("first run: every slide and the task page judged, all clean",
          not note and not probs and last == {"slides": (4, 4), "pages": (1, 1)}, (note, probs, last))
    check("... and all five recorded clean", len(cached(cache)) == 5, cached(cache))
    probs, note, last = run()
    check("nothing changed: nothing judged again, still clean", not probs and last == {"slides": (0, 4), "pages": (0, 1)},
          (probs, last))
    deck(mdir, {2: CUT})
    probs, note, last = run()
    check("a tank cut off on slide 2: only slide 2 judged again", last["slides"] == (1, 4), last)
    check("... and the cut-off tank IS found, on slide 2", len(probs) >= 1 and all(re.search(r"slide 2 \(s02\)", p) for p in probs)
          and any("cut off" in p for p in probs), probs)
    check("... and slide 2 is no longer recorded clean, the other three still are",
          "presentation/index.html#1" not in cached(cache) and len(cached(cache)) == 4, cached(cache))
    probs, note, last = run()
    check("run again unchanged: the failing slide 2 is judged again and found again (a failure is never cached)",
          last["slides"] == (1, 4) and any("slide 2 (s02)" in p and "cut off" in p for p in probs), (last, probs))
    write(os.path.join(mdir, "assets", "img", "pump.svg"), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                                                           '<circle cx="5" cy="5" r="5" fill="#9ab"/></svg>')
    probs, note, last = run()
    check("the picture slide 3 shows changed: slides 2 and 3 judged", last["slides"] == (2, 4), last)
    write(os.path.join(mdir, "assets", "extra.css"), "/* fixture, edited */\n")
    probs, note, last = run()
    check("a design file in assets\\ changed: every slide and the task page judged", last == {"slides": (4, 4), "pages": (1, 1)}, last)
    deck(mdir, {})
    run()
    probs, note, last = run(full=True)
    check("full=True (build_module.py --full): everything judged though nothing changed",
          not probs and last == {"slides": (4, 4), "pages": (1, 1)}, (probs, last))
    write(task_p, TASK % (DRAWING % CUT))
    probs, note, last = run()
    check("a tank cut off on the task page: only the page judged, and the defect IS found",
          last == {"slides": (0, 4), "pages": (1, 1)} and any("tasks/t1.html" in p and "cut off" in p for p in probs), (last, probs))
    # a deck the browser counts differently from the fingerprints (a slide nobody split): judged whole, nothing cached
    text = io.open(deck_p, encoding="utf-8").read()
    write(deck_p, text.replace('<section class="slide" id="s04"', '<div class="slide" style="display:none"></div>'
                                                                   '<section class="slide" id="s04"', 1))
    real, before = check_cache.SLIDE_TAG, cached(cache)
    try:
        drawing_check.SLIDE_TAG = check_cache.SLIDE_TAG = re.compile(r"<section\b[^>]*\bclass=\"slide\b", re.I)
        probs, note, last = run(full=True)
    finally:
        drawing_check.SLIDE_TAG = check_cache.SLIDE_TAG = real
    check("a deck the browser counts differently is judged whole (no finding lost, none cached)",
          not note and all("could not finish" not in p for p in probs)
          and any("tasks/t1.html" in p and "cut off" in p for p in probs) and cached(cache) == before, (note, probs))


def audits_part(root):
    mdir = module(os.path.join(root, "a"))
    deck_p = os.path.join(mdir, "presentation", "index.html")
    cache = os.path.join(root, "a", "_build", "M01_audits_clean.json")

    def cli(*args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_audits.main([deck_p, "--cache", cache] + list(args))
        out = buf.getvalue()
        m = re.search(r"measured (\d+) of (\d+) slides at 1280x800", out)
        return code, out, (int(m.group(1)), int(m.group(2))) if m else None

    code, out, n = cli()
    check("audits, first run: every slide measured, every probe passes", code == 0 and n == (4, 4), out)
    code, out, n = cli()
    check("audits, nothing changed: no slide measured, still a pass", code == 0 and n == (0, 4) and "unchanged" in out, out)
    deck(mdir, {})
    text = io.open(deck_p, encoding="utf-8").read()
    write(deck_p, text.replace('<p class="lead">The gas valve unit', '<p class="lead" style="font-size:9px">The gas valve unit', 1))
    code, out, n = cli()
    check("text too small on slide 1: only slide 1 measured, and the audit FAILS naming it",
          code == 1 and n == (1, 4) and re.search(r"slide 1 \(s01\): small text", out), out)
    code, out, n = cli()
    check("run again unchanged: slide 1 measured again and fails again (a failure is never cached)",
          code == 1 and n == (1, 4) and "slide 1 (s01)" in out, out)
    code, out, n = cli("--full")
    check("--full measures every slide", code == 1 and n == (4, 4), out)


def main():
    exe = drawing_check.find_browser()
    if not exe:
        print("skip  no Chrome or Edge found - the cache was not tried in a browser")
        return 0
    root = tempfile.mkdtemp(prefix="cf_cache_test_")
    try:
        drawing_part(root)
        audits_part(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("%d failure(s)" % len(FAILS) if FAILS else "Every check-cache check passed.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
