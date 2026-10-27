# -*- coding: utf-8 -*-
"""Every drawing the compiler builds is checked for parts poking out - by itself, at every build (L54).

    drawing_check.py <page.html> [<page.html> ...]      check pages by hand (exit 1 when anything is found)

WHY THIS EXISTS
audit_drawing.js finds a part poking out of the hull, tank, room or box it sits in, a part cut off at the drawing's
edge, a label crowding a line, a drawing lost in empty space, and (2.44.0) a part of a figure-kit drawing that cannot
be seen against the figure's dark panel (navy or steel text and lines, coloured for a light slide). Until 2.35.0 someone had to remember to run it in a
browser - and a task page never was: the IGF pilot's Module 1 check shipped an engine room sticking out of the stern.
compile_module.py now runs it on every page it writes - the deck slide by slide, a task page question by question,
each drawing as the trainee sees it (moved into its question, its labels hidden) - in a hidden Chrome or Edge at
1280 x 800, and every finding is a problem to fix before the module is shown.

2.48.0: the page really is 1280 x 800 (a hidden browser's page is smaller than its window: it was 1264 x 705); a kit
figure in a deck is judged at the end of every step, not only at step 0; and a kit figure's words under 12.5 px are a
finding (SMALL TEXT). A kit figure is tried alone, in seconds, with course-visuals/kit/scripts/studio.py.

A crossing that is meant is marked in the drawing, so the reason is written down: data-may-cross, data-no-contain,
data-may-overlap (course-module-ux/measure/scripts/audit_drawing.js).

No Chrome or Edge on the computer (or CF_BROWSER pointing at one): the check says plainly that it did not run.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
AUDIT = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "audit_drawing.js")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from measure_slides import find_browser  # noqa: E402
import browser_slots  # noqa: E402
import cf_timing  # noqa: E402
import check_cache  # noqa: E402

SIZE = (1280, 800)
OUT = "__audit_out"
KEEP = ("check", "where", "part", "other", "detail")
# r.virt: the page's own clock at the end (virtual ms under the budget) - cf_timing.py sets it beside the real seconds
WRITE = ("function __done(r){r.virt=Math.round(performance.now());var p=document.createElement('pre');p.id='%s';p.textContent=JSON.stringify(r);"
         "document.body.appendChild(p);}"
         "function __keep(f,pre){return {check:f.check,where:(pre||'')+f.where,part:f.part,other:f.other||'',detail:f.detail||''};}" % OUT)
# a deck: every slide in turn, as the deck shows it (audit_drawing.js all() presses Start). 2.56.0: a long deck is checked
# in slices side by side - each browser keeps only its slides and the finding's slide number is put back. Put
# in <head>, before the page is read: a slide not kept is taken out as the parser adds it, so neither the deck
# nor the figure kit ever lays it out (removing it after the load left every browser drawing the whole deck).
# 2.57.0: the slides kept are a list (the ones changed since their last clean check), and the browser says how many
# slides it counted, so a deck the fingerprints split differently is checked whole instead
SLICE = ("<script>(function(){var i=0,K=%s;window.__cfSlides=0;new MutationObserver(function(ms){ms.forEach(function(m){"
         "[].forEach.call(m.addedNodes,function(n){if(n.nodeType===1&&n.classList&&n.classList.contains('slide')"
         "&&!(n.parentNode&&n.parentNode.closest&&n.parentNode.closest('.slide'))){if(!K[i]){n.parentNode.removeChild(n);}"
         "i++;window.__cfSlides=i;}});"
         "});}).observe(document.documentElement,{childList:true,subtree:true});})();</script>")
DECK = WRITE + ("setTimeout(function(){AuditDrawing.all().then(function(r){"
                "__done({drawings:r.drawings||0,aborted:r.ABORTED||'',seen:window.__cfSlides,"
                "findings:(r.findings||[]).map(function(f){return __keep(f)})});"
                "},function(e){__done({error:String(e)})});},300);")
# a task page: every question that shows a picture, with the shared drawing moved into it - as gb_answer.js does
TASK = WRITE + ("setTimeout(function(){try{var out=[],n=0,ab='';"
                "[].forEach.call(document.querySelectorAll('.scr[data-script]'),function(s){"
                " if(!s.querySelector('.ga, img, svg')){return;}"
                " [].forEach.call(document.querySelectorAll('.scr'),function(x){x.classList.remove('on');});s.classList.add('on');"
                " [].forEach.call(s.querySelectorAll('.ga[data-fig]'),function(h){var v=document.querySelector("
                "'svg.taskfig[data-fig=\"'+h.getAttribute('data-fig')+'\"]');if(v&&v.parentNode!==h){h.insertBefore(v,h.firstChild);}});"
                " var r=AuditDrawing.page();n+=r.drawings||0;if(r.ABORTED){ab=r.ABORTED;}"
                " (r.findings||[]).forEach(function(f){out.push(__keep(f,s.getAttribute('data-script')+', '));});});"
                "__done({drawings:n,aborted:ab,findings:out});}catch(e){__done({error:String(e)});}},300);")


def wrapper(page, deck, keep=None):
    """the page as it is, read from its own folder (<base>), with the probe and its runner added at the end;
    keep = [slide index, ...] (from 0) keeps only those slides of a deck"""
    text = io.open(page, encoding="utf-8").read()
    base = '<base href="%s/">' % Path(os.path.dirname(os.path.abspath(page))).as_uri()
    kept = SLICE % json.dumps({str(i): 1 for i in keep}) if deck and keep is not None else ""
    text = re.sub(r"<head>", lambda m: "<head>" + base + kept, text, count=1, flags=re.I)
    tail = '<script src="%s"></script><script>%s</script>' % (Path(AUDIT).as_uri(), DECK if deck else TASK)
    i = text.lower().rfind("</body>")
    return text[:i] + tail + text[i:] if i >= 0 else text + tail


_WIN = {}


def window_for(exe, size=SIZE):
    """the window that gives a page of exactly `size` (2.48.0): a hidden Chrome's page is smaller than its window -
    --window-size=1280,800 gave a 1264 x 705 page, so every drawing used to be checked smaller than the tablet shows it.
    Measured once per run, then the same difference for every size."""
    if "d" not in _WIN:
        tmp = tempfile.mkdtemp(prefix="cf_cal_")
        try:
            f = os.path.join(tmp, "cal.html")
            io.open(f, "w", encoding="utf-8").write("<html><body><script>var p=document.createElement('pre');p.id='cal';"
                                                    "p.textContent=innerWidth+'x'+innerHeight;document.body.appendChild(p)</script></body></html>")
            p = browser_slots.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--user-data-dir=" +
                                   os.path.join(tmp, "p"), "--window-size=1280,800", "--dump-dom", Path(f).as_uri()],
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            m = re.search(r'<pre id="cal">(\d+)x(\d+)</pre>', p.stdout or "")
            _WIN["d"] = (1280 - int(m.group(1)), 800 - int(m.group(2))) if m else (0, 0)
        except (OSError, subprocess.TimeoutExpired):
            _WIN["d"] = (0, 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return size[0] + _WIN["d"][0], size[1] + _WIN["d"][1]


def is_deck(page):
    return os.path.basename(page).lower() == "index.html" and os.path.basename(os.path.dirname(page)).lower() == "presentation"


SLIDE_TAG = check_cache.SLIDE_TAG
DRAWN = re.compile(r"<(?:svg|img|canvas|video|object|iframe)\b|\bdata-kit", re.I)   # what this check can judge on a page (2.70.0)


def slices(page, jobs, todo=None):
    """a deck's slides cut into lists for `jobs` browsers (at least 3 slides each); [None] = the page whole.
    todo = the slides to check (2.57.0: the ones changed since their last clean check), else every slide"""
    if not is_deck(page):
        return [None]
    n = len(SLIDE_TAG.findall(io.open(page, encoding="utf-8").read()))
    todo = list(range(n)) if todo is None else todo
    if len(todo) == n and (jobs < 2 or n <= max(3, -(-n // jobs))):
        return [None]
    per = max(3, -(-len(todo) // max(1, jobs)))
    return [todo[k:k + per] for k in range(0, len(todo), per)]


def renumber(res, keep):
    """a slice's findings with the deck's own slide numbers ("slide 2 (s05)" of the slides [9, 11, 12] is slide 12)"""
    if keep is None:
        return res
    for f in res.get("findings", []):
        f["where"] = re.sub(r"^slide (\d+)", lambda m: "slide %d" % (keep[int(m.group(1)) - 1] + 1)
                            if 0 < int(m.group(1)) <= len(keep) else m.group(0), f.get("where", ""))
    return res


def time_limit(page, keep):
    """seconds a hidden browser may take for this piece of work (2.62.1): a slide takes 1-3 s and a 3-slide piece 4-10 s,
    so a stalled page is stopped in about a minute, not 600 s (IGF M01, 2.62.0: slides 3-5 with a 3D scene held the
    build for 600 s twice). A single slide 45 s (CF_DRAWING_SLIDE_SECONDS), a piece of n slides 45 x (1 + 0.45 n) - 106 s for
    three - at most 600; a task page 60 s"""
    try:
        one = float(os.environ.get("CF_DRAWING_SLIDE_SECONDS") or 45)
    except ValueError:
        one = 45.0
    if not is_deck(page):
        return one * 4 / 3
    n = len(keep) if keep is not None else len(SLIDE_TAG.findall(io.open(page, encoding="utf-8").read()))
    return one if n == 1 else min(600, one * (1 + 0.45 * n))


def run_page(exe, page, prof, tmp, keep=None):
    deck = is_deck(page)
    w = os.path.join(tmp, "check_%d_%s.html" % (abs(hash(page)), "-".join(map(str, keep[:1] + keep[-1:])) if keep else "all"))
    io.open(w, "w", encoding="utf-8").write(wrapper(page, deck, keep))
    t0 = time.time()
    try:
        with browser_slots.slot():
            t1 = time.time()
            # --disable-3d-apis (2.62.1): the drawing check judges drawings and words, never a WebGL render - a 3D scene
            # shows its poster, as on a tablet without WebGL. Software WebGL was the stalled pages' one common part, and the
            # check of three slides with a 3D scene took 3.7 s instead of 9.8 s
            p = browser_slots.run_tree([exe, "--headless=new", "--disable-gpu", "--disable-3d-apis", "--hide-scrollbars", "--no-first-run",
                                "--mute-audio", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                                "--window-size=%d,%d" % window_for(exe), "--virtual-time-budget=%d" % (120000 if deck else 8000),
                                "--dump-dom", Path(w).as_uri()],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=time_limit(page, keep))
    except subprocess.TimeoutExpired as err:
        return {"error": "the hidden browser did not finish in %.0f s" % err.timeout, "timeout": True}
    except OSError as err:
        return {"error": str(err)}
    m = re.search(r'<pre id="%s">(.*?)</pre>' % OUT, p.stdout, re.S)
    try:
        res = json.loads(html.unescape(m.group(1))) if m else {"error": "the page did not finish loading in the hidden browser"}
    except ValueError:
        res = {"error": "the probe's answer could not be read"}
    cf_timing.note("drawing_check", "%s %s" % (os.path.basename(os.path.dirname(page)) + "/" + os.path.basename(page),
                                               "slides %d-%d (%d)" % (keep[0] + 1, keep[-1] + 1, len(keep)) if keep else "whole"),
                   time.time() - t1, queued=round(t1 - t0, 3), virt=res.get("virt"), drawings=res.get("drawings"))
    return res


def jobs_for(n):
    """how many hidden browsers check at once (2.56.0): the deck in slices and every task page side by side, each its own
    browser with its own profile - half the computer's cores, at most 8, CF_DRAWING_JOBS to set it (1 = one page at a
    time, the deck whole, as before). The findings are the same and come back in the pages' and slides' order."""
    try:
        want = int(os.environ.get("CF_DRAWING_JOBS") or 0)
    except ValueError:
        want = 0
    return max(1, min(n, want or min(8, max(1, (os.cpu_count() or 2) // 2))))


LAST = {}      # what the last check() judged: {"slides": (judged, of), "pages": (judged, of)} - for the build's note


def check(pages, root=None, cache=None, full=False):
    """(problems, a note when the check could not run) for the built pages.
    cache = a JSON file of the slides and task pages last judged clean (check_cache.py, 2.57.0): one whose fingerprint
    is unchanged is not judged again; full = judge every one (and record the clean ones)"""
    LAST.clear()
    exe = find_browser()
    if not exe:
        return [], ("the drawing check (parts poking out, cut off, crowded labels) did not run - no Chrome or Edge on this "
                    "computer; set CF_BROWSER to one, or run AuditDrawing.page() / .all() by hand in a browser")
    probs = []
    prof, tmp = tempfile.mkdtemp(prefix="cf_drawing_"), tempfile.mkdtemp(prefix="cf_pages_")
    store = check_cache.Cache(cache, use=not full)
    try:
        window_for(exe)                      # measured once, before the pages run side by side
        salt = check_cache.salt(AUDIT, os.path.abspath(__file__), extra="%s|%dx%d" % (check_cache.browser_id(exe), *window_for(exe)))
        prints, todo = {}, {}
        for page in pages:                   # [(unit key, fingerprint)] per page, and the slides to judge (None = all)
            fps = check_cache.fingerprints(page, is_deck(page), salt) if cache else None
            name = os.path.relpath(page, root).replace("\\", "/") if root else page
            prints[page] = [("%s#%d" % (name, k), fp) for k, (_, fp) in enumerate(fps)] if fps else None
            todo[page] = None if not fps else [k for k, (key, fp) in enumerate(prints[page]) if not store.clean(key, fp)]
            # 2.70.0 - a page with nothing drawn on it (no svg, picture, canvas, video or kit figure - an instructor's plan,
            # an answer key) has nothing for this check to judge: no browser for it (gas M15 on 2.67: 48 s and 21 s, plus
            # up to 80 s waiting for a browser slot, on two pages that reported "drawings": 0)
            if not is_deck(page) and not DRAWN.search(io.open(page, encoding="utf-8").read()):
                todo[page] = []
        slides = [p for p in pages if is_deck(p)]
        n_sl = sum(len(prints[p]) if prints[p] else len(SLIDE_TAG.findall(io.open(p, encoding="utf-8").read())) for p in slides)
        LAST["slides"] = (sum(len(todo[p]) if todo[p] is not None else len(SLIDE_TAG.findall(io.open(p, encoding="utf-8").read()))
                              for p in slides), n_sl)
        LAST["pages"] = (sum(1 for p in pages if not is_deck(p) and todo[p] != []), len(pages) - len(slides))
        import concurrent.futures as cf
        n = jobs_for(8)

        def judge(work):
            if not work:
                return []
            with cf.ThreadPoolExecutor(max_workers=min(n, len(work))) as ex:
                # a browser locks its profile folder: one per piece of work
                return list(ex.map(lambda iw: renumber(run_page(exe, iw[1][0], os.path.join(prof, "p%d_%d" % (len(work), iw[0])),
                                                                tmp, iw[1][1]), iw[1][1]), enumerate(work)))
        # a deck whose results are recorded always runs with the counting script (every slide kept when it runs whole), so
        # a finding's "slide N" is known to be the fingerprints' slide N
        work = [(page, list(range(len(prints[page]))) if keep is None and prints[page] and is_deck(page) else keep)
                for page in pages if todo[page] != [] for keep in slices(page, n, todo[page])]
        got = judge(work)
        # a deck the browser counted differently from its fingerprints (a slide in a slide, an odd tag): judged whole
        odd = sorted({p for (p, keep), r in zip(work, got) if keep is not None and not r.get("error")
                      and r.get("seen") != (len(prints[p]) if prints[p] else len(SLIDE_TAG.findall(io.open(p, encoding="utf-8").read())))})
        if odd:
            work, got = [w for w in work if w[0] not in odd], [r for w, r in zip(work, got) if w[0] not in odd]
            again = [(p, None) for p in odd]
            work, got = work + again, got + judge(again)
            for p in odd:
                prints[p] = None
        # 2.62.1 - a piece that ran out of time: its slides one by one, so the slide that stalls is named and the others
        # are still judged
        k = 0
        while k < len(work):
            (page, keep), r = work[k], got[k]
            if r.get("timeout") and keep and len(keep) > 1:
                singles = [(page, [x]) for x in keep]
                work[k:k + 1], got[k:k + 1] = singles, judge(singles)
                k += len(singles)
            else:
                k += 1
        done = []                            # one answer per page, its slices joined in slide order
        for page in pages:
            parts = [(keep, r) for (p, keep), r in zip(work, got) if p == page]
            stalls = [keep[0] for keep, r in parts if r.get("timeout") and keep and len(keep) == 1]
            bad = [r for keep, r in parts if (r.get("error") and not (r.get("timeout") and keep and len(keep) == 1))
                   or r.get("aborted")]
            done.append(bad[0] if bad else {"drawings": sum(r.get("drawings", 0) for _, r in parts), "stalls": stalls,
                                            "findings": [f for _, r in parts for f in r.get("findings", [])]})
            # 2.57.0 - what was judged clean is recorded; a slide or page with a finding, or that did not finish, is not
            units = prints.get(page)
            if not units:
                continue
            judged = [k for keep, _ in parts for k in (keep if keep is not None else range(len(units)))]
            if bad:
                hit = set(judged)
            elif is_deck(page):
                nums = [re.match(r"slide (\d+)", f.get("where", "")) for f in done[-1]["findings"]]
                hit = set(judged) if not all(nums) else {int(m.group(1)) - 1 for m in nums}
                hit |= set(done[-1].get("stalls") or [])        # a slide that stalled is judged again next time
            else:
                hit = set(judged) if done[-1]["findings"] else set()
            for k in judged:
                (store.bad(units[k][0]) if k in hit else store.ok(*units[k]))
        store.save()
        for page, res in zip(pages, done):
            name = os.path.relpath(page, root).replace("\\", "/") if root else page
            if res.get("error") or res.get("aborted"):
                probs.append("%s: the drawing check could not finish - %s" % (name, res.get("error") or res.get("aborted")))
                continue
            for k in res.get("stalls") or []:
                probs.append("%s, slide %d: stalls the hidden browser - the page never settles in %.0f s, so its drawings were not "
                             "judged (the other slides were); look at what this slide runs - a 3D scene or a module script that "
                             "never lets the page finish - and open the slide alone in a browser" % (name, k + 1, time_limit(page, [k])))
            for f in res.get("findings", []):
                if f.get("check") == "contrast":     # a kit figure's part that cannot be seen on its dark panel (finding 13)
                    probs.append("%s, %s: contrast - %s %s (L54: colour the part for the figure's dark panel, or mark one "
                                 "meant to be quiet data-low-contrast)" % (name, f.get("where"), f.get("part"), f.get("detail")))
                    continue
                if f.get("check") == "small text":   # a kit figure's word under 12.5 px at 1280 x 800 (2.48.0)
                    probs.append("%s, %s: small text - %s %s (try the figure in the studio: course-visuals\\kit\\scripts\\"
                                 "studio.py <figure>.kit.json)" % (name, f.get("where"), f.get("part"), f.get("detail")))
                    continue
                if f.get("check") == "photo over drawing":   # a real photo hiding the drawing it sits on (IGF M02, 2.49.6)
                    probs.append("%s, %s: photo over drawing - %s covers %s (L54: a photo goes beside the drawing - its own "
                                 "column in the figure or an .inset - never on it; data-may-overlap does not excuse a photo)"
                                 % (name, f.get("where"), f.get("part"), f.get("other")))
                    continue
                if f.get("check") == "inset":        # a photo laid "over" a kit drawing, its caption or credit on words or controls (2.60.0)
                    probs.append("%s, %s: inset - %s: %s - %s (move \"over\" to a blank corner of the drawing, keep the credit "
                                 "short, or put the photo beside the drawing: \"inset\" without \"over\")"
                                 % (name, f.get("where"), f.get("part"), f.get("detail"), f.get("other")))
                    continue
                if f.get("check") == "empty":        # judged at the figure's busiest step; the finding names the blank piece (2.49.1)
                    probs.append("%s, %s: empty - %s: %s (see every step at once: course-visuals\\kit\\scripts\\studio.py "
                                 "<figure>.kit.json --step all)" % (name, f.get("where"), f.get("part"), f.get("detail")))
                    continue
                probs.append("%s, %s: %s - %s %s%s (L54: fix the drawing, or mark a crossing that is meant with "
                             "data-may-cross / data-no-contain / data-may-overlap; a kit figure: course-visuals\\kit\\"
                             "scripts\\studio.py shows it at every step in seconds)"
                             % (name, f.get("where"), f.get("check"), f.get("part"), f.get("detail"),
                                (" - " + f["other"]) if f.get("other") else ""))
    finally:
        shutil.rmtree(prof, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
    return probs, None


def main(argv=None):
    pages = [os.path.abspath(p) for p in (argv if argv is not None else sys.argv[1:])]
    if not pages:
        print(__doc__)
        return 2
    probs, note = check(pages)
    if note:
        print("Not checked: " + note)
        return 2
    for x in probs:
        print("  - " + x)
    print("%d drawing problem(s) in %d page(s)" % (len(probs), len(pages)) if probs else "Every drawing is whole and clean (%d page(s))." % len(pages))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
