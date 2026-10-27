# -*- coding: utf-8 -*-
"""test_tiles - several photographs on one slide, built by the compiler; the module's photographs put on the slides their
records name at --init-build (2.67.0).

    python test_tiles.py
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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_compile_module as tc  # noqa: E402
import compile_module as cm  # noqa: E402

AUDITS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "course-module-ux", "measure", "scripts", "run_audits.py")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def photos(md, names, purpose=None):
    meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
    for k, n in enumerate(names):
        io.open(os.path.join(md, "assets", "img", n), "wb").write(tc.png(1800, 1200, (40 * k, 90, 150)))
        rec = dict(tc.PHOTO_META["ship.jpg"], description="Picture %s." % n, url_or_origin="https://example.org/" + n)
        if purpose:
            rec["teaching_purpose"] = purpose[k]
        meta[n] = rec
    tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)


def main():
    tmp = tempfile.mkdtemp(prefix="tiles_")
    try:
        os.makedirs(os.path.join(tmp, "a"))
        c, md = tc.new_course(os.path.join(tmp, "a"), tc.script(screens=tc.SCREENS))
        photos(md, ["t1.png", "t2.png", "t3.png", "t4.png"])
        sc = tc.cs.load(os.path.join(c, "working_claude", "script", "M01.json"))
        sid = next(x["id"] for x in sc["screens"] if x["kind"] == "slide" and len(tc.cs.lines_of(x.get("text"))) >= 2)
        tc.build_of(c, lambda b: b["screens"].update({sid: {"tiles": ["assets/img/t1.png", {"photo": "assets/img/t2.png", "caption": "The shipper's SDS"},
                                                                     "assets/img/t3.png", "assets/img/t4.png"]}}))
        code, out = run(tc.COMPILE, c, "--module", "1")
        deck = io.open(os.path.join(md, "presentation", "index.html"), encoding="utf-8").read()
        sec = re.search(r'<section [^>]*data-script="%s".*?</section>' % sid, deck, re.S).group(0)
        tiles = re.findall(r'<figure class="lt-tile" data-zoom="button">.*?</figure>', sec, re.S)
        check("\"tiles\": the compiler builds the slide's picture - four photographs, each opening full screen", len(tiles) == 4, sec[:900])
        check("... each with its own record full screen (what it shows, its credit) and its caption when one is given",
              all('data-about="Picture t' in x and "data-credit=" in x for x in tiles) and "<figcaption>The shipper&#x27;s SDS</figcaption>" in sec,
              tiles[:2])
        check("... and nothing to fix on it", not re.search(r"\(%s\)[^\n]*(tile|picture)" % sid, out), out[-900:])
        a_code, a_out = run(AUDITS, os.path.join(md, "presentation", "index.html"), "--viewport", "1024x768")
        check("... the slide passes the layout audits at 1280 x 800 and 1024 x 768", "slide" not in a_out.split("run_audits")[0].lower()
              or a_code == 0, a_out[-800:])
        tc.build_of(c, lambda b: b["screens"][sid].update({"tiles_as": "strips"}))
        run(tc.COMPILE, c, "--module", "1")
        sec = re.search(r'<section [^>]*data-script="%s".*?</section>' % sid,
                        io.open(os.path.join(md, "presentation", "index.html"), encoding="utf-8").read(), re.S).group(0)
        check("\"tiles_as\": \"strips\" - the cuts of one document stacked, numbered 1 2 3 4", 'class="lt-strips"' in sec
              and re.findall(r'<b class="lt-n">(\d)</b>', sec) == ["1", "2", "3", "4"], sec[:600])
        tc.build_of(c, lambda b: b["screens"][sid].update({"tiles": ["assets/img/t1.png", "assets/img/gone.png"]}))
        code, out = run(tc.COMPILE, c, "--module", "1")
        check("a tile that is not there is said", "its tile assets/img/gone.png is not in the module folder" in out, out[-600:])
        code, out = run(os.path.join(HERE, "precheck.py"), c, "--module", "1")
        check("... and the pre-check stops the build on it, before anything is built", code == 1 and "gone.png" in out, out)

        print("\n-- --init-build: the module's photographs go on the slides their records name")
        os.makedirs(os.path.join(tmp, "b"))
        c2, md2 = tc.new_course(os.path.join(tmp, "b"), tc.script(screens=tc.SCREENS))
        slides = [x["id"] for x in tc.cs.load(os.path.join(c2, "working_claude", "script", "M01.json"))["screens"] if x["kind"] == "slide"]
        one, many = slides[0], slides[1]
        photos(md2, ["p_one.png", "p_a.png", "p_b.png", "p_c.png"],
               purpose=["%s - the ship" % one, "%s - group A" % many, "%s - group B" % many, "%s - group C" % many])
        os.remove(cm.build_path(c2, 1))
        tc.gate_fixture.open_gate(c2)
        run(tc.COMPILE, c2, "--module", "1", "--init-build")
        sheet = tc.cs.load(cm.build_path(c2, 1))["screens"]
        check("one photograph that names a slide is its picture", sheet[one].get("figure") == "assets/img/p_one.png"
              and "linked by --init-build" in sheet[one].get("_photo", ""), sheet[one])
        check("... several are its tiles (gas M02: 24 photographs found for its slides went on none)",
              sheet[many].get("tiles") == ["assets/img/p_a.png", "assets/img/p_b.png", "assets/img/p_c.png"], sheet[many])
        import build_module as bm
        check("(merge, 2.72.7) a slide whose picture is its tiles is no starter blank - the build is not stopped on it",
              not any(many in ids for ids, _ in bm.starter_blanks(c2, 1)), bm.starter_blanks(c2, 1))

        print("\n-- (merge, 2.72.7) a record that only says where a photograph was SHOWN does not replace a planned drawing")
        os.makedirs(os.path.join(tmp, "c"))
        c3, md3 = tc.new_course(os.path.join(tmp, "c"), tc.script(screens=tc.SCREENS))
        sc3 = tc.cs.load(os.path.join(c3, "working_claude", "script", "M01.json"))
        drawn = next(x["id"] for x in sc3["screens"] if x["kind"] == "slide" and x.get("visual_kind") == "interactive_diagram")
        shot = next(x["id"] for x in sc3["screens"] if x["kind"] == "slide" and x.get("visual_kind") == "photo")
        photos(md3, ["u_a.png", "u_b.png", "u_c.png"])
        meta = tc.cs.load(os.path.join(md3, "assets", "img", "_photo_meta.json"))
        meta["u_a.png"]["used_in"] = "M01 presentation, slide %s" % drawn         # shown in the drawing's photo row before
        meta["u_b.png"]["used_in"] = "M01 presentation, slide %s" % drawn
        meta["u_c.png"]["used_in"] = "M01 presentation, slide %s" % shot
        tc.cs.save(os.path.join(md3, "assets", "img", "_photo_meta.json"), meta)
        os.remove(cm.build_path(c3, 1))
        tc.gate_fixture.open_gate(c3)
        code, out = run(tc.COMPILE, c3, "--module", "1", "--init-build")
        sheet3 = tc.cs.load(cm.build_path(c3, 1))["screens"]
        check("the planned diagram (%s) keeps its starter drawing, not the photos only shown there before (the 2.66.5 run's M02 "
              "s03 / s07 / s12 became photo tiles)" % drawn, not sheet3[drawn].get("tiles")
              and str(sheet3[drawn].get("figure") or "").endswith((".kit.json", ".html")), sheet3[drawn])
        check("... a slide that plans a photograph takes the one its record names", sheet3[shot].get("figure") == "assets/img/u_c.png",
              sheet3[shot])
        check("... and a fresh module is not 'seeded' from the sheet just written (the course is its own predecessor only for "
              "a module it built before)", "seeded from the predecessor" not in out, out[-600:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
