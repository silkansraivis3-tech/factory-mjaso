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
  * no link inside a slide (L35: the deck never navigates away);
  * L61 (2.52.0): every slide is one of the owner's thirteen layout templates, chosen from the slide or asked for by name;
    the owner's rules - 55 / 45, dense text has a picture, never three teaching slides in a row without one, long words
    in parts - are problems with the slide's id;
  * L62 (2.53.0): two slides in a row never look the same (shape and ground); a drawing made for a white page keeps
    the light ground; a photograph smaller than 1600 px is enlarged once, its original kept.
"""
from __future__ import annotations

import html
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
import gate_fixture  # noqa: E402

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
    """the fixtures' drawings are bare shapes, not L54-clean drawings: the drawing check runs only where a test asks
    for it (--drawing-check), so every other test sees the build alone"""
    args = list(args)
    if args and args[0] == COMPILE:
        args = [x for x in args if x != "--drawing-check"] if "--drawing-check" in args else args + ["--no-drawing-check"]
    p = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def script(approved=True, screens=SCREENS):
    # 2.47.0 - the module plan states allocated against built minutes and a mismatch is a build problem (exit 1): a fixture
    # allocates what its screens add up to (SCREENS: 25), as an approved script does
    built = sum(x.get("minutes") or 0 for x in screens if x["kind"] in cs.INSTRUCTOR)
    s = {"module": 1, "title": "IGF ships", "course_language": "English", "operator_language": "en",
         "minutes_allocated": built or 25, "status": "draft", "screens": json.loads(json.dumps(screens))}
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
                        "s03": {"figure": "ga.html"},
                        "s04": {"figure": "hull.svg", "dark": True, "declined_3d": "the fixture's hull section stays a flat drawing"}}})
    return c, md


def deck(md):
    return io.open(os.path.join(md, "presentation", "index.html"), encoding="utf-8").read()


def section(page, sid):
    m = re.search(r'<section [^>]*id="%s".*?</section>' % sid, page, re.S)
    return m.group(0) if m else ""


GA = ('<svg viewBox="0 0 400 200" role="img"><path id="hull" d="M10 60 H390 V190 H10 Z" fill="#fff" stroke="#000"/>'
      '<g fill="#eee" stroke="#000"><rect x="20" y="70" width="110" height="110"/><rect x="40" y="90" width="60" height="50"/>'
      '<rect x="290" y="70" width="40" height="110"/><rect x="340" y="70" width="40" height="110"/>'
      '<rect x="295" y="20" width="80" height="38"/><rect x="40" y="10" width="70" height="48"/>'
      '<rect x="150" y="150" width="130" height="30"/><rect x="200" y="70" width="80" height="22"/></g>'
      '<g id="sp-tank" data-name="Fuel tank"><rect class="hit" x="200" y="100" width="80" height="50"/></g>'
      '<g id="sp-tcs" data-name="Tank connection space"><rect class="hit" x="150" y="100" width="40" height="40"/></g>'
      '<g id="sp-vent" data-name="Vent mast"><rect class="hit" x="230" y="5" width="10" height="55"/></g>'
      '<g id="labels"><text x="200" y="195">Fuel tank</text></g></svg>')
TASKS = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the spaces", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the tank connection space.",
     "visual": "the GA", "answer": "Tank connection space*\nFuel tank\nFunnel", "feedback": "It holds the tank valves."},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "match", "question": "Match each space to what it holds.",
     "answer": "Fuel preparation room = pumps and vaporizers\nTank connection space = the tank valves\nVent mast = the vapour outlet",
     "feedback": "Each space has one job."},
    {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "multi_select", "question": "Which are fuels under the IGF Code?",
     "options": ["LNG", "Coal", "CNG"], "correct": "A, C", "feedback": "Natural gas."},
    {"id": "q04", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the bunkering steps in order.",
     "answer": "Safety meeting\nConnect the hose\nTransfer\nDisconnect", "feedback": "Meeting first."},
    {"id": "t02", "kind": "task-slide", "opens": "SC2", "title": "Self-check 2 - gaps", "text": "Self-check on your tablet now.", "minutes": 3},
    {"id": "q05", "kind": "self-check", "set": "SC2", "mechanic": "cloze", "question": "Complete the sentence.",
     "answer": "LNG is stored at [-162* | 0 | 20] °C.", "feedback": "Very cold."},
    {"id": "t03", "kind": "task-slide", "opens": "MC", "title": "Module check - Module 1",
     "text": "Module check on your tablet now.\nThree questions on the whole module.\nYou see PASSED or NOT PASSED.", "minutes": 5},
    {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "label_diagram", "question": "Drag each label to its place.",
     "visual": "the GA", "answer": "Fuel tank\nTank connection space\nVent mast", "feedback": "These are the new spaces."},
    {"id": "m02", "kind": "module-check", "set": "MC", "mechanic": "categorise", "question": "Sort the fuels.",
     "answer": "Detailed rules: LNG; CNG\nAlternative design: methanol; ammonia", "feedback": "Natural gas has detailed rules."},
    {"id": "m03", "kind": "module-check", "set": "MC", "mechanic": "single_choice", "question": "Is venting acceptable?",
     "options": ["Yes", "No, only in an emergency"], "correct": "B", "feedback": "Only in an emergency."},
]


def keys_of(page):
    """[(words, data-key)] of every answer element"""
    return [(html_unescape(t), k) for k, t in re.findall(r'data-key="([0-9a-f]{8})">(?:<span class="vh">)?([^<]+)<', page)]


def html_unescape(s):
    import html
    return html.unescape(s).strip()


def recap_part(tmp):
    """L51: a slide marked "recap" is built in the one shared closing design, and still says the approved words"""
    print("\n-- the recap slide")
    os.makedirs(os.path.join(tmp, "r"))
    recap = {"id": "s05", "kind": "slide", "recap": True, "title": "What to take away", "visual_kind": "none",
             "text": "Kept liquid - cold, under pressure, or both.\nTwo barriers - between the gas and people.\nThe spaces are new.",
             "notes": "- Ask three trainees.", "minutes": 2}
    screens = json.loads(json.dumps(SCREENS))
    screens.insert([x["id"] for x in screens].index("t02"), recap)
    c, md = new_course(os.path.join(tmp, "r"), script(screens=screens))
    code, out = run(COMPILE, c, "--module", "1")
    r = section(deck(md), "s05")
    check("a recap slide is built in the shared closing design (slide dark recap, data-kind Summary)",
          code == 0 and 'class="slide dark recap"' in r and 'data-kind="Summary"' in r, out + r[:400])
    check("... one box per line, its title bold before ' - '",
          r.count('class="rc-item"') == 3 and '<b class="rc-t">Kept liquid</b><span class="rc-sep"> - </span>'
          '<span class="rc-d">cold, under pressure, or both.</span>' in r and '<span class="rc-d">The spaces are new.</span>' in r, r)
    check("... with the 'next: the module check' strip outside the script's words",
          '<p class="rc-next" data-script-ignore>' in r, r)
    code, out = run(MATCH, c, "--module", "1", "--part", "instructor")
    check("... and check_script_match finds exactly the approved words on it", code == 0, out)
    long_layouts_part(tmp)


# IGF M01 s01 and M02 s16, as approved: the words that spilled in every 2026-10-20 benchmark build
M01_S01 = ("Some ships burn gases or low-flashpoint liquids as fuel: LNG, methanol, ammonia, hydrogen.\nThese ships follow the IGF "
           "Code.\nIn this module:\n• the rules and the ships they cover\n• what is new on board\n• how the ship runs and "
           "takes on fuel\nAfter 40 minutes you can point out what is new on a general arrangement plan, and say how the ship runs "
           "and takes on fuel.")
M02_S16 = ("Fuels - LNG, CNG, LPG, methanol, ethanol, ammonia and hydrogen are kept cold, under pressure or as normal liquids.\n"
           "The LNG path - tank, tank connection space, vaporizer, gas valve unit, double-walled pipe, engine.\n"
           "Tanks - independent A, B and C, membrane and integral; the secondary barrier needed depends on the type.\n"
           "Zones - 0, 1 and 2 show where gas may be, and decide which equipment and work are allowed.\n"
           "Fire plan - the fuel preparation room is category A; A-60 boundaries shield spaces facing the fuel.\n"
           "Watching - level, pressure, temperature and gas are read locally and remotely; at 40 % LEL on two detectors the "
           "safety system acts.")


def long_layouts_part(tmp):
    """2.52.0 - a long opening over a full-screen photograph is laid out beside the photograph (it spilled 18 / 42 px), and a
    six-box recap fits a 1024 x 768 screen (its last line went 9 px under the deck's chrome) - by the deck audit itself"""
    print("\n-- long words on the opening photograph and the recap (2.52.0)")
    sys.path.insert(0, HERE)
    import compile_module as cm
    s = {"layout": "visual_full", "text": M01_S01}
    check("a full-screen photograph with more than %d words is laid out beside them (two-col: the split photo); a short one "
          "stays full screen" % cm.STAGE_MAX_WORDS,
          cm.composition(s, {}, True, True) == "two-col" and cm.composition(dict(s, text="Gas as fuel."), {}, True, True) == "photo"
          and cm.composition(s, {"composition": "photo"}, True, True) == "photo", cm.composition(s, {}, True, True))
    os.makedirs(os.path.join(tmp, "rl"))
    screens = json.loads(json.dumps(SCREENS))
    screens[0]["text"] = M01_S01
    screens.insert([x["id"] for x in screens].index("t02"), {"id": "s05", "kind": "slide", "recap": True, "title": "What to take away",
                                                             "visual_kind": "none", "text": M02_S16, "minutes": 2})
    c, md = new_course(os.path.join(tmp, "rl"), script(screens=screens))
    code, out = run(COMPILE, c, "--module", "1")
    check("the long fixture builds", code == 0 and 'class="slide photo split"' in section(deck(md), "s01"), out)
    audits = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "run_audits.py")
    code, aout = run(audits, os.path.join(md, "presentation", "index.html"), "--viewport", "1024x768", "--quiet")
    bad = [x for x in aout.splitlines() if re.search(r"\((s01|s05)\)", x) and re.search(r"spills|under #chrome|over-filled", x)]
    check("audited at 1280 x 800 and 1024 x 768: the opening's words stay on the slide, the recap clears the deck's chrome",
          "1024x768" in aout and not bad, bad or aout[-800:])


