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
import re
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


def refit_part(md, out):
    """2.63.2 (QA of IGF M12 s02 / M14 s05: figure_fit re-fit a drawing after the review, and the build said "no screen
    changed since the last review") - a figure whose spec changed is a changed screen, however few px it moved"""
    print("\n-- 2.63.2: a re-fitted figure is reviewed again")
    deck = os.path.join(md, "presentation", "index.html")
    text = io.open(deck, encoding="utf-8").read()
    sec = re.search(r'<section[^>]*id="s03".*?</section>', text, re.S)
    spec = re.search(r'(<script type="application/json"[^>]*>)(.*?)(</script>)', sec.group(0), re.S) if sec else None
    if not spec:
        check("s03 carries its kit spec in the deck", False, sec and sec.group(0)[:300])
        return
    data = json.loads(spec.group(2).replace("<\\/", "</"))
    data["parts"][0]["x"] = data["parts"][0].get("x", 0) + 0.3        # a third of a unit - a refit nudges this little
    new_sec = sec.group(0).replace(spec.group(0), spec.group(1) + json.dumps(data).replace("</", "<\\/") + spec.group(3))
    io.open(deck, "w", encoding="utf-8").write(text.replace(sec.group(0), new_sec))
    p = subprocess.run(["node", REVIEW, md, out], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    sheets = json.load(io.open(os.path.join(out, "sheets.json"), encoding="utf-8")) if os.path.isfile(os.path.join(out, "sheets.json")) else {}
    shown = [s for x in sheets.get("sheets", []) for s in x.get("screens", [])]
    check("the slide whose figure moved a third of a unit (under the picture fingerprint) is on the new sheets; the others not",
          p.returncode == 0 and any("s03" in str(s) for s in shown) and not any("s02" in str(s) for s in shown), (shown, p.stdout[-300:]))
    io.open(deck, "w", encoding="utf-8").write(text)


def shots_part(md, tmp):
    """2.63.3 (the 2.63.2 full-course run: every screen photographed in every round, 3,406 shots / 3,334 s; the earlier parts
    of 103 paged slides never photographed; M11's last slide looped 381 times) - --shots keeps the picture of a screen
    unchanged in everything it loads; every part of a paged slide is its own picture, changed together; the walk stops"""
    print("\n-- 2.63.3: only changed screens are photographed; every part of a paged slide; a Next that never stops")
    pd = os.path.join(tmp, "parts_module")
    shutil.copytree(md, pd)
    deck = os.path.join(pd, "presentation", "index.html")
    text = io.open(deck, encoding="utf-8").read()
    sec = re.search(r'(<section[^>]*id="s02"[^>]*>)(.*?)(</section>)', text, re.S)
    parted = sec.group(1) + sec.group(2) + ('<div class="lt-part on" data-part="1"><p>PART ONE words</p></div>'
                                            '<div class="lt-part" data-part="2"><p>PART TWO words</p></div>') + sec.group(3)
    io.open(deck, "w", encoding="utf-8").write(text.replace(sec.group(0), parted))
    shots, base = os.path.join(tmp, "shots"), os.path.join(tmp, "nobase")

    def go(out, base=base):
        t = time.time()
        p = subprocess.run(["node", REVIEW, pd, out, "--shots=" + shots, "--base=" + base], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        man = json.load(io.open(os.path.join(out, "manifest.json"), encoding="utf-8")) if os.path.isfile(os.path.join(out, "manifest.json")) else {}
        sh = json.load(io.open(os.path.join(out, "sheets.json"), encoding="utf-8")) if os.path.isfile(os.path.join(out, "sheets.json")) else {}
        return p.returncode, p.stdout + p.stderr, man, sh, time.time() - t
    c1, o1, m1, s1, t1 = go(os.path.join(tmp, "sh1"))
    parts = [k for k in m1 if k.startswith("deck/s02")]
    check("a paged slide gets one picture per part (deck/s02 and deck/s02#2)", c1 == 0 and sorted(parts) == ["deck/s02", "deck/s02#2"],
          (c1, parts, o1[-300:]))
    c2, o2, m2, s2, t2 = go(os.path.join(tmp, "sh2"))
    m = re.search(r"(\d+) photographed, (\d+) unchanged kept", o2)
    check("a second run with nothing changed photographs nothing and keeps every picture (%s)" % (m and m.group(0)),
          c2 == 0 and m and m.group(1) == "0" and int(m.group(2)) == len(m1), o2[-300:])
    diff = {k: worst(m1[k], m2[k]) for k in m1 if k in m2}
    check("... the same screens with the same pictures, and the same grading (failures none)",
          list(m1) == list(m2) and not any(v > 8 for v in diff.values()) and s1.get("failures") == s2.get("failures") == [],
          (list(m1), list(m2), s2.get("failures")))
    check("... and it is faster (%.1f s, the first %.1f s)" % (t2, t1), t2 < t1, (t1, t2))
    text = io.open(deck, encoding="utf-8").read()
    io.open(deck, "w", encoding="utf-8").write(text.replace("PART TWO words", "PART TWO words, changed"))
    c3, o3, m3, s3, t3 = go(os.path.join(tmp, "sh3"), os.path.join(tmp, "sh2"))       # compared with the run before
    m = re.search(r"(\d+) photographed", o3)
    shown = [s for x in s3.get("sheets", []) for s in x.get("screens", [])]
    check("one part's words changed: only that slide is photographed again (%s)" % (m and m.group(0)),
          c3 == 0 and m and m.group(1) == "2", o3[-300:])
    check("... and both of its parts are on the sheets, nothing else (parts change together)",
          len(shown) == 2 and all("(s02)" in s for s in shown), shown)
    # a last slide whose Next never turns off: the walk stops instead of looping 400 times
    loop = ("<script>setInterval(function(){var b=document.getElementById('btnNext');if(b)b.disabled=false;},5);</script>")
    text = io.open(deck, encoding="utf-8").read()
    i = text.lower().rfind("</body>")
    io.open(deck, "w", encoding="utf-8").write(text[:i] + loop + text[i:])
    t = time.time()
    p = subprocess.run(["node", REVIEW, pd, os.path.join(tmp, "sh4"), "--all"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, env=dict(os.environ, CF_TIMING=os.path.join(tmp, "loop.jsonl")))
    rows = [json.loads(x) for x in io.open(os.path.join(tmp, "loop.jsonl"), encoding="utf-8") if x.strip()] \
        if os.path.isfile(os.path.join(tmp, "loop.jsonl")) else []
    steps = [r for r in rows if str(r.get("what", "")).startswith("deck ") and "(step)" in str(r.get("what"))]
    check("a deck whose last slide never turns Next off: the walk stops after the slide's own parts and steps (%d extra visits)"
          % len(steps), p.returncode == 0 and len(steps) <= 3, (p.returncode, len(steps), p.stdout[-200:]))


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
        refit_part(md, os.path.join(tmp, "still"))
        shots_part(md, tmp)
        blind_part(md, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
