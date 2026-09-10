/* ==========================================================================
   cv_pins - annotate a photograph in IMAGE space

   Pins are positioned as a percentage of the PHOTOGRAPH (data-ix / data-iy),
   not of the box that displays it, and are mapped through the object-fit:cover
   crop at paint time. So the annotation stays on target at any screen aspect,
   survives a re-crop, and survives the photograph being replaced.

   That is the whole point: annotation baked into the pixels invalidates the
   teaching the moment somebody changes the crop. Annotation in the DOM does not.

   Markup
     <div class="cv-photo">
       <img src="..." alt="..." data-cv-pins
            data-pin-ox="0.5" data-pin-oy="0.5">   <!-- object-position, optional -->
       <button class="cv-pin" data-ix="42" data-iy="61">
         <span>Manifold</span>
       </button>
     </div>

   Behaviour
     - a pin whose target is cropped out of view hides itself
     - a pin near the right edge flips its label to the left
     - a pin flips, or un-flips, to stay off a sibling .cv-photo-copy column
     - the DOT never moves: on a photo screen the dot is the answer

   ES5. No dependencies. Safe on an old Android WebView.
   ========================================================================== */
(function (w, d) {
  "use strict";

  function each(list, fn) { Array.prototype.forEach.call(list, fn); }

  function place(img) {
    var box = img.parentElement;
    if (!box) { return; }
    var pins = box.querySelectorAll(".cv-pin[data-ix]");
    if (!pins.length) { return; }

    var W = box.clientWidth, H = box.clientHeight;
    var iw = img.naturalWidth, ih = img.naturalHeight;
    if (!W || !H || !iw || !ih) { return; }

    /* replicate object-fit: cover */
    var sc = Math.max(W / iw, H / ih);
    var rw = iw * sc, rh = ih * sc;

    var px = parseFloat(img.getAttribute("data-pin-ox"));
    var py = parseFloat(img.getAttribute("data-pin-oy"));
    if (isNaN(px)) { px = 0.5; }
    if (isNaN(py)) { py = 0.5; }
    var ox = (W - rw) * px, oy = (H - rh) * py;

    /* a copy column beside the photo that a label must not cover */
    var copy = box.parentElement &&
               box.parentElement.querySelector(".cv-photo-copy");
    var boxRect = box.getBoundingClientRect();
    var copyRect = copy ? copy.getBoundingClientRect() : null;

    each(pins, function (p) {
      var x = ox + (parseFloat(p.getAttribute("data-ix")) / 100) * rw;
      var y = oy + (parseFloat(p.getAttribute("data-iy")) / 100) * rh;

      /* target cropped away - hide rather than point at the wrong thing */
      var off = x < 8 || x > W - 8 || y < 8 || y > H - 8;
      p.style.visibility = off ? "hidden" : "";
      if (off) { return; }

      p.style.left = x + "px";
      p.style.top = y + "px";

      /* flip the LABEL, never the dot */
      var flip = x > W * 0.62;
      if (copyRect) {
        var absX = boxRect.left + x;
        var copyIsRight = copyRect.left >= boxRect.left + W * 0.5;
        /* if the label would run into the copy column, send it the other way,
           but only when the other side actually has room */
        if (copyIsRight && absX > copyRect.left - 180 && x > 180) { flip = true; }
        if (!copyIsRight && absX < copyRect.right + 180 && x < W - 180) { flip = false; }
      }
      if (flip) { p.classList.add("cv-pin-flip"); }
      else { p.classList.remove("cv-pin-flip"); }
    });
  }

  function placeAll(scope) {
    each((scope || d).querySelectorAll("img[data-cv-pins]"), function (img) {
      if (img.complete && img.naturalWidth) { place(img); }
      else { img.addEventListener("load", function () { place(img); }); }
    });
  }

  var t = null;
  function reflow() {
    clearTimeout(t);
    t = setTimeout(function () { placeAll(d); }, 60);
  }

  if (d.readyState === "loading") {
    d.addEventListener("DOMContentLoaded", function () { placeAll(d); });
  } else {
    placeAll(d);
  }
  w.addEventListener("resize", reflow);
  w.addEventListener("orientationchange", reflow);

  w.CVPins = { place: place, placeAll: placeAll, reflow: reflow };
})(window, document);
