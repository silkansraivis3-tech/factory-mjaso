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
    f.T = {}; f.S = {}; f.fx = []; f.pending = []; f.out = {}; f.parts = []; f.byId = {}; f.labels = []; f.solids = []; f.rate = spec.rates || {};
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
    prev: function () { if (this.step > 0) { this.goStep(this.step - 1, true); } },
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
      f.pending = (f.pending || []).filter(function (q) { if (t >= q.at || instant) { f.T[q.k] = q.v; return false; } busy = true; return true; });
      for (k in f.T) {
        if (f.S[k] == null || instant || reduce) { f.S[k] = f.T[k]; continue; }
        if (Math.abs(f.S[k] - f.T[k]) > 1e-4 * (1 + Math.abs(f.T[k]))) {
          f.S[k] = approach(f.S[k], f.T[k], dt, f.rate[k] || 6); busy = true;
        } else { f.S[k] = f.T[k]; }
      }
      f.parts.forEach(function (q) { if (q.calc) { q.calc(dt); } });
      f.parts.forEach(function (q) { if (q.draw) { q.draw(dt, instant || reduce); } if (q.live && q.live()) { busy = true; } });
      f.fx = (f.fx || []).filter(function (e) {           /* one-shot effects: a ring where something has just changed */
        var k2 = (t - e.t0) / e.ms;
        if (k2 < 0) { busy = true; return true; }
        if (k2 >= 1 || instant) { e.done(); return false; }
        e.go(k2); busy = true; return true;
      });
      f.readouts();
      f.follow();
      if (!busy && f.relayout) { f.relayout = false; f.layout(); }
      return busy;
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
      f.frame(true);
      f.layout();
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
    layout: function () {
      var f = this, placed = [], solids = [], i;
      for (i = 0; i < f.solids.length; i++) { solids.push(f.solids[i]()); }
      f.labels.forEach(function (L) {
        var at = L.o.at(), b = L.t.getBBox(), bw = b.width, bh = b.height, best = null, bestCost = 1e9;
        if (!bw) { return; }
        var sides = L.o.side ? [L.o.side] : [];
        sides = sides.concat(['right', 'left', 'up', 'down', 'upright', 'upleft', 'downright', 'downleft']);
        var dists = L.o.fixed ? [L.o.dist || 16] : [L.o.dist || 16, 46, 80];
        dists.forEach(function (dist, di) {
          sides.forEach(function (s, si) {
            var dx = /right/.test(s) ? 1 : /left/.test(s) ? -1 : 0, dy = /up/.test(s) ? -1 : /down/.test(s) ? 1 : 0;
            var x = at[0] + dx * dist + (dx < 0 ? -bw : dx === 0 ? -bw / 2 : 0);
            var y = at[1] + dy * dist + (dy < 0 ? -bh : dy === 0 ? -bh / 2 : 0);
            var R = { x: x, y: y, x2: x + bw, y2: y + bh }, cost = di * 40 + si * 3;
            if (R.x < 6 || R.y < 6 || R.x2 > f.W - 6 || R.y2 > f.H - 6) { cost += 500; }
            placed.concat(solids).forEach(function (o) { if (o && R.x < o.x2 && o.x < R.x2 && R.y < o.y2 && o.y < R.y2) { cost += 200; } });
            if (cost < bestCost) { bestCost = cost; best = { R: R, dist: dist, di: di }; }
          });
          if (L.o.fixed) { return; }
        });
        L.off = [best.R.x - at[0], best.R.y - at[1]]; L.far = (best.di > 0 || best.dist > 30) && L.o.lead !== false; L.bw = bw; L.bh = bh; L.by = b.y;
        placed.push({ x: best.R.x - 4, y: best.R.y - 4, x2: best.R.x2 + 4, y2: best.R.y2 + 4 });
      });
      f.follow();
    },
    follow: function () {
      this.labels.forEach(function (L) {
        if (!L.off) { return; }
        var at = L.o.at(), x = at[0] + L.off[0], y = at[1] + L.off[1];
        L.box.setAttribute('transform', 'translate(' + (x).toFixed(1) + ' ' + (y - L.by).toFixed(1) + ')');
        var show = L.o.show ? L.o.show() : 1;
        setOp(L.g, show);
        if (L.far) {
          var ex = clamp(at[0], x, x + L.bw), ey = clamp(at[1], y, y + L.bh);
          L.lead.setAttribute('d', 'M' + pt(at) + ' L' + pt([ex, ey]));
          L.dot.setAttribute('cx', at[0].toFixed(1)); L.dot.setAttribute('cy', at[1].toFixed(1));
          L.lead.style.display = L.dot.style.display = '';
        } else { L.lead.style.display = L.dot.style.display = 'none'; }
        if (L.o.text && L.o.live) { L.t.firstChild.textContent = L.o.live(); }
      });
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
      box: { x: x0, y: y0, w: W, h: H }, xaxis: X, yaxis: Y
    };
    f.charts = f.charts || {}; f.charts[p.id] = C;
    var g = el('g', {}, f.L.back), v;
    for (v = X.min; v <= X.max + 1e-9; v += X.step) {
      el('line', { x1: C.X(v), y1: y0, x2: C.X(v), y2: y0 + H, 'class': 'k2-grid' }, g);
      el('text', { x: C.X(v), y: y0 + H + 24, 'text-anchor': 'middle', 'class': 'k2-t-tick' }, g, num(v, X.decimals));
    }
    for (v = Y.min; v <= Y.max + 1e-9; v += Y.step) {
      el('line', { x1: x0, y1: C.Y(v), x2: x0 + W, y2: C.Y(v), 'class': 'k2-grid' }, g);
      el('text', { x: x0 - 12, y: C.Y(v) + 5, 'text-anchor': 'end', 'class': 'k2-t-tick' }, g, num(v, Y.decimals));
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
      var t = el('g', {}, parent), r = el('rect', { rx: 8, height: 28, 'class': 'k2-tag' }, t), tx = el('text', { 'class': 'k2-t-tag', y: 20 }, t);
      return { g: t, r: r, t: tx, set: function (s, x, y, anchor) {
        tx.textContent = s; var bw = tx.getComputedTextLength() + 18, h = 28;
        r.setAttribute('width', bw.toFixed(1)); tx.setAttribute('x', 9);
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
        setOp(g, f.get(p.show, 1));
        if (ghost) {
          var gx = f.get(p.ghost.x), gy = F(gx), gpx = C.X(gx), gpy = C.Y(gy);
          ghost.drop.setAttribute('d', 'M' + pt([b.x, gpy]) + ' H' + gpx.toFixed(1) + ' V' + (b.y + b.h).toFixed(1));
          ghost.dot.setAttribute('cx', gpx.toFixed(1)); ghost.dot.setAttribute('cy', gpy.toFixed(1));
          ghost.ty.set(tpl(p.tagy || '{y}', { y: gy }, p.dy == null ? 0 : p.dy), b.x - 8, gpy, 'end');
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
      var val = el('text', { x: 0, y: 30, 'class': 'k2-t-val k2-halo' }, words);
      var valA = el('text', { x: 0, y: 30, 'class': 'k2-t-val k2-t-amber k2-halo' }, words);
      var note = c.note ? el('text', { x: 0, y: 58, 'class': 'k2-t-note k2-halo' }, words, c.note) : null;
      var at = corner(c, 'to');
      return { g: g, ra: ra, lock: lock, words: words, val: val, valA: valA, note: note,
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
          var v = f.get(c.value, 0), txt = tpl(c.fmt || '{v}', { v: v }, c.decimals || 0);
          N.val.textContent = txt; N.valA.textContent = txt; setOp(N.valA, hot); setOp(N.val, 1 - hot);
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
  w.KIT2D = { mount: mount, define: define, types: TYPES, figures: figs,
    h: { el: el, clamp: clamp, lerp: lerp, approach: approach, num: num, tpl: tpl, pt: pt, poly: poly, setOp: setOp, textLines: textLines } };
  if (d.readyState === 'loading') { d.addEventListener('DOMContentLoaded', auto); } else { setTimeout(auto, 0); }
}(window));
