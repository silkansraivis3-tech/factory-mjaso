#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""run_audits - the three browser probes on a deck, in headless Chrome or Edge, with no browser pane.

    python run_audits.py <deck index.html | folder with one> [--viewport 1920x1080 ...] [--json out.json] [--quiet]

Loads audit_deck.js, audit_collide.js and audit_compose.js into the deck, runs each one's `.all()` in turn at
1280x800 (and at every --viewport given), and prints one compact summary per probe and viewport:

    1280x800  deck     PASS   17 slides
    1280x800  collide  FAIL n=2   slide 4: text-on-text x2
    1280x800  compose  PASS   17 screens (REVIEW 1: 9)

Exit code: 0 every probe passed, 1 at least one probe failed (the summary says which slides), 2 nothing could
be measured (no Chrome or Edge, the page did not answer, a probe aborted). A pass is `window.__auditExit == 0`
- the same contract the probes keep in a browser tab; an abort is a failure, never a pass. compose's REVIEW
screens are listed but do not fail the run (only WEAK does).

The deck is never changed on disk: the page the probes are injected into is written beside it as
`_audit_<pid>.html` (so its relative assets load) and removed again, whatever happens. --json writes the
full result of every probe to the file you name - put it outside the course.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_audit_drawing import browser  # noqa: E402  - the one place that finds Chrome or Edge

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PROBES = (("deck", "audit_deck.js", "AuditDeck"), ("collide", "audit_collide.js", "AuditCollide"),
          ("compose", "audit_compose.js", "AuditCompose"))

RUN = """<script>
(async function(){
 var o={}, names=%s;
 for (var i=0;i<names.length;i++){
  var n=names[i][0], g=window[names[i][1]];
  window.__auditExit=undefined;
  try{ if(!g){o[n]={ABORTED:"probe did not load"}; continue;}
       var r=await g.all(); o[n]={res:r, exit:window.__auditExit}; }
  catch(e){ o[n]={ABORTED:String(e&&e.stack||e)}; }
 }
 o.viewport=[window.innerWidth,window.innerHeight];
 var p=document.createElement('pre');p.id='AUDIT_OUT';p.textContent=JSON.stringify(o);document.body.appendChild(p);
})();
</script>"""


def find_deck(arg):
    p = Path(arg).resolve()
    if p.is_file():
        return p
    for c in (p / "index.html", p / "presentation" / "index.html"):
        if c.is_file():
            return c
    sys.exit("run_audits: no deck at %s (give the deck's index.html, or the folder that holds it)" % arg)


def frame_offset(exe):
    """--window-size is the OUTER size; the page gets less (about 16 x 95 px on Windows). Ask a blank page how
    much, once, so a '1280x800' run really lays the deck out at 1280 x 800."""
    d = tempfile.mkdtemp(prefix="run_audits_cal_")
    try:
        page = Path(d) / "cal.html"
        page.write_text('<body><pre id="o"></pre><script>o.textContent=innerWidth+"x"+innerHeight</script>', encoding="utf-8")
        p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + os.path.join(d, "p"),
                            "--window-size=1280,800", "--virtual-time-budget=1000", "--dump-dom", page.as_uri()],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        m = re.search(r'<pre id="o">(\d+)x(\d+)</pre>', p.stdout)
        return (max(0, 1280 - int(m.group(1))), max(0, 800 - int(m.group(2)))) if m else (0, 0)
    except (subprocess.TimeoutExpired, OSError):
        return 0, 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


