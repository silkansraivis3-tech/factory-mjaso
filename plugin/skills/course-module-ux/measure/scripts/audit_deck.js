/* ==========================================================================
   audit_deck.js — course-agnostic deck audit probe.

   WHAT IT DOES
     Walks every slide of an HTML deck, reveals every progressive-reveal
     element, waits for the slide transition to settle, and measures:
       low       text contrast below the WCAG threshold for its size
       small     text below the minimum readable px
       spill     elements overhanging the slide box
       tap       controls below the minimum touch-target px
       svgSmall  SVG <text> whose EFFECTIVE px (declared x render scale) is small
       collide   absolutely-positioned labels printing over each other
     plus per-slide weighted-median font px, content fill %, in-slide link
     count, and whether the document scrolls horizontally.

   HOW TO RUN
     Not an IIFE that measures on load — it only DEFINES the probe. It is
     async and MUST be awaited:

         await AuditDeck.all()          every slide
         await AuditDeck.slice(0, 9)    slides 1-9
         AuditDeck.spec()               the thresholds it applies

     (also registered as window.__audit.deck)

     It prints a single-line verdict and sets window.__auditExit to 0 or 1 so
     a wrapper can turn the run into a process exit code.

   TO PORT TO ANOTHER DECK
     Edit the CONFIG block below — nothing else in this file names a course, a
     module, a path or a port. You can also override CONFIG without editing
     the file by setting window.__auditConfig = {...} BEFORE loading it.

   TRAPS THIS FILE ALREADY HONOURS (do not "simplify" them away)
     * A slide that transitions opacity/visibility is still computing
       visibility:hidden 150 ms after activation. A probe that skips hidden
       elements then measures NOTHING and reports a clean sweep. So: wait
       CONFIG.settleMs (floored at CONFIG.minSettleMs = 520) and filter on
       `display` ONLY, never on `visibility`.
     * A hidden or collapsed browser pane lays out at 0x0 and every geometry
       number becomes garbage. Refused up front against a MINIMUM WIDTH, not
       merely against zero.
     * Geometry is read from offsetLeft/offsetTop/offsetWidth/offsetHeight
       where possible, because getBoundingClientRect() is post-transform and
       decks scale slides.
     * SVG <text> has no CSS background, so an ancestor walk returns ~1.09:1
       for every node. SVG text is reported by SIZE only. Composite its
       contrast by hand.
     * Contrast by walking ANCESTORS cannot see a background painted by a
       SIBLING. An element overlapping a painted sibling must be composited
       by hand; this probe will report it as passing.
     * Toggling the active class by hand skips the deck engine's own per-slide
       layout hook (pin placement, label nudging). A resize event is
       dispatched after activation because such hooks normally listen for it.
       If your deck's hook is not resize-bound, drive the deck instead —
       see audit_drive.js.
     * `spill` OVER-REPORTS by design: an element the engine has hidden with
       inline visibility:hidden still occupies a box. Each spill entry carries
       its computed `vis` so phantoms are identifiable; set
       CONFIG.countHiddenVisibilitySpills = false to drop them from the count.

   ES5-safe syntax (no arrow functions, no optional chaining, no ??). Requires
   a Promise implementation.
   ========================================================================== */
