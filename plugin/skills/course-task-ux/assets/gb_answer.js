/* gb_answer.js - the one shared engine of every compiled trainee task page (self-check, module check, final).
   Promoted from the IGF pilot's m01_tasks.js (2.34.0), so every module answers the same way (L38, L42).
   Plain ES5, no network. Copied into each module's assets/ by design_system.py, never edited there.

   A compiled page (course-factory/compile/scripts/compile_module.py) is only its questions as markup:
     <body data-code="SC1" data-title="..." data-pass="0">      data-pass: the pass mark in %, 0 = a self-check
     <section class="scr" data-script="q01" data-mech="hotspot" [data-multi="1"]> ... </section>
   One question per screen; choose, tap the picture, drag-and-drop with a tap-then-tap alternative, a dial.
   A question is one or more parts (.part - none: the whole screen is one part), each answered and checked once:
   a scenario's steps, the incident's order and then where it should have stopped. A part holds groups:
     choose  a .cg (or the screen's .opt / .hot): one, or all that are right (data-multi="1")
     place   .chip into .zone, back into .tray; data-need="slots": every slot filled, a card may stay in the tray
     dial    .dial: a value from data-lo to data-hi in data-step, set by dragging or with - and +
     stop    a part with data-kind="stop": tap one card of the part before it

   The answers are NOT in the page: every answer element carries data-key = gbKey(screen id, its text, value)
   and the page grades by working out the key of what the trainee did (classroom-system.json task_page.answer_keys).
   Value of a key:  choose / tap the picture / a gap / a reason / a step's action / a line of the document /
                    the faulty part / a card that belongs in the plan / the moment to stop: 1 right, 0 wrong
                    (a .cg's data-val instead of 1: operate the panel - the control's name)
                    put in order: the place, 1, 2, 3 ...  (a card that also says right or wrong - build the plan,
                    rebuild the incident - carries its place in data-place, the same key: 0 = stays out)
                    match: the partner's text (the left side the right side belongs to)
                    sort into groups: the group's name
                    label the drawing: the id of the place on the drawing
                    set the value: the unit, value - data-key lists one key per accepted step

   The classroom: the result is reported once - parent.postMessage({type: 'gb-task-done', code, title, ok, total,
   head, items, answered, of, timeout: true|false}); the instructor's timer {type: 'gb-timer'} is heard, and at 0
   what was done is marked and reported with timeout: true. "Start again" exists only outside the classroom frame
   (window.parent === window): inside it, one opening gives one result.
   The words on the controls are in the page's language (<html lang>: en, lv, ru - LANG below); a page may still
   override any of them with window.GB_ANSWER_TEXT. */
