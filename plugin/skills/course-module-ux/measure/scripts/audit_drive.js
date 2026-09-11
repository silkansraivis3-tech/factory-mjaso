/* ==========================================================================
   audit_drive.js — course-agnostic DRIVEN sweep.
   Requires audit_deck.js and audit_collide.js to be loaded FIRST.

   WHAT IT DOES
     audit_deck.js and audit_collide.js walk the deck by toggling the active
     class themselves. Any deck with a per-slide layout hook — pin placement,
     label nudging, a canvas resize, a chart relayout — called from the
     engine's own show() then never runs that hook, so positioned elements sit
     at their raw CSS defaults and the probes report spills and collisions
     that do not exist on screen (and would hide any that do).

     This one walks the deck the way an instructor does: press the deck's own
     Next button, through every fragment, to the end. At each slide, with all
     fragments revealed, it runs BOTH the audit_deck.js per-slide checks and
     the audit_collide.js full pairwise collision checks, and reports them
     together.

     Use this as the authoritative sweep. Use the other two when you want to
     re-measure a single slide fast, or when a deck has no Next button.

   HOW TO RUN
     Only DEFINES the probe. Async — MUST be awaited:

         await AuditDrive.run()          every slide
         await AuditDrive.run(0, 12)     slides 1-12
         AuditDrive.goto(7)              jump to slide 7 (1-based), frags shown

     (also registered as window.__audit.drive)

     run() prints a single-line verdict and sets window.__auditExit to 0 or 1.
     goto() is a hand tool and sets no verdict.

   TO PORT TO ANOTHER DECK
     Edit the CONFIG block, and the CONFIG blocks of the two probes it calls.
     Nothing here names a course, a path or a port.
     window.__auditDriveConfig = {...} set BEFORE load overrides it.

   ES5-safe syntax (no arrow functions, no optional chaining, no ??).
   ========================================================================== */
