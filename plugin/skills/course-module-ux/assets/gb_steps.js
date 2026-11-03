/* gb_steps.js - Next walks an upgraded slide's stops. Plain ES5, loaded before gb_deck.js (its hooks go into GB_HOOKS).
   A stop is every [data-stop] element in order, or the elements sharing a data-k number ("0 2" = shown at both). The stop
   now gets .cur, the ones before .lit; the slide carries data-at (the stop now) and data-last (on its last stop).
   data-stops on the slide sets how many stops there are when the marks do not say it. What a stop does to the picture
   comes from the slide's own parts: a live scene ([data-lt-scene], gb_scene.js), photo spots, a photo zoom, a question
   that opens, parts with tabs, a line that fills, a meter, a before / after slider, a drill's clock. */
(function (w, d) {
  'use strict';
  var H = w.GB_HOOKS = w.GB_HOOKS || {};
  var CALM = !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches);
  function each(l, f) { for (var i = 0; i < l.length; i++) { f(l[i], i); } }
  function q(s, r) { return (r || d).querySelector(s); }
  function qa(s, r) { return (r || d).querySelectorAll(s); }

  /* a point on a photograph (its own pixels; data-px-w: the width they were given in, before the photo was enlarged) to a
     point in its box, as object-fit: cover draws it */
  function cover(img, px, py) {
    var box = img.parentNode, iw = img.naturalWidth || 1600, ih = img.naturalHeight || 1000, W = box.clientWidth, Hh = box.clientHeight, sc = Math.max(W / iw, Hh / ih);
    var k = iw / (+img.getAttribute('data-px-w') || iw); px *= k; py *= k;
    return { x: (W - iw * sc) / 2 + px * sc, y: (Hh - ih * sc) / 2 + py * sc, ox: (W - iw * sc) / 2, oy: (Hh - ih * sc) / 2, dw: iw * sc, dh: ih * sc, W: W, H: Hh };
  }

  /* what each kind of part does at a stop */
  var PARTS = [
    /* photo spots: placed on the photograph's own pixels */
    function (s) {
      var img = q('.photo-wrap img, .lt-pic > img', s), spots = qa('.lt-spot', s);
      if (!img || !spots.length) { return null; }
      var place = function () { each(spots, function (sp) { var c = cover(img, +sp.getAttribute('data-x'), +sp.getAttribute('data-y')); sp.style.left = c.x + 'px'; sp.style.top = c.y + 'px'; }); };
      if (img.complete) { place(); } else { img.addEventListener('load', place); }
      w.addEventListener('resize', place);
      return null;
    },
    /* the photograph zooms to the part the line names, and a ring marks it */
    function (s) {
      if (!s.classList.contains('lt-zoom')) { return null; }
      var img = q('.photo-wrap img', s), ring = q('.lt-ring', s);
      var at = function (k) {
        var st = q('[data-k="' + k + '"]', s), z = +(st && st.getAttribute('data-z')) || 1;
        var c = cover(img, +(st && st.getAttribute('data-x')) || 800, +(st && st.getAttribute('data-y')) || 500);
        var tx = c.W / 2 - z * c.x, ty = c.H / 2 - z * c.y;
        tx = Math.min(-z * c.ox, Math.max(c.W - z * (c.ox + c.dw), tx)); ty = Math.min(-z * c.oy, Math.max(c.H - z * (c.oy + c.dh), ty));
        img.style.transform = 'translate(' + tx.toFixed(1) + 'px,' + ty.toFixed(1) + 'px) scale(' + z + ')';
        if (ring) { ring.style.left = (z * c.x + tx) + 'px'; ring.style.top = (z * c.y + ty) + 'px'; ring.classList.toggle('on', z > 1); }
      };
      w.addEventListener('resize', function () { if (s.classList.contains('active')) { at(+s.getAttribute('data-at') || 0); } });
      return at;
    },
    /* a question first; the answer opens beside it */
    function (s) { var qa2 = q('.lt-qa', s); return qa2 ? function (k) { qa2.classList.toggle('open', k >= 1); } : null; },
    /* the reading slide: a spot moves to the part the line names, and a part is a way to its line */
    function (s) {
      var link = q('.lt-link', s) || q('.lt-cmp', s), spot = link && q('.spot', link);
      if (!spot) { return null; }
      each(qa('.hs', link), function (h, j) { h.addEventListener('click', function () { var st = qa('[data-k="' + j + '"]', s)[0]; if (st) { st.click(); } }); });
      return function (k) {
        var h = qa('.hs', link)[k]; if (!h) { return; }
        spot.setAttribute('transform', 'translate(' + h.getAttribute('data-x') + ' ' + h.getAttribute('data-y') + ')');
        spot.style.transform = 'translate(' + h.getAttribute('data-x') + 'px,' + h.getAttribute('data-y') + 'px)'; spot.classList.add('on');
      };
    },
    /* words in parts: the part holding the line now is the one shown, its tab lit */
    function (s) {
      var pts = qa('.lt-pt', s); if (!pts.length) { return null; }
      each(qa('.lt-ptabs button', s), function (b) { b.addEventListener('click', function () { var x = q('[data-k="' + b.getAttribute('data-go') + '"]', s); if (x) { x.click(); } }); });
      return function (k) {
        var cur = q('[data-k="' + k + '"]', s), part = cur && cur.closest('.lt-pt');
        each(pts, function (p) { p.classList.toggle('on', p === part); });
        each(qa('.lt-ptabs button', s), function (b) { b.classList.toggle('on', !!part && b.getAttribute('data-part') === part.getAttribute('data-part')); });
      };
    },
    /* steps as boxes: the line under them fills */
    function (s) { var t = q('.lt-track i', s); return t ? function (k, n) { t.style.width = (n > 1 ? k / (n - 1) * 100 : 100) + '%'; } : null; },
    /* numbers on a live scene: the one now lights */
    function (s) { var tags = qa('.lt-tag.num', s); return tags.length ? function (k) { each(tags, function (t) { t.classList.toggle('hot', +t.getAttribute('data-n') === k); }); } : null; },
    /* a meter that counts to each stop's reading: data-meter = [[value, shown or null, status, kind], ...] on .lt-meter, full scale data-max */
    function (s) {
      var m = q('.lt-meter[data-meter]', s); if (!m) { return null; }
      var V = JSON.parse(m.getAttribute('data-meter')), max = +m.getAttribute('data-max') || 5, vol = q('[data-v="vol"]', m), sh = q('[data-v="lel"]', m), st = q('[data-v="st"]', m), sc = q('.scale', m);
      var shown = 0, raf = 0;
      return function (k) {
        var v = V[Math.min(k, V.length - 1)], from = shown, t0 = 0;
        sc.style.setProperty('--f', (v[0] / max * 100) + '%'); st.textContent = v[2]; st.className = 'st ' + (v[3] || '');
        var draw = function (x) { vol.textContent = x.toFixed(1); sh.textContent = v[1] === null ? '?' : Math.round(x / max * 100); };
        if (raf) { w.cancelAnimationFrame(raf); }
        if (CALM) { shown = v[0]; draw(shown); return; }
        raf = w.requestAnimationFrame(function tick(now) {
          t0 = t0 || now; var e = Math.min(1, (now - t0) / 700); e = 1 - Math.pow(1 - e, 3);
          shown = from + (v[0] - from) * e; draw(shown); if (e < 1) { raf = w.requestAnimationFrame(tick); }
        });
      };
    },
    /* before / after: Next moves the line (data-x, one place a stop), a finger drags it */
    function (s) {
      var ba = q('.lt-ba', s); if (!ba) { return null; }
      var X = (ba.getAttribute('data-x') || '50').split(' ');
      var drag = function (e) { var r = ba.getBoundingClientRect(); ba.style.setProperty('--x', Math.max(0, Math.min(100, (e.clientX - r.left) / r.width * 100)) + '%'); };
      ba.addEventListener('pointerdown', function (e) { ba.classList.add('drag'); ba.setPointerCapture(e.pointerId); drag(e); });
      ba.addEventListener('pointermove', function (e) { if (ba.classList.contains('drag')) { drag(e); } });
      ba.addEventListener('pointerup', function () { ba.classList.remove('drag'); });
      return function (k) { ba.style.setProperty('--x', (X[Math.min(k, X.length - 1)] || 50) + '%'); };
    }
  ];

  /* a choice the room taps before the answer: one picked at a time */
  function pickers(s) {
    each(['.lt-vote button', '.lt-opt'], function (sel) {
      var l = qa(sel, s);
      each(l, function (b) { b.addEventListener('click', function () { each(l, function (x) { x.classList.toggle('picked', x === b); }); }); });
    });
  }

  /* a drill's clock: data-run on .lt-timer names the stops it runs at; at zero it shakes and the next stop (the answer)
     shows by itself */
  function clock(s) {
    var box = q('.lt-timer', s); if (!box) { return null; }
    var secs = +box.getAttribute('data-secs'), b = q('b', box), run = (box.getAttribute('data-run') || '1').split(' '), id = 0;
    var stop = function () { if (id) { w.clearInterval(id); w.clearTimeout(id); id = 0; } };
    var show = function (left) { b.textContent = Math.ceil(left); box.style.setProperty('--left', left / secs); box.classList.toggle('low', left > 0 && left <= 10); };
    return {
      stop: stop,
      at: function (k, go) {
        stop(); box.classList.remove('low', 'done'); s.removeAttribute('data-running');
        var runs = run.indexOf(String(k)) >= 0, after = run.indexOf(String(k - 1)) >= 0;
        if (after) { s.setAttribute('data-reveal', ''); } else { s.removeAttribute('data-reveal'); }
        if (!runs) { show(secs); return; }
        s.setAttribute('data-running', '');
        if (CALM) { show(secs * 0.4); return; }
        var end = Date.now() + secs * 1000;
        id = w.setInterval(function () {
          var left = Math.max(0, (end - Date.now()) / 1000); show(left);
          if (left <= 0) { w.clearInterval(id); box.classList.add('done'); id = w.setTimeout(function () { id = 0; go(k + 1); }, 700); }
        }, 200);
        show(secs);
      }
    };
  }

  function walker(s) {
    each(qa('[data-stop]', s), function (x, j) { if (!x.hasAttribute('data-k')) { x.setAttribute('data-k', j); } });
    each(qa('[data-k]', s), function (x) { var ks = x.getAttribute('data-k').split(' '); if (ks.length > 1) { x.setAttribute('data-ks', ' ' + ks.join(' ') + ' '); x.setAttribute('data-k', ks[0]); } });
    var marks = qa('[data-k]', s), n = +s.getAttribute('data-stops') || 0, i = 0, box = q('[data-lt-scene]', s), fns = [], clk = clock(s);
    if (!n) { each(marks, function (x) { n = Math.max(n, +x.getAttribute('data-k') + 1); }); }
    each(PARTS, function (f) { var g = f(s); if (g) { fns.push(g); } });
    pickers(s);
    function go(k) {
      if (k < 0 || k >= n) { return; }
      i = k;
      each(marks, function (x) {
        var many = x.getAttribute('data-ks'), j = +x.getAttribute('data-k');
        if (many) { x.classList.toggle('cur', many.indexOf(' ' + k + ' ') >= 0); x.classList.remove('lit'); return; }
        x.classList.toggle('cur', j === k); x.classList.toggle('lit', j < k);
      });
      s.setAttribute('data-at', k);
      if (k === n - 1) { s.setAttribute('data-last', ''); } else { s.removeAttribute('data-last'); }
      if (box && box.__lt) { box.__lt.go(k); }
      each(fns, function (f) { f(k, n); });
      if (clk) { clk.at(k, go); }
    }
    each(marks, function (x) { x.addEventListener('click', function () { go(+x.getAttribute('data-k')); }); });
    var old = H[s.id] || {};
    H[s.id] = {
      enter: function () { go(0); if (old.enter) { old.enter(); } },
      leave: function () { if (clk) { clk.stop(); } if (old.leave) { old.leave(); } },
      step: function (dir) { var k = i + dir; if (k < 0 || k >= n) { return false; } go(k); return true; }
    };
    go(0);
  }

  each(qa('.slide'), function (s) {
    if (!s.id || !(q('[data-k]', s) || q('[data-stop]', s) || s.hasAttribute('data-stops'))) { return; }
    walker(s);
  });
})(window, document);
