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
  /* words that change with the story: a plain text, or {"pick": "@k", "of": [texts]} - the k-th (from 0) as the state is */
  function pick(f, v) {
    if (!v || typeof v !== 'object' || !v.of) { return v == null ? '' : String(v); }
    return String(v.of[clamp(Math.round(f.target(v.pick, 0)), 0, v.of.length - 1)] || '');
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
      f.frame(!f.sized);                            /* the first size jumps to the step; a later one (a step title wrapping) lets it play on */
      f.sized = true;
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
          var u = d.createElement('i'); u.textContent = o.words ? '' : o.unit || ''; box.appendChild(u);
          return { o: o, b: b };
        });
      }
    },
    syncControls: function () { (this.ctl || []).forEach(function (c) { c.sync(); }); },
    readouts: function () {
      var f = this;
      (f.reads || []).forEach(function (r) {
        var v = f.get(r.o.value, 0), W = r.o.words;                /* words: ["Closed", "Open"] - the value picks one */
        r.b.textContent = W ? W[clamp(Math.round(v), 0, W.length - 1)] : num(v * (r.o.scale || 1), r.o.decimals);
      });
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
     {on: chart, curve, x: "@speed", tagx: "{x} kn" (false: none), tagy: "{y} t/day", drag: "speed", show, ghost: {x, show, label}} */
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
    if (p.tagx === false) { tx.g.style.display = 'none'; }        /* a second point at the same x: one x tag is enough */
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
        if (p.tagx !== false) { tx.set(tpl(p.tagx || '{x}', { x: x }, p.dx == null ? 0 : p.dx), px, b.y + b.h + 24, 'middle'); }
        ty.set(tpl(p.tagy || '{y}', { y: y }, p.dy == null ? 0 : p.dy), b.x - 8, py, 'end');
        var shw = f.get(p.show, 1);
        if (p.tagx !== false) { C.cover.push(['x', px, tx.w / 2 + 6, shw]); }
        C.cover.push(['y', py, ty.h / 2 + 10, shw]);
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

  /* trace - a route on a chart from point to point (a mixture changing, a state moving), drawn on with a bright tip;
     a coordinate may be a state ("@left"), so a slider moves the route. Publishes x, y (the tip, in the chart's units).
     {on: chart, pts: [[x, y], ...], cat, draw: "@d" (0..1), label, sub, side, labelAt (0..1 along the route, 1 if not given)} */
  define('trace', function (f, p) {
    var C = f.charts[p.on], cat = p.cat || 1, ps = [], dv = [], cum = [0];
    var line = el('path', { 'class': 'k2-curve k2-c-' + cat, pathLength: 1, 'stroke-dasharray': '0 1' }, f.L.hero);
    var tipGlow = el('circle', { r: 16, 'class': 'k2-tip-glow k2-f-' + cat }, f.L.hero), tip = el('circle', { r: 6.5, 'class': 'k2-tip' }, f.L.hero);
    function geo() {
      var i; dv = p.pts.map(function (q) { return [f.get(q[0], 0), f.get(q[1], 0)]; });
      ps = dv.map(function (q) { return [C.X(q[0]), C.Y(q[1])]; }); cum = [0];
      for (i = 1; i < ps.length; i++) { cum.push(cum[i - 1] + Math.hypot(ps[i][0] - ps[i - 1][0], ps[i][1] - ps[i - 1][1])); }
    }
    function along(k) {                                       /* the point and the value a fraction k of the way along */
      var N = ps.length - 1, L0 = k * cum[N], j = 1; while (j < N && cum[j] < L0) { j++; }
      var t = clamp((L0 - cum[j - 1]) / Math.max(1e-6, cum[j] - cum[j - 1]), 0, 1);
      return { px: [lerp(ps[j - 1][0], ps[j][0], t), lerp(ps[j - 1][1], ps[j][1], t)], v: [lerp(dv[j - 1][0], dv[j][0], t), lerp(dv[j - 1][1], dv[j][1], t)] };
    }
    geo();
    f.line(function () {                                     /* short pieces, so a slanting route keeps words off itself only */
      var q = [ps[0]], i, j, n; for (i = 1; i < ps.length; i++) { n = Math.max(1, Math.ceil((cum[i] - cum[i - 1]) / 28));
        for (j = 1; j <= n; j++) { q.push([lerp(ps[i - 1][0], ps[i][0], j / n), lerp(ps[i - 1][1], ps[i][1], j / n)]); } }
      return f.get(p.draw, 1) > 0.05 ? q : [];
    });
    var L = p.label ? f.label({ text: p.label, sub: p.sub, at: function () { return along(p.labelAt == null ? 1 : p.labelAt).px; }, side: p.side || 'upleft',
      show: function () { return f.get(p.draw, 1) > 0.9 ? 1 : 0; } }) : null;
    return {
      calc: function () {
        geo(); var k = clamp(f.get(p.draw, 1), 0, 1), a = along(k);
        f.publish(p.id, 'x', a.v[0]); f.publish(p.id, 'y', a.v[1]);
        f.publish(p.id, 'path', k > 0.02 ? ps.slice(0, 1).concat(sample(k)) : []);
      },
      draw: function () {
        var k = clamp(f.get(p.draw, 1), 0, 1), a = along(k).px, on = k > 0.005 && k < 0.995 ? 1 : 0;
        line.setAttribute('d', poly(ps)); line.setAttribute('stroke-dasharray', k.toFixed(4) + ' 1'); setOp(line, k > 0.003 ? 1 : 0);
        tip.setAttribute('cx', a[0].toFixed(1)); tip.setAttribute('cy', a[1].toFixed(1)); setOp(tip, on);
        tipGlow.setAttribute('cx', a[0].toFixed(1)); tipGlow.setAttribute('cy', a[1].toFixed(1)); setOp(tipGlow, on * 0.35);
      }
    };
    function sample(k) { var q = [], j; for (j = 1; j <= 40; j++) { q.push(along(k * j / 40).px); } return q; }
  });

  /* region - an area on a chart (a flammable zone, a safe envelope), its edge dashed; it lights when a drawn route
     crosses it and publishes hit (1 or 0), so a callout can say what that means.
     {on: chart, pts: [[x, y], ...], cat, label, sub, labelPt: [x, y] (where the words point; the top corner if not given), show, hit: [trace ids]} */
  define('region', function (f, p) {
    var C = f.charts[p.on], cat = p.cat || 4, g = el('g', {}, f.L.back), ps = p.pts.map(function (q) { return [C.X(q[0]), C.Y(q[1])]; });
    var d = poly(ps) + ' Z', hit = 0, glow = 0;
    var fill = el('path', { d: d, fill: f.url('solid-cat-' + cat), opacity: 0.35 }, g);
    el('path', { d: d, 'class': 'k2-c-' + cat, fill: 'none', 'stroke-width': 3, 'stroke-dasharray': '9 7', 'stroke-linejoin': 'round' }, g);
    var top = p.labelPt ? [C.X(p.labelPt[0]), C.Y(p.labelPt[1])] : ps.reduce(function (a, b) { return b[1] < a[1] ? b : a; });
    if (p.label) { f.label({ text: p.label, sub: p.sub, at: function () { return top; }, side: p.side || 'upright', show: function () { return f.get(p.show, 1) > 0.5 ? 1 : 0; } }); }
    function inside(q) {
      var c = false, i, j;
      for (i = 0, j = ps.length - 1; i < ps.length; j = i++) {
        if ((ps[i][1] > q[1]) !== (ps[j][1] > q[1]) && q[0] < (ps[j][0] - ps[i][0]) * (q[1] - ps[i][1]) / (ps[j][1] - ps[i][1]) + ps[i][0]) { c = !c; }
      }
      return c;
    }
    return {
      calc: function () {
        hit = (p.hit || []).some(function (id) { return ((f.out[id] || {}).path || []).some(inside); }) ? 1 : 0;
        f.publish(p.id, 'hit', hit);
      },
      draw: function (dt, snap) {
        glow = snap ? hit : glow + (hit - glow) * Math.min(1, (dt || 0) * 8);
        fill.setAttribute('opacity', (0.3 + 0.45 * glow).toFixed(3));
        setOp(g, f.get(p.show, 1));
      },
      live: function () { return Math.abs(hit - glow) > 0.01; }
    };
  });

  /* ===== OBJECTS ============================================================================================= */
  /* pipe - a pipe cut along its length: outline, metal walls hatched as cut faces, the liquid in its bore, and the flow
     as particles that follow the line, faster where it narrows, stopped when nothing flows.
     {pts: [[x, y], ...] (straight runs), r: bore radius, wall, flow: "V.flow" (0..1), speed, n: particles,
      gate: {x, open: ref} - a gate valve across it: the particles squeeze through the opening under the gate} */
  define('pipe', function (f, p) {
    var A = p.from && f.byId[p.from] && f.byId[p.from].port, Z = p.to && f.byId[p.to] && f.byId[p.to].port;
    var P = (p.pts || []).map(function (q) { return q.slice(); });
    if (A) { if (P.length) { P[0][1] = A.y; } P.unshift([A.x, A.y]); }        /* it leaves the nozzle level, and arrives level */
    if (Z) { if (P.length) { P[P.length - 1][1] = Z.y; } P.push([Z.x, Z.y]); }
    var r = p.r || (A && A.r) || 26, wall = p.wall || (A && A.wall) || 9, R = r + wall, d0 = poly(P), i, segs = [], len = 0;
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
    var fw = (A && A.fw) || Math.max(8, wall * 1.2), fl = (A && A.fl) || wall;
    function flange(x0, y, layer) {
      var d = 'M' + pt([x0, y - R - fl]) + ' h' + fw.toFixed(1) + ' V' + (y + R + fl).toFixed(1) + ' h' + (-fw).toFixed(1) + ' Z';
      el('path', { d: d, 'class': 'k2-outline-s', 'stroke-width': 5, 'stroke-linejoin': 'round' }, layer);
      el('path', { d: d, fill: f.url('metalv') }, layer); el('path', { d: d, 'class': 'k2-edge' }, layer);
    }
    function bolts(x0, x1, y, layer) {           /* the studs through a flange pair */
      [-1, 1].forEach(function (sg) { el('rect', { x: x0 - 4, y: y + sg * (R + fl * 0.5) - 2.5, width: x1 - x0 + 8, height: 5, rx: 2, 'class': 'k2-outline' }, layer); });
    }
    if (A) { flange(A.x, A.y, f.L.hero); bolts(A.x - fw, A.x + fw, A.y, f.L.hero); }
    if (Z) {
      var sx = Z.x, sw = Z.through + 6, sl = 'M' + pt([sx, Z.y - R]) + ' h' + sw + ' V' + (Z.y + R).toFixed(1) + ' h' + (-sw) + ' Z';
      el('path', { d: sl, 'class': 'k2-outline-s', 'stroke-width': 5 }, f.L.front);    /* the pipe carried through the tank's wall */
      el('path', { d: sl, fill: f.url('metalv') }, f.L.front);
      el('rect', { x: sx, y: Z.y - r, width: sw, height: 2 * r, fill: f.band('liquid', yTop - r, yBot + r) }, f.L.front);
      el('path', { d: sl, 'class': 'k2-edge' }, f.L.front);
      flange(sx - 2 * fw, Z.y, f.L.front); flange(sx - fw, Z.y, f.L.front); bolts(sx - 2 * fw, sx, Z.y, f.L.front);
    }
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
  /* callout - words for a place, beside it with a leader when they must go further. {at: [x, y], text, sub, side, show}
     - text and sub may change with the story: {"pick": "@k", "of": [...]} */
  define('callout', function (f, p) {
    var t0 = pick(f, p.text), s0 = pick(f, p.sub);
    var L = f.label({ text: t0, sub: p.sub ? s0 : null, at: function () { return p.at; }, side: p.side, dist: p.dist, lead: p.lead,
      show: p.show != null ? function () { return f.get(p.show, 1); } : null });
    if (!(p.text && p.text.of) && !(p.sub && p.sub.of)) { return {}; }
    return {
      draw: function () {
        var t = pick(f, p.text), sb = pick(f, p.sub), n = L.t.childNodes;
        if (t === t0 && sb === s0) { return; }
        t0 = t; s0 = sb; n[0].textContent = t; if (n[1]) { n[1].textContent = sb; }
        f.relayout = true;
      }
    };
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
     line in turn; words that would touch the last ones on their side go a lane further out. {x, y, w, start, end, step,
     tick: "{v}", clock (the times are minutes after midnight, shown as 02:10), events: [{at, label, sub, cat}], cursor:
     "@t", cursorTag: "{v}", stem, lane (px between lanes, 58)} */
  define('events', function (f, p) {
    function clock(m) { m = ((Math.round(m) % 1440) + 1440) % 1440; return (m < 600 ? '0' : '') + Math.floor(m / 60) + ':' + (m % 60 < 10 ? '0' : '') + m % 60; }
    var x0 = p.x, y0 = p.y, W = p.w, t0 = p.start, t1 = p.end, E = p.events || [], g = el('g', {}, f.L.back), t, ticks = [];
    function X(tt) { return x0 + (tt - t0) / (t1 - t0) * W; }
    el('rect', { x: x0 - 6, y: y0 - 5, width: W + 12, height: 10, rx: 5, 'class': 'k2-outline' }, g);
    el('rect', { x: x0 - 4, y: y0 - 3, width: W + 8, height: 6, rx: 3, fill: f.url('metalv') }, g);
    var done = el('rect', { x: x0 - 4, y: y0 - 3, height: 6, rx: 3, 'class': 'k2-done-line' }, g);
    for (t = t0; t <= t1 + 1e-9; t += (p.step || 1)) {
      el('line', { x1: X(t), y1: y0 + 8, x2: X(t), y2: y0 + 16, 'class': 'k2-axis' }, g);
      ticks.push({ n: el('text', { x: X(t), y: y0 + 36, 'text-anchor': 'middle', 'class': 'k2-t-tick' }, g, tpl(p.tick || '{v}', { v: p.clock ? clock(t) : t }, 0)), at: X(t) });
    }
    f.thin(ticks, 'x');
    var evs = E.map(function (e, i) {
      var up = i % 2 === 0, ex = X(e.at), len = p.stem || 92, cat = e.cat || (i % 5) + 1, eg = el('g', {}, f.L.front);
      el('path', { d: 'M' + ex + ' ' + y0 + ' V' + (y0 + (up ? -len : len)), 'class': 'k2-stem' }, eg);
      el('circle', { cx: ex, cy: y0, r: 11, 'class': 'k2-outline' }, eg);
      el('circle', { cx: ex, cy: y0, r: 8, fill: f.url('solid-cat-' + cat) }, eg);
      var stem = eg.firstChild, tg = el('g', { 'text-anchor': 'middle' }, eg), ty = y0 + (up ? -len - 12 : len + 24);
      var tl = el('text', { x: ex, y: ty - (up && e.sub ? 22 : 0), 'class': 'k2-t-lbl k2-halo' }, tg, e.label || '');
      var ts = e.sub ? el('text', { x: ex, y: ty + (up ? 0 : 22), 'class': 'k2-t-sub k2-halo' }, tg, e.sub) : null;
      return { e: e, g: eg, x: ex, y: ty, up: up, stem: stem, tl: tl, ts: ts, tg: tg };
    });
    /* lanes: each event takes the nearest free place - its own side, else the other side, else a lane further out -
       so words close in time never sit on each other */
    function lanes() {
      var base = p.stem || 92, gap = p.lane || 58, last = { true: [], false: [] };
      evs.forEach(function (o, i) {
        var b = o.tg.getBBox(), half = b.width / 2 + 10, pref = i % 2 === 0, lane, side, k;
        for (k = 0; k < 2 * evs.length; k++) {
          lane = k >> 1; side = k % 2 ? !pref : pref;
          if (last[side][lane] == null || last[side][lane] <= o.x - half) { break; }
        }
        if (side !== o.up) {                                   /* the words change side: they hang below or stand above */
          o.up = side; o.tg.setAttribute('text-anchor', 'middle');
        }
        last[side][lane] = o.x + half;
        var len = base + lane * gap, ty = y0 + (o.up ? -len - 12 : len + 24);
        o.stem.setAttribute('d', 'M' + o.x + ' ' + y0 + ' V' + (y0 + (o.up ? -len : len)));
        o.tl.setAttribute('y', ty - (o.up && o.ts ? 22 : 0)); if (o.ts) { o.ts.setAttribute('y', ty + (o.up ? 0 : 22)); }
        o.y = ty;
      });
    }
    lanes(); (f.fits = f.fits || []).push(lanes);
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
          setOp(o.g, k); o.g.setAttribute('transform', 'translate(0 ' + ((1 - k) * (o.up ? -14 : 14)).toFixed(1) + ')');
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
     them, and what they say in a bubble that a step brings in. {x, y (feet), scale, name, role, cat, say (or {"pick":
     "@k", "of": [lines]} - a new line each step), sayShow,
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
      var said = pick(f, p.say), sayNow = function () { wrapText(bt, said, bx + bw / 2, by + bh / 2, bw - 30); };
      (f.fits = f.fits || []).push(sayNow);
      f.solid(function () { return { x: bx, y: by, x2: bx + bw, y2: by + bh + 26 }; });
      bub.__o = [bx + bw / 2, by + bh];
    }
    f.solid(function () { return { x: x - 50 * k, y: y - 160 * k, x2: x + 50 * k, y2: y + 56 }; });
    var sp = new Spring(f.target(p.sayShow, 1)), moving = false;
    return {
      draw: function (dt, snap) {
        setOp(g, f.get(p.show, 1)); setOp(nm, f.get(p.show, 1)); setOp(lit, clamp(f.get(p.lit, 0), 0, 1));
        if (bub) {
          var nowSaid = pick(f, p.say);                          /* a new line: the bubble pops with it */
          if (nowSaid !== said) { said = nowSaid; sayNow(); if (!snap) { sp.x = 0.3; } }
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
      port: p.inlet != null ? { x: x, y: clamp(p.inlet, y + r + 30, y + H - r - 30), through: wall } : null,
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

  /* pump - a centrifugal pump cut open: the volute casing hatched, widening round the impeller into a straight discharge
     nozzle with a flange, the impeller turning as fast as its speed (it stops when the speed is 0), the eye where the
     liquid comes in. Publishes flow = speed; a pipe with "from" set to its id starts at the nozzle's flange.
     {x, y (the shaft), r, speed: "@s", label, sub, vanes} */
  define('pump', function (f, p) {
    var cx = p.x, cy = p.y, R = p.r || 90, i, N = 48, R2 = R * 1.32, bo = R * 0.27, wa = R * 0.1, fl = R * 0.1, fw = Math.max(8, R * 0.12);
    var xe = cx + R * 1.65, yt = cy - R2, yb = yt + 2 * (bo + wa), yo = yt + wa + bo;
    function spiral(off, yCut) {                  /* the volute wall, from where it leaves the nozzle's lower edge to the top */
      var o = [], j, prev;
      for (j = 0; j <= N; j++) {
        var a = -Math.PI / 2 + j / N * 2 * Math.PI, rr = R * (1 + 0.32 * j / N) - off, q = [cx + rr * Math.cos(a), cy + rr * Math.sin(a)];
        if (!o.length && q[1] < yCut) { prev = q; continue; }
        if (!o.length && prev) { var t = (yCut - prev[1]) / (q[1] - prev[1]); o.push([lerp(prev[0], q[0], t), yCut]); }
        o.push(q);
      }
      return o;
    }
    var casing = poly(spiral(0, yb)) + ' L' + pt([xe - fw, yt]) + ' L' + pt([xe - fw, yb]) + ' Z';
    var flange = 'M' + pt([xe - fw, yt - fl]) + ' H' + xe.toFixed(1) + ' V' + (yb + fl).toFixed(1) + ' H' + (xe - fw).toFixed(1) + ' Z';
    var water = poly(spiral(wa, yo + bo)) + ' L' + pt([xe, yo - bo]) + ' L' + pt([xe, yo + bo]) + ' Z';
    f.shadow(cx, cy + R2 + 18, R2 * 1.1, 14);
    var base = 'M' + (cx - R2 * 0.9) + ' ' + (cy + R2 + 14) + ' H' + (cx + R2 * 0.9) + ' L' + (cx + R2 * 0.6) + ' ' + (cy + R * 0.6) + ' H' + (cx - R2 * 0.6) + ' Z';
    el('path', { d: base, 'class': 'k2-outline-s', 'stroke-width': 6 }, f.L.back); el('path', { d: base, fill: f.url('metal') }, f.L.back);
    el('path', { d: casing + ' ' + flange, 'class': 'k2-outline-s', 'stroke-width': 6, 'stroke-linejoin': 'round' }, f.L.hero);
    el('path', { d: casing, fill: f.url('metal') }, f.L.hero);
    el('path', { d: casing, fill: f.url('hatch') }, f.L.hero);
    el('path', { d: flange, fill: f.url('metalv') }, f.L.hero);
    el('path', { d: water, fill: f.url('liquid') }, f.L.hero);
    el('path', { d: casing + ' ' + flange, 'class': 'k2-edge' }, f.L.hero);
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
    f.solid(function () { return { x: cx - R2, y: yt - fl - 4, x2: xe + 4, y2: cy + R2 + 16 }; });
    var ang = 0, sp = 0;
    return {
      port: { x: xe, y: yo, r: bo, wall: wa, fl: fl, fw: fw },
      calc: function () { sp = clamp(f.get(p.speed, 0), 0, 1); f.publish(p.id, 'flow', sp); f.publish(p.id, 'speed', sp); },
      draw: function (dt) { ang = (ang + sp * (p.rpm || 220) * (dt || 0)) % 360; imp.setAttribute('transform', 'rotate(' + ang.toFixed(1) + ' ' + cx + ' ' + cy + ')'); },
      live: function () { return sp > 0.001 && !f.hidden; }
    };
  });

  /* tanker_section - a double-hull oil tanker cut through midships: the shell with its bilges and cambered deck, the
     inner hull, the wing and double-bottom ballast tanks with their web frames, girders, stringers and longitudinals cut
     as steel, two cargo tanks either side of the centreline bulkhead with their heating coils, and on deck the cargo
     pipelines, the IG main, the catwalk and a P/V valve. The ship floats at the draught its cargo and ballast give it;
     a breach tears the starboard shell below the waterline and the sea floods that ballast tank up to the waterline
     while the oil stays in; the liquids stay level as she lists, and settle after a change.
     {x (the centreline), sea (the waterline's y), k (px a metre), beam, depth (m), cargo, ballast (0..1), breach (0..1,
      the tank floods as it rises), list (degrees when flooded), highlight (1 outer hull, 2 inner hull, 3 ballast tanks,
      4 cargo tanks), labels (which set of words shows), sets: {n: [names]}, words: {name: text}}
     - publishes draught (m), list (degrees), cargo, ballast */
  define('tanker_section', function (f, p) {
    var cx = p.x != null ? p.x : f.W / 2, SEA = p.sea != null ? p.sea : Math.round(f.H * 0.57), k = p.k || 12.5;
    var hb = (p.beam || 43) * k / 2, D = (p.depth || 21) * k, R = 4 * k, hdb = 3.2 * k, ww = 3.2 * k, hop = 4 * k, cam = 0.8 * k;
    var t = 8, ti = 6, td = 8, cgh = 3, cbh = 3.5, PI = Math.PI, xh = hb - ww - hop, j, q;
    function deckY(x) { return -D - cam * (1 - (x / hb) * (x / hb)); }
    function deckU(x) { return deckY(x) + td; }
    function arc(ax, ay, r, a0, a1, n) { var o = [], i; for (i = 0; i <= n; i++) { var a = lerp(a0, a1, i / n); o.push([ax + r * Math.cos(a), ay + r * Math.sin(a)]); } return o; }
    function run(x0, x1, n, off) { var o = [], i; for (i = 0; i <= n; i++) { var x = lerp(x0, x1, i / n); o.push([x, deckY(x) + off]); } return o; }
    function mir(ps) { return ps.map(function (a) { return [-a[0], a[1]]; }); }
    function nrm(a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy); return l ? [dy / l, -dx / l] : null; }
    function offset(ps, dd) {                     /* a plate's other face: the line moved dd to its side, mitred at the knuckles */
      return ps.map(function (b, i) {
        var a = ps[Math.max(0, i - 1)], c = ps[Math.min(ps.length - 1, i + 1)], n1 = nrm(a, b) || nrm(b, c), n2 = nrm(b, c) || n1;
        var mx = n1[0] + n2[0], my = n1[1] + n2[1], ml = Math.hypot(mx, my), co = (mx * n1[0] + my * n1[1]) / ml;
        return [b[0] + mx / ml * dd / co, b[1] + my / ml * dd / co];
      });
    }
    function R4(x0, y0, x1, y1) { return 'M' + pt([x0, y0]) + ' H' + x1.toFixed(1) + ' V' + y1.toFixed(1) + ' H' + x0.toFixed(1) + ' Z '; }
    function circ(x, y, r) { return 'M' + pt([x - r, y]) + ' a' + r + ' ' + r + ' 0 1 0 ' + 2 * r + ' 0 a' + r + ' ' + r + ' 0 1 0 ' + (-2 * r) + ' 0 Z '; }
    function ell(x, y, rx, ry) { return 'M' + pt([x - rx, y]) + ' a' + rx + ' ' + ry + ' 0 1 0 ' + 2 * rx + ' 0 a' + rx + ' ' + ry + ' 0 1 0 ' + (-2 * rx) + ' 0 Z '; }

    /* the steel lines: the shell's two faces, the inner hull, the tanks between them */
    var outer = [[-hb, deckY(-hb)], [-hb, -R]].concat(arc(-hb + R, -R, R, PI, PI / 2, 12), arc(hb - R, -R, R, PI / 2, 0, 12), [[hb, deckY(hb)]], run(hb, -hb, 30, 0));
    var inner = [[-(hb - t), deckU(-(hb - t))]].concat(arc(-hb + R, -R, R - t, PI, PI / 2, 12), arc(hb - R, -R, R - t, PI / 2, 0, 12), [[hb - t, deckU(hb - t)]], run(hb - t, -(hb - t), 30, td));
    var ihS = [[0, -hdb], [xh, -hdb], [hb - ww, -hdb - hop], [hb - ww, deckU(hb - ww) - 3]];
    var ihFull = mir(ihS).reverse().concat(ihS.slice(1)), band = ihFull.concat(offset(ihFull, ti).reverse());
    var cS = offset([[cbh, -hdb], [xh, -hdb], [hb - ww, -hdb - hop], [hb - ww, deckU(hb - ww)]], ti).concat(run(hb - ww - ti, cbh, 16, td)), cP = mir(cS);
    var lS = [[cgh, -t]].concat(arc(hb - R, -R, R - t, PI / 2, 0, 8), run(hb - t, hb - ww, 3, td), [[hb - ww, -hdb - hop], [xh, -hdb], [cgh, -hdb]]), lP = mir(lS);
    var ys1 = lerp(-hdb - hop, deckU(hb - ww), 0.2), ys2 = lerp(-hdb - hop, deckU(hb - ww), 0.6), xg = [xh / 3, 2 * xh / 3];
    var yh = -8 * k, hh = 1.6 * k, xm = (hb - ww) / 2;

    var G = {};
    ['back', 'contents', 'hero', 'front'].forEach(function (n) { G[n] = el('g', {}, f.L[n]); });

    /* the sea: deeper is darker, a gentle surface, a few glints */
    var sg = el('linearGradient', { id: f.id + '-sea' + (++UID), gradientUnits: 'userSpaceOnUse', x1: 0, y1: SEA, x2: 0, y2: f.H }, f.defs);
    stops(sg, [[0, 'k2-s-sea-hi', 0.95], [1, 'k2-s-sea-lo', 0.9]]);
    var sh = el('linearGradient', { id: f.id + '-sh' + (++UID), x1: 0, y1: 0, x2: 0, y2: 1 }, f.defs);
    stops(sh, [[0, 'k2-s-sea-line', 0.3], [1, 'k2-s-sea-line', 0]]);
    el('rect', { x: -f.W, y: SEA, width: 3 * f.W, height: f.H, fill: 'url(#' + sg.id + ')' }, f.L.bg);
    el('rect', { x: -f.W, y: SEA, width: 3 * f.W, height: 30, fill: 'url(#' + sh.id + ')' }, f.L.bg);
    var wv = 'M' + (-f.W) + ' ' + SEA;
    for (j = -f.W; j < 2 * f.W; j += 50) { wv += ' Q' + (j + 25) + ' ' + (SEA + ((j / 50) % 2 ? -3.5 : 3.5)) + ' ' + (j + 50) + ' ' + SEA; }
    el('path', { d: wv, 'class': 'k2-tk-wave' }, f.L.bg);
    var gl = '', seed = 11;
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    for (j = 0; j < 16; j++) {
      var gx = rnd() * f.W, gy = SEA + 14 + rnd() * (f.H - SEA - 24) * 0.8, gw = 14 + rnd() * 26;
      gl += 'M' + pt([gx, gy]) + ' h' + gw.toFixed(1) + ' ';
    }
    el('path', { d: gl, 'class': 'k2-tk-glint' }, f.L.bg);

    /* behind the liquids: the open tanks, the faces of the floors, web frames and deck transverses with their holes */
    var B = G.back;
    el('path', { d: poly(inner, true), 'class': 'k2-cavity' }, B);
    var web = poly(lS, true) + ' ' + poly(lP, true), holes = '';
    [-1, 1].forEach(function (s2) {
      var dtr = [[s2 * (hb - ww - ti), deckU(hb - ww - ti)], [s2 * (hb - ww - ti), deckU(hb - ww) + 44]].concat(
        run(s2 * (hb - ww - ti - 34), s2 * (cbh + 34), 12, td + 18), [[s2 * cbh, deckU(cbh) + 44], [s2 * cbh, deckU(cbh)]], run(s2 * cbh, s2 * (hb - ww - ti), 12, td).slice(1));
      web += ' ' + poly(dtr, true);
      [[0, xg[0]], [xg[0], xg[1]], [xg[1], xh]].forEach(function (bay) { holes += ell(s2 * (bay[0] + bay[1]) / 2, -(t + hdb) / 2, (bay[1] - bay[0]) * 0.3, (hdb - t) * 0.2); });
      holes += circ(s2 * (hb - 0.45 * R - 9), -0.62 * hdb - 9, 0.12 * R + 1);
      holes += ell(s2 * (hb - t / 2 - ww / 2), (ys1 + ys2) / 2, (ww - t) * 0.22, Math.abs(ys2 - ys1) * 0.3);
      holes += ell(s2 * (hb - t / 2 - ww / 2), (ys2 + deckU(hb - ww)) / 2, (ww - t) * 0.22, Math.abs(deckU(hb - ww) - ys2) * 0.3);
      holes += ell(s2 * (hb - t / 2 - ww / 2), (ys1 - hdb - hop) / 2 - 1, (ww - t) * 0.16, Math.abs(ys1 + hdb + hop) * 0.22);
    });
    el('path', { d: web, 'class': 'k2-tk-web' }, B);
    el('path', { d: holes, 'class': 'k2-cavity' }, B);

    /* the liquids: each in its own tank, kept level by a frame that turns back the ship's list */
    function grad(a, b) { var g = el('linearGradient', { id: f.id + '-tk' + (++UID), x1: 0, y1: 0, x2: 0, y2: 1 }, f.defs); stops(g, [[0, a], [1, b]]); return 'url(#' + g.id + ')'; }
    var oilFill = grad('k2-s-oil-hi', 'k2-s-oil-lo'), watFill = grad('k2-s-liq-hi', 'k2-s-liq-lo');
    function liquid(ps, fill, top) {
      var id = f.id + '-tc' + (++UID);
      el('path', { d: poly(ps, true) }, el('clipPath', { id: id }, f.defs));
      var g = el('g', { 'clip-path': 'url(#' + id + ')' }, G.contents), wg = el('g', {}, g);
      return { wg: wg, r: el('rect', { x: -600, width: 1200, height: 460, fill: fill, 'class': 'k2-tk-liq' }, wg), l: el('line', { x1: -600, x2: 600, 'class': top }, wg) };
    }
    var LQ = { cp: liquid(cP, oilFill, 'k2-tk-oiltop'), cs: liquid(cS, oilFill, 'k2-tk-oiltop'), bp: liquid(lP, watFill, 'k2-surface'), bs: liquid(lS, watFill, 'k2-surface') };

    /* the steel, cut: girders and stringers, longitudinals, the inner hull, the centreline bulkhead, the shell and deck */
    var H = G.hero, plates = '', stiff = '';
    function lng(x, y, nx, ny, hgt) {             /* a longitudinal seen end on: its web off the plate and a flange */
      var tx = -ny, ty = nx, a = 1.4, fl = 6;
      stiff += 'M' + pt([x - tx * a, y - ty * a]) + ' L' + pt([x + tx * a, y + ty * a]) + ' L' + pt([x + tx * a + nx * hgt, y + ty * a + ny * hgt]) +
        ' L' + pt([x + tx * fl + nx * hgt, y + ty * fl + ny * hgt]) + ' L' + pt([x + tx * fl + nx * (hgt + 2.6), y + ty * fl + ny * (hgt + 2.6)]) +
        ' L' + pt([x - tx * a + nx * (hgt + 2.6), y - ty * a + ny * (hgt + 2.6)]) + ' Z ';
    }
    function near(v, list, dd) { return list.some(function (u) { return Math.abs(v - u) < dd; }); }
    [-1, 1].forEach(function (s2) {
      plates += R4(s2 * xg[0] - 2.5, -hdb + 1, s2 * xg[0] + 2.5, -t - 1) + R4(s2 * xg[1] - 2.5, -hdb + 1, s2 * xg[1] + 2.5, -t - 1);
      [ys1, ys2].forEach(function (y) {
        var xa = s2 * (hb - ww + 1), xb = s2 * (hb - t - 1);
        plates += R4(Math.min(xa, xb), y, Math.max(xa, xb), y + 5);
        plates += 'M' + pt([xa, y + 5]) + ' L' + pt([xa + s2 * 9, y + 5]) + ' L' + pt([xa, y + 14]) + ' Z ';
        plates += 'M' + pt([xb, y + 5]) + ' L' + pt([xb - s2 * 9, y + 5]) + ' L' + pt([xb, y + 14]) + ' Z ';
      });
      for (q = 13; q < hb - R - 4; q += 13) { if (!near(q, xg.concat([0]), 6)) { lng(s2 * q, -t, 0, -1, 7); } }
      for (q = 13; q < xh - 6; q += 13) { if (!near(q, xg.concat([0]), 6)) { lng(s2 * q, -hdb, 0, 1, 6); } }
      for (q = -R - 8; q > deckU(hb) + 8; q -= 13) { if (!near(q, [ys1 + 2, ys2 + 2], 8)) { lng(s2 * (hb - t), q, -s2, 0, 7); } }
      for (q = -hdb - hop - 10; q > deckU(hb - ww) + 8; q -= 13) { if (!near(q, [ys1 + 2, ys2 + 2], 8)) { lng(s2 * (hb - ww), q, s2, 0, 6); } }
      [0.33, 0.66].forEach(function (u) { var hx = lerp(xh, hb - ww, u), hy = lerp(-hdb, -hdb - hop, u); lng(s2 * hx, hy, s2 * Math.SQRT1_2, Math.SQRT1_2, 6); });
      [0.3, 0.62].forEach(function (u) { var a = lerp(PI / 2, 0, u); lng(s2 * (hb - R + (R - t) * Math.cos(a)), -R + (R - t) * Math.sin(a), -s2 * Math.cos(a), -Math.sin(a), 6); });
      for (q = 16; q < hb - ww - ti - 10; q += 17) { lng(s2 * q, deckU(q), 0, 1, 9); }
      lng(s2 * (hb - ww / 2 - 2), deckU(hb - ww / 2), 0, 1, 6);
    });
    for (q = -hdb - 24; q > deckU(0) + 30; q -= 19) { lng(-cbh, q, -1, 0, 7); }
    plates += R4(-cgh, -hdb + 1, cgh, -t - 1);
    el('path', { d: plates, fill: f.url('metal'), 'class': 'k2-tk-plate' }, H);
    el('path', { d: stiff, fill: f.url('metal'), 'class': 'k2-tk-stiff' }, H);
    function cutSteel(d, g) {
      el('path', { d: d, 'class': 'k2-outline-s', 'stroke-width': 3.5, 'stroke-linejoin': 'round' }, g);
      el('path', { d: d, 'fill-rule': 'evenodd', fill: f.url('metal') }, g);
      el('path', { d: d, 'fill-rule': 'evenodd', fill: f.url('hatch') }, g);
    }
    cutSteel(poly(band, true), H);
    cutSteel(R4(-cbh, deckU(0) + 1, cbh, -hdb - ti + 1), H);
    var shellD = poly(outer, true) + ' ' + poly(inner, true);
    cutSteel(shellD, H);
    el('path', { d: poly(outer, true), 'class': 'k2-edge' }, H);
    /* the bottom's antifouling up to the loaded waterline, and a bilge keel at each turn of the bilge */
    var yL = -(p.load || 14.5) * k;
    el('path', { d: poly([[-hb - 1.5, yL]].concat(arc(-hb + R, -R, R + 1.5, PI, PI / 2, 12), arc(hb - R, -R, R + 1.5, PI / 2, 0, 12), [[hb + 1.5, yL]])), 'class': 'k2-tk-paint' }, H);
    var bk = '';
    [-1, 1].forEach(function (s2) {
      var a = s2 < 0 ? 0.75 * PI : 0.25 * PI, bx = s2 * (hb - R) + R * Math.cos(a), by = -R + R * Math.sin(a), ux = Math.cos(a), uy = Math.sin(a);
      bk += poly([[bx - uy * 2.2 - ux * 2, by + ux * 2.2 - uy * 2], [bx - uy * 2.2 + ux * 15, by + ux * 2.2 + uy * 15],
        [bx + uy * 2.2 + ux * 15, by - ux * 2.2 + uy * 15], [bx + uy * 2.2 - ux * 2, by - ux * 2.2 - uy * 2]], true) + ' ';
    });
    el('path', { d: bk, fill: f.url('metal'), 'class': 'k2-tk-plate' }, H);
    /* heating coils on the tank bottom: steam pipes seen end on, on small feet */
    var coil = '', coilO = '', feet = '';
    [-1, 1].forEach(function (s2) {
      for (q = 22; q < xh - 10; q += 22) {
        var y = -hdb - ti - 11;
        coilO += circ(s2 * q, y, 5.6); coil += circ(s2 * q, y, 4.2) + circ(s2 * q, y, 1.8);
        feet += R4(s2 * q - 1.5, y + 4, s2 * q + 1.5, -hdb - ti + 0.5);
      }
    });
    el('path', { d: feet, 'class': 'k2-spoke' }, H);
    el('path', { d: coilO, 'class': 'k2-outline' }, H);
    el('path', { d: coil, 'fill-rule': 'evenodd', fill: f.url('metal') }, H);

    /* the zones a step can light */
    function zone(d, fill) {
      var g = el('g', { opacity: 0 }, H);
      if (fill) { el('path', { d: d, fill: f.url('fill-blue'), 'fill-opacity': 0.7 }, g); }
      el('path', { d: d, 'class': 'k2-tk-zone-glow' }, g); el('path', { d: d, 'class': 'k2-tk-zone' }, g);
      return g;
    }
    var Z = [zone(poly(outer, true)), zone(poly(offset(ihFull, ti / 2))), zone(poly(lS, true) + ' ' + poly(lP, true), true), zone(poly(cS, true) + ' ' + poly(cP, true), true)];

    /* the breach: the shell torn open, its plate ends bent in */
    var hg = el('g', { opacity: 0 }, H), gx0 = hb - t - 10;
    var gap = [[hb + 3, yh - hh + 2], [hb - 3, yh - hh], [hb - t, yh - hh + 3], [gx0, yh - hh + 1], [gx0 + 2, yh - 4], [gx0 - 1, yh + 5], [gx0, yh + hh - 1],
      [hb - t, yh + hh - 4], [hb - 2, yh + hh], [hb + 3, yh + hh - 2]];
    el('path', { d: poly(gap, true), 'class': 'k2-outline-s', 'stroke-width': 3 }, hg);
    el('path', { d: poly(gap, true), 'class': 'k2-tk-gap' }, hg);
    [-1, 1].forEach(function (sy) {
      var y0 = yh - sy * hh;
      var fd = 'M' + pt([hb + 0.5, y0]) + ' Q' + pt([hb - 6, y0 + sy * 3]) + ' ' + pt([hb - t - 17, y0 + sy * 13]) + ' L' + pt([hb - t - 15, y0 + sy * 7]) +
        ' Q' + pt([hb - t - 3, y0 - sy * 1]) + ' ' + pt([hb - t + 1, y0 - sy * 5]) + ' L' + pt([hb + 0.5, y0 - sy * 5]) + ' Z';
      el('path', { d: fd, 'class': 'k2-outline-s', 'stroke-width': 3, 'stroke-linejoin': 'round' }, hg);
      el('path', { d: fd, fill: f.url('metal') }, hg);
      el('path', { d: fd, fill: f.url('hatch') }, hg);
    });

    /* on deck: railings, the pipe rack under the catwalk, the IG main, a tank hatch and a P/V valve */
    var F = G.front, y0d = deckY(0), metal = '', rails = '', grate = '';
    [-1, 1].forEach(function (s2) {
      var xr = s2 * (hb - 5), yd = deckY(hb - 5);
      metal += R4(xr - 1.6, yd - 30, xr + 1.6, yd + 1);
      rails += circ(xr, yd - 30, 2.6) + circ(xr, yd - 16, 2.6);
    });
    var ps0 = y0d - 10, pipes = [[-95, 11], [-70, 11], [-45, 11], [-23, 6]], igx = 32, igr = 10, igy = y0d - 14 - igr;
    pipes.forEach(function (pp) { pp[2] = ps0 - pp[1]; });
    metal += 'M' + pt([-112, deckY(-112) + 1]) + ' L' + pt([-112, ps0]) + ' L' + pt([-8, ps0]) + ' L' + pt([-8, deckY(-8) + 1]) + ' Z ';
    var cb = y0d - 49, cw0 = -99, cw1 = -41;
    metal += R4(-118, cb, -114, deckY(-116) + 1) + R4(-6, cb, -2, deckY(-4) + 1);
    grate += R4(-120, cb - 6, 0, cb) + R4(cw0, cb - 11, cw1, cb - 6);
    metal += R4(cw0, cb - 35, cw0 + 3, cb - 11) + R4(cw1 - 3, cb - 35, cw1, cb - 11);
    rails += circ(cw0 + 1.5, cb - 35, 2.6) + circ(cw0 + 1.5, cb - 23, 2.6) + circ(cw1 - 1.5, cb - 35, 2.6) + circ(cw1 - 1.5, cb - 23, 2.6);
    metal += R4(igx - 7, igy + igr - 1, igx + 7, deckY(igx) + 1);
    var hx = -190, hyd = deckY(hx);
    metal += R4(hx - 15, hyd - 10, hx + 15, hyd + 1) + R4(hx - 18, hyd - 14, hx + 18, hyd - 10);
    var pvx = 150, pyd = deckY(pvx), pvTop = pyd - 78;          /* riser, flanged body, flame screen, weather hood */
    metal += R4(pvx - 5, pyd - 28, pvx + 5, pyd + 1) + R4(pvx - 12, pyd - 32, pvx + 12, pyd - 28);
    metal += 'M' + pt([pvx - 16, pyd - 32]) + ' V' + (pyd - 48) + ' Q' + pt([pvx - 16, pyd - 52]) + ' ' + pt([pvx - 12, pyd - 52]) + ' H' + (pvx + 12) +
      ' Q' + pt([pvx + 16, pyd - 52]) + ' ' + pt([pvx + 16, pyd - 48]) + ' V' + (pyd - 32) + ' Z ';
    metal += R4(pvx - 13, pyd - 55, pvx + 13, pyd - 52);
    metal += 'M' + pt([pvx - 21, pyd - 64]) + ' Q' + pt([pvx - 20, pyd - 75]) + ' ' + pt([pvx, pvTop + 1]) + ' Q' + pt([pvx + 20, pyd - 75]) + ' ' + pt([pvx + 21, pyd - 64]) + ' Z ';
    grate += R4(pvx - 10, pyd - 64, pvx + 10, pyd - 55);
    el('path', { d: metal + grate, 'class': 'k2-outline-s', 'stroke-width': 3.5, 'stroke-linejoin': 'round' }, F);
    el('path', { d: metal + grate, fill: f.url('metal') }, F);
    el('path', { d: grate, fill: f.url('hatch') }, F);
    el('path', { d: rails, 'class': 'k2-tk-rail' }, F);
    el('path', { d: circ(pvx - 8, pyd - 30, 1.4) + circ(pvx + 8, pyd - 30, 1.4) + circ(pvx - 8, pyd - 53.5, 1.3) + circ(pvx + 8, pyd - 53.5, 1.3), 'class': 'k2-outline' }, F);
    var bores = '';
    pipes.concat([[igx, igr, igy]]).forEach(function (pp) {
      var ring = circ(pp[0], pp[2], pp[1]) + circ(pp[0], pp[2], pp[1] * 0.68);
      el('path', { d: circ(pp[0], pp[2], pp[1] + 1.8), 'class': 'k2-outline' }, F);
      el('path', { d: ring, 'fill-rule': 'evenodd', fill: f.url('metal') }, F);
      el('path', { d: ring, 'fill-rule': 'evenodd', fill: f.url('hatch') }, F);
      bores += circ(pp[0], pp[2], pp[1] * 0.68);
    });
    el('path', { d: bores, 'class': 'k2-cavity' }, F);
    var boreOil = el('path', { d: pipes.map(function (pp) { return circ(pp[0], pp[2], pp[1] * 0.68); }).join(''), 'class': 'k2-tk-oil', opacity: 0 }, F);
    /* the draught marks on the port side, a metre a tick, every second one numbered */
    var mk = el('g', {}, F), mticks = '';
    for (q = 4; q <= Math.floor(D / k) - 2; q++) {
      mticks += 'M' + pt([-hb - (q % 2 ? 5 : 9), -q * k]) + ' H' + (-hb - 1) + ' ';
      if (q % 2 === 0) { el('text', { x: -hb - 12, y: -q * k + 5, 'text-anchor': 'end', 'class': 'k2-t-tick k2-halo' }, mk, q + 'M'); }
    }
    el('path', { d: mticks, 'class': 'k2-tk-mark' }, mk);
    /* sea water rushing in through the breach, and vapour out of the P/V valve while she loads */
    var sgp = el('g', {}, F), jets = [];
    for (j = 0; j < 18; j++) { jets.push({ on: false, x: 0, y: 0, vx: 0, vy: 0, c: el('line', { 'stroke-width': (3.6 + rnd() * 2.6).toFixed(1), 'class': 'k2-particle-s', opacity: 0 }, sgp) }); }
    var wisps = [0, 1, 2].map(function () { return el('ellipse', { 'class': 'k2-tk-vapour', opacity: 0 }, F); });

    /* the ship as it floats now: sunk to its draught, listed, and the world point of a point on its section */
    var dpx = 0, hd = 0, h = 0, sl = 0, slv = 0, lr = 0, cPrev = null, wph = 0, moving = false;
    var hs = new Spring(f.target(p.breach, 0) > 0.5 ? 1 : 0), lastB = f.target(p.breach, 0);
    function W(x, y) { var c = Math.cos(h), sn = Math.sin(h); return [cx + c * x - sn * (y + dpx), SEA + sn * x + c * (y + dpx)]; }
    function wb(x0, y0, x1, y1) {
      var ps = [W(x0, y0), W(x1, y0), W(x0, y1), W(x1, y1)], xs = ps.map(function (a) { return a[0]; }), yv = ps.map(function (a) { return a[1]; });
      return { x: Math.min.apply(null, xs), y: Math.min.apply(null, yv), x2: Math.max.apply(null, xs), y2: Math.max.apply(null, yv) };
    }
    f.solid(function () {
      var o = [wb(-hb - 4, deckY(-hb) - 32, -hb + ww + ti + 2, -R), wb(hb - ww - ti - 2, deckY(hb) - 32, hb + 4, -R), wb(-hb, -hdb - ti - 18, hb, 4),
        wb(-hb, deckY(0) - 4, hb, deckU(hb) + 12), wb(-cbh - 3, deckU(0), cbh + 3, -hdb), wb(-122, cb - 38, 4, deckY(0)), wb(igx - igr - 3, igy - igr - 3, igx + igr + 3, deckY(igx)),
        wb(pvx - 23, pvTop - 2, pvx + 23, pyd), wb(hx - 19, hyd - 15, hx + 19, hyd), wb(-hb - 48, -(Math.floor(D / k) - 2) * k - 10, -hb, -4 * k + 10)];
      if (f.target(p.breach, 0) > 0.5 || hs.x > 0.3) { o.push(wb(hb - t - 20, yh - hh - 14, hb + 54, yh + hh + 14)); }
      o.push({ x: 0, y: SEA - 7, x2: f.W, y2: SEA + 7 });
      return o;
    });

    /* the words: one set a step, the others fade out (a hidden label is laid out away from the figure) */
    var words = p.words || {}, SETS = p.sets || { 1: ['outer', 'inner', 'cargo', 'coils', 'wl'], 2: ['outer', 'inner', 'wing', 'db'],
      3: ['cargo', 'pipes', 'ig', 'pv', 'wl'], 4: ['breach', 'wing', 'inner', 'cargo'], 5: ['inner', 'cargo', 'wing', 'wl'] };
    function vis(nm, v) { var o = 0, key; for (key in SETS) { if (SETS[key].indexOf(nm) >= 0) { o += clamp(1 - Math.abs(v - (+key)), 0, 1); } } return clamp(o, 0, 1); }
    var LB = {
      outer: ['Outer hull', null, function () { return W(hb - R * 0.3, -R * 0.3); }, 'downright', 40],
      inner: ['Inner hull', null, function () { return W(-(hb - ww - ti), -D * 0.6); }, 'right', 40],
      wing: ['Wing ballast tank', null, function () { return W(hb - ww / 2 - t / 2, -D * 0.8); }, 'upright', 40],
      db: ['Double bottom', null, function () { return W(-xg[0] * 1.5, -hdb / 2 - t / 2); }, 'down', 36],
      cargo: ['Cargo tank', null, function () { return W(xm, -D * 0.45); }, 'up', 10],
      coils: ['Heating coils', null, function () { return W(-66, -hdb - ti - 16); }, 'up', 36],
      pipes: ['Deck pipeline', null, function () { return W(-95 - 8, ps0 - 19); }, 'upleft', 36],
      ig: ['IG main', null, function () { return W(igx + 5, igy - igr + 2); }, 'upright', 36],
      pv: ['P/V valve', null, function () { return W(pvx + 15, pyd - 70); }, 'upright', 36],
      wl: ['Waterline', null, function () { return [cx - hb / Math.cos(h) - 3, SEA]; }, 'upleft', 16],
      breach: ['Breach', 'sea water floods in', function () { return W(hb + 2, yh); }, 'right', 40]
    };
    var LR = Object.keys(LB).map(function (nm) {
      var o = LB[nm], r = { nm: nm, hid: false };
      r.L = f.label({ text: words[nm] || o[0], sub: o[1], side: o[3], dist: o[4],
        at: function () { return r.hid ? [-4000, -4000] : o[2](); },
        show: function () { var v = vis(nm, f.get(p.labels, 0)); r.hid = v < 0.02 && vis(nm, f.target(p.labels, 0)) < 0.5; return v; } });
      return r;
    });
    function placeNew() {                         /* words a step brings in are placed where they go before they fade in */
      var fresh = [];
      LR.forEach(function (r) {
        var was = r.hid; r.hid = vis(r.nm, f.get(p.labels, 0)) < 0.02 && vis(r.nm, f.target(p.labels, 0)) < 0.5;
        if (was && !r.hid) { fresh.push(r); }
      });
      if (!fresh.length) { return; }
      var keep = LR.map(function (r) { return r.L.off && fresh.indexOf(r) < 0 ? r.L.off.slice() : null; });
      fresh.forEach(function (r) { r.L.off = null; });
      f.layout();
      LR.forEach(function (r, i) { if (keep[i]) { r.L.off = keep[i]; } });
      f.follow(0, true);
    }

    function level(L, xp, yp, ang, on) {          /* a liquid's surface through (xp, yp) on the section, ang off level */
      var c = Math.cos(h), sn = Math.sin(h), u = c * xp - sn * (yp + dpx), v = sn * xp + c * (yp + dpx), vy = -Math.sin(ang) * u + Math.cos(ang) * v;
      L.wg.setAttribute('transform', 'translate(0 ' + (-dpx).toFixed(2) + ') rotate(' + ((ang - h) * 180 / PI).toFixed(3) + ')');
      L.r.setAttribute('y', vy.toFixed(1)); L.l.setAttribute('y1', vy.toFixed(1)); L.l.setAttribute('y2', vy.toFixed(1));
      setOp(L.wg, on ? 1 : 0);
    }
    function lvl(xp, v) { return (v - Math.sin(h) * xp) / Math.cos(h) - dpx; }   /* the section's y of a level v (0 = the sea) */

    return {
      onStep: function (n, instant) {
        var b = f.target(p.breach, 0);
        if (!instant && b > 0.5 && lastB <= 0.5) { var a = W(hb, yh); f.pulse(a[0], a[1], { tone: 'amber', r: 64, delay: 150 }); }
        lastB = b;
        placeNew();
      },
      calc: function () {
        var c = clamp(f.get(p.cargo, 0), 0, 1), b = clamp(f.get(p.ballast, 0), 0, 1), fl = clamp(f.get(p.breach, 0), 0, 1);
        var dm = Math.min(5.5 + 3.2 * b + 8 * c + 0.8 * fl, D / k - 2.5);
        hd = (p.list != null ? p.list : 3.8) * fl; h = hd * PI / 180; dpx = dm * k;
        f.publish(p.id, 'draught', dm); f.publish(p.id, 'list', hd); f.publish(p.id, 'cargo', c); f.publish(p.id, 'ballast', b);
      },
      draw: function (dt, snap) {
        var c = clamp(f.get(p.cargo, 0), 0, 1), b = clamp(f.get(p.ballast, 0), 0, 1), fl = clamp(f.get(p.breach, 0), 0, 1), busy = false;
        dt = dt || 0;
        var tr = 'translate(' + cx + ' ' + SEA + ') rotate(' + hd.toFixed(3) + ') translate(0 ' + dpx.toFixed(2) + ')';
        G.back.setAttribute('transform', tr); G.contents.setAttribute('transform', tr); G.hero.setAttribute('transform', tr); G.front.setAttribute('transform', tr);
        /* how fast the cargo comes in: the lines run full and the tank breathes out while it does */
        if (snap || cPrev == null || !dt) { lr = 0; } else { lr = approach(lr, clamp((c - cPrev) / dt * 3, -1, 1), dt, 5); }
        if (Math.abs(lr) < 0.003) { lr = 0; } else { busy = true; }
        cPrev = c;
        setOp(boreOil, Math.min(1, Math.abs(lr) * 1.6));
        wph = (wph + dt * 0.8 * Math.max(0, lr)) % 1;
        wisps.forEach(function (e, i) {
          var u = (wph + i / 3) % 1, a = Math.max(0, lr) * 0.55 * (1 - u) * Math.min(1, u * 5);
          e.setAttribute('cx', (pvx + Math.sin(u * 5 + i * 2) * 4).toFixed(1)); e.setAttribute('cy', (pvTop - 4 - u * 34).toFixed(1));
          e.setAttribute('rx', (5 + u * 9).toFixed(1)); e.setAttribute('ry', (3 + u * 5).toFixed(1)); setOp(e, a);
        });
        /* the liquids lag the list a little and settle back level; pouring in tips the oil a touch */
        var aim = h - lr * 0.014;
        if (snap) { sl = aim; slv = 0; } else {
          slv += (36 * (aim - sl) - 3.4 * slv) * dt; sl += slv * dt;
          if (Math.abs(aim - sl) < 2e-4 && Math.abs(slv) < 5e-4) { sl = aim; slv = 0; } else { busy = true; }
        }
        var ang = h - sl, yc = lerp(-hdb - ti, deckU(xm), c);
        level(LQ.cp, -xm, yc, ang, c > 0.003); level(LQ.cs, xm, yc, ang, c > 0.003);
        [LQ.cp.l, LQ.cs.l].forEach(function (l) { setOp(l, c < 0.995 ? 1 : 0); });
        var yb = lerp(-t, deckU(hb - ww / 2), b), xb = yb > -hdb ? hb / 2 : hb - ww / 2;
        level(LQ.bp, -xb, yb, ang, b > 0.003);
        var co = Math.cos(h), sn = Math.sin(h), vBot = sn * hb / 2 + co * (-t + dpx), vF = lerp(vBot, 0, fl), vB = sn * xb + co * (yb + dpx);
        var vS = Math.min(b > 0.003 ? vB : 1e4, fl > 0.003 ? vF : 1e4);
        level(LQ.bs, xb, lvl(xb, vS), ang, vS < 1e4);
        /* the zone a step lights */
        var hl = f.get(p.highlight, 0);
        Z.forEach(function (g, i) { setOp(g, clamp(1 - Math.abs(hl - (i + 1)), 0, 1)); });
        /* the breach opens with a jolt; the sea pours in until the tank stands at the waterline */
        var bt = f.target(p.breach, 0) > 0.5 ? 1 : 0;
        if (hs.go(bt, dt, snap)) { busy = true; }
        var sc = clamp(hs.x, 0, 1.3);
        hg.setAttribute('transform', 'translate(' + hb + ' ' + yh + ') scale(' + Math.max(0.01, sc).toFixed(3) + ') translate(' + (-hb) + ' ' + (-yh) + ')');
        setOp(hg, sc * 3);
        var pour = bt && !snap ? clamp((1 - fl) * 1.5, 0, 1) * clamp(hs.x, 0, 1) : 0;
        jets.forEach(function (e) {
          if (snap) { e.on = false; }
          if (e.on) {
            e.vy += 320 * dt; e.x += e.vx * dt; e.y += e.vy * dt;
            if (e.x < hb - ww + 3 || e.y > lvl(e.x, vS) || e.y > -t) { e.on = false; }
          }
          if (!e.on && pour > 0.06 && rnd() < dt * 14) {
            e.on = true; e.x = hb + 22 + rnd() * 26; e.y = yh + (rnd() - 0.5) * hh * 1.1; e.vx = -(190 + rnd() * 110); e.vy = (rnd() - 0.45) * 70;
          }
          if (e.on) {
            busy = true;
            e.c.setAttribute('x1', (e.x - e.vx * 0.05).toFixed(1)); e.c.setAttribute('y1', (e.y - e.vy * 0.05).toFixed(1));
            e.c.setAttribute('x2', e.x.toFixed(1)); e.c.setAttribute('y2', e.y.toFixed(1));
          }
          setOp(e.c, e.on ? 0.95 * Math.max(0.35, pour) : 0);
        });
        if (pour > 0.06) { busy = true; }
        moving = busy;
      },
      live: function () { return moving && !f.hidden; }
    };
  });

  /* radar_ppi - a ship's radar display in relative motion: the bezel, the round screen with its range rings and bearing
     scale, own ship and its heading line, a sweep that paints the coast, the targets and the sea clutter as it passes,
     trails, ARPA vectors with the CPA, a VRM and an EBL, and the data column beside the screen. Publishes cpa (nm),
     tcpa (min), rng (nm) and brg of the first target.
     {x, y (the screen's centre), r (the picture's radius), range, rings (nm), up: north | head, own: {course, speed},
      sweep: "@sweep" (revolutions, turned at a steady speed), t: "@t" (minutes), alter (the minute own ship altered),
      trails, vectors, vecmin, limit (CPA limit, nm), clutter (0..1), wind, ringAt (the screen angle of the range figures),
      targets: [{name, brg, rng, course, speed, size, show}] (true course and speed), land: [{from, to, rng, depth}],
      vrm: {rng, show}, ebl: {brg, show}, labels: {own, heading, rings, coast, names, cpa}} */
  define('radar_ppi', function (f, p) {
    var cx = p.x != null ? p.x : 300, cy = p.y != null ? p.y : 300, Rv = p.r || 214, Rs = Rv + 50, RG = p.range || 6, K = Rv / RG;
    var ring = p.rings || RG / 4, own = p.own || {}, vmin = p.vecmin || 6, lim = p.limit || 1, LB = p.labels || {}, D2R = Math.PI / 180;
    var REV = (p.rev || 2.2) * 1000, TAU = 320, STEADY = 0.66, seed = p.seed || 11, VR = p.vrm || {}, EB = p.ebl || {}, i, k;
    var X0 = cx - Rs - 22, Y0 = cy - Rs - 22, X1 = p.w ? X0 + p.w : f.W - X0, Y1 = cy + Rs + 22, CX0 = cx + Rs + 22, CX1 = X1 - 30;
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    function vel(c, s) { return [s * Math.sin(c * D2R), s * Math.cos(c * D2R)]; }        /* also a place: bearing, range */
    function brgOf(q) { return (Math.atan2(q[0], q[1]) / D2R + 360) % 360; }
    function rot() { return p.up === 'head' ? f.get(own.course, 0) : 0; }
    function polarS(a, rr) { return [cx + rr * Math.sin(a * D2R), cy - rr * Math.cos(a * D2R)]; }   /* a screen angle, 0 up */
    function polar(b, rr) { return polarS(b - rot(), rr); }                                           /* a true bearing */
    function scr0(q) { return [cx + q[0] * K, cy - q[1] * K]; }
    function scr(q) { var a = rot() * D2R, c = Math.cos(a), s = Math.sin(a); return [cx + (q[0] * c - q[1] * s) * K, cy - (q[0] * s + q[1] * c) * K]; }
    function deg3(v) { v = ((v % 360) + 360) % 360; var s = v.toFixed(1); return (s.length < 4 ? '00' : s.length < 5 ? '0' : '') + s + '°'; }
    function pieces(a, b) { var n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / 24)), q = [], j; for (j = 0; j <= n; j++) { q.push([lerp(a[0], b[0], j / n), lerp(a[1], b[1], j / n)]); } return q; }
    function put(n, s) { if (n.textContent !== s) { n.textContent = s; } }
    /* relative motion: a thing's velocity less own ship's; its place at minute tm on the first course up to the
       alteration and on the present course after it; its CPA from where it is and its relative velocity */
    function relV(vt, c) { var o = vel(c, f.get(own.speed, 12)); return [vt[0] - o[0], vt[1] - o[1]]; }
    function where(p0, vt, tm) {
      var ta = p.alter != null ? p.alter : 1e9, v0 = relV(vt, f.rest(own.course, 0)), v1 = relV(vt, f.get(own.course, 0));
      var t1 = Math.min(tm, ta) / 60, t2 = Math.max(0, tm - ta) / 60;
      return [p0[0] + v0[0] * t1 + v1[0] * t2, p0[1] + v0[1] * t1 + v1[1] * t2];
    }
    function cpaOf(q, v) {
      var vv = v[0] * v[0] + v[1] * v[1], th = vv > 1e-9 ? -(q[0] * v[0] + q[1] * v[1]) / vv : 0, c = [q[0] + v[0] * th, q[1] + v[1] * th];
      return { cpa: Math.hypot(c[0], c[1]), tcpa: th * 60, at: c };
    }
    var gid = f.id + '-rd' + (++UID);
    stops(el('radialGradient', { id: gid + 's', cx: 0.46, cy: 0.42, r: 0.6 }, f.defs), [[0, 'k2-s-rd-scope-hi'], [1, 'k2-s-rd-scope-lo']]);
    stops(el('radialGradient', { id: gid + 'v' }, f.defs), [[0.8, 'k2-s-rd-shade', 0], [1, 'k2-s-rd-shade', 0.6]]);
    stops(el('linearGradient', { id: gid + 'g', x1: 0.1, y1: 0, x2: 0.6, y2: 0.75 }, f.defs), [[0, 'k2-s-rd-sheen', 0.1], [0.45, 'k2-s-rd-sheen', 0.03], [1, 'k2-s-rd-sheen', 0]]);
    stops(el('linearGradient', { id: gid + 'p', x1: 0, y1: 0, x2: 0, y2: 1 }, f.defs), [[0, 'k2-s-rd-panel-hi'], [1, 'k2-s-rd-panel-lo']]);

    /* the console: a metal bezel, the glass, the round screen sunk in it */
    f.shadow((X0 + X1) / 2, Y1 + 4, (X1 - X0) * 0.5, 18);
    var bz = 'M' + (X0 + 28) + ' ' + Y0 + ' H' + (X1 - 28) + ' Q' + X1 + ' ' + Y0 + ' ' + X1 + ' ' + (Y0 + 28) + ' V' + (Y1 - 28) + ' Q' + X1 + ' ' + Y1 + ' ' + (X1 - 28) + ' ' + Y1 +
      ' H' + (X0 + 28) + ' Q' + X0 + ' ' + Y1 + ' ' + X0 + ' ' + (Y1 - 28) + ' V' + (Y0 + 28) + ' Q' + X0 + ' ' + Y0 + ' ' + (X0 + 28) + ' ' + Y0 + ' Z';
    el('path', { d: bz, 'class': 'k2-outline-s', 'stroke-width': 6, 'stroke-linejoin': 'round' }, f.L.back);
    el('path', { d: bz, fill: f.url('metal') }, f.L.back);
    el('path', { d: bz, 'class': 'k2-edge' }, f.L.back);
    el('rect', { x: X0 + 12, y: Y0 + 12, width: X1 - X0 - 24, height: Y1 - Y0 - 24, rx: 17, 'class': 'k2-outline' }, f.L.back);
    el('rect', { x: X0 + 15, y: Y0 + 15, width: X1 - X0 - 30, height: Y1 - Y0 - 30, rx: 14, 'class': 'k2-rd-glass' }, f.L.back);
    [[X0 + 7, Y0 + 7], [X1 - 7, Y0 + 7], [X0 + 7, Y1 - 7], [X1 - 7, Y1 - 7]].forEach(function (q) {
      el('circle', { cx: q[0], cy: q[1], r: 4.5, 'class': 'k2-outline' }, f.L.back);
      el('circle', { cx: q[0], cy: q[1], r: 3.2, fill: f.url('metal') }, f.L.back);
      el('path', { d: 'M' + (q[0] - 2.2) + ' ' + (q[1] + 2.2) + ' L' + (q[0] + 2.2) + ' ' + (q[1] - 2.2), 'class': 'k2-rd-slot' }, f.L.back);
    });
    el('circle', { cx: cx, cy: cy, r: Rs + 6, 'class': 'k2-outline' }, f.L.back);
    el('circle', { cx: cx, cy: cy, r: Rs + 3, 'class': 'k2-rd-rim' }, f.L.back);
    el('circle', { cx: cx, cy: cy, r: Rs, fill: 'url(#' + gid + 's)' }, f.L.back);
    el('circle', { cx: cx, cy: cy, r: Rs + 6.5, 'class': 'k2-edge' }, f.L.back);
    /* range rings, the bearing scale: a tick each degree, longer each 5 and 10, its figures each 30 */
    for (k = 1; k * ring < RG - 1e-6; k++) { el('circle', { cx: cx, cy: cy, r: k * ring * K, 'class': 'k2-rd-ring' }, f.L.back); }
    el('circle', { cx: cx, cy: cy, r: Rv, 'class': 'k2-rd-edge' }, f.L.back);
    var scale = el('g', {}, f.L.back), t1 = '', t10 = '';
    for (k = 0; k < 360; k++) {
      var tl = k % 10 === 0 ? 14 : k % 5 === 0 ? 9 : 5, qa = polarS(k, Rv + 1), qb = polarS(k, Rv + 1 + tl), seg = 'M' + pt(qa) + ' L' + pt(qb) + ' ';
      if (k % 10 === 0) { t10 += seg; } else { t1 += seg; }
    }
    el('path', { d: t1, 'class': 'k2-rd-tick' }, scale);
    el('path', { d: t10, 'class': 'k2-rd-tick k2-rd-tick-10' }, scale);
    el('circle', { cx: cx, cy: cy, r: Rs - 6, 'class': 'k2-rd-ring' }, scale);
    var nums = [];
    for (k = 0; k < 360; k += 30) {
      nums.push({ b: k, n: el('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'class': 'k2-t-tick k2-rd-num' }, f.L.back, (k < 100 ? (k < 10 ? '00' : '0') : '') + k) });
    }
    var figs = [];
    for (k = 1; k * ring < RG - 1e-6; k++) {
      var fq = polarS(p.ringAt != null ? p.ringAt : 160, k * ring * K);
      figs.push(el('text', { x: fq[0].toFixed(1), y: fq[1].toFixed(1), 'text-anchor': 'middle', 'dominant-baseline': 'central', 'class': 'k2-t-tick k2-rd-num k2-halo k2-rd-halo' }, f.L.hero, num(k * ring, (k * ring) % 1 ? 1 : 0)));
    }

    /* what the sweep paints, all inside the picture's circle: clutter round own ship, the land, trails, the targets */
    var cid = gid + 'c';
    el('circle', { cx: cx, cy: cy, r: Rv }, el('clipPath', { id: cid }, f.defs));
    var vid = el('g', { 'clip-path': 'url(#' + cid + ')' }, f.L.contents);
    var wedge = el('g', {}, vid), clutG = el('g', {}, vid), landG = el('g', {}, vid), landB = el('g', {}, landG), landH = el('g', {}, landG), trailG = el('g', {}, vid), echoG = el('g', {}, vid), E = [];
    for (k = 1; k <= 18; k++) {         /* the afterglow behind the trace: thin sectors laid over each other, brightest at the trace */
      el('path', { d: 'M' + cx + ' ' + cy + ' L' + pt(polarS(-k * 4, Rv)) + ' A' + Rv + ' ' + Rv + ' 0 0 1 ' + pt(polarS(0, Rv)) + ' Z', 'class': 'k2-rd-wedge' }, wedge);
    }
    function shape(q, box) {
      q.forEach(function (s) { box.x = Math.min(box.x, s[0]); box.y = Math.min(box.y, s[1]); box.x2 = Math.max(box.x2, s[0]); box.y2 = Math.max(box.y2, s[1]); });
      return poly(q, true) + ' ';
    }
    function blob(b, r, wa, wr, box) {  /* a patch of echo: a wobbly oval wa degrees wide and wr nm deep at bearing b, range r */
      var q = [], j;
      for (j = 0; j < 9; j++) { var a = j / 9 * 2 * Math.PI, m = 0.7 + rnd() * 0.45; q.push(scr0(vel(b + Math.cos(a) * wa / 2 * m, r + Math.sin(a) * wr / 2 * m))); }
      return shape(q, box);
    }
    function shore(L0, s, b) {          /* the shore's range at bearing b: bays and headlands, tapering off at the ends */
      var u = (b - L0.from) / (L0.to - L0.from), tp = Math.sqrt(clamp(Math.min(u, 1 - u) / 0.16, 0, 1)), wg = L0.wiggle != null ? L0.wiggle : 1;
      return { r: L0.rng + wg * (0.7 * Math.sin(b * 0.071 + s[0]) + 0.32 * Math.sin(b * 0.19 + s[1]) + 0.14 * Math.sin(b * 0.57 + s[2])) + (1 - tp) * 0.4, tp: tp };
    }
    var coastAt = null;
    (p.land || []).forEach(function (L0, li) {
      var s = [rnd() * 6.3, rnd() * 6.3, rnd() * 6.3], st = L0.step || 1.5, span = L0.to - L0.from, dep = L0.depth || 1, b;
      for (b = L0.from; b < L0.to - 1e-6; b += st) {
        var P = shore(L0, s, b), Q = shore(L0, s, b + st), M = shore(L0, s, b + st / 2), box = { x: 1e9, y: 1e9, x2: -1e9, y2: -1e9 }, j;
        var dd = function () { return (0.14 + 0.18 * rnd()) * (0.35 + 0.65 * M.tp); };
        /* the shore line itself returns a strong, unbroken echo */
        var d = shape([scr0(vel(b - st * 0.2, P.r)), scr0(vel(b + st / 2, M.r - 0.02)), scr0(vel(b + st * 1.2, Q.r)),
          scr0(vel(b + st * 1.2, Q.r + dd())), scr0(vel(b + st / 2, M.r + dd() + 0.04)), scr0(vel(b - st * 0.2, P.r + dd()))], box);
        for (j = 0; j < 5; j++) {          /* behind the shore the hills return patchy echoes, shadowed in between */
          var o = Math.pow(rnd(), 1.1) * dep * M.tp;
          if (rnd() < (0.7 - 0.45 * o / dep) * M.tp) { d += blob(b + st * rnd(), M.r + 0.32 + o, st * (0.5 + 1.1 * rnd()), 0.08 + 0.22 * rnd(), box); }
        }
        E.push({ n: el('path', { d: d, 'class': 'k2-rd-land' }, landB), h: el('path', { d: d, 'class': 'k2-rd-land-hot' }, landH),
                 c: vel(b + st / 2, M.r), box: box, kind: 'land', on: false, pt: -1e9, lo: 9 });
        if (li === 0 && Math.abs(b + st / 2 - (L0.from + L0.to) / 2) <= st / 2 + 1e-6) { coastAt = vel(b + st / 2, M.r); }
      }
    });
    var cb = {}, CL = p.clutterR || 1.7, wind = p.wind != null ? p.wind : 30;
    for (k = 0; k < 900; k++) {            /* sea clutter: dense close in, thinning out, more on the weather side */
      var cbb = rnd() * 360, crr = 0.12 + CL * Math.pow(rnd(), 2), cup = (Math.cos((cbb - wind) * D2R) + 1) / 2;
      if (rnd() > 0.3 + 0.7 * cup) { continue; }
      var sec = Math.floor(cbb / 5), cq = scr0(vel(cbb, crr)), cr = (0.6 + 1.3 * rnd() * (1 - crr / (CL + 0.3))).toFixed(1);
      cb[sec] = (cb[sec] || '') + 'M' + (cq[0] - cr).toFixed(1) + ' ' + cq[1].toFixed(1) + ' a' + cr + ' ' + cr + ' 0 1 0 ' + (2 * cr).toFixed(1) + ' 0 a' + cr + ' ' + cr + ' 0 1 0 ' + (-2 * cr).toFixed(1) + ' 0 ';
    }
    for (k in cb) { E.push({ n: el('path', { d: cb[k], 'class': 'k2-rd-echo' }, clutG), b: (+k + 0.5) * 5, kind: 'clut', on: false, pt: -1e9, lo: 9 }); }
    var arpa = el('g', {}, f.L.hero);
    var TG = (p.targets || []).map(function (t) {
      var o = { t: t, p0: vel(t.brg, t.rng), vt: vel(t.course || 0, t.speed || 0), w: t.size || 10, kind: 'tgt', on: false, pt: -1e9, lo: 9, dots: [], s: [cx, cy] };
      for (k = 1; k <= 12; k++) { o.dots.push(el('circle', { r: (2.7 - k * 0.1).toFixed(2), 'class': 'k2-rd-echo' }, trailG)); }
      o.n = el('path', { 'class': 'k2-rd-blip' }, echoG);
      o.hot = el('path', { 'class': 'k2-rd-blip-hot' }, echoG);
      o.vec = el('path', { 'class': 'k2-arrow k2-rd-vec' }, arpa);
      o.sym = el('circle', { r: 15, 'class': 'k2-rd-sym' }, arpa);
      E.push(o);
      return o;
    });
    var A = TG[0], sel = el('path', { 'class': 'k2-rd-sel' }, arpa), track = el('path', { 'class': 'k2-arrow k2-rd-track' }, arpa);
    var mark = el('path', { d: 'M0 -7 L7 0 L0 7 L-7 0 Z', 'class': 'k2-rd-cpa' }, arpa);
    /* own ship, its heading line, the VRM and the EBL; the trace above the picture; the glass over it all */
    var vrm = el('circle', { cx: cx, cy: cy, r: 1, 'class': 'k2-rd-vrm' }, f.L.hero), ebl = el('path', { 'class': 'k2-arrow k2-rd-ebl' }, f.L.hero);
    var head = el('path', { 'class': 'k2-arrow k2-rd-head' }, f.L.hero);
    var ship = el('path', { d: 'M0 -15 C5 -9 6.5 -3 6 4 L5 11 H-5 L-6 4 C-6.5 -3 -5 -9 0 -15 Z', 'class': 'k2-rd-own' }, f.L.hero);
    el('circle', { cx: cx, cy: cy, r: 2.2, 'class': 'k2-rd-ccrp' }, f.L.hero);
    var trace = el('g', {}, f.L.fx);
    el('path', { d: 'M' + cx + ' ' + cy + ' V' + (cy - Rv), 'class': 'k2-rd-trace-glow' }, trace);
    el('path', { d: 'M' + cx + ' ' + cy + ' V' + (cy - Rv), 'class': 'k2-rd-trace' }, trace);
    el('circle', { cx: cx, cy: cy, r: Rs, fill: 'url(#' + gid + 'v)' }, f.L.fx);
    el('circle', { cx: cx, cy: cy, r: Rs, fill: 'url(#' + gid + 'g)' }, f.L.front);

    /* the data column: radar settings, own ship and the markers, the target's ARPA data, the picture controls */
    var cw = (CX1 - CX0) / 2;
    function panel(y, h) {
      var g = el('g', {}, f.L.front), r = el('rect', { x: CX0, y: y, width: CX1 - CX0, height: h, rx: 9, fill: 'url(#' + gid + 'p)', 'class': 'k2-rd-panel' }, g);
      holds(g, r); return g;
    }
    function cell(g, x, y, name) {
      el('text', { x: x + 14, y: y + 22, 'class': 'k2-t-name k2-rd-dim' }, g, name);
      return el('text', { x: x + 14, y: y + 48, 'class': 'k2-t-lbl k2-rd-ink' }, g, '');
    }
    var py = Y0 + 24, g1 = panel(py, 120), V = {};
    put(cell(g1, CX0, py + 4, 'Range'), num(RG, RG % 1 ? 1 : 0) + ' nm'); put(cell(g1, CX0 + cw, py + 4, 'Rings'), num(ring, ring % 1 ? 1 : 0) + ' nm');
    put(cell(g1, CX0, py + 60, 'Mode'), (p.up === 'head' ? 'Head up' : 'North up') + ' RM'); put(cell(g1, CX0 + cw, py + 60, 'Vector'), 'Rel ' + vmin + ' min');
    py += 129; var g2 = panel(py, 120);
    V.hdg = cell(g2, CX0, py + 4, 'Heading'); V.spd = cell(g2, CX0 + cw, py + 4, 'Speed');
    V.vrm = cell(g2, CX0, py + 60, 'VRM'); V.ebl = cell(g2, CX0 + cw, py + 60, 'EBL');
    py += 129; var g3 = panel(py, 190);
    el('text', { x: CX0 + 14, y: py + 26, 'class': 'k2-t-name k2-rd-ink' }, g3, A ? A.t.name || 'Target' : 'Target');
    V.st = el('text', { x: CX1 - 14, y: py + 26, 'text-anchor': 'end', 'class': 'k2-t-name k2-rd-dim' }, g3, '');
    V.brg = cell(g3, CX0, py + 34, 'Bearing'); V.rng = cell(g3, CX0 + cw, py + 34, 'Range');
    V.cpa = cell(g3, CX0, py + 90, 'CPA'); V.tcpa = cell(g3, CX0 + cw, py + 90, 'TCPA');
    var alarm = el('rect', { x: CX0 + 8, y: py + 150, width: CX1 - CX0 - 16, height: 32, rx: 6, 'class': 'k2-rd-alarm' }, g3);
    V.al = el('text', { x: CX0 + 20, y: py + 166, 'dominant-baseline': 'central', 'class': 'k2-t-name k2-rd-dim' }, g3, '');
    py += 199; var g4 = panel(py, Y1 - 24 - py), bars = {}, c3 = (CX1 - CX0) / 3;
    [['Gain', 0.7], ['Sea', 0], ['Rain', 0.25]].forEach(function (b, j) {
      var bx = CX0 + j * c3 + 14, segs = [];
      el('text', { x: bx, y: py + 24, 'class': 'k2-t-name k2-rd-dim' }, g4, b[0]);
      for (k = 0; k < 8; k++) {
        el('rect', { x: bx + k * 11.5, y: py + 36, width: 9, height: 13, rx: 2, 'class': 'k2-rd-seg' }, g4);
        segs.push(el('rect', { x: bx + k * 11.5, y: py + 36, width: 9, height: 13, rx: 2, 'class': 'k2-rd-seg-on' }, g4));
      }
      bars[b[0]] = { segs: segs, v: b[1] };
    });

    /* words: each shown by its own state; while hidden it stands aside, so it keeps no room from the others */
    function lab(o, show) {
      var at = o.at;
      o.show = function () { return clamp(f.get(show, 0), 0, 1); };
      o.at = function () { return f.target(show, 0) < 0.5 && f.get(show, 0) < 0.02 ? [-4000, -4000] : at(); };
      return f.label(o);
    }
    var cpaNow = null;
    if (LB.own) { lab({ text: 'Own ship', at: function () { return [cx, cy]; }, r: 15, side: 'downright' }, LB.own); }
    if (LB.heading) { lab({ text: 'Heading line', at: function () { return polar(f.get(own.course, 0), Rv * 0.62); }, side: 'right' }, LB.heading); }
    if (LB.rings) { lab({ text: 'Range rings', sub: num(ring, ring % 1 ? 1 : 0) + ' nm apart', at: function () { return polarS(p.ringsLabelAt != null ? p.ringsLabelAt : 215, 2 * ring * K); }, side: 'left' }, LB.rings); }
    if (LB.coast && coastAt) { lab({ text: 'Coast', at: function () { return scr(where(coastAt, [0, 0], f.get(p.t, 0))); }, side: 'right' }, LB.coast); }
    TG.forEach(function (o) {
      var sh = o.t.show != null ? o.t.show : LB.names;
      if (sh != null && o.t.name) { lab({ text: o.t.name, at: function () { return o.s; }, r: 15, side: 'right' }, sh); }
    });
    if (LB.cpa && A) { lab({ text: 'CPA', live: function () { return 'CPA ' + num(cpaNow ? cpaNow.cpa : 0, 1) + ' nm'; }, at: function () { return cpaNow ? scr(cpaNow.at) : [cx, cy]; }, r: 8, side: 'downleft' }, LB.cpa); }
    if (VR.show != null) { lab({ text: 'VRM', live: function () { return 'VRM ' + num(f.get(VR.rng, 0), 1) + ' nm'; }, at: function () { return polarS(135, f.get(VR.rng, 0) * K); }, side: 'downright' }, VR.show); }
    if (EB.show != null) { lab({ text: 'EBL', live: function () { return 'EBL ' + deg3(f.get(EB.brg, 0)); }, at: function () { return polar(f.get(EB.brg, 0), Rv * 0.9); }, side: 'left' }, EB.show); }

    /* what labels keep clear of */
    var off = [0, 0];
    f.solid(function () { return { x: cx - 17, y: cy - 17, x2: cx + 17, y2: cy + 17 }; });
    f.solid(function () { return { x: CX0 - 8, y: Y0, x2: X1, y2: Y1 }; });
    f.solid(function () { var o = [], a; for (a = 0; a < 360; a += 10) { var q = polarS(a, Rv + 25); o.push({ x: q[0] - 21, y: q[1] - 17, x2: q[0] + 21, y2: q[1] + 17 }); } return o; });
    f.solid(function () { return figs.map(function (n) { var b = n.getBBox(); return { x: b.x - 4, y: b.y - 2, x2: b.x + b.width + 4, y2: b.y + b.height + 2 }; }); });
    f.solid(function () { return TG.map(function (o) { return o.on ? { x: o.s[0] - 18, y: o.s[1] - 18, x2: o.s[0] + 18, y2: o.s[1] + 18 } : null; }); });
    f.solid(function () {
      var dx = off[0] * K, dy = -off[1] * K;
      return E.map(function (e) { return e.kind === 'land' && e.on ? { x: e.box.x + dx, y: e.box.y + dy, x2: e.box.x2 + dx, y2: e.box.y2 + dy } : null; });
    });
    f.line(function () { return pieces([cx, cy], polar(f.get(own.course, 0), Rv + 14)); });
    f.line(function () { return f.get(EB.show, 0) > 0.5 ? pieces([cx, cy], polar(f.get(EB.brg, 0), Rv)) : []; });
    TG.forEach(function (o) { f.line(function () { return f.get(p.vectors, 0) > 0.5 && o.tip ? pieces(o.s, o.tip) : []; }); });
    f.line(function () { return cpaNow && f.get(p.vectors, 0) > 0.5 && cpaNow.tcpa > 0 ? pieces(A.s, scr(cpaNow.at)) : []; });

    var ang = 0, vis = 0, lastPaint = -1e9, tNow = 0, lastVec = f.target(p.vectors, 0), lastCrs = f.target(own.course, 0);
    function glowOf(e) { return e.on ? Math.exp(-(tNow - e.pt) / TAU) : 0; }
    return {
      onStep: function (n, instant) {
        var v = f.target(p.vectors, 0), c = f.target(own.course, 0);
        if (!instant && A && v > 0.5 && lastVec <= 0.5) { f.pulse(A.s[0], A.s[1], { delay: 250, r: 40, tone: cpaNow && cpaNow.cpa < lim ? 'amber' : null }); }
        if (!instant && Math.abs(c - lastCrs) > 0.5) { f.pulse(cx, cy, { delay: 200, r: 50 }); }
        lastVec = v; lastCrs = c;
      },
      calc: function () {
        var tm = f.get(p.t, 0), c = f.get(own.course, 0);
        off = where([0, 0], [0, 0], tm);
        TG.forEach(function (o) {
          o.q = where(o.p0, o.vt, tm); o.v = relV(o.vt, c); o.c = cpaOf(o.q, o.v);
          o.s = scr(o.q); o.tip = scr([o.q[0] + o.v[0] * vmin / 60, o.q[1] + o.v[1] * vmin / 60]);
        });
        if (A) {
          cpaNow = A.c;
          f.publish(p.id, 'cpa', A.c.cpa); f.publish(p.id, 'tcpa', A.c.tcpa);
          f.publish(p.id, 'rng', Math.hypot(A.q[0], A.q[1])); f.publish(p.id, 'brg', brgOf(A.q));
        }
      },
      draw: function (dt, snap) {
        var r0 = rot(), c = f.get(own.course, 0), tm = f.get(p.t, 0), clut = clamp(f.get(p.clutter, 1), 0, 1), vec = clamp(f.get(p.vectors, 0), 0, 1);
        var tr = clamp(f.get(p.trails, 0), 0, 1), tg = Math.max(0, f.target(p.sweep, 0)), a0 = ang, moved = false;
        tNow = now(); dt = dt || 0;
        /* the bearing scale and the picture turn with the ship's head when head up */
        scale.setAttribute('transform', 'rotate(' + (-r0).toFixed(2) + ' ' + cx + ' ' + cy + ')');
        nums.forEach(function (o) { var q = polarS(o.b - r0, Rv + 29); o.n.setAttribute('x', q[0].toFixed(1)); o.n.setAttribute('y', q[1].toFixed(1)); });
        landG.setAttribute('transform', 'rotate(' + (-r0).toFixed(2) + ' ' + cx + ' ' + cy + ') translate(' + (off[0] * K).toFixed(2) + ' ' + (-off[1] * K).toFixed(2) + ')');
        clutG.setAttribute('transform', 'rotate(' + (-r0).toFixed(2) + ' ' + cx + ' ' + cy + ')');
        E.forEach(function (e) {             /* where each echo is on the screen, as an angle from the top */
          var b = e.kind === 'land' ? brgOf([e.c[0] + off[0], e.c[1] + off[1]]) : e.kind === 'clut' ? e.b : brgOf(e.q);
          e.es = ((b - r0) % 360 + 360) % 360;
        });
        /* the sweep: turned at a steady speed to the count the step asks for; an echo paints as the trace passes it */
        if (snap || tg < ang - 1e-6) {
          ang = tg;
          E.forEach(function (e) { e.on = ang > 1e-6 && (ang >= 1 || ang * 360 >= e.es); e.pt = -1e9; });
        } else if (tg > ang) {
          if (tg - ang > 1) { ang = a0 = tg - 1; }
          ang = Math.min(tg, ang + dt * 1000 / REV); moved = true;
          var A0 = a0 * 360, A1 = ang * 360;
          E.forEach(function (e) { if (Math.floor((A1 - e.es) / 360) > Math.floor((A0 - e.es) / 360)) { e.on = true; e.pt = tNow; lastPaint = tNow; } });
        }
        vis = snap ? 0 : moved ? approach(vis, 1, dt, 16) : approach(vis, 0, dt, 7);
        if (vis < 0.004) { vis = 0; }
        trace.setAttribute('transform', 'rotate(' + ((ang % 1) * 360).toFixed(2) + ' ' + cx + ' ' + cy + ')'); setOp(trace, vis);
        wedge.setAttribute('transform', trace.getAttribute('transform')); setOp(wedge, vis);
        E.forEach(function (e) {
          var v = e.on ? (e.h ? glowOf(e) : (STEADY + (1 - STEADY) * glowOf(e)) * (e.kind === 'clut' ? clut : 1)) : -1;
          if (Math.abs(v - e.lo) > 0.004) {      /* land: an opaque steady echo, and its fresh paint over it */
            if (e.h) { setOp(e.n, v < 0 ? 0 : 1); setOp(e.h, Math.max(0, v)); } else { setOp(e.n, Math.max(0, v)); }
            e.lo = v;
          }
        });
        /* the targets: an echo as wide as its bearing spread, its trail of past places, its ARPA symbol and vector */
        TG.forEach(function (o, j) {
          var s = o.s, rr = Math.max(20, Math.hypot(s[0] - cx, s[1] - cy)), sa = Math.atan2(s[0] - cx, cy - s[1]) / D2R, hw = o.w / 2 / rr / D2R;
          var d = 'M' + pt(polarS(sa - hw, rr)) + ' A' + rr.toFixed(1) + ' ' + rr.toFixed(1) + ' 0 0 1 ' + pt(polarS(sa + hw, rr));
          o.n.setAttribute('d', d); o.hot.setAttribute('d', d); setOp(o.hot, glowOf(o));
          o.dots.forEach(function (dn, m) {
            var q = scr(where(o.p0, o.vt, tm - (m + 1) * 0.5));
            dn.setAttribute('cx', q[0].toFixed(1)); dn.setAttribute('cy', q[1].toFixed(1)); setOp(dn, o.on ? tr * (1 - (m + 1) / 13) * 0.9 : 0);
          });
          var hot = o.c.cpa < lim && o.c.tcpa > 0, cls = hot ? ' k2-rd-hot' : '';
          if (o.cls !== cls) { o.cls = cls; o.vec.setAttribute('class', 'k2-arrow k2-rd-vec' + cls); o.sym.setAttribute('class', 'k2-rd-sym' + cls); }
          o.vec.setAttribute('d', 'M' + pt(s) + ' L' + pt(o.tip)); setOp(o.vec, vec * (o.on ? 1 : 0));
          o.sym.setAttribute('cx', s[0].toFixed(1)); o.sym.setAttribute('cy', s[1].toFixed(1)); setOp(o.sym, vec * (o.on ? 1 : 0));
        });
        if (A) {                              /* the first target is selected: its brackets, its track to the CPA, the CPA */
          var s = A.s, b = 22, e = 7, hc = A.cls ? ' k2-rd-hot' : '';
          sel.setAttribute('d', [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(function (q) {
            var x = s[0] + q[0] * b, y = s[1] + q[1] * b;
            return 'M' + (x - q[0] * e).toFixed(1) + ' ' + y.toFixed(1) + ' H' + x.toFixed(1) + ' V' + (y - q[1] * e).toFixed(1);
          }).join(' '));
          setOp(sel, vec);
          var cq = scr(A.c.at), ahead = A.c.tcpa > 0 ? 1 : 0;
          track.setAttribute('d', 'M' + pt(s) + ' L' + pt(cq)); track.setAttribute('class', 'k2-arrow k2-rd-track' + hc); setOp(track, vec * ahead);
          mark.setAttribute('transform', 'translate(' + pt(cq) + ')'); mark.setAttribute('class', 'k2-rd-cpa' + hc); setOp(mark, vec * ahead);
        }
        /* own ship, its heading line, the VRM and the EBL */
        var hq = polar(c, Rv + 14);
        head.setAttribute('d', 'M' + cx + ' ' + cy + ' L' + pt(hq));
        ship.setAttribute('transform', 'translate(' + cx + ' ' + cy + ') rotate(' + (c - r0).toFixed(2) + ')');
        var vr = Math.max(0, f.get(VR.rng, 0)), vs = clamp(f.get(VR.show, 0), 0, 1), eb = f.get(EB.brg, 0), es = clamp(f.get(EB.show, 0), 0, 1);
        vrm.setAttribute('r', Math.max(1, vr * K).toFixed(1)); setOp(vrm, vs);
        ebl.setAttribute('d', 'M' + cx + ' ' + cy + ' L' + pt(polar(eb, Rv))); setOp(ebl, es);
        /* the data column */
        put(V.hdg, deg3(c)); put(V.spd, num(f.get(own.speed, 12), 1) + ' kn');
        put(V.vrm, vs > 0.5 ? num(vr, 2) + ' nm' : 'Off'); put(V.ebl, es > 0.5 ? deg3(eb) : 'Off');
        var on = A && vec > 0.5;
        put(V.st, on ? 'Tracked' : 'Not tracked');
        put(V.brg, on ? deg3(brgOf(A.q)) : '—'); put(V.rng, on ? num(Math.hypot(A.q[0], A.q[1]), 2) + ' nm' : '—');
        put(V.cpa, on ? num(A.c.cpa, 2) + ' nm' : '—'); put(V.tcpa, on ? num(A.c.tcpa, 1) + ' min' : '—');
        var al = on && A.cls ? 1 : 0;
        setOp(alarm, al);
        put(V.al, al ? 'CPA alarm: under ' + num(lim, 1) + ' nm' : 'CPA limit ' + num(lim, 1) + ' nm');
        V.al.setAttribute('class', al ? 'k2-t-name k2-rd-alarm-t' : 'k2-t-name k2-rd-dim');
        bars.Sea.v = 1 - clut;
        Object.keys(bars).forEach(function (n) { bars[n].segs.forEach(function (sg, m) { setOp(sg, clamp(bars[n].v * 8 - m, 0, 1)); }); });
      },
      live: function () { return !f.hidden && (Math.max(0, f.target(p.sweep, 0)) > ang + 1e-9 || vis > 0 || now() - lastPaint < TAU * 4.2); }
    };
  });

  /* kanban - a team's kanban board on the wall: an aluminium-framed whiteboard, its columns taped off and headed in
     marker with their WIP limits, sticky-note cards (who owns each, a Bug / Feature tag) that are pulled from column to
     column - a card lifts, glides on a gentle arc and lands, and the cards it left close the gap - a WIP badge that
     turns amber when its column holds more than the limit, a red magnet on a blocked card, a marker tray below.
     {x, y, w, h (the frame), columns: [{name, wip}], cards: [{id, text, who, cat, tag, col: "@c_a" | 0.., order,
      blocked: "@b_a"}], labels: [{text, sub, card, edge: left | right | bottom | pin, col, side, dist, show}]}
     - publishes done (cards in the last column), over (columns over their limit) and n0, n1, .. (cards in each) */
  define('kanban', function (f, p) {
    var Cols = p.columns || [], nc = Math.max(1, Cols.length), X0 = p.x != null ? p.x : 22, Y0 = p.y != null ? p.y : 12;
    var W = p.w || f.W - 2 * X0, H = p.h || f.H - Y0 - 46, fr = 12, sx = X0 + fr, sy = Y0 + fr, sw = W - 2 * fr, sh = H - 2 * fr;
    var cw = sw / nc, hy = sy + 32, ty = sy + 84, top = sy + 100, w = Math.min(p.cardW || 216, cw - 40), h = p.cardH || 94, pitch = h + 8;
    var gid = f.id + '-kb' + (++UID), i;
    function paint(name, kind, at, list) {
      var a = { id: gid + '-' + name }, k;
      for (k in at) { a[k] = at[k]; }
      stops(el(kind, a, f.defs), list);
      return 'url(#' + gid + '-' + name + ')';
    }
    /* where a state is going now (a step's "after" holds a card back until its turn) */
    function tv(ref, dflt) {
      if (typeof ref === 'string' && ref.charAt(0) === '@') { var v = f.T[ref.slice(1)]; return v == null ? dflt : v; }
      return f.get(ref, dflt);
    }
    var P = {
      board: paint('board', 'linearGradient', { x1: 0, y1: 0, x2: 1, y2: 1 }, [[0, 'k2-s-kb-board-hi'], [1, 'k2-s-kb-board-lo']]),
      sheen: paint('sheen', 'linearGradient', { x1: 0, y1: 0, x2: 1, y2: 0 }, [[0, 'k2-s-kb-sheen', 0], [0.5, 'k2-s-kb-sheen', 0.9], [1, 'k2-s-kb-sheen', 0]]),
      lip: paint('lip', 'linearGradient', { x1: 0, y1: 0, x2: 0, y2: 1 }, [[0, 'k2-s-kb-ink', 0.2], [1, 'k2-s-kb-ink', 0]]),
      aluV: paint('aluv', 'linearGradient', { x1: 0, y1: 0, x2: 0, y2: 1 }, [[0, 'k2-s-kb-alu-hi'], [0.4, 'k2-s-kb-alu-mid'], [0.55, 'k2-s-kb-alu-hi'], [1, 'k2-s-kb-alu-lo']]),
      aluH: paint('aluh', 'linearGradient', { x1: 0, y1: 0, x2: 1, y2: 0 }, [[0, 'k2-s-kb-alu-hi'], [0.4, 'k2-s-kb-alu-mid'], [0.55, 'k2-s-kb-alu-hi'], [1, 'k2-s-kb-alu-lo']]),
      corner: paint('corner', 'linearGradient', { x1: 0, y1: 0, x2: 1, y2: 1 }, [[0, 'k2-s-kb-corner-hi'], [1, 'k2-s-kb-corner-lo']]),
      tapeV: paint('tapev', 'linearGradient', { x1: 0, y1: 0, x2: 1, y2: 0 }, [[0, 'k2-s-kb-tape-lo'], [0.5, 'k2-s-kb-tape-hi'], [1, 'k2-s-kb-tape-lo']]),
      tapeH: paint('tapeh', 'linearGradient', { x1: 0, y1: 0, x2: 0, y2: 1 }, [[0, 'k2-s-kb-tape-lo'], [0.5, 'k2-s-kb-tape-hi'], [1, 'k2-s-kb-tape-lo']]),
      paper: paint('paper', 'linearGradient', { x1: 0, y1: 0, x2: 0.5, y2: 1 }, [[0, 'k2-s-kb-sheen', 0.42], [0.45, 'k2-s-kb-sheen', 0.14], [0.85, 'k2-s-kb-sheen', 0], [1, 'k2-s-kb-ink', 0.08]]),
      curl: paint('curl', 'linearGradient', { x1: 1, y1: 1, x2: 0, y2: 0 }, [[0, 'k2-s-kb-ink', 0.26], [0.22, 'k2-s-kb-ink', 0.08], [0.48, 'k2-s-kb-ink', 0]]),
      magnet: paint('magnet', 'radialGradient', { cx: 0.38, cy: 0.34, r: 0.72 }, [[0, 'k2-s-kb-magnet-hi'], [1, 'k2-s-kb-magnet-lo']]),
      floor: paint('floor', 'linearGradient', { x1: 0, y1: 0, x2: 0, y2: 1 }, [[0, 'k2-s-kb-alu-lo'], [1, 'k2-s-kb-alu-mid']]),
      body: paint('body', 'linearGradient', { x1: 0, y1: 0, x2: 0, y2: 1 }, [[0, 'k2-s-kb-board-hi'], [0.55, 'k2-s-kb-board-lo'], [1, 'k2-s-kb-alu-mid']])
    };

    /* ---- the board on the wall: its shadow, the frame, the white surface with its sheen */
    var bg = el('g', {}, f.L.bg);
    [[16, 0.16], [9, 0.16], [3, 0.2]].forEach(function (s) {
      el('rect', { x: X0 - s[0] + 4, y: Y0 - s[0] + 10, width: W + 2 * s[0], height: H + 2 * s[0], rx: 12 + s[0], 'class': 'k2-kb-wall', opacity: s[1] }, bg);
    });
    f.shadow(X0 + W / 2, Y0 + H + 30, W * 0.42, 7);
    var bk = el('g', {}, f.L.back);
    el('rect', { x: X0 - 1, y: Y0 - 1, width: W + 2, height: H + 2, rx: 9, 'class': 'k2-outline' }, bk);
    el('path', { d: poly([[X0, Y0], [X0 + W, Y0], [X0 + W - fr, sy], [sx, sy]], true), fill: P.aluV }, bk);
    el('path', { d: poly([[X0, Y0 + H], [X0 + W, Y0 + H], [X0 + W - fr, sy + sh], [sx, sy + sh]], true), fill: P.aluV }, bk);
    el('path', { d: poly([[X0, Y0], [sx, sy], [sx, sy + sh], [X0, Y0 + H]], true), fill: P.aluH }, bk);
    el('path', { d: poly([[X0 + W, Y0], [X0 + W - fr, sy], [X0 + W - fr, sy + sh], [X0 + W, Y0 + H]], true), fill: P.aluH }, bk);
    el('rect', { x: X0 + 1.5, y: Y0 + 1.5, width: W - 3, height: H - 3, rx: 8, 'class': 'k2-kb-shine' }, bk);
    el('rect', { x: sx, y: sy, width: sw, height: sh, fill: P.board }, bk);
    var cid = gid + '-clip';
    el('rect', { x: sx, y: sy, width: sw, height: sh }, el('clipPath', { id: cid }, f.defs));
    var gl = el('g', { 'clip-path': 'url(#' + cid + ')' }, bk);
    el('path', { d: poly([[sx + sw * 0.16, sy], [sx + sw * 0.31, sy], [sx + sw * 0.13, sy + sh], [sx - sw * 0.02, sy + sh]], true), fill: P.sheen, opacity: 0.55 }, gl);
    el('path', { d: poly([[sx + sw * 0.35, sy], [sx + sw * 0.38, sy], [sx + sw * 0.2, sy + sh], [sx + sw * 0.17, sy + sh]], true), fill: P.sheen, opacity: 0.7 }, gl);
    el('path', { d: poly([[sx + sw * 0.78, sy], [sx + sw * 0.86, sy], [sx + sw * 0.68, sy + sh], [sx + sw * 0.6, sy + sh]], true), fill: P.sheen, opacity: 0.35 }, gl);
    /* the faint ghost of old marker that never quite wipes off */
    el('path', { d: 'M' + (sx + sw * 0.6) + ' ' + (sy + sh - 34) + ' q 30 -14 62 -4 t 70 -6', 'class': 'k2-kb-ghost' }, gl);
    el('path', { d: 'M' + (sx + sw * 0.05) + ' ' + (sy + sh - 22) + ' q 22 -10 48 -2', 'class': 'k2-kb-ghost' }, gl);
    el('rect', { x: sx, y: sy, width: sw, height: 9, fill: P.lip }, gl);
    el('rect', { x: sx, y: sy, width: sw, height: sh, 'class': 'k2-kb-inner' }, bk);
    [[X0, Y0], [X0 + W, Y0], [X0, Y0 + H], [X0 + W, Y0 + H]].forEach(function (c) {
      var x = c[0] - (c[0] > X0 ? 26 : 0), y = c[1] - (c[1] > Y0 ? 26 : 0);
      el('rect', { x: x - 1, y: y - 1, width: 28, height: 28, rx: 9, 'class': 'k2-outline' }, bk);
      el('rect', { x: x, y: y, width: 26, height: 26, rx: 8, fill: P.corner }, bk);
      el('circle', { cx: x + 13, cy: y + 13, r: 3.2, 'class': 'k2-kb-screw' }, bk);
    });

    /* ---- masking tape: the columns' dividers and the line under the headers, torn at the ends */
    function tape(x1, y1, x2, y2, wd, fill) {
      var vert = Math.abs(x2 - x1) < Math.abs(y2 - y1), J = [0, 1.6, 0.4, 2.2, 0.8, 1.8, 0.2, 2.4], n = 7, ps = [], j;
      for (j = 0; j <= n; j++) { var u = j / n, e = J[j % J.length]; ps.push(vert ? [x1 - wd / 2 + wd * u, y1 + e] : [x1 + e, y1 - wd / 2 + wd * u]); }
      for (j = 0; j <= n; j++) { var u2 = 1 - j / n, e2 = J[(j + 3) % J.length]; ps.push(vert ? [x2 - wd / 2 + wd * u2, y2 - e2] : [x2 - e2, y2 - wd / 2 + wd * u2]); }
      var g = el('g', {}, bk);
      el('path', { d: poly(ps, true), fill: fill, opacity: 0.93 }, g);
      el('path', { d: vert ? 'M' + (x1 - wd / 2 + 0.5) + ' ' + y1 + ' L' + (x2 - wd / 2 + 0.5) + ' ' + y2 + ' M' + (x1 + wd / 2 - 0.5) + ' ' + y1 + ' L' + (x2 + wd / 2 - 0.5) + ' ' + y2
        : 'M' + x1 + ' ' + (y1 - wd / 2 + 0.5) + ' L' + x2 + ' ' + (y2 - wd / 2 + 0.5) + ' M' + x1 + ' ' + (y1 + wd / 2 - 0.5) + ' L' + x2 + ' ' + (y2 + wd / 2 - 0.5), 'class': 'k2-kb-tape-edge' }, g);
    }
    for (i = 1; i < nc; i++) { tape(sx + i * cw + 1.5, sy + 8, sx + i * cw - 1.5, sy + sh - 8, 14, P.tapeV); }
    tape(sx + 10, ty + 1, sx + sw - 10, ty - 1, 10, P.tapeH);

    /* ---- the headers in marker, each with its WIP badge, and a wash over a column that is over its limit */
    var heads = Cols.map(function (c, k) {
      var x0 = sx + k * cw, hd = { c: c, x0: x0, over: false, wash: 0, pop: new Spring(1) };
      hd.washR = el('rect', { x: x0 + 9, y: ty + 9, width: cw - 18, height: sy + sh - ty - 16, rx: 10, 'class': 'k2-kb-wash', opacity: 0 }, f.L.back);
      hd.name = el('text', { x: x0 + 18, y: hy, 'dominant-baseline': 'central', 'class': 'k2-t-kb-head' }, f.L.contents, c.name || '');
      hd.ul = el('path', { 'class': 'k2-kb-ul' }, f.L.contents);
      if (c.wip != null) {
        hd.bg = el('g', {}, f.L.contents);
        hd.br = el('rect', { rx: 7, 'class': 'k2-kb-badge' }, hd.bg);
        hd.bt = el('text', { 'dominant-baseline': 'central', 'text-anchor': 'middle', 'class': 'k2-t-kb-badge' }, hd.bg, 'WIP ' + c.wip);
        holds(hd.bg, hd.br);
      }
      hd.box = []; hd.at = [x0 + cw - 50, hy];
      return hd;
    });
    (f.fits = f.fits || []).push(function () {
      heads.forEach(function (hd) {
        var x1 = hd.x0 + 18, x2 = x1 + hd.name.getBBox().width, tb = hd.bg ? hd.bt.getBBox() : null;
        var bw = tb ? tb.width + 20 : 0, bh = tb ? Math.max(26, tb.height + 6) : 0, bx = hd.x0 + cw - 14 - bw, two = !!tb && x2 + 12 > bx;
        hd.name.setAttribute('y', two ? hy - 4 : (sy + ty - 4) / 2);
        var nb = hd.name.getBBox(), uy = nb.y + nb.height + 3;
        hd.ul.setAttribute('d', 'M' + (x1 - 2) + ' ' + (uy + 1).toFixed(1) + ' C' + (x1 + (x2 - x1) * 0.3).toFixed(1) + ' ' + (uy - 2).toFixed(1) + ' ' +
          (x1 + (x2 - x1) * 0.7).toFixed(1) + ' ' + (uy + 3).toFixed(1) + ' ' + (x2 + 4).toFixed(1) + ' ' + (uy - 1).toFixed(1));
        hd.box = [{ x: nb.x - 4, y: nb.y - 4, x2: x2 + 6, y2: uy + 6 }];
        if (!tb) { return; }
        var by = two ? Math.min(uy + 8 + bh / 2, ty - 7 - bh / 2) : (sy + ty - 4) / 2;
        if (two) { bx = x1; }
        hd.br.setAttribute('x', bx.toFixed(1)); hd.br.setAttribute('y', (by - bh / 2).toFixed(1));
        hd.br.setAttribute('width', bw.toFixed(1)); hd.br.setAttribute('height', bh.toFixed(1));
        hd.bt.setAttribute('x', (bx + bw / 2).toFixed(1)); hd.bt.setAttribute('y', by.toFixed(1));
        hd.at = [bx + bw / 2, by];
        hd.box.push({ x: bx - 4, y: by - bh / 2 - 4, x2: bx + bw + 4, y2: by + bh / 2 + 4 });
      });
    });
    f.solid(function () { var out = []; heads.forEach(function (hd) { out = out.concat(hd.box); }); return out; });

    /* ---- the marker tray under the board: two markers and an eraser lying in it */
    var tr = el('g', {}, f.L.back), tyy = Y0 + H, tx0 = X0 + 70, tx1 = X0 + W - 70;
    var lip = function (y0, y1, x0, x1) { var r = (y1 - y0) / 2; return 'M' + x0 + ' ' + y0 + ' H' + x1 + ' A' + r + ' ' + r + ' 0 0 1 ' + x1 + ' ' + y1 + ' H' + x0 + ' A' + r + ' ' + r + ' 0 0 1 ' + x0 + ' ' + y0 + ' Z'; };
    el('rect', { x: tx0 - 2, y: tyy - 4, width: tx1 - tx0 + 4, height: 18, rx: 4, 'class': 'k2-outline' }, tr);
    el('rect', { x: tx0, y: tyy - 3, width: tx1 - tx0, height: 16, rx: 3, fill: P.floor }, tr);
    function marker(x, len, cap, rot) {
      var g = el('g', { transform: 'rotate(' + rot + ' ' + (x + len / 2) + ' ' + (tyy + 5) + ')' }, tr), y = tyy - 2;
      el('rect', { x: x - 5, y: y + 2, width: 8, height: 10, rx: 3, 'class': 'k2-kb-plug' }, g);
      el('rect', { x: x - 1, y: y - 1, width: len + 2, height: 16, rx: 7, 'class': 'k2-outline' }, g);
      el('rect', { x: x, y: y, width: len - 32, height: 14, rx: 6, fill: P.body }, g);
      el('rect', { x: x + 16, y: y, width: 30, height: 14, 'class': 'k2-kb-cap-' + cap, opacity: 0.85 }, g);
      el('rect', { x: x + len - 36, y: y - 0.5, width: 36, height: 15, rx: 6, 'class': 'k2-kb-cap-' + cap }, g);
      el('rect', { x: x + len - 34, y: y - 0.5, width: 3, height: 15, 'class': 'k2-kb-ring' }, g);
      el('rect', { x: x + len - 28, y: y - 3, width: 22, height: 4, rx: 2, 'class': 'k2-kb-cap-' + cap }, g);
      el('rect', { x: x + 4, y: y + 2.5, width: len - 40, height: 2.6, rx: 1.3, 'class': 'k2-kb-glint' }, g);
      el('rect', { x: x + len - 30, y: y + 2, width: 26, height: 2.4, rx: 1.2, 'class': 'k2-kb-glint' }, g);
    }
    marker(tx1 - 340, 128, 'blue', -1.2);
    marker(tx1 - 196, 122, 'red', 0.8);
    var er = el('g', {}, tr), ex = tx0 + 60;
    el('path', { d: 'M' + (ex - 1) + ' ' + (tyy + 12) + ' V' + (tyy - 6) + ' Q' + (ex - 1) + ' ' + (tyy - 14) + ' ' + (ex + 10) + ' ' + (tyy - 14) + ' H' + (ex + 102) + ' Q' + (ex + 113) + ' ' + (tyy - 14) + ' ' + (ex + 113) + ' ' + (tyy - 6) + ' V' + (tyy + 12) + ' Z', 'class': 'k2-outline' }, er);
    el('path', { d: 'M' + ex + ' ' + (tyy + 3) + ' V' + (tyy - 6) + ' Q' + ex + ' ' + (tyy - 13) + ' ' + (ex + 10) + ' ' + (tyy - 13) + ' H' + (ex + 102) + ' Q' + (ex + 112) + ' ' + (tyy - 13) + ' ' + (ex + 112) + ' ' + (tyy - 6) + ' V' + (tyy + 3) + ' Z', 'class': 'k2-kb-handle' }, er);
    el('rect', { x: ex + 10, y: tyy - 10, width: 66, height: 3, rx: 1.5, 'class': 'k2-kb-glint' }, er);
    el('rect', { x: ex + 1, y: tyy + 3, width: 110, height: 9, 'class': 'k2-kb-felt' }, er);
    el('path', { d: lip(tyy + 8, tyy + 25, tx0, tx1), 'class': 'k2-outline-s', 'stroke-width': 2.5 }, tr);
    el('path', { d: lip(tyy + 8, tyy + 25, tx0, tx1), fill: P.aluV }, tr);
    el('path', { d: 'M' + (tx0 + 2) + ' ' + (tyy + 10) + ' H' + (tx1 - 2), 'class': 'k2-kb-shine' }, tr);
    [tx0 - 12, tx1 - 6].forEach(function (x) {
      el('rect', { x: x - 1, y: tyy + 3, width: 20, height: 25, rx: 6, 'class': 'k2-outline' }, tr);
      el('rect', { x: x, y: tyy + 4, width: 18, height: 23, rx: 5, fill: P.corner }, tr);
    });

    /* ---- the cards: a sticky note with a lifted corner, its words, a tag, who owns it, a magnet when blocked */
    var L = -w / 2, T = -h / 2, R = w / 2, B = h / 2;
    var note = 'M' + L + ' ' + (T + 2) + ' Q' + L + ' ' + T + ' ' + (L + 2) + ' ' + T + ' H' + (R - 2) + ' Q' + R + ' ' + T + ' ' + R + ' ' + (T + 2) +
      ' V' + (B - 8) + ' Q' + (R - 10) + ' ' + (B - 0.5) + ' ' + (R - 60) + ' ' + B + ' H' + (L + 2) + ' Q' + L + ' ' + B + ' ' + L + ' ' + (B - 2) + ' Z';
    var gcards = el('g', {}, f.L.hero), byId = {};
    var cards = (p.cards || []).map(function (k, idx) {
      var hsh = 0, j, id = String(k.id || idx);
      for (j = 0; j < id.length; j++) { hsh = (hsh * 31 + id.charCodeAt(j)) % 1000; }
      var g = el('g', {}, gcards), sg = el('g', {}, g), inner = el('g', {}, g);
      var soft = el('rect', { x: L - 16, y: T - 12, width: w + 32, height: h + 34, fill: f.url('shadow') }, sg);
      var contact = el('path', { d: note, 'class': 'k2-kb-contact', transform: 'translate(1.2 2.6)' }, sg);
      el('ellipse', { cx: R - 24, cy: B + 3, rx: 34, ry: 6, fill: f.url('shadow'), transform: 'rotate(-5 ' + (R - 24) + ' ' + (B + 3) + ')' }, sg);
      var body = el('path', { d: note, 'class': 'k2-kb-note-' + (k.cat || 1) }, inner);
      el('path', { d: note, fill: P.paper }, inner);
      el('path', { d: 'M' + R + ' ' + (B - 36) + ' V' + (B - 8) + ' Q' + (R - 10) + ' ' + (B - 0.5) + ' ' + (R - 60) + ' ' + B + ' H' + (R - 90) + ' Z', fill: P.curl }, inner);
      el('path', { d: 'M' + (R - 1.4) + ' ' + (B - 10) + ' Q' + (R - 11) + ' ' + (B - 2.6) + ' ' + (R - 56) + ' ' + (B - 1.6), 'class': 'k2-kb-fold' }, inner);
      el('path', { d: 'M' + (L + 3) + ' ' + (T + 1.2) + ' H' + (R - 3), 'class': 'k2-kb-fold' }, inner);
      var txt = el('text', { 'text-anchor': 'start', 'class': 'k2-t-kb-card' }, inner), tag = null;
      if (k.tag) {
        tag = { g: el('g', {}, inner) };
        tag.r = el('rect', { rx: 6, 'class': /bug/i.test(k.tag) ? 'k2-kb-tag-bug' : 'k2-kb-tag-feat' }, tag.g);
        tag.t = el('text', { 'dominant-baseline': 'central', 'class': 'k2-t-kb-tag' }, tag.g, k.tag);
      }
      var av = k.who ? { ol: el('circle', { 'class': 'k2-outline' }, inner), disc: el('circle', { 'class': 'k2-kb-av' }, inner),
        hi: el('ellipse', { 'class': 'k2-kb-av-hi' }, inner),
        t: el('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'class': 'k2-t-kb-av' }, inner, k.who) } : null;
      var mg = null;
      if (k.blocked != null) {
        mg = el('g', {}, g);
        el('circle', { cx: R - 18, cy: T + 22, r: 16, fill: f.url('shadow') }, mg);
        el('circle', { cx: R - 20, cy: T + 19, r: 15, 'class': 'k2-outline' }, mg);
        el('circle', { cx: R - 20, cy: T + 19, r: 14, fill: P.magnet }, mg);
        el('rect', { x: R - 28, y: T + 16.4, width: 16, height: 5.2, rx: 2, 'class': 'k2-kb-bar' }, mg);
        el('ellipse', { cx: R - 24, cy: T + 12.5, rx: 6, ry: 3, 'class': 'k2-kb-mag-hi' }, mg);
      }
      holds(inner, body);
      var c0 = clamp(Math.round(tv(k.col, 0)), 0, nc - 1);
      var o = { k: k, i: idx, g: g, soft: soft, contact: contact, txt: txt, tag: tag, av: av, mg: mg, rot: (hsh / 1000 - 0.5) * 2.4,
        c: c0, last: c0, ord: tv(k.order, idx), x: 0, y: 0, vx: 0, vy: 0, lift: new Spring(0), trip: null, pin: new Spring(tv(k.blocked, 0)) };
      byId[id] = o;
      f.solid(function () { return { x: o.x - w / 2 - 6, y: o.y - h / 2 - 8, x2: o.x + w / 2 + 6, y2: o.y + h / 2 + 8 }; });
      return o;
    });
    f.fits.push(function () {
      cards.forEach(function (o) {
        wrapText(o.txt, o.k.text, L + 14, T + 29, w - 62);
        if (o.av) {                                   /* the initials' circle grows with the type */
          var r = Math.max(16, o.av.t.getBBox().width / 2 + 6), ax = R - 9 - r, ay = Math.min(B - 23, B - 7 - r);
          o.av.ol.setAttribute('cx', ax); o.av.ol.setAttribute('cy', ay); o.av.ol.setAttribute('r', (r + 1.5).toFixed(1));
          o.av.disc.setAttribute('cx', ax); o.av.disc.setAttribute('cy', ay); o.av.disc.setAttribute('r', r.toFixed(1));
          o.av.hi.setAttribute('cx', (ax - r * 0.32).toFixed(1)); o.av.hi.setAttribute('cy', (ay - r * 0.45).toFixed(1));
          o.av.hi.setAttribute('rx', (r * 0.5).toFixed(1)); o.av.hi.setAttribute('ry', (r * 0.3).toFixed(1));
          o.av.t.setAttribute('x', ax); o.av.t.setAttribute('y', ay);
        }
        if (o.tag) {
          var tb = o.tag.t.getBBox(), tw = tb.width + 18, th = Math.max(24, tb.height + 4);
          o.tag.r.setAttribute('x', L + 12); o.tag.r.setAttribute('y', (B - 23 - th / 2).toFixed(1));
          o.tag.r.setAttribute('width', tw.toFixed(1)); o.tag.r.setAttribute('height', th.toFixed(1));
          o.tag.t.setAttribute('x', L + 21); o.tag.t.setAttribute('y', B - 23);
        }
      });
    });
    function inCol(k) { var out = []; cards.forEach(function (o) { if (o.c === k) { out.push(o); } }); return out; }
    function slots() {
      var S = {}, k;
      for (k = 0; k < nc; k++) {
        inCol(k).sort(function (a, b) { return (a.ord - b.ord) || (a.i - b.i); })
          .forEach(function (o, j) { S[o.i] = [sx + (k + 0.5) * cw, top + h / 2 + j * pitch]; });
      }
      return S;
    }

    /* ---- words for a card or a column, in red marker on the board; each comes in once the cards have landed */
    var labs = (p.labels || []).map(function (lb) {
      var o = { lb: lb, op: 0 };
      o.L = f.label({ text: lb.text, sub: lb.sub, cls: 'k2-t-kb-call', side: lb.side, dist: lb.dist, lead: lb.col != null ? false : lb.lead,
        r: lb.edge === 'pin' ? 16 : 0, show: function () { return o.op; },
        at: function () {
          var c = lb.card != null ? byId[lb.card] : null, e = lb.edge || 'right';
          if (c) { return e === 'left' ? [c.x - w / 2, c.y] : e === 'bottom' ? [c.x, c.y + h / 2] : e === 'pin' ? [c.x + w / 2 - 20, c.y - h / 2 + 19] : [c.x + w / 2, c.y]; }
          var n = inCol(lb.col || 0).length;
          return [sx + ((lb.col || 0) + 0.5) * cw, n ? top + (n - 1) * pitch + h + 4 : top];
        } });
      o.L.g.classList.add('k2-kb-lbl'); setOp(o.L.g, 0); o.L.g.style.display = 'none';
      return o;
    });

    var moving = false, busy = false;
    return {
      draw: function (dt, snap) {
        var was = moving, relay = false;
        moving = false; busy = false;
        cards.forEach(function (o) { o.c = clamp(Math.round(tv(o.k.col, 0)), 0, nc - 1); o.ord = tv(o.k.order, o.i); });
        var S = slots();
        cards.forEach(function (o) {
          var q = S[o.i], aim;
          if (o.c !== o.last) {
            if (!snap) { o.trip = { D: Math.max(1, Math.hypot(q[0] - o.x, q[1] - o.y)), x: o.x, y: o.y, go: false }; gcards.appendChild(o.g); }
            o.last = o.c;
          }
          /* a card is lifted off the board before it moves */
          if (o.trip && !o.trip.go && o.lift.x > 0.55) { o.trip.go = true; }
          aim = o.trip && !o.trip.go ? [o.trip.x, o.trip.y] : q;
          if (snap) { o.x = q[0]; o.y = q[1]; o.vx = o.vy = 0; o.trip = null; o.lift.x = 0; o.lift.v = 0; }
          else {
            o.vx += (64 * (aim[0] - o.x) - 11 * o.vx) * dt; o.x += o.vx * dt;
            o.vy += (64 * (aim[1] - o.y) - 11 * o.vy) * dt; o.y += o.vy * dt;
            if (Math.abs(aim[0] - o.x) + Math.abs(aim[1] - o.y) < 0.05 && Math.abs(o.vx) + Math.abs(o.vy) < 0.1) { o.x = aim[0]; o.y = aim[1]; o.vx = o.vy = 0; }
          }
          var dist = Math.hypot(q[0] - o.x, q[1] - o.y), up = o.lift.go(o.trip && dist > 14 ? 1 : 0, dt, snap);
          if (o.trip && dist < 0.5 && !up) { o.trip = null; if (o.c === nc - 1) { f.pulse(o.x, o.y, { tone: 'good', r: 96 }); } }
          var lf = clamp(o.lift.x, -0.2, 1.2), lp = clamp(lf, 0, 1), u = o.trip ? clamp(1 - dist / o.trip.D, 0, 1) : 1;
          var arc = o.trip ? -Math.min(46, o.trip.D * 0.2) * Math.sin(Math.PI * u) : 0, rot = o.rot * (1 - lp) + clamp(o.vx * 0.006, -5, 5) * lp;
          o.g.setAttribute('transform', 'translate(' + o.x.toFixed(1) + ' ' + (o.y + arc).toFixed(1) + ') rotate(' + rot.toFixed(2) + ') scale(' + (1 + 0.07 * lf).toFixed(3) + ')');
          o.soft.setAttribute('transform', 'translate(' + (3 + 14 * lp).toFixed(1) + ' ' + (5 + 24 * lp).toFixed(1) + ') scale(' + (1 + 0.08 * lp).toFixed(3) + ')');
          setOp(o.soft, 0.75 - 0.3 * lp); setOp(o.contact, 0.3 * (1 - lp));
          if (o.trip || o.vx || o.vy || up) { moving = true; }
          if (o.mg) {
            var pv = clamp(tv(o.k.blocked, 0), 0, 1), pu = o.pin.go(pv, dt, snap), ps = Math.max(0, o.pin.x), mx = R - 20, my = T + 19;
            o.mg.setAttribute('transform', 'translate(' + mx + ' ' + my + ') scale(' + (0.4 + 0.6 * ps).toFixed(3) + ') translate(' + (-mx) + ' ' + (-my) + ')');
            setOp(o.mg, clamp(ps * 1.5, 0, 1)); o.mg.style.display = ps < 0.01 && !pv ? 'none' : '';
            if (pu) { busy = true; }
          }
        });
        /* what each column holds once its cards have landed: the badge, the wash, the readouts */
        var n = [], over = 0, k;
        for (k = 0; k < nc; k++) { n.push(0); }
        cards.forEach(function (o) { if (!o.trip) { n[o.c] += 1; } });
        heads.forEach(function (hd, k2) {
          var on = hd.c.wip != null && n[k2] > hd.c.wip;
          if (on) { over += 1; }
          if (on !== hd.over) {
            hd.over = on;
            if (hd.bg) {
              hd.br.setAttribute('class', on ? 'k2-kb-badge k2-kb-badge-alarm' : 'k2-kb-badge');
              hd.bt.setAttribute('class', on ? 'k2-t-kb-badge k2-t-kb-alarm' : 'k2-t-kb-badge');
              if (on && !snap) { f.pulse(hd.at[0], hd.at[1], { tone: 'amber', r: 44 }); hd.pop.x = 1.35; }
            }
          }
          hd.wash = snap ? (on ? 1 : 0) : approach(hd.wash, on ? 1 : 0, dt, 6);
          if (Math.abs(hd.wash - (on ? 1 : 0)) > 0.003) { busy = true; } else { hd.wash = on ? 1 : 0; }
          setOp(hd.washR, 0.1 * hd.wash);
          if (hd.bg) {
            if (hd.pop.go(1, dt, snap)) { busy = true; }
            hd.bg.setAttribute('transform', 'translate(' + hd.at[0].toFixed(1) + ' ' + hd.at[1].toFixed(1) + ') scale(' + hd.pop.x.toFixed(3) + ') translate(' + (-hd.at[0]).toFixed(1) + ' ' + (-hd.at[1]).toFixed(1) + ')');
          }
          f.publish(p.id, 'n' + k2, n[k2]);
        });
        f.publish(p.id, 'done', n[nc - 1]); f.publish(p.id, 'over', over);
        labs.forEach(function (o) {
          var want = tv(o.lb.show, 0) > 0.5 && !moving ? 1 : 0;
          if (want && o.L.g.style.display === 'none') { o.L.g.style.display = ''; relay = true; }
          o.op = snap ? want : approach(o.op, want, dt, 8);
          if (Math.abs(o.op - want) < 0.004) { o.op = want; } else { busy = true; }
          if (!want && !o.op) { o.L.g.style.display = 'none'; }
        });
        if (!snap && (relay || (was && !moving))) { f.layout(); }
      },
      live: function () { return moving || busy; }
    };
  });

  /* motherboard - a PC main board seen from above: the CPU in its socket with the VRM beside it, RAM in its slots, the
     graphics card, an M.2 SSD, the chipset, the rear ports, power and SATA plugs; its buses are bundles of copper traces
     that light up and carry bursts of data, and a monitor can stand beside it. Drawn 740 x 592 board units, then placed.
     {x, y, w (the board's width), ram (sticks: 2 or 4), focus: "@focus" (0 none, 1 CPU and VRM, 2 RAM, 3 graphics card,
      4 SSD, 5 chipset, 6 CPU and RAM), power: "@pwr" (the VRM's chokes glow), buses: [{pts (board units), lanes, gap, lit: "@p" (0..1),
      send: "@x" (each whole step up sends one burst), both (bursts go back and forth), back, tone: "amber", fans (the
      card's fans run while it carries data), cable, label, sub, at, side, show}], tags: [{on: cpu | ram | gpu | ssd |
      chipset | vrm | io | power | sata | display | port, text, sub, show, side, dist, fixed, at}], display: {x, y, w,
      show: "@screen"} - a monitor beside the board, in board units} */
  define('motherboard', function (f, p) {
    var X0 = p.x || 0, Y0 = p.y || 0, s = (p.w || 740) / 740, i, k, q, seed = 11;
    var tf = 'translate(' + X0 + ' ' + Y0 + ') scale(' + s.toFixed(4) + ')';
    var gB = el('g', { transform: tf }, f.L.back), gC = el('g', { transform: tf }, f.L.contents);
    var gH = el('g', { transform: tf }, f.L.hero), gF = el('g', { transform: tf }, f.L.front);
    function A(x, y) { return [X0 + x * s, Y0 + y * s]; }
    function box(r) { return { x: X0 + r[0] * s, y: Y0 + r[1] * s, x2: X0 + r[2] * s, y2: Y0 + r[3] * s }; }
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    function paint(a, fill) { if (/^url/.test(fill)) { a.fill = fill; } else { a['class'] = fill; } return a; }
    function rect(g, x, y, w, h, fill, rx) { return el('rect', paint({ x: x, y: y, width: w, height: h, rx: rx || null }, fill), g); }
    function disc(g, x, y, r, fill) { return el('circle', paint({ cx: x, cy: y, r: r }, fill), g); }
    function ln(g, x1, y1, x2, y2, cls) { return el('line', { x1: x1, y1: y1, x2: x2, y2: y2, 'class': cls }, g); }
    function path(g, dd, fill) { return el('path', paint({ d: dd }, fill), g); }
    /* a solid piece: its outline, its body, a lit edge */
    function piece(g, x, y, w, h, fill, rx, edge) {
      rect(g, x - 1.2, y - 1.2, w + 2.4, h + 2.4, 'k2-outline', rx ? rx + 1 : null);
      var b = rect(g, x, y, w, h, fill, rx);
      if (edge !== false) { el('rect', { x: x + 0.6, y: y + 0.6, width: w - 1.2, height: h - 1.2, rx: rx || null, 'class': 'k2-mb-edge' }, g); }
      return b;
    }
    function grad(list, a, radial) { var id = f.id + '-mb' + (++UID); a.id = id; stops(el(radial ? 'radialGradient' : 'linearGradient', a, f.defs), list); return 'url(#' + id + ')'; }
    var G = {
      pcb: grad([[0, 'k2-s-pcb-hi'], [1, 'k2-s-pcb-lo']], { x1: 0, y1: 0, x2: 0.7, y2: 1 }),
      sheen: grad([[0, 'k2-s-hi', 0], [0.4, 'k2-s-hi', 0.05], [0.5, 'k2-s-hi', 0], [1, 'k2-s-hi', 0]], { x1: 0, y1: 0, x2: 1, y2: 1 }),
      plastic: grad([[0, 'k2-s-plastic-hi'], [1, 'k2-s-plastic-lo']], { x1: 0, y1: 0, x2: 0.3, y2: 1 }),
      plastic2: grad([[0, 'k2-s-plastic2-hi'], [1, 'k2-s-plastic2-lo']], { x1: 0, y1: 0, x2: 0.3, y2: 1 }),
      chip: grad([[0, 'k2-s-chip-hi'], [1, 'k2-s-chip-lo']], { x1: 0, y1: 0, x2: 1, y2: 1 }),
      gold: grad([[0, 'k2-s-gold-hi'], [1, 'k2-s-gold-lo']], { x1: 0, y1: 0, x2: 1, y2: 1 }),
      copper: grad([[0, 'k2-s-copper-hi'], [1, 'k2-s-copper-lo']], { x1: 0, y1: 0, x2: 0.4, y2: 1 }),
      sub: grad([[0, 'k2-s-sub-hi'], [1, 'k2-s-sub-lo']], { x1: 0, y1: 0, x2: 1, y2: 1 }),
      ihs: grad([[0, 'k2-s-metal-mid'], [0.3, 'k2-s-metal-hi'], [0.42, 'k2-s-hi', 0.9], [0.52, 'k2-s-metal-hi'], [0.8, 'k2-s-metal-mid'], [1, 'k2-s-metal-lo']], { x1: 0, y1: 0, x2: 1, y2: 1 }),
      sink: grad([[0, 'k2-s-metal-hi'], [0.45, 'k2-s-metal-mid'], [1, 'k2-s-metal-lo']], { x1: 0, y1: 0, x2: 0.5, y2: 1 }),
      shroud: grad([[0, 'k2-s-shroud-hi'], [1, 'k2-s-shroud-lo']], { x1: 0, y1: 0, x2: 0.25, y2: 1 }),
      blade: grad([[0, 'k2-s-fan-hi'], [1, 'k2-s-fan-lo']], { x1: 0, y1: 0, x2: 1, y2: 1 }),
      hub: grad([[0, 'k2-s-metal-hi'], [0.6, 'k2-s-metal-mid'], [1, 'k2-s-metal-lo']], { cx: 0.35, cy: 0.3, r: 0.8 }, true),
      blur: grad([[0, 'k2-s-fan-hi', 0], [0.27, 'k2-s-fan-hi', 0], [0.34, 'k2-s-fan-hi', 0.55], [0.85, 'k2-s-fan-hi', 0.35], [1, 'k2-s-fan-hi', 0.1]], {}, true),
      bezel: grad([[0, 'k2-s-plastic-hi'], [1, 'k2-s-chip-lo']], { x1: 0, y1: 0, x2: 0.2, y2: 1 }),
      sky: grad([[0, 'k2-s-sky-hi'], [1, 'k2-s-sky-lo']], { x1: 0, y1: 0, x2: 0, y2: 1 }),
      ground: grad([[0, 'k2-s-ground-hi'], [1, 'k2-s-ground-lo']], { x1: 0, y1: 0, x2: 0, y2: 1 }),
      sun: grad([[0, 'k2-s-sun', 1], [0.22, 'k2-s-sun', 0.9], [1, 'k2-s-sun', 0]], {}, true)
    };
    /* a line moved sideways by dd (mitred at its bends): one lane of a bundle */
    function offset(ps, dd) {
      return ps.map(function (c, j) {
        var a = ps[Math.max(0, j - 1)], b = ps[Math.min(ps.length - 1, j + 1)], n1, n2;
        function nrm(u, v) { var l = Math.hypot(v[0] - u[0], v[1] - u[1]) || 1; return [-(v[1] - u[1]) / l, (v[0] - u[0]) / l]; }
        n1 = j > 0 ? nrm(a, c) : nrm(c, b); n2 = j < ps.length - 1 ? nrm(c, b) : n1;
        var m = [n1[0] + n2[0], n1[1] + n2[1]], ml = Math.hypot(m[0], m[1]) || 1, cs = (m[0] * n1[0] + m[1] * n1[1]) / ml || 1;
        return [c[0] + m[0] / ml * dd / cs, c[1] + m[1] / ml * dd / cs];
      });
    }
    function track(ps) {
      var segs = [], L = 0;
      for (var j = 1; j < ps.length; j++) { var l = Math.hypot(ps[j][0] - ps[j - 1][0], ps[j][1] - ps[j - 1][1]); segs.push([ps[j - 1], ps[j], L, l]); L += l; }
      return { ps: ps, len: L, at: function (d) {
        d = clamp(d, 0, L);
        for (var j = 0; j < segs.length; j++) { var g = segs[j]; if (d <= g[2] + g[3] || j === segs.length - 1) { var u = (d - g[2]) / (g[3] || 1); return [lerp(g[0][0], g[1][0], u), lerp(g[0][1], g[1][1], u)]; } }
        return ps[0];
      } };
    }
    function bundle(ps, n, gap, cls, g) { for (var j = 0; j < n; j++) { el('path', { d: poly(offset(ps, (j - (n - 1) / 2) * gap)), 'class': cls }, g); } }

    /* ---- the board: dark glass-fibre with a soft sheen, copper traces under the lacquer, vias, holes, silkscreen */
    f.shadow(X0 + 386 * s, Y0 + 306 * s, 420 * s, 330 * s);
    var pcb = 'M10 0 H730 Q740 0 740 10 V582 Q740 592 730 592 H10 Q0 592 0 582 V10 Q0 0 10 0 Z';
    el('path', { d: pcb, 'class': 'k2-outline-s', 'stroke-width': 6 }, gB);
    path(gB, pcb, G.pcb); path(gB, pcb, G.sheen);
    [[[[100, 284], [140, 284], [156, 300], [156, 352], [140, 368], [130, 368]], 6, 3.4],
     [[[566, 40], [566, 300], [592, 326], [640, 326], [656, 342], [656, 412]], 7, 3.4],
     [[[618, 78], [618, 96], [636, 114], [636, 250]], 4, 3.4],
     [[[686, 336], [686, 404], [694, 412], [694, 424]], 4, 3.4],
     [[[60, 300], [60, 340], [76, 356]], 4, 3.4],
     [[[606, 500], [606, 520], [618, 532], [690, 532]], 4, 3.4],
     [[[30, 566], [284, 566], [296, 578]], 3, 3.4],
     [[[380, 30], [380, 60], [404, 84], [450, 84], [460, 94], [460, 110]], 5, 3.4],
     [[[380, 290], [380, 296]], 1, 3.4],
     [[[154, 18], [160, 24], [160, 60]], 3, 3.4]].forEach(function (t) { bundle(t[0], t[1], t[2], 'k2-mb-trace', gB); });
    [[386, 250, 70, 46], [212, 278, 150, 18], [580, 60, 90, 60], [580, 260, 80, 40], [30, 354, 30, 18], [610, 506, 80, 12]].forEach(function (v) {
      for (q = 0; q < Math.round(v[2] * v[3] / 160); q++) { disc(gB, v[0] + rnd() * v[2], v[1] + rnd() * v[3], 1.6, 'k2-mb-via'); }
    });
    [[436, 22], [718, 22], [24, 578], [718, 578], [690, 372]].forEach(function (h) {
      disc(gB, h[0], h[1], 12.5, 'k2-mb-silk');
      disc(gB, h[0], h[1], 10, f.url('metal')); disc(gB, h[0], h[1], 5, 'k2-cavity');
      for (q = 0; q < 8; q++) { disc(gB, h[0] + Math.cos(q * Math.PI / 4) * 7.6, h[1] + Math.sin(q * Math.PI / 4) * 7.6, 0.9, 'k2-mb-hole'); }
    });
    /* silkscreen: corner marks round the socket and the slots, a pin-1 arrow, polarity marks */
    [[198, 96, 386, 280], [462, 10, 566, 368], [190, 298, 422, 362]].forEach(function (r) {
      var c = 10;
      path(gB, 'M' + r[0] + ' ' + (r[1] + c) + ' V' + r[1] + ' H' + (r[0] + c) + ' M' + (r[2] - c) + ' ' + r[1] + ' H' + r[2] + ' V' + (r[1] + c) +
        ' M' + r[2] + ' ' + (r[3] - c) + ' V' + r[3] + ' H' + (r[2] - c) + ' M' + (r[0] + c) + ' ' + r[3] + ' H' + r[0] + ' V' + (r[3] - c), 'k2-mb-silk');
    });
    path(gB, 'M206 286 L214 286 L206 294 Z', 'k2-mb-silk-f');

    /* ---- the rear ports through the I/O shield, under their cover */
    var io = el('g', {}, gH);
    rect(io, -14, 14, 5, 290, f.url('metalv'), 1);
    [[22, 22, 'usb'], [48, 22, 'usb'], [76, 22, 'usb'], [102, 22, 'usb'], [130, 14, 'hdmi'], [150, 14, 'hdmi'], [172, 30, 'rj'], [210, 16, 'usb'], [232, 22, 'usb'], [262, 36, 'audio']].forEach(function (o) {
      piece(io, -10, o[0], 30, o[1], o[2] === 'audio' ? G.plastic : G.sink, 2);
      if (o[2] === 'rj') { rect(io, -10, o[0] + 9, 6, 12, 'k2-mb-hole', 1); }
      if (o[2] === 'usb') { ln(io, -9, o[0] + o[1] / 2, 4, o[0] + o[1] / 2, 'k2-mb-seam'); }
      if (o[2] === 'audio') { for (q = 0; q < 3; q++) { disc(io, 0, o[0] + 7 + q * 11, 3.2, 'k2-mb-hole'); } }
    });
    var cover = 'M12 14 H92 L102 24 V238 L78 300 H12 Z';
    el('path', { d: cover, 'class': 'k2-outline-s', 'stroke-width': 3 }, io);
    path(io, cover, G.shroud);
    path(io, 'M84 34 L92 42 V230 L84 248 Z', G.sink);
    for (q = 0; q < 7; q++) { ln(io, 22, 60 + q * 24, 70, 60 + q * 24 - 14, 'k2-mb-groove-s'); }
    path(io, cover, 'k2-mb-edge');
    /* the audio codec and its capacitors, below the cover */
    piece(gH, 22, 316, 30, 30, G.chip, 2);
    for (q = 0; q < 7; q++) { ln(gH, 25 + q * 4, 313, 25 + q * 4, 316, 'k2-mb-pinline'); ln(gH, 25 + q * 4, 346, 25 + q * 4, 349, 'k2-mb-pinline'); }
    [[72, 322], [88, 322], [72, 340]].forEach(function (c) { cap(c[0], c[1], 6.5); });

    /* ---- CPU power: the 8-pin plug, the VRM heatsinks joined by a heat pipe, the chokes, polymer capacitors */
    piece(gH, 108, 4, 44, 26, G.plastic, 3);
    for (q = 0; q < 8; q++) { rect(gH, 111 + (q % 4) * 10, 7 + Math.floor(q / 4) * 11, 8, 8, 'k2-mb-hole', 1.5); rect(gH, 113.5 + (q % 4) * 10, 9.5 + Math.floor(q / 4) * 11, 3, 3, G.gold); }
    rect(gH, 124, 30, 12, 4, G.plastic, 1);
    var vrm = el('g', {}, gH);
    piece(vrm, 168, 12, 232, 46, G.sink, 5);
    for (q = 0; q < 25; q++) { rect(vrm, 176 + q * 9, 18, 4, 34, 'k2-mb-slit', 1.5); }
    piece(vrm, 102, 70, 46, 198, G.sink, 5);
    for (q = 0; q < 21; q++) { rect(vrm, 108, 78 + q * 9, 34, 4, 'k2-mb-slit', 1.5); }
    el('path', { d: 'M125 72 V44 Q125 34 135 34 H170', 'class': 'k2-outline-s', 'stroke-width': 11, 'stroke-linecap': 'round', fill: 'none' }, vrm);
    el('path', { d: 'M125 72 V44 Q125 34 135 34 H170', stroke: G.copper, 'stroke-width': 8, 'stroke-linecap': 'round', fill: 'none' }, vrm);
    el('path', { d: 'M123 70 V44 Q123 32 135 32 H168', 'class': 'k2-mb-edge', 'stroke-width': 1.5 }, vrm);
    var chokes = [];
    for (q = 0; q < 9; q++) { chokes.push([178 + q * 26, 64]); }
    for (q = 0; q < 8; q++) { chokes.push([154, 78 + q * 24]); }
    var hot = el('g', {}, gH);
    chokes.forEach(function (c) {
      piece(gH, c[0], c[1], 20, 20, G.plastic, 2.5);
      rect(gH, c[0] + 5, c[1] + 5, 10, 10, 'k2-mb-mark', 1);
      rect(hot, c[0], c[1], 20, 20, 'k2-mb-hot', 2.5);
    });
    gH.appendChild(hot);
    function cap(x, y, r) {
      disc(gH, x, y, r + 0.9, 'k2-outline'); disc(gH, x, y, r, G.hub);
      path(gH, 'M' + (x - r * 0.78) + ' ' + (y - r * 0.62) + ' A' + r + ' ' + r + ' 0 0 1 ' + (x + r * 0.78) + ' ' + (y - r * 0.62) + ' Z', 'k2-mb-capband');
      ln(gH, x - r * 0.45, y + r * 0.15, x + r * 0.45, y + r * 0.15, 'k2-mb-seam'); ln(gH, x, y - r * 0.3, x, y + r * 0.6, 'k2-mb-seam');
    }
    for (q = 0; q < 9; q++) { cap(222 + q * 17, 94, 5.5); }

    /* ---- the CPU socket: its plastic base, the package and its tiny capacitors, the heat spreader, the load plate and lever */
    piece(gH, 206, 104, 168, 168, G.plastic, 6);
    rect(gH, 226, 124, 128, 128, G.sub, 3);
    for (q = 0; q < 10; q++) {
      rect(gH, 240 + q * 10, 127, 4, 2.4, G.gold); rect(gH, 240 + q * 10, 247, 4, 2.4, G.gold);
      rect(gH, 229, 140 + q * 10, 2.4, 4, G.gold); rect(gH, 349, 140 + q * 10, 2.4, 4, G.gold);
    }
    var ihs = 'M244 134 H336 Q344 134 344 142 V168 Q338 172 338 188 Q338 204 344 208 V234 Q344 242 336 242 H244 Q236 242 236 234 V208 Q242 204 242 188 Q242 172 236 168 V142 Q236 134 244 134 Z';
    el('path', { d: ihs, 'class': 'k2-outline-s', 'stroke-width': 3 }, gH);
    path(gH, ihs, G.ihs);
    el('rect', { x: 252, y: 150, width: 76, height: 76, rx: 6, 'class': 'k2-mb-ihs-line' }, gH);
    path(gH, ihs, 'k2-mb-edge');
    path(gH, 'M242 238 L254 238 L242 226 Z', G.gold);
    var plate = 'M220 112 H360 Q366 112 366 118 V258 Q366 264 360 264 H220 Q214 264 214 258 V118 Q214 112 220 112 Z M232 128 V248 H348 V128 Z';
    el('path', { d: plate, 'fill-rule': 'evenodd', 'class': 'k2-outline' }, gH);
    el('path', { d: 'M221 113 H359 Q365 113 365 119 V257 Q365 263 359 263 H221 Q215 263 215 257 V119 Q215 113 221 113 Z M231 127 V249 H349 V127 Z', 'fill-rule': 'evenodd', fill: G.sink }, gH);
    rect(gH, 270, 106, 40, 7, G.sink, 2); rect(gH, 270, 263, 40, 7, G.sink, 2);
    [[222, 120], [358, 120], [222, 256], [358, 256]].forEach(function (c) { disc(gH, c[0], c[1], 4.2, 'k2-outline'); disc(gH, c[0], c[1], 3.4, G.hub); ln(gH, c[0] - 2, c[1], c[0] + 2, c[1], 'k2-mb-seam'); });
    piece(gH, 195, 116, 6, 152, G.sink, 3);
    piece(gH, 195, 264, 30, 6, G.sink, 3);
    disc(gH, 198, 116, 4.5, G.hub);

    /* ---- the memory: four DIMM slots with their latches, the sticks in them with their chips */
    var nRam = p.ram === 2 ? 2 : 4;
    for (i = 0; i < 4; i++) {
      var dx = 478 + i * 24, has = nRam === 4 || i % 2 === 1;
      piece(gH, dx - 8, 26, 16, 324, i % 2 ? G.plastic2 : G.plastic, 3);
      rect(gH, dx - 2, 32, 4, 312, 'k2-mb-groove', 1.5);
      piece(gH, dx - 9, 14, 18, 14, G.plastic2, 3); piece(gH, dx - 9, 348, 18, 14, G.plastic2, 3);
      if (!has) { continue; }
      piece(gH, dx - 10, 32, 20, 312, G.sub, 2);
      for (k = 0; k < 8; k++) { piece(gH, dx - 7, 40 + k * 38, 14, 28, G.chip, 1.5, false); rect(gH, dx - 5, 43 + k * 38, 3, 3, 'k2-mb-mark', 1.5); }
      rect(gH, dx - 10, 335, 20, 3, G.gold);
    }

    /* ---- power and headers on the right: the 24-pin plug, fan and front-panel headers, the SATA ports */
    piece(gH, 694, 124, 38, 200, G.plastic, 3);
    for (q = 0; q < 24; q++) { var cx0 = 698 + (q % 2) * 16, cy0 = 129 + Math.floor(q / 2) * 16; rect(gH, cx0, cy0, 13, 13, 'k2-mb-hole', 2); rect(gH, cx0 + 4.5, cy0 + 4.5, 4, 4, G.gold); }
    rect(gH, 732, 206, 4, 36, G.plastic, 1);
    function header(x, y, cols, rows) {
      piece(gH, x, y, cols * 7 + 3, rows * 7 + 3, G.plastic, 1.5);
      for (var a = 0; a < cols; a++) { for (var b = 0; b < rows; b++) { rect(gH, x + 3 + a * 7, y + 3 + b * 7, 3.4, 3.4, G.gold); } }
    }
    header(588, 8, 4, 1); header(630, 8, 4, 1); header(600, 376, 10, 2); header(590, 572, 5, 2); header(450, 572, 4, 1);
    /* small parts: resistors and capacitors in rows, a controller chip, the firmware chip */
    function row(x, y, n, dx, dy, vert) {
      for (var j = 0; j < n; j++) { rect(gH, x + j * dx, y + j * dy, vert ? 2.8 : 5.5, vert ? 5.5 : 2.8, j % 3 === 1 ? 'k2-mb-smd2' : 'k2-mb-smd', 0.6); }
    }
    row(384, 250, 6, 0, 8, true); row(580, 110, 8, 8, 0); row(580, 118, 8, 8, 0); row(586, 262, 6, 8, 0); row(612, 502, 9, 8, 0);
    row(214, 278, 4, 8, 0); row(540, 380, 6, 8, 0); row(36, 356, 3, 0, 8, true);
    function chip(x, y, w, h, pins, sides) {
      for (var j = 0; j < pins; j++) {
        var u = (j + 0.5) / pins;
        if (sides > 2) { ln(gH, x + u * w, y - 3, x + u * w, y, 'k2-mb-pinline'); ln(gH, x + u * w, y + h, x + u * w, y + h + 3, 'k2-mb-pinline'); }
        ln(gH, x - 3, y + u * h, x, y + u * h, 'k2-mb-pinline'); ln(gH, x + w, y + u * h, x + w + 3, y + u * h, 'k2-mb-pinline');
      }
      piece(gH, x, y, w, h, G.chip, 1.5); disc(gH, x + 4, y + 4, 1.4, 'k2-mb-mark');
    }
    chip(604, 46, 28, 28, 7, 4); chip(640, 268, 14, 11, 4, 2); chip(596, 214, 10, 10, 3, 2);
    [[702, 424], [702, 454], [702, 494], [702, 524]].forEach(function (c) {
      piece(gH, c[0], c[1], 32, 26, G.plastic, 2);
      path(gH, 'M' + (c[0] + 4) + ' ' + (c[1] + 7) + ' H' + (c[0] + 28) + ' V' + (c[1] + 19) + ' H' + (c[0] + 12) + ' V' + (c[1] + 13) + ' H' + (c[0] + 4) + ' Z', 'k2-mb-hole');
    });

    /* ---- the M.2 SSD: a screw at one end, the connector at the other, flash chips and the controller between */
    piece(gH, 400, 302, 14, 56, G.plastic, 2);
    var m2 = 'M206 308 H402 V352 H206 Q206 340 200 336 V324 Q206 320 206 308 Z';
    el('path', { d: m2, 'class': 'k2-outline-s', 'stroke-width': 2.4 }, gH);
    path(gH, m2, G.sub);
    for (q = 0; q < 12; q++) { rect(gH, 396, 311 + q * 3.4, 6, 2, G.gold); }
    piece(gH, 222, 314, 54, 32, G.chip, 2); piece(gH, 284, 314, 54, 32, G.chip, 2);
    piece(gH, 350, 318, 26, 24, G.chip, 2);
    rect(gH, 226, 318, 4, 4, 'k2-mb-mark', 2); rect(gH, 288, 318, 4, 4, 'k2-mb-mark', 2); rect(gH, 353, 321, 3, 3, 'k2-mb-mark', 1.5);
    for (q = 0; q < 5; q++) { rect(gH, 382, 316 + q * 6, 5, 3, G.gold); }
    disc(gH, 202, 330, 8.5, 'k2-outline'); disc(gH, 202, 330, 7.5, G.hub);
    ln(gH, 197.5, 325.5, 206.5, 334.5, 'k2-mb-seam'); ln(gH, 206.5, 325.5, 197.5, 334.5, 'k2-mb-seam');

    /* ---- the expansion slots: a short x1 above the graphics card, a long x4 below it */
    piece(gH, 60, 360, 64, 12, G.plastic, 2); rect(gH, 70, 364, 50, 4, 'k2-mb-groove', 1);
    piece(gH, 60, 568, 230, 12, G.plastic, 2); rect(gH, 82, 572, 200, 4, 'k2-mb-groove', 1); rect(gH, 66, 572, 12, 4, 'k2-mb-groove', 1);
    piece(gH, 60, 384, 236, 14, G.sink, 2);

    /* ---- the chipset under its heatsink, the CMOS battery in its holder */
    var cs = 'M612 412 H686 V486 L678 494 H604 V420 Z';
    el('path', { d: cs, 'class': 'k2-outline-s', 'stroke-width': 3 }, gH);
    path(gH, cs, G.sink);
    for (q = 0; q < 6; q++) { ln(gH, 606 + q * 14, 492, 626 + q * 14, 414 + (q > 4 ? 6 : 0), 'k2-mb-groove-s'); }
    piece(gH, 622, 430, 46, 46, G.ihs, 4);
    path(gH, cs, 'k2-mb-edge');
    disc(gH, 650, 540, 24, 'k2-outline'); disc(gH, 650, 540, 23, G.plastic); disc(gH, 650, 540, 19, G.ihs);
    ln(gH, 644, 540, 656, 540, 'k2-mb-seam'); ln(gH, 650, 534, 650, 546, 'k2-mb-seam');
    rect(gH, 646, 514, 8, 8, G.sink, 1);

    /* ---- the graphics card in the x16 slot, its fan side up: the bracket with its outputs, the shroud, two fans */
    var gpu = el('g', {}, gH);
    [[404, 'dp'], [432, 'dp'], [462, 'hdmi'], [494, 'dp']].forEach(function (o) {
      piece(gpu, -20, o[0], 14, o[1] === 'hdmi' ? 26 : 22, G.sink, 2);
      rect(gpu, -18, o[0] + 4, 6, o[1] === 'hdmi' ? 18 : 14, 'k2-mb-hole', 1);
    });
    piece(gpu, -8, 386, 12, 180, G.sink, 2);
    rect(gpu, -10, 380, 22, 10, G.sink, 2);
    piece(gpu, 8, 390, 590, 8, G.sub, 1, false);
    var shroud = 'M16 396 H588 L600 408 V548 L588 560 H16 L6 550 V406 Z';
    el('path', { d: shroud, 'class': 'k2-outline-s', 'stroke-width': 4 }, gpu);
    path(gpu, shroud, G.shroud);
    rect(gpu, 10, 394, 586, 5, G.sink, 2);
    path(gpu, 'M262 404 H298 L278 552 H242 Z', G.sink);
    path(gpu, 'M262 404 H298 L278 552 H242 Z', 'k2-mb-tint');
    path(gpu, 'M480 404 H496 L496 552 H470 Z', G.sink);
    path(gpu, 'M480 404 H496 L496 552 H470 Z', 'k2-mb-tint');
    piece(gpu, 504, 410, 86, 136, 'k2-cavity', 4);
    for (q = 0; q < 14; q++) { ln(gpu, 510 + q * 6, 414, 510 + q * 6, 542, 'k2-mb-fin'); }
    piece(gpu, 440, 384, 36, 10, G.plastic, 2);
    path(gpu, shroud, 'k2-edge');
    var fans = [[146, 478], [376, 478]].map(function (c, fi) {
      var R0 = 72, cid = f.id + '-fan' + (++UID), cl = el('clipPath', { id: cid }, f.defs);
      el('circle', { cx: c[0], cy: c[1], r: R0 }, cl);
      disc(gpu, c[0], c[1], R0 + 3, 'k2-outline'); disc(gpu, c[0], c[1], R0, 'k2-cavity');
      var fins = el('g', { 'clip-path': 'url(#' + cid + ')' }, gpu);
      for (q = -12; q <= 12; q++) { ln(fins, c[0] - R0, c[1] + q * 6, c[0] + R0, c[1] + q * 6, 'k2-mb-fin-dark'); }
      var rot = el('g', {}, gpu), blades = el('g', {}, rot);
      function P(r, a) { return pt([r * Math.cos(a), r * Math.sin(a)]); }
      var bd = 'M' + P(20, 0) + ' Q' + P(48, 0.1) + ' ' + P(68, 0.42) + ' A68 68 0 0 1 ' + P(68, 0.9) + ' Q' + P(44, 0.62) + ' ' + P(20, 0.56) + ' Z';
      for (q = 0; q < 9; q++) { el('path', { d: bd, fill: G.blade, 'class': 'k2-mb-blade', transform: 'rotate(' + (q * 40 + fi * 13) + ')' }, blades); }
      var blur = el('circle', { r: 69, fill: G.blur, opacity: 0 }, rot);
      disc(rot, 0, 0, 21, 'k2-outline'); disc(rot, 0, 0, 20, G.hub); disc(rot, 0, 0, 12, G.shroud);
      el('circle', { cx: c[0], cy: c[1], r: R0 - 1, 'class': 'k2-mb-rim' }, gpu);
      return { c: c, rot: rot, blades: blades, blur: blur };
    });

    /* ---- a monitor beside the board, its picture drawn in as the frame arrives */
    var D = p.display, pic = null, wipe = null, led = null, mon = null;
    if (D) {
      var mx = D.x, my = D.y, mw = D.w || 260, mh = Math.round(mw * 0.6), sx = mx + 8, sy = my + 8, sw = mw - 16, shh = mh - 22, hz = sy + shh * 0.58;
      mon = [mx, my, mx + mw, my + mh + 56];
      path(gH, 'M' + (mx + mw / 2 - 70) + ' ' + (my + mh + 56) + ' Q' + (mx + mw / 2) + ' ' + (my + mh + 40) + ' ' + (mx + mw / 2 + 70) + ' ' + (my + mh + 56) + ' Z', G.sink);
      piece(gH, mx + mw / 2 - 11, my + mh - 4, 22, 50, G.sink, 3);
      piece(gH, mx, my, mw, mh, G.bezel, 10);
      rect(gH, sx, sy, sw, shh, 'k2-mb-screen', 3);
      var wid = f.id + '-wipe' + (++UID), wc = el('clipPath', { id: wid }, f.defs);
      wipe = el('rect', { x: sx, y: sy, width: sw, height: 0 }, wc);
      pic = el('g', { 'clip-path': 'url(#' + wid + ')', opacity: 0 }, gH);
      rect(pic, sx, sy, sw, hz - sy + 1, G.sky);
      el('ellipse', { cx: sx + sw * 0.66, cy: hz, rx: sw * 0.3, ry: shh * 0.42, fill: G.sun }, pic);
      path(pic, 'M' + sx + ' ' + hz + ' L' + (sx + sw * 0.12) + ' ' + (hz - 18) + ' L' + (sx + sw * 0.22) + ' ' + (hz - 9) + ' L' + (sx + sw * 0.36) + ' ' + (hz - 30) +
        ' L' + (sx + sw * 0.5) + ' ' + (hz - 12) + ' L' + (sx + sw * 0.58) + ' ' + (hz - 16) + ' L' + (sx + sw * 0.7) + ' ' + (hz - 4) + ' L' + (sx + sw * 0.84) + ' ' + (hz - 22) +
        ' L' + (sx + sw) + ' ' + (hz - 8) + ' V' + hz + ' Z', 'k2-mb-hill');
      rect(pic, sx, hz, sw, sy + shh - hz, G.ground);
      for (q = -6; q <= 6; q++) {
        var gx0 = sx + sw / 2 + q * 4, gx1 = sx + sw / 2 + q * sw * 0.16, gy1 = sy + shh, ex = clamp(gx1, sx, sx + sw);
        if (ex !== gx1) { gy1 = hz + (gy1 - hz) * (ex - gx0) / (gx1 - gx0); gx1 = ex; }
        ln(pic, gx0, hz, gx1, gy1, 'k2-mb-grid');
      }
      for (q = 1; q <= 5; q++) { var gy = hz + (sy + shh - hz) * Math.pow(q / 5, 1.8); ln(pic, sx, gy, sx + sw, gy, 'k2-mb-grid'); }
      path(gH, 'M' + (sx + sw * 0.55) + ' ' + sy + ' H' + (sx + sw * 0.75) + ' L' + (sx + sw * 0.45) + ' ' + (sy + shh) + ' H' + (sx + sw * 0.25) + ' Z', 'k2-mb-shine');
      led = disc(gH, mx + mw - 18, my + mh - 7, 2.2, 'k2-mb-led');
    }

    /* ---- the buses: copper lanes on the board, lit in the course's blue, bursts of data along them */
    var buses = (p.buses || []).map(function (b) {
      var n = b.lanes || 4, gap = b.gap || 5, tone = b.tone === 'amber' ? '-amber' : '', lanes = [], host = gC;
      if (b.cable) {
        el('path', { d: poly(b.pts), 'class': 'k2-mb-cable', 'stroke-width': n * gap + 9 }, gB);
        el('path', { d: poly(offset(b.pts, -(n * gap + 9) * 0.22)), 'class': 'k2-mb-cable-hi' }, gB);
        var p0 = b.pts[0], p1 = b.pts[1], an = Math.atan2(p1[1] - p0[1], p1[0] - p0[0]) * 180 / Math.PI, pg = el('g', { transform: 'translate(' + pt(p0) + ') rotate(' + an.toFixed(1) + ')' }, gH);
        piece(pg, 0, -(n * gap + 12) / 2, 22, n * gap + 12, G.plastic, 3); rect(pg, 2, -(n * gap + 6) / 2, 5, n * gap + 6, G.sink, 1);
      }
      for (q = 0; q < n; q++) { lanes.push(track(offset(b.pts, (q - (n - 1) / 2) * gap))); }
      if (!b.cable) { lanes.forEach(function (L) { el('path', { d: poly(L.ps), 'class': 'k2-mb-bus' }, gB); }); }
      var lit = el('g', { opacity: 0 }, host);
      el('path', { d: poly(b.pts), 'class': 'k2-mb-glow' + tone, 'stroke-width': n * gap + 12 }, lit);
      lanes.forEach(function (L) { el('path', { d: poly(L.ps), 'class': 'k2-mb-lit' + tone }, lit); });
      var o = { b: b, lanes: lanes, lit: lit, tone: tone, host: host, shots: [], fired: Math.floor(f.get(b.send, 0) + 0.5), half: n * gap / 2 + 3 };
      if (b.label) {
        var li = 1, best = 0;
        for (q = 1; q < b.pts.length; q++) { var ll = Math.hypot(b.pts[q][0] - b.pts[q - 1][0], b.pts[q][1] - b.pts[q - 1][1]); if (ll > best) { best = ll; li = q; } }
        var ma = b.at || [(b.pts[li - 1][0] + b.pts[li][0]) / 2, (b.pts[li - 1][1] + b.pts[li][1]) / 2];
        f.label({ text: b.label, sub: b.sub, cls: 'k2-t-note', at: function () { return A(ma[0], ma[1]); }, side: b.side, dist: b.dist, fixed: b.fixed, lead: b.lead,
          show: function () { return b.show != null ? f.get(b.show, 0) : clamp(f.get(b.lit, 0) * 2 - 1, 0, 1); } });
      }
      f.solid(function () {
        if (f.get(b.lit, 0) < 0.05) { return []; }
        var out = [];
        for (var j = 1; j < b.pts.length; j++) {
          var u = b.pts[j - 1], v = b.pts[j];
          out.push(box([Math.min(u[0], v[0]) - o.half, Math.min(u[1], v[1]) - o.half, Math.max(u[0], v[0]) + o.half, Math.max(u[1], v[1]) + o.half]));
        }
        return out;
      });
      return o;
    });
    var clock = 0;
    function burst(o, back) {
      var b = o.b, sp = b.speed || 300, nk = b.packets || 3, len = b.len || 16;
      o.lanes.forEach(function (L, li) {
        for (var j = 0; j < nk; j++) {
          var gl = el('line', { 'class': 'k2-mb-pkt-glow' + o.tone, opacity: 0 }, o.host), co = el('line', { 'class': 'k2-mb-pkt', opacity: 0 }, o.host);
          o.shots.push({ L: L, t0: clock + j * 0.16 + rnd() * 0.1 + li * 0.02, sp: sp * (0.92 + rnd() * 0.16), len: len, back: back, g: gl, c: co });
        }
      });
    }
    function drop(sh) { [sh.g, sh.c].forEach(function (n) { if (n.parentNode) { n.parentNode.removeChild(n); } }); }

    /* ---- focus: the part in question keeps its light and gets a blue outline; the rest of the board steps back */
    var FOC = { 1: [192, 84, 388, 282], 2: [462, 8, 566, 366], 3: [-24, 378, 604, 568], 4: [190, 298, 420, 362], 5: [598, 406, 692, 500] };
    for (k in FOC) { FOC[k] = FOC[k].concat(FOC[k]); }
    FOC[6] = FOC[1].slice(0, 4).concat(FOC[2].slice(0, 4));          /* two outlines: the CPU and its RAM */
    var dimSets = [[1, [[192, 84, 388, 282], [98, 6, 408, 92], [98, 64, 180, 274]]], [2, [[462, 8, 566, 366]]], [3, [[-24, 378, 604, 568]]],
      [4, [[190, 298, 420, 362]]], [5, [[598, 406, 692, 500]]], [0, [[-16, 12, 104, 304], [104, 2, 156, 36], [690, 120, 738, 328], [698, 420, 738, 554], [624, 514, 676, 566], [16, 310, 98, 352], [56, 356, 128, 376], [56, 564, 294, 584]]]];
    var dims = dimSets.map(function (d0) {
      var g = el('g', { opacity: 0 }, gH);
      d0[1].forEach(function (r) { rect(g, r[0], r[1], r[2] - r[0], r[3] - r[1], 'k2-mb-dim', 6); });
      return { k: d0[0], g: g, v: 0 };
    });
    var ringG = el('g', { opacity: 0 }, gF), rings = [0, 1].map(function () { return [el('rect', { 'class': 'k2-mb-focus-glow', rx: 10 }, ringG), el('rect', { 'class': 'k2-mb-focus', rx: 10 }, ringG)]; });
    var fNow = Math.round(f.target(p.focus, 0)), fFrom = FOC[fNow] || null, fTo = fFrom, fK = 1, ringA = 0, fanV = 0, fanA = 0, fanHold = 0, moving = false;

    /* ---- names */
    var anchors = { cpu: [290, 188], ram: [562, 190], gpu: [300, 478], ssd: [300, 354], chipset: [645, 412], vrm: [125, 168], io: [52, 150], power: [713, 124],
      sata: [700, 490], port: [-20, 474], display: D ? [D.x + (D.w || 260) / 2, D.y] : [0, 0] };
    (p.tags || []).forEach(function (t) {
      var a = t.at || anchors[t.on] || [0, 0];
      f.label({ text: t.text, sub: t.sub, at: function () { return A(a[0], a[1]); }, side: t.side, dist: t.dist, fixed: t.fixed, lead: t.lead, r: t.r,
        show: t.show != null ? function () { return f.get(t.show, 1); } : null });
    });
    [[192, 84, 388, 282], [462, 8, 566, 366], [-24, 378, 604, 568], [190, 298, 420, 362], [598, 406, 692, 500], [98, 2, 408, 92], [98, 64, 180, 274],
     [-16, 12, 104, 304], [690, 120, 738, 328], [698, 420, 738, 554], [624, 514, 676, 566], [56, 564, 294, 584]].forEach(function (r) { f.solid(function () { return box(r); }); });
    if (mon) { f.solid(function () { return box(mon); }); }

    function setR(n, r, pad) { n.setAttribute('x', (r[0] - pad).toFixed(1)); n.setAttribute('y', (r[1] - pad).toFixed(1)); n.setAttribute('width', (r[2] - r[0] + 2 * pad).toFixed(1)); n.setAttribute('height', (r[3] - r[1] + 2 * pad).toFixed(1)); }
    return {
      onStep: function (n, instant) {
        var t = Math.round(f.target(p.focus, 0));
        if (!instant && t > 0 && t !== fNow) {
          var r = FOC[t], c = A((r[0] + r[2]) / 2, (r[1] + r[3]) / 2);
          f.pulse(c[0], c[1], { delay: 200, r: Math.min(140, Math.max(r[2] - r[0], r[3] - r[1]) * s * 0.45) });
        }
      },
      draw: function (dt, snap) {
        dt = dt || 0; clock += dt; moving = false;
        /* focus */
        var t = Math.round(f.target(p.focus, 0));
        if (t !== fNow) { if (t > 0) { fFrom = fNow > 0 && fTo ? cur() : FOC[t]; fTo = FOC[t]; fK = 0; } fNow = t; }
        fK = snap ? 1 : Math.min(1, fK + dt * 2.4);
        ringA = snap ? (fNow > 0 ? 1 : 0) : approach(ringA, fNow > 0 ? 1 : 0, dt, 6);
        if (Math.abs(ringA - (fNow > 0 ? 1 : 0)) < 0.004) { ringA = fNow > 0 ? 1 : 0; }
        if (fK < 1 || (ringA > 0 && ringA < 1)) { moving = true; }
        function cur() { var e = fK * fK * (3 - 2 * fK); return fFrom.map(function (v, j) { return lerp(v, fTo[j], e); }); }
        if (fTo) { var rr = cur(); rings.forEach(function (rg, j) { setR(rg[0], rr.slice(j * 4), 4); setR(rg[1], rr.slice(j * 4), 4); }); }
        setOp(ringG, ringA);
        dims.forEach(function (d0) {
          var want = fNow > 0 && d0.k !== fNow && !(fNow === 6 && (d0.k === 1 || d0.k === 2)) ? 1 : 0;
          d0.v = snap ? want : approach(d0.v, want, dt, 5);
          if (Math.abs(d0.v - want) < 0.004) { d0.v = want; } else { moving = true; }
          setOp(d0.g, d0.v * 0.5);
        });
        /* power */
        setOp(hot, clamp(f.get(p.power, 0), 0, 1) * 0.5);
        /* buses and their bursts */
        var fanBusy = false;
        buses.forEach(function (o) {
          var b = o.b, want = Math.floor(f.get(b.send, 0) + 0.5);
          setOp(o.lit, clamp(f.get(b.lit, 0), 0, 1));
          if (snap) { o.fired = want; o.shots.forEach(drop); o.shots = []; }
          while (o.fired < want) { o.fired++; burst(o, b.both ? o.fired % 2 === 0 : !!b.back); }
          if (want < o.fired) { o.fired = want; }
          var keep = [];
          o.shots.forEach(function (sh) {
            var d = (clock - sh.t0) * sh.sp, L = sh.L.len;
            if (d - sh.len > L) { drop(sh); return; }
            var h = clamp(d, 0, L), tl = clamp(d - sh.len, 0, L);
            if (sh.back) { h = L - h; tl = L - tl; }
            var a = sh.L.at(tl), c = sh.L.at(h), on = d > 0 ? 1 : 0;
            [sh.g, sh.c].forEach(function (nd) { nd.setAttribute('x1', a[0].toFixed(1)); nd.setAttribute('y1', a[1].toFixed(1)); nd.setAttribute('x2', c[0].toFixed(1)); nd.setAttribute('y2', c[1].toFixed(1)); });
            setOp(sh.g, on * 0.55); setOp(sh.c, on);
            keep.push(sh);
          });
          o.shots = keep;
          if (o.shots.length) { moving = true; if (b.fans) { fanBusy = true; } }
        });
        /* the card's fans: they spin up while it works, run on a moment, then coast to a stop */
        if (snap) { fanV = 0; fanHold = 0; }
        else {
          fanHold = fanBusy ? 0.6 : Math.max(0, fanHold - dt);
          fanV = fanBusy || fanHold > 0 ? fanV + (1 - fanV) * (1 - Math.exp(-dt * 2.6)) : Math.max(0, fanV - dt * 0.75);
        }
        fanA = (fanA + fanV * fanV * 1500 * dt) % 360;
        if (fanV > 0) { moving = true; }
        fans.forEach(function (fn, j) {
          fn.rot.setAttribute('transform', 'translate(' + fn.c[0] + ' ' + fn.c[1] + ') rotate(' + (fanA * (j ? 1.07 : 1)).toFixed(1) + ')');
          setOp(fn.blades, 1 - fanV * 0.6); setOp(fn.blur, fanV * 0.85);
        });
        /* the picture on the monitor */
        if (pic) {
          var sh2 = clamp(f.get(D.show, 0), 0, 1);
          wipe.setAttribute('height', (sh2 * (Math.round((D.w || 260) * 0.6) - 22)).toFixed(1));
          setOp(pic, sh2 > 0.002 ? 1 : 0); setOp(led, 0.35 + 0.65 * sh2);
        }
      },
      live: function () { return moving && !f.hidden; }
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
