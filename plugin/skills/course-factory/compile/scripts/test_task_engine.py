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
import browser_slots  # noqa: E402  - on the path drawing_check put it on; one pool of hidden browsers (2.57.0)

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
    if (!p[2]) { queue.push(function () { out.steps.push(p[0] + ':' + dock()); }); }    /* Next, or See my score; a blind final has none */
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


def drive(exe, page, plan, tmp, look=True, size=None, blind=False):
    """size=(w, h): the page's viewport exactly that tablet's size, as probe() opens it; blind: the page as a final's"""
    text = io.open(page, encoding="utf-8").read()
    if blind:
        text = text.replace("<body ", '<body data-blind="1" ', 1)
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    text = text[:i] + "<script>%s</script>" % (DRIVER % (json.dumps(plan, ensure_ascii=False), "true" if look else "false")) + text[i:]
    w = os.path.join(tmp, "drive.html")
    io.open(w, "w", encoding="utf-8").write(text)
    win = ["--hide-scrollbars", "--window-size=%d,%d" % (size[0], size[1] + 95)] if size else ["--window-size=1280,800"]
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--user-data-dir=" + os.path.join(tmp, "prof"),
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
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--user-data-dir=" + os.path.join(tmp, "prof"),
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
    check("the landing card's module in Latvian (1. modulis) - and no stats chips (2.63.0, the instructors' review)",
          (r.get("mod") or "").endswith("1. modulis") and not r.get("chips"), r)
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
               motion: k.hasAttribute('data-motion'), want: k.getAttribute('data-kit-step'), inside: [], leaders: [], boxes: {}, hots: {}};
      Object.keys(k.__kit.parts).forEach(function (id) { q.kit.boxes[id] = R(k.__kit.parts[id].g); });
      /* a named place inside a part ("G.funnel", 2.52.0): its own shape */
      function shape(pid) { var d = pid.indexOf('.'), g = k.__kit.parts[d > 0 ? pid.slice(0, d) : pid].g;
                            return d > 0 ? g.querySelector('[data-kit-place="' + pid.slice(d + 1) + '"]') : g; }
      [].forEach.call(s.querySelectorAll('.hot[data-part]'), function (h) {
        var pr = R(shape(h.getAttribute('data-part'))), hr = R(h);
        if (h.getAttribute('data-part').indexOf('.') > 0) { q.kit.boxes[h.getAttribute('data-part')] = pr; }
        q.kit.hots[h.getAttribute('data-part')] = hr;
        q.kit.inside.push({part: h.getAttribute('data-part'), ok: hr.l <= pr.l + 1 && hr.r >= pr.r - 1 && hr.t <= pr.t + 1 && hr.b >= pr.b - 1 && hr.w >= 55 && hr.h >= 55});
      });
      [].forEach.call(s.querySelectorAll('line[data-part]'), function (ln) {
        var pr = R(shape(ln.getAttribute('data-part'))), g = R(ga), x = g.l + g.w * parseFloat(ln.getAttribute('x2')) / 100, y = g.t + g.h * parseFloat(ln.getAttribute('y2')) / 100;
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
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--hide-scrollbars",
                        "--user-data-dir=" + os.path.join(tmp, "prof"), "--allow-file-access-from-files",
                        "--window-size=%d,%d" % (size[0], size[1] + 95), "--virtual-time-budget=20000", "--dump-dom", Path(w).as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]], "qs": []}


VENT_KIT = {"size": [400, 240], "label": "A fuel tank, a pump and the vent mast", "parts": [
    {"id": "tk", "type": "tank", "x": 30, "y": 150, "w": 160, "h": 70, "label": "Fuel tank", "value": 0.5},
    {"id": "pp", "type": "pump", "x": 250, "y": 185, "r": 24, "label": "Pump", "value": 0},
    {"id": "vp", "type": "pipe", "fluid": "gas", "d": "M330 210 V40", "value": 0},
    {"id": "vm", "type": "vent", "x": 330, "y": 40, "label": "Vent mast"}]}
FIGURE_TASKS_VENT = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the vent mast", "text": "Self-check on your tablet now.", "minutes": 2},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the vent mast.", "visual": "the vent mast",
     "answer": "Vent mast*\nFuel tank\nPump", "feedback": "The tall pipe with the outlet on top."}]
VENT_BUILD = {"module": 1, "screens": {"t01": {"try_tablet": False},
              "q01": {"figure": "vent.kit.json", "unlabel": "answers", "areas": {"Vent mast": "vm", "Fuel tank": "tk", "Pump": "pp"}}}}
# 2.52.0 (IGF M01 q03, 5 of 5 benchmark builds hand-built a % box for it) - a ga's funnel is a place a question can name
FUNNEL_KIT = {"size": [640, 300], "label": "An LNG-fuelled ship, side view", "parts": [
    {"id": "G", "type": "ga", "x": 30, "y": 140, "w": 580, "h": 110, "house": {"x": 440, "w": 110, "h": 60},
     "funnel": {"x": 470, "w": 30, "h": 40}, "label": "LNG-fuelled ship"},
    {"id": "ft", "type": "tank", "x": 80, "y": 160, "w": 150, "h": 60, "label": "Fuel tank", "value": 0.6}]}
FUNNEL_TASKS = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the funnel", "text": "Self-check on your tablet now.", "minutes": 2},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the funnel.", "visual": "the ship",
     "answer": "Funnel*\nFuel tank", "feedback": "The exhaust goes up the funnel."}]
FUNNEL_BUILD = {"module": 1, "screens": {"t01": {"try_tablet": False},
                "q01": {"figure": "ship.kit.json", "areas": {"Funnel": "G.funnel", "Fuel tank": "ft"}}}}


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

    # 2.49.7 (IGF M01 q03) - a vent on top of a pipe's upright run is a vent mast: its tap area is the whole mast, not the cap
    os.makedirs(os.path.join(tmp, "vent"))
    c, md = tcm.figures_course(os.path.join(tmp, "vent"), build=VENT_BUILD, screens=FIGURE_TASKS_VENT)
    io.open(os.path.join(c, "working_claude", "figures", "M01", "vent.kit.json"), "w", encoding="utf-8").write(json.dumps(VENT_KIT))
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    check("a hotspot on a kit vent mast, named by its part id, builds clean - no box in %", code == 0, out)
    pages = [os.path.join(md, "tasks", x) for x in os.listdir(os.path.join(md, "tasks")) if x.startswith("sc1_")]
    r = probe(exe, pages[0], tmp) if pages else {}
    k = ({q["id"]: q for q in r.get("qs", [])}.get("q01") or {}).get("kit") or {}
    hot, mast = (k.get("hots") or {}).get("vm"), (k.get("boxes") or {}).get("vp")
    check("the vent mast's tap area covers its whole mast - the pipe run under the outlet, not the cap alone",
          bool(hot and mast) and hot["t"] <= mast["t"] + 1 and hot["b"] >= mast["b"] - 1 and hot["l"] <= mast["l"] + 1 and hot["r"] >= mast["r"] - 1,
          {"hot": hot, "mast": mast, "errors": r.get("errors")})

    # 2.52.0 (IGF M01 q03) - "areas": {"Funnel": "G.funnel"}: a named place inside a ga, no box in % by hand
    os.makedirs(os.path.join(tmp, "funnel"))
    c, md = tcm.figures_course(os.path.join(tmp, "funnel"), build=FUNNEL_BUILD, screens=FUNNEL_TASKS)
    io.open(os.path.join(c, "working_claude", "figures", "M01", "ship.kit.json"), "w", encoding="utf-8").write(json.dumps(FUNNEL_KIT))
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    check("a hotspot on a ga's funnel, named \"G.funnel\", builds clean - no box in %", code == 0, out)
    pages = [os.path.join(md, "tasks", x) for x in os.listdir(os.path.join(md, "tasks")) if x.startswith("sc1_")]
    r = probe(exe, pages[0], tmp) if pages else {}
    k = ({q["id"]: q for q in r.get("qs", [])}.get("q01") or {}).get("kit") or {}
    hot, fun, ship = (k.get("hots") or {}).get("G.funnel"), (k.get("boxes") or {}).get("G.funnel"), (k.get("boxes") or {}).get("G")
    check("the funnel's tap area lies on the funnel drawn (at least 56 px), not on the whole ship",
          bool(hot and fun and ship) and hot["l"] <= fun["l"] + 1 and hot["r"] >= fun["r"] - 1 and hot["t"] <= fun["t"] + 1
          and hot["b"] >= fun["b"] - 1 and hot["w"] >= 55 and hot["w"] < ship["w"] / 2 and not r.get("errors"),
          {"hot": hot, "funnel": fun, "errors": r.get("errors")})


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
     + [["card", t, n] for t, n in PIPE]
     + [["eval", RECT +            # the verdict as it is after Check: it is laid out when it shows, so show it
         "var w = s.querySelector('.why'); w.className += ' on';"
         "out.q04w = {why: R(w), rows: R(s.querySelector('.rows')), tray: R(s.querySelector('.tray'))};"]]],
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
        " return {bg: getComputedStyle(v).backgroundColor, fill: getComputedStyle(f).fill, op: getComputedStyle(f).opacity,"
        " plate: getComputedStyle(v.querySelector('.kit-valve-bg')).fill}; }"
        "[].filter.call(s.querySelectorAll('.opt'), function (o) { return o.textContent.trim() === 'open'; })[0].click(); out.open = look(s);"],
             ["tap", ".opt", "closed"], ["eval", "var v = s.querySelector('svg.csym'), f = v.querySelector('.kit-vfill');"
        "out.closed = {bg: getComputedStyle(v).backgroundColor, fill: getComputedStyle(f).fill, op: getComputedStyle(f).opacity,"
        " plate: getComputedStyle(v.querySelector('.kit-valve-bg')).fill};"]]],
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
    qw = r.get("q04w") or {}
    w_, ro, tr = qw.get("why") or {}, qw.get("rows") or {}, qw.get("tray") or {}
    check("F21 (2.49.2): the verdict box of a long order runs the full width under the places and the cards - never in the narrow column",
          w_ and ro and tr and w_["l"] <= ro["l"] + 1 and w_["r"] >= tr["r"] - 1 and w_["t"] >= max(ro["b"], tr["b"]) - 1, qw)
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
    # 2.52.0 (L63): the valve is a real valve whose ISA bow-tie is a light plate on its cast body - closed, the bow-tie is
    # filled in the plate's dark ink, so "closed" reads against the plate, not against the screen
    check("operate the panel: the valve is drawn on the deck's dark screen, closed = filled (dark on its light plate), open = hollow, as in the deck",
          s.get("bg") == o.get("bg") == "rgb(12, 30, 58)" and float(s.get("op", 0)) > 0.9 and float(o.get("op", 1)) < 0.1
          and lum(s.get("plate")) > lum(s.get("fill")) + 80, {"open": o, "closed": s})
    q = r.get("m03") or {}
    check("rebuild the incident with 7 events: the cards beside the places, all above the Check bar",
          q.get("many") == "part" and q.get("low", 9e9) <= q.get("dock", 0) + 0.5, q)

    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    dk = tcm.deck(md)
    icons = re.findall(r'<svg class="act-ico" data-icon="(\w+)"', dk)
    check("the deck's task slides show what the trainees will do: choose for SC1, drag for the module check - not one generic tablet",
          icons == ["choose", "drag"], icons or out)


