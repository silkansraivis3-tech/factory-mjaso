#!/usr/bin/env python3
"""test_kit3d.py - the 3D kit in a hidden browser: does it build, put its labels on the parts, fill its box, select a
part from its label and from a tap, walk its steps with the deck's Next, go full screen, share one WebGL context with the
deck's other scenes, and say so without WebGL?

    python -I test_kit3d.py

Serves plugin/skills on a free local port, drives headless Chrome with shot3d.mjs (one browser per run, from the
computer's pool), and reads each scene's own report (KIT3D api .info()). Needs Node and Chrome; ~1-2 minutes.
"""
from __future__ import annotations

import functools
import glob
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
SKILLS = os.path.dirname(os.path.dirname(KIT))
SHOT = os.path.join(HERE, "shot3d.mjs")
FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "  -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


class Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):     # a browser that closes its connection early is not a test failure
        pass


srv = Server(("127.0.0.1", 0), functools.partial(Quiet, directory=SKILLS))
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:%d/" % srv.server_address[1]
STUDIO = BASE + "course-visuals/kit3d/studio3d.html?spec=examples/%s.kit3d.json&w=%d&h=%d"

# helpers in the page: labels whose dot is off their part; pills that overlap each other, the controls or the box edge
HELP = r"""window.T3 = {
  off: function () {
    var S = k3.scene, out = [], p = new THREE.Vector3();
    S.labels.forEach(function (l) {
      if (!l.shown || !l.key || !S.parts[l.key] || S.parts[l.key].box.isEmpty()) return;
      var b = S.parts[l.key].box, x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, i, sx, sy;
      for (i = 0; i < 8; i++) {
        p.set(i & 1 ? b.max.x : b.min.x, i & 2 ? b.max.y : b.min.y, i & 4 ? b.max.z : b.min.z).project(S.camera);
        sx = (p.x * 0.5 + 0.5) * S.W; sy = (-p.y * 0.5 + 0.5) * S.H;
        x0 = Math.min(x0, sx); x1 = Math.max(x1, sx); y0 = Math.min(y0, sy); y1 = Math.max(y1, sy);
      }
      if (!(l.sx >= x0 - 24 && l.sx <= x1 + 24 && l.sy >= y0 - 24 && l.sy <= y1 + 24)) out.push(l.text);
    });
    return out;
  },
  overlaps: function () {
    var S = k3.scene, wr = S.wrap.getBoundingClientRect(), out = [], rs = [];
    [].forEach.call(S.wrap.querySelectorAll('.k3-lab:not(.k3-off) .k3-pill'), function (e) { rs.push([e.textContent, e.getBoundingClientRect()]); });
    var ctl = S.ctl.offsetWidth ? S.ctl.getBoundingClientRect() : null;
    function hit(a, b) { return a.left < b.right - 2 && b.left < a.right - 2 && a.top < b.bottom - 2 && b.top < a.bottom - 2; }
    rs.forEach(function (a, i) {
      if (a[1].left < wr.left - 1 || a[1].right > wr.right + 1 || a[1].top < wr.top - 1 || a[1].bottom > wr.bottom + 1) out.push(a[0] + ' / the box edge');
      if (ctl && hit(a[1], ctl)) out.push(a[0] + ' / the controls');
      rs.slice(i + 1).forEach(function (b) { if (hit(a[1], b[1])) out.push(a[0] + ' / ' + b[0]); });
    });
    return out;
  },
  shown: function () { return k3.info().labels.filter(function (l) { return l.shown; }).map(function (l) { return l.text; }); }
};"""


def run(plan, *args):
    """the plan's shots in one browser -> one dict per shot (probe parsed from JSON)"""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(plan, f)
    try:
        p = subprocess.run(["node", SHOT, f.name] + list(args), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=400)
    finally:
        os.remove(f.name)
    out = []
    for line in p.stdout.splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r.get("probe"), str):
            try:
                r["probe"] = json.loads(r["probe"])
            except ValueError:
                pass
        out.append(r)
    if len(out) < len(plan):
        out += [{"error": "no answer: " + (p.stderr or p.stdout)[-300:]}] * (len(plan) - len(out))
    return out


J = "JSON.stringify(%s)"
INFO = "(function(i){return {ok:i.ok,warn:i.warnings,calls:i.calls,tri:i.triangles,parts:i.parts,fill:i.fill,size:i.size,step:i.step," \
       "sel:i.selected,states:i.states,view:i.view,off:T3.off(),over:T3.overlaps(),shown:T3.shown()}})(k3.info())"

