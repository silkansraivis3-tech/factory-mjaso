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
      else if (x[0] === 'eval') { (new Function('out', 's', x[1]))(out, s); }
    });
  }
  /* one step at a time, so a message to the page (gb-team, gb-team-done) arrives between the taps, as in class */
  var queue = [];
  PLAN.forEach(function (p) {
    if (p[0] === 'post') { queue.push(function () { window.postMessage(p[1], '*'); }); return; }
    if (p[0] === 'eval') { queue.push(function () { (new Function('out', p[1]))(out); }); return; }
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


def drive(exe, page, plan, tmp, look=True, size=None):
    """size=(w, h): the page's viewport exactly that tablet's size, as probe() opens it"""
    text = io.open(page, encoding="utf-8").read()
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    text = text[:i] + "<script>%s</script>" % (DRIVER % (json.dumps(plan, ensure_ascii=False), "true" if look else "false")) + text[i:]
    w = os.path.join(tmp, "drive.html")
    io.open(w, "w", encoding="utf-8").write(text)
    win = ["--hide-scrollbars", "--window-size=%d,%d" % (size[0], size[1] + 95)] if size else ["--window-size=1280,800"]
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--user-data-dir=" + os.path.join(tmp, "prof"),
                        "--allow-file-access-from-files"] + win + ["--virtual-time-budget=15000", "--dump-dom", Path(w).as_uri()],
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


def language_part(exe, tmp):
    """L19: the engine's own words in the page's language - lv here (ru is the same table)"""
    print("\n-- a Latvian page")
    os.makedirs(os.path.join(tmp, "lv"))
    sc = tcm.script(screens=tcm.IN_LANGUAGE["Latvian"])
    sc["course_language"] = "Latvian"
    sc.update(approved_hash=tcm.cs.content_hash(sc))
    c, md = tcm.new_course(os.path.join(tmp, "lv"), sc, build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
    tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", [f for f in os.listdir(os.path.join(md, "tasks")) if f.startswith("sc1_")][0])
    peek = "out.dial = document.querySelector('.dial-val').textContent;"
    r = drive(exe, page, [["q01", [["tap", ".cg .opt", "-162 °C"]]],
                          ["q02", [["plus", 35]]], ["eval", peek],
                          ["q03", [["tap", ".opt", "aizvērts"], ["tap", ".opt", "darbojas"]]]], tmp, look=False)
    steps = r.get("steps", [])
    check("the buttons speak Latvian: Pārbaudīt, Tālāk, Mans rezultāts", not r.get("errors") and "q01:Pārbaudīt" in steps
          and "q01:Tālāk" in steps and "q03:Mans rezultāts" in steps, r)
    check("the dial shows the decimal comma (−42,5), and the value is graded the same", r.get("dial") == "−42,5"
          and (r.get("report") or {}).get("ok") == 3, r)


DECK_DRIVER = r"""
(function () {
  var out = {errors: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  function q(s) { return document.querySelector(s); }
  function txt(s) { var n = q(s); return n ? n.textContent.replace(/\s+/g, ' ').trim() : null; }
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        out.labels = {};
        ['btnGrid', 'btnCue', 'btnPrev', 'btnNext', 'btnFull', 'btnExit'].forEach(function (id) {
          var b = document.getElementById(id);
          out.labels[id] = b.getAttribute('aria-label') + '|' + b.getAttribute('title');
        });
        out.start = txt('#startBtn'); out.hint = txt('.landing-hint'); out.mod = txt('.landing-mod');
        out.chips = txt('.landing-meta'); out.close = txt('#ovClose'); out.ovHead = txt('#overview .ov-head');
        out.back = txt('.gbt-topback');
        document.getElementById('startBtn').click();
        document.getElementById('btnCue').click();
        out.cue = txt('#cue .tag');
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out);
      document.body.appendChild(pre);
    }, 50);
  });
}());
"""


def drive_deck(exe, page, tmp, lang=None):
    """the deck opened as the instructor does; lang= puts the same page in another <html lang>"""
    text = io.open(page, encoding="utf-8").read()
    if lang:
        text = re.sub(r'<html lang="[^"]*">', '<html lang="%s">' % lang, text, count=1)
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    text = text[:i] + "<script>%s</script>" % DECK_DRIVER + text[i:]
    w = os.path.join(tmp, "deck.html")
    io.open(w, "w", encoding="utf-8").write(text)
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--user-data-dir=" + os.path.join(tmp, "prof"),
                        "--allow-file-access-from-files", "--window-size=1280,800", "--virtual-time-budget=10000", "--dump-dom", Path(w).as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]]}


