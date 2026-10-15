/* ==========================================================================
   gb_photo.js — every photograph on a deck screen opens: large, with what it
   shows and whose it is, and from there full screen.

   WHY (owner, 2026-10-15, after Aigars's review of the IGF pilot): real
   photographs are the illustrations, and a photograph squeezed into a column
   or under a heading is a photograph nobody looks at. "Images need to be
   expandable - a lightbox with more explanation about the photo." The factory
   does it on its own: no build-sheet key, no request per slide. Ported from
   the definition panel and the full-screen figure of the oil/chemical course
   (Modules 6 and 10, course_deck_ext.js), which the owner had already
   approved in the classroom.

   WHAT IT DOES
     Tap a photograph on a slide -> a panel in the middle of the screen: the
     photograph large and whole (never cropped), the slide's title, what the
     photograph shows, and its credit. Tap the photograph in the panel -> it
     fills the screen; tap again -> back to the panel.
     A slide that IS a photograph (.slide.photo, the words over it) gets a
     "Photo" button in its top-right corner, because the words and the dark
     scrim lie over the picture; tapping the picture area works too.
     Three ways out, as everywhere: the close button (56 px), the dimmed screen
     around the panel, Escape. Escape unwinds one layer at a time: full screen,
     then the panel. While the panel is open the deck does not move - arrow
     keys, Space and swipes stay with the panel.

   WHERE THE WORDS COME FROM
     data-about on the <img>   what the photograph shows - written by the
                               compiler from the photo's own record
                               (assets/img/_photo_meta.json "description")
     data-credit on the <img>  author, source, licence - the same credit line
                               the slide prints
     else the <figcaption> of the photo's figure, else its alt text.
     The words are the photograph's caption, like its credit line: they say
     what the photograph shows, never more than it evidences
     (course-task-ux rulings §7).

   data-name on the <img>     the panel's heading - the part of a drawing a
                              small photo shows (L57, .photo-strip), else the
                              slide's title
   data-no-zoom on an <img> leaves it alone (a logo, an icon, a card face).
   Loaded by every compiled deck (course-factory compile/), after gb_deck.js.
   ES5, no dependencies, safe on an old Android WebView.
   ========================================================================== */