# ---------------------------------------------------------------- the M01 port at a slide's size: build, labels, steps, select, tap
r = run([
    {"url": STUDIO % ("m01_hull", 1280, 720), "wait": "window.k3ready", "do": HELP, "settle": 500, "probe": J % INFO},
    {"do": "k3.step(1)", "settle": 1300, "probe": J % ("(function(o){o.btn=k3.scene.btns[0].getAttribute('aria-pressed');return o})(%s)" % INFO)},
    {"do": "k3.step(0)", "settle": 1300, "probe": J % INFO},
    {"do": "document.querySelector('.k3-pill[data-3d-part=\"tank\"]').click()", "settle": 1200,
     "probe": J % ("(function(o){var p=document.querySelector('.k3-pill[data-3d-part=\"tank\"]');o.hl=p.className;o.pressed=p.getAttribute('aria-pressed');o.role=p.getAttribute('role');return o})(%s)" % INFO)},
    {"do": "document.querySelector('.k3-pill[data-3d-part=\"tank\"]').click()", "settle": 1200, "probe": J % INFO},
    {"do": "(function(){var S=k3.scene,c=new THREE.Vector3();S.parts.tank.box.getCenter(c);c.project(S.camera);var r=S.wrap.getBoundingClientRect();"
           "k3.tap(r.left+(c.x*0.5+0.5)*S.W, r.top+(-c.y*0.5+0.5)*S.H);})()", "settle": 1200, "probe": J % INFO},
    {"do": ["k3.select(null)", "k3.scene.labelsBtn.click()"], "settle": 1000,
     "probe": J % "(function(){k3.render();return {n:T3.shown().length,pressed:k3.scene.labelsBtn.getAttribute('aria-pressed')}})()"},
    {"do": "k3.scene.labelsBtn.click()", "settle": 400,
     "probe": J % "(function(){k3.render();return {n:T3.shown().length,pressed:k3.scene.labelsBtn.getAttribute('aria-pressed')}})()"},
], "--w=1280", "--h=720")
a = r[0].get("probe") or {}
check("M01 builds with no warning and no page error", a.get("ok") and not a.get("warn") and not r[0].get("errors"), r[0])
check("M01 has its parts and sub-parts", set(["tank", "tcs", "fpr", "er", "pipe", "inner", "annulus", "outer", "lng"]) <= set(a.get("parts") or []), a.get("parts"))
check("M01 is merged to few draw calls (< 120)", 0 < (a.get("calls") or 0) < 120, a.get("calls"))
check("M01 has the hand-made scene's detail (> 10,000 triangles)", (a.get("triangles") or a.get("tri") or 0) > 10000, a.get("tri"))
check("M01 fills its box (>= 80 % of the width)", (a.get("fill") or {}).get("w", 0) >= 0.8, a.get("fill"))
check("M01 labels stand on their parts", a.get("off") == [], a.get("off"))
check("M01 labels touch nothing (each other, the controls, the box edge)", a.get("over") == [], a.get("over"))
check("M01 shows its 7+ labels", len(a.get("shown") or []) >= 7, a.get("shown"))
b = r[1].get("probe") or {}
check("step 2: the pipe is cut open", (b.get("states") or {}).get("pipe.cut") == 1, b.get("states"))
check("step 2: the cut pipe's own labels show", "Inner pipe: gas" in (b.get("shown") or []), b.get("shown"))
check("step 2: the control that cuts the pipe shows pressed", b.get("btn") == "true", b.get("btn"))
check("step 2: the labels stand on their parts and touch nothing", b.get("off") == [] and b.get("over") == [], (b.get("off"), b.get("over")))
c = r[2].get("probe") or {}
check("back to step 1: the pipe closed, its inner labels gone", (c.get("states") or {}).get("pipe.cut") == 0 and "Inner pipe: gas" not in (c.get("shown") or []), c)
d = r[3].get("probe") or {}
check("a label selects its part (outside a deck: the kit's own button)", d.get("sel") == "tank" and "k3-hl" in (d.get("hl") or "")
      and d.get("pressed") == "true" and d.get("role") == "button", d)
check("the selected part is framed (the camera moves in)", (d.get("view") or {}).get("zoom", 1) < 0.9, d.get("view"))
e = r[4].get("probe") or {}
check("the label again lets it go", e.get("sel") is None and abs((e.get("view") or {}).get("zoom", 0) - 1) < 0.02, e)
f = r[5].get("probe") or {}
check("a tap on the tank selects the tank (or its liquid)", f.get("sel") in ("tank", "lng"), f.get("sel"))
g, h = r[6].get("probe") or {}, r[7].get("probe") or {}
check("the Labels button hides every label (the class names the parts)", g.get("n") == 0 and g.get("pressed") == "false", g)
check("the Labels button again shows them", h.get("n", 0) >= 7 and h.get("pressed") == "true", h)