def tasks_part(tmp):
    """the trainee task pages built from the same script, with the one shared engine (gb_answer.js)"""
    print("\n-- the task pages")
    os.makedirs(os.path.join(tmp, "t"))
    c, md = new_course(os.path.join(tmp, "t"), script(screens=TASKS), build=False)
    io.open(os.path.join(md, "assets", "fig", "ga.svg"), "w", encoding="utf-8").write(GA)
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "q01": {"figure": "assets/fig/ga.svg", "areas": {"Funnel": [5, 5, 10, 20]}},
        "m01": {"figure": "assets/fig/ga.svg"}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    sc1 = os.path.join(md, "tasks", "sc1_the_spaces.html")
    mc = os.path.join(md, "assessment", "check.html")
    check("every set gets its page, named as the deck links it - none is left as it is",
          os.path.isfile(sc1) and os.path.isfile(mc) and os.path.isfile(os.path.join(md, "tasks", "sc2_gaps.html"))
          and "left as it is" not in out, out)
    code, out = run(MATCH, c, "--module", "1", "--part", "trainee")
    check("check_script_match --part trainee passes on the built pages", code == 0, out)
    p, m = io.open(sc1, encoding="utf-8").read(), io.open(mc, encoding="utf-8").read()
    check("<title> is 'CODE — Title' and the page is marked generated",
          "<title>SC1 — The spaces</title>" in p and "<title>MC — Module 1 check</title>" in m and "GENERATED by course-factory" in p)
    check("the page loads the factory's shared engine and styles, nothing of its own",
          '<script src="../assets/gb_answer.js"></script>' in p and 'href="../assets/gb_answer.css"' in p
          and "<script>" not in p and "postMessage" not in p)
    check("the answers are never in the page - only data-key", "data-correct" not in p + m and "data-answer" not in p + m)
    ks = dict(keys_of(p))
    check("tap the picture: the right area's key is gb_key(id, words, 1), the others 0",
          ks.get("Tank connection space") == cs.gb_key("q01", "Tank connection space", 1)
          and ks.get("Funnel") == cs.gb_key("q01", "Funnel", 0), ks)
    check("an area is found on the drawing by its data-name and its .hit shape, grown to a 56 px tap target",
          re.search(r'class="hot" style="left:3[0-9.]+%;top:4[0-9.]+%;width:1[0-9.]+%;height:2[0-9.]+%"', p), p[:200])
    check("an area the drawing does not name takes its box from the build sheet", 'style="left:5%;top:5%;width:10%;height:20%"' in p)
    check("the drawing is in the page once, marked for the engine, its own labels hidden by the shared styles",
          p.count('class="taskfig" data-fig="assets_fig_ga_svg"') == 1)
    check("match: each right side's key is its left side's words",
          ks.get("the tank valves") == cs.gb_key("q02", "the tank valves", "Tank connection space"))
    check("choose all that are right: one key per option, 1 for each right one",
          ks.get("LNG") == cs.gb_key("q03", "LNG", 1) and ks.get("CNG") == cs.gb_key("q03", "CNG", 1)
          and ks.get("Coal") == cs.gb_key("q03", "Coal", 0) and 'class="opts multi"' in p)
    check("... and its screen says data-multi=\"1\", so the engine keeps every option tapped, not only the last",
          '<section class="scr" data-script="q03" data-mech="multi_select" data-multi="1">' in p,
          re.search(r'<section[^>]*data-script="q03"[^>]*>', p).group(0) if re.search(r'<section[^>]*data-script="q03"[^>]*>', p) else p[:300])
    check("a single-choice screen is not multi", re.search(r'data-script="m03" data-mech="single_choice">', io.open(mc, encoding="utf-8").read()) is not None)
    check("put in order: the key is the place, and the cards are not shown in order",
          ks.get("Transfer") == cs.gb_key("q04", "Transfer", 3)
          and [t for t, _ in keys_of(p) if t in ("Safety meeting", "Connect the hose", "Transfer", "Disconnect")]
          != ["Safety meeting", "Connect the hose", "Transfer", "Disconnect"])
    check("the course's first self-check opens with 'try your tablet first'; the module check with its pass mark",
          'id="tryScr"' in p and 'id="introScr"' in m and "Pass mark 70 % – 3 of 3 right" in m and 'data-pass="70"' in m)
    check("2.60.0: the module check and a self-check are not blind - they show the right answer after each Check",
          "data-blind" not in m and "data-blind" not in p)
    km = dict(keys_of(m))
    check("label the drawing: the key is the place's id, the boxes sit in bands added to the drawing",
          km.get("Fuel tank") == cs.gb_key("m01", "Fuel tank", "sp-tank") and 'viewBox="0 ' not in m.split('data-fig')[1][:80]
          and m.count('class="lbox zone"') == 3, m[:300])
    check("sort into groups: the key is the group's name", km.get("methanol") == cs.gb_key("m02", "methanol", "Alternative design"))
    check("a page with a picture loads the picture viewer (L51)", 'src="../assets/gb_zoom.js"' in m)
    check("2.46.0: a picture answered on carries its ⤢ button on its own frame (data-zoom=\"button\" on .ga)",
          'data-zoom="button"' in p and 'class="ga lab" data-fig="assets_fig_ga_svg" data-zoom="button"' in m)
    # 2.46.0 - the instructor's answer key, compiled from the same approved script (the hand-made ones held old answers)
    kp = os.path.join(md, "assessment", "check_answer_key.html")
    k = io.open(kp, encoding="utf-8").read() if os.path.isfile(kp) else ""
    check("2.46.0: the answer key is compiled - assessment/check_answer_key.html, instructor-only by its name, marked generated",
          "GENERATED by course-factory" in k and "Instructor only" in k and "answer_key.py" in k, kp)
    check("... every self-check and module-check question in order, with its feedback, in the shared document look",
          all(k.find(">%s<" % x) > 0 for x in ("q01", "q02", "q03", "q04", "q05", "m01", "m02", "m03"))
          and k.find(">q04<") < k.find(">q05<") < k.find(">m01<") and "It holds the tank valves." in k
          and 'href="../assets/gb_page.css"' in k and "Self-check SC1 – The spaces" in k and "<h2>Module check</h2>" in k, k[:600])
    def shown(page, sid):                               # the options in the order the tablet shows them, lettered A, B ...
        sec = re.search(r'data-script="%s".*?</section>' % sid, page, re.S).group(0)
        return {t: chr(65 + i) for i, t in enumerate(html_unescape(x) for x in re.findall(r'class="opt"[^>]*>([^<]+)<', sec))}
    l3, lm = shown(p, "q03"), shown(m, "m03")
    want = sorted([(l3["LNG"], "LNG"), (l3["CNG"], "CNG")])
    check("... each right answer in the script's words: the area, the options by the letter the tablet SHOWS (shuffled since "
          "2.44.2), the order, the gap, the label places",
          "<td>Tank connection space</td>" in k and "<br>".join("<b>%s</b> – %s" % x for x in want) in k
          and "1. Safety meeting<br>2. Connect the hose" in k and "LNG is stored at <b>[-162]</b> °C." in k
          and "<b>%s</b> – No, only in an emergency" % lm["No, only in an emergency"] in k
          and "Fuel preparation room: pumps and vaporizers" in k, (l3, lm, k[k.find("q03"):k.find("q03") + 400]))
    check("... how the pages mark: no pass mark on a self-check; the check's pass mark and what it needs",
          "no pass mark" in k and "Pass mark 70 %: 3 of 3 right = PASSED" in k, k)
    check("... and nothing in it a checker could take for a task page: no data-script, no data-key",
          "data-script" not in k and "data-key" not in k)
    # 2.46.0 - a label box as wide as its words: the 17 % box cut "Tank connection space" off once the tick appeared
    import task_pages as tp
    vb = tp.band_vb((0, 0, 400, 200))
    places = [{"t": t, "box": bx} for t, bx in (("Fuel tank", [50, 50, 20, 20]), ("Tank connection space", [37, 50, 10, 20]),
                                                ("Vent mast", [57, 2, 5, 28]))]
    tp.label_boxes(places, vb)
    need = tp.label_px("Tank connection space") * 100 / (vb[2] * tp.ppu(vb))
    lr = sorted((p["at"][0], p["at"][0] + p["at"][2], p["at"][1]) for p in places)
    check("label boxes: every box as wide as the longest label needs, inside the drawing, none over another",
          all(abs(p["at"][2] - need) < 0.01 for p in places) and lr[0][0] >= 0 and max(x[1] for x in lr) <= 100
          and not any(a_[1] > b_[0] and a_[2] == b_[2] for a_, b_ in zip(lr, lr[1:])), places)
    probs = []
    eight = [{"t": "Tank connection space %d" % i, "box": [10 * i, 60, 5, 5]} for i in range(9)]
    tp.label_boxes(eight, vb, probs, "MC (m09)")
    check("... a row that is full passes boxes to the other row; what still does not fit is reported, never cut off",
          {p["at"][1] for p in eight} == {places[0]["at"][1], places[2]["at"][1]} and probs and "do not fit" in probs[0], probs or eight)
    check("... a box placed by hand narrower than its words is reported", tp.label_width_problems(
        [{"t": "Tank connection space", "at": [1, 1, 10], "hand": True}], vb, "MC (m01)"), "")
    # the classroom's own rules for a task page, read from the page and its shared engine
    eng = io.open(os.path.join(SKILLS, "course-task-ux", "assets", "gb_answer.js"), encoding="utf-8").read()
    check("the engine reports gb-task-done with ok, total, items, PASSED / NOT PASSED, timeout, and hears gb-timer",
          all(x in eng for x in ("gb-task-done", "ok:", "total:", "items:", "'PASSED'", "'NOT PASSED'", "timeout:", "gb-timer")))
    check("'Start again' only outside the classroom frame (window.parent === window)", "window.parent === window" in eng)
    first = io.open(sc1, encoding="utf-8").read()
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    check("the same script and build sheet give the same page", io.open(sc1, encoding="utf-8").read() == first, out)
    io.open(sc1, "w", encoding="utf-8").write(first.replace("Tap the tank", "Tap the TANK"))
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    check("a task page changed by hand is never overwritten without --force",
          code == 1 and "tasks/sc1_the_spaces.html was changed by hand" in out and "TANK" in io.open(sc1, encoding="utf-8").read(), out)
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    check("--force builds it again from the script", "TANK" not in io.open(sc1, encoding="utf-8").read(), out)
    sb = os.path.join(c, "working_claude", "script", "M01.build.json")
    cs.save(sb, {"module": 1, "screens": {"q01": {"figure": "assets/fig/ga.svg"}, "m01": {"figure": "assets/fig/ga.svg"}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    check("an answer the drawing does not name, with no box in the build sheet, is reported - never guessed",
          code == 1 and '"Funnel" is not on the drawing' in out, out)
    # 2.46.0 - the pass mark is the script's when it has one (content_script.py propose {"script_field": "pass_mark"})
    sp = os.path.join(c, "working_claude", "script", "M01.json")
    sc = cs.load(sp)
    cs.save(sp, dict(sc, pass_mark=80))
    cs.save(sb, {"module": 1, "pass_mark": 70, "screens": {"q01": {"figure": "assets/fig/ga.svg", "areas": {"Funnel": [5, 5, 10, 20]}},
                                                           "m01": {"figure": "assets/fig/ga.svg"}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    m, k = io.open(mc, encoding="utf-8").read(), io.open(kp, encoding="utf-8").read()
    check("the script's pass mark is used on the check and in the answer key; the build sheet's other one is reported",
          'data-pass="80"' in m and "Pass mark 80 %" in k and "the script's pass mark is 80 %, the build sheet still says 70 %" in out, out)
    cs.save(sp, sc)

    # ---- L54 at every build: a part poking out is found by the build itself, on a task page as on a deck
    sys.path.insert(0, HERE)
    import drawing_check
    if not drawing_check.find_browser():
        print("  skip  no Chrome or Edge found - the automatic drawing check was not tried")
        return
    cs.save(sb, {"module": 1, "screens": {"q01": {"figure": "assets/fig/ga.svg", "areas": {"Funnel": [5, 5, 10, 20]}},
                                          "m01": {"figure": "assets/fig/ga.svg"}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force", "--drawing-check")
    check("a clean drawing passes the automatic drawing check on every question that shows it",
          "Drawing check (L54): every drawing whole and clean" in out, out)
    bad = GA.replace('<rect class="hit" x="150"', '<rect x="2" y="150" width="60" height="40" stroke="#000" fill="#fff"/><rect class="hit" x="150"')
    io.open(os.path.join(md, "assets", "fig", "ga.svg"), "w", encoding="utf-8").write(bad)
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force", "--drawing-check")
    check("a room poking out of the hull is reported by the build itself, naming the page and the question",
          code == 1 and re.search(r"tasks/sc1_the_spaces\.html, q01, .*inside - rect .*pokes out", out)
          and re.search(r"assessment/check\.html, m01, .*inside", out), out)
    io.open(os.path.join(md, "assets", "fig", "ga.svg"), "w", encoding="utf-8").write(
        bad.replace('<rect x="2" y="150"', '<rect data-may-cross x="2" y="150"'))
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force", "--drawing-check")
    check("a crossing marked as meant (data-may-cross) is not a finding", "every drawing whole and clean" in out, out)

    # ---- finding 13: a kit figure's part coloured for a light slide cannot be seen on its dark panel - the same check
    kit_page = os.path.join(md, "kit_contrast.html")
    io.open(kit_page, "w", encoding="utf-8").write(
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}'
        '.kit-screen{background:#0C1E3A;padding:12px;width:640px}svg{display:block;width:100%;height:auto}'
        '.kit-panel{fill:#0C1E3A}text{font:600 14px sans-serif}#a{fill:#F3F8FD}#b{fill:#0A2463}</style></head><body>'
        '<div class="scr on" data-script="q01"><div class="kit-screen"><svg class="kit" viewBox="0 0 300 100">'
        '<rect class="kit-panel" x="1" y="1" width="298" height="98" rx="12"/>'
        '<text id="a" x="20" y="30">Boiling point</text><text id="b" x="20" y="60">Pressure rises</text></svg></div></div></body></html>')
    kprobs, knote = drawing_check.check([kit_page], root=md)
    kprobs = [x for x in kprobs if ": contrast - " in x]
    check("the build's drawing check reports a kit figure's label that vanishes on its dark panel, naming the part and the ratio",
          knote is None and len(kprobs) == 1 and "contrast" in kprobs[0] and "Pressure rises" in kprobs[0] and ":1" in kprobs[0], (kprobs, knote))
    os.remove(kit_page)


# ---- 2.43.0: real photographs and figure-kit drawings on a task page
PLANT_KIT = {"size": [400, 200], "label": "The fuel plant", "parts": [
    {"id": "tk", "type": "tank", "x": 20, "y": 50, "w": 150, "h": 110, "label": "Fuel tank", "value": 0.2},
    {"id": "mv", "type": "valve", "x": 210, "y": 100, "size": 16, "label": "Master valve", "value": 1},
    {"id": "pp", "type": "pump", "x": 300, "y": 100, "r": 26, "label": "Pump", "value": 0},
    {"id": "cap", "type": "text", "x": 200, "y": 20, "text": "Fuel plant", "style": "h"}],
    "steps": [{"title": "1 · Fill the tank", "play": [["tk", 0.8, 400]]}, {"title": "2 · Pump runs", "set": {"pp": 1}}]}
FIGURE_TASKS = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - look at the plant", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "read_instrument", "question": "What does the gauge read?", "visual": "a gauge",
     "options": ["2.0 bar", "4.0 bar", "6.0 bar", "8.0 bar"], "correct": "B", "feedback": "The needle is on 4."},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the relief valve.", "visual": "the pump room",
     "answer": "Relief valve*\nPump\nStrainer", "feedback": "It is the small red valve."},
    {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "What is this?", "visual": "the pump room",
     "options": ["A pump", "A boiler", "A tank", "A cooler"], "correct": "A", "feedback": "A pump."},
    {"id": "q04", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the master valve.", "visual": "the plant",
     "answer": "Master valve*\nFuel tank\nPump", "feedback": "It is between the tank and the pump."},
    {"id": "q05", "kind": "self-check", "set": "SC1", "mechanic": "compare", "question": "Which pump room do you accept?", "options": ["Room A", "Room B"],
     "correct": "B", "answer": "Valves labelled: no | yes\nFloor clear: yes | yes", "feedback": "Room B is labelled."},
    {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - Module 1", "text": "Module check on your tablet now.", "minutes": 5},
    {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "label_diagram", "question": "Drag each label to its place.", "visual": "the pump room",
     "answer": "Relief valve\nPump", "feedback": "These are the valve and the pump."},
    {"id": "m02", "kind": "module-check", "set": "MC", "mechanic": "label_diagram", "question": "Drag each label to its place.", "visual": "the plant",
     "answer": "Fuel tank\nMaster valve\nPump", "feedback": "Tank, valve, pump."},
]
FIGURE_BUILD = {"module": 1, "screens": {
    "t01": {"try_tablet": False},
    "q01": {"figure": "assets/img/gauge.png"},
    "q02": {"figure": "assets/img/pump.png", "areas": {"Relief valve": [62.5, 31, 12, 18], "Pump": [20, 40, 30, 35], "Strainer": [5, 5, 15, 20]}},
    "q03": {"figure": "assets/img/pump.png"},
    "q04": {"figure": "plant.kit.json", "unlabel": "all"},
    "q05": {"figures": {"Room A": "assets/img/pump.png", "Room B": "assets/img/gauge.png"}},
    "m01": {"figure": "assets/img/pump.png", "areas": {"Relief valve": [62.5, 31, 12, 18], "Pump": [20, 40, 30, 35]}},
    "m02": {"figure": "plant.kit.json", "unlabel": "all", "kit_step": "Pump runs"}}}


def png(w, h, rgb=(205, 214, 228)):
    """a real .png of w x h pixels, one colour - a photograph stand-in the compiler can read the size of"""
    import struct
    import zlib
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def figures_course(tmp, build=None, screens=FIGURE_TASKS):
    """a course whose tasks stand on real photographs (with their records) and a figure-kit drawing"""
    c, md = new_course(tmp, script(screens=screens), build=False)
    img = os.path.join(md, "assets", "img")
    for name, size in (("pump.png", (600, 400)), ("gauge.png", (1200, 1200)), ("gen.png", (600, 400))):
        io.open(os.path.join(img, name), "wb").write(png(*size))
    io.open(os.path.join(img, "nometa.png"), "wb").write(png(600, 400))
    cs.save(os.path.join(img, "_photo_meta.json"), dict(PHOTO_META, **{
        "pump.png": {"source": "Own photograph, Novikontas", "licence": "own work", "attribution_required": False,
                     "description": "The pump room: the relief valve is the small red one.", "shows": "pump room"},
        "gauge.png": {"source": "Wikimedia Commons", "author": "Jane Doe (Wikimedia Commons user), own work", "licence": "CC BY-SA 4.0",
                      "attribution_required": True, "description": "A pressure gauge reading 4 bar.", "title": "Pressure gauge"},
        "gen.png": {"source": "GENERATED", "generated": True, "description": "A made-up pump room."}}))
    figs = os.path.join(c, "working_claude", "figures", "M01")
    io.open(os.path.join(figs, "plant.kit.json"), "w", encoding="utf-8").write(json.dumps(PLANT_KIT))
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), build or FIGURE_BUILD)
    return c, md


def figures_part(tmp):
    """a task stands on a REAL PHOTOGRAPH or a FIGURE-KIT drawing - the same *.kit.json the deck plays"""
    print("\n-- real photographs and figure-kit drawings on the task pages")
    os.makedirs(os.path.join(tmp, "figtasks"))
    c, md = figures_course(os.path.join(tmp, "figtasks"))
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    check("a module whose tasks stand on photographs and a kit drawing builds clean", code == 0 and "tasks/sc1_look_at_the_plant.html" in out, out)
    p = io.open(os.path.join(md, "tasks", "sc1_look_at_the_plant.html"), encoding="utf-8").read()
    m = io.open(os.path.join(md, "assessment", "check.html"), encoding="utf-8").read()
    code, out = run(MATCH, c, "--module", "1", "--part", "trainee")
    check("check_script_match --part trainee passes on the photo and kit pages", code == 0, out)
    q01, q02, q04 = (p.split('data-script="%s"' % x)[1].split("</section>")[0] for x in ("q01", "q02", "q04"))
    check("a photograph is a real <img> of the module's assets/img, in the shape of the photograph (--ar 1.5), tappable areas over it",
          '<img class="taskfig" src="../assets/img/pump.png"' in q02 and "--ar:1.500" in q02 and q02.count('class="hot"') == 3, q02[:400])
    check("the areas are the build sheet's boxes in % of the photograph - nothing is guessed",
          'style="left:62.5%;top:31%;width:12%;height:18%"' in q02, q02)
    check("a tap on the photograph stays the answer: the picture opens only by its corner button, so the viewer gets the credit "
          "and not what it shows (that could be the answer)",
          'data-about' not in q02 + q01 and 'data-credit="Photo: Pressure gauge · Jane Doe · Wikimedia Commons · CC BY-SA 4.0"' in q01,
          q01[:500])
    check("a photograph read from a task is a big picture beside its four choices (data-pic) - the screen's own height decides its size",
          'data-pic="beside"' in q01 and 'data-mech="read_instrument"' in q01 and "--ar:1.000" in q01, q01[:300])
    check("a task that shows a photograph loads the picture viewer", 'src="../assets/gb_zoom.js"' in p and 'href="../assets/gb_zoom.css"' in p)
    q03 = p.split('data-script="q03"')[1].split("</section>")[0]
    check("a picture beside a plain single-choice question: the photograph, then its choices",
          'data-pic="beside"' in q03 and q03.find("<img") < q03.find('class="opts"'), q03[:400])
    fields = re.findall(r'data-script-field="(opt\.[A-Z])"', q03)
    check("choose-one options are out of the script's order (a script writes the right one first) - the same order every build",
          len(fields) > 1 and fields != sorted(fields), fields)
    q05 = p.split('data-script="q05"')[1].split("</section>")[0]
    check("compare: a picture over each column's choice", q05.count('class="cmpfig"') == 2 and q05.find("cmpfig") < q05.find('class="opt"'), q05[:500])
    # the kit drawing
    check("a kit drawing is the deck's own spec, drawn still at its last step (kit.js: data-kit-step), with no step buttons",
          'data-kit="#kit-task-' in q04 and 'data-kit-step="2"' in q04 and "mediabar" not in p and 'data-act=' not in p, q04[:500])
    check("one spec: the page ships kit.js and kit.css, like the panel's valves",
          '<script src="../assets/kit.js"></script>' in p and 'href="../assets/kit.css"' in p)
    check("a module with no parts of its own loads no kit_parts.js on its task page", "kit_parts.js" not in p)
    io.open(os.path.join(md, "assets", "kit_parts.js"), "w", encoding="utf-8").write("/* a course's new parts */")
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    pk = io.open(os.path.join(md, "tasks", "sc1_look_at_the_plant.html"), encoding="utf-8").read()
    check("a course's own kit parts (assets/kit_parts.js) load on the task page after kit.js, as in the deck - else a "
          "drawing using them says 'unknown part type' and its tap areas collapse (IGF M05 q02)",
          'src="../assets/kit_parts.js"' in pk and pk.index("../assets/kit.js") < pk.index("../assets/kit_parts.js"), out)
    os.remove(os.path.join(md, "assets", "kit_parts.js"))
    spec = json.loads(re.search(r'<script type="application/json" id="kit-task-[^"]+">(.*?)</script>', q04, re.S).group(1))
    check("\"unlabel\": \"all\" takes every word off the drawing (the answers' words) - the parts stay, the caption goes",
          not any(k in pt for pt in spec["parts"] for k in ("label", "caption", "title", "tag")) and len(spec["parts"]) == 3
          and "Fuel tank" not in json.dumps(spec), spec)
    ks = dict(keys_of(p))
    check("a kit part is found by the words it is drawn with, and carries its part id: the engine lays the area on the drawn part",
          'data-part="mv"' in q04 and 'data-part="tk"' in q04 and 'data-part="pp"' in q04 and ks.get("Master valve") == cs.gb_key("q04", "Master valve", 1), q04)
    check("the answers are still only data-key: no word of the spec's labels is in the page's markup outside the keyed buttons",
          "data-correct" not in p)
    m02 = m.split('data-script="m02"')[1].split("</section>")[0]
    check("a named step ('Pump runs') is the step the task page shows: 2", 'data-kit-step="2"' in m02, m02[:300])
    ms = re.search(r'id="kit-task-[^"]+">(.*?)</script>', m02, re.S)
    check("label the kit drawing: the spec gets a band above and below it (\"view\") for the empty label boxes; 3 boxes, 3 leader lines "
          "that follow their parts",
          ms and json.loads(ms.group(1)).get("view", [0, 0, 0, 0])[1] < 0 and m02.count('class="lbox zone"') == 3
          and m02.count("<line") == 3 and m02.count('data-part="') == 3, m02[:600])
    m01 = m.split('data-script="m01"')[1].split("</section>")[0]
    check("label a photograph: the photo sits in a drawing with a band above and below it; its record's credit goes with it",
          "<image " in m01 and 'href="../assets/img/pump.png"' in m01 and re.search(r'viewBox="0 -[\d.]+ 1000', m01) and m01.count('class="lbox zone"') == 2, m01[:500])
    # what must be reported, never invented
    def build_with(**kw):
        return {"module": 1, "screens": dict(FIGURE_BUILD["screens"], **kw)}

    def broken(name, build, text, shown=True):
        cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), build)
        code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
        check(name, code == 1 and text in out, out)

    broken("a photograph that is not in the module is reported, not invented",
           build_with(q02={"figure": "assets/img/missing.png", "areas": {"Relief valve": [1, 1, 10, 10]}}), "its photograph assets/img/missing.png is not there")
    broken("a photograph with no record in _photo_meta.json is reported, never shown without one",
           build_with(q02={"figure": "assets/img/nometa.png", "areas": {"Relief valve": [1, 1, 10, 10]}}), "assets/img/nometa.png has no record")
    broken("a picture made by an image model is refused for what a trainee must recognise",
           build_with(q02={"figure": "assets/img/gen.png", "areas": {"Relief valve": [1, 1, 10, 10]}}), "assets/img/gen.png was made by an image model")
    broken("an answer with no box on a photograph is reported, never guessed",
           build_with(q02={"figure": "assets/img/pump.png", "areas": {"Pump": [1, 1, 10, 10]}}), '"Relief valve" has no place on the photograph')
    broken("an answer that is no part of the kit drawing is reported, with the parts there are",
           build_with(q04={"figure": "plant.kit.json", "areas": {"Master valve": "nope"}}), '"Master valve" is not a part of the kit figure')
    broken("a kit step that does not exist is reported", build_with(m02={"figure": "plant.kit.json", "kit_step": "Cooling"}), '"kit_step" \'Cooling\' is no step')
    broken("'unlabel' naming a part the spec does not have is reported", build_with(q04={"figure": "plant.kit.json", "unlabel": ["zz"]}),
           '"unlabel" names zz')
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), FIGURE_BUILD)
    run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")


EVERY_WAY = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - every way", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "cloze", "question": "Complete the sentence.",
     "answer": "LNG is stored at [-162 °C* | 0 °C | 20 °C], so the tank is [insulated* | painted | heated].", "feedback": "Very cold."},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "choose_and_justify", "question": "The tank pressure rises. What do you do, and why?",
     "options": ["Vent to the mast", "Send the gas to the gas combustion unit", "Isolate a relief valve"], "correct": "B",
     "answer": "It burns the gas safely without venting*\nIt makes room for more liquid\nVenting is the normal way", "feedback": "Venting is for emergencies."},
    {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "scenario", "question": "You are on watch. Choose at each step.",
     "answer": "Gas alarm at 20 % LEL => find the leak* | silence it and carry on\nGas at 40 % LEL at two detectors => the gas is shut off* | carry on | bypass the detectors",
     "feedback": "40 % LEL shuts the gas."},
    {"id": "q04", "kind": "self-check", "set": "SC1", "mechanic": "set_value", "question": "Set the tank temperature alarm.", "visual": "a dial",
     "answer": "-42 °C ± 2, range -60 to 20", "feedback": "-42 °C."},
    {"id": "q05", "kind": "self-check", "set": "SC1", "mechanic": "find_the_fault", "question": "Tank 2 pressure keeps rising. Check the parts, then name the fault.",
     "visual": "the reliquefaction plant",
     "answer": "! Tank 2 pressure rises about 0.05 bar an hour\n! The compressor is running\nCompressor: running at 1,450 rpm\n"
               "Condenser: sea-water outlet 32 °C, 10 °C above normal *\nPressure gauge: reads the same as the second gauge",
     "feedback": "A fouled condenser cannot take the heat away."},
    {"id": "q06", "kind": "self-check", "set": "SC1", "mechanic": "spot_the_error", "question": "Tap every wrong line of the permit.",
     "answer": "Space: cargo tank 2\nOxygen: 18.5 % * => below 20.9 % - nobody enters\nHydrocarbon: 0 % LFL\n"
               "Rescue team: not assigned * => a rescue team stands by before anyone enters\nSigned: Chief Officer",
     "feedback": "Oxygen 20.9 % and a rescue team."},
    {"id": "q07", "kind": "self-check", "set": "SC1", "mechanic": "build_the_plan", "question": "Build the plan for tank entry. Not every card belongs.",
     "answer": "Ventilate the tank *\nMeasure the atmosphere *\nIssue the entry permit *\nStart loading cargo\nOpen the manifold valve",
     "feedback": "Ventilate, measure, permit."},
    {"id": "q08", "kind": "self-check", "set": "SC1", "mechanic": "timeline", "question": "Rebuild the night, then tap where it should have stopped.",
     "answer": "The compressor tripped at 02:10\nTank pressure rose past the alarm set point *\nThe alarm was silenced and not reported\nThe relief valve lifted at 04:30",
     "feedback": "The alarm was the barrier."},
    {"id": "q09", "kind": "self-check", "set": "SC1", "mechanic": "compare", "question": "Which loading plan do you sign?",
     "options": ["Plan A", "Plan B"], "correct": "B", "answer": "Trim at the end: 1.2 m | 0.3 m\nHighest shear force: 92 % | 71 %",
     "feedback": "Plan B keeps the shear force inside the limit."},
    {"id": "q10", "kind": "self-check", "set": "SC1", "mechanic": "panel_operate", "question": "Line up the bunkering valves.", "visual": "the bunker panel",
     "answer": "Master gas valve = closed\nVent fan = running\nBunker valve = open\nPurge mode = Auto", "feedback": "Gas closed, fan running."},
]


