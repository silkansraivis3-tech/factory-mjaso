/* gb_answer.js - the one shared engine of every compiled trainee task page (self-check, module check, final).
   Promoted from the IGF pilot's m01_tasks.js (2.34.0), so every module answers the same way (L38, L42).
   Plain ES5, no network. Copied into each module's assets/ by design_system.py, never edited there.

   A compiled page (course-factory/compile/scripts/compile_module.py) is only its questions as markup:
     <body data-code="SC1" data-title="..." data-pass="0">      data-pass: the pass mark in %, 0 = a self-check
     <section class="scr" data-script="q01" data-mech="hotspot" [data-multi="1"]> ... </section>
   One question per screen; choose, tap the picture, drag-and-drop with a tap-then-tap alternative.

   The answers are NOT in the page: every answer element carries data-key = gbKey(screen id, its text, value)
   and the page grades by working out the key of what the trainee did (classroom-system.json task_page.answer_keys).
   Value of a key:  choose / tap the picture: 1 right, 0 wrong
                    put in order: the place, 1, 2, 3 ...
                    match: the partner's text (the left side the right side belongs to)
                    sort into groups: the group's name
                    label the drawing: the id of the place on the drawing

   The classroom: the result is reported once - parent.postMessage({type: 'gb-task-done', code, title, ok, total,
   head, items, answered, of, timeout: true|false}); the instructor's timer {type: 'gb-timer'} is heard, and at 0
   what was done is marked and reported with timeout: true. "Start again" exists only outside the classroom frame
   (window.parent === window): inside it, one opening gives one result.
   The words on the controls come from window.GB_ANSWER_TEXT (the compiler writes them in the course language). */
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
    got: 'You got {ok} of {total} right.', timeUp: ' The time was up.',
    passNote: 'Pass mark {pass} % – {need} of {total} right. This shows what to review. It is not a grade.'
  };
  (function () { var k, o = W.GB_ANSWER_TEXT || {}; for (k in o) { if (o.hasOwnProperty(k)) { T[k] = o[k]; } } }());
  function say(k, v) {
    return String(T[k]).replace(/\{(\w+)\}/g, function (m, n) { return (v && v[n] !== undefined) ? v[n] : m; });
  }

  /* ---------------------------------------------------------------- the classroom */
  var CR = (function () {
    var sent = false;
    return {
      inFrame: !(window.parent === window),
      send: function (r) {
        if (sent) { return; }
        sent = true;
        try {
          W.parent.postMessage({ type: 'gb-task-done', code: r.code, title: r.title, ok: r.ok, total: r.total,
            head: r.head, items: r.items, answered: r.answered, of: r.of, timeout: r.timeout === true }, '*');
        } catch (e) { /* opened on its own - no classroom to tell */ }
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
  function has(el, c) { return (' ' + el.className + ' ').indexOf(' ' + c + ' ') >= 0; }
  function add(el, c) { if (el && !has(el, c)) { el.className = (el.className ? el.className + ' ' : '') + c; } }
  function del(el, c) {
    if (el) { el.className = norm((' ' + el.className + ' ').replace(' ' + c + ' ', ' ')); }
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
      begin(e, true);
    }, false);
    chip.addEventListener('touchmove', onMove, false);
    chip.addEventListener('touchend', onTouchEnd, false);
    chip.addEventListener('touchcancel', function () { clean(); }, false);
    chip.addEventListener('mousedown', function (e) {
      if (e.button !== 0 || new Date().getTime() - lastTouch < 700) { return; }
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
  function placed(q) { var n = 0; each(q.chips, function (c) { if (c.parentNode !== q.tray) { n++; } }); return n; }
  function zoneValue(z) { return z ? norm(z.getAttribute('data-val') || '') : ''; }
  function chipGood(q, c) {
    var z = c.parentNode;
    return z !== q.tray && has(z, 'zone') && gbKey(q.id, txt(c), zoneValue(z)) === keyOf(c);
  }
  function rightZone(q, c) {
    var i;
    for (i = 0; i < q.zones.length; i++) {
      if (gbKey(q.id, txt(c), zoneValue(q.zones[i])) === keyOf(c)) { return q.zones[i]; }
    }
    return null;
  }

  /* ---------------------------------------------------------------- questions */
  var CHOOSE = { single_choice: 1, read_instrument: 1, multi_select: 1, hotspot: 1, spot_the_hazard: 1 };
  function isRight(q, it) { return keyOf(it) === gbKey(q.id, txt(it), 1); }
  function mkQ(sec) {
    var q = { sec: sec, id: sec.getAttribute('data-script'), mech: sec.getAttribute('data-mech'),
      multi: sec.getAttribute('data-multi') === '1', done: false, ok: false, locked: false, sel: null, picked: [], touched: false };
    q.text = txt($('[data-script-field="question"]', sec));
    q.why = $('.why', sec);
    q.vd = $('.vd', sec);
    if (CHOOSE[q.mech]) {
      q.items = $$('.opt, .hot', sec);
      each(q.items, function (it) {
        it.addEventListener('click', function () {
          if (q.locked) { return; }
          if (q.multi) {
            if (has(it, 'sel')) { del(it, 'sel'); } else { add(it, 'sel'); }
            q.picked = q.items.filter(function (o) { return has(o, 'sel'); });
          } else {
            each(q.items, function (o) { del(o, 'sel'); });
            add(it, 'sel');
            q.picked = [it];
          }
          q.sel = q.picked[0] || null;
          q.touched = true;
          refresh();
        }, false);
      });
    } else {
      q.chips = $$('.chip', sec);
      q.zones = $$('.zone', sec);
      q.tray = $('.tray', sec);
      q.onchange = function () { q.touched = true; refresh(); };
      bindPlacement(q);
    }
    return q;
  }
  function hasAnswer(q) {
    if (q.items) { return q.picked.length > 0; }
    return placed(q) === q.chips.length;
  }
  function anyAnswer(q) {
    if (q.items) { return q.picked.length > 0; }
    return placed(q) > 0;
  }
  function grade(q) {
    var ok = true;
    if (q.items) {
      each(q.items, function (it) { if (has(it, 'sel') !== isRight(q, it)) { ok = false; } });
      return ok && q.picked.length > 0;
    }
    each(q.chips, function (c) { if (!chipGood(q, c)) { ok = false; } });
    return ok;
  }
  function lock(q) { q.locked = true; add(q.sec, 'locked'); if (q.chips) { select(q, null); } }
  function reveal(q, ok) {
    var bad = [];
    if (q.items) {
      each(q.items, function (it) {
        if (isRight(q, it)) { add(it, 'right'); }
        else if (has(it, 'sel')) { add(it, 'wrong'); }
        else if (has(it, 'opt')) { add(it, 'dim'); }
      });
      if (!ok) { each(q.picked, function (it) { if (!isRight(q, it)) { add(it, 'shake'); } }); }
    } else {
      each(q.chips, function (c) {
        if (chipGood(q, c)) { add(c, 'right'); } else { bad.push(c); }
      });
      each(bad, function (c) { q.tray.appendChild(c); });      /* lift the wrong ones out first */
      each(bad, function (c) {
        var z = rightZone(q, c);
        add(c, 'fixed');
        (z || q.tray).appendChild(c);
      });
    }
    if (q.vd) { q.vd.textContent = ok ? say('correct') : say(q.items ? 'notQuiteChoice' : 'notQuitePlace'); }
    if (q.why) { add(q.why, 'on'); add(q.why, ok ? 'good' : 'bad'); }
  }

  /* ---------------------------------------------------------------- a drawing shared by several questions */
  /* the drawing is in the page once (svg.taskfig[data-fig]) and moves into the question on screen */
  function moveFig(sec) {
    each($$('.ga[data-fig]', sec), function (holder) {
      var svg = $('svg.taskfig[data-fig="' + holder.getAttribute('data-fig') + '"]');
      if (svg && svg.parentNode !== holder) { holder.insertBefore(svg, holder.firstChild); }
    });
  }
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
    var q = qs[cur];
    if (q.done) { return; }
    go.disabled = !hasAnswer(q);
  }
  function screensOff() { each($$('.scr'), function (s) { del(s, 'on'); }); }
  function hint(q) {
    if (shown[q.mech] || q.items && !$('.hot', q.sec)) { return; }
    shown[q.mech] = true;
    later(500, function () {
      if (qs[cur] !== q || q.touched || q.done || ended) { return; }
      if (q.items) { demoTap(neutralSpot(q.sec)); return; }
      var a = q.chips[0], b = q.zones[0];
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
    setPart(say('question', { n: i + 1, of: qs.length }));
    setGot();
    setBar(i);
    setBtn(say('check'), 'off');
    D.documentElement.scrollTop = 0;
    body.scrollTop = 0;
    hint(q);
  }
  function check() {
    var q = qs[cur], ok;
    if (!hasAnswer(q) || q.done) { return; }
    killHand();
    ok = grade(q);
    q.done = true;
    q.ok = ok;
    if (ok) { okCount++; }
    lock(q);
    reveal(q, ok);
    setGot();
    setBar(cur + 1);
    if (cur === qs.length - 1) {
      report(false);
      setBtn(say('seeScore'), 'next');
    } else {
      setBtn(say('next'), 'next');
    }
  }
  function next() {
    if (cur < qs.length - 1) { showQ(cur + 1); } else { showResult(); }
  }
  function onGo() {
    if (ended) { return; }
    if (!started) { started = true; showQ(0); return; }
    if (!qs[cur].done) { check(); } else { next(); }
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
      if (h) { badge.textContent = h; badge.style.display = 'inline-block'; if (h === 'NOT PASSED') { add(badge, 'no'); } }
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
    if (cur >= 0 && qs[cur] && !qs[cur].done && anyAnswer(qs[cur])) {
      var q = qs[cur], ok = grade(q);
      q.done = true; q.ok = ok;
      if (ok) { okCount++; }
      lock(q);
    }
    report(true);
    showResult();
  }
  CR.onTimer(function (rem) { if (rem <= 0 && !reported) { timeUp(); } });

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
  function init() {
    each($$('.scr[data-script]'), function (s) { qs.push(mkQ(s)); });
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
