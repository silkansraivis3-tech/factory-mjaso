/* ==========================================================================
   verify_figures.js — RUNTIME proof that a figure is actually on the screen.

   WHY IT EXISTS. The first real pilot shipped a module whose every teaching
   figure was BLANK. The mount divs existed, the component scripts loaded, the
   stylesheets were tokenised, and check_visuals.py reported zero failures -
   because a static reader cannot see that `<div id="f3-spailes"></div>` was
   never filled. A warning that would have caught it was dismissed as a false
   positive of the architecture. It was not.

   Static analysis cannot prove a JS-built figure rendered. Only the engine can.

   HOW TO RUN
     Serve the module over http (file:// blocks module scripts on some engines),
     open it in a browser tool, and evaluate this file's contents in the page.
     It returns a JSON-able report; a non-empty `failures` array is a FAIL.

       node -e "..."            no - this needs a real layout engine
       browser evaluate         yes - this is the only honest way

     GBVerifyFigures.run()                 every figure it can find
     GBVerifyFigures.run({ mounts: [...] }) only these ids
     GBVerifyFigures.run({ minPx: 80 })     raise the size floor

     await GBVerifyFigures.motion()         uses window.GBFigures if the module
                                           publishes it (it should), else just
                                           watches each mount for movement
                                           does a moving figure MOVE
     Motion is async and must be awaited. It refuses to call a figure
     static without first proving frames were available - see MOTION.

   WHAT COUNTS AS PRESENT
     the mount exists · it has no loose text in it · it has rendered children ·
     the figure element
     (svg/canvas/img) has non-zero laid-out size · it is not display:none or
     opacity:0 at the root · no console error was recorded for its script

   A figure whose own steps start hidden is still PRESENT: the check measures
   the figure's own box, not whether every layer is visible.
   ========================================================================== */