def picture_part(exe, tmp):
    """2.49.1 - IGF M06: a photo over a sort left its drop zones under the Check bar; the right state on a dark drawing
    was near-black with a tiny tick"""
    print("\n-- 2.49.1: a picture over a sort, the right state on a dark drawing")
    screens = [
        {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the picture", "text": "Self-check on your tablet now.", "minutes": 4},
        {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "categorise", "question": "Sort each precaution under the hazard it protects against.",
         "answer": "Pressure surge: close manual valves slowly; open the next tank's valve before closing the last\n"
                   "Trapped liquid: a small relief valve on each section between valves; drain lines after use\n"
                   "Cold burns: a face shield over goggles; trousers worn over the boots", "feedback": "x"},
        {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the master valve.", "visual": "the plant",
         "answer": "Master valve*\nFuel tank\nPump", "feedback": "Between the tank and the pump."}]
    os.makedirs(os.path.join(tmp, "pic"))
    c, md = tcm.new_course(os.path.join(tmp, "pic"), tcm.script(screens=screens), build=False)
    io.open(os.path.join(md, "assets", "img", "gloves.png"), "wb").write(tcm.png(1000, 740))
    tcm.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), {"gloves.png": {"source": "Own photograph, Novikontas", "licence": "own work",
        "attribution_required": False, "description": "Thick blue gloves."}})
    io.open(os.path.join(c, "working_claude", "figures", "M01", "plant.kit.json"), "w", encoding="utf-8").write(json.dumps(tcm.PLANT_KIT))
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "t01": {"try_tablet": False}, "q01": {"figure": "assets/img/gloves.png"},
        "q02": {"figure": "plant.kit.json", "unlabel": "answers", "areas": {"Master valve": "mv", "Fuel tank": "tk", "Pump": "pp"}}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_the_picture.html")
    check("the fixture page is built", code == 0 and os.path.isfile(page), out)
    r = drive(exe, page, [["eval", RECT + "document.getElementById('go').click(); var s = document.querySelector('.scr.on');"
        " out.cat = {pic: s.getAttribute('data-pic'), vh: innerHeight, dock: R(document.getElementById('go').parentNode),"
        " zones: [].map.call(s.querySelectorAll('.zone'), R), img: R(s.querySelector('.instrument'))};"]], tmp, look=False, size=(1280, 800))
    cat = r.get("cat") or {}
    check("no script error", not r.get("errors"), r.get("errors"))
    check("a photo over a sort: it sits beside the cards, and every drop zone is above the Check bar at 1280 x 800",
          cat.get("pic") == "beside" and len(cat.get("zones", [])) == 3 and max(z["b"] for z in cat["zones"]) <= cat["dock"]["t"] + 0.5
          and cat["img"]["b"] <= cat["dock"]["t"], cat)
    r = drive(exe, page, [["eval",
        "var s = document.querySelector('.scr[data-script=\"q02\"]'); s.className += ' on';"
        " var h = [].filter.call(s.querySelectorAll('.hot'), function (x) { return x.textContent.trim() === 'Master valve'; })[0];"
        " h.className += ' sel right'; var cs = getComputedStyle(h), af = getComputedStyle(h, '::after');"
        " out.hot = {blend: cs.mixBlendMode, border: cs.borderTopColor, bg: cs.backgroundColor, tick: af.width, tickbg: af.backgroundColor,"
        " dark: !!h.closest('.ga.kitfig')};"]], tmp, look=False, size=(1280, 800))
    hot = r.get("hot") or {}
    check("the right area on a dark drawing: a plain light-green wash (not multiply: near-black), a clear light-green border, a 34 px tick",
          hot.get("dark") and hot.get("blend") == "normal" and hot.get("border") == "rgb(79, 214, 160)" and hot.get("tick") == "34px"
          and hot.get("tickbg") == "rgb(79, 214, 160)" and lum(hot.get("bg")) > 40, hot)


ZOOM_CORNER_KIT = {"size": [640, 300], "label": "The spaces", "parts": [
    {"id": "VM", "type": "space", "x": 520, "y": 8, "w": 112, "h": 96, "label": "Vent mast"},
    {"id": "FT", "type": "space", "x": 20, "y": 150, "w": 200, "h": 120, "label": "Fuel tank"},
    {"id": "ER", "type": "space", "x": 260, "y": 150, "w": 160, "h": 120, "label": "Engine room"}]}


def corner_part(exe, tmp):
    """2.63.2 (Aleksis, 2026-10-22; the 2.63.2 rebuild's M01 q03 / M08 m01 and the IGF original course's M03 SC2 q6, M04
    check q2, M09 check q2) - the photo viewer's ⤢ button never sits on an answer picture's tap area or label: the right
    area here is in its old corner (top right)"""
    print("\n-- 2.63.2: the ⤢ button keeps off an answer picture's tap areas and labels")
    screens = [{"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the corner", "text": "Self-check on your tablet now.", "minutes": 4},
               {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the vent mast.", "visual": "the ship",
                "answer": "Vent mast*\nFuel tank\nEngine room", "feedback": "High above the deck."}]
    os.makedirs(os.path.join(tmp, "corner"))
    c, md = tcm.new_course(os.path.join(tmp, "corner"), tcm.script(screens=screens), build=False)
    io.open(os.path.join(c, "working_claude", "figures", "M01", "zoomcorner.kit.json"), "w", encoding="utf-8").write(json.dumps(ZOOM_CORNER_KIT))
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "t01": {"try_tablet": False}, "q01": {"figure": "zoomcorner.kit.json", "areas": {"Vent mast": "VM", "Fuel tank": "FT", "Engine room": "ER"}}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_the_corner.html")
    check("the corner fixture page is built", code == 0 and os.path.isfile(page), out[-400:])
    look = (RECT + "document.getElementById('go').click();"
            " var s = document.querySelector('.scr.on'), b = s && s.querySelector('.gbz-corner');"
            " function hit(a, c) { return a.l < c.r - 0.5 && a.r > c.l + 0.5 && a.t < c.b - 0.5 && a.b > c.t + 0.5; }"
            " var things = [].slice.call(s.querySelectorAll('.hot, .zone, .lbox, svg text')).map(R).filter(function (x) { return x.r > x.l; });"
            " out.corner = b ? {btn: R(b), over: things.filter(function (x) { return hit(R(b), x); }).length, n: things.length} : null;")
    for size in ((1280, 800), (1024, 768)):
        r = drive(exe, page, [["eval", look]], tmp, look=False, size=size)
        cr = r.get("corner") or {}
        check("%dx%d: the ⤢ button covers no tap area and no word of the answer picture (%s things measured)" % (size[0], size[1], cr.get("n")),
              not r.get("errors") and cr and cr.get("n") and cr.get("over") == 0, (r.get("errors"), cr))


STEPS = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the steps", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "scenario", "question": "Three situations. In each one, choose what happens or what is done.",
     "answer": "At sea the engine runs in gas mode and the gas supply trips => The engine keeps burning the gas left in the pipe | "
               "The engine changes over to fuel-oil mode and keeps running* | The engine stops and the ship loses power\n"
               "Before any fuel flows from the bunker truck => The ship's and the supplier's persons in charge agree the procedure in writing and sign the safety checklist* | "
               "The supplier decides alone how the transfer runs | The crew starts the transfer and signs the checklist afterwards\n"
               "A ship with a gas-only engine loses its gas supply => The engine changes over to fuel-oil mode | The engine stops - it cannot switch to oil* | "
               "The engine keeps running on the gas in the tank",
     "feedback": "A dual-fuel engine changes over to oil and keeps running; a gas-only engine cannot, so it stops. Before any fuel flows, the persons in charge "
                 "agree the procedure in writing and sign the checklist."}]
STEP_OPT = [("The engine keeps burning the gas left in the pipe", "The engine changes over to fuel-oil mode and keeps running"),
            ("The supplier decides alone how the transfer runs", "The ship's and the supplier's persons in charge agree the procedure in writing and sign the safety checklist"),
            ("The engine changes over to fuel-oil mode", "The engine stops - it cannot switch to oil")]
STEP_MEASURE = (RECT + BAR + "var p = [].slice.call(s.querySelectorAll('.part')), w = s.querySelector('.why'), d = document.getElementById('dock').getBoundingClientRect().top;"
                "out.steps3 = {vh: innerHeight, bar: bar, dock: d, why: R(w), whyOn: /\\bon\\b/.test(w.className), vd: s.querySelector('.vd').textContent,"
                " heads: p.map(function (x) { return R(x.querySelector('.phead')); }), parts: p.map(function (x) { return R(x); }),"
                " past: p.map(function (x) { return /\\bpast\\b/.test(x.className); }),"
                " last: R([].filter.call(p[2].querySelectorAll('.opt.right'), function (x) { return true; })[0])};")


