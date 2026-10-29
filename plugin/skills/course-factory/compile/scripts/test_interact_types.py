# -*- coding: utf-8 -*-
"""test_interact_types - Part A + Part B, the ten interactive task types and the debrief rule (2.74.0), end to end.

    python test_interact_types.py

course-task-ux/templates/interact/example_set.json (one self-check with every type, its 3D scenes and build-sheet
entries) is compiled into a throwaway course and answered in headless Chrome or Edge through the real engine. Pinned:
  * every question of the example set is written as an approved script may write it, and the built page says exactly
    what was approved (check_script_match --part trainee);
  * all twelve answered right give 12 of 12, with no script error - the 3D types through the 3D kit's own api;
  * the debrief rule: a wrong answer is "Not right." with its brief reason, the right answer never marked on the tablet
    or on the result screen, while the classroom's items carry it whole - question, answer, right answer, why, brief, how
    sure - none cut to 90 / 120 characters;
  * "feedback": "now" keeps the older reveal; a brief that names the right answer is refused;
  * a self-check with no Part B, or Part B before Part A, gets its suggestion (never a must-fix).
Skipped (not failed) when no Chrome or Edge is found - the same rule as the drawing check.
"""
from __future__ import annotations

import copy
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drawing_check  # noqa: E402
import test_compile_module as tcm  # noqa: E402
import browser_slots  # noqa: E402

cs = tcm.cs
T = os.path.join(tcm.SKILLS, "course-task-ux", "templates", "interact")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def example():
    return json.load(io.open(os.path.join(T, "example_set.json"), encoding="utf-8"))


def course(tmp, feedback=None, delay=0.02):
    ex = example()
    c, md = tcm.new_course(tmp, tcm.script(screens=ex["screens"]), build=False)
    figs = os.path.join(c, "working_claude", "figures", "M01")
    screens = {"t10": {"try_tablet": False}}
    for qid, b in ex["build"].items():
        if isinstance(b, str):
            b = json.load(io.open(os.path.join(T, b), encoding="utf-8"))
        if b.get("scene"):
            shutil.copyfile(os.path.join(T, b["scene"]), os.path.join(figs, b["scene"]))
        screens[qid] = b
    screens["q30"] = dict(screens["q30"], delay=delay)
    sheet = {"module": 1, "screens": screens}
    if feedback:
        sheet["feedback"] = feedback
    cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), sheet)
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    return c, md, code, out


