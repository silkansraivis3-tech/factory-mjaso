/* ==========================================================================
   cv_schematic - render a system from a TYPED TOPOLOGY, not by hand

   The alternative to [BOX] -> [BOX] -> [BOX].

   You declare the system as data: nodes with a kind and a position, and
   segments with a service, two endpoints and a state. The renderer draws it.
   Because the model exists, the same system can be re-laid-out, re-stated,
   asked questions ("what is downstream of V3 if it shuts?"), and checked -
   none of which is possible with a hand-drawn picture of boxes.

   Model
     var SYS = {
       viewBox: [0, 0, 1000, 470],
       services: {
         liquid: { colour: "var(--blue, #2EB6F8)", width: 6 },
         vapour: { colour: "var(--amber, #E9A51E)", width: 4, dash: "10 6" }
       },
       nodes: [
         { id: "t1", kind: "tank",     x: 140, y: 250, w: 260, h: 180, label: "No.1 TANK" },
         { id: "p1", kind: "pump",     x: 240, y: 404, label: "Pump" },
         { id: "v1", kind: "valve",    x: 240, y: 170, label: "V1", state: "shut" },
         { id: "mf", kind: "manifold", x: 940, y: 170, label: "Manifold" }
       ],
       segments: [
         { id: "s1", service: "liquid", from: "p1", to: "v1" },
         { id: "s2", service: "liquid", from: "v1", to: "mf", via: [[240,170],[940,170]],
           flow: "forward", state: "active" }
       ]
     };

   State per segment: "active" | "idle" | "isolated".
   Flow direction is DRAWN (an animated dash along the real route), never
   asserted with a floating arrow.

   Honest simplification: dropping a branch to keep the figure readable is
   fine. Drawing a branch that does not exist, or a direction that is wrong,
   is an error - not a style choice.

   ES5. No dependencies.
   ========================================================================== */
