/* ==========================================================================
   measure_in_page.js — the in-page half of the measurable floor (SKILL.md §11).

   Paste into the browser console on a served task page, or run it through
   whatever browser tooling the session has. It prints a table of violations and
   returns the result object, so it can be read programmatically.

   It measures what only a laid-out page can tell you: real tap geometry, the
   painted size of text, contrast against the RESOLVED (alpha-composited)
   background, horizontal overflow, and overlap.

   IT REFUSES TO RUN IN A 0 x 0 PANE. A hidden or unfocused browser pane lays
   out at zero and every number taken there is garbage — garbage that reads as
   either a catastrophic failure or a clean pass. Read innerWidth first, always.
   references/verify.md has the rest of the traps.

   WHAT IT CANNOT DO, and you must do by hand: decide whether the RIGHT control
   is the one live control (§4), whether a hint gives the answer away (§6),
   whether a caption over-claims what a photograph shows (§7), and whether the
   completion panel says what happens next (§9). Also: activate each part of the
   task first. Progressive disclosure means most of the page is legitimately
   display:none, zero-size nodes are skipped, and a genuinely collapsed control
   can hide inside that exemption.

   WHAT A NEW COURSE CHANGES: FLOOR below, if its device is not an 800 x 1280
   portrait tablet. Re-measure the floor; do not inherit it.

   Plain ES5, no dependencies.
   ========================================================================== */