def deck_language_part(exe, tmp):
    """L19: the deck engine's own words (gb_deck.js LANG) and the landing card in the page's language - lv here"""
    print("\n-- a Latvian deck")
    os.makedirs(os.path.join(tmp, "dlv"))
    sc = tcm.script(screens=tcm.IN_LANGUAGE["Latvian"])
    sc["course_language"] = "Latvian"
    sc.update(approved_hash=tcm.cs.content_hash(sc))
    c, md = tcm.new_course(os.path.join(tmp, "dlv"), sc, build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    page = tcm.deck(md)
    check("the Latvian deck is built with no language problem, marked lang=\"lv\", no English words passed to the engine",
          code == 0 and '<html lang="lv">' in page and "GBDeck.init({ hooks:" in page and "not in the factory" not in out, out)
    r = drive_deck(exe, os.path.join(md, "presentation", "index.html"), tmp)
    lab = r.get("labels") or {}
    check("no script error on the Latvian deck", not r.get("errors"), r.get("errors"))
    check("the controls speak Latvian: Tālāk (→), Atpakaļ (←), Visi ekrāni (G), Norāde instruktoram (N), Iziet",
          lab.get("btnNext") == "Tālāk|Tālāk (→)" and lab.get("btnPrev") == "Atpakaļ|Atpakaļ (←)" and lab.get("btnGrid") == "Visi ekrāni|Visi ekrāni (G)"
          and lab.get("btnCue") == "Norāde instruktoram|Norāde instruktoram (N)" and lab.get("btnFull") == "Pilnekrāns|Pilnekrāns (F)"
          and lab.get("btnExit") == "Iziet|Iziet", lab)
    check("Start, the overview, the landing hint, the Back link and the cue's tag in Latvian",
          r.get("start") == "Sākt" and r.get("close") == "Aizvērt" and (r.get("ovHead") or "").startswith("Visi ekrāniPieskarieties ekrānam")
          and (r.get("hint") or "").startswith("→ / atstarpe – tālāk") and r.get("back") == "Atpakaļ" and r.get("cue") == "Norāde instruktoram", r)
    check("the landing card's chips in Latvian: 1. modulis, 25 min, Mācību ekrāni: 0, Paškontrole SC1, Moduļa pārbaude MC",
          (r.get("mod") or "").endswith("1. modulis") and "Mācību ekrāni: 0" in (r.get("chips") or "") and "Paškontrole SC1" in (r.get("chips") or "")
          and "Moduļa pārbaude MC" in (r.get("chips") or ""), r)
    check("no English word of the deck's own left on the Latvian landing or controls",
          not re.search(r"\b(Next|Back|Start|All screens|Instructor cue|Fullscreen|Leave|Close|teaching screens|Self-check|Module)\b",
                        json.dumps(r, ensure_ascii=False)), r)
    r = drive_deck(exe, os.path.join(md, "presentation", "index.html"), tmp, lang="en")
    check("the same deck as an English page keeps the frame's own English words",
          not r.get("errors") and (r.get("labels") or {}).get("btnNext") == "Next|Next (→)" and r.get("cue") == "Instructor cue"
          and r.get("back") == "Back", r)
    eng = io.open(os.path.join(tcm.SKILLS, "course-module-ux", "assets", "gb_deck.js"), encoding="utf-8").read()
    check("the deck engine has its words in lv and ru, chosen by <html lang>, marked PROVISIONAL",
          "Tālāk" in eng and "Далее" in eng and "PROVISIONAL" in eng and 'documentElement.getAttribute("lang")' in eng)


PROBE = r"""
(function () {
  var out = {qs: [], errors: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  var go = document.getElementById('go');
  function R(e) { var b = e.getBoundingClientRect(); return {l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height}; }
  function press(el) {
    var r = el.getBoundingClientRect(), o = {bubbles: true, button: 0, clientX: r.left + 5, clientY: r.top + 5};
    el.dispatchEvent(new MouseEvent('mousedown', o)); document.dispatchEvent(new MouseEvent('mouseup', o));
  }
  function measure(s) {
    var q = {id: s.getAttribute('data-script'), vh: innerHeight, doc: document.documentElement.scrollHeight,
             dockTop: R(document.getElementById('dock')).t, opts: [].map.call(s.querySelectorAll('.opt'), R),
             hots: [].map.call(s.querySelectorAll('.hot'), R), chips: [].map.call(s.querySelectorAll('.chip'), R)};
    var ga = s.querySelector('.ga'); if (ga) { q.ga = R(ga); }
    var k = s.querySelector('svg.taskfig[data-kit]');
    if (k) {
      q.kit = {mounted: !!k.__kit, n: k.__kit && k.__kit.n, steps: k.__kit && k.__kit.steps(), still: k.hasAttribute('data-kit-still'),
               motion: k.hasAttribute('data-motion'), want: k.getAttribute('data-kit-step'), inside: [], leaders: []};
      [].forEach.call(s.querySelectorAll('.hot[data-part]'), function (h) {
        var pr = R(k.__kit.parts[h.getAttribute('data-part')].g), hr = R(h);
        q.kit.inside.push({part: h.getAttribute('data-part'), ok: hr.l <= pr.l + 1 && hr.r >= pr.r - 1 && hr.t <= pr.t + 1 && hr.b >= pr.b - 1 && hr.w >= 55 && hr.h >= 55});
      });
      [].forEach.call(s.querySelectorAll('line[data-part]'), function (ln) {
        var pr = R(k.__kit.parts[ln.getAttribute('data-part')].g), g = R(ga), x = g.l + g.w * parseFloat(ln.getAttribute('x2')) / 100, y = g.t + g.h * parseFloat(ln.getAttribute('y2')) / 100;
        q.kit.leaders.push({part: ln.getAttribute('data-part'), ok: x >= pr.l - 2 && x <= pr.r + 2 && y >= pr.t - 2 && y <= pr.b + 2});
      });
    }
    var corner = s.querySelector('.gbz-corner'); q.corner = !!corner;
    return q;
  }
  function visible() { var z = document.querySelector('.gbz'); return !!z && !z.hidden && getComputedStyle(z).display !== 'none'; }
  function answer(s, q) {
    var hot = s.querySelector('.hot'), corner = s.querySelector('.gbz-corner');
    if (hot) {
      hot.click(); q.afterTap = {viewer: visible(), selected: /\bsel\b/.test(hot.className)};
      if (corner) { corner.click(); q.afterCorner = {viewer: visible(), text: (document.querySelector('.gbz-cap') || {}).textContent || ''};
        var x = document.querySelector('.gbz-close'); if (x) { x.click(); } q.afterClose = visible(); }
    } else if (s.querySelector('.chip')) {               /* label boxes, slots, groups: every card somewhere */
      var ch = s.querySelectorAll('.chip'), zs = s.querySelectorAll('.zone');
      for (var i = 0; i < ch.length && zs.length; i++) { press(ch[i]); zs[Math.min(i, zs.length - 1)].click(); }
    } else { [].forEach.call(s.querySelectorAll('.part.on .opt, .cg .opt, .opts .opt'), function (o, i, l) { if (!o.closest('.cg') || !o.closest('.cg').querySelector('.sel')) { o.click(); } }); }
  }
  var left = document.querySelectorAll('.scr[data-script]').length;
  function step() {
    var intro = document.getElementById('introScr') || document.getElementById('tryScr');
    if (intro && /\bon\b/.test(intro.className)) { go.disabled = false; go.click(); return setTimeout(step, 200); }
    var s = document.querySelector('.scr[data-script].on');
    if (!s || !left) { return finish(); }
    left--;
    setTimeout(function () {
      try { var q = measure(s); answer(s, q); out.qs.push(q); go.click(); go.click(); }
      catch (err) { out.errors.push(String(err && err.stack || err)); }
      setTimeout(step, 250);
    }, 450);
  }
  function finish() { var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre); }
  window.addEventListener('load', function () { setTimeout(step, 100); });
}());
"""


def probe(exe, page, tmp, size=(1280, 800)):
    """the page opened at a tablet's size, every question measured as the trainee sees it, then answered (see PROBE).
    The window is taller by the browser's own chrome so the page's viewport is exactly size (and no scrollbar)."""
    text = io.open(page, encoding="utf-8").read()
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    text = text[:i] + "<script>%s</script>" % PROBE + text[i:]
    w = os.path.join(tmp, "probe.html")
    io.open(w, "w", encoding="utf-8").write(text)
    p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--hide-scrollbars",
                        "--user-data-dir=" + os.path.join(tmp, "prof"), "--allow-file-access-from-files",
                        "--window-size=%d,%d" % (size[0], size[1] + 95), "--virtual-time-budget=20000", "--dump-dom", Path(w).as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]], "qs": []}


