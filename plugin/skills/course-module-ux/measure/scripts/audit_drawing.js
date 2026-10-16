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
                     shape (a hull, a room) fills only along its outline; a figure
                     that steps is judged at its last step as well (operator,
                     2026-10-15: "the visual is too big, much empty space").

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
    return s;
  }
  /* a part drawn through a clip-path is cut to that shape - by construction it cannot poke out */
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
  function toLocal(el, p) { return pt(el, p.x, p.y).matrixTransform(el.getScreenCTM().inverse()); }
  /* a part's outline as screen points - its real geometry where it has one, its box otherwise */
  function outline(el) {
    var pts = [], i;
    if (typeof el.getTotalLength === "function" && tag(el) !== "text") {
      var L = 0;
      try { L = el.getTotalLength(); } catch (e) { L = 0; }
      if (L > 0) {
        /* a point every ~5 screen px along a long outline (a hull, a deck line), never fewer than CONFIG.samples */
        var m = el.getScreenCTM(), sc = m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1;
        var N = Math.min(600, Math.max(CONFIG.samples, Math.ceil(L * sc / 5)));
        /* a closed outline is sampled half a step off its seam: Chrome's isPointInFill misreads a circle's own
           start point at some scales (a gauge hub "poking out" of its dial at 1920 x 1080) */
        var off = closed(el) ? 0.5 : 0;
        for (i = 0; i < N; i++) {
          var a = el.getPointAtLength(L * (i + off) / N);
          pts.push(toScreen(el, a.x, a.y));
        }
        if (!closed(el)) { var z = el.getPointAtLength(L); pts.push(toScreen(el, z.x, z.y)); }
        return pts;
      }
    }
    var b = el.getBBox();
    if (tag(el) === "text") {
      /* SVG gives a label's box as its whole line (the em box); the letters themselves sit in about
         the middle three-quarters - judged on that, a "1" in a badge or a word over a line is fair */
      b = { x: b.x, y: b.y + 0.18 * b.height, width: b.width, height: 0.74 * b.height };
    }
    [[0, 0], [0.5, 0], [1, 0], [1, 0.5], [1, 1], [0.5, 1], [0, 1], [0, 0.5]].forEach(function (f) {
      pts.push(toScreen(el, b.x + f[0] * b.width, b.y + f[1] * b.height));
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
  function painted(svg) {
    return qa(svg, PARTS).filter(function (el) {
      return !inHiddenRoot(el, svg) && laidOut(el) && (fills(el) || strokes(el));
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
    var copies = expandUses(svg);
    try {
      /* every painted part that is laid out - also one faded out now that a later step of the figure shows
         (a zone ring, a highlight): it must not be cut off when it appears. Checks 1 and 3 judge what shows now. */
      var geom = painted(svg);
      var items = geom.filter(function (it) { return shown(it.el, svg); });

      /* ---- 1 INSIDE ---- */
      var holders = items.filter(function (it) {
        return closed(it.el) && strokes(it.el) && !upFlag(it.el, "data-no-contain", svg);
      });
      items.forEach(function (P) {
        if (upFlag(P.el, "data-may-cross", svg) || clippedPart(P.el, svg)) { return; }
        if (!(closed(P.el) || P.t === "text" || P.t === "image")) { return; }
        holders.forEach(function (S) {
          if (S === P || S.b.w * S.b.h < CONFIG.minAreaRatio * P.b.w * P.b.h) { return; }
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
        items.forEach(function (E) {
          if (E === T || E.el.contains(T.el) || upFlag(E.el, "data-may-overlap", svg)) { return; }
          if (E.t === "text") {
            /* two labels: their letters may not overlap. Lines of one label stacked one under the other are
               a paragraph - only side by side do they need the safe zone between them */
            var ox = Math.min(T.b.x + T.b.w, E.b.x + E.b.w) - Math.max(T.b.x, E.b.x);
            var oy = Math.min(T.b.y + T.b.h, E.b.y + E.b.h) - Math.max(T.b.y, E.b.y);
            var stacked = ox > 0 && oy <= 0;
            var touch = stacked ? oy > 1 : (ox > -pad && oy > 1);
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
      /* ---- 4 EMPTY ---- the drawing fills the frame it is given: no large blank area inside it */
      var E4 = emptySpace(svg, geom);
      if (E4) {
        report(out, { check: "empty", where: where, part: "blank " + Math.round(E4.blank * 100) + " % of the frame, largest piece " +
                      Math.round(E4.w) + " x " + Math.round(E4.h) + " px = " + Math.round(E4.share * 100) + " %", other: E4.frame,
                      detail: "too much empty space (limits: " + Math.round(CONFIG.emptyMaxBlank * 100) + " % blank, " +
                      Math.round(CONFIG.emptyMaxShare * 100) + " % in one piece) - draw to the frame, crop the drawing, or give the room to the words" }, [svg]);
      }
    } finally {
      copies.forEach(function (c) { c.parentNode.removeChild(c); });
    }
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
    var full = [];
    for (r = 0; r < rows; r++) { full.push([]); for (c = 0; c < cols; c++) { full[r].push(0); } }
    function mark(x0, y0, x1, y1) {
      var c0 = Math.max(0, Math.floor((x0 - fr.x) / cell)), c1 = Math.min(cols - 1, Math.floor((x1 - fr.x) / cell));
      var r0 = Math.max(0, Math.floor((y0 - fr.y) / cell)), r1 = Math.min(rows - 1, Math.floor((y1 - fr.y) / cell));
      for (r = r0; r <= r1; r++) { for (c = c0; c <= c1; c++) { full[r][c] = 1; } }
    }
    /* a figure that steps is judged complete - its last step - as well as now: parts that arrive later are content */
    var parts = geom, f = svg.__kit;
    if (f && f.steps && f.steps() && f.n !== f.steps()) {
      var n0 = f.n;
      try { f.go(f.steps(), true); parts = geom.concat(painted(svg)); } finally { f.go(n0, true); }
    }
    /* on a task, what is laid ON the drawing to answer (a tap area, an empty label box - absolutely placed, with
       data-key or data-zone, as gb_zoom.js counts them) is content of the picture too: a band left for the label
       boxes is not empty space */
    var holder = svg.parentNode;
    if (holder && holder.querySelectorAll) {
      Array.prototype.forEach.call(holder.querySelectorAll("[data-key],[data-zone],[data-hotspot]"), function (el) {
        if (el.parentNode !== holder || getComputedStyle(el).position !== "absolute") { return; }
        var bb = el.getBoundingClientRect();
        if (bb.width && bb.height) { mark(bb.left, bb.top, bb.right, bb.bottom); }
      });
    }
    parts.forEach(function (it) {
      var b = it.b, a = b.w * b.h;
      if (a >= 0.8 * fr.w * fr.h) { return; }                    /* a panel or background is not content */
      if (a < CONFIG.emptyBigPart * fr.w * fr.h || it.t === "text") { mark(b.x, b.y, b.x + b.w, b.y + b.h); return; }
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
          if (height * width > best.a) { best = { a: height * width, w: width, h: height }; }
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
    if (!hole && blank <= CONFIG.emptyMaxBlank) { return null; }
    return { w: w, h: h, share: share, blank: blank, hole: hole, frame: name };
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

  function page() {
    var ab = guard();
    if (ab) { return verdict(ab); }
    var out = [], svgs = qa(document, "svg").filter(function (s) { return !s.ownerSVGElement && shown(s, s); });
    svgs.forEach(function (s, i) { checkSvg(s, "drawing " + (i + 1) + (s.id ? " #" + s.id : ""), out, document.body); });
    checkPictures(document.body, "page", out, document.body);
    return verdict({ drawings: svgs.length, findings: out });
  }

  function all() {
    var ab = guard();
    if (ab) { return Promise.resolve(verdict(ab)); }
    var sb = document.querySelector(CONFIG.startBtnSel);
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
            .forEach(function (v) { count++; checkSvg(v, where, out, s); });
          checkPictures(s, where, out, s);
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

  global.AuditDrawing = { all: all, page: page, show: show, spec: function () { return CONFIG; } };
  global.__audit = global.__audit || {};
  global.__audit.drawing = global.AuditDrawing;
})(window);
