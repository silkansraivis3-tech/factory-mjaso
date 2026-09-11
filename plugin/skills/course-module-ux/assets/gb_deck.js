/* ==========================================================================
   gb_deck.js — the canonical NOVIKONTAS module engine
   Extracted from GAS BASIC Module_01 on 2026-09-11 and generalised.

   Open the page, press Start, press Next to the end. That is the whole model.

   PAIRS WITH  course-module-ui/templates/gb_shell.css   (the look)
               course-module-ui/templates/gb_shell.html  (the markup skeleton)

   WHAT IT OWNS
     start / exit · next / prev · progress · counter · block tag · footer
     overview grid · instructor cue · fullscreen · keyboard · swipe · idle chrome
     per-screen enter/leave hooks for figures

   THE RULE THAT COST A PILOT
     A tablet has no keyboard. Every navigation path must exist as a TAP.
     This engine refuses to start silently if its controls are missing - it
     writes a visible banner instead, because a module that cannot be advanced
     in front of a class is worse than one that says so.
     course-module-ux/measure/scripts/check_navigation.py catches it earlier.

   ES5. No dependencies. Safe on an old Android WebView.
   ========================================================================== */
var GBDeck = (function (w, d) {
  "use strict";

  function el(id) { return d.getElementById(id); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  function init(opts) {
    opts = opts || {};
    var TXT = opts.text || {};
    var T = {
      cue: TXT.cue || "Instructor cue",
      noCue: TXT.noCue || "No cue for this screen.",
      start: TXT.start || "Start",
      screen: TXT.screen || "Screen",
      of: TXT.of || "of",
      missing: TXT.missing ||
        "Navigation controls are missing from this page. Add the chrome block from " +
        "gb_shell.html before delivering this module."
    };

    var slides = Array.prototype.slice.call(d.querySelectorAll(".slide"));
    if (!slides.length) { return null; }

    var landing = el("landing"), progress = el("progress"), counter = el("counter");
    var chrome = el("chrome"), cue = el("cue"), overview = el("overview");
    var blockTag = el("blockTag");
    var btnNext = el("btnNext"), btnPrev = el("btnPrev");
    var cur = 0, started = false, cueOn = false;

    /* ---- the contract check, loud on purpose ---------------------------- */
    if (slides.length > 1 && (!btnNext || !btnPrev)) {
      var warn = d.createElement("div");
      warn.setAttribute("data-gbdeck-error", "no-touch-nav");
      warn.style.cssText = "position:fixed;left:0;right:0;bottom:0;z-index:99;" +
        "background:#B4453A;color:#fff;padding:14px 18px;font:700 15px/1.4 sans-serif";
      warn.textContent = T.missing;
      d.body.appendChild(warn);
    }

    var HOOKS = opts.hooks || {};     /* slide id -> {enter, leave} */

    function show(idx) {
      idx = Math.max(0, Math.min(slides.length - 1, idx));
      var prevSlide = slides[cur];
      if (prevSlide && prevSlide.id && HOOKS[prevSlide.id] && HOOKS[prevSlide.id].leave) {
        HOOKS[prevSlide.id].leave();
      }
      each(slides, function (s, i) {
        if (i === idx) { s.classList.add("active"); } else { s.classList.remove("active"); }
      });
      cur = idx;
      var s = slides[idx];
      if (counter) { counter.innerHTML = "<b>" + (idx + 1) + "</b> / " + slides.length; }
      if (progress) { progress.style.width = (100 * (idx + 1) / slides.length) + "%"; }
      if (blockTag) { blockTag.textContent = s.getAttribute("data-block") || ""; }
      if (s.classList.contains("dark") || s.classList.contains("photo")) {
        d.body.classList.add("dark-active");
      } else {
        d.body.classList.remove("dark-active");
      }
      if (cue) {
        cue.innerHTML = '<span class="tag">' + T.cue + "</span>" +
          (s.getAttribute("data-cue") || T.noCue);
      }
      if (btnPrev) { btnPrev.disabled = (idx === 0); }
      if (btnNext) { btnNext.disabled = (idx === slides.length - 1); }
      if (s.id && HOOKS[s.id] && HOOKS[s.id].enter) { HOOKS[s.id].enter(); }
      markOverview();
      s.scrollTop = 0;
    }

    function next() { if (cur < slides.length - 1) { show(cur + 1); } }
    function prev() { if (cur > 0) { show(cur - 1); } }

    /* ---- start / exit --------------------------------------------------- */
    function start() {
      started = true;
      if (landing) { landing.classList.add("gone"); }
      show(0);
      requestFull();
    }
    function exitPresentation() {
      started = false;
      if (d.fullscreenElement && d.exitFullscreen) { d.exitFullscreen()["catch"](function () {}); }
      if (overview) { overview.classList.remove("on"); }
      if (landing) { landing.classList.remove("gone"); }
    }
    var startBtn = el("startBtn");
    if (startBtn) { startBtn.addEventListener("click", start); }
    var btnExit = el("btnExit");
    if (btnExit) { btnExit.addEventListener("click", exitPresentation); }

    /* ---- fullscreen ----------------------------------------------------- */
    function requestFull() {
      var root = d.documentElement;
      var rq = root.requestFullscreen || root.webkitRequestFullscreen || root.msRequestFullscreen;
      if (d.fullscreenElement || !rq) { return; }
      try {
        var pr = rq.call(root);
        if (pr && typeof pr["catch"] === "function") { pr["catch"](function () {}); }
      } catch (e) {}
    }
    function toggleFull() {
      if (d.fullscreenElement) {
        if (d.exitFullscreen) { d.exitFullscreen()["catch"](function () {}); }
      } else { requestFull(); }
    }
    var btnFull = el("btnFull");
    if (btnFull) { btnFull.addEventListener("click", toggleFull); }

    /* ---- overview grid --------------------------------------------------- */
    var ovGrid = el("ovGrid");
    if (ovGrid && !ovGrid.children.length) {
      each(slides, function (s, i) {
        var b = d.createElement("button");
        b.type = "button";
        b.className = "ov-item";
        b.innerHTML =
          '<span class="n">' + (i + 1) + "</span>" +
          '<span class="t">' + (s.getAttribute("data-title") || (T.screen + " " + (i + 1))) + "</span>" +
          '<span class="k">' + (s.getAttribute("data-kind") || "") + "</span>";
        b.addEventListener("click", function () {
          if (overview) { overview.classList.remove("on"); }
          show(i);
        });
        ovGrid.appendChild(b);
      });
    }
    function markOverview() {
      if (!ovGrid) { return; }
      each(ovGrid.children, function (c, i) {
        if (i === cur) { c.classList.add("cur"); } else { c.classList.remove("cur"); }
      });
    }
    function toggleOverview() {
      if (!started || !overview) { return; }
      overview.classList.toggle("on");
      markOverview();
    }
    var btnGrid = el("btnGrid");
    if (btnGrid) { btnGrid.addEventListener("click", toggleOverview); }
    var ovClose = el("ovClose");
    if (ovClose) { ovClose.addEventListener("click", toggleOverview); }

    /* ---- instructor cue --------------------------------------------------- */
    function toggleCue() {
      if (!cue) { return; }
      cueOn = !cueOn;
      if (cueOn) { cue.classList.add("on"); } else { cue.classList.remove("on"); }
    }
    var btnCue = el("btnCue");
    if (btnCue) { btnCue.addEventListener("click", toggleCue); }

    /* ---- keyboard, with keyCode fallback for old WebViews ----------------- */
    var KC = { 39: "ArrowRight", 37: "ArrowLeft", 32: " ", 34: "PageDown", 33: "PageUp",
               70: "f", 36: "Home", 35: "End", 13: "Enter", 71: "g", 78: "n", 27: "Escape" };
    d.addEventListener("keydown", function (e) {
      var k = e.key || KC[e.keyCode] || "";
      if (!started) {
        if (k === "Enter" || k === " ") { e.preventDefault(); start(); }
        return;
      }
      if (overview && overview.classList.contains("on")) {
        if (k === "g" || k === "G" || k === "Escape") { e.preventDefault(); toggleOverview(); }
        return;
      }
      switch (k) {
        case "ArrowRight": case "Right": case " ": case "PageDown":
          e.preventDefault(); next(); break;
        case "ArrowLeft": case "Left": case "PageUp":
          e.preventDefault(); prev(); break;
        case "f": case "F": toggleFull(); break;
        case "g": case "G": e.preventDefault(); toggleOverview(); break;
        case "n": case "N": e.preventDefault(); toggleCue(); break;
        case "Home": show(0); break;
        case "End": show(slides.length - 1); break;
      }
    });

    if (btnNext) { btnNext.addEventListener("click", next); }
    if (btnPrev) { btnPrev.addEventListener("click", prev); }

    /* ---- touch: horizontal swipe, guarded --------------------------------
       Guarded so a swipe inside an interactive figure does not turn the page. */
    var tx = null, ty = null;
    var GUARD = "input,textarea,select,button,a,.cbtn,.ov-item,[data-motion],svg";
    d.addEventListener("touchstart", function (e) {
      if (!started || e.touches.length !== 1) { tx = null; return; }
      var t = e.target;
      if (t && t.closest && t.closest(GUARD)) { tx = null; return; }
      tx = e.touches[0].clientX; ty = e.touches[0].clientY;
    }, { passive: true });
    d.addEventListener("touchend", function (e) {
      if (tx === null || !started) { return; }
      var dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
      if (Math.abs(dx) > 60 && Math.abs(dx) > 1.6 * Math.abs(dy)) {
        if (dx < 0) { next(); } else { prev(); }
      }
      tx = null;
    }, { passive: true });

    /* ---- idle chrome ------------------------------------------------------
       Fades, never hides, never stops accepting taps. A tablet user cannot
       "move the mouse" to bring it back. */
    var idle = null;
    function poke() {
      if (!chrome) { return; }
      chrome.classList.remove("idle");
      if (blockTag) { blockTag.classList.remove("idle"); }
      clearTimeout(idle);
      idle = setTimeout(function () {
        chrome.classList.add("idle");
        if (blockTag) { blockTag.classList.add("idle"); }
      }, 4200);
    }
    each(["mousemove", "touchstart", "keydown", "click"], function (ev) {
      d.addEventListener(ev, poke, { passive: true });
    });
    poke();

    return {
      show: show, next: next, prev: prev, start: start, exit: exitPresentation,
      toggleCue: toggleCue, toggleOverview: toggleOverview,
      count: slides.length,
      current: function () { return cur; },
      started: function () { return started; }
    };
  }

  return { init: init };
})(window, document);