def measure(exe, deck, size, budget, offset=(0, 0)):
    """-> (results by probe, error text). The injected page is removed whatever happens."""
    size = (size[0] + offset[0], size[1] + offset[1])
    scripts = "".join('<script src="%s"></script>' % (HERE / js).as_uri() for _, js, _ in PROBES)
    inject = scripts + RUN % json.dumps([[n, g] for n, _, g in PROBES])
    html = deck.read_text(encoding="utf-8")
    i = html.lower().rfind("</body>")
    page = deck.with_name("_audit_%d.html" % os.getpid())
    prof = tempfile.mkdtemp(prefix="run_audits_")
    try:
        page.write_text(html[:i] + inject + html[i:] if i >= 0 else html + inject, encoding="utf-8")
        p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                            "--window-size=%d,%d" % size, "--virtual-time-budget=%d" % budget, "--dump-dom", page.as_uri()],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    except subprocess.TimeoutExpired:
        return None, "the browser did not finish in 15 minutes"
    finally:
        if page.exists():
            page.unlink()
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'<pre id="AUDIT_OUT">(.*?)</pre>', p.stdout, re.S)
    if not m:
        return None, "the page gave no result (the deck may not load, or the budget is too short): " + p.stderr[-200:].strip()
    return json.loads(unescape(m.group(1))), ""


def short(items, n=4):
    items = [str(x) for x in items]
    return ", ".join(items[:n]) + (" +%d" % (len(items) - n) if len(items) > n else "")


def quote(t, n=40):
    t = " ".join(str(t or "").split())
    return ' "%s"' % (t[:n] + ("..." if len(t) > n else "")) if t else ""


def finding(kind, f):
    """one finding of the deck probe as the person needs it to fix it: the element and its words, not a count
    (M01 benchmark run 4: "slide 2: low 1" took a separate run_audits.py --json to find a bold term in the conclusion)"""
    if not isinstance(f, dict):
        return "%s %s" % (kind, f)
    sel = f.get("sel") or f.get("el") or "?"
    if kind == "low":
        return "low contrast %s%s %s:1 (need %s)" % (sel, quote(f.get("txt")), f.get("ratio"), f.get("need"))
    if kind == "small":
        return "small text %s%s %s px" % (sel, quote(f.get("txt")), f.get("px"))
    if kind == "spill":
        return "spills %s by %s px" % (sel, f.get("byPx"))
    if kind == "tap":
        return "small tap target %s %sx%s px" % (sel, f.get("w"), f.get("h"))
    if kind == "svgSmall":
        return "drawing text too small%s %s px on screen" % (quote(f.get("txt")), f.get("effPx", f.get("declaredPx")))
    if kind == "scroll":
        return "scrolls %s by %s px" % (sel, f.get("overflowPx"))
    if kind == "collide":
        return "labels collide %s / %s" % (f.get("a"), f.get("b"))
    return "%s %s" % (kind, sel)


def where(s):
    return "slide %s%s" % (s.get("slide"), " (%s)" % s["id"] if s.get("id") else "")


