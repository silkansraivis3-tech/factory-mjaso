/* ==========================================================================
   gb_lab.js - the shared shell of the higher-level tablet tasks.

   WHY IT EXISTS. Simple tasks can be hand-written per module. Tasks where the
   screen answers back - a live system, a drawing, a survey, a chart that is
   run - cannot: written again for every module they come out different and
   broken. So everything a task needs that is NOT its subject lives here once:

     the one big button      GBLab.go(label, fn) / GBLab.goEnabled(bool)
     calm feedback           GBLab.toast(text, kind)        kind: ok | hint | no | info
     what happened           GBLab.show({img, tag, title, text, kind, buttons}) -> a sheet over the task,
                             with the photograph of what happened on top when img is given
     small sounds            GBLab.sfx('tap' | 'good' | 'bad' | 'win')
     how sure are you?       GBLab.sure(fn)                 fn('guess' | 'think' | 'sure')
     the result              GBLab.finish({items, mode, pass})  ring, calibration, report ONCE
     answer keys             GBLab.key(id, text, value)     FNV-1a, as classroom-system.json
     drag, or tap then tap   GBLab.drag({items, targets, onDrop(item, target, point), root})
     where on the photo      GBLab.toScene(event) -> {x %, y %, inside} · GBLab.nearest(p, list, maxPct)
     show the gesture once   GBLab.hand(kind, fromEl, toEl)
     always clear            GBLab.intro({title, text, steps, start, onStart}) the opening card ·
                             GBLab.now(html, ''|'done'|'warn') what to do now · GBLab.hint(fn) ·
                             GBLab.goReady(bool) the big button glows when it is the next move
     sound                   GBLab.sound.play([[hz, ms, gapMs], ...])
     the classroom           GBLab.on('team' | 'timer', fn)
     the photograph          <div class="tl-scene" data-aspect="16:9"> img.tl-photo + .tl-pin at % </div>,
                             fitted whole inside the stage (GBLab.fitScenes() after changing one)

   THE CLASSROOM CONTRACT (course-factory/knowledge/classroom-system.json):
   one gb-task-done per opening, items capped at 40 (t 90, a/c 120, w 400
   characters), head '' on a self-check and PASSED / NOT PASSED on a module
   check, no "start again" inside the classroom frame, no countdown of our own.

   Plain ES5, no dependencies, nothing fetched. Safe on an old Android WebView.
   ========================================================================== */
