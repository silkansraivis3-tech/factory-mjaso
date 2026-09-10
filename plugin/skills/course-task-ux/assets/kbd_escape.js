/* ==========================================================================
   kbd_escape.js — three ways out of the soft keyboard.

   THE DEFECT THIS FIXES, in the owner's words:

     "when i try to type my name in module2 task cards, i cannot basically and
      safely come back"

   On an Android tablet a WebView raises the soft keyboard when a field takes
   focus and lowers it when that field LOSES focus. On the pages that shipped,
   nothing ever took the focus away — so the keyboard stayed up over the bottom
   third of the screen with no way back. The device Back button dismisses it,
   but a trainee should not have to know that, and on a kiosk-style tablet Back
   may be bound to something else. One page carried 99 input fields and was
   unusable.

   Three routes out, because any one of them can be unavailable — WebView
   versions differ in which they honour, and a keyboard skin can replace the
   action key:

     1. enterkeyhint="done" on every single-line field, so the keyboard's own
        action key reads Done instead of a next-field arrow. Pressing it fires
        Enter, which (2) turns into a blur.
     2. Enter in a single-line input blurs it. Textareas are exempt — Enter is
        a newline there, which is the entire point of a textarea.
     3. A Done pill, shown only while a field has focus, positioned clear of
        the keyboard. This is the only one of the three that cannot be defeated
        by a WebView quirk, so it is the one that must never be dropped.

     ...and tapping the page outside any field also blurs, which is what a user
     who has never seen a tablet tries first.

   Nothing is stored, nothing is sent, no dependencies, plain ES5.

   WIRING — in <head>, and that is the whole integration:
     <link rel="stylesheet" href="../assets/kbd_escape.css">
     <script src="../assets/kbd_escape.js" defer></script>

   WHAT A NEW COURSE CHANGES
     - The pill's label, below, if the delivery language is not English.
     - FIELD / isField() if the course uses input types this list misses
       (date, tel, email). Add them to BOTH — they must agree or the pill
       shows for a field Enter will not blur.
     - Nothing else.

   PREVIOUS COURSE: shipped as gb_kbd.js.
   ========================================================================== */
(function () {
  "use strict";

  var PILL_LABEL = "Done ✓";
  var PILL_ARIA  = "Close the keyboard";

  var FIELD = "input[type=text],input[type=number],input[type=search]," +
              "input:not([type]),textarea";

  function isField(el) {
    if (!el || !el.tagName) { return false; }
    var t = el.tagName;
    if (t === "TEXTAREA") { return true; }
    if (t !== "INPUT") { return false; }
    var ty = (el.getAttribute("type") || "text").toLowerCase();
    return ty === "text" || ty === "number" || ty === "search";
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else { fn(); }
  }

  ready(function () {
    /* ---- 1 · the keyboard's own action key says Done ------------------ */
    var fields = document.querySelectorAll(FIELD);
    Array.prototype.forEach.call(fields, function (el) {
      if (el.tagName !== "TEXTAREA" && !el.getAttribute("enterkeyhint")) {
        el.setAttribute("enterkeyhint", "done");
      }
    });

    /* ---- 3 · the Done pill ------------------------------------------- */
    var pill = document.createElement("button");
    pill.type = "button";
    pill.id = "kbd-done";
    pill.setAttribute("aria-label", PILL_ARIA);
    pill.textContent = PILL_LABEL;
    document.body.appendChild(pill);

    var hideTimer = null;

    function show() {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
      pill.classList.add("on");
    }
    function hideSoon() {
      /* moving between two fields fires focusout before the next focusin, so
         settle first and only hide if nothing at all has focus — otherwise the
         pill flickers off between every two fields of a 99-field page */
      if (hideTimer) { clearTimeout(hideTimer); }
      hideTimer = setTimeout(function () {
        hideTimer = null;
        if (!isField(document.activeElement)) { pill.classList.remove("on"); }
      }, 120);
    }

    document.addEventListener("focusin", function (e) {
      if (isField(e.target)) { show(); }
    });
    document.addEventListener("focusout", function (e) {
      if (isField(e.target)) { hideSoon(); }
    });

    pill.addEventListener("click", function (e) {
      e.preventDefault();
      var a = document.activeElement;
      if (isField(a)) { a.blur(); }
      pill.classList.remove("on");
    });
    /* the pill must not steal focus before it has had a chance to act on it */
    pill.addEventListener("mousedown", function (e) { e.preventDefault(); });

    /* ---- 2 · Enter closes a single-line field ------------------------- */
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" && e.keyCode !== 13) { return; }
      var a = e.target;
      if (!isField(a) || a.tagName === "TEXTAREA") { return; }
      e.preventDefault();          /* never submit a form we do not own */
      a.blur();
    });

    /* ---- and tapping the page outside a field ------------------------- */
    document.addEventListener("pointerdown", function (e) {
      var a = document.activeElement;
      if (!isField(a)) { return; }
      var t = e.target;
      if (t === pill || (t.closest && t.closest("#kbd-done"))) { return; }
      if (t.closest && t.closest("input,textarea,label")) { return; }
      a.blur();
    }, true);
  });
})();
