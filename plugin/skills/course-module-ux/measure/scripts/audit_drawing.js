/* ==========================================================================
   audit_drawing.js — is every drawing whole, in one piece, and readable?

   THE FAILURES THIS WAS WRITTEN AFTER (owner, 2026-10-15, IGF pilot Modules 1-2)
   An engine room drawn as a plain rectangle in a hull whose stern slopes: its
   corner poked out through the ship. A fuel tank and a vent-mast top cut off
   at the edge of their drawing. A label printed over a deckhouse, a caption
   running through a box's border. Every other check was green: nothing
   overflowed the slide and no HTML text collided - these are all INSIDE one
   <svg>, where no other probe looks.

   FOUR CHECKS, in every visible <svg> (and every <img>/<canvas> on a slide):

     1  INSIDE       a part (a closed shape, a label, a picture) whose centre lies
                     inside an OUTLINED closed shape - a hull, a tank, a room, a box,
                     at least CONFIG.minAreaRatio x its size - stays inside it
                     everywhere. Judged on real geometry: points along the part's
                     own outline, tested with isPointInFill / isPointInStroke, so a
                     sloping hull, a round tank and a rounded corner are exact.
     2  CUT OFF      nothing is clipped: no part reaches past the edge of its
                     <svg> box or of any clipping ancestor (overflow hidden), and no
                     picture past its slide. Reported with how many px are lost.
     3  TEXT ZONE    every label has its own safe zone: its box, grown by
                     CONFIG.textPadPx, touches no other painted shape, line or
                     label - unless the label sits INSIDE that shape, and then it
                     keeps the same clearance from the shape's edge. A leader line
                     may end at its label (CONFIG.leaderPx around its ends).

     4  EMPTY        the drawing fills the frame it is shown in (a kit figure's
                     panel, or the <svg> box): at most CONFIG.emptyMaxBlank of the
                     frame more than one grid cell from any content, and no blank
                     piece over CONFIG.emptyMaxShare. Letterbox bands count; a large
                     shape (a hull, a room) fills only along its outline; a pipe (an open
                     stroked path) counts by its bounding box; a figure that steps is
                     judged at its BUSIEST step - the state with the least blank, not
                     step 0 - and the finding says where the largest blank piece is
                     (operator, 2026-10-15: "the visual is too big, much empty space";
                     IGF M06 2026-10-16: thin pipes read as blank, rest states failed).

     5  CONTRAST     (a figure-kit drawing only, 2.44.0) every part can be seen against the figure's dark panel:
                     a label 4.5:1 (3:1 large), a shape or line 3:1. A part coloured for a light slide (navy,
                     steel) vanishes there. The kit's own parts (colour set in kit.css) are exempt; data-low-contrast
                     marks a part meant to be quiet. See checkContrast(). Since 2.48.0 the kit colours every part
                     for the panel it is on (kit.css .kit-light): this check is the safety net.
     6  SMALL TEXT   (a figure-kit drawing, 2.48.0) no word under CONFIG.minTextPx as rendered. The kit grows its
                     own type classes when a figure is shown smaller than 1:1; a size a course part sets is judged.
     7  PHOTO OVER   (2.49.6) a real photograph (<image> of a .jpg/.png, or <foreignObject> holding an <img>) is
                     painted over parts of the drawing. A photo goes beside the drawing; a marker drawn after the
                     photo is fine. data-may-overlap does not excuse it. See checkPhotos().

     A figure-kit drawing is laid out by kit.js first (its labels, the 12.5 px floor, its frame) and, in a deck,
     judged at the end of every step as well as at step 0 (CONFIG.kitSteps).

     MOTION (2.50.6, M01 benchmark run 5). A drawing with an endless animation (a running engine's pistons, a vent's
     puffs, a flow) is judged on EVERY frame of it, not on the one the probe happened to see: checks 1-3 run at
     CONFIG.motionPhases evenly spaced phases of every endless animation's cycle, held still, and a finding on any of
     them is reported once ("on 3 of 9 frames of its motion"). The animations are put back as they were. An unchanged
     spec flipped between PASS and FAIL from one build to the next before (s03: puffs out of the hull, RUNNING over
     its own piston).

     Shapes inside <defs> drawn with <use> (a shared hull, a symbol) are copied
     in, invisibly, for the measurement and removed after.

   NOT A FINDING - mark it in the drawing, so the reason is written down:
     data-may-cross    a part MEANT to cross an outline (a pipe through a bulkhead,
                       a mast above the deck)
     data-no-contain   an outline that holds nothing (a sea band, a dimension frame)
     data-may-overlap  a label meant to sit on a shape (a value on a gauge face)
     data-audit-ignore a whole <svg>

   HOW TO RUN (serve over http, then in the page)
     await AuditDrawing.all()     every slide of a deck (Start is pressed)
     AuditDrawing.page()          every drawing on any page - a task page, a figure
     AuditDrawing.show(res.findings)   outline them: the part red, the other blue
   (also window.__audit.drawing) - prints one line per finding and a verdict, and
   sets window.__auditExit to 0 or 1.

   ES5-safe syntax (no arrow functions, no optional chaining, no ??).
   ========================================================================== */
