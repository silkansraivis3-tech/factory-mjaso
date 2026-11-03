/* ==========================================================================
   gb_hmi.js - the ship's own screens inside a task (needs gb_lab.js first).

   WHY IT EXISTS. A trainee who has worked these tasks must find their way on
   the training simulator and in a real cargo control room. So the screens a
   task shows follow the simulator's own conventions (Wärtsilä LCHS TechSim
   LPG Tanker, Trainee Manual §4.2, §6.4, §6.9) - tags, pipe colours, valve
   symbols, hydraulic release (HVK), panels that open on a tap, valves that
   take time to move, alarms that flash and sound until acknowledged - drawn
   in the factory's dark look. Written once here, so no task invents its own.

     var h = GBHMI.create(el, { page: 'CMS · TANK 0001', box: [1000, 600] });
     h.pipe(id, 'M.. ', 'liquid' | 'vapour' | 'condensate' | 'nitrogen' | 'water')
     h.setPipe(id, { live, flow, rev, cold })
     h.valve('PL0126', { x, y, dir: 'h'|'v', kind: 'onoff'|'reg', hvk: 'HVK-0101', travel: s, what, label })
     h.hvk('HVK-0101', { x, y, what })            hydraulic pressure for a group of valves
     h.readout('P0107', { x, y, unit, digits, al, ah, alarm: 'text' })   h.set('P0107', 4.2)
     h.tank('T-0001', { x, y, w, h, name, level })                       h.level('T-0001', 62)
     h.pump('PM-0001', { x, y, what, onStart, onStop, lampsAt: [x, y] })                  h.trip('PM-0001', 'HIGH PRESSURE')
     h.esd({ x, y, onPress })                    h.blank('BL-PS-V', { x, y, dir })
     h.alarm(id, text) / h.clear(id) / h.acked() h.pos(tag) h.isOpen(tag) h.reach(start, edges)
     h.on('change', fn(tag, obj))                every settled change, for the task's own physics

   Plain ES5, nothing fetched. Every control is a tap (56 px or more on the
   tablet); nothing is a hidden gesture.
   ========================================================================== */
