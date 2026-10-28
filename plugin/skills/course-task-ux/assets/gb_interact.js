/* gb_interact.js - the interactive task types of a compiled trainee page (2.74.0), beside gb_answer.js.
   Plain ES5, no network. Copied into each module's assets/ with gb_answer.js, never edited there.

   Owner, 2026-10-28: "more interesting / modern / technology self checks, so self checks become practical learning as
   well ... tasks where they are given a little bit difficult task, where they need to find the answer by themselves" -
   and "3D deck view, 3D models, equipment in 3D, panorama, on-ship activities". The prototypes the owner approved are
   design/task-prototypes/index.html; these are the same types made from any course's script.

   A compiled question (task_pages.py) holds an element <div class="lab" data-lab="TYPE"> inside its part. gb_answer.js
   asks window.GB_LAB[TYPE](el, api) for the part's group and then talks to it like any other group:
     answered()  touched()  right()  show(ok, later)  said() -> {a, c}  lock()  word()  (the dock's words for its Check)
   api: id (the screen), key(id, text, value) (the page's gbKey), say(k), later (the debrief rule: a wrong answer is
   never followed by the right one), blind (a graded final), lang, changed() (tell the engine), check() (press Check).

   THE ANSWERS ARE NOT IN THE PAGE (classroom-system.json task_page.answer_keys): every right answer is a data-key the
   compiler worked out, and a type grades by working out the key of what the trainee did. What a type shows is the
   task's world - a data sheet, a network of pipes, a room - never which choice is right.

   FINGERS FIRST (course-task-ux section 0): every drag has a tap, every pinch has + and -, 56 px targets, nothing that
   only a mouse can do. The 3D types run on the factory's 3D kit (course-visuals/kit3d, three.js r128) - the same parts
   and look as the deck's 3D slides. */