def steps_part(exe, tmp):
    """2.50.1 - IGF M01 m02: after the last Check of a 3-step scenario the verdict and the part in hand were below the frame and
    \"Step 2 of 3\" under the top bar. The earlier steps fold to a summary; the verdict, the last step's right answer and
    every step's label are on the screen together, at 1280 x 800 and 1024 x 768, whichever way the steps were answered."""
    print("\n-- 2.50.1: a 3-step scenario after its last Check")
    os.makedirs(os.path.join(tmp, "st"))
    c, md = tcm.new_course(os.path.join(tmp, "st"), tcm.script(screens=STEPS), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_the_steps.html")
    check("the 3-step fixture page is built", code == 0 and os.path.isfile(page), out)
    for size in ((1280, 800), (1024, 768)):
        for how, pick in (("right", 1), ("wrong", 0)):
            plan = [["eval", "document.getElementById('go').click();"],
                    ["q01", [["tap", ".opt", STEP_OPT[0][pick]], ["dock"], ["dock"], ["tap", ".opt", STEP_OPT[1][1]], ["dock"], ["dock"],
                             ["tap", ".opt", STEP_OPT[2][1]], ["dock"], ["eval", STEP_MEASURE]]]]
            r = drive(exe, page, plan, tmp, look=False, size=size)
            q = r.get("steps3") or {}
            tag = "%dx%d, step 1 answered %s" % (size[0], size[1], how)
            check("no script error (%s)" % tag, not r.get("errors"), r.get("errors"))
            ok = bool(q.get("whyOn")) and q.get("why", {}).get("t", -1) >= q.get("bar", 9e9) and q["why"]["b"] <= q["dock"] + 0.5 and q["last"]["b"] <= q["why"]["t"] + 0.5
            check("%s: the verdict (%s) and the last step's right answer are on the screen above the Check bar" % (tag, q.get("vd")), ok, q)
            heads = q.get("heads") or []
            check("%s: every step's label is below the top bar and none is above the frame" % tag,
                  len(heads) == 3 and all(h["t"] >= q["bar"] - 1 and h["b"] <= q["dock"] for h in heads), q)
            check("%s: the two finished steps are folded, and a folded step is shorter than the step in hand" % tag,
                  q.get("past") == [True, True, False] and all((p["b"] - p["t"]) < 0.5 * (q["parts"][2]["b"] - q["parts"][2]["t"]) for p in q["parts"][:2]), q)


DECK_FIT = r"""
(function () {
  var out = {errors: [], credits: [], recaps: [], insets: [], photos: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  function R(e) { var r = e.getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom}; }
  function hit(a, b) { return Math.min(a.r, b.r) - Math.max(a.l, b.l) > 0.5 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 0.5; }
  function clip(e) {                        /* what is seen of a picture: its box inside every clipping ancestor */
    var r = R(e), p, q;
    for (p = e.parentElement; p && !p.classList.contains('slide'); p = p.parentElement) {
      if (getComputedStyle(p).overflow !== 'visible') { q = R(p); r = {l: Math.max(r.l, q.l), t: Math.max(r.t, q.t), r: Math.min(r.r, q.r), b: Math.min(r.b, q.b)}; }
    }
    return r;
  }
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        var st = document.createElement('style');
        st.textContent = '*,*::before,*::after{animation:none!important;transition:none!important}';
        document.head.appendChild(st);
        var sb = document.getElementById('startBtn'); if (sb) { sb.click(); }
        var ch = document.getElementById('chrome'), slides = [].slice.call(document.querySelectorAll('.slide'));
        out.vp = [innerWidth, innerHeight];
        function show(s) { slides.forEach(function (x) { x.classList.remove('active'); }); s.classList.add('active'); void s.offsetHeight; }
        slides.forEach(function (s) {
          var c = s.querySelector('.credit'), rb = s.querySelector('.slide-body.recap');
          if (c) {
            show(s);
            var cr = R(c), bad = [], w, n;
            if (cr.l < -0.5 || cr.t < -0.5 || cr.r > innerWidth + 0.5 || cr.b > innerHeight + 0.5) { bad.push('off the screen'); }
            if (ch && hit(cr, R(ch))) { bad.push('under #chrome'); }
            [].forEach.call(s.querySelectorAll('img,video,canvas'), function (m) {
              var r = clip(m);
              if (r.r - r.l > 1 && r.b - r.t > 1 && hit(cr, r)) { bad.push('over the ' + m.tagName.toLowerCase() + ' by ' + Math.round(Math.min(cr.b, r.b) - Math.max(cr.t, r.t)) + ' px'); }
            });
            w = document.createTreeWalker(s, NodeFilter.SHOW_TEXT);
            while ((n = w.nextNode())) {
              if (!n.textContent.trim() || c.contains(n) || n.parentElement.closest('.slide-kind')) { continue; }
              var rg = document.createRange(); rg.selectNodeContents(n);
              [].forEach.call(rg.getClientRects(), function (q) {
                if (hit(cr, {l: q.left, t: q.top, r: q.right, b: q.bottom})) { bad.push('over the words "' + n.textContent.trim().slice(0, 30) + '"'); }
              });
            }
            var fa = getComputedStyle(s, '::after');          /* the slide's footer line (its module title), drawn by CSS */
            if (fa.content && fa.content !== 'none' && fa.position === 'absolute') {
              var ft = R(s).b - parseFloat(fa.bottom) - parseFloat(fa.height);
              if (cr.b > ft + 0.5) { bad.push('on the footer line by ' + Math.round(cr.b - ft) + ' px'); }
            }
            var sb2 = s.querySelector('.slide-body');
            if (sb2 && sb2.scrollHeight - sb2.clientHeight > 1) { bad.push('the body spills ' + (sb2.scrollHeight - sb2.clientHeight) + ' px'); }
            out.credits.push({id: s.id, cls: s.className, h: Math.round(cr.b - cr.t), bad: bad, inCol: !!c.closest('.fill.photo-col')});
          }
          if (rb) {
            show(s);
            var bottom = R(s).b - parseFloat(getComputedStyle(s).paddingBottom), nx = s.querySelector('.rc-next'), cut = 0;
            [].forEach.call(s.querySelectorAll('.rc-item'), function (it) { cut = Math.max(cut, it.scrollHeight - it.clientHeight); });
            out.recaps.push({id: s.id, n: s.querySelectorAll('.rc-item').length, cut: cut,
                             over: Math.round(Math.max(rb.scrollHeight - rb.clientHeight, R(nx || rb).b - bottom)),
                             chrome: !!(ch && nx && hit(R(nx), R(ch))),
                             fs: parseFloat(getComputedStyle(s.querySelector('.rc-d')).fontSize)});
          }
          var pim = s.querySelector('.photo-wrap img, .fill.photo-col > img, .slide-body.stage img');
          if (pim) {                              /* a photo slide: its credit in the full-screen record (2.63.0) */
            show(s);
            var pb = s.querySelector('.slide-body');
            out.photos.push({id: s.id, credit: pim.getAttribute('data-credit') || '', text: !!s.querySelector('.credit'),
                             spill: pb ? Math.max(0, pb.scrollHeight - pb.clientHeight) : 0});
          }
          var ins = s.querySelector('.copy > .inset');
          if (ins) {                              /* a photo under the words beside a picture (2.63.0) */
            show(s);
            var bd = s.querySelector('.slide-body'), im = R(ins.querySelector('img')), lw = s.querySelector('.copy .support li, .copy .lead');
            out.insets.push({id: s.id, spill: bd.scrollHeight - bd.clientHeight, off: Math.round(Math.max(0, R(bd).b - R(s).b)),
                             img: Math.round(im.b - im.t), past: Math.round(Math.max(0, im.b - R(bd).b)),
                             fs: lw ? parseFloat(getComputedStyle(lw).fontSize) : 0});
          }
        });
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out);
      document.body.appendChild(pre);
    }, 300);
  });
}());
"""
# the IGF recaps that spilled at 1280 x 800 (2.59.0 builders wrote module CSS for them), as approved
M03_S18 = ("Pipes - double-walled in enclosed spaces, free to shrink in the cold, a relief valve wherever liquid can be trapped.\n"
           "Valves - cryogenic valves with extended bonnets; on a gas trip two block valves close and the bleed valve opens.\n"
           "Tanks - pressure kept in range, filled only to the loading limit; relief valves lift to the vent mast, a hazardous zone.\n"
           "Vent fire - stop the venting, nitrogen into the mast, cool the mast head; never block the relief valve.\n"
           "Bunkering - prepare, connect, inert, cool down, transfer, drain, purge, disconnect.\n"
           "Spills and leaks - a drip tray and cold-tolerant steel protect the hull; fixed detectors find the leak.")
M05_S11 = ("Goals first - the IGF Code sets goals and functional requirements; an alternative design must be just as safe.\n"
           "Two barriers - a single failure must not let the fuel reach the people.\n"
           "Layers of protection - contain, detect, no ignition, limit harm.\n"
           "Machinery spaces - gas-safe with double-walled pipes, or ESD-protected with automatic shutdown at 40 % LEL.\n"
           "ISM Code - the SMS, reporting and continuous improvement make a safety culture.")
# IGF M05 s03 beside its photo column (wide-left, split 0.6): a credit strip that took its height from the body made it 102 %
M05_S03 = ("Chapter 3 of the Code sets the safety principles for every IGF ship.\n• as safe and reliable as a ship with oil-fuelled "
           "engines\n• a single failure must not lead to an unsafe situation\n• hazardous areas as small as possible, with few "
           "ignition sources in them\n• no gas may gather where it is not meant to be - ventilation and fixed gas detection\n• "
           "alarms, automatic shutdowns, fire detection and fire-fighting for each hazard\nRisk assessment - the risks to the "
           "people, the environment and the ship are analysed, removed where possible, otherwise reduced, and written down.")
# as long as IGF M05 s01's (three lines at 1024 x 768): a wrapped credit must still stop short of the chrome
LONG_CREDIT = {"source": "Wikimedia Commons", "author": "Wolfmann (Wikimedia Commons user), own work", "licence": "CC BY-SA 4.0",
               "title": "MF Raunefjord (Florø, Norway, 2007) LNWU, part of safety plan (sikkerhetsplan), drawing onboard ferry. "
                        "Photo 2018-03-15", "modification": "resized", "attribution_required": True, "description": "A ship taking gas."}
# as long as IGF M05 s08's - beside the photo column it wraps at 1024 x 768 and must still stop short of the chrome
MID_CREDIT = {"source": "Wikimedia Commons", "author": "John Konrad", "licence": "CC BY-SA 3.0", "title": "ESD Button",
              "modification": "resized", "attribution_required": True, "description": "A gas detector."}


def deck_fit(exe, page, tmp, size, js=DECK_FIT):
    text = io.open(page, encoding="utf-8").read()
    text = re.sub(r"<head>", '<head><base href="%s/">' % Path(os.path.dirname(page)).as_uri(), text, count=1)
    i = text.rfind("</body>")
    w = os.path.join(tmp, "fit.html")
    io.open(w, "w", encoding="utf-8").write(text[:i] + "<script>%s</script>" % js + text[i:])
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--hide-scrollbars",
                        "--user-data-dir=" + os.path.join(tmp, "prof"), "--allow-file-access-from-files",
                        "--window-size=%d,%d" % (size[0] + 16, size[1] + 95), "--virtual-time-budget=10000", "--dump-dom", Path(w).as_uri()],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]]}


