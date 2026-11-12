# -*- coding: utf-8 -*-
"""test_precheck - what would fail a build is found in seconds, before it is built; photographs are found large enough;
a rebuild of a built module is a fix (2.65.0).

    python test_precheck.py
"""
from __future__ import annotations

import io
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["CF_UPSCALE"] = "off"     # 2.73.2: the build enlarges small photos first - off here, the same on every PC
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
        check("an old-course photograph nobody recorded opening stops the build - its catalogue words were its old slide's, "
              "not what it shows (five auto picks went in with the script's wanted picture as their record)",
              code == 1 and "old.png (on s01): nobody has recorded opening it" in out, out)
        meta["old.png"].update(visually_verified="yes - a gas-fuelled ship alongside a bunker vessel, hose connected 2026-11-12",
                               description="A gas-fuelled ship alongside a bunker vessel, the bunkering hose connected")
        tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
        code, out = run(PRE, c, "--module", "1")
        check("2.73.2 (owner, 2026-10-28) a small picture from the old course is reused and enlarged - a note, never a stop",
              "old.png" not in out.split("PRE-CHECK notes")[0] and "reused and enlarged" in out and "old.png 400x300" in out, out)
        check("a still rendered from the module's own 3D model is a note - render it again larger - never a stop",
              "still.png" not in out.split("PRE-CHECK notes")[0] and "render again at 1600 px or more: still.png 798x497" in out, out)
        code, out = run(PRE, c, "--module", "1", "--rebuild")
        check("--rebuild (a module already built): its small pictures are a note, not a stop",
              code == 0 and "1 picture(s) under 800 px" in out and "reused and enlarged" in out, out)
        c, md = course(tmp, "mid", sheet={"s01": {"figure": "assets/img/mid.png"}}, photos={"mid.png": (1200, 800)})
        code, out = run(PRE, c, "--module", "1")
        check("a 1200 px photograph is accepted without a note - 1024 px or more is enough",
              code == 0 and "mid.png" not in out and "found under" not in out, out)
        code, out = run(tc.COMPILE, c, "--module", "1", "--no-drawing-check")
        keep = os.path.join(c, "working_claude", "photo_originals", "M01", "mid.png")
        check("built: the photograph is enlarged to 1600 px, its original kept",
              pixel_size(os.path.join(md, "assets", "img", "mid.png")) == (1600, 1067) and pixel_size(keep) == (1200, 800))
        code, out = run(PRE, c, "--module", "1")
        check("... and the pre-check still judges the photograph as it was found (1200 px), not its enlargement",
              code == 0 and "mid.png" not in out, out)

        print("\n-- what a photograph shows, and what is printed on it")
        import precheck
        sc = tc.cs.load(os.path.join(c, "working_claude", "script", "M01.json"))
        wants = tc.cs.picture_of(next(s for s in sc["screens"] if s["id"] == "s01"))["shows"]
        own = {"source": "Novikontas old course", "url_or_origin": "1. Liquefied Gas tankers.pptx, slide 13", "catalogue_id": "p0025",
               "rights_state": "OWNER_CLEARED", "description": "x", "visually_verified": "yes - a gas carrier at sea 2026-11-12",
               "marks_seen": "none"}

        def looked(**kw):
            meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
            meta["mid.png"] = dict(own, **kw)
            tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
            return precheck.check(c, 1)[0], precheck.check(c, 1, rebuild=True)
        must, _ = looked(description=wants, shows=wants, visually_verified="yes - %s 2026-11-12" % wants)
        check("a photograph whose record is the script's wanted picture word for word stops the build",
              any("word for word" in x for x in must), must)
        must, _ = looked(description="One cutaway of an SPB tank: dome, swash bulkhead, insulation, inner hull")
        check("... and one whose record names little of what the slide's picture names (an SPB cutaway on the slide naming "
              "a gas-fuelled ship bunkering)", any("has little of what the slide's picture names" in x for x in must), must)
        must, _ = looked(description="One cutaway of an SPB tank", fits_slide="no - one tank, not the ship bunkering")
        check("... and one its opener said does not fit", any("does not show what the slide names" in x for x in must), must)
        must, _ = looked(description="A gas-fuelled ship bunkering LNG from a truck on the quay")
        check("... one that shows what the slide names goes", must == [], must)
        must, (_, notes) = looked(description="A gas-fuelled ship bunkering alongside", marks_seen="Shipfax (c) Mac Mackay")
        check("a third party's watermark on a photograph its record calls the course's own stops the build - a rebuild too",
              any("third party's mark" in x for x in must) and any("third party's mark" in x for x in _), (must, _))
        must, _ = looked(description="A gas-fuelled ship bunkering alongside", marks_seen=None)
        check("... and the course's own photograph with no watermark looked for stops a new build",
              any("watermark or credit" in x for x in must), must)
        must, _ = looked(description="A gas-fuelled ship bunkering alongside, its parts labelled", printed_text="HOSE, MANIFOLD",
                         enlarged="Real-ESRGAN realesrgan-x4plus on this computer, from 398 x 500 to 1592 x 2000")
        check("a photograph with printed labels enlarged by Real-ESRGAN stops the build - its letters come out wrong",
              any("Real-ESRGAN, which makes them sharp and wrong" in x for x in must), must)
        must, (_, notes) = looked(visually_verified="")
        check("... a rebuild's photographs nobody opened are notes, never a stop",
              any("nobody has recorded opening it" in x for x in must) and not any("nobody has recorded" in x for x in _)
              and any("nobody has recorded" in x for x in notes), (_, notes))
        meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
        meta["mid.png"] = dict(tc.PHOTO_META["ship.jpg"], description="mid.png", url_or_origin="https://example.org/mid.png")
        tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)

        print("\n-- the trainee task pages' pictures")
        figs = os.path.join(md, "assets", "fig")
        door = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400"><rect x="0" y="0" width="600" height="400" '
                'fill="#eee"/><rect x="90" y="100" width="240" height="40" fill="#9ab"/><polygon points="1,2 3,4 5,6"/>'
                '<g id="hs-a" data-name="%s"><rect x="392" y="250" width="50" height="110" fill="#678"/>'
                '<rect class="hit" x="392" y="250" width="50" height="110" fill="#fff" fill-opacity="0.01"/></g>'
                '<g id="hs-b" data-name="Fixed window on the%s front"><rect class="hit" x="90" y="100" width="240" height="40"/></g></svg>')
        io.open(os.path.join(figs, "q_front.svg"), "w", encoding="utf-8").write(door % ("Air intake on the outboard side", " accommodation"))
        io.open(os.path.join(figs, "m_front.svg"), "w", encoding="utf-8").write(door % ("Entrance on the outboard side, 5 m from the front", ""))
        tc.build_of(c, lambda b: (b["screens"].setdefault("q01", {}).update(figure="assets/fig/q_front.svg"),
                                  b["screens"].setdefault("m01", {}).update(figure="assets/fig/m_front.svg")))
        code, out = run(PRE, c, "--module", "1")
        check("a task page's drawing with no _figure_meta.json entry stops the build - not first found by the QA after it",
              code == 1 and "assets/fig/q_front.svg (q01's picture) has no entry in assets/fig/_figure_meta.json" in out, out)
        check("... and two task pages on one drawing that name the same part differently stop it (an air intake on one "
              "question, an entrance on the next); a name said a little differently does not",
              "are the same drawing, but the part at one place is" in out and "\"Air intake on the outboard side\" on q01" in out
              and "\"Entrance on the outboard side, 5 m from the front\" on m01" in out and "Fixed window" not in out, out)
        rec = {"origin": "authored diagram", "rights_state": "PROJECT_OWNED", "shows": "x", "teaching_purpose": "x", "used_in": "x",
               "visually_verified": "yes - read 2026-11-12"}
        tc.cs.save(os.path.join(figs, "_figure_meta.json"), {"q_front.svg": rec, "m_front.svg": rec})
        io.open(os.path.join(figs, "m_front.svg"), "w", encoding="utf-8").write(door % ("Air intake on the outboard side", ""))
        code, out = run(PRE, c, "--module", "1")
        check("... with their records and one name for the part, nothing stops it", code == 0, out)
        tc.build_of(c, lambda b: (b["screens"]["q01"].pop("figure"), b["screens"]["m01"].pop("figure")))
        c3, md3 = course(tmp, "mid1000", sheet={"s01": {"figure": "assets/img/mid.png"}}, photos={"mid.png": (1000, 700)})
        code, out = run(PRE, c3, "--module", "1")
        check("a 1000 px photograph is a note - under 1024 px a larger original would be sharper - never a stop",
              code == 0 and "1 photograph(s) found under 1024 px" in out and "mid.png 1000x700" in out, out)
        c3, md3 = course(tmp, "mid700", sheet={"s01": {"figure": "assets/img/mid.png"}}, photos={"mid.png": (700, 500)})
        code, out = run(PRE, c3, "--module", "1")
        check("a 700 px photograph still stops the build", code == 1 and "mid.png (on s01) is only 700 x 500 px" in out, out)
        c3, md3 = course(tmp, "unclear", sheet={"s01": {"figure": "assets/img/book.png"}}, photos={"book.png": (1800, 1200)})
        meta = tc.cs.load(os.path.join(md3, "assets", "img", "_photo_meta.json"))
        meta["book.png"]["rights_state"] = "RIGHTS_REVIEW_REQUIRED"
        tc.cs.save(os.path.join(md3, "assets", "img", "_photo_meta.json"), meta)
        code, out = run(PRE, c3, "--module", "1")
        check("a picture whose rights are not cleared does not stop the build - it is in the module's notes, publishing refused",
              code == 0 and "book.png" not in out.split("PRE-CHECK notes")[0] and "rights not cleared" in out
              and "book.png (on s01)" in out and "publishing to the tablets is refused" in out, out)
        io.open(os.path.join(md, "assets", "img", "mid.png"), "wb").write(tc.png(2400, 1600))
        check("a new, larger picture put in its place is judged as itself - the old kept original no longer counts",
              found_size(os.path.join(md, "assets", "img", "mid.png"), keep) == (2400, 1600))
        code, out = run(ASSETS, os.path.join(md, "assets", "img"))
        check("the asset check (photo-finding time) has no size warning for the 2400 px one",
              "under 1600 px" not in out and "no enlargement makes it sharp" not in out, out)
        c2, md2 = course(tmp, "assets", photos={"a.png": (500, 400), "b.png": (1000, 700), "c.png": (1200, 800)})
        code, out = run(ASSETS, os.path.join(md2, "assets", "img"))
        check("the asset check warns on a photograph under 800 px - no enlargement makes it sharp",
              "only 500 x 400 px - no enlargement makes it sharp" in out, out)
        check("... and on one under 1024 px - the original would be sharper", "1000 x 700 px - under 1024 px" in out, out)
        check("... and has no size warning for a 1200 px one", "1200 x 800 px" not in out, out)

        print("\n-- the pre-check finds what would fail the build (point 1)")
        c, md = course(tmp, "missing", sheet={"s02": {"figure": "assets/fig/none.svg"}})
        code, out = run(PRE, c, "--module", "1")
        check("a picture the build sheet names that is not there", code == 1 and "s02) : its figure assets/fig/none.svg".replace(") :", "):") in out, out)
        c, md = course(tmp, "parked", sheet={"s02": {"figure": "assets/img/back.png"}}, photos={"back.png": (1800, 1200)})
        os.makedirs(os.path.join(md, "assets", "img", "_unused"))
        os.replace(os.path.join(md, "assets", "img", "back.png"), os.path.join(md, "assets", "img", "_unused", "back.png"))
        code, out = run(PRE, c, "--module", "1")
        check("2.66.0: a picture waiting in assets/img/_unused/ is there - the build brings it back (gas M02 run 5 was stopped)",
              code == 0 and "waits in assets/img/_unused/ - the build brings it back" in out, out)
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
        check("96 words with no picture beside them is a note (the word guideline), never a stop",
              code == 0 and "(s05): 96 words and no picture" in out and "past 120 words the build shows it in steps" in out, out)
        short = lambda i: {"id": "x%d" % i, "kind": "slide", "title": "Point %d" % i, "visual_kind": "none", "minutes": 1,
                           "text": "A short point."}
        scr = json.loads(json.dumps(tc.SCREENS))
        scr[4:4] = [short(1), short(2), short(3)]
        c, md = course(tmp, "three", screens=scr)
        code, out = run(PRE, c, "--module", "1")
        check("three teaching slides in a row without a picture are fine (L61's 'two in a row' removed, 2.116.0)",
              code == 0 and "three teaching slides in a row" not in out, out)
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
        check("... a fix under a minute says its seconds, never \"0 min\"", "this fix took 24 s" in cf_timing.fix_line(24))

        print("\n-- 2.67.0: a slide whose own layout spills is built again with its words in parts - not a builder's run")
        import build_module as bm
        import compile_module as cm
        c, md = course(tmp, "spill")
        run(tc.COMPILE, c, "--module", "1", "--no-drawing-check")
        sc = tc.cs.load(os.path.join(c, "working_claude", "script", "M01.json"))
        sheet = tc.cs.load(cm.build_path(c, 1))["screens"]
        sid = next(x["id"] for x in sc["screens"] if x["kind"] == "slide" and (sheet.get(x["id"]) or {}).get("figure")
                   and not (sheet.get(x["id"]) or {}).get("template") and len(tc.cs.lines_of(x.get("text"))) >= 2)
        deck_html = io.open(os.path.join(md, "presentation", "index.html"), encoding="utf-8").read()
        # 2.116.0 (operator, 2026-11-09): the automatic paging of a slide whose own layout spilled (spilled_own / parts_out, and the
        # pre-check fallback that overrode a requested template) was the rule - removed: the factory never pages or moves the words
        check("2.116.0: the factory has no automatic words-in-parts fallback any more (spilled_own, parts_out, wants_parts are gone)",
              not hasattr(bm, "spilled_own") and not hasattr(bm, "parts_out") and not hasattr(cm, "wants_parts"))
        tag = re.search(r'<section [^>]*data-script="%s"[^>]*>' % sid, deck_html).group(0)
        check("... a slide the compiler laid out itself is never built content-in-parts unasked", 'data-template="content-in-parts' not in tag, tag)
        tc.build_of(c, lambda b: b["screens"][sid].update({"template": "explain-figure"}))
        run(tc.COMPILE, c, "--module", "1", "--no-drawing-check")
        tag2 = re.search(r'<section [^>]*data-script="%s"[^>]*>' % sid, io.open(os.path.join(md, "presentation", "index.html"),
                                                                               encoding="utf-8").read()).group(0)
        check("... and a template the builder asked for by name is built as asked", 'data-template="explain-figure' in tag2, tag2)

        print("\n-- a rebuild of a built module is a fix (fix.py rebuild)")
        c, md = course(tmp, "rebuild")
        run(tc.COMPILE, c, "--module", "1", "--no-drawing-check")
        t = time.time()
        code, out = run(FIX, "rebuild", c, "--modules", "1")
        check("fix.py rebuild: the module built again from its approved words, then ONE check - the build's own audits at "
              "1280x800, 1024x768 and 1280x720 (not the 16 px sweep) - and the package check",
              "Module 1: rebuilt from its approved words" in out and "One check for the rebuilt modules (1) - the build's own "
              "audits, 1280x800, 1024x768 and 1280x720" in out and ("Module 1: the audits pass" in out or "For the full build: module(s) 1" in out)
              and "layout at 1280x800" not in out, out[-900:])
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
              "Module 1: rebuilt from its approved words" in out and "1 picture(s) under 800 px" in out
              and "tiny.png 300x200" in out, out[-900:])
        code, out = run(BUILD, c, "--module", "1", "--no-review", "--no-course-pages")
        check("... and build_module.py on a module built before (the full build fix.py names) is not stopped by it either",
              "nothing built: the pre-check" not in out and "Pre-check: 1 picture(s) under 800 px" in out,
              out[-900:])
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