(function (global) {
  "use strict";

  /* ======================= CONFIG — EDIT THIS BLOCK ======================= */
  var CONFIG = {
    /* --- structural selectors. These are the ones to change per deck. --- */
    slideSel: ".slide",            /* CHANGE: one deck page */
    fragSel: ".frag",              /* CHANGE: progressive-reveal element */
    activeClass: "active",         /* CHANGE: class marking the shown slide */
    fragOnClass: "on",             /* CHANGE: class marking a revealed frag */
    transientClasses: ["leaving", "leaving-back", "prev", "next"],
                                   /* CHANGE: classes stripped before activating
                                      a slide, so no outgoing-slide animation
                                      state is left behind */
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",
                                   /* CHANGE: title-screen button that has to be
                                      pressed before slide 1 exists. Optional —
                                      no match is fine. */
    contentRegionSels: [".slide-body", ".slide-content", ".content"],
                                   /* CHANGE: the inner region that actually
                                      holds slide content, for the fill %.
                                      First match wins; the slide itself is the
                                      fallback. */
    labelSels: [".pin-lbl", ".pin-label", ".hlabel", "[data-label]"],
                                   /* CHANGE: absolutely-positioned callout
                                      labels, pairwise-tested for overlap.
                                      Empty array disables that check. */
    controlSel: "button, a, input, select, textarea, [role=button]",
                                   /* CHANGE: what counts as a touch target */

    /* --- timing --- */
    settleMs: 560,                 /* > your slide transition duration */
    minSettleMs: 520,              /* hard floor; do not lower */
    startSettleMs: 400,            /* after pressing the start button */
    dispatchResize: true,          /* re-run resize-bound per-slide layout */

    /* --- refuse-to-run guards --- */
    minViewportWidth: 900,         /* CHANGE for a tablet/phone deck */
    minViewportHeight: 400,

    /* --- measurement thresholds --- */
    minFontPx: 12.5,
    minControlPx: 44,
    contrastNormal: 4.5,
    contrastLarge: 3.0,
    largePx: 24,                   /* >= this px counts as large text */
    largeBoldPx: 18.66,            /* >= this px AND bold counts as large */
    boldWeight: 700,
    spillTolPx: 1,                 /* px of overhang before it counts */
    countHiddenVisibilitySpills: true,
    fillMax: 100,                  /* fill above this is overflow, even when the
                                      spill probe is silent -- a flex-centred body
                                      pushes residual content UPWARD into the
                                      header band instead of off the bottom */

    /* --- advisory only, never failed on (as in the original) --- */
    projectorMedianPx: 19,
    projectorMedianAtWidth: 1920,

    /* --- reporting --- */
    maxExamples: 4,
    maxTapExamples: 3,
    txtSample: 30,
    svgTxtSample: 22
  };
  /* ===================== END CONFIG — EDIT THIS BLOCK ===================== */

  if (global.__auditConfig) {
    for (var ck in global.__auditConfig) {
      if (Object.prototype.hasOwnProperty.call(global.__auditConfig, ck)) {
        CONFIG[ck] = global.__auditConfig[ck];
      }
    }
  }

  function simpleClass(sel) {
    return /^\.[A-Za-z0-9_-]+$/.test(sel) ? sel.slice(1) : "";
  }
  /* class names that are pure state and would only add noise to a selector
     label in the report */
  var NOISE = [CONFIG.activeClass, CONFIG.fragOnClass, simpleClass(CONFIG.fragSel)]
    .concat(CONFIG.transientClasses);

  function settleMs() { return Math.max(CONFIG.settleMs, CONFIG.minSettleMs); }
  function sleep(ms) {
    return new Promise(function (r) { setTimeout(r, ms); });
  }
  function q(sel) {
    if (!sel) { return null; }
    try { return document.querySelector(sel); } catch (e) { return null; }
  }
  function qa(root, sel) {
    if (!sel) { return []; }
    try { return Array.prototype.slice.call(root.querySelectorAll(sel)); }
    catch (e) { return []; }
  }
  function fireResize() {
    if (!CONFIG.dispatchResize) { return; }
    var ev;
    try { ev = new Event("resize"); }
    catch (e) {
      ev = document.createEvent("Event");
      ev.initEvent("resize", true, true);
    }
    window.dispatchEvent(ev);
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
  /* NOTE: ancestor walk only. Cannot see a background painted by a SIBLING. */
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
  function ratio(el) {
    var s = getComputedStyle(el), fg = parse(s.color);
    if (!fg) { return null; }
    var bg = bgOf(el);
    if (fg[3] < 1) { fg = over(fg, bg); }
    var a = lum(fg), b = lum(bg);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
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

  /* ------------------------------ labelling ------------------------------ */
  function label(el) {
    var s = el.tagName.toLowerCase();
    if (typeof el.className === "string" && el.className.trim()) {
      var c = el.className.trim().split(/\s+/).filter(function (x) {
        return NOISE.indexOf(x) < 0;
      }).slice(0, 2).join(".");
      if (c) { s += "." + c; }
    }
    return s;
  }
  function ownText(el) {
    return Array.prototype.filter.call(el.childNodes, function (n) {
      return n.nodeType === 3 && n.textContent.trim();
    }).map(function (n) { return n.textContent.trim(); }).join(" ");
  }
  function isSvg(el) {
    return !!(el.namespaceURI && el.namespaceURI.indexOf("svg") >= 0);
  }

  /* ------------------------------- geometry -------------------------------
     Every box in this file is expressed in the ROOT'S LAYOUT SPACE — px
     relative to the slide's top-left, unscaled — so offset-derived and
     rect-derived boxes are mutually comparable and can be mixed freely.

     offset* is preferred, because a scaled or translated deck makes every
     getBoundingClientRect number a RENDERED number while the question here is
     whether an element overhangs its slide in LAYOUT terms.

     offsetBox returns null in the two cases where offsets are not merely
     imprecise but WRONG, and the caller then falls back to a normalised rect:

       a) the offsetParent chain escapes the root — fixed positioning, or a
          root that is not itself a positioned element;
       b) THE ELEMENT GENERATES MORE THAN ONE BOX — i.e. a wrapped inline.
          Measured live: a <b> wrapping across two lines reported
          offsetLeft 1627 (the left edge of its FIRST line box) with
          offsetWidth 1463 (the width of the UNION of all its boxes). Adding
          those gives right = 3090 on a 1920-wide slide and invents a 1170 px
          spill. Its true union box is left 273, right 1736 — inside the
          slide. Do not remove this test. */
  function offsetBox(el, root) {
    if (!el || typeof el.offsetWidth !== "number") { return null; }
    if (el.getClientRects && el.getClientRects().length > 1) { return null; }
    var l = 0, t = 0, n = el, guard = 0;
    while (n && n !== root && guard++ < 300) {
      l += n.offsetLeft || 0;
      t += n.offsetTop || 0;
      n = n.offsetParent;
    }
    if (n !== root) { return null; }
    return { left: l, top: t, width: el.offsetWidth, height: el.offsetHeight,
             right: l + el.offsetWidth, bottom: t + el.offsetHeight };
  }
  /* rendered rect, divided back out of any scale the deck applies to the
     slide, so the result is in the same layout space as offsetBox */
  function rectBox(el, root) {
    var a = el.getBoundingClientRect(), b = root.getBoundingClientRect();
    var sx = 1, sy = 1;
    if (root.offsetWidth && b.width) { sx = b.width / root.offsetWidth; }
    if (root.offsetHeight && b.height) { sy = b.height / root.offsetHeight; }
    if (!sx || isNaN(sx)) { sx = 1; }
    if (!sy || isNaN(sy)) { sy = 1; }
    return { left: (a.left - b.left) / sx, top: (a.top - b.top) / sy,
             width: a.width / sx, height: a.height / sy,
             right: (a.right - b.left) / sx, bottom: (a.bottom - b.top) / sy,
             scale: [sx, sy] };
  }
  function boxIn(el, root) {
    var o = offsetBox(el, root);
    if (o) { return o; }
    var r = rectBox(el, root);
    r.viaRect = true;
    return r;
  }
  function rootExtent(root) {
    if (typeof root.offsetWidth === "number" && root.offsetWidth) {
      return { w: root.offsetWidth, h: root.offsetHeight };
    }
    var r = root.getBoundingClientRect();
    return { w: r.width, h: r.height };
  }
  function overlaps(A, B) {
    if (A.right <= B.left || B.right <= A.left) { return false; }
    if (A.bottom <= B.top || B.bottom <= A.top) { return false; }
    return true;
  }

  /* ------------------------------ one slide ------------------------------ */
  function auditSlide(s, n) {
    var ext = rootExtent(s);
    var out = { slide: n, low: [], small: [], spill: [], tap: [],
                svgSmall: [], collide: [] };
    var sizes = [], chars = 0;

    qa(s, "*").forEach(function (el) {
      if (isSvg(el)) { return; }
      var st = getComputedStyle(el);
      if (st.display === "none") { return; }   /* NOT visibility — see the header */

      var t = ownText(el);
      if (t) {
        var fs = parseFloat(st.fontSize), r = ratio(el);
        sizes.push([fs, t.length]);
        chars += t.length;
        var need = needFor(fs, st);
        if (fs < CONFIG.minFontPx) {
          out.small.push({ sel: label(el), px: +fs.toFixed(1),
                           txt: t.slice(0, CONFIG.txtSample) });
        }
        if (r && r < need) {
          out.low.push({ sel: label(el), ratio: +r.toFixed(2), need: need,
                         px: +fs.toFixed(1), txt: t.slice(0, CONFIG.txtSample) });
        }
      }

      var b = boxIn(el, s), tol = CONFIG.spillTolPx;
      if (b.width && (b.right > ext.w + tol || b.bottom > ext.h + tol ||
                      b.left < -tol)) {
        if (CONFIG.countHiddenVisibilitySpills || st.visibility !== "hidden") {
          out.spill.push({ sel: label(el),
                           byPx: Math.round(Math.max(b.right - ext.w,
                                                     b.bottom - ext.h)),
                           vis: st.visibility,
                           viaRect: !!b.viaRect });
        }
      }
    });

    qa(s, CONFIG.controlSel).forEach(function (e) {
      var w = e.offsetWidth, h = e.offsetHeight;
      if (typeof w !== "number" || (!w && !h)) {
        var rr = e.getBoundingClientRect(); w = rr.width; h = rr.height;
      }
      if (w > 0 && (w < CONFIG.minControlPx || h < CONFIG.minControlPx)) {
        out.tap.push({ sel: label(e), w: Math.round(w), h: Math.round(h) });
      }
    });

    /* SVG text: SIZE only. Effective px = declared font-size x
       (rendered width / viewBox width). Never the declared value on its own.
       getBoundingClientRect is used deliberately here: SVG elements expose no
       offsetWidth, and the RENDERED width is exactly what this formula wants. */
    qa(s, "svg").forEach(function (sv) {
      var vb = (sv.getAttribute("viewBox") || "").split(/[\s,]+/).map(Number);
      var w = sv.getBoundingClientRect().width;
      if (!vb[2] || !w) { return; }
      var sc = w / vb[2];
      qa(sv, "text").forEach(function (t) {
        var f = parseFloat(getComputedStyle(t).fontSize);
        if (!f || isNaN(f)) { f = parseFloat(t.getAttribute("font-size")) || 0; }
        var eff = f * sc;
        if (eff && eff < CONFIG.minFontPx) {
          out.svgSmall.push({ declaredPx: +f.toFixed(2), scale: +sc.toFixed(3),
                              effPx: +eff.toFixed(1),
                              txt: (t.textContent || "").trim()
                                     .slice(0, CONFIG.svgTxtSample) });
        }
      });
    });

    /* absolutely-positioned labels printing over each other. boxIn() puts
       offset- and rect-derived boxes in one layout space, so they mix. */
    var lbls = [];
    CONFIG.labelSels.forEach(function (sel) {
      qa(s, sel).forEach(function (l) {
        if (getComputedStyle(l).display === "none") { return; }
        if (lbls.indexOf(l) < 0) { lbls.push(l); }
      });
    });
    var boxes = lbls.map(function (l) { return boxIn(l, s); });
    for (var i = 0; i < lbls.length; i++) {
      for (var j = i + 1; j < lbls.length; j++) {
        var A = boxes[i], B = boxes[j];
        if (!A || !B || !A.width || !B.width) { continue; }
        if (!overlaps(A, B)) { continue; }
        out.collide.push({ a: label(lbls[i]), b: label(lbls[j]) });
      }
    }

    /* median font size, weighted by how much text sits at each size */
    sizes.sort(function (a, b) { return a[0] - b[0]; });
    var half = chars / 2, run = 0, med = null;
    for (var k = 0; k < sizes.length; k++) {
      run += sizes[k][1];
      if (med === null && run >= half) { med = sizes[k][0]; }
    }
    out.medianPx = med === null ? null : +med.toFixed(1);
    out.chars = chars;

    /* fill of whichever region actually holds the content */
    var body = null;
    for (var ri = 0; ri < CONFIG.contentRegionSels.length && !body; ri++) {
      var cand = qa(s, CONFIG.contentRegionSels[ri]);
      if (cand.length) { body = cand[0]; }
    }
    if (!body) { body = s; }
    var kids = Array.prototype.slice.call(body.children);
    var bext = rootExtent(body);
    var bot = 0;
    kids.forEach(function (k2) {
      var kb = boxIn(k2, body);
      if (kb && kb.bottom > bot) { bot = kb.bottom; }
    });
    out.fillPct = bext.h ? Math.round(100 * bot / bext.h) : null;
    return out;
  }

  /* ------------------------------- the sweep ------------------------------ */
  var KINDS = ["low", "small", "spill", "tap", "svgSmall", "collide"];

  function spec() {
    return {
      minFontPx: CONFIG.minFontPx,
      minControlPx: CONFIG.minControlPx,
      contrast: CONFIG.contrastNormal + ":1 normal, " + CONFIG.contrastLarge +
                ":1 at >=" + CONFIG.largePx + "px or >=" + CONFIG.largeBoldPx +
                "px weight " + CONFIG.boldWeight,
      spillTolPx: CONFIG.spillTolPx,
      projectorMedianAdvisory: "median >=" + CONFIG.projectorMedianPx +
                               "px at " + CONFIG.projectorMedianAtWidth +
                               " wide (reported, never failed on)",
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
      "). A hidden, collapsed or unfocused browser pane lays out at 0x0 and " +
      "EVERY geometry number becomes garbage. Front the tab / widen the pane, " +
      "or lower CONFIG.minViewportWidth if this deck is genuinely narrow, " +
      "then re-run.";
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
      /* classList.toggle's second argument is ES5-era and widely present */
      if (j === i) { x.classList.add(CONFIG.activeClass); }
      else { x.classList.remove(CONFIG.activeClass); }
    });
  }
  function revealFrags(slide) {
    qa(slide, CONFIG.fragSel).forEach(function (f) {
      f.classList.add(CONFIG.fragOnClass);
    });
  }

  function report(rows, slides, from, to) {
    var totals = { low: 0, small: 0, spill: 0, tap: 0, svgSmall: 0, collide: 0 };
    rows.forEach(function (r) {
      KINDS.forEach(function (k) { totals[k] += r[k].length; });
    });
    var failing = rows.filter(function (r) {
      for (var i = 0; i < KINDS.length; i++) {
        if (r[KINDS[i]].length) { return true; }
      }
      return false;
    });
    var n = 0;
    KINDS.forEach(function (k) { n += totals[k]; });

    /* Three structural defects that this probe REPORTED but did not COUNT, so a
       deck whose only fault was one of them printed VERDICT: PASS. Verified: a
       single injected <a href> inside a slide left the verdict at PASS.

       Note what the defect WAS and WAS NOT: the printed numbers were already
       true. querySelectorAll(".slide a[href]").length is a correct count, so a
       reported 0 was genuine evidence -- it just could not make the verdict
       fail. A weak verdict, not wrong data. The fix is to enforce the field, not
       to distrust it.

       Under-fill is deliberately still NOT counted -- openers, summaries and the
       check screen are legitimately sparer, and only a human can say which. */
    var overfill = [];
    rows.forEach(function (r) {
      if (r.fillPct !== null && r.fillPct > CONFIG.fillMax) {
        overfill.push({ slide: r.slide, fillPct: r.fillPct });
      }
    });
    var linksInside = qa(document, CONFIG.slideSel + " a[href]").length;
    var hScroll = document.documentElement.scrollWidth >
                  document.documentElement.clientWidth;
    totals.overfill = overfill.length;
    totals.linkInSlide = linksInside;
    totals.docHScroll = hScroll ? 1 : 0;
    n += overfill.length + linksInside + (hScroll ? 1 : 0);

    var out = {
      page: CONFIG.deckLabel || window.location.href,
      viewport: [window.innerWidth, window.innerHeight],
      slidesChecked: (from + 1) + ".." + to,
      slidesTotal: slides.length,
      totals: totals,
      failures: n,
      medians: rows.map(function (r) { return r.medianPx; }),
      fills: rows.map(function (r) { return r.fillPct; }),
      overfilledSlides: overfill,
      linksInsideSlides: qa(document, CONFIG.slideSel + " a[href]").length,
      docHScroll: document.documentElement.scrollWidth >
                  document.documentElement.clientWidth,
      failingSlides: failing.map(function (r) {
        return { slide: r.slide,
                 low: r.low.slice(0, CONFIG.maxExamples),
                 small: r.small.slice(0, CONFIG.maxExamples),
                 spill: r.spill.slice(0, CONFIG.maxExamples),
                 tap: r.tap.slice(0, CONFIG.maxTapExamples),
                 svgSmall: r.svgSmall.slice(0, CONFIG.maxExamples),
                 collide: r.collide.slice(0, CONFIG.maxExamples) };
      })
    };
    return out;
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
        return verdict({ ABORTED: m, viewport: [window.innerWidth, window.innerHeight] });
      }
      var hi = Math.min(to === undefined ? slides.length : to, slides.length);
      var rows = [];

      function step(i) {
        if (i >= hi) { return Promise.resolve(); }
        activate(slides, i);
        revealFrags(slides[i]);
        fireResize();   /* re-run resize-bound per-slide layout hooks */
        return sleep(settleMs()).then(function () {
          rows.push(auditSlide(slides[i], i + 1));
          return step(i + 1);
        });
      }
      return step(from).then(function () {
        var res = report(rows, slides, from, hi);
        if (global.console) {
          console.log("audit_deck " + res.page + "  viewport " +
                      res.viewport[0] + "x" + res.viewport[1] +
                      "  slides " + res.slidesChecked + "/" + res.slidesTotal);
          console.log(JSON.stringify(res.totals));
        }
        return verdict(res);
      });
    });
  }

  function all() { return slice(0, undefined); }

  var api = { all: all, slice: slice, spec: spec, auditSlide: auditSlide,
              CONFIG: CONFIG, settleMs: settleMs, sleep: sleep,
              guardViewport: guardViewport, pressStart: pressStart,
              activate: activate, revealFrags: revealFrags,
              fireResize: fireResize, label: label, boxIn: boxIn,
              KINDS: KINDS, verdict: verdict };

  global.__audit = global.__audit || {};
  global.__audit.deck = api;
  global.AuditDeck = api;   /* convenience alias for pasting into a console */
})(typeof window !== "undefined" ? window : this);
