/* gb_scene.js - a slide's picture as a live 3D scene, drawn by the graphics chip (three.js, the 3D kit's copy).
   A picture box ([data-lt-scene]) names its scene (a course's scenes file, registered on LTStage.scenes; course-visuals/scene/examples); it draws only while its slide is up, follows the
   slide's stops and glides its camera between them. All boxes share one canvas, so a deck of many scenes holds one
   graphics context. With reduced motion a stop is settled and shown still. Later the same box takes generated clips,
   one clip a stop. Plain ES5. */
(function (w, d) {
  'use strict';
  var T = w.THREE;
  if (!T) { return; }
  var H = w.GB_HOOKS = w.GB_HOOKS || {};
  var CALM = !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var SCENES = {}, R = null;
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function approach(v, to, rate, dt) { return v < to ? Math.min(to, v + rate * dt) : Math.max(to, v - rate * dt); }
  function rnd() { return Math.random(); }

  function renderer() {
    if (R) { return R; }
    R = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    R.setPixelRatio(Math.min(w.devicePixelRatio || 1, 1.75));
    R.outputEncoding = T.sRGBEncoding;
    R.toneMapping = T.ACESFilmicToneMapping; R.toneMappingExposure = 0.95;
    R.localClippingEnabled = true;
    R.domElement.className = 'lt-canvas';
    return R;
  }

  /* a soft round dot for gas and glow */
  function softDot() {
    var c = d.createElement('canvas'); c.width = c.height = 64;
    var g = c.getContext('2d'), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.35, 'rgba(255,255,255,.55)'); r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, 64, 64);
    return new T.CanvasTexture(c);
  }
  /* bands that run along a pipe, to show the flow */
  function flowBands() {
    var c = d.createElement('canvas'); c.width = 8; c.height = 64;
    var g = c.getContext('2d'), r = g.createLinearGradient(0, 0, 0, 64);
    r.addColorStop(0, 'rgba(255,255,255,0)'); r.addColorStop(0.5, 'rgba(255,255,255,1)'); r.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = r; g.fillRect(0, 0, 8, 64);
    var t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping;
    return t;
  }

  /* the building blocks every scene uses */
  function kit(scene) {
    var K = {};
    K.mat = function (col, o) {
      var p = { color: col, roughness: 0.6, metalness: 0 }, k;
      for (k in (o || {})) { p[k] = o[k]; }
      return new T.MeshStandardMaterial(p);
    };
    K.add = function (obj, x, y, z, parent) { obj.position.set(x || 0, y || 0, z || 0); (parent || scene).add(obj); return obj; };
    K.box = function (wd, ht, dp, mat, x, y, z, parent) { return K.add(new T.Mesh(new T.BoxGeometry(wd, ht, dp), mat), x, y, z, parent); };
    K.edges = function (mesh, col, op) {
      var e = new T.LineSegments(new T.EdgesGeometry(mesh.geometry), new T.LineBasicMaterial({ color: col || 0x53A7DB, transparent: true, opacity: op || 0.4 }));
      e.position.copy(mesh.position); e.rotation.copy(mesh.rotation); e.scale.copy(mesh.scale); (mesh.parent || scene).add(e); return e;
    };
    /* a rod from a to b; grow(f) draws the first part of it */
    K.rod = function (a, b, r, mat, parent) {
      var g = new T.CylinderGeometry(r, r, 1, 14); g.translate(0, 0.5, 0);
      var m = new T.Mesh(g, mat), dir = new T.Vector3().subVectors(b, a), len = dir.length();
      m.position.copy(a); m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), dir.normalize()); m.scale.y = len;
      (parent || scene).add(m);
      m.grow = function (f) { m.scale.y = Math.max(0.0001, len * f); m.visible = f > 0.001; };
      return m;
    };
    /* sky, ground and a sun, in the brand's light */
    K.lights = function (sky, ground, hemi, sunCol, sunI, sunAt) {
      scene.add(new T.HemisphereLight(sky || 0xcfe3ff, ground || 0x0a2463, hemi || 0.8));
      var s = new T.DirectionalLight(sunCol || 0xffffff, sunI || 1.1); s.position.fromArray(sunAt || [-4, 9, 7]); scene.add(s);
      return s;
    };
    /* the space cut open: floor, back wall and the walls named; thin blue edges and a deck grid */
    K.room = function (wd, ht, dp, col, walls, grid) {
      var g = new T.Group(); scene.add(g);
      function slab(sw, sh, sd, c, x, y, z) { var m = K.box(sw, sh, sd, K.mat(c, { roughness: 0.92 }), x, y, z, g); K.edges(m, 0x53A7DB, 0.4); return m; }
      slab(wd, 0.16, dp, col[0], 0, -0.08, 0);
      if (walls.indexOf('back') >= 0) { slab(wd, ht, 0.16, col[1], 0, ht / 2, -dp / 2); }
      if (walls.indexOf('right') >= 0) { slab(0.16, ht, dp, col[2] || col[1], wd / 2, ht / 2, 0); }
      if (walls.indexOf('left') >= 0) { slab(0.16, ht, dp, col[2] || col[1], -wd / 2, ht / 2, 0); }
      if (grid !== false) {
        var gr = new T.GridHelper(Math.max(wd, dp), Math.round(Math.max(wd, dp) * 2), 0x53A7DB, 0x53A7DB);
        gr.position.y = 0.005; gr.scale.set(wd / Math.max(wd, dp), 1, dp / Math.max(wd, dp));
        gr.material.transparent = true; gr.material.opacity = 0.15; g.add(gr);
      }
      return g;
    };
    return K;
  }

  /* gas, vapour or mist: soft particles that rise or sink, spread along a ceiling or a deck, drift and can be drawn
     out through a point. o: at, n, size, color [r,g,b], alpha, buoy, drag, jit, wind [x,z], vel(), life [a,b],
     box {x0,x1,y0,y1,z0,z1}, spread (along a ceiling or deck), tube {y,z,r,x0} (held inside a pipe), normal (blending) */
  function Gas(scene, o) {
    var N = o.n || 500, P = new Float32Array(N * 3), C = new Float32Array(N * 3), V = new Float32Array(N * 3), L = new Float32Array(N), M = new Float32Array(N), X = new Float32Array(N);
    for (var q0 = 0; q0 < N; q0++) { P[q0 * 3 + 1] = -999; }
    var geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.BufferAttribute(P, 3)); geo.setAttribute('color', new T.BufferAttribute(C, 3));
    var pts = new T.Points(geo, new T.PointsMaterial({ size: o.size || 0.6, map: softDot(), vertexColors: true, transparent: true, depthWrite: false,
      blending: o.normal ? T.NormalBlending : T.AdditiveBlending, sizeAttenuation: true }));
    pts.frustumCulled = false; scene.add(pts);
    var col = o.color || [1, 0.45, 0.4], alpha = o.alpha || 0.16, b = o.box, rate = 0, carry = 0, next = 0, pullP = null, pullK = 0;
    var at = o.at.clone();
    function spawn() {
      for (var j = 0; j < N; j++) {
        var q = (next + j) % N;
        if (L[q] > 0) { continue; }
        next = q + 1; L[q] = 0.001; X[q] = 0;
        M[q] = o.life ? o.life[0] + rnd() * (o.life[1] - o.life[0]) : 8;
        var s = o.jitAt || 0.08, v = o.vel ? o.vel() : [0, 0.6, 0];
        P[q * 3] = at.x + (rnd() - 0.5) * s; P[q * 3 + 1] = at.y + (rnd() - 0.5) * s; P[q * 3 + 2] = at.z + (rnd() - 0.5) * s;
        V[q * 3] = v[0]; V[q * 3 + 1] = v[1]; V[q * 3 + 2] = v[2];
        return;
      }
    }
    var G = {
      pts: pts, at: at,
      rate: function (r) { rate = r; },
      level: function () { var n = 0; for (var j = 0; j < N; j++) { if (L[j] > 0) { n++; } } return n / N; },
      clear: function () { for (var j = 0; j < N; j++) { L[j] = 0; C[j * 3] = C[j * 3 + 1] = C[j * 3 + 2] = 0; P[j * 3 + 1] = -999; } geo.attributes.color.needsUpdate = true; geo.attributes.position.needsUpdate = true; },
      pull: function (p, k) { pullP = p; pullK = k; },
      tick: function (dt) {
        carry += rate * dt; while (carry >= 1) { spawn(); carry -= 1; }
        var buoy = o.buoy || 0, drag = Math.pow(o.drag || 0.98, dt * 60), jit = o.jit || 0.8, wx = o.wind ? o.wind[0] : 0, wz = o.wind ? o.wind[1] : 0, sp = o.spread || 0.5, tb = o.tube;
        for (var j = 0; j < N; j++) {
          var i3 = j * 3;
          if (L[j] <= 0) { continue; }
          L[j] += dt;
          if (L[j] >= M[j]) { L[j] = 0; C[i3] = C[i3 + 1] = C[i3 + 2] = 0; P[i3 + 1] = -999; continue; }
          var x = P[i3], y = P[i3 + 1], z = P[i3 + 2], vx = V[i3], vy = V[i3 + 1], vz = V[i3 + 2];
          vy += buoy * dt; vx += ((rnd() - 0.5) * jit + wx) * dt; vy += (rnd() - 0.5) * jit * 0.4 * dt; vz += ((rnd() - 0.5) * jit + wz) * dt;
          if (pullP && pullK > 0) {
            var dx = pullP.x - x, dy = pullP.y - y, dz = pullP.z - z, dl = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.001;
            vx += dx / dl * pullK * dt; vy += dy / dl * pullK * dt; vz += dz / dl * pullK * dt;
            if (dl < 0.6) { X[j] = 1; }
          }
          vx *= drag; vy *= drag; vz *= drag;
          x += vx * dt; y += vy * dt; z += vz * dt;
          if (tb) {
            var ty = y - tb.y, tz = z - tb.z, tr = Math.sqrt(ty * ty + tz * tz);
            if (tr > tb.r) { y = tb.y + ty / tr * tb.r; z = tb.z + tz / tr * tb.r; vy *= -0.3; vz *= -0.3; }
            if (x < tb.x0) { L[j] = M[j] - 0.4; }
          }
          if (b) {
            if (y > b.y1) { y = b.y1; vy = -Math.abs(vy) * 0.15; vx += (rnd() - 0.5) * sp; vz += (rnd() - 0.5) * sp; }
            if (y < b.y0) { y = b.y0; vy = Math.abs(vy) * 0.15; vx += (rnd() - 0.5) * sp; vz += (rnd() - 0.5) * sp; }
            if (!X[j]) { x = clamp(x, b.x0, b.x1); z = clamp(z, b.z0, b.z1); }
          }
          P[i3] = x; P[i3 + 1] = y; P[i3 + 2] = z; V[i3] = vx; V[i3 + 1] = vy; V[i3 + 2] = vz;
          var a = Math.min(1, L[j] / 0.5) * Math.min(1, (M[j] - L[j]) / 1.2) * alpha;
          if (X[j]) { a *= 0.6; if (L[j] < M[j] - 0.5) { L[j] = M[j] - 0.5; } }
          C[i3] = a * col[0]; C[i3 + 1] = a * col[1]; C[i3 + 2] = a * col[2];
        }
        geo.attributes.position.needsUpdate = true; geo.attributes.color.needsUpdate = true;
      }
    };
    return G;
  }

  function Stage(box, def) {
    var scene = new T.Scene(), cam = new T.PerspectiveCamera(40, 1, 0.1, 200);
    var still = CALM && !!def.still;
    var api = { T: T, scene: scene, cam: cam, box: box, t: 0, calm: CALM && !def.still, still: still, softDot: softDot, flowBands: flowBands, ease: ease, clamp: clamp,
                approach: approach, rnd: rnd, kit: kit(scene), Gas: function (o) { return Gas(scene, o); } };
    var S = (def.build || def)(api);
    /* colours are written as the brand's sRGB values; the renderer works in linear light */
    scene.traverse(function (o) {
      [].concat(o.material || []).forEach(function (m) { if (m.userData.lin) { return; } m.userData.lin = true; if (m.color) { m.color.convertSRGBToLinear(); } if (m.emissive) { m.emissive.convertSRGBToLinear(); } });
    });
    var pos = new T.Vector3(), look = new T.Vector3(), from = null, to = null, tw = 1, k = 0, running = false, last = 0, raf = 0;
    var tags = [].slice.call(box.querySelectorAll('[data-tag]')), v3 = new T.Vector3();
    function mine() { return R && R.domElement.parentNode === box; }
    function size() {
      var W = box.clientWidth, Hh = box.clientHeight;
      if (!W || !Hh) { return; }
      if (mine()) { R.setSize(W, Hh, false); }
      /* the scene keeps its width: a box narrower than 3:2 shows more height, never less of the sides */
      var v = (def.fov || 40) * Math.PI / 180, hw = Math.tan(v / 2) * 1.5;
      cam.aspect = W / Hh; cam.fov = Math.max(v, 2 * Math.atan(hw / cam.aspect)) * 180 / Math.PI; cam.updateProjectionMatrix();
      if (still && running) { draw(0); }
    }
    function aim(v, jump) {
      var to2 = { p: new T.Vector3().fromArray(v.pos), a: new T.Vector3().fromArray(v.at) };
      if (jump || CALM) { pos.copy(to2.p); look.copy(to2.a); tw = 1; return; }
      from = { p: pos.clone(), a: look.clone() }; to = to2; tw = 0;
    }
    function draw(dt) {
      if (!mine()) { return; }
      api.t += dt;
      if (tw < 1) { tw = Math.min(1, tw + dt / 1.6); var e = ease(tw); pos.lerpVectors(from.p, to.p, e); look.lerpVectors(from.a, to.a, e); }
      var sx = CALM ? 0 : Math.sin(api.t * 0.23) * 0.14 * (def.sway || 1), sy = CALM ? 0 : Math.sin(api.t * 0.17) * 0.06 * (def.sway || 1);
      cam.position.set(pos.x + sx, pos.y + sy, pos.z); cam.lookAt(look);
      S.tick(dt, api.t);
      R.render(scene, cam);
      /* the name tags follow their part on the screen */
      var W = box.clientWidth, Hh = box.clientHeight;
      tags.forEach(function (el) {
        var p = S.anchors[el.getAttribute('data-tag')]; if (!p) { return; }
        v3.copy(p).project(cam);
        el.style.transform = 'translate(' + ((v3.x + 1) / 2 * W).toFixed(1) + 'px,' + ((1 - v3.y) / 2 * Hh).toFixed(1) + 'px)';
      });
    }
    function frame(now) {
      raf = 0;
      var dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
      draw(dt);
      if (running && !still) { raf = w.requestAnimationFrame(frame); }
    }
    /* still: play the stop for a few seconds out of sight, then show where it settled */
    function settle() { for (var i = 0; i < 200; i++) { api.t += 1 / 30; S.tick(1 / 30, api.t); } draw(0); }
    var me = {
      go: function (n) {
        k = n; aim(S.views[Math.min(n + 1, S.views.length - 1)]); S.go(n);
        tags.forEach(function (el) { el.classList.toggle('on', (' ' + el.getAttribute('data-at') + ' ').indexOf(' ' + n + ' ') >= 0); });
        if (still && running) { settle(); }
      },
      start: function () {
        if (running) { return; }
        var r = renderer();
        if (r.domElement.parentNode !== box) { box.insertBefore(r.domElement, box.firstChild); }
        running = true; last = 0; size(); S.reset(); aim(S.views[0], true); me.go(k);
        if (!still && !raf) { raf = w.requestAnimationFrame(frame); }
      },
      stop: function () { running = false; if (raf) { w.cancelAnimationFrame(raf); raf = 0; } },
      step: function () { return k; }
    };
    if (w.ResizeObserver) { new w.ResizeObserver(size).observe(box); } else { w.addEventListener('resize', size); }
    aim(S.views[0], true);
    return me;
  }

  /* every picture box with a scene gets its stage; the slide's own hooks start and stop it */
  function boot() {
    [].forEach.call(d.querySelectorAll('[data-lt-scene]'), function (box) {
      var def = SCENES[box.getAttribute('data-lt-scene')], slide = box.closest('.slide');
      if (!def || !slide || box.__lt) { return; }
      var st;
      try { st = new Stage(box, def); } catch (e) { box.classList.add('lt-no3d'); if (w.console) { w.console.warn('lt_stage', e); } return; }
      box.__lt = st;
      var old = H[slide.id] || {};
      H[slide.id] = {
        enter: function () { st.start(); if (old.enter) { old.enter(); } },
        leave: function () { st.stop(); if (old.leave) { old.leave(); } },
        step: old.step
      };
    });
  }
  w.LTStage = { scenes: SCENES, boot: boot, THREE: T };
})(window, document);