# ---------------------------------------------------------------- framing at other sizes (a small column, a portrait tablet)
r = run([
    {"url": STUDIO % ("m01_hull", 690, 418), "wait": "window.k3ready", "do": HELP, "settle": 500, "probe": J % INFO},
    {"url": STUDIO % ("m01_hull", 600, 800), "wait": "window.k3ready", "do": HELP, "settle": 500, "probe": J % INFO},
], "--w=1280", "--h=900")
for i, what in enumerate(("a small slide column 690 x 418", "a portrait box 600 x 800")):
    a = r[i].get("probe") or {}
    check("framing in %s: the hull fills the width (>= 75 %%)" % what, (a.get("fill") or {}).get("w", 0) >= 0.75, a.get("fill"))
    check("framing in %s: labels on their parts, touching nothing" % what, a.get("off") == [] and a.get("over") == [], (a.get("off"), a.get("over")))

# ---------------------------------------------------------------- full screen outside a deck (the kit's own button)
r = run([
    {"url": STUDIO % ("m01_hull", 800, 500), "wait": "window.k3ready", "do": HELP, "settle": 300,
     "probe": J % "(function(){var b=document.querySelector('.k3-fs');return {btn:!!b,w:b&&b.offsetWidth,h:b&&b.offsetHeight}})()"},
    {"do": "document.querySelector('.k3-fs').click()", "settle": 900,
     "probe": J % "(function(){k3.render();var s=document.getElementById('stage').getBoundingClientRect();return {w:s.width,h:s.height,size:k3.info().size,pressed:document.querySelector('.k3-fs').getAttribute('aria-pressed'),over:T3.overlaps()}})()"},
    {"do": "document.querySelector('.k3-fs').click()", "settle": 900,
     "probe": J % "(function(){k3.render();return {size:k3.info().size,pressed:document.querySelector('.k3-fs').getAttribute('aria-pressed')}})()"},
], "--w=1280", "--h=720")
a, b, c = (x.get("probe") or {} for x in r)
check("outside a deck the scene has a 44 px Full screen button", a.get("btn") and a.get("w", 0) >= 44 and a.get("h", 0) >= 44, a)
check("Full screen: the scene fills the window and redraws at that size", b.get("w", 0) >= 1270 and (b.get("size") or [0])[0] >= 1270
      and b.get("pressed") == "true", b)
check("Full screen: the labels still touch nothing", b.get("over") == [], b.get("over"))
check("the button again leaves full screen", (c.get("size") or [0])[0] == 800 and c.get("pressed") == "false", c)

# ---------------------------------------------------------------- every part in the kit (the catalogue) and its states
r = run([
    {"url": STUDIO % ("catalogue", 1280, 720), "wait": "window.k3ready", "do": HELP, "settle": 400,
     "probe": J % "(function(){var S=k3.scene,e=[];Object.keys(S.parts).forEach(function(k){var p=S.parts[k];if(p.type!=='gas'&&p.type!=='flow'&&(!p.box||p.box.isEmpty()||isNaN(p.box.min.x)))e.push(k)});"
                  "var t={};Object.keys(S.parts).forEach(function(k){if(S.parts[k].type)t[S.parts[k].type]=1});return {warn:k3.info().warnings,empty:e,types:Object.keys(t),all:Object.keys(KIT3D.types())}})()"},
    {"do": "k3.step(1)", "settle": 2200, "probe": J % "k3.info().states"},
], "--w=1280", "--h=720")
a, b = (x.get("probe") or {} for x in r)
check("the catalogue builds every part with no warning and no page error", not a.get("warn") and not r[0].get("errors") and not r[1].get("errors"),
      (a.get("warn"), r[0].get("errors"), r[1].get("errors")))
check("the catalogue has one of every part type the kit defines", set(a.get("all") or ["?"]) <= set(a.get("types") or []),
      sorted(set(a.get("all") or []) - set(a.get("types") or [])))
check("every part draws something (a box to frame)", a.get("empty") == [], a.get("empty"))
check("every state a step sets arrives (cut, open, alarm, shut, gas, flow)", all(b.get(k) == 1 for k in
      ("pipe_dw.cut", "tcs.open", "detector.alarm", "valve_act.shut", "gas.on", "plume.on", "flow.on", "relief.open", "tank_c.ghost")), b)

