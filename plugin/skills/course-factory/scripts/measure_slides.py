#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Measure every slide of many modules in one run, in a hidden browser - for a fix (L50).

    measure_slides.py <deck.html or module folder> [more ...] [--size 1280x800] [--workers 3] [--json out.json]

WHY THIS EXISTS
Before 2.29.0 a sentence like "modules 1-3 have too much free space - find it in the others" sent an agent
into every module: serve it, open it in a browser pane, press Start, press Next to the end, paste a probe,
read the numbers, at two screen sizes - and then a second agent did the same to check the first. On GAS
ADVANCED that was most of the 30 minutes a small fix took (FEEDBACK_LOG #61-#93). This does the walk for
all modules at once, without a window, in about four seconds a module.

HOW
One small web server serves the course (so every module's own links work, never file://); each module's
deck is opened in a hidden Chrome or Edge at exactly the asked screen size (the window is calibrated
first - a hidden window of 1280x800 shows a page of 1264x705). A little script added to the page presses
Start, then Next until nothing changes any more, and measures the active slide after every press, with
the course-module-ux probe `audit_compose.js` for how much of the slide carries content. The browser's
own clock is run fast (virtual time), so the waits after every press cost nothing.

PER SLIDE (the fullest step of it)
  ink           share of the slide that carries content (audit_compose: union of text, pictures, controls)
  empty_bottom  share of the slide's height below the lowest content - "space up and down" (owner, 2026-10-09)
  min_text      the smallest text on the slide in px, SVG text at its real on-screen size
  small_text    how many text runs are under the floor given (--text-floor, default 16)
  overflow      px of content below or right of the slide - content the room never sees
  verdict       audit_compose's COMPOSED / REVIEW / WEAK, with its findings

Standard library only. Exit 0 measured, 1 a module could not be measured, 2 no browser or bad input.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
PROBES = os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-module-ux", "measure", "scripts")
DECK_NAMES = (os.path.join("presentation", "index.html"), "module.html", "index.html")

RUNNER = r"""<script src="/__probe/audit_compose.js"></script><script>
(function () {
  var TOKEN = "%(token)s", FLOOR = %(floor)s, SETTLE = 650;
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  var SKIP = "script,style,noscript,.credit,.srcline,.src,.slide-kind,#chrome,[aria-hidden='true']";
  function shown(el) {
    var cs = getComputedStyle(el);
    return cs.display !== "none" && cs.visibility !== "hidden" && parseFloat(cs.opacity) > 0.05;
  }
  function measure(s) {
    var sr = s.getBoundingClientRect(), min = 999, sample = "", small = 0, low = sr.top, right = sr.left;
    var w = document.createTreeWalker(s, NodeFilter.SHOW_TEXT), n;
    while ((n = w.nextNode())) {
      if (!n.nodeValue.trim()) { continue; }
      var el = n.parentElement;
      if (!el || el.closest(SKIP) || !shown(el)) { continue; }
      var r = el.getBoundingClientRect();
      if (!r.width || !r.height) { continue; }
      var fs = parseFloat(getComputedStyle(el).fontSize), svg = el.closest("svg");
      if (svg && svg.getScreenCTM) { var m = svg.getScreenCTM(); if (!m) { continue; } fs = fs * m.a; }
      if (fs < min) { min = fs; sample = n.nodeValue.trim().slice(0, 40); }
      if (fs < FLOOR) { small++; }
    }
    s.querySelectorAll("*").forEach(function (el) {
      if (el.closest(SKIP)) { return; }
      var r = el.getBoundingClientRect();
      if (r.width < 6 || r.height < 6 || !shown(el)) { return; }
      var own = /^(svg|img|canvas|video|button|input|select|textarea)$/i.test(el.tagName) ||
        Array.prototype.some.call(el.childNodes, function (c) { return c.nodeType === 3 && c.nodeValue.trim(); });
      if (!own) { return; }
      /* something that starts outside the slide is a panel parked off screen on purpose, not a spill */
      if (r.top >= sr.bottom - 1 || r.left >= sr.right - 1) { return; }
      if (r.bottom > low) { low = r.bottom; }
      if (r.right > right) { right = r.right; }
    });
    var c = window.AuditCompose ? AuditCompose.one(s) : {};
    return {
      id: s.id || "", title: s.getAttribute("data-title") || "", kind: s.getAttribute("data-kind") || "",
      script: s.getAttribute("data-script") || "", ink: (typeof c.ink === "number") ? c.ink : null,
      verdict: c.verdict || "", findings: c.findings || [],
      min_text: min === 999 ? null : Math.round(min * 10) / 10, min_text_sample: sample, small_text: small,
      overflow: Math.max(0, Math.round(Math.max(low - sr.bottom, right - sr.right))),
      empty_bottom: sr.height ? Math.max(0, Math.round(1000 * (sr.bottom - low) / sr.height) / 1000) : null
    };
  }
  async function settle() {                  /* the slide as the room sees it once it has come in: every
                                                entrance animation and transition run to its end */
    await wait(SETTLE);
    for (var k = 0; k < 3; k++) {
      (document.getAnimations ? document.getAnimations() : []).forEach(function (an) {
        try { if (an.effect && an.effect.getTiming && isFinite(an.effect.getTiming().iterations)) { an.finish(); } } catch (e) {}
      });
      await wait(120);
    }
  }
  function merge(a, b) {
    if (!a) { b.steps = 1; return b; }
    a.steps++;
    if ((b.ink || 0) > (a.ink || 0)) { a.ink = b.ink; a.verdict = b.verdict; a.findings = b.findings; }
    if (b.min_text !== null && (a.min_text === null || b.min_text < a.min_text)) { a.min_text = b.min_text; a.min_text_sample = b.min_text_sample; }
    a.small_text = Math.max(a.small_text, b.small_text);
    a.overflow = Math.max(a.overflow, b.overflow);
    if (b.empty_bottom !== null && (a.empty_bottom === null || b.empty_bottom < a.empty_bottom)) { a.empty_bottom = b.empty_bottom; }
    return a;
  }
  function probe() {                         /* the probe must be there - a slide with no probe reads as empty */
    if (window.AuditCompose) { return Promise.resolve(true); }
    return new Promise(function (ok) {
      var s = document.createElement("script");
      s.src = "/__probe/audit_compose.js?again=" + Date.now();
      s.onload = function () { ok(!!window.AuditCompose); };
      s.onerror = function () { ok(false); };
      document.head.appendChild(s);
    });
  }
  async function go() {
    var res = { viewport: [innerWidth, innerHeight], slides: [], errors: [] };
    try {
      if (!(await probe()) && !(await probe())) { throw new Error("the measuring probe audit_compose.js did not load"); }
      var C = window.AuditCompose ? AuditCompose.CONFIG : { startBtnSel: "#startBtn", nextBtnSel: "#btnNext", slideSel: ".slide" };
      var all = Array.prototype.slice.call(document.querySelectorAll(C.slideSel || ".slide"));
      var got = {}, order = [], changes = 0;
      new MutationObserver(function (l) { changes += l.length; }).observe(document.body, { attributes: true, childList: true, subtree: true });
      var start = document.querySelector(C.startBtnSel);
      if (start && !document.querySelector(".slide.active")) { start.click(); await wait(SETTLE); }
      var next = document.querySelector(C.nextBtnSel);
      if (next) {
        for (var i = 0; i < 800; i++) {
          var a = document.querySelector(".slide.active");
          if (!a) { break; }
          await settle();
          var key = a.id || ("#" + all.indexOf(a));
          if (!got[key]) { order.push(key); }
          got[key] = merge(got[key], measure(a));
          if (next.disabled) { break; }
          changes = 0; next.click(); await wait(200);
          if (changes === 0 && document.querySelector(".slide.active") === a) { break; }
        }
      }
      var pending = [];
      all.forEach(function (s, i) {            /* a deck with no Next, or slides Next never reached */
        var key = s.id || ("#" + i);
        if (got[key]) { return; }
        all.forEach(function (o) { o.classList.remove("active"); });
        s.classList.add("active"); window.dispatchEvent(new Event("resize"));
        order.push(key); pending.push([key, s]);
      });
      for (var q = 0; q < pending.length; q++) {
        await settle();
        got[pending[q][0]] = measure(pending[q][1]); got[pending[q][0]].steps = 0; got[pending[q][0]].not_reached_by_next = !!next;
      }
      all.forEach(function (s, i) {
        var g = got[s.id || ("#" + i)]; if (g) { g.n = i + 1; res.slides.push(g); }
      });
    } catch (e) { res.errors.push(String(e && e.stack || e)); }
    fetch("/__result/" + TOKEN, { method: "POST", body: JSON.stringify(res) });
  }
  window.addEventListener("load", function () { setTimeout(go, 900); });
})();
</script>"""


def find_browser():
    env = os.environ.get("CF_BROWSER")
    if env and os.path.isfile(env):
        return env
    pf = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    cands = [os.path.join(p, *rest) for p in pf if p for rest in (
        ("Google", "Chrome", "Application", "chrome.exe"), ("Microsoft", "Edge", "Application", "msedge.exe"))]
    cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for c in cands:
        if os.path.isfile(c):
            return c
    for n in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"):
        if shutil.which(n):
            return shutil.which(n)
    return None


def deck_of(path):
    """A deck file, or the deck inside a module folder (L45 presentation/index.html; older module.html)."""
    if os.path.isfile(path):
        return os.path.abspath(path)
    for n in DECK_NAMES:
        p = os.path.join(path, n)
        if os.path.isfile(p):
            return os.path.abspath(p)
    return None


class _Server:
    def __init__(self, root):
        self.root, self.results, self.inject = root, {}, {}
        outer = self

        class H(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def translate_path(self, path):
                if path.startswith("/__probe/"):
                    return os.path.join(PROBES, path.split("?")[0][len("/__probe/"):])
                return super().translate_path(path)

            def do_GET(self):
                p = self.path.split("?")[0]
                if p == "/__calibrate":
                    return self._send(b"<html><body><script>fetch('/__result/' + location.hash.slice(1) || 'cal',"
                                      b"{method:'POST',body:JSON.stringify({viewport:[innerWidth,innerHeight]})})"
                                      b"</script></body></html>")
                tok = self.path.split("cf_token=")[-1] if "cf_token=" in self.path else None
                if tok in outer.inject:
                    t = io.open(self.translate_path(p), encoding="utf-8", errors="replace").read()
                    add = outer.inject[tok]
                    i = t.rfind("</body>")            # the LAST one: a deck's own script may hold "</body>" in a string
                    t = t[:i] + add + t[i:] if i >= 0 else t + add
                    return self._send(t.encode("utf-8"))
                return super().do_GET()

            def _send(self, b):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                outer.results[self.path.rsplit("/", 1)[-1]] = json.loads(self.rfile.read(n) or b"{}")
                self.send_response(204)
                self.end_headers()

        class Quiet(http.server.ThreadingHTTPServer):
            daemon_threads = True

            def handle_error(self, request, client_address):
                pass                                         # the browser closing a connection as it exits

        self.httpd = Quiet(("127.0.0.1", 0), functools.partial(H, directory=root))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d/" % self.httpd.server_address[1]

    def close(self):
        self.httpd.shutdown()


def _open(browser, url, win, token, server, timeout):
    prof = tempfile.mkdtemp(prefix="cf_measure_")
    args = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--mute-audio",
            "--no-default-browser-check", "--user-data-dir=" + prof, "--window-size=%d,%d" % win,
            "--virtual-time-budget=600000", "--dump-dom", url]
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import browser_slots                                     # 2.57.0: one pool of hidden browsers for the whole computer
    with browser_slots.slot():
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.time()
        while token not in server.results and time.time() - t0 < timeout and p.poll() is None:
            time.sleep(0.1)
        for _ in range(20):                                  # the result may land just as the browser exits
            if token in server.results:
                break
            time.sleep(0.1)
        if p.poll() is None:
            p.kill()
        p.wait()
    shutil.rmtree(prof, ignore_errors=True)
    return server.results.pop(token, None)


def calibrate(browser, server, size):
    """The hidden window's page is smaller than the window: find the window that gives exactly `size`."""
    win = size
    for _ in range(3):
        tok = uuid.uuid4().hex
        got = _open(browser, server.base + "__calibrate#" + tok, win, tok, server, 30)
        if not got:
            return size
        vw, vh = got["viewport"]
        if (vw, vh) == size:
            return win
        win = (win[0] + size[0] - vw, win[1] + size[1] - vh)
    return win


def measure(decks, size=(1280, 800), workers=1, text_floor=16, timeout=300, browser=None):
    """{deck path: {"viewport": [w, h], "slides": [...], "errors": [...]} or {"error": "..."}}"""
    browser = browser or find_browser()
    if not browser:
        raise RuntimeError("no Chrome or Edge found on this computer (set CF_BROWSER to the browser's path)")
    decks = [os.path.abspath(d) for d in decks]
    # serve the folder that holds the module folders, so ../assets and ../../_course_shell resolve
    mods = [os.path.dirname(os.path.dirname(d)) if os.path.basename(os.path.dirname(d)) == "presentation"
            else os.path.dirname(d) for d in decks]
    root = os.path.commonpath([os.path.dirname(m) for m in mods])
    server = _Server(root)
    try:
        win = calibrate(browser, server, size)

        def one(d):
            tok = uuid.uuid4().hex
            server.inject[tok] = RUNNER % {"token": tok, "floor": text_floor}
            rel = os.path.relpath(d, root).replace(os.sep, "/")
            got = _open(browser, server.base + rel + "?cf_token=" + tok, win, tok, server, timeout)
            return d, got or {"error": "the page did not finish within %d s (it may be waiting for something)" % timeout}

        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(decks)))) as ex:
            res = dict(ex.map(one, decks))
        # several hidden browsers at once left whole modules reading 0 % on every slide (2.29.0 test on GAS ADVANCED:
        # three of four modules, alone they measure the same to the last per cent every time) - so one at a time
        # is the default, and anything that still comes back broken or mostly empty is measured again, alone
        for d, r in list(res.items()):
            sl = r.get("slides") or []
            if r.get("error") or r.get("errors") or not sl or sum(1 for s in sl if not s.get("ink")) * 2 >= len(sl):
                again = one(d)[1]
                good = lambda x: not x.get("error") and not x.get("errors") and bool(x.get("slides"))
                if good(again) or not good(r):           # never trade a measured result for a failed one
                    res[d] = again
        return res
    finally:
        server.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+", help="deck files or module folders")
    ap.add_argument("--size", default="1280x800")
    ap.add_argument("--workers", type=int, default=1, help="more than 1 is faster but less reliable")
    ap.add_argument("--text-floor", type=float, default=16)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    decks, missing = [], []
    for p in a.paths:
        d = deck_of(p)
        (decks if d else missing).append(d or p)
    for m in missing:
        print("No slides found in %s" % m)
    if not decks:
        return 2
    w, h = (int(x) for x in a.size.lower().split("x"))
    try:
        res = measure(decks, (w, h), a.workers, a.text_floor)
    except RuntimeError as e:
        print("Stopped - %s." % e)
        return 2
    bad = 0
    for d, r in res.items():
        if r.get("error") or r.get("errors"):
            bad += 1
            print("%s: could not be measured - %s" % (d, r.get("error") or r["errors"][0][:300]))
            continue
        print("%s: %d slides at %dx%d" % (d, len(r["slides"]), r["viewport"][0], r["viewport"][1]))
        for s in r["slides"]:
            print("  %3d %-8s ink %3s%%  empty below %3s%%  smallest text %s px (%s)  overflow %s px  %s" % (
                s["n"], s["id"][:8], round(100 * (s["ink"] or 0)), round(100 * (s["empty_bottom"] or 0)),
                s["min_text"], s.get("min_text_sample", "")[:20], s["overflow"], s["title"][:40]))
    if a.json:
        with io.open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