# the driver: answers each question as a trainee does (taps, the 3D kit's own select for a tap on a part), then writes
# what the classroom heard into <pre id="gbtest">. WRONG = the ids answered wrong on purpose.
DRIVER = r"""
(async function () {
  var WRONG = %s, out = {errors: [], report: null, look: {}};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  window.addEventListener('message', function (e) { if (e.data && e.data.type === 'gb-task-done') { out.report = e.data; } });
  var S = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };
  var q = function (s, r) { return (r || document).querySelector(s); }, qa = function (s, r) { return [].slice.call((r || document).querySelectorAll(s)); };
  var t = function (sel, w, r) { return qa(sel, r).filter(function (b) { return b.textContent.trim().indexOf(w) === 0; })[0]; };
  var go = async function () { q('#go').click(); await S(300); };
  var sec = function () { return q('.scr.on'); };
  try {
    await S(800);
    var s = sec(), TR = {'Propane vapour': 1, 'LPG boils': 0, 'Warm methane': 1, 'A reading of 0': 0};
    var cards = qa('.sw-card', s).map(function (c) { return q('.sw-st', c).textContent; });
    for (var i = 0; i < cards.length; i++) {
      var k = Object.keys(TR).filter(function (x) { return cards[i].indexOf(x) === 0; })[0];
      (TR[k] ? q('.sw-side.t', s) : q('.sw-side.f', s)).click(); await S(120);
      if (i < cards.length - 1) { q('.sw-next', s).click(); }
    }
    await S(200); await go();
    s = sec();
    t('.opt', WRONG.indexOf('q21') >= 0 ? '-0.5' : '-42', s).click(); qa('.sure button', s)[2].click(); await go();
    if (WRONG.indexOf('q21') >= 0) {
      out.look.q21 = {right: qa('.opt.right, .opt.missed', s).length, wrong: qa('.opt.wrong', s).length, vd: q('.vd', s).textContent,
        brief: getComputedStyle(q('.why .brief', s)).display, feedback: getComputedStyle(q('.why [data-script-field="feedback"]', s)).display,
        later: (q('.why .later', s) || {}).textContent || ''};
    }
    await go();
    s = sec(); q('.cl-sheetbtn', s).click();
    ['0', '.', '4', '×', '2', '.', '1'].forEach(function (k) { t('.cl-k', k, s).click(); });
    out.look.calcDock = q('#go').textContent; await go(); await go();
    s = sec(); var svg = q('.pr-box svg', s), r = svg.getBoundingClientRect(), yv = 462 - 13.7 / 18 * 434;
    var o = {bubbles: true, pointerId: 5, clientX: r.left + r.width * 0.85, clientY: r.top + yv / 520 * r.height, isPrimary: true};
    svg.dispatchEvent(new PointerEvent('pointerdown', o)); svg.dispatchEvent(new PointerEvent('pointerup', o)); await go(); await go();
    s = sec(); var rg = q('.ex-range', s); rg.value = 12; rg.dispatchEvent(new Event('input')); await go(); await go(); await S(150);
    rg.value = 1.05; rg.dispatchEvent(new Event('input')); out.look.covered = qa('.ex-ro.cover', s).length; await go(); await go();
    s = sec();
    ['Gas detection log', 'Cargo data sheet', 'Deck round note', 'Engine room log'].forEach(function (tl) {
      qa('.iv-src', s).filter(function (b) { return q('.iv-tl', b).textContent === tl; })[0].click(); q('.iv-pin', s).click();
    });
    t('.opt', 'A leak', s).click(); await go(); await go();
    s = sec();
    var pickC = async function (i, w) { qa('.cr-claim', s)[i].click(); await S(80); t('.gi-sh-o', w).click(); await S(80); };
    await pickC(0, 'Propane vapour is heavier'); await pickC(1, 'It is right'); await pickC(2, 'Butane boils at about -0.5'); await go(); await go();
    s = sec();
    var V = async function (tag, open) { t('.lu-v', tag, s).click(); await S(80); (open ? q('.lu-o', s) : q('.lu-s', s)).click(); await S(80); };
    out.look.k3 = !!q('.lu-stage', s).__k3;
    await V('V102', 1); await V('V202', 1); await V('V301', 1); await V('V302', 0); await V('V201', 0);
    out.look.pump = q('#go').textContent; await go(); out.look.flow = (q('.lu-side .gi-fb', s) || {}).textContent; await S(300); await go();
    s = sec(); var k3 = q('.in-stage', s).__k3;
    var rep = async function (part, bad) { k3.select(part); await S(150); (bad ? q('.in-rep', s) : q('.in-fine', s)).click(); await S(80); k3.select(null); await S(80); };
    await rep('line', 1); await rep('lamp', 1); await rep('det_cap', 1); await rep('fan', 1); await rep('ext', 0); await rep('gauge', 0); await go(); await go();
    s = sec(); var kk = q('.ta-stage', s).__k3;
    kk.select('seat_l'); await S(200); await go(); await go(); await S(200);
    kk.select('nut'); await S(200); await go(); await go(); await S(200);
    qa('.ta-t', s)[1].click(); await S(300); await go(); await go();
    s = sec(); q('.at-keys button', s).click(); await S(80);
    var lower = async function (n) { for (var j = 0; j < n; j++) { t('.at-lv button', 'Lower', s).click(); await S(30); } };
    var rec = async function (ms) { await S(ms); qa('.at-keys button', s)[1].click(); await S(80); };
    await lower(2); await rec(600); await lower(6); await rec(900); await lower(6); await rec(1300); await go(); await go();
    s = sec(); t('.opt', 'No', s).click(); qa('.sure button', s)[1].click(); await go(); await go(); await S(500);
    out.look.result = {rightShown: /Right answer/.test(q('#resScr').textContent), calib: (q('#resCalib') || {}).textContent || ''};
  } catch (e) { out.errors.push('driver: ' + e.message); }
  var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
}());
"""


def drive(exe, page, wrong, tmp):
    text = io.open(page, encoding="utf-8").read()
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    text = text[:i] + "<script>%s</script>" % (DRIVER % json.dumps(wrong)) + text[i:]
    w = os.path.join(os.path.dirname(page), "drive_interact.html")
    io.open(w, "w", encoding="utf-8").write(text)
    p = browser_slots.run([exe, "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--no-first-run", "--mute-audio",
                           "--user-data-dir=" + os.path.join(tmp, "prof"), "--allow-file-access-from-files", "--window-size=1280,800",
                           "--virtual-time-budget=60000", "--dump-dom", Path(w).as_uri()],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=400)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]]}


