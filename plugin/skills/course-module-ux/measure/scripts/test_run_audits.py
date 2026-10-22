# -*- coding: utf-8 -*-
"""test_run_audits - run_audits.py runs the three browser probes in headless Chrome or Edge and turns them into an exit code.

    python test_run_audits.py

Pinned, on measure/fixtures decks (and the step-figure deck beside the scripts):
  * the viewport it measures at is the one asked for, not the browser window's smaller inside;
  * a failing deck (deck_steps: every screen a corner cluster) exits 1 and names the screens; a passing probe is not listed with --quiet;
  * a sideways-scrolling deck (deck_scroll) fails the deck probe; a deck with no Next control cannot be composed -> exit 2, never a pass;
  * audit_compose.js answers `.all()` like the other probes and sets window.__auditExit;
  * the page injected beside the deck is gone afterwards, and the deck file is untouched;
  * what is printed and returned for a clean run (a stubbed browser: a clean run needs a real clean deck).
Skips, and says so, when no Chrome or Edge is installed.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_audits as ra  # noqa: E402
from test_audit_drawing import browser  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
STEPS = HERE / "fixtures" / "deck_steps.html"
SCROLL = HERE.parent / "fixtures" / "deck_scroll.html"
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ra.main(list(args))
    return code, buf.getvalue()


def leftovers():
    return sorted(p.name for d in (STEPS.parent, SCROLL.parent) for p in d.glob("_audit_*.html"))


def main():
    src = (HERE / "audit_compose.js").read_text(encoding="utf-8")
    check("audit_compose.js has .all(), keeps .run(), sets __auditExit and registers like the others",
          "all: all" in src and "run: run" in src and "__auditExit" in src and "__audit.compose" in src)
    check("the GUIDE lists the entry point as .all()", "AuditCompose.all()" in (HERE.parent / "GUIDE.md").read_text(encoding="utf-8"))

    # the summary and the exit code, on records shaped like the probes' own (no browser needed)
    ok = {"res": {"slidesTotal": 5, "failures": 0, "failingSlides": [], "verdict": "VERDICT: PASS"}, "exit": 0}
    st, line, det = ra.summarise("deck", ok)
    check("a passing deck probe is PASS and names its slides", st == "PASS" and "5 slides" in line and not det, (st, line))
    st, line, det = ra.summarise("compose", {"res": {"screens": 4, "review": 1, "weak": 0, "verdict": "REVIEW n=1",
                                                     "problems": [{"n": 3, "verdict": "REVIEW", "title": "T", "findings": ["x"]}]}, "exit": 0})
    check("a compose REVIEW screen is listed but does not fail", st == "PASS" and "REVIEW 1: 3" in line and det and "screen 3" in det[0], (st, line, det))
    st, line, det = ra.summarise("collide", {"res": {"ABORTED": "VIEWPORT TOO SMALL"}, "exit": 1})
    check("an aborted probe is ABORT, never PASS", st == "ABORT", (st, line))
    st, _, _ = ra.summarise("deck", {"res": {"failures": 0}, "exit": None})
    check("a probe that never set __auditExit is ABORT", st == "ABORT")
    # a failing slide names the element and its words, not "slide 2: low 1" (M01 benchmark run 4: a --json run was needed)
    bad = {"res": {"slidesTotal": 8, "failures": 2, "verdict": "VERDICT: FAIL n=2", "failingSlides": [
        {"slide": 2, "id": "s02", "low": [{"sel": "b", "ratio": 2.29, "need": 4.5, "px": 22, "txt": "flashpoint"}],
         "spill": [{"sel": "p.call", "byPx": 18}]}]}, "exit": 1}
    st, line, det = ra.summarise("deck", bad)
    check("a low-contrast finding names the slide id, the element, its words and the ratio",
          st == "FAIL" and any("s02" in d and "low contrast b" in d and '"flashpoint"' in d and "2.29:1" in d for d in det)
          and any("spills p.call by 18 px" in d for d in det), det)
    st, line, det = ra.summarise("collide", {"res": {"totalCollisions": 1, "slides": [
        {"slide": 4, "id": "s04", "n": 1, "text": [{"a": "p.lead", "aTxt": "Gas valve unit", "b": "text", "bTxt": "GVU"}],
         "box": [], "chrome": []}]}, "exit": 1})
    check("a collision names both elements and their words",
          st == "FAIL" and det and "s04" in det[0] and '"Gas valve unit"' in det[0] and '"GVU"' in det[0], det)
    real_measure, real_browser, real_offset = ra.measure, ra.browser, ra.frame_offset
    try:
        clean = {"deck": ok, "collide": {"res": {"totalCollisions": 0, "slides": []}, "exit": 0},
                 "compose": {"res": {"screens": 5, "review": 0, "weak": 0, "verdict": "COMPOSED", "problems": []}, "exit": 0}, "viewport": [1280, 800]}
        ra.browser, ra.frame_offset = (lambda: "stub"), (lambda exe: (0, 0))
        ra.measure = lambda exe, deck, size, budget, offset=(0, 0): (clean, "")
        code, out = cli(str(STEPS))
        check("every probe clean: exit 0, three PASS lines", code == 0 and out.count("PASS") >= 3 and "every probe passed" in out, out)
        code, out = cli(str(STEPS), "--quiet")
        check("--quiet prints no passing line", code == 0 and "deck  " not in out, out)
        # 2.61.0 - the viewports are measured side by side, and said in their own order whichever finishes first
        import threading
        import time
        live, most, lock = [0], [0], threading.Lock()

        def slow(exe, deck, size, budget, offset=(0, 0)):
            with lock:
                live[0] += 1
                most[0] = max(most[0], live[0])
            time.sleep(0.6 if size[0] == 1280 else 0.45)         # the first viewport finishes last
            with lock:
                live[0] -= 1
            return dict(clean, viewport=list(size)), ""
        ra.measure = slow
        t = time.time()
        code, out = cli(str(STEPS), "--viewport", "1024x768", "--viewport", "1920x1080")
        took = time.time() - t
        lines = [x.split()[0] for x in out.splitlines() if " PASS " in x]
        check("three viewports run at once (2.61.0): all three measured together, in about the slowest one's time "
              "(one after the other: 1.5 s)", code == 0 and most[0] == 3 and took < 1.4, (most[0], round(took, 2), out))
        check("... and are said in the order asked for, not the order they finished",
              lines == ["1280x800"] * 3 + ["1024x768"] * 3 + ["1920x1080"] * 3, lines)
        live[0] = most[0] = 0
        code, out = cli(str(STEPS), "--viewport", "1024x768", "--jobs", "1")
        check("--jobs 1 measures one viewport after the other", code == 0 and most[0] == 1, most[0])
        ra.measure = lambda exe, deck, size, budget, offset=(0, 0): (None, "boom")
        code, out = cli(str(STEPS))
        check("a page that gave no result is exit 2, not a pass", code == 2 and "NOT MEASURED" in out, out)
        ra.browser = lambda: None
        code, out = cli(str(STEPS))
        check("no Chrome or Edge: exit 2 and it says nothing was measured", code == 2 and "nothing measured" in out, out)
    finally:
        ra.measure, ra.browser, ra.frame_offset = real_measure, real_browser, real_offset

    exe = browser()
    if not exe:
        print("  skip  no Chrome or Edge found - the probes were not run in a browser")
        print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
        return 1 if FAIL else 0

    before = (STEPS.read_bytes(), SCROLL.read_bytes())
    out_json = Path(__import__("tempfile").mkdtemp(prefix="run_audits_t_")) / "full.json"
    code, out = cli(str(STEPS), "--viewport", "1024x768", "--json", str(out_json))
    full = json.loads(out_json.read_text(encoding="utf-8")) if out_json.is_file() else {}
    check("both viewports are measured, at the size asked for (not the window's smaller inside)",
          sorted(full) == ["1024x768", "1280x800"] and full["1280x800"]["viewport"] == [1280, 800]
          and full["1024x768"]["viewport"] == [1024, 768], {k: v.get("viewport") for k, v in full.items()})
    check("deck_steps: the deck probe passes, compose fails on its three corner-cluster screens, the exit is 1",
          code == 1 and "1280x800  deck     PASS" in out and "1280x800  compose  FAIL" in out and out.count("WEAK -") >= 3, out)
    check("... and every probe wrote the verdict the others write (__auditExit 0/1)",
          all(full["1280x800"][k]["exit"] in (0, 1) for k in ("deck", "collide", "compose")), full.get("1280x800"))
    # 2.61.0 - side by side, every probe finds exactly what one viewport after the other found (the page clock aside)
    one_json = out_json.with_name("one.json")
    code1, out1 = cli(str(STEPS), "--viewport", "1024x768", "--json", str(one_json), "--jobs", "1")
    one = json.loads(one_json.read_text(encoding="utf-8")) if one_json.is_file() else {}
    strip = lambda d: {k: {n: r for n, r in v.items() if n != "virt"} for k, v in d.items()}   # noqa: E731
    check("the viewports side by side give the same results and the same report as one after the other",
          one and strip(one) == strip(full) and (code1, out1) == (code, out), (code1, code))
    code, out = cli(str(STEPS), "--quiet")
    check("--quiet leaves out the passing probes", code == 1 and "deck  " not in out and "compose" in out, out)
    code, out = cli(str(SCROLL))
    check("a deck that scrolls sideways fails the deck probe; no Next control means compose aborts, so exit 2",
          code == 2 and "1280x800  deck     FAIL" in out and "scrolls sideways" in out and "compose  ABORT" in out, out)
    check("the injected page is gone and the decks are untouched",
          not leftovers() and (STEPS.read_bytes(), SCROLL.read_bytes()) == before, leftovers())
    overlay_part()
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


def overlay_part():
    """2.63.2 (the IGF M06 rebuild on 2.63.2: "box on box div.m06-3d / button.gb-fs3d-btn") - a control laid over a figure
    on purpose (data-overlay: the 3D Full screen button, a part's camera badge) may sit on the figure's painted boxes, and
    is judged never over a word"""
    fs = HERE / "fixtures" / "deck_3d_fs.html"
    base = fs.read_text(encoding="utf-8")
    framed = base.replace(".fixture-stage { position: relative; height: 360px; }",
                          ".fixture-stage { position: relative; height: 360px; margin-top: 24px; border: 2px solid #0A2463; }", 1)
    over = framed.replace('<section class="slide" id="s1" data-visual="none"><div class="slide-body"><h2>Title</h2>',
                          '<section class="slide" id="s1" data-visual="none"><div class="slide-body"><div style="position:relative">'
                          '<h2>Title of the module</h2><button type="button" data-overlay style="position:absolute;left:0;top:0;'
                          'width:220px;height:100%;background:#0A2463;border:0"></button></div>', 1)
    for name, text, want in (("framed", framed, "no"), ("over a word", over, "yes")):
        p = fs.with_name("_ov_%d.html" % os.getpid())
        p.write_text(text, encoding="utf-8")
        try:
            code, out = cli(str(p), "--quiet")
        finally:
            p.unlink()
        hit = "collide  FAIL" in out
        check("2.63.2 overlay %s: %s" % (name, "the Full screen button on the scene's framed box is no collision" if want == "no"
                                          else "an overlay control over a heading is a collision (like the chrome)"),
              hit == (want == "yes") and (want == "no" or "Title of the module" in out or "under" in out), out[-700:])


if __name__ == "__main__":
    sys.exit(main())
