/* ==========================================================================
   audit_motion.js — L65: a drawing that moves stays smooth on a tablet (2.78.0).

   WHAT IT DECIDES
     Walks every slide (and every step of every kit figure on it) and finds each
     drawing (<svg>) where something moves FOR EVER - a flow, a fan, a spray, any
     endless CSS or SMIL animation. In such a drawing the tablet repaints the
     drawing on every frame, and two things make that frame expensive:
       filter   a CSS or SVG filter (drop-shadow, blur) on the drawing, on a
                shape or group inside it, or on an element around it on the slide
       mask     a mask on the drawing, inside it or around it
     Each is a FAILURE. Measured on the classroom tablets (Lenovo Yoga Tab 11,
     IGF M03, 2026-10-29): drop-shadows and masks in a drawing with a running flow
     kept the graphics chip 97 % busy - 32-43 fps, 65-100 ms hitches.
     Reported, never failed on (notes):
       layer    a moving drawing without its own compositing layer
                (will-change: transform) - 38 -> 60 fps on the tablet with it
       dash     how many endless animations move stroke-dashoffset - cheap once
                the two above are gone; transform or opacity is cheaper still

     A drawing where nothing moves for ever may keep its filters: they are drawn
     once. The kit's figures bake their shadows (kit.js bake) - the probe waits
     for that ([data-kit-baking]) before it looks.

   HOW TO RUN
     Defines the probe only; every entry point returns a Promise:

         await AuditMotion.all()         every slide of a deck
         await AuditMotion.page()        the whole page (a task page, the kit gallery)

     It prints one line, VERDICT: PASS or VERDICT: FAIL n=<count>, and sets
     window.__auditExit to 0 or 1 (also window.__audit.motion).
     run_audits.py loads it with the other deck probes.

   ES5-safe syntax, like the other probes.
   ========================================================================== */