(function (global) {
  "use strict";

  var CONFIG = {
    slideSel: ".slide",
    activeClass: "active",
    transientClasses: ["leaving", "leaving-back", "prev", "next"],
    startBtnSel: "#startBtn, [data-audit-start], .deck-start",
    settleMs: 600,
    minViewportWidth: 320,
    minViewportHeight: 320,
    tolPx: 1.5,              /* screen px a part may stand past an outline it sits in (anti-aliasing) */
    edgeTolPx: 0.4,          /* screen px of a part's paint the drawing's frame may shave - next to nothing */
    minAreaRatio: 2.2,       /* a container is at least this many times the part's size */
    minPartPx: 3,            /* parts smaller than this on screen are not judged */
    samples: 28,             /* points along a part's outline */
    textPadPx: 4,            /* a label's own safe zone, screen px */
    leaderPx: 9,             /* a line may touch a label this close to the line's own end */
    emptyGrid: 60,           /* EMPTY: cells along the frame's longer side */
    emptyMaxShare: 0.2,      /* EMPTY: the largest blank rectangle may take at most this share of the frame */
    emptyMinSide: 0.2,       /* EMPTY: ... and counts only when it is this wide AND this tall (a share of the frame) */
    emptyMinFramePx: 160,    /* EMPTY: frames smaller than this are not judged */
    emptyMaxBlank: 0.5,      /* EMPTY: at most this share of the frame may be more than one cell from any content
                                (calibrated on the IGF pilot, 2026-10-15: well-filled figures 24-33 %, the ones the
                                operator called empty 53-74 %) */
    emptyBigPart: 0.06,      /* EMPTY: a shape larger than this share of the frame fills only along its outline */
    emptyPipeBox: 0.25,      /* EMPTY: a pipe (an open stroked path, no fill) counts by its bounding box up to this share of
                                the frame; a longer route only a cell either side of its line */
    figTextContrast: 4.5,    /* CONTRAST: a kit figure's label against its panel (WCAG AA), */
    figLargeContrast: 3,     /*           a large one (24 px, or bold 18.66 px, as rendered) */
    figGraphicContrast: 3,   /*           a shape or line (WCAG 1.4.11) */
    minTextPx: 12.5,         /* SMALL TEXT: a kit figure's words, as rendered */
    kitSteps: true,          /* all(): a kit figure is judged at the end of each of its steps as well as at step 0 */
    motionPhases: 9,         /* MOTION: checks 1-3 at this many phases (0 to 1) of every endless animation's cycle */
    outlineCache: true,      /* a shape's outline sampled once while its geometry is unchanged (2.61.0) - false: every time */
    maxExamples: 40
  };
  if (global.__auditDrawingConfig) {
    for (var ck in global.__auditDrawingConfig) {
      if (Object.prototype.hasOwnProperty.call(global.__auditDrawingConfig, ck)) { CONFIG[ck] = global.__auditDrawingConfig[ck]; }
    }
  }

  var NS = "http://www.w3.org/2000/svg";
  var HIDDEN_ROOTS = "defs, symbol, clipPath, mask, marker, pattern";
  var PARTS = "rect, polygon, path, circle, ellipse, line, polyline, text, image";
  var CLOSED = { rect: 1, polygon: 1, circle: 1, ellipse: 1 };

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function qa(root, sel) { return Array.prototype.slice.call(root.querySelectorAll(sel)); }
  function tag(el) { return (el.tagName || "").toLowerCase(); }
  function upFlag(el, attr, stop) {
    for (var n = el; n && n !== stop; n = n.parentNode) {
      if (n.hasAttribute && n.hasAttribute(attr)) { return true; }
    }
    return false;
  }
  function inHiddenRoot(el, svg) {
    for (var n = el.parentNode; n && n !== svg; n = n.parentNode) {
      if (n.matches && n.matches(HIDDEN_ROOTS)) { return true; }
    }
    return false;
  }
  /* `display` ONLY above the drawing - the deck fades a slide in, so opacity is mid-transition when we
     measure (the trap audit_collide.js honours). Inside the drawing, a part at opacity 0 paints nothing. */
  function laidOut(el) {
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      if (getComputedStyle(n).display === "none") { return false; }
    }
    return true;
  }
  /* Animations and transitions that END are run to their end before a drawing is judged, as audit_deck.js does for a slide
     (C11, IGF M06: a sign of kit-static-charge, 16:1 on its panel, read 1.5:1 once - caught mid-fade; a deck's own fade-in
     or a colour transition moves a computed colour for a moment too). Only what is in the drawing, or holds it. An endless
     animation (a flow, a flicker) has no end and is left running. */
  function settle(svg) {
    var n = 0;
    if (!document.getAnimations) { return 0; }
    document.getAnimations().forEach(function (a) {
      var t = a.effect && a.effect.target;
      if (!t || !(svg.contains(t) || t.contains(svg))) { return; }
      try {
        var timing = a.effect.getComputedTiming ? a.effect.getComputedTiming() : {};
        if (timing.endTime !== Infinity && timing.iterations !== Infinity) { a.finish(); n++; }
      } catch (e) { /* an endless animation cannot finish */ }
    });
    return n;
  }
  /* MOTION (2.50.6) - the endless animations in a drawing (a running engine's pistons, a vent's puffs, a flow), all held
     still at one moment of ONE clock: `phase` 0 to 1 across the longest cycle, started two cycles in, so every delay has
     passed. One clock keeps the frames real - parts the kit staggers on purpose (puffs, spray dots, pistons out of step)
     stay staggered; held each at the same phase of its own cycle, a spray's dots piled onto each other */
  function endless(svg) {
    if (!document.getAnimations) { return []; }
    return document.getAnimations().filter(function (a) {
      var t = a.effect && a.effect.target;
      if (!t || !svg.contains(t)) { return false; }
      try {
        var c = a.effect.getComputedTiming();
        return c.iterations === Infinity && c.duration > 0;
      } catch (e) { return false; }
    });
  }
  function holdAt(anims, phase) {
    var span = 0, lag = 0;
    anims.forEach(function (a) {
      try { span = Math.max(span, a.effect.getComputedTiming().duration); lag = Math.max(lag, a.effect.getTiming().delay || 0); }
      catch (e) { /* not timed */ }
    });
    var T = lag + (2 + phase) * span;
    anims.forEach(function (a) {
      try { a.pause(); a.currentTime = T; } catch (e) { /* judged as it is */ }
    });
  }
  /* does an animation run on this element's opacity? (a kit part fading in or out by its value, or a blink) */
  function animatesOpacity(n) {
    if (!n.getAnimations) { return false; }
    try {
      return n.getAnimations().some(function (a) {
        var kf = a.effect && a.effect.getKeyframes ? a.effect.getKeyframes() : [];
        return kf.some(function (k) { return k.opacity !== undefined; });
      });
    } catch (e) { return false; }
  }
  function shown(el, svg) {
    var n;
    if (!laidOut(el)) { return false; }
    for (n = el; n && n !== svg && n.nodeType === 1; n = n.parentElement) {
      if (n.hasAttribute("data-audit-copy")) { continue; }
      var c = getComputedStyle(n);
      if (parseFloat(c.opacity) < 0.05 || c.visibility === "hidden") { return false; }
    }
    return true;
  }
  function paint(v, op) {
    return v && v !== "none" && !/rgba\([^)]*,\s*0\)$/.test(v) && v !== "transparent" && parseFloat(op === "" ? 1 : op) > 0.05;
  }
  function fills(el) { var c = getComputedStyle(el); return tag(el) === "text" || tag(el) === "image" || paint(c.fill, c.fillOpacity); }
  function strokes(el) { var c = getComputedStyle(el); return paint(c.stroke, c.strokeOpacity) && parseFloat(c.strokeWidth) > 0; }
  function closed(el) {
    var t = tag(el);
    if (CLOSED[t]) { return true; }
    return t === "path" && /[Zz]\s*$/.test(el.getAttribute("d") || "");
  }
  function label(el) {
    var t = tag(el), s = t;
    if (el.id) { s += "#" + el.id; }
    var c = (el.getAttribute("class") || "").trim();
    if (c) { s += "." + c.split(/\s+/).slice(0, 2).join("."); }
    if (t === "text") { s += ' "' + (el.textContent || "").trim().slice(0, 28) + '"'; }
    var g = el.parentNode;
    while (g && tag(g) === "g") {
      var gc = (g.getAttribute("class") || "").trim();
      if (g.id || gc) { s += " in g" + (g.id ? "#" + g.id : "") + (gc ? "." + gc.split(/\s+/)[0] : ""); break; }
      g = g.parentNode;
    }
    /* a figure-kit part's own spec id (2.56.0): "path.kit-vessel in g.kit-part" did not say WHICH part of the spec to
       move, so a fix was a guess - the builder now reads "[part TK1]" and finds it in the .kit.json */
    var kp = el.closest ? el.closest("[data-kit-id]") : null;
    if (kp && kp.getAttribute("data-kit-id")) { s += " [part " + kp.getAttribute("data-kit-id") + "]"; }
    return s;
  }
  /* a part drawn through a clip-path is cut to that shape - by construction it cannot poke out */
  /* the piece of equipment a shape belongs to: a figure-kit part drawn as the real thing (2.52.0) is built of pieces that
     overlap by design - a valve's flanges, cast body, bonnet and actuator; a tank's saddles under its shell. The kit draws
     them in one group marked data-kit-body, and INSIDE judges that group as one object: a piece is never "poking out" of
     another piece of the same equipment, but the equipment still is, out of the room it stands in */
  function kitBody(el, svg) {
    for (var n = el; n && n !== svg; n = n.parentNode) {
      if (n.hasAttribute && n.hasAttribute("data-kit-body")) { return n; }
    }
    return null;
  }
  function clippedPart(el, svg) {
    for (var n = el; n && n !== svg && n.nodeType === 1; n = n.parentElement) {
      if (n.getAttribute("clip-path") || getComputedStyle(n).clipPath !== "none") { return true; }
    }
    return false;
  }
  function origin(el) {
    for (var n = el; n; n = n.parentNode) {
      if (n.hasAttribute && n.hasAttribute("data-audit-copy")) { return n.previousSibling; }
    }
    return el;
  }

  /* ---- a <use> of something in <defs> is drawn in a closed shadow tree: copy it in for the measurement ---- */
  function expandUses(svg) {
    var made = [];
    qa(svg, "use").forEach(function (u) {
      if (inHiddenRoot(u, svg) || getComputedStyle(u).display === "none") { return; }
      var ref = u.getAttribute("href") || u.getAttribute("xlink:href") || "";
      if (ref.charAt(0) !== "#") { return; }
      var src = document.getElementById(ref.slice(1));
      if (!src) { return; }
      var x = u.getAttribute("x") || "0", y = u.getAttribute("y") || "0", copy;
      if (tag(src) === "symbol") {
        copy = document.createElementNS(NS, "svg");
        ["viewBox", "preserveAspectRatio"].forEach(function (k) { if (src.getAttribute(k)) { copy.setAttribute(k, src.getAttribute(k)); } });
        copy.setAttribute("x", x); copy.setAttribute("y", y);
        copy.setAttribute("width", u.getAttribute("width") || "100%");
        copy.setAttribute("height", u.getAttribute("height") || "100%");
        copy.setAttribute("overflow", "visible");
        Array.prototype.forEach.call(src.childNodes, function (c) { copy.appendChild(c.cloneNode(true)); });
      } else {
        copy = document.createElementNS(NS, "g");
        copy.setAttribute("transform", "translate(" + x + " " + y + ")");
        copy.appendChild(src.cloneNode(true));
      }
      var wrap = document.createElementNS(NS, "g");
      if (u.getAttribute("transform")) { wrap.setAttribute("transform", u.getAttribute("transform")); }
      if (u.getAttribute("class")) { wrap.setAttribute("class", u.getAttribute("class")); }
      ["data-may-cross", "data-no-contain", "data-may-overlap"].forEach(function (k) { if (u.hasAttribute(k)) { wrap.setAttribute(k, ""); } });
      wrap.setAttribute("data-audit-copy", ref);
      wrap.setAttribute("aria-hidden", "true");
      wrap.style.opacity = "0.001";            /* laid out and measurable, never seen */
      wrap.appendChild(copy);
      qa(wrap, "[id]").forEach(function (n) { n.removeAttribute("id"); });
      u.parentNode.insertBefore(wrap, u.nextSibling);
      made.push(wrap);
    });
    return made;
  }

  function pt(el, x, y) {
    var o = el.ownerSVGElement || el, p = o.createSVGPoint();
    p.x = x; p.y = y;
    return p;
  }
  function toScreen(el, x, y) { return pt(el, x, y).matrixTransform(el.getScreenCTM()); }
  /* INV (2.52.0): each shape's inverse screen matrix, kept for one pass over a still drawing (the checks below ask it again
     for every point they test; a figure-kit drawing of real equipment has twice the shapes, and an audit ran past the
     studio's time). Started and ended by the pass that uses it; nothing moves inside a pass */
  var INV = null;
  function toLocal(el, p) {
    var m = INV && INV.get(el);
    if (!m) { m = el.getScreenCTM().inverse(); if (INV) { INV.set(el, m); } }
    return pt(el, p.x, p.y).matrixTransform(m);
  }
  /* 2.61.0 - a shape's outline in its OWN units is the same while its geometry is: kept per shape and sampled again only
     when its geometry changes (its attributes, the CSS geometry properties, its length, the number of points). A drawing
     is measured at every frame of its motion (CONFIG.motionPhases) and at every step, and the kit's motions only move,
     turn, fade or flow a shape (transform, opacity, stroke-dashoffset) - never change its own geometry: getPointAtLength
     was 40 % of a deck's check (IGF M02: 21 of 53 s). Where the points are on screen is worked out every time, from the
     shape's screen matrix - asked once per shape now, not once per point (the same matrix, the same points).
     CONFIG.outlineCache false: sampled every time, as before (the test that the findings are the same) */
  var LOCAL = typeof WeakMap === "function" ? new WeakMap() : null;
  var GEO_ATTR = ["d", "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry", "x1", "y1", "x2", "y2", "points", "pathLength", "transform"];
  var GEO_CSS = ["d", "x", "y", "width", "height", "cx", "cy", "r", "rx", "ry"];
  function geoKey(el, L, N, off) {
    var cs = getComputedStyle(el), s = tag(el) + "|" + L + "|" + N + "|" + off, i;
    for (i = 0; i < GEO_ATTR.length; i++) { s += "|" + el.getAttribute(GEO_ATTR[i]); }
    for (i = 0; i < GEO_CSS.length; i++) { s += "|" + cs.getPropertyValue(GEO_CSS[i]); }
    return s;
  }
  /* a part's outline as screen points - its real geometry where it has one, its box otherwise */
  function outline(el) {
    var pts = [], i, m = el.getScreenCTM();
    if (typeof el.getTotalLength === "function" && tag(el) !== "text") {
      var L = 0;
      try { L = el.getTotalLength(); } catch (e) { L = 0; }
      if (L > 0) {
        /* a point every ~5 screen px along a long outline (a hull, a deck line), never fewer than CONFIG.samples */
        var sc = m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1;
        var N = Math.min(600, Math.max(CONFIG.samples, Math.ceil(L * sc / 5)));
        /* a closed outline is sampled half a step off its seam: Chrome's isPointInFill misreads a circle's own
           start point at some scales (a gauge hub "poking out" of its dial at 1920 x 1080) */
        var off = closed(el) ? 0.5 : 0;
        var key = CONFIG.outlineCache && LOCAL ? geoKey(el, L, N, off) : null, kept = key && LOCAL.get(el), loc;
        if (kept && kept.key === key) {
          loc = kept.loc;
        } else {
          loc = [];
          for (i = 0; i < N; i++) {
            var a = el.getPointAtLength(L * (i + off) / N);
            loc.push(a.x, a.y);
          }
          if (!closed(el)) { var z = el.getPointAtLength(L); loc.push(z.x, z.y); }
          if (key) { LOCAL.set(el, { key: key, loc: loc }); }
        }
        for (i = 0; i < loc.length; i += 2) { pts.push(pt(el, loc[i], loc[i + 1]).matrixTransform(m)); }
        return pts;
      }
    }
    var b = el.getBBox();
    if (tag(el) === "text") {
      /* SVG gives a label's box as its whole line (the em box); the letters themselves sit in about
         the middle three-quarters - judged on that, a "1" in a badge or a word over a line is fair.
         2.60.0: the trim is one LINE's, not the block's - a four-line kit text lost a whole line's height off its foot
         and its last line printed over the next text's first one unseen ("cool the liquid" over "no venting to
         atmosphere", M01 benchmark s07; only the review sheet saw it) */
      var rows = Math.max(1, qa(el, "tspan").filter(function (s) { return getComputedStyle(s).display !== "none"; }).length);
      var lh = b.height / rows;
      b = { x: b.x, y: b.y + 0.18 * lh, width: b.width, height: b.height - 0.26 * lh };
    }
    [[0, 0], [0.5, 0], [1, 0], [1, 0.5], [1, 1], [0.5, 1], [0, 1], [0, 0.5]].forEach(function (f) {
      pts.push(pt(el, b.x + f[0] * b.width, b.y + f[1] * b.height).matrixTransform(m));
    });
    return pts;
  }
  function box(pts) {
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    pts.forEach(function (p) { x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y); x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y); });
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2 };
  }
  function inFill(S, p) { try { return S.isPointInFill(toLocal(S, p)); } catch (e) { return false; } }
  function onStroke(S, p) { try { return S.isPointInStroke(toLocal(S, p)); } catch (e) { return false; } }
  function within(S, p) { return inFill(S, p) || onStroke(S, p); }
  function strokeHalfPx(el) {
    if (!strokes(el)) { return 0; }
    var m = el.getScreenCTM();
    return parseFloat(getComputedStyle(el).strokeWidth) * Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) / 2;
  }
  function report(out, f, els) {
    Object.defineProperty(f, "els", { value: els.map(origin), enumerable: false });
    out.push(f);
  }

  /* the visible rectangle of an element: itself (if it clips) cut by every clipping ancestor up to the slide */
  function clipRect(el, stop) {
    var r = { x0: -1e9, y0: -1e9, x1: 1e9, y1: 1e9 };
    for (var n = el; n && n.nodeType === 1; n = n.parentElement) {
      var cs = getComputedStyle(n);
      var clips = n === el ? (tag(n) === "svg" && cs.overflow !== "visible")
                           : (cs.overflowX !== "visible" || cs.overflowY !== "visible" || cs.clipPath !== "none");
      if (clips || n === stop) {
        var b = n.getBoundingClientRect();
        r = { x0: Math.max(r.x0, b.left), y0: Math.max(r.y0, b.top), x1: Math.min(r.x1, b.right), y1: Math.min(r.y1, b.bottom) };
      }
      if (n === stop) { break; }
    }
    return r;
  }
  function lost(b, c) {
    return Math.max(0, c.x0 - b.x, c.y0 - b.y, b.x + b.w - c.x1, b.y + b.h - c.y1);
  }

  /* every painted part of a drawing that is laid out, with its outline as screen points and its box */
  /* a figure-kit body's light and shade or its section hatching (2.52.0, kit.js body(): class kit-sh) is a second copy of
     the body's own shape - judged once, as the body; a bolt sits on a body that is judged */
  function kitCopy(el) { return el.classList && (el.classList.contains("kit-sh") || el.classList.contains("kit-m-bolt")); }
  function painted(svg) {
    return qa(svg, PARTS).filter(function (el) {
      return !kitCopy(el) && !inHiddenRoot(el, svg) && laidOut(el) && (fills(el) || strokes(el));
    }).map(function (el) {
      var pts;
      try { pts = outline(el); } catch (e) { pts = []; }
      return { el: el, t: tag(el), pts: pts, b: box(pts), copy: upFlag(el, "data-audit-copy", svg) };
    }).filter(function (it) { return it.pts.length && (it.b.w >= CONFIG.minPartPx || it.b.h >= CONFIG.minPartPx); });
  }

  function checkSvg(svg, where, out, stop) {
    if (svg.hasAttribute("data-audit-ignore") || svg.ownerSVGElement) { return; }
    var r = svg.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) { return; }
    /* a figure-kit drawing lays itself out for the size it is shown at (its labels, the 12.5 px floor, its frame) the
       first time it is on screen - which may be this very moment, when a check moved it into a question */
    if (svg.__kit && typeof svg.__kit.layout === "function") { try { svg.__kit.layout(); } catch (e) { /* judged as it is */ } }
    settle(svg);
    var copies = expandUses(svg);
    var moving = endless(svg), held = moving.map(function (a) { return { a: a, t: a.currentTime, run: a.playState === "running" }; });
    try {
      /* every painted part that is laid out - also one faded out now that a later step of the figure shows
         (a zone ring, a highlight): it must not be cut off when it appears. Checks 1 and 3 judge what shows now. */
      var geom, items;
      var measure = function () {
        geom = painted(svg);
        items = geom.filter(function (it) { return shown(it.el, svg); });
      };
      var shapes = function (out) {
      INV = new Map();
      try { shapesNow(out); } finally { INV = null; }
      };
      var shapesNow = function (out) {
      /* ---- 1 INSIDE ---- */
      var holders = items.filter(function (it) {
        return closed(it.el) && strokes(it.el) && !upFlag(it.el, "data-no-contain", svg);
      });
      items.forEach(function (P) {
        if (upFlag(P.el, "data-may-cross", svg) || clippedPart(P.el, svg)) { return; }
        if (!(closed(P.el) || P.t === "text" || P.t === "image")) { return; }
        var pb = kitBody(P.el, svg);
        holders.forEach(function (S) {
          if (S === P || S.b.w * S.b.h < CONFIG.minAreaRatio * P.b.w * P.b.h) { return; }
          if (pb && pb === kitBody(S.el, svg)) { return; }   /* two pieces of one piece of equipment (2.52.0) */
          /* a centre outside the holder's box is never in its fill: no point test needed (2.52.0, speed only) */
          if (P.b.cx < S.b.x - 0.5 || P.b.cx > S.b.x + S.b.w + 0.5 || P.b.cy < S.b.y - 0.5 || P.b.cy > S.b.y + S.b.h + 0.5) { return; }
          /* held only when the part's centre is truly inside - a roof bar centred ON a deckhouse's line overhangs by design */
          if (!inFill(S.el, { x: P.b.cx, y: P.b.cy }) || onStroke(S.el, { x: P.b.cx, y: P.b.cy })) { return; }
          var tol = CONFIG.tolPx, worst = 0, n = 0;
          P.pts.forEach(function (p) {
            var dx = P.b.cx - p.x, dy = P.b.cy - p.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
            var q = { x: p.x + dx / d * Math.min(tol, d), y: p.y + dy / d * Math.min(tol, d) };
            if (!within(S.el, q)) {
              n++;
              for (var s = 1; s <= 80; s++) {
                if (s >= d || within(S.el, { x: q.x + dx / d * s, y: q.y + dy / d * s })) { worst = Math.max(worst, s); break; }
              }
            }
          });
          if (n) {
            report(out, { check: "inside", where: where, part: label(P.el), other: label(S.el),
                          detail: "pokes out by " + worst + " px (" + n + "/" + P.pts.length + " points)" }, [P.el, S.el]);
          }
        });
      });

      /* ---- 2 CUT OFF ---- */
      var clip = clipRect(svg, stop);
      geom.forEach(function (P) {
        if (clippedPart(P.el, svg) || P.copy) { return; }
        /* the painted extent - the outline's own thickness counts: a tank whose line is shaved by the frame is cut */
        var h = strokeHalfPx(P.el), hx = h, hy = h;
        /* a straight line with flat ends paints nothing past its ends - a waterline drawn edge to edge is whole */
        if (getComputedStyle(P.el).strokeLinecap === "butt") {
          if (P.b.w < 1) { hy = 0; }
          if (P.b.h < 1) { hx = 0; }
        }
        var b = { x: P.b.x - hx, y: P.b.y - hy, w: P.b.w + 2 * hx, h: P.b.h + 2 * hy };
        var px = lost(b, clip);
        if (px > CONFIG.edgeTolPx) {
          report(out, { check: "cut off", where: where, part: label(P.el), other: "the edge of the drawing",
                        detail: (Math.round(px * 10) / 10) + " px cut off" + (shown(P.el, svg) ? "" : " (in a later step)") }, [P.el]);
        }
      });

      /* ---- 3 TEXT ZONE ---- */
      var pad = CONFIG.textPadPx;
      items.filter(function (it) { return it.t === "text" && !upFlag(it.el, "data-may-overlap", svg); }).forEach(function (T) {
        var g = [], cols = 7, rows = 4, i, j;
        for (i = 0; i < cols; i++) {
          for (j = 0; j < rows; j++) {
            g.push({ x: T.b.x - pad + (T.b.w + 2 * pad) * i / (cols - 1), y: T.b.y - pad + (T.b.h + 2 * pad) * j / (rows - 1) });
          }
        }
        /* an opaque shape drawn over everything behind it that holds this label's whole zone (a step badge's disc on a
           room's line, a readout tile on a pipe) hides what is under it: a line there is not seen through it (2.48.0) */
        var zone = { x: T.b.x - pad, y: T.b.y - pad, x2: T.b.x + T.b.w + pad, y2: T.b.y + T.b.h + pad };
        var covers = items.filter(function (C) {
          if (C === T || !closed(C.el) || !fills(C.el) || C.b.w * C.b.h <= T.b.w * T.b.h) { return false; }
          if (C.b.x > zone.x + 0.5 || C.b.y > zone.y + 0.5 || C.b.x + C.b.w < zone.x2 - 0.5 || C.b.y + C.b.h < zone.y2 - 0.5) { return false; }   /* cannot hold the zone (speed only) */
          var cs = getComputedStyle(C.el), c = parseRgba(cs.fill), op = parseFloat(cs.fillOpacity);
          if (!c || c[3] * (isNaN(op) ? 1 : op) * groupOpacity(C.el, svg) < 0.95) { return false; }
          return [[zone.x, zone.y], [zone.x2, zone.y], [zone.x, zone.y2], [zone.x2, zone.y2]].every(function (q) { return inFill(C.el, { x: q[0], y: q[1] }); });
        });
        items.forEach(function (E) {
          if (E === T || E.el.contains(T.el) || upFlag(E.el, "data-may-overlap", svg)) { return; }
          if (E.t !== "text" && covers.some(function (C) { return C !== E && (E.el.compareDocumentPosition(C.el) & 4); })) { return; }
          if (E.t !== "text") {                    /* a shape nowhere near the label's zone cannot touch it (2.52.0, speed only) */
            var hx = strokeHalfPx(E.el) + 1;
            if (E.b.x - hx > zone.x2 + hx || E.b.x + E.b.w + hx < zone.x - hx || E.b.y - hx > zone.y2 + hx || E.b.y + E.b.h + hx < zone.y - hx) { return; }
          }
          if (E.t === "text") {
            /* two labels: their letters may not overlap. Lines of one label stacked one under the other are
               a paragraph - only side by side do they need the safe zone between them */
            var ox = Math.min(T.b.x + T.b.w, E.b.x + E.b.w) - Math.max(T.b.x, E.b.x);
            var oy = Math.min(T.b.y + T.b.h, E.b.y + E.b.h) - Math.max(T.b.y, E.b.y);
            var stacked = ox > 0 && oy <= 0;
            /* 2.60.0: that is so for the lines of ONE label (a valve's name and its state); two different labels stacked
               may not meet either - "no venting to atmosphere" stood on "cool the liquid" (M01 benchmark s07) */
            var lblT = T.el.closest ? T.el.closest(".kit-lbl") : null, lblE = E.el.closest ? E.el.closest(".kit-lbl") : null;
            var apart = lblT && lblE && lblT !== lblE;
            var touch = stacked ? (apart ? oy > -1 : oy > 1) : (ox > -pad && oy > 1);
            if (touch && (T.el.compareDocumentPosition(E.el) & 4)) {
              report(out, { check: "text zone", where: where, part: label(T.el), other: label(E.el),
                            detail: ox > 1 && oy > 1 ? "two labels print over each other" : "two labels touch" }, [T.el, E.el]);
            }
            return;
          }
          var isClosed = closed(E.el), f = fills(E.el), st = strokes(E.el);
          var holds = isClosed && E.b.w * E.b.h > T.b.w * T.b.h && inFill(E.el, { x: T.b.cx, y: T.b.cy });
          /* inside a small shape (a number in a badge) the clearance is in proportion to the shape */
          var p2 = holds ? Math.min(pad, 0.12 * Math.min(E.b.w, E.b.h)) : pad;
          var gg = g;
          if (p2 !== pad) {
            gg = g.map(function (p) {
              return { x: p.x + (p.x < T.b.cx ? pad - p2 : p.x > T.b.cx ? p2 - pad : 0) * (Math.abs(p.x - T.b.cx) > T.b.w / 2 ? 1 : 0),
                       y: p.y + (p.y < T.b.cy ? pad - p2 : p.y > T.b.cy ? p2 - pad : 0) * (Math.abs(p.y - T.b.cy) > T.b.h / 2 ? 1 : 0) };
            });
          }
          var ends = [];
          if (!isClosed && E.pts.length) { ends = [E.pts[0], E.pts[E.pts.length - 1]]; }
          var nearEnd = function (p) {
            return ends.some(function (e) { return Math.abs(e.x - p.x) + Math.abs(e.y - p.y) < CONFIG.leaderPx * 2; });
          };
          var hit = gg.filter(function (p) {
            if (nearEnd(p)) { return false; }
            if (holds) { return !inFill(E.el, p) || (st && onStroke(E.el, p)); }    /* clearance from its own box's edge */
            return (f && isClosed && inFill(E.el, p)) || (st && onStroke(E.el, p));
          }).length;
          /* and the shape's own outline through the label's safe zone - a thin line slips between grid points */
          if (!hit && st) {
            var h = strokeHalfPx(E.el), x0 = T.b.x - p2 - h, y0 = T.b.y - p2 - h, x1 = T.b.x + T.b.w + p2 + h, y1 = T.b.y + T.b.h + p2 + h;
            hit = E.pts.filter(function (p) {
              return p.x > x0 && p.x < x1 && p.y > y0 && p.y < y1 && !nearEnd(p);
            }).length;
          }
          if (hit) {
            report(out, { check: "text zone", where: where, part: label(T.el), other: label(E.el),
                          detail: holds ? "touches the edge of the shape it sits in" : "is printed over a shape or line" }, [T.el, E.el]);
          }
        });
      });
      };
      /* MOTION - checks 1-3 on every frame of an endless animation, each finding once; the rest at phase 0 */
      var phases = moving.length ? Math.max(2, CONFIG.motionPhases) : 1, seen = [], k;
      for (k = 0; k < phases; k++) {
        if (moving.length) { holdAt(moving, k / (phases - 1)); }
        measure();
        var here = [];
        shapes(here);
        here.forEach(function (f) {
          var s = null;
          seen.forEach(function (o) {
            if (!s && o.f.check === f.check && o.f.part === f.part && o.f.other === f.other && o.f.els.length === f.els.length &&
                o.f.els.every(function (el, i) { return el === f.els[i]; })) { s = o; }
          });
          if (!s) { seen.push({ f: f, k: [k] }); } else if (s.k.indexOf(k) < 0) { s.k.push(k); }
        });
      }
      seen.forEach(function (s) {
        if (s.k.length < phases) { s.f.detail += " - on " + s.k.length + " of " + phases + " frames of its motion"; }
        out.push(s.f);
      });
      if (moving.length) { holdAt(moving, 0); measure(); }
      /* ---- 4 EMPTY ---- the drawing fills the frame it is given: no large blank area inside it */
      var E4 = emptySpace(svg, geom);
      /* EMPTY walks a stepping figure's steps, which restarts its animations: the rest is judged on the frame held again */
      if (moving.length || endless(svg).length) {
        endless(svg).forEach(function (a) {
          if (moving.indexOf(a) < 0) { moving.push(a); held.push({ a: a, t: a.currentTime, run: a.playState === "running" }); }
        });
        holdAt(endless(svg), 0);
        measure();
      }
      if (E4) {
        report(out, { check: "empty", where: where, part: "blank " + Math.round(E4.blank * 100) + " % of the frame, largest piece " +
                      Math.round(E4.w) + " x " + Math.round(E4.h) + " px = " + Math.round(E4.share * 100) + " %", other: E4.frame,
                      detail: "too much empty space" + (E4.steps ? ", even at its busiest step (step " + E4.step + " of " + E4.steps + ")" : "") +
                      " (limits: " + Math.round(CONFIG.emptyMaxBlank * 100) + " % blank, " +
                      Math.round(CONFIG.emptyMaxShare * 100) + " % in one piece) - the largest blank piece is " + E4.region +
                      " - draw to the frame there, crop the drawing, or give the room to the words", region: E4.at }, [svg]);
      }
      /* ---- 5 CONTRAST ---- every part of a kit figure can be seen against what is behind it */
      checkContrast(svg, where, items, out);
      /* ---- 6 SMALL TEXT ---- no word of a kit figure under CONFIG.minTextPx as it is shown (2.48.0) */
      if (svg.classList && svg.classList.contains("kit")) {
        items.forEach(function (T) {
          if (T.t !== "text" || !(T.el.textContent || "").trim()) { return; }
          var m = T.el.getScreenCTM(), px = parseFloat(getComputedStyle(T.el).fontSize) * (m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1);
          if (px < CONFIG.minTextPx - 0.05) {
            report(out, { check: "small text", where: where, part: label(T.el), other: "",
                          detail: "drawn at " + (Math.round(px * 10) / 10) + " px - the floor is " + CONFIG.minTextPx + " px (the kit sets " +
                                  "its own type classes larger by itself; a size set in a course part's css does not grow)" }, [T.el]);
          }
        });
      }
      /* ---- 7 PHOTO OVER THE DRAWING ---- */
      checkPhotos(svg, where, items, out);
    } finally {
      var live = document.getAnimations ? document.getAnimations() : [];
      held.forEach(function (h) {                     /* the motion put back as it was - only what still runs: an */
        if (live.indexOf(h.a) < 0) { return; }        /* animation a step change cancelled is never revived */
        try { h.a.currentTime = h.t; if (h.run) { h.a.play(); } } catch (e) { /* gone with its element */ }
      });
      copies.forEach(function (c) { c.parentNode.removeChild(c); });
    }
  }

  /* A real photograph laid ON the drawing hides the drawing: the M02 fire control plan put its photos on the "free"
     cargo area and they covered the bow of the ship it teaches (IGF M02, 2026-10-19). A photo goes beside the drawing -
     its own column in the figure, or an .inset - never over it. Only parts painted BEFORE the photo count (a marker
     drawn on a photo, "tap the place", is the point of that photo), and a panel behind the whole drawing is not a part.
     data-may-overlap does not excuse a photo: it is for a label on a shape. */
  var PHOTO_RX = /\.(jpe?g|png|webp|avif|gif)(\?|#|$)/i;
  function isPhoto(ph) {
    return tag(ph) === "image" ? PHOTO_RX.test(ph.getAttribute("href") || ph.getAttribute("xlink:href") || "")
                               : !!ph.querySelector("img, picture, video");
  }
  function checkPhotos(svg, where, items, out) {
    var sv = svg.getBoundingClientRect();
    qa(svg, "foreignObject, image").forEach(function (ph) {
      if (!isPhoto(ph) || inHiddenRoot(ph, svg) || !shown(ph, svg)) { return; }
      var r = ph.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) { return; }
      var hits = [];
      items.forEach(function (E) {
        if (E.el === ph || ph.contains(E.el) || E.copy) { return; }
        if (!(E.el.compareDocumentPosition(ph) & 4)) { return; }          /* drawn after the photo: on it, by design */
        if (E.b.w >= 0.9 * sv.width && E.b.h >= 0.9 * sv.height) { return; }   /* a panel behind everything */
        var x0 = Math.max(r.left, E.b.x), y0 = Math.max(r.top, E.b.y), x1 = Math.min(r.right, E.b.x + E.b.w), y1 = Math.min(r.bottom, E.b.y + E.b.h);
        if (x1 - x0 < 2 || y1 - y0 < 2) { return; }
        var n = 0, i, j;
        if (E.t === "text" || E.t === "image") { n = 1; }
        else {
          for (i = 0; i <= 6 && !n; i++) {
            for (j = 0; j <= 6 && !n; j++) {
              if (within(E.el, { x: x0 + (x1 - x0) * i / 6, y: y0 + (y1 - y0) * j / 6 })) { n = 1; }
            }
          }
        }
        if (n) { hits.push(E.el); }
      });
      if (hits.length) {
        report(out, { check: "photo over drawing", where: where, part: label(ph), other: label(hits[0]),
                      detail: "a photograph is painted over " + hits.length + " part(s) of the drawing - put it beside the drawing " +
                              "(its own column, or an .inset), never on it" }, [ph, hits[0]]);
      }
    });
  }

  /* the largest blank rectangle in the frame a drawing is shown in (its .kit-screen panel, or the <svg> box), on a
     grid of the painted parts' boxes. Letterbox bands count: a short drawing in a tall panel leaves them blank too.
     A part as large as the frame (a panel, a background) is not content. Returns null when the frame is filled. */
  function emptySpace(svg, geom) {
    var host = svg.closest ? svg.closest(".kit-screen") : null, fr, name;
    if (host) {
      var hb = host.getBoundingClientRect(), cs = getComputedStyle(host);
      fr = { x: hb.left + parseFloat(cs.paddingLeft), y: hb.top + parseFloat(cs.paddingTop),
             w: hb.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
             h: hb.height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) };
      name = "the figure's panel";
    } else {
      var sb = svg.getBoundingClientRect();
      fr = { x: sb.left, y: sb.top, w: sb.width, h: sb.height };
      name = "the drawing's box";
    }
    if (fr.w < CONFIG.emptyMinFramePx || fr.h < CONFIG.emptyMinFramePx) { return null; }
    var cell = Math.max(fr.w, fr.h) / CONFIG.emptyGrid, cols = Math.ceil(fr.w / cell), rows = Math.ceil(fr.h / cell), r, c;
    /* on a task, what is laid ON the drawing to answer (a tap area, an empty label box - absolutely placed, with
       data-key or data-zone, as gb_zoom.js counts them) is content of the picture too: a band left for the label
       boxes is not empty space */
    var laid = [], holder = svg.parentNode;
    if (holder && holder.querySelectorAll) {
      Array.prototype.forEach.call(holder.querySelectorAll("[data-key],[data-zone],[data-hotspot]"), function (el) {
        if (el.parentNode !== holder || getComputedStyle(el).position !== "absolute") { return; }
        var bb = el.getBoundingClientRect();
        if (bb.width && bb.height) { laid.push(bb); }
      });
    }
    /* one state of the drawing judged: the blank share, the largest blank rectangle and where it is */
    function judge(parts) {
      var full = [], r, c;
      for (r = 0; r < rows; r++) { full.push([]); for (c = 0; c < cols; c++) { full[r].push(0); } }
      function mark(x0, y0, x1, y1) {
        var c0 = Math.max(0, Math.floor((x0 - fr.x) / cell)), c1 = Math.min(cols - 1, Math.floor((x1 - fr.x) / cell));
        var r0 = Math.max(0, Math.floor((y0 - fr.y) / cell)), r1 = Math.min(rows - 1, Math.floor((y1 - fr.y) / cell));
        for (var rr = r0; rr <= r1; rr++) { for (var cc = c0; cc <= c1; cc++) { full[rr][cc] = 1; } }
      }
      laid.forEach(function (bb) { mark(bb.left, bb.top, bb.right, bb.bottom); });
      /* a real photo shown beside the drawing, in its own column, is content too (IGF M02, 2.49.6) */
      qa(svg, "foreignObject, image").forEach(function (ph) {
        if (!isPhoto(ph) || inHiddenRoot(ph, svg) || !shown(ph, svg)) { return; }
        var bb = ph.getBoundingClientRect();
        if (bb.width && bb.height) { mark(bb.left, bb.top, bb.right, bb.bottom); }
      });
      parts.forEach(function (it) {
        var b = it.b, a = b.w * b.h;
        if (a >= 0.8 * fr.w * fr.h) { return; }                    /* a panel or background is not content */
        if (a < CONFIG.emptyBigPart * fr.w * fr.h || it.t === "text") { mark(b.x, b.y, b.x + b.w, b.y + b.h); return; }
        /* a pipe, a wire, a line (an open stroked path with no fill) is counted by its bounding box - the space its bends
           enclose is where its valves, gauges and words sit; counted by its outline alone, a thin pipe read as blank
           (K12, IGF M06). A route longer than CONFIG.emptyPipeBox of the frame is only counted a cell either side. */
        if (!CLOSED[it.t] && !closed(it.el) && strokes(it.el) && !fills(it.el)) {
          if (a <= CONFIG.emptyPipeBox * fr.w * fr.h) { mark(b.x, b.y, b.x + b.w, b.y + b.h); return; }
          it.pts.forEach(function (p) { mark(p.x - cell, p.y - cell, p.x + cell, p.y + cell); });
          return;
        }
        /* a large shape (a hull, a room, a tank) carries information along its outline, not across its blank inside */
        it.pts.forEach(function (p) { mark(p.x, p.y, p.x, p.y); });
      });
      /* largest all-blank rectangle: one histogram of blank cells per row, the largest rectangle under each */
      var hgt = [], best = { a: 0 };
      for (c = 0; c < cols; c++) { hgt.push(0); }
      for (r = 0; r < rows; r++) {
        for (c = 0; c < cols; c++) { hgt[c] = full[r][c] ? 0 : hgt[c] + 1; }
        var st = [];
        for (c = 0; c <= cols; c++) {
          var hh = c < cols ? hgt[c] : 0;
          while (st.length && hgt[st[st.length - 1]] >= hh) {
            var top = st.pop(), height = hgt[top], left = st.length ? st[st.length - 1] + 1 : 0, width = c - left;
            if (height * width > best.a) { best = { a: height * width, w: width, h: height, c0: left, r0: r - height + 1 }; }
          }
          st.push(c);
        }
      }
      /* and the blank share overall: cells more than one cell away from any content */
      var blank = 0;
      for (r = 0; r < rows; r++) {
        for (c = 0; c < cols; c++) {
          var near = false;
          for (var dr = -1; dr <= 1 && !near; dr++) {
            for (var dc = -1; dc <= 1 && !near; dc++) {
              var rr = r + dr, cc = c + dc;
              if (rr >= 0 && rr < rows && cc >= 0 && cc < cols && full[rr][cc]) { near = true; }
            }
          }
          if (!near) { blank++; }
        }
      }
      blank /= rows * cols;
      var w = best.w * cell, h = best.h * cell, share = best.a ? (w * h) / (fr.w * fr.h) : 0;
      /* a margin strip along an edge is not a hole: it must be large both ways to count */
      var hole = share > CONFIG.emptyMaxShare && w >= CONFIG.emptyMinSide * fr.w && h >= CONFIG.emptyMinSide * fr.h;
      return { w: w, h: h, share: share, blank: blank, hole: hole, x: (best.c0 || 0) * cell, y: (best.r0 || 0) * cell };
    }
    /* a figure that steps is judged at its BUSIEST step - the state with the least blank, a hole counting against it - not
       at step 0 (a rest state is sparse by design: the steps bring the parts in) and not only at the last. A figure whose
       fullest state is still too empty is empty. Remembered per drawing and frame, so a run that visits every step judges
       once (K12, IGF M06).
       Each state is judged by what it SHOWS (2.49.7, IGF M01 s02): a part a later step brings in waits at opacity 0, and
       counted at every step it made every state look alike - the rest state won the tie and the finding named "step 0",
       the state with the scale's markers hidden. A tie now goes to the later step, where a figure's parts have come in. */
    var f = svg.__kit, key = [Math.round(fr.x), Math.round(fr.y), Math.round(fr.w), Math.round(fr.h), svg.getAttribute("viewBox"),
                              f && f.steps ? f.steps() : 0].join("|");
    if (svg.__emptyKey === key) { return null; }
    svg.__emptyKey = key;
    var res = null, step = 0;
    var showing = function (parts) { return parts.filter(function (it) { return shown(it.el, svg); }); };
    if (f && f.steps && f.steps() && f.go) {
      var n0 = f.n, k, here;
      try {
        for (k = 0; k <= f.steps(); k++) {
          f.go(k, true);
          settle(svg);                                /* a fade the step started is judged at its end */
          here = judge(showing(painted(svg)));
          if (!res || (here.hole ? 1 : 0) + here.blank <= (res.hole ? 1 : 0) + res.blank) { res = here; step = k; }
        }
      } finally { f.go(n0, true); settle(svg); }
    } else {
      res = judge(showing(geom));
    }
    if (!res.hole && res.blank <= CONFIG.emptyMaxBlank) { return null; }
    /* where the blank piece is, so the drawing can be filled there */
    var tl = res.x <= cell, tr = res.x + res.w >= fr.w - cell, tt = res.y <= cell, tb = res.y + res.h >= fr.h - cell;
    var across = tl && tr ? "across the full width" : tr ? "on the right" : tl ? "on the left" : "in the middle";
    var down = tt && tb ? "the full height" : tb ? "at the bottom" : tt ? "at the top" : "";
    var region = [across, down].filter(Boolean).join(", ") + " - from x " + Math.round(res.x) + ", y " + Math.round(res.y) + " to x " +
                 Math.round(res.x + res.w) + ", y " + Math.round(res.y + res.h) + " px of the frame (" + Math.round(fr.w) + " x " + Math.round(fr.h) + ")";
    return { w: res.w, h: res.h, share: res.share, blank: res.blank, hole: res.hole, frame: name, step: step, steps: f && f.steps ? f.steps() : 0,
             region: region, at: { x: res.x, y: res.y, w: res.w, h: res.h } };
  }

  /* ---- INSET (2.60.0) ---- a real photo laid "over" a kit drawing (figure.inset.over in its .kit-holder) is not part of
     the drawing: the kit places its labels without knowing it, so the photo, its caption and its credit lay over the
     labels and ran past the drawing onto the step buttons (M01 benchmark s03: "Vent mast", "Bunkering station", Next /
     Replay) - and every check was green, only the review sheet saw it. Each of the inset's boxes (the photo, every line
     box of its caption) is judged against the drawing's shown words, against the controls, and against the drawing's
     own box. */
  function rectOf(r) { return { x: r.left, y: r.top, x2: r.right, y2: r.bottom }; }
  function overlapPx(a, b) { return Math.min(Math.min(a.x2, b.x2) - Math.max(a.x, b.x), Math.min(a.y2, b.y2) - Math.max(a.y, b.y)); }
  function checkInsets(svg, where, out) {
    var holder = svg.parentElement;
    if (!holder || !holder.querySelectorAll) { return; }
    qa(holder, "figure.inset.over").forEach(function (fig) {
      if (getComputedStyle(fig).display === "none") { return; }
      var boxes = [];
      qa(fig, "img").forEach(function (im) { var r = im.getBoundingClientRect(); if (r.width > 1 && r.height > 1) { boxes.push({ what: "the photo", r: rectOf(r) }); } });
      qa(fig, "figcaption").forEach(function (fc) {
        var rg = document.createRange();
        rg.selectNodeContents(fc);
        Array.prototype.forEach.call(rg.getClientRects(), function (r) {
          if (r.width > 1 && r.height > 1) { boxes.push({ what: "its caption", r: rectOf(r) }); }
        });
      });
      if (!boxes.length) { return; }
      var name = "inset photo" + (fig.querySelector("img") && fig.querySelector("img").getAttribute("src") ?
                 " " + fig.querySelector("img").getAttribute("src").split("/").pop() : "");
      var seen = {};
      function add(other, what, detail, els) {
        var k = other + "|" + what;
        if (seen[k]) { return; }
        seen[k] = 1;
        report(out, { check: "inset", where: where, part: name, other: other, detail: what + " " + detail }, els);
      }
      qa(svg, "text").forEach(function (t) {
        if (!shown(t, svg) || !(t.textContent || "").trim()) { return; }
        var tr = rectOf(t.getBoundingClientRect());
        boxes.forEach(function (b) {
          if (overlapPx(b.r, tr) > 1) { add(label(t), b.what, "lies over the drawing's words", [fig, t]); }
        });
      });
      var slide = svg.closest ? (svg.closest(CONFIG.slideSel) || document.body) : document.body;
      qa(slide, "button, [data-act], .mediabar").concat(qa(document, "#chrome")).forEach(function (c) {
        if (fig.contains(c) || getComputedStyle(c).display === "none") { return; }
        var cr = c.getBoundingClientRect();
        if (cr.width < 1 || cr.height < 1) { return; }
        boxes.forEach(function (b) {
          if (overlapPx(b.r, rectOf(cr)) > 1) {
            add(c.id ? "#" + c.id : (c.getAttribute("aria-label") || c.getAttribute("data-act") || tag(c)), b.what, "lies over a control", [fig, c]);
          }
        });
      });
      var sr = rectOf(svg.getBoundingClientRect()), past = 0;
      boxes.forEach(function (b) { past = Math.max(past, sr.x - b.r.x, sr.y - b.r.y, b.r.x2 - sr.x2, b.r.y2 - sr.y2); });
      if (past > CONFIG.tolPx) { add("the edge of the drawing", "it", "runs " + Math.round(past) + " px past the drawing", [fig]); }
    });
  }

  function checkPictures(root, where, out, stop) {
    qa(root, "img, canvas, video").forEach(function (el) {
      if (getComputedStyle(el).display === "none" || el.closest(".photo-wrap")) { return; }   /* a full-bleed photo crops by design */
      var b0 = el.getBoundingClientRect();
      if (b0.width < 4 || b0.height < 4) { return; }
      var px = lost({ x: b0.left, y: b0.top, w: b0.width, h: b0.height }, clipRect(el.parentElement, stop));
      if (px > CONFIG.tolPx) {
        report(out, { check: "cut off", where: where, part: tag(el) + (el.id ? "#" + el.id : ""), other: "its box or the slide",
                      detail: Math.round(px) + " px cut off" }, [el]);
      }
    });
  }

  /* ---- 5 CONTRAST (finding 13, IGF M04, 2026-10-16) ----
     A kit figure is drawn on its own dark panel - on a light slide too - so a part coloured for a light slide (navy,
     steel, ink) is painted dark on dark and disappears, and every other probe stayed green. Each painted part of a
     figure-kit drawing is judged against what lies under it: the figure's panel, or the opaque shape it sits on.
       a label      CONFIG.figTextContrast (3:1, a large label CONFIG.figLargeContrast) - set in the rendered size
       a shape/line CONFIG.figGraphicContrast (3:1, WCAG 1.4.11) by its fill or its stroke, whichever shows
     A part the kit itself colours (a fill/stroke rule in kit.css - its frame, bores, masks, rules) is exempt: the
     gallery calibrates those. What a course adds (kit_parts.js css, an inline style) is judged. Anything marked
     data-low-contrast is exempt too (write why next to it). Judged on a kit drawing only: any other drawing
     sits on the slide, whose own colours the deck audit measures. */
  function parseRgba(s) {
    var m = /rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:[ ,/]+([\d.]+%?))?\s*\)/.exec(s || "");
    if (!m) { return null; }
    var a = m[4] === undefined ? 1 : (/%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
    return [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), a];
  }
  function over(top, under, alpha) {
    var a = (top[3] === undefined ? 1 : top[3]) * (alpha === undefined ? 1 : alpha);
    return [top[0] * a + under[0] * (1 - a), top[1] * a + under[1] * (1 - a), top[2] * a + under[2] * (1 - a), 1];
  }
  function relLum(c) {
    function lin(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  }
  function ratioOf(a, b) {
    var l1 = relLum(a), l2 = relLum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  }
  /* what lies behind the drawing: the first non-transparent backgrounds up the page, composited, then the kit's own
     panel rectangle when it is drawn */
  function panelColour(svg) {
    var chain = [], n, c, base = [255, 255, 255, 1], i;
    for (n = svg; n && n.nodeType === 1; n = n.parentElement) {
      c = parseRgba(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) { chain.push(c); if (c[3] >= 0.99) { break; } }
    }
    for (i = chain.length - 1; i >= 0; i--) { base = over(chain[i], base); }
    var pr = qa(svg, "rect.kit-panel")[0];
    if (pr) {
      var f = parseRgba(getComputedStyle(pr).fill), op = parseFloat(getComputedStyle(pr).fillOpacity);
      if (f && f[3] > 0) { base = over(f, base, isNaN(op) ? 1 : op); }
    }
    return base;
  }
  function groupOpacity(el, svg) {
    var o = 1, n;
    for (n = el; n && n.nodeType === 1; n = n.parentElement) {
      var v = parseFloat(getComputedStyle(n).opacity);
      if (!isNaN(v)) { o *= v; }
      if (n === svg) { break; }
    }
    return o;
  }
  /* The opacity a part is JUDGED at: its stylesheet's opacity (a pale cloud, a quiet grid) counts, but a fade a figure's
     value drives - inline style.opacity set by a kit part's render, or an animation on opacity - does not: a sign that is
     fading in by the charge is as legible as it will be at the end of the fade, and measuring it half-faded read 1.5:1 for
     a 16:1 part (C11, IGF M06). A part that is not there at all (opacity under 0.05) is not judged: see shown(). */
  function judgedOpacity(el, svg) {
    var o = 1, n;
    for (n = el; n && n.nodeType === 1; n = n.parentElement) {
      var v = parseFloat(getComputedStyle(n).opacity);
      var driven = n !== svg && ((n.style && n.style.opacity !== "") || animatesOpacity(n));
      if (!isNaN(v) && !driven) { o *= v; }
      if (n === svg) { break; }
    }
    return o;
  }
  function paintOf(el, svg, what) {      /* [r,g,b,a] of a part's fill or stroke, opacities folded into a */
    var cs = getComputedStyle(el), c = parseRgba(what === "stroke" ? cs.stroke : cs.fill);
    if (!c) { return null; }
    var op = parseFloat(what === "stroke" ? cs.strokeOpacity : cs.fillOpacity);
    c[3] = c[3] * (isNaN(op) ? 1 : op) * judgedOpacity(el, svg);
    return c;
  }
  /* the colour rules of kit.css - the kit's own parts are drawn and calibrated for the panel in the gallery (a pipe's
     bore, a valve's mask, a track, a quiet rule are meant to be near the panel's colour). A part whose fill or stroke
     is set by one of those rules is the kit's own; what a course adds (kit_parts.js css, an inline style, an
     attribute) is judged. Where kit.css cannot be read, nothing is exempt. */
  var kitRules = null;
  function kitColourRules() {
    if (kitRules) { return kitRules; }
    kitRules = [];
    function walk(rules) {
      Array.prototype.forEach.call(rules || [], function (r) {
        if (r.cssRules && !r.selectorText) { walk(r.cssRules); return; }
        if (r.selectorText && r.style && (r.style.fill || r.style.stroke)) { kitRules.push(r.selectorText); }
      });
    }
    Array.prototype.forEach.call(document.styleSheets, function (sh) {
      if (!/(^|\/)kit\.css(\?|#|$)/.test(sh.href || "")) { return; }
      try { walk(sh.cssRules); } catch (e) { /* cross-origin: unreadable */ }
    });
    return kitRules;
  }
  function kitOwn(el) {
    return kitColourRules().some(function (sel) { try { return el.matches(sel); } catch (e) { return false; } });
  }
  function checkContrast(svg, where, items, out) {
    if (!(svg.classList && svg.classList.contains("kit")) || svg.hasAttribute("data-low-contrast")) { return; }
    var panel = panelColour(svg), sb = svg.getBoundingClientRect(), seen = 0;
    var shapes = items.filter(function (it) {
      var c = it.t === "text" || it.t === "image" || it.t === "line" || it.t === "polyline" ? null : paintOf(it.el, svg, "fill");
      return c && c[3] >= 0.5 && it.b.w * it.b.h < 0.8 * sb.width * sb.height;
    });
    items.forEach(function (P) {
      if (P.copy || upFlag(P.el, "data-low-contrast", svg) || kitOwn(P.el)) { return; }
      if (P.el.matches(".kit-panel") || (P.t !== "text" && P.b.w * P.b.h >= 0.8 * sb.width * sb.height)) { return; }   /* the panel is what it is judged against */
      var behind = panel, k;
      for (k = shapes.length - 1; k >= 0; k--) {          /* the latest opaque shape drawn under it that holds its centre */
        var S = shapes[k];
        if (S === P || !(S.el.compareDocumentPosition(P.el) & 4) || S.b.w * S.b.h <= P.b.w * P.b.h) { continue; }
        if (P.b.cx < S.b.x - 0.5 || P.b.cx > S.b.x + S.b.w + 0.5 || P.b.cy < S.b.y - 0.5 || P.b.cy > S.b.y + S.b.h + 0.5) { continue; }   /* speed only */
        if (inFill(S.el, { x: P.b.cx, y: P.b.cy })) { behind = over(paintOf(S.el, svg, "fill"), panel); break; }
      }
      var cs = getComputedStyle(P.el), why = "", worst = 99, need = 0, what = "";
      if (P.t === "text") {
        var c = paintOf(P.el, svg, "fill");
        if (!c || !(P.el.textContent || "").trim()) { return; }
        var m = P.el.getScreenCTM(), px = parseFloat(cs.fontSize) * (m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1);
        var large = px >= 24 || (px >= 18.66 && parseFloat(cs.fontWeight) >= 700);
        need = large ? CONFIG.figLargeContrast : CONFIG.figTextContrast;
        worst = ratioOf(over(c, behind), behind);
        what = "label \"" + (P.el.textContent || "").trim().slice(0, 24) + "\" (" + cs.fill + ")";
      } else if (P.t !== "image") {
        var f = fills(P.el) ? paintOf(P.el, svg, "fill") : null, s = strokes(P.el) ? paintOf(P.el, svg, "stroke") : null;
        var rf = f && f[3] > 0.05 ? ratioOf(over(f, behind), behind) : 0, rs = s && s[3] > 0.05 ? ratioOf(over(s, behind), behind) : 0;
        if (!rf && !rs) { return; }
        need = CONFIG.figGraphicContrast;
        worst = Math.max(rf, rs);                               /* it shows if either its fill or its outline does */
        what = (rf >= rs ? "fill " + cs.fill : "line " + cs.stroke);
      } else { return; }
      seen++;
      if (worst < need) {
        report(out, { check: "contrast", where: where, part: label(P.el), other: "the figure's panel",
                      detail: what + " reads " + (Math.round(worst * 10) / 10) + ":1 against what is behind it (" +
                              "rgb(" + Math.round(behind[0]) + "," + Math.round(behind[1]) + "," + Math.round(behind[2]) + ")), needs " + need +
                              ":1 - a kit figure is drawn on a dark panel; colour the part for it (var(--txt-d), --dim-d, --cold ...), " +
                              "or mark a part that is meant to be quiet data-low-contrast" }, [P.el]);
      }
    });
  }

  /* owner, 2026-10-16: "no scrollbar at all allowed" on a slide - a box that scrolls hides what does not fit behind a
     scrollbar the room cannot use. Any element of the slide (the slide too) set to scroll that has more inside than
     it shows; scrollHeight rounds up, so a 1 px difference is not counted */
  function checkScroll(root, where, out) {
    [root].concat(qa(root, "*")).forEach(function (el) {
      var cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden") { return; }
      var down = /(auto|scroll)/.test(cs.overflowY) && el.scrollHeight - el.clientHeight > CONFIG.tolPx;
      var side = /(auto|scroll)/.test(cs.overflowX) && el.scrollWidth - el.clientWidth > CONFIG.tolPx;
      if (down || side) {
        report(out, { check: "scrolls", where: where, part: tag(el), other: "the slide - no scrollbar on a slide",
                      detail: (down ? (el.scrollHeight - el.clientHeight) + " px more than it shows" : "")
                              + (down && side ? ", " : "") + (side ? (el.scrollWidth - el.clientWidth) + " px wider" : "") }, [el]);
      }
    });
  }

  function guard() {
    var w = window.innerWidth || 0, h = window.innerHeight || 0;
    if (w >= CONFIG.minViewportWidth && h >= CONFIG.minViewportHeight) { return null; }
    return { ABORTED: "viewport too small: " + w + "x" + h + " - front the tab and run again", viewport: [w, h] };
  }
  function verdict(res) {
    var fail = !!res.ABORTED || res.findings.length > 0;
    global.__auditExit = fail ? 1 : 0;
    res.counts = {};
    (res.findings || []).forEach(function (f) { res.counts[f.check] = (res.counts[f.check] || 0) + 1; });
    res.verdict = res.ABORTED ? "VERDICT: FAIL (aborted)" : fail ? ("VERDICT: FAIL n=" + res.findings.length) : "VERDICT: PASS";
    if (global.console) {
      console.log("audit_drawing " + location.href + "  viewport " + innerWidth + "x" + innerHeight + "  drawings " +
                  (res.drawings || 0) + "  " + JSON.stringify(res.counts));
      (res.findings || []).slice(0, CONFIG.maxExamples).forEach(function (f) {
        console.log("  [" + f.check + "] " + f.where + ": " + f.part + " - " + f.detail + (f.other ? " (" + f.other + ")" : ""));
      });
      console.log(res.verdict);
    }
    return res;
  }

  /* EMPTY is judged once per drawing and frame in a run (it looks at every step itself): a new run judges again */
  function resetEmpty(root) { qa(root || document, "svg").forEach(function (s) { s.__emptyKey = null; }); }

  function page() {
    var ab = guard();
    if (ab) { return verdict(ab); }
    resetEmpty();
    var out = [], svgs = qa(document, "svg").filter(function (s) { return !s.ownerSVGElement && shown(s, s); });
    svgs.forEach(function (s, i) {
      checkSvg(s, "drawing " + (i + 1) + (s.id ? " #" + s.id : ""), out, document.body);
      checkInsets(s, "drawing " + (i + 1) + (s.id ? " #" + s.id : ""), out);
    });
    checkPictures(document.body, "page", out, document.body);
    return verdict({ drawings: svgs.length, findings: out });
  }

  function all() {
    var ab = guard();
    if (ab) { return Promise.resolve(verdict(ab)); }
    var sb = document.querySelector(CONFIG.startBtnSel);
    resetEmpty();
    var go = (sb && getComputedStyle(sb).display !== "none") ? (sb.click(), sleep(400)) : Promise.resolve();
    return go.then(function () {
      var slides = qa(document, CONFIG.slideSel), out = [], count = 0;
      function step(i) {
        if (i >= slides.length) { return Promise.resolve(); }
        slides.forEach(function (x, j) {
          CONFIG.transientClasses.forEach(function (c) { x.classList.remove(c); });
          x.classList.toggle(CONFIG.activeClass, j === i);
        });
        return sleep(CONFIG.settleMs).then(function () {
          var s = slides[i], where = "slide " + (i + 1) + (s.id ? " (" + s.id + ")" : "");
          qa(s, "svg").filter(function (v) { return !v.ownerSVGElement && shown(v, v) && !v.closest("button, .mediabar, .slide-kind"); })
            .forEach(function (v) {
              count++;
              checkSvg(v, where, out, s);
              checkInsets(v, where, out);
              /* a figure that steps is judged at the end of every step too (2.48.0): an alarm row, a lit label or a moved
                 part that only appears in step 3 was never on screen when the deck was checked at step 0 */
              var f = v.__kit;
              if (!CONFIG.kitSteps || !f || !f.steps || !f.steps()) { return; }
              var seen = {};
              out.forEach(function (x) { if (x.where === where) { seen[x.check + "|" + x.part + "|" + (x.other || "")] = 1; } });
              for (var k = 1; k <= f.steps(); k++) {
                f.go(k, true);
                var more = [];
                checkSvg(v, where + " step " + k, more, s);
                checkInsets(v, where + " step " + k, more);
                more.forEach(function (x) {
                  var key = x.check + "|" + x.part + "|" + (x.other || "");
                  if (!seen[key]) { seen[key] = 1; out.push(x); }
                });
              }
              f.go(0, true);
            });
          checkPictures(s, where, out, s);
          checkScroll(s, where, out);
          return step(i + 1);
        });
      }
      return step(0).then(function () { return verdict({ drawings: count, findings: out }); });
    });
  }

  /* show(findings) - outline them on the page: the part red, the other blue */
  function show(findings) {
    (findings || []).forEach(function (f) {
      (f.els || []).forEach(function (el, k) {
        if (el && el.style) {
          el.style.stroke = k ? "#1565C0" : "#E53935";
          el.style.strokeWidth = k ? "3px" : "4px";
          el.style.strokeDasharray = "none";
          if (tag(el) === "text") { el.style.fill = k ? "#1565C0" : "#E53935"; }
          if (tag(el) === "img" || tag(el) === "canvas") { el.style.outline = "4px solid #E53935"; }
        }
      });
    });
    return (findings || []).length;
  }

  /* figure(svg) - one drawing alone (the figure studio, course-visuals/kit/scripts/studio.py) */
  function figure(svg, where) {
    var ab = guard();
    if (ab) { return verdict(ab); }
    var out = [];
    svg.__emptyKey = null;
    checkSvg(svg, where || "figure", out, (svg.closest && svg.closest(CONFIG.slideSel)) || document.body);
    return verdict({ drawings: 1, findings: out });
  }

  global.AuditDrawing = { all: all, page: page, figure: figure, show: show, spec: function () { return CONFIG; } };
  global.__audit = global.__audit || {};
  global.__audit.drawing = global.AuditDrawing;
})(window);
