/* m01_scenes.js - the reference deck's scenes (IGF ships, module 1) for gb_scene.js: what a slide's picture box can name
   (data-lt-scene), each a short story told in stops: the
   camera views (the first is where it opens), what each stop does and what moves on its own. Plain ES5. */
(function (w, d) {
  'use strict';
  var L = w.LTStage;
  if (!L) { return; }
  var T = L.THREE, SCENES = L.scenes;

  /* ------------------------------------------------------------------ the safety system: detect, shut down, ventilate */
  SCENES.safety = function (A) {
    var scene = A.scene, NAVY = 0x0A2463, BLUE = 0x53A7DB;
    scene.add(new T.HemisphereLight(0xcfe3ff, 0x0a2463, 0.8));
    var sun = new T.DirectionalLight(0xffffff, 1.1); sun.position.set(-4, 9, 7); scene.add(sun);
    var alarm = new T.PointLight(0xff3b30, 0, 9, 1.6); alarm.position.set(-0.8, 3.5, -1.7); scene.add(alarm);

    /* the space, cut open to the front and the left */
    function slab(wd, ht, dp, col, x, y, z) {
      var m = new T.Mesh(new T.BoxGeometry(wd, ht, dp), new T.MeshStandardMaterial({ color: col, roughness: 0.92, metalness: 0.05 }));
      m.position.set(x, y, z); scene.add(m);
      var e = new T.LineSegments(new T.EdgesGeometry(m.geometry), new T.LineBasicMaterial({ color: BLUE, transparent: true, opacity: 0.45 }));
      e.position.copy(m.position); scene.add(e);
      return m;
    }
    slab(8.6, 0.16, 5.2, 0x15306a, -0.2, -0.08, 0);
    slab(8.6, 4.6, 0.16, 0x1a3a7c, -0.2, 2.3, -2.6);
    slab(0.16, 4.6, 5.2, 0x183676, 4.0, 2.3, 0);
    var grid = new T.GridHelper(8.6, 17, BLUE, BLUE); grid.position.set(-0.2, 0.005, 0);
    grid.material.transparent = true; grid.material.opacity = 0.16; scene.add(grid);

    var steel = new T.MeshStandardMaterial({ color: 0xc9d6e4, roughness: 0.45, metalness: 0 });
    var dark = new T.MeshStandardMaterial({ color: 0x6f84a3, roughness: 0.6, metalness: 0 });
    /* the gas pipe along the back, with the flow showing through its skin */
    var PY = 0.75, PZ = -1.55;
    var pipe = new T.Mesh(new T.CylinderGeometry(0.17, 0.17, 8.2, 28, 1, true), new T.MeshStandardMaterial({ color: 0xbfd2e6, roughness: 0.25, metalness: 0.5, transparent: true, opacity: 0.38, side: T.DoubleSide }));
    pipe.rotation.z = Math.PI / 2; pipe.position.set(-0.2, PY, PZ); scene.add(pipe);
    var bands = A.flowBands(); bands.repeat.set(1, 9);
    var core = new T.Mesh(new T.CylinderGeometry(0.1, 0.1, 8.2, 16, 1, true), new T.MeshBasicMaterial({ color: BLUE, map: bands, transparent: true, opacity: 0.95, blending: T.AdditiveBlending, depthWrite: false }));
    core.rotation.z = Math.PI / 2; core.position.copy(pipe.position); scene.add(core);
    [-3.6, 0.55, 0.85, 3.4].forEach(function (x) {
      var f = new T.Mesh(new T.CylinderGeometry(0.27, 0.27, 0.08, 28), steel); f.rotation.z = Math.PI / 2; f.position.set(x, PY, PZ); scene.add(f);
    });
    [-3, 3].forEach(function (x) {
      var s = new T.Mesh(new T.BoxGeometry(0.12, PY - 0.17, 0.3), dark); s.position.set(x, (PY - 0.17) / 2, PZ); scene.add(s);
    });
    /* the master gas valve and its handwheel */
    var VX = -1.6;
    var body = new T.Mesh(new T.SphereGeometry(0.3, 32, 20), new T.MeshStandardMaterial({ color: 0xa9bacb, roughness: 0.4, metalness: 0, emissive: 0xff3b30, emissiveIntensity: 0 }));
    body.scale.set(1.25, 1, 1); body.position.set(VX, PY, PZ); scene.add(body);
    var stem = new T.Mesh(new T.CylinderGeometry(0.04, 0.04, 0.6, 12), steel); stem.position.set(VX, PY + 0.55, PZ); scene.add(stem);
    var wheel = new T.Group(); wheel.position.set(VX, PY + 0.86, PZ); scene.add(wheel);
    var rim = new T.Mesh(new T.TorusGeometry(0.34, 0.045, 14, 48), new T.MeshStandardMaterial({ color: 0xd94f45, roughness: 0.45, metalness: 0.3 }));
    rim.rotation.x = Math.PI / 2; wheel.add(rim);
    for (var i = 0; i < 3; i++) { var sp = new T.Mesh(new T.BoxGeometry(0.66, 0.035, 0.05), steel); sp.rotation.y = i * Math.PI / 3; wheel.add(sp); }
    /* the gas detector, high on the back wall */
    var det = new T.Group(); det.position.set(-0.8, 3.75, -2.47); scene.add(det);
    var dbox = new T.Mesh(new T.BoxGeometry(0.46, 0.34, 0.18), new T.MeshStandardMaterial({ color: 0xe8eef5, roughness: 0.5 })); det.add(dbox);
    var head = new T.Mesh(new T.CylinderGeometry(0.1, 0.12, 0.2, 20), dark); head.position.set(0, -0.26, 0.02); det.add(head);
    var led = new T.Mesh(new T.SphereGeometry(0.055, 16, 12), new T.MeshBasicMaterial({ color: 0x4fd6a0 })); led.position.set(0.13, 0.07, 0.1); det.add(led);
    var halo = new T.Sprite(new T.SpriteMaterial({ map: A.softDot(), color: 0xff3b30, transparent: true, opacity: 0, blending: T.AdditiveBlending, depthWrite: false }));
    halo.scale.set(1.4, 1.4, 1); halo.position.set(-0.67, 3.82, -2.3); scene.add(halo);
    /* the fan in the side wall: the rotor turns about its own hub */
    var FAN = new T.Vector3(3.9, 3.05, -0.7);
    var fan = new T.Group(); fan.position.copy(FAN); fan.rotation.y = -Math.PI / 2; scene.add(fan);
    var duct = new T.Mesh(new T.TorusGeometry(0.78, 0.09, 16, 56), steel); fan.add(duct);
    var shroud = new T.Mesh(new T.CylinderGeometry(0.78, 0.78, 0.22, 48, 1, true), new T.MeshStandardMaterial({ color: 0x23407f, roughness: 0.8, side: T.DoubleSide }));
    shroud.rotation.x = Math.PI / 2; shroud.position.z = -0.1; fan.add(shroud);
    var rotor = new T.Group(); fan.add(rotor);
    var hub = new T.Mesh(new T.CylinderGeometry(0.15, 0.15, 0.16, 24), steel); hub.rotation.x = Math.PI / 2; rotor.add(hub);
    var bladeMat = new T.MeshStandardMaterial({ color: BLUE, roughness: 0.4, metalness: 0.1, emissive: 0x0a2463, emissiveIntensity: 0.4 });
    for (var b = 0; b < 5; b++) {
      var g = new T.BoxGeometry(0.22, 0.6, 0.03); g.rotateY(0.5); g.translate(0, 0.42, 0);
      var bl = new T.Mesh(g, bladeMat); bl.rotation.z = b * Math.PI * 2 / 5; rotor.add(bl);
    }

    /* the gas: soft particles that rise from the leaking flange and gather under the deckhead */
    var N = 700, P = new Float32Array(N * 3), C = new Float32Array(N * 3), V = new Float32Array(N * 3), L = new Float32Array(N), M = new Float32Array(N), X = new Float32Array(N);
    var geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.BufferAttribute(P, 3)); geo.setAttribute('color', new T.BufferAttribute(C, 3));
    var gas = new T.Points(geo, new T.PointsMaterial({ size: 0.7, map: A.softDot(), vertexColors: true, transparent: true, depthWrite: false, blending: T.AdditiveBlending, sizeAttenuation: true }));
    gas.frustumCulled = false; scene.add(gas);
    var LEAK = new T.Vector3(0.7, PY + 0.1, PZ + 0.12), next = 0, carry = 0;
    function spawn() {
      for (var j = 0; j < N; j++) {
        var q = (next + j) % N;
        if (L[q] <= 0) {
          next = q + 1; L[q] = 0.001; M[q] = 9 + Math.random() * 7; X[q] = 0;
          P[q * 3] = LEAK.x + (Math.random() - 0.5) * 0.1; P[q * 3 + 1] = LEAK.y; P[q * 3 + 2] = LEAK.z + (Math.random() - 0.5) * 0.1;
          V[q * 3] = (Math.random() - 0.5) * 0.5; V[q * 3 + 1] = 0.5 + Math.random() * 0.5; V[q * 3 + 2] = 0.25 + Math.random() * 0.45;
          return;
        }
      }
    }

    var st = {};
    var read = A.box.querySelector('.lt-read'), num = read && read.querySelector('[data-lel]'), bar = read && read.querySelector('.bar i'), chip = read && read.querySelector('.st');
    function say(text, kind) { if (chip && chip.textContent !== text) { chip.textContent = text; chip.className = 'st ' + kind; } }
    var S = {
      anchors: { det: new T.Vector3(-0.8, 4.05, -2.4), valve: new T.Vector3(VX, PY + 1.05, PZ), fan: new T.Vector3(FAN.x - 0.1, FAN.y + 0.95, FAN.z), leak: LEAK },
      views: [
        { pos: [-5.6, 4.6, 8.4], at: [0.2, 1.8, -0.6] },
        { pos: [-3.4, 3.2, 4.6], at: [-0.5, 2.9, -1.9] },
        { pos: [-3.4, 2.5, 3.1], at: [-1.1, 1.0, -1.4] },
        { pos: [-1.6, 3.1, 4.4], at: [2.9, 2.5, -0.7] }
      ],
      reset: function () {
        for (var j = 0; j < N; j++) { L[j] = 0; C[j * 3] = C[j * 3 + 1] = C[j * 3 + 2] = 0; }
        st = { k: 0, lel: 0, goal: 0, leak: true, open: 1, shut: false, fan: 0.12, fanGoal: 0.12, spin: 0 };
      },
      go: function (k) {
        st.k = k;
        if (k === 0) { st.goal = 22; st.leak = true; st.shut = false; st.fanGoal = 0.12; }
        if (k === 1) { st.goal = 40; st.leak = !st.shut; st.fanGoal = 0.12; }
        if (k === 2) { st.goal = 0; st.leak = false; st.shut = true; st.fanGoal = 1; }
        if (A.calm) { if (k === 2) { for (var j = 0; j < N; j++) { L[j] = 0; C[j * 3] = C[j * 3 + 1] = C[j * 3 + 2] = 0; } } st.lel = k === 2 ? 0 : st.goal; if (k > 0) { st.shut = true; st.leak = false; } }
      },
      tick: function (dt, t) {
        /* the reading, the shutdown at 40 % LEL, the fan */
        st.lel = A.approach(st.lel, st.goal, st.k === 2 ? 7 : 5.5, dt);
        if (st.k === 1 && st.lel >= 40 && !st.shut) { st.shut = true; st.leak = false; }
        st.open = A.approach(st.open, st.shut ? 0 : 1, 0.8, dt);
        st.fan = A.approach(st.fan, st.fanGoal, 0.6, dt);
        wheel.rotation.y = (1 - st.open) * Math.PI * 1.5;
        body.material.emissiveIntensity = (1 - st.open) * 0.55;
        bands.offset.y -= dt * 2.2 * st.open;
        core.material.opacity = 0.25 + 0.7 * st.open;
        rotor.rotation.z -= dt * (A.calm ? 0 : st.fan * 16);
        var hot = st.lel >= 20, pulse = hot ? 0.55 + 0.45 * Math.sin(t * 7) : 0;
        led.material.color.setHex(hot ? 0xff3b30 : 0x4fd6a0).convertSRGBToLinear();
        alarm.intensity = hot ? 1.2 + 1.6 * pulse : A.approach(alarm.intensity, 0, 4, dt);
        halo.material.opacity = hot ? 0.35 + 0.5 * pulse : 0;
        if (num) { num.textContent = Math.round(st.lel); bar.style.width = (st.lel / 50 * 100) + '%'; }
        if (st.k === 2) { say(st.lel > 0.5 ? 'Ventilating' : 'Clear', st.lel > 0.5 ? 'vent' : 'ok'); }
        else if (st.shut) { say('Gas valve closed', 'alarm'); }
        else if (hot) { say('Alarm', 'alarm'); }
        else { say('Normal', 'ok'); }
        if (read) { read.classList.toggle('hot', hot && st.k < 2); }

        /* the gas */
        if (st.leak && !A.calm) { carry += dt * 38; while (carry >= 1) { spawn(); carry -= 1; } }
        if (A.calm && st.k < 2 && !st.seeded && (st.seeded = true)) { for (var s = 0; s < 260; s++) { spawn(); var q = (next - 1 + N) % N; L[q] = 3; P[q * 3] = -2.4 + Math.random() * 4.2; P[q * 3 + 1] = 2.6 + Math.random() * 1.6; P[q * 3 + 2] = -2.3 + Math.random() * 2.4; } }
        var pull = st.fan > 0.5 ? (st.fan - 0.5) * 2 : 0;
        for (var j = 0; j < N; j++) {
          if (L[j] <= 0) { continue; }
          var o = j * 3, x = P[o], y = P[o + 1], z = P[o + 2];
          if (!A.calm) {
            L[j] += dt;
            var vx = V[o], vy = V[o + 1], vz = V[o + 2];
            vy += 0.42 * dt; vx += (Math.random() - 0.5) * 0.9 * dt; vz += (Math.random() - 0.5) * 0.9 * dt;
            if (pull > 0) {
              var dx = FAN.x - x, dy = FAN.y - y, dz = FAN.z - z, dl = Math.sqrt(dx * dx + dy * dy + dz * dz) + 0.001;
              vx += dx / dl * 3.2 * pull * dt; vy += dy / dl * 3.2 * pull * dt; vz += dz / dl * 3.2 * pull * dt;
              if (dl < 0.75) { X[j] = 1; }
            }
            vx *= 0.985; vy *= 0.97; vz *= 0.985;
            x += vx * dt; y += vy * dt; z += vz * dt;
            if (y > 4.35) { y = 4.35; vy = -Math.abs(vy) * 0.2; vx += (Math.random() - 0.5) * 0.6; vz += (Math.random() - 0.5) * 0.6; }
            if (X[j] === 0) { x = A.clamp(x, -4.3, 3.75); } else { x += 1.5 * dt; }
            z = A.clamp(z, -2.4, 2.3);
            P[o] = x; P[o + 1] = y; P[o + 2] = z; V[o] = vx; V[o + 1] = vy; V[o + 2] = vz;
            if (L[j] > M[j] && pull === 0) { L[j] = M[j] * 0.6; }
            if (X[j] && x > 4.3) { L[j] = 0; }
          }
          var a = Math.min(1, L[j] / 0.6) * (X[j] ? Math.max(0, (4.4 - x) / 0.7) : 1) * 0.16;
          if (pull > 0 && !X[j]) { a *= A.clamp(st.lel / 30, 0.25, 1); }
          C[o] = a; C[o + 1] = a * 0.45; C[o + 2] = a * 0.4;
          if (L[j] <= 0) { C[o] = C[o + 1] = C[o + 2] = 0; }
        }
        if (st.k === 2 && st.lel < 0.5) { for (var e2 = 0; e2 < N; e2++) { if (L[e2] > 0 && !X[e2]) { X[e2] = 1; } } }
        geo.attributes.position.needsUpdate = true; geo.attributes.color.needsUpdate = true;
      }
    };
    S.reset();
    return S;
  };


  var BLUE = 0x53A7DB, NAVY = 0x0A2463;
  function V3(x, y, z) { return new T.Vector3(x, y, z); }

  /* ------------------------------------------------------------------ the cold cloud: what a gas leak looks like */
  SCENES.cloud = { still: true, fov: 38, build: function (A) {
    var K = A.kit, rnd = A.rnd;
    K.lights(0xe3ecff, 0x2b3d66, 0.95, 0xfff0dc, 1.25, [-7, 6, 5]);
    var deck = K.box(16, 0.2, 10, K.mat(0x55688a, { roughness: 0.85 }), 0, -0.1, 0); K.edges(deck, BLUE, 0.3);
    var grid = new T.GridHelper(16, 32, BLUE, BLUE); grid.material.transparent = true; grid.material.opacity = 0.12; grid.position.y = 0.01; A.scene.add(grid);
    var bulwark = K.box(16, 1.1, 0.18, K.mat(0x8b9cb6), 0, 0.55, -5); K.edges(bulwark, BLUE, 0.35);
    var rail = K.mat(0xc9d6e4, { roughness: 0.4 });
    K.box(16, 0.06, 0.06, rail, 0, 1.6, -5);
    for (var i = -7; i <= 7; i += 1.75) { K.box(0.06, 0.5, 0.06, rail, i, 1.35, -5); }
    var steel = K.mat(0xc9d6e4, { roughness: 0.45 }), pipeM = K.mat(0xd9e2ec, { roughness: 0.35 });
    var pipe = K.add(new T.Mesh(new T.CylinderGeometry(0.16, 0.16, 15, 24), pipeM), 0, 0.7, -3); pipe.rotation.z = Math.PI / 2;
    [-0.06, 0.06].forEach(function (x) { var f = K.add(new T.Mesh(new T.CylinderGeometry(0.3, 0.3, 0.1, 28), steel), x, 0.7, -3); f.rotation.z = Math.PI / 2; });
    [-5, 5].forEach(function (x) { K.box(0.14, 0.55, 0.36, K.mat(0x5a6f8e), x, 0.28, -3); });
    /* frost on the flange */
    var frost = K.add(new T.Mesh(new T.TorusGeometry(0.32, 0.06, 10, 32), K.mat(0xffffff, { roughness: 1, emissive: 0xbfd8ff, emissiveIntensity: 0.25 })), 0, 0.7, -3);
    frost.rotation.y = Math.PI / 2;
    /* the cold vapour sinks, rolls along the deck and drifts with the air */
    var gas = A.Gas({ at: V3(0.15, 0.62, -2.82), n: 1100, size: 1.25, color: [0.9, 0.94, 1], alpha: 0.075, buoy: -0.32, drag: 0.975, jit: 0.7,
      wind: [0.12, 0.05], spread: 1.1, life: [11, 16], vel: function () { return [(rnd() - 0.5) * 0.6, -0.15, 0.55 + rnd() * 0.5]; },
      box: { x0: -7.5, x1: 7.5, y0: 0.14, y1: 4, z0: -4.6, z1: 4.6 } });
    var on = false;
    return {
      anchors: { cloud: V3(0.6, 1.1, -1.2), gas: V3(2.4, 0.5, 1.6) },
      views: [{ pos: [-8.5, 6, 10.5], at: [0.5, 0.4, -0.6] }, { pos: [-8.5, 6, 10.5], at: [0.5, 0.4, -0.6] }, { pos: [-6.2, 3.6, 7.6], at: [0.9, 0.3, -0.6] }],
      reset: function () { gas.clear(); on = false; },
      go: function (k) { on = k >= 1; gas.rate(on ? 85 : 0); if (!on) { gas.clear(); } },
      tick: function (dt) { gas.tick(dt); }
    };
  } };

  /* ------------------------------------------------------------------ the vent mast and its 10 m zone */
  SCENES.vent = { still: true, fov: 36, build: function (A) {
    var K = A.kit, rnd = A.rnd;
    K.lights(0xdfe9ff, 0x223a6e, 0.9, 0xffffff, 1.1, [-10, 16, 12]);
    var deck = K.box(36, 0.4, 14, K.mat(0x4d6185, { roughness: 0.9 }), 3, -0.2, 0); K.edges(deck, BLUE, 0.3);
    var grid = new T.GridHelper(36, 36, BLUE, BLUE); grid.material.transparent = true; grid.material.opacity = 0.1; grid.position.set(3, 0.01, 0); grid.scale.z = 14 / 36; A.scene.add(grid);
    /* the accommodation, its air intake and door */
    var acc = K.box(8, 9, 10, K.mat(0xe9eef5, { roughness: 0.7 }), 13, 4.5, 0); K.edges(acc, BLUE, 0.35);
    var dark = K.mat(0x1d2d4f, { roughness: 0.6 });
    for (var r = 0; r < 3; r++) { for (var c = -3; c <= 3; c += 1.5) { K.box(0.06, 0.6, 0.9, dark, 8.98, 3.2 + r * 2, c); } }
    var intake = K.box(0.12, 1.2, 1.8, K.mat(0x2a3f66, { emissive: 0x4FD6A0, emissiveIntensity: 0 }), 8.94, 6.2, -3.6); K.edges(intake, 0x4FD6A0, 0.9);
    for (var s = 0; s < 5; s++) { K.box(0.14, 0.06, 1.7, K.mat(0x9fb3c8), 8.9, 5.75 + s * 0.22, -3.6); }
    var door = K.box(0.1, 2.2, 1.1, K.mat(0x52688d, { emissive: 0x4FD6A0, emissiveIntensity: 0 }), 8.95, 1.1, 3.2);
    /* the vent mast */
    var mast = K.mat(0xd3dde8, { roughness: 0.4 });
    K.add(new T.Mesh(new T.CylinderGeometry(0.22, 0.28, 11, 20), mast), -6, 5.5, 0);
    K.add(new T.Mesh(new T.CylinderGeometry(0.4, 0.3, 0.5, 20), mast), -6, 11.15, 0);
    [3.5, 7.5].forEach(function (y) { K.add(new T.Mesh(new T.TorusGeometry(0.5, 0.04, 8, 28), mast), -6, y, 0).rotation.x = Math.PI / 2; });
    var O = V3(-6, 11.45, 0), I = V3(8.9, 6.2, -3.6);
    var plume = A.Gas({ at: O, n: 500, size: 1, color: [0.78, 0.88, 1], alpha: 0.09, buoy: 0.35, drag: 0.985, jit: 0.6, wind: [0.25, 0], life: [5, 8],
      vel: function () { return [0.3 + rnd() * 0.3, 1.4 + rnd() * 0.6, (rnd() - 0.5) * 0.4]; } });
    plume.rate(45);
    /* the 10 m zone around the outlet, and the line to the intake */
    var zone = new T.Group(); zone.position.copy(O); A.scene.add(zone);
    zone.add(new T.Mesh(new T.SphereGeometry(10, 48, 32), new T.MeshBasicMaterial({ color: BLUE, transparent: true, opacity: 0.09, depthWrite: false, side: T.DoubleSide })));
    zone.add(new T.LineSegments(new T.WireframeGeometry(new T.SphereGeometry(10, 18, 10)), new T.LineBasicMaterial({ color: BLUE, transparent: true, opacity: 0.22 })));
    var dir = new T.Vector3().subVectors(I, O), far = dir.length(); dir.normalize();
    var edge = O.clone().addScaledVector(dir, 10);
    var r10 = K.rod(O, edge, 0.07, new T.MeshBasicMaterial({ color: BLUE }));
    var rest = K.rod(edge, I, 0.05, new T.MeshBasicMaterial({ color: 0x4FD6A0 }));
    var st = { z: 0, goal: 0 };
    return {
      anchors: { mast: V3(-6, 12.6, 0), outlet: V3(-5.6, 11.9, 0), r10: O.clone().addScaledVector(dir, 5).add(V3(0, 0.6, 0)), intake: V3(8.9, 7.3, -3.6), door: V3(8.9, 2.6, 3.2) },
      far: Math.round(far),
      views: [{ pos: [-20, 12, 26], at: [2, 6, 0] }, { pos: [-16, 9, 20], at: [-4, 7, 0] }, { pos: [-11, 13.5, 9], at: [-6, 11, 0] },
              { pos: [-2, 7, 16], at: [9, 4.5, 0] }, { pos: [-12, 15, 34], at: [2, 6.5, -1] }, { pos: [-10, 14, 32], at: [2.5, 6.5, -1.5] }],
      reset: function () { st.z = st.goal = 0; st.r = 0; st.k = 0; },
      go: function (k) { st.k = k; st.goal = k >= 3 ? 1 : 0; if (A.still) { st.z = st.goal; st.r = k >= 4 ? 1 : 0; } },
      tick: function (dt) {
        plume.tick(dt);
        st.z = A.approach(st.z, st.goal, 0.7, dt);
        var e = A.ease(st.z);
        zone.scale.setScalar(Math.max(0.001, e)); zone.visible = e > 0.002;
        st.r = A.approach(st.r || 0, st.k >= 4 ? 1 : 0, 0.9, dt);
        r10.grow(A.clamp(st.z * 1.4 - 0.2, 0, 1)); rest.grow(A.ease(st.r));
        /* the places that breathe air light up while they are the subject */
        var glow = (st.k === 2 || st.k === 4) ? 0.35 + 0.3 * Math.sin((st.t = (st.t || 0) + dt) * 4) : 0;
        intake.material.emissiveIntensity = glow; door.material.emissiveIntensity = st.k === 2 ? glow : 0;
      }
    };
  } };

  /* ------------------------------------------------------------------ two barriers: gas safe, or ESD-protected */
  SCENES.barriers = { still: true, build: function (A) {
    var K = A.kit, rnd = A.rnd;
    K.lights(0xcfe3ff, 0x0a2463, 0.75, 0xffffff, 0.9, [-5, 9, 7]);
    K.room(10, 4.4, 7, [0x132c63, 0x17346f, 0x163170], ['back', 'right']);
    /* the engine */
    var eng = new T.Group(); eng.position.set(2, 0, -1); A.scene.add(eng);
    var em = K.mat(0x8597b2, { roughness: 0.5 }), dk = K.mat(0x3f5375, { roughness: 0.6 });
    K.box(3.2, 1.5, 2, em, 0, 0.75, 0, eng); K.box(3.4, 0.25, 2.2, dk, 0, 0.12, 0, eng);
    for (var c = -1.1; c <= 1.2; c += 0.75) { K.box(0.5, 0.55, 0.9, em, c, 1.78, 0, eng); K.box(0.56, 0.1, 0.96, dk, c, 2.08, 0, eng); }
    /* the gas supply and the outer pipe that holds a leak */
    var PY = 2.4, PZ = -1;
    var pipe = K.add(new T.Mesh(new T.CylinderGeometry(0.08, 0.08, 6.2, 16), K.mat(0xd8e1ea, { roughness: 0.35 })), -2, PY, PZ); pipe.rotation.z = Math.PI / 2;
    K.add(new T.Mesh(new T.CylinderGeometry(0.08, 0.08, 0.6, 16), K.mat(0xd8e1ea)), 1, PY - 0.3, PZ);
    var ductM = new T.MeshStandardMaterial({ color: 0x9cc9ec, roughness: 0.2, transparent: true, opacity: 0.32, side: T.DoubleSide, depthWrite: false });
    var duct = K.add(new T.Mesh(new T.CylinderGeometry(0.3, 0.3, 6.2, 28, 1, true), ductM), -2, PY, PZ); duct.rotation.z = Math.PI / 2;
    var LEAK = V3(-1.6, PY, PZ);
    var held = A.Gas({ at: LEAK, n: 300, size: 0.32, color: [1, 0.5, 0.45], alpha: 0.32, jit: 0.4, tube: { y: PY, z: PZ, r: 0.22, x0: -4.9 },
      life: [4, 6], vel: function () { return [-0.9 - rnd() * 0.4, (rnd() - 0.5) * 0.5, (rnd() - 0.5) * 0.5]; } });
    var free = A.Gas({ at: LEAK, n: 700, size: 0.75, color: [1, 0.45, 0.4], alpha: 0.13, buoy: 0.42, jit: 0.9, spread: 0.8, life: [9, 14],
      vel: function () { return [(rnd() - 0.5) * 0.4, 0.5 + rnd() * 0.4, 0.3 + rnd() * 0.4]; }, box: { x0: -4.8, x1: 4.8, y0: 0.1, y1: 4.2, z0: -3.3, z1: 3.3 } });
    /* the detector, the lights and a motor: the sources of ignition */
    var det = K.box(0.42, 0.3, 0.16, K.mat(0xe8eef5), -0.6, 3.75, -3.4);
    var led = K.add(new T.Mesh(new T.SphereGeometry(0.05, 14, 10), new T.MeshBasicMaterial({ color: 0x4fd6a0 })), -0.47, 3.8, -3.3);
    var lamps = [], lampL = [];
    [-3.4, 3.2].forEach(function (x) {
      K.box(0.9, 0.08, 0.3, K.mat(0x8597b2), x, 4.1, -3.2);
      var l = K.add(new T.Mesh(new T.BoxGeometry(0.8, 0.06, 0.2), new T.MeshStandardMaterial({ color: 0xfff6dc, emissive: 0xfff1c9, emissiveIntensity: 1.4 })), x, 4.03, -3.2);
      var pl = new T.PointLight(0xffe7b0, 0.9, 7, 1.6); pl.position.set(x, 3.7, -2.6); A.scene.add(pl);
      lamps.push(l); lampL.push(pl);
    });
    var motor = K.add(new T.Mesh(new T.CylinderGeometry(0.4, 0.4, 0.9, 24), K.mat(0x4f6a96)), -3.4, 0.45, 1.2); motor.rotation.z = Math.PI / 2;
    var spark = new T.Sprite(new T.SpriteMaterial({ map: A.softDot(), color: 0xffd36b, transparent: true, blending: T.AdditiveBlending, depthWrite: false }));
    spark.scale.set(0.7, 0.7, 1); spark.position.set(-2.85, 0.75, 1.5); A.scene.add(spark);
    var alarm = new T.PointLight(0xff3b30, 0, 9, 1.6); alarm.position.set(-0.6, 3.4, -2.6); A.scene.add(alarm);
    var st = { k: 0, duct: 0, t2: 0, off: 0 };
    return {
      anchors: { engine: V3(2, 2.6, -1), supply: V3(-4, 2.9, -1), held: V3(-1.6, 3.0, -1), det: V3(-0.6, 4.2, -3.4), off: V3(3.2, 4.5, -3.2) },
      views: [{ pos: [-9, 6.5, 10], at: [0, 1.8, -1] }, { pos: [-8, 5.6, 8.5], at: [0, 1.8, -1] }, { pos: [-5.4, 3.6, 3.6], at: [-1.8, 2.3, -1] }, { pos: [-7.5, 5, 7.5], at: [0, 2.2, -1.4] }],
      reset: function () { held.clear(); free.clear(); st.k = 0; st.duct = 0; st.t2 = 0; st.off = 0; },
      go: function (k) {
        st.k = k; st.t2 = 0;
        held.rate(k === 1 ? 32 : 0); free.rate(k === 2 ? 42 : 0);
        if (k !== 1) { held.clear(); } if (k !== 2) { free.clear(); st.off = 0; }
      },
      tick: function (dt, t) {
        held.tick(dt); free.tick(dt);
        st.duct = A.approach(st.duct, st.k === 1 ? 1 : st.k === 0 ? 0.6 : 0, 1.5, dt);
        ductM.opacity = 0.34 * st.duct; duct.visible = st.duct > 0.01;
        if (st.k === 2) { st.t2 += dt; }
        var hot = st.k === 2 && st.t2 > 2.2;
        st.off = A.approach(st.off, hot ? 1 : 0, 1.4, dt);
        led.material.color.setHex(hot ? 0xff3b30 : 0x4fd6a0).convertSRGBToLinear();
        alarm.intensity = hot ? 1 + Math.sin(t * 7) * 0.8 : 0;
        lamps.forEach(function (l, i) { l.material.emissiveIntensity = 1.4 * (1 - st.off); lampL[i].intensity = 0.9 * (1 - st.off); });
        spark.material.opacity = (1 - st.off) * (0.4 + 0.6 * Math.abs(Math.sin(t * 13) * Math.sin(t * 5.3)));
      }
    };
  } };

  /* ------------------------------------------------------------------ the fuel preparation room */
  SCENES.fpr = { still: true, build: function (A) {
    var K = A.kit, rnd = A.rnd;
    K.lights(0xdfe9ff, 0x223a6e, 0.85, 0xffffff, 1.05, [-4, 9, 7]);
    K.room(9, 4.4, 6, [0x1a3570, 0x1f3f80, 0x1c3a79], ['back', 'left', 'right'], true);
    var steel = K.mat(0xd2dce7, { roughness: 0.4 }), blue = K.mat(0x3e7fc0, { roughness: 0.45 }), dk = K.mat(0x41557a);
    /* pump, vaporizer, heater */
    var pump = new T.Group(); pump.position.set(-2.9, 0, -1.4); A.scene.add(pump);
    K.add(new T.Mesh(new T.CylinderGeometry(0.42, 0.42, 1.3, 24), blue), 0, 0.85, 0, pump);
    K.add(new T.Mesh(new T.CylinderGeometry(0.3, 0.3, 0.5, 20), steel), 0, 1.75, 0, pump);
    K.box(1.1, 0.2, 1.1, dk, 0, 0.1, 0, pump);
    var vap = new T.Group(); vap.position.set(-0.2, 0, -1.4); A.scene.add(vap);
    K.box(1.8, 1.3, 1.1, K.mat(0x9fb3c8, { roughness: 0.5 }), 0, 0.95, 0, vap);
    for (var f = -0.75; f <= 0.76; f += 0.15) { K.box(0.04, 1.36, 1.16, K.mat(0xdfe8f1), f, 0.95, 0, vap); }
    var heat = new T.Group(); heat.position.set(2.4, 0, -1.4); A.scene.add(heat);
    var hb = K.add(new T.Mesh(new T.CylinderGeometry(0.45, 0.45, 1.6, 24), K.mat(0xc96a3a, { roughness: 0.5 })), 0, 0.9, 0, heat); hb.rotation.z = Math.PI / 2;
    K.box(1.2, 0.3, 0.6, dk, 0, 0.3, 0, heat);
    /* the path of the fuel: in from the tank, through all three, out to the engine room in a double wall */
    var path = [V3(-2.9, 2.05, -3), V3(-2.9, 2.05, -1.4), V3(-2.9, 1.4, -1.4), V3(-1.1, 1.4, -1.4), V3(0.7, 1.4, -1.4), V3(1.6, 0.9, -1.4), V3(3.2, 0.9, -1.4),
                V3(3.4, 0.9, -1.4), V3(3.4, 3.2, -1.4), V3(-4.5, 3.2, -1.4)];
    var segL = [], total = 0, pm = K.mat(0xd8e1ea, { roughness: 0.35 });
    for (var i = 0; i < path.length - 1; i++) { var l = path[i].distanceTo(path[i + 1]); segL.push(l); total += l; K.rod(path[i], path[i + 1], 0.07, pm); }
    var outer = K.rod(V3(3.4, 3.2, -1.4), V3(-4.5, 3.2, -1.4), 0.2, new T.MeshStandardMaterial({ color: 0x9cc9ec, transparent: true, opacity: 0.3, depthWrite: false }));
    var vapAt = 0; for (i = 0; i < 4; i++) { vapAt += segL[i]; }
    function at(u, out) {
      for (var j = 0; j < segL.length; j++) { if (u <= segL[j]) { return out.lerpVectors(path[j], path[j + 1], u / segL[j]); } u -= segL[j]; }
      return out.copy(path[path.length - 1]);
    }
    var FN = 160, FP = new Float32Array(FN * 3), FC = new Float32Array(FN * 3), FU = new Float32Array(FN), tmp = V3(0, 0, 0);
    for (i = 0; i < FN; i++) { FU[i] = i / FN * total; }
    var fg = new T.BufferGeometry(); fg.setAttribute('position', new T.BufferAttribute(FP, 3)); fg.setAttribute('color', new T.BufferAttribute(FC, 3));
    var flow = new T.Points(fg, new T.PointsMaterial({ size: 0.28, map: A.softDot(), vertexColors: true, transparent: true, depthWrite: false, blending: T.AdditiveBlending }));
    flow.frustumCulled = false; A.scene.add(flow);
    /* the room's own ventilation, the detector and the supply valve, the door to the open deck */
    var FAN = V3(3, 3.7, -2.9);
    var fan = new T.Group(); fan.position.copy(FAN); A.scene.add(fan);
    K.add(new T.Mesh(new T.TorusGeometry(0.45, 0.06, 12, 40), steel), 0, 0, 0, fan);
    var rotor = new T.Group(); fan.add(rotor);
    for (var b = 0; b < 5; b++) { var bg = new T.BoxGeometry(0.14, 0.36, 0.02); bg.rotateY(0.5); bg.translate(0, 0.24, 0); var bl = new T.Mesh(bg, K.mat(BLUE)); bl.rotation.z = b * Math.PI * 2 / 5; rotor.add(bl); }
    var air = A.Gas({ at: V3(-1, 1, 1.5), n: 260, size: 0.5, color: [0.6, 0.8, 1], alpha: 0.07, jit: 1.2, life: [3, 5], jitAt: 4,
      vel: function () { return [(rnd() - 0.5) * 0.3, 0.2, -0.2]; }, box: { x0: -4.3, x1: 4.3, y0: 0.1, y1: 4.2, z0: -2.8, z1: 2.8 } });
    air.pull(FAN, 2.2);
    K.box(0.42, 0.3, 0.16, K.mat(0xe8eef5), 0, 3.85, -2.9);
    var led = K.add(new T.Mesh(new T.SphereGeometry(0.05, 14, 10), new T.MeshBasicMaterial({ color: 0x4fd6a0 })), 0.13, 3.9, -2.8);
    var wheel = new T.Group(); wheel.position.set(-2.9, 2.45, -2.5); A.scene.add(wheel);
    var rim = K.add(new T.Mesh(new T.TorusGeometry(0.26, 0.04, 12, 36), K.mat(0xd94f45)), 0, 0, 0, wheel); rim.rotation.x = Math.PI / 2;
    for (var sp = 0; sp < 3; sp++) { K.box(0.5, 0.03, 0.04, steel, 0, 0, 0, wheel).rotation.y = sp * Math.PI / 3; }
    var doorPivot = new T.Group(); doorPivot.position.set(4.45, 0, 1.9); A.scene.add(doorPivot);
    K.box(0.08, 2.3, 1.2, K.mat(0xb9c8d8), 0, 1.15, -0.6, doorPivot);
    var day = K.add(new T.Mesh(new T.PlaneGeometry(1.2, 2.3), new T.MeshBasicMaterial({ color: 0xdff1ff })), 4.52, 1.15, 1.3); day.rotation.y = -Math.PI / 2;
    var st = { k: 0, speed: 1, door: 0, fanS: 0.3 };
    return {
      anchors: { pump: V3(-2.9, 2.4, -1.4), vap: V3(-0.2, 2.0, -1.4), heat: V3(2.4, 1.7, -1.4), fan: V3(3, 4.4, -2.9), det: V3(0, 4.3, -2.9), valve: V3(-2.9, 2.85, -2.5),
                 deck: V3(4.1, 2.7, 1.3), er: V3(-4.1, 2.4, 0.6), dw: V3(-1.5, 3.65, -1.4) },
      views: [{ pos: [-7, 6.5, 9.5], at: [0, 1.6, -1] }, { pos: [-5.5, 5.2, 8], at: [0, 1.4, -1.2] }, { pos: [-3, 4.6, 5.5], at: [2.4, 3, -2.4] },
              { pos: [-4.5, 4.2, 5], at: [-1.2, 2.6, -2.4] }, { pos: [0.3, 5.6, 13], at: [0.2, 1.7, 0] }, { pos: [-1.5, 5, 6.5], at: [-2, 3, -1.4] }],
      reset: function () { st.k = 0; st.speed = 1; st.door = 0; air.clear(); },
      go: function (k) { st.k = k; },
      tick: function (dt, t) {
        var shut = st.k === 2;
        st.speed = A.approach(st.speed, shut ? 0 : 1, 0.8, dt);
        st.door = A.approach(st.door, st.k === 3 ? 1 : 0, 0.8, dt);
        st.fanS = A.approach(st.fanS, st.k === 1 ? 1 : 0.35, 0.6, dt);
        doorPivot.rotation.y = A.ease(st.door) * 1.6;
        wheel.rotation.y = (1 - st.speed) * Math.PI * 1.5;
        rotor.rotation.z -= dt * st.fanS * 14;
        air.rate(st.fanS * 50); air.tick(dt);
        led.material.color.setHex(shut ? 0xff3b30 : 0x4fd6a0).convertSRGBToLinear();
        outer.material.opacity = st.k === 4 ? 0.3 + 0.25 * Math.abs(Math.sin(t * 2.5)) : 0.3;
        for (var j = 0; j < FN; j++) {
          FU[j] += dt * 1.2 * st.speed; if (FU[j] > total) { FU[j] -= total; }
          at(FU[j], tmp); var o = j * 3;
          FP[o] = tmp.x; FP[o + 1] = tmp.y; FP[o + 2] = tmp.z;
          var gasNow = FU[j] > vapAt, a = 0.3 + 0.6 * st.speed;
          FC[o] = (gasNow ? 0.95 : 0.2) * a; FC[o + 1] = (gasNow ? 0.85 : 0.6) * a; FC[o + 2] = (gasNow ? 0.8 : 1) * a;
        }
        fg.attributes.position.needsUpdate = true; fg.attributes.color.needsUpdate = true;
      }
    };
  } };

  /* ------------------------------------------------------------------ three fuels: how cold, how much insulation */
  SCENES.tanks = { still: true, fov: 38, build: function (A) {
    var K = A.kit, rnd = A.rnd;
    K.lights(0xcfe3ff, 0x0a2463, 0.8, 0xffffff, 1.1, [-5, 10, 8]);
    var floor = K.box(12, 0.16, 5, K.mat(0x14306b, { roughness: 0.9 }), 0, -0.08, 0); K.edges(floor, BLUE, 0.35);
    var fuels = [{ x: -3.6, t: -162, ins: 0.42, liq: 0x8fd0ff, name: 'LNG' }, { x: 0, t: -42, ins: 0.2, liq: 0x7fb6e8, name: 'LPG' }, { x: 3.6, t: 20, ins: 0, liq: 0xc9e6f5, name: 'Methanol' }];
    var shellM = new T.MeshStandardMaterial({ color: 0xdfe7f0, roughness: 0.45, side: T.DoubleSide });
    var insM = new T.MeshStandardMaterial({ color: 0xf2d9a6, roughness: 0.95, side: T.DoubleSide, emissive: 0x53A7DB, emissiveIntensity: 0 });
    var cols = [], glows = [];
    fuels.forEach(function (f) {
      var g = new T.Group(); g.position.set(f.x, 0, 0); A.scene.add(g);
      var R0 = 0.9, open = Math.PI * 0.6, start = open / 2 - open;
      K.add(new T.Mesh(new T.CylinderGeometry(R0, R0, 2.4, 40, 1, true, open / 2, Math.PI * 2 - open), shellM), 0, 1.4, 0, g);
      K.add(new T.Mesh(new T.CylinderGeometry(R0, R0, 1.5, 40, 1, false), new T.MeshStandardMaterial({ color: f.liq, roughness: 0.15, transparent: true, opacity: 0.85 })), 0, 0.95, 0, g).scale.set(0.97, 1, 0.97);
            if (f.ins > 0) {
        K.add(new T.Mesh(new T.CylinderGeometry(R0 + f.ins, R0 + f.ins, 2.4, 40, 1, true, open / 2, Math.PI * 2 - open), insM), 0, 1.4, 0, g);
        K.add(new T.Mesh(new T.RingGeometry(R0, R0 + f.ins, 40, 1, -Math.PI / 2 + open / 2, Math.PI * 2 - open), insM), 0, 2.61, 0, g).rotation.x = -Math.PI / 2;
      }
      K.box(2.2, 0.2, 1.2, K.mat(0x41557a), 0, 0.1, 0, g);
      /* the thermometer */
      var tx = R0 + f.ins + 0.5;
      K.add(new T.Mesh(new T.CylinderGeometry(0.11, 0.11, 2.4, 16, 1, true), new T.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.25, depthWrite: false })), tx, 1.4, 0.4, g);
      var colm = K.add(new T.Mesh((function () { var cg = new T.CylinderGeometry(0.07, 0.07, 1, 12); cg.translate(0, 0.5, 0); return cg; })(),
        new T.MeshBasicMaterial({ color: 0x53A7DB })), tx, 0.2, 0.4, g);
      K.add(new T.Mesh(new T.SphereGeometry(0.14, 16, 12), new T.MeshBasicMaterial({ color: 0x53A7DB })), tx, 0.2, 0.4, g);
      cols.push({ m: colm, goal: 2.2, now: 2.2, f: f });
      glows.push(g);
    });
    var mist = A.Gas({ at: V3(-3.6, 2.4, 0.4), n: 300, size: 0.6, color: [0.85, 0.93, 1], alpha: 0.08, buoy: -0.25, jit: 0.5, life: [4, 7], jitAt: 1.6,
      vel: function () { return [(rnd() - 0.5) * 0.3, -0.1, 0.3 + rnd() * 0.3]; }, box: { x0: -6, x1: 6, y0: 0.15, y1: 3.5, z0: -2.4, z1: 2.4 } });
    function h(t) { return 0.2 + (t + 170) / 210 * 2.2; }
    var st = { k: 0 };
    return {
      anchors: { t0: V3(-2.4, 3.0, 0.4), t1: V3(1.2, 3.0, 0.4), t2: V3(3.9, 3.0, 0.4), ins: V3(-3.6, 1.2, 1.3) },
      views: [{ pos: [0, 6, 14], at: [0, 1.3, 0] }, { pos: [-1.4, 4.2, 8.2], at: [-3.2, 1.3, 0] }, { pos: [1.8, 4.2, 8.2], at: [0.1, 1.3, 0] },
              { pos: [5.2, 4.2, 8.2], at: [3.6, 1.3, 0] }, { pos: [0, 5.4, 13], at: [0, 1.3, 0] }],
      reset: function () { st.k = 0; mist.clear(); cols.forEach(function (c) { c.now = c.goal = h(30); }); },
      go: function (k) { st.k = k; cols.forEach(function (c, i) { c.goal = (k >= i) ? h(c.f.t) : h(30); }); },
      tick: function (dt, t) {
        cols.forEach(function (c) { c.now = A.approach(c.now, c.goal, 0.9, dt); c.m.scale.y = Math.max(0.01, c.now - 0.2); });
        mist.rate(st.k === 0 || st.k === 3 ? 30 : 8); mist.tick(dt);
        insM.emissiveIntensity = st.k === 3 ? 0.25 + 0.2 * Math.sin(t * 3) : 0;
      }
    };
  } };

  /* ------------------------------------------------------------------ the tank in 3D, beside its drawing */
  SCENES.tank = { still: true, fov: 34, sway: 0.5, build: function (A) {
    var K = A.kit, rnd = A.rnd;
    K.lights(0xcfe3ff, 0x0a2463, 0.85, 0xffffff, 1.15, [-4, 8, 7]);
    var g = new T.Group(); A.scene.add(g);
    var R0 = 1.1, LEN = 3.2;
    var shellM = new T.MeshStandardMaterial({ color: 0xbfd2e6, roughness: 0.3, transparent: true, opacity: 0.28, depthWrite: false, side: T.DoubleSide, emissive: BLUE, emissiveIntensity: 0 });
    function capsule(r, m, parent) {
      var c = K.add(new T.Mesh(new T.CylinderGeometry(r, r, LEN, 48, 1, true), m), 0, 0, 0, parent); c.rotation.z = Math.PI / 2;
      [-1, 1].forEach(function (s) { var e = K.add(new T.Mesh(new T.SphereGeometry(r, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2), m), s * LEN / 2, 0, 0, parent); e.rotation.z = -s * Math.PI / 2; });
    }
    var tank = new T.Group(); tank.position.y = 1.5; g.add(tank);
    capsule(R0, shellM, tank);
    var level = new T.Plane(V3(0, -1, 0), 1.5);
    var liqM = new T.MeshStandardMaterial({ color: 0x2f8fd0, roughness: 0.2, transparent: true, opacity: 0.9, clippingPlanes: [level], emissive: 0x53A7DB, emissiveIntensity: 0 });
    capsule(R0 * 0.96, liqM, tank);
    /* the liquid's surface, the tank's own outline at that height */
    var sh = new T.Shape(), sr = 1.0, hl = LEN / 2;
    sh.moveTo(-hl, -sr); sh.lineTo(hl, -sr); sh.absarc(hl, 0, sr, -Math.PI / 2, Math.PI / 2, false); sh.lineTo(-hl, sr); sh.absarc(-hl, 0, sr, Math.PI / 2, Math.PI * 1.5, false);
    var surf = K.add(new T.Mesh(new T.ShapeGeometry(sh, 24), new T.MeshBasicMaterial({ color: 0x9fdcff, transparent: true, opacity: 0.35, side: T.DoubleSide, depthWrite: false })), 0, 0, 0, tank);
    surf.rotation.x = -Math.PI / 2;
    var dome = K.add(new T.Mesh(new T.CylinderGeometry(0.22, 0.22, 0.5, 20), K.mat(0xd2dce7)), 0.6, R0 + 0.15, 0, tank);
    K.rod(V3(0.6, 1.5 + R0 + 0.4, 0), V3(1.6, 1.5 + R0 + 0.4, 0), 0.06, K.mat(0xd2dce7));
    [-1.3, 1.3].forEach(function (x) { K.box(0.25, 0.6, 1.3, K.mat(0x41557a), x, 0.3, 0, g); });
    var vap = A.Gas({ at: V3(0, 2.15, 0), n: 220, size: 0.45, color: [0.75, 0.88, 1], alpha: 0.12, jit: 0.9, life: [3, 5], jitAt: 2,
      vel: function () { return [(rnd() - 0.5) * 0.4, (rnd() - 0.5) * 0.2, (rnd() - 0.5) * 0.4]; }, box: { x0: -2.2, x1: 2.2, y0: 1.75, y1: 2.45, z0: -0.7, z1: 0.7 } });
    var st = { k: -1, lv: 0.25 };
    return {
      anchors: { c: V3(-2.4, 2.4, 0.3), l: V3(2.6, 1.6, 0.4), v: V3(1.8, 2.5, 0.2) },
      views: [{ pos: [2.5, 3.4, 7.6], at: [0, 1.4, 0] }, { pos: [2.5, 3.4, 7.6], at: [0, 1.4, 0] }, { pos: [3.2, 2.2, 6.4], at: [0.4, 1.5, 0] }, { pos: [1.5, 3.8, 6.4], at: [0.2, 1.9, 0] }],
      reset: function () { st.k = -1; vap.clear(); },
      go: function (k) { st.k = k; },
      tick: function (dt, t) {
        g.rotation.y = A.still ? -0.35 : -0.35 + Math.sin(t * 0.3) * 0.25;
        shellM.emissiveIntensity = st.k === 0 ? 0.35 + 0.25 * Math.sin(t * 3) : 0;
        shellM.opacity = st.k === 0 ? 0.42 : 0.28;
        var goal = st.k === 1 ? 0.15 + Math.sin(t * 0.9) * 0.05 : 0.25;
        st.lv = A.approach(st.lv, goal, 0.5, dt);
        level.constant = 1.5 + st.lv; surf.position.y = st.lv; surf.material.opacity = st.k === 1 ? 0.6 : 0.25;
        vap.rate(st.k === 2 ? 45 : 6); vap.tick(dt);
      }
    };
  } };

  /* ------------------------------------------------------------------ the tablet the room is about to pick up */
  SCENES.tablet = { still: true, fov: 30, sway: 0.4, build: function (A) {
    var K = A.kit;
    A.scene.add(new T.HemisphereLight(0xffffff, 0x8fa3bd, 0.9));
    var key = new T.DirectionalLight(0xffffff, 1.0); key.position.set(-4, 5, 8); A.scene.add(key);
    var rim = new T.DirectionalLight(0xcfe3ff, 1.6); rim.position.set(5, 3, -4); A.scene.add(rim);
    /* the screen: the task as the trainee will see it */
    var W = 1280, H = 820, cv = d.createElement('canvas'); cv.width = W; cv.height = H;
    var g = cv.getContext('2d'), tex = new T.CanvasTexture(cv); tex.encoding = T.sRGBEncoding; tex.anisotropy = 8;
    function rr(x, y, w2, h2, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w2, y, x + w2, y + h2, r); g.arcTo(x + w2, y + h2, x, y + h2, r); g.arcTo(x, y + h2, x, y, r); g.arcTo(x, y, x + w2, y, r); g.closePath(); }
    var F = 'Raleway, Arial, sans-serif', rows = ['Fuel tank', 'Tank connection space', 'Fuel preparation room'], last = '';
    function paint(sel, tap, next) {
      var key2 = sel + '|' + tap.toFixed(2) + '|' + next; if (key2 === last) { return; } last = key2;
      g.clearRect(0, 0, W, H); g.save(); rr(0, 0, W, H, 34); g.clip();
      g.fillStyle = '#F7F8FA'; g.fillRect(0, 0, W, H);
      g.fillStyle = '#0A2463'; g.fillRect(0, 0, W, 132);
      rr(48, 38, 118, 56, 28); g.fillStyle = '#53A7DB'; g.fill();
      g.fillStyle = '#0A2463'; g.font = '800 34px ' + F; g.fillText('SC1', 74, 78);
      g.fillStyle = '#fff'; g.font = '700 36px ' + F; g.fillText('Self-check 1 - the new spaces', 196, 79);
      g.fillStyle = '#415C8F'; g.font = '700 24px ' + F; g.fillText('QUESTION 3 OF 5', 56, 196);
      for (var i = 0; i < 5; i++) { rr(1012 + i * 42, 178, 32, 12, 6); g.fillStyle = i < 2 ? '#4FD6A0' : i === 2 ? '#53A7DB' : '#DCE3EB'; g.fill(); }
      g.fillStyle = '#0A2463'; g.font = '800 46px ' + F; g.fillText('Which space holds the vaporizer?', 56, 262);
      rows.forEach(function (r, j) {
        var y = 310 + j * 118, on = sel === j;
        rr(56, y, W - 112, 96, 22); g.fillStyle = on ? '#E6F2FA' : '#fff'; g.fill();
        g.lineWidth = on ? 5 : 3; g.strokeStyle = on ? '#53A7DB' : '#DCE3EB'; g.stroke();
        g.beginPath(); g.arc(112, y + 48, 20, 0, Math.PI * 2); g.lineWidth = 4; g.strokeStyle = on ? '#0A2463' : '#9fb3c8'; g.stroke();
        if (on) { g.beginPath(); g.arc(112, y + 48, 11, 0, Math.PI * 2); g.fillStyle = '#0A2463'; g.fill(); }
        g.fillStyle = '#0A2463'; g.font = (on ? '700' : '600') + ' 38px ' + F; g.fillText(r, 156, y + 61);
      });
      rr(W - 296, H - 96, 240, 68, 34); g.fillStyle = sel === 2 ? (next ? '#123681' : '#0A2463') : '#B8C7DA'; g.fill();
      g.fillStyle = '#fff'; g.font = '800 30px ' + F; g.fillText('Next  ›', W - 230, H - 51);
      if (tap > 0) {
        g.beginPath(); g.arc(860, 310 + 2 * 118 + 48, 26 + (1 - tap) * 70, 0, Math.PI * 2);
        g.lineWidth = 8; g.strokeStyle = 'rgba(83,167,219,' + (tap * 0.9).toFixed(2) + ')'; g.stroke();
        g.beginPath(); g.arc(860, 310 + 2 * 118 + 48, 22, 0, Math.PI * 2); g.fillStyle = 'rgba(10,36,99,' + (tap * 0.25).toFixed(2) + ')'; g.fill();
      }
      g.restore(); tex.needsUpdate = true;
    }
    /* the device: a rounded aluminium body, a black glass front, the screen, a sheen across the glass */
    function rounded(w2, h2, r) {
      var s = new T.Shape(), x = -w2 / 2, y = -h2 / 2;
      s.moveTo(x + r, y); s.lineTo(x + w2 - r, y); s.quadraticCurveTo(x + w2, y, x + w2, y + r); s.lineTo(x + w2, y + h2 - r);
      s.quadraticCurveTo(x + w2, y + h2, x + w2 - r, y + h2); s.lineTo(x + r, y + h2); s.quadraticCurveTo(x, y + h2, x, y + h2 - r);
      s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s;
    }
    var tab = new T.Group(); A.scene.add(tab);
    var bodyG = new T.ExtrudeGeometry(rounded(3.44, 2.26, 0.2), { depth: 0.1, bevelEnabled: true, bevelThickness: 0.035, bevelSize: 0.035, bevelSegments: 5, curveSegments: 18 });
    bodyG.translate(0, 0, -0.05);
    tab.add(new T.Mesh(bodyG, K.mat(0x8d9bb0, { roughness: 0.32, metalness: 0.15 })));
    var front = new T.Mesh(new T.ShapeGeometry(rounded(3.42, 2.24, 0.19), 18), new T.MeshStandardMaterial({ color: 0x0b0f17, roughness: 0.12, metalness: 0.1 }));
    front.position.z = 0.087; tab.add(front);
    var screen = new T.Mesh(new T.PlaneGeometry(3.14, 2.01), new T.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false }));
    screen.position.z = 0.089; tab.add(screen);
    K.add(new T.Mesh(new T.CircleGeometry(0.025, 16), new T.MeshBasicMaterial({ color: 0x2b3a55 })), -1.63, 0, 0.09, tab);
    var sc = d.createElement('canvas'); sc.width = 256; sc.height = 256;
    var sg = sc.getContext('2d'), lg = sg.createLinearGradient(0, 0, 256, 256);
    lg.addColorStop(0, 'rgba(255,255,255,.22)'); lg.addColorStop(0.42, 'rgba(255,255,255,.04)'); lg.addColorStop(0.5, 'rgba(255,255,255,0)'); lg.addColorStop(1, 'rgba(255,255,255,0)');
    sg.fillStyle = lg; sg.fillRect(0, 0, 256, 256);
    var sheen = new T.Mesh(new T.ShapeGeometry(rounded(3.42, 2.24, 0.19), 18), new T.MeshBasicMaterial({ map: new T.CanvasTexture(sc), transparent: true, depthWrite: false, blending: T.AdditiveBlending }));
    var uv = sheen.geometry.attributes.uv, pos = sheen.geometry.attributes.position;
    for (var i = 0; i < uv.count; i++) { uv.setXY(i, pos.getX(i) / 3.42 + 0.5, pos.getY(i) / 2.24 + 0.5); }
    sheen.position.z = 0.092; tab.add(sheen);
    var shadow = K.add(new T.Mesh(new T.CircleGeometry(2, 48), new T.MeshBasicMaterial({ map: A.softDot(), color: 0x0A2463, transparent: true, opacity: 0.32, depthWrite: false })), 0, -1.55, -0.4);
    shadow.rotation.x = -Math.PI / 2; shadow.scale.set(1, 0.3, 1);
    paint(-1, 0, false);
    return {
      anchors: {},
      views: [{ pos: [0.2, 0.2, 5.2], at: [0, -0.1, 0] }, { pos: [0.2, 0.2, 5.2], at: [0, -0.1, 0] }],
      reset: function () { last = ''; },
      go: function () {},
      tick: function (dt, t) {
        /* a six-second loop: read, tap the answer, press Next */
        var c = t % 6, sel = c < 2.2 ? -1 : 2, tap = c >= 2.2 && c < 2.9 ? 1 - (c - 2.2) / 0.7 : 0, next = c >= 4.4 && c < 4.8;
        if (A.still) { sel = 2; tap = 0; next = false; }
        paint(sel, tap, next);
        tab.rotation.y = -0.42 + Math.sin(t * 0.45) * 0.06; tab.rotation.x = -0.1 + Math.sin(t * 0.35) * 0.03; tab.rotation.z = 0.025;
        tab.position.y = Math.sin(t * 0.8) * 0.05;
        shadow.material.opacity = 0.32 - tab.position.y * 0.6;
      }
    };
  } };

  /* ------------------------------------------------------------------ a scene held at one camera, for naming parts or comparing two states */
  function fixed(name, view, hold) {
    return { still: true, build: function (A) {
      var S = SCENES[name].build(A), v = S.views[view], go = S.go;
      S.views = [v, v, v, v, v, v, v, v];
      if (hold) { S.go = function () { go(0); }; }
      return S;
    } };
  }
  SCENES.fprq = fixed('fpr', 1, true);
  SCENES.barriers2 = fixed('barriers', 3);

  L.boot();
})(window, document);