def deck_fit_part(exe, tmp):
    """2.60.0 - what a trainee saw on the IGF build: the photo credit over the photograph's lower edge (seven modules) and
    over the lead (M15 s01); six recap boxes 13-27 px taller than the slide at 1280 x 800 (M02, M03, M05 - each builder
    wrote module CSS). Built from the factory's CSS alone and measured at 1280 x 800 and 1024 x 768: every credit is a
    strip of its own (over no picture, no word, not under the chrome), and every recap fits with the words' size kept."""
    print("\n-- 2.60.0: photo credits and recaps on the slide, at both tablet sizes")
    for name, recap in (("m02", tcm.M02_S16), ("m03", M03_S18), ("m05", M05_S11)):
        os.makedirs(os.path.join(tmp, "fit_" + name))
        screens = [
            {"id": "s01", "kind": "slide", "title": "Module 1 · Gas as fuel", "layout": "visual_full", "visual_kind": "photo",
             "text": "Some ships burn gas as fuel.", "visual": "A ship bunkering - a real photograph.", "minutes": 3},
            {"id": "s02", "kind": "slide", "title": "The IGF Code", "layout": "visual_full", "visual_kind": "photo",
             "text": tcm.M01_S01, "visual": "A gas-fuelled ship - a real photograph.", "minutes": 4},
            {"id": "s03", "kind": "slide", "title": "The safety principles of the IGF Code", "layout": "split", "visual_kind": "photo",
             "text": M05_S03, "visual": "A fixed gas detector - a real photograph.", "minutes": 4},
            {"id": "s04", "kind": "slide", "title": "The bunker station", "layout": "visual_wide", "visual_kind": "photo",
             "text": "The hose is earthed before it is connected.", "visual": "The bunker station - a real photograph.", "minutes": 2},
        ] + json.loads(json.dumps(tcm.SCREENS[4:6])) + [
            {"id": "s05", "kind": "slide", "recap": True, "title": "What to take away", "visual_kind": "none", "text": recap, "minutes": 2},
        ] + json.loads(json.dumps(tcm.SCREENS[6:]))
        c, md = tcm.new_course(os.path.join(tmp, "fit_" + name), tcm.script(screens=screens), build=False)
        img = os.path.join(md, "assets", "img")
        for k, f in enumerate(("ship.jpg", "deck.jpg", "station.jpg", "hose.jpg")):   # four pictures, not one shown four times (L58)
            io.open(os.path.join(img, f), "wb").write(tcm.png(1200, 800, (90 + 20 * k, 110, 140)))
        tcm.cs.save(os.path.join(img, "_photo_meta.json"), {"ship.jpg": LONG_CREDIT, "deck.jpg": LONG_CREDIT, "station.jpg": LONG_CREDIT,
                                                            "hose.jpg": MID_CREDIT})
        tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
            # s02 asks for the split photo by name: since 2.62.1 a long full-screen photo is a photo column by default
            "s01": {"figure": "assets/img/ship.jpg"}, "s02": {"figure": "assets/img/deck.jpg", "composition": "two-col"},
            "s03": {"figure": "assets/img/station.jpg", "composition": "wide-left", "split": 0.6},
            "s04": {"figure": "assets/img/hose.jpg", "composition": "stage"}, "t01": {"try_tablet": False}}})
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1")
        page = os.path.join(md, "presentation", "index.html")
        check("%s: the photo and recap fixture builds" % name, code == 0 and os.path.isfile(page), out[-600:])
        for size in ((1280, 800), (1024, 768)):
            r = deck_fit(exe, page, tmp, size)
            tag = "%s %dx%d" % (name, size[0], size[1])
            check("%s: no script error, measured at the size asked for" % tag, not r.get("errors") and r.get("vp") == list(size), r.get("errors") or r.get("vp"))
            if name == "m02":
                # 2.63.0 (owner Raivis, 2026-10-21): no credit text on a slide - the record carries it full screen
                ph = r.get("photos") or []
                check("%s: four photo slides (full screen, split, photo column, stage), no credit text on any - each photo's "
                      "credit in its full-screen record" % tag, len(ph) == 4 and not r.get("credits")
                      and all(x["credit"] and not x["text"] for x in ph), (ph, r.get("credits")))
                check("%s: ... and the body beside a photo column (M05 s03's 121 words) keeps its room" % tag,
                      ph and not any(x["spill"] > 1 for x in ph), ph)
            rc = (r.get("recaps") or [{}])[0]
            check("%s: the %s-box recap fits the slide - nothing past its foot, no box cutting its words, 'Next' clear of the chrome"
                  % (tag, rc.get("n")), rc.get("over", 99) <= 0 and rc.get("cut", 99) <= 1 and not rc.get("chrome"), rc)
            check("%s: ... with the words at their size (17 px or more)" % tag, rc.get("fs", 0) >= 17, rc)


INSET_KIT = {"size": [400, 220], "label": "A fuel tank and the vent mast", "parts": [
    {"id": "T", "type": "tank", "x": 30, "y": 100, "w": 200, "h": 80, "label": "Fuel tank", "value": 0.5},
    {"id": "V", "type": "vent", "x": 330, "y": 60, "label": "Vent mast"}],
    "steps": [{"title": "The tank fills", "line": 1, "play": [["T", 0.8, 0]]}]}


def inset_part(exe, tmp):
    """2.60.0 (M01 benchmark, compiler_v259 runs 5-9: four of eleven runs only the review sheet saw it) - a real photo laid
    "over" a kit drawing: the photo and its wrapped caption / credit lay over the kit's labels and ran onto the step
    buttons, and the drawing check was clean. Now it is a finding (audit_drawing.js INSET); a short credit on a blank
    corner is not."""
    print("\n-- 2.60.0: a photo laid over a kit drawing, judged against its words and the buttons")
    for name, over, cap, want in (
            ("covers", {"x": 20, "y": 90, "w": 230}, "The deck tanks of a gas-fuelled ferry, seen from the bridge wing, before bunkering.", True),
            ("corner", {"x": 245, "y": 110, "w": 100}, "", False)):
        os.makedirs(os.path.join(tmp, "in_" + name))
        c, md = tcm.new_course(os.path.join(tmp, "in_" + name), tcm.script(), build=False)
        io.open(os.path.join(md, "assets", "img", "ship.jpg"), "wb").write(tcm.png(300, 200, (120, 130, 150)))
        tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "tank.kit.json"), INSET_KIT)
        ins = {"photo": "assets/img/ship.jpg", "over": over, "credit": "Photo: J. Doe · CC BY-SA 4.0" if not cap else
               "Photo: Jane Doe (Wikimedia Commons user), own work · Wikimedia Commons · CC BY-SA 4.0 · resized"}
        if cap:
            ins["caption"] = cap
        tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
            "s01": {"figure": "assets/fig/scale.svg"}, "s02": {"figure": "tank.kit.json", "dark": True, "inset": ins},
            "s04": {"figure": "hull.svg", "dark": True, "declined_3d": "the fixture's hull stays flat"}, "t01": {"try_tablet": False}}})
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
        page = os.path.join(md, "presentation", "index.html")
        check("%s: the kit slide with its photo 'over' builds" % name, os.path.isfile(page) and 'class="inset over"' in io.open(page, encoding="utf-8").read(), out[-500:])
        probs, note = drawing_check.check([page], root=md)
        found = [x for x in probs if ": inset - " in x]
        if want:
            check("covers: the photo and its caption are found over the drawing's words (Fuel tank) - and past the drawing",
                  any("Fuel tank" in x and "lies over the drawing's words" in x for x in found) and any("past the drawing" in x for x in found),
                  found or probs or note)
        else:
            check("corner: a short credit on a blank corner of the drawing is clean", not found and not note, found or note)


# the parts on the right and along the foot, the top-left corner left blank for a photo laid "over" it
CORNER_KIT = {"size": [400, 220], "label": "A fuel tank, a day tank and the vent mast", "parts": [
    {"id": "T", "type": "tank", "x": 200, "y": 110, "w": 180, "h": 90, "label": "Fuel tank", "value": 0.5},
    {"id": "D", "type": "tank", "x": 20, "y": 150, "w": 150, "h": 55, "label": "Day tank", "value": 0.3},
    {"id": "V", "type": "vent", "x": 330, "y": 40, "label": "Vent mast"}]}


def inset_empty_part(exe, tmp):
    """2.63.0 (IGF M01 v262 s02 / s04, builder's bug 2) - a figure drawn to leave a corner for a photo laid "over" it failed
    EMPTY: the drawing check counted the corner the photo fills as blank, so the builder dropped the photo. The same
    drawing without its photo is still EMPTY (the corner is really blank); with the photo there it is not."""
    print("\n-- 2.63.0: the corner an 'over' photo fills is not empty space")
    for name, with_photo in (("bare", False), ("photo", True)):
        os.makedirs(os.path.join(tmp, "ie_" + name))
        c, md = tcm.new_course(os.path.join(tmp, "ie_" + name), tcm.script(), build=False)
        io.open(os.path.join(md, "assets", "img", "ship.jpg"), "wb").write(tcm.png(300, 200, (120, 130, 150)))
        tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "corner.kit.json"), CORNER_KIT)
        s02 = {"figure": "corner.kit.json", "no_photo": ["Fuel tank", "Day tank", "Vent mast"]}
        if with_photo:
            s02["inset"] = {"photo": "assets/img/ship.jpg", "over": {"x": 8, "y": 6, "w": 170}, "credit": "J. Doe, CC BY 4.0"}
        tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
            "s01": {"figure": "assets/fig/scale.svg"}, "s02": s02,
            "s04": {"figure": "hull.svg", "declined_3d": "the fixture's hull stays flat"}, "t01": {"try_tablet": False}}})
        code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
        page = os.path.join(md, "presentation", "index.html")
        check("%s: the kit slide builds" % name, os.path.isfile(page), out[-500:])
        probs, note = drawing_check.check([page], root=md)
        empty = [x for x in probs if ": empty - " in x and "s02" in x]
        if with_photo:
            check("photo: the corner the photo fills is not EMPTY", not empty and not note, empty or note)
        else:
            check("bare: without its photo the corner is blank - EMPTY (the fixture is a real hole)", empty, probs or note)


# as long as IGF M01 s03 (58 words), which with its photo under the words ran 21 px off the slide on 2.62.0 (18 at 1024)
UNDER_S02 = ("The IGF ship has five spaces a ship on oil fuel does not have.\n• the fuel tank, in its own hold\n"
             "• the tank connection space, around every pipe that leaves the tank\n• the fuel preparation room, with the pumps "
             "and the vaporizer\n• the bunkering station, where the fuel comes on board\n• the vent mast, for the relief valves")


def inset_under_part(exe, tmp):
    """2.63.0 (IGF M01 v262 runs 4-5, builder's bug 4) - a photo under the words beside a kit drawing ran the slide body
    9-22 px past its foot at both sizes (the photo at its full 26 vh); "split" 0.58-0.6 did not help. Now the photo takes
    the room the words leave: nothing spills, the words keep their size, the photo stays a photo (80 px or more)."""
    print("\n-- 2.63.0: a photo under the words beside a drawing takes only the room the words leave")
    os.makedirs(os.path.join(tmp, "iu"))
    screens = json.loads(json.dumps(tcm.SCREENS))
    screens[1]["text"] = UNDER_S02
    c, md = tcm.new_course(os.path.join(tmp, "iu"), tcm.script(screens=screens), build=False)
    io.open(os.path.join(md, "assets", "img", "ship.jpg"), "wb").write(tcm.png(1200, 800, (120, 130, 150)))
    tcm.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), {"ship.jpg": MID_CREDIT})
    tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "corner.kit.json"), CORNER_KIT)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "s01": {"figure": "assets/fig/scale.svg"},
        "s02": {"figure": "corner.kit.json", "composition": "two-col", "no_photo": ["Fuel tank", "Day tank", "Vent mast"],
                "inset": {"photo": "assets/img/ship.jpg", "caption": "Two LNG fuel tanks on the open aft deck of a ferry."}},
        "s04": {"figure": "hull.svg", "declined_3d": "the fixture's hull stays flat"}, "t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    page = os.path.join(md, "presentation", "index.html")
    check("the drawing slide with its photo under the words builds", os.path.isfile(page) and 'class="inset"' in io.open(page, encoding="utf-8").read(), out[-600:])
    for size in ((1280, 800), (1024, 768)):
        r = deck_fit(exe, page, tmp, size)
        tag = "%dx%d" % size
        ins = (r.get("insets") or [{}])[0]
        check("%s: no script error, the slide measured" % tag, not r.get("errors") and ins.get("id"), r.get("errors") or r)
        check("%s: nothing spills - the body neither scrolls nor runs past the slide, the photo ends inside it" % tag,
              ins.get("spill", 99) <= 1 and ins.get("off", 99) <= 0 and ins.get("past", 99) <= 0, ins)
        check("%s: the words keep their size (17 px or more) and the photo stays a photo (75 px or more)" % tag,
              ins.get("fs", 0) >= 17 and ins.get("img", 0) >= 75, ins)


RUN_AUDITS = os.path.join(HERE, "..", "..", "..", "course-module-ux", "measure", "scripts", "run_audits.py")