(function (global) {
  "use strict";

  /* ======================= CONFIG — EDIT THIS BLOCK ======================= */
  var CONFIG = {
    slideSel: ".slide",
    activeClass: "active",
    transientClasses: ["leaving", "leaving-back", "prev", "next"],
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",
    settleMs: 560,                 /* > the slide transition */
    startSettleMs: 400,
    bakeWaitMs: 3000,              /* the kit's baked shadows: at most this long */
    walkKitSteps: true,            /* every step of a kit figure, not only the one it opens on */
    maxExamples: 6
  };
  /* ===================== END CONFIG — EDIT THIS BLOCK ===================== */
  if (global.__auditConfig) {
    for (var ck in global.__auditConfig) {
      if (Object.prototype.hasOwnProperty.call(global.__auditConfig, ck) && ck in CONFIG) { CONFIG[ck] = global.__auditConfig[ck]; }
    }
  }

  var NOT_DRAWN = "defs, symbol, clipPath, mask, marker, pattern, [data-kit-shade]";
  var SMIL = "animate, animateTransform, animateMotion, set";

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function qa(root, sel) {
    try { return Array.prototype.slice.call(root.querySelectorAll(sel)); } catch (e) { return []; }
  }
  function tag(el) { return (el.tagName || "").toLowerCase(); }
  function label(el) {
    var s = tag(el);
    if (el.id) { return s + "#" + el.id; }
    var c = (el.getAttribute && el.getAttribute("class")) || "";
    c = c.split(/\s+/).filter(function (x) { return x && !/^(active|on|kit-baked|kit-moving)$/.test(x); }).slice(0, 2);
    return s + (c.length ? "." + c.join(".") : "");
  }
  function drawingName(svg) {
    var k = svg.closest ? svg.closest("[id]") : null, all = qa(document, "svg"), name = svg.getAttribute("aria-label") || "";
    if (!name && k) {                                   // the nearest id, and which drawing under it
      var under = qa(k, "svg");
      name = k.id + (under.length > 1 ? " #" + (under.indexOf(svg) + 1) : "");
    }
    return label(svg) + (name ? ' "' + String(name).slice(0, 40) + '"' : " #" + (all.indexOf(svg) + 1));
  }

  /* the endless animations in a drawing, running now - CSS and Web Animations, and SMIL */
  function endless(svg) {
    var out = [];
    if (svg.getAnimations) {
      try {
        svg.getAnimations({ subtree: true }).forEach(function (a) {
          var t = a.effect && a.effect.getComputedTiming ? a.effect.getComputedTiming() : null;
          if (t && t.iterations === Infinity && a.playState === "running") { out.push(a); }
        });
      } catch (e) { /* an old engine: SMIL only */ }
    }
    qa(svg, SMIL).forEach(function (s) {
      if (/indefinite/.test((s.getAttribute("repeatCount") || "") + (s.getAttribute("repeatDur") || ""))) {
        out.push({ smil: s, effect: { target: s.parentNode } });
      }
    });
    return out;
  }
  function movesDash(a) {
    try {
      return a.effect.getKeyframes().some(function (k) { return "strokeDashoffset" in k || "stroke-dashoffset" in k; });
    } catch (e) { return a.smil ? a.smil.getAttribute("attributeName") === "stroke-dashoffset" : false; }
  }

  /* is it painted: no display:none or visibility:hidden up to the drawing, and not faded to nothing */
  function painted(el, svg, memo) {
    function vis(p) {
      if (memo.has(p)) { return memo.get(p); }
      var cs = getComputedStyle(p), v;
      if (cs.display === "none" || cs.visibility === "hidden") { v = 0; }
      else if (p === svg || !p.parentElement) { v = parseFloat(cs.opacity); }
      else { v = vis(p.parentElement) * parseFloat(cs.opacity); }
      memo.set(p, v);
      return v;
    }
    return vis(el) > 0.001;
  }
  function filterOf(cs) { return cs.filter && cs.filter !== "none" ? cs.filter : ""; }
  function maskOf(el, cs) {
    var m = cs.getPropertyValue("mask") || "", mi = cs.getPropertyValue("mask-image") || cs.getPropertyValue("-webkit-mask-image") || "";
    if (m && m !== "none") { return m; }
    if (mi && mi !== "none") { return mi; }
    return (el.getAttribute && el.getAttribute("mask")) || "";
  }

  /* one drawing: does something move for ever, and what makes its frame expensive */
  function drawing(svg, step) {
    var live = endless(svg);
    if (!live.length) { return null; }
    var memo = new Map(), hits = [], seen = {};
    function add(el, what, value, around) {
      var key = label(el) + "|" + what;
      if (seen[key]) { return; }
      seen[key] = 1;
      hits.push({ el: label(el), what: what, value: String(value).slice(0, 80), around: !!around, step: step || 0 });
    }
    [svg].concat(qa(svg, "*")).forEach(function (el) {
      if (el !== svg && el.closest && el.closest(NOT_DRAWN)) { return; }
      if (tag(el) === "mask" || tag(el) === "filter") { return; }
      if (!painted(el, svg, memo)) { return; }
      var cs = getComputedStyle(el), f = filterOf(cs), m = maskOf(el, cs);
      if (f) { add(el, "filter", f); }
      if (m) { add(el, "mask", m); }
    });
    var stop = svg.closest ? svg.closest(CONFIG.slideSel) : null;
    for (var p = svg.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      var pcs = getComputedStyle(p), pf = filterOf(pcs), pm = maskOf(p, pcs);
      if (pf) { add(p, "filter", pf, true); }
      if (pm) { add(p, "mask", pm, true); }
      if (p === stop) { break; }
    }
    var scs = getComputedStyle(svg);
    var layer = /transform/.test(scs.willChange || "") || (scs.transform && scs.transform !== "none");
    return {
      node: svg,
      svg: drawingName(svg),
      moving: live.length,
      dash: live.filter(movesDash).length,
      layer: !!layer,
      hits: hits
    };
  }
  function drawingsIn(root) {
    return qa(root, "svg").filter(function (s) {
      return !s.ownerSVGElement && !s.hasAttribute("data-audit-ignore") && !(s.classList && s.classList.contains("kit-materials"));
    });
  }
  function waitBakes(root) {
    var t0 = Date.now();
    function poll() {
      if (!root.querySelector("[data-kit-baking]") || Date.now() - t0 > CONFIG.bakeWaitMs) { return Promise.resolve(); }
      return sleep(50).then(poll);
    }
    return sleep(80).then(poll);
  }
  /* the kit figures in this root: each walked through its steps, the drawings checked at every one */
  function kitFigures(root) {
    var K = global.KIT;
    if (!CONFIG.walkKitSteps || !K || !K.figures) { return []; }
    return K.figures.filter(function (f) { return f && f.svg && root.contains(f.svg) && f.steps && f.steps() > 0; });
  }
  function merge(into, d) {
    if (!d) { return; }
    var have = null;
    into.forEach(function (x) { if (x.node === d.node) { have = x; } });
    if (!have) { into.push(d); return; }
    have.moving = Math.max(have.moving, d.moving);
    have.dash = Math.max(have.dash, d.dash);
    have.layer = have.layer && d.layer;
    d.hits.forEach(function (h) {
      if (!have.hits.some(function (x) { return x.el === h.el && x.what === h.what; })) { have.hits.push(h); }
    });
  }
  function check(root) {
    var out = [];
    return waitBakes(root).then(function () {
      drawingsIn(root).forEach(function (s) { merge(out, drawing(s)); });
      var figs = kitFigures(root);
      function walk(i) {
        if (i >= figs.length) { return Promise.resolve(); }
        var f = figs[i], n0 = f.n || 0, k = 0;
        function stepTo() {
          k++;
          if (k > f.steps()) {
            try { f.go(n0, true); } catch (e) { /* left at its last step */ }
            return waitBakes(root).then(function () { return walk(i + 1); });
          }
          try { f.go(k, true); } catch (e) { return stepTo(); }
          return waitBakes(root).then(function () { merge(out, drawing(f.svg, k)); return stepTo(); });
        }
        return stepTo();
      }
      return walk(0);
    }).then(function () { return out; });
  }

  function line(d, h) {
    return d.svg + (h.step ? " at step " + h.step : "") + ": " + h.what + (h.around ? " around it on " : " on ") + h.el + " (" + h.value + ")";
  }
  function finish(rows, total, mode) {
    var failing = [], notes = [], n = 0, moving = 0;
    rows.forEach(function (r) {
      var hits = [];
      r.drawings.forEach(function (d) {
        delete d.node;                                  // the element itself: not for the JSON
        moving++;
        d.hits.forEach(function (h) { hits.push(line(d, h)); });
        if (!d.layer) { notes.push((r.slide ? "slide " + r.slide + ": " : "") + d.svg + " moves without its own layer (will-change: transform)"); }
        if (d.dash) { notes.push((r.slide ? "slide " + r.slide + ": " : "") + d.svg + " " + d.dash + " endless stroke-dashoffset animation(s)"); }
      });
      if (hits.length) {
        n += hits.length;
        failing.push({ slide: r.slide, id: r.id, hits: hits.slice(0, CONFIG.maxExamples), more: Math.max(0, hits.length - CONFIG.maxExamples) });
      }
    });
    var res = { mode: mode, slidesTotal: total, movingDrawings: moving, failures: n, failingSlides: failing, notes: notes,
                rows: rows };
    global.__auditExit = n ? 1 : 0;
    res.verdict = n ? "VERDICT: FAIL n=" + n : "VERDICT: PASS";
    if (global.console) { console.log("audit_motion " + moving + " moving drawing(s)  " + res.verdict); }
    return res;
  }
  function pressStart() {
    var sb = null;
    try { sb = document.querySelector(CONFIG.startBtnSel); } catch (e) { sb = null; }
    if (sb && getComputedStyle(sb).display !== "none") { sb.click(); return sleep(CONFIG.startSettleMs); }
    return Promise.resolve();
  }
  function activate(slides, i) {
    slides.forEach(function (x, j) {
      CONFIG.transientClasses.forEach(function (c) { x.classList.remove(c); });
      if (j === i) { x.classList.add(CONFIG.activeClass); } else { x.classList.remove(CONFIG.activeClass); }
    });
    try { global.dispatchEvent(new Event("resize")); } catch (e) { /* an old engine */ }
  }

  /* only = [slide index from 0, ...] (run_audits.py): just those slides */
  function all(only) {
    return pressStart().then(function () {
      var slides = qa(document, CONFIG.slideSel);
      if (!slides.length) { return page(); }
      var rows = [];
      function next(i) {
        if (i >= slides.length) { return Promise.resolve(); }
        if (only && only.indexOf(i) < 0) { return next(i + 1); }
        activate(slides, i);
        return sleep(CONFIG.settleMs).then(function () { return check(slides[i]); }).then(function (ds) {
          rows.push({ slide: i + 1, id: slides[i].id || "", drawings: ds });
          return next(i + 1);
        });
      }
      return next(0).then(function () { return finish(rows, slides.length, "deck"); });
    }).catch(function (e) {
      global.__auditExit = 1;
      if (global.console) { console.error("audit_motion aborted: " + (e && e.stack || e)); }
      return { ABORTED: String(e && e.message || e), verdict: "VERDICT: FAIL n=1" };
    });
  }
  function page() {
    return check(document.body).then(function (ds) { return finish([{ slide: 0, id: "", drawings: ds }], 0, "page"); });
  }

  var api = { all: all, page: page, drawing: drawing, endless: endless, CONFIG: CONFIG };
  global.__audit = global.__audit || {};
  global.__audit.motion = api;
  global.AuditMotion = api;
})(window);
