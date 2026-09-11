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

  return { run: run, discover: discover, errors: errors, listen: listen };
})(window, document);