(function () {
  "use strict";

  var FLOOR = {
    text: 12.5,          /* px, anything a trainee reads */
    tap: 44,             /* px, both dimensions */
    contrast: 4.5,       /* :1 normal text */
    contrastLarge: 3.0,  /* :1 >=24px, or >=18.66px bold */
    minViewport: 320     /* below this, refuse — the pane is not laid out */
  };

  var vw = window.innerWidth, vh = window.innerHeight;
  if (!vw || vw < FLOOR.minViewport) {
    var msg = "REFUSING TO MEASURE: innerWidth is " + vw + ". The pane is hidden, " +
      "unfocused or not laid out, and every geometry number would be garbage. " +
      "Show and focus the pane, reload, and run again.";
    console.error(msg);
    return { ok: false, refused: msg };
  }

  /* ------------------------------------------------------------ colour ---- */
  function parseColor(s) {
    var m = /rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?/.exec(s || "");
    if (!m) { return null; }
    return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] };
  }
  function over(fg, bg) {           /* alpha-composite fg onto bg */
    var a = fg.a;
    return { r: fg.r * a + bg.r * (1 - a),
             g: fg.g * a + bg.g * (1 - a),
             b: fg.b * a + bg.b * (1 - a), a: 1 };
  }
  function lum(c) {
    function ch(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  }
  function ratio(a, b) {
    var la = lum(a), lb = lum(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }
  /* The resolved background: walk up until something is actually opaque, and
     composite every translucent layer on the way. Reading only the element's
     own background-color is how a "passing" 1.1:1 gets reported as fine. */
  function resolvedBg(el) {
    var stack = [], n = el;
    while (n && n.nodeType === 1) {
      var c = parseColor(getComputedStyle(n).backgroundColor);
      if (c && c.a > 0) { stack.push(c); if (c.a >= 1) { break; } }
      n = n.parentElement;
    }
    var base = { r: 255, g: 255, b: 255, a: 1 };
    for (var i = stack.length - 1; i >= 0; i--) { base = over(stack[i], base); }
    return base;
  }

  /* -------------------------------------------------------- svg text px ---- */
  /* effective px = declared px x (rendered width / viewBox width)
     A label declared at 12px inside a 350-unit viewBox rendered 843px wide is
     painted at 28.9px. Reading the declared value alone made a correct label
     look like a violation and nearly got it "fixed" upward. It cuts the other
     way too: a viewBox wider than its box shrinks text below the floor while
     the markup reads as compliant. */
  function svgScale(el) {
    var svg = el.ownerSVGElement || (el.tagName === "svg" ? el : null);
    if (!svg) { return 1; }
    var vb = svg.viewBox && svg.viewBox.baseVal;
    if (!vb || !vb.width) { return 1; }
    var w = svg.getBoundingClientRect().width;
    return w && vb.width ? (w / vb.width) : 1;
  }

  /* ------------------------------------------------------------- helpers -- */
  function visible(el) {
    var s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || +s.opacity === 0) { return false; }
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;      /* zero-size nodes are skipped */
  }
  function where(el) {
    var s = el.tagName.toLowerCase();
    if (el.id) { s += "#" + el.id; }
    else if (el.className && typeof el.className === "string") {
      s += "." + el.className.trim().split(/\s+/).slice(0, 2).join(".");
    }
    var t = (el.textContent || "").replace(/\s+/g, " ").trim();
    return s + (t ? ' "' + t.slice(0, 44) + (t.length > 44 ? "…" : "") + '"' : "");
  }

  var out = { viewport: vw + " x " + vh, tap: [], text: [], contrast: [],
              overflow: [], overlap: [], examined: 0, skippedHidden: 0 };

  /* ----------------------------------------------------------- tap size --- */
  var TAPPABLE = "a[href],button,input,select,textarea,summary,[role=button]," +
                 "[onclick],[data-answer],[tabindex]:not([tabindex='-1'])";
  Array.prototype.forEach.call(document.querySelectorAll(TAPPABLE), function (el) {
    if (!visible(el)) { out.skippedHidden++; return; }
    var r = el.getBoundingClientRect();
    if (r.width < FLOOR.tap || r.height < FLOOR.tap) {
      out.tap.push({ node: where(el),
                     size: Math.round(r.width) + " x " + Math.round(r.height),
                     need: FLOOR.tap + " x " + FLOOR.tap });
    }
  });

  /* -------------------------------------------- text size and contrast ---- */
  var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode: function (n) {
      return (n.nodeValue || "").trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });
  var seen = [], node;
  while ((node = walker.nextNode())) {
    var el = node.parentElement;
    if (!el || seen.indexOf(el) !== -1) { continue; }
    seen.push(el);
    if (!visible(el)) { out.skippedHidden++; continue; }
    out.examined++;
    var st = getComputedStyle(el);
    var declared = parseFloat(st.fontSize) || 0;
    var scale = svgScale(el);
    var painted = declared * scale;

    if (painted < FLOOR.text) {
      out.text.push({ node: where(el), painted: painted.toFixed(1) + "px",
                      declared: declared.toFixed(1) + "px",
                      svgScale: scale === 1 ? "-" : scale.toFixed(3),
                      need: FLOOR.text + "px" });
    }
    var fg = parseColor(st.color);
    if (fg) {
      var bg = resolvedBg(el);
      var c = ratio(fg.a < 1 ? over(fg, bg) : fg, bg);
      var bold = (parseInt(st.fontWeight, 10) || 400) >= 700;
      var need = (painted >= 24 || (bold && painted >= 18.66))
        ? FLOOR.contrastLarge : FLOOR.contrast;
      if (c < need) {
        out.contrast.push({ node: where(el), ratio: c.toFixed(2) + ":1",
                            need: need + ":1", color: st.color,
                            resolvedBg: "rgb(" + [bg.r, bg.g, bg.b]
                              .map(Math.round).join(",") + ")" });
      }
    }
  }

  /* --------------------------------------------------- horizontal scroll -- */
  var de = document.documentElement;
  if (de.scrollWidth > de.clientWidth + 1) {
    out.overflow.push({ node: "document", scrollWidth: de.scrollWidth,
                        clientWidth: de.clientWidth });
    Array.prototype.forEach.call(document.querySelectorAll("body *"), function (el) {
      if (!visible(el)) { return; }
      var r = el.getBoundingClientRect();
      if (r.right > vw + 1 || r.left < -1) {
        var p = el.parentElement, ps = p ? getComputedStyle(p).overflowX : "";
        if (ps === "auto" || ps === "scroll") { return; }   /* legitimately scrolls */
        out.overflow.push({ node: where(el), left: Math.round(r.left),
                            right: Math.round(r.right), viewport: vw });
      }
    });
  }

  /* --------------------------------------------------------- overlap ------ */
  /* Text boxes that intersect each other. Sampled against siblings only, which
     is where every real case came from and keeps this from being O(n^2). */
  seen.forEach(function (a) {
    if (!a.parentElement) { return; }
    var ra = a.getBoundingClientRect();
    Array.prototype.forEach.call(a.parentElement.children, function (b) {
      if (b === a || seen.indexOf(b) === -1) { return; }
      var rb = b.getBoundingClientRect();
      var ox = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      var oy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (ox > 2 && oy > 2) {
        var s = getComputedStyle(a), t = getComputedStyle(b);
        if (s.position === "static" && t.position === "static") {
          out.overlap.push({ a: where(a), b: where(b),
                             by: Math.round(ox) + " x " + Math.round(oy) + "px" });
        }
      }
    });
  });

  /* ---------------------------------------------------------- report ------ */
  out.violations = out.tap.length + out.text.length + out.contrast.length +
                   out.overflow.length + out.overlap.length;
  out.ok = out.violations === 0;

  console.log("%c task-ux floor · " + out.viewport + " · " + out.examined +
    " text node(s), " + out.skippedHidden + " hidden skipped",
    "font-weight:bold");
  ["tap", "text", "contrast", "overflow", "overlap"].forEach(function (k) {
    if (out[k].length) {
      console.log("%c" + k + " — " + out[k].length, "color:#b00;font-weight:bold");
      if (console.table) { console.table(out[k]); } else { console.log(out[k]); }
    }
  });
  if (out.ok) {
    console.log("%cno violations at this viewport, in the parts currently visible.",
      "color:#0a0");
    console.log("Not done yet: activate every part and re-run, drive the task to its " +
      "completion panel, and read the console for errors (SKILL.md §12).");
  }
  return out;
})();
