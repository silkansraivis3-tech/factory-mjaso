/* ==========================================================================
   audit_opacity.js — course-agnostic contrast probe for the case where
   ELEMENT OPACITY is in play.

   WHAT IT DOES
     audit_deck.js computes contrast from `color` against the nearest painted
     `background-color`. It never looks at `opacity`, and an element at
     opacity:.68 is composited toward its background BEFORE the eye sees it.
     A caption measured naively at 6.4:1 was 4.02:1 in truth — under AA — and
     an element at opacity:.9 measured 4.15:1 the same way. This probe walks
     every slide, multiplies the inherited opacity chain into the text colour's
     alpha, composites it over the ancestor background, and reports every text
     element whose TRUE ratio is under the threshold for its size.

     Elements at effectively full opacity are skipped — audit_deck.js already
     covers those, and reporting them twice doubles every count.

   HOW TO RUN
     Only DEFINES the probe. Async — MUST be awaited:

         await AuditOpacity.all()          every slide
         await AuditOpacity.slice(0, 9)    slides 1-9
         AuditOpacity.spec()               the thresholds it applies

     (also registered as window.__audit.opacity)

     Prints a single-line verdict and sets window.__auditExit to 0 or 1.

   TO PORT TO ANOTHER DECK
     Edit the CONFIG block. Nothing else names a course, a path or a port.
     window.__auditOpacityConfig = {...} set BEFORE load overrides it.

   TWO TRAPS THAT ARE THE WHOLE REASON THIS FILE IS DELICATE

     1  THE OPACITY WALK STOPS AT THE SLIDE. A deck fades its slides, so the
        slide's own opacity must NOT be multiplied in — otherwise every
        element on a settling slide reads opacity 0 and ratio 1:1, and the
        report is pure fiction.

     2  A TRANSITIONED OPACITY CANNOT BE TRUSTED IN AN AUTOMATED PANE. A
        headless or backgrounded pane does not composite reliably, so an
        element that fades 0 -> 1 can compute 0 for ever. Any element whose
        opacity is UNDER A TRANSITION is therefore skipped: its resting state
        is the revealed value, which in the usual deck idiom is 1. A STATIC
        reduced opacity — the real defect — carries no transition and is still
        measured.

        AND THE DURATION TEST IS NOT OPTIONAL. `transition-property`'s INITIAL
        value is the keyword `all`, so getComputedStyle().transitionProperty
        returns "all" for every element that declares no transition at all.
        Test the property alone and the guard matches EVERYTHING and turns the
        whole probe into a silent no-op that reports zero failures across
        every slide. An element only transitions if a matching property is
        listed AND its duration is non-zero. Both are required. Keep both.

   Other traps honoured: settle past the slide transition (floored at 520 ms),
   filter on `display` ONLY and never on `visibility`, reveal every frag
   first, refuse to run in a collapsed pane against a MINIMUM WIDTH.

   ES5-safe syntax (no arrow functions, no optional chaining, no ??).
   ========================================================================== */