(function (global) {
  "use strict";

  /* ======================= CONFIG — EDIT THIS BLOCK ======================= */
  var CONFIG = {
    deckLabel: "",                 /* blank -> window.location.href */

    /* --- structural selectors --- */
    slideSel: ".slide",            /* CHANGE: one deck page */
    fragSel: ".frag",              /* CHANGE: progressive-reveal element */
    activeClass: "active",         /* CHANGE */
    fragOnClass: "on",             /* CHANGE */
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",  /* CHANGE */
    nextBtnSel: "#btnNext, [data-audit-next], .deck-next",      /* CHANGE:
                                      the deck's own forward control. This
                                      probe is worthless without it. */
    slideTitleAttr: "data-title",  /* CHANGE: attribute goto() reports back */

    /* --- timing --- */
    settleMs: 620,                 /* > your slide transition duration */
    minSettleMs: 520,              /* hard floor; do not lower */
    startSettleMs: 500,
    dispatchResize: true,          /* re-run resize-bound per-slide layout */

    /* --- refuse-to-run guards --- */
    /* A DEGENERACY guard, not a size preference. A hidden or collapsed pane lays out
       at 0x0 and every geometry number below becomes garbage - that is what this
       catches. It is deliberately NOT set to a landscape minimum: 900 wide rejected
       800x1280, a NOVIKONTAS tablet in portrait, which is a viewport the retrofit
       guide tells the operator to measure at. */
    minViewportWidth: 320,
    minViewportHeight: 320,

    /* --- click guards: a deck that will not advance must not spin for ever --- */
    maxSeekClicks: 400,            /* clicks allowed to reach a target slide */
    maxFragClicks: 200,            /* clicks allowed to reveal one slide's frags */
    maxGotoClicks: 600,            /* clicks allowed by goto() */

    /* --- reporting --- */
    maxExamples: 5,
    maxTapExamples: 3,
    maxCollisionExamples: 6
  };
  /* ===================== END CONFIG — EDIT THIS BLOCK ===================== */

  if (global.__auditDriveConfig) {
    for (var ck in global.__auditDriveConfig) {
      if (Object.prototype.hasOwnProperty.call(global.__auditDriveConfig, ck)) {
        CONFIG[ck] = global.__auditDriveConfig[ck];
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

  function deps() {
    var a = global.__audit || {};
    var deck = a.deck || global.AuditDeck;
    var coll = a.collide || global.AuditCollide;
    var missing = [];
    if (!deck || typeof deck.auditSlide !== "function") { missing.push("audit_deck.js"); }
    if (!coll || typeof coll.collideSlide !== "function") { missing.push("audit_collide.js"); }
    return { deck: deck, coll: coll, missing: missing };
  }

  function guardViewport() {
    var w = window.innerWidth || 0, h = window.innerHeight || 0;
    if (w >= CONFIG.minViewportWidth && h >= CONFIG.minViewportHeight) {
      return null;
    }
    var msg = "!!! AUDIT ABORTED — VIEWPORT TOO SMALL: " + w + "x" + h +
      " (minimum " + CONFIG.minViewportWidth + "x" + CONFIG.minViewportHeight +
      "). A hidden or collapsed browser pane lays out at 0x0 and EVERY " +
      "geometry number becomes garbage. This is a degeneracy guard, not a " +
      "size preference - a real portrait tablet passes it. Front the tab, " +
      "then re-run.";
    if (global.console) { console.error(msg); }
    return { ABORTED: msg, viewport: [w, h] };
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

  function abortWith(msg) {
    if (global.console) { console.error(msg); }
    return verdict({ ABORTED: msg,
                     viewport: [window.innerWidth || 0, window.innerHeight || 0] });
  }

  var KINDS = ["low", "small", "spill", "tap", "svgSmall", "collide", "scroll"];

  function run(from, to) {
    from = from || 0;

    var abort = guardViewport();
    if (abort) { return Promise.resolve(verdict(abort)); }

    var D = deps();
    if (D.missing.length) {
      return Promise.resolve(abortWith(
        "!!! AUDIT ABORTED — audit_drive.js needs " + D.missing.join(" and ") +
        " loaded first. It reuses their per-slide checks rather than " +
        "duplicating them. Load them, then re-run."));
    }

    var nextBtn = q(CONFIG.nextBtnSel);
    if (!nextBtn) {
      return Promise.resolve(abortWith(
        "!!! AUDIT ABORTED — no forward control matches CONFIG.nextBtnSel (" +
        CONFIG.nextBtnSel + "). This probe exists to drive the deck through " +
        "its OWN engine; without that button use AuditDeck.all() and " +
        "AuditCollide.all() instead, and accept that any per-slide layout " +
        "hook will not have run."));
    }

    var sb = q(CONFIG.startBtnSel);
    var started = (sb && getComputedStyle(sb).display !== "none")
      ? (sb.click(), sleep(CONFIG.startSettleMs))
      : Promise.resolve();

    return started.then(function () {
      var slides = qa(document, CONFIG.slideSel);
      if (!slides.length) {
        return abortWith("!!! AUDIT ABORTED — no elements match " +
          "CONFIG.slideSel (" + CONFIG.slideSel + ").");
      }
      var hi = Math.min(to === undefined ? slides.length : to, slides.length);
      var rows = [], coll = [], stalled = [];
      var totals = { low: 0, small: 0, spill: 0, tap: 0,
                     svgSmall: 0, collide: 0, xcollide: 0, scroll: 0 };

      function activeIdx() {
        for (var i = 0; i < slides.length; i++) {
          if (slides[i].classList.contains(CONFIG.activeClass)) { return i; }
        }
        return -1;
      }
      function seekTo(target) {
        var guard = 0;
        while (activeIdx() < target && guard++ < CONFIG.maxSeekClicks) {
          nextBtn.click();
        }
        if (activeIdx() !== target) {
          stalled.push({ wanted: target + 1, reached: activeIdx() + 1,
                         clicks: guard });
          return false;
        }
        return true;
      }
      function revealFrags(slide) {
        var guard = 0;
        while (slide.querySelector(CONFIG.fragSel + ":not(." + CONFIG.fragOnClass + ")") &&
               guard++ < CONFIG.maxFragClicks) {
          nextBtn.click();
        }
        return guard < CONFIG.maxFragClicks;
      }

      seekTo(from);

      function step(i) {
        if (i >= hi) { return Promise.resolve(); }
        if (activeIdx() !== i) { seekTo(i); }
        revealFrags(slides[i]);
        fireResize();
        return sleep(settleMs()).then(function () {
          var r = D.deck.auditSlide(slides[i], i + 1);
          KINDS.forEach(function (k) { totals[k] += r[k].length; });
          rows.push(r);

          var x = D.coll.collideSlide(slides[i], i + 1);
          totals.xcollide += x.n;
          if (x.n) {
            coll.push({ slide: i + 1, n: x.n,
                        text: x.text.slice(0, CONFIG.maxCollisionExamples),
                        box: x.box.slice(0, CONFIG.maxCollisionExamples),
                        chrome: x.chrome.slice(0, CONFIG.maxCollisionExamples) });
          }
          if (i < hi - 1) { nextBtn.click(); }   /* on to the next slide */
          return step(i + 1);
        });
      }

      return step(from).then(function () {
        var failing = rows.filter(function (r) {
          for (var i = 0; i < KINDS.length; i++) {
            if (r[KINDS[i]].length) { return true; }
          }
          return false;
        });
        var n = totals.xcollide;
        KINDS.forEach(function (k) { n += totals[k]; });
        var res = {
          page: CONFIG.deckLabel || window.location.href,
          viewport: [window.innerWidth, window.innerHeight],
          range: (from + 1) + ".." + hi,
          slidesTotal: slides.length,
          totals: totals,
          failures: n,
          /* a stalled seek means the numbers below are for the WRONG slides —
             read this before reading anything else */
          stalledNavigation: stalled,
          medians: rows.map(function (r) { return r.medianPx; }),
          fills: rows.map(function (r) { return r.fillPct; }),
          linksInsideSlides: qa(document, CONFIG.slideSel + " a[href]").length,
          docHScroll: document.documentElement.scrollWidth >
                      document.documentElement.clientWidth,
          failingSlides: failing.map(function (r) {
            return { slide: r.slide,
                     low: r.low.slice(0, CONFIG.maxExamples),
                     small: r.small.slice(0, CONFIG.maxExamples - 1),
                     spill: r.spill.slice(0, CONFIG.maxExamples - 1),
                     tap: r.tap.slice(0, CONFIG.maxTapExamples),
                     svgSmall: r.svgSmall.slice(0, CONFIG.maxExamples - 1),
                     scroll: (r.scroll || []).slice(0, CONFIG.maxExamples - 1),
                     collide: r.collide.slice(0, CONFIG.maxExamples - 1) };
          }),
          collisions: coll
        };
        if (global.console) {
          console.log("audit_drive " + res.page + "  viewport " +
                      res.viewport[0] + "x" + res.viewport[1] +
                      "  slides " + res.range + "/" + res.slidesTotal);
          console.log(JSON.stringify(res.totals));
          if (stalled.length) {
            console.error("!!! NAVIGATION STALLED on " + stalled.length +
              " slide(s) — the deck would not advance, so some rows below " +
              "measure the wrong slide: " + JSON.stringify(stalled));
          }
        }
        return verdict(res);
      });
    });
  }

  /* jump to slide n (1-based) through the deck's own Next, all frags revealed */
  function goto(n) {
    var slides = qa(document, CONFIG.slideSel);
    if (!slides.length || !slides[n - 1]) { return null; }
    var sb = q(CONFIG.startBtnSel);
    if (sb && getComputedStyle(sb).display !== "none") { sb.click(); }
    var b = q(CONFIG.nextBtnSel);
    if (!b) { return null; }
    var g = 0, h = 0;
    while (!slides[n - 1].classList.contains(CONFIG.activeClass) &&
           g++ < CONFIG.maxGotoClicks) { b.click(); }
    while (slides[n - 1].querySelector(
             CONFIG.fragSel + ":not(." + CONFIG.fragOnClass + ")") &&
           h++ < CONFIG.maxFragClicks) { b.click(); }
    fireResize();
    return slides[n - 1].getAttribute(CONFIG.slideTitleAttr) ||
           slides[n - 1].className;
  }

  function spec() {
    return { settleMs: settleMs(),
             minViewport: [CONFIG.minViewportWidth, CONFIG.minViewportHeight],
             clickGuards: [CONFIG.maxSeekClicks, CONFIG.maxFragClicks,
                           CONFIG.maxGotoClicks],
             inherits: "thresholds come from audit_deck.js and " +
                       "audit_collide.js CONFIG" };
  }

  var api = { run: run, goto: goto, spec: spec, CONFIG: CONFIG,
              guardViewport: guardViewport, verdict: verdict };

  global.__audit = global.__audit || {};
  global.__audit.drive = api;
  global.AuditDrive = api;
})(typeof window !== "undefined" ? window : this);
