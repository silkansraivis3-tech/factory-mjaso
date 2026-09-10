/* ==========================================================================
   audit_collide.js — course-agnostic FULL collision probe.
   Companion to audit_deck.js, which only compares absolutely-positioned
   labels against each other and therefore cannot see label-over-side-text,
   card-text-over-band, or anything sitting under the deck's own chrome.

   WHAT IT DOES — three checks:

     1  TEXT OVER TEXT, measured on the PAINTED INK, not the element box.
        A centred heading in a full-width block shares its box with whatever
        sits to its left while its glyphs are nowhere near it; comparing boxes
        calls that a collision and it is not one. So every element's OWN text
        nodes are measured with Range.getClientRects(), which returns one rect
        per rendered LINE, and every line of A is tested against every line of
        B. That is literally "text printing over other text".

     2  BOXES COLLIDING — element border-boxes, but only for elements that
        actually PAINT a box (a background or a border). Two invisible
        wrappers sharing space is normal layout; two cards or two bands
        sharing space is the defect.

     3  TEXT UNDER THE DECK CHROME — the persistent nav/footer furniture that
        lives OUTSIDE the slide. It is typically never removed and never given
        pointer-events:none (it only fades when idle), so slide content behind
        it is genuinely overlapped, and its buttons carry no text of their own
        for check 1 to catch. Every slide text line is therefore tested
        against the chrome's own BOX.

     Checks 1 and 2 ignore true nesting — a DOM ancestor/descendant pair, or
     one box fully inside another.

   HOW TO RUN
     Only DEFINES the probe. Async — MUST be awaited:

         await AuditCollide.all()          every slide
         await AuditCollide.slice(0, 9)    slides 1-9

     (also registered as window.__audit.collide)

     Prints a single-line verdict and sets window.__auditExit to 0 or 1.

   TO PORT TO ANOTHER DECK
     Edit the CONFIG block. Nothing else names a course, a path or a port.
     window.__auditCollideConfig = {...} set BEFORE load overrides it.

   WHY THIS ONE USES getBoundingClientRect AND NOT offset*
     Deliberate, and the opposite of audit_deck.js. "Printing over" is a
     RENDERED phenomenon, and Range.getClientRects() only ever speaks in
     rendered viewport coordinates. Mixing a layout-space box with an
     ink-space rect would produce nonsense, so every rect in this file is
     rendered-space and they are all mutually comparable. Any deck transform
     applies to both sides equally and the overlap verdict is unchanged.

   TRAPS HONOURED: settle past the slide transition (floored at 520 ms),
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
    slideSel: ".slide",            /* CHANGE: one deck page */
    fragSel: ".frag",              /* CHANGE: progressive-reveal element */
    activeClass: "active",         /* CHANGE */
    fragOnClass: "on",             /* CHANGE */
    transientClasses: ["leaving", "leaving-back", "prev", "next"],  /* CHANGE */
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",      /* CHANGE */

    /* CHANGE: persistent furniture that lives OUTSIDE a slide. Its subtree is
       pulled into the text pool so slide text running past the slide floor is
       caught colliding with it. These ids belong to a DECK TEMPLATE, not to
       any one course — replace them with your own, or mark your chrome with
       data-audit-chrome and delete the ids. Verified per deck: several of
       these are absent from some decks, which is harmless (no match is fine)
       but means a missing check, not a pass. */
    chromeSels: ["#chrome", "#brandFooter", "#footerCourse", "#blockTag",
                 "#counter", "[data-audit-chrome]"],

    /* CHANGE: the subset of the above that OVERLAYS the slide — never
       removed, never pointer-events:none, only faded. Their whole BOX is
       tested against every slide text line. */
    chromeBoxSels: ["#chrome", "#brandFooter", "[data-audit-chrome-box]"],

    /* --- timing --- */
    settleMs: 600,                 /* > your slide transition duration */
    minSettleMs: 520,              /* hard floor; do not lower */
    startSettleMs: 400,

    /* --- refuse-to-run guards --- */
    minViewportWidth: 900,         /* CHANGE for a tablet/phone deck */
    minViewportHeight: 400,

    /* --- measurement thresholds --- */
    tolPx: 2,                      /* overlap needed in BOTH axes to count */
    minInkPx: 1,                   /* ignore ink rects thinner than this */
    minBoxPx: 2,                   /* ignore painted boxes smaller than this */
    minChromeBoxPx: 2,
    bgAlphaMin: 0.05,              /* background alpha that counts as painted */
    borderMinPx: 0.5,              /* border width that counts as painted */
    insideTolPx: 1,                /* slack when deciding "fully inside" */
    skipOpacityZero: true,         /* opacity:0 paints nothing */

    /* --- reporting --- */
    maxExamples: 6,
    txtSample: 28
  };
  /* ===================== END CONFIG — EDIT THIS BLOCK ===================== */

  if (global.__auditCollideConfig) {
    for (var ck in global.__auditCollideConfig) {
      if (Object.prototype.hasOwnProperty.call(global.__auditCollideConfig, ck)) {
        CONFIG[ck] = global.__auditCollideConfig[ck];
      }
    }
  }

  function simpleClass(sel) {
    return /^\.[A-Za-z0-9_-]+$/.test(sel) ? sel.slice(1) : "";
  }
  var NOISE = [CONFIG.activeClass, CONFIG.fragOnClass, simpleClass(CONFIG.fragSel)]
    .concat(CONFIG.transientClasses);

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
  function ownTextNodes(el) {
    return Array.prototype.filter.call(el.childNodes, function (n) {
      return n.nodeType === 3 && n.textContent.trim();
    });
  }
  /* one rect per rendered LINE of this element's OWN text */
  function inkRects(el) {
    var out = [];
    ownTextNodes(el).forEach(function (n) {
      var r = document.createRange();
      r.selectNodeContents(n);
      Array.prototype.forEach.call(r.getClientRects(), function (b) {
        if (b.width > CONFIG.minInkPx && b.height > CONFIG.minInkPx) {
          out.push(b);
        }
      });
      if (r.detach) { r.detach(); }
    });
    return out;
  }
  function paintsBox(st) {
    var bg = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/
      .exec(st.backgroundColor);
    var hasBg = !!(bg && (bg[4] === undefined || +bg[4] > CONFIG.bgAlphaMin));
    var bw = ["borderTopWidth", "borderRightWidth",
              "borderBottomWidth", "borderLeftWidth"]
      .some(function (k) { return parseFloat(st[k]) > CONFIG.borderMinPx; });
    return hasBg || bw;
  }
  function ov(A, B) {
    return {
      x: Math.min(A.right, B.right) - Math.max(A.left, B.left),
      y: Math.min(A.bottom, B.bottom) - Math.max(A.top, B.top)
    };
  }
  function inside(A, B) {
    var t = CONFIG.insideTolPx;
    return A.left >= B.left - t && A.right <= B.right + t &&
           A.top >= B.top - t && A.bottom <= B.bottom + t;
  }

  /* ------------------------------ one slide ------------------------------ */
  function collideSlide(s, n) {
    var texts = [], boxes = [];

    var chrome = [];
    CONFIG.chromeSels.forEach(function (sel) {
      qa(document, sel).forEach(function (e) {
        if (getComputedStyle(e).display === "none") { return; }
        if (chrome.indexOf(e) < 0) { chrome.push(e); }
        qa(e, "*").forEach(function (c) {
          if (chrome.indexOf(c) < 0) { chrome.push(c); }
        });
      });
    });

    var all = qa(s, "*").concat(chrome);
    all.forEach(function (el) {
      if (el.namespaceURI && el.namespaceURI.indexOf("svg") >= 0) { return; }
      var st = getComputedStyle(el);
      if (st.display === "none") { return; }   /* NOT visibility — see header */
      if (CONFIG.skipOpacityZero && parseFloat(st.opacity) === 0) { return; }
      var ink = inkRects(el);
      if (ink.length) {
        texts.push({ el: el, ink: ink, sel: label(el),
                     txt: (el.textContent || "").trim().slice(0, CONFIG.txtSample) });
      }
      if (paintsBox(st) && s.contains(el)) {
        var b = el.getBoundingClientRect();
        if (b.width > CONFIG.minBoxPx && b.height > CONFIG.minBoxPx) {
          boxes.push({ el: el, r: b, sel: label(el) });
        }
      }
    });

    /* check 3 — slide text under the overlaying chrome's own box */
    var chromeBox = [];
    CONFIG.chromeBoxSels.forEach(function (sel) {
      qa(document, sel).forEach(function (e) {
        var st = getComputedStyle(e);
        if (st.display === "none" || st.visibility === "hidden") { return; }
        var r = e.getBoundingClientRect();
        if (r.width > CONFIG.minChromeBoxPx && r.height > CONFIG.minChromeBoxPx) {
          chromeBox.push({ q: sel, r: r });
        }
      });
    });
    var underChrome = [];
    texts.forEach(function (T) {
      if (!s.contains(T.el)) { return; }
      chromeBox.forEach(function (C) {
        var worst = null;
        T.ink.forEach(function (rr) {
          var o = ov(rr, C.r);
          if (o.x <= CONFIG.tolPx || o.y <= CONFIG.tolPx) { return; }
          if (!worst || o.x * o.y > worst.x * worst.y) { worst = o; }
        });
        if (worst) {
          underChrome.push({ sel: T.sel, txt: T.txt, under: C.q,
                             ox: Math.round(worst.x), oy: Math.round(worst.y) });
        }
      });
    });

    /* check 1 — ink line against ink line */
    var text = [], box = [];
    for (var i = 0; i < texts.length; i++) {
      for (var j = i + 1; j < texts.length; j++) {
        var A = texts[i], B = texts[j];
        if (A.el.contains(B.el) || B.el.contains(A.el)) { continue; }
        var worst = null;
        for (var a = 0; a < A.ink.length; a++) {
          for (var b2 = 0; b2 < B.ink.length; b2++) {
            var o = ov(A.ink[a], B.ink[b2]);
            if (o.x <= CONFIG.tolPx || o.y <= CONFIG.tolPx) { continue; }
            if (!worst || o.x * o.y > worst.x * worst.y) { worst = o; }
          }
        }
        if (worst) {
          text.push({ a: A.sel, aTxt: A.txt, b: B.sel, bTxt: B.txt,
                      ox: Math.round(worst.x), oy: Math.round(worst.y) });
        }
      }
    }
    /* check 2 — painted box against painted box */
    for (var k = 0; k < boxes.length; k++) {
      for (var m = k + 1; m < boxes.length; m++) {
        var C2 = boxes[k], D = boxes[m];
        if (C2.el.contains(D.el) || D.el.contains(C2.el)) { continue; }
        var o2 = ov(C2.r, D.r);
        if (o2.x <= CONFIG.tolPx || o2.y <= CONFIG.tolPx) { continue; }
        if (inside(C2.r, D.r) || inside(D.r, C2.r)) { continue; }
        box.push({ a: C2.sel, b: D.sel,
                   ox: Math.round(o2.x), oy: Math.round(o2.y) });
      }
    }
    return { slide: n, n: text.length + box.length + underChrome.length,
             text: text, box: box, chrome: underChrome };
  }

  /* ------------------------------- the sweep ------------------------------ */
  function spec() {
    return {
      tolPx: CONFIG.tolPx,
      paintedBox: "background alpha > " + CONFIG.bgAlphaMin + " or border > " +
                  CONFIG.borderMinPx + "px",
      minBoxPx: CONFIG.minBoxPx,
      minInkPx: CONFIG.minInkPx,
      insideTolPx: CONFIG.insideTolPx,
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
      "). A hidden or collapsed browser pane lays out at 0x0 and EVERY " +
      "geometry number becomes garbage — a collision probe would report a " +
      "clean deck or an entirely invented one. Front the tab, then re-run.";
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
    else { n = res.totalCollisions; fail = n > 0; }
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
      var rows = [], total = 0;

      function step(i) {
        if (i >= hi) { return Promise.resolve(); }
        activate(slides, i);
        revealFrags(slides[i]);
        return sleep(settleMs()).then(function () {
          var r = collideSlide(slides[i], i + 1);
          total += r.n;
          if (r.n) { rows.push(r); }
          return step(i + 1);
        });
      }
      return step(from).then(function () {
        var res = {
          page: CONFIG.deckLabel || window.location.href,
          viewport: [window.innerWidth, window.innerHeight],
          range: (from + 1) + ".." + hi,
          slidesTotal: slides.length,
          totalCollisions: total,
          slides: rows.map(function (r) {
            return { slide: r.slide, n: r.n,
                     text: r.text.slice(0, CONFIG.maxExamples),
                     box: r.box.slice(0, CONFIG.maxExamples),
                     chrome: r.chrome.slice(0, CONFIG.maxExamples) };
          })
        };
        if (global.console) {
          console.log("audit_collide " + res.page + "  viewport " +
                      res.viewport[0] + "x" + res.viewport[1] +
                      "  slides " + res.range + "/" + res.slidesTotal +
                      "  collisions " + total);
        }
        return verdict(res);
      });
    });
  }

  function all() { return slice(0, undefined); }

  var api = { all: all, slice: slice, collideSlide: collideSlide, spec: spec,
              CONFIG: CONFIG, settleMs: settleMs, guardViewport: guardViewport,
              pressStart: pressStart, activate: activate,
              revealFrags: revealFrags, verdict: verdict };

  global.__audit = global.__audit || {};
  global.__audit.collide = api;
  global.AuditCollide = api;
})(typeof window !== "undefined" ? window : this);
