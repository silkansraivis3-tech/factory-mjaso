/* ==========================================================================
   gb_zoom.js — every picture opens full screen, and closes again
   Owner, 2026-10-15 (L51): "all images, every picture, illustration,
   explanatory image ... can be clicked and be full screened, and later you can
   close it as well".

   ONE FILE FOR EVERY PAGE. The presentation, every task page, the module check
   and the handout load it; nothing is wired per picture. It starts by itself.

   WHAT OPENS
     every <img>, and every inline <svg> drawing, that is at least 64 px on the
     screen. Not: icons inside buttons and links, the logo, the landing card,
     the overview grid, video and 3D (<canvas> - they have their own controls),
     anything inside [data-no-zoom], anything inside [data-motion] (a figure
     that is driven step by step).

   HOW IT OPENS
     * an ordinary picture: tap the picture itself;
     * a picture the trainee ANSWERS ON (its frame holds [data-key] answer
       elements - tap-the-place, label-the-drawing): a tap must stay the answer,
       so the picture gets a round ⤢ button in its corner instead;
       data-zoom="button" on a frame asks for the same;
     * a closed card (.cmp-card that is not .zoom): the first tap opens the card,
       only the open card's picture goes full screen (course-task-ux §8).

   HOW IT CLOSES - every way a person tries first
     the X (56 px) · a tap on the dark around the picture · Esc · swipe down ·
     Back on the tablet (history) · the deck moving to another slide.
     ArrowLeft / ArrowRight close it AND turn the slide, so the instructor's
     Next on the panel is never blocked by an open picture.

   LOOKING CLOSER
     pinch, double-tap, or the + and − buttons (never a gesture as the only way,
     L42); drag to move a zoomed picture.

   ES5. No dependencies. Safe on an old Android WebView.
   ========================================================================== */