def figures_part(exe, tmp):
    """2.43.0 in a browser: nothing ever sits under the Check bar at 1280 x 800 and 1024 x 768; a photograph's tap is the
    answer and its corner button opens it; a figure-kit drawing is drawn still at its last step and its tappable areas
    lie on the drawn parts"""
    print("\n-- photographs and kit drawings in a browser")
    os.makedirs(os.path.join(tmp, "fg"))
    c, md = tcm.figures_course(os.path.join(tmp, "fg"))
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    check("the fixture pages are built", code == 0, out)
    sc, mc = os.path.join(md, "tasks", "sc1_look_at_the_plant.html"), os.path.join(md, "assessment", "check.html")
    for size in ((1280, 800), (1024, 768)):
        tag = "%dx%d" % size
        r = probe(exe, sc, tmp, size)
        qs = {q["id"]: q for q in r.get("qs", [])}
        check("%s: no script error, every question of the self-check shown" % tag, not r.get("errors") and len(qs) == 5, r.get("errors") or sorted(qs))
        under = ["%s: %s > %s" % (q["id"], round(max([o["b"] for o in q["opts"] + q["hots"]] or [0])), round(q["dockTop"]))
                 for q in qs.values() if max([o["b"] for o in q["opts"] + q["hots"]] or [0]) > q["dockTop"] + 0.5]
        check("%s: no choice and no tappable area is ever under the Check bar - not for a big photograph beside four choices either" % tag,
              not under, under)
        check("%s: a big square photo read beside its four choices: the page does not grow past the screen" % tag,
              qs.get("q01", {}).get("doc", 0) <= size[1] + 1 and qs.get("q03", {}).get("doc", 0) <= size[1] + 1,
              {k: qs.get(k, {}).get("doc") for k in ("q01", "q03")})
        if "q01" in qs and qs["q01"]["opts"]:
            q = qs["q01"]
            check("%s: the picture is beside the four choices, not over them, and does not shrink to nothing" % tag,
                  q["ga"]["r"] <= q["opts"][0]["l"] + 1 and q["ga"]["h"] >= 300 and all(o["l"] == q["opts"][0]["l"] for o in q["opts"]), q)
        check("%s: the second question's photograph answers on a tap and does NOT open; its corner button opens it with the credit, and it closes"
              % tag, (qs.get("q02", {}).get("afterTap") or {}).get("viewer") is False and (qs["q02"]["afterTap"]).get("selected")
              and (qs["q02"].get("afterCorner") or {}).get("viewer") is True and qs["q02"].get("afterClose") is False, qs.get("q02"))
        check("%s: the viewer shows the photograph's credit" % tag, "Own photograph" in (qs.get("q02", {}).get("afterCorner") or {}).get("text", ""),
              qs.get("q02", {}).get("afterCorner"))
        k = (qs.get("q04") or {}).get("kit") or {}
        check("%s: the kit drawing is drawn, still, at its last step (2 of 2), no longer a driven figure" % tag,
              k.get("mounted") and k.get("n") == 2 and k.get("steps") == 2 and k.get("still") and not k.get("motion"), k)
        check("%s: each tappable area covers its drawn part, at least 56 px (L42)" % tag,
              len(k.get("inside", [])) == 3 and all(x["ok"] for x in k["inside"]), k.get("inside"))
        check("%s: the kit drawing opens full screen only by its corner button" % tag, (qs.get("q04") or {}).get("corner") is True, qs.get("q04"))
    r = probe(exe, mc, tmp)
    qs = {q["id"]: q for q in r.get("qs", [])}
    check("the module check: both labelled drawings (a photograph, a kit drawing) are answered without a script error",
          not r.get("errors") and set(qs) == {"m01", "m02"}, r.get("errors") or sorted(qs))
    k = (qs.get("m02") or {}).get("kit") or {}
    check("label the kit drawing: still at step 2 (the named step), every leader line ends on its drawn part",
          k.get("n") == 2 and len(k.get("leaders", [])) == 3 and all(x["ok"] for x in k["leaders"]), k)
    check("label the photograph: opens by its corner button too", (qs.get("m01") or {}).get("corner") is True, qs.get("m01"))
    low = [q["id"] for q in qs.values() if max([o["b"] for o in q["chips"]] or [0]) > q["dockTop"] + 0.5]
    check("1280 x 800: the label chips are above the Check bar", not low, low)


