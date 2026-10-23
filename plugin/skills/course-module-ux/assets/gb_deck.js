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
     per-screen steps: a figure that builds takes Next / Back first (hook "step")
     the controls' words in the page's language (<html lang>: en, lv, ru - LANG)

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
  /* a scene's script loads before init: GB3D.wire is there from the start and keeps the scene's functions on its
     element until the deck finds them (2.63.2 - init replaces this with the whole of it) */
  w.GB3D = w.GB3D || { wire: function (e, api) { if (e) { e.__gb3dApi = api || {}; } return true; },
                       sync: function () {}, full: function () { return null; }, leave: function () {} };

  /* the engine's own words. The deck is the instructor's, so lv / ru use the polite form, as the start pages do.
     The course language (L19) - the page's <html lang>; PROVISIONAL (2.41.0), written by Claude, to be checked by a
     native speaker: course-factory/compile/TRANSLATIONS_REVIEW.md. opts.text still overrides any word. */
  var EN = {
    cue: "Instructor cue", noCue: "No cue for this screen.", start: "Start", screen: "Screen {n}", of: "of",
    next: "Next", back: "Back", grid: "All screens", full: "Fullscreen", leave: "Leave", close: "Close",
    fsIn: "Full screen", fsOut: "Exit full screen",
    ovHint: "Tap a screen to jump there · G closes this view",
    hint: "→ / Space next · ← back · F fullscreen · G all screens · N instructor cue",
    missing: "Navigation controls are missing from this page. Add the chrome block from " +
      "gb_shell.html before delivering this module."
  };
  var LANG = {
    lv: {
      cue: "Norāde instruktoram", noCue: "Šim ekrānam norādes nav.", start: "Sākt", screen: "{n}. ekrāns", of: "no",
      next: "Tālāk", back: "Atpakaļ", grid: "Visi ekrāni", full: "Pilnekrāns", leave: "Iziet", close: "Aizvērt",
      fsIn: "Pilnekrāns", fsOut: "Iziet no pilnekrāna",
      ovHint: "Pieskarieties ekrānam, lai uz to pārietu · G aizver šo skatu",
      hint: "→ / atstarpe – tālāk · ← atpakaļ · F pilnekrāns · G visi ekrāni · N norāde instruktoram",
      missing: "Šajā lapā trūkst navigācijas pogu. Pirms šī moduļa vadīšanas pievienojiet pogu bloku no gb_shell.html."
    },
    ru: {
      cue: "Подсказка для инструктора", noCue: "Для этого экрана подсказки нет.", start: "Начать", screen: "Экран {n}",
      of: "из", next: "Далее", back: "Назад", grid: "Все экраны", full: "Полный экран", leave: "Выйти", close: "Закрыть",
      fsIn: "Полный экран", fsOut: "Выйти из полного экрана",
      ovHint: "Коснитесь экрана, чтобы перейти к нему · G закрывает этот вид",
      hint: "→ / пробел – далее · ← назад · F полный экран · G все экраны · N подсказка для инструктора",
      missing: "На этой странице нет кнопок навигации. Перед проведением модуля добавьте блок кнопок из gb_shell.html."
    }
  };
  /* id -> [word, key]: the chrome is copied from gb_shell.html word for word, in English; a page in a language the
     engine has words for gets them on its controls here */
  var LABELS = { btnGrid: ["grid", "G"], btnCue: ["cue", "N"], btnPrev: ["back", "←"], btnNext: ["next", "→"],
                 btnFull: ["full", "F"], btnExit: ["leave", ""] };

  function init(opts) {
    opts = opts || {};
    var TXT = opts.text || {}, T = {}, k;
    var L = LANG[(d.documentElement.getAttribute("lang") || "en").slice(0, 2).toLowerCase()];
    for (k in EN) { if (EN.hasOwnProperty(k)) { T[k] = TXT[k] || (L && L[k]) || EN[k]; } }
    function said(word) { return !!(L || TXT[word]); }

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

    /* ---- the controls' words, in the page's language ---------------------- */
    each(Object.keys(LABELS), function (id) {
      var b = el(id), w = LABELS[id][0], key = LABELS[id][1];
      if (!b || !said(w)) { return; }
      b.setAttribute("aria-label", T[w]);
      b.setAttribute("title", T[w] + (key ? " (" + key + ")" : ""));
    });
    function relabel(node, word) {         /* the word only - an icon beside it stays */
      if (!node || !said(word)) { return; }
      var t = null;
      each(node.childNodes, function (c) { if (c.nodeType === 3 && /\S/.test(c.nodeValue)) { t = c; } });
      if (t) { t.nodeValue = t.nodeValue.replace(/\S(?:[\s\S]*\S)?/, T[word]); }
      else if (!node.children.length) { node.textContent = T[word]; }
    }
    var sb = el("startBtn");
    relabel(sb && sb.querySelector(".btn-label"), "start");
    relabel(el("ovClose"), "close");
    relabel(d.querySelector("#overview .ov-head b"), "grid");
    relabel(d.querySelector("#overview .ov-head span"), "ovHint");
    relabel(d.querySelector("#landing .landing-hint"), "hint");
    relabel(d.querySelector(".gbt-topback"), "back");

    /* slide id OR zero-based index -> {enter, leave, step}. Both are accepted because both
       are what people reach for; a key matching neither is announced rather than
       ignored, because a hook that never fires looks exactly like a figure that has
       no animation.
       step(dir), dir 1 or -1: the screen's own steps. Return true when the screen took
       the press (a step forward or back); false when it has none left that way, and the
       deck moves on. Next, Back, the arrow keys and a swipe all ask it first - a figure
       whose steps only its own small buttons can reach is skipped in front of a class
       (M03, 2026-10-15: each module carried its own copy of this, one did not). */
    var HOOKS = opts.hooks || {};

    function hookFor(i) {
      var s = slides[i];
      if (s && s.id && HOOKS[s.id]) { return HOOKS[s.id]; }
      if (HOOKS[i]) { return HOOKS[i]; }
      return null;
    }

    (function warnUnmatchedHooks() {
      var k, i, ok, keys = [];
      for (k in HOOKS) {
        if (!Object.prototype.hasOwnProperty.call(HOOKS, k)) { continue; }
        ok = false;
        for (i = 0; i < slides.length; i++) {
          if ((slides[i].id && slides[i].id === k) || String(i) === String(k)) {
            ok = true; break;
          }
        }
        if (!ok) { keys.push(k); }
      }
      if (keys.length && w.console && w.console.warn) {
        w.console.warn("GBDeck: " + keys.length + " hook key(s) match no slide id or " +
          "index and will never fire: " + keys.join(", ") +
          ". Key hooks by the slide's id attribute, or by its zero-based index.");
      }
    })();

    function show(idx) {
      idx = Math.max(0, Math.min(slides.length - 1, idx));
      var prevHook = hookFor(cur);
      if (prevHook && prevHook.leave) { prevHook.leave(); }
      each(slides, function (s, i) {
        if (i === idx) { s.classList.add("active"); } else { s.classList.remove("active"); }
      });
      cur = idx;
      var s = slides[idx];
      if (s.querySelector(".lt-part")) { setPart(s, 0); }
      if (counter) { counter.innerHTML = "<b>" + (idx + 1) + "</b> / " + slides.length; }
      if (progress) { progress.style.width = (100 * (idx + 1) / slides.length) + "%"; }
      if (blockTag) {
        blockTag.textContent = s.getAttribute("data-block") || "";
        /* a screen with a header band already names itself there - the corner tag sat on top of it */
        if (s.querySelector(".slide-kind")) { blockTag.classList.add("banded"); }
        else { blockTag.classList.remove("banded"); }
      }
      if (s.classList.contains("dark") || s.classList.contains("photo")) {
        d.body.classList.add("dark-active");
      } else {
        d.body.classList.remove("dark-active");
      }
      if (cue) {
        cue.innerHTML = '<span class="tag">' + T.cue + "</span>" +
          (s.getAttribute("data-cue") || T.noCue);
      }
      var h = hookFor(idx);
      navState();
      if (h && h.enter) { h.enter(); }
      var L0 = lockFor(idx);                          /* 2.63.3: a figure and its lines start together, at the first stop */
      if (L0) { L0.pos = 0; lockLight(s, L0); }
      markOverview();
      s.scrollTop = 0;
      if (fsBox && fsBox !== boxes3d[idx]) { fsLeave(); }
      if (boxes3d[idx]) {                            /* the scene's labels are placed once it draws */
        var bx = boxes3d[idx];
        fsPlace(bx);
        w.requestAnimationFrame(function () { if (cur === idx) { fsPlace(bx); } });
        each([150, 700], function (ms) { setTimeout(function () { if (cur === idx) { fsPlace(bx); lblSync(bx); } }, ms); });
      }
    }

    /* L61 (2.52.0) - a content-in-parts slide (.lt-part): Next / Back walk its parts first, every part reachable */
    function setPart(s, j) {
      each(s.querySelectorAll(".lt-part"), function (p, k) { p.classList[k === j ? "add" : "remove"]("on"); });
      each(s.querySelectorAll(".lt-tab"), function (t, k) {
        t.classList[k === j ? "add" : "remove"]("on");
        t.setAttribute("aria-pressed", k === j ? "true" : "false");
      });
      if (s === slides[cur]) { navState(); }
    }
    /* Back is off on the first slide and Next on the last - unless the screen still has a step or a part that way.
       2.63.2 (the 2.63.2 full-course run, M08-M10 and M12-M14): the parts were not counted, so on a deck whose LAST slide
       holds parts (the practical slide) Next was off on part 1 and part 2 could not be reached with it */
    function navState() {
      var s = slides[cur], h = hookFor(cur), ps = s ? s.querySelectorAll(".lt-part") : [], on = 0, k;
      for (k = 0; k < ps.length; k++) { if (ps[k].classList.contains("on")) { on = k; } }
      if (btnPrev) { btnPrev.disabled = (cur === 0) && !(h && h.step) && !(ps.length && on > 0); }
      if (btnNext) { btnNext.disabled = (cur === slides.length - 1) && !(h && h.step) && !(ps.length && on < ps.length - 1); }
    }
    function partStep(dir) {
      var s = slides[cur], ps = s ? s.querySelectorAll(".lt-part") : [], i = 0, k;
      if (!ps.length) { return false; }
      for (k = 0; k < ps.length; k++) { if (ps[k].classList.contains("on")) { i = k; } }
      if (i + dir < 0 || i + dir >= ps.length) { return false; }
      setPart(s, i + dir);
      return true;
    }
    d.addEventListener("click", function (e) {
      var t = e.target && e.target.closest ? e.target.closest(".lt-tab") : null;
      var s = t && t.closest(".slide");
      if (!t || !s) { return; }
      setPart(s, (parseInt(t.getAttribute("data-part"), 10) || 1) - 1);
    });

    /* 2.63.3 - ONE counter for a slide's figure steps, its text lines and its parts (Aleksis, the 2.63.2 build: on IGF M06
       s12 "the cloud finds a spark" Next walked both text parts first, then the figure's steps - and the lit line jumped
       back to line 1 with them; the original deck, compiled before parts, stepped them together). A hook that says which
       line(s) each of its steps lights - lines: [[1], [2], [3, 4] ...], go(n, animate) - is driven by the deck: each Next is
       one stop, the figure at its step, that step's line lit (.cur, the lines before .lit) and the part holding it shown.
       A line no step names is a stop of its own (the figure stays); a step that names no line keeps the last line lit.
       Back mirrors it, and Back into the slide lands on its last stop. kit.js gives every deck figure such a hook; a 3D
       scene with steps joins by giving its hook lines and go. */
    function lockFor(i) {
      var s = slides[i], h = hookFor(i);
      if (!s || !h || !h.lines || !h.go) { return null; }
      if (s.__lock && s.__lock.h === h) { return s.__lock; }
      var nums = [], named = {}, stops = [{ n: 0, line: [] }], k, j;
      each(s.querySelectorAll("[data-i]"), function (x) {
        var v = parseInt(x.getAttribute("data-i"), 10);
        if (!isNaN(v) && nums.indexOf(v) < 0 && !(x.closest && x.closest("svg"))) { nums.push(v); }
      });
      nums.sort(function (a, b) { return a - b; });
      each(h.lines, function (ls) { each(ls || [], function (v) { named[v] = 1; }); });
      var lone = nums.filter(function (v) { return !named[v]; }), at = 0;
      for (k = 0; k < h.lines.length; k++) {
        var ls = h.lines[k] || [], first = ls.length ? Math.min.apply(Math, ls) : null;
        while (first !== null && at < lone.length && lone[at] < first) { stops.push({ n: k, line: [lone[at]] }); at++; }
        stops.push({ n: k + 1, line: ls.slice() });
      }
      for (j = at; j < lone.length; j++) { stops.push({ n: h.lines.length, line: [lone[j]] }); }
      s.__lock = { h: h, stops: stops, pos: 0, busy: false };
      h.sync = function (n) {                           /* the figure stepped by itself (its buttons, a tapped line) */
        var L = s.__lock;
        if (!L || L.busy) { return; }
        if (L.stops[L.pos].n !== n) {
          for (k = 0; k < L.stops.length; k++) { if (L.stops[k].n === n) { L.pos = k; break; } }
        }
        lockLight(s, L);
      };
      return s.__lock;
    }
    function lockLight(s, L) {
      var lit = [], curL = [], q;
      for (q = 0; q <= L.pos; q++) {
        if (L.stops[q].line.length) { lit = lit.concat(curL); curL = L.stops[q].line; }
      }
      each(s.querySelectorAll("[data-i]"), function (x) { x.classList.remove("cur", "lit"); });
      each(lit, function (v) { each(s.querySelectorAll('[data-i="' + v + '"]'), function (x) { x.classList.add("lit"); }); });
      each(curL, function (v) { each(s.querySelectorAll('[data-i="' + v + '"]'), function (x) { x.classList.add("cur"); }); });
      var ln = curL.length ? s.querySelector('[data-i="' + curL[0] + '"]') : null, part = ln && ln.closest ? ln.closest(".lt-part") : null;
      if (!part && !L.pos) { part = s.querySelector(".lt-part"); }
      if (part && !part.classList.contains("on")) {
        var ps = s.querySelectorAll(".lt-part"), k;
        for (k = 0; k < ps.length; k++) { if (ps[k] === part) { setPart(s, k); } }
      }
    }
    function lockGo(s, L, p, animate) {
      L.pos = p;
      L.busy = true;
      try { L.h.go(L.stops[p].n, animate); } finally { L.busy = false; }
      lockLight(s, L);
    }

    function stepHere(dir) {
      var L = lockFor(cur);
      if (L) {
        var p = L.pos + dir;
        if (p < 0 || p >= L.stops.length) { return false; }
        lockGo(slides[cur], L, p, true);
        return true;
      }
      if (partStep(dir)) { return true; }
      var h = hookFor(cur);
      return !!(h && h.step && h.step(dir));
    }
    function next() { if (stepHere(1)) { return; } if (cur < slides.length - 1) { show(cur + 1); } }
    function prev() {
      if (stepHere(-1)) { return; }
      if (cur > 0) {
        show(cur - 1);
        var L = lockFor(cur);
        if (L) { lockGo(slides[cur], L, L.stops.length - 1, false); return; }   /* back into it: its last stop */
        var ps = slides[cur].querySelectorAll(".lt-part");          /* back into a parts slide: its last part first */
        if (ps.length) { setPart(slides[cur], ps.length - 1); }
      }
    }

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

    /* ---- a 3D scene: full screen on its own, and its labels select their parts (2.63.2) ----------------
       Aleksis, 2026-10-22: "the 3D scenes sit small" (both IGF builds) and "I want to be able to click on the labels as
       well to highlight that object". Every 3D slide (data-visual of the 3D family, or a canvas / [data-3d] /
       [data-scene] in it) gets a 44 px Full screen button in a free corner of the scene's own box - the [data-3d-box],
       else the figure (.fig) that holds its [data-stage]: canvas, labels, buttons and hint go full screen together
       (Fullscreen API, webkit fallback, else a fixed full-window box). Esc, the button or the browser leave it; inside
       the deck's own full screen it stacks and leaving returns there. While a scene is full screen Next / Back / the
       swipe never turn the slide. A window "resize" and a "gb3d-resize" on the box tell the scene to resize its
       renderer and camera.
       Labels: an element with data-3d-part="<name>" in the box is a control for that part - role="button", focusable,
       Enter / Space, a 44 px tap area - and does what a tap on the part does, through the scene's own function:
         GB3D.wire(stage or box, { select: function (name or null) {...}, current: function () { return name; } })
       a second tap on the selected label lets it go; the selected label shows as selected (aria-pressed, .gb3d-on).
       The scene calls GB3D.sync(stage) after a tap on the part itself. The deck's keys never fire from a label. */
    var fsBox = null, fsFaked = false, boxes3d = [];
    var ICON_IN = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/></svg>';
    var ICON_OUT = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5"/></svg>';
    function fsNow() { return d.fullscreenElement || d.webkitFullscreenElement || null; }
    function is3d(s) {
      return /3d/i.test(s.getAttribute("data-visual") || "") || !!s.querySelector("canvas,[data-3d],[data-scene]");
    }
    function boxOf(s) {
      var b = s.querySelector("[data-3d-box]"), st = s.querySelector("[data-stage],[data-3d],[data-scene],canvas");
      if (b) { return b; }
      return st ? (st.closest(".fig") || st.parentNode) : null;
    }
    function fsWord(b, on) {
      b.setAttribute("aria-label", on ? T.fsOut : T.fsIn);
      b.setAttribute("title", on ? T.fsOut + " (Esc)" : T.fsIn);
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.innerHTML = on ? ICON_OUT : ICON_IN;
    }
    function kick(box) {
      w.requestAnimationFrame(function () {
        var e1, e2;
        try { e1 = new Event("resize"); e2 = new CustomEvent("gb3d-resize", { bubbles: true }); }
        catch (x) { e1 = d.createEvent("Event"); e1.initEvent("resize", true, true); e2 = d.createEvent("CustomEvent"); e2.initCustomEvent("gb3d-resize", true, true, null); }
        w.dispatchEvent(e1);
        if (box) { box.dispatchEvent(e2); }
      });
    }
    function fsSync() {
      var now = fsNow();
      if (!fsFaked) { fsBox = (now && now.classList && now.classList.contains("gb-fs3d")) ? now : null; }
      each(boxes3d, function (b) {
        var on = b === fsBox, btn = b.querySelector(".gb-fs3d-btn");
        b.classList[on ? "add" : "remove"]("gb-fs3d-on");
        if (btn) { fsWord(btn, on); }
      });
      d.documentElement.classList[fsFaked ? "add" : "remove"]("gb-fs3d-faked");
      kick(fsBox || boxes3d[cur] || null);
    }
    function fsFake(box) { fsFaked = true; fsBox = box; fsSync(); }
    function fsEnter(box) {
      var rq = box.requestFullscreen || box.webkitRequestFullscreen;
      if (!rq) { fsFake(box); return; }
      try {
        var pr = rq.call(box);
        if (pr && typeof pr["catch"] === "function") { pr["catch"](function () { fsFake(box); }); }
      } catch (x) { fsFake(box); }
    }
    function fsLeave() {
      if (fsFaked) { fsFaked = false; fsBox = null; fsSync(); return; }
      var ex = d.exitFullscreen || d.webkitExitFullscreen;
      if (fsNow() === fsBox && ex) {
        try { var pr = ex.call(d); if (pr && typeof pr["catch"] === "function") { pr["catch"](function () {}); } } catch (x) {}
      }
    }
    /* the button goes in the corner of the box farthest from the scene's words and controls (IGF M04 s10: a fixed
       corner covered "1 Cold methane"); placed again each time the slide opens, as a scene's labels move with its view */
    function fsPlace(box) {
      var btn = box.querySelector(".gb-fs3d-btn"), R = box.getBoundingClientRect(), best = null;
      if (!btn || !R.width) { return; }
      var words = [];
      each(box.querySelectorAll("button,a,[role=button],[data-3d-part],[data-hint],label,span,p,b,strong,div"), function (x) {
        if (x === btn || btn.contains(x) || x.contains(btn)) { return; }
        var own = false;
        each(x.childNodes, function (c) { if (c.nodeType === 3 && /\S/.test(c.nodeValue)) { own = true; } });
        if (!own && !/^(BUTTON|A)$/.test(x.tagName) && x.getAttribute("role") !== "button") { return; }
        var r = x.getBoundingClientRect();
        if (r.width && r.height) { words.push(r); }
      });
      /* the corners first, then the middles of the edges (IGF M01 s05 at 1024 x 768: every corner held a word or the
         scene's own "Reset view"); the fewest things covered wins, then the widest gap */
      each([[8, 8, "top", "right"], [8, 8, "top", "left"], [8, 8, "bottom", "right"], [8, 8, "bottom", "left"],
            [8, (R.width - 44) / 2, "top", "left"], [8, (R.width - 44) / 2, "bottom", "left"],
            [(R.height - 44) / 2, 8, "top", "right"], [(R.height - 44) / 2, 8, "top", "left"]], function (c) {
        var x = c[3] === "right" ? R.right - c[1] - 44 : R.left + c[1], y = c[2] === "top" ? R.top + c[0] : R.bottom - c[0] - 44;
        var gap = 1e9, hit = 0;
        each(words, function (r) {
          var dx = Math.max(r.left - (x + 44), x - r.right, 0), dy = Math.max(r.top - (y + 44), y - r.bottom, 0);
          if (!dx && !dy) { hit++; }
          gap = Math.min(gap, Math.sqrt(dx * dx + dy * dy));
        });
        if (!best || hit < best.hit || (hit === best.hit && gap > best.gap + 0.5)) { best = { c: c, gap: gap, hit: hit }; }
      });
      btn.style.top = btn.style.bottom = btn.style.left = btn.style.right = "auto";   /* the stylesheet's top / right too */
      btn.style[best.c[2]] = best.c[0].toFixed(0) + "px";
      btn.style[best.c[3]] = best.c[1].toFixed(0) + "px";
    }
    /* labels: what the scene registered, found from the box */
    function scene(box) {
      if (!box) { return null; }
      if (box.__gb3d) { return box.__gb3d; }
      var found = null;                                /* wired before the deck started: on its stage or canvas */
      each(box.querySelectorAll("[data-stage],[data-3d],[data-scene],canvas"), function (x) { if (!found && x.__gb3dApi) { found = x.__gb3dApi; } });
      return found;
    }
    function lblSync(box) {
      var S = scene(box), now = S && S.current ? S.current() : null;
      each(box.querySelectorAll("[data-3d-part]"), function (lb) {
        if (!lb.hasAttribute("role")) {
          lb.setAttribute("role", "button");
          lb.setAttribute("tabindex", "0");
          lb.classList.add("gb3d-lbl");
          if (w.getComputedStyle && w.getComputedStyle(lb).position === "static") { lb.style.position = "relative"; }
        }
        var on = now != null && lb.getAttribute("data-3d-part") === String(now);
        lb.setAttribute("aria-pressed", on ? "true" : "false");
        lb.classList[on ? "add" : "remove"]("gb3d-on");
      });
    }
    function lblPick(box, lb) {
      var S = scene(box), name = lb.getAttribute("data-3d-part");
      if (!S || !S.select) { return; }
      S.select(S.current && String(S.current()) === name ? null : name);    /* a second tap lets it go */
      lblSync(box);
    }
    each(slides, function (s, i) {
      if (!is3d(s)) { return; }
      var box = boxOf(s);
      if (!box || boxes3d.indexOf(box) >= 0) { return; }
      boxes3d[i] = box;
      box.classList.add("gb-fs3d");
      var btn = d.createElement("button");
      btn.type = "button";
      btn.className = "gb-fs3d-btn";
      btn.setAttribute("data-no-zoom", "");
      btn.setAttribute("data-overlay", "");          // laid over the scene's box: the audit judges it never over a word
      fsWord(btn, false);
      btn.addEventListener("click", function (e) {
        e.preventDefault(); e.stopPropagation();
        if (fsBox === box) { fsLeave(); } else { fsEnter(box); }
      });
      box.appendChild(btn);
      box.addEventListener("click", function (e) {
        var lb = e.target && e.target.closest ? e.target.closest("[data-3d-part]") : null;
        if (!lb || !box.contains(lb)) { return; }
        e.stopPropagation();
        lblPick(box, lb);
        if (e.detail) { lb.blur(); }                  /* a mouse or a finger: the deck keeps its keys */
      });
      box.addEventListener("keydown", function (e) {
        var lb = e.target && e.target.closest ? e.target.closest("[data-3d-part]") : null, kk = e.key || KC3[e.keyCode] || "";
        if (!lb) { return; }
        if (kk === "Enter" || kk === " " || kk === "Spacebar") { e.preventDefault(); lblPick(box, lb); }
        if (DECK_KEYS[kk]) { e.stopPropagation(); }   /* never a slide turned from a label */
      });
      each(["pointerdown", "mousedown", "touchstart"], function (ev) {      /* a press on a label is not the scene's drag */
        box.addEventListener(ev, function (e) {
          if (e.target && e.target.closest && e.target.closest("[data-3d-part]")) { e.stopPropagation(); }
        }, ev === "touchstart" ? { passive: true } : false);
      });
      var again = 0;                                   /* the scene adds its labels and controls as it builds: placed again */
      if (w.MutationObserver) {
        new w.MutationObserver(function (ms) {
          if (ms.every(function (m) { return m.target === btn || btn.contains(m.target); })) { return; }
          lblSync(box);
          if (!again) { again = w.requestAnimationFrame(function () { again = 0; if (boxes3d[cur] === box) { fsPlace(box); } }); }
        }).observe(box, { childList: true, subtree: true });
      }
    });
    var KC3 = { 39: "ArrowRight", 37: "ArrowLeft", 32: " ", 34: "PageDown", 33: "PageUp", 36: "Home", 35: "End", 13: "Enter" };
    var DECK_KEYS = { ArrowRight: 1, Right: 1, ArrowLeft: 1, Left: 1, " ": 1, Spacebar: 1, PageDown: 1, PageUp: 1,
                      Home: 1, End: 1, f: 1, F: 1, g: 1, G: 1, n: 1, N: 1, Enter: 1 };
    w.addEventListener("resize", function () { if (boxes3d[cur]) { w.requestAnimationFrame(function () { fsPlace(boxes3d[cur]); }); } });
    d.addEventListener("fullscreenchange", fsSync);
    d.addEventListener("webkitfullscreenchange", fsSync);
    w.GB3D = {
      wire: function (el, api) {
        var box = el && (el.classList && el.classList.contains("gb-fs3d") ? el : el.closest && el.closest(".gb-fs3d"));
        if (el) { el.__gb3dApi = api || {}; }
        if (!box) { return false; }
        box.__gb3d = api || {};
        lblSync(box);
        return true;
      },
      sync: function (el) { var box = el && el.closest && el.closest(".gb-fs3d"); if (box) { lblSync(box); } },
      full: function () { return fsBox; },
      leave: fsLeave
    };

    /* ---- overview grid --------------------------------------------------- */
    var ovGrid = el("ovGrid");
    if (ovGrid && !ovGrid.children.length) {
      each(slides, function (s, i) {
        var b = d.createElement("button");
        b.type = "button";
        b.className = "ov-item";
        b.innerHTML =
          '<span class="n">' + (i + 1) + "</span>" +
          '<span class="t">' + (s.getAttribute("data-title") ||
            (T.screen.indexOf("{n}") < 0 ? T.screen + " " + (i + 1) : T.screen.replace("{n}", i + 1))) + "</span>" +
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
      if (fsBox) {                                    /* a 3D scene full screen: the deck turns no slide (2.63.2) */
        if (k === "Escape" && fsFaked) { e.preventDefault(); fsLeave(); }
        return;
      }
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
      if (!started || fsBox || e.touches.length !== 1) { tx = null; return; }
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