# ---------------------------------------------------------------- in a deck: built ahead, Next walks the steps, the deck wires the labels
DECK = BASE + "course-visuals/kit3d/scripts/fixtures/deck_kit3d.html"
API = "document.querySelector('[data-kit3d]').__k3"
r = run([
    {"url": DECK, "wait": "document.getElementById('startBtn')", "do": ["document.getElementById('startBtn').click()"], "settle": 1500,
     "probe": J % "(function(){return {n:document.querySelectorAll('#s2 .k3-lab').length,drawn:document.querySelectorAll('#s2 .k3-lab:not(.k3-off)').length}})()"},
    {"do": "document.getElementById('btnNext').click()", "settle": 1200,
     "probe": J % ("(function(){var i=%s.info(),sc=window.__scene3d||{};return {active:document.querySelector('.slide.active').id,first:sc.firstFrameT>0,prepared:!!sc.prepared,"
                   "wired:i.wired,fs:!!document.querySelector('#s2 .gb-fs3d-btn'),step:i.step,line1:document.querySelector('[data-i=\"1\"]').className}})()" % API)},
    {"do": "document.getElementById('btnNext').click()", "settle": 1300,
     "probe": J % ("(function(){var i=%s.info();return {active:document.querySelector('.slide.active').id,step:i.step,cut:i.states['pipe.cut'],line2:document.querySelector('[data-i=\"2\"]').className}})()" % API)},
    {"do": "document.querySelector('#s2 .k3-pill[data-3d-part=\"tank\"]').click()", "settle": 1200,
     "probe": J % ("(function(){var p=document.querySelector('#s2 .k3-pill[data-3d-part=\"tank\"]');return {sel:%s.current(),pressed:p.getAttribute('aria-pressed'),cls:p.className,role:p.getAttribute('role')}})()" % API)},
    {"do": ["document.querySelector('#s2 .k3-pill[data-3d-part=\"tank\"]').click()", "document.getElementById('btnNext').click()"], "settle": 600,
     "probe": J % "document.querySelector('.slide.active').id"},
    {"do": "document.getElementById('btnPrev').click()", "settle": 900,
     "probe": J % ("(function(){return {active:document.querySelector('.slide.active').id,step:%s.info().step}})()" % API)},
], "--w=1280", "--h=800")
a, b, c, d, e = (x.get("probe") or {} for x in r[1:])
ahead = r[0].get("probe") or {}
check("in a deck: a scene built ahead draws none of its label boxes until it is shown (none stacked on one spot)",
      ahead.get("n", 0) > 0 and ahead.get("drawn") == 0, ahead)
check("in a deck: the scene is built ahead on the slide before and draws on entering", a.get("active") == "s2" and a.get("first") and a.get("prepared"), a)
check("in a deck: the labels are wired to the deck (GB3D.wire) and the box has the deck's Full screen button", a.get("wired") and a.get("fs"), a)
check("in a deck: step 1 lights the slide's line 1", a.get("step") == 0 and "cur" in (a.get("line1") or ""), a)
check("in a deck: Next walks the scene's step - the pipe cut, line 2 lit, the slide kept", b.get("active") == "s2" and b.get("step") == 1
      and b.get("cut") == 1 and "cur" in (b.get("line2") or ""), b)
check("in a deck: a label is the deck's button for its part", c.get("sel") == "tank" and c.get("pressed") == "true" and c.get("role") == "button", c)
check("in a deck: Next after the last step turns the slide", d == "s3", d)
check("in a deck: Back returns to the scene", e.get("active") == "s2", e)
check("in a deck: no page error", not any(x.get("errors") for x in r), [x.get("errors") for x in r])

# ---------------------------------------------------------------- steps that name no line: the lines walk with them (M01 s11)
NOLINES = BASE + "course-visuals/kit3d/scripts/fixtures/deck_kit3d_nolines.html"
LIT = J % ("(function(){return {active:document.querySelector('.slide.active').id,step:%s.info().step,"
           "cur:[].map.call(document.querySelectorAll('#s2 [data-i].cur'),function(x){return x.getAttribute('data-i')}),"
           "lit:[].map.call(document.querySelectorAll('#s2 [data-i].lit'),function(x){return x.getAttribute('data-i')})}})()" % API)
