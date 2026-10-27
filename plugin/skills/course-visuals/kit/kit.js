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
  /* a part's own words go and come back with what it draws (2.60.0): a fire that is out takes its name with it - "gas
     burning at the mast" stood beside a mast with no flame (IGF M05 s10, M06 s12, M11 s08, M13 s02 / s04). Opacity, never
     display: the words keep their place, so the layout and the steps where they show are unchanged. */
  function gone(w, out) {
    if (!w) return;
    var o = out ? '0' : '';
    w.style.opacity = o;
    w.__kitFade = out ? '0' : null;
    if (w.__kitLeader) w.__kitLeader.style.opacity = o;
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
  /* 2.66.0 - a drag (the approved scripts ask trainees to "drag the marker to 45 °C", and the kit had no way to): one
     invisible, focusable area over box {x, y, w, h} in g's own coordinates, moved by a finger, the mouse or the arrow keys.
     opt.move(x, y) gets the point in g's coordinates; opt.step(dx, dy) the arrow keys' nudges (-1 / +1). The press, the
     touch and the key never reach the deck: no swipe, no slide turned by an arrow key while the drawing has the focus.
     The area paints nothing (fill-opacity 0), so the drawing check sees only what is drawn. */
  function drag(g, box, opt) {
    var hit = el('rect', { x: box.x, y: box.y, width: box.w, height: box.h, 'class': 'kit-hit', tabindex: 0, role: 'slider',
      'aria-label': opt.name || 'drag to read the value', 'data-may-cross': '', 'data-may-overlap': '', 'data-kit-hit': '' }, g);
    var on = false;
    function local(e) {
      var m = g.getScreenCTM ? g.getScreenCTM() : null;
      if (!m) return null;
      m = m.inverse();
      return [e.clientX * m.a + e.clientY * m.c + m.e, e.clientX * m.b + e.clientY * m.d + m.f];
    }
    function stop(e) { e.stopPropagation(); }
    function to(e) { var q = local(e); if (q) opt.move(q[0], q[1]); }
    hit.addEventListener('pointerdown', function (e) {
      on = true; stop(e); e.preventDefault();
      try { if (hit.setPointerCapture) hit.setPointerCapture(e.pointerId); } catch (x) { /* an old WebView */ }
      try { hit.focus({ preventScroll: true }); } catch (x) { /* no focus() on svg there */ }
      to(e);
    });
    hit.addEventListener('pointermove', function (e) { if (on) { stop(e); to(e); } });
    ['pointerup', 'pointercancel'].forEach(function (ev) { hit.addEventListener(ev, function (e) { on = false; stop(e); }); });
    ['touchstart', 'touchmove', 'touchend', 'mousedown', 'click'].forEach(function (ev) {
      hit.addEventListener(ev, stop, ev.indexOf('touch') === 0 ? { passive: true } : false);
    });
    hit.addEventListener('keydown', function (e) {
      var d = { ArrowLeft: [-1, 0], Left: [-1, 0], ArrowRight: [1, 0], Right: [1, 0], ArrowUp: [0, -1], Up: [0, -1],
                ArrowDown: [0, 1], Down: [0, 1] }[e.key];
      if (!d) return;
      e.preventDefault(); stop(e);
      if (opt.step) opt.step(d[0], d[1]);
    });
    return hit;
  }
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

  /* MATERIALS (2.52.0, L63) - physical equipment is drawn as it looks on board: in its material, with light and shade, and
     its real features. The textures are drawn ONCE per page, in a hidden <svg id="kit-materials"> (never display:none -
     Chrome then drops its paint servers), and a part names a material by class (kit.css .kit-m-*), most often through
     body() below. Their colours are the kit's --mat-* tokens (kit.css); a paint server takes the colours of the place it
     is defined, so the light page has a set of its own (".kit-mat-light", ids ending -l) and kit.css points a figure on a
     light ground at it. Approved by the operator from the plain-vs-realistic mock-up, 2026-10-20. */
  var MAT_ID = 'kit-materials';
  /* the grain of a material: grey noise drawn ONCE per page into three small bitmaps - fine grain, brushed streaks, a
     mottle - carrying no colour of its own. Not an feTurbulence filter in the pattern: that was rendered again on every
     frame of every flow and piston, slow on a tablet, and a hidden browser never finished the page. Seeded, so every
     page and every screenshot shows the same grain. */
  function noiseTiles() {
    var out = {}, seed = 7, c, x2;
    try { c = document.createElement('canvas'); x2 = c.getContext && c.getContext('2d'); } catch (e) { x2 = null; }
    if (!x2) return out;
    function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    function bitmap(w, h, v) {
      c.width = w; c.height = h;
      var img = x2.createImageData(w, h), d = img.data, x, y, i;
      for (y = 0; y < h; y++) for (x = 0; x < w; x++) { i = (y * w + x) * 4; d[i] = d[i + 1] = d[i + 2] = Math.round(clamp(v(x, y), 0, 1) * 255); d[i + 3] = 255; }
      x2.putImageData(img, 0, 0);
      try { return c.toDataURL('image/png'); } catch (e) { return null; }
    }
    var G = [], x, y, B = [], M = [];
    for (y = 0; y < 64; y++) { G.push([]); for (x = 0; x < 64; x++) G[y].push(rnd()); }
    out.grain = bitmap(64, 64, function (x, y) { return G[y][x]; });
    for (y = 0; y < 64; y++) {                            // brushed: each row a long streak, smoothed along x (wrapping)
      var raw = [], row = [], base = rnd(), s = 0;
      for (x = 0; x < 128; x++) raw.push(rnd());
      for (x = -12; x < 12; x++) s += raw[(x + 128) % 128];
      for (x = 0; x < 128; x++) { row.push(0.55 * base + 0.45 * s / 24); s += raw[(x + 12) % 128] - raw[(x - 12 + 128) % 128]; }
      B.push(row);
    }
    out.brushed = bitmap(128, 64, function (x, y) { return 0.5 + (B[y][x] - 0.5) * 1.6; });
    var N = 6, cell = 128 / N;                            // mottle: a coarse random grid, smoothly blended (wrapping)
    for (y = 0; y < N; y++) { M.push([]); for (x = 0; x < N; x++) M[y].push(rnd()); }
    out.mottle = bitmap(128, 128, function (x, y) {
      var gx = x / cell, gy = y / cell, i0 = Math.floor(gx), j0 = Math.floor(gy), fx = gx - i0, fy = gy - j0;
      fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
      function at(i, j) { return M[(j + N) % N][(i + N) % N]; }
      var a = at(i0, j0) + (at(i0 + 1, j0) - at(i0, j0)) * fx, b = at(i0, j0 + 1) + (at(i0 + 1, j0 + 1) - at(i0, j0 + 1)) * fx;
      return a + (b - a) * fy;
    });
    return out;
  }
  function materials() {
    if (document.getElementById(MAT_ID)) return;
    var host = document.body || document.documentElement;
    if (!host) return;
    var svg = el('svg', { id: MAT_ID, 'class': 'kit-materials', 'aria-hidden': 'true', focusable: 'false', 'data-audit-ignore': '',
                          width: 0, height: 0, style: 'position:absolute;left:0;top:0;width:0;height:0;overflow:hidden;pointer-events:none' });
    var NZ = noiseTiles(), fx = el('defs', {}, svg);
    /* soft edges - a vapour fog, smoke, a glow: drawn on a shape that only changes while a step plays */
    [['soft', 2.5], ['fog', 5]].forEach(function (f) {
      el('feGaussianBlur', { stdDeviation: f[1] }, el('filter', { id: 'kit-f-' + f[0], x: '-60%', y: '-60%', width: '220%', height: '220%' }, fx));
    });
    [['', 1], ['-l', 0.8]].forEach(function (set) {
      var sfx = set[0], k = set[1], d = el('defs', { 'class': 'kit-mat-set' + (sfx ? ' kit-mat-light' : '') }, svg);
      function tile(name, w, h) {
        var t = el('pattern', { id: 'kit-m-' + name + sfx, patternUnits: 'userSpaceOnUse', width: w, height: h }, d);
        el('rect', { width: w, height: h, 'class': 'kit-mt-' + name }, t);
        return t;
      }
      function noise(t, kind, op) {
        if (NZ[kind]) el('image', { href: NZ[kind], width: t.getAttribute('width'), height: t.getAttribute('height'), preserveAspectRatio: 'none', opacity: op }, t);
      }
      /* aluminium cladding over a tank's insulation: sheets with a seam (its lit edge beside it), a rivet row, fine grain */
      var clad = tile('clad', 34, 56);
      noise(clad, 'brushed', 0.16);
      el('line', { x1: 0.6, y1: 0, x2: 0.6, y2: 56, 'stroke-width': 1.2, 'class': 'kit-mt-seam' }, clad);
      el('line', { x1: 1.9, y1: 0, x2: 1.9, y2: 56, 'stroke-width': 0.9, 'class': 'kit-mt-seam-lit' }, clad);
      [14, 42].forEach(function (y) { el('circle', { cx: 4.4, cy: y, r: 1.1, 'class': 'kit-mt-rivet' }, clad); });
      noise(tile('steel', 200, 60), 'brushed', 0.22);                         // brushed stainless
      var paint = tile('paint', 160, 160);                                     // machinery paint, mottled
      noise(paint, 'mottle', 0.18); noise(paint, 'grain', 0.1);
      noise(tile('paintl', 160, 160), 'grain', 0.12);                          // the same paint, a lighter coat (covers, plates)
      noise(tile('cast', 120, 120), 'grain', 0.16);                            // cast metal: valve bodies, casings
      var deck = tile('deck', 120, 60);                                        // painted deck plate, welded in strakes
      noise(deck, 'grain', 0.14);
      el('line', { x1: 0, y1: 59.5, x2: 120, y2: 59.5, 'stroke-width': 1, 'class': 'kit-mt-weld' }, deck);
      noise(tile('rubber', 80, 80), 'grain', 0.2);                             // a hose's rubber
      var hull = tile('hull', 96, 24);                                         // a ship's painted shell plating: strakes and butts
      noise(hull, 'mottle', 0.05); noise(hull, 'grain', 0.04);
      el('path', { d: 'M0 23.5 H96 M0 0 V12 M48 12 V24', 'stroke-width': 0.8, fill: 'none', 'class': 'kit-mt-strake' }, hull);
      var white = tile('white', 120, 120);                                     // a superstructure's white paint
      noise(white, 'mottle', 0.08); noise(white, 'grain', 0.06);
      var hatch = el('pattern', { id: 'kit-m-hatch' + sfx, patternUnits: 'userSpaceOnUse', width: 6, height: 6 }, d);   // a cut face's section hatching
      el('path', { d: 'M-1 7 L7 -1 M-1 1 L1 -1 M5 7 L7 5', 'stroke-width': 1, 'class': 'kit-mt-hatch' }, hatch);
      var cloth = tile('cloth', 40, 40);                                       // workwear cloth, woven
      noise(cloth, 'grain', 0.07); noise(cloth, 'brushed', 0.04);
      var suit = tile('suit', 60, 60);                                         // a protective suit's coated fabric
      noise(suit, 'mottle', 0.12); noise(suit, 'grain', 0.08);
      var foam = tile('foam', 60, 60);                                         // insulation foam, cellular
      noise(foam, 'mottle', 0.25); noise(foam, 'grain', 0.18);
      /* LNG seen through a cut-away: pale at the surface, deep blue at the bottom */
      var lng = el('linearGradient', { id: 'kit-m-lng' + sfx, x1: 0, y1: 0, x2: 0, y2: 1 }, d);
      [[0, 1, 0.85], [0.25, 2, 0.7], [1, 3, 0.75]].forEach(function (s) {
        el('stop', { offset: s[0], 'stop-opacity': s[2], 'class': 'kit-mt-lng' + s[1] }, lng);
      });
      /* a fire's flame - white-hot at its base, orange, red at its tips - standing up (fire) or along a jet (firejet); the
         sea, lit at its surface and deep below (sea) */
      [['fire', { x1: 0, y1: 1, x2: 0, y2: 0 }, [[0, 'hot', 0.95], [0.4, 'mid', 0.92], [1, 'tip', 0.8]]],
       ['firejet', { x1: 0, y1: 0, x2: 1, y2: 0 }, [[0, 'root', 0.55], [0.14, 'hot', 0.95], [0.45, 'mid', 0.92], [1, 'tip', 0.8]]]].forEach(function (f) {
        var gr = el('linearGradient', { id: 'kit-m-' + f[0] + sfx, x1: f[1].x1, y1: f[1].y1, x2: f[1].x2, y2: f[1].y2 }, d);
        f[2].forEach(function (s) { el('stop', { offset: s[0], 'stop-opacity': s[2], 'class': 'kit-mt-fire-' + s[1] }, gr); });
      });
      var sea = el('linearGradient', { id: 'kit-m-sea' + sfx, x1: 0, y1: 0, x2: 0, y2: 1 }, d);
      [[0, 'top'], [1, 'deep']].forEach(function (s) { el('stop', { offset: s[0], 'class': 'kit-mt-sea-' + s[1] }, sea); });
      /* light and shade, laid over a body so it has a form: light from above (k: softer on a light page) */
      function shade(name, grad, stops) {
        var gr = el(grad.r ? 'radialGradient' : 'linearGradient', (function () {
          var a = { id: 'kit-sh-' + name + sfx };
          for (var key in grad) if (key !== 'r') a[key] = grad[key];
          if (grad.r) a.r = grad.r;
          return a;
        })(), d);
        stops.forEach(function (s) { el('stop', { offset: s[0], 'stop-opacity': (s[2] * k).toFixed(3), 'class': s[1] ? 'kit-mt-hi' : 'kit-mt-lo' }, gr); });
      }
      var CYL = [[0, 0, 0.55], [0.12, 0, 0.15], [0.28, 1, 0.42], [0.42, 1, 0.06], [0.78, 0, 0.28], [1, 0, 0.62]];
      shade('cyl', { x1: 0, y1: 0, x2: 0, y2: 1 }, CYL);                        // a cylinder lying down: a tank, a pipe, a shell
      shade('cylv', { x1: 0, y1: 0, x2: 1, y2: 0 }, CYL);                       // a cylinder standing up: a bottle, a mast
      shade('box', { x1: 0, y1: 0, x2: 0, y2: 1 }, [[0, 1, 0.32], [0.18, 1, 0.04], [0.8, 0, 0.22], [1, 0, 0.5]]);
      shade('round', { cx: 0.36, cy: 0.3, r: 0.78 }, [[0, 1, 0.5], [0.45, 1, 0], [1, 0, 0.55]]);
    });
    host.appendChild(svg);
  }

  /* a BODY of a piece of equipment: the shape in its material (o.mat: clad, steel, paint, paintl, cast, deck, rubber,
     foam, lng), with o.shade (cyl, cylv, box, round) laid over it - a second copy of the same shape, light from above.
     A body that changes its shape later changes through reshape(), so its shade goes with it. */
  function body(tag, attrs, parent, o) {
    o = o || {};
    var a = {}, s = { 'class': 'kit-sh kit-sh-' + o.shade, 'aria-hidden': 'true' }, k;
    for (k in attrs) a[k] = attrs[k];
    a['class'] = ((attrs['class'] || '') + (o.mat ? ' kit-m-' + o.mat : '')).trim() || null;
    var n = el(tag, a, parent);
    if (o.shade) {
      for (k in attrs) if (k !== 'class' && k !== 'style' && k !== 'id') s[k] = attrs[k];
      n.__kitShade = el(tag, s, parent);
    }
    if (o.hatch) {                                      // a cut face in a cut-away: its section hatching over it
      var c = { 'class': 'kit-sh kit-m-hatch', 'aria-hidden': 'true' };
      for (k in attrs) if (k !== 'class' && k !== 'style' && k !== 'id') c[k] = attrs[k];
      el(tag, c, parent);
    }
    return n;
  }
  /* a PIECE OF EQUIPMENT: the group its bodies are drawn in. Its pieces overlap by design (a valve's flanges, body,
     bonnet and actuator; a pump's casing and foot) - the drawing check judges the piece as one object (data-kit-body) -
     and it casts one soft shadow on what is behind it (shadow: false - none) */
  function equip(parent, o) {
    return el('g', { 'class': o && o.shadow === false ? 'kit-eq' : 'kit-eq kit-m-drop', 'data-kit-body': '' }, parent);
  }
  function reshape(n, attrs) {
    for (var k in attrs) {
      n.setAttribute(k, attrs[k]);
      if (n.__kitShade) n.__kitShade.setAttribute(k, attrs[k]);
    }
    return n;
  }
  /* a bolted pipe FLANGE square across the line at (x, y): angle the line's direction in degrees, len across it (the
     pipe's width + 10), t its thickness. It sits where a pipe joins the next pipe or a piece of equipment, so it lies on
     that boundary by nature (data-may-cross). */
  function flange(parent, x, y, angle, len, t) {
    len = len || 23; t = t || 5;
    var f = el('g', { 'class': 'kit-flg', 'data-may-cross': '', 'data-no-contain': '',
                      transform: 'translate(' + (+x).toFixed(2) + ' ' + (+y).toFixed(2) + ')' + (angle ? ' rotate(' + (+angle).toFixed(1) + ')' : '') }, parent);
    body('rect', { x: -t / 2, y: -len / 2, width: t, height: len, rx: 1.2 }, f, { mat: 'steel', shade: 'box' });
    [-1, 1].forEach(function (s) { el('circle', { cx: 0, cy: s * (len / 2 - 3.2), r: 1.3, 'class': 'kit-m-bolt' }, f); });
    return f;
  }
  /* where the pipes of a spec end, in figure coordinates (a path read as straight runs between its vertices) */
  function pipeEnds(fig) {
    var out = [];
    (fig.spec.parts || []).forEach(function (q) {
      if (q.type !== 'pipe' || !q.d) return;
      var t = String(q.d).match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [], N = { M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, A: 7 };
      var ox = q.x || 0, oy = q.y || 0, cx = 0, cy = 0, cmd = '', i = 0, pts = [];
      while (i < t.length) {
        if (/[a-zA-Z]/.test(t[i])) { cmd = t[i++]; if (/z/i.test(cmd)) continue; }
        var up = cmd.toUpperCase(), rel = cmd !== up, n = N[up];
        if (!n) break;
        var a = t.slice(i, i + n).map(Number), x = cx, y = cy; i += n;
        if (up === 'H') x = a[0] + (rel ? cx : 0); else if (up === 'V') y = a[0] + (rel ? cy : 0);
        else { x = a[n - 2] + (rel ? cx : 0); y = a[n - 1] + (rel ? cy : 0); }
        if (up === 'M') cmd = rel ? 'l' : 'L';
        cx = x; cy = y;
        pts.push([ox + cx, oy + cy]);
      }
      if (pts.length) { out.push(pts[0]); out.push(pts[pts.length - 1]); }
    });
    return out;
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

  /* kit-relate */
  /* ----------------------------------------------------------------- relations (2.72.0)
     A part is placed BY WHAT IT STANDS ON, not by a raw y (IGF M01 s03, 2.71.0: a vent mast drawn at y 184 under the deck
     line, inside the hull; a "Bunkering station" that was words with no manifold; pipes that ended in the air). A spec may
     say, instead of x / y / d:
       "on": "G.deck"            stand on an anchor - the part's foot on that line (a vent mast's foot, a manifold's flange)
       "in": "S"                 stand on the floor of a space or of the ship's hold
       "at": 0.7 | 312 | "K.top" across: a fraction of the host's length, a figure x, or another part's port
       "at": "P1@0.4"            ON a pipe: that far along it, turned with it (a valve, a coupling)
       "side": "left" | "right"  against that wall of the space it is in
       "from": "K.top", "to": "V.inlet", "via": [[x, y], "R.outlet"], "level": y   a pipe or hose routed between ports
       "for": "B"                (a text) a callout to that part - its leader ends on it
       "around": "V.outlet", "r": 40 | "pad": 8    (a zone) round a port or a part
       "from": "V.outlet"        (a gas cloud) grows from that port
       "aim": "W"                (a spray) pointed at that part, reaching it
     Anchors of a side-view ship (ga): deck, bottom, floor, waterline, side; of a plan view: port, starboard, side; of any
     part: its ports (PARTS of GEOM below: top, bottom, left, right, center, inlet, outlet ... and "top@0.3" along an edge).
     Pure numbers, no DOM: check_kit.py runs this block under node to judge what a figure MEANS (kit_relate.py). The
     resolved spec keeps the relation keys; a part with no relation is left exactly as it was. */
  var RELATE = (function () {
    function n(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
    function cl(v, a, b) { return Math.max(a, Math.min(b, v)); }
    function r1(v) { return Math.round(v * 10) / 10; }
    function edges(x0, y0, x1, y1, more) {
      var o = { top: [(x0 + x1) / 2, y0, 'up'], bottom: [(x0 + x1) / 2, y1, 'down'], left: [x0, (y0 + y1) / 2, 'left'],
                right: [x1, (y0 + y1) / 2, 'right'], center: [(x0 + x1) / 2, (y0 + y1) / 2, null] };
      for (var k in more || {}) o[k] = more[k];
      return o;
    }
    /* each type's shape in its own units (origin = its x, y): box [x0, y0, x1, y1]; foot [x, y] - where it stands (or, for
       a part that hangs, "hang" - where it hangs from); span [x0, x1] - the run "top@f" / "bottom@f" are measured along;
       ports {name: [x, y, dir]} - where a pipe joins it, dir the way a pipe leaves it. Read from the parts' drawing code;
       a type not here is judged by its w / h or r */
    var GEOM = {
      tank: function (p) {
        var w = n(p.w, 190), h = n(p.h, 110), f = cl(h * 0.1, 4, 12);
        return { box: [0, -10, w, h + f], foot: [w / 2, h + f], span: [h * 0.28, w - h * 0.28], ports: edges(0, -10, w, h, { top: [w / 2, -10, 'up'], vapour: [w / 2, -10, 'up'], liquid: [w / 2, h, 'down'] }) };
      },
      integral_tank: function (p) { var w = n(p.w, 160), h = n(p.h, 110); return { box: [0, 0, w, h], foot: [w / 2, h], ports: edges(0, 0, w, h) }; },
      boil_off: function (p) { var w = n(p.w, 260), h = n(p.h, 150); return { box: [0, 0, w, h], foot: [w / 2, h], ports: edges(0, 0, w, h) }; },
      tank_type: function (p) { var w = n(p.w, 150), h = n(p.h, 110); return { box: [0, 0, w, h], foot: [w / 2, h], ports: edges(0, 0, w, h) }; },
      space: function (p) {
        var w = n(p.w, 120), h = n(p.h, 90);
        return { box: [0, 0, w, h], foot: [w / 2, h], floor: h - 3, room: true, ports: edges(0, 0, w, h, { floor: [w / 2, h - 3, 'up'], ceiling: [w / 2, 3, 'down'] }) };
      },
      vent: function (p) {
        var m = typeof p.mast === 'number' ? p.mast : p.mast === true ? 60 : 0;
        return { box: [-10, -46, 10, Math.max(m, 2)], foot: [0, m], ports: { inlet: [0, m, 'down'], outlet: [0, -7, 'up'], top: [0, -7, 'up'], bottom: [0, m, 'down'] }, gasFrom: [0, -12] };
      },
      valve: function (p) {
        var s = n(p.size, 12), k = s * 0.72, hw = s + 9;
        return { box: [-hw, -k - 3 - 1.45 * s, hw, k + 3], foot: [0, k + 3], ports: { in: [-hw, 0, 'left'], out: [hw, 0, 'right'], left: [-hw, 0, 'left'], right: [hw, 0, 'right'], center: [0, 0, null] }, turns: true };
      },
      relief_valve: function (p) {
        var s = n(p.size, 14), k = s * 0.7, top = -s - 22, L = p.outlet === 'left' ? -1 : 1;
        return { box: [L > 0 ? -k - 13 : -s - 8, top - 11, L > 0 ? s + 8 : k + 13, s + 8], foot: [0, s + 7.5],
                 ports: { inlet: [0, s + 7.5, 'down'], outlet: [L * (s + 7.5), 0, L > 0 ? 'right' : 'left'], bottom: [0, s + 7.5, 'down'], center: [0, 0, null] } };
      },
      pump: function (p) {
        var r = n(p.r, 15);
        return { box: [-r - 4, -r, r + 8, r + 6], foot: [0, r + 6], ports: { inlet: [-r, 0, 'left'], outlet: [r + 8, -r + 4, 'right'], left: [-r, 0, 'left'], right: [r + 8, -r + 4, 'right'], center: [0, 0, null] } };
      },
      exchanger: function (p) {
        var r = n(p.r, 18), a = r * 0.78 + 2.5;
        return { box: [-a, -r * 0.83 - 2, a, r + 3], foot: [0, r + 3], ports: { in: [-a, 0, 'left'], out: [a, 0, 'right'], inlet: [-a, 0, 'left'], outlet: [a, 0, 'right'], left: [-a, 0, 'left'], right: [a, 0, 'right'], center: [0, 0, null] } };
      },
      engine: function (p) {
        var w = n(p.w, 100), h = n(p.h, 70);
        return { box: [-31, -10, w, h + 5], foot: [w / 2, h + 5], span: [0, w], ports: edges(0, -10, w, h, { inlet: [0, h / 2, 'left'], gas: [0, h / 2, 'left'] }) };
      },
      cylinder: function (p) { var w = n(p.w, 140), h = n(p.h, 230); return { box: [0, 0, w, h], foot: [w / 2, h], ports: edges(0, 0, w, h, { gas: [w * 0.78, 0, 'up'], oil: [w * 0.22, 0, 'up'] }) }; },
      manifold: function (p) {
        var outs = (p.outlets || []).length || 1, w = n(p.w, 560), hh = n(p.h, 24), y0 = hh + n(p.drop, 44) + 7, sp = w / outs, o = {};
        for (var i = 0; i < outs; i++) o['out' + (i + 1)] = [sp * (i + 0.5), y0 + 9, 'down'];
        o.outlet = o.out1; o.bottom = o.out1; o.left = [-8, hh / 2, 'left']; o.right = [w + 8, hh / 2, 'right']; o.top = [w / 2, -6, 'up']; o.center = [w / 2, hh / 2, null];
        return { box: [-8, -6, w + 8, y0 + 9], foot: [w / 2, y0 + 9], span: [0, w], ports: o };
      },
      drip_tray: function (p) { var w = n(p.w, 160), d = n(p.h, 24); return { box: [-1.5, -1, w + 1.5, d + 11], foot: [w / 2, d + 11], ports: edges(-1.5, 0, w + 1.5, d + 11) }; },
      water_curtain: function (p) {
        var w = n(p.w, 36), h = n(p.h, 120);
        return { box: [-6, -10, w + 6, h], hang: [w / 2, -10], ports: edges(-6, -10, w + 6, h, { header: [w / 2, -10, 'up'] }), water: [0, 0, w, h] };
      },
      coupling: function () { return { box: [-24, -16, 24, 16], foot: [0, 16], ports: { left: [-23.5, 0, 'left'], right: [23.5, 0, 'right'], in: [-23.5, 0, 'left'], out: [23.5, 0, 'right'], center: [0, 0, null] }, turns: true }; },
      hatch: function (p) { var w = n(p.w, 64); return { box: [-3, 0, w + 3, 20], foot: [w / 2, 20], ports: edges(-3, 0, w + 3, 20) }; },
      detector: function (p) { var r = n(p.r, 19); return { box: [-r, -22, r, 22], foot: [0, 22], hang: [0, -22], ports: edges(-r, -22, r, 22) }; },
      lamp: function (p) { var r = p.ex ? 20 : 13; return { box: [-r, 0, r, 48], hang: [0, 0], ports: edges(-r, 0, r, 48) }; },
      gas_cylinder: function (p) {                       // (x, y) is the middle of its foot ring; the valve on its neck
        var w = n(p.w, 56), h = n(p.h, 150), s = cl(h / 150, 0.55, 1), top = -h - 34 * s;
        return { box: [-w / 2 - 4, top, Math.max(w / 2 + 4, 22 * s), 2], foot: [0, 2],
                 ports: edges(-w / 2 - 4, top, w / 2 + 4, 2, { valve: [22 * s, -h - 17.5 * s, 'right'], outlet: [22 * s, -h - 17.5 * s, 'right'], top: [0, top, 'up'] }) };
      },
      fan: function (p) {
        var r = n(p.r, 26), hl = n(p.len, 170) / 2, wh = r + 9, vert = p.dir === 'up' || p.dir === 'down';
        var b = vert ? [-wh, -hl, wh, hl] : [-hl, -wh, hl, wh];
        return { box: b, foot: [0, b[3]], ports: edges(b[0], b[1], b[2], b[3], vert ? { inlet: [0, p.dir === 'up' ? hl : -hl, p.dir === 'up' ? 'down' : 'up'], outlet: [0, p.dir === 'up' ? -hl : hl, p.dir === 'up' ? 'up' : 'down'] }
                                                                                      : { inlet: [p.dir === 'left' ? hl : -hl, 0, p.dir === 'left' ? 'right' : 'left'], outlet: [p.dir === 'left' ? -hl : hl, 0, p.dir === 'left' ? 'left' : 'right'] }) };
      },
      spool_piece: function (p) { var w = n(p.w, 560), t = n(p.t, 26); return { box: [0, -t / 2 - 5, w, t / 2 + 5], foot: [w / 2, t / 2 + 5], ports: edges(0, -t / 2, w, t / 2) }; },
      push_button: function (p) { var h = n(p.h, 120), s = h / 182; return { box: [-60 * s, 0, 60 * s, h], foot: [0, h], ports: edges(-60 * s, 0, 60 * s, h) }; },
      airlock: function (p) { var w = n(p.w, 130), h = n(p.h, 124), sd = n(p.safeW, n(p.side, 92)), sd2 = n(p.hazardW, sd); return { box: [0, 0, sd + w + sd2, h], foot: [(sd + w + sd2) / 2, h], ports: edges(0, 0, sd + w + sd2, h) }; },
      badge: function () { return { box: [-17, -17, 17, 17], ports: edges(-17, -17, 17, 17) }; },
      gauge: function (p) { var r = n(p.r, 40); return { box: [-r, -r, r, r + 20], ports: edges(-r, -r, r, r) }; },
      flame: function (p) { var s = n(p.size, 44); return { box: [-s / 2, -s, s / 2, 0], foot: [0, 0], ports: edges(-s / 2, -s, s / 2, 0) }; },
      scale: function (p) {                              // across: the bar along y, its markers on stems above it; upright: x, y the top
        var bw = n(p.w, 22), rise = 0;
        (p.markers || []).forEach(function (m) { rise = Math.max(rise, n(m && m.rise, 60)); });
        if (p.orient === 'h') { var L = n(p.len, 400); return { box: [-10, -rise - 34, L + 10, bw + 34], ports: edges(0, 0, L, bw) }; }
        var H = n(p.h, 300); return { box: [-40, -10, n(p.reach, bw + 300), H + 10], ports: edges(0, 0, bw, H) };
      },
      zone: function (p) { var w = p.r != null ? 2 * p.r : n(p.w, 80), h = p.r != null ? 2 * p.r : n(p.h, 60); return { box: [0, 0, w, h], ports: edges(0, 0, w, h) }; },
      gas_cloud: function (p) { var w = n(p.w, 200), h = n(p.h, 120); return { box: [0, 0, w, h], ports: edges(0, 0, w, h) }; }
    };
    function shapeOf(p) {
      if (GEOM[p.type]) return GEOM[p.type](p);
      if (p.type === 'ga') return gaShape(p);
      var w = n(p.w, 0), h = n(p.h, 0), r = n(p.r, 0);
      if (w && h) return { box: [0, 0, w, h], foot: [w / 2, h], ports: edges(0, 0, w, h) };
      if (r) return { box: [-r, -r, r, r], foot: [0, r], ports: edges(-r, -r, r, r) };
      /* a part whose shape this table does not know: judged generously (approx), never failed on a guess */
      return { box: [-100, -100, 100, 100], foot: [0, 10], approx: true, ports: edges(-10, -10, 10, 10) };
    }
    /* the hull of a side-view ship as kit.js draws it (TYPES.ga): deck at 0, stern line in to 0.1 w at the keel, the bow a
       curve from (w, 0) to (0.87 w, h). hullX(y) = [left, right] of the hull at depth y */
    function gaShape(p) {
      var w = n(p.w, 600), d = n(p.h, 80), wl = n(p.draft, 0.55), plan = p.view === 'plan';
      var up = p.house ? n(p.house.h, 0) + (p.funnel ? n(p.funnel.h, 22) : 0) + 20 : 6;
      var o = { box: [0, -up, w, d], span: [0, w], ga: true, plan: plan, deckY: 0, keelY: d, wl: d * wl,
                house: p.house ? [n(p.house.x, 0), -n(p.house.h, 0), n(p.house.x, 0) + n(p.house.w, 0), 0] : null,
                houseTop: p.house ? -n(p.house.h, 0) - (p.funnel ? n(p.funnel.h, 22) : 0) : 0 };
      o.ports = plan ? { port: [w / 2, 0, 'up'], starboard: [w / 2, d, 'down'], side: [w / 2, 0, 'up'], deck: [w / 2, d / 2, null], center: [w / 2, d / 2, null] }
                     : { deck: [w / 2, 0, 'up'], bottom: [w / 2, d, 'down'], keel: [w / 2, d, 'down'], floor: [w / 2, d * 0.9, 'up'],
                         waterline: [w / 2, d * wl, null], side: [w / 2, d * 0.28, null], center: [w / 2, d / 2, null] };
      o.hullX = function (y) {
        if (plan || p.cut) return [0, w];
        var t = cl(y / d, 0, 1), left = t < 0.5 ? 0.03 * w * (t / 0.5) : 0.03 * w + 0.07 * w * ((t - 0.5) / 0.5);
        var lo = 0, hi = 1;                                  /* the bow: y(s) = 2s(1-s) 0.62 d + s^2 d, x(s) = (1-s)^2 w + 2s(1-s) 0.97 w + s^2 0.87 w */
        for (var i = 0; i < 30; i++) { var m = (lo + hi) / 2, ym = 2 * m * (1 - m) * 0.62 * d + m * m * d; if (ym < y) lo = m; else hi = m; }
        var s = (lo + hi) / 2, right = (1 - s) * (1 - s) * w + 2 * s * (1 - s) * 0.97 * w + s * s * 0.87 * w;
        return [left, right];
      };
      return o;
    }
    /* a pipe's path as straight runs between its vertices (M L H V; a curve's end points), in figure units */
    function pathPts(d, ox, oy) {
      var t = String(d || '').match(/[a-zA-Z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [], N = { M: 2, L: 2, H: 1, V: 1, C: 6, S: 4, Q: 4, T: 2, A: 7 };
      var cx = 0, cy = 0, cmd = '', i = 0, pts = [];
      while (i < t.length) {
        if (/[a-zA-Z]/.test(t[i])) { cmd = t[i++]; if (/z/i.test(cmd)) continue; }
        var up = cmd.toUpperCase(), rel = cmd !== up, k = N[up];
        if (!k) break;
        var a = t.slice(i, i + k).map(Number), x = cx, y = cy; i += k;
        if (up === 'H') x = a[0] + (rel ? cx : 0); else if (up === 'V') y = a[0] + (rel ? cy : 0);
        else { x = a[k - 2] + (rel ? cx : 0); y = a[k - 1] + (rel ? cy : 0); }
        if (up === 'M') cmd = rel ? 'l' : 'L';
        cx = x; cy = y;
        pts.push([(ox || 0) + cx, (oy || 0) + cy]);
      }
      return pts;
    }
    function along(pts, f) {
      var L = 0, i, seg = [];
      for (i = 1; i < pts.length; i++) { var l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(l); L += l; }
      var want = cl(f, 0, 1) * L;
      for (i = 0; i < seg.length; i++) {
        if (want <= seg[i] || i === seg.length - 1) {
          var k = seg[i] ? want / seg[i] : 0, a = pts[i], b = pts[i + 1];
          return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, Math.abs(b[0] - a[0]) < Math.abs(b[1] - a[1]) ? 'v' : 'h'];
        }
        want -= seg[i];
      }
      return pts.length ? [pts[0][0], pts[0][1], 'h'] : [0, 0, 'h'];
    }
    var TURN = { up: 'right', right: 'down', down: 'left', left: 'up' };
    function turnDir(d, deg) { var k = ((Math.round((deg || 0) / 90) % 4) + 4) % 4; while (k--) d = d ? TURN[d] : d; return d; }
    function rot(pt, deg) {
      var a = (deg || 0) * Math.PI / 180, c = Math.round(Math.cos(a) * 1e6) / 1e6, s = Math.round(Math.sin(a) * 1e6) / 1e6;
      return [pt[0] * c - pt[1] * s, pt[0] * s + pt[1] * c];
    }

    function resolve(spec0) {
      if (!spec0 || !spec0.parts) return spec0;
      var spec = JSON.parse(JSON.stringify(spec0)), byId = {}, state = {}, errs = [];
      spec.parts.forEach(function (p) { if (p && p.id) byId[p.id] = p; });
      if (!spec.parts.some(related)) return spec;
      function related(p) { return p && (p.on || p.in || p.at != null || p['for'] || p.around || p.aim ||
                                         ((p.type === 'pipe' || p.type === 'hose' || p.type === 'wire') && (p.from || p.to)) ||
                                         (p.type === 'gas_cloud' && typeof p.from === 'string')); }
      function err(p, msg) { errs.push((p.id || p.type) + ': ' + msg); }
      function shape(id) { var p = byId[id]; if (!p) return null; done(p); return shapeOf(p); }
      function done(p) {                                  // a part referred to is placed first
        if (state[p.id] === 2) return;
        if (state[p.id] === 1) { err(p, 'its placement refers back to itself'); return; }
        state[p.id] = 1; place(p); state[p.id] = 2;
      }
      /* "<id>.<anchor>" -> [x, y, dir, part] in figure units; "<pipe>@f" -> the point f along the pipe */
      function anchor(ref, who) {
        if (Array.isArray(ref)) return [n(ref[0], 0), n(ref[1], 0), null, null];
        var s = String(ref), at = s.indexOf('@'), f = at >= 0 ? parseFloat(s.slice(at + 1)) : null, base = at >= 0 ? s.slice(0, at) : s;
        var dot = base.indexOf('.'), id = dot >= 0 ? base.slice(0, dot) : base, name = dot >= 0 ? base.slice(dot + 1) : '';
        var q = byId[id];
        if (!q) { err(who, 'refers to ' + s + ' - there is no part ' + id); return null; }
        done(q);
        if ((q.type === 'pipe' || q.type === 'hose' || q.type === 'wire') && q.d) {
          var pts = pathPts(q.d, q.x, q.y);
          if (!pts.length) return null;
          if (name === 'start' || (!name && f == null)) return [pts[0][0], pts[0][1], null, q];
          if (name === 'end') return [pts[pts.length - 1][0], pts[pts.length - 1][1], null, q];
          var a = along(pts, f != null ? f : 0.5);
          return [a[0], a[1], a[2], q];
        }
        var S = shapeOf(q), X = n(q.x, 0), Y = n(q.y, 0);
        if (!name) name = 'center';
        var P = S.ports[name];
        if (!P) { err(who, 'refers to ' + s + ' - a ' + q.type + ' has no "' + name + '" (it has ' + Object.keys(S.ports).join(', ') + ')'); return null; }
        var px = P[0], py = P[1], dir = P[2];
        if (f != null && (name === 'top' || name === 'bottom' || name === 'deck' || name === 'floor' || name === 'ceiling' || name === 'keel' || name === 'waterline' || name === 'side' || name === 'port' || name === 'starboard')) {
          var sp = S.span || [S.box[0], S.box[2]]; px = sp[0] + cl(f, 0, 1) * (sp[1] - sp[0]);
        } else if (f != null && (name === 'left' || name === 'right')) py = S.box[1] + cl(f, 0, 1) * (S.box[3] - S.box[1]);
        if (S.turns && q.rotate) { var rp = rot([px, py], q.rotate); px = rp[0]; py = rp[1]; dir = turnDir(dir, q.rotate); }
        return [X + px, Y + py, dir, q, S];
      }
      function acrossX(p, host, H) {                      // "at": a fraction of the host's length, a figure x, or a port
        if (p.at == null) return null;
        if (typeof p.at === 'number') {
          if (p.at >= 0 && p.at <= 1 && host) { var sp = H.span || [H.box[0], H.box[2]]; return n(host.x, 0) + sp[0] + p.at * (sp[1] - sp[0]); }
          return p.at;
        }
        var a = anchor(p.at, p);
        return a ? a[0] : null;
      }
      function place(p) {
        if (!related(p)) return;
        var t = p.type;
        if (t === 'pipe' || t === 'hose' || t === 'wire') return route(p);
        if (t === 'text' && p['for']) {
          var tgt = p['for'], a = String(tgt).indexOf('.') >= 0 ? anchor(tgt, p) : null, q = byId[tgt];
          if (!a && !q) { err(p, 'is "for" ' + tgt + ', which is not a part'); return; }
          var pt = a;
          if (!pt && q && (q.type === 'pipe' || q.type === 'hose' || q.type === 'wire')) pt = anchor(tgt + '@0.5', p);   // a line: its middle
          if (!pt) { done(q); var Q = shapeOf(q), qx = n(q.x, 0), qy = n(q.y, 0); pt = [qx + (Q.box[0] + Q.box[2]) / 2, qy + (Q.box[1] + Q.box[3]) / 2]; p._forBox = [qx + Q.box[0], qy + Q.box[1], qx + Q.box[2], qy + Q.box[3]]; }
          p.to = [r1(pt[0]), r1(pt[1])];
          if (p.x == null) p.x = p.to[0];
          if (p.y == null) p.y = r1((p._forBox ? p._forBox[1] : pt[1]) - 22);
          return;
        }
        if (t === 'zone' && p.around) {
          var ar = anchor(p.around, p);
          if (!ar) return;
          if (p.r != null && String(p.around).indexOf('.') >= 0) { p.x = r1(ar[0] - p.r); p.y = r1(ar[1] - p.r); return; }
          var zq = byId[String(p.around).split('.')[0]], ZS = shapeOf(zq), pad = n(p.pad, 8), zx = n(zq.x, 0), zy = n(zq.y, 0);
          if (p.r != null) { p.x = r1(ar[0] - p.r); p.y = r1(ar[1] - p.r); return; }
          p.x = r1(zx + ZS.box[0] - pad); p.y = r1(zy + ZS.box[1] - pad); p.w = r1(ZS.box[2] - ZS.box[0] + 2 * pad); p.h = r1(ZS.box[3] - ZS.box[1] + 2 * pad);
          return;
        }
        if (t === 'gas_cloud' && typeof p.from === 'string') {
          var fa = anchor(p.from, p);
          if (!fa) return;
          var gq = fa[3], gS = gq ? shapeOf(gq) : null, gx = fa[0], gy = fa[1];
          if (gS && gS.gasFrom && /outlet|top$/.test(p.from)) { gx = n(gq.x, 0) + gS.gasFrom[0]; gy = n(gq.y, 0) + gS.gasFrom[1]; }
          p._from = p.from; p.from = [r1(gx), r1(gy)]; p.fromIn = 'figure';
          var cw = n(p.w, 200), ch = n(p.h, 120);
          if (p.x == null) p.x = r1(gx - cw / 2);
          if (p.y == null) p.y = r1(fa[2] === 'up' || /outlet/.test(p._from) ? gy - ch * 0.85 : gy - ch / 2);
          return;
        }
        var S = shapeOf(p), host = null, H = null, ax = null;
        if (t === 'spray' && p.aim) {
          var tq = byId[String(p.aim).split('.')[0]], tp = String(p.aim).indexOf('.') >= 0 ? anchor(p.aim, p) : null;
          if (!tq) { err(p, 'aims at ' + p.aim + ', which is not a part'); }
          else {
            if (!tp) { done(tq); var TS = shapeOf(tq), tx = n(tq.x, 0), ty = n(tq.y, 0); tp = [tx + (TS.box[0] + TS.box[2]) / 2, ty + (TS.box[1] + TS.box[3]) / 2]; }
            var dx = tp[0] - n(p.x, 0), dy = tp[1] - n(p.y, 0);
            if (p.angle == null) p.angle = r1(-Math.atan2(dy, dx) * 180 / Math.PI);
            if (p.reach == null) p.reach = Math.max(30, r1(Math.hypot(dx, dy)));
          }
        }
        if (p.on) {
          var a2 = anchor(p.on, p);
          if (!a2) return;
          host = a2[3]; H = a2[4] || (host ? shapeOf(host) : null);
          if (t === 'vent' && p.mast == null) {           // a mast stands clear above the superstructure, as the rules want
            var hs = H && H.ga && !H.plan ? H : null;
            p.mast = hs && hs.houseTop ? Math.max(60, -hs.houseTop + 14) : 60;
            S = shapeOf(p);
          }
          if (t === 'water_curtain' && p.h == null && H && H.ga && !H.plan) { p.h = r1(Math.max(30, H.wl - 6)); S = shapeOf(p); }
          var mount = S.hang || S.foot || [0, 0];
          ax = acrossX(p, host, H);
          if (ax == null && (p.x == null || /\.(top|bottom|inlet|outlet|floor|ceiling|in|out|left|right|center|valve|header)(@|$)/.test(p.on) && p.at == null && !(H && H.ga)))
            ax = a2[0];
          if (ax != null) p.x = r1(ax - mount[0]);
          p.y = r1(a2[1] - mount[1] - (S.hang ? -n(p.gap, 0) : n(p.gap, 0)));
        } else if (p['in']) {
          var sq = byId[p['in']];
          if (!sq) { err(p, 'is "in" ' + p['in'] + ', which is not a part'); return; }
          done(sq);
          var SS = shapeOf(sq), sx = n(sq.x, 0), sy = n(sq.y, 0), floor = SS.ga ? SS.keelY * 0.9 : SS.floor != null ? SS.floor : SS.box[3];
          var ft = S.foot || [0, S.box[3]];
          ax = acrossX(p, sq, SS);
          if (p.side === 'left' || p.side === 'right') {
            var lo = sx + (SS.ga ? SS.hullX(floor)[0] : SS.box[0]) + 6, hi = sx + (SS.ga ? SS.hullX(floor)[1] : SS.box[2]) - 6;
            p.x = r1(p.side === 'left' ? lo - S.box[0] : hi - S.box[2]);
          } else if (ax != null) p.x = r1(ax - ft[0]);
          p.y = r1(sy + floor - ft[1] - n(p.gap, 0));
        } else if (p.at != null) {
          if (typeof p.at === 'string' && p.at.indexOf('@') >= 0) {   // ON a pipe: that far along it, turned with it
            var a3 = anchor(p.at, p);
            if (!a3) return;
            p.x = r1(a3[0]); p.y = r1(a3[1]);
            if (S.turns && p.rotate == null && a3[2] === 'v') p.rotate = 90;
          } else {
            var ax2 = acrossX(p, null, null);
            if (ax2 != null) p.x = r1(ax2 - ((S.foot || [0])[0]));
          }
        }
      }
      function route(p) {
        if (!p.from || !p.to) { err(p, 'needs both "from" and "to" (or neither, with a "d")'); return; }
        var A = anchor(p.from, p), B = anchor(p.to, p);
        if (!A || !B) return;
        var mids = [], how = p.route;
        (p.via || []).forEach(function (v) { var a = anchor(v, p); if (a) mids.push([a[0], a[1]]); });
        var pts = [[A[0], A[1]]];
        if (mids.length) pts = pts.concat(mids);
        else if (Math.abs(A[0] - B[0]) > 0.5 && Math.abs(A[1] - B[1]) > 0.5) {
          var vA = A[2] === 'up' || A[2] === 'down', vB = B[2] === 'up' || B[2] === 'down';
          if (p.type === 'hose' && !how) how = 'curve';
          how = how || (vA && !vB ? 'vh' : !vA && vB ? 'hv' : vA && vB ? 'vhv' : A[2] || B[2] ? 'hvh' : 'hv');
          if (how === 'vh') pts.push([A[0], B[1]]);
          else if (how === 'hv') pts.push([B[0], A[1]]);
          else if (how === 'vhv') {
            var my = p.level != null ? p.level : A[2] === 'up' && B[2] === 'up' ? Math.min(A[1], B[1]) - 24 : A[2] === 'down' && B[2] === 'down' ? Math.max(A[1], B[1]) + 24 : (A[1] + B[1]) / 2;
            pts.push([A[0], my], [B[0], my]);
          } else if (how === 'hvh') {
            var mx = p.level != null ? p.level : A[2] === 'right' && B[2] === 'right' ? Math.max(A[0], B[0]) + 24 : A[2] === 'left' && B[2] === 'left' ? Math.min(A[0], B[0]) - 24 : (A[0] + B[0]) / 2;
            pts.push([mx, A[1]], [mx, B[1]]);
          }
        }
        pts.push([B[0], B[1]]);
        var d;
        if (how === 'curve') {                            // a hose hangs in a curve between its ends
          var L = Math.hypot(B[0] - A[0], B[1] - A[1]) * 0.4, sag = n(p.sag, 30);
          var dv = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }, ua = dv[A[2]] || [0, 1], ub = dv[B[2]] || [0, 1];
          d = 'M' + r1(A[0]) + ' ' + r1(A[1]) + ' C' + r1(A[0] + ua[0] * L) + ' ' + r1(A[1] + ua[1] * L + sag) + ' ' +
              r1(B[0] + ub[0] * L) + ' ' + r1(B[1] + ub[1] * L + sag) + ' ' + r1(B[0]) + ' ' + r1(B[1]);
        } else {
          d = pts.map(function (q, i) { return (i ? 'L' : 'M') + r1(q[0]) + ' ' + r1(q[1]); }).join(' ');
        }
        p.d = d; p.x = 0; p.y = 0;
      }
      spec.parts.forEach(function (p) { if (p && p.id) done(p); else if (p) place(p); });
      if (errs.length) spec._relate = errs;
      return spec;
    }

    /* every part's box and ports in figure units, for the checks (kit_relate.py) */
    function geometry(spec) {
      return (spec.parts || []).map(function (p) {
        if (!p) return null;
        var o = { id: p.id || null, type: p.type };
        if ((p.type === 'pipe' || p.type === 'hose' || p.type === 'wire') && p.d) { o.pts = pathPts(p.d, p.x, p.y); return o; }
        var S = shapeOf(p), X = n(p.x, 0), Y = n(p.y, 0), R = S.turns && p.rotate ? p.rotate : 0;
        var bx = S.box;
        if (R) { var c = [rot([bx[0], bx[1]], R), rot([bx[2], bx[3]], R)]; bx = [Math.min(c[0][0], c[1][0]), Math.min(c[0][1], c[1][1]), Math.max(c[0][0], c[1][0]), Math.max(c[0][1], c[1][1])]; }
        o.box = [X + bx[0], Y + bx[1], X + bx[2], Y + bx[3]];
        o.ports = {};
        for (var k in S.ports) { var P = R ? rot(S.ports[k], R) : S.ports[k]; o.ports[k] = [X + P[0], Y + P[1], turnDir(S.ports[k][2], R)]; }
        if (S.foot) o.foot = [X + S.foot[0], Y + S.foot[1]];
        if (S.approx) o.approx = true;
        if (S.ga) {
          o.ga = { plan: S.plan, deck: Y, keel: Y + S.keelY, wl: Y + S.wl, house: S.house ? [X + S.house[0], Y + S.house[1], X + S.house[2], Y + S.house[3]] : null,
                   houseTop: Y + S.houseTop, hull: [] };
          for (var i = 0; i <= 20; i++) { var yy = S.keelY * i / 20, hx = S.hullX(yy); o.ga.hull.push([r1(Y + yy), r1(X + hx[0]), r1(X + hx[1])]); }
        }
        if (p.type === 'spray') {
          var a = n(p.angle, p.nozzle === 'sprinkler' ? -90 : p.nozzle === 'hand' ? 12 : 22) * Math.PI / 180, rr = n(p.reach, p.nozzle === 'sprinkler' ? 90 : 130);
          o.reach = [X + rr * Math.cos(a), Y - rr * Math.sin(a)];
        }
        if (p.type === 'gas_cloud' && Array.isArray(p.from)) o.from = p.fromIn === 'figure' ? p.from : (p.from[0] <= n(p.w, 200) && p.from[1] <= n(p.h, 120) ? [X + p.from[0], Y + p.from[1]] : p.from);
        if (S.gasFrom) o.gasFrom = [X + S.gasFrom[0], Y + S.gasFrom[1]];
        return o;
      });
    }
    return { resolve: resolve, geometry: geometry, shapes: GEOM, pathPts: pathPts };
  })();
  /* end kit-relate */

  /* ----------------------------------------------------------------- figure */
  function Figure(host, spec) {
    spec = RELATE.resolve(spec);
    if (spec && spec._relate && root.console) root.console.warn('kit: ' + spec._relate.join('; '));
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
    materials();                                       // the page's textures, once (2.52.0)
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
        if (self.laid) inkSoon(self);                 // 2.63.2: the ground a word stands on may have changed with the step
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
      if ((n === 0 || instant || reducedMotion()) && this.laid && !this.laying) inkSoon(this);   // 2.63.2: the step's ground
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
  var FIGS = [], UP_MAX = 2, UP_MARGIN = 1.02, ZOOM_MAX = 1.5, GROW_MAX = 1.3, FLOOR_PX = 12.5, PAD_PX = 4.5, CELL = 2;
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
  /* a name drawn over light equipment - a tank's cladding, the ship's white superstructure, machinery paint - is printed
     in dark ink as on a nameplate, not light letters in a dark halo (2.52.0, operator's review). Read once the labels are
     placed: the topmost painted shape under the name's centre (shades and hatches take no pointer, so they are passed by) */
  /* 2.63.2 - the words are judged against what is there NOW: a shape that is not shown (a cloud before its step, a wash
     at opacity 0) is no ground - the kit printed dark ink on the navy panel over a cloud not yet drawn (IGF M02 s15,
     M06 s04, M06 s11: 1.4:1). And every word of a part, not only names and captions: a part's own word on its light
     contents ("LNG" on the liquid of boil_off, 2:1, IGF M03 s06) gets the dark ink, or on a dark ground the panel's halo */
  function shownAt(n, svg) {                    // its opacity times its ancestors' up to the drawing (0: not shown)
    var o = 1;
    for (var e = n; e && e.nodeType === 1; e = e.parentNode) {
      var cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
      var v = parseFloat(cs.opacity);
      if (!isNaN(v)) o *= v;
      if (e === svg) break;
    }
    return o;
  }
  function ratio(a, b) { var x = luminance(a), y = luminance(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  /* now, and again once the kit's fades (0.3 s) have ended - a shape fading out still reads as ground halfway */
  function inkSoon(f) {
    inkOn(f);
    clearTimeout(f.inkT);
    f.inkT = setTimeout(function () { inkOn(f); }, 450);
  }
  /* 2.63.2 - a veil (a vapour cloud, data-veil) lies over shapes, never over words: a cloud listed after a part covered
     that part's words (IGF M06 s04, "hot exhaust 540 °C" and "lamp not certified safe", fixed there by moving the words).
     A cloud that covers an earlier part's words is drawn just before that part instead - the part and its words on top,
     still inside the cloud. (Kept out of the label solver: a room's own name inside its cloud found no place - the
     gallery's gas_cloud card.) */
  function veilsUnder(f) {
    q(f.svg, '[data-veil]').forEach(function (v) {
      var cloud = v.closest ? v.closest('g.kit-part') : null, holder = cloud && cloud.parentNode;
      if (!cloud || !holder) return;
      var vr = v.getBoundingClientRect(), first = null;
      if (!vr.width) return;
      q(f.svg, 'g.kit-lbl text').forEach(function (t) {
        var owner = t.closest('g.kit-part');
        while (owner && owner.parentNode !== holder) owner = owner.parentNode.closest ? owner.parentNode.closest('g.kit-part') : null;
        if (!owner || owner === cloud || !(owner.compareDocumentPosition(cloud) & 4)) return;   // 4: the cloud comes after
        var r = t.getBoundingClientRect();
        if (r.width && r.left < vr.right && r.right > vr.left && r.top < vr.bottom && r.bottom > vr.top &&
            (!first || (owner.compareDocumentPosition(first) & 4))) first = owner;
      });
      if (first) holder.insertBefore(cloud, first);
    });
  }
  function inkOn(f) {
    if (!document.elementsFromPoint) return;
    veilsUnder(f);
    q(f.svg, 'text.kit-sl, text.kit-cap, text.kit-h, text.kit-state').forEach(function (t) {
      t.classList.remove('kit-sl-ink');
      t.classList.remove('kit-ink-halo');
      var r = t.getBoundingClientRect(), name = t.classList.contains('kit-sl') || t.classList.contains('kit-cap');
      if (!r.width || shownAt(t, f.svg) < 0.5) return;
      var under = document.elementsFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      for (var i = 0; i < under.length; i++) {
        var n = under[i];
        if (n === f.svg || !f.svg.contains(n)) return;
        if (/^(text|tspan|g|line|polyline)$/.test(tagOf(n))) continue;
        var cs = getComputedStyle(n), c = rgba(cs.fill), op = parseFloat(cs.fillOpacity);
        if (!c || c[3] < 0.5 || (!isNaN(op) && op < 0.5) || shownAt(n, f.svg) < 0.5) continue;
        if (name) { if (luminance(c) > 0.25) t.classList.add('kit-sl-ink'); return; }
        var own = rgba(getComputedStyle(t).fill);              /* a part's own word: only when it does not read there */
        if (own && ratio(own, c) < 3) t.classList.add(luminance(c) > 0.25 ? 'kit-sl-ink' : 'kit-ink-halo');
        return;
      }
    });
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
  function seen(n, svg, memo) {                 // painted now: laid out, and not faded out by its step
    /* memo (2.52.0): one Map per measuring pass - a drawn piece of equipment nests its shapes deeper (an equipment group,
       a flange group), and every shape walked all its ancestors' styles again */
    memo = memo || new Map();
    function vis(p) {                           // its opacity times its ancestors' up to the drawing; -1 when not shown
      if (memo.has(p)) return memo.get(p);
      var cs = getComputedStyle(p), v;
      if (cs.display === 'none' || cs.visibility === 'hidden') v = -1;
      else if (p === svg || !p.parentElement) v = 1;
      else { var up = vis(p.parentElement); v = up < 0 ? -1 : up * parseFloat(cs.opacity); }
      memo.set(p, v);
      return v;
    }
    return vis(n) > 0.05;
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
  /* a label's words as the drawing audit judges them: the letters, the middle three-quarters of the line box - of ONE
     line (2.60.0): trimmed by the whole block, a four-line text lost a line's height and its last line was laid over the
     next text's first (M01 benchmark s07, "cool the liquid" over the venting caption) */
  function textBox(t, M) {
    var b;
    try { b = t.getBBox(); } catch (e) { return null; }
    if (!b || (!b.width && !b.height)) return null;
    var rows = Math.max(1, q(t, 'tspan').filter(function (s) { return s.style.display !== 'none'; }).length), lh = b.height / rows;
    var y = b.y + 0.18 * lh, h = b.height - 0.26 * lh;
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
      /* 2.50.6 - a part that moves for ever (an engine's pistons, a cylinder's piston, a vent's puffs) is measured at
         MOTION_PHASES of its cycle, held still: what it sweeps is in the way, not the one frame the layout happened on.
         The cylinder's "piston" label was placed clear of one frame and sat on the moving piston on others (M01 benchmark
         run 5, s06), as the drawing check now finds on every build */
      var anims = motions(svg), held = anims.map(function (a) { return { a: a, t: a.currentTime, run: a.playState === 'running' }; });
      try {
        /* 2.52.0: what does not move is measured once per state; the later phases measure only what the motions move */
        var movers = anims.map(function (a) { return a.effect.target; });
        (anims.length ? MOTION_PHASES : [null]).forEach(function (ph, pi) {
          if (ph !== null) holdAt(anims, ph);
          measure(pi > 0 ? movers : null);
        });
      } finally {
        var live = document.getAnimations();
        held.forEach(function (x) {
          if (live.indexOf(x.a) < 0) return;          // cancelled meanwhile: never revived
          try { x.a.currentTime = x.t; if (x.run) x.a.play(); } catch (e) { /* gone */ }
        });
      }
    });
    return G;

    function measure(only) {
      var ctm = svg.getScreenCTM();
      if (!ctm) return;
      var inv = ctm.inverse(), s = det(ctm), memo = new Map();
      G.scale = s;
      q(svg, GEOM).forEach(function (n, idx) {
        if (only && !only.some(function (t) { return t === n || t.contains(n); })) return;
        /* a body's light and shade (body()) is the same shape again: measured once, as the body; a bolt always sits on a
           body that is measured (2.52.0) */
        if (n.classList.contains('kit-sh') || n.classList.contains('kit-m-bolt') || notDrawn(n, svg) || !seen(n, svg, memo) || !painted(n)) return;
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
    }
  }
  /* the endless animations in a drawing, all held still at one moment of ONE clock (0 to 1 across the longest cycle, two
     cycles in) - real frames, so what the kit staggers stays staggered - as audit_drawing.js judges them */
  var MOTION_PHASES = [0, 0.25, 0.5, 0.75, 1];
  function motions(svg) {
    if (!document.getAnimations) return [];
    return document.getAnimations().filter(function (a) {
      var t = a.effect && a.effect.target;
      if (!t || !svg.contains(t)) return false;
      try { var c = a.effect.getComputedTiming(); return c.iterations === Infinity && c.duration > 0; } catch (e) { return false; }
    });
  }
  function holdAt(anims, ph) {
    var span = 0, lag = 0;
    anims.forEach(function (a) {
      try { span = Math.max(span, a.effect.getComputedTiming().duration); lag = Math.max(lag, a.effect.getTiming().delay || 0); }
      catch (e) { /* not timed */ }
    });
    anims.forEach(function (a) { try { a.pause(); a.currentTime = lag + (2 + ph) * span; } catch (e) { /* measured as it is */ } });
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
    var words = obs.filter(function (o) { return o.rect; }).map(function (o) { return o.rect; });   // the words drawn in parts
    labs.forEach(function (L) { L.opt = L.opt || {}; L.anchor = L.anchor || L.box; L.at = null; L.leader = null; });
    function inBounds(b) { return b.x >= bounds.x && b.y >= bounds.y && b.x2 <= bounds.x2 && b.y2 <= bounds.y2; }
    /* the grid marks every obstacle half a cell larger, so a box clear by `pad` on it is at least pad + half a cell from
       the obstacle itself. Words inside a room keep P from its walls - the 4 px audit_drawing.js judges. 2.63.0: they were
       let one cell closer (P - CELL, for a low bilge), which is 4.5 - s px on screen, 3.4-4 px at the usual scales - every
       such name then failed "touches the edge of the shape it sits in" (30 findings on IGF M05 s07 alone); a room too
       low for its name at that clearance sends the name beside it (search(L, true)) */
    function clear(b, inside) {
      var pad = inside ? Math.max(1, P - q2) : P;
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
      /* a name that keeps inside its part (a room's) and finds no clear place there - the room is filled with equipment,
         a valve's actuator stands where the name was - goes beside the part instead, with a leader if it must (2.52.0),
         never left on top of what is in the room */
      var best = search(L) || (L.opt.inside && !L.opt.fixed ? search(L, true) : null);
      if (best) { L.at = best.box; L.leader = best.leader; out.moved++; if (best.leader) out.leaders++; }
      else { L.at = L.box; out.unplaced.push(labs.indexOf(L)); }
      taken.push(L.at);
    });
    function search(L, outside) {
      var b = L.box, w = b.x2 - b.x, h = b.y2 - b.y, cx0 = (b.x + b.x2) / 2, cy0 = (b.y + b.y2) / 2, A = L.anchor;
      var inside = !!L.opt.inside && !outside, lead = !inside && L.opt.lead !== false, near = L.opt.near != null ? L.opt.near : 8;
      var C = inside ? (L.within || A) : null, R = inside ? 0 : (lead ? 160 : near + P), st = inside ? 2 : 4, best = null;
      var x0 = inside ? C.x : A.x - R - w, x1 = inside ? C.x2 - w : A.x2 + R, y0 = inside ? C.y : A.y - R - h, y1 = inside ? C.y2 - h : A.y2 + R;
      var selfA = !outside && (L.opt.self || meets(b, A));
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
      var own = words.filter(function (w) { var g2 = grown(w, P); return !(a.x > g2.x && a.x < g2.x2 && a.y > g2.y && a.y < g2.y2); });   // not a word the leader starts in
      var hits = 0, n = Math.ceil(len / CELL);
      for (var i = 0; i <= n; i++) {
        var px = a.x + dx * i / n, py = a.y + dy * i / n, from = len * i / n;
        /* a leader keeps the full clearance from every word - the labels placed, and the words drawn in parts (a
           detector's tag) - not just from the labels at half of it (2.52.0: IGF M07 s08, M09 s06) */
        for (var j = 0; j < taken.length + own.length; j++) {
          var t = grown(j < taken.length ? taken[j] : own[j - taken.length], P);
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
  /* 2 % over 1/s (2.52.0; 0.1 % before): a word grown to exactly 12.5 px once drawn read 12.4999 to the deck audit's
     svgSmall, which compares declared x rendered width / viewBox width against 12.5 (2.49.2) - and a frame grown a little
     after the words were sized left them at 12.4 px (scales 0.978-0.996, M01/M02 workflow benchmark 2026-10-20) */
  function upFor(s, fl) { var k = (fl || FLOOR_PX) / FLOOR_PX; return Math.min(UP_MAX * k, Math.max(1, UP_MARGIN * k / s)); }
  /* 2.63.3 (item 4 - the 2.63.2 full-course run: "tiny labels" in 14 of 15 modules, a deck figure is read from the back of a
     classroom): the floor a figure's words keep, from its --kit-floor (px) - 16 on a deck slide (kit.css), 12.5 elsewhere */
  function floorOf(svg) { var v = parseFloat(getComputedStyle(svg).getPropertyValue('--kit-floor')); return v > 0 ? v : FLOOR_PX; }
  /* words under the floor at the scale shown now grow at once, however small the change; larger words shrink back only
     past 1 %, so a few rounds of a frame settling do not re-lay the labels for nothing */
  function regrow(up2, up) { return up2 > up + 1e-4 || up - up2 >= 0.01; }
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
    var V = f.base.slice(), fl = floorOf(svg), upMax = UP_MAX * fl / FLOOR_PX;
    setView(svg, V);
    function upTo(u) {                    // the words' size, then every box sized to them, then the frames that hold boxes
      f.upNow = u;
      svg.style.setProperty('--kit-up', u.toFixed(3));
      f.fits.forEach(function (fit) { if (!fit.late) fit(u); });
      f.fits.forEach(function (fit) { if (fit.late) fit(u); });
    }
    var s = scaleNow(svg), up = upFor(s, fl);
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
        var up2 = upFor(s, fl);
        if (!crowded && regrow(up2, up)) { up = up2; upTo(up); }
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
          var up3 = upFor(s, fl);
          if (regrow(up3, up)) {
            up = up3; upTo(up);
            G = gather(f, states);
            P = PAD_PX / s;
            res = place(f, G, V, P);
          }
        }
      }
    }
    /* measured again once laid out: whatever moved the frame or the drawing's size on the way, no word is left under
       the floor at the scale it is shown at now (2.52.0) */
    s = scaleNow(svg);
    if (!crowded && up < upMax && regrow(upFor(s, fl), up)) {
      up = upFor(s, fl); upTo(up);
      G = gather(f, states);
      P = PAD_PX / s;
      res = place(f, G, V, P);
    }
    inkOn(f);
    return { theme: f.tone, scale: +s.toFixed(3), up: +up.toFixed(3), zoom: +zoom.toFixed(3), view: V.map(function (v) { return +v.toFixed(1); }),
             minTextPx: G.minPx < 1e8 ? +(G.minPx * scaleNow(svg) / G.scale).toFixed(2) : null, labels: res.labels, moved: res.moved,
             leaders: res.leaders, unplaced: res.unplaced, crowded: crowded, floorMet: !crowded && (up < upMax || s * UP_MAX >= 1), floorPx: fl };
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
    /* 2.52.0: the painted deck plate the well is let into, and the leaking pipe end with its flange, in their materials */
    body('path', { d: 'M0 ' + top + ' H' + x0 + ' V' + bot + ' H' + x1 + ' V' + top + ' H' + w + ' V' + h + ' H0 Z' }, g, { mat: 'deck', shade: 'box' });
    el('line', { x1: dx, y1: -20, x2: dx, y2: -2, 'class': 'kit-pipe-s kit-ms-steel' }, g);
    flange(g, dx, -1, 90, 24, 4);
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

  /* valve - a real valve: a cast body bolted into the line by its end flanges, a bonnet, and on top what works it - a
     yoke and a pneumatic diaphragm actuator on an automatic valve (the default), a stem and a handwheel on a manual one
     ("actuator": false). The ISA bow-tie stays on the body as a light plate: outline when open, filled when closed, red
     when it shut on a trip ("trip": false: closing is normal here, no red) (2.52.0). value 1 = open, 0 = closed */
  TYPES.valve = function (fig, part, g, p) {
    var s = p.size || 12, k = s * 0.72, u = s / 10;
    var bow = 'M' + (-s) + ' ' + (-k) + ' L' + s + ' ' + k + ' V' + (-k) + ' L' + (-s) + ' ' + k + ' Z';
    var sym = el('g', { transform: p.rotate ? 'rotate(' + p.rotate + ')' : null }, g);   // 90 = on a vertical pipe
    var cast = equip(sym);
    /* no taller than the ISA symbol it replaces (s + 15 above the line): a room's name over it keeps its place */
    [-1, 1].forEach(function (side) { flange(cast, side * (s + 6.5), 0, 0, 2 * k + 12, 5); });
    body('ellipse', { rx: s + 4.5, ry: k + 3 }, cast, { mat: 'cast', shade: 'round' });
    var top = -k - 3;
    body('rect', { x: -5 * u, y: top - 4 * u, width: 10 * u, height: 4.5 * u, rx: 1.5 }, cast, { mat: 'cast', shade: 'box' });   // the bonnet
    [-3.4 * u, 3.4 * u].forEach(function (bx) { el('circle', { cx: bx, cy: top - 3.2 * u, r: 0.9 * u, 'class': 'kit-m-bolt' }, cast); });   // its bolts
    top -= 4 * u;
    if (p.actuator !== false) {
      el('path', { d: 'M' + (-4.5 * u) + ' ' + top + ' V' + (top - 3 * u) + ' M' + (4.5 * u) + ' ' + top + ' V' + (top - 3 * u), 'class': 'kit-m-yoke' }, cast);
      el('line', { x1: 0, y1: top, x2: 0, y2: top - 3 * u, 'class': 'kit-m-stem' }, cast);
      /* the positioner on the yoke - the box that tells an automatic valve from a manual one, its air line to the actuator */
      body('rect', { x: 5.5 * u, y: top - 3.6 * u, width: 5 * u, height: 4 * u, rx: 0.6 }, cast, { mat: 'steel', shade: 'box' });
      el('path', { d: 'M' + (8 * u) + ' ' + (top - 3.6 * u) + ' V' + (top - 5.5 * u) + ' H' + (6 * u), 'class': 'kit-m-spoke' }, cast);
      top -= 3 * u;
      body('rect', { x: -11 * u, y: top - 1.5 * u, width: 22 * u, height: 1.5 * u, rx: 0.6 }, cast, { mat: 'steel' });   // the diaphragm case's flange
      top -= 1.5 * u;
      body('path', { d: 'M' + (-10 * u) + ' ' + top + ' Q' + (-10 * u) + ' ' + (top - 6 * u) + ' 0 ' + (top - 6 * u) + ' Q' + (10 * u) + ' ' + (top - 6 * u) +
                        ' ' + (10 * u) + ' ' + top + ' Z' }, cast, { mat: 'paint', shade: 'round' });
    } else {                                             // the gland nut, the yoke head and the stem nut under the handwheel
      body('rect', { x: -2.5 * u, y: top - 1.5 * u, width: 5 * u, height: 1.5 * u }, cast, { mat: 'steel' });
      el('line', { x1: 0, y1: top, x2: 0, y2: top - 6 * u, 'class': 'kit-m-stem' }, cast);
      body('rect', { x: -3 * u, y: top - 4.6 * u, width: 6 * u, height: 2.6 * u, rx: 0.6 }, cast, { mat: 'cast', shade: 'box' });
      el('ellipse', { cy: top - 6 * u, rx: 11 * u, ry: 3.2 * u, 'class': 'kit-m-wheel' }, cast);
      el('path', { d: 'M' + (-10 * u) + ' ' + (top - 6 * u) + ' H' + (10 * u) + ' M0 ' + (top - 8.8 * u) + ' V' + (top - 3.2 * u), 'class': 'kit-m-spoke' }, cast);
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
    /* a bolted flange at each end, where the pipe joins the next pipe or a piece of equipment: two pipes that meet
       show a pair of mating flanges (2.52.0). Square to the line however the path runs (a bend, a curve) */
    if (L > 12) {
      var across = (p.double ? 25 : fluid === 'air' ? 18 : 13) + (p.double ? 6 : 10);
      [[0, 2.5], [L, L - 2.5]].forEach(function (e) {
        var a = reach.getPointAtLength(e[1]), b = reach.getPointAtLength(e[0] ? Math.max(0, L - 6) : Math.min(L, 6));
        var dx = e[0] ? a.x - b.x : b.x - a.x, dy = e[0] ? a.y - b.y : b.y - a.y;
        /* it sits where the pipe meets what it runs into: that thing's own words (a bottle's tag) may cross it */
        flange(g, a.x, a.y, Math.atan2(dy, dx) * 180 / Math.PI, across, 5).setAttribute('data-may-overlap', '');
      });
    }
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
  /* 2.52.0: drawn as the tank is on deck - aluminium cladding over its insulation, cladding straps, standing on two
     saddles, with its dome (a flange on top) where a pipe of the spec leaves it, else near its right end. The lower part
     stays cut away so the LNG level is seen, pale at its surface and deep blue below. */
  TYPES.tank = function (fig, part, g, p) {
    var w = p.w || 190, h = p.h || 110, ex = h * 0.28, cid = fig.uid + '-' + p.id + '-t';
    var TANK_FOOT = clamp(h * 0.1, 4, 12);             // the saddles' feet below the shell: a low tank in a tight hold keeps to it
    var shape = 'M' + ex + ' 0 H' + (w - ex) + ' A' + ex + ' ' + (h / 2) + ' 0 0 1 ' + (w - ex) + ' ' + h +
      ' H' + ex + ' A' + ex + ' ' + (h / 2) + ' 0 0 1 ' + ex + ' 0 Z';
    el('path', { d: shape }, el('clipPath', { id: cid }, el('defs', {}, g)));
    var eq = equip(g);
    var sw = Math.min(21, w * 0.11);
    [0.25, 0.75].forEach(function (f) {                 // the saddles it stands on, each on a foot plate
      var cx = w * f;
      /* their tops are hidden behind the shell: words written on the tank may cross them (data-may-overlap) */
      body('path', { d: 'M' + (cx - sw) + ' ' + (h + TANK_FOOT - 3) + ' L' + (cx - sw * 0.72) + ' ' + (h - 24) + ' Q' + cx + ' ' + (h - 12) + ' ' +
                        (cx + sw * 0.72) + ' ' + (h - 24) + ' L' + (cx + sw) + ' ' + (h + TANK_FOOT - 3) + ' Z', 'data-may-overlap': '', 'data-no-contain': '' }, eq, { mat: 'paint', shade: 'box' });
      body('rect', { x: cx - sw - 6, y: h + TANK_FOOT - 4, width: 2 * sw + 12, height: 4, rx: 1 }, eq, { mat: 'paint' });
    });
    body('path', { d: shape }, eq, { mat: 'clad', shade: 'cyl' });
    var straps = el('g', { 'clip-path': 'url(#' + cid + ')', 'data-may-overlap': '', 'data-no-contain': '' }, eq);   // surface detail: words and marks on the tank cross them
    [0.36, 0.5, 0.64].forEach(function (f) {            // the cladding straps
      body('rect', { x: w * f - 2, y: 0, width: 4, height: h }, straps, { mat: 'steel', shade: 'cyl' });
    });
    var liq = el('rect', { x: 0, width: w, 'class': 'kit-liquid kit-m-lng', 'clip-path': 'url(#' + cid + ')' }, eq);
    var surf = el('line', { x1: 0, x2: w, 'class': 'kit-surface kit-m-lngs', 'clip-path': 'url(#' + cid + ')' }, eq);
    el('path', { d: shape, 'class': 'kit-vessel-o' }, eq);
    /* the dome: over the pipe that leaves the tank's top, else near its right end */
    /* 2.72.0: a dome under EVERY pipe that leaves the top (a second one - the vent line beside the bunker line - ended 10
       units over the shell, on nothing) */
    var tx = p.x || 0, ty = p.y || 0, domes = [];
    pipeEnds(fig).forEach(function (e) {
      if (Math.abs(e[1] - ty) <= 10 && e[0] - tx > ex && e[0] - tx < w - ex &&
          !domes.some(function (d) { return Math.abs(d - (e[0] - tx)) < 30; })) domes.push(e[0] - tx);
    });
    if (!domes.length) domes.push(w - ex - 22);
    var dome = el('g', { 'data-may-cross': '' }, eq);        // it rises into the tank connection space over it, by nature
    domes.forEach(function (dx) {
      body('rect', { x: dx - 11, y: -8, width: 22, height: 11, rx: 2 }, dome, { mat: 'clad', shade: 'box' });
      body('rect', { x: dx - 15, y: -10, width: 30, height: 3.5, rx: 1 }, dome, { mat: 'steel' });
    });
    if (p.label) label(fig, g, { x: w / 2, y: h + TANK_FOOT + 20, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
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

  /* exchanger - a heat exchanger (vaporizer, heater) drawn as one: a shell-and-tube body with flanged heads and the
     heating medium's nozzles under it, and its copper coil seen through the shell, so the heating still shows (2.52.0).
     value 0..1 = heating */
  TYPES.exchanger = function (fig, part, g, p) {
    var r = p.r || 18, z = r * 0.62, a = r * 0.78, b = r * 0.83, c = r / 3;
    var eq = equip(g);
    [-z, z].forEach(function (x) {                       // the heating medium's nozzles, under the shell
      body('rect', { x: x - 2.2, y: b - 1, width: 4.4, height: r + 3 - b }, eq, { mat: 'steel' });
    });
    body('path', { d: 'M' + (-a) + ' ' + (-b) + ' H' + a + ' A' + c + ' ' + b + ' 0 0 1 ' + a + ' ' + b + ' H' + (-a) + ' A' + c + ' ' + b + ' 0 0 1 ' + (-a) + ' ' + (-b) + ' Z' },
         eq, { mat: 'cast', shade: 'cyl' });
    [-a - 1, a - 2].forEach(function (x) {               // the flanged heads
      body('rect', { x: x, y: -b - 2, width: 3, height: 2 * b + 4, rx: 1 }, eq, { mat: 'steel', shade: 'box' });
    });
    var coil = el('path', { d: 'M' + (-r) + ' 0 L' + (-z) + ' 0 L' + (-z / 2) + ' ' + (-z) + ' L0 ' + z + ' L' + (z / 2) + ' ' + (-z) + ' L' + z + ' 0 L' + r + ' 0', 'class': 'kit-coil' }, g);
    el('line', { x1: -z, y1: r + 2, x2: -z, y2: r + 12, 'class': 'kit-hm' }, g);
    el('line', { x1: z, y1: r + 2, x2: z, y2: r + 12, 'class': 'kit-hm' }, g);
    if (p.label) label(fig, g, { x: 0, y: r + 30, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { g.classList.toggle('kit-active', v > 0.5); coil.style.opacity = (0.55 + 0.45 * clamp(v, 0, 1)).toFixed(2); };
  };

  /* pump - P&ID centrifugal pump. value 0 stopped, 1 running (impeller turns) */
  /* 2.52.0: a cast volute casing on its foot, the discharge nozzle leaving it at the top, the impeller seen turning in its
     eye */
  TYPES.pump = function (fig, part, g, p) {
    var r = p.r || 15;
    var eq = equip(g);
    body('path', { d: 'M' + (-r * 0.55) + ' ' + (r * 0.6) + ' L' + (-r * 0.8) + ' ' + (r + 3) + ' H' + (r * 0.8) + ' L' + (r * 0.55) + ' ' + (r * 0.6) + ' Z' },
         eq, { mat: 'paint', shade: 'box' });                                                         // the foot
    body('rect', { x: -r - 4, y: r + 2, width: 2 * r + 8, height: 4, rx: 1 }, eq, { mat: 'paint' });  // the base plate
    body('path', { d: 'M0 ' + (-r) + ' H' + (r + 8) + ' V' + (-r + 8) + ' H' + (r * 0.5) + ' Z' }, eq, { mat: 'cast', shade: 'box' });   // discharge
    body('circle', { r: r }, eq, { mat: 'cast', shade: 'round' });
    el('circle', { r: r * 0.76, 'class': 'kit-m-hole' }, eq);
    var imp = el('g', { 'class': 'kit-imp' }, g);
    [0, 120, 240].forEach(function (a) { el('path', { d: 'M0 0 L' + (r * 0.7) + ' -3', transform: 'rotate(' + a + ')' }, imp); });
    if (p.label) label(fig, g, { x: 0, y: r + 22, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
    part.render = function (v) { g.classList.toggle('kit-running', v > 0.5); };
  };

  /* engine - a dual-fuel engine block. value 0 stopped, 1 running */
  var ENGINE_STROKE_LOW = 25;
  /* 2.52.0: the painted block on its bedplate, bolted cylinder covers, a turbocharger at the end no pipe of the spec comes
     in at (none when both are taken), and RUNNING / STOPPED on a name plate on the block, where it reads */
  TYPES.engine = function (fig, part, g, p) {
    var w = p.w || 100, h = p.h || 70, n = p.cylinders || 4, cw = (w - 16) / n, X = p.x || 0, Y = p.y || 0;
    var eq = equip(g);
    var bed = body('rect', { x: -4, y: h - 3, width: w + 8, height: 8, rx: 1.5 }, eq, { mat: 'paint', shade: 'box' });
    /* the turbocharger: its casing, the duct into the block, its intake - drawn at the left end, mirrored to the right when
       a pipe or another part is in the way there, left out when both ends are taken (decided at layout, from what is
       drawn: a spool piece's pipe runs into the block as well as a pipe does) */
    var tg = el('g', {}, eq);
    body('rect', { x: -6, y: 16, width: 8, height: 12 }, tg, { mat: 'steel' });
    body('rect', { x: -31, y: 15, width: 9, height: 14, rx: 2 }, tg, { mat: 'steel', shade: 'cyl' });   // the intake silencer
    body('circle', { cx: -13, cy: 22, r: 11 }, tg, { mat: 'cast', shade: 'round' });
    el('circle', { cx: -13, cy: 22, r: 4.5, 'class': 'kit-m-hole' }, tg);
    function taken(B, own) {
      if (pipeThrough(fig, B)) return true;
      return q(fig.svg, '.kit-part').some(function (o) {
        if (o === g || !o.getBBox) return false;
        var m = /translate\(\s*([-\d.]+)[ ,]+([-\d.]+)/.exec(o.getAttribute('transform') || ''), b;
        try { b = o.getBBox(); } catch (e) { return false; }
        if (!b.width && !b.height) return false;
        var ox = m ? +m[1] : 0, oy = m ? +m[2] : 0, R = { x: ox + b.x, y: oy + b.y, x2: ox + b.x + b.width, y2: oy + b.y + b.height };
        /* a room the engine stands in: the turbocharger must fit inside it too, never through its wall */
        if (R.x <= own.x && R.y <= own.y && R.x2 >= own.x2 && R.y2 >= own.y2) return !(B.x >= R.x + 2 && B.x2 <= R.x2 - 2);
        return meets(R, B);
      });
    }
    var block = body('rect', { width: w, height: h, rx: 6 }, eq, { mat: 'paint', shade: 'box' });
    for (var i = 0; i < n; i++) {
      var cx = 8 + cw * i + cw / 2, hw = cw * 0.64;
      body('rect', { x: cx - hw / 2, y: -10, width: hw, height: 14, rx: 2 }, eq, { mat: 'paintl', shade: 'box' });
      [cx - hw / 2 + 3, cx + hw / 2 - 3].forEach(function (bx) { el('circle', { cx: bx, cy: -6.5, r: 1.2, 'class': 'kit-m-bolt' }, eq); });
      /* the crankcase door the piston is seen working behind (2.52.0): a bolted steel door round a dark opening */
      var dw = cw * 0.76;
      body('rect', { x: cx - dw / 2, y: 5, width: dw, height: 22, rx: 2 }, eq, { mat: 'steel', shade: 'box' });
      el('rect', { x: cx - cw * 0.27, y: 7, width: cw * 0.54, height: 19, rx: 1.5, 'class': 'kit-engine-recess' }, eq);
      [[cx - dw / 2 + 2.2, 7.2], [cx + dw / 2 - 2.2, 7.2], [cx - dw / 2 + 2.2, 24.8], [cx + dw / 2 - 2.2, 24.8]].forEach(function (b) {
        el('circle', { cx: b[0], cy: b[1], r: 0.9, 'class': 'kit-m-bolt' }, eq);
      });
      el('rect', { x: cx - cw * 0.22, y: 8, width: cw * 0.44, height: 12, rx: 2, 'class': 'kit-piston', style: 'animation-delay:' + (-0.15 * i) + 's' }, g);
    }
    var plate = el('rect', { rx: 3, 'class': 'kit-m-label' }, g);
    var st = el('text', { x: w / 2, y: h - 12, 'text-anchor': 'middle', 'class': 'kit-state' }, g);
    /* RUNNING / STOPPED under the LOWEST point of the pistons' stroke (y 8 + 12 tall + kit.css kit-piston's 5 = 25) with the
       kit's clearance on screen (PAD_PX, grown with the words), its letters measured, not guessed; the block as tall and as
       wide as that needs. Before 2.50.6 the word was placed for 29 + 10 x its growth: at a grown size its letters reached
       up into the stroke, so the part's own RUNNING sat over its own piston on some frames (M01 benchmark run 5, s03) and
       ran past a narrow block's sides. */
    /* 2.52.0: the word stands on a dark name plate (it reads on the paint), the plate clear of the stroke, the block round
       the plate, the bedplate under the block and the name under the bedplate */
    var lt = null;
    fig.fit(function (k) {
      var keep = st.textContent, pad = PAD_PX * k, bb = null, px = 5 * k, py = 3 * k;
      st.textContent = 'RUNNING';
      st.setAttribute('y', 0);
      try { bb = st.getBBox(); } catch (e) { bb = null; }
      var up = bb && bb.height ? -bb.y : 10 * k, down = bb && bb.height ? bb.y + bb.height : 3 * k;
      var tw = widest(st, ['RUNNING', 'STOPPED']);
      st.textContent = keep;
      var base = Math.max(h - 12 - py, ENGINE_STROKE_LOW + pad + py + up), pw = tw + 2 * px;
      var bh = Math.max(h, base + down + py + pad + 2), bw = Math.max(w, pw + 2 * pad + 4), x0 = (w - bw) / 2;
      st.setAttribute('y', base);
      plate.setAttribute('x', w / 2 - pw / 2); plate.setAttribute('width', pw);
      plate.setAttribute('y', base - up - py); plate.setAttribute('height', up + down + 2 * py);
      reshape(block, { x: x0, width: bw, height: bh });
      reshape(bed, { x: x0 - 4, width: bw + 8, y: bh - 3 });
      var own = { x: X + x0, y: Y - 10, x2: X + x0 + bw, y2: Y + bh + 5 };
      var side = !taken({ x: X + x0 - 32, y: Y + 10, x2: X + x0 - 1, y2: Y + 34 }, own) ? -1 :
                 !taken({ x: X + x0 + bw + 1, y: Y + 10, x2: X + x0 + bw + 32, y2: Y + 34 }, own) ? 1 : 0;
      tg.style.display = side ? '' : 'none';
      tg.setAttribute('transform', side < 0 ? 'translate(' + x0.toFixed(2) + ' 0)' : 'translate(' + (w - x0).toFixed(2) + ' 0) scale(-1 1)');
      if (lt) lt.setAttribute('y', bh + 5 + 4 + 14 * k);
    });
    if (p.label) lt = label(fig, g, { x: w / 2, y: h + 28, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label).querySelector('text');
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
  /* how far a vent's puffs may rise: into free air only (2.50.7). A puff starts 12 above the outlet, rises PUFF_RISE and
     grows to 10.5 across; it stops PAD_PX short of the lowest thing drawn above the outlet - another part, a room's ceiling
     when the outlet is inside it - so it never enters another drawing. M01 benchmark run 5, s03: the lower ship's vent mast
     stood under the upper ship's drawing and its puffs rose into a space there on some frames - the deterministic drawing
     check (2.50.6) found it on every build. Measured in the drawing's own units, at every layout (after the boxes are sized). */
  var PUFF_RISE = 34;
  function ventRise(fig, g) {
    var svg = fig.svg, sc = svg.getScreenCTM(), gc = g.getScreenCTM();
    if (!sc || !gc) return PUFF_RISE;
    var inv = sc.inverse(), o = onto(inv.multiply(gc), 0, 0), pad = PAD_PX / det(sc);
    var xs = [-15, -10, -5, 0, 5, 10, 15].map(function (d) { return o.x + d; });
    var start = o.y - 8.5, top = o.y - 22.5 - PUFF_RISE - pad, ceil = -1e9, pt = svg.createSVGPoint();
    function has(n, L, x, y, how) {
      var l = onto(L, x, y);
      pt.x = l.x; pt.y = l.y;
      try { return how === 'fill' ? n.isPointInFill(pt) : n.isPointInStroke(pt); } catch (e) { return false; }
    }
    q(svg, GEOM).forEach(function (n) {
      if (g.contains(n) || (n.closest && n.closest('.kit-lbl, .kit-leaders, defs')) || n.classList.contains('kit-hit') || !painted(n)) return;
      var b, nc = n.getScreenCTM();
      try { b = n.getBBox(); } catch (e) { return; }
      if (!nc || !(b.width || b.height)) return;
      var M = inv.multiply(nc), bb = boxOf([onto(M, b.x, b.y), onto(M, b.x + b.width, b.y), onto(M, b.x, b.y + b.height), onto(M, b.x + b.width, b.y + b.height)]);
      if (bb.x2 < xs[0] || bb.x > xs[6] || bb.y2 < top || bb.y > start) return;
      if (tagOf(n) === 'text') { ceil = Math.max(ceil, Math.min(bb.y2, start)); return; }
      /* scanned upward from the puffs' start, across their width: the first height where the shape is met - its line or
         its inside, or, for a room the outlet stands in, the room's ceiling (geometry, as the drawing check judges it) */
      var L = nc.inverse().multiply(sc), within = has(n, L, o.x, start, 'fill');
      for (var y = start; y >= top; y -= 1) {
        if (xs.some(function (x) { return has(n, L, x, y, 'stroke') || (within ? !has(n, L, x, y, 'fill') : has(n, L, x, y, 'fill')); })) {
          ceil = Math.max(ceil, y);
          break;
        }
      }
    });
    return Math.max(0, Math.min(PUFF_RISE, o.y - ceil - 22.5 - pad));
  }
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
    /* 2.52.0: the vent head as it is - a flange on the pipe end and the flame screen's cast collar over it, open above */
    var head = equip(g);
    body('rect', { x: -10, y: -2, width: 20, height: 4, rx: 1 }, head, { mat: 'steel', shade: 'box' });
    body('rect', { x: -7, y: -7, width: 14, height: 5.5, rx: 1.2 }, head, { mat: 'cast', shade: 'box' });
    el('path', { d: 'M-4 -7 V-1.5 M0 -7 V-1.5 M4 -7 V-1.5', 'class': 'kit-m-spoke' }, head);     // the screen's mesh
    /* 2.72.0 - the gas leaving, STILL: a plume over the outlet that stays while it vents. The puffs are pure animation from
       opacity 0, so a still figure (a task page, a screenshot, reduced motion) showed a venting mast with no gas at all
       (IGF 2.71.0 review: "the gas is not being ejected"). It rises as far as the puffs may (into free air only) */
    var plume = el('g', { 'class': 'kit-plume', 'data-may-cross': '', 'data-no-contain': '', 'data-low-contrast': '' }, g);
    [[0, -13, 5], [-3, -22, 6.5], [3, -31, 8]].forEach(function (c) { el('circle', { cx: c[0], cy: c[1], r: c[2] }, plume); });
    var puffs = el('g', { 'class': 'kit-puffs' }, g);
    [0, 0.45, 0.9].forEach(function (d, i) {
      el('circle', { cx: (i - 1) * 5, cy: -12, r: 7, style: 'animation-delay:' + d + 's' }, puffs);
    });
    fig.fit(function () {
      var rise = ventRise(fig, g);
      puffs.style.setProperty('--rise', -rise + 'px');
      plume.setAttribute('transform', 'translate(0 -8) scale(' + Math.max(0.35, Math.min(1, rise / PUFF_RISE)).toFixed(2) + ') translate(0 8)');
    }, true);
    if (p.label) label(fig, g, { x: p.labelAt === 'left' ? -18 : 18, y: -2, 'text-anchor': p.labelAt === 'left' ? 'end' : 'start', 'class': 'kit-cap' }, p.label);
    part.render = function (v) {
      puffs.style.opacity = clamp(v, 0, 1).toFixed(2);
      plume.style.opacity = (0.55 * clamp(v, 0, 1)).toFixed(2);
      g.classList.toggle('kit-venting', v > 0.05);
    };
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
    var w = p.w || 560, rows = p.rows || 2, rh = 24, k = 1, tx = 94, two = {}, lines2 = false, msgY = 15.5;
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
      /* 2.60.0: a row of several lines is as tall as its words MEASURED, with 7 above and below them, and they sit in its
         middle - 16 a line fell behind the words once they grew to the 12.5 px floor: a three-line alarm stood 4 px under
         the row's top, a narrow log's six-to-eight-line one on its foot (0-1 px). The drawing audit's old whole-block trim
         hid both; it measures one line's letters now. A one-line row is as it was. */
      rh = (8 + 16 * lines2) * k; msgY = 15.5 * k;
      if (lines2 > 1) {
        var pg = el('g', { 'aria-hidden': 'true' }, g), pb;          // lines2 rows of tall and deep letters, as styled
        lines(pg, { x: 0, y: 0, 'class': 'kit-msg' }, new Array(lines2 + 1).join('Hg\n').slice(0, -1));
        try { pb = pg.getBBox(); } catch (e) { pb = null; }
        g.removeChild(pg);
        if (pb && pb.height) {
          rh = Math.max(rh, pb.height + 14 * k + 3);
          msgY = (rh - 3 - pb.height) / 2 - pb.y;
        }
      }
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
        el('text', { x: 16, y: msgY, 'class': 'kit-time' }, row, clock(fig, a.t));       // on the message's first line
        /* a wrapped alarm keeps the space it was broken at: lines() puts an undrawn space between rows, so "HIGH PRESSURE"
           over "ALARM" reads "HIGH PRESSURE ALARM" to a screen reader and to the drawing audit (K11, 2.49.1) */
        lines(row, { x: tx, y: msgY, 'class': 'kit-msg' }, two[a.text] ? two[a.text].join('\n') : a.text);
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
    function ids(s) { return s && s.line != null ? [].concat(s.line).map(Number) : []; }
    /* 2.63.3 - the deck drives the figure, its lines and the slide's text parts from ONE counter (gb_deck.js lockFor): the
       line(s) each step lights, and a way to put the figure at a step. Not when the module's own hook steps the slide */
    if (!before.step && (f.spec.steps || []).length) {
      root.GB_HOOKS[id].lines = (f.spec.steps || []).map(ids);
      root.GB_HOOKS[id].go = function (n, animate) {
        if (animate && n === f.n + 1) f.next();
        else if (animate && n === f.n - 1) f.prev();
        else if (n !== f.n) f.go(n, true);
      };
    }
    f.on('step', function (n) {
      [].forEach.call(slide.querySelectorAll('[data-i]'), function (x) { x.classList.remove('cur', 'lit'); });
      (f.spec.steps || []).slice(0, n).forEach(function (s, i) {
        ids(s).forEach(function (k) {
          var line = slide.querySelector('[data-i="' + k + '"]');
          if (line) line.classList.add(i === n - 1 ? 'cur' : 'lit');
        });
      });
      var hk = root.GB_HOOKS[id];                       // the deck re-lights from its counter, and shows the line's part
      if (hk && hk.sync) hk.sync(n);
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
      /* 2.63.2 (item 4): a part merged into the kit has its colours calibrated in the gallery like kit.css's own rules, so
         the drawing check (audit_drawing.js kitColourRules) treats this sheet as the kit's own - push_button's cap, lid and
         tag failed 2.3:1 on a task page's symbol, where only kit.css was exempt */
      if (!mine) st.setAttribute('data-kit-own', '');
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
    /* 2.72.0 - a spec's relations ("on", "at", "from"/"to" ...) resolved to x / y / d, and every part's box and ports */
    relate: RELATE.resolve, geometry: RELATE.geometry,
    /* the drawing helpers every part uses - a new part uses these too, never its own */
    h: { el: el, lines: lines, label: label, gone: gone, widest: widest, readings: readings, clamp: clamp, num: num, fmt: fmt, polar: polar, arc: arc,
         drag: drag,
         flagMark: flagMark, textWidth: textWidth, NS: NS,
         /* physical equipment in its material, its light and shade, its flanges (2.52.0, L63) */
         equip: equip, body: body, reshape: reshape, flange: flange },
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
  var wl = p.draft != null ? p.draft : 0.55, hull, cid = fig.uid + '-' + (p.id || 'ga') + '-hull';
  /* 2.52.0: the ship as she looks from the quay (operator, from photos of LNG-fuelled ships): painted topsides in their
     plating strakes, a white sheer stripe and the deck rail, a pale boot-top line at the waterline, dark bottom paint
     under it, the rudder under the counter, the anchor in its hawse at the bow; a white superstructure with its bridge
     windows and a lower row, the funnel with its band and its sooty top. The outline is the one specs were placed on:
     a named space keeps its place. Seen from above ("plan") she is her painted deck inside a white bulwark. */
  /* 2.72.0 "cut": true - a straight piece of the ship's side (deck edge, plating, boot-top, the sea) for a close-up: the
     bunkering station, a vent mast's foot - something on board to stand on and hang from, never parts floating in air */
  var cut = !plan && !!p.cut;
  if (plan) {
    var b = w * 0.16;
    hull = 'M0 0 H' + (w - b) + ' Q' + w + ' 0 ' + w + ' ' + (d / 2) + ' Q' + w + ' ' + d + ' ' + (w - b) + ' ' + d + ' H0 Z';
  } else if (cut) {
    hull = 'M0 0 H' + w + ' V' + d + ' H0 Z';
    if (p.water !== false) {
      h.el('rect', { x: -12, y: d * wl, width: w + 24, height: d * (1 - wl) + 10, 'class': 'kit-ga-sea', 'data-no-contain': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);
    }
  } else {
    hull = 'M0 0 H' + w + ' Q' + (w * 0.97) + ' ' + (d * 0.62) + ' ' + (w * 0.87) + ' ' + d +
      ' H' + (w * 0.1) + ' L' + (w * 0.03) + ' ' + (d * 0.5) + ' Z';
    if (p.water !== false) {
      h.el('rect', { x: -12, y: d * wl, width: w + 24, height: d * (1 - wl) + 10, 'class': 'kit-ga-sea', 'data-no-contain': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);   // a backdrop: the hull covers it
    }
  }
  h.el('path', { d: hull }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var ship = h.equip(g, { shadow: false });
  if (!plan && !cut) {                                  // the rudder under the counter, the bulbous bow under the stem
    h.el('path', { d: 'M' + (w * 0.042) + ' ' + (d * 0.6) + ' H' + (w * 0.075) + ' V' + (d * 0.96) + ' H' + (w * 0.05) + ' Z', 'class': 'kit-m-bottom', 'data-may-cross': '' }, ship);
    if (d >= 30) h.el('path', { d: 'M' + (w * 0.9) + ' ' + (d * 0.68) + ' Q' + (w * 0.985) + ' ' + (d * 0.66) + ' ' + (w * 0.985) + ' ' + (d * 0.8) +
                                    ' Q' + (w * 0.985) + ' ' + (d * 0.93) + ' ' + (w * 0.88) + ' ' + (d * 0.96) + ' Z', 'class': 'kit-m-bottom', 'data-may-cross': '' }, ship);
  }
  h.body('path', { d: hull }, ship, { mat: plan ? 'deck' : 'hull' });
  /* the hull's paint - bottom paint, boot-top, sheer stripe - is surface detail: words over the ship may cross it (a tank
     name in the hold met the boot-top line, IGF M03 s10); the hull's outline still holds them */
  var paint = h.el('g', { 'clip-path': 'url(#' + cid + ')', 'data-may-overlap': '' }, ship);
  if (plan) {
    h.el('path', { d: hull, 'class': 'kit-ga-bulwark' }, paint);
  } else {
    h.el('rect', { x: 0, y: d * wl, width: w, height: d * (1 - wl) + 2, 'class': 'kit-m-bottom' }, paint);
    h.el('line', { x1: 0, x2: w, y1: d * wl, y2: d * wl, 'class': 'kit-ga-boot' }, paint);
    h.el('rect', { x: 0, y: 0, width: w, height: Math.max(2, Math.min(4, d * 0.07)), 'class': 'kit-m-white' }, paint);
    if (d >= 30 && !cut) h.body('ellipse', { cx: w * 0.088, cy: d * 0.8, rx: 2.6, ry: d * 0.15 }, paint, { mat: 'cast', shade: 'round' });   // the propeller
    if (d >= 30 && !cut) {                             // the hawse pipe and the anchor in it, under the bulwark at the bow
      var ax = w * 0.935, ay = d * 0.2;
      h.el('ellipse', { cx: ax, cy: ay, rx: 3.2, ry: 2.2, 'class': 'kit-m-window' }, paint);
      h.el('path', { d: 'M' + ax + ' ' + (ay + 2) + ' V' + (ay + 9) + ' M' + (ax - 4) + ' ' + (ay + 7) + ' Q' + ax + ' ' + (ay + 11) + ' ' + (ax + 4) + ' ' + (ay + 7),
                     'class': 'kit-ga-anchor' }, paint);
    }
  }
  h.el('path', { d: hull, 'class': 'kit-sh kit-sh-box' }, ship);   // light from above over all of it
  h.el('path', { d: hull, 'class': 'kit-ga-hull' }, ship);
  if (!plan) {                                          // the deck rail: a top rail on its stanchions
    var rail = 'M2 -6 H' + (w - 6);
    for (var rx = 2; rx < w - 6; rx += 12) rail += ' M' + rx + ' -6 V0';
    h.el('path', { d: rail, 'class': 'kit-ga-rail' }, ship);
  }
  var wash = h.el('path', { d: hull, 'class': 'kit-wash', 'data-no-contain': '' }, g);
  (p.frames || []).forEach(function (x) {
    h.el('line', { x1: x, x2: x, y1: 3, y2: d - 3, 'class': 'kit-ga-frame' }, g);
  });
  if (!plan && p.house) {
    var hs = p.house, hh = hs.h, hx = hs.x, hw = hs.w, i, mx = hx + hw * (p.funnel && p.funnel.x > hx + hw / 2 ? 0.25 : 0.72);
    h.el('path', { d: 'M' + mx + ' ' + (-hh) + ' V' + (-hh - 20) + ' M' + (mx - 7) + ' ' + (-hh - 16) + ' H' + (mx + 7), 'class': 'kit-ga-mast' }, ship);   // the mast and its radar
    /* data-kit-place (2.52.0): a task question asks for "G.house" / "G.funnel" (task_pages.py kit_places) and its tap area
       is laid on this shape (gb_answer.js placeParts - the first match: the body, drawn before its shading) */
    h.body('rect', { x: hx, y: -hh, width: hw, height: hh, rx: 3, 'data-kit-place': 'house' }, ship, { mat: 'white', shade: 'box' });
    var rows = [[-hh + 4, Math.max(2.5, Math.min(5, hh * 0.08)), 5.5]];          // the bridge windows along the top
    if (hh >= 30) rows.push([-hh * 0.34, Math.max(2, Math.min(3.5, hh * 0.05)), 3.5]);   // and a lower row
    rows.forEach(function (r) {
      for (i = hx + 5; i + r[2] <= hx + hw - 4; i += 9) h.el('rect', { x: i, y: r[0], width: r[2], height: r[1], rx: 0.6, 'class': 'kit-m-window' }, ship);
    });
    if (p.funnel) {
      var f = p.funnel, fh = f.h || 22, fw = f.w || 18;
      h.body('rect', { x: f.x, y: -hh - fh, width: fw, height: fh, rx: 2, 'data-kit-place': 'funnel' }, ship, { mat: 'white', shade: 'cylv' });
      h.el('rect', { x: f.x, y: -hh - fh * 0.62, width: fw, height: fh * 0.24, 'class': 'kit-ga-band' }, ship);     // the funnel's band
      h.el('rect', { x: f.x, y: -hh - fh, width: fw, height: fh * 0.16, rx: 2, 'class': 'kit-m-window' }, ship);    // its sooty top
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
  look: 'equipment',
  why: 'M02 s12 zones on an IGF ship, M01 s04 the five new spaces and s09 two ships compared: the ship the named spaces sit in',
  value: 'how strongly the ship is picked out, 0..1 (named spaces are space parts placed on it)',
  css: '.kit-ga-hull{fill:none;stroke:var(--dim-d);stroke-width:2;stroke-linejoin:round;transition:stroke .3s}.kit-ga-sea{fill:var(--cold);opacity:.12}' +
    '.kit-ga-boot{stroke:var(--mat-stem);stroke-width:1.5}.kit-ga-anchor{fill:none;stroke:var(--mat-yoke);stroke-width:1.6;stroke-linecap:round}' +
    '.kit-ga-rail{fill:none;stroke:var(--dim-d);stroke-width:1}.kit-ga-band{fill:var(--mat-hull)}' +
    '.kit-ga-mast{fill:none;stroke:var(--dim-d);stroke-width:2;stroke-linecap:round}' +
    '.kit-ga-bulwark{fill:none;stroke:var(--mat-white);stroke-width:6}' +
    '.kit-ga-frame{stroke:var(--faint-d);stroke-width:1;stroke-dasharray:3 4}.kit-lit .kit-ga-hull{stroke:var(--blue)}',
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
  /* 2.66.0 - markers[k].drag: true - the trainee drags that marker along the scale (finger, mouse, the arrow keys) and its
     word reads the value live (gas M02 s11: "two trainees drag the tank marker"); the next step puts it back */
  var drag = dragger(fig, h, part, g, p, made, markT, lo, hi, every, function (v) { return 'translate(0 ' + y(v).toFixed(1) + ')'; },
                     function (dm) { return { x: -4, y: 0, w: bw + 44, h: H }; },
                     function (px, py) { return lo + h.clamp((H - py) / H, 0, 1) * (hi - lo); });
  part.render = function (v) {
    made.forEach(function (m, k) {
      var c = h.clamp(v - k, 0, 1), from = 0;            // from the top of the scale
      m.g.setAttribute('transform', 'translate(0 ' + (from + (m.at - from) * c).toFixed(1) + ')');
      m.g.style.opacity = c > 0.001 ? '1' : '0';
    });
    drag(v);
  };
  /* the dragged marker: one per scale - the first that asks (a second would take the first one's place under a finger) */
  function dragger(fig, h, part, g, p, made, markT, lo, hi, every, at, box, value) {
    var dm = -1;
    (p.markers || []).forEach(function (m, k) { if (m.drag && dm < 0) dm = k; });
    if (dm < 0) return function () {};
    var mk = p.markers[dm], now = null, lastV = null, step = p.step || every / 4;
    function put() {
      made[dm].g.setAttribute('transform', at(now));
      made[dm].g.style.opacity = '1';
      markT[dm].word.textContent = (mk.label ? mk.label + ' ' : '') + h.fmt(now, { decimals: p.decimals || 0, unit: p.unit });
    }
    h.drag(g, box(dm), {
      name: 'drag the ' + (mk.label || 'marker') + ' along the scale to read its value',
      move: function (px, py) { now = value(px, py); put(); },
      step: function (dx, dy) { now = h.clamp((now != null ? now : mk.at) + (dx - dy) * step, lo, hi); put(); }
    });
    return function (v) {
      if (v !== lastV) {                                 // the steps moved the figure: the marker goes where they say
        if (now != null) markT[dm].word.textContent = mk.label || '';
        now = null; lastV = v;
      }
      if (now != null) put();
    };
  }
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
    var drag = dragger(fig, h, part, g, p, made, markT, lo, hi, every, function (v) { return 'translate(' + x(v).toFixed(1) + ' 0)'; },
                       function (k) { var r = markT[k].rise; return { x: 0, y: -r - 14, w: L, h: r + th + 22 }; },
                       function (px) { return lo + h.clamp(px / L, 0, 1) * (hi - lo); });
    part.render = function (v) {
      made.forEach(function (m, k) {
        var c = h.clamp(v - k, 0, 1);                     // drops onto its own place on the axis
        /* not yet there (c = 0) it waits invisibly at its own place: a marker parked 40 above its place stood past the
           frame the layout zoomed to, and the drawing audit reported it "cut off (in a later step)" (2.49.1) */
        m.g.setAttribute('transform', 'translate(' + m.at.toFixed(1) + ' ' + (c > 0.001 ? -(1 - c) * 40 : 0).toFixed(1) + ')');
        m.g.style.opacity = c > 0.001 ? Math.min(1, c * 2).toFixed(2) : '0';
      });
      drag(v);
    };
  }
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M01",
  course: 'IGF Basic', module: 'M01', made: '2026-10-15',
  look: 'diagram',
  why: 'M01 s02: oil fuel, methanol and LNG slide to their places on a temperature scale either side of the 60 °C line',
  value: '0..number of markers - marker k slides from the top of the scale to its place while the value goes from k to k+1; a marker with drag: true the trainee moves too (2.66.0)',
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
  /* 2.52.0: cut through as on board - the cast liner and cover, the steel piston on its rod, the exhaust valve and the
     injectors in their materials; the sprays and the flame stay the teaching colours */
  var moving = h.el('g', { 'class': 'kit-cylinder-moving', 'data-kit-body': '' }, g), pin = pTop + ph * 0.62, be = H - 46;   // piston and rod: one moving piece
  /* the connecting rod, tapered from the gudgeon pin to its big end - it stays in the liner at the bottom of the stroke */
  h.body('path', { d: 'M' + (w / 2 - 6) + ' ' + pin + ' L' + (w / 2 - 9) + ' ' + be + ' H' + (w / 2 + 9) + ' L' + (w / 2 + 6) + ' ' + pin + ' Z' }, moving, { mat: 'steel', shade: 'cylv' });
  h.body('circle', { cx: w / 2, cy: be, r: 9 }, moving, { mat: 'cast', shade: 'round' });
  h.body('rect', { x: 4, y: pTop, width: w - 8, height: ph, rx: 4 }, moving, { mat: 'steel', shade: 'box' });
  h.el('path', { d: 'M6 ' + (pTop + 3) + ' Q' + (w / 2) + ' ' + (pTop - 4) + ' ' + (w - 6) + ' ' + (pTop + 3), 'class': 'kit-cylinder-crown' }, moving);   // the crown
  [10, 18, 26].forEach(function (dy) { h.el('line', { x1: 6, x2: w - 6, y1: pTop + dy, y2: pTop + dy, 'class': 'kit-cylinder-ring' }, moving); });
  h.body('circle', { cx: w / 2, cy: pin, r: 4.5 }, moving, { mat: 'steel', shade: 'round' });                      // the gudgeon pin
  var eq = h.equip(g);
  h.body('rect', { x: -12, y: cov, width: 12, height: H - cov }, eq, { mat: 'cast', shade: 'box', hatch: true });
  h.body('rect', { x: w, y: cov, width: 12, height: H - cov }, eq, { mat: 'cast', shade: 'box', hatch: true });
  h.body('rect', { x: -16, y: 0, width: w + 32, height: cov, rx: 4 }, eq, { mat: 'cast', shade: 'box', hatch: true });
  h.el('line', { x1: w / 2, x2: w / 2, y1: -26, y2: cov + 2, 'class': 'kit-m-stem kit-cylinder-stem' }, eq);
  h.body('rect', { x: w / 2 - 5, y: -6, width: 10, height: 6, rx: 1 }, eq, { mat: 'cast', shade: 'box' });          // the valve guide
  h.el('path', { d: 'M' + (w / 2) + ' -7 l5 -2 l-10 -3 l10 -3 l-10 -3 l10 -3 l-5 -2', 'class': 'kit-cylinder-spring' }, eq);   // and its spring
  [12, w - 12, -8, w + 8].forEach(function (sx) { h.el('circle', { cx: sx, cy: 5, r: 2, 'class': 'kit-m-bolt' }, eq); });   // the cover's studs
  h.body('path', { d: 'M' + (w / 2 - 18) + ' ' + (cov + 6) + ' Q' + (w / 2) + ' ' + (cov - 2) + ' ' + (w / 2 + 18) + ' ' + (cov + 6) + ' Z' }, eq, { mat: 'steel' });
  [ox, gx].forEach(function (x) {                       // an injector passes through the cover by design
    h.body('rect', { x: x - 5, y: -6, width: 10, height: cov + 12, rx: 2, 'data-may-cross': '' }, eq, { mat: 'steel', shade: 'cylv' });
  });
  function fan(x, cls, ends) {
    var fg = h.el('g', { 'class': cls }, g);
    ends.forEach(function (e) { h.el('line', { x1: x, y1: top, x2: x + e[0], y2: top + e[1] }, fg); });
    return fg;
  }
  var gas = fan(gx, 'kit-cylinder-gas', [[-62, 30], [-50, 44], [-34, 52]]);
  var pilot = fan(ox, 'kit-cylinder-pilot', [[16, 14], [22, 8]]);
  var oil = fan(ox, 'kit-cylinder-oil', [[58, 30], [48, 44], [32, 52], [64, 16]]);
  /* the COMBUSTION (2.52.0): a burning plume along each jet - lifted off the nozzle, widening to a rounded tip, a white-hot
     core in it - flickering while it burns: the gas jets lit by the pilot in gas mode, the oil sprays in fuel-oil mode. It
     was a disc with rays, read as a sun (operator, 2026-10-20). Pale flame, never the alarm colours */
  /* As optical engines show it: a methane jet burns with little soot - a faint bluish flame along the jet - lit by the
     pilot diesel, which burns bright; fuel oil burns in bright, sooty plumes along its sprays */
  function plumes(x, ends, kind) {
    var pg = h.el('g', { 'class': 'kit-cylinder-fire kit-cylinder-fire-' + kind, 'data-may-cross': '' }, g), fl = h.el('g', { 'class': 'kit-cylinder-flick' }, pg);
    function tongue(e, lift, wd, cls, quiet) {
      var L = Math.sqrt(e[0] * e[0] + e[1] * e[1]), ux = e[0] / L, uy = e[1] / L, nx = -uy, ny = ux;
      var ax = x + ux * L * lift, ay = top + uy * L * lift, bx = x + e[0], by = top + e[1];
      var d = 'M' + (ax + nx).toFixed(1) + ' ' + (ay + ny).toFixed(1) + ' L' + (bx + nx * wd).toFixed(1) + ' ' + (by + ny * wd).toFixed(1) +
              ' Q' + (bx + ux * wd * 1.6).toFixed(1) + ' ' + (by + uy * wd * 1.6).toFixed(1) + ' ' + (bx - nx * wd).toFixed(1) + ' ' + (by - ny * wd).toFixed(1) +
              ' L' + (ax - nx).toFixed(1) + ' ' + (ay - ny).toFixed(1) + ' Z';
      h.el('path', { d: d, 'class': cls, 'data-low-contrast': quiet ? '' : null }, fl);
    }
    /* one flame: the first plume carries the contrast on the panel; the others, and the cores inside them, go with it */
    ends.forEach(function (e, i) { tongue(e, 0.3, 6, 'kit-cylinder-flame', i > 0); });
    ends.forEach(function (e) { tongue([e[0] * 0.85, e[1] * 0.85], 0.42, 2.2, 'kit-cylinder-core', true); });
    return pg;
  }
  var gasFire = plumes(gx, [[-62, 30], [-50, 44], [-34, 52]], 'gas');
  var pilotFire = plumes(ox, [[16, 14], [22, 8]], 'oil');
  var oilFire = plumes(ox, [[58, 30], [48, 44], [32, 52], [64, 16]], 'oil');
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
    gasFire.style.opacity = Math.min(gs, pl).toFixed(2);
    pilotFire.style.opacity = Math.min(gs, pl).toFixed(2);
    oilFire.style.opacity = oi.toFixed(2);
    g.classList.toggle('kit-cylinder-run', v > 0.05);
    g.classList.toggle('kit-cylinder-trip', v > 1.25 && v < 1.75);
    st.textContent = v < 0.05 ? 'STOPPED' : v <= 1.25 ? 'GAS MODE' : v < 1.75 ? 'GAS SUPPLY STOPPED' : 'FUEL-OIL MODE';
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M01",
  course: 'IGF Basic', module: 'M01', made: '2026-10-15',
  look: 'equipment',
  why: 'M01 s06: a dual-fuel engine cylinder in gas mode (gas jet lit by a pilot oil spray), on a gas trip, and in fuel-oil mode; M06 and M13 need it too',
  value: '0 stopped · 1 gas mode (gas jet + pilot spray) · 1.5 gas supply stopped (pilot only) · 2 fuel-oil mode (oil spray)',
  css: '.kit-cylinder-ring{stroke:var(--mat-edge);stroke-width:2}.kit-cylinder-stem{stroke-width:3}' +
    '.kit-cylinder-crown{fill:none;stroke:var(--mat-edge);stroke-width:1.5}.kit-cylinder-spring{fill:none;stroke:var(--dim-d);stroke-width:1.6;stroke-linejoin:round}' +
    '.kit-cylinder-gas line{stroke:var(--txt-d);stroke-width:3;stroke-linecap:round;stroke-dasharray:2 6}.kit-cylinder-pilot line,.kit-cylinder-oil line{stroke:var(--cold);stroke-width:2.5;stroke-dasharray:5 4}.kit-cylinder-fire{opacity:0}.kit-cylinder-flame{fill:var(--mat-flame);opacity:.92}.kit-cylinder-fire-gas .kit-cylinder-flame{fill:var(--cold);opacity:.6}.kit-cylinder-fire-gas .kit-cylinder-core{opacity:.75}.kit-light .kit-cylinder-flame{stroke:var(--mat-flame-edge);stroke-width:1.5}.kit-light .kit-cylinder-fire-gas .kit-cylinder-flame{opacity:.9}.kit-cylinder-core{fill:var(--txt-d)}.kit-cylinder-run .kit-cylinder-flick{transform-box:fill-box;transform-origin:50% 0;animation:kit-cylinder-flicker .3s ease-in-out infinite alternate}@keyframes kit-cylinder-flicker{to{transform:scale(1.05,.94)}}.kit-cylinder-run .kit-cylinder-moving{animation:kit-cylinder-stroke .9s ease-in-out infinite alternate}.kit-cylinder-run .kit-cylinder-gas line,.kit-cylinder-run .kit-cylinder-pilot line,.kit-cylinder-run .kit-cylinder-oil line{animation:kit-flow .8s linear infinite}.kit-cylinder-run .kit-state{fill:var(--txt-d)}.kit-cylinder-trip .kit-state{fill:var(--warn-d)}@keyframes kit-cylinder-stroke{to{transform:translateY(34px)}}',
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
  /* 2.52.0: the insulation in its foam, the inner tank's steel wall cut through, the LNG pale at its surface (no shadow:
     the bubbles move inside it for as long as it boils, and a shadow would be drawn again on every frame) */
  var eq = h.equip(g, { shadow: false });
  h.body('rect', { width: w, height: ht, rx: ht / 2, 'class': 'kit-boil-off-ins' }, eq, { mat: 'foam', shade: 'cyl' });
  h.el('rect', { width: w, height: ht, rx: ht / 2, 'class': 'kit-boil-off-wall kit-boil-off-jacket kit-ms-steel' }, eq);   // the outer steel jacket over the insulation
  h.el('rect', { x: ins, y: ins, width: iw, height: ih, rx: r }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var ves = h.el('rect', { x: ins, y: ins, width: iw, height: ih, rx: r, 'class': 'kit-vessel' }, eq);
  var inside = h.el('g', { 'clip-path': 'url(#' + cid + ')' }, eq);
  h.el('rect', { x: ins, y: sy, width: iw, height: ins + ih - sy, 'class': 'kit-liquid kit-m-lng' }, inside);
  h.el('line', { x1: ins, x2: ins + iw, y1: sy, y2: sy, 'class': 'kit-surface kit-m-lngs' }, inside);
  h.el('rect', { x: ins, y: ins, width: iw, height: ih, rx: r, 'class': 'kit-boil-off-wall kit-ms-steel' }, eq);   // the inner tank's wall
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
  look: 'equipment',
  why: 'M01 s07: heat leaks through the insulation into a cold LNG tank and some of the liquid boils off as vapour',
  value: 'how much heat leaks in and boils the liquid, 0..1 (arrows and rising bubbles)',
  css: '.kit-boil-off-wall{fill:none;stroke-width:5}.kit-boil-off-jacket{stroke-width:3}.kit-boil-off-bubbles circle{fill:none;stroke:var(--deep);stroke-width:2}.kit-light .kit-boil-off-bubbles circle{stroke:var(--txt-d)}.kit-boil-off-heat path{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.kit-boil-off-on .kit-boil-off-bubbles circle{animation:kit-boil-off-rise 1.6s ease-in infinite}.kit-boil-off-on .kit-boil-off-heat g path{animation:kit-boil-off-in 1.2s ease-in-out infinite alternate}@keyframes kit-boil-off-rise{to{transform:translateY(var(--rise,-60px))}}@keyframes kit-boil-off-in{to{transform:translateX(6px)}}',
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
  /* a zone laid over a tank sits on its light cladding (2.52.0): it takes the deep inks a light surface needs */
  var zx = p.x || 0, zy = p.y || 0;                 // only a zone that lies on the tank: one bigger than it is over the hull
  if ((fig.spec.parts || []).some(function (q) { return q.type === 'tank' && zx >= (q.x || 0) - 4 && zx + w <= (q.x || 0) + (q.w || 190) + 4 && zy >= (q.y || 0) - 4 && zy + ht <= (q.y || 0) + (q.h || 110) + 4; })) {
    g.classList.add('kit-zone-onlight');
  }
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
  look: 'diagram',
  why: 'M02 s12: hazardous zones 0, 1 and 2 growing around tanks, spaces and openings on an IGF ship',
  value: 'how far the zone has grown from its origin, 0..1',
  css: '.kit-zone-area{stroke-width:2;stroke-dasharray:6 4}.kit-zone-z0{fill:var(--warn-d);fill-opacity:.38;stroke:var(--warn-d)}.kit-zone-z1{fill:var(--amber);fill-opacity:.3;stroke:var(--amber)}.kit-zone-z2{fill:var(--amber);fill-opacity:.1;stroke:var(--amber);stroke-dasharray:2 4}' +
    '.kit-zone-onlight .kit-zone-z0{stroke:var(--mat-trip-deep)}.kit-zone-onlight .kit-zone-z1,.kit-zone-onlight .kit-zone-z2{stroke:var(--amber-ink)}',
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
  look: 'diagram',
  why: 'M02 s11: zones 0, 1 and 2 told apart by how often and how long gas is present; the start of the Charts family M04 and M06 need',
  value: '0..number of rows - row k sweeps its time line while the value goes from k to k+1; its clock fills with the share of time gas is there',
  css: '.kit-bands-chip{fill:var(--deep);stroke:var(--faint-d);stroke-width:2}.kit-bands-track{fill:var(--deep);stroke:var(--faint-d);stroke-width:1.5}.kit-bands-gas{fill:var(--txt-d);opacity:.55}.kit-bands-cursor{stroke:var(--txt-d);stroke-width:2}.kit-bands-clock{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}.kit-bands-pie{fill:var(--dim-d)}.kit-bands-z0 .kit-bands-chip{stroke:var(--warn-d)}.kit-bands-z0 .kit-bands-gas,.kit-bands-z0 .kit-bands-pie{fill:var(--warn-d);opacity:.9}.kit-bands-z1 .kit-bands-chip{stroke:var(--amber)}.kit-bands-z1 .kit-bands-gas,.kit-bands-z1 .kit-bands-pie{fill:var(--amber);opacity:1}.kit-bands-z2 .kit-bands-chip{stroke:var(--amber);stroke-dasharray:4 3}.kit-bands-z2 .kit-bands-gas,.kit-bands-z2 .kit-bands-pie{fill:var(--amber);opacity:.6}',
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
                 'data-veil': '',                                                            // over shapes, never over words (2.63.2)
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
  look: 'diagram',
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
  /* 2.52.0: the hull's painted steel - the tank's walls and the bottom plate - round the void of the cofferdam */
  var eq = h.equip(g, { shadow: false });
  h.el('rect', { width: w, height: ht, rx: 3, 'class': 'kit-integral-tank-cd' }, eq);
  h.el('rect', { x: tx, y: ty, width: tw, height: th }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var ves = h.el('rect', { x: tx, y: ty, width: tw, height: th, 'class': 'kit-vessel' }, eq);
  var liq = h.el('rect', { x: tx, width: tw, 'class': 'kit-liquid', 'clip-path': 'url(#' + cid + ')' }, eq);
  var surf = h.el('line', { x1: tx, x2: tx + tw, 'class': 'kit-surface', 'clip-path': 'url(#' + cid + ')' }, eq);
  h.el('rect', { x: tx, y: ty, width: tw, height: th, 'class': 'kit-integral-tank-wall kit-ms-cast' }, eq);
  h.body('rect', { x: -10, y: ht, width: w + 20, height: 8 }, eq, { mat: 'deck', shade: 'box' });
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
  look: 'equipment',
  why: 'M02 s05: the methanol path starts in an integral fuel tank - part of the hull, surrounded by a cofferdam',
  value: 'liquid level 0..1',
  css: '.kit-integral-tank-cd{fill:var(--deep);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:5 4}' +   // the cofferdam: a void
    '.kit-integral-tank-wall{fill:none;stroke-width:5;stroke-linejoin:round}',
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
  var walls = h.equip(g, { shadow: false });
  [[0, 0, bx - t, t], [bx + bw + t, 0, w - bx - bw - t, t], [0, D - t, w, t], [0, yi, w, t], [0, D - yi - t, w, t],
   [bx - t, -bh, t, bh + t], [bx + bw, -bh, t, bh + t], [w - t, t, t, an], [w - t, D - yi, t, an]].forEach(function (r) {
    h.body('rect', { x: r[0], y: r[1], width: r[2], height: r[3] }, walls, { mat: 'steel', hatch: true });     // the pipes' steel, cut through (2.52.0)
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
  look: 'equipment',
  why: 'M03 s02: a cut along a double-walled gas pipe - gas in the inner pipe, air drawn through the annular space to an outlet; a leak stays in the annular space and is carried out',
  value: '0 still · 1 gas flowing and the annular space ventilated · 1..2 a leak from the inner pipe spreads along the annular space and up the outlet',
  css: '.kit-pipe-section-bore{fill:var(--txt-d);opacity:.08}.kit-pipe-section-gas{fill:var(--txt-d);fill-opacity:.4;stroke:var(--txt-d);stroke-width:1.5}.kit-pipe-section-air path{fill:none;stroke:var(--cold);stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.kit-pipe-section-crack{fill:none;stroke:var(--mat-window);stroke-width:3}.kit-pipe-section-on .kit-pipe-section-ax{animation:kit-pipe-section-x 1.1s linear infinite}.kit-pipe-section-on .kit-pipe-section-ay{animation:kit-pipe-section-y .9s linear infinite}@keyframes kit-pipe-section-x{to{transform:translateX(40px)}}@keyframes kit-pipe-section-y{to{transform:translateY(-28px)}}',
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
  /* 2.52.0 (operator: "make this relief valve look better"): a real spring-loaded safety valve - a rounded cast angle body
     on its inlet neck and outlet neck, both flanged; a cut-away window in the body showing the disc on its seat; the open
     bonnet (two cast yoke bars on the bonnet flange) where its steel coil spring is seen pressing the disc down; the
     spindle up through the top plate, the adjusting cap, and the lifting lever */
  var eq = h.equip(sym), wy = -k + 1;
  h.flange(eq, 0, s + 5, 90, 2 * k + 10, 5);
  h.flange(eq, s + 5, 0, 0, 2 * k + 10, 5);
  h.body('rect', { x: -k * 0.75, y: 0, width: 1.5 * k, height: s + 3 }, eq, { mat: 'cast', shade: 'cylv' });       // the inlet neck
  h.body('rect', { x: 0, y: -k * 0.75, width: s + 3, height: 1.5 * k }, eq, { mat: 'cast', shade: 'cyl' });        // the outlet neck
  h.body('ellipse', { rx: k + 4, ry: k + 3 }, eq, { mat: 'cast', shade: 'round' });                                // the body
  h.el('rect', { x: -k + 1.5, y: wy, width: 2 * k - 3, height: 4 - wy, rx: 2, 'class': 'kit-relief-valve-win' }, eq);   // the cut-away window
  h.body('rect', { x: -6, y: 0, width: 12, height: 3, rx: 0.8 }, eq, { mat: 'steel' });                            // the seat on the inlet nozzle
  [-1, 1].forEach(function (sd) {                                                                                   // the yoke bars
    h.body('rect', { x: sd < 0 ? -k - 1 : k - 2, y: top, width: 3, height: -k - 4 - top }, eq, { mat: 'cast', shade: 'cylv' });
  });
  h.body('rect', { x: -k - 2.5, y: -k - 6, width: 2 * k + 5, height: 3.5, rx: 1 }, eq, { mat: 'steel', shade: 'box' });   // the bonnet flange
  h.body('rect', { x: -k - 3, y: top - 3, width: 2 * k + 6, height: 4, rx: 1 }, eq, { mat: 'steel', shade: 'box' });     // the top plate
  h.body('rect', { x: -3, y: top - 9, width: 6, height: 6, rx: 1 }, eq, { mat: 'cast', shade: 'box' });          // the adjusting screw's cap
  h.body('rect', { x: -4.5, y: top - 11, width: 9, height: 3, rx: 1 }, eq, { mat: 'steel' });
  h.el('path', { d: 'M-3 ' + (top - 6) + ' L' + (-k - 10) + ' ' + (top + 4), 'class': 'kit-m-stem kit-relief-valve-lever' }, eq);   // the lifting lever
  h.body('circle', { cx: -k - 10, cy: top + 4, r: 2.4 }, eq, { mat: 'cast', shade: 'round' });
  var spindle = h.el('line', { x1: 0, x2: 0, y2: top - 6, 'class': 'kit-m-stem kit-relief-valve-spindle' }, sym);
  var spring = h.el('path', { 'class': 'kit-relief-valve-spring' }, sym);
  var disc = h.el('rect', { x: -7, width: 14, height: 4, rx: 1.5, 'class': 'kit-relief-valve-disc' }, sym);
  var right = p.labelAt === 'right', lx = right ? s + 14 : 0, ly = right ? top + 10 : s + 22, anchor = right ? 'start' : 'middle';
  var lg = p.label || p.state !== false ? h.label(fig, g, {}, '') : null;           // its name and its state move together
  var nl = p.label ? h.lines(lg, { x: lx, y: ly, 'text-anchor': anchor, 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state === false ? null : h.el('text', { x: lx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': anchor, 'class': 'kit-state' }, lg);
  part.render = function (v) {
    /* the disc lifts off its seat into the window; the coil spring between the disc's washer and the top plate is squeezed */
    var lift = h.clamp(v, 0, 1), dy = -4 - lift * 4.5, b0 = dy - 1, n = 9, seg = (top - b0) / n, d = 'M-6 ' + b0.toFixed(1) + ' H6';
    for (var i = 1; i <= n; i++) d += ' L' + (i % 2 ? -6 : 6) + ' ' + (b0 + seg * i).toFixed(1);
    spring.setAttribute('d', d);
    disc.setAttribute('y', (dy).toFixed(1));
    spindle.setAttribute('y1', dy.toFixed(1));
    if (st) st.textContent = lift > 0.1 ? 'RELIEVING' : 'CLOSED';
    g.classList.toggle('kit-relief-valve-lift', lift > 0.1);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  look: 'equipment',
  why: 'M03 s03 and s09: a spring-loaded relief valve - the spring holds the disc on its seat until the pressure beats it, then the disc lifts and the vapour goes to the vent',
  value: 'how far the disc has lifted, 0 closed .. 1 fully open; inlet at (0, size) below, outlet at (size, 0) to the side',
  css: '.kit-relief-valve-win{fill:var(--mat-hole);stroke:var(--mat-edge);stroke-width:1}.kit-relief-valve-lever{stroke-width:2.4}.kit-relief-valve-spindle{stroke-width:2}' +
    '.kit-relief-valve-spring{fill:none;stroke:var(--kit-steel);stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round}.kit-light .kit-relief-valve-spring{stroke:var(--dim-d)}' +
    '.kit-relief-valve-disc{fill:var(--mat-stem);stroke:var(--txt-d);stroke-width:1.5}.kit-relief-valve-lift .kit-relief-valve-spring{stroke:var(--amber)}.kit-relief-valve-lift .kit-state{fill:var(--amber)}',
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
  var rails = [], discs = [];
  for (var k = 0; !box && k < n - 1; k++) {           // the rail runs between the circles, never under a number
    var a0 = gap * k + 20, a1 = gap * (k + 1) - 20;
    rails.push(h.el('line', vert ? { x1: 0, x2: 0, y1: a0, y2: a1, 'class': 'kit-step-track-rail' }
                                 : { x1: a0, x2: a1, y1: 0, y2: 0, 'class': 'kit-step-track-rail' }, g));
  }
  var made = steps.map(function (label, i) {
    var sg = h.el('g', { transform: 'translate(' + (vert ? 0 : gap * i) + ' ' + (vert ? gap * i : 0) + ')', 'class': 'kit-step-track-step' }, g);
    if (box) h.el('rect', { x: -10, y: -10, width: 20, height: 20, rx: 4, 'class': 'kit-badge-o' }, sg);
    else {
      discs.push([h.el('circle', { r: 17, 'class': 'kit-badge-o' }, sg),              /* room for a digit at 0.8x (audit_drawing) */
                  h.el('circle', { r: 17, 'class': 'kit-badge' }, sg),
                  h.el('text', { y: 5, 'text-anchor': 'middle', 'class': 'kit-badge-t' }, sg, String(i + 1))]);
    }
    h.el('path', { d: 'M-6 0 L-2 5 L7 -6', 'class': 'kit-step-track-tick' }, sg);
    var lt = h.label(fig, sg, vert ? { x: 24, y: 5, 'class': 'kit-cap' } : { x: 0, y: 34, 'text-anchor': 'middle', 'class': 'kit-cap' }, label,
                     { near: 22, lead: false }).querySelector('text');      // two long neighbours step apart, never far from their number
    if (lt) discs.length && (discs[discs.length - 1][3] = lt);
    return sg;
  });
  /* 2.63.0 - the disc grows with its digit (the 12.5 px floor, k), as the badge part's does - but never into its
     neighbour - and the rail and the step's words keep clear of it: at r 17 a digit grown 1.5-1.8x touched its ring
     (IGF M11 s04: 33 text-zone findings) */
  if (!box) {
    fig.fit(function (k) {
      var r = Math.max(17, Math.min(17 * k, gap / 2 - 3));
      discs.forEach(function (d) {
        d[0].setAttribute('r', r.toFixed(1)); d[1].setAttribute('r', r.toFixed(1)); d[2].setAttribute('y', (5 * k).toFixed(1));
        if (d[3] && vert) {               // its rows carry their own x (lines())
          [d[3]].concat([].slice.call(d[3].querySelectorAll('tspan[x]'))).forEach(function (t) { t.setAttribute('x', (r + 7).toFixed(1)); });
        } else if (d[3]) d[3].setAttribute('y', (r + 17).toFixed(1));
      });
      rails.forEach(function (ln, j) {
        ln.setAttribute(vert ? 'y1' : 'x1', (gap * j + r + 3).toFixed(1));
        ln.setAttribute(vert ? 'y2' : 'x2', (gap * (j + 1) - r - 3).toFixed(1));
      });
    });
  }
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
  look: 'diagram',
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
  /* 2.52.0: two stainless halves, each bolted to its line by a flange, with the collar that locks them */
  var eq = h.equip(sym), L = h.el('g', {}, eq), R = h.el('g', {}, eq);
  h.flange(L, -21, 0, 0, 30, 5);
  h.flange(R, 21, 0, 0, 30, 5);
  h.body('rect', { x: -20, y: -11, width: 18, height: 22, rx: 3 }, L, { mat: 'steel', shade: 'cyl' });
  h.body('rect', { x: 2, y: -11, width: 18, height: 22, rx: 3 }, R, { mat: 'steel', shade: 'cyl' });
  h.body('rect', { x: -12, y: -13, width: 6, height: 26, rx: 1.5 }, L, { mat: 'cast', shade: 'box' });
  h.body('rect', { x: 6, y: -13, width: 6, height: 26, rx: 1.5 }, R, { mat: 'cast', shade: 'box' });
  var seals = [h.el('rect', { x: -6, y: -8, width: 3, height: 16, 'class': 'kit-coupling-seal' }, L),
               h.el('rect', { x: 3, y: -8, width: 3, height: 16, 'class': 'kit-coupling-seal' }, R)];
  var mark = brk ? h.el('line', { x1: 0, x2: 0, y1: -16, y2: 16, 'class': 'kit-coupling-break' }, sym) : null;
  /* a breakaway coupling is held by shear bolts across its joint (2.52.0): pulled hard, they break and it parts */
  var shear = brk ? h.el('g', {}, sym) : null;
  if (shear) [-8, 0, 8].forEach(function (y) { h.body('rect', { x: -4, y: y - 1.3, width: 8, height: 2.6, rx: 1 }, shear, { mat: 'steel' }); });
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
    if (shear) shear.style.opacity = c > 0.5 ? '1' : '0';
    if (st) st.textContent = c > 0.5 ? 'CONNECTED' : (brk ? 'PARTED - SEALED' : 'DISCONNECTED');
    g.classList.toggle('kit-coupling-parted', c < 0.5);
  };
}, {
  family: 'piping',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  look: 'equipment',
  why: 'M03 s13 and s15: the dry-disconnect coupling and the breakaway coupling at the bunkering station - when they part, both halves are sealed',
  value: '1 connected, 0 parted (each half shows its closed face); kind "dry" or "breakaway"',
  css: '.kit-coupling-seal{fill:var(--mat-plate);stroke:var(--mat-ink);stroke-width:1}.kit-coupling-break{stroke:var(--dim-d);stroke-width:2;stroke-dasharray:3 3}',
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
  /* 2.52.0: a stainless pan (its walls 3 thick) on its insulating strip, the liquid it caught inside it */
  var eq = h.equip(g);
  h.body('rect', { x: 6, y: d + 3, width: w - 12, height: 8, rx: 2, 'class': 'kit-drip-tray-ins' }, eq, { mat: 'foam' });
  h.el('rect', { x: 3, y: 0, width: w - 6, height: d - 3 }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var pool = h.el('rect', { x: 3, width: w - 6, 'class': 'kit-pool', 'clip-path': 'url(#' + cid + ')' }, g);
  h.body('path', { d: 'M-1.5 -1 V' + (d + 1.5) + ' H' + (w + 1.5) + ' V-1 H' + (w - 1.5) + ' V' + (d - 1.5) + ' H1.5 V-1 Z' }, eq, { mat: 'steel', shade: 'box' });
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
  look: 'equipment',
  why: 'M03 s16: a stainless steel drip tray, insulated from the deck, catches LNG leaking from a flange at the bunker manifold',
  value: 'how full the tray is, 0..1 (drops fall while it fills); labelAt: below (default) | above | left | right',
  css: '.kit-drip-tray-ins{stroke-dasharray:4 3}',
  example: { size: [300, 160], parts: [
    { id: 'D', type: 'drip_tray', x: 70, y: 70, w: 160, drip: 50, label: 'drip tray' } ],
    steps: [ { title: 'A spill is caught', play: [['D', 1, 2500]] } ] }
});
/* end kit-part */
/* kit-part: water_curtain */
KIT.define('water_curtain', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 36, ht = p.h || 120, n = Math.max(3, Math.round(w / 9));
  var sheet = h.el('g', { 'class': 'kit-water-curtain-sheet' }, g);
  /* 2.52.0: the water comes from a spray header across the top, a nozzle over each stream */
  var eq = h.equip(g);
  h.body('rect', { x: -6, y: -10, width: w + 12, height: 7, rx: 3.5 }, eq, { mat: 'steel', shade: 'cyl' });
  for (var j = 0; j < n; j++) h.body('rect', { x: (j + 0.5) * w / n - 1.8, y: -3.5, width: 3.6, height: 3.5 }, eq, { mat: 'cast' });
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
  look: 'equipment',
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
  /* 2.52.0: a fixed gas detector as fitted (Honeywell Sensepoint-like): a flameproof cast junction box on its bracket, its
     cover screws, its tag on a nameplate, a cable gland at its side, the sensor head with its weather guard hanging
     below, and the alarm lamp on its corner (amber in alarm, red at trip). Box and sensor together are centred on
     (x, y) and kept near the old r footprint: a detector is put near a deckhead or a deck, and must stay inside its room */
  var eq = h.equip(g), top = -12;                    // set in fit
  var gland = h.body('path', { d: '' }, eq, { mat: 'steel', shade: 'box' });
  var head = h.body('rect', { x: -r + 2, y: top, width: 2 * r - 4, height: 22, rx: 3, 'class': 'kit-detector-head' }, eq, { mat: 'cast', shade: 'box' });
  var screws = [0, 1, 2, 3].map(function () { return h.el('circle', { r: 1.3, 'class': 'kit-m-bolt' }, eq); });
  var sensor = h.body('rect', { x: -6, width: 12, height: 8 }, eq, { mat: 'steel', shade: 'cylv' });
  var guard = h.body('rect', { x: -7.5, width: 15, height: 4.5, rx: 1.5 }, eq, { mat: 'cast', shade: 'box' });
  var slits = h.el('path', { 'class': 'kit-detector-slit' }, eq);
  var lamp = h.el('circle', { r: 2.6, 'class': 'kit-detector-lamp' }, eq);
  var plate = h.el('rect', { rx: 2, 'class': 'kit-detector-plate' }, g);
  var tag = h.el('text', { y: 4.5, 'text-anchor': 'middle', 'class': 'kit-bubble-t' }, g, p.tag || 'GD');
  var pos = { right: { x: r + 8, y: 4.5, a: 'start' }, left: { x: -r - 8, y: 4.5, a: 'end' }, below: { x: 0, y: r + 20, a: 'middle' } }[at] || { x: r + 8, y: 4.5, a: 'start' };
  /* the reading is a label: the layout keeps it clear of the equipment drawn round the detector */
  var val = p.readout === false ? null : h.el('text', { x: pos.x, y: pos.y, 'text-anchor': pos.a, 'class': 'kit-state' }, h.label(fig, g, {}, '', { near: 20 }));
  fig.fit(function (k) {                          // the box grows with its tag (the 12.5 px floor), the reading beside it
    var tw = h.widest(tag, [p.tag || 'GD']), pw = tw + 10, ph = 22 * k, bw = Math.max(2 * r - 4, pw + 10), bh = Math.max(26, ph + 6);
    top = -(bh + 12) / 2;                         // box, sensor (8) and guard (4) centred on the part's point
    var x0 = -bw / 2, mid = top + bh / 2, bot = top + bh, sb = bot + 8;
    h.reshape(head, { x: x0, y: top, width: bw, height: bh });
    [[x0 + 3, top + 3], [-x0 - 3, top + 3], [x0 + 3, bot - 3], [-x0 - 3, bot - 3]].forEach(function (c, i) { screws[i].setAttribute('cx', c[0]); screws[i].setAttribute('cy', c[1]); });
    plate.setAttribute('x', -pw / 2); plate.setAttribute('width', pw); plate.setAttribute('y', mid - ph / 2); plate.setAttribute('height', ph);
    tag.setAttribute('y', mid + 4.5 * k);
    h.reshape(gland, { d: 'M' + (x0 - 6) + ' ' + (mid - 3.5) + ' H' + x0 + ' V' + (mid + 3.5) + ' H' + (x0 - 6) + ' L' + (x0 - 7.5) + ' ' + mid + ' Z' });
    h.reshape(sensor, { y: bot }); h.reshape(guard, { y: sb });
    slits.setAttribute('d', 'M-4 ' + (sb + 1) + ' V' + (sb + 3.5) + ' M0 ' + (sb + 1) + ' V' + (sb + 3.5) + ' M4 ' + (sb + 1) + ' V' + (sb + 3.5));
    lamp.setAttribute('cx', -x0 + 3); lamp.setAttribute('cy', top + 4);           // on the box's side, clear of its tag
    if (val) {
      val.setAttribute('x', at === 'below' ? 0 : (at === 'left' ? -1 : 1) * (bw / 2 + (at === 'left' ? 16 : 8)));
      val.setAttribute('y', at === 'below' ? sb + 4.5 + 16 * k : mid + 4.5 * k);
    }
  });
  if (p.label) h.label(fig, g, { x: 0, y: at === 'below' ? r + 56 : r + 36, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);   // under the sensor head
  part.render = function (v) { if (val) val.textContent = h.fmt(v, p); };
  part.flag = function (m, on) { g.classList.toggle('kit-on-' + m.kind, on); };
}, {
  family: 'instruments',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  look: 'equipment',
  why: 'M03 s17: a fixed gas detector head placed in a space - where it sits is the lesson; it reads % LEL and alarms on its marks',
  value: 'the reading (for gas: % LEL); its marks turn it amber (alarm) or red (trip)',
  css: '.kit-detector-plate{fill:var(--deep);stroke:var(--mat-edge-steel);stroke-width:1}.kit-detector-slit{fill:none;stroke:var(--mat-window);stroke-width:1.2}' +
    '.kit-detector-lamp{fill:var(--mat-stem);stroke:var(--mat-edge);stroke-width:.8}' +
    '.kit-on-alarm .kit-detector-head{stroke:var(--amber);stroke-width:3}.kit-on-alarm .kit-detector-lamp{fill:var(--amber)}.kit-on-alarm .kit-state{fill:var(--amber)}' +
    '.kit-on-trip .kit-detector-head{stroke:var(--warn-d);stroke-width:3}.kit-on-trip .kit-detector-lamp{fill:var(--warn-d)}.kit-on-trip .kit-state{fill:var(--warn-d)}',
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
  /* 2.52.0: a real flame is never a symmetric candle - its tip leans and curls (lean), smaller tongues burn behind it, and
     the gas burns blue where it leaves the outlet */
  function tongue(k, dx, lean) {
    var t = (dx || 0) + (lean || 0) * s * k;
    return 'M' + (dx || 0) + ' 0 C' + ((dx || 0) - s * 0.45 * k) + ' ' + (-s * 0.22 * k) + ' ' + (t - s * 0.42 * k) + ' ' + (-s * 0.62 * k) + ' ' + t + ' ' + (-s * k) +
           ' C' + (t + s * 0.18 * k) + ' ' + (-s * 0.72 * k) + ' ' + ((dx || 0) + s * 0.48 * k) + ' ' + (-s * 0.24 * k) + ' ' + (dx || 0) + ' 0 Z';
  }
  var grow = h.el('g', {}, g), body = h.el('g', { 'class': 'kit-flame-body' }, grow);
  /* a flame stands on a tank, a room's roof or a vent and burns up past it by its nature: it is not judged as poking out of
     what it stands on, and it holds nothing (2.49.1) */
  h.el('path', { d: tongue(0.62, -s * 0.24, -0.16), 'class': 'kit-flame-outer kit-m-fire', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, body);   // behind the main tongue: it carries the contrast
  h.el('path', { d: tongue(0.5, s * 0.26, 0.2), 'class': 'kit-flame-outer kit-m-fire', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, body);
  h.el('path', { d: tongue(1, 0, 0.12), 'class': 'kit-flame-outer kit-m-fire', 'data-may-cross': '', 'data-no-contain': '' }, body);
  h.el('path', { d: tongue(0.55, 0, 0.06), 'class': 'kit-flame-core', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, body);   // the hot core inside the flame: its outer tongue carries the contrast
  h.el('ellipse', { cx: 0, cy: -s * 0.04, rx: s * 0.2, ry: s * 0.08, 'class': 'kit-flame-root', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, body);
  var lb = p.label ? h.label(fig, g, { x: s * 0.6, y: -s * 0.6, 'class': 'kit-cap' }, p.label) : null;
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    grow.setAttribute('transform', 'scale(' + Math.max(k, 0.001).toFixed(3) + ')');
    grow.style.opacity = k > 0.02 ? '1' : '0';
    h.gone(lb, k <= 0.02);
    g.classList.toggle('kit-flame-on', k > 0.05);
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M03",
  course: 'IGF Basic', module: 'M03', made: '2026-10-15',
  look: 'diagram',
  why: 'M03 s11: venting gas has caught fire at the vent mast outlet - the flame stands while gas is released and goes out when the release stops and nitrogen smothers it; M13 needs it too',
  value: 'the size of the flame, 0 out .. 1 full; it stands on its point (x, y) and burns upwards',
  css: '.kit-flame-outer{opacity:.95}.kit-flame-core{fill:var(--mat-fire-hot);opacity:.85}.kit-flame-root{fill:var(--mat-fire-root);opacity:.65}.kit-flame-on .kit-flame-body{transform-box:fill-box;transform-origin:50% 100%;animation:kit-flame-flicker .35s ease-in-out infinite alternate}@keyframes kit-flame-flicker{to{transform:scale(1.07,.9)}}',
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
  /* 2.66.0 - yaxis.log: true - a vapour-pressure chart over decades (0.1 ... 100 bar) reads on a log scale; the ticks are
     the decades (yaxis.ticks to choose others), and between its points a curve runs straight on the log scale */
  var ylog = !!Y.log && Y.min > 0 && Y.max > Y.min;
  var L0 = ylog ? Math.log(Y.min) / Math.LN10 : 0, L1 = ylog ? Math.log(Y.max) / Math.LN10 : 1;
  function sx(v) { return (v - X.min) / (X.max - X.min) * w; }
  function sy(v) {
    if (ylog) return ht - (Math.log(Math.max(v, Y.min / 1000)) / Math.LN10 - L0) / (L1 - L0) * ht;
    return ht - (v - Y.min) / (Y.max - Y.min) * ht;
  }
  var axes = h.el('g', { 'class': 'kit-curve-chart-axes' }, g);
  for (var xv = X.min; xv <= X.max + 1e-9; xv += X.every) {
    h.el('line', { x1: sx(xv), y1: 0, x2: sx(xv), y2: ht, 'class': 'kit-curve-chart-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, axes);
    h.el('text', { x: sx(xv), y: ht + 18, 'text-anchor': 'middle', 'class': 'kit-tick' }, axes, String(xv).replace('-', '−'));
  }
  var yticks = Y.ticks || [];
  if (!Y.ticks && ylog) for (var e = Math.ceil(L0 - 1e-9); e <= L1 + 1e-9; e++) yticks.push(Math.pow(10, e));
  if (!Y.ticks && !ylog) for (var yv = Y.min; yv <= Y.max + 1e-9; yv += Y.every) yticks.push(yv);
  yticks.forEach(function (yv) {
    h.el('line', { x1: 0, y1: sy(yv), x2: w, y2: sy(yv), 'class': 'kit-curve-chart-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, axes);
    h.el('text', { x: -12, y: sy(yv) + 4, 'text-anchor': 'end', 'class': 'kit-tick' }, axes, String(+yv.toPrecision(6)));
  });
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
      /* 2.67.0 - a label the layout keeps clear: a point read at a curve's last value sat on its name (the studio, gas M02) */
      lab = h.label(fig, cg, { x: sx(at[0]), y: sy(at[1]), 'text-anchor': c.anchor || 'start', 'class': 'kit-cap' }, c.label, { near: 24, lead: false });
    }
    if (c.bp) {
      var bl = h.el('text', { x: sx(first[0]) + (c.bpDx || 0), y: sy(first[1]) + (c.bpDy != null ? c.bpDy : 22), 'text-anchor': 'middle', 'class': 'kit-num' }, cg, c.bp);
      lab = lab || bl; c._bp = bl;
    }
    var len = 0; try { len = path.getTotalLength(); } catch (e2) { len = 0; }
    return { path: path, dot: dot, lab: lab, bpl: c._bp, len: len || 1000, g: cg, k: 0 };
  });
  function along(c, xv) {                              // the curve's value at xv, straight between its points (on a log scale: in log)
    var q = curves[c].pts, f;
    if (xv <= q[0][0]) return q[0][1];
    for (var k = 1; k < q.length; k++) if (xv <= q[k][0]) {
      f = (xv - q[k - 1][0]) / (q[k][0] - q[k - 1][0]);
      if (ylog && q[k - 1][1] > 0 && q[k][1] > 0) return Math.exp(Math.log(q[k - 1][1]) + f * (Math.log(q[k][1]) - Math.log(q[k - 1][1])));
      return q[k - 1][1] + f * (q[k][1] - q[k - 1][1]);
    }
    return q[q.length - 1][1];
  }
  /* the point: one, sliding along point.curve; or, with point.curve "all", a line across the chart that reads every curve
     drawn so far. 2.66.0 - point.drag: true - a trainee drags it along the temperature axis (finger, mouse, arrow keys) and
     reads the value live; a step that moves the figure's value puts it back where the steps say */
  var all = pt && pt.curve === 'all', mark = null, gv, gh, pd, pl, dots = [];
  var dx = pt ? (pt.decimals != null ? pt.decimals : 1) : 1;
  if (pt) {
    mark = h.el('g', { 'class': 'kit-curve-chart-point' }, g);
    gv = h.el('line', { 'class': 'kit-curve-chart-guide', 'data-may-cross': '' }, mark);
    if (!all) {
      gh = h.el('line', { 'class': 'kit-curve-chart-guide', 'data-may-cross': '' }, mark);
      pd = h.el('circle', { r: 7, 'class': 'kit-curve-chart-pdot' }, mark);
    } else {
      /* every curve's reading beside its own dot, the temperature over the line: each a label the layout places
         (one line of every reading across the top printed over the axis numbers - the studio, 2.66.0) */
      dots = curves.map(function () { return h.el('circle', { r: 6, 'class': 'kit-curve-chart-pdot' }, mark); });
      dots.forEach(function (d) { d._t = h.el('text', { 'class': 'kit-num', 'text-anchor': 'start' }, h.label(fig, mark, {}, '', { near: 30, lead: false })); });
    }
    pl = h.el('text', { 'class': 'kit-num', 'text-anchor': 'start' }, h.label(fig, mark, {}, '', { near: 30, lead: false }));   // the layout keeps the reading off the curves
  }
  /* where the point may go: its curve's own points (every curve's, for "all") - never read past a curve's data */
  var span = pt ? (all ? curves : [curves[pt.curve]]).filter(Boolean) : [];
  var lo = pt ? (pt.min != null ? pt.min : Math.max(X.min, Math.min.apply(null, span.map(function (c) { return c.pts[0][0]; })))) : 0;
  var hi = pt ? (pt.max != null ? pt.max : Math.min(X.max, Math.max.apply(null, span.map(function (c) { return c.pts[c.pts.length - 1][0]; })))) : 0;
  function covers(i, xv) { var q = curves[i].pts; return xv >= q[0][0] - 1e-9 && xv <= q[q.length - 1][0] + 1e-9; }
  function reading(xv) {
    var xs = h.fmt(xv, { decimals: pt.xdecimals || 0, unit: X.unit });
    if (!all) return xs + ' · ' + h.fmt(along(pt.curve, xv), { decimals: dx, unit: Y.unit });
    return xs;
  }
  function place(xv, show, live) {
    xv = h.clamp(xv, Math.min(lo, hi), Math.max(lo, hi));
    mark.style.opacity = show > 0.001 ? '1' : '0';
    var x = sx(xv), yTop = ht;
    if (!all) {
      var y = sy(along(pt.curve, xv));
      gv.setAttribute('x1', x); gv.setAttribute('x2', x); gv.setAttribute('y1', y); gv.setAttribute('y2', ht);
      gh.setAttribute('x1', 0); gh.setAttribute('x2', x); gh.setAttribute('y1', y); gh.setAttribute('y2', y);
      pd.setAttribute('cx', x); pd.setAttribute('cy', y);
      yTop = y;
    } else {
      gv.setAttribute('x1', x); gv.setAttribute('x2', x); gv.setAttribute('y1', 0); gv.setAttribute('y2', ht);
      var side = pt.labelSide === 'left' || (pt.labelSide == null && x > w * 0.62);
      dots.forEach(function (d, i) {
        var y2 = sy(along(i, xv)), on = drawn[i].k > 0.95 && covers(i, xv), c = curves[i];
        d.setAttribute('cx', x); d.setAttribute('cy', y2);
        d.style.opacity = on ? '1' : '0';
        d._t.setAttribute('text-anchor', side ? 'end' : 'start');
        d._t.setAttribute('x', side ? x - 12 : x + 12); d._t.setAttribute('y', y2 + 5);
        d._t.textContent = on && (live || show > 0.97) ? (c.label ? c.label + ' ' : '') + h.fmt(along(i, xv), { decimals: dx, unit: Y.unit }) : '';
      });
    }
    var left = pt.labelSide === 'left' || (pt.labelSide == null && x > w * 0.62);
    pl.setAttribute('text-anchor', all ? 'middle' : left ? 'end' : 'start');
    pl.setAttribute('x', all ? x : left ? x - 14 : x + 12); pl.setAttribute('y', all ? -10 : (left ? yTop - 12 : yTop + 5));
    // a step's reading is shown where the point stops (a moving number would sit on the labels it passes); a drag reads live
    pl.textContent = live || show > 0.97 ? (!live && pt.label ? pt.label : reading(xv)) : '';
    part.dragged = live ? xv : null;
  }
  var dragX = null, lastV = null, lastShow = 0;
  if (pt && pt.drag) {
    var stepBy = pt.step || (X.every || (X.max - X.min) / 10) / 4;
    h.drag(g, { x: 0, y: 0, w: w, h: ht }, {
      name: 'drag along the ' + (X.label || 'axis') + ' to read the value',
      move: function (x) { dragX = X.min + h.clamp(x / w, 0, 1) * (X.max - X.min); place(dragX, 1, true); },
      step: function (d) {
        var from = dragX != null ? dragX : pt.from != null ? pt.from : lo;
        dragX = h.clamp(from + d * stepBy, Math.min(lo, hi), Math.max(lo, hi)); place(dragX, 1, true);
      }
    });
  }
  part.render = function (v) {
    var n = curves.length;
    drawn.forEach(function (c, i) {
      var k = h.clamp(v - i, 0, 1);
      c.k = k;
      c.path.setAttribute('stroke-dasharray', c.len);
      c.path.setAttribute('stroke-dashoffset', (c.len * (1 - k)).toFixed(1));
      c.g.style.opacity = k > 0.001 ? '1' : '0';
      c.dot.style.opacity = k > 0.001 ? '1' : '0';
      if (c.lab) c.lab.style.opacity = k > 0.95 ? '1' : '0';
      if (c.bpl) c.bpl.style.opacity = k > 0.95 ? '1' : '0';
    });
    if (mark) {
      if (v !== lastV) { dragX = null; lastV = v; }   // the steps moved the figure: the point goes where they say
      var m = h.clamp(v - n, 0, 1), from = pt.from != null ? pt.from : lo, to = pt.to != null ? pt.to : from;
      lastShow = m;
      if (dragX != null) place(dragX, 1, true);
      else place(from + (to - from) * m, m, false);
    }
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M04",
  course: 'IGF Basic', module: 'M04', made: '2026-10-16',
  look: 'diagram',
  why: 'M04 s03: vapour pressure against temperature for methane, propane and methanol - each curve meets the 1 bar line at its boiling point, then a point slides up the propane curve to 20 °C and reads about 8 bar (SPEC.md family 6: "curve with a moving point"). 2.66.0 (gas M02 s11 / s14: "pick a cargo, drag to 45 °C"): yaxis.log, point.drag, point.curve "all"',
  value: '0..n: curve k draws itself from k to k+1; then n..n+1 the point slides along point.curve from point.from to point.to (point.drag: the trainee moves it too)',
  css: '.kit-curve-chart-grid{stroke:var(--line-d);stroke-width:1}.kit-curve-chart-frame{fill:none;stroke:var(--faint-d);stroke-width:1.5}.kit-curve-chart-hline{stroke:var(--dim-d);stroke-width:2;stroke-dasharray:8 6}.kit-curve-chart-line{fill:none;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}.kit-curve-chart-c0 .kit-curve-chart-line{stroke:var(--blue)}.kit-curve-chart-c0 .kit-curve-chart-dot{fill:var(--blue)}.kit-curve-chart-c1 .kit-curve-chart-line{stroke:var(--txt-d);stroke-dasharray:14 7}.kit-curve-chart-c1 .kit-curve-chart-dot{fill:var(--txt-d)}.kit-curve-chart-c2 .kit-curve-chart-line{stroke:var(--cold);stroke-width:5;stroke-dasharray:1 8}.kit-curve-chart-c2 .kit-curve-chart-dot{fill:var(--cold)}.kit-curve-chart-guide{stroke:var(--blue);stroke-width:1.5;stroke-dasharray:4 4}.kit-curve-chart-pdot{fill:var(--txt-d);stroke:var(--blue);stroke-width:3}',
  example: { size: [420, 260], parts: [
    { id: 'VP', type: 'curve_chart', x: 50, y: 30, w: 340, h: 180,
      xaxis: { min: -60, max: 60, every: 20, unit: '°C', label: 'temperature °C' }, yaxis: { min: 0, max: 16, every: 4, unit: 'bar', label: 'bar' },
      hline: { at: 1, label: '1 bar', labelX: -58 },
      curves: [{ label: 'propane', pts: [[-42, 1], [0, 4.7], [20, 8.4], [40, 13.7]], labelAt: [42, 14.5] }],
      point: { curve: 0, from: -42, to: 20, label: '20 °C · about 8 bar', drag: true } } ],
    steps: [ { title: 'The curve', play: [['VP', 1, 1500]] }, { title: 'Read it at 20 °C', play: [['VP', 2, 1500]] } ] }
});
/* end kit-part */
/* kit-part: molecule */
KIT.define('molecule', function (fig, part, g, p) {
  /* 2.66.0 (gas M02 s20-s22: "condensed structural formulas, atom counts" drawn as text - the kit had no molecule): a
     structural formula, the atoms as their letters in rings, single / double / triple bonds between them. A cargo by
     its name ("formula": "propane", "C3H8", "ethylene", "VCM", "ammonia" ...) or any molecule as "atoms": [[el, x, y]] and
     "bonds": [[i, j, order]] in bond lengths. "build": true - the value brings the skeleton (0..1), then the hydrogens (1..2) */
  var h = KIT.h;
  function alkane(n) {                                  // a straight chain: H above and below every carbon, one at each end
    var at = [], bd = [], i;
    for (i = 0; i < n; i++) { at.push(['C', i, 0]); if (i) bd.push([i - 1, i, 1]); }
    for (i = 0; i < n; i++) {
      at.push(['H', i, -1]); bd.push([i, at.length - 1, 1]);
      at.push(['H', i, 1]); bd.push([i, at.length - 1, 1]);
    }
    at.push(['H', -1, 0]); bd.push([0, at.length - 1, 1]);
    at.push(['H', n, 0]); bd.push([n - 1, at.length - 1, 1]);
    return { atoms: at, bonds: bd };
  }
  var D = 0.72;                                         // a hydrogen on a double-bonded carbon stands off at 45 degrees
  var KNOWN = {
    methane: ['CH4', alkane(1)], ethane: ['C2H6', alkane(2)], propane: ['C3H8', alkane(3)], butane: ['C4H10', alkane(4)],
    ethylene: ['C2H4', { atoms: [['C', 0, 0], ['C', 1, 0], ['H', -D, -D], ['H', -D, D], ['H', 1 + D, -D], ['H', 1 + D, D]],
                         bonds: [[0, 1, 2], [0, 2, 1], [0, 3, 1], [1, 4, 1], [1, 5, 1]] }],
    propylene: ['C3H6', { atoms: [['C', 0, 0], ['C', 1, 0], ['C', 2, 0], ['H', -D, -D], ['H', -D, D], ['H', 1, -1], ['H', 2, -1], ['H', 2, 1], ['H', 3, 0]],
                          bonds: [[0, 1, 2], [1, 2, 1], [0, 3, 1], [0, 4, 1], [1, 5, 1], [2, 6, 1], [2, 7, 1], [2, 8, 1]] }],
    butadiene: ['C4H6', { atoms: [['C', 0, 0], ['C', 1, 0], ['C', 2, 0], ['C', 3, 0], ['H', -D, -D], ['H', -D, D], ['H', 1, -1], ['H', 2, 1], ['H', 3 + D, -D], ['H', 3 + D, D]],
                          bonds: [[0, 1, 2], [1, 2, 1], [2, 3, 2], [0, 4, 1], [0, 5, 1], [1, 6, 1], [2, 7, 1], [3, 8, 1], [3, 9, 1]] }],
    'vinyl chloride': ['C2H3Cl', { atoms: [['C', 0, 0], ['C', 1, 0], ['H', -D, -D], ['H', -D, D], ['H', 1 + D, -D], ['Cl', 1 + D, D]],
                                    bonds: [[0, 1, 2], [0, 2, 1], [0, 3, 1], [1, 4, 1], [1, 5, 1]] }],
    ammonia: ['NH3', { atoms: [['N', 0, 0], ['H', -1, 0], ['H', 1, 0], ['H', 0, 1]], bonds: [[0, 1, 1], [0, 2, 1], [0, 3, 1]] }],
    nitrogen: ['N2', { atoms: [['N', 0, 0], ['N', 1, 0]], bonds: [[0, 1, 3]] }],
    'carbon dioxide': ['CO2', { atoms: [['O', 0, 0], ['C', 1, 0], ['O', 2, 0]], bonds: [[0, 1, 2], [1, 2, 2]] }],
    water: ['H2O', { atoms: [['O', 0, 0], ['H', -0.8, 0.6], ['H', 0.8, 0.6]], bonds: [[0, 1, 1], [0, 2, 1]] }]
  };
  var ALIAS = { 'n-butane': 'butane', ethene: 'ethylene', propene: 'propylene', vcm: 'vinyl chloride', 'co2': 'carbon dioxide',
                ch4: 'methane', c2h6: 'ethane', c3h8: 'propane', c4h10: 'butane', c2h4: 'ethylene', c3h6: 'propylene',
                c4h6: 'butadiene', c2h3cl: 'vinyl chloride', nh3: 'ammonia', n2: 'nitrogen', h2o: 'water' };
  var key = String(p.formula || '').toLowerCase().trim(), name = KNOWN[key] ? key : ALIAS[key] || null;
  var mol = p.atoms ? { atoms: p.atoms, bonds: p.bonds || [] } : name ? KNOWN[name][1] : alkane(1);
  var sub = function (f) { return String(f).replace(/\d/g, function (d) { return '₀₁₂₃₄₅₆₇₈₉'.charAt(+d); }); };
  var caption = p.label != null ? p.label : name ? name + '  ' + sub(KNOWN[name][0]) : '';
  var xs = mol.atoms.map(function (a) { return a[1]; }), ys = mol.atoms.map(function (a) { return a[2]; });
  var x0 = Math.min.apply(null, xs), y0 = Math.min.apply(null, ys);
  var spanX = Math.max.apply(null, xs) - x0, spanY = Math.max.apply(null, ys) - y0, pad = 18;
  var L = p.bond || 46, LX, LY;                          // a box (w, h): the molecule grows to fill it, up to bonds of 90
  if (p.w || p.h) {
    L = p.bond || 90;
    if (p.w) L = Math.min(L, (p.w - 2 * pad) / Math.max(spanX, 0.5));
    if (p.h) L = Math.min(L, (p.h - 2 * pad - (caption ? 30 : 0)) / Math.max(spanY, 0.5));
  }
  /* 2.67.0 - a structural formula is a schema, not a scale drawing: in its box the bonds across and down may differ, by
     at most 1.6 times, so a long flat chain fills a tall box instead of leaving it half blank (two and three cargoes on
     one slide, the drawing check) */
  LX = LY = L;
  if (p.w && p.h && spanX > 0.5 && spanY > 0.5) {
    LX = Math.min((p.w - 2 * pad) / spanX, L * 1.6, p.bond || 90);
    LY = Math.min((p.h - 2 * pad - (caption ? 30 : 0)) / spanY, L * 1.6, p.bond || 90);
  }
  /* in a box, the molecule stands in its middle: a flat one (ethylene) in a tall box left all its room under it */
  var cx = p.w ? Math.max(0, (p.w - 2 * pad - spanX * LX) / 2) : 0;
  var cy = p.h ? Math.max(0, (p.h - 2 * pad - (caption ? 30 : 0) - spanY * LY) / 2) : 0;
  function at(a) { return [pad + cx + (a[1] - x0) * LX, pad + cy + (a[2] - y0) * LY]; }
  var heavy = function (a) { return a[0] !== 'H'; };
  /* the formula's whole area is its content (data-kit-fills: the drawing check counts its box, as a pipe's bends) */
  var body = h.el('g', { 'data-kit-fills': '' }, g);
  var gB = [h.el('g', {}, body), h.el('g', {}, body)], gA = [h.el('g', {}, body), h.el('g', {}, body)];   // [skeleton, hydrogens]
  mol.bonds.forEach(function (b) {
    var A = mol.atoms[b[0]], B = mol.atoms[b[1]], pa = at(A), pb = at(B), n = b[2] || 1;
    var dx = pb[0] - pa[0], dy = pb[1] - pa[1], len = Math.sqrt(dx * dx + dy * dy) || 1, ox = -dy / len, oy = dx / len;
    var off = n === 1 ? [0] : n === 2 ? [-3.6, 3.6] : [-5.5, 0, 5.5];
    var layer = gB[heavy(A) && heavy(B) ? 0 : 1];
    off.forEach(function (o) {
      h.el('line', { x1: (pa[0] + ox * o).toFixed(1), y1: (pa[1] + oy * o).toFixed(1), x2: (pb[0] + ox * o).toFixed(1), y2: (pb[1] + oy * o).toFixed(1),
                     'class': 'kit-molecule-bond', 'data-may-cross': '', 'data-may-overlap': '' }, layer);
    });
  });
  var rings = [];
  mol.atoms.forEach(function (a) {
    var q = at(a), layer = gA[heavy(a) ? 0 : 1], el = String(a[0]);
    var ag = h.el('g', { transform: 'translate(' + q[0].toFixed(1) + ' ' + q[1].toFixed(1) + ')', 'data-may-overlap': '' }, layer);
    var ring = h.el('circle', { r: heavy(a) ? 13 : 10, 'class': 'kit-molecule-atom kit-molecule-' + (el === 'C' ? 'c' : el === 'H' ? 'h' : 'x') }, ag);
    h.el('text', { y: 4.5, 'text-anchor': 'middle', 'class': heavy(a) ? 'kit-h' : 'kit-cap' }, ag, el);
    rings.push({ ring: ring, r: heavy(a) ? 13 : 10, el: el });
  });
  fig.fit(function (k) { rings.forEach(function (o) { o.ring.setAttribute('r', (o.r * Math.max(1, k * (o.el.length > 1 ? 1.15 : 1))).toFixed(1)); }); });
  var cap = caption ? h.label(fig, g, { x: (pad + cx + spanX * LX / 2).toFixed(1), y: (pad * 2 + cy + spanY * LY + 14).toFixed(1), 'text-anchor': 'middle', 'class': 'kit-cap' }, caption) : null;
  part.render = function (v) {
    var a = p.build ? h.clamp(v, 0, 1) : 1, b = p.build ? h.clamp(v - 1, 0, 1) : 1;
    if (cap) cap.style.opacity = a > 0.001 ? a.toFixed(2) : '0';     // its name comes in with it
    gB[0].style.opacity = gA[0].style.opacity = a > 0.001 ? a.toFixed(2) : '0';
    gB[1].style.opacity = gA[1].style.opacity = b > 0.001 ? b.toFixed(2) : '0';
  };
}, {
  family: 'charts',
  status: 'kit',
  course: 'GAS BASIC', module: 'M02', made: '2026-10-26',
  look: 'diagram',
  why: 'gas M02 s20-s22 (the timed 2.65 build): the cargoes\' structural formulas - methane to butane, the double bond of ethylene and propylene, VCM, ammonia - were drawn as lines of text; the kit had no molecule',
  value: 'with build: true, 0..1 the skeleton (every atom but hydrogen, and its bonds) comes in, 1..2 the hydrogens; without build the whole molecule shows',
  css: '.kit-molecule-bond{stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round}.kit-molecule-atom{fill:var(--deep-3);stroke-width:2}.kit-molecule-c{stroke:var(--blue);stroke-width:2.5}.kit-molecule-h{stroke:var(--faint-d)}.kit-molecule-x{stroke:var(--cold);stroke-width:2.5}',
  example: { size: [300, 200], parts: [{ id: 'M', type: 'molecule', x: 30, y: 20, formula: 'propane', build: true }],
    steps: [{ title: 'Three carbons in a chain', play: [['M', 1, 1200]] }, { title: 'Eight hydrogens', play: [['M', 2, 1200]] }] }
});
/* end kit-part */
/* kit-part: fan */
KIT.define('fan', function (fig, part, g, p) {
  var h = KIT.h, r = p.r || 26, half = (p.len || 170) / 2, wh = r + 9;
  var deg = { right: 0, down: 90, left: 180, up: 270 }[p.dir || 'right'] || 0, vert = deg === 90 || deg === 270;
  var sym = h.el('g', { transform: deg ? 'rotate(' + deg + ')' : null }, g);
  /* 2.52.0: the duct's steel walls, the fan's cast casing ring bolted between them, steel blades on their hub */
  var eq = h.equip(sym, { shadow: false });
  [-1, 1].forEach(function (s) {
    h.body('rect', { x: -half, y: s < 0 ? -wh - 6 : wh, width: 2 * half, height: 6, rx: 2 }, eq, { mat: 'steel', shade: 'box' });
  });
  h.el('circle', { r: r + 3, 'class': 'kit-fan-case' }, eq);
  [45, 135, 225, 315].forEach(function (a) { var b = h.polar(r + 3, a); h.el('circle', { cx: b[0].toFixed(1), cy: b[1].toFixed(1), r: 1.4, 'class': 'kit-m-bolt' }, eq); });
  var rotor = h.el('g', { 'class': 'kit-fan-rotor' }, sym);
  for (var bl = 0; bl < 7; bl++) {                      // an axial fan's seven blades
    h.el('path', { d: 'M0 0 Q ' + (r * 0.4) + ' ' + (-r * 0.48) + ' ' + (r * 0.85) + ' ' + (-r * 0.15) + ' Q ' + (r * 0.48) + ' ' + (r * 0.04) + ' 0 0 Z',
      transform: 'rotate(' + (bl * 360 / 7).toFixed(1) + ')', 'class': 'kit-fan-blade' }, rotor);
  }
  h.el('circle', { r: 7, 'class': 'kit-fan-hub' }, sym);
  h.el('path', { d: 'M' + (-r) + ' 0 H' + r + ' M0 ' + (-r) + ' V' + r, 'class': 'kit-fan-guard', 'data-low-contrast': '' }, sym);   // the guard over the rotor: thin, the blades carry it
  h.el('circle', { r: r + 0.5, 'class': 'kit-fan-guard', 'data-low-contrast': '' }, sym);
  var air = h.el('g', {}, sym);
  [-15, 0, 15].forEach(function (y) {
    [[-half + 10, -r - 10], [r + 10, half - 10]].forEach(function (s) {
      if (s[1] - s[0] < 16) return;                    // a duct too short for its arrows: they would sit on the casing - the rotor shows it turns
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
  look: 'equipment',
  why: 'M05 (machinery space ventilation) and M11 (enclosed-space entry): a mechanical ventilation fan in a duct or wall opening - the arrows show which way it moves the air, and no arrows means no air',
  value: '0 stopped .. 1 running: blades turn faster, the air arrows flow in the direction dir (right, left, up, down); RUNNING or STOPPED under the name',
  css: '.kit-fan-case{fill:var(--deep);stroke:var(--kit-cast);stroke-width:6}' +
    '.kit-fan-blade{fill:var(--kit-steel);stroke:var(--mat-edge-steel);stroke-width:1;stroke-linejoin:round}' +
    '.kit-fan-hub{fill:var(--mat-stem);stroke:var(--mat-edge-steel);stroke-width:1}' +
    '.kit-fan-guard{fill:none;stroke:var(--mat-yoke);stroke-width:1;opacity:.7}' +
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
    var px = -30 * Math.cos(a), py = 30 * Math.sin(a), ped = h.equip(g);
    h.body('rect', { x: (px - 4).toFixed(1), y: py.toFixed(1), width: 8, height: 34 }, ped, { mat: 'steel', shade: 'cylv' });
    h.body('rect', { x: (px - 18).toFixed(1), y: (py + 33).toFixed(1), width: 36, height: 5, rx: 1 }, ped, { mat: 'steel', shade: 'box' });
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
  /* 2.52.0: the nozzle as it is - a cast monitor barrel on its pivot, a branch pipe on its rubber hose, a sprinkler head */
  var nz = h.equip(sym);
  if (kind === 'monitor') {
    h.body('path', { d: 'M-48 -6 H-10 L0 -10 V10 L-10 6 H-48 Z' }, nz, { mat: 'cast', shade: 'box' });
    h.el('circle', { cx: -30, cy: 0, r: 5, 'class': 'kit-spray-pivot' }, nz);
  } else if (kind === 'hand') {
    h.el('path', { d: 'M-34 0 C-52 0 -52 26 -78 26', 'class': 'kit-pipe-s kit-ms-rubber kit-spray-hose' }, nz);
    h.body('path', { d: 'M-34 -5 H-8 L0 -9 V9 L-8 5 H-34 Z' }, nz, { mat: 'steel', shade: 'box' });
    h.body('path', { d: 'M-24 5 L-28 20 H-19 L-16 5' }, nz, { mat: 'cast' });
  } else {
    h.el('line', { x1: -42, y1: 0, x2: -10, y2: 0, 'class': 'kit-pipe-s kit-ms-steel' }, nz);
    h.el('path', { d: 'M-12 -9 L-2 -13 M-12 9 L-2 13', 'class': 'kit-m-stem kit-spray-frame' }, nz);
    h.el('line', { x1: 0, y1: -13, x2: 0, y2: 13, 'class': 'kit-m-stem kit-spray-frame' }, nz);
    h.body('circle', { cx: -7, cy: 0, r: 3.5 }, nz, { mat: 'cast' });
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
  look: 'equipment',
  why: 'M13 fixed dry-powder installation, powder monitors and hand hoses: what comes out of the nozzle, which way and how far - a cone of powder, water or foam of a given reach and angle',
  value: '0..1 how much is discharged: the spray grows out of the nozzle to its reach (nozzle monitor, hand or sprinkler; agent powder, water or foam; angle in degrees above horizontal, -90 = down)',
  css: '.kit-spray-cone line,.kit-spray-cone path{fill:none;stroke:var(--dim-d);stroke-width:1.5;stroke-dasharray:4 5}' +
    '.kit-spray-pivot{fill:var(--kit-steel);stroke:var(--txt-d);stroke-width:1.5}' +
    '.kit-spray-hose{fill:none;stroke-width:8;stroke-linecap:round}.kit-spray-frame{stroke-width:3}' +
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
  /* 2.52.0 (operator's review): a compressed gas fills its bottle at every pressure - there is no level to see, and a fill
     dropping in a see-through bottle taught that the gas "runs down" like a liquid. The bottle is opaque, painted (its
     shoulder in the gas's colour code with "code": true, below), and how much is left is read
     where a seafarer reads it: the pressure gauge on its valve, the needle driven by the value, the reading in bar on the
     bottle's plate under its name ("bar": the full pressure, 200, or 300 for breathing air).
     CO2 is stored as a LIQUID: its gauge would read its vapour pressure, about 57 bar at 20 degC, full or nearly empty -
     its contents are checked by WEIGHING it. So a CO2 bottle has no gauge; its plate reads its weight of CO2 ("kg": full,
     45), and its liquid shows in a cut-away window, named at its line ("liquid": false leaves the window out). Falling
     contents never make a CO2 bottle's pressure fall (operator's review, 2026-10-20). */
  var h = KIT.h, w = p.w || 56, ht = p.h || 150, cid = fig.uid + '-' + (p.id || 'gc') + '-cyl', gas = String(p.gas || '').toUpperCase();
  var co2 = gas === 'CO2', full = p.bar != null ? +p.bar : (gas === 'AIR' ? 300 : 200), kg = p.kg != null ? +p.kg : 45, liquid = co2 && p.liquid !== false;
  function shell(wd) {
    var hw = wd / 2;
    return 'M' + (-hw) + ' 0 V' + (-(ht - hw)) + ' A' + hw + ' ' + hw + ' 0 0 1 ' + hw + ' ' + (-(ht - hw)) + ' V0 Z';
  }
  var eq = h.equip(g);
  var clip = h.el('path', { d: shell(w) }, h.el('clipPath', { id: cid }, h.el('defs', {}, g)));
  var body = h.body('path', { d: shell(w) }, eq, { mat: 'paint', shade: 'cylv' });
  /* the shoulder's colour code (EN 1089-3) only when the lesson teaches it ("code": true): the standard leaves out the
     cylinders of fixed extinguishing systems, and a dark dome on a dark slide read as "empty" (operator's review). When on,
     it is paint on the dome down to a seam, shaded as the bottle is; breathing air's quarters seen from the front: a
     white quarter facing us, black ones either side, their seams curving over the dome to its top */
  var codeOf = { N2: ['dark', 'black shoulder'], CO2: ['grey', 'grey shoulder'], AIR: ['dark', 'black and white shoulder'] }[gas];
  var coded = !!(p.code && codeOf), shPaint = null, shQuarter = null, shShade = null, shSeam = null;
  if (coded) {
    var shoulder = h.el('g', { 'clip-path': 'url(#' + cid + ')' }, eq);
    shPaint = h.el('path', { 'class': 'kit-gas-cylinder-sh-' + codeOf[0], 'data-low-contrast': '' }, shoulder);   // the bottle's outline carries the shape
    if (gas === 'AIR') shQuarter = h.el('path', { 'class': 'kit-gas-cylinder-sh-white', 'data-low-contrast': '' }, shoulder);
    shShade = h.el('path', { 'class': 'kit-sh kit-sh-cylv', 'aria-hidden': 'true' }, shoulder);                       // curved paint, lit as the body is
    shSeam = h.el('path', { 'class': 'kit-gas-cylinder-seam', 'data-low-contrast': '' }, shoulder);   // the paint's edge: on black it is the colour change that shows it
  }
  var bodyLine = h.el('path', { d: shell(w), 'class': 'kit-gas-cylinder-o' }, eq);
  var ring = h.body('rect', { x: -w / 2 - 4, y: -3, width: w + 8, height: 5, rx: 1.5 }, eq, { mat: 'paint', shade: 'box' });   // foot ring
  /* the valve on the bottle's neck, drawn for a 150-high bottle and scaled down with a smaller one (a 58-high bottle's
     hand wheel reached into the readout above it, IGF M07 q02) */
  var vg = h.el('g', { transform: 'translate(0 ' + (-ht) + ') scale(' + h.clamp(ht / 150, 0.55, 1).toFixed(3) + ')' }, eq);
  h.body('rect', { x: -7, y: -8, width: 14, height: 10 }, vg, { mat: 'steel', shade: 'cylv' });                 // neck
  h.body('rect', { x: -9.5, y: -3, width: 19, height: 3.5, rx: 1 }, vg, { mat: 'steel', shade: 'box' });       // its collar
  h.body('rect', { x: -11, y: -25, width: 22, height: 17, rx: 3 }, vg, { mat: 'steel', shade: 'box' });         // valve body
  h.body('rect', { x: 11, y: -21, width: 11, height: 7, rx: 2 }, vg, { mat: 'steel', shade: 'cyl' });           // outlet
  h.el('line', { x1: 0, y1: -25, x2: 0, y2: -31, 'class': 'kit-m-stem' }, vg);
  h.el('ellipse', { cx: 0, cy: -31, rx: 13, ry: 3.4, 'class': 'kit-m-wheel' }, vg);                               // hand wheel
  var gx = -19, gy = -17, needle = null;
  if (!co2) {                                          // the pressure gauge on the valve: an icon, its reading is on the plate
    h.body('rect', { x: -13, y: gy - 2, width: 3, height: 4 }, vg, { mat: 'steel' });
    h.el('circle', { cx: gx, cy: gy, r: 8.5, 'class': 'kit-gas-cylinder-dial' }, vg);
    h.el('path', { d: h.arc(6.4, 135, 405), transform: 'translate(' + gx + ' ' + gy + ')', 'class': 'kit-gas-cylinder-scale' }, vg);
    needle = h.el('line', { x1: 0, y1: 0, x2: 6.2, y2: 0, 'class': 'kit-gas-cylinder-needle' }, vg);
    h.el('circle', { cx: gx, cy: gy, r: 1.3, 'class': 'kit-m-bolt' }, vg);
  }
  /* liquid CO2 in a cut-away window under the plate: dark inside, the liquid pale, named at its line */
  var win = liquid ? h.el('rect', { rx: 3, 'class': 'kit-gas-cylinder-win' }, eq) : null;
  var lvl = liquid ? h.el('rect', { 'class': 'kit-gas-cylinder-liq' }, eq) : null;
  var surf = liquid ? h.el('line', { 'class': 'kit-surface kit-m-lngs' }, eq) : null;
  /* the window says what it shows on a tag under it, inside the bottle: no room beside a bottle in a row of them */
  var ltag = liquid ? h.el('rect', { rx: 2, 'class': 'kit-gas-cylinder-plate' }, g) : null;
  var lname = liquid ? h.el('text', { x: 0, 'text-anchor': 'middle', 'class': 'kit-cap' }, g, p.liquidLabel || 'liquid') : null;
  /* the plate: the gas's name, and under it what is left - the pressure in bar, or for CO2 its weight in kg - the number
     over its unit, so the bottle stays as narrow as a real one. Shown when the steps change this bottle ("reading":
     true / false says so outright): a bottle that never changes carries its name only */
  var moved = (fig.spec.steps || []).some(function (s) {
    return (s.play || []).some(function (a) { return a[0] === p.id; }) || (s.set && s.set[p.id] != null);
  });
  var showRead = p.reading != null ? !!p.reading : moved;
  var plate = h.el('rect', { rx: 3, 'class': 'kit-gas-cylinder-plate' }, g);
  var cap = p.gas ? h.el('text', { x: 0, 'text-anchor': 'middle', 'class': 'kit-tl' }, g, p.gas) : null;
  var reading = showRead ? h.el('text', { x: 0, 'text-anchor': 'middle', 'class': 'kit-state kit-gas-cylinder-read' }, g) : null;
  var unit = showRead ? h.el('text', { x: 0, 'text-anchor': 'middle', 'class': 'kit-state kit-gas-cylinder-read' }, g, co2 ? 'kg' : 'bar') : null;
  if (!cap && !reading) plate.style.display = 'none';
  var winTop = 0, winBot = 0, ww = 16;
  var capText = coded ? (p.label ? p.label + '\n' : '') + codeOf[1] : p.label;   // a coded bottle's caption names its code
  if (capText) h.label(fig, g, { x: 0, y: 24, 'text-anchor': 'middle', 'class': 'kit-cap' }, capText);
  fig.fit(function (k) {                                // the bottle is as wide as its plate's words need, 8 a side
    var tw = Math.max(cap ? h.widest(cap, [p.gas]) : 0, reading ? h.widest(reading, [String(co2 ? kg : full)]) : 0, unit ? h.widest(unit, [unit.textContent]) : 0);
    if (lname) tw = Math.max(tw, h.widest(lname, [lname.textContent]));   // the window's tag sits inside the bottle too
    var rows = (cap ? 1 : 0) + (reading ? 2 : 0), pw = tw + 16, ph = (rows * 16 + 10) * k, wd = Math.max(w, pw + 12), py = -ht * 0.62 - ph / 2;
    [clip, bodyLine].forEach(function (n) { n.setAttribute('d', shell(wd)); });
    h.reshape(body, { d: shell(wd) }); h.reshape(ring, { x: -wd / 2 - 4, width: wd + 8 });
    if (coded) {
      var hw = wd / 2, yd = -(ht - hw), yb = yd + Math.max(8, hw * 0.3), q = hw * Math.SQRT1_2;   // dome base, the seam under it, a quarter's edge
      var band = 'M' + (-hw - 1) + ' ' + yb + ' V' + (-ht - 1) + ' H' + (hw + 1) + ' V' + yb + ' Z';
      shPaint.setAttribute('d', band); shShade.setAttribute('d', band);
      var seam = 'M' + (-hw) + ' ' + yb + ' H' + hw;
      if (shQuarter) {
        shQuarter.setAttribute('d', 'M' + (-q) + ' ' + yb + ' V' + yd + ' A' + q + ' ' + hw + ' 0 0 1 0 ' + (-ht) +
          ' A' + q + ' ' + hw + ' 0 0 1 ' + q + ' ' + yd + ' V' + yb + ' Z');
        seam += ' M' + (-q) + ' ' + yb + ' V' + yd + ' A' + q + ' ' + hw + ' 0 0 1 0 ' + (-ht) + ' A' + q + ' ' + hw + ' 0 0 1 ' + q + ' ' + yd + ' V' + yb;
      }
      shSeam.setAttribute('d', seam);
    }
    plate.setAttribute('x', -pw / 2); plate.setAttribute('width', pw); plate.setAttribute('y', py); plate.setAttribute('height', ph);
    if (cap) cap.setAttribute('y', py + 18 * k);
    if (reading) { reading.setAttribute('y', py + (cap ? 34 : 18) * k); unit.setAttribute('y', py + (cap ? 50 : 34) * k); }
    if (win) {
      ww = Math.max(16, wd * 0.34);
      var th = 22 * k, tw2 = h.widest(lname, [lname.textContent]) + 16, ty = -7 - th;
      ltag.setAttribute('x', -tw2 / 2); ltag.setAttribute('width', tw2); ltag.setAttribute('y', ty); ltag.setAttribute('height', th);
      lname.setAttribute('y', ty + 16 * k);
      winTop = py + ph + 10; winBot = ty - 6;
      win.setAttribute('x', -ww / 2); win.setAttribute('width', ww); win.setAttribute('y', winTop); win.setAttribute('height', Math.max(8, winBot - winTop));
      lvl.setAttribute('x', -ww / 2 + 2); lvl.setAttribute('width', ww - 4);
      surf.setAttribute('x1', -ww / 2 + 2); surf.setAttribute('x2', ww / 2 - 2);
      part.render(part.v);
    }
  });
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    if (needle) needle.setAttribute('transform', 'translate(' + gx + ' ' + gy + ') rotate(' + (135 + 270 * k).toFixed(1) + ')');
    if (reading) reading.textContent = String(Math.round(k * (co2 ? kg : full)));
    if (lvl && winBot > winTop) {                       // the liquid's level in the window: full is about three quarters of it
      var H2 = winBot - winTop - 2, top2 = winBot - 1 - k * 0.75 * H2;
      lvl.setAttribute('y', top2.toFixed(1)); lvl.setAttribute('height', Math.max(0, winBot - 1 - top2).toFixed(1));
      surf.setAttribute('y1', top2.toFixed(1)); surf.setAttribute('y2', top2.toFixed(1)); surf.style.opacity = k > 0.02 ? '1' : '0';
    }
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  look: 'equipment',
  why: 'M13 nitrogen cylinders that drive a dry-powder installation, and M10 breathing-air cylinders (SCBA): a compressed-gas bottle with its valve, shown with how much pressure is left in it - on the pressure gauge of its valve (2.52.0)',
  value: 'how full the cylinder is, 0..1. A compressed gas (N2, AIR): its pressure - the gauge needle, and the reading in bar on its plate ("bar": the full pressure, 200, or 300 for AIR). CO2, stored as a liquid: its weight of CO2 in kg on its plate ("kg": full, 45) and its liquid level in a cut-away window, named at its line ("liquid": false leaves it out) - no gauge, its pressure does not fall as it empties. The reading (number over unit, the bottle keeps its width) shows when the steps change this bottle; "reading": true / false says so outright. It stands on its base point (x, y); w and h size it; gas is the word on its plate. "code": true paints the shoulder in its EN 1089-3 colour code and names it in the caption (N2 black, CO2 grey, AIR black and white quarters) - only when the lesson teaches the code: the standard does not cover the cylinders of fixed extinguishing systems',
  css: '.kit-gas-cylinder-sh-dark{fill:var(--mat-window)}.kit-gas-cylinder-sh-grey{fill:var(--mat-yoke)}.kit-gas-cylinder-sh-white{fill:var(--mat-white)}' +
    '.kit-gas-cylinder-seam{fill:none;stroke:var(--mat-window);stroke-width:1.5}' +
    '.kit-gas-cylinder-o{fill:none;stroke:var(--dim-d);stroke-width:1.5}' +
    '.kit-gas-cylinder-win{fill:var(--mat-hole);stroke:var(--mat-plate);stroke-width:1.2}.kit-gas-cylinder-liq{fill:var(--mat-lng-mid);opacity:.85}' +
    '.kit-gas-cylinder-dial{fill:var(--mat-plate);stroke:var(--mat-ink);stroke-width:1.4}.kit-gas-cylinder-scale{fill:none;stroke:var(--mat-edge-clad);stroke-width:1.2}' +
    '.kit-gas-cylinder-needle{stroke:var(--mat-ink);stroke-width:1.5;stroke-linecap:round}' +
    '.kit-gas-cylinder-plate{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}',
  example: { size: [520, 300], parts: [
    { id: 'A', type: 'gas_cylinder', x: 100, y: 240, w: 84, h: 180, gas: 'N2', label: 'nitrogen', value: 1 },
    { id: 'C', type: 'gas_cylinder', x: 260, y: 240, w: 84, h: 180, gas: 'CO2', label: 'carbon dioxide', value: 1 },
    { id: 'D', type: 'gas_cylinder', x: 420, y: 240, w: 84, h: 180, gas: 'AIR', label: 'breathing air', code: true, value: 0.6 } ],
    steps: [ { title: 'The nitrogen is used - its pressure falls', play: [['A', 0.45, 2800]] },
             { title: 'The CO2 is used - its weight and its liquid fall; its pressure does not', play: [['C', 0.35, 2800]] },
             { title: 'The breathing-air cylinder is refilled', play: [['D', 1, 1800]] } ] }
});
/* end kit-part */
/* kit-part: push_button */
KIT.define('push_button', function (fig, part, g, p) {
  /* SIZE (2.49.2): "h" is the height of the wall plate, 120 units unless the spec says (it was a fixed 182, so two did not
     stack in a 390-high figure). The picture is drawn at h/182 of its first size; its words (the tag, the name, READY /
     PRESSED) keep their own size and sit under it, and the plate grows to hold the tag when the words are grown. */
  var h = KIT.h, S = h.clamp((p.h || 120) / 182, 0.3, 1.5);
  /* 2.52.0: the painted wall plate, the button's cast housing, its steel stem and the guard's steel posts */
  var eq = h.equip(g, { shadow: false });
  var plate = h.body('rect', { rx: 8, 'class': 'kit-push-button-plate' }, eq, { mat: 'paint', shade: 'box' });   // the wall plate it is mounted on
  var art = h.el('g', { transform: 'scale(' + S.toFixed(4) + ')' }, eq);
  h.el('line', { x1: -38, y1: 10, x2: -38, y2: -36, 'class': 'kit-m-stem kit-push-button-post' }, art);
  h.el('line', { x1: 38, y1: 10, x2: 38, y2: -36, 'class': 'kit-m-stem kit-push-button-post' }, art);
  h.body('rect', { x: -44, y: 10, width: 88, height: 30, rx: 5 }, art, { mat: 'cast', shade: 'box' });
  h.body('rect', { x: -7, y: -2, width: 14, height: 13 }, art, { mat: 'steel', shade: 'cylv' });
  [-1, 1].forEach(function (s) { h.body('circle', { cx: 38 * s, cy: -38, r: 3 }, art, { mat: 'steel', shade: 'round' }); });   // the guard's hinge knuckles
  var screws = [0, 1, 2, 3].map(function () { return h.el('circle', { r: 2, 'class': 'kit-m-bolt' }, eq); });
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
    h.reshape(plate, { x: -pw / 2, y: -102 * S, width: pw, height: bottom + 102 * S });
    [[-pw / 2 + 6, -102 * S + 6], [pw / 2 - 6, -102 * S + 6], [-pw / 2 + 6, bottom - 6], [pw / 2 - 6, bottom - 6]].forEach(function (c, i) {
      screws[i].setAttribute('cx', c[0]); screws[i].setAttribute('cy', c[1]);
    });
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
  look: 'equipment',
  why: 'M14 the ESD panel: an emergency-stop mushroom push button under a hinged guard, with its tag - the guard lifts, the button goes down and turns red, the word PRESSED shows (the shutdown it starts is drawn by the other parts)',
  value: '0 ready, 1 pressed: the guard lifts over 0..0.4, the button goes down over 0.4..1 and turns red (trip); READY or PRESSED under the name; option h: the height of the wall plate, 120 units (2.49.2; it was a fixed 182, so two did not stack in a 390-high figure) - the words under it keep their size',
  css: '.kit-push-button-post{stroke-width:3}' +
    '.kit-push-button-cap{fill:var(--cold);fill-opacity:.45;stroke:var(--mat-stem);stroke-width:2}' +
    '.kit-push-button-lid{fill:var(--cold);fill-opacity:.2;stroke:var(--mat-stem);stroke-width:2}' +
    '.kit-push-button-tag{fill:var(--deep);stroke:var(--dim-d);stroke-width:1.5}' +
    '.kit-push-button-on .kit-push-button-cap{fill:var(--warn-d);fill-opacity:.9;stroke:var(--mat-stem)}' +
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
  /* 2.52.0 (operator: "definitely ... the person"): a real worker, not a pictogram - a shaped body in navy workwear with
     reflective bands, face, hair and hands; each item of PPE drawn as the thing itself: a white hard hat with its peak, a
     clear face shield on its frame, rubber-framed goggles, a half mask with its two filters, gauntlet gloves, rubber
     boots, a chemical suit with its zip and tape, a PVC apron, breathing apparatus - cylinder on the back, harness,
     full-face mask and demand hose. Same frame as before (feet at 0, the head at -152): the names keep their places */
  var b = h.el('g', { transform: S === 1 ? null : 'scale(' + S + ')' }, g), nodes = {}, B = h.equip(b);
  function put(item, node) { (nodes[item] = nodes[item] || []).push(node); return node; }
  function use(item) { return wear.indexOf(item) >= 0; }
  function piece(item) { return put(item, h.el('g', {}, B)); }
  var TORSO = 'M-22 -132 Q0 -138 22 -132 L19 -84 Q0 -78 -19 -84 Z';
  function sleeve(s) { return 'M' + (20 * s) + ' -131 L' + (26 * s) + ' -130 L' + (35 * s) + ' -89 L' + (27 * s) + ' -87 Z'; }
  function leg(s) { return 'M' + (2 * s) + ' -85 L' + (19 * s) + ' -85 L' + (16 * s) + ' -11 L' + (6 * s) + ' -11 Z'; }
  if (use('scba')) {                                                   // the cylinder on its back plate, behind the shoulder
    var bk = piece('scba');
    h.body('rect', { x: 12, y: -154, width: 15, height: 66, rx: 6.5 }, bk, { mat: 'paint', shade: 'cylv' });
    h.body('rect', { x: 16, y: -161, width: 7, height: 8, rx: 1.5 }, bk, { mat: 'steel', shade: 'cylv' });
    h.el('circle', { cx: 19.5, cy: -163, r: 3, 'class': 'kit-m-wheel' }, bk);
  }
  [-1, 1].forEach(function (s) {                                       // the worker: legs, shoes, arms, hands
    h.body('path', { d: leg(s) }, B, { mat: 'cloth', shade: 'cylv' });
    [-44, -36].forEach(function (y) { h.el('rect', { x: s < 0 ? -17.6 : 4.2, y: y, width: 13.4, height: 3, 'class': 'kit-m-reflect' }, B); });
    h.body('ellipse', { cx: 11.5 * s, cy: -6, rx: 8.5, ry: 5.5 }, B, { mat: 'rubber', shade: 'round' });
  });
  h.body('path', { d: TORSO }, B, { mat: 'cloth', shade: 'box' });
  h.el('path', { d: 'M-6 -135 L0 -127 L6 -135', 'class': 'kit-person-collar' }, B);
  h.el('rect', { x: -19, y: -97, width: 38, height: 3, 'class': 'kit-m-reflect' }, B);
  [-1, 1].forEach(function (s) {
    h.body('path', { d: sleeve(s) }, B, { mat: 'cloth', shade: 'cylv' });
    h.body('ellipse', { cx: 31.5 * s, cy: -82, rx: 4.6, ry: 6.2 }, B, { mat: 'skin', shade: 'round' });
  });
  h.body('rect', { x: -4.5, y: -142, width: 9, height: 9, rx: 2 }, B, { mat: 'skin' });                       // the neck
  [-1, 1].forEach(function (s) { h.el('ellipse', { cx: 11 * s, cy: -152, rx: 2.4, ry: 3.6, 'class': 'kit-m-skin' }, B); });
  h.body('ellipse', { cx: 0, cy: -153, rx: 11, ry: 13 }, B, { mat: 'skin', shade: 'round' });                 // the head
  h.el('path', { d: 'M-11.4 -154 Q-12.5 -168 0 -168.5 Q12.5 -168 11.4 -154 Q9 -161 0 -161.5 Q-9 -161 -11.4 -154 Z', 'class': 'kit-m-hair' }, B);
  [-1, 1].forEach(function (s) { h.el('ellipse', { cx: 4.4 * s, cy: -153, rx: 1.3, ry: 1.1, 'class': 'kit-m-hair' }, B); });
  h.el('path', { d: 'M-3 -145.5 Q0 -144 3 -145.5', 'class': 'kit-person-mouth' }, B);
  if (use('suit')) {                                                   // a chemical protective suit over the workwear
    var su = piece('suit');
    [-1, 1].forEach(function (s) {
      h.body('path', { d: 'M' + (1.5 * s) + ' -86 L' + (20 * s) + ' -86 L' + (17.5 * s) + ' -12 L' + (5 * s) + ' -12 Z' }, su, { mat: 'suit', shade: 'cylv' });
      h.el('rect', { x: s < 0 ? -18.6 : 3.4, y: -40, width: 15, height: 3.5, 'class': 'kit-m-reflect' }, su);
    });
    h.body('path', { d: 'M-23.5 -133 Q0 -140 23.5 -133 L20.5 -83 Q0 -77 -20.5 -83 Z' }, su, { mat: 'suit', shade: 'box' });
    [-1, 1].forEach(function (s) {
      h.body('path', { d: 'M' + (19.5 * s) + ' -132 L' + (27 * s) + ' -131 L' + (36.5 * s) + ' -88.5 L' + (26.5 * s) + ' -86.5 Z' }, su, { mat: 'suit', shade: 'cylv' });
    });
    h.el('line', { x1: 0, y1: -134, x2: 0, y2: -82, 'class': 'kit-person-zip' }, su);
    h.el('rect', { x: -20.5, y: -98, width: 41, height: 3.5, 'class': 'kit-m-reflect' }, su);
  }
  if (use('boots')) {                                                  // rubber safety boots, up the calf
    var bo = piece('boots');
    [-1, 1].forEach(function (s) {
      h.body('path', { d: 'M' + (4 * s) + ' -34 H' + (18.5 * s) + ' L' + (19.5 * s) + ' -7 Q' + (21.5 * s) + ' -1 ' + (19 * s) + ' 0 H' + (2.5 * s) + ' Q' + (1.5 * s) + ' -4 ' + (3.5 * s) + ' -8 Z',
                       'class': 'kit-person-out' }, bo, { mat: 'rubber', shade: 'cylv' });
    });
  }
  if (use('gloves')) {                                                 // gauntlet gloves over the hands and cuffs
    var gl = piece('gloves');
    [-1, 1].forEach(function (s) {
      h.body('path', { d: 'M' + (25 * s) + ' -95 L' + (36.5 * s) + ' -97 L' + (37.5 * s) + ' -83 Q' + (32 * s) + ' -70 ' + (26 * s) + ' -82 Z', 'class': 'kit-person-out' },
             gl, { mat: 'rubber', shade: 'round' });
    });
  }
  if (use('apron')) {                                                  // a PVC apron over the front, on its neck loop
    var ap = piece('apron');
    h.el('path', { d: 'M-8 -129 Q0 -142 8 -129', 'class': 'kit-person-loop', 'data-low-contrast': '' }, ap);   // a thin loop on the collar: the apron carries it
    h.body('path', { d: 'M-12 -129 H12 L13 -108 L18 -104 L19 -58 Q0 -55 -19 -58 L-18 -104 L-13 -108 Z' }, ap, { mat: 'white', shade: 'box' });
  }
  if (use('scba')) {                                                   // the harness, the full-face mask and its demand hose
    var sf = piece('scba');
    h.el('path', { d: 'M-15 -133 L-13 -88 M15 -133 L13 -88 M-18 -104 H18', 'class': 'kit-person-strap', 'data-low-contrast': '' }, sf);   // black webbing: the cylinder and mask carry the item
    h.el('path', { d: 'M3 -139 C14 -128 30 -136 21 -159', 'class': 'kit-person-loop', 'data-low-contrast': '' }, sf);   // the demand hose, dark rubber: the mask and cylinder carry it
    h.el('ellipse', { cx: 0, cy: -153, rx: 12.5, ry: 14.5, 'class': 'kit-person-mask' }, sf);
    h.body('circle', { cx: 0, cy: -139.5, r: 4 }, sf, { mat: 'cast', shade: 'round' });
  }
  if (use('helmet')) {                                                 // a white hard hat: shell, ridge, peak
    var he = piece('helmet');
    h.body('path', { d: 'M-14 -159 C-14 -178 14 -178 14 -159 Z' }, he, { mat: 'white', shade: 'round' });
    h.el('path', { d: 'M0 -175.5 V-160', 'class': 'kit-person-ridge' }, he);
    h.body('path', { d: 'M-16.5 -160 H17 Q20 -157 16 -156 H-15.5 Q-18.5 -157 -16.5 -160 Z' }, he, { mat: 'white', shade: 'box' });
  }
  if (use('visor')) {                                                  // a clear face shield hinged on its frame
    var vi = piece('visor');
    h.el('path', { d: 'M-14 -160 H14 L13 -138 Q0 -133 -13 -138 Z', 'class': 'kit-person-lens' }, vi);
    h.body('rect', { x: -15, y: -163, width: 30, height: 4, rx: 1.5 }, vi, { mat: 'cast', shade: 'box' });
  }
  if (use('goggles')) {                                                // a rubber-framed goggle on its band
    var go = piece('goggles');
    h.el('line', { x1: -12, y1: -153, x2: 12, y2: -153, 'class': 'kit-person-strap' }, go);
    h.el('rect', { x: -10.5, y: -157.5, width: 21, height: 9, rx: 4, 'class': 'kit-person-goggle' }, go);
  }
  if (use('respirator')) {                                             // a half mask over nose and mouth, a filter each side
    var re = piece('respirator');
    h.body('path', { d: 'M-7.5 -150 Q0 -153 7.5 -150 Q10 -142 0 -137 Q-10 -142 -7.5 -150 Z', 'class': 'kit-person-out' }, re, { mat: 'rubber', shade: 'round' });
    [-1, 1].forEach(function (s) { h.body('circle', { cx: 9.5 * s, cy: -142.5, r: 4 }, re, { mat: 'cast', shade: 'round' }); });
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
  look: 'equipment',
  why: 'M10 PPE for gas work, M11 the attendant and the entrant, M15 spill response: a worker who puts on the protective equipment one item at a time - drawn as a real worker in real PPE since 2.52.0',
  value: '0..n: item k of wear appears (and its name) from k to k+1; wear is any of helmet, visor, goggles, respirator, gloves, suit, apron, boots, scba, in the order they are put on; option labels (or names): {item: words} names an item in the slide\'s own words - {"visor": "GOGGLES"} - or a list in the order of wear, false for no names (2.49.2)',
  css: '.kit-person-out{stroke:var(--mat-yoke)}' +
    '.kit-person-collar{fill:none;stroke:var(--mat-reflect);stroke-width:1.6;stroke-linejoin:round}' +
    '.kit-person-mouth{fill:none;stroke:var(--mat-hair);stroke-width:1;stroke-linecap:round}' +
    '.kit-person-zip{stroke:var(--mat-edge);stroke-width:1.6;stroke-dasharray:2.5 2}' +
    '.kit-person-strap{fill:none;stroke:var(--mat-window);stroke-width:4;stroke-linecap:round}' +
    '.kit-person-loop{fill:none;stroke:var(--mat-window);stroke-width:2.5;stroke-linecap:round}' +
    '.kit-person-ridge{fill:none;stroke:var(--mat-edge);stroke-width:1.5}' +
    '.kit-person-lens{fill:var(--cold);fill-opacity:.22;stroke:var(--dim-d);stroke-width:1.5}' +
    '.kit-person-goggle{fill:var(--cold);fill-opacity:.35;stroke:var(--mat-window);stroke-width:2.5}' +
    '.kit-person-mask{fill:var(--cold);fill-opacity:.2;stroke:var(--dim-d);stroke-width:3.5}',
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
  look: 'diagram',
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
  function plus(x, y, onMetal) {          // a sign on the steel part is dark, so it reads on the metal (2.52.0)
    return h.el('path', { d: 'M' + (x - 4.5) + ' ' + y + ' H' + (x + 4.5) + ' M' + x + ' ' + (y - 4.5) + ' V' + (y + 4.5),
                          'class': 'kit-static-charge-sign' + (onMetal ? ' kit-static-charge-metal' : '') }, g);
  }
  h.el('path', { d: 'M-130 -46 H-26 Q0 -46 0 -20 V-3', 'class': 'kit-pipe kit-ms-rubber' }, g);        // hose (rubber, 2.52.0)
  h.el('line', { x1: -10, y1: -2, x2: 10, y2: -2, 'class': 'kit-flange' }, g);
  var stream = h.el('line', { x1: 0, y1: 4, x2: 0, y2: 66, 'class': 'kit-static-charge-stream' }, g);
  var tsign = [20, 36, 52].map(function (y) { return plus(0, y); });
  h.el('line', { x1: -74, y1: 140, x2: 74, y2: 140, 'class': 'kit-tickl' }, g);                       // the floor
  [-38, 38].forEach(function (x) { h.body('rect', { x: x - 10, y: 130, width: 20, height: 10, rx: 2, 'class': 'kit-static-charge-ins' }, g, { mat: 'rubber', shade: 'box' }); });   // rubber feet: it stands insulated
  h.el('rect', { x: -52, y: 70, width: 104, height: 60, rx: 12, 'class': 'kit-steel' }, g);           // the isolated part
  var order = [2, 7, 0, 9, 4, 5, 1, 8, 3, 6], signs = [];
  for (i = 0; i < 10; i++) signs[order.indexOf(i)] = plus(-36 + 18 * (i % 5), i < 5 ? 88 : 112, true);
  h.body('rect', { x: 112, y: 90, width: 12, height: 50, rx: 2 }, g, { mat: 'steel', shade: 'cylv' });         // an earthed steel post
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
  look: 'diagram',
  why: 'M06 and M07 ignition sources: a liquid or gas flowing out of a hose charges an isolated metal part until a spark jumps to earthed steel - and a bonding cable to earth stops the charge from ever building',
  value: '0..1 the charge on the isolated part builds; 1..1.2 a spark jumps and the charge is gone; option bonded: true draws the bonding cable to earth and the charge never builds',
  css: '.kit-static-charge-stream{stroke:var(--cold);stroke-width:4;stroke-dasharray:8 7;stroke-linecap:round;opacity:0}' +
    '.kit-static-charge-on .kit-static-charge-stream{opacity:1;animation:kit-static-charge-run .5s linear infinite}' +
    '.kit-static-charge-sign{fill:none;stroke:var(--txt-d);stroke-width:2.5;stroke-linecap:round}.kit-static-charge-metal{stroke:var(--mat-window)}' +
    '.kit-static-charge-ins{stroke:var(--mat-yoke)}' +
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
      h.flange(sym, -4, 0, 0, 23, 5);                                                            // its broken flange
    }
    grow = h.el('g', {}, sym);
    var jt = h.el('g', { 'class': 'kit-fire-jet' }, grow);
    /* 2.52.0, as a real jet fire burns: lifted off the nozzle on a blue root, ragged turbulent edges, the tail bent up by
       buoyancy, the hot core starting after the lift-off gap */
    function smooth(pts) {
      var d = 'M' + pts[0][0].toFixed(1) + ' ' + pts[0][1].toFixed(1);
      for (var j = 1; j < pts.length - 1; j++) {
        d += ' Q' + pts[j][0].toFixed(1) + ' ' + pts[j][1].toFixed(1) + ' ' + ((pts[j][0] + pts[j + 1][0]) / 2).toFixed(1) + ' ' + ((pts[j][1] + pts[j + 1][1]) / 2).toFixed(1);
      }
      return d + ' L' + pts[pts.length - 1][0].toFixed(1) + ' ' + pts[pts.length - 1][1].toFixed(1);
    }
    function lift(x) { return -0.12 * len * Math.pow(x / len, 2); }   // the tail rises
    var T = [[0.06, 0.1], [0.18, 0.62], [0.32, 0.9], [0.48, 1], [0.64, 0.88], [0.8, 0.62], [0.92, 0.32], [1, 0]];
    var top = [], bot = [];
    T.forEach(function (q, j) {
      var x = q[0] * len, hw = q[1] * R * (1 + (j % 2 ? 0.07 : -0.05)), y = lift(x);
      top.push([x, y - hw * (1 + (j % 3 === 1 ? 0.06 : 0))]); bot.push([x, y + hw * (j % 3 === 2 ? 1.07 : 1)]);
    });
    h.el('path', { d: smooth(top.concat(bot.reverse())) + ' Z', 'class': 'kit-fire-out kit-m-firejet', 'data-may-cross': '', 'data-no-contain': '' }, jt);
    var C2 = [[0.1, 0.1], [0.22, 0.45], [0.38, 0.5], [0.52, 0.32], [0.62, 0]], ct = [], cb = [];
    C2.forEach(function (q) { var x = q[0] * len, y = lift(x); ct.push([x, y - q[1] * R]); cb.push([x, y + q[1] * R]); });
    h.el('path', { d: smooth(ct.concat(cb.reverse())) + ' Z', 'class': 'kit-fire-core', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, jt);   // the hot core inside the jet: its outer tongue carries the contrast
    lx = -8; ly = 30; la = 'end';
  } else {
    h.el('rect', { x: 1, y: 0, width: w - 2, height: 12, 'class': 'kit-pool' }, g);
    h.el('path', { d: 'M-2 -2 V16 H' + (w + 2) + ' V-2', 'class': 'kit-fire-pan' }, g);
    grow = h.el('g', {}, body);
    /* 2.52.0, as a real pool fire burns: broad billows of uneven height leaning one way (it was a comb of equal teeth),
       a white-hot glow along the pool, smoke above the flames where the core runs out of air */
    var n = Math.max(3, Math.round(w / 34)), sp = w / n, top = p.height || Math.min(w * 0.55, 140);
    [[0.3, -0.9, 0.17, 0.2], [0.56, -1, 0.21, 0.22], [0.8, -0.86, 0.15, 0.17]].forEach(function (q) {      // the smoke, over the tips
      h.el('ellipse', { cx: (w * q[0]).toFixed(1), cy: (top * q[1]).toFixed(1), rx: (w * q[2]).toFixed(1), ry: (top * q[3]).toFixed(1),
                        'class': 'kit-fire-smoke kit-m-smoke kit-m-fog', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, grow);
    });
    for (i = 0; i < n; i++) {
      var cx = (i + 0.5) * sp, s = top * (0.5 + 0.5 * rnd()), wd = sp * (0.85 + 0.6 * rnd()), lean = s * (0.1 + 0.08 * rnd());
      wd = Math.min(wd, cx + 2, w + 2 - cx); lean = Math.min(lean, w - cx - 4);   // the fire stays over its pool
      var c2 = h.el('g', { 'class': 'kit-fire-tongue', style: 'animation-delay:' + (-rnd() * 0.4).toFixed(2) + 's' }, grow);
      h.el('path', { d: 'M' + (cx - wd).toFixed(1) + ' 0 C' + (cx - wd * 1.15).toFixed(1) + ' ' + (-s * 0.35).toFixed(1) + ' ' + (cx - wd * 0.2 + lean * 0.4).toFixed(1) + ' ' + (-s * 0.6).toFixed(1) + ' ' + (cx + lean).toFixed(1) + ' ' + (-s).toFixed(1) +
        ' C' + (cx + wd * 0.45 + lean * 0.5).toFixed(1) + ' ' + (-s * 0.62).toFixed(1) + ' ' + (cx + wd * 1.1).toFixed(1) + ' ' + (-s * 0.28).toFixed(1) + ' ' + (cx + wd).toFixed(1) + ' 0 Z', 'class': 'kit-fire-out kit-m-fire', 'data-may-cross': '', 'data-no-contain': '' }, c2);
      h.el('path', { d: 'M' + (cx - wd * 0.5).toFixed(1) + ' 0 C' + (cx - wd * 0.6).toFixed(1) + ' ' + (-s * 0.15).toFixed(1) + ' ' + (cx - wd * 0.2 + lean * 0.2).toFixed(1) + ' ' + (-s * 0.35).toFixed(1) + ' ' + (cx + lean * 0.5).toFixed(1) + ' ' + (-s * 0.5).toFixed(1) +
        ' C' + (cx + wd * 0.3 + lean * 0.3).toFixed(1) + ' ' + (-s * 0.35).toFixed(1) + ' ' + (cx + wd * 0.6).toFixed(1) + ' ' + (-s * 0.15).toFixed(1) + ' ' + (cx + wd * 0.5).toFixed(1) + ' 0 Z', 'class': 'kit-fire-core', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, c2);   // the hot core inside each billow
    }
    h.el('ellipse', { cx: w / 2, cy: -2, rx: w / 2, ry: 7, 'class': 'kit-fire-glow kit-m-soft', 'data-low-contrast': '', 'data-may-cross': '', 'data-no-contain': '' }, grow);
    lx = w / 2; ly = 36;
  }
  var lg = p.label || p.state ? h.label(fig, g, {}, '') : null;
  var nl = p.label ? h.lines(lg, { x: lx, y: ly, 'text-anchor': la, 'class': 'kit-cap' }, p.label) : 0;
  var st = p.state ? h.el('text', { x: lx, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': la, 'class': 'kit-state' }, lg) : null;
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    grow.setAttribute('transform', jet ? 'scale(' + Math.max(k, 0.001).toFixed(3) + ' ' + (0.5 + 0.5 * k).toFixed(3) + ')' : 'scale(1 ' + Math.max(k, 0.001).toFixed(3) + ')');
    grow.style.opacity = k > 0.02 ? '1' : '0';
    if (!st) h.gone(lg, k <= 0.02);                // with a state line its words stay: "OUT" is what it says then
    g.classList.toggle('kit-fire-on', k > 0.05);
    if (st) st.textContent = k > 0.05 ? 'BURNING' : 'OUT';
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  look: 'diagram',
  why: 'M13 fire types: a pool fire (a spilled liquid burning over its surface - wide, low flames) and a jet fire (gas leaking under pressure and burning as a long tongue from the leak point)',
  value: '0 out .. 1 full; kind pool (width w, optional height) or jet (length, angle in degrees above horizontal), the flame stands on the surface (pool) or grows out of the leak point (jet); a jet is drawn on a 90 px pipe end unless stub: false',
  css: '.kit-fire-out{opacity:.95}' +                         // its fill is the kit's fire (2.52.0): white-hot, orange, red tips
    '.kit-fire-smoke{opacity:.55}.kit-fire-glow{fill:var(--mat-fire-hot);opacity:.7}' +
    '.kit-fire-core{fill:var(--mat-fire-hot);opacity:.85}' +
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
/* 2.63.2 - the standard flammability composition diagram (ISGOTT fig. 1-1 / SIGTTO layout - the one the instructors teach
   from; IGF review 2026-10-21, M06 3/21 and M07 2/18 "the flammability diagram is wrong"): OXYGEN % by volume across
   (0..22, air at 20.9), FUEL gas % by volume up (0..20); the air line from air up to the left (fuel added to air:
   oxygen = air x (1 - fuel / 100)); the flammable zone the triangle on it between the LFL and the UFL with its nose at the
   limiting oxygen (the spec's `lfl`, `ufl`, `nose`, methane 5 / 15 % and [12 %, 6 %] by default - or its own `zone`);
   the line of critical dilution with air from air past the nose to the fuel axis; inerting is a path along the oxygen
   axis below the zone, gas-freeing a path back to air under that line (the spec's `path`). Points are [oxygen %, fuel %];
   null in a path lifts the pen. Before 2.63.2 the part drew fuel 0..100 across and oxygen up, so the zone was a sliver:
   a spec in that form (points [fuel %, oxygen %], xmax 100 - or `axes: 'fuel-o2'`) is read into this layout, its steps
   stopping where they did (the path's length is measured as the old part measured it). Layout: the IGF original
   course's hand-built `flammability_o2` (M06 / M07 kit_parts.js, 2026-10-22). */
KIT.define('flammability', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 380, ht = p.h || 250;
  /* the old form, told by its numbers: a scale past 25, a point more than 22 across, a path from [0, 21], or a zone whose
     corners lie on the old air line (oxygen = 21 x (1 - fuel / 100)) rather than on this one */
  function oldForm() {
    if (p.axes) return p.axes === 'fuel-o2';
    if ((p.xmax || 0) > 25) return true;
    var a = p.air || 21, all = (p.zone || []).concat(p.path || []).concat([].concat.apply([], (p.lines || []).map(function (l) { return l.pts || []; })));
    if (all.some(function (q) { return q && q[0] > 22.5; })) return true;
    if (p.path && p.path[0] && p.path[0][0] === 0 && Math.abs(p.path[0][1] - a) < 0.3 && !(p.ymax > 20)) return true;
    var o = 0, n = 0;
    (p.zone || []).forEach(function (q) {
      if (Math.abs(q[1] - a * (1 - q[0] / 100)) < 0.3) o++;
      if (Math.abs(q[0] - a * (1 - q[1] / 100)) < 0.3) n++;
    });
    return o > n;
  }
  var old = oldForm(), air = p.air || (old ? 21 : 20.9);
  var X = old ? Math.max(22, Math.ceil(air)) : p.xmax || 22, Y = old ? 20 : p.ymax || 20;
  var words = p.words || ['NOT FLAMMABLE', 'FLAMMABLE'], byLegs = p.by === 'legs';
  function pt(q) { return q == null ? null : old ? [h.clamp(q[1], 0, X), h.clamp(q[0], 0, Y)] : [h.clamp(q[0], 0, X), h.clamp(q[1], 0, Y)]; }
  function sx(v) { return v / X * w; }
  function sy(v) { return ht - v / Y * ht; }
  function xy(q) { return [sx(q[0]), sy(q[1])]; }
  function list(a) { return a.map(function (q) { q = xy(q); return q[0].toFixed(1) + ' ' + q[1].toFixed(1); }); }
  function onAir(f) { return [air * (1 - f / 100), f]; }
  var zone = p.zone ? p.zone.map(pt) : p.zone === false ? [] : [onAir(+p.lfl || 5), onAir(+p.ufl || 15), p.nose || [12, 6]];
  var v, i, xn = [], yn = [];
  g.classList.add('kit-flammability-o2');
  h.el('path', { d: 'M0 0 V' + ht + ' H' + w, 'class': 'kit-flammability-axis' }, g);
  for (v = 0; v <= X + 1e-9; v += (old ? 0 : p.xevery) || 5) {
    h.el('line', { x1: sx(v), x2: sx(v), y1: ht, y2: ht + 6, 'class': 'kit-tickl' }, g);
    if (v > 0) h.el('line', { x1: sx(v), x2: sx(v), y1: 0, y2: ht, 'class': 'kit-flammability-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);   // a quiet grid
    if (Math.abs(v - air) > 1.6) xn.push(h.el('text', { x: sx(v), y: ht + 22, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, String(v)));
  }
  h.el('line', { x1: sx(air), x2: sx(air), y1: ht, y2: ht + 6, 'class': 'kit-tickl' }, g);
  /* "air" a little lower than the numbers: every path starts at air, and its dot sits on the axis above the word */
  var at = h.el('text', { x: sx(air), y: ht + 28, 'text-anchor': 'middle', 'class': 'kit-tick' }, g, p.airTick || 'air');
  fig.fit(function (k) { at.setAttribute('y', (ht + 18 + 10 * k).toFixed(1)); });
  for (v = 0; v <= Y + 1e-9; v += (old ? 0 : p.yevery) || 5) {
    h.el('line', { x1: -6, x2: 0, y1: sy(v), y2: sy(v), 'class': 'kit-tickl' }, g);
    if (v > 0) h.el('line', { x1: 0, x2: w, y1: sy(v), y2: sy(v), 'class': 'kit-flammability-grid', 'data-may-cross': '', 'data-may-overlap': '', 'data-low-contrast': '' }, g);
    yn.push(h.el('text', { x: -15, y: sy(v) + 4.5, 'text-anchor': 'end', 'class': 'kit-tick' }, g, String(v)));
  }
  /* 2.63.0 - the scale's numbers keep their distance from the axis as the 12.5 px floor grows them (k): at a fixed
     ht + 22 their tops came down onto the axis and its ticks (IGF M06 s03, M07 s02: 11-20 text-zone findings a figure) */
  fig.fit(function (k) {
    xn.forEach(function (t) { t.setAttribute('y', (ht + 12 + 10 * k).toFixed(1)); });
    yn.forEach(function (t) { t.setAttribute('x', (-9 - 6 * k).toFixed(1)); });
  });
  /* the old form's labels named fuel across and oxygen up - its words for the axes are the other way round now */
  var xcap = h.label(fig, g, { x: w / 2, y: ht + 48, 'text-anchor': 'middle', 'class': 'kit-cap' }, (old ? p.ylabel : p.xlabel) || '% oxygen in the mixture');
  fig.fit(function (k) {                         // the axis name stays under the scale's numbers as both grow
    [].forEach.call(xcap.querySelectorAll('text'), function (t) { t.setAttribute('y', (ht + Math.max(48, 16 + 23 * k)).toFixed(1)); });
  });
  h.label(fig, g, { x: 0, y: -14, 'text-anchor': 'start', 'class': 'kit-cap' }, (old ? p.xlabel : p.ylabel) || '% fuel gas');
  /* the flammable zone: a polygon of [oxygen %, fuel %] points - the LFL and UFL on the air line and the nose */
  if (zone.length > 2) {
    h.el('polygon', { points: list(zone).join(' '), 'class': 'kit-flammability-zone', 'data-no-contain': '', 'data-low-contrast': '' }, g);
  }
  var top = onAir(Y);
  h.el('line', { x1: sx(air), y1: sy(0), x2: sx(top[0]), y2: sy(Y), 'class': 'kit-flammability-air', 'data-may-cross': '' }, g);
  /* the line of critical dilution with air: from air past the zone's nose (the zone's corner with the least fuel for the
     oxygen it takes away) to the fuel axis - a mixture above it passes through the zone when air is let in */
  var crit = null;
  if (zone.length > 2 && p.dilution !== false) {
    var m = Math.min.apply(null, zone.filter(function (q) { return q[0] < air - 0.01; }).map(function (q) { return q[1] / (air - q[0]); }));
    if (isFinite(m) && m > 0) {
      crit = air * m <= Y ? [0, air * m] : [air - Y / m, Y];
      h.el('line', { x1: sx(crit[0]), y1: sy(crit[1]), x2: sx(air), y2: sy(0), 'class': 'kit-flammability-crit', 'data-may-cross': '' }, g);
      if (p.dilutionLabel !== '') {
        var cm = [crit[0] + (air - crit[0]) * 0.18, crit[1] * 0.82];
        h.label(fig, g, { x: sx(cm[0]) + 4, y: sy(cm[1]) - 8, 'text-anchor': 'start', 'class': 'kit-cap' }, p.dilutionLabel || 'critical dilution with air');
      }
    }
  }
  (p.lines || []).forEach(function (ln) {
    var pts = ln.pts.map(pt), e = ln.at ? pt(ln.at) : pts[pts.length - 1], vert = pts[0][0] === e[0] && !ln.at;
    if (vert) e = [e[0], Y * 0.9];
    h.el('polyline', { points: list(pts).join(' '), 'class': 'kit-flammability-line', 'data-may-cross': '' }, g);
    /* an oxygen line's words go on the side with more room: left of it, or between it and the air line */
    var left = ln.side ? ln.side === 'left' : !vert || sx(e[0]) > sx(onAir(e[1])[0]) - sx(e[0]);
    /* beside an upright line long words take two rows (the room is between two upright lines, not along one) */
    var said = ln.label || '';
    if (vert && said.length > 18 && said.indexOf('\n') < 0) {
      var cut = said.split(' ').reduce(function (a, wd, n, all) { var l = all.slice(0, n).join(' ').length; return Math.abs(l - said.length / 2) < Math.abs(a - said.length / 2) ? l : a; }, 0);
      if (cut > 0) said = said.slice(0, cut) + '\n' + said.slice(cut + 1);
    }
    if (said) h.label(fig, g, { x: sx(e[0]) + (left ? -8 : 8), y: sy(e[1]) + (vert ? 4.5 : -9), 'text-anchor': left ? 'end' : 'start', 'class': 'kit-cap' }, said);
  });
  (p.notes || []).forEach(function (n) {
    var q = pt(n.at);
    h.label(fig, g, { x: sx(q[0]), y: sy(q[1]), 'text-anchor': n.anchor || 'middle', 'class': 'kit-cap' }, n.text);
  });
  if (p.airLabel) { var al = onAir(Y * 0.8); h.label(fig, g, { x: sx(al[0]) + 10, y: sy(al[1]), 'text-anchor': 'start', 'class': 'kit-cap' }, p.airLabel); }
  if (p.zoneLabel && zone.length > 2) {
    var cx = 0, cy = 0;
    zone.forEach(function (q) { cx += q[0] / zone.length; cy += q[1] / zone.length; });
    h.label(fig, g, { x: sx(cx), y: sy(cy) + 4.5, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.zoneLabel);
  }
  /* the state sits above the plot at the right of the title row - inside the plot it read as the name of a region */
  var st = h.label(fig, g, {}, '');
  var stText = h.el('text', { x: w, y: -14, 'text-anchor': 'end', 'class': 'kit-state kit-flammability-st' }, st);
  /* the path in legs; a null lifts the pen (the point jumps, no trail). Its length is measured on the screen - or, for a
     spec in the old form, on the old part's own scale, so a step's value stops the point where it stopped before */
  var raw = p.path || [onAir(0), onAir(Y)], legs = [], last = null, lift = false, total = 0, cum = [0];
  var oX = p.xmax || 100, oY = p.ymax || 25;
  raw.forEach(function (q) {
    if (q == null) { lift = true; return; }
    if (last) {
      var a = xy(pt(last)), b = xy(pt(q)), d = old ? Math.sqrt(Math.pow((q[0] - last[0]) / oX * w, 2) + Math.pow((q[1] - last[1]) / oY * ht, 2))
        : Math.sqrt(Math.pow(b[0] - a[0], 2) + Math.pow(b[1] - a[1], 2));
      legs.push({ a: a, b: b, jump: lift, d: lift ? 0 : d, len: Math.sqrt(Math.pow(b[0] - a[0], 2) + Math.pow(b[1] - a[1], 2)) || 1 });
      total += lift ? 0 : d; cum.push(total);
    }
    last = q; lift = false;
  });
  total = total || 1;
  legs.forEach(function (s, k) {
    var sc = (p.segClass || {})[String(k)];      // {leg: 'bad' | 'air'}: the forbidden leg amber, the way back to air green
    if (!s.jump) s.el = h.el('line', { x1: s.a[0].toFixed(1), y1: s.a[1].toFixed(1), x2: s.b[0].toFixed(1), y2: s.b[1].toFixed(1), 'class': 'kit-flammability-trail' + (sc ? ' kit-flammability-trail-' + sc : ''), 'data-may-cross': '' }, g);
  });
  var dot = h.el('circle', { r: 7, 'class': 'kit-flammability-dot', 'data-may-cross': '' }, g);
  part.__fl = { zone: zone, air: [[air, 0], top], crit: crit, sx: sx, sy: sy, old: old, X: X, Y: Y };   // for the tests
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
  /* value: 0..1 of the path's length - or, with by: 'legs', how many legs are done (1.5 = halfway along the second) */
  part.render = function (val) {
    var s = byLegs ? null : h.clamp(val, 0, 1) * total, x = legs.length ? legs[0].a[0] : sx(air), y = legs.length ? legs[0].a[1] : sy(0);
    legs.forEach(function (L, k) {
      var f = byLegs ? h.clamp(val - k, 0, 1) : L.d > 0 ? h.clamp((s - cum[k]) / L.d, 0, 1) : s > cum[k] + 1e-6 ? 1 : 0;
      if (L.el) {                                    // a leg not yet begun is hidden: its round cap alone draws a dot
        L.el.setAttribute('stroke-dasharray', (f * L.len).toFixed(1) + ' ' + (L.len * 2).toFixed(1));
        L.el.style.visibility = f > 0 ? '' : 'hidden';
      }
      if (f > 0) { x = L.a[0] + f * (L.b[0] - L.a[0]); y = L.a[1] + f * (L.b[1] - L.a[1]); }
    });
    dot.setAttribute('cx', x.toFixed(1)); dot.setAttribute('cy', y.toFixed(1));
    var hot = inZone(x, y);
    g.classList.toggle('kit-flammability-hot', hot);
    stText.textContent = hot ? words[1] : words[0];
  };
}, {
  family: 'charts',
  status: 'kit', merged_from: "IGF Basic M05-M15",
  course: 'IGF Basic', module: 'M05-M15', made: '2026-10-16',
  look: 'diagram',
  why: 'M06 the flammability diagram for methane and M07 the inerting path that stays out of the zone (plan: the media plans of modules 6 and 7); 2.63.2 redrawn as the standard ISGOTT / SIGTTO flammability composition diagram (oxygen across, fuel up, the air line, the zone between the LFL and UFL, the line of critical dilution with air) after the instructors\' review (IGF M06 3/21, M07 2/18)',
  value: '0..1 how far the point has travelled along path (a list of [oxygen %, fuel %], null lifts the pen), or with by: \'legs\' how many legs are done; the zone lights amber while the point is inside it',
  css: '.kit-flammability-axis{fill:none;stroke:var(--faint-d);stroke-width:2}' +
    '.kit-flammability-crit{stroke:var(--dim-d);stroke-width:2;stroke-dasharray:3 5}' +
    '.kit-flammability-grid{stroke:var(--faint-d);stroke-width:1;stroke-dasharray:2 6;opacity:.7}' +
    '.kit-flammability-air{stroke:var(--dim-d);stroke-width:2.5}' +
    '.kit-flammability-zone{fill:var(--faint-d);fill-opacity:.25;stroke:var(--dim-d);stroke-width:2;stroke-dasharray:6 4;stroke-linejoin:round}' +
    '.kit-flammability-hot .kit-flammability-zone{fill:var(--amber);fill-opacity:.4;stroke:var(--amber);stroke-dasharray:none}' +
    '.kit-flammability-line{fill:none;stroke:var(--cold);stroke-width:2;stroke-dasharray:8 5}' +
    '.kit-flammability-trail{fill:none;stroke:var(--blue);stroke-width:4;stroke-linecap:round;stroke-linejoin:round}' +
    '.kit-flammability-trail-bad{stroke:var(--amber)}.kit-flammability-trail-air{stroke:var(--good-d)}' +
    '.kit-flammability-dot{fill:var(--txt-d);stroke:var(--blue);stroke-width:3}' +
    '.kit-flammability-hot .kit-flammability-dot{stroke:var(--amber)}' +
    '.kit-flammability-hot .kit-flammability-st{fill:var(--amber)}',
  /* example data is methane (the part's own default zone: LFL 5 %, UFL 15 %, the nose at 12 % oxygen); a course gives its
     own lfl / ufl / nose or zone, lines and path from its sources. Air straight to gas crosses the zone; inerting first
     (along the oxygen axis), then the gas; gas-freeing - inert gas until the fuel is under the critical line, then air */
  example: { size: [560, 360], parts: [
    { id: 'F', type: 'flammability', x: 70, y: 40, w: 440, h: 250, by: 'legs', zoneLabel: 'flammable zone', airLabel: 'air line',
      path: [[20.9, 0], [18.81, 10], [16.72, 20], null, [20.9, 0], [3, 0], [2.4, 20], [0.24, 2], [20.9, 0]],
      segClass: { '0': 'bad', '1': 'bad', '6': 'air' } } ],
    steps: [ { title: 'Gas added to air: between 5 and 15 % the mixture can burn', play: [['F', 1, 1600, 0, 'linear']] },
             { title: 'More gas: above 15 % it is too rich', play: [['F', 2, 1200, 0, 'linear']] },
             { title: 'Inerting first: the oxygen goes down, no fuel yet', play: [['F', 4, 1800, 0, 'linear']] },
             { title: 'Then the gas goes in, left of the zone', play: [['F', 5, 1500, 0, 'linear']] },
             { title: 'Gas-freeing: inert gas until the fuel is under the line, then air', play: [['F', 7, 2400, 0, 'linear']] } ] }
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
  look: 'diagram',
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
  h.el('path', { d: p.d, 'class': 'kit-hose-body kit-ms-rubber' }, g);      // 2.52.0: rubber, its steel couplings bolted on
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
    /* 2.52.0: each end as a real hose end fitting, square to the hose - its bolted flange, the swaged steel ferrule, a
       stepped bend restrictor onto the hose; and a pale marker band at a quarter and three quarters of its length */
    [[a0, a1], [b0, b1]].forEach(function (c) {
      var ang = Math.atan2(c[1].y - c[0].y, c[1].x - c[0].x) * 180 / Math.PI;
      var col = h.equip(g), fg = h.el('g', { 'data-may-cross': '', transform: 'translate(' + c[0].x.toFixed(1) + ' ' + c[0].y.toFixed(1) + ') rotate(' + ang.toFixed(1) + ')' }, col);
      h.body('rect', { x: 14, y: -12.5, width: 6, height: 25, rx: 2 }, fg, { mat: 'steel', shade: 'cyl' });
      h.body('rect', { x: 3, y: -14.5, width: 12, height: 29, rx: 2 }, fg, { mat: 'steel', shade: 'cyl' });
      h.flange(fg, 0, 0, 0, 36, 6);
      [-1, 1].forEach(function (s) { h.el('circle', { cx: 0, cy: s * 7, r: 1.3, 'class': 'kit-m-bolt' }, fg); });
    });
    [0.25, 0.75].forEach(function (f) {
      var q0 = reach.getPointAtLength(L * f), q1 = reach.getPointAtLength(Math.min(L, L * f + 4));
      var ang = Math.atan2(q1.y - q0.y, q1.x - q0.x) * 180 / Math.PI;
      h.el('rect', { x: -2, y: -12, width: 4, height: 24, 'class': 'kit-m-reflect', 'data-may-cross': '',
                     transform: 'translate(' + q0.x.toFixed(1) + ' ' + q0.y.toFixed(1) + ') rotate(' + ang.toFixed(1) + ')' }, g);
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
  look: 'equipment',
  why: 'M13 the hand hoses used for bunkering and sampling, M14 the bunkering hose in the ESD chain between shore and ship (plan: media plans of modules 13 and 14)',
  value: 'flow 0 still .. 1 fast, as a pipe; the second value "<id>.fill" is 0..1 the fluid front advancing along d, 1..2 the hose emptying (set "empty": true to start dry). The spec checker only knows pipe.fill - hose.fill is new',
  css: '.kit-hose-body{fill:none;stroke-width:24}' +
    '.kit-hose-rib{fill:none;stroke:var(--mat-edge);stroke-width:24;stroke-dasharray:2 9;opacity:.45}' +
    '.kit-hose-bore{fill:none;stroke:var(--deep);stroke-width:11}' +
    '.kit-hose-fluid{fill:none;stroke:var(--cold);stroke-width:8;opacity:.55}' +
    '.kit-hose-gas .kit-hose-fluid{stroke:var(--txt-d);opacity:.22}' +
    '.kit-hose-gas .kit-flow{stroke:var(--txt-d);stroke-dasharray:2 6;stroke-linecap:round;stroke-width:3}' +
    '',
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
  /* 2.52.0: the steel header with its end caps, each outlet a steel stub down to a bolted flange; a blind flange bolted
     on until a rubber hose is coupled */
  var eq = h.equip(g);
  h.body('rect', { x: 0, y: 0, width: w, height: hh, rx: 6 }, eq, { mat: 'steel', shade: 'cyl' });
  (n > 1 ? [sp, w - sp] : []).forEach(function (x) { h.flange(eq, x - 2.5, hh / 2, 0, hh + 10, 5); h.flange(eq, x + 2.5, hh / 2, 0, hh + 10, 5); });   // the header's bolted joints, between outlets
  h.body('rect', { x: -8, y: -6, width: 10, height: hh + 12, rx: 2 }, eq, { mat: 'cast', shade: 'box' });
  h.body('rect', { x: w - 2, y: -6, width: 10, height: hh + 12, rx: 2 }, eq, { mat: 'cast', shade: 'box' });
  if (p.label) h.label(fig, g, { x: w / 2, y: -20, 'text-anchor': 'middle', 'class': 'kit-h' }, p.label);
  var made = outs.map(function (o, i) {
    var cx = sp * (i + 0.5), og = h.el('g', { 'class': 'kit-manifold-out' }, g), oe = h.equip(og), vy = hh + drop * 0.45;
    h.body('rect', { x: cx - 8, y: hh, width: 16, height: drop }, oe, { mat: 'steel', shade: 'cylv' });
    h.body('ellipse', { cx: cx, cy: vy, rx: 10, ry: 7 }, oe, { mat: 'cast', shade: 'round' });                // its block valve
    h.body('rect', { x: cx + 9, y: vy - 1.5, width: 3, height: 3 }, oe, { mat: 'steel' });
    h.body('rect', { x: cx + 11, y: vy - 1.5, width: 15, height: 3, rx: 1 }, oe, { mat: 'steel', shade: 'box' });   // and its lever
    h.flange(oe, cx, hh + drop + 3.5, 90, 36, 7);
    var hose = h.el('rect', { x: cx - 10, y: y0, width: 20, height: 0, 'class': 'kit-manifold-hose kit-m-rubber', 'data-may-cross': '' }, oe);
    var coll = h.el('rect', { x: cx - 14, y: y0, width: 28, height: 9, rx: 2, 'class': 'kit-manifold-collar kit-m-steel', 'data-may-cross': '' }, oe);
    var blind = h.el('g', { 'data-may-cross': '' }, oe);                               // a blind flange, bolted on
    h.el('rect', { x: cx - 18, y: y0, width: 36, height: 9, rx: 2, 'class': 'kit-manifold-blind kit-m-paintl' }, blind);
    [-13, -5, 5, 13].forEach(function (bx) { h.el('circle', { cx: cx + bx, cy: y0 + 4.5, r: 1.3, 'class': 'kit-m-bolt' }, blind); });
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
  look: 'equipment',
  why: 'M14 and M15 the bunker station: the manifold header with its liquid and vapour-return connections, each blanked with a blind flange until a hose is connected (plan: media plans of modules 14 and 15)',
  value: '0..n how many outlets are connected, counted from the left: outlet k grows its hose while the value goes from k to k+1; the others keep their blind flange',
  css: '.kit-manifold-blind{stroke:var(--mat-stem);stroke-width:1.5}' +
    '.kit-manifold-hose{stroke:var(--cold);stroke-width:2}' +
    '.kit-manifold-collar{opacity:0}' +
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
  /* 2.52.0: steel pipe on painted saddles, bolted flanges, the spool a steel pipe of its own, blind flanges painted */
  var eq = h.equip(g);
  function pipe(x0, x1, at) {
    h.body('rect', { x: x0, y: -t / 2, width: x1 - x0, height: t }, at, { mat: 'steel', shade: 'cyl' });
    return h.el('rect', { x: x0 + 3, y: -t / 2 + 5, width: Math.max(1, x1 - x0 - 6), height: t - 10, 'class': 'kit-liquid' }, at);
  }
  function flg(x, at) { h.flange(at, x + fl / 2, 0, 0, fh, fl); }
  function support(x) {                                 // a pipe saddle under the pipe
    h.body('path', { d: 'M' + (x - 6) + ' ' + t / 2 + ' L' + (x + 6) + ' ' + t / 2 + ' L' + (x + 16) + ' ' + (t / 2 + 16) + ' L' + (x - 16) + ' ' + (t / 2 + 16) + ' Z' }, eq, { mat: 'paint', shade: 'box' });
  }
  pipe(0, gx - fl, eq);
  var rightFill = pipe(gx + sl + fl, w, eq);
  [18, gx - fl - 18, gx + sl + fl + 18, w - 18].forEach(support);
  flg(gx - fl, eq); flg(gx + sl, eq);
  var sg = h.el('g', { 'class': 'kit-spool-piece-spool' }, g), se = h.equip(sg);
  h.body('rect', { x: gx + fl, y: -t / 2, width: sl - 2 * fl, height: t }, se, { mat: 'steel', shade: 'cyl' });
  var sFill = h.el('rect', { x: gx + fl, y: -t / 2 + 5, width: sl - 2 * fl, height: t - 10, 'class': 'kit-liquid' }, se);
  flg(gx, se); flg(gx + sl - fl, se);
  var bl = h.el('rect', { x: gx, y: -fh / 2, width: 12, height: fh, rx: 2, 'class': 'kit-spool-piece-blind kit-m-paintl', 'data-may-cross': '' }, g);
  var br = h.el('rect', { x: gx + sl - 12, y: -fh / 2, width: 12, height: fh, rx: 2, 'class': 'kit-spool-piece-blind kit-m-paintl', 'data-may-cross': '' }, g);
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
  look: 'equipment',
  why: 'M07 segregation of a gas line: two flanged pipe ends with a removable spool between them - fitted, the line is connected; removed, a blank flange on each end keeps the gas from passing (plan: media plan of module 7)',
  value: '1 the spool is fitted and the line connected, 0 the spool is removed (it lifts away) and a blank flange is fitted on each end - SEGREGATED; between, it moves',
  css: '.kit-spool-piece-blind{stroke:var(--mat-stem);stroke-width:1.5}' +
    '.kit-spool-piece-seg .kit-spool-piece-st{fill:var(--blue)}',
  example: { size: [640, 190], parts: [
    { id: 'K', type: 'tank', x: 8, y: 54, w: 132, h: 100, label: 'LNG tank', value: 0.7 },
    { id: 'S', type: 'spool_piece', x: 140, y: 104, w: 370, t: 30, spool: 130, lift: 46, label: 'gas supply line', left: 'tank side', right: 'engine side', spoolLabel: 'spool piece', value: 1 },
    { id: 'E', type: 'engine', x: 510, y: 69, w: 122, h: 70, cylinders: 3, label: 'dual-fuel engine', value: 1 } ],
    steps: [ { title: 'The spool is removed and each end blanked - no gas reaches the engine', play: [['S', 0, 1800], ['E', 0, 300, 1800]] },
             { title: 'The spool is fitted again - the line is connected', play: [['S', 1, 1800], ['E', 1, 300, 1800]] } ] }
});
/* end kit-part */
/* kit-part: airlock */
KIT.define('airlock', function (fig, part, g, p) {
  /* 2.63.2 (item 12, the instructors' review of IGF Basic M02 s10 "Getting into the fuel spaces"): the access to a fuel space
     had no part - the slide drew an airlock as a white box with two bars. Two gas-tight steel doors in two bulkheads with the
     space between them, the SAFE side on one hand and the HAZARDOUS side on the other, each named and tinted (green, and the
     hazardous zone's amber); a door open is a gap in the bulkhead and its leaf swung into the airlock, a door shut is the
     leaf in the bulkhead with its dogs. Value 0 both shut, 1 the safe-side door open, 2 the hazardous-side door open: the one
     that is open shuts before the other opens, so the two are never open together (the words say so). */
  var h = KIT.h, w = p.w || 130, H = p.h || 124, bt = 10, T = 8;
  var sd = p.side != null ? p.side : 92, sd2 = p.hazardW != null ? p.hazardW : sd;      // the two sides' widths: "safeW" / "hazardW" (0 draws no side)
  sd = p.safeW != null ? p.safeW : sd;
  var W = sd + w + sd2, M = 2 * sd + w, dh = Math.min(p.door || 64, H - 2 * T - 14), top = H - T - dh, L = Math.min(38, (w - 2 * bt) * 0.42);
  var words = p.words || ['BOTH DOORS SHUT', 'ONE DOOR OPEN'];
  var safe = sd > 0 ? h.el('rect', { x: 0, y: 0, width: sd, height: H, rx: 4, 'class': 'kit-airlock-safe' }, g) : null;
  var haz = sd2 > 0 ? h.el('rect', { x: sd + w, y: 0, width: sd2, height: H, rx: 4, 'class': 'kit-airlock-haz' }, g) : null;
  var room = h.el('rect', { x: sd + bt, y: T, width: w - 2 * bt, height: H - 2 * T, 'class': 'kit-airlock-room' }, g);   // the space between the doors
  /* the steel: the deck under all three spaces, the airlock's deckhead, and the two bulkheads over their doorways */
  var eq = h.equip(g, { shadow: false });
  h.body('rect', { x: 0, y: H - T, width: W, height: T }, eq, { mat: 'deck', shade: 'box' });
  h.body('rect', { x: sd, y: 0, width: w, height: T }, eq, { mat: 'paint', shade: 'box' });
  [sd, sd + w - bt].forEach(function (x) {
    h.body('rect', { x: x, y: T, width: bt, height: top - T }, eq, { mat: 'paint', shade: 'box' });
  });
  function door(mirror) {                              // the safe-side door as drawn; the other is the same, turned about the airlock
    var dg = h.el('g', mirror ? { transform: 'translate(' + M + ' 0) scale(-1 1)' } : {}, eq);
    var hole = h.el('rect', { x: sd, y: top, width: bt, height: dh, 'class': 'kit-airlock-hole' }, dg);   // the doorway, dark once the leaf has swung
    var leaf = h.body('path', { d: '' }, dg, { mat: 'steel', shade: 'box' });
    var dogs = [0.2, 0.5, 0.8].map(function (f) { return h.el('circle', { cx: sd + bt / 2, cy: top + dh * f, r: 1.7, 'class': 'kit-m-bolt' }, dg); });
    return function (o) {                              // o 0 shut .. 1 swung open into the airlock
      var xh = sd + bt, xf = xh - bt + (bt + L) * o, e = 6 * o;
      h.reshape(leaf, { d: 'M' + xh + ' ' + top + ' L' + xf.toFixed(1) + ' ' + (top + e).toFixed(1) + ' L' + xf.toFixed(1) + ' ' + (H - T - e).toFixed(1) + ' L' + xh + ' ' + (H - T) + ' Z' });
      hole.style.opacity = h.clamp(o * 4, 0, 1).toFixed(2);
      dogs.forEach(function (d) { d.style.opacity = (1 - h.clamp(o * 3, 0, 1)).toFixed(2); });
    };
  }
  var doors = [door(false), door(true)];
  /* the words: both sides named inside their tint, the airlock inside its own walls; the layout keeps each clear and puts one
     outside with a leader line when the type has grown past its room */
  if (safe && p.safe !== false) h.label(fig, g, { x: sd / 2, y: 24, 'text-anchor': 'middle', 'class': 'kit-h' }, p.safe || 'safe\nside', { inside: true, within: safe });
  if (haz && p.hazard !== false) h.label(fig, g, { x: sd + w + sd2 / 2, y: 24, 'text-anchor': 'middle', 'class': 'kit-h' }, p.hazard || 'hazardous\nside', { inside: true, within: haz });
  if (p.label !== false) h.label(fig, g, { x: sd + w / 2, y: 24, 'text-anchor': 'middle', 'class': 'kit-h' }, p.label || 'airlock', { inside: true, within: room });
  var lg = h.label(fig, g, {}, '');
  var st = p.state === false ? null : h.el('text', { x: sd + w / 2, y: H + 22, 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 2), a = c <= 1 ? c : h.clamp(3 - 2 * c, 0, 1), b = h.clamp(2 * (c - 1.5), 0, 1);
    doors[0](a); doors[1](b);
    var open = a > 0.02 || b > 0.02;
    if (st) st.textContent = open ? words[1] : words[0];
    g.classList.toggle('kit-airlock-open', open);
  };
}, {
  family: 'spaces',
  status: 'kit', merged_from: "IGF review 2026-10-21",
  course: 'IGF Basic', module: 'M02', made: '2026-10-22',
  look: 'equipment',
  why: 'M02 s10 getting into the fuel spaces: no direct access from a safe area into a hazardous one - an airlock, two gas-tight doors with a space between them that are never open together',
  value: '0 both doors shut, 1 the safe-side door open, 2 the hazardous-side door open; from 1 to 2 the first door shuts before the second opens (two doors never open at once); options w h door, side (or safeW / hazardW: 0 draws no side), safe / hazard / label (the words; false for none), state false (no BOTH DOORS SHUT / ONE DOOR OPEN under it), words',
  css: '.kit-airlock-safe{fill:var(--good-d);fill-opacity:.26;stroke:var(--good-d);stroke-width:2}' +
    '.kit-airlock-haz{fill:var(--amber);fill-opacity:.3;stroke:var(--amber);stroke-width:2;stroke-dasharray:6 4}' +
    '.kit-airlock-room{fill:var(--cold);fill-opacity:.12}' +
    '.kit-airlock-hole{fill:var(--mat-hole);stroke:var(--dim-d);stroke-width:1.5;stroke-dasharray:3 3;opacity:0}' +
    '.kit-airlock-open .kit-state{fill:var(--txt-d)}',
  example: { size: [340, 186], parts: [
    { id: 'A', type: 'airlock', x: 13, y: 20 } ],
    steps: [ { title: 'The safe-side door opens - the person steps in, the other door stays shut', play: [['A', 1, 1400]] },
             { title: 'The safe-side door shuts, then the hazardous-side door opens', play: [['A', 2, 2400]] },
             { title: 'Both doors shut again', play: [['A', 0, 1800]] } ] }
});
/* end kit-part */
/* kit-part: hatch */
KIT.define('hatch', function (fig, part, g, p) {
  /* 2.63.2 (item 12): the bolted hatch in the open deck over a tank connection space - a steel cover bolted down on its
     coaming; opened, it lifts clear and the opening shows. (x, y) is the top left of the cover when it is shut. */
  var h = KIT.h, w = p.w || 64, t = 8, ch = 12, n = Math.max(3, Math.round(w / 15)), lift = p.lift || 24;
  var words = p.words || ['BOLTED', 'OPEN'];
  var eq = h.equip(g, { shadow: false });
  h.el('rect', { x: 5, y: t, width: w - 10, height: ch, 'class': 'kit-hatch-opening' }, g);                    // the opening under the cover
  h.body('rect', { x: 0, y: t, width: 6, height: ch, rx: 1 }, eq, { mat: 'cast', shade: 'box' });                // the coaming
  h.body('rect', { x: w - 6, y: t, width: 6, height: ch, rx: 1 }, eq, { mat: 'cast', shade: 'box' });
  var cover = h.el('g', {}, eq);
  h.body('rect', { x: -3, y: 0, width: w + 6, height: t, rx: 2 }, cover, { mat: 'steel', shade: 'box' });         // the cover plate
  for (var i = 0; i < n; i++) h.el('circle', { cx: 3 + (w - 6) * (i + 0.5) / n, cy: t / 2, r: 1.8, 'class': 'kit-m-bolt' }, cover);   // its bolts
  if (p.label) h.label(fig, g, { x: w / 2, y: -10, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  var lg = h.label(fig, g, {}, '');
  var st = p.state === false ? null : h.el('text', { x: w / 2, y: t + ch + 18, 'text-anchor': 'middle', 'class': 'kit-state' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 1);
    cover.setAttribute('transform', 'translate(0 ' + (-lift * c).toFixed(1) + ')');
    cover.style.opacity = (1 - 0.35 * c).toFixed(2);
    if (st) st.textContent = c > 0.5 ? words[1] : words[0];
    g.classList.toggle('kit-hatch-open', c > 0.5);
  };
}, {
  family: 'spaces',
  status: 'kit', merged_from: "IGF review 2026-10-21",
  course: 'IGF Basic', module: 'M02', made: '2026-10-22',
  look: 'equipment',
  why: 'M02 s10 the tank connection space is entered from the open deck through a bolted hatch (the space with the hatch then counts as hazardous)',
  value: '0 bolted shut, 1 the cover lifted clear and the opening showing; options w, lift, label, state false, words',
  css: '.kit-hatch-opening{fill:var(--mat-hole)}.kit-hatch-open .kit-state{fill:var(--txt-d)}',
  example: { size: [240, 116], parts: [
    { id: 'H', type: 'hatch', x: 40, y: 36, w: 160, label: 'hatch in the open deck' } ],
    steps: [ { title: 'The bolts are undone and the cover lifted - the space is open', play: [['H', 1, 1400]] },
             { title: 'Bolted down again', play: [['H', 0, 1200]] } ] }
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
    h.el('rect', { x: 0, y: 0, width: w, height: 52, 'class': 'kit-liquid kit-m-lng', 'data-no-contain': '' }, g);
    h.el('line', { x1: 0, x2: w, y1: 0, y2: 0, 'class': 'kit-surface kit-m-lngs', 'data-may-cross': '' }, g);
    h.label(fig, g, { x: lx, y: 31, 'text-anchor': 'start', 'class': 'kit-h' }, p.insideLabel);
    y = 52;
  }
  var made = layers.map(function (l, i) {
    var lh = l.h || def[Math.min(i, def.length - 1)].h, k = kind(l), lg = h.el('g', { 'class': 'kit-tank-wall-layer' }, g), y1 = y;
    /* 2.52.0: each layer cut through in its material - the steel plates, the cellular foam; the barrier keeps its line */
    if (k === 'barrier') h.el('rect', { x: 0, y: y1, width: w, height: lh, 'class': 'kit-tank-wall-barrier' }, lg);
    else h.body('rect', { x: 0, y: y1, width: w, height: lh }, lg, { mat: k === 'foam' ? 'foam' : 'steel', shade: 'box', hatch: k !== 'foam' });
    if (k === 'foam') for (var px = 50; px < w; px += 50) h.el('line', { x1: px, x2: px, y1: y1 + 2, y2: y1 + lh - 2, 'class': 'kit-tank-wall-joint', 'data-low-contrast': '' }, lg);   // its panels' joints
    if (k === 'barrier') h.body('rect', { x: 0, y: y1 + lh / 2 - 2, width: w, height: 4 }, lg, { mat: 'steel' });   // the barrier's foil
    var wash = h.el('rect', { x: 0, y: y1, width: w, height: lh, 'class': 'kit-tank-wall-wash', 'data-may-overlap': '' }, lg);
    h.label(fig, lg, { x: lx, y: y1 + lh / 2 + 4.5, 'text-anchor': 'start', 'class': 'kit-cap kit-tank-wall-nm' }, l.label || '');
    y += lh;
    return { g: lg, wash: wash };
  });
  if (p.outsideLabel) {
    var sea = /sea|water|ocean/i.test(p.outsideLabel);                   // the sea outside the hull is drawn as the sea (2.52.0)
    h.el('rect', { x: 0, y: y, width: w, height: 48, 'class': sea ? 'kit-tank-wall-sea kit-m-sea' : 'kit-tank-wall-out', 'data-no-contain': '' }, g);
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
  look: 'equipment',
  why: 'M07 the wall of a cryogenic LNG tank, cut away: inner tank, insulation, secondary barrier and hull, named from the cargo outward (plan: media plan of module 7)',
  value: '0..n: layer k (counted from the cargo side, 1..n) is picked out while the value is about k, and 0 picks none; layers:[{label, kind steel|foam|barrier, h}] renames or drops layers',
  css: '.kit-tank-wall-barrier{fill:var(--deep-2);stroke:var(--cold);stroke-width:2.5}' +
    '.kit-tank-wall-wash{fill:var(--blue);opacity:0}' +
    '.kit-tank-wall-out{fill:var(--deep);stroke:var(--faint-d);stroke-width:1.5;stroke-dasharray:6 5}' +
    '.kit-tank-wall-sea{stroke:var(--mat-reflect);stroke-width:1.5}.kit-tank-wall-joint{stroke:var(--mat-edge-clad);stroke-width:1.5}' +
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
    h.el('rect', { x: 0, y: S, width: w, height: T, 'class': 'kit-spill-water kit-m-sea', 'data-low-contrast': '', 'data-no-contain': '' }, g);   // the sea, lit at its surface (2.52.0)
    var d = 'M0 ' + S, nw = Math.floor(w / 30);
    for (i = 0; i < nw; i++) d += ' q 7.5 -6 15 0 t 15 0';
    if (w - nw * 30 > 0.5) d += ' H' + w;                                 // the last part-wave is a straight run to the edge
    h.el('path', { d: d, 'class': 'kit-spill-wave', 'data-may-cross': '' }, g);
  } else {
    h.body('rect', { x: 0, y: S, width: w, height: T }, g, { mat: 'deck', shade: 'box' });                 // the painted deck plate (2.52.0)
    for (i = 30; i < w; i += 60) h.el('path', { d: 'M' + i + ' ' + (S + T) + ' V' + (S + 34), 'class': 'kit-spill-beam' }, g);   // the stiffeners under the deck plate
  }
  var nz = Math.max(10, Math.min(46, S - 78));                           // the nozzle, shortened when the box is
  var nzl = h.equip(g);                                                  // the leaking pipe end and its flange, in steel
  h.body('rect', { x: fx - 7, y: S - 78 - nz, width: 14, height: nz }, nzl, { mat: 'steel', shade: 'cylv' });
  h.body('rect', { x: fx - 15, y: S - 78, width: 30, height: 7, rx: 2 }, nzl, { mat: 'steel', shade: 'box' });   // its flange, bolted
  [-1, 1].forEach(function (sd) { h.el('circle', { cx: fx + sd * 11.5, cy: S - 74.5, r: 1.3, 'class': 'kit-m-bolt' }, nzl); });
  var stream = h.el('line', { x1: fx, x2: fx, y1: S - 71, y2: S - 1, 'class': 'kit-spill-stream', 'data-may-cross': '' }, g);
  var pool = h.el('path', { d: 'M' + fx + ' ' + S, 'class': 'kit-spill-pool kit-m-lng', 'data-may-cross': '' }, g);
  var fr = [-0.82, -0.52, -0.22, 0.12, 0.42, 0.72, 0.95];
  /* 2.52.0: LNG boiling off makes a dense, low white fog that hugs the surface and rolls outward (it was drawn as squiggles
     that read as steam or wires); the liquid flashes where the stream lands; the pool seethes with fine bubbles */
  var flash = h.el('ellipse', { cx: fx, cy: S - 5, rx: 11, ry: 6, 'class': 'kit-spill-flash kit-m-vapour kit-m-fog', 'data-low-contrast': '', 'data-may-cross': '' }, g);
  fr.forEach(function (f, j) {
    bubs.push(h.el('circle', { r: 1.4 + 0.5 * (j % 3), 'class': 'kit-spill-bub', 'data-low-contrast': '', 'data-may-cross': '' }, g));
    var wg = h.el('g', {}, g);
    h.el('ellipse', { cx: 0, cy: -9, rx: 20, ry: 10, 'class': 'kit-spill-wisp kit-m-vapour kit-m-fog', 'data-low-contrast': '', 'data-may-cross': '' }, wg);
    wisps.push(wg);
  });
  var lg = h.label(fig, g, {}, ''), ly = S + T + 30, nl = 0;       // under the plate or the water: its name, then the word for what the pool does
  if (p.label) nl = h.lines(lg, { x: w / 2, y: ly, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  var st = h.el('text', { x: w / 2, y: ly, dy: (nl * 1.28).toFixed(2) + 'em', 'text-anchor': 'middle', 'class': 'kit-state kit-spill-st' }, lg);
  part.render = function (v) {
    var c = h.clamp(v, 0, 1), r = reach * (water ? 1 - Math.pow(1 - c, 2.2) : Math.pow(c, 0.8)), boil = h.clamp((c - 0.45) / 0.4, 0, 1);
    stream.style.opacity = c > 0.01 ? '1' : '0';
    flash.style.opacity = c > 0.01 ? '0.8' : '0';
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
  look: 'diagram',
  why: 'M15 LNG spilt on the deck and on the water: a pool spreads from the leak (far wider and thinner on water) and boils off in vapour - why the deck is steel and why water is not a safe place for a spill (plan: media plan of module 15)',
  value: '0..1 how far the pool has spread from the leak; from about 0.5 it boils (it seethes, and a low white vapour fog rolls over it); surface "deck" or "water" (drawn as water, the pool spreads wider and boils harder); drawn inside its box x..x+w, y..y+h (2.49.2): the nozzle top at y, h 206 (deck) or 240 (water) unless the spec gives a shorter one, which shortens the nozzle',
  css: '.kit-spill-water{fill-opacity:.85;stroke:none}' +
    '.kit-spill-wave{fill:none;stroke:var(--mat-reflect);stroke-width:2.5}' +
    '.kit-spill-beam{fill:none;stroke:var(--faint-d);stroke-width:3}' +
    '.kit-spill-stream{stroke:var(--cold);stroke-width:3;opacity:0}' +
    '.kit-spill-pool{stroke:var(--mat-lng-surf);stroke-width:1.5;stroke-linejoin:round}' +
    '.kit-spill-bub{fill:var(--mat-vapour);opacity:0}' +
    '.kit-spill-flash{opacity:0}.kit-spill-wisp{opacity:.6}' +
    '.kit-spill-live .kit-spill-wisp{transform-box:fill-box;transform-origin:50% 100%;animation:kit-spill-roll 1.6s ease-in-out infinite alternate}' +
    '@keyframes kit-spill-roll{0%{opacity:.45;transform:scale(1,1)}100%{opacity:.7;transform:scale(1.12,1.08)}}',
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
  look: 'diagram',
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
  look: 'diagram',
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
  /* 2.52.0: the steel conduit down from the deckhead, the fitting's cast cap; an Ex fitting's heavy cast guard */
  var eq = h.equip(g, { shadow: false });
  h.el('line', { x1: 0, x2: 0, y1: -28, y2: -8, 'class': 'kit-lamp-stem kit-ms-steel' }, eq);       // the cable down from the deckhead
  h.body('path', { d: 'M-12 -8 H12 V2 H-12 Z' }, eq, { mat: 'cast', shade: 'box' });               // the fitting
  var rays = h.el('g', { 'class': 'kit-lamp-rays' }, g);
  for (i = 0; i < 7; i++) {
    var a = 25 + i * 21.67, q0 = h.polar(r0, a), q1 = h.polar(r0 + 12, a);
    h.el('line', { x1: q0[0].toFixed(1), y1: (cy + q0[1]).toFixed(1), x2: q1[0].toFixed(1), y2: (cy + q1[1]).toFixed(1) }, rays);
  }
  h.el('circle', { cx: 0, cy: cy, r: 16, 'class': 'kit-lamp-bulb', 'data-no-contain': '' }, g);   // the glass: its fitting meets it by nature
  /* 2.52.0: an ordinary fitting has a light wire guard over its glass; an explosion-protected (Ex) one is a heavy bolted
     cast housing with its cable glands, a flange ring, thick glass and a steel cage - the enclosure that holds any spark in */
  if (!ex) h.el('path', { d: 'M-15 4 C-20 30 -8 40 0 40 C8 40 20 30 15 4 M0 4 V40', 'class': 'kit-lamp-guard', 'data-may-cross': '', 'data-no-contain': '' }, g);
  else {
    g.classList.add('kit-lamp-exg');
    var hx = h.equip(g);
    [-12, 12].forEach(function (x) { h.body('rect', { x: x - 3, y: -13, width: 6, height: 6, rx: 1 }, hx, { mat: 'steel', shade: 'box' }); });   // cable glands
    h.body('rect', { x: -22, y: -8, width: 44, height: 18, rx: 3 }, hx, { mat: 'cast', shade: 'box' });
    [-17, -6, 6, 17].forEach(function (x) { h.el('circle', { cx: x, cy: -4, r: 1.3, 'class': 'kit-m-bolt' }, hx); });
    h.body('ellipse', { cx: 0, cy: 11, rx: 21, ry: 3.5 }, hx, { mat: 'steel', shade: 'box' });
    h.el('path', { d: 'M-19 12 C-27 34 -12 47 0 47 C12 47 27 34 19 12 M-9 13 C-12 32 -6 46 0 47 M9 13 C12 32 6 46 0 47', 'class': 'kit-lamp-cage', 'data-may-cross': '', 'data-no-contain': '' }, g);
  }
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
  look: 'equipment',
  why: 'M06 ignition sources: electrical equipment (a light fitting, a switch, a motor) is an ignition source in a gas-dangerous space unless it is explosion-protected - an ordinary lamp and an Ex-protected one side by side',
  value: '0 off, 1 lit (the glass fills and its rays show); option ex: true draws the heavy explosion-protected enclosure round the glass',
  css: '.kit-lamp-stem{stroke-width:4;stroke-linecap:round}' +
    '.kit-lamp-bulb{fill:var(--deep);stroke:var(--dim-d);stroke-width:2.5}' +
    '.kit-lamp-on .kit-lamp-bulb{fill:var(--txt-d);stroke:var(--txt-d)}' +
    '.kit-lamp-rays line{stroke:var(--txt-d);stroke-width:3;stroke-linecap:round;stroke-dasharray:6 5}' +
    '.kit-lamp-guard{fill:none;stroke:var(--dim-d);stroke-width:1.4}.kit-lamp-cage{fill:none;stroke:var(--kit-steel);stroke-width:3;stroke-linecap:round}' +
    '.kit-light .kit-lamp-cage{stroke:var(--dim-d)}' +
    '.kit-lamp-exg .kit-lamp-bulb{stroke-width:4.5}',
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
    /* friction (2.52.0, as it looks): a tool scraping a steel edge throws hot particles one way - a spray of glowing streaks
       that fall away under gravity, from a white-hot point of contact */
    var eqf = h.equip(g, { shadow: false });
    h.body('rect', { x: -44, y: 3, width: 54, height: 7, rx: 1 }, eqf, { mat: 'steel', shade: 'box' });   // the steel edge being scraped
    var lens = [30, 22, 36, 26, 33, 20, 35, 27, 31, 24, 34];
    for (i = 0; i < 11; i++) {
      var a = -100 + i * 8.5, q0 = h.polar(5, a), q1 = h.polar(lens[i], a), drop = lens[i] * 0.22;
      var mx = (q0[0] + q1[0]) / 2, my = (q0[1] + q1[1]) / 2 - 2;
      h.el('path', { d: 'M' + q0[0].toFixed(1) + ' ' + q0[1].toFixed(1) + ' Q' + mx.toFixed(1) + ' ' + my.toFixed(1) + ' ' + q1[0].toFixed(1) + ' ' + (q1[1] + drop).toFixed(1),
                     'class': 'kit-spark-ray' }, flick);
      if (i % 3 === 1) h.el('circle', { cx: q1[0].toFixed(1), cy: (q1[1] + drop).toFixed(1), r: 1.8, 'class': 'kit-spark-hot' }, flick);
    }
    h.el('circle', { cx: 0, cy: 0, r: 8, 'class': 'kit-spark-glow kit-m-soft', 'data-low-contrast': '' }, flick);   // the glow round the contact
    h.el('circle', { cx: 0, cy: 0, r: 4, 'class': 'kit-spark-hot' }, flick);
  } else {
    /* electric (2.52.0, as it looks): an arc jumps between two steel terminals - an irregular, branched path, a blue halo
       round a bright core - from (0, 0) to the point "to" */
    var len = Math.sqrt(to[0] * to[0] + to[1] * to[1]) || 1, ux = to[0] / len, uy = to[1] / len, amp = Math.min(14, len * 0.16), d = 'M0 0', pts = [];
    var AMP = [0.7, -1, 0.45, -0.85, 0.95, -0.5, 0.6];
    for (i = 1; i < 8; i++) {
      var f = len * i / 8, s = AMP[i - 1];
      pts.push([ux * f - uy * amp * s, uy * f + ux * amp * s]);
      d += ' L' + pts[i - 1][0].toFixed(1) + ' ' + pts[i - 1][1].toFixed(1);
    }
    d += ' L' + to[0] + ' ' + to[1];
    [[2, 0.9, -1], [5, 0.7, 1]].forEach(function (b) {                       // two short branches off the arc
      var q = pts[b[0]], e = [q[0] + (ux * 0.5 - uy * b[2]) * amp * b[1] * 1.6, q[1] + (uy * 0.5 + ux * b[2]) * amp * b[1] * 1.6];
      d += ' M' + q[0].toFixed(1) + ' ' + q[1].toFixed(1) + ' L' + e[0].toFixed(1) + ' ' + e[1].toFixed(1);
    });
    h.el('path', { d: d, 'class': 'kit-spark-halo kit-m-soft', 'data-low-contrast': '' }, flick);   // the glow round the arc: its core carries it
    h.el('path', { d: d, 'class': 'kit-spark-bolt' }, flick);
    h.el('path', { d: d, 'class': 'kit-spark-core', 'data-low-contrast': '' }, flick);
    var eqe = h.equip(g, { shadow: false });                                  // the two terminals stay drawn at rest
    [[0, 0], to].forEach(function (c) { h.body('circle', { cx: c[0], cy: c[1], r: 5.5 }, eqe, { mat: 'steel', shade: 'round' }); });
    cx = to[0] / 2; cy = to[1] / 2;
  }
  var lb = p.label ? h.label(fig, g, { x: cx, y: cy - (fric ? 44 : 26), 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label) : null;
  part.render = function (v) {
    var k = h.clamp(v, 0, 1);
    burst.setAttribute('transform', 'translate(' + cx + ' ' + cy + ') scale(' + (0.4 + 0.6 * k).toFixed(3) + ') translate(' + (-cx) + ' ' + (-cy) + ')');
    burst.style.opacity = k > 0.02 ? '1' : '0';
    h.gone(lb, k <= 0.02);
    g.classList.toggle('kit-spark-on', k > 0.05);
  };
}, {
  family: 'gas-fire-machinery',
  status: 'kit', merged_from: "IGF Basic M06",
  course: 'IGF Basic', module: 'M06', made: '2026-10-16',
  look: 'diagram',
  why: 'M06 ignition sources: an electric spark (a switch or a loose contact) and a frictional spark (a tool, a chain or a rope scraping steel) - the small energy that lights a gas-air mixture',
  value: '0 no spark, 1 the spark at full; kind "electric" (default: an arc jumps from this point to to: [dx, dy]) or "friction" (hot particles thrown from this point, off a steel edge); the two terminals of an electric spark stay drawn at rest',
  css: '.kit-spark-halo{fill:none;stroke:var(--cold);stroke-width:10;opacity:.35;stroke-linejoin:round;stroke-linecap:round}' +
    '.kit-spark-bolt{fill:none;stroke:var(--cold);stroke-width:4;stroke-linejoin:round;stroke-linecap:round}' +
    '.kit-spark-core{fill:none;stroke:var(--mat-vapour);stroke-width:1.6;stroke-linejoin:round;stroke-linecap:round}' +
    '.kit-spark-ray{fill:none;stroke:var(--mat-fire-mid);stroke-width:2.2;stroke-linecap:round}.kit-light .kit-spark-ray{stroke:var(--mat-flame-edge)}' +
    '.kit-spark-hot{fill:var(--mat-fire-hot)}.kit-light .kit-spark-hot{fill:var(--mat-flame-edge)}' +
    '.kit-spark-glow{fill:var(--mat-fire-mid);opacity:.6}' +
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
  look: 'diagram',
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
/* kit-part: tank_type */
KIT.define('tank_type', function (fig, part, g, p) {
  var h = KIT.h, w = p.w || 150, ht = p.h || 110, kind = p.kind || 'c', cx = w / 2, cy = ht / 2;
  var eq = h.equip(g);
  var bar = h.el('g', { 'class': 'kit-tank-type-bar', opacity: 0 }, g);      // the secondary barrier, brought in by the value
  function barEl(tag, at) {                                                   // a dark halo under the dashed line: it reads on steel as well as on the panel
    var halo = {}, k;
    for (k in at) { halo[k] = at[k]; }
    halo['class'] = 'kit-tank-type-halo';
    halo['data-low-contrast'] = '';                                           // a dark halo, quiet on purpose
    h.el(tag, halo, bar);
    at['class'] = 'kit-tank-type-barline';
    at['data-low-contrast'] = '';                                             // the dark halo under it keeps it legible on steel
    return h.el(tag, at, bar);
  }
  if (kind === 'a') {
    // type A: a prismatic tank of flat plates, chamfered corners, stiffeners on its walls
    var a = 14, x0 = 14, y0 = 10, x1 = w - 14, y1 = ht - 14;
    h.body('path', { d: 'M' + (x0 + a) + ' ' + y0 + ' H' + (x1 - a) + ' L' + x1 + ' ' + (y0 + a) + ' V' + (y1 - a) + ' L' + (x1 - a) + ' ' + y1 + ' H' + (x0 + a) + ' L' + x0 + ' ' + (y1 - a) + ' V' + (y0 + a) + ' Z' }, eq, { mat: 'clad', shade: 'box' });
    [0.33, 0.66].forEach(function (f) {
      h.el('line', { x1: x0 + 6, x2: x1 - 6, y1: y0 + (y1 - y0) * f, y2: y0 + (y1 - y0) * f, 'class': 'kit-tank-type-rib' }, eq);
    });
    barEl('rect', { x: x0 - 8, y: y0 - 7, width: x1 - x0 + 16, height: y1 - y0 + 14, rx: 4 });   // a complete barrier all round
    h.body('rect', { x: 8, y: y1 + 8, width: w - 16, height: 8, rx: 2 }, eq, { mat: 'deck', shade: 'box' });
  } else if (kind === 'b') {
    // type B: a sphere on a cylindrical skirt at its equator
    var r = Math.min(cx - 18, (ht - 20) / 2);
    var sy = (ht - 14) / 2 + 4;
    h.body('rect', { x: cx - r * 0.55, y: sy, width: r * 1.1, height: r + 8, rx: 2 }, eq, { mat: 'steel', shade: 'cylv' });
    h.body('circle', { cx: cx, cy: sy, r: r }, eq, { mat: 'clad', shade: 'round' });
    h.body('rect', { x: 8, y: sy + r + 8, width: w - 16, height: 8, rx: 2 }, eq, { mat: 'deck', shade: 'box' });
    barEl('path', { d: 'M' + (cx - r - 10) + ' ' + (sy + r * 0.6) + ' V' + (sy + r + 4) + ' H' + (cx - r * 0.62) +
                        ' M' + (cx + r + 10) + ' ' + (sy + r * 0.6) + ' V' + (sy + r + 4) + ' H' + (cx + r * 0.62) });   // two drip trays either side of the skirt   // a drip tray: a partial barrier
  } else if (kind === 'membrane') {
    // membrane tank: a thin corrugated metal layer inside insulation, carried by the hull
    var m0 = 10, m1 = 10, mw = w - 20, mh = ht - 24;
    h.body('rect', { x: m0, y: m1, width: mw, height: mh, rx: 5 }, eq, { mat: 'hull', shade: 'box' });
    h.body('rect', { x: m0 + 7, y: m1 + 7, width: mw - 14, height: mh - 14, rx: 3 }, eq, { mat: 'foam', shade: 'box' });
    var zig = 'M' + (m0 + 12) + ' ' + (m1 + 12);
    var n = Math.floor((mw - 24) / 8);
    for (var i = 0; i < n; i++) { zig += ' l4 -3 l4 3'; }
    h.el('path', { d: zig, 'class': 'kit-tank-type-membrane' }, eq);
    h.el('path', { d: 'M' + (m0 + 12) + ' ' + (m1 + mh - 12) + ' H' + (m0 + mw - 12), 'class': 'kit-tank-type-membrane' }, eq);
    h.el('path', { d: 'M' + (m0 + 12) + ' ' + (m1 + 12) + ' V' + (m1 + mh - 12) + ' M' + (m0 + mw - 12) + ' ' + (m1 + 12) + ' V' + (m1 + mh - 12), 'class': 'kit-tank-type-membrane' }, eq);
    barEl('rect', { x: m0 + 3, y: m1 + 3, width: mw - 6, height: mh - 6, rx: 3 });   // the second membrane: a complete barrier
    h.body('rect', { x: 4, y: m1 + mh + 6, width: w - 8, height: 8, rx: 2 }, eq, { mat: 'deck', shade: 'box' });
  } else {
    // type C: a horizontal pressure vessel on two saddles - no secondary barrier
    var bh = Math.min(ht - 38, (w - 32) * 0.55);                  // always a horizontal vessel, whatever the box
    var cy0 = 14 + ((ht - 38) - bh) / 2;                            // centred in the room the other tanks fill
    h.body('rect', { x: 16, y: cy0, width: w - 32, height: bh, rx: bh / 2 }, eq, { mat: 'clad', shade: 'cyl' });
    [0.28, 0.72].forEach(function (f) {
      h.body('rect', { x: 16 + (w - 32) * f - 8, y: cy0 + bh - 4, width: 16, height: 14, rx: 2 }, eq, { mat: 'steel', shade: 'box' });
    });
    h.body('rect', { x: 8, y: cy0 + bh + 10, width: w - 16, height: 8, rx: 2 }, eq, { mat: 'deck', shade: 'box' });
  }
  if (p.label) h.label(fig, g, { x: cx, y: ht + 14, 'text-anchor': 'middle', 'class': 'kit-cap' }, p.label);
  part.render = function (v) {
    bar.setAttribute('opacity', h.clamp(v, 0, 1));
  };
}, {
  family: 'cutaways',
  status: 'kit', merged_from: "IGF Basic M02",
  look: 'equipment',
  course: 'IGF Basic', module: 'M02', made: '2026-10-21',
  why: 'M02 s07 and q05: the IMO tank types A, B and C and a membrane tank drawn side by side, the secondary barrier brought in by the value',
  value: 'how much of the secondary barrier is drawn, 0..1',
  css: '.kit-tank-type-halo{fill:none;stroke:var(--deep);stroke-width:7;stroke-linejoin:round}' +
    '.kit-tank-type-barline{fill:none;stroke:var(--cold);stroke-width:3;stroke-dasharray:7 4;stroke-linecap:round}' +
    '.kit-tank-type-rib{stroke:var(--mat-edge-clad);stroke-width:1.5}' +
    '.kit-tank-type-membrane{fill:none;stroke:var(--mat-edge-steel);stroke-width:2;stroke-linejoin:round}',
  example: { size: [640, 190], parts: [
    { id: 'A', type: 'tank_type', kind: 'a', x: 10, y: 20, label: 'type A' },
    { id: 'B', type: 'tank_type', kind: 'b', x: 170, y: 20, label: 'type B' },
    { id: 'C', type: 'tank_type', kind: 'c', x: 330, y: 20, label: 'type C' },
    { id: 'M', type: 'tank_type', kind: 'membrane', x: 490, y: 20, label: 'membrane' } ],
    steps: [ { title: 'The secondary barrier', play: [['A', 1, 800], ['B', 1, 800], ['M', 1, 800]] } ] }
});
/* end kit-part */
/* kit-parts: end */
