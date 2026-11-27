/* n2d.js - the 2D kit for new courses (SPEC.md). A figure is written as words and data only - things, links, steps -
   and lays itself out in the box it is shown in: no coordinates, no sizes, no states to tune. Each form holds a fixed
   amount; a spec that asks for more is refused by the check (scripts/n2d_check.py, check() here), never shrunk to fit.
   In a deck the slide's Next and Back walk the steps, each step lighting the slide's line it names. */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var C = { navy: '#0A2463', ink: '#14213D', sub: '#4A5B74', line: '#8E9DB4', ghost: '#E3E8EF', amber: '#E9A51E', amberInk: '#5C3D00',
    good: '#12805A', warn: '#C8402F', white: '#FFFFFF', sea: '#DCEFFA', seaLine: '#B9DDF2', oil: '#6E4420', oilHi: '#E0B27A', brick: '#C2493A' };
  var TONES = { blue: '#1F78C8', teal: '#0F8B7E', violet: '#6A4FC4', rose: '#C2386A', slate: '#47608F', orange: '#D46A12', green: '#2E8B3E', red: '#C8402F', navy: '#0A2463' };
  var ORDER = ['blue', 'teal', 'violet', 'orange', 'rose', 'slate'];
  var REDUCED = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  var FONT = 'Raleway, "Segoe UI", Arial, sans-serif';
  var LIMIT = { name: 3, chars: 24, tag: 4, act: 4, read: 14, words: 2 };
  var pale = function (h, k) { return window.N2THINGS.pale(h, k); };

  function tone(t, i) { return TONES[t] || (t && t[0] === '#' ? t : TONES[ORDER[(i || 0) % ORDER.length]]); }
  function E(tag, a, p) { var e = document.createElementNS(NS, tag); if (a) for (var k in a) if (a[k] != null) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  var cv = document.createElement('canvas').getContext('2d');
  function tw(s, size, wt) { cv.font = (wt || 700) + ' ' + size + 'px ' + FONT; return cv.measureText(String(s)).width; }
  function wrap(s, size, maxW, wt) {
    var ws = String(s).split(/\s+/), out = [], cur = '';
    ws.forEach(function (w) { var t = cur ? cur + ' ' + w : w; if (cur && tw(t, size, wt) > maxW) { out.push(cur); cur = w; } else cur = t; });
    if (cur) out.push(cur);
    return out;
  }
  function fit(s, size, minSize, maxW, maxLines, wt) {
    for (var z = size; z >= minSize; z -= 0.5) {
      var L = wrap(s, z, maxW, wt);
      if (L.length <= maxLines && L.every(function (l) { return tw(l, z, wt) <= maxW; })) return { lines: L, size: z };
    }
    return { lines: wrap(s, minSize, maxW, wt), size: minSize, over: true };
  }
  function text(p, x, y, s, size, o) {
    o = o || {};
    var lines = Array.isArray(s) ? s : [s];
    var t = E('text', { x: x, y: y, 'font-size': size.toFixed(1), 'font-weight': o.wt || 700, fill: o.fill || C.ink, 'text-anchor': o.anchor || 'middle' }, p);
    if (o.halo !== false) { t.setAttribute('paint-order', 'stroke'); t.setAttribute('stroke', o.halo || C.white); t.setAttribute('stroke-width', Math.max(3, size * 0.24).toFixed(1)); t.setAttribute('stroke-linejoin', 'round'); }
    if (o.cls) t.setAttribute('class', o.cls);
    lines.forEach(function (l, i) { var ts = E('tspan', { x: x, dy: i ? (size * 1.13).toFixed(1) : 0 }, t); ts.textContent = l; });
    return t;
  }
  function setText(t, s) { var ts = t.querySelector('tspan'); if (ts) ts.textContent = s; else t.textContent = s; }
  function pill(p, x, y, s, size, bg, fg, cls) {
    var w = tw(s, size, 800) + size * 1.2, h = size * 1.6;
    var pos = E('g', { transform: 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')' }, p);
    var g = E('g', { 'class': cls || '', 'data-may-overlap': '' }, pos);     /* a pill's words sit on the pill by design */
    E('rect', { x: -w / 2, y: -h / 2, width: w, height: h, rx: h / 2, fill: bg, 'data-no-contain': '' }, g);
    g.t = text(g, 0, size * 0.36, s, size, { fill: fg, wt: 800, halo: false });
    g.w = w; g.h = h; return g;
  }
  function picture(p, is, t, size) {      /* a thing's picture: its own digits and marks are part of the picture */
    var g = E('g', { 'class': 'n2-pic', 'aria-hidden': 'true', 'data-may-overlap': '', 'data-no-contain': '', 'data-may-cross': '',
      transform: 'translate(' + (-size / 2).toFixed(1) + ' ' + (-size / 2).toFixed(1) + ') scale(' + (size / 100).toFixed(4) + ')' }, p);
    g.innerHTML = window.N2THINGS.draw(is, t);
    return g;
  }
  /* the drawing check's blank count (audit_drawing.js): an n2d figure lays itself out across its box, so the area it
     shares out is content */
  function fills(p, x, y, w, h) { return E('rect', { x: x, y: y, width: w, height: h, fill: 'none', 'data-kit-fills': '', 'data-no-contain': '', 'aria-hidden': 'true' }, p); }
  var running = 0, settleAt = 0;
  function tween(ms, fn, done) {
    if (REDUCED || ms <= 0) { fn(1); if (done) done(); return { stop: function () {} }; }
    var t0 = performance.now(), live = true;
    running++;
    function end() { if (live) { live = false; running--; } }
    function f(now) { if (!live) return; var k = clamp((now - t0) / ms, 0, 1); fn(k); if (k < 1) requestAnimationFrame(f); else { end(); if (done) done(); } }
    requestAnimationFrame(f);
    return { stop: end };
  }
  function ease(k) { return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; }
  function nwords(s) { return String(s || '').trim().split(/\s+/).filter(Boolean).length; }
  function typeSize(W, H) { return clamp(Math.min(W * 0.036, H * 0.054), 19, 32); }
  function along(pts, d) {
    for (var i = 1; i < pts.length; i++) {
      var s = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      if (d <= s || i === pts.length - 1) { var k = s ? clamp(d / s, 0, 1) : 0; return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * k, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * k]; }
      d -= s;
    }
    return pts[pts.length - 1];
  }
  function plen(pts) { var L = 0; for (var i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); return L; }
  function dPath(pts, r) {
    var f = function (q) { return q[0].toFixed(1) + ' ' + q[1].toFixed(1); };
    if (pts.length < 3 || !r) return 'M' + pts.map(f).join(' L');
    var d = 'M' + f(pts[0]);
    for (var i = 1; i < pts.length - 1; i++) {
      var a = pts[i - 1], b = pts[i], c = pts[i + 1];
      var l1 = Math.hypot(b[0] - a[0], b[1] - a[1]), l2 = Math.hypot(c[0] - b[0], c[1] - b[1]), rr = Math.min(r, l1 / 2, l2 / 2);
      d += ' L' + f([b[0] + (a[0] - b[0]) * rr / l1, b[1] + (a[1] - b[1]) * rr / l1]) + ' Q' + f(b) + ' ' + f([b[0] + (c[0] - b[0]) * rr / l2, b[1] + (c[1] - b[1]) * rr / l2]);
    }
    return d + ' L' + f(pts[pts.length - 1]);
  }
  function instant(el, fn) { el.style.transition = 'none'; fn(); el.getBoundingClientRect(); el.style.transition = ''; }
  function scaleShow(g, on) { g.style.transform = on ? 'scale(1)' : 'scale(0)'; g.style.opacity = on ? 1 : 0; }

  function checkName(P, where, s, max) {
    max = max || LIMIT.name;
    if (!s) return;
    if (nwords(s) > max) P.push(where + ': "' + s + '" is ' + nwords(s) + ' words; at most ' + max + ' - the picture says the rest');
    else if (String(s).length > LIMIT.chars + (max - LIMIT.name) * 6) P.push(where + ': "' + s + '" is too long for the back of the room');
  }
  function checkThing(P, where, is) { if (!window.N2THINGS.has(is)) P.push(where + ': no picture for "' + is + '" - pick a thing from the library, or add this one to it'); }

  function badge(p, x, y, r, kind) {
    /* a badge sits on its thing's corner by design */
    var pos = E('g', { transform: 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ')', 'data-may-overlap': '', 'data-may-cross': '', 'data-no-contain': '' }, p), b = E('g', { 'class': 'tz' }, pos);
    var col = { alarm: C.amber, fail: C.warn, ok: C.good, bug: C.white }[kind];
    E('circle', { r: r, fill: col, stroke: kind === 'bug' ? C.warn : C.white, 'stroke-width': (r * 0.2).toFixed(1) }, b);
    if (kind === 'bug') picture(b, 'malware', C.warn, r * 1.45);
    else if (kind === 'ok') E('path', { d: 'M' + (-r * 0.45) + ' 0 l' + (r * 0.3) + ' ' + (r * 0.32) + ' l' + (r * 0.6) + ' ' + (-r * 0.62), fill: 'none', stroke: C.white, 'stroke-width': r * 0.28, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, b);
    else if (kind === 'fail') E('path', { d: 'M' + (-r * 0.38) + ' ' + (-r * 0.38) + ' L' + (r * 0.38) + ' ' + (r * 0.38) + ' M' + (r * 0.38) + ' ' + (-r * 0.38) + ' L' + (-r * 0.38) + ' ' + (r * 0.38), stroke: C.white, 'stroke-width': r * 0.28, 'stroke-linecap': 'round' }, b);
    else { E('rect', { x: -r * 0.13, y: -r * 0.62, width: r * 0.26, height: r * 0.72, rx: r * 0.12, fill: C.navy }, b); E('circle', { cy: r * 0.42, r: r * 0.15, fill: C.navy }, b); }
    scaleShow(b, false);
    return b;
  }

  /* ---------- path: things in order, something travels between them ---------- */
  function parseLinks(arr) {
    var out = [];
    (arr || []).forEach(function (str) {
      var lab = null, m = String(str).split(':');
      if (m.length > 1) { lab = m.slice(1).join(':').trim(); str = m[0]; }
      var ids = str.split('>').map(function (x) { return x.trim(); });
      for (var i = 1; i < ids.length; i++) out.push({ a: ids[i - 1], b: ids[i], label: i === ids.length - 1 ? lab : null, key: ids[i - 1] + '>' + ids[i] });
    });
    return out;
  }
  function chainKeys(str) { var ids = String(str).split('>').map(function (x) { return x.trim(); }), k = []; for (var i = 1; i < ids.length; i++) k.push(ids[i - 1] + '>' + ids[i]); return k; }
  function chainIds(str) { return String(str).split('>').map(function (x) { return x.trim(); }); }

  var PATH = {
    check: function (s) {
      var P = [], ids = {};
      var th = s.things || [];
      if (th.length < 2) P.push('a path needs at least two things');
      if (th.length > 7) P.push(th.length + ' things; a path holds at most 7 - show the part this slide teaches');
      th.forEach(function (t) { ids[t.id] = 1; checkName(P, 'thing ' + t.id, t.name); if (t.is !== 'decision') checkThing(P, 'thing ' + t.id, t.is); });
      var L = parseLinks(s.links), rank = {}, ins = {}, outs = {};
      L.forEach(function (l) { if (!ids[l.a] || !ids[l.b]) P.push('link ' + l.key + ' names a thing that is not drawn'); });
      th.forEach(function (t) { rank[t.id] = 0; ins[t.id] = 0; outs[t.id] = 0; });
      L.forEach(function (l) { outs[l.a] = (outs[l.a] || 0) + 1; ins[l.b] = (ins[l.b] || 0) + 1; });
      th.forEach(function () { L.forEach(function (l) { if (l.a in rank && l.b in rank && rank[l.b] < rank[l.a] + 1) rank[l.b] = rank[l.a] + 1; }); });
      var cols = 1 + Math.max.apply(null, [0].concat(Object.keys(rank).map(function (k) { return rank[k]; })));
      var chain = cols === th.length && th.every(function (t) { return ins[t.id] <= 1 && outs[t.id] <= 1; });
      if (cols > 5 && !chain) P.push(cols + ' things in a row with branches; a path with branches is at most 5 long - show the part this slide teaches');
      (s.steps || []).forEach(function (x, i) {
        if (x.tag) Object.keys(x.tag).forEach(function (k) { checkName(P, 'step ' + (i + 1) + ' tag', x.tag[k], LIMIT.tag); });
        ['go', 'bug'].forEach(function (k) { if (x[k]) [].concat(x[k]).forEach(function (c) { chainIds(c).forEach(function (id) { if (!ids[id]) P.push('step ' + (i + 1) + ' ' + k + ' names "' + id + '", not drawn'); }); }); });
      });
      if ((s.steps || []).length > 7) P.push('more than 7 steps');
      return P;
    },
    state: function (s, n) {
      var st = { lit: {}, fail: {}, cut: {}, wrong: {}, shown: {}, mark: {}, tag: {}, inf: {}, go: null, bug: null };
      (s.things || []).forEach(function (t) { if (!t.hidden) st.shown[t.id] = 1; });
      for (var i = 0; i <= n && i < s.steps.length; i++) {
        var x = s.steps[i];
        if (x.clear) { st.lit = {}; st.fail = {}; st.cut = {}; st.inf = {}; st.wrong = {}; }
        if (x.wrong) [].concat(x.wrong).forEach(function (k) { st.wrong[k] = 1; });
        if (x.add) [].concat(x.add).forEach(function (id) { st.shown[id] = 1; });
        if (x.go) [].concat(x.go).forEach(function (c) { chainKeys(c).forEach(function (k) { st.lit[k] = 1; }); });
        if (x.fail) [].concat(x.fail).forEach(function (id) { st.fail[id] = 1; });
        if (x.cut) [].concat(x.cut).forEach(function (k) { st.cut[k] = 1; });
        if (x.bug) chainIds(x.bug).forEach(function (id) { st.inf[id] = 1; });
        if (i === n) {
          st.go = x.go ? [].concat(x.go) : null; st.bug = x.bug || null; st.tag = x.tag || {};
          if (x.mark) [].concat(x.mark).forEach(function (id) { st.mark[id] = 1; });
        }
      }
      return st;
    },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg;
      var th = s.things, L = parseLinks(s.links), ids = th.map(function (t) { return t.id; });
      var rank = {}, succ = {}, pred = {}, byId = {};
      th.forEach(function (t, i) { rank[t.id] = 0; succ[t.id] = []; pred[t.id] = []; byId[t.id] = t; t._i = i; });
      L.forEach(function (l) { succ[l.a].push(l.b); pred[l.b].push(l.a); });
      for (var it = 0; it < ids.length; it++) L.forEach(function (l) { if (rank[l.b] < rank[l.a] + 1) rank[l.b] = rank[l.a] + 1; });
      var nC = 0; ids.forEach(function (id) { nC = Math.max(nC, rank[id] + 1); });
      var cols = []; for (var c = 0; c < nC; c++) cols.push([]);
      ids.forEach(function (id) { cols[rank[id]].push(id); });
      for (var pass = 0; pass < 2; pass++) for (c = 1; c < nC; c++) {
        var prevIdx = {}; cols[c - 1].forEach(function (id, j) { prevIdx[id] = j; });
        cols[c].sort(function (a, b) {
          var fa = pred[a].filter(function (q) { return q in prevIdx; }), fb = pred[b].filter(function (q) { return q in prevIdx; });
          var ma = fa.length ? fa.reduce(function (s2, q) { return s2 + prevIdx[q]; }, 0) / fa.length : byId[a]._i;
          var mb = fb.length ? fb.reduce(function (s2, q) { return s2 + prevIdx[q]; }, 0) / fb.length : byId[b]._i;
          return ma - mb || byId[a]._i - byId[b]._i;
        });
      }
      var nR = 0; cols.forEach(function (cc) { nR = Math.max(nR, cc.length); });
      // a link that skips columns would run through the lone thing between: that thing steps down a row
      var down = {};
      L.forEach(function (l) {
        if (rank[l.b] - rank[l.a] < 2 || cols[rank[l.a]].length > 1 || cols[rank[l.b]].length > 1) return;
        for (var cc = rank[l.a] + 1; cc < rank[l.b]; cc++) if (cols[cc].length === 1) down[cols[cc][0]] = 1;
      });
      var hasDown = Object.keys(down).length > 0;
      if (hasDown) nR = Math.max(nR, 2);
      var pad = base * 0.9, lab = base * 2.5, tagRoom = base * 1.6;
      function sizeFor(nc, nr) { var cw = (W - 2 * pad) / nc, ch = (H - 2 * pad - tagRoom) / nr; return { cw: cw, ch: ch, g: Math.min(cw * 0.64, ch - lab - base * 0.4, H * 0.36, 190) }; }
      var one = sizeFor(nC, nR), use = one, snake = false, k = nC;
      if (nR === 1 && nC >= 5) { k = Math.ceil(nC / 2); var two = sizeFor(k, 2); if (two.g > one.g * 1.2) { use = two; snake = true; } }
      var g = Math.max(use.g, base * 2), pos = {};
      cols.forEach(function (cc, ci) {
        cc.forEach(function (id, j) {
          var row = 0, col = ci, n = cc.length, ch = use.ch, top;
          if (snake) { row = ci < k ? 0 : 1; col = ci < k ? ci : ci - k; top = pad + tagRoom + row * ch; }
          else if (hasDown && n === 1 && nR === 2 && !snake) top = pad + tagRoom + (down[id] ? ch : 0) + (down[id] ? 0 : ch * 0.18);
          else top = pad + tagRoom + ((H - 2 * pad - tagRoom) - n * ch) / 2 + j * ch;
          pos[id] = { x: pad + use.cw * (col + 0.5), y: top + (ch - (g + lab)) / 2 + g / 2, row: row };
        });
      });
      var ew = Math.max(5, g * 0.06), r = g * 0.6, carry = tone(s.tone || 'blue');
      var gl = E('g', null, svg), gt = E('g', null, svg), gtok = E('g', null, svg), gtag = E('g', null, svg);
      if (snake) [0, 1].forEach(function (row) { fills(gl, pad, pad + tagRoom + row * use.ch, W - 2 * pad, use.ch); });
      else cols.forEach(function (cc, ci) { fills(gl, pad + use.cw * ci, pad, use.cw, H - 2 * pad); });
      var LV = {}, srcIdx = {};
      cols.forEach(function (cc) { cc.forEach(function (id, j) { srcIdx[id] = { k: j, n: cc.length }; }); });
      L.forEach(function (l) {
        var a = pos[l.a], b = pos[l.b], pts;
        if (snake && a.row === 0 && b.row === 1) {
          var yA = a.y + g / 2 + lab * 0.92, yM = (yA + b.y - r) / 2;
          pts = [[a.x, yA], [a.x, yM], [b.x, yM], [b.x, b.y - r - ew * 2.6]];
        } else if (Math.abs(b.y - a.y) > g * 0.3 && b.x - a.x > g) {
          // the turn runs down the gap between two columns, clear of every name: names stay within their column
          var si = srcIdx[l.a], x0 = a.x + r, x1 = b.x - r - ew * 2.6;
          var xm = b.x - use.cw * 0.5 + (si.k - (si.n - 1) / 2) * Math.min(use.cw * 0.05, base * 0.5);
          pts = [[x0, a.y], [xm, a.y], [xm, b.y], [x1, b.y]];
        } else {
          var dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy), ux = dx / d, uy = dy / d;
          pts = [[a.x + ux * r, a.y + uy * r], [b.x - ux * (r + ew * 2.6), b.y - uy * (r + ew * 2.6)]];
        }
        var dd = dPath(pts, base), len = plen(pts);
        var v = { pts: pts, len: len };
        v.g = E('g', { 'class': 'tc' }, gl);
        v.base = E('path', { d: dd, fill: 'none', stroke: C.line, 'stroke-width': ew, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'class': 'tc' }, v.g);
        v.lit = E('path', { d: dd, fill: 'none', stroke: carry, 'stroke-width': ew * 1.3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-dasharray': len.toFixed(1) + ' ' + (len + 10).toFixed(1), 'stroke-dashoffset': len.toFixed(1), 'class': 'td' }, v.g);
        var z = pts[pts.length - 1], y0 = pts[pts.length - 2], ang = Math.atan2(z[1] - y0[1], z[0] - y0[0]), ah = ew * 3;
        var tip = [z[0] + Math.cos(ang) * ah * 0.95, z[1] + Math.sin(ang) * ah * 0.95];
        v.head = E('path', { d: 'M' + tip[0].toFixed(1) + ' ' + tip[1].toFixed(1) + ' L' + (z[0] + Math.cos(ang + 2.3) * ah * 0.75).toFixed(1) + ' ' + (z[1] + Math.sin(ang + 2.3) * ah * 0.75).toFixed(1) + ' L' + (z[0] + Math.cos(ang - 2.3) * ah * 0.75).toFixed(1) + ' ' + (z[1] + Math.sin(ang - 2.3) * ah * 0.75).toFixed(1) + ' Z', fill: C.line, 'class': 'tc' }, v.g);
        var mid = along(pts, len / 2);
        v.cut = badge(gtag, mid[0], mid[1], Math.max(base * 0.62, ew * 2.4), 'fail');
        if (l.label) pill(v.g, mid[0], mid[1] - base * 0.1, l.label, base * 0.72, C.white, C.navy).querySelector('rect').setAttribute('stroke', C.line);
        LV[l.key] = v;
      });
      var TV = {};
      th.forEach(function (t, i) {
        var p = pos[t.id], tn = tone(t.tone, i);
        var outer = E('g', { transform: 'translate(' + p.x.toFixed(1) + ' ' + p.y.toFixed(1) + ')' }, gt);
        var v = { inner: E('g', { 'class': 'tz' }, outer), tone: tn };
        v.ring = E('circle', { r: r + ew * 0.9, fill: 'none', stroke: C.amber, 'stroke-width': 0, 'class': 'tc' }, v.inner);
        v.disc = E('circle', { r: r, fill: pale(tn, 0.86), 'class': 'tc' }, v.inner);
        if (t.is === 'decision') {
          v.pic = E('g', { 'class': 'tc' }, v.inner);
          var q = g * 0.46;
          E('path', { d: 'M0 ' + (-q) + ' L' + q + ' 0 L0 ' + q + ' L' + (-q) + ' 0 Z', fill: tn, stroke: C.white, 'stroke-width': ew }, v.pic);
          text(v.pic, 0, g * 0.15, '?', g * 0.42, { fill: C.white, wt: 900, halo: false });
        } else { v.pic = E('g', { 'class': 'tc' }, v.inner); picture(v.pic, t.is, tn, g * 0.86); }
        var f = fit(t.name || '', base, base * 0.82, Math.min(use.cw * 0.86, g * 2.2), 2, 800);
        text(v.inner, 0, r + f.size * 1.05, f.lines, f.size, { fill: C.ink, wt: 800 });
        var br = Math.max(base * 0.66, g * 0.15);
        v.b = { alarm: badge(v.inner, r * 0.92, -r * 0.3, br, 'alarm'), fail: badge(v.inner, r * 0.92, -r * 0.3, br, 'fail'), bug: badge(v.inner, -r * 0.92, -r * 0.3, br, 'bug') };
        v.p = p; v.labH = f.lines.length * f.size * 1.13 + base * 0.3; v.labW = Math.max.apply(null, f.lines.map(function (l) { return tw(l, f.size, 800); }));
        TV[t.id] = v;
      });
      // a tag goes where it covers no thing, no name and no other tag: above, beside, then under the name
      function hits(a, b) { return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }
      // a badge sits on its thing's edge where it touches no other thing's picture or name
      ids.forEach(function (id) {
        var v = TV[id], br = Math.max(base * 0.66, g * 0.15), others = [];
        ids.forEach(function (q) { if (q === id) return; var u = TV[q]; others.push({ x0: u.p.x - r, y0: u.p.y - r, x1: u.p.x + r, y1: u.p.y + r }, { x0: u.p.x - u.labW / 2, y0: u.p.y + r, x1: u.p.x + u.labW / 2, y1: u.p.y + r + u.labH }); });
        var spots = [[r * 0.92, -r * 0.3], [r * 0.74, -r * 0.74], [r * 0.92, r * 0.3], [-r * 0.92, -r * 0.3], [-r * 0.74, -r * 0.74]];
        function cover(c) {
          var x = v.p.x + c[0], y = v.p.y + c[1], bx = { x0: x - br, y0: y - br, x1: x + br, y1: y + br };
          return others.reduce(function (s2, o) { return s2 + (hits(bx, o) ? (Math.min(bx.x1, o.x1) - Math.max(bx.x0, o.x0)) * (Math.min(bx.y1, o.y1) - Math.max(bx.y0, o.y0)) : 0); }, 0);
        }
        var ranked = spots.slice().sort(function (p1, p2) { return cover(p1) - cover(p2); });
        var a = ranked[0], b2 = ranked[1];
        v.b.alarm.parentNode.setAttribute('transform', 'translate(' + a[0].toFixed(1) + ' ' + a[1].toFixed(1) + ')');
        v.b.fail.parentNode.setAttribute('transform', 'translate(' + a[0].toFixed(1) + ' ' + a[1].toFixed(1) + ')');
        v.b.bug.parentNode.setAttribute('transform', 'translate(' + b2[0].toFixed(1) + ' ' + b2[1].toFixed(1) + ')');
      });
      function placeTag(id, s2, size, taken) {
        var v = TV[id], p = v.p, w = tw(s2, size, 800) + size * 1.2, h = size * 1.6;
        var cand = [[p.x, p.y - r - h * 0.7], [p.x + r + w / 2 + base * 0.2, p.y - r * 0.55], [p.x - r - w / 2 - base * 0.2, p.y - r * 0.55], [p.x, p.y + r + v.labH + h * 0.6], [p.x + r + w / 2 + base * 0.2, p.y + r * 0.6]];
        var occ = taken.slice();
        L.forEach(function (l) {                 /* the links too: a tag never lies on a line */
          var P2 = LV[l.key].pts;
          for (var k2 = 1; k2 < P2.length; k2++) occ.push({ x0: Math.min(P2[k2 - 1][0], P2[k2][0]) - ew, y0: Math.min(P2[k2 - 1][1], P2[k2][1]) - ew, x1: Math.max(P2[k2 - 1][0], P2[k2][0]) + ew, y1: Math.max(P2[k2 - 1][1], P2[k2][1]) + ew });
        });
        ids.forEach(function (q) { var u = TV[q]; occ.push({ x0: u.p.x - r, y0: u.p.y - r, x1: u.p.x + r, y1: u.p.y + r }, { x0: u.p.x - u.labW / 2, y0: u.p.y + r, x1: u.p.x + u.labW / 2, y1: u.p.y + r + u.labH }); });
        var best = null;
        for (var i = 0; i < cand.length; i++) {
          var cx2 = clamp(cand[i][0], w / 2 + 4, W - w / 2 - 4), cy2 = clamp(cand[i][1], h / 2 + 2, H - h / 2 - 2);
          var rc = { x0: cx2 - w / 2, y0: cy2 - h / 2, x1: cx2 + w / 2, y1: cy2 + h / 2 };
          if (!occ.some(function (o) { return hits(rc, o); })) { best = [cx2, cy2, rc]; break; }
          if (!best) best = [cx2, cy2, rc];
        }
        taken.push(best[2]);
        return best;
      }
      var sinks = ids.filter(function (id) { return !succ[id].length; });
      function reach(from, cut) {
        var seen = {}, q = [from];
        while (q.length) { var x = q.shift(); if (seen[x]) continue; seen[x] = 1; succ[x].forEach(function (y) { if (!cut[x + '>' + y]) q.push(y); }); }
        return seen;
      }
      var run = [], tags = [];
      function stopRuns() { run.forEach(function (a) { a.stop(); }); run = []; gtok.innerHTML = ''; }
      function travel(chain, kind, onNode, done) {
        var keys = chainKeys(chain), nodes = chainIds(chain), pts = [], marks = [0];
        keys.forEach(function (kk) { var v = LV[kk]; if (!v) return; v.pts.forEach(function (q, j) { if (j || !pts.length) pts.push(q); else pts.push(q); }); marks.push(plen(pts)); });
        if (!pts.length) return;
        var tot = plen(pts), dur = clamp(tot / (Math.max(W, H) / 1500), 900, 3200);
        var tk = E('g', null, gtok), tkIn = E('g', null, tk);
        if (kind === 'bug') picture(tkIn, 'malware', C.warn, g * 0.34);
        else { E('circle', { r: g * 0.12, fill: carry, stroke: C.white, 'stroke-width': ew * 0.8 }, tkIn); }
        var reached = 0;
        run.push(tween(dur, function (kk) {
          var d = ease(kk) * tot, q = along(pts, d);
          tk.setAttribute('transform', 'translate(' + q[0].toFixed(1) + ' ' + q[1].toFixed(1) + ')');
          while (reached < keys.length && d >= marks[reached]) {
            var lv = LV[keys[reached]];
            if (lv && kind !== 'bug') { lv.lit.style.transitionDuration = ((marks[reached + 1] - marks[reached]) / tot * dur / 1000).toFixed(2) + 's'; lv.lit.style.strokeDashoffset = 0; }
            reached++;
            if (onNode) onNode(nodes[reached - 1]);
          }
        }, function () { if (onNode) onNode(nodes[nodes.length - 1]); tk.style.transition = 'opacity .6s'; tk.style.opacity = 0; if (done) done(); }));
      }
      return {
        show: function (st, fwd) {
          stopRuns();
          tags.forEach(function (t2) { t2.parentNode.parentNode.removeChild(t2.parentNode); }); tags = [];
          var lost = {};
          Object.keys(st.fail).forEach(function (id) { var R = reach(id, {}); Object.keys(R).forEach(function (x) { if (x !== id) lost[x] = 1; }); });
          if (Object.keys(st.cut).length) ids.forEach(function (id) { var R = reach(id, st.cut); if (!sinks.some(function (sk) { return R[sk]; })) lost[id] = 1; });
          var animInf = fwd && st.bug ? chainIds(st.bug) : [];
          ids.forEach(function (id) {
            var v = TV[id], on = !!st.shown[id], f = !!st.fail[id], ls = !!lost[id] && !f, inf = !!st.inf[id];
            v.inner.style.opacity = on ? 1 : 0; v.inner.style.transform = on ? 'scale(1)' : 'scale(.55)';
            v.pic.style.opacity = f ? 0.32 : 1;
            v.disc.setAttribute('fill', f ? '#E6E9EE' : inf ? '#F8D7D1' : ls ? '#FBEAC4' : pale(v.tone, 0.86));
            v.ring.setAttribute('stroke-width', st.mark[id] ? ew * 1.2 : 0);
            scaleShow(v.b.fail, f); scaleShow(v.b.alarm, ls); scaleShow(v.b.bug, inf && animInf.indexOf(id) < 0);
          });
          L.forEach(function (l) {
            var v = LV[l.key], on = st.shown[l.a] && st.shown[l.b], lit = !!st.lit[l.key], wr = !!st.wrong[l.key], cut = !!st.cut[l.key] || wr;
            v.g.style.opacity = on ? 1 : 0;
            v.base.setAttribute('stroke', wr ? C.warn : C.line);
            v.base.setAttribute('stroke-dasharray', cut && !wr ? ew * 1.5 + ' ' + ew * 2 : 'none');
            v.head.setAttribute('fill', lit && !cut ? carry : C.line);
            v.lit.style.transitionDuration = '';
            v.lit.style.strokeDashoffset = lit && !cut ? 0 : v.len;
            v.lit.style.opacity = cut ? 0 : 1;
            scaleShow(v.cut, cut);
          });
          if (fwd && st.go) {
            st.go.forEach(function (c2) { chainKeys(c2).forEach(function (kk) { var v = LV[kk]; if (v) instant(v.lit, function () { v.lit.style.strokeDashoffset = v.len; }); }); });
            st.go.forEach(function (c2) { travel(c2, 'data'); });
          }
          if (animInf.length) travel(st.bug, 'bug', function (id) { if (TV[id]) scaleShow(TV[id].b.bug, true); });
          var taken = [];
          Object.keys(st.tag).forEach(function (id) {
            var v = TV[id]; if (!v) return;
            var at = placeTag(id, st.tag[id], base * 0.86, taken);
            var pg = pill(gtag, at[0], at[1], st.tag[id], base * 0.86, C.amber, C.amberInk, 'tz');
            scaleShow(pg, false); tags.push(pg);
            setTimeout(function () { scaleShow(pg, true); }, fwd ? 350 : 0);
          });
        },
        stop: stopRuns
      };
    }
  };

  /* ---------- zones: places kept apart, the things in them, what crosses ---------- */
  var ZONES = {
    check: function (s) {
      var P = [], z = s.zones || [];
      if (z.length < 2 || z.length > 4) P.push(z.length + ' zones; zones hold 2 to 4');
      z.forEach(function (q) { checkName(P, 'zone ' + q.id, q.name); if ((q.things || []).length > 3) P.push('zone ' + q.id + ' has ' + q.things.length + ' things; at most 3'); (q.things || []).forEach(function (t) { checkName(P, 'zone ' + q.id, t.name); checkThing(P, 'zone ' + q.id, t.is); }); });
      (s.steps || []).forEach(function (x, i) { if (x.tag) Object.keys(x.tag).forEach(function (k) { checkName(P, 'step ' + (i + 1) + ' tag', x.tag[k], LIMIT.tag); }); });
      return P;
    },
    state: function (s, n) {
      var st = { walls: !!s.walls, bug: null, mark: {}, tag: {} };
      for (var i = 0; i <= n && i < s.steps.length; i++) {
        var x = s.steps[i];
        if (x.walls != null) st.walls = !!x.walls;
        if (i === n) { st.bug = x.bug || null; st.tag = x.tag || {}; if (x.mark) [].concat(x.mark).forEach(function (id) { st.mark[id] = 1; }); }
      }
      return st;
    },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg, Z = s.zones, nz = Z.length;
      var pad = base * 0.8, x0 = pad, x1 = W - pad, y0 = pad + (s.wall ? base * 2.1 : base * 1.2), y1 = H - pad;
      var hull = !!s.hull, ww = Math.max(12, W * 0.016), bowW = hull ? (x1 - x0) * 0.11 : 0;
      var xi0 = hull ? x0 + (x1 - x0) * 0.03 : x0, xi1 = hull ? x1 - bowW * 1.05 : x1, gap = hull ? 0 : base * 1.1;
      var zw = (xi1 - xi0 - gap * (nz - 1)) / nz, yb = hull ? y1 - (y1 - y0) * 0.04 : y1;
      var gBack = E('g', null, svg);
      fills(gBack, pad, pad, W - 2 * pad, H - 2 * pad);
      if (hull) {
        var yw = y0 + (y1 - y0) * 0.5;
        E('rect', { x: 0, y: yw, width: W, height: H - yw, fill: C.sea }, gBack);
        E('path', { d: 'M0 ' + yw + ' L' + W + ' ' + yw, stroke: C.seaLine, 'stroke-width': 3 }, gBack);
        E('path', { d: 'M' + x0 + ' ' + y0 + ' L' + (x1 - bowW * 0.15) + ' ' + (y0 - base * 0.5) + ' Q' + x1 + ' ' + (y0 - base * 0.6) + ' ' + (x1 - bowW * 0.25) + ' ' + ((y0 + y1) / 2) + ' Q' + (x1 - bowW * 0.6) + ' ' + y1 + ' ' + (x1 - bowW) + ' ' + y1 + ' L' + (x0 + (x1 - x0) * 0.04) + ' ' + y1 + ' Q' + x0 + ' ' + y1 + ' ' + x0 + ' ' + (y1 - (y1 - y0) * 0.3) + ' Z', fill: C.white, stroke: C.navy, 'stroke-width': Math.max(4, base * 0.2), 'stroke-linejoin': 'round' }, gBack);
      }
      var ZV = {}, gW = E('g', null, svg), gTag = E('g', null, svg);
      Z.forEach(function (q, i) {
        var tn = tone(q.tone, i), zx = xi0 + i * (zw + gap), v = { tone: tn, x: zx, w: zw };
        v.panel = E('rect', { x: zx + (hull ? ww * 0.6 : 0), y: y0 + (hull ? base * 0.4 : 0), width: zw - (hull ? ww * 1.2 : 0), height: yb - y0 - (hull ? base * 0.4 : 0), rx: hull ? base * 0.3 : base * 0.6, fill: pale(tn, 0.86), stroke: hull ? 'none' : tn, 'stroke-width': hull ? 0 : 3, 'class': 'tc' }, gBack);
        v.ring = E('rect', { x: zx + ww * 0.6 - 4, y: y0 + base * 0.4 - 4, width: zw - ww * 1.2 + 8, height: yb - y0 - base * 0.4 + 8, rx: base * 0.4, fill: 'none', stroke: C.amber, 'stroke-width': 0, 'class': 'tc' }, gBack);
        var nameY = y0 + base * 1.55;
        pill(gBack, zx + zw / 2, nameY, q.name, Math.min(base * 0.92, fit(q.name, base * 0.92, base * 0.7, zw * 0.8, 1, 800).size), tn, C.white);
        var T = q.things || [], nt = Math.max(1, T.length), lab = base * 2.4;
        var areaTop = nameY + base * 1.2, areaH = yb - areaTop - base * 2.0;
        // side by side, or one above the other when the zone is narrow: whichever gives the larger pictures and names that fit
        var inner = zw - ww * 1.6, across = { cw: inner / nt, ch: areaH }, down = { cw: inner, ch: areaH / nt };
        [across, down].forEach(function (o) {
          o.gz = Math.min(o.cw * 0.82, o.ch - lab, H * 0.36);
          o.fits = T.every(function (t) { return !fit(t.name || '', base * 0.9, base * 0.75, o.cw * 0.84, 2, 800).over; });
        });
        var lay = nt > 1 && (!across.fits || (down.fits && down.gz > across.gz * 1.15)) ? down : across, gz = Math.max(lay.gz, base * 1.6);
        T.forEach(function (t, j) {
          var row = lay === down ? j : 0, col = lay === down ? 0 : j;
          var tx = zx + ww * 0.8 + lay.cw * (col + 0.5), ty = areaTop + lay.ch * row + (lay.ch - (gz + lab)) / 2 + gz / 2;
          var pg = E('g', { transform: 'translate(' + tx.toFixed(1) + ' ' + ty.toFixed(1) + ')' }, gBack);
          picture(pg, t.is, tn, gz);
          var f = fit(t.name || '', base * 0.9, base * 0.75, lay.cw * 0.84, 2, 800);
          text(pg, 0, gz / 2 + f.size * 1.1, f.lines, f.size, { wt: 800 });
        });
        v.bugB = badge(gTag, zx + zw - ww - base * 0.9, y0 + base * 1.55, base * 0.85, 'bug');
        ZV[q.id] = v; v.i = i;
      });
      var walls = [];
      for (var i = 1; i < nz; i++) {
        var bx = xi0 + i * (zw + gap) - gap / 2, wg = E('g', null, gW);
        E('path', { d: 'M' + bx + ' ' + (y0 + base * 0.2) + ' V' + yb, stroke: C.navy, 'stroke-width': 2, 'stroke-dasharray': '3 7', opacity: 0.45 }, wg);
        var brick = E('g', { 'class': 'tb' }, wg), hb = ww * 0.9, yy = y0, row = 0;
        E('rect', { x: bx - ww / 2, y: y0, width: ww, height: yb - y0, fill: C.brick, rx: 2 }, brick);
        for (yy = y0 + hb; yy < yb; yy += hb, row++) E('path', { d: 'M' + (bx - ww / 2) + ' ' + yy.toFixed(1) + ' h' + ww + (row % 2 ? ' M' + bx + ' ' + yy.toFixed(1) + ' v' + hb.toFixed(1) : ''), stroke: '#F3D2CB', 'stroke-width': 1.6 }, brick);
        walls.push({ g: brick, x: bx });
      }
      var wallTag = null;
      if (s.wall && walls.length) { wallTag = pill(gW, walls[0].x, y0 - base * 1.0, s.wall, base * 0.8, C.brick, C.white, 'tz'); }
      var timers = [], stopped = null;
      return {
        show: function (st, fwd) {
          timers.forEach(clearTimeout); timers = [];
          if (stopped) { stopped.parentNode.parentNode.removeChild(stopped.parentNode); stopped = null; }
          walls.forEach(function (w) { w.g.style.transform = st.walls ? 'scaleY(1)' : 'scaleY(0)'; });
          if (wallTag) scaleShow(wallTag, st.walls);
          gTag.querySelectorAll('.n2-ztag').forEach(function (e) { e.parentNode.parentNode.removeChild(e.parentNode); });
          var hit = {};
          if (st.bug && ZV[st.bug]) {
            var i0 = ZV[st.bug].i;
            Z.forEach(function (q) { var d = Math.abs(ZV[q.id].i - i0); if (!st.walls || d === 0) hit[q.id] = d; });
          }
          Z.forEach(function (q) {
            var v = ZV[q.id], h = q.id in hit;
            v.ring.setAttribute('stroke-width', st.mark[q.id] ? 6 : 0);
            function on() { v.panel.setAttribute('fill', h ? '#F6D3CC' : pale(v.tone, 0.86)); scaleShow(v.bugB, h); }
            if (h && fwd) { v.panel.setAttribute('fill', pale(v.tone, 0.86)); scaleShow(v.bugB, false); timers.push(setTimeout(on, 250 + hit[q.id] * 650)); } else on();
          });
          if (st.bug && st.walls && ZV[st.bug]) {
            var v0 = ZV[st.bug], wx = v0.i < walls.length ? walls[v0.i].x : walls[v0.i - 1].x;
            stopped = pill(gTag, wx, (y0 + yb) / 2, s.stopped || 'Stopped', base * 0.8, C.good, C.white, 'tz');
            scaleShow(stopped, false);
            timers.push(setTimeout(function () { if (stopped) scaleShow(stopped, true); }, fwd ? 900 : 0));
          }
          Object.keys(st.tag).forEach(function (id) {
            var v = ZV[id]; if (!v) return;
            var pg = pill(gTag, v.x + v.w / 2, yb - base * 1.25, st.tag[id], Math.min(base * 0.82, fit(st.tag[id], base * 0.82, base * 0.62, v.w * 0.86, 1, 800).size), C.amber, C.amberInk, 'tz n2-ztag');
            scaleShow(pg, false); timers.push(setTimeout(function () { scaleShow(pg, true); }, fwd ? 300 : 0));
          });
        },
        stop: function () { timers.forEach(clearTimeout); }
      };
    }
  };

  /* ---------- steps: a procedure, one action at a time ---------- */
  var STEPS = {
    check: function (s) {
      var P = [], S = s.steps || [];
      if (S.length < 2 || S.length > 7) P.push(S.length + ' steps; a procedure shows 2 to 7 - group the rest');
      S.forEach(function (x, i) { checkThing(P, 'step ' + (i + 1), x.is); checkName(P, 'step ' + (i + 1), x['do'], LIMIT.act); if (x.read && String(x.read).length > LIMIT.read) P.push('step ' + (i + 1) + ' reading "' + x.read + '" is too long'); });
      return P;
    },
    state: function (s, n) { return { n: n }; },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg, S = s.steps, n = S.length;
      var pad = base * 0.8, rr = Math.min((W - 2 * pad) / (n * 2.5), H * 0.085, 56), railY = H - pad - rr * 1.15;
      var heroTop = pad, heroBot = railY - rr * 1.15 - base * 0.9, heroH = heroBot - heroTop, wide = W / H > 1.1;
      var gs = wide ? Math.min(heroH * 0.9, W * 0.34) : Math.min(heroH * 0.5, W * 0.6);
      var gx = wide ? pad + gs / 2 + W * 0.03 : W / 2, gy = wide ? heroTop + heroH / 2 : heroTop + gs / 2 + base * 0.3;
      var txL = wide ? gx + gs / 2 + base * 1.4 : pad, txW = wide ? W - pad - txL : W - 2 * pad;
      var heroes = [], tn = tone(s.tone || 'blue');
      fills(svg, pad, pad, W - 2 * pad, H - 2 * pad);
      S.forEach(function (x, i) {
        var hg = E('g', { 'class': 'tr' }, svg);
        var pg = E('g', { transform: 'translate(' + gx.toFixed(1) + ' ' + gy.toFixed(1) + ')' }, hg);
        E('circle', { r: gs * 0.5, fill: pale(tone(x.tone || s.tone || 'blue'), 0.86) }, pg);
        picture(pg, x.is, tone(x.tone || s.tone || 'blue'), gs * 0.74);
        var f = fit(x['do'], base * 2.1, base * 1.3, txW, 2, 800);
        var blockH = base * 1.2 + f.lines.length * f.size * 1.13 + (x.read ? base * 2.4 : 0);
        var ty = wide ? gy - blockH / 2 + base * 0.9 : gy + gs / 2 + base * 1.5;
        var anchor = wide ? 'start' : 'middle', ax = wide ? txL : W / 2;
        text(hg, ax, ty, 'Step ' + (i + 1) + ' of ' + n, base * 0.8, { fill: C.sub, anchor: anchor, wt: 700 });
        text(hg, ax, ty + base * 0.55 + f.size, f.lines, f.size, { fill: C.navy, anchor: anchor, wt: 800 });
        if (x.read) {
          var ry = ty + base * 0.55 + f.size + (f.lines.length - 1) * f.size * 1.13 + base * 1.65;
          var rw = tw(x.read, base * 1.15, 800) + base * 1.4, rx0 = wide ? txL : W / 2 - rw / 2;
          E('rect', { x: rx0, y: ry - base * 1.05, width: rw, height: base * 1.75, rx: base * 0.35, fill: C.navy }, hg);
          text(hg, rx0 + rw / 2, ry + base * 0.15, x.read, base * 1.15, { fill: '#7FF0B6', wt: 800, halo: false });
        }
        heroes.push(hg);
      });
      var x0 = pad + (W - 2 * pad) / n / 2, x1 = W - pad - (W - 2 * pad) / n / 2;
      E('path', { d: 'M' + x0 + ' ' + railY + ' H' + x1, stroke: C.ghost, 'stroke-width': rr * 0.22, 'stroke-linecap': 'round' }, svg);
      var prog = E('path', { d: 'M' + x0 + ' ' + railY + ' H' + x1, stroke: C.good, 'stroke-width': rr * 0.22, 'stroke-linecap': 'round', 'stroke-dasharray': (x1 - x0) + ' ' + (x1 - x0 + 9), 'stroke-dashoffset': x1 - x0, 'class': 'td' }, svg);
      var dots = S.map(function (x, i) {
        var cxp = x0 + (x1 - x0) * (n > 1 ? i / (n - 1) : 0.5);
        var pos = E('g', { transform: 'translate(' + cxp.toFixed(1) + ' ' + railY.toFixed(1) + ')' }, svg), gd = E('g', { 'class': 'tz' }, pos);
        var c = E('circle', { r: rr, fill: C.white, stroke: C.line, 'stroke-width': rr * 0.12, 'class': 'tc' }, gd);
        var pic = E('g', { 'class': 'tc' }, gd); picture(pic, x.is, tone(x.tone || s.tone || 'blue'), rr * 1.3);
        var ok = badge(gd, rr * 0.72, -rr * 0.72, rr * 0.42, 'ok');
        return { c: c, g: gd, pic: pic, ok: ok, x: cxp };
      });
      return {
        show: function (st, fwd) {
          heroes.forEach(function (hg, i) { hg.style.opacity = i === st.n ? 1 : 0; hg.style.transform = 'translateX(' + (i === st.n ? 0 : i < st.n ? -40 : 40) + 'px)'; });
          prog.style.strokeDashoffset = (x1 - x0) * (1 - (n > 1 ? st.n / (n - 1) : 1));
          dots.forEach(function (d, i) {
            var done = i < st.n, cur = i === st.n;
            d.c.setAttribute('stroke', cur ? C.amber : done ? C.good : C.line);
            d.c.setAttribute('stroke-width', cur ? rr * 0.24 : rr * 0.12);
            d.c.setAttribute('fill', done ? '#E3F3EC' : C.white);
            d.pic.style.opacity = i > st.n ? 0.4 : 1;
            d.g.style.transform = cur ? 'scale(1.14)' : 'scale(1)';
            scaleShow(d.ok, done);
          });
        }
      };
    }
  };

  /* ---------- options: two or three choices, rated, raced ---------- */
  var OPTIONS = {
    check: function (s) {
      var P = [], O = s.options || [], Q = s.qualities || [];
      if (O.length < 2 || O.length > 3) P.push(O.length + ' options; 2 or 3');
      if (Q.length < 1 || Q.length > 3) P.push(Q.length + ' qualities; 1 to 3');
      O.forEach(function (o, i) { checkName(P, 'option ' + (i + 1), o.name); checkThing(P, 'option ' + (i + 1), o.is); });
      Q.forEach(function (q, i) { checkName(P, 'quality ' + (i + 1), q.name, 2); (q.values || []).forEach(function (v) { if (v < 0 || v > 3) P.push('quality ' + q.name + ': a value is 0 to 3'); }); (q.words || []).forEach(function (w) { checkName(P, 'quality ' + q.name, w, LIMIT.words); }); });
      return P;
    },
    state: function (s, n) {
      var st = { show: s.qualities.length, race: null, pick: null, tag: {} }, any = s.steps.some(function (x) { return x.show != null; });
      if (any) st.show = 0;
      for (var i = 0; i <= n && i < s.steps.length; i++) {
        var x = s.steps[i];
        if (x.show != null) st.show = Math.max(st.show, x.show);
        if (i === n) { st.race = x.race != null ? x.race : null; st.pick = x.pick != null ? x.pick : null; st.tag = x.tag || {}; }
      }
      return st;
    },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg, O = s.options, Q = s.qualities, nO = O.length, nQ = Q.length;
      var pad = base * 0.8, qs = base * 0.95;
      var Lw = Math.min(W * 0.3, Math.max.apply(null, Q.map(function (q) { return Math.min(tw(q.name, qs, 800), W * 0.26); })) + base);
      var colW = (W - 2 * pad - Lw) / nO, gh = Math.min(colW * 0.5, H * 0.24);
      var nameY = pad + gh + base * 1.15, rowsTop = nameY + base * 1.1, rowH = (H - pad - rowsTop) / nQ;
      var colX = O.map(function (o, i) { return pad + Lw + colW * (i + 0.5); });
      var PK = [];
      fills(svg, pad, pad, W - 2 * pad, H - 2 * pad);
      O.forEach(function (o, i) {
        var tn = tone(o.tone, i), pos = E('g', { transform: 'translate(' + colX[i].toFixed(1) + ' ' + (pad + gh / 2).toFixed(1) + ')' }, svg);
        E('circle', { r: gh * 0.5, fill: pale(tn, 0.86) }, pos); picture(pos, o.is, tn, gh * 0.82);
        var f = fit(o.name, base, base * 0.8, colW * 0.96, 1, 800);
        text(svg, colX[i], nameY, f.lines, f.size, { wt: 800 });
        PK.push(E('rect', { x: colX[i] - colW * 0.47, y: pad - base * 0.3, width: colW * 0.94, height: H - pad * 2 + base * 0.6, rx: base * 0.6, fill: 'none', stroke: C.amber, 'stroke-width': 0, 'class': 'tc' }, svg));
      });
      var rows = Q.map(function (q, qi) {
        var cy = rowsTop + rowH * (qi + 0.5), rg = E('g', { 'class': 'tc' }, svg), rv = { g: rg, cells: [], cy: cy };
        E('path', { d: 'M' + pad + ' ' + (rowsTop + rowH * qi).toFixed(1) + ' H' + (W - pad), stroke: C.ghost, 'stroke-width': 2 }, rg);
        var f = fit(q.name, qs, base * 0.75, Lw - base * 0.6, 2, 800);
        text(rg, pad, cy - base * 0.1 - (f.lines.length - 1) * f.size * 0.56, f.lines, f.size, { anchor: 'start', wt: 800, fill: C.navy });
        text(rg, pad, cy + base * 0.95, q.low ? 'less is better' : 'more is better', base * 0.62, { anchor: 'start', wt: 700, fill: C.sub });
        // pips always mean "better": a quality where low is good is filled the other way round
        var good = q.values.map(function (v) { return q.low ? 4 - v : v; });
        var pw = Math.min(colW * 0.17, rowH * 0.42), ph = pw * 0.62, gp = pw * 0.22, hasW = q.words && q.words.length;
        O.forEach(function (o, i) {
          var tn = tone(o.tone, i), cg = E('g', { 'class': 'tc' }, rg), py = cy - (hasW ? base * 0.5 : 0) - ph / 2, cell = { g: cg, pips: [] };
          for (var k = 0; k < 3; k++) cell.pips.push(E('rect', { x: colX[i] - (3 * pw + 2 * gp) / 2 + k * (pw + gp), y: py, width: pw, height: ph, rx: ph * 0.3, fill: k < good[i] ? tn : C.ghost, 'class': 'tc' }, cg));
          if (hasW && q.words[i]) text(cg, colX[i], py + ph + base * 1.1, q.words[i], base * 0.86, { fill: C.ink, wt: 800 });
          var trk = E('g', { 'class': 'tc' }, rg), tx0 = colX[i] - colW * 0.38, tx1 = colX[i] + colW * 0.38;
          E('path', { d: 'M' + tx0 + ' ' + cy + ' H' + tx1, stroke: pale(tn, 0.5), 'stroke-width': base * 0.3, 'stroke-linecap': 'round' }, trk);
          E('path', { d: 'M' + tx1 + ' ' + (cy - base * 0.6) + ' V' + (cy + base * 0.6), stroke: C.navy, 'stroke-width': 3 }, trk);
          var dot = E('circle', { cx: tx0, cy: cy, r: base * 0.45, fill: tn, stroke: C.white, 'stroke-width': 3 }, trk);
          trk.style.opacity = 0;
          cell.trk = trk; cell.dot = dot; cell.tx0 = tx0; cell.tx1 = tx1;
          rv.cells.push(cell);
        });
        return rv;
      });
      var runs = [], tagG = E('g', null, svg);
      return {
        show: function (st, fwd) {
          runs.forEach(function (r2) { r2.stop(); }); runs = []; tagG.innerHTML = '';
          rows.forEach(function (rv, qi) {
            rv.g.style.opacity = qi < st.show ? 1 : 0.28;
            var racing = st.race === qi;
            rv.cells.forEach(function (c, i) {
              c.pips.forEach(function (p) { p.style.opacity = racing ? 0 : 1; });
              c.g.style.opacity = racing ? 0 : 1;
              c.trk.style.opacity = racing ? 1 : 0;
              c.dot.setAttribute('cx', c.tx0);
              if (racing) {
                var q = Q[qi], v = q.values[i], dur = 500 + 1100 * (q.low ? v : 3 - v + 1);
                (function (cc, d0) { runs.push(tween(fwd ? d0 : 0, function (k) { cc.dot.setAttribute('cx', (cc.tx0 + (cc.tx1 - cc.tx0) * ease(k)).toFixed(1)); })); })(c, dur);
              }
            });
          });
          PK.forEach(function (r2, i) { r2.setAttribute('stroke-width', st.pick === i ? 6 : 0); });
          Object.keys(st.tag).forEach(function (k) {
            var i = +k; if (!(i >= 0 && i < nO)) return;
            var pg = pill(tagG, colX[i], H - pad - base * 0.2, st.tag[k], base * 0.82, C.amber, C.amberInk, 'tz');
            scaleShow(pg, false); setTimeout(function () { scaleShow(pg, true); }, fwd ? 300 : 0);
          });
        },
        stop: function () { runs.forEach(function (r2) { r2.stop(); }); }
      };
    }
  };

  /* ---------- amounts: numbers that change, the change measured by code ---------- */
  function nice(a, b, n) {
    var span = b - a || 1, step = Math.pow(10, Math.floor(Math.log10(span / n))), m = span / n / step;
    step *= m > 5 ? 10 : m > 2 ? 5 : m > 1 ? 2 : 1;
    var lo = Math.floor(a / step) * step, hi = Math.ceil(b / step) * step, t = [];
    for (var v = lo; v <= hi + step * 0.01; v += step) t.push(+v.toFixed(6));
    return { lo: lo, hi: hi, step: step, ticks: t };
  }
  var AMOUNTS = {
    check: function (s) {
      var P = [], S = s.series || [];
      if (S.length < 1 || S.length > 3) P.push(S.length + ' series; 1 to 3');
      S.forEach(function (q) { checkName(P, 'series', q.name); if ((q.pts || []).length < 2 || q.pts.length > 24) P.push('series ' + q.name + ': 2 to 24 points'); });
      if (s.scale && s.scale.bands && s.scale.bands.length > 5) P.push('a scale has at most 5 bands');
      (s.steps || []).forEach(function (x, i) { if (x.tag) checkName(P, 'step ' + (i + 1) + ' tag', x.tag, LIMIT.tag); });
      return P;
    },
    state: function (s, n) {
      var xs = []; s.series.forEach(function (q) { q.pts.forEach(function (p) { xs.push(p[0]); }); });
      var st = { upto: Math.max.apply(null, xs), span: null, tag: null };
      for (var i = 0; i <= n && i < s.steps.length; i++) { var x = s.steps[i]; if (x.upto != null) st.upto = x.upto; if (i === n) { st.span = x.span || null; st.tag = x.tag || null; } }
      return st;
    },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg, S = s.series;
      var xs = [], ys = []; S.forEach(function (q) { q.pts.forEach(function (p) { xs.push(p[0]); ys.push(p[1]); }); });
      if (s.limit) ys.push(s.limit.value);
      var X = nice(Math.min.apply(null, xs), Math.max.apply(null, xs), 6), Y = nice(Math.min.apply(null, ys), Math.max.apply(null, ys), 5);
      X.lo = Math.min.apply(null, xs); X.hi = Math.max.apply(null, xs);
      var pad = base * 0.8, tick = base * 0.82, dec = s.y && s.y.decimals || 0;
      var yl = Math.max.apply(null, Y.ticks.map(function (v) { return tw(v.toFixed(dec), tick, 700); }));
      var spanRoom = s.steps.some(function (x) { return x.span; }) ? tw('−00 ' + ((s.y && s.y.unit) || '') + ' in 00 ' + ((s.x && s.x.unit) || ''), base * 1.15, 900) + base * 1.2 : base * 0.6;
      var top = pad + base * 4.1, left = pad + yl + base * 0.6, right = W - pad - spanRoom, bottom = H - pad - base * 2.5;
      function px(x) { return left + (x - X.lo) / (X.hi - X.lo) * (right - left); }
      function py(y) { return bottom - (y - Y.lo) / (Y.hi - Y.lo) * (bottom - top); }
      var gGrid = E('g', null, svg);
      fills(gGrid, pad, pad, W - 2 * pad, H - 2 * pad);
      Y.ticks.forEach(function (v) { E('path', { d: 'M' + left + ' ' + py(v).toFixed(1) + ' H' + right, stroke: C.ghost, 'stroke-width': 2 }, gGrid); text(gGrid, left - base * 0.4, py(v) + tick * 0.35, v.toFixed(dec), tick, { anchor: 'end', fill: C.sub, wt: 700 }); });
      var xt = nice(X.lo, X.hi, 6).ticks.filter(function (v) { return v >= X.lo && v <= X.hi; });
      xt.forEach(function (v) { text(gGrid, px(v), bottom + tick * 1.35, String(v), tick, { fill: C.sub, wt: 700 }); });
      E('path', { d: 'M' + left + ' ' + top + ' V' + bottom + ' H' + right, stroke: C.navy, 'stroke-width': 3, fill: 'none' }, gGrid);
      if (s.x && s.x.name) text(gGrid, (left + right) / 2, H - pad, s.x.name + (s.x.unit ? ' (' + s.x.unit + ')' : ''), base * 0.82, { fill: C.sub, wt: 700 });
      if (s.limit) {
        E('path', { d: 'M' + left + ' ' + py(s.limit.value).toFixed(1) + ' H' + right, stroke: C.warn, 'stroke-width': 3, 'stroke-dasharray': '10 8' }, gGrid);
        text(gGrid, right, py(s.limit.value) - base * 0.4, s.limit.name, base * 0.8, { anchor: 'end', fill: C.warn, wt: 800 });
      }
      var clipId = 'n2c' + Math.random().toString(36).slice(2, 8), defs = E('defs', null, svg), cp = E('clipPath', { id: clipId }, defs);
      var clipR = E('rect', { x: 0, y: 0, width: px(X.hi) + base, height: H }, cp);
      var gS = E('g', { 'clip-path': 'url(#' + clipId + ')' }, svg);
      S.forEach(function (q, i) { E('path', { d: dPath(q.pts.map(function (p) { return [px(p[0]), py(p[1])]; }), 0), fill: 'none', stroke: tone(q.tone, i), 'stroke-width': Math.max(5, base * 0.22), 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, gS); });
      var main = S[0], mt = tone(main.tone, 0);
      function yAt(x) { var p = main.pts; for (var i = 1; i < p.length; i++) if (x <= p[i][0]) { var k = (x - p[i - 1][0]) / (p[i][0] - p[i - 1][0] || 1); return p[i - 1][1] + (p[i][1] - p[i - 1][1]) * k; } return p[p.length - 1][1]; }
      var tip = E('circle', { r: base * 0.42, fill: mt, stroke: C.white, 'stroke-width': 4 }, svg);
      var unit = s.y && s.y.unit ? ' ' + s.y.unit : '';
      var readName = text(svg, pad, pad + base * 0.85, (s.y && s.y.name) || main.name, base * 0.8, { anchor: 'start', fill: C.sub, wt: 700 });
      var read = text(svg, pad, pad + base * 2.75, '', base * 1.75, { anchor: 'start', fill: C.navy, wt: 900 });
      var sc = null;
      if (s.scale) {
        var B = s.scale.bands, sx0 = Math.max(W * 0.36, pad + tw('0000 hPa', base * 1.75, 900) + base), sx1 = W - pad, sy = pad + base * 1.45, sh = base * 1.45, segW = (sx1 - sx0) / B.length;
        sc = { g: E('g', null, svg), x0: sx0, segW: segW, B: B };
        text(sc.g, sx0, pad + base * 0.6, s.scale.name, base * 0.75, { anchor: 'start', fill: C.sub, wt: 700 });
        var cols = ['#2E8B3E', '#8DB33A', '#E9A51E', '#D46A12', '#C8402F'];
        B.forEach(function (b, i) {
          E('rect', { x: sx0 + i * segW + 1, y: sy, width: segW - 2, height: sh, rx: 4, fill: b.tone ? tone(b.tone) : cols[Math.round(i * (cols.length - 1) / Math.max(1, B.length - 1))] }, sc.g);
          var f = fit(b.name, base * 0.85, base * 0.62, segW - 8, 1, 800);
          text(sc.g, sx0 + (i + 0.5) * segW, sy + sh / 2 + f.size * 0.36, f.lines, f.size, { fill: C.white, wt: 800, halo: false });
        });
        sc.ptr = E('path', { d: 'M0 0 l-' + base * 0.5 + ' -' + base * 0.7 + ' h' + base + ' z', fill: C.navy, transform: 'translate(' + sx0 + ' ' + sy + ')' }, sc.g);
        sc.sy = sy; sc.g.style.opacity = 0.35; sc.g.setAttribute('class', 'tc');
      }
      var gSpan = E('g', null, svg), cur = null, run = null, tagT = null;
      function place(u) {
        clipR.setAttribute('width', Math.max(0, px(u) - 0 + base * 0.1).toFixed(1));
        var y = yAt(u); tip.setAttribute('cx', px(u).toFixed(1)); tip.setAttribute('cy', py(y).toFixed(1));
        setText(read, y.toFixed(dec) + unit);
      }
      return {
        show: function (st, fwd) {
          if (run) run.stop();
          gSpan.innerHTML = '';
          var from = cur == null ? st.upto : cur;
          cur = st.upto;
          run = tween(fwd && from < st.upto ? 1600 : 0, function (k) { place(from + (st.upto - from) * ease(k)); }, function () {
            if (st.span) {
              var a = st.span[0], b = st.span[1], ya = yAt(a), yb = yAt(b), d = yb - ya;
              var g2 = E('g', { 'class': 'tz' }, gSpan);
              E('path', { d: 'M' + px(a) + ' ' + py(ya) + ' H' + px(b), stroke: C.navy, 'stroke-width': 2.5, 'stroke-dasharray': '6 6' }, g2);
              E('path', { d: 'M' + px(b) + ' ' + py(ya) + ' V' + (py(yb) + (d < 0 ? -base * 0.5 : base * 0.5)), stroke: C.warn, 'stroke-width': base * 0.28, 'stroke-linecap': 'round' }, g2);
              var ah = base * 0.6, yy = py(yb), dir = d < 0 ? 1 : -1;
              E('path', { d: 'M' + (px(b) - ah) + ' ' + (yy - dir * ah * 1.1) + ' L' + px(b) + ' ' + yy + ' L' + (px(b) + ah) + ' ' + (yy - dir * ah * 1.1) + ' Z', fill: C.warn }, g2);
              var lbl = (d > 0 ? '+' : '−') + Math.abs(d).toFixed(dec) + unit + ' in ' + (b - a) + (s.x && s.x.unit ? ' ' + s.x.unit : '');
              text(g2, px(b) + base * 0.7, (py(ya) + py(yb)) / 2 + base * 0.4, lbl, base * 1.15, { anchor: 'start', fill: C.warn, wt: 900 });
              scaleShow(g2, false); setTimeout(function () { scaleShow(g2, true); }, 30);
              if (sc) {
                var m = Math.abs(d), idx = 0; while (idx < sc.B.length - 1 && m > sc.B[idx].to) idx++;
                var lo = idx ? sc.B[idx - 1].to : 0, hi = sc.B[idx].to, kk = hi > lo ? clamp((m - lo) / (hi - lo), 0.1, 0.9) : 0.5;
                sc.g.style.opacity = 1;
                sc.ptr.setAttribute('transform', 'translate(' + (sc.x0 + (idx + kk) * sc.segW).toFixed(1) + ' ' + sc.sy + ')');
              }
            } else if (sc) sc.g.style.opacity = 0.35;
            if (st.tag) {
              var tgw = tw(st.tag, base * 0.86, 800) + base * 1.1, ty0 = py(yAt(st.upto));
              var pg = pill(gSpan, clamp(px(st.upto) - tgw * 0.35, left + tgw / 2, W - pad - tgw / 2), Math.min(ty0 + base * 1.8, bottom - base * 0.9), st.tag, base * 0.86, C.amber, C.amberInk, 'tz');
              scaleShow(pg, false); setTimeout(function () { scaleShow(pg, true); }, 30);
            }
          });
        },
        stop: function () { if (run) run.stop(); }
      };
    }
  };

  /* ---------- scenes: one real system a module tells its story on ---------- */
  var SCENES = {};
  SCENES.pump_line = {
    check: function (s) {
      var P = [];
      checkName(P, 'from', s.from && s.from.name); checkName(P, 'to', s.to && s.to.name);
      (s.parts || []).forEach(function (p) { if (['filter', 'pump', 'gauge', 'valve'].indexOf(p) < 0) P.push('pump_line has no part "' + p + '" (filter, pump, gauge, valve)'); });
      (s.steps || []).forEach(function (x, i) { if (x.tag) Object.keys(x.tag).forEach(function (k) { checkName(P, 'step ' + (i + 1) + ' tag', x.tag[k], LIMIT.tag); }); });
      return P;
    },
    state: function (s, n) {
      var st = { pump: false, valve: false, a: s.from.level, b: s.to.level, tag: {} };
      for (var i = 0; i <= n && i < s.steps.length; i++) {
        var x = s.steps[i];
        if (x.pump != null) st.pump = x.pump === 'on' || x.pump === true;
        if (x.valve != null) st.valve = x.valve === 'open' || x.valve === true;
        var flow = st.pump && st.valve, mv = s.transfer || 0.25;
        if (flow && i > 0) { var d = Math.min(mv, st.a - 0.08); st.a -= d; st.b = Math.min(0.95, st.b + d); }
        if (i === n) st.tag = x.tag || {};
      }
      st.flow = st.pump && st.valve;
      st.p = !st.pump ? 0.04 : st.valve ? 0.55 : 0.93;
      return st;
    },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg;
      var pad = base * 0.8, tankW = W * 0.14, pr = clamp(H * 0.042, 10, 26);
      fills(svg, pad, pad, W - 2 * pad, H - 2 * pad);
      var yLow = H - pad - (pr * 2.25 + base * 4.1), tankH = Math.min(H * 0.6, yLow - pad - base * 2.4), tB = yLow + tankH * 0.14, tT = tB - tankH;
      var Lx = pad, Rx = W - pad - tankW, yHigh = tT + tankH * 0.18, riseX = Rx - pr * 2.4;
      var oil = s.liquid === 'water' ? '#2F7FC0' : C.oil, oilHi = s.liquid === 'water' ? '#A9D6F5' : C.oilHi;
      function tank(x, t) {
        var g = E('g', null, svg), clip = 'n2t' + Math.random().toString(36).slice(2, 7), defs = E('defs', null, g), cp = E('clipPath', { id: clip }, defs);
        E('rect', { x: x, y: tT, width: tankW, height: tankH, rx: base * 0.4 }, cp);
        E('rect', { x: x, y: tT, width: tankW, height: tankH, rx: base * 0.4, fill: '#F3F6FA' }, g);
        var liq = E('rect', { x: x, y: tT, width: tankW, height: tankH, fill: oil, 'clip-path': 'url(#' + clip + ')', 'class': 'tb' }, g);
        for (var k = 1; k < 4; k++) E('path', { d: 'M' + (x + tankW - base * 0.7) + ' ' + (tT + tankH * k / 4) + ' h' + base * 0.5, stroke: C.navy, 'stroke-width': 2, opacity: 0.5 }, g);
        E('rect', { x: x, y: tT, width: tankW, height: tankH, rx: base * 0.4, fill: 'none', stroke: C.navy, 'stroke-width': Math.max(4, base * 0.18) }, g);
        var f = fit(t.name, base * 0.95, base * 0.7, tankW + 2 * pad - 8, 2, 800);     /* never past the frame's edge */
        text(g, x + tankW / 2, tB + base * 1.3, f.lines, f.size, { wt: 800 });
        return liq;
      }
      var pts = [[Lx + tankW, yLow], [riseX, yLow], [riseX, yHigh], [Rx, yHigh]], dd = dPath(pts, pr * 1.4);
      E('path', { d: dd, fill: 'none', stroke: C.navy, 'stroke-width': pr + 9, 'stroke-linejoin': 'round' }, svg);
      E('path', { d: dd, fill: 'none', stroke: oil, 'stroke-width': pr, 'stroke-linejoin': 'round' }, svg);
      var per = pr * 2.6, streak = E('path', { d: dd, fill: 'none', stroke: oilHi, 'stroke-width': pr * 0.36, 'stroke-linecap': 'round', 'stroke-dasharray': (pr * 0.9).toFixed(1) + ' ' + (per - pr * 0.9).toFixed(1), 'class': 'tc' }, svg);
      var flowA = streak.animate ? streak.animate([{ strokeDashoffset: 0 }, { strokeDashoffset: -per }], { duration: 380, iterations: Infinity }) : null;
      if (flowA) flowA.pause();
      var liqA = tank(Lx, s.from), liqB = tank(Rx, s.to);
      [[Lx + tankW, yLow], [Rx, yHigh]].forEach(function (q) { E('rect', { x: q[0] - 4, y: q[1] - pr * 0.95, width: 8, height: pr * 1.9, fill: C.navy, rx: 2 }, svg); });
      var parts = s.parts || ['pump', 'valve'], run0 = Lx + tankW + pr * 2, run1 = riseX - pr * 2.2, V = {};
      var labY = yLow + pr * 2.25 + base * 0.95, slot = (run1 - run0) / Math.max(1, parts.length), stateY = labY + base * 2.3;
      parts.forEach(function (p, i) {
        var x = run0 + (run1 - run0) * (parts.length > 1 ? (i + 0.5) / parts.length : 0.5), g = E('g', null, svg), nm;
        if (p === 'pump') {
          var rp = pr * 2.1, tn = tone(s.tone || 'slate');
          E('rect', { x: x - pr * 1.3, y: yLow - rp - pr * 2.6, width: pr * 2.6, height: pr * 2.2, rx: 4, fill: C.navy }, g);
          for (var k = 0; k < 4; k++) E('path', { d: 'M' + (x - pr * 1.1) + ' ' + (yLow - rp - pr * 2.2 + k * pr * 0.5) + ' h' + pr * 2.2, stroke: '#8FA3C0', 'stroke-width': 2 }, g);
          E('rect', { x: x - pr * 0.25, y: yLow - rp - pr * 0.45, width: pr * 0.5, height: pr * 0.6, fill: C.navy }, g);
          E('circle', { cx: x, cy: yLow, r: rp, fill: tn, stroke: C.navy, 'stroke-width': 4 }, g);
          E('circle', { cx: x, cy: yLow, r: rp * 0.66, fill: C.white }, g);
          var imp = E('g', null, g);
          for (k = 0; k < 6; k++) E('path', { transform: 'rotate(' + k * 60 + ' ' + x + ' ' + yLow + ')', d: 'M' + x + ' ' + yLow + ' q' + rp * 0.3 + ' ' + (-rp * 0.2) + ' ' + rp * 0.18 + ' ' + (-rp * 0.6), fill: 'none', stroke: C.navy, 'stroke-width': Math.max(3, pr * 0.2), 'stroke-linecap': 'round' }, imp);
          E('circle', { cx: x, cy: yLow, r: rp * 0.12, fill: C.navy }, imp);
          imp.style.transformBox = 'view-box'; imp.style.transformOrigin = x + 'px ' + yLow + 'px';
          V.spin = imp.animate ? imp.animate([{ transform: 'rotate(0deg)' }, { transform: 'rotate(360deg)' }], { duration: 650, iterations: Infinity }) : null;
          if (V.spin) V.spin.pause();
          nm = s.names && s.names.pump || 'Pump';
          V.pumpState = pill(svg, x, stateY, 'Stopped', base * 0.7, C.ghost, C.navy);
          V.pumpAt = [x, yLow - rp - pr * 2.6 - base * 1.1];
        } else if (p === 'filter') {
          E('rect', { x: x - pr * 1.1, y: yLow - pr * 2.2, width: pr * 2.2, height: pr * 3.4, rx: pr * 0.5, fill: tone('slate'), stroke: C.navy, 'stroke-width': 3 }, g);
          E('rect', { x: x - pr * 1.3, y: yLow - pr * 2.6, width: pr * 2.6, height: pr * 0.6, rx: 3, fill: C.navy }, g);
          for (k = 0; k < 3; k++) E('path', { d: 'M' + (x - pr * 0.7) + ' ' + (yLow - pr * 1.4 + k * pr * 0.7) + ' h' + pr * 1.4, stroke: C.white, 'stroke-width': 2, opacity: 0.7 }, g);
          nm = s.names && s.names.filter || 'Filter';
        } else if (p === 'gauge') {
          var gr = pr * 1.55, gy = yLow - pr / 2 - pr * 1.3 - gr;
          E('path', { d: 'M' + x + ' ' + (yLow - pr / 2) + ' V' + (gy + gr), stroke: C.navy, 'stroke-width': 5 }, g);
          E('circle', { cx: x, cy: gy, r: gr, fill: C.white, stroke: C.navy, 'stroke-width': 4 }, g);
          function arc(a1, a2, col) { var r = gr * 0.78, f = function (a) { a = (a - 90) * Math.PI / 180; return (x + r * Math.cos(a)).toFixed(1) + ' ' + (gy + r * Math.sin(a)).toFixed(1); }; E('path', { d: 'M' + f(a1) + ' A' + r + ' ' + r + ' 0 0 1 ' + f(a2), fill: 'none', stroke: col, 'stroke-width': gr * 0.2 }, g); }
          arc(-120, 40, '#2E8B3E'); arc(40, 80, C.amber); arc(80, 120, C.warn);
          var nd = E('g', null, g); E('path', { d: 'M' + x + ' ' + gy + ' L' + x + ' ' + (gy - gr * 0.72), stroke: C.navy, 'stroke-width': 4, 'stroke-linecap': 'round' }, nd);
          E('circle', { cx: x, cy: gy, r: gr * 0.12, fill: C.navy }, g);
          nd.style.transformBox = 'view-box'; nd.style.transformOrigin = x + 'px ' + gy + 'px'; nd.style.transition = 'transform 1.4s cubic-bezier(.3,1.25,.5,1)';
          V.needle = nd; V.gaugeAt = [x, gy - gr - base * 1.3];
          text(g, x, gy - gr - base * 0.45, s.names && s.names.gauge || 'Pressure', base * 0.82, { wt: 800 });
          nm = '';
        } else if (p === 'valve') {
          var vw = pr * 1.6, vh = pr * 1.4;
          E('path', { d: 'M' + (x - vw) + ' ' + (yLow - vh) + ' L' + x + ' ' + yLow + ' L' + (x - vw) + ' ' + (yLow + vh) + ' Z M' + (x + vw) + ' ' + (yLow - vh) + ' L' + x + ' ' + yLow + ' L' + (x + vw) + ' ' + (yLow + vh) + ' Z', fill: tone(s.tone || 'slate'), stroke: C.navy, 'stroke-width': 3, 'stroke-linejoin': 'round' }, g);
          var gate = E('g', { 'class': 'tr' }, g);
          E('path', { d: 'M' + x + ' ' + (yLow - pr * 3.1) + ' V' + (yLow - pr * 0.6), stroke: C.navy, 'stroke-width': 5 }, gate);
          E('ellipse', { cx: x, cy: yLow - pr * 3.1, rx: pr * 1.3, ry: pr * 0.4, fill: 'none', stroke: C.warn, 'stroke-width': 6 }, gate);
          E('rect', { x: x - pr * 0.32, y: yLow - pr * 0.62, width: pr * 0.64, height: pr * 1.24, rx: 3, fill: C.navy }, gate);
          V.gate = gate; V.gateUp = pr * 1.5;
          nm = s.names && s.names.valve || 'Valve';
          V.valveState = pill(svg, x, stateY, 'Shut', base * 0.7, C.ghost, C.navy);
          V.valveAt = [x, yLow - pr * 3.1 - base * 1.1];
        }
        if (nm) { var lf = fit(nm, base * 0.9, base * 0.72, slot * 0.94, 2, 800); text(svg, x, labY - (lf.lines.length - 1) * lf.size * 0.5, lf.lines, lf.size, { wt: 800 }); }
      });
      var tagG = E('g', null, svg);
      return {
        show: function (st, fwd) {
          tagG.innerHTML = '';
          liqA.style.transform = 'scaleY(' + st.a.toFixed(3) + ')'; liqB.style.transform = 'scaleY(' + st.b.toFixed(3) + ')';
          if (V.spin) { if (st.pump) V.spin.play(); else V.spin.pause(); }
          if (flowA) { if (st.flow) flowA.play(); else flowA.pause(); }
          streak.style.opacity = st.flow ? 1 : 0;
          if (V.needle) V.needle.style.transform = 'rotate(' + (-120 + 240 * st.p).toFixed(1) + 'deg)';
          if (V.gate) V.gate.style.transform = 'translateY(' + (st.valve ? -V.gateUp : 0) + 'px)';
          if (V.pumpState) { setText(V.pumpState.t.firstChild ? V.pumpState.t : V.pumpState.t, st.pump ? 'Running' : 'Stopped'); V.pumpState.querySelector('rect').setAttribute('fill', st.pump ? '#CDEBDC' : C.ghost); }
          if (V.valveState) { setText(V.valveState.t, st.valve ? 'Open' : 'Shut'); V.valveState.querySelector('rect').setAttribute('fill', st.valve ? '#CDEBDC' : '#F6D3CC'); }
          var at = { pump: V.pumpAt, gauge: V.gaugeAt, valve: V.valveAt };
          Object.keys(st.tag).forEach(function (k) {
            if (!at[k]) return;
            var tsz = base * 0.84, tgw = tw(st.tag[k], tsz, 800) + tsz * 1.2, ty = pad + tsz * 0.9, tx = clamp(at[k][0], tgw / 2 + 4, W - tgw / 2 - 4);
            E('path', { d: 'M' + at[k][0].toFixed(1) + ' ' + (ty + tsz * 0.8).toFixed(1) + ' V' + at[k][1].toFixed(1), stroke: C.amber, 'stroke-width': 3, 'stroke-dasharray': '5 5' }, tagG);
            var pg = pill(tagG, tx, ty, st.tag[k], tsz, C.amber, C.amberInk, 'tz');
            scaleShow(pg, false); setTimeout(function () { scaleShow(pg, true); }, fwd ? 500 : 0);
          });
        },
        stop: function () { if (V.spin) V.spin.pause(); if (flowA) flowA.pause(); }
      };
    }
  };

  SCENES.crossing = {
    check: function (s) {
      var P = [];
      checkName(P, 'own', s.own && s.own.name); checkName(P, 'other', s.other && s.other.name);
      (s.steps || []).forEach(function (x, i) { if (['start', 'bearing', 'lights', 'alter'].indexOf(x.show || 'start') < 0) P.push('step ' + (i + 1) + ': crossing shows start, bearing, lights or alter'); });
      return P;
    },
    state: function (s, n) { var ph = { start: 0, bearing: 1, lights: 2, alter: 3 }, st = { ph: 0 }; for (var i = 0; i <= n && i < s.steps.length; i++) st.ph = Math.max(st.ph, ph[s.steps[i].show || 'start']); return st; },
    build: function (cx, s) {
      var W = cx.W, H = cx.H, base = cx.base, svg = cx.svg, pad = base * 0.6;
      E('rect', { x: 0, y: 0, width: W, height: H, rx: base * 0.5, fill: C.sea, 'data-no-contain': '' }, svg);
      fills(svg, pad, pad, W - 2 * pad, H - 2 * pad);
      for (var k = 1; k < 6; k++) E('path', { d: 'M' + (W * 0.05) + ' ' + (H * k / 6) + ' q' + W * 0.04 + ' -6 ' + W * 0.08 + ' 0', stroke: C.seaLine, 'stroke-width': 3, fill: 'none' }, svg);
      var nx = W - pad - base * 1.2, ny = pad + base * 2;
      E('path', { d: 'M' + nx + ' ' + (ny - base * 1.3) + ' l' + base * 0.55 + ' ' + base * 1.5 + ' l-' + base * 0.55 + ' -' + base * 0.4 + ' l-' + base * 0.55 + ' ' + base * 0.4 + ' z', fill: C.navy }, svg);
      text(svg, nx, ny + base * 1.1, 'N', base * 0.85, { wt: 900, fill: C.navy });
      var Px = W * 0.4, Py = H * 0.32, D = Math.min(W * 0.42, H * 0.45), Ls = Math.min(W, H) * 0.135, bm = Ls * 0.36;
      function own(t) { return [Px, Py + D * (1 - t)]; }
      function oth(t) { return [Px + D * (1 - t), Py]; }
      var man = [], N2 = 140, u0 = 0.42, u1 = 1.22, hp = [Px, Py + D * (1 - u0)], hd = 0;
      for (var i = 0; i <= N2; i++) {
        var u = u0 + (u1 - u0) * i / N2;
        if (i) { var dt = (u1 - u0) / N2; hd = Math.min(70, hd + 70 * dt / 0.1); var a = hd * Math.PI / 180; hp = [hp[0] + Math.sin(a) * D * dt, hp[1] - Math.cos(a) * D * dt]; }
        man.push({ o: hp.slice(), h: hd, t: oth(u) });
      }
      var gTrail = E('g', null, svg), gSect = E('g', { 'class': 'tc' }, svg), gBear = E('g', null, svg), gShips = E('g', null, svg), gTag = E('g', null, svg);
      var trail = E('path', { d: '', fill: 'none', stroke: tone('blue'), 'stroke-width': 4, 'stroke-dasharray': '10 9', 'stroke-linecap': 'round' }, gTrail);
      function ship(tn, nm) {
        var g = E('g', null, gShips), body = E('g', null, g);
        E('path', { d: 'M0 ' + (-Ls / 2) + ' C' + bm * 0.75 + ' ' + (-Ls * 0.3) + ' ' + bm / 2 + ' ' + (-Ls * 0.1) + ' ' + bm / 2 + ' 0 V' + Ls / 2 + ' H' + (-bm / 2) + ' V0 C' + (-bm / 2) + ' ' + (-Ls * 0.1) + ' ' + (-bm * 0.75) + ' ' + (-Ls * 0.3) + ' 0 ' + (-Ls / 2) + ' Z', fill: tn, stroke: C.navy, 'stroke-width': 3 }, body);
        E('rect', { x: -bm * 0.32, y: Ls * 0.18, width: bm * 0.64, height: Ls * 0.22, rx: 2, fill: C.white }, body);
        E('circle', { cx: -bm / 2, cy: -Ls * 0.02, r: bm * 0.16, fill: '#E0312B', stroke: C.white, 'stroke-width': 1.5 }, body);
        E('circle', { cx: bm / 2, cy: -Ls * 0.02, r: bm * 0.16, fill: '#20B24A', stroke: C.white, 'stroke-width': 1.5 }, body);
        var lab = text(g, 0, 0, nm, base * 0.85, { wt: 800 });
        return { g: g, body: body, lab: lab };
      }
      var A = ship(tone('blue'), s.own.name), B = ship(tone('slate'), s.other.name);
      function put(sh, p, h, lx, ly) { sh.body.setAttribute('transform', 'translate(' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ') rotate(' + h.toFixed(1) + ')'); sh.lab.setAttribute('x', (p[0] + lx).toFixed(1)); sh.lab.setAttribute('y', (p[1] + ly).toFixed(1)); sh.lab.querySelector('tspan').setAttribute('x', (p[0] + lx).toFixed(1)); sh.p = p; }
      function wedge(c, h, a1, a2, r, col) { var f = function (a) { a = (h + a - 90) * Math.PI / 180; return (c[0] + r * Math.cos(a)).toFixed(1) + ' ' + (c[1] + r * Math.sin(a)).toFixed(1); }; return E('path', { d: 'M' + c[0].toFixed(1) + ' ' + c[1].toFixed(1) + ' L' + f(a1) + ' A' + r + ' ' + r + ' 0 0 1 ' + f(a2) + ' Z', fill: col, opacity: 0.3 }, gSect); }
      var tags = [], run = null, curPh = null;
      function pose(ph, k) {
        if (ph < 3) { var t = ph >= 1 ? u0 * (ph === 1 ? k : 1) : 0; put(A, own(t), 0, 0, Ls * 0.5 + base * 1.1); put(B, oth(t), 270, 0, -Ls * 0.5 - base * 0.4); trail.setAttribute('d', ''); return t; }
        var j = Math.round(k * N2), m = man[j]; put(A, m.o, m.h, 0, Ls * 0.5 + base * 1.1); put(B, m.t, 270, 0, -Ls * 0.5 - base * 0.4);
        trail.setAttribute('d', 'M' + own(u0).map(function (v) { return v.toFixed(1); }).join(' ') + man.slice(0, j + 1).filter(function (q, ii) { return ii % 4 === 0 || ii === j; }).map(function (q) { return ' L' + q.o[0].toFixed(1) + ' ' + q.o[1].toFixed(1); }).join(''));
      }
      function bearings(upto) {
        gBear.innerHTML = '';
        [0, 0.14, 0.28, 0.42].forEach(function (t, i) {
          if (t > upto + 1e-6) return;
          var a = own(t), b = oth(t), fade = 0.35 + 0.65 * (t / 0.42);
          E('path', { d: 'M' + a[0] + ' ' + a[1] + ' L' + b[0] + ' ' + b[1], stroke: C.navy, 'stroke-width': 4.5, 'stroke-dasharray': '14 8', opacity: fade }, gBear);
          if (t < 0.42) { E('circle', { cx: a[0], cy: a[1], r: bm * 0.5, fill: tone('blue'), opacity: 0.35 }, gBear); E('circle', { cx: b[0], cy: b[1], r: bm * 0.5, fill: tone('slate'), opacity: 0.35 }, gBear); }
        });
      }
      function tag(x, y, s2, bg, fg, delay) { var pg = pill(gTag, clamp(x, base * 5, W - base * 5), clamp(y, base, H - base), s2, base * 0.86, bg, fg, 'tz'); scaleShow(pg, false); tags.push(setTimeout(function () { scaleShow(pg, true); }, delay)); }
      return {
        show: function (st, fwd) {
          if (run) run.stop(); tags.forEach(clearTimeout); tags = []; gTag.innerHTML = ''; gSect.innerHTML = '';
          var ph = st.ph, anim = fwd && curPh != null && ph === curPh + 1 && (ph === 1 || ph === 3);
          curPh = ph;
          if (ph < 1) bearings(-1);
          run = tween(anim ? (ph === 1 ? 2600 : 3200) : 0, function (k) { var t = pose(ph, k); if (ph === 1) bearings(t); }, function () {
            if (ph >= 1) bearings(0.42);
            if (ph === 1) { var a = own(0.28), b = oth(0.28); tag((a[0] + b[0]) / 2 + base * 5.5, (a[1] + b[1]) / 2 + base * 0.6, s.say_bearing || 'Bearing steady', C.amber, C.amberInk, 0); }
            if (ph === 2) {
              wedge(B.p, 270, -112.5, 0, Ls * 2.4, '#E0312B'); wedge(A.p, 0, 0, 112.5, Ls * 2.4, '#20B24A');
              tag(A.p[0] - base * 0.4, A.p[1] + Ls * 0.5 + base * 2.7, s.say_own || 'Give way', C.amber, C.amberInk, fwd ? 400 : 0);
              tag(B.p[0], B.p[1] - Ls * 0.5 - base * 1.9, s.say_other || 'Stand on', C.navy, C.white, fwd ? 700 : 0);
            }
            if (ph === 3) {
              tag(A.p[0], A.p[1] + Ls * 0.5 + base * 2.7, s.say_alter || 'Pass astern', C.amber, C.amberInk, 0);
              tag(B.p[0], B.p[1] - Ls * 0.5 - base * 1.9, s.say_other || 'Stand on', C.navy, C.white, 0);
            }
          });
        },
        stop: function () { if (run) run.stop(); tags.forEach(clearTimeout); }
      };
    }
  };

  var FORMS = { path: PATH, zones: ZONES, steps: STEPS, options: OPTIONS, amounts: AMOUNTS };
  function formOf(spec) { return spec.form === 'scene' ? SCENES[spec.scene] : FORMS[spec.form]; }

  function check(spec) {
    var f = formOf(spec);
    if (!f) return ['no form "' + spec.form + (spec.scene ? ':' + spec.scene : '') + '"'];
    var P = [];
    if (!spec.say) P.push('"say": the one point this figure makes, in one sentence');
    if (!spec.steps || !spec.steps.length) P.push('a figure needs at least its arrival step');
    return P.concat(f.check(spec));
  }

  var figures = [];
  function mount(host, spec) {
    var f = formOf(spec);
    if (!f) throw new Error('no form "' + spec.form + (spec.scene ? ':' + spec.scene : '') + '"');
    var fig = { n: 0, spec: spec, count: (spec.steps || []).length, host: host }, view = null, lastW = 0, lastH = 0;
    figures.push(fig);
    host.classList.add('n2');
    function build() {
      var W = Math.round(host.clientWidth), H = Math.round(host.clientHeight);
      if (W < 40 || H < 40) return;
      if (W === lastW && H === lastH && view) return;
      lastW = W; lastH = H;
      if (view && view.stop) view.stop();
      host.innerHTML = '';
      var svg = E('svg', { viewBox: '0 0 ' + W + ' ' + H, width: W, height: H, role: 'img', 'aria-label': spec.say || '' });
      host.appendChild(svg);
      view = f.build({ W: W, H: H, base: typeSize(W, H), svg: svg }, spec);
      view.show(f.state(spec, fig.n), false);
    }
    fig.go = function (n, still) {
      n = clamp(n, 0, fig.count - 1);
      var fwd = n > fig.n && !still; fig.n = n;
      settleAt = Math.max(settleAt, performance.now() + (still || REDUCED ? 0 : 1600));
      if (view) view.show(f.state(spec, n), fwd);
      if (fig.onstep) fig.onstep(n);
    };
    fig.next = function () { if (fig.n < fig.count - 1) { fig.go(fig.n + 1); return true; } return false; };
    fig.prev = function () { if (fig.n > 0) { fig.go(fig.n - 1); return true; } return false; };
    fig.relayout = function () { lastW = 0; build(); };
    fig.idle = function () { return running === 0 && performance.now() >= settleAt; };
    if (window.ResizeObserver) new ResizeObserver(function () { build(); }).observe(host);
    build();
    return fig;
  }

  /* every word on the figure as it stands now: none over another, none cut by the figure's edge. The words inside a
     thing's picture (a gauge's digits) are part of the picture and left out. -> findings in plain words */
  function audit(fig) {
    var svg = fig.host.querySelector('svg'), found = [];
    if (!svg) return found;
    var sr = svg.getBoundingClientRect();
    function seen(e) { var o = 1; for (var x = e; x && x !== svg; x = x.parentNode) { var cs = getComputedStyle(x); if (cs.display === 'none' || cs.visibility === 'hidden') return 0; o *= +cs.opacity; if (/^matrix\(0,/.test(cs.transform)) return 0; } return o; }
    var T = [].filter.call(svg.querySelectorAll('text'), function (t) { return t.textContent.trim() && !t.closest('.n2-pic') && seen(t) > 0.5; })
      .map(function (t) { var r = t.getBoundingClientRect(), ih = r.height * 0.18; return { t: t, w: t.textContent.trim().slice(0, 30), x: r.left, y: r.top + ih, x2: r.right, y2: r.bottom - ih }; });
    T.forEach(function (a, i) {
      if (a.x < sr.left - 1 || a.y < sr.top - 1 || a.x2 > sr.right + 1 || a.y2 > sr.bottom + 1) found.push('words cut at the edge: "' + a.w + '"');
      for (var j = i + 1; j < T.length; j++) {
        var b = T[j], w = Math.min(a.x2, b.x2) - Math.max(a.x, b.x), h = Math.min(a.y2, b.y2) - Math.max(a.y, b.y);
        if (w > 2 && h > 2) found.push('words over words: "' + a.w + '" and "' + b.w + '"');
      }
    });
    return found;
  }

  /* in a deck: the slide's Next and Back walk the steps, and a step lights the slide's line it names */
  function hook(id, fns) {
    var H = window.GB_HOOKS = window.GB_HOOKS || {}, old = H[id] || {}, cur = {};
    cur.enter = function () { if (old.enter) old.enter.apply(this, arguments); fns.enter(); };
    cur.leave = function () { if (old.leave) old.leave.apply(this, arguments); if (fns.leave) fns.leave(); };
    cur.step = function (dir) {
      var mine = function () { return !!fns.step(dir); }, theirs = function () { return !!(old.step && old.step(dir)); };
      if (fns.first) return dir > 0 ? (mine() || theirs()) : (theirs() || mine());
      return theirs() || mine();
    };
    H[id] = cur;
  }
  function deck(fig, slide) {
    fig.onstep = function (n) {
      [].forEach.call(slide.querySelectorAll('[data-i]'), function (x) { x.classList.remove('cur', 'lit'); });
      for (var i = 0; i <= n; i++) {
        [].concat(fig.spec.steps[i].line == null ? [] : fig.spec.steps[i].line).forEach(function (k) {
          var line = slide.querySelector('[data-i="' + k + '"]'); if (line) line.classList.add(i === n ? 'cur' : 'lit');
        });
      }
    };
    hook(slide.id, {
      first: !!slide.querySelector('.lt-why, .lt-opts'),       /* a true / false or a scenario walks the drawing before its answer */
      enter: function () { fig.relayout(); fig.go(0, true); },
      step: function (dir) {
        if (dir > 0 && fig.n < fig.count - 1) { fig.next(); return true; }
        if (dir < 0 && fig.n > 0) { fig.prev(); return true; }
        return false;
      }
    });
  }
  function auto() {
    [].forEach.call(document.querySelectorAll('[data-n2d]'), function (host) {
      if (host.__n2) return;
      var ref = host.getAttribute('data-n2d'), node = ref.charAt(0) === '#' ? document.getElementById(ref.slice(1)) : null, spec;
      try { spec = JSON.parse(node ? node.textContent : ref); } catch (e) { spec = null; }
      if (!spec) { host.__n2 = 'bad'; return; }
      try { host.__n2 = mount(host, spec); }
      catch (err) { host.__n2 = 'bad'; host.textContent = 'This figure could not be drawn: ' + (err.message || err); return; }
      var slide = host.closest('.slide');
      if (slide && slide.id) deck(host.__n2, slide);
    });
  }

  window.N2D = { mount: mount, check: check, audit: audit, figures: figures, forms: Object.keys(FORMS), scenes: Object.keys(SCENES), tones: TONES, limits: LIMIT };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto); else setTimeout(auto, 0);
})();