def strip_contrast_part(exe, tmp):
    """2.63.0 (IGF M02 v262 run 5, s03, builder's bug 3) - on a LIGHT slide the L57 photo strip under a kit drawing sits in
    the Navy figure panel, but its captions kept the light page's grey: "Fuel tank" read 1.89:1, and the number badge was
    Navy on Navy. With 80 / 20 (2.62.1) light is the default, so every such strip would fail. Measured by the deck audit."""
    print("\n-- 2.63.0: the photo strip under a drawing on a light slide reads on the Navy panel")
    os.makedirs(os.path.join(tmp, "sc"))
    c, md = tcm.new_course(os.path.join(tmp, "sc"), tcm.script(), build=False)
    io.open(os.path.join(md, "assets", "img", "tank.jpg"), "wb").write(tcm.png(600, 400, (150, 160, 170)))
    tcm.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), dict(tcm.PHOTO_META, **{"tank.jpg": dict(
        MID_CREDIT, description="A type C fuel tank on a ship's deck.", shows=["fuel tank"])}))
    tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "corner.kit.json"), CORNER_KIT)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "s01": {"figure": "assets/fig/scale.svg"}, "s02": {"figure": "corner.kit.json", "composition": "two-col"},
        "s04": {"figure": "hull.svg", "declined_3d": "the fixture's hull stays flat"}, "t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    page = os.path.join(md, "presentation", "index.html")
    text = io.open(page, encoding="utf-8").read() if os.path.isfile(page) else ""
    s02 = re.search(r'<section class="slide"[^>]*data-title="The Code".*?</section>', text, re.S)
    check("a light kit slide with the strip under its drawing, in the figure's panel", s02 and re.search(
        r'class="fill fig[^"]*".*class="photo-strip"', s02.group(0), re.S), out[-600:])
    p = subprocess.run([sys.executable, RUN_AUDITS, page, "--quiet"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    low = [x.strip() for x in p.stdout.splitlines() if "low contrast" in x and "(s02)" in x]
    check("no caption or badge of the strip under the contrast floor at 1280 x 800",
          ("deck" in p.stdout or "every probe passed" in p.stdout) and not low, low or p.stdout[-600:])


PUSH_BUTTON_SC = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "panel_operate", "question": "Stop the bunkering now.",
     "visual": "the panel", "answer": "ESD push button = pressed", "feedback": "The ESD stops the transfer."}]


def push_button_part(exe, tmp):
    """2.63.2 (item 4, IGF M14's builder) - the kit's push_button, drawn as the symbol of a ready / pressed position on the
    light task page, failed the contrast check (cap 2.7:1, lid 2.7:1, tag plate 2.3:1 on the symbol's panel): its colours live
    in kit.js, and only kit.css's rules were taken as the kit's own, so M14 worked around it with "waiting" / "pressed" (no
    symbol). A part merged into the kit is now marked (<style data-kit-own>) and its colours are the kit's own too."""
    print("\n-- 2.63.2: the kit's push_button as a task page's symbol passes the contrast check")
    os.makedirs(os.path.join(tmp, "pb"))
    c, md = tcm.new_course(os.path.join(tmp, "pb"), tcm.script(screens=PUSH_BUTTON_SC), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "t01": {"try_tablet": False}, "q01": {"states": {"ESD push button": ["ready", "pressed"]}}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_self_check_1.html")
    text = io.open(page, encoding="utf-8").read() if os.path.isfile(page) else ""
    check("a ready / pressed question on the task page carries the kit's push_button symbol", '"type":"push_button"' in text, out[-500:])
    probs, note = drawing_check.check([page])
    bad = [x for x in probs if "contrast" in x]
    check("the push_button symbol passes the drawing check's contrast (cap, lid and tag plate are the kit's own colours)",
          note is None and not bad, bad or note)


SHIP_PLAN = {"size": [640, 300], "label": "The spaces of an IGF ship", "parts": [
    {"id": "ER", "type": "space", "x": 10, "y": 120, "w": 120, "h": 150, "label": "Engine room"},
    {"id": "FPR", "type": "space", "x": 140, "y": 120, "w": 110, "h": 150, "label": "Fuel preparation room"},
    {"id": "TCS", "type": "space", "x": 260, "y": 120, "w": 110, "h": 150, "label": "Tank connection space"},
    {"id": "FT", "type": "space", "x": 380, "y": 120, "w": 140, "h": 150, "label": "Fuel tank"},
    {"id": "BS", "type": "space", "x": 530, "y": 120, "w": 100, "h": 150, "label": "Bunkering station"},
    {"id": "VM", "type": "space", "x": 260, "y": 10, "w": 110, "h": 90, "label": "Vent mast"}]}
SHIP_PLAN_DRIVE = r"""
(function () {
  var out = {errors: [], taps: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        var sb = document.getElementById('startBtn'); if (sb) { sb.click(); }
        var s = document.querySelector('.slide svg[data-kit]').closest('.slide');
        [].slice.call(document.querySelectorAll('.slide')).forEach(function (x) { x.classList.remove('active'); });
        s.classList.add('active');
        GBZoom.scan();
        out.thumbs = s.querySelectorAll('.photo-strip img[data-part]').length;
        out.tapOnly = s.querySelectorAll('.photo-taps img[data-part]').length;
        [].slice.call(s.querySelectorAll('.gbz-part')).forEach(function (p) {
          var shape = p.querySelector('rect, path') || p;
          shape.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
          var im = document.querySelector('.gbz-stage img'), cap = document.querySelector('.gbz-cap');
          out.taps.push({part: p.getAttribute('data-photo'), shown: im ? im.getAttribute('src').split('/').pop() : null,
                         record: cap ? cap.textContent.replace(/\s+/g, ' ').trim().slice(0, 80) : ''});
          GBZoom.close();
        });
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out);
      document.body.appendChild(pre);
    }, 600);
  });
}());
"""


def ship_plan_part(exe, tmp):
    """2.63.0 (the instructors' review of IGF Basic, M01 3/11 and 4/11: "a clickable vessel - tap Engine room, FPR, TCS,
    bunkering station, vent mast, oil fuel tank and see a real photo"): a ship plan whose six spaces have six real photos -
    four as L57 thumbnails, two tap-only - and a tap on each drawn space opens ITS photo full screen, with its record"""
    print("\n-- 2.63.0: a tap on a drawn space opens its real photograph")
    os.makedirs(os.path.join(tmp, "sp"))
    screens = json.loads(json.dumps(tcm.SCREENS))
    screens[1]["text"] = "The spaces of an IGF ship.\n• engine room\n• fuel preparation room\n• tank connection space"
    c, md = tcm.new_course(os.path.join(tmp, "sp"), tcm.script(screens=screens), build=False)
    img, meta = os.path.join(md, "assets", "img"), {}
    for k, name in enumerate(["Engine room", "Fuel preparation room", "Tank connection space", "Fuel tank", "Bunkering station", "Vent mast"]):
        f = "sp%d.jpg" % k
        io.open(os.path.join(img, f), "wb").write(tcm.png(900, 600, (40 + 30 * k, 90, 140)))
        meta[f] = dict(MID_CREDIT, description="The %s of an LNG-fuelled ship." % name.lower(), shows=[name.lower()])
    tcm.cs.save(os.path.join(img, "_photo_meta.json"), meta)
    tcm.cs.save(os.path.join(c, "working_claude", "figures", "M01", "plan.kit.json"), SHIP_PLAN)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "s01": {"figure": "assets/fig/scale.svg"}, "s02": {"figure": "plan.kit.json", "composition": "two-col"},
        "s04": {"figure": "hull.svg", "declined_3d": "the fixture's hull stays flat"}, "t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    page = os.path.join(md, "presentation", "index.html")
    text = io.open(page, encoding="utf-8").read()
    check("the plan builds with four thumbnails and the rest tap-only", 'class="photo-taps" hidden' in text, out[-500:])
    w = os.path.join(md, "presentation", "_ship.html")
    io.open(w, "w", encoding="utf-8").write(text.replace("</body>", "<script>%s</script></body>" % SHIP_PLAN_DRIVE))
    p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--user-data-dir=" + os.path.join(tmp, "spp"),
                           "--allow-file-access-from-files", "--window-size=1296,895", "--virtual-time-budget=10000", "--dump-dom",
                           Path(w).as_uri()], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    r = json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result"]}
    taps = {t["part"]: t for t in r.get("taps") or []}
    check("no script error; 4 thumbnails, 2 tap-only", not r.get("errors") and r.get("thumbs") == 4 and r.get("tapOnly") == 2, r)
    check("all six drawn spaces open a photo when tapped - the thumbnail ones and the tap-only ones", len(taps) == 6, sorted(taps))
    want = {"Engine room": "sp0.jpg", "Fuel preparation room": "sp1.jpg", "Tank connection space": "sp2.jpg", "Fuel tank": "sp3.jpg",
            "Bunkering station": "sp4.jpg", "Vent mast": "sp5.jpg"}
    check("... each its OWN photo, with its record under it", all((taps.get(k) or {}).get("shown") == v for k, v in want.items())
          and all("LNG-fuelled ship" in (t.get("record") or "") for t in taps.values()), taps)
    # 2.63.2 (item 16): the parts that open a photo show it - a camera badge each, clear of every word, at both sizes
    for size in ((1280, 800), (1024, 768)):
        r = drive_page(exe, page, BADGE_DRIVE, os.path.join(tmp, "spb%d" % size[0]), size)
        bd = r.get("badges") or []
        check("%dx%d: a camera badge on each of the six parts with a photo, 44 px, 'Photo of <part>'" % size,
              not r.get("errors") and len(bd) == 6 and all(b["w"] >= 44 and b["h"] >= 44 for b in bd)
              and sorted(b["label"] for b in bd) == sorted("Photo of " + k for k in want), r)
        check("%dx%d: no badge covers a word of the drawing or another badge" % size,
              bd and not [b for b in bd if b["over"]], [b for b in bd if b["over"]])
        check("%dx%d: a tap on a badge opens its part's photo full screen" % size,
              r.get("opened") and all(r["opened"].get(k) == v for k, v in want.items()), r.get("opened"))
    sheet = tcm.cs.load(os.path.join(c, "working_claude", "script", "M01.build.json"))
    sheet["screens"]["s02"]["photo_badges"] = False
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), sheet)
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    r = drive_page(exe, page, BADGE_DRIVE, os.path.join(tmp, "spb0"), (1280, 800))
    check("\"photo_badges\": false turns them off on that slide - the parts still open their photos",
          'data-photo-badges="off"' in io.open(page, encoding="utf-8").read() and r.get("badges") == [] and r.get("parts") == 6,
          (out[-300:], r))


