/* Module runner — course-agnostic. Storage namespace is the `key` you pass; no course name appears in this file.
   One job: the instructor presses Next and lands where they need to be.

   Two modes, chosen automatically.

   RUNNER MODE — on START_HERE, where `steps` is passed. Renders ONE step at a
   time: a progress bar, the step's number and time, its title, ONE primary
   button that opens what this step needs, three short lines, and Back / Next.
   The current step is kept on the device, so a reload or a trip to another
   page comes back to the right place.

   BAR MODE — on every other page, where `steps` is omitted. Renders a fixed
   top bar: "Back to step N" and "Done - next step". "Done" advances the stored
   step and returns to the runner, so the instructor never has to work out
   where to go next.

   RETURN-TO-DECK. A page opened from a presentation must go back to the
   presentation, at the screen it was launched from - not to the runner. When
   a deck launches a task it writes the block code to "gbdeck:<key>"; the bar
   sees it, points both buttons at the deck's own anchor with that block, and
   clears the flag on the way out. One device projecting means the instructor
   never leaves the deck for longer than the task takes.

   Both routes are found through anchors in the markup - id="gb-home" for the
   runner, id="gb-deck" for the presentation. That is deliberate: the
   single-file build rewrites href attributes but not URLs held in JavaScript,
   so the links have to exist in the markup.

   Plain ES5. No dependencies. Nothing is sent anywhere. */
