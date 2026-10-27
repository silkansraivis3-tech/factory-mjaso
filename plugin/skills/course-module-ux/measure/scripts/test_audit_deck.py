# -*- coding: utf-8 -*-
"""test_audit_deck - audit_deck.js measures a slide's END state, not a frame of its entrance animation (finding 5).

    python test_audit_deck.py

Opens measure/fixtures/deck_rise_in.html in headless Chrome or Edge: a recap whose content rises in from 23 px low, its
animation paused (what a hidden / preview pane does). Pinned:
  * with finishAnimations off the audit reports the 23 px "scroll" (the false finding this exists to remove);
  * with it on (the default) the audit finishes the animation first and reports none;
  * an endless animation on the slide does not stop the audit;
  * (deck_mark.html) a line a stepping figure marks .cur must look selected: the old blue/amber boxes fail, the
    shipped gb_compose.css passes (IGF M05, 2026-10-19);
  * (deck_call_dark.html) a conclusion on a dark stepping slide passes contrast: its bold term takes the callout's
    colour, and the mark check restores the last line with no fade left running (M01 benchmark run 4);
  * (deck_svg_floor.html) drawing words 0.03 px under the floor pass, as in audit_drawing.js (2.72.7, one rule).
Skips, and says so, when no Chrome or Edge is installed.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_audit_drawing import browser, browser_slots  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FIX = Path(__file__).resolve().parent.parent / "fixtures" / "deck_rise_in.html"
MARK = FIX.parent / "deck_mark.html"
CALL = FIX.parent / "deck_call_dark.html"
LOGO = FIX.parent / "deck_logo_overhang.html"
FLOOR = FIX.parent / "deck_svg_floor.html"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(exe, prof, query="", fix=FIX):
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                        "--window-size=1280,800", "--virtual-time-budget=4000", "--dump-dom", fix.as_uri() + query],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    m = re.search(r'<pre id="out">(.*?)</pre>', p.stdout, re.S)
    return json.loads(unescape(m.group(1))) if m and m.group(1).strip() else None


def main():
    exe = browser()
    if not exe:
        print("  skip  no Chrome or Edge found - audit_deck.js was not run")
        return 0
    prof = tempfile.mkdtemp(prefix="audit_deck_")
    try:
        kept = run(exe, prof, "?keep")
        check("without finishing, the paused rise-in is measured as a 23 px scroll (the false finding)",
              bool(kept) and kept.get("scroll") == 1, kept)
        done = run(exe, prof)
        check("the audit ran with an endless animation on the slide", done is not None, done)
        check("finishing the entrance first: the recap is measured at rest, no scroll",
              bool(done) and done.get("scroll") == 0 and done.get("verdict") == "VERDICT: PASS", done)
        # a selected line must look selected: the old blue/amber boxes, where .cur on the amber box changed nothing
        old = run(exe, prof, "?old", MARK)
        check("the old look: the amber box marked .cur looks like itself at rest - mark fails",
              bool(old) and old.get("mark", 0) >= 1 and any(m.get("looksLike") == "itself" for m in old.get("marks", [])), old)
        new = run(exe, prof, "", MARK)
        check("gb_compose.css as shipped: every line marked .cur changes and looks like no line at rest",
              bool(new) and new.get("mark") == 0 and new.get("verdict") == "VERDICT: PASS", new)
        # the conclusion on a dark stepping slide: its bold term reads, and the mark check leaves no fade behind it
        call = run(exe, prof, "", CALL)
        check("a conclusion on a dark stepping slide passes contrast - its bold term and its words (M01 run 4, s02 / s07)",
              bool(call) and call.get("low") == 0 and call.get("verdict") == "VERDICT: PASS", call)
        # 2.62.0 - the official logo's clear space hangs below the template's top line: a pseudo-element, no words
        logo = run(exe, prof, "", LOGO)
        check("the logo box hanging 35 px below the top line of a photograph slide is no scroll (IGF M04 s01, s08)",
              bool(logo) and logo.get("scroll") == 0 and logo.get("verdict") == "VERDICT: PASS", logo)
        words = run(exe, prof, "?words", LOGO)
        check("... a line of words that falls out of the top line still is", bool(words) and words.get("scroll") == 1, words)
        # 2.72.7 - one 12.5 px rule: the deck audit keeps audit_drawing.js's 0.05 px tolerance (2.72.5 run: 27 builds
        # failed only on drawing words "12.5 px" that the studio called clean)
        fl = run(exe, prof, "", FLOOR)
        check("drawing words at 12.47 px pass, as in the figure audit; words at 12.4 px still fail",
              bool(fl) and fl.get("words") == ["under"], fl)
    finally:
        shutil.rmtree(prof, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