(function (global) {
  "use strict";

  /* ======================= CONFIG — EDIT THIS BLOCK ======================= */
  var CONFIG = {
    deckLabel: "",                 /* blank -> window.location.href */

    /* --- structural selectors --- */
    slideSel: ".slide",            /* CHANGE: one deck page. ALSO the element
                                      the opacity walk stops at — see trap 1.
                                      It must be the element your deck fades. */
    fragSel: ".frag",              /* CHANGE: progressive-reveal element */
    activeClass: "active",         /* CHANGE */
    fragOnClass: "on",             /* CHANGE */
    transientClasses: ["leaving", "leaving-back", "prev", "next"],  /* CHANGE */
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",      /* CHANGE */

    /* --- timing --- */
    settleMs: 560,                 /* > your slide transition duration */
    minSettleMs: 520,              /* hard floor; do not lower */
    startSettleMs: 400,

    /* --- refuse-to-run guards --- */
    /* A DEGENERACY guard, not a size preference - see audit_drive.js. 900 wide
       rejected 800x1280, a NOVIKONTAS tablet in portrait. */
    minViewportWidth: 320,
    minViewportHeight: 320,

    /* --- measurement thresholds (same as audit_deck.js) --- */
    opacityFloor: 0.995,           /* at or above this, audit_deck.js owns it */
    contrastNormal: 4.5,
    contrastLarge: 3.0,
    largePx: 24,                   /* >= this px counts as large text */
    largeBoldPx: 18.66,            /* >= this px AND bold counts as large */
    boldWeight: 700,
    skipTransitionedOpacity: true,  /* trap 2. Turning this OFF in a REAL,
                                      fronted browser gives wider coverage;
                                      leave it ON in any automated pane. */

    /* --- reporting --- */
    txtSample: 22
  };
  /* ===================== END CONFIG — EDIT THIS BLOCK ===================== */

  if (global.__auditOpacityConfig) {
    for (var ck in global.__auditOpacityConfig) {
      if (Object.prototype.hasOwnProperty.call(global.__auditOpacityConfig, ck)) {
        CONFIG[ck] = global.__auditOpacityConfig[ck];
      }
    }
  }

  function settleMs() { return Math.max(CONFIG.settleMs, CONFIG.minSettleMs); }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function q(sel) {
    if (!sel) { return null; }
    try { return document.querySelector(sel); } catch (e) { return null; }
  }
  function qa(root, sel) {
    if (!sel) { return []; }
    try { return Array.prototype.slice.call(root.querySelectorAll(sel)); }
    catch (e) { return []; }
  }

  /* ---------------------------- colour maths ---------------------------- */
  function parse(c) {
    var m = /^rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/
      .exec((c || "").trim());
    return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null;
  }
  function lin(v) {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  }
  function lum(c) { return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]); }
  function over(f, b) {
    var a = f[3];
    return [f[0] * a + b[0] * (1 - a),
            f[1] * a + b[1] * (1 - a),
            f[2] * a + b[2] * (1 - a), 1];
  }
  /* ancestor walk only — cannot see a background painted by a SIBLING */
  function bgOf(el) {
    var n = el;
    while (n && n !== document.documentElement) {
      var c = parse(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) {
        return c[3] < 1 ? over(c, bgOf(n.parentElement || document.body)) : c;
      }
      n = n.parentElement;
    }
    return [255, 255, 255, 1];
  }
  function weightOf(st) {
    var w = parseInt(st.fontWeight, 10);
    if (!isNaN(w)) { return w; }
    var k = (st.fontWeight || "").toLowerCase();
    return (k === "bold" || k === "bolder") ? 700 : 400;
  }
  function needFor(fs, st) {
    return (fs >= CONFIG.largePx ||
            (fs >= CONFIG.largeBoldPx && weightOf(st) >= CONFIG.boldWeight))
      ? CONFIG.contrastLarge : CONFIG.contrastNormal;
  }

  /* --------------------------- the opacity walk --------------------------- */
  /* BOTH conditions are required. See trap 2 in the header. */
  function fading(el, slide) {
    var n = el;
    while (n && n !== slide) {
      var st = getComputedStyle(n);
      var tp = st.transitionProperty || "";
      var moves = (tp.indexOf("opacity") >= 0 || tp.indexOf("all") >= 0);
      var runs = (st.transitionDuration || "").split(",").some(function (d) {
        return parseFloat(d) > 0;
      });
      if (moves && runs) { return true; }
      n = n.parentElement;
    }
    return false;
  }
  /* stops AT the slide — the slide's own fade is excluded. Trap 1. */
  function ownOpacity(el, slide) {
    var o = 1, n = el;
    while (n && n !== slide) {
      var v = parseFloat(getComputedStyle(n).opacity);
      if (!isNaN(v)) { o *= v; }
      n = n.parentElement;
    }
    return o;
  }

  function selOf(el) {
    return el.tagName.toLowerCase() +
      (typeof el.className === "string" && el.className.trim()
        ? "." + el.className.trim().split(/\s+/)[0] : "");
  }

  function auditSlide(slide, n) {
    var bad = [], skippedFading = 0;
    qa(slide, "*").forEach(function (el) {
      if (el.namespaceURI && el.namespaceURI.indexOf("svg") >= 0) { return; }
      var st = getComputedStyle(el);
      if (st.display === "none") { return; }   /* NOT visibility — see header */
      var has = Array.prototype.some.call(el.childNodes, function (t) {
        return t.nodeType === 3 && t.textContent.trim();
      });
      if (!has) { return; }
      if (CONFIG.skipTransitionedOpacity && fading(el, slide)) {
        skippedFading++;
        return;                                /* frozen transition — unreadable */
      }
      var op = ownOpacity(el, slide);
      if (op >= CONFIG.opacityFloor) { return; }   /* audit_deck.js owns these */
      var bg = bgOf(el), fg = parse(st.color);
      if (!fg) { return; }
      fg = over([fg[0], fg[1], fg[2], fg[3] * op], bg);
      var a = lum(fg), b = lum(bg);
      var r = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      var fs = parseFloat(st.fontSize);
      var need = needFor(fs, st);
      if (r < need) {
        bad.push({ slide: n, sel: selOf(el), opacity: +op.toFixed(2),
                   ratio: +r.toFixed(2), need: need, px: +fs.toFixed(1),
                   txt: (el.textContent || "").trim().slice(0, CONFIG.txtSample) });
      }
    });
    return { bad: bad, skippedFading: skippedFading };
  }

  /* ------------------------------- the sweep ------------------------------ */
  function spec() {
    return {
      opacityFloor: CONFIG.opacityFloor,
      contrast: CONFIG.contrastNormal + ":1 normal, " + CONFIG.contrastLarge +
                ":1 at >=" + CONFIG.largePx + "px or >=" + CONFIG.largeBoldPx +
                "px weight " + CONFIG.boldWeight,
      opacityWalkStopsAt: CONFIG.slideSel,
      skipTransitionedOpacity: CONFIG.skipTransitionedOpacity,
      settleMs: settleMs(),
      minViewport: [CONFIG.minViewportWidth, CONFIG.minViewportHeight]
    };
  }

  function guardViewport() {
    var w = window.innerWidth || 0, h = window.innerHeight || 0;
    if (w >= CONFIG.minViewportWidth && h >= CONFIG.minViewportHeight) {
      return null;
    }
    var msg = "!!! AUDIT ABORTED — VIEWPORT TOO SMALL: " + w + "x" + h +
      " (minimum " + CONFIG.minViewportWidth + "x" + CONFIG.minViewportHeight +
      "). A hidden or collapsed browser pane lays out at 0x0; font sizes " +
      "collapse and the size threshold picks the wrong contrast target. " +
      "Front the tab, then re-run.";
    if (global.console) { console.error(msg); }
    return { ABORTED: msg, viewport: [w, h] };
  }

  function pressStart() {
    var sb = q(CONFIG.startBtnSel);
    if (sb && getComputedStyle(sb).display !== "none") {
      sb.click();
      return sleep(CONFIG.startSettleMs);
    }
    return Promise.resolve();
  }
  function activate(slides, i) {
    slides.forEach(function (x, j) {
      CONFIG.transientClasses.forEach(function (c) { x.classList.remove(c); });
      if (j === i) { x.classList.add(CONFIG.activeClass); }
      else { x.classList.remove(CONFIG.activeClass); }
    });
  }
  function revealFrags(slide) {
    qa(slide, CONFIG.fragSel).forEach(function (f) {
      f.classList.add(CONFIG.fragOnClass);
    });
  }

  function verdict(res) {
    var fail, n;
    if (res && res.ABORTED) { fail = true; n = 1; }
    else { n = res.failures; fail = n > 0; }
    global.__auditExit = fail ? 1 : 0;
    var line = fail ? ("VERDICT: FAIL n=" + n) : "VERDICT: PASS";
    if (global.console) { console.log(line); }
    res.verdict = line;
    return res;
  }

  function slice(from, to) {
    from = from || 0;
    var abort = guardViewport();
    if (abort) { return Promise.resolve(verdict(abort)); }

    return pressStart().then(function () {
      var slides = qa(document, CONFIG.slideSel);
      if (!slides.length) {
        var m = "!!! AUDIT ABORTED — no elements match CONFIG.slideSel (" +
                CONFIG.slideSel + "). Set it to this deck's slide selector.";
        if (global.console) { console.error(m); }
        return verdict({ ABORTED: m,
                         viewport: [window.innerWidth, window.innerHeight] });
      }
      var hi = Math.min(to === undefined ? slides.length : to, slides.length);
      var bad = [], skipped = 0;

      function step(i) {
        if (i >= hi) { return Promise.resolve(); }
        activate(slides, i);
        revealFrags(slides[i]);
        return sleep(settleMs()).then(function () {
          var r = auditSlide(slides[i], i + 1);
          bad = bad.concat(r.bad);
          skipped += r.skippedFading;
          return step(i + 1);
        });
      }
      return step(from).then(function () {
        var res = {
          page: CONFIG.deckLabel || window.location.href,
          viewport: [window.innerWidth, window.innerHeight],
          range: (from + 1) + ".." + hi,
          slidesTotal: slides.length,
          failures: bad.length,
          /* NOT a pass: these were unmeasurable, not clean. If this number is
             large and failures is 0, the guard is eating the probe — re-run in
             a real fronted browser with skipTransitionedOpacity false. */
          skippedUnderTransition: skipped,
          bad: bad
        };
        if (global.console) {
          console.log("audit_opacity " + res.page + "  viewport " +
                      res.viewport[0] + "x" + res.viewport[1] +
                      "  slides " + res.range + "/" + res.slidesTotal +
                      "  failures " + res.failures +
                      "  skipped-under-transition " + skipped);
        }
        return verdict(res);
      });
    });
  }

  function all() { return slice(0, undefined); }

  var api = { all: all, slice: slice, auditSlide: auditSlide, spec: spec,
              CONFIG: CONFIG, settleMs: settleMs, guardViewport: guardViewport,
              pressStart: pressStart, activate: activate,
              revealFrags: revealFrags, verdict: verdict,
              fading: fading, ownOpacity: ownOpacity };

  global.__audit = global.__audit || {};
  global.__audit.opacity = api;
  global.AuditOpacity = api;
})(typeof window !== "undefined" ? window : this);