(function () {
  "use strict";

  var STORE_OK = (function () {
    try { localStorage.setItem("__gbr_", "1"); localStorage.removeItem("__gbr_"); return true; }
    catch (e) { return false; }
  })();

  function esc(s) {
    return String(s == null ? "" : s).replace(/[<>&"]/g, function (c) {
      return { "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c];
    });
  }
  function read(key, max) {
    if (!STORE_OK) return 0;
    var n = parseInt(localStorage.getItem("gbrun:" + key), 10);
    if (isNaN(n) || n < 0) n = 0;
    if (max != null && n > max) n = max;
    return n;
  }
  function write(key, n) {
    if (!STORE_OK) return;
    try { localStorage.setItem("gbrun:" + key, String(n)); } catch (e) {}
  }
  function homeHref() {
    var a = document.getElementById("gb-home");
    return a ? a.getAttribute("href") : null;
  }
  function deckHref() {
    var a = document.getElementById("gb-deck");
    return a ? a.getAttribute("href") : null;
  }
  /* ---- the trail ------------------------------------------------- *
     Where the instructor came from, so "back" means back. sessionStorage,
     not localStorage: a trail belongs to this sitting, not to the tablet. */
  function trailKey(k) { return "gbtrail:" + k; }

  function trailRead(k) {
    try { return JSON.parse(sessionStorage.getItem(trailKey(k)) || "[]") || []; }
    catch (e) { return []; }
  }

  function trailWrite(k, v) {
    try { sessionStorage.setItem(trailKey(k), JSON.stringify(v.slice(-6))); }
    catch (e) {}
  }

  function trailClear(k) {
    try { sessionStorage.removeItem(trailKey(k)); } catch (e) {}
  }

  function here() {
    return location.pathname.split("/").pop() + location.search + location.hash;
  }

  function markDone(key) {
    if (!STORE_OK) return;
    try { localStorage.setItem("gbdone:" + key, "1"); } catch (e) {}
  }
  function takeDone(key) {
    if (!STORE_OK) return false;
    try {
      var v = localStorage.getItem("gbdone:" + key);
      if (v) localStorage.removeItem("gbdone:" + key);
      return !!v;
    } catch (e) { return false; }
  }
  function launchedFromDeck(key) {
    if (!STORE_OK) return null;
    try { return localStorage.getItem("gbdeck:" + key) || null; } catch (e) { return null; }
  }

  /* ------------------------------------------------------------------ *
   * BAR MODE
   * ------------------------------------------------------------------ */
  /* Left button. If the instructor arrived here from another page in the
     module, back means THAT page - naming it, so the button says where it
     goes. Only with nothing behind them does it mean the step list. */
  function backBtn(opts, home) {
    var t = trailRead(opts.key);
    var prev = t.length ? t[t.length - 1] : null;
    if (prev && prev.h) {
      var lbl = prev.t || "the last page";
      if (lbl.length > 26) lbl = lbl.slice(0, 25) + "\u2026";
      return '<a class="gbrun-b back" href="' + esc(prev.h) + '" data-gbrun-back="1">' +
        '<span aria-hidden="true">\u25c0</span> ' + esc(lbl) + "</a>";
    }
    return '<a class="gbrun-b back" href="' + esc(home) + '#run">' +
      '<span aria-hidden="true">\u25c0</span> Steps</a>';
  }

  /* When back went somewhere else, the step list still needs a door - but
     only then. With an empty trail the back button already IS that door, and
     two identical buttons is exactly the noise this bar exists to avoid. */
  function stepsBtn(opts, home) {
    var t = trailRead(opts.key);
    if (!t.length || !t[t.length - 1].h) return "";
    return '<a class="gbrun-b steps" href="' + esc(home) + '#run">Steps</a>';
  }

  function bar(opts) {
    var block = launchedFromDeck(opts.key);
    var deck = block ? deckHref() : null;
    var home = opts.home || homeHref();
    if (!deck && !home) return;              /* no way back declared - draw nothing */

    var total = opts.total || 0;
    var i = read(opts.key, total ? total - 1 : null);
    var el = document.createElement("div");
    el.className = "gbrun-bar";

    if (deck) {
      /* Launched from the presentation: both buttons go back to it, at the
         screen it was launched from. The instructor is projecting; getting
         them back on the slide matters more than the runner's step count. */
      var to = esc(deck) + "#b=" + esc(block);
      el.innerHTML =
        '<a class="gbrun-b back" href="' + to + '" data-gbrun-deck="1">' +
          '<span aria-hidden="true">◀</span> Back to the presentation</a>' +
        '<span class="gbrun-where">' +
          esc(opts.label || document.title.split("—").pop().trim()) + "</span>" +
        '<a class="gbrun-b next" href="' + to + '" data-gbrun-deck="1">' +
          "Done — back to the presentation <span aria-hidden=\"true\">▶</span></a>";
    } else {
      /* THE CHAIN, AND ONLY THE CHAIN.
         A page advances the session only if it says where the session goes
         next (`next`) or that it is the end of it (`finish`). Every other
         page - the handout, the task list, the plan, a reference card - is
         somewhere the instructor went to look at something, and gets a way
         back and nothing else.

         This is not a style choice. When every page carried an advancing
         "Done - next step" button, opening three reference pages and tapping
         it on each left the stored step at 3, and the next "Start module"
         opened the last step of the module. */
      var nx = opts.next || null;
      var fin = opts.finish === true;
      var where = '<span class="gbrun-where">' +
        esc(opts.label || document.title.split("—").pop().trim()) + "</span>";

      if (!nx && !fin) {
        el.innerHTML =
          backBtn(opts, home) + where + stepsBtn(opts, home);
      } else {
        el.innerHTML =
          backBtn(opts, home) + where + stepsBtn(opts, home) +
          '<a class="gbrun-b next" href="' + esc(nx ? nx.href : (home + "#run")) +
            '" data-gbrun-next="1">' +
            (nx ? "Finish — next: " + esc(nx.label) : "Finish the module") +
            " <span aria-hidden=\"true\">▶</span></a>";
      }
    }
    document.body.insertBefore(el, document.body.firstChild);
    document.body.classList.add("has-gbrun-bar");

    /* Leaving by any in-module link? Remember this page, so the page being
       opened can offer a back button that names it. The bar's own buttons
       manage the trail themselves and are skipped. */
    document.addEventListener("click", function (e) {
      var a = e.target && e.target.closest ? e.target.closest("a[href]") : null;
      if (!a || a.closest(".gbrun-bar")) return;
      var h = a.getAttribute("href") || "";
      if (!h || h.charAt(0) === "#" || /^(https?:|mailto:|tel:|data:)/.test(h)) return;
      if (a.hasAttribute("download") || a.getAttribute("target") === "_blank") return;
      var t = trailRead(opts.key);
      var mine = here();
      if (t.length && t[t.length - 1].h === mine) return;      /* no duplicates */
      t.push({ h: mine, t: opts.label || document.title.split("\u2014").pop().trim() });
      trailWrite(opts.key, t);
    });

    el.addEventListener("click", function (e) {
      if (e.target.closest("[data-gbrun-deck]")) {
        try { localStorage.removeItem("gbdeck:" + opts.key); } catch (err) {}
        return;
      }
      /* going back consumes the step of the trail it used */
      if (e.target.closest("[data-gbrun-back]")) {
        var t = trailRead(opts.key);
        t.pop();
        trailWrite(opts.key, t);
        return;
      }
      /* the step list is the top of the module: nothing is behind it */
      if (e.target.closest(".gbrun-b.steps")) {
        trailClear(opts.key);
        return;
      }
      if (e.target.closest("[data-gbrun-next]")) {
        trailClear(opts.key);            /* forward in the chain is not a side trip */
        write(opts.key, i + 1);              /* the runner clamps to the last step */
        /* The index cannot go past the last step, so the last page in the
           chain raises a separate flag. Without it the closing card never
           fires and the module has no visible end. */
        if (opts.finish === true) markDone(opts.key);
      }
    });
  }

  /* ------------------------------------------------------------------ *
   * RUNNER MODE
   * ------------------------------------------------------------------ */
  function runner(opts) {
    var steps = opts.steps;
    var host = document.querySelector(opts.mount || "#gbrun");
    if (!host || !steps || !steps.length) return;
    var last = steps.length - 1;
    var i = read(opts.key, last);

    host.innerHTML =
      '<div class="gbrun">' +
        '<div class="gbrun-rail"><i id="gbrunBar"></i></div>' +
        '<div class="gbrun-card" id="gbrunCard"></div>' +
        '<div class="gbrun-nav">' +
          '<button type="button" class="gbrun-n" id="gbrunPrev">◀ Back</button>' +
          '<span class="gbrun-count" id="gbrunCount"></span>' +
          '<button type="button" class="gbrun-n go" id="gbrunNext">Next ▶</button>' +
        "</div>" +
        '<div class="gbrun-jump" id="gbrunJump"></div>' +
      "</div>";

    var card = document.getElementById("gbrunCard");
    var railBar = document.getElementById("gbrunBar");
    var count = document.getElementById("gbrunCount");
    var prev = document.getElementById("gbrunPrev");
    var next = document.getElementById("gbrunNext");
    var jump = document.getElementById("gbrunJump");

    jump.innerHTML = steps.map(function (s, k) {
      return '<button type="button" class="gbrun-dot" data-k="' + k + '" ' +
             'title="' + esc(s.n + " · " + s.title) + '">' + esc(s.n) + "</button>";
    }).join("");

    function draw() {
      var s = steps[i];
      write(opts.key, i);

      railBar.style.width = Math.round(100 * (i + 1) / steps.length) + "%";
      count.innerHTML = "Step <b>" + (i + 1) + "</b> of " + steps.length;
      prev.disabled = (i === 0);
      next.textContent = (i === last) ? "Finish ▶" : "Next ▶";

      var meta = [];
      if (s.day) meta.push('<span class="gbrun-day">' + esc(s.day) + "</span>");
      meta.push('<span class="gbrun-code">' + esc(s.n) + "</span>");
      if (s.mins) meta.push('<span class="gbrun-min">' + esc(s.mins) + " min</span>");
      if (s.tag) meta.push('<span class="gbrun-tag ' + esc(s.tagKind || "") + '">' +
                           esc(s.tag) + "</span>");

      var html =
        '<div class="gbrun-meta">' + meta.join("") + "</div>" +
        "<h2>" + esc(s.title) + "</h2>";

      if (s.open) {
        html += '<a class="gbrun-open' + (s.openKind ? " " + esc(s.openKind) : "") + '" href="' +
                esc(s.open.href) + '">' + esc(s.open.label) + "</a>";
      } else {
        html += '<div class="gbrun-noopen">' + esc(s.noOpen || "Nothing to open — " +
                "this one happens in the room.") + "</div>";
      }

      html += '<dl class="gbrun-facts">';
      if (s.they) html += "<dt>They do</dt><dd>" + s.they + "</dd>";
      if (s.done) html += '<dt class="fin">Finished when</dt><dd class="fin">' + s.done + "</dd>";
      if (s.watch) html += '<dt class="watch">Watch for</dt><dd class="watch">' + s.watch + "</dd>";
      html += "</dl>";

      /* Words the instructor says verbatim. They belong on the step that needs
         them, and they belong closed - the card has to stay a card. */
      if (s.say && s.say.items && s.say.items.length) {
        html += '<details class="gbrun-say"><summary>' +
          esc(s.say.title || "The words, verbatim") +
          ' <span class="n">' + s.say.items.length + '</span></summary><ol>' +
          s.say.items.map(function (x) { return "<li>" + x + "</li>"; }).join("") +
          "</ol></details>";
      }

      if (s.also && s.also.length) {
        html += '<div class="gbrun-also">' + s.also.map(function (a) {
          return '<a class="' + (a.kind || "") + '" href="' + esc(a.href) + '">' +
                 esc(a.label) + "</a>";
        }).join("") + "</div>";
      }
      card.innerHTML = html;

      Array.prototype.forEach.call(jump.children, function (b, k) {
        b.classList.toggle("on", k === i);
        b.classList.toggle("past", k < i);
      });
      if (location.hash.indexOf("#run") !== 0) return;
      history.replaceState(null, "", location.pathname + "#run=" + (i + 1));
    }

    function go(n) {
      i = Math.max(0, Math.min(last, n));
      draw();
      host.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    /* Arrived here from the last page of the chain: show where we ended and
       run the closing card, once. */
    if (takeDone(opts.key)) {
      i = last;
      draw();
      if (typeof opts.onFinish === "function") opts.onFinish();
    }

    prev.addEventListener("click", function () { go(i - 1); });
    next.addEventListener("click", function () {
      if (i === last && typeof opts.onFinish === "function") { opts.onFinish(); return; }
      go(i + 1);
    });
    jump.addEventListener("click", function (e) {
      var b = e.target.closest(".gbrun-dot");
      if (b) go(parseInt(b.getAttribute("data-k"), 10));
    });
    document.addEventListener("keydown", function (e) {
      if (host.offsetParent === null) return;                 /* runner not visible */
      if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
      var k = e.key || "";
      if (k === "ArrowRight" || e.keyCode === 39) { e.preventDefault(); go(i + 1); }
      if (k === "ArrowLeft" || e.keyCode === 37) { e.preventDefault(); go(i - 1); }
    });

    /* #run=4 jumps; plain #run resumes where the device left off */
    var m = /^#run=(\d+)$/.exec(location.hash || "");
    if (m) i = Math.max(0, Math.min(last, parseInt(m[1], 10) - 1));
    draw();

    window.GBRunGo = go;
  }

  /* Called by a presentation before it navigates to a task, so the task knows
     which screen to send the instructor back to. */
  /* ------------------------------------------------------------------ *
   * THE ENTRY ACTION
   * "Start module" opens what the current step needs, directly. No landing
   * on a step card first. If the session is already part-way through, the
   * same button resumes it and says so, rather than silently restarting.
   * ------------------------------------------------------------------ */
  window.GBRunStart = function (opts) {
    var b = document.querySelector(opts.button || ".bigstart");
    if (!b || !opts.steps || !opts.steps.length) return;
    var steps = opts.steps;
    /* A part-way session is a fact the entry screen has to state. An
       instructor who taps a big button and lands in the middle of the module
       has no way to know why - so say it, and make starting over one tap. */
    var strip = document.createElement("div");
    strip.className = "gbrun-resume";
    strip.hidden = true;
    strip.innerHTML =
      '<span class="rt">Part-way through</span>' +
      '<span class="rw"></span>' +
      '<button type="button" class="rb" data-gbrun-reset="1">' +
        "Start from the beginning</button>";
    if (b.parentNode) b.parentNode.insertBefore(strip, b.nextSibling);
    var rw = strip.querySelector(".rw");

    function paint() {
      var i = read(opts.key, steps.length - 1);
      var s = steps[i];
      var href = s.open && s.open.href;
      if (!href) return;
      b.setAttribute("href", href);
      b.innerHTML = i === 0
        ? "▶ Start module"
        : "▶ Resume — step " + (i + 1) + " of " + steps.length + ": " + esc(s.title);
      b.removeAttribute("data-go");
      strip.hidden = (i === 0);
      rw.textContent = "This tablet stopped at step " + (i + 1) + " of " + steps.length +
        " — " + s.title + ".";
    }

    function reset(e) {
      if (e) e.preventDefault();
      write(opts.key, 0);
      paint();
      window.scrollTo({ top: 0 });
    }

    paint();
    window.addEventListener("focus", paint);
    strip.querySelector("[data-gbrun-reset]").addEventListener("click", reset);

    /* the same job, from the step map */
    var r = document.querySelector(opts.restart || "[data-gbrun-restart]");
    if (r) r.addEventListener("click", reset);
  };

  window.GBRunFromDeck = function (key, block) {
    if (!STORE_OK) return;
    try { localStorage.setItem("gbdeck:" + key, block); } catch (e) {}
  };

  /* A deck has no bar, so its last screen advances the step itself. */
  window.GBRunAdvance = function (key, to) {
    write(key, to);
  };

  window.GBRun = function (opts) {
    opts = opts || {};
    if (!opts.key) return;
    if (opts.steps) runner(opts);
    else bar(opts);
  };
})();
