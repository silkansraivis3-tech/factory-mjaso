/* ==========================================================================
   task_complete.js — "you have finished; here is what happens next".

   WHY IT EXISTS. When a trainee finishes a task, something has to say so and
   say what comes next. Without it a trainee finishes, sees nothing change, and
   either sits not knowing whether they are done or keeps tapping at a finished
   task. Every task in a programme should end the same way, which is why this
   is one shared engine and not per-page markup: 32 pages hand-rolling a
   completion state produced 32 slightly different endings.

   IT IS A PANEL, NOT AN alert(). It must be dismissible, because the reason
   for every answer is on the page behind it and reading those reasons is the
   point of the task.

   TONE. A self-check and a recorded module check are different things, but
   neither gets shouted about. The owner was explicit: "no need to type
   REMEMBER, ITS ONLY SELF TEST, maybe small notice but not like contrast
   info". So the difference between them is one quiet line, and the panel never
   says "PASSED".

   THE SCORE GOES IN `line`. If a record sheet asks an instructor for a number
   the trainee's tablet showed, that number has to be rendered here — see
   SKILL.md §10. Computing a total and never painting it is the defect this
   parameter exists to prevent.

   Nothing is stored, nothing is sent, plain ES5.

   WIRING
     <link rel="stylesheet" href="../assets/task_complete.css">
     <script src="../assets/task_complete.js" defer></script>

     TaskDone.show({
       kind: "check",                       // "task" (self-check) | "check"
       line: "You got <b>7 of 8</b> right.",// the number a record may ask for
       href: "../tasks/index.html",         // optional route back
       hrefLabel: "Back to the task list"
     });

   WHAT A NEW COURSE CHANGES
     - Every default string below, if the delivery language is not English, and
       the `next` copy if the class does not debrief together.
     - Nothing else. Do not add a second panel type; one ending per programme.

   PREVIOUS COURSE: shipped as gb_done.js, global GBDone.
   ========================================================================== */
var TaskDone = (function () {
  "use strict";

  /* ---- copy a new course may translate or reword --------------------- */
  var TXT = {
    titleTask : "Task complete",
    titleCheck: "Module check complete",
    next      : "<b>Wait for your instructor.</b> The class goes through this " +
                "task together — that discussion is where anything you got " +
                "wrong gets explained.",
    noteTask  : "This is a self-check. Nothing here is recorded, and nothing " +
                "is sent anywhere.",
    noteCheck : "This one is recorded. Your instructor takes the result from " +
                "your screen.",
    closeLabel: "Look at the answers again"
  };

  var shown = false;

  function make(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) { n.className = cls; }
    if (html != null) { n.innerHTML = html; }
    return n;
  }

  function close(wrap) {
    /* removed outright rather than waiting on a transition that may never run
       — the trainee tapped close and the page behind has to come back */
    if (wrap.parentNode) { wrap.parentNode.removeChild(wrap); }
  }

  function show(opts) {
    opts = opts || {};
    if (shown && !opts.again) { return null; }
    shown = true;

    var kind = opts.kind || "task";            /* "task" | "check" */
    var wrap = make("div", "taskdone");
    var card = make("div", "taskdone-card");

    var title = opts.title ||
      (kind === "check" ? TXT.titleCheck : TXT.titleTask);

    var body = '<div class="taskdone-tick" aria-hidden="true">✓</div>' +
      "<h2>" + title + "</h2>";

    /* the score / result line — omitted only when the task has no number */
    if (opts.line) { body += '<p class="taskdone-line">' + opts.line + "</p>"; }

    body += '<p class="taskdone-next">' + (opts.next || TXT.next) + "</p>";

    body += '<p class="taskdone-note">' + (opts.note || (kind === "check"
      ? TXT.noteCheck : TXT.noteTask)) + "</p>";

    body += '<div class="taskdone-acts">' +
      '<button type="button" class="taskdone-btn" data-taskdone-close>' +
      (opts.closeLabel || TXT.closeLabel) + "</button>";
    if (opts.href) {
      body += '<a class="taskdone-btn ghost" href="' + opts.href + '">' +
        (opts.hrefLabel || "Back to the task list") + "</a>";
    }
    body += "</div>";

    card.innerHTML = body;
    wrap.appendChild(card);
    document.body.appendChild(wrap);

    var btn = card.querySelector("[data-taskdone-close]");
    if (btn) {
      btn.addEventListener("click", function () { close(wrap); });
      try { btn.focus(); } catch (e) {}
    }
    /* tapping the backdrop closes it; tapping the card does not */
    wrap.addEventListener("click", function (e) {
      if (e.target === wrap) { close(wrap); }
    });
    document.addEventListener("keydown", function esc(e) {
      if (e.key === "Escape") { close(wrap); document.removeEventListener("keydown", esc); }
    });
    return wrap;
  }

  /* ------------------------------------------------------------------ watch
     A CONVERSION BRIDGE, not the destination. Tasks written before this engine
     existed each signal completion differently, but what they nearly always
     share is a running count rendered as "n / total". Point watch() at that
     node and it fires once when the two numbers meet.

     A task built new should call show() from its own finish handler instead —
     the watcher is guessing, and a task that never renders its total (the very
     defect in SKILL.md §10) will never fire it. */
  function watch(sel, opts) {
    var node = typeof sel === "string" ? document.querySelector(sel) : sel;
    if (!node || !window.MutationObserver) { return null; }
    var fired = false;
    function look() {
      if (fired) { return; }
      var m = /(\d+)\s*(?:\/|of)\s*(\d+)/.exec(node.textContent || "");
      if (!m) { return; }
      var n = parseInt(m[1], 10), tot = parseInt(m[2], 10);
      if (tot > 0 && n >= tot) {
        fired = true;
        setTimeout(function () { show(opts || {}); }, 550);
      }
    }
    new MutationObserver(look).observe(node,
      { childList: true, characterData: true, subtree: true });
    look();
    return { check: look };
  }

  return { show: show, watch: watch };
})();