var GBZoom = (function (w, d) {
  "use strict";

  var MIN = 64;
  var NEVER = "button,a,label,input,select,textarea,#landing,#overview,#chrome,.cbtn,.ov-item," +
              ".brand-chip,.logo,[data-no-zoom],[data-motion],.gbz";
  var L = {
    en: { close: "Close", zin: "Zoom in", zout: "Zoom out", open: "Show the picture full screen" },
    lv: { close: "Aizvērt", zin: "Tuvināt", zout: "Attālināt", open: "Rādīt attēlu pa visu ekrānu" },
    ru: { close: "Закрыть", zin: "Приблизить", zout: "Отдалить", open: "Показать на весь экран" }
  };
  var T = L[(d.documentElement.getAttribute("lang") || "en").slice(0, 2).toLowerCase()] || L.en;

  var box = null, stage = null, media = null, cap = null, lastFocus = null, watch = null;
  var scale = 1, px = 0, py = 0, pushed = false, ownBack = false;

  function closest(el, sel) {
    while (el && el.nodeType === 1) {
      if ((el.matches || el.msMatchesSelector || el.webkitMatchesSelector).call(el, sel)) { return el; }
      el = el.parentNode;
    }
    return null;
  }

  /* the picture a tap landed on - the outermost <svg>, or the <img> */
  function pictureOf(t) {
    if (!t || t.nodeType !== 1) { return null; }
    var svg = closest(t, "svg"), outer = svg;
    while (svg) { outer = svg; svg = svg.parentNode && closest(svg.parentNode, "svg"); }
    if (outer) { return outer; }
    return t.tagName === "IMG" ? t : null;
  }

  function big(el) {
    var r = el.getBoundingClientRect();
    return r.width >= MIN && r.height >= MIN;
  }

  /* the frame around a picture: the nearest figure, card or parent */
  function frameOf(pic) {
    return closest(pic.parentNode, "figure,.fig,.fill,.stage,.cmp-card,.photo-frame,[data-zoom]") || pic.parentNode;
  }

  /* answered on = answer elements sit ON the picture: inside the drawing, or laid
     over it (absolutely placed hotspots and labels). Options beside a picture
     do not count - that picture still opens with a tap. */
  function answeredOn(pic) {
    var z = closest(pic, "[data-zoom]");
    if (z && z.getAttribute("data-zoom") === "button") { return true; }
    if (pic.querySelector && pic.querySelector("[data-key],[data-zone],[data-hotspot]")) { return true; }
    var f = frameOf(pic), keys, i, pos;
    if (!f || !f.querySelectorAll) { return false; }
    keys = f.querySelectorAll("[data-key],[data-zone],[data-hotspot]");
    for (i = 0; i < keys.length; i++) {
      pos = w.getComputedStyle(keys[i]).position;
      if (pos === "absolute" || pos === "fixed") { return true; }
    }
    return false;
  }

  function eligible(pic) {
    if (!pic || closest(pic, NEVER) || closest(pic, "[data-key]")) { return false; }
    var card = closest(pic, ".cmp-card");
    if (card && !card.classList.contains("zoom")) { return false; }
    return big(pic);
  }

  /* ---- the viewer ------------------------------------------------------- */
  function btn(cls, label, svgPath) {
    var b = d.createElement("button");
    b.type = "button";
    b.className = "gbz-btn " + cls;
    b.setAttribute("aria-label", label);
    b.title = label;
    b.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + svgPath + '"/></svg>';
    return b;
  }

  function build() {
    box = d.createElement("div");
    box.className = "gbz";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.hidden = true;
    stage = d.createElement("div");
    stage.className = "gbz-stage";
    cap = d.createElement("p");
    cap.className = "gbz-cap";
    var close = btn("gbz-close", T.close, "M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12z");
    var zin = btn("gbz-in", T.zin, "M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6z");
    var zout = btn("gbz-out", T.zout, "M19 13H5v-2h14z");
    var tools = d.createElement("div");
    tools.className = "gbz-tools";
    tools.appendChild(zout); tools.appendChild(zin);
    box.appendChild(stage); box.appendChild(cap); box.appendChild(tools); box.appendChild(close);
    d.body.appendChild(box);

    close.addEventListener("click", function (e) { e.stopPropagation(); hide(); });
    zin.addEventListener("click", function (e) { e.stopPropagation(); zoomTo(scale * 1.6); });
    zout.addEventListener("click", function (e) { e.stopPropagation(); zoomTo(scale / 1.6); });
    box.addEventListener("click", function (e) {
      if (e.target === box || e.target === stage) { hide(); }
    });
    gestures();
  }

  function apply() {
    if (media) { media.style.transform = "translate(" + px + "px," + py + "px) scale(" + scale + ")"; }
    box.classList.toggle("gbz-zoomed", scale > 1.01);
  }
  function zoomTo(s) {
    scale = Math.max(1, Math.min(5, s));
    if (scale === 1) { px = 0; py = 0; }
    apply();
  }

  function captionOf(pic) {
    var f = closest(pic, "figure");
    var fc = f && f.querySelector("figcaption");
    if (fc) { return fc.textContent; }
    var s = pic.getAttribute("alt") || pic.getAttribute("aria-label") || "";
    var t = pic.querySelector && pic.querySelector("title");
    return s || (t ? t.textContent : "");
  }

  function show(pic) {
    if (!box) { build(); }
    stage.innerHTML = "";
    if (pic.tagName === "IMG") {
      media = d.createElement("img");
      media.src = pic.currentSrc || pic.src;
      media.alt = pic.alt || "";
    } else {
      media = pic.cloneNode(true);
      if (!media.getAttribute("viewBox")) {
        var r = pic.getBoundingClientRect();
        media.setAttribute("viewBox", "0 0 " + Math.round(r.width) + " " + Math.round(r.height));
      }
      media.removeAttribute("width"); media.removeAttribute("height");
      media.removeAttribute("style"); media.removeAttribute("class");
      var bg = w.getComputedStyle(frameOf(pic) || pic).backgroundColor;
      media.style.background = (bg && bg !== "rgba(0, 0, 0, 0)" && bg !== "transparent") ? bg : "var(--gbz-paper, #FFFFFF)";
    }
    media.setAttribute("class", "gbz-media");          /* an <svg> has a read-only className */
    media.setAttribute("draggable", "false");
    stage.appendChild(media);
    var c = captionOf(pic);
    cap.textContent = c;
    cap.hidden = !c;
    scale = 1; px = 0; py = 0; apply();
    lastFocus = d.activeElement;
    box.hidden = false;
    d.documentElement.classList.add("gbz-open");
    fit();
    setTimeout(function () { box.classList.add("on"); box.querySelector(".gbz-close").focus(); }, 10);
    if (w.history && w.history.pushState) {
      try { w.history.pushState({ gbz: 1 }, ""); pushed = true; } catch (e) { pushed = false; }
    }
    watchSlides();
  }

  function hide(fromHistory) {
    if (!box || box.hidden) { return; }
    box.classList.remove("on");
    box.hidden = true;
    stage.innerHTML = "";
    media = null;
    d.documentElement.classList.remove("gbz-open");
    if (watch) { watch.disconnect(); watch = null; }
    if (pushed && !fromHistory) { pushed = false; ownBack = true; try { w.history.back(); } catch (e) { ownBack = false; } }
    pushed = false;
    if (lastFocus && lastFocus.focus) { try { lastFocus.focus(); } catch (e) {} }
  }

  /* an inline drawing has no size of its own - give it the largest that fits */
  function fit() {
    if (!media || media.tagName.toLowerCase() !== "svg") { return; }
    var vb = (media.getAttribute("viewBox") || "").split(/[\s,]+/), vw = +vb[2], vh = +vb[3];
    var sw = stage.clientWidth, sh = stage.clientHeight, k;
    if (!(vw > 0 && vh > 0 && sw > 0 && sh > 0)) { return; }
    k = Math.min(sw / vw, sh / vh);
    media.style.width = Math.floor(vw * k) + "px";
    media.style.height = Math.floor(vh * k) + "px";
  }

  /* the deck moved on (the panel, a hook, the overview) - the picture goes */
  function watchSlides() {
    var on = d.querySelector(".slide.active");
    if (!w.MutationObserver || !on) { return; }
    var slides = d.querySelectorAll(".slide");
    watch = new w.MutationObserver(function () { if (!on.classList.contains("active")) { hide(); } });
    for (var i = 0; i < slides.length; i++) {
      watch.observe(slides[i], { attributes: true, attributeFilter: ["class"] });
    }
  }

  /* ---- pinch, double-tap, drag, swipe down -------------------------------- */
  function gestures() {
    var start = null, pinch = null, lastTap = 0;
    function dist(t) { var x = t[0].clientX - t[1].clientX, y = t[0].clientY - t[1].clientY; return Math.sqrt(x * x + y * y); }
    box.addEventListener("touchstart", function (e) {
      e.stopPropagation();                              /* never a swipe for the deck */
      if (e.touches.length === 2) { pinch = { d: dist(e.touches), s: scale }; start = null; return; }
      var t = e.touches[0];
      start = { x: t.clientX, y: t.clientY, px: px, py: py, t: Date.now() };
    }, { passive: true });
    box.addEventListener("touchmove", function (e) {
      e.stopPropagation();
      if (pinch && e.touches.length === 2) { zoomTo(pinch.s * dist(e.touches) / pinch.d); e.preventDefault(); return; }
      if (start && scale > 1) {
        var t = e.touches[0];
        px = start.px + (t.clientX - start.x); py = start.py + (t.clientY - start.y);
        apply(); e.preventDefault();
      }
    }, { passive: false });
    box.addEventListener("touchend", function (e) {
      e.stopPropagation();
      if (pinch) { if (e.touches.length < 2) { pinch = null; } return; }
      if (!start) { return; }
      var t = e.changedTouches[0], dx = t.clientX - start.x, dy = t.clientY - start.y;
      if (scale === 1 && dy > 90 && Math.abs(dy) > 1.6 * Math.abs(dx)) { start = null; hide(); return; }
      if (Math.abs(dx) < 10 && Math.abs(dy) < 10 && closest(e.target, ".gbz-media")) {
        var now = Date.now();
        if (now - lastTap < 320) { zoomTo(scale > 1 ? 1 : 2.2); lastTap = 0; } else { lastTap = now; }
      }
      start = null;
    });
    box.addEventListener("dblclick", function (e) {
      if (closest(e.target, ".gbz-media")) { zoomTo(scale > 1 ? 1 : 2.2); }
    });
    box.addEventListener("wheel", function (e) {
      e.preventDefault();
      zoomTo(scale * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
    }, { passive: false });
    var drag = null;
    box.addEventListener("mousedown", function (e) {
      if (scale > 1 && closest(e.target, ".gbz-media")) { drag = { x: e.clientX, y: e.clientY, px: px, py: py }; e.preventDefault(); }
    });
    d.addEventListener("mousemove", function (e) {
      if (drag) { px = drag.px + e.clientX - drag.x; py = drag.py + e.clientY - drag.y; apply(); }
    });
    d.addEventListener("mouseup", function () { drag = null; });
  }

  /* ---- the ⤢ corner button, for pictures the trainee answers on ----------- */
  function corner(pic) {
    var f = frameOf(pic);
    if (!f || f.querySelector(".gbz-corner")) { return; }
    if (w.getComputedStyle(f).position === "static") { f.style.position = "relative"; }
    var b = btn("gbz-corner", T.open, "M5 5h6v2H8.4l3.3 3.3-1.4 1.4L7 8.4V11H5zm14 14h-6v-2h2.6l-3.3-3.3 1.4-1.4 3.3 3.3V13h2z");
    b.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); show(pic); });
    b.addEventListener("pointerdown", function (e) { e.stopPropagation(); });
    b.addEventListener("touchstart", function (e) { e.stopPropagation(); }, { passive: true });
    f.appendChild(b);
  }

  function scan() {
    var all = d.querySelectorAll("img,svg"), i, p;
    for (i = 0; i < all.length; i++) {
      p = pictureOf(all[i]);
      if (p !== all[i] || closest(p, NEVER) || closest(p, "[data-key]")) { continue; }
      if (answeredOn(p)) { corner(p); p.classList.add("gbz-answer"); }
      else { p.classList.add("gbz-can"); }
    }
  }

  /* ---- start ------------------------------------------------------------- */
  function onTap(e) {
    if (box && !box.hidden) { return; }
    var p = pictureOf(e.target);
    if (!p || answeredOn(p) || !eligible(p)) { return; }
    e.preventDefault();
    e.stopPropagation();
    show(p);
  }

  function init() {
    if (w.GB_ZOOM === false || d.documentElement.getAttribute("data-zoom") === "off") { return; }
    d.addEventListener("click", onTap, false);
    /* capture, so Esc and the arrows reach the viewer before the deck */
    d.addEventListener("keydown", function (e) {
      if (!box || box.hidden) { return; }
      var k = e.key || ({ 27: "Escape", 37: "ArrowLeft", 39: "ArrowRight" })[e.keyCode] || "";
      if (k === "Escape" || k === "Esc") { e.preventDefault(); e.stopPropagation(); hide(); return; }
      if (k === "+" || k === "=") { e.preventDefault(); e.stopPropagation(); zoomTo(scale * 1.6); return; }
      if (k === "-") { e.preventDefault(); e.stopPropagation(); zoomTo(scale / 1.6); return; }
      if (k === "Tab") { e.preventDefault(); return; }
      if (k === "ArrowLeft" || k === "ArrowRight" || k === "Left" || k === "Right" ||
          k === " " || k === "PageDown" || k === "PageUp") { hide(); }   /* and the deck turns the slide */
    }, true);
    w.addEventListener("resize", fit);
    w.addEventListener("popstate", function () {
      if (ownBack) { ownBack = false; return; }          /* our own step back after a close */
      if (box && !box.hidden) { pushed = false; hide(true); }   /* Back on the tablet */
    });
    scan();
    w.addEventListener("load", scan);
    if (w.MutationObserver) {
      var t = null;
      new w.MutationObserver(function () { clearTimeout(t); t = setTimeout(scan, 250); })
        .observe(d.body, { childList: true, subtree: true });
    }
  }

  if (d.readyState === "loading") { d.addEventListener("DOMContentLoaded", init); } else { init(); }

  return { open: show, close: hide, scan: scan };
})(window, document);