(function (W, D) {
  'use strict';

  var cfg = { code: '', title: '', mode: 'self', pass: 0.8 };
  var done = false, sureLog = [], handlers = { team: [], timer: [] };

  function $(s, r) { return (r || D).querySelector(s); }
  function el(tag, cls, html) { var e = D.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function cut(s, n) { s = String(s == null ? '' : s).replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function inClassroom() { try { return W.parent !== W; } catch (e) { return true; } }

  /* ---- answer keys: gbKey, byte for byte as the classroom rulebook ---------- */
  function key(id, text, value) {
    var s = id + '|' + String(text).replace(/\s+/g, ' ').trim() + '|' + value, b, h = 0x811c9dc5, i;
    if (W.TextEncoder) b = new TextEncoder().encode(s);
    else { b = []; s = unescape(encodeURIComponent(s)); for (i = 0; i < s.length; i++) b.push(s.charCodeAt(i)); }
    for (i = 0; i < b.length; i++) { h ^= b[i]; h = Math.imul(h, 0x01000193) >>> 0; }
    return ('0000000' + h.toString(16)).slice(-8);
  }

  /* ---- the one button ---------------------------------------------------------- */
  var goFn = null, goLast = 0;
  function go(label, fn) {
    var b = $('.tl-go');
    if (!b) return;
    b.textContent = label;
    goFn = fn || null;
    b.disabled = !fn;
  }
  function goEnabled(on) { var b = $('.tl-go'); if (b) b.disabled = !on; }

  /* ---- calm feedback ------------------------------------------------------------- */
  var toastT = 0;
  function toast(text, kind) {
    var t = $('.tl-toast');
    if (!t) { t = el('div', 'tl-toast'); ($('.tl-bar') || D.body).appendChild(t); }
    t.className = 'tl-toast ' + (kind || 'info');
    t.textContent = text;
    // next frame, so the transition runs even when one toast replaces another
    W.requestAnimationFrame(function () { t.className += ' on'; });
    clearTimeout(toastT);
    toastT = setTimeout(function () { t.className = t.className.replace(' on', ''); }, kind === 'hint' ? 5200 : 3800);
  }

  /* ---- a sheet over the task: what happened, a choice, the result ------------------- */
  var openSheet = null;
  function show(o) {
    // only ever one sheet: a new one replaces the old one, never stacks on it
    if (openSheet) openSheet.close();
    var veil = el('div', 'tl-veil'), sheet = el('div', 'tl-sheet ' + (o.kind || ''));
    var h = '';
    if (o.img) h += '<div class="tl-shot"><img src="' + esc(o.img) + '" alt=""></div>';
    h += '<div class="tl-in">';
    if (o.tag) h += '<span class="tl-tag">' + esc(o.tag) + '</span>';
    if (o.title) h += '<h2>' + esc(o.title) + '</h2>';
    if (o.text) h += '<p>' + o.text + '</p>';
    sheet.innerHTML = h + '</div>';
    var inner = sheet.querySelector('.tl-in'), shot = sheet.querySelector('.tl-shot img');
    // a photograph not made yet: the sheet simply has no picture, never a broken one
    if (shot) shot.onerror = function () { var s = shot.parentNode; if (s && s.parentNode) s.parentNode.removeChild(s); };
    if (o.node) inner.appendChild(o.node);
    if (o.kind === 'no') sfx('bad'); else if (o.kind === 'ok') sfx('good');
    var btns = o.buttons || [{ label: 'Continue' }];
    var row = el('div', 'tl-row');
    btns.forEach(function (b) {
      var x = el('button', b.primary === false ? 'tl-btn' : 'tl-go', esc(b.label));
      x.type = 'button';
      x.addEventListener('click', function () { if (closed) return; close(); if (b.fn) b.fn(); });
      row.appendChild(x);
    });
    if (btns.length) inner.appendChild(row);
    veil.appendChild(sheet);
    D.body.appendChild(veil);
    W.requestAnimationFrame(function () { veil.className += ' on'; });
    var closed = false, handle = { close: close, sheet: sheet };
    function close() { closed = true; if (veil.parentNode) veil.parentNode.removeChild(veil); if (openSheet === handle) openSheet = null; }
    openSheet = handle;
    return handle;
  }

  /* ---- how sure are you? (before Check - a safety officer's most useful habit) ------- */
  function sure(fn) {
    var box = el('div', 'tl-sure');
    var opts = [['guess', 'Guessing', 'not sure at all'], ['think', 'I think so', 'fairly sure'], ['sure', 'Sure', 'I would act on it']];
    var s, picked = false;
    opts.forEach(function (o) {
      var n = o[0] === 'guess' ? 1 : o[0] === 'think' ? 2 : 3, bars = '';
      for (var j = 1; j <= 3; j++) bars += '<i class="' + (j <= n ? 'f' : '') + '" style="height:' + (6 + j * 6) + 'px"></i>';
      var b = el('button', 'tl-btn', '<span class="tl-bars">' + bars + '</span><b>' + o[1] + '</b><em>' + o[2] + '</em>');
      b.type = 'button';
      b.addEventListener('click', function () { if (picked) return; picked = true; s.close(); fn(o[0]); });
      box.appendChild(b);
    });
    s = show({ title: 'How sure are you?', text: 'Answer honestly - it is not scored. It shows you which answers to trust.', node: box, buttons: [] });
  }
  function sureNote(level, ok) { sureLog.push({ level: level, ok: !!ok }); }

  /* ---- the result: ring, calibration, the reasons, and ONE report ------------------- */
  function finish(r) {
    if (done) return;
    done = true;
    var items = (r.items || []).slice(0, 40), ok = 0, i;
    for (i = 0; i < items.length; i++) if (items[i].ok) ok++;
    var total = r.total != null ? r.total : items.length;
    if (r.ok != null) ok = r.ok;
    var mode = r.mode || cfg.mode, pass = r.pass != null ? r.pass : cfg.pass;
    var head = mode === 'check' ? (total && ok / total >= pass ? 'PASSED' : 'NOT PASSED') : '';

    var node = el('div', 'tl-result');
    var C = 2 * Math.PI * 62, frac = total ? ok / total : 0;
    node.innerHTML =
      '<svg class="tl-ring" viewBox="0 0 150 150" aria-hidden="true">' +
      '<defs><linearGradient id="tl-grad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#53A7DB"/><stop offset="1" stop-color="#7FD9B5"/></linearGradient></defs>' +
      '<circle class="bg" cx="75" cy="75" r="62"/>' +
      '<circle class="fg" cx="75" cy="75" r="62" transform="rotate(-90 75 75)" stroke-dasharray="' + C + '" stroke-dashoffset="' + C + '"/>' +
      '<text x="75" y="82" text-anchor="middle">' + ok + '</text>' +
      '<text class="of" x="75" y="104" text-anchor="middle">of ' + total + '</text></svg>' +
      (head ? '<div class="tl-head ' + (head === 'PASSED' ? 'pass' : 'fail') + '">' + head + '</div>' : '');

    // calibration: sure-and-wrong is the dangerous one, and says so
    if (sureLog.length) {
      var sw = 0, sr = 0, gr = 0;
      sureLog.forEach(function (x) {
        if (x.level === 'sure' && !x.ok) sw++;
        if (x.level === 'sure' && x.ok) sr++;
        if (x.level === 'guess' && x.ok) gr++;
      });
      var line = 'Sure and right: <b>' + sr + '</b>. ';
      if (sw) line += 'Sure but wrong: <b>' + sw + '</b> - on board those are the dangerous ones; read them first. ';
      if (gr) line += 'Guessed and right: <b>' + gr + '</b> - worth learning properly.';
      if (!sw && !gr) line += 'Your confidence matched your answers - good.';
      node.appendChild(el('div', 'tl-cal', line));
    }
    var ul = el('ul', 'tl-items');
    items.forEach(function (it) {
      ul.appendChild(el('li', it.ok ? 'ok' : 'no',
        '<i>' + (it.ok ? '✓' : '✕') + '</i><span>' + esc(it.t) + '</span>' + (it.w ? '<small>' + esc(it.w) + '</small>' : '')));
    });
    if (items.length) node.appendChild(ul);

    var buttons = [{ label: 'Done', primary: true }];
    if (!inClassroom()) buttons.push({ label: 'Start again', primary: false, fn: function () { location.reload(); } });
    show({ title: mode === 'check' ? 'Module check' : 'Your result', node: node, buttons: buttons });
    sfx(frac >= 0.8 ? 'win' : 'good');
    [].forEach.call(D.querySelectorAll('.tl-items li'), function (li, n) { li.style.animationDelay = (0.5 + n * 0.08) + 's'; });
    setTimeout(function () { var fg = $('.tl-ring .fg'); if (fg) fg.setAttribute('stroke-dashoffset', String(C * (1 - frac))); }, 60);
    go('Finished', null);

    var msg = {
      type: 'gb-task-done', code: cfg.code, title: cfg.title, ok: ok, total: total, head: head,
      items: items.map(function (it) {
        return { t: cut(it.t, 90), ok: !!it.ok, a: cut(it.a, 120), c: cut(it.c, 120), w: cut(it.w, 400) };
      }),
      answered: r.answered != null ? r.answered : items.length, of: r.of != null ? r.of : total, timeout: !!r.timeout
    };
    if (r.scope) msg.scope = r.scope;
    try { W.parent.postMessage(msg, '*'); } catch (e) {}
  }

  /* ---- drag, or tap the item then tap where it goes (L42: never drag only) -----------
     onDrop(item, target, point) - point is where the finger let go, in screen px, so a page
     can place the item exactly there. A touch the system cancels (a scroll, a call, a second
     finger) ends the drag cleanly: nothing is left hanging under the finger, nothing is lost. */
  function drag(o) {
    var root = o.root || D, picked = null, ghost = null, start = null, moved = false, over = null, justDragged = 0;
    function targetAt(x, y) {
      if (ghost) ghost.style.display = 'none';
      var t = D.elementFromPoint(x, y);
      if (ghost) ghost.style.display = '';
      while (t && t !== D.body) { if (t.matches && t.matches(o.targets)) return t; t = t.parentNode; }
      return null;
    }
    function clear() { if (picked) picked.classList.remove('tl-picked'); picked = null; }
    function dropGhost() {
      if (ghost && ghost.parentNode) ghost.parentNode.removeChild(ghost);
      ghost = null;
      if (over) over.classList.remove('tl-over');
      over = null;
    }
    function cancel() { dropGhost(); start = null; moved = false; }
    root.addEventListener('pointerdown', function (e) {
      if (e.isPrimary === false || start) return;
      var it = e.target.closest ? e.target.closest(o.items) : null;
      if (!it || it.getAttribute('aria-disabled') === 'true') return;
      start = { x: e.clientX, y: e.clientY, it: it, id: e.pointerId };
      moved = false;
    });
    D.addEventListener('pointermove', function (e) {
      if (!start || e.pointerId !== start.id) return;
      var dx = e.clientX - start.x, dy = e.clientY - start.y;
      if (!moved && dx * dx + dy * dy < 100) return;
      if (!moved) {
        moved = true;
        clear();
        var r = start.it.getBoundingClientRect();
        ghost = start.it.cloneNode(true);
        ghost.removeAttribute('id');
        [].forEach.call(ghost.querySelectorAll('[id]'), function (n) { n.removeAttribute('id'); });
        ghost.className += ' tl-ghost';
        ghost.style.width = r.width + 'px'; ghost.style.height = r.height + 'px';
        ghost.style.margin = '0';
        ghost.offX = start.x - r.left; ghost.offY = start.y - r.top;
        D.body.appendChild(ghost);
      }
      ghost.style.left = (e.clientX - ghost.offX) + 'px';
      ghost.style.top = (e.clientY - ghost.offY) + 'px';
      var t = targetAt(e.clientX, e.clientY);
      if (t !== over) { if (over) over.classList.remove('tl-over'); over = t; if (over) over.classList.add('tl-over'); }
    });
    D.addEventListener('pointerup', function (e) {
      if (!start || e.pointerId !== start.id) return;
      var it = start.it, wasMoved = moved, x = e.clientX, y = e.clientY;
      var t = wasMoved ? targetAt(x, y) : null;
      cancel();
      if (wasMoved) {
        justDragged = Date.now();
        if (t) o.onDrop(it, t, { x: x, y: y });
        return;
      }
      if (picked === it) clear();
      else { clear(); picked = it; it.classList.add('tl-picked'); if (o.onPick) o.onPick(it); }
    });
    D.addEventListener('pointercancel', function (e) { if (start && e.pointerId === start.id) cancel(); });
    W.addEventListener('blur', cancel);
    D.addEventListener('visibilitychange', cancel);
    // the second tap of tap-then-tap (the click a browser sends straight after a drag is the drag's own)
    root.addEventListener('click', function (e) {
      if (!picked || Date.now() - justDragged < 350) return;
      var t = e.target.closest ? e.target.closest(o.targets) : null;
      if (t && !(e.target.closest(o.items) === picked)) { var it = picked; clear(); o.onDrop(it, t, { x: e.clientX, y: e.clientY }); }
    });
    return { clear: clear, picked: function () { return picked; } };
  }

  /* ---- where on the photograph: a point in % of a .tl-scene, and the nearest of a list --- */
  function toScene(e, scene) {
    var sc = scene || $('.tl-scene'), r = sc.getBoundingClientRect();
    return { x: (e.clientX - r.left) / r.width * 100, y: (e.clientY - r.top) / r.height * 100, inside: e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom };
  }
  function nearest(p, list, maxPct) {
    var best = null, bd = 1e9;
    list.forEach(function (q) { var d = Math.sqrt((p.x - q.x) * (p.x - q.x) + (p.y - q.y) * (p.y - q.y)); if (d < bd) { bd = d; best = q; } });
    return maxPct == null || bd <= maxPct ? best : null;
  }

  /* ---- the hand: shows a gesture once per kind of task ------------------------------- */
  function hand(kind, fromEl, toEl) {
    var k = 'gblab-hand-' + kind;
    try { if (W.localStorage.getItem(k)) return; W.localStorage.setItem(k, '1'); } catch (e) {}
    var h = el('div', 'tl-hand',
      '<svg viewBox="0 0 54 54"><circle cx="20" cy="14" r="11" fill="rgba(83,167,219,.35)"/>' +
      '<path d="M18 30V12a4 4 0 0 1 8 0v12l10 2a5 5 0 0 1 4 6l-2 12a6 6 0 0 1-6 5H24a6 6 0 0 1-5-3l-7-11a4 4 0 0 1 6-5z" fill="#fff" stroke="#0A2463" stroke-width="2.4" stroke-linejoin="round"/></svg>');
    D.body.appendChild(h);
    function at(e) { var r = e.getBoundingClientRect(); return { x: r.left + r.width / 2 - 20, y: r.top + r.height / 2 - 14 }; }
    var a = at(fromEl), b = toEl ? at(toEl) : a, t0 = null, dur = toEl ? 1400 : 900, rounds = 0;
    h.style.left = a.x + 'px'; h.style.top = a.y + 'px';
    setTimeout(function () { h.className += ' on'; W.requestAnimationFrame(step); }, 350);
    function step(ts) {
      if (!t0) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur), e = p < .5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      h.style.left = (a.x + (b.x - a.x) * e) + 'px';
      h.style.top = (a.y + (b.y - a.y) * e + (toEl ? 0 : Math.sin(p * Math.PI) * -8)) + 'px';
      if (p < 1) return W.requestAnimationFrame(step);
      if (++rounds < 2) { t0 = null; return setTimeout(function () { W.requestAnimationFrame(step); }, 300); }
      h.className = 'tl-hand';
      setTimeout(function () { if (h.parentNode) h.parentNode.removeChild(h); }, 400);
    }
    D.addEventListener('pointerdown', function gone() { if (h.parentNode) h.parentNode.removeChild(h); D.removeEventListener('pointerdown', gone); });
  }

  /* ---- sound: made in the page, nothing to load. Needs one tap first (WebView rule) --- */
  var ctx = null;
  function audio() {
    if (!ctx) { var A = W.AudioContext || W.webkitAudioContext; if (A) ctx = new A(); }
    if (ctx && ctx.state === 'suspended') ctx.resume();
    return ctx;
  }
  D.addEventListener('pointerdown', function () { audio(); }, { once: true });
  var sound = {
    // steps: [[hz, ms, gapMs, type], ...]; returns the total length in ms
    play: function (steps, vol) {
      var c = audio();
      if (!c) return 0;
      var t = c.currentTime + 0.05, total = 0;
      steps.forEach(function (s) {
        var o = c.createOscillator(), g = c.createGain();
        o.type = s[3] || 'square';
        o.frequency.value = s[0];
        g.gain.setValueAtTime(0, t);
        g.gain.linearRampToValueAtTime(vol || 0.12, t + 0.01);
        g.gain.setValueAtTime(vol || 0.12, t + s[1] / 1000 - 0.02);
        g.gain.linearRampToValueAtTime(0, t + s[1] / 1000);
        o.connect(g); g.connect(c.destination);
        o.start(t); o.stop(t + s[1] / 1000 + 0.02);
        t += (s[1] + (s[2] || 0)) / 1000;
        total += s[1] + (s[2] || 0);
      });
      return total;
    },
    stop: function () { if (ctx) { ctx.close(); ctx = null; } }
  };

  /* ---- small sounds that make the screen feel alive (quiet; one tap unlocks audio) ---- */
  var SFX = {
    tap: [[880, 18, 0, 'sine']],
    good: [[660, 90, 10, 'sine'], [990, 140, 0, 'sine']],
    bad: [[220, 140, 30, 'triangle'], [180, 220, 0, 'triangle']],
    win: [[523, 110, 10, 'sine'], [659, 110, 10, 'sine'], [784, 110, 10, 'sine'], [1047, 260, 0, 'sine']]
  };
  function sfx(name) { try { sound.play(SFX[name] || SFX.tap, name === 'tap' ? 0.03 : 0.07); } catch (e) {} }
  D.addEventListener('pointerdown', function (e) {
    var t = e.target.closest ? e.target.closest('button, .tl-tap, [data-drag], [data-tap]') : null;
    if (!t) return;
    var r = el('div', 'tl-ripple');
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
    D.body.appendChild(r);
    setTimeout(function () { if (r.parentNode) r.parentNode.removeChild(r); }, 500);
    sfx('tap');
  });

  /* ---- the classroom's messages --------------------------------------------------- */
  var teamSeen = false;
  W.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.type === 'gb-team') { teamSeen = true; handlers.team.forEach(function (f) { f(d.team); }); }
    if (d.type === 'gb-timer') handlers.timer.forEach(function (f) { f(d); });
  });
  function on(name, fn) {
    handlers[name].push(fn);
    // no team within about 2 seconds: the class has no teams - run as an individual task
    if (name === 'team') setTimeout(function () { if (!teamSeen) fn(null); }, 2000);
  }

  /* ---- the scene: a photograph and everything placed on it, fitted whole ------------------
     <div class="tl-scene" data-aspect="16:9"><img class="tl-photo" src="..."> <b class="tl-pin" style="left:32%;top:40%">..</b></div>
     The scene keeps the photograph's own proportions and is fitted INSIDE the stage, so a pin
     at 32 % / 40 % stays on the same valve on a tablet, turned or not, and on a phone. The rest
     of the stage is filled with a blurred copy of the same photograph, never with a white band. */
  function fitScenes() {
    [].forEach.call(D.querySelectorAll('.tl-scene'), function (sc) {
      var st = sc.parentNode, a = String(sc.getAttribute('data-aspect') || '16:9').split(':');
      var ar = (+a[0] || 16) / (+a[1] || 9), W0 = st.clientWidth, H0 = st.clientHeight, w = W0, h = W0 / ar;
      if (h > H0) { h = H0; w = H0 * ar; }
      sc.style.width = w + 'px'; sc.style.height = h + 'px';
      sc.style.left = (W0 - w) / 2 + 'px';
      sc.style.top = (sc.getAttribute('data-align') === 'top' ? 0 : (H0 - h) / 2) + 'px';
      var ph = sc.querySelector('.tl-photo'), b = null;
      [].forEach.call(st.children, function (c) { if (c.classList.contains('tl-blur')) b = c; });
      if (ph && !b) { b = el('div', 'tl-blur'); st.insertBefore(b, st.firstChild); }
      var src = ph && ph.getAttribute('src');
      if (b && src && b.getAttribute('data-src') !== src) { b.style.backgroundImage = 'url("' + src + '")'; b.setAttribute('data-src', src); }
    });
  }
  W.addEventListener('resize', fitScenes);
  if (W.ResizeObserver) {
    var ro = new ResizeObserver(function () { fitScenes(); });
    var watch = function () { [].forEach.call(D.querySelectorAll('.tl-stage'), function (st) { ro.observe(st); }); };
    if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', watch); else watch();
  }
  /* A tap that never becomes a click. Measured 2026-10-15 (tools/task-test/diag2.js): on a busy
     page about 1 tap in 12 reached an enabled button - pointerdown, pointerup, touchend - and the
     browser never sent the click, so the press did nothing. A trainee calls that "broken". So: a
     clean tap (down and up on the same control, the finger moved less than 12 px) that is not
     followed by the browser's own click within 250 ms gets its click delivered here. When the
     browser does send it, nothing more happens - a press can never count twice. */
  var TAPPABLE = 'button, [data-tap], .hm-obj, .tl-btn, .tl-pin, [role="button"]';
  var tapDown = null, nativeClick = null;
  D.addEventListener('pointerdown', function (e) {
    if (e.pointerType === 'mouse' || e.isPrimary === false) { tapDown = null; return; }
    var t = e.target.closest ? e.target.closest(TAPPABLE) : null;
    tapDown = t ? { el: t, x: e.clientX, y: e.clientY, id: e.pointerId } : null;
  }, true);
  var delivered = null;
  D.addEventListener('click', function (e) {
    // the browser's own click arriving late, after this shell already delivered one: swallowed
    if (e.isTrusted && delivered && Date.now() < delivered.until && (delivered.el === e.target || delivered.el.contains(e.target))) {
      e.stopImmediatePropagation(); e.preventDefault(); return;
    }
    nativeClick = { el: e.target, at: Date.now() };
  }, true);
  D.addEventListener('pointerup', function (e) {
    var d = tapDown;
    tapDown = null;
    if (!d || e.pointerId !== d.id) return;
    var dx = e.clientX - d.x, dy = e.clientY - d.y;
    if (dx * dx + dy * dy > 144) return;
    var under = D.elementFromPoint(e.clientX, e.clientY), el = d.el;
    if (!under || !(el === under || el.contains(under))) return;
    var upAt = Date.now();
    setTimeout(function () {
      if (nativeClick && nativeClick.at >= upAt - 50 && (el === nativeClick.el || el.contains(nativeClick.el))) return;
      if (!el.isConnected || el.disabled) return;
      delivered = { el: el, until: Date.now() + 800 };
      el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: W, clientX: e.clientX, clientY: e.clientY }));
    }, 250);
  }, true);
  D.addEventListener('pointercancel', function () { tapDown = null; }, true);

  // a long press never opens the browser's own menu, and a picture is never dragged out as a file
  D.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  D.addEventListener('dragstart', function (e) { e.preventDefault(); });
  W.addEventListener('orientationchange', function () { setTimeout(fitScenes, 200); });

  /* ---- wiring --------------------------------------------------------------------- */
  function init(o) {
    for (var k in o) cfg[k] = o[k];
    var b = $('.tl-go');
    // one press = one action: a double tap, or a press while a sheet is open, does nothing
    if (b) b.addEventListener('click', function () {
      var now = Date.now();
      if (!goFn || b.disabled || openSheet || now - goLast < 450) return;
      goLast = now; goFn();
    });
    if (cfg.title) D.title = (cfg.code ? cfg.code + ' — ' : '') + cfg.title;
    fitScenes();
    W.addEventListener('load', fitScenes);
  }

  /* ---- clear at every moment: how it works, what to do now, a hint, the next move ---- */
  function intro(o) { // the opening card: what this is, the steps in order, one button to begin
    var ol = el('ol', 'tl-how', (o.steps || []).map(function (s, i) { return '<li><b>' + (i + 1) + '</b><span>' + s + '</span></li>'; }).join(''));
    var h = show({ tag: o.tag || 'How it works', title: o.title, text: o.text, node: ol, buttons: [{ label: o.start || 'Start', fn: o.onStart }] });
    h.sheet.className += ' tl-intro';
    return h;
  }
  var nowEl = null;
  function now(html, state) { // the one thing to do now, over the stage; state: '' | 'done' | 'warn'
    var st = $('.tl-stage'); if (!st) return;
    if (nowEl && nowEl.getAttribute('data-k') === (state || '') + '|' + html) return; // unchanged: no flicker
    // a phone: its own strip above the picture, so it never covers a small photo; else over the stage
    var strip = W.matchMedia && W.matchMedia('(max-width: 600px)').matches;
    if (!nowEl) { nowEl = el('div', 'tl-now'); nowEl.setAttribute('aria-live', 'polite'); }
    if (strip && nowEl.nextSibling !== st) st.parentNode.insertBefore(nowEl, st);
    if (!strip && nowEl.parentNode !== st) st.appendChild(nowEl);
    nowEl.setAttribute('data-k', (state || '') + '|' + html);
    nowEl.className = 'tl-now' + (strip ? ' strip' : '') + (state ? ' ' + state : '');
    nowEl.innerHTML = html ? '<i></i><span>' + html + '</span>' : '';
    nowEl.style.display = html ? '' : 'none';
  }
  var hintsUsed = 0;
  function hint(fn) { // a hint button on the stage; fn returns the hint for this moment (or nothing)
    var st = $('.tl-stage'); if (!st) return;
    var b = el('button', 'tl-hintb', '<b>?</b><span>Hint</span>'); b.type = 'button'; b.setAttribute('aria-label', 'Hint');
    b.addEventListener('click', function () { if (openSheet) return; var t = fn(); if (t) { hintsUsed++; toast('Hint: ' + t, 'hint'); } });
    st.appendChild(b);
  }
  function goReady(on) { var b = $('.tl-go'); if (b) b.classList.toggle('tl-ready', !!on); } // the next move is the big button

  W.GBLab = {
    init: init, key: key, go: go, goEnabled: goEnabled, toast: toast, show: show,
    sure: sure, sureNote: sureNote, finish: finish, drag: drag, hand: hand, sound: sound, sfx: sfx, on: on,
    esc: esc, el: el, fitScenes: fitScenes, toScene: toScene, nearest: nearest,
    intro: intro, now: now, hint: hint, goReady: goReady, hints: function () { return hintsUsed; },
    sheetOpen: function () { return !!openSheet; }
  };
})(window, document);