(function () {
  'use strict';
  var D = document, W = window;

  /* ---------------------------------------------------------------- words (the page's <html lang>) */
  var T = {
    t: 'True', f: 'False', flick: 'Flick the card, or tap a side', cardOf: 'Card {n} of {of}', nextCard: 'Next card',
    right: 'Right.', notRight: 'Not right.', later: 'We will check this one together in the debrief.',
    keep: 'It is right as written – keep it', review: 'Review this sentence', reviewed: '{n} of {of} reviewed',
    sheet: 'Data sheet', sheetClose: 'Close the data sheet', handIn: 'Hand in {v}', handInEmpty: 'Hand in my answer',
    reveal: 'Show the real curve', yourPoint: 'Your prediction: {v}', dragPoint: 'Drag the point',
    tooLow: 'Your point is too low.', tooHigh: 'Your point is too high.',
    lock: 'Lock this in', test: 'Test', tests: 'Your tests', none: 'None yet', covered: 'Covered', over: 'OVER RANGE',
    pin: 'Pin as evidence', pinned: 'Pinned', openSrc: 'Open a source on the left.', evidence: 'Your evidence', noPins: 'Nothing pinned yet',
    open: 'OPEN', shut: 'SHUT', start: 'Start the pump', goalOk: 'It flows from {a} to {b}.',
    dead: 'The pump is running against a shut valve. Nothing moves.', into: 'It is also running into {n}.', noGoal: 'Nothing reaches {n}.',
    fine: 'Looks fine', report: 'Report a problem', inspect: 'Tap anything to inspect it', reported: 'Reported {n} · looked at {m}',
    handRound: 'Hand in my round', explode: 'Take it apart', xray: 'X-ray', operate: 'Operate', tapPart: 'Tap a part',
    answerPart: 'This is my answer', setDone: 'Hand in', zero: 'Zero in fresh air', record: 'Record reading',
    zeroFirst: 'Zero the meter in fresh air first.', bringUp: 'Bring the hose end up to fresh air to zero.',
    travelling: 'Sample on its way up the hose… {s} s', steady: 'Steady · sample from {d}', alarm: 'ALARM · sample from {d}',
    hatch: 'the hatch', early: '* recorded before the sample reached the meter', samplesDone: 'Hand in my readings',
    no3d: 'The 3D view is not available on this device.', turnHint: 'Drag to turn · tap a part', lookHint: 'Drag to look around · tap to inspect',
    lower: 'Lower 1 m', raise: 'Raise 1 m', toHatch: 'Up to the hatch', decimal: '.'
  };
  var LANG = {
    lv: {
      t: 'Patiesi', f: 'Nepatiesi', flick: 'Pavelc kartīti vai pieskaries malai', cardOf: '{n}. kartīte no {of}', nextCard: 'Nākamā kartīte',
      right: 'Pareizi.', notRight: 'Nav pareizi.', later: 'Šo kopā pārrunāsim atskaitē.',
      keep: 'Teikums ir pareizs – atstāj to', review: 'Pārskati šo teikumu', reviewed: 'Pārskatīti {n} no {of}',
      sheet: 'Datu lapa', sheetClose: 'Aizvērt datu lapu', handIn: 'Iesniegt {v}', handInEmpty: 'Iesniegt atbildi',
      reveal: 'Rādīt īsto līkni', yourPoint: 'Tava prognoze: {v}', dragPoint: 'Pavelc punktu',
      tooLow: 'Tavs punkts ir par zemu.', tooHigh: 'Tavs punkts ir par augstu.',
      lock: 'Fiksēt', test: 'Pārbaudīt', tests: 'Tavas pārbaudes', none: 'Vēl nav', covered: 'Aizsegts', over: 'PĀRSNIEGTS',
      pin: 'Piespraust kā pierādījumu', pinned: 'Piesprausts', openSrc: 'Atver avotu kreisajā pusē.', evidence: 'Tavi pierādījumi', noPins: 'Nekas nav piesprausts',
      open: 'ATVĒRTS', shut: 'AIZVĒRTS', start: 'Iedarbināt sūkni', goalOk: 'Plūst no {a} uz {b}.',
      dead: 'Sūknis strādā pret aizvērtu vārstu. Nekas nekustas.', into: 'Tas plūst arī uz {n}.', noGoal: 'Līdz {n} nekas nenonāk.',
      fine: 'Viss kārtībā', report: 'Ziņot par problēmu', inspect: 'Pieskaries jebkam, lai apskatītu', reported: 'Ziņots {n} · apskatīts {m}',
      handRound: 'Iesniegt apgaitu', explode: 'Izjaukt', xray: 'Rentgens', operate: 'Darbināt', tapPart: 'Pieskaries daļai',
      answerPart: 'Šī ir mana atbilde', setDone: 'Iesniegt', zero: 'Nulle svaigā gaisā', record: 'Pierakstīt rādījumu',
      zeroFirst: 'Vispirms nonullē mērītāju svaigā gaisā.', bringUp: 'Pacel šļūtenes galu svaigā gaisā, lai nonullētu.',
      travelling: 'Paraugs ceļā pa šļūteni… {s} s', steady: 'Stabils · paraugs no {d}', alarm: 'TRAUKSME · paraugs no {d}',
      hatch: 'lūkas', early: '* pierakstīts, pirms paraugs sasniedza mērītāju', samplesDone: 'Iesniegt rādījumus',
      no3d: 'Šajā ierīcē 3D skats nav pieejams.', turnHint: 'Velc, lai grieztu · pieskaries daļai', lookHint: 'Velc, lai skatītos apkārt · pieskaries, lai apskatītu',
      lower: 'Nolaist 1 m', raise: 'Pacelt 1 m', toHatch: 'Līdz lūkai', decimal: ','
    },
    ru: {
      t: 'Верно', f: 'Неверно', flick: 'Смахни карточку или коснись стороны', cardOf: 'Карточка {n} из {of}', nextCard: 'Следующая',
      right: 'Правильно.', notRight: 'Неверно.', later: 'Разберём это вместе на разборе.',
      keep: 'Написано верно – оставить', review: 'Проверь это предложение', reviewed: 'Проверено {n} из {of}',
      sheet: 'Справочный лист', sheetClose: 'Закрыть лист', handIn: 'Сдать {v}', handInEmpty: 'Сдать ответ',
      reveal: 'Показать настоящую кривую', yourPoint: 'Твой прогноз: {v}', dragPoint: 'Перетащи точку',
      tooLow: 'Твоя точка слишком низко.', tooHigh: 'Твоя точка слишком высоко.',
      lock: 'Зафиксировать', test: 'Проверить', tests: 'Твои проверки', none: 'Пока нет', covered: 'Закрыто', over: 'ВНЕ ДИАПАЗОНА',
      pin: 'Закрепить как довод', pinned: 'Закреплено', openSrc: 'Открой источник слева.', evidence: 'Твои доводы', noPins: 'Ничего не закреплено',
      open: 'ОТКРЫТ', shut: 'ЗАКРЫТ', start: 'Пустить насос', goalOk: 'Поток идёт из {a} в {b}.',
      dead: 'Насос работает на закрытый клапан. Ничего не движется.', into: 'Груз идёт и в {n}.', noGoal: 'До {n} ничего не доходит.',
      fine: 'Всё в порядке', report: 'Сообщить о проблеме', inspect: 'Коснись чего угодно, чтобы осмотреть', reported: 'Сообщено {n} · осмотрено {m}',
      handRound: 'Сдать обход', explode: 'Разобрать', xray: 'Рентген', operate: 'Управлять', tapPart: 'Коснись детали',
      answerPart: 'Это мой ответ', setDone: 'Сдать', zero: 'Ноль на чистом воздухе', record: 'Записать показание',
      zeroFirst: 'Сначала обнули прибор на чистом воздухе.', bringUp: 'Подними конец шланга на чистый воздух, чтобы обнулить.',
      travelling: 'Проба идёт по шлангу… {s} с', steady: 'Стабильно · проба с {d}', alarm: 'ТРЕВОГА · проба с {d}',
      hatch: 'люка', early: '* записано до того, как проба дошла до прибора', samplesDone: 'Сдать показания',
      no3d: 'На этом устройстве 3D недоступно.', turnHint: 'Тяни, чтобы вращать · коснись детали', lookHint: 'Тяни, чтобы осмотреться · коснись, чтобы осмотреть',
      lower: 'Опустить на 1 м', raise: 'Поднять на 1 м', toHatch: 'К люку', decimal: ','
    }
  };
  (function () {
    var k, l = LANG[(D.documentElement.getAttribute('lang') || 'en').slice(0, 2).toLowerCase()] || {}, o = W.GB_INTERACT_TEXT || {};
    for (k in l) { if (l.hasOwnProperty(k)) { T[k] = l[k]; } }
    for (k in o) { if (o.hasOwnProperty(k)) { T[k] = o[k]; } }
  }());
  function say(k, v) { return String(T[k]).replace(/\{(\w+)\}/g, function (m, n) { return (v && v[n] !== undefined) ? v[n] : m; }); }

  /* ---------------------------------------------------------------- helpers */
  function $(s, r) { return (r || D).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || D).querySelectorAll(s)); }
  function each(l, fn) { for (var i = 0; i < l.length; i++) { fn(l[i], i); } }
  function norm(s) { return String(s == null ? '' : s).replace(/\s+/g, ' ').replace(/^ | $/g, ''); }
  function txt(e) { return e ? norm(e.textContent) : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function el(tag, cls, html, parent) {
    var e = D.createElement(tag);
    if (cls) { e.className = cls; }
    if (html != null) { e.innerHTML = html; }
    if (parent) { parent.appendChild(e); }
    return e;
  }
  function btn(cls, label, parent) { var b = el('button', cls, esc(label), parent); b.type = 'button'; return b; }
  function cls(e, c, on) { if (e && e.classList) { if (on === undefined) { e.classList.add(c); } else { e.classList.toggle(c, !!on); } } }
  function data(e, n) { return e ? e.getAttribute('data-' + n) || '' : ''; }
  function keys(e, n) { return data(e, n || 'keys').toLowerCase().split(/\s+/).filter(function (x) { return x; }); }
  /* the world a type is drawn from - JSON the compiler base64-encodes, so it is not read off the page as words */
  function world(e, n) {
    var s = data(e, n || 'world');
    if (!s) { return {}; }
    try { return JSON.parse(decodeURIComponent(escape(W.atob(s)))); } catch (x) { return {}; }
  }
  function fmtNum(v, dec) {
    var s = (Math.round(v * Math.pow(10, dec)) / Math.pow(10, dec)).toFixed(dec);
    return T.decimal === ',' ? s.replace('.', ',') : s;
  }
  function vibe(ms) {
    try {
      var ua = W.navigator.userActivation;                /* a tablet buzzes only after a real touch - never before one */
      if (W.navigator.vibrate && (!ua || ua.hasBeenActive)) { W.navigator.vibrate(ms); }
    } catch (x) { /* none */ }
  }

  /* one line under a lab: what just happened, without the right answer when the debrief rule is on */
  function feedback(box, ok, why, brief, later) {
    if (!box) { return; }
    box.className = 'gi-fb ' + (ok ? 'ok' : 'no');
    box.innerHTML = '<b>' + esc(ok ? say('right') : say('notRight')) + '</b> ' + esc(ok ? (why || '') : (brief || '')) +
      (!ok && later ? '<span class="gi-later">' + esc(say('later')) + '</span>' : '');
  }

  /* a sheet that slides up inside the lab: a question about one thing, the answers as big buttons */
  function sheet(host) {
    var veil = el('div', 'gi-veil', null, host), box = el('div', 'gi-sheet', null, host);
    veil.addEventListener('click', function () { close(); }, false);
    function close() { cls(veil, 'on', false); cls(box, 'on', false); }
    return {
      open: function (head, sub, choices, chosen, pickFn) {
        box.innerHTML = '<p class="gi-sh-h">' + esc(head) + '</p>' + (sub ? '<p class="gi-sh-s">' + esc(sub) + '</p>' : '') + '<div class="gi-sh-g"></div>';
        var g = $('.gi-sh-g', box), x = btn('gi-sh-x', '✕', box);
        x.setAttribute('aria-label', 'Close');
        x.addEventListener('click', close, false);
        each(choices, function (c, i) {
          var b = btn('gi-sh-o' + (chosen === i ? ' sel' : ''), c, g);
          b.addEventListener('click', function () { close(); pickFn(i); }, false);
        });
        cls(veil, 'on', true); cls(box, 'on', true);
      },
      close: close
    };
  }

  /* a tiny calculator and expression reader: numbers, names, + - * / ( ), comparisons, and, or, not.
     Used by the explore model (readouts and the test's rules); never by grading - grading is keys. */
  function expr(src) {
    var toks = String(src).replace(/×/g, '*').replace(/÷/g, '/').replace(/−/g, '-')
      .match(/\d*\.?\d+(?:e[-+]?\d+)?|[A-Za-z_][\w]*|<=|>=|==|!=|&&|\|\||[-+*\/()<>!=]/g) || [];
    var i = 0;
    function peek() { return toks[i]; }
    function next() { return toks[i++]; }
    function prim(v) {
      var t = next();
      if (t === '(') { var r = or(v); next(); return r; }
      if (t === '-') { return -prim(v); }
      if (t === '!' || t === 'not') { return !prim(v); }
      if (/^[\d.]/.test(t)) { return parseFloat(t); }
      if (t === 'true') { return true; }
      if (t === 'false') { return false; }
      if (v && v.hasOwnProperty(t)) { return v[t]; }
      throw new Error('unknown ' + t);
    }
    function mul(v) { var a = prim(v); while (peek() === '*' || peek() === '/') { var o = next(), b = prim(v); a = o === '*' ? a * b : a / b; } return a; }
    function add(v) { var a = mul(v); while (peek() === '+' || peek() === '-') { var o = next(), b = mul(v); a = o === '+' ? a + b : a - b; } return a; }
    function cmp(v) {
      var a = add(v), o, b, r = null;
      while (/^(<|>|<=|>=|==|!=|=)$/.test(peek() || '')) {
        o = next(); b = add(v);
        var ok = o === '<' ? a < b : o === '>' ? a > b : o === '<=' ? a <= b : o === '>=' ? a >= b : o === '!=' ? a !== b : a === b;
        r = (r === null ? true : r) && ok; a = b;
      }
      return r === null ? a : r;
    }
    function and(v) { var a = cmp(v); while (peek() === '&&' || peek() === 'and') { next(); var b = cmp(v); a = a && b; } return a; }
    function or(v) { var a = and(v); while (peek() === '||' || peek() === 'or') { next(); var b = and(v); a = a || b; } return a; }
    return function (v) { i = 0; try { return or(v); } catch (e) { return null; } };
  }

  /* drag with one finger; a press that does not move is a tap. Coordinates are the screen's. */
  function finger(target, o) {
    var st = null;
    target.addEventListener('pointerdown', function (e) {
      if (st || (e.button && e.button > 0)) { return; }
      st = { id: e.pointerId, x: e.clientX, y: e.clientY, moved: 0 };
      try { target.setPointerCapture(e.pointerId); } catch (x) { /* old WebView */ }
      if (o.down) { o.down(e); }
    }, false);
    target.addEventListener('pointermove', function (e) {
      if (!st || e.pointerId !== st.id) { return; }
      st.moved = Math.max(st.moved, Math.abs(e.clientX - st.x) + Math.abs(e.clientY - st.y));
      if (o.move) { o.move(e.clientX - st.x, e.clientY - st.y, e); }
    }, false);
    function end(e, cancel) {
      if (!st || e.pointerId !== st.id) { return; }
      var s = st; st = null;
      if (cancel) { if (o.cancel) { o.cancel(); } return; }
      if (s.moved < 10 && o.tap) { o.tap(e); } else if (o.up) { o.up(e.clientX - s.x, e.clientY - s.y, e); }
    }
    target.addEventListener('pointerup', function (e) { end(e, false); }, false);
    target.addEventListener('pointercancel', function (e) { end(e, true); }, false);
    target.addEventListener('lostpointercapture', function (e) { if (st && e.pointerId === st.id) { end(e, true); } }, false);
  }

  /* the 3D kit, mounted for a task: taps come back as part ids, the camera stays where the trainee put it */
  function mount3d(stage, spec, onTap) {
    if (!W.KIT3D || !W.THREE) { el('p', 'gi-no3d', esc(say('no3d')), stage); return null; }
    try {
      var api = W.KIT3D.mount(stage, spec, { keepView: true, onSelect: function (k) { if (onTap) { onTap(k); } } });
      return api;
    } catch (e) { el('p', 'gi-no3d', esc(say('no3d')), stage); return null; }
  }

  var LAB = W.GB_LAB = W.GB_LAB || {};

  /* ================================================================ 1. TRUE OR FALSE - flick the card (Part A)
     <div class="lab gi-swipe" data-lab="swipe">
       <div class="sw-card" data-key="gbKey(id, statement, 'true'|'false')">
         <p class="sw-st" data-script-field="answer">statement</p> <p class="sw-why" data-script-field="answer">why</p></div> ...
     One card at a time; each is answered with its own line of feedback; the last one presses Check by itself. */
  LAB.swipe = function (root, api) {
    var cards = $$('.sw-card', root), n = cards.length, i = 0, done = [], locked = false;
    var deck = el('div', 'sw-deck'), sides = el('div', 'sw-sides'), fb = el('div', 'gi-fb'), nav = el('div', 'sw-nav');
    root.insertBefore(deck, cards[0]);
    each(cards, function (c) { deck.appendChild(c); });
    var bF = btn('sw-side f', say('f'), sides), bT = btn('sw-side t', say('t'), sides);
    root.appendChild(sides); root.appendChild(fb); root.appendChild(nav);
    var count = el('span', 'sw-count', '', nav), nx = btn('sw-next', say('nextCard'), nav);
    nx.style.visibility = 'hidden';
    function show() {
      each(cards, function (c, k) { cls(c, 'on', k === i); cls(c, 'back', k === i + 1); c.style.transform = ''; });
      count.textContent = say('cardOf', { n: Math.min(i + 1, n), of: n });
      fb.className = 'gi-fb'; fb.innerHTML = '<span class="gi-hint">' + esc(say('flick')) + '</span>';
      nx.style.visibility = 'hidden';
      cls(bF, 'off', false); cls(bT, 'off', false);
    }
    function decide(v) {
      if (locked || i >= n || done[i]) { return; }
      var c = cards[i], st = txt($('.sw-st', c)), ok = (c.getAttribute('data-key') || '').toLowerCase() === api.key(api.id, st, v ? 'true' : 'false');
      done[i] = { v: v, ok: ok, st: st };
      cls(c, 'fly-' + (v ? 't' : 'f')); vibe(ok ? 15 : 40);
      cls(bF, 'off', true); cls(bT, 'off', true);
      feedback(fb, ok, txt($('.sw-why', c)), '', api.later && !api.blind);
      if (api.blind) { fb.className = 'gi-fb'; fb.innerHTML = ''; }
      api.changed();
      if (i === n - 1) { api.check(); return; }
      nx.style.visibility = 'visible';
    }
    nx.addEventListener('click', function () { if (i < n - 1) { i++; show(); } }, false);
    bF.addEventListener('click', function () { decide(false); }, false);
    bT.addEventListener('click', function () { decide(true); }, false);
    each(cards, function (c) {
      var w = 0;
      finger(c, {
        move: function (dx) { if (done[i] || locked || c !== cards[i]) { return; } w = dx; c.style.transform = 'translateX(' + dx + 'px) rotate(' + (dx / 24) + 'deg)'; cls(bT, 'hot', dx > 60); cls(bF, 'hot', dx < -60); },
        up: function (dx) { cls(bT, 'hot', false); cls(bF, 'hot', false); if (c !== cards[i] || done[i]) { return; } if (Math.abs(dx) > 110) { decide(dx > 0); } else { c.style.transform = ''; } },
        cancel: function () { c.style.transform = ''; cls(bT, 'hot', false); cls(bF, 'hot', false); }
      });
    });
    show();
    return {
      answered: function () { return done.length === n && done.every(function (x) { return !!x; }); },
      touched: function () { return done.length > 0; },
      right: function () { return this.answered() && done.every(function (x) { return x.ok; }); },
      show: function (ok) { count.textContent = done.filter(function (x) { return x && x.ok; }).length + ' / ' + n; },
      lock: function () { locked = true; },
      said: function () {
        var bad = done.filter(function (x) { return x && !x.ok; });
        return { a: bad.map(function (x) { return x.st + ' → ' + (x.v ? say('t') : say('f')); }).join(' | '),
          c: bad.map(function (x) { return x.st + ' → ' + (x.v ? say('f') : say('t')); }).join(' | ') };
      }
    };
  };

  /* ================================================================ 2. CHECK A COLLEAGUE - keep or correct each claim (Part B)
     <div class="lab gi-crit" data-lab="critique"><div class="cr-claim">
        <p class="cr-text" data-script-field="answer">claim</p>
        <button class="cr-o" data-key="gbKey(id, claim + ' => ' + option, 1|0)" data-o="*">…</button> … (hidden; the sheet shows them)
     "*" is "it is right as written - keep it". */
  LAB.critique = function (root, api) {
    var claims = $$('.cr-claim', root), pick = [], locked = false, sh = sheet(root), cnt = el('p', 'cr-count', '', root);
    function optLabel(o) { return o.getAttribute('data-o') === '*' ? say('keep') : txt(o); }
    function paint() {
      each(claims, function (c, k) {
        var p = pick[k], opts = $$('.cr-o', c), o = p == null ? null : opts[p], fx = $('.cr-fx', c) || el('p', 'cr-fx', '', c);
        cls(c, 'kept', !!(o && o.getAttribute('data-o') === '*'));
        cls(c, 'fixed', !!(o && o.getAttribute('data-o') !== '*'));
        fx.textContent = o && o.getAttribute('data-o') !== '*' ? '→ ' + txt(o) : '';
      });
      cnt.textContent = say('reviewed', { n: pick.filter(function (x) { return x != null; }).length, of: claims.length });
    }
    each(claims, function (c, k) {
      c.setAttribute('tabindex', '0'); c.setAttribute('role', 'button');
      function open() {
        if (locked) { return; }
        var opts = $$('.cr-o', c);
        sh.open(say('review'), '“' + txt($('.cr-text', c)) + '”', opts.map(optLabel), pick[k], function (i) { pick[k] = i; paint(); api.changed(); });
      }
      c.addEventListener('click', open, false);
      c.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } }, false);
    });
    function good(k) {
      var c = claims[k], o = $$('.cr-o', c)[pick[k]];
      return !!o && (o.getAttribute('data-key') || '').toLowerCase() === api.key(api.id, txt($('.cr-text', c)) + ' => ' + o.getAttribute('data-o'), 1);
    }
    paint();
    return {
      answered: function () { return claims.every(function (c, k) { return pick[k] != null; }); },
      touched: function () { return pick.some(function (x) { return x != null; }); },
      right: function () { return claims.every(function (c, k) { return good(k); }); },
      show: function () { each(claims, function (c, k) { cls(c, good(k) ? 'ok' : 'no'); }); },
      lock: function () { locked = true; sh.close(); },
      said: function () {
        var a = [], r = [];
        each(claims, function (c, k) {
          if (good(k)) { return; }
          var opts = $$('.cr-o', c), o = opts[pick[k]], t = txt($('.cr-text', c));
          a.push(t + ' → ' + (o ? optLabel(o) : '–'));
          each(opts, function (x) { if ((x.getAttribute('data-key') || '').toLowerCase() === api.key(api.id, t + ' => ' + x.getAttribute('data-o'), 1)) { r.push(t + ' → ' + optLabel(x)); } });
        });
        return { a: a.join(' | '), c: r.join(' | ') };
      }
    };
  };

  /* ================================================================ 3. WORK IT OUT - read, look up, calculate (Part B)
     <div class="lab gi-calc" data-lab="calc" data-unit="% vol" data-dec="2" data-keys="gbKey(id, unit, value) …">
       <div class="cl-dev"><p class="cl-read" data-script-field="answer">EX · PROPANE: 40 % LEL</p></div>
       <table class="cl-sheet">…data-script-field="answer" cells…</table> */
  LAB.calc = function (root, api) {
    var unit = data(root, 'unit'), dec = parseInt(data(root, 'dec') || '2', 10), K = keys(root), ex = '', val = null, locked = false;
    var tbl = $('.cl-sheet', root), sb = null;
    if (tbl) {
      tbl.hidden = true;
      sb = btn('cl-sheetbtn', say('sheet'), null);
      root.insertBefore(sb, tbl);
      sb.addEventListener('click', function () { tbl.hidden = !tbl.hidden; sb.textContent = say(tbl.hidden ? 'sheet' : 'sheetClose'); api.changed(); }, false);
    }
    var calc = el('div', 'cl-calc', null, root), disp = el('div', 'cl-disp', '<span class="cl-ex"></span><span class="cl-rs"></span>', calc);
    var pad = el('div', 'cl-keys', null, calc);
    each(['7', '8', '9', '÷', '4', '5', '6', '×', '1', '2', '3', '−', '0', '.', '⌫', '+', 'C', '='], function (k) {
      var b = btn('cl-k' + ('÷×−+'.indexOf(k) >= 0 ? ' op' : k === 'C' ? ' c' : k === '=' ? ' eq' : ''), k === '.' ? (T.decimal || '.') : k, pad);
      b.addEventListener('click', function () {
        if (locked) { return; }
        if (k === 'C') { ex = ''; } else if (k === '⌫') { ex = ex.slice(0, -1); }
        else if (k === '=') { var v = ev(); if (v != null) { ex = String(Math.round(v * 1e6) / 1e6); } }
        else if (ex.length < 24) { ex += k; }
        paint(); api.changed();
      }, false);
    });
    var calcFn = null;
    function ev() { calcFn = expr(ex); var v = ex ? calcFn({}) : null; return typeof v === 'number' && isFinite(v) ? v : null; }
    function paint() {
      $('.cl-ex', disp).textContent = (ex || '0').replace(/\./g, T.decimal || '.');
      val = ev();
      $('.cl-rs', disp).textContent = val != null && /[-+×÷−]/.test(ex.slice(1)) ? '= ' + fmtNum(val, Math.max(dec, 3)) : '';
    }
    paint();
    return {
      answered: function () { return val != null; },
      touched: function () { return !!ex; },
      right: function () { return val != null && K.indexOf(api.key(api.id, unit, (Math.round(val * Math.pow(10, dec)) / Math.pow(10, dec)).toFixed(dec))) >= 0; },
      show: function (ok) { cls(calc, ok ? 'ok' : 'no'); },
      lock: function () { locked = true; },
      word: function () { return val != null ? say('handIn', { v: fmtNum(val, dec) + ' ' + unit }) : say('handInEmpty'); },
      said: function () { return { a: val != null ? fmtNum(val, dec) + ' ' + unit : '–', c: '' }; }
    };
  };

  /* ================================================================ 4. PREDICT, THEN SEE (Part B)
     <div class="lab gi-pred" data-lab="predict" data-world="b64 {x:[name,unit,lo,hi], y:[…], at, dec, given:[[x,y,label]], c: b64 curve}"
          data-keys="gbKey(id, y unit, value) …"> + <span class="pr-given" data-script-field="answer">label</span> …
     The trainee drags the point on the "at" line; Check draws the real curve - unless the answer was wrong and the debrief
     rule is on: then only "too high / too low". */
  LAB.predict = function (root, api) {
    var w = world(root), X = w.x || ['', '', 0, 1], Y = w.y || ['', '', 0, 1], dec = w.dec || 1, K = keys(root), pv = null, locked = false;
    var WD = 860, HT = 520, L = 82, R = 830, TOP = 28, B = 462, NS = 'http://www.w3.org/2000/svg';
    function px(x) { return L + (x - X[2]) / (X[3] - X[2]) * (R - L); }
    function py(y) { return B - (y - Y[2]) / (Y[3] - Y[2]) * (B - TOP); }
    function vy(p) { return Math.max(Y[2], Math.min(Y[3], Y[2] + (B - p) / (B - TOP) * (Y[3] - Y[2]))); }
    function tick(lo, hi) { var r = hi - lo, s = Math.pow(10, Math.floor(Math.log(r / 5) / Math.LN10)); if (r / s > 10) { s *= 2; } if (r / s > 10) { s *= 2.5; } return s; }
    var h = '', sx = tick(X[2], X[3]), sy = tick(Y[2], Y[3]), v;
    for (v = Math.ceil(X[2] / sx) * sx; v <= X[3] + 1e-9; v += sx) { h += '<line class="pr-grid" x1="' + px(v) + '" y1="' + TOP + '" x2="' + px(v) + '" y2="' + B + '"/><text class="pr-tk" x="' + px(v) + '" y="' + (B + 24) + '" text-anchor="middle">' + esc(fmtNum(v, sx < 1 ? 1 : 0)) + '</text>'; }
    for (v = Math.ceil(Y[2] / sy) * sy; v <= Y[3] + 1e-9; v += sy) { h += '<line class="pr-grid" x1="' + L + '" y1="' + py(v) + '" x2="' + R + '" y2="' + py(v) + '"/><text class="pr-tk" x="' + (L - 10) + '" y="' + (py(v) + 5) + '" text-anchor="end">' + esc(fmtNum(v, sy < 1 ? 1 : 0)) + '</text>'; }
    h += '<text class="pr-ax" x="' + ((L + R) / 2) + '" y="' + (HT - 4) + '" text-anchor="middle">' + esc(X[0] + (X[1] ? ', ' + X[1] : '')) + '</text>';
    h += '<text class="pr-ax" transform="translate(20,' + ((TOP + B) / 2) + ') rotate(-90)" text-anchor="middle">' + esc(Y[0] + (Y[1] ? ', ' + Y[1] : '')) + '</text>';
    h += '<line class="pr-at" x1="' + px(w.at) + '" y1="' + TOP + '" x2="' + px(w.at) + '" y2="' + B + '"/>';
    each(w.given || [], function (g) { h += '<circle class="pr-g" cx="' + px(g[0]) + '" cy="' + py(g[1]) + '" r="8"/><text class="pr-gl" x="' + (px(g[0]) + 12) + '" y="' + (py(g[1]) - 12) + '">' + esc(g[2] || '') + '</text>'; });
    h += '<path class="pr-curve" d=""/><circle class="pr-truth" r="10" cx="-99" cy="-99"/><g class="pr-h"><circle r="30" class="pr-h0"/><circle r="14" class="pr-h1"/></g><text class="pr-hv"></text>';
    var box = el('div', 'pr-box', '<svg data-audit-ignore viewBox="0 0 ' + WD + ' ' + HT + '" xmlns="' + NS + '" role="img" aria-label="' + esc(X[0] + ' / ' + Y[0]) + '">' + h + '</svg>', root);
    each($$('.pr-given', root), function (g) { g.hidden = true; });
    var svg = $('svg', box), hd = $('.pr-h', svg), hv = $('.pr-hv', svg), fb = el('div', 'gi-fb', '<span class="gi-hint">' + esc(say('dragPoint')) + '</span>', root);
    var y0 = (w.given && w.given.length) ? w.given[w.given.length - 1][1] : (Y[2] + Y[3]) / 2;
    function place(y, set) {
      if (set) { pv = Math.round(y * Math.pow(10, dec)) / Math.pow(10, dec); }
      hd.setAttribute('transform', 'translate(' + px(w.at) + ',' + py(y) + ')');
      hv.setAttribute('x', px(w.at) - 40); hv.setAttribute('y', py(y) + 6); hv.setAttribute('text-anchor', 'end');
      hv.textContent = set ? fmtNum(pv, dec) + ' ' + (Y[1] || '') : say('dragPoint');
    }
    place(y0, false);
    function at(e) { var r = svg.getBoundingClientRect(); return vy((e.clientY - r.top) / r.height * HT); }
    finger(svg, {
      down: function (e) { if (!locked) { place(at(e), true); api.changed(); } },
      move: function (dx, dy, e) { if (!locked) { place(at(e), true); api.changed(); } },
      tap: function () {}
    });
    function curve() {
      var c = [];
      try { c = JSON.parse(decodeURIComponent(escape(W.atob(w.c || '')))); } catch (x) { c = []; }
      if (c.length < 2) { return; }
      var P = c.map(function (q) { return [px(q[0]), py(q[1])]; }), d = 'M' + P[0][0] + ',' + P[0][1], k;
      for (k = 0; k < P.length - 1; k++) {
        var p0 = P[k - 1] || P[k], p1 = P[k], p2 = P[k + 1], p3 = P[k + 2] || p2;
        d += ' C' + (p1[0] + (p2[0] - p0[0]) / 6) + ',' + (p1[1] + (p2[1] - p0[1]) / 6) + ' ' + (p2[0] - (p3[0] - p1[0]) / 6) + ',' + (p2[1] - (p3[1] - p1[1]) / 6) + ' ' + p2[0] + ',' + p2[1];
      }
      var path = $('.pr-curve', svg); path.setAttribute('d', d);
      try { var len = path.getTotalLength(); path.style.strokeDasharray = len; path.style.strokeDashoffset = len; void path.getBoundingClientRect(); path.style.transition = 'stroke-dashoffset 1.4s ease-in-out'; path.style.strokeDashoffset = 0; } catch (x) { /* drawn at once */ }
      return c;
    }
    function good() { return pv != null && K.indexOf(api.key(api.id, Y[1] || 'y', pv.toFixed(dec))) >= 0; }
    return {
      answered: function () { return pv != null; },
      right: good,
      show: function (ok, later) {
        if (ok || !later) {
          var c = curve(), t = null;
          each(c || [], function (q) { if (Math.abs(q[0] - w.at) < 1e-9) { t = q[1]; } });
          if (t != null) { var tr = $('.pr-truth', svg); tr.setAttribute('cx', px(w.at)); tr.setAttribute('cy', py(t)); }
          fb.className = 'gi-fb ' + (ok ? 'ok' : 'no'); fb.innerHTML = '<b>' + esc(say(ok ? 'right' : 'notRight')) + '</b>';
        } else {
          var hi = false;               /* a wrong point is above or below every accepted value: which, from the keys alone */
          for (var s = 1; s < 4000; s++) { var vv = (pv - s * Math.pow(10, -dec)).toFixed(dec); if (K.indexOf(api.key(api.id, Y[1] || 'y', vv)) >= 0) { hi = true; break; } if (parseFloat(vv) < Y[2]) { break; } }
          feedback(fb, false, '', say(hi ? 'tooHigh' : 'tooLow'), true);
        }
      },
      lock: function () { locked = true; },
      word: function () { return say('reveal'); },
      said: function () { return { a: pv != null ? fmtNum(pv, dec) + ' ' + (Y[1] || '') : '–', c: '' }; }
    };
  };

  /* ================================================================ 5. EXPLORE AND FIND - a small live model (Part B)
     The model (one per question, data-world on the question's .gi-model): {var: {name, unit, min, max, step, start},
     choice: {label, items: {name: {k: v}}}, readouts: [{name, unit, expr, max, over}], test: {label, rules: [{if, say, fx}]}}.
     Each part's <div class="lab" data-lab="explore" data-n="1" data-hide="Detector" data-keys="gbKey(id, 'find1', choice|value)"> is
     one challenge: set the model, then lock it in. */
  var MODELS = [];
  function model(sec) {
    for (var i = 0; i < MODELS.length; i++) { if (MODELS[i].sec === sec) { return MODELS[i]; } }
    var host = $('.gi-model', sec);
    if (!host) { return null; }
    var w = world(host), V = w['var'] || { name: 'x', unit: '', min: 0, max: 10, step: 0.1, start: 0 }, ch = w.choice || null;
    var names = ch ? Object.keys(ch.items || {}) : [], M = { sec: sec, x: V.start != null ? V.start : V.min, c: names[0] || '', hide: {}, tests: [], dirty: false, locked: false };
    var dec = Math.max(0, Math.ceil(-Math.log(V.step) / Math.LN10 - 1e-9));
    M.dec = dec;
    var wrap = el('div', 'ex-wrap', null, host), rig = el('div', 'ex-rig', '<canvas></canvas><div class="ex-fx"></div><div class="ex-say"></div>', wrap), side = el('div', 'ex-side', null, wrap);
    var chips = ch ? el('div', 'ex-chips', null, side) : null;
    each(names, function (n) { var b = btn('ex-chip', n, chips); b.addEventListener('click', function () { if (!M.locked && !b.disabled) { M.c = n; paint(); M.touch(); } }, false); });
    var ros = el('div', 'ex-ros', null, side);
    var roEls = [{ name: V.name, unit: V.unit, x: true }].concat(w.readouts || []).map(function (r) { var d = el('div', 'ex-ro', '<span class="k">' + esc(r.name) + '</span><span class="v"></span>', ros); d.__r = r; return d; });
    var sl = el('div', 'ex-sl', null, side), minus = btn('ex-fine', '−', sl), rng = el('input', 'ex-range', null, sl), plus = btn('ex-fine', '+', sl);
    rng.type = 'range'; rng.min = V.min; rng.max = V.max; rng.step = V.step; rng.value = M.x; rng.setAttribute('aria-label', V.name);
    var testB = w.test ? btn('ex-test', w.test.label || say('test'), side) : null;
    var log = el('div', 'ex-log', '<p>' + esc(say('tests')) + '</p><div></div>', side);
    function vars() { var o = { x: M.x }, it = ch && ch.items[M.c], k; o[(V.id || 'x')] = M.x; if (it) { for (k in it) { if (it.hasOwnProperty(k)) { o[k] = it[k]; } } } return o; }
    var fns = {};
    function f(src) { return fns[src] || (fns[src] = expr(src)); }
    function paint() {
      if (chips) { each($$('.ex-chip', chips), function (b) { cls(b, 'sel', txt(b) === M.c); }); }
      var v = vars();
      each(roEls, function (d) {
        var r = d.__r, out = $('.v', d);
        if (r.x) { out.innerHTML = esc(fmtNum(M.x, dec)) + '<small> ' + esc(r.unit || '') + '</small>'; return; }
        if (M.hide[r.name]) { cls(d, 'cover', true); out.textContent = say('covered'); return; }
        cls(d, 'cover', false);
        var val = f(r.expr)(v);
        if (typeof val !== 'number' || !isFinite(val)) { out.textContent = '–'; return; }
        cls(d, 'over', r.max != null && val > r.max);
        out.innerHTML = r.max != null && val > r.max ? esc(r.over || say('over')) : esc(fmtNum(val, r.dec != null ? r.dec : 0)) + '<small> ' + esc(r.unit || '') + '</small>';
      });
      dots();
    }
    var cv = $('canvas', rig), ctx = cv.getContext && cv.getContext('2d'), parts = [], raf = 0;
    function dots() {
      if (!ctx) { return; }
      var wv = cv.width = rig.clientWidth || 300, hv = cv.height = rig.clientHeight || 400, N = 240, g = Math.round(N * (M.x - V.min) / ((V.max - V.min) || 1) * 1.6);
      parts = [];
      for (var k = 0; k < N; k++) { parts.push({ x: Math.random() * wv, y: Math.random() * (hv - 40), vx: (Math.random() - 0.5) * 0.6, vy: (Math.random() - 0.5) * 0.6, g: k < g }); }
      if (!raf) { loop(); }
    }
    function loop() {
      if (!D.body.contains(cv)) { raf = 0; return; }
      var wv = cv.width, hv = cv.height; ctx.clearRect(0, 0, wv, hv);
      each(parts, function (p) {
        p.x += p.vx; p.y += p.vy; if (p.x < 0 || p.x > wv) { p.vx *= -1; } if (p.y < 0 || p.y > hv - 36) { p.vy *= -1; }
        ctx.beginPath(); ctx.arc(p.x, p.y, p.g ? 4.2 : 2.4, 0, 6.3); ctx.fillStyle = p.g ? 'rgba(242,179,61,.9)' : 'rgba(143,194,255,.35)'; ctx.fill();
      });
      raf = W.requestAnimationFrame(loop);
    }
    function setX(v) { M.x = Math.max(V.min, Math.min(V.max, Math.round(v / V.step) * V.step)); rng.value = M.x; paint(); M.touch(); }
    rng.addEventListener('input', function () { if (!M.locked) { setX(parseFloat(rng.value)); } }, false);
    minus.addEventListener('click', function () { if (!M.locked) { setX(M.x - V.step); } }, false);
    plus.addEventListener('click', function () { if (!M.locked) { setX(M.x + V.step); } }, false);
    if (testB) {
      testB.addEventListener('click', function () {
        if (M.locked) { return; }
        var v = vars(), rule = null;
        each(w.test.rules || [], function (r) { if (!rule && (!r['if'] || f(r['if'])(v) === true)) { rule = r; } });
        var fx = $('.ex-fx', rig), sy = $('.ex-say', rig);
        fx.className = 'ex-fx'; void fx.offsetWidth; fx.className = 'ex-fx ' + ((rule && rule.fx) || 'spark');
        sy.textContent = rule ? rule.say : ''; cls(sy, 'on', true); cls(sy, 'hot', !!(rule && rule.fx && rule.fx !== 'none'));
        setTimeout(function () { cls(sy, 'on', false); }, 1900);
        M.tests.unshift((M.c ? M.c + ' ' : '') + fmtNum(M.x, dec) + ' ' + (V.unit || '') + ' → ' + (rule ? rule.say : ''));
        $('div', log).innerHTML = M.tests.slice(0, 8).map(function (t) { return '<span>' + esc(t) + '</span>'; }).join('');
        M.touch();
      }, false);
    }
    M.touch = function () { M.dirty = true; each(M.subs || [], function (fn) { fn(); }); };
    M.only = function (choice) { if (!chips) { return; } each($$('.ex-chip', chips), function (b) { b.disabled = !!choice && txt(b) !== choice; }); if (choice) { M.c = choice; } paint(); };
    M.paint = paint;
    MODELS.push(M);
    $('div', log).innerHTML = '<span class="none">' + esc(say('none')) + '</span>';
    setTimeout(paint, 0);
    return M;
  }
  LAB.explore = function (root, api) {
    var sec = root.closest ? root.closest('.scr') : root.parentNode, M = model(sec), K = keys(root), n = data(root, 'n') || '1', mine = null, active = false;
    if (!M) { return { answered: function () { return false; }, right: function () { return false; }, show: function () {} }; }
    M.subs = M.subs || [];
    M.subs.push(function () { if (active) { api.changed(); } });
    function on() {                                          /* this challenge's conditions: what the model hides, the one choice */
      active = true; M.hide = {};
      each(data(root, 'hide').split('|'), function (h) { if (h) { M.hide[h] = true; } });
      M.only(data(root, 'only') || '');
      M.locked = false; M.dirty = false;
    }
    /* the part is shown when the engine opens it (.on): watch for that once */
    var part = root.closest ? root.closest('.part') : null;
    if (!part || part.classList.contains('on')) { on(); }
    else if (W.MutationObserver) { new W.MutationObserver(function () { if (part.classList.contains('on') && !active) { on(); } }).observe(part, { attributes: true, attributeFilter: ['class'] }); }
    function key() { return api.key(api.id, 'find' + n, (M.c || '') + '|' + M.x.toFixed(M.dec)); }
    return {
      answered: function () { return active && M.dirty; },
      right: function () { return K.indexOf(mine || key()) >= 0; },
      show: function (ok, later) { var fb = $('.gi-fb', root) || el('div', 'gi-fb', null, root); feedback(fb, ok, data(root, 'why'), data(root, 'brief'), later); },
      lock: function () { mine = key(); M.locked = true; active = false; root.setAttribute('data-was', (M.c ? M.c + ' ' : '') + fmtNum(M.x, M.dec)); },
      word: function () { return say('lock'); },
      said: function () { return { a: root.getAttribute('data-was') || '', c: '' }; }
    };
  };

  /* ================================================================ 6. INVESTIGATE - open the sources, pin the evidence (Part B)
     The conclusion is the question's own choices (a .cg, graded by gb_answer.js). This group is the evidence:
     <div class="lab gi-inv" data-lab="evidence" data-min="3">
       <button class="iv-src" data-key="gbKey(id, title, 1|0)"><span class="iv-tg">LOG</span><span class="iv-tl" data-script-field="answer">title</span>
         <span class="iv-raw" data-script-field="answer" hidden>content</span></button> …
     The content's rows are split by ";;", cells by "|" (the first row is the header). */
  LAB.evidence = function (root, api) {
    var srcs = $$('.iv-src', root), min = parseInt(data(root, 'min') || '2', 10), pinned = {}, seen = {}, open = -1, locked = false;
    var list = el('div', 'iv-list'), view = el('div', 'iv-view', '<p class="iv-empty">' + esc(say('openSrc')) + '</p>'), pins = el('div', 'iv-pins');
    root.insertBefore(list, srcs[0]);
    each(srcs, function (s) { list.appendChild(s); });
    root.appendChild(view);
    el('p', 'iv-ph', esc(say('evidence')), root); root.appendChild(pins);
    function body(raw) {
      if (raw.indexOf(';;') < 0 || raw.indexOf('|') < 0) { return '<p class="iv-note">' + esc(raw) + '</p>'; }
      var rows = raw.split(';;').map(function (r) { return r.split('|').map(norm); });
      return '<table class="iv-t">' + rows.map(function (r, i) { return '<tr>' + r.map(function (c) { return (i ? '<td' + (/alarm|trauksme|тревога/i.test(c) ? ' class="al"' : '') + '>' : '<th>') + esc(c) + (i ? '</td>' : '</th>'); }).join('') + '</tr>'; }).join('') + '</table>';
    }
    function paint() {
      each(srcs, function (s, i) { cls(s, 'open', i === open); cls(s, 'pinned', !!pinned[i]); cls(s, 'seen', !!seen[i]); });
      var ids = Object.keys(pinned);
      pins.innerHTML = ids.length ? ids.map(function (i) { return '<span>' + esc(txt($('.iv-tg', srcs[i])) || txt($('.iv-tl', srcs[i]))) + '</span>'; }).join('') : '<em>' + esc(say('noPins')) + '</em>';
      if (open >= 0) {
        var s = srcs[open];
        view.innerHTML = '<div class="iv-vh"><h4>' + esc(txt($('.iv-tl', s))) + '</h4></div><div class="iv-body">' + body(txt($('.iv-raw', s))) + '</div>';
        var pb = btn('iv-pin' + (pinned[open] ? ' on' : ''), say(pinned[open] ? 'pinned' : 'pin'), $('.iv-vh', view));
        pb.addEventListener('click', function () { if (locked) { return; } if (pinned[open]) { delete pinned[open]; } else { pinned[open] = true; } paint(); api.changed(); }, false);
      }
    }
    each(srcs, function (s, i) { s.addEventListener('click', function () { open = i; seen[i] = true; paint(); api.changed(); }, false); });
    function good(i) { return (srcs[i].getAttribute('data-key') || '').toLowerCase() === api.key(api.id, txt($('.iv-tl', srcs[i])), 1); }
    paint();
    return {
      answered: function () { return Object.keys(pinned).length >= Math.min(min, 2); },
      touched: function () { return Object.keys(seen).length > 0; },
      right: function () { var ids = Object.keys(pinned); return ids.length >= min && ids.every(function (i) { return good(i); }); },
      show: function () { each(Object.keys(pinned), function (i) { cls(srcs[i], good(i) ? 'ok' : 'no'); }); },
      lock: function () { locked = true; },
      said: function () { return { a: Object.keys(pinned).map(function (i) { return txt($('.iv-tl', srcs[i])); }).join('; '), c: srcs.filter(function (s, i) { return good(i); }).map(function (s) { return txt($('.iv-tl', s)); }).join('; ') }; }
    };
  };

  /* ================================================================ 7. LINE IT UP - valves on a 3D deck, then the pump (Part B)
     <div class="lab gi-line" data-lab="lineup" data-world="b64 {spec: kit3d spec, valves: {tag: part}, pipes: [{a, b, valve, flow, back}],
          source, goal, out: [names], start: {tag: 'open'|'shut'}}">
       <ul class="lu-orders"><li data-script-field="answer">Tank 2</li> …</ul>  <ul class="lu-valves"><li …>V102</li> … </ul>
     Nothing is keyed: the right line-up is whatever lets the source reach the goal and nothing it must keep out. What
     happens is worked out on the network and shown - cargo into the wrong tank, against a blank, or nowhere. */
  LAB.lineup = function (root, api) {
    var w = world(root), st = {}, sel = null, locked = false, ran = null;
    each(Object.keys(w.start || {}), function (t) { st[t] = w.start[t] === 'open'; });
    var stage = el('div', 'gi-stage lu-stage', null, root), side = el('div', 'lu-side', null, root);
    each($$('.lu-orders, .lu-valves', root), function (u) { side.appendChild(u); });
    var vl = el('div', 'lu-list', null, side), out = el('div', 'gi-fb', null, side);
    var vsheet = el('div', 'lu-sheet', '<div class="t"></div>', stage), bo = btn('lu-o', say('open'), vsheet), bs = btn('lu-s', say('shut'), vsheet);
    var k3 = mount3d(stage, w.spec || {}, function (k) { var t = tagOf(k); if (t) { pick(t); } else if (!k) { pick(null); } });
    el('div', 'gi-tip', esc(say('turnHint')), stage);
    function tagOf(part) { var t = null; each(Object.keys(w.valves || {}), function (x) { if (w.valves[x] === part) { t = x; } }); return t; }
    function name(t) { var li = $('.lu-valves [data-tag="' + t + '"]', root); return li ? txt($('.lu-name', li)) : ''; }
    function set3d() { if (!k3) { return; } each(Object.keys(st), function (t) { var p = w.valves[t]; if (p) { try { k3.state(p + '.shut', st[t] ? 0 : 1); } catch (x) { /* no such state */ } } }); }
    function paint() {
      vl.innerHTML = '';
      each(Object.keys(st), function (t) {
        var b = btn('lu-v' + (t === sel ? ' sel' : ''), '', vl);
        b.innerHTML = '<b>' + esc(t) + '</b><i class="' + (st[t] ? 'o' : 'c') + '">' + esc(say(st[t] ? 'open' : 'shut')) + '</i>';
        b.addEventListener('click', function () { pick(t); }, false);
      });
      if (sel) {
        $('.t', vsheet).innerHTML = '<b>' + esc(sel) + '</b>' + esc(name(sel));
        cls(bo, 'on', st[sel]); cls(bs, 'on', !st[sel]);
      }
      cls(vsheet, 'on', !!sel && !locked);
    }
    function pick(t) { if (locked) { return; } sel = t; if (k3 && t && k3.current() !== w.valves[t]) { k3.select(w.valves[t]); } paint(); }
    function setV(v) { if (locked || !sel) { return; } st[sel] = v; set3d(); paint(); api.changed(); }
    bo.addEventListener('click', function () { setV(true); }, false);
    bs.addEventListener('click', function () { setV(false); }, false);
    function route() {
      var seen = {}, q = [w.source], segs = [];
      seen[w.source] = true;
      while (q.length) {
        var n = q.shift();
        each(w.pipes || [], function (p) {
          if (p.valve && !st[p.valve]) { return; }
          var o = p.a === n ? p.b : p.b === n ? p.a : null;
          if (o && !seen[o]) { seen[o] = true; q.push(o); segs.push({ p: p, fwd: p.a === n }); }
        });
      }
      return { seen: seen, segs: segs };
    }
    function result() {
      var R = route(), bad = [];
      if (!R.segs.length) { return { ok: false, s: say('dead'), R: R }; }
      each(w.out || [], function (n) { if (R.seen[n]) { bad.push(say('into', { n: n })); } });
      if (!R.seen[w.goal]) { bad.push(say('noGoal', { n: w.goal })); }
      return bad.length ? { ok: false, s: bad.join(' '), R: R } : { ok: true, s: say('goalOk', { a: w.source, b: w.goal }), R: R };
    }
    set3d(); paint();
    return {
      answered: function () { return true; },
      touched: function () { return true; },
      right: function () { ran = ran || result(); return ran.ok; },
      show: function (ok) {
        ran = ran || result();
        if (k3) { each(ran.R.segs, function (s) { var f = s.fwd ? s.p.flow : (s.p.back || s.p.flow); if (f) { try { k3.state(f + '.on', 1); } catch (x) { /* no flow part */ } } }); }
        out.className = 'gi-fb ' + (ok ? 'ok' : 'no');
        out.innerHTML = '<b>' + esc(say(ok ? 'right' : 'notRight')) + '</b> ' + esc(ran.s);
        vibe(ok ? 20 : 60);
      },
      lock: function () { locked = true; sel = null; paint(); },
      word: function () { return data(root, 'start') || say('start'); },
      said: function () {
        var open = Object.keys(st).filter(function (t) { return st[t]; });
        return { a: (open.join(', ') || '–') + ' → ' + (ran ? ran.s : ''), c: '' };
      }
    };
  };

  /* ================================================================ 8. INSPECTION ROUND - look around, judge each thing (Part B)
     <div class="lab gi-insp" data-lab="inspect" data-world="b64 {spec: kit3d spec | pano: 'img.jpg', points: {name: part | [yaw, pitch]}}" data-need="5">
       <div class="in-thing" data-key="gbKey(id, name, 'report'|'fine')"><b data-script-field="answer">name</b><p data-script-field="answer">what you see</p></div> …
     The number of problems is said in the question ("there are 4 problems"); a thing never looked at counts as fine. */
  LAB.inspect = function (root, api) {
    var w = world(root), things = $$('.in-thing', root), st = {}, seen = {}, cur = -1, locked = false, need = parseInt(data(root, 'need') || '5', 10);
    var stage = el('div', 'gi-stage in-stage', null, root), side = el('div', 'in-side', null, root);
    var head = el('div', 'in-head', '<p class="in-n"></p>', side), card = el('div', 'in-card', '<p class="in-empty">' + esc(say('inspect')) + '</p>', side);
    var byName = {};
    each(things, function (t, i) { t.hidden = true; byName[txt($('b', t))] = i; });
    function thingOfPart(k) {                     /* a thing may be several parts of the scene: "points": {"thing": ["det", "det_cap"]} */
      var r = -1;
      each(Object.keys(w.points || {}), function (n) { var p = w.points[n]; if ((p === k || (p instanceof Array && p.indexOf(k) >= 0 && typeof p[0] === 'string')) && byName[n] != null) { r = byName[n]; } });
      return r;
    }
    function inspect(i) {
      if (i < 0) { return; }
      cur = i; seen[i] = true;
      var t = things[i], s = st[i];
      card.innerHTML = '<p class="in-name">' + esc(txt($('b', t))) + '</p><p class="in-what">' + esc(txt($('p', t))) + '</p>';
      var row = el('div', 'in-btns', null, card), bf = btn('in-fine' + (s === 'fine' ? ' on' : ''), say('fine'), row), br = btn('in-rep' + (s === 'report' ? ' on' : ''), say('report'), row);
      bf.addEventListener('click', function () { if (!locked) { st[i] = 'fine'; inspect(i); api.changed(); } }, false);
      br.addEventListener('click', function () { if (!locked) { st[i] = 'report'; inspect(i); api.changed(); } }, false);
      count();
    }
    function count() {
      $('.in-n', head).textContent = say('reported', { n: Object.keys(st).filter(function (k) { return st[k] === 'report'; }).length, m: Object.keys(seen).length });
    }
    if (w.pano) { pano(stage, w, function (name) { inspect(byName[name] != null ? byName[name] : -1); }); }
    else { mount3d(stage, w.spec || {}, function (k) { if (k) { inspect(thingOfPart(k)); } }); }
    el('div', 'gi-tip', esc(say('lookHint')), stage);
    count();
    root.__look = function (name) { inspect(byName[name] != null ? byName[name] : -1); };   /* the build's grader looks by name - a 360 photo has no parts to select */
    function good(i) { return (things[i].getAttribute('data-key') || '').toLowerCase() === api.key(api.id, txt($('b', things[i])), st[i] || 'fine'); }
    return {
      answered: function () { return Object.keys(seen).length >= Math.min(need, things.length); },
      touched: function () { return Object.keys(seen).length > 0; },
      right: function () { return things.every(function (t, i) { return good(i); }); },
      show: function () { var n = things.filter(function (t, i) { return good(i); }).length; $('.in-n', head).textContent = n + ' / ' + things.length; },
      lock: function () { locked = true; },
      word: function () { return say('handRound'); },
      said: function () {
        var a = [], c = [];
        each(things, function (t, i) { if (!good(i)) { a.push(txt($('b', t)) + ': ' + say(st[i] === 'report' ? 'report' : 'fine')); c.push(txt($('b', t)) + ': ' + say(st[i] === 'report' ? 'fine' : 'report')); } });
        return { a: a.join(' | '), c: c.join(' | ') };
      }
    };
  };
  /* a 360-degree photograph to look around in (an equirectangular .jpg from the module's assets/img): drag to look,
     + and - to zoom, the buttons do the same; a tap near a point inspects it */
  function pano(stage, w, onPoint) {
    var TH = W.THREE;
    if (!TH) { el('p', 'gi-no3d', esc(say('no3d')), stage); return; }
    var r;
    try { r = new TH.WebGLRenderer({ antialias: true }); } catch (e) { el('p', 'gi-no3d', esc(say('no3d')), stage); return; }
    r.setPixelRatio(Math.min(W.devicePixelRatio || 1, 2));
    stage.appendChild(r.domElement); r.domElement.className = 'pano-cv';
    var sc = new TH.Scene(), cam = new TH.PerspectiveCamera(70, 1, 0.1, 100), yaw = 0, pitch = 0, fov = 70;
    var geo = new TH.SphereGeometry(50, 48, 32); geo.scale(-1, 1, 1);
    sc.add(new TH.Mesh(geo, new TH.MeshBasicMaterial({ map: new TH.TextureLoader().load(w.pano, function () { draw(); }) })));
    var marks = el('div', 'pano-marks', null, stage);
    function dir(yw, pt) { var y = yw * Math.PI / 180, p = pt * Math.PI / 180; return new TH.Vector3(Math.sin(y) * Math.cos(p), Math.sin(p), -Math.cos(y) * Math.cos(p)); }
    function draw() {
      var wd = stage.clientWidth || 800, ht = stage.clientHeight || 500;
      r.setSize(wd, ht, false); cam.aspect = wd / ht; cam.fov = fov; cam.updateProjectionMatrix();
      cam.lookAt(dir(yaw, pitch)); r.render(sc, cam);
    }
    function angles(cx, cy) {
      var rc = r.domElement.getBoundingClientRect(), v = new TH.Vector3((cx - rc.left) / rc.width * 2 - 1, -(cy - rc.top) / rc.height * 2 + 1, 0.5).unproject(cam).normalize();
      return [Math.atan2(v.x, -v.z) * 180 / Math.PI, Math.asin(v.y) * 180 / Math.PI];
    }
    finger(r.domElement, {
      move: function (dx, dy, e) { var s = fov / (stage.clientWidth || 800); yaw = this.y0 - dx * s; pitch = Math.max(-80, Math.min(80, this.p0 + dy * s)); draw(); },
      down: function () { this.y0 = yaw; this.p0 = pitch; },
      tap: function (e) {
        var a = angles(e.clientX, e.clientY), best = null, bd = 12;
        each(Object.keys(w.points || {}), function (n) {
          var p = w.points[n]; if (!(p instanceof Array)) { return; }
          var d = Math.sqrt(Math.pow(((a[0] - p[0] + 540) % 360) - 180, 2) + Math.pow(a[1] - p[1], 2));
          if (d < bd) { bd = d; best = n; }
        });
        if (best) { onPoint(best); }
      }
    });
    var bar = el('div', 'gi-bar', null, stage);
    each([['←', function () { yaw -= 6; }], ['→', function () { yaw += 6; }], ['↑', function () { pitch = Math.min(80, pitch + 5); }], ['↓', function () { pitch = Math.max(-80, pitch - 5); }],
      ['+', function () { fov = Math.max(30, fov - 6); }], ['−', function () { fov = Math.min(90, fov + 6); }]], function (b) {
      var x = btn('', b[0], bar); x.addEventListener('click', function () { b[1](); draw(); }, false);
    });
    W.addEventListener('resize', draw);
    setTimeout(draw, 30);
  }

  /* ================================================================ 9. TAKE IT APART - a 3D model to explore (Part B)
     The model, once per question (.gi-model3d data-world): {spec: kit3d spec, names: {part: name}, explode: {part: [x,y,z]},
     xray: [parts], operate: {label, states: {word: {rot: {part: degrees about y}, kit: {"p.on": 1}}}, start: word}}.
     Each part of the question is one step:
       <div class="lab" data-lab="takeapart" data-step="find" data-ask="…" data-key="gbKey(id, ask, rightName)">  tap the part, then answer
       <div class="lab" data-lab="takeapart" data-step="set" data-ask="…" data-key="gbKey(id, ask, word)">        operate it, then hand in */
  var MODELS3 = [];
  function model3(sec) {
    for (var i = 0; i < MODELS3.length; i++) { if (MODELS3[i].sec === sec) { return MODELS3[i]; } }
    var host = $('.gi-model3d', sec);
    if (!host) { return null; }
    var w = world(host), M = { sec: sec, w: w, sel: null, ex: 0, xr: false, state: (w.operate && w.operate.start) || '', subs: [] };
    var stage = el('div', 'gi-stage ta-stage', null, host), side = el('div', 'ta-tools', null, host);
    var card = el('div', 'ta-card', '<p class="ta-name">' + esc(say('tapPart')) + '</p>', side);
    var exRow = el('div', 'ta-ex', '<span>' + esc(say('explode')) + '</span>', side), exR = el('input', 'ex-range', null, exRow);
    exR.type = 'range'; exR.min = 0; exR.max = 1; exR.step = 0.01; exR.value = 0; exR.setAttribute('aria-label', say('explode'));
    var row = el('div', 'ta-row', null, side), xb = btn('ta-t', say('xray'), row), ob = w.operate ? btn('ta-t', w.operate.label || say('operate'), row) : null;
    var k3 = mount3d(stage, w.spec || {}, function (k) { M.sel = k; tell(); });
    el('div', 'gi-tip', esc(say('turnHint')), stage);
    M.k3 = k3;
    function nameOf(k) { return (w.names || {})[k] || ''; }
    var says = {};
    each($$('.ta-part', sec), function (p) { says[txt($('b', p))] = txt($('span', p)); p.hidden = true; });
    function tell() {
      var n = nameOf(M.sel);
      card.innerHTML = n ? '<p class="ta-name">' + esc(n) + '</p><p class="ta-says">' + esc(says[n] || '') + '</p>' : '<p class="ta-name">' + esc(say('tapPart')) + '</p>';
      each(M.subs, function (fn) { fn(); });
    }
    /* the parts' meshes, moved apart along their own way and turned about their own centre - straight on three.js */
    var S = k3 && k3.scene, base = [];
    if (S) {
      each(Object.keys(S.parts || {}), function (k) {
        each(S.parts[k].items || [], function (m) { base.push({ m: m, k: k, p: m.position.clone(), q: m.quaternion.clone() }); });
      });
    }
    var TH = W.THREE;
    function pose() {
      if (!S || !TH) { return; }
      var ops = (w.operate && w.operate.states && w.operate.states[M.state]) || {}, R = ops.rot || {};
      each(base, function (b) {
        var d = (w.explode || {})[b.k] || [0, 0, 0], deg = R[b.k] || 0, ax = (w.operate && w.operate.axis) || [0, 0];
        var p = b.p.clone(), q = b.q.clone();
        if (deg) {                               /* turned about the operating axis - a vertical line through [x, z] (a valve's stem) */
          var piv = new TH.Vector3(ax[0], 0, ax[1]);
          var Q = new TH.Quaternion().setFromAxisAngle(new TH.Vector3(0, 1, 0), deg * Math.PI / 180);
          p.sub(piv).applyQuaternion(Q).add(piv); q.premultiply(Q);
        }
        b.m.position.set(p.x + d[0] * M.ex, p.y + d[1] * M.ex, p.z + d[2] * M.ex); b.m.quaternion.copy(q);
      });
      each(Object.keys(ops.kit || {}), function (n) { try { k3.state(n, ops.kit[n]); } catch (x) { /* none */ } });
      if (k3) { k3.render(); }
    }
    exR.addEventListener('input', function () { M.ex = parseFloat(exR.value); pose(); }, false);
    xb.addEventListener('click', function () {
      M.xr = !M.xr; cls(xb, 'on', M.xr);
      each(w.xray || [], function (k) { try { k3.state(k + '.ghost', M.xr ? 1 : 0); } catch (x) { /* none */ } });
    }, false);
    if (ob) {
      ob.addEventListener('click', function () {
        if (M.locked) { return; }
        var words = Object.keys(w.operate.states || {}), i = words.indexOf(M.state);
        M.state = words[(i + 1) % words.length]; pose(); each(M.subs, function (fn) { fn(); });
      }, false);
    }
    M.name = nameOf;
    MODELS3.push(M);
    setTimeout(pose, 50);
    return M;
  }
  LAB.takeapart = function (root, api) {
    var sec = root.closest ? root.closest('.scr') : root.parentNode, M = model3(sec), step = data(root, 'step'), ask = data(root, 'ask'), mine = null, active = false;
    if (!M) { return { answered: function () { return false; }, right: function () { return false; }, show: function () {} }; }
    var part = root.closest ? root.closest('.part') : null;
    /* a set step can be handed in as it stands (its position may already be the one asked): Check wakes when the step opens */
    function on() { active = true; M.locked = false; if (step === 'find') { M.sel = null; if (M.k3) { M.k3.select(null); } } setTimeout(api.changed, 0); }
    if (!part || part.classList.contains('on')) { on(); }
    else if (W.MutationObserver) { new W.MutationObserver(function () { if (part.classList.contains('on') && !active) { on(); } }).observe(part, { attributes: true, attributeFilter: ['class'] }); }
    M.subs.push(function () { if (active) { api.changed(); } });
    function value() { return step === 'find' ? M.name(M.sel) : M.state; }
    return {
      answered: function () { return active && (step !== 'find' || !!M.name(M.sel)); },
      right: function () { return (root.getAttribute('data-key') || '').toLowerCase() === api.key(api.id, ask, mine != null ? mine : value()); },
      show: function (ok, later) { var fb = $('.gi-fb', root) || el('div', 'gi-fb', null, root); feedback(fb, ok, data(root, 'why'), data(root, 'brief'), later); },
      lock: function () { mine = value(); active = false; M.locked = true; },
      word: function () { return step === 'find' ? say('answerPart') : say('setDone'); },
      said: function () { return { a: mine || '–', c: '' }; }
    };
  };

  /* ================================================================ 10. TEST BEFORE ENTRY - an instrument, a space, a procedure (Part B)
     <div class="lab gi-atm" data-lab="atmosphere" data-world="b64 {space, depth, hose, delay, gases: [{name, unit, pts: [[d, v]], lo, hi, dec}]}"
          data-levels="3" data-keys-0="gbKey(id, 'L0', depth) …" data-keys-1="…" …>
       <p class="at-g" data-script-field="answer">O₂ %</p> …
     Zero in fresh air (the hose end at the hatch), lower the hose, wait for the sample to come up, record. A reading taken
     before the sample arrived is marked and does not count. Every level the course asks for needs a fresh reading. */
  LAB.atmosphere = function (root, api) {
    var w = world(root), G = w.gases || [], depthMax = w.depth || 16, hose = w.hose || 4, delay = w.delay || 0.28;
    var nL = parseInt(data(root, 'levels') || '0', 10), LK = [], k;
    for (k = 0; k < nL; k++) { LK.push(keys(root, 'keys-' + k)); }
    var depth = 0, shown = 0, zeroed = false, transit = null, rows = [], locked = false;
    each($$('.at-g', root), function (g) { g.hidden = true; });
    var wrap = el('div', 'at-wrap', null, root), sect = el('div', 'at-sect', null, wrap), side = el('div', 'at-side', null, wrap);
    var Y0 = 120, Y1 = 590, PX = (Y1 - Y0) / depthMax, NS = 'http://www.w3.org/2000/svg';
    function Y(d) { return Y0 + d * PX; }
    var ticks = '', m;
    for (m = 2; m < depthMax; m += 2) { ticks += '<line x1="112" x2="132" y1="' + Y(m) + '" y2="' + Y(m) + '" class="at-tk"/><text x="140" y="' + (Y(m) + 5) + '" class="at-tt">' + m + ' m</text>'; }
    var rungs = '';
    for (m = Y0 + 20; m < Y1; m += 28) { rungs += '<line x1="470" x2="500" y1="' + m + '" y2="' + m + '" class="at-rung"/>'; }
    sect.innerHTML = '<svg data-audit-ignore viewBox="0 0 760 620" xmlns="' + NS + '" role="img" aria-label="' + esc(w.space || '') + '">' +
      '<rect x="0" y="' + (Y0 - 14) + '" width="760" height="14" class="at-deck"/><rect x="110" y="' + Y0 + '" width="540" height="' + (Y1 - Y0) + '" class="at-tank"/>' +
      '<rect x="340" y="' + (Y0 - 14) + '" width="80" height="14" class="at-hole"/><rect x="330" y="' + (Y0 - 44) + '" width="10" height="30" class="at-coam"/><rect x="420" y="' + (Y0 - 44) + '" width="10" height="30" class="at-coam"/>' +
      '<line x1="470" x2="470" y1="' + Y0 + '" y2="' + Y1 + '" class="at-rail"/><line x1="500" x2="500" y1="' + Y0 + '" y2="' + Y1 + '" class="at-rail"/>' + rungs + ticks +
      '<text x="160" y="' + (Y1 - 16) + '" class="at-tt">' + esc(w.space || '') + '</text>' +
      '<rect x="560" y="' + (Y0 - 70) + '" width="70" height="52" rx="12" class="at-met"/><rect x="570" y="' + (Y0 - 62) + '" width="50" height="22" rx="4" class="at-mets"/>' +
      '<path class="at-hose"/><g class="at-end"><circle r="26" class="at-e0"/><circle r="11" class="at-e1"/></g><text class="at-dl"></text></svg>';
    var lv = el('div', 'at-lv', null, sect);
    /* lower and raise in metres - never a button per level the course asks for: which levels to test is the task */
    each([['raise', -1], ['lower', 1], ['toHatch', null]], function (q) {
      var b = btn('', say(q[0]), lv); b.addEventListener('click', function () { setDepth(q[1] == null ? 0 : depth + q[1]); }, false);
    });
    var meter = el('div', 'at-meter', null, side), scr = el('div', 'at-scr', null, meter);
    var cells = G.map(function (g) { return el('div', 'at-c', '<span class="k">' + esc(g.name) + '</span><span class="v">--</span>', scr); });
    var bar = el('div', 'at-bar', '<i></i>', scr), stat = el('div', 'at-stat', '', scr);
    var keysRow = el('div', 'at-keys', null, meter), kz = btn('', say('zero'), keysRow), kr = btn('', say('record'), keysRow);
    var log = el('table', 'at-log', null, side);
    var svg = $('svg', sect);
    function at(d, g) {
      var p = g.pts || [[0, 0]], i;
      if (d <= p[0][0]) { return p[0][1]; }
      for (i = 0; i < p.length - 1; i++) { if (d <= p[i + 1][0]) { return p[i][1] + (p[i + 1][1] - p[i][1]) * (d - p[i][0]) / ((p[i + 1][0] - p[i][0]) || 1); } }
      return p[p.length - 1][1];
    }
    function alarm(g, v) { return (g.lo != null && v < g.lo) || (g.hi != null && v >= g.hi); }
    function hoseDraw() {
      var y = Y(depth), d = 'M560,' + (Y0 - 40) + ' C500,' + (Y0 - 70) + ' 420,' + (Y0 - 60) + ' 380,' + (Y0 - 20) + ' L380,' + y;
      $('.at-hose', svg).setAttribute('d', d); $('.at-end', svg).setAttribute('transform', 'translate(380,' + y + ')');
      var t = $('.at-dl', svg); t.setAttribute('x', 404); t.setAttribute('y', y + 6); t.textContent = depth ? fmtNum(depth, 1) + ' m' : say('hatch');
    }
    function setDepth(d) {
      if (locked) { return; }
      d = Math.max(0, Math.min(depthMax - 0.5, Math.round(d * 2) / 2));
      if (d === depth) { return; }
      depth = d; hoseDraw();
      if (zeroed) { transit = { t0: Date.now(), t: 0, total: (hose + depth) * delay, to: depth }; }
      paint(); api.changed();
    }
    finger(svg, {
      down: function (e) { mv(e); }, move: function (dx, dy, e) { mv(e); }, tap: function () {}
    });
    function mv(e) { var rc = svg.getBoundingClientRect(); setDepth(((e.clientY - rc.top) / rc.height * 620 - Y0) / PX); }
    function paint() {
      kz.disabled = zeroed || locked; kr.disabled = !zeroed || locked;
      if (!zeroed) {
        each(cells, function (c) { $('.v', c).textContent = '--'; cls($('.v', c), 'al', false); });
        stat.textContent = say(depth > 0.5 ? 'bringUp' : 'zeroFirst'); $('i', bar).style.width = '0'; return;
      }
      each(G, function (g, i) { var v = at(shown, g), o = $('.v', cells[i]); o.textContent = fmtNum(v, g.dec != null ? g.dec : 0); cls(o, 'al', alarm(g, v)); });
      if (transit) { stat.textContent = say('travelling', { s: fmtNum(Math.max(0, transit.total - transit.t), 1) }); $('i', bar).style.width = (transit.t / transit.total * 100) + '%'; }
      else {
        var al = G.some(function (g) { return alarm(g, at(shown, g)); });
        stat.textContent = say(al ? 'alarm' : 'steady', { d: shown ? fmtNum(shown, 1) + ' m' : say('hatch') }); $('i', bar).style.width = '100%';
      }
    }
    function arrive() {
      if (!transit) { return; }
      transit.t = (Date.now() - transit.t0) / 1000;
      if (transit.t >= transit.total) { shown = transit.to; transit = null; if (G.some(function (g) { return alarm(g, at(shown, g)); })) { vibe([60, 40, 60]); } }
    }
    var timer = setInterval(function () {
      if (!D.body.contains(root)) { clearInterval(timer); return; }
      if (transit && !locked) { arrive(); paint(); }
    }, 100);
    kz.addEventListener('click', function () { if (depth > 0.5 || locked) { return; } zeroed = true; shown = 0; transit = null; paint(); api.changed(); }, false);
    kr.addEventListener('click', function () {
      if (locked) { return; }
      arrive();
      rows.push({ d: depth, s: shown, fresh: !transit && shown === depth });
      log.innerHTML = '<tr><th>m</th>' + G.map(function (g) { return '<th>' + esc(g.name) + '</th>'; }).join('') + '</tr>' +
        rows.slice(-5).map(function (r) {
          return '<tr class="' + (r.fresh ? '' : 'stale') + '"><td>' + (r.d ? fmtNum(r.d, 1) : '0') + (r.fresh ? '' : ' *') + '</td>' +
            G.map(function (g) { var v = at(r.s, g); return '<td class="' + (alarm(g, v) ? 'al' : '') + '">' + fmtNum(v, g.dec != null ? g.dec : 0) + '</td>'; }).join('') + '</tr>';
        }).join('') + (rows.some(function (r) { return !r.fresh; }) ? '<tr><td colspan="' + (G.length + 1) + '" class="note">' + esc(say('early')) + '</td></tr>' : '');
      api.changed();
    }, false);
    hoseDraw(); paint();
    function covered(i) { return rows.some(function (r) { return r.fresh && LK[i].indexOf(api.key(api.id, 'L' + i, r.d.toFixed(1))) >= 0; }); }
    return {
      answered: function () { return rows.length > 0; },
      right: function () { for (var i = 0; i < nL; i++) { if (!covered(i)) { return false; } } return true; },
      show: function (ok, later) { var fb = $('.gi-fb', root) || el('div', 'gi-fb', null, side); feedback(fb, ok, data(root, 'why'), data(root, 'brief'), later); },
      lock: function () { locked = true; paint(); },
      word: function () { return say('samplesDone'); },
      said: function () {
        var fr = rows.filter(function (r) { return r.fresh; }).map(function (r) { return fmtNum(r.d, 1) + ' m'; }), st = rows.length - fr.length;
        return { a: (fr.join(', ') || '–') + (st ? ' (+' + st + ' *)' : ''), c: '' };
      }
    };
  };
}());