r = run([
    {"url": NOLINES, "wait": "document.getElementById('startBtn')", "do": ["document.getElementById('startBtn').click()"], "settle": 1500,
     "probe": J % "document.querySelector('.slide.active').id"},
    {"do": "document.getElementById('btnNext').click()", "settle": 1200, "probe": LIT},
    {"do": "document.getElementById('btnNext').click()", "settle": 1300, "probe": LIT},
    {"do": "document.getElementById('btnNext').click()", "settle": 1300, "probe": LIT},
    {"do": "document.getElementById('btnPrev').click()", "settle": 1300, "probe": LIT},
    {"do": ["document.getElementById('btnNext').click()", "document.getElementById('btnNext').click()"], "settle": 900,
     "probe": J % "document.querySelector('.slide.active').id"},
], "--w=1280", "--h=800")
a, b, c, d, e = (x.get("probe") or {} for x in r[1:])
check("steps that name no line: the slide opens with its first line lit and the scene at its first step",
      a.get("active") == "s2" and a.get("step") == 0 and a.get("cur") == ["1"], a)
check("... each Next walks the scene one step and the lit line one line (the lines before it marked as read)",
      b.get("step") == 1 and b.get("cur") == ["2"] and b.get("lit") == ["1"] and c.get("step") == 2 and c.get("cur") == ["3"], (b, c))
check("... Back walks both back", d.get("step") == 1 and d.get("cur") == ["2"], d)
check("... and Next after the last of them turns the slide", e == "s3", e)
check("... no page error", not any(x.get("errors") for x in r), [x.get("errors") for x in r])

# ---------------------------------------------------------------- the fit gate waits for a scene to stand before it measures
# (M01 s02 at 1024 x 768: a pill pushed past the box after the walk had measured the slide - the build never saw it cut)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "course-module-ux", "measure", "scripts"))
import fit_gate  # noqa: E402
TURN = J % ("(%s)()" % fit_gate.TURNING)
r = run([
    {"url": NOLINES, "wait": "document.getElementById('startBtn')", "do": ["document.getElementById('startBtn').click()"], "settle": 1500,
     "probe": J % "document.querySelector('.slide.active').id"},
    {"do": "document.getElementById('btnNext').click()", "settle": 2000, "probe": TURN},
    {"do": "document.getElementById('btnNext').click(); window.__turning = (%s)()" % fit_gate.TURNING, "settle": 0,
     "probe": J % "window.__turning"},
    {"do": "0", "settle": 2000, "probe": TURN},
], "--w=1280", "--h=800")
a, b, c = (x.get("probe") for x in r[1:])
check("fit gate: a scene standing at its step, its labels laid, is measured at once", a is False, a)
check("... a scene still turning to its next step is waited for", b is True, b)
check("... and measured once it stands", c is False, c)

# ---------------------------------------------------------------- many scenes in a deck: ONE WebGL context, memory given back
MANY = BASE + "course-visuals/kit3d/scripts/fixtures/deck_kit3d_many.html"
MP = J % ("(function(){var o={active:document.querySelector('.slide.active').id,canvases:document.querySelectorAll('canvas').length,"
          "scenes:{}},a=KIT3D.all().map(function(x){return x.scene;}),r0=null;a.forEach(function(S){"
          "var k=S.stage.getAttribute('data-kit3d').slice(4);if(S.r&&!S.own){if(!r0)r0=S.r;if(S.r!==r0)o.split=true;}"
          "o.scenes[k]={live:!!S.live,prepared:!!S.prepared,own:!!S.own,frames:S.frames}});return o;})()")
NEXT, BACK = "document.getElementById('btnNext').click()", "document.getElementById('btnPrev').click()"
r = run([
    {"url": MANY, "wait": "document.getElementById('startBtn')", "do": ["document.getElementById('startBtn').click()"], "settle": 1200, "probe": MP},
    {"do": NEXT, "settle": 900, "probe": MP},
    {"do": [NEXT, NEXT], "settle": 900, "probe": MP},
    {"do": [NEXT, NEXT], "settle": 1200, "probe": MP},
    {"do": NEXT, "settle": 900, "probe": MP},
    {"do": [BACK, BACK, BACK, BACK, BACK], "settle": 1200, "probe": MP},
], "--w=1280", "--h=800")
m = [x.get("probe") or {} for x in r]
sc = [x.get("scenes") or {} for x in m]
check("many scenes: the scene of the next slide is built ahead, and no canvas is drawn yet",
      (sc[0].get("m2") or {}).get("prepared") and m[0].get("canvases", 9) <= 1, m[0])
check("many scenes: every scene draws with ONE renderer - one canvas in the page", m[1].get("active") == "m2"
      and (sc[1].get("m2") or {}).get("frames", 0) > 0 and m[1].get("canvases") == 1 and not m[1].get("split"), m[1])
