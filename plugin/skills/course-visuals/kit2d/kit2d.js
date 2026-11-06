/* kit2d.js - the 2D kit: a teaching figure drawn from a short JSON spec (*.kit2d.json), plain SVG and ES5, no library.
   A spec names its state (numbers), its parts, its steps and the controls a trainee may try. The kit does the rest:
     - state eases towards its targets every frame; steps, sliders, toggles and drags all write the same targets,
       so nothing jumps and nothing fights;
     - depth from layers: an outline, a body lit from the top left, a hatched cut wall, its contents, a glow behind the
       hero and one soft shadow under it - gradients only, never a filter (smooth on the tablet);
     - words beside the drawing with a halo and a leader, placed clear of each other and of the solids;
     - type that grows so no word is drawn under 12.5 px on screen;
     - draws only while something moves; steps walked by the deck's Next / Back (GB_HOOKS step) or its own bar.
   A part's value can be a number, "@name" (a state) or "id.key" (what another part computes).
   SPEC.md is the reference. */
(function (w) {
  'use strict';
  var d = w.document, NS = 'http://www.w3.org/2000/svg', UID = 0, TYPES = {}, figs = [];
  var reduce = false;
  try { reduce = !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e0) { reduce = false; }

  /* ------------------------------------------------------------------------------------------------ helpers */
  function el(tag, attrs, parent, text) {
    var n = d.createElementNS(NS, tag), k;
    for (k in attrs) { if (attrs[k] != null) { n.setAttribute(k, attrs[k]); } }
    if (text != null) { n.textContent = text; }
    if (parent) { parent.appendChild(n); }
    return n;
  }
  function now() { return (w.performance && w.performance.now) ? w.performance.now() : +new Date(); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function approach(cur, target, dt, rate) { return cur + (target - cur) * (1 - Math.exp(-dt * rate)); }
  function num(v, dec) {
    var s = Math.abs(v).toFixed(dec == null ? 0 : dec);
    return (v < 0 && +s !== 0 ? '−' : '') + s;
  }
  /* "{v} jobs", "{y} t/day" - the braces read from vals, each to its decimals */
  function tpl(s, vals, dec) {
    return String(s == null ? '' : s).replace(/\{(\w+)\}/g, function (m, k) {
      return vals[k] == null ? '' : (typeof vals[k] === 'number' ? num(vals[k], dec) : vals[k]);
    });
  }
  function pt(p) { return p[0].toFixed(1) + ' ' + p[1].toFixed(1); }
  function poly(ps, close) { return ps.map(function (p, i) { return (i ? 'L' : 'M') + pt(p); }).join(' ') + (close ? ' Z' : ''); }
  function Spring(x) { this.x = x; this.v = 0; }
  Spring.prototype.go = function (to, dt, snap) {
    if (snap || reduce) { this.x = to; this.v = 0; return false; }
    var a = 120 * (to - this.x) - 13 * this.v;
    this.v += a * dt; this.x += this.v * dt;
    if (Math.abs(to - this.x) < 0.02 && Math.abs(this.v) < 0.05) { this.x = to; this.v = 0; return false; }
    return true;
  };
  function Roller(parent, attrs) {
    this.a = el('text', attrs, parent); this.b = el('text', attrs, parent);
  }
  Roller.prototype.set = function (v, fmt, dec) {
    if (dec) { this.a.textContent = tpl(fmt, { v: v }, dec); this.b.textContent = ''; this.a.removeAttribute('transform'); this.a.removeAttribute('opacity'); return; }
    var lo = Math.floor(v + 1e-6), fr = v - lo, e = fr * fr * (3 - 2 * fr);
    this.a.textContent = tpl(fmt, { v: lo }, 0); this.b.textContent = fr > 0.001 ? tpl(fmt, { v: lo + 1 }, 0) : '';
    this.a.setAttribute('transform', 'translate(0 ' + (-18 * e).toFixed(1) + ')'); setOp(this.a, 1 - e);
    this.b.setAttribute('transform', 'translate(0 ' + (18 * (1 - e)).toFixed(1) + ')'); setOp(this.b, e);
  };
  function setOp(n, v) { n.setAttribute('opacity', clamp(v, 0, 1).toFixed(3)); }
  function textLines(parent, attrs, rows) {
    var t = el('text', attrs, parent);
    rows.forEach(function (r, i) {
      el('tspan', { x: attrs.x || 0, dy: i ? '1.25em' : 0, 'class': r.cls || null }, t, r.text);
    });
    return t;
  }
  function stops(grad, list) {
    list.forEach(function (s) { el('stop', { offset: s[0], 'class': s[1], 'stop-opacity': s[2] == null ? null : s[2] }, grad); });
    return grad;
  }

  /* ------------------------------------------------------------------------------------------------ a figure */
  function Fig(host, spec) {
    var f = this;
    f.spec = spec; f.host = host; f.id = 'k2-' + (++UID);
    f.W = (spec.size || [960, 540])[0]; f.H = (spec.size || [960, 540])[1];
    f.T = {}; f.S = {}; f.V = {}; f.fx = []; f.pending = []; f.out = {}; f.parts = []; f.byId = {}; f.labels = []; f.solids = []; f.rate = spec.rates || {};
    f.step = 0; f.steps = [{ title: spec.idle || '' }].concat(spec.steps || []);
    var k;
    for (k in (spec.state || {})) { f.T[k] = f.S[k] = +spec.state[k]; }
    f.build();
    (spec.parts || []).forEach(function (p) {
      var make = TYPES[p.type];
      if (!make) { throw new Error('kit2d: no part "' + p.type + '"'); }
      var inst = make(f, p) || {};
      inst.p = p; f.parts.push(inst);
      if (p.id) { f.byId[p.id] = inst; }
    });
    f.side(); f.bar();
    f.goStep(0, true);
    f.resize();
    if (w.ResizeObserver) { new w.ResizeObserver(function () { f.resize(); }).observe(f.stage); }
    else { w.addEventListener('resize', function () { f.resize(); }); }
  }
  Fig.prototype = {
    build: function () {
      var f = this, h = f.host, light = f.spec.theme === 'light' || (f.spec.theme !== 'dark' && lightBehind(h));
      h.innerHTML = '';
      f.root = d.createElement('div'); f.root.className = 'k2' + (light ? ' k2-light' : '');
      f.main = d.createElement('div'); f.main.className = 'k2-main';
      f.stage = d.createElement('div'); f.stage.className = 'k2-stage';
      f.root.appendChild(f.main); f.main.appendChild(f.stage); h.appendChild(f.root);
      f.svg = el('svg', { viewBox: '0 0 ' + f.W + ' ' + f.H, role: 'img', 'aria-label': f.spec.label || '', preserveAspectRatio: 'xMidYMid meet' }, f.stage);
      f.defs = el('defs', {}, f.svg);
      f.L = {};
      ['bg', 'back', 'contents', 'fx', 'hero', 'front', 'lbl'].forEach(function (n) { f.L[n] = el('g', { 'class': 'k2-l-' + n }, f.svg); });
      f.paints();
      if (f.spec.glow !== false) {                  /* a soft light behind the hero: the eye goes there first */
        var gw = f.spec.glow || {};
        el('ellipse', { cx: gw.x != null ? gw.x : f.W / 2, cy: gw.y != null ? gw.y : f.H * 0.48, rx: gw.rx || f.W * 0.42, ry: gw.ry || f.H * 0.45,
          fill: 'url(#' + f.id + '-glow)' }, f.L.bg);
      }
    },
    /* the paint servers every part shares: metal lit from the top left, the cut wall's hatching, a liquid, the glow,
       the soft shadow, a fill in each category colour */
    paints: function () {
      var f = this, D = f.defs, id = f.id;
      stops(el('linearGradient', { id: id + '-metal', x1: 0, y1: 0, x2: 1, y2: 1 }, D), [[0, 'k2-s-metal-hi'], [0.45, 'k2-s-metal-mid'], [1, 'k2-s-metal-lo']]);
      stops(el('linearGradient', { id: id + '-metalv', x1: 0, y1: 0, x2: 0, y2: 1 }, D), [[0, 'k2-s-metal-hi'], [0.5, 'k2-s-metal-mid'], [1, 'k2-s-metal-lo']]);
      var hp = el('pattern', { id: id + '-hatch', width: 9, height: 9, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' }, D);
      el('line', { x1: 0, y1: 0, x2: 0, y2: 9, 'class': 'k2-hatch-line' }, hp);
      stops(el('radialGradient', { id: id + '-liquid', cx: 0.5, cy: 0.3, r: 0.85 }, D), [[0, 'k2-s-liq-hi'], [1, 'k2-s-liq-lo']]);
      stops(el('radialGradient', { id: id + '-glow' }, D), [[0, 'k2-s-glow'], [1, 'k2-s-glow0']]);
      stops(el('radialGradient', { id: id + '-shadow' }, D), [[0, 'k2-s-shadow'], [1, 'k2-s-shadow0']]);
      ['blue', 'amber', 'good', 'cat-1', 'cat-2', 'cat-3', 'cat-4', 'cat-5'].forEach(function (c) {
        stops(el('linearGradient', { id: id + '-fill-' + c, x1: 0, y1: 0, x2: 0, y2: 1 }, D),
          [[0, 'k2-s-' + c, 0.5], [0.6, 'k2-s-' + c, 0.2], [1, 'k2-s-' + c, 0.06]]);
        stops(el('linearGradient', { id: id + '-solid-' + c, x1: 0, y1: 0, x2: 0.35, y2: 1 }, D), [[0, 'k2-s-' + c, 1], [1, 'k2-s-' + c, 0.62]]);
      });
    },
    url: function (name) { return 'url(#' + this.id + '-' + name + ')'; },
    /* a paint server of the figure's own: a vertical gradient across a band y0..y1 (a horizontal pipe's wall or bore -
       a box gradient does not paint a straight stroke, whose box has no height) */
    band: function (kind, y0, y1) {
      var id = this.id + '-b' + (++UID), g = el('linearGradient', { id: id, gradientUnits: 'userSpaceOnUse', x1: 0, y1: y0, x2: 0, y2: y1 }, this.defs);
      stops(g, kind === 'liquid' ? [[0, 'k2-s-liq-hi'], [1, 'k2-s-liq-lo']] : [[0, 'k2-s-metal-hi'], [0.5, 'k2-s-metal-mid'], [1, 'k2-s-metal-lo']]);
      return 'url(#' + id + ')';
    },
    /* one soft shadow under a solid: a fill that fades, never a blur */
    shadow: function (cx, cy, rx, ry) { return el('ellipse', { cx: cx, cy: cy, rx: rx, ry: ry, fill: this.url('shadow') }, this.L.bg); },

    /* ---- values */
    get: function (ref, dflt) {
      if (ref == null) { return dflt; }
      if (typeof ref === 'number') { return ref; }
      var s = String(ref);
      if (s.charAt(0) === '@') { var v = this.S[s.slice(1)]; return v == null ? dflt : v; }
      var i = s.indexOf('.');
      if (i > 0) { var o = this.out[s.slice(0, i)]; return o && o[s.slice(i + 1)] != null ? o[s.slice(i + 1)] : dflt; }
      return isNaN(+s) ? dflt : +s;
    },
    rest: function (ref, dflt) {                        /* the value at step 0 - a ghost of where things started */
      if (typeof ref === 'string' && ref.charAt(0) === '@') { var v = (this.spec.state || {})[ref.slice(1)]; return v == null ? dflt : +v; }
      return this.get(ref, dflt);
    },
    target: function (ref, dflt) {                      /* where a value is going - a part that springs aims there */
      if (typeof ref === 'string' && ref.charAt(0) === '@') {
        var k = ref.slice(1), v = this.T[k];
        (this.pending || []).forEach(function (q) { if (q.k === k) { v = q.v; } });
        return v == null ? dflt : v;
      }
      return this.get(ref, dflt);
    },
    /* a ring that grows from a point and fades, once, where something has just changed (never a loop) */
    pulse: function (x, y, o) {
      o = o || {};
      if (reduce) { return; }
      var c = el('circle', { cx: x, cy: y, r: 0, 'class': 'k2-pulse' + (o.tone ? ' k2-pulse-' + o.tone : '') }, this.L.lbl), R = o.r || 46;
      this.L.lbl.insertBefore(c, this.L.lbl.firstChild);
      this.fx.push({ t0: now() + (o.delay || 0), ms: o.ms || 750,
        go: function (k) { var e = 1 - Math.pow(1 - k, 3); c.setAttribute('r', (R * e).toFixed(1)); setOp(c, 0.9 * (1 - k)); },
        done: function () { if (c.parentNode) { c.parentNode.removeChild(c); } } });
      this.kick();
    },
    publish: function (id, key, v) { (this.out[id] = this.out[id] || {})[key] = v; },
    setT: function (name, v, now0) { this.T[name] = v; if (now0) { this.S[name] = v; } this.kick(); },

    /* ---- steps: step n starts from the end of step n-1, and is the spec's state with every set up to n */
    targets: function (n) {
      var T = {}, k, i;
      for (k in (this.spec.state || {})) { T[k] = +this.spec.state[k]; }
      for (i = 1; i <= n; i++) { for (k in (this.steps[i].set || {})) { T[k] = +this.steps[i].set[k]; } }
      return T;
    },
    /* a step's "after": {"strain": 350} - that state starts moving 350 ms later, so a step tells its story in order
       (the corner moves, then the strain shows) */
    goStep: function (n, instant) {
      var f = this, T = f.targets(n), k, after = (!instant && !reduce && f.steps[n].after) || {}, t = now();
      f.step = n; f.pending = [];
      for (k in T) {
        if (after[k] && T[k] !== f.T[k]) { f.pending.push({ k: k, v: T[k], at: t + after[k] }); continue; }
        f.T[k] = T[k]; if (instant || reduce) { f.S[k] = T[k]; }
      }
      f.parts.forEach(function (q) { if (q.onStep) { q.onStep(n, instant || reduce); } });
      f.syncControls();
      if (f.onStep) { f.onStep(n); }
      f.showBar();
      f.relayout = true;
      f.kick();
      if (instant) { f.frame(true); }
    },
    next: function () { if (this.step < this.steps.length - 1) { this.goStep(this.step + 1); } },
    prev: function () { if (this.step > 0) { this.goStep(this.step - 1); } },
    replay: function () { if (this.step > 0) { this.goStep(this.step - 1, true); this.goStep(this.step + 1); } },

    /* ---- the frame loop: draws only while something moves */
    kick: function () {
      var f = this;
      if (f.raf || f.hidden) { return; }
      f.t0 = now();
      f.raf = w.requestAnimationFrame(function tick() {
        var t = now(), dt = Math.min(0.05, (t - f.t0) / 1000);
        f.t0 = t;
        var busy = f.frame(false, dt);
        f.raf = (busy && !f.hidden) ? w.requestAnimationFrame(tick) : 0;
      });
    },
    frame: function (instant, dt) {
      var f = this, busy = false, k, t = now();
      dt = dt || 0;
      f.pending = (f.pending || []).filter(function (q) { if (t >= q.at || instant) { f.T[q.k] = q.v; f.syncControls(); return false; } busy = true; return true; });
      for (k in f.T) {
        if (f.S[k] == null || instant || reduce) { f.S[k] = f.T[k]; f.V[k] = 0; continue; }
        var om = f.rate[k] || 7, x = f.S[k], v = f.V[k] || 0, to = f.T[k], eps = 1e-4 * (1 + Math.abs(to)), n2, h;
        for (n2 = 0; n2 < 2; n2++) { h = dt / 2; v += (om * om * (to - x) - 2 * om * v) * h; x += v * h; }
        if (Math.abs(to - x) < eps && Math.abs(v) < eps * om) { x = to; v = 0; } else { busy = true; }
        f.S[k] = x; f.V[k] = v;
      }
      f.parts.forEach(function (q) { if (q.calc) { q.calc(dt); } });
      f.parts.forEach(function (q) { if (q.draw) { q.draw(dt, instant || reduce); } if (q.live && q.live()) { busy = true; } });
      for (k in (f.charts || {})) { f.charts[k].clear(); }
      f.fx = (f.fx || []).filter(function (e) {           /* one-shot effects: a ring where something has just changed */
        var k2 = (t - e.t0) / e.ms;
        if (k2 < 0) { busy = true; return true; }
        if (k2 >= 1 || instant) { e.done(); return false; }
        e.go(k2); busy = true; return true;
      });
      f.readouts();
      if (f.follow(instant ? 0 : dt)) { busy = true; }
      if (!busy && f.relayout) { f.relayout = false; f.layout(); if (f.follow(0, true)) { busy = true; f.kick(); } }
      return busy;
    },
    /* nothing on its way anywhere: every state at its target, nothing waiting, no ring still growing */
    idle: function () {
      var f = this, k;
      if ((f.pending || []).length || (f.fx || []).length) { return false; }
      for (k in f.T) { if (Math.abs(f.S[k] - f.T[k]) > 1e-3 * (1 + Math.abs(f.T[k]))) { return false; } }
      return true;
    },
    show: function () { this.hidden = false; this.kick(); },
    hide: function () { this.hidden = true; if (this.raf) { w.cancelAnimationFrame(this.raf); this.raf = 0; } },

    /* ---- the 12.5 px floor: type grows by 1 / the scale the drawing is shown at */
    resize: function () {
      var f = this, r = f.stage.getBoundingClientRect();
      if (!r.width || !r.height) { return; }
      var scale = Math.min(r.width / f.W, r.height / f.H), up = Math.max(1, 12.6 / (14 * scale));
      f.svg.style.setProperty('--k2-up', up.toFixed(3));
      f.scale = scale;
      f.thinNow();
      (f.fits || []).forEach(function (fn) { fn(); });
      f.frame(true);
      f.layout();
      this.labels.forEach(function (L) { if (L.goal) { L.off = L.goal.slice(); } });
      f.follow(0);
    },

    /* ---- labels: words for a place, beside it, clear of the others and of the solids */
    label: function (o) {
      var f = this, g = el('g', { 'class': 'k2-lbl' }, f.L.lbl), L = { o: o, g: g };
      L.lead = el('path', { 'class': 'k2-lead', d: '' }, g);
      L.dot = el('circle', { 'class': 'k2-dot', r: 4 }, g);
      L.box = el('g', {}, g);
      var rows = [{ text: o.text || '', cls: o.cls || 'k2-t-lbl' }];
      if (o.sub) { rows.push({ text: o.sub, cls: 'k2-t-sub' }); }
      L.t = textLines(L.box, { x: 0, y: 0, 'class': 'k2-halo', 'text-anchor': 'start' }, rows);
      L.off = null;
      f.labels.push(L);
      return L;
    },
    solid: function (fn) { this.solids.push(fn); },
    /* a row of axis words (ticks, week numbers): when the grown type no longer fits between them, only every 2nd, 3rd or
       4th is shown - never two on top of each other. items: [{n: text element, at: position along the axis}] */
    thin: function (items, axis) { (this.thins = this.thins || []).push({ items: items, axis: axis || 'x' }); },
    thinNow: function () {
      (this.thins || []).forEach(function (T) {
        var it = T.items, i, need = 0, gap = 1e9, k;
        if (it.length < 3) { return; }
        it.forEach(function (x) { x.n.style.display = ''; });
        for (i = 0; i < it.length; i++) {
          var b = it[i].n.getBBox(); need = Math.max(need, (T.axis === 'x' ? b.width : b.height) + 10);
          if (i) { gap = Math.min(gap, Math.abs(it[i].at - it[i - 1].at)); }
        }
        for (k = 1; k < it.length && gap * k < need; k++) { /* the smallest step that fits */ }
        it.forEach(function (x, j) { x.n.style.display = j % k === 0 ? '' : 'none'; });
      });
    },
    /* a line that words keep clear of: fn returns its points; each straight piece becomes a thin box */
    line: function (fn) {
      var f = this;
      f.solids.push(function () {
        var ps = fn(), out = [], i;
        for (i = 1; i < ps.length; i++) {
          var a = ps[i - 1], b = ps[i];
          out.push({ x: Math.min(a[0], b[0]) - 5, y: Math.min(a[1], b[1]) - 5, x2: Math.max(a[0], b[0]) + 5, y2: Math.max(a[1], b[1]) + 5 });
        }
        return out;
      });
    },
    layout: function () {
      var f = this, placed = [], solids = [], i;
      for (i = 0; i < f.solids.length; i++) { solids = solids.concat(f.solids[i]()); }
      f.labels.forEach(function (L) {
        var at = L.o.at(), b = L.t.getBBox(), bw = b.width, bh = b.height, best = null, bestCost = 1e9;
        if (!bw) { return; }
        var sides = L.o.side ? [L.o.side] : [];
        sides = sides.concat(['right', 'left', 'up', 'down', 'upright', 'upleft', 'downright', 'downleft']);
        var dists = L.o.fixed ? [L.o.dist || 16] : [L.o.dist || 16, 34, 56, 84];
        dists.forEach(function (dist, di) {
          sides.forEach(function (s, si) {
            var dx = /right/.test(s) ? 1 : /left/.test(s) ? -1 : 0, dy = /up/.test(s) ? -1 : /down/.test(s) ? 1 : 0;
            var x = at[0] + dx * dist + (dx < 0 ? -bw : dx === 0 ? -bw / 2 : 0);
            var y = at[1] + dy * dist + (dy < 0 ? -bh : dy === 0 ? -bh / 2 : 0);
            var R = { x: x, y: y, x2: x + bw, y2: y + bh }, cost = di * 40 + si * 3;
            if (R.x < 6 || R.y < 6 || R.x2 > f.W - 6 || R.y2 > f.H - 6) { cost += 500; }
            placed.forEach(function (o) { if (R.x < o.x2 && o.x < R.x2 && R.y < o.y2 && o.y < R.y2) { cost += 400; } });
            solids.forEach(function (o) { if (o && R.x < o.x2 && o.x < R.x2 && R.y < o.y2 && o.y < R.y2) { cost += 200; } });
            if (cost < bestCost) { bestCost = cost; best = { R: R, dist: dist, di: di }; }
          });
          if (L.o.fixed) { return; }
        });
        L.goal = [best.R.x - at[0], best.R.y - at[1]]; if (!L.off) { L.off = L.goal.slice(); } L.far = (best.di > 0 || best.dist > 30) && L.o.lead !== false; L.bw = bw; L.bh = bh; L.by = b.y;
        placed.push({ x: best.R.x - 4, y: best.R.y - 4, x2: best.R.x2 + 4, y2: best.R.y2 + 4 });
      });
      f.follow();
    },
    follow: function (dt, keep) {
      var moving = false;
      this.labels.forEach(function (L) {
        if (!L.off) { return; }
        if (L.goal && !keep) {
          var gx = L.goal[0] - L.off[0], gy = L.goal[1] - L.off[1];
          if (Math.abs(gx) + Math.abs(gy) > 0.3 && dt && !reduce) { var k = 1 - Math.exp(-dt * 9); L.off[0] += gx * k; L.off[1] += gy * k; moving = true; }
          else { L.off[0] = L.goal[0]; L.off[1] = L.goal[1]; }
        } else if (L.goal && keep) { moving = moving || Math.abs(L.goal[0] - L.off[0]) + Math.abs(L.goal[1] - L.off[1]) > 0.3; }
        var at = L.o.at(), x = at[0] + L.off[0], y = at[1] + L.off[1];
        L.box.setAttribute('transform', 'translate(' + (x).toFixed(1) + ' ' + (y - L.by).toFixed(1) + ')');
        var show = L.o.show ? L.o.show() : 1;
        setOp(L.g, show);
        if (L.far) {
          var ex = clamp(at[0], x, x + L.bw), ey = clamp(at[1], y, y + L.bh), r0 = L.o.r || 0, dl = Math.hypot(ex - at[0], ey - at[1]) || 1;
          var st = [at[0] + (ex - at[0]) / dl * r0, at[1] + (ey - at[1]) / dl * r0];
          L.lead.setAttribute('d', 'M' + pt(st) + ' L' + pt([ex, ey]));
          L.dot.setAttribute('cx', st[0].toFixed(1)); L.dot.setAttribute('cy', st[1].toFixed(1));
          L.lead.style.display = L.dot.style.display = '';
        } else { L.lead.style.display = L.dot.style.display = 'none'; }
        if (L.o.text && L.o.live) { L.t.firstChild.textContent = L.o.live(); }
      });
      return moving;
    },

    /* ---- the side panel: controls write the same targets the steps do */
    side: function () {
      var f = this, sp = f.spec;
      if (!(sp.controls || []).length && !(sp.readouts || []).length) { return; }
      var side = d.createElement('div'); side.className = 'k2-side'; f.root.appendChild(side);
      f.ctl = [];
      (sp.controls || []).forEach(function (c) {
        var card = d.createElement('div'); card.className = 'k2-card'; side.appendChild(card);
        var head = d.createElement('div'); head.className = 'k2-card-h'; card.appendChild(head);
        var name = d.createElement('span'); name.textContent = c.label || c.state; head.appendChild(name);
        if (c.type === 'toggle') {
          var row = d.createElement('div'); row.className = 'k2-opts'; card.appendChild(row);
          var btns = (c.options || []).map(function (o) {
            var b = d.createElement('button'); b.type = 'button'; b.textContent = o[0]; row.appendChild(b);
            b.addEventListener('click', function () { f.setT(c.state, +o[1]); f.syncControls(); f.relayout = true; });
            return { b: b, v: +o[1] };
          });
          f.ctl.push({ sync: function () { btns.forEach(function (x) { x.b.classList.toggle('on', Math.abs(f.T[c.state] - x.v) < 1e-6); }); } });
        } else {
          var val = d.createElement('b'); head.appendChild(val);
          var r = d.createElement('input'); r.type = 'range'; r.className = 'k2-range';
          r.min = c.min; r.max = c.max; r.step = c.step || 'any'; r.setAttribute('aria-label', c.label || c.state); card.appendChild(r);
          r.addEventListener('input', function () { f.setT(c.state, +r.value); show(); f.relayout = true; });
          var show = function () { val.textContent = num(f.T[c.state] * (c.scale || 1), c.decimals) + (c.unit ? ' ' + c.unit : ''); };
          f.ctl.push({ sync: function () { r.value = f.T[c.state]; show(); } });
        }
      });
      if ((sp.readouts || []).length) {
        var grid = d.createElement('div'); grid.className = 'k2-reads'; side.appendChild(grid);
        f.reads = sp.readouts.map(function (o) {
          var box = d.createElement('div'); box.className = 'k2-read'; grid.appendChild(box);
          var s = d.createElement('span'); s.textContent = o.label; box.appendChild(s);
          var b = d.createElement('b'); box.appendChild(b);
          var u = d.createElement('i'); u.textContent = o.unit || ''; box.appendChild(u);
          return { o: o, b: b };
        });
      }
    },
    syncControls: function () { (this.ctl || []).forEach(function (c) { c.sync(); }); },
    readouts: function () {
      var f = this;
      (f.reads || []).forEach(function (r) { r.b.textContent = num(f.get(r.o.value, 0) * (r.o.scale || 1), r.o.decimals); });
    },

    /* ---- its own step bar, outside a deck */
    bar: function () {
      var f = this;
      if (f.spec.bar === false || f.host.closest && f.host.closest('.slide')) { return; }
      var bar = d.createElement('div'); bar.className = 'k2-bar'; f.main.appendChild(bar);
      function btn(t, fn) { var b = d.createElement('button'); b.type = 'button'; b.innerHTML = t; b.addEventListener('click', fn); bar.appendChild(b); return b; }
      f.bPrev = btn('&#8249;&nbsp; Previous step', function () { f.prev(); });
      f.dots = d.createElement('span'); f.dots.className = 'k2-dots'; bar.appendChild(f.dots);
      f.steps.forEach(function () { f.dots.appendChild(d.createElement('i')); });
      f.bNext = btn('Next step &nbsp;&#8250;', function () { f.next(); });
      f.bAgain = btn('Replay', function () { f.replay(); });
      f.title = d.createElement('span'); f.title.className = 'k2-title'; bar.appendChild(f.title);
    },
    showBar: function () {
      var f = this, n = f.step;
      if (!f.dots) { return; }
      [].forEach.call(f.dots.children, function (x, i) { x.classList.toggle('on', i === n); });
      f.bPrev.disabled = n === 0; f.bNext.disabled = n >= f.steps.length - 1; f.bAgain.disabled = n === 0;
      f.title.textContent = (n ? 'Step ' + n + ' of ' + (f.steps.length - 1) + ' · ' : '') + (f.steps[n].title || '');
    }
  };
  function lightBehind(n) {
    for (var x = n; x && x.nodeType === 1; x = x.parentNode) {
      var c = w.getComputedStyle(x).backgroundColor, m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/.exec(c || '');
      if (m && (m[4] == null || +m[4] > 0.5)) { return (0.2126 * m[1] + 0.7152 * m[2] + 0.0722 * m[3]) / 255 > 0.6; }
    }
    return false;
  }

  /* ------------------------------------------------------------------------------------------------ PARTS
     Each part: KIT2D.define(type, function (f, p) { build; return { calc(dt), draw(dt), live() } }).
     calc publishes what others read (f.publish), draw paints from f.get(...). Colours by class only. */
  function define(type, make) { TYPES[type] = make; }

  /* ===== CHARTS ============================================================================================== */
  /* chart - a plot area with its grid, axes, ticks and titles; curves, points and spans are drawn on it.
     {x, y, w, h, xaxis:{min, max, step, label, unit}, yaxis:{...}} */
  define('chart', function (f, p) {
    var X = p.xaxis || {}, Y = p.yaxis || {}, x0 = p.x, y0 = p.y, W = p.w, H = p.h;
    var C = {
      X: function (v) { return x0 + (v - X.min) / (X.max - X.min) * W; },
      Y: function (v) { return y0 + H - (v - Y.min) / (Y.max - Y.min) * H; },
      vx: function (px) { return X.min + (px - x0) / W * (X.max - X.min); },
      box: { x: x0, y: y0, w: W, h: H }, xaxis: X, yaxis: Y, tx: [], ty: [], cover: [],
      /* the tags over each axis this frame: [axis, centre, half size, how shown]; the ticks under them fade */
      clear: function () {
        [['x', C.tx], ['y', C.ty]].forEach(function (A) {
          A[1].forEach(function (t) {
            var op = 1;
            C.cover.forEach(function (c) { if (c[0] === A[0]) { op = Math.min(op, 1 - c[3] * (1 - clamp((Math.abs(t.at - c[1]) - c[2]) / 10, 0, 1))); } });
            setOp(t.n, op);
          });
        });
        C.cover = [];
      }
    };
    f.charts = f.charts || {}; f.charts[p.id] = C;
    f.thin(C.tx, 'x'); f.thin(C.ty, 'y');
    var g = el('g', {}, f.L.back), v;
    for (v = X.min; v <= X.max + 1e-9; v += X.step) {
      el('line', { x1: C.X(v), y1: y0, x2: C.X(v), y2: y0 + H, 'class': 'k2-grid' }, g);
      C.tx.push({ n: el('text', { x: C.X(v), y: y0 + H + 24, 'text-anchor': 'middle', 'class': 'k2-t-tick' }, g, num(v, X.decimals)), at: C.X(v) });
    }
    for (v = Y.min; v <= Y.max + 1e-9; v += Y.step) {
      el('line', { x1: x0, y1: C.Y(v), x2: x0 + W, y2: C.Y(v), 'class': 'k2-grid' }, g);
      C.ty.push({ n: el('text', { x: x0 - 12, y: C.Y(v) + 5, 'text-anchor': 'end', 'class': 'k2-t-tick' }, g, num(v, Y.decimals)), at: C.Y(v) });
    }
    el('path', { d: 'M' + x0 + ' ' + y0 + ' V' + (y0 + H) + ' H' + (x0 + W), 'class': 'k2-axis' }, g);
    if (X.label) { el('text', { x: x0 + W, y: y0 + H + 52, 'text-anchor': 'end', 'class': 'k2-t-axis' }, g, X.label + (X.unit ? ' (' + X.unit + ')' : '')); }
    if (Y.label) { el('text', { x: x0 - 12, y: y0 - 18, 'text-anchor': 'start', 'class': 'k2-t-axis' }, g, Y.label + (Y.unit ? ' (' + Y.unit + ')' : '')); }
    return {};
  });

  /* a curve's function - a model, never code: power a*x^n + b, poly [c0, c1, ...], exp a*e^(k*x) + b, or pts joined smoothly */
  function curveFn(p) {
    var F = p.fn;
    if (F && F.kind === 'power') { return function (x) { return (F.a || 1) * Math.pow(Math.max(0, x), F.n || 1) + (F.b || 0); }; }
    if (F && F.kind === 'poly') { return function (x) { var s = 0, i; for (i = F.c.length - 1; i >= 0; i--) { s = s * x + F.c[i]; } return s; }; }
    if (F && F.kind === 'exp') { return function (x) { return (F.a || 1) * Math.exp((F.k || 1) * x) + (F.b || 0); }; }
    var P = (p.pts || []).slice().sort(function (a, b) { return a[0] - b[0]; });
    return function (x) {                                   /* monotone cubic through the points: no overshoot */
      if (!P.length) { return 0; }
      if (x <= P[0][0]) { return P[0][1]; }
      if (x >= P[P.length - 1][0]) { return P[P.length - 1][1]; }
      var i = 1; while (P[i][0] < x) { i++; }
      var a = P[i - 1], b = P[i], t = (x - a[0]) / (b[0] - a[0]);
      var m = function (k) {
        if (k <= 0 || k >= P.length - 1) { return (P[Math.min(k + 1, P.length - 1)][1] - P[Math.max(k - 1, 0)][1]) / (P[Math.min(k + 1, P.length - 1)][0] - P[Math.max(k - 1, 0)][0]); }
        var d0 = (P[k][1] - P[k - 1][1]) / (P[k][0] - P[k - 1][0]), d1 = (P[k + 1][1] - P[k][1]) / (P[k + 1][0] - P[k][0]);
        return d0 * d1 <= 0 ? 0 : 2 / (1 / d0 + 1 / d1);
      };
      var h = b[0] - a[0], t2 = t * t, t3 = t2 * t;
      return (2 * t3 - 3 * t2 + 1) * a[1] + (t3 - 2 * t2 + t) * h * m(i - 1) + (-2 * t3 + 3 * t2) * b[1] + (t3 - t2) * h * m(i);
    };
  }

  /* curve - {on: chart, fn | pts, cat 1-5, label, draw: "@d" (0..1 drawn in), area: true} */
  define('curve', function (f, p) {
    var C = f.charts[p.on], fn = curveFn(p), X = C.xaxis, cat = p.cat || 1, ps = [], i, N = 140;
    for (i = 0; i <= N; i++) { var xv = X.min + (X.max - X.min) * i / N; ps.push([C.X(xv), C.Y(clamp(fn(xv), C.yaxis.min, C.yaxis.max))]); }
    var cid = f.id + '-clip' + (++UID), clip = el('rect', { x: C.box.x, y: C.box.y - 40, width: 0, height: C.box.h + 40 }, el('clipPath', { id: cid }, f.defs));
    var area = p.area !== false ? el('path', { d: poly(ps) + ' L' + pt([C.X(X.max), C.Y(C.yaxis.min)]) + ' L' + pt([C.X(X.min), C.Y(C.yaxis.min)]) + ' Z',
      fill: f.url('fill-cat-' + cat), 'clip-path': 'url(#' + cid + ')' }, f.L.back) : null;
    var line = el('path', { d: poly(ps), 'class': 'k2-curve k2-c-' + cat, pathLength: 1, 'stroke-dasharray': '0 1' }, f.L.hero);
    var tipGlow = el('circle', { r: 16, 'class': 'k2-tip-glow k2-f-' + cat }, f.L.hero), tip = el('circle', { r: 6.5, 'class': 'k2-tip' }, f.L.hero);
    var cum = [0]; for (i = 1; i <= N; i++) { cum.push(cum[i - 1] + Math.hypot(ps[i][0] - ps[i - 1][0], ps[i][1] - ps[i - 1][1])); }
    function along(k) {                                       /* the point a fraction k of the way along the line */
      var L0 = k * cum[N], j = 1; while (j < N && cum[j] < L0) { j++; }
      var t = (L0 - cum[j - 1]) / Math.max(1e-6, cum[j] - cum[j - 1]);
      return [lerp(ps[j - 1][0], ps[j][0], t), lerp(ps[j - 1][1], ps[j][1], t)];
    }
    var end = ps[N];
    f.line(function () { var q = [], j; for (j = 0; j <= N; j += 7) { q.push(ps[j]); } q.push(ps[N]); return q; });
    f.fns = f.fns || {}; f.fns[p.id] = { fn: fn, chart: C };
    var L = p.label ? f.label({ text: p.label, at: function () { return end; }, side: 'upleft', show: function () { return f.get(p.draw, 1) > 0.9 ? 1 : 0; } }) : null;
    return {
      draw: function () {
        var k = clamp(f.get(p.draw, 1), 0, 1), at = along(k), on = k > 0.005 && k < 0.995 ? 1 : 0;
        line.setAttribute('stroke-dasharray', k.toFixed(4) + ' 1');
        clip.setAttribute('width', Math.max(0, at[0] - C.box.x).toFixed(1));
        tip.setAttribute('cx', at[0].toFixed(1)); tip.setAttribute('cy', at[1].toFixed(1)); setOp(tip, on);
        tipGlow.setAttribute('cx', at[0].toFixed(1)); tipGlow.setAttribute('cy', at[1].toFixed(1)); setOp(tipGlow, on * 0.35);
      }
    };
  });

  /* point - a dot on a curve at x, its drop lines and its values on both axes; drag: the state it writes.
     {on: chart, curve, x: "@speed", tagx: "{x} kn", tagy: "{y} t/day", drag: "speed", show, ghost: {x, show, label}} */
  define('point', function (f, p) {
    var C = f.charts[p.on], F = f.fns[p.curve].fn, cat = p.cat || 1, g = el('g', {}, f.L.front), gg = el('g', {}, f.L.front);
    var X = C.xaxis;
    function tag(parent) {
      var t = el('g', {}, parent), r = el('rect', { rx: 8, height: 28, 'class': 'k2-tag' }, t), tx = el('text', { 'class': 'k2-t-tag', 'dominant-baseline': 'central' }, t);
      return { g: t, r: r, t: tx, w: 0, h: 28, set: function (s, x, y, anchor) {
        tx.textContent = s; var bb = tx.getBBox(), bw = bb.width + 18, h = Math.max(28, bb.height + 8);
        r.setAttribute('width', bw.toFixed(1)); r.setAttribute('height', h.toFixed(1)); tx.setAttribute('x', 9); tx.setAttribute('y', (h / 2).toFixed(1));
        this.w = bw; this.h = h;
        var ox = anchor === 'end' ? x - bw : anchor === 'middle' ? x - bw / 2 : x;
        t.setAttribute('transform', 'translate(' + ox.toFixed(1) + ' ' + (y - h / 2).toFixed(1) + ')');
      } };
    }
    var ghost = null;
    if (p.ghost) {
      ghost = { drop: el('path', { 'class': 'k2-drop' }, gg), dot: el('circle', { r: 9, 'class': 'k2-pt-ghost' }, gg), ty: tag(gg) };
    }
    var drop = el('path', { 'class': 'k2-drop' }, g), tx = tag(g), ty = tag(g);
    var dot = el('circle', { r: 10, 'class': 'k2-pt k2-c-' + cat }, g);
    var lastX = f.target(p.x, X.min), lastShow = f.target(p.show, 1), lastGhost = p.ghost ? f.target(p.ghost.show, 1) : 0;
    var self = {
      onStep: function (n, instant) {
        var x = f.target(p.x, X.min), sh = f.target(p.show, 1), gs = p.ghost ? f.target(p.ghost.show, 1) : 0;
        if (!instant && sh > 0.5 && (Math.abs(x - lastX) > 1e-6 || lastShow < 0.5)) { f.pulse(C.X(x), C.Y(F(x)), { delay: lastShow < 0.5 ? 150 : 600 }); }
        if (!instant && p.ghost && gs > 0.5 && lastGhost < 0.5) { var gx = f.get(p.ghost.x); f.pulse(C.X(gx), C.Y(F(gx)), { r: 30 }); }
        lastX = x; lastShow = sh; lastGhost = gs;
      },
      calc: function () { var x = f.get(p.x, X.min); f.publish(p.id, 'x', x); f.publish(p.id, 'y', F(x)); if (p.ghost) { f.publish(p.id, 'y0', F(f.get(p.ghost.x))); } },
      draw: function () {
        var x = f.get(p.x, X.min), y = F(x), px = C.X(x), py = C.Y(y), b = C.box;
        drop.setAttribute('d', 'M' + pt([b.x, py]) + ' H' + px.toFixed(1) + ' V' + (b.y + b.h).toFixed(1));
        dot.setAttribute('cx', px.toFixed(1)); dot.setAttribute('cy', py.toFixed(1));
        tx.set(tpl(p.tagx || '{x}', { x: x }, p.dx == null ? 0 : p.dx), px, b.y + b.h + 24, 'middle');
        ty.set(tpl(p.tagy || '{y}', { y: y }, p.dy == null ? 0 : p.dy), b.x - 8, py, 'end');
        var shw = f.get(p.show, 1);
        C.cover.push(['x', px, tx.w / 2 + 6, shw], ['y', py, ty.h / 2 + 10, shw]);
        setOp(g, f.get(p.show, 1));
        if (ghost) {
          var gx = f.get(p.ghost.x), gy = F(gx), gpx = C.X(gx), gpy = C.Y(gy);
          ghost.drop.setAttribute('d', 'M' + pt([b.x, gpy]) + ' H' + gpx.toFixed(1) + ' V' + (b.y + b.h).toFixed(1));
          ghost.dot.setAttribute('cx', gpx.toFixed(1)); ghost.dot.setAttribute('cy', gpy.toFixed(1));
          ghost.ty.set(tpl(p.tagy || '{y}', { y: gy }, p.dy == null ? 0 : p.dy), b.x - 8, gpy, 'end');
          C.cover.push(['y', gpy, ghost.ty.h / 2 + 10, f.get(p.ghost.show, 1)]);
          setOp(gg, f.get(p.ghost.show, 1));
        }
      }
    };
    if (p.drag) {                                         /* the trainee moves the point along the curve */
      var hit = el('circle', { r: 30, 'class': 'k2-hit', tabindex: 0, role: 'slider', 'aria-label': p.dragLabel || 'drag along the curve' }, f.L.front);
      var on = false;
      var move = function (e) {
        var m = f.svg.getScreenCTM(); if (!m) { return; }
        var q = f.svg.createSVGPoint(); q.x = e.clientX; q.y = e.clientY; q = q.matrixTransform(m.inverse());
        var v = clamp(C.vx(q.x), p.min != null ? p.min : X.min, p.max != null ? p.max : X.max);
        if (p.snap) { v = Math.round(v / p.snap) * p.snap; }
        f.setT(p.drag, v, true); f.syncControls(); f.relayout = true;
      };
      hit.addEventListener('pointerdown', function (e) { on = true; e.stopPropagation(); e.preventDefault(); try { hit.setPointerCapture(e.pointerId); } catch (x) { /* old WebView */ } move(e); });
      hit.addEventListener('pointermove', function (e) { if (on) { e.stopPropagation(); move(e); } });
      ['pointerup', 'pointercancel'].forEach(function (ev) { hit.addEventListener(ev, function () { on = false; }); });
      hit.addEventListener('keydown', function (e) {
        var k = { ArrowLeft: -1, ArrowRight: 1, ArrowDown: -1, ArrowUp: 1 }[e.key]; if (!k) { return; }
        e.preventDefault(); e.stopPropagation();
        f.setT(p.drag, clamp(f.T[p.drag] + k * (p.snap || X.step / 2), X.min, X.max)); f.syncControls();
      });
      var d0 = self.draw;
      self.draw = function () { d0(); var x = f.get(p.x, X.min); hit.setAttribute('cx', C.X(x).toFixed(1)); hit.setAttribute('cy', C.Y(F(x)).toFixed(1)); };
    }
    return self;
  });

  /* span - what changes between two points on a curve: a band between their heights and a bracket with the
     difference. {on, curve, from: x or "@x0", to: "@x", show, text: "{pct} % less"} */
  define('span', function (f, p) {
    var C = f.charts[p.on], F = f.fns[p.curve].fn, g = el('g', {}, f.L.back), gf = el('g', {}, f.L.front);
    var band = el('rect', { 'class': 'k2-band-good' }, g), br = el('path', { 'class': 'k2-bracket-good' }, gf);
    var t = el('text', { 'class': 'k2-t-good k2-halo' }, gf);
    return {
      draw: function () {
        var a = f.get(p.from), b = f.get(p.to), ya = F(a), yb = F(b), pa = C.Y(ya), pb = C.Y(yb), x1 = C.X(Math.max(a, b)) + 34;
        band.setAttribute('x', C.box.x); band.setAttribute('width', (x1 - C.box.x).toFixed(1));
        band.setAttribute('y', Math.min(pa, pb).toFixed(1)); band.setAttribute('height', Math.abs(pa - pb).toFixed(1));
        br.setAttribute('d', 'M' + (x1 - 10) + ' ' + pa.toFixed(1) + ' H' + x1 + ' V' + pb.toFixed(1) + ' H' + (x1 - 10));
        var pct = ya ? (1 - yb / ya) * 100 : 0;
        t.textContent = tpl(p.text || '{pct} %', { pct: pct }, 0);
        t.setAttribute('x', (x1 + 12).toFixed(1)); t.setAttribute('y', ((pa + pb) / 2 + 8).toFixed(1));
        var op = f.get(p.show, 1) * (Math.abs(pa - pb) > 4 ? 1 : 0);
        setOp(g, op); setOp(gf, op);
      }
    };
  });

  /* ===== OBJECTS ============================================================================================= */
  /* pipe - a pipe cut along its length: outline, metal walls hatched as cut faces, the liquid in its bore, and the flow
     as particles that follow the line, faster where it narrows, stopped when nothing flows.
     {pts: [[x, y], ...] (straight runs), r: bore radius, wall, flow: "V.flow" (0..1), speed, n: particles,
      gate: {x, open: ref} - a gate valve across it: the particles squeeze through the opening under the gate} */
  define('pipe', function (f, p) {
    var P = p.pts, r = p.r || 26, wall = p.wall || 9, R = r + wall, d0 = poly(P), i, segs = [], len = 0;
    for (i = 1; i < P.length; i++) {
      var a = P[i - 1], b = P[i], l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      segs.push({ a: a, b: b, s: len, l: l, ux: (b[0] - a[0]) / l, uy: (b[1] - a[1]) / l }); len += l;
    }
    var yTop = Math.min.apply(null, P.map(function (q) { return q[1]; })), yBot = Math.max.apply(null, P.map(function (q) { return q[1]; }));
    el('path', { d: d0, 'class': 'k2-outline-s', 'stroke-width': 2 * R + 5, 'stroke-linejoin': 'round' }, f.L.back);
    el('path', { d: d0, fill: 'none', stroke: f.band('metal', yTop - R, yBot + R), 'stroke-width': 2 * R, 'stroke-linejoin': 'round' }, f.L.back);
    el('path', { d: d0, fill: 'none', stroke: f.url('hatch'), 'stroke-width': 2 * R, 'stroke-linejoin': 'round' }, f.L.back);
    el('path', { d: d0, fill: 'none', stroke: f.band('liquid', yTop - r, yBot + r), 'stroke-width': 2 * r, 'stroke-linejoin': 'round' }, f.L.contents);
    el('path', { d: d0, 'class': 'k2-edge', transform: 'translate(0 ' + (-R + 1) + ')' }, f.L.back);
    f.solid(function () { var xs = P.map(function (q) { return q[0]; }); return { x: Math.min.apply(null, xs), y: yTop - R, x2: Math.max.apply(null, xs), y2: yBot + R }; });
    var n = p.n || Math.round(len / 9), parts = [], g = el('g', {}, f.L.fx), seed = 7;
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    for (i = 0; i < n; i++) { parts.push({ s: rnd() * len, o: rnd() * 2 - 1, k: 0.75 + rnd() * 0.5, c: el('line', { 'stroke-width': (4.4 + rnd() * 3.2).toFixed(1), 'class': 'k2-particle-s' }, g) }); }
    function at(s) {
      for (var j = 0; j < segs.length; j++) { if (s <= segs[j].s + segs[j].l || j === segs.length - 1) { var q = segs[j], t = s - q.s; return [q.a[0] + q.ux * t, q.a[1] + q.uy * t, -q.uy, q.ux]; } }
      return [0, 0, 0, 1];
    }
    var flow = 0, G = p.gate;
    return {
      calc: function () { flow = clamp(f.get(p.flow, 1), 0, 1); },
      draw: function (dt) {
        var v = (p.speed || 120) * flow, open = G ? clamp(f.get(G.open, 1), 0.02, 1) : 1, band = r * 2.2;
        parts.forEach(function (q) {
          var c = at(q.s), near = G ? clamp(1 - Math.abs(c[0] - G.x) / band, 0, 1) : 0, sm = near * near * (3 - 2 * near);
          q.s += v * q.k * dt * (1 + sm * (1 / open - 1) * 0.8);
          if (q.s > len) { q.s -= len; } else if (q.s < 0) { q.s += len; }
          c = at(q.s); near = G ? clamp(1 - Math.abs(c[0] - G.x) / band, 0, 1) : 0; sm = near * near * (3 - 2 * near);
          var o = q.o * 0.82, o2 = 1 - (1 - o) * open;                    /* under the gate: squeezed into the open part */
          var off = lerp(o, o2, sm) * r, X1 = c[0] + c[2] * off, Y1 = c[1] + c[3] * off;
          var vx = q.x == null || !dt ? 0 : (X1 - q.x) / dt, vy = q.x == null || !dt ? 0 : (Y1 - q.y) / dt, sp = Math.hypot(vx, vy);
          if (sp > 2500) { vx = vy = sp = 0; }                              /* it wrapped round to the start */
          var tail = Math.min(34, sp * 0.045) / Math.max(sp, 1e-6);         /* a streak: as long as it is fast */
          q.c.setAttribute('x1', (X1 - vx * tail).toFixed(1)); q.c.setAttribute('y1', (Y1 - vy * tail).toFixed(1));
          q.c.setAttribute('x2', X1.toFixed(1)); q.c.setAttribute('y2', Y1.toFixed(1));
          q.x = X1; q.y = Y1;
        });
      },
      live: function () { return flow > 0.001 && !f.hidden; }
    };
  });

  /* gate_valve - a gate valve cut through on a horizontal pipe: body and bonnet hatched as cut faces, the wedge gate
     sliding down across the bore into its seat, a rising stem, the handwheel turning as it moves. Publishes flow (0..1)
     and, with "pressure": [at open, at shut], the pressure before it.
     {x, y (the pipe's axis), r (the pipe's bore), open: "@open", turns, label, sub} */
  define('gate_valve', function (f, p) {
    var x = p.x, y = p.y, r = p.r || 30, bw = p.bw || r * 2.5, pw = Math.max(16, r * 0.5), nw = pw + 16, fh = nw + 20;
    var yb = y + r * 2.0, yc = y - r * 2.0, top = y - r * 4.6, wy = top - 30, wr = r * 1.9, gh = 2 * r + 14;
    function R(x0, y0, x1, y1) { return ' M' + x0 + ' ' + y0 + ' H' + x1 + ' V' + y1 + ' H' + x0 + ' Z'; }
    var body = 'M' + (x - bw) + ' ' + (y - r - 12) + ' Q' + (x - bw) + ' ' + yc + ' ' + (x - nw) + ' ' + (yc - 6) +
      ' L' + (x - nw) + ' ' + (top + 20) + ' L' + (x - fh) + ' ' + (top + 20) + ' L' + (x - fh) + ' ' + top + ' L' + (x + fh) + ' ' + top +
      ' L' + (x + fh) + ' ' + (top + 20) + ' L' + (x + nw) + ' ' + (top + 20) + ' L' + (x + nw) + ' ' + (yc - 6) +
      ' Q' + (x + bw) + ' ' + yc + ' ' + (x + bw) + ' ' + (y - r - 12) + ' L' + (x + bw) + ' ' + (y + r + 12) +
      ' Q' + (x + bw) + ' ' + yb + ' ' + x + ' ' + (yb + 4) + ' Q' + (x - bw) + ' ' + yb + ' ' + (x - bw) + ' ' + (y + r + 12) + ' Z';
    /* open inside: the bore the liquid runs through, the pocket the gate rises into, the seat it closes on */
    var bore = R(x - bw, y - r, x + bw, y + r), pocket = R(x - pw, top + 28, x + pw, y - r), seat = R(x - pw, y + r, x + pw, y + r + 12);
    f.shadow(x, yb + 14, bw * 1.25, 16);
    el('path', { d: body, 'class': 'k2-outline-s', 'stroke-width': 7, 'stroke-linejoin': 'round' }, f.L.hero);
    el('path', { d: body + bore + pocket + seat, 'fill-rule': 'evenodd', fill: f.url('metal') }, f.L.hero);
    el('path', { d: body + bore + pocket + seat, 'fill-rule': 'evenodd', fill: f.url('hatch') }, f.L.hero);
    el('path', { d: body, 'class': 'k2-edge' }, f.L.hero);
    el('path', { d: pocket + seat, 'class': 'k2-cavity' }, f.L.contents);
    /* the gate: a wedge, wider at its top, seen edge on */
    var gate = el('g', {}, f.L.front);
    var stem = el('rect', { x: x - 4.5, width: 9, rx: 2, fill: f.url('metalv') }, gate);
    var wedge = 'M' + (-(pw - 2)) + ' ' + (-gh) + ' H' + (pw - 2) + ' L' + (pw - 6) + ' 0 H' + (-(pw - 6)) + ' Z';
    var gg = el('g', {}, gate);
    el('path', { d: wedge, 'class': 'k2-outline-s', 'stroke-width': 4, 'stroke-linejoin': 'round' }, gg);
    el('path', { d: wedge, fill: f.url('metalv') }, gg);
    el('path', { d: wedge, fill: f.url('hatch') }, gg);
    /* the handwheel seen from the side: its rim, its hub on the stem, spokes that turn round it */
    var wheel = el('g', {}, f.L.front);
    el('rect', { x: x - wr - 3, y: wy - 9, width: 2 * wr + 6, height: 18, rx: 9, 'class': 'k2-outline' }, wheel);
    el('rect', { x: x - wr, y: wy - 6, width: 2 * wr, height: 12, rx: 6, fill: f.url('metalv') }, wheel);
    var spokes = [], i;
    for (i = 0; i < 5; i++) { spokes.push(el('rect', { y: wy - 6, width: 7, height: 12, rx: 2, 'class': 'k2-spoke' }, wheel)); }
    el('rect', { x: x - 12, y: wy - 12, width: 24, height: 24, rx: 5, 'class': 'k2-outline' }, wheel);
    el('rect', { x: x - 10, y: wy - 10, width: 20, height: 20, rx: 4, fill: f.url('metal') }, wheel);
    f.solid(function () { return { x: x - bw - 4, y: wy - 14, x2: x + bw + 4, y2: yb + 6 }; });
    if (p.label) { f.label({ text: p.label, sub: p.sub, at: function () { return [x + wr, wy]; }, side: 'right', dist: 18 }); }
    var lastO = f.target(p.open, 1);
    return {
      onStep: function (n, instant) {
        var o = f.target(p.open, 1);
        if (!instant && o < 0.01 && lastO >= 0.01) { f.pulse(x, y + r + 6, { delay: 900, tone: 'amber', r: 60 }); }
        lastO = o;
      },
      calc: function () {
        var o = clamp(f.get(p.open, 1), 0, 1), pr = p.pressure;
        f.publish(p.id, 'flow', o); f.publish(p.id, 'open', o);
        if (pr) { f.publish(p.id, 'pressure', pr[1] + (pr[0] - pr[1]) * Math.pow(o, 0.5)); }
      },
      draw: function () {
        var o = clamp(f.get(p.open, 1), 0, 1), gb = (y + r + 11) - (2 * r + 11) * o;   /* the gate's foot: in its seat when shut */
        gg.setAttribute('transform', 'translate(' + x + ' ' + gb.toFixed(1) + ')');
        var st = wy - 12 - 2 * r * o * 0.85 - 8;                    /* the rising stem stands out above the wheel when open */
        stem.setAttribute('y', st.toFixed(1)); stem.setAttribute('height', (gb - gh - st + 2).toFixed(1));
        var ph = o * (p.turns || 3) * 2 * Math.PI;
        spokes.forEach(function (s, k) {
          var a = ph + k * 2 * Math.PI / spokes.length;
          s.setAttribute('x', (x + Math.sin(a) * (wr - 8) - 3.5).toFixed(1)); s.style.opacity = Math.cos(a) > 0 ? 1 : 0.3;
        });
      }
    };
  });

  /* gauge - a pressure gauge on a stem, its needle easing to the value. {x, y, r, min, max, step, value, label, unit, stem} */
  define('gauge', function (f, p) {
    var x = p.x, y = p.y, r = p.r || 48, lo = p.min || 0, hi = p.max != null ? p.max : 10, a0 = -225, a1 = 45, g = el('g', {}, f.L.front);
    if (p.stem) { el('rect', { x: x - 6, y: y + r - 2, width: 12, height: p.stem, fill: f.url('metal') }, f.L.hero); }
    el('circle', { cx: x, cy: y, r: r + 5, 'class': 'k2-outline' }, g);
    el('circle', { cx: x, cy: y, r: r + 2, fill: f.url('metal') }, g);
    el('circle', { cx: x, cy: y, r: r - 4, 'class': 'k2-face' }, g);
    function ang(v) { return (a0 + (clamp(v, lo, hi) - lo) / (hi - lo) * (a1 - a0)) * Math.PI / 180; }
    for (var v = lo; v <= hi + 1e-9; v += (p.step || (hi - lo) / 8)) {
      var a = ang(v), c = Math.cos(a), s = Math.sin(a), major = Math.abs(((v - lo) / (p.step || 1)) % 2) < 1e-6;
      el('line', { x1: x + c * (r - 8), y1: y + s * (r - 8), x2: x + c * (r - (major ? 17 : 13)), y2: y + s * (r - (major ? 17 : 13)), 'class': major ? 'k2-tick-major' : 'k2-tick' }, g);
      if (major) { el('text', { x: x + c * (r - 31), y: y + s * (r - 31) + 5, 'text-anchor': 'middle', 'class': 'k2-t-face' }, g, num(v, 0)); }
    }
    if (p.unit) { el('text', { x: x, y: y + r * 0.66, 'text-anchor': 'middle', 'class': 'k2-t-face' }, g, p.unit); }
    var nd = el('path', { d: 'M -5 0 L ' + (r - 12) + ' -1.2 L ' + (r - 12) + ' 1.2 L -5 0 Z M -8 -4 L 0 -4 L 0 4 L -8 4 Z', 'class': 'k2-needle' }, g);
    el('circle', { cx: x, cy: y, r: 6, 'class': 'k2-hub' }, g);
    f.solid(function () { return { x: x - r - 6, y: y - r - 6, x2: x + r + 6, y2: y + r + 6 }; });
    if (p.label) { f.label({ text: p.label, at: function () { return [x - r - 4, y]; }, side: 'left', dist: 10 }); }
    return { draw: function () { nd.setAttribute('transform', 'translate(' + x + ' ' + y + ') rotate(' + (ang(f.get(p.value, lo)) * 180 / Math.PI).toFixed(2) + ')'); } };
  });

  /* ===== WORDS =============================================================================================== */
  /* callout - words for a place, beside it with a leader when they must go further. {at: [x, y], text, sub, side, show} */
  define('callout', function (f, p) {
    f.label({ text: p.text, sub: p.sub, at: function () { return p.at; }, side: p.side, dist: p.dist, lead: p.lead,
      show: p.show != null ? function () { return f.get(p.show, 1); } : null });
    return {};
  });

  /* ===== CONCEPTS ============================================================================================ */
  /* triangle - three things held together: each corner moves out by its value, the old shape stays as a ghost, a strain
     turns the stretched sides amber, a corner can be held (a padlock), and a frame can close round it.
     {corners: [{at:[x, y], dir:[dx, dy], push: "@scope", k: px per unit, name, value: "@scope", fmt: "{v} jobs",
                 note, noteShow: "@extra", side: left|right, hold: "@same", strain: true}],
      strain: "@strain", frame: {label, show: "@frame", inset}} */
  define('triangle', function (f, p) {
    var Cs = p.corners, frame = p.frame, i, fb, fon, fl;
    if (frame) {
      var fi = frame.inset || 26, fw = f.W - 2 * fi, fh = f.H - 2 * fi;
      f.frameLine = el('rect', { x: fi, y: fi, width: fw, height: fh, rx: 24, 'class': 'k2-frame' }, f.L.back);
      fb = el('rect', { x: fi + 9, y: fi + 9, width: fw - 18, height: fh - 18, rx: 18, fill: 'none', stroke: f.url('hatch'), 'stroke-width': 14 }, f.L.back);
      /* the frame closes round the shape: its line is drawn on, from the corner its words stand at */
      fon = el('rect', { x: fi, y: fi, width: fw, height: fh, rx: 24, 'class': 'k2-frame-on', pathLength: 1, 'stroke-dasharray': '0 1' }, f.L.back);
      fl = el('text', { x: fi + 40, y: fi + 6, 'class': 'k2-t-lbl k2-halo k2-halo-wide' }, f.L.lbl, frame.label || '');
    }
    var ghost = el('path', { 'class': 'k2-ghost' }, f.L.back);
    var hero = el('g', {}, f.L.hero);
    var fill = el('path', { fill: f.url('fill-blue') }, hero), warm = el('path', { fill: f.url('fill-amber') }, hero);
    var sides = [], sidesA = [];
    for (i = 0; i < 3; i++) { sides.push(el('path', { 'class': 'k2-side-blue' }, hero)); sidesA.push(el('path', { 'class': 'k2-side-amber' }, hero)); }
    var edge = el('path', { 'class': 'k2-edge', 'stroke-linejoin': 'round' }, hero);
    function corner(c, how) {
      var v = how === 'rest' ? f.rest(c.push, 0) : how === 'to' ? f.target(c.push, 0) : f.get(c.push, 0), b = f.rest(c.base, 0), k = c.k || 50;
      return [c.at[0] + c.dir[0] * (v - b) * k, c.at[1] + c.dir[1] * (v - b) * k];
    }
    var nodes = Cs.map(function (c) {
      var g = el('g', {}, f.L.front);
      el('circle', { r: 11, 'class': 'k2-node' }, g);
      el('circle', { r: 11, 'class': 'k2-node-ring' }, g);
      var ra = el('circle', { r: 11, 'class': 'k2-node-ring-amber' }, g);
      var lock = el('g', {}, f.L.front);
      el('path', { d: 'M-10 -9 V-19 A10 10 0 0 1 10 -19 V-9', 'class': 'k2-lock-arc' }, lock);
      el('rect', { x: -17, y: -11, width: 34, height: 27, rx: 5, 'class': 'k2-lock' }, lock);
      el('circle', { cy: 1, r: 4, 'class': 'k2-lock-hole' }, lock);
      var end = c.side === 'left' ? 'end' : 'start';
      var words = el('g', { 'text-anchor': end }, f.L.lbl);
      el('text', { x: 0, y: -8, 'class': 'k2-t-name k2-halo' }, words, c.name || '');
      var vg = el('g', {}, words), vgA = el('g', {}, words);
      var val = new Roller(vg, { x: 0, y: 30, 'class': 'k2-t-val k2-halo' }), valA = new Roller(vgA, { x: 0, y: 30, 'class': 'k2-t-val k2-t-amber k2-halo' });
      var note = c.note ? el('text', { x: 0, y: 58, 'class': 'k2-t-note k2-halo' }, words, c.note) : null;
      var at = corner(c, 'to');
      return { g: g, ra: ra, lock: lock, words: words, val: val, valA: valA, vg: vg, vgA: vgA, note: note,
               sx: new Spring(at[0]), sy: new Spring(at[1]), sl: new Spring(f.target(c.hold, 0)), to: at, hold: f.target(c.hold, 0) };
    });
    var moving = false;
    f.solid(function () { var q = nodes.map(function (N) { return [N.sx.x, N.sy.x]; }); var xs = q.map(function (a) { return a[0]; }), ys = q.map(function (a) { return a[1]; });
      return { x: Math.min.apply(null, xs), y: Math.min.apply(null, ys), x2: Math.max.apply(null, xs), y2: Math.max.apply(null, ys) }; });
    return {
      /* a ring where a corner is about to land, or where a corner is held */
      onStep: function (n, instant) {
        if (instant) { return; }
        Cs.forEach(function (c, j) {
          var N = nodes[j], to = corner(c, 'to'), h = f.target(c.hold, 0);
          if (Math.hypot(to[0] - N.to[0], to[1] - N.to[1]) > 2) { f.pulse(to[0], to[1], { delay: 380, tone: c.strain ? 'amber' : null }); }
          if (h > N.hold + 0.5) { f.pulse(to[0], to[1], { delay: 120 }); }
          N.to = to; N.hold = h;
        });
      },
      draw: function (dt, snap) {
        var q0 = Cs.map(function (c) { return corner(c, 'rest'); }), m = false;
        var q = Cs.map(function (c, j) {
          var N = nodes[j], to = corner(c, 'to');
          m = N.sx.go(to[0], dt, snap) || m; m = N.sy.go(to[1], dt, snap) || m;
          m = N.sl.go(f.target(c.hold, 0), dt, snap) || m;
          return [N.sx.x, N.sy.x];
        });
        moving = m;
        var tri = poly(q, true), s = clamp(f.get(p.strain, 0), 0, 1);
        fill.setAttribute('d', tri); warm.setAttribute('d', tri); setOp(warm, s); edge.setAttribute('d', tri);
        var moved = q0.map(function (a, j) { return Math.hypot(corner(Cs[j])[0] - a[0], corner(Cs[j])[1] - a[1]); }).reduce(function (x, y) { return Math.max(x, y); }, 0);
        ghost.setAttribute('d', poly(q0, true)); setOp(ghost, clamp(moved / 20, 0, 1));
        for (var j = 0; j < 3; j++) {
          var a = q[j], b = q[(j + 1) % 3], dd = 'M' + pt(a) + ' L' + pt(b);
          var hot = Cs[j].strain || Cs[(j + 1) % 3].strain;                /* a side to a strained corner warms */
          sides[j].setAttribute('d', dd); sidesA[j].setAttribute('d', dd); setOp(sidesA[j], hot ? s : 0);
        }
        Cs.forEach(function (c, j) {
          var N = nodes[j], at = q[j], hold = clamp(f.get(c.hold, 0), 0, 1), pop = Math.max(0, N.sl.x), hot = c.strain ? s : 0;
          N.g.setAttribute('transform', 'translate(' + pt(at) + ')'); setOp(N.g, 1 - hold); setOp(N.ra, hot);
          N.lock.setAttribute('transform', 'translate(' + pt(at) + ') scale(' + (0.2 + 0.8 * pop).toFixed(3) + ')'); setOp(N.lock, hold);
          var dx = c.side === 'left' ? -28 : 30, oy = c.dy != null ? c.dy : 0;
          N.words.setAttribute('transform', 'translate(' + (at[0] + dx).toFixed(1) + ' ' + (at[1] + oy).toFixed(1) + ')');
          var v = f.get(c.value, 0);
          N.val.set(v, c.fmt || '{v}', c.decimals || 0); N.valA.set(v, c.fmt || '{v}', c.decimals || 0); setOp(N.vgA, hot); setOp(N.vg, 1 - hot);
          if (N.note) {                                                  /* a note rises into place as it appears */
            var ns = clamp(f.get(c.noteShow, 1), 0, 1);
            setOp(N.note, ns); N.note.setAttribute('transform', 'translate(0 ' + ((1 - ns) * 14).toFixed(1) + ')');
          }
        });
        if (frame) {
          var fo = clamp(f.get(frame.show, 0), 0, 1);
          fon.setAttribute('stroke-dasharray', fo.toFixed(4) + ' 1'); setOp(fb, clamp(fo * 2 - 1, 0, 1)); setOp(f.frameLine, 1 - fo * 0.7);
        }
      },
      live: function () { return moving; }
    };
  });

  /* cycle - stages round a ring, each an arrow into the next (plan-do-check-act, a maintenance cycle, a watch routine).
     at: "@stage" - k lights stage k; between two the light passes on; past the last it goes round again, and a marker
     runs round the ring with it. {x, y, r, band, stages: [{name, sub, cat}], at, center: {text, sub}} */
  define('cycle', function (f, p) {
    var St = p.stages || [], n = St.length, cx = p.x, cy = p.y, R = p.r || 150, B = p.band || 42, seg = 2 * Math.PI / n;
    var gap = 0.045, tip = Math.min(0.17, seg * 0.2), a00 = -Math.PI / 2;
    function P(a, rr) { return [cx + rr * Math.cos(a), cy + rr * Math.sin(a)]; }
    var g = el('g', {}, f.L.hero), items;
    el('circle', { cx: cx, cy: cy, r: R - B / 2 - 14, 'class': 'k2-hub-disc' }, f.L.back);
    items = St.map(function (st, j) {
      var a0 = a00 + j * seg + gap, a1 = a00 + (j + 1) * seg - gap, ro = R + B / 2, ri = R - B / 2, cat = st.cat || (j % 5) + 1, big = a1 - a0 > Math.PI ? 1 : 0;
      var d = 'M' + pt(P(a0, ro)) + ' A' + ro + ' ' + ro + ' 0 ' + big + ' 1 ' + pt(P(a1, ro)) + ' L' + pt(P(a1 + tip, R)) + ' L' + pt(P(a1, ri)) +
        ' A' + ri + ' ' + ri + ' 0 ' + big + ' 0 ' + pt(P(a0, ri)) + ' L' + pt(P(a0 + tip, R)) + ' Z';
      var sg = el('g', {}, g);
      el('path', { d: d, 'class': 'k2-outline-s', 'stroke-width': 6, 'stroke-linejoin': 'round' }, sg);
      el('path', { d: d, fill: f.url('solid-cat-' + cat) }, sg);
      el('path', { d: d, 'class': 'k2-edge' }, sg);
      var mid = (a0 + a1) / 2, c = Math.cos(mid), sn = Math.sin(mid), lp = P(mid, ro + 22);
      var anchor = c > 0.25 ? 'start' : c < -0.25 ? 'end' : 'middle';
      var wg = el('g', { 'text-anchor': anchor }, f.L.lbl);
      var dy = sn < -0.5 ? -26 : sn > 0.5 ? 18 : -6;
      el('text', { x: lp[0], y: lp[1] + dy, 'class': 'k2-t-lbl k2-t-big k2-halo' }, wg, st.name || '');
      if (st.sub) { el('text', { x: lp[0], y: lp[1] + dy + 24, 'class': 'k2-t-sub k2-halo' }, wg, st.sub); }
      return { g: sg, mid: mid, words: wg };
    });
    var glow = el('circle', { r: 26, 'class': 'k2-marker-glow' }, f.L.front), mark = el('circle', { r: 12, 'class': 'k2-marker' }, f.L.front);
    if (p.center) {
      el('text', { x: cx, y: cy + (p.center.sub ? -2 : 10), 'text-anchor': 'middle', 'class': 'k2-t-val k2-halo' }, f.L.lbl, p.center.text || '');
      if (p.center.sub) { el('text', { x: cx, y: cy + 28, 'text-anchor': 'middle', 'class': 'k2-t-sub k2-halo' }, f.L.lbl, p.center.sub); }
    }
    f.solid(function () { return { x: cx - R - B, y: cy - R - B, x2: cx + R + B, y2: cy + R + B }; });
    var last = f.target(p.at, 0);
    return {
      onStep: function (n2, instant) {
        var a = f.target(p.at, 0);
        if (!instant && a >= 1 && Math.round(a) !== Math.round(last)) { var q = P(a00 + (a - 0.5) * seg, R); f.pulse(q[0], q[1], { delay: 520, r: 54 }); }
        last = a;
      },
      draw: function () {
        var at = f.get(p.at, 0), on = clamp(at * 2 - 1, 0, 1), cyc = at - 1;
        items.forEach(function (it, j) {
          var dd = Math.abs(((cyc - j) % n + n + n / 2) % n - n / 2), lit = on * clamp(1 - dd, 0, 1), e = lit * lit * (3 - 2 * lit);
          setOp(it.g, 0.34 + 0.66 * Math.max(e, 1 - on));
          it.g.setAttribute('transform', 'translate(' + (Math.cos(it.mid) * 10 * e).toFixed(1) + ' ' + (Math.sin(it.mid) * 10 * e).toFixed(1) + ')');
          setOp(it.words, 0.5 + 0.5 * Math.max(e, 1 - on));
        });
        var q = P(a00 + (at - 0.5) * seg, R);
        mark.setAttribute('cx', q[0].toFixed(1)); mark.setAttribute('cy', q[1].toFixed(1)); setOp(mark, on);
        glow.setAttribute('cx', q[0].toFixed(1)); glow.setAttribute('cy', q[1].toFixed(1)); setOp(glow, on * 0.4);
      }
    };
  });

  /* gantt - tasks on a time line, each bar starting when the tasks before it end: a slip pushes everything after it,
     the critical path lights, the finish moves (or holds, when the slip had slack), today's line shows what is done.
     {x, y, w, h, nameW, start, end, step, tick: "W{v}", tasks: [{id, name, d, after: [ids], slip: "@x", crit, cat}],
      draw: "@d", crit: "@c", today: "@t", finish: "Finish {v}"} */
  define('gantt', function (f, p) {
    var T = p.tasks || [], n = T.length, x0 = p.x, y0 = p.y, W = p.w, H = p.h, nw = p.nameW || 210, tx = x0 + nw, tw = W - nw - 10;
    var t0 = p.start || 0, t1 = p.end, head = 40, rh = Math.min(p.rowH || 74, (H - head - 60) / n), bh = Math.round(rh * 0.56);
    function X(t) { return tx + (t - t0) / (t1 - t0) * tw; }
    var g = el('g', {}, f.L.back), t, heads = [];
    f.thin(heads, 'x');
    for (t = t0; t <= t1 + 1e-9; t += (p.step || 1)) {
      el('line', { x1: X(t), y1: y0 + head - 6, x2: X(t), y2: y0 + head + n * rh, 'class': 'k2-grid' }, g);
      if (t < t1) { heads.push({ n: el('text', { x: (X(t) + X(t + (p.step || 1))) / 2, y: y0 + 24, 'text-anchor': 'middle', 'class': 'k2-t-tick' }, g, tpl(p.tick || '{v}', { v: t + 1 }, 0)), at: (X(t) + X(t + (p.step || 1))) / 2 }); }
    }
    var rows = T.map(function (k, i) {
      var cy = y0 + head + i * rh + rh / 2;
      if (i % 2 === 0) { el('rect', { x: x0, y: cy - rh / 2, width: W, height: rh, rx: 8, 'class': 'k2-row' }, g); }
      el('text', { x: x0 + 12, y: cy + 6, 'class': 'k2-t-lbl k2-halo' }, f.L.lbl, k.name || k.id);
      var bg = el('g', {}, f.L.hero), cat = k.cat || 1;
      var crit = el('rect', { y: cy - bh / 2 - 5, height: bh + 10, rx: 12, 'class': 'k2-crit' }, bg);
      var ol = el('rect', { y: cy - bh / 2 - 2.5, height: bh + 5, rx: 10, 'class': 'k2-outline' }, bg);
      var bar = el('rect', { y: cy - bh / 2, height: bh, rx: 8, fill: f.url('solid-cat-' + cat) }, bg);
      var done = el('rect', { y: cy - bh / 2, height: bh, rx: 8, 'class': 'k2-bar-done' }, bg);
      var slipR = el('rect', { y: cy - bh / 2, height: bh, rx: 8, 'class': 'k2-bar-slip' }, bg);
      var lab = el('text', { y: cy + 6, 'class': 'k2-t-inbar' }, bg);
      return { k: k, cy: cy, crit: crit, ol: ol, bar: bar, done: done, slipR: slipR, lab: lab, deps: (k.after || []).map(function () { return { path: el('path', { 'class': 'k2-dep' }, f.L.back), head: el('path', { 'class': 'k2-dep-head' }, f.L.back) }; }) };
    });
    var byId = {}; rows.forEach(function (r) { byId[r.k.id] = r; });
    var fy = y0 + head + n * rh + 10, finLine = el('path', { 'class': 'k2-finish' }, f.L.front), finTag = el('g', {}, f.L.front);
    var finR = el('rect', { rx: 8, height: 30, 'class': 'k2-tag-amber' }, finTag), finT = new Roller(finTag, { y: 15, x: 10, 'class': 'k2-t-tag', 'dominant-baseline': 'central' });
    var tdLine = el('path', { 'class': 'k2-today' }, f.L.front), tdTag = el('g', {}, f.L.front);
    var tdR = el('rect', { rx: 8, height: 28, 'class': 'k2-tag' }, tdTag), tdT = el('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'class': 'k2-t-tag' }, tdTag, p.todayLabel || 'Today');
    var lastFin = null;
    function plan(to) {
      var S = {}, E = {}, end = t0;
      T.forEach(function (k) {
        var st = k.s != null ? k.s : t0;
        (k.after || []).forEach(function (a) { st = Math.max(st, E[a]); });
        S[k.id] = st; E[k.id] = st + k.d + (to ? f.target(k.slip, 0) : f.get(k.slip, 0)); end = Math.max(end, E[k.id]);
      });
      return { S: S, E: E, end: end };
    }
    f.solid(function () { return { x: x0, y: y0, x2: x0 + W, y2: fy + 40 }; });
    return {
      onStep: function (n2, instant) {
        var e = plan(true).end;
        if (!instant && lastFin != null && Math.abs(e - lastFin) > 0.01) { f.pulse(X(e), fy + 15, { delay: 700, tone: 'amber', r: 50 }); }
        lastFin = e;
      },
      calc: function () { var q = plan(); f.publish(p.id, 'finish', q.end); },
      draw: function () {
        var q = plan(), dr = clamp(f.get(p.draw, 1), 0, 1), cr = clamp(f.get(p.crit, 0), 0, 1), today = f.get(p.today, t0);
        rows.forEach(function (r, i) {
          var k = r.k, s0 = q.S[k.id], e0 = q.E[k.id], grow = clamp(dr * (n * 0.55 + 1) - i * 0.55, 0, 1), ge = grow * grow * (3 - 2 * grow);
          var xs = X(s0), wfull = X(e0) - xs, w0 = Math.max(0, wfull * ge), slip = f.get(k.slip, 0), ws = X(e0) - X(e0 - slip);
          [r.bar, r.done, r.slipR].forEach(function (b) { b.setAttribute('x', xs.toFixed(1)); });
          r.bar.setAttribute('width', w0.toFixed(1));
          r.ol.setAttribute('x', (xs - 2.5).toFixed(1)); r.ol.setAttribute('width', (w0 + 5).toFixed(1)); setOp(r.ol, ge > 0.01 ? 1 : 0);
          r.crit.setAttribute('x', (xs - 5).toFixed(1)); r.crit.setAttribute('width', (w0 + 10).toFixed(1)); setOp(r.crit, k.crit ? cr * ge : 0);
          r.done.setAttribute('width', clamp(X(today) - xs, 0, w0).toFixed(1));
          r.slipR.setAttribute('x', (xs + w0 - Math.min(ws, w0)).toFixed(1)); r.slipR.setAttribute('width', Math.min(ws, w0).toFixed(1)); setOp(r.slipR, slip > 0.02 ? 1 : 0);
          r.lab.textContent = tpl(p.dur || '{v} wk', { v: k.d + slip }, 0); r.lab.setAttribute('x', (xs + 12).toFixed(1)); setOp(r.lab, w0 > 70 ? ge : 0);
          (k.after || []).forEach(function (a, j) {
            var pr = byId[a]; if (!pr) { return; }
            var ex = X(q.E[a]) - 12, ey = pr.cy + bh / 2 + 2, sy = r.cy, dep = r.deps[j], up = sy < ey;
            dep.path.setAttribute('d', 'M' + ex.toFixed(1) + ' ' + (up ? pr.cy - bh / 2 - 2 : ey).toFixed(1) + ' V' + sy.toFixed(1) + ' H' + (xs - 9).toFixed(1));
            dep.head.setAttribute('d', 'M' + (xs - 1).toFixed(1) + ' ' + sy.toFixed(1) + ' l -10 -6 v 12 Z');
            var hot = k.crit && pr.k.crit ? cr : 0;
            dep.path.setAttribute('class', hot > 0.5 ? 'k2-dep k2-dep-crit' : 'k2-dep'); dep.head.setAttribute('class', hot > 0.5 ? 'k2-dep-head k2-dep-head-crit' : 'k2-dep-head');
            setOp(dep.path, ge); setOp(dep.head, ge);
          });
        });
        var fx = X(q.end), fo = clamp(dr * 2 - 1, 0, 1);
        finLine.setAttribute('d', 'M' + fx.toFixed(1) + ' ' + (y0 + head - 6) + ' V' + fy); setOp(finLine, fo);
        finT.set(q.end, p.finish || 'Finish {v}', 0);
        var fb2 = finT.a.getBBox(), fwid = fb2.width + 20, fh2 = Math.max(30, fb2.height + 8);
        finR.setAttribute('width', fwid.toFixed(1)); finR.setAttribute('height', fh2.toFixed(1)); finR.setAttribute('x', 0);
        finT.a.setAttribute('y', (fh2 / 2).toFixed(1)); finT.b.setAttribute('y', (fh2 / 2).toFixed(1));
        finTag.setAttribute('transform', 'translate(' + (fx - fwid / 2).toFixed(1) + ' ' + fy + ')'); setOp(finTag, fo);
        var to = clamp((today - t0) * 3, 0, 1);
        tdLine.setAttribute('d', 'M' + X(today).toFixed(1) + ' ' + (y0 + head - 4) + ' V' + (y0 + head + n * rh)); setOp(tdLine, to);
        tdTag.setAttribute('transform', 'translate(' + X(today).toFixed(1) + ' ' + (y0 + head - 4) + ')'); setOp(tdTag, to);
        var tb = tdT.getBBox(), tw2 = tb.width + 20, th2 = Math.max(28, tb.height + 8);
        tdR.setAttribute('x', (-tw2 / 2).toFixed(1)); tdR.setAttribute('y', (-th2 - 6).toFixed(1)); tdR.setAttribute('width', tw2.toFixed(1)); tdR.setAttribute('height', th2.toFixed(1));
        tdT.setAttribute('y', (-th2 / 2 - 6).toFixed(1));
        heads.forEach(function (hd) { var hw = hd.n.getBBox().width / 2; setOp(hd.n, 1 - to * (1 - clamp((Math.abs(hd.at - X(today)) - tw2 / 2 - hw - 6) / 10, 0, 1))); });
      }
    };
  });

  /* matrix - a grid of rows and columns (a risk matrix, a stakeholder grid, urgent / important), its cells coloured by
     how high and how far right they are, and items that move from cell to cell; where an item started stays as a
     ghost with an arrow to where it is now. {x, y, w, h, rows: [top .. bottom], cols: [left .. right], xlabel, ylabel,
     heat: true, items: [{name, r: "@r1", c: "@c1", dx, dy, show}]} - r and c count from 0 at the top left */
  define('matrix', function (f, p) {
    var Rw = p.rows || [], Cl = p.cols || [], x0 = p.x, y0 = p.y, W = p.w, H = p.h, cw = W / Cl.length, ch = H / Rw.length, g = el('g', {}, f.L.back);
    Rw.forEach(function (rl, r) {
      Cl.forEach(function (cl, c) {
        var sc = ((Rw.length - 1 - r) / Math.max(1, Rw.length - 1) + c / Math.max(1, Cl.length - 1)) / 2;
        var tone = p.heat === false ? 'plain' : sc < 0.38 ? 'good' : sc < 0.68 ? 'amber' : 'warn';
        el('rect', { x: x0 + c * cw + 3, y: y0 + r * ch + 3, width: cw - 6, height: ch - 6, rx: 10, 'class': 'k2-heat k2-heat-' + tone }, g);
      });
      el('text', { x: x0 - 14, y: y0 + (r + 0.5) * ch + 5, 'text-anchor': 'end', 'class': 'k2-t-tick' }, g, rl);
    });
    Cl.forEach(function (cl, c) { el('text', { x: x0 + (c + 0.5) * cw, y: y0 + H + 24, 'text-anchor': 'middle', 'class': 'k2-t-tick' }, g, cl); });
    if (p.xlabel) { el('text', { x: x0 + W / 2, y: y0 + H + 54, 'text-anchor': 'middle', 'class': 'k2-t-axis' }, g, p.xlabel + ' →'); }
    if (p.ylabel) { el('text', { x: x0 - 14, y: y0 - 16, 'text-anchor': 'end', 'class': 'k2-t-axis' }, g, p.ylabel + ' ↑'); }
    function at(r, c, it) { return [x0 + (c + 0.5) * cw + (it.dx || 0), y0 + (r + 0.5) * ch + (it.dy || 0)]; }
    var its = (p.items || []).map(function (it, i) {
      var gh = el('g', {}, f.L.back), trail = el('path', { 'class': 'k2-trail' }, gh), ghost = el('circle', { r: 19, 'class': 'k2-pt-ghost' }, gh);
      var gi = el('g', {}, f.L.front), cat = it.cat || (i % 5) + 1;
      el('circle', { r: 22, 'class': 'k2-outline' }, gi);
      el('circle', { r: 19, fill: f.url('solid-cat-' + cat) }, gi);
      el('text', { y: 6, 'text-anchor': 'middle', 'class': 'k2-t-badge' }, gi, String(it.n || i + 1));
      var p0 = at(f.rest(it.r, 0), f.rest(it.c, 0), it);
      var o = { it: it, gh: gh, trail: trail, ghost: ghost, gi: gi, p0: p0, last: [f.target(it.r, 0), f.target(it.c, 0)], sx: new Spring(p0[0]), sy: new Spring(p0[1]) };
      f.solid(function () { return { x: o.sx.x - 23, y: o.sy.x - 23, x2: o.sx.x + 23, y2: o.sy.x + 23 }; });
      f.line(function () { return Math.hypot(o.sx.x - o.p0[0], o.sy.x - o.p0[1]) > 30 ? [o.p0, [o.sx.x, o.sy.x]] : []; });
      f.solid(function () { return { x: o.p0[0] - 20, y: o.p0[1] - 20, x2: o.p0[0] + 20, y2: o.p0[1] + 20 }; });
      if (it.name) { f.label({ text: it.name, at: function () { return [o.sx.x, o.sy.x]; }, r: 22, side: 'right', dist: 28, show: function () { return f.get(it.show, 1); } }); }
      return o;
    });
    var moving = false;
    return {
      onStep: function (n2, instant) {
        its.forEach(function (o) {
          var r = f.target(o.it.r, 0), c = f.target(o.it.c, 0);
          if (!instant && (r !== o.last[0] || c !== o.last[1])) { var q = at(r, c, o.it); f.pulse(q[0], q[1], { delay: 480, r: 44 }); }
          o.last = [r, c];
        });
      },
      draw: function (dt, snap) {
        moving = false;
        its.forEach(function (o) {
          var q = at(f.target(o.it.r, 0), f.target(o.it.c, 0), o.it);
          moving = o.sx.go(q[0], dt, snap) || moving; moving = o.sy.go(q[1], dt, snap) || moving;
          var x = o.sx.x, y = o.sy.x, sh = clamp(f.get(o.it.show, 1), 0, 1), dist = Math.hypot(x - o.p0[0], y - o.p0[1]);
          o.gi.setAttribute('transform', 'translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ') scale(' + (0.6 + 0.4 * sh).toFixed(3) + ')'); setOp(o.gi, sh);
          o.ghost.setAttribute('cx', o.p0[0]); o.ghost.setAttribute('cy', o.p0[1]);
          var ux = (x - o.p0[0]) / (dist || 1), uy = (y - o.p0[1]) / (dist || 1);
          o.trail.setAttribute('d', 'M' + (o.p0[0] + ux * 22).toFixed(1) + ' ' + (o.p0[1] + uy * 22).toFixed(1) + ' L' + (x - ux * 26).toFixed(1) + ' ' + (y - uy * 26).toFixed(1));
          setOp(o.gh, sh * clamp((dist - 30) / 40, 0, 1));
        });
      },
      live: function () { return moving; }
    };
  });

  /* node - a box in a process: a step (box), a decision (diamond) or where it starts and ends (pill). It pops in when
     shown and glows when lit. {id, x, y (its middle), w, h, kind: box | decision | end, text, sub, cat, show, lit} */
  define('node', function (f, p) {
    var x = p.x, y = p.y, w = p.w || 200, h = p.h || 74, kind = p.kind || 'box', d;
    if (kind === 'decision') { d = 'M' + x + ' ' + (y - h / 2 - 14) + ' L' + (x + w / 2 + 10) + ' ' + y + ' L' + x + ' ' + (y + h / 2 + 14) + ' L' + (x - w / 2 - 10) + ' ' + y + ' Z'; }
    else { var rr = kind === 'end' ? h / 2 : 14; d = 'M' + (x - w / 2 + rr) + ' ' + (y - h / 2) + ' H' + (x + w / 2 - rr) + ' A' + rr + ' ' + rr + ' 0 0 1 ' + (x + w / 2) + ' ' + (y - h / 2 + rr) +
      ' V' + (y + h / 2 - rr) + ' A' + rr + ' ' + rr + ' 0 0 1 ' + (x + w / 2 - rr) + ' ' + (y + h / 2) + ' H' + (x - w / 2 + rr) + ' A' + rr + ' ' + rr + ' 0 0 1 ' + (x - w / 2) + ' ' + (y + h / 2 - rr) +
      ' V' + (y - h / 2 + rr) + ' A' + rr + ' ' + rr + ' 0 0 1 ' + (x - w / 2 + rr) + ' ' + (y - h / 2) + ' Z'; }
    var g = el('g', {}, f.L.hero), inner = el('g', {}, g);
    var lit = el('path', { d: d, 'class': 'k2-lit' }, inner);
    el('path', { d: d, 'class': 'k2-outline-s', 'stroke-width': 7, 'stroke-linejoin': 'round' }, inner);
    el('path', { d: d, fill: p.cat ? f.url('solid-cat-' + p.cat) : f.url('metal'), 'class': p.cat ? null : 'k2-node-plain' }, inner);
    el('path', { d: d, 'class': 'k2-node-face' + (p.cat ? ' k2-node-face-cat' : '') }, inner);
    el('path', { d: d, 'class': 'k2-edge' }, inner);
    var tc = p.cat ? 'k2-t-oncat' : 'k2-t-lbl';
    inner.setAttribute('data-k2-holds', '');
    inner.querySelector('.k2-outline-s').setAttribute('data-k2-shape', '');
    var name = el('text', { x: x, 'text-anchor': 'middle', 'class': tc }, inner), subT = null;
    if (p.sub) { subT = el('text', { x: x, 'text-anchor': 'middle', 'class': p.cat ? 'k2-t-oncat-sub' : 'k2-t-sub' }, inner, p.sub); }
    /* the name on as many lines as the box's width needs (a decision's diamond is narrower where its words are) */
    (f.fits = f.fits || []).push(function () {
      var room = (kind === 'decision' ? w * 0.72 : w - 26), words = String(p.text || '').split(/\s+/), rows = [], cur = '';
      name.textContent = '';
      var probe = el('tspan', {}, name);
      words.forEach(function (wd) {
        var t = cur ? cur + ' ' + wd : wd;
        probe.textContent = t;
        if (cur && probe.getComputedTextLength() > room) { rows.push(cur); cur = wd; } else { cur = t; }
      });
      if (cur) { rows.push(cur); }
      name.removeChild(probe);
      var fs = parseFloat((name.ownerDocument.defaultView.getComputedStyle(name).fontSize) || 17);
      var total = rows.length * fs * 1.15 + (subT ? fs * 1.1 : 0), y0 = y - total / 2 + fs * 0.85;
      rows.forEach(function (r, i) { el('tspan', { x: x, y: (y0 + i * fs * 1.15).toFixed(1) }, name, r); });
      if (subT) { subT.setAttribute('y', (y0 + rows.length * fs * 1.15 + fs * 0.05).toFixed(1)); }
    });
    (f.nodes = f.nodes || {})[p.id] = { x: x, y: y, w: kind === 'decision' ? w + 20 : w, h: kind === 'decision' ? h + 28 : h };
    var sp = new Spring(f.target(p.show, 1)), moving = false, wasLit = f.target(p.lit, 0);
    f.solid(function () { return { x: x - w / 2 - 12, y: y - h / 2 - 16, x2: x + w / 2 + 12, y2: y + h / 2 + 16 }; });
    return {
      onStep: function (n, instant) { var l = f.target(p.lit, 0); if (!instant && l > 0.5 && wasLit < 0.5) { f.pulse(x, y, { delay: 250, r: Math.max(w, h) * 0.7 }); } wasLit = l; },
      draw: function (dt, snap) {
        moving = sp.go(f.target(p.show, 1), dt, snap);
        var sh = clamp(f.get(p.show, 1), 0, 1), sc = 0.7 + 0.3 * Math.max(0, sp.x);
        inner.setAttribute('transform', 'translate(' + x + ' ' + y + ') scale(' + sc.toFixed(3) + ') translate(' + (-x) + ' ' + (-y) + ')');
        setOp(g, sh); setOp(lit, clamp(f.get(p.lit, 0), 0, 1));
      },
      live: function () { return moving; }
    };
  });

  /* arrow - from one node to another, right-angled where they do not line up, drawn on as it appears.
     {id, from, to, label, draw: "@d", via: "h" | "v" (which way it leaves)} */
  define('arrow', function (f, p) {
    var A = f.nodes[p.from], B = f.nodes[p.to], ps;
    var dx = B.x - A.x, dy = B.y - A.y, hz = p.via ? p.via === 'h' : Math.abs(dx) >= Math.abs(dy);
    if (hz) {
      var sx = A.x + Math.sign(dx || 1) * A.w / 2, ex = B.x - Math.sign(dx || 1) * (B.w / 2 + 6);
      ps = Math.abs(dy) < 4 ? [[sx, A.y], [ex, B.y]] : (p.via === 'h' ? [[sx, A.y], [B.x, A.y], [B.x, B.y - Math.sign(dy) * (B.h / 2 + 6)]] : [[sx, A.y], [(sx + ex) / 2, A.y], [(sx + ex) / 2, B.y], [ex, B.y]]);
    } else {
      var sy = A.y + Math.sign(dy || 1) * A.h / 2, ey = B.y - Math.sign(dy || 1) * (B.h / 2 + 6);
      ps = Math.abs(dx) < 4 ? [[A.x, sy], [B.x, ey]] : (p.via === 'v' ? [[A.x, sy], [A.x, B.y], [B.x - Math.sign(dx) * (B.w / 2 + 6), B.y]] : [[A.x, sy], [A.x, (sy + ey) / 2], [B.x, (sy + ey) / 2], [B.x, ey]]);
    }
    var line = el('path', { d: poly(ps), 'class': 'k2-arrow', pathLength: 1, 'stroke-dasharray': '0 1' }, f.L.back);
    var e = ps[ps.length - 1], b = ps[ps.length - 2], ang = Math.atan2(e[1] - b[1], e[0] - b[0]) * 180 / Math.PI;
    var head = el('path', { d: 'M 0 0 L -14 -8 L -14 8 Z', 'class': 'k2-arrow-head', transform: 'translate(' + pt([e[0] + Math.cos(ang * Math.PI / 180) * 4, e[1] + Math.sin(ang * Math.PI / 180) * 4]) + ') rotate(' + ang.toFixed(1) + ')' }, f.L.back);
    (f.routes = f.routes || {})[p.id] = ps;
    var lab = null;
    f.line(function () { return ps; });
    if (p.label) {
      var li = 0, best = 0;                                  /* beside the longest straight piece */
      for (var q2 = 1; q2 < ps.length; q2++) { var ll = Math.hypot(ps[q2][0] - ps[q2 - 1][0], ps[q2][1] - ps[q2 - 1][1]); if (ll > best) { best = ll; li = q2; } }
      var m = ps[li - 1], m2 = ps[li], mid = [(m[0] + m2[0]) / 2, (m[1] + m2[1]) / 2], vert = Math.abs(m2[0] - m[0]) < 1;
      lab = f.label({ text: p.label, cls: 'k2-t-note', at: function () { return mid; }, side: vert ? 'right' : 'up', dist: 10, lead: false,
        show: function () { return clamp(f.get(p.draw, 1) * 3 - 2, 0, 1); } });
    }
    return {
      draw: function () {
        var k = clamp(f.get(p.draw, 1), 0, 1);
        line.setAttribute('stroke-dasharray', k.toFixed(4) + ' 1'); setOp(head, clamp(k * 8 - 7, 0, 1));
      }
    };
  });

  /* token - a glowing dot that travels the arrows in order, the way a case goes through a process.
     {route: [arrow ids], at: "@t" - 0 at the start of the first, k at the end of the k-th} */
  define('token', function (f, p) {
    var legs = (p.route || []).map(function (id) {
      var ps = f.routes[id], L = 0, seg = [];
      for (var i = 1; i < ps.length; i++) { var l = Math.hypot(ps[i][0] - ps[i - 1][0], ps[i][1] - ps[i - 1][1]); seg.push([ps[i - 1], ps[i], L, l]); L += l; }
      return { seg: seg, L: L };
    });
    var glow = el('circle', { r: 22, 'class': 'k2-marker-glow' }, f.L.front), dot = el('circle', { r: 10, 'class': 'k2-marker' }, f.L.front);
    function where(t) {
      var i = clamp(Math.floor(t), 0, legs.length - 1), fr = clamp(t - i, 0, 1), lg = legs[i], d = fr * lg.L;
      for (var j = 0; j < lg.seg.length; j++) { var s2 = lg.seg[j]; if (d <= s2[2] + s2[3] || j === lg.seg.length - 1) { var u = (d - s2[2]) / (s2[3] || 1); return [lerp(s2[0][0], s2[1][0], u), lerp(s2[0][1], s2[1][1], u)]; } }
      return [0, 0];
    }
    return {
      draw: function () {
        var t = f.get(p.at, 0), q = where(t), on = clamp(f.get(p.show, t > 0.001 ? 1 : 0), 0, 1);
        [glow, dot].forEach(function (c) { c.setAttribute('cx', q[0].toFixed(1)); c.setAttribute('cy', q[1].toFixed(1)); });
        setOp(dot, on); setOp(glow, on * 0.45);
      }
    };
  });

  /* a box's words on as many lines as its width needs, centred on (x, y) - at the type's grown size (run from a fit) */
  function wrapText(t, text, x, y, room) {
    var words = String(text || '').split(/\s+/), rows = [], cur = '', probe;
    t.textContent = '';
    probe = el('tspan', {}, t);
    words.forEach(function (wd) {
      var q = cur ? cur + ' ' + wd : wd;
      probe.textContent = q;
      if (cur && probe.getComputedTextLength() > room) { rows.push(cur); cur = wd; } else { cur = q; }
    });
    if (cur) { rows.push(cur); }
    t.removeChild(probe);
    var fs = parseFloat(w.getComputedStyle(t).fontSize) || 16, y0 = y - (rows.length - 1) * fs * 0.58 + fs * 0.34;
    rows.forEach(function (r, i) { el('tspan', { x: x, y: (y0 + i * fs * 1.16).toFixed(1) }, t, r); });
    return rows.length;
  }
  function holds(g, shape) { g.setAttribute('data-k2-holds', ''); shape.setAttribute('data-k2-shape', ''); }

  /* bars - a value for each thing, side by side: the bars grow in one after another, one can be picked out, a target
     line can cross them. {x, y, w, h, items: [{label, value, cat}], max, step, unit, decimals, grow: "@g", pick: "@p"
     (k picks out the k-th, 0 none), target: {value, label, show}} */
  define('bars', function (f, p) {
    var It = p.items || [], n = It.length, x0 = p.x, y0 = p.y, W = p.w, H = p.h, mx = p.max || 1, g = el('g', {}, f.L.back), v;
    var Y = function (val) { return y0 + H - clamp(val / mx, 0, 1.05) * H; }, ty = [];
    for (v = 0; v <= mx + 1e-9; v += (p.step || mx / 4)) {
      el('line', { x1: x0, y1: Y(v), x2: x0 + W, y2: Y(v), 'class': 'k2-grid' }, g);
      ty.push({ n: el('text', { x: x0 - 12, y: Y(v) + 5, 'text-anchor': 'end', 'class': 'k2-t-tick' }, g, num(v, 0)), at: Y(v) });
    }
    f.thin(ty, 'y');
    el('line', { x1: x0, y1: y0 + H, x2: x0 + W, y2: y0 + H, 'class': 'k2-axis' }, g);
    if (p.unit) { el('text', { x: x0 - 12, y: y0 - 18, 'class': 'k2-t-axis' }, g, p.unit); }
    var slot = W / n, bw = Math.min(110, slot * 0.6);
    var bars = It.map(function (it, i) {
      var cx = x0 + slot * (i + 0.5), bg = el('g', {}, f.L.hero), cat = it.cat || (i % 5) + 1;
      var ol = el('rect', { x: cx - bw / 2 - 3, width: bw + 6, rx: 10, 'class': 'k2-outline' }, bg);
      var bar = el('rect', { x: cx - bw / 2, width: bw, rx: 8, fill: f.url('solid-cat-' + cat) }, bg);
      var ed = el('rect', { x: cx - bw / 2, width: bw, rx: 8, 'class': 'k2-edge' }, bg);
      var val = el('text', { x: cx, 'text-anchor': 'middle', 'class': 'k2-t-lbl k2-t-big k2-halo' }, f.L.lbl);
      var lab = el('text', { x: cx, y: y0 + H + 30, 'text-anchor': 'middle', 'class': 'k2-t-lbl k2-halo' }, f.L.lbl, it.label || '');
      return { it: it, bg: bg, ol: ol, bar: bar, ed: ed, val: val, lab: lab, cx: cx };
    });
    (f.fits = f.fits || []).push(function () { bars.forEach(function (b) { wrapText(b.lab, b.it.label, b.cx, y0 + H + 30, slot - 14); }); });
    var tg = p.target ? { line: el('path', { 'class': 'k2-finish' }, f.L.front), t: el('text', { 'class': 'k2-t-note k2-t-amber k2-halo', 'text-anchor': 'end' }, f.L.front, p.target.label || '') } : null;
    f.solid(function () { return { x: x0, y: y0, x2: x0 + W, y2: y0 + H }; });
    var lastPick = f.target(p.pick, 0);
    return {
      onStep: function (n2, instant) {
        var k = Math.round(f.target(p.pick, 0));
        if (!instant && k && k !== lastPick && bars[k - 1]) { var b = bars[k - 1]; f.pulse(b.cx, Y(f.target(b.it.value, 0)), { delay: 300, r: 50 }); }
        lastPick = k;
      },
      draw: function () {
        var gr = clamp(f.get(p.grow, 1), 0, 1), pk = f.get(p.pick, 0);
        bars.forEach(function (b, i) {
          var k = clamp(gr * (n * 0.5 + 1) - i * 0.5, 0, 1), e = k * k * (3 - 2 * k), vv = f.get(b.it.value, 0), top = Y(vv * e), hh = y0 + H - top;
          [b.bar, b.ed].forEach(function (r) { r.setAttribute('y', top.toFixed(1)); r.setAttribute('height', Math.max(0, hh).toFixed(1)); });
          b.ol.setAttribute('y', (top - 3).toFixed(1)); b.ol.setAttribute('height', Math.max(0, hh + 3).toFixed(1)); setOp(b.ol, e > 0.01 ? 1 : 0);
          b.val.textContent = num(vv * e, p.decimals || 0) + (p.suffix || ''); b.val.setAttribute('y', (top - 12).toFixed(1)); setOp(b.val, clamp(e * 2 - 1, 0, 1));
          var on = pk < 0.5 ? 1 : clamp(1 - Math.abs(pk - (i + 1)), 0, 1);
          setOp(b.bg, 0.35 + 0.65 * on); setOp(b.lab, 0.5 + 0.5 * on);
        });
        if (tg) {
          var tv = f.get(p.target.value, 0), yy = Y(tv), so = clamp(f.get(p.target.show, 1), 0, 1);
          tg.line.setAttribute('d', 'M' + x0 + ' ' + yy.toFixed(1) + ' H' + (x0 + W)); setOp(tg.line, so);
          tg.t.setAttribute('x', x0 + W); tg.t.setAttribute('y', (yy - 10).toFixed(1)); setOp(tg.t, so);
        }
      }
    };
  });

  /* pyramid - levels from the top down (a hierarchy of controls, of needs, of command): each comes in as a step
     reaches it, one can be picked out; a side note can run along it ("most effective" .. "least effective").
     {x, y, w, h, levels: [{name, cat}], at: "@k" (levels shown, from the top), pick: "@p", top: text, bottom: text} */
  define('pyramid', function (f, p) {
    var Lv = p.levels || [], n = Lv.length, x0 = p.x, y0 = p.y, W = p.w, H = p.h, gap = 8, bh = (H - gap * (n - 1)) / n, cx = x0 + W / 2;
    function half(yy) { return (yy - y0) / H * W / 2; }
    var bands = Lv.map(function (lv, i) {
      var ya = y0 + i * (bh + gap), yb = ya + bh, a = half(ya), b = half(yb), cat = lv.cat || (i % 5) + 1;
      var d = i === 0 ? 'M' + cx + ' ' + ya + ' L' + (cx + b) + ' ' + yb + ' L' + (cx - b) + ' ' + yb + ' Z'
        : 'M' + (cx - a) + ' ' + ya + ' L' + (cx + a) + ' ' + ya + ' L' + (cx + b) + ' ' + yb + ' L' + (cx - b) + ' ' + yb + ' Z';
      var g = el('g', {}, f.L.hero), inner = el('g', {}, g);
      var lit = el('path', { d: d, 'class': 'k2-lit' }, inner);
      var ol = el('path', { d: d, 'class': 'k2-outline-s', 'stroke-width': 6, 'stroke-linejoin': 'round' }, inner);
      el('path', { d: d, fill: f.url('solid-cat-' + cat) }, inner);
      el('path', { d: d, 'class': 'k2-edge' }, inner);
      var t = el('text', { 'text-anchor': 'middle', 'class': 'k2-t-oncat' }, inner);
      holds(inner, ol);
      return { g: g, inner: inner, lit: lit, t: t, lv: lv, ym: (ya + yb) / 2, room: i === 0 ? b * 0.9 : (a + b) * 0.82, top: i === 0, ya: ya, yb: yb };
    });
    (f.fits = f.fits || []).push(function () {
      bands.forEach(function (b) {
        if (!b.top) { wrapText(b.t, b.lv.name, cx, b.ym, b.room); return; }
        var fs = parseFloat(w.getComputedStyle(b.t).fontSize) || 17, ty = b.yb - fs * 0.9;
        wrapText(b.t, b.lv.name, cx, ty, 2 * half(ty - fs * 0.6) - 16);
      });
    });
    if (p.top || p.bottom) {
      var ax = x0 + W + 34, ar = el('g', {}, f.L.back);
      el('path', { d: 'M' + ax + ' ' + (y0 + H - 6) + ' V' + (y0 + 14), 'class': 'k2-arrow' }, ar);
      el('path', { d: 'M ' + ax + ' ' + (y0 + 4) + ' l -8 14 h 16 Z', 'class': 'k2-arrow-head' }, ar);
      if (p.top) { el('text', { x: ax + 16, y: y0 + 18, 'class': 'k2-t-note k2-halo' }, f.L.lbl, p.top); }
      if (p.bottom) { el('text', { x: ax + 16, y: y0 + H - 4, 'class': 'k2-t-sub k2-halo' }, f.L.lbl, p.bottom); }
    }
    f.solid(function () { return { x: x0, y: y0, x2: x0 + W, y2: y0 + H }; });
    var last = f.target(p.pick, 0);
    return {
      onStep: function (n2, instant) { var k = Math.round(f.target(p.pick, 0)); if (!instant && k && k !== last && bands[k - 1]) { f.pulse(cx, bands[k - 1].ym, { delay: 250, r: 70 }); } last = k; },
      draw: function () {
        var at = f.get(p.at, n), pk = f.get(p.pick, 0);
        bands.forEach(function (b, i) {
          var k = clamp(at - i, 0, 1), e = k * k * (3 - 2 * k);
          b.inner.setAttribute('transform', 'translate(' + cx + ' ' + b.ym + ') scale(' + (0.85 + 0.15 * e).toFixed(3) + ') translate(' + (-cx) + ' ' + (-b.ym) + ')');
          setOp(b.g, e * (pk < 0.5 ? 1 : 0.4 + 0.6 * clamp(1 - Math.abs(pk - (i + 1)), 0, 1)));
          setOp(b.lit, pk < 0.5 ? 0 : clamp(1 - Math.abs(pk - (i + 1)), 0, 1));
        });
      }
    };
  });

  /* balance - two things weighed against each other: the beam tips towards the heavier side on a spring, each pan holds
     its things as blocks. {x, y (the pivot), w (the beam), left: {label, items: [names], weight: "@l"}, right: {...},
     max: the most it tips (degrees, 14)} - a pan shows as many of its items as its weight */
  define('balance', function (f, p) {
    var cx = p.x, cy = p.y, L = (p.w || 520) / 2, mx = p.max || 14;
    var chain = p.chain || Math.max(90, Math.max(((p.left || {}).items || []).length, ((p.right || {}).items || []).length) * 38 + 46);
    f.shadow(cx, cy + 190, 150, 14);
    var post = el('g', {}, f.L.hero);
    var pd = 'M' + (cx - 16) + ' ' + (cy + 182) + ' L' + (cx - 7) + ' ' + (cy + 6) + ' L' + (cx + 7) + ' ' + (cy + 6) + ' L' + (cx + 16) + ' ' + (cy + 182) + ' Z';
    el('path', { d: pd, 'class': 'k2-outline-s', 'stroke-width': 6 }, post); el('path', { d: pd, fill: f.url('metal') }, post);
    var bd = 'M' + (cx - 90) + ' ' + (cy + 196) + ' H' + (cx + 90) + ' L' + (cx + 70) + ' ' + (cy + 180) + ' H' + (cx - 70) + ' Z';
    el('path', { d: bd, 'class': 'k2-outline-s', 'stroke-width': 6 }, post); el('path', { d: bd, fill: f.url('metal') }, post);
    var beam = el('g', {}, f.L.hero);
    el('rect', { x: cx - L - 4, y: cy - 9, width: 2 * L + 8, height: 18, rx: 9, 'class': 'k2-outline' }, beam);
    el('rect', { x: cx - L, y: cy - 6, width: 2 * L, height: 12, rx: 6, fill: f.url('metalv') }, beam);
    el('circle', { cx: cx, cy: cy, r: 13, 'class': 'k2-outline' }, f.L.front); el('circle', { cx: cx, cy: cy, r: 10, fill: f.url('metal') }, f.L.front);
    function pan(side, sgn) {
      var g = el('g', {}, f.L.front), ch = el('path', { 'class': 'k2-chain' }, g), dish = el('g', {}, g), pw = 150;
      var dd = 'M' + (-pw / 2) + ' 0 Q 0 ' + 46 + ' ' + (pw / 2) + ' 0 Z';
      el('path', { d: dd, 'class': 'k2-outline-s', 'stroke-width': 6 }, dish); el('path', { d: dd, fill: f.url('metal') }, dish);
      var blocks = (side.items || []).map(function (nm, i) {
        var bg = el('g', {}, dish), cat = side.cat || (sgn < 0 ? 4 : 2), bwid = pw - 40, bh = 34;
        var r = el('rect', { x: -bwid / 2, y: -(i + 1) * (bh + 4), width: bwid, height: bh, rx: 8, fill: f.url('solid-cat-' + cat) }, bg);
        var o = el('rect', { x: -bwid / 2, y: -(i + 1) * (bh + 4), width: bwid, height: bh, rx: 8, 'class': 'k2-outline-s', 'stroke-width': 3 }, bg);
        var t = el('text', { x: 0, y: -(i + 1) * (bh + 4) + bh / 2, 'text-anchor': 'middle', 'class': 'k2-t-oncat-sub' }, bg);
        holds(bg, o);
        return { g: bg, t: t, nm: nm, y: -(i + 1) * (bh + 4) + bh / 2, room: bwid - 14 };
      });
      var lab = el('text', { 'text-anchor': 'middle', 'class': 'k2-t-lbl k2-t-big k2-halo' }, f.L.lbl, side.label || '');
      return { g: g, ch: ch, dish: dish, blocks: blocks, lab: lab, side: side, sgn: sgn };
    }
    var pans = [pan(p.left || {}, -1), pan(p.right || {}, 1)];
    (f.fits = f.fits || []).push(function () { pans.forEach(function (q) { q.blocks.forEach(function (b) { wrapText(b.t, b.nm, 0, b.y, b.room); }); }); });
    var ang = new Spring(0), moving = false;
    function tilt(to) { var l = to ? f.target(p.left && p.left.weight, 0) : f.get(p.left && p.left.weight, 0), r = to ? f.target(p.right && p.right.weight, 0) : f.get(p.right && p.right.weight, 0); return clamp((r - l) * (p.k || 5), -mx, mx); }
    f.solid(function () { return { x: cx - L - 80, y: cy - 30, x2: cx + L + 80, y2: cy + chain + 60 }; });
    return {
      draw: function (dt, snap) {
        moving = ang.go(tilt(true), dt, snap);
        var a = ang.x * Math.PI / 180;
        beam.setAttribute('transform', 'rotate(' + ang.x.toFixed(2) + ' ' + cx + ' ' + cy + ')');
        pans.forEach(function (q) {
          var ex = cx + q.sgn * L * Math.cos(a), ey = cy + q.sgn * L * Math.sin(a), py = ey + chain;
          q.ch.setAttribute('d', 'M' + ex.toFixed(1) + ' ' + ey.toFixed(1) + ' L' + (ex - 74).toFixed(1) + ' ' + py.toFixed(1) + ' M' + ex.toFixed(1) + ' ' + ey.toFixed(1) + ' L' + (ex + 74).toFixed(1) + ' ' + py.toFixed(1));
          q.dish.setAttribute('transform', 'translate(' + ex.toFixed(1) + ' ' + py.toFixed(1) + ')');
          var wgt = f.get(q.side.weight, 0);
          q.blocks.forEach(function (b, i) { var k = clamp(wgt - i, 0, 1); setOp(b.g, k); b.g.setAttribute('transform', 'translate(0 ' + ((1 - k) * -30).toFixed(1) + ')'); });
          q.lab.setAttribute('x', ex.toFixed(1)); q.lab.setAttribute('y', (py + 76).toFixed(1));
        });
      },
      live: function () { return moving; }
    };
  });

  /* events - things that happened along a time line: each comes in as the cursor reaches it, above and below the
     line in turn. {x, y, w, start, end, step, tick: "{v}", events: [{at, label, sub, cat}], cursor: "@t", cursorTag: "{v}"} */
  define('events', function (f, p) {
    var x0 = p.x, y0 = p.y, W = p.w, t0 = p.start, t1 = p.end, E = p.events || [], g = el('g', {}, f.L.back), t, ticks = [];
    function X(tt) { return x0 + (tt - t0) / (t1 - t0) * W; }
    el('rect', { x: x0 - 6, y: y0 - 5, width: W + 12, height: 10, rx: 5, 'class': 'k2-outline' }, g);
    el('rect', { x: x0 - 4, y: y0 - 3, width: W + 8, height: 6, rx: 3, fill: f.url('metalv') }, g);
    var done = el('rect', { x: x0 - 4, y: y0 - 3, height: 6, rx: 3, 'class': 'k2-done-line' }, g);
    for (t = t0; t <= t1 + 1e-9; t += (p.step || 1)) {
      el('line', { x1: X(t), y1: y0 + 8, x2: X(t), y2: y0 + 16, 'class': 'k2-axis' }, g);
      ticks.push({ n: el('text', { x: X(t), y: y0 + 36, 'text-anchor': 'middle', 'class': 'k2-t-tick' }, g, tpl(p.tick || '{v}', { v: t }, 0)), at: X(t) });
    }
    f.thin(ticks, 'x');
    var evs = E.map(function (e, i) {
      var up = i % 2 === 0, ex = X(e.at), len = p.stem || 92, cat = e.cat || (i % 5) + 1, eg = el('g', {}, f.L.front);
      el('path', { d: 'M' + ex + ' ' + y0 + ' V' + (y0 + (up ? -len : len)), 'class': 'k2-stem' }, eg);
      el('circle', { cx: ex, cy: y0, r: 11, 'class': 'k2-outline' }, eg);
      el('circle', { cx: ex, cy: y0, r: 8, fill: f.url('solid-cat-' + cat) }, eg);
      var tg = el('g', { 'text-anchor': 'middle' }, eg), ty = y0 + (up ? -len - 12 : len + 24);
      el('text', { x: ex, y: ty - (up && e.sub ? 22 : 0), 'class': 'k2-t-lbl k2-halo' }, tg, e.label || '');
      if (e.sub) { el('text', { x: ex, y: ty + (up ? 0 : 22), 'class': 'k2-t-sub k2-halo' }, tg, e.sub); }
      return { e: e, g: eg, x: ex, y: ty };
    });
    var cur = el('g', {}, f.L.front), cg = el('circle', { r: 22, 'class': 'k2-marker-glow' }, cur), cm = el('circle', { r: 10, 'class': 'k2-marker' }, cur);
    var ctag = p.cursorTag ? el('text', { 'text-anchor': 'middle', 'class': 'k2-t-note k2-halo' }, cur) : null;
    f.solid(function () { return { x: x0, y: y0 - 8, x2: x0 + W, y2: y0 + 40 }; });
    var seen = {};
    return {
      draw: function () {
        var tc = f.get(p.cursor, t1), cx2 = X(clamp(tc, t0, t1)), on = tc > t0 + 1e-6 ? 1 : 0;
        done.setAttribute('width', Math.max(0, cx2 - x0 + 4).toFixed(1));
        [cg, cm].forEach(function (c) { c.setAttribute('cx', cx2.toFixed(1)); c.setAttribute('cy', y0); });
        setOp(cur, on);
        if (ctag) { ctag.textContent = tpl(p.cursorTag, { v: tc }, 0); ctag.setAttribute('x', cx2.toFixed(1)); ctag.setAttribute('y', y0 + 60); }
        evs.forEach(function (o, i) {
          var k = clamp((tc - o.e.at) / ((t1 - t0) * 0.03) + 1, 0, 1);
          setOp(o.g, k); o.g.setAttribute('transform', 'translate(0 ' + ((1 - k) * (i % 2 ? 14 : -14)).toFixed(1) + ')');
          if (k > 0.5 && !seen[i]) { seen[i] = 1; f.pulse(o.x, y0, { r: 34 }); } else if (k < 0.1) { seen[i] = 0; }
        });
      }
    };
  });

  /* compare - two or three things side by side, row by row (gas safe / ESD-protected, before / after): each row comes
     in as a step reaches it, a tick or a cross where the row says. {x, y, w, h, cols: [{title, cat}], rows: [{cells:
     [text, text], marks: [1, 0] (1 a tick, 0 a cross, null none)}], at: "@r" (rows shown)} */
  define('compare', function (f, p) {
    var C = p.cols || [], R = p.rows || [], x0 = p.x, y0 = p.y, W = p.w, H = p.h, nc = C.length, cw = (W - 16 * (nc - 1)) / nc, hh = 58;
    var rh = Math.min(p.rowH || 96, (H - hh - 12) / Math.max(1, R.length));
    C.forEach(function (c, j) {
      var x = x0 + j * (cw + 16), hg = el('g', {}, f.L.hero), cat = c.cat || j * 2 + 1;
      var o = el('rect', { x: x, y: y0, width: cw, height: hh, rx: 14, 'class': 'k2-outline-s', 'stroke-width': 5 }, hg);
      el('rect', { x: x, y: y0, width: cw, height: hh, rx: 14, fill: f.url('solid-cat-' + cat) }, hg);
      el('text', { x: x + cw / 2, y: y0 + hh / 2 + 7, 'text-anchor': 'middle', 'class': 'k2-t-oncat' }, hg, c.title || '');
      holds(hg, o);
    });
    var rows = R.map(function (r, i) {
      var y = y0 + hh + 12 + i * rh, rg = el('g', {}, f.L.front), cells = [];
      (r.cells || []).forEach(function (txt, j) {
        var x = x0 + j * (cw + 16), cg = el('g', {}, rg), mk = r.marks ? r.marks[j] : null;
        var o = el('rect', { x: x, y: y, width: cw, height: rh - 10, rx: 12, 'class': 'k2-cell' }, cg);
        var t = el('text', { 'text-anchor': 'middle', 'class': 'k2-t-lbl' }, cg);
        if (mk === 1 || mk === 0) {
          var ix = x + 30, iy = y + (rh - 10) / 2;
          el('circle', { cx: ix, cy: iy, r: 14, 'class': mk ? 'k2-mark-good' : 'k2-mark-warn' }, cg);
          el('path', { d: mk ? 'M' + (ix - 7) + ' ' + iy + ' l 5 5 l 9 -10' : 'M' + (ix - 6) + ' ' + (iy - 6) + ' l 12 12 M' + (ix + 6) + ' ' + (iy - 6) + ' l -12 12', 'class': 'k2-mark-ink' }, cg);
        }
        holds(cg, o);
        cells.push({ t: t, txt: txt, x: x + cw / 2 + (mk === 1 || mk === 0 ? 18 : 0), y: y + (rh - 10) / 2, room: cw - (mk === 1 || mk === 0 ? 70 : 28) });
      });
      return { g: rg, cells: cells, y: y };
    });
    (f.fits = f.fits || []).push(function () { rows.forEach(function (r) { r.cells.forEach(function (c) { wrapText(c.t, c.txt, c.x, c.y, c.room); }); }); });
    f.solid(function () { return { x: x0, y: y0, x2: x0 + W, y2: y0 + H }; });
    return {
      draw: function () {
        var at = f.get(p.at, R.length);
        rows.forEach(function (r, i) { var k = clamp(at - i, 0, 1), e = k * k * (3 - 2 * k); setOp(r.g, e); r.g.setAttribute('transform', 'translate(0 ' + ((1 - e) * 16).toFixed(1) + ')'); });
      }
    };
  });

  /* person - someone in the story (a role at work: master, officer, sponsor), drawn simply with depth, a name under
     them, and what they say in a bubble that a step brings in. {x, y (feet), scale, name, role, cat, say, sayShow,
     side: "right" | "left" (where the bubble goes), show, lit} */
  define('person', function (f, p) {
    var x = p.x, y = p.y, k = p.scale || 1, cat = p.cat || 1, g = el('g', {}, f.L.hero), inner = el('g', {}, g);
    var body = 'M' + (x - 46 * k) + ' ' + y + ' Q' + (x - 46 * k) + ' ' + (y - 92 * k) + ' ' + x + ' ' + (y - 96 * k) + ' Q' + (x + 46 * k) + ' ' + (y - 92 * k) + ' ' + (x + 46 * k) + ' ' + y + ' Z';
    f.shadow(x, y + 4, 60 * k, 10);
    var lit = el('path', { d: body, 'class': 'k2-lit' }, inner);
    el('path', { d: body, 'class': 'k2-outline-s', 'stroke-width': 6 }, inner);
    el('path', { d: body, fill: f.url('solid-cat-' + cat) }, inner);
    el('path', { d: body, 'class': 'k2-edge' }, inner);
    el('circle', { cx: x, cy: y - 126 * k, r: 30 * k, 'class': 'k2-outline' }, inner);
    el('circle', { cx: x, cy: y - 126 * k, r: 27 * k, 'class': 'k2-skin' }, inner);
    el('circle', { cx: x - 8 * k, cy: y - 134 * k, r: 9 * k, 'class': 'k2-skin-hi' }, inner);
    var nm = el('g', { 'text-anchor': 'middle' }, f.L.lbl);
    el('text', { x: x, y: y + 30, 'class': 'k2-t-lbl k2-halo' }, nm, p.name || '');
    if (p.role) { el('text', { x: x, y: y + 52, 'class': 'k2-t-sub k2-halo' }, nm, p.role); }
    var bub = null;
    if (p.say) {
      var up = p.side === 'up', right = p.side !== 'left', bw = p.bubbleW || 260, bh = p.bubbleH || 84;
      var bx = up ? x - bw / 2 : right ? x + 50 * k : x - 50 * k - bw, by = up ? y - 170 * k - bh - 30 : y - 190 * k - bh / 2;
      var tx = up ? x + 8 : right ? bx + 26 : bx + bw - 26;
      var bd = 'M' + (bx + 14) + ' ' + by + ' H' + (bx + bw - 14) + ' Q' + (bx + bw) + ' ' + by + ' ' + (bx + bw) + ' ' + (by + 14) + ' V' + (by + bh - 14) +
        ' Q' + (bx + bw) + ' ' + (by + bh) + ' ' + (bx + bw - 14) + ' ' + (by + bh) + ' H' + (tx + 14) + ' L' + (up ? x : right ? x + 18 * k : x - 18 * k) + ' ' + (by + bh + 26) + ' L' + (tx - 4) + ' ' + (by + bh) +
        ' H' + (bx + 14) + ' Q' + bx + ' ' + (by + bh) + ' ' + bx + ' ' + (by + bh - 14) + ' V' + (by + 14) + ' Q' + bx + ' ' + by + ' ' + (bx + 14) + ' ' + by + ' Z';
      bub = el('g', {}, f.L.front);
      var bo = el('path', { d: bd, 'class': 'k2-outline-s', 'stroke-width': 5, 'stroke-linejoin': 'round' }, bub);
      el('path', { d: bd, 'class': 'k2-bubble' }, bub);
      var bt = el('text', { 'text-anchor': 'middle', 'class': 'k2-t-face' }, bub);
      holds(bub, bo);
      (f.fits = f.fits || []).push(function () { wrapText(bt, p.say, bx + bw / 2, by + bh / 2, bw - 30); });
      f.solid(function () { return { x: bx, y: by, x2: bx + bw, y2: by + bh + 26 }; });
      bub.__o = [bx + bw / 2, by + bh];
    }
    f.solid(function () { return { x: x - 50 * k, y: y - 160 * k, x2: x + 50 * k, y2: y + 56 }; });
    var sp = new Spring(f.target(p.sayShow, 1)), moving = false;
    return {
      draw: function (dt, snap) {
        setOp(g, f.get(p.show, 1)); setOp(nm, f.get(p.show, 1)); setOp(lit, clamp(f.get(p.lit, 0), 0, 1));
        if (bub) {
          moving = sp.go(f.target(p.sayShow, 1), dt, snap);
          var s2 = clamp(f.get(p.sayShow, 1), 0, 1), sc = 0.6 + 0.4 * Math.max(0, sp.x), o = bub.__o;
          bub.setAttribute('transform', 'translate(' + o[0] + ' ' + o[1] + ') scale(' + sc.toFixed(3) + ') translate(' + (-o[0]) + ' ' + (-o[1]) + ')'); setOp(bub, s2);
        }
      },
      live: function () { return moving; }
    };
  });

  /* tank - a tank cut open: its walls hatched, the liquid in it rising and falling with its level, a scale beside it
     and the level read on a tag. {x, y, w, h, level: "@l" (0..1), label, scale: true, unit: "%"} - publishes level */
  define('tank', function (f, p) {
    var x = p.x, y = p.y, W = p.w || 200, H = p.h || 300, wall = 14, r = Math.min(40, W / 4);
    var outer = 'M' + x + ' ' + (y + r) + ' Q' + x + ' ' + y + ' ' + (x + r) + ' ' + y + ' H' + (x + W - r) + ' Q' + (x + W) + ' ' + y + ' ' + (x + W) + ' ' + (y + r) +
      ' V' + (y + H - r) + ' Q' + (x + W) + ' ' + (y + H) + ' ' + (x + W - r) + ' ' + (y + H) + ' H' + (x + r) + ' Q' + x + ' ' + (y + H) + ' ' + x + ' ' + (y + H - r) + ' Z';
    var ix = x + wall, iy = y + wall, iw = W - 2 * wall, ih = H - 2 * wall, ir = Math.max(6, r - wall);
    var inner = 'M' + ix + ' ' + (iy + ir) + ' Q' + ix + ' ' + iy + ' ' + (ix + ir) + ' ' + iy + ' H' + (ix + iw - ir) + ' Q' + (ix + iw) + ' ' + iy + ' ' + (ix + iw) + ' ' + (iy + ir) +
      ' V' + (iy + ih - ir) + ' Q' + (ix + iw) + ' ' + (iy + ih) + ' ' + (ix + iw - ir) + ' ' + (iy + ih) + ' H' + (ix + ir) + ' Q' + ix + ' ' + (iy + ih) + ' ' + ix + ' ' + (iy + ih - ir) + ' Z';
    f.shadow(x + W / 2, y + H + 10, W * 0.7, 14);
    el('path', { d: inner, 'class': 'k2-cavity' }, f.L.back);
    var cid = f.id + '-tk' + (++UID), clip = el('clipPath', { id: cid }, f.defs);
    el('path', { d: inner }, clip);
    var liq = el('rect', { x: ix, width: iw, fill: f.band('liquid', iy, iy + ih), 'clip-path': 'url(#' + cid + ')' }, f.L.contents);
    var surf = el('line', { x1: ix + 2, x2: ix + iw - 2, 'class': 'k2-surface', 'clip-path': 'url(#' + cid + ')' }, f.L.contents);
    el('path', { d: outer, 'class': 'k2-outline-s', 'stroke-width': 6 }, f.L.hero);
    el('path', { d: outer + ' ' + inner, 'fill-rule': 'evenodd', fill: f.url('metal') }, f.L.hero);
    el('path', { d: outer + ' ' + inner, 'fill-rule': 'evenodd', fill: f.url('hatch') }, f.L.hero);
    el('path', { d: outer, 'class': 'k2-edge' }, f.L.hero);
    var tag = el('g', {}, f.L.front), tr = el('rect', { rx: 8, height: 30, 'class': 'k2-tag' }, tag), tt = el('text', { 'dominant-baseline': 'central', 'class': 'k2-t-tag' }, tag);
    if (p.scale !== false) {
      var sg = el('g', {}, f.L.back), sx = x + W + 14;
      for (var q = 0; q <= 4; q++) { var yy = iy + ih - q / 4 * ih; el('line', { x1: sx, y1: yy, x2: sx + (q % 2 ? 8 : 14), y2: yy, 'class': 'k2-axis' }, sg); }
    }
    if (p.label) { f.label({ text: p.label, sub: p.sub, at: function () { return [x + W / 2, y]; }, side: 'up', dist: 14 }); }
    f.solid(function () { return { x: x - 4, y: y - 4, x2: x + W + 4, y2: y + H + 4 }; });
    return {
      calc: function () { f.publish(p.id, 'level', clamp(f.get(p.level, 0), 0, 1)); },
      draw: function () {
        var lv = clamp(f.get(p.level, 0), 0, 1), top = iy + ih * (1 - lv);
        liq.setAttribute('y', top.toFixed(1)); liq.setAttribute('height', (ih * lv + 1).toFixed(1));
        surf.setAttribute('y1', top.toFixed(1)); surf.setAttribute('y2', top.toFixed(1)); setOp(surf, lv > 0.01 && lv < 0.99 ? 1 : 0);
        tt.textContent = num(lv * 100, 0) + ' ' + (p.unit || '%');
        var bb = tt.getBBox(), tw = bb.width + 18, th = Math.max(30, bb.height + 8);
        tr.setAttribute('width', tw.toFixed(1)); tr.setAttribute('height', th.toFixed(1)); tt.setAttribute('x', 9); tt.setAttribute('y', (th / 2).toFixed(1));
        tag.setAttribute('transform', 'translate(' + (x + W + 30) + ' ' + (top - th / 2).toFixed(1) + ')');
      }
    };
  });

  /* pump - a centrifugal pump cut open: the volute casing hatched, the impeller turning as fast as its speed (it stops
     when the speed is 0), the eye where the liquid comes in. Publishes flow = speed. {x, y (the shaft), r, speed: "@s",
     label, sub, vanes} */
  define('pump', function (f, p) {
    var cx = p.x, cy = p.y, R = p.r || 90, i, d = '', N = 48;
    for (i = 0; i <= N; i++) {                    /* the volute: a spiral that widens over one turn, then the outlet */
      var a = -Math.PI / 2 + i / N * 2 * Math.PI, rr = R * (1 + 0.32 * i / N);
      d += (i ? ' L' : 'M') + pt([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]);
    }
    var R2 = R * 1.32, casing = d + ' L' + pt([cx + R2 * 1.25, cy - R2]) + ' L' + pt([cx + R2 * 1.25, cy - R2 * 0.55]) + ' L' + pt([cx + R * 0.95, cy - R * 0.32]);
    f.shadow(cx, cy + R2 + 18, R2 * 1.1, 14);
    var base = 'M' + (cx - R2 * 0.9) + ' ' + (cy + R2 + 14) + ' H' + (cx + R2 * 0.9) + ' L' + (cx + R2 * 0.6) + ' ' + (cy + R * 0.6) + ' H' + (cx - R2 * 0.6) + ' Z';
    el('path', { d: base, 'class': 'k2-outline-s', 'stroke-width': 6 }, f.L.back); el('path', { d: base, fill: f.url('metal') }, f.L.back);
    el('path', { d: casing + ' Z', 'class': 'k2-outline' }, f.L.hero);
    el('path', { d: casing + ' Z', fill: f.url('metal') }, f.L.hero);
    el('path', { d: casing + ' Z', fill: f.url('hatch') }, f.L.hero);
    el('circle', { cx: cx, cy: cy, r: R * 1.06, fill: f.url('liquid') }, f.L.hero);
    el('path', { d: casing + ' Z', 'class': 'k2-edge' }, f.L.hero);
    var imp = el('g', {}, f.L.hero), nv = p.vanes || 6;
    el('circle', { cx: cx, cy: cy, r: R * 0.82, 'class': 'k2-outline' }, imp);
    el('circle', { cx: cx, cy: cy, r: R * 0.78, fill: f.url('metal') }, imp);
    for (i = 0; i < nv; i++) {
      var a0 = i / nv * 2 * Math.PI, p1 = [cx + R * 0.22 * Math.cos(a0), cy + R * 0.22 * Math.sin(a0)], p2 = [cx + R * 0.74 * Math.cos(a0 + 0.9), cy + R * 0.74 * Math.sin(a0 + 0.9)];
      var c1 = [cx + R * 0.55 * Math.cos(a0 + 0.15), cy + R * 0.55 * Math.sin(a0 + 0.15)];
      el('path', { d: 'M' + pt(p1) + ' Q' + pt(c1) + ' ' + pt(p2), 'class': 'k2-vane' }, imp);
    }
    el('circle', { cx: cx, cy: cy, r: R * 0.2, 'class': 'k2-outline' }, imp);
    el('circle', { cx: cx, cy: cy, r: R * 0.17, fill: f.url('liquid') }, imp);
    el('circle', { cx: cx, cy: cy, r: R * 0.07, 'class': 'k2-hub' }, f.L.front);
    if (p.label) { f.label({ text: p.label, sub: p.sub, at: function () { return [cx - R2 * 0.7, cy - R2 * 0.7]; }, side: 'upleft', dist: 20 }); }
    f.solid(function () { return { x: cx - R2, y: cy - R2 - 4, x2: cx + R2 * 1.3, y2: cy + R2 + 16 }; });
    var ang = 0, sp = 0;
    return {
      calc: function () { sp = clamp(f.get(p.speed, 0), 0, 1); f.publish(p.id, 'flow', sp); f.publish(p.id, 'speed', sp); },
      draw: function (dt) { ang = (ang + sp * (p.rpm || 220) * (dt || 0)) % 360; imp.setAttribute('transform', 'rotate(' + ang.toFixed(1) + ' ' + cx + ' ' + cy + ')'); },
      live: function () { return sp > 0.001 && !f.hidden; }
    };
  });

  /* ------------------------------------------------------------------------------------------------ in a deck */
  function hook(id, fns) {
    if (!id) { return; }
    var H = w.GB_HOOKS = w.GB_HOOKS || {}, old = H[id] || {}, cur = {};
    cur.enter = function () { if (old.enter) { old.enter.apply(this, arguments); } if (fns.enter) { fns.enter(); } };
    cur.leave = function () { if (old.leave) { old.leave.apply(this, arguments); } if (fns.leave) { fns.leave(); } };
    cur.step = function (dir) { if (old.step && old.step(dir)) { return true; } return !!(fns.step && fns.step(dir)); };
    H[id] = cur;
  }
  function deck(f, slide) {
    f.onStep = function (n) {
      [].forEach.call(slide.querySelectorAll('[data-i]'), function (x) { x.classList.remove('cur', 'lit'); });
      for (var i = 0; i <= n; i++) {
        [].concat(f.steps[i].line == null ? [] : f.steps[i].line).forEach(function (k) {
          var line = slide.querySelector('[data-i="' + k + '"]'); if (line) { line.classList.add(i === n ? 'cur' : 'lit'); }
        });
      }
    };
    f.hide();
    hook(slide.id, {
      enter: function () { f.goStep(0, true); f.show(); f.resize(); },
      leave: function () { f.hide(); },
      step: function (dir) {
        if (dir > 0 && f.step < f.steps.length - 1) { f.next(); return true; }
        if (dir < 0 && f.step > 0) { f.prev(); return true; }
        return false;
      }
    });
  }
  function shown(n, svg) {
    var o = 1;
    for (var x = n; x && x !== svg; x = x.parentNode) {
      if (x.style && x.style.display === 'none') { return 0; }
      var a = x.getAttribute && x.getAttribute('opacity'); if (a != null) { o *= +a; }
      if (x.style && x.style.opacity !== '') { o *= +x.style.opacity; }
    }
    return o;
  }
  /* every word on the figure as it stands now: no two overlap, none is cut by the picture's edge, no label lies on a
     line. Returns the findings in plain words (an empty list is clean). The demo checks and the studio call it at
     the end of every step. */
  function audit(f) {
    var svg = f.svg, sr = svg.getBoundingClientRect(), found = [], vb = svg.viewBox.baseVal, k = Math.min(sr.width / vb.width, sr.height / vb.height);
    var ox = sr.left + (sr.width - vb.width * k) / 2, oy = sr.top + (sr.height - vb.height * k) / 2;
    var T = [].filter.call(svg.querySelectorAll('text'), function (t) { return t.textContent.trim() && shown(t, svg) > 0.15; }).map(function (t) {
      var r = t.getBoundingClientRect(), ih = r.height * 0.2;
      return { t: t, w: t.textContent.trim().slice(0, 30), x: r.left, y: r.top + ih, x2: r.right, y2: r.bottom - ih, lbl: !!(t.closest && t.closest('.k2-lbl')) };
    });
    T.forEach(function (a, i) {
      if (a.x < ox - 1 || a.y < oy - 1 || a.x2 > ox + vb.width * k + 1 || a.y2 > oy + vb.height * k + 1) { found.push('words cut at the edge: "' + a.w + '"'); }
      for (var j = i + 1; j < T.length; j++) {
        var b = T[j], w = Math.min(a.x2, b.x2) - Math.max(a.x, b.x), h = Math.min(a.y2, b.y2) - Math.max(a.y, b.y);
        if (w > 1.5 && h > 1.5) { found.push('words over words: "' + a.w + '" and "' + b.w + '"'); }
      }
    });
    [].forEach.call(svg.querySelectorAll('.k2-arrow, .k2-dep, .k2-curve, .k2-axis, .k2-trail, .k2-pt-ghost'), function (ln) {
      if (shown(ln, svg) < 0.15 || !ln.getTotalLength) { return; }
      var L = ln.getTotalLength(), m = ln.getScreenCTM(), d0 = ln.getAttribute('stroke-dasharray'), drawn = d0 && /^[\d.]+ 1$/.test(d0) ? +d0.split(' ')[0] : 1;
      if (!m) { return; }
      T.forEach(function (a) {
        if (!a.lbl) { return; }
        for (var s2 = 0; s2 <= L * drawn; s2 += 3) {
          var q = ln.getPointAtLength(s2), X = q.x * m.a + q.y * m.c + m.e, Y = q.x * m.b + q.y * m.d + m.f;
          if (X > a.x + 1 && X < a.x2 - 1 && Y > a.y + 1 && Y < a.y2 - 1) { found.push('words on a line: "' + a.w + '"'); break; }
        }
      });
    });
    [].forEach.call(svg.querySelectorAll('[data-k2-holds]'), function (g) {
      var sh = g.querySelector('[data-k2-shape]');
      if (!sh || shown(g, svg) < 0.15) { return; }
      var m = sh.getScreenCTM(), inv = m && m.inverse();
      [].forEach.call(g.querySelectorAll('text'), function (t) {
        if (!t.textContent.trim() || !inv) { return; }
        [].forEach.call(t.getClientRects().length > 1 ? t.querySelectorAll('tspan') : [t], function (row) {
          var r = row.getBoundingClientRect(), ih = r.height * 0.2, bad = false;
          [[r.left + 1, r.top + ih], [r.right - 1, r.top + ih], [r.left + 1, r.bottom - ih], [r.right - 1, r.bottom - ih]].forEach(function (c) {
            var q = svg.createSVGPoint(); q.x = c[0]; q.y = c[1]; q = q.matrixTransform(inv);
            if (sh.isPointInFill && !sh.isPointInFill(q)) { bad = true; }
          });
          if (bad) { found.push('words spill out of their box: "' + t.textContent.trim().slice(0, 30) + '"'); }
        });
      });
    });
    var boxes = [].filter.call(svg.querySelectorAll('[data-k2-holds]'), function (g) { return shown(g, svg) > 0.15; }).map(function (g) {
      var r = g.querySelector('[data-k2-shape]').getBoundingClientRect(); return { g: g, x: r.left, y: r.top, x2: r.right, y2: r.bottom };
    });
    boxes.forEach(function (a, i) {
      for (var j = i + 1; j < boxes.length; j++) {
        var b = boxes[j];
        if (a.g.contains(b.g) || b.g.contains(a.g)) { continue; }
        if (Math.min(a.x2, b.x2) - Math.max(a.x, b.x) > 4 && Math.min(a.y2, b.y2) - Math.max(a.y, b.y) > 4) {
          found.push('boxes on each other: "' + (a.g.textContent || '').trim().slice(0, 24) + '" and "' + (b.g.textContent || '').trim().slice(0, 24) + '"');
        }
      }
    });
    /* a shape in the hero or the front layer cut by the picture's edge (a pipe that runs on off the picture is drawn in
       the back on purpose) */
    [].forEach.call(svg.querySelectorAll('.k2-l-hero *, .k2-l-front *'), function (n) {
      if (!n.getBBox || /^(g|tspan|stop)$/i.test(n.tagName) || shown(n, svg) < 0.15 || n.classList.contains('k2-hit')) { return; }
      var r = n.getBoundingClientRect();
      if (r.width && (r.left < ox - 2 || r.top < oy - 2 || r.right > ox + vb.width * k + 2 || r.bottom > oy + vb.height * k + 2)) {
        found.push('a shape cut at the edge: ' + n.tagName + (n.getAttribute('class') ? '.' + n.getAttribute('class').split(' ')[0] : ''));
      }
    });
    return found.filter(function (x, i, A) { return A.indexOf(x) === i; });
  }
  function mount(host, spec) { var f = new Fig(host, spec); figs.push(f); return f; }
  function auto() {
    [].forEach.call(d.querySelectorAll('[data-kit2d]'), function (host) {
      if (host.__k2) { return; }
      var ref = host.getAttribute('data-kit2d'), node = ref.charAt(0) === '#' ? d.getElementById(ref.slice(1)) : null, spec;
      try { spec = JSON.parse(node ? node.textContent : ref); } catch (e) { spec = null; }
      if (!spec) { host.__k2 = 'bad'; if (w.console) { w.console.warn('KIT2D: no spec for ' + ref); } return; }
      try { host.__k2 = mount(host, spec); }
      catch (err) { host.__k2 = 'bad'; host.textContent = 'This figure could not be drawn: ' + (err.message || err); if (w.console) { w.console.error(err); } return; }
      var slide = host.closest ? host.closest('.slide') : null;
      if (slide && slide.id) { deck(host.__k2, slide); }
    });
  }
  w.KIT2D = { mount: mount, define: define, types: TYPES, figures: figs, audit: audit,
    h: { el: el, clamp: clamp, lerp: lerp, approach: approach, num: num, tpl: tpl, pt: pt, poly: poly, setOp: setOp, textLines: textLines } };
  if (d.readyState === 'loading') { d.addEventListener('DOMContentLoaded', auto); } else { setTimeout(auto, 0); }
}(window));