(function (w, d) {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";

  function el(name, attrs) {
    var n = d.createElementNS(NS, name), k;
    for (k in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, k) && attrs[k] !== null) {
        n.setAttribute(k, attrs[k]);
      }
    }
    return n;
  }

  function nodeById(sys, id) {
    for (var i = 0; i < sys.nodes.length; i++) {
      if (sys.nodes[i].id === id) { return sys.nodes[i]; }
    }
    return null;
  }

  function pathFor(sys, seg) {
    var a = nodeById(sys, seg.from), b = nodeById(sys, seg.to);
    if (!a || !b) { return null; }
    var pts = [[a.x, a.y]];
    if (seg.via) { pts = pts.concat(seg.via); }
    pts.push([b.x, b.y]);
    var dstr = "M" + pts[0][0] + " " + pts[0][1];
    for (var i = 1; i < pts.length; i++) { dstr += " L" + pts[i][0] + " " + pts[i][1]; }
    return dstr;
  }

  /* ---------------------------------------------------------- components */
  var DRAW = {
    tank: function (n) {
      var g = el("g", { "class": "cv-n cv-tank", "data-id": n.id });
      var w2 = n.w || 220, h2 = n.h || 160;
      var x = n.x - w2 / 2, y = n.y - h2 / 2;
      g.appendChild(el("rect", {
        x: x, y: y, width: w2, height: h2, rx: 24,
        fill: "var(--deep-3, #122A52)",
        stroke: "var(--line-d, rgba(46,182,248,.34))", "stroke-width": 2
      }));
      /* liquid level - a tank is not an empty box; the phase split is content */
      var lvl = (n.level === undefined) ? 0.55 : n.level;
      g.appendChild(el("rect", {
        x: x + 6, y: y + h2 * (1 - lvl), width: w2 - 12, height: h2 * lvl - 6, rx: 18,
        fill: "var(--blue, #2EB6F8)", opacity: .22
      }));
      return g;
    },
    valve: function (n) {
      var g = el("g", { "class": "cv-n cv-valve", "data-id": n.id,
                        "data-state": n.state || "shut" });
      var s = 13;
      /* the conventional two-triangle valve body, so it reads as a valve */
      g.appendChild(el("path", {
        d: "M" + (n.x - s) + " " + (n.y - s) + " L" + (n.x + s) + " " + (n.y + s) +
           " L" + (n.x + s) + " " + (n.y - s) + " L" + (n.x - s) + " " + (n.y + s) + " Z",
        fill: (n.state === "open") ? "var(--good, #12805A)" : "var(--deep-2, #0C1E3A)",
        stroke: "var(--txt-d, #F3F8FD)", "stroke-width": 2
      }));
      return g;
    },
    pump: function (n) {
      var g = el("g", { "class": "cv-n cv-pump", "data-id": n.id });
      g.appendChild(el("circle", {
        cx: n.x, cy: n.y, r: 16,
        fill: "var(--deep-2, #0C1E3A)",
        stroke: "var(--txt-d, #F3F8FD)", "stroke-width": 2
      }));
      g.appendChild(el("path", {
        d: "M" + (n.x - 7) + " " + (n.y - 8) + " L" + (n.x + 9) + " " + n.y +
           " L" + (n.x - 7) + " " + (n.y + 8) + " Z",
        fill: "var(--txt-d, #F3F8FD)"
      }));
      return g;
    },
    manifold: function (n) {
      var g = el("g", { "class": "cv-n cv-manifold", "data-id": n.id });
      g.appendChild(el("rect", {
        x: n.x - 12, y: n.y - 30, width: 24, height: 60, rx: 6,
        fill: "var(--steel, #415C8F)",
        stroke: "var(--txt-d, #F3F8FD)", "stroke-width": 2
      }));
      return g;
    },
    generic: function (n) {
      var g = el("g", { "class": "cv-n", "data-id": n.id });
      g.appendChild(el("circle", {
        cx: n.x, cy: n.y, r: 14,
        fill: "var(--deep-2, #0C1E3A)",
        stroke: "var(--txt-d, #F3F8FD)", "stroke-width": 2
      }));
      return g;
    }
  };

  function render(host, sys) {
    var vb = sys.viewBox || [0, 0, 1000, 470];
    var svg = el("svg", {
      viewBox: vb.join(" "),
      "class": "cv-schem",
      role: "img",
      "aria-label": sys.label || "System schematic"
    });

    var gSeg = el("g", { "class": "cv-segs" });
    var gNode = el("g", { "class": "cv-nodes" });
    var gLbl = el("g", { "class": "cv-labels" });

    /* segments first, so components sit on top of the pipework */
    for (var i = 0; i < (sys.segments || []).length; i++) {
      var seg = sys.segments[i];
      var svc = (sys.services || {})[seg.service] || {};
      var dstr = pathFor(sys, seg);
      if (!dstr) { continue; }
      var p = el("path", {
        d: dstr,
        "class": "cv-seg",
        "data-id": seg.id,
        "data-service": seg.service,
        "data-state": seg.state || "idle",
        fill: "none",
        stroke: svc.colour || "var(--faint-d, #71879F)",
        "stroke-width": svc.width || 5,
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
        "stroke-dasharray": svc.dash || null
      });
      gSeg.appendChild(p);

      /* flow is DRAWN along the real route, never a floating arrow */
      if (seg.flow && (seg.state === "active")) {
        var f = el("path", {
          d: dstr,
          "class": "cv-flow",
          "data-motion": "teaching",
          "data-dir": seg.flow,
          fill: "none",
          stroke: svc.colour || "var(--blue, #2EB6F8)",
          "stroke-width": (svc.width || 5) + 2,
          "stroke-linecap": "round",
          "stroke-dasharray": "14 22"
        });
        gSeg.appendChild(f);
      }
    }

    for (var j = 0; j < (sys.nodes || []).length; j++) {
      var n = sys.nodes[j];
      gNode.appendChild((DRAW[n.kind] || DRAW.generic)(n));
      if (n.label) {
        /* 15 units in a 1000-unit viewBox is ~5.7px in a 380px column:
           label size is chosen against the RENDERED width, not the viewBox */
        var ly = (n.kind === "tank") ? (n.y + (n.h || 160) / 2 - 14) : (n.y - 26);
        var t = el("text", {
          x: n.x, y: ly,
          "text-anchor": "middle",
          fill: "var(--dim-d, #A2B7CF)",
          "font-family": 'var(--font, Raleway, "Segoe UI", Arial, sans-serif)',
          "font-size": 26, "font-weight": 700
        });
        t.textContent = n.label;
        gLbl.appendChild(t);
      }
    }

    svg.appendChild(gSeg);
    svg.appendChild(gNode);
    svg.appendChild(gLbl);
    host.innerHTML = "";
    host.appendChild(svg);
    return svg;
  }

  /* ------------------------------------------------ ask the model a question
     The reason a typed topology beats a drawing: the figure can be queried,
     so "what is downstream if this shuts" has an answer the author can check. */
  function downstream(sys, fromId, shutIds) {
    var shut = {}, i;
    for (i = 0; i < (shutIds || []).length; i++) { shut[shutIds[i]] = true; }
    var seen = {}, queue = [fromId], out = [];
    while (queue.length) {
      var cur = queue.shift();
      if (seen[cur]) { continue; }
      seen[cur] = true;
      if (cur !== fromId) { out.push(cur); }
      for (i = 0; i < (sys.segments || []).length; i++) {
        var s = sys.segments[i];
        if (shut[s.from] || shut[s.to] || shut[s.id]) { continue; }
        if (s.from === cur && !seen[s.to]) { queue.push(s.to); }
        if (s.to === cur && !seen[s.from]) { queue.push(s.from); }
      }
    }
    return out;
  }

  function setState(svg, segId, state) {
    var p = svg.querySelector('.cv-seg[data-id="' + segId + '"]');
    if (p) { p.setAttribute("data-state", state); }
  }

  w.CVSchematic = {
    render: render,
    downstream: downstream,
    setState: setState,
    _draw: DRAW
  };
})(window, document);