check("many scenes: two slides on, the first scene gave its graphics memory back; still one canvas", m[2].get("active") == "m4"
      and not (sc[2].get("m2") or {}).get("prepared") and (sc[2].get("m4") or {}).get("frames", 0) > 0
      and m[2].get("canvases") == 1 and not m[2].get("split"), m[2])
check("many scenes: two scenes on one slide both draw - the second with a renderer of its own while it is shown",
      m[3].get("active") == "m6" and all((sc[3].get(k) or {}).get("frames", 0) > 0 for k in ("m6a", "m6b"))
      and (sc[3].get("m6b") or {}).get("own") and m[3].get("canvases") == 2, m[3])
check("many scenes: leaving that slide gives the second renderer back - one canvas again",
      m[4].get("active") == "m7" and not (sc[4].get("m6b") or {}).get("own") and m[4].get("canvases") == 1, m[4])
check("many scenes: Back to a scene that gave its memory back draws it again",
      m[5].get("active") == "m2" and (sc[5].get("m2") or {}).get("live")
      and (sc[5].get("m2") or {}).get("frames", 0) > (sc[1].get("m2") or {}).get("frames", 0), m[5])
check("many scenes: no page error", not any(x.get("errors") for x in r), [x.get("errors") for x in r])

# ---------------------------------------------------------------- no WebGL: it says so, nothing breaks
r = run([{"url": STUDIO % ("m01_hull", 800, 500), "settle": 3000,
          "probe": J % "(function(){var i=window.k3&&k3.info();return {ok:i&&i.ok,msg:(document.querySelector('.k3-msg')||{}).textContent||''}})()"}],
        "--gl=none")
a = r[0].get("probe") or {}
check("without WebGL the scene says it cannot show, with no page error", a.get("ok") is False and "not available" in a.get("msg", "")
      and not r[0].get("errors"), r[0])

# ---------------------------------------------------------------- 2.68.0 the ground shadow: under a model with no floor, never doubling a floor
GROUND = os.path.join(KIT, "examples", "_t_ground.kit3d.json")
with open(GROUND, "w", encoding="utf-8") as f:
    json.dump({"label": "test: a tank standing on nothing", "units": "m",
               "parts": [{"id": "tank", "type": "tank_c", "at": [0, 5, 0], "r": 3, "len": 10, "head": 1.5}]}, f)
GP = J % "(function(){var g=k3.scene.groundMesh;return {ok:k3.info().ok,g:!!g,vis:!!(g&&g.visible),dpr:k3.scene.r.getPixelRatio()}})()"
try:
    r = run([
        {"url": STUDIO % ("_t_ground", 800, 500), "wait": "window.k3ready", "settle": 400, "probe": GP},
        {"url": STUDIO % ("m03_station", 800, 500), "wait": "window.k3ready", "settle": 400, "probe": GP},
        {"url": (STUDIO % ("m02_tank", 800, 500)), "wait": "window.k3ready", "settle": 300,
         "do": "(function(){var S=k3.scene,t=0;S.r.setPixelRatio(2);for(var i=0;i<22;i++){t+=60;S.steady(true,t);}})()",
         "probe": J % "(function(){return {dpr:k3.scene.r.getPixelRatio(),seen:window.__scene3d&&window.__scene3d.dpr}})()"},
        {"url": (STUDIO % ("m02_tank", 800, 500)), "wait": "window.k3ready", "settle": 300,
         "do": "(function(){var S=k3.scene,t=0;S.r.setPixelRatio(2);for(var i=0;i<40;i++){t+=16;S.steady(true,t);}})()",
         "probe": J % "(function(){return {dpr:k3.scene.r.getPixelRatio()}})()"},
        {"url": (STUDIO % ("m02_tank", 800, 500)), "wait": "window.k3ready", "settle": 300,
         "do": "(function(){Object.defineProperty(window,'devicePixelRatio',{value:2,configurable:true});var S=k3.scene;"
               "S.bufW=0;S.size(760,480);window.__p1=S.r.getPixelRatio();S.bufW=0;S.size(1280,800);window.__p2=S.r.getPixelRatio();})()",
         "probe": J % "({box:window.__p1,full:window.__p2})"},
        {"url": (STUDIO % ("m02_tank", 800, 500)), "wait": "window.k3ready", "settle": 300,
         "do": "(function(){var S=k3.scene,t=0;window.__l0=S.lite;S.r.setPixelRatio(1.5);for(var i=0;i<22;i++){t+=40;S.steady(true,t);}"
               "window.__due=S.lite;S.steady(false,t);"
               "window.__l1={lite:S.lite,dpr:S.r.getPixelRatio(),env:!!S.scene.environment,sh:S.r.shadowMap.enabled,"
               "mem:localStorage.getItem('kit3d.lite')};localStorage.removeItem('kit3d.lite');})()",
         "probe": J % "({before:window.__l0,turning:window.__due,after:window.__l1})"},
    ], "--w=900", "--h=600")
