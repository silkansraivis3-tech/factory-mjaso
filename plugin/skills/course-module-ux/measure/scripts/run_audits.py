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
import time
from html import unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_audit_drawing import browser  # noqa: E402  - the one place that finds Chrome or Edge
sys.path.insert(0, str(HERE.parents[2] / "course-factory" / "scripts"))
import browser_slots  # noqa: E402  - one pool of hidden browsers for the whole computer (2.57.0)
import cf_timing  # noqa: E402  - CF_TIMING: each run's real seconds and the page's own clock (2.61.0)
import check_cache  # noqa: E402  - a slide audited clean is not measured again until it changes (2.57.0)

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
       var r=await g.all(%s); o[n]={res:r, exit:window.__auditExit}; }
  catch(e){ o[n]={ABORTED:String(e&&e.stack||e)}; }
 }
 o.viewport=[window.innerWidth,window.innerHeight]; o.virt=Math.round(performance.now());
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
        p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + os.path.join(d, "p"),
                               "--window-size=1280,800", "--virtual-time-budget=1000", "--dump-dom", page.as_uri()],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        m = re.search(r'<pre id="o">(\d+)x(\d+)</pre>', p.stdout)
        return (max(0, 1280 - int(m.group(1))), max(0, 800 - int(m.group(2)))) if m else (0, 0)
    except (subprocess.TimeoutExpired, OSError):
        return 0, 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


def measure(exe, deck, size, budget, offset=(0, 0), only=None):
    """-> (results by probe, error text). The injected page is removed whatever happens. only = [slide index from 0, ...]:
    the whole deck is loaded, just those slides are measured (2.57.0)"""
    size = (size[0] + offset[0], size[1] + offset[1])
    scripts = "".join('<script src="%s"></script>' % (HERE / js).as_uri() for _, js, _ in PROBES)
    inject = scripts + RUN % (json.dumps([[n, g] for n, _, g in PROBES]), json.dumps(only))
    html = deck.read_text(encoding="utf-8")
    i = html.lower().rfind("</body>")
    page = deck.with_name("_audit_%d_%dx%d.html" % ((os.getpid(),) + tuple(size)))     # one per viewport: they run side by side
    prof = tempfile.mkdtemp(prefix="run_audits_")
    t0 = t1 = time.time()
    try:
        page.write_text(html[:i] + inject + html[i:] if i >= 0 else html + inject, encoding="utf-8")
        # 2.62.1 - a limit from the slides measured (a deck's audit takes 6-30 s), not 15 minutes, and a timeout ends the
        # browser's whole process tree: a stalled page held a build 600-900 s and its processes outlived the kill
        n = len(only) if only is not None else len(re.findall(r'<section\b[^>]*\bclass="[^"]*\bslide\b', html))
        limit = min(900, 120 + 15 * n)
        with browser_slots.slot():
            t1 = time.time()
            p = browser_slots.run_tree([exe, "--headless=new", "--disable-gpu", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                                        "--window-size=%d,%d" % size, "--virtual-time-budget=%d" % budget, "--dump-dom", page.as_uri()],
                                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=limit)
    except subprocess.TimeoutExpired:
        return None, "the browser did not finish in %d s - a slide's own script may never let the page settle" % limit
    finally:
        if page.exists():
            page.unlink()
        shutil.rmtree(prof, ignore_errors=True)
    m = re.search(r'<pre id="AUDIT_OUT">(.*?)</pre>', p.stdout, re.S)
    res = json.loads(unescape(m.group(1))) if m else None
    cf_timing.note("run_audits", "%dx%d %s" % (size[0] - offset[0], size[1] - offset[1], "slides %s" % len(only) if only else "whole"),
                   time.time() - t1, queued=round(t1 - t0, 3), virt=(res or {}).get("virt"))
    if not m:
        return None, "the page gave no result (the deck may not load, or the budget is too short): " + p.stderr[-200:].strip()
    return res, ""


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
    if kind == "strip":
        return ("photo cropped to a strip %s: %s %% of its %s shows in a %s frame - give it more height (the words in parts), "
                "another layout, or a photo of that shape" % (sel, f.get("pct"), f.get("side"), f.get("box")))
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
            bits = [finding(k, f) for k in ("low", "small", "spill", "tap", "strip", "svgSmall", "scroll", "collide") for f in s.get(k) or []]
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
                        + ["text under %s: %s%s" % (c.get("under"), c.get("sel"), quote(c.get("txt"), 30)) for c in s.get("chrome") or []]
                        + ["text cut off %s%s: %s px of it hidden by its box" % (c.get("sel"), quote(c.get("txt"), 30), c.get("px"))
                           for c in s.get("cut") or []])
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