def script_part():
    print("\n-- the formats, the brief, Part A and Part B")
    ex = example()
    qs = [q for q in ex["screens"] if q["kind"] in cs.TASKS]
    bad = [x for q in qs for x in cs.read_answer(q)[0]]
    check("every question of the example set is written as an approved script may write it", bad == [], bad)
    q = copy.deepcopy([x for x in qs if x["id"] == "q21"][0])
    q["brief"] = "The right answer is -42 °C."
    check("a brief that names the right answer is refused", any("gives the right answer away" in x for x in cs.read_answer(q)[0]))
    q = copy.deepcopy([x for x in qs if x["id"] == "q26"][0])
    q["answer"] = q["answer"].replace(" | The pressure stays the same - the tank is closed", "")
    check("2.74.1 - check a colleague: claims with unequal numbers of choices are refused",
          any("same number of choices" in x for x in cs.read_answer(q)[0]), cs.read_answer(q)[0])
    for m, ans in (("true_false", "Only one statement*"), ("critique", "A claim with no corrections"), ("calculate", "about one"),
                   ("predict", "13.7 @ 40"), ("explore", "find: something => x >> 3"), ("line_up", "goal: A"),
                   ("inspect_round", "Lamp: fine"), ("take_apart", "part: Ball: a ball"), ("test_atmosphere", "space: Tank")):
        p = cs.read_answer({"id": "qx", "mechanic": m, "answer": ans, "options": ["a", "b"], "correct": "A"})[0]
        check("%s: a wrong format is caught in plain words" % m, bool(p), p)
    items, right = cs.answer_items([x for x in qs if x["id"] == "q27"][0])
    check("line it up: its pieces are the goal, the names kept out and every valve's tag and name",
          "Tank 2" in items and "Port manifold" in items and "V102" in items and "Tank 2 valve" in items and right == [], items)
    ex2 = example()
    a_only = [s for s in ex2["screens"] if s["kind"] == "task-slide" or s["id"] in ("q20", "q21", "q26")]
    for s in a_only:
        if s["id"] == "q26":
            s.update(mechanic="single_choice", options=["x", "y"], correct="A", bloom=1)
            s.pop("answer", None)
    slides = [{"id": "s%02d" % i, "kind": "slide", "title": "Theory %d" % i, "text": " ".join(["The cargo boils off on deck."] * 30),
               "visual": "x", "notes": "- " + " ".join(["Explain it."] * 12), "minutes": 6, "sub_ilo": "1.%d" % i} for i in (1, 2)]
    found, _ = cs.theory_findings(tcm.script(screens=slides + a_only)) if hasattr(cs, "theory_findings") else ([], None)
    rules = {f["rule"] for f in found} if found else set()
    if found:
        check("a self-check with no Part B question gets the suggestion, as a note", "t_no_challenge" in rules, sorted(rules))


