/* ==========================================================================
   audit_compose.js — is this screen COMPOSED, or does it just fit?

   WHY IT EXISTS
   audit_deck.js reports a `fill` percentage. That number is computed from the
   bounding box of the slide body's children, so a large empty container
   scores a high fill while the only thing a learner can read sits in its
   top-left corner. A module can pass every existing check — no spill, no
   collision, contrast fine, tap sizes fine, fill 90 % — and still look like a
   web page rather than a designed presentation screen.

   This probe measures MEANINGFUL CONTENT instead.

     MEANINGFUL   headings, body copy, list items, table cells, svg, img,
                  canvas, video, buttons, links, form controls, figcaption —
                  anything a learner reads, looks at or presses.
     NOT          the div, section, panel or card that holds them. A card with
                  a border and a shadow is furniture; the sentence inside it
                  is the content. Furniture inherits its right to the space
                  from what it contains.

   WHAT IT REPORTS, per screen

     ink          the union area of meaningful content, as a % of the stage
     centroid     where the weight of the content actually sits, 0..1 in x
                  and y. 0.5/0.5 is centred.
     deadHalf     a half of the screen (left/right/top/bottom) with under 8 %
                  of the ink in it. This is the corner-cluster detector.
     focal        the largest single meaningful element, as a % of the stage.
                  A teaching visual that is the point of the screen and covers
                  11 % of it is undersized.
     verdict      COMPOSED · REVIEW · WEAK

   WHAT IT IS NOT
   Not a percentage law. A deliberately sparse screen — one statement, one
   question, one activity code — is a strong composition and will score low
   ink on purpose. Declare it and the probe respects it:

       <section class="slide" data-compose="sparse">

   A sparse screen is still checked for the thing that is always wrong:
   content pushed into a corner. Sparse means FEW elements, deliberately
   placed. It never means "a small cluster top-left".

   Choosing a named composition counts as declaring intent. `opener`,
   `activity`, `checkbody`, `stage`, `sum` and `two-col` on the slide body are
   deliberate choices from a vocabulary, so the ink floor is not applied to
   them. `data-compose="sparse"` is the escape hatch for a default-flow screen
   that is thin on purpose. Everything else is measured.

   HOW TO RUN
     serve over http, then in the page:
       await AuditCompose.run()        every screen
       AuditCompose.one()              the screen you are looking at

   Requires the deck's own Next button (#btnNext) and start button, same as
   audit_drive.js. ES5-safe: no arrow functions, no optional chaining.
   ========================================================================== */
