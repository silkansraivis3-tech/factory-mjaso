/* ==========================================================================
   kit3d.js - the 3D KIT of the Course Factory (course-visuals/kit3d). "3D kit (to merge after 2.63.3)".

   A 3D scene is a SPEC - a short JSON: the parts and where they stand, the labels, the steps (camera,
   highlight, state) and the controls. The kit draws it and gives every scene, unasked:
     - the look of the hand-made IGF scenes (M01-M15, 2026-10): ACES tone mapping, a procedural studio
       environment, one soft sun shadow drawn once, the course palette, cut-aways that show the insides;
     - labels ON the parts - an amber dot on the part, a white stem, a pill - that never cover each other,
       a control, the Full screen button or the box edge (the hand-made settle pass, IGF slide review
       2026-10-22), and that select their part (data-3d-part + GB3D.wire, 2.63.2);
     - framing that fills its box: the scene's box is fitted to the canvas at every size, a step or a
       tapped part is framed from its own box;
     - a tap on a part: it glows blue, its pill lights, the camera frames it; again (or beside) lets go;
     - steps that the deck's Next / Back walk (GB_HOOKS step), each with its camera, highlight and state,
       and the slide's own lines lit (line: 2), as the 2D kit does;
     - full screen (the deck's button; its own outside a deck), the poster fallback ([data-poster]),
       no-WebGL message, context loss, prefers-reduced-motion;
     - tablet performance: draws only on demand, pixel ratio <= 2, shadows once, static meshes merged
       per part and material, built and shader-compiled on the slide BEFORE (window.__noPrepare),
       one WebGL context for the whole page (GL), the graphics memory of a scene two slides away given
       back (sweep), window.__scene3d for perf3d.mjs / smoke3d.py, perf_gate.py the deck's budget.
   SPEC.md is the format; PARTS.md the parts and how to add one (KIT3D.define).

   In a deck:  <div class="fill fig kit3d-fig" data-3d-box>
                 <div class="kit3d-stage" data-stage data-kit3d="#k3-s05"> <img data-poster ...> </div>
                 <script type="application/json" id="k3-s05">{ ...spec... }</script></div>
               after three.min.js:  <script src="../assets/kit3d.js"></script>   (kit3d.css in the head)
   Alone:      KIT3D.mount(element, spec) -> scene api {select, step, state, info, snapshot, dispose}

   Global THREE r128 (the factory's course-module-ui/templates/vendor/three.min.js). ES5 only - an old
   Android WebView: no arrow functions, let/const, classes or template strings.
   ========================================================================== */