finally:
    os.remove(GROUND)
pb = r[4].get("probe") or {}
check("2.70.0 the pixel budget on a 2x screen: a slide's box keeps 2x, full screen 1280 x 800 is drawn at 1.5x",
      pb.get("box") == 2 and pb.get("full") == 1.5, pb)
a, b, c, d = [x.get("probe") or {} for x in r[:4]]
check("a model with no floor stands on a soft ground shadow", a.get("ok") and a.get("g") and a.get("vis"), (a, r[0].get("errors")))
check("a model with its own deck or floor gets no second ground", not b.get("vis"), b)
check("a slow screen (frames of 60 ms) is drawn one step less sharp: 2 -> 1.5", c.get("dpr") == 1.5, c)
check("a fast screen (frames of 16 ms) keeps its sharpness", d.get("dpr") == 2, d)
pl = r[5].get("probe") or {}
la = pl.get("after") or {}
check("2.75.2 a slow screen at 1.5x (frames of 40 ms) goes lite before it loses sharpness - when the turn stops, not in it "
      "(its shaders are compiled again) - and the device is remembered",
      pl.get("before") is False and pl.get("turning") is False and la.get("lite") is True and la.get("dpr") == 1.5 and not la.get("env") and not la.get("sh")
      and la.get("mem") == "1", pl)

# ---------------------------------------------------------------- a label whose point is just past the picture's edge
EDGE = ("(function(){var S=k3.scene,l=S.labels.filter(function(x){return x.shown;})[0];"
        "l.v=new THREE.Vector3(0,1.04,0.5).unproject(S.camera);S.updateLabels();"
        "var p=l.pill.getBoundingClientRect(),w=S.wrap.getBoundingClientRect();"
        "return JSON.stringify({text:l.text,shown:l.shown,cut:l.shown&&p.top<w.top-1});})()")
r = run([{"url": STUDIO % ("m01_hull", 1280, 720), "wait": "window.k3ready", "do": HELP, "settle": 500, "probe": EDGE}],
        "--w=1280", "--h=720")
ed = r[0].get("probe") or {}
check("a label whose point is just above the picture is hidden, not cut at the box's edge (the factory trial: a step that "
      "framed one tank left its neighbour's name cut off)", ed.get("text") and ed.get("shown") is False, (ed, r[0].get("errors")))

# ---------------------------------------------------------------- the picked part is the clearest thing on the screen
# (the factory trial: the select look washed the part to a pale see-through blue, the least visible thing in M01, M08, M19)
LOOK = ("(function(){var S=k3.scene,lum=function(c){return c.r+c.g+c.b;},out={};"
        "var mats=function(id){return S.parts[id].mats.filter(function(m){return m.userData.c0&&!m.userData.glow;});};"
        "var asWas=function(id){return mats(id).every(function(m){return m.color.equals(m.userData.c0)&&Math.abs(m.opacity-m.userData.o0)<1e-6;});};"
        "var a=mats('tank'),b=mats('tcs'),c=mats('pipe_outer');"
        "k3.select('tank');k3.render();out.own=a.every(function(m){return m.color.equals(m.userData.c0);});"
        "out.lit=a.filter(function(m){return m.emissive;}).every(function(m){return m.emissiveIntensity>0;});"
        "out.back=b.every(function(m){return lum(m.color)<lum(m.userData.c0)||lum(m.userData.c0)===0;});"
        "k3.select('pipe_outer');k3.render();"
        "out.solid=c.filter(function(m){return m.userData.o0<1;}).map(function(m){return [m.userData.o0,m.opacity];});"
        "k3.select(null);k3.render();out.rest=asWas('tank')&&asWas('tcs')&&asWas('pipe_outer');return JSON.stringify(out);})()")
r = run([{"url": STUDIO % ("m02_tank", 900, 560), "wait": "window.k3ready", "settle": 300, "probe": LOOK}], "--w=900", "--h=560")
lk = r[0].get("probe") or {}
check("a picked part keeps its own colour and is lit from within (no wash to pale blue)", lk.get("own") and lk.get("lit"), (lk, r[0].get("errors")))
check("... a see-through part turns more solid", lk.get("solid") and all(o > o0 + 0.2 for o0, o in lk["solid"]), lk.get("solid"))
check("... the parts not picked step back (darker)", lk.get("back"), lk)
check("... and let go, every part is as it was", lk.get("rest"), lk)

