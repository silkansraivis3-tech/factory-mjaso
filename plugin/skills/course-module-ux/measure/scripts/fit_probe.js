/* fit_probe.js - what the trainee sees on the active slide, at the step it is at now: the words a box cuts off, a box
   a part that spills out of the slide, and a picture shown only in part. fit_gate.py runs it
   after every press of Next, so the last step of a slide (its answer, its last line) is measured, not only its first.
   One function, called as FitProbe() in the page; it returns null when no slide is active. */
window.FitProbe = function () {
  var s = document.querySelector(".slide.active");
  if (!s) return null;
  var vw = innerWidth, vh = innerHeight;
  var out = { id: s.id, tpl: s.getAttribute("data-template") || "", last: s.hasAttribute("data-last"),
              cut: [], spill: [], pic: [] };
  function shown(el) {                     // seen at all: nothing on the way up hides it or fades it out
    var o = 1;
    for (var e = el; e && e !== document.body; e = e.parentElement) {
      var c = getComputedStyle(e);
      if (c.display === "none" || c.visibility === "hidden") return 0;
      o *= parseFloat(c.opacity);
    }
    return o;
  }
  function name(el) { return el.tagName.toLowerCase() + [].slice.call(el.classList, 0, 3).map(function (c) { return "." + c; }).join(""); }
  function words(el) { return (el.textContent || el.getAttribute("alt") || "").replace(/\s+/g, " ").trim().slice(0, 70); }
  function seen(el) {                      // the part of el's box left after every box that clips it, and the window
    var r = el.getBoundingClientRect(), L = r.left, T = r.top, R = r.right, B = r.bottom, by = "the window";
    for (var e = el.parentElement; e && e !== document.documentElement; e = e.parentElement) {
      var c = getComputedStyle(e);
      if (c.overflowX !== "visible" || c.overflowY !== "visible" || c.contain.indexOf("paint") >= 0) {
        var q = e.getBoundingClientRect();
        if (q.bottom < B - 0.5 || q.top > T + 0.5 || q.right < R - 0.5 || q.left > L + 0.5) by = name(e);
        L = Math.max(L, q.left); T = Math.max(T, q.top); R = Math.min(R, q.right); B = Math.min(B, q.bottom);
      }
    }
    return { L: Math.max(L, 0), T: Math.max(T, 0), R: Math.min(R, vw), B: Math.min(B, vh), by: by, r: r };
  }
  function ownText(el) {
    for (var i = 0; i < el.childNodes.length; i++) {
      var n = el.childNodes[i];
      if (n.nodeType === 3 && n.textContent.trim().length > 2) return true;
    }
    return false;
  }
  var all = s.querySelectorAll("*"), i, el;
  // 1. words cut by a box that clips them, or by the window
  for (i = 0; i < all.length; i++) {
    el = all[i];
    if (!ownText(el) || el.closest("svg") || el.closest(".mediabar") || el.closest("[data-fit-skip]") || shown(el) < 0.05) continue;
    var k = seen(el), r = k.r;
    if (r.width < 2 || r.height < 2) continue;
    var dy = Math.max(0, r.bottom - k.B) + Math.max(0, k.T - r.top), dx = Math.max(0, r.right - k.R) + Math.max(0, k.L - r.left);
    if (dy > 8 || dx > 8) out.cut.push({ el: name(el), words: words(el), px: Math.round(Math.max(dy, dx)), by: k.by });
  }
  // 1b. a card's frame cut by the box that holds it: its words may all show and its right or bottom border still be cut
  //     (a question card nudged past its column's edge)
  for (i = 0; i < all.length; i++) {
    el = all[i];
    if (el.closest("svg") || el.closest(".mediabar") || el.closest("[data-fit-skip]") || shown(el) < 0.05) continue;
    var bs = getComputedStyle(el);
    if (!["Top", "Right", "Bottom", "Left"].some(function (k) {
      return parseFloat(bs["border" + k + "Width"]) > 0 && bs["border" + k + "Style"] !== "none" &&
             !/rgba\([^)]*,\s*0\)|transparent/.test(bs["border" + k + "Color"]);
    })) continue;
    var f = seen(el), fr = f.r;
    if (fr.width < 2 || fr.height < 2 || f.R <= f.L || f.B <= f.T) continue;
    var cutBy = Math.max(fr.right - f.R, fr.bottom - f.B, f.L - fr.left, f.T - fr.top);
    if (cutBy > 2) out.cut.push({ el: name(el) + " (its frame)", words: words(el), px: Math.round(cutBy), by: f.by });
  }
  // 1c. a frame drawn round a line (its ::before / ::after, outside the line's own box) in a list that flows in columns:
  //     a line that opens a column has the frame's top edge left at the foot of the column before - an empty outlined box
  //     under another line. Only a line that is one unbreakable box (an inline block) keeps its frame whole
  function frameOut(el, at) {
    var c = getComputedStyle(el, at);
    if (c.content === "none" || c.display === "none" || c.position !== "absolute") return null;
    if (!["Top", "Right", "Bottom", "Left"].some(function (k) {
      return parseFloat(c["border" + k + "Width"]) > 0 && c["border" + k + "Style"] !== "none" &&
             !/rgba\([^)]*,\s*0\)|transparent/.test(c["border" + k + "Color"]);
    })) return null;
    return { up: Math.max(0, -parseFloat(c.top) || 0), down: Math.max(0, -parseFloat(c.bottom) || 0) };
  }
  function flowsIn(el) {                   // the box that flows el in columns, or null when el (or a box on the way) is unbreakable
    for (var e = el; e && e !== s; e = e.parentElement) {
      var c = getComputedStyle(e);
      if (e !== el && (c.columnCount !== "auto" || c.columnWidth !== "auto")) return e;
      if (/^inline-/.test(c.display) || /^(IMG|SVG|CANVAS|VIDEO|IFRAME)$/i.test(e.tagName) ||
          ["auto", "scroll", "hidden"].indexOf(c.overflowY) >= 0) return null;
    }
    return null;
  }
  for (i = 0; i < all.length; i++) {
    el = all[i];
    if (el.closest("svg") || el.closest(".mediabar") || el.closest("[data-fit-skip]") || shown(el) < 0.05) continue;
    var fo = frameOut(el, "::after") || frameOut(el, "::before");
    if (!fo || (!fo.up && !fo.down)) continue;
    var mc = flowsIn(el);
    if (!mc) continue;
    var mr = mc.getBoundingClientRect(), ms = getComputedStyle(mc), er = el.getBoundingClientRect();
    var top = mr.top + parseFloat(ms.borderTopWidth) + parseFloat(ms.paddingTop),
        bot = mr.bottom - parseFloat(ms.borderBottomWidth) - parseFloat(ms.paddingBottom),
        lft = mr.left + parseFloat(ms.borderLeftWidth) + parseFloat(ms.paddingLeft),
        rgt = mr.right - parseFloat(ms.borderRightWidth) - parseFloat(ms.paddingRight);
    var firstCol = er.left < lft + Math.max(2, er.width / 2), lastCol = er.right > rgt - Math.max(2, er.width / 2);
    var over = Math.max(firstCol ? 0 : top - (er.top - fo.up), lastCol ? 0 : (er.bottom + fo.down) - bot);
    if (over > 0.5) out.cut.push({ el: name(el) + " (its frame, split at the column break)", words: words(el),
                                   px: Math.max(1, Math.round(over)), by: name(mc) });
  }
  // 2. a card, a line, a picture that spills out of the slide
  var sr = s.getBoundingClientRect(), body = s.querySelector(".slide-body") || s;
  var parts = body.querySelectorAll(".copy, .fill, figure, li, .lt-in, .lt-pic, .lt-opt, img");
  for (i = 0; i < parts.length; i++) {
    el = parts[i];
    if (el.closest("[data-fit-skip]") || shown(el) < 0.05) continue;
    var p = el.getBoundingClientRect();
    if (p.width < 2) continue;
    var over = Math.max(p.bottom - Math.min(sr.bottom, vh), p.right - Math.min(sr.right, vw), sr.top - p.top, sr.left - p.left);
    if (over > 8) out.spill.push({ el: name(el), words: words(el).slice(0, 50), px: Math.round(over) });
  }
  // 3. pictures: how much of the picture shows (cover crops it), stretched (fill), and how much of its box is seen.
  //    A backdrop is cropped on purpose: inside data-fit="cover", the before/after slider (its two pictures lie exactly
  //    over each other) and the strip of small thumbnails.
  var imgs = s.querySelectorAll("img");
  for (i = 0; i < imgs.length; i++) {
    var im = imgs[i];
    if (im.closest("[data-fit-skip]") || shown(im) < 0.05) continue;
    if (!im.naturalWidth) { if (im.complete) out.pic.push({ src: im.getAttribute("src"), broken: true }); continue; }
    var b = im.getBoundingClientRect();
    if (b.width < 40 || b.height < 40) continue;
    var cs = getComputedStyle(im), nw = im.naturalWidth, nh = im.naturalHeight, bw = b.width, bh = b.height;
    var part = 1, stretch = 1, ar = (nw / nh) / (bw / bh);
    if (cs.objectFit === "cover") { var sc = Math.max(bw / nw, bh / nh); part = (bw * bh) / (nw * sc * nh * sc); }
    else if (cs.objectFit === "fill") stretch = Math.max(ar, 1 / ar);
    var v = seen(im), boxSeen = Math.max(0, v.R - v.L) * Math.max(0, v.B - v.T) / (bw * bh);
    out.pic.push({ src: (im.getAttribute("src") || "").split("/").pop(), fit: cs.objectFit, natural: nw + "x" + nh,
                   box: Math.round(bw) + "x" + Math.round(bh), part: +part.toFixed(2), stretch: +stretch.toFixed(2),
                   seen: +boxSeen.toFixed(2), by: boxSeen < 0.97 ? v.by : "",
                   backdrop: !!im.closest('[data-fit="cover"], .lt-ba, .photo-strip') });
  }
  return out;
};
