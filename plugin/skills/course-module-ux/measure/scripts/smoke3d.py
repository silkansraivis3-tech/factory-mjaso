# -*- coding: utf-8 -*-
"""smoke3d.py - a deck's 3D scene loaded alone in a hidden browser, in seconds: does it load, draw and stay quiet? (2.63.0)

    python smoke3d.py <deck.html> [--slide s05[,s09]] [--limit 15]

WHY (IGF M01 v262, runs 6-8): a scene that stalled the hidden browser was found by the drawing check of a whole build,
which waited its 600 s three times - about 25 minutes before anyone knew the scene was the cause. Run this after every
edit of a scene file (m01_ship3d.js ...) and before build_module.py: one slide, one page, a short limit.

WHAT IT DOES
  The deck is copied beside itself (presentation\\_smoke3d_<pid>.html, removed afterwards) with only each 3D slide and
  the slide before it (the build-ahead hook - compile GUIDE 2b), and perf3d.mjs drives it: Start, Next to the slide,
  wait for the scene's first frame (window.__scene3d.firstFrameT), at the computer's own speed - this is a smoke test, the
  speed budget stays perf3d.mjs's at its 4x throttle. A 3D slide is one with a <canvas>, [data-3d], [data-scene] or,
  as the compiler writes it, data-visual="model_3d".
  Each slide: OK with its first frame in ms - or FAIL: it never drew within the limit, the page threw an error, it does
  not report window.__scene3d, or the browser did not finish at all (a scene that hangs is ended with its browser).
Exit 0 every scene drew with no page error, 1 a scene failed, 2 bad input (no deck, no 3D slide, no Node).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "course-factory", "scripts"))
import browser_slots  # noqa: E402  - a scene that hangs is ended with every browser it started

PERF = os.path.join(HERE, "perf3d.mjs")
SLIDE = re.compile(r'<section\b[^>]*\bclass="[^"]*\bslide\b[^"]*"[^>]*>.*?</section>', re.S)
# a compiled deck marks its 3D slide data-visual="model_3d" - the scene makes its <canvas> itself (IGF M01 s05); a 3D-kit
# scene (course-visuals/kit3d) is a [data-kit3d] stage that kit3d.js fills
IS_3D = re.compile(r'<canvas\b|\bdata-3d\b|\bdata-scene\b|\bdata-kit3d\b|\bdata-visual="model_3d"')


def sid_of(sec):
    m = re.search(r'\bid="([^"]+)"', sec[:sec.find(">") + 1])
    return m.group(1) if m else ""


def alone(page, ids):
    """the deck with only the asked 3D slides and the slide before each (its build-ahead hook)"""
    secs = list(SLIDE.finditer(page))
    keep = set()
    for i, m in enumerate(secs):
        if sid_of(m.group(0)) in ids:
            keep.add(i)
            if i:
                keep.add(i - 1)
    out, last = [], 0
    for i, m in enumerate(secs):
        out.append(page[last:m.start()])
        if i in keep:
            out.append(m.group(0))
        last = m.end()
    return "".join(out) + page[last:]


def full_screen(sid, fs):
    """2.63.2 (Aleksis 2026-10-22: the 3D scenes sit small; labels should select their part) - ([problems], what it saw)
    from perf3d.mjs --fs3d: the scene's Full screen button there and 44 px, the box filling the window and still drawing,
    Next kept off, the button leaving it; a label a button that selects its part and lets it go"""
    bad = []
    if not fs.get("button"):
        return (["%s: no Full screen button on the scene (gb_deck.js 2.63.2 adds it to a 3D slide's box)" % sid]
                if fs.get("deck") else []), ("" if fs.get("deck") else "not a factory deck - full screen not checked")
    b, on, lb = fs["button"], fs.get("on") or {}, fs.get("label")
    if b.get("w", 0) < 44 or b.get("h", 0) < 44:
        bad.append("%s: the Full screen button is %sx%s px - a tap needs 44" % (sid, b.get("w"), b.get("h")))
    if b.get("over"):
        bad.append("%s: the Full screen button covers the scene's words: %s (IGF M04 s10 \"1 Cold methane\")"
                   % (sid, "; ".join(b["over"])))
    if not on:
        bad.append("%s: pressing Full screen did not fill the window with the scene" % sid)
    elif (fs.get("drew") or 0) <= 0 and (on.get("buffer") or [0])[0] < 0.8 * (on.get("w") or 1) * (on.get("dpr") or 1):
        # a scene that draws only when something changes (IGF M01 s05) has no new frames: its renderer's own buffer grown
        # to the box is the proof it redrew at the new size (the canvas's css size grows by itself)
        bad.append("%s: full screen, the scene stopped drawing (its renderer does not follow the box - listen to "
                   "window resize / gb3d-resize)" % sid)
    if on and fs.get("keptSlide") is False:
        bad.append("%s: Next turned the slide while the scene was full screen" % sid)
    if on and not fs.get("left"):
        bad.append("%s: the button did not leave full screen" % sid)
    if lb and not (lb.get("role") == "button" and lb.get("selected") and lb.get("released")):
        bad.append("%s: a tap on the label \"%s\" did not select its part and let it go (data-3d-part + GB3D.wire, "
                   "compile GUIDE 2b)" % (sid, lb.get("part")))
    seen = "full screen %sx%s px, drawing (%s frames)%s; label %s" % (
        on.get("w"), on.get("h"), fs.get("drew"), "" if on.get("real") else " (window box)",
        ("\"%s\" selects its part" % lb["part"]) if lb and not bad else "none to tap" if not lb else "-")
    return bad, seen


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--slide", default="", help="slide ids, comma-separated (default: every 3D slide)")
    ap.add_argument("--limit", type=float, default=15, help="seconds a scene has to draw its first frame (default 15)")
    o = ap.parse_args(argv)
    if not os.path.isfile(o.deck):
        print("Stopped - there is no deck at %s" % o.deck)
        return 2
    node = shutil.which("node")
    if not node:
        print("Stopped - Node.js is not on this computer (perf3d.mjs needs it)")
        return 2
    page = io.open(o.deck, encoding="utf-8").read()
    found = [sid_of(m.group(0)) for m in SLIDE.finditer(page) if IS_3D.search(m.group(0))]
    ids = [x.strip() for x in o.slide.split(",") if x.strip()] or found
    if not ids:
        print("Stopped - the deck has no 3D slide (a <canvas>, [data-3d], [data-scene] or [data-kit3d])")
        return 2
    unknown = [x for x in ids if x not in {sid_of(m.group(0)) for m in SLIDE.finditer(page)}]
    if unknown:
        print("Stopped - the deck has no slide %s" % ", ".join(unknown))
        return 2
    tmp = os.path.join(os.path.dirname(os.path.abspath(o.deck)), "_smoke3d_%d.html" % os.getpid())
    io.open(tmp, "w", encoding="utf-8", newline="\n").write(alone(page, set(ids)))
    ms = int(o.limit * 1000)
    cmd = [node, PERF, tmp, "--slides=" + ",".join(ids), "--no-cold", "--no-fps", "--throttle=1", "--dwell=300",
           "--wait-ms=%d" % ms, "--budget-ms=%d" % ms, "--json", "--fs3d"]
    t0, rep, said = time.time(), None, ""
    try:
        p = browser_slots.run_tree(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=o.limit * len(ids) + 30)
        said = (p.stdout or "") + (p.stderr or "")
        try:
            rep = json.loads(p.stdout[p.stdout.index("{"):p.stdout.rindex("}") + 1])
        except ValueError:
            rep = None
    except subprocess.TimeoutExpired:
        said = "timed out"
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    secs = time.time() - t0
    bad = []
    if rep is None:
        why = ("the browser did not finish in %.0f s - the scene hangs the page (an endless loop, a wait that never ends); "
               "it was ended" % (o.limit * len(ids) + 30)) if said == "timed out" else \
              "no answer from perf3d.mjs: %s" % " ".join(said.split())[-300:]
        print("FAIL 3D smoke test (%.0f s): %s" % (secs, why))
        return 1
    errs = rep.get("consoleErrors") or []
    for s in rep.get("slides") or []:
        w = s.get("warm") or {}
        ff = w.get("firstFrameMs")
        if ff is None:
            bad.append("%s: no first frame within %.0f s%s" % (s.get("id"), o.limit, (" - " + w["error"]) if w.get("error") else ""))
        else:
            print("  %s: first frame %.0f ms%s" % (s.get("id"), ff, " (built ahead on the slide before)" if w.get("preparedAhead") else ""))
            fs = w.get("fs3d") or {}
            said_fs = full_screen(s.get("id"), fs)
            bad += said_fs[0]
            if said_fs[1]:
                print("    " + said_fs[1])
    if rep.get("error"):
        bad.append(str(rep["error"]))
    bad += ["page error: %s" % e for e in errs]
    if bad:
        print("FAIL 3D smoke test (%.0f s):\n%s" % (secs, "\n".join("  - " + x for x in bad)))
        return 1
    print("PASS 3D smoke test (%.0f s): %s - every scene drew, no page error" % (secs, ", ".join(ids)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