# ---------------------------------------------------------------- every example spec passes the checker
specs = sorted(glob.glob(os.path.join(KIT, "examples", "*.kit3d.json")))
p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "check_kit3d.py"), "spec"] + specs, capture_output=True, text=True)
check("check_kit3d.py passes every example (%d)" % len(specs), p.returncode == 0, p.stdout[-400:])

# ---------------------------------------------------------------- the labels in a turn: placed only when something moved
# (the factory trial's M01 s22 / s27: a membrane tank corner peeled layer by layer, five labels on thin layers - each search
# for their places took up to 200 ms at 4x CPU, made every 100 ms of a turn: p95 three frames in perf_gate)
LAYERS = os.path.join(KIT, "examples", "_t_layers.kit3d.json")
with open(LAYERS, "w", encoding="utf-8") as f:
    json.dump({"label": "test: a membrane tank corner, layer by layer", "units": "m", "view": {"az": 24, "el": 23},
               "parts": [{"id": "hull", "type": "hull", "pick": False, "x": [-6, 6], "half": 7, "bottom": 0, "floor": 1.2, "top": 12,
                          "near": 0.12, "bottom_id": "dbt", "side_id": "ballast"},
                         {"id": "mt", "type": "tank_prism", "at": [0, 6.4, 0], "size": [10, 8, 10], "kind": "membrane", "fill": 0.5,
                          "layers": [{"id": "ins2", "name": "Insulation", "t": 0.5, "mat": "insulation"},
                                     {"id": "sec", "name": "Secondary membrane", "t": 0.05, "mat": "barrier"},
                                     {"id": "ins1", "name": "Insulation", "t": 0.5, "mat": "insulation"},
                                     {"id": "prim", "name": "Primary membrane", "t": 0.05, "mat": "membrane"}]}],
               "labels": [{"part": "prim", "text": "Primary membrane", "up": 56}, {"part": "ins1", "text": "Insulation", "up": 40},
                          {"part": "sec", "text": "Secondary membrane", "up": -40}, {"part": "ins2", "text": "Insulation", "up": 40},
                          {"part": "ballast", "text": "Ballast tank", "up": 40}]}, f)
TURN = ("(function(){var S=k3.scene,places=function(){return S.labels.map(function(l){var r=l.pill.getBoundingClientRect();"
        "return [l.text,l.shown,Math.round(r.left),Math.round(r.top)];});};"
        "var p0=places(),az=S.view.az,n=0,k=S.keepOut,searches=0,t0;S.keepOut=function(){n++;return k.apply(S,arguments);};"
        "S.setCost=50;t0=S.setT;"
        "for(var i=0;i<20;i++){S.view.az+=0.01;S.frame();if(S.setT!==t0){searches++;t0=S.setT;}}"
        "var turnReads=n;S.view.az=az;S.frame();S.frame();var p1=places();n=0;"
        "var tf=S.labels.map(function(l){return l.el.style.transform;}).join();for(var j=0;j<5;j++){S.frame();}"
        "S.keepOut=k;"
        "return JSON.stringify({p0:p0,p1:p1,searches:searches,turnReads:turnReads,standReads:n,"
        "same:tf===S.labels.map(function(l){return l.el.style.transform;}).join()});})()")
try:
    r = run([{"url": STUDIO % ("_t_layers", 900, 600), "wait": "window.k3ready", "settle": 800, "probe": TURN}], "--w=900", "--h=600")
finally:
    os.remove(LAYERS)
tn = r[0].get("probe") or {}
check("in a turn whose label search is slow, the labels follow their points and are not searched again; the page is not "
      "read for the controls' places", tn.get("searches") == 0 and tn.get("turnReads") == 0, (tn, r[0].get("errors")))
check("... back at rest, every label is exactly where it stood before the turn",
      tn.get("p0") and tn.get("p0") == tn.get("p1") and any(x[1] for x in tn.get("p0")), (tn.get("p0"), tn.get("p1")))
check("... and a standing view drawn again reads nothing and writes nothing for its labels",
      tn.get("standReads") == 0 and tn.get("same") is True, tn)

srv.shutdown()
print()
print("ALL PASS" if not FAILS else "%d FAILED: %s" % (len(FAILS), "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
