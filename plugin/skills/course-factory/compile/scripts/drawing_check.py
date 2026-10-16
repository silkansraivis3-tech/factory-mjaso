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
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
AUDIT = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "audit_drawing.js")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "scripts"))
from measure_slides import find_browser  # noqa: E402

SIZE = (1280, 800)
OUT = "__audit_out"
KEEP = ("check", "where", "part", "other", "detail")
WRITE = ("function __done(r){var p=document.createElement('pre');p.id='%s';p.textContent=JSON.stringify(r);"
         "document.body.appendChild(p);}"
         "function __keep(f,pre){return {check:f.check,where:(pre||'')+f.where,part:f.part,other:f.other||'',detail:f.detail||''};}" % OUT)
# a deck: every slide in turn, as the deck shows it (audit_drawing.js all() presses Start)
DECK = WRITE + ("setTimeout(function(){AuditDrawing.all().then(function(r){"
                "__done({drawings:r.drawings||0,aborted:r.ABORTED||'',findings:(r.findings||[]).map(function(f){return __keep(f)})});"
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


def wrapper(page, deck):
    """the page as it is, read from its own folder (<base>), with the probe and its runner added at the end"""
    text = io.open(page, encoding="utf-8").read()
    base = '<base href="%s/">' % Path(os.path.dirname(os.path.abspath(page))).as_uri()
    text = re.sub(r"<head>", "<head>" + base, text, count=1, flags=re.I)
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
            p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--user-data-dir=" +
                                os.path.join(tmp, "p"), "--window-size=1280,800", "--dump-dom", Path(f).as_uri()],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            m = re.search(r'<pre id="cal">(\d+)x(\d+)</pre>', p.stdout or "")
            _WIN["d"] = (1280 - int(m.group(1)), 800 - int(m.group(2))) if m else (0, 0)
        except (OSError, subprocess.TimeoutExpired):
            _WIN["d"] = (0, 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return size[0] + _WIN["d"][0], size[1] + _WIN["d"][1]


def run_page(exe, page, prof, tmp):
    deck = os.path.basename(page).lower() == "index.html" and os.path.basename(os.path.dirname(page)).lower() == "presentation"
    w = os.path.join(tmp, "check_%d.html" % abs(hash(page)))
    io.open(w, "w", encoding="utf-8").write(wrapper(page, deck))
    try:
        p = subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--mute-audio",
                            "--user-data-dir=" + prof, "--allow-file-access-from-files", "--window-size=%d,%d" % window_for(exe),
                            "--virtual-time-budget=%d" % (120000 if deck else 8000), "--dump-dom", Path(w).as_uri()],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    except (OSError, subprocess.TimeoutExpired) as err:
        return {"error": str(err)}
    m = re.search(r'<pre id="%s">(.*?)</pre>' % OUT, p.stdout, re.S)
    if not m:
        return {"error": "the page did not finish loading in the hidden browser"}
    try:
        return json.loads(html.unescape(m.group(1)))
    except ValueError:
        return {"error": "the probe's answer could not be read"}


def check(pages, root=None):
    """(problems, a note when the check could not run) for the built pages"""
    exe = find_browser()
    if not exe:
        return [], ("the drawing check (parts poking out, cut off, crowded labels) did not run - no Chrome or Edge on this "
                    "computer; set CF_BROWSER to one, or run AuditDrawing.page() / .all() by hand in a browser")
    probs = []
    prof, tmp = tempfile.mkdtemp(prefix="cf_drawing_"), tempfile.mkdtemp(prefix="cf_pages_")
    try:
        for page in pages:
            name = os.path.relpath(page, root).replace("\\", "/") if root else page
            res = run_page(exe, page, prof, tmp)
            if res.get("error") or res.get("aborted"):
                probs.append("%s: the drawing check could not finish - %s" % (name, res.get("error") or res.get("aborted")))
                continue
            for f in res.get("findings", []):
                if f.get("check") == "contrast":     # a kit figure's part that cannot be seen on its dark panel (finding 13)
                    probs.append("%s, %s: contrast - %s %s (L54: colour the part for the figure's dark panel, or mark one "
                                 "meant to be quiet data-low-contrast)" % (name, f.get("where"), f.get("part"), f.get("detail")))
                    continue
                if f.get("check") == "small text":   # a kit figure's word under 12.5 px at 1280 x 800 (2.48.0)
                    probs.append("%s, %s: small text - %s %s (try the figure in the studio: course-visuals\\kit\\scripts\\"
                                 "studio.py <figure>.kit.json)" % (name, f.get("where"), f.get("part"), f.get("detail")))
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