def main():
    exe = drawing_check.find_browser()
    tmp = tempfile.mkdtemp(prefix="interact_")
    try:
        script_part()
        print("\n-- compiled from the approved script")
        c, md, code, out = course(os.path.join(tmp, "a"))
        page = os.path.join(md, "tasks", "sc2_cargo_hazards.html")
        check("the set compiles with no problem", code == 0 and os.path.isfile(page), out[-800:])
        if not os.path.isfile(page):
            return 1
        code2, out2 = tcm.run(tcm.MATCH, c, "--module", "1", "--part", "trainee")
        check("check_script_match: every word as approved (12 screens)", code2 == 0 and "12 screens" in out2, out2[-600:])
        p = io.open(page, encoding="utf-8").read()
        check("the page carries the debrief rule, the 3D kit and gb_interact.js before gb_answer.js",
              'data-reveal="debrief"' in p and "assets/kit3d.js" in p and p.index("gb_interact.js") < p.index("gb_answer.js"))
        check("no right answer readable in the page", "data-correct" not in p and "data-answer" not in p)
        crit = re.findall(r'<div class="cr-claim">(.*?)</div>', p)
        check("2.74.1 - check a colleague: every claim ends with 'keep it' and offers the same number of choices",
              crit and all(re.findall(r'data-o="([^"]*)"', x)[-1] == "*" for x in crit) and len({x.count('class="cr-o"') for x in crit}) == 1,
              [re.findall(r'data-o="([^"]*)"', x) for x in crit])
        rs = os.path.join(HERE, "..", "..", "..", "course-module-ux", "measure", "scripts", "review_sheets.mjs")
        g = subprocess.run(["node", rs, md, os.path.join(tmp, "graded"), "--grade-only"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("2.74.1 - the build's grader answers every type right and wrong by its keys (review_sheets.mjs --grade-only)",
              g.returncode == 0 and "every question graded as expected" in g.stdout, (g.stdout + g.stderr)[-900:])
        check("three.js is in the module for the 3D tasks", os.path.isfile(os.path.join(md, "assets", "vendor", "three.min.js")))
        _, md_now, _, _ = course(os.path.join(tmp, "b"), feedback="now")
        p_now = io.open(os.path.join(md_now, "tasks", "sc2_cargo_hazards.html"), encoding="utf-8").read()
        check('"feedback": "now" keeps the older reveal (no data-reveal)', "data-reveal" not in p_now)
        check("2.74.2 - a self-check under the debrief rule is answered once: no Start again (a 'feedback: now' page keeps it)",
              'id="again"' not in p and 'id="again"' in p_now)
        if not exe:
            print("  skip  no Chrome or Edge found - the page was not driven")
        else:
            print("\n-- answered on the tablet, in a browser")
            r = drive(exe, page, ["q21"], tmp)
            rep, look = r.get("report") or {}, r.get("look") or {}
            check("no script error on the page", not r.get("errors"), r.get("errors"))
            check("the 3D kit is up for the line-up", look.get("k3") is True, look)
            check("eleven right, one wrong on purpose: the classroom hears 11 of 12, detail 2",
                  rep.get("ok") == 11 and rep.get("total") == 12 and rep.get("detail") == 2, {k: rep.get(k) for k in ("ok", "total", "detail")})
            oks = [x.get("ok") for x in rep.get("items", [])]
            check("every interactive type answered right is right (all but question 2)", oks == [True, False] + [True] * 10, oks)
            w = look.get("q21") or {}
            check("the debrief rule: wrong is marked, the right one is not; 'Not right.', the brief shown, why hidden, 'in the debrief'",
                  w.get("right") == 0 and w.get("wrong") == 1 and w.get("vd") == "Not right." and w.get("brief") == "block"
                  and w.get("feedback") == "none" and "debrief" in w.get("later", ""), w)
            check("the result screen never shows the right answer; it counts certain-but-wrong",
                  (look.get("result") or {}).get("rightShown") is False and "1" in (look.get("result") or {}).get("calib", ""), look.get("result"))
            it = (rep.get("items") or [{}, {}])[1]
            check("the classroom gets the wrong item whole: answer, right answer, why, brief, how sure",
                  it.get("a") == "-0.5 °C" and it.get("c") == "-42 °C" and it.get("w") and it.get("n") and it.get("sure") == "Certain", it)
            items = rep.get("items") or []
            order = re.findall(r'<section class="scr" data-script="(q\d+)"', p)
            check("every item says which question it is (q, the script's id)", [x.get("q") for x in items] == order,
                  [[x.get("q") for x in items], order])
            q21 = p[p.index('data-script="q21"'):]
            q21 = q21[:q21.index("</section>")]
            k05 = [m.group(1) for m in re.finditer(r'<button[^>]*data-key="([0-9a-f]{8})"[^>]*>\s*([^<]*)', q21) if m.group(2).strip().startswith("-0.5")]
            check("the wrong pick goes as its key (p) and how sure as a number (s): the factory can count it across classes",
                  k05 and it.get("p") == k05 and it.get("s") == 2, [it.get("p"), k05, it.get("s")])
            np_ = {x.get("q"): len(x.get("p") or []) for x in items}
            n_cards = len(re.findall(r'class="sw-card"', p))
            check("true or false, check a colleague, investigate: one key per choice (each card, each claim, each pin and the pick)",
                  np_.get(items[0].get("q")) == n_cards and sorted(np_.values()).count(3) >= 1 and 5 in np_.values(), np_)
            longest = max((x.get("t") or "" for x in rep.get("items", [])), key=len)
            check("questions reach the classroom uncut (the longest is %d characters, never ending in …)" % len(longest),
                  len(longest) > 90 and not longest.endswith("…"), longest)
            check("work it out: the dock says what is handed in", "0.84" in look.get("calcDock", ""), look.get("calcDock"))
            check("explore: the detector is covered for the second challenge", look.get("covered") == 1, look)
            check("line it up: the dock starts the pump, and the cargo goes ashore",
                  look.get("pump") == "Start cargo pump 2" and "Port manifold" in (look.get("flow") or ""), look)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if not FAIL:
        print("\nPart A and Part B, ten interactive types and the debrief rule - built from the script, answered in a browser.")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