BADGE_DRIVE = r"""
(function () {
  var out = {errors: [], badges: [], opened: {}};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        var sb = document.getElementById('startBtn'); if (sb) { sb.click(); }
        var s = document.querySelector('.slide svg[data-kit]').closest('.slide');
        [].slice.call(document.querySelectorAll('.slide')).forEach(function (x) { x.classList.remove('active'); });
        s.classList.add('active');
        GBZoom.scan();
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      setTimeout(function () {
        try {
          var s = document.querySelector('.slide.active'), words = [].slice.call(s.querySelectorAll('svg text')).map(function (t) { return t.getBoundingClientRect(); });
          var bs = [].slice.call(s.querySelectorAll('.gbz-cam')), rs = bs.map(function (b) { return b.getBoundingClientRect(); });
          function hit(a, b) { return a.left < b.right - 0.5 && a.right > b.left + 0.5 && a.top < b.bottom - 0.5 && a.bottom > b.top + 0.5 && a.width && b.width; }
          out.parts = s.querySelectorAll('.gbz-part').length;
          bs.forEach(function (b, i) {
            var r = rs[i], over = words.filter(function (w) { return hit(r, w); }).length + rs.filter(function (q, j) { return j !== i && hit(r, q); }).length;
            out.badges.push({label: b.getAttribute('aria-label'), w: Math.round(r.width), h: Math.round(r.height), over: over});
            b.click();
            var im = document.querySelector('.gbz-stage img');
            out.opened[b.getAttribute('aria-label').replace('Photo of ', '')] = im ? im.getAttribute('src').split('/').pop() : null;
            GBZoom.close();
          });
        } catch (err) { out.errors.push(String(err && err.stack || err)); }
        var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
      }, 600);
    }, 400);
  });
}());
"""


LAST_PARTS_DRIVE = r"""
(function () {
  var out = {errors: [], seen: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        var nx = document.getElementById('btnNext');
        document.getElementById('startBtn').click();
        for (var i = 0; i < 5; i++) {
          var s = document.querySelector('.slide.active'), p = s && s.querySelector('.lt-part.on');
          out.seen.push((s ? s.id : '-') + (p ? ':' + p.getAttribute('data-n') : '') + (nx.disabled ? ' (Next off)' : ''));
          if (!nx.disabled) { nx.click(); }
        }
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
    }, 300);
  });
}());
"""


def last_parts_part(exe, tmp):
    """2.63.2 (the 2.63.2 full-course run: M08-M10, M12-M14 - the practical slide, in two parts, is the deck's last) - Next
    walks the parts of the LAST slide too, and is off only on its last part"""
    print("\n-- 2.63.2: Next walks the parts of the deck's last slide")
    d = os.path.join(tmp, "lastparts")
    os.makedirs(d)
    deck = Path(HERE).parent.parent.parent / "course-module-ux" / "assets" / "gb_deck.js"
    page = os.path.join(d, "index.html")
    io.open(page, "w", encoding="utf-8").write(
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"></head><body>'
        '<div id="landing"><button id="startBtn" type="button">Start</button></div>'
        '<div id="chrome"><button id="btnPrev" type="button">Back</button><button id="btnNext" type="button">Next</button></div>'
        '<main><section class="slide" id="s1"><h2>One</h2></section>'
        '<section class="slide" id="s2"><h2>Practical</h2><div class="lt-part" data-n="1">Part 1</div>'
        '<div class="lt-part" data-n="2">Part 2</div></section></main>'
        '<script src="%s"></script><script>GBDeck.init({});</script></body></html>' % deck.as_uri())
    r = drive_page(exe, page, LAST_PARTS_DRIVE, os.path.join(tmp, "lpp"), (1280, 800))
    check("on the last slide Next shows its part 2, then is off: %s" % " -> ".join(r.get("seen") or []),
          not r.get("errors") and (r.get("seen") or [])[:3] == ["s1", "s2:1", "s2:2 (Next off)"], r)


LOCKSTEP_DRIVE = r"""
(function () {
  var out = {errors: [], fwd: [], back: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        var nx = document.getElementById('btnNext'), bk = document.getElementById('btnPrev');
        function at() {
          var s = document.querySelector('.slide.active'), svg = s && s.querySelector('svg[data-kit]'), f = svg && svg.__kit;
          var cur = s ? [].map.call(s.querySelectorAll('.cur'), function (x) { return x.getAttribute('data-i'); }).join(',') : '';
          var lit = s ? [].map.call(s.querySelectorAll('.lit'), function (x) { return x.getAttribute('data-i'); }).join(',') : '';
          var p = s && s.querySelector('.lt-part.on'), shown = '';
          if (cur && p) { shown = p.querySelector('[data-i="' + cur.split(',')[0] + '"]') ? 'shown' : 'HIDDEN'; }
          return (s ? s.id : '-') + (f ? ' step ' + f.n : '') + ' line ' + (cur || '-') + ' lit ' + (lit || '-') +
                 (p ? ' part ' + p.getAttribute('data-part') : '') + (shown ? ' ' + shown : '');
        }
        document.getElementById('startBtn').click();
        for (var i = 0; i < 6; i++) { out.fwd.push(at()); nx.click(); }
        out.fwd.push(at());
        for (var j = 0; j < 6; j++) { bk.click(); out.back.push(at()); }
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
    }, 500);
  });
}());
"""


def lockstep_part(exe, tmp):
    """2.63.3 (Aleksis, the 2.63.2 build of IGF M06 s12 "the cloud finds a spark": Next walked both text parts first, then
    the figure's steps, and the lit line jumped back to line 1; the original deck - before parts - stepped them together) -
    ONE Next is one step of both: the figure at step k, line k lit and in the part shown; Back mirrors it"""
    print("\n-- 2.63.3: a figure's steps, its lines and the text parts move together")
    d = os.path.join(tmp, "lockstep")
    os.makedirs(d)
    a = Path(HERE).parent.parent.parent
    spec = {"size": [400, 240], "label": "four steps",
            "parts": [{"id": "T", "type": "tank", "x": 30, "y": 80, "w": 160, "h": 90, "label": "tank", "value": 0.2},
                      {"id": "V", "type": "valve", "x": 300, "y": 125, "label": "valve", "value": 1}],
            "steps": [{"title": "1", "line": 1, "play": [["T", 0.4, 0]]}, {"title": "2", "line": 2, "play": [["T", 0.6, 0]]},
                      {"title": "3", "line": 3, "play": [["V", 0, 0]]}, {"title": "4", "line": 4, "play": [["T", 0.9, 0]]}]}
    page = os.path.join(d, "index.html")
    io.open(page, "w", encoding="utf-8").write(
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><link rel="stylesheet" href="%s"></head><body>'
        '<div id="landing"><button id="startBtn" type="button">Start</button></div>'
        '<div id="chrome"><button id="btnPrev" type="button">Back</button><button id="btnNext" type="button">Next</button></div>'
        '<main><section class="slide" id="s1"><h2>Cloud</h2><div class="fill fig kit-fig"><div class="kit-screen">'
        '<svg data-kit="#kit-s1"></svg></div><script type="application/json" id="kit-s1">%s</script></div>'
        '<div class="copy"><div class="lt-parts" data-parts="2"><div class="lt-part on" data-part="1"><p data-i="1">one</p>'
        '<p data-i="2">two</p></div><div class="lt-part" data-part="2"><p data-i="3">three</p><p data-i="4">four</p></div>'
        '<div class="lt-tabs"><button type="button" class="lt-tab on" data-part="1">1</button>'
        '<button type="button" class="lt-tab" data-part="2">2</button></div></div></div></section>'
        '<section class="slide" id="s2"><h2>After</h2></section></main>'
        '<script src="%s"></script><script src="%s"></script><script>GBDeck.init({ hooks: window.GB_HOOKS || {} });</script>'
        '</body></html>' % ((a / "course-visuals" / "kit" / "kit.css").as_uri(), json.dumps(spec),
                            (a / "course-module-ux" / "assets" / "gb_deck.js").as_uri(), (a / "course-visuals" / "kit" / "kit.js").as_uri()))
    r = drive_page(exe, page, LOCKSTEP_DRIVE, os.path.join(tmp, "lsp"), (1280, 800))
    fwd, back = r.get("fwd") or [], r.get("back") or []
    want = ["s1 step 0 line - lit - part 1", "s1 step 1 line 1 lit - part 1 shown", "s1 step 2 line 2 lit 1 part 1 shown",
            "s1 step 3 line 3 lit 1,2 part 2 shown", "s1 step 4 line 4 lit 1,2,3 part 2 shown", "s2 line - lit -"]
    check("each Next is one step of both - the figure at step k, line k lit and in the part shown, no extra presses: %s"
          % " | ".join(fwd), not r.get("errors") and fwd[:6] == want, r)
    check("... Back mirrors it, and Back into the slide lands on its last stop: %s" % " | ".join(back),
          back[:5] == ["s1 step 4 line 4 lit 1,2,3 part 2 shown", "s1 step 3 line 3 lit 1,2 part 2 shown",
                       "s1 step 2 line 2 lit 1 part 1 shown", "s1 step 1 line 1 lit - part 1 shown", "s1 step 0 line - lit - part 1"], back)


def drive_page(exe, page, js, prof, size):
    """a compiled deck with a driver script added, at a window `size` (its viewport exactly that, as probe() opens it)"""
    text = io.open(page, encoding="utf-8").read()
    w = os.path.join(os.path.dirname(page), "_drive_%d.html" % os.getpid())
    io.open(w, "w", encoding="utf-8").write(text.replace("</body>", "<script>%s</script></body>" % js))
    try:
        p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--user-data-dir=" + prof, "--hide-scrollbars",
                               "--allow-file-access-from-files", "--window-size=%d,%d" % (size[0], size[1] + 95), "--virtual-time-budget=10000",
                               "--dump-dom", Path(w).as_uri()], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    finally:
        os.remove(w)
    m = re.search(r'<pre id="gbtest">(.*?)</pre>', p.stdout, re.S)
    return json.loads(html.unescape(m.group(1))) if m else {"errors": ["no result: " + p.stdout[-300:] + p.stderr[-300:]]}


BLIND_LOOK = ("var seen = []; document.querySelectorAll('.scr[data-script]').forEach(function (s) {"
              "  s.querySelectorAll('.checked,.right,.wrong,.fixed,.shake,.missed,.dim,.stopat,.good,.bad,.why.on').forEach("
              "    function (n) { seen.push(s.getAttribute('data-script') + ':' + (n.getAttribute('class') || '')); });"
              "  var vd = s.querySelector('.vd'); if (vd && vd.textContent.trim()) { seen.push(s.getAttribute('data-script') + ':vd ' + vd.textContent); }"
              "}); out.looked = document.querySelectorAll('.scr[data-script=\"q05\"] .ffc.seen').length; out.shown = seen; out.result = document.getElementById('resScr').className;")


