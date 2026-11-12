# -*- coding: utf-8 -*-
"""test_line_binding - every line a slide lights changes its figure to the thing the line names.

    python test_line_binding.py

The factory trial's M01 and M16 decks: the figure ran one stop behind its words (M01 s04, s19b, s23 - an opening view on
line 1, the part line 1 names on line 2, and the last two steps on one line), stood still through a slide of points and
played its steps after them (M16 s01, s04), and lit one line on two Nexts (M01 s04, s23). Pinned here:
  * line_binding.deck_problems on those slides as they were built, and on the same slides bound one step a line;
  * starter_kit3d writes one step a line, line 1's part framed on the opening step;
  * kit_meaning.kit2d_boxes refuses the flat boxes-with-titles figure and arrows chaining options set side by side;
  * kit2d_figure (the compile) reports it; the 2D starter never composes boxes and arrows;
  * gb_steps.js walks the figure of a slide of points with its points (browser, when Playwright and Chrome are here).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compile_module as cm  # noqa: E402
import line_binding as lb  # noqa: E402

SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(SKILLS, "course-visuals", "kit", "scripts"))
import kit_meaning as km  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def slide(sid, spec, lines, kind="k3", head="", points=False):
    words = ('<ul class="lt-points">%s</ul>' % "".join('<li data-k="%d">%s</li>' % (k, x) for k, x in enumerate(lines))
             if points else "".join('<p class="lead" data-i="%d">%s</p>' % (k, x) for k, x in enumerate(lines, 1)))
    host = {"k3": "data-kit3d", "k2": "data-kit2d", "kit": "data-kit"}[kind]
    return ('<section class="slide" id="%s"%s><div %s="#%s-%s"></div><script type="application/json" id="%s-%s">%s</script>'
            '<div class="copy">%s</div></section>' % (sid, head, host, kind, sid, kind, sid, json.dumps(spec).replace("</", "<\\/"),
                                                       words))


# M01 s04 as the builder wrote it: an opening view on line 1, then the tank on line 2, the plant on line 3, the pump and the
# heater on line 4, and a fifth step "fixed" from line 5 to line 4
S04_LINES = ["Semi-refrigerated (semi-pressurised) ships use insulated Type C tanks, designed for about 7 bar and cooled to -10 C to -48 C.",
             "A refrigeration plant gives a fully refrigerated capability while the design pressure stays below that required for fully pressurised carriage.",
             "Cargo heaters and booster pumps let them discharge to a pressurised facility.",
             "Up to 30,000 m3: LPG, ammonia, propylene, VCM."]
S04_LABELS = [{"part": "tank", "text": "Insulated Type C tanks, about 7 bar"}, {"part": "plant", "text": "Reliquefaction plant"},
              {"part": "pump", "text": "Booster pump"}, {"part": "heater", "text": "Cargo heater"},
              {"part": "dbottom", "text": "Double bottom ballast"}]
S04_BEHIND = {"label": "x", "parts": [{"id": "tank", "type": "tank_c"}], "labels": S04_LABELS, "groups": {"discharge": ["pump", "heater"]},
              "steps": [{"view": {"az": 24, "el": 23}, "line": 1},
                        {"view": {"az": 24, "el": 23, "frame": ["tank"]}, "select": "tank", "labels": ["tank", "dbottom"], "line": 2},
                        {"view": {"az": 22, "el": 22, "frame": ["plant"]}, "select": "plant", "labels": ["plant"], "line": 3},
                        {"view": {"az": 20, "el": 42, "frame": ["pump", "heater"]}, "select": "discharge", "labels": ["pump", "heater"], "line": 4},
                        {"view": {"az": 24, "el": 23}, "labels": ["tank", "plant", "pump", "heater"], "line": 4}]}
S04_BOUND = dict(S04_BEHIND, steps=[dict(S04_BEHIND["steps"][1], line=1), dict(S04_BEHIND["steps"][2], line=2),
                                    dict(S04_BEHIND["steps"][3], line=3), S04_BEHIND["steps"][4]])

# M01 s23: the rooms on line 2 (line 1's subject), the bulkhead and the shafts on line 2 again, the airlock on line 3
S23_LINES = ["The reliquefaction plant is in a compressor house on deck; its electric motors are in the motor room beside it.",
             "A gastight bulkhead with sealed drive shafts separates them.",
             "From a gas-dangerous deck to a gas-safe space only through an airlock: two self-closing gastight steel doors."]
S23_LABELS = [{"part": "comp", "text": "Compressor room (on deck)"}, {"part": "motor", "text": "Electric motor room"},
              {"part": "bulkhead", "text": "Gastight bulkhead"}, {"part": "shaft", "text": "Sealed drive shaft"},
              {"part": "airlock", "text": "Airlock: two self-closing doors"}]
S23_PARTS = [{"id": "house", "type": "compressor_house", "subs": {"compressor": "comp", "motor": "motor", "bulkhead": "bulkhead",
                                                                  "shaft": "shaft"}}, {"id": "airlock", "type": "airlock"}]
S23_BEHIND = {"label": "x", "parts": S23_PARTS, "labels": S23_LABELS,
              "steps": [{"view": {"az": 25, "el": 28}, "line": 1},
                        {"view": {"az": 25, "el": 28}, "labels": ["comp", "motor"], "line": 2},
                        {"view": {"az": 20, "el": 22, "frame": ["bulkhead"]}, "select": "bulkhead", "labels": ["bulkhead", "shaft"], "line": 2},
                        {"view": {"az": 20, "el": 25, "frame": ["airlock"]}, "select": "airlock", "labels": ["airlock"], "line": 3}]}

# M16 s01: five points beside a scene whose five steps name no line
M16_POINTS = ["Two kinds: portable foam extinguishers and the applicator set", "Kept in a foam station: applicator, hose, concentrate container",
              "Reaches sheltered areas the foam monitors cannot", "For oil spill fires - never a liquefied gas pool",
              "Dry chemical powder is used for fighting liquefied gas fire"]
M16_LABELS = [{"part": "extinguisher", "text": "Portable foam extinguisher"}, {"part": "station", "text": "Foam station"},
              {"part": "monitor", "text": "Foam monitor"}, {"part": "shelter", "text": "Sheltered area"}, {"part": "spill", "text": "Oil spill on deck"}]
M16_FREE = {"label": "x", "parts": [{"id": "station", "type": "box"}], "labels": M16_LABELS,
            "steps": [{"labels": ["extinguisher", "station"]}, {"labels": ["station"]}, {"labels": ["monitor", "shelter"]},
                      {"labels": ["spill"]}, {"labels": ["station", "spill"]}]}


def binding():
    print("-- the figure runs one stop behind its words (M01 s04, s23)")
    got = lb.deck_problems(slide("s04", S04_BEHIND, S04_LINES))
    text = " | ".join(m for _, m in got)
    check("M01 s04 as built: the same line on two Nexts (steps 3 and 4, line 4) and one stop behind (steps 1 and 2) - must-fixes",
          all(sid == "s04" for sid, _ in got) and "steps 3 and 4 both light line 4" in text and "one stop behind" in text
          and "step 1 (line 2)" in text and "step 2 (line 3)" in text, got)
    check("... the same scene bound one step a line passes",
          not lb.deck_problems(slide("s04", S04_BOUND, S04_LINES)), lb.deck_problems(slide("s04", S04_BOUND, S04_LINES)))
    got = lb.deck_problems(slide("s23", S23_BEHIND, S23_LINES))
    text = " | ".join(m for _, m in got)
    check("M01 s23 as built: line 2 lit on two Nexts, and the rooms of line 1 shown on line 2",
          "steps 1 and 2 both light line 2" in text and "one stop behind" in text and "step 1 (line 2)" in text, got)
    bound = dict(S23_BEHIND, steps=[dict(S23_BEHIND["steps"][1], line=1)] + S23_BEHIND["steps"][2:])
    bound["steps"][1] = dict(bound["steps"][1], line=2)
    check("... bound one step a line it passes", not lb.deck_problems(slide("s23", bound, S23_LINES)))
    other = dict(S04_BOUND, steps=[S04_BOUND["steps"][0], dict(S04_BOUND["steps"][1], select="pump", labels=["pump"],
                                                                   view={"az": 20, "el": 42, "frame": ["pump"]})] + S04_BOUND["steps"][2:])
    got = lb.deck_problems(slide("s04", other, S04_LINES))
    check("a step whose line names a labelled part while it shows another is a must-fix naming both",
          len(got) == 1 and "does not show what its line names" in got[0][1] and "plant" in got[0][1] and "booster" in got[0][1], got)
    vague = ["The ship carries cargo in the vapour space.", "It is kept cold."]
    sp = {"label": "x", "parts": [], "labels": [{"part": "h", "text": "Hold space"}, {"part": "t", "text": "Cargo tank"}],
          "steps": [{"labels": ["t"], "line": 1}, {"labels": ["h"], "line": 2}]}
    check("a line sharing only a word for a kind of thing (space, tank, cargo) with a label names nothing - not judged",
          not lb.deck_problems(slide("s09", sp, vague)))

    print("-- a slide of points whose figure's steps name no line (M16 s01, s04)")
    got = lb.deck_problems(slide("s01", M16_FREE, M16_POINTS, head=' data-template="long-explanation.v1"', points=True))
    check("M16 s01: five points, five steps naming no line - a must-fix (the points count as the slide's lines)",
          len(got) == 1 and "5 steps that name no line, beside 5 lines" in got[0][1], got)
    tied = dict(M16_FREE, steps=[dict(st, line=k) for k, st in enumerate(M16_FREE["steps"], 1)])
    check("... each step given its point's number (\"line\": 1 .. 5) passes, and the compile's line check counts the points",
          not lb.deck_problems(slide("s01", tied, M16_POINTS, points=True))
          and not cm.step_line_problems(slide("s01", tied, M16_POINTS, points=True)),
          cm.step_line_problems(slide("s01", tied, M16_POINTS, points=True)))
    sys.path.insert(0, os.path.join(SKILLS, "course-visuals", "kit3d", "scripts"))
    import check_kit3d
    check("... and so does the 3D check of a built deck (check_kit3d.py module, scene3d_check.py)",
          not check_kit3d.deck_line_problems(slide("s01", tied, M16_POINTS, points=True)))

    print("-- every line changes the figure")
    gap = dict(S04_BOUND, steps=[S04_BOUND["steps"][0], dict(S04_BOUND["steps"][2], line=3), dict(S04_BOUND["steps"][3], line=4)])
    got = lb.deck_problems(slide("s04", gap, S04_LINES))
    check("a line between two bound lines that no step lights is a must-fix (the figure stands still while it is lit)",
          len(got) == 1 and "no step for line 2" in got[0][1], got)
    one = dict(S04_BOUND, steps=[S04_BOUND["steps"][0]])
    got = lb.deck_problems(slide("s04", one, S04_LINES))
    check("a 3D scene with one step beside four lines never changes - a must-fix",
          len(got) == 1 and "never changes while its 4 lines are lit" in got[0][1], got)
    check("... a slide the build sheet shows whole (data-still) is not walked",
          not lb.deck_problems(slide("s04", one, S04_LINES, head=" data-still")))
    flat = dict(S04_BOUND, steps=[S04_BOUND["steps"][0], dict(S04_BOUND["steps"][0], line=2)] + S04_BOUND["steps"][2:])
    got = lb.deck_problems(slide("s04", flat, S04_LINES))
    check("a 3D step with the same view, part and labels as the step before (M01 s19b: 2PG shown as 2G) is a must-fix",
          any("does not change on step 1" in m for _, m in got), got)
    ask = ('<li class="you"><b class="ask">Why?</b></li>')
    asked = slide("s06", dict(S04_BOUND, steps=[S04_BOUND["steps"][0], dict(S04_BOUND["steps"][1], line=2)]),
                  S04_LINES).replace("</div></section>", ask + "</div></section>")
    check("a slide with a question plays its last steps with the answer: its lines are not all bound - not a problem there",
          not lb.deck_problems(asked), lb.deck_problems(asked))

    print("-- a 2D figure")
    nodes = {"size": [480, 300], "state": {"l1": 0, "l2": 0}, "parts": [
        {"id": "N1", "type": "node", "x": 100, "y": 100, "w": 160, "h": 60, "text": "Fully pressurised", "lit": "@l1"},
        {"id": "N2", "type": "node", "x": 300, "y": 100, "w": 160, "h": 60, "text": "Semi-refrigerated", "lit": "@l2"},
        {"id": "A1", "type": "arrow", "from": "N1", "to": "N2"}],
        "steps": [{"set": {"l1": 1}, "line": 1}, {"set": {"l1": 0, "l2": 1}, "line": 1}]}
    page = slide("s06", nodes, ["Fully pressurised: heavy tanks.", "Semi-refrigerated: thinner tanks."], "k2")
    got = lb.deck_problems(page) + cm.step_line_problems(page)
    text = " | ".join(m for _, m in got)
    check("a 2D figure lighting line 1 on two Nexts and never line 2: the same line twice, Semi-refrigerated shown while line 1 "
          "names Fully pressurised, and line 2 left with the figure standing - must-fixes",
          "same line" in text and "fully/pressurised" in text and "come after line 1" in text, got)
    arrows = dict(nodes, state={"a1": 0, "a2": 0}, parts=nodes["parts"][:2] + [
        {"id": "N3", "type": "node", "x": 100, "y": 200, "w": 160, "h": 60, "text": "Fully refrigerated"},
        {"id": "A1", "type": "arrow", "from": "N1", "to": "N2", "draw": "@a1"}, {"id": "A2", "type": "arrow", "from": "N2", "to": "N3", "draw": "@a2"}],
        steps=[{"set": {"l1": 1}, "line": 1}, {"set": {"a1": 1}, "line": 2}, {"set": {"a2": 1}, "line": 3}])
    got = lb.deck_problems(slide("s02", arrows, ["Fully pressurised: Type C.", "Semi-refrigerated: insulated.", "Fully refrigerated: cold."], "k2"))
    check("M01 s02 as built: each Next only draws an arrow while the lit line names a box that never lights - a must-fix",
          len(got) == 1 and "only unnamed parts move" in got[0][1] and "step 1 lights line 2" in got[0][1], got)


def starter():
    print("-- the 3D starter: one step a line, line 1's part on the opening step")
    sp = cm.starter_kit3d({"module": 1}, {"id": "s04", "title": "Semi-refrigerated ships", "visual": "A hull section.",
                                          "text": "Type C tank - insulated, about 7 bar.\nIt is cooled.\nVent mast - high above the deck."})
    st = sp["steps"]
    tank = next(p["id"] for p in sp["parts"] if p["type"] == "tank_c")
    hull = next(p["id"] for p in sp["parts"] if p["type"] == "hull")
    mast = next(p["id"] for p in sp["parts"] if p["type"] == "vent_mast")
    check("starter_kit3d: three lines, three steps lighting lines 1, 2, 3; the opening step frames line 1's tank in its hull "
          "section and selects it; the vent mast on line 3; no overview step before line 1's",
          [x["line"] for x in st] == [1, 2, 3] and st[0].get("select") == tank and st[0]["view"].get("frame") == [hull]
          and st[2].get("select") == mast and st[2]["view"].get("frame") == [mast]
          and "frame" not in st[1]["view"], st)


def boxes():
    print("-- the flat boxes-with-titles 2D figure (M01 s02, s06, s14, s18, M16 s03)")
    node = lambda i, t, x, y: {"id": "N%d" % i, "type": "node", "x": x, "y": y, "w": 150, "h": 50, "text": t}
    chain = {"why": "sequence", "parts": [node(1, "Fully pressurised", 80, 60), node(2, "Semi-refrigerated", 80, 140),
                                          node(3, "Fully refrigerated", 80, 220), node(4, "By cargo", 260, 60)] +
             [{"id": "A%d" % i, "type": "arrow", "from": "N%d" % i, "to": "N%d" % (i + 1)} for i in (1, 2, 3)]}
    got = km.kit2d_boxes(chain, parallel=True)
    check("M01 s02 as built: four boxes of words chained by arrows, nothing drawn - BOXES, and the arrows chain options the "
          "slide compares - CHAIN; each says what to use instead",
          len(got) == 2 and got[0].startswith("BOXES") and all(w in got[0] for w in ("part drawing", "3D scene", "photograph",
                                                                                     "no figure", "blueprint")), got)
    check("... CHAIN names the chain", any(x.startswith("CHAIN") and "N1 -> N2 -> N3" in x for x in got), got)
    branch = dict(chain, why="comparison", parts=chain["parts"][:4] + [{"id": "T%d" % i, "type": t, "x": 300, "y": 60 * i, "w": 40, "h": 50}
                                                                      for i in (1, 2, 3) for t in ("tank", "gauge")] +
                  [{"id": "B%d" % i, "type": "arrow", "from": "N4", "to": "N%d" % i} for i in (1, 2, 3)])
    check("a branch from one root to the options, with a drawing beside them, passes", not km.kit2d_boxes(branch), km.kit2d_boxes(branch))
    many = {"parts": [node(i, "Box %d" % i, 60 * i, 40) for i in range(1, 6)] + [{"id": "T", "type": "tank", "x": 10, "y": 10, "w": 40, "h": 60}]}
    check("five boxes of words beside one drawn tank - BOXES (a list in boxes beside a few drawings)",
          len(km.kit2d_boxes(many)) == 1 and "5 of its parts are boxes" in km.kit2d_boxes(many)[0], km.kit2d_boxes(many))
    drawn = {"parts": [{"id": "T", "type": "tank", "x": 10, "y": 10, "w": 40, "h": 60}, {"id": "P", "type": "pump", "x": 90, "y": 50},
                       {"id": "L", "type": "pipe", "pts": [[10, 10], [90, 50]]}, {"id": "C", "type": "callout", "at": [40, 40], "text": "Suction"}]}
    check("a drawing with a callout passes", not km.kit2d_boxes(drawn), km.kit2d_boxes(drawn))
    probs = []
    cm.kit2d_figure(json.dumps(dict(chain, label="x", size=[480, 300])), {"id": "s02", "visual_kind": "comparison", "title": "t"}, probs, "s02")
    check("the compile refuses it: a must-fix for the slide naming BOXES and CHAIN (the slide's visual kind is a comparison)",
          len(probs) == 2 and all(p.startswith("s02: its 2D kit figure - ") for p in probs), probs)
    proc = {"id": "s05", "kind": "slide", "visual_kind": "process_animation", "title": "Handling a change",
            "visual": "The steps of a change request.",
            "text": "Request - the change is written down.\nAssess - cost, time and risk.\nDecide - approve or escalate.\nPlan - the plan is updated."}
    st = cm.starter_kit2d({"module": 1}, proc)
    check("the 2D starter never composes one box a line with arrows (a process slide gets another kind or none)",
          not st or not any(p.get("type") in ("node", "arrow") for p in st.get("parts") or []), st)


def browser():
    print("-- gb_steps.js walks the figure of a slide of points with its points (M16 s01, s04)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  (skipped: no Playwright)")
        return
    sys.path.insert(0, os.path.join(SKILLS, "course-module-ux", "measure", "scripts"))
    from test_audit_drawing import browser as find_browser
    exe = find_browser()
    if not exe:
        print("  (skipped: no Chrome or Edge)")
        return
    steps_js = os.path.join(SKILLS, "course-module-ux", "assets", "gb_steps.js")
    tmp = tempfile.mkdtemp(prefix="linebind_")
    try:
        page = os.path.join(tmp, "p.html")
        pts = "".join('<li data-k="%d">point %d</li>' % (k, k + 1) for k in range(3))

        def html(steps):
            return ('<!doctype html><html><body><section class="slide" id="s01"><ul class="lt-points">%s</ul>'
                    '<div data-kit3d="#k3-s01"></div></section><script>var at = 0, S = %s;'
                    'document.getElementById("s01").__fig = {steps: function () { return S; }, at: function () { return at; },'
                    'go: function (n) { at = n; }};</script><script src="%s"></script></body></html>'
                    % (pts, json.dumps(steps), "file:///" + steps_js.replace("\\", "/")))
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=exe, args=["--allow-file-access-from-files"])
            pg = b.new_page()
            for name, steps in (("named", [{"line": 1}, {"line": 2}, {"line": 3}]), ("unnamed", [{}, {}, {}])):
                with open(page, "w", encoding="utf-8") as f:
                    f.write(html(steps))
                pg.goto("file:///" + page.replace("\\", "/"))
                seen = pg.evaluate("""() => { const h = GB_HOOKS.s01, out = []; h.enter();
                    for (let k = 0; k < 3; k++) { out.push(at); h.step(1); } return out; }""")
                check("a slide of points: the figure is at step k while point k+1 is lit (%s steps), never after the points" % name,
                      seen == [0, 1, 2], seen)
            b.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# the gas trial M01 scenes as built, with the lines of their slides
HULL = {"type": "hull", "pick": False, "half": 7, "bottom": 0, "floor": 1.2, "top": 10, "topwing": [2.2, 2.2]}
S16_LINES = ["Access from a gas-dangerous zone on the open deck to a gas-safe space is through an airlock.",
             "Two self-closing, gastight steel doors, 1.5 to 2.5 m apart, with no hook or other device to hold them open.",
             "An audible and visual alarm on both sides warns when the doors are moved from the closed position."]
S16 = {"label": "x", "units": "m",
       "parts": [{"id": "lock", "type": "room", "at": [0, 0, 0], "size": [4, 2.6, 3], "open": "front", "roof": True},
                 {"id": "door1", "type": "box", "at": [-2, 1.1, 0], "size": [0.1, 2.2, 1.0]},
                 {"id": "door2", "type": "box", "at": [2, 1.1, 0], "size": [0.1, 2.2, 1.0]}],
       "labels": [{"part": "lock", "text": "Airlock from the open deck", "steps": [0]},
                  {"part": "door1", "text": "Self-closing gastight door", "steps": [1]},
                  {"part": "door2", "text": "Second door, no hook", "steps": [1]}, {"part": "lock", "text": "Alarm on both sides", "steps": [2]}],
       "steps": [{"view": {"az": 30, "el": 22, "frame": ["lock"]}, "line": 1, "select": "lock"},
                 {"view": {"az": 30, "el": 22, "frame": ["lock"]}, "line": 2, "select": "door1"},
                 {"view": {"az": 60, "el": 18, "frame": ["lock"]}, "line": 3, "select": "lock"}]}
S16_KIT = dict(S16, parts=[{"id": "lock", "type": "airlock", "at": [0, 0, 0], "gap": 2}],
               labels=[{"part": "lock", "text": "Airlock from the open deck", "steps": [0]},
                       {"part": "lock_door1", "text": "Self-closing gastight door", "steps": [1]},
                       {"part": "lock_door2", "text": "Second door, no hook", "steps": [1]},
                       {"part": "lock_alarm", "text": "Alarm on both sides", "steps": [2]}],
               steps=[S16["steps"][0], dict(S16["steps"][1], select="lock_door1"), dict(S16["steps"][2], select="lock_alarm")])
S23_TRIAL_LINES = ["The most common Type B tank is the spherical Kvaerner Moss design.",
                   "Detailed stress, fatigue and crack propagation analysis allows a partial secondary barrier: a drip tray under the tank.",
                   "The aluminium sphere is supported by an equatorial ring on a cylindrical skirt resting on the inner hull.",
                   "The hold space may be filled with dry air."]
S23_TRIAL = {"label": "x", "units": "m",
             "parts": [{"id": "hull", "type": "hull", "pick": False, "x": [-8, 8], "half": 10, "bottom": 0, "floor": 2, "top": 11, "double": 2.2},
                       {"id": "sphere", "type": "tank_sphere", "in": "hull", "r": 7, "insulation": 0.3, "cut": True, "fill": 0.5,
                        "drip": True, "cover": True}],
             "labels": [{"part": "sphere", "text": "Moss sphere", "steps": [0]}, {"part": "sphere_drip", "text": "Drip tray", "steps": [1]},
                        {"part": "sphere_skirt", "text": "Skirt at the equator", "steps": [2]}, {"part": "sphere_cover", "text": "Tank cover", "steps": [3]}],
             "steps": [{"view": {"az": 35, "el": 18, "frame": ["hull"]}, "line": 1, "select": "sphere"},
                       {"view": {"az": 35, "el": 12, "frame": ["hull"]}, "line": 2, "select": "sphere_drip"},
                       {"view": {"az": 45, "el": 16, "frame": ["hull"]}, "line": 3, "select": "sphere_skirt"},
                       {"view": {"az": 30, "el": 28, "frame": ["hull"]}, "line": 4, "select": "sphere_cover"}]}
S05_LINES = ["A fully pressurised ship carries LPG at ambient temperature in tanks built for about 18 bar.",
             "A semi-pressurised ship cools the same cargo, so its tanks need only a working pressure of about 5 to 7 bar."]
S05 = {"label": "x", "units": "m",
       "parts": [dict(HULL, id="pres", x=[-30, -20]), {"id": "tanka", "type": "tank_c", "in": "pres", "r": 3, "cut": True, "fill": 0.6},
                 dict(HULL, id="semi", x=[0, 10]), {"id": "tankb", "type": "tank_c", "in": "semi", "r": 3, "cut": True, "fill": 0.6,
                                                    "insulation": 0.3}],
       "labels": [{"part": "tanka", "text": "Fully pressurised: about 18 bar", "steps": [0]},
                  {"part": "tankb", "text": "Semi-pressurised: 5 to 7 bar", "steps": [1]}],
       "steps": [{"view": {"az": 35, "el": 20, "frame": ["pres"]}, "line": 1, "select": "tanka"},
                 {"view": {"az": 35, "el": 20, "frame": ["semi"]}, "line": 2, "select": "tankb"}]}


def scenes():
    print("-- a 3D scene against its lines: what they name is drawn and pointed at, what they compare is framed together "
          "(the gas trial)")
    text = " | ".join(m for _, m in lb.deck_problems(slide("s16", S16, S16_LINES)))
    check("M01 s16 as built: an airlock and its alarm named by the lines, a plain room and two slabs in the scene - must-fixes",
          "names an airlock, and the scene has none" in text and "names an alarm, and the scene has none" in text, text)
    got = lb.deck_problems(slide("s16", S16_KIT, S16_LINES))
    check("... drawn with the kit's airlock (its doors and its alarm) it passes", not got, got)
    text = " | ".join(m for _, m in lb.deck_problems(slide("s23", S23_TRIAL, S23_TRIAL_LINES)))
    check("M01 s23 as built: line 4 names the hold space, its step points at the tank cover - a must-fix",
          "step 3 lights line 4, which names a hold space, and points at sphere_cover" in text, text)
    fixed = json.loads(json.dumps(S23_TRIAL))
    fixed["labels"][3] = {"part": "hull_hold", "text": "Hold space: dry air", "steps": [3]}
    fixed["steps"][3]["select"] = "hull_hold"
    got = lb.deck_problems(slide("s23", fixed, S23_TRIAL_LINES))
    check("... its step on the hull's hold space passes", not got, got)
    text = " | ".join(m for _, m in lb.deck_problems(slide("s05", S05, S05_LINES)))
    check("M01 s05 as built: two ships compared, each step framing one hull - a must-fix",
          "a line compares and its step shows one side of it" in text and "step 1 (line 2) frames semi of pres and semi" in text, text)
    both = json.loads(json.dumps(S05))
    for st in both["steps"]:
        st["view"]["frame"] = ["pres", "semi"]
    got = lb.deck_problems(slide("s05", both, S05_LINES))
    check("... each step framing both hulls passes the line check", not got, got)


def main():
    binding()
    scenes()
    starter()
    boxes()
    browser()
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