var AuditCompose = (function (w, d) {
  "use strict";

  var CONFIG = {
    slideSel: ".slide",
    activeClass: "active",
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",
    nextBtnSel: "#btnNext, [data-audit-next], .deck-next",
    settleMs: 420,

    /* an element is MEANINGFUL if it matches this and has painted content */
    inkSel: "h1,h2,h3,h4,h5,h6,p,li,td,th,figcaption,blockquote,code,pre," +
            "svg,img,canvas,video,button,a[href],input,select,textarea,label," +
            "[data-ink]",
    /* ...unless it is chrome, or the author excluded it */
    skipSel: "#chrome,#overview,#cue,#progress,#blockTag,#landing," +
             ".slide-kind,.credit,[data-ink='no'],[aria-hidden='true']",

    minPaintedPx: 6,        /* below this in either axis it is a hairline */
    deadHalfShare: 0.08,    /* under this share of ink, a half is dead */
    inkFloor: 0.14,         /* under this, a non-sparse screen is thin */
    focalFloor: 0.22,       /* a screen whose point is one visual wants this */
    centroidDrift: 0.20     /* how far off centre the weight may sit */
  };

  function each(a, f) { Array.prototype.forEach.call(a, f); }
  function round(n) { return Math.round(n * 1000) / 1000; }

  function visible(el) {
    var s = w.getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") { return false; }
    if (parseFloat(s.opacity) < 0.06) { return false; }
    return true;
  }

  /* Does this element carry ink of its OWN, rather than only through
     descendants? A <p> wrapping a <svg> is not itself ink. */
  function ownsInk(el) {
    var tag = el.tagName.toLowerCase();
    if (tag === "svg" || tag === "img" || tag === "canvas" || tag === "video") { return true; }
    if (el.hasAttribute && el.hasAttribute("data-ink")) { return el.getAttribute("data-ink") !== "no"; }
    /* a text-bearing element: does it have a non-empty direct text node? */
    var n = el.childNodes, i;
    for (i = 0; i < n.length; i++) {
      if (n[i].nodeType === 3 && n[i].nodeValue && n[i].nodeValue.trim().length) { return true; }
    }
    return false;
  }

  function inkRects(slide) {
    var out = [];
    each(slide.querySelectorAll(CONFIG.inkSel), function (el) {
      if (el.closest && el.closest(CONFIG.skipSel)) { return; }
      if (!visible(el)) { return; }
      if (!ownsInk(el)) { return; }
      var r = el.getBoundingClientRect();
      if (r.width < CONFIG.minPaintedPx || r.height < CONFIG.minPaintedPx) { return; }
      out.push({ el: el, x: r.left, y: r.top, w: r.width, h: r.height,
                 tag: el.tagName.toLowerCase(), cls: (el.className && el.className.baseVal !== undefined
                        ? el.className.baseVal : el.className) || "" });
    });
    return out;
  }

  /* Union area by scan-grid. Exact polygon union is overkill here; a 64 x 40
     cell grid over the stage resolves to ~20 x 20 px, well under anything that
     matters, and it cannot double-count overlapping rects the way a naive sum
     of areas does. */
  function measure(slide) {
    var sr = slide.getBoundingClientRect();
    var COLS = 64, ROWS = 40;
    var cw = sr.width / COLS, ch = sr.height / ROWS;
    var grid = [], i;
    for (i = 0; i < COLS * ROWS; i++) { grid.push(0); }

    var rects = inkRects(slide);
    var biggest = null;
    each(rects, function (r) {
      var a = r.w * r.h;
      if (!biggest || a > biggest.w * biggest.h) { biggest = r; }
      var c0 = Math.max(0, Math.floor((r.x - sr.left) / cw));
      var c1 = Math.min(COLS - 1, Math.floor((r.x + r.w - sr.left) / cw));
      var r0 = Math.max(0, Math.floor((r.y - sr.top) / ch));
      var r1 = Math.min(ROWS - 1, Math.floor((r.y + r.h - sr.top) / ch));
      var cc, rr;
      for (rr = r0; rr <= r1; rr++) {
        for (cc = c0; cc <= c1; cc++) { grid[rr * COLS + cc] = 1; }
      }
    });

    var lit = 0, sx = 0, sy = 0;
    var left = 0, right = 0, top = 0, bottom = 0;
    var rr2, cc2;
    for (rr2 = 0; rr2 < ROWS; rr2++) {
      for (cc2 = 0; cc2 < COLS; cc2++) {
        if (!grid[rr2 * COLS + cc2]) { continue; }
        lit++;
        sx += (cc2 + 0.5) / COLS;
        sy += (rr2 + 0.5) / ROWS;
        if (cc2 < COLS / 2) { left++; } else { right++; }
        if (rr2 < ROWS / 2) { top++; } else { bottom++; }
      }
    }

    return {
      rects: rects.length,
      ink: lit / (COLS * ROWS),
      cx: lit ? sx / lit : 0.5,
      cy: lit ? sy / lit : 0.5,
      halves: { left: lit ? left / lit : 0, right: lit ? right / lit : 0,
                top: lit ? top / lit : 0, bottom: lit ? bottom / lit : 0 },
      focal: biggest ? (biggest.w * biggest.h) / (sr.width * sr.height) : 0,
      focalW: biggest ? biggest.w / sr.width : 0,
      focalOf: biggest ? (biggest.tag + (biggest.cls ? "." + String(biggest.cls).split(" ")[0] : "")) : null,
      stage: [Math.round(sr.width), Math.round(sr.height)]
    };
  }

  /* A screen that uses a NAMED composition from the vocabulary has already
     declared its intent - the author chose `opener` or `activity` from a list,
     which is a decision, not an accident. Those compositions are centred by
     construction and are meant to be spare: an activity announcement that
     tiled the screen with text would be the defect.

     The ink floor therefore applies to DEFAULT-FLOW screens, where nothing was
     chosen and content simply landed where it fell. Those are the ones that
     produce a cluster in a corner of a large empty box.

     Corner-cluster and centroid checks apply to every screen regardless. A
     declared composition still has to be composed. */
  var DECLARED = ["opener", "activity", "checkbody", "stage", "sum", "two-col"];

  function judge(slide, m) {
    var body = slide.querySelector(".slide-body");
    var bodyCls = body ? " " + ((body.className && body.className.baseVal !== undefined
                    ? body.className.baseVal : body.className) || "") + " " : " ";
    var declared = null, di;
    for (di = 0; di < DECLARED.length; di++) {
      if (bodyCls.indexOf(" " + DECLARED[di] + " ") >= 0) { declared = DECLARED[di]; break; }
    }
    var sparse = declared !== null ||
                 (slide.getAttribute("data-compose") || "").indexOf("sparse") >= 0;
    var kind = slide.getAttribute("data-kind") || "";
    var findings = [];

    /* the corner cluster. Checked on EVERY screen, sparse included: a
       deliberately sparse screen is still centred or deliberately offset, it
       is never a huddle in one corner. */
    var dead = [];
    ["left", "right", "top", "bottom"].forEach(function (k) {
      if (m.rects > 0 && m.halves[k] < CONFIG.deadHalfShare) { dead.push(k); }
    });
    if (dead.length) {
      findings.push("the " + dead.join(" and ") + " half of this screen holds under " +
        Math.round(CONFIG.deadHalfShare * 100) + "% of the content - it is a cluster, not a composition");
    }

    if (Math.abs(m.cx - 0.5) > CONFIG.centroidDrift && dead.length === 0) {
      findings.push("content weight sits at x=" + round(m.cx) +
        " - noticeably off centre without a composition that asks for it");
    }
    /* Vertical drift was missing from the first version of this probe, and it
       is the one the eye notices first: a screen whose content stops at 60%
       has an empty band along the bottom, which reads as unfinished even when
       every element is correct. Checked on declared compositions too - an
       `opener` is centred by construction, so if its weight has drifted the
       composition is not doing what it claims. */
    if (Math.abs(m.cy - 0.5) > CONFIG.centroidDrift && dead.length === 0) {
      findings.push("content weight sits at y=" + round(m.cy) +
        (m.cy < 0.5 ? " - the lower part of the screen is empty"
                    : " - the upper part of the screen is empty"));
    }

    if (!sparse) {
      if (m.ink < CONFIG.inkFloor) {
        findings.push("only " + Math.round(m.ink * 100) +
          "% of the screen carries content. Either compose it to use the screen, " +
          "or declare it: data-compose=\"sparse\"");
      }
      /* A screen whose point IS a visual: the visual has to be big.
         AREA alone is a landscape assumption. A 780 x 340 drawing at the full
         width of an 800 x 1280 portrait screen covers 20 % of its area and is
         using the screen exactly as well as it can - flagging it taught the
         author to do nothing useful. A figure is undersized only when it is
         small in its OWN dominant axis as well: under 60 % of the stage width
         and under the area floor. */
      if (m.focalOf && /^(svg|img|canvas)/.test(m.focalOf) &&
          m.focal < CONFIG.focalFloor && m.focalW < CONFIG.focalWidthFloor) {
        findings.push("the teaching visual covers " + Math.round(m.focal * 100) +
          "% of the screen and " + Math.round(m.focalW * 100) + "% of its width" +
          " - too small to read from the back of a room. " +
          "Use .slide-body.stage or a .two-col with .fill");
      }
    }

    var verdict = findings.length === 0 ? "COMPOSED" : (dead.length ? "WEAK" : "REVIEW");
    return { verdict: verdict, findings: findings, sparse: sparse,
             composition: declared || "flow", kind: kind };
  }

  function one(slide) {
    slide = slide || d.querySelector("." + CONFIG.activeClass + CONFIG.slideSel) ||
            d.querySelector(CONFIG.slideSel + "." + CONFIG.activeClass);
    if (!slide) { return { error: "no active slide" }; }
    var m = measure(slide);
    var j = judge(slide, m);
    return {
      title: slide.getAttribute("data-title") || "",
      kind: j.kind, composition: j.composition, sparse: j.sparse, verdict: j.verdict,
      ink: round(m.ink), focal: round(m.focal), focalW: round(m.focalW),
      focalOf: m.focalOf,
      centroid: [round(m.cx), round(m.cy)],
      halves: { l: round(m.halves.left), r: round(m.halves.right),
                t: round(m.halves.top), b: round(m.halves.bottom) },
      elements: m.rects, findings: j.findings
    };
  }

  function wait(ms) { return new Promise(function (r) { w.setTimeout(r, ms); }); }

  function run() {
    var slides = d.querySelectorAll(CONFIG.slideSel);
    var start = d.querySelector(CONFIG.startBtnSel);
    var next = d.querySelector(CONFIG.nextBtnSel);
    if (!next) { return Promise.resolve({ ABORTED: "no next button (" + CONFIG.nextBtnSel + ")" }); }

    var results = [];
    var chain = Promise.resolve();
    if (start && !d.querySelector("." + CONFIG.activeClass)) {
      chain = chain.then(function () { start.click(); return wait(CONFIG.settleMs); });
    }
    /* walk from wherever we are back to the first screen, then forward */
    chain = chain.then(function () {
      var prev = d.querySelector("#btnPrev");
      var back = Promise.resolve(), i;
      for (i = 0; i < slides.length; i++) {
        back = back.then(function () { if (prev) { prev.click(); } return wait(40); });
      }
      return back;
    }).then(function () { return wait(CONFIG.settleMs); });

    for (var i = 0; i < slides.length; i++) {
      /* jshint loopfunc:true */
      chain = chain.then(function () {
        results.push(one());
        next.click();
        return wait(CONFIG.settleMs);
      });
    }

    return chain.then(function () {
      var weak = results.filter(function (r) { return r.verdict === "WEAK"; });
      var review = results.filter(function (r) { return r.verdict === "REVIEW"; });
      return {
        viewport: [w.innerWidth, w.innerHeight],
        screens: results.length,
        composed: results.length - weak.length - review.length,
        review: review.length,
        weak: weak.length,
        verdict: weak.length ? "WEAK n=" + weak.length
               : (review.length ? "REVIEW n=" + review.length : "COMPOSED"),
        problems: weak.concat(review).map(function (r, i) {
          return { n: results.indexOf(r) + 1, title: r.title, verdict: r.verdict,
                   ink: r.ink, focal: r.focal, centroid: r.centroid, findings: r.findings };
        }),
        all: results
      };
    });
  }

  return { run: run, one: one, measure: measure, CONFIG: CONFIG };
})(window, document);
