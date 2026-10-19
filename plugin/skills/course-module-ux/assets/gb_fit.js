/* ==========================================================================
   gb_fit.js — no drawing is ever cut off at its edges.

   WHY (owner, 2026-10-15, IGF pilot Modules 1-2): a vent mast's top, a fuel
   tank's side and a caption's end were cut off where their drawing's frame
   (the <svg> viewBox) stopped. On a projector a half-drawn tank reads as a
   different shape. audit_drawing.js finds it before a deck is shown; this is
   the safety net for whatever still slips through - a step of an animation
   that only appears later, a label longer on the tablet's font.

   WHAT IT DOES
     When a slide comes up (and when a stepping figure changes step), every
     <svg> on it that has a viewBox is measured: if its drawing reaches past
     the frame, the frame is widened just enough to hold it, plus a small
     margin. It only ever GROWS the frame - never crops, never moves a part -
     and logs a console warning naming the drawing, so the drawing itself is
     fixed at the source. A page with no slides (a task page, a figure) is
     fitted once on load.

     data-fit="off" on an <svg> leaves it alone (a drawing that crops on purpose).

   Loaded by every compiled deck (course-factory compile/). ES5, no dependencies.
   ========================================================================== */
(function (w, d) {
  "use strict";
  var MARGIN = 0.012;          /* of the frame's larger side, at least 3 units */
  var SHAPES = "rect, circle, ellipse, path, polygon, polyline, line, text, image";
  var NOT_DRAWN = "defs, symbol, clipPath, mask, marker, pattern";

  /* what the drawing really paints, in its own units: every shape's box PLUS half its line - getBBox() leaves
     the line out, and getBBox({stroke:true}) is not in Chrome. A shape faded out for a later step counts;
     one inside a clip-path does not (it is cut to its clip). */
  function extent(svg) {
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    Array.prototype.forEach.call(svg.querySelectorAll(SHAPES), function (el) {
      if (el.closest(NOT_DRAWN) || el.closest("[clip-path]")) { return; }
      var bb, m, r;
      try { bb = el.getBBox(); m = el.getScreenCTM(); r = svg.getScreenCTM(); } catch (e) { return; }
      if (!bb || (!bb.width && !bb.height) || !m || !r) { return; }
      var to = r.inverse().multiply(m);           /* the shape's own units -> the drawing's units */
      var cs = w.getComputedStyle(el);
      var h = cs.stroke && cs.stroke !== "none" ? (parseFloat(cs.strokeWidth) || 0) / 2 : 0;
      /* a straight line with flat ends paints no line past its ends: a waterline drawn edge to edge is inside */
      var butt = cs.strokeLinecap === "butt", hx = h, hy = h;
      if (butt && bb.width < 0.5) { hy = 0; }
      if (butt && bb.height < 0.5) { hx = 0; }
      [[bb.x, bb.y], [bb.x + bb.width, bb.y], [bb.x, bb.y + bb.height], [bb.x + bb.width, bb.y + bb.height]].forEach(function (c) {
        var px = to.a * c[0] + to.c * c[1] + to.e, py = to.b * c[0] + to.d * c[1] + to.f;
        x0 = Math.min(x0, px - hx); y0 = Math.min(y0, py - hy); x1 = Math.max(x1, px + hx); y1 = Math.max(y1, py + hy);
      });
    });
    return x1 > x0 ? { x: x0, y: y0, width: x1 - x0, height: y1 - y0 } : null;
  }

  function fit(svg) {
    if (svg.ownerSVGElement || svg.getAttribute("data-fit") === "off" || !svg.viewBox || !svg.viewBox.baseVal) { return; }
    var vb = svg.viewBox.baseVal;
    if (!vb.width || !vb.height) { return; }
    var cs = w.getComputedStyle(svg);
    if (cs.display === "none") { return; }
    var b = extent(svg);
    if (!b) { return; }
    var orig = svg.getAttribute("data-fit-orig");
    if (!orig) { orig = vb.x + " " + vb.y + " " + vb.width + " " + vb.height; }
    var o = orig.split(/[\s,]+/).map(parseFloat);
    var m = Math.max(3, MARGIN * Math.max(o[2], o[3])), p = 0.25;
    /* room is added only on the side that overflows - the other sides keep the drawing's own frame */
    var x0 = b.x < o[0] - p ? b.x - m : o[0], y0 = b.y < o[1] - p ? b.y - m : o[1];
    var x1 = b.x + b.width > o[0] + o[2] + p ? b.x + b.width + m : o[0] + o[2];
    var y1 = b.y + b.height > o[1] + o[3] + p ? b.y + b.height + m : o[1] + o[3];
    /* everything painted is inside the original frame (a background drawn edge to edge is fine): keep it */
    if (b.x >= o[0] - p && b.y >= o[1] - p && b.x + b.width <= o[0] + o[2] + p && b.y + b.height <= o[1] + o[3] + p) {
      if (svg.getAttribute("data-fit-orig")) { svg.setAttribute("viewBox", orig); }
      return;
    }
    svg.setAttribute("data-fit-orig", orig);
    svg.setAttribute("viewBox", [x0, y0, x1 - x0, y1 - y0].map(function (v) { return Math.round(v * 10) / 10; }).join(" "));
    if (w.console && console.warn) {
      console.warn("gb_fit: a drawing reached past its frame and the frame was widened - fix the drawing: " +
                   (svg.id ? "#" + svg.id : (svg.getAttribute("class") || "svg")) + " " + orig + " -> " + svg.getAttribute("viewBox"));
    }
  }
  function fitIn(root) {
    Array.prototype.forEach.call((root || d).querySelectorAll("svg[viewBox]"), fit);
  }
  var queued = false;
  function soon(root) {
    if (queued) { return; }
    queued = true;
    /* the next frame - or a short timer, whichever comes first: a browser pauses frames on a hidden page,
       and the fit must still happen. Called through window: a bare requestAnimationFrame throws. */
    var done = false;
    function run() {
      if (done) { return; }
      done = true;
      queued = false;
      var active = d.querySelector(".slide.active");
      fitIn(active || d);
    }
    if (w.requestAnimationFrame) { w.requestAnimationFrame(run); }
    w.setTimeout(run, 60);
  }

  function start() {
    var slides = d.querySelectorAll(".slide");
    if (!slides.length) { fitIn(d); return; }
    if (!w.MutationObserver) { return; }
    new MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var t = list[i].target;
        if (t.classList && (t.classList.contains("active") || (t.closest && t.closest(".slide.active")))) { soon(); return; }
      }
    }).observe(d.body, { attributes: true, subtree: true, attributeFilter: ["class", "data-step", "hidden", "style"] });
    w.addEventListener("resize", function () { soon(); });
    soon();
  }
  if (d.readyState === "loading") { d.addEventListener("DOMContentLoaded", start); } else { start(); }
  w.GBFit = { fit: fit, fitIn: fitIn };
})(window, document);
