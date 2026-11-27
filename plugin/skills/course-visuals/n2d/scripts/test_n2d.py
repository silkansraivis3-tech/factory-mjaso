#!/usr/bin/env python3
"""test_n2d.py - the 2D kit for new courses.

Without a browser: every demo figure passes the check; the check refuses what a form cannot hold (too many things, long
names, a thing with no picture, a tag too long, a step naming a line the slide has not); a module's system ("world") is
joined in; the things list the check reads is the one n2d-things.js draws; code chooses the figure from the slide's words
and the starter names what the writer writes.
In a hidden browser: every demo figure walked step by step in a projector box and a tablet box, N2D.audit clean at the
end of each step (no words over words, none cut at the edge), and a step lighting the slide's line in a deck.

    python -I test_n2d.py            about a minute
    python -I test_n2d.py --quick    the checks only, no browser
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
KIT = HERE.parent
SKILLS = KIT.parents[1]
sys.path.insert(0, str(HERE))
import figure_plan  # noqa: E402
import n2d_check  # noqa: E402

FAILS = []


def check(what, ok, detail=""):
    print("  %s  %s%s" % ("ok  " if ok else "FAIL", what, "" if ok else "  -> %s" % str(detail)[:600]))
    if not ok:
        FAILS.append(what)


def demos():
    text = io.open(KIT / "demo-specs.js", encoding="utf-8").read()
    return json.loads(text[text.index("["):text.rindex("]") + 1])


def test_checks():
    print("the check")
    for d in demos():
        check("demo passes: %s" % d["title"], not n2d_check.check(d["spec"]), n2d_check.check(d["spec"]))
    base = {"form": "path", "say": "A reading travels to shore.", "things": [{"id": "s", "is": "sensor", "name": "Sensor"},
            {"id": "o", "is": "office", "name": "Office ashore"}], "links": ["s>o"], "steps": [{"line": 1, "go": "s>o"}]}
    check("a plain path passes", not n2d_check.check(base), n2d_check.check(base))
    many = dict(base, things=[{"id": "t%d" % i, "is": "pc", "name": "PC %d" % i} for i in range(8)], links=[], steps=[{"line": 1}])
    check("8 things refused", any("at most 7" in p for p in n2d_check.check(many)))
    six = [{"id": "t%d" % i, "is": "pc", "name": "PC %d" % i} for i in range(6)]
    check("a single chain of 6 folds and passes", not n2d_check.check(dict(base, things=six, links=["t0>t1>t2>t3>t4>t5"], steps=[{"line": 1}])))
    branch = six + [{"id": "x", "is": "sensor", "name": "Sensor"}]
    check("6 long with a branch refused (pictures would shrink past reading)",
          any("at most 5 long" in p for p in n2d_check.check(dict(base, things=branch, links=["t0>t1>t2>t3>t4>t5", "x>t2"]))))
    long_ = dict(base, things=[{"id": "s", "is": "sensor", "name": "The alarm and monitoring system"}, base["things"][1]])
    check("a 5-word name refused", any("5 words" in p for p in n2d_check.check(long_)))
    nopic = dict(base, things=[{"id": "s", "is": "flux capacitor", "name": "Unit"}, base["things"][1]])
    check("a thing with no picture refused", any("no picture" in p for p in n2d_check.check(nopic)))
    tag = dict(base, steps=[{"line": 1, "tag": {"o": "The office ashore reads it every morning"}}])
    check("a long tag refused", any("tag" in p for p in n2d_check.check(tag)))
    check("a line past the slide's refused", any("line 5" in p for p in n2d_check.check(dict(base, steps=[{"line": 5}]), n_lines=3)))
    check("a step naming a thing not drawn refused", any('"x"' in p for p in n2d_check.check(dict(base, steps=[{"line": 1, "go": "s>x"}]))))
    check("no say refused", any('"say"' in p for p in n2d_check.check(dict(base, say=""))))
    check("an unknown form refused", n2d_check.check(dict(base, form="matrix")) != [])
    world = {"bridge": {"things": [{"id": "g", "is": "gyro", "name": "Gyro"}, {"id": "r", "is": "radar", "name": "Radar"}], "links": ["g>r"]}}
    w = {"form": "path", "world": "bridge", "say": "The gyro feeds the radar.", "steps": [{"line": 1, "fail": "g"}]}
    check("a world is joined in", not n2d_check.check(w, world), n2d_check.check(w, world))
    check("an unknown world refused", any("not in the module" in p for p in n2d_check.check(w, {})))
    opt = {"form": "options", "say": "x.", "options": [{"is": "satellite", "name": "GEO"}, {"is": "mast", "name": "Mobile"}],
           "qualities": [{"name": "Reach", "values": [3, 5]}], "steps": [{"line": 1}]}
    check("a rating past 3 refused", any("0 to 3" in p for p in n2d_check.check(opt)))


def test_things():
    print("the things list")
    js = io.open(KIT / "n2d-things.js", encoding="utf-8").read()
    names = set(re.findall(r"^    ([a-z_]+): function", js[js.index("var T = {"):js.index("var ALIAS")], re.M)) - {"question"}
    alias = dict(re.findall(r"'([^']+)': '([a-z_]+)'", js[js.index("var ALIAS"):js.index("function find")]))
    alias.update(re.findall(r"\b([a-z]+): '([a-z_]+)'", js[js.index("var ALIAS"):js.index("function find")]))
    check("things.json names = the pictures n2d-things.js draws", names == set(n2d_check.THINGS["names"]),
          names ^ set(n2d_check.THINGS["names"]))
    check("things.json aliases = n2d-things.js aliases", alias == n2d_check.THINGS["alias"],
          set(alias.items()) ^ set(n2d_check.THINGS["alias"].items()))
    check("every alias names a picture", all(v in names for v in alias.values()))


def test_plan():
    print("code chooses the figure")
    cases = [
        ({"title": "Engine-room data: from sensor to shore", "text": "Sensors send readings to controllers.\nThe alarm system gathers them."}, "path"),
        ({"title": "Keep the networks apart", "text": "Segregation stops an incident.\nOT is separate from IT."}, "zones"),
        ({"title": "IT, OT and IoT", "text": "IT refers to data.\nOT controls a process."}, "zones"),
        ({"title": "Worked example: a PC with no network", "text": "No network | Lights first\nRead the port | Dark\nTest the cable | Broken"}, "steps"),
        ({"title": "Ship-to-shore connections", "text": "GEO satellite: wide cover, longer delay.\nMobile network: quick near the coast, out of reach far away."}, "options"),
        ({"title": "Two faults", "text": "Fault A: one PC has no link light.\nFault B: the firewall uplink is dark."}, "path"),
        ({"title": "True or false: a VPN makes the link faster", "text": "A VPN encrypts."}, "none"),
        ({"title": "Explore: which machine runs which job?", "text": "Drag each job to its machine."}, "task"),
        ({"title": "The devices", "text": "Switch - joins devices.", "visual": "A real photograph of a rack."}, "photo"),
        ({"title": "Starting the pump", "text": "Start the pump against the shut discharge valve: pressure builds.\nOpen it: oil flows."}, "scene:pump_line"),
        ({"title": "Crossing", "text": "The other ship is on your starboard side: you give way."}, "scene:crossing"),
        ({"title": "A falling barometer", "text": "1013 hPa at 00:00, 1012 hPa at 03:00.\n1009 hPa at 06:00, 1003 hPa at 09:00."}, "amounts"),
    ]
    for s, want in cases:
        got = figure_plan.choose(s)["form"]
        check("%s -> %s" % (s["title"], want), got == want, got)
    st = figure_plan.starter(cases[0][0])
    check("the starter: the form, one step a line, and what the writer writes in _todo",
          st["form"] == "path" and len(st["steps"]) == 2 and "things" in st["_todo"], st)
    check("a photo, a task or no figure has no starter", figure_plan.starter(cases[8][0]) is None and figure_plan.starter(cases[7][0]) is None)
    check("a starter is refused until it is written", n2d_check.check(dict(st, _todo=None)) != [])


AUDIT = """async () => { const out = []; const F = window.__demos.figs();
  for (let i = 0; i < F.length; i++) { const f = F[i];
    for (let n = 0; n < f.count; n++) { f.go(n, true); await new Promise(r => setTimeout(r, 40));
      N2D.audit(f).forEach(x => out.push(window.N2D_DEMOS[i].title + ' step ' + (n + 1) + ': ' + x)); } }
  return out; }"""

DECK = """<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="%s">
<section class="slide" id="s01"><ul><li data-i="1">One</li><li data-i="2">Two</li></ul><div style="width:800px;height:500px" data-n2d="#n2-s01"></div>
<script type="application/json" id="n2-s01">%s</script></section>
<script src="%s"></script><script src="%s"></script>"""


def test_browser():
    print("in a browser")
    sys.path.insert(0, str(SKILLS / "course-module-ux" / "measure" / "scripts"))
    from test_audit_drawing import browser
    from playwright.sync_api import sync_playwright
    exe = browser()
    if not exe:
        check("a browser to test in", False, "no Chrome or Edge found")
        return
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=exe, headless=True, args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto((KIT / "demos.html").as_uri())
        pg.wait_for_function("window.__demos && window.__demos.figs().length > 0")
        for tablet in (False, True):
            pg.evaluate("window.__demos.size(%s)" % ("true" if tablet else "false"))
            pg.wait_for_function("window.__demos.figs().length > 0")
            found = pg.evaluate(AUDIT)
            check("every demo figure clean at every step (%s box)" % ("tablet" if tablet else "projector"), not found, found[:8])
        check("no script errors on the demo page", not errs, errs[:3])
        spec = json.dumps(demos()[4]["spec"]).replace("</", "<\\/")
        tmp = KIT / "scripts" / "_deck_test.html"
        tmp.write_text(DECK % ((KIT / "n2d.css").as_uri(), spec, (KIT / "n2d-things.js").as_uri(), (KIT / "n2d.js").as_uri()), encoding="utf-8")
        try:
            pg.goto(tmp.as_uri())
            pg.wait_for_function("window.GB_HOOKS && GB_HOOKS.s01")
            pg.evaluate("GB_HOOKS.s01.enter()")
            first = pg.evaluate("document.querySelector('[data-i=\"1\"]').className")
            moved = pg.evaluate("GB_HOOKS.s01.step(1)")
            second = pg.evaluate("[document.querySelector('[data-i=\"1\"]').className, document.querySelector('[data-i=\"2\"]').className]")
            check("in a deck: arrival lights line 1, Next walks the figure", first == "cur" and moved, (first, moved))
            check("in a deck: the step's line is lit now, the one before stays lit", second[1] == "cur" and second[0] == "lit", second)
            pg.wait_for_timeout(1800)
            check("the figure is idle once it has settled", pg.evaluate("N2D.figures[0].idle()"))
        finally:
            tmp.unlink()
        b.close()


def main():
    test_checks()
    test_things()
    test_plan()
    if "--quick" not in sys.argv:
        test_browser()
    print("\n%s" % ("ALL PASS" if not FAILS else "FAILED: %d - %s" % (len(FAILS), "; ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
