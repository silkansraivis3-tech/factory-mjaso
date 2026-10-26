# -*- coding: utf-8 -*-
"""test_precheck - what would fail a build is found in seconds, before it is built; photographs are found large enough;
a rebuild of a built module is a fix (2.65.0).

    python test_precheck.py
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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
sys.path.insert(0, os.path.join(SKILLS, "course-visuals", "scripts"))
import test_compile_module as tc  # noqa: E402  - its sample course, script, png() and build sheet helpers
from image_size import pixel_size, found_size  # noqa: E402

PRE = os.path.join(HERE, "precheck.py")
BUILD = os.path.join(HERE, "build_module.py")
FIX = os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts", "fix.py")
ASSETS = os.path.join(SKILLS, "course-visuals", "scripts", "check_assets.py")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def course(tmp, name, screens=None, sheet=None, photos=None):
    os.makedirs(os.path.join(tmp, name))
    c, md = tc.new_course(os.path.join(tmp, name), tc.script(screens=screens or tc.SCREENS))
    meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
    for fname, (w, h) in (photos or {}).items():
        io.open(os.path.join(md, "assets", "img", fname), "wb").write(tc.png(w, h, (w % 200, 90, 150)))
        meta[fname] = dict(tc.PHOTO_META["ship.jpg"], description=fname, url_or_origin="https://example.org/" + fname)
    tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
    if sheet:
        tc.build_of(c, lambda b: b["screens"].update(sheet))
    return c, md


def main():
    tmp = tempfile.mkdtemp(prefix="pre_")
    try:
        print("-- the pre-check: seconds, from the files alone")
        c, md = course(tmp, "clean")
        t = time.time()
        code, out = run(PRE, c, "--module", "1")
        check("the sample module has nothing that stops its build", code == 0 and "nothing stops module 1" in out, out)
        check("... and it answers in seconds - no browser, no build", time.time() - t < 20, time.time() - t)

        print("\n-- photographs are found large enough (point 2)")
        c, md = course(tmp, "small", sheet={"s01": {"figure": "assets/img/tiny.png"}}, photos={"tiny.png": (400, 300)})
        code, out = run(PRE, c, "--module", "1")
        check("a 400 x 300 photograph stops the build: find a larger original, or say why it stays",
              code == 1 and "tiny.png (on s01) is only 400 x 300 px" in out and "low_resolution_ok" in out, out)
        meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
        meta["tiny.png"]["low_resolution_ok"] = "the only photograph of this ship there is"
        tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
        code, out = run(PRE, c, "--module", "1")
        check("... a reason recorded in its record lets it through", code == 0, out)
        c, md = course(tmp, "old", sheet={"s01": {"figure": "assets/img/old.png"}, "s02": {"figure": "assets/img/still.png"}},
                       photos={"old.png": (400, 300), "still.png": (798, 497)})
        meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
        meta["old.png"].update(source="old course, Liquefied Gas tankers, slide 23", url_or_origin="working_claude/old_course_images/x.jpg")
        meta["still.png"].update(source="NOVIKONTAS - render of the module's own 3D model", url_or_origin="render of assets/m_3d.js")
        tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
        code, out = run(PRE, c, "--module", "1")
        check("a picture from the old course: the stop says it has no larger original - find a larger photograph of the same thing",
              code == 1 and "comes from the old course (old course, Liquefied Gas tankers, slide 23), which has no larger original" in out, out)
        check("a still rendered from the module's own 3D model is a note - render it again larger - never a stop",
              "still.png" not in out.split("PRE-CHECK notes")[0] and "render again at 1600 px or more: still.png 798x497" in out, out)
        code, out = run(PRE, c, "--module", "1", "--rebuild")
        check("--rebuild (a module already built): its small pictures are a note, not a stop",
              code == 0 and "1 picture(s) under 800 px the module already had" in out, out)
        c, md = course(tmp, "mid", sheet={"s01": {"figure": "assets/img/mid.png"}}, photos={"mid.png": (1200, 800)})
        code, out = run(PRE, c, "--module", "1")
        check("a 1200 px photograph is a note - the compile enlarges it - never a stop",
              code == 0 and "1 photograph(s) under 1600 px" in out and "mid.png 1200x800" in out, out)
        code, out = run(tc.COMPILE, c, "--module", "1", "--no-drawing-check")
        keep = os.path.join(c, "working_claude", "photo_originals", "M01", "mid.png")
        check("built: the photograph is enlarged to 1600 px, its original kept",
              pixel_size(os.path.join(md, "assets", "img", "mid.png")) == (1600, 1067) and pixel_size(keep) == (1200, 800))
        code, out = run(PRE, c, "--module", "1")
        check("... and the pre-check still judges the photograph as it was found (1200 px), not its enlargement",
              "mid.png 1200x800" in out, out)
        io.open(os.path.join(md, "assets", "img", "mid.png"), "wb").write(tc.png(2400, 1600))
        check("a new, larger picture put in its place is judged as itself - the old kept original no longer counts",
              found_size(os.path.join(md, "assets", "img", "mid.png"), keep) == (2400, 1600))
        code, out = run(ASSETS, os.path.join(md, "assets", "img"))
        check("the asset check (photo-finding time) has no size warning for the 2400 px one",
              "under 1600 px" not in out and "no enlargement makes it sharp" not in out, out)
        c2, md2 = course(tmp, "assets", photos={"a.png": (500, 400), "b.png": (1000, 700)})
        code, out = run(ASSETS, os.path.join(md2, "assets", "img"))
        check("the asset check warns on a photograph under 800 px - no enlargement makes it sharp",
              "only 500 x 400 px - no enlargement makes it sharp" in out, out)
        check("... and on one under 1600 px - the original would be sharper", "1000 x 700 px - under 1600 px" in out, out)

        print("\n-- the pre-check finds what would fail the build (point 1)")
        c, md = course(tmp, "missing", sheet={"s02": {"figure": "assets/fig/none.svg"}})
        code, out = run(PRE, c, "--module", "1")
        check("a picture the build sheet names that is not there", code == 1 and "s02) : its figure assets/fig/none.svg".replace(") :", "):") in out, out)
        c, md = course(tmp, "tmpl", sheet={"s02": {"figure": "assets/fig/scale.svg", "template": "fancy"},
                                           "s03": {"figure": "ga.html", "template": "explain-figure", "variant": "diagonal"}})
        code, out = run(PRE, c, "--module", "1")
        check("a template, or a variant, the factory does not have", code == 1 and "the template \"fancy\"" in out
              and "has no variant \"diagonal\"" in out, out)
        dense = {"id": "s05", "kind": "slide", "title": "Why gas needs rules", "visual_kind": "none", "minutes": 3,
                 "text": " ".join(["Natural gas is stored cold and every part that touches it must stay cold and tight."] * 6)}
        scr = json.loads(json.dumps(tc.SCREENS))
        scr.insert(4, dense)
        c, md = course(tmp, "dense", screens=scr)
        code, out = run(PRE, c, "--module", "1")
        check("more than 60 words with no picture beside them (L61)", code == 1 and "(s05): 96 words and no picture" in out, out)
        short = lambda i: {"id": "x%d" % i, "kind": "slide", "title": "Point %d" % i, "visual_kind": "none", "minutes": 1,
                           "text": "A short point."}
        scr = json.loads(json.dumps(tc.SCREENS))
        scr[4:4] = [short(1), short(2), short(3)]
        c, md = course(tmp, "three", screens=scr)
        code, out = run(PRE, c, "--module", "1")
        check("three teaching slides in a row without a picture (L61)", code == 1 and "three teaching slides in a row without a picture (x1, x2, x3)" in out, out)
        drawn = [{"id": "d%d" % i, "kind": "slide", "title": "Drawing %d" % i, "layout": "split", "visual_kind": "schematic",
                  "visual": "x", "minutes": 2, "text": "A line about the drawing."} for i in range(1, 5)]
        c, md = course(tmp, "forced", screens=drawn + tc.SCREENS[-2:],
                       sheet={x["id"]: {"figure": "ga.html", "template": "explain-figure"} for x in drawn})
        code, out = run(PRE, c, "--module", "1")
        check("the same template forced on 4 slides in a row is a note - the compiler varies the look itself (L62)",
              code == 0 and "forces the template explain-figure on 4 slides in a row (d1 ... d4)" in out, out)

        print("\n-- build_module.py runs it first: nothing is built on a module that could not pass")
        c, md = course(tmp, "stop", sheet={"s01": {"figure": "assets/img/tiny.png"}}, photos={"tiny.png": (400, 300)})
        t = time.time()
        code, out = run(BUILD, c, "--module", "1", "--no-review", "--no-course-pages")
        check("the build stops at the pre-check, before the figures, and says what to fix",
              code == 1 and "nothing built: the pre-check found 1 thing(s) to fix first" in out and "tiny.png" in out, out[-800:])
        check("... in seconds, not a build's minutes", time.time() - t < 60, time.time() - t)
        check("... and nothing was built", not os.path.isfile(os.path.join(md, "presentation", "index.html")))
        clock = os.path.join(c, "working_claude", "_build", "M01_clock.json")
        check("... but the module's clock runs from its first build run (its sheet was not written by --init-build)",
              os.path.isfile(clock) and json.load(io.open(clock))["since"] == "its first build run")

        print("\n-- the gold standard: 30-40 min a module, 20 for its fixes (owner, 2026-10-26)")
        c, md = course(tmp, "clock")
        os.remove(os.path.join(c, "working_claude", "script", "M01.build.json"))
        tc.gate_fixture.open_gate(c)
        run(tc.COMPILE, c, "--module", "1", "--init-build")
        clock = os.path.join(c, "working_claude", "_build", "M01_clock.json")
        started = json.load(io.open(clock))["started"] if os.path.isfile(clock) else None
        check("--init-build (a new starter build sheet) starts the module's clock", started and abs(time.time() - started) < 120)
        import cf_timing
        line = cf_timing.clock_pass(c, "M01", now=started + 34 * 60)
        check("its first PASS says its minutes, inside the gold standard",
              line == "TIME M01: 34 min from its starter build sheet to its first PASS - inside the gold standard (30-40 min a module)", line)
        check("... once: a later PASS (a fix round) does not move it", cf_timing.clock_pass(c, "M01", now=started + 90 * 60) is None
              and json.load(io.open(clock))["minutes"] == 34)
        cf_timing.clock_start(c, "M01", reset=True)
        st = json.load(io.open(clock))["started"]
        check("a module over 40 min is said loud, with where to look",
              "OVER the gold standard of 30-40 min by 12 min" in cf_timing.clock_pass(c, "M01", now=st + 52 * 60))
        check("a fix inside 20 min / over it", "inside the gold standard's 20 min" in cf_timing.fix_line(17 * 60)
              and "OVER the gold standard's 20 min" in cf_timing.fix_line(25 * 60))

        print("\n-- a rebuild of a built module is a fix (fix.py rebuild)")
        c, md = course(tmp, "rebuild")
        run(tc.COMPILE, c, "--module", "1", "--no-drawing-check")
        t = time.time()
        code, out = run(FIX, "rebuild", c, "--modules", "1")
        check("fix.py rebuild: the module built again from its approved words, then ONE layout check and the package check",
              "Module 1: rebuilt from its approved words" in out and "One check for the rebuilt modules (1)" in out
              and "layout at 1280x800" in out, out[-900:])
        check("... no figure stage, no review sheets", "figure_fit" not in out and "review sheets" not in out.lower(), out[-600:])
        check("... and it says its minutes against the 20 a fix gets", "TIME: this fix took" in out
              and "inside the gold standard's 20 min for fixes" in out, out[-300:])
        meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
        io.open(os.path.join(md, "assets", "img", "tiny.png"), "wb").write(tc.png(300, 200))
        meta["tiny.png"] = dict(tc.PHOTO_META["ship.jpg"], description="tiny", url_or_origin="https://example.org/tiny")
        tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
        tc.build_of(c, lambda b: b["screens"].update({"s01": {"figure": "assets/img/tiny.png"}}))
        code, out = run(FIX, "rebuild", c, "--modules", "1")
        check("... a small picture the module already has does not stop a rebuild - it is a note to replace it",
              "Module 1: rebuilt from its approved words" in out and "1 picture(s) under 800 px the module already had" in out
              and "tiny.png 300x200" in out, out[-900:])
        tc.build_of(c, lambda b: b["screens"].update({"s01": {"figure": "assets/img/gone.png"}}))
        code, out = run(FIX, "rebuild", c, "--modules", "1")
        check("... a module the pre-check stops (a picture that is not there) is not rebuilt, and says why",
              code == 1 and "Module 1: not rebuilt - the pre-check found" in out and "Nothing rebuilt." in out, out[-600:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("What would fail a build is found before it, photographs are found large enough, and a rebuild is a fix.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