def summarise(name, rec):
    """-> (status 'PASS'|'FAIL'|'ABORT', one line, [detail lines]) - every detail line names the element and its words"""
    if "ABORTED" in rec:
        return "ABORT", str(rec["ABORTED"]).strip().splitlines()[0][:160], []
    r, ex = rec.get("res") or {}, rec.get("exit")
    if r.get("ABORTED"):
        return "ABORT", str(r["ABORTED"]).strip()[:160], []
    if ex not in (0, 1):
        return "ABORT", "the probe did not set window.__auditExit", []
    lines = []
    if name == "deck":
        for s in r.get("failingSlides") or []:
            bits = [finding(k, f) for k in ("low", "small", "spill", "tap", "svgSmall", "scroll", "collide") for f in s.get(k) or []]
            # a line a stepping figure selects that does not look selected (IGF M05, 2026-10-19)
            bits += ["selected line looks unselected: %s (= %s)" % (m.get("txt") or m.get("sel"), m.get("looksLike"))
                     for m in s.get("mark") or []]
            lines += ["%s: %s" % (where(s), b) for b in bits] or ["%s: failed" % where(s)]
        if r.get("overfilledSlides"):
            lines.append("over-filled: " + short("%s (%s %%)" % (o["slide"], o["fillPct"]) for o in r["overfilledSlides"]))
        if r.get("linksInsideSlides"):
            lines.append("%d link(s) inside slides" % r["linksInsideSlides"])
        if r.get("docHScroll"):
            lines.append("the page scrolls sideways")
        tail = "%s slides" % r.get("slidesTotal", "?")
    elif name == "collide":
        for s in r.get("slides") or r.get("failingSlides") or []:
            if s.get("collisions") or s.get("total") or s.get("n"):
                bits = (["text on text %s%s / %s%s" % (c.get("a"), quote(c.get("aTxt"), 30), c.get("b"), quote(c.get("bTxt"), 30))
                         for c in s.get("text") or []]
                        + ["box on box %s / %s" % (c.get("a"), c.get("b")) for c in s.get("box") or []]
                        + ["text under %s: %s%s" % (c.get("under"), c.get("sel"), quote(c.get("txt"), 30)) for c in s.get("chrome") or []])
                lines += ["%s: %s" % (where(s), b) for b in bits] or ["%s: collision" % where(s)]
        tail = "%s collision(s)" % r.get("totalCollisions", "?")
    else:
        for p in r.get("problems") or []:
            lines.append("screen %s %s%s: %s" % (p.get("n"), p.get("verdict"), (" - " + p["title"]) if p.get("title") else "",
                                                 short((f if isinstance(f, str) else json.dumps(f, ensure_ascii=False)) for f in p.get("findings") or [])))
        review = [p["n"] for p in r.get("problems") or [] if p.get("verdict") == "REVIEW"]
        tail = "%s screens (REVIEW %d%s)" % (r.get("screens", "?"), r.get("review", 0), (": " + short(review, 8)) if review else "")
    word = "PASS" if ex == 0 else "FAIL"
    v = r.get("verdict")
    if ex and isinstance(v, str) and v.startswith("VERDICT:"):
        word = v.replace("VERDICT: ", "")
    elif ex and name == "compose":
        word = "FAIL " + str(v)
    return ("PASS" if ex == 0 else "FAIL"), "%s   %s" % (word, tail), lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--viewport", action="append", default=[], metavar="WxH", help="another viewport; 1280x800 is always run")
    ap.add_argument("--json", metavar="FILE", help="write every probe's full result here (outside the course)")
    ap.add_argument("--budget", type=int, default=240000, help="the browser's virtual-time budget in ms (default 240000)")
    ap.add_argument("--quiet", action="store_true", help="only the failing lines")
    a = ap.parse_args(argv)
    exe = browser()
    if not exe:
        print("run_audits: no Chrome or Edge found - nothing measured")
        return 2
    deck = find_deck(a.deck)
    sizes = []
    for s in ["1280x800"] + a.viewport:
        m = re.fullmatch(r"(\d{3,5})x(\d{3,5})", s.lower())
        if not m:
            sys.exit("run_audits: --viewport wants WxH, like 1920x1080 - not %r" % s)
        if (int(m.group(1)), int(m.group(2))) not in sizes:
            sizes.append((int(m.group(1)), int(m.group(2))))
    worst, full = 0, {}
    offset = frame_offset(exe)
    for size in sizes:
        res, err = measure(exe, deck, size, a.budget, offset)
        label = "%dx%d" % size
        if res is None:
            print("%s  NOT MEASURED  %s" % (label, err))
            worst = 2
            continue
        full[label] = res
        for name, _, _ in PROBES:
            st, line, detail = summarise(name, res.get(name) or {"ABORTED": "no result"})
            worst = max(worst, {"PASS": 0, "FAIL": 1, "ABORT": 2}[st])
            if st == "PASS" and a.quiet:
                continue
            print("%s  %-8s %s" % (label, name, line if st != "ABORT" else "ABORT  " + line))
            for d in detail[:12]:
                print("            " + d)
            if len(detail) > 12:
                print("            ... %d more (--json has them all)" % (len(detail) - 12))
    if a.json:
        Path(a.json).write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")
    print("run_audits: %s" % ("every probe passed" if worst == 0 else "a probe failed" if worst == 1 else "something could not be measured"))
    return worst


if __name__ == "__main__":
    sys.exit(main())