def blind_part(exe, page, tmp):
    """2.60.0 - a graded final is blind: the IGF build showed the right answer and the why after each question of final_a/b.
    The EVERY_WAY page as a final's (data-blind): one press per part records the answer and moves on; nothing right or
    wrong is marked, no verdict, no 'right so far'; the result screen and the classroom get the same score as a check."""
    print("\n-- 2.60.0: a blind final, five answered wrong")
    plan = []
    for q, steps in WRONG:
        once = []
        for x in steps:                                   # a part's Check + Go on is one press on a blind final
            if x == ["dock"] and once and once[-1] == ["dock"]:
                continue
            once.append(x)
        plan.append([q, once, "once"])
        if q == "q05":
            plan.append(["eval", "out.got = document.getElementById('gotLbl').textContent;"])
    plan.append(["eval", BLIND_LOOK])
    plan.append(["eval", "out.fixes = document.querySelectorAll('#resList .fix').length;"])
    r = drive(exe, page, plan, tmp, look=False, blind=True)
    check("2.63.2: the final's result lists no answers - it stays blind (L27)", r.get("fixes") == 0, r.get("fixes"))
    rep, steps = r.get("report") or {}, r.get("steps", [])
    check("no script error on the blind page", not r.get("errors"), r.get("errors"))
    check("the classroom hears the same 5 of 10 and the same items as on a check",
          rep.get("ok") == 5 and [x["ok"] for x in rep.get("items", [])] == [False, True, False, False, True, True, False, True, False, True], rep)
    check("one press per part: Next, Go on inside a scenario, See my score on the last - never Check",
          not any(s.endswith(":Check") for s in steps) and "q01:Next" in steps and "q03:Go on" in steps
          and steps[-1] == "q10:See my score", steps)
    check("nothing is revealed: no right/wrong/amber/missed mark, no why, no verdict on any question", r.get("shown") == [], r.get("shown"))
    check("a fault-finding panel shows only the reading the trainee looked at, not every part's", r.get("looked") == 1, r.get("looked"))
    check("no 'right so far' between questions", r.get("got") == "", r.get("got"))
    check("the result screen is open at the end", " on" in " " + (r.get("result") or ""), r.get("result"))


# 2.63.2 (item 18, Aleksis 2026-10-22: "for the checks you should be able to see your wrong answers and the reordered to
# correct ones") - a self-check and a module check answered partly wrong
REVIEW = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "r01", "kind": "self-check", "set": "SC1", "mechanic": "match", "question": "Match each space to what it holds.",
     "answer": "Fuel preparation room = pumps and vaporizers\nTank connection space = the tank valves\nVent mast = the vapour outlet",
     "feedback": "Each space has one job."},
    {"id": "r02", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the bunkering steps in order.",
     "answer": "Safety meeting\nConnect the hose\nTransfer\nDisconnect", "feedback": "Meeting first."},
    {"id": "r03", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Which is the fuel?",
     "options": ["LNG", "Coal"], "correct": "A", "feedback": "LNG."},
    {"id": "r04", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Is venting acceptable?",
     "options": ["Yes", "No, only in an emergency"], "correct": "B", "feedback": "Only in an emergency."},
    {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - Module 1", "text": "Module check on your tablet now.", "minutes": 5},
    {"id": "m01", "kind": "module-check", "set": "MC", "mechanic": "categorise", "question": "Sort the fuels.",
     "answer": "Detailed rules: LNG; CNG\nAlternative design: methanol; ammonia", "feedback": "Natural gas has detailed rules."},
    {"id": "m02", "kind": "module-check", "set": "MC", "mechanic": "single_choice", "question": "Is venting acceptable?",
     "options": ["Yes", "No, only in an emergency"], "correct": "B", "feedback": "Only in an emergency."},
]
RES_LOOK = ("var L=[].slice.call(document.querySelectorAll('#resList > li'));"
            "out.res=L.map(function(li){var o={cls:li.className,fix:li.querySelector('.fix')?li.querySelector('.fix').textContent.replace(/\\s+/g,' ').trim():''};"
            "o.mine=[].map.call(li.querySelectorAll('s.mine'),function(x){return x.textContent;});"
            "o.good=[].map.call(li.querySelectorAll('em.good'),function(x){return x.textContent;});"
            "o.order=[].map.call(li.querySelectorAll('.ord ol'),function(ol){return [].map.call(ol.children,function(x){return (x.className==='moved'?'*':'')+x.textContent;});});return o;});"
            "var r=document.getElementById('resScr');"
            "out.press=[].filter.call(r.querySelectorAll('#resList a, #resList button, #resList input, #resList [onclick], #resList [tabindex], #resList [role=button]'),function(){return true;}).length;"
            "out.onRes=/\\bon\\b/.test(r.className);")