(function (w, d) {
  'use strict';

  var T = null;                                   /* THREE, taken when the first scene is built */
  var NAVY = '#0A2463', BLUE = '#2EB6F8', AMBER = '#E9A51E';
  var DEG = Math.PI / 180;
  var PIXEL_BUDGET = 2.4e6;           /* 2.70.0 - the most pixels a frame draws (P.size) */
  var TURN_SEARCH_MS = 8;             /* a label search slower than this waits for the view to stand (P.settle) */
  var EDGE = 40;                      /* a pill past the box's edge counts as this many touches: inside always wins (P.settle) */
  var CLOSE_UP = 3;                   /* a step's frame closes in only this many times nearer than the whole model (P.viewFor) */
  /* lite light: a device a scene juddered on is remembered, and every scene after builds lite there (P.goLite) */
  var LITE_KEY = 'kit3d.lite';
  function slowDevice(set) {
    try {
      if (set) { w.localStorage.setItem(LITE_KEY, '1'); }
      return w.localStorage.getItem(LITE_KEY) === '1';
    } catch (e) { return !!set; }
  }
  var PART = {};                                  /* part type -> builder(k, p) */
  var PART_INFO = {};                             /* part type -> {family, about} for check_kit3d / PARTS.md */
  var scenes = [];

  /* ONE graphics context for the page: every scene draws with one renderer and its one canvas, which the scene shown holds
     (P.take). A browser keeps only so many WebGL contexts - 16 on a computer, fewer in a tablet's WebView, the oldest lost -
     and each keeps its own drawing buffer in the graphics memory: a deck of 18 3D slides held 16 (perf_gate.py). A scene
     built ahead while another is shown draws off screen (P.prepare); gb_scene.js borrows the same renderer (KIT3D.gl). */
  var GL = { r: null, holder: null, failed: false, rt: null, dpr: 0, v2: null };
  function newRenderer() {
    var r;
    try {
      r = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: false, powerPreference: 'high-performance' });
    } catch (e1) { r = null; }
    if (!r) { return null; }
    r.setPixelRatio(Math.min(w.devicePixelRatio || 1, 2));
    r.outputEncoding = T.sRGBEncoding;
    r.toneMapping = T.ACESFilmicToneMapping;
    r.localClippingEnabled = true;
    r.shadowMap.type = T.PCFSoftShadowMap;
    r.shadowMap.autoUpdate = false;               /* the scene stands still: shadows are worked out once */
    r.setClearColor(0x000000, 0);
    return r;
  }
  function shared() {
    if (!GL.r && !GL.failed) {
      T = T || w.THREE;
      GL.r = T ? newRenderer() : null;
      GL.failed = !GL.r;
    }
    return GL.r;
  }
  /* the scenes of the slides two or more away from the slide shown give their graphics memory back */
  function sweep(here) {
    scenes.forEach(function (S) {
      if (S.at != null && S.prepared && !S.live && Math.abs(S.at - here) >= 2) { S.release(); }
    });
  }

  /* ---- the palette: [colour (sRGB), roughness, metalness] - taken from the hand-made scenes ---- */
  var PAL = {
    steel: ['#8f9ba6', 0.45, 0.6], steel_mid: ['#8c98a3', 0.4, 0.7], steel_dark: ['#5b6670', 0.5, 0.6],
    steel_black: ['#2c363f', 0.6, 0.4], flange: ['#74808b', 0.45, 0.65], pipe: ['#a8b3bd', 0.4, 0.6],
    hull: ['#33475c', 0.6, 0.35], deck: ['#566574', 0.78, 0.3], side: ['#6f7d8b', 0.7, 0.35],
    floor: ['#cfd9e2', 0.85, 0.0], floor_dark: ['#46535f', 0.7, 0.35], wall: ['#8493a1', 0.85, 0.05],
    frame: ['#6c7b89', 0.6, 0.35], trim: ['#e4e9ee', 0.6, 0.1],
    shell: ['#d6dce2', 0.36, 0.62], tank: ['#e2e7ec', 0.42, 0.38], ring: ['#c3cad1', 0.4, 0.6],
    saddle: ['#56616c', 0.7, 0.3], insulation: ['#e9dfc2', 0.92, 0.0], barrier: ['#b07a2e', 0.55, 0.3],
    membrane: ['#d3dae0', 0.3, 0.85], stainless: ['#d6dde3', 0.3, 0.8],
    gas: ['#e3b023', 0.45, 0.25], cold: ['#cfe8f4', 0.55, 0.05], vapour: ['#e3b023', 0.45, 0.25],
    red: ['#d0342c', 0.5, 0.1], amber: [AMBER, 0.5, 0.0], yellow: ['#e3b023', 0.5, 0.2],
    green: ['#3f9b5a', 0.5, 0.1], rubber: ['#2b333c', 0.8, 0.1],
    engine: ['#3a6a94', 0.45, 0.35], engine_dark: ['#2c4f6f', 0.5, 0.4], cover: ['#c4ccd3', 0.5, 0.3],
    foundation: ['#4d5660', 0.7, 0.4], cabinet: ['#e6eaee', 0.5, 0.1], panel: ['#cdd5db', 0.5, 0.15],
    screen: ['#2f3a44', 0.3, 0.2], accommodation: ['#e8ecef', 0.7, 0.05], window: ['#2a3d52', 0.2, 0.3],
    skin: ['#e0b58f', 0.7, 0.0], overall: ['#e46b1f', 0.8, 0.0], helmet: ['#f2f2f2', 0.4, 0.0],
    lng: ['#5fb4ea', 0.15, 0.0], glass: ['#cfe6f4', 0.12, 0.0], wood: ['#a8865a', 0.85, 0.0]
  };
  var TINT = { amber: '#f0c36a', green: '#7fcf9d', blue: '#86b8ee', grey: '#b8c6d4', red: '#f08f86', violet: '#b9a3e3' };
  var ZONE = ['#ff4040', '#ff9a1f', '#f4e04d'];   /* zone 0 red, 1 amber, 2 yellow (IGF M07) */

  function each(o, fn) { var k; for (k in o) { if (Object.prototype.hasOwnProperty.call(o, k)) { fn(o[k], k); } } }
  function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
  function num(v, dflt) { return typeof v === 'number' && isFinite(v) ? v : dflt; }
  function now() { return (w.performance && w.performance.now) ? w.performance.now() : new Date().getTime(); }
  function ease(u) { return u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2; }
  function v3(a, dflt) { return a && a.length === 3 ? a : (dflt || [0, 0, 0]); }
  function el(tag, cls, parent) { var e = d.createElement(tag); if (cls) { e.className = cls; } if (parent) { parent.appendChild(e); } return e; }
  function hasCls(e, c) { return (' ' + e.className + ' ').indexOf(' ' + c + ' ') >= 0; }
  function setCls(e, c, on) {
    if (on && !hasCls(e, c)) { e.className += ' ' + c; }
    if (!on && hasCls(e, c)) { e.className = (' ' + e.className + ' ').replace(' ' + c + ' ', ' ').replace(/^\s+|\s+$/g, ''); }
  }
  var reduce = false;
  try { reduce = !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e0) { reduce = false; }

  /* "pipe.cut > 0.5", "!tcs.open", "gas.on" - a condition on the scene's states */
  function test(S, expr) {
    if (!expr) { return true; }
    var m = /^\s*(!?)\s*([\w.\-]+)\s*(?:(>=|<=|>|<|==)\s*([\d.]+))?\s*$/.exec(String(expr));
    if (!m) { return true; }
    var st = S.states[m[2]], v = st ? st.v : 0, r;
    if (m[3]) {
      var b = parseFloat(m[4]);
      r = m[3] === '>' ? v > b : m[3] === '<' ? v < b : m[3] === '>=' ? v >= b : m[3] === '<=' ? v <= b : Math.abs(v - b) < 1e-6;
    } else { r = v > 0.5; }
    return m[1] ? !r : r;
  }

  /* ======================================================================== the builder a part draws with */
  function Builder(S) {
    var k = this;
    k.S = S; k.T = T; k.cur = null; k.g = S.root; k.stack = [];
    k.PAL = PAL; k.TINT = TINT; k.ZONE = ZONE; k.AMBER = AMBER; k.BLUE = BLUE; k.NAVY = NAVY;
  }
  var B = Builder.prototype;
  B.col = function (hex) {
    var c = new T.Color(hex);
    if (c.convertSRGBToLinear) { c.convertSRGBToLinear(); }
    return c;
  };
  /* a part of its own while it is built: every mesh and material from here on belongs to it (glow, pick, frame) */
  B.part = function (id, info) {
    var S = this.S;
    if (!id) { this.cur = null; return null; }
    var p = S.parts[id];
    if (!p) {
      p = S.parts[id] = { id: id, items: [], mats: [], g: 0, g0: 0, g1: 0, anchors: {}, kids: [], parent: null,
                          pick: true, name: '' };
      S.order.push(id);
    }
    if (info) { each(info, function (v, n) { p[n] = v; }); }
    this.cur = p;
    return p;
  };
  /* a sub-part (a pipe's inner pipe, a hull's space): selectable alone; selecting the parent lights it too */
  B.sub = function (id, info) {
    var parent = this.cur, p = this.part(id, info);
    if (parent && parent !== p && !p.parent) { p.parent = parent.id; parent.kids.push(id); }
    return p;
  };
  B.track = function (g) { this.S.geos.push(g); return g; };
  /* a material: a palette name ("gas"), or {color, rough, metal}; extra: opacity, double, clip [planes], emissive,
     depthTest, flat. Each part has its own copy, so it can glow alone. */
  B.mat = function (name, extra) {
    var S = this.S, src = typeof name === 'string' ? (PAL[name] || [name, 0.5, 0.2]) : [name.color || '#8f9ba6',
      num(name.rough, 0.5), num(name.metal, 0.2)];
    var x = extra || {}, key = [src.join(','), this.cur ? this.cur.id : '', x.opacity, x.double, x.emissive, x.depthTest,
      x.flat, x.clip ? x.clip.map(function (c) { return c.id; }).join('+') : ''].join('|');
    if (S.matCache[key]) { return S.matCache[key]; }
    var p = { color: this.col(src[0]), roughness: src[1], metalness: src[2] };
    if (x.opacity != null && x.opacity < 1) { p.transparent = true; p.opacity = x.opacity; p.depthWrite = false; }
    if (x.double || p.transparent) { p.side = T.DoubleSide; }
    if (x.clip) { p.clippingPlanes = x.clip.map(function (c) { return c.plane; }); p.clipShadows = true; p.side = T.DoubleSide; }
    if (x.emissive) { p.emissive = this.col(x.emissive); p.emissiveIntensity = num(x.emissiveIntensity, 1); }
    if (x.depthTest === false) { p.depthTest = false; }
    if (x.flat) { p.flatShading = true; }
    var m;
    /* lite: lit once per corner, not per pixel - no roughness, no metal shine */
    if (S.lite) { delete p.roughness; delete p.metalness; m = new T.MeshLambertMaterial(p); }
    else { m = new T.MeshStandardMaterial(p); }
    this.reg(m);
    S.matCache[key] = m;
    return m;
  };
  /* a see-through panel or a ghost wall: unlit, double sided, no depth write */
  B.basic = function (hex, opacity, extra) {
    var p = { color: this.col(hex), transparent: opacity < 1, opacity: opacity, side: T.DoubleSide, depthWrite: false };
    if (extra) { each(extra, function (v, n) { p[n] = v; }); }
    var m = new T.MeshBasicMaterial(p);
    this.reg(m);
    return m;
  };
  B.reg = function (m) {
    this.S.mats.push(m);
    if (this.cur) {
      this.cur.mats.push(m);
      m.userData.part = this.cur.id;
      if (m.color) { m.userData.c0 = m.color.clone(); }
      m.userData.o0 = m.opacity;
      if (m.emissive) { m.userData.e0 = m.emissive.clone(); m.userData.ei0 = m.emissiveIntensity; }
    }
    return m;
  };
  /* placing: k.push([x,y,z], rotYdeg, scale) ... k.pop() */
  B.push = function (at, rot, scale, flip) {
    var g = new T.Group(), a = v3(at);
    g.position.set(a[0], a[1], a[2]);
    if (rot) { g.rotation.y = rot * DEG; }
    if (scale) { g.scale.set(scale, scale, scale); }
    if (flip === 'x') { g.scale.x *= -1; } else if (flip === 'z') { g.scale.z *= -1; }   /* a mirror image (an engine turned end for end) */
    this.g.add(g);
    this.stack.push(this.g);
    this.g = g;
    g.updateMatrixWorld(true);
    return g;
  };
  B.pop = function () { this.g = this.stack.pop() || this.S.root; };
  B.add = function (geo, mat, x, y, z, o) {
    o = o || {};
    var m = new T.Mesh(this.track(geo), mat);
    m.position.set(x || 0, y || 0, z || 0);
    var see = mat.transparent || mat.isMeshBasicMaterial;
    m.castShadow = o.cast != null ? !!o.cast : !see;
    m.receiveShadow = o.recv != null ? !!o.recv : !mat.isMeshBasicMaterial;
    if (o.order != null) { m.renderOrder = o.order; } else if (see) { m.renderOrder = 2; }
    if (o.keep) { m.userData.keep = true; }
    if (o.noPick) { m.userData.noPick = true; }
    if (o.rx) { m.rotation.x = o.rx; } if (o.ry) { m.rotation.y = o.ry; } if (o.rz) { m.rotation.z = o.rz; }
    this.claim(m);
    (o.parent || this.g).add(m);
    return m;
  };
  B.claim = function (m) {
    if (this.cur && m) { m.userData.part = this.cur.id; this.cur.items.push(m); }
    return m;
  };
  B.box = function (w0, h, d0, mat, x, y, z, o) { return this.add(new T.BoxGeometry(w0, h, d0), mat, x, y, z, o); };
  /* a cylinder along 'x', 'y' or 'z'; o.open, o.seg, o.r2 (other end radius), o.t0 / o.tl (part of the round) */
  B.cyl = function (axis, r, len, mat, x, y, z, o) {
    o = o || {};
    var g = new T.CylinderGeometry(o.r2 != null ? o.r2 : r, r, len, o.seg || 32, 1, !!o.open, o.t0 || 0, o.tl || Math.PI * 2);
    if (axis === 'x') { g.rotateZ(-Math.PI / 2); } else if (axis === 'z') { g.rotateX(Math.PI / 2); }
    return this.add(g, mat, x, y, z, o);
  };
  B.ball = function (r, mat, x, y, z, o) { return this.add(new T.SphereGeometry(r, (o && o.seg) || 20, 14), mat, x, y, z, o); };
  /* a ring round the axis (a handwheel, a stiffening ring) */
  B.ring = function (axis, R, r, mat, x, y, z, o) {
    var g = new T.TorusGeometry(R, r, 8, (o && o.seg) || 32);
    if (axis === 'x') { g.rotateY(Math.PI / 2); } else if (axis === 'y') { g.rotateX(Math.PI / 2); }
    return this.add(g, mat, x, y, z, o);
  };
  var UP = null;
  /* a thin cylinder from a to b */
  B.seg = function (a, b, r, mat, o) {
    if (!UP) { UP = new T.Vector3(0, 1, 0); }
    var dv = new T.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]), len = dv.length();
    if (len < 1e-6) { return null; }
    var m = this.add(new T.CylinderGeometry(r, r, len, (o && o.seg) || 16, 1, !!(o && o.open)), mat,
      (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2, o);
    m.quaternion.setFromUnitVectors(UP, dv.normalize());
    return m;
  };
  /* an arrow head with its tip at tip, pointing along dir */
  B.cone = function (tip, dir, r, h, mat, o) {
    if (!UP) { UP = new T.Vector3(0, 1, 0); }
    var dv = new T.Vector3(dir[0], dir[1], dir[2]).normalize();
    var m = this.add(new T.ConeGeometry(r, h, 16), mat, tip[0] - dv.x * h / 2, tip[1] - dv.y * h / 2, tip[2] - dv.z * h / 2, o);
    m.quaternion.setFromUnitVectors(UP, dv);
    return m;
  };
  /* a pipe run through points: straight legs and a ball at each bend */
  B.run = function (pts, r, mat, o) {
    var i, out = [];
    for (i = 0; i < pts.length - 1; i++) { out.push(this.seg(pts[i], pts[i + 1], r, mat, o)); }
    for (i = 1; i < pts.length - 1; i++) { out.push(this.ball(r * 1.02, mat, pts[i][0], pts[i][1], pts[i][2], o)); }
    return out;
  };
  /* a smooth tube through points (a hose) */
  B.tube = function (pts, r, mat, o) {
    var vs = pts.map(function (p) { return new T.Vector3(p[0], p[1], p[2]); });
    var c = new T.CatmullRomCurve3(vs, false, 'catmullrom', 0.5);
    return this.add(new T.TubeGeometry(c, Math.max(24, pts.length * 12), r, (o && o.seg) || 14, false), mat, 0, 0, 0, o);
  };
  B.lines = function (pts, hex, o) {
    var g = new T.BufferGeometry();
    g.setAttribute('position', new T.Float32BufferAttribute(pts, 3));
    var m = o && o.dash ? new T.LineDashedMaterial({ color: this.col(hex), dashSize: o.dash, gapSize: o.gap || o.dash * 0.7,
      transparent: true, opacity: num(o.opacity, 0.9) }) : new T.LineBasicMaterial({ color: this.col(hex),
      transparent: o && o.opacity != null, opacity: num(o && o.opacity, 1) });
    this.reg(m);
    var l = new T.LineSegments(this.track(g), m);
    if (o && o.dash) { l.computeLineDistances(); }
    if (o && o.order != null) { l.renderOrder = o.order; }
    l.userData.noPick = true;
    this.g.add(l);
    return l;
  };
  B.boxEdges = function (x0, x1, y0, y1, z0, z1) {
    var p = [], a, b, xs = [x0, x1], ys = [y0, y1], zs = [z0, z1];
    for (a = 0; a < 2; a++) {
      for (b = 0; b < 2; b++) {
        p.push(x0, ys[a], zs[b], x1, ys[a], zs[b]);
        p.push(xs[a], y0, zs[b], xs[a], y1, zs[b]);
        p.push(xs[a], ys[b], z0, xs[a], ys[b], z1);
      }
    }
    return p;
  };
  /* many copies of one shape as ONE draw call; list of [x, y, z] or {at, rx, ry, rz, s:[sx,sy,sz]} */
  B.many = function (geo, mat, list, o) {
    var im = new T.InstancedMesh(this.track(geo), mat, list.length), dm = new T.Object3D(), i, it, a;
    for (i = 0; i < list.length; i++) {
      it = list[i]; a = Array.isArray(it) ? it : it.at;     /* not it.at on an array: that is Array.prototype.at */
      dm.position.set(a[0], a[1], a[2]);
      dm.rotation.set(it.rx || 0, it.ry || 0, it.rz || 0);
      if (it.s) { dm.scale.set(it.s[0], it.s[1], it.s[2]); } else { dm.scale.set(1, 1, 1); }
      dm.updateMatrix();
      im.setMatrixAt(i, dm.matrix);
    }
    im.castShadow = !(o && o.cast === false); im.receiveShadow = true;
    this.claim(im);
    this.g.add(im);
    this.S.disposeLater.push(im);
    return im;
  };
  /* a clipping plane: what lies on the side the normal points AWAY from is cut off. Given in the part's own
     coordinates; c.set(constant) moves it (a state can open a cut). */
  B.clip = function (normal, constant) {
    var S = this.S, local = new T.Plane(new T.Vector3(normal[0], normal[1], normal[2]).normalize(), constant || 0);
    this.g.updateMatrixWorld(true);
    var mw = this.g.matrixWorld.clone(), c = { id: 'c' + (S.clipN++), local: local, plane: local.clone().applyMatrix4(mw) };
    c.set = function (k0) { c.local.constant = k0; c.plane.copy(c.local).applyMatrix4(mw); };
    return c;
  };
  /* a state of the scene ("pipe.cut"): a number a step or a control sets, tweened; fn(v) shows it */
  B.state = function (name, v0, fn) {
    var S = this.S, st = S.states[name];
    if (!st) { st = S.states[name] = { v: v0 || 0, v0: v0 || 0, fns: [] }; }
    st.fns.push(fn);
    fn(st.v);
    return st;
  };
  /* a point a label can stand on, in the part's own coordinates */
  B.anchor = function (name, at) {
    if (!this.cur) { return; }
    var v = new T.Vector3(at[0], at[1], at[2]);
    this.g.updateMatrixWorld(true);
    v.applyMatrix4(this.g.matrixWorld);
    this.cur.anchors[name] = [v.x, v.y, v.z];
  };
  /* a port: where a hose or another part joins this one (its anchor too), dir the way a hose leaves it - in the part's
     own coordinates; another part's "connect", a hose's "from" / "to" read it as "<id>.<name>" */
  B.port = function (name, at, dir) {
    if (!this.cur) { return; }
    this.anchor(name, at);
    var dv = new T.Vector3(dir[0], dir[1], dir[2]).transformDirection(this.g.matrixWorld);
    (this.cur.ports = this.cur.ports || {})[name] = { at: this.cur.anchors[name], dir: [dv.x, dv.y, dv.z] };
  };
  /* a point and a direction in the world, in the part's own coordinates (a hose's end on another part's port) */
  B.local = function (at) {
    this.g.updateMatrixWorld(true);
    var v = this.g.worldToLocal(new T.Vector3(at[0], at[1], at[2]));
    return [v.x, v.y, v.z];
  };
  B.localDir = function (dir) {
    this.g.updateMatrixWorld(true);
    var m = new T.Matrix4().copy(this.g.matrixWorld).invert(), v = new T.Vector3(dir[0], dir[1], dir[2]).transformDirection(m);
    return [v.x, v.y, v.z];
  };
  /* a label the part makes itself (a dimension's value, the names of a hull's spaces); at in the part's coordinates */
  B.label = function (lb) {
    var v = new T.Vector3(lb.at[0], lb.at[1], lb.at[2]), x = {};
    this.g.updateMatrixWorld(true);
    v.applyMatrix4(this.g.matrixWorld);
    each(lb, function (val, n) { x[n] = val; });
    x.at = [v.x, v.y, v.z];
    if (!x.part && this.cur) { x.part = this.cur.id; }
    this.S.autoLabels.push(x);
  };
  /* something that moves by itself while it is on (gas, flow): fn(t seconds since on) -> true while it still moves */
  B.anim = function (name, fn) { this.S.anims.push({ name: name, fn: fn, t0: 0, on: false }); };

  /* ======================================================================== the scene */
  function Scene(spec, stage, opt) {
    var S = this;
    S.spec = spec; S.stage = stage; S.opt = opt || {};
    S.parts = {}; S.order = []; S.states = {}; S.anims = []; S.autoLabels = []; S.clipN = 0;
    S.geos = []; S.mats = []; S.matCache = {}; S.disposeLater = []; S.listeners = [];
    S.built = false; S.live = false; S.dead = false; S.frames = 0; S.step = 0; S.sel = null; S.lit = {};
    S.free = false;                     /* the presenter turned the view by hand since the last step / pick */
    S.raf = 0; S.tween = null; S.shadowsDone = false;
    /* "light": "full" | "lite" | "auto" (lite on a device a scene juddered on before, and lite from the moment one does) */
    S.lightMode = spec.light === 'full' || spec.light === 'lite' ? spec.light : 'auto';
    S.lite = S.lightMode === 'lite' || (S.lightMode === 'auto' && slowDevice());
    S.shadows = spec.shadows !== false && !S.lite;
  }
  var P = Scene.prototype;

  P.listen = function (t, type, fn, o) { t.addEventListener(type, fn, o || false); this.listeners.push([t, type, fn, o || false]); };

  /* ---- the DOM: a wrap in the stage, the canvas, the label layer, the controls ---- */
  P.dom = function () {
    var S = this, st = S.stage, spec = S.spec;
    if (w.getComputedStyle && w.getComputedStyle(st).position === 'static') { st.style.position = 'relative'; }
    S.wrap = el('div', 'k3', st);
    S.wrap.setAttribute('role', 'img');
    S.wrap.setAttribute('aria-label', spec.label || spec.title || '3D model');
    S.labelLayer = el('div', 'k3-labels', S.wrap);
    S.labelLayer.style.visibility = 'hidden';
    if (spec.pill_max) { S.wrap.style.setProperty('--k3-pill-max', spec.pill_max + 'px'); }   /* the widest a pill wraps at */
    S.ctl = el('div', 'k3-ctl' + (spec.controls_at === 'right' ? ' k3-ctl-col' : ''), S.wrap);
    /* captions: one line of words top left for the state the scene is in (IGF M04 "Warm natural gas: rises to the
       deckhead") - {"text", "when"}, the first whose state holds */
    if (spec.captions && spec.captions.length) { S.cap = el('div', 'k3-cap', S.wrap); S.cap.setAttribute('aria-live', 'polite'); }
    S.poster = st.querySelector('[data-poster]');
  };

  P.renderer = function () {
    this.exposure = num(this.spec.exposure, 1.05);
    return shared();
  };
  /* the renderer set for this scene before it draws: one renderer serves every scene, each with its own light */
  P.gl = function () {
    var S = this;
    S.r.toneMappingExposure = S.exposure;
    S.r.shadowMap.enabled = S.shadows;
    if (S.envAgain) {
      S.envAgain = false;
      if (!S.lite) { try { S.env(); } catch (e1) { S.scene.environment = null; } }
    }
  };
  /* the canvas to this scene: moved into its box - or, while another scene shown holds it (two on one slide, a page of
     scenes), a renderer of its own until this one is hidden */
  P.take = function () {
    var S = this, h = GL.holder;
    if (S.own || S.r !== GL.r) { return; }
    if (h && h !== S && h.live && !h.dead && S.live) {
      var r = newRenderer();
      if (r) { S.adopt(r); return; }
    }
    if (GL.holder !== S) { GL.holder = S; S.W = S.H = 0; }      /* sized again: another scene drew with it since */
    var cv = S.r.domElement;
    if (cv.parentNode !== S.wrap) { cv.className = ''; S.wrap.insertBefore(cv, S.labelLayer); }
  };
  P.adopt = function (r) {
    var S = this;
    S.own = S.r = r;
    S.wrap.insertBefore(r.domElement, S.labelLayer);
    S.lost();
    S.W = S.H = 0;
  };
  P.disown = function () {
    var S = this, r = S.own;
    S.release();
    S.own = null; S.r = GL.r;
    r.dispose();
    try { r.forceContextLoss(); } catch (e2) { /* gone */ }
    if (r.domElement.parentNode) { r.domElement.parentNode.removeChild(r.domElement); }
  };
  /* the graphics memory is gone (the context lost, given back, another renderer): the shadows and the studio light are
     made again before the next frame */
  P.lost = function () {
    var S = this;
    S.shadowsDone = false;
    if (S.envRT) { S.envRT.dispose(); S.envRT = null; S.envAgain = true; }
    S.schedule();
  };
  /* the scene's graphics memory given back when its slide is two or more away (sweep): its parts stay in the page and go
     to the graphics chip again when the scene is built ahead next time */
  P.release = function () {
    var S = this;
    if (S.live || !S.ok) { return; }
    S.prepared = false;
    S.scene.traverse(function (o) {
      if (o.geometry) { o.geometry.dispose(); }
      [].concat(o.material || []).forEach(function (m) { m.dispose(); });
      if (o.isInstancedMesh && o.dispose) { o.dispose(); }
    });
    S.mats.forEach(function (m) { m.dispose(); });
    if (S.sun.shadow.map) { S.sun.shadow.map.dispose(); S.sun.shadow.map = null; }
    S.lost();
  };

  /* a soft studio light, made once from a gradient sphere and three bright panels (the hand-made scenes' makeEnv) */
  P.env = function () {
    var S = this, pm = new T.PMREMGenerator(S.r), es = new T.Scene(), R = 40;
    var sg = new T.SphereGeometry(R, 24, 12), pos = sg.attributes.position, cols = [], i, y, k;
    for (i = 0; i < pos.count; i++) {
      y = pos.getY(i) / R;
      if (y >= 0) { cols.push(0.88 - 0.30 * y, 0.92 - 0.20 * y, 0.95 - 0.02 * y); }
      else { k = 1 + y; cols.push(0.22 + 0.66 * k, 0.24 + 0.68 * k, 0.27 + 0.68 * k); }
    }
    sg.setAttribute('color', new T.Float32BufferAttribute(cols, 3));
    var sm = new T.MeshBasicMaterial({ vertexColors: true, side: T.BackSide });
    es.add(new T.Mesh(sg, sm));
    var pg = new T.PlaneGeometry(26, 12), specs = [[-22, 24, 18, 5.0], [26, 14, -8, 2.6], [0, 8, 30, 2.0]], pms = [];
    for (i = 0; i < specs.length; i++) {
      var pmat = new T.MeshBasicMaterial({ side: T.DoubleSide });
      pmat.color.setRGB(specs[i][3], specs[i][3], specs[i][3] * 1.04);
      var pmesh = new T.Mesh(pg, pmat);
      pmesh.position.set(specs[i][0], specs[i][1], specs[i][2]);
      pmesh.lookAt(0, 0, 0);
      es.add(pmesh);
      pms.push(pmat);
    }
    S.envRT = pm.fromScene(es, 0.03);
    S.scene.environment = S.envRT.texture;
    pm.dispose(); sg.dispose(); sm.dispose(); pg.dispose();
    for (i = 0; i < pms.length; i++) { pms[i].dispose(); }
  };

  /* ---- build: renderer, light, every part, labels, controls ---- */
  P.build = function () {
    var S = this, spec = S.spec, i;
    if (S.built || S.dead) { return S.ok; }
    S.built = true;
    if (S.lightMode === 'auto' && slowDevice()) { S.lite = true; S.shadows = false; }   /* a scene juddered since the page opened */
    T = T || w.THREE;
    if (!T) { S.fail('three.js is not loaded'); return false; }
    S.dom();
    S.r = S.renderer();
    if (!S.r) { S.fail('no WebGL'); return false; }
    S.scene = new T.Scene();
    S.root = new T.Group();
    S.scene.add(S.root);
    var envOk = !S.lite;
    if (envOk) { try { S.env(); } catch (e2) { envOk = false; S.scene.environment = null; } }
    S.hemi = new T.HemisphereLight(0xf2f7ff, 0x5a6672, envOk ? 0.30 : 0.95);
    S.scene.add(S.hemi);
    S.sun = new T.DirectionalLight(0xfff6e8, envOk ? 0.85 : 1.0);
    S.sun.castShadow = S.shadows;
    S.sun.shadow.mapSize.set(2048, 2048);
    S.sun.shadow.bias = -0.0006;
    S.sun.shadow.normalBias = 0.03;
    S.scene.add(S.sun); S.scene.add(S.sun.target);

    var k = new Builder(S), list = spec.parts || [], p, fn, ok = true, order = joinOrder(list, S), oi;
    S.k = k;
    for (oi = 0; oi < order.length; oi++) {
      i = order[oi];
      p = joinRelation(inRelation(list, deckRelation(list, list[i], S), S), S);
      fn = PART[p.type];
      if (!fn) { S.warn('part "' + (p.id || i) + '": the kit has no part type "' + p.type + '"'); continue; }
      k.g = S.root; k.stack = [];
      /* the same id again is more of the same part: a space's pipes and valves are that space (IGF M01 'tcs') */
      var info = { type: p.type, name: p.name || '', pick: p.pick !== false && !!p.id };
      if (p.az != null) { info.az = p.az; }           /* the angle a tap on it frames it from (IGF M03 PARTS[].az) */
      if (p.el != null) { info.el = p.el; }
      k.part(p.id || ('_' + p.type + i), info);
      k.push(p.at, p.rot, p.scale, p.flip);
      try { fn(k, p); } catch (e3) { ok = false; S.warn('part "' + (p.id || i) + '" (' + p.type + '): ' + e3.message); }
      k.pop();
      k.part(null);
    }
    if (!ok && S.opt.strict) { S.fail('a part failed to build'); return false; }
    /* "<id>.ghost": any part turns see-through steel (0..1) - the inside of a tank or a pipe shown without a cut (IGF M07:
       the red zone 0 inside the tank and the pipes). Made only for the parts a spec names it for. */
    var txt = JSON.stringify(spec.steps || []) + JSON.stringify(spec.controls || []) + JSON.stringify(spec.states || {});
    each(S.parts, function (p) {
      if (txt.indexOf('"' + p.id + '.ghost"') < 0) { return; }
      var ms = p.mats.filter(function (m) { return m.isMeshStandardMaterial || m.isMeshLambertMaterial; });
      k.cur = p;
      k.state(p.id + '.ghost', 0, function (v) {
        ms.forEach(function (m) {
          var o0 = m.userData.o0 == null ? 1 : m.userData.o0, see = v > 0.01;
          if (m.transparent !== (see || o0 < 1)) { m.transparent = see || o0 < 1; m.needsUpdate = true; }
          m.opacity = o0 + (0.22 - o0) * v;
          m.depthWrite = v < 0.5 && o0 >= 1;
        });
      });
      k.cur = null;
    });
    S.scene.updateMatrixWorld(true);
    S.measure();
    S.light();
    if (spec.merge !== false) { S.merge(); }
    S.camera = new T.PerspectiveCamera(num(spec.fov, 32), 1.6, 0.05, 2000);
    S.view = { az: 0, el: 0, zoom: 1, tx: 0, ty: 0, tz: 0 };
    S.labelsMake();
    S.controlsMake();
    S.events();
    S.ok = true;
    return true;
  };

  P.fail = function (why) {
    var S = this;
    S.ok = false;
    S.why = why;
    if (S.poster) { S.poster.removeAttribute('hidden'); S.poster.style.display = ''; }
    else if (S.stage && !S.stage.querySelector('.k3-msg')) {
      var m = el('div', 'k3-msg', S.stage);
      m.appendChild(d.createTextNode(S.spec.unavailable || 'The 3D view is not available on this device.'));
    }
    if (S.wrap && S.r === null && S.wrap.parentNode) { S.wrap.parentNode.removeChild(S.wrap); }
  };
  P.warn = function (m) { (this.warnings = this.warnings || []).push(m); if (w.console && w.console.warn) { w.console.warn('KIT3D: ' + m); } };

  /* the scene's box (the spec's "box", else every part) and each part's own */
  P.measure = function () {
    var S = this, bx = new T.Box3(), tmp = new T.Box3(), im = new T.Matrix4();
    each(S.parts, function (p) {
      p.box = new T.Box3();
      p.items.forEach(function (m) {
        if (m.isLine || m.isLineSegments || m.userData.noFrame) { return; }
        if (m.isInstancedMesh) {                  /* r128 boxes an instanced mesh by its one shape: each copy instead */
          if (!m.geometry.boundingBox) { m.geometry.computeBoundingBox(); }
          for (var i = 0; i < m.count; i++) {
            m.getMatrixAt(i, im);
            tmp.copy(m.geometry.boundingBox).applyMatrix4(im).applyMatrix4(m.matrixWorld);
            p.box.union(tmp);
          }
          return;
        }
        tmp.setFromObject(m);
        if (!tmp.isEmpty()) { p.box.union(tmp); }
      });
      if (!p.box.isEmpty() && !p.noFrame) { bx.union(p.box); }
    });
    each(S.parts, function (p) {            /* a parent's box holds its kids */
      if (p.parent && S.parts[p.parent] && !p.box.isEmpty()) { S.parts[p.parent].box.union(p.box); }
    });
    if (S.spec.box && S.spec.box.length === 6) {
      var b = S.spec.box;
      bx.set(new T.Vector3(b[0], b[1], b[2]), new T.Vector3(b[3], b[4], b[5]));
    }
    if (bx.isEmpty()) { bx.set(new T.Vector3(-1, -1, -1), new T.Vector3(1, 1, 1)); }
    S.box = bx;
  };

  /* the sun stands up and to the front-left of the scene; its shadow box covers the scene */
  P.light = function () {
    var S = this, c = new T.Vector3(), sz = new T.Vector3();
    S.box.getCenter(c); S.box.getSize(sz);
    var R = 0.5 * sz.length() + 0.5, sun = S.sun, dir = v3(S.spec.sun, [0.45, 0.75, 0.5]);
    var dv = new T.Vector3(dir[0], dir[1], dir[2]).normalize();
    sun.position.set(c.x + dv.x * R * 2.2, c.y + dv.y * R * 2.2, c.z + dv.z * R * 2.2);
    sun.target.position.copy(c);
    sun.shadow.camera.left = -R; sun.shadow.camera.right = R; sun.shadow.camera.top = R; sun.shadow.camera.bottom = -R;
    sun.shadow.camera.near = 0.1; sun.shadow.camera.far = R * 4.5;
    sun.shadow.camera.updateProjectionMatrix();
    sun.shadow.normalBias = 0.03 * Math.max(0.3, Math.min(2, R / 20));
    /* 2.68.0 - the model stands on something: an unseen ground just under its lowest point that shows only the shadow the
       model throws on it (owner: "3D models so it looks better but not lagging"). The shadows are worked out once, so it
       costs nothing while the model turns; it is never framed, never tapped, never merged. "ground": false leaves it out */
    /* never under a scene that has a floor of its own (a deck, a bottom shell: a broad flat part at its foot) - there the
       ground only showed stray shadow beyond the deck's edge (the m15 venting and m03 station examples) */
    var floored = false;
    each(S.parts, function (p) {
      if (floored || !p.box || p.box.isEmpty()) { return; }
      var ps = new T.Vector3();
      p.box.getSize(ps);
      if (ps.x >= 0.6 * sz.x && ps.z >= 0.6 * sz.z && ps.y <= 0.2 * sz.y + 0.01 && p.box.min.y <= S.box.min.y + 0.1 * sz.y + 0.01) {
        floored = true;
      }
    });
    if (S.groundMesh) { S.groundMesh.visible = !floored; }
    if (S.shadows && S.spec.ground !== false && !floored) {
      if (!S.groundMesh) {
        var gm = new T.Mesh(new T.PlaneGeometry(1, 1), new T.ShadowMaterial({ opacity: num(S.spec.ground_shadow, 0.24) }));
        gm.rotation.x = -Math.PI / 2;
        gm.receiveShadow = true; gm.castShadow = false;
        gm.userData.keep = true; gm.userData.noFrame = true;
        gm.raycast = function () {};
        S.scene.add(gm);
        S.groundMesh = gm;
      }
      S.groundMesh.scale.set(R * 2.6, R * 2.6, 1);
      S.groundMesh.position.set(c.x, S.box.min.y - Math.max(0.002, sz.y * 0.002), c.z);
    }
  };

  /* static meshes of one part and one material become ONE mesh (the hand-made M05's bake): fewer draw calls on a tablet */
  P.merge = function () {
    var S = this, groups = {};
    S.root.traverse(function (m) {
      if (!m.isMesh || m.isInstancedMesh || m.userData.keep || !m.geometry || !m.geometry.isBufferGeometry) { return; }
      if (m.material.transparent || Array.isArray(m.material) || m.geometry.morphAttributes.position) { return; }
      var key = (m.userData.part || '') + '|' + m.material.uuid + '|' + (m.castShadow ? 1 : 0) + (m.receiveShadow ? 1 : 0) + '|' +
        (m.renderOrder || 0) + '|' + (m.userData.noPick ? 1 : 0);
      (groups[key] = groups[key] || []).push(m);
    });
    var nm = new T.Matrix3();
    each(groups, function (ms) {
      if (ms.length < 2) { return; }
      var n = 0, i, j, gg = [], pos, nor, out, outN, o = 0, g, a, b, m0 = ms[0];
      for (i = 0; i < ms.length; i++) {
        g = ms[i].geometry.index ? ms[i].geometry.toNonIndexed() : ms[i].geometry;
        if (!g.attributes.normal) { g.computeVertexNormals(); }
        gg.push(g); n += g.attributes.position.count;
      }
      out = new Float32Array(n * 3); outN = new Float32Array(n * 3);
      var v = new T.Vector3();
      for (i = 0; i < ms.length; i++) {
        ms[i].updateMatrixWorld(true);
        nm.getNormalMatrix(ms[i].matrixWorld);
        pos = gg[i].attributes.position; nor = gg[i].attributes.normal;
        var flip = ms[i].matrixWorld.determinant() < 0;     /* a mirrored piece: each triangle turned back to face out */
        for (j = 0; j < pos.count; j++) {
          a = flip ? (j % 3 === 1 ? j + 1 : j % 3 === 2 ? j - 1 : j) : j;
          v.set(pos.getX(a), pos.getY(a), pos.getZ(a)).applyMatrix4(ms[i].matrixWorld);
          out[o] = v.x; out[o + 1] = v.y; out[o + 2] = v.z;
          v.set(nor.getX(a), nor.getY(a), nor.getZ(a)).applyMatrix3(nm).normalize();
          outN[o] = v.x; outN[o + 1] = v.y; outN[o + 2] = v.z;
          o += 3;
        }
        if (gg[i] !== ms[i].geometry) { gg[i].dispose(); }
      }
      g = new T.BufferGeometry();
      g.setAttribute('position', new T.BufferAttribute(out, 3));
      g.setAttribute('normal', new T.BufferAttribute(outN, 3));
      S.geos.push(g);
      var mm = new T.Mesh(g, m0.material);
      mm.castShadow = m0.castShadow; mm.receiveShadow = m0.receiveShadow; mm.renderOrder = m0.renderOrder;
      mm.userData.part = m0.userData.part; mm.userData.noPick = m0.userData.noPick; mm.userData.merged = ms.length;
      S.root.add(mm);
      var part = S.parts[m0.userData.part];
      for (i = 0; i < ms.length; i++) {
        if (ms[i].parent) { ms[i].parent.remove(ms[i]); }
        if (part) { a = part.items.indexOf(ms[i]); if (a >= 0) { part.items.splice(a, 1); } }
      }
      if (part) { part.items.push(mm); }
    });
  };

  /* ======================================================================== camera: fit a box to the canvas */
  P.basis = function (az, el0) {
    var dir = new T.Vector3(Math.sin(az) * Math.cos(el0), Math.sin(el0), Math.cos(az) * Math.cos(el0));
    var f = dir.clone().negate(), r = new T.Vector3().crossVectors(f, new T.Vector3(0, 1, 0)).normalize();
    var u = new T.Vector3().crossVectors(r, f).normalize();
    return { dir: dir, r: r, u: u };
  };
  /* the room the scene may use in the canvas: the labels above it, the controls below, the box edge */
  P.reserve = function () {
    var S = this, W = S.W || 640, H = S.H || 400, top = num(S.spec.frame && S.spec.frame.top, 56);
    var bot = 16, ch = S.ctl && S.ctl.offsetHeight ? S.ctl.offsetHeight + 20 : 0, cw = S.ctl && S.ctl.offsetWidth || 0, x1 = W - 16;
    if (S.cap && S.cap.offsetHeight) { top = Math.max(top, S.cap.offsetHeight + 24); }   /* the caption, top left */
    top = Math.min(top, H * 0.2);
    if (S.spec.controls_at === 'right' && cw) { x1 = W - Math.min(cw + 28, W * 0.3); }   /* a column of buttons takes the right */
    else if (ch && cw > W * 0.55) { bot = ch; }             /* a wide control bar takes the bottom; a small one sits in a corner */
    else if (ch) {
      /* ... and the model keeps off it too (the Labels button lay over the end of the model, gas trial M01 s04): the strip
         beside it or the strip above it, whichever leaves the model more room - a wide low band gives up the strip beside it */
      var side = W - cw - 28;
      if (ch > H * 0.25 || (side - 16) * (H - 16 - top) > (W - 32) * (H - ch - top)) { x1 = side; } else { bot = ch; }
    }
    bot = Math.min(bot, ch && cw > W * 0.55 ? H * 0.34 : H * 0.25);   /* a bar of buttons: never over the model */
    return { x0: 16, x1: x1, y0: top, y1: H - bot };
  };
  /* the distance and target that show box b from (az, el) as large as fill allows inside the reserve */
  P.fit = function (b, az, el0, fill) {
    var S = this, bs = S.basis(az, el0), c = new T.Vector3(), corners = [], i;
    b.getCenter(c);
    var mn = b.min, mx = b.max;
    for (i = 0; i < 8; i++) {
      var p = new T.Vector3(i & 1 ? mx.x : mn.x, i & 2 ? mx.y : mn.y, i & 4 ? mx.z : mn.z).sub(c);
      corners.push([p.dot(bs.r), p.dot(bs.u), p.dot(bs.dir)]);
    }
    var W = S.W || 640, H = S.H || 400, rs = S.reserve(), th = Math.tan(S.camera.fov * DEG / 2), asp = W / H;
    var nx0 = rs.x0 / W * 2 - 1, nx1 = rs.x1 / W * 2 - 1, ny0 = 1 - rs.y1 / H * 2, ny1 = 1 - rs.y0 / H * 2;
    var hw = (nx1 - nx0) / 2 * (fill || 0.94), hh = (ny1 - ny0) / 2 * (fill || 0.94), cx = (nx0 + nx1) / 2, cy = (ny0 + ny1) / 2;
    var sx = 0, sy = 0, D = 0, it, q, x, y, minx, maxx, miny, maxy, z;
    /* the room's sides seen from the middle of the canvas, where the target is: a room off the middle (the controls'
       strip, the labels' band) has a near side and a far one - each corner is fitted to the side it lies towards */
    var xr = Math.max(hw + cx, 0.05), xl = Math.max(hw - cx, 0.05), yt = Math.max(hh + cy, 0.05), yb = Math.max(hh - cy, 0.05);
    for (it = 0; it < 6; it++) {
      D = 0;                                             /* the closest distance where every corner fits the room */
      for (i = 0; i < 8; i++) {
        q = corners[i]; x = q[0] - sx; y = q[1] - sy;
        D = Math.max(D, q[2] + (x > 0 ? x / xr : -x / xl) / (th * asp), q[2] + (y > 0 ? y / yt : -y / yb) / th);
      }
      minx = miny = 1e9; maxx = maxy = -1e9;
      for (i = 0; i < 8; i++) {
        q = corners[i]; z = Math.max(D - q[2], 1e-3);
        x = (q[0] - sx) / (z * th * asp); y = (q[1] - sy) / (z * th);
        minx = Math.min(minx, x); maxx = Math.max(maxx, x); miny = Math.min(miny, y); maxy = Math.max(maxy, y);
      }
      /* move the target so the picture sits in the middle of the room it has */
      sx += ((minx + maxx) / 2 - cx) * D * th * asp * 0.9;
      sy += ((miny + maxy) / 2 - cy) * D * th * 0.9;
    }
    var t = c.clone().addScaledVector(bs.r, sx).addScaledVector(bs.u, sy);
    return { d: Math.max(D, 0.01), tx: t.x, ty: t.y, tz: t.z };
  };
  /* a step's or the home view: angles in degrees, a box from "frame" (parts) or the whole scene; n: the step it is for */
  P.viewFor = function (vw, n) {
    var S = this, v = vw || {}, home = S.spec.view || {};
    var az = num(v.az, num(home.az, 30)) * DEG, el0 = num(v.el, num(home.el, 24)) * DEG;
    var b = S.box;
    if (v.frame && v.frame.length) { b = S.stepBox(v.frame, n) || S.box; }
    var f = S.fit(b, az, el0, num(v.fill, num(home.fill, 0.94)));
    if (b !== S.box) {
      /* a close-up that brings its parts less than CLOSE_UP times nearer than the whole model does only cuts the model at
         the box edge (gas trial M01 s12: one of four rooms side by side in a wide low band, 1.8 times nearer, the rest ran
         off under the Labels button; s15: the airlock 2.9 times nearer, the room beside it blown up past the edge) - the
         step shows the whole model, its part still the one selected */
      var whole = S.box.clone().union(b), fw = S.fit(whole, az, el0, num(v.fill, num(home.fill, 0.94)));
      if (f.d * CLOSE_UP > fw.d) { f = fw; }
    }
    if (!v.frame || !v.frame.length) { S.fitDist = f.d; }
    var zoom = (f.d / (S.fitDist || f.d)) * num(v.zoom, 1);
    if (v.target) { f.tx = v.target[0]; f.ty = v.target[1]; f.tz = v.target[2]; }
    return { az: az, el: el0, zoom: zoom, tx: f.tx, ty: f.ty, tz: f.tz };
  };
  P.boxOf = function (keys) {
    var S = this, b = new T.Box3();
    keys.forEach(function (k0) {
      var p = S.parts[k0];
      if (p && p.box && !p.box.isEmpty()) { b.union(p.box); }
      else if (S.spec.groups && S.spec.groups[k0]) { var g = S.boxOf(S.spec.groups[k0]); if (g) { b.union(g); } }
    });
    return b.isEmpty() ? null : b;
  };
  /* what a step frames: its "frame" parts, and with them the whole of the part it selects and the points of the labels it
     names - a Moss sphere above its hull is never cut at the top edge, its label never off the picture (gas trial M01 s09) */
  P.stepBox = function (frame, n) {
    var S = this, b = S.boxOf(frame), st = n != null ? S.steps()[n] : null;
    if (!b || !st) { return b; }
    b = b.clone();
    [].concat(st.select || []).forEach(function (k0) { var sb = S.boxOf(S.keysOf(k0)); if (sb) { b.union(sb); } });
    (S.labels || []).forEach(function (l) {
      if (l.tag || l.tapOnly || l.when) { return; }
      if (l.steps ? l.steps.indexOf(n) >= 0 : (st.labels && st.labels.indexOf(l.key) >= 0)) { b.expandByPoint(l.v); }
    });
    return b;
  };
  P.homeFit = function () {
    var S = this, v = (S.spec.view || {});
    S.home = S.viewFor({ az: v.az, el: v.el });
  };
  P.applyCamera = function () {
    var S = this, v = S.view, bx = S.box, sz = new T.Vector3();
    bx.getSize(sz);
    var m = 0.25 * Math.max(sz.x, sz.y, sz.z);
    v.el = clamp(v.el, num(S.spec.min_el, 2) * DEG, num(S.spec.max_el, 82) * DEG);
    v.zoom = clamp(v.zoom, num(S.spec.min_zoom, 0.06), num(S.spec.max_zoom, 1.5));
    v.tx = clamp(v.tx, bx.min.x - m, bx.max.x + m); v.ty = clamp(v.ty, bx.min.y - m, bx.max.y + m); v.tz = clamp(v.tz, bx.min.z - m, bx.max.z + m);
    var dd = S.fitDist * v.zoom, ce = Math.cos(v.el), cam = S.camera;
    cam.position.set(v.tx + dd * Math.sin(v.az) * ce, v.ty + dd * Math.sin(v.el), v.tz + dd * Math.cos(v.az) * ce);
    cam.near = Math.max(0.02, dd * 0.02); cam.far = dd * 6 + sz.length() * 3;
    cam.updateProjectionMatrix();
    cam.lookAt(v.tx, v.ty, v.tz);
    cam.updateMatrixWorld();
  };
  P.resize = function () {
    var S = this, W = S.wrap.clientWidth || 640, H = S.wrap.clientHeight || 400;
    if (W === S.W && H === S.H) { return false; }
    S.W = W; S.H = H;
    S.size(W, H);
    S.camera.aspect = W / H;
    S.camera.updateProjectionMatrix();
    S.dense = false;                                    /* judged again at the new size (settle) */
    /* 2.69.0 - a slide's column (gas M01 s26 at 1280x720: 640 x 440 with nine names and six buttons - the model hidden under
       them): under 720 x 460 the names and the buttons are the compact ones */
    var small = W < 720 || H < 460;
    if (small !== S.small) { S.small = small; setCls(S.wrap, 'k3-small', small); S.labels.forEach(function (l) { l.pw = 0; }); }
    S.homeFit();
    /* the view follows its box: a step's view is fitted again; a view the presenter turned keeps its turn */
    if (!S.free && !S.tween) { S.setView(S.target()); }
    return true;
  };

  /* the drawing buffer, only when its size changes: a new antialiased buffer cost ~1 s with the CPU slowed 4x in software
     GL (perf3d, IGF M01 kit port) - so it is made at the box's size while the slide before is on screen */
  P.size = function (W, H) {
    var S = this;
    S.bufW = W; S.bufH = H;
    /* 2.70.0 - a pixel budget (owner: "better ... but not lagging"): at most ~2.4 million pixels a frame. A slide's box keeps
       twice the screen's pixels; full screen on a sharp tablet (2560 x 1600) is drawn at 1.5x, still smoothed - about half
       the work for the graphics chip, the part of the frame a slow tablet spends longest on. steady() may step it down further */
    var pr = Math.min(w.devicePixelRatio || 1, 2, S.dpr || GL.dpr || 2, Math.sqrt(PIXEL_BUDGET / Math.max(1, W * H)));
    pr = Math.max(1, Math.round(pr * 4) / 4);
    /* the one renderer is sized by the scene that draws: a new buffer only when this scene's size or sharpness differs */
    var now0 = S.r.getSize(GL.v2 || (GL.v2 = new T.Vector2()));
    if (now0.x !== W || now0.y !== H || S.r.getPixelRatio() !== pr) { S.r.setDrawingBufferSize(W, H, pr); }
  };
  /* the size the stage will have when its slide shows: the slide laid out for a moment, unseen, as the one on screen is */
  P.measureHidden = function () {
    var S = this, slide = slideOf(S.stage), out = { w: S.stage.clientWidth, h: S.stage.clientHeight };
    if (out.w && out.h) { return out; }
    if (!slide || !slide.parentNode) { return out; }
    var shown = null, sib = slide.parentNode.children, i;
    for (i = 0; i < sib.length; i++) { if (sib[i] !== slide && sib[i].offsetWidth && /\bslide\b/.test(sib[i].className)) { shown = sib[i]; break; } }
    var old = slide.getAttribute('style');
    slide.style.visibility = 'hidden';
    slide.style.display = shown && w.getComputedStyle ? w.getComputedStyle(shown).display : 'block';
    out = { w: S.stage.clientWidth, h: S.stage.clientHeight };
    if (old == null) { slide.removeAttribute('style'); } else { slide.setAttribute('style', old); }
    return out;
  };

  /* what the camera should show now: the tapped part, else the step's view */
  P.target = function () {
    var S = this, st = S.steps()[S.step] || {};
    if (S.sel) { return S.frameSel(S.sel); }
    return st.view ? S.viewFor(st.view, S.step) : S.home;
  };
  P.frameSel = function (key) {
    var S = this, keys = S.keysOf(key), b = S.boxOf(keys), base = S.view, sz = new T.Vector3(), c = new T.Vector3();
    if (!b) { return S.home; }
    S.box.getSize(sz);
    var h = 0.07 * sz.length();                  /* never closer than a part 14 % of the scene across: a bolt is seen with its pipe */
    b = b.clone(); b.getCenter(c);
    b.expandByPoint(c.clone().addScalar(h)); b.expandByPoint(c.clone().addScalar(-h));
    var p = S.parts[key] || {}, az = p.az != null ? p.az * DEG : base.az, el0 = p.el != null ? p.el * DEG : clamp(base.el, 0.15, 0.9);
    var f = S.fit(b, az, el0, num(S.spec.pick_fill, 0.62));
    return { az: az, el: el0, zoom: clamp(f.d / S.fitDist, num(S.spec.min_zoom, 0.06), 1.2), tx: f.tx, ty: f.ty, tz: f.tz };
  };
  P.setView = function (to) { var v = this.view; v.az = to.az; v.el = to.el; v.zoom = to.zoom; v.tx = to.tx; v.ty = to.ty; v.tz = to.tz; };
  P.copyView = function () { var v = this.view; return { az: v.az, el: v.el, zoom: v.zoom, tx: v.tx, ty: v.ty, tz: v.tz }; };

  /* ======================================================================== states, glow, tween */
  P.setState = function (name, v) {
    var st = this.states[name];
    if (!st) { return; }
    st.v = v;
    st.fns.forEach(function (fn) { fn(v); });
  };
  /* a picked part (a = 1) keeps its own colour, lit from within in that colour with a little of the kit's blue, and a
     see-through one turns more solid; while a part is picked the others (a = -1) step back, a little darker - the part
     being taught is the clearest thing on the screen, never a pale wash */
  var GLOW = null, HUE = null, DIM = 0.3;
  P.glow = function (p, a) {
    var i, m, up = Math.max(0, a), dn = Math.max(0, -a), base;
    if (!GLOW) { GLOW = Builder.prototype.col(BLUE); HUE = new T.Color(); }
    p.g = a;
    for (i = 0; i < p.mats.length; i++) {
      m = p.mats[i];
      if (m.userData.glow) { m.userData.glow(up); continue; }
      if (!m.userData.c0) { continue; }
      m.color.copy(m.userData.c0).multiplyScalar(1 - DIM * dn);
      if (m.emissive) {
        HUE.copy(m.userData.c0).lerp(GLOW, 0.3);
        m.emissive.copy(m.userData.e0 || HUE).lerp(HUE, up);
        m.emissiveIntensity = (m.userData.ei0 || 0) * (1 - up) * (1 - DIM * dn) + up * 0.2;
      }
      /* on top of the opacity the part has now (a ghost or a cut state sets its own): what the glow added is taken back */
      base = m.opacity === m.userData.os ? m.opacity - m.userData.oa : m.opacity;
      m.userData.oa = base < 1 ? (1 - base) * 0.75 * up : 0;
      m.opacity = m.userData.os = base + m.userData.oa;
    }
  };
  /* the parts a key lights: the part and its kids, or a group's parts */
  P.keysOf = function (key) {
    var S = this, out = [], g = S.spec.groups && S.spec.groups[key];
    (g ? g : [key]).forEach(function (k0) {
      if (out.indexOf(k0) < 0) { out.push(k0); }
      var p = S.parts[k0];
      if (p) { p.kids.forEach(function (c) { if (out.indexOf(c) < 0) { out.push(c); } }); }
    });
    return out;
  };
  /* go: to a camera view, state values and the lit parts, together in one tween (750 ms, ease in-out) */
  P.go = function (to, states, lit) {
    var S = this, from = S.copyView(), s0 = {}, s1 = {};
    each(states || {}, function (v, n) { if (S.states[n]) { s0[n] = S.states[n].v; s1[n] = v; } });
    S.lit = {};
    (lit || []).forEach(function (k0) { S.keysOf(k0).forEach(function (x) { S.lit[x] = true; }); });
    var any = Object.keys(S.lit).length > 0;
    each(S.parts, function (p) { p.g0 = p.g; p.g1 = S.lit[p.id] ? 1 : any ? -1 : 0; });
    S.pillsLit();
    if (reduce || !S.live) {
      if (to) { S.setView(to); }
      each(s1, function (v, n) { S.setState(n, v); });
      each(S.parts, function (p) { S.glow(p, p.g1); });
      S.tween = null;
    } else {
      S.tween = { t0: now(), dur: 750, from: from, to: to || from, s0: s0, s1: s1 };
    }
    S.schedule();
  };
  P.tweenStep = function () {
    var S = this, tw = S.tween;
    if (!tw) { return false; }
    var u = clamp((now() - tw.t0) / tw.dur, 0, 1), e = ease(u), f = tw.from, t = tw.to, v = S.view, da = t.az - f.az;
    if (da > Math.PI) { da -= 2 * Math.PI; } else if (da < -Math.PI) { da += 2 * Math.PI; }
    v.az = f.az + da * e; v.el = f.el + (t.el - f.el) * e; v.zoom = f.zoom + (t.zoom - f.zoom) * e;
    v.tx = f.tx + (t.tx - f.tx) * e; v.ty = f.ty + (t.ty - f.ty) * e; v.tz = f.tz + (t.tz - f.tz) * e;
    each(tw.s1, function (b, n) { S.setState(n, tw.s0[n] + (b - tw.s0[n]) * e); });
    each(S.parts, function (p) { if (p.g !== p.g1 || p.g0 !== p.g1) { S.glow(p, p.g0 + (p.g1 - p.g0) * e); } });
    if (u >= 1) { S.tween = null; return false; }
    return true;
  };
  P.endTween = function () {
    var S = this, tw = S.tween;
    if (!tw) { return; }
    each(tw.s1, function (b, n) { S.setState(n, b); });
    each(S.parts, function (p) { p.g0 = p.g1; S.glow(p, p.g1); });
    S.tween = null;
  };

  /* ======================================================================== steps, selection, controls */
  P.steps = function () { return this.spec.steps && this.spec.steps.length ? this.spec.steps : [{}]; };
  /* the states a step means: the spec's starting states, then every step's up to this one */
  P.stepStates = function (n) {
    var S = this, out = {}, i, st = S.steps();
    each(S.states, function (s, name) { out[name] = s.v0; });
    each(S.spec.states || {}, function (v, name) { out[name] = v; });
    for (i = 0; i <= n && i < st.length; i++) { each(st[i].state || {}, function (v, name) { out[name] = v; }); }
    each(S.toggled || {}, function (v, name) { out[name] = v; });
    return out;
  };
  P.goStep = function (n, instant) {
    var S = this, st = S.steps(), s;
    n = clamp(n, 0, st.length - 1);
    S.step = n; s = st[n];
    S.sel = null; S.free = false; S.toggled = {};
    var to = s.view ? S.viewFor(s.view, n) : S.home;
    if (instant) { var lv = S.live; S.live = false; S.go(to, S.stepStates(n), s.select ? [].concat(s.select) : []); S.live = lv; }
    else { S.go(to, S.stepStates(n), s.select ? [].concat(s.select) : []); }
    S.ctlSync();                                       /* a step that cuts the pipe open shows its button pressed */
    S.animsFor(n);
    if (S.onStep) { S.onStep(n); }
    S.syncDeck();
  };
  /* a tap on a part or on its label: it glows, its pill lights, the camera frames it; the same again lets it go */
  P.select = function (key) {
    var S = this;
    if (key && !(S.parts[key] || (S.spec.groups && S.spec.groups[key]))) { return; }
    if (!key || key === S.sel) {
      S.sel = null;
      var st = S.steps()[S.step] || {};
      S.go(S.opt.keepView ? null : st.view ? S.viewFor(st.view, S.step) : S.home, null, st.select ? [].concat(st.select) : []);
    } else {
      S.sel = key;
      S.go(S.opt.keepView ? null : S.frameSel(key), null, [key]);
    }
    S.free = false;
    S.ctlSync();
    S.pillsLit();
    S.syncDeck();
    /* 2.74.0 - a tablet task (gb_interact.js) is told what was tapped; keepView: the camera stays where the trainee put it */
    if (S.opt.onSelect) { try { S.opt.onSelect(S.sel); } catch (e9) { /* the task's own */ } }
  };
  P.current = function () { return this.sel; };
  P.syncDeck = function () { if (w.GB3D && w.GB3D.sync && this.wired) { try { w.GB3D.sync(this.stage); } catch (e4) { /* deck */ } } };

  /* the controls: toggles that set states (with a view), buttons that select a group, or go to a step */
  P.controlsMake = function () {
    var S = this, list = S.spec.controls || [];
    S.btns = [];
    list.forEach(function (c) {
      var b = el('button', 'k3-btn', S.ctl);
      b.type = 'button';
      b.setAttribute('aria-pressed', 'false');
      b.appendChild(d.createTextNode(c.text || ''));
      b.__c = c;
      S.btns.push(b);
      S.listen(b, 'click', function (e) {
        e.preventDefault(); e.stopPropagation();
        S.control(c);
        if (e.detail && b.blur) { b.blur(); }      /* a mouse or a finger: the deck keeps its keys */
      });
    });
    if (S.spec.reset) {
      var r = el('button', 'k3-btn', S.ctl);
      r.type = 'button';
      r.appendChild(d.createTextNode(S.spec.reset === true ? 'Reset view' : S.spec.reset));
      S.listen(r, 'click', function (e) { e.preventDefault(); e.stopPropagation(); S.goStep(S.step); if (e.detail) { r.blur(); } });
    }
    /* "Labels": the instructor hides the names to ask the class what each part is, and shows them again (the hand-made
       M03, M07, M09, M15 had it; the review of the kit ports missed it, 2026-10-23). "labels_button": false leaves it out */
    if (S.spec.labels_button !== false && (S.spec.labels || []).length + S.autoLabels.length > 0) {
      var lb = el('button', 'k3-btn', S.ctl);
      lb.type = 'button';
      lb.setAttribute('aria-pressed', 'true');
      lb.appendChild(d.createTextNode(typeof S.spec.labels_button === 'string' ? S.spec.labels_button : 'Labels'));
      S.labelsBtn = lb;
      S.listen(lb, 'click', function (e) {
        e.preventDefault(); e.stopPropagation();
        S.labelsOff = !S.labelsOff;
        lb.setAttribute('aria-pressed', S.labelsOff ? 'false' : 'true');
        S.schedule();
        if (e.detail) { lb.blur(); }
      });
    }
    if (!S.ctl.children.length) { S.ctl.style.display = 'none'; }
  };
  P.control = function (c) {
    var S = this, on;
    if (c.select) { S.select(c.select); return; }
    if (c.step != null) { S.goStep(c.step); return; }
    if (c.state) {
      S.toggled = S.toggled || {};
      on = !S.ctlOn(c);
      var states = {};
      /* off: the step's own value - or the control's "off" ({"z0.on": 0}) when the step itself set it on */
      each(c.state, function (v, n) { states[n] = on ? v : (c.off && c.off[n] != null ? c.off[n] : S.stepStatesNoToggle(n)); S.toggled[n] = states[n]; });
      var to = null;
      if (on) { S.saved = S.copyView(); to = c.view ? S.viewFor(c.view) : null; }
      else { to = S.saved || null; S.saved = null; }
      if (S.sel && !S.keyShown(S.sel, states)) { S.sel = null; }
      S.go(to, states, S.sel ? [S.sel] : (S.steps()[S.step].select ? [].concat(S.steps()[S.step].select) : []));
      S.ctlSync(states);
      S.syncDeck();
    }
  };
  P.stepStatesNoToggle = function (n) {
    var S = this, t = S.toggled; S.toggled = {};
    var v = S.stepStates(S.step)[n];
    S.toggled = t;
    return v;
  };
  P.ctlOn = function (c, pending) {
    var S = this, on = !!c.state;
    if (c.select) { return S.sel === c.select; }
    if (c.step != null) { return S.step === c.step; }
    each(c.state || {}, function (v, n) {
      var cur = pending && pending[n] != null ? pending[n] : (S.tween && S.tween.s1[n] != null ? S.tween.s1[n] : (S.states[n] ? S.states[n].v : 0));
      if (Math.abs(cur - v) > 1e-3) { on = false; }
    });
    return on;
  };
  P.ctlSync = function (pending) {
    var S = this;
    (S.btns || []).forEach(function (b) {
      var c = b.__c, on = S.ctlOn(c, pending);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      if (c.text_on) { b.firstChild.nodeValue = on ? c.text_on : c.text; }
    });
  };
  /* is a part's label shown in these states (a cut-open part has no label while closed) */
  P.keyShown = function (key, pending) {
    var S = this, i, l;
    for (i = 0; i < S.labels.length; i++) {
      l = S.labels[i];
      if (l.key === key && S.labelWhen(l, pending)) { return true; }
    }
    return !S.labels.some(function (x) { return x.key === key; });
  };
  P.labelWhen = function (l, pending) {
    var S = this;
    if (!l.when) { return true; }
    if (!pending) { return test(S, l.when); }
    var saved = {};
    each(pending, function (v, n) { if (S.states[n]) { saved[n] = S.states[n].v; S.states[n].v = v; } });
    var r = test(S, l.when);
    each(saved, function (v, n) { S.states[n].v = v; });
    return r;
  };

  /* ======================================================================== labels on the parts */
  P.labelsMake = function () {
    var S = this, defs = (S.spec.labels || []).concat(S.autoLabels);
    S.labels = []; S.labKey = S.setKey = null; S.setFull = false;
    defs.forEach(function (ld) {
      var key = ld.part || '', p = S.parts[key], at = ld.at;
      if (!at && p) {
        at = p.anchors[ld.anchor || 'label'];
        if (!at && p.box && !p.box.isEmpty()) {
          var c = new T.Vector3(); p.box.getCenter(c);
          at = [c.x, p.box.max.y, c.z];
        }
      }
      if (!at) { S.warn('label "' + ld.text + '": no part "' + key + '" and no "at"'); return; }
      var up = num(ld.up, 48), L = { key: key, text: ld.text, when: ld.when, steps: ld.steps, tag: !!ld.tag, small: !!ld.small,
        v: new T.Vector3(at[0], at[1], at[2]), base: Math.abs(up), isUp: up > 0, gap: Math.abs(up), dx: 0, ox: num(ld.ox, 0),
        side: ld.side === 1 || ld.side === -1 ? ld.side : 0, dx0: num(ld.dx, 0), ups: ld.up_steps || null,
        isUp0: up > 0, base0: Math.abs(up),
        oy: num(ld.oy, 0), pw: 0, ph: 0, tapOnly: !!ld.tap_only };
      L.el = el('div', 'k3-lab k3-off', S.labelLayer);        /* not drawn until the first frame places it */
      if (!L.tag) { L.stem = el('div', 'k3-stem', L.el); L.dot = el('div', 'k3-dot', L.el); }
      L.pill = el('div', 'k3-pill' + (L.tag ? ' k3-tag' : '') + (L.tag && String(ld.text).length > 24 ? ' k3-wrap' : '') +
        (L.small ? ' k3-sm' : '') + (ld.tone ? ' k3-' + ld.tone : ''), L.el);     /* a long value tag wraps (IGF M15) */
      L.pill.appendChild(d.createTextNode(ld.text));
      if (key && ((p && p.pick) || (S.spec.groups && S.spec.groups[key]))) {
        L.pill.setAttribute('data-3d-part', key);
        L.pick = true;
      }
      S.labels.push(L);
    });
  };
  P.pillsLit = function () {
    var S = this;
    S.labels.forEach(function (l) {
      var on = !!l.key && !!S.lit[l.key] && (!S.sel || S.keysOf(S.sel).indexOf(l.key) >= 0);
      setCls(l.pill, 'k3-hl', on);
      if (l.pick && !S.wired) { l.pill.setAttribute('aria-pressed', S.sel === l.key ? 'true' : 'false'); }
    });
  };
  P.labelShown = function (l) {
    var S = this, st = S.steps()[S.step] || {};
    if (S.labelsOff && !(S.sel && S.keysOf(S.sel).indexOf(l.key) >= 0)) { return false; }   /* hidden: a tapped part still says its name */
    if (!S.labelWhen(l)) { return false; }
    if (l.steps && l.steps.indexOf(S.step) < 0) { return false; }
    if (st.labels && st.labels.indexOf(l.key) < 0 && !(S.sel && S.keysOf(S.sel).indexOf(l.key) >= 0)) { return false; }
    if (l.tapOnly && !S.lit[l.key]) { return false; }      /* lit by a tap, a label, a control or the step's own select */
    return true;
  };
  var tmpV = null;
  P.updateLabels = function () {
    var S = this, W = S.W, H = S.H;
    if (!tmpV) { tmpV = new T.Vector3(); }
    if (S.cap) {
      var cap = '';
      S.spec.captions.some(function (c) { if (c.text && test(S, c.when)) { cap = c.text; return true; } return false; });
      if (S.cap.textContent !== cap) { S.cap.textContent = cap; }
      if (S.cap.style.display !== (cap ? '' : 'none')) { S.cap.style.display = cap ? '' : 'none'; }
    }
    /* the labels are placed only when something on the picture moved - the view, a labelled point, the step, the size,
       the caption, which labels show: a flow or a pulse that redraws a standing view costs them nothing */
    var lay = W + 'x' + H + '|' + S.step + '|' + (S.small ? 's' : '') + '|' + (S.cap ? S.cap.textContent : ''), key = lay;
    S.labels.forEach(function (l) {
      var s = S.labelShown(l);
      if (s) {
        tmpV.copy(l.v).project(S.camera);
        l.sx = (tmpV.x * 0.5 + 0.5) * W; l.sy = (-tmpV.y * 0.5 + 0.5) * H;
        /* behind the camera, or off the picture: a point past the edge has no place for its pill inside the picture, and
           the pill was cut (a step that frames one tank left its neighbour's point just above the top) */
        if (tmpV.z > 1 || l.sx < 0 || l.sx > W || l.sy < 0 || l.sy > H) { s = false; }
      }
      if (s && S.outAt === W + 'x' + H + '|' + S.step && S.outs[l.text]) { s = false; }      /* stepped out (P.settle) */
      l.shown = s;
      key += s ? '|' + l.text + ':' + l.sx.toFixed(1) + ',' + l.sy.toFixed(1) : '|-';
    });
    if (key === S.labKey && S.setFull) { return; }
    /* the places the pills keep off are read from the page only when the view stands or the slide's layout changed - never
       in the frames of a turn, where a read after the last frame's writes would lay the page out again */
    if (lay !== S.labLay || key === S.labKey || !S.res) { S.keepOut(); }
    S.standing = key === S.labKey;                      /* nothing moved since the last frame: the view stands */
    S.labLay = lay; S.labKey = key;
    S.labels.forEach(function (l) {
      setCls(l.el, 'k3-off', !l.shown);
      if (!l.shown) { return; }
      var tf = 'translate(' + l.sx.toFixed(1) + 'px,' + l.sy.toFixed(1) + 'px)';
      if (l.tf !== tf) { l.el.style.transform = l.el.style.webkitTransform = l.tf = tf; }
    });
    S.settle();
    if (W && H) { S.labelLayer.style.visibility = 'visible'; }
  };
  /* the places a pill keeps off - the controls, the caption, the Full screen button - read before the labels move in this
     frame: read after, each frame paid a whole layout of the page (perf_gate: a fifth of a turn's time at 4x) */
  P.keepOut = function () {
    var S = this, W = S.W, H = S.H, res = [], lr = S.labelLayer.getBoundingClientRect();
    function rectOf(e2, pad) {
      var r = e2.getBoundingClientRect();
      return { x1: r.left - lr.left - pad, y1: r.top - lr.top - pad, x2: r.right - lr.left + pad, y2: r.bottom - lr.top + pad };
    }
    if (S.ctl.offsetWidth) { res.push(rectOf(S.ctl, 8)); }
    if (S.cap && S.cap.offsetWidth) { res.push(rectOf(S.cap, 6)); }
    var box = S.stage.closest ? S.stage.closest('.gb-fs3d') || S.stage.parentNode : S.stage.parentNode;
    var fb = box && box.querySelector ? box.querySelector('.gb-fs3d-btn') : null;
    if (fb && fb.offsetWidth) { res.push(rectOf(fb, 6)); } else { res.push({ x1: W - 60, y1: 0, x2: W, y2: 60 }); }
    S.res = res;
  };
  /* Every label that touches another pill, stem or dot, a control, the Full screen button, the top-right corner
     or the box edge tries other stem lengths, the other side of its point and a sideways shift, and takes the place
     where the least touches and the stem changes least (the hand-made settleLabels, IGF slide review 2026-10-22). */
  P.settle = function () {
    var S = this, W = S.W, H = S.H, res = S.res || [], shown = [], i, k0, a, pass, outAt = W + 'x' + H + '|' + S.step;
    S.labels.forEach(function (l) {
      if (!l.shown) { return; }
      var j, r0;
      for (j = 0; j < res.length; j++) {                /* its point is under a button: it names nothing the class sees */
        r0 = res[j];
        if (l.sx > r0.x1 && l.sx < r0.x2 && l.sy > r0.y1 && l.sy < r0.y2) { l.shown = false; setCls(l.el, 'k3-off', true); return; }
      }
      if (!l.pw) { l.pw = l.pill.offsetWidth; l.ph = l.pill.offsetHeight; }
      var u0 = l.ups && l.ups[S.step] != null ? l.ups[S.step] : null;     /* "up_steps": {"1": -40} - this step's stem */
      l.isUp = u0 != null ? u0 > 0 : l.isUp0; l.base = u0 != null ? Math.abs(u0) : l.base0;
      l.up = l.isUp; l.gap = l.base; l.dx = 0;
      shown.push(l);
    });
    /* 2.75.2 - nothing on the picture moved since the last settle (a gas flow or a pulse redraws the frame, the view stands):
       the pills keep their places, no search. While the view moves, one order is tried; every order once it is at rest (one
       more frame is asked for). Was every order on every frame of a turn the presenter did not drag: m01 23 ms a frame */
    var key = W + 'x' + H + '|' + S.step + '|' + (S.small ? 's' : '') + '|' + (S.cap ? S.cap.textContent : '') + '|' +
      shown.map(function (l) { return l.text + ':' + Math.round(l.sx) + ',' + Math.round(l.sy); }).join(';');
    var still = key === S.setKey;
    if (still && S.setFull) {
      shown.forEach(function (l) { if (l.f) { l.up = l.f[0]; l.gap = l.f[1]; l.dx = l.f[2]; l.oy = l.f[3]; } });
      return;
    }
    /* while the view turns, the places are searched again only after 100 ms, or three times as long as the last search took;
       between, each pill keeps its place round its moving point (perf_gate, a turn at 4x: the search was a third to half of
       every frame, 15 labels 130 ms a search). A search that took longer than TURN_SEARCH_MS is not made in a turn at all:
       crowded labels on a thin layer (the membrane tank's four) took up to 200 ms each, a frame of the turn every 100 ms
       held for it - p95 three frames in perf_gate. At rest the full search follows, as before - only while the view moves is
       a search put off: a view that stands after a step is searched however long the last search took (the factory trial,
       M01 s16 and M19 s03: a slow search kept every later step's pills at the places of the step before, cut at the box's
       edge and on top of each other) */
    var tn = now();
    if (!still && !S.standing && S.setT && (tn - S.setT < Math.max(100, 3 * (S.setCost || 0)) || S.setCost > TURN_SEARCH_MS)
        && shown.every(function (l) { return !!l.f; })) {
      shown.forEach(function (l) { l.up = l.f[0]; l.gap = l.f[1]; l.dx = l.f[2]; l.oy = l.f[3]; });
      S.setFull = false;
      S.schedule();
      return;
    }
    function pillR(l) {
      if (l.tag) { var tx = l.sx + l.ox + l.dx - l.pw / 2, ty = l.sy + l.oy - l.ph / 2; return { x1: tx, y1: ty, x2: tx + l.pw, y2: ty + l.ph }; }
      var x1 = l.sx - l.pw / 2 + l.dx, y1 = l.up ? l.sy - l.gap - l.ph : l.sy + l.gap;
      return { x1: x1, y1: y1, x2: x1 + l.pw, y2: y1 + l.ph };
    }
    function stemR(l) { return l.tag ? null : { x1: l.sx - 2, y1: Math.min(l.sy, l.up ? l.sy - l.gap : l.sy + l.gap), x2: l.sx + 2, y2: Math.max(l.sy, l.up ? l.sy - l.gap : l.sy + l.gap) }; }
    function dotR(l) { return l.tag ? null : { x1: l.sx - 8, y1: l.sy - 8, x2: l.sx + 8, y2: l.sy + 8 }; }
    function hit(p, q, pad) { return !!p && !!q && p.x1 < q.x2 + pad && q.x1 < p.x2 + pad && p.y1 < q.y2 + pad && q.y1 < p.y2 + pad; }
    /* the parts on the picture (their screen boxes, a large space or hull left out): a pill is placed off them where it
       can be - not stacked on the tank it is about (IGF M02 review, 2026-10-23) */
    var obst = [], pv = new T.Vector3();
    each(S.parts, function (p) {
      if (!p.pick || !p.box || p.box.isEmpty()) { return; }
      var b = p.box, q, x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (q = 0; q < 8; q++) {
        pv.set(q & 1 ? b.max.x : b.min.x, q & 2 ? b.max.y : b.min.y, q & 4 ? b.max.z : b.min.z).project(S.camera);
        x0 = Math.min(x0, (pv.x * 0.5 + 0.5) * W); x1 = Math.max(x1, (pv.x * 0.5 + 0.5) * W);
        y0 = Math.min(y0, (-pv.y * 0.5 + 0.5) * H); y1 = Math.max(y1, (-pv.y * 0.5 + 0.5) * H);
      }
      if ((x1 - x0) * (y1 - y0) < 0.2 * W * H) { obst.push({ x1: x0, y1: y0, x2: x1, y2: y1, key: p.id, up: p.parent }); }
    });
    /* how many parts' pictures the pill sits a third or more on - another part's twice its own: a name on the tap's
       handwheel reads as the tap's name, wherever its stem goes */
    function cover(l) {
      var p = pillR(l), n = 0, j, o, ix, iy, area = l.pw * l.ph || 1, me = S.parts[l.key], up = me && me.parent;
      for (j = 0; j < obst.length; j++) {
        o = obst[j];
        ix = Math.min(p.x2, o.x2) - Math.max(p.x1, o.x1); iy = Math.min(p.y2, o.y2) - Math.max(p.y1, o.y1);
        if (ix > 0 && iy > 0 && ix * iy > area / 3) { n += o.key === l.key || o.key === up || o.up === l.key ? 1 : 2; }
      }
      return n;
    }
    function confl(l) {
      var n = 0, p = pillR(l), s = stemR(l), j, b, bp;
      for (j = 0; j < res.length; j++) { if (hit(p, res[j], 4) || hit(s, res[j], 0)) { n++; } }
      /* a pill past the box's edge is cut, its name unread: worse than any number of touches (fit gate, 1024 x 768) */
      if (p.y1 < 4 || p.y2 > H - 4 || p.x1 < 4 || p.x2 > W - 4) { n += EDGE; }
      for (j = 0; j < shown.length; j++) {
        b = shown[j];
        if (b === l) { continue; }
        bp = pillR(b);
        if (hit(p, bp, 6)) { n++; }
        if (hit(s, bp, 2)) { n++; }
        if (hit(stemR(b), p, 2)) { n++; }
        if (hit(dotR(l), bp, 0)) { n++; }
        if (hit(dotR(b), p, 0)) { n++; }
        /* two stems in one column, or a stem through another label's dot: the lines cross and each name points at the
           other's part */
        if (hit(s, stemR(b), 0)) { n++; }
        if (hit(s, dotR(b), -3) || hit(stemR(b), dotR(l), -3)) { n++; }
      }
      return n;
    }
    /* the pill's sideways place: the one wanted, moved back inside the box; a pill on a stem never so far that the
       stem misses it (it meets the pill at least 12 px in from its corner) */
    function place(l, want) {
      l.dx = want;
      var r = pillR(l), t = want, lim = l.pw / 2 - 12;
      if (r.x1 < 4) { t += 4 - r.x1; } else if (r.x2 > W - 4) { t += W - 4 - r.x2; }
      if (l.tag) { return t; }
      /* a point nearer the box's edge than that: the pill stays inside, its stem nearer its corner (still under it) */
      return t !== want && Math.abs(t) > lim ? clamp(t, -(l.pw / 2 - 3), l.pw / 2 - 3) : clamp(t, -lim, lim);
    }
    /* "side": 1 hangs the pill to the right of its stem, -1 to the left (IGF M03's labels), or "dx" in px */
    function pref(l) { return l.tag ? 0 : (l.side ? l.side * (l.pw / 2 - 12) : l.dx0); }
    /* a crowded box (the pills would cover more than 22 % of it - IGF M02: 11 labels in 690 x 418 covered 30 %) takes the
       compact pills a small box has, so every name can find a free place (independent review of the M02 port,
       2026-10-23). Compact words are smaller for the back of the class: better a second step than a crowded view */
    var sig = shown.map(function (l) { return l.text; }).join('|');
    if (S.dense && sig !== S.denseSig) {               /* other labels now (a step, a state): judged again at full size */
      S.dense = S.small = false;
      setCls(S.wrap, 'k3-small', false);
      S.labels.forEach(function (l) { l.pw = 0; });
      shown.forEach(function (l) { l.pw = l.pill.offsetWidth; l.ph = l.pill.offsetHeight; });
    }
    S.denseSig = sig;
    if (!S.small && W && H) {
      var area = 0;
      shown.forEach(function (l) { area += l.pw * l.ph; });
      if (area > 0.22 * W * H) {
        S.dense = S.small = true;
        setCls(S.wrap, 'k3-small', true);
        S.labels.forEach(function (l) { l.pw = 0; });
        shown.forEach(function (l) { l.pw = l.pill.offsetWidth; l.ph = l.pill.offsetHeight; });
      }
    }
    /* the greedy pass depends on the order the labels are moved in: when a touch is left, the other orders are tried and
       the arrangement with the fewest touches is kept (IGF M02 review, 2026-10-23: a fix in one place moved the clash) */
    function reset() {
      shown.forEach(function (l) { l.up = l.isUp; l.gap = l.base; if (l.tag && l.oy0 != null) { l.oy = l.oy0; } l.dx = place(l, pref(l)); });
    }
    function total() { var n = 0; shown.forEach(function (l) { n += confl(l); }); return n; }
    function snap() { return shown.map(function (l) { return [l.up, l.gap, l.dx, l.oy]; }); }
    var orders = [shown, shown.slice().reverse(), shown.slice().sort(function (p, q) { return p.sx - q.sx; }),
                  shown.slice().sort(function (p, q) { return p.sy - q.sy; })], oi, bestN = 1e9, bestS = null, nNow;
    var calm = still && !S.tween && !hasCls(S.wrap, 'k3-drag');   /* while the view moves, one order: a turn stays smooth */
    function search() {
      bestN = 1e9; bestS = null;
      for (oi = 0; oi < (calm ? orders.length : 1); oi++) {
        reset();
        solve(orders[oi]);
        nNow = total();
        if (nNow < bestN) { bestN = nNow; bestS = snap(); }
        if (!nNow) { break; }
      }
      if (bestS && nNow !== bestN) {
        shown.forEach(function (l, i) { l.up = bestS[i][0]; l.gap = bestS[i][1]; l.dx = bestS[i][2]; l.oy = bestS[i][3]; });
      }
    }
    search();
    /* names on parts close together in a low box (M16 s03 at 1280 x 800: the why under the picture left the scene 180 px
       high, and three names round the inductor found no free place - two lay on each other, one cut): a pill still on
       another after every order, the compact pills are tried, as for a crowded box; and on a step that names its own part
       (a lit name), a name still on another that is not lit steps out of this view - a name read whole beats two unread */
    function onPill(l) { return shown.some(function (b) { return b !== l && hit(pillR(l), pillR(b), 0); }); }
    if (calm && bestN > 0 && shown.some(onPill)) {
      if (!S.small) {
        S.dense = S.small = true;
        setCls(S.wrap, 'k3-small', true);
        S.labels.forEach(function (l) { l.pw = 0; });
        shown.forEach(function (l) { l.pw = l.pill.offsetWidth; l.ph = l.pill.offsetHeight; });
        search();
      }
      var lit = shown.some(function (l) { return hasCls(l.pill, 'k3-hl'); });
      for (oi = shown.length - 1; oi >= 0 && lit; oi--) {
        a = shown[oi];
        if (hasCls(a.pill, 'k3-hl') || !onPill(a)) { continue; }
        a.shown = false; setCls(a.el, 'k3-off', true);
        if (S.outAt !== outAt) { S.outAt = outAt; S.outs = {}; }
        S.outs[a.text] = 1;
        shown.splice(oi, 1);
      }
      S.denseSig = shown.map(function (l) { return l.text; }).join('|');
    }
    function solve(order) {
    for (pass = 0; pass < 6; pass++) {                  /* until nothing moves: a label moved can free or block another */
      var changed = false;
      for (k0 = 0; k0 < order.length; k0++) {
        a = order[k0];
        if (confl(a) === 0 && (a.tag || cover(a) === 0)) { continue; }
        var best = null, dir, g, up, c, cands, ci;
        if (a.tag) {
          cands = [];                                   /* round its point, nearest first: up to 120 px across, 72 down / up */
          [0, 40, -40, 80, -80, 120, -120].forEach(function (cx) { [0, 26, -26, 48, -48, 72, -72].forEach(function (cy) { cands.push([cx, cy]); }); });
          for (ci = 0; ci < cands.length; ci++) {
            a.oy = a.oy0 != null ? a.oy0 : a.oy; a.oy0 = a.oy;
            a.oy = a.oy0 + cands[ci][1];
            a.dx = place(a, cands[ci][0]);
            c = confl(a) * 1000 + Math.abs(cands[ci][0]) + Math.abs(cands[ci][1]);
            if (!best || c < best.c) { best = { c: c, dx: a.dx, oy: a.oy }; }
          }
          a.dx = best.dx; a.oy = best.oy;
        } else {
          /* other stem lengths, the other side of the point, and the pill slid sideways along its stem's end -
             the wanted side first (the hand-made settleLabels tried the same) */
          var lim = a.pw / 2 - 12, p0 = pref(a), dxs = [p0, 0, -lim, lim, -lim / 2, lim / 2], di, gs = [], gi;
          /* 2.75.2 - stem lengths nearest the wanted one first: once no length left can cost less than the best place found
             (a length's own cost only grows with its distance), the rest are not tried - the same place, a fraction of the work */
          for (g = 14; g <= a.base + 260; g += 6) { gs.push(g); }
          gs.sort(function (p, q) { return Math.abs(p - a.base) - Math.abs(q - a.base) || p - q; });
          for (dir = 0; dir < 2; dir++) {
            if (best && dir * 160 >= best.c) { break; }
            up = dir === 0 ? a.isUp : !a.isUp;
            for (gi = 0; gi < gs.length; gi++) {
              g = gs[gi];
              if (best && Math.abs(g - a.base) + dir * 160 >= best.c) { break; }
              for (di = 0; di < dxs.length; di++) {
                a.up = up; a.gap = g;
                a.dx = place(a, dxs[di]);
                c = confl(a) * 1000 + cover(a) * 150 + Math.abs(g - a.base) + dir * 160 + Math.abs(a.dx - p0) * 0.4;
                if (!best || c < best.c) { best = { c: c, up: up, gap: g, dx: a.dx }; }
              }
            }
          }
          a.up = best.up; a.gap = best.gap; a.dx = best.dx;
        }
        changed = true;
      }
      if (!changed) { break; }
    }
    }
    /* the box's edge is a hard limit: a pill the search left past it (no place inside free of the others) gets the stem that
       fits, or the other side of its point, and is slid inside */
    shown.forEach(function (l) {
      var r = pillR(l), upG = l.sy - 4 - l.ph, dnG = H - 4 - l.sy - l.ph;
      if (l.tag || (r.x1 >= 4 && r.x2 <= W - 4 && r.y1 >= 4 && r.y2 <= H - 4)) { return; }
      if (r.y1 < 4 || r.y2 > H - 4) {
        if ((l.up ? upG : dnG) >= 6) { l.gap = l.up ? upG : dnG; } else if ((l.up ? dnG : upG) >= 6) { l.up = !l.up; l.gap = Math.min(l.base, l.up ? upG : dnG); }
      }
      l.dx = place(l, l.dx);
    });
    /* a value is written only when it changed: an unchanged write still marks the page for another layout */
    function put(el, k, v) { if (el.style[k] !== v) { el.style[k] = v; } }
    shown.forEach(function (l) {
      if (l.tag) {
        put(l.pill, 'marginLeft', (l.ox + l.dx).toFixed(0) + 'px');
        put(l.pill, 'marginTop', l.oy.toFixed(0) + 'px');
        return;
      }
      var cls = l.up ? 'k3-up' : 'k3-down';
      if (l.cls !== cls) { setCls(l.pill, 'k3-up', l.up); setCls(l.pill, 'k3-down', !l.up); l.cls = cls; }
      put(l.stem, 'height', l.gap + 'px');
      put(l.stem, 'top', (l.up ? -l.gap : 0) + 'px');
      put(l.pill, 'top', (l.up ? -l.gap : l.gap) + 'px');
      put(l.pill, 'marginLeft', l.dx.toFixed(0) + 'px');
    });
    shown.forEach(function (l) { l.f = [l.up, l.gap, l.dx, l.oy]; });
    S.setKey = key; S.setFull = calm;
    S.setT = now(); S.setCost = S.setT - tn;
    if (!calm) { S.schedule(); }
  };

  /* ======================================================================== drawing on demand */
  P.schedule = function () {
    var S = this;
    if (S.raf || S.dead || !S.live) { return; }
    S.raf = w.requestAnimationFrame(function () { S.raf = 0; S.frame(); });
  };
  P.animsFor = function (n) {
    var S = this;
    S.anims.forEach(function (a) {
      var on = test(S, a.name + '.on') || test(S, a.name + '.play');
      if (on && !a.on) { a.t0 = now(); }
      a.on = on;
    });
  };
  P.frame = function () {
    var S = this;
    if (S.dead || !S.ok) { return; }
    S.take();
    var moving = S.tweenStep(), tnow = now(), first = S.frames === 0 || (w.__scene3d && w.__scene3d.__k3 === S && !w.__scene3d.firstFrameT);
    if (first) { S.mark('frame'); }
    S.anims.forEach(function (a) {
      var on = test(S, a.name + '.on');
      if (on && !a.on) { a.t0 = tnow; }
      a.on = on;
      if (a.fn((tnow - a.t0) / 1000, on)) { moving = true; }
    });
    S.resize();
    S.applyCamera();
    S.updateLabels();
    if (first) { S.mark('labels'); }
    S.gl();
    if (!S.shadowsDone) { S.r.shadowMap.needsUpdate = true; S.shadowsDone = true; }
    S.r.render(S.scene, S.camera);
    S.drawn = [S.r.info.render.calls, S.r.info.render.triangles];
    if (first) { S.mark('rendered'); }
    S.frames++;
    var sc = w.__scene3d;
    if (sc && sc.__k3 === S) {
      sc.frames++;
      if (!sc.firstFrameT) { sc.firstFrameT = now(); S.ready(); }
    } else if (S.frames === 1) { S.ready(); }
    S.steady(moving || S.spin, tnow);
    if (moving || S.spin) { S.schedule(); }
  };
  /* 2.68.0 - steady on a slow tablet: while the model moves, its frames are timed; when 20 in a row take over 30 ms on average
     (under 33 a second - the turn judders; 2.75.2, was 45) it is drawn one step less sharp from then on: twice the screen's
     pixels, then 1.5, then lite light (P.goLite), then 1. Each step makes the drawing buffer once - the cost of a new buffer (perf3d: up to a second on a slowed CPU)
     is why it never goes back and forth; a fast screen never loses sharpness. window.__scene3d.dpr says where it is */
  P.steady = function (moving, tnow) {
    var S = this;
    if (!moving) {
      /* lite comes when the turn stops: its shaders are compiled again, a pause of up to seconds on a slow tablet
         (perf_gate, 4x) - in the middle of a turn a judder, at rest a still picture a moment longer */
      if (S.liteDue) { S.liteDue = false; S.goLite(); S.schedule(); }
      S.lastT = 0; S.dts = []; return;
    }
    if (S.lastT) {
      S.dts = S.dts || [];
      S.dts.push(tnow - S.lastT);
      if (S.dts.length > 20) { S.dts.shift(); }
    }
    S.lastT = tnow;
    var n = S.dts ? S.dts.length : 0, sum = 0;
    if (n < 8 || (n < 20 && S.stepped)) { return; }
    S.dts.forEach(function (d) { sum += d; });
    /* a screen far too slow is judged after 8 frames, on their middle one (over 50 ms): at 300 ms a frame (perf_gate, 4x)
       20 frames were six seconds of a juddering turn. Its first step only - each step after waits for 20 frames */
    if (n < 20 ? S.dts.slice().sort(function (p, q) { return p - q; })[n >> 1] <= 50 : sum / n <= 30) { return; }
    var pr = S.r.getPixelRatio(), next = pr > 1.5 ? 1.5 : pr > 1 ? 1 : 0;
    S.dts = []; S.stepped = true;
    if (pr <= 1.5 && !S.lite && S.lightMode === 'auto') {      /* before the last sharpness step */
      if (!S.liteDue) { S.liteDue = true; slowDevice(true); }  /* the scenes built from now on are lite already */
      return;
    }
    if (!next) { return; }
    S.r.setPixelRatio(next);
    S.dpr = GL.dpr = next;                              /* the scenes after it on this page start there */
    if (w.__scene3d && w.__scene3d.__k3 === S) { w.__scene3d.dpr = next; }
  };
  /* lite from now on: this scene drops its shadows and its studio light at once (its materials stay; their metal is turned
     down so it does not go black without the studio light - one shader rebuild), and the device is remembered as slow, so
     every scene after builds lite from the start. "light": "full" never comes here; window.__scene3d.light says where it is */
  P.goLite = function () {
    var S = this;
    S.lite = true; S.shadows = false;
    slowDevice(true);
    S.r.shadowMap.enabled = false;
    S.sun.castShadow = false;
    if (S.groundMesh) { S.groundMesh.visible = false; }
    if (S.scene.environment) { S.scene.environment = null; S.hemi.intensity = 0.95; S.sun.intensity = 1.0; }
    if (S.envRT) { S.envRT.dispose(); S.envRT = null; }
    S.mats.forEach(function (m) {
      if (m.isMeshStandardMaterial) { m.metalness = Math.min(m.metalness, 0.2); }
      if (m.lights) { m.needsUpdate = true; }
    });
    if (w.__scene3d && w.__scene3d.__k3 === S) { w.__scene3d.light = 'lite'; }
  };
  P.ready = function () {
    var S = this;
    if (S.poster) { S.poster.setAttribute('hidden', ''); }
    setCls(S.stage, 'k3-ready', true);
  };

  /* ======================================================================== the presenter's hands: turn, zoom, tap */
  P.events = function () {
    var S = this, wrap = S.wrap, pts = {}, gs = { mode: '', lx: 0, ly: 0, dist: 0, mx: 0, my: 0, sx: 0, sy: 0, t0: 0, moved: 0, multi: false };
    function count() { var n = 0; each(pts, function () { n++; }); return n; }
    function list() { var a = []; each(pts, function (p) { a.push(p); }); return a; }
    function orbit(dx, dy) { S.view.az -= dx * 0.0062; S.view.el += dy * 0.0055; S.free = true; S.schedule(); }
    function pan(dx, dy) {
      var dd = S.fitDist * S.view.zoom, k0 = dd * Math.tan(S.camera.fov * DEG / 2) * 2 / (S.H || 400);
      var bs = S.basis(S.view.az, S.view.el);
      S.view.tx -= (dx * bs.r.x - dy * bs.u.x) * k0; S.view.ty -= (dx * bs.r.y - dy * bs.u.y) * k0; S.view.tz -= (dx * bs.r.z - dy * bs.u.z) * k0;
      S.free = true; S.schedule();
    }
    function start() {
      var n = count(), a;
      if (n === 1) { a = list()[0]; gs.mode = gs.pan ? 'pan' : 'orbit'; gs.lx = a.x; gs.ly = a.y; }
      else if (n >= 2) {
        a = list(); gs.mode = 'pinch';
        gs.dist = Math.sqrt(Math.pow(a[0].x - a[1].x, 2) + Math.pow(a[0].y - a[1].y, 2)) || 1;
        gs.mx = (a[0].x + a[1].x) / 2; gs.my = (a[0].y + a[1].y) / 2;
      } else { gs.mode = ''; }
    }
    function down(id, x, y, shift) {
      S.endTween();
      pts[id] = { x: x, y: y };
      if (count() === 1) { gs.sx = x; gs.sy = y; gs.t0 = now(); gs.moved = 0; gs.multi = false; gs.pan = !!shift; } else { gs.multi = true; }
      start();
      setCls(wrap, 'k3-drag', true);
    }
    function move(id, x, y) {
      if (!pts[id]) { return; }
      pts[id].x = x; pts[id].y = y;
      gs.moved = Math.max(gs.moved, Math.abs(x - gs.sx) + Math.abs(y - gs.sy));
      if (gs.mode === 'orbit') { orbit(x - gs.lx, y - gs.ly); gs.lx = x; gs.ly = y; }
      else if (gs.mode === 'pan') { pan(x - gs.lx, y - gs.ly); gs.lx = x; gs.ly = y; }
      else if (gs.mode === 'pinch' && count() >= 2) {
        var a = list(), dd = Math.sqrt(Math.pow(a[0].x - a[1].x, 2) + Math.pow(a[0].y - a[1].y, 2)) || 1;
        var mx = (a[0].x + a[1].x) / 2, my = (a[0].y + a[1].y) / 2;
        S.view.zoom *= gs.dist / dd; pan(mx - gs.mx, my - gs.my);
        gs.dist = dd; gs.mx = mx; gs.my = my;
      }
    }
    function upP(id, x, y, isUp) {
      var one = count() === 1 && !!pts[id];
      if (pts[id]) { delete pts[id]; }
      start();
      if (count() === 0) {
        setCls(wrap, 'k3-drag', false);
        S.schedule();                                   /* the labels settled once more, the view still */
        if (isUp && one && !gs.multi && gs.moved < 8 && now() - gs.t0 < 600) { S.tap(x, y); }
      }
    }
    function skip(t) {
      while (t && t !== wrap) {
        if (t.tagName === 'BUTTON' || (t.getAttribute && t.getAttribute('data-3d-part'))) { return true; }
        t = t.parentNode;
      }
      return false;
    }
    if (w.PointerEvent) {
      S.listen(wrap, 'pointerdown', function (e) {
        if (skip(e.target)) { return; }
        if (e.pointerType === 'mouse' && e.button !== 0 && e.button !== 2) { return; }
        down(e.pointerId, e.clientX, e.clientY, e.shiftKey || e.button === 2);
        try { wrap.setPointerCapture(e.pointerId); } catch (e5) { /* old */ }
      });
      S.listen(wrap, 'pointermove', function (e) { move(e.pointerId, e.clientX, e.clientY); });
      S.listen(wrap, 'pointerup', function (e) { upP(e.pointerId, e.clientX, e.clientY, e.button === 0 || e.pointerType !== 'mouse'); });
      S.listen(wrap, 'pointercancel', function (e) { upP(e.pointerId, 0, 0, false); });
      S.listen(wrap, 'lostpointercapture', function (e) { upP(e.pointerId, 0, 0, false); });
    } else {
      S.listen(wrap, 'touchstart', function (e) {
        if (skip(e.target)) { return; }
        var i;
        for (i = 0; i < e.changedTouches.length; i++) { down('t' + e.changedTouches[i].identifier, e.changedTouches[i].clientX, e.changedTouches[i].clientY, false); }
        e.preventDefault();
      });
      S.listen(wrap, 'touchmove', function (e) {
        var i;
        for (i = 0; i < e.changedTouches.length; i++) { move('t' + e.changedTouches[i].identifier, e.changedTouches[i].clientX, e.changedTouches[i].clientY); }
        e.preventDefault();
      });
      var tEnd = function (e) {
        var i;
        for (i = 0; i < e.changedTouches.length; i++) { upP('t' + e.changedTouches[i].identifier, e.changedTouches[i].clientX, e.changedTouches[i].clientY, e.type === 'touchend'); }
      };
      S.listen(wrap, 'touchend', tEnd); S.listen(wrap, 'touchcancel', tEnd);
      var mm = function (e) { move('m', e.clientX, e.clientY); }, mu = function (e) { upP('m', e.clientX, e.clientY, true); w.removeEventListener('mousemove', mm); w.removeEventListener('mouseup', mu); };
      S.listen(wrap, 'mousedown', function (e) {
        if (skip(e.target)) { return; }
        down('m', e.clientX, e.clientY, e.shiftKey);
        w.addEventListener('mousemove', mm); w.addEventListener('mouseup', mu);
      });
    }
    S.listen(wrap, 'wheel', function (e) {
      e.preventDefault();
      S.endTween();
      var dy = e.deltaY;
      if (e.deltaMode === 1) { dy *= 30; }
      S.view.zoom *= Math.exp(clamp(dy, -200, 200) * 0.0012);
      S.free = true;
      S.schedule();
    }, { passive: false });
    S.listen(wrap, 'contextmenu', function (e) { e.preventDefault(); });
    S.listen(wrap, 'dblclick', function (e) { if (skip(e.target)) { return; } S.goStep(S.step); });
    /* a label: the deck wires it (GB3D.wire); outside a deck the kit does - a tap, Enter or Space selects its part */
    S.listen(S.labelLayer, 'click', function (e) {
      if (S.wired) { return; }
      var t = e.target;
      while (t && t !== S.labelLayer && !(t.getAttribute && t.getAttribute('data-3d-part'))) { t = t.parentNode; }
      if (!t || t === S.labelLayer) { return; }
      e.preventDefault(); e.stopPropagation();
      S.select(t.getAttribute('data-3d-part'));
      if (e.detail && t.blur) { t.blur(); }
    });
    S.listen(S.labelLayer, 'keydown', function (e) {
      if (S.wired) { return; }
      var t = e.target, k0 = e.key || '';
      if (!t.getAttribute || !t.getAttribute('data-3d-part')) { return; }
      if (k0 === 'Enter' || k0 === ' ' || k0 === 'Spacebar') { e.preventDefault(); e.stopPropagation(); S.select(t.getAttribute('data-3d-part')); }
    });
    S.listen(w, 'resize', function () { S.schedule(); });
    S.listen(S.stage, 'gb3d-resize', function () { S.schedule(); });
    var box = S.stage.parentNode;
    if (box) { S.listen(box, 'gb3d-resize', function () { S.schedule(); }); }
    S.listen(S.r.domElement, 'webglcontextlost', function (e) { e.preventDefault(); });
    S.listen(S.r.domElement, 'webglcontextrestored', function () { S.lost(); });
    if (w.ResizeObserver) { S.ro = new w.ResizeObserver(function () { S.schedule(); }); S.ro.observe(S.wrap); }
  };
  /* a tap - not a drag - on a part picks it; a tap beside the parts lets go. A ring of 8 more rays 12 px round the
     point when the first finds nothing (IGF M04, M07). See-through and cut-away pieces let the ray through. */
  P.tap = function (cx, cy) {
    var S = this, r = S.wrap.getBoundingClientRect(), px = cx - r.left, py = cy - r.top, k0 = S.pickXY(px, py), a;
    for (a = 0; !k0 && a < 8; a++) { k0 = S.pickXY(px + 12 * Math.cos(a * 0.7854), py + 12 * Math.sin(a * 0.7854)); }
    if (k0) { S.select(k0 === S.sel ? null : k0); }
    else if (S.sel) { S.select(null); }
  };
  P.pickXY = function (px, py) {
    var S = this, ray = S.ray || (S.ray = new T.Raycaster()), ndc = new T.Vector2((px / (S.W || 1)) * 2 - 1, -(py / (S.H || 1)) * 2 + 1);
    S.camera.updateMatrixWorld();
    ray.setFromCamera(ndc, S.camera);
    var hits = ray.intersectObjects(S.root.children, true), i, h, k0, p, see = '';
    for (i = 0; i < hits.length; i++) {
      h = hits[i];
      if (!h.object.isMesh || !S.live0(h.object, h.point)) { continue; }
      k0 = h.object.userData.part;
      p = k0 && S.parts[k0];
      if (!p || !p.pick || h.object.userData.noPick) {
        if (h.object.material.transparent) { continue; }
        break;                                                   /* a solid thing that is not a part hides what is behind */
      }
      if (p.resolve) { k0 = p.resolve(h, ray); p = S.parts[k0] || p; }
      k0 = S.up(k0);
      if (!S.keyShown(k0)) { continue; }
      if (h.object.material.transparent) { if (!see) { see = k0; } continue; }
      return k0;
    }
    return see;
  };
  /* a kid that has no label in this state (a closed pipe's inner pipe) is its parent */
  P.up = function (k0) {
    var S = this, p = S.parts[k0];
    while (p && p.parent && p.need && !test(S, p.need)) { k0 = p.parent; p = S.parts[k0]; }
    return k0;
  };
  P.live0 = function (o, pt) {
    var p = o, m = o.material, i, pl;
    while (p) { if (p.visible === false) { return false; } p = p.parent; }
    if (m.visible === false || (m.transparent && m.opacity < 0.2)) { return false; }
    pl = m.clippingPlanes;
    if (pl && pl.length) { for (i = 0; i < pl.length; i++) { if (pl[i].distanceToPoint(pt) < 0) { return false; } } }
    return true;
  };

  /* ======================================================================== life: prepare, show, hide */
  /* built and its shaders compiled ahead, off screen (the slide before is on screen) */
  P.prepare = function () {
    var S = this;
    if (S.prepared || S.dead) { return; }
    if (!S.build()) { return; }
    S.prepared = true;
    /* built full before a scene juddered: lite now, while its shaders are compiled ahead - not in the middle of its turn */
    if (!S.lite && S.lightMode === 'auto' && slowDevice()) { S.goLite(); }
    /* the canvas shows another scene (or gb_scene's picture) right now: this one draws into a small target off screen - the
       same shaders (its colours are written as the canvas's), its shadows worked out, its parts sent to the graphics chip */
    var h = GL.holder, busy = S.r === GL.r && h && h !== S && h.live && !h.dead, rt = null;
    try {
      var sz = S.measureHidden(), pw = sz.w || 64, ph = sz.h || 48;
      if (busy) {
        rt = GL.rt = GL.rt || new T.WebGLRenderTarget(64, 64, { encoding: T.sRGBEncoding });
      } else { S.size(pw, ph); }
      S.camera.aspect = pw / ph; S.camera.updateProjectionMatrix();
      S.W = pw; S.H = ph;
      S.homeFit();
      S.goStep(0, true);
      S.applyCamera();
      S.gl();
      S.r.setRenderTarget(rt);
      S.r.compile(S.scene, S.camera);
      S.r.shadowMap.needsUpdate = true;
      S.r.render(S.scene, S.camera);
      S.drawn = [S.r.info.render.calls, S.r.info.render.triangles];
      S.shadowsDone = true;
      S.W = S.H = 0;
    } catch (e6) { S.warn('prepare: ' + e6.message); }
    if (rt) { S.r.setRenderTarget(null); }
  };
  P.mark = function (name) {
    var sc = w.__scene3d;
    if (sc && sc.__k3 === this) { (sc.marks = sc.marks || {})[name] = Math.round(now() - sc.enterT); }
  };
  P.show = function () {
    var S = this;
    S.mark('show');
    if (!S.build()) { return false; }
    if (!S.prepared) { S.prepare(); }
    if (!S.ok) { return false; }
    S.mark('built');
    S.live = true;
    S.take();
    S.W = S.H = 0;
    S.resize();
    S.mark('resized');
    S.goStep(0, true);
    if (w.GB3D && w.GB3D.wire && !S.ownWire) {
      try { S.wired = !!w.GB3D.wire(S.stage, { select: function (k0) { S.select(k0 || null); }, current: function () { return S.sel; } }); }
      catch (e7) { S.wired = false; }
      if (S.wired && !(S.stage.closest && S.stage.closest('.gb-fs3d'))) { S.wired = false; }
    }
    if (!S.wired) { S.ownLabels(); S.ownFull(); }
    /* drawn at once: the canvas just moved here still holds the last scene's picture */
    try { S.frame(); } catch (e8) { S.warn('frame: ' + e8.message); }
    S.schedule();                                       /* and once more when the slide has its places */
    return true;
  };
  P.hide = function () {
    var S = this;
    S.live = false;
    if (S.raf) { w.cancelAnimationFrame(S.raf); S.raf = 0; }
    S.endTween();
    S.anims.forEach(function (a) { a.on = false; });
    if (S.liteDue) { S.liteDue = false; S.goLite(); }
    if (S.own) { S.disown(); }
  };
  /* outside a deck: the labels are buttons of the kit's own */
  P.ownLabels = function () {
    this.labels.forEach(function (l) {
      if (!l.pick) { return; }
      l.pill.setAttribute('role', 'button');
      l.pill.setAttribute('tabindex', '0');
      l.pill.setAttribute('aria-pressed', 'false');
    });
  };
  /* outside a deck: a Full screen button of the kit's own (the deck's gb_deck.js adds its own to a 3D slide) */
  P.ownFull = function () {
    var S = this, box = S.stage;
    if (S.fsBtn || S.spec.fullscreen === false || (box.closest && box.closest('.gb-fs3d'))) { return; }
    var b = el('button', 'gb-fs3d-btn k3-fs', S.wrap);
    b.type = 'button';
    function word(on) {
      b.setAttribute('aria-label', on ? 'Exit full screen' : 'Full screen');
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.innerHTML = on ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5"/></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/></svg>';
    }
    word(false);
    S.fsBtn = b;
    S.listen(b, 'click', function (e) {
      e.preventDefault(); e.stopPropagation();
      var fe = d.fullscreenElement || d.webkitFullscreenElement;
      if (fe === box || hasCls(box, 'k3-fake')) {
        if (hasCls(box, 'k3-fake')) { setCls(box, 'k3-fake', false); word(false); S.schedule(); }
        else { (d.exitFullscreen || d.webkitExitFullscreen).call(d); }
        return;
      }
      var rq = box.requestFullscreen || box.webkitRequestFullscreen, pr = null;
      try { pr = rq ? rq.call(box) : null; } catch (x) { pr = null; }
      if (!rq) { setCls(box, 'k3-fake', true); word(true); S.schedule(); }
      else if (pr && pr['catch']) { pr['catch'](function () { setCls(box, 'k3-fake', true); word(true); S.schedule(); }); }
    });
    function sync() { var fe = d.fullscreenElement || d.webkitFullscreenElement; word(fe === box); S.schedule(); }
    S.listen(d, 'fullscreenchange', sync); S.listen(d, 'webkitfullscreenchange', sync);
  };

  /* what a check or a test reads: what is drawn, where the labels are, how much of the box the picture fills */
  P.info = function () {
    var S = this;
    if (!S.ok) { return { ok: false, why: S.why || '', warnings: S.warnings || [] }; }
    var c = [], i, mn = S.box.min, mx = S.box.max, x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, p = new T.Vector3();
    for (i = 0; i < 8; i++) {
      p.set(i & 1 ? mx.x : mn.x, i & 2 ? mx.y : mn.y, i & 4 ? mx.z : mn.z).project(S.camera);
      c.push(p.x, p.y);
      x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y);
    }
    var lr = S.labelLayer.getBoundingClientRect();
    return {
      ok: true, frames: S.frames, size: [S.W, S.H], pixelRatio: S.r.getPixelRatio(), light: S.lite ? 'lite' : 'full',
      step: S.step, steps: S.steps().length,
      selected: S.sel, lit: Object.keys(S.lit), wired: !!S.wired,
      calls: (S.drawn || [0])[0], triangles: (S.drawn || [0, 0])[1], geometries: S.r.info.memory.geometries,
      parts: S.order.filter(function (k0) { return S.parts[k0].pick; }),
      states: (function () { var o = {}; each(S.states, function (s, n) { o[n] = Math.round(s.v * 1000) / 1000; }); return o; }()),
      view: { az: S.view.az / DEG, el: S.view.el / DEG, zoom: S.view.zoom },
      fill: { w: (Math.min(x1, 1) - Math.max(x0, -1)) / 2, h: (Math.min(y1, 1) - Math.max(y0, -1)) / 2 },
      labels: S.labels.map(function (l) {
        var r = l.pill.getBoundingClientRect();
        return { part: l.key, text: l.text, shown: !!l.shown, x: l.sx, y: l.sy, pick: !!l.pick, lit: hasCls(l.pill, 'k3-hl'),
                 pill: l.shown ? [r.left - lr.left, r.top - lr.top, r.width, r.height] : null };
      }),
      warnings: S.warnings || []
    };
  };
  P.snapshot = function () { this.frame(); return this.r.domElement.toDataURL('image/png'); };
  P.dispose = function () {
    var S = this;
    S.hide();
    S.dead = true;
    S.listeners.forEach(function (l) { l[0].removeEventListener(l[1], l[2], l[3]); });
    S.listeners = [];
    if (S.ro) { S.ro.disconnect(); }
    if (S.ok) { S.release(); }                          /* the one renderer stays, for the other scenes */
    S.geos.forEach(function (g) { g.dispose(); });
    S.mats.forEach(function (m) { m.dispose(); });
    S.disposeLater.forEach(function (m) { if (m.dispose) { m.dispose(); } });
    if (S.envRT) { S.envRT.dispose(); }
    if (GL.holder === S) { GL.holder = null; }
    if (S.wrap && S.wrap.parentNode) { S.wrap.parentNode.removeChild(S.wrap); }
    var i = scenes.indexOf(S);
    if (i >= 0) { scenes.splice(i, 1); }
  };

  /* the scene's api - what a test, the deck and a studio page use */
  function api(S) {
    return {
      scene: S,
      select: function (k0) { S.select(k0 || null); },
      current: function () { return S.sel; },
      step: function (n) { if (n == null) { return S.step; } S.goStep(n); return S.step; },
      steps: function () { return S.steps().length; },
      next: function () { if (S.step < S.steps().length - 1) { S.goStep(S.step + 1); return true; } return false; },
      prev: function () { if (S.step > 0) { S.goStep(S.step - 1); return true; } return false; },
      state: function (n, v) { if (v == null) { return S.states[n] ? S.states[n].v : undefined; } S.go(null, (function () { var o = {}; o[n] = v; return o; }()), Object.keys(S.lit)); return v; },
      control: function (i) { var b = (S.btns || [])[i]; if (b) { S.control(b.__c); } },
      tap: function (x, y) { S.tap(x, y); },
      info: function () { return S.info(); },
      render: function () { S.endTween(); S.frame(); },
      snapshot: function () { return S.snapshot(); },
      show: function () { return S.show(); },
      hide: function () { S.hide(); },
      dispose: function () { S.dispose(); }
    };
  }

  /* ======================================================================== in a deck: hooks, steps, lines */
  function slideOf(e) { return e && e.closest ? e.closest('.slide') : null; }
  function prevSlide(s) {
    var p = s && s.previousElementSibling;
    while (p && !(p.classList && p.classList.contains('slide'))) { p = p.previousElementSibling; }
    return p;
  }
  function hook(id, fns) {
    if (!id) { return; }
    var H = w.GB_HOOKS = w.GB_HOOKS || {}, old = H[id] || {}, cur = {};
    cur.enter = function () { if (old.enter) { old.enter.apply(this, arguments); } if (fns.enter) { fns.enter(); } };
    cur.leave = function () { if (old.leave) { old.leave.apply(this, arguments); } if (fns.leave) { fns.leave(); } };
    if (old.step || fns.step) {
      cur.step = function (dir) { if (old.step && old.step(dir)) { return true; } return !!(fns.step && fns.step(dir)); };
    }
    /* the next slide's scene hooks this slide too (it prepares on enter): the way the deck walks this slide's figure with
       its lines stays */
    ['lines', 'line0', 'go'].forEach(function (k) { if (old[k] !== undefined) { cur[k] = old[k]; } });
    H[id] = cur;
  }
  function deck(S, slide) {
    var id = slide.id, before = prevSlide(slide), timer = 0;
    function lines(n) {
      var st = S.steps(), i;
      [].forEach.call(slide.querySelectorAll('[data-i]'), function (x) { x.classList.remove('cur', 'lit'); });
      for (i = 0; i <= n && i < st.length; i++) {      /* step 0 is the scene as the slide opens: its line too */
        [].concat(st[i].line == null ? [] : st[i].line).forEach(function (k0) {
          var line = slide.querySelector('[data-i="' + k0 + '"]');
          if (line) { line.classList.add(i === n ? 'cur' : 'lit'); }
        });
      }
    }
    S.onStep = function (n) {
      lines(n);
      var hk = (w.GB_HOOKS || {})[id];                 /* the deck re-lights the lines from its one counter */
      if (hk && hk.sync) { hk.sync(n); }
    };
    S.at = [].indexOf.call(d.querySelectorAll('.slide'), slide);
    hook(before && before.id, {
      enter: function () {
        sweep(S.at - 1);
        if (w.__noPrepare || S.prepared) { return; }
        clearTimeout(timer);
        /* in two turns - the parts made, then the shaders compiled and the first picture drawn - so the slide shown (its own
           scene may be turning) is held up twice briefly, not once for the whole build */
        timer = setTimeout(function () {
          S.build();
          timer = setTimeout(function () { S.prepare(); if (w.__scene3d && w.__scene3d.__k3 === S) { w.__scene3d.prepared = true; } }, 40);
        }, 120);
      }
    });
    var other = !!((w.GB_HOOKS || {})[id] || {}).step;     /* the slide's own stops (gb_steps.js) walk it already */
    hook(id, {
      enter: function () {
        clearTimeout(timer);
        w.__scene3d = { __k3: S, enterT: now(), firstFrameT: 0, frames: 0, prepared: !!S.prepared, light: S.lite ? 'lite' : 'full',
          spin: function (ms, cb) {
            var t0 = now(), f0 = S.frames;
            S.spin = true; S.schedule();
            (function turn() {
              S.view.az += 0.01; S.schedule();
              if (now() - t0 < ms) { w.requestAnimationFrame(turn); } else { S.spin = false; cb({ frames: S.frames - f0, ms: now() - t0 }); }
            }());
          } };
        sweep(S.at);
        if (!S.show()) { return; }
      },
      leave: function () { S.hide(); },
      step: function (dir) {
        if (!S.live) { return false; }
        if (dir > 0 && S.step < S.steps().length - 1) { S.goStep(S.step + 1); return true; }
        if (dir < 0 && S.step > 0) { S.goStep(S.step - 1); return true; }
        return false;
      }
    });
    /* the deck walks the scene and the slide's lines with one counter (gb_deck.js lockFor), as the 2D kit does: the lines
       each step after the first lights, the first step's own (line0), and a way to put the scene at a step. Not when
       another hook already steps the slide */
    var hk = (w.GB_HOOKS || {})[id], ids = function (st) { return st && st.line != null ? [].concat(st.line).map(Number) : []; };
    if (hk && S.steps().length > 1 && !other) {
      hk.line0 = ids(S.steps()[0]);
      hk.lines = S.steps().slice(1).map(ids);
      hk.go = function (n, animate) { if (S.live && n !== S.step) { S.goStep(n, !animate); } };
    }
    /* for the slide's own stops (gb_steps.js), which play the scene's steps before the answer: false when it cannot step */
    slide.__fig = { steps: function () { return S.steps(); }, at: function () { return S.step; },
      go: function (n) { if (!S.live) { return false; } if (n !== S.step) { S.goStep(n); } } };
    /* a line a step lights is also the way to that step (the 2D kit's rule) */
    S.steps().forEach(function (st, i) {
      [].concat(st.line == null ? [] : st.line).forEach(function (k0) {
        var line = slide.querySelector('[data-i="' + k0 + '"]');
        if (!line || line.__k3Step) { return; }
        line.__k3Step = i;
        line.classList.add('kit-tap');
        line.setAttribute('tabindex', '0');
        line.setAttribute('role', 'button');
        line.addEventListener('click', function () { if (S.live) { S.goStep(line.__k3Step); } });
        line.addEventListener('keydown', function (e) { if ((e.key || '') === 'Enter' && S.live) { e.preventDefault(); e.stopPropagation(); S.goStep(line.__k3Step); } });
      });
    });
  }

  function specOf(host) {
    var ref = host.getAttribute('data-kit3d') || '', node, txt;
    if (ref.charAt(0) === '#') {
      node = d.getElementById(ref.slice(1));
      txt = node ? node.textContent : '';
    } else if (KIT3D.specs[ref]) { return KIT3D.specs[ref]; }
    else { txt = ref; }
    try { return JSON.parse(txt); } catch (e9) { return null; }
  }
  function auto() {
    [].forEach.call(d.querySelectorAll('[data-kit3d]'), function (host) {
      if (host.__k3) { return; }
      var spec = specOf(host), slide = slideOf(host);
      if (!spec) { host.__k3 = 'bad'; if (w.console) { w.console.warn('KIT3D: no spec for ' + host.getAttribute('data-kit3d')); } return; }
      var S = new Scene(spec, host, {});
      scenes.push(S);
      host.__k3 = api(S);
      if (slide && slide.id) { deck(S, slide); }
      else {                               /* not in a deck: shown at once */
        if (d.readyState === 'loading') { d.addEventListener('DOMContentLoaded', function () { S.show(); }); } else { setTimeout(function () { S.show(); }, 0); }
      }
    });
  }

  var KIT3D = {
    version: '1.0.0',
    specs: {},
    PAL: PAL, TINT: TINT, ZONE: ZONE,
    /* a part type: KIT3D.define('valve', function (k, p) {...}, {family: 'piping', about: '...'}) */
    define: function (type, fn, info) { PART[type] = fn; PART_INFO[type] = info || {}; },
    types: function () { var o = {}; each(PART_INFO, function (v, n) { o[n] = v; }); return o; },
    /* a scene of its own in an element (a gallery, a test, a studio page); shown at once */
    mount: function (host, spec, opt) {
      var S = new Scene(spec, host, opt || {});
      scenes.push(S);
      host.__k3 = api(S);
      if (!(opt && opt.hidden)) { S.show(); }
      return host.__k3;
    },
    auto: auto,
    all: function () { return scenes.map(function (S) { return S.stage.__k3; }); },
    /* the one renderer, lent to gb_scene.js: to a holder ({live}) when no scene shown holds it, else null */
    gl: function (holder) {
      var r = shared(), h = GL.holder;
      if (!r || (h && h !== holder && h.live && !h.dead)) { return null; }
      GL.holder = holder;
      return r;
    },
    _test: test,
    light: true                       /* 2.75.2: this kit chooses its own light ("light"); a host's lite patch leaves it be */
  };
  w.KIT3D = KIT3D;

  /* ======================================================================== PARTS */
  /* The catalogue - strict JSON between the two markers: check_kit3d.py reads it (types, sub-parts, states, where
     "at" is). "subs": the sub-parts a part makes, id "<id>_<sub>" unless the spec names it ("subs": {"inner": "x"});
     "subs_from": a list in the spec whose items' "id" are sub-parts; "states": "<id>.<state>" numbers 0..1;
     "ports": the "<id>.<port>" another part "connect"s to or a hose runs "from" / "to". */
  var CATALOG = /* @@CATALOG@@ */ {
    "box": {"family": "primitives", "at": "centre", "about": "a box: size [w,h,d]"},
    "cylinder": {"family": "primitives", "at": "centre", "about": "a cylinder: r, len, axis x|y|z"},
    "sphere": {"family": "primitives", "at": "centre", "about": "a ball: r"},
    "hull": {"family": "structures", "at": "the hull's own origin: x as given, y = bottom shell 0, z = centre line",
             "subs_from": ["spaces"], "anchors": ["outer_shell", "inner_hull", "double_bottom", "wing_tank", "hopper_tank", "top_wing_tank"],
             "about": "a hull section: double bottom, spaces between bulkheads, ghost walls, frames; a gas carrier's double hull - outer shell, inner hull, wing, hopper and top-wing tanks"},
    "deck_plate": {"family": "structures", "at": "deck top at the ship's side (z = 0 is the side, inboard is -z)",
                   "about": "a piece of steel deck and ship's side plating with seams"},
    "room": {"family": "structures", "at": "floor centre", "about": "a cut-open room: floor, back and side walls, frames, the front open"},
    "enclosure": {"family": "structures", "at": "floor centre", "states": ["open"], "about": "a gas-tight steel box (TCS) whose walls fade away"},
    "panel": {"family": "structures", "at": "centre", "about": "a see-through wall"},
    "accommodation": {"family": "structures", "at": "base centre", "about": "a deckhouse with window rows and a wheelhouse; doors in its side walls (doors)"},
    "airlock": {"family": "structures", "at": "floor centre", "subs": ["door1", "door2", "alarm"], "states": ["open", "alarm"],
                "anchors": ["door1", "door2", "alarm"],
                "about": "an airlock: two self-closing gastight steel doors gap apart on their sills, door closers, an alarm lamp and sounder on both sides"},
    "compressor_house": {"family": "structures", "at": "floor centre", "subs": ["compressor", "motor", "bulkhead", "shaft"], "states": ["on"],
                         "about": "a cargo compressor house: compressor room and electric motor room divided by a gastight bulkhead, the shaft through it in a gastight seal; ventilation arrows"},
    "tank_c": {"family": "tanks", "at": "axis centre", "subs": ["liquid"],
               "about": "IMO type C: cylinder, dished ends, rings, saddles (sub-part saddles); cut open, liquid level, insulation; a dome (sub-part dome) through the deck; a bilobe (lobes 2) with its centreline bulkhead; seated in a hold (in)"},
    "tank_sphere": {"family": "tanks", "at": "centre", "subs": ["liquid", "skirt"],
                    "about": "a spherical (Moss) tank on its skirt at the equator; its dome (sub-part dome); cut open, liquid, insulation, drip tray, tank cover; seated in a hold (in)"},
    "tank_prism": {"family": "tanks", "at": "centre", "subs": ["liquid"], "subs_from": ["layers"],
                   "about": "prismatic / membrane / semi-membrane tank: chamfered (or rounded) section, the layers of insulation and barriers seen at the cut; lining the hold, or a Type A / B tank on chocks with its centreline bulkhead (in)"},
    "pipe": {"family": "piping", "at": "the path's origin", "about": "a pipe run through points: bends, flanges, ID bands"},
    "pipe_dw": {"family": "piping", "at": "the pipe's middle", "subs": ["inner", "annulus", "outer"], "states": ["cut"],
                "about": "a double-walled gas pipe: yellow inner pipe, see-through outer pipe, the annulus; cut open"},
    "valve": {"family": "piping", "at": "on the pipe axis", "states": ["shut", "open"], "about": "a valve: body, flanges, bonnet, handwheel or actuator; or a relief valve whose bonnet lifts"},
    "arrow": {"family": "measures", "at": "origin of a and b", "states": ["on"], "about": "one arrow a -> b, shaft and head (the wind's way)"},
    "flange": {"family": "piping", "at": "on the pipe axis", "about": "a flange pair with a gasket and bolts"},
    "coupling": {"family": "piping", "at": "on the pipe axis", "about": "a dry-disconnect or breakaway coupling"},
    "hose": {"family": "piping", "at": "the path's origin", "states": ["on"], "ports": ["start", "end"],
             "about": "a hose through points, or from a port to a port with its couplings; water arrows along it"},
    "vent_mast": {"family": "piping", "at": "base", "about": "a vent mast with hood, flanges, bands and stays"},
    "vessel": {"family": "equipment", "at": "axis centre", "about": "a horizontal vessel on legs (vaporiser, heater)"},
    "cabinet": {"family": "equipment", "at": "base centre", "about": "a cabinet (gas valve unit, panel)"},
    "engine": {"family": "equipment", "at": "base centre", "about": "a dual-fuel engine: block, heads, turbocharger, exhaust"},
    "pump": {"family": "equipment", "at": "base centre", "about": "a pump: casing, motor, base"},
    "drip_tray": {"family": "equipment", "at": "base centre", "about": "a stainless drip tray on insulating pads"},
    "esd_button": {"family": "equipment", "at": "base", "about": "an emergency shutdown push button on a yellow post"},
    "foam_extinguisher": {"family": "equipment", "at": "base", "about": "a portable foam extinguisher with hose and nozzle"},
    "foam_inductor": {"family": "equipment", "at": "the body's middle, on its axis (water along +x)", "subs": ["valve", "pickup", "venturi"],
                      "states": ["cut", "on"], "ports": ["in", "out", "pickup"],
                      "about": "an in-line foam inductor (eductor): couplings, metering valve, clear pick-up tube and wand; cut open, the venturi inside"},
    "foam_branch_pipe": {"family": "equipment", "at": "the inlet coupling's face (barrel along +x)", "subs": ["air", "mesh"], "states": ["on"],
                         "ports": ["in", "out"], "about": "a foam branch pipe: medium expansion (wide head, mesh) or low expansion; air in, foam out"},
    "foam_container": {"family": "equipment", "at": "base centre", "ports": ["mouth"],
                       "about": "a 20-25 litre foam concentrate container: jerrycan or drum, the pick-up wand in its mouth"},
    "fire_hydrant": {"family": "equipment", "at": "base", "ports": ["out"], "about": "a fire main hydrant: riser, valve with handwheel, outlet with a hose coupling"},
    "detector": {"family": "equipment", "at": "where it is fixed", "states": ["alarm"], "about": "a gas detector head, a leak sensor or a temperature sensor (kind); its lamp lights in alarm"},
    "person": {"family": "equipment", "at": "between the feet", "about": "a person for scale"},
    "air_intake": {"family": "equipment", "at": "centre", "about": "an air intake with louvres"},
    "dimension": {"family": "measures", "at": "origin of a and b", "states": ["on"], "about": "a measured line with arrow heads and its value"},
    "limit_box": {"family": "measures", "at": "origin of min and max", "about": "a dashed amber box and faint planes: where a thing must stay"},
    "zone": {"family": "measures", "at": "centre", "states": ["on"], "about": "a hazardous zone volume (0 red, 1 amber, 2 yellow)"},
    "gas": {"family": "effects", "at": "the leak", "states": ["on"], "about": "a gas cloud that rises, sinks, spreads or vents as a plume"},
    "flow": {"family": "effects", "at": "the path's origin", "states": ["on"], "about": "arrows that run along a path"}
  } /* @@END@@ */;
  each(CATALOG, function (v, n) { PART_INFO[n] = v; });

  var define = KIT3D.define;
  /* the part's material: its own palette name, or the spec's "mat" / "color" */
  function M(k, p, dflt, extra) {
    var n = p.mat || dflt;
    if (!n && !p.color) { return null; }               /* the part's own material follows (M(...) || its own) */
    if (p.color) { var b = PAL[n] || ['#888888', 0.5, 0.2]; n = { color: p.color, rough: b[1], metal: b[2] }; }
    return k.mat(n, extra);
  }
  function tint(t, dflt) { return TINT[t] || t || dflt; }
  function mix(hex, to, a) { var c = new T.Color(hex); c.lerp(new T.Color(to), a); return '#' + c.getHexString(); }
  function seeded(s) { var seed = s || 1; return function () { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }; }
  function hashId(id) { var h = 7, i; for (i = 0; i < String(id).length; i++) { h = (h * 31 + String(id).charCodeAt(i)) % 100003; } return h + 1; }
  /* the sub-part id a part makes: the spec's "subs": {"inner": "x"}, else "<id>_inner" */
  function subId(k, p, name) { return (p.subs && p.subs[name]) || (k.cur ? k.cur.id : p.id) + '_' + name; }
  function rectX(x, y0, y1, z0, z1) { return [x, y0, z0, x, y0, z1, x, y0, z1, x, y1, z1, x, y1, z1, x, y1, z0, x, y1, z0, x, y0, z0]; }

  /* -------------------------------------------------------------------- primitives */
  define('box', function (k, p) {
    var s = v3(p.size, [1, 1, 1]);
    k.box(s[0], s[1], s[2], M(k, p, 'steel', p.opacity != null ? { opacity: p.opacity } : null), 0, 0, 0);
    k.anchor('label', [0, s[1] / 2, 0]);
  });
  define('cylinder', function (k, p) {
    var r = num(p.r, 0.5), len = num(p.len, 1), ax = p.axis || 'y';
    k.cyl(ax, r, len, M(k, p, 'steel', p.opacity != null ? { opacity: p.opacity } : null), 0, 0, 0, { open: !!p.open, seg: 40 });
    k.anchor('label', [0, ax === 'y' ? len / 2 : r, 0]);
  });
  define('sphere', function (k, p) {
    var r = num(p.r, 0.5);
    k.ball(r, M(k, p, 'steel', p.opacity != null ? { opacity: p.opacity } : null), 0, 0, 0, { seg: 32 });
    k.anchor('label', [0, r, 0]);
  });

  /* -------------------------------------------------------------------- structures */
  /* a hull section (IGF M01, M02): the double bottom, spaces between bulkheads - each a sub-part with its tinted floor and
     far wall - see-through bulkheads (one may have a round opening for a tank), ghost side walls, frame lines.
     x: [from, to]; half (half breadth); bottom (0), floor (top of the double bottom), top (main deck);
     spaces [{id, x: [a, b], tint, floor, wall}]; bulkheads [{x, hole: [y, r], opacity}]; near / far / ends: wall
     opacities; ribs (spacing on the far side); bottom_id / side_id: the double bottom / far side as sub-parts */
  /* 2.72.0 - "on": "<hull>.deck" | ".floor" | ".bottom" (or "<deck_plate>.deck"): the part's height is that level's, as in the
     2D kit - a vent mast's foot, a drip tray, an ESD button, an air intake stand on the deck, never at a guessed y inside
     the hull. The part's x and z stay its own. check_kit3d.py fails a deck part below the deck (the same numbers) */
  function deckLevel(h, lvl) {
    var bot = num(h.bottom, 0), fl = num(h.floor, bot + 1.2), top = num(h.top, fl + 9), y0 = (h.at || [0, 0, 0])[1] || 0;
    if (h.type === 'deck_plate') return y0;
    return y0 + (lvl === 'floor' ? fl : lvl === 'bottom' ? bot : top);
  }
  function deckRelation(list, p, S) {
    var m = typeof p.on === 'string' && /^([\w-]+)\.(deck|floor|bottom)$/.exec(p.on);
    if (!m) return p;
    var h = list.filter(function (q) { return q && q.id === m[1] && (q.type === 'hull' || q.type === 'deck_plate'); })[0];
    if (!h) { S.warn('part "' + (p.id || p.type) + '" is "on" ' + p.on + ' - there is no hull or deck_plate ' + m[1]); return p; }
    var q = {}, a = (p.at || [0, 0, 0]).slice();
    for (var key in p) q[key] = p[key];
    a[1] = deckLevel(h, m[2]) + num(p.gap, 0);
    q.at = a;
    return q;
  }
  /* Parts that join end to end: "<id>.<port>" names another part's port (PORTS, below; a hose's "start" / "end").
     "connect": "I.out" (or {"to": "I.out", "port": "in"}) puts this part's own port - "in" unless named - on that port,
     turned round the vertical to face it: a branch pipe on the inductor's outlet, never a gap guessed in metres.
     A hose's "from" / "to" (and any point of its "path") may name a port: it starts and ends there, leaving straight.
     The parts named are built first. */
  var REF = /^([\w-]+)\.(\w+)$/;
  function joinRefs(p) {
    var out = [], c = p.connect && typeof p.connect === 'object' ? p.connect.to : p.connect;
    [c, p.from, p.to, p.pickup].concat(Array.isArray(p.path) ? p.path : []).forEach(function (r) {
      var m = typeof r === 'string' && REF.exec(r);
      if (m && m[1] !== p.id) { out.push(m[1]); }
    });
    return out;
  }
  function joinOrder(list, S) {
    var ids = {}, done = {}, order = [], left = [], i, pass, moved;
    list.forEach(function (p, j) { if (p && p.id) { (ids[p.id] = ids[p.id] || []).push(j); } left.push(j); });
    for (pass = 0; pass < list.length + 1 && left.length; pass++) {
      moved = false;
      left = left.filter(function (j) {
        var ready = joinRefs(list[j] || {}).every(function (id) { return (ids[id] || []).every(function (x) { return done[x]; }); });
        if (ready) { done[j] = true; order.push(j); moved = true; }
        return !ready;
      });
      if (!moved) { break; }
    }
    for (i = 0; i < left.length; i++) {                 /* joined in a ring: built as listed */
      S.warn('part "' + (list[left[i]].id || left[i]) + '" joins a part that joins it back - built as listed');
      order.push(left[i]);
    }
    return order;
  }
  function portOf(S, ref, who) {
    var m = typeof ref === 'string' && REF.exec(ref), p = m && S.parts[m[1]];
    if (!m) { return null; }
    var pt = p && p.ports && p.ports[m[2]];
    if (!pt) {
      S.warn('part "' + who + '" joins ' + ref + ' - ' + (p ? 'a ' + p.type + ' has no port "' + m[2] + '" (it has ' +
        Object.keys(p.ports || {}).join(', ') + ')' : 'there is no part ' + m[1]));
      return null;
    }
    return pt;
  }
  function joinRelation(p, S) {
    var refs = joinRefs(p);
    if (!refs.length) { return p; }
    var q = {}, key, who = p.id || p.type;
    for (key in p) { q[key] = p[key]; }
    ['from', 'to', 'pickup'].forEach(function (n) { if (typeof p[n] === 'string') { q['_' + n] = portOf(S, p[n], who); } });
    if (Array.isArray(p.path)) { q._path = p.path.map(function (x) { return typeof x === 'string' ? portOf(S, x, who) : x; }); }
    var c = p.connect && typeof p.connect === 'object' ? p.connect : { to: p.connect };
    if (typeof c.to === 'string') {
      var tp = portOf(S, c.to, who), own = PORTS[p.type] && PORTS[p.type](p)[c.port || 'in'];
      if (tp && !own) { S.warn('part "' + who + '" connects ' + c.to + ' - a ' + p.type + ' has no port "' + (c.port || 'in') + '"'); }
      if (tp && own) {
        /* turn round the vertical so the own port faces the other one, then put it on that port */
        var want = Math.atan2(tp.dir[2], -tp.dir[0]), have = Math.atan2(-own[1][2], own[1][0]), rot = want - have, s = num(p.scale, 1);
        var cs = Math.cos(rot), sn = Math.sin(rot), lx = own[0][0] * s, lz = own[0][2] * s;
        q.rot = rot / DEG;
        q.at = [tp.at[0] - (lx * cs + lz * sn), tp.at[1] - own[0][1] * s, tp.at[2] - (-lx * sn + lz * cs)];
      }
    }
    return q;
  }
  /* "in": "<hull>" (or one of its spaces' ids): a tank in a hull's hold, seated by the kit as a gas carrier carries it -
     never at a guessed height beside guessed wing boxes. tank_prism: a membrane or semi-membrane tank lines the hold
     (the inner hull) end to end; a Type A / Type B prismatic tank stands in it with its clearance (clear, 0.8) on chocks.
     tank_sphere: its skirt runs from the equator down to the inner bottom (skirt: the equator's height above it).
     tank_c: its saddles stand on the inner bottom (clear: the tank's bottom above it); the length fills the hold
     unless given. The tank's x (and a tank_c's z) are its own "at"'s when given; its height is the hold's. */
  var SEATED = ['tank_c', 'tank_sphere', 'tank_prism'];
  function holdOf(list, ref) {
    var f = null;
    list.forEach(function (q) {
      if (f || !q || q.type !== 'hull') { return; }
      if (q.id === ref) { f = { h: q, x: q.x || [-10, 10] }; return; }
      (q.spaces || []).forEach(function (s) { if (!f && s.id === ref) { f = { h: q, x: s.x }; } });
    });
    return f;
  }
  function inRelation(list, p, S) {
    if (typeof p.in !== 'string' || SEATED.indexOf(p.type) < 0) { return p; }
    var f = holdOf(list, p.in);
    if (!f) {
      if (!list.some(function (q) { return q && q.id === p.in; })) { S.warn('part "' + (p.id || p.type) + '" is "in" ' + p.in + ' - there is no hull or hull space ' + p.in); }
      return p;
    }
    var q = {}, key, o = v3(f.h.at), sec = holdSection(f.h), X0 = o[0] + f.x[0], X1 = o[0] + f.x[1];
    for (key in p) { q[key] = p[key]; }
    var own = Array.isArray(p.at) && p.at.length === 3, ax = own ? p.at[0] : (X0 + X1) / 2, az = own ? p.at[2] : o[2];
    var R = num(p.r, p.type === 'tank_sphere' ? 5 : 3), ins = num(p.insulation, 0), fl = o[1] + sec.fl, h;
    q._hold = { sec: sec, x0: X0, x1: X1, y0: o[1], z0: o[2] };
    if (p.type === 'tank_prism') {
      q.at = [(X0 + X1) / 2, o[1], o[2]];
    } else if (p.type === 'tank_sphere') {
      h = num(p.skirt, (R + ins) * 1.25);
      q.at = [ax, fl + h, az];
      q.base = -h;
      q._deck = o[1] + sec.top - q.at[1];
    } else {
      h = num(p.clear, Math.max(0.5, R * 0.15)) + R + ins;
      q.at = [ax, fl + h, az];
      q.base = -h;
      if (p.len == null) { q.len = Math.max(1, (X1 - X0) - 2 * num(p.head, R / 2) - 2); }
    }
    return q;
  }
  /* the hold's section in a hull (y-z, the hull's own coordinates, counter-clockwise): the inner bottom, the hopper's slope,
     the inner side, the top wing's slope, the deck. double: the double side's width; hopper [w, h]; topwing [w, h]. None of
     them: the hull's own sides over its double bottom. */
  function holdSection(p) {
    var hz = num(p.half, num(p.breadth, 12) / 2), bot = num(p.bottom, 0), fl = num(p.floor, bot + 1.2), top = num(p.top, fl + 9);
    var zi = hz - num(p.double, 0), hp = p.hopper || [0, 0], tw = p.topwing || [0, 0];
    var a = num(hp[0], 0), b = num(hp[1], 0), c = num(tw[0], 0), e = num(tw[1], 0), pts = [], raw;
    raw = [[-(zi - a), fl], [zi - a, fl], [zi, fl + b], [zi, top - e], [zi - c, top], [-(zi - c), top], [-zi, top - e], [-zi, fl + b]];
    raw.forEach(function (q) {
      var l = pts[pts.length - 1];
      if (!l || Math.abs(l[0] - q[0]) + Math.abs(l[1] - q[1]) > 1e-6) { pts.push(q); }
    });
    if (Math.abs(pts[0][0] - pts[pts.length - 1][0]) + Math.abs(pts[0][1] - pts[pts.length - 1][1]) < 1e-6) { pts.pop(); }
    return { hz: hz, zi: zi, bot: bot, fl: fl, top: top, hw: a, hh: b, tw: c, th: e, pts: pts, inner: zi < hz - 1e-6 || b > 0 || e > 0 };
  }
  /* a convex section moved inwards by d (the layers of a tank that lines the hold, the clearance round a prismatic tank) */
  function inset(pts, d) {
    if (!d) { return pts.slice(); }
    var n = pts.length, area = 0, i, a, b, out = [], L = [];
    for (i = 0; i < n; i++) { a = pts[i]; b = pts[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
    var sg = area > 0 ? 1 : -1;
    for (i = 0; i < n; i++) {
      a = pts[i]; b = pts[(i + 1) % n];
      var dx = b[0] - a[0], dy = b[1] - a[1], l = Math.sqrt(dx * dx + dy * dy) || 1;
      L.push([a[0] - dy / l * sg * d, a[1] + dx / l * sg * d, dx, dy]);
    }
    for (i = 0; i < n; i++) {
      var p1 = L[(i + n - 1) % n], p2 = L[i], den = p1[2] * p2[3] - p1[3] * p2[2];
      if (Math.abs(den) < 1e-9) { out.push([p2[0], p2[1]]); continue; }
      var t = ((p2[0] - p1[0]) * p2[3] - (p2[1] - p1[1]) * p2[2]) / den;
      out.push([p1[0] + p1[2] * t, p1[1] + p1[3] * t]);
    }
    return out;
  }
  /* the same section with every corner rounded to radius r (a semi-membrane tank: flat sides, large round corners) */
  function rounded(pts, r) {
    var n = pts.length, out = [], i, j;
    for (i = 0; i < n; i++) {
      var v = pts[i], a = pts[(i + n - 1) % n], b = pts[(i + 1) % n];
      var ux = a[0] - v[0], uy = a[1] - v[1], la = Math.sqrt(ux * ux + uy * uy) || 1, wx = b[0] - v[0], wy = b[1] - v[1], lb = Math.sqrt(wx * wx + wy * wy) || 1;
      ux /= la; uy /= la; wx /= lb; wy /= lb;
      var th = Math.acos(clamp(ux * wx + uy * wy, -1, 1));
      if (th > Math.PI - 0.02) { out.push(v); continue; }
      var t = Math.min(r / Math.tan(th / 2), la * 0.5, lb * 0.5), rr = t * Math.tan(th / 2);
      var bx = ux + wx, by = uy + wy, bl = Math.sqrt(bx * bx + by * by) || 1, dc = rr / Math.sin(th / 2);
      var cx = v[0] + bx / bl * dc, cy = v[1] + by / bl * dc;
      var a0 = Math.atan2(v[1] + uy * t - cy, v[0] + ux * t - cx), a1 = Math.atan2(v[1] + wy * t - cy, v[0] + wx * t - cx), da = a1 - a0;
      while (da > Math.PI) { da -= 2 * Math.PI; }
      while (da < -Math.PI) { da += 2 * Math.PI; }
      for (j = 0; j <= 4; j++) { out.push([cx + rr * Math.cos(a0 + da * j / 4), cy + rr * Math.sin(a0 + da * j / 4)]); }
    }
    return out;
  }
  function centroid(pts) {
    var x = 0, y = 0;
    pts.forEach(function (q) { x += q[0]; y += q[1]; });
    return [x / pts.length, y / pts.length];
  }
  function spanY(pts) {
    var lo = 1e9, hi = -1e9;
    pts.forEach(function (q) { lo = Math.min(lo, q[1]); hi = Math.max(hi, q[1]); });
    return [lo, hi];
  }
  function shapeZY(pts, hole) {
    var s = shapeXY(pts);
    if (hole) { var h = new T.Path(), i; h.moveTo(hole[0][0], hole[0][1]); for (i = hole.length - 1; i >= 0; i--) { h.lineTo(hole[i][0], hole[i][1]); } s.holes.push(h); }
    return s;
  }
  /* a section [[z, y] ...] (with a hole) drawn along x from x0 to x1 - a wing tank, a layer of a tank that lines the hold */
  function alongX(k, pts, x0, x1, m, o, hole) {
    var g = new T.ExtrudeGeometry(shapeZY(pts, hole), { depth: x1 - x0, bevelEnabled: false, curveSegments: 4 });
    g.rotateY(-Math.PI / 2); g.translate(x1, 0, 0);
    return k.add(g, m, 0, 0, 0, o);
  }
  /* a section [[z, y] ...] standing across the ship at x, facing +x (the cut face of a tank) */
  function faceX(k, pts, m, x, hole, o) {
    var flip = function (q) { return q.map(function (v) { return [-v[0], v[1]]; }); };
    var g = new T.ShapeGeometry(shapeZY(flip(pts), hole ? flip(hole) : null));
    g.rotateY(Math.PI / 2);
    return k.add(g, m, x, 0, 0, o || { cast: false });
  }
  define('hull', function (k, p) {
    var x = p.x || [-10, 10], x0 = x[0], x1 = x[1], hz = num(p.half, num(p.breadth, 12) / 2), bot = num(p.bottom, 0);
    var fl = num(p.floor, bot + 1.2), top = num(p.top, fl + 9), self = k.cur, edge = '#41566b', i;
    var sec = holdSection(p), dbl = sec.inner;
    function back() { k.cur = self; }
    /* a gas carrier's hull (double, hopper, topwing): each structure is a sub-part a label names - the outer shell, the inner
       hull, the double bottom, the wing, hopper and top-wing tanks - with its point on the section at the +x end */
    if (dbl) { k.sub(p.bottom_id || subId(k, p, 'bottom'), { pick: true, name: 'Double bottom' }); } else if (p.bottom_id) { k.sub(p.bottom_id, { pick: true }); }
    k.box(x1 - x0, fl - bot, 2 * hz, k.mat('hull'), (x0 + x1) / 2, (bot + fl) / 2, 0, { cast: false });
    if (dbl) { k.anchor('label', [x1, (bot + fl) / 2, hz * 0.55]); back(); k.anchor('double_bottom', [x1, (bot + fl) / 2, hz * 0.55]); }
    back();
    /* a gas carrier's hold with no spaces given is a sub-part of its own, <hull>_hold: the hold space round the tank */
    var sp = p.spaces && p.spaces.length ? p.spaces : [{ x: [x0, x1], tint: 'grey', id: dbl ? subId(k, p, 'hold') : null, name: 'Hold space' }], bounds = [];
    var fw = dbl ? sec.zi - sec.hw : hz, wy0 = dbl ? fl + sec.hh : fl, wy1 = dbl ? top - sec.th : top;
    sp.forEach(function (s) {
      var a = s.x[0], b = s.x[1], t = tint(s.tint, TINT.grey), mid = (a + b) / 2;
      if (s.id) { k.sub(s.id, { pick: true, name: s.name || '' }); } else { back(); }
      k.box(b - a, 0.1, 2 * fw, k.mat({ color: s.floor || mix(t, '#ffffff', 0.55), rough: 0.85, metal: 0 }), mid, fl + 0.05, 0, { cast: false });
      if (dbl) { k.add(new T.PlaneGeometry(b - a, wy1 - wy0), k.basic(t, num(s.wall, 0.26)), mid, (wy1 + wy0) / 2, -sec.zi + 0.05, { order: 1 }); }
      else if (!p.side_id) { k.add(new T.PlaneGeometry(b - a, top - fl), k.basic(t, num(s.wall, 0.26)), mid, (top + fl) / 2, -hz, { order: 1 }); }
      /* the space's point is on its tinted far wall, low and near its +x end: not on the deck where a deckhouse stands over
         it (gas trial M01 s14), not behind a tank seated in it */
      k.anchor('label', [b - Math.min(0.6, (b - a) / 4), wy0 + (wy1 - wy0) * 0.3, (dbl ? -sec.zi : -hz) + 0.06]);
      back();
      if (a > x0 + 1e-3 && bounds.indexOf(a) < 0) { bounds.push(a); }
      if (b < x1 - 1e-3 && bounds.indexOf(b) < 0) { bounds.push(b); }
    });
    if (dbl) {
      var L = x1 - x0, zi = sec.zi, hw = sec.hw, hh = sec.hh, tw = sec.tw, th = sec.th;
      var bal = tint(p.ballast, TINT.blue), op = num(p.ballast_opacity, 0.3);
      var bfar = k.mat({ color: bal, rough: 0.8, metal: 0 }, { opacity: op }), bnear = k.mat({ color: bal, rough: 0.8, metal: 0 }, { opacity: op * 0.4 });
      var bend = k.mat({ color: bal, rough: 0.8, metal: 0 }, { opacity: Math.min(0.8, op * 2), double: true });
      var name = function (label, at) { k.anchor('label', at); back(); k.anchor(label, at); };
      k.sub(p.side_id || subId(k, p, 'outer'), { pick: true, name: 'Outer shell' });
      k.add(new T.PlaneGeometry(L, top - bot), k.basic(TINT.grey, num(p.far, 0.24)), (x0 + x1) / 2, (top + bot) / 2, -hz, { order: 1 });
      k.add(new T.PlaneGeometry(L, top - bot), k.basic(TINT.grey, num(p.near, 0.1)), (x0 + x1) / 2, (top + bot) / 2, hz, { order: 1, noPick: true });
      /* each structure's point is on the far side (-z), at the +x end: the side the kit draws solid, and from a view of the
         cut-open hold the tank never stands in front of it nor behind it - the near side is ghosted, a point there reads as
         on the tank behind it (gas trial M01 s01, s05, s12: "Top wing tank" on the cargo tank) */
      name('outer_shell', [x1, (wy0 + wy1) / 2, -hz]);
      k.sub(subId(k, p, 'inner'), { pick: true, name: 'Inner hull' });
      var pl = sec.pts, nf = k.mat('steel_mid', { opacity: num(p.inner_far, 0.5) }), nn = k.mat('steel_mid', { opacity: num(p.inner_near, 0.14) });
      for (i = 0; i < pl.length; i++) {
        var a0 = pl[i], b0 = pl[(i + 1) % pl.length], dz = b0[0] - a0[0], dy = b0[1] - a0[1], sl = Math.sqrt(dz * dz + dy * dy);
        if (Math.abs(dy) < 1e-6 || sl < 1e-6) { continue; }                          /* the inner bottom and the deck are not side plating */
        k.box(L, sl, 0.08, (a0[0] + b0[0]) / 2 < 0 ? nf : nn, (x0 + x1) / 2, (a0[1] + b0[1]) / 2, (a0[0] + b0[0]) / 2, { rx: Math.atan2(dz, dy) });
      }
      name('inner_hull', [x1, wy0 + (wy1 - wy0) * 0.62, -zi]);
      [['wing', 'wing_tank', 'Wing tank', zi < hz - 1e-6, function (sg) { return [[sg * zi, wy0], [sg * hz, wy0], [sg * hz, wy1], [sg * zi, wy1]]; }],
       ['hopper', 'hopper_tank', 'Hopper tank', hh > 0, function (sg) { return [[sg * (zi - hw), fl], [sg * hz, fl], [sg * hz, fl + hh], [sg * zi, fl + hh]]; }],
       ['topwing', 'top_wing_tank', 'Top wing tank', th > 0, function (sg) { return [[sg * zi, top - th], [sg * hz, top - th], [sg * hz, top], [sg * (zi - tw), top]]; }]
      ].forEach(function (r) {
        if (!r[3]) { return; }
        k.sub(subId(k, p, r[0]), { pick: true, name: r[2] });
        var far = null;
        [-1, 1].forEach(function (sg) {
          var q = r[4](sg).filter(function (v, j, all) { var w = all[(j + all.length - 1) % all.length]; return Math.abs(v[0] - w[0]) + Math.abs(v[1] - w[1]) > 1e-6; });
          alongX(k, q, x0, x1, sg < 0 ? bfar : bnear, { cast: false });
          /* the section at both ends: the tank reads at once; the near one lighter, so what stands behind it (a Type A tank's
             chocks) still shows */
          faceX(k, q, sg < 0 ? bend : bfar, x1 + 0.01); faceX(k, q, sg < 0 ? bend : bfar, x0 - 0.01);
          if (sg < 0) { far = centroid(q); }
        });
        name(r[1], [x1, far[1], far[0]]);
      });
    } else if (p.side_id) {
      k.sub(p.side_id, { pick: true });
      k.add(new T.PlaneGeometry(x1 - x0, top - fl), k.basic(TINT.grey, num(p.far, 0.24)), (x0 + x1) / 2, (top + fl) / 2, -hz, { order: 1 });
      k.anchor('label', [(x0 + x1) / 2, (fl + top) / 2, -hz]);
      back();
    }
    if (p.near && !dbl) { k.add(new T.PlaneGeometry(x1 - x0, top - fl), k.basic(TINT.grey, p.near), (x0 + x1) / 2, (top + fl) / 2, hz, { order: 1, noPick: true }); }
    var bh = bounds.map(function (bx) { return { x: bx, opacity: 0.16 }; });
    bh.push({ x: x0, opacity: num(p.ends, 0.1) }, { x: x1, opacity: num(p.ends, 0.1) });
    (p.bulkheads || []).forEach(function (o) {
      var f = null;
      bh.forEach(function (b0) { if (Math.abs(b0.x - o.x) < 0.01) { f = b0; } });
      if (f) { each(o, function (v, n) { f[n] = v; }); } else { bh.push(o); }
    });
    bh.forEach(function (b0) {
      var sh = new T.Shape();
      sh.moveTo(-hz, fl); sh.lineTo(hz, fl); sh.lineTo(hz, top); sh.lineTo(-hz, top); sh.lineTo(-hz, fl);
      if (b0.hole) { var h = new T.Path(); h.absarc(0, b0.hole[0], b0.hole[1] + 0.02, 0, Math.PI * 2, true); sh.holes.push(h); }
      var g = new T.ShapeGeometry(sh, 48);
      g.rotateY(Math.PI / 2);
      k.add(g, k.basic('#c3ced9', num(b0.opacity, 0.16)), b0.x, 0, 0, { order: 1, noPick: true });
    });
    var ln = k.boxEdges(x0, x1, bot, top, -hz, hz);
    bounds.forEach(function (bx) { ln = ln.concat(rectX(bx, fl, top, -hz, hz)); });
    if (dbl) {                                          /* the inner hull's lines at both ends and along x, the tanks' tops */
      var pp = sec.pts;
      for (i = 0; i < pp.length; i++) {
        var u = pp[i], w = pp[(i + 1) % pp.length];
        ln.push(x0, u[1], u[0], x0, w[1], w[0], x1, u[1], u[0], x1, w[1], w[0], x0, u[1], u[0], x1, u[1], u[0]);
      }
      [-1, 1].forEach(function (sg) {
        if (sec.hh > 0) { ln.push(x0, fl + sec.hh, sg * sec.zi, x0, fl + sec.hh, sg * hz, x1, fl + sec.hh, sg * sec.zi, x1, fl + sec.hh, sg * hz); }
        if (sec.th > 0) { ln.push(x0, top - sec.th, sg * sec.zi, x0, top - sec.th, sg * hz, x1, top - sec.th, sg * sec.zi, x1, top - sec.th, sg * hz); }
      });
    }
    if (p.ribs) {
      for (i = x0 + p.ribs; i < x1 - 0.5; i += p.ribs) { ln.push(i, fl, -hz, i, top, -hz); }
      ln.push(x0, fl, -hz, x1, fl, -hz, x0, fl, hz, x1, fl, hz);
    }
    k.lines(ln, edge);
    k.anchor('label', [(x0 + x1) / 2, top, 0]);
  });

  /* a piece of steel deck at the ship's side (IGF M03): the deck top is y = 0, the ship's side is the plane z = 0,
     inboard is -z. size [along x, inboard depth]; side: how far the side plating goes down (3.2); seams (spacing) */
  define('deck_plate', function (k, p) {
    var s = p.size || [6, 5], w0 = s[0], dz = s[1], t = num(p.thick, 0.3), sd = num(p.side, 3.2), sm = num(p.seams, 2.2), lp = [], v;
    k.box(w0, t, dz, M(k, p, 'deck'), 0, -t / 2, -dz / 2, { cast: false });
    if (sd > 0) { k.box(w0, sd, 0.14, k.mat('side'), 0, -sd / 2, -0.07, { cast: false }); }
    for (v = -w0 / 2 + sm / 2; v < w0 / 2 - 0.3; v += sm) { lp.push(v, 0.002, -dz, v, 0.002, 0); if (sd > 0) { lp.push(v, 0, 0.002, v, -sd, 0.002); } }
    for (v = -sm * 0.8; v > -dz; v -= sm * 0.8) { lp.push(-w0 / 2, 0.002, v, w0 / 2, 0.002, v); }
    for (v = -1.5; sd > 0 && v > -sd + 0.3; v -= 1.5) { lp.push(-w0 / 2, v, 0.002, w0 / 2, v, 0.002); }
    k.lines(lp, '#33424f');
    k.cyl('x', 0.06, w0, k.mat({ color: '#4a5764', rough: 0.6, metal: 0.4 }), 0, 0.02, 0.02, { seg: 12, cast: false });
    if (p.rail) {
      var rm = k.mat({ color: '#d6b13a', rough: 0.5, metal: 0.3 });
      k.cyl('x', 0.03, w0, rm, 0, 1.0, -0.05, { seg: 8 }); k.cyl('x', 0.025, w0, rm, 0, 0.5, -0.05, { seg: 8 });
      for (v = -w0 / 2 + 0.2; v <= w0 / 2; v += 1.5) { k.cyl('y', 0.03, 1.0, rm, v, 0.5, -0.05, { seg: 8 }); }
    }
    k.anchor('label', [0, 0, -dz * 0.6]);
  });

  /* a cut-open room (IGF M04, M05, M09): floor plates, back and side walls with frames, the front left open with light
     cut-edge strips. size [w, h, d]; at = the floor's centre. roof: true; glass: ["right", "roof"] see-through sides;
     frames: spacing (0.6); open: "front" (default) or "front+right" ... */
  define('room', function (k, p) {
    var s = p.size || [6, 3, 4], W = s[0], H = s[1], D = s[2], t = 0.08, wall = M(k, p, 'wall'), glass = p.glass || [];
    var open = p.open || 'front', fr = num(p.frames, 0.6), x, lp = [];
    function see(side) { return glass.indexOf(side) >= 0; }
    function ghost() { return k.basic('#cfe2ee', 0.16); }
    var fm0 = k.mat('floor_dark'), ho = p.hole;          /* hole [x0, z0, x1, z1]: a bilge well's opening in the floor */
    if (ho) {
      k.box(ho[0] + W / 2, 0.06, D, fm0, (-W / 2 + ho[0]) / 2, -0.03, 0, { cast: false });
      k.box(W / 2 - ho[2], 0.06, D, fm0, (ho[2] + W / 2) / 2, -0.03, 0, { cast: false });
      k.box(ho[2] - ho[0], 0.06, ho[1] + D / 2, fm0, (ho[0] + ho[2]) / 2, -0.03, (-D / 2 + ho[1]) / 2, { cast: false });
      k.box(ho[2] - ho[0], 0.06, D / 2 - ho[3], fm0, (ho[0] + ho[2]) / 2, -0.03, (ho[3] + D / 2) / 2, { cast: false });
    } else { k.box(W, 0.06, D, fm0, 0, -0.03, 0, { cast: false }); }
    for (x = -W / 2 + 1.2; x < W / 2; x += 1.2) { lp.push(x, 0.002, -D / 2, x, 0.002, D / 2); }
    k.lines(lp, '#33424f');
    k.box(W, H, t, see('back') ? ghost() : wall, 0, H / 2, -D / 2 - t / 2, { cast: false });
    if (open.indexOf('left') < 0) { k.box(t, H, D, see('left') ? ghost() : wall, -W / 2 - t / 2, H / 2, 0, { cast: false }); }
    if (open.indexOf('right') < 0) { k.box(t, H, D, see('right') ? ghost() : wall, W / 2 + t / 2, H / 2, 0, { cast: false }); }
    if (p.roof) { k.box(W, t, D, see('roof') ? ghost() : wall, 0, H + t / 2, 0, { cast: false }); }
    if (fr > 0) {
      var fm = k.mat('frame'), list = [];
      for (x = -W / 2 + fr; x < W / 2 - 0.1; x += fr) { list.push([x, H / 2, -D / 2 + 0.06]); }
      if (list.length) { k.many(new T.BoxGeometry(0.06, H, 0.12), fm, list); }
    }
    var trim = k.mat('trim');
    k.box(W + 2 * t, 0.06, 0.06, trim, 0, 0, D / 2);
    if (open.indexOf('left') < 0) { k.box(0.06, H, 0.06, trim, -W / 2 - t / 2, H / 2, D / 2); }
    if (open.indexOf('right') < 0) { k.box(0.06, H, 0.06, trim, W / 2 + t / 2, H / 2, D / 2); }
    k.anchor('label', [0, H, -D / 2]);
  });

  /* a gas-tight steel box standing on what it covers (IGF M02's tank connection space): its five walls fade away with
     the state "<id>.open" (0..1) to show what is inside. size [w, h, d]; at = floor centre; wall (0.25); floor: true */
  define('enclosure', function (k, p) {
    var s = p.size || [4, 3, 4], W = s[0], H = s[1], D = s[2], t = num(p.wall, 0.25), walls = [];
    var m = M(k, p, null);
    if (!p.mat && !p.color) { m = k.mat({ color: '#d8b05a', rough: 0.5, metal: 0.3 }); }
    m.transparent = true; m.depthWrite = true; m.userData.o0 = 1;
    walls.push(k.box(t, H, D, m, -W / 2, H / 2, 0, { keep: true, cast: false }), k.box(t, H, D, m, W / 2, H / 2, 0, { keep: true, cast: false }),
      k.box(W, H, t, m, 0, H / 2, -D / 2, { keep: true, cast: false }), k.box(W, H, t, m, 0, H / 2, D / 2, { keep: true, cast: false }),
      k.box(W + t, t, D + t, m, 0, H, 0, { keep: true, cast: false }));
    if (p.floor) { walls.push(k.box(W, t, D, m, 0, 0, 0, { keep: true, cast: false })); }
    var e1 = k.lines(k.boxEdges(-W / 2, W / 2, 0, H, -D / 2, D / 2), '#7a5410');
    var e2 = k.lines(k.boxEdges(-W / 2 - 0.1, W / 2 + 0.1, 0, H + 0.1, -D / 2 - 0.1, D / 2 + 0.1), '#f7d58a', { order: 5 });
    var o1 = num(p.open_opacity, 0);                    /* open_opacity: open, the walls stay as glass (0.15) - still a space */
    k.state(k.cur.id + '.open', 0, function (a) {
      m.opacity = 1 - a * (1 - o1);
      m.depthWrite = a < 0.02;
      walls.forEach(function (x) { x.visible = o1 > 0 || a < 0.995; });
      e1.visible = a < 0.5;
      e2.visible = p.keep_frame || a < 0.98;           /* keep_frame: its light outline stays, so the space is still seen */
    });
    k.anchor('label', [0, H + t / 2, 0]);
  });

  /* a see-through wall, size [w, h] in the x-y plane (turn it with "rot") */
  define('panel', function (k, p) {
    var s = p.size || [4, 3];
    k.add(new T.PlaneGeometry(s[0], s[1]), k.basic(tint(p.tint, TINT.grey), num(p.opacity, 0.2)), 0, 0, 0, { order: 1 });
    k.anchor('label', [0, s[1] / 2, 0]);
  });

  /* a deckhouse (IGF M15): a block with rows of windows, a wheelhouse on top. size [w, h, d]; decks (rows) */
  define('accommodation', function (k, p) {
    var s = p.size || [10, 9, 8], W = s[0], H = s[1], D = s[2], n = num(p.decks, 3), i, j, win = [], dh = H / (n + 0.6);
    var body = M(k, p, 'accommodation');
    k.box(W, H, D, body, 0, H / 2, 0);
    k.box(W * 0.55, dh * 0.9, D * 0.7, body, -W * 0.1, H + dh * 0.45, 0);
    var lp = [];
    for (i = 1; i <= n; i++) { lp.push(-W / 2, i * dh, D / 2 + 0.01, W / 2, i * dh, D / 2 + 0.01); }
    k.lines(lp, '#9aa6b1');
    for (i = 0; i < n; i++) {
      for (j = -W / 2 + 0.9; j < W / 2 - 0.5; j += 1.4) { win.push([j, i * dh + dh * 0.55, D / 2 + 0.02]); }
    }
    for (j = -W * 0.32; j < W * 0.15; j += 0.9) { win.push([j, H + dh * 0.5, D * 0.35 + 0.02]); }
    if (win.length) { k.many(new T.BoxGeometry(0.8, dh * 0.38, 0.04), k.mat('window'), win, { cast: false }); }
    k.anchor('label', [0, H + dh * 0.9, 0]);
    /* doors: a door in each side wall (+z and -z), that far from the -x end (the front, which faces the cargo area) -
       sub-part <id>_doors; the front itself has none */
    if (num(p.doors, 0) > 0) {
      var self = k.cur, dx = -W / 2 + Math.min(p.doors, W - 0.6);
      k.sub(subId(k, p, 'doors'), { pick: true, name: 'Doors' });
      [-1, 1].forEach(function (sg) {
        k.box(0.95, 2.05, 0.06, k.mat('steel_dark'), dx, 1.12, sg * (D / 2 + 0.03));
        k.box(0.8, 1.9, 0.05, k.mat('steel_mid'), dx, 1.12, sg * (D / 2 + 0.06));
      });
      k.anchor('label', [dx, 2.1, D / 2 + 0.08]);
      k.cur = self;
    }
  });

  /* an airlock: the small steel space between a gas-dangerous open deck (-x) and a gas-safe space (+x) - two
     self-closing gastight steel doors `gap` apart (2 m; 1.5 to 2.5), each on its sill with a door closer and no hook, and
     an alarm lamp and sounder on both sides. at = the floor's centre; size [gap, h, w]; the near wall (+z) is glass so the
     inside shows. Sub-parts <id>_door1 (the outer door, from the deck), <id>_door2 (the inner door), <id>_alarm (the
     lamps and sounders); anchors door1, door2, alarm; states <id>.open (the outer door swings open) and <id>.alarm (the
     lamps light: 0.5 amber, 1 red) */
  define('airlock', function (k, p) {
    var s = p.size || [num(p.gap, 2), 2.4, 1.6], L = s[0], H = s[1], Wd = s[2], t = 0.06, self = k.cur, wall = M(k, p, 'wall');
    k.box(L, 0.06, Wd, k.mat('floor_dark'), 0, -0.03, 0, { cast: false });
    k.box(L, H, t, wall, 0, H / 2, -Wd / 2 - t / 2, { cast: false });
    k.add(new T.PlaneGeometry(L, H), k.basic('#cfe2ee', 0.16), 0, H / 2, Wd / 2, { order: 1, noPick: true });
    k.box(L + 2 * t, t, Wd + t, wall, 0, H + t / 2, 0, { cast: false });
    var dw = Math.min(0.8, Wd - 0.4), dh = Math.min(1.9, H - 0.4), sill = 0.3, open = [];
    [-1, 1].forEach(function (sg) {                      /* the end walls round each door: steel to each side and above */
      var x = sg * (L / 2 + t / 2), side = (Wd - dw) / 2;
      k.box(t, H, side, wall, x, H / 2, -(dw + side) / 2, { cast: false });
      k.box(t, H, side, wall, x, H / 2, (dw + side) / 2, { cast: false });
      k.box(t, H - sill - dh, dw, wall, x, (sill + dh + H) / 2, 0, { cast: false });
      k.box(t, sill, dw, k.mat('steel_dark'), x, sill / 2, 0, { cast: false });
    });
    ['door1', 'door2'].forEach(function (n, i) {
      var sg = i ? 1 : -1, x = sg * (L / 2 + t / 2);
      k.sub(subId(k, p, n), { pick: true, name: i ? 'Inner door' : 'Outer door' });
      k.box(0.05, dh + 0.1, dw + 0.1, k.mat('steel_black'), x - sg * 0.02, sill + dh / 2, 0);   /* the frame and its gasket */
      var g = k.push([x + sg * 0.05, sill, -dw / 2]);
      k.box(0.05, dh, dw, k.mat('steel_mid'), 0, dh / 2, dw / 2, { keep: true });
      k.box(0.03, 0.05, dw * 0.45, k.mat('steel_dark'), sg * 0.05, dh - 0.12, dw * 0.3, { keep: true });   /* the door closer */
      k.cyl('x', 0.035, 0.12, k.mat('steel_dark'), sg * 0.06, dh - 0.12, dw * 0.08, { keep: true, seg: 12 });
      k.box(0.04, 0.12, 0.03, k.mat('steel_black'), sg * 0.05, dh * 0.5, dw * 0.85, { keep: true });          /* the handle */
      k.pop();
      if (!i) { open.push(g); }
      k.anchor('label', [x + sg * 0.08, sill + dh * 0.62, dw * 0.15]);
      k.cur = self;
      k.anchor(n, [x + sg * 0.08, sill + dh * 0.62, dw * 0.15]);
    });
    k.state(self.id + '.open', 0, function (v) { open.forEach(function (g) { g.rotation.y = v * 1.4; }); });
    /* the alarm on both sides: a lamp and a sounder over the outer door on the deck, and over the inner door inside the
       gas-safe space */
    k.sub(subId(k, p, 'alarm'), { pick: true, name: 'Alarm' });
    var lamps = [], off = k.col('#3a2a20'), amb = new T.Color('#ffb020'), red = new T.Color('#ff3030');
    [-1, 1].forEach(function (sg) {
      var x = sg * (L / 2 + t + 0.12), y = sill + dh + 0.25;
      k.box(0.18, 0.12, 0.3, k.mat('steel_dark'), x, y, -dw * 0.2);
      var lm = k.basic('#3a2a20', 1, { toneMapped: false });
      k.ball(0.07, lm, x + sg * 0.04, y + 0.12, -dw * 0.2, { seg: 14, cast: false, keep: true });
      lamps.push(lm);
      k.cyl('x', 0.07, 0.08, k.mat('red'), x + sg * 0.04, y, dw * 0.25, { seg: 16 });          /* the sounder */
    });
    k.state(self.id + '.alarm', 0, function (v) {
      var c = v < 0.5 ? off.clone().lerp(amb, v * 2) : amb.clone().lerp(red, (v - 0.5) * 2);
      lamps.forEach(function (lm) { lm.color.copy(c); lm.userData.c0 = c.clone(); });
    });
    k.anchor('label', [-(L / 2 + t + 0.16), sill + dh + 0.4, -dw * 0.2]);
    k.cur = self;
    k.anchor('alarm', [-(L / 2 + t + 0.16), sill + dh + 0.4, -dw * 0.2]);
    k.anchor('label', [0, H + t, 0]);
  });

  /* a cargo compressor house on deck: the compressor room (-x) and the electric motor room (+x) side by
     side, divided by a gastight bulkhead the drive shaft passes through in a gastight seal. at = the floor's centre; size
     [w, h, d]; split (0.5, where the bulkhead stands across w); the near wall (+z) and the roof are glass so both rooms
     show. Sub-parts <id>_compressor (the room and its compressor), <id>_motor (the room and its motor), <id>_bulkhead,
     <id>_shaft (the shaft and its seal). State <id>.on: the ventilation runs - air drawn out of the compressor room
     (negative pressure, the arrow up out of its roof) and pushed into the motor room (positive pressure, the arrow down
     into it) */
  define('compressor_house', function (k, p) {
    var s = p.size || [10, 4, 5], W = s[0], H = s[1], D = s[2], t = 0.08, self = k.cur, wall = M(k, p, 'wall');
    var xb = -W / 2 + W * clamp(num(p.split, 0.5), 0.2, 0.8), arrows = [];
    function room(n, name, a, b, tint0) {
      k.cur = self;
      k.sub(subId(k, p, n), { pick: true, name: name });
      k.box(b - a, 0.06, D, k.mat({ color: mix(TINT[tint0], '#ffffff', 0.55), rough: 0.85, metal: 0 }), (a + b) / 2, -0.03, 0, { cast: false });
      k.box(b - a, H, t, wall, (a + b) / 2, H / 2, -D / 2 - t / 2, { cast: false });
      k.add(new T.PlaneGeometry(b - a, H), k.basic('#cfe2ee', 0.14), (a + b) / 2, H / 2, D / 2, { order: 1, noPick: true });
      k.add(new T.PlaneGeometry(b - a, D), k.basic('#cfe2ee', 0.12), (a + b) / 2, H, 0, { order: 1, noPick: true, rx: -Math.PI / 2 });
    }
    room('compressor', 'Compressor room', -W / 2, xb, 'amber');
    var cx = (-W / 2 + xb) / 2, cm = k.mat('engine');
    k.box(Math.min(2.2, (xb + W / 2) * 0.6), 0.25, 1.4, k.mat('foundation'), cx, 0.125, -D * 0.1);
    k.cyl('x', 0.55, Math.min(1.8, (xb + W / 2) * 0.5), cm, cx, 0.9, -D * 0.1, { seg: 28 });
    k.cyl('y', 0.18, 1.2, k.mat('pipe'), cx - 0.3, 1.9, -D * 0.1, { seg: 16 });
    k.box(t, H, D, wall, -W / 2 - t / 2, H / 2, 0, { cast: false });
    k.anchor('label', [cx, 1.5, -D * 0.1]);
    room('motor', 'Motor room', xb, W / 2, 'green');
    var mx = (xb + W / 2) / 2;
    k.box(Math.min(2.0, (W / 2 - xb) * 0.6), 0.25, 1.2, k.mat('foundation'), mx, 0.125, -D * 0.1);
    k.cyl('x', 0.5, Math.min(1.6, (W / 2 - xb) * 0.45), k.mat({ color: '#4f6f8f', rough: 0.5, metal: 0.4 }), mx, 0.85, -D * 0.1, { seg: 28 });
    k.box(t, H, D, wall, W / 2 + t / 2, H / 2, 0, { cast: false });
    k.anchor('label', [mx, 1.4, -D * 0.1]);
    k.cur = self;
    k.sub(subId(k, p, 'bulkhead'), { pick: true, name: 'Gastight bulkhead' });
    k.box(0.12, H, D, k.mat('steel_mid'), xb, H / 2, 0, { cast: false });
    k.anchor('label', [xb, H * 0.75, D * 0.3]);
    k.cur = self;
    k.sub(subId(k, p, 'shaft'), { pick: true, name: 'Shaft seal' });
    k.cyl('x', 0.06, mx - cx, k.mat('stainless'), (cx + mx) / 2, 0.88, -D * 0.1, { seg: 16 });
    k.cyl('x', 0.2, 0.3, k.mat('steel_dark'), xb, 0.88, -D * 0.1, { seg: 24 });
    k.anchor('label', [xb + 0.2, 0.88, -D * 0.1 + 0.2]);
    k.cur = self;
    [[cx, 0.3, 1], [mx, -0.3, -1]].forEach(function (a) {   /* out of the compressor room's roof; into the motor room's */
      var y0 = a[2] > 0 ? H - 0.6 : H + 1.4, y1 = a[2] > 0 ? H + 1.4 : H - 0.6, m = k.mat('cold');
      arrows.push(k.seg([a[0], y0, D * 0.2], [a[0], y1 - a[2] * 0.3, D * 0.2], 0.06, m, { keep: true }));
      arrows.push(k.cone([a[0], y1, D * 0.2], [0, a[2], 0], 0.16, 0.3, m, { keep: true }));
    });
    k.state(self.id + '.on', 0, function (v) { arrows.forEach(function (m) { m.visible = v > 0.5; }); });
    k.anchor('label', [0, H + 0.1, 0]);
  });

  /* -------------------------------------------------------------------- tanks */
  /* IMO type C (IGF M01, M02, M07): a cylinder with 2:1 dished ends, stiffening rings, two saddles. at = the axis's
     centre; the axis runs along x (turn it with "rot"). r, len (the cylindrical part), head (end depth, r/2), rings
     [x] or a count, saddles [x], base (the floor's y under it, -r - 0.6); cut: true takes the front half (z > 0) away;
     fill (0..1 of the diameter) draws the liquid, sub-part "liquid"; insulation (thickness) its own layer, seen at
     the cut; dome: true a manway dome on top */
  /* a bilobe Type C tank ("lobes": 2): two cylinders that meet in ONE vessel, a centreline bulkhead where they join (sub-part
     <id>_bulkhead). spread: each lobe's axis off the centre line (0.55 r); "cut": the +x half away, so the section shows
     both lobes, the bulkhead and the liquid on each side of it. Saddles carry both lobes. */
  function bilobe(k, p, R, L, A) {
    var X0 = -L / 2, X1 = L / 2, self = k.cur, d = num(p.spread, R * 0.55), h = Math.sqrt(Math.max(0.01, R * R - d * d));
    var ti = num(p.insulation, 0), cutC = p.cut ? k.clip([-1, 0, 0], 0) : null, i, j, lp = [];
    var rings = p.rings != null ? p.rings : 4, rt = num(p.ring_t, Math.max(0.05, R * 0.027));
    if (typeof rings === 'number') { var rr = []; for (i = 0; i < rings; i++) { rr.push(X0 + L * (i + 0.5) / rings); } rings = rr; }
    var halves = {}, bulkId = subId(k, p, 'bulkhead'), liqId = subId(k, p, 'liquid');
    function head(sign, x, r, m, zc) {
      var g = new T.SphereGeometry(r, 72, 24, 0, Math.PI * 2, 0, Math.PI / 2);
      g.scale(1, (A + r - R) / r, 1);
      g.rotateZ(sign * Math.PI / 2);
      return k.add(g, m, x, 0, zc);
    }
    /* the arc of one lobe's circle (radius r) on its own side of the centre line, top to bottom, in [z, y] */
    function arc(sg, r) {
      var t0 = Math.acos(clamp(-d / r, -1, 1)), out = [], n = 36;
      for (j = 0; j <= n; j++) { var t = t0 - 2 * t0 * j / n; out.push([sg * (d + r * Math.cos(t)), r * Math.sin(t)]); }
      return out;
    }
    [-1, 1].forEach(function (sg) {
      var half = k.clip([0, 0, sg], 0), cl = cutC ? [half, cutC] : [half], ex = { clip: cl }, zc = sg * d;
      halves[sg] = cl;
      var shell = M(k, p, p.cut ? 'shell' : 'tank', ex), ringM = k.mat('ring', ex);
      var cyl = new T.CylinderGeometry(R, R, L, 72, 1, true);
      cyl.rotateZ(Math.PI / 2);
      k.add(cyl, shell, 0, 0, zc);
      head(1, X0, R, shell, zc); head(-1, X1, R, shell, zc);
      rings.forEach(function (x) { k.ring('x', R + 0.04 + (rt > 0.1 ? rt * 0.5 : 0), rt, ringM, x, 0, zc, { seg: 72 }); });
      if (ti) {
        var im = k.mat('insulation', ex), ic = new T.CylinderGeometry(R + ti, R + ti, L, 72, 1, true);
        ic.rotateZ(Math.PI / 2);
        k.add(ic, im, 0, 0, zc);
        head(1, X0, R + ti, im, zc); head(-1, X1, R + ti, im, zc);
      }
      if (p.cut) {                                       /* the section: each lobe's wall, its insulation */
        var a = arc(sg, R);
        for (j = 0; j < a.length - 1; j++) { lp.push(0.004, a[j][1], a[j][0], 0.004, a[j + 1][1], a[j + 1][0]); }
        if (ti) { faceX(k, arc(sg, R + ti).concat(arc(sg, R).reverse()), k.mat('insulation'), 0.003); }
      }
    });
    var base = num(p.base, -R - 0.6), Rr = R + ti + 0.03, zw = d + Rr * 0.88, sads = p.saddles || [X0 + L * 0.2, X1 - L * 0.2];
    if (sads.length) { k.sub(subId(k, p, 'saddles'), { pick: true, name: 'Saddles' }); }
    sads.forEach(function (sx) {
      var sh = new T.Shape(), n = 40;
      sh.moveTo(-zw, base); sh.lineTo(zw, base);
      for (j = 0; j <= n; j++) {
        var z = zw - 2 * zw * j / n, u = Math.abs(z) - d;
        sh.lineTo(z, -Math.sqrt(Math.max(0, Rr * Rr - u * u)));
      }
      sh.lineTo(-zw, base);
      var dep = Math.max(0.5, R * 0.2), g = new T.ExtrudeGeometry(sh, { depth: dep, bevelEnabled: false, curveSegments: 24 });
      g.rotateY(Math.PI / 2);
      k.add(g, k.mat('saddle', cutC ? { clip: [cutC] } : null), sx - dep / 2, 0, 0);
    });
    if (sads.length) {                                   /* on the first saddle: a cut takes the +x half away */
      k.anchor('label', [sads[0] + Math.max(0.5, R * 0.2) / 2, (base - h) / 2, -zw * 0.6]);
      k.cur = self;
    }
    if (p.dome) { tankDome(k, p, R, X1 - L * 0.25, -d); }
    if (lp.length) { lp.push(0.004, -h, 0, 0.004, h, 0); k.lines(lp, '#3f4a54'); }
    k.anchor('label', [cutC ? 0 : X0 + L * 0.3, R + ti, -d]);
    k.sub(bulkId, { pick: true, name: 'Centreline bulkhead' });
    var ah = A * h / R, bs = new T.Shape();
    bs.moveTo(X0, -h); bs.lineTo(X1, -h);
    bs.absellipse(X1, 0, ah, h, -Math.PI / 2, Math.PI / 2, false);
    bs.lineTo(X0, h);
    bs.absellipse(X0, 0, ah, h, Math.PI / 2, Math.PI * 1.5, false);
    k.add(new T.ShapeGeometry(bs, 24), k.mat('steel_mid', cutC ? { clip: [cutC] } : { double: true }), 0, 0, 0);
    k.anchor('label', [cutC ? 0 : X0 + L * 0.3, h * 0.45, 0]);
    k.cur = self;
    if (p.fill > 0) {
      k.sub(liqId, { pick: true });
      var Rl = R * 0.985, lv = -Rl + p.fill * 2 * Rl;
      [-1, 1].forEach(function (sg) {
        k.push([0, 0, sg * d]);
        liquidC(k, Rl, A * 0.985, X0, X1, p.fill, halves[sg], p.liquid_color, { face: false });
        k.pop();
        if (p.cut) {
          var poly = below(arc(sg, Rl), lv), col = p.liquid_color || '#5fb4ea';
          if (poly.length > 2) { faceX(k, poly, k.mat({ color: mix(col, '#2a8fd6', 0.3), rough: 0.2, metal: 0 }, { opacity: 0.8, double: true }), 0.01, null, { order: 3, cast: false }); }
        }
      });
      k.anchor('label', [cutC ? 0 : X0 + L * 0.15, lv - R * 0.3, d]);
      k.cur = self;
    }
  }
  /* a Type C tank's dome (sub-part <id>_dome, its point on top): on a tank seated "in" a hold it rises through the deck,
     where the cargo pipes leave the tank (gas trial M01 s12: a stub that ended below the deck); otherwise a short manway */
  function tankDome(k, p, R, x, z) {
    var self = k.cur, r = R * 0.18, y0 = R * 0.94, y1 = R * 1.295, hold = p._hold;
    if (hold && Array.isArray(p.at)) { y1 = Math.max(y1, hold.y0 + hold.sec.top - p.at[1] + 0.8); }
    k.sub(subId(k, p, 'dome'), { pick: true, name: 'Tank dome' });
    k.cyl('y', r, y1 - y0, k.mat(p.cut ? 'shell' : 'tank'), x, (y0 + y1) / 2, z, { seg: 32 });
    k.cyl('y', r * 1.25, 0.08, k.mat('flange'), x, y1 - 0.04, z, { seg: 32 });
    k.anchor('label', [x, y1, z]);
    k.cur = self;
  }
  define('tank_c', function (k, p) {
    var R = num(p.r, 3), L = num(p.len, 10), A = num(p.head, R / 2), X0 = -L / 2, X1 = L / 2, self = k.cur, i;
    if (num(p.lobes, 1) >= 2) { bilobe(k, p, R, L, A); return; }
    var clip = p.cut ? [k.clip([0, 0, -1], 0)] : null, ex = clip ? { clip: clip } : null;
    var shell = M(k, p, p.cut ? 'shell' : 'tank', ex), ringM = k.mat('ring', ex);
    var cyl = new T.CylinderGeometry(R, R, L, 72, 1, true);
    cyl.rotateZ(Math.PI / 2);
    k.add(cyl, shell, 0, 0, 0);
    function head(sign, x, r, m) {
      var g = new T.SphereGeometry(r, 72, 24, 0, Math.PI * 2, 0, Math.PI / 2);
      g.scale(1, (A + r - R) / r, 1);
      g.rotateZ(sign * Math.PI / 2);
      return k.add(g, m, x, 0, 0);
    }
    head(1, X0, R, shell); head(-1, X1, R, shell);
    var rings = p.rings != null ? p.rings : 4;
    if (typeof rings === 'number') { var rr = []; for (i = 0; i < rings; i++) { rr.push(X0 + L * (i + 0.5) / rings); } rings = rr; }
    var rt = num(p.ring_t, Math.max(0.05, R * 0.027));  /* ring_t: a thicker band (IGF M02's insulation bands) */
    rings.forEach(function (x) { k.ring('x', R + 0.04 + (rt > 0.1 ? rt * 0.5 : 0), rt, ringM, x, 0, 0, { seg: 72 }); });
    var base = num(p.base, -R - 0.6), zw = num(p.saddle_w, R * 0.88), sads = p.saddles || [X0 + L * 0.2, X1 - L * 0.2];
    if (sads.length) { k.sub(subId(k, p, 'saddles'), { pick: true, name: 'Saddles' }); }
    sads.forEach(function (sx) {
      var Rr = R + (p.insulation || 0) + 0.03, yt = -Math.sqrt(Math.max(0.01, Rr * Rr - zw * zw)), a0 = Math.atan2(yt, zw);
      var sh = new T.Shape();
      sh.moveTo(-zw, base); sh.lineTo(zw, base); sh.lineTo(zw, yt);
      sh.absarc(0, 0, Rr, a0, -Math.PI - a0, true);
      sh.lineTo(-zw, base);
      var dep = Math.max(0.5, R * 0.2), g = new T.ExtrudeGeometry(sh, { depth: dep, bevelEnabled: false, curveSegments: 24 });
      g.rotateY(Math.PI / 2);
      k.add(g, k.mat('saddle'), sx - dep / 2, 0, 0);
    });
    if (sads.length) {                                   /* the point on the last saddle's +x face, between its foot and its seat */
      var Rs0 = R + (p.insulation || 0) + 0.03, ys = -Math.sqrt(Math.max(0.01, Rs0 * Rs0 - zw * zw));
      k.anchor('label', [sads[sads.length - 1] + Math.max(0.5, R * 0.2) / 2, (base + ys) / 2, -zw * 0.6]);
      k.cur = self;
    }
    if (p.insulation) {
      var ti = p.insulation, im = k.mat('insulation', ex);
      var ic = new T.CylinderGeometry(R + ti, R + ti, L, 72, 1, true); ic.rotateZ(Math.PI / 2);
      k.add(ic, im, 0, 0, 0);
      head(1, X0, R + ti, im); head(-1, X1, R + ti, im);
      if (p.cut) {                                       /* the cut faces of the layer, top and bottom */
        k.box(L, ti, 0.02, k.mat('insulation'), 0, R + ti / 2, 0.005);
        k.box(L, ti, 0.02, k.mat('insulation'), 0, -R - ti / 2, 0.005);
      }
    }
    if (p.dome) { tankDome(k, p, R, X1 - L * 0.25, -(p.cut ? R * 0.3 : 0)); }
    if (p.cut) {                                        /* the cut rim: thin lines where the shell is cut */
      var lp = [X0, R, 0, X1, R, 0, X0, -R, 0, X1, -R, 0], n = 20, j, side, u, ra, rb;
      for (side = 0; side < 2; side++) {
        for (j = 0; j < n; j++) {
          u = j / n; ra = R * Math.sqrt(Math.max(0, 1 - u * u)); u = (j + 1) / n; rb = R * Math.sqrt(Math.max(0, 1 - u * u));
          var xa = side === 0 ? X0 - (j / n) * A : X1 + (j / n) * A, xb = side === 0 ? X0 - ((j + 1) / n) * A : X1 + ((j + 1) / n) * A;
          lp.push(xa, ra, 0, xb, rb, 0, xa, -ra, 0, xb, -rb, 0);
        }
      }
      k.lines(lp, '#3f4a54');
    }
    k.anchor('label', [0, R + (p.insulation || 0), 0]);
    if (p.fill > 0) {
      k.sub(subId(k, p, 'liquid'), { pick: true });
      liquidC(k, R * 0.985, A * 0.985, X0, X1, p.fill, clip, p.liquid_color);
      k.anchor('label', [X0 + L * 0.15, -R + p.fill * 2 * R - R * 0.38, 0]);
      k.cur = self;
    }
  });
  /* the liquid in a horizontal tank with dished ends: a real volume below the level, its surface, and its flat section
     where the tank is cut (IGF M01); o.face false leaves that section out (a bilobe draws its own at its end cut) */
  function liquidC(k, Rl, A, X0, X1, fill, clip, color, o) {
    var level = -Rl + fill * 2 * Rl, slices = [], i, j, nh = 14, nc = 8, Mn = 40, u;
    for (i = 0; i <= nh; i++) { u = -1 + i / nh; slices.push({ x: X0 + u * A, R: Rl * Math.sqrt(Math.max(0, 1 - u * u)) }); }
    for (i = 1; i < nc; i++) { slices.push({ x: X0 + (X1 - X0) * i / nc, R: Rl }); }
    for (i = 0; i <= nh; i++) { u = i / nh; slices.push({ x: X1 + u * A, R: Rl * Math.sqrt(Math.max(0, 1 - u * u)) }); }
    var pos = [], idx = [], spos = [], sidx = [], cpos = [], cidx = [], lvl = [], sl, y0, t0, t, a, b, c0, d0, base;
    for (i = 0; i < slices.length; i++) {
      sl = slices[i];
      y0 = Math.min(level, sl.R);
      t0 = sl.R > 1e-4 ? Math.acos(clamp(y0 / sl.R, -1, 1)) : 0;
      for (j = 0; j <= Mn; j++) { t = t0 + (2 * Math.PI - 2 * t0) * j / Mn; pos.push(sl.x, sl.R * Math.cos(t), sl.R * Math.sin(t)); }
      spos.push(sl.x, y0, sl.R * Math.sin(t0), sl.x, y0, -sl.R * Math.sin(t0));
      cpos.push(sl.x, -sl.R, 0, sl.x, y0, 0);
      if (i > 0) {
        lvl.push(slices[i - 1].x, Math.min(level, slices[i - 1].R), 0, sl.x, y0, 0);
        cidx.push(2 * (i - 1), 2 * i, 2 * (i - 1) + 1, 2 * (i - 1) + 1, 2 * i, 2 * i + 1);
      }
    }
    for (i = 0; i < slices.length - 1; i++) {
      for (j = 0; j < Mn; j++) { a = i * (Mn + 1) + j; b = a + 1; c0 = a + Mn + 1; d0 = c0 + 1; idx.push(a, c0, b, b, c0, d0); }
      base = i * 2; sidx.push(base, base + 2, base + 1, base + 1, base + 2, base + 3);
    }
    function geo(P0, I0) { var g = new T.BufferGeometry(); g.setAttribute('position', new T.Float32BufferAttribute(P0, 3)); g.setIndex(I0); g.computeVertexNormals(); return g; }
    var col = color || '#5fb4ea', cut = clip ? { clip: clip } : {};
    var ex1 = { opacity: 0.55, double: true }, ex2 = { opacity: 0.85, double: true };
    if (clip) { ex1.clip = clip; ex2.clip = clip; }
    k.add(geo(pos, idx), k.mat({ color: col, rough: 0.15, metal: 0 }, ex1), 0, 0, 0, { order: 2 });
    k.add(geo(spos, sidx), k.mat({ color: mix(col, '#ffffff', 0.4), rough: 0.1, metal: 0 }, ex2), 0, 0, 0, { order: 3 });
    if (clip && !(o && o.face === false)) {
      k.add(geo(cpos, cidx), k.mat({ color: mix(col, '#2a8fd6', 0.3), rough: 0.2, metal: 0 }, { opacity: 0.78, double: true }), 0, 0, 0, { order: 3 });
      k.lines(lvl, '#2f86c0');
    }
    return cut;
  }

  /* a spherical (Moss) tank on its skirt (cut, fill, insulation as tank_c). at = the sphere's centre; r; base: the skirt's foot
     below the centre (negative) - the skirt (sub-part <id>_skirt) carries the sphere at its equator, its equatorial ring there,
     and stands on the inner bottom ("in": "<hull>" puts it there). drip: the drip tray under the sphere, the partial secondary
     barrier (<id>_drip); cover: the tank cover above the deck (<id>_cover; the deck's height above the centre, or the hull's) */
  define('tank_sphere', function (k, p) {
    var R = num(p.r, 5), self = k.cur, clip = p.cut ? [k.clip([0, 0, -1], 0)] : null, ex = clip ? { clip: clip } : null;
    k.ball(R, M(k, p, p.cut ? 'shell' : 'tank', ex), 0, 0, 0, { seg: 72 });
    if (p.insulation) { k.ball(R + p.insulation, k.mat('insulation', ex), 0, 0, 0, { seg: 72 }); }
    var base = num(p.base, -R * 1.25), Rs = R + (p.insulation || 0);
    if (p.dome !== false) {                             /* the dome on top: sub-part <id>_dome */
      k.sub(subId(k, p, 'dome'), { pick: true, name: 'Tank dome' });
      k.cyl('y', R * 0.14, R * 0.2, k.mat('tank'), 0, Rs + R * 0.08, 0, { seg: 24 });
      k.anchor('label', [0, Rs + R * 0.18, 0]);
      k.cur = self;
    }
    if (p.cut) {
      var lp = [], n = 48, i, a0, a1;
      for (i = 0; i < n; i++) { a0 = i / n * Math.PI * 2; a1 = (i + 1) / n * Math.PI * 2; lp.push(R * Math.cos(a0), R * Math.sin(a0), 0, R * Math.cos(a1), R * Math.sin(a1), 0); }
      k.lines(lp, '#3f4a54');
    }
    k.anchor('label', [0, Rs, 0]);
    k.sub(subId(k, p, 'skirt'), { pick: true, name: 'Skirt' });
    if (base < 0) {
      k.cyl('y', Rs, -base, k.mat('saddle', ex || { double: true }), 0, base / 2, 0, { open: true, seg: 72 });
      k.ring('y', Rs + 0.03, Math.max(0.08, R * 0.022), k.mat('steel_dark', ex), 0, 0, 0, { seg: 72 });
      k.anchor('label', p.cut ? [Rs, base * 0.45, -0.05] : [Rs * 0.71, base * 0.45, Rs * 0.71]);
    } else { k.S.warn('part "' + self.id + '": a skirt\'s "base" is its foot below the sphere\'s centre - a negative number'); }
    k.cur = self;
    if (p.drip && base < 0) {
      k.sub(subId(k, p, 'drip'), { pick: true, name: 'Drip tray' });
      var dr = typeof p.drip === 'number' ? p.drip : R * 0.45, dm = k.mat('stainless');
      k.cyl('y', dr, 0.06, dm, 0, base + 0.03, 0, { seg: 48 });
      k.ring('y', dr, 0.05, dm, 0, base + 0.08, 0, { seg: 48 });
      k.anchor('label', [dr * 0.7, base + 0.1, dr * 0.5]);
      k.cur = self;
    }
    var deck = typeof p.cover === 'number' ? p.cover : p._deck;
    if (p.cover && deck != null) {
      k.sub(subId(k, p, 'cover'), { pick: true, name: 'Tank cover' });
      var Rc = Rs + Math.max(0.4, R * 0.08), th = Math.acos(clamp(deck / Rc, -1, 1));
      k.add(new T.SphereGeometry(Rc, 64, 20, 0, Math.PI * 2, 0, th), k.mat('cover', clip ? { opacity: 0.42, clip: clip } : { opacity: 0.42 }), 0, 0, 0, { order: 2 });
      k.anchor('label', p.cut ? [Rc * 0.6, Rc * 0.8, -0.05] : [Rc * 0.45, Rc * 0.8, Rc * 0.4]);
      k.cur = self;
    }
    if (p.fill > 0) {
      k.sub(subId(k, p, 'liquid'), { pick: true });
      var Rl = R * 0.985, lv = -Rl + p.fill * 2 * Rl, prof = [], j, t0 = Math.acos(clamp(lv / Rl, -1, 1));
      for (j = 0; j <= 32; j++) { var t = Math.PI - (Math.PI - t0) * j / 32; prof.push(new T.Vector2(Rl * Math.sin(t), Rl * Math.cos(t))); }
      prof.push(new T.Vector2(0, lv));
      var g = new T.LatheGeometry(prof, 64), col = p.liquid_color || '#5fb4ea';
      k.add(g, k.mat({ color: col, rough: 0.15, metal: 0 }, clip ? { opacity: 0.6, clip: clip } : { opacity: 0.6 }), 0, 0, 0, { order: 2 });
      if (clip) {
        var sh = new T.Shape(), rl = Math.sqrt(Math.max(0, Rl * Rl - lv * lv));
        sh.moveTo(-rl, lv); sh.absarc(0, 0, Rl, Math.PI - Math.asin(clamp(lv / Rl, -1, 1)), 2 * Math.PI + Math.asin(clamp(lv / Rl, -1, 1)), false); sh.lineTo(-rl, lv);
        k.add(new T.ShapeGeometry(sh, 48), k.mat({ color: mix(col, '#2a8fd6', 0.3), rough: 0.2, metal: 0 }, { opacity: 0.78, double: true }), 0, 0, 0.005, { order: 3 });
      }
      k.anchor('label', [0, lv - R * 0.35, 0]);
      k.cur = self;
    }
  });

  /* a prismatic tank or a membrane tank (IGF course, containment systems): a chamfered section along x, the layers of
     insulation and barriers inside the inner hull seen where it is cut. size [L, H, B]; chamfer; kind "membrane"
     (default) | "semi_membrane" (the section's corners rounded, the tank a plate thicker than a membrane) | "type_b" |
     "type_a"; or layers [{id, name, t, mat}] from the inner hull inwards; cut "end" (x > 0 away, the section shows every
     layer) or "front" (z > 0 away); fill (0..1 of the height).
     "in": "<hull>" (inRelation): the hold gives the section and the length. A membrane or semi-membrane tank lines the
     inner hull with no gap - its layers <id>_ins2 (secondary insulation), _barrier2 (secondary barrier), _ins1 (primary
     insulation), _barrier1 (the membrane, or the semi-membrane's tank plate); the hull draws the inner hull. A "type_a" /
     "type_b" tank stands clear of the hull (clear, 0.8) on its chocks (<id>_chocks), insulated outside (<id>_insulation,
     <id>_shell) with its centreline bulkhead (<id>_bulkhead; "bulkhead": false leaves it out); type_b, or "drip": true, has
     the drip tray under it (<id>_drip). The section shows at the +x end, the hull's own. */
  var LAYERS = {
    membrane: [{ t: 0.45, mat: 'insulation' }, { t: 0.03, mat: 'barrier' }, { t: 0.25, mat: 'insulation' }, { t: 0.03, mat: 'membrane' }],
    semi_membrane: [{ t: 0.45, mat: 'insulation' }, { t: 0.03, mat: 'barrier' }, { t: 0.25, mat: 'insulation' }, { t: 0.08, mat: 'tank' }],
    type_b: [{ t: 0.3, mat: 'insulation' }, { t: 0.04, mat: 'tank' }],
    type_a: [{ t: 0.08, mat: 'tank' }, { t: 0.0, mat: 'insulation' }]
  };
  function holdLayers(k, p, kind) {
    var id = function (n) { return subId(k, p, n); };
    if (kind === 'membrane' || kind === 'semi_membrane') {
      return [{ id: id('ins2'), name: 'Secondary insulation', t: 0.4, mat: 'insulation' },
              { id: id('barrier2'), name: 'Secondary barrier', t: 0.05, mat: 'barrier' },
              { id: id('ins1'), name: 'Primary insulation', t: 0.25, mat: 'insulation' },
              { id: id('barrier1'), name: kind === 'membrane' ? 'Primary barrier (membrane)' : 'Primary barrier (tank)',
                t: kind === 'membrane' ? 0.05 : 0.1, mat: kind === 'membrane' ? 'membrane' : 'tank' }];
    }
    return [{ id: id('insulation'), name: 'Insulation', t: num(p.insulation, 0.25), mat: 'insulation' },
            { id: id('shell'), name: 'Tank shell', t: 0.08, mat: 'tank' }];
  }
  function octagon(hy, hz, c) {
    c = Math.max(0, Math.min(c, hy * 0.9, hz * 0.9));
    return [[-hz + c, -hy], [hz - c, -hy], [hz, -hy + c], [hz, hy - c], [hz - c, hy], [-hz + c, hy], [-hz, hy - c], [-hz, -hy + c]];
  }
  /* the same section with its corners rounded (a semi-membrane tank): a quarter circle of radius c in five points */
  function round4(hy, hz, c) {
    c = Math.max(0, Math.min(c, hy * 0.9, hz * 0.9));
    var out = [], k, cs = [[hz - c, -hy + c, -90], [hz - c, hy - c, 0], [-hz + c, hy - c, 90], [-hz + c, -hy + c, 180]];
    cs.forEach(function (q) { for (k = 0; k <= 4; k++) { var a = (q[2] + k * 22.5) * Math.PI / 180; out.push([q[0] + c * Math.cos(a), q[1] + c * Math.sin(a)]); } });
    return out;
  }
  function shapeOf(pts, hole) {
    var s = new T.Shape(), i;
    s.moveTo(pts[0][0], pts[0][1]);
    for (i = 1; i < pts.length; i++) { s.lineTo(pts[i][0], pts[i][1]); }
    s.lineTo(pts[0][0], pts[0][1]);
    if (hole) { var h = new T.Path(); h.moveTo(hole[0][0], hole[0][1]); for (i = hole.length - 1; i >= 0; i--) { h.lineTo(hole[i][0], hole[i][1]); } s.holes.push(h); }
    return s;
  }
  function below(pts, lv) {                         /* the polygon cut at a level: what lies under it */
    var out = [], i, a, b, n = pts.length;
    for (i = 0; i < n; i++) {
      a = pts[i]; b = pts[(i + 1) % n];
      if (a[1] <= lv) { out.push(a); }
      if ((a[1] < lv) !== (b[1] < lv)) { var t = (lv - a[1]) / (b[1] - a[1]); out.push([a[0] + (b[0] - a[0]) * t, lv]); }
    }
    return out;
  }
  define('tank_prism', function (k, p) {
    var s = p.size || [20, 12, 14], L = s[0], hy = s[1] / 2, hz = s[2] / 2, c = num(p.chamfer, Math.min(hy, hz) * 0.3), self = k.cur;
    var hold = p._hold, kind = p.kind || 'membrane', lining = kind === 'membrane' || kind === 'semi_membrane';
    var layers = p.layers || LAYERS[kind] || LAYERS.membrane, prof, hullT = num(p.hull, 0.2);
    if (hold) {
      var sect = hold.sec.pts, rc = num(p.chamfer, 2.2), clear = lining ? 0 : num(p.clear, 0.8);
      sect = inset(sect, clear);
      L = hold.x1 - hold.x0 - 2 * clear;
      prof = function (off) { var q = inset(sect, off); return kind === 'semi_membrane' ? rounded(q, Math.max(0.3, rc - off)) : q; };
      hullT = 0;
      if (!p.layers) { layers = holdLayers(k, p, kind); }
    } else {
      var octo = kind === 'semi_membrane' ? round4 : octagon;
      prof = function (off) { return octo(hy - off, hz - off, c - off * 0.414); };
    }
    var cut = p.cut === undefined ? 'end' : p.cut, clip = null;
    if (cut === 'end' && !hold) { clip = [k.clip([-1, 0, 0], 0)]; } else if (cut === 'front' || cut === true) { clip = [k.clip([0, 0, -1], 0)]; }
    var ex = clip ? { clip: clip } : null, off = 0, i, endX = hold ? L / 2 : 0, endCut = cut === 'end';
    function extr(outer, inner, m, len) {
      var g = new T.ExtrudeGeometry(shapeOf(outer, inner), { depth: len, bevelEnabled: false, curveSegments: 4 });
      g.rotateY(-Math.PI / 2); g.translate(len / 2, 0, 0);
      return k.add(g, m, 0, 0, 0);
    }
    function cap(outer, inner, m, x) {                   /* the layer's face where it is cut, or the tank's end */
      var g = new T.ShapeGeometry(shapeOf(outer, inner));
      g.rotateY(Math.PI / 2);
      return k.add(g, m, x, 0, 0, { cast: false });
    }
    /* the top of a section: its height and how far across its flat top runs */
    function topOf(q) {
      var y = spanY(q)[1], z = 0;
      q.forEach(function (v) { if (v[1] > y - 1e-6) { z = Math.max(z, Math.abs(v[0])); } });
      return [y, z];
    }
    var outer = prof(0), t0 = topOf(outer);
    if (hullT > 0) {
      var inner = prof(hullT), hm = M(k, p, 'steel', ex);
      extr(outer, inner, hm, L);
      cap(outer, null, k.mat('steel'), -L / 2);
      if (endCut) { cap(outer, inner, k.mat('steel_dark'), 0.003); }
      off = hullT;
    }
    k.anchor('label', [hold ? endX : 0, t0[0], hold ? -t0[1] * 0.5 : 0]);
    layers.forEach(function (ly, li) {
      if (!(ly.t > 0)) { return; }
      if (ly.id) { k.sub(ly.id, { pick: true, name: ly.name || '' }); }
      var o = prof(off), n2 = prof(off + ly.t), lenL = L - 2 * off, m = k.mat(ly.mat || 'insulation', ex), tp = topOf(o);
      extr(o, n2, m, lenL);
      if (!hold) { cap(o, n2, k.mat(ly.mat || 'insulation'), -lenL / 2); }
      if (endCut && !hold) { cap(o, n2, k.mat(ly.mat || 'insulation'), 0.004 + li * 0.0005); }
      /* each layer's point on the section's top, a step further across than the one outside it: no two in one column */
      k.anchor('label', [endCut ? (hold ? lenL / 2 : 0) : -lenL / 4, tp[0] - ly.t / 2, endCut ? tp[1] * Math.min(0.85, 0.2 + 0.14 * li) : 0]);
      off += ly.t;
      k.cur = self;
    });
    var inn = prof(off), sy = spanY(inn), lenIn = L - 2 * off;
    if (hold) { cap(inn, null, k.mat((layers[layers.length - 1] || {}).mat || 'tank'), -lenIn / 2); }   /* the tank's far end, seen from inside */
    if (hold && !lining) {
      if (p.bulkhead !== false) {
        k.sub(subId(k, p, 'bulkhead'), { pick: true, name: 'Centreline bulkhead' });
        k.box(lenIn, sy[1] - sy[0], 0.05, k.mat('steel_mid', ex), 0, (sy[0] + sy[1]) / 2, -0.03);
        k.anchor('label', [endCut ? lenIn / 2 : -lenIn / 4, sy[0] + (sy[1] - sy[0]) * 0.55, -0.03]);
        k.cur = self;
      }
      var ob = spanY(outer)[0], fl = hold.sec.fl, chH = ob - fl, bw = 0;
      outer.forEach(function (v) { if (v[1] < ob + 1e-6) { bw = Math.max(bw, Math.abs(v[0])); } });
      if (kind === 'type_b' || p.drip) {
        k.sub(subId(k, p, 'drip'), { pick: true, name: 'Drip tray' });
        k.box(L * 0.92, 0.06, bw * 1.9, k.mat('stainless'), 0, fl + 0.03, 0, { cast: false });
        k.anchor('label', [endCut ? L * 0.4 : -L / 4, fl + 0.06, bw * 0.9]);
        k.cur = self;
      }
      if (chH > 0.05) {
        k.sub(subId(k, p, 'chocks'), { pick: true, name: 'Chocks' });
        var nx = Math.max(2, Math.round(L / 4)), list = [], ci, cz;
        for (ci = 0; ci < nx; ci++) { for (cz = -1; cz <= 1; cz++) { list.push([-L / 2 + L * (ci + 0.5) / nx, fl + chH / 2, cz * bw * 0.65]); } }
        k.many(new T.BoxGeometry(0.5, chH, 0.7), k.mat('wood'), list);
        /* the point on the last chock's +x face, halfway up: on the chock, not on the tank's bottom edge above it */
        k.anchor('label', [list[list.length - 1][0] + 0.25, fl + chH * 0.5, list[list.length - 1][2]]);
        k.cur = self;
      }
    }
    if (p.fill > 0) {
      k.sub(subId(k, p, 'liquid'), { pick: true });
      var lv = sy[0] + p.fill * (sy[1] - sy[0]), poly = below(inn, lv), lenQ = lenIn - 0.02;
      var col = p.liquid_color || '#5fb4ea';
      extr(poly, null, k.mat({ color: col, rough: 0.15, metal: 0 }, clip ? { opacity: 0.6, clip: clip } : { opacity: 0.6 }), lenQ).renderOrder = 2;
      if (endCut && !hold) { cap(poly, null, k.mat({ color: mix(col, '#2a8fd6', 0.3), rough: 0.2, metal: 0 }, { opacity: 0.8, double: true }), 0.01).renderOrder = 3; }
      k.anchor('label', [endCut ? (hold ? lenQ / 2 : 0) : -L / 4, lv - (sy[1] - sy[0]) * 0.15, 0]);
      k.cur = self;
    }
    if (clip || hold) {
      var lp = [], j, ends = hold ? [-L / 2, L / 2] : [0];
      if (endCut || hold) {
        ends.forEach(function (ex0) {
          for (j = 0; j < outer.length; j++) {
            var a = outer[j], b = outer[(j + 1) % outer.length];
            lp.push(ex0, a[1], a[0], ex0, b[1], b[0]);
          }
        });
      }
      if (lp.length) { k.lines(lp, '#2a3640'); }
    }
  });

  /* -------------------------------------------------------------------- piping */
  /* a pipe run through points (in the part's coordinates): straight legs, a ball at each bend. r (0.15); mat "pipe" |
     "gas" | "cold" | "steel"; flanges: "ends" or [point index]; bands: spacing of yellow ID bands (m) */
  define('pipe', function (k, p) {
    var pts = p.path || [[0, 0, 0], [2, 0, 0]], r = num(p.r, 0.15), m = M(k, p, 'pipe'), fm = k.mat('flange'), i;
    k.run(pts, r, m, { seg: 20 });
    var fl = p.flanges === 'ends' ? [0, pts.length - 1] : (p.flanges || []);
    fl.forEach(function (ix) {
      var a = pts[ix], b = pts[ix === 0 ? 1 : ix - 1], dv = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], L0 = Math.sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]) || 1;
      var e = 0.06 / L0;
      k.seg([a[0] - dv[0] * e * 0.2, a[1] - dv[1] * e * 0.2, a[2] - dv[2] * e * 0.2], [a[0] + dv[0] * e, a[1] + dv[1] * e, a[2] + dv[2] * e], r * 1.7, fm, { seg: 24 });
    });
    if (p.bands) {
      var bm = k.mat('yellow');
      for (i = 0; i < pts.length - 1; i++) {
        var a2 = pts[i], b2 = pts[i + 1], dx = b2[0] - a2[0], dy = b2[1] - a2[1], dz = b2[2] - a2[2], L1 = Math.sqrt(dx * dx + dy * dy + dz * dz), sN;
        for (sN = p.bands / 2; sN < L1 - 0.1; sN += p.bands) {
          var f0 = (sN - 0.06) / L1, f1 = (sN + 0.06) / L1;
          k.seg([a2[0] + dx * f0, a2[1] + dy * f0, a2[2] + dz * f0], [a2[0] + dx * f1, a2[1] + dy * f1, a2[2] + dz * f1], r + 0.008, bm, { seg: 20 });
        }
      }
    }
    if (p.end_cone) {                                   /* "it goes on" - a cone at the last point (IGF M02: to the engine room) */
      var e0 = pts[pts.length - 1], e1 = pts[pts.length - 2], dd = [e0[0] - e1[0], e0[1] - e1[1], e0[2] - e1[2]];
      var Ld = Math.sqrt(dd[0] * dd[0] + dd[1] * dd[1] + dd[2] * dd[2]) || 1, h = r * 5;
      k.cone([e0[0] + dd[0] / Ld * h, e0[1] + dd[1] / Ld * h, e0[2] + dd[2] / Ld * h], dd, r * 2.1, h, m);
    }
    var mid = pts[Math.floor((pts.length - 1) / 2)], nx = pts[Math.floor((pts.length - 1) / 2) + 1] || mid;
    k.anchor('label', [(mid[0] + nx[0]) / 2, (mid[1] + nx[1]) / 2 + r, (mid[2] + nx[2]) / 2]);
  });

  /* a double-walled gas pipe (IGF M01): the yellow inner pipe, the see-through outer pipe (drawn thicker than true so
     the annulus shows), spacers in the annulus, collars, supports, a bulkhead gland. Along x; at = its middle.
     len, r_in, r_out; collars [x]; spacers [x]; supports [x] down to base (y); glands [x]. State "<id>.cut": the front
     half of the outer pipe is sliced away; while cut, the sub-parts "inner", "annulus", "outer" are tapped and
     labelled alone - closed, a tap on any of them is the whole pipe. */
  define('pipe_dw', function (k, p) {
    var L = num(p.len, 8), ri = num(p.r_in, 0.26), ro = num(p.r_out, 0.42), self = k.cur, id = self.id;
    var pl = k.clip([0, 0, -1], ro + 0.1), clip = [pl], need = id + '.cut > 0.5';
    k.sub(subId(k, p, 'inner'), { pick: true, need: need });
    k.cyl('x', ri, L, k.mat(p.gas || 'gas'), 0, 0, 0, { seg: 28 });
    k.anchor('label', [-L * 0.4, 0, 0]);
    k.cur = self;
    k.sub(subId(k, p, 'outer'), { pick: true, need: need });
    var om = k.mat('glass', { opacity: 0.30, clip: clip });
    k.cyl('x', ro, L, om, 0, 0, 0, { open: true, seg: 48, order: 4, recv: false });
    var em = k.mat({ color: '#1b2733', rough: 0.6, metal: 0.2 }), edges = [k.cyl('x', 0.03, L, em, 0, ro, 0, { seg: 6, keep: true, order: 5 }),
      k.cyl('x', 0.03, L, em, 0, -ro, 0, { seg: 6, keep: true, order: 5 })];
    k.anchor('label', [L * 0.25, -ro, 0]);
    var outerPart = k.cur, axisP = null, axisD = null;
    outerPart.resolve = function (hit, ray) {      /* the inner half of the band between the walls is the annulus */
      if (!axisP) {
        var g = hit.object.parent || k.S.root; g.updateMatrixWorld(true);
        axisP = new T.Vector3(); axisD = new T.Vector3(1, 0, 0);
        axisP.setFromMatrixPosition(outerG.matrixWorld); axisD.transformDirection(outerG.matrixWorld);
      }
      var n = new T.Vector3().crossVectors(ray.ray.direction, axisD);
      if (n.lengthSq() > 1e-9) {
        n.normalize();
        if (Math.abs(n.dot(ray.ray.origin.clone().sub(axisP))) < (ri + ro) / 2) { return subId(k, p, 'annulus'); }
      }
      return outerPart.id;
    };
    var outerG = k.g;
    k.cur = self;
    var cm = k.mat('flange', { clip: clip }), list = (p.collars || []).map(function (x) { return [x, 0, 0]; });
    var cg = new T.CylinderGeometry(ro + 0.07, ro + 0.07, 0.22, 36, 1, true); cg.rotateZ(Math.PI / 2);
    if (list.length) { k.many(cg, cm, list); }
    (p.glands || []).forEach(function (x) {
      k.cyl('x', ro + 0.34, 0.14, k.mat({ color: '#5f6b76', rough: 0.5, metal: 0.6 }, { clip: clip }), x, 0, 0, { seg: 40, order: 4 });
      k.cyl('x', ro + 0.07, 0.42, cm, x, 0, 0, { seg: 36, open: true, order: 4 });
    });
    k.sub(subId(k, p, 'annulus'), { pick: true, need: need });
    var sp = [], rm = (ro + ri) / 2, j, a;
    (p.spacers || []).forEach(function (x, si) {
      for (j = 0; j < 3; j++) { a = j * (2 * Math.PI / 3) + (si % 2) * 0.5; sp.push({ at: [x, rm * Math.cos(a), rm * Math.sin(a)], rx: a }); }
    });
    if (sp.length) { k.many(new T.BoxGeometry(0.14, ro - ri + 0.02, 0.14), k.mat({ color: '#445059', rough: 0.6, metal: 0.3 }, { clip: clip }), sp); }
    k.anchor('label', [-L * 0.1, -rm, 0]);
    k.cur = self;
    if (p.supports) {
      var base = num(p.base, -ro - 2), h = -ro - 0.12 - base, sm = k.mat({ color: '#6f7b86', rough: 0.6, metal: 0.4 });
      k.many(new T.BoxGeometry(0.26, h, 0.26), sm, p.supports.map(function (x) { return [x, base + h / 2, 0]; }));
      k.many(new T.BoxGeometry(0.5, 0.14, 0.9), sm, p.supports.map(function (x) { return [x, -ro - 0.07, 0]; }));
    }
    k.anchor('label', [-L * 0.25, ro, 0]);
    k.state(id + '.cut', 0, function (v) {
      pl.set((ro + 0.1) * (1 - v));
      om.opacity = 0.30 + 0.28 * v;
      edges.forEach(function (e) { e.visible = v > 0.97; });
    });
  });

  /* a valve (IGF M01-M03): body, flanges, bonnet, stem and a handwheel - or, "actuator": true, a remote-operated valve's
     actuator on a yoke with its solenoid box. at = on the pipe axis; axis "x" | "z"; wheel "red" | "grey"; body (r 0.34,
     drawn for a pipe of r ~0.25 - scale it); state "<id>.shut" turns a grey wheel red */
  define('valve', function (k, p) {
    var z = p.axis === 'z', dark = k.mat('steel_dark'), mid = k.mat('steel_mid'), self = k.cur;
    if (p.kind === 'relief') {                          /* a relief valve (IGF M15): inlet below, outlet to the side, a bonnet */
      var bm = M(k, p, 'steel_mid'), lift = num(p.lift, 0.16);    /* and spring housing that lift ("<id>.open") */
      k.cyl('y', 0.18, 0.5, bm, 0, 0.25, 0, { seg: 24 });
      k.cyl('y', 0.26, 0.08, k.mat('flange'), 0, 0.02, 0, { seg: 28 });
      k.cyl(z ? 'z' : 'x', 0.13, 0.5, bm, z ? 0 : 0.3, 0.32, z ? 0.3 : 0, { seg: 20 });
      k.cyl(z ? 'z' : 'x', 0.2, 0.06, k.mat('flange'), z ? 0 : 0.56, 0.32, z ? 0.56 : 0, { seg: 24 });
      var top = k.push([0, 0, 0]);
      k.cyl('y', 0.16, 0.18, dark, 0, 0.6, 0, { seg: 24, keep: true });
      k.cyl('y', 0.11, 0.55, k.mat('red'), 0, 0.96, 0, { seg: 20, keep: true });
      k.cyl('y', 0.05, 0.12, dark, 0, 1.3, 0, { seg: 12, keep: true });
      k.pop();
      k.anchor('label', [0, 1.36, 0]);
      k.state(self.id + '.open', 0, function (v) { top.position.y = lift * v; });
      return;
    }
    var bg = new T.CylinderGeometry(0.34, 0.34, 0.9, 20); bg.rotateZ(Math.PI / 2); if (z) { bg.rotateY(Math.PI / 2); }
    k.add(bg, M(k, p, 'steel_dark'), 0, 0, 0);
    [-0.5, 0.5].forEach(function (o) {
      var fg = new T.CylinderGeometry(0.44, 0.44, 0.1, 24); fg.rotateZ(Math.PI / 2); if (z) { fg.rotateY(Math.PI / 2); }
      k.add(fg, mid, z ? 0 : o, 0, z ? o : 0);
    });
    k.cyl('y', 0.2, 0.55, dark, 0, 0.45, 0, { seg: 16 });
    if (p.actuator) {
      k.cyl('y', 0.11, 0.5, mid, 0, 0.95, 0, { seg: 12 });
      k.box(0.7, 0.06, 0.5, mid, 0, 1.22, 0);
      var act = k.mat({ color: '#9aa6b1', rough: 0.45, metal: 0.5 });
      k.cyl('y', 0.3, 0.7, act, 0, 1.6, 0, { seg: 28 });
      k.add(new T.SphereGeometry(0.3, 24, 8, 0, Math.PI * 2, 0, Math.PI / 2), act, 0, 1.95, 0);
      k.box(0.3, 0.34, 0.24, k.mat({ color: '#7c8893', rough: 0.55, metal: 0.45 }), 0.5, 1.45, 0);
      k.anchor('label', [0, 2.25, 0]);
      var a0 = act.color.clone(), ar = k.col('#d0342c');      /* shut: the actuator shows red, as a shut valve's wheel */
      k.state(self.id + '.shut', 0, function (v) { act.color.copy(a0).lerp(ar, v * 0.8); if (act.userData.c0) { act.userData.c0.copy(act.color); } });
    } else {
      k.cyl('y', 0.05, 0.75, mid, 0, 0.95, 0, { seg: 8 });
      var grey = p.wheel === 'grey', wm = k.mat(grey ? { color: '#8d98a3', rough: 0.5, metal: 0.55 } : 'red');
      k.ring('y', 0.34, 0.05, wm, 0, 1.3, 0, { seg: 24 });
      k.box(0.68, 0.05, 0.05, wm, 0, 1.3, 0); k.box(0.05, 0.05, 0.68, wm, 0, 1.3, 0);
      k.anchor('label', [0, 1.36, 0]);
      if (grey) {
        var g0 = wm.color.clone(), rc = k.col('#d0342c');
        k.state(self.id + '.shut', 0, function (v) { wm.color.copy(g0).lerp(rc, v); if (wm.userData.c0) { wm.userData.c0.copy(wm.color); } });
      }
    }
  });

  /* a flange pair with a gasket and a ring of bolts. at = on the pipe axis; axis "x" | "y" | "z"; r (the pipe's) */
  define('flange', function (k, p) {
    var r = num(p.r, 0.15), ax = p.axis || 'x', fm = M(k, p, 'flange'), n = num(p.bolts, 8), i, a, list = [];
    var t = Math.max(0.04, r * 0.35), R = r * 1.9;
    function at(o, u, v) { return ax === 'x' ? [o, u, v] : ax === 'y' ? [u, o, v] : [u, v, o]; }
    var q1 = at(-t * 0.55, 0, 0), q2 = at(t * 0.55, 0, 0);
    k.cyl(ax, R, t, fm, q1[0], q1[1], q1[2], { seg: 32 });
    k.cyl(ax, R, t, fm, q2[0], q2[1], q2[2], { seg: 32 });
    k.cyl(ax, R * 0.96, t * 0.12, k.mat('steel_black'), 0, 0, 0, { seg: 32 });
    for (i = 0; i < n; i++) { a = i * Math.PI * 2 / n; list.push(at(0, Math.cos(a) * R * 0.78, Math.sin(a) * R * 0.78)); }
    var bg = new T.CylinderGeometry(r * 0.13, r * 0.13, t * 2.9, 8);
    if (ax === 'x') { bg.rotateZ(Math.PI / 2); } else if (ax === 'z') { bg.rotateX(Math.PI / 2); }
    k.many(bg, k.mat('steel_dark'), list);
    var top = at(0, R, 0); k.anchor('label', top);
  });

  /* a coupling at a bunker connection (IGF M03): "dry" - a dry-disconnect coupling with its clamp collar and locking
     lever; "breakaway" - two halves joined at a break ring with shear bolts. at = on the pipe axis; axis "z" (default)
     or "x"; r (the pipe's, 0.11) */
  define('coupling', function (k, p) {
    var f = num(p.r, 0.11) / 0.11, xax = p.axis === 'x', dark = k.mat('steel_dark'), fl = k.mat('flange');
    k.push([0, 0, 0], xax ? 90 : 0, f);
    if (p.kind === 'breakaway') {
      var bm = M(k, p, null);
      if (!p.mat && !p.color) { bm = k.mat({ color: '#a2adb7', rough: 0.4, metal: 0.65 }); }
      k.cyl('z', 0.17, 0.5, bm, 0, 0, 0, { seg: 28 });
      k.cyl('z', 0.19, 0.08, k.mat({ color: '#3b444d', rough: 0.55, metal: 0.5 }), 0, 0, 0, { seg: 32 });
      k.cyl('z', 0.215, 0.05, fl, 0, 0, -0.25, { seg: 32 }); k.cyl('z', 0.215, 0.05, fl, 0, 0, 0.25, { seg: 32 });
      var i, a, list = [];
      for (i = 0; i < 4; i++) { a = i * Math.PI / 2 + Math.PI / 4; list.push([Math.cos(a) * 0.19, Math.sin(a) * 0.19, 0]); }
      var g = new T.CylinderGeometry(0.016, 0.016, 0.16, 8); g.rotateX(Math.PI / 2);
      k.many(g, dark, list);
      k.anchor('label', [0, 0.19, 0]);
    } else {
      var dm = M(k, p, null);
      if (!p.mat && !p.color) { dm = k.mat({ color: '#7f8c98', rough: 0.4, metal: 0.7 }); }
      k.cyl('z', 0.165, 0.58, dm, 0, 0, 0, { seg: 28 });
      k.cyl('z', 0.225, 0.13, k.mat({ color: '#5b6670', rough: 0.45, metal: 0.65 }), 0, 0, 0.02, { seg: 32 });
      k.cyl('z', 0.2, 0.05, fl, 0, 0, 0.3, { seg: 32 });
      k.box(0.06, 0.2, 0.1, dark, 0, 0.3, 0.02);
      k.ball(0.05, dark, 0, 0.42, 0.02);
      k.box(0.1, 0.12, 0.08, dark, 0.22, 0.02, 0.02);
      k.anchor('label', [0, 0.45, 0.02]);
    }
    k.pop();
  });

  /* a hose through points (a bunker hose over the side, a fire hose): r (0.13); path in the part's coordinates.
     "from" / "to" (or a point of "path"): "<id>.<port>" - the hose starts / ends on that port, leaving it straight, with a
     hose coupling there (ends "coupling"; a free end has a flange, or "ends": "coupling"); path is then only the bends.
     Ports "start" and "end". State "<id>.on" (when the spec names it): arrows run along its top, the way it flows (color,
     water blue) - outside the hose, where the class sees them */
  define('hose', function (k, p) {
    var r = num(p.r, 0.13), lead = Math.max(r * 3, 0.08), pts = [], i, joined = false;
    function add(x) {
      if (x && !Array.isArray(x) && x.at) { joined = true; return { at: k.local(x.at), dir: k.localDir(x.dir) }; }
      return Array.isArray(x) && x.length === 3 ? { at: x } : null;
    }
    var mid = (p._path || p.path || (p.from || p.to ? [] : [[0, 0, 0], [0, 0, 1], [0, -1, 1.3]])).map(add).filter(Boolean);
    if (p._from) { mid.unshift(add(p._from)); }
    if (p._to) { mid.push(add(p._to)); }
    mid.forEach(function (e, j) {
      var a = e.at, d = e.dir, off = d ? [a[0] + d[0] * lead, a[1] + d[1] * lead, a[2] + d[2] * lead] : null;
      if (d && j === mid.length - 1 && j > 0) { pts.push(off); }
      pts.push(a);
      if (d && j === 0) { pts.push(off); }
    });
    if (pts.length < 2) { pts = [[0, 0, 0], [0, 0, 1]]; }
    var curve = k.tube(pts, r, M(k, p, 'rubber'), { seg: 14 }).geometry.parameters.path;
    var a = pts[pts.length - 1], b = pts[pts.length - 2], dv = [a[0] - b[0], a[1] - b[1], a[2] - b[2]], s0 = [pts[0][0] - pts[1][0], pts[0][1] - pts[1][1], pts[0][2] - pts[1][2]];
    if (joined || p.ends === 'coupling') {
      couplingAt(k, pts[0], s0, r * 1.45, alloy(k));
      couplingAt(k, a, dv, r * 1.45, alloy(k));
    } else {
      var L0 = Math.sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]) || 1, e = 0.03 / L0;
      k.seg([a[0] - dv[0] * e, a[1] - dv[1] * e, a[2] - dv[2] * e], [a[0] + dv[0] * e, a[1] + dv[1] * e, a[2] + dv[2] * e], r * 1.55, k.mat('flange'), { seg: 28 });
    }
    k.port('start', pts[0], unit(s0));
    k.port('end', a, unit(dv));
    var m = curve.getPointAt(0.5);
    k.anchor('label', [m.x, m.y + r, m.z]);
    if (JSON.stringify(k.S.spec.steps || []).concat(JSON.stringify(k.S.spec.controls || []), JSON.stringify(k.S.spec.states || {}))
        .indexOf('"' + k.cur.id + '.on"') >= 0) {
      /* the arrows ride on the hose's top: each point lifted by the hose's radius, square to its run */
      var n = Math.max(12, Math.round(curve.getLength() / (r * 2))), top = [], up = new T.Vector3(0, 1, 0);
      for (i = 0; i <= n; i++) {
        var u = i / n, P0 = curve.getPointAt(u), tg = curve.getTangentAt(u), nv = up.clone().addScaledVector(tg, -tg.dot(up));
        if (nv.lengthSq() < 1e-6) { nv.set(0, 0, 1); }
        nv.normalize().multiplyScalar(r * 1.25);
        top.push([P0.x + nv.x, P0.y + nv.y, P0.z + nv.z]);
      }
      flowArrows(k, top, k.cur.id, { color: p.color || WATER, r: r * 0.6, spacing: Math.max(r * 6, 0.12), speed: num(p.speed, 0.5) });
    }
  });

  function unit(v) { var L = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) || 1; return [v[0] / L, v[1] / L, v[2] / L]; }
  /* light alloy: hose couplings, an inductor's body */
  function alloy(k) { return k.mat({ color: '#c2cad1', rough: 0.32, metal: 0.75 }); }
  /* a hose coupling (instantaneous, Storz-like) on a joint at e, its face square to dir (pointing away from the hose); rc its
     radius: the body, a collar at the face and two lugs */
  function couplingAt(k, e, dir, rc, m) {
    var d = unit(dir), len = rc * 1.15, b = [e[0] - d[0] * len, e[1] - d[1] * len, e[2] - d[2] * len];
    var f = [e[0] - d[0] * len * 0.3, e[1] - d[1] * len * 0.3, e[2] - d[2] * len * 0.3];
    k.seg(b, e, rc, m, { seg: 24 });
    k.seg(f, e, rc * 1.12, m, { seg: 24 });
    var u = Math.abs(d[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0], s = [d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0]];
    s = unit(s);
    [-1, 1].forEach(function (sg) { k.ball(rc * 0.3, k.mat('steel_dark'), f[0] + s[0] * rc * 1.1 * sg, f[1] + s[1] * rc * 1.1 * sg, f[2] + s[2] * rc * 1.1 * sg, { seg: 10 }); });
  }

  /* a vent mast (IGF M07, M15): the mast, a hood at the outlet, flanges, yellow bands, stays. at = its foot; h (height
     above the foot), r (0.2) */
  define('vent_mast', function (k, p) {
    var h = num(p.h, 8), r = num(p.r, 0.2), m = M(k, p, 'pipe'), fm = k.mat('flange'), i;
    k.cyl('y', r, h, m, 0, h / 2, 0, { seg: 24 });
    k.cyl('y', r * 2.4, 0.14, fm, 0, 0.07, 0, { seg: 28 });
    for (i = 1; i < h / 3; i++) { k.cyl('y', r * 1.5, 0.06, fm, 0, i * 3, 0, { seg: 24 }); }
    k.cyl('y', r + 0.008, 0.25, k.mat('yellow'), 0, h * 0.35, 0, { seg: 24 });
    k.cyl('y', r * 1.2, 0.3, fm, 0, h + 0.15, 0, { seg: 24, open: false });
    k.add(new T.ConeGeometry(r * 2.2, r * 1.6, 24, 1, true), k.mat('steel_mid', { double: true }), 0, h + 0.55, 0);
    if (p.stays !== false) {
      var sm = k.mat('steel_dark'), R = h * 0.32;
      for (i = 0; i < 3; i++) { var a = i * Math.PI * 2 / 3 + 0.5; k.seg([0, h * 0.62, 0], [Math.cos(a) * R, 0.02, Math.sin(a) * R], 0.018, sm, { seg: 6 }); }
    }
    k.anchor('label', [0, h + 0.7, 0]);
  });

  /* -------------------------------------------------------------------- equipment */
  /* a horizontal vessel on two legs (a vaporiser, a heater; IGF M01): at = the axis's centre (along x); r, len; base
     (the floor's y, -r - 0.5) */
  define('vessel', function (k, p) {
    var r = num(p.r, 0.85), L = num(p.len, 3.4), base = num(p.base, -r - 0.5), fm = k.mat('steel_mid'), m = M(k, p, null);
    if (!p.mat && !p.color) { m = k.mat({ color: '#b8c3cc', rough: 0.38, metal: 0.55 }); }
    k.cyl('x', r, L, m, 0, 0, 0, { seg: 40 });
    k.cyl('x', r * 1.12, 0.14, fm, -L / 2, 0, 0, { seg: 40 }); k.cyl('x', r * 1.12, 0.14, fm, L / 2, 0, 0, { seg: 40 });
    var g = new T.SphereGeometry(r, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2); g.scale(1, 0.45, 1);
    var g2 = g.clone(); g.rotateZ(Math.PI / 2); g2.rotateZ(-Math.PI / 2);
    k.add(g, m, -L / 2 - 0.07, 0, 0); k.add(g2, m, L / 2 + 0.07, 0, 0);
    var lh = -r * 0.6 - base, dark = k.mat('steel_dark');
    k.box(0.4, lh, r * 1.6, dark, -L * 0.27, base + lh / 2, 0); k.box(0.4, lh, r * 1.6, dark, L * 0.27, base + lh / 2, 0);
    k.anchor('label', [0, r, 0]);
  });

  /* a cabinet (a gas valve unit, a control panel; IGF M01): size [w, h, d], at = the base's centre, its door facing +z;
     band: true an amber band near the top; screen: true a small display */
  define('cabinet', function (k, p) {
    var s = p.size || [1.6, 2.2, 1], W = s[0], H = s[1], D = s[2], m = M(k, p, 'cabinet');
    k.box(W, H, D, m, 0, H / 2, 0);
    if (p.band !== false) { k.box(W + 0.02, Math.min(0.3, H * 0.06), D + 0.02, k.mat('amber'), 0, H * 0.86, 0, { cast: false }); }
    k.box(W * 0.8, H * 0.55, 0.04, k.mat('panel'), 0, H * 0.43, D / 2 + 0.02, { cast: false });
    if (p.screen) { k.box(W * 0.3, W * 0.22, 0.04, k.mat('screen'), 0, H * 0.72, D / 2 + 0.03, { cast: false }); }
    k.anchor('label', [0, H, 0]);
  });

  /* a dual-fuel engine (IGF M01, M05, M09): foundation, crankcase, sump, flywheel housing, cylinder head covers, charge
     air receiver, turbocharger and its exhaust. at = the foundation's underside, centre; n cylinders (6); exhaust: the
     height the exhaust pipe goes up to above the foundation (0 = none); gas_rail: true the gas valve block with an amber
     band on the +z side */
  define('engine', function (k, p) {
    var n = num(p.n, 6), L = 1.25 * n + 0.5, x0 = -L / 2, i, heads = [], tops = [];
    var blue = M(k, p, 'engine');
    k.box(L + 1.6, 0.7, 4.0, k.mat('foundation'), 0.2, 0.35, 0);
    k.box(L, 2.2, 2.6, blue, 0, 1.9, 0);
    k.box(L, 0.35, 2.7, k.mat('engine_dark'), 0, 0.85, 0);
    k.box(1.1, 2.3, 2.5, k.mat({ color: '#2a4a68', rough: 0.5, metal: 0.4 }), x0 - 0.5, 2.05, 0);
    for (i = 0; i < n; i++) { heads.push([x0 + 0.8 + i * 1.25, 3.5, 0]); tops.push([x0 + 0.8 + i * 1.25, 4.12, 0]); }
    k.many(new T.BoxGeometry(0.95, 0.95, 1.5), k.mat('cover'), heads);
    k.many(new T.BoxGeometry(0.55, 0.3, 0.7), k.mat({ color: '#8fa0ae', rough: 0.5, metal: 0.5 }), tops);
    k.cyl('x', 0.42, L - 0.6, k.mat({ color: '#b0bac3', rough: 0.4, metal: 0.6 }), 0, 2.7, -1.7, { seg: 24 });
    k.cyl('x', 0.65, 1.5, k.mat({ color: '#9aa6b0', rough: 0.4, metal: 0.6 }), L / 2 + 0.7, 3.5, -0.2, { seg: 28 });
    k.box(1.2, 1.7, 2.4, blue, L / 2 + 0.7, 1.25, 0);
    var ex = num(p.exhaust, 0);
    if (ex > 4.1) { k.cyl('y', 0.4, ex - 4.1, k.mat({ color: '#a7b0b8', rough: 0.5, metal: 0.4 }), L / 2 + 1.2, (4.1 + ex) / 2, -0.2, { seg: 24 }); }
    if (p.gas_rail) {
      k.box(1.2, 2.8, 1.7, k.mat({ color: '#cfd5db', rough: 0.45, metal: 0.25 }), L / 2 - 1.3, 3.5, 2.15);
      k.box(1.22, 0.3, 1.72, k.mat('amber'), L / 2 - 1.3, 2.6, 2.15, { cast: false });
    }
    k.anchor('label', [0, 4.3, 0]);
  });

  /* a pump with its motor on a base (at = the base's centre on the floor); size (the volute's radius, 0.4) */
  define('pump', function (k, p) {
    var r = num(p.r, 0.4), m = M(k, p, 'engine');
    k.box(r * 6, 0.15, r * 2.6, k.mat('foundation'), r * 1.5, 0.075, 0);
    k.cyl('z', r, r * 0.9, m, 0, r + 0.25, 0, { seg: 32 });
    k.cyl('y', r * 0.32, r * 1.2, k.mat('pipe'), 0, r * 2 + 0.25 + r * 0.3, 0, { seg: 20 });
    k.cyl('x', r * 0.22, r * 1.2, k.mat('steel_dark'), r * 1.0, r + 0.25, 0, { seg: 16 });
    k.cyl('x', r * 0.85, r * 2.4, k.mat({ color: '#4f6f8f', rough: 0.5, metal: 0.4 }), r * 2.8, r * 0.85 + 0.15, 0, { seg: 32 });
    k.anchor('label', [0, r * 2.8 + 0.25, 0]);
  });

  /* a stainless drip tray on insulating pads (IGF M03): size [w, d], at = the base's centre on the deck; wall height */
  define('drip_tray', function (k, p) {
    var s = p.size || [2.2, 3.6], W = s[0], D = s[1], wh = num(p.wall, 0.2), y0 = 0.07, t = 0.04, tm = M(k, p, 'stainless');
    var pads = [], ix, iz;
    for (ix = -1; ix <= 1; ix += 2) { for (iz = -1; iz <= 1; iz++) { pads.push([ix * (W / 2 - 0.3), y0 / 2, iz * (D / 2 - 0.4)]); } }
    k.many(new T.BoxGeometry(0.32, y0, 0.32), k.mat({ color: '#d9cdb0', rough: 0.9, metal: 0 }), pads);
    k.box(W, 0.03, D, tm, 0, y0 + 0.015, 0);
    k.box(W, wh, t, tm, 0, y0 + wh / 2, -D / 2 + t / 2); k.box(W, wh, t, tm, 0, y0 + wh / 2, D / 2 - t / 2);
    k.box(t, wh, D, tm, -W / 2 + t / 2, y0 + wh / 2, 0); k.box(t, wh, D, tm, W / 2 - t / 2, y0 + wh / 2, 0);
    k.cyl('z', 0.035, 0.16, tm, W * 0.3, y0 + 0.07, D / 2 + 0.04, { seg: 10 });
    k.anchor('label', [-W * 0.25, y0 + wh, D * 0.2]);
  });

  /* an emergency shutdown push button (IGF M03): a red mushroom in a yellow housing on a post; at = its foot; facing +z */
  define('esd_button', function (k, p) {
    var h = num(p.h, 1.24), dark = k.mat('steel_dark'), yel = k.mat('yellow'), red = k.mat('red');
    k.box(0.34, 0.03, 0.34, dark, 0, 0.015, 0);
    k.cyl('y', 0.045, h - 0.14, yel, 0, (h - 0.14) / 2, 0, { seg: 16 });
    k.box(0.3, 0.26, 0.17, yel, 0, h, 0);
    k.cyl('z', 0.115, 0.04, dark, 0, h, 0.1, { seg: 24 });
    k.cyl('z', 0.085, 0.07, red, 0, h, 0.14, { seg: 24 });
    k.add(new T.SphereGeometry(0.085, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2), red, 0, h, 0.175, { rx: Math.PI / 2 });
    k.anchor('label', [0, h + 0.16, 0]);
  });

  /* a portable foam extinguisher: a red cylinder with a carrying handle, a valve head, a hose and a foam nozzle; at = its
     foot; the hose leaves toward +z */
  define('foam_extinguisher', function (k, p) {
    var h = num(p.h, 0.6), r = h * 0.2, red = M(k, p, 'red'), dark = k.mat('steel_dark'), blk = k.mat('steel_black');
    k.cyl('y', r, h, red, 0, h / 2, 0, { seg: 24 });
    k.ball(r, red, 0, h, 0, { seg: 24 });
    k.cyl('y', r * 0.4, 0.06, dark, 0, h + r * 0.9, 0, { seg: 14 });
    k.box(r * 1.5, 0.025, 0.05, dark, 0, h + r * 0.9 + 0.045, 0);
    k.cyl('x', 0.02, r * 1.1, dark, r * 0.55, h + r * 0.9, 0, { seg: 10 });
    k.run([[r * 0.8, h + r * 0.85, 0], [r * 1.4, h * 0.7, r * 0.7], [r * 0.9, h * 0.35, r * 1.5], [0, h * 0.3, r * 1.4]], 0.014, blk);
    k.cyl('z', 0.04, 0.16, dark, 0, h * 0.3, r * 1.4 + 0.08, { seg: 12 });
    k.anchor('label', [0, h + r * 1.4, 0]);
  });

  /* -------------------------------------------------------------------- portable foam equipment
     The parts join end to end by their ports (PORTS below): a fire hose from the hydrant's "out" to the inductor's "in",
     the branch pipe "connect"ed to the inductor's "out", the inductor's pick-up tube in the container's "mouth" ("pickup").
     Water runs along +x through the inductor and the branch pipe. */
  var PORTS = {};
  function lathe(k, prof, m, o) {
    var g = new T.LatheGeometry(prof.map(function (q) { return new T.Vector2(q[1], q[0]); }), 36);
    g.rotateZ(-Math.PI / 2);
    return k.add(g, m, 0, 0, 0, o);
  }
  function shapeXY(pts) { var s = new T.Shape(); s.moveTo(pts[0][0], pts[0][1]); pts.slice(1).forEach(function (q) { s.lineTo(q[0], q[1]); }); return s; }
  function outline(pts, y) {
    var out = [], i, a, b;
    for (i = 0; i < pts.length; i++) { a = pts[i]; b = pts[(i + 1) % pts.length]; out.push(a[0], a[1] * y, 0.002, b[0], b[1] * y, 0.002); }
    return out;
  }

  /* the inductor's shape along x (len 0.42, r the bore 0.032): couplings, the inlet bore, the jet nozzle converging in the
     suction chamber, the throat, the diffuser; xp the concentrate port on top of the chamber, the metering valve over it
     (yv) and its hose tail pointing back (-z, zTail) */
  function inductorGeo(p) {
    var L = num(p.len, 0.42), r = num(p.r, 0.032), x0 = -L / 2;
    function X(u) { return x0 + u * L; }
    var g = { L: L, r: r, x0: x0, x1: L / 2, rc: r * 1.6, R1: r * 1.38, R2: r * 1.8, rn: r * 0.42, rt: r * 0.58, rcI: r * 1.25,
              t: r * 0.22, xn0: X(0.22), xs: X(0.32), xn: X(0.47), xe: X(0.56), xt: X(0.68), xd: X(0.86) };
    g.xa = x0 + g.rc * 1.15; g.xb = g.x1 - g.rc * 1.15; g.xp = g.xs + (g.xe - g.xs) * 0.3;
    g.yv = g.R2 + r * 1.1; g.zTail = -r * 0.9 - r * 1.6;
    return g;
  }
  PORTS.foam_inductor = function (p) {
    var g = inductorGeo(p);
    return { 'in': [[g.x0, 0, 0], [-1, 0, 0]], out: [[g.x1, 0, 0], [1, 0, 0]], pickup: [[g.xp, g.yv, g.zTail], [0, 0, -1]] };
  };
  /* an in-line foam inductor (eductor): light-alloy body with hose couplings at both ends (water in at -x, out at +x), the
     metering valve on top (its dial faces up, the hose tail back to -z) and the pick-up tube - clear, the concentrate seen rising in it - with its
     rigid pick-up wand. at = the middle of the body, on its axis. len (0.42), r (bore, 0.032); pickup: "<id>.mouth" (a
     foam_container's) or [x, y, z] - where the wand goes in. Sub-parts "valve" (metering valve), "pickup" (tube and wand),
     "venturi" (the inside - jet nozzle, throat, diffuser and the concentrate port; anchors "nozzle", "throat", "port").
     States: "<id>.cut" opens the near half (the venturi seen in section); "<id>.on" - water through the jet, the
     concentrate drawn up the tube and in at the throat. Ports "in", "out", "pickup". */
  define('foam_inductor', function (k, p) {
    var g = inductorGeo(p), self = k.cur, id = self.id, r = g.r, i;
    var pl = k.clip([0, 0, -1], g.R2 + 0.2), clip = [pl];
    var body = M(k, p, null, { clip: clip }) || k.mat({ color: '#c2cad1', rough: 0.32, metal: 0.75 }, { clip: clip });
    var bore = k.mat({ color: '#6c7782', rough: 0.55, metal: 0.4 }, { clip: clip });
    function rNz(x) { return r + (g.rn - r) * (x - g.xn0) / (g.xn - g.xn0); }
    var outer = [[g.xa, g.R1], [g.xs - r * 0.4, g.R1], [g.xs, g.R2], [g.xe, g.R2], [g.xe + r * 0.4, g.R1], [g.xb, g.R1 * 1.06]];
    var inner = [[g.x0, r], [g.xn0, r], [g.xn, g.rn], [g.xn, g.rn + g.t], [g.xs, rNz(g.xs) + g.t], [g.xs, g.rcI], [g.xe, g.rcI],
                 [g.xe, g.rt], [g.xt, g.rt], [g.xd, r], [g.x1, r]];
    lathe(k, outer, body);
    lathe(k, inner, bore);
    k.add(new T.RingGeometry(r, g.R1, 36), body, g.xa, 0, 0, { ry: Math.PI / 2 });
    k.add(new T.RingGeometry(r, g.R1 * 1.06, 36), body, g.xb, 0, 0, { ry: Math.PI / 2 });
    couplingAt(k, [g.x0, 0, 0], [-1, 0, 0], g.rc, body);
    couplingAt(k, [g.x1, 0, 0], [1, 0, 0], g.rc, body);
    var ports = PORTS.foam_inductor(p);
    each(ports, function (q, n) { k.port(n, q[0], q[1]); });
    k.anchor('label', [(g.xt + g.xb) / 2, g.R1, 0]);

    /* the metering valve: a boss on the chamber, the valve body, its dial on top with the knob, the hose tail to the back */
    k.sub(subId(k, p, 'valve'), { pick: true });
    var vm = k.mat({ color: '#aeb7bf', rough: 0.35, metal: 0.7 }), dark = k.mat('steel_black'), y0 = g.R2 * 0.7, y1 = g.yv - r * 0.6;
    k.cyl('y', r * 0.5, y1 - y0, vm, g.xp, (y0 + y1) / 2, 0, { seg: 16 });
    k.cyl('y', r * 0.9, r * 1.2, vm, g.xp, g.yv, 0, { seg: 24 });
    k.cyl('y', r * 0.82, r * 0.12, k.mat({ color: '#eef1f3', rough: 0.5, metal: 0 }), g.xp, g.yv + r * 0.62, 0, { seg: 24 });
    k.box(r * 1.35, r * 0.3, r * 0.3, dark, g.xp, g.yv + r * 0.8, 0, { ry: 0.5 });
    for (i = 0; i < 5; i++) { k.box(r * 0.05, r * 0.05, r * 0.22, dark, g.xp + Math.sin(-1 + i * 0.5) * r * 0.62, g.yv + r * 0.69, Math.cos(-1 + i * 0.5) * r * 0.62, { ry: -1 + i * 0.5 }); }
    k.cyl('z', r * 0.3, -g.zTail - r * 0.6, vm, g.xp, g.yv, (g.zTail - r * 0.6) / 2, { seg: 12 });
    k.cyl('z', r * 0.38, r * 0.18, vm, g.xp, g.yv, g.zTail + r * 0.4, { seg: 12 });
    k.anchor('label', [g.xp, g.yv + r * 0.7, 0]);
    k.cur = self;

    /* the pick-up tube: clear, from the hose tail to the top of the rigid wand that stands in the container's mouth */
    k.sub(subId(k, p, 'pickup'), { pick: true });
    var tgt = p._pickup ? { at: k.local(p._pickup.at), dir: k.localDir(p._pickup.dir) } :
      (Array.isArray(p.pickup) && p.pickup.length === 3 ? { at: k.local(p.pickup), dir: [0, 1, 0] } : { at: [g.xp + 0.2, g.yTail - 0.45, 0.45], dir: [0, 1, 0] });
    var up = unit(tgt.dir), T0 = tgt.at, W = [T0[0] + up[0] * 0.16, T0[1] + up[1] * 0.16, T0[2] + up[2] * 0.16];
    var P0 = ports.pickup[0], P1 = [P0[0], P0[1], P0[2] - 0.08], Pn = [W[0] + up[0] * 0.08, W[1] + up[1] * 0.08, W[2] + up[2] * 0.08];
    var dist = Math.sqrt(Math.pow(Pn[0] - P1[0], 2) + Math.pow(Pn[1] - P1[1], 2) + Math.pow(Pn[2] - P1[2], 2));
    var Pm = [(P1[0] + Pn[0]) / 2, Math.min(P1[1], Pn[1]) - 0.12 * dist, (P1[2] + Pn[2]) / 2];
    var tr = r * 0.34, path = [P0, P1, Pm, Pn, W];
    var clear = k.mat({ color: '#dfeaf0', rough: 0.15, metal: 0 }, { opacity: 0.45 });
    var tube = k.tube(path, tr, clear, { seg: 12 }), curve = tube.geometry.parameters.path;
    var core = k.add(new T.TubeGeometry(curve, Math.max(24, path.length * 12), tr * 0.62, 8, false),
      k.mat({ color: CONCENTRATE, rough: 0.3, metal: 0 }), 0, 0, 0, { keep: true, cast: false });
    var coreN = core.geometry.index.count, coreSeg = core.geometry.parameters.tubularSegments;
    var al = alloy(k);
    k.seg([T0[0] - up[0] * 0.3, T0[1] - up[1] * 0.3, T0[2] - up[2] * 0.3], W, r * 0.36, al, { seg: 12 });
    k.seg([W[0] - up[0] * 0.03, W[1] - up[1] * 0.03, W[2] - up[2] * 0.03], [W[0] + up[0] * 0.03, W[1] + up[1] * 0.03, W[2] + up[2] * 0.03], r * 0.46, al, { seg: 12 });
    var mt = curve.getPointAt(0.3);
    k.anchor('label', [mt.x, mt.y + tr, mt.z]);
    function fill(f) {
      var s = Math.round((1 - clamp(f, 0, 1)) * coreSeg) * (coreN / coreSeg);
      core.geometry.setDrawRange(s, coreN - s);
      core.visible = f > 0.01;
    }
    fill(0);
    k.cur = self;

    /* the inside: the wall seen in section where the near half is cut away, the water and the concentrate in it */
    k.sub(subId(k, p, 'venturi'), { pick: true, need: id + '.cut > 0.5' });
    var face = k.mat({ color: '#e6eaed', rough: 0.6, metal: 0.1 }, { double: true });
    var sec = outer.slice();
    sec.unshift([g.x0, g.rc], [g.xa, g.rc]); sec.push([g.xb, g.rc], [g.x1, g.rc]);
    var wall = sec.concat(inner.slice().reverse()), cut = [];
    [1, -1].forEach(function (s) {
      var sg = new T.ShapeGeometry(shapeXY(wall.map(function (q) { return [q[0], q[1] * s]; })));
      cut.push(k.add(sg, face, 0, 0, 0.001, { keep: true, cast: false }));
      cut.push(k.lines(outline(wall, s), '#3f4a54'));
    });
    var pw = r * 0.42, cm = k.mat({ color: CONCENTRATE, rough: 0.4, metal: 0 }, { double: true });
    cut.push(k.box(pw, g.R2 - g.rcI, 0.002, cm, g.xp, (g.R2 + g.rcI) / 2, 0.003, { keep: true, cast: false }));
    /* while it runs: the water in the bore and the jet, the concentrate round the jet in the chamber (flat, at the cut) */
    var wm = k.mat({ color: '#a9c8f2', rough: 0.4, metal: 0 }, { double: true });
    var jet = [[g.x0, r], [g.xn0, r], [g.xn, g.rn], [g.xe, g.rn * 1.05], [g.xt, g.rt], [g.xd, r], [g.x1, r]];
    var water = jet.concat(jet.slice().reverse().map(function (q) { return [q[0], -q[1]]; }));
    var chamber = [[g.xn, g.rn + g.t], [g.xs, rNz(g.xs) + g.t], [g.xs, g.rcI], [g.xe, g.rcI], [g.xe, g.rt], [g.xt, g.rt], [g.xe, g.rn * 1.05]];
    var run = [k.add(new T.ShapeGeometry(shapeXY(water)), wm, 0, 0, 0.0005, { keep: true, cast: false })];
    [1, -1].forEach(function (s) {
      run.push(k.add(new T.ShapeGeometry(shapeXY(chamber.map(function (q) { return [q[0], q[1] * s]; }))), cm, 0, 0, 0.0007, { keep: true, cast: false }));
    });
    k.anchor('nozzle', [g.xn - r * 0.5, -(rNz(g.xn - r * 0.5) + g.t), 0]);
    k.anchor('throat', [(g.xe + g.xt) / 2, g.rt, 0]);
    k.anchor('port', [g.xp, g.rcI, 0]);
    k.anchor('label', [(g.xe + g.xt) / 2, g.rt, 0]);
    k.cur = self;
    flowArrows(k, [[g.x0 + 0.01, 0, 0.004], [g.x1 - 0.01, 0, 0.004]], id, { color: WATER, r: r * 0.22, spacing: r * 2.2, speed: 0.35 });
    flowArrows(k, [[g.xp, g.R2, 0.004], [g.xp, g.rcI * 0.9, 0.004], [g.xe, g.rt * 0.75, 0.004], [g.xd, r * 0.5, 0.004]], id,
      { color: CONCENTRATE, r: r * 0.2, spacing: r * 1.6, speed: 0.2 });
    flowArrows(k, [[g.xp, g.rcI * 0.9, 0.004], [g.xs + r * 0.1, (g.rcI + rNz(g.xs) + g.t) / 2, 0.004]], id,
      { color: CONCENTRATE, r: r * 0.16, spacing: r * 1.4, speed: 0.12 });
    k.state(id + '.cut', p.cut ? 1 : 0, function (v) {
      pl.set((g.R2 + 0.2) * (1 - v));
      cut.forEach(function (m) { m.visible = v > 0.95; });
    });
    k.state(id + '.on', 0, function (v) { run.forEach(function (m) { m.visible = v > 0.5; }); });
    k.anim(id, function (t, on) { fill(on ? (reduce ? 1 : t / 1.4) : 0); return on && !reduce && t < 1.5; });
  });

  /* the branch pipe's shape along x: the coupling at x = 0, the nozzle, the wide head with the mesh at its mouth */
  function branchGeo(p) {
    var low = p.kind === 'low', rc = 0.051;
    if (low) { var L0 = num(p.len, 0.85), r0 = num(p.r, 0.032); return { low: true, rc: rc, L: L0, r: r0, x1: L0 }; }
    var R = num(p.r, 0.13), Lh = num(p.len, 0.75) - 0.3;
    return { low: false, rc: rc, R: R, xn: 0.2, xh0: 0.3, x1: 0.3 + Lh };
  }
  PORTS.foam_branch_pipe = function (p) {
    var g = branchGeo(p);
    return { 'in': [[0, 0, 0], [-1, 0, 0]], out: [[g.x1, 0, 0], [1, 0, 0]] };
  };
  /* a foam branch pipe. kind "medium" (default): medium-expansion - the inlet coupling, the nozzle with its grip, the air
     inlets round the nozzle (open windows between the struts), the wide head (r 0.13, len 0.75 in all) and the fine
     stainless mesh across its mouth, a carrying handle on top. kind "low": the low-expansion branch - a long barrel (r
     0.032, len 0.85) with air holes behind the nozzle. at = the inlet coupling's face, the barrel to +x; "connect":
     "<inductor>.out" puts it on the inductor's outlet. Sub-parts "air" (the air inlets) and "mesh" (medium). State
     "<id>.on": air drawn in, foam out of the mouth. Ports "in", "out". */
  define('foam_branch_pipe', function (k, p) {
    var g = branchGeo(p), self = k.cur, id = self.id, al = alloy(k), m = M(k, p, 'red', { double: true }), dark = k.mat('steel_dark');
    var grip = k.mat('rubber'), i, a;
    couplingAt(k, [0, 0, 0], [-1, 0, 0], g.rc, al);
    var cl = g.rc * 1.15;
    if (g.low) {
      lathe(k, [[cl, g.r * 1.15], [0.2, g.r * 1.1], [0.24, g.r], [g.L - 0.12, g.r], [g.L, g.r * 1.35]], m);
      k.add(new T.RingGeometry(g.r * 0.8, g.r * 1.35, 32), dark, g.L, 0, 0, { ry: Math.PI / 2 });
      k.add(new T.CircleGeometry(g.r * 0.8, 24), k.mat('steel_black', { double: true }), g.L - 0.01, 0, 0, { ry: Math.PI / 2 });
      k.box(0.03, 0.11, 0.032, grip, 0.12, -0.08, 0, { rz: 0.25 });
      k.anchor('label', [g.L * 0.6, g.r, 0]);
      k.sub(subId(k, p, 'air'), { pick: true });
      var holes = [];
      for (i = 0; i < 6; i++) { a = i * Math.PI / 3; holes.push({ at: [0.28, Math.cos(a) * g.r, Math.sin(a) * g.r], rx: a }); }
      k.many(new T.BoxGeometry(0.05, 0.004, g.r * 0.7), k.mat('steel_black'), holes);
      k.anchor('label', [0.28, g.r, 0]);
      k.cur = self;
      foamOut(k, id, g.L, g.r * 1.2, 0.5);
      flowArrows(k, [[0.24, g.r * 3.2, 0], [0.28, g.r * 1.15, 0]], id, { color: AIR, r: 0.012, spacing: 0.04, speed: 0.08 });
    } else {
      var R = g.R;
      lathe(k, [[cl, 0.036], [0.15, 0.034], [g.xn, 0.026]], al);
      k.box(0.03, 0.12, 0.034, grip, 0.11, -0.085, 0, { rz: 0.28 });
      k.seg([0.07, -0.035, 0], [0.16, -0.035, 0], 0.008, al, { seg: 8 });
      k.cyl('x', R, g.x1 - g.xh0, m, (g.xh0 + g.x1) / 2, 0, 0, { open: true, seg: 40 });
      k.ring('x', R, 0.008, al, g.xh0, 0, 0, { seg: 40 });
      k.ring('x', R, 0.01, al, g.x1, 0, 0, { seg: 40 });
      k.seg([0.42, R, 0], [0.42, R + 0.06, 0], 0.008, dark, { seg: 8 });
      k.seg([0.62, R, 0], [0.62, R + 0.06, 0], 0.008, dark, { seg: 8 });
      k.seg([0.4, R + 0.06, 0], [0.64, R + 0.06, 0], 0.012, grip, { seg: 10 });
      k.anchor('label', [(g.xh0 + g.x1) / 2, R, 0]);
      /* the air inlets: six struts carry the head on the nozzle; the windows between them are open */
      k.sub(subId(k, p, 'air'), { pick: true });
      for (i = 0; i < 6; i++) {
        a = i * Math.PI / 3 + Math.PI / 6;
        k.seg([g.xn - 0.04, Math.cos(a) * 0.034, Math.sin(a) * 0.034], [g.xh0, Math.cos(a) * R, Math.sin(a) * R], 0.006, al, { seg: 6 });
      }
      k.ring('x', 0.036, 0.006, al, g.xn - 0.04, 0, 0, { seg: 20 });
      k.anchor('label', [(g.xn + g.xh0) / 2 - 0.02, R * 0.55, R * 0.25]);
      k.cur = self;
      /* the mesh: a fine stainless screen across the mouth - a see-through disc and its wires */
      k.sub(subId(k, p, 'mesh'), { pick: true });
      k.add(new T.CircleGeometry(R, 40), k.mat({ color: '#9aa4ad', rough: 0.5, metal: 0.6 }, { opacity: 0.45 }), g.x1 - 0.006, 0, 0, { ry: Math.PI / 2 });
      var wires = [], st = R / 9, c;
      for (c = -R + st; c < R - 1e-6; c += st) {
        var h = Math.sqrt(R * R - c * c);
        wires.push(g.x1 - 0.005, c, -h, g.x1 - 0.005, c, h, g.x1 - 0.005, -h, c, g.x1 - 0.005, h, c);
      }
      k.lines(wires, '#59646e', { opacity: 0.85 });
      k.anchor('label', [g.x1, R * 0.55, R * 0.3]);
      k.cur = self;
      foamOut(k, id, g.x1, R, 1);
      [0, 1].forEach(function (j) {
        var s = j ? 1 : -1;
        flowArrows(k, [[g.xn - 0.07, 0, s * R * 1.25], [(g.xn + g.xh0) / 2, 0, s * R * 0.4]], id, { color: AIR, r: 0.014, spacing: 0.045, speed: 0.09 });
      });
      flowArrows(k, [[g.xn - 0.07, R * 1.25, 0], [(g.xn + g.xh0) / 2, R * 0.4, 0]], id, { color: AIR, r: 0.014, spacing: 0.045, speed: 0.09 });
    }
    each(PORTS.foam_branch_pipe(p), function (q, n) { k.port(n, q[0], q[1]); });
  });
  /* foam out of a mouth at x (radius R) while "<id>.on": a white mass of bubbles that leaves the mesh, swells and droops */
  function foamOut(k, id, x, R, scale) {
    var n = 90, rnd = seeded(hashId(id) + 5), seeds = [], i;
    for (i = 0; i < n; i++) { var a = rnd() * Math.PI * 2, d = Math.sqrt(rnd()) * R * 0.85; seeds.push([Math.cos(a) * d, Math.sin(a) * d, i / n, 0.8 + rnd() * 0.5]); }
    var g = new T.SphereGeometry(R * 0.2, 10, 7), fm = k.mat({ color: '#f4f7fa', rough: 0.9, metal: 0 });
    var im = new T.InstancedMesh(k.track(g), fm, n), dm = new T.Object3D(), reach = 0.6 * scale;
    im.userData.noPick = true; im.visible = false; im.castShadow = true;
    k.g.add(im); k.S.disposeLater.push(im);
    function place(t) {
      for (var j = 0; j < n; j++) {
        var u = (seeds[j][2] + t * 0.3) % 1, sp = 1 + u * 0.7, s = (0.9 + u * 1.4) * seeds[j][3];
        dm.position.set(x + R * 0.12 + u * reach, seeds[j][0] * sp - u * u * 0.3 * scale, seeds[j][1] * sp);
        dm.scale.set(s, s * 0.85, s);
        dm.updateMatrix();
        im.setMatrixAt(j, dm.matrix);
      }
      im.instanceMatrix.needsUpdate = true;
    }
    place(0);
    k.state(id + '.on', 0, function (v) { im.visible = v > 0.5; });
    k.anim(id, function (t, on) { im.visible = on; if (on) { place(reduce ? 0 : t); } return on && !reduce; });
  }

  /* the foam concentrate container's size: jerrycan [w 0.3, h 0.4, d 0.2]; drum r 0.15, h 0.42 */
  function containerGeo(p) {
    var s = p.size || [], drum = p.kind === 'drum';
    var W = num(s[0], drum ? 0.3 : 0.3), H = num(s[1], drum ? 0.42 : 0.4), D = num(s[2], drum ? 0.3 : 0.2);
    return { drum: drum, W: W, H: H, D: D, mouth: [drum ? W * 0.28 : W * 0.27, H + 0.035, 0] };
  }
  PORTS.foam_container = function (p) { return { mouth: [containerGeo(p).mouth, [0, 1, 0]] }; };
  /* a foam concentrate container (20-25 litres): kind "jerrycan" (default) - a plastic can with its top handle and
     screw neck, a label on its front (+z); kind "drum" - a plastic drum with rolling rings. size [w, h, d]; at = its base
     centre on the deck; open: true (or an inductor's "pickup" in its mouth) - the cap off. Port "mouth". */
  define('foam_container', function (k, p) {
    var g = containerGeo(p), m = M(k, p, null) || k.mat({ color: '#e7e1cf', rough: 0.62, metal: 0 }), W = g.W, H = g.H, D = g.D;
    var me = (k.cur && k.cur.id) || '', open = p.open === true || (k.S.spec.parts || []).some(function (q) { return q && q.pickup === me + '.mouth'; });
    var paper = k.mat({ color: '#f6f5f0', rough: 0.7, metal: 0 }), band = k.mat('red'), ink = k.mat('steel_black'), cap = k.mat({ color: '#3a4652', rough: 0.5, metal: 0.1 });
    if (g.drum) {
      var R = W / 2;
      k.cyl('y', R, H, m, 0, H / 2, 0, { seg: 40 });
      k.ring('y', R + 0.002, 0.008, m, 0, H * 0.33, 0, { seg: 40 }); k.ring('y', R + 0.002, 0.008, m, 0, H * 0.66, 0, { seg: 40 });
      k.ring('y', R - 0.01, 0.01, m, 0, H, 0, { seg: 40 });
      k.cyl('y', R + 0.003, H * 0.22, paper, 0, H * 0.5, 0, { open: true, seg: 24, t0: -0.85, tl: 1.7 });
      k.cyl('y', R + 0.004, H * 0.05, band, 0, H * 0.57, 0, { open: true, seg: 24, t0: -0.85, tl: 1.7 });
      k.cyl('y', 0.02, 0.012, cap, -R * 0.55, H + 0.006, 0, { seg: 16 });
      k.anchor('label', [-R * 0.3, H, R * 0.3]);
    } else {
      var b = 0.014, rr = 0.03, w = W / 2 - b, sh = new T.Shape();
      sh.moveTo(-w + rr, b); sh.lineTo(w - rr, b); sh.quadraticCurveTo(w, b, w, b + rr); sh.lineTo(w, H - b - rr);
      sh.quadraticCurveTo(w, H - b, w - rr, H - b); sh.lineTo(-w + rr, H - b); sh.quadraticCurveTo(-w, H - b, -w, H - b - rr);
      sh.lineTo(-w, b + rr); sh.quadraticCurveTo(-w, b, -w + rr, b);
      var eg = new T.ExtrudeGeometry(sh, { depth: D - 2 * b, bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelSegments: 2, curveSegments: 6 });
      eg.translate(0, 0, -(D - 2 * b) / 2);
      k.add(eg, m, 0, 0, 0);
      k.box(W * 0.7, H * 0.42, 0.003, paper, 0, H * 0.45, D / 2 + 0.0015);
      k.box(W * 0.7, H * 0.08, 0.004, band, 0, H * 0.58, D / 2 + 0.002);
      k.box(W * 0.46, 0.012, 0.004, ink, 0, H * 0.42, D / 2 + 0.002);
      k.box(W * 0.32, 0.01, 0.004, ink, 0, H * 0.36, D / 2 + 0.002);
      k.seg([-W * 0.38, H - 0.01, 0], [-W * 0.38, H + 0.05, 0], 0.012, m, { seg: 10 });
      k.seg([-W * 0.02, H - 0.01, 0], [-W * 0.02, H + 0.05, 0], 0.012, m, { seg: 10 });
      k.seg([-W * 0.4, H + 0.052, 0], [0, H + 0.052, 0], 0.014, m, { seg: 12 });
      k.anchor('label', [-W * 0.2, H + 0.065, 0]);
    }
    var mo = g.mouth;
    k.cyl('y', 0.022, 0.035, m, mo[0], H + 0.0175, 0, { seg: 20 });
    if (!open) { k.cyl('y', 0.027, 0.026, cap, mo[0], H + 0.035 + 0.013, 0, { seg: 20 }); }
    else { k.ring('y', 0.022, 0.004, cap, mo[0], H + 0.035, 0, { seg: 20 }); }
    k.port('mouth', mo, [0, 1, 0]);
  });

  PORTS.fire_hydrant = function (p) { var h = num(p.h, 0.75); return { out: [[0.19, h - 0.07, 0], unit([1, -0.45, 0])] }; };
  /* a fire main hydrant: the riser from the deck, the valve with its red handwheel, the outlet turned down to +x with its
     hose coupling. at = its foot; h (the outlet's height, 0.75). Port "out" - a fire hose's "from". */
  define('fire_hydrant', function (k, p) {
    var h = num(p.h, 0.75), red = M(k, p, 'red'), dark = k.mat('steel_dark'), o = PORTS.fire_hydrant(p).out, d = o[1];
    k.cyl('y', 0.09, 0.025, dark, 0, 0.0125, 0, { seg: 24 });
    k.cyl('y', 0.048, h - 0.05, red, 0, (h - 0.05) / 2, 0, { seg: 20 });
    k.cyl('y', 0.075, 0.018, dark, 0, h * 0.55, 0, { seg: 24 });
    k.ball(0.075, red, 0, h, 0, { seg: 24 });
    k.cyl('y', 0.034, 0.13, red, 0, h + 0.09, 0, { seg: 16 });
    k.cyl('y', 0.008, 0.07, dark, 0, h + 0.18, 0, { seg: 8 });
    k.ring('y', 0.085, 0.009, red, 0, h + 0.2, 0, { seg: 28 });
    k.box(0.17, 0.012, 0.012, red, 0, h + 0.2, 0); k.box(0.012, 0.012, 0.17, red, 0, h + 0.2, 0);
    var len = 0.051 * 1.15, e = [o[0][0] - d[0] * len, o[0][1] - d[1] * len, o[0][2] - d[2] * len];
    k.seg([0.02, h, 0], e, 0.038, red, { seg: 16 });
    couplingAt(k, o[0], d, 0.051, alloy(k));
    k.port('out', o[0], d);
    k.anchor('label', [0, h + 0.2, 0]);
  });

  /* a gas detector head (IGF M09): base plate, yellow body, cap and a lamp that lights in alarm ("<id>.alarm" 0..1,
     amber at half, red at 1). at = where it is fixed; face "down" (on a deckhead, default) or "up". kind "leak": a liquid
     leak sensor (a cold probe in its guard, at the bottom of a hold space); "temperature": a temperature sensor (a probe
     with its head, in a hull's insulation or on the inner hull) - each with the same lamp */
  define('detector', function (k, p) {
    var s = p.face === 'up' ? 1 : -1, self = k.cur, kind = p.kind || 'gas', top = 0.3;
    k.cyl('y', 0.11, 0.03, k.mat('steel_dark'), 0, s * 0.015, 0, { seg: 20 });
    if (kind === 'leak') {
      k.cyl('y', 0.05, 0.28, k.mat('stainless'), 0, s * 0.17, 0, { seg: 16 });
      k.cyl('y', 0.09, 0.12, k.mat('steel_black'), 0, s * 0.27, 0, { seg: 8, open: true });
      k.box(0.16, 0.1, 0.12, k.mat('amber'), 0, s * 0.05, 0.12);
    } else if (kind === 'temperature') {
      k.box(0.12, 0.1, 0.12, k.mat('steel_mid'), 0, s * 0.08, 0);
      k.cyl('y', 0.015, 0.5, k.mat('stainless'), 0, s * 0.38, 0, { seg: 10 });
      top = 0.62;
    } else {
      k.cyl('y', 0.07, 0.2, k.mat('yellow'), 0, s * 0.13, 0, { seg: 20 });
      k.cyl('y', 0.085, 0.05, k.mat('steel_black'), 0, s * 0.255, 0, { seg: 20 });
    }
    var lm = k.basic('#3a2a20', 1, { toneMapped: false });
    k.ball(0.045, lm, 0.09, s * 0.16, 0.0, { seg: 12, cast: false });
    var off = k.col('#3a2a20'), amb = new T.Color('#ffb020'), red = new T.Color('#ff3030');
    k.state(self.id + '.alarm', 0, function (v) {
      var c = v < 0.5 ? off.clone().lerp(amb, v * 2) : amb.clone().lerp(red, (v - 0.5) * 2);
      lm.color.copy(c); lm.userData.c0 = c.clone();
    });
    k.anchor('label', [0, s * top, 0]);
  });

  /* a person for scale (1.8 m): at = between the feet, facing +z; h; wear "helmet" */
  define('person', function (k, p) {
    var f = num(p.h, 1.8) / 1.8, o = M(k, p, 'overall'), skin = k.mat('skin');
    k.push([0, 0, 0], 0, f);
    k.box(0.15, 0.85, 0.18, o, -0.1, 0.425, 0); k.box(0.15, 0.85, 0.18, o, 0.1, 0.425, 0);
    k.box(0.44, 0.62, 0.26, o, 0, 1.16, 0);
    k.box(0.11, 0.6, 0.12, o, -0.29, 1.12, 0); k.box(0.11, 0.6, 0.12, o, 0.29, 1.12, 0);
    k.ball(0.115, skin, 0, 1.6, 0, { seg: 16 });
    if (p.wear !== 'none') { k.add(new T.SphereGeometry(0.13, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), k.mat('helmet'), 0, 1.63, 0); }
    k.pop();
    k.anchor('label', [0, 1.8 * f, 0]);
  });

  /* an air intake with louvres (IGF M15): size [w, h, d], at = centre, louvres facing +z */
  define('air_intake', function (k, p) {
    var s = p.size || [1.6, 1.2, 0.5], W = s[0], H = s[1], D = s[2], m = M(k, p, 'steel'), list = [], y;
    k.box(W, H, D, m, 0, 0, 0);
    for (y = -H / 2 + 0.12; y < H / 2 - 0.05; y += 0.14) { list.push({ at: [0, y, D / 2 + 0.03], rx: -0.6 }); }
    k.many(new T.BoxGeometry(W * 0.9, 0.02, 0.12), k.mat('steel_dark'), list);
    k.anchor('label', [0, H / 2, 0]);
  });

  /* -------------------------------------------------------------------- measures */
  /* a measured line a -> b with arrow heads and end ticks (IGF M02), drawn over everything; text: its value, a tag on
     the line (the label comes by itself); tick: half a tick [x, y, z]; color (amber); white: true */
  define('dimension', function (k, p) {
    var a = v3(p.a), b = v3(p.b, [1, 0, 0]), dv = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
    var len = Math.sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]) || 1, r = num(p.r, Math.max(0.02, len * 0.02));
    var mt = k.basic(p.white ? '#ffffff' : (p.color || '#F5B52E'), 1, { transparent: true, depthTest: false });
    k.seg(a, b, r, mt, { order: 10, seg: 8 });
    var hh = Math.min(r * 5.5, len * 0.3);
    k.cone(a, [-dv[0], -dv[1], -dv[2]], hh * 0.42, hh, mt, { order: 10 });
    k.cone(b, dv, hh * 0.42, hh, mt, { order: 10 });
    var t = p.tick;
    if (t) {
      k.seg([a[0] - t[0], a[1] - t[1], a[2] - t[2]], [a[0] + t[0], a[1] + t[1], a[2] + t[2]], r * 0.8, mt, { order: 10, seg: 8 });
      k.seg([b[0] - t[0], b[1] - t[1], b[2] - t[2]], [b[0] + t[0], b[1] + t[1], b[2] + t[2]], r * 0.8, mt, { order: 10, seg: 8 });
    }
    var mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2], self = k.cur, g = k.g;
    if (p.text) { k.label({ text: p.text, at: mid, tag: true, ox: num(p.ox, 0), oy: num(p.oy, 0), tone: p.white ? 'white' : '', when: self.id + '.on' }); }
    k.anchor('label', mid);
    k.state(self.id + '.on', 1, function (v) { g.visible = v > 0.5; });   /* shown and hidden with what it measures */
  });

  /* where a thing must stay (IGF M02): a dashed amber box min -> max and faint planes on the faces named in planes,
     {"z-": 0.07, "z+": 0.07, "y-": 0.16} */
  define('limit_box', function (k, p) {
    var a = v3(p.min), b = v3(p.max, [1, 1, 1]), col = p.color || AMBER;
    k.lines(k.boxEdges(a[0], b[0], a[1], b[1], a[2], b[2]), col, { dash: num(p.dash, 0.7), opacity: 0.85, order: 6 });
    var cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2, cz = (a[2] + b[2]) / 2, W = b[0] - a[0], H = b[1] - a[1], D = b[2] - a[2];
    each(p.planes || {}, function (op, face) {
      var g;
      if (face.charAt(0) === 'z') { g = new T.PlaneGeometry(W, H); k.add(g, k.basic(col, op), cx, cy, face === 'z-' ? a[2] : b[2], { order: 2, noPick: true }); }
      else if (face.charAt(0) === 'x') { g = new T.PlaneGeometry(D, H); g.rotateY(Math.PI / 2); k.add(g, k.basic(col, op), face === 'x-' ? a[0] : b[0], cy, cz, { order: 2, noPick: true }); }
      else { g = new T.PlaneGeometry(W, D); g.rotateX(-Math.PI / 2); k.add(g, k.basic(col, op), cx, face === 'y-' ? a[1] : b[1], cz, { order: 2, noPick: true }); }
    });
    k.anchor('label', [cx, b[1], cz]);
  });

  /* a hazardous zone (IGF M07): a soft shell with a glowing rim - faint inside, brighter where it turns away - zone 0
     red, 1 amber, 2 yellow. shape "sphere" (r) | "capsule" (r, half: half its straight length, along axis "x"|"z") |
     "box" (size); floor: nothing below this world height (the deck); "<id>.on" fades it in (starts 1 unless set) */
  define('zone', function (k, p) {
    var lvl = num(p.level, 1), c = new T.Color(p.color || ZONE[lvl] || ZONE[1]), self = k.cur;
    var pr = lvl === 0 ? [0.12, 0.6, 2.0] : lvl === 1 ? [0.05, 0.5, 2.6] : [0.022, 0.4, 2.8];
    if (p.base != null) { pr[0] = p.base; }             /* a flat fill (a box zone, a lamp's halo) */
    if (p.rim != null) { pr[1] = p.rim; }
    var u = { uColor: { value: new T.Vector3(c.r, c.g, c.b) }, uBase: { value: pr[0] }, uRim: { value: pr[1] }, uPow: { value: pr[2] },
      uFloor: { value: p.floor != null ? p.floor : -1e9 }, uOn: { value: 1 } };
    var m = new T.ShaderMaterial({
      transparent: true, depthWrite: false, depthTest: true, side: T.DoubleSide, uniforms: u,
      vertexShader: 'varying vec3 vN; varying vec3 vV; varying float vY;\n' +
        'void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.0);\n' +
        '  vV = normalize(-mv.xyz); vY = (modelMatrix * vec4(position, 1.0)).y; gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'uniform vec3 uColor; uniform float uBase; uniform float uRim; uniform float uPow; uniform float uFloor; uniform float uOn;\n' +
        'varying vec3 vN; varying vec3 vV; varying float vY;\n' +
        'void main(){ if (vY < uFloor) { discard; }\n' +
        '  float f = 1.0 - abs(dot(normalize(vN), normalize(vV))); f = pow(clamp(f, 0.0, 1.0), uPow);\n' +
        '  gl_FragColor = vec4(uColor, (uBase + uRim * f) * uOn); }'
    });
    k.reg(m);
    m.userData.glow = function (a) { u.uBase.value = pr[0] + a * 0.08; u.uRim.value = pr[1] + a * 0.3; };
    var g, shape = p.shape || 'sphere', r = num(p.r, 1.5);
    if (shape === 'box') { var s = p.size || [2, 2, 2]; g = new T.BoxGeometry(s[0], s[1], s[2]); }
    else {
      g = new T.SphereGeometry(r, 40, 26);
      var half = shape === 'capsule' ? num(p.half, 1) : 0, ps = g.attributes.position, i;
      for (i = 0; i < ps.count; i++) { ps.setY(i, ps.getY(i) + (ps.getY(i) >= 0 ? half : -half)); }
      if (shape === 'capsule') { if (p.axis === 'x') { g.rotateZ(Math.PI / 2); } else if (p.axis !== 'y') { g.rotateX(Math.PI / 2); } }
      g.computeVertexNormals();
    }
    var zm = k.add(g, m, 0, 0, 0, { order: 11 + (2 - lvl), cast: false, recv: false, keep: true });
    k.state(self.id + '.on', 1, function (v) { u.uOn.value = v; zm.visible = v > 0.01; });
    k.anchor('label', [0, shape === 'box' ? (p.size || [2, 2, 2])[1] / 2 : r + (shape === 'capsule' && p.axis === 'y' ? num(p.half, 1) : 0), 0]);
  });

  /* -------------------------------------------------------------------- effects: gas and flow */
  /* a gas cloud of soft puffs (IGF M04, M05, M09) or a vent plume (M15). at = the leak (or the outlet).
     kind: "rise" - up in a column to "to" (the deckhead's height above the leak), then spreads under it;
           "sink" - falls to "to" (the floor, negative) and spreads over it; "spread" - mixes round the leak;
           "plume" - leaves an outlet upwards and the wind (wind [x, y, z]) carries it, looping.
     area [x0, z0, x1, z1] - where it spreads (round the leak, 3 m); n (puffs, 240); color; dur (seconds to settle, 4);
     "<id>.on" plays it from the leak. Drawn by the GPU, no allocation per frame; reduced motion shows the end. */
  /* the hand-made M04's colour for each fuel's cloud - one colour, one fuel, across the course */
  var FUEL = { natural_gas: '#f2c230', cold_methane: '#c4f1ff', propane: '#f0653a', methanol: '#a98bff', ammonia: '#74d66f',
               hydrogen: '#ff6fb5', vented: '#f2f8ff' };
  define('gas', function (k, p) {
    var self = k.cur, id = self.id, kind = p.kind || 'rise', grp = k.g;
    var col = new T.Color(p.color || FUEL[p.fuel] || (kind === 'plume' ? FUEL.vented : kind === 'sink' ? FUEL.cold_methane : FUEL.natural_gas));
    self.pick = false;
    if (kind === 'plume') { plume(k, p, id, col); return; }
    var N = num(p.n, 240), rnd = seeded(hashId(id)), to = num(p.to, kind === 'sink' ? -1.5 : 3), dur = num(p.dur, 4);
    var ar = p.area || [-3, -2, 3, 2], al = num(p.opacity, 0.3), s0 = num(p.size0, 0.3), s1 = num(p.size, 1.2);
    var pg0 = new T.PlaneGeometry(1, 1), cg = new T.InstancedBufferGeometry();
    cg.index = pg0.index; cg.setAttribute('position', pg0.getAttribute('position')); cg.setAttribute('uv', pg0.getAttribute('uv'));
    var aC = new T.InstancedBufferAttribute(new Float32Array(N * 3), 3), aA = new T.InstancedBufferAttribute(new Float32Array(N), 1),
      aS = new T.InstancedBufferAttribute(new Float32Array(N), 1);
    aC.setUsage(T.DynamicDrawUsage); aA.setUsage(T.DynamicDrawUsage); aS.setUsage(T.DynamicDrawUsage);
    cg.setAttribute('iCenter', aC); cg.setAttribute('iA', aA); cg.setAttribute('iSize', aS);
    cg.instanceCount = N;
    k.track(cg); k.track(pg0);
    var m = new T.ShaderMaterial({
      transparent: true, depthWrite: false, depthTest: true, side: T.DoubleSide,
      uniforms: { uColor: { value: new T.Vector3(col.r, col.g, col.b) } },
      vertexShader: 'attribute vec3 iCenter; attribute float iA; attribute float iSize; varying vec2 vUv; varying float vA;\n' +
        'void main(){ vUv = uv; vA = iA; vec4 mv = modelViewMatrix * vec4(iCenter, 1.0);\n  mv.xy += position.xy * iSize; gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'uniform vec3 uColor; varying vec2 vUv; varying float vA;\n' +
        'void main(){ vec2 d = vUv - 0.5; float r2 = dot(d, d) * 4.0; float a = exp(-r2 * 3.2) * (1.0 - smoothstep(0.6, 1.0, r2));\n  gl_FragColor = vec4(uColor, vA * a); }'
    });
    k.S.mats.push(m);
    var mesh = new T.Mesh(cg, m);
    mesh.frustumCulled = false; mesh.renderOrder = 10; mesh.visible = false; mesh.userData.noPick = true; mesh.userData.keep = true;
    grp.add(mesh);
    /* each puff: when it leaves, where it goes through, where it ends */
    var kt = new Float32Array(N * 3), kp = new Float32Array(N * 9), i, u, tb, x2, z2, y2;
    function inA(x, lo, hi) { return clamp(x, lo, hi); }
    for (i = 0; i < N; i++) {
      u = (i + 0.5) / N; tb = dur * 0.45 * u;
      var th = rnd() * 6.283, rho = (0.15 + 0.85 * u) * (0.5 + 0.5 * rnd());
      x2 = inA((ar[0] + ar[2]) / 2 + Math.cos(th) * rho * (ar[2] - ar[0]) / 2, ar[0], ar[2]);
      z2 = inA((ar[1] + ar[3]) / 2 + Math.sin(th) * rho * (ar[3] - ar[1]) / 2, ar[1], ar[3]);
      var thick = (0.15 + 0.6 * u) * Math.pow(rnd(), 1.2) * Math.abs(to) * 0.35;
      if (kind === 'rise') { y2 = to - 0.15 - thick; }
      else if (kind === 'sink') { y2 = to + 0.08 + thick * 0.6; }
      else { y2 = (rnd() - 0.5) * 1.6 * rho; x2 = (rnd() - 0.5) * 2.4 * rho; z2 = (rnd() - 0.5) * 2.4 * rho; }
      kt[i * 3] = tb; kt[i * 3 + 1] = tb + dur * 0.3; kt[i * 3 + 2] = tb + dur * (0.45 + 0.35 * rho);
      kp[i * 9] = (rnd() - 0.5) * 0.06; kp[i * 9 + 1] = 0; kp[i * 9 + 2] = (rnd() - 0.5) * 0.06;
      if (kind === 'spread') { kp[i * 9 + 3] = x2 * 0.4; kp[i * 9 + 4] = y2 * 0.5 + 0.2; kp[i * 9 + 5] = z2 * 0.4; }
      else { kp[i * 9 + 3] = (rnd() - 0.5) * 0.6; kp[i * 9 + 4] = (kind === 'rise' ? to * 0.62 : to * 0.85); kp[i * 9 + 5] = (rnd() - 0.5) * 0.6; }
      kp[i * 9 + 6] = x2; kp[i * 9 + 7] = y2; kp[i * 9 + 8] = z2;
    }
    var tEnd = dur * 1.3, ph = new Float32Array(N);
    for (i = 0; i < N; i++) { ph[i] = rnd() * 6.283; }
    /* delay: it starts that many seconds after "on"; until: it fades away then (1 s) - two clouds in turn tell what one
       fuel does over time (IGF M04: cold methane sinks, then warms past -110 °C and rises) */
    var delay = num(p.delay, 0), until = p.until != null ? p.until : null;
    function put(t0) {
      var t = t0 - delay, fade = until == null ? 1 : clamp(1 - (t0 - until), 0, 1);
      var c = aC.array, a = aA.array, s = aS.array, j, q, f, e, o;
      for (j = 0; j < N; j++) {
        q = j * 3; o = j * 9;
        if (t <= kt[q]) { a[j] = 0; s[j] = 0.01; c[q] = 0; c[q + 1] = 0; c[q + 2] = 0; continue; }
        if (t < kt[q + 1]) { f = (t - kt[q]) / (kt[q + 1] - kt[q]); e = f * f * (3 - 2 * f); c[q] = kp[o] + (kp[o + 3] - kp[o]) * e; c[q + 1] = kp[o + 1] + (kp[o + 4] - kp[o + 1]) * e; c[q + 2] = kp[o + 2] + (kp[o + 5] - kp[o + 2]) * e; }
        else if (t < kt[q + 2]) { f = (t - kt[q + 1]) / (kt[q + 2] - kt[q + 1]); e = 1 - (1 - f) * (1 - f); c[q] = kp[o + 3] + (kp[o + 6] - kp[o + 3]) * e; c[q + 1] = kp[o + 4] + (kp[o + 7] - kp[o + 4]) * e; c[q + 2] = kp[o + 5] + (kp[o + 8] - kp[o + 5]) * e; }
        else { c[q] = kp[o + 6]; c[q + 1] = kp[o + 7]; c[q + 2] = kp[o + 8]; }
        var tt = Math.min(t, tEnd);
        c[q] += Math.sin(tt * 1.9 + ph[j]) * 0.045; c[q + 2] += Math.cos(tt * 1.6 + ph[j] * 1.7) * 0.045; c[q + 1] += Math.sin(tt * 1.3 + ph[j] * 2.3) * 0.03;
        f = Math.min(1, (t - kt[q]) / 0.5); a[j] = al * f * f * (3 - 2 * f) * fade;
        f = Math.min(1, (t - kt[q]) / (kt[q + 2] - kt[q] + 0.001)); s[j] = s0 + (s1 - s0) * f * f * (3 - 2 * f);
      }
      aC.needsUpdate = true; aA.needsUpdate = true; aS.needsUpdate = true;
    }
    k.state(id + '.on', 0, function (v) { mesh.visible = v > 0.5; });
    k.anim(id, function (t, on) {
      if (!on) { mesh.visible = false; return false; }
      var end = until != null ? until + 1 : tEnd + delay;
      mesh.visible = true;
      put(reduce ? (until != null ? until + 1 : tEnd + delay) : t);
      return !reduce && t < end;
    });
    k.anchor('label', [0, kind === 'sink' ? 0.5 : to * 0.5, 0]);
  });
  function plume(k, p, id, col) {
    var NP = num(p.n, 110), g = new T.BufferGeometry(), seed = new Float32Array(NP * 3), pos = new Float32Array(NP * 3), i;
    for (i = 0; i < NP; i++) {
      seed[i * 3] = (i + 0.5) / NP;
      seed[i * 3 + 1] = Math.abs((Math.sin(i * 12.9898) * 43758.5453) % 1);
      seed[i * 3 + 2] = Math.abs((Math.sin(i * 78.233) * 24634.6345) % 1);
    }
    g.setAttribute('position', new T.BufferAttribute(pos, 3));
    g.setAttribute('aSeed', new T.BufferAttribute(seed, 3));
    k.track(g);
    var wv = v3(p.wind, [-1, 0, 0]), rise = num(p.to, 5);
    var u = { uTime: { value: 0 }, uScale: { value: 400 }, uWind: { value: new T.Vector3(wv[0], wv[1], wv[2]) }, uRise: { value: rise },
      uColor: { value: new T.Vector3(col.r, col.g, col.b) }, uAlpha: { value: num(p.opacity, 0.5) } };
    var grow = num(p.size, 1);                          /* size: puffs this many times larger; opacity: their strongest alpha */
    var m = new T.ShaderMaterial({
      transparent: true, depthWrite: false, depthTest: true, uniforms: u,
      vertexShader: 'attribute vec3 aSeed; uniform float uTime; uniform float uScale; uniform vec3 uWind; uniform float uRise; uniform float uAlpha; varying float vA;\n' +
        'void main(){ float a = fract(uTime * 0.15 + aSeed.x); vec3 p = vec3(0.0);\n' +
        '  p.y += uRise * (1.0 - (1.0 - a) * (1.0 - a)); p += uWind * (a * a * 8.0 + a * 0.4);\n' +
        '  p += (aSeed.yzy - 0.5) * (0.3 + 2.8 * a) * vec3(1.0, 0.6, 1.2); float sz = 0.7 + 4.4 * a;\n' +
        '  vA = smoothstep(0.0, 0.05, a) * pow(1.0 - a, 1.35) * uAlpha; vec4 mv = modelViewMatrix * vec4(p, 1.0);\n' +
        '  gl_PointSize = sz * uScale * projectionMatrix[1][1] / max(-mv.z, 0.1); gl_Position = projectionMatrix * mv; }',
      fragmentShader: 'uniform vec3 uColor; varying float vA;\n' +
        'void main(){ vec2 c = gl_PointCoord - 0.5; float d = length(c) * 2.0; float f = 1.0 - smoothstep(0.0, 1.0, d);\n  gl_FragColor = vec4(uColor, vA * f); }'
    });
    k.S.mats.push(m);
    var pts = new T.Points(g, m);
    pts.frustumCulled = false; pts.renderOrder = 13; pts.visible = false; pts.userData.noPick = true;
    k.g.add(pts);
    k.state(id + '.on', 0, function (v) { pts.visible = v > 0.5; });
    k.anim(id, function (t, on) {
      if (!on) { pts.visible = false; return false; }
      pts.visible = true;
      u.uScale.value = (k.S.H || 400) * 0.5 * (k.S.r ? k.S.r.getPixelRatio() : 1) / 1.2 * grow;
      u.uTime.value = reduce ? 4.2 : t;
      return !reduce;
    });
    k.anchor('label', [0, rise * 0.6, 0]);
  }

  /* one arrow a -> b, a shaft and a head (the wind's way, IGF M15); color; r (the shaft's, 0.08); "<id>.on" shows it */
  define('arrow', function (k, p) {
    var a = v3(p.a), b = v3(p.b, [2, 0, 0]), r = num(p.r, 0.08), m = k.basic(p.color || '#ffffff', 1, { toneMapped: false });
    var dv = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], L = Math.sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]) || 1, h = Math.min(r * 5, L * 0.4);
    var e = [b[0] - dv[0] / L * h, b[1] - dv[1] / L * h, b[2] - dv[2] / L * h], g = k.g, self = k.cur;
    k.seg(a, e, r, m, { seg: 12, cast: false });
    k.cone(b, dv, r * 2.6, h, m, { cast: false });
    k.anchor('label', [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + r * 3, (a[2] + b[2]) / 2]);
    k.state(self.id + '.on', p.on != null ? p.on : 1, function (v) { g.visible = v > 0.5; });
  });

  /* arrows that run along a path while "<id>.on" (gas, LNG, air): path; color; spacing (1.2 m); speed (m/s, 0.8); r */
  define('flow', function (k, p) {
    var pts = p.path || [[0, 0, 0], [3, 0, 0]], self = k.cur;
    self.pick = !!p.id && p.pick === true;
    flowArrows(k, pts, self.id, { color: p.color, r: p.r, spacing: p.spacing, speed: p.speed });
    k.anchor('label', pts[Math.floor(pts.length / 2)]);
  });
  /* arrows along a polyline, shown while "<name>.on" holds - a flow part's, a hose's, the water and the concentrate in an
     inductor: color (#ffd23f), r (0.12), spacing (1.2 m), speed (m/s, 0.8) */
  var WATER = '#3b82f6', CONCENTRATE = '#c46a1c', AIR = '#5ec4b6';
  function flowArrows(k, pts, name, o) {
    var sp = num(o.spacing, 1.2), v = num(o.speed, 0.8), r = num(o.r, 0.12), i;
    var segs = [], total = 0;
    for (i = 0; i < pts.length - 1; i++) {
      var a = pts[i], b = pts[i + 1], dv = new T.Vector3(b[0] - a[0], b[1] - a[1], b[2] - a[2]), L = dv.length();
      segs.push({ a: a, d: dv.clone().normalize(), L: L, s: total }); total += L;
    }
    var n = Math.max(1, Math.floor(total / sp)), g = new T.ConeGeometry(r, r * 2.6, 14);
    var m = k.basic(o.color || '#ffd23f', 1, { toneMapped: false });
    var im = new T.InstancedMesh(k.track(g), m, n), dm = new T.Object3D(), up = new T.Vector3(0, 1, 0);
    im.userData.noPick = true; im.visible = false; im.renderOrder = 9;
    k.g.add(im); k.S.disposeLater.push(im);
    function place(t) {
      var j, s, q, sg;
      for (j = 0; j < n; j++) {
        s = ((j * sp + t * v) % total + total) % total;
        sg = segs[0];
        for (q = 0; q < segs.length; q++) { if (s >= segs[q].s) { sg = segs[q]; } }
        var o = s - sg.s;
        dm.position.set(sg.a[0] + sg.d.x * o, sg.a[1] + sg.d.y * o, sg.a[2] + sg.d.z * o);
        dm.quaternion.setFromUnitVectors(up, sg.d);
        dm.updateMatrix();
        im.setMatrixAt(j, dm.matrix);
      }
      im.instanceMatrix.needsUpdate = true;
    }
    place(0);
    k.state(name + '.on', 0, function (x) { im.visible = x > 0.5; });
    k.anim(name, function (t, on) {
      if (!on) { im.visible = false; return false; }
      im.visible = true; place(reduce ? 0 : t);
      return !reduce;
    });
    return im;
  }

  /* at once - kit3d.js is loaded at the end of the deck, before GBDeck.init reads GB_HOOKS - and again when the
     page is complete, for a figure written after this script */
  auto();
  if (d.readyState === 'loading') { d.addEventListener('DOMContentLoaded', auto); }
}(window, document));