def slides_hit(res):
    """{slide index from 0} that any probe found something on - None when a finding cannot be put on one slide (an abort,
    the page scrolling sideways, a failure with no slide named): then no slide of the run is recorded clean. A compose
    REVIEW screen counts too, so it is listed on every run"""
    hit = set()
    for name, _, _ in PROBES:
        rec = res.get(name) or {}
        r, ex = rec.get("res") or {}, rec.get("exit")
        if "ABORTED" in rec or r.get("ABORTED") or ex not in (0, 1):
            return None
        if name == "deck":
            if r.get("linksInsideSlides") or r.get("docHScroll"):
                return None
            found = [s.get("slide") for s in (r.get("failingSlides") or []) + (r.get("overfilledSlides") or [])]
        elif name == "collide":
            found = [s.get("slide") for s in r.get("slides") or r.get("failingSlides") or []
                     if s.get("collisions") or s.get("total") or s.get("n")]
        else:
            found = [p.get("n") for p in r.get("problems") or []]
        if not all(isinstance(x, int) for x in found) or (ex == 1 and not found):
            return None
        hit |= {x - 1 for x in found}
    return hit


def counted(res):
    """how many slides each probe saw (the deck's and collide's slidesTotal, compose's screens)"""
    return {((res.get(n) or {}).get("res") or {}).get("slidesTotal" if n != "compose" else "screens") for n, _, _ in PROBES}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck")
    ap.add_argument("--viewport", action="append", default=[], metavar="WxH", help="another viewport; 1280x800 is always run")
    ap.add_argument("--json", metavar="FILE", help="write every probe's full result here (outside the course)")
    ap.add_argument("--budget", type=int, default=240000, help="the browser's virtual-time budget in ms (default 240000)")
    ap.add_argument("--quiet", action="store_true", help="only the failing lines")
    ap.add_argument("--cache", metavar="FILE", help="the slides last audited clean (2.57.0): a slide unchanged in everything "
                                                    "it loads since is not measured again (outside the course)")
    ap.add_argument("--full", action="store_true", help="with --cache: measure every slide again (and record the clean ones)")
    ap.add_argument("--jobs", type=int, default=0, help="viewports measured at once (default: all of them, each taking a slot "
                                                       "of the computer's pool of hidden browsers; 1 = one after the other)")
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
    store, judged = check_cache.Cache(a.cache, use=not a.full), []
    salt = check_cache.salt(*[str(HERE / js) for _, js, _ in PROBES], __file__,
                            extra="%s|%d|%s" % (check_cache.browser_id(exe), a.budget, offset))
    fps = check_cache.fingerprints(str(deck), True, salt) if a.cache else None

    def viewport(size):
        """one viewport measured: (label, units, slides to judge [] = none, only, result, error). 2.61.0: the viewports
        run side by side, each in its own thread and hidden browser (a slot of the computer's pool each)"""
        label = "%dx%d" % size
        units = [("%s#%d" % (label, k), check_cache.sha(fp, label)) for k, (_, fp) in enumerate(fps)] if fps else None
        todo = [k for k, (key, fp) in enumerate(units) if not store.clean(key, fp)] if units else None
        if todo == []:
            return label, units, todo, None, None, ""
        only = todo if units and len(todo) < len(units) else None
        res, err = measure(exe, deck, size, a.budget, offset) if only is None else measure(exe, deck, size, a.budget, offset, only)
        if res is not None and units and counted(res) != {len(units)}:
            # the browser counted the slides differently from the fingerprints: measured whole, nothing recorded
            if only is not None:
                res, err = measure(exe, deck, size, a.budget, offset)
            units, only = None, None
        return label, units, todo, only, res, err
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=max(1, min(len(sizes), a.jobs or len(sizes)))) as ex:
        measured = list(ex.map(viewport, sizes))
    # what each viewport found is recorded and said in the viewports' order, as when they ran one after the other
    for label, units, todo, only, res, err in measured:
        if todo == []:
            judged.append("0 of %d slides at %s" % (len(units), label))
            if not a.quiet:
                print("%s  unchanged  every slide clean at its last audit (%d slides) - not measured again" % (label, len(units)))
            continue
        if res is None:
            print("%s  NOT MEASURED  %s" % (label, err))
            worst = 2
            continue
        full[label] = res
        if units:
            judged.append("%d of %d slides at %s" % (len(only or units), len(units), label))
            hit = slides_hit(res)
            for k in (only if only is not None else range(len(units))):
                (store.bad(units[k][0]) if hit is None or k in hit else store.ok(*units[k]))
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
    store.save()
    if a.json:
        Path(a.json).write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")
    print("run_audits: %s%s" % ("every probe passed" if worst == 0 else "a probe failed" if worst == 1 else "something could not be measured",
                                " (measured %s; the rest unchanged since their last clean audit)" % ", ".join(judged) if judged else ""))
    return worst


if __name__ == "__main__":
    sys.exit(main())