# ---------------------------------------------------------------- 2.46.0: what rebuilding IGF M01-M03 found in the engine
PREP = ('<svg viewBox="0 0 640 400" role="img"><rect x="20" y="20" width="600" height="360" fill="#fff" stroke="#000"/>'
        '<g id="hs-top" data-name="Under the deckhead"><rect class="hit" x="40" y="30" width="560" height="50"/></g>'
        '<g id="hs-vent" data-name="Ventilation outlet"><rect class="hit" x="30" y="150" width="60" height="70"/></g>'
        '<g id="hs-door" data-name="Near the floor by the door"><rect class="hit" x="500" y="300" width="100" height="60"/></g></svg>')
PIPE = [("Ventilate the space", 1), ("Isolate the line", 2), ("Drain the liquid", 3), ("Purge with nitrogen", 4),
        ("Measure the atmosphere", 5), ("Issue the permit", 6), ("Open the flange", 7), ("Make the repair", 8)]
FIXES = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the room", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap every place where a fixed gas detector belongs.",
     "visual": "the room", "answer": "Under the deckhead*\nVentilation outlet*\nNear the floor by the door", "feedback": "Methane rises."},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "multi_select", "question": "Which are fuels under the IGF Code?",
     "options": ["LNG", "Coal", "CNG"], "correct": "A, C", "feedback": "Natural gas."},
    {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "scenario", "question": "A leak in the fuel preparation room.",
     "answer": "The detector alarms at 20 % LEL => Find the leak* | Silence it | Carry on\n"
               "It reaches 40 % LEL => Leave the room* | Stay and look | Open the door wide\n"
               "The gas is shut off => Report to the bridge* | Restart the pump | Go home", "feedback": "Find, leave, report."},
    {"id": "q04", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the eight steps of opening a gas line in order.",
     "answer": "\n".join(t for t, _ in PIPE), "feedback": "Make it safe first."},
    {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - Module 1",
     "text": "Module check on your tablet now.\nThree questions.\nYou see PASSED or NOT PASSED.", "minutes": 5},
    {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "label_diagram", "question": "Drag each label to its place.",
     "visual": "the GA", "answer": "Fuel tank\nTank connection space\nVent mast", "feedback": "These are the new spaces."},
    {"id": "m02", "kind": "module-check", "set": "MC", "mechanic": "panel_operate", "question": "Shut the bunkering down.",
     "visual": "the panel", "answer": "Bunker valve = closed", "feedback": "The valve closes."},
    {"id": "m03", "kind": "module-check", "set": "MC", "mechanic": "timeline", "question": "Rebuild the incident.",
     "answer": "\n".join(["The compressor tripped", "Pressure rose*", "The alarm was silenced", "Nobody reported it",
                          "The relief valve lifted", "Gas reached the deck", "The crew mustered"]), "feedback": "Stop at the pressure."},
]
RECT = "function R(e){var b=e.getBoundingClientRect();return {l:b.left,t:b.top,r:b.right,b:b.bottom,w:b.width,h:b.height};}"
BAR = "var bar = document.querySelector('.state').getBoundingClientRect().bottom;"
SC_PLAN = [
    ["q01", [["tap", ".hot", "Under the deckhead"], ["dock"], ["eval", RECT + BAR +
        "var m = [].filter.call(s.querySelectorAll('.hot'), function (h) { return /missed/.test(h.className); });"
        "var ga = s.querySelector('.ga'), why = s.querySelector('.why'), z = ga.querySelector('.gbz-corner');"
        "out.q01 = {side: s.getAttribute('data-pic'), missed: m.map(function (h) { return h.textContent + '|' + h.className; }),"
        " ga: R(ga), why: R(why), corner: z ? R(z) : null, vh: innerHeight};"]]],
    ["q02", [["tap", ".opt", "LNG"], ["dock"], ["eval",
        "var c = [].filter.call(s.querySelectorAll('.opt'), function (o) { return o.textContent.trim() === 'CNG'; })[0];"
        "out.q02 = {cls: c.className, before: getComputedStyle(c, '::before').content, tag: c.getAttribute('data-miss'),"
        " vd: s.querySelector('.vd').textContent};"]]],
    # a step taller than the screen, and a long result list - as on a 1024 x 768 tablet with long words
    ["eval", "var st = document.createElement('style'); st.textContent = '.sit{min-height:560px} .res li{min-height:160px}';"
             "document.head.appendChild(st);"],
    ["q03", [["eval", "var o = [].filter.call(s.querySelectorAll('.part')[0].querySelectorAll('.opt'), function (x) {"
                      " return x.textContent.trim() === 'Find the leak'; })[0]; out.l1 = getComputedStyle(o, '::before').content;"],
             ["tap", ".opt", "Find the leak"], ["dock"], ["dock"], ["eval", RECT + BAR +
        "var p = s.querySelectorAll('.part'), o = [].filter.call(p[0].querySelectorAll('.opt'), function (x) { return x.textContent.trim() === 'Find the leak'; })[0];"
        "out.q03 = {bar: bar, head: R(p[1].querySelector('.phead')), vh: innerHeight, l1: getComputedStyle(o, '::before').content, shown: o.getAttribute('data-l')};"],
             ["tap", ".opt", "Leave the room"], ["dock"], ["dock"], ["tap", ".opt", "Report to the bridge"]]],
    ["q04", [["eval", RECT + "var d = document.getElementById('dock').getBoundingClientRect().top;"
        "out.q04 = {low: Math.max.apply(null, [].map.call(s.querySelectorAll('.chip,.slot'), function (c) { return R(c).b; })), dock: d,"
        " doc: document.documentElement.scrollHeight, vh: innerHeight, many: s.getAttribute('data-many')};"]]
     + [["card", t, n] for t, n in PIPE]],
    ["eval", RECT + BAR + "out.res = {y: scrollY, ring: R(document.getElementById('resRing')), bar: bar};"],
]
MC_PLAN = [
    ["eval", "document.getElementById('go').click();"],
    ["m01", [["eval",                    # two labels swapped: after Check they are moved, with the arrow, into their own boxes
        "function card(t) { return [].filter.call(s.querySelectorAll('.chip'), function (c) { return c.textContent.trim() === t; })[0]; }"
        "function put(t, v) { var c = card(t), r = c.getBoundingClientRect(), o = {bubbles: true, button: 0, clientX: r.left + 5, clientY: r.top + 5};"
        " c.dispatchEvent(new MouseEvent('mousedown', o)); document.dispatchEvent(new MouseEvent('mouseup', o));"
        " s.querySelector('.lbox[data-val=\"' + v + '\"]').click(); }"
        "put('Fuel tank', 'sp-tcs'); put('Tank connection space', 'sp-tank'); put('Vent mast', 'sp-vent');"],
             ["dock"], ["eval", RECT +
        "var z = s.querySelector('.gbz-corner'); out.corner = z ? R(z) : null;"
        "out.m01 = [].map.call(s.querySelectorAll('.lbox'), function (b) { var c = b.querySelector('.chip');"
        " return {box: R(b), cls: c.className, sw: c.scrollWidth, cw: c.clientWidth, sh: c.scrollHeight, ch: c.clientHeight, t: c.textContent.trim()}; });"]]],
    ["m02", [["eval",
        "function look(s) { var v = s.querySelector('svg.csym'), f = v.querySelector('.kit-vfill');"
        " return {bg: getComputedStyle(v).backgroundColor, fill: getComputedStyle(f).fill, op: getComputedStyle(f).opacity}; }"
        "[].filter.call(s.querySelectorAll('.opt'), function (o) { return o.textContent.trim() === 'open'; })[0].click(); out.open = look(s);"],
             ["tap", ".opt", "closed"], ["eval", "var v = s.querySelector('svg.csym'), f = v.querySelector('.kit-vfill');"
        "out.closed = {bg: getComputedStyle(v).backgroundColor, fill: getComputedStyle(f).fill, op: getComputedStyle(f).opacity};"]]],
    ["m03", [["eval", RECT + "out.m03 = {low: Math.max.apply(null, [].map.call(s.querySelectorAll('.chip'), function (c) { return R(c).b; })),"
        " dock: document.getElementById('dock').getBoundingClientRect().top, many: s.getAttribute('data-many')};"]]],
]