def review_part(exe, tmp):
    """2.63.2 - the result screen of a self-check and of a module check lists every wrong question: the trainee's answer
    and the right one, an order beside the right order (the moved cards marked), the corrected pairs / groups; a right
    one is not listed; nothing pressable is added; the classroom's report is unchanged"""
    print("\n-- 2.63.2: the result shows the wrong answers and the right ones")
    os.makedirs(os.path.join(tmp, "rv"))
    c, md = tcm.new_course(os.path.join(tmp, "rv"), tcm.script(screens=REVIEW), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"),
                {"module": 1, "screens": {"t01": {"try_tablet": False}, "t02": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    sc = [os.path.join(md, "tasks", f) for f in sorted(os.listdir(os.path.join(md, "tasks"))) if f.startswith("sc1")] if code == 0 else []
    mc = os.path.join(md, "assessment", "check.html")
    check("the self-check and module-check pages are built", code == 0 and sc and os.path.isfile(mc), out[-800:])
    if not sc or not os.path.isfile(mc):
        return
    plan = [["r01", [["card", "the tank valves", 1], ["card", "pumps and vaporizers", 2], ["card", "the vapour outlet", 3]]],
            ["r02", [["card", "Connect the hose", 1], ["card", "Safety meeting", 2], ["card", "Transfer", 3], ["card", "Disconnect", 4]]],
            ["r03", [["tap", ".opt", "Coal"]]],
            ["r04", [["tap", ".opt", "No, only in an emergency"]]],
            ["eval", RES_LOOK]]
    r = drive(exe, sc[0], plan, tmp, look=False)
    res, rep = r.get("res") or [], r.get("report") or {}
    check("no script error", not r.get("errors"), r.get("errors"))
    check("the classroom hears the same report as before (1 of 4; the same fields, nothing added)",
          rep.get("ok") == 1 and set(rep) == {"type", "code", "title", "ok", "total", "head", "items", "answered", "of", "timeout"}, rep)
    check("the result screen is open, and every wrong question carries its correction - a right one none",
          r.get("onRes") and [x["cls"] for x in res] == ["no", "no", "no", "yes"] and all(x["fix"] for x in res[:3]) and not res[3]["fix"], res)
    m = res[0] if res else {}
    check("match: each card in the wrong place - where the trainee put it (struck) and where it goes",
          "the tank valves" in m.get("fix", "") and "Fuel preparation room" in m.get("mine", []) and "Tank connection space" in m.get("good", [])
          and "Fuel preparation room" in m.get("good", []), m)
    o = res[1] if len(res) > 1 else {}
    check("order: the trainee's order beside the right order, the moved cards marked",
          o.get("order") == [["*Connect the hose", "*Safety meeting", "Transfer", "Disconnect"],
                             ["Safety meeting", "Connect the hose", "Transfer", "Disconnect"]], o)
    ch = res[2] if len(res) > 2 else {}
    check("a choice: the trainee's answer struck, the right one beside it", ch.get("mine") == ["Coal"] and ch.get("good") == ["LNG"], ch)
    check("nothing to press is added after the result (result_is_last)", r.get("press") == 0, r.get("press"))
    plan = [["m01", [["dock"], ["card", "LNG", 2], ["card", "CNG", 1], ["card", "methanol", 2], ["card", "ammonia", 2]]],
            ["m02", [["tap", ".opt", "No, only in an emergency"]]], ["eval", RES_LOOK]]
    r = drive(exe, mc, plan, tmp, look=False)
    res = r.get("res") or []
    g = res[0] if res else {}
    check("module check, sort into groups: the card in the wrong group and its right group; the right question not listed",
          not r.get("errors") and "LNG" in g.get("fix", "") and g.get("mine") == ["Alternative design"] and g.get("good") == ["Detailed rules"]
          and len(res) == 2 and not res[1]["fix"], (r.get("errors"), res))


PATTERNS = [
    {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - the patterns", "text": "Self-check on your tablet now.", "minutes": 4},
    {"id": "q01", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the three steps in order.",
     "answer": "Ventilate the tank\nMeasure the atmosphere\nIssue the permit", "feedback": "Ventilate, measure, permit."},
    {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "Where is the fuel prepared?",
     "options": ["Fuel preparation room", "Bridge", "Galley"], "correct": "A", "feedback": "Pumps and vaporizers are there."},
    {"id": "q03", "kind": "self-check", "set": "SC1", "mechanic": "scenario", "question": "A leak in the fuel preparation room.",
     "answer": "The detector alarms at 20 % LEL => Find the leak* | Silence it | Carry on\n"
               "It reaches 40 % LEL => Leave the room* | Stay and look | Open the door wide", "feedback": "Find, leave."},
    {"id": "q04", "kind": "self-check", "set": "SC1", "mechanic": "cloze", "question": "Complete the sentence.",
     "answer": "LNG is stored at [-162 °C* | 0 °C | 20 °C], so the tank is [insulated* | painted | heated].", "feedback": "Very cold."},
    {"id": "q05", "kind": "self-check", "set": "SC1", "mechanic": "order", "question": "Put the eight steps of opening a gas line in order.",
     "answer": "\n".join(t for t, _ in PIPE), "feedback": "Make it safe first."},
]
PAT_PLAN = [
    ["q01", [["card", "Ventilate the tank", 2], ["card", "Measure the atmosphere", 1], ["card", "Issue the permit", 3],
             ["eval", "var t = s.querySelector('.tray');"          # every card placed, Check not pressed: the bank is empty and says so
                      "out.tray0 = {attr: t.getAttribute('data-empty'), before: getComputedStyle(t, '::before').content,"
                      " chips: t.querySelectorAll('.chip').length, display: getComputedStyle(t).display};"],
             ["dock"],
             ["eval", "function c(e, p) { return getComputedStyle(e)[p]; }"
                      "var t = s.querySelector('.tray'), f = s.querySelector('.chip.fixed'), r = s.querySelector('.chip.right');"
                      "out.fix = {tray: c(t, 'display'), nfixed: s.querySelectorAll('.chip.fixed').length,"
                      " fb: c(f, 'borderTopColor'), fs: c(f, 'boxShadow'), fbg: c(f, 'backgroundColor'), rb: c(r, 'borderTopColor'), rbg: c(r, 'backgroundColor')};"]]],
    ["q02", [["tap", ".opt", "Bridge"], ["dock"],
             ["eval", "out.dim = [].map.call(s.querySelectorAll('.opt.dim'), function (o) { return parseFloat(getComputedStyle(o).opacity); });"]]],
    ["q03", [["tap", ".opt", "Find the leak"], ["dock"], ["dock"],
             ["eval", RECT + "var p = s.querySelectorAll('.part'); out.sc1 = {a: R(p[0]), b: R(p[1]), cls: [p[0].className, p[1].className]};"],
             ["tap", ".opt", "Leave the room"], ["dock"],
             ["eval", RECT + "var p = s.querySelectorAll('.part'); out.sc2 = {a: R(p[0]), b: R(p[1]), cls: [p[0].className, p[1].className]};"]]],
    ["q04", [["tap", ".cg .opt", "-162 °C"], ["tap", ".cg .opt", "painted"], ["dock"],
             ["eval", "function c(e, p) { return getComputedStyle(e)[p]; }"
                      "var f = s.querySelector('.gap.fixed'), r = s.querySelector('.gap.right');"
                      "out.gap = {fb: c(f, 'borderTopColor'), fs: c(f, 'boxShadow'), fbg: c(f, 'backgroundColor'), rb: c(r, 'borderTopColor')};"]]],
    ["q05", [["card", t, n] for t, n in PIPE]          # eight rows: the places beside the bank (data-many); all placed right
            + [["eval", RECT + "var t = s.querySelector('.tray'); out.many0 = {many: s.getAttribute('data-many'), label: getComputedStyle(t, '::before').content,"
                              " tray: R(t), rows: R(s.querySelector('.rows'))};"],
               ["dock"],
               ["eval", RECT + "out.many1 = {tray: getComputedStyle(s.querySelector('.tray')).display, rows: R(s.querySelector('.rows')), vw: innerWidth};"]]],
]
# the deck's patterns: a five-card recap, and the lines a figure lights, measured on the compiled deck
PATTERN_DECK = r"""
(function () {
  var out = {errors: [], recap: null, lit: [], tight: []};
  window.addEventListener('error', function (e) { out.errors.push(String(e.message)); });
  function R(e) { var r = e.getBoundingClientRect(); return {l: r.left, t: r.top, r: r.right, b: r.bottom}; }
  function pads(e) { var c = getComputedStyle(e); return {tag: e.tagName.toLowerCase(), cls: e.className, box: e.classList.contains('box') || e.classList.contains('call'),
                                                          pl: parseFloat(c.paddingLeft), pr: parseFloat(c.paddingRight)}; }
  window.addEventListener('load', function () {
    setTimeout(function () {
      try {
        var st = document.createElement('style');
        st.textContent = '*,*::before,*::after{animation:none!important;transition:none!important}';
        document.head.appendChild(st);
        var sb = document.getElementById('startBtn'); if (sb) { sb.click(); }
        out.vp = [innerWidth, innerHeight];
        var g = document.querySelector('.rc-grid[data-n="5"]');
        if (g) {
          var s = g.closest('.slide');
          [].forEach.call(document.querySelectorAll('.slide'), function (x) { x.classList.remove('active'); });
          s.classList.add('active'); void s.offsetHeight;
          out.recap = {grid: R(g), items: [].map.call(g.querySelectorAll('.rc-item'), R)};
        }
        var lines = [].slice.call(document.querySelectorAll('.copy [data-i]'));
        out.lit = lines.map(pads);
        [].forEach.call(document.querySelectorAll('.copy'), function (c) { if (c.querySelector('[data-i]')) { c.classList.add('tight'); } });
        out.tight = lines.map(pads);
      } catch (err) { out.errors.push(String(err && err.stack || err)); }
      var pre = document.createElement('pre'); pre.id = 'gbtest'; pre.textContent = JSON.stringify(out);
      document.body.appendChild(pre);
    }, 300);
  });
}());
"""


def patterns_part(exe, tmp):
    """2.63.2 item 19 (IGF slide review - every module had them, the course fixed each by hand): the shared patterns of the
    task engine and the recap, each measured in a real browser. a) the dashed bank under a sort says "Cards not placed"
    and goes after the check; b) the options not chosen stay readable (.8); c) a card or gap the check moved is amber
    AND has the right-answer green on its edge; d) five recap cards: 3 + 2, the last row centred; e) a line a figure lights
    keeps 10 px inside, `.copy.tight` opts out; f) a scenario's step in hand sits in the column of its folded steps."""
    print("\n-- 2.63.2: the engine's and the recap's shared patterns (IGF slide review)")
    os.makedirs(os.path.join(tmp, "pat"))
    c, md = tcm.new_course(os.path.join(tmp, "pat"), tcm.script(screens=PATTERNS), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {"t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "tasks")
    page = os.path.join(md, "tasks", "sc1_the_patterns.html")
    check("the pattern fixture page is built", code == 0 and os.path.isfile(page), out)
    r = drive(exe, page, PAT_PLAN, tmp, look=False, size=(1280, 800))
    check("no script error on the pattern page", not r.get("errors"), r.get("errors"))
    t = r.get("tray0") or {}
    check("a) every card placed, Check not yet pressed: the empty dashed bank says \"Cards not placed\"",
          t.get("chips") == 0 and t.get("attr") == "Cards not placed" and t.get("before") == '"Cards not placed"' and t.get("display") != "none", t)
    f = r.get("fix") or {}
    check("a) ... after Check, with nothing left in it, the bank is gone", f.get("tray") == "none", f)
    check("c) two cards moved to their place: the edge is the right-answer green (that of a right card), the wash stays amber, an amber bar on the left",
          f.get("nfixed") == 2 and f.get("fb") == f.get("rb") and f.get("fbg") != f.get("rbg") and f.get("fs", "none") != "none"
          and f.get("rb", "").startswith("rgb(") and f.get("fb", "").startswith("rgb("), f)
    check("b) the options not chosen after the check: opacity .8 or more (was .55)", (r.get("dim") or [0]) and min(r.get("dim") or [0]) >= 0.8, r.get("dim"))
    for k, when in (("sc1", "step 2 open"), ("sc2", "the last step checked")):
        q = r.get(k) or {}
        a, b = q.get("a") or {}, q.get("b") or {}
        check("f) a scenario, %s: it has the left and right edge of the folded step above it (one centred column)" % when,
              a and b and "past" in q["cls"][0] and "past" not in q["cls"][1] and abs(a["l"] - b["l"]) <= 1 and abs(a["r"] - b["r"]) <= 1, q)
    g = r.get("gap") or {}
    check("c) a gap the check filled with the right words: green edge as a right gap's, amber bar kept",
          g.get("fb") == g.get("rb") and g.get("fb", "").startswith("rgb(") and g.get("fs", "none") != "none", g)
    m0, m1 = r.get("many0") or {}, r.get("many1") or {}
    check("a) eight places beside the bank (data-many): the empty bank, in its right-hand column, says \"Cards not placed\" there too",
          m0.get("many") == "1" and m0.get("label") == '"Cards not placed"' and m0["tray"]["l"] > m0["rows"]["r"] - 1, m0)
    check("a) ... after Check the bank is gone and the places take the whole width - not the left half with the right half blank",
          m1.get("tray") == "none" and m1.get("rows", {}).get("r", 0) - m1.get("rows", {}).get("l", 0) >= 0.9 * m1.get("vw", 9e9), m1)
    js = io.open(os.path.join(HERE, "..", "..", "..", "course-task-ux", "assets", "gb_answer.js"), encoding="utf-8").read()
    check("a) the bank's words are in the engine's three languages (en, lv, ru)", js.count("trayEmpty:") == 3, js.count("trayEmpty:"))
    # 2.63.3 (item 9 - IGF M02 check m01 / m06: passed in the busy 2.63.2 build, failed on a quiet PC)
    check("2.63.3 the leaders are placed again once the course font is in and kit.js has laid it out (fonts.ready, two "
          "frames, and on every font load)", "D.fonts.addEventListener('loadingdone', function () { settled(replace); })" in js
          and "placeParts(q.sec);\n    settled(replace);" in js and "raf(function () { raf(fn); })" in js)
    rv = io.open(os.path.join(HERE, "..", "..", "..", "course-module-ux", "measure", "scripts", "review_sheets.mjs"), encoding="utf-8").read()
    check("... and review_sheets.mjs judges them only after the same (fonts.ready, two frames)",
          "judged once the course font is in and laid out" in rv and "document.fonts.ready : Promise.resolve()).then(" in rv
          and rv.index("judged once the course font is in") < rv.index("__rv.leaders()')) failures.push"))

    # the deck: a five-card recap and the stepped lines
    os.makedirs(os.path.join(tmp, "patd"))
    screens = json.loads(json.dumps(tcm.SCREENS[:6])) + [
        {"id": "s05", "kind": "slide", "recap": True, "title": "What to take away", "visual_kind": "none", "text": M05_S11, "minutes": 2}
    ] + json.loads(json.dumps(tcm.SCREENS[6:]))
    c, md = tcm.new_course(os.path.join(tmp, "patd"), tcm.script(screens=screens), build=False)
    tcm.cs.save(os.path.join(c, "working_claude", "script", "M01.build.json"), {"module": 1, "screens": {
        "s01": {"figure": "assets/img/ship.jpg"}, "s02": {"figure": "assets/fig/scale.svg"}, "s03": {"figure": "ga.html"},
        "s04": {"figure": "hull.svg", "dark": True, "declined_3d": "the fixture's hull section stays a flat drawing"}, "t01": {"try_tablet": False}}})
    code, out = tcm.run(tcm.COMPILE, c, "--module", "1", "--only", "deck")
    dpage = os.path.join(md, "presentation", "index.html")
    check("the pattern deck is built", code == 0 and os.path.isfile(dpage), out[-600:])
    for size in ((1280, 800), (1024, 768)):
        r = deck_fit(exe, dpage, tmp, size, js=PATTERN_DECK)
        tag = "%dx%d" % size
        check("%s: no script error, measured at the size asked for" % tag, not r.get("errors") and r.get("vp") == list(size), r.get("errors") or r.get("vp"))
        rc = r.get("recap") or {}
        it, gd = rc.get("items") or [], rc.get("grid") or {}
        if len(it) == 5:
            top1 = [x["t"] for x in it[:3]]
            top2 = [x["t"] for x in it[3:]]
            mid = ((min(x["l"] for x in it[3:]) + max(x["r"] for x in it[3:])) / 2.0, (gd["l"] + gd["r"]) / 2.0)
            ws = [x["r"] - x["l"] for x in it]
            check("d) %s: five recap cards sit 3 + 2 - the last two centred under the three, every card the same width, no empty cell" % tag,
                  max(top1) - min(top1) < 1 and max(top2) - min(top2) < 1 and min(top2) > max(x["b"] for x in it[:3]) - 1
                  and abs(mid[0] - mid[1]) <= 2 and max(ws) - min(ws) <= 1, rc)
        else:
            check("d) %s: the five-card recap is on the slide" % tag, False, rc)
        lit, tight = r.get("lit") or [], r.get("tight") or []
        plain = [x for x in lit if not x["box"] and x["tag"] != "li"]
        check("e) %s: a line a figure lights has 10 px inside on both sides (at rest) - and a bullet line 10 px on the right" % tag,
              plain and all(x["pl"] == 10 and x["pr"] == 10 for x in plain) and all(x["pr"] == 10 for x in lit if x["tag"] == "li" and not x["box"]), lit)
        check("e) %s: `.copy.tight` opts the slide out - no inner padding" % tag,
              plain and all(x["pl"] == 0 and x["pr"] == 0 for x in tight if not x["box"] and x["tag"] != "li"), tight)


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
        blind_part(exe, page, tmp)
        review_part(exe, tmp)
        deck_fit_part(exe, tmp)
        inset_part(exe, tmp)
        inset_empty_part(exe, tmp)
        inset_under_part(exe, tmp)
        strip_contrast_part(exe, tmp)
        push_button_part(exe, tmp)
        ship_plan_part(exe, tmp)
        figures_part(exe, tmp)
        fixes_part(exe, tmp)
        picture_part(exe, tmp)
        corner_part(exe, tmp)
        last_parts_part(exe, tmp)
        lockstep_part(exe, tmp)
        steps_part(exe, tmp)
        patterns_part(exe, tmp)
        team_part(exe, tmp)
        language_part(exe, tmp)
        deck_language_part(exe, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
