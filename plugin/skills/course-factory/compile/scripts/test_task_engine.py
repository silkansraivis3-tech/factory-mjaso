# -*- coding: utf-8 -*-
"""test_task_engine - a compiled task page answered in a real (hidden) browser, through the one shared engine.

    python test_task_engine.py

The page of test_compile_module's EVERY_WAY fixture (the ten ways of answering added in 2.38.0) is opened in headless
Chrome or Edge with a driver added at its end. The driver answers the way a trainee does - taps on the words shown,
tap-then-tap for the cards, the dial's + button, Check / Go on / Next on the dock - and reads the result the page
reports to the classroom (gb-task-done). Pinned:
  * everything answered right gives 10 of 10, and every part of a two-part question needs its own Check;
  * five answered wrong give 5 of 10, and each shows what was right: the gap's right words (amber), the dial's band
    of right values, a card that does not belong back in the bank and the one that does in its slot;
  * the panel's little figure-kit valve follows the position chosen.
Skipped (not failed) when no Chrome or Edge is found - the same rule as the drawing check.
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
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import drawing_check  # noqa: E402
import test_compile_module as tcm  # noqa: E402

PASS, FAIL = [], []

DRIVER = r"""
(function () {
  var PLAN = %s, LOOK = %s, out = {steps: [], report: null, reports: 0, errors: []};
  window.addEventListener('message', function (e) { if (e.data && e.data.type === 'gb-task-done') { out.report = e.data; out.reports++; } });
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  function sec(id) { return document.querySelector('.scr[data-script="' + id + '"]'); }
  function byText(root, sel, t) {
    var l = root.querySelectorAll(sel), i;
    for (i = 0; i < l.length; i++) { if (l[i].textContent.replace(/\s+/g, ' ').trim() === t) { return l[i]; } }
    throw new Error('no "' + t + '" in ' + sel);
  }
  function press(el) {                     /* a tap on a card: the engine's tap-then-tap path */
    var r = el.getBoundingClientRect(), o = {bubbles: true, button: 0, clientX: r.left + 5, clientY: r.top + 5};
    el.dispatchEvent(new MouseEvent('mousedown', o));
    document.dispatchEvent(new MouseEvent('mouseup', o));
  }
  var go = document.getElementById('go');
  function dock() { var t = go.textContent; go.click(); return t; }
  function answer(q, a) {
    var s = sec(q);
    a.forEach(function (x) {
      if (x[0] === 'tap') { byText(s, x[1], x[2]).click(); }
      else if (x[0] === 'card') { press(byText(s, '.chip', x[1])); s.querySelectorAll('.zone')[x[2] - 1].click(); }
      else if (x[0] === 'stop') { press(byText(s, '.chip', x[1])); }
      else if (x[0] === 'plus') { for (var i = 0; i < x[1]; i++) { s.querySelector('.dial-plus').click(); } }
      else if (x[0] === 'look') { byText(s, '.ff-part', x[1]).parentNode.click(); }
      else if (x[0] === 'fault') { byText(s, '.ff-part', x[1]).parentNode.parentNode.querySelector('.ff-pick').click(); }
      else if (x[0] === 'dock') { out.steps.push(q + ':' + dock()); }
    });
  }
  /* one step at a time, so a message to the page (gb-team, gb-team-done) arrives between the taps, as in class */
  var queue = [];
  PLAN.forEach(function (p) {
    if (p[0] === 'post') { queue.push(function () { window.postMessage(p[1], '*'); }); return; }
    if (p[0] === 'eval') { queue.push(function () { (new Function(p[1]))(); }); return; }
    queue.push(function () { answer(p[0], p[1]); });
    queue.push(function () { out.steps.push(p[0] + ':' + dock()); });     /* Check */
    queue.push(function () { out.steps.push(p[0] + ':' + dock()); });     /* Next, or See my score */
  });
  function run() {
    var f = queue.shift();
    if (f) {
      try { f(); } catch (err) { out.errors.push(String(err && err.stack || err)); }
      setTimeout(run, 30);
      return;
    }
    if (LOOK) { look(); }
    var bar = document.getElementById('teamBar');
    if (bar) { out.team = {hidden: bar.hasAttribute('hidden'), text: bar.textContent.replace(/\s+/g, ' ').trim(), go: document.getElementById('dock').className}; }
    finish();
  }
  function look() {
    try {
      var look = {};
      look.gap2 = sec('q01').querySelectorAll('.gap')[1].className + '|' + sec('q01').querySelectorAll('.gap')[1].textContent;
      look.dial = sec('q04').querySelector('.dial').className + '|' + sec('q04').querySelector('.dial-band').style.width;
      look.cargo = byText(sec('q07'), '.chip', 'Start loading cargo').className + '|' + byText(sec('q07'), '.chip', 'Start loading cargo').parentNode.className;
      look.permit = byText(sec('q07'), '.chip', 'Issue the entry permit').className + '|' + byText(sec('q07'), '.chip', 'Issue the entry permit').parentNode.getAttribute('data-val');
      var v = sec('q10').querySelector('svg.csym g.kit-shut');
      look.valveShut = !!v;
      look.stopat = sec('q08').querySelectorAll('.chip.stopat').length;
      out.look = look;
    } catch (err) { out.errors.push(String(err && err.stack || err)); }
  }
  function finish() {
    setTimeout(function () {                               /* postMessage arrives as a task of its own */
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out);
      document.body.appendChild(pre);
    }, 300);
  }
  window.addEventListener('load', function () { setTimeout(run, 50); });
}());
"""

RIGHT = [
    ["q01", [["tap", ".cg .opt", "-162 °C"], ["tap", ".cg .opt", "insulated"]]],
    ["q02", [["tap", ".opt", "Send the gas to the gas combustion unit"], ["tap", ".opt", "It burns the gas safely without venting"]]],
    ["q03", [["tap", ".opt", "find the leak"], ["dock"], ["dock"], ["tap", ".opt", "the gas is shut off"]]],
    ["q04", [["plus", 9]]],
    ["q05", [["look", "Condenser"], ["fault", "Condenser"]]],
    ["q06", [["tap", ".opt", "Oxygen: 18.5 %"], ["tap", ".opt", "Rescue team: not assigned"]]],
    ["q07", [["card", "Ventilate the tank", 1], ["card", "Measure the atmosphere", 2], ["card", "Issue the entry permit", 3]]],
    ["q08", [["card", "The compressor tripped at 02:10", 1], ["card", "Tank pressure rose past the alarm set point", 2],
             ["card", "The alarm was silenced and not reported", 3], ["card", "The relief valve lifted at 04:30", 4],
             ["dock"], ["dock"], ["stop", "Tank pressure rose past the alarm set point"]]],
    ["q09", [["tap", ".opt", "Plan B"]]],
    ["q10", [["tap", ".opt", "closed"], ["tap", ".opt", "running"],
             ["tap", '[data-val="Bunker valve"] .opt', "open"], ["tap", ".opt", "Auto"]]],
]
WRONG = json.loads(json.dumps(RIGHT))
WRONG[0][1][1] = ["tap", ".cg .opt", "painted"]                                   # q01 the second gap
WRONG[2][1][0] = ["tap", ".opt", "silence it and carry on"]                        # q03 step 1
WRONG[3][1][0] = ["plus", 5]                                                       # q04 -50 °C
WRONG[6][1][2] = ["card", "Start loading cargo", 3]                                # q07 a card that does not belong
WRONG[8][1][0] = ["tap", ".opt", "Plan A"]                                         # q09


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def drive(exe, page, plan, tmp, look=True):
    text = io.open(page, encoding="utf-8").read()
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    text = text[:i] + "<script>%s</script>" % (DRIVER % (json.dumps(plan, ensure_ascii=False), "true" if look else "false")) + text[i:]
    w = os.path.join(tmp, "drive.html")
    io.open(w, "w", encoding="utf-8").write(text)
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--user-data-dir=" + os.path.join(tmp, "prof"),
                        "--allow-file-access-from-files", "--window-size=1280,800", "--virtual-time-budget=15000", "--dump-dom", Path(w).as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]]}


TEAM_A = {"type": "gb-team", "team": {"name": "Team A", "colour": "#4fd1c5", "members": ["Olena", "Juris", "Anna"],
                                      "me": "Juris", "role": "Recorder"}}
TT = [["p01", [["card", "Safety meeting", 1], ["card", "Connect the hose", 2], ["card", "Transfer", 3], ["card", "Disconnect", 4]]],
      ["p02", [["tap", ".opt", "Either side, at once"]]]]


def team_part(exe, tmp):
    """classroom-system.json team_task, in the browser: the team shown, one answer per team, no team = alone"""
    print("\n-- a team task")
    os.makedirs(os.path.join(tmp, "t"))
    c, md = tcm.new_course(os.path.join(tmp, "t"), tcm.script(screens=tcm.TEAMWORK))
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    tt1, tt2 = os.path.join(md, "tasks", "tt1_plan_the_bunkering.html"), os.path.join(md, "tasks", "tt2_check_each_other.html")
    r = drive(exe, tt1, TT, tmp, look=False)
    rep = r.get("report") or {}
    check("no team from the classroom: it runs as an individual task - nothing hidden, no scope",
          not r.get("errors") and rep.get("ok") == 2 and "scope" not in rep and (r.get("team") or {}).get("hidden") is True, r)
    r = drive(exe, tt1, [["post", TEAM_A]] + TT, tmp, look=False)
    rep, bar = r.get("report") or {}, (r.get("team") or {}).get("text", "")
    check("the team arrives: its name and the trainee's role at the top", "Team A" in bar and "You are the Recorder" in bar
          and "One answer for the whole team" in bar, r.get("team"))
    check("scope team: the one answer is handed in with scope 'team', the team and who handed in",
          rep.get("scope") == "team" and rep.get("team") == "Team A" and rep.get("by") == "Juris" and rep.get("ok") == 2, rep)
    r = drive(exe, tt1, [["post", TEAM_A], ["post", {"type": "gb-team-done", "by": "Olena", "team": "Team A"}]] + TT, tmp, look=False)
    check("handed in from another tablet: this one says who did, locks, and sends nothing",
          r.get("reports") == 0 and "Handed in by Olena for Team A" in (r.get("team") or {}).get("text", "")
          and "off" in (r.get("team") or {}).get("go", ""), r)
    r = drive(exe, tt2, [["post", dict(TEAM_A, team=dict(TEAM_A["team"], role=None))], ["p03", [["tap", ".opt", "Fuel preparation room"]]]],
              tmp, look=False)
    rep, bar = r.get("report") or {}, (r.get("team") or {}).get("text", "")
    check("scope member, no roles: everyone reports as usual; the team is still shown, no role is invented",
          rep.get("ok") == 1 and "scope" not in rep and "Team A" in bar and "You are" not in bar, r)


def main():
    exe = drawing_check.find_browser()
    if not exe:
        print("  skip  no Chrome or Edge found - the engine was not driven")
        return 0
    tmp = tempfile.mkdtemp(prefix="engine_")
    try:
        os.makedirs(os.path.join(tmp, "c"))
        c, md = tcm.new_course(os.path.join(tmp, "c"), tcm.script(screens=tcm.EVERY_WAY), build=False)
        tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
        page = os.path.join(md, "tasks", "sc1_every_way.html")
        check("the fixture page is built", code == 0 and os.path.isfile(page), out)
        print("\n-- every question answered right")
        # found by the walkthrough on the IGF pilot: a drawing's own element with a class and data-for in the question
        # made the engine write .className on an SVG node and stop - the drawing is never the engine's to touch
        svg = ("var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg'), g = document.createElementNS(s.namespaceURI, 'g');"
               "g.setAttribute('data-for', 't-a'); g.setAttribute('class', 'sel'); s.appendChild(g);"
               "document.querySelector('.scr[data-script=\"q09\"]').appendChild(s);")
        r = drive(exe, page, [["eval", svg]] + RIGHT, tmp)
        check("no script error on the page - also with a drawing's own data-for and classes in a question", not r.get("errors"), r.get("errors"))
        rep = r.get("report") or {}
        check("the classroom hears 10 of 10, every question answered, no time-out",
              rep.get("ok") == 10 and rep.get("total") == 10 and rep.get("answered") == 10 and rep.get("timeout") is False, rep)
        steps = r.get("steps", [])
        check("a scenario's step and the incident's order each have their own Check, then Go on",
              "q03:Check" in steps and "q03:Go on" in steps and "q08:Go on" in steps and steps.count("q03:Check") == 2, steps)
        check("the panel's figure-kit valve shows closed when 'closed' is chosen", (r.get("look") or {}).get("valveShut") is True, r.get("look"))
        check("the stop point is marked on its card", (r.get("look") or {}).get("stopat") == 1, r.get("look"))
        print("\n-- five answered wrong")
        r = drive(exe, page, WRONG, tmp)
        rep, look = r.get("report") or {}, r.get("look") or {}
        check("no script error on the page", not r.get("errors"), r.get("errors"))
        check("the classroom hears 5 of 10, the wrong ones marked in its items",
              rep.get("ok") == 5 and [x["ok"] for x in rep.get("items", [])] == [False, True, False, False, True, True, False, True, False, True], rep)
        check("a wrong gap shows the right words, in amber", look.get("gap2", "").endswith("|insulated") and "fixed" in look.get("gap2", ""), look)
        check("a wrong value shows the band of right values", "wrong" in look.get("dial", "") and not look.get("dial", "").endswith("|"), look)
        check("a card that does not belong goes back to the bank; the one that belongs is put in its slot",
              "fixed" in look.get("cargo", "") and look.get("cargo", "").endswith("|tray") and look.get("permit", "").endswith("|3"), look)
        team_part(exe, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
