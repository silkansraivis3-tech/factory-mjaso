# -*- coding: utf-8 -*-
"""test_drawing_check - the drawing check in slices side by side finds what it finds whole (2.56.0).

    python test_drawing_check.py

A deck of 8 slides with one room poking out of its hull on slide 7 is checked one page at a time with the deck whole
(CF_DRAWING_JOBS=1, as before 2.56.0) and in slices side by side (the default): the same findings, the same slide
number (a slice keeps only its slides, so its own count starts at 1 - drawing_check puts the deck's number back).
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import drawing_check as dc  # noqa: E402

FAILS = []

GOOD = ('<svg viewBox="0 0 100 60"><path d="M5 10 H95 L90 50 H25 L8 40 Z" fill="#fff" stroke="#0A2463"/>'
        '<rect x="30" y="16" width="30" height="26" fill="#eef" stroke="#0A2463"/></svg>')
BAD = ('<svg viewBox="0 0 100 60"><path d="M5 10 H95 L90 50 H25 L8 40 Z" fill="#fff" stroke="#0A2463"/>'
       '<g class="kit-part" data-kit-id="ER"><rect id="room" x="10" y="14" width="30" height="34" fill="#eef" stroke="#0A2463"/>'
       '</g></svg>')
DECK = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>deck</title>
<style>.slide{display:none;width:1280px;height:800px}.slide.active{display:block}svg{width:600px;height:auto}</style></head>
<body>%s</body></html>"""


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def main():
    check("a deck is cut into slices of at least 3 slides; a task page and a short deck stay whole",
          dc.slices("x/tasks/a.html", 7) == [None] and dc.renumber({"findings": [{"where": "slide 2 (s05)"}]}, [9, 10, 11])
          ["findings"][0]["where"] == "slide 11 (s05)")
    check("2.57.0 a slice is the list of slides it keeps: the 2nd of slides 3, 8, 12 is slide 9",
          dc.renumber({"findings": [{"where": "slide 2 (s09) step 1"}]}, [2, 8, 11])["findings"][0]["where"] == "slide 9 (s09) step 1")
    if not dc.find_browser():
        print("SKIP the browser part - no Chrome or Edge")
        return 1 if FAILS else 0
    tmp = tempfile.mkdtemp(prefix="test_dc_")
    try:
        os.makedirs(os.path.join(tmp, "presentation"))
        deck = os.path.join(tmp, "presentation", "index.html")
        body = "".join('<section class="slide%s" id="s%02d">%s</section>' % (" active" if i == 0 else "", i + 1,
                                                                             BAD if i == 6 else GOOD) for i in range(8))
        io.open(deck, "w", encoding="utf-8").write(DECK % body)
        check("... an 8-slide deck is cut into 3 slices for 3 browsers", dc.slices(deck, 3) == [[0, 1, 2], [3, 4, 5], [6, 7]],
              dc.slices(deck, 3))
        check("... and only the slides asked for, when some are unchanged (2.57.0)", dc.slices(deck, 3, [1, 6]) == [[1, 6]],
              dc.slices(deck, 3, [1, 6]))
        out = {}
        for jobs in ("1", "3"):
            os.environ["CF_DRAWING_JOBS"] = jobs
            out[jobs] = dc.check([deck], root=tmp)[0]
        os.environ.pop("CF_DRAWING_JOBS", None)
        check("whole: the room poking out of the hull is found on slide 7",
              any("slide 7 (s07)" in p and "room" in p for p in out["1"]), out["1"])
        check("in slices side by side: the same findings, the same slide number", out["1"] == out["3"], out)
        check("2.56.0 a kit part's finding names its spec id ([part ER]), so the fix knows what to move",
              any("[part ER]" in p for p in out["1"]), out["1"])
        # 2.62.1 - a slide whose own script never lets the page finish (IGF M01 v262: slides 3-5 with a 3D scene held the
        # build 600 s, twice, and the build said only "could not finish")
        hang = DECK % (body + "<script>setTimeout(function(){if(document.getElementById('s04')){while(true){}}},50);</script>")
        io.open(deck, "w", encoding="utf-8").write(hang)
        os.environ["CF_DRAWING_JOBS"], os.environ["CF_DRAWING_SLIDE_SECONDS"] = "3", "6"
        import time
        t = time.time()
        got = dc.check([deck], root=tmp)[0]
        secs = time.time() - t
        os.environ.pop("CF_DRAWING_JOBS", None)
        os.environ.pop("CF_DRAWING_SLIDE_SECONDS", None)
        check("a slide that stalls the browser is named on its own (slide 4), not the whole deck 'could not finish'",
              any(p.startswith("presentation/index.html, slide 4: stalls the hidden browser") for p in got)
              and not any("could not finish" in p for p in got), got)
        check("... and the other slides are still judged: the room on slide 7 is still found", any("slide 7 (s07)" in p for p in got), got)
        check("... within its time limits (a 3-slide piece, then each slide alone), not 600 s: %.0f s" % secs, secs < 60, secs)
        check("the limits: 45 s a slide, 106 s for three, at most 600; a task page 60 s",
              dc.time_limit(deck, [3]) == 45 and round(dc.time_limit(deck, [0, 1, 2])) == 106
              and dc.time_limit(deck, list(range(40))) == 600 and dc.time_limit("x/tasks/a.html", None) == 60)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