def every_way_part(tmp):
    """the ten ways of answering added in 2.38.0 - built by the compiler, graded by the one shared engine"""
    print("\n-- every way of answering an approved script can hold")
    os.makedirs(os.path.join(tmp, "w"))
    sc = script(screens=EVERY_WAY)
    wrong = [x for q in sc["screens"] if q["kind"] in cs.TASKS for x in cs.read_answer(q)[0]]
    check("every task of the fixture is written as an approved script may write it", wrong == [], wrong)
    c, md = new_course(os.path.join(tmp, "w"), sc, build=False)
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "t01": {"try_tablet": False}, "q05": {"figure": "assets/fig/scale.svg"}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_every_way.html")
    check("the set is compiled, nothing left as it is", code == 0 and os.path.isfile(page) and "left as it is" not in out, out)
    if not os.path.isfile(page):
        return
    code, out = run(MATCH, c, "--module", "1", "--part", "trainee")
    check("check_script_match --part trainee passes: every word and every right answer as approved", code == 0, out)
    p = io.open(page, encoding="utf-8").read()
    ks = dict(keys_of(p))
    check("no answer readable in the page", "data-correct" not in p and "data-answer" not in p)
    check("complete the sentence: the sentence's words stay, each gap has its choices, the right one keyed 1",
          '<span data-script-field="answer">LNG is stored at</span> <button type="button" class="gap" data-g="1"' in p
          and '</button><span data-script-field="answer">, so the tank is</span>' in p
          and ks.get("-162 °C") == cs.gb_key("q01", "-162 °C", 1) and ks.get("painted") == cs.gb_key("q01", "painted", 0)
          and p.count('class="cg opts" data-g=') == 2)
    check("choose the action, then the reason: the actions as options, the reasons keyed 1 / 0, one Check",
          'class="cj"' in p and ks.get("Send the gas to the gas combustion unit") == cs.gb_key("q02", "Send the gas to the gas combustion unit", 1)
          and ks.get("It burns the gas safely without venting") == cs.gb_key("q02", "It burns the gas safely without venting", 1))
    sec3 = re.search(r'<section class="scr" data-script="q03".*?</section>', p, re.S).group(0)
    check("scenario: one part per step, each with its situation and its actions",
          sec3.count('<div class="part step">') == 2 and '<p class="sit" data-script-field="answer">Gas alarm at 20 % LEL</p>' in sec3
          and ks.get("the gas is shut off") == cs.gb_key("q03", "the gas is shut off", 1))
    dial = re.search(r'<div class="dial"[^>]*>', p).group(0)
    check("set the value: a dial from -60 to 20 in steps of 2, one key per accepted step (-44, -42, -40) and no value in the page",
          'data-lo="-60" data-hi="20" data-step="2" data-dec="0"' in dial
          and re.search(r'data-key="([0-9a-f ]+)"', dial).group(1).split() == [cs.gb_key("q04", "°C", v) for v in ("-44", "-42", "-40")]
          and "-42" not in dial, dial)
    check("find the fault: the symptoms, a card per part to turn over, the faulty part keyed 1; its picture from the build sheet",
          '<p data-script-field="answer">Tank 2 pressure rises about 0.05 bar an hour</p>' in p and p.count('class="ffc"') == 3
          and ks.get("Condenser") == cs.gb_key("q05", "Condenser", 1) and ks.get("Compressor") == cs.gb_key("q05", "Compressor", 0)
          and re.search(r'data-script="q05".*?<div class="ffhead">\s*<div class="instrument">', p, re.S) and 'src="../assets/gb_zoom.js"' in p)
    check("spot the errors: the document in its order, each line keyed, each why shown after the Check",
          ks.get("Oxygen: 18.5 %") == cs.gb_key("q06", "Oxygen: 18.5 %", 1) and ks.get("Space: cargo tank 2") == cs.gb_key("q06", "Space: cargo tank 2", 0)
          and p.index("Space: cargo tank 2") < p.index("Oxygen: 18.5 %") < p.index("Signed: Chief Officer")
          and '<p class="ewhy" data-script-field="answer">below 20.9 % - nobody enters</p>' in p)
    plan = re.findall(r'data-key="([0-9a-f]{8})" data-place="([0-9a-f]{8})">([^<]+)<', p)
    pl = {t: (k, pk) for k, pk, t in plan}
    check("build the plan: a slot per card that belongs; a card says if it belongs (data-key) and where (data-place, 0 = out)",
          'data-script="q07" data-mech="build_the_plan" data-need="slots"' in p
          and pl.get("Measure the atmosphere") == (cs.gb_key("q07", "Measure the atmosphere", 1), cs.gb_key("q07", "Measure the atmosphere", 2))
          and pl.get("Start loading cargo") == (cs.gb_key("q07", "Start loading cargo", 0), cs.gb_key("q07", "Start loading cargo", 0)), pl)
    check("rebuild the incident: part 1 the order (data-place), part 2 the stop point (data-key 1)",
          pl.get("Tank pressure rose past the alarm set point") == (cs.gb_key("q08", "Tank pressure rose past the alarm set point", 1),
                                                                     cs.gb_key("q08", "Tank pressure rose past the alarm set point", 2))
          and '<div class="part" data-kind="stop">' in p)
    check("compare: the options as columns, chosen by name or by any figure of the column",
          '<button type="button" class="opt" id="q09-B" data-script-field="opt.B" data-key="%s">Plan B</button>' % cs.gb_key("q09", "Plan B", 1) in p
          and '<td data-for="q09-A" data-script-field="answer">92 %</td>' in p)
    gas = re.search(r'data-val="Master gas valve".*?</div></div>', p, re.S).group(0)
    check("operate the panel: each control with every position; the one it must end in keyed with the control's name",
          'data-key="%s">closed<' % cs.gb_key("q10", "closed", "Master gas valve") in gas
          and 'data-key="%s">open<' % cs.gb_key("q10", "open", "-") in gas
          and ks.get("stopped") == cs.gb_key("q10", "stopped", "-") and ">Manual</button>" in p, gas)
    check("operate the panel: a valve and a pump drawn by the figure kit, shipped with the module",
          '"type":"valve"' in p and '"type":"pump"' in p and 'src="../assets/kit.js"' in p and 'href="../assets/kit.css"' in p
          and p.index("kit.js") < p.index("gb_answer.js"))
    tp = os.path.join(SKILLS, "course-task-ux", "scripts", "check_task_pages.py")
    code, out = run(tp, page, "--only", "deadmarkup")
    check("check_task_pages finds no dead markup on it", code == 0, out[-800:])
    # the checker's own rule for the panel: another position is the panel's word - any other extra word is not
    io.open(page, "w", encoding="utf-8").write(p.replace('data-state data-script-field="answer" data-key="%s">Manual' % ks["Manual"],
                                                         'data-script-field="answer" data-key="%s">Manual' % ks["Manual"]))
    code, out = run(MATCH, c, "--module", "1", "--part", "trainee")
    check("a word on the panel that is not a control's position is still caught", code == 1 and "q10" in out, out)
    sb = os.path.join(c, "working_claude", "script", "M01.build.json")
    sc["screens"][-1]["answer"] = sc["screens"][-1]["answer"].replace("Purge mode = Auto", "Purge mode = Sweep")
    sc.update(approved_hash=cs.content_hash(sc))
    cs.save(os.path.join(c, "working_claude", "script", "M01.json"), sc)
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    check("a control whose positions are not known is reported, never guessed", code == 1 and 'positions of "Purge mode" are not known' in out, out)
    cs.save(sb, {"module": 1, "screens": {"t01": {"try_tablet": False}, "q10": {"states": {"Purge mode": ["Off", "Sweep", "Hold"]}}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    p = io.open(page, encoding="utf-8").read()
    check("... and taken from the build sheet when it lists them", code == 0 and ">Hold</button>" in p, out)
    # found on the IGF pilot's drawings: a place outlined by a path, inside a group moved by translate()
    sys.path.insert(0, HERE)
    import task_pages
    g = '<g id="t-b" transform="translate(300 0)"><path class="hit" d="M84 104 H216 L236 124 V262 L216 282 H84 L64 262 V124 Z"/></g>'
    check("a place outlined by a straight-line path, in a group moved by translate(), is found where it is drawn",
          task_pages.shape_box(g) == (364.0, 104.0, 172.0, 178.0), task_pages.shape_box(g))
    check("a curved path is left to a rect or circle of class hit", task_pages.shape_box('<path class="hit" d="M0 0 C 1 2 3 4 5 6"/>') is None)


TEAMWORK = SCREENS[:6] + [
    {"id": "t03", "kind": "task-slide", "opens": "TT1", "title": "Team task 1 - plan the bunkering",
     "text": "Team task on your tablets now.\nOne answer for the team.", "minutes": 5,
     "team": {"size": "3-4", "roles": ["Leader", "Recorder", "Checker"], "scope": "team"}},
    {"id": "p01", "kind": "self-check", "set": "TT1", "mechanic": "order", "question": "Put the bunkering steps in order.",
     "answer": "Safety meeting\nConnect the hose\nTransfer\nDisconnect", "feedback": "Meeting first."},
    {"id": "p02", "kind": "self-check", "set": "TT1", "question": "Who stops the transfer when contact is lost?",
     "options": ["Either side, at once", "Only the bunker vessel"], "correct": "A", "feedback": "Either side.", "mechanic": "single_choice"},
    {"id": "t04", "kind": "task-slide", "opens": "TT2", "title": "Team task 2 - check each other",
     "text": "Each of you answers on your own tablet.", "minutes": 3, "team": {"size": "2", "scope": "member"}},
    {"id": "p03", "kind": "self-check", "set": "TT2", "question": "Where is the fuel prepared?", "options": ["Fuel preparation room", "Bridge"],
     "correct": "A", "feedback": "Pumps and vaporizers are there.", "mechanic": "single_choice"},
] + SCREENS[6:]


def team_part(tmp):
    """a team task (classroom-system.json team_task): marked on the slide and the page, the team shown by the engine"""
    print("\n-- a team task")
    os.makedirs(os.path.join(tmp, "team"))
    c, md = new_course(os.path.join(tmp, "team"), script(screens=TEAMWORK))
    code, out = run(COMPILE, c, "--module", "1")
    tt1, tt2 = os.path.join(md, "tasks", "tt1_plan_the_bunkering.html"), os.path.join(md, "tasks", "tt2_check_each_other.html")
    check("a team task's page is compiled, not left as it is", code == 0 and os.path.isfile(tt1) and os.path.isfile(tt2)
          and "left as it is" not in out, out)
    if not os.path.isfile(tt1):
        return
    p1, p2, d = io.open(tt1, encoding="utf-8").read(), io.open(tt2, encoding="utf-8").read(), deck(md)
    check("the page says it is a team task, its roles and how it hands in (task-mode, task-roles, task-scope)",
          '<meta name="task-mode" content="team">' in p1 and '<meta name="task-roles" content="Leader|Recorder|Checker">' in p1
          and '<meta name="task-scope" content="team">' in p1 and '<meta name="task-scope" content="member">' in p2)
    check("the slide says it too: data-mode, data-team-size, data-roles",
          re.search(r'<section [^>]*data-activity="TT1"[^>]*data-mode="team" data-team-size="3-4" data-roles="Leader\|Recorder\|Checker"', d)
          and re.search(r'<section [^>]*data-activity="TT2"[^>]*data-mode="team" data-team-size="2"', d), d[:300])
    check("the team's name and the trainee's role have their place at the top, hidden until the classroom sends them",
          '<div class="teambar" id="teamBar" hidden>' in p1 and p1.index('id="teamBar"') < p1.index('<header class="state">'))
    check("an individual task carries none of it", "task-mode" not in io.open(os.path.join(md, "tasks", "sc1_the_new_spaces.html"),
                                                                          encoding="utf-8").read())
    code, out = run(MATCH, c, "--module", "1", "--part", "trainee")
    check("check_script_match --part trainee passes on the team pages", code == 0, out)
    code, out = run(os.path.join(SKILL, "scripts", "check_course_package.py"), os.path.join(c, "modules"), "--no-importer")
    check("check_course_package finds nothing wrong with the team tasks (both marks, gb-team, the 2 s fallback, scope: 'team')",
          not re.search(r"tt[12]_|data-team-size|task-scope|gb-team", out), out)


IN_LANGUAGE = {
    "Latvian": [
        {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Paškontrole 1 - vārsti", "text": "Paškontrole planšetē tagad.", "minutes": 4},
        {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "cloze", "question": "Pabeidz teikumu.",
         "answer": "SDG glabā [-162 °C* | 0 °C | 20 °C] temperatūrā.", "feedback": "Ļoti auksts."},
        {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "set_value", "question": "Iestati trauksmes temperatūru.",
         "visual": "skala", "answer": "-42,5 °C ± 0,5, range -60 to 20", "feedback": "-42,5 °C."},
        {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "panel_operate", "question": "Sagatavo vārstu līniju.",
         "visual": "panelis", "answer": "Galvenais gāzes vārsts = aizvērts\nVentilators = darbojas", "feedback": "Gāze ciet, ventilators strādā."},
        {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Moduļa pārbaude - 1. modulis", "text": "Moduļa pārbaude planšetē tagad.", "minutes": 4},
        {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "single_choice", "question": "Kur sagatavo degvielu?",
         "options": ["Degvielas sagatavošanas telpā", "Uz tiltiņa"], "correct": "A", "feedback": "Tur ir sūkņi un iztvaicētāji."}],
    "Russian": [
        {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Самопроверка 1 - клапаны", "text": "Самопроверка на планшете.", "minutes": 4},
        {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "cloze", "question": "Дополни предложение.",
         "answer": "СПГ хранится при [-162 °C* | 0 °C | 20 °C].", "feedback": "Очень холодно."},
        {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "set_value", "question": "Установи температуру тревоги.",
         "visual": "шкала", "answer": "-42,5 °C ± 0,5, range -60 to 20", "feedback": "-42,5 °C."},
        {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "panel_operate", "question": "Выставь клапаны.",
         "visual": "панель", "answer": "Главный газовый клапан = закрыт\nВентилятор = работает", "feedback": "Газ закрыт, вентилятор работает."},
        {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Проверка по модулю - модуль 1", "text": "Проверка на планшете.", "minutes": 4},
        {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "single_choice", "question": "Где готовят топливо?",
         "options": ["В помещении подготовки топлива", "На мостике"], "correct": "A", "feedback": "Там насосы и испарители."}],
}


def language_part(tmp):
    """L19 COURSE_LANGUAGE: the task screen's own words in the course language - lv and ru, flagged PROVISIONAL"""
    print("\n-- the task screens in Latvian and Russian")
    sys.path.insert(0, HERE)
    import task_pages
    words = {"Latvian": ("lv", "Sākt paškontroli", "1. moduļa pārbaude", "Ieskaites slieksnis 70 % – 1 no 1 pareizi", "atvērts", "Pieskaries tukšajai vietai"),
             "Russian": ("ru", "Начать самопроверку", "Проверка по модулю 1", "Проходной балл 70 % – 1 из 1 правильно", "открыт", "Коснись пропуска")}
    for lang, (code_l, start, mc_title, pass_line, other, cloze_say) in words.items():
        os.makedirs(os.path.join(tmp, code_l))
        sc = script(screens=IN_LANGUAGE[lang])
        sc["course_language"] = lang
        sc.update(approved_hash=cs.content_hash(sc))
        c, md = new_course(os.path.join(tmp, code_l), sc, build=False)
        cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
        code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
        sc1 = [f for f in os.listdir(os.path.join(md, "tasks")) if f.startswith("sc1_")]
        p = io.open(os.path.join(md, "tasks", sc1[0]), encoding="utf-8").read() if sc1 else ""
        m = io.open(os.path.join(md, "assessment", "check.html"), encoding="utf-8").read() if code == 0 else ""
        check("%s: compiled with no language problem, the page marked lang=\"%s\"" % (lang, code_l),
              code == 0 and '<html lang="%s">' % code_l in p and "not in the factory in that language" not in out, out)
        check("%s: the page's own words are %s - start, the gap's prompt, the module check's title and pass mark" % (lang, lang),
              start in p and cloze_say in p and "<title>MC — %s</title>" % mc_title in m and pass_line in m, (p[-600:], m[:900]))
        check("%s: no English word of the factory's left on the page" % lang,
              not re.search(r">(Start the self-check|Back|Your score|Start again|Tap a gap|Less|More)<", p + m))
        check("%s: the dial's scale reads −60 °C to 20 °C; its keys stay the same in every language (-43.0 / -42.5 / -42.0)" % lang,
              "<span>−60 °C</span><span>20 °C</span>" in p and re.search(r'data-key="([0-9a-f ]+)"', p.split('class="dial"')[1]).group(1).split()
              == [cs.gb_key("q02", "°C", v) for v in ("-43.0", "-42.5", "-42.0")], p.split('class="dial"')[1][:300])
        check("%s: the panel offers the other position in the course language, and draws the valve" % lang,
              ">%s</button>" % other in p and '"type":"valve"' in p and '"type":"pump"' in p)
        code, out = run(MATCH, c, "--module", "1", "--part", "trainee")
        check("%s: check_script_match passes" % lang, code == 0, out)
    eng = io.open(os.path.join(SKILLS, "course-task-ux", "assets", "gb_answer.js"), encoding="utf-8").read()
    check("the engine has its words in lv and ru, chosen by <html lang>, marked PROVISIONAL",
          "Pārbaudīt" in eng and "Проверить" in eng and "PROVISIONAL" in eng and "documentElement.getAttribute('lang')" in eng)
    check("the compiler's words are PROVISIONAL too, and listed for review",
          "PROVISIONAL" in io.open(os.path.join(HERE, "task_pages.py"), encoding="utf-8").read()
          and os.path.isfile(os.path.join(SKILL, "compile", "TRANSLATIONS_REVIEW.md")) and set(task_pages.WORDS) == {"en", "lv", "ru"})
    # a language the factory has no words for is reported - the page is built, its own words English, never silently
    os.makedirs(os.path.join(tmp, "no"))
    sc = script(screens=IN_LANGUAGE["Latvian"])
    sc["course_language"] = "Norwegian"
    sc.update(approved_hash=cs.content_hash(sc))
    c, md = new_course(os.path.join(tmp, "no"), sc, build=False)
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    check("Norwegian: reported (the course is in Norwegian - the words are not in the factory in that language), page lang=\"no\"",
          code == 1 and "the course is in Norwegian" in out and "not in the factory in that language" in out, out)
    check("'Latvian' is lv everywhere, never 'la'", task_pages.cm.lang_code("Latvian") == "lv" and task_pages.cm.lang_code("Latviešu") == "lv"
          and task_pages.cm.lang_code("ru") == "ru" and task_pages.cm.lang_code("Klingon") is None)


def build_of(c, mutate):
    """change the course's build sheet with `mutate(sheet)` and save it"""
    bp = os.path.join(c, "working_claude", "script", "M01.build.json")
    sheet = cs.load(bp)
    mutate(sheet)
    cs.save(bp, sheet)
    return sheet


LAYOUTS = cs.load(os.path.join(SKILLS, "course-module-ui", "knowledge", "layout-templates.json"))
LONG_LINES = ["The tank connection space surrounds every pipe, valve and instrument that joins the fuel tank, and it is gas-tight "
              "to the ship around it, so a leak at a flange or a valve gland stays inside the space.",
              "• Its ventilation runs all the time and changes the air at least 30 times an hour.",
              "• Gas detectors at the top and the bottom of the space raise the alarm at 20 % LEL.",
              "• At 40 % LEL the master gas valve closes and the bunkering stops at once.",
              "The space is entered only with a permit: the atmosphere is measured, the ventilation proved and a second person "
              "stands at the entrance; inside, the escape route is kept clear and the lighting is certified for a gas atmosphere.",
              "After work every opened flange is tested for tightness before gas is let back into the pipes, and the test is "
              "written in the log with the pressure, the time and the name of the person who did it."]


def layouts_part(tmp):
    """L61 (2.52.0) - every slide is one of the owner's layout templates, in the brandbook's colours, with the official logo"""
    print("\n-- L61: every slide is one of the owner's layout templates")
    os.makedirs(os.path.join(tmp, "lt"))
    c, md = new_course(os.path.join(tmp, "lt"), script())
    code, out = run(COMPILE, c, "--module", "1")
    page = deck(md)
    slides = re.findall(r'<section [^>]*>', page)
    named = [(re.search(r'data-template="([\w-]+)\.v(\d+)"', x), re.search(r'data-variant="([\w-]+)"', x)) for x in slides]
    check("every slide names its template and variant", slides and all(t and v for t, v in named), [x[:160] for x in slides])
    check("... and each is one of the catalogue's thirteen, with one of its variants",
          len(LAYOUTS["templates"]) == 13 and all(t.group(1) in LAYOUTS["templates"] and v.group(1) in LAYOUTS["templates"][t.group(1)]["variants"]
                                                   for t, v in named if t and v), [(t.group(0), v.group(0)) for t, v in named if t and v])
    want = {"s01": ("photo-explain", "full"), "s02": ("explain-figure", "figure-right"), "s03": ("figure-stage", "figure"),
            "t01": ("task-launch", "tablet"), "t02": ("task-launch", "check")}
    got = {sid: (re.search(r'data-template="([\w-]+)\.', section(page, sid)) or re.search("$^", "")) for sid in want}
    check("the template comes from the slide: a full photograph, a split figure, a stage, a task, the module check",
          all(got[s] and (got[s].group(1), re.search(r'data-variant="([\w-]+)"', section(page, s)).group(1)) == w for s, w in want.items()),
          {s: section(page, s)[:200] for s in want})
    check("the deck loads the templates' look (gb_layouts.css) after gb_compose.css",
          page.index("gb_compose.css") < page.index("gb_layouts.css"), page[:1500])
    check("... and the module carries it, the official logo and the bundled Raleway (the brandbook's typeface, offline)",
          all(os.path.isfile(os.path.join(md, "assets", f)) for f in ("gb_layouts.css", "novikontas_logo.svg", "raleway-variable.ttf")))
    css = io.open(os.path.join(SKILLS, "course-module-ui", "templates", "gb_layouts.css"), encoding="utf-8").read()
    brand = {"#0A2463", "#53A7DB", "#011111", "#415C8F", "#E7EBF0", "#FFFFFF"}
    hexes = set(x.upper() for x in re.findall(r"#[0-9A-Fa-f]{6}\b", css))
    check("its colours are the brandbook's six, and the few tints between them - no amber, no other blue",
          brand <= hexes and not hexes & {"#E9A51E", "#E9AB39", "#2EB6F8"}, sorted(hexes))
    check("... the logo is the official file, used as it is; on a dark (blue) slide its white version, no plate (owner, 2026-10-21)",
          'url("novikontas_logo.svg")' in css and 'url("novikontas_logo_white.svg")' in css
          and os.path.isfile(os.path.join(md, "assets", "novikontas_logo_white.svg")))
    check("the built deck still says exactly the approved words", run(MATCH, c, "--module", "1", "--part", "instructor")[0] == 0)

    print("\n-- L61: the owner's rules - 55 / 45, dense text has a picture, never three slides in a row without one")
    def fresh(name, screens, sheet=None):
        os.makedirs(os.path.join(tmp, name))
        c2, md2 = new_course(os.path.join(tmp, name), script(screens=screens))
        if sheet:
            build_of(c2, lambda b: b["screens"].update(sheet))
        code2, out2 = run(COMPILE, c2, "--module", "1")
        return c2, md2, code2, out2
    c2, md2, code, out = fresh("split", SCREENS, {"s02": {"figure": "assets/fig/scale.svg", "split": 0.5}})
    check("a build sheet sets the text share of a split slide: \"split\": 0.5 -> --lt-text:50",
          code == 0 and 'style="--lt-text:50"' in section(deck(md2), "s02"), out + section(deck(md2), "s02")[:300])
    c2, md2, code, out = fresh("split2", SCREENS, {"s02": {"figure": "assets/fig/scale.svg", "split": 0.7}})
    check("caught: a split outside 50-60 % text", code == 1 and "\"split\": 0.7 - the text takes 50-60 %" in out, out)

    dense = {"id": "s05", "kind": "slide", "title": "Why gas needs its own rules", "visual_kind": "none", "minutes": 3,
             "text": "\n".join(LONG_LINES[:3])}
    scr = json.loads(json.dumps(SCREENS))
    scr.insert(4, dense)
    c2, md2, code, out = fresh("dense", scr)
    check("caught: a slide of more than 60 words with no picture beside it",
          code == 1 and "words and no picture beside them - dense text always has" in out and "(s05)" in out, out)

    short = lambda i: {"id": "x%d" % i, "kind": "slide", "title": "Point %d" % i, "visual_kind": "none", "minutes": 1,
                       "text": "A short point, said plainly."}
    scr = json.loads(json.dumps(SCREENS))
    scr[4:4] = [short(1), short(2)]
    c2, md2, code, out = fresh("two", scr)
    check("two text-only slides in a row are fine", "three teaching slides in a row" not in out, out)
    scr = json.loads(json.dumps(SCREENS))
    scr[4:4] = [short(1), short(2), short(3)]
    c2, md2, code, out = fresh("three", scr)
    check("caught: a third teaching slide in a row without a teaching picture",
          code == 1 and "three teaching slides in a row without a teaching picture (x1, x2, x3)" in out, out)
    scr = json.loads(json.dumps(SCREENS))
    i = [x["id"] for x in scr].index("t01")
    scr[i:i] = [short(1), short(2)]
    scr.insert(i + 4, short(3))         # x1 x2, the task launch t01 and its question, then x3: the task does not break the run
    c2, md2, code, out = fresh("task", scr)
    check("... a task launch between them neither counts nor breaks the run", "three teaching slides in a row" in out, out)

    print("\n-- L61: a template asked for by name, and the ones built from the words")
    c2, md2, code, out = fresh("unknown", SCREENS, {"s02": {"figure": "assets/fig/scale.svg", "template": "fancy-layout"}})
    check("caught: a template the factory does not have", code == 1 and "asks for the template \"fancy-layout\" - the templates are" in out, out)
    c2, md2, code, out = fresh("unfit", SCREENS, {"s02": {"figure": "assets/fig/scale.svg", "template": "photo-explain"}})
    check("caught: a template that does not suit the slide (photo-explain without a photograph)",
          code == 1 and "asks for the template photo-explain, which needs a photograph" in out, out)
    c2, md2, code, out = fresh("variant", SCREENS, {"s02": {"figure": "assets/fig/scale.svg", "template": "explain-figure", "variant": "diagonal"}})
    check("caught: a variant the template does not have", code == 1 and "has no variant \"diagonal\"" in out, out)
    c2, md2, code, out = fresh("stage", SCREENS, {"s02": {"figure": "assets/fig/scale.svg", "template": "figure-stage"}})
    s = section(deck(md2), "s02")
    check("a template asked for by name decides the layout (figure-stage -> a stage)",
          'data-template="figure-stage.v1"' in s and "slide-body stage" in s, s[:400])

    long_slide = {"id": "s05", "kind": "slide", "title": "The tank connection space", "layout": "split", "visual_kind": "schematic",
                  "visual": "The space.", "minutes": 5, "text": "\n".join(LONG_LINES)}
    table = {"id": "s06", "kind": "slide", "title": "Three fuels compared", "layout": "split", "visual_kind": "comparison", "visual": "Tanks.",
             "minutes": 3, "text": "LNG | about -162 °C\nLPG | about -42 °C\nMethanol | room temperature\nThe colder the fuel, the more insulation."}
    blocks = {"id": "s07", "kind": "slide", "title": "The safety system", "layout": "split", "visual_kind": "schematic", "visual": "Loop.",
              "minutes": 3, "text": "Detection\nThe gas is found.\nShutdown\nThe valve closes.\nVentilation\nThe gas is cleared."}
    two = {"id": "s08", "kind": "slide", "title": "Drawing and ship", "layout": "split", "visual_kind": "comparison", "visual": "Both.",
           "minutes": 2, "text": "The drawing\nHow the parts connect.\nThe ship\nWhat you see on board."}
    scr = json.loads(json.dumps(SCREENS))
    scr[4:4] = [long_slide, table, blocks, two]
    c2, md2, code, out = fresh("built", scr, {
        "s05": {"figure": "assets/fig/scale.svg"}, "s06": {"figure": "assets/fig/scale.svg"},
        "s07": {"figure": "assets/fig/scale.svg", "template": "three-content-blocks", "blocks": [[1, 2], [3, 4], [5, 6]]},
        "s08": {"figure": "assets/fig/scale.svg", "figure_b": "hull.svg", "template": "compare-two", "blocks": [[1, 2], [3, 4]]}})
    page = deck(md2)
    s5, s6, s7, s8 = (section(page, x) for x in ("s05", "s06", "s07", "s08"))
    parts = re.findall(r'<div class="lt-part[^"]*" data-part="(\d)">', s5)
    order = [int(x) for x in re.findall(r'data-i="(\d+)"', s5)]
    check("more than 135 words beside a picture become content-in-parts: two parts or more, the first shown",
          'data-template="content-in-parts.v1"' in s5 and len(parts) >= 2 and 'class="lt-part on" data-part="1"' in s5, s5[:600])
    check("... every approved line in a part, once, in order - nothing cut", order == list(range(1, len(LONG_LINES) + 1)), order)
    check("... with a numbered tab for each part (Next walks them too - gb_deck.js)",
          len(re.findall(r'<button type="button" class="lt-tab', s5)) == len(parts) and "lt-part" in io.open(os.path.join(md2, "assets", "gb_deck.js"), encoding="utf-8").read())
    check("lines with cells \" | \" are a table: reference-table, one row a line, the separator kept (hidden)",
          'data-template="reference-table.v1"' in s6 and s6.count('<tr data-script-field="text"') == 3 and '<span class="lt-sep"> | </span>' in s6, s6[:700])
    check("three-content-blocks: three numbered blocks beside the picture", 'data-template="three-content-blocks.v1"' in s7
          and s7.count('class="lt-block"') == 3, s7[:700])
    check("compare-two: two cards, each its own picture and its block", 'data-template="compare-two.v1"' in s8
          and s8.count('class="lt-card"') == 2 and s8.count("<svg") >= 2, s8[:900])
    check("... and all of it still says exactly the approved words",
          run(MATCH, c2, "--module", "1", "--part", "instructor")[0] == 0, run(MATCH, c2, "--module", "1", "--part", "instructor")[1])


def variety_part(tmp):
    """L62 (2.53.0) - two slides in a row never look the same; small photographs enlarged, never blocky"""
    print("\n-- L62: never the same look twice in a row")
    sys.path.insert(0, HERE)
    import compile_module as cm
    from PIL import Image
    words = "The tank connection space holds every valve and flange of the fuel tank, so a leak stays inside it.\n" \
            "• Its ventilation runs all the time.\n• Detectors raise the alarm at 20 % LEL."
    drawn = [{"id": "d%d" % i, "kind": "slide", "title": "Drawing slide %d" % i, "layout": "split", "visual_kind": "schematic",
              "visual": "The space.", "minutes": 2, "text": words} for i in range(1, 7)]
    shot = [{"id": "p%d" % i, "kind": "slide", "title": "Photo slide %d" % i, "layout": "split", "visual_kind": "photo",
             "visual": "A ship.", "minutes": 2, "text": words} for i in range(1, 5)]
    os.makedirs(os.path.join(tmp, "var"))
    c, md = new_course(os.path.join(tmp, "var"), script(screens=drawn + shot + SCREENS[-2:]))
    meta = cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
    for i in range(1, 5):
        io.open(os.path.join(md, "assets", "img", "p%d.png" % i), "wb").write(png(400, 250, (40 * i, 90, 160)))
        meta["p%d.png" % i] = dict(PHOTO_META["ship.jpg"], description="Ship %d." % i, url_or_origin="https://example.org/ship%d" % i)
    cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)
    sheet = {x["id"]: {"figure": "ga.html"} for x in drawn}
    sheet.update({x["id"]: {"figure": "assets/img/%s.png" % x["id"]} for x in shot})
    build_of(c, lambda b: b.__setitem__("screens", sheet))
    code, out = run(COMPILE, c, "--module", "1")
    page = deck(md)
    secs = re.findall(r"<section [^>]*>.*?</section>", page, re.S)
    keys = [cm.layout_key(x) for x in secs]
    ids = [re.search(r'id="(\w+)"', x).group(1) for x in secs]
    check("ten split slides in a row, all with the same layout asked for: no two neighbours look the same",
          all(a != b for a, b in zip(keys, keys[1:])) and "looks exactly like the slide before it" not in out, list(zip(ids, keys)))
    drawn_keys = [k for i, k in zip(ids, keys) if i.startswith("d")]
    check("... the drawings (made for a white page) keep the light ground - they move side instead",
          all(g == "light" for _, g in drawn_keys) and {s for s, _ in drawn_keys} == {"picture-right", "picture-left"}, drawn_keys)
    shot_keys = [k for i, k in zip(ids, keys) if i.startswith("p")]
    check("... the photographs take more looks: on top, the other side, the dark ground, framed",
          len(set(shot_keys)) >= 3, shot_keys)
    check("... and each slide still says exactly the approved words", run(MATCH, c, "--module", "1", "--part", "instructor")[0] == 0)

    print("\n-- L62: a small photograph is enlarged, never shown as blocks of pixels")
    big = Image.open(os.path.join(md, "assets", "img", "p1.png")).size
    keep = os.path.join(c, "working_claude", "photo_originals", "M01", "p1.png")
    check("a 400 x 250 photograph is shipped at 1600 px on its long side (never more than 4 times larger)", max(big) == 1600 and big == (1600, 1000), big)
    check("... its original is kept for the factory (working_claude/photo_originals/M01/)",
          os.path.isfile(keep) and Image.open(keep).size == (400, 250))
    check("... and the build says it was small - find a larger one", "p1.png was only 400 x 250 px - enlarged to 1600 x 1000" in out, out)
    code2, out2 = run(COMPILE, c, "--module", "1", "--force")
    check("built again, it is not enlarged twice and the original stays the original",
          Image.open(os.path.join(md, "assets", "img", "p1.png")).size == (1600, 1000) and Image.open(keep).size == (400, 250)
          and "p1.png was only" not in out2, out2[-600:])

    print("\n-- L62: the logo is larger, and a light panel stays light on a dark slide")
    css = io.open(os.path.join(SKILLS, "course-module-ui", "templates", "gb_layouts.css"), encoding="utf-8").read()
    check("the logo box is sized for the artwork (10.5 vmin tall) with the file's own clear space running into the margin",
          "--lt-logo-h:16.9vmin" in css and "right:calc(var(--lt-pad-x) - var(--lt-logo-w) * .159)" in css)
    white = io.open(os.path.join(SKILLS, "..", "resources", "brand", "novikontas_logo_white.svg"), encoding="utf-8").read()
    navy = io.open(os.path.join(SKILLS, "..", "resources", "brand", "novikontas_logo.svg"), encoding="utf-8").read()
    check("the white logo is the official file with its one colour switched - the same shapes, nothing else changed",
          white.replace('fill="#FFFFFF"', 'fill="#022367"').replace(" (white, for dark backgrounds)", "") == navy)
    check("... on a dark slide no plate, and over a photograph the corner behind it is darkened, not the logo",
          "border-radius:0;box-shadow:none" in css and ".slide[data-template].photo .slide-kind::before" in css)
    check("... and a long title leaves room for it", "max-width:min(24em,calc(100% - var(--lt-logo-w)))" in css)
    check("a light panel on a dark slide keeps its white ground and dark words",
          ".slide[data-template].dark .fill.fig.lt-light{background:var(--lt-white)" in css
          and ".fill.fig.lt-light{color:var(--lt-black)}" in css)


def fixes_part(tmp):
    """2.49.1 - the problems found building IGF Module 6 with the compiler (C1-C16)"""
    print("\n-- 2.49.1: what building IGF Module 6 found")
    sys.path.insert(0, HERE)
    import compile_module as cm
    import task_pages as tp

    # C1 - `python -I` leaves the script's own folder off sys.path: task_pages, module_plan, answer_key were not found
    os.makedirs(os.path.join(tmp, "c1"))
    c, md = new_course(os.path.join(tmp, "c1"), script())
    p = subprocess.run([sys.executable, "-I", COMPILE, c, "--module", "1", "--no-drawing-check"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    check("C1: compile_module.py runs under python -I (isolated) - the script's own folder is on sys.path",
          p.returncode == 0 and "ModuleNotFoundError" not in p.stdout + p.stderr and os.path.isfile(os.path.join(md, "tasks", "sc1_the_new_spaces.html")),
          (p.stdout + p.stderr)[-600:])

    # C2 - a crash after the deck is written must not leave the compiler's own file "changed by hand"
    os.makedirs(os.path.join(tmp, "c2"))
    c, md = new_course(os.path.join(tmp, "c2"), script())
    crash = ("import sys; sys.path.insert(0, %r)\nimport compile_module as cm, task_pages as tp\n"
             "def boom(*a, **k): raise RuntimeError('boom')\ntp.compile_tasks = boom\n"
             "cm.main([%r, '--module', '1', '--no-drawing-check'])\n" % (HERE, c))
    p = subprocess.run([sys.executable, "-c", crash], capture_output=True, text=True, encoding="utf-8", errors="replace")
    recs = [os.path.join(r, f) for r, _, fs in os.walk(c) for f in fs if f == "compiled.json"]
    rec = cs.load(recs[0]) if recs else {}
    check("C2: a crash after the deck was written leaves the deck in the build record (written with the file)",
          p.returncode != 0 and "boom" in p.stderr and os.path.isfile(os.path.join(md, "presentation", "index.html"))
          and "index.html" in rec, (p.stderr[-300:], rec))
    code, out = run(COMPILE, c, "--module", "1")
    check("C2: the next run then works - the compiler's own deck is not refused as 'changed by hand' (no --force)",
          code in (0, 1) and "changed by hand" not in out and "tasks/sc1_the_new_spaces.html" in out, out)

    # C3 - the starter build sheet takes the landing rule and the pass mark from the course's other sheets
    sc = json.loads(json.dumps(script()))
    sc["screens"] += [
        {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the valve.", "answer": "Valve*\nPump", "feedback": "x"},
        {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Which?", "options": ["a", "b"], "correct": "A", "feedback": "x"}]
    sc["title"] = "Hazards of operations on IGF ships and the people who run them"
    st = cm.starter_build(sc, [{"landing_rule": "Old rule", "pass_mark": 60}, {"landing_rule": "Basic training · IGF Code", "pass_mark": 70, "foot": "OTHER"}])
    check("C3: the starter build sheet has the course's landing rule and pass mark (the latest sheet that has them)",
          st["landing_rule"] == "Basic training · IGF Code" and st["pass_mark"] == 70, st)
    check("C3: ... a foot from the module's own title (whole words), and an entry for each question answered on a picture",
          st["foot"] == "HAZARDS OF OPERATIONS ON IGF SHIPS AND" and st["screens"]["q02"] == {"figure": "", "areas": {}} and "q03" not in st["screens"], st)
    check("C3: ... nothing invented when no other sheet exists", "pass_mark" not in cm.starter_build(sc) and cm.starter_build(sc)["landing_rule"] == "")
    os.makedirs(os.path.join(tmp, "c3"))
    c, md = new_course(os.path.join(tmp, "c3"), script(), build=False)
    gate_fixture.open_gate(c)
    sdir = os.path.join(c, "working_claude", "script")
    cs.save(os.path.join(sdir, "M02.build.json"), {"module": 2, "landing_rule": "Basic training · IGF Code", "pass_mark": 75, "screens": {}})
    code, out = run(COMPILE, c, "--module", "1", "--init-build")
    sheet = cs.load(os.path.join(sdir, "M01.build.json"))
    check("C3: --init-build reads the sibling build sheets of the course", code == 0 and sheet["landing_rule"] == "Basic training · IGF Code"
          and sheet["pass_mark"] == 75 and sheet["foot"] == "IGF SHIPS", (out, sheet))

    # C5 / C6 - a chart's axis is no thing to photograph; "not_things" takes a name off the list altogether
    chart = ('<div class="fill fig kit-fig"><script type="application/json" id="k">' + json.dumps(
        {"size": [640, 390], "parts": [{"type": "flammability", "id": "F"}, {"type": "text", "text": "Air line"}]}) + "</script></div>")
    check("C5: a figure made only of the kit's chart parts names no real thing - 'Air line' is not listed",
          cm.chart_only(chart) and cm.drawn_parts(["Air line - the line the mixture follows.", "Flammable zone - burns."], chart) == [], cm.drawn_parts(["Air line - x"], chart))
    mixed = chart.replace('"type": "flammability"', '"type": "tank"')
    check("C5: a drawing with a tank among its parts still names its things",
          not cm.chart_only(mixed) and [n for _, n in cm.drawn_parts(["Air line - the line."], mixed)] == ["Air line"])
    notes = []
    cm.part_photos(["Air line - x.", "Relief valve - y."], mixed, set(), md, [], notes, "s03", {}, (), [])
    check("C6: with no help both names are listed", sorted(n[2] for n in notes) == ["Air line", "Relief valve"], notes)
    notes = []
    cm.part_photos(["Air line - x.", "Relief valve - y."], mixed, set(), md, [], notes, "s03", {}, (), ["air line"])
    check("C6: \"not_things\" removes the name from the list altogether (\"no_photo\" keeps it listed)",
          [n[2] for n in notes] == ["Relief valve"], notes)
    notes = []
    cm.part_photos(["Air line - x.", "Relief valve - y."], mixed, set(), md, [], notes, "s03", {}, ["air line"], [])
    check("C6: ... and 'no_photo' still lists it", sorted(n[2] for n in notes) == ["Air line", "Relief valve"], notes)

    # C7 - an inset under a drawing that leaves it a small part of its panel is warned about
    sh = cm.under_share('<script type="application/json" id="k">{"size": [640, 390], "parts": []}</script>')
    sh2 = cm.under_share('<svg viewBox="0 0 640 640"></svg>')
    check("C7: a 640 x 390 drawing keeps ~47 % of its panel under an inset (the M06 measure: 197 of 417 px); a square one keeps more",
          sh and round(sh[0], 2) == 0.47 and round(sh[1]) == 416 and sh2 and sh2[0] > cm.UNDER_MIN_SHARE and cm.under_share("<p>none</p>") is None, (sh, sh2))
    os.makedirs(os.path.join(tmp, "c7"))
    c, md = new_course(os.path.join(tmp, "c7"), script())
    io.open(os.path.join(c, "working_claude", "figures", "M01", "ind.kit.json"), "w", encoding="utf-8").write(json.dumps(
        {"size": [640, 390], "parts": [{"id": "t", "type": "tank", "x": 20, "y": 50, "w": 150, "h": 110, "value": 0.3}]}))
    build_of(c, lambda s: s["screens"].update(s04={"figure": "ind.kit.json", "dark": True, "inset": {"photo": "assets/img/ship.jpg", "under": "figure"}}))
    code, out = run(COMPILE, c, "--module", "1")
    check("C7: \"under\": \"figure\" that leaves the figure under ~60 % of its panel is reported at build",
          code == 1 and "leaves the drawing only about 47 %" in out and "(s04)" in out, out)
    build_of(c, lambda s: s["screens"].update(s04={"figure": "ind.kit.json", "dark": True, "inset": {"photo": "assets/img/ship.jpg"}}))
    code, out = run(COMPILE, c, "--module", "1", "--force")
    check("C7: the same inset under the words is not reported", "leaves the drawing only" not in out, out)

    # C8 / C9 - a photo in a real column; a photo in a figure fragment keeps its visible credit
    os.makedirs(os.path.join(tmp, "c8"))
    c, md = new_course(os.path.join(tmp, "c8"), script())
    io.open(os.path.join(c, "working_claude", "figures", "M01", "cards.html"), "w", encoding="utf-8").write(
        '<div class="fig-cards"><img src="../assets/img/ship.jpg" alt="Truck to ship"></div>')
    build_of(c, lambda s: s["screens"].update(s01={}, s02={"figure": "assets/img/ship.jpg", "composition": "wide-left"}, s03={"figure": "cards.html"}))
    code, out = run(COMPILE, c, "--module", "1")
    d2, d3 = section(deck(md), "s02"), section(deck(md), "s03")
    check("C8: a photograph slide with \"composition\": \"wide-left\" is a real column layout (the words as wide as asked), not 'photo split'",
          'class="slide-body two-col wide-left photo-col dom-fig"' in d2 and "photo split" not in d2 and 'class="slide photo' not in d2, d2[:700])
    check("C8: ... the photo fills its own column and keeps its visible credit line",
          '<div class="fill fig photo-col"><img src="../assets/img/ship.jpg"' in d2 and '<div class="credit">Photo: Jane Doe' in d2, d2)
    check("C9: a photograph inside a figure fragment keeps the slide credit line", '<div class="credit">Photo: Jane Doe' in d3 and "data-credit=" in d3, d3)
    css = io.open(os.path.join(md, "assets", "gb_compose.css"), encoding="utf-8").read()
    check("C8: the column layout is styled - the photo is cropped to its column, which has the slide's height",
          ".slide-body.two-col.photo-col{grid-template-rows:minmax(0,1fr)" in css and "object-fit:cover" in css.split(".photo-col > .fill.photo-col > img")[1][:200], css[:100])
    code, out = run(COMPILE, c, "--module", "1", "--force")
    build_of(c, lambda s: s["screens"].update(s02={"figure": "assets/img/ship.jpg", "composition": "two-col"}, s03={}))
    run(COMPILE, c, "--module", "1", "--force")
    check("C8: \"two-col\" with a photograph is still the photo-on-the-right slide (words on the scrim)", 'class="slide photo split"' in section(deck(md), "s02"))

    # C4 / C12 / C13 - the task pages
    spec = {"size": [400, 200], "parts": [
        {"id": "tk", "type": "tank", "x": 20, "y": 50, "w": 150, "h": 110, "label": "Fuel tank", "value": 0.2},
        {"id": "mv", "type": "valve", "x": 210, "y": 100, "size": 16, "label": "Master valve", "value": 1},
        {"id": "pp", "type": "pump", "x": 300, "y": 100, "r": 26, "label": "Pump", "value": 0},
        {"id": "sv", "type": "valve", "x": 350, "y": 40, "size": 16, "label": "Spare valve", "value": 0},
        {"id": "T_mv", "type": "text", "x": 190, "y": 150, "text": "the master valve"},
        {"type": "text", "to": [214, 104], "x": 190, "y": 180, "text": "points at the valve"},
        {"type": "text", "to": [300, 100], "x": 280, "y": 180, "text": "points at the pump"},
        {"type": "text", "x": 200, "y": 20, "text": "Fuel plant", "style": "h"}], "steps": [{"title": "1 · Fill", "set": {"tk": 0.8}}]}
    screens = [
        {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the plant", "text": "Self-check on your tablet now.", "minutes": 4},
        {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the master valve.", "visual": "the plant",
         "answer": "Master valve*\nFuel tank\nPump", "feedback": "Between tank and pump."},
        {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "categorise", "question": "Sort each precaution under its hazard.",
         "answer": "Surge: close valves slowly\nCold burns: wear a face shield", "feedback": "x"},
        {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "What is this?",
         "options": ["A pump", "A boiler"], "correct": "A", "feedback": "A pump."},
        {"id": "q04", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the steps in order.",
         "answer": "Open the valve\nStart the pump", "feedback": "x"}]
    os.makedirs(os.path.join(tmp, "c4"))
    c, md = new_course(os.path.join(tmp, "c4"), script(screens=screens), build=False)
    img = os.path.join(md, "assets", "img")
    io.open(os.path.join(img, "pump.png"), "wb").write(png(600, 400))
    cs.save(os.path.join(img, "_photo_meta.json"), {"pump.png": {"source": "Own photograph, Novikontas", "licence": "own work",
            "attribution_required": False, "description": "A grey pump on a blue base. It has a red relief valve.", "shows": "pump"}})
    io.open(os.path.join(c, "working_claude", "figures", "M01", "plant.kit.json"), "w", encoding="utf-8").write(json.dumps(spec))
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "t01": {"try_tablet": False},
        "q01": {"figure": "plant.kit.json", "unlabel": "answers", "areas": {"Master valve": "mv", "Fuel tank": "tk", "Pump": "pp"}},
        "q02": {"figure": "assets/img/pump.png"},
        "q03": {"figure": "assets/img/pump.png"},
        "q04": {"figure": "assets/img/pump.png"}}})
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks")
    page = io.open(os.path.join(md, "tasks", "sc1_the_plant.html"), encoding="utf-8").read()
    q = {k: page.split('data-script="%s"' % k)[1].split("</section>")[0] for k in ("q01", "q02", "q03", "q04")}
    ks = re.search(r'id="kit-task-[^"]+">(.*?)</script>', q["q01"], re.S)
    kspec = json.loads(ks.group(1)) if ks else {}
    got, ghost = kspec.get("parts") or [], kspec.get("ghost") or []
    shown = json.dumps([p for p in got if p.get("id") not in ghost])
    # 2.50.4: the answers' words stay in the spec and the kit hides them after laying them out ("ghost") - so the words
    # left stand where the deck has them (taking them out re-laid the rest: M01 benchmark run 4, q01 / q03)
    check("C4: \"unlabel\": \"answers\" takes the words off only the parts the answers name (laid out, then hidden: \"ghost\")",
          code == 0 and {"tk", "mv", "pp"} <= set(ghost) and "sv" not in ghost and "Fuel tank" not in shown
          and "Master valve" not in shown and "\"Pump\"" not in shown and "Spare valve" in shown and len(got) == 8, (out, kspec))
    check("C4: ... and the callouts of those parts (pointing at them, or T_<id>), but not a free caption or another part's callout",
          "the master valve" not in shown and "points at the valve" not in shown and "points at the pump" not in shown
          and "Fuel plant" in shown and len(ghost) == 6, kspec)
    broken_sheet = {"module": 1, "screens": {"t01": {"try_tablet": False}, "q01": {"figure": "plant.kit.json", "unlabel": "everything",
                    "areas": {"Master valve": "mv"}}}}
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), broken_sheet)
    code, out = run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    check("C4: an unknown \"unlabel\" is reported and names the three choices", code == 1 and '"answers", "all" or a list' in out, out)
    check("C12: a photo over a categorise / an order lays itself beside the cards on landscape (data-pic=beside), like a choice",
          all('data-pic="beside"' in q[k] and "instrument" in q[k] for k in ("q02", "q04", "q03")) and 'data-mech="categorise" data-pic="beside"' in q["q02"], q["q02"][:300])
    gcss = io.open(os.path.join(SKILLS, "course-task-ux", "assets", "gb_answer.css"), encoding="utf-8").read()
    check("F20 (2.49.2): a photograph beside a question carries its credit as a line on the picture and the round open-full-screen button",
          all('data-zoom="button"' in q[k] and '<p class="figcredit">Photo: ' in q[k] for k in ("q03", "q04")), q["q03"][:700])
    check("C12: the engine's stylesheet places the picture and the cards of a sort / put-in-order beside each other",
          '.scr[data-pic="beside"][data-mech="categorise"]>.grps{grid-column:1/-1}' in gcss and '[data-mech="order"],[data-mech="match"]' in gcss, "")
    check("C13: a task photograph's alt comes from the question's visual, else the photo's own record",
          '<img class="taskfig" src="../assets/img/pump.png" alt="A grey pump on a blue base."' in q["q02"] and tp.photo_alt({"name": "A pump"}) == "A pump"
          and tp.photo_alt({"shows": ["a pump", "a base"]}) == "a pump, a base" and tp.photo_alt({}) == "", q["q02"][:500])
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False},
            "q02": {"figure": "assets/img/pump.png", "alt": "The pump room, seen from the door"}, "q03": {"figure": "assets/img/pump.png"}, "q04": {}}})
    run(COMPILE, c, "--module", "1", "--only", "tasks", "--force")
    page = io.open(os.path.join(md, "tasks", "sc1_the_plant.html"), encoding="utf-8").read()
    check("C13: the build sheet's own alt wins", 'alt="The pump room, seen from the door"' in page, "")
    # C15 / C16 - the stylesheet
    check("C15: .dial-val (the set-value readout the engine writes) has a rule", re.search(r"\.dial-read \.dial-val\{", gcss) is not None)
    check("C16: on a dark drawing (and a photo) a right / wrong area is a plain wash, not multiply (near-black) - with a larger tick",
          ".ga.kitfig .hot.right,.ga:has(>img.taskfig) .hot.right{border-color:var(--good-d)" in gcss
          and "mix-blend-mode:normal}" in gcss and "width:34px;height:34px" in gcss)


def final_script(variants=("FA", "FB")):
    """a final assessment's script: a slide, one task slide per variant, two graded questions per variant"""
    screens = [{"id": "s01", "kind": "slide", "title": "The final assessment", "layout": "split", "visual_kind": "comparison",
                "text": "Two variants, 60 minutes.\nYou need 70 %.", "visual": "A table.", "notes": "- Hand out one variant.", "minutes": 5}]
    for i, v in enumerate(variants, 1):
        screens.append({"id": "t%02d" % i, "kind": "task-slide", "opens": v, "title": "Final assessment %s - the whole course" % v[1],
                        "text": "Final assessment on your tablet.", "notes": "- Press OPEN TASK.", "minutes": 10})
    for v in variants:
        for k in (1, 2):
            screens.append({"id": "%s%02d" % (v.lower(), k), "kind": "final", "set": v, "question": "Which space surrounds the tank valves? (%s%d)" % (v, k),
                            "options": ["Tank connection space", "Galley"], "correct": "A", "feedback": "It holds every tank connection.",
                            "mechanic": "single_choice"})
    s = script(approved=False, screens=screens)
    s.update(module="final", title="Final assessment")
    s.update(status="approved", approved_hash=cs.content_hash(s), approved_by="Test")
    return s


def final_course(tmp, name, sc, architecture=True):
    c = os.path.join(tmp, name, "course")
    os.makedirs(os.path.join(c, "working_claude", "script"))
    cs.save(os.path.join(c, "working_claude", "script", "FINAL.json"), sc)
    if architecture:
        cs.save(os.path.join(c, "working_claude", "architecture.json"), {
            "course": {"title": "IGF", "course_language": "English"},
            "modules": [{"module": 1, "title": "One"}, {"module": 2, "title": "Two"}], "final_assessment": {"topic": "3"}})
    return c


def v2492_part(tmp):
    """2.49.2 - what building IGF Modules 7-15 and the final found in the compiler (F1 F2 F4 F5 F6 F7 F12 F25)"""
    print("\n-- 2.49.2: the compiler fixes found on IGF M07-M15 and the final")
    sys.path.insert(0, os.path.join(SKILLS, "course-module-ui", "scripts"))
    sys.path.insert(0, HERE)
    import design_system
    import task_pages as tp
    # F1 - a design file that only fell behind is put right, and the build says so
    os.makedirs(os.path.join(tmp, "v1"))
    c, md = new_course(os.path.join(tmp, "v1"), script())
    kit = os.path.join(md, "assets", "kit.js")
    io.open(kit, "w", encoding="utf-8").write("/* an older kit */")
    spec = design_system.load_list()
    rp = design_system.record_path(md, spec)
    rec = json.load(io.open(rp, encoding="utf-8"))
    rec["files"]["kit.js"] = design_system.sha(kit)                     # what was installed once - the factory has moved on since
    json.dump(rec, io.open(rp, "w", encoding="utf-8"))
    code, out = run(COMPILE, c, "--module", "1")
    canon = os.path.join(SKILLS, "course-visuals", "kit", "kit.js")
    check("F1: a kit.js that only fell behind is updated before the build - and the build says which file, and that it did",
          code == 0 and "updated from the factory" in out and "kit.js (older version)" in out
          and io.open(kit, "rb").read() == io.open(canon, "rb").read(), out)
    code, out = run(COMPILE, c, "--module", "1")
    check("F1: a second build says the design files are the factory's own, and changes nothing",
          code == 0 and "all" in out.split("\n")[0] and "are the factory's own" in out.split("\n")[0], out)
    # F2 - the module folder exists (assets\img made first) but holds no design files
    os.makedirs(os.path.join(tmp, "v2"))
    c2, md2 = new_course(os.path.join(tmp, "v2"), script(), build=False)
    gate_fixture.open_gate(c2)
    for f in os.listdir(os.path.join(md2, "assets")):
        if os.path.isfile(os.path.join(md2, "assets", f)):
            os.remove(os.path.join(md2, "assets", f))
    code, out = run(COMPILE, c2, "--module", "1", "--init-build")
    check("F2: --init-build in a module folder that exists but has no design files says so plainly and installs them",
          code == 0 and "Design files were missing" in out and os.path.isfile(os.path.join(md2, "assets", "kit.js"))
          and os.path.isfile(os.path.join(md2, "assets", "gb_answer.js")), out)
    for f in ("gb_deck.js", "kit.js"):
        os.remove(os.path.join(md2, "assets", f))
    code, out = run(COMPILE, c2, "--module", "1")
    check("F2: a compile with design files missing installs them (and says: missing) instead of building without them",
          "kit.js (missing)" in out and "gb_deck.js (missing)" in out and os.path.isfile(os.path.join(md2, "assets", "gb_deck.js")), out)
    # F5 / F6 - the final: the folder after the last planned module, and each variant a graded assessment page
    os.makedirs(os.path.join(tmp, "v5"))
    cf = final_course(os.path.join(tmp, "v5"), "f", final_script())
    code, out = run(COMPILE, cf, "--module", "final")
    mf = os.path.join(cf, "modules", "module03")
    check("F5: --module final builds into the folder after the last planned module (module03), no --module-dir needed",
          os.path.isfile(os.path.join(mf, "presentation", "index.html")), out)
    check("F6: a final with variants - FA and FB each a graded assessment page with its own answer key row; no task page for a variant",
          os.path.isfile(os.path.join(mf, "assessment", "final_a.html")) and os.path.isfile(os.path.join(mf, "assessment", "final_b.html"))
          and not os.path.isfile(os.path.join(mf, "assessment", "final.html")) and not os.path.isdir(os.path.join(mf, "tasks")), out)
    dk = deck(mf)
    check("F6: the deck's slides open them as Check slides (data-kind Check), and the landing card names the variants",
          'data-task-href="../assessment/final_a.html"' in dk and 'data-task-href="../assessment/final_b.html"' in dk
          and dk.count('data-kind="Check"') == 2 and "Final assessment A" in dk and "Final assessment B" in dk, dk[:300])
    fb = io.open(os.path.join(mf, "assessment", "final_b.html"), encoding="utf-8").read()
    check("F6: variant B is graded like the check - a pass mark, its own title FB",
          'data-pass="70"' in fb and "<title>FB — " in fb and "(FB2)" in fb and "(FA1)" not in fb, fb[:600])
    fa = io.open(os.path.join(mf, "assessment", "final_a.html"), encoding="utf-8").read()
    check("2.60.0: both final variants are blind (data-blind on the body) - the engine shows no answer until the score",
          re.search(r'<body [^>]*data-blind="1"', fa) is not None and re.search(r'<body [^>]*data-blind="1"', fb) is not None,
          re.search(r"<body[^>]*>", fb).group(0) if re.search(r"<body[^>]*>", fb) else fb[:300])
    key = io.open(os.path.join(mf, "assessment", "check_answer_key.html"), encoding="utf-8").read()
    check("F6: the instructor's key lists both variants and names their pages",
          "final_a.html" in key and "final_b.html" in key and "Final assessment A" in key and "Final assessment B" in key, key[:600])
    os.makedirs(os.path.join(tmp, "v6"))
    c1 = final_course(os.path.join(tmp, "v6"), "f", final_script(("FA",)))
    code, out = run(COMPILE, c1, "--module", "final")
    check("F6: a final with ONE variant keeps assessment/final.html, as before",
          os.path.isfile(os.path.join(c1, "modules", "module03", "assessment", "final.html"))
          and not os.path.isfile(os.path.join(c1, "modules", "module03", "assessment", "final_a.html")), out)
    os.makedirs(os.path.join(tmp, "v7"))
    cn = final_course(os.path.join(tmp, "v7"), "f", final_script(), architecture=False)
    code, out = run(COMPILE, cn, "--module", "final")
    check("F5: with no architecture to count the modules, --module final stops and says to give --module-dir (no crash)",
          code == 2 and "--module-dir" in out and "Traceback" not in out, out)
    # F7 - a draft is marked; the mark goes when the approved script is built
    os.makedirs(os.path.join(tmp, "v8"))
    c3, md3 = new_course(os.path.join(tmp, "v8"), script(approved=False))
    code, out = run(COMPILE, c3, "--module", "1", "--draft")
    mark = os.path.join(md3, "DRAFT_NOT_PACKAGED.txt")
    check("F7: --draft marks the module folder as a draft (DRAFT_NOT_PACKAGED.txt) and says it is left out of the package",
          os.path.isfile(mark) and "marked as a draft" in out, out)
    cs.save(os.path.join(c3, "working_claude", "script", "M01.json"), script())
    code, out = run(COMPILE, c3, "--module", "1", "--force")
    check("F7: building the approved script takes the mark away", code == 0 and not os.path.isfile(mark) and "draft mark" in out, out)
    # F4 - words too long for an inset photograph under them are said at build
    os.makedirs(os.path.join(tmp, "v9"))
    longer = json.loads(json.dumps(SCREENS))
    longer[1]["text"] = "\n".join("The Code sets rule %d for gas fuelled ships and every one of them needs a long careful line of words." % i
                                  for i in range(1, 7))
    c4, md4 = new_course(os.path.join(tmp, "v9"), script(screens=longer))
    bp4 = os.path.join(c4, "working_claude", "script", "M01.build.json")
    sh4 = cs.load(bp4)
    sh4["screens"]["s02"]["inset"] = {"photo": "assets/img/ship.jpg", "caption": "On board."}
    cs.save(bp4, sh4)
    code, out = run(COMPILE, c4, "--module", "1")
    check("F4: %d words with an inset photograph under them in a column are reported at build, with the px it will spill"
          % len(" ".join(longer[1]["text"].split("\n")).split()),
          code == 1 and "photograph will spill about" in out and "s02" in out, out)
    sh4["screens"]["s02"].pop("inset")
    cs.save(bp4, sh4)
    code, out = run(COMPILE, c4, "--module", "1", "--force")
    check("F4: the same words with no inset are not reported", "will spill" not in out, out)
    # F25 - a push button on the operate-the-panel card
    sym = tp.kit_symbol("m01", 1, ["ready", "pressed"], "ready", "ESD push button")
    spec_ = json.loads(re.search(r'application/json" id="[^"]+">(.*?)</script>', sym).group(1))
    check("F25: a control with ready / pressed is drawn with the kit's push_button, tagged ESD, in a taller card symbol",
          'class="csym tall"' in sym and spec_["parts"][0]["type"] == "push_button" and spec_["parts"][0]["tag"] == "ESD"
          and spec_["parts"][0]["value"] == 0 and tp.kit_symbol("m01", 1, ["ready", "open"], "", "x") == ""
          and "pump" in tp.kit_symbol("m01", 2, ["running", "stopped"], "", "Pump"), sym[:300])
    gc = io.open(os.path.join(SKILLS, "course-module-ui", "templates", "gb_compose.css"), encoding="utf-8").read()
    check("F12: a 3D stage takes its column's height (no fixed 100vh - 300px that overran the column by 28 px)",
          "[data-stage]{height:max(320px,calc(100vh - 300px))" not in gc and "fig-wide > .fill:has([data-stage])" in gc and "[data-stage]{width:100%;flex:1 1 0" in gc, "")


def v2494_part(tmp):
    """2.49.4 - what the pre-merge review of the branch found in the compiler"""
    print("\n-- 2.49.4: the pre-merge review's compiler fixes")
    sys.path.insert(0, HERE)
    import compile_module as cm
    fig = '<div class="fill"><svg viewBox="0 0 10 10"></svg></div>'
    extra = '<div class="inset-cap">Photo taken from C:\\Users\\crew\\deck.jpg</div>'
    try:
        got = cm.under_figure(fig, extra)
    except Exception as ex:                       # re.error: bad escape \U - before 2.49.4
        got = "%s: %s" % (type(ex).__name__, ex)
    check("an inset caption with a backslash (C:\\Users\\...) is put under the drawing as it is written, no crash",
          extra in got and got.endswith("</div>") and got.count("</div>") == 2, got)
    check("a slide with no words gives no word lines (no IndexError)", cm.words_html([]) == [] and cm.words_html([], legend=True) == [])
    os.makedirs(os.path.join(tmp, "w1"))
    bare = json.loads(json.dumps(SCREENS))
    bare[1]["text"] = ""                          # a split slide: title and figure only
    bare[2]["text"] = ""                          # a wide slide: title and figure only
    c, md = new_course(os.path.join(tmp, "w1"), script(screens=bare))
    code, out = run(COMPILE, c, "--module", "1")
    check("a title-and-figure slide with no words compiles", code in (0, 1) and "Traceback" not in out
          and os.path.isfile(os.path.join(md, "presentation", "index.html")), out)
    # the draft mark stays until the deck itself is rebuilt from the approved script
    os.makedirs(os.path.join(tmp, "w2"))
    c2, md2 = new_course(os.path.join(tmp, "w2"), script(approved=False))
    run(COMPILE, c2, "--module", "1", "--draft")
    mark = os.path.join(md2, "DRAFT_NOT_PACKAGED.txt")
    cs.save(os.path.join(c2, "working_claude", "script", "M01.json"), script())
    code, out = run(COMPILE, c2, "--module", "1", "--only", "tasks", "--force")
    check("--only tasks after approval keeps the draft mark - the deck on disk is still the draft's - and says why",
          os.path.isfile(mark) and "mark (DRAFT_NOT_PACKAGED.txt) stays" in out and "--only deck" in out, out)
    code, out = run(COMPILE, c2, "--module", "1", "--only", "deck", "--force")
    check("--only deck after approval takes the mark away", not os.path.isfile(mark) and "draft mark" in out, out)
    # PHOTOS_TO_TAKE.md in a course that has no working_claude folder yet
    bare_course = os.path.join(tmp, "w3")
    os.makedirs(bare_course)
    try:
        p = cm.write_to_take(bare_course, {"module": 1, "title": "Gas as fuel"}, [])
        ok = os.path.isfile(p) and "## M01" in io.open(p, encoding="utf-8").read()
    except Exception as ex:
        ok, p = False, "%s: %s" % (type(ex).__name__, ex)
    check("PHOTOS_TO_TAKE.md is written where the course keeps its factory files, the folder made when missing", ok, p)


def v2497_part(tmp):
    """2.49.7 (IGF M01 benchmark) - a slide the script plans as 3D, built with a 2D figure, is said - in the build and on the
    review page - until the operator keeps the 2D figure with a reason"""
    print("\n-- 2.49.7: a 3D slide is never quietly built in 2D")
    sp = lambda c: os.path.join(c, "working_claude", "script", "M01.build.json")

    def built(name, s04, files=()):
        os.makedirs(os.path.join(tmp, name))
        c, md = new_course(os.path.join(tmp, name), script())
        sheet = cs.load(sp(c))
        sheet["screens"]["s04"] = s04
        cs.save(sp(c), sheet)
        for fn, text in files:
            io.open(os.path.join(c, "working_claude", "figures", "M01", fn), "w", encoding="utf-8").write(text)
        code, out = run(COMPILE, c, "--module", "1", "--only", "deck", "--no-drawing-check")
        return c, code, out

    c, code, out = built("f1", {"figure": "hull.svg", "dark": True})
    check("s04 (model_3d) given a 2D drawing: the build says it - \"asks for a 3D scene; it has a 2D figure\" - exit 1",
          code == 1 and "(s04) asks for a 3D scene (model_3d); it has a 2D figure (hull.svg)" in out and "declined_3d" in out, out)
    found = cs.build_findings(c, script())
    check("... and the script's review page shows it beside the picture findings, as a note",
          [f["screen"] for f in found] == ["s04"] and found[0]["level"] != "fail" and "hull.svg" in found[0]["detail"]
          and found[0]["detail"] in html.unescape(cs.render_html(c, script())), found)
    _c, code, out = built("f2", {"figure": "hull.kit.json", "dark": True},
                          [("hull.kit.json", json.dumps({"size": [400, 200], "parts": [{"id": "T", "type": "tank", "x": 40, "y": 40, "w": 200, "h": 100}]}))])
    check("a kit figure is a 2D figure too (IGF M01 s05)", code == 1 and "it has a 2D figure (hull.kit.json)" in out, out)
    _c, code, out = built("f3", {"figure": "ga.html", "dark": True})
    check("an .html figure holding a scene ([data-stage]) is the 3D scene - nothing said", "asks for a 3D scene" not in out, out)
    c4, code, out = built("f4", {"figure": "hull.svg", "dark": True, "declined_3d": "the operator: a flat section reads better here"})
    check("the 2D figure kept with the operator's reason (\"declined_3d\") is not flagged again - build and review page",
          code == 0 and "asks for a 3D scene" not in out and not cs.build_findings(c4, script()), out)
    _c, code, out = built("f5", {"figure": "hull.svg", "dark": True, "declined_3d": " "})
    check("... a \"declined_3d\" with no reason keeps it said", code == 1 and "asks for a 3D scene" in out, out)

    # L60 (Aleksis, 2026-10-19: "very recommended to build a 3D model at least once where you can in a module")
    flat = json.loads(json.dumps(SCREENS))
    flat[3].update(visual_kind="interactive_diagram", visual="A hull section: the double-walled gas pipe and the engine room.")
    flat[2].update(notes="- Name each space.")     # 2.52.0: "Tap each space" on a flat drawing is a cue to fix - not this test's point
    os.makedirs(os.path.join(tmp, "l60"))
    c6, md6 = new_course(os.path.join(tmp, "l60"), script(screens=flat), build=False)
    gate_fixture.open_gate(c6)
    code, out = run(COMPILE, c6, "--module", "1", "--init-build")
    sheet = cs.load(sp(c6))
    s3 = sheet["screens"].get("s03", {})
    check("L60: a module with no 3D slide in its script - --init-build gives the best slide (the spaces and their arrangement) "
          "a starter scene, unasked, and says why and how to decline",
          code == 0 and s3.get("figure") == "m01_s03_3d.html" and "assets/js/m01_s03_3d.js" in sheet["scripts"]
          and "L60" in s3.get("_3d", "") and "arrangement" in s3.get("_3d", "") and "declined_3d" in s3.get("_3d", ""), sheet)
    check("... never on a slide whose picture is a real photograph (L52)", "_3d" not in sheet["screens"].get("s01", {}), sheet)
    sheet["screens"]["s04"] = {"figure": "hull.svg", "dark": True}
    sheet["scripts"] = []
    for sid in ("s01", "s02", "s03"):
        sheet["screens"][sid] = {"figure": {"s01": "assets/img/ship.jpg", "s02": "assets/fig/scale.svg", "s03": "hull.svg"}[sid]}
    cs.save(sp(c6), sheet)
    code, out = run(COMPILE, c6, "--module", "1", "--only", "deck", "--no-drawing-check")
    check("L60: built with no 3D scene - the build says it loud, names the best candidate and why, and does not block on it",
          "RECOMMENDED (L60) - no 3D scene in this module; the best candidate is s03 \"Five new spaces\", because spaces, arrangement" in out
          and "To fix before it is shown" not in out and code == 0, out)
    page = html.unescape(cs.render_html(c6, script(screens=flat)))
    check("... and the review page shows it in its own card", "No 3D scene in this module yet" in page
          and page.find("No 3D scene in this module yet") < page.find("the best candidate is s03"), page[:300])
    sheet["declined_3d"] = "the operator: this module is about rules, a drawing is enough"
    cs.save(sp(c6), sheet)
    code, out = run(COMPILE, c6, "--module", "1", "--only", "deck", "--no-drawing-check")
    check("L60: declined with the operator's reason - not proposed again, in the build or on the review page",
          "RECOMMENDED (L60)" not in out and not cs.build_findings(c6, script(screens=flat)), out)

    # IGF M01 q01/q03: two questions on one kit figure, "unlabel": "answers", other answers - two drawings, not one shared
    sys.path.insert(0, HERE)
    import task_pages
    text = json.dumps(PLANT_KIT)
    f1 = task_pages.kit_fig({}, {"unlabel": "answers", "areas": {"Fuel tank": "tk"}}, text, "plant.kit.json", [], "q01", False)
    f2 = task_pages.kit_fig({}, {"unlabel": "answers", "areas": {"Pump": "pp"}}, text, "plant.kit.json", [], "q03", False)
    f3 = task_pages.kit_fig({}, {"unlabel": "answers", "areas": {"Pump": "pp"}}, text, "plant.kit.json", [], "q04", False)
    check("\"unlabel\": \"answers\" on one kit figure with other answers gives each question its own drawing - q03 never shows "
          "q01's, with its own answer still written on it; the same answers still share one",
          f1.name != f2.name and f2.name == f3.name and '"ghost":["tk"]' in f1.html(True) and '"ghost":["pp"]' in f2.html(True),
          (f1.name, f2.name, f3.name))



STEP_KIT = {"size": [400, 200], "parts": [{"id": "T", "type": "tank", "x": 40, "y": 40, "w": 200, "h": 100, "label": "Fuel tank"}],
            "steps": [{"title": "The tank", "show": ["T"], "line": 1}]}


def three_part(tmp):
    """2.59.0 - the 3D engine ships with the factory: a sheet naming assets/vendor/three.min.js gets the factory's copy (IGF
    M03 declined its 3D scene overnight because no copy was to be found)"""
    print("\n-- 2.59.0: three.js comes with the factory")
    c, md = new_course(os.path.join(tmp, "three59"), script())
    build_of(c, lambda s: s.update(scripts=["assets/vendor/three.min.js"]))
    code, out = run(COMPILE, c, "--module", "1", "--only", "deck")
    mine = os.path.join(md, "assets", "vendor", "three.min.js")
    src = os.path.join(SKILLS, "course-module-ui", "templates", "vendor", "three.min.js")
    check("a build sheet naming three.min.js gets the factory's r128 copy, byte for byte, and no 'not in the module folder'",
          os.path.isfile(mine) and open(mine, "rb").read() == open(src, "rb").read() and 'const e="128"' in open(src, encoding="utf-8").read()
          and "three.min.js, which is not in the module folder" not in out, out[-600:])
    # 2.60.0 - the scene's control hint failed check_script_match on IGF M05 s06, M13 s07, M15 s05
    print("\n-- 2.60.0: a 3D scene's control hint is not script words")
    c, md = new_course(os.path.join(tmp, "hint60"), script())
    io.open(os.path.join(c, "working_claude", "figures", "M01", "m01_s04_3d.html"), "w", encoding="utf-8").write(
        '<div class="fill fig" data-stage data-3d><canvas></canvas><div data-hint>Drag to turn - tap a part to look closer</div>'
        '<p data-hint data-script-ignore>Tap it again</p></div>')
    build_of(c, lambda s: s["screens"].update(s04={"figure": "m01_s04_3d.html", "dark": True}))
    code, out = run(COMPILE, c, "--module", "1")
    s04 = section(deck(md), "s04")
    check("the hint's holder [data-hint] goes into the deck marked data-script-ignore - once, also where it already was",
          '<div data-script-ignore data-hint>Drag to turn' in s04 and '<p data-hint data-script-ignore>Tap it again' in s04
          and s04.count("data-script-ignore") == 2, s04[:800])
    code, mout = run(MATCH, c, "--module", "1", "--part", "instructor")
    check("... so check_script_match passes the slide: the approved words and a counted hint", code == 0 and "Drag to turn" not in mout, mout)
    sys.path.insert(0, HERE)
    import compile_module as cm
    note = cm.starter_scene({"module": 1}, "s05", [])["_figure"]
    check("the starter 3D entry says where the hint goes and that a class of the module's own needs a rule",
          "<div data-hint></div>" in note and "data-script-ignore" in note and "no rule styles" in note, note)


def v2520_part(tmp):
    """2.52.0 (IGF M01 + M02 benchmark, 2026-10-20) - six things a trainee or an instructor saw"""
    print("\n-- 2.52.0: what the deck says is what was built; only what is shown ships")
    sys.path.insert(0, HERE)
    sp = lambda c: os.path.join(c, "working_claude", "script", "M01.build.json")
    os.makedirs(os.path.join(tmp, "v52"))
    sc = json.loads(json.dumps(SCREENS))
    sc[1]["active"] = "predict-then-reveal"                 # s02, 4 min, active
    sc[2]["notes"] = "- Tap each space.\n- Before you tap, ask."
    sc[3]["notes"] = "- ESD in module 14.\n- Rotate the model and cut the pipe open."
    c, md = new_course(os.path.join(tmp, "v52"), script(screens=sc))
    code, out = run(COMPILE, c, "--module", "1", "--only", "deck")
    page = deck(md)
    s01, s02, s03, s04 = (section(page, x) for x in ("s01", "s02", "s03", "s04"))

    # 1 - 3D wording after the 3D was declined
    check("1: a 3D slide kept as a 2D drawing (\"declined_3d\") says the kind it was built with - data-visual is no model_3d",
          'data-visual="schematic"' in s04 and "model_3d" not in s04, s04[:400])
    check("1: ... a slide whose figure holds a scene keeps its planned kind", 'data-visual="interactive_diagram"' in s03, s03[:300])
    check("1: a cue that asks the built picture for what it cannot do is in \"To fix\" - the approved words unchanged in the deck",
          code == 1 and "To fix before it is shown" in out and "(s04): the instructor's cue says \"Rotate the model and cut the pipe open.\""
          in out and "not a 3D scene" in out and 'data-cue="- ESD in module 14.\n- Rotate the model and cut the pipe open."' in s04, out)
    check("1: ... a cue the picture can do (tap the parts of a 3D scene) is not reported", "(s03): the instructor" not in out, out)
    fixes_p = os.path.join(c, "working_claude", "script", "M01.cue_fixes.json")
    fixes = cs.load(fixes_p) if os.path.isfile(fixes_p) else None
    check("1: ... with a drafted line in its place, written as a changes file beside the script, and the exact propose command",
          "Drafted in its place: \"Point to each part on the drawing in turn.\"" in out and "propose" in out and "M01.cue_fixes.json" in out
          and fixes == [{"field": "s04.notes", "new": "- ESD in module 14.\n- Point to each part on the drawing in turn."}], (out, fixes))
    code_pr, out_pr = run(os.path.join(SKILL, "scripts", "content_script.py"), "propose", c, "--module", "1", "--changes", fixes_p)
    check("1: ... content_script.py propose takes the file as it is (pending - the script itself is unchanged)",
          code_pr == 0 and cs.load(os.path.join(c, "working_claude", "script", "M01.json"))["screens"][3]["notes"] == sc[3]["notes"], out_pr)
    sheet = cs.load(sp(c))
    sheet["screens"]["s04"]["cue_kept"] = "the operator: the instructor turns the printed model in the room"
    cs.save(sp(c), sheet)
    code_k, out_k = run(COMPILE, c, "--module", "1", "--only", "deck")
    check("1: ... kept with the operator's reason (\"cue_kept\") it is not reported again - and no drafted file is left", code_k == 0
          and "the instructor's cue says" not in out_k and not os.path.isfile(fixes_p), out_k)
    import compile_module as cm
    kit = '<div class="fill fig kit-fig"><script type="application/json" id="kit-s09">%s</script></div>' % json.dumps(STEP_KIT)
    s9 = {"id": "s09", "notes": "- Tap each part in order, tank to engine.\n- Tap the next step when the room answers."}
    found = cm.cue_problems(s9, kit, "interactive_diagram", False, {}, md, "s09")
    check("1: on a kit drawing \"tap each part\" is reported (its parts do not answer a tap), \"tap\" alone is not (its step "
          "buttons and lit lines do)", len(found) == 1 and "Tap each part in order" in found[0] and "tap on its parts" in found[0], found)
    sheet = cs.load(sp(c))
    sheet["screens"]["s04"]["figure"] = "s04.kit.json"
    cs.save(sp(c), sheet)
    io.open(os.path.join(c, "working_claude", "figures", "M01", "s04.kit.json"), "w", encoding="utf-8").write(json.dumps(STEP_KIT))
    code_p, out_p = run(COMPILE, c, "--module", "1", "--only", "plan")
    plan = io.open(os.path.join(md, "instructor", "M01_PLAN.html"), encoding="utf-8").read()
    row = re.search(r"<tr><td class=\"n\">4</td>.*?</tr>", plan, re.S)
    check("1: the instructor's plan labels the slide by the picture built (a step animation), not the script's 3D model",
          row and "Step-by-step animation" in row.group(0) and "3D model" not in row.group(0), row.group(0) if row else plan[-600:])

    # 4 - data-active
    check("4: every block carries data-active - a plain theory slide 0, an active slide its minutes, a task slide its minutes",
          'data-mins="3" data-active="0"' in s01 and 'data-mins="4" data-active="4"' in s02
          and 'data-mins="4" data-active="4"' in section(page, "t01"), (s01[:300], s02[:300]))
    bal = os.path.join(SKILL, "hours", "scripts", "check_balance.py")
    code_b, out_b = run(bal, os.path.join(md, "presentation", "index.html"))
    check("4: check_balance.py reads every compiled block (no 'data-active missing')", "data-active missing" not in out_b
          and "learner-active" in out_b, out_b)

    # 5 - the figure first in the markup, the projector layout kept by CSS
    check("5: a two-col slide writes its figure before its words, marked dom-fig", re.search(
        r'<div class="slide-body two-col wide-right dom-fig">\s*<div class="fill fig">.*?<div class="copy">', s04, re.S), s04)
    css = io.open(os.path.join(SKILLS, "course-module-ui", "templates", "gb_compose.css"), encoding="utf-8").read()
    check("5: ... and gb_compose.css puts the words back first on a landscape screen only",
          "@media (min-width:901px){.slide-body.dom-fig > .copy{order:-1}}" in css)
    flow = cm.slide_html(script(), {"id": "s07", "kind": "slide", "title": "T", "text": "One.\nTwo.", "minutes": 2},
                         1, 1, {"figure": "assets/fig/scale.svg", "composition": "flow"}, md, None, "F", [])
    check("5: a flow slide with a figure: figure first, dom-fig", re.search(r'<div class="slide-body dom-fig">\s*<div class="fill fig">'
                                                                         r'.*?<div class="copy">', flow, re.S), flow)
    ff = cm.slide_html(script(), {"id": "s07", "kind": "slide", "title": "T", "text": "One.\nTwo.", "minutes": 2, "layout": "split"},
                       1, 1, {"figure": "assets/fig/scale.svg", "figure_first": True}, md, None, "F", [])
    check("5: \"figure_first\" (the drawing on the left) is unchanged - no dom-fig", "fig-wide fig-first" in ff and "dom-fig" not in ff, ff)

    # 2 - only what is shown ships, "used_in" from the real references
    img = os.path.join(md, "assets", "img")
    io.open(os.path.join(img, "spare_ai.webp"), "wb").write(b"RIFF")
    meta = cs.load(os.path.join(img, "_photo_meta.json"))
    meta["spare_ai.webp"] = {"generated": True, "description": "An AI tank.", "used_in": "M01 presentation, slide s02"}
    meta["ship.jpg"]["used_in"] = "M07 presentation, slide s09"
    cs.save(os.path.join(img, "_photo_meta.json"), meta)
    code, out = run(COMPILE, c, "--module", "1", "--only", "deck")
    meta = cs.load(os.path.join(img, "_photo_meta.json"))
    left = cs.load(os.path.join(img, "_unused", "_photo_meta.json"))
    check("2: a picture no page shows is left out of the package - moved, with its record, to assets/img/_unused/ - and said",
          not os.path.isfile(os.path.join(img, "spare_ai.webp")) and os.path.isfile(os.path.join(img, "_unused", "spare_ai.webp"))
          and "spare_ai.webp" not in meta and "spare_ai.webp" in left and "left out of the package" in out
          and "- spare_ai.webp" in out, out)
    check("2: ... \"used_in\" is rewritten from where the pages really show the picture", meta["ship.jpg"]["used_in"] == "M01 presentation, slide s01",
          meta["ship.jpg"])
    sheet = cs.load(sp(c))
    sheet["screens"]["s02"]["inset"] = {"photo": "assets/img/spare_ai.webp", "caption": "An AI tank"}
    cs.save(sp(c), sheet)
    code, out = run(COMPILE, c, "--module", "1", "--only", "deck")
    meta = cs.load(os.path.join(img, "_photo_meta.json"))
    check("2: ... named again in the build sheet, it comes back with its record and is shown", os.path.isfile(os.path.join(img, "spare_ai.webp"))
          and meta.get("spare_ai.webp", {}).get("used_in") == "M01 presentation, slide s02" and "Back in the package" in out
          and "spare_ai.webp" in section(deck(md), "s02"), out)

    # 3 - a real photograph proposed for a task question answered on a picture
    tq = json.loads(json.dumps(SCREENS))
    tq.insert(5, {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "visual": "the plan",
                  "question": "On the fire control plan, tap the fuel preparation room.", "answer": "Fuel preparation room*\nGalley",
                  "feedback": "It is a category A machinery space."})
    os.makedirs(os.path.join(tmp, "v52t"))
    c3, md3 = new_course(os.path.join(tmp, "v52t"), script(screens=tq))
    sheet = cs.load(sp(c3))
    sheet["screens"]["q02"] = {"figure": "assets/fig/scale.svg", "areas": {"Fuel preparation room": [10, 10, 20, 20], "Galley": [50, 10, 20, 20]}}
    cs.save(sp(c3), sheet)
    io.open(os.path.join(md3, "assets", "img", "plan.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
    pm = cs.load(os.path.join(md3, "assets", "img", "_photo_meta.json"))
    pm["plan.jpg"] = {"source": "Wikimedia Commons", "author": "A", "licence": "CC BY 4.0", "description": "A fire control plan.",
                      "shows": ["fire control plan"]}
    cs.save(os.path.join(md3, "assets", "img", "_photo_meta.json"), pm)
    code, out = run(COMPILE, c3, "--module", "1", "--only", "tasks")
    fix_list = out.split("To fix before it is shown")[1] if "To fix before it is shown" in out else ""
    check("3: a tap-the-place question about what a real photograph of the module shows: a note with the photo and the build-sheet "
          "line - never in \"To fix\"", "Real photographs a task question could be answered on" in out
          and '(q02, hotspot): the real photograph plan.jpg shows "fire control plan" - build-sheet line: "q02": {"figure": '
          '"assets/img/plan.jpg", "areas": {"Fuel preparation room":' in out and "plan.jpg" not in fix_list, out)


def main():
    tmp = tempfile.mkdtemp(prefix="compile_")
    try:
        # ---- a clean build
        os.makedirs(os.path.join(tmp, "a"))
        c, md = new_course(os.path.join(tmp, "a"), script())
        code, out = run(COMPILE, c, "--module", "1")
        check("an approved script with every picture builds clean (exit 0)", code == 0, out)
        check("finding 14 (2.50.0): the build points at build_module.py and the required visual review with its brief",
              "build_module.py" in out and "required" in out and "REVIEW_PROMPT.md" in out and "not handed over" in out, out)
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
        check("L56: the photograph carries what it shows and its credit into the full-screen viewer, unasked",
              'data-about="A ship taking gas." data-credit="Photo: Jane Doe · Wikimedia Commons · CC BY-SA 4.0"' in s01, s01)
        check("L51: every compiled deck loads the one picture viewer, gb_zoom, after the deck engine - never a second one",
              'href="../assets/gb_zoom.css"' in page and "gb_photo" not in page and
              page.find('src="../assets/gb_deck.js"') < page.find('src="../assets/gb_zoom.js"') < page.find("GBDeck.init"))
        check("design_system.py ships gb_zoom.js and gb_zoom.css with every module",
              all(os.path.isfile(os.path.join(md, "assets", x)) for x in ("gb_zoom.js", "gb_zoom.css")))
        sys.path.insert(0, HERE)
        import compile_module as cm
        bl = "\n".join(cm.words_html(["Ways named in the Code:", "• reliquefy", "• burn it", "Venting: not acceptable."]))
        check("a line starting with • becomes a list item (bullet drawn by the list)",
              '<li data-script-field="text" data-i="2">reliquefy</li>' in bl and "•" not in bl and bl.count('class="lead"') == 2, bl)
        check("over a photograph a • line stays a lead line marked .sub, its heading lines .head - no list on photos",
              '<p class="lead sub" data-script-field="text" data-i="3">the fuels</p>' in s01 and "<ul" not in s01
              and 'class="lead head"' in s01 and 'class="lead"' not in s01, s01)
        check("every line is numbered in script order, so a stepping figure can light it up",
              re.findall(r'data-i="(\d+)"', s02) == ["1", "2", "3"] and re.findall(r'data-i="(\d+)"', s01) == ["1", "2", "3", "4", "5"])
        check("a fragment that is already a .fill is not wrapped again (its contents would get no width)",
              cm.fill('<div class="fill m01-3d">x</div>') == '<div class="fill m01-3d">x</div>' and cm.fill("<svg/>") == '<div class="fill fig"><svg/></div>')
        tb = "\n".join(cm.words_html(["Two ways:", "Gas safe machinery space - a single failure cannot release gas.",
                                      "ESD-protected machinery space - gas may be released.", "So: two barriers.",
                                      "Anyone with safety duties needs this certificate."], emph={"boxes": [2, 3], "conclusion": 5}))
        check("the term before \" - \" or \": \" is bold (four words or fewer); the words are unchanged",
              "<b>Gas safe machinery space</b> - a single failure" in tb and "<b>So</b>: two barriers." in tb
              and "<b>" not in cm.marked("Ways named in the IGF Code: reliquefy") and "<b>" not in cm.marked("a fuel tank - with"))
        check("the build sheet's boxes and conclusion: .box, .call - in script order, every box one colour",
              re.findall(r'class="(box(?: alt)?|call|lead)"', tb) == ["lead", "box", "box", "lead", "call"], tb)
        ta = "\n".join(cm.words_html(["Two ways:", "Gas safe - no release.", "ESD-protected - may release."],
                                     emph={"boxes": [2, 3], "box_alt": [3]}))
        check("a .box.alt only where the build sheet names box_alt",
              re.findall(r'class="(box(?: alt)?|lead)"', ta) == ["lead", "box", "box alt"], ta)
        bb = "\n".join(cm.words_html(["Two ways:", "• ventilated - fans draw air out", "• inerted - filled with gas"],
                                     emph={"boxes": [2, 3]}))
        check("a • line in a box loses its typed bullet - the box sets it apart, one bullet look per deck",
              "•" not in bb and bb.count('class="box') == 2, bb)
        sq = "\n".join(cm.words_html(["1 Risk assessment - by the master.", "2 Isolate - pipes blanked.",
                                      "3 Ventilate the space."]))
        check("steps numbered in the script are one numbered list: no headline, no square, the number its marker",
              '<ol class="support seq">' in sq and sq.count("<li ") == 3 and 'class="statement"' not in sq
              and '<span class="n">1</span> <b>Risk assessment</b> - by the master.' in sq, sq)
        nq = "\n".join(cm.words_html(["2 tanks hold the fuel.", "3 pumps move it."]))
        check("lines that start with a count but not 1, 2, 3 ... stay ordinary lines",
              "seq" not in nq and 'class="n"' not in nq, nq)
        pq = "\n".join(cm.words_html(["Before entry:", "1 Test the air.", "2 Enter."], dark_photo=True))
        check("numbered steps over a photograph: .lead.sub.step with the number as marker, the line above .head",
              pq.count('class="lead sub step"') == 2 and 'class="lead head"' in pq and '<span class="n">2</span>' in pq, pq)
        lg = "\n".join(cm.words_html(["Fuel tank - in a hold.", "Vent mast - high above deck."], legend=True))
        check("a legend: a numbered row counting 1, 2 ... (data-n), the script number kept as data-i",
              lg.startswith('<ol class="legend">') and '<li data-script-field="text" data-i="2" data-n="2"><b>Vent mast</b> - high above deck.</li>' in lg, lg)
        lg2 = "\n".join(cm.words_html(["Five steps:", "1 Fuel tank - cold.", "2 TCS - valves."], legend=False, first_statement=False,
                                      idx=[1, 2, 3]))
        lg3 = "\n".join(cm.words_html(["1 Fuel tank - cold.", "2 TCS - valves."], legend=True, idx=[2, 3]))
        check("a legend whose words already carry their numbers draws no second number; badges count within the row",
              lg3.startswith('<ol class="legend own-numbers">') and 'data-i="2" data-n="1"' in lg3, lg3)
        check("around a stage drawing one line is reading text, not a headline",
              '<p class="lead" data-script-field="text" data-i="1">Five steps:</p>' in "\n".join(cm.words_html(["Five steps:"], first_statement=False)), lg2)
        meta = {"author": "Tholme (Wikimedia Commons user), own work", "source": "Wikimedia Commons", "licence": "CC BY-SA 4.0",
                "url_or_origin": "https://commons.wikimedia.org/wiki/File:MF_Bergensfjord_filling_LNG_in_Arsv%C3%A5gen.jpg",
                "orig_size": "4032x3024 px", "stored_size": "1600x1200 px JPEG q82 (resized, not cropped)", "attribution_required": True}
        check("a credit names the work, the author, the source, the licence and the change (CC BY-SA)",
              cm.credit_line(meta) == "Photo: MF Bergensfjord filling LNG in Arsvågen · Tholme · Wikimedia Commons · CC BY-SA 4.0 · resized",
              cm.credit_line(meta))
        few = [f for f in cs.media_findings(script()) if f["rule"] == "v_few_photos"]
        more = json.loads(json.dumps(SCREENS))
        more[1]["visual"] = "Thermometer scale; a real photo of a bunker station beside it."
        check("L52: fewer than half the teaching slides with a real photograph -> a suggestion; a real photo beside a drawing counts",
              len(few) == 1 and few[0]["level"] != "fail" and "1 of 3" in few[0]["detail"]
              and not [f for f in cs.media_findings(script(screens=more)) if f["rule"] == "v_few_photos"], few)
        check("a task slide carries the tablet sign and its lines grouped",
              'class="act-ico"' in section(page, "t01") and '<div class="act-lines">' in section(page, "t01"))
        check("the footer's title is cut at a whole word", 'data-foot="M01 · IGF SHIPS · NOVIKONTAS"' in s02
              and cm.compile_deck(dict(script(), title="IGF ship design and operational characteristics"), {}, md, None, "x", True)[0]
              .count('data-foot="M01 · IGF SHIP DESIGN AND OPERATIONAL · NOVIKONTAS"') == 6)
        check("split + a drawing -> two-col fig-wide: the reading column (.copy), its statement and list, the picture in .fill.fig",
              'slide-body two-col fig-wide dom-fig"' in s02 and '<div class="copy">' in s02 and 'class="statement"' in s02
              and 'class="support"' in s02 and '<div class="fill fig"><svg viewBox' in s02, s02)
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
        # 2.52.0: the kind BUILT - s04 is planned as a 3D model and kept a flat drawing ("declined_3d")
        check("every teaching slide says its picture kind (data-visual), as built",
              'data-visual="schematic"' in s04 and 'data-visual="photo"' in s01 and 'data-visual="interactive_diagram"' in s03)
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
        check("2.42.0: --init-build waits for the approved ILO map and the knowledge-base decision (belt and braces)",
              code == 2 and "cannot be built yet" in out and "ILO map" in out
              and not os.path.isfile(os.path.join(c4, "working_claude", "script", "M01.build.json")), out)
        gate_fixture.open_gate(c4)
        code, out = run(COMPILE, c4, "--module", "1", "--init-build")
        check("--init-build writes a starter build sheet",
              code == 0 and os.path.isfile(os.path.join(c4, "working_claude", "script", "M01.build.json")), out)
        sheet = cs.load(os.path.join(c4, "working_claude", "script", "M01.build.json"))
        check("the starter build sheet lists every slide with an empty figure (a photo's stays empty; a drawing's names its starter spec, 2.50.0)",
              sorted(sheet["screens"]) == ["s01", "s02", "s03", "s04", "t01", "t02"]
              and sheet["screens"]["s01"] == {"figure": "", "visual_kind": "photo"}
              and sheet["screens"]["s02"].get("figure") == "s02.kit.json", sheet["screens"])
        # 2.50.0 - starter figure-kit specs: the agent edits them, it does not write them from nothing
        figs = os.path.join(c4, "working_claude", "figures", "M01")
        s2e, s3e = sheet["screens"]["s02"], sheet["screens"]["s03"]
        check("2.50.0: --init-build writes a starter spec for each drawing slide and none for a photo slide, and the "
              "slide's entry names it (two-col, dark, a note that it is a starter)",
              {"s02.kit.json", "s03.kit.json"} <= set(os.listdir(figs)) and "s01.kit.json" not in os.listdir(figs)
              and s2e["composition"] == "two-col" and s2e["dark"] is True and "starter" in s2e["_figure"]
              and s3e["figure"] == "s03.kit.json" and "figure" in sheet["screens"]["s04"] and sheet["screens"]["s04"]["figure"] == "m01_s04_3d.html"
              and "starter figure: figures\\M01\\s03.kit.json - 3 parts, 3 steps" in out, (sorted(os.listdir(figs)), out))
        # 2.50.6 (M01 benchmark run 5, s05) - a model_3d slide gets its 2D starter too: declining the 3D ("declined_3d") edits
        # it, never writes a spec from nothing. The scene stays the plan: the entry still names the 3D figure
        s4e = sheet["screens"]["s04"]
        s4k = os.path.join(figs, "s04.kit.json")
        spec4 = cs.load(s4k) if os.path.isfile(s4k) else {}
        check("2.50.6: --init-build writes a 2D starter spec for a model_3d slide - the script's own parts, a step per line - "
              "and its entry keeps the 3D scene as the plan, with a note how to switch to the starter (\"_2d\")",
              bool(spec4.get("parts")) and len(spec4.get("steps") or []) >= 2 and s4e.get("figure") == "m01_s04_3d.html"
              and "s04.kit.json" in s4e.get("_2d", "") and "declined_3d" in s4e.get("_2d", "")
              and "_2d" in s4e.get("_figure", "")
              and "figures\\M01\\s04.kit.json" in out and "the 2D figure if the 3D scene is declined" in out, (s4e, spec4, out))
        if spec4:
            code, kout = run(os.path.join(SKILLS, "course-visuals", "kit", "scripts", "check_kit.py"), "spec", s4k)
            check("2.50.6: ... and that starter passes check_kit.py", code == 0 and "clean" in kout, kout)
        spec3 = cs.load(os.path.join(figs, "s03.kit.json"))
        spec2 = cs.load(os.path.join(figs, "s02.kit.json"))
        ids3 = [p["id"] for p in spec3["parts"] if p.get("id")]
        check("... the parts are the script's own words (each line's name), typed by the kit's words (tank, space), one step per "
              "line lighting it and moving its part",
              [p["type"] for p in spec3["parts"]] == ["tank", "space", "space"]
              and [p["label"] for p in spec3["parts"]] == ["Fuel tank", "Tank connection space", "Fuel preparation room"]
              and [t["line"] for t in spec3["steps"]] == [1, 2, 3] and [t["play"][0][0] for t in spec3["steps"]] == ids3
              and spec3["size"] == [640, 390] and spec3["idle"] == "Press Next step" and spec3["label"] == "General arrangement."
              and spec3["steps"][0]["title"].startswith("1 · Fuel tank"), spec3)
        check("... a line the kit has no word for becomes a text callout the step reveals, a scale word a scale; none overlap",
              [p["type"] for p in spec2["parts"]] == ["ga", "text", "scale"]
              and spec2["parts"][1]["text"] == "Mandatory since 2017" and spec2["parts"][1].get("reveal") is True
              and spec2["steps"][1]["play"] == [["P2", 1, 600]], spec2)
        boxes = [(p["x"], p["y"]) for p in spec2["parts"] + spec3["parts"]]
        check("... every part has its own place on the grid", all("x" in p and "y" in p for p in spec2["parts"] + spec3["parts"])
              and len({(p["x"], p["y"]) for p in spec3["parts"]}) == len(spec3["parts"]), boxes)
        kit = os.path.join(SKILLS, "course-visuals", "kit", "scripts", "check_kit.py")
        for name in ("s02", "s03"):
            code, kout = run(kit, "spec", os.path.join(figs, name + ".kit.json"))
            check("2.50.0: the starter %s spec passes check_kit.py" % name, code == 0 and "clean" in kout, kout)
        # never overwritten: a spec the agent has edited stays as it is, however many times --init-build runs again
        mine = os.path.join(figs, "s03.kit.json")
        edited = dict(spec3, label="Edited by hand.")
        cs.save(mine, edited)
        os.remove(os.path.join(c4, "working_claude", "script", "M01.build.json"))
        code, out = run(COMPILE, c4, "--module", "1", "--init-build")
        again = cs.load(os.path.join(c4, "working_claude", "script", "M01.build.json"))
        check("2.50.0: --init-build never overwrites a figure spec that is there (the entry still names it, with no starter note)",
              code == 0 and cs.load(mine) == edited and "s03.kit.json" not in out and "s02.kit.json" not in out
              and again["screens"]["s03"]["figure"] == "s03.kit.json" and "_figure" not in again["screens"]["s03"], out)
        s4 = sheet["screens"]["s04"]
        check("2.49.7: a model_3d slide's starter entry plans its scene by default - its figure, its scene file and three.js in "
              "\"scripts\", how to build it (M03's m03_station3d.js, GUIDE 2b) and how to keep a 2D figure instead (\"declined_3d\")",
              s4.get("figure") == "m01_s04_3d.html" and s4.get("visual_kind") == "model_3d"
              and sheet["scripts"] == ["assets/vendor/three.min.js", "assets/js/m01_s04_3d.js"]
              and "m03_station3d.js" in s4.get("_figure", "") and "declined_3d" in s4.get("_figure", "")
              and "__scene3d" in s4.get("_figure", ""), sheet)
        code, out = run(COMPILE, c4, "--module", "1", "--init-build")
        check("--init-build never replaces an existing build sheet", code == 2, out)
        # finding 8: a new module has no folder - --init-build makes it, with the factory's style files, ready to compile
        os.makedirs(os.path.join(tmp, "d2"))
        c4b, md4b = new_course(os.path.join(tmp, "d2"), script(), build=False)
        gate_fixture.open_gate(c4b)
        shutil.rmtree(md4b)
        code, out = run(COMPILE, c4b, "--module", "1", "--init-build")
        check("finding 8: --init-build makes the module folder and puts the factory's style files in it",
              code == 0 and os.path.isfile(os.path.join(md4b, "assets", "gb_tokens.css"))
              and os.path.isfile(os.path.join(md4b, "assets", "gb_deck.js")), out)
        code, out = run(COMPILE, c4b, "--module", "1")
        check("... and the first compile then runs (exit 1: the pictures are not chosen yet, not 2: no folder)",
              code == 1 and os.path.isfile(os.path.join(md4b, "presentation", "index.html")), out[-500:])

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

        # ---- a photograph beside the words, a legend, an inset photograph
        os.makedirs(os.path.join(tmp, "f"))
        c6, md6 = new_course(os.path.join(tmp, "f"), script())
        bp = os.path.join(c6, "working_claude", "script", "M01.build.json")
        sheet = cs.load(bp)
        sheet["screens"]["s02"] = {"figure": "assets/img/ship.jpg"}
        sheet["screens"]["s03"]["legend"] = True
        sheet["screens"]["s03"]["figure"] = "cards.html"
        io.open(os.path.join(c6, "working_claude", "figures", "M01", "cards.html"), "w", encoding="utf-8").write(
            '<div class="fig-cards"><img src="../assets/img/ship.jpg" alt="Truck to ship"><img src="../assets/img/ship.jpg" '
            'alt="Logo" data-no-zoom /></div>')
        sheet["screens"]["s04"].update(inset={"photo": "assets/img/ship.jpg", "caption": "On board: the tanks."}, boxes=[2, 3])
        cs.save(bp, sheet)
        code, out = run(COMPILE, c6, "--module", "1")
        p6 = deck(md6)
        a2, a3, a4 = section(p6, "s02"), section(p6, "s03"), section(p6, "s04")
        check("split + a photograph -> the photo fills the right of the screen (.slide.photo.split), never a small photo in a column",
              'class="slide photo split"' in a2 and "photo-wrap" in a2 and "two-col" not in a2, a2)
        check("legend: true -> the lines as a numbered row under the drawing", '<ol class="legend">' in a3, a3)
        check("inset: a real photograph under the words, its caption and credit marked data-script-ignore",
              '<figure class="inset"><img src="../assets/img/ship.jpg"' in a4 and "<figcaption data-script-ignore>On board: the tanks. Photo:" in a4, a4)
        check("L56: a photograph inside a drawing fragment gets its description and credit; data-no-zoom is left alone",
              '<img src="../assets/img/ship.jpg" alt="Truck to ship" data-about="A ship taking gas." data-credit="Photo:' in a3
              and '<img src="../assets/img/ship.jpg" alt="Logo" data-no-zoom />' in a3, a3)
        check("L56: an inset photograph opens too, with what it shows and its credit",
              'data-about="A ship taking gas."' in a4.split('<figure class="inset">')[1], a4)
        code, out = run(MATCH, c6, "--module", "1", "--part", "instructor")
        check("... and the words still match the approved script", code == 0, out)
        # finding 3: an inset on a photo slide (.photo.split) sat in .photo-copy, which no inset rule reached - 74 px off the slide
        sheet["screens"]["s02"]["inset"] = {"photo": "assets/img/ship.jpg", "caption": "A second look."}
        cs.save(bp, sheet)
        run(COMPILE, c6, "--module", "1", "--force")
        a2 = section(deck(md6), "s02")
        css6 = io.open(os.path.join(md6, "assets", "gb_compose.css"), encoding="utf-8").read()
        m_inset = re.search(r"\.photo-copy \.inset img\{([^}]*)\}", css6)
        check("finding 3: an inset on a photo slide is inside the words' column and that column styles it at inset size",
              'class="slide photo split"' in a2 and 0 <= a2.find("photo-copy") < a2.find('<figure class="inset">')
              and m_inset and "max-height:min(16vh" in m_inset.group(1) and ".photo-copy .inset{display:flex" in css6, a2[:600])
        sheet["screens"]["s02"].pop("inset")
        cs.save(bp, sheet)
        run(COMPILE, c6, "--module", "1", "--force")
        cs.save(os.path.join(md6, "assets", "img", "_photo_meta.json"),
                {"ship.jpg": dict(PHOTO_META["ship.jpg"], description="")})
        code, out = run(COMPILE, c6, "--module", "1")
        check("L56: a photograph with no description is reported - its panel would say nothing",
              code == 1 and 'has no "description"' in out, out)
        # finding 14: a credit that shows where the file lives on somebody's computer is a build problem
        for field, val in (("source", "C:\\Users\\aleksisv\\Desktop\\photos\\ship.jpg"), ("author", "D:/Kursi/photos/jane"),
                           ("source", "working_claude\\figures\\M01"), ("source", "assets/img/ship_raw.jpg")):
            cs.save(os.path.join(md6, "assets", "img", "_photo_meta.json"), {"ship.jpg": dict(PHOTO_META["ship.jpg"], **{field: val})})
            code, out = run(COMPILE, c6, "--module", "1", "--force")
            check("finding 14: a credit with a path in its %s (%s) is a build problem" % (field, val[:14]),
                  code == 1 and "credit or caption shows a file-system path" in out, out)
        cs.save(os.path.join(md6, "assets", "img", "_photo_meta.json"), PHOTO_META)
        code, out = run(COMPILE, c6, "--module", "1", "--force")
        check("... and a clean credit (a name, a source, a licence, a web address) is not", "file-system path" not in out, out)
        io.open(os.path.join(md6, "assets", "gb_zoom.js"), "a", encoding="utf-8").write("/* old */")
        code, out = run(COMPILE, c6, "--module", "1")
        check("F1 (2.49.2): a module whose gb_zoom.js was edited inside it stops the build, naming the file and the exact command",
              code == 2 and "gb_zoom.js" in out and "design_system.py" in out and "install" in out and "--update" in out
              and "Stopped - nothing was built" in out, out)
        io.open(os.path.join(md6, "assets", "gb_compose.css"), "a", encoding="utf-8").write("/* old */")
        code, out = run(COMPILE, c6, "--module", "1")
        check("... and so does every shared style file edited there (both listed)",
              code == 2 and "gb_compose.css" in out and "gb_zoom.js" in out and "install" in out, out)

        # ---- L57: a drawing of real things carries their real photographs, unasked
        os.makedirs(os.path.join(tmp, "h"))
        c8, md8 = new_course(os.path.join(tmp, "h"), script())
        io.open(os.path.join(md8, "assets", "img", "room.jpg"), "wb").write(b"\xff\xd8room\xff\xd9")
        cs.save(os.path.join(md8, "assets", "img", "_photo_meta.json"),
                dict(PHOTO_META, **{"room.jpg": dict(PHOTO_META["ship.jpg"], shows=["gas safe machinery spaces"])}))
        sib = os.path.join(c8, "modules", "module02", "assets", "img")
        os.makedirs(sib)
        io.open(os.path.join(sib, "esd.jpg"), "wb").write(b"\xff\xd8esd\xff\xd9")
        cs.save(os.path.join(sib, "_photo_meta.json"), {
            "esd.jpg": {"source": "Wikimedia Commons", "author": "Ann Roe", "licence": "CC0", "description": "An ESD room.",
                        "shows": ["esd-protected machinery space"]},
            "held.jpg": {"description": "x", "shows": ["fuel tank"], "rights_state": "RIGHTS_REVIEW_REQUIRED"}})
        io.open(os.path.join(sib, "held.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
        code, out = run(COMPILE, c8, "--module", "1")
        p8 = deck(md8)
        h4 = section(p8, "s04")
        check("L57: each real thing a drawing names gets its photo under the drawing, matched by 'shows' (plural or not)",
              '<div class="photo-strip" data-script-ignore>' in h4 and 'data-name="Gas safe machinery space"' in h4
              and 'data-about="A ship taking gas."' in h4, h4[-900:])
        check("L57: a photo from another module of the course is copied in with its record",
              'src="../assets/img/esd.jpg"' in h4 and os.path.isfile(os.path.join(md8, "assets", "img", "esd.jpg"))
              and cs.load(os.path.join(md8, "assets", "img", "_photo_meta.json"))["esd.jpg"].get("copied_from") == "module02", out)
        check("L58: the slide's own photograph is never shown again as a thumbnail", p8.count('src="../assets/img/ship.jpg"') == 1, p8.count("ship.jpg"))
        check("L57: a photo awaiting a rights review is never used", "held.jpg" not in p8 and
              not os.path.isfile(os.path.join(md8, "assets", "img", "held.jpg")))
        check("L57: the photo strip's words are marked data-script-ignore, and the deck still matches the script",
              run(MATCH, c8, "--module", "1", "--part", "instructor")[0] == 0)
        check("L57: a slide that is a photograph gets no strip", "photo-strip" not in section(p8, "s01"))
        take = os.path.join(c8, "working_claude", "PHOTOS_TO_TAKE.md")
        check("L57: a build with every drawn thing photographed says so in PHOTOS_TO_TAKE.md",
              os.path.isfile(take) and "every drawn thing has its photograph" in io.open(take, encoding="utf-8").read(), out)
        cs.save(os.path.join(md8, "assets", "img", "_photo_meta.json"), PHOTO_META)
        io.open(take, "a", encoding="utf-8").write("- my own note\n")
        code, out = run(COMPILE, c8, "--module", "1", "--force")
        t = io.open(take, encoding="utf-8").read()
        check("L57: a drawn thing with no photo is reported and listed for Novikontas; the operator's notes are kept",
              "Gas safe machinery space · s04" in out and "- Gas safe machinery space · s04" in t and "- my own note" in t
              and t.count("## M01") == 1, t)
        check("L57: a photo without 'shows' is pointed out - no drawing can use it", 'without "shows"' in out and "ship.jpg" in out, out)
        check("L57: the build is not blocked by a photo still to take (exit 0)", code == 0, out)
        os.makedirs(os.path.join(tmp, "i"))
        c9, md9 = new_course(os.path.join(tmp, "i"), script())
        cs.save(os.path.join(md9, "assets", "img", "_photo_meta.json"),
                {"ship.jpg": dict(PHOTO_META["ship.jpg"], shows=["gas safe machinery space"])})
        io.open(os.path.join(c9, "working_claude", "figures", "M01", "row3d.html"), "w", encoding="utf-8").write(
            '<div class="fill m-3d-col"><canvas></canvas><div class="m-ctl">x</div></div>')
        bp9 = os.path.join(c9, "working_claude", "script", "M01.build.json")
        sh9 = cs.load(bp9)
        sh9["screens"]["s04"] = {"figure": "row3d.html", "inset": {"photo": "assets/img/ship.jpg", "under": "figure"}}
        cs.save(bp9, sh9)
        run(COMPILE, c9, "--module", "1")
        i4 = section(deck(md9), "s04")
        frag = i4[i4.find('<div class="fill m-3d-col">'):i4.find("</div></div>", i4.find('<div class="fill m-3d-col">'))]
        check("a 3D fragment that lays itself out keeps its row: the inset and the L57 strip go with the words, never beside the canvas",
              "<figure" not in frag and "photo-strip" not in frag and '<figure class="inset">' in i4, i4[-900:])
        # ---- L58: every photograph once in the whole course
        os.makedirs(os.path.join(tmp, "j"))
        c10, md10 = new_course(os.path.join(tmp, "j"), script())
        io.open(os.path.join(md10, "assets", "img", "room.jpg"), "wb").write(b"\xff\xd8room\xff\xd9")
        cs.save(os.path.join(md10, "assets", "img", "_photo_meta.json"), dict(PHOTO_META, **{"room.jpg": {
            "description": "A machinery space.", "shows": ["gas safe machinery space"]}}))
        m0 = os.path.join(c10, "modules", "module00")              # an earlier module, already built
        os.makedirs(os.path.join(m0, "assets", "img"))
        os.makedirs(os.path.join(m0, "presentation"))
        io.open(os.path.join(m0, "assets", "img", "m00_room.jpg"), "wb").write(b"\xff\xd8room\xff\xd9")       # the same bytes
        io.open(os.path.join(m0, "assets", "img", "m00_ship.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
        io.open(os.path.join(m0, "presentation", "index.html"), "w", encoding="utf-8").write(
            '<section class="slide" id="s07"><img src="../assets/img/m00_ship.jpg"></section>'
            '<section class="slide" id="s08"><div class="photo-strip" data-script-ignore><figure class="pthumb">'
            '<img src="../assets/img/m00_room.jpg"></figure></div></section>')
        bp10 = os.path.join(c10, "working_claude", "script", "M01.build.json")
        sh10 = cs.load(bp10)
        sh10["screens"]["s02"] = {"figure": "assets/img/ship.jpg"}
        cs.save(bp10, sh10)
        code, out = run(COMPILE, c10, "--module", "1")
        p10 = deck(md10)
        check("L58: one photograph placed by hand on two slides is a problem to fix (exit 1)",
              code == 1 and "already shown on M01 s01" in out and "(s02)" in out, out)
        check("L58: a photograph an earlier module already shows (the same file under another name) is a problem here",
              "already shown on M00 s07" in out, out)
        check("L58: a thumbnail never repeats a photograph another module shows - it gives way and the thing is listed",
              "room.jpg" not in p10 and "Gas safe machinery space · s04" in out, out)
        check("L58: a thumbnail elsewhere is not a problem for a photo placed by hand here - that thumbnail gives way",
              "M00 s08" not in out, out)
        sh8 = cs.load(os.path.join(c8, "working_claude", "script", "M01.build.json"))
        sh8["screens"]["s04"]["no_photo"] = ["gas safe machinery space"]
        cs.save(os.path.join(c8, "working_claude", "script", "M01.build.json"), sh8)
        cs.save(os.path.join(md8, "assets", "img", "_photo_meta.json"),
                dict(PHOTO_META, **{"room.jpg": dict(PHOTO_META["ship.jpg"], shows=["gas safe machinery space"])}))
        code, out = run(COMPILE, c8, "--module", "1", "--force")
        check("L57: 'no_photo' in the build sheet keeps a photo that does not fit how the thing is drawn off that slide - and lists it",
              "room.jpg" not in section(deck(md8), "s04") and "Gas safe machinery space · s04" in out, out)
        # ---- a generated picture: no credit line and no label on screen (operator, 2026-10-15); never an L57 thumbnail
        os.makedirs(os.path.join(tmp, "k"))
        c11, md11 = new_course(os.path.join(tmp, "k"), script())
        io.open(os.path.join(md11, "assets", "img", "ai_tank.webp"), "wb").write(b"RIFF\x00\x00\x00\x00WEBPgen")
        cs.save(os.path.join(md11, "assets", "img", "_photo_meta.json"), dict(PHOTO_META, **{"ai_tank.webp": {
            "source": "GENERATED", "generated": True, "generator": "Nano Banana", "licence": "AI-generated",
            "url_or_origin": "generated:ai_tank", "description": "A tank in its hold.",
            "shows": ["gas safe machinery space"]}}))
        bp11 = os.path.join(c11, "working_claude", "script", "M01.build.json")
        sh11 = cs.load(bp11)
        sh11["screens"]["s04"]["inset"] = {"photo": "assets/img/ai_tank.webp", "caption": "an LNG tank in its hold."}
        cs.save(bp11, sh11)
        code, out = run(COMPILE, c11, "--module", "1")
        k4 = section(deck(md11), "s04")
        check("a generated inset: its caption is the build sheet's own, with no credit line and no label",
              "<figcaption data-script-ignore>An LNG tank in its hold.</figcaption>" in k4
              and "data-credit" not in k4.split('<figure class="inset">')[1] and "generated" not in k4.lower(), k4[-700:])
        sh11["screens"]["s04"].pop("inset")
        cs.save(bp11, sh11)
        code, out = run(COMPILE, c11, "--module", "1", "--force")
        check("L57 never places a generated picture as a real-photo thumbnail, even when its record says what it shows",
              "ai_tank.webp" not in deck(md11) and "Gas safe machinery space · s04" in out, out)
        kitfig = ('<div class="fill fig kit-fig"><script type="application/json" id="k">' + json.dumps(
            {"parts": [{"type": "space", "label": "ENGINE\nROOM"}, {"type": "space", "label": "TCS"}, {"type": "text", "text": "up the vent mast"},
                       {"type": "text", "text": "LNG LIQUID LINE"}, {"type": "text", "text": "Tank"}, {"type": "text", "text": "0 % LEL"}],
             "steps": [{"line": 2}, {"line": [1, 3]}]}) + "</script></div>")
        got = cm.drawn_parts(["Tank connection space - around the valves.", "Fuel tank - in the hold.", "Gas mode: pilot oil."], kitfig)
        check("L57: parts come from the slide's terms with the drawing's own step numbers (one line or several), then its labels;"
              " an abbreviation, a bare 'Tank', a reading and a leading 'up the' are dropped",
              got == [(2, "Tank connection space"), (1, "Fuel tank"), (2, "Gas mode"), (None, "Engine room"), (None, "Vent mast"),
                      (None, "LNG liquid line")], got)
        check("L57: a photo of an 'LNG fuel tank' shows a 'fuel tank', but a 'fuel tank' photo is never an 'oil fuel tank'",
              cm.shows_it("LNG fuel tanks", "Fuel tank") and not cm.shows_it("fuel tank", "Oil fuel tank")
              and not cm.shows_it("fuel tank", "Tank") and cm.shows_it("vent mast", "Vent masts"))
        check("L57: the list is one row per thing, with every slide that draws it",
              cm.by_thing([("s04", 2, "Vent mast"), ("s09", None, "vent masts"), ("s09", None, "Vent mast")]) == ["Vent mast · s04 (2), s09"])
        check("L57: only a real thing is listed as a photo to take - 'Gas mode' is not",
              cm.is_thing("Fuel tank") and cm.is_thing("Engine room") and not cm.is_thing("Gas mode"))

        # ---- a figure-kit spec (L55): data in the page, the kit shipped, the deck's own step buttons
        os.makedirs(os.path.join(tmp, "g"))
        c7, md7 = new_course(os.path.join(tmp, "g"), script())
        kit_spec = {"size": [300, 200], "label": "A valve closes on a pipe.",
                    "parts": [{"id": "F", "type": "pipe", "d": "M10 100 H290", "value": 1},
                              {"id": "V", "type": "valve", "x": 150, "y": 100, "value": 1, "label": "valve </script>"}],
                    "steps": [{"title": "The valve closes", "line": 2, "play": [["V", 0, 800], ["F", 0, 400]]}]}
        cs.save(os.path.join(c7, "working_claude", "figures", "M01", "valve.kit.json"), kit_spec)
        bp = os.path.join(c7, "working_claude", "script", "M01.build.json")
        sheet = cs.load(bp)
        sheet["screens"]["s04"] = {"figure": "valve.kit.json", "dark": True, "declined_3d": "the fixture's kit figure stands in for the scene"}
        cs.save(bp, sheet)
        code, out = run(COMPILE, c7, "--module", "1")
        p7 = deck(md7)
        k4 = section(p7, "s04")
        check("a .kit.json figure goes in as data for kit.js, never as a drawing",
              re.search(r'<svg data-kit="#kit-s04"[^>]*></svg>', k4) and '<script type="application/json" id="kit-s04">' in k4, k4[:600])
        tag = re.search(r'<svg data-kit="#kit-s04"[^>]*>', k4)
        check("2.60.0: the empty kit <svg> already says what kit.js will - role img, the spec's label, a viewBox - so "
              "check_visuals.py does not warn on it", tag and 'role="img"' in tag.group(0) and 'aria-label="A valve closes on a pipe."' in tag.group(0)
              and re.search(r'viewBox="0 0 [\d.]+ [\d.]+"', tag.group(0)), tag.group(0) if tag else k4[:400])
        check("... with the deck's own step buttons (.mediabar, prev / next / replay)",
              'class="mediabar"' in k4 and 'data-act="next"' in k4 and 'data-act="replay"' in k4, k4[-600:])
        check("... a '</script>' inside the spec cannot end the page's script early", "valve <\\/script>" in k4, k4)
        check("kit.css and kit.js are loaded, kit.js before GBDeck.init so its slide hooks are seen",
              '<link rel="stylesheet" href="../assets/kit.css">' in p7
              and p7.index('src="../assets/kit.js"') < p7.index("GBDeck.init"), p7[-900:])
        check("design_system.py ships kit.js and kit.css with every module, so the copy is the factory's",
              code == 0 and os.path.isfile(os.path.join(md7, "assets", "kit.js")), out)
        check("a deck with no kit figure loads no kit", "kit.js" not in page and "kit.css" not in page)
        io.open(os.path.join(md7, "assets", "kit_parts.js"), "w", encoding="utf-8").write("/* a course's new parts */")
        code, out = run(COMPILE, c7, "--module", "1", "--force")
        check("a course's own new parts (assets/kit_parts.js) load after kit.js",
              deck(md7).index("../assets/kit.js") < deck(md7).index("../assets/kit_parts.js"), out)
        sheet["screens"]["s04"] = {"figure": "valve.kit.json", "dark": True,
                                   "inset": {"photo": "assets/img/ship.jpg", "caption": "a ship.", "over": {"x": 30, "y": 10, "w": 90}}}
        cs.save(bp, sheet)
        code, out = run(COMPILE, c7, "--module", "1", "--force")
        k4 = section(deck(md7), "s04")
        check("an inset photo 'over' a kit drawing lies on it in the drawing's units, inside the drawing's own box",
              re.search(r'<div class="kit-holder"><svg data-kit="#kit-s04"[^>]*></svg><figure class="inset over" '
                        r'style="left:10.00%;top:5.00%;width:30.00%"><img src="../assets/img/ship.jpg"', k4), k4[:700])
        sheet["screens"]["s04"]["inset"]["over"] = {"x": 250, "y": 10, "w": 90}
        cs.save(bp, sheet)
        code, out = run(COMPILE, c7, "--module", "1", "--force")
        check("... one that would reach past the drawing is reported, and the photo goes under the words instead",
              code == 1 and '"over" puts the photo outside the drawing' in out and "kit-holder" not in deck(md7), out)
        sheet["screens"]["s04"] = {"figure": "valve.kit.json", "dark": True}
        cs.save(bp, sheet)
        cs.save(os.path.join(c7, "working_claude", "figures", "M01", "valve.kit.json"), {"size": [1, 1]})
        code, out = run(COMPILE, c7, "--module", "1", "--force")
        check("a kit spec with no parts is reported, not shipped blank", code == 1 and "has no parts" in out, out)

        # ---- a changed word is still caught on a compiled deck
        p = os.path.join(md, "presentation", "index.html")
        io.open(p, "w", encoding="utf-8").write(page.replace("Mandatory since 2017.", "Mandatory since 2016."))
        code, out = run(MATCH, c, "--module", "1", "--part", "instructor")
        check("check_script_match still fails a changed word", code == 1 and "2016" in out, out)

        recap_part(tmp)
        tasks_part(tmp)
        figures_part(tmp)
        every_way_part(tmp)
        team_part(tmp)
        language_part(tmp)
        fixes_part(tmp)
        v2492_part(tmp)
        v2494_part(tmp)
        v2497_part(tmp)
        v2520_part(tmp)
        layouts_part(tmp)
        three_part(tmp)
        variety_part(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
