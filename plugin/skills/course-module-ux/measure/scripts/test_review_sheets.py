# -*- coding: utf-8 -*-
"""test_review_sheets - review_sheets.mjs's waits end when the page is still (2.61.0), and the review is what it was.

    python test_review_sheets.py

Pinned, on a module the compiler builds from the compile tests' fixtures (slides with a photo, a drawing and a stepping
figure-kit drawing; task pages on photographs and on the kit drawing, every mechanic the fixtures have):
  * the review with the new waits photographs the same screens as with the fixed waits (--fixed-waits, the waits before
    2.61.0): every picture the same by the review's own "changed" test (its fingerprint, 16 x 16 px cells), most of them
    byte for byte, and the same labels;
  * every question is graded the same (the same failures, none here) - item 4 of the review is the same check;
  * a page timer the fixed wait let run still runs before the picture (a word put on the slide 120 ms after a click);
  * it is faster.
Skips, and says so, when no Chrome or Edge or no node is installed.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
COMPILE_DIR = os.path.join(SKILLS, "course-factory", "compile", "scripts")
sys.path.insert(0, COMPILE_DIR)
sys.path.insert(0, HERE)
import test_compile_module as tcm  # noqa: E402
from test_audit_drawing import browser  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REVIEW = os.path.join(HERE, "review_sheets.mjs")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def review(md, out, *extra):
    t = time.time()
    p = subprocess.run(["node", REVIEW, md, out, "--all"] + list(extra), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    took = time.time() - t
    man = json.load(io.open(os.path.join(out, "manifest.json"), encoding="utf-8")) if os.path.isfile(os.path.join(out, "manifest.json")) else {}
    sheets = json.load(io.open(os.path.join(out, "sheets.json"), encoding="utf-8")) if os.path.isfile(os.path.join(out, "sheets.json")) else {}
    return p.returncode, p.stdout + p.stderr, man, sheets, took


def worst(a, b):
    """the review's own measure of a changed picture: the largest grey difference of one 16 x 16 px cell (changed at > 8)"""
    import base64
    x, y = base64.b64decode(a), base64.b64decode(b)
    return 999 if len(x) != len(y) else max([abs(i - j) for i, j in zip(x, y)] or [0])


def module(tmp):
    """the compile tests' slides and task pages in one module - s03 the stepping kit drawing (its pump runs: an endless
    animation), s05 a slide whose words a timer changes 120 ms after it is shown"""
    screens = tcm.SCREENS[:4] + [{"id": "s05", "kind": "slide", "title": "Later words", "layout": "split", "visual_kind": "comparison",
                                  "text": "The words change.\nA timer changes them.", "visual": "Thermometer scale.", "minutes": 4}] \
        + tcm.FIGURE_TASKS
    build = json.loads(json.dumps(tcm.FIGURE_BUILD))
    build["screens"].update({"s01": {"figure": "assets/img/ship.jpg"}, "s02": {"figure": "assets/fig/scale.svg"},
                             "s03": {"figure": "plant.kit.json"}, "s05": {"figure": "assets/fig/scale.svg"},
                             "s04": {"figure": "hull.svg", "dark": True, "declined_3d": "the fixture's hull section stays a flat drawing"}})
    c, md = tcm.figures_course(tmp, build=build, screens=screens)
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1")
    deck = os.path.join(md, "presentation", "index.html")
    if not os.path.isfile(deck):
        return None, out
    # a timer the page sets when s05 is shown: the fixed 160 + 140 ms waits let it run before the picture, so must the new ones
    text = io.open(deck, encoding="utf-8").read()
    later = ("<script>new MutationObserver(function(){var s=document.getElementById('s05');if(s&&s.classList.contains('active')"
             "&&!s.__t){s.__t=1;setTimeout(function(){var h=s.querySelector('h2');if(h)h.textContent='CHANGED BY A TIMER';},120);}})"
             ".observe(document.body,{attributes:true,subtree:true,attributeFilter:['class']});</script>")
    i = text.lower().rfind("</body>")
    io.open(deck, "w", encoding="utf-8").write(text[:i] + later + text[i:])
    return md, out


