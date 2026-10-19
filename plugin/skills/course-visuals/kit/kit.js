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
  /* the line spacing is in em, so a label the kit sets larger (--kit-up, the 12.5 px floor) keeps its spacing:
     16 at the 12.5 px caption size, as before */
  function lines(parent, attrs, text, lh) {
    var t = el('text', attrs, parent), rows = String(text).split('\n');
    rows.forEach(function (s, i) {
      /* the rows are stacked, so their words never touch on screen - but a screen reader and the drawing audit read the
         text as one run: "HIGH PRESSURE" over "ALARM" came out "HIGH PRESSUREALARM". A space that is not drawn
         (display:none: it takes no width, so a centred row does not shift) is put between the rows (2.49.1) */
      if (i) el('tspan', { 'class': 'kit-sp', 'aria-hidden': 'true', style: 'display:none' }, t, ' ');
      el('tspan', { x: attrs.x || 0, dy: i ? ((lh || 16) / 12.5).toFixed(3) + 'em' : 0 }, t, s);
    });
    return rows.length;
  }
  /* a LABEL: words that belong to a part and may be moved by the layout (layout() below) to a place clear of every
     shape, line and other label - with a leader line back to the part when it had to go further than beside it.
       opt.inside  true: it stays inside the part (a room's name), clear of its edge
       opt.near    how far it may go without a leader (default: beside the part); opt.lead false: never a leader
       opt.fixed   true: it is never moved (it is still checked)
       opt.at      [x, y] in the part's own units: the place on the part the words name (a cylinder's "oil injector"). The
                   label is judged against that point, not the whole part: moved off it, it gets a leader from it - a
                   label pushed down a part's side by a neighbour no longer sits, with no line, beside the wrong feature
                   (M01 benchmark run 4, s06)
     Returns the label's group; more text may be added to it (a valve's state under its name). */
  function label(fig, g, attrs, text, opt) {
    var w = el('g', { 'class': 'kit-lbl' }, g), L = { g: w, part: g, opt: opt || {} };
    if (text != null && text !== '') lines(w, attrs, text, opt && opt.lh);
    w.__kitL = L;
    if (L.opt.within) (L.opt.within.__kitWithin = L.opt.within.__kitWithin || []).push(L);
    fig.labels.push(L);
    return w;
  }
  /* the width of the widest of these words in a text element as it is styled (restores what it said) */
  function widest(t, words) {
    var keep = t.textContent, w = 0;
    words.forEach(function (s) { t.textContent = s; w = Math.max(w, textWidth(t, 8.5)); });
    t.textContent = keep;
    return w;
  }
  /* what a scale's readout can show: its ends, its middle, its marks and its start */
  function readings(p, lo, hi, marks, v0) {
    var vs = [lo, hi, (lo + hi) / 2, v0].concat((marks || []).map(function (m) { return m.at; }));
    return vs.map(function (v) { return fmt(v, p); });
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
    /* "view": [x, y, w, h] shows a different window on the same canvas - a task page adds a band above and below
       the drawing for its empty label boxes (compile/task_pages.py); a deck never sets it */
    this.base = (spec.view && spec.view.length === 4 ? spec.view : [0, 0, size[0], size[1]]).map(Number);
    this.svg.setAttribute('viewBox', this.base.join(' '));
    this.svg.setAttribute('role', 'img');
    this.svg.setAttribute('data-motion', 'teaching');
    this.svg.setAttribute('data-fit', 'off');          // the kit fits its own frame (layout), gb_fit.js leaves it alone
    if (spec.label) this.svg.setAttribute('aria-label', spec.label);
    this.svg.classList.add('kit');
    this.parts = {}; this.list = []; this.handlers = {}; this.labels = []; this.fits = [];
    this.tweens = []; this.alarms = []; this.now = 0; this.n = 0; this.raf = 0; this.silent = false;
    this.report = null; this.laid = 0;
    this.theme();
    (spec.parts || []).forEach(function (p) { self.add(p); });
    ghosts(this, true);
    this.clearState();
    watch(this);
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
      var g = el('g', { 'class': 'kit-part kit-part-' + p.type, transform: 'translate(' + (p.x || 0) + ' ' + (p.y || 0) + ')',
                        'data-kit-id': p.id || null }, this.svg);
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
      if (!this.tweens.length && this.later && !this.silent) { this.later = false; var me = this; setTimeout(function () { me.layout(true); }, 0); }
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
      if (!this.laying) {
        this.emit('step', n);
        if (!this.laid) this.layout();               // the first time it is on screen
      }
    },
    next: function () { if (this.n < this.steps()) this.go(this.n + 1); },
    prev: function () { if (this.n > 0) this.go(this.n - 1, true); },
    replay: function () { this.go(this.n); },
    /* a part's box that holds words is sized to them at layout time, when the words have their real width */
    fit: function (fn, late) { if (late) fn.late = true; this.fits.push(fn); },

    /* the figure's colours follow what it is drawn on (theme() below) */
    theme: function () { return theme(this); },
    /* lay the figure out for the size it is shown at now: the 12.5 px floor, boxes sized to their words, every label
       clear, the frame filled. Runs by itself the first time the figure is on screen and whenever its size changes;
       returns what it did (fig.report) - the figure studio and audit_drawing.js read it. */
    layout: function (force) {
      var svg = this.svg, r = svg.getBoundingClientRect ? svg.getBoundingClientRect() : null;
      if (!r || r.width < 2 || r.height < 2 || this.laying) return this.report;
      if (!force && this.laid && Math.abs(r.width - this.laid) < 1) return this.report;
      if (this.raf) { this.later = true; return this.report; }     // after the step that is playing
      var n0 = this.n, rep, kept = this.list.map(function (part) { return part.v; });
      this.laying = true;
      try { ghosts(this, false); rep = lay(this); }
      catch (err) { rep = { error: String((err && err.message) || err) }; if (root.console) console.error(err); }
      finally {
        ghosts(this, true);
        try { this.go(n0, true); } catch (e2) { /* the figure stays where the layout left it */ }
        /* going back to step n0 rebuilds the values from the steps: a value set from outside the steps (a task page's panel
           valve turned to "closed", gb_answer.js kitSet) was lost when a layout ran after it - at random, as a font arrived or
           the window changed size. What was shown before the layout is shown after it. */
        var self2 = this;
        this.list.forEach(function (part, i) {
          if (part.v !== kept[i] && !part.p.source) { part.v = kept[i]; self2.paint(part); }
        });
        this.laying = false;
      }
      this.laid = svg.getBoundingClientRect().width || r.width;
      this.report = rep;
      /* a task page lays its tap areas on the drawn parts (gb_answer.js placeParts, on "resize"): tell it they may have moved */
      if (svg.hasAttribute('data-kit-still') && root.dispatchEvent) {
        setTimeout(function () { try { root.dispatchEvent(new Event('resize')); } catch (e) { /* an old WebView */ } }, 0);
      }
      if (rep && rep.unplaced && rep.unplaced.length && root.console) {
        console.warn('kit: ' + rep.unplaced.length + ' label(s) found no clear place in ' + (this.svg.id || this.spec.label || 'a figure') +
                     ': ' + rep.unplaced.map(function (u) { return '"' + u.text + '"'; }).join(', '));
      }
      return rep;
    }
  };

  /* ==========================================================================
     LAYOUT (2.48.0) - the drawing work the kit does by itself, so no build sheet places a label by hand
       THEME   the parts' colours come from the course tokens through a dark or a light mapping (kit.css), chosen by
               what the figure is drawn on: a deck's dark panel (a task page's too, 2.46.0), a light page - so every word and line
               keeps its contrast on either, by construction (audit_drawing.js CONTRAST stays as the safety net)
       FLOOR   no word is drawn under 12.5 px: shown smaller than 1:1, every kit type class grows by 1/scale
               (--kit-up, at most UP_MAX), and the layout makes room for it
       FIT     a box that holds words (a readout, an alarm row) is as wide as its widest words
       LABELS  every label (KIT.h.label) gets a place clear of every shape, line and other label and its own box's
               edge (4 px, L54) - beside its part if it can, further out with a leader line if it must
       FRAME   a drawing that reaches past its frame makes the frame larger; one lost in its frame is zoomed in to
               fill it (L53, at most ZOOM_MAX; never with "view", an inset photo over it, or "fit": false)
     Measured on the drawing as it is on screen, at the end of every step, so a part that only shows later is
     never covered either.
     ========================================================================== */
  var FIGS = [], UP_MAX = 2, ZOOM_MAX = 1.5, GROW_MAX = 1.3, FLOOR_PX = 12.5, PAD_PX = 4.5, CELL = 2;
  var GEOM = 'rect, circle, ellipse, line, polyline, polygon, path, text, image';
  var NOT_DRAWN = 'defs, symbol, clipPath, mask, marker, pattern';

  function rgba(s) {
    var m = /rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+%?))?\s*\)/.exec(s || '');
    if (!m) return null;
    var a = m[4] === undefined ? 1 : (/%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
    return [+m[1], +m[2], +m[3], a];
  }
  function luminance(c) {
    function lin(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  }
  /* "light" or "dark": the spec's "theme", a data-kit-theme above the figure, a deck's figure panel or dark slide -
     else the colour actually behind the figure */
  function theme(f) {
    var t = f.spec.theme, n, svg = f.svg;
    for (n = svg; !t && n && n.nodeType === 1; n = n.parentElement) t = n.getAttribute('data-kit-theme');
    if (t !== 'light' && t !== 'dark') {
      t = null;
      for (n = svg; !t && n && n.nodeType === 1; n = n.parentElement) {
        if (n.classList && (n.classList.contains('kit-screen') || (n.classList.contains('slide') && n.classList.contains('dark')))) t = 'dark';
      }
      if (!t) {
        var chain = [], base = [255, 255, 255, 1], c, i;
        for (n = svg; n && n.nodeType === 1; n = n.parentElement) {
          try { c = rgba(getComputedStyle(n).backgroundColor); } catch (e) { c = null; }
          if (c && c[3] > 0.02) { chain.push(c); if (c[3] >= 0.99) break; }
        }
        for (i = chain.length - 1; i >= 0; i--) {
          var a = chain[i][3];
          base = [chain[i][0] * a + base[0] * (1 - a), chain[i][1] * a + base[1] * (1 - a), chain[i][2] * a + base[2] * (1 - a), 1];
        }
        t = luminance(base) > 0.35 ? 'light' : 'dark';
      }
    }
    svg.classList.toggle('kit-light', t === 'light');
    svg.classList.toggle('kit-dark', t !== 'light');
    f.tone = t;
    return t;
  }

  function watch(f) {
    FIGS.push(f);
    if (root.ResizeObserver) {
      /* after the notification, never inside it: the layout may change the drawing's height, and a change made inside
         a ResizeObserver callback is reported as a script error ("loop completed with undelivered notifications") */
      try { new root.ResizeObserver(function () { setTimeout(function () { f.layout(); }, 0); }).observe(f.svg); }
      catch (e) { /* laid out on its first step */ }
    }
  }
  /* A WINDOW RESIZE lays the figures out too (2.49.2, F4). The ResizeObserver does it in a browser with frames; a probe that
     measures a slide the moment it is shown (audit_deck.js fires "resize" for exactly that and waits) gets no observer call in
     a hidden browser, so a figure with a photo "over" it - which is not zoomed to fill its panel, so it is shown below 1:1 -
     kept its words at 12.5 px declared and the audit reported them smaller (svgSmall). A figure whose width has not changed
     since its last layout is left as it is. */
  if (root.addEventListener) {
    root.addEventListener('resize', function () {
      FIGS.forEach(function (f) { try { f.layout(); } catch (e) { /* the observer or the next resize tries again */ } });
    });
  }
  if (document.fonts && document.fonts.addEventListener) {          // the course font arrives: the words have their real width
    document.fonts.addEventListener('loadingdone', function () { FIGS.forEach(function (f) { if (f.laid) f.layout(true); }); });
  }

  function q(rootEl, sel) { return Array.prototype.slice.call(rootEl.querySelectorAll(sel)); }
  function tagOf(n) { return (n.tagName || '').toLowerCase(); }
  function notDrawn(n, svg) {
    for (var p = n.parentNode; p && p !== svg; p = p.parentNode) if (p.matches && p.matches(NOT_DRAWN)) return true;
    return false;
  }
  function flagged(n, attr, svg) {
    for (var p = n; p && p !== svg; p = p.parentNode) if (p.hasAttribute && p.hasAttribute(attr)) return true;
    return false;
  }
  function seen(n, svg) {                       // painted now: laid out, and not faded out by its step
    var o = 1;
    for (var p = n; p && p.nodeType === 1; p = p.parentElement) {
      var cs = getComputedStyle(p);
      if (cs.display === 'none' || cs.visibility === 'hidden') return false;
      if (p === svg) break;
      o *= parseFloat(cs.opacity);
      if (!(o > 0.05)) return false;
    }
    return true;
  }
  function painted(n) {
    var cs = getComputedStyle(n), t = tagOf(n);
    function on(v, op) { return v && v !== 'none' && v !== 'transparent' && !/rgba\([^)]*,\s*0\)$/.test(v) && !(parseFloat(op) <= 0.05); }
    return t === 'text' || t === 'image' || on(cs.fill, cs.fillOpacity) || (on(cs.stroke, cs.strokeOpacity) && parseFloat(cs.strokeWidth) > 0);
  }
  function labelOf(n, svg) {
    for (var p = n; p && p !== svg; p = p.parentNode) if (p.__kitL) return p.__kitL;
    return null;
  }
  function partOf(n, svg) {
    for (var p = n; p && p !== svg; p = p.parentNode) if (p.classList && p.classList.contains('kit-part')) return p;
    return null;
  }
  function det(M) { return Math.sqrt(Math.abs(M.a * M.d - M.b * M.c)) || 1; }
  function onto(M, x, y) { return { x: M.a * x + M.c * y + M.e, y: M.b * x + M.d * y + M.f }; }
  function boxOf(pts) {
    var b = { x: 1e9, y: 1e9, x2: -1e9, y2: -1e9 };
    pts.forEach(function (p) { b.x = Math.min(b.x, p.x); b.y = Math.min(b.y, p.y); b.x2 = Math.max(b.x2, p.x); b.y2 = Math.max(b.y2, p.y); });
    return b;
  }
  function join(a, b) {
    if (!a) return b ? { x: b.x, y: b.y, x2: b.x2, y2: b.y2 } : null;
    if (!b) return a;
    return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), x2: Math.max(a.x2, b.x2), y2: Math.max(a.y2, b.y2) };
  }
  function grown(b, d) { return { x: b.x - d, y: b.y - d, x2: b.x2 + d, y2: b.y2 + d }; }
  function meets(a, b) { return a.x < b.x2 && b.x < a.x2 && a.y < b.y2 && b.y < a.y2; }
  function gapOf(a, b) {
    var dx = Math.max(0, b.x - a.x2, a.x - b.x2), dy = Math.max(0, b.y - a.y2, a.y - b.y2);
    return Math.sqrt(dx * dx + dy * dy);
  }
  /* a label's words as the drawing audit judges them: the letters, the middle three-quarters of the line box */
  function textBox(t, M) {
    var b;
    try { b = t.getBBox(); } catch (e) { return null; }
    if (!b || (!b.width && !b.height)) return null;
    var y = b.y + 0.18 * b.height, h = 0.74 * b.height;
    return boxOf([onto(M, b.x, y), onto(M, b.x + b.width, y), onto(M, b.x, y + h), onto(M, b.x + b.width, y + h)]);
  }
  function outline(n, M) {
    var pts = [], L = 0, i;
    try { L = n.getTotalLength(); } catch (e) { L = 0; }
    if (L > 0) {
      var N = Math.max(8, Math.min(1500, Math.ceil(L * det(M) / CELL)));
      for (i = 0; i <= N; i++) { var a = n.getPointAtLength(L * i / N); pts.push(onto(M, a.x, a.y)); }
      return pts;
    }
    try {
      var b = n.getBBox();
      if (b.width || b.height) {
        [[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0], [1, 0.5], [0.5, 1], [0, 0.5]].forEach(function (k) {
          pts.push(onto(M, b.x + k[0] * b.width, b.y + k[1] * b.height));
        });
      }
    } catch (e2) { /* nothing to measure */ }
    return pts;
  }
  function geomKey(n, M) {
    var s = [M.a, M.b, M.c, M.d, M.e, M.f].map(function (v) { return v.toFixed(2); }).join(',');
    ['d', 'x', 'y', 'width', 'height', 'cx', 'cy', 'r', 'rx', 'ry', 'x1', 'y1', 'x2', 'y2', 'points'].forEach(function (k) {
      var v = n.getAttribute(k);
      if (v != null) s += '|' + v;
    });
    return s;
  }

  /* everything drawn, at the end of every step: the obstacles (outlines, and the words that are not labels), each
     label's box, each part's outline (where a leader goes), the whole drawing's box, the smallest word on screen */
  function gather(f, states) {
    var svg = f.svg, G = { obs: [], body: null, parts: [], minPx: 1e9, seenKeys: {}, scale: 1 };
    /* measured where their parts put them: a move from an earlier round is taken off first (else a second round - after a
       zoom - read the moved place as the label's own and left it on the line it had been moved off) */
    f.labels.forEach(function (L) { L.box = null; L.seen = false; L.within = null; L.g.removeAttribute('transform'); });
    var oldLeaders = svg.querySelector('g.kit-leaders');
    if (oldLeaders) oldLeaders.parentNode.removeChild(oldLeaders);
    q(svg, '.kit-part').forEach(function (p) { p.__kitBox = null; p.__kitPts = null; });
    states.forEach(function (k) {
      if (states.length > 1 || k !== f.n) f.go(k, true);
      var ctm = svg.getScreenCTM();
      if (!ctm) return;
      var inv = ctm.inverse(), s = det(ctm);
      G.scale = s;
      q(svg, GEOM).forEach(function (n, idx) {
        if (notDrawn(n, svg) || !seen(n, svg) || !painted(n)) return;
        var sc = n.getScreenCTM();
        if (!sc) return;
        var M = inv.multiply(sc), t = tagOf(n), L = labelOf(n, svg), part = partOf(n, svg), b, key;
        if (t === 'text') {
          b = textBox(n, M);
          if (!b) return;
          G.minPx = Math.min(G.minPx, parseFloat(getComputedStyle(n).fontSize) * det(M) * s);
          if (L) { L.box = join(L.box, b); L.seen = true; return; }
          G.body = join(G.body, b);
          key = idx + 't' + b.x.toFixed(1) + ',' + b.y.toFixed(1) + ',' + b.x2.toFixed(1);
          if (G.seenKeys[key]) return;
          G.seenKeys[key] = 1;
          if (!flagged(n, 'data-may-overlap', svg)) G.obs.push({ rect: b });
          if (part) { part.__kitBox = join(part.__kitBox, b); }
          return;
        }
        if (n.__kitWithin) {                       // the box a label keeps inside (opt.within)
          try { var wb = n.getBBox(); n.__kitWithin.forEach(function (L2) { L2.within = boxOf([onto(M, wb.x, wb.y), onto(M, wb.x + wb.width, wb.y + wb.height)]); }); }
          catch (e3) { /* not drawn */ }
        }
        if (L || t === 'image') {
          if (t === 'image') { try { var ib = n.getBBox(); G.body = join(G.body, boxOf([onto(M, ib.x, ib.y), onto(M, ib.x + ib.width, ib.y + ib.height)])); } catch (e) { /* none */ } }
          return;
        }
        key = idx + '|' + geomKey(n, M);
        var cs = getComputedStyle(n), sw = parseFloat(cs.strokeWidth) || 0;
        var r = (cs.stroke && cs.stroke !== 'none' && sw > 0 ? sw / 2 * det(M) : 0) + 0.5;
        var known = G.seenKeys[key];
        var pts = known ? known.pts : outline(n, M);
        if (!pts.length) return;
        var pb = grown(boxOf(pts), r);
        G.body = join(G.body, pb);
        if (known) return;
        G.seenKeys[key] = { pts: pts };
        if (!flagged(n, 'data-may-overlap', svg)) G.obs.push({ pts: pts, r: r });
        if (part) {
          part.__kitBox = join(part.__kitBox, pb);
          part.__kitPts = (part.__kitPts || []).concat(pts.filter(function (p, i) { return i % 3 === 0; }));
          if (G.parts.indexOf(part) < 0) G.parts.push(part);
        }
      });
    });
    return G;
  }

  /* the occupied cells of the drawing, CELL units square, with a summed table for "is this box clear?" in one look */
  function Grid(V) {
    var cols = Math.ceil(V[2] / CELL) + 2, rows = Math.ceil(V[3] / CELL) + 2, occ = new Uint8Array(cols * rows), sat = null;
    function ci(x) { return Math.max(0, Math.min(cols - 1, Math.floor((x - V[0]) / CELL))); }
    function ri(y) { return Math.max(0, Math.min(rows - 1, Math.floor((y - V[1]) / CELL))); }
    return {
      mark: function (x0, y0, x1, y1) {
        var c0 = ci(x0), c1 = ci(x1), r0 = ri(y0), r1 = ri(y1), r, c;
        for (r = r0; r <= r1; r++) for (c = c0; c <= c1; c++) occ[r * cols + c] = 1;
      },
      done: function () {
        sat = new Int32Array((cols + 1) * (rows + 1));
        for (var r = 0; r < rows; r++) {
          var run = 0;
          for (var c = 0; c < cols; c++) { run += occ[r * cols + c]; sat[(r + 1) * (cols + 1) + c + 1] = sat[r * (cols + 1) + c + 1] + run; }
        }
      },
      sum: function (b) {
        var c0 = ci(b.x), c1 = ci(b.x2), r0 = ri(b.y), r1 = ri(b.y2), W = cols + 1;
        return sat[(r1 + 1) * W + c1 + 1] - sat[r0 * W + c1 + 1] - sat[(r1 + 1) * W + c0] + sat[r0 * W + c0];
      },
      at: function (x, y) { return occ[ri(y) * cols + ci(x)]; }
    };
  }

  function nearestOn(pts, x, y) {
    var best = null, d = 1e18;
    (pts || []).forEach(function (p) { var e = (p.x - x) * (p.x - x) + (p.y - y) * (p.y - y); if (e < d) { d = e; best = p; } });
    return best;
  }
  function edgePoint(b, x, y) { return { x: Math.max(b.x, Math.min(b.x2, x)), y: Math.max(b.y, Math.min(b.y2, y)) }; }

  /* SOLVE - every label a clear place, in plain numbers, with no SVG in it: a 3D figure's projected outlines take the
     same solver for their label overlays (KIT.solveLabels).
       obs     [{rect: {x, y, x2, y2}} | {pts: [{x, y}], r}]   what is drawn: words' boxes, outlines (points, half width)
       labels  [{box, anchor, pts, within, opt}]                a label's box where its part put it, the part's box and
                                                               outline points (where a leader ends), opt as h.label's
       V       [x, y, w, h] the frame; P the clearance (L54's 4 px, in these units)
     -> { at: [box], leader: [{x1, y1, x2, y2} | null], unplaced: [index], moved, leaders }
     Those already clear stay; the others, largest first, take the nearest clear place - beside the part, else further
     out with a leader line that crosses no other label. */
  function solveLabels(obs, labs, V, P) {
    var grid = Grid(V), bounds = { x: V[0] + P, y: V[1] + P, x2: V[0] + V[2] - P, y2: V[1] + V[3] - P };
    var q2 = CELL / 2;                         // half a cell more all round: the grid never lets a label in closer than P
    obs.forEach(function (o) {
      if (o.rect) { grid.mark(o.rect.x - q2, o.rect.y - q2, o.rect.x2 + q2, o.rect.y2 + q2); return; }
      var r = o.r + q2;
      o.pts.forEach(function (p) { grid.mark(p.x - r, p.y - r, p.x + r, p.y + r); });
    });
    grid.done();
    var taken = [], out = { at: [], leader: [], unplaced: [], moved: 0, leaders: 0 };
    labs.forEach(function (L) { L.opt = L.opt || {}; L.anchor = L.anchor || L.box; L.at = null; L.leader = null; });
    function inBounds(b) { return b.x >= bounds.x && b.y >= bounds.y && b.x2 <= bounds.x2 && b.y2 <= bounds.y2; }
    /* the grid is coarse (a cell, plus half a cell round every obstacle): words inside a low room (a bilge 28 high) are
       allowed one cell closer to its walls - still clear of them, and audit_drawing.js judges the true 4 px */
    function clear(b, inside) {
      var pad = inside ? Math.max(1, P - CELL) : P;
      if (!inBounds(b) || grid.sum(grown(b, pad)) > 0) return false;
      for (var i = 0; i < taken.length; i++) if (meets(grown(taken[i], P), b)) return false;
      return true;
    }
    var todo = [];
    labs.forEach(function (L) {
      if (L.opt.fixed || clear(L.box, L.opt.inside)) { L.at = L.box; taken.push(L.box); } else todo.push(L);
    });
    /* a callout where it was put still gets its leader to the place it names */
    labs.forEach(function (L) {
      if (!L.opt.callout || L.at !== L.box || gapOf(L.box, L.anchor) <= (L.opt.near || 0) + P) return;
      taken.splice(taken.indexOf(L.box), 1);
      var ln = leaderFor(L, L.box);
      taken.push(L.box);
      if (ln) { L.leader = ln; out.leaders++; }
    });
    todo.sort(function (a, b) { return (b.box.x2 - b.box.x) * (b.box.y2 - b.box.y) - (a.box.x2 - a.box.x) * (a.box.y2 - a.box.y); });
    todo.forEach(function (L) {
      var best = search(L);
      if (best) { L.at = best.box; L.leader = best.leader; out.moved++; if (best.leader) out.leaders++; }
      else { L.at = L.box; out.unplaced.push(labs.indexOf(L)); }
      taken.push(L.at);
    });
    function search(L) {
      var b = L.box, w = b.x2 - b.x, h = b.y2 - b.y, cx0 = (b.x + b.x2) / 2, cy0 = (b.y + b.y2) / 2, A = L.anchor;
      var inside = !!L.opt.inside, lead = !inside && L.opt.lead !== false, near = L.opt.near != null ? L.opt.near : 8;
      var C = inside ? (L.within || A) : null, R = inside ? 0 : (lead ? 160 : near + P), st = inside ? 2 : 4, best = null;
      var x0 = inside ? C.x : A.x - R - w, x1 = inside ? C.x2 - w : A.x2 + R, y0 = inside ? C.y : A.y - R - h, y1 = inside ? C.y2 - h : A.y2 + R;
      var selfA = L.opt.self || meets(b, A);
      for (var y = y0; y <= y1; y += st) {
        for (var x = x0; x <= x1; x += st) {
          var c = { x: x, y: y, x2: x + w, y2: y + h };
          if (!selfA && meets(c, A)) continue;
          var d = Math.sqrt((x + w / 2 - cx0) * (x + w / 2 - cx0) + (y + h / 2 - cy0) * (y + h / 2 - cy0));
          if (best && d >= best.cost) continue;
          if (!clear(c, inside)) continue;
          var cost = d, ln = null;
          /* a label naming a point (opt.at) may be nudged (near) from its own place, or sit beside the point, with no line */
          if (!inside && !L.opt.self && gapOf(c, A) > near + P && !(L.opt.at && Math.sqrt((x - b.x) * (x - b.x) + (y - b.y) * (y - b.y)) <= near)) {
            if (!lead) continue;
            ln = leaderFor(L, c);
            if (!ln) continue;
            cost += 24 + ln.cost;
          }
          if (!best || cost < best.cost) best = { box: c, leader: ln, cost: cost };
        }
      }
      return best;
    }
    /* from the part's own outline to the label's nearest edge; never through another label, a crossed line costs */
    function leaderFor(L, c) {
      var cx = (c.x + c.x2) / 2, cy = (c.y + c.y2) / 2;
      var a = nearestOn(L.pts, cx, cy) || edgePoint(L.anchor, cx, cy);
      var e = edgePoint(grown(c, P * 0.5), a.x, a.y), dx = e.x - a.x, dy = e.y - a.y, len = Math.sqrt(dx * dx + dy * dy);
      if (len < 4) return null;
      var hits = 0, n = Math.ceil(len / CELL);
      for (var i = 0; i <= n; i++) {
        var px = a.x + dx * i / n, py = a.y + dy * i / n, from = len * i / n;
        for (var j = 0; j < taken.length; j++) {
          var t = grown(taken[j], P * 0.5);
          if (px > t.x && px < t.x2 && py > t.y && py < t.y2) return null;
        }
        if (from > 5 && len - from > 3 && grid.at(px, py)) hits++;
      }
      return { x1: a.x, y1: a.y, x2: e.x, y2: e.y, cost: hits * 3 + len * 0.15 };
    }
    labs.forEach(function (L) { out.at.push(L.at); out.leader.push(L.leader); });
    return out;
  }

  /* PLACE - the solver's answer laid on the figure: each label's group moved, its leader drawn */
  function place(f, G, V, P) {
    var svg = f.svg;
    f.labels.forEach(function (L) { L.g.removeAttribute('transform'); L.at = null; L.leader = null; });
    var old = svg.querySelector('g.kit-leaders');
    if (old) old.parentNode.removeChild(old);
    var labs = f.labels.filter(function (L) { return L.seen && L.box; });
    var sm0 = svg.getScreenCTM(), inv0 = sm0 && sm0.inverse();
    var input = labs.map(function (L) {
      var A = (L.part && L.part.__kitBox) || L.box, pts = L.part && L.part.__kitPts;
      var pm = L.opt.at && inv0 && L.g.parentNode.getScreenCTM();
      if (pm) {                              // opt.at: judged against the point it names, a leader starts there
        var pt = onto(inv0.multiply(pm), +L.opt.at[0], +L.opt.at[1]);
        A = { x: pt.x - 1, y: pt.y - 1, x2: pt.x + 1, y2: pt.y + 1 };
        pts = [pt];
      }
      return { box: L.box, anchor: A, pts: pts, within: L.within, opt: L.opt };
    });
    var res = solveLabels(G.obs, input, V, P), out = { moved: res.moved, leaders: res.leaders, unplaced: [] };
    labs.forEach(function (L, i) { L.at = res.at[i]; L.leader = res.leader[i]; });
    res.unplaced.forEach(function (i) {
      var L = labs[i], owner = partOf(L.g, svg);
      out.unplaced.push({ text: (L.g.textContent || '').replace(/\s+/g, ' ').trim(), part: (owner && owner.getAttribute('data-kit-id')) || '' });
    });
    var lg = null;
    labs.forEach(function (L) {
      if (!L.at) return;
      if (L.at !== L.box) {
        var dx = L.at.x - L.box.x, dy = L.at.y - L.box.y, pm = L.g.parentNode.getScreenCTM(), sm = svg.getScreenCTM();
        if (pm && sm) {                         // the move in the label's own units (its part may be scaled)
          var k = det(sm) / det(pm);
          dx *= k; dy *= k;
        }
        L.g.setAttribute('transform', 'translate(' + dx.toFixed(2) + ' ' + dy.toFixed(2) + ')');
      }
      if (L.leader) {
        if (!lg) lg = el('g', { 'class': 'kit-leaders', 'aria-hidden': 'true' }, svg);
        L.g.__kitLeader = el('line', { x1: L.leader.x1.toFixed(1), y1: L.leader.y1.toFixed(1), x2: L.leader.x2.toFixed(1), y2: L.leader.y2.toFixed(1),
                                       'class': 'kit-leader', 'data-may-cross': '' }, lg);
        if (L.g.__kitFade != null) L.g.__kitLeader.style.opacity = L.g.__kitFade;      // a revealed callout's leader fades with it
      }
    });
    out.labels = labs.length;
    return out;
  }

  /* GHOST (2.50.4) - spec.ghost: [part ids] whose words a task takes off ("unlabel": "answers" or a list, task_pages.py).
     They are laid out like every other label, so the words left stand exactly where the deck has them, and are hidden
     after every layout: a `text` part whole, any other part's labels and their leader lines. Taking the words out of the
     spec instead re-laid the rest, and a label could land beside the wrong space (M01 benchmark run 4, q01 / q03). */
  function ghosts(f, hide) {
    var ids = f.spec.ghost;
    if (!ids || !ids.length) return;
    q(f.svg, '.kit-part').forEach(function (p) {
      if (ids.indexOf(p.getAttribute('data-kit-id')) < 0) return;
      var lbls = q(p, '.kit-lbl'), d = hide ? 'none' : '';
      if (p.classList.contains('kit-part-text')) p.style.display = d;
      else lbls.forEach(function (n) { n.style.display = d; });
      lbls.forEach(function (n) { if (n.__kitLeader) n.__kitLeader.style.display = d; });
    });
  }

  function setView(svg, V) { svg.setAttribute('viewBox', V.map(function (v) { return +v.toFixed(2); }).join(' ')); }
  function scaleNow(svg) { var m = svg.getScreenCTM(); return m ? det(m) : 1; }
  /* 0.1 % over 1/s: a word grown to exactly 12.5 px once drawn read 12.4999 to the deck audit's svgSmall, which compares
     declared x rendered width / viewBox width against 12.5 (2.49.2) */
  function upFor(s) { return Math.min(UP_MAX, Math.max(1, 1.001 / s)); }
  /* the height a deck figure may take: its column, less the step buttons (0 when it is not in a deck's figure column) */
  function roomPx(svg) {
    var col = svg.closest && svg.closest('.kit-fig');
    if (!col) return 0;
    var bar = col.querySelector('.mediabar'), scr = svg.closest('.kit-screen'), cs = scr ? getComputedStyle(scr) : null;
    var pad = cs ? (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0) : 0;
    return col.clientHeight - (bar ? bar.getBoundingClientRect().height + 14 : 0) - pad;
  }
  /* the frame made larger to hold B with a margin. Only taller, when the drawing needs height alone and its column has
     the room (so it is not shown smaller); else keeping its shape */
  function holding(V, B, m, svg) {
    var x0 = Math.min(V[0], B.x - m), y0 = Math.min(V[1], B.y - m), x1 = Math.max(V[0] + V[2], B.x2 + m), y1 = Math.max(V[1] + V[3], B.y2 + m);
    var w = x1 - x0, h = y1 - y0, a = V[2] / V[3];
    if (svg && w <= V[2] + 0.5) {
      var r = svg.getBoundingClientRect(), room = roomPx(svg);
      if (room > 0 && r.width * h / V[2] <= room) return [V[0], y0, V[2], h];
    }
    if (w / h > a) { var h2 = w / a; y0 -= (h2 - h) / 2; h = h2; } else { var w2 = h * a; x0 -= (w2 - w) / 2; w = w2; }
    return [x0, y0, w, h];
  }

  function lay(f) {
    var svg = f.svg, steps = f.steps(), states = [], k, i;
    for (k = 0; k <= steps; k++) states.push(k);
    /* a still figure on a task page keeps its frame: the page lays its tap areas, label boxes and leader lines on it in
       % of that frame (task_pages.py, gb_answer.js) */
    var still = svg.hasAttribute('data-kit-step') || svg.hasAttribute('data-kit-still');
    var zoomOK = !(still || f.spec.view || f.spec.fit === false ||
                   (svg.parentNode && svg.parentNode.querySelector && svg.parentNode.querySelector('.inset.over')));
    f.theme();
    var V = f.base.slice();
    setView(svg, V);
    function upTo(u) {                    // the words' size, then every box sized to them, then the frames that hold boxes
      f.upNow = u;
      svg.style.setProperty('--kit-up', u.toFixed(3));
      f.fits.forEach(function (fit) { if (!fit.late) fit(u); });
      f.fits.forEach(function (fit) { if (fit.late) fit(u); });
    }
    var s = scaleNow(svg), up = upFor(s);
    upTo(up);
    f.labels.forEach(function (L) { L.g.removeAttribute('transform'); });
    var G = gather(f, states);
    /* a drawing that reaches past its frame: the frame grows to hold it (keeping its shape) */
    function holds(B) { return B.x >= V[0] - 0.5 && B.y >= V[1] - 0.5 && B.x2 <= V[0] + V[2] + 0.5 && B.y2 <= V[1] + V[3] + 0.5; }
    /* words grown for the floor grow their boxes, which may need a larger frame, which shows everything smaller:
       a few rounds settle it */
    var crowded = false;
    function contain(extra) {
      for (var r = 0; r < 6 && !still; r++) {
        var B = join(G.body, extra);
        if (!B || holds(B)) return;
        V = holding(V, B, 3, f.spec.view ? null : svg);
        setView(svg, V);
        s = scaleNow(svg);
        /* words that need more room than the panel gives would grow the frame, which shows them smaller, which grows
           them again: past GROW_MAX the words stop growing (the drawing audit's SMALL TEXT then says so) */
        if (V[2] > f.base[2] * GROW_MAX) crowded = true;
        var up2 = upFor(s);
        if (!crowded && Math.abs(up2 - up) >= 0.01) { up = up2; upTo(up); }
        G = gather(f, states);
        extra = null;
      }
    }
    contain(null);
    var P = PAD_PX / s, res = place(f, G, V, P), zoom = 1;
    /* a label with no clear place inside the frame: the frame grows to give it one (gb_fit.js did this for every drawing) */
    var lost = null;
    f.labels.forEach(function (L) { if (L.at && L.at === L.box && L.seen && !holds(grown(L.box, P))) lost = join(lost, grown(L.box, P)); });
    if (lost) {
      contain(lost);
      P = PAD_PX / s;
      res = place(f, G, V, P);
    }
    /* a drawing lost in its frame is zoomed in to fill it (L53) */
    if (zoomOK && G.body) {
      var C = G.body;
      f.labels.forEach(function (L) { if (L.at) C = join(C, L.at); });
      if (C) {
        var m = P + 6, z = Math.min(V[2] / (C.x2 - C.x + 2 * m), V[3] / (C.y2 - C.y + 2 * m), ZOOM_MAX);
        if (z > 1.04) {
          var w2 = V[2] / z, h2 = V[3] / z;
          V = [(C.x + C.x2) / 2 - w2 / 2, (C.y + C.y2) / 2 - h2 / 2, w2, h2];
          setView(svg, V);
          zoom = z;
          s = scaleNow(svg);
          var up3 = upFor(s);
          if (Math.abs(up3 - up) > 0.01) {
            up = up3; upTo(up);
            G = gather(f, states);
            P = PAD_PX / s;
            res = place(f, G, V, P);
          }
        }
      }
    }
    return { theme: f.tone, scale: +s.toFixed(3), up: +up.toFixed(3), zoom: +zoom.toFixed(3), view: V.map(function (v) { return +v.toFixed(1); }),
             minTextPx: G.minPx < 1e8 ? +(G.minPx * scaleNow(svg) / G.scale).toFixed(2) : null, labels: res.labels, moved: res.moved,
             leaders: res.leaders, unplaced: res.unplaced, crowded: crowded, floorMet: !crowded && (up < UP_MAX || s * UP_MAX >= 1) };
  }

  /* ------------------------------------------------------------------ parts */

  /* panel - the monitoring screen frame, its title and the alarm-state chip */
  TYPES.panel = function (fig, part, g, p) {
    var w = p.w || 600, h = p.h || 440, w0 = w, h0 = h, px = p.x || 0, py = p.y || 0;
    var frame = el('rect', { x: 1, y: 1, width: w - 2, height: h - 2, rx: 14, 'class': 'kit-panel' }, g);
    /* the screen holds every part placed on it: a readout or an alarm list that grew with its words (the 12.5 px
       floor, a long alarm) makes the screen larger, never pokes out of it */
    fig.fit(function () {
      var W = w0, H = h0;
      q(fig.svg, '.kit-part').forEach(function (o) {
        if (o === g || !o.getBBox) return;
        var m = /translate\(\s*([-\d.]+)[ ,]+([-\d.]+)/.exec(o.getAttribute('transform') || ''), ox = m ? +m[1] - px : 0, oy = m ? +m[2] - py : 0;
        if (ox < 0 || oy < 0 || ox > w0 || oy > h0) return;              // placed outside the screen: not on it
        var b;
        try { b = o.getBBox(); } catch (e) { return; }
        if (!b.width && !b.height) return;
        W = Math.max(W, ox + b.x + b.width + 16);
        H = Math.max(H, oy + b.y + b.height + 16);
      });
      w = W; h = H;
      frame.setAttribute('width', w - 2); frame.setAttribute('height', h - 2);
      rule.setAttribute('x2', w - 1);
      chip.setAttribute('transform', 'translate(' + (w - 16) + ' 12)');
    }, true);
    var ttl = p.title ? el('text', { x: 20, y: 29, 'class': 'kit-ptitle' }, g, p.title) : null;
    var rule = el('line', { x1: 1, x2: w - 1, y1: 44, y2: 44, 'class': 'kit-rule' }, g);
    var chip = el('g', { transform: 'translate(' + (w - 16) + ' 12)' }, g);
    var box = el('rect', { y: -2, height: 26, rx: 13 }, chip);      // 26 high, 16 a side: the words keep 4 px clear at 2/3 size (L54)
    var txt = el('text', { y: 15.5, 'text-anchor': 'middle' }, chip);
    fig.fit(function (k) {                          // the header grows with its words (the 12.5 px floor)
      if (ttl) ttl.setAttribute('y', 29 + 12 * (k - 1));
      rule.setAttribute('y1', 44 + 14 * (k - 1)); rule.setAttribute('y2', 44 + 14 * (k - 1));
      box.setAttribute('height', 26 * k); box.setAttribute('rx', 13 * k); txt.setAttribute('y', 15.5 * k);
      part.alarms(fig.alarms);
    });
    part.alarms = function (list) {
      var n = list.length;
      var worst = list.some(function (a) { return a.kind === 'trip'; }) ? 'trip' : 'alarm';
      txt.textContent = n ? n + (n > 1 ? ' ALARMS' : ' ALARM') : 'ALL NORMAL';
      var tw = textWidth(txt, 8) + 32;
      box.setAttribute('x', -tw); box.setAttribute('width', tw); txt.setAttribute('x', -tw / 2);
      chip.setAttribute('class', 'kit-chip' + (n ? ' kit-on-' + worst : ''));
    };
  };

  /* does a pipe of the spec run through this box (x, y, x2, y2 in figure coordinates)? A pipe's path is read as straight runs
     between its vertices (a curve by its end points); a pipe part is placed by its "d" and its own x, y. */
  function pipeThrough(fig, B) {
    var hit = false;
    (fig.spec.parts || []).forEach(function (q) {
      if (hit || q.type !== 'pipe' || !q.d) return;
      var t = String(q.d).match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [], N = { M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, A: 7 };
      var ox = q.x || 0, oy = q.y || 0, cx = 0, cy = 0, sx = 0, sy = 0, cmd = '', i = 0;
      while (i < t.length && !hit) {
        if (/[a-zA-Z]/.test(t[i])) { cmd = t[i++]; if (/z/i.test(cmd)) { cx = sx; cy = sy; continue; } }
        var up = cmd.toUpperCase(), rel = cmd !== up, n = N[up];
        if (!n) break;
        var a = t.slice(i, i + n).map(Number), x = cx, y = cy; i += n;
        if (up === 'H') x = a[0] + (rel ? cx : 0); else if (up === 'V') y = a[0] + (rel ? cy : 0);
        else { x = a[n - 2] + (rel ? cx : 0); y = a[n - 1] + (rel ? cy : 0); }
        if (up === 'M') { sx = x; sy = y; cmd = rel ? 'l' : 'L'; }
        else {
          var len = Math.max(Math.abs(x - cx), Math.abs(y - cy)), steps = Math.max(1, Math.ceil(len / 3));
          for (var s = 0; s <= steps && !hit; s++) {
            var px = ox + cx + (x - cx) * s / steps, py = oy + cy + (y - cy) * s / steps;
            if (px >= B.x && px <= B.x2 && py >= B.y && py <= B.y2) hit = true;
          }
        }
        cx = x; cy = y;
      }
    });
    return hit;
  }

  /* level - a tank level column with its marks and a digital readout. The tick numbers stand left of the column; a pipe
     that runs into that strip (a feed line to the tank) puts them on the right instead (2.49.2), or say "ticks": "right" /
     "left" / false. */
  TYPES.level = function (fig, part, g, p) {
    var w = p.w || 60, h = p.h || 200, lo = p.min || 0, hi = p.max != null ? p.max : 100;
    var lx = p.x || 0, ly = p.y || 0, onRight = p.ticks === 'right' ||
      (p.ticks !== 'left' && p.ticks !== false && pipeThrough(fig, { x: lx - 62, y: ly - 8, x2: lx + 1, y2: ly + h + 8 }) &&
       !pipeThrough(fig, { x: lx + w - 1, y: ly - 8, x2: lx + w + 62, y2: ly + h + 8 }));
    function y(v) { return h - clamp((v - lo) / (hi - lo), 0, 1) * h; }
    var cid = fig.uid + '-' + p.id + '-clip';
    el('rect', { x: 3, y: 3, width: w - 6, height: h - 6, rx: 5 }, el('clipPath', { id: cid }, el('defs', {}, g)));
    if (p.label) label(fig, g, { x: w / 2, y: -14, 'text-anchor': 'middle', 'class': 'kit-h' }, p.label);
    el('rect', { width: w, height: h, rx: 8, 'class': 'kit-vessel' }, g);
    var inside = el('g', { 'clip-path': 'url(#' + cid + ')' }, g);
    var body = el('rect', { x: 0, width: w, 'class': 'kit-liquid' }, inside);
    var surf = el('line', { x1: 0, x2: w, 'class': 'kit-surface' }, inside);
    if (p.ticks !== false) {
      for (var i = 0; i <= 4; i++) {
        var tv = lo + (hi - lo) * i / 4, ty = y(tv);
        el('line', { x1: onRight ? w : -7, x2: onRight ? w + 7 : 0, y1: ty, y2: ty, 'class': 'kit-tickl' }, g);
        el('text', { x: onRight ? w + 11 : -11, y: ty + 4.5, 'text-anchor': onRight ? 'start' : 'end', 'class': 'kit-tick' }, g, num(tv, 0));
      }
    }
    part.marks.forEach(function (m) {
      var my = y(m.at), mg = el('g', { 'class': 'kit-mark kit-' + m.kind }, g);
      el('line', { x1: -4, x2: w + 10, y1: my, y2: my }, mg);
      if (m.label) label(fig, mg, { x: w + 14, y: my + 4.5 }, m.label, { near: 16, lead: false });   // it may shift, never far from its mark
      m.node = mg;
    });
    var out = null;
    if (p.readout !== false) {
      var dig = el('rect', { y: h + 14, height: 30, rx: 6, 'class': 'kit-dig' }, g);
      out = el('text', { x: w / 2, y: h + 35, 'text-anchor': 'middle', 'class': 'kit-num' }, g);
      fig.fit(function (k) {                      // as wide as its widest reading, 12 a side; as tall as its words
        var bw = Math.max(w + 16, 78, widest(out, readings(p, lo, hi, p.marks, part.v0)) + 24);
        dig.setAttribute('x', w / 2 - bw / 2); dig.setAttribute('width', bw);
        dig.setAttribute('height', 30 * k); out.setAttribute('y', h + 14 + 21 * k);
      });
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
    if (p.label) label(fig, g, { x: 0, y: -r - 14, 'text-anchor': 'middle', 'class': 'kit-h' }, p.label);
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
        label(fig, mg, { x: pt[0], y: y0, 'text-anchor': c > 0.3 ? 'start' : c < -0.3 ? 'end' : 'middle' }, m.label, { near: 16, lead: false });
      }
      m.node = mg;
    });
    var nd = el('g', { 'class': 'kit-needle' }, g), tail = mini ? 5 : 13, wd = mini ? 2 : 3;
    el('path', { d: 'M' + (-tail) + ' ' + (-wd) + ' L' + (tr - tw) + ' -0.9 L' + (tr - tw) + ' 0.9 L' + (-tail) + ' ' + wd + ' Z' }, nd);
    el('circle', { r: mini ? 3.5 : 7, 'class': 'kit-hub' }, g);
    var val = null, below = r + 22;
    if (!mini && p.readout !== false) {         // under the dial, clear of the scale numbers
      var dig = el('rect', { y: r + 10, height: 30, rx: 6, 'class': 'kit-dig' }, g);
      val = el('text', { x: 0, y: r + 31, 'text-anchor': 'middle', 'class': 'kit-num' }, g);
      below = r + 58;
      fig.fit(function (k) {
        var bw = Math.max(88, widest(val, readings(p, lo, hi, p.marks, part.v0)) + 24);
        dig.setAttribute('x', -bw / 2); dig.setAttribute('width', bw);
        dig.setAttribute('height', 30 * k); val.setAttribute('y', r + 10 + 21 * k);
      });
    }
    if (p.caption) {
      var right = p.captionAt === 'right';
      label(fig, g, { x: right ? r + 12 : 0, y: right ? 0 : below, 'text-anchor': right ? 'start' : 'middle', 'class': 'kit-cap' }, p.caption);
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
    var tile = el('rect', { width: w, height: h, rx: 8, 'class': 'kit-tile' }, g);
    var name = p.label ? el('text', { x: 12, y: 20, 'class': 'kit-tl' }, g, p.label) : null;
    var val = el('text', { x: w - 12, y: h - 11, 'text-anchor': 'end', 'class': 'kit-big' }, g);
    fig.fit(function (k) {                        // its name and its widest reading, 12 a side; as tall as its words
      var tw = Math.max(w, (name ? widest(name, [p.label]) : 0) + 24, widest(val, readings(p, p.min || 0, p.max != null ? p.max : 100, p.marks, part.v0)) + 24);
      var th = Math.max(h, 56 * k);
      tile.setAttribute('width', tw); tile.setAttribute('height', th);
      val.setAttribute('x', tw - 12); val.setAttribute('y', th - 11 * k);
      if (name) name.setAttribute('y', 20 * k);
    });
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
    var ring = el('circle', { cx: tx, cy: top - 22, r: 20, 'class': 'kit-bubble' }, g);   // 20: "TT" keeps its 4 px clear of the ring down to 2/3 size (L54)
    var tag = el('text', { x: tx, y: top - 17.5, 'text-anchor': 'middle', 'class': 'kit-bubble-t' }, g, p.tag || 'TT');
    fig.fit(function (k) {                          // the ring grows with its letters, standing on the probe
      ring.setAttribute('r', 20 * k); ring.setAttribute('cy', top - 2 - 20 * k); tag.setAttribute('y', top - 2 - 20 * k + 4.5 * k);
    });
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
    var lg = p.label || p.state !== false ? label(fig, g, {}, '') : null;          // its name and its state move together
    var nl = p.label ? lines(lg, { x: lx, y: ly, 'text-anchor': anchor, 'class': 'kit-cap' }, p.label) : 0;
    var st = p.state === false ? null : el('text', { x: lx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': anchor, 'class': 'kit-state' }, lg);
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
    var fluid = p.fluid === 'gas' || p.fluid === 'air' ? p.fluid : 'liquid', mid = fig.uid + '-' + (p.id || 'p' + (++UID)) + '-m';
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
    if (p.label) label(fig, g, { x: w / 2, y: h + 22, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) {
      var y = h - clamp(v, 0, 1) * h;
      liq.setAttribute('y', y); liq.setAttribute('height', h - y);
      surf.setAttribute('y1', y); surf.setAttribute('y2', y);
    };
    /* RUPTURE (2.49.1): "burst": true (or {"r": fireball radius, "label": "..."}) gives the tank a second value,
       "<id>.burst" 0..1 - the shell cracks (0..0.25), then the contents ignite and a fireball swells from the crack. The
       fireball reaches past the tank by design (data-may-cross) and past the figure's frame if the spec gives it no room:
       leave r of room round the tank. A tank without "burst" draws none of it, so nothing hidden can be cut off. */
    if (p.burst) {
      var B = p.burst === true ? {} : p.burst, R = B.r || w * 0.62, cx = w / 2, cy = h / 2;
      var crack = el('path', { d: 'M' + (cx - 8) + ' 0 L' + (cx + 6) + ' ' + (h * 0.22) + ' L' + (cx - 10) + ' ' + (h * 0.42) + ' L' + (cx + 8) + ' ' + (h * 0.62) +
                                  ' L' + (cx - 4) + ' ' + h, 'class': 'kit-tank-crack', 'data-may-cross': '' }, g);
      var ball = el('g', { 'class': 'kit-tank-fireball', 'data-may-cross': '', 'data-no-contain': '' }, g), lobes = [];
      [[0, 0, 1], [-0.42, 0.18, 0.62], [0.44, 0.12, 0.66], [-0.2, -0.34, 0.6], [0.24, -0.38, 0.58]].forEach(function (b) {
        lobes.push(el('circle', { cx: cx + b[0] * R, cy: cy + b[1] * R, r: b[2] * R * 0.62, 'class': 'kit-tank-fire-out', 'data-may-cross': '', 'data-no-contain': '' }, ball));
      });
      el('circle', { cx: cx, cy: cy, r: R * 0.34, 'class': 'kit-tank-fire-core', 'data-may-cross': '', 'data-no-contain': '', 'data-low-contrast': '' }, ball);
      var bl = B.label ? label(fig, g, { x: cx, y: -(R * 0.62 + 18), 'text-anchor': 'middle', 'class': 'kit-h' }, B.label) : null;   // named when it happens
      var pathLen = 0;
      try { pathLen = crack.getTotalLength(); } catch (e) { pathLen = 0; }
      pathLen = pathLen || 200;
      fig.sub(part, 'burst', 0, function (b) {
        var c = clamp(b / 0.25, 0, 1), e = clamp((b - 0.15) / 0.85, 0, 1);
        crack.setAttribute('stroke-dasharray', (pathLen * c).toFixed(1) + ' ' + (pathLen * 2).toFixed(1));
        crack.style.opacity = c > 0.01 ? '1' : '0';
        ball.setAttribute('transform', 'translate(' + cx + ' ' + cy + ') scale(' + Math.max(0.05, 0.15 + 0.85 * e).toFixed(3) + ') translate(' + (-cx) + ' ' + (-cy) + ')');
        ball.style.opacity = e > 0.01 ? '1' : '0';
        if (bl) bl.style.opacity = e > 0.01 ? '1' : '0';
        g.classList.toggle('kit-tank-burst', b > 0.01);
        g.classList.toggle('kit-tank-burning', e > 0.05);
      });
    }
  };

  /* space - a room or enclosure, named. value 0..1 = how strongly it is picked out.
     style "room" (dashed boundary, default) or "enclosure" (solid: a gas valve unit, a hood) */
  TYPES.space = function (fig, part, g, p) {
    var w = p.w || 120, h = p.h || 90;
    /* "crosses": true - a box laid over another shape on purpose (over a tank's rounded end, over a hull's line): it is
       not judged as poking out of what it sits on (2.49.1) */
    var over = p.crosses ? { 'data-may-cross': '' } : {};
    var wash = el('rect', { width: w, height: h, rx: 8, 'class': 'kit-wash', 'data-may-cross': over['data-may-cross'] }, g);
    el('rect', { width: w, height: h, rx: 8, 'class': 'kit-space kit-' + (p.style || 'room'), 'data-may-cross': over['data-may-cross'] }, g);
    if (p.label) {
      var below = p.labelAt === 'below';
      // 14 / 24: the name keeps its 4 px clear of the room's edge also when the figure is shown at 2/3 size (L54);
      // in a low room (a TCS 30 high) it sits in the middle, clear of the top and the bottom alike
      var nameG = label(fig, g, { x: below ? w / 2 : 14, y: below ? h + 20 : Math.min(24, h / 2 + 4.5), 'text-anchor': below ? 'middle' : 'start',
                                  'class': below ? 'kit-cap' : 'kit-sl' }, p.label, below ? null : { inside: true });
      /* a name inside a room that the grown type (the 12.5 px floor) no longer fits goes outside, under the room, instead
         of poking out of its side (2.49.1) */
      if (!below && String(p.label).indexOf('\n') < 0) {
        var nameT = nameG.querySelector('text'), inY = Math.min(24, h / 2 + 4.5);
        fig.fit(function (k) {
          nameT.setAttribute('class', 'kit-sl');
          var out = widest(nameT, [p.label]) + 14 + 4.5 * k + 2 > w;
          nameT.setAttribute('class', out ? 'kit-cap' : 'kit-sl');
          nameT.setAttribute('x', out ? w / 2 : 14);
          nameT.setAttribute('y', out ? h + 8 + 14 * k : inY);
          nameT.setAttribute('text-anchor', out ? 'middle' : 'start');
          nameG.__kitL.opt.inside = !out;
          [].forEach.call(nameT.querySelectorAll('tspan'), function (ts) { ts.setAttribute('x', out ? w / 2 : 14); });
        });
      }
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
    if (p.label) label(fig, g, { x: 0, y: r + 30, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { g.classList.toggle('kit-active', v > 0.5); coil.style.opacity = (0.55 + 0.45 * clamp(v, 0, 1)).toFixed(2); };
  };

  /* pump - P&ID centrifugal pump. value 0 stopped, 1 running (impeller turns) */
  TYPES.pump = function (fig, part, g, p) {
    var r = p.r || 15;
    el('path', { d: 'M0 ' + (-r) + ' H' + (r + 8) + ' V' + (-r + 8) + ' H' + (r * 0.5), 'class': 'kit-shell-o' }, g);
    el('circle', { r: r, 'class': 'kit-shell' }, g);
    var imp = el('g', { 'class': 'kit-imp' }, g);
    [0, 120, 240].forEach(function (a) { el('path', { d: 'M0 0 L' + (r * 0.7) + ' -3', transform: 'rotate(' + a + ')' }, imp); });
    if (p.label) label(fig, g, { x: 0, y: r + 22, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { g.classList.toggle('kit-running', v > 0.5); };
  };

  /* engine - a dual-fuel engine block. value 0 stopped, 1 running */
  TYPES.engine = function (fig, part, g, p) {
    var w = p.w || 100, h = p.h || 70, n = p.cylinders || 4, cw = (w - 16) / n;
    var block = el('rect', { width: w, height: h, rx: 8, 'class': 'kit-block' }, g);
    for (var i = 0; i < n; i++) {
      var cx = 8 + cw * i + cw / 2;
      el('rect', { x: cx - cw * 0.32, y: -10, width: cw * 0.64, height: 14, rx: 2, 'class': 'kit-head' }, g);
      el('rect', { x: cx - cw * 0.22, y: 8, width: cw * 0.44, height: 12, rx: 2, 'class': 'kit-piston', style: 'animation-delay:' + (-0.15 * i) + 's' }, g);
    }
    var st = el('text', { x: w / 2, y: h - 12, 'text-anchor': 'middle', 'class': 'kit-state' }, g);
    fig.fit(function (k) {          // RUNNING under the pistons' lowest point (25) with 4 clear, the block as tall as that needs
      var base = Math.max(h - 12, 29 + 10 * k), bh = Math.max(h, base + 8 * k);
      st.setAttribute('y', base); block.setAttribute('height', bh);
    });
    if (p.label) label(fig, g, { x: w / 2, y: h + 20, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { var on = v > 0.5; g.classList.toggle('kit-running', on); st.textContent = on ? 'RUNNING' : 'STOPPED'; };
  };

  /* the mast a vent stands on: the straight upright run of a spec pipe that ends at the vent's outlet, as [x, top, bottom]
     in the vent's own units (2.49.7, IGF M01 q03) - read like pipeThrough reads a pipe, absolute or relative M L H V */
  function mastUnder(fig, x, y) {
    var best = null;
    (fig.spec.parts || []).forEach(function (q) {
      if (q.type !== 'pipe' || !q.d) return;
      var t = String(q.d).match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [], N = { M: 2, L: 2, H: 1, V: 1 };
      var ox = q.x || 0, oy = q.y || 0, cx = 0, cy = 0, cmd = '', i = 0, pts = [];
      while (i < t.length) {
        if (/[a-zA-Z]/.test(t[i])) cmd = t[i++];
        var up = cmd.toUpperCase(), rel = cmd !== up, n = N[up];
        if (!n) { pts = []; break; }                       // a curve: no straight mast to read
        var a = t.slice(i, i + n).map(Number), nx = cx, ny = cy; i += n;
        if (up === 'H') nx = a[0] + (rel ? cx : 0); else if (up === 'V') ny = a[0] + (rel ? cy : 0);
        else { nx = a[0] + (rel ? cx : 0); ny = a[1] + (rel ? cy : 0); }
        if (up === 'M') { pts = []; cmd = rel ? 'l' : 'L'; }
        cx = nx; cy = ny;
        pts.push([ox + cx, oy + cy]);
      }
      [[0, 1], [pts.length - 1, pts.length - 2]].forEach(function (e) {
        var A = pts[e[0]], B = pts[e[1]];
        if (!A || !B || Math.abs(A[0] - x) > 3 || Math.abs(A[1] - y) > 3 || Math.abs(B[0] - A[0]) > 3 || B[1] - A[1] < 12) return;
        if (!best || B[1] - A[1] > best[2] - best[1]) best = [A[0] - x, A[1] - y, B[1] - y];
      });
    });
    return best;
  }

  /* vent - a vent outlet to the open air. value 0..1 = how much is venting (puffs).
     A vent on top of a pipe's upright run is a VENT MAST: its tap area on a task (gb_answer.js lays it on the part's box) is the
     whole mast, not the outlet alone - an unpainted box down the run (2.49.7, IGF M01 q03 needed a hand-made % box).
     "mast": false keeps the outlet alone; "mast": <length> gives the run when no pipe of the spec draws it; "mast": true asks
     for a mast. With no pipe of the spec under the outlet, a `true` or a length is DRAWN - an upright pipe down from the outlet
     (true: VENT_MAST long) - never a bare outlet floating in the air (M01 benchmark run 4: `true` was silently ignored).
     Any other value stops the figure with what it takes. */
  var VENT_MAST = 60;
  TYPES.vent = function (fig, part, g, p) {
    var m = p.mast;
    if (m !== undefined && m !== null && m !== true && m !== false && !(typeof m === 'number' && m > 0)) {
      throw new Error('kit: vent ' + (p.id || '') + ' has "mast": ' + JSON.stringify(m) +
                      ' - true (a mast), false (the outlet alone) or a length in figure units (the mast under the outlet)');
    }
    var under = m === false ? null : mastUnder(fig, p.x || 0, p.y || 0);
    var mast = m === false ? null : typeof m === 'number' ? [0, 0, m] : under || (m === true ? [0, 0, VENT_MAST] : null);
    if (mast && !under) el('path', { d: 'M0 0 V' + mast[2], 'class': 'kit-pipe kit-vent-mast' }, g);
    if (mast) {
      el('rect', { x: mast[0] - 9, y: mast[1], width: 18, height: mast[2] - mast[1], 'class': 'kit-hit',
                   style: 'fill:none;stroke:none' }, g);
    }
    el('path', { d: 'M-9 0 H9 M-6 -6 H6', 'class': 'kit-flange' }, g);
    var puffs = el('g', { 'class': 'kit-puffs' }, g);
    [0, 0.45, 0.9].forEach(function (d, i) {
      el('circle', { cx: (i - 1) * 5, cy: -12, r: 7, style: 'animation-delay:' + d + 's' }, puffs);
    });
    if (p.label) label(fig, g, { x: p.labelAt === 'left' ? -18 : 18, y: -2, 'text-anchor': p.labelAt === 'left' ? 'end' : 'start', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { puffs.style.opacity = clamp(v, 0, 1).toFixed(2); g.classList.toggle('kit-venting', v > 0.05); };
  };

  /* badge - a numbered step marker. value 0..1 = lit */
  TYPES.badge = function (fig, part, g, p) {
    var ring = el('circle', { r: 17, 'class': 'kit-badge-o' }, g);       // 17: every digit keeps its 4 px clear of the ring down to 2/3 size
    var disc = el('circle', { r: 17, 'class': 'kit-badge' }, g);
    var num_ = el('text', { y: 5, 'text-anchor': 'middle', 'class': 'kit-badge-t' }, g, String(p.n != null ? p.n : ''));
    fig.fit(function (k) { ring.setAttribute('r', 17 * k); disc.setAttribute('r', 17 * k); num_.setAttribute('y', 5 * k); });
    part.render = function (v) { disc.style.opacity = clamp(v, 0, 1).toFixed(2); g.classList.toggle('kit-lit', v > 0.5); };
  };

  /* wire - an instrument signal line (ISA: dashed) */
  TYPES.wire = function (fig, part, g, p) { el('path', { d: p.d, 'class': 'kit-wire' }, g); };

  /* text - a heading or caption; "\n" breaks lines.
     REVEAL (2.49.1): "reveal": true, or a "value", makes the words (and a callout's dot and leader line) a thing a step
     brings in: the value 0..1 is their opacity, so a step can fade them in ["T", 1, 600] after the figure has shown the
     cause - the answer is no longer printed at rest. Without either, the words stand at rest as before. */
  TYPES.text = function (fig, part, g, p) {        // it may shift a little to stay clear, never far and never with a leader
    var lbl;
    if (p.to && p.to.length === 2) {               // a CALLOUT: words for a place ("to": [x, y]) - a leader line joins them
      el('circle', { cx: p.to[0] - (p.x || 0), cy: p.to[1] - (p.y || 0), r: 2.5, 'class': 'kit-leader-dot', 'data-may-cross': '' }, g);
      lbl = label(fig, g, { x: 0, y: 0, 'text-anchor': p.anchor || 'middle', 'class': 'kit-' + (p.style || 'cap') }, p.text,
                  { callout: true, near: 6, fixed: !!p.fixed });
    } else {
      lbl = label(fig, g, { x: 0, y: 0, 'text-anchor': p.anchor || 'middle', 'class': 'kit-' + (p.style || 'cap') }, p.text,
                  { self: true, near: p.near != null ? p.near : 28, lead: false, fixed: !!p.fixed });
    }
    if (p.reveal === true || p.value != null) {
      part.render = function (v) {
        var k = clamp(v, 0, 1), o = k > 0.005 ? k.toFixed(2) : '0';
        g.style.opacity = o;
        lbl.__kitFade = o;
        if (lbl.__kitLeader) lbl.__kitLeader.style.opacity = o;
      };
    }
  };

  /* log - the alarm list: newest on top, time-stamped, flashing until it settles */
  TYPES.log = function (fig, part, g, p) {
    var w = p.w || 560, rows = p.rows || 2, rh = 24, k = 1, tx = 94, two = {}, lines2 = false;
    var box = el('rect', { width: w, height: 32 + rows * rh, rx: 10, 'class': 'kit-logbox' }, g);
    var head = el('text', { x: 14, y: 20, 'class': 'kit-tl' }, g, p.label || 'ALARM LOG');
    var body = el('g', { transform: 'translate(0 29)' }, g);
    /* no message runs out of its row: an alarm (every mark's text in the spec) too long for the log's width goes on two
       lines, broken at its best space, and every row is then two lines high - the log never gets wider than it was
       drawn, so a long alarm cannot push the figure smaller. As tall as its words at the 12.5 px floor (k). */
    fig.fit(function (up) {
      k = up || 1;
      var said = [];
      (fig.spec.parts || []).forEach(function (q2) { (q2.marks || []).forEach(function (m) { if (m.alarm) said.push(m.alarm); }); });
      var probe = el('text', { x: 0, y: -999, 'class': 'kit-time', 'aria-hidden': 'true' }, g);
      tx = 16 + widest(probe, ['00:00:00']) + 14;
      probe.setAttribute('class', 'kit-msg');
      var room = w - 16 - tx - 12;
      two = {}; lines2 = 1;
      /* 2.49.2: a long alarm (M14, M15) went on two lines only, and a narrow log still ran out of its box. The words are now
         set greedily, line by line, as many lines as they need to fit the room; every row is as tall as the most lines. */
      said.forEach(function (s) {
        if (widest(probe, [s]) <= room) return;
        var ws = s.split(' '), out = [], cur = '';
        ws.forEach(function (wd) {
          var t = cur ? cur + ' ' + wd : wd;
          if (cur && widest(probe, [t]) > room) { out.push(cur); cur = wd; } else cur = t;
        });
        if (cur) out.push(cur);
        if (out.length > 1) {
          /* balance: move words back from the shorter-line end so the lines are near equal (the same line count) */
          var L = out.length, flat = ws, best = out, bw = Math.max.apply(null, out.map(function (x) { return widest(probe, [x]); }));
          if (L === 2) {
            for (var c = 1; c < flat.length; c++) {
              var a = flat.slice(0, c).join(' '), b = flat.slice(c).join(' '), ww = Math.max(widest(probe, [a]), widest(probe, [b]));
              if (ww < bw) { bw = ww; best = [a, b]; }
            }
          }
          two[s] = best; lines2 = Math.max(lines2, best.length);
        }
      });
      g.removeChild(probe);
      rh = (8 + 16 * lines2) * k;
      box.setAttribute('height', 32 * k + rows * rh);
      head.setAttribute('y', 20 * k);
      body.setAttribute('transform', 'translate(0 ' + (29 * k) + ')');
      part.alarms(fig.alarms, null);
    });
    part.alarms = function (list, newest) {
      while (body.firstChild) body.removeChild(body.firstChild);
      if (!list.length) { el('text', { x: 14, y: 16 * k, 'class': 'kit-empty' }, body, p.empty || 'No active alarms'); return; }
      list.slice(0, rows).forEach(function (a, i) {
        var at = el('g', { transform: 'translate(8 ' + (i * rh) + ')' }, body);
        var row = el('g', { 'class': 'kit-row kit-' + a.kind + (a === newest ? ' kit-new' : '') }, at);
        el('rect', { width: w - 16, height: rh - 3, rx: 5 }, row);
        el('rect', { width: 5, height: rh - 3, rx: 2, 'class': 'kit-sev' }, row);
        el('text', { x: 16, y: 15.5 * k, 'class': 'kit-time' }, row, clock(fig, a.t));
        /* a wrapped alarm keeps the space it was broken at: lines() puts an undrawn space between rows, so "HIGH PRESSURE"
           over "ALARM" reads "HIGH PRESSURE ALARM" to a screen reader and to the drawing audit (K11, 2.49.1) */
        lines(row, { x: tx, y: 15.5 * k, 'class': 'kit-msg' }, two[a.text] ? two[a.text].join('\n') : a.text);
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
      still(host, fig);
    });
  }

  /* TASK MODE (2.43.0): <svg data-kit="#spec" data-kit-step="3"> is drawn STILL, at the end of step 3 ("final" or empty
     = the last step), with no step buttons - the same spec a deck plays, as a picture a trainee answers on. A static
     figure is not a driven one, so it opens full screen like any picture (gb_zoom) */
  function still(host, fig) {
    if (!host.hasAttribute || !host.hasAttribute('data-kit-step')) return;
    var want = host.getAttribute('data-kit-step'), n = /^\d+$/.test(want) ? +want : fig.steps();
    fig.go(Math.min(n, fig.steps()), true);
    host.removeAttribute('data-motion');
    host.setAttribute('data-kit-still', '');
  }
  /* after kit_parts.js has had its turn to define parts, which loads after this file */
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', auto); else setTimeout(auto, 0);

  root.KIT = {
    mount: mount, controls: controls, Figure: Figure, types: TYPES, define: define, local: LOCAL, added: ADDED,
    reducedMotion: reducedMotion,
    /* the drawing helpers every part uses - a new part uses these too, never its own */
    h: { el: el, lines: lines, label: label, widest: widest, readings: readings, clamp: clamp, num: num, fmt: fmt, polar: polar, arc: arc,
         flagMark: flagMark, textWidth: textWidth, NS: NS },
    figures: FIGS,
    /* the label solver alone, in plain numbers - for any drawing that can say where its outlines are (a 3D figure's
       projected parts); see solveLabels() */
    solveLabels: solveLabels,
    /* every figure on the page laid out again for the size it is shown at (the drawing audit calls it first) */
    layoutAll: function (force) { return FIGS.map(function (f) { return f.layout(force); }); }
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
  if (p.label) h.label(fig, g, { x: w / 2, y: d + (plan ? 22 : 30), 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
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
  if (p.orient === 'h') return across(fig, h, part, g, p, lo, hi, every);
  function y(v) { return H - h.clamp((v - lo) / (hi - lo), 0, 1) * H; }
  h.el('rect', { width: bw, height: H, rx: bw / 2, 'class': 'kit-vessel' }, g);
  /* 2.49.1: every word is placed as the type grows (the 12.5 px floor) - the tick numbers keep clear of their ticks, the
     limit's name of its line, a marker's note of its word - and the names (a limit's, a marker's word and note) are LABELS,
     so the layout keeps them clear of everything and the drawing audit judges them like any other label */
  var tickN = [], unitT = null, limitT = [], markT = [];
  for (var t = Math.ceil(lo / every) * every; t <= hi; t += every) {
    h.el('line', { x1: -7, x2: 0, y1: y(t), y2: y(t), 'class': 'kit-tickl' }, g);
    tickN.push({ y: y(t), n: h.el('text', { x: -11, y: y(t) + 4.5, 'text-anchor': 'end', 'class': 'kit-tick' }, g, h.num(t, 0)) });
  }
  if (p.unit) unitT = h.el('text', { x: bw / 2, y: -12, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, p.unit);
  (p.limits || []).forEach(function (m) {
    var lg = h.el('g', { 'class': 'kit-scale-limit' }, g);
    h.el('line', { x1: -4, x2: reach, y1: y(m.at), y2: y(m.at) }, lg);
    if (m.label) limitT.push({ y: y(m.at), n: h.label(fig, lg, { x: reach, y: y(m.at) - 11, 'text-anchor': 'end', 'class': 'kit-h' }, m.label, { near: 14, lead: false }).querySelector('text') });
  });
  var made = (p.markers || []).map(function (m) {
    var mg = h.el('g', {}, g);
    h.el('path', { d: 'M' + (bw + 2) + ' 0 L' + (bw + 12) + ' -6 V6 Z', 'class': 'kit-scale-pointer' }, mg);
    h.el('path', { d: 'M' + (bw + 18) + ' -9 H' + (bw + 30) + ' L' + (bw + 34) + ' -5 V11 H' + (bw + 18) + ' Z', 'class': 'kit-scale-can' }, mg);
    var ml = h.label(fig, mg, {}, '', { near: 16, lead: false });
    var word = h.el('text', { x: bw + 44, y: m.note ? -2 : 5, 'class': 'kit-h' }, ml, m.label || '');
    if (m.note) { h.lines(ml, { x: bw + 44, y: 14, 'class': 'kit-cap' }, m.note); }
    markT.push({ word: word, note: m.note ? ml.querySelector('text.kit-cap') : null });
    return { g: mg, at: y(m.at) };
  });
  fig.fit(function (k) {
    tickN.forEach(function (o) { o.n.setAttribute('x', (-(7 + 4.5 * k)).toFixed(1)); o.n.setAttribute('y', (o.y + 4.5 * k).toFixed(1)); });
    if (unitT) unitT.setAttribute('y', (-(5 + 7 * k)).toFixed(1));
    limitT.forEach(function (o) { o.n.setAttribute('y', (o.y - (3.5 + 7.5 * k)).toFixed(1)); });
    markT.forEach(function (o) { o.word.setAttribute('y', (o.note ? -2 * k : 5 * k).toFixed(1)); if (o.note) o.note.setAttribute('y', (14 * k).toFixed(1)); });
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
  function across(fig, h, part, g, p, lo, hi, every) {
    var L = p.len || 560, th = p.w || 18, reach = p.reach || 260;
    function x(v) { return h.clamp((v - lo) / (hi - lo), 0, 1) * L; }
    h.el('rect', { width: L, height: th, rx: th / 2, 'class': 'kit-vessel' }, g);
    var tickN = [], unitT = null, markT = [];                      // 2.49.1: words placed as the type grows, names are labels (see above)
    for (var t = Math.ceil(lo / every) * every; t <= hi; t += every) {
      h.el('line', { x1: x(t), x2: x(t), y1: th, y2: th + 7, 'class': 'kit-tickl' }, g);
      tickN.push(h.el('text', { x: x(t), y: th + 24, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, h.num(t, 0)));
    }
    if (p.unit) unitT = h.el('text', { x: L + 12, y: th / 2 + 4.5, 'class': 'kit-tick' }, g, p.unit);
    (p.limits || []).forEach(function (m) {
      var lg = h.el('g', { 'class': 'kit-scale-limit' }, g);
      h.el('line', { x1: x(m.at), x2: x(m.at), y1: -reach, y2: th + 4 }, lg);
      if (m.label) h.label(fig, lg, { x: x(m.at) + (m.side === 'left' ? -10 : 10), y: -reach + 14, 'text-anchor': m.side === 'left' ? 'end' : 'start',
                                      'class': 'kit-h' }, m.label, { near: 14, lead: false });
    });
    var made = (p.markers || []).map(function (m, k) {
      var rise = m.rise || 60 + 70 * k, left = m.side === 'left', ax = left ? 'end' : 'start', tx = left ? -16 : 16;
      var mg = h.el('g', {}, g);
      h.el('path', { d: 'M0 -2 L-6 -12 H6 Z', 'class': 'kit-scale-pointer' }, mg);
      h.el('line', { x1: 0, x2: 0, y1: -12, y2: -rise + 12, 'class': 'kit-scale-stem' }, mg);
      h.el('path', { d: 'M-6 ' + (-rise - 10) + ' H6 L10 ' + (-rise - 6) + ' V' + (-rise + 10) + ' H-6 Z', 'class': 'kit-scale-can' }, mg);
      var ml = h.label(fig, mg, {}, '', { near: 16, lead: false });
      var word = h.el('text', { x: tx, y: -rise + (m.note ? -2 : 5), 'text-anchor': ax, 'class': 'kit-h' }, ml, m.label || '');
      if (m.note) h.lines(ml, { x: tx, y: -rise + 14, 'text-anchor': ax, 'class': 'kit-cap' }, m.note);
      markT.push({ rise: rise, word: word, note: m.note ? ml.querySelector('text.kit-cap') : null });
      return { g: mg, at: x(m.at) };
    });
    fig.fit(function (k) {
      tickN.forEach(function (n) { n.setAttribute('y', (th + 7 + 16 * k).toFixed(1)); });       // under its tick by as far as the type is tall
      if (unitT) unitT.setAttribute('y', (th / 2 + 4.5 * k).toFixed(1));
      markT.forEach(function (o) {
        o.word.setAttribute('y', (-o.rise + (o.note ? -2 * k : 5 * k)).toFixed(1));
        if (o.note) o.note.setAttribute('y', (-o.rise + 14 * k).toFixed(1));
      });
    });
    part.render = function (v) {
      made.forEach(function (m, k) {
        var c = h.clamp(v - k, 0, 1);                     // drops onto its own place on the axis
        /* not yet there (c = 0) it waits invisibly at its own place: a marker parked 40 above its place stood past the
           frame the layout zoomed to, and the drawing audit reported it "cut off (in a later step)" (2.49.1) */
        m.g.setAttribute('transform', 'translate(' + m.at.toFixed(1) + ' ' + (c > 0.001 ? -(1 - c) * 40 : 0).toFixed(1) + ')');
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
  if (p.labels !== false) {          // each names its own feature (at): moved by a neighbour, it keeps a leader to it
    h.label(fig, g, { x: -24, y: 16, 'text-anchor': 'end', 'class': 'kit-cap' }, 'oil injector', { at: [ox - 5, 10] });
    h.label(fig, g, { x: w + 24, y: 16, 'text-anchor': 'start', 'class': 'kit-cap' }, 'gas injector', { at: [gx + 5, 10] });
    h.label(fig, g, { x: w / 2, y: -36, 'text-anchor': 'middle', 'class': 'kit-cap' }, 'exhaust valve', { at: [w / 2, -26] });
    h.label(fig, g, { x: -24, y: pTop + ph / 2 + 4, 'text-anchor': 'end', 'class': 'kit-cap' }, 'piston', { at: [4, pTop + ph / 2] });
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
  var ves = h.el('rect', { x: ins, y: ins, width: iw, height: ih, rx: r, 'class': 'kit-vessel' }, g);
  var inside = h.el('g', { 'clip-path': 'url(#' + cid + ')' }, g);
  h.el('rect', { x: ins, y: sy, width: iw, height: ins + ih - sy, 'class': 'kit-liquid' }, inside);
  h.el('line', { x1: ins, x2: ins + iw, y1: sy, y2: sy, 'class': 'kit-surface' }, inside);
  var bub = h.el('g', { 'class': 'kit-boil-off-bubbles' }, inside);
  [0.46, 0.55, 0.64, 0.73, 0.82].forEach(function (fx, i) {     // right of the liquid's name (IGF M04 finding 4: they rose through it)
    h.el('circle', { cx: ins + iw * fx, cy: ins + ih - 6, r: 3 + (i % 2), style: 'animation-delay:' + (-0.37 * i) + 's;--rise:' + Math.min(0, sy + 9 - (ins + ih - 6)).toFixed(0) + 'px' }, bub);
  });
  var heat = h.el('g', { 'class': 'kit-boil-off-heat' }, g);
  [[-30, ht / 2, 0], [w + 30, ht / 2, 180], [w * 0.38, ht + 30, -90], [w * 0.62, ht + 30, -90]].forEach(function (a) {
    var hg = h.el('g', { transform: 'translate(' + a[0] + ' ' + a[1] + ') rotate(' + a[2] + ')' }, heat);
    h.el('path', { d: 'M-14 0 q4 -5 8 0 t8 0 t8 0 M10 -6 L18 0 L10 6' }, hg);
  });
  var lx = ins + r * 0.75;                                 // clear of the rounded ends
  if (p.liquidLabel !== false) h.label(fig, g, { x: lx, y: ins + ih - 18, 'class': 'kit-h' }, p.liquidLabel || 'LNG', { inside: true, within: ves });
  if (p.vapourLabel !== false) h.label(fig, g, { x: lx, y: ins + 26, 'class': 'kit-h' }, p.vapourLabel || 'vapour', { inside: true, within: ves });
  if (p.heatLabel) h.label(fig, g, { x: w * 0.5, y: ht + 58, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.heatLabel);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    heat.style.opacity = k > 0.02 ? (0.6 + 0.4 * k).toFixed(2) : '0';      // a little heat is still drawn so it can be seen
    bub.style.opacity = k > 0.02 ? '1' : '0';                               // a bubble is there or not: never a faint one
    g.classList.toggle('kit-boil-off-on', k > 0.05);
  };
}, {
  family: 'cutaways',
  status: 'kit', merged_from: "IGF Basic M01",
  course: 'IGF Basic', module: 'M01', made: '2026-10-15',
  why: 'M01 s07: heat leaks through the insulation into a cold LNG tank and some of the liquid boils off as vapour',
  value: 'how much heat leaks in and boils the liquid, 0..1 (arrows and rising bubbles)',
  css: '.kit-boil-off-ins{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:4 3}.kit-boil-off-bubbles circle{fill:none;stroke:var(--deep);stroke-width:2}.kit-light .kit-boil-off-bubbles circle{stroke:var(--txt-d)}.kit-boil-off-heat path{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.kit-boil-off-on .kit-boil-off-bubbles circle{animation:kit-boil-off-rise 1.6s ease-in infinite}.kit-boil-off-on .kit-boil-off-heat g path{animation:kit-boil-off-in 1.2s ease-in-out infinite alternate}@keyframes kit-boil-off-rise{to{transform:translateY(var(--rise,-60px))}}@keyframes kit-boil-off-in{to{transform:translateX(6px)}}',
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
  /* WHERE IT GROWS FROM (2.49.2): "from": [x, y] is read in the cloud's own box (as every spec before 2.49.2 wrote it) OR in
     figure coordinates, the way every other part is placed. "fromIn": "box" | "figure" says which; left out, the kit reads it
     in the box when it lies inside the box (an old spec draws as it did) and otherwise, when it lies inside the box only as
     figure coordinates (x - the cloud's x, y - its y), as figure coordinates. A point inside the box both ways is read in the
     box - say "fromIn": "figure" to mean the other. check_kit.py warns when the origin lands off the figure. */
  var cx0 = p.x || 0, cy0 = p.y || 0, ox = w / 2, oy = ht * 0.6;
  if (p.from && p.from.length === 2) {
    var fx0 = +p.from[0], fy0 = +p.from[1], inBox = function (x, y) { return x >= 0 && x <= w && y >= 0 && y <= ht; };
    var asFig = p.fromIn === 'figure' || (p.fromIn !== 'box' && !inBox(fx0, fy0) && inBox(fx0 - cx0, fy0 - cy0));
    ox = asFig ? fx0 - cx0 : fx0; oy = asFig ? fy0 - cy0 : fy0;
  }
  var fid = fig.uid + '-' + p.id + '-soft';
  h.el('feGaussianBlur', { stdDeviation: Math.max(4, Math.min(w, ht) * 0.05) },
       h.el('filter', { id: fid, x: '-20%', y: '-20%', width: '140%', height: '140%' }, h.el('defs', {}, g)));
  /* DRIFT (2.49.1): "drift": [dx, dy] (or true: 0.4 w to the right) gives the cloud a second value, "<id>.drift" 0..1 - the
     whole cloud moves that far, spreading a little as it goes (wind carrying a leak away from where it began). It crosses
     walls and openings by design (data-may-cross); leave the room for its end place in the figure. */
  var drift = p.drift === true ? [w * 0.4, 0] : (p.drift && p.drift.length === 2 ? p.drift : null);
  var wrap = h.el('g', {}, g);
  var grow = h.el('g', { filter: 'url(#' + fid + ')' }, wrap);
  [[0.5, 0.56, 0.34, 0.3], [0.29, 0.62, 0.21, 0.25], [0.71, 0.6, 0.23, 0.26], [0.42, 0.4, 0.22, 0.2], [0.61, 0.42, 0.2, 0.2]]
    .forEach(function (b, i) {
      var at = { cx: b[0] * w, cy: b[1] * ht, rx: b[2] * w, ry: b[3] * ht, 'class': 'kit-gas-cloud-puff',
                 'data-no-contain': '', 'data-may-overlap': '', 'data-low-contrast': '',     // pale by design: methane vapour has no colour
                 style: 'animation-delay:' + (-0.7 * i) + 's' };
      if (drift) at['data-may-cross'] = '';
      h.el('ellipse', at, grow);
    });
  var level = 0, moved = 0;
  function put() {
    var k = h.clamp(level, 0, 1), s = 0.2 + 0.8 * k, d = h.clamp(moved, 0, 1), sp = 1 + 0.25 * d;
    grow.setAttribute('transform', 'translate(' + ox + ' ' + oy + ') scale(' + (s * sp).toFixed(3) + ') translate(' + (-ox) + ' ' + (-oy) + ')');
    if (drift) wrap.setAttribute('transform', 'translate(' + (drift[0] * d).toFixed(1) + ' ' + (drift[1] * d).toFixed(1) + ')');
    grow.style.opacity = k > 0.005 ? (0.45 + 0.55 * k).toFixed(2) : '0';
  }
  part.render = function (v) { level = v; put(); };
  part.motion = function (d) { g.classList.toggle('kit-gas-cloud-spreading', d > 0); };
  if (drift) {
    var dc = fig.sub(part, 'drift', 0, function (d) { moved = d; put(); });
    dc.motion = function (d) { g.classList.toggle('kit-gas-cloud-spreading', d > 0); };
  }
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M02",
  course: 'IGF Basic', module: 'M02', made: '2026-10-15',
  why: 'M02 s15: leaked gas gathering in the tank connection space until the detectors alarm and the gas is shut off; M06 and M13 need it too',
  value: 'how much gas has gathered, 0..1 (the cloud grows from its leak point, pale - methane vapour has no colour); option drift: [dx, dy] adds the value "<id>.drift" 0..1 - the cloud moves that far and spreads a little (wind carrying a leak away); option from: [x, y] is where it grows from - in figure coordinates like every other part (2.49.2), or in the own box of the cloud as older specs wrote it ("fromIn": "box" | "figure"; left out, the kit reads it in the box when it lies there, else in figure coordinates)',
  css: '.kit-gas-cloud-puff{fill:var(--txt-d);opacity:.2;transform-box:fill-box;transform-origin:center}.kit-gas-cloud-spreading .kit-gas-cloud-puff{animation:kit-gas-cloud-drift 2.4s ease-in-out infinite alternate}@keyframes kit-gas-cloud-drift{to{transform:scale(1.06)}}',
  example: { size: [400, 190], parts: [
    { id: 'R', type: 'space', x: 20, y: 20, w: 280, h: 150, label: 'TANK CONNECTION SPACE' },
    { id: 'C', type: 'gas_cloud', x: 20, y: 20, w: 280, h: 150, from: [110, 130], fromIn: 'figure', drift: [70, 0] } ],
    steps: [ { title: 'A leak: gas gathers', play: [['C', 1, 4000, 0, 'linear']] },
             { title: 'The wind carries the cloud away', play: [['C.drift', 1, 3000, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: integral_tank */
KIT.define('integral_tank', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 160, ht = p.h || 110, c = p.cofferdam != null ? p.cofferdam : 14;
  var tx = c, ty = c, tw = w - 2 * c, th = ht - c, cid = fig.uid + '-' + p.id + '-it';
  h.el('rect', { width: w, height: ht, rx: 3, 'class': 'kit-integral-tank-cd' }, g);
  h.el('rect', { x: tx, y: ty, width: tw, height: th }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var ves = h.el('rect', { x: tx, y: ty, width: tw, height: th, 'class': 'kit-vessel' }, g);
  var liq = h.el('rect', { x: tx, width: tw, 'class': 'kit-liquid', 'clip-path': 'url(#' + cid + ')' }, g);
  var surf = h.el('line', { x1: tx, x2: tx + tw, 'class': 'kit-surface', 'clip-path': 'url(#' + cid + ')' }, g);
  h.el('rect', { x: -10, y: ht, width: w + 20, height: 8, 'class': 'kit-steel' }, g);
  if (p.label) h.label(fig, g, { x: tx + 10, y: ty + 20, 'class': 'kit-sl' }, p.label, { inside: true, within: ves });
  if (p.cofferdamLabel !== false) h.label(fig, g, { x: w / 2, y: -8, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.cofferdamLabel || 'cofferdam');
  if (p.hullLabel !== false) h.label(fig, g, { x: w / 2, y: ht + 26, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.hullLabel || 'hull');
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
/* kit-part: pipe_section */
KIT.define('pipe_section', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 520, D = p.h || 100, t = 6, an = p.annulus || 18;
  var yi = t + an, b0 = yi + t, b1 = D - yi - t, bx = p.branchAt != null ? p.branchAt : w - 80, bw = 28, bh = p.branch || 56;
  var lk = (p.leakAt != null ? p.leakAt : 0.3) * bx, cid = fig.uid + '-' + p.id + '-ps', run = bx + bw - lk;
  var clip = h.el('clipPath', { id: cid }, h.el('defs', {}, g));
  h.el('rect', { x: 0, y: t, width: w - t, height: an }, clip);
  h.el('rect', { x: 0, y: D - yi, width: w - t, height: an }, clip);
  h.el('rect', { x: bx, y: -bh, width: bw, height: bh + t }, clip);
  h.el('rect', { x: 0, y: b0, width: w, height: b1 - b0, 'class': 'kit-pipe-section-bore', 'data-low-contrast': '' }, g);
  var inner = h.el('g', { 'class': 'kit-fl-gas' }, g);
  var flow = h.el('path', { d: 'M0 ' + (D / 2) + ' H' + w, 'class': 'kit-flow' }, inner);
  var ann = h.el('g', { 'clip-path': 'url(#' + cid + ')' }, g);
  var gas = h.el('rect', { x: lk, y: t, height: an, width: 0, 'class': 'kit-pipe-section-gas' }, ann);
  var gasUp = h.el('rect', { x: bx, width: bw, y: t, height: 0, 'class': 'kit-pipe-section-gas' }, ann);
  var air = h.el('g', { 'class': 'kit-pipe-section-air' }, ann), ax = h.el('g', { 'class': 'kit-pipe-section-ax' }, air);
  [t + an / 2, D - yi + an / 2].forEach(function (cy) {
    for (var x = -40; x < w; x += 40) h.el('path', { d: 'M' + (x - 4) + ' ' + (cy - 5) + ' L' + (x + 3) + ' ' + cy + ' L' + (x - 4) + ' ' + (cy + 5) }, ax);
  });
  var ay = h.el('g', { 'class': 'kit-pipe-section-ay' }, air), cx = bx + bw / 2;
  for (var y = t + 28; y > -bh - 28; y -= 28) h.el('path', { d: 'M' + (cx - 5) + ' ' + (y + 4) + ' L' + cx + ' ' + (y - 3) + ' L' + (cx + 5) + ' ' + (y + 4) }, ay);
  [[0, 0, bx - t, t], [bx + bw + t, 0, w - bx - bw - t, t], [0, D - t, w, t], [0, yi, w, t], [0, D - yi - t, w, t],
   [bx - t, -bh, t, bh + t], [bx + bw, -bh, t, bh + t], [w - t, t, t, an], [w - t, D - yi, t, an]].forEach(function (r) {
    h.el('rect', { x: r[0], y: r[1], width: r[2], height: r[3], 'class': 'kit-pipe-section-wall' }, g);
  });
  var crack = h.el('path', { d: 'M' + (lk - 4) + ' ' + yi + ' L' + (lk + 2) + ' ' + (yi + t / 2) + ' L' + (lk - 2) + ' ' + (yi + t), 'class': 'kit-pipe-section-crack' }, g);
  part.render = function (v) {
    var a = h.clamp(v, 0, 1), k = h.clamp(v - 1, 0, 1), along = h.clamp(k / 0.75, 0, 1), up = h.clamp((k - 0.75) / 0.25, 0, 1);
    flow.style.opacity = a > 0.02 ? '1' : '0';
    air.style.opacity = (0.65 + 0.35 * a).toFixed(2);
    g.classList.toggle('kit-pipe-section-on', a > 0.05);
    gas.setAttribute('width', (along * run).toFixed(1));
    gasUp.setAttribute('y', (t - up * (bh + t)).toFixed(1)); gasUp.setAttribute('height', (up * (bh + t)).toFixed(1));
    crack.style.opacity = k > 0.01 ? '1' : '0';
  };
}, {
  family: 'cutaways',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s02: a cut along a double-walled gas pipe - gas in the inner pipe, air drawn through the annular space to an outlet; a leak stays in the annular space and is carried out',
  value: '0 still · 1 gas flowing and the annular space ventilated · 1..2 a leak from the inner pipe spreads along the annular space and up the outlet',
  css: '.kit-pipe-section-wall{fill:var(--faint-d)}.kit-pipe-section-bore{fill:var(--txt-d);opacity:.08}.kit-pipe-section-gas{fill:var(--txt-d);fill-opacity:.4;stroke:var(--txt-d);stroke-width:1.5}.kit-pipe-section-air path{fill:none;stroke:var(--cold);stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.kit-pipe-section-crack{fill:none;stroke:var(--deep-2);stroke-width:3}.kit-pipe-section-on .kit-pipe-section-ax{animation:kit-pipe-section-x 1.1s linear infinite}.kit-pipe-section-on .kit-pipe-section-ay{animation:kit-pipe-section-y .9s linear infinite}@keyframes kit-pipe-section-x{to{transform:translateX(40px)}}@keyframes kit-pipe-section-y{to{transform:translateY(-28px)}}',
  example: { size: [460, 220], parts: [
    { id: 'P', type: 'pipe_section', x: 20, y: 90, w: 420, h: 96 } ],
    steps: [ { title: 'Gas flows; air is drawn through the annular space', play: [['P', 1, 800]] },
             { title: 'A leak stays in the annular space and is carried out', play: [['P', 2, 4000, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: relief_valve */
KIT.define('relief_valve', function (fig, part, g, p) {
  var h = KIT.h, s = p.size || 14, k = s * 0.7, top = -s - 22, left = p.outlet === 'left';
  var sym = h.el('g', { transform: left ? 'scale(-1 1)' : null }, g);
  [['M0 0 L' + (-k) + ' ' + s + ' H' + k + ' Z'], ['M0 0 L' + s + ' ' + (-k) + ' V' + k + ' Z']].forEach(function (d) {
    h.el('path', { d: d[0], 'class': 'kit-valve-bg' }, sym);
    h.el('path', { d: d[0], 'class': 'kit-valve' }, sym);
  });
  h.el('line', { x1: -8, x2: 8, y1: top, y2: top, 'class': 'kit-flange' }, sym);
  var spring = h.el('path', { 'class': 'kit-relief-valve-spring' }, sym);
  var disc = h.el('rect', { x: -k, width: 2 * k, height: 4, rx: 1.5, 'class': 'kit-relief-valve-disc' }, sym);
  var right = p.labelAt === 'right', lx = right ? s + 14 : 0, ly = right ? top + 10 : s + 22, anchor = right ? 'start' : 'middle';
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;           // its name and its state move together
  var nl = p.label ? h.lines(lg, { x: lx, y: ly, 'text-anchor': anchor, 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state === false ? null : h.el('text', { x: lx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': anchor, 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var lift = h.clamp(v, 0, 1), dy = -4 - lift * 8, d = 'M0 ' + (dy - 1), n = 6, seg = (top - (dy - 1)) / n;
    for (var i = 1; i <= n; i++) d += ' L' + (i === n ? 0 : (i % 2 ? 6 : -6)) + ' ' + (dy - 1 + seg * i).toFixed(1);
    spring.setAttribute('d', d);
    disc.setAttribute('y', (dy).toFixed(1));
    if (st) st.textContent = lift > 0.1 ? 'RELIEVING' : 'CLOSED';
    g.classList.toggle('kit-relief-valve-lift', lift > 0.1);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s03 and s09: a spring-loaded relief valve - the spring holds the disc on its seat until the pressure beats it, then the disc lifts and the vapour goes to the vent',
  value: 'how far the disc has lifted, 0 closed .. 1 fully open; inlet at (0, size) below, outlet at (size, 0) to the side',
  css: '.kit-relief-valve-spring{fill:none;stroke:var(--dim-d);stroke-width:2;stroke-linejoin:round}.kit-relief-valve-disc{fill:var(--dim-d)}.kit-relief-valve-lift .kit-relief-valve-spring{stroke:var(--amber)}.kit-relief-valve-lift .kit-relief-valve-disc{fill:var(--amber)}.kit-relief-valve-lift .kit-state{fill:var(--amber)}',
  example: { size: [320, 200], parts: [
    { id: 'P', type: 'pipe', fluid: 'gas', d: 'M120 170 V114', value: 0 },
    { id: 'O', type: 'pipe', fluid: 'gas', d: 'M134 100 H240 V40', value: 0 },
    { id: 'R', type: 'relief_valve', x: 120, y: 100, labelAt: 'right', outlet: 'left', label: 'relief valve' },
    { id: 'V', type: 'vent', x: 240, y: 40 } ],
    steps: [ { title: 'The pressure beats the spring: the valve lifts', play: [['R', 1, 600], ['P', 1, 300], ['O', 1, 300, 300], ['V', 1, 400, 500]] },
             { title: 'The pressure falls: the spring closes it', play: [['R', 0, 600], ['P', 0, 300], ['O', 0, 300], ['V', 0, 400]] } ] }
});
/* end kit-part */
/* kit-part: step_track */
KIT.define('step_track', function (fig, part, g, p) {
  var h = KIT.h, steps = p.steps || [], n = steps.length, vert = !!p.vertical, box = !!p.boxes;
  var gap = vert ? (p.gap || 34) : (n > 1 ? (p.w || 600) / (n - 1) : 0);
  for (var k = 0; !box && k < n - 1; k++) {           // the rail runs between the circles, never under a number
    var a0 = gap * k + 20, a1 = gap * (k + 1) - 20;
    h.el('line', vert ? { x1: 0, x2: 0, y1: a0, y2: a1, 'class': 'kit-step-track-rail' }
                      : { x1: a0, x2: a1, y1: 0, y2: 0, 'class': 'kit-step-track-rail' }, g);
  }
  var made = steps.map(function (label, i) {
    var sg = h.el('g', { transform: 'translate(' + (vert ? 0 : gap * i) + ' ' + (vert ? gap * i : 0) + ')', 'class': 'kit-step-track-step' }, g);
    if (box) h.el('rect', { x: -10, y: -10, width: 20, height: 20, rx: 4, 'class': 'kit-badge-o' }, sg);
    else {
      h.el('circle', { r: 17, 'class': 'kit-badge-o' }, sg);              /* room for a digit at 0.8x (audit_drawing) */
      h.el('circle', { r: 17, 'class': 'kit-badge' }, sg);
      h.el('text', { y: 5, 'text-anchor': 'middle', 'class': 'kit-badge-t' }, sg, String(i + 1));
    }
    h.el('path', { d: 'M-6 0 L-2 5 L7 -6', 'class': 'kit-step-track-tick' }, sg);
    h.label(fig, sg, vert ? { x: 24, y: 5, 'class': 'kit-cap' } : { x: 0, y: 34, 'text-anchor': 'middle', 'class': 'kit-cap' }, label,
            { near: 22, lead: false });      // two long neighbours step apart, never far from their number
    return sg;
  });
  part.render = function (v) {
    made.forEach(function (sg, i) {
      var k = i + 1, cur = !box && Math.abs(v - k) < 0.5, done = box ? v >= k - 0.001 : v >= k + 0.5;
      sg.classList.toggle('kit-lit', cur);
      sg.classList.toggle('kit-step-track-done', done);
    });
  };
}, {
  family: 'procedures',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s18 the eight steps of a bunkering operation, s14 the bunker safety checklist ticked off; the first part of the Procedures family M05, M11, M14 and M15 need',
  value: 'circles: step k is the current one while the value is about k, and ticked once it passes k + 0.5 · boxes (a checklist): item k is ticked once the value reaches k',
  css: '.kit-step-track-rail{stroke:var(--faint-d);stroke-width:2}.kit-step-track-step.kit-lit .kit-badge{opacity:1}.kit-step-track-tick{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;opacity:0}.kit-step-track-done .kit-step-track-tick{opacity:1}.kit-step-track-done .kit-badge-t{display:none}.kit-step-track-step.kit-lit .kit-cap,.kit-step-track-done .kit-cap{fill:var(--txt-d)}',
  example: { size: [460, 150], parts: [
    { id: 'S', type: 'step_track', x: 40, y: 40, w: 380, steps: ['Prepare', 'Connect', 'Inert', 'Cool down', 'Transfer'] } ],
    steps: [ { title: 'Step 1', play: [['S', 1, 400]] }, { title: 'Step 2', play: [['S', 2, 400]] }, { title: 'Step 3', play: [['S', 3, 400]] } ] }
});
/* end kit-part */
/* kit-part: coupling */
KIT.define('coupling', function (fig, part, g, p) {
  var h = KIT.h, brk = p.kind === 'breakaway';
  var sym = h.el('g', { transform: p.rotate ? 'rotate(' + p.rotate + ')' : null }, g);
  var L = h.el('g', {}, sym), R = h.el('g', {}, sym);
  h.el('rect', { x: -20, y: -11, width: 18, height: 22, rx: 3, 'class': 'kit-coupling-body' }, L);
  h.el('rect', { x: 2, y: -11, width: 18, height: 22, rx: 3, 'class': 'kit-coupling-body' }, R);
  var seals = [h.el('rect', { x: -6, y: -8, width: 3, height: 16, 'class': 'kit-coupling-seal' }, L),
               h.el('rect', { x: 3, y: -8, width: 3, height: 16, 'class': 'kit-coupling-seal' }, R)];
  var mark = brk ? h.el('line', { x1: 0, x2: 0, y1: -16, y2: 16, 'class': 'kit-coupling-break' }, sym) : null;
  var above = p.labelAt === 'above', nl = p.label ? String(p.label).split('\n').length : 0;
  var ly = above ? -24 - (nl - 1) * 16 : 32;
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;           // its name and its state move together
  if (p.label) h.lines(lg, { x: 0, y: ly, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  var st = p.state === false ? null : h.el('text', { x: 0, y: ly, dy: (above ? -1.28 : nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 1), gap = (1 - c) * 12;
    L.setAttribute('transform', 'translate(' + (-gap).toFixed(1) + ' 0)');
    R.setAttribute('transform', 'translate(' + gap.toFixed(1) + ' 0)');
    seals.forEach(function (s) { s.style.opacity = c < 0.5 ? '1' : '0'; });
    if (mark) mark.style.opacity = c > 0.5 ? '1' : '0';
    if (st) st.textContent = c > 0.5 ? 'CONNECTED' : (brk ? 'PARTED - SEALED' : 'DISCONNECTED');
    g.classList.toggle('kit-coupling-parted', c < 0.5);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s13 and s15: the dry-disconnect coupling and the breakaway coupling at the bunkering station - when they part, both halves are sealed',
  value: '1 connected, 0 parted (each half shows its closed face); kind "dry" or "breakaway"',
  css: '.kit-coupling-body{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}.kit-coupling-seal{fill:var(--txt-d)}.kit-coupling-break{stroke:var(--dim-d);stroke-width:2;stroke-dasharray:3 3}',
  example: { size: [320, 140], parts: [
    { id: 'A', type: 'pipe', d: 'M20 50 H148', value: 0 },
    { id: 'B', type: 'pipe', d: 'M172 50 H300', value: 0 },
    { id: 'C', type: 'coupling', x: 160, y: 50, kind: 'breakaway', label: 'breakaway coupling' } ],
    steps: [ { title: 'Connected', play: [['C', 1, 600]] }, { title: 'Pulled apart - both halves seal', play: [['C', 0, 600]] } ] }
});
/* end kit-part */
/* kit-part: drip_tray */
KIT.define('drip_tray', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 160, d = p.h || 24, cid = fig.uid + '-' + p.id + '-dt';
  h.el('rect', { x: 6, y: d + 3, width: w - 12, height: 8, rx: 2, 'class': 'kit-drip-tray-ins' }, g);
  h.el('rect', { x: 3, y: 0, width: w - 6, height: d - 3 }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var pool = h.el('rect', { x: 3, width: w - 6, 'class': 'kit-pool', 'clip-path': 'url(#' + cid + ')' }, g);
  h.el('path', { d: 'M0 0 V' + d + ' H' + w + ' V0', 'class': 'kit-drip-tray-pan' }, g);
  if (p.drip) {
    var dx = p.dripAt != null ? p.dripAt : w / 2;
    [0, 0.3, 0.6].forEach(function (s) {
      h.el('circle', { cx: dx, cy: -p.drip, r: 3.2, 'class': 'kit-drop', style: 'animation-delay:' + s + 's;--fall:' + (p.drip + d - 8) + 'px' }, g);
    });
  }
  /* the name sits just under the insulation strip (not 32 px below it, onto a deck line) and is placed by the layout,
     which keeps it clear of the deck; "labelAt": "above" | "left" | "right" puts it elsewhere (2.49.1) */
  if (p.label) {
    var at = p.labelAt || 'below', lab = h.label(fig, g, { x: w / 2, y: d + 25, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label), lt = lab.querySelector('text');
    fig.fit(function (k) {
      var x = at === 'left' ? -10 : at === 'right' ? w + 10 : w / 2, y = at === 'above' ? -(6 + 4.5 * k) : at === 'below' ? d + 11 + 14 * k : d / 2 + 4.5 * k;
      lt.setAttribute('x', x); lt.setAttribute('y', y);
      lt.setAttribute('text-anchor', at === 'left' ? 'end' : at === 'right' ? 'start' : 'middle');
      [].forEach.call(lt.querySelectorAll('tspan'), function (ts) { ts.setAttribute('x', x); });
    });
  }
  part.render = function (v) {
    var lv = h.clamp(v, 0, 1) * (d - 6);
    pool.setAttribute('y', (d - 3 - lv).toFixed(1)); pool.setAttribute('height', lv.toFixed(1));
  };
  part.motion = function (dv) { g.classList.toggle('kit-dripping', dv > 0); };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s16: a stainless steel drip tray, insulated from the deck, catches LNG leaking from a flange at the bunker manifold',
  value: 'how full the tray is, 0..1 (drops fall while it fills); labelAt: below (default) | above | left | right',
  css: '.kit-drip-tray-pan{fill:none;stroke:var(--dim-d);stroke-width:3;stroke-linejoin:round}.kit-drip-tray-ins{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:4 3}',
  example: { size: [300, 160], parts: [
    { id: 'D', type: 'drip_tray', x: 70, y: 70, w: 160, drip: 50, label: 'drip tray' } ],
    steps: [ { title: 'A spill is caught', play: [['D', 1, 2500]] } ] }
});
/* end kit-part */
/* kit-part: water_curtain */
KIT.define('water_curtain', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 36, ht = p.h || 120, n = Math.max(3, Math.round(w / 9));
  var sheet = h.el('g', { 'class': 'kit-water-curtain-sheet' }, g);
  for (var i = 0; i < n; i++) {
    var x = ((i + 0.5) * w / n).toFixed(1);
    h.el('line', { x1: x, x2: x, y1: 0, y2: ht, style: 'animation-delay:' + (-0.17 * i).toFixed(2) + 's' }, sheet);
  }
  if (p.label) h.label(fig, g, { x: p.labelAt === 'left' ? -10 : w + 10, y: ht / 2, 'text-anchor': p.labelAt === 'left' ? 'end' : 'start', 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    sheet.style.opacity = k.toFixed(2);
    g.classList.toggle('kit-water-curtain-on', k > 0.05);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s11: water spray cooling a burning vent mast head (a water curtain down the hull is only an "other solutions" bullet on s16, not drawn)',
  value: 'how much water is running, 0..1',
  css: '.kit-water-curtain-sheet line{stroke:var(--cold);stroke-width:2;stroke-dasharray:6 8;stroke-linecap:round}.kit-water-curtain-on .kit-water-curtain-sheet line{animation:kit-water-curtain-fall .7s linear infinite}@keyframes kit-water-curtain-fall{to{stroke-dashoffset:-28}}',
  example: { size: [300, 180], parts: [
    { type: 'text', x: 110, y: 22, text: 'hull' },
    { id: 'W', type: 'water_curtain', x: 120, y: 30, w: 40, h: 120, label: 'water curtain' } ],
    steps: [ { title: 'The water curtain runs', play: [['W', 1, 800]] } ] }
});
/* end kit-part */
/* kit-part: detector */
KIT.define('detector', function (fig, part, g, p) {
  var h = KIT.h, r = p.r || 19, at = p.readAt || 'right';
  var head = h.el('circle', { r: r, 'class': 'kit-detector-head' }, g);
  var tag = h.el('text', { y: 4.5, 'text-anchor': 'middle', 'class': 'kit-bubble-t' }, g, p.tag || 'GD');
  var pos = { right: { x: r + 8, y: 4.5, a: 'start' }, left: { x: -r - 8, y: 4.5, a: 'end' }, below: { x: 0, y: r + 20, a: 'middle' } }[at] || { x: r + 8, y: 4.5, a: 'start' };
  var val = p.readout === false ? null : h.el('text', { x: pos.x, y: pos.y, 'text-anchor': pos.a, 'class': 'kit-state' }, g);
  fig.fit(function (k) {                          // the head grows with its letters (the 12.5 px floor), the reading beside it
    head.setAttribute('r', r * k); tag.setAttribute('y', 4.5 * k);
    if (val) {
      val.setAttribute('x', at === 'below' ? 0 : (at === 'left' ? -1 : 1) * (r * k + 8));
      val.setAttribute('y', at === 'below' ? r * k + 20 * k : 4.5 * k);
    }
  });
  if (p.label) h.label(fig, g, { x: 0, y: at === 'below' ? r + 38 : r + 20, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  part.render = function (v) { if (val) val.textContent = h.fmt(v, p); };
  part.flag = function (m, on) { g.classList.toggle('kit-on-' + m.kind, on); };
}, {
  family: 'instruments',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s17: a fixed gas detector head placed in a space - where it sits is the lesson; it reads % LEL and alarms on its marks',
  value: 'the reading (for gas: % LEL); its marks turn it amber (alarm) or red (trip)',
  css: '.kit-detector-head{fill:var(--deep);stroke:var(--dim-d);stroke-width:2}.kit-on-alarm .kit-detector-head{stroke:var(--amber);stroke-width:3.5}.kit-on-alarm .kit-state{fill:var(--amber)}.kit-on-trip .kit-detector-head{stroke:var(--warn-d)}.kit-on-trip .kit-state{fill:var(--warn-d)}',
  example: { size: [300, 160], parts: [
    { id: 'R', type: 'space', x: 20, y: 30, w: 260, h: 110, label: 'FUEL PREPARATION ROOM' },
    { id: 'D', type: 'detector', x: 150, y: 70, unit: '% LEL', label: 'near the deckhead',
      marks: [{ at: 20, kind: 'alarm', alarm: 'GAS 20 % LEL · alarm' }] } ],
    steps: [ { title: 'Gas reaches the detector', play: [['D', 24, 2500, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: flame */
KIT.define('flame', function (fig, part, g, p) {
  var h = KIT.h, s = p.size || 44;
  function tongue(k) {
    return 'M0 0 C' + (-s * 0.45 * k) + ' ' + (-s * 0.22 * k) + ' ' + (-s * 0.32 * k) + ' ' + (-s * 0.7 * k) + ' 0 ' + (-s * k) +
           ' C' + (s * 0.32 * k) + ' ' + (-s * 0.7 * k) + ' ' + (s * 0.45 * k) + ' ' + (-s * 0.22 * k) + ' 0 0 Z';
  }
  var grow = h.el('g', {}, g), body = h.el('g', { 'class': 'kit-flame-body' }, grow);
  /* a flame stands on a tank, a room's roof or a vent and burns up past it by its nature: it is not judged as poking out of
     what it stands on, and it holds nothing (2.49.1) */
  h.el('path', { d: tongue(1), 'class': 'kit-flame-outer', 'data-may-cross': '', 'data-no-contain': '' }, body);
  h.el('path', { d: tongue(0.55), 'class': 'kit-flame-core', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, body);   // the hot core inside the flame: its outer tongue carries the contrast
  if (p.label) h.label(fig, g, { x: s * 0.6, y: -s * 0.6, 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    grow.setAttribute('transform', 'scale(' + Math.max(k, 0.001).toFixed(3) + ')');
    grow.style.opacity = k > 0.02 ? '1' : '0';
    g.classList.toggle('kit-flame-on', k > 0.05);
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  why: 'M03 s11: venting gas has caught fire at the vent mast outlet - the flame stands while gas is released and goes out when the release stops and nitrogen smothers it; M13 needs it too',
  value: 'the size of the flame, 0 out .. 1 full; it stands on its point (x, y) and burns upwards',
  css: '.kit-flame-outer{fill:var(--warn-d);opacity:.7}.kit-flame-core{fill:var(--amber)}.kit-flame-on .kit-flame-body{transform-box:fill-box;transform-origin:50% 100%;animation:kit-flame-flicker .35s ease-in-out infinite alternate}@keyframes kit-flame-flicker{to{transform:scale(1.07,.9)}}',
  example: { size: [240, 160], parts: [
    { id: 'P', type: 'pipe', fluid: 'gas', d: 'M120 150 V90', value: 1 },
    { id: 'V', type: 'vent', x: 120, y: 90, value: 1 },
    { id: 'F', type: 'flame', x: 120, y: 80, label: 'gas burning\nat the outlet' } ],
    steps: [ { title: 'The venting gas ignites', play: [['F', 1, 900]] }, { title: 'Venting stops - the flame goes out', play: [['F', 0, 1200], ['V', 0, 600], ['P', 0, 600]] } ] }
});
/* end kit-part */
/* kit-part: curve_chart */
KIT.define('curve_chart', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 560, ht = p.h || 320;
  var X = p.xaxis || { min: 0, max: 100, every: 20, unit: '' }, Y = p.yaxis || { min: 0, max: 10, every: 2, unit: '' };
  var curves = p.curves || [], pt = p.point || null;
  function sx(v) { return (v - X.min) / (X.max - X.min) * w; }
  function sy(v) { return ht - (v - Y.min) / (Y.max - Y.min) * ht; }
  var axes = h.el('g', { 'class': 'kit-curve-chart-axes' }, g);
  for (var xv = X.min; xv <= X.max + 1e-9; xv += X.every) {
    h.el('line', { x1: sx(xv), y1: 0, x2: sx(xv), y2: ht, 'class': 'kit-curve-chart-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, axes);
    h.el('text', { x: sx(xv), y: ht + 18, 'text-anchor': 'middle', 'class': 'kit-tick' }, axes, String(xv).replace('-', '−'));
  }
  for (var yv = Y.min; yv <= Y.max + 1e-9; yv += Y.every) {
    h.el('line', { x1: 0, y1: sy(yv), x2: w, y2: sy(yv), 'class': 'kit-curve-chart-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, axes);
    h.el('text', { x: -12, y: sy(yv) + 4, 'text-anchor': 'end', 'class': 'kit-tick' }, axes, String(yv));
  }
  h.el('path', { d: 'M0 0 V' + ht + ' H' + w, 'class': 'kit-curve-chart-frame', 'data-may-cross': '' }, axes);
  if (X.label) h.el('text', { x: w, y: ht + 38, 'text-anchor': 'end', 'class': 'kit-cap' }, axes, X.label);
  if (Y.label) h.el('text', { x: 0, y: -12, 'text-anchor': 'start', 'class': 'kit-cap' }, axes, Y.label);
  if (p.hline) {
    h.el('line', { x1: 0, y1: sy(p.hline.at), x2: w, y2: sy(p.hline.at), 'class': 'kit-curve-chart-hline', 'data-may-cross': '' }, g);
    if (p.hline.label) h.label(fig, g, { x: p.hline.labelX != null ? sx(p.hline.labelX) : 6,
                                         y: sy(p.hline.at) + (p.hline.below ? 18 : -11), 'class': 'kit-cap' }, p.hline.label, { near: 20, lead: false });
  }
  var drawn = curves.map(function (c, i) {
    var d = c.pts.map(function (q, k) { return (k ? 'L' : 'M') + sx(q[0]).toFixed(1) + ' ' + sy(q[1]).toFixed(1); }).join(' ');
    var cg = h.el('g', { 'class': 'kit-curve-chart-c' + (i % 3) }, g);
    var path = h.el('path', { d: d, 'class': 'kit-curve-chart-line', 'data-may-cross': '' }, cg);
    var first = c.pts[0], dot = h.el('circle', { cx: sx(first[0]), cy: sy(first[1]), r: 5, 'class': 'kit-curve-chart-dot' }, cg);
    var lab = null;
    if (c.label) {
      var at = c.labelAt || c.pts[c.pts.length - 1];
      lab = h.el('text', { x: sx(at[0]), y: sy(at[1]), 'text-anchor': c.anchor || 'start', 'class': 'kit-cap' }, cg, c.label);
    }
    if (c.bp) {
      var bl = h.el('text', { x: sx(first[0]) + (c.bpDx || 0), y: sy(first[1]) + (c.bpDy != null ? c.bpDy : 22), 'text-anchor': 'middle', 'class': 'kit-num' }, cg, c.bp);
      lab = lab || bl; c._bp = bl;
    }
    var len = 0; try { len = path.getTotalLength(); } catch (e) { len = 0; }
    return { path: path, dot: dot, lab: lab, bpl: c._bp, len: len || 1000, g: cg };
  });
  var mark = null;
  if (pt) {
    mark = h.el('g', { 'class': 'kit-curve-chart-point' }, g);
    var gv = h.el('line', { 'class': 'kit-curve-chart-guide', 'data-may-cross': '' }, mark);
    var gh = h.el('line', { 'class': 'kit-curve-chart-guide', 'data-may-cross': '' }, mark);
    var pd = h.el('circle', { r: 7, 'class': 'kit-curve-chart-pdot' }, mark);
    var pl = h.el('text', { 'class': 'kit-num', 'text-anchor': 'start' }, h.label(fig, mark, {}, '', { near: 30, lead: false }));   // the layout keeps the reading off the curves
  }
  function along(c, xv) {                              // the curve's value at xv, straight between its points
    var q = curves[c].pts;
    for (var k = 1; k < q.length; k++) if (xv <= q[k][0]) {
      var f = (xv - q[k - 1][0]) / (q[k][0] - q[k - 1][0]); return q[k - 1][1] + f * (q[k][1] - q[k - 1][1]);
    }
    return q[q.length - 1][1];
  }
  part.render = function (v) {
    var n = curves.length;
    drawn.forEach(function (c, i) {
      var k = h.clamp(v - i, 0, 1);
      c.path.setAttribute('stroke-dasharray', c.len);
      c.path.setAttribute('stroke-dashoffset', (c.len * (1 - k)).toFixed(1));
      c.g.style.opacity = k > 0.001 ? '1' : '0';
      c.dot.style.opacity = k > 0.001 ? '1' : '0';
      if (c.lab) c.lab.style.opacity = k > 0.95 ? '1' : '0';
      if (c.bpl) c.bpl.style.opacity = k > 0.95 ? '1' : '0';
    });
    if (mark) {
      var m = h.clamp(v - n, 0, 1);
      mark.style.opacity = m > 0.001 ? '1' : '0';
      var xv = pt.from + (pt.to - pt.from) * m, yv = along(pt.curve, xv), x = sx(xv), y = sy(yv);
      gv.setAttribute('x1', x); gv.setAttribute('x2', x); gv.setAttribute('y1', y); gv.setAttribute('y2', ht);
      gh.setAttribute('x1', 0); gh.setAttribute('x2', x); gh.setAttribute('y1', y); gh.setAttribute('y2', y);
      pd.setAttribute('cx', x); pd.setAttribute('cy', y);
      var left = pt.labelSide === 'left';
      pl.setAttribute('text-anchor', left ? 'end' : 'start');
      pl.setAttribute('x', left ? x - 14 : x + 12); pl.setAttribute('y', left ? y - 12 : y + 5);
      // the reading is shown where the point stops - a moving number would sit on the labels it passes
      pl.textContent = m > 0.97 ? (pt.label || h.fmt(xv, { decimals: 0, unit: X.unit }) + ' · ' + h.fmt(yv, { decimals: 1, unit: Y.unit })) : '';
    }
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M04",
  course: 'IGF Basic', module: 'M04', made: '2026-10-16',
  why: 'M04 s03: vapour pressure against temperature for methane, propane and methanol - each curve meets the 1 bar line at its boiling point, then a point slides up the propane curve to 20 °C and reads about 8 bar (SPEC.md family 6: "curve with a moving point")',
  value: '0..n: curve k draws itself from k to k+1; then n..n+1 the point slides along point.curve from point.from to point.to',
  css: '.kit-curve-chart-grid{stroke:var(--line-d);stroke-width:1}.kit-curve-chart-frame{fill:none;stroke:var(--faint-d);stroke-width:1.5}.kit-curve-chart-hline{stroke:var(--dim-d);stroke-width:2;stroke-dasharray:8 6}.kit-curve-chart-line{fill:none;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}.kit-curve-chart-c0 .kit-curve-chart-line{stroke:var(--blue)}.kit-curve-chart-c0 .kit-curve-chart-dot{fill:var(--blue)}.kit-curve-chart-c1 .kit-curve-chart-line{stroke:var(--txt-d);stroke-dasharray:14 7}.kit-curve-chart-c1 .kit-curve-chart-dot{fill:var(--txt-d)}.kit-curve-chart-c2 .kit-curve-chart-line{stroke:var(--cold);stroke-width:5;stroke-dasharray:1 8}.kit-curve-chart-c2 .kit-curve-chart-dot{fill:var(--cold)}.kit-curve-chart-guide{stroke:var(--blue);stroke-width:1.5;stroke-dasharray:4 4}.kit-curve-chart-pdot{fill:var(--txt-d);stroke:var(--blue);stroke-width:3}',
  example: { size: [420, 260], parts: [
    { id: 'VP', type: 'curve_chart', x: 50, y: 30, w: 340, h: 180,
      xaxis: { min: -60, max: 60, every: 20, unit: '°C', label: 'temperature °C' }, yaxis: { min: 0, max: 16, every: 4, unit: 'bar', label: 'bar' },
      hline: { at: 1, label: '1 bar', labelX: -58 },
      curves: [{ label: 'propane', pts: [[-42, 1], [0, 4.7], [20, 8.4], [40, 13.7]], labelAt: [42, 14.5] }],
      point: { curve: 0, from: -42, to: 20, label: '20 °C · about 8 bar' } } ],
    steps: [ { title: 'The curve', play: [['VP', 1, 1500]] }, { title: 'Read it at 20 °C', play: [['VP', 2, 1500]] } ] }
});
/* end kit-part */
/* kit-part: fan */
KIT.define('fan', function (fig, part, g, p) {
  var h = KIT.h, r = p.r || 26, half = (p.len || 170) / 2, wh = r + 9;
  var deg = { right: 0, down: 90, left: 180, up: 270 }[p.dir || 'right'] || 0, vert = deg === 90 || deg === 270;
  var sym = h.el('g', { transform: deg ? 'rotate(' + deg + ')' : null }, g);
  [-1, 1].forEach(function (s) {
    h.el('rect', { x: -half, y: s < 0 ? -wh - 6 : wh, width: 2 * half, height: 6, rx: 2, 'class': 'kit-steel' }, sym);
  });
  h.el('circle', { r: r + 3, 'class': 'kit-shell' }, sym);
  var rotor = h.el('g', { 'class': 'kit-fan-rotor' }, sym);
  [0, 90, 180, 270].forEach(function (a) {
    h.el('path', { d: 'M0 0 Q ' + (r * 0.5) + ' ' + (-r * 0.62) + ' ' + (r * 0.88) + ' ' + (-r * 0.12) + ' Q ' + (r * 0.42) + ' ' + (r * 0.12) + ' 0 0 Z',
      transform: 'rotate(' + a + ')', 'class': 'kit-fan-blade' }, rotor);
  });
  h.el('circle', { r: 5, 'class': 'kit-fan-hub' }, sym);
  var air = h.el('g', {}, sym);
  [-15, 0, 15].forEach(function (y) {
    [[-half + 10, -r - 10], [r + 10, half - 10]].forEach(function (s) {
      h.el('line', { x1: s[0], y1: y, x2: s[1] - 7, y2: y, 'class': 'kit-fan-air' }, air);
      h.el('path', { d: 'M' + (s[1] - 8) + ' ' + (y - 5) + ' L' + s[1] + ' ' + y + ' L' + (s[1] - 8) + ' ' + (y + 5), 'class': 'kit-fan-head' }, air);
    });
  });
  var ex = vert ? wh + 6 : half, ey = vert ? half : wh + 6;
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;           // its name and its state move together
  var lx = vert ? ex + 14 : 0, ly = vert ? -4 : ey + 22, anc = vert ? 'start' : 'middle';
  var nl = p.label ? h.lines(lg, { x: lx, y: ly, 'text-anchor': anc, 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state === false ? null : h.el('text', { x: lx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': anc, 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1), on = k > 0.02;
    air.style.opacity = on ? (0.35 + 0.65 * k).toFixed(2) : '0';
    if (on) rotor.style.animationDuration = (1.1 - 0.8 * k).toFixed(2) + 's';
    g.classList.toggle('kit-fan-on', on);
    if (st) st.textContent = on ? 'RUNNING' : 'STOPPED';
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M05 (machinery space ventilation) and M11 (enclosed-space entry): a mechanical ventilation fan in a duct or wall opening - the arrows show which way it moves the air, and no arrows means no air',
  value: '0 stopped .. 1 running: blades turn faster, the air arrows flow in the direction dir (right, left, up, down); RUNNING or STOPPED under the name',
  css: '.kit-fan-blade{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:1.5;stroke-linejoin:round}' +
    '.kit-fan-hub{fill:var(--dim-d)}' +
    '.kit-fan-air{stroke:var(--cold);stroke-width:3;stroke-dasharray:10 8;stroke-linecap:round}' +
    '.kit-fan-head{fill:none;stroke:var(--cold);stroke-width:3;stroke-linecap:round;stroke-linejoin:round}' +
    '.kit-fan-on .kit-fan-rotor{animation:kit-fan-spin .6s linear infinite}' +
    '.kit-fan-on .kit-fan-air{animation:kit-fan-air .7s linear infinite}' +
    '.kit-fan-on .kit-state{fill:var(--txt-d)}' +
    '@keyframes kit-fan-spin{to{transform:rotate(360deg)}}@keyframes kit-fan-air{to{stroke-dashoffset:-18}}',
  example: { size: [320, 150], parts: [
    { id: 'F', type: 'fan', x: 160, y: 56, dir: 'right', r: 34, len: 300, label: 'extract fan' } ],
    steps: [ { title: 'The fan runs - the air moves along the arrows', play: [['F', 1, 1500]] },
             { title: 'The fan stops - no air moves', play: [['F', 0, 1000]] } ] }
});
/* end kit-part */
/* kit-part: spray */
KIT.define('spray', function (fig, part, g, p) {
  var h = KIT.h, kind = p.nozzle || 'monitor', agent = p.agent || 'water', reach = p.reach || (kind === 'sprinkler' ? 90 : 130);
  var ang = p.angle != null ? p.angle : (kind === 'sprinkler' ? -90 : kind === 'hand' ? 12 : 22);
  var spread = ({ water: 6, foam: 14, powder: 20 }[agent] || 10) * (kind === 'hand' ? 1.4 : 1);
  if (kind === 'sprinkler') spread = 38;
  var a = ang * Math.PI / 180, seed = 11, i;
  function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
  if (kind === 'monitor') {                                     // the pedestal stays upright while the barrel turns
    var px = -30 * Math.cos(a), py = 30 * Math.sin(a);
    h.el('path', { d: 'M' + px.toFixed(1) + ' ' + py.toFixed(1) + ' V' + (py + 36).toFixed(1), 'class': 'kit-pipe-s' }, g);
    h.el('path', { d: 'M' + (px - 18).toFixed(1) + ' ' + (py + 36).toFixed(1) + ' H' + (px + 18).toFixed(1), 'class': 'kit-flange' }, g);
  }
  var sym = h.el('g', { transform: ang ? 'rotate(' + (-ang) + ')' : null }, g);
  var cone = h.el('g', { 'class': 'kit-spray-cone' }, sym);
  [-spread, spread].forEach(function (d) {
    var e = h.polar(reach, d);
    h.el('line', { x1: 0, y1: 0, x2: e[0].toFixed(1), y2: e[1].toFixed(1) }, cone);
  });
  var a0 = h.polar(reach, -spread), a1 = h.polar(reach, spread);
  h.el('path', { d: 'M' + a0[0].toFixed(1) + ' ' + a0[1].toFixed(1) + ' A' + reach + ' ' + reach + ' 0 0 1 ' + a1[0].toFixed(1) + ' ' + a1[1].toFixed(1) }, cone);
  var streaks = [], dots = [];
  if (agent === 'water') {
    var ns = kind === 'sprinkler' ? 9 : 5;
    for (i = 0; i < ns; i++) {
      var dd = -spread + 2 * spread * i / (ns - 1);
      streaks.push({ n: h.el('line', { 'class': 'kit-spray-streak', style: 'animation-delay:' + (-0.1 * i).toFixed(2) + 's' }, sym),
                     d: dd, len: reach * (0.8 + 0.2 * rnd()) });
    }
  } else {
    var nd = agent === 'powder' ? 70 : 24, tries = 0;
    while (dots.length < nd && tries++ < 3000) {                  // no two grains on one another
      var t = Math.pow(rnd(), 0.85), pt = h.polar(10 + t * (reach - 10), (rnd() * 2 - 1) * spread * Math.min(1, 0.25 + t * 1.1));
      var rr = agent === 'powder' ? 1.8 + 2.2 * t : 3 + 6 * t;
      if (dots.some(function (o) { return Math.sqrt(Math.pow(o.x - pt[0], 2) + Math.pow(o.y - pt[1], 2)) < o.r + rr + 4; })) continue;
      dots.push({ t: t, x: pt[0], y: pt[1], r: rr, n: h.el('circle', { cx: pt[0].toFixed(1), cy: pt[1].toFixed(1), r: rr.toFixed(1),
        'class': agent === 'powder' ? 'kit-spray-dot' : 'kit-spray-foam', style: 'animation-delay:' + (-rnd()).toFixed(2) + 's' }, sym) });
    }
  }
  if (kind === 'monitor') {
    h.el('path', { d: 'M-48 -6 H-10 L0 -10 V10 L-10 6 H-48 Z', 'class': 'kit-steel' }, sym);
    h.el('circle', { cx: -30, cy: 0, r: 5, 'class': 'kit-spray-pivot' }, sym);
  } else if (kind === 'hand') {
    h.el('path', { d: 'M-34 0 C-52 0 -52 26 -78 26', 'class': 'kit-pipe-s' }, sym);
    h.el('path', { d: 'M-34 -5 H-8 L0 -9 V9 L-8 5 H-34 Z', 'class': 'kit-steel' }, sym);
    h.el('path', { d: 'M-24 5 L-28 20 H-19 L-16 5', 'class': 'kit-steel' }, sym);
  } else {
    h.el('line', { x1: -42, y1: 0, x2: -10, y2: 0, 'class': 'kit-pipe-s' }, sym);
    h.el('path', { d: 'M-12 -9 L-2 -13 M-12 9 L-2 13', 'class': 'kit-flange' }, sym);
    h.el('line', { x1: 0, y1: -13, x2: 0, y2: 13, 'class': 'kit-flange' }, sym);
    h.el('circle', { cx: -7, cy: 0, r: 3.5, 'class': 'kit-spray-pivot' }, sym);
  }
  var rear = { monitor: 48, hand: 60, sprinkler: 42 }[kind] || 48;
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;
  var lx = -rear * Math.cos(a) - 8, ly = rear * Math.sin(a) - 14;
  var nl = p.label ? h.lines(lg, { x: lx.toFixed(1), y: ly.toFixed(1), 'text-anchor': 'end', 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state === false ? null : h.el('text', { x: lx.toFixed(1), y: ly.toFixed(1), dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'end', 'class': 'kit-state' }, lg);
  var word = { powder: 'DRY POWDER', water: 'WATER', foam: 'FOAM' }[agent] || 'AGENT';
  var rl = null;
  if (p.reachLabel) {
    var re = h.polar(reach, 0);
    rl = h.label(fig, g, { x: 0, y: 0, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.reachLabel);
    rl.setAttribute('transform', 'translate(' + (re[0] * Math.cos(a) + 0).toFixed(1) + ' ' + (-re[0] * Math.sin(a) - 14).toFixed(1) + ')');
  }
  part.render = function (v) {
    var k = h.clamp(v, 0, 1), on = k > 0.02;
    streaks.forEach(function (s) {
      var e0 = h.polar(8, s.d), e1 = h.polar(Math.max(9, s.len * k), s.d);
      s.n.setAttribute('x1', e0[0].toFixed(1)); s.n.setAttribute('y1', e0[1].toFixed(1));
      s.n.setAttribute('x2', e1[0].toFixed(1)); s.n.setAttribute('y2', e1[1].toFixed(1));
      s.n.style.opacity = on ? '1' : '0';
    });
    dots.forEach(function (d) { d.n.style.opacity = h.clamp((k - d.t * 0.85) / 0.15, 0, 1).toFixed(2); });
    cone.style.opacity = (0.75 + 0.25 * k).toFixed(2);          // the reach is drawn faintly even at rest
    if (rl) rl.style.opacity = k > 0.9 ? '1' : '0';
    g.classList.toggle('kit-spray-on', on);
    if (st) st.textContent = word + (on ? ' ON' : ' OFF');
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M13 fixed dry-powder installation, powder monitors and hand hoses: what comes out of the nozzle, which way and how far - a cone of powder, water or foam of a given reach and angle',
  value: '0..1 how much is discharged: the spray grows out of the nozzle to its reach (nozzle monitor, hand or sprinkler; agent powder, water or foam; angle in degrees above horizontal, -90 = down)',
  css: '.kit-spray-cone line,.kit-spray-cone path{fill:none;stroke:var(--dim-d);stroke-width:1.5;stroke-dasharray:4 5}' +
    '.kit-spray-pivot{fill:var(--deep);stroke:var(--dim-d);stroke-width:2}' +
    '.kit-spray-streak{stroke:var(--cold);stroke-width:3;stroke-linecap:round;stroke-dasharray:9 7;opacity:0}' +
    '.kit-spray-dot{fill:var(--txt-d)}' +
    '.kit-spray-foam{fill:var(--cold);fill-opacity:.25;stroke:var(--txt-d);stroke-width:1.5}' +
    '.kit-spray-on .kit-spray-streak{animation:kit-spray-run .5s linear infinite}' +
    '.kit-spray-on .kit-spray-dot,.kit-spray-on .kit-spray-foam{animation:kit-spray-drift .9s linear infinite}' +
    '.kit-spray-on .kit-state{fill:var(--txt-d)}' +
    '@keyframes kit-spray-run{to{stroke-dashoffset:-16}}@keyframes kit-spray-drift{to{transform:translateX(12px)}}',
  example: { size: [640, 330], parts: [
    { id: 'M', type: 'spray', x: 100, y: 235, nozzle: 'monitor', agent: 'powder', angle: 12, reach: 270, label: 'powder monitor' },
    { id: 'H', type: 'spray', x: 410, y: 70, nozzle: 'hand', agent: 'foam', angle: -12, reach: 200, label: 'foam hose' },
    { id: 'S', type: 'spray', x: 560, y: 250, nozzle: 'sprinkler', agent: 'water', label: 'sprinkler' } ],
    steps: [ { title: 'The monitor discharges powder over its reach', play: [['M', 1, 2200]] },
             { title: 'A hand hose lays foam', play: [['H', 1, 1800]] },
             { title: 'The sprinkler wets the area below it', play: [['S', 1, 1800]] } ] }
});
/* end kit-part */
/* kit-part: gas_cylinder */
KIT.define('gas_cylinder', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 56, ht = p.h || 150, cid = fig.uid + '-' + (p.id || 'gc') + '-cyl';
  function shell(wd) {
    var hw = wd / 2;
    return 'M' + (-hw) + ' 0 V' + (-(ht - hw)) + ' A' + hw + ' ' + hw + ' 0 0 1 ' + hw + ' ' + (-(ht - hw)) + ' V0 Z';
  }
  var clip = h.el('path', { d: shell(w) }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var body = h.el('path', { d: shell(w), 'class': 'kit-vessel' }, g);
  var fill = h.el('g', { 'clip-path': 'url(#' + cid + ')' }, g);
  var gas = h.el('rect', { x: -w / 2, width: w, 'class': 'kit-gas-cylinder-fill', 'data-low-contrast': '' }, fill);   // the fill is quiet on purpose: the surface line above it carries the contrast
  var top = h.el('line', { x1: -w / 2, x2: w / 2, 'class': 'kit-surface' }, fill);
  var bodyLine = h.el('path', { d: shell(w), 'class': 'kit-shell-o' }, g);
  h.el('line', { x1: -w / 2 - 4, y1: 0, x2: w / 2 + 4, y2: 0, 'class': 'kit-flange' }, g);
  h.el('rect', { x: -7, y: -ht - 8, width: 14, height: 10, 'class': 'kit-steel' }, g);                 // neck
  h.el('rect', { x: -11, y: -ht - 25, width: 22, height: 17, rx: 3, 'class': 'kit-steel' }, g);       // valve body
  h.el('rect', { x: 11, y: -ht - 21, width: 11, height: 7, rx: 2, 'class': 'kit-steel' }, g);         // outlet
  h.el('line', { x1: 0, y1: -ht - 25, x2: 0, y2: -ht - 31, 'class': 'kit-stem' }, g);
  h.el('line', { x1: -13, y1: -ht - 31, x2: 13, y2: -ht - 31, 'class': 'kit-flange' }, g);           // hand wheel
  var plate = p.gas ? h.el('rect', { x: -20, y: -ht * 0.62 - 11, width: 40, height: 22, rx: 3, 'class': 'kit-gas-cylinder-plate' }, g) : null;
  var cap = p.gas ? h.el('text', { x: 0, y: -ht * 0.62 + 4.5, 'text-anchor': 'middle', 'class': 'kit-tl' }, g, p.gas) : null;
  if (p.label) h.label(fig, g, { x: 0, y: 24, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  fig.fit(function (k) {                                // the bottle is as wide as its gas word needs, 8 a side
    var tw = cap ? h.widest(cap, [p.gas]) : 0, pw = tw + 16, ph = 22 * k, wd = Math.max(w, pw + 12);
    [clip, body, bodyLine].forEach(function (n) { n.setAttribute('d', shell(wd)); });
    gas.setAttribute('x', -wd / 2); gas.setAttribute('width', wd);
    top.setAttribute('x1', -wd / 2); top.setAttribute('x2', wd / 2);
    if (cap) {
      plate.setAttribute('x', -pw / 2); plate.setAttribute('width', pw); plate.setAttribute('height', ph);
      plate.setAttribute('y', -ht * 0.62 - ph / 2); cap.setAttribute('y', -ht * 0.62 + 4.5 * k);
    }
  });
  part.render = function (v) {
    var lv = h.clamp(v, 0, 1) * (ht - 8);
    gas.setAttribute('y', (-lv).toFixed(1)); gas.setAttribute('height', (lv + 2).toFixed(1));
    top.setAttribute('y1', (-lv).toFixed(1)); top.setAttribute('y2', (-lv).toFixed(1));
    top.style.opacity = lv > 2 ? '1' : '0';
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M13 nitrogen cylinders that drive a dry-powder installation, and M10 breathing-air cylinders (SCBA): a compressed-gas bottle with its valve, shown with how much pressure is left in it',
  value: 'how full the cylinder is (its pressure), 0..1; it stands on its base point (x, y); w and h size it, gas is the short word on the bottle (N2, CO2, AIR)',
  css: '.kit-gas-cylinder-fill{fill:var(--cold);opacity:.5}.kit-gas-cylinder-plate{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}',
  example: { size: [640, 300], parts: [
    { id: 'A', type: 'gas_cylinder', x: 100, y: 240, w: 84, h: 180, gas: 'N2', label: 'nitrogen', value: 1 },
    { id: 'B', type: 'gas_cylinder', x: 240, y: 240, w: 84, h: 180, gas: 'N2', label: 'nitrogen', value: 1 },
    { id: 'C', type: 'gas_cylinder', x: 380, y: 240, w: 84, h: 180, gas: 'CO2', label: 'carbon dioxide', value: 1 },
    { id: 'D', type: 'gas_cylinder', x: 520, y: 240, w: 84, h: 180, gas: 'AIR', label: 'breathing air', value: 0.6 } ],
    steps: [ { title: 'The nitrogen cylinders are used - their pressure falls', play: [['A', 0.45, 2800], ['B', 0.45, 2800]] },
             { title: 'The breathing-air cylinder is refilled', play: [['D', 1, 1800]] } ] }
});
/* end kit-part */
/* kit-part: push_button */
KIT.define('push_button', function (fig, part, g, p) {
  /* SIZE (2.49.2): "h" is the height of the wall plate, 120 units unless the spec says (it was a fixed 182, so two did not
     stack in a 390-high figure). The picture is drawn at h/182 of its first size; its words (the tag, the name, READY /
     PRESSED) keep their own size and sit under it, and the plate grows to hold the tag when the words are grown. */
  var h = KIT.h, S = h.clamp((p.h || 120) / 182, 0.3, 1.5);
  var plate = h.el('rect', { rx: 8, 'class': 'kit-push-button-plate' }, g);   // the wall plate it is mounted on
  var art = h.el('g', { transform: 'scale(' + S.toFixed(4) + ')' }, g);
  h.el('line', { x1: -38, y1: 10, x2: -38, y2: -36, 'class': 'kit-probe' }, art);
  h.el('line', { x1: 38, y1: 10, x2: 38, y2: -36, 'class': 'kit-probe' }, art);
  h.el('rect', { x: -44, y: 10, width: 88, height: 30, rx: 5, 'class': 'kit-vessel' }, art);
  h.el('rect', { x: -7, y: -2, width: 14, height: 13, 'class': 'kit-steel' }, art);
  var cap = h.el('g', {}, art);
  h.el('path', { d: 'M-30 2 C-30 -28 30 -28 30 2 Z', 'class': 'kit-push-button-cap' }, cap);
  h.el('line', { x1: -33, y1: 2, x2: 33, y2: 2, 'class': 'kit-flange' }, cap);
  var lid = h.el('g', {}, art);
  h.el('rect', { x: -38, y: -41, width: 76, height: 6, rx: 3, 'class': 'kit-push-button-lid' }, lid);
  var tagBox = h.el('rect', { x: -22, y: 46 * S, width: 44, height: 22, rx: 4, 'class': 'kit-push-button-tag' }, g);
  var tagTxt = h.el('text', { x: 0, y: 46 * S + 15, 'text-anchor': 'middle', 'class': 'kit-tl' }, g, p.tag || 'ESD');
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;
  var ly0 = 46 * S + 22 + 8 + 12.5 + 8;
  var nl = p.label ? h.lines(lg, { x: 0, y: ly0, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state === false ? null : h.el('text', { x: 0, y: ly0, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
  fig.fit(function (k) {                                // the tag plate is as wide as its words need, 8 a side, and as tall
    var wd = Math.max(44, h.widest(tagTxt, [p.tag || 'ESD']) + 16), th = 22 * k, ty = 46 * S;
    var bottom = Math.max(80 * S, ty + th + 8), pw = Math.max(120 * S, wd + 16);
    plate.setAttribute('x', -pw / 2); plate.setAttribute('y', -102 * S); plate.setAttribute('width', pw); plate.setAttribute('height', bottom + 102 * S);
    tagBox.setAttribute('x', -wd / 2); tagBox.setAttribute('width', wd); tagBox.setAttribute('height', th);
    tagTxt.setAttribute('y', ty + th / 2 + 4.5 * k);
    if (lg) [].forEach.call(lg.querySelectorAll('text'), function (t) { t.setAttribute('y', bottom + 8 + 12.5 * k); });
  });
  part.render = function (v) {
    var c = h.clamp(v, 0, 1), up = h.clamp(c / 0.4, 0, 1), dn = h.clamp((c - 0.4) / 0.6, 0, 1);
    lid.setAttribute('transform', 'rotate(' + (-55 * up).toFixed(1) + ' -38 -38)');
    cap.setAttribute('transform', 'translate(0 ' + (9 * dn).toFixed(1) + ')');
    g.classList.toggle('kit-push-button-on', c > 0.5);
    if (st) st.textContent = c > 0.5 ? 'PRESSED' : 'READY';
  };
}, {
  family: 'instruments',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M14 the ESD panel: an emergency-stop mushroom push button under a hinged guard, with its tag - the guard lifts, the button goes down and turns red, the word PRESSED shows (the shutdown it starts is drawn by the other parts)',
  value: '0 ready, 1 pressed: the guard lifts over 0..0.4, the button goes down over 0.4..1 and turns red (trip); READY or PRESSED under the name; option h: the height of the wall plate, 120 units (2.49.2; it was a fixed 182, so two did not stack in a 390-high figure) - the words under it keep their size',
  css: '.kit-push-button-plate{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:2}' +
    '.kit-push-button-cap{fill:var(--cold);fill-opacity:.45;stroke:var(--dim-d);stroke-width:2}' +
    '.kit-push-button-lid{fill:var(--cold);fill-opacity:.2;stroke:var(--dim-d);stroke-width:2}' +
    '.kit-push-button-tag{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}' +
    '.kit-push-button-on .kit-push-button-cap{fill:var(--warn-d);fill-opacity:.9;stroke:var(--warn-d)}' +
    '.kit-push-button-on .kit-state{fill:var(--warn-d)}',
  example: { size: [640, 250], parts: [
    { id: 'A', type: 'push_button', x: 110, y: 114, tag: 'ESD 1', label: 'navigation bridge' },
    { id: 'B', type: 'push_button', x: 320, y: 114, tag: 'ESD 2', label: 'engine control room' },
    { id: 'C', type: 'push_button', x: 530, y: 114, tag: 'ESD 3', label: 'bunker station' } ],
    steps: [ { title: 'The guard is lifted and the button pressed - shutdown starts', play: [['C', 1, 1800]] },
             { title: 'Reset - ready again', play: [['C', 0, 900]] } ] }
});
/* end kit-part */
/* kit-part: person */
KIT.define('person', function (fig, part, g, p) {
  /* WORDS (2.49.2): each item is named by default (NAMES), and "labels" says the words a slide uses instead, per item -
     {"visor": "GOGGLES", "scba": "BREATHING APPARATUS"} (or a list in the order of "wear"; "names" is the same, kept for the
     specs that have it; "labels": false names none). More to wear: goggles, apron, respirator. */
  var h = KIT.h, S = p.scale || 1, wear = p.wear || [], names = {};
  var NAMES = { helmet: 'HELMET', visor: 'VISOR', goggles: 'GOGGLES', respirator: 'RESPIRATOR', gloves: 'GLOVES', suit: 'SUIT',
                apron: 'APRON', boots: 'BOOTS', scba: 'SCBA' };
  var POS = { helmet: [26, -166, 'start'], visor: [-24, -156, 'end'], goggles: [-22, -151, 'end'], respirator: [-22, -138, 'end'],
              suit: [40, -104, 'start'], apron: [-34, -108, 'end'], gloves: [-42, -72, 'end'], boots: [26, -8, 'start'],
              scba: [40, -136, 'start'] };
  [p.names, p.labels].forEach(function (src) {
    if (src && typeof src === 'object' && !Array.isArray(src)) for (var key in src) names[key] = src[key];
    else if (Array.isArray(src)) src.forEach(function (txt, i) { if (wear[i]) names[wear[i]] = txt; });
  });
  var b = h.el('g', { transform: S === 1 ? null : 'scale(' + S + ')' }, g), nodes = {};
  function put(item, node) { (nodes[item] = nodes[item] || []).push(node); return node; }
  function use(item) { return wear.indexOf(item) >= 0; }
  if (use('scba')) {                                                   // the bottle behind the shoulder
    var bk = h.el('g', {}, b);
    h.el('rect', { x: 14, y: -150, width: 15, height: 62, rx: 6, 'class': 'kit-person-ppe' }, bk);
    h.el('rect', { x: 18, y: -157, width: 7, height: 8, rx: 1, 'class': 'kit-person-ppe' }, bk);
    put('scba', bk);
  }
  h.el('line', { x1: -9, y1: -80, x2: -11, y2: -12, 'class': 'kit-person-leg' }, b);
  h.el('line', { x1: 9, y1: -80, x2: 11, y2: -12, 'class': 'kit-person-leg' }, b);
  h.el('line', { x1: -22, y1: -128, x2: -31, y2: -86, 'class': 'kit-person-arm' }, b);
  h.el('line', { x1: 22, y1: -128, x2: 31, y2: -86, 'class': 'kit-person-arm' }, b);
  h.el('rect', { x: -21, y: -135, width: 42, height: 56, rx: 10, 'class': 'kit-person-body' }, b);
  h.el('circle', { cx: 0, cy: -150, r: 13, 'class': 'kit-person-body' }, b);
  [-1, 1].forEach(function (s) {
    h.el('circle', { cx: 31 * s, cy: -82, r: 5.5, 'class': 'kit-person-body' }, b);
    h.el('ellipse', { cx: 13 * s, cy: -5, rx: 9, ry: 4.5, 'class': 'kit-person-body' }, b);
  });
  if (use('suit')) {
    var su = h.el('g', {}, b);
    h.el('line', { x1: -9, y1: -80, x2: -11, y2: -12, 'class': 'kit-person-suit-l' }, su);
    h.el('line', { x1: 9, y1: -80, x2: 11, y2: -12, 'class': 'kit-person-suit-l' }, su);
    h.el('line', { x1: -22, y1: -128, x2: -31, y2: -86, 'class': 'kit-person-suit-a' }, su);
    h.el('line', { x1: 22, y1: -128, x2: 31, y2: -86, 'class': 'kit-person-suit-a' }, su);
    h.el('rect', { x: -21, y: -135, width: 42, height: 56, rx: 10, 'class': 'kit-person-suit-t' }, su);
    h.el('line', { x1: 0, y1: -134, x2: 0, y2: -82, 'class': 'kit-person-zip' }, su);
    put('suit', su);
  }
  if (use('boots')) {
    var bo = h.el('g', {}, b);
    [-1, 1].forEach(function (s) { h.el('rect', { x: s < 0 ? -22 : 7, y: -17, width: 15, height: 15, rx: 4, 'class': 'kit-person-ppe' }, bo); });
    put('boots', bo);
  }
  if (use('gloves')) {
    var gl = h.el('g', {}, b);
    [-1, 1].forEach(function (s) { h.el('circle', { cx: 31 * s, cy: -82, r: 8, 'class': 'kit-person-ppe' }, gl); });
    put('gloves', gl);
  }
  if (use('apron')) {                                                  // over the front of the body, held by a neck loop
    var ap = h.el('g', {}, b);
    h.el('path', { d: 'M-8 -131 Q0 -142 8 -131', 'class': 'kit-person-hose' }, ap);
    h.el('rect', { x: -15, y: -132, width: 30, height: 50, rx: 4, 'class': 'kit-person-apron' }, ap);
    put('apron', ap);
  }
  if (use('scba')) {
    var sf = h.el('g', {}, b);
    h.el('line', { x1: -15, y1: -132, x2: 15, y2: -88, 'class': 'kit-person-strap' }, sf);
    h.el('line', { x1: 15, y1: -132, x2: -15, y2: -88, 'class': 'kit-person-strap' }, sf);
    h.el('path', { d: 'M10 -141 C22 -128 36 -140 24 -150', 'class': 'kit-person-hose' }, sf);
    h.el('path', { d: 'M-10 -148 H10 V-142 Q0 -134 -10 -142 Z', 'class': 'kit-person-ppe' }, sf);
    put('scba', sf);
  }
  if (use('helmet')) {
    var he = h.el('g', {}, b);
    h.el('path', { d: 'M-16 -151 C-16 -178 16 -178 16 -151 Z', 'class': 'kit-person-ppe' }, he);
    h.el('line', { x1: -21, y1: -151, x2: 21, y2: -151, 'class': 'kit-person-brim' }, he);
    put('helmet', he);
  }
  if (use('visor')) {
    var vi = h.el('g', {}, b);
    h.el('path', { d: 'M-15 -160 H15 V-139 Q0 -134 -15 -139 Z', 'class': 'kit-person-visor' }, vi);
    put('visor', vi);
  }
  if (use('goggles')) {                                                // two lenses on a band across the eyes
    var go = h.el('g', {}, b);
    h.el('line', { x1: -14, y1: -152, x2: 14, y2: -152, 'class': 'kit-person-strap' }, go);
    [-6, 6].forEach(function (x) { h.el('circle', { cx: x, cy: -152, r: 5, 'class': 'kit-person-visor' }, go); });
    put('goggles', go);
  }
  if (use('respirator')) {                                             // a half mask over nose and mouth, with two filters
    var re = h.el('g', {}, b);
    h.el('path', { d: 'M-9 -147 H9 Q11 -140 0 -136 Q-11 -140 -9 -147 Z', 'class': 'kit-person-ppe' }, re);
    [-1, 1].forEach(function (s) { h.el('circle', { cx: 10 * s, cy: -141, r: 3.5, 'class': 'kit-person-ppe' }, re); });
    put('respirator', re);
  }
  var tags = {};
  if (p.names !== false && p.labels !== false) wear.forEach(function (item) {
    var q = POS[item], txt = names[item] || NAMES[item];
    if (!q || !txt) return;
    tags[item] = h.label(fig, g, { x: q[0] * S, y: q[1] * S, 'text-anchor': q[2], 'class': 'kit-cap' }, txt);
  });
  if (p.label) h.label(fig, g, { x: 0, y: 24 * S, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    wear.forEach(function (item, i) {
      var k = h.clamp(v - i, 0, 1);
      (nodes[item] || []).forEach(function (n) { n.style.opacity = k.toFixed(2); });
      if (tags[item]) tags[item].style.opacity = k > 0.95 ? '1' : '0';
    });
  };
}, {
  family: 'procedures',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M10 PPE for gas work, M11 the attendant and the entrant, M15 spill response: a plain standing worker pictogram (not a drawing of real equipment) that puts on its protective equipment one item at a time',
  value: '0..n: item k of wear appears (and its name) from k to k+1; wear is any of helmet, visor, goggles, respirator, gloves, suit, apron, boots, scba, in the order they are put on; option labels (or names): {item: words} names an item in the slide\'s own words - {"visor": "GOGGLES"} - or a list in the order of wear, false for no names (2.49.2)',
  css: '.kit-person-body{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}' +
    '.kit-person-leg{stroke:var(--dim-d);stroke-width:11;stroke-linecap:round}' +
    '.kit-person-arm{stroke:var(--dim-d);stroke-width:9;stroke-linecap:round}' +
    '.kit-person-ppe{fill:var(--cold);fill-opacity:.55;stroke:var(--txt-d);stroke-width:2;stroke-linejoin:round}' +
    '.kit-person-suit-l{stroke:var(--cold);stroke-opacity:.6;stroke-width:15;stroke-linecap:round}' +
    '.kit-person-suit-a{stroke:var(--cold);stroke-opacity:.6;stroke-width:13;stroke-linecap:round}' +
    '.kit-person-suit-t{fill:var(--cold);fill-opacity:.5;stroke:var(--txt-d);stroke-width:1.5}' +
    '.kit-person-zip{stroke:var(--txt-d);stroke-width:2;stroke-dasharray:3 3}' +
    '.kit-person-strap{stroke:var(--txt-d);stroke-width:4;stroke-linecap:round}' +
    '.kit-person-hose{fill:none;stroke:var(--txt-d);stroke-width:3;stroke-linecap:round}' +
    '.kit-person-brim{stroke:var(--txt-d);stroke-width:4;stroke-linecap:round}' +
    '.kit-person-visor{fill:var(--cold);fill-opacity:.2;stroke:var(--txt-d);stroke-width:2}' +
    '.kit-person-apron{fill:var(--cold);fill-opacity:.4;stroke:var(--txt-d);stroke-width:2;stroke-linejoin:round}',
  example: { size: [640, 330], parts: [
    { id: 'A', type: 'person', x: 110, y: 290, scale: 1.3, wear: ['goggles', 'respirator', 'apron', 'gloves'], labels: { respirator: 'HALF MASK' }, label: 'sample handler' },
    { id: 'B', type: 'person', x: 320, y: 290, scale: 1.3, wear: ['helmet', 'gloves', 'suit', 'boots', 'scba'], label: 'entrant' },
    { id: 'C', type: 'person', x: 530, y: 290, scale: 1.3, wear: ['helmet', 'visor', 'gloves', 'suit', 'boots', 'scba'], label: 'spill responder' } ],
    steps: [ { title: 'Head and hands: helmet, visor, gloves', play: [['A', 2, 1600, 0, 'linear'], ['B', 2, 1600, 0, 'linear'], ['C', 2, 1600, 0, 'linear']] },
             { title: 'Body: gloves, suit, boots', play: [['A', 4, 1600, 0, 'linear'], ['B', 4, 1600, 0, 'linear'], ['C', 4, 1600, 0, 'linear']] },
             { title: 'Breathing: the apparatus goes on last', play: [['B', 5, 1000, 0, 'linear'], ['C', 6, 1600, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: sensor */
KIT.define('sensor', function (fig, part, g, p) {
  var h = KIT.h, ir = p.kind === 'infrared', ox = p.oxygen != null ? p.oxygen : 1, key, i;
  var LB = { cap: 'sintered cap', bead: 'heated bead', gas: 'gas', oxygen: 'oxygen', lamp: 'IR lamp', cell: 'gas in the beam', det: 'detector' };
  var WD = ir ? { none: 'NO GAS - BEAM FULL', on: 'GAS DIMS THE BEAM' }
              : { none: 'NO GAS', on: 'GAS BURNS - SIGNAL', off: 'NO OXYGEN - NO SIGNAL' };
  for (key in (p.labels || {})) LB[key] = p.labels[key];
  for (key in (p.words || {})) WD[key] = p.words[key];
  var seed = 5, labs = {};
  function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
  function lab(name, x, y, anchor) {
    if (!LB[name]) return null;
    labs[name] = h.label(fig, g, { x: x, y: y, 'text-anchor': anchor || 'middle', 'class': 'kit-cap' }, LB[name]);
    return labs[name];
  }
  var gasDots = [], oxDots = [], rays = [], beam = null, bar = null, barH = 40, sx = 0, sy = 0;
  if (!ir) {
    h.el('path', { d: 'M-34 -4 V-84 Q-34 -114 0 -114 Q34 -114 34 -84 V-4 Z', 'class': 'kit-vessel' }, g);
    h.el('path', { d: 'M-34 -84 Q-34 -114 0 -114 Q34 -114 34 -84', 'class': 'kit-sensor-sinter' }, g);
    h.el('rect', { x: -40, y: -6, width: 80, height: 14, rx: 3, 'class': 'kit-steel' }, g);
    [-8, 8].forEach(function (x) {
      h.el('line', { x1: x, y1: -6, x2: x, y2: -40, 'class': 'kit-probe' }, g);
      h.el('line', { x1: x, y1: 8, x2: x, y2: 22, 'class': 'kit-probe' }, g);
    });
    for (i = 0; i < 8; i++) {
      var a0 = h.polar(15, i * 45), a1 = h.polar(23, i * 45);
      rays.push(h.el('line', { x1: a0[0].toFixed(1), y1: (a0[1] - 50).toFixed(1), x2: a1[0].toFixed(1), y2: (a1[1] - 50).toFixed(1), 'class': 'kit-sensor-ray' }, g));
    }
    h.el('circle', { cx: 0, cy: -50, r: 11, 'class': 'kit-sensor-bead' }, g);
    var gx = [-20, -6, 8, 22, 0], ox_ = [-26, -12, 2, 16, 28];
    for (i = 0; i < 5; i++) {
      gasDots.push(h.el('circle', { cx: gx[i], cy: -148 + (i % 2) * 14, r: 3.2, 'class': 'kit-sensor-gas kit-sensor-in', style: 'animation-delay:' + (-0.36 * i).toFixed(2) + 's' }, g));
      oxDots.push(h.el('circle', { cx: ox_[i], cy: -134 + (i % 2) * 14, r: 3.4, 'class': 'kit-sensor-ox kit-sensor-in', style: 'animation-delay:' + (-0.36 * i - 0.18).toFixed(2) + 's' }, g));
    }
    lab('cap', 44, -92, 'start'); lab('bead', 44, -50, 'start');
    lab('gas', -36, -150, 'end'); lab('oxygen', -36, -128, 'end');
    sx = 0; sy = 38;
  } else {
    h.el('circle', { r: 16, 'class': 'kit-shell' }, g);
    for (i = 0; i < 6; i++) {
      var r0 = h.polar(21, -50 + i * 20), r1 = h.polar(29, -50 + i * 20);
      h.el('line', { x1: r0[0].toFixed(1), y1: r0[1].toFixed(1), x2: r1[0].toFixed(1), y2: r1[1].toFixed(1), 'class': 'kit-sensor-lamp' }, g);
    }
    h.el('rect', { x: 40, y: -34, width: 140, height: 68, rx: 4, 'class': 'kit-sensor-cell' }, g);
    h.el('rect', { x: 196, y: -28, width: 34, height: 56, rx: 4, 'class': 'kit-shell' }, g);
    h.el('rect', { x: 205, y: -20, width: 16, height: 40, 'class': 'kit-sensor-slot' }, g);
    bar = h.el('rect', { x: 205, width: 16, 'class': 'kit-sensor-sig' }, g);
    beam = h.el('g', { 'data-low-contrast': '' }, g);              // gas dims the beam: that is the lesson, so a dim beam is not a fault
    [-10, 0, 10].forEach(function (y) { h.el('line', { x1: 20, y1: y, x2: 194, y2: y, 'class': 'kit-sensor-beam' }, beam); });
    for (i = 0; i < 12; i++) {
      gasDots.push(h.el('circle', { cx: (50 + rnd() * 120).toFixed(1), cy: (-26 + rnd() * 52).toFixed(1), r: 3.2, 'class': 'kit-sensor-gas kit-sensor-wob', style: 'animation-delay:' + (-rnd() * 2).toFixed(2) + 's' }, g));
    }
    lab('lamp', 0, -42); lab('cell', 110, -46); lab('det', 213, -42);
    sx = 113; sy = 60;
  }
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;           // its name and its reading word move together
  var nl = p.label ? h.lines(lg, { x: sx, y: sy + 8, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state === false ? null : h.el('text', { x: sx, y: sy + 8, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1), on = k > 0.02, burn = k * h.clamp(ox, 0, 1), word;
    if (ir) {
      var n = on ? Math.ceil(k * gasDots.length) : 0, sig = 1 - 0.8 * k;
      gasDots.forEach(function (d, j) { d.setAttribute('visibility', j < n ? 'visible' : 'hidden'); });
      beam.style.opacity = (0.15 + 0.85 * sig).toFixed(2);
      bar.setAttribute('height', (40 * sig).toFixed(1)); bar.setAttribute('y', (20 - 40 * sig).toFixed(1));
      word = on ? WD.on : WD.none;
    } else {
      var ng = on ? Math.ceil(k * 5) : 0, no = Math.ceil(h.clamp(ox, 0, 1) * 5);
      gasDots.forEach(function (d, j) { d.setAttribute('visibility', j < ng ? 'visible' : 'hidden'); });
      oxDots.forEach(function (d, j) { d.setAttribute('visibility', j < no ? 'visible' : 'hidden'); });
      rays.forEach(function (r) { r.style.opacity = burn.toFixed(2); });
      if (labs.gas) labs.gas.style.opacity = on ? '1' : '0';
      if (labs.oxygen) labs.oxygen.style.opacity = no ? '1' : '0';
      word = !on ? WD.none : (ox > 0.05 ? WD.on : WD.off);
    }
    g.classList.toggle('kit-sensor-on', on);
    g.classList.toggle('kit-sensor-hot', !ir && burn > 0.2);
    if (st) st.textContent = word;
  };
}, {
  family: 'cutaways',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M09 gas detection: how a gas sensor sees gas, as a principle cutaway - a catalytic bead that burns the gas (and needs oxygen to do it) and an infrared cell where gas dims a beam',
  value: '0..1 how much gas is in the sensor; kind catalytic (heated bead in a sintered cap; option oxygen 0..1 - with none, nothing burns) or infrared (lamp, cell, detector); a reading word sits under it, words and labels can be replaced',
  css: '.kit-sensor-sinter{fill:none;stroke:var(--dim-d);stroke-width:4;stroke-dasharray:2 4}' +
    '.kit-sensor-bead{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2.5}' +
    '.kit-sensor-hot .kit-sensor-bead{fill:var(--txt-d);stroke:var(--txt-d)}' +
    '.kit-sensor-ray{stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round;opacity:0}' +
    '.kit-sensor-gas{fill:var(--txt-d)}' +
    '.kit-sensor-ox{fill:none;stroke:var(--cold);stroke-width:2}' +
    '.kit-sensor-lamp{stroke:var(--cold);stroke-width:2.5;stroke-linecap:round}' +
    '.kit-sensor-cell{fill:none;stroke:var(--faint-d);stroke-width:2;stroke-dasharray:6 4}' +
    '.kit-sensor-slot{fill:var(--deep);stroke:var(--faint-d);stroke-width:1}' +
    '.kit-sensor-sig{fill:var(--cold)}' +
    '.kit-sensor-beam{stroke:var(--cold);stroke-width:3;stroke-linecap:round}' +
    '.kit-sensor-on .kit-sensor-in{animation:kit-sensor-in 1.8s linear infinite}' +
    '.kit-sensor-on .kit-sensor-wob{animation:kit-sensor-wob 1.2s ease-in-out infinite alternate}' +
    '.kit-sensor-on .kit-state{fill:var(--txt-d)}' +
    '@keyframes kit-sensor-in{0%{transform:translateY(0);opacity:0}15%{opacity:1}85%{opacity:1}100%{transform:translateY(80px);opacity:0}}' +
    '@keyframes kit-sensor-wob{to{transform:translate(6px,-4px)}}',
  example: { size: [600, 250], parts: [
    { id: 'C', type: 'sensor', kind: 'catalytic', x: 70, y: 170, label: 'catalytic' },
    { id: 'N', type: 'sensor', kind: 'catalytic', oxygen: 0, x: 290, y: 170, label: 'catalytic, no oxygen', labels: { cap: false, bead: false } },
    { id: 'I', type: 'sensor', kind: 'infrared', x: 400, y: 100, label: 'infrared' } ],
    steps: [ { title: 'Gas reaches the sensors', play: [['C', 1, 2000], ['N', 1, 2000], ['I', 1, 2000]] },
             { title: 'The gas goes away', play: [['C', 0, 1200], ['N', 0, 1200], ['I', 0, 1200]] } ] }
});
/* end kit-part */
/* kit-part: static_charge */
KIT.define('static_charge', function (fig, part, g, p) {
  var h = KIT.h, bonded = !!p.bonded, key, i;
  var LB = { part: 'isolated metal part', earth: 'earthed steel', bond: 'bonding cable' };
  for (key in (p.labels || {})) LB[key] = p.labels[key];
  function lab(name, x, y, anchor) { if (LB[name]) h.label(fig, g, { x: x, y: y, 'text-anchor': anchor, 'class': 'kit-cap' }, LB[name]); }
  function plus(x, y) { return h.el('path', { d: 'M' + (x - 4.5) + ' ' + y + ' H' + (x + 4.5) + ' M' + x + ' ' + (y - 4.5) + ' V' + (y + 4.5), 'class': 'kit-static-charge-sign' }, g); }
  h.el('path', { d: 'M-130 -46 H-26 Q0 -46 0 -20 V-3', 'class': 'kit-pipe' }, g);                      // hose
  h.el('line', { x1: -10, y1: -2, x2: 10, y2: -2, 'class': 'kit-flange' }, g);
  var stream = h.el('line', { x1: 0, y1: 4, x2: 0, y2: 66, 'class': 'kit-static-charge-stream' }, g);
  var tsign = [20, 36, 52].map(function (y) { return plus(0, y); });
  h.el('line', { x1: -74, y1: 140, x2: 74, y2: 140, 'class': 'kit-tickl' }, g);                       // the floor
  [-38, 38].forEach(function (x) { h.el('rect', { x: x - 10, y: 130, width: 20, height: 10, 'class': 'kit-static-charge-ins' }, g); });
  h.el('rect', { x: -52, y: 70, width: 104, height: 60, rx: 12, 'class': 'kit-steel' }, g);           // the isolated part
  var order = [2, 7, 0, 9, 4, 5, 1, 8, 3, 6], signs = [];
  for (i = 0; i < 10; i++) signs[order.indexOf(i)] = plus(-36 + 18 * (i % 5), i < 5 ? 88 : 112);
  h.el('line', { x1: 118, y1: 90, x2: 118, y2: 140, 'class': 'kit-pipe-s' }, g);                       // an earthed post
  h.el('path', { d: 'M105 144 H131 M110 150 H126 M115 156 H121', 'class': 'kit-flange' }, g);
  var spark = h.el('path', { d: 'M52 100 L66 91 L76 107 L88 93 L98 107 L116 100', 'class': 'kit-static-charge-spark' }, g);
  var cable = null, drain = null;
  if (bonded) {
    var cd = 'M-52 100 C-92 100 -92 126 -92 146';
    cable = h.el('path', { d: cd, 'class': 'kit-static-charge-cable' }, g);
    drain = h.el('path', { d: cd, 'class': 'kit-static-charge-drain' }, g);
    h.el('path', { d: 'M-105 150 H-79 M-100 156 H-84 M-95 162 H-89', 'class': 'kit-flange' }, g);
  }
  lab('part', 0, 164, 'middle'); lab('earth', 118, 76, 'middle');
  if (bonded) lab('bond', -100, 100, 'end');
  /* the words stand ABOVE the hose (its line is at y -46), the state on the bottom row and the label above it; the rows
     keep clear of the hose as the type grows (the 12.5 px floor) - they used to start at -66 and run down onto it (2.49.1) */
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '', { self: true }) : null;      // self: it may stand within the part's own box
  var nl = p.label ? h.lines(lg, { x: -130, y: -66, 'text-anchor': 'start', 'class': 'kit-cap' }, p.label) : 0;
  var lt = p.label ? lg.querySelector('text.kit-cap') : null;
  var st = p.state === false ? null : h.el('text', { x: -130, y: -66, 'text-anchor': 'start', 'class': 'kit-state' }, lg);
  function rows(k) {
    var base = -(46 + 4.5 * k + 5 * k + 3);               // the bottom row's baseline: its letters clear of the hose line
    if (st) st.setAttribute('y', base.toFixed(1));
    if (lt) lt.setAttribute('y', (base - (st ? 16 * k : 0) - (nl - 1) * 16 * k).toFixed(1));
  }
  rows(1);
  fig.fit(rows);
  part.render = function (v) {
    var c = Math.max(0, v), build = h.clamp(c, 0, 1), s = h.clamp((c - 1) / 0.2, 0, 1), on = c > 0.02;
    var shown = bonded ? 0 : build * signs.length * (1 - s), word;
    signs.forEach(function (n, j) { n.style.opacity = h.clamp(shown - j, 0, 1).toFixed(2); });
    tsign.forEach(function (n) { n.style.opacity = h.clamp(build * 3, 0, 1).toFixed(2); });
    var fire = !bonded && c > 1 && c <= 1.2;
    spark.style.opacity = fire ? '1' : '0';
    g.classList.toggle('kit-static-charge-on', on);
    g.classList.toggle('kit-static-charge-hot', fire);
    if (st) {
      if (!on) word = 'AT REST';
      else if (bonded) word = 'BONDED - NO CHARGE BUILDS';
      else if (fire) word = 'SPARK - IGNITION SOURCE';
      else if (c > 1.2) word = 'DISCHARGED';
      else word = 'CHARGE BUILDS UP';
      st.textContent = word;
    }
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M06 and M07 ignition sources: a liquid or gas flowing out of a hose charges an isolated metal part until a spark jumps to earthed steel - and a bonding cable to earth stops the charge from ever building',
  value: '0..1 the charge on the isolated part builds; 1..1.2 a spark jumps and the charge is gone; option bonded: true draws the bonding cable to earth and the charge never builds',
  css: '.kit-static-charge-stream{stroke:var(--cold);stroke-width:4;stroke-dasharray:8 7;stroke-linecap:round;opacity:0}' +
    '.kit-static-charge-on .kit-static-charge-stream{opacity:1;animation:kit-static-charge-run .5s linear infinite}' +
    '.kit-static-charge-sign{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round}' +
    '.kit-static-charge-ins{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:4 3}' +
    '.kit-static-charge-spark{fill:none;stroke:var(--txt-d);stroke-width:3.5;stroke-linejoin:round;stroke-linecap:round;opacity:0}' +
    '.kit-static-charge-cable{fill:none;stroke:var(--dim-d);stroke-width:5;stroke-linecap:round}' +
    '.kit-static-charge-drain{fill:none;stroke:var(--txt-d);stroke-width:3;stroke-dasharray:3 9;stroke-linecap:round;opacity:0}' +
    '.kit-static-charge-on .kit-static-charge-drain{opacity:1;animation:kit-static-charge-run 1s linear infinite}' +
    '.kit-static-charge-on .kit-state{fill:var(--txt-d)}' +
    '.kit-static-charge-hot .kit-state{fill:var(--amber)}' +
    '@keyframes kit-static-charge-run{to{stroke-dashoffset:-15}}',
  example: { size: [640, 250], parts: [
    { id: 'A', type: 'static_charge', x: 150, y: 80, label: 'not bonded' },
    { id: 'B', type: 'static_charge', x: 460, y: 80, bonded: true, label: 'bonded to earth', labels: { part: false, earth: false } } ],
    steps: [ { title: 'Liquid flows from the hose - charge builds on the isolated part', play: [['A', 1, 2600, 0, 'linear'], ['B', 1, 2600, 0, 'linear']] },
             { title: 'The charge jumps to earthed steel as a spark - the bonded part never charged', play: [['A', 1.1, 600]] } ] }
});
/* end kit-part */
/* kit-part: fire */
KIT.define('fire', function (fig, part, g, p) {
  var h = KIT.h, jet = p.kind === 'jet', w = p.w || 140, len = p.length || 170, ang = p.angle || 0, seed = 3, i;
  function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
  var body = h.el('g', {}, g), grow, lx, ly, la = 'middle';
  if (jet) {
    var sym = h.el('g', { transform: ang ? 'rotate(' + (-ang) + ')' : null }, body), R = Math.min(len * 0.12, 70);
    /* "stub": false leaves out the 90 px pipe end the jet is drawn on - when the figure has the real pipe, it is drawn over it */
    if (p.stub !== false) {
      h.el('line', { x1: -90, y1: 0, x2: -4, y2: 0, 'class': 'kit-pipe' }, sym);                 // the pipe the gas leaks from
      h.el('line', { x1: -4, y1: -9, x2: -4, y2: 9, 'class': 'kit-flange' }, sym);
    }
    grow = h.el('g', {}, sym);
    var jt = h.el('g', { 'class': 'kit-fire-jet' }, grow);
    h.el('path', { d: 'M0 -5 C' + (len * 0.25) + ' ' + (-R) + ' ' + (len * 0.6) + ' ' + (-R * 0.8) + ' ' + len + ' 0 C' + (len * 0.6) + ' ' + (R * 0.8) + ' ' + (len * 0.25) + ' ' + R + ' 0 5 Z', 'class': 'kit-fire-out', 'data-may-cross': '', 'data-no-contain': '' }, jt);
    h.el('path', { d: 'M0 -3 C' + (len * 0.2) + ' ' + (-R * 0.5) + ' ' + (len * 0.4) + ' ' + (-R * 0.4) + ' ' + (len * 0.58) + ' 0 C' + (len * 0.4) + ' ' + (R * 0.4) + ' ' + (len * 0.2) + ' ' + (R * 0.5) + ' 0 3 Z', 'class': 'kit-fire-core', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, jt);   // the hot core inside the jet: its outer tongue carries the contrast
    lx = -8; ly = 30; la = 'end';
  } else {
    h.el('rect', { x: 1, y: 0, width: w - 2, height: 12, 'class': 'kit-pool' }, g);
    h.el('path', { d: 'M-2 -2 V16 H' + (w + 2) + ' V-2', 'class': 'kit-fire-pan' }, g);
    grow = h.el('g', {}, body);
    var n = Math.max(3, Math.round(w / 22)), sp = w / n, top = p.height || Math.min(w * 0.55, 140);
    for (i = 0; i < n; i++) {
      var cx = (i + 0.5) * sp, s = top * (0.62 + 0.38 * rnd()), wd = sp * 0.78, c2 = h.el('g', { 'class': 'kit-fire-tongue', style: 'animation-delay:' + (-rnd() * 0.4).toFixed(2) + 's' }, grow);
      h.el('path', { d: 'M' + (cx - wd).toFixed(1) + ' 0 C' + (cx - wd * 1.2).toFixed(1) + ' ' + (-s * 0.3).toFixed(1) + ' ' + (cx - wd * 0.55).toFixed(1) + ' ' + (-s * 0.65).toFixed(1) + ' ' + cx.toFixed(1) + ' ' + (-s).toFixed(1) +
        ' C' + (cx + wd * 0.55).toFixed(1) + ' ' + (-s * 0.65).toFixed(1) + ' ' + (cx + wd * 1.2).toFixed(1) + ' ' + (-s * 0.3).toFixed(1) + ' ' + (cx + wd).toFixed(1) + ' 0 Z', 'class': 'kit-fire-out', 'data-may-cross': '', 'data-no-contain': '' }, c2);
      h.el('path', { d: 'M' + (cx - wd * 0.5).toFixed(1) + ' 0 C' + (cx - wd * 0.6).toFixed(1) + ' ' + (-s * 0.15).toFixed(1) + ' ' + (cx - wd * 0.25).toFixed(1) + ' ' + (-s * 0.35).toFixed(1) + ' ' + cx.toFixed(1) + ' ' + (-s * 0.55).toFixed(1) +
        ' C' + (cx + wd * 0.25).toFixed(1) + ' ' + (-s * 0.35).toFixed(1) + ' ' + (cx + wd * 0.6).toFixed(1) + ' ' + (-s * 0.15).toFixed(1) + ' ' + (cx + wd * 0.5).toFixed(1) + ' 0 Z', 'class': 'kit-fire-core', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, c2);   // the hot core inside each tongue
    }
    lx = w / 2; ly = 36;
  }
  var lg = p.label || p.state ? h.label(fig, g, {}, '') : null;
  var nl = p.label ? h.lines(lg, { x: lx, y: ly, 'text-anchor': la, 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state ? h.el('text', { x: lx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': la, 'class': 'kit-state' }, lg) : null;
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    grow.setAttribute('transform', jet ? 'scale(' + Math.max(k, 0.001).toFixed(3) + ' ' + (0.5 + 0.5 * k).toFixed(3) + ')' : 'scale(1 ' + Math.max(k, 0.001).toFixed(3) + ')');
    grow.style.opacity = k > 0.02 ? '1' : '0';
    g.classList.toggle('kit-fire-on', k > 0.05);
    if (st) st.textContent = k > 0.05 ? 'BURNING' : 'OUT';
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M13 fire types: a pool fire (a spilled liquid burning over its surface - wide, low flames) and a jet fire (gas leaking under pressure and burning as a long tongue from the leak point)',
  value: '0 out .. 1 full; kind pool (width w, optional height) or jet (length, angle in degrees above horizontal), the flame stands on the surface (pool) or grows out of the leak point (jet); a jet is drawn on a 90 px pipe end unless stub: false',
  css: '.kit-fire-out{fill:var(--warn-d);opacity:.7}' +
    '.kit-fire-core{fill:var(--amber)}' +
    '.kit-fire-pan{fill:none;stroke:var(--dim-d);stroke-width:3;stroke-linejoin:round}' +
    '.kit-fire-on .kit-fire-tongue{transform-box:fill-box;transform-origin:50% 100%;animation:kit-fire-flick .4s ease-in-out infinite alternate}' +
    '.kit-fire-on .kit-fire-jet{transform-box:fill-box;transform-origin:0% 50%;animation:kit-fire-jet .3s ease-in-out infinite alternate}' +
    '.kit-fire-on .kit-state{fill:var(--warn-d)}' +
    '@keyframes kit-fire-flick{to{transform:scale(1.08,.88)}}@keyframes kit-fire-jet{to{transform:scale(1.06,.88)}}',
  example: { size: [640, 330], parts: [
    { id: 'J', type: 'fire', kind: 'jet', x: 190, y: 90, length: 430, angle: 0, value: 1, label: 'jet fire\ngas leaks under pressure' },
    { id: 'P', type: 'fire', kind: 'pool', x: 90, y: 250, w: 460, value: 1, label: 'pool fire: a spilled liquid burns' } ],
    steps: [ { title: 'The leak is reduced - the jet fire gets smaller', play: [['J', 0.75, 1800]] },
             { title: 'Foam goes on the pool - its flames get lower', play: [['P', 0.75, 1800]] } ] }
});
/* end kit-part */
/* kit-part: flammability */
KIT.define('flammability', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 380, ht = p.h || 250, X = p.xmax || 100, Y = p.ymax || 25, air = p.air || 21;
  var zone = p.zone || [], path = p.path || [[0, air], [100, 0]], words = p.words || ['NOT FLAMMABLE', 'FLAMMABLE'];
  function sx(v) { return v / X * w; }
  function sy(v) { return ht - v / Y * ht; }
  function list(a) { return a.map(function (q) { return sx(q[0]).toFixed(1) + ' ' + sy(q[1]).toFixed(1); }); }
  var v, i;
  h.el('path', { d: 'M0 0 V' + ht + ' H' + w, 'class': 'kit-flammability-axis' }, g);
  for (v = 0; v <= X + 1e-9; v += p.xevery || 20) {
    h.el('line', { x1: sx(v), x2: sx(v), y1: ht, y2: ht + 6, 'class': 'kit-tickl' }, g);
    if (v > 0) h.el('line', { x1: sx(v), x2: sx(v), y1: 0, y2: ht, 'class': 'kit-flammability-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);   // a quiet grid
    h.el('text', { x: sx(v), y: ht + 22, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, String(v));
  }
  for (v = 0; v <= Y + 1e-9; v += p.yevery || 5) {
    h.el('line', { x1: -6, x2: 0, y1: sy(v), y2: sy(v), 'class': 'kit-tickl' }, g);
    if (v > 0) h.el('line', { x1: 0, x2: w, y1: sy(v), y2: sy(v), 'class': 'kit-flammability-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);
    h.el('text', { x: -15, y: sy(v) + 4.5, 'text-anchor': 'end', 'class': 'kit-tick' }, g, String(v));
  }
  h.label(fig, g, { x: w / 2, y: ht + 48, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.xlabel || '% fuel in the mixture');
  h.label(fig, g, { x: 0, y: -14, 'text-anchor': 'start', 'class': 'kit-cap' }, p.ylabel || '% oxygen');
  /* the flammable zone is a polygon of [fuel %, oxygen %] points: a course gives its own numbers from its sources */
  if (zone.length > 2) {
    h.el('polygon', { points: list(zone).join(' '), 'class': 'kit-flammability-zone', 'data-no-contain': '', 'data-low-contrast': '' }, g);
  }
  h.el('line', { x1: sx(0), y1: sy(air), x2: sx(100), y2: sy(0), 'class': 'kit-flammability-air', 'data-may-cross': '' }, g);
  (p.lines || []).forEach(function (m) {
    h.el('polyline', { points: list(m.pts).join(' '), 'class': 'kit-flammability-line', 'data-may-cross': '' }, g);
    var e = m.pts[m.pts.length - 1];
    if (m.label) h.label(fig, g, { x: sx(e[0]) - 6, y: sy(e[1]) - 9, 'text-anchor': 'end', 'class': 'kit-cap' }, m.label);
  });
  if (p.airLabel) h.label(fig, g, { x: sx(60) + 8, y: sy(air * 0.4) - 12, 'text-anchor': 'start', 'class': 'kit-cap' }, p.airLabel);
  if (p.zoneLabel && zone.length > 2) {
    var nose = zone.reduce(function (a, b) { return b[1] < a[1] ? b : a; });
    h.label(fig, g, { x: sx(nose[0]) + 4, y: sy(nose[1] - 2.4) + 4.5, 'text-anchor': 'start', 'class': 'kit-cap' }, p.zoneLabel);
  }
  var st = h.label(fig, g, {}, '');
  var stText = h.el('text', { x: w - 6, y: 16, 'text-anchor': 'end', 'class': 'kit-state kit-flammability-st' }, st);
  var P = path.map(function (q) { return [sx(q[0]), sy(q[1])]; }), cum = [0], total = 0;
  for (i = 1; i < P.length; i++) { total += Math.sqrt(Math.pow(P[i][0] - P[i - 1][0], 2) + Math.pow(P[i][1] - P[i - 1][1], 2)); cum.push(total); }
  total = total || 1;
  var trail = h.el('polyline', { points: P.map(function (q) { return q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' '), 'class': 'kit-flammability-trail', 'data-may-cross': '' }, g);
  var dot = h.el('circle', { r: 7, 'class': 'kit-flammability-dot', 'data-may-cross': '' }, g);
  function near(px, py, a, b) {                       // px from the segment a-b
    var dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy || 1;
    var t = h.clamp(((px - a[0]) * dx + (py - a[1]) * dy) / l2, 0, 1);
    return Math.sqrt(Math.pow(px - a[0] - t * dx, 2) + Math.pow(py - a[1] - t * dy, 2));
  }
  function inZone(px, py) {                           // inside the polygon, or on its edge
    var z = zone.map(function (q) { return [sx(q[0]), sy(q[1])]; }), c = false, j, k;
    if (z.length < 3) return false;
    for (k = 0, j = z.length - 1; k < z.length; j = k++) {
      if ((z[k][1] > py) !== (z[j][1] > py) && px < (z[j][0] - z[k][0]) * (py - z[k][1]) / (z[j][1] - z[k][1]) + z[k][0]) c = !c;
    }
    for (k = 0, j = z.length - 1; k < z.length; j = k++) if (near(px, py, z[k], z[j]) < 2.5) c = true;
    return c;
  }
  part.render = function (val) {
    var s = h.clamp(val, 0, 1) * total, k = 1, f, x, y;
    while (k < P.length - 1 && cum[k] < s) k++;
    f = cum[k] > cum[k - 1] ? h.clamp((s - cum[k - 1]) / (cum[k] - cum[k - 1]), 0, 1) : 0;
    x = P[k - 1][0] + f * (P[k][0] - P[k - 1][0]);
    y = P[k - 1][1] + f * (P[k][1] - P[k - 1][1]);
    dot.setAttribute('cx', x.toFixed(1)); dot.setAttribute('cy', y.toFixed(1));
    trail.setAttribute('stroke-dasharray', s.toFixed(1) + ' ' + (total * 2).toFixed(1));
    var hot = inZone(x, y);
    g.classList.toggle('kit-flammability-hot', hot);
    stText.textContent = hot ? words[1] : words[0];
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M06 the flammability diagram for methane (fuel % against oxygen %, the air line, the flammable zone, a mixture moving along the air line) and M07 the inerting path that stays out of the zone (plan: the media plans of modules 6 and 7)',
  value: '0..1 how far the point has travelled along path (a list of [fuel %, oxygen %]); the zone lights amber while the point is inside it',
  css: '.kit-flammability-axis{fill:none;stroke:var(--faint-d);stroke-width:2}' +
    '.kit-flammability-grid{stroke:var(--faint-d);stroke-width:1;stroke-dasharray:2 6;opacity:.7}' +
    '.kit-flammability-air{stroke:var(--dim-d);stroke-width:2.5}' +
    '.kit-flammability-zone{fill:var(--faint-d);fill-opacity:.25;stroke:var(--dim-d);stroke-width:2;stroke-dasharray:6 4;stroke-linejoin:round}' +
    '.kit-flammability-hot .kit-flammability-zone{fill:var(--amber);fill-opacity:.4;stroke:var(--amber);stroke-dasharray:none}' +
    '.kit-flammability-line{fill:none;stroke:var(--cold);stroke-width:2;stroke-dasharray:8 5}' +
    '.kit-flammability-trail{fill:none;stroke:var(--blue);stroke-width:4;stroke-linecap:round;stroke-linejoin:round}' +
    '.kit-flammability-dot{fill:var(--txt-d);stroke:var(--blue);stroke-width:3}' +
    '.kit-flammability-hot .kit-flammability-dot{stroke:var(--amber)}' +
    '.kit-flammability-hot .kit-flammability-st{fill:var(--amber)}',
  /* example data is methane, drawn from nothing but the corners the air line gives (5 and 15 % in air); a course gives
     its own zone, lines and path from its sources */
  example: { size: [520, 340], parts: [
    { id: 'F', type: 'flammability', x: 70, y: 40, w: 400, h: 250,
      zone: [[5, 19.95], [15, 17.85], [6, 12]], zoneLabel: 'flammable zone', airLabel: 'air line',
      lines: [{ label: 'oxygen limit', pts: [[0, 12], [100, 12]] }],
      path: [[0, 21], [100, 0]] } ],
    steps: [ { title: 'Methane is added to air: too lean', play: [['F', 0.04, 1500, 0, 'linear']] },
             { title: 'Between 5 and 15 % the mixture can burn', play: [['F', 0.1, 1500, 0, 'linear']] },
             { title: 'Above 15 % it is too rich', play: [['F', 0.4, 1800, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: range_bar */
KIT.define('range_bar', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 520, bh = p.h || 34, max = p.max || 100, lel = +p.lel, uel = +p.uel;
  var words = p.words || { lean: 'LEAN', flammable: 'FLAMMABLE', rich: 'RICH' };
  function sx(v) { return h.clamp(v / max, 0, 1) * w; }
  var a = sx(lel), b = sx(uel);
  h.el('rect', { x: 0, y: 0, width: a, height: bh, 'class': 'kit-range-bar-out' }, g);
  var mid = h.el('rect', { x: a, y: 0, width: Math.max(1, b - a), height: bh, 'class': 'kit-range-bar-mid' }, g);
  h.el('rect', { x: b, y: 0, width: Math.max(1, w - b), height: bh, 'class': 'kit-range-bar-out' }, g);
  h.el('rect', { x: 0, y: 0, width: w, height: bh, rx: 4, 'class': 'kit-range-bar-frame', 'data-no-contain': '' }, g);
  /* the numbers under the bar: both limits and both ends of the axis - but an end number crowds the limit next to it when
     the limit is within 8 % of the axis (a lower limit of 4-6 % sat on top of the "0"): then the end's number is left out.
     "nums": [..] names the numbers outright (2.49.1) */
  var every = p.every || 10, v, near = 0.08 * max, nums;
  if (p.nums && p.nums.length) nums = p.nums.map(Number);
  else {
    nums = [lel, uel];
    if (lel >= near) nums.unshift(0);
    if (max - uel >= near) nums.push(max);
  }
  for (v = 0; v <= max + 1e-9; v += every) h.el('line', { x1: sx(v), x2: sx(v), y1: bh, y2: bh + 5, 'class': 'kit-tickl' }, g);
  var numT = [], wordT = [];
  nums.forEach(function (n) {
    h.el('line', { x1: sx(n), x2: sx(n), y1: bh, y2: bh + 9, 'class': 'kit-tickl' }, g);
    numT.push(h.el('text', { x: sx(n), y: bh + 26, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, String(n)));
  });
  h.label(fig, g, { x: (a + b) / 2, y: -26, 'text-anchor': 'middle', 'class': 'kit-cap' }, words.flammable);
  wordT.push(h.label(fig, g, { x: a / 2, y: bh + 52, 'text-anchor': 'middle', 'class': 'kit-cap' }, words.lean).querySelector('text'));
  wordT.push(h.label(fig, g, { x: (b + w) / 2, y: bh + 52, 'text-anchor': 'middle', 'class': 'kit-cap' }, words.rich).querySelector('text'));
  fig.fit(function (k) {      // the numbers sit under their ticks as far as the grown type is tall; the words under the numbers
    var ny = bh + 9 + 14.5 * k, wy = ny + Math.max(14.5 * k, 26);
    numT.forEach(function (t) { t.setAttribute('y', ny.toFixed(1)); });
    wordT.forEach(function (t) { t.setAttribute('y', wy.toFixed(1)); });
  });
  if (p.label) h.label(fig, g, { x: 0, y: -56, 'text-anchor': 'start', 'class': 'kit-h' }, p.label);
  var rd = h.label(fig, g, {}, '');
  var rdText = h.el('text', { x: w, y: -56, 'text-anchor': 'end', 'class': 'kit-state kit-range-bar-st' }, rd);
  var ptr = h.el('g', {}, g);
  h.el('line', { x1: 0, x2: 0, y1: -14, y2: bh + 9, 'class': 'kit-range-bar-needle', 'data-may-cross': '' }, ptr);
  h.el('path', { d: 'M-8 -15 H8 L0 -1 Z', 'class': 'kit-range-bar-ptr', 'data-may-cross': '' }, ptr);
  part.render = function (val) {
    var c = h.clamp(val, 0, max), on = c >= lel && c <= uel;
    ptr.setAttribute('transform', 'translate(' + sx(c).toFixed(1) + ' 0)');
    g.classList.toggle('kit-range-bar-hot', on);
    rdText.textContent = h.fmt(c, { decimals: p.decimals || 0, unit: '%' }) + ' · ' + (on ? words.flammable : (c < lel ? words.lean : words.rich));
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M06 the flammable range of each fuel in air (methane 5-15, methanol 6-36, ammonia 15-28, hydrogen 4-75 %): lean below the lower limit, flammable between the limits, rich above (plan: media plan of module 6)',
  value: 'the concentration in %, 0..max (default 100); the pointer slides there and the flammable band lights amber while it is between lel and uel; the numbers under the bar are the limits and the ends (an end is left out when a limit is within 8 % of the axis from it), or nums: [..]',
  css: '.kit-range-bar-out{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:1.5}' +
    '.kit-range-bar-mid{fill:var(--faint-d);fill-opacity:.55;stroke:var(--dim-d);stroke-width:1.5}' +
    '.kit-range-bar-hot .kit-range-bar-mid{fill:var(--amber);fill-opacity:.7;stroke:var(--amber)}' +
    '.kit-range-bar-frame{fill:none;stroke:var(--dim-d);stroke-width:2}' +
    '.kit-range-bar-needle{stroke:var(--txt-d);stroke-width:3}' +
    '.kit-range-bar-ptr{fill:var(--txt-d)}' +
    '.kit-range-bar-hot .kit-range-bar-st{fill:var(--amber)}',
  example: { size: [560, 330], parts: [
    { id: 'M', type: 'range_bar', x: 20, y: 76, w: 520, lel: 5, uel: 15, label: 'methane in air', value: 0 },
    { id: 'H', type: 'range_bar', x: 20, y: 246, w: 520, lel: 4, uel: 75, label: 'hydrogen in air', value: 0 } ],
    steps: [ { title: 'Methane: 2 % is too lean', play: [['M', 2, 900]] },
             { title: 'Methane: 10 % is flammable', play: [['M', 10, 1000]] },
             { title: 'Methane: 30 % is too rich - hydrogen burns across most of the scale', play: [['M', 30, 1000], ['H', 50, 1400, 200]] } ] }
});
/* end kit-part */
/* kit-part: hose */
KIT.define('hose', function (fig, part, g, p) {
  var h = KIT.h, fluid = p.fluid === 'gas' ? 'gas' : 'liquid', mid = fig.uid + '-' + (p.id || 'hs') + '-m';
  g.classList.add('kit-hose-' + fluid);
  h.el('path', { d: p.d, 'class': 'kit-hose-body' }, g);
  /* the corrugation rings and the bore are dark on the hose's own body: quiet on purpose, the body and the fluid carry it */
  h.el('path', { d: p.d, 'class': 'kit-hose-rib', 'data-low-contrast': '' }, g);
  h.el('path', { d: p.d, 'class': 'kit-hose-bore', 'data-low-contrast': '' }, g);
  var mask = h.el('mask', { id: mid, maskUnits: 'userSpaceOnUse', x: -4000, y: -4000, width: 8000, height: 8000 }, h.el('defs', {}, g));
  var reach = h.el('path', { d: p.d, 'class': 'kit-reach' }, mask);
  var inside = h.el('g', { mask: 'url(#' + mid + ')' }, g);
  h.el('path', { d: p.d, 'class': 'kit-hose-fluid', 'data-low-contrast': '' }, inside);      // translucent liquid, as the kit's own pipe content
  var flow = h.el('path', { d: p.d, 'class': 'kit-flow' }, inside);
  var L = 0, m0 = null;
  try { L = reach.getTotalLength(); } catch (e) { L = 0; }
  if (L) {
    var a0 = reach.getPointAtLength(0), a1 = reach.getPointAtLength(Math.min(6, L)), b0 = reach.getPointAtLength(L), b1 = reach.getPointAtLength(Math.max(0, L - 6));
    [[a0, a1], [b0, b1]].forEach(function (c) {          // a coupling collar at each end, square to the hose
      var ang = Math.atan2(c[1].y - c[0].y, c[1].x - c[0].x) * 180 / Math.PI;
      h.el('rect', { x: -5, y: -17, width: 10, height: 34, rx: 2, 'class': 'kit-hose-collar', 'data-may-cross': '',
                     transform: 'translate(' + c[0].x.toFixed(1) + ' ' + c[0].y.toFixed(1) + ') rotate(' + ang.toFixed(1) + ')' }, g);
    });
    m0 = reach.getPointAtLength(L / 2);
  }
  L = L || 1000;
  if (p.label) {
    var lx = p.labelAt ? p.labelAt[0] : (m0 ? m0.x : 0), ly = p.labelAt ? p.labelAt[1] : (m0 ? m0.y - 30 : 0);
    h.label(fig, g, { x: lx, y: ly, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  }
  part.render = function (v) {                         // the flow, as a pipe's
    flow.style.opacity = v > 0.02 ? Math.min(1, 0.35 + v).toFixed(2) : 0;
    flow.style.animationDuration = (0.8 / Math.max(v, 0.2)).toFixed(2) + 's';
  };
  var drain = p.drain != null ? +p.drain : 1;
  fig.sub(part, 'fill', p.fill != null ? +p.fill : (p.empty ? 0 : 1), function (f) {     // "<id>.fill": the front advancing, 1..2 emptying
    var s, e;
    if (f <= 1) { s = 0; e = h.clamp(f, 0, 1) * L; }
    else { var k = h.clamp(f - 1, 0, 1); s = k * drain * L; e = L - k * (1 - drain) * L; }
    reach.setAttribute('stroke-dasharray', '0 ' + s.toFixed(1) + ' ' + Math.max(0, e - s).toFixed(1) + ' ' + (2 * L).toFixed(1));
  });
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M13 the hand hoses used for bunkering and sampling, M14 the bunkering hose in the ESD chain between shore and ship (plan: media plans of modules 13 and 14)',
  value: 'flow 0 still .. 1 fast, as a pipe; the second value "<id>.fill" is 0..1 the fluid front advancing along d, 1..2 the hose emptying (set "empty": true to start dry). The spec checker only knows pipe.fill - hose.fill is new',
  css: '.kit-hose-body{fill:none;stroke:var(--faint-d);stroke-width:24}' +
    '.kit-hose-rib{fill:none;stroke:var(--deep-3);stroke-width:24;stroke-dasharray:3 7}' +
    '.kit-hose-bore{fill:none;stroke:var(--deep);stroke-width:14}' +
    '.kit-hose-fluid{fill:none;stroke:var(--cold);stroke-width:10;opacity:.55}' +
    '.kit-hose-gas .kit-hose-fluid{stroke:var(--txt-d);opacity:.22}' +
    '.kit-hose-gas .kit-flow{stroke:var(--txt-d);stroke-dasharray:2 6;stroke-linecap:round;stroke-width:3}' +
    '.kit-hose-collar{fill:var(--dim-d);stroke:var(--txt-d);stroke-width:1.5}',
  example: { size: [640, 300], parts: [
    { id: 'H', type: 'hose', empty: true, label: 'bunker hose', value: 0,
      d: 'M40 28 H560 C610 28 610 88 560 88 H80 C30 88 30 148 80 148 H560 C610 148 610 208 560 208 H80 C30 208 30 268 80 268 H600' } ],
    steps: [ { title: 'The hose is connected and dry', play: [['H', 0, 200]] },
             { title: 'LNG from the shore fills the hose', play: [['H', 0.8, 400], ['H.fill', 1, 3600, 0, 'linear']] },
             { title: 'LNG flows through to the ship', play: [['H', 1, 800]] } ] }
});
/* end kit-part */
/* kit-part: manifold */
KIT.define('manifold', function (fig, part, g, p) {
  var h = KIT.h, outs = p.outlets || [], n = outs.length || 1, w = p.w || 560, sp = w / n, hh = p.h || 24;
  var drop = p.drop || 44, hl = p.hose || 56, y0 = hh + drop + 7, words = p.words || ['BLANKED', 'CONNECTED'];
  h.el('rect', { x: 0, y: 0, width: w, height: hh, rx: 6, 'class': 'kit-steel' }, g);
  h.el('rect', { x: -8, y: -6, width: 10, height: hh + 12, rx: 2, 'class': 'kit-manifold-cap' }, g);
  h.el('rect', { x: w - 2, y: -6, width: 10, height: hh + 12, rx: 2, 'class': 'kit-manifold-cap' }, g);
  if (p.label) h.label(fig, g, { x: w / 2, y: -20, 'text-anchor': 'middle', 'class': 'kit-h' }, p.label);
  var made = outs.map(function (o, i) {
    var cx = sp * (i + 0.5), og = h.el('g', { 'class': 'kit-manifold-out' }, g);
    h.el('rect', { x: cx - 8, y: hh, width: 16, height: drop, 'class': 'kit-steel' }, og);
    h.el('rect', { x: cx - 18, y: hh + drop, width: 36, height: 7, rx: 2, 'class': 'kit-manifold-flange' }, og);
    var hose = h.el('rect', { x: cx - 10, y: y0, width: 20, height: 0, 'class': 'kit-manifold-hose', 'data-may-cross': '' }, og);
    var coll = h.el('rect', { x: cx - 14, y: y0, width: 28, height: 9, rx: 2, 'class': 'kit-manifold-collar', 'data-may-cross': '' }, og);
    var blind = h.el('rect', { x: cx - 18, y: y0, width: 36, height: 9, rx: 2, 'class': 'kit-manifold-blind', 'data-may-cross': '' }, og);
    var lg = h.label(fig, og, {}, '');
    var nl = h.lines(lg, { x: cx, y: y0 + hl + 26, 'text-anchor': 'middle', 'class': 'kit-cap' }, o.label || '');
    var st = h.el('text', { x: cx, y: y0 + hl + 26, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
    return { g: og, hose: hose, coll: coll, blind: blind, st: st };
  });
  part.render = function (v) {
    made.forEach(function (o, i) {
      var c = h.clamp(v - i, 0, 1);
      o.hose.setAttribute('height', (hl * c).toFixed(1));
      o.coll.style.opacity = c > 0.02 ? '1' : '0';
      o.blind.style.opacity = (1 - c).toFixed(2);
      o.st.textContent = c > 0.5 ? words[1] : words[0];
      o.g.classList.toggle('kit-manifold-on', c > 0.5);
    });
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M14 and M15 the bunker station: the manifold header with its liquid and vapour-return connections, each blanked with a blind flange until a hose is connected (plan: media plans of modules 14 and 15)',
  value: '0..n how many outlets are connected, counted from the left: outlet k grows its hose while the value goes from k to k+1; the others keep their blind flange',
  css: '.kit-manifold-cap{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}' +
    '.kit-manifold-flange{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}' +
    '.kit-manifold-blind{fill:var(--dim-d);stroke:var(--txt-d);stroke-width:1.5}' +
    '.kit-manifold-hose{fill:var(--deep-3);stroke:var(--cold);stroke-width:2}' +
    '.kit-manifold-collar{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2;opacity:0}' +
    '.kit-manifold-on .kit-state{fill:var(--txt-d)}',
  example: { size: [640, 248], parts: [
    { id: 'M', type: 'manifold', x: 40, y: 46, w: 560, label: 'bunker manifold',
      outlets: [{ label: 'liquid 1' }, { label: 'liquid 2' }, { label: 'vapour return' }, { label: 'spare' }], value: 0 } ],
    steps: [ { title: 'Liquid 1 is connected, the others stay blanked', play: [['M', 1, 1200]] },
             { title: 'The vapour return is connected too', play: [['M', 3, 1800]] } ] }
});
/* end kit-part */
/* kit-part: spool_piece */
KIT.define('spool_piece', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 560, t = p.t || 26, sl = p.spool || 120, lift = p.lift || 64, fl = 10;
  var gx = (w - sl) / 2, words = p.words || ['SEGREGATED', 'CONNECTED'], fh = t + 10;
  function pipe(x0, x1) {
    h.el('rect', { x: x0, y: -t / 2, width: x1 - x0, height: t, 'class': 'kit-steel' }, g);
    return h.el('rect', { x: x0 + 3, y: -t / 2 + 5, width: Math.max(1, x1 - x0 - 6), height: t - 10, 'class': 'kit-liquid' }, g);
  }
  function support(x) {                                 // a pipe saddle under the pipe
    h.el('path', { d: 'M' + (x - 6) + ' ' + t / 2 + ' L' + (x + 6) + ' ' + t / 2 + ' L' + (x + 16) + ' ' + (t / 2 + 16) + ' L' + (x - 16) + ' ' + (t / 2 + 16) + ' Z', 'class': 'kit-spool-piece-support' }, g);
  }
  pipe(0, gx - fl);
  var rightFill = pipe(gx + sl + fl, w);
  [18, gx - fl - 18, gx + sl + fl + 18, w - 18].forEach(support);
  h.el('rect', { x: gx - fl, y: -fh / 2, width: fl, height: fh, rx: 2, 'class': 'kit-spool-piece-flange' }, g);
  h.el('rect', { x: gx + sl, y: -fh / 2, width: fl, height: fh, rx: 2, 'class': 'kit-spool-piece-flange' }, g);
  var sg = h.el('g', { 'class': 'kit-spool-piece-spool' }, g);
  h.el('rect', { x: gx + fl, y: -t / 2, width: sl - 2 * fl, height: t, 'class': 'kit-steel' }, sg);
  var sFill = h.el('rect', { x: gx + fl, y: -t / 2 + 5, width: sl - 2 * fl, height: t - 10, 'class': 'kit-liquid' }, sg);
  h.el('rect', { x: gx, y: -fh / 2, width: fl, height: fh, rx: 2, 'class': 'kit-spool-piece-flange' }, sg);
  h.el('rect', { x: gx + sl - fl, y: -fh / 2, width: fl, height: fh, rx: 2, 'class': 'kit-spool-piece-flange' }, sg);
  var bl = h.el('rect', { x: gx, y: -fh / 2, width: 12, height: fh, rx: 2, 'class': 'kit-spool-piece-blind', 'data-may-cross': '' }, g);
  var br = h.el('rect', { x: gx + sl - 12, y: -fh / 2, width: 12, height: fh, rx: 2, 'class': 'kit-spool-piece-blind', 'data-may-cross': '' }, g);
  /* the spool's name stays where the spool is parked (a label that moves with the spool would be placed over both places) */
  if (p.spoolLabel) h.label(fig, g, { x: gx + sl / 2, y: -fh / 2 - lift - 10, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.spoolLabel);
  if (p.left) h.label(fig, g, { x: (gx - fl) / 2, y: fh / 2 + 24, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.left);
  if (p.right) h.label(fig, g, { x: w - (gx - fl) / 2, y: fh / 2 + 24, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.right);
  var lg = h.label(fig, g, {}, ''), ny = fh / 2 + 24, nl = 0;
  if (p.label) nl = h.lines(lg, { x: w / 2, y: ny, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  var st = h.el('text', { x: w / 2, y: ny, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state kit-spool-piece-st' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 1);
    sg.setAttribute('transform', 'translate(0 ' + (-(1 - c) * lift).toFixed(1) + ')');
    sg.style.opacity = (0.75 + 0.25 * c).toFixed(2);
    sFill.style.opacity = c > 0.5 ? '1' : '0';
    rightFill.style.opacity = c > 0.5 ? '1' : '0';
    bl.style.opacity = (1 - c).toFixed(2); br.style.opacity = (1 - c).toFixed(2);
    st.textContent = c > 0.5 ? words[1] : words[0];
    g.classList.toggle('kit-spool-piece-seg', c <= 0.5);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M07 segregation of a gas line: two flanged pipe ends with a removable spool between them - fitted, the line is connected; removed, a blank flange on each end keeps the gas from passing (plan: media plan of module 7)',
  value: '1 the spool is fitted and the line connected, 0 the spool is removed (it lifts away) and a blank flange is fitted on each end - SEGREGATED; between, it moves',
  css: '.kit-spool-piece-flange{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}' +
    '.kit-spool-piece-support{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:2;stroke-linejoin:round}' +
    '.kit-spool-piece-blind{fill:var(--dim-d);stroke:var(--txt-d);stroke-width:1.5}' +
    '.kit-spool-piece-seg .kit-spool-piece-st{fill:var(--blue)}',
  example: { size: [640, 190], parts: [
    { id: 'K', type: 'tank', x: 8, y: 54, w: 132, h: 100, label: 'LNG tank', value: 0.7 },
    { id: 'S', type: 'spool_piece', x: 140, y: 104, w: 370, t: 30, spool: 130, lift: 46, label: 'gas supply line', left: 'tank side', right: 'engine side', spoolLabel: 'spool piece', value: 1 },
    { id: 'E', type: 'engine', x: 510, y: 69, w: 122, h: 70, cylinders: 3, label: 'dual-fuel engine', value: 1 } ],
    steps: [ { title: 'The spool is removed and each end blanked - no gas reaches the engine', play: [['S', 0, 1800], ['E', 0, 300, 1800]] },
             { title: 'The spool is fitted again - the line is connected', play: [['S', 1, 1800], ['E', 1, 300, 1800]] } ] }
});
/* end kit-part */
/* kit-part: tank_wall */
KIT.define('tank_wall', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 300, def = [{ label: 'inner tank', kind: 'steel', h: 28 }, { label: 'insulation', kind: 'foam', h: 90 },
    { label: 'secondary barrier', kind: 'barrier', h: 24 }, { label: 'hull', kind: 'steel', h: 44 }];
  var layers = p.layers || def, y = 0, lx = w + 16;
  function kind(l) {
    if (l.kind) return l.kind;
    return /insul|foam|perlite/i.test(l.label || '') ? 'foam' : (/barrier|membrane/i.test(l.label || '') ? 'barrier' : 'steel');
  }
  if (p.insideLabel) {                                  // the cargo side
    h.el('rect', { x: 0, y: 0, width: w, height: 52, 'class': 'kit-liquid', 'data-no-contain': '' }, g);
    h.el('line', { x1: 0, x2: w, y1: 0, y2: 0, 'class': 'kit-surface', 'data-may-cross': '' }, g);
    h.label(fig, g, { x: lx, y: 31, 'text-anchor': 'start', 'class': 'kit-h' }, p.insideLabel);
    y = 52;
  }
  var made = layers.map(function (l, i) {
    var lh = l.h || def[Math.min(i, def.length - 1)].h, k = kind(l), lg = h.el('g', { 'class': 'kit-tank-wall-layer' }, g), y1 = y;
    h.el('rect', { x: 0, y: y1, width: w, height: lh, 'class': 'kit-tank-wall-' + k }, lg);
    if (k === 'foam') {
      for (var r = 1; r <= 3; r++) {
        h.el('line', { x1: 14, x2: w - 14, y1: y1 + lh * r / 4, y2: y1 + lh * r / 4, 'class': 'kit-tank-wall-cells' }, lg);
      }
    }
    var wash = h.el('rect', { x: 0, y: y1, width: w, height: lh, 'class': 'kit-tank-wall-wash', 'data-may-overlap': '' }, lg);
    h.label(fig, lg, { x: lx, y: y1 + lh / 2 + 4.5, 'text-anchor': 'start', 'class': 'kit-cap kit-tank-wall-nm' }, l.label || '');
    y += lh;
    return { g: lg, wash: wash };
  });
  if (p.outsideLabel) {
    h.el('rect', { x: 0, y: y, width: w, height: 48, 'class': 'kit-tank-wall-out', 'data-no-contain': '' }, g);
    h.label(fig, g, { x: lx, y: y + 29, 'text-anchor': 'start', 'class': 'kit-h' }, p.outsideLabel);
  }
  part.render = function (v) {
    made.forEach(function (m, i) {
      var pick = h.clamp(1 - Math.abs(v - (i + 1)), 0, 1);
      m.wash.style.opacity = (pick * 0.55).toFixed(2);
      m.g.classList.toggle('kit-tank-wall-lit', pick > 0.5);
    });
  };
}, {
  family: 'cutaways',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M07 the wall of a cryogenic LNG tank, cut away: inner tank, insulation, secondary barrier and hull, named from the cargo outward (plan: media plan of module 7)',
  value: '0..n: layer k (counted from the cargo side, 1..n) is picked out while the value is about k, and 0 picks none; layers:[{label, kind steel|foam|barrier, h}] renames or drops layers',
  css: '.kit-tank-wall-steel{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:2}' +
    '.kit-tank-wall-foam{fill:var(--deep);stroke:var(--faint-d);stroke-width:2}' +
    '.kit-tank-wall-barrier{fill:var(--deep-2);stroke:var(--cold);stroke-width:2.5}' +
    '.kit-tank-wall-cells{stroke:var(--dim-d);stroke-width:3;stroke-dasharray:2 9;stroke-linecap:round}' +
    '.kit-tank-wall-wash{fill:var(--blue);opacity:0}' +
    '.kit-tank-wall-out{fill:var(--deep);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:6 5}' +
    '.kit-tank-wall-lit .kit-tank-wall-nm{fill:var(--txt-d);font-weight:700}',
  example: { size: [470, 318], parts: [
    { id: 'W', type: 'tank_wall', x: 20, y: 16, w: 300, insideLabel: 'LNG, -163 °C', outsideLabel: 'sea', value: 0 } ],
    steps: [ { title: 'The inner tank holds the LNG', play: [['W', 1, 700]] },
             { title: 'The insulation keeps the cold in', play: [['W', 2, 700]] },
             { title: 'The secondary barrier catches a leak', play: [['W', 3, 700]] },
             { title: 'The hull is the ship\'s own steel', play: [['W', 4, 700]] } ] }
});
/* end kit-part */
/* kit-part: spill */
KIT.define('spill', function (fig, part, g, p) {
  /* THE BOX (2.49.2): the part is drawn inside [0, w] x [0, h] at its x, y - the nozzle's top at y, the surface 124 under it, then
     the plate or the water, then the name and READY-like word. "h" (default: as tall as that takes) shortens the nozzle to fit
     a shorter box; the pool and its vapour never reach past the sides (the wave is cut at w, a "reach" larger than the room is
     held to it). It was drawn from y + 26 down to y + 254 whatever the spec said, so a figure that placed it by its box grew. */
  var h = KIT.h, w = p.w || 300, water = p.surface === 'water', T = water ? 50 : 16;
  var rows = p.label ? String(p.label).split('\n').length : 0, below = T + 30 + 16 * rows + 20;
  // the surface, from the top of the part: a spec's surfaceY as before, else from "h", else 150 as before 2.49.2 - an
  // approved drawing (IGF M06 s11, M15 s02) never moves because the kit changed
  var S = p.surfaceY != null ? p.surfaceY : p.h ? h.clamp(p.h - below, 90, 600) : 150;
  var fx = p.from != null ? p.from : w / 2, room = Math.max(0, Math.min(fx, w - fx) - 8);
  var reach = Math.min(p.reach || room, room), words = p.words || ['SPREADING', 'BOILING OFF'];
  var ht = water ? 4 : 7, wisps = [], bubs = [], i;
  if (water) {
    h.el('rect', { x: 0, y: S, width: w, height: T, 'class': 'kit-spill-water', 'data-low-contrast': '', 'data-no-contain': '' }, g);
    var d = 'M0 ' + S, nw = Math.floor(w / 30);
    for (i = 0; i < nw; i++) d += ' q 7.5 -6 15 0 t 15 0';
    if (w - nw * 30 > 0.5) d += ' H' + w;                                 // the last part-wave is a straight run to the edge
    h.el('path', { d: d, 'class': 'kit-spill-wave', 'data-may-cross': '' }, g);
  } else {
    h.el('rect', { x: 0, y: S, width: w, height: T, 'class': 'kit-steel' }, g);
    for (i = 30; i < w; i += 60) h.el('path', { d: 'M' + i + ' ' + (S + T) + ' V' + (S + 34), 'class': 'kit-spill-beam' }, g);   // the stiffeners under the deck plate
  }
  var nz = Math.max(10, Math.min(46, S - 78));                           // the nozzle, shortened when the box is
  h.el('rect', { x: fx - 7, y: S - 78 - nz, width: 14, height: nz, 'class': 'kit-steel' }, g);
  h.el('rect', { x: fx - 15, y: S - 78, width: 30, height: 7, rx: 2, 'class': 'kit-spill-flange' }, g);
  var stream = h.el('line', { x1: fx, x2: fx, y1: S - 71, y2: S - 1, 'class': 'kit-spill-stream', 'data-may-cross': '' }, g);
  var pool = h.el('path', { d: 'M' + fx + ' ' + S, 'class': 'kit-spill-pool', 'data-may-cross': '' }, g);
  var fr = [-0.82, -0.52, -0.22, 0.12, 0.42, 0.72, 0.95];
  fr.forEach(function (f, j) {
    bubs.push(h.el('circle', { r: 3 + (j % 3), 'class': 'kit-spill-bub', 'data-low-contrast': '', 'data-may-cross': '' }, g));
    var wg = h.el('g', {}, g);
    h.el('path', { d: 'M0 0 q 7 -10 0 -20 t 0 -20 t 0 -20', 'class': 'kit-spill-wisp', 'data-low-contrast': '', 'data-may-cross': '' }, wg);
    wisps.push(wg);
  });
  var lg = h.label(fig, g, {}, ''), ly = S + T + 30, nl = 0;       // under the plate or the water: its name, then the word for what the pool does
  if (p.label) nl = h.lines(lg, { x: w / 2, y: ly, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  var st = h.el('text', { x: w / 2, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state kit-spill-st' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 1), r = reach * (water ? 1 - Math.pow(1 - c, 2.2) : Math.pow(c, 0.8)), boil = h.clamp((c - 0.45) / 0.4, 0, 1);
    stream.style.opacity = c > 0.01 ? '1' : '0';
    pool.setAttribute('d', r < 1 ? 'M' + fx + ' ' + S : 'M' + (fx - r).toFixed(1) + ' ' + S + ' Q' + fx + ' ' + (S - 2 * ht) + ' ' + (fx + r).toFixed(1) + ' ' + S + ' Z');
    wisps.forEach(function (wg, j) {
      var x = fx + fr[j] * r, sc = boil * (water ? 1.35 : 1) * (0.7 + 0.1 * (j % 4));
      wg.setAttribute('transform', 'translate(' + x.toFixed(1) + ' ' + (S - ht - 6) + ') scale(1 ' + sc.toFixed(2) + ')');
      wg.style.opacity = boil.toFixed(2);
      bubs[j].setAttribute('cx', x.toFixed(1)); bubs[j].setAttribute('cy', (S - ht - 3 - 3 * (j % 3)).toFixed(1));
      bubs[j].style.opacity = boil.toFixed(2);
    });
    st.textContent = c < 0.02 ? '' : (boil > 0.5 ? words[1] : words[0]);
    g.classList.toggle('kit-spill-boil', boil > 0.5);
  };
  part.motion = function (d) { g.classList.toggle('kit-spill-live', d > 0); };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M15 LNG spilt on the deck and on the water: a pool spreads from the leak (far wider and thinner on water) and boils off in vapour - why the deck is steel and why water is not a safe place for a spill (plan: media plan of module 15)',
  value: '0..1 how far the pool has spread from the leak; from about 0.5 it boils (bubbles and rising vapour wisps); surface "deck" or "water" (drawn as water, the pool spreads wider and boils harder); drawn inside its box x..x+w, y..y+h (2.49.2): the nozzle top at y, h 206 (deck) or 240 (water) unless the spec gives a shorter one, which shortens the nozzle',
  css: '.kit-spill-water{fill:var(--cold);fill-opacity:.14;stroke:none}' +
    '.kit-spill-wave{fill:none;stroke:var(--cold);stroke-width:2.5}' +
    '.kit-spill-beam{fill:none;stroke:var(--faint-d);stroke-width:3}' +
    '.kit-spill-flange{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2}' +
    '.kit-spill-stream{stroke:var(--cold);stroke-width:3;opacity:0}' +
    '.kit-spill-pool{fill:var(--cold);fill-opacity:.7;stroke:var(--cold);stroke-width:1.5;stroke-linejoin:round}' +
    '.kit-spill-bub{fill:none;stroke:var(--txt-d);stroke-width:1.5;opacity:0}' +
    '.kit-spill-wisp{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round;opacity:.45}' +
    '.kit-spill-live .kit-spill-wisp{animation:kit-spill-rise 1.1s ease-out infinite}' +
    '@keyframes kit-spill-rise{0%{opacity:.15}100%{opacity:.6}}',
  example: { size: [640, 260], parts: [
    { id: 'D', type: 'spill', x: 10, y: 10, w: 300, surface: 'deck', label: 'LNG on deck', value: 0 },
    { id: 'W', type: 'spill', x: 330, y: 10, w: 300, surface: 'water', label: 'LNG on water', value: 0 } ],
    steps: [ { title: 'The LNG spreads - much further and thinner on water', play: [['D', 0.4, 1800, 0, 'linear'], ['W', 0.55, 1800, 0, 'linear']] },
             { title: 'Both pools boil off in vapour', play: [['D', 1, 2200, 0, 'linear'], ['W', 1, 2200, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: wind */
KIT.define('wind', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 260, rows = p.rows || 5, gap = p.gap || 34, ht = gap * (rows - 1), words = p.words || ['CALM', 'LIGHT', 'MODERATE', 'STRONG'];
  var cx = w / 2, cy = ht / 2, ang = (p.dir || 0) * Math.PI / 180, off = [0.04, 0.2, 0, 0.14, 0.09], mul = [1, 0.8, 1.1, 0.7, 0.95];
  var R = Math.abs(cx * Math.sin(ang)) + Math.abs(cy * Math.cos(ang));          // half the height of the turned drawing
  var rg = h.el('g', { transform: 'rotate(' + (p.dir || 0) + ' ' + cx + ' ' + cy + ')' }, g), streaks = [];
  for (var i = 0; i < rows; i++) {
    var sg = h.el('g', { 'class': 'kit-wind-streak' }, rg);
    streaks.push({
      line: h.el('line', { y1: i * gap, y2: i * gap, 'class': 'kit-wind-line', 'data-may-cross': '' }, sg),
      head: h.el('path', { d: 'M0 -7 L13 0 L0 7 Z', 'class': 'kit-wind-head', 'data-may-cross': '' }, sg), g: sg, y: i * gap, o: off[i % off.length], m: mul[i % mul.length]
    });
  }
  var lg = h.label(fig, g, {}, ''), ly = cy + R + 24, nl = 0;
  if (p.label) nl = h.lines(lg, { x: cx, y: ly, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  var st = h.el('text', { x: cx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 1);
    streaks.forEach(function (s, i) {
      var len = w * (0.22 + 0.5 * c) * s.m, x0 = s.o * w * (0.4 + c), vis = h.clamp((c - i * 0.12) * 8, 0, 1);
      s.line.setAttribute('x1', x0.toFixed(1)); s.line.setAttribute('x2', (x0 + len - 6).toFixed(1));
      s.head.setAttribute('transform', 'translate(' + (x0 + len - 6).toFixed(1) + ' ' + s.y + ')');
      s.g.style.opacity = (0.8 + 0.2 * vis).toFixed(2);
    });
    st.textContent = p.max ? Math.round(c * p.max) + (p.unit ? ' ' + p.unit : '') : (c < 0.05 ? words[0] : (c < 0.4 ? words[1] : (c < 0.75 ? words[2] : words[3])));
  };
  part.motion = function (d) { g.classList.toggle('kit-wind-live', d !== 0); };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M06 a vapour cloud drifts with the wind: the direction and strength of the wind that carries a leak away from, or over, the deck (plan: media plan of module 6)',
  value: '0..1 how strong the wind is: more and longer streaks, faster while it changes; dir is the way it blows, in degrees (0 = to the right, 90 = down); with max and unit the words are a reading (12 m/s), else CALM / LIGHT / MODERATE / STRONG',
  css: '.kit-wind-line{stroke:var(--cold);stroke-width:3.5;stroke-linecap:round}' +
    '.kit-wind-head{fill:var(--cold)}' +
    '.kit-wind-live .kit-wind-line{stroke-dasharray:26 14;animation:kit-wind-run .6s linear infinite}' +
    '@keyframes kit-wind-run{to{stroke-dashoffset:-40}}',
  example: { size: [640, 330], parts: [
    { id: 'R', type: 'space', x: 10, y: 40, w: 270, h: 210, label: 'open deck', value: 0 },
    { id: 'C', type: 'gas_cloud', x: 15, y: 50, w: 260, h: 190, from: [70, 130], value: 0 },
    { id: 'W', type: 'wind', x: 320, y: 56, w: 300, rows: 6, gap: 40, dir: 0, label: 'wind', value: 0 } ],
    steps: [ { title: 'A light wind - the gas gathers slowly', play: [['W', 0.3, 1400], ['C', 0.5, 2000, 0, 'linear']] },
             { title: 'A strong wind carries the cloud away', play: [['W', 1, 1600], ['C', 1, 2000, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-part: tree */
KIT.define('tree', function (fig, part, g, p) {
  var h = KIT.h, nodes = [], kids = [];
  function norm(n) { return typeof n === 'string' ? { label: n } : n; }
  var link = h.el('path', { d: 'M0 0', 'class': 'kit-tree-link' }, g);
  var probeH = h.el('text', { x: 0, y: 0, 'class': 'kit-h kit-tree-probe' }, g, ''), probeC = h.el('text', { x: 0, y: 0, 'class': 'kit-cap kit-tree-probe' }, g, '');
  function make(n, big, level) {
    var ng = h.el('g', { 'class': 'kit-tree-node' }, g), rect = h.el('rect', { rx: 8, 'class': 'kit-tree-box' }, ng);
    var text = h.el('text', { x: 0, y: 0, 'text-anchor': 'middle', 'class': big ? 'kit-h' : 'kit-cap' }, ng);
    var rows = String(n.label || '').split('\n');
    rows.forEach(function (s, i) { h.el('tspan', { x: 0, dy: i ? (16 / 12.5).toFixed(3) + 'em' : 0 }, text, s); });
    var o = { g: ng, rect: rect, text: text, rows: rows, rows0: rows.slice(), big: big, level: level, w: 0, h: 0, x: 0, y: 0, kids: [] };
    nodes.push(o);
    return o;
  }
  var root = make(norm(p.root || { label: '' }), true, 0);
  (p.children || []).forEach(function (c) {
    var n = norm(c), o = make(n, false, 1);
    root.kids.push(o); kids.push(o);
  });
  (p.children || []).forEach(function (c, i) {            // the second level comes after the first, in reading order
    (norm(c).children || []).forEach(function (s) { kids[i].kids.push(make(norm(s), false, 2)); });
  });
  /* THE WIDTH (2.49.2): the tree is laid out to fit "w" (default: the figure's width less the tree's x and 10) and never
     wider - it drew a 640-wide figure's four columns 700+ wide, so the frame grew past what the type growth can follow and
     the words were left at 11.5 px. Three tries, each tighter (the box padding, the gap between columns, then the words
     broken at a space), the first that fits is used. */
  var W = p.w || ((fig.spec.size && fig.spec.size[0] || 640) - (p.x || 0) - 10);
  var CFG = [{ pad: 36, gapX: 26, minW: p.minW || 104, wrap: false }, { pad: 24, gapX: 14, minW: 80, wrap: false },
             { pad: 20, gapX: 10, minW: 64, wrap: true }];
  function rowsFor(o, c, room) {            // the words of a box, each row broken at its best space while it is wider than the room
    var probe = o.big ? probeH : probeC, out = [];
    function brk(s, left) {
      if (!c.wrap || left < 1 || h.widest(probe, [s]) <= room - c.pad || s.indexOf(' ') < 0) { out.push(s); return; }
      var best = null, bw = 1e9, re = / /g, m;
      while ((m = re.exec(s))) {
        var a = s.slice(0, m.index), b = s.slice(m.index + 1), ww = Math.max(h.widest(probe, [a]), h.widest(probe, [b]));
        if (ww < bw) { bw = ww; best = [a, b]; }
      }
      brk(best[0], left - 1); brk(best[1], left - 1);
    }
    o.rows0.forEach(function (s) { brk(s, 2); });
    return out;
  }
  function setRows(o, rows) {
    if (o.rows.join('\n') === rows.join('\n')) return;
    o.rows = rows;
    while (o.text.firstChild) o.text.removeChild(o.text.firstChild);
    rows.forEach(function (s, i) { h.el('tspan', { x: 0, dy: i ? (16 / 12.5).toFixed(3) + 'em' : 0 }, o.text, s); });
  }
  function size(o, k, c, room) {
    setRows(o, rowsFor(o, c, room));
    o.w = Math.max(c.minW, h.widest(o.big ? probeH : probeC, o.rows) + c.pad);
    o.h = o.rows.length * 16 * k + 28 * k;
  }
  function put(o, x, y, k) {
    o.x = x; o.y = y;
    o.rect.setAttribute('x', x.toFixed(1)); o.rect.setAttribute('y', y.toFixed(1));
    o.rect.setAttribute('width', o.w.toFixed(1)); o.rect.setAttribute('height', o.h.toFixed(1));
    var lh = 16 * k, top = y + (o.h - o.rows.length * lh) / 2, base = top + lh / 2 + 0.36 * (o.big ? 15 : 12.5) * k, cx = x + o.w / 2;
    o.text.setAttribute('x', cx.toFixed(1)); o.text.setAttribute('y', base.toFixed(1));
    [].forEach.call(o.text.childNodes, function (t) { t.setAttribute('x', cx.toFixed(1)); });
  }
  function place(k) {
    var gapY = 56 * Math.max(1, k * 0.9), ind = 28, rowH = 0, gapX, cols, rowW, c, ci;
    for (ci = 0; ci < CFG.length; ci++) {            // the first of the three tries whose columns fit the width
      c = CFG[ci]; gapX = c.gapX; rowH = 0;
      var colRoom = (W - gapX * Math.max(0, kids.length - 1)) / Math.max(1, kids.length);
      size(root, k, c, W);
      kids.forEach(function (o) { size(o, k, c, colRoom - (o.kids.length ? ind : 0)); o.kids.forEach(function (s) { size(s, k, c, colRoom - ind); }); });
      kids.forEach(function (o) { o.h = 0; rowH = Math.max(rowH, o.rows.length * 16 * k + 28 * k); });
      kids.forEach(function (o) { o.h = rowH; });
      cols = kids.map(function (o) {
        var gw = 0; o.kids.forEach(function (s) { gw = Math.max(gw, s.w); });
        return Math.max(o.w, o.kids.length ? ind + gw : 0);
      });
      rowW = cols.reduce(function (a, b) { return a + b; }, 0) + gapX * Math.max(0, kids.length - 1);
      if (Math.max(rowW, root.w) <= W + 0.5) break;
    }
    var total = Math.max(rowW, root.w), x = (total - rowW) / 2, d = '';
    put(root, (total - root.w) / 2, 0, k);
    var rcx = root.x + root.w / 2, busY = root.h + gapY / 2, y1 = root.h + gapY;
    var firstCx = 0, lastCx = 0;
    kids.forEach(function (o, i) {
      put(o, x, y1, k);
      var ccx = o.x + o.w / 2;
      if (i === 0) firstCx = ccx;
      lastCx = ccx;
      d += 'M' + ccx.toFixed(1) + ' ' + busY.toFixed(1) + ' V' + y1.toFixed(1);
      if (o.kids.length) {
        var sx = o.x + 12, yy = y1 + o.h + 12, yEnd = yy;
        o.kids.forEach(function (s) {
          put(s, o.x + ind, yy, k);
          yEnd = yy + s.h / 2;
          d += 'M' + sx.toFixed(1) + ' ' + yEnd.toFixed(1) + ' H' + s.x.toFixed(1);
          yy += s.h + 10;
        });
        d += 'M' + sx.toFixed(1) + ' ' + (y1 + o.h).toFixed(1) + ' V' + yEnd.toFixed(1);
      }
      x += cols[i] + gapX;
    });
    if (kids.length) d += 'M' + rcx.toFixed(1) + ' ' + root.h.toFixed(1) + ' V' + busY.toFixed(1) + ' M' + firstCx.toFixed(1) + ' ' + busY.toFixed(1) + ' H' + lastCx.toFixed(1);
    link.setAttribute('d', d || 'M0 0');
  }
  place(1);
  fig.fit(place);
  part.render = function (v) {
    var idx = Math.round(v);
    nodes.forEach(function (o, i) {
      o.g.classList.toggle('kit-tree-lit', idx === i + 1);
      o.g.classList.toggle('kit-tree-seen', idx > i + 1);
    });
  };
}, {
  family: 'procedures',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  why: 'M14 the emergency organisation and M15 the reporting chain: who leads and who reports to whom, as boxes joined by lines (plan: media plans of modules 14 and 15)',
  value: '0..n lights box k, in reading order (the root is 1, then its children left to right, then the second level under them in the same order); 0 lights none, and the boxes passed keep a blue edge',
  css: '.kit-tree-probe{opacity:0}' +
    '.kit-tree-link{fill:none;stroke:var(--faint-d);stroke-width:2;stroke-linejoin:round}' +
    '.kit-tree-box{fill:var(--deep-3);stroke:var(--faint-d);stroke-width:2}' +
    '.kit-tree-seen .kit-tree-box{stroke:var(--blue)}' +
    '.kit-tree-lit .kit-tree-box{fill:var(--deep);stroke:var(--blue);stroke-width:3.5}' +
    '.kit-tree-lit text{fill:var(--txt-d)}',
  example: { size: [520, 300], parts: [
    { id: 'T', type: 'tree', x: 10, y: 10, root: 'Master', value: 0,
      children: [{ label: 'Chief officer\n(on-scene leader)', children: ['Deck team', 'Fire team'] },
                 { label: 'Chief engineer\n(engine control)', children: ['Engine team'] },
                 { label: 'Second officer\n(communications)' }] } ],
    steps: [ { title: 'The master commands the emergency', play: [['T', 1, 500]] },
             { title: 'The chief officer leads on the scene', play: [['T', 2, 500]] },
             { title: 'The deck team reports to the chief officer', play: [['T', 5, 600]] } ] }
});
/* end kit-part */
/* kit-part: lamp */
KIT.define('lamp', function (fig, part, g, p) {
  var h = KIT.h, ex = !!p.ex, cy = 22, r0 = ex ? 40 : 25, i;
  h.el('line', { x1: 0, x2: 0, y1: -28, y2: -8, 'class': 'kit-lamp-stem' }, g);                     // the cable down from the deckhead
  h.el('path', { d: 'M-12 -8 H12 V2 H-12 Z', 'class': 'kit-lamp-cap' }, g);                         // the fitting
  var rays = h.el('g', { 'class': 'kit-lamp-rays' }, g);
  for (i = 0; i < 7; i++) {
    var a = 25 + i * 21.67, q0 = h.polar(r0, a), q1 = h.polar(r0 + 12, a);
    h.el('line', { x1: q0[0].toFixed(1), y1: (cy + q0[1]).toFixed(1), x2: q1[0].toFixed(1), y2: (cy + q1[1]).toFixed(1) }, rays);
  }
  h.el('circle', { cx: 0, cy: cy, r: 16, 'class': 'kit-lamp-bulb' }, g);
  /* an explosion-protected (Ex) fitting: the glass sits inside a heavy enclosure that holds any spark in */
  if (ex) h.el('rect', { x: -27, y: -4, width: 54, height: 52, rx: 12, 'class': 'kit-lamp-ex', 'data-no-contain': '' }, g);
  if (p.label) h.label(fig, g, { x: 0, y: cy + r0 + 38, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    rays.style.opacity = k > 0.02 ? k.toFixed(2) : '0';
    g.classList.toggle('kit-lamp-on', k > 0.5);
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M06",
  course: 'IGF Basic', module: 'M06', made: '2026-10-16',
  why: 'M06 ignition sources: electrical equipment (a light fitting, a switch, a motor) is an ignition source in a gas-dangerous space unless it is explosion-protected - an ordinary lamp and an Ex-protected one side by side',
  value: '0 off, 1 lit (the glass fills and its rays show); option ex: true draws the heavy explosion-protected enclosure round the glass',
  css: '.kit-lamp-stem{stroke:var(--dim-d);stroke-width:3;stroke-linecap:round}' +
    '.kit-lamp-cap{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2;stroke-linejoin:round}' +
    '.kit-lamp-bulb{fill:var(--deep);stroke:var(--dim-d);stroke-width:2.5}' +
    '.kit-lamp-on .kit-lamp-bulb{fill:var(--txt-d);stroke:var(--txt-d)}' +
    '.kit-lamp-rays line{stroke:var(--txt-d);stroke-width:3;stroke-linecap:round;stroke-dasharray:6 5}' +
    '.kit-lamp-ex{fill:none;stroke:var(--dim-d);stroke-width:4.5;stroke-linejoin:round}',
  example: { size: [380, 190], parts: [
    { id: 'A', type: 'lamp', x: 100, y: 40, label: 'ordinary lamp' },
    { id: 'B', type: 'lamp', x: 280, y: 40, ex: true, label: 'Ex-protected lamp' } ],
    steps: [ { title: 'Both are switched on', play: [['A', 1, 700], ['B', 1, 700]] } ] }
});
/* end kit-part */
/* kit-part: spark */
KIT.define('spark', function (fig, part, g, p) {
  var h = KIT.h, fric = p.kind === 'friction', to = p.to && p.to.length === 2 ? p.to : [70, 0], i;
  var burst = h.el('g', {}, g), flick = h.el('g', { 'class': 'kit-spark-flick' }, burst), cx = 0, cy = 0;
  if (fric) {
    /* friction: a tool or a chain scraping steel throws a burst of hot particles from the point of contact */
    var lens = [30, 20, 34, 22, 28, 18, 33, 24, 29, 21];
    for (i = 0; i < 10; i++) {
      var a = -170 + i * 18.9, q0 = h.polar(8, a), q1 = h.polar(lens[i], a);
      h.el('line', { x1: q0[0].toFixed(1), y1: q0[1].toFixed(1), x2: q1[0].toFixed(1), y2: q1[1].toFixed(1), 'class': 'kit-spark-ray' }, flick);
    }
    h.el('circle', { cx: 0, cy: 0, r: 5, 'class': 'kit-spark-hot' }, flick);
  } else {
    /* electric: an arc jumps across the gap between two contacts - a zig-zag from (0, 0) to the point "to" */
    var len = Math.sqrt(to[0] * to[0] + to[1] * to[1]) || 1, ux = to[0] / len, uy = to[1] / len, amp = Math.min(14, len * 0.16), d = 'M0 0';
    for (i = 1; i < 6; i++) {
      var f = len * i / 6, s = i % 2 ? 1 : -1;
      d += ' L' + (ux * f - uy * amp * s).toFixed(1) + ' ' + (uy * f + ux * amp * s).toFixed(1);
    }
    h.el('path', { d: d + ' L' + to[0] + ' ' + to[1], 'class': 'kit-spark-bolt' }, flick);
    h.el('circle', { cx: 0, cy: 0, r: 5, 'class': 'kit-spark-contact' }, g);                          // the two contacts stay drawn at rest
    h.el('circle', { cx: to[0], cy: to[1], r: 5, 'class': 'kit-spark-contact' }, g);
    cx = to[0] / 2; cy = to[1] / 2;
  }
  if (p.label) h.label(fig, g, { x: cx, y: cy - (fric ? 44 : 26), 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    burst.setAttribute('transform', 'translate(' + cx + ' ' + cy + ') scale(' + (0.4 + 0.6 * k).toFixed(3) + ') translate(' + (-cx) + ' ' + (-cy) + ')');
    burst.style.opacity = k > 0.02 ? '1' : '0';
    g.classList.toggle('kit-spark-on', k > 0.05);
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M06",
  course: 'IGF Basic', module: 'M06', made: '2026-10-16',
  why: 'M06 ignition sources: an electric spark (a switch or a loose contact) and a frictional spark (a tool, a chain or a rope scraping steel) - the small energy that lights a gas-air mixture',
  value: '0 no spark, 1 the spark at full; kind "electric" (default: an arc jumps from this point to to: [dx, dy]) or "friction" (hot particles thrown from this point); the two contacts of an electric spark stay drawn at rest',
  css: '.kit-spark-bolt{fill:none;stroke:var(--amber);stroke-width:3.5;stroke-linejoin:round;stroke-linecap:round}' +
    '.kit-spark-ray{stroke:var(--amber);stroke-width:3;stroke-linecap:round}' +
    '.kit-spark-hot{fill:var(--amber)}' +
    '.kit-spark-contact{fill:var(--deep-3);stroke:var(--dim-d);stroke-width:2.5}' +
    '.kit-spark-on .kit-spark-flick{transform-box:fill-box;transform-origin:center;animation:kit-spark-flick .18s steps(1) infinite alternate}' +
    '@keyframes kit-spark-flick{to{transform:scale(1.14) rotate(5deg)}}',
  example: { size: [460, 190], parts: [
    { id: 'E', type: 'spark', x: 60, y: 110, to: [110, 0], label: 'electric spark' },
    { id: 'F', type: 'spark', x: 340, y: 110, kind: 'friction', label: 'frictional spark' } ],
    steps: [ { title: 'A switch is made', play: [['E', 1, 500]] }, { title: 'A tool scrapes steel', play: [['F', 1, 500]] } ] }
});
/* end kit-part */
/* kit-part: composition_bar */
KIT.define('composition_bar', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 460, bh = p.h || 38, segs = p.segments || [], unit = p.unit != null ? p.unit : '%', total = +p.total || 0;
  if (!total) segs.forEach(function (s) { total += +s.pct || 0; });
  total = total || 100;
  h.el('rect', { width: w, height: bh, rx: 4, 'class': 'kit-composition-bar-frame', 'data-no-contain': '' }, g);
  var x0 = 0, made = segs.map(function (s, i) {
    var wd = Math.max(2, (+s.pct || 0) / total * w), cx = x0 + wd / 2, up = i % 2 === 0;
    var rect = h.el('rect', { x: x0, y: 0, width: 0, height: bh, 'class': 'kit-composition-bar-s kit-composition-bar-t' + (i % 4) }, g);
    var words = (s.label || '') + '\n' + h.num(+s.pct || 0, s.decimals != null ? s.decimals : ((+s.pct || 0) % 1 ? 1 : 0)) + (unit ? ' ' + unit : '');
    var lb = h.label(fig, g, { x: cx, y: up ? -28 : bh + 24, 'text-anchor': 'middle', 'class': 'kit-cap' }, words, { near: 24, lead: true });
    var o = { rect: rect, x: x0, w: wd, lb: lb, up: up, t: lb.querySelector('text') };
    x0 += wd;
    return o;
  });
  if (p.label) var title = h.label(fig, g, { x: 0, y: -62, 'text-anchor': 'start', 'class': 'kit-h' }, p.label);
  fig.fit(function (k) {
    made.forEach(function (o) { o.t.setAttribute('y', (o.up ? -(10 + 4.5 * k + 16 * k) : bh + 8 + 14 * k).toFixed(1)); });
    if (title) title.querySelector('text').setAttribute('y', (-(26 + 36 * k)).toFixed(1));
  });
  part.render = function (v) {
    made.forEach(function (o, k) {
      var c = h.clamp(v - k, 0, 1);
      o.rect.setAttribute('width', (o.w * c).toFixed(1));
      o.rect.style.opacity = c > 0.001 ? '1' : '0';
      o.lb.style.opacity = c > 0.5 ? '1' : '0';
    });
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M06",
  course: 'IGF Basic', module: 'M06', made: '2026-10-16',
  why: 'M06 what a fuel is made of: natural gas is mostly methane with some ethane, propane and nitrogen - one bar split into the shares of its components',
  value: '0..n segments: segment k fills from its left edge while the value goes from k to k+1, and its name and share appear once it is half drawn; segments: [{label, pct}], total (default: the sum), unit (default %)',
  css: '.kit-composition-bar-frame{fill:none;stroke:var(--dim-d);stroke-width:2}' +
    '.kit-composition-bar-s{stroke:var(--deep-2);stroke-width:2}' +
    '.kit-composition-bar-t0{fill:var(--cold)}.kit-composition-bar-t1{fill:var(--dim-d)}' +
    '.kit-composition-bar-t2{fill:var(--blue)}.kit-composition-bar-t3{fill:var(--faint-d)}',
  example: { size: [540, 210], parts: [
    { id: 'C', type: 'composition_bar', x: 40, y: 100, w: 460, label: 'natural gas, share by volume',
      segments: [{ label: 'methane', pct: 90 }, { label: 'ethane', pct: 5 }, { label: 'propane', pct: 3 }, { label: 'nitrogen', pct: 2 }], value: 0 } ],
    steps: [ { title: 'Methane is most of it', play: [['C', 1, 900]] }, { title: 'The rest is ethane, propane and nitrogen', play: [['C', 4, 1800, 0, 'linear']] } ] }
});
/* end kit-part */
/* kit-parts: end */