(function () {
  'use strict';
  var D = document, W = window;

  /* ---------------------------------------------------------------- words */
  var T = {
    tryFirst: 'Try your tablet first', startSelf: 'Start the self-check', moduleCheck: 'Module check',
    startCheck: 'Start the check', question: 'Question {n} of {of}', soFar: '{n} right so far',
    check: 'Check', next: 'Next', seeScore: 'See my score', result: 'Your result',
    correct: 'Correct.', notQuiteChoice: 'Not quite – the right answer is marked.',
    notQuitePlace: 'Not quite – the amber ones were moved to where they belong.',
    notQuiteValue: 'Not quite – the green band shows the values that are right.',
    notQuiteMissed: 'Not quite – what you missed is outlined in green.', alsoRight: 'Also right', alsoWrong: 'Also wrong',
    goOn: 'Go on', decimal: '.',
    teamRole: 'You are the {role}', teamOne: 'One answer for the whole team', handedIn: 'Handed in by {by} for {team}',
    got: 'You got {ok} of {total} right.', timeUp: ' The time was up.',
    passNote: 'Pass mark {pass} % – {need} of {total} right. This shows what to review. It is not a grade.',
    passed: 'PASSED', notPassed: 'NOT PASSED'
  };
  /* the course language (L19) - the page's <html lang>; PROVISIONAL (2.40.0), written by Claude, to be checked by a
     native speaker: course-factory/compile/TRANSLATIONS_REVIEW.md. The message to the classroom keeps 'PASSED' /
     'NOT PASSED' - a code, not a word on the screen. */
  var LANG = {
    lv: {
      tryFirst: 'Vispirms izmēģini planšeti', startSelf: 'Sākt paškontroli', moduleCheck: 'Moduļa pārbaude',
      startCheck: 'Sākt pārbaudi', question: '{n}. jautājums no {of}', soFar: 'Pagaidām pareizi: {n}',
      check: 'Pārbaudīt', next: 'Tālāk', seeScore: 'Mans rezultāts', result: 'Tavs rezultāts',
      correct: 'Pareizi.', notQuiteChoice: 'Ne gluži – pareizā atbilde ir atzīmēta.',
      notQuitePlace: 'Ne gluži – dzeltenās kartītes ir pārliktas savās vietās.',
      notQuiteValue: 'Ne gluži – zaļā josla rāda pareizās vērtības.',
      notQuiteMissed: 'Ne gluži – tas, ko palaidi garām, ir apvilkts zaļā krāsā.', alsoRight: 'Arī pareizi', alsoWrong: 'Arī kļūdaini',
      goOn: 'Turpināt', decimal: ',',
      teamRole: 'Tava loma: {role}', teamOne: 'Viena atbilde visai komandai', handedIn: '{team} atbildi iesniedza: {by}',
      got: 'Pareizi: {ok} no {total}.', timeUp: ' Laiks beidzās.',
      passNote: 'Ieskaites slieksnis {pass} % – {need} no {total} pareizi. Tas rāda, ko atkārtot. Tā nav atzīme.',
      passed: 'IESKAITĪTS', notPassed: 'NAV IESKAITĪTS'
    },
    ru: {
      tryFirst: 'Сначала попробуй планшет', startSelf: 'Начать самопроверку', moduleCheck: 'Проверка по модулю',
      startCheck: 'Начать проверку', question: 'Вопрос {n} из {of}', soFar: 'Пока правильно: {n}',
      check: 'Проверить', next: 'Далее', seeScore: 'Мой результат', result: 'Твой результат',
      correct: 'Правильно.', notQuiteChoice: 'Не совсем – правильный ответ отмечен.',
      notQuitePlace: 'Не совсем – жёлтые карточки перенесены на свои места.',
      notQuiteValue: 'Не совсем – зелёная полоса показывает правильные значения.',
      notQuiteMissed: 'Не совсем – пропущенное обведено зелёным.', alsoRight: 'Тоже верно', alsoWrong: 'Тоже ошибка',
      goOn: 'Дальше', decimal: ',',
      teamRole: 'Твоя роль: {role}', teamOne: 'Один ответ на всю команду', handedIn: 'Ответ команды {team} сдал(а): {by}',
      got: 'Правильно: {ok} из {total}.', timeUp: ' Время вышло.',
      passNote: 'Проходной балл {pass} % – {need} из {total} правильно. Это показывает, что повторить. Это не оценка.',
      passed: 'ЗАЧТЕНО', notPassed: 'НЕ ЗАЧТЕНО'
    }
  };
  (function () {
    var k, l = LANG[(D.documentElement.getAttribute('lang') || 'en').slice(0, 2).toLowerCase()] || {}, o = W.GB_ANSWER_TEXT || {};
    for (k in l) { if (l.hasOwnProperty(k)) { T[k] = l[k]; } }
    for (k in o) { if (o.hasOwnProperty(k)) { T[k] = o[k]; } }
  }());
  function say(k, v) {
    return String(T[k]).replace(/\{(\w+)\}/g, function (m, n) { return (v && v[n] !== undefined) ? v[n] : m; });
  }

  /* ---------------------------------------------------------------- the classroom */
  var CR = (function () {
    var sent = false;
    return {
      inFrame: !(window.parent === window),
      stop: function () { sent = true; },            /* the team's answer was handed in from another tablet */
      send: function (r) {
        if (sent) { return; }
        sent = true;
        var msg = { type: 'gb-task-done', code: r.code, title: r.title, ok: r.ok, total: r.total,
          head: r.head, items: r.items, answered: r.answered, of: r.of, timeout: r.timeout === true };
        if (TEAM.handsIn()) {                        /* one answer for the team: the classroom records it for every member */
          var t = { scope: 'team', team: TEAM.team.name, by: TEAM.team.me }, k;
          for (k in t) { if (t.hasOwnProperty(k)) { msg[k] = t[k]; } }
        }
        try { W.parent.postMessage(msg, '*'); } catch (e) { /* opened on its own - no classroom to tell */ }
      },
      onTimer: function (fn) {
        W.addEventListener('message', function (e) {
          var d = e && e.data;
          if (!d || typeof d !== 'object' || d.type !== 'gb-timer') { return; }
          var rem = d.remaining;
          if (typeof rem !== 'number' && d.endsAt) { rem = d.endsAt - new Date().getTime(); }
          if (typeof rem === 'number') { fn(rem); }
        }, false);
      }
    };
  }());
  /* ---------------------------------------------------------------- a team task (classroom-system.json team_task) */
  /* <meta name="task-mode" content="team">: the classroom sends the team shortly after the page opens -
     {type: 'gb-team', team: {name, colour, members, me, role}} - and it is shown at the top, as large as the question.
     No team within about 2 seconds: the class has no teams and the task runs as an individual one (it never waits).
     task-scope team: the first tablet of the team to finish hands in the one answer, with scope: 'team' (and team, by);
     when another member's tablet has handed in, the classroom says so - {type: 'gb-team-done', by, team} - and this
     page shows "Handed in by ... for Team A" and sends nothing. task-scope member: everyone answers and reports as
     usual. Any team size; a role never locks anyone out - every member reads and answers the whole task. */
  var TEAM = (function () {
    function meta(n) { var m = D.querySelector('meta[name="' + n + '"]'); return m ? m.getAttribute('content') || '' : ''; }
    var o = { on: meta('task-mode') === 'team', scope: meta('task-scope') === 'member' ? 'member' : 'team',
      team: null, alone: false, done: null, onDone: null };
    o.handsIn = function () { return !!(o.on && o.team && o.scope === 'team'); };
    function show() {
      var bar = D.getElementById('teamBar'), t = o.team;
      if (!bar) { return; }
      D.getElementById('teamName').textContent = String(t.name || '');
      D.getElementById('teamRole').textContent = t.role ? say('teamRole', { role: String(t.role) }) : '';
      D.getElementById('teamNote').textContent = o.scope === 'team' ? say('teamOne') : '';
      if (/^#[0-9a-f]{3,8}$/i.test(t.colour || '')) { bar.style.borderLeftColor = t.colour; }
      bar.removeAttribute('hidden');
    }
    if (o.on) {
      W.addEventListener('message', function (e) {
        var d = e && e.data;
        if (!d || typeof d !== 'object') { return; }
        if (d.type === 'gb-team' && d.team && typeof d.team === 'object') { o.team = d.team; show(); }
        if (d.type === 'gb-team-done' && o.scope === 'team' && !o.done) { o.done = d; if (o.onDone) { o.onDone(d); } }
      }, false);
      setTimeout(function () { if (!o.team) { o.alone = true; } }, 2000);     /* no teams in this class */
    }
    return o;
  }());

  /* the hidden Back link - the Android Back button clicks it; it only steps back, never to an instructor page */
  (function () {
    var back = D.querySelector('.gbt-topback');
    if (!back) { return; }
    back.addEventListener('click', function (e) {
      e.preventDefault();
      try { if (W.history.length > 1) { W.history.back(); } } catch (x) { /* nothing to go back to */ }
    }, false);
  }());

  /* ---------------------------------------------------------------- helpers */
  function $(s, r) { return (r || D).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || D).querySelectorAll(s)); }
  function norm(s) { return String(s).replace(/\s+/g, ' ').replace(/^ | $/g, ''); }
  function txt(el) { return norm(el.textContent); }
  /* through the class attribute, never .className - a drawing's SVG elements have a read-only className */
  function cls(el) { return (el && el.getAttribute && el.getAttribute('class')) || ''; }
  function has(el, c) { return (' ' + cls(el) + ' ').indexOf(' ' + c + ' ') >= 0; }
  function add(el, c) { if (el && !has(el, c)) { el.setAttribute('class', (cls(el) ? cls(el) + ' ' : '') + c); } }
  function del(el, c) {
    if (el && has(el, c)) { el.setAttribute('class', norm((' ' + cls(el) + ' ').replace(' ' + c + ' ', ' '))); }
  }
  function each(list, fn) { for (var i = 0; i < list.length; i++) { fn(list[i], i); } }

  /* FNV-1a over "<screen id>|<text>|<value>" - the same function as the factory's gb_key */
  function imul(a, b) {
    var ah = (a >>> 16) & 0xffff, al = a & 0xffff, bh = (b >>> 16) & 0xffff, bl = b & 0xffff;
    return ((al * bl) + (((ah * bl + al * bh) << 16) >>> 0) | 0);
  }
  function gbKey(id, text, value) {
    var s = unescape(encodeURIComponent(id + '|' + norm(text) + '|' + value)), h = 0x811c9dc5, i;
    for (i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = imul(h, 0x01000193) >>> 0; }
    return ('0000000' + h.toString(16)).slice(-8);
  }
  function keyOf(el) { return (el.getAttribute('data-key') || '').toLowerCase(); }

  /* ---------------------------------------------------------------- page */
  var body = D.body;
  var CODE = body.getAttribute('data-code') || '';
  var TITLE = body.getAttribute('data-title') || '';
  var PASS = parseInt(body.getAttribute('data-pass') || '0', 10);   /* % ; 0 = no pass mark */
  var inFrame = CR.inFrame;
  var partEl = $('#partLbl'), gotEl = $('#gotLbl'), barEl = $('#barFill');
  var dock = $('#dock'), go = $('#go');
  var tryScr = $('#tryScr'), introScr = $('#introScr'), resScr = $('#resScr');
  var qs = [], cur = -1, started = false, ended = false, reported = false, okCount = 0;
  var shown = {}, lastTouch = 0;

  /* ---------------------------------------------------------------- the hand that shows a gesture once */
  var handEl = null, ghostEl = null, handTimers = [];
  function later(ms, fn) { handTimers.push(setTimeout(fn, ms)); }
  function killHand() {
    var i;
    for (i = 0; i < handTimers.length; i++) { clearTimeout(handTimers[i]); }
    handTimers = [];
    if (handEl && handEl.parentNode) { handEl.parentNode.removeChild(handEl); }
    if (ghostEl && ghostEl.parentNode) { ghostEl.parentNode.removeChild(ghostEl); }
    handEl = ghostEl = null;
  }
  function centre(el) { var r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height }; }
  function put(el, x, y) { el.style.transform = 'translate(' + Math.round(x) + 'px,' + Math.round(y) + 'px)'; }
  function makeHand() {
    var h = D.createElement('div');
    h.className = 'hand';
    h.innerHTML = '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M18 24V10a3 3 0 0 1 6 0v12l11 3a4 4 0 0 1 3 4l-2 11a4 4 0 0 1-4 3H22a4 4 0 0 1-3-1L9 31a3 3 0 0 1 4-4l5 4z" fill="#fff" stroke="#0A2463" stroke-width="2.4" stroke-linejoin="round"/></svg>';
    D.body.appendChild(h);
    return h;
  }
  function ripple(x, y) {
    var r = D.createElement('i');
    r.className = 'rip';
    r.style.left = x + 'px';
    r.style.top = y + 'px';
    D.body.appendChild(r);
    setTimeout(function () { if (r.parentNode) { r.parentNode.removeChild(r); } }, 700);
  }
  /* the fingertip sits at (24, 8) of the 56 px hand */
  function demoTap(pt) {
    killHand();
    handEl = makeHand();
    put(handEl, pt.x - 26, pt.y - 9);
    handEl.style.opacity = '1';
    later(450, function () { add(handEl, 'press'); ripple(pt.x, pt.y); });
    later(850, function () { del(handEl, 'press'); });
    later(1250, function () { if (handEl) { handEl.style.opacity = '0'; } });
    later(1700, killHand);
  }
  function demoDrag(a, b) {
    killHand();
    handEl = makeHand();
    ghostEl = D.createElement('div');
    ghostEl.className = 'dghost';
    var gw = Math.min(a.w, 260), gh = Math.min(a.h, 62);
    ghostEl.style.width = gw + 'px';
    ghostEl.style.height = gh + 'px';
    D.body.appendChild(ghostEl);
    put(ghostEl, a.x - gw / 2, a.y - gh / 2);
    put(handEl, a.x - 26, a.y - 9);
    handEl.style.opacity = '1';
    later(450, function () { add(handEl, 'press'); ghostEl.style.opacity = '.9'; });
    later(800, function () {
      put(ghostEl, b.x - gw / 2, b.y - gh / 2);
      put(handEl, b.x - 26, b.y - 9);
    });
    later(1850, function () { del(handEl, 'press'); ghostEl.style.opacity = '0'; });
    later(2250, function () { if (handEl) { handEl.style.opacity = '0'; } });
    later(2700, killHand);
  }
  D.addEventListener('touchstart', killHand, false);
  D.addEventListener('mousedown', killHand, false);

  /* ---------------------------------------------------------------- drag and drop */
  function pop(el) {
    add(el, 'snap');
    setTimeout(function () { del(el, 'snap'); }, 320);
  }
  function select(q, chip) {
    each(q.chips, function (c) { del(c, 'sel'); });
    q.sel = chip || null;
    if (chip) { add(chip, 'sel'); add(q.sec, 'armed'); } else { del(q.sec, 'armed'); }
  }
  function moveChip(q, chip, zone) {
    if (zone === chip.parentNode) { return; }
    if (zone.getAttribute('data-cap') === '1') {
      var occ = $('.chip', zone);
      if (occ && occ !== chip) { q.tray.appendChild(occ); pop(occ); }
    }
    zone.appendChild(chip);
    pop(chip);
    if (q.onchange) { q.onchange(); }
  }
  function zoneAt(q, x, y) {
    var el = D.elementFromPoint(x, y), z = null;
    while (el && el !== q.sec && el !== D.body) {
      if (el.nodeType === 1 && (has(el, 'zone') || has(el, 'tray'))) { z = el; break; }
      el = el.parentNode;
    }
    return z;
  }
  function attachDrag(q, chip) {
    var st = null;
    function pos(e) {
      var t = (e.changedTouches && e.changedTouches[0]) || (e.touches && e.touches[0]) || e;
      return { x: t.clientX, y: t.clientY };
    }
    function clean() {
      if (st && st.ghost && st.ghost.parentNode) { st.ghost.parentNode.removeChild(st.ghost); }
      del(chip, 'lifted');
      each(q.zones, function (z) { del(z, 'over'); });
      if (q.tray) { del(q.tray, 'over'); }
      D.removeEventListener('mousemove', onMove, false);
      D.removeEventListener('mouseup', onUp, false);
      st = null;
    }
    function tap() {
      if (q.sel === chip) { select(q, null); return; }
      var par = chip.parentNode;
      if (q.sel && has(par, 'zone')) { moveChip(q, q.sel, par); select(q, null); return; }
      select(q, chip);
    }
    function onMove(e) {
      if (!st) { return; }
      var p = pos(e), dx = p.x - st.x, dy = p.y - st.y, z;
      if (!st.drag) {
        if (dx * dx + dy * dy < 64) { return; }
        st.drag = true;
        var r = chip.getBoundingClientRect();
        st.ox = st.x - r.left; st.oy = st.y - r.top;
        st.ghost = chip.cloneNode(true);
        st.ghost.removeAttribute('data-key');
        st.ghost.removeAttribute('data-script-field');
        st.ghost.className = 'chip ghost';
        st.ghost.style.width = r.width + 'px';
        D.body.appendChild(st.ghost);
        add(chip, 'lifted');
        select(q, null);
      }
      if (e.cancelable && e.type === 'mousemove') { e.preventDefault(); }
      st.ghost.style.left = (p.x - st.ox) + 'px';
      st.ghost.style.top = (p.y - st.oy) + 'px';
      z = zoneAt(q, p.x, p.y);
      each(q.zones, function (zz) { del(zz, 'over'); });
      del(q.tray, 'over');
      if (z) { add(z, 'over'); }
    }
    function onUp(e) {
      if (!st) { return; }
      var p = pos(e), z;
      if (!st.drag) { clean(); tap(); return; }
      z = zoneAt(q, p.x, p.y);
      clean();
      if (z) { moveChip(q, chip, z); }
    }
    function onTouchEnd(e) { if (e.cancelable) { e.preventDefault(); } onUp(e); }
    function begin(e, isTouch) {
      if (q.locked || st) { return; }
      var p = pos(e);
      st = { x: p.x, y: p.y, drag: false, ghost: null, ox: 0, oy: 0 };
      if (!isTouch) {
        D.addEventListener('mousemove', onMove, false);
        D.addEventListener('mouseup', onUp, false);
      }
    }
    chip.addEventListener('touchstart', function (e) {
      lastTouch = new Date().getTime();
      if (e.cancelable) { e.preventDefault(); }
      if (q.locked && q.tapLocked) { q.tapLocked(chip); return; }     /* a placed card tapped as an answer (stop) */
      begin(e, true);
    }, false);
    chip.addEventListener('touchmove', onMove, false);
    chip.addEventListener('touchend', onTouchEnd, false);
    chip.addEventListener('touchcancel', function () { clean(); }, false);
    chip.addEventListener('mousedown', function (e) {
      if (e.button !== 0 || new Date().getTime() - lastTouch < 700) { return; }
      if (q.locked && q.tapLocked) { q.tapLocked(chip); return; }
      begin(e, false);
      e.preventDefault();
    }, false);
    chip.addEventListener('click', function (e) { e.stopPropagation(); }, false);
  }
  function bindPlacement(q) {
    each(q.chips, function (c) { attachDrag(q, c); });
    each(q.zones.concat(q.tray ? [q.tray] : []), function (z) {
      z.addEventListener('click', function () {
        if (q.locked || !q.sel) { return; }
        moveChip(q, q.sel, z);
        select(q, null);
      }, false);
    });
  }
  function placed(g) { var n = 0; each(g.chips, function (c) { if (c.parentNode !== g.tray) { n++; } }); return n; }
  function slotsFull(g) { var n = 0; each(g.zones, function (z) { if ($('.chip', z)) { n++; } }); return n === g.zones.length; }
  function zoneValue(z) { return z ? norm(z.getAttribute('data-val') || '') : ''; }
  /* a card's place: data-place when the card also says right or wrong in data-key (build the plan, the incident) */
  function placeKey(c) { return (c.getAttribute('data-place') || c.getAttribute('data-key') || '').toLowerCase(); }
  function belongs(g, c) { return keyOf(c) === gbKey(g.id, txt(c), 1); }
  function chipGood(g, c) {
    var z = c.parentNode;
    if (z === g.tray) { return g.need === 'slots' && !belongs(g, c); }     /* a card that does not belong stays out */
    return has(z, 'zone') && gbKey(g.id, txt(c), zoneValue(z)) === placeKey(c);
  }
  function rightZone(g, c) {
    var i;
    for (i = 0; i < g.zones.length; i++) {
      if (gbKey(g.id, txt(c), zoneValue(g.zones[i])) === placeKey(c)) { return g.zones[i]; }
    }
    return null;
  }

  /* ---------------------------------------------------------------- questions */
  /* the element whose words and key an item stands for: itself, or (the faulty part's "This is the fault"
     button) the keyed element beside it */
  function keyEl(it) { return it.hasAttribute('data-key') ? it : ($('[data-key]', it.parentNode) || it); }
  function itemRight(g, it) { var k = keyEl(it); return keyOf(k) === gbKey(g.id, txt(k), g.val); }

  function mkChoose(q, box, multi, val, items) {
    var g = { type: 'choose', q: q, id: q.id, box: box, multi: multi, val: val, picked: [], locked: false,
      items: items || $$('.opt, .hot', box) };
    if (!items) { each(g.items, function (it) { it.addEventListener('click', function () { pick(g, it); }, false); }); }
    g.picked = g.items.filter(function (o) { return has(o, 'sel'); });      /* a panel control already in a position */
    return g;
  }
  /* operate the panel: the control's little figure-kit drawing follows the position chosen */
  function kitSet(box, v) {
    var s = $('svg.csym', box), f = s && s.__kit;
    del(box, 'unset');
    if (f && f.parts.c) { f.set(f.parts.c, parseFloat(v)); }
  }
  function pick(g, it) {
    if (g.locked) { return; }
    if (g.multi) {
      if (has(it, 'sel')) { del(it, 'sel'); } else { add(it, 'sel'); }
      g.picked = g.items.filter(function (o) { return has(o, 'sel'); });
    } else {
      each(g.items, function (o) { del(o, 'sel'); });
      add(it, 'sel');
      g.picked = [it];
    }
    g.q.touched = true;
    if (g.onpick) { g.onpick(it); }
    if (it.hasAttribute('data-kv')) { kitSet(g.box, it.getAttribute('data-kv')); }
    syncFor(g.q.sec);
    refresh();
  }
  /* compare: the figures of a column show what its name button shows - chosen, right, wrong */
  function syncFor(root) {
    each($$('.cmp [data-for]', root), function (c) {      /* only the compare table - a drawing may use data-for too */
      var it = D.getElementById(c.getAttribute('data-for'));
      each(['sel', 'right', 'wrong', 'dim'], function (k) { if (it && has(it, k)) { add(c, k); } else { del(c, k); } });
    });
  }
  function mkPlace(q, part) {
    var g = { type: 'place', q: q, id: q.id, sec: part, chips: $$('.chip', part), zones: $$('.zone', part),
      tray: $('.tray', part), need: part.getAttribute('data-need') || 'all', locked: false, sel: null };
    g.onchange = function () { q.touched = true; refresh(); };
    bindPlacement(g);
    return g;
  }

  /* set the value: drag along the track, tap it, or step with - and + ; the number is shown large */
  function mkDial(q, el) {
    var g = { type: 'dial', q: q, id: q.id, el: el, k: -1, locked: false };
    var lo = parseFloat(el.getAttribute('data-lo')), hi = parseFloat(el.getAttribute('data-hi'));
    var step = parseFloat(el.getAttribute('data-step')), dec = parseInt(el.getAttribute('data-dec') || '0', 10);
    var S = Math.pow(10, dec), LO = Math.round(lo * S), ST = Math.round(step * S), n = Math.round((hi - lo) / step);
    var track = $('.dial-track', el), thumb = $('.dial-thumb', el), fill = $('.dial-fill', el), out = $('.dial-val', el);
    var drag = false;
    g.unit = el.getAttribute('data-unit') || '';
    g.keys = keyOf(el).split(/\s+/);
    g.n = n;
    g.thumb = thumb;
    g.track = track;
    g.at = function (k) { return ((LO + k * ST) / S).toFixed(dec); };
    g.good = function (k) { return g.keys.indexOf(gbKey(g.id, g.unit, g.at(k))) >= 0; };
    g.shown = function (k) { return g.at(k).replace('-', '−').replace('.', T.decimal); };
    g.paint = function () {
      var p = 100 * Math.max(g.k, 0) / n;
      thumb.style.left = p + '%';
      fill.style.width = p + '%';
      out.textContent = g.k < 0 ? '–' : g.shown(g.k);
    };
    g.set = function (k) {
      if (g.locked) { return; }
      g.k = Math.max(0, Math.min(n, k));
      q.touched = true;
      g.paint();
      refresh();
    };
    function at(e) {
      var t = (e.changedTouches && e.changedTouches[0]) || (e.touches && e.touches[0]) || e, r = track.getBoundingClientRect();
      return Math.round((t.clientX - r.left) / r.width * n);
    }
    track.addEventListener('touchstart', function (e) {
      if (g.locked) { return; }
      lastTouch = new Date().getTime();
      if (e.cancelable) { e.preventDefault(); }
      drag = true;
      g.set(at(e));
    }, false);
    track.addEventListener('touchmove', function (e) { if (drag) { if (e.cancelable) { e.preventDefault(); } g.set(at(e)); } }, false);
    track.addEventListener('touchend', function () { drag = false; }, false);
    track.addEventListener('mousedown', function (e) {
      if (g.locked || e.button !== 0 || new Date().getTime() - lastTouch < 700) { return; }
      drag = true;
      g.set(at(e));
      e.preventDefault();
    }, false);
    D.addEventListener('mousemove', function (e) { if (drag) { g.set(at(e)); } }, false);
    D.addEventListener('mouseup', function () { drag = false; }, false);
    $('.dial-minus', el).addEventListener('click', function () { g.set(Math.max(g.k, 0) - 1); }, false);
    $('.dial-plus', el).addEventListener('click', function () { g.set(Math.max(g.k, 0) + 1); }, false);
    g.paint();
    return g;
  }

  /* complete the sentence: the gap tapped (or the first empty one) shows its choices; a choice fills the gap */
  function wireGaps(p) {
    var gaps = $$('.gap', p.el);
    if (!gaps.length) { return; }
    function act(i) {
      each(gaps, function (x, j) { if (j === i) { add(x, 'act'); } else { del(x, 'act'); } });
      each(p.groups, function (g, j) { if (j === i) { add(g.box, 'act'); } else { del(g.box, 'act'); } });
    }
    each(gaps, function (x, i) {
      x.addEventListener('click', function () { if (p.groups[i] && !p.groups[i].locked) { act(i); } }, false);
    });
    each(p.groups, function (g, i) {
      g.gap = gaps[i];
      g.onpick = function (it) {
        var j, nx = -1;
        gaps[i].textContent = txt(it);
        add(gaps[i], 'full');
        for (j = 1; j <= gaps.length && nx < 0; j++) { if (!p.groups[(i + j) % gaps.length].picked.length) { nx = (i + j) % gaps.length; } }
        if (nx >= 0) { act(nx); }
      };
    });
    act(0);
  }

  function mkPart(q, el, i) {
    var p = { q: q, el: el, i: i, kind: el.getAttribute('data-kind') || '', groups: [], done: false, ok: false };
    if (p.kind === 'stop') { return p; }                   /* its cards are the part's before it - made when it opens */
    var cgs = $$('.cg', el);
    if (cgs.length) {
      each(cgs, function (b) { p.groups.push(mkChoose(q, b, b.getAttribute('data-multi') === '1', b.getAttribute('data-val') || '1')); });
    } else if ($('.opt, .hot', el)) {
      p.groups.push(mkChoose(q, el, q.multi || el.getAttribute('data-multi') === '1', '1'));
    }
    if ($('.chip', el)) { p.groups.push(mkPlace(q, el)); }
    each($$('.dial', el), function (d) { p.groups.push(mkDial(q, d)); });
    /* compare: a figure in a column chooses that column */
    each($$('.cmp [data-for]', el), function (c) {
      c.addEventListener('click', function () { var it = D.getElementById(c.getAttribute('data-for')); if (it) { it.click(); } }, false);
    });
    /* find the fault: tap a part to check it - it turns over and stays turned over; checking is never wrong */
    each($$('.ff-look', el), function (b) {
      b.addEventListener('click', function () { add(b.parentNode, 'seen'); q.touched = true; }, false);
    });
    wireGaps(p);
    return p;
  }
  /* rebuild the incident, part two: the cards in their places are tapped to say where it should have stopped */
  function mkStop(q, before) {
    var place = null, g;
    each(before.groups, function (x) { if (x.type === 'place') { place = x; } });
    g = mkChoose(q, before.el, false, '1', place ? place.chips : []);
    g.rightCls = 'stopat';
    if (place) { place.tapLocked = function (chip) { pick(g, chip); }; }
    each(g.items, function (c) {
      c.addEventListener('click', function () { if (!place || place.locked) { pick(g, c); } }, false);
    });
    return g;
  }

  function mkQ(sec) {
    var q = { sec: sec, id: sec.getAttribute('data-script'), mech: sec.getAttribute('data-mech'),
      multi: sec.getAttribute('data-multi') === '1', done: false, ok: false, touched: false, k: 0, parts: [] };
    var ps = $$('.part', sec);
    q.text = txt($('[data-script-field="question"]', sec));
    q.why = $('.why', sec);
    q.vd = $('.vd', sec);
    each(ps.length ? ps : [sec], function (el, i) { q.parts.push(mkPart(q, el, i)); });
    if (ps.length) { add(ps[0], 'on'); }
    return q;
  }
  function groupAnswered(g) {
    if (g.type === 'choose') { return g.picked.length > 0; }
    if (g.type === 'dial') { return g.k >= 0; }
    return g.need === 'slots' ? slotsFull(g) : placed(g) === g.chips.length;
  }
  function groupTouched(g) {
    if (g.type === 'choose') { return g.picked.length > 0; }
    if (g.type === 'dial') { return g.k >= 0; }
    return placed(g) > 0;
  }
  function hasAnswer(p) {
    var ok = p.groups.length > 0;
    each(p.groups, function (g) { if (!groupAnswered(g)) { ok = false; } });
    return ok;
  }
  function anyAnswer(p) {
    var any = false;
    each(p.groups, function (g) { if (groupTouched(g)) { any = true; } });
    return any;
  }
  function gradeGroup(g) {
    var ok = true;
    if (g.type === 'choose') {
      each(g.items, function (it) { if (has(it, 'sel') !== itemRight(g, it)) { ok = false; } });
      return ok && g.picked.length > 0;
    }
    if (g.type === 'dial') { return g.k >= 0 && g.good(g.k); }
    each(g.chips, function (c) { if (!chipGood(g, c)) { ok = false; } });
    return ok;
  }
  function grade(p) {
    var ok = p.groups.length > 0;
    each(p.groups, function (g) { if (!gradeGroup(g)) { ok = false; } });
    return ok;
  }
  function lock(p) {
    add(p.el, 'locked');
    each(p.groups, function (g) { g.locked = true; if (g.type === 'place') { select(g, null); } });
  }
  function revealGroup(g, ok) {
    var bad = [], lo = -1, hi = -1, k, band;
    if (g.type === 'choose') {
      each(g.items, function (it) {
        /* choose all that are right: a right one the trainee did not choose is shown as one ("Also right"), outlined -
           never ticked as if it had been chosen (2.46.0; course-task-ux §0.5: a tick is what the trainee did right) */
        if (itemRight(g, it) && g.multi && !has(it, 'sel')) {
          add(it, 'missed');
          it.setAttribute('data-miss', say(g.q.mech === 'spot_the_error' ? 'alsoWrong' : 'alsoRight'));
        }
        else if (itemRight(g, it)) { add(it, g.rightCls || 'right'); }
        else if (has(it, 'sel')) { add(it, 'wrong'); }
        else if (has(it, 'opt')) { add(it, 'dim'); }
      });
      if (!ok) { each(g.picked, function (it) { if (!itemRight(g, it)) { add(it, 'shake'); } }); }
      if (g.gap) {                                       /* the gap shows the right words: green, or amber when moved */
        each(g.items, function (it) { if (itemRight(g, it)) { g.gap.textContent = txt(it); } });
        add(g.gap, ok ? 'right' : 'fixed');
        del(g.gap, 'act');
        del(g.box, 'act');
      }
    } else if (g.type === 'dial') {
      for (k = 0; k <= g.n; k++) { if (g.good(k)) { if (lo < 0) { lo = k; } hi = k; } }
      band = $('.dial-band', g.el);
      if (band && lo >= 0) {
        band.style.left = (100 * Math.max(lo - 0.5, 0) / g.n) + '%';
        band.style.width = (100 * (Math.min(hi + 0.5, g.n) - Math.max(lo - 0.5, 0)) / g.n) + '%';
      }
      add(g.el, ok ? 'right' : 'wrong');
    } else {
      each(g.chips, function (c) {
        if (chipGood(g, c)) { add(c, c.parentNode === g.tray ? 'out' : 'right'); } else { bad.push(c); }
      });
      each(bad, function (c) { g.tray.appendChild(c); });      /* lift the wrong ones out first */
      each(bad, function (c) {
        var z = rightZone(g, c);
        add(c, 'fixed');
        (z || g.tray).appendChild(c);
      });
    }
  }
  function reveal(p, ok) {
    each(p.groups, function (g) { revealGroup(g, gradeGroup(g)); });
    each($$('.ffc', p.el), function (c) { add(c, 'seen'); });       /* every part's reading, once it is answered */
    add(p.el, 'checked');
    syncFor(p.el);
    if (p.q.parts.length > 1) { add(p.el, ok ? 'good' : 'bad'); }
  }
  function verdict(q) {
    var kind = 'notQuiteChoice';
    each(q.parts, function (p) {
      each(p.groups, function (g) {
        if (g.type === 'place' && kind === 'notQuiteChoice') { kind = 'notQuitePlace'; }
        if (g.type === 'dial') { kind = 'notQuiteValue'; }
      });
    });
    if (kind === 'notQuiteChoice' && $('.missed', q.sec)) { kind = 'notQuiteMissed'; }
    if (q.vd) { q.vd.textContent = q.ok ? say('correct') : say(kind); }
    if (q.why) {
      add(q.why, 'on'); add(q.why, q.ok ? 'good' : 'bad');
      /* above the dock, not under it - and a question of several parts keeps its last part's own label in view */
      if (q.parts.length > 1) { settle(q.why, q.parts[q.k].el); } else { bring(q.why, null); }
    }
  }
  /* bring an element into the band between the top bar and the dock (2.46.0). The top bar is sticky: scrollIntoView
     left a scenario's "Step 2 of 3" under it. Scrolled down only as far as keeps `from` (default: the element itself)
     below the top bar - when both do not fit, the top wins. */
  function band() {
    var top = 8, bot = (W.innerHeight || D.documentElement.clientHeight) - 8, bar = $('.state'), team = $('#teamBar');
    if (bar) { top = Math.max(top, bar.getBoundingClientRect().bottom + 8); }
    if (team && !team.hasAttribute('hidden')) { top = Math.max(top, team.getBoundingClientRect().bottom + 8); }
    if (dock && !has(dock, 'off')) { bot = Math.min(bot, dock.getBoundingClientRect().top - 8); }
    return { top: top, bot: bot };
  }
  function bring(el, from) {
    if (!el || !el.getBoundingClientRect) { return; }
    var r = el.getBoundingClientRect(), t = (from || el).getBoundingClientRect().top, d = 0, b = band();
    if (r.bottom > b.bot) { d = Math.min(r.bottom - b.bot, t - b.top); } else if (t < b.top) { d = t - b.top; }
    if (d) { try { W.scrollBy(0, d); } catch (x) { D.documentElement.scrollTop += d; } }
  }
  /* a question of several parts (2.50.1): once the earlier parts have folded, the question, the folded parts, the part
     in hand and its verdict usually fit the screen together - then the page goes back to the top, so nothing of it
     is left above the frame; when they do not, bring() keeps the part's own label under the top bar */
  function settle(el, from) {
    if (!el || !el.getBoundingClientRect) { return; }
    var y = W.pageYOffset || D.documentElement.scrollTop || 0;
    if (y > 0 && el.getBoundingClientRect().bottom + y <= band().bot) { toTop(); return; }
    bring(el, from);
  }
  function toTop() { try { W.scrollTo(0, 0); } catch (x) { /* an old WebView */ } D.documentElement.scrollTop = 0; body.scrollTop = 0; }
  function allOk(q) {
    var ok = true;
    each(q.parts, function (p) { if (!(p.done && p.ok)) { ok = false; } });
    return ok;
  }

  /* ---------------------------------------------------------------- a drawing shared by several questions */
  /* the drawing is in the page once (svg.taskfig[data-fig]) and moves into the question on screen */
  function moveFig(sec) {
    each($$('.ga[data-fig]', sec), function (holder) {
      var svg = $('svg.taskfig[data-fig="' + holder.getAttribute('data-fig') + '"]');
      if (svg && svg.parentNode !== holder) { holder.insertBefore(svg, holder.firstChild); }
    });
  }
  /* a figure-kit drawing in a task (2.43.0): its tappable areas and the ends of its leader lines are the drawn parts
     themselves - [data-part="<part id>"] is laid on the part's own box once kit.js has drawn it (it draws after this
     file starts, so wait for it), grown to a 56 px tap target (L42) */
  function placeParts(sec, tries) {
    var held = $$('[data-part]', sec), ga = $('.ga', sec), svg = ga && $('svg.taskfig[data-kit]', ga);
    if (!held.length || !svg) { return; }
    if (!svg.__kit) {
      if ((tries || 0) < 80) { setTimeout(function () { if (qs[cur] && qs[cur].sec === sec) { placeParts(sec, (tries || 0) + 1); } }, 50); }
      return;
    }
    var g = ga.getBoundingClientRect();
    if (!g.width || !g.height) { return; }
    each(held, function (h) {
      var part = svg.__kit.parts[h.getAttribute('data-part')], r = part && part.g.getBoundingClientRect();
      if (!r || !r.width) { return; }
      var cx = r.left + r.width / 2 - g.left, cy = r.top + r.height / 2 - g.top;
      if (h.tagName.toLowerCase() === 'line') {                    /* a leader line ends on the middle of its part */
        /* 2.50.1 - of what is DRAWN of it: a vent's tap area is the whole mast run (2.49.7) but unpainted, and the middle of
           the part's box was empty deck (IGF M01 m01, found by three reviews and now by review_sheets.mjs) */
        var pb = paintedBox(part.g);
        if (pb) { cx = (pb.left + pb.right) / 2 - g.left; cy = (pb.top + pb.bottom) / 2 - g.top; }
        h.setAttribute('x2', (100 * cx / g.width).toFixed(2)); h.setAttribute('y2', (100 * cy / g.height).toFixed(2));
        return;
      }
      var w = Math.max(r.width + 16, 56), ht = Math.max(r.height + 16, 56);
      var x = Math.min(Math.max(cx - w / 2, 0), g.width - Math.min(w, g.width)), y = Math.min(Math.max(cy - ht / 2, 0), g.height - Math.min(ht, g.height));
      h.style.left = (100 * x / g.width).toFixed(2) + '%'; h.style.top = (100 * y / g.height).toFixed(2) + '%';
      h.style.width = (100 * Math.min(w, g.width) / g.width).toFixed(2) + '%'; h.style.height = (100 * Math.min(ht, g.height) / g.height).toFixed(2) + '%';
    });
  }
  /* the screen box of what is painted of a kit part: its shapes and lines - not its words, not an unpainted tap area */
  function paintedBox(g) {
    var box = null;
    each($$('*', g), function (e) {
      var tag = (e.tagName || '').toLowerCase();
      if (!e.getBoundingClientRect || tag === 'g' || tag === 'text' || tag === 'tspan' || has(e, 'hit') ||
          (e.closest && e.closest('.kit-lbl'))) { return; }
      var cs = W.getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0 || (cs.fill === 'none' && cs.stroke === 'none')) { return; }
      var r = e.getBoundingClientRect();
      if (!r.width && !r.height) { return; }
      box = box ? { left: Math.min(box.left, r.left), top: Math.min(box.top, r.top), right: Math.max(box.right, r.right),
                    bottom: Math.max(box.bottom, r.bottom) } : { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
    });
    return box;
  }
  W.addEventListener('resize', function () { if (cur >= 0 && qs[cur]) { placeParts(qs[cur].sec); } });
  function neutralSpot(sec) {
    var ga = $('.ga', sec), r = ga.getBoundingClientRect();
    return { x: r.left + r.width * 0.83, y: r.top + r.height * 0.88 };
  }

  /* ---------------------------------------------------------------- the flow */
  function setBar(n) {
    if (barEl) { barEl.style.width = Math.round(100 * n / Math.max(qs.length, 1)) + '%'; }
  }
  function setPart(label) { if (partEl) { partEl.textContent = label; } }
  function setGot() {
    if (!gotEl) { return; }
    var n = 0; each(qs, function (q) { if (q.done) { n++; } });
    gotEl.textContent = n ? say('soFar', { n: okCount }) : '';
  }
  function setBtn(label, state) {
    go.textContent = label;
    go.disabled = (state === 'off');
    if (state === 'next') { add(go, 'next'); } else { del(go, 'next'); }
  }
  function refresh() {
    if (cur < 0 || ended) { return; }
    var q = qs[cur], p = q.parts[q.k];
    if (q.done || p.done) { return; }
    go.disabled = !hasAnswer(p);
  }
  function screensOff() { each($$('.scr'), function (s) { del(s, 'on'); }); }
  /* the hand shows a gesture once per way of answering: tap the picture, drag a card, slide the dial -
     a button that says what it does needs no hand */
  function hint(q) {
    var g = q.parts[q.k].groups[0];
    if (!g || shown[q.mech] || g.type === 'choose' && !$('.hot', q.sec)) { return; }
    shown[q.mech] = true;
    later(500, function () {
      if (qs[cur] !== q || q.touched || q.done || ended) { return; }
      if (g.type === 'choose') { demoTap(neutralSpot(q.sec)); return; }
      if (g.type === 'dial') {
        var r = g.track.getBoundingClientRect();
        demoDrag(centre(g.thumb), { x: r.left + r.width * 0.6, y: r.top + r.height / 2 });
        return;
      }
      var a = g.chips[0], b = g.zones[0];
      if (a && b) { demoDrag(centre(a), centre(b)); }
    });
  }
  function showQ(i) {
    killHand();
    cur = i;
    var q = qs[i];
    screensOff();
    moveFig(q.sec);
    add(q.sec, 'on');
    placeParts(q.sec);
    setPart(say('question', { n: i + 1, of: qs.length }));
    setGot();
    setBar(i);
    setBtn(say('check'), 'off');
    toTop();
    hint(q);
  }
  /* one Check per part; the question is right when every part is */
  function check() {
    var q = qs[cur], p = q.parts[q.k];
    if (q.done || p.done || !hasAnswer(p)) { return; }
    killHand();
    p.ok = grade(p);
    p.done = true;
    lock(p);
    reveal(p, p.ok);
    if (q.k < q.parts.length - 1) { setBtn(say('goOn'), 'next'); return; }
    finish(q);
  }
  function finish(q) {
    q.done = true;
    q.ok = allOk(q);
    if (q.ok) { okCount++; }
    each(q.parts, function (p) { del(p.el, 'stopping'); });
    verdict(q);
    setGot();
    setBar(cur + 1);
    if (cur === qs.length - 1) {
      report(false);
      setBtn(say('seeScore'), 'next');
    } else {
      setBtn(say('next'), 'next');
    }
  }
  /* the next part: a scenario's next step (the step before folds up), or the incident's stop point (the cards stay) */
  function openPart(q, k) {
    var before = q.parts[k - 1], p = q.parts[k];
    q.k = k;
    if (p.kind === 'stop') { p.groups = [mkStop(q, before)]; add(before.el, 'stopping'); } else { add(before.el, 'past'); }
    add(p.el, 'on');
    setBtn(say('check'), 'off');
    settle(p.el);                                      /* the part's own label ("Step 2 of 3") stays under the top bar */
  }
  function next() {
    if (cur < qs.length - 1) { showQ(cur + 1); } else { showResult(); }
  }
  function onGo() {
    if (ended) { return; }
    if (!started) { started = true; showQ(0); return; }
    var q = qs[cur];
    if (q.done) { next(); } else if (!q.parts[q.k].done) { check(); } else { openPart(q, q.k + 1); }
  }

  /* ---------------------------------------------------------------- result and report */
  function totals() {
    var ok = 0, answered = 0;
    each(qs, function (q) { if (q.done) { answered++; if (q.ok) { ok++; } } });
    return { ok: ok, answered: answered, total: qs.length };
  }
  /* a check reports its head: 'PASSED' or 'NOT PASSED' against the pass mark on the page; a self-check none */
  function head(t) {
    if (!PASS) { return ''; }
    return (t.ok * 100 >= PASS * t.total) ? 'PASSED' : 'NOT PASSED';
  }
  function report(timeout) {
    if (reported) { return; }
    reported = true;
    var t = totals(), items = [];
    each(qs, function (q, i) { items.push({ t: (i + 1) + '. ' + q.text, ok: !!(q.done && q.ok) }); });
    buildResult(t, timeout);
    CR.send({ code: CODE, title: TITLE, ok: t.ok, total: t.total, head: head(t), items: items,
      answered: t.answered, of: t.total, timeout: !!timeout });
  }
  function buildResult(t, timeout) {
    if (!resScr) { return; }
    var arc = $('#resArc'), ring = $('#resRing'), num = $('#resNum'), list = $('#resList');
    var badge = $('#resBadge'), line = $('#resLine'), note = $('#resNote'), h = head(t), C = 502.65, html = '';
    num.textContent = t.ok + ' / ' + t.total;
    if (arc) { arc.setAttribute('data-off', String(Math.round(C * (1 - (t.total ? t.ok / t.total : 0)) * 10) / 10)); }
    if (badge) {
      if (h) {
        badge.textContent = say(h === 'PASSED' ? 'passed' : 'notPassed');
        badge.style.display = 'inline-block';
        if (h === 'NOT PASSED') { add(badge, 'no'); }
      }
      else { badge.style.display = 'none'; }
    }
    if (h === 'PASSED') { add(ring, 'pass'); }
    line.textContent = say('got', { ok: t.ok, total: t.total }) + (timeout ? say('timeUp') : '');
    if (note && PASS) {
      note.textContent = say('passNote', { pass: PASS, need: Math.ceil(t.total * PASS / 100 - 0.000001), total: t.total });
    }
    each(qs, function (q, i) {
      var cls = q.done ? (q.ok ? 'yes' : 'no') : 'skip';
      html += '<li class="' + cls + '"><i>' + (q.done ? (q.ok ? '✓' : '✕') : '–') + '</i><span>' + (i + 1) + '. ' +
        q.text.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</span></li>';
    });
    list.innerHTML = html;
  }
  function showResult() {
    killHand();
    screensOff();
    add(resScr, 'on');
    add(dock, 'off');
    toTop();                     /* the last question was scrolled: the ring opened half under the top bar (2.46.0) */
    setPart(say('result'));
    if (gotEl) { gotEl.textContent = ''; }
    setBar(qs.length);
    var arc = $('#resArc');
    if (arc) {
      arc.setAttribute('stroke-dasharray', '502.65');
      arc.style.strokeDashoffset = '502.65';
      void arc.getBoundingClientRect();
      setTimeout(function () { arc.style.strokeDashoffset = arc.getAttribute('data-off') || '0'; }, 60);
    }
    ended = true;
  }
  function timeUp() {
    if (ended && reported) { return; }
    var q = cur >= 0 ? qs[cur] : null, p = q ? q.parts[q.k] : null;
    if (q && !q.done) {                       /* what was done is marked; a question half done counts as answered, not right */
      if (!p.done && anyAnswer(p)) { p.ok = grade(p); p.done = true; lock(p); }
      if (q.k > 0 || p.done) {
        q.done = true; q.ok = allOk(q);
        if (q.ok) { okCount++; }
      }
    }
    report(true);
    showResult();
  }
  CR.onTimer(function (rem) { if (rem <= 0 && !reported) { timeUp(); } });
  /* a team's answer handed in from another member's tablet: this one says so, locks, and sends nothing */
  function handedElsewhere(d) {
    if (reported) { return; }                                 /* this tablet handed in first */
    reported = true;
    CR.stop();
    killHand();
    ended = true;
    var msg = D.getElementById('teamDone');
    if (msg) {
      msg.textContent = say('handedIn', { by: String(d.by || ''), team: String(d.team || (TEAM.team && TEAM.team.name) || '') });
    }
    add(body, 'handed');
    add(dock, 'off');
    each(qs, function (q) { each(q.parts, function (p) { lock(p); }); });
  }

  /* ---------------------------------------------------------------- first screen of the course: try the tablet */
  function initTry() {
    var tap = $('#tryTap'), s1 = $('#try1'), s2 = $('#try2'), hello = $('#tryHello');
    var chip = $('#tryChip'), zone = $('#tryZone'), tray = $('#tryTray');
    var done1 = false, done2 = false;
    var tq = { sec: tryScr, chips: [chip], zones: [zone], tray: tray, locked: false, sel: null, id: 'try' };
    function both() { if (done1 && done2) { add(hello, 'on'); } }
    tap.addEventListener('click', function () {
      if (done1) { return; }
      done1 = true; add(s1, 'done'); both();
      killHand();
      later(500, function () {
        if (!done2) { demoDrag(centre(chip), centre(zone)); }
      });
    }, false);
    tq.onchange = function () {
      if ($('.chip', zone) && !done2) { done2 = true; add(s2, 'done'); both(); }
    };
    bindPlacement(tq);
    later(600, function () { if (!done1) { demoTap(centre(tap)); } });
  }

  /* ---------------------------------------------------------------- start */
  /* every choice keeps the letter it was shown with (2.46.0): a CSS counter re-lettered a scenario's step once the
     choices that were not right had folded away - "C" became "A" after Check */
  function letterAll() {
    each($$('.opt'), function (o) {
      var c = o.parentNode;
      while (c && c !== body && !has(c, 'opts') && c.tagName !== 'TR') { c = c.parentNode; }
      if (!c || c === body) { return; }
      c.__gbn = (c.__gbn || 0) + 1;
      o.setAttribute('data-l', String.fromCharCode(64 + c.__gbn));
    });
  }
  function init() {
    letterAll();
    each($$('.scr[data-script]'), function (s) { qs.push(mkQ(s)); });
    TEAM.onDone = handedElsewhere;
    if (TEAM.done) { handedElsewhere(TEAM.done); }
    go.addEventListener('click', onGo, false);
    var again = $('#again');
    if (again) {
      if (inFrame) { again.style.display = 'none'; }          /* one opening, one result inside the classroom */
      else { again.addEventListener('click', function () { W.location.reload(); }, false); }
    }
    if (tryScr) {
      add(tryScr, 'on');
      setPart(say('tryFirst'));
      setBar(0);
      setBtn(say('startSelf'), 'go');
      initTry();
    } else if (introScr) {
      add(introScr, 'on');
      setPart(say('moduleCheck'));
      setBar(0);
      setBtn(say('startCheck'), 'go');
    } else {
      started = true; showQ(0);
    }
  }
  init();
}());