def blind_part(md, tmp):
    """2.63.0 (the IGF full build on 2.63.0: the final passed only with --no-review) - a blind page (a graded final, data-blind,
    2.60.0) shows no verdict, so the probe read every right answer as graded wrong. It reads the page's report instead"""
    print("\n-- 2.63.0: a blind page is graded by its report to the classroom")
    bd = os.path.join(tmp, "blind_module")
    shutil.copytree(md, bd)
    pages = [os.path.join(bd, d, f) for d in ("tasks", "assessment") if os.path.isdir(os.path.join(bd, d))
             for f in os.listdir(os.path.join(bd, d)) if f.endswith(".html") and "answer_key" not in f]
    for p in pages:
        t = io.open(p, encoding="utf-8").read()
        io.open(p, "w", encoding="utf-8").write(t.replace("<body ", '<body data-blind="1" ', 1))
    code, out, man, sheets, took = review(bd, os.path.join(tmp, "blind_out"))
    check("every question of the blind pages graded as expected - right answers right, wrong ones not (%d pages)" % len(pages),
          code == 0 and sheets.get("failures") == [] and "Every question graded as expected" in out, (code, sheets.get("failures"), out[-400:]))
    eng = os.path.join(bd, "assets", "gb_answer.js")
    src = io.open(eng, encoding="utf-8").read()        # read before the write opens (and empties) it
    io.open(eng, "w", encoding="utf-8").write(src.replace("ok: !!(q.done && q.ok)", "ok: true", 1))
    code, out, man, sheets, took = review(bd, os.path.join(tmp, "blind_bad"))
    bad = [x for x in sheets.get("failures") or [] if "WRONG answer was graded right - its report says ok: true" in x]
    check("... and an engine that reports every answer right is caught on them", code == 1 and bad, (code, (sheets.get("failures") or [])[:3]))


def main():
    exe = browser()
    node = shutil.which("node")
    if not exe or not node:
        print("  skip  %s - review_sheets.mjs was not run" % ("no Chrome or Edge" if not exe else "no node"))
        print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
        return 0
    tmp = tempfile.mkdtemp(prefix="review_sheets_t_")
    try:
        md, out = module(tmp)
        check("the fixture module is built (a deck and its task pages)", md is not None, out[-600:])
        if not md:
            return 1
        c0, o0, m0, s0, t0 = review(md, os.path.join(tmp, "fixed"), "--fixed-waits")
        c1, o1, m1, s1, t1 = review(md, os.path.join(tmp, "still"))
        check("both reviews run and photograph screens", c0 == 0 and c1 == 0 and len(m0) > 10, (c0, c1, len(m0), o0[-300:], o1[-300:]))
        check("... the same screens, in the same order, with the same labels",
              list(m0) == list(m1) and [x["screens"] for x in s0.get("sheets", [])] == [x["screens"] for x in s1.get("sheets", [])],
              (list(m0), list(m1)))
        diff = {k: worst(m0[k], m1[k]) for k in m0 if k in m1}
        changed = sorted(k for k, v in diff.items() if v > 8)
        check("every picture is the same by the review's own test (no 16 px cell more than 8 grey levels apart)", not changed,
              {k: diff[k] for k in changed})
        same = sum(1 for v in diff.values() if v == 0)
        check("... most of them exactly the same (%d of %d)" % (same, len(diff)), same >= 0.8 * len(diff), diff)
        check("every question graded the same: the same failures (none)", s0.get("failures") == s1.get("failures") == [],
              (s0.get("failures"), s1.get("failures")))
        s05 = [k for k in m1 if k.endswith("/s05")]
        # the fixed waits (160 + 140 ms) always let the 120 ms timer run: the same picture means the new waits did too
        check("a heading a page timer changes 120 ms after the slide is shown is changed on its picture, as with the fixed waits",
              s05 and diff.get(s05[0], 999) <= 8, (s05, [diff.get(k) for k in s05]))
        check("the new waits are faster (%.1f s, the fixed ones %.1f s)" % (t1, t0), t1 < t0, (t0, t1))
        blind_part(md, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
