# -*- coding: utf-8 -*-
"""test_smoke3d - smoke3d.py loads a deck's 3D scene alone and says in seconds whether it drew (2.63.0).

    python test_smoke3d.py

On fixtures/deck_3d_perf.html (a fake scene on a 2D canvas) and three broken copies of it: a scene that draws passes
in seconds; one that throws, one that never draws and one that hangs the page each fail - the hanging one ended by the
limit, not after the drawing check's 600 s (IGF M01 v262 runs 6-8, ~25 min). The temp page is removed afterwards.
Skips (exit 0) without Node or Chrome.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "smoke3d.py")
DECK = os.path.join(HERE, "fixtures", "deck_3d_perf.html")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(deck, *args):
    t = time.time()
    p = subprocess.run([sys.executable, TOOL, deck] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=180)
    return p.returncode, p.stdout + p.stderr, time.time() - t


def variant(tmp, name, delay, extra=""):
    text = io.open(DECK, encoding="utf-8").read()
    text = text.replace('id="s-fast" data-delay="0"', 'id="s-fast" data-delay="%s"' % delay)
    text = text.replace("function startScene(cv, delay) {", "function startScene(cv, delay) {" + extra, 1)
    d = os.path.join(tmp, name)
    os.makedirs(d)
    p = os.path.join(d, "index.html")
    io.open(p, "w", encoding="utf-8").write(text)
    return p


FS_DECK = os.path.join(HERE, "fixtures", "deck_3d_fs.html")


def full_screen_part():
    """2.63.2 (Aleksis 2026-10-22: the 3D scenes sit small; a label should select its object too) - on the factory's deck
    engine a 3D scene has a 44 px Full screen button; pressed, the scene's box fills the window and keeps drawing, Next
    stays off, the button leaves it; a label tap selects its part and a second lets it go. Variants that break one each"""
    print("\n-- 2.63.2: a 3D scene full screen, its labels select their parts")
    code, out, secs = run(FS_DECK, "--limit", "8")
    check("the fixture scene on gb_deck.js: Full screen fills the window and keeps drawing, a label selects its part (%.1f s)" % secs,
          code == 0 and "full screen 1280x800 px, drawing" in out and "label \"tank\" selects its part" in out, out)
    base = io.open(FS_DECK, encoding="utf-8").read()
    for name, old, new, said in (
            ("still", "var FIXTURE_FOLLOWS = true", "var FIXTURE_FOLLOWS = false", "full screen, the scene stopped drawing"),
            ("unwired", "FIXTURE_WIRES = true", "FIXTURE_WIRES = false", "a tap on the label \"tank\" did not select its part"),
            ("nobutton", '<script src="../../../assets/gb_deck.js"></script>',
             '<script src="../../../assets/gb_deck.js"></script><script>GBDeck.init = (function (f) { return function (o) { var r = f(o);'
             ' [].forEach.call(document.querySelectorAll(".gb-fs3d-btn"), function (b) { b.remove(); }); return r; }; })(GBDeck.init);</script>',
             "no Full screen button on the scene")):
        p = os.path.join(HERE, "fixtures", "_fs_%s_%d.html" % (name, os.getpid()))
        io.open(p, "w", encoding="utf-8").write(base.replace(old, new, 1))
        try:
            code, out, secs = run(p, "--limit", "8")
        finally:
            os.remove(p)
        check("%s: FAIL - %s" % (name, said), code == 1 and said in out, out)
    p = os.path.join(HERE, "fixtures", "_fs_corner_%d.html" % os.getpid())
    io.open(p, "w", encoding="utf-8").write(base.replace('style="left:30%;top:16%"', 'style="right:4px;top:4px"', 1))
    try:
        code, out, secs = run(p, "--limit", "8")
    finally:
        os.remove(p)
    check("a label in the top right corner: the button goes to another corner, covering no word (IGF M04 s10)",
          code == 0 and "covers the scene's words" not in out, out)


def main():
    if not shutil.which("node"):
        print("skipped: no Node")
        return 0
    tmp = tempfile.mkdtemp(prefix="smoke3d_")
    try:
        good = variant(tmp, "good", 0)
        code, out, secs = run(good, "--slide", "s-fast", "--limit", "5")
        if "no Chrome" in out or "Chrome" in out and code == 2:
            print("skipped: no Chrome")
            return 0
        check("a scene that draws passes, its first frame named, in seconds (%.1f s)" % secs,
              code == 0 and "s-fast: first frame" in out and "PASS 3D smoke test" in out and secs < 30, out)
        check("... the page made beside the deck is gone again", os.listdir(os.path.dirname(good)) == ["index.html"], os.listdir(os.path.dirname(good)))
        code, out, secs = run(good, "--limit", "5")
        check("every 3D slide when none is named - the two canvases, not the title slide (s-slow draws at 2 s, inside 5)",
              code == 0 and "s-fast: first frame" in out and "s-slow: first frame" in out and "s1:" not in out, out)
        bad = variant(tmp, "throws", -1, " if (delay < 0) { throw new Error('the scene file is broken'); }")
        code, out, secs = run(bad, "--slide", "s-fast", "--limit", "4")
        check("a scene that throws fails, with the page's error", code == 1 and "the scene file is broken" in out, out)
        never = variant(tmp, "never", 999999)
        code, out, secs = run(never, "--slide", "s-fast", "--limit", "3")
        check("a scene that never draws fails within its limit (%.1f s)" % secs, code == 1 and "no first frame within 3 s" in out and secs < 40, out)
        hang = variant(tmp, "hang", 7, " if (delay === 7) { var t = Date.now(); while (Date.now() - t < 600000) {} }")
        code, out, secs = run(hang, "--slide", "s-fast", "--limit", "3")
        check("a scene that hangs the page is ended by the limit, not after 600 s (%.1f s)" % secs,
              code == 1 and "FAIL 3D smoke test" in out and secs < 90, out)
        check("a deck with no 3D slide, or a slide it has not, stops (exit 2)",
              run(good, "--slide", "s9")[0] == 2)
        full_screen_part()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