def lum(css):
    """the luminance of an rgb() colour, 0 .. 255"""
    v = [float(x) for x in re.findall(r"[\d.]+", css or "")[:3]] or [0, 0, 0]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def fixes_part(exe, tmp):
    """2.46.0 - what rebuilding IGF M01-M03 as compiled pages found in the shared engine, each driven in the browser"""
    print("\n-- 2.46.0: the engine fixes found on IGF M01-M03")
    os.makedirs(os.path.join(tmp, "fx"))
    c, md = tcm.new_course(os.path.join(tmp, "fx"), tcm.script(screens=FIXES), build=False)
    io.open(os.path.join(md, "assets", "fig", "prep.svg"), "w", encoding="utf-8").write(PREP)
    io.open(os.path.join(md, "assets", "fig", "ga.svg"), "w", encoding="utf-8").write(tcm.GA)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "t01": {"try_tablet": False}, "q01": {"figure": "assets/fig/prep.svg"}, "m01": {"figure": "assets/fig/ga.svg"}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    check("the fixture pages are built", code in (0, 1) and os.path.isfile(os.path.join(md, "tasks", "sc1_the_room.html")), out)
    r = drive(exe, os.path.join(md, "tasks", "sc1_the_room.html"), SC_PLAN, tmp, look=False, size=(1280, 800))
    check("no script error on the self-check", not r.get("errors"), r.get("errors"))
    q = r.get("q01") or {}
    ga, why, z = q.get("ga") or {}, q.get("why") or {}, q.get("corner") or {}
    check("tap the place on a drawing that is not wide: it takes the screen's height, the explanation beside it - not half the screen empty",
          q.get("side") == "side" and ga.get("h", 0) >= 0.62 * q.get("vh", 800) and why.get("l", 0) >= ga.get("r", 9e9) - 1, q)
    check("... and its ⤢ button sits ON the drawing's corner, not out at the edge of the screen",
          z and ga["l"] <= z["l"] and z["r"] <= ga["r"] + 1 and ga["t"] <= z["t"] and z["b"] <= ga["b"] + 1, q)
    check("tap every place, one missed: the missed place is outlined green as missed, never ticked as chosen",
          len(q.get("missed", [])) == 1 and "Ventilation outlet" in q["missed"][0] and " right" not in q["missed"][0], q.get("missed"))
    q = r.get("q02") or {}
    check("choose all that are right, one missed: it says \"Also right\", its box is not ticked, the verdict says what was missed",
          "missed" in q.get("cls", "") and "right" not in q.get("cls", "").split() and q.get("tag") == "Also right"
          and "✓" not in q.get("before", "") and q.get("vd") == "Not quite – what you missed is outlined in green.", q)
    q = r.get("q03") or {}
    check("a scenario's next step: its \"Step 2 of 3\" is below the top bar, not scrolled under it",
          q.get("head") and q["head"]["t"] >= q["bar"] - 1 and q["head"]["b"] <= q["vh"], q)
    check("after Check a folded step keeps the letter its choice was shown with - not re-lettered \"A\"",
          r.get("l1") and q.get("l1") == r.get("l1") == '"%s"' % q.get("shown"),
          {"before": r.get("l1"), "after": q})
    q = r.get("q04") or {}
    check("8 rows to put in order at 1280 x 800: the places beside the cards, every card on the screen without a scroll",
          q.get("many") == "1" and q.get("low", 9e9) <= q.get("dock", 0) + 0.5 and q.get("doc", 9e9) <= q.get("vh", 0) + 1, q)
    q = r.get("res") or {}
    check("the result screen opens at the top: the score ring whole, under the top bar", q.get("y") == 0 and q.get("ring", {}).get("t", -1) >= q.get("bar", 0) - 1, q)
    rep = r.get("report") or {}
    check("graded as before: 2 of 4 (the two with a miss are wrong)", rep.get("ok") == 2 and rep.get("total") == 4, rep)

    r = drive(exe, os.path.join(md, "assessment", "check.html"), MC_PLAN, tmp, look=False, size=(1280, 800))
    check("no script error on the module check", not r.get("errors"), r.get("errors"))
    boxes = r.get("m01") or []
    cut = ["%s %s>%s / %s>%s" % (b["t"], b["sw"], b["cw"], b["sh"], b["ch"]) for b in boxes if b["sw"] > b["cw"] + 1 or b["sh"] > b["ch"] + 1]
    check("label the drawing: \"Tank connection space\" and every label fits its box with the tick or the arrow - nothing cut off",
          len(boxes) == 3 and not cut and sum("fixed" in b["cls"] for b in boxes) == 2, cut or boxes)
    over = [(x["t"], y["t"]) for i, x in enumerate(boxes) for y in boxes[i + 1:]
            if x["box"]["l"] < y["box"]["r"] and y["box"]["l"] < x["box"]["r"] and x["box"]["t"] < y["box"]["b"] and y["box"]["t"] < x["box"]["b"]]
    check("... and no two label boxes overlap", not over, over)
    z = r.get("corner") or {}
    under = [b["t"] for b in boxes if z and b["box"]["l"] < z["r"] and z["l"] < b["box"]["r"] and b["box"]["t"] < z["b"] and z["t"] < b["box"]["b"]]
    check("... and none lies under the drawing's ⤢ button (M03 q06: the arrow of a card was hidden under it)", z and not under, under or z)
    key = drive(exe, os.path.join(md, "assessment", "check_answer_key.html"), [["eval", RECT +
        "out.key = [].map.call(document.querySelectorAll('table'), function (t) { var r = t.rows;"
        " return {th: R(r[0].cells[0]), td: R(r[1].cells[0])}; });"]], tmp, look=False, size=(1280, 800))
    rows = key.get("key") or []
    check("the answer key's tables: the head row sits on its first question, not pushed down over it (gb_page.css .scroll th)",
          len(rows) == 2 and all(x["th"]["b"] <= x["td"]["t"] + 1 for x in rows), rows or key)
    o, s = r.get("open") or {}, r.get("closed") or {}
    check("operate the panel: the valve is drawn on the deck's dark screen, closed = filled and bright, open = hollow, as in the deck",
          s.get("bg") == o.get("bg") == "rgb(12, 30, 58)" and float(s.get("op", 0)) > 0.9 and float(o.get("op", 1)) < 0.1
          and lum(s.get("fill")) > lum(s.get("bg")) + 80, {"open": o, "closed": s})
    q = r.get("m03") or {}
    check("rebuild the incident with 7 events: the cards beside the places, all above the Check bar",
          q.get("many") == "part" and q.get("low", 9e9) <= q.get("dock", 0) + 0.5, q)

    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    dk = tcm.deck(md)
    icons = re.findall(r'<svg class="act-ico" data-icon="(\w+)"', dk)
    check("the deck's task slides show what the trainees will do: choose for SC1, drag for the module check - not one generic tablet",
          icons == ["choose", "drag"], icons or out)


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
        figures_part(exe, tmp)
        fixes_part(exe, tmp)
        team_part(exe, tmp)
        language_part(exe, tmp)
        deck_language_part(exe, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
