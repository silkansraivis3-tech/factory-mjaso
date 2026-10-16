/* ==========================================================================
   kit.js - the NOVIKONTAS figure kit (course-visuals)

   A figure is a SPEC, not a drawing: ready-made parts (gauge, level, valve,
   pipe, alarm log ...) placed on a panel, and STEPS that move their values.
   The engine tweens each value; when a value crosses one of its marks the
   alarm fires there and then. "The alarm comes before the relief valve" is
   therefore true by construction - never by a hand-placed second picture.

   Mount:  KIT.mount(svgOrContainer, spec) -> figure
           or <svg data-kit="#spec-id"> + <script type="application/json" id="spec-id">
   Drive:  figure.next() / prev() / go(n) / replay()   (KIT.controls wires buttons)

   Plain SVG + DOM, no dependencies, works offline. The format is in SPEC.md.
   ========================================================================== */
(function (root) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';
  var UID = 0;
  var TYPES = {};
  var EASE = {
    linear: function (t) { return t; },
    inout: function (t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; },
    out: function (t) { return 1 - Math.pow(1 - t, 3); }
  };

  /* ---------------------------------------------------------------- helpers */
  function reducedMotion() {
    return !!(root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }
  function el(tag, attrs, parent, text) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    if (text != null) n.textContent = text;
    if (parent) parent.appendChild(n);
    return n;
  }
  function lines(parent, attrs, text, lh) {
    var t = el('text', attrs, parent), rows = String(text).split('\n');
    rows.forEach(function (s, i) { el('tspan', { x: attrs.x || 0, dy: i ? (lh || 16) : 0 }, t, s); });
    return rows.length;
  }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function num(v, d) {
    var s = Math.abs(v).toFixed(d);
    return (v < 0 && +s !== 0 ? '−' : '') + s;
  }
  function fmt(v, p) {
    var s = (p.sign && v > 0.0001 ? '+' : '') + num(v, p.decimals != null ? p.decimals : 0);
    return p.unit ? s + ' ' + p.unit : s;
  }
  function polar(r, deg) { var a = deg * Math.PI / 180; return [r * Math.cos(a), r * Math.sin(a)]; }
  function arc(r, d0, d1) {
    var p0 = polar(r, d0), p1 = polar(r, d1);
    return 'M' + p0[0].toFixed(2) + ' ' + p0[1].toFixed(2) + ' A' + r + ' ' + r + ' 0 ' +
      (d1 - d0 > 180 ? 1 : 0) + ' 1 ' + p1[0].toFixed(2) + ' ' + p1[1].toFixed(2);
  }
  function clock(fig, t) {
    var b = String(fig.spec.clock || '10:42:00').split(':');
    var s = (+b[0]) * 3600 + (+b[1]) * 60 + (+b[2] || 0) + Math.floor(t / 1000);
    function two(n) { return (n < 10 ? '0' : '') + n; }
    return two(Math.floor(s / 3600) % 24) + ':' + two(Math.floor(s / 60) % 60) + ':' + two(s % 60);
  }
  function textWidth(t, fallbackPerChar) {
    var w = 0;
    try { w = t.getComputedTextLength(); } catch (e) { w = 0; }
    return w || t.textContent.length * fallbackPerChar;
  }

  /* marks: a value on a part's scale. Crossing it lights the mark, may log an
     alarm, may HOLD the value there (a shut-off) and may start other moves. */
  function mark(m) {
    return { at: +m.at, label: m.label || '', kind: m.kind || 'alarm', dir: m.dir || 'up',
             alarm: m.alarm || '', stop: !!m.stop, then: m.then || [], fired: false, node: null, zone: null };
  }
  function crossed(m, a, b) { return m.dir === 'down' ? (a > m.at && b <= m.at) : (a < m.at && b >= m.at); }
  function past(m, v) { return m.dir === 'down' ? v <= m.at : v >= m.at; }
  function flagMark(m, on) { if (m.node) m.node.classList.toggle('on', on); }

  /* ----------------------------------------------------------------- figure */
  function Figure(host, spec) {
    var self = this, size = spec.size || [600, 440];
    this.spec = spec;
    this.uid = 'kit' + (++UID);
    this.svg = host.namespaceURI === NS ? host : el('svg', {}, host);
    this.svg.setAttribute('viewBox', '0 0 ' + size[0] + ' ' + size[1]);
    this.svg.setAttribute('role', 'img');
    this.svg.setAttribute('data-motion', 'teaching');
    if (spec.label) this.svg.setAttribute('aria-label', spec.label);
    this.svg.classList.add('kit');
    this.parts = {}; this.list = []; this.handlers = {};
    this.tweens = []; this.alarms = []; this.now = 0; this.n = 0; this.raf = 0; this.silent = false;
    (spec.parts || []).forEach(function (p) { self.add(p); });
    this.clearState();
  }

  Figure.prototype = {
    add: function (p) {
      var make = TYPES[p.type];
      if (!make) throw new Error('kit: unknown part type "' + p.type + '"');
      var src = p.source && this.parts[p.source];
      if (src) {                       // a repeater draws the same scale as its source
        var q = {};
        ['min', 'max', 'start', 'sweep', 'normal', 'marks', 'unit', 'decimals'].forEach(function (k) { if (src.p[k] != null) q[k] = src.p[k]; });
        for (var k in p) q[k] = p[k];
        p = q;
      }
      var g = el('g', { 'class': 'kit-part kit-part-' + p.type, transform: 'translate(' + (p.x || 0) + ' ' + (p.y || 0) + ')' }, this.svg);
      var part = { id: p.id, p: p, g: g, marks: (p.marks || []).map(mark), mirrors: [], moving: 0,
                   v0: p.value != null ? +p.value : (src ? src.v0 : 0) };
      part.v = part.v0;
      make(this, part, g, p);
      if (p.id) this.parts[p.id] = part;
      if (src) src.mirrors.push(part);
      this.list.push(part);
      return part;
    },

    /* a second value on one part, addressed as "<id>.<key>" (a pipe's fill as well as its flow) */
    sub: function (part, key, v0, render) {
      var child = { id: part.id + '.' + key, p: {}, g: part.g, marks: [], mirrors: [], moving: 0, v0: v0, v: v0, render: render };
      if (part.id) this.parts[child.id] = child;
      this.list.push(child);
      return child;
    },

    on: function (ev, fn) { (this.handlers[ev] = this.handlers[ev] || []).push(fn); return this; },
    emit: function (ev, a) { (this.handlers[ev] || []).forEach(function (fn) { fn(a); }); },
    steps: function () { return (this.spec.steps || []).length; },

    paint: function (part) {
      if (part.render) part.render(part.v);
      part.mirrors.forEach(function (mm) { if (mm.render) mm.render(part.v); });
    },
    repaint: function () {
      var self = this;
      this.list.forEach(function (part) {
        if (!part.p.source) self.paint(part);
        if (part.moving && part.motion) part.motion(0);
        part.moving = 0;
      });
      this.alarmsChanged(null);
    },
    flag: function (part, m, on) {
      if (part.flag) part.flag(m, on);
      var i = part.marks.indexOf(m);
      part.mirrors.forEach(function (mm) { if (mm.flag && mm.marks[i]) mm.flag(mm.marks[i], on); });
    },
    alarmsChanged: function (newest) {
      if (this.silent) return;
      var self = this;
      this.list.forEach(function (part) { if (part.alarms) part.alarms(self.alarms, newest, self); });
    },

    /* every value change goes through here, so every crossing is seen */
    set: function (part, v) {
      var self = this, prev = part.v, held = false;
      part.marks.forEach(function (m) { if (m.stop && crossed(m, prev, v)) { v = m.at; held = true; } });
      part.v = v;
      part.marks.filter(function (m) { return !m.fired && crossed(m, prev, v); })
        .sort(function (a, b) { return a.dir === 'down' ? b.at - a.at : a.at - b.at; })   // in the order the value meets them
        .forEach(function (m) { m.fired = true; self.fire(part, m); });
      part.marks.forEach(function (m) { if (m.fired && !past(m, v)) { m.fired = false; self.flag(part, m, false); } });
      if (!this.silent) this.paint(part);
      return held;
    },
    fire: function (part, m) {
      var self = this;
      this.flag(part, m, true);
      if (m.alarm) {
        var a = { text: m.alarm, kind: m.kind, t: this.now };
        this.alarms.unshift(a);
        this.alarmsChanged(a);
        this.emit('alarm', a);
      }
      m.then.forEach(function (act) { self.play(act); });
    },

    /* act = [partId, to, ms, delay, ease]. Moves on one part queue up: a move takes
       over from the one before it when its own delay runs out. */
    play: function (act) {
      var part = this.parts[act[0]];
      if (!part) return;
      this.tweens.push({ part: part, to: +act[1], ms: Math.max(0, act[2] || 0), at: this.now + (act[3] || 0),
                         ease: EASE[act[4]] || EASE.inout, from: null, dead: false });
    },
    tick: function (dt) {
      var self = this, mv = {};
      this.now += dt;
      this.tweens.slice().forEach(function (t) {
        if (t.dead || self.now < t.at) return;
        if (t.from === null) {
          t.from = t.part.v;
          self.tweens.forEach(function (o) { if (o !== t && o.part === t.part && o.from !== null) o.dead = true; });
        }
        var k = t.ms ? clamp((self.now - t.at) / t.ms, 0, 1) : 1;
        var held = self.set(t.part, t.from + (t.to - t.from) * t.ease(k));
        if (held || k >= 1) t.dead = true;
      });
      this.tweens = this.tweens.filter(function (t) { return !t.dead; });
      this.tweens.forEach(function (t) { if (t.from !== null && t.part.id) mv[t.part.id] = t.to > t.from ? 1 : -1; });
      this.list.forEach(function (part) {
        var d = mv[part.id] || 0;
        if (d !== part.moving) { part.moving = d; if (part.motion && !self.silent) part.motion(d); }
      });
    },
    /* frames drive the motion; a timer keeps time when a WebView stops sending frames
       (a hidden or throttled pane), so a step always reaches its end */
    run: function () {
      var self = this, last = null, clock = root.performance || Date;
      this.stop();
      function step() {
        var now = clock.now(), dt = last === null ? 16 : Math.min(100, now - last);   // a slow device still keeps time
        last = now;
        self.tick(dt);
        if (self.tweens.length) return true;
        self.stop();
        self.emit('settled', self.n);
        return false;
      }
      function frame() { if (step()) self.raf = root.requestAnimationFrame(frame); }
      this.raf = root.requestAnimationFrame(frame);
      this.timer = root.setInterval(function () { if (last === null || clock.now() - last > 200) step(); }, 120);
    },
    stop: function () {
      if (this.raf) root.cancelAnimationFrame(this.raf);
      if (this.timer) root.clearInterval(this.timer);
      this.raf = 0; this.timer = 0;
    },
    flush: function () {            // run the remaining moves to their end, invisibly
      var guard = 0;
      this.silent = true;
      while (this.tweens.length && guard++ < 50000) this.tick(16);
      this.silent = false;
      this.repaint();
    },

    clearState: function () {
      var self = this;
      this.tweens = []; this.alarms = [];
      this.list.forEach(function (part) {
        part.v = part.v0;
        part.marks.forEach(function (m) { m.fired = false; self.flag(part, m, false); });
      });
      if (!this.silent) this.repaint();
    },
    applyStep: function (k) {
      var self = this, s = this.spec.steps[k - 1];
      if (s.reset) this.clearState();
      if (s.set) Object.keys(s.set).forEach(function (id) {
        var part = self.parts[id];
        if (part) { part.v = +s.set[id]; if (!self.silent) self.paint(part); }
      });
      (s.play || []).forEach(function (a) { self.play(a); });
    },
    /* step n always starts from the end of step n-1, however you got here */
    go: function (n, instant) {
      n = clamp(n | 0, 0, this.steps());
      this.stop();
      this.now = 0;
      this.silent = true;
      this.clearState();
      for (var k = 1; k < n; k++) { this.applyStep(k); this.flush(); this.silent = true; }
      this.silent = false;
      this.repaint();
      this.n = n;
      if (n > 0) {
        this.applyStep(n);
        if (instant || reducedMotion()) this.flush(); else this.run();
      }
      this.emit('step', n);
    },
    next: function () { if (this.n < this.steps()) this.go(this.n + 1); },
    prev: function () { if (this.n > 0) this.go(this.n - 1, true); },
    replay: function () { this.go(this.n); }
  };

  /* ------------------------------------------------------------------ parts */

  /* panel - the monitoring screen frame, its title and the alarm-state chip */
  TYPES.panel = function (fig, part, g, p) {
    var w = p.w || 600, h = p.h || 440;
    el('rect', { x: 1, y: 1, width: w - 2, height: h - 2, rx: 14, 'class': 'kit-panel' }, g);
    if (p.title) el('text', { x: 20, y: 29, 'class': 'kit-ptitle' }, g, p.title);
    el('line', { x1: 1, x2: w - 1, y1: 44, y2: 44, 'class': 'kit-rule' }, g);
    var chip = el('g', { transform: 'translate(' + (w - 16) + ' 12)' }, g);
    var box = el('rect', { y: -2, height: 26, rx: 13 }, chip);      // 26 high, 16 a side: the words keep 4 px clear at 2/3 size (L54)
    var txt = el('text', { y: 15.5, 'text-anchor': 'middle' }, chip);
    part.alarms = function (list) {
      var n = list.length;
      var worst = list.some(function (a) { return a.kind === 'trip'; }) ? 'trip' : 'alarm';
      txt.textContent = n ? n + (n > 1 ? ' ALARMS' : ' ALARM') : 'ALL NORMAL';
      var tw = textWidth(txt, 8) + 32;
      box.setAttribute('x', -tw); box.setAttribute('width', tw); txt.setAttribute('x', -tw / 2);
      chip.setAttribute('class', 'kit-chip' + (n ? ' kit-on-' + worst : ''));
    };
  };

  /* level - a tank level column with its marks and a digital readout */
  TYPES.level = function (fig, part, g, p) {
    var w = p.w || 60, h = p.h || 200, lo = p.min || 0, hi = p.max != null ? p.max : 100;
    function y(v) { return h - clamp((v - lo) / (hi - lo), 0, 1) * h; }
    var cid = fig.uid + '-' + p.id + '-clip';
    el('rect', { x: 3, y: 3, width: w - 6, height: h - 6, rx: 5 }, el('clipPath', { id: cid }, el('defs', {}, g)));
    if (p.label) el('text', { x: w / 2, y: -14, 'text-anchor': 'middle', 'class': 'kit-h' }, g, p.label);
    el('rect', { width: w, height: h, rx: 8, 'class': 'kit-vessel' }, g);
    var inside = el('g', { 'clip-path': 'url(#' + cid + ')' }, g);
    var body = el('rect', { x: 0, width: w, 'class': 'kit-liquid' }, inside);
    var surf = el('line', { x1: 0, x2: w, 'class': 'kit-surface' }, inside);
    if (p.ticks !== false) {
      for (var i = 0; i <= 4; i++) {
        var tv = lo + (hi - lo) * i / 4, ty = y(tv);
        el('line', { x1: -7, x2: 0, y1: ty, y2: ty, 'class': 'kit-tickl' }, g);
        el('text', { x: -11, y: ty + 4.5, 'text-anchor': 'end', 'class': 'kit-tick' }, g, num(tv, 0));
      }
    }
    part.marks.forEach(function (m) {
      var my = y(m.at), mg = el('g', { 'class': 'kit-mark kit-' + m.kind }, g);
      el('line', { x1: -4, x2: w + 10, y1: my, y2: my }, mg);
      if (m.label) el('text', { x: w + 14, y: my + 4.5 }, mg, m.label);
      m.node = mg;
    });
    var out = null;
    if (p.readout !== false) {
      var bw = Math.max(w + 16, 78);
      el('rect', { x: w / 2 - bw / 2, y: h + 14, width: bw, height: 30, rx: 6, 'class': 'kit-dig' }, g);
      out = el('text', { x: w / 2, y: h + 35, 'text-anchor': 'middle', 'class': 'kit-num' }, g);
    }
    part.render = function (v) {
      var yy = y(v);
      body.setAttribute('y', yy); body.setAttribute('height', h - yy);
      surf.setAttribute('y1', yy); surf.setAttribute('y2', yy);
      if (out) out.textContent = fmt(v, p);
    };
    part.flag = flagMark;
  };

  /* gauge - a dial: normal band, alarm and trip zones, needle, readout.
     With "source" it repeats another gauge (a bridge repeater); "mini" drops the labels. */
  TYPES.gauge = function (fig, part, g, p) {
    var r = p.r || 70, lo = p.min || 0, hi = p.max != null ? p.max : 10;
    var a0 = p.start != null ? p.start : 135, sw = p.sweep || 270, mini = !!p.mini;
    var tw = mini ? 4 : 7, tr = r - tw / 2 - 4;
    function ang(v) { return a0 + clamp((v - lo) / (hi - lo), 0, 1) * sw; }
    function zone(m, a, b) {
      m.zone = el('path', { d: arc(tr, ang(a), ang(b)), 'class': 'kit-zone kit-' + m.kind, 'stroke-width': tw }, g);
    }
    if (p.label) el('text', { x: 0, y: -r - 14, 'text-anchor': 'middle', 'class': 'kit-h' }, g, p.label);
    el('circle', { r: r, 'class': 'kit-dial' }, g);
    el('path', { d: arc(tr, a0, a0 + sw), 'class': 'kit-track', 'stroke-width': tw }, g);
    if (p.normal) el('path', { d: arc(tr, ang(p.normal[0]), ang(p.normal[1])), 'class': 'kit-band', 'stroke-width': tw }, g);
    var ups = part.marks.filter(function (m) { return m.dir !== 'down' && m.kind !== 'limit'; }).sort(function (a, b) { return a.at - b.at; });
    ups.forEach(function (m, i) { zone(m, m.at, i + 1 < ups.length ? ups[i + 1].at : hi); });
    var downs = part.marks.filter(function (m) { return m.dir === 'down' && m.kind !== 'limit'; }).sort(function (a, b) { return b.at - a.at; });
    downs.forEach(function (m, i) { zone(m, i + 1 < downs.length ? downs[i + 1].at : lo, m.at); });
    if (!mini) {
      var n = p.ticks || 10, every = p.every || 2;
      for (var i = 0; i <= n; i++) {
        var a = a0 + sw * i / n, major = i % every === 0;
        var t0 = polar(tr - tw / 2 - 2, a), t1 = polar(tr - tw / 2 - (major ? 10 : 6), a);
        el('line', { x1: t0[0], y1: t0[1], x2: t1[0], y2: t1[1], 'class': 'kit-tickl' }, g);
        if (major && p.numbers !== false) {
          var tp = polar(tr - tw / 2 - 22, a);
          el('text', { x: tp[0], y: tp[1] + 4.5, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, num(lo + (hi - lo) * i / n, 0));
        }
      }
    }
    part.marks.forEach(function (m) {
      var a = ang(m.at), mg = el('g', { 'class': 'kit-mark kit-' + m.kind }, g);
      var q0 = polar(tr - tw / 2 - 1, a), q1 = polar(r + (mini ? 2 : 5), a);
      el('line', { x1: q0[0], y1: q0[1], x2: q1[0], y2: q1[1] }, mg);
      if (!mini && m.label) {
        var c = Math.cos(a * Math.PI / 180), s = Math.sin(a * Math.PI / 180), pt = polar(r + 14, a);
        var nl = String(m.label).split('\n').length;
        var y0 = pt[1] + 4.5 + (s > 0.3 ? 6 : s < -0.3 ? -6 - (nl - 1) * 16 : -(nl - 1) * 8);
        lines(mg, { x: pt[0], y: y0, 'text-anchor': c > 0.3 ? 'start' : c < -0.3 ? 'end' : 'middle' }, m.label);
      }
      m.node = mg;
    });
    var nd = el('g', { 'class': 'kit-needle' }, g), tail = mini ? 5 : 13, wd = mini ? 2 : 3;
    el('path', { d: 'M' + (-tail) + ' ' + (-wd) + ' L' + (tr - tw) + ' -0.9 L' + (tr - tw) + ' 0.9 L' + (-tail) + ' ' + wd + ' Z' }, nd);
    el('circle', { r: mini ? 3.5 : 7, 'class': 'kit-hub' }, g);
    var val = null, below = r + 22;
    if (!mini && p.readout !== false) {         // under the dial, clear of the scale numbers
      el('rect', { x: -44, y: r + 10, width: 88, height: 30, rx: 6, 'class': 'kit-dig' }, g);
      val = el('text', { x: 0, y: r + 31, 'text-anchor': 'middle', 'class': 'kit-num' }, g);
      below = r + 58;
    }
    if (p.caption) {
      var right = p.captionAt === 'right';
      lines(g, { x: right ? r + 12 : 0, y: right ? 0 : below, 'text-anchor': right ? 'start' : 'middle', 'class': 'kit-cap' }, p.caption);
    }
    part.render = function (v) {
      nd.setAttribute('transform', 'rotate(' + ang(v).toFixed(2) + ')');
      if (val) val.textContent = fmt(v, p);
    };
    part.flag = function (m, on) { flagMark(m, on); if (m.zone) m.zone.classList.toggle('on', on); };
  };

  /* readout - a digital tile (temperature, gas %LEL ...) that changes state on its marks */
  TYPES.readout = function (fig, part, g, p) {
    var w = p.w || 120, h = p.h || 56;
    el('rect', { width: w, height: h, rx: 8, 'class': 'kit-tile' }, g);
    if (p.label) el('text', { x: 12, y: 20, 'class': 'kit-tl' }, g, p.label);
    var val = el('text', { x: w - 12, y: h - 11, 'text-anchor': 'end', 'class': 'kit-big' }, g);
    part.render = function (v) { val.textContent = fmt(v, p); };
    part.flag = function (m, on) { g.classList.toggle('kit-on-' + m.kind, on); };
  };

  /* well - a bilge well let into the deck, a leak dripping into it, a temperature
     sensor (ISA "TT") at the bottom. value = how full the pool is, 0..1 */
  TYPES.well = function (fig, part, g, p) {
    var w = p.w || 130, h = p.h || 110, x0 = Math.round(w * 0.3), x1 = Math.round(w * 0.7), top = 34, bot = h - 16;
    var dx = x0 + 14, cid = fig.uid + '-' + p.id + '-pit';
    el('rect', { x: x0, y: top, width: x1 - x0, height: bot - top }, el('clipPath', { id: cid }, el('defs', {}, g)));
    var pool = el('rect', { x: x0, width: x1 - x0, 'class': 'kit-pool', 'clip-path': 'url(#' + cid + ')' }, g);
    el('path', { d: 'M0 ' + top + ' H' + x0 + ' V' + bot + ' H' + x1 + ' V' + top + ' H' + w + ' V' + h + ' H0 Z', 'class': 'kit-steel' }, g);
    el('line', { x1: dx, y1: -20, x2: dx, y2: 0, 'class': 'kit-pipe-s' }, g);
    el('line', { x1: dx - 12, y1: 0, x2: dx + 12, y2: 0, 'class': 'kit-flange' }, g);
    [0, 0.3, 0.6].forEach(function (d) {
      el('circle', { cx: dx, cy: 6, r: 3.2, 'class': 'kit-drop', style: 'animation-delay:' + d + 's;--fall:' + (bot - 14) + 'px' }, g);
    });
    var tx = x1 - 10;
    el('line', { x1: tx, y1: top - 8, x2: tx, y2: bot - 6, 'class': 'kit-probe' }, g);
    el('circle', { cx: tx, cy: top - 22, r: 20, 'class': 'kit-bubble' }, g);   // 20: "TT" keeps its 4 px clear of the ring down to 2/3 size (L54)
    el('text', { x: tx, y: top - 17.5, 'text-anchor': 'middle', 'class': 'kit-bubble-t' }, g, p.tag || 'TT');
    part.render = function (v) {
      var ly = bot - clamp(v, 0, 1) * (bot - top) * 0.75;
      pool.setAttribute('y', ly); pool.setAttribute('height', bot - ly);
    };
    part.motion = function (d) { g.classList.toggle('kit-dripping', d > 0); };
  };

  /* valve - ISA bow-tie with an actuator. value 1 = open, 0 = closed (filled) */
  TYPES.valve = function (fig, part, g, p) {
    var s = p.size || 12, k = s * 0.72;
    var bow = 'M' + (-s) + ' ' + (-k) + ' L' + s + ' ' + k + ' V' + (-k) + ' L' + (-s) + ' ' + k + ' Z';
    var sym = el('g', { transform: p.rotate ? 'rotate(' + p.rotate + ')' : null }, g);   // 90 = on a vertical pipe
    if (p.actuator !== false) {
      el('line', { x1: 0, y1: 0, x2: 0, y2: -s - 6, 'class': 'kit-stem' }, sym);
      el('path', { d: 'M-9 ' + (-s - 6) + ' A9 9 0 0 1 9 ' + (-s - 6) + ' Z', 'class': 'kit-act' }, sym);
    }
    el('path', { d: bow, 'class': 'kit-valve-bg' }, sym);
    var fill = el('path', { d: bow, 'class': 'kit-vfill' }, sym);
    el('path', { d: bow, 'class': 'kit-valve' }, sym);
    var right = p.labelAt === 'right', lx = right ? s + 26 : 0, ly = right ? -4 : s + 22, anchor = right ? 'start' : 'middle';
    var nl = p.label ? lines(g, { x: lx, y: ly, 'text-anchor': anchor, 'class': 'kit-cap' }, p.label) : 0;
    var st = p.state === false ? null : el('text', { x: lx, y: ly + nl * 16, 'text-anchor': anchor, 'class': 'kit-state' }, g);
    if (p.trip === false) g.classList.add('kit-quiet');   // closing is normal here: no red
    part.render = function (v) {
      var shut = v < 0.5;
      fill.style.opacity = (1 - clamp(v, 0, 1)).toFixed(3);
      if (st) st.textContent = shut ? 'CLOSED' : 'OPEN';
      g.classList.toggle('kit-shut', shut);
    };
  };

  /* pipe - a line, its contents and their movement. Two values:
       value      0..1  how fast the contents flow (0 = standing still)
       "<id>.fill" 0..1 the fluid front advancing from the start of the path;
                  1..2 the pipe emptying towards p.drain (0 = start, 0.5 = middle, 1 = end, default)
     fluid: "liquid" (cold blue, long dashes) or "gas" (pale, fine dots). double: a double-walled pipe. */
  TYPES.pipe = function (fig, part, g, p) {
    var fluid = p.fluid === 'gas' ? 'gas' : 'liquid', mid = fig.uid + '-' + (p.id || 'p' + (++UID)) + '-m';
    g.classList.add('kit-fl-' + fluid);
    if (p.double) {
      el('path', { d: p.d, 'class': 'kit-jacket' }, g);
      el('path', { d: p.d, 'class': 'kit-annulus' }, g);
    }
    el('path', { d: p.d, 'class': 'kit-pipe' }, g);
    el('path', { d: p.d, 'class': 'kit-bore' }, g);
    var mask = el('mask', { id: mid, maskUnits: 'userSpaceOnUse', x: -4000, y: -4000, width: 8000, height: 8000 }, el('defs', {}, g));
    var reach = el('path', { d: p.d, 'class': 'kit-reach' }, mask);
    var inside = el('g', { mask: 'url(#' + mid + ')' }, g);
    el('path', { d: p.d, 'class': 'kit-content' }, inside);
    var flow = el('path', { d: p.d, 'class': 'kit-flow' }, inside);
    var L = 0;
    try { L = reach.getTotalLength(); } catch (e) { L = 0; }
    L = L || 1000;
    var drain = p.drain != null ? +p.drain : 1;
    part.render = function (v) {
      flow.style.opacity = v > 0.02 ? Math.min(1, 0.35 + v).toFixed(2) : 0;
      flow.style.animationDuration = (0.8 / Math.max(v, 0.2)).toFixed(2) + 's';
    };
    fig.sub(part, 'fill', p.fill != null ? +p.fill : 1, function (f) {
      var s, e;
      if (f <= 1) { s = 0; e = clamp(f, 0, 1) * L; }
      else { var k = clamp(f - 1, 0, 1); s = k * drain * L; e = L - k * (1 - drain) * L; }
      reach.setAttribute('stroke-dasharray', '0 ' + s.toFixed(1) + ' ' + Math.max(0, e - s).toFixed(1) + ' ' + (2 * L).toFixed(1));
    });
  };

  /* tank - a horizontal type C tank (cylinder with dished ends). value = liquid level 0..1 */
  TYPES.tank = function (fig, part, g, p) {
    var w = p.w || 190, h = p.h || 110, ex = h * 0.28, cid = fig.uid + '-' + p.id + '-t';
    var shape = 'M' + ex + ' 0 H' + (w - ex) + ' A' + ex + ' ' + (h / 2) + ' 0 0 1 ' + (w - ex) + ' ' + h +
      ' H' + ex + ' A' + ex + ' ' + (h / 2) + ' 0 0 1 ' + ex + ' 0 Z';
    el('path', { d: shape }, el('clipPath', { id: cid }, el('defs', {}, g)));
    el('path', { d: shape, 'class': 'kit-vessel' }, g);
    var liq = el('rect', { x: 0, width: w, 'class': 'kit-liquid', 'clip-path': 'url(#' + cid + ')' }, g);
    var surf = el('line', { x1: 0, x2: w, 'class': 'kit-surface', 'clip-path': 'url(#' + cid + ')' }, g);
    el('path', { d: shape, 'class': 'kit-vessel-o' }, g);
    if (p.label) lines(g, { x: w / 2, y: h + 22, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) {
      var y = h - clamp(v, 0, 1) * h;
      liq.setAttribute('y', y); liq.setAttribute('height', h - y);
      surf.setAttribute('y1', y); surf.setAttribute('y2', y);
    };
  };

  /* space - a room or enclosure, named. value 0..1 = how strongly it is picked out.
     style "room" (dashed boundary, default) or "enclosure" (solid: a gas valve unit, a hood) */
  TYPES.space = function (fig, part, g, p) {
    var w = p.w || 120, h = p.h || 90;
    var wash = el('rect', { width: w, height: h, rx: 8, 'class': 'kit-wash' }, g);
    el('rect', { width: w, height: h, rx: 8, 'class': 'kit-space kit-' + (p.style || 'room') }, g);
    if (p.label) {
      var below = p.labelAt === 'below';
      // 14 / 24: the name keeps its 4 px clear of the room's edge also when the figure is shown at 2/3 size (L54);
      // in a low room (a TCS 30 high) it sits in the middle, clear of the top and the bottom alike
      lines(g, { x: below ? w / 2 : 14, y: below ? h + 20 : Math.min(24, h / 2 + 4.5), 'text-anchor': below ? 'middle' : 'start',
                 'class': below ? 'kit-cap' : 'kit-sl' }, p.label);
    }
    part.render = function (v) { wash.style.opacity = clamp(v, 0, 1).toFixed(3); g.classList.toggle('kit-lit', v > 0.5); };
  };

  /* exchanger - P&ID heat exchanger (vaporizer, heater). value 0..1 = heating */
  TYPES.exchanger = function (fig, part, g, p) {
    var r = p.r || 18, z = r * 0.62;
    el('circle', { r: r, 'class': 'kit-shell' }, g);
    var coil = el('path', { d: 'M' + (-r) + ' 0 L' + (-z) + ' 0 L' + (-z / 2) + ' ' + (-z) + ' L0 ' + z + ' L' + (z / 2) + ' ' + (-z) + ' L' + z + ' 0 L' + r + ' 0', 'class': 'kit-coil' }, g);
    el('line', { x1: -z, y1: r + 2, x2: -z, y2: r + 12, 'class': 'kit-hm' }, g);
    el('line', { x1: z, y1: r + 2, x2: z, y2: r + 12, 'class': 'kit-hm' }, g);
    if (p.label) lines(g, { x: 0, y: r + 30, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { g.classList.toggle('kit-active', v > 0.5); coil.style.opacity = (0.55 + 0.45 * clamp(v, 0, 1)).toFixed(2); };
  };

  /* pump - P&ID centrifugal pump. value 0 stopped, 1 running (impeller turns) */
  TYPES.pump = function (fig, part, g, p) {
    var r = p.r || 15;
    el('path', { d: 'M0 ' + (-r) + ' H' + (r + 8) + ' V' + (-r + 8) + ' H' + (r * 0.5), 'class': 'kit-shell-o' }, g);
    el('circle', { r: r, 'class': 'kit-shell' }, g);
    var imp = el('g', { 'class': 'kit-imp' }, g);
    [0, 120, 240].forEach(function (a) { el('path', { d: 'M0 0 L' + (r * 0.7) + ' -3', transform: 'rotate(' + a + ')' }, imp); });
    if (p.label) lines(g, { x: 0, y: r + 22, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { g.classList.toggle('kit-running', v > 0.5); };
  };

  /* engine - a dual-fuel engine block. value 0 stopped, 1 running */
  TYPES.engine = function (fig, part, g, p) {
    var w = p.w || 100, h = p.h || 70, n = p.cylinders || 4, cw = (w - 16) / n;
    el('rect', { width: w, height: h, rx: 8, 'class': 'kit-block' }, g);
    for (var i = 0; i < n; i++) {
      var cx = 8 + cw * i + cw / 2;
      el('rect', { x: cx - cw * 0.32, y: -10, width: cw * 0.64, height: 14, rx: 2, 'class': 'kit-head' }, g);
      el('rect', { x: cx - cw * 0.22, y: 8, width: cw * 0.44, height: 12, rx: 2, 'class': 'kit-piston', style: 'animation-delay:' + (-0.15 * i) + 's' }, g);
    }
    var st = el('text', { x: w / 2, y: h - 12, 'text-anchor': 'middle', 'class': 'kit-state' }, g);
    if (p.label) lines(g, { x: w / 2, y: h + 20, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { var on = v > 0.5; g.classList.toggle('kit-running', on); st.textContent = on ? 'RUNNING' : 'STOPPED'; };
  };

  /* vent - a vent outlet to the open air. value 0..1 = how much is venting (puffs) */
  TYPES.vent = function (fig, part, g, p) {
    el('path', { d: 'M-9 0 H9 M-6 -6 H6', 'class': 'kit-flange' }, g);
    var puffs = el('g', { 'class': 'kit-puffs' }, g);
    [0, 0.45, 0.9].forEach(function (d, i) {
      el('circle', { cx: (i - 1) * 5, cy: -12, r: 7, style: 'animation-delay:' + d + 's' }, puffs);
    });
    if (p.label) lines(g, { x: p.labelAt === 'left' ? -18 : 18, y: -2, 'text-anchor': p.labelAt === 'left' ? 'end' : 'start', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { puffs.style.opacity = clamp(v, 0, 1).toFixed(2); g.classList.toggle('kit-venting', v > 0.05); };
  };

  /* badge - a numbered step marker. value 0..1 = lit */
  TYPES.badge = function (fig, part, g, p) {
    el('circle', { r: 17, 'class': 'kit-badge-o' }, g);       // 17: every digit keeps its 4 px clear of the ring down to 2/3 size
    var disc = el('circle', { r: 17, 'class': 'kit-badge' }, g);
    el('text', { y: 5, 'text-anchor': 'middle', 'class': 'kit-badge-t' }, g, String(p.n != null ? p.n : ''));
    part.render = function (v) { disc.style.opacity = clamp(v, 0, 1).toFixed(2); g.classList.toggle('kit-lit', v > 0.5); };
  };

  /* wire - an instrument signal line (ISA: dashed) */
  TYPES.wire = function (fig, part, g, p) { el('path', { d: p.d, 'class': 'kit-wire' }, g); };

  /* text - a heading or caption; "\n" breaks lines */
  TYPES.text = function (fig, part, g, p) {
    lines(g, { x: 0, y: 0, 'text-anchor': p.anchor || 'middle', 'class': 'kit-' + (p.style || 'cap') }, p.text);
  };

  /* log - the alarm list: newest on top, time-stamped, flashing until it settles */
  TYPES.log = function (fig, part, g, p) {
    var w = p.w || 560, rows = p.rows || 2, rh = 24;
    el('rect', { width: w, height: 32 + rows * rh, rx: 10, 'class': 'kit-logbox' }, g);
    el('text', { x: 14, y: 20, 'class': 'kit-tl' }, g, p.label || 'ALARM LOG');
    var body = el('g', { transform: 'translate(0 29)' }, g);
    part.alarms = function (list, newest) {
      while (body.firstChild) body.removeChild(body.firstChild);
      if (!list.length) { el('text', { x: 14, y: 16, 'class': 'kit-empty' }, body, p.empty || 'No active alarms'); return; }
      list.slice(0, rows).forEach(function (a, i) {
        var at = el('g', { transform: 'translate(8 ' + (i * rh) + ')' }, body);
        var row = el('g', { 'class': 'kit-row kit-' + a.kind + (a === newest ? ' kit-new' : '') }, at);
        el('rect', { width: w - 16, height: rh - 3, rx: 5 }, row);
        el('rect', { width: 5, height: rh - 3, rx: 2, 'class': 'kit-sev' }, row);
        el('text', { x: 16, y: 15.5, 'class': 'kit-time' }, row, clock(fig, a.t));
        el('text', { x: 94, y: 15.5, 'class': 'kit-msg' }, row, a.text);
      });
    };
  };

  /* --------------------------------------------------------------- mounting */
  function mount(host, spec) {
    var f = new Figure(host, spec), slide = host.closest ? host.closest('.slide[id]') : null;
    host.__kit = f;
    if (slide) deck(f, slide);
    return f;
  }

  /* in a compiled deck: the figure starts fresh each time its slide is entered, stops when it is
     left, and lights the slide's own text line for each step - spec step "line": 2 (or [2, 3])
     marks [data-i="2"] .cur, and the lines of the steps before it .lit (gb_compose.css).
     The deck's own Next / Back (button, arrow keys, swipe) walk its steps before the slide changes -
     gb_deck.js hook "step"; a module no longer carries its own copy of this (M03, 2026-10-15) */
  root.GB_HOOKS = root.GB_HOOKS || {};
  function deck(f, slide) {
    var id = slide.id, before = root.GB_HOOKS[id] || {};
    root.GB_HOOKS[id] = {
      enter: function () { if (before.enter) before.enter(); f.go(0, true); },
      leave: function () { if (before.leave) before.leave(); f.stop(); },
      step: function (dir) {
        if (before.step && before.step(dir)) return true;
        if (dir > 0 && f.n < f.steps()) { f.next(); return true; }
        if (dir < 0 && f.n > 0) { f.prev(); return true; }
        return false;
      }
    };
    function ids(s) { return s && s.line != null ? [].concat(s.line) : []; }
    f.on('step', function (n) {
      [].forEach.call(slide.querySelectorAll('[data-i]'), function (x) { x.classList.remove('cur', 'lit'); });
      (f.spec.steps || []).slice(0, n).forEach(function (s, i) {
        ids(s).forEach(function (k) {
          var line = slide.querySelector('[data-i="' + k + '"]');
          if (line) line.classList.add(i === n - 1 ? 'cur' : 'lit');
        });
      });
    });
    /* a line a step lights is also the way to that step: the presenter taps "3 Fuel preparation room" (or
       focuses it and presses Enter) and step 3 plays - the hand-built decks did this, and a legend card that
       looks like a button and does nothing reads as broken (operator, 2026-10-15). The first step that
       lights a line owns it. */
    (f.spec.steps || []).forEach(function (s, i) {
      ids(s).forEach(function (k) {
        var line = slide.querySelector('[data-i="' + k + '"]');
        /* a line that heads a grouped box ("Zone 1:" over its list) - the whole box is what the presenter taps */
        var tap = line && line.parentNode && line.parentNode.matches && line.parentNode.matches('.copy > div.box') ? line.parentNode : line;
        if (!tap || tap.__kitStep) return;
        tap.__kitStep = i + 1;
        tap.classList.add('kit-tap');
        tap.setAttribute('tabindex', '0');
        tap.setAttribute('role', 'button');
        tap.addEventListener('click', function () { f.go(tap.__kitStep); });
        tap.addEventListener('keydown', function (e) {
          if ((e.key || '') === 'Enter') { e.preventDefault(); e.stopPropagation(); f.go(tap.__kitStep); }
        });
      });
    });
  }

  /* a part a course needed that the kit did not have yet. It is built to the same contract as the
     parts above, lives in the module's assets/kit_parts.js, and is promoted into this file by a merge
     request once the module is complete (course-visuals/kit/PARTS.md). A part the kit already has
     wins: the module's copy is then out of date and is skipped. */
  var LOCAL = {}, ADDED = {};
  function define(type, make, meta) {
    meta = meta || {};
    var mine = meta.status !== 'kit';               // "new": a course's part, not merged yet
    if (TYPES[type] && mine) {
      if (root.console) console.warn('kit: "' + type + '" is in the kit now - the module\'s own copy is skipped');
      return;
    }
    TYPES[type] = make;
    (mine ? LOCAL : ADDED)[type] = meta;
    if (meta.css && document.head && !document.querySelector('style[data-kit-part="' + type + '"]')) {
      var st = document.createElement('style');
      st.setAttribute('data-kit-part', type);
      st.textContent = meta.css;
      document.head.appendChild(st);
    }
  }

  /* wires [data-act=prev|next|replay], .dots and [data-kit-title] found inside scope */
  function controls(fig, scope) {
    function q(s) { return scope.querySelector(s); }
    var dots = q('.dots'), title = q('[data-kit-title]');
    var prev = q('[data-act="prev"]'), next = q('[data-act="next"]'), again = q('[data-act="replay"]');
    if (dots) {
      dots.innerHTML = '';
      for (var i = 0; i <= fig.steps(); i++) dots.appendChild(document.createElement('i'));
    }
    function show(n) {
      if (dots) [].forEach.call(dots.children, function (d, i) { d.classList.toggle('on', i === n); });
      if (prev) prev.disabled = n === 0;
      if (next) next.disabled = n >= fig.steps();
      if (again) again.disabled = n === 0;
      if (title) title.textContent = n ? (fig.spec.steps[n - 1].title || '') : (fig.spec.idle || '');
    }
    fig.on('step', show);
    if (prev) prev.addEventListener('click', function () { fig.prev(); });
    if (next) next.addEventListener('click', function () { fig.next(); });
    if (again) again.addEventListener('click', function () { fig.replay(); });
    show(fig.n);
  }

  function auto() {
    [].forEach.call(document.querySelectorAll('[data-kit]'), function (host) {
      if (host.__kit) return;
      var src = document.querySelector(host.getAttribute('data-kit'));
      if (!src) return;
      var fig;
      try { fig = mount(host, JSON.parse(src.textContent)); }
      catch (err) {                    // say so on the screen - a blank figure in front of a class says nothing
        if (root.console) console.error(err);
        host.outerHTML = '<p class="kit-error">This figure could not be drawn: ' + String(err.message || err).replace(/</g, '&lt;') + '</p>';
        return;
      }
      controls(fig, host.closest('[data-kit-scope]') || host.parentNode);
    });
  }
  /* after kit_parts.js has had its turn to define parts, which loads after this file */
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto); else setTimeout(auto, 0);

  root.KIT = {
    mount: mount, controls: controls, Figure: Figure, types: TYPES, define: define, local: LOCAL, added: ADDED,
    reducedMotion: reducedMotion,
    /* the drawing helpers every part uses - a new part uses these too, never its own */
    h: { el: el, lines: lines, clamp: clamp, num: num, fmt: fmt, polar: polar, arc: arc,
         flagMark: flagMark, textWidth: textWidth, NS: NS }
  };
})(window);

/* ==========================================================================
   PARTS ADDED FROM COURSES
   Each block below was made by a course build that needed it, used in that course's module, and
   merged here by a reviewed merge request (scripts/kit_parts.py promote). Same contract as the
   parts above - PARTS.md. Never edit a block here to suit one course: change it for every course.
   ========================================================================== */
/* kit-part: ga */
KIT.define('ga', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 600, d = p.h || 80, plan = p.view === 'plan';
  var wl = p.draft != null ? p.draft : 0.55, hull;
  if (plan) {
    var b = w * 0.16;
    hull = 'M0 0 H' + (w - b) + ' Q' + w + ' 0 ' + w + ' ' + (d / 2) + ' Q' + w + ' ' + d + ' ' + (w - b) + ' ' + d + ' H0 Z';
  } else {
    hull = 'M0 0 H' + w + ' Q' + (w * 0.97) + ' ' + (d * 0.62) + ' ' + (w * 0.87) + ' ' + d +
      ' H' + (w * 0.1) + ' L' + (w * 0.03) + ' ' + (d * 0.5) + ' Z';
    if (p.water !== false) {
      h.el('rect', { x: -12, y: d * wl, width: w + 24, height: d * (1 - wl) + 10, 'class': 'kit-ga-sea', 'data-no-contain': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);   // a backdrop: the hull covers it
    }
  }
  h.el('path', { d: hull, 'class': 'kit-ga-hull' }, g);
  var wash = h.el('path', { d: hull, 'class': 'kit-wash', 'data-no-contain': '' }, g);
  (p.frames || []).forEach(function (x) {
    h.el('line', { x1: x, x2: x, y1: 3, y2: d - 3, 'class': 'kit-ga-frame' }, g);
  });
  if (!plan && p.house) {
    var hs = p.house;
    h.el('rect', { x: hs.x, y: -hs.h, width: hs.w, height: hs.h, rx: 3, 'class': 'kit-ga-house' }, g);
    if (p.funnel) {
      var f = p.funnel, fh = f.h || 22;
      h.el('rect', { x: f.x, y: -hs.h - fh, width: f.w || 18, height: fh, rx: 2, 'class': 'kit-ga-house' }, g);
    }
  }
  if (p.label) h.lines(g, { x: w / 2, y: d + (plan ? 22 : 30), 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    wash.style.opacity = h.clamp(v, 0, 1).toFixed(3);
    g.classList.toggle('kit-lit', v > 0.5);
  };
}, {
  family: 'spaces',
  status: 'kit', merged_from: "IGF Basic M02",
  course: 'IGF Basic', module: 'M02', made: '2026-10-15',
  why: 'M02 s12 zones on an IGF ship, M01 s04 the five new spaces and s09 two ships compared: the ship the named spaces sit in',
  value: 'how strongly the ship is picked out, 0..1 (named spaces are space parts placed on it)',
  css: '.kit-ga-hull{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2;stroke-linejoin:round;transition:stroke .3s}.kit-ga-sea{fill:var(--cold);opacity:.12}.kit-ga-house{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:1.5}.kit-ga-frame{stroke:var(--faint-d);stroke-width:1;stroke-dasharray:3 4}.kit-lit .kit-ga-hull{stroke:var(--blue)}',
  example: { size: [420, 200], parts: [
    { id: 'G', type: 'ga', x: 30, y: 80, w: 360, h: 64, house: { x: 30, w: 60, h: 40 }, funnel: { x: 50, w: 16, h: 18 }, label: 'side view' },
    { id: 'S', type: 'space', x: 140, y: 88, w: 150, h: 46, label: 'FUEL TANK HOLD' } ],
    steps: [ { title: 'The ship', play: [['G', 1, 500]] }, { title: 'A space in it', play: [['G', 0, 400], ['S', 1, 500]] } ] }
});
/* end kit-part */
/* kit-part: scale */
KIT.define('scale', function (fig, part, g, p) {
  var h = KIT.h, H = p.h || 300, bw = p.w || 22, lo = p.min != null ? p.min : 0, hi = p.max != null ? p.max : 100;
  var every = p.every || 20, reach = p.reach || bw + 300;
  if (p.orient === 'h') return across(h, part, g, p, lo, hi, every);
  function y(v) { return H - h.clamp((v - lo) / (hi - lo), 0, 1) * H; }
  h.el('rect', { width: bw, height: H, rx: bw / 2, 'class': 'kit-vessel' }, g);
  for (var t = Math.ceil(lo / every) * every; t <= hi; t += every) {
    h.el('line', { x1: -7, x2: 0, y1: y(t), y2: y(t), 'class': 'kit-tickl' }, g);
    h.el('text', { x: -11, y: y(t) + 4.5, 'text-anchor': 'end', 'class': 'kit-tick' }, g, h.num(t, 0));
  }
  if (p.unit) h.el('text', { x: bw / 2, y: -12, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, p.unit);
  (p.limits || []).forEach(function (m) {
    var lg = h.el('g', { 'class': 'kit-scale-limit' }, g);
    h.el('line', { x1: -4, x2: reach, y1: y(m.at), y2: y(m.at) }, lg);
    if (m.label) h.el('text', { x: reach, y: y(m.at) - 11, 'text-anchor': 'end', 'class': 'kit-h' }, lg, m.label);
  });
  var made = (p.markers || []).map(function (m) {
    var mg = h.el('g', {}, g);
    h.el('path', { d: 'M' + (bw + 2) + ' 0 L' + (bw + 12) + ' -6 V6 Z', 'class': 'kit-scale-pointer' }, mg);
    h.el('path', { d: 'M' + (bw + 18) + ' -9 H' + (bw + 30) + ' L' + (bw + 34) + ' -5 V11 H' + (bw + 18) + ' Z', 'class': 'kit-scale-can' }, mg);
    h.el('text', { x: bw + 44, y: m.note ? -2 : 5, 'class': 'kit-h' }, mg, m.label || '');
    if (m.note) h.lines(mg, { x: bw + 44, y: 14, 'class': 'kit-cap' }, m.note);
    return { g: mg, at: y(m.at) };
  });
  part.render = function (v) {
    made.forEach(function (m, k) {
      var c = h.clamp(v - k, 0, 1), from = 0;            // from the top of the scale
      m.g.setAttribute('transform', 'translate(0 ' + (from + (m.at - from) * c).toFixed(1) + ')');
      m.g.style.opacity = c > 0.001 ? '1' : '0';
    });
  };
  /* orient "h": the scale runs across (len wide, w thick), each marker stands on a stem at its own height
     (rise) so the labels fill the panel above the axis instead of stacking in one column; side "left" puts a
     marker's words to the left of its stem */
  function across(h, part, g, p, lo, hi, every) {
    var L = p.len || 560, th = p.w || 18, reach = p.reach || 260;
    function x(v) { return h.clamp((v - lo) / (hi - lo), 0, 1) * L; }
    h.el('rect', { width: L, height: th, rx: th / 2, 'class': 'kit-vessel' }, g);
    for (var t = Math.ceil(lo / every) * every; t <= hi; t += every) {
      h.el('line', { x1: x(t), x2: x(t), y1: th, y2: th + 7, 'class': 'kit-tickl' }, g);
      h.el('text', { x: x(t), y: th + 24, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, h.num(t, 0));
    }
    if (p.unit) h.el('text', { x: L + 12, y: th / 2 + 4.5, 'class': 'kit-tick' }, g, p.unit);
    (p.limits || []).forEach(function (m) {
      var lg = h.el('g', { 'class': 'kit-scale-limit' }, g);
      h.el('line', { x1: x(m.at), x2: x(m.at), y1: -reach, y2: th + 4 }, lg);
      if (m.label) h.el('text', { x: x(m.at) + (m.side === 'left' ? -10 : 10), y: -reach + 14, 'text-anchor': m.side === 'left' ? 'end' : 'start',
                                  'class': 'kit-h' }, lg, m.label);
    });
    var made = (p.markers || []).map(function (m, k) {
      var rise = m.rise || 60 + 70 * k, left = m.side === 'left', ax = left ? 'end' : 'start', tx = left ? -16 : 16;
      var mg = h.el('g', {}, g);
      h.el('path', { d: 'M0 -2 L-6 -12 H6 Z', 'class': 'kit-scale-pointer' }, mg);
      h.el('line', { x1: 0, x2: 0, y1: -12, y2: -rise + 12, 'class': 'kit-scale-stem' }, mg);
      h.el('path', { d: 'M-6 ' + (-rise - 10) + ' H6 L10 ' + (-rise - 6) + ' V' + (-rise + 10) + ' H-6 Z', 'class': 'kit-scale-can' }, mg);
      h.el('text', { x: tx, y: -rise + (m.note ? -2 : 5), 'text-anchor': ax, 'class': 'kit-h' }, mg, m.label || '');
      if (m.note) h.lines(mg, { x: tx, y: -rise + 14, 'text-anchor': ax, 'class': 'kit-cap' }, m.note);
      return { g: mg, at: x(m.at) };
    });
    part.render = function (v) {
      made.forEach(function (m, k) {
        var c = h.clamp(v - k, 0, 1);                     // drops onto its own place on the axis
        m.g.setAttribute('transform', 'translate(' + m.at.toFixed(1) + ' ' + (-(1 - c) * 40).toFixed(1) + ')');
        m.g.style.opacity = c > 0.001 ? Math.min(1, c * 2).toFixed(2) : '0';
      });
    };
  }
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M01",
  course: 'IGF Basic', module: 'M01', made: '2026-10-15',
  why: 'M01 s02: oil fuel, methanol and LNG slide to their places on a temperature scale either side of the 60 °C line',
  value: '0..number of markers - marker k slides from the top of the scale to its place while the value goes from k to k+1',
  css: '.kit-scale-limit line{stroke:var(--blue);stroke-width:2.5;stroke-dasharray:8 5}.kit-scale-limit text{fill:var(--blue)}.kit-scale-stem{stroke:var(--dim-d);stroke-width:1.5}.kit-scale-pointer{fill:var(--txt-d)}.kit-scale-can{fill:var(--deep-3);stroke:var(--txt-d);stroke-width:1.5;stroke-linejoin:round}',
  example: { size: [360, 300], parts: [
    { id: 'S', type: 'scale', x: 60, y: 40, h: 220, min: -40, max: 100, every: 20, unit: '°C', reach: 270,
      limits: [{ at: 60, label: '60 °C' }],
      markers: [{ label: 'oil fuel', at: 75 }, { label: 'methanol', note: 'flashpoint about 12 °C', at: 12 }] } ],
    steps: [ { title: 'Oil fuel', play: [['S', 1, 1500]] }, { title: 'Methanol', play: [['S', 2, 1500]] } ] }
});
/* end kit-part */
/* kit-part: cylinder */
KIT.define('cylinder', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 140, H = p.h || 230, cov = 26, ox = w * 0.22, gx = w * 0.78, top = cov + 6;
  var pTop = cov + (H - cov) * 0.34, ph = 46;
  var moving = h.el('g', { 'class': 'kit-cylinder-moving' }, g);
  h.el('line', { x1: w / 2, x2: w / 2, y1: pTop + ph, y2: H - 36, 'class': 'kit-cylinder-rod' }, moving);   // stays in the liner at the bottom of the stroke
  h.el('rect', { x: 4, y: pTop, width: w - 8, height: ph, rx: 4, 'class': 'kit-cylinder-piston' }, moving);
  [10, 18, 26].forEach(function (dy) { h.el('line', { x1: 6, x2: w - 6, y1: pTop + dy, y2: pTop + dy, 'class': 'kit-cylinder-ring' }, moving); });
  h.el('rect', { x: -12, y: cov, width: 12, height: H - cov, 'class': 'kit-cylinder-wall' }, g);
  h.el('rect', { x: w, y: cov, width: 12, height: H - cov, 'class': 'kit-cylinder-wall' }, g);
  h.el('rect', { x: -16, y: 0, width: w + 32, height: cov, rx: 4, 'class': 'kit-cylinder-wall' }, g);
  h.el('line', { x1: w / 2, x2: w / 2, y1: -26, y2: cov + 2, 'class': 'kit-stem' }, g);
  h.el('path', { d: 'M' + (w / 2 - 18) + ' ' + (cov + 6) + ' Q' + (w / 2) + ' ' + (cov - 2) + ' ' + (w / 2 + 18) + ' ' + (cov + 6) + ' Z', 'class': 'kit-cylinder-inj' }, g);
  [ox, gx].forEach(function (x) {                       // an injector passes through the cover by design
    h.el('rect', { x: x - 5, y: -6, width: 10, height: cov + 12, rx: 2, 'class': 'kit-cylinder-inj', 'data-may-cross': '' }, g);
  });
  function fan(x, cls, ends) {
    var fg = h.el('g', { 'class': cls }, g);
    ends.forEach(function (e) { h.el('line', { x1: x, y1: top, x2: x + e[0], y2: top + e[1] }, fg); });
    return fg;
  }
  var gas = fan(gx, 'kit-cylinder-gas', [[-62, 30], [-50, 44], [-34, 52]]);
  var pilot = fan(ox, 'kit-cylinder-pilot', [[16, 14], [22, 8]]);
  var oil = fan(ox, 'kit-cylinder-oil', [[58, 30], [48, 44], [32, 52], [64, 16]]);
  var fire = h.el('g', { 'class': 'kit-cylinder-fire' }, g), fx = w * 0.46, fy = top + 26;
  h.el('circle', { cx: fx, cy: fy, r: 9 }, fire);
  [0, 45, 90, 135, 180, 225, 270, 315].forEach(function (a) {
    var q0 = h.polar(13, a), q1 = h.polar(20, a);
    h.el('line', { x1: fx + q0[0], y1: fy + q0[1], x2: fx + q1[0], y2: fy + q1[1] }, fire);
  });
  if (p.labels !== false) {
    h.el('text', { x: -24, y: 16, 'text-anchor': 'end', 'class': 'kit-cap' }, g, 'oil injector');
    h.el('text', { x: w + 24, y: 16, 'text-anchor': 'start', 'class': 'kit-cap' }, g, 'gas injector');
    h.el('text', { x: w / 2, y: -36, 'text-anchor': 'middle', 'class': 'kit-cap' }, g, 'exhaust valve');
    h.el('text', { x: -24, y: pTop + ph / 2 + 4, 'text-anchor': 'end', 'class': 'kit-cap' }, g, 'piston');
  }
  var st = h.el('text', { x: w / 2, y: H + 24, 'text-anchor': 'middle', 'class': 'kit-state' }, g);
  part.render = function (v) {
    var gs = v <= 1 ? h.clamp(v, 0, 1) : h.clamp(1 - (v - 1) * 2, 0, 1);
    var pl = v <= 1 ? h.clamp(v, 0, 1) : h.clamp(1 - (v - 1.5) * 2, 0, 1);
    var oi = h.clamp((v - 1.5) * 2, 0, 1);
    gas.style.opacity = gs.toFixed(2); pilot.style.opacity = pl.toFixed(2); oil.style.opacity = oi.toFixed(2);
    fire.style.opacity = Math.max(Math.min(gs, pl), oi).toFixed(2);
    g.classList.toggle('kit-cylinder-run', v > 0.05);
    g.classList.toggle('kit-cylinder-trip', v > 1.25 && v < 1.75);
    st.textContent = v < 0.05 ? 'STOPPED' : v <= 1.25 ? 'GAS MODE' : v < 1.75 ? 'GAS SUPPLY STOPPED' : 'FUEL-OIL MODE';
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M01",
  course: 'IGF Basic', module: 'M01', made: '2026-10-15',
  why: 'M01 s06: a dual-fuel engine cylinder in gas mode (gas jet lit by a pilot oil spray), on a gas trip, and in fuel-oil mode; M06 and M13 need it too',
  value: '0 stopped · 1 gas mode (gas jet + pilot spray) · 1.5 gas supply stopped (pilot only) · 2 fuel-oil mode (oil spray)',
  css: '.kit-cylinder-wall{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}.kit-cylinder-piston{fill:var(--steel);stroke:var(--dim-d);stroke-width:1.5}.kit-cylinder-ring{stroke:var(--deep);stroke-width:2}.kit-cylinder-rod{stroke:var(--faint-d);stroke-width:10}.kit-cylinder-inj{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}.kit-cylinder-gas line{stroke:var(--txt-d);stroke-width:3;stroke-linecap:round;stroke-dasharray:2 6}.kit-cylinder-pilot line,.kit-cylinder-oil line{stroke:var(--cold);stroke-width:2.5;stroke-dasharray:5 4}.kit-cylinder-fire{fill:var(--txt-d);stroke:var(--txt-d);stroke-width:2;opacity:0}.kit-cylinder-run .kit-cylinder-moving{animation:kit-cylinder-stroke .9s ease-in-out infinite alternate}.kit-cylinder-run .kit-cylinder-gas line,.kit-cylinder-run .kit-cylinder-pilot line,.kit-cylinder-run .kit-cylinder-oil line{animation:kit-flow .8s linear infinite}.kit-cylinder-run .kit-state{fill:var(--txt-d)}.kit-cylinder-trip .kit-state{fill:var(--warn-d)}@keyframes kit-cylinder-stroke{to{transform:translateY(34px)}}',
  example: { size: [420, 330], parts: [
    { id: 'C', type: 'cylinder', x: 140, y: 50, w: 140, h: 230 } ],
    steps: [ { title: 'Gas mode', play: [['C', 1, 900]] }, { title: 'Gas trip', play: [['C', 1.5, 900]] },
             { title: 'Fuel-oil mode', play: [['C', 2, 900]] } ] }
});
/* end kit-part */
/* kit-part: boil_off */
KIT.define('boil_off', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 260, ht = p.h || 150, ins = p.insulation || 12, lv = p.level != null ? p.level : 0.6;
  var iw = w - 2 * ins, ih = ht - 2 * ins, r = ih / 2, sy = ins + ih * (1 - lv), cid = fig.uid + '-' + p.id + '-bo';
  h.el('rect', { width: w, height: ht, rx: ht / 2, 'class': 'kit-boil-off-ins' }, g);
  h.el('rect', { x: ins, y: ins, width: iw, height: ih, rx: r }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  h.el('rect', { x: ins, y: ins, width: iw, height: ih, rx: r, 'class': 'kit-vessel' }, g);
  var inside = h.el('g', { 'clip-path': 'url(#' + cid + ')' }, g);
  h.el('rect', { x: ins, y: sy, width: iw, height: ins + ih - sy, 'class': 'kit-liquid' }, inside);
  h.el('line', { x1: ins, x2: ins + iw, y1: sy, y2: sy, 'class': 'kit-surface' }, inside);
  var bub = h.el('g', { 'class': 'kit-boil-off-bubbles' }, inside);
  [0.3, 0.42, 0.55, 0.66, 0.78].forEach(function (fx, i) {
    h.el('circle', { cx: ins + iw * fx, cy: ins + ih - 6, r: 3 + (i % 2), style: 'animation-delay:' + (-0.37 * i) + 's;--rise:' + (sy - (ins + ih - 6)).toFixed(0) + 'px' }, bub);
  });
  var heat = h.el('g', { 'class': 'kit-boil-off-heat' }, g);
  [[-30, ht / 2, 0], [w + 30, ht / 2, 180], [w * 0.38, ht + 30, -90], [w * 0.62, ht + 30, -90]].forEach(function (a) {
    var hg = h.el('g', { transform: 'translate(' + a[0] + ' ' + a[1] + ') rotate(' + a[2] + ')' }, heat);
    h.el('path', { d: 'M-14 0 q4 -5 8 0 t8 0 t8 0 M10 -6 L18 0 L10 6' }, hg);
  });
  var lx = ins + r * 0.75;                                 // clear of the rounded ends
  if (p.liquidLabel !== false) h.el('text', { x: lx, y: ins + ih - 18, 'class': 'kit-h' }, g, p.liquidLabel || 'LNG');
  if (p.vapourLabel !== false) h.el('text', { x: lx, y: ins + 26, 'class': 'kit-h' }, g, p.vapourLabel || 'vapour');
  if (p.heatLabel) h.el('text', { x: w * 0.5, y: ht + 58, 'text-anchor': 'middle', 'class': 'kit-cap' }, g, p.heatLabel);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    heat.style.opacity = k.toFixed(2); bub.style.opacity = k.toFixed(2);
    g.classList.toggle('kit-boil-off-on', k > 0.05);
  };
}, {
  family: 'cutaways',
  status: 'kit', merged_from: "IGF Basic M01",
  course: 'IGF Basic', module: 'M01', made: '2026-10-15',
  why: 'M01 s07: heat leaks through the insulation into a cold LNG tank and some of the liquid boils off as vapour',
  value: 'how much heat leaks in and boils the liquid, 0..1 (arrows and rising bubbles)',
  css: '.kit-boil-off-ins{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:4 3}.kit-boil-off-bubbles circle{fill:none;stroke:var(--txt-d);stroke-width:1.5}.kit-boil-off-heat path{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.kit-boil-off-on .kit-boil-off-bubbles circle{animation:kit-boil-off-rise 1.6s ease-in infinite}.kit-boil-off-on .kit-boil-off-heat g path{animation:kit-boil-off-in 1.2s ease-in-out infinite alternate}@keyframes kit-boil-off-rise{to{transform:translateY(var(--rise,-60px))}}@keyframes kit-boil-off-in{to{transform:translateX(6px)}}',
  example: { size: [360, 260], parts: [
    { id: 'B', type: 'boil_off', x: 50, y: 40, w: 260, h: 140, heatLabel: 'heat leaks in' } ],
    steps: [ { title: 'Heat leaks in and some LNG boils off', play: [['B', 1, 1500]] } ] }
});
/* end kit-part */
/* kit-part: zone */
KIT.define('zone', function (fig, part, g, p) {
  var h = KIT.h, z = p.zone != null ? p.zone : 1, round = p.r != null;
  var w = round ? p.r * 2 : (p.w || 80), ht = round ? p.r * 2 : (p.h || 60);
  var ox = p.from ? p.from[0] : w / 2, oy = p.from ? p.from[1] : ht / 2;
  var grow = h.el('g', {}, g);
  var at = round ? { cx: p.r, cy: p.r, r: p.r } : { width: w, height: ht, rx: p.rx != null ? p.rx : 6 };
  at['class'] = 'kit-zone-area kit-zone-z' + z;
  at['data-may-cross'] = '';                       // a zone reaches over walls and decks by its nature
  at['data-no-contain'] = '';
  h.el(round ? 'circle' : 'rect', at, grow);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    grow.setAttribute('transform', 'translate(' + ox + ' ' + oy + ') scale(' + Math.max(k, 0.001).toFixed(3) + ') translate(' + (-ox) + ' ' + (-oy) + ')');
    grow.style.opacity = k > 0.01 ? '1' : '0';
  };
}, {
  family: 'spaces',
  status: 'kit', merged_from: "IGF Basic M02",
  course: 'IGF Basic', module: 'M02', made: '2026-10-15',
  why: 'M02 s12: hazardous zones 0, 1 and 2 growing around tanks, spaces and openings on an IGF ship',
  value: 'how far the zone has grown from its origin, 0..1',
  css: '.kit-zone-area{stroke-width:2;stroke-dasharray:6 4}.kit-zone-z0{fill:var(--warn-d);fill-opacity:.38;stroke:var(--warn-d)}.kit-zone-z1{fill:var(--amber);fill-opacity:.3;stroke:var(--amber)}.kit-zone-z2{fill:var(--amber);fill-opacity:.1;stroke:var(--amber);stroke-dasharray:2 4}',
  example: { size: [320, 190], parts: [
    { id: 'Z2', type: 'zone', zone: 2, x: 100, y: 35, r: 60 },
    { id: 'Z1', type: 'zone', zone: 1, x: 130, y: 65, r: 30 },
    { id: 'Z0', type: 'zone', zone: 0, x: 150, y: 85, w: 20, h: 70, from: [10, 10] },
    { type: 'text', x: 160, y: 182, text: 'zones growing around a vent outlet' } ],
    steps: [ { title: 'Zone 0', play: [['Z0', 1, 600]] }, { title: 'Zone 1', play: [['Z1', 1, 700]] },
             { title: 'Zone 2', play: [['Z2', 1, 800]] } ] }
});
/* end kit-part */
/* kit-part: bands */
KIT.define('bands', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 520, rows = p.rows || [], rh = p.rowH || 72, cw = p.chip || 96, r = 15;
  var x0 = cw + 16, L = w - x0 - 2 * r - 14, top = p.axis ? 26 : 0;
  if (p.axis) h.el('text', { x: x0, y: 12, 'class': 'kit-tl' }, g, p.axis);
  var made = rows.map(function (row, k) {
    var gr = h.el('g', { transform: 'translate(0 ' + (top + k * rh) + ')', 'class': 'kit-bands-row' + (row.tone ? ' kit-bands-' + row.tone : '') }, g);
    h.el('rect', { width: cw, height: 34, rx: 8, 'class': 'kit-bands-chip' }, gr);
    h.el('text', { x: cw / 2, y: 22, 'text-anchor': 'middle', 'class': 'kit-h' }, gr, row.label || '');
    h.el('rect', { x: x0, y: 6, width: L, height: 22, rx: 4, 'class': 'kit-bands-track' }, gr);
    var segs = (row.gas || []).map(function (s) {
      return { s: s[0], e: s[1], n: h.el('rect', { x: x0 + 2 + s[0] * (L - 4), y: 8, width: 0, height: 18, 'class': 'kit-bands-gas' }, gr) };
    });
    var cur = h.el('line', { x1: x0 + 2, x2: x0 + 2, y1: 8, y2: 26, 'class': 'kit-bands-cursor' }, gr);
    var cx = w - r - 2;
    h.el('circle', { cx: cx, cy: 17, r: r, 'class': 'kit-bands-clock' }, gr);
    var pie = h.el('path', { 'class': 'kit-bands-pie' }, gr);
    if (row.caption) h.lines(gr, { x: x0 + L / 2, y: 50, 'text-anchor': 'middle', 'class': 'kit-cap' }, row.caption);
    return { segs: segs, cur: cur, pie: pie, cx: cx };
  });
  function sector(cx, f) {
    if (f <= 0.001) return 'M' + cx + ' 17';
    if (f >= 0.999) return 'M' + cx + ' 4 A13 13 0 1 1 ' + cx + ' 30 A13 13 0 1 1 ' + cx + ' 4 Z';
    var q = h.polar(13, -90 + 360 * f);
    return 'M' + cx + ' 17 L' + cx + ' 4 A13 13 0 ' + (f > 0.5 ? 1 : 0) + ' 1 ' + (cx + q[0]).toFixed(2) + ' ' + (17 + q[1]).toFixed(2) + ' Z';
  }
  part.render = function (v) {
    made.forEach(function (m, k) {
      var c = h.clamp(v - k, 0, 1), on = 0;
      m.segs.forEach(function (s) {
        var seen = h.clamp(c - s.s, 0, s.e - s.s);
        on += seen;
        s.n.setAttribute('width', (seen * (L - 4)).toFixed(1));
      });
      var cx = x0 + 2 + c * (L - 4);
      m.cur.setAttribute('x1', cx.toFixed(1)); m.cur.setAttribute('x2', cx.toFixed(1));
      m.cur.style.opacity = c > 0.001 && c < 0.999 ? '1' : '0';
      m.pie.setAttribute('d', sector(m.cx, on));
    });
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M02",
  course: 'IGF Basic', module: 'M02', made: '2026-10-15',
  why: 'M02 s11: zones 0, 1 and 2 told apart by how often and how long gas is present; the start of the Charts family M04 and M06 need',
  value: '0..number of rows - row k sweeps its time line while the value goes from k to k+1; its clock fills with the share of time gas is there',
  css: '.kit-bands-chip{fill:var(--deep);stroke:var(--faint-d);stroke-width:2}.kit-bands-track{fill:var(--deep);stroke:var(--faint-d);stroke-width:1.5}.kit-bands-gas{fill:var(--txt-d);opacity:.55}.kit-bands-cursor{stroke:var(--txt-d);stroke-width:2}.kit-bands-clock{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}.kit-bands-pie{fill:var(--dim-d)}.kit-bands-z0 .kit-bands-chip{stroke:var(--warn-d)}.kit-bands-z0 .kit-bands-gas,.kit-bands-z0 .kit-bands-pie{fill:var(--warn-d);opacity:.9}.kit-bands-z1 .kit-bands-chip{stroke:var(--amber)}.kit-bands-z1 .kit-bands-gas,.kit-bands-z1 .kit-bands-pie{fill:var(--amber);opacity:.9}.kit-bands-z2 .kit-bands-chip{stroke:var(--amber);stroke-dasharray:4 3}.kit-bands-z2 .kit-bands-gas,.kit-bands-z2 .kit-bands-pie{fill:var(--amber);opacity:.5}',
  example: { size: [420, 180], parts: [
    { id: 'B', type: 'bands', x: 10, y: 10, w: 400, axis: 'present - over time', rows: [
      { label: 'Often', caption: 'most of the time', gas: [[0, 0.8]] },
      { label: 'Rarely', caption: 'once, and short', gas: [[0.5, 0.56]] } ] } ],
    steps: [ { title: 'Row 1', play: [['B', 1, 2000, 0, 'linear']] }, { title: 'Row 2', play: [['B', 2, 2000, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: gas_cloud */
KIT.define('gas_cloud', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 200, ht = p.h || 120;
  var ox = p.from ? p.from[0] : w / 2, oy = p.from ? p.from[1] : ht * 0.6, fid = fig.uid + '-' + p.id + '-soft';
  h.el('feGaussianBlur', { stdDeviation: Math.max(4, Math.min(w, ht) * 0.05) },
       h.el('filter', { id: fid, x: '-20%', y: '-20%', width: '140%', height: '140%' }, h.el('defs', {}, g)));
  var grow = h.el('g', { filter: 'url(#' + fid + ')' }, g);
  [[0.5, 0.56, 0.34, 0.3], [0.29, 0.62, 0.21, 0.25], [0.71, 0.6, 0.23, 0.26], [0.42, 0.4, 0.22, 0.2], [0.61, 0.42, 0.2, 0.2]]
    .forEach(function (b, i) {
      h.el('ellipse', { cx: b[0] * w, cy: b[1] * ht, rx: b[2] * w, ry: b[3] * ht, 'class': 'kit-gas-cloud-puff',
                        'data-no-contain': '', 'data-may-overlap': '', style: 'animation-delay:' + (-0.7 * i) + 's' }, grow);
    });
  part.render = function (v) {
    var k = h.clamp(v, 0, 1), s = 0.2 + 0.8 * k;
    grow.setAttribute('transform', 'translate(' + ox + ' ' + oy + ') scale(' + s.toFixed(3) + ') translate(' + (-ox) + ' ' + (-oy) + ')');
    grow.style.opacity = k > 0.005 ? (0.45 + 0.55 * k).toFixed(2) : '0';
  };
  part.motion = function (d) { g.classList.toggle('kit-gas-cloud-spreading', d > 0); };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M02",
  course: 'IGF Basic', module: 'M02', made: '2026-10-15',
  why: 'M02 s15: leaked gas gathering in the tank connection space until the detectors alarm and the gas is shut off; M06 and M13 need it too',
  value: 'how much gas has gathered, 0..1 (the cloud grows from its leak point, pale - methane vapour has no colour)',
  css: '.kit-gas-cloud-puff{fill:var(--txt-d);opacity:.2;transform-box:fill-box;transform-origin:center}.kit-gas-cloud-spreading .kit-gas-cloud-puff{animation:kit-gas-cloud-drift 2.4s ease-in-out infinite alternate}@keyframes kit-gas-cloud-drift{to{transform:scale(1.06)}}',
  example: { size: [320, 190], parts: [
    { id: 'R', type: 'space', x: 20, y: 20, w: 280, h: 150, label: 'TANK CONNECTION SPACE' },
    { id: 'C', type: 'gas_cloud', x: 20, y: 20, w: 280, h: 150, from: [90, 110] } ],
    steps: [ { title: 'A leak: gas gathers', play: [['C', 1, 4000, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: integral_tank */
KIT.define('integral_tank', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 160, ht = p.h || 110, c = p.cofferdam != null ? p.cofferdam : 14;
  var tx = c, ty = c, tw = w - 2 * c, th = ht - c, cid = fig.uid + '-' + p.id + '-it';
  h.el('rect', { width: w, height: ht, rx: 3, 'class': 'kit-integral-tank-cd' }, g);
  h.el('rect', { x: tx, y: ty, width: tw, height: th }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  h.el('rect', { x: tx, y: ty, width: tw, height: th, 'class': 'kit-vessel' }, g);
  var liq = h.el('rect', { x: tx, width: tw, 'class': 'kit-liquid', 'clip-path': 'url(#' + cid + ')' }, g);
  var surf = h.el('line', { x1: tx, x2: tx + tw, 'class': 'kit-surface', 'clip-path': 'url(#' + cid + ')' }, g);
  h.el('rect', { x: -10, y: ht, width: w + 20, height: 8, 'class': 'kit-steel' }, g);
  if (p.label) h.el('text', { x: tx + 10, y: ty + 20, 'class': 'kit-sl' }, g, p.label);
  if (p.cofferdamLabel !== false) h.el('text', { x: w / 2, y: -8, 'text-anchor': 'middle', 'class': 'kit-cap' }, g, p.cofferdamLabel || 'cofferdam');
  if (p.hullLabel !== false) h.el('text', { x: w / 2, y: ht + 26, 'text-anchor': 'middle', 'class': 'kit-cap' }, g, p.hullLabel || 'hull');
  part.render = function (v) {
    var y = ty + th - h.clamp(v, 0, 1) * th;
    liq.setAttribute('y', y); liq.setAttribute('height', ty + th - y);
    surf.setAttribute('y1', y); surf.setAttribute('y2', y);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M02",
  course: 'IGF Basic', module: 'M02', made: '2026-10-15',
  why: 'M02 s05: the methanol path starts in an integral fuel tank - part of the hull, surrounded by a cofferdam',
  value: 'liquid level 0..1',
  css: '.kit-integral-tank-cd{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:5 4}',
  example: { size: [300, 220], parts: [
    { id: 'T', type: 'integral_tank', x: 70, y: 40, w: 160, h: 120, label: 'methanol', value: 0.7 } ],
    steps: [ { title: 'Fuel is drawn off', play: [['T', 0.45, 3000]] } ] }
});
/* end kit-part */
/* kit-parts: end */