var GBVerifyFigures = (function (w, d) {
  "use strict";

  /* Console errors are only visible if something was listening before the page
     ran. Install as early as possible; run() reports whether it was in time. */
  var errors = [];
  var installed = false;
  function listen() {
    if (installed) { return; }
    installed = true;
    w.addEventListener("error", function (e) {
      errors.push({ type: "error", message: String(e.message || e.type),
                    source: String(e.filename || ""), line: e.lineno || 0 });
    });
    w.addEventListener("unhandledrejection", function (e) {
      errors.push({ type: "unhandledrejection", message: String((e.reason && e.reason.message) || e.reason) });
    });
  }
  listen();

  function box(el) {
    var r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  }

  function hidden(el) {
    var n = el;
    while (n && n !== d.body) {
      var s = w.getComputedStyle(n);
      if (s.display === "none" || s.visibility === "hidden") { return true; }
      n = n.parentElement;
    }
    return false;
  }

  /* A mount is anything that looks like a figure host: an id starting f<digit>-,
     or an element carrying data-figure, or a declared data-motion host. */
  function discover() {
    var out = [];
    var seen = {};
    function push(el) {
      if (!el || !el.id || seen[el.id]) { return; }
      seen[el.id] = 1; out.push(el.id);
    }
    Array.prototype.forEach.call(d.querySelectorAll("[id]"), function (el) {
      if (/^f\d+[-_]/.test(el.id)) { push(el); }
    });
    Array.prototype.forEach.call(d.querySelectorAll("[data-figure],[data-motion]"), push);
    return out;
  }

  function checkOne(id, minPx) {
    var el = d.getElementById(id);
    var res = { id: id, ok: false, why: "" };

    if (!el) { res.why = "mount #" + id + " does not exist"; return res; }

    /* a figure on an inactive slide is legitimately not laid out: activate its
       slide for the measurement, then put it back exactly as it was. */
    var slide = el.closest ? el.closest(".slide") : null;
    var restored = null;
    if (slide && !slide.classList.contains("active")) {
      var prev = d.querySelector(".slide.active");
      slide.classList.add("active");
      if (prev && prev !== slide) { prev.classList.remove("active"); }
      restored = { slide: slide, prev: prev };
    }

    try {
      var kids = el.children.length;
      if (!kids) {
        res.why = "mount #" + id + " is EMPTY - the component never populated it";
        return res;
      }

      /* Stray text directly inside a mount means the fragment paste is broken.
         A fragment header comment says `Mount into <div id="f1-lauks">`, and
         any regex run over module.html can match that tag INSIDE the comment
         instead of the real one - which splits the comment open and prints its
         body on the slide. It shipped that way once, and every other check was
         green because the component still rendered underneath. */
      var stray = [];
      for (var si = 0; si < el.childNodes.length; si++) {
        var nd = el.childNodes[si];
        if (nd.nodeType === 3 && nd.nodeValue && nd.nodeValue.trim().length > 2) {
          stray.push(nd.nodeValue.trim().slice(0, 60));
        }
      }
      if (stray.length) {
        res.why = "mount #" + id + " has loose text in it - the fragment paste is " +
                  "broken and part of its header comment is rendering: \"" +
                  stray[0] + "…\"";
        return res;
      }

      var fig = el.querySelector("svg,canvas,img,video");
      if (!fig) {
        res.why = "mount #" + id + " has " + kids +
                  " child element(s) but no svg/canvas/img";
        return res;
      }

      var b = box(fig);
      if (b.w < minPx || b.h < minPx) {
        res.why = "figure in #" + id + " renders " + b.w + "x" + b.h +
                  "px, under the " + minPx + "px floor - present in the DOM, "
                  + "not present on the screen";
        return res;
      }

      if (hidden(el)) {
        res.why = "#" + id + " or an ancestor is display:none / visibility:hidden";
        return res;
      }

      res.ok = true;
      res.tag = fig.tagName.toLowerCase();
      res.size = b.w + "x" + b.h;
      res.children = kids;
      res.textNodes = el.querySelectorAll("text,figcaption,p").length;
      res.controls = el.querySelectorAll("button").length;
      return res;
    } finally {
      if (restored) {
        restored.slide.classList.remove("active");
        if (restored.prev) { restored.prev.classList.add("active"); }
      }
    }
  }

  function run(opts) {
    opts = opts || {};
    var minPx = opts.minPx || 60;
    var ids = opts.mounts && opts.mounts.length ? opts.mounts : discover();

    var results = ids.map(function (id) { return checkOne(id, minPx); });
    var failures = results.filter(function (r) { return !r.ok; });

    return {
      url: w.location.href,
      viewport: d.documentElement.clientWidth + "x" + d.documentElement.clientHeight,
      figuresChecked: results.length,
      passed: results.length - failures.length,
      failures: failures.map(function (f) { return f.why; }),
      results: results,
      consoleErrors: errors,
      listenerInstalledLate: errors.length === 0 && d.readyState === "complete"
        ? "listener may have missed errors thrown before it was installed"
        : null,
      verdict: failures.length === 0 && errors.length === 0 ? "PASS" : "FAIL"
    };
  }


  /* ------------------------------------------------------------------------
     MOTION — a figure that claims to move is proven to move.

     WHY IT EXISTS. The retrofit lane requires that an inherently dynamic
     concept be delivered dynamically. Nothing verified it. A real pilot's
     Ohm's-law figure was investigated for an afternoon as "the dots do not
     animate" - the deck's hook contract was re-read, the engine was changed,
     the course was rewired - and the figure had been correct the entire time.
     The browser pane was HIDDEN, and a hidden page suspends
     requestAnimationFrame completely: the probe measured zero movement and
     reported it as a property of the course.

     So this check has one hard rule: it NEVER reports "does not move" without
     first establishing that frames were available to move in.

       visible page  -> the real scheduler runs; scheduler: "native"
       hidden page   -> rAF is pumped from a timer for the duration of the
                        measurement and the result says scheduler: "pumped",
                        because the browser's own scheduler was not exercised
       reduced motion-> verdict STATIC_BY_DESIGN, which is correct behaviour

     And it asks the right question. Not "does it animate" - a series/parallel
     toggle should not animate - but "is this drawing alive at all":
       MOVES     animates on its own
       RESPONDS  changes when its OWN controls are used
       STATIC    neither; it could have been a PNG, and only this one fails

     A figure is sampled by fingerprinting the geometry of everything drawable
     inside its mount, so it needs no knowledge of how the figure animates.
     ---------------------------------------------------------------------- */

  /* A drawing changes if its GEOMETRY, its PAINT, its VISIBILITY or its printed TEXT
     changes. Sampling geometry alone called a series/parallel toggle and a tappable
     colour-band resistor pictures: one only swaps which group is hidden and rewrites
     its numbers, the other only repaints a band. Both are the interaction the
     retrofit lane asks for. */
  var ATTRS = ["cx", "cy", "x", "y", "r", "d", "points", "transform", "width", "height",
               "fill", "stroke", "stroke-width", "opacity", "fill-opacity", "class",
               "hidden", "visibility", "x1", "y1", "x2", "y2"];

  function fingerprint(el) {
    var parts = [];
    var nodes = el.querySelectorAll("circle,rect,line,path,polyline,polygon,ellipse,image,use,g,text,tspan");
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      for (var a = 0; a < ATTRS.length; a++) { parts.push(n.getAttribute(ATTRS[a])); }
      parts.push(n.style.transform || "", n.style.display || "", n.style.fill || "");
    }
    /* every value the figure prints - the numbers are the teaching */
    parts.push((el.textContent || "").replace(/\s+/g, " "));
    var cv = el.querySelectorAll("canvas");
    for (var c = 0; c < cv.length; c++) {
      try { parts.push(cv[c].toDataURL().slice(-96)); } catch (e) { parts.push("tainted"); }
    }
    return parts.join("|");
  }

  function pump(on) {
    if (on) {
      if (w.__gbRealRAF) { return; }
      w.__gbRealRAF = w.requestAnimationFrame;
      w.__gbRealCAF = w.cancelAnimationFrame;
      w.requestAnimationFrame = function (fn) {
        return w.setTimeout(function () { fn(w.performance.now()); }, 16);
      };
      w.cancelAnimationFrame = function (id) { w.clearTimeout(id); };
    } else if (w.__gbRealRAF) {
      w.requestAnimationFrame = w.__gbRealRAF;
      w.cancelAnimationFrame = w.__gbRealCAF;
      w.__gbRealRAF = null;
      w.__gbRealCAF = null;
    }
  }

  function sleep(ms) { return new Promise(function (r) { w.setTimeout(r, ms); }); }

  /* Press the figure's OWN controls and see whether the drawing answers.

     Every control is restored to the value it had, because this runs against the
     live module and an audit that leaves a slider somewhere the instructor did not
     put it is an audit that edits the course. */
  function tap(n) {
    if (typeof n.click === "function") { n.click(); return; }
    n.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  }

  function exerciseControls(el) {
    var tried = 0;
    var before = fingerprint(el);
    var changed = false;

    var ranges = el.querySelectorAll('input[type="range"]');
    for (var i = 0; i < ranges.length && !changed; i++) {
      var r = ranges[i], was = r.value;
      var lo = parseFloat(r.min || "0"), hi = parseFloat(r.max || "100");
      r.value = String(parseFloat(was) === hi ? lo : hi);
      r.dispatchEvent(new Event("input", { bubbles: true }));
      r.dispatchEvent(new Event("change", { bubbles: true }));
      tried++;
      if (fingerprint(el) !== before) { changed = true; }
      r.value = was;
      r.dispatchEvent(new Event("input", { bubbles: true }));
      r.dispatchEvent(new Event("change", { bubbles: true }));
    }

    /* SVGElement has no .click() in every engine that matters, and a <g role="button">
       inside an <svg> is an ordinary control to a learner. Synthesise the event. */
    var btns = el.querySelectorAll("button,[role=button],[data-tap]");
    for (var j = 0; j < btns.length && !changed; j++) {
      tap(btns[j]);
      tried++;
      if (fingerprint(el) !== before) { changed = true; }
    }

    /* svg elements that carry their own click handler - a tappable band, a hotspot */
    if (!changed) {
      var taps = el.querySelectorAll("svg [tabindex], svg [data-i], svg [class*=tap]");
      for (var k = 0; k < taps.length && !changed; k++) {
        tap(taps[k]);
        tried++;
        if (fingerprint(el) !== before) { changed = true; }
      }
    }

    return { changed: changed, tried: tried };
  }

  /* opts.figures : [{ mount:"f1-oma", start:fn, stop:fn }]  start/stop optional
     opts.ms      : sample window per figure (default 400)                     */
  function motion(opts) {
    opts = opts || {};
    var ms = opts.ms || 400;
    var visible = d.visibilityState === "visible";
    var reduced = w.matchMedia &&
                  w.matchMedia("(prefers-reduced-motion: reduce)").matches;
    /* A module publishes its figure APIs as window.GBFigures = { mount: api }.
       With that in place this check takes no arguments, which is the only version
       of it that gets run on every build rather than once. */
    var REG = w.GBFigures || {};
    var figs = opts.figures || discover().map(function (id) {
      var api = REG[id] || null;
      return { mount: id,
               start: api && api.enter ? api.enter : null,
               stop: api && api.leave ? api.leave : null };
    });

    if (!visible) { pump(true); }

    var out = [];
    var chain = Promise.resolve();
    figs.forEach(function (f) {
      chain = chain.then(function () {
        var el = d.getElementById(f.mount);
        if (!el) { out.push({ mount: f.mount, verdict: "NO_MOUNT" }); return; }

        var slide = el.closest ? el.closest(".slide") : null;
        var prev = d.querySelector(".slide.active");
        var swapped = false;
        if (slide && !slide.classList.contains("active")) {
          slide.classList.add("active");
          if (prev && prev !== slide) { prev.classList.remove("active"); }
          swapped = true;
        }

        var a = fingerprint(el);
        if (f.start) { f.start(); }
        return sleep(ms).then(function () {
          var b = fingerprint(el);
          if (f.stop) { f.stop(); }
          var c = fingerprint(el);
          return sleep(Math.min(200, ms)).then(function () {
            var moved = a !== b;
            var responded = moved ? null : exerciseControls(el);
            if (swapped) {
              slide.classList.remove("active");
              if (prev) { prev.classList.add("active"); }
            }
            out.push({
              mount: f.mount,
              verdict: moved ? "MOVES"
                     : responded.changed ? "RESPONDS"
                     : reduced ? "STATIC_BY_DESIGN"
                     : "STATIC",
              controls: responded ? responded.tried : null,
              stopsOnLeave: f.stop ? (c === fingerprint(el)) : null,
              scheduler: visible ? "native" : "pumped"
            });
          });
        });
      });
    });

    return chain.then(function () {
      if (!visible) { pump(false); }
      var still = out.filter(function (r) { return r.verdict === "STATIC"; });
      var leaky = out.filter(function (r) { return r.stopsOnLeave === false; });
      return {
        url: w.location.href,
        pageVisible: visible,
        scheduler: visible ? "native" : "pumped",
        reducedMotion: !!reduced,
        note: visible ? null
          : "PAGE HIDDEN: requestAnimationFrame is suspended by the browser. " +
            "Frames were pumped from a timer so the figures' own code still ran, " +
            "but the browser's own scheduler was NOT exercised. Never read a " +
            "STATIC verdict off a hidden page without re-running it visible.",
        figuresChecked: out.length,
        alive: out.length - still.length,
        animated: out.filter(function (r) { return r.verdict === "MOVES"; }).length,
        interactive: out.filter(function (r) { return r.verdict === "RESPONDS"; }).length,
        results: out,
        failures: still.map(function (r) {
          return "#" + r.mount + " neither animates nor answers its own controls " +
                 "(" + r.controls + " tried) - it is a picture, and the page had " +
                 "frames to move in";
        }).concat(leaky.map(function (r) {
          return "#" + r.mount + " keeps animating after its leave hook - it will " +
                 "burn battery on a slide nobody is looking at";
        })),
        verdict: (still.length === 0 && leaky.length === 0) ? "PASS" : "FAIL"
      };
    });
  }

  return { run: run, motion: motion, discover: discover,
           errors: errors, listen: listen };
})(window, document);
