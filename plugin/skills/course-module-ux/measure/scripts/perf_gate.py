#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""perf_gate - the deck walked as the instructor walks it, on a slowed computer, and every slide timed: does the 3D keep up?

    python perf_gate.py <deck index.html | module folder> [--throttle 4] [--viewport 1280x800] [--dsf 2] [--json out.json]

A module carries a lot of interactive 3D. On the classroom tablet (about 1280 x 800, a mid-range graphics chip, the training
app's WebView) a scene that draws when its slide is not shown, a graphics context kept for every 3D slide passed, or a
picture drawn at the screen's full 2x-3x sharpness makes the whole deck lag. This gate presses Start, then Next to the end,
with the CPU slowed (--throttle, 4x by default) and the screen at the tablet's size and sharpness, and on every slide reads:

  ctx      live WebGL contexts in the page (made and not lost or collected)
  first    ms from Next to the first frame a canvas of the new slide draws (3D slides)
  med/p95  frame times in ms while the slide is up, --ms long (a kit3d scene is turned meanwhile: window.__scene3d.spin)
  hidden   frames drawn by canvases NOT on the slide shown, in that time - a scene that keeps drawing off screen
  heap     the page's JS heap in MB, after a garbage collection

Fails when a 3D slide's p95 is over --p95-ms (33: under 30 frames a second the turn judders), when more than --max-ctx
live contexts (1) are held at once, when a slide's first frame takes over --first-ms (1500), or when canvases off screen
draw more than --max-hidden frames (10) while a slide is up. Only a slide with a scene is judged on its frames; every
slide is judged on contexts and off-screen drawing.

It drives the Chrome or Edge already on the computer through Playwright (python -m pip install playwright). WebGL runs on
this computer's graphics chip (--gl gpu); --gl swiftshader draws in software, as on a computer without one - there a
kit3d scene takes 300-450 ms a frame on any CPU, so use it for contexts and off-screen drawing, not frame times. The CPU
throttle slows scripts, not the graphics chip. Exit 0 within the budget, 1 over it (each slide named), 2 nothing could
be measured. The deck is never changed.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_audit_drawing import browser  # noqa: E402  - the one place that finds Chrome or Edge
sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
import browser_slots  # noqa: E402  - one pool of hidden browsers for the whole computer

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAX_STEPS = 3000
GL_ARGS = {"swiftshader": ["--use-angle=swiftshader", "--use-gl=angle", "--enable-unsafe-swiftshader",
                           "--ignore-gpu-blocklist"],
           "gpu": ["--ignore-gpu-blocklist", "--enable-gpu-rasterization"]}

# before the deck's own scripts: every WebGL context the page makes, and every frame a canvas draws (on the slide shown
# or not); a click on Next marks the time the next first frame is counted from
PROBE = r"""(() => {
  const pg = window.__pg = { refs: [], made: 0, mark: 0, first: 0, hidden: 0, shown: 0 };
  const get = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type) {
    const c = get.apply(this, arguments);
    if (c && /webgl/i.test(String(type)) && !this.__pgCtx) {
      this.__pgCtx = 1; pg.made++;
      pg.refs.push(window.WeakRef ? new WeakRef(c) : { deref: () => c });
    }
    return c;
  };
  function drew(cv) {
    const t = performance.now();
    if (cv.__pgT && t - cv.__pgT < 6) { return; }          /* one count a frame, however many draw calls */
    cv.__pgT = t;
    const s = document.querySelector('.slide.active');
    if (s && s.contains(cv) && cv.offsetWidth > 0) {
      pg.shown++;
      if (pg.mark && !pg.first) { pg.first = t; }
    } else { pg.hidden++; }
  }
  [window.WebGLRenderingContext, window.WebGL2RenderingContext].forEach(function (C) {
    if (!C) { return; }
    ['drawElements', 'drawArrays', 'drawElementsInstanced', 'drawArraysInstanced', 'drawRangeElements'].forEach(function (n) {
      const f = C.prototype[n];
      if (!f) { return; }
      C.prototype[n] = function () { drew(this.canvas); return f.apply(this, arguments); };
    });
  });
  document.addEventListener('click', function (e) {
    if (e.target && e.target.closest && e.target.closest('#btnNext')) { pg.mark = performance.now(); pg.first = 0; }
  }, true);
  pg.live = function () {
    return pg.refs.filter(function (r) { const c = r.deref(); return c && !c.isContextLost(); }).length;
  };
})();"""

SLIDE = """() => { const s = document.querySelector('.slide.active');
  if (!s) { return null; }
  const all = [].slice.call(document.querySelectorAll('.slide'));
  return { id: s.id || String(all.indexOf(s)), index: all.indexOf(s),
           kind: s.querySelector('[data-kit3d]') ? 'kit3d' : s.querySelector('[data-lt-scene]') ? 'scene'
                 : s.querySelector('canvas, [data-3d], [data-scene]') ? 'canvas' : '' }; }"""

# frame times for ms: our own frame loop, while a kit3d scene turns (its window.__scene3d.spin) or a scene plays. The turn
# outlasts the timing: what a scene does when it comes to rest (its labels' full search, a lite switch) is not a turn's frame
SAMPLE = """(ms) => new Promise(function (done) {
  const pg = window.__pg, s = document.querySelector('.slide.active'), sc = window.__scene3d;
  const h0 = pg.hidden, n0 = pg.shown, ts = [];
  if (sc && sc.spin && sc.__k3 && s && s.contains(sc.__k3.stage)) { try { sc.spin(ms + 400, function () {}); } catch (e) {} }
  const t0 = performance.now();
  (function tick(t) {
    ts.push(t);
    if (t - t0 < ms) { requestAnimationFrame(tick); return; }
    const dt = [];
    for (let i = 1; i < ts.length; i++) { dt.push(ts[i] - ts[i - 1]); }
    done({ dt: dt, hidden: pg.hidden - h0, shown: pg.shown - n0 });
  })(t0);
})"""


def find_deck(arg):
    p = Path(arg)
    for d in (p, p / "presentation" / "index.html", p / "index.html"):
        if d.is_file():
            return d.resolve()
    return None


def p95(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def heap(cdp):
    cdp.send("HeapProfiler.collectGarbage")
    return round(cdp.send("Runtime.getHeapUsage")["usedSize"] / 1048576.0, 1)


def measure(page, cdp, o):
    """the load, then one row per slide: {id, index, kind, ctx, first, med, p95, hidden, heap}"""
    page.goto(o.deck.as_uri())
    page.wait_for_timeout(1500)
    rows = [{"id": "(load)", "index": -1, "kind": "", "ctx": page.evaluate("() => __pg.live()"), "first": None,
             "med": None, "p95": None, "hidden": 0, "heap": heap(cdp)}]
    if page.locator("#startBtn").count() and page.locator("#startBtn").is_visible():
        page.click("#startBtn")
    seen, same = set(), 0
    for _ in range(MAX_STEPS):
        page.wait_for_timeout(250)
        s = page.evaluate(SLIDE)
        if not s:
            break
        if s["id"] not in seen:
            seen.add(s["id"])
            first = None
            if s["kind"]:
                for _ in range(int(o.wait_ms / 100)):
                    f = page.evaluate("() => __pg.mark && __pg.first ? __pg.first - __pg.mark : 0")
                    if f:
                        first = round(f)
                        break
                    page.wait_for_timeout(100)
                if first is None and rows and page.evaluate("() => !__pg.mark"):
                    first = 0                               # the first slide: no Next pressed
            r = page.evaluate(SAMPLE, o.ms if s["kind"] else min(o.ms, 600))
            dt = r["dt"][1:] if len(r["dt"]) > 2 else r["dt"]
            rows.append({"id": s["id"], "index": s["index"], "kind": s["kind"], "ctx": page.evaluate("() => __pg.live()"),
                         "first": first if s["kind"] else None,
                         "med": round(statistics.median(dt), 1) if dt else None, "p95": round(p95(dt), 1) if dt else None,
                         "hidden": r["hidden"], "heap": heap(cdp)})
            same = 0
        else:
            same += 1
            if same > 60:                                   # a last slide whose Next never turns off
                break
        nxt = page.locator("#btnNext")
        if not nxt.count() or nxt.is_disabled():
            break
        nxt.click()
    rows.append({"id": "(end)", "index": 10 ** 6, "kind": "", "ctx": page.evaluate("() => __pg.live()"), "first": None,
                 "med": None, "p95": None, "hidden": 0, "heap": heap(cdp),
                 "made": page.evaluate("() => __pg.made")})
    return rows


def judge(rows, o):
    """[(slide id, what)] over the budget"""
    bad = []
    for r in rows:
        if r["ctx"] > o.max_ctx:
            bad.append((r["id"], "%d live WebGL contexts (at most %d)" % (r["ctx"], o.max_ctx)))
        if r["hidden"] > o.max_hidden:
            bad.append((r["id"], "%d frames drawn by canvases not on the slide shown (at most %d)" % (r["hidden"], o.max_hidden)))
        if r["kind"] and r["p95"] is not None and r["p95"] > o.p95_ms:
            bad.append((r["id"], "p95 frame %.1f ms (at most %d)" % (r["p95"], o.p95_ms)))
        if r["kind"] and r["first"] is not None and r["first"] > o.first_ms:
            bad.append((r["id"], "first frame %d ms after Next (at most %d)" % (r["first"], o.first_ms)))
        if r["kind"] and r["first"] is None and r["index"] >= 0 and r["index"] < 10 ** 6:
            bad.append((r["id"], "no frame within %d ms of Next" % o.wait_ms))
    return bad


def table(rows):
    out = ["%-14s %-6s %4s %7s %7s %7s %7s %7s" % ("slide", "3D", "ctx", "first", "med", "p95", "hidden", "heap")]
    for r in rows:
        f = lambda v, fmt: (fmt % v) if v is not None else "-"   # noqa: E731
        out.append("%-14s %-6s %4d %7s %7s %7s %7d %7s" % (r["id"][:14], r["kind"] or "", r["ctx"], f(r["first"], "%d"),
                                                          f(r["med"], "%.1f"), f(r["p95"], "%.1f"), r["hidden"],
                                                          f(r["heap"], "%.1f")))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--viewport", default="1280x800")
    ap.add_argument("--dsf", type=float, default=2.0, help="device pixel ratio of the screen (the tablets: 2)")
    ap.add_argument("--throttle", type=float, default=4.0)
    ap.add_argument("--gl", choices=sorted(GL_ARGS), default="gpu")
    ap.add_argument("--ms", type=int, default=2000, help="how long the frames are timed on a 3D slide")
    ap.add_argument("--wait-ms", type=int, default=8000, help="how long a first frame is waited for")
    ap.add_argument("--p95-ms", type=float, default=33)
    ap.add_argument("--first-ms", type=float, default=1500)
    ap.add_argument("--max-ctx", type=int, default=1)
    ap.add_argument("--max-hidden", type=int, default=10)
    ap.add_argument("--json")
    o = ap.parse_args(argv)
    given, o.deck = o.deck, find_deck(o.deck)
    if not o.deck:
        print("perf_gate: no deck at %s (give the deck's index.html, or the module folder)" % given)
        return 2
    try:
        vw, vh = (int(x) for x in o.viewport.lower().split("x"))
    except ValueError:
        print("perf_gate: --viewport wants WxH, like 1280x800 - not %r" % o.viewport)
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("perf_gate: Playwright is not installed - python -m pip install playwright (it drives the Chrome or Edge "
              "already here, nothing else to download)")
        return 2
    exe = browser()
    if not exe:
        print("perf_gate: no Chrome or Edge found - nothing measured")
        return 2
    try:
        with browser_slots.slot(), sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=exe, headless=True,
                                   args=["--allow-file-access-from-files"] + GL_ARGS[o.gl])
            page = b.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=o.dsf)
            page.add_init_script(PROBE)
            cdp = page.context.new_cdp_session(page)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": o.throttle})
            rows = measure(page, cdp, o)
            b.close()
    except Exception as err:                                # the browser did not start or the page did not answer
        print("perf_gate: could not measure %s - %s" % (o.deck, str(err).splitlines()[0] if str(err) else type(err).__name__))
        return 2
    bad = judge(rows, o)
    if o.json:
        Path(o.json).write_text(json.dumps({"deck": str(o.deck), "viewport": o.viewport, "dsf": o.dsf, "throttle": o.throttle,
                                            "gl": o.gl, "rows": rows, "over": bad}, indent=1), encoding="utf-8")
    print(table(rows))
    scenes = [r for r in rows if r["kind"]]
    print("%s  %d slides, %d with 3D, contexts made %d, most live %d, worst p95 %.1f ms, heap %.1f -> %.1f MB  (%gx CPU, %s, %gx)"
          % (o.viewport, len(rows) - 2, len(scenes), rows[-1].get("made", 0), max(r["ctx"] for r in rows),
             max([r["p95"] for r in scenes if r["p95"] is not None] or [0]), rows[0]["heap"], rows[-1]["heap"],
             o.throttle, o.gl, o.dsf))
    for sid, what in bad[:40]:
        print("  %s  %s" % (sid, what))
    if len(bad) > 40:
        print("  ... and %d more" % (len(bad) - 40))
    print("perf_gate: %s" % ("PASS - the 3D keeps up" if not bad else "FAIL %d slide(s), %d finding(s) - the 3D lags on the "
                                                                      "tablet; see the slides named above"
                                                                      % (len(set(s for s, _ in bad)), len(bad))))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