(function (w, d) {
  "use strict";
  var box = null, opener = null;

  function slideOf(n) { return n && n.closest ? n.closest(".slide") : null; }

  function canOpen(img) {
    if (!img || img.tagName !== "IMG") { return false; }
    if (!slideOf(img) || img.hasAttribute("data-no-zoom")) { return false; }
    if (img.closest(".brand-chip, .gbphoto, button, a")) { return false; }
    return true;
  }

  /* the photograph a tap means: the image itself, or - on a photo slide - its
     Photo button and the bare picture area under the scrim */
  function photoAt(t) {
    if (!t || !t.closest) { return null; }
    var s = slideOf(t);
    if (t.closest(".photo-open") || t.closest(".photo-scrim") || t.closest(".photo-wrap")) {
      var main = s ? s.querySelector(".photo-wrap img") : null;
      return canOpen(main) ? main : null;
    }
    return canOpen(t) ? t : null;
  }

  function esc(s) { return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }

  function wordsOf(img) {
    var about = img.getAttribute("data-about") || "";
    var credit = img.getAttribute("data-credit") || "";
    var fig = img.closest("figure");
    var cap = fig ? fig.querySelector("figcaption") : null;
    if (!about && cap) { about = cap.textContent.trim(); }
    if (!about) { about = img.getAttribute("alt") || ""; }
    if (!credit) {
      var s = slideOf(img), c = s ? s.querySelector(":scope > .credit") : null;
      if (c && s.querySelector(".photo-wrap img") === img) { credit = c.textContent.trim(); }
    }
    return { about: about, credit: credit };
  }

  function close() {
    if (!box) { return; }
    if (box.parentNode) { box.parentNode.removeChild(box); }
    box = null;
    if (opener) { try { opener.focus(); } catch (err) {} opener = null; }
  }

  function open(img) {
    close();
    var s = slideOf(img), words = wordsOf(img);
    /* a photo of one part of a drawing (L57) is named after that part, else after its slide */
    var title = img.getAttribute("data-name") || (s ? (s.getAttribute("data-title") || "") : "");
    var dark = s && (s.classList.contains("dark") || s.classList.contains("photo"));
    box = d.createElement("div");
    box.className = "gbphoto" + (dark ? " on-dark" : "");
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Photograph" + (title ? ": " + title : ""));
    box.innerHTML =
      '<div class="gbphoto-panel" tabindex="-1">' +
        '<button type="button" class="gbphoto-x" aria-label="Close">&times;</button>' +
        '<figure class="gbphoto-shot">' +
          '<img src="' + esc(img.getAttribute("src")) + '" alt="' + esc(img.getAttribute("alt")) + '">' +
          '<figcaption class="gbphoto-cue">Tap the photo to see it full screen</figcaption>' +
        "</figure>" +
        '<div class="gbphoto-say">' +
          '<p class="gbphoto-kicker">Photograph</p>' +
          (title ? '<h3 class="gbphoto-name">' + esc(title) + "</h3>" : "") +
          (words.about ? '<p class="gbphoto-about">' + esc(words.about) + "</p>" : "") +
          (words.credit ? '<p class="gbphoto-credit">' + esc(words.credit) + "</p>" : "") +
        "</div>" +
        '<p class="gbphoto-hint">Tap outside the panel, or press Esc, to close</p>' +
      "</div>";
    d.body.appendChild(box);
    opener = d.activeElement;
    try { box.querySelector(".gbphoto-panel").focus(); } catch (err) {}
  }

  function full(on) { if (box) { box.classList[on ? "add" : "remove"]("is-full"); } }

  /* capture on the window: the panel sees every tap and key before the deck does */
  w.addEventListener("click", function (e) {
    var t = e.target;
    if (box) {
      e.stopPropagation();
      if (t.closest && t.closest(".gbphoto-x")) { e.preventDefault(); if (box.classList.contains("is-full")) { full(false); } else { close(); } return; }
      if (t.closest && t.closest(".gbphoto-shot img")) { full(!box.classList.contains("is-full")); return; }
      if (box.classList.contains("is-full")) { full(false); return; }
      if (t.closest && t.closest(".gbphoto-panel")) { return; }
      close();
      return;
    }
    var img = photoAt(t);
    if (!img) { return; }
    e.stopPropagation();
    e.preventDefault();
    open(img);
  }, true);

  w.addEventListener("keydown", function (e) {
    if (!box) { return; }
    var k = e.key || "";
    if (k === "Escape" || k === "Esc" || e.keyCode === 27) {
      if (box.classList.contains("is-full")) { full(false); } else { close(); }
      e.stopPropagation(); e.preventDefault(); return;
    }
    if (k === "Tab" || e.keyCode === 9) {          /* Tab stays inside the panel */
      var x = box.querySelector(".gbphoto-x");
      if (x) { x.focus(); }
      e.preventDefault();
    }
    e.stopPropagation();                            /* the deck does not move under an open photograph */
  }, true);

  ["touchstart", "touchmove", "touchend"].forEach(function (ev) {
    w.addEventListener(ev, function (e) { if (box) { e.stopPropagation(); } }, true);
  });

  /* the Photo button on every slide that is a photograph, and the zoom cursor on every photograph */
  function mark() {
    Array.prototype.forEach.call(d.querySelectorAll(".slide img"), function (img) {
      if (canOpen(img)) { img.classList.add("gbphoto-can"); }
    });
    Array.prototype.forEach.call(d.querySelectorAll(".slide.photo"), function (s) {
      if (s.querySelector(".photo-open") || !canOpen(s.querySelector(".photo-wrap img"))) { return; }
      var b = d.createElement("button");
      b.type = "button";
      b.className = "photo-open";
      b.setAttribute("data-script-ignore", "");
      b.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" ' +
                    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/></svg>' +
                    "<span>Photo</span>";
      s.appendChild(b);
    });
  }
  if (d.readyState === "loading") { d.addEventListener("DOMContentLoaded", mark); } else { mark(); }

  w.GBPhoto = { open: open, close: close };
})(window, document);
