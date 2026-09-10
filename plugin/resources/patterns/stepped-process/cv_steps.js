/* ==========================================================================
   cv_steps - the stepped process reveal

   The default shape of a TEACHING animation in this factory. Layers of a
   figure are revealed cumulatively, one caption per step saying what changed
   and why, under the instructor's control - play, pause, step, replay.

   It is instructor-paced on purpose. Nothing auto-advances past the point
   being made, and the resting state is readable with the motion stopped.

   Markup
     <figure class="cv-steps" data-motion="teaching" data-step-ms="3000">
       <svg viewBox="0 0 800 450" role="img"
            aria-label="What the whole figure shows">
         <g data-step="0"> ... always visible ... </g>
         <g data-step="1" opacity="0"> ... </g>
         <g data-step="2" opacity="0" data-op="0.85"> ... </g>
       </svg>
       <p class="cv-steps-cap" data-caps='[
            "Step one: what changes, and why.",
            "Step two: ..."]'></p>
       <div class="cv-steps-bar">
         <button data-cv="play">Play</button>
         <button data-cv="step">Step</button>
         <button data-cv="replay">Replay</button>
         <span class="cv-steps-dots"></span>
         <span class="cv-steps-n">0</span>
       </div>
     </figure>

   Contract
     - captions are the teaching; the motion carries the change between them
     - pauses when the figure is off screen (battery, and replay sync)
     - honours prefers-reduced-motion: no autoplay, stepping still works
     - every control is a 44px target (see cv_steps.css)

   ES5. No dependencies.
   ========================================================================== */
(function (w, d) {
  "use strict";

  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  var REDUCED = w.matchMedia &&
                w.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function build(fig) {
    var svg = fig.querySelector("svg");
    var capEl = fig.querySelector(".cv-steps-cap");
    var dotsEl = fig.querySelector(".cv-steps-dots");
    var numEl = fig.querySelector(".cv-steps-n");
    var playBtn = fig.querySelector('[data-cv="play"]');
    var stepBtn = fig.querySelector('[data-cv="step"]');
    var replayBtn = fig.querySelector('[data-cv="replay"]');
    if (!svg) { return null; }

    var caps = [];
    if (capEl && capEl.getAttribute("data-caps")) {
      try { caps = JSON.parse(capEl.getAttribute("data-caps")); }
      catch (e) { caps = []; }
    }

    var layers = svg.querySelectorAll("[data-step]");
    var max = 0;
    each(layers, function (el) {
      var n = parseInt(el.getAttribute("data-step"), 10) || 0;
      if (n > max) { max = n; }
    });
    var total = Math.max(max, caps.length ? caps.length - 1 : 0);

    var step = 0, timer = null, playing = false;
    var ms = parseInt(fig.getAttribute("data-step-ms"), 10) || 3000;

    if (dotsEl && !dotsEl.children.length) {
      for (var i = 0; i <= total; i++) { dotsEl.appendChild(d.createElement("i")); }
    }

    function apply() {
      each(layers, function (el) {
        var n = parseInt(el.getAttribute("data-step"), 10) || 0;
        var on = n <= step;
        el.style.opacity = on ? (el.getAttribute("data-op") || "1") : "0";
      });
      if (capEl && caps.length) { capEl.innerHTML = caps[Math.min(step, caps.length - 1)] || ""; }
      if (numEl) { numEl.textContent = (step + 1) + " / " + (total + 1); }
      if (dotsEl) {
        each(dotsEl.children, function (dot, j) {
          if (j <= step) { dot.className = "on"; } else { dot.className = ""; }
        });
      }
      setPlayLabel();
    }

    function setPlayLabel() {
      if (!playBtn) { return; }
      playBtn.textContent = playing ? "Pause"
                          : (step >= total ? "Play again" : "Play");
      playBtn.setAttribute("aria-pressed", playing ? "true" : "false");
    }

    function advance() {
      if (step >= total) { stop(); return; }
      step++; apply();
      if (step >= total) { stop(); }
    }

    function play() {
      if (step >= total) { step = 0; apply(); }
      playing = true;
      clearInterval(timer);
      timer = setInterval(advance, ms);
      advance();
    }

    function stop() { playing = false; clearInterval(timer); setPlayLabel(); }

    function reset() { stop(); step = 0; apply(); }

    if (playBtn) {
      playBtn.addEventListener("click", function () {
        if (playing) { stop(); } else { play(); }
      });
    }
    if (stepBtn) {
      stepBtn.addEventListener("click", function () { stop(); advance(); });
    }
    if (replayBtn) {
      replayBtn.addEventListener("click", function () {
        reset();
        if (!REDUCED) { play(); }
      });
    }

    apply();
    return { enter: function () {}, leave: stop, reset: reset, stop: stop };
  }

  var made = [];

  function init(scope) {
    each((scope || d).querySelectorAll(".cv-steps"), function (fig) {
      if (fig.getAttribute("data-cv-ready")) { return; }
      var api = build(fig);
      if (!api) { return; }
      fig.setAttribute("data-cv-ready", "1");
      made.push({ fig: fig, api: api });
    });

    /* stop anything that scrolls or slides out of view */
    if (w.IntersectionObserver) {
      var io = new IntersectionObserver(function (entries) {
        each(entries, function (e) {
          if (e.isIntersecting) { return; }
          for (var i = 0; i < made.length; i++) {
            if (made[i].fig === e.target) { made[i].api.stop(); }
          }
        });
      }, { threshold: 0.05 });
      each(made, function (m) { io.observe(m.fig); });
    }
  }

  if (d.readyState === "loading") {
    d.addEventListener("DOMContentLoaded", function () { init(d); });
  } else {
    init(d);
  }

  w.CVSteps = { init: init, all: made, reducedMotion: REDUCED };
})(window, document);