(function (W, D) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg';

  function svgEl(tag, attrs, parent) {
    var e = D.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function txt(parent, x, y, s, cls, anchor) {
    var t = svgEl('text', { x: x, y: y, 'class': cls, 'text-anchor': anchor || 'middle' }, parent);
    t.textContent = s;
    return t;
  }
  function esc(s) { return W.GBLab ? GBLab.esc(s) : String(s); }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }

  function create(host, opt) {
    opt = opt || {};
    var box = opt.box || [1000, 600];
    var root = D.createElement('div');
    root.className = 'hm';
    root.innerHTML =
      '<div class="hm-top"><i class="hm-dot"></i><span class="hm-page">' + esc(opt.page || 'CMS') + '</span>' +
      (opt.sub ? '<span>' + esc(opt.sub) + '</span>' : '') +
      '<div class="hm-alarm"><span class="hm-n"></span><b></b><button type="button">ACK</button></div></div>';
    var scroll = D.createElement('div');
    scroll.className = 'hm-scroll';
    root.appendChild(scroll);
    var svg = svgEl('svg', { 'class': 'hm-svg', viewBox: '0 0 ' + box[0] + ' ' + box[1], preserveAspectRatio: 'xMidYMid meet' }, scroll);
    var gPipe = svgEl('g', {}, svg), gFlow = svgEl('g', {}, svg), gObj = svgEl('g', {}, svg);
    host.appendChild(root);
    // a phone shows the screen at a size a finger can use, and it scrolls sideways - as the
    // simulator's own screens pan; on a tablet it simply fills the space
    function fit() {
      var w = scroll.clientWidth, hh = scroll.clientHeight;
      if (!w || !hh) return;
      // never smaller than 80 % of its drawn size on a phone: text stays readable (13 px tags
      // become 10-11 px), and the screen pans both ways instead of shrinking
      var k = Math.min(w / box[0], hh / box[1]), narrow = w < 700 && k < 0.8;
      root.className = 'hm' + (narrow ? ' narrow' : '');
      var s = Math.max(0.8, hh / box[1]);
      root.style.setProperty('--hm-w', Math.round(box[0] * s) + 'px');
      root.style.setProperty('--hm-h', Math.round(box[1] * s) + 'px');
    }
    W.addEventListener('resize', function () { fit(); });
    if (W.ResizeObserver) new ResizeObserver(fit).observe(scroll);
    setTimeout(fit, 0);

    var objs = {}, pipes = {}, handlers = { change: [], alarm: [] }, panel = null, sel = null;
    var alarms = [], hornT = 0;

    function emit(name, a, b) { handlers[name].forEach(function (f) { f(a, b); }); }

    /* ---- pipes ------------------------------------------------------------- */
    function pipe(id, d, medium) {
      var p = svgEl('path', { d: d, 'class': 'hm-pipe ' + (medium || 'liquid') }, gPipe);
      var f = svgEl('path', { d: d, 'class': 'hm-flow' }, gFlow);
      pipes[id] = { p: p, f: f, medium: medium || 'liquid' };
      return pipes[id];
    }
    function setPipe(id, s) {
      var o = pipes[id];
      if (!o) return;
      o.p.setAttribute('class', 'hm-pipe ' + o.medium + (s.live || s.flow ? ' live' : '') + (s.cold ? ' cold' : ''));
      o.f.setAttribute('class', 'hm-flow' + (s.flow ? ' on' : '') + (s.rev ? ' rev' : ''));
    }

    /* ---- the panel that opens next to what was tapped --------------------- */
    function closePanel() {
      if (panel && panel.parentNode) panel.parentNode.removeChild(panel);
      panel = null;
      if (sel) { var r = sel.g.querySelector('.hm-ring'); if (r) r.parentNode.removeChild(r); sel.g.classList.remove('hm-sel'); }
      sel = null;
    }
    function openPanel(o, html, wire) {
      closePanel();
      sel = o;
      o.g.classList.add('hm-sel');
      svgEl('circle', { cx: o.x, cy: o.y, r: 34, 'class': 'hm-ring' }, o.g);
      panel = D.createElement('div');
      panel.className = 'hm-panel';
      panel.innerHTML = '<button type="button" class="hm-x" aria-label="Close">&times;</button>' + html;
      root.appendChild(panel);
      panel.querySelector('.hm-x').addEventListener('click', closePanel);
      wire(panel);
      // next to the object, kept inside the screen
      var m = svg.getScreenCTM(), rr = root.getBoundingClientRect();
      // the panel belongs to the screen, not to the scrolled drawing
      var sx = m.a * o.x + m.e - rr.left, sy = m.d * o.y + m.f - rr.top;
      var pw = panel.offsetWidth, ph = panel.offsetHeight;
      var left = sx + 44 + pw < rr.width ? sx + 44 : sx - 44 - pw;
      panel.style.left = clamp(left, 6, rr.width - pw - 6) + 'px';
      panel.style.top = clamp(sy - ph / 2, 56, rr.height - ph - 6) + 'px';
    }
    root.addEventListener('click', function (e) {
      if (panel && !panel.contains(e.target) && !(e.target.closest && e.target.closest('.hm-obj'))) closePanel();
    });

    function hit(g, x, y, r) { svgEl('circle', { cx: x, cy: y, r: r || 40, 'class': 'hm-hit' }, g); }
    function label(g, x, y, s, where, dx) {
      var p = { below: [x, y + 46], above: [x, y - 32], left: [x - 46, y + 5, 'end'], right: [x + 46, y + 5, 'start'] }[where || 'below'];
      return txt(g, p[0] + (dx || 0), p[1], s, 'hm-tag', p[2]);
    }

    /* ---- valves: on/off or regulating, with travel time and hydraulics ----- */
    function valve(tag, o) {
      o = o || {};
      var v = { type: 'valve', tag: tag, x: o.x, y: o.y, kind: o.kind || 'onoff', hvk: o.hvk || null, travel: o.travel || 3,
                pos: o.pos || 0, target: o.pos || 0, what: o.what || '', fault: false };
      var g = svgEl('g', { 'class': 'hm-obj hm-v', 'data-tag': tag, 'data-tap': '1' }, gObj);
      v.g = g;
      hit(g, o.x, o.y);
      var s = 13, d = o.dir === 'v'
        ? 'M' + (o.x - s) + ' ' + (o.y - s - 2) + ' h' + 2 * s + ' l' + -2 * s + ' ' + (2 * s + 4) + ' h' + 2 * s + ' z'
        : 'M' + (o.x - s - 2) + ' ' + (o.y - s) + ' v' + 2 * s + ' l' + (2 * s + 4) + ' ' + -2 * s + ' v' + 2 * s + ' z';
      // the actuator - the simulator's T on a remote valve, a wheel stem on a manual one
      if (o.dir === 'v') { svgEl('path', { d: 'M' + (o.x + s + 2) + ' ' + o.y + ' h12 M' + (o.x + s + 14) + ' ' + (o.y - 7) + ' v14', 'class': 'hm-act' }, g); }
      else { svgEl('path', { d: 'M' + o.x + ' ' + (o.y - s - 2) + ' v-12 M' + (o.x - 8) + ' ' + (o.y - s - 14) + ' h16', 'class': 'hm-act' }, g); }
      v.body = svgEl('path', { d: d, 'class': 'hm-body' }, g);
      v.lamp = svgEl('circle', { cx: o.dir === 'v' ? o.x - s - 10 : o.x + s + 10, cy: o.dir === 'v' ? o.y : o.y + s + 4, r: 6, 'class': 'hm-lamp' }, g);
      v.tagT = label(g, o.x, o.y, tag, o.label);
      v.pctT = txt(g, o.x, o.label === 'above' ? o.y + 40 : o.y - 26, '', 'hm-pct');
      g.addEventListener('click', function (e) { e.stopPropagation(); valvePanel(v); });
      objs[tag] = v;
      paintValve(v);
      return v;
    }
    function locked(v) { return v.hvk && objs[v.hvk] && !objs[v.hvk].on; }
    function paintValve(v) {
      var st = locked(v) ? 'locked' : v.pos !== v.target ? 'moving' : v.pos >= 99.5 ? 'open' : v.pos > 0.5 ? 'part' : 'shut';
      v.g.setAttribute('class', 'hm-obj hm-v ' + st + (v.fault ? ' fault' : '') + (sel === v ? ' hm-sel' : ''));
      v.pctT.textContent = (st === 'moving' || st === 'part' || v.kind === 'reg' && v.pos > 0.5) ? Math.round(v.pos) + '%' : '';
    }
    function valvePanel(v) {
      W.GBLab && GBLab.sfx('tap');
      var head = '<h4>' + esc(v.tag) + '</h4><p class="hm-what">' + esc(v.what) + '</p>';
      if (locked(v)) {
        return openPanel(v, head + '<p class="hm-note">No hydraulic pressure on this valve. Release it first with <b>' + esc(v.hvk) + '</b>.</p>', function () {});
      }
      if (v.fault) return openPanel(v, head + '<p class="hm-note">Valve does not respond - fault.</p>', function () {});
      var pos = '<div class="hm-pos"><b class="hm-p">' + Math.round(v.pos) + ' %</b><span class="hm-bar"><i style="width:' + v.pos + '%"></i></span></div>';
      var html = head + pos + (v.kind === 'reg'
        ? '<div class="hm-row"><button type="button" class="hm-b stop" data-to="0">SHUT</button><button type="button" class="hm-b" data-step="-10">−10</button>' +
          '<button type="button" class="hm-b" data-step="10">+10</button><button type="button" class="hm-b go" data-to="100">OPEN</button></div>'
        : '<div class="hm-row"><button type="button" class="hm-b go" data-to="100">OPEN</button><button type="button" class="hm-b stop" data-to="0">CLOSE</button></div>');
      openPanel(v, html, function (p) {
        [].forEach.call(p.querySelectorAll('[data-to],[data-step]'), function (b) {
          b.addEventListener('click', function () {
            var to = b.hasAttribute('data-to') ? +b.getAttribute('data-to') : clamp(Math.round(v.target / 10) * 10 + +b.getAttribute('data-step'), 0, 100);
            move(v.tag, to);
            refreshPanel(v);
          });
        });
      });
    }
    function refreshPanel(v) {
      if (!panel || sel !== v) return;
      var p = panel.querySelector('.hm-p'), bar = panel.querySelector('.hm-bar i');
      if (p) p.textContent = Math.round(v.pos) + ' %';
      if (bar) bar.style.width = v.pos + '%';
    }
    function move(tag, to) {
      var v = objs[tag];
      if (!v || locked(v) || v.fault) return false;
      v.target = clamp(to, 0, 100);
      if (v.target !== v.pos) { W.GBLab && GBLab.sound.play([[340, 50, 0, 'triangle']], 0.04); run(); }
      paintValve(v);
      return true;
    }
    function setPos(tag, p) { var v = objs[tag]; if (!v) return; v.pos = v.target = clamp(p, 0, 100); paintValve(v); }

    // valves travel at their own speed - the trainee watches them move, as on board
    var last = 0, running = false;
    function run() { if (!running) { running = true; last = 0; W.requestAnimationFrame(tick); } }
    function tick(ts) {
      var dt = last ? Math.min(0.1, (ts - last) / 1000) : 0;
      last = ts;
      var busy = false;
      Object.keys(objs).forEach(function (k) {
        var v = objs[k];
        if (v.type !== 'valve' || v.pos === v.target) return;
        var step = 100 / v.travel * dt;
        v.pos = Math.abs(v.target - v.pos) <= step ? v.target : v.pos + (v.target > v.pos ? step : -step);
        paintValve(v);
        refreshPanel(v);
        if (v.pos === v.target) { W.GBLab && GBLab.sound.play([[520, 40, 0, 'triangle']], 0.035); emit('change', v.tag, v); }
        else busy = true;
      });
      if (busy) W.requestAnimationFrame(tick); else running = false;
    }

    /* ---- HVK: hydraulic pressure for a group of valves ---------------------- */
    function hvk(tag, o) {
      var k = { type: 'hvk', tag: tag, x: o.x, y: o.y, on: !!o.on, what: o.what || 'Hydraulic pressure for the remote valves' };
      var g = svgEl('g', { 'class': 'hm-obj hm-hvk', 'data-tag': tag, 'data-tap': '1' }, gObj);
      k.g = g;
      hit(g, o.x, o.y, 42);
      svgEl('rect', { x: o.x - 52, y: o.y - 30, width: 104, height: 26, rx: 5, 'class': 'hm-btn' }, g);
      k.state = txt(g, o.x, o.y - 12, 'OFF', '');
      svgEl('rect', { x: o.x - 52, y: o.y, width: 104, height: 24, rx: 5, 'class': 'hm-btn', style: 'fill:#0E1B2E' }, g);
      txt(g, o.x, o.y + 17, tag, '');
      g.addEventListener('click', function (e) {
        e.stopPropagation();
        openPanel(k, '<h4>' + esc(tag) + '</h4><p class="hm-what">' + esc(k.what) + '</p><div class="hm-row">' +
          '<button type="button" class="hm-b go" data-on="1">OPEN</button><button type="button" class="hm-b stop" data-on="0">CLOSE</button></div>' +
          '<p class="hm-note" style="color:#9DB3CC">OPEN releases pressure: its valves can then be moved.</p>', function (p) {
          [].forEach.call(p.querySelectorAll('[data-on]'), function (b) {
            b.addEventListener('click', function () { setHvk(tag, b.getAttribute('data-on') === '1'); closePanel(); });
          });
        });
      });
      objs[tag] = k;
      paintHvk(k);
      // valves drawn before their HVK now show they are locked
      Object.keys(objs).forEach(function (t) { if (objs[t].type === 'valve' && objs[t].hvk === tag) paintValve(objs[t]); });
      return k;
    }
    function paintHvk(k) { k.g.setAttribute('class', 'hm-obj hm-hvk' + (k.on ? ' on' : '')); k.state.textContent = k.on ? 'RELEASED' : 'OFF'; }
    function setHvk(tag, on) {
      var k = objs[tag]; if (!k) return;
      k.on = on; paintHvk(k);
      Object.keys(objs).forEach(function (t) { if (objs[t].type === 'valve' && objs[t].hvk === tag) paintValve(objs[t]); });
      emit('change', tag, k);
    }

    /* ---- readouts: value over tag, AL / AH lamps ----------------------------- */
    function readout(tag, o) {
      var r = { type: 'readout', tag: tag, x: o.x, y: o.y, unit: o.unit || '', digits: o.digits == null ? 1 : o.digits, al: o.al, ah: o.ah, alarmText: o.alarm, v: null };
      var w = o.w || 112;
      var g = svgEl('g', { 'class': 'hm-ro' }, gObj);
      r.g = g;
      svgEl('rect', { x: o.x - w / 2, y: o.y - 30, width: w, height: 26, rx: 4, 'class': 'hm-val' }, g);
      r.t = txt(g, o.x, o.y - 11, '--', 'hm-v1');
      svgEl('rect', { x: o.x - w / 2, y: o.y - 2, width: w, height: 20, rx: 4, 'class': 'hm-tagbox' }, g);
      txt(g, o.x, o.y + 13, tag, 'hm-sub');
      if (o.al != null || o.ah != null) {
        r.lAL = svgEl('rect', { x: o.x - w / 2, y: o.y - 50, width: w / 2 - 2, height: 16, rx: 3, 'class': 'hm-l' }, g);
        txt(g, o.x - w / 4, o.y - 38, 'AL', 'hm-lt');
        r.lAH = svgEl('rect', { x: o.x + 2, y: o.y - 50, width: w / 2 - 2, height: 16, rx: 3, 'class': 'hm-l' }, g);
        txt(g, o.x + w / 4, o.y - 38, 'AH', 'hm-lt');
      }
      if (o.what) txt(g, o.x, o.y + 32, o.what, 'hm-sub');
      objs[tag] = r;
      return r;
    }
    function set(tag, v) {
      var r = objs[tag];
      if (!r || r.type !== 'readout') return;
      r.v = v;
      r.t.textContent = (typeof v === 'number' ? v.toFixed(r.digits) : v) + (r.unit ? ' ' + r.unit : '');
      var lo = r.al != null && v < r.al, hi = r.ah != null && v > r.ah;
      if (r.lAL) r.lAL.setAttribute('class', 'hm-l' + (lo ? ' on' : ''));
      if (r.lAH) r.lAH.setAttribute('class', 'hm-l' + (hi ? ' on' : ''));
      r.g.setAttribute('class', 'hm-ro' + (lo || hi ? ' alarm' : ''));
      if (r.alarmText) { if (lo || hi) alarm(tag, tag + ' ' + (hi ? 'HIGH' : 'LOW') + ' - ' + r.alarmText); else clear(tag); }
    }

    /* ---- tanks ------------------------------------------------------------------ */
    function tank(id, o) {
      var t = { type: 'tank', tag: id, o: o };
      var g = svgEl('g', {}, gObj);
      var cid = 'hmc' + id.replace(/\W/g, '') + Math.floor(Math.random() * 1e6);
      var cp = svgEl('clipPath', { id: cid }, g);
      svgEl('rect', { x: o.x, y: o.y, width: o.w, height: o.h, rx: Math.min(o.h / 2.6, 70) }, cp);
      var defs = svgEl('defs', {}, g), gr = svgEl('linearGradient', { id: cid + 'g', x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
      svgEl('stop', { offset: 0, 'stop-color': '#5AB8FF', 'stop-opacity': '.9' }, gr);
      svgEl('stop', { offset: 1, 'stop-color': '#1B4FA8', 'stop-opacity': '.75' }, gr);
      svgEl('rect', { x: o.x, y: o.y, width: o.w, height: o.h, rx: Math.min(o.h / 2.6, 70), 'class': 'hm-tank' }, g);
      t.lvl = svgEl('rect', { x: o.x, y: o.y + o.h, width: o.w, height: 0, 'clip-path': 'url(#' + cid + ')', fill: 'url(#' + cid + 'g)', 'class': 'hm-lvl' }, g);
      txt(g, o.x + o.w / 2, o.y + o.h / 2 - 6, o.name || id, 'hm-name');
      t.sub = txt(g, o.x + o.w / 2, o.y + o.h / 2 + 16, '', 'hm-sub');
      objs[id] = t;
      level(id, o.level || 0, o.subText);
      return t;
    }
    function level(id, pct, sub) {
      var t = objs[id]; if (!t) return;
      var o = t.o, hgt = o.h * clamp(pct, 0, 100) / 100;
      t.lvl.setAttribute('y', o.y + o.h - hgt); t.lvl.setAttribute('height', hgt);
      t.sub.textContent = sub != null ? sub : Math.round(pct) + ' %';
      t.pct = pct;
    }

    /* ---- pumps -------------------------------------------------------------------- */
    function pump(tag, o) {
      var p = { type: 'pump', tag: tag, x: o.x, y: o.y, run: false, trip: '', what: o.what || 'Cargo pump', onStart: o.onStart, onStop: o.onStop };
      var g = svgEl('g', { 'class': 'hm-obj hm-pump', 'data-tag': tag, 'data-tap': '1' }, gObj);
      p.g = g;
      hit(g, o.x, o.y, 42);
      svgEl('circle', { cx: o.x, cy: o.y, r: 22, 'class': 'hm-m' }, g);
      txt(g, o.x, o.y + 6, 'M', 'hm-mt');
      txt(g, o.x, o.y + 44, tag, 'hm-tag');
      var lb = svgEl('g', { 'class': 'hm-lampbox' }, g);
      var lx = o.lampsAt ? o.lampsAt[0] : o.x + (o.lamps === 'left' ? -150 : 34), ly = o.lampsAt ? o.lampsAt[1] : o.y - 34;
      p.lamps = {};
      ['READY', 'RUNNING', 'TRIP'].forEach(function (n, i) {
        p.lamps[n] = svgEl('rect', { x: lx, y: ly + i * 24, width: 116, height: 20, rx: 4 }, lb);
        txt(lb, lx + 58, ly + i * 24 + 14, n, '');
      });
      g.addEventListener('click', function (e) {
        e.stopPropagation();
        openPanel(p, '<h4>' + esc(tag) + '</h4><p class="hm-what">' + esc(p.what) + '</p>' +
          (p.trip ? '<p class="hm-note">TRIPPED: ' + esc(p.trip) + '. Reset by starting again once the cause is gone.</p>' : '') +
          '<div class="hm-row"><button type="button" class="hm-b go" data-run="1">START</button><button type="button" class="hm-b stop" data-run="0">STOP</button></div>', function (pp) {
          [].forEach.call(pp.querySelectorAll('[data-run]'), function (b) {
            b.addEventListener('click', function () { closePanel(); runPump(tag, b.getAttribute('data-run') === '1'); });
          });
        });
      });
      objs[tag] = p;
      paintPump(p);
      return p;
    }
    function paintPump(p) {
      p.g.setAttribute('class', 'hm-obj hm-pump' + (p.run ? ' run' : '') + (p.trip ? ' trip' : ''));
      p.lamps.READY.setAttribute('class', !p.run && !p.trip ? 'on' : '');
      p.lamps.RUNNING.setAttribute('class', p.run ? 'on' : '');
      p.lamps.TRIP.setAttribute('class', p.trip ? 'bad' : '');
    }
    function runPump(tag, on) {
      var p = objs[tag]; if (!p) return;
      if (on && p.run) return;
      if (on) { p.trip = ''; p.run = true; W.GBLab && GBLab.sound.play([[90, 700, 0, 'sawtooth']], 0.03); if (p.onStart) p.onStart(); }
      else if (p.run) { p.run = false; if (p.onStop) p.onStop(); }
      paintPump(p); emit('change', tag, p);
    }
    function trip(tag, why) {
      var p = objs[tag]; if (!p) return;
      p.run = false; p.trip = why || 'TRIP'; paintPump(p);
      alarm(tag + '-trip', tag + ' TRIPPED - ' + p.trip);
      emit('change', tag, p);
    }

    /* ---- ESD and spectacle blanks ------------------------------------------------- */
    function esd(o) {
      var e0 = { type: 'esd', tag: 'ESD', x: o.x, y: o.y, tripped: false };
      var g = svgEl('g', { 'class': 'hm-obj hm-esd', 'data-tag': 'ESD', 'data-tap': '1' }, gObj);
      e0.g = g;
      hit(g, o.x, o.y, 44);
      svgEl('circle', { cx: o.x, cy: o.y, r: 30 }, g);
      txt(g, o.x, o.y + 5, 'ESD', '');
      g.addEventListener('click', function (ev) {
        ev.stopPropagation();
        openPanel(e0, '<h4>ESD</h4><p class="hm-what">Emergency shutdown: stops the cargo pumps and shuts the ESD valves.</p>' +
          '<div class="hm-row"><button type="button" class="hm-b esd">EMERGENCY STOP</button></div>', function (p) {
          p.querySelector('.hm-b.esd').addEventListener('click', function () {
            closePanel();
            e0.tripped = true; g.setAttribute('class', 'hm-obj hm-esd tripped');
            alarm('ESD', 'ESD ACTIVATED');
            if (o.onPress) o.onPress();
          });
        });
      });
      objs.ESD = e0;
      return e0;
    }
    function blank(tag, o) {
      var b = { type: 'blank', tag: tag, x: o.x, y: o.y, open: !!o.open, what: o.what || 'Spectacle blank' };
      var g = svgEl('g', { 'class': 'hm-obj hm-blank', 'data-tag': tag, 'data-tap': '1' }, gObj);
      b.g = g;
      hit(g, o.x, o.y, 36);
      svgEl('circle', { cx: o.x, cy: o.y, r: 11, 'class': 'hm-bl' }, g);
      label(g, o.x, o.y - 6, tag, o.label || 'below');
      g.addEventListener('click', function (e) {
        e.stopPropagation();
        openPanel(b, '<h4>' + esc(tag) + '</h4><p class="hm-what">' + esc(b.what) + '</p><div class="hm-row">' +
          '<button type="button" class="hm-b go" data-o="1">OPEN</button><button type="button" class="hm-b stop" data-o="0">BLANKED</button></div>', function (p) {
          [].forEach.call(p.querySelectorAll('[data-o]'), function (x) {
            x.addEventListener('click', function () { b.open = x.getAttribute('data-o') === '1'; paintBlank(b); closePanel(); emit('change', tag, b); });
          });
        });
      });
      objs[tag] = b;
      paintBlank(b);
      return b;
    }
    function paintBlank(b) { b.g.setAttribute('class', 'hm-obj hm-blank' + (b.open ? ' open' : '')); }

    /* ---- alarms: flash and sound until acknowledged -------------------------------- */
    var bar = root.querySelector('.hm-alarm'), barT = bar.querySelector('b'), barN = bar.querySelector('.hm-n');
    bar.querySelector('button').addEventListener('click', function (e) {
      e.stopPropagation();
      alarms.forEach(function (a) { a.ack = true; });
      paintAlarms();
    });
    function alarm(id, text) {
      for (var i = 0; i < alarms.length; i++) if (alarms[i].id === id) return;
      alarms.push({ id: id, text: text, ack: false });
      paintAlarms();
      emit('alarm', id, text);
    }
    function clear(id) {
      alarms = alarms.filter(function (a) { return a.id !== id; });
      paintAlarms();
    }
    function paintAlarms() {
      var un = alarms.filter(function (a) { return !a.ack; }), top = un[un.length - 1] || alarms[alarms.length - 1];
      bar.className = 'hm-alarm' + (alarms.length ? ' on' : '') + (un.length ? ' unack' : '');
      barT.textContent = top ? top.text : '';
      barN.textContent = alarms.length > 1 ? alarms.length + ' ALARMS' : '';
      clearInterval(hornT);
      if (un.length && W.GBLab) {
        var horn = function () { GBLab.sound.play([[740, 220, 80, 'square'], [740, 220, 0, 'square']], 0.04); };
        horn(); hornT = setInterval(horn, 2600);
      }
    }

    /* ---- for the task's own physics: what is open, and where can cargo go ------------ */
    function isOpen(tag) {
      var o = objs[tag];
      if (!o) return false;
      if (o.type === 'valve') return o.pos >= 5;
      if (o.type === 'blank') return o.open;
      return false;
    }
    function reach(start, edges) {
      var seen = {}, q = [start];
      seen[start] = true;
      while (q.length) {
        var n = q.shift();
        edges.forEach(function (e) {
          if (e[2] && !isOpen(e[2])) return;
          var m = e[0] === n ? e[1] : e[1] === n ? e[0] : null;
          if (m && !seen[m]) { seen[m] = true; q.push(m); }
        });
      }
      return seen;
    }

    return {
      root: root, svg: svg, fit: fit,
      pipe: pipe, setPipe: setPipe, valve: valve, move: move, setPos: setPos, pos: function (t) { return objs[t] ? objs[t].pos : 0; },
      hvk: hvk, setHvk: setHvk, readout: readout, set: set, tank: tank, level: level,
      pump: pump, runPump: runPump, trip: trip, running: function (t) { return !!(objs[t] && objs[t].run); },
      esd: esd, blank: blank, alarm: alarm, clear: clear, alarms: function () { return alarms.slice(); },
      acked: function () { return alarms.every(function (a) { return a.ack; }); },
      isOpen: isOpen, reach: reach, obj: function (t) { return objs[t]; }, closePanel: closePanel,
      fault: function (tag, on) { var v = objs[tag]; if (v) { v.fault = on !== false; paintValve(v); } },
      on: function (name, fn) { handlers[name].push(fn); }
    };
  }

  W.GBHMI = { create: create };
})(window, document);
