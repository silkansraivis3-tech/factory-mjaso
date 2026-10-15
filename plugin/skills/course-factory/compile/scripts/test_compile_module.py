# -*- coding: utf-8 -*-
"""test_compile_module - the deck is built from the approved script, the same way for every module.

    python test_compile_module.py

Pinned:
  * the built deck says exactly the approved words - check_script_match.py --part instructor passes on it;
  * every layout comes from the factory's own vocabulary: split -> two-col, visual_full + photo -> .slide.photo,
    visual_wide -> stage or two-col wide-right, a task slide -> activity with data-task-href to the set's page;
  * the frame (landing, chrome) is the factory's gb_shell.html, the style files and engine the factory's own;
  * a photograph's credit line comes from _photo_meta.json; an .svg / .html figure is placed in the slide as it is;
  * the same script and build sheet always give the same bytes;
  * an unapproved script builds nothing (only a --draft preview, which exits 1);
  * a deck changed by hand, or built by hand before the compiler, is never overwritten without --force;
  * a missing picture file is reported, never invented;
  * no link inside a slide (L35: the deck never navigates away).
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
SKILL = os.path.dirname(os.path.dirname(HERE))
SKILLS = os.path.dirname(SKILL)
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import content_script as cs  # noqa: E402

COMPILE = os.path.join(HERE, "compile_module.py")
MATCH = os.path.join(SKILL, "scripts", "check_script_match.py")
DESIGN = os.path.join(SKILLS, "course-module-ui", "scripts", "design_system.py")
PASS, FAIL = [], []

SCREENS = [
    {"id": "s01", "kind": "slide", "title": "Module 1 · Gas as fuel", "layout": "visual_full", "visual_kind": "photo",
     "text": "Some ships burn gas as fuel.\nIn this module:\n• the fuels\n• the spaces\nAfter 40 minutes you can name each space.",
     "visual": "A gas-fuelled ship bunkering - a real photograph.", "notes": "- Ask who has sailed on one.", "minutes": 3},
    {"id": "s02", "kind": "slide", "title": "The Code", "layout": "split", "visual_kind": "comparison",
     "text": "The Code sets the rules for gas-fuelled ships.\nMandatory since 2017.\nFlashpoint below 60 °C.",
     "visual": "Thermometer scale.", "notes": "- Stress the 60 °C line.", "minutes": 4},
    {"id": "s03", "kind": "slide", "title": "Five new spaces", "layout": "visual_wide", "visual_kind": "interactive_diagram",
     "text": "Fuel tank.\nTank connection space.\nFuel preparation room.", "visual": "General arrangement.", "notes": "- Tap each space.", "minutes": 5},
    {"id": "s04", "kind": "slide", "title": "Two barriers", "layout": "visual_wide", "visual_kind": "model_3d",
     "text": "Two ways to protect the engine room:\nGas safe machinery space - a single failure cannot release gas into the space, "
             "because the gas pipe runs inside an outer pipe or duct where a leak is held, ventilated and detected.\n"
             "ESD-protected machinery space - a single failure may release gas; if gas is detected, ignition sources are shut down.",
     "visual": "3D hull section.", "notes": "- ESD in module 14.", "minutes": 4},
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the new spaces",
     "text": "Self-check on your tablet now.\nYour score is for you only.", "notes": "- Press OPEN TASK.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "question": "Where is the fuel prepared?", "options": ["Fuel preparation room", "Bridge"],
     "correct": "A", "feedback": "Pumps and vaporizers are there.", "mechanic": "single_choice"},
    {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - Module 1",
     "text": "Module check on your tablet now.", "notes": "- Press OPEN TASK.", "minutes": 5},
    {"id": "m01", "kind": "module-check", "set": "MC", "question": "Which space surrounds the tank valves?", "options": ["Tank connection space", "Galley"],
     "correct": "A", "feedback": "It holds every tank connection.", "mechanic": "single_choice"},
]
SVG = '<?xml version="1.0"?>\n<svg viewBox="0 0 100 50" role="img" aria-label="Scale"><rect width="100" height="50"/><text x="5" y="20">60 °C</text></svg>\n'
FRAGMENT = '<div class="fig-ga" data-stage><svg viewBox="0 0 10 10"><circle r="4" cx="5" cy="5"/></svg></div>'
PHOTO_META = {"ship.jpg": {"source": "Wikimedia Commons", "author": "Jane Doe (Wikimedia Commons user), own work",
                           "licence": "CC BY-SA 4.0", "attribution_required": True, "description": "A ship taking gas."}}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(*args):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def script(approved=True, screens=SCREENS):
    s = {"module": 1, "title": "IGF ships", "course_language": "English", "operator_language": "en",
         "minutes_allocated": 25, "status": "draft", "screens": json.loads(json.dumps(screens))}
    if approved:
        s.update(status="approved", approved_hash=cs.content_hash(s), approved_by="Test")
    return s


def new_course(tmp, sc, build=True):
    c = os.path.join(tmp, "course")
    sdir = os.path.join(c, "working_claude", "script")
    os.makedirs(sdir)
    cs.save(os.path.join(sdir, "M01.json"), sc)
    md = os.path.join(c, "modules", "module01")
    os.makedirs(md)
    code, out = run(DESIGN, "install", md)
    assert code == 0, out
    os.makedirs(os.path.join(md, "assets", "img"))
    os.makedirs(os.path.join(md, "assets", "fig"))
    io.open(os.path.join(md, "assets", "img", "ship.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
    cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), PHOTO_META)
    io.open(os.path.join(md, "assets", "fig", "scale.svg"), "w", encoding="utf-8").write(SVG)
    figs = os.path.join(c, "working_claude", "figures", "M01")         # drawing source - never shipped
    os.makedirs(figs)
    io.open(os.path.join(figs, "ga.html"), "w", encoding="utf-8").write(FRAGMENT)
    io.open(os.path.join(figs, "hull.svg"), "w", encoding="utf-8").write(SVG.replace("Scale", "Hull"))
    if build:
        cs.save(os.path.join(sdir, "M01.build.json"), {
            "module": 1, "landing_rule": "Basic training · IGF Code",
            "screens": {"s01": {"figure": "assets/img/ship.jpg"}, "s02": {"figure": "assets/fig/scale.svg"},
                        "s03": {"figure": "ga.html"}, "s04": {"figure": "hull.svg", "dark": True}}})
    return c, md


def deck(md):
    return io.open(os.path.join(md, "presentation", "index.html"), encoding="utf-8").read()


def section(page, sid):
    m = re.search(r'<section [^>]*id="%s".*?</section>' % sid, page, re.S)
    return m.group(0) if m else ""


def main():
    tmp = tempfile.mkdtemp(prefix="compile_")
    try:
        # ---- a clean build
        os.makedirs(os.path.join(tmp, "a"))
        c, md = new_course(os.path.join(tmp, "a"), script())
        code, out = run(COMPILE, c, "--module", "1")
        check("an approved script with every picture builds clean (exit 0)", code == 0, out)
        page = deck(md)
        code, out = run(MATCH, c, "--module", "1", "--part", "instructor")
        check("check_script_match --part instructor passes on the built deck", code == 0, out)
        check("the deck is marked as generated, from which script", "GENERATED by course-factory" in page and "M01.json" in page)
        check("the factory's own style files and engine are used",
              all('href="../assets/%s"' % x in page for x in ("gb_tokens.css", "gb_shell.css", "gb_compose.css"))
              and '<script src="../assets/gb_deck.js"></script>' in page)
        shell = io.open(os.path.join(SKILLS, "course-module-ui", "templates", "gb_shell.html"), encoding="utf-8").read()
        chrome = shell[shell.find('<div id="chrome">'):shell.find("</div>", shell.find('id="btnExit"')) + 6]
        check("the chrome is the factory frame's, word for word", chrome and chrome in page)
        check("the Android Back hook is there", '<a class="gbt-topback" href="../START_HERE_EXTENDED.html" hidden>Back</a>' in page)
        s01, s02, s03, s04 = (section(page, x) for x in ("s01", "s02", "s03", "s04"))
        check("visual_full + a photograph -> .slide.photo with photo-wrap and photo-copy",
              'class="slide photo"' in s01 and '<div class="photo-wrap"><img src="../assets/img/ship.jpg"' in s01 and "photo-copy" in s01)
        check("the photo's credit comes from _photo_meta.json", '<div class="credit">Photo: Jane Doe · Wikimedia Commons · CC BY-SA 4.0</div>' in s01, s01)
        sys.path.insert(0, HERE)
        import compile_module as cm
        bl = "\n".join(cm.words_html(["Ways named in the Code:", "• reliquefy", "• burn it", "Venting: not acceptable."]))
        check("a line starting with • becomes a list item (bullet drawn by the list)",
              '<li data-script-field="text" data-i="2">reliquefy</li>' in bl and "•" not in bl and bl.count('class="lead"') == 2, bl)
        check("over a photograph a • line stays a lead line, bullet kept - the shared look has no list style on photos",
              '<p class="lead" data-script-field="text" data-i="3">• the fuels</p>' in s01 and "<ul" not in s01, s01)
        check("every line is numbered in script order, so a stepping figure can light it up",
              re.findall(r'data-i="(\d+)"', s02) == ["1", "2", "3"] and re.findall(r'data-i="(\d+)"', s01) == ["1", "2", "3", "4", "5"])
        check("a fragment that is already a .fill is not wrapped again (its contents would get no width)",
              cm.fill('<div class="fill m01-3d">x</div>') == '<div class="fill m01-3d">x</div>' and cm.fill("<svg/>") == '<div class="fill"><svg/></div>')
        check("the footer's title is cut at a whole word", 'data-foot="M01 · IGF SHIPS · NOVIKONTAS"' in s02
              and cm.compile_deck(dict(script(), title="IGF ship design and operational characteristics"), {}, md, None, "x", True)[0]
              .count('data-foot="M01 · IGF SHIP DESIGN AND OPERATIONAL · NOVIKONTAS"') == 6)
        check("split -> two-col: the statement, its support list, the picture in .fill",
              'slide-body two-col"' in s02 and 'class="statement"' in s02 and 'class="support"' in s02 and '<div class="fill"><svg viewBox' in s02)
        check("an .svg figure goes in as it is, without its XML prolog", "<?xml" not in page and "60 °C</text>" in s02)
        check("visual_wide with few words -> stage; an .html fragment placed as it is",
              'slide-body stage"' in s03 and FRAGMENT in s03)
        check("visual_wide with many words -> two-col wide-right; dark from the build sheet",
              "two-col wide-right" in s04 and 'class="slide dark"' in s04)
        t01, t02 = section(page, "t01"), section(page, "t02")
        check("a task slide -> activity, Task, its code, data-task-href to tasks/sc1_<title>.html",
              'class="slide dark activity"' in t01 and 'data-kind="Task"' in t01 and 'data-activity="SC1"' in t01
              and 'data-task-href="../tasks/sc1_the_new_spaces.html"' in t01 and '<p class="act-code" data-script-ignore>SC1</p>' in t01, t01)
        check("the module check slide -> Check, ../assessment/check.html",
              'data-kind="Check"' in t02 and 'data-task-href="../assessment/check.html"' in t02)
        check("every slide has data-title and the instructor notes as data-cue",
              all('data-title="' in section(page, x) and 'data-cue="- ' in section(page, x) for x in ("s01", "s02", "s03", "s04", "t01", "t02")))
        check("every teaching slide says its picture kind (data-visual)", 'data-visual="model_3d"' in s04 and 'data-visual="photo"' in s01)
        check("no question is ever on a slide", "q01" not in page and "m01" not in re.sub(r"(?i)M01", "", page))
        check("no link inside a slide", not re.search(r"<main.*<a\s[^>]*href", page, re.S))
        check("the landing card shows the course line, the module, the minutes and the tasks",
              "Basic training · IGF Code" in page and "25 min" in page and "Self-check SC1" in page and "Module check MC" in page)
        check("figure hooks come from window.GB_HOOKS", "hooks: window.GB_HOOKS || {}" in page)

        # ---- the same in, the same out
        code, out = run(COMPILE, c, "--module", "1")
        check("compiling again gives the same bytes", code == 0 and deck(md) == page, out)

        # ---- a hand edit is never overwritten
        io.open(os.path.join(md, "presentation", "index.html"), "a", encoding="utf-8").write("<!-- hand -->")
        code, out = run(COMPILE, c, "--module", "1")
        check("a deck changed by hand is not overwritten (exit 2)", code == 2 and deck(md).endswith("<!-- hand -->"), out)
        code, out = run(COMPILE, c, "--module", "1", "--force")
        check("--force overwrites it", code == 0 and deck(md) == page, out)

        # ---- a hand-built deck from before the compiler is protected too
        os.makedirs(os.path.join(tmp, "b"))
        c2, md2 = new_course(os.path.join(tmp, "b"), script())
        os.makedirs(os.path.join(md2, "presentation"))
        io.open(os.path.join(md2, "presentation", "index.html"), "w", encoding="utf-8").write("<html>hand-built</html>")
        code, out = run(COMPILE, c2, "--module", "1")
        check("a hand-built deck with no compile record is not overwritten", code == 2 and deck(md2) == "<html>hand-built</html>", out)

        # ---- not approved
        os.makedirs(os.path.join(tmp, "c"))
        c3, md3 = new_course(os.path.join(tmp, "c"), script(approved=False))
        code, out = run(COMPILE, c3, "--module", "1")
        check("an unapproved script builds nothing (exit 2)", code == 2 and not os.path.exists(os.path.join(md3, "presentation", "index.html")), out)
        code, out = run(COMPILE, c3, "--module", "1", "--draft")
        check("--draft builds a preview, marked, exit 1", code == 1 and "DRAFT - NOT APPROVED" in deck(md3), out)

        # ---- a missing picture is reported, never invented
        os.makedirs(os.path.join(tmp, "d"))
        c4, md4 = new_course(os.path.join(tmp, "d"), script(), build=False)
        code, out = run(COMPILE, c4, "--module", "1")
        check("no build sheet: the deck is built, every missing picture is listed (exit 1)",
              code == 1 and out.count("has no picture file in the build sheet") == 4, out)
        code, out = run(MATCH, c4, "--module", "1", "--part", "instructor")
        check("... and its words still match the script", code == 0, out)
        code, out = run(COMPILE, c4, "--module", "1", "--init-build")
        check("--init-build writes a starter build sheet",
              code == 0 and os.path.isfile(os.path.join(c4, "working_claude", "script", "M01.build.json")), out)
        sheet = cs.load(os.path.join(c4, "working_claude", "script", "M01.build.json"))
        check("the starter build sheet lists every slide with an empty figure", sorted(sheet["screens"]) == ["s01", "s02", "s03", "s04", "t01", "t02"]
              and sheet["screens"]["s04"] == {"figure": "", "visual_kind": "model_3d"})
        code, out = run(COMPILE, c4, "--module", "1", "--init-build")
        check("--init-build never replaces an existing build sheet", code == 2, out)

        # ---- an .html drawing in the module folder would ship as a page - refused
        os.makedirs(os.path.join(tmp, "e"))
        c5, md5 = new_course(os.path.join(tmp, "e"), script())
        shutil.copy(os.path.join(c5, "working_claude", "figures", "M01", "ga.html"), os.path.join(md5, "assets", "fig", "ga.html"))
        bp = os.path.join(c5, "working_claude", "script", "M01.build.json")
        sheet = cs.load(bp)
        sheet["screens"]["s03"]["figure"] = "assets/fig/ga.html"
        cs.save(bp, sheet)
        code, out = run(COMPILE, c5, "--module", "1")
        check("an .html drawing in the module folder is refused - it would go to the tablets as a page",
              code == 1 and "classroom would take it for a page" in out and FRAGMENT not in deck(md5), out)

        # ---- a changed word is still caught on a compiled deck
        p = os.path.join(md, "presentation", "index.html")
        io.open(p, "w", encoding="utf-8").write(page.replace("Mandatory since 2017.", "Mandatory since 2016."))
        code, out = run(MATCH, c, "--module", "1", "--part", "instructor")
        check("check_script_match still fails a changed word", code == 1 and "2016" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
