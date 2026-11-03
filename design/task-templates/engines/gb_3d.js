/* ==========================================================================
   gb_3d.js - a real object in 3D, and a 360-degree place, for tablet tasks.
   Needs vendor/three-0.147.0/three.min.js (+ GLTFLoader.js, OrbitControls.js)
   and gb_lab.js. Everything is offline, from the course pack.

   FINGERS FIRST (owner, 2026-10-16: "all of these elements will be clicked with
   fingers, not pointers"): one finger turns the object or looks around; two
   fingers zoom; and big on-screen buttons do every one of those too - a pinch
   or a drag is never the only way. Points on the object are finger-sized pins
   that hide when they are behind it.

     var m = GB3D.model(el, { src: '../img/x.glb', pins: [{ id, at: [x, y, z], label }], onPin: fn(id), onReady })
     m.focus(id)  m.reset()  m.pinState(id, 'done'|'bad'|'')  m.setPins(list)

     var p = GB3D.pano(el, { src: '../img/x.jpg', onLook: fn({yaw, pitch}), yaw, pitch, pitchMin, pitchMax })
     p.mark(id, yaw, pitch, cls)   p.angleTo(yaw, pitch)   - a tap on the view reports where it looked (degrees)
   ========================================================================== */
(function (W, D) {
  'use strict';
  var T = W.THREE;

  function controlsBar(host, buttons) {
    var bar = D.createElement('div');
    bar.className = 'g3-bar';
    buttons.forEach(function (b) {
      var x = D.createElement('button');
      x.type = 'button'; x.className = 'g3-b'; x.innerHTML = b[0]; x.setAttribute('aria-label', b[1]);
      // a held button keeps turning; a tap turns one step
      var t = 0;
      function go() { b[2](); }
      x.addEventListener('pointerdown', function () { go(); clearInterval(t); t = setInterval(go, 60); });
      ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (ev) { x.addEventListener(ev, function () { clearInterval(t); }); });
      bar.appendChild(x);
    });
    host.appendChild(bar);
    return bar;
  }

  function renderer(host) {
    var r = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    r.setPixelRatio(Math.min(W.devicePixelRatio || 1, 2));
    r.outputEncoding = T.sRGBEncoding;
    r.domElement.className = 'g3-canvas';
    host.appendChild(r.domElement);
    return r;
  }

  function fit(r, cam, host) {
    // the canvas, not the host: on a tall narrow screen the buttons sit below the canvas
    var w = r.domElement.clientWidth || host.clientWidth, h = r.domElement.clientHeight || host.clientHeight;
    if (!w || !h) return;
    r.setSize(w, h, false);
    cam.aspect = w / h; cam.updateProjectionMatrix();
  }

  /* ---- an object in 3D ------------------------------------------------------------- */
  function model(host, o) {
    host.classList.add('g3');
    var r = renderer(host), scene = new T.Scene(), cam = new T.PerspectiveCamera(35, 1, 0.01, 100);
    scene.add(new T.HemisphereLight(0xdfeeff, 0x223040, 1.0));
    var key = new T.DirectionalLight(0xffffff, 1.3); key.position.set(2, 3, 2.5); scene.add(key);
    var rim = new T.DirectionalLight(0x8fb8ff, 0.6); rim.position.set(-3, 1.5, -2); scene.add(rim);
    var ctl = new T.OrbitControls(cam, r.domElement);
    ctl.enableDamping = true; ctl.dampingFactor = 0.12; ctl.enablePan = false; ctl.rotateSpeed = 0.9;
    ctl.touches = { ONE: T.TOUCH.ROTATE, TWO: T.TOUCH.DOLLY_PAN };
    var root = new T.Group(); scene.add(root);
    var pinLayer = D.createElement('div'); pinLayer.className = 'g3-pins'; host.appendChild(pinLayer);
    var pins = [], home = null, radius = 1, ready = false;

    var loading = D.createElement('div'); loading.className = 'g3-loading'; loading.textContent = 'Loading the 3D model…'; host.appendChild(loading);
    new T.GLTFLoader().load(o.src, function (g) {
      var obj = g.scene;
      // centre it and scale it to a unit size, whatever the file's own units
      var box = new T.Box3().setFromObject(obj), c = box.getCenter(new T.Vector3()), s = box.getSize(new T.Vector3());
      var k = 1.6 / Math.max(s.x, s.y, s.z);
      obj.position.sub(c).multiplyScalar(1); obj.scale.setScalar(k); obj.position.multiplyScalar(k);
      root.add(obj);
      radius = 1.1;
      home = { pos: new T.Vector3(0.9, 0.5, 2.6), target: new T.Vector3(0, 0, 0) };
      reset(true);
      ctl.minDistance = 1.0; ctl.maxDistance = 5;
      ready = true;
      loading.parentNode && loading.parentNode.removeChild(loading);
      setPins(o.pins || []);
      if (o.onReady) o.onReady(obj);
    }, undefined, function () { loading.textContent = 'The 3D model could not be loaded.'; });

    function setPins(list) {
      pinLayer.innerHTML = ''; pins = [];
      list.forEach(function (p) {
        var b = D.createElement('button');
        b.type = 'button'; b.className = 'g3-pin'; b.setAttribute('data-pin', p.id); b.setAttribute('data-tap', '1');
        b.innerHTML = '<i></i>' + (p.label ? '<span>' + GBLab.esc(p.label) + '</span>' : '');
        b.addEventListener('click', function () { if (o.onPin) o.onPin(p.id); });
        pinLayer.appendChild(b);
        pins.push({ id: p.id, v: new T.Vector3(p.at[0], p.at[1], p.at[2]), el: b });
      });
    }
    function pinState(id, cls) { pins.forEach(function (p) { if (p.id === id) p.el.className = 'g3-pin' + (cls ? ' ' + cls : ''); }); }

    var anim = null;
    function flyTo(pos, target, ms) {
      var p0 = cam.position.clone(), t0v = ctl.target.clone(), t0 = performance.now();
      anim = function (now) {
        var k = Math.min(1, (now - t0) / (ms || 700)), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        cam.position.lerpVectors(p0, pos, e); ctl.target.lerpVectors(t0v, target, e);
        if (k >= 1) anim = null;
      };
    }
    function reset(now) { if (!home) return; if (now === true) { cam.position.copy(home.pos); ctl.target.copy(home.target); } else flyTo(home.pos, home.target); }
    function focus(id) {
      var p = pins.filter(function (x) { return x.id === id; })[0]; if (!p) return;
      // turn round the object to face that part from a normal distance - never dive into the model
      var dir = p.v.clone(); dir.y *= 0.5; if (dir.lengthSq() < 0.01) dir.set(0, 0, 1); dir.normalize();
      var target = p.v.clone().multiplyScalar(0.4);
      flyTo(target.clone().add(dir.multiplyScalar(2.2)).add(new T.Vector3(0, 0.25, 0)), target);
    }
    function orbit(dAz, dEl) {
      var off = cam.position.clone().sub(ctl.target), sph = new T.Spherical().setFromVector3(off);
      sph.theta += dAz; sph.phi = Math.max(0.15, Math.min(Math.PI - 0.15, sph.phi + dEl));
      cam.position.copy(ctl.target).add(new T.Vector3().setFromSpherical(sph));
    }
    function zoom(f) {
      var off = cam.position.clone().sub(ctl.target), d = Math.max(ctl.minDistance, Math.min(ctl.maxDistance, off.length() * f));
      cam.position.copy(ctl.target).add(off.setLength(d));
    }
    var bar = controlsBar(host, [
      ['&#8630;', 'Turn left', function () { orbit(-0.06, 0); }], ['&#8631;', 'Turn right', function () { orbit(0.06, 0); }],
      ['&#8593;', 'Tilt up', function () { orbit(0, -0.05); }], ['&#8595;', 'Tilt down', function () { orbit(0, 0.05); }],
      ['&#65291;', 'Closer', function () { zoom(0.94); }], ['&#65293;', 'Further', function () { zoom(1.06); }],
      ['&#10226;', 'Back to start', function () { reset(); }]
    ]);

    var v = new T.Vector3(), ray = new T.Raycaster(), lastOcc = 0;
    function underBar(x, y) {
      var b = bar.getBoundingClientRect(), hb = host.getBoundingClientRect();
      return x > b.left - hb.left - 30 && x < b.right - hb.left + 30 && y > b.top - hb.top - 30;
    }
    function loop(now) {
      W.requestAnimationFrame(loop);
      if (anim) anim(now);
      ctl.update();
      r.render(scene, cam);
      if (!ready) return;
      var w = r.domElement.clientWidth, h = r.domElement.clientHeight;
      // whether a pin is behind the object costs a ray through every face: five times a second
      // is plenty for the eye and keeps a tablet smooth
      var occ = now - lastOcc > 200;
      if (occ) lastOcc = now;
      pins.forEach(function (p) {
        v.copy(p.v).project(cam);
        var x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h;
        if (occ) {
          ray.set(cam.position, p.v.clone().sub(cam.position).normalize());
          var hit = ray.intersectObject(root, true)[0], far = cam.position.distanceTo(p.v);
          p.behind = !!(hit && hit.distance < far - 0.1);
        }
        p.el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
        // a point behind the object fades but stays tappable (a tap turns the set to face it);
        // a point under the button bar or off the view is not offered at all
        p.el.classList.toggle('behind', !!p.behind);
        p.el.classList.toggle('hid', v.z > 1 || x < 0 || x > w || y < 0 || y > h || underBar(x, y));
      });
    }
    function onSize() { fit(r, cam, host); }
    W.addEventListener('resize', onSize);
    if (W.ResizeObserver) new ResizeObserver(onSize).observe(host);
    onSize(); W.requestAnimationFrame(loop);
    return { focus: focus, reset: reset, pinState: pinState, setPins: setPins, camera: cam, root: root };
  }

  /* ---- a 360-degree place ------------------------------------------------------------- */
  function pano(host, o) {
    host.classList.add('g3');
    var r = renderer(host), scene = new T.Scene(), cam = new T.PerspectiveCamera(70, 1, 0.1, 100);
    var yaw = o.yaw || 0, pitch = o.pitch || 0, fov = 70;
    var lo = o.pitchMin === undefined ? -80 : o.pitchMin, hi = o.pitchMax === undefined ? 80 : o.pitchMax; // how far the view tilts
    function tilt(p) { return Math.max(lo, Math.min(hi, p)); }
    var tex = new T.TextureLoader().load(o.src, function () { if (o.onReady) o.onReady(); });
    tex.encoding = T.sRGBEncoding;
    var geo = new T.SphereGeometry(10, 64, 40); geo.scale(-1, 1, 1);
    scene.add(new T.Mesh(geo, new T.MeshBasicMaterial({ map: tex })));
    var markLayer = D.createElement('div'); markLayer.className = 'g3-pins'; host.appendChild(markLayer);
    var marks = [];

    function dirOf(yw, pt) { var y = yw * Math.PI / 180, p = pt * Math.PI / 180; return new T.Vector3(Math.sin(y) * Math.cos(p), Math.sin(p), -Math.cos(y) * Math.cos(p)); }
    function look() { cam.fov = fov; cam.updateProjectionMatrix(); cam.lookAt(dirOf(yaw, pitch)); }

    // one finger looks around; a tap (finger barely moved) reports where it looked
    var drag = null;
    r.domElement.style.touchAction = 'none';
    r.domElement.addEventListener('pointerdown', function (e) {
      if (drag || e.isPrimary === false) return;
      drag = { id: e.pointerId, x: e.clientX, y: e.clientY, yaw: yaw, pitch: pitch, moved: 0 };
      try { r.domElement.setPointerCapture(e.pointerId); } catch (x) {}
    });
    r.domElement.addEventListener('pointermove', function (e) {
      if (!drag || e.pointerId !== drag.id) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y, k = fov / host.clientHeight;
      drag.moved = Math.max(drag.moved, Math.abs(dx) + Math.abs(dy));
      yaw = drag.yaw - dx * k; pitch = tilt(drag.pitch + dy * k); look();
    });
    function end(e) {
      if (!drag || (e && e.pointerId !== drag.id)) return;
      var tap = e && e.type === 'pointerup' && drag.moved < 12;
      drag = null;
      if (tap && o.onLook) o.onLook(screenToAngles(e.clientX, e.clientY));
    }
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (ev) { r.domElement.addEventListener(ev, end); });
    W.addEventListener('blur', function () { drag = null; });

    function screenToAngles(cx, cy) {
      var b = r.domElement.getBoundingClientRect(), v = new T.Vector3((cx - b.left) / b.width * 2 - 1, -((cy - b.top) / b.height) * 2 + 1, 0.5);
      v.unproject(cam).sub(cam.position).normalize();
      return { yaw: ((Math.atan2(v.x, -v.z) * 180 / Math.PI) + 360) % 360, pitch: Math.asin(v.y) * 180 / Math.PI };
    }
    function angleTo(a, b) { // degrees between two looks
      var d1 = dirOf(a.yaw, a.pitch), d2 = dirOf(b.yaw, b.pitch);
      return Math.acos(Math.max(-1, Math.min(1, d1.dot(d2)))) * 180 / Math.PI;
    }
    function mark(id, yw, pt, cls, label) {
      var m = marks.filter(function (x) { return x.id === id; })[0];
      if (!m) {
        var el = D.createElement('div'); el.className = 'g3-mark'; markLayer.appendChild(el);
        m = { id: id, el: el }; marks.push(m);
      }
      m.v = dirOf(yw, pt).multiplyScalar(9); m.el.className = 'g3-mark ' + (cls || '');
      m.el.innerHTML = '<i></i>' + (label ? '<span>' + GBLab.esc(label) + '</span>' : '');
    }
    function turnTo(yw, pt) { yaw = yw; pitch = tilt(pt); look(); }
    controlsBar(host, [
      ['&#8592;', 'Look left', function () { yaw -= 2.5; look(); }], ['&#8594;', 'Look right', function () { yaw += 2.5; look(); }],
      ['&#8593;', 'Look up', function () { pitch = tilt(pitch + 2); look(); }], ['&#8595;', 'Look down', function () { pitch = tilt(pitch - 2); look(); }],
      ['&#65291;', 'Closer', function () { fov = Math.max(35, fov - 2); look(); }], ['&#65293;', 'Wider', function () { fov = Math.min(90, fov + 2); look(); }]
    ]);

    var v = new T.Vector3();
    function loop() {
      W.requestAnimationFrame(loop);
      r.render(scene, cam);
      var w = r.domElement.clientWidth, h = r.domElement.clientHeight;
      marks.forEach(function (m) {
        v.copy(m.v).project(cam);
        var x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h;
        m.el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';
        m.el.classList.toggle('hid', v.z > 1 || x < -40 || x > w + 40);
      });
    }
    function onSize() { fit(r, cam, host); look(); }
    W.addEventListener('resize', onSize);
    if (W.ResizeObserver) new ResizeObserver(onSize).observe(host);
    onSize(); W.requestAnimationFrame(loop);
    return { mark: mark, angleTo: angleTo, turnTo: turnTo, view: function () { return { yaw: yaw, pitch: pitch, fov: fov }; } };
  }

  W.GB3D = { model: model, pano: pano };
})(window, document);
